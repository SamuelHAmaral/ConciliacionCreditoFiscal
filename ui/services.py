"""Validation, logging cleanup, and orchestration for desktop / optional web UI."""

from __future__ import annotations

import json
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Project root: reconciliation_engine/
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SRC = _PROJECT_ROOT / "src"


def ensure_src_on_path() -> None:
    """Allow imports of ingestion, pipeline, rules, etc. (dev only; frozen uses the bundle)."""
    if getattr(sys, "frozen", False):
        return
    s = str(_SRC.resolve())
    if s not in sys.path:
        sys.path.insert(0, s)


def project_root() -> Path:
    return _PROJECT_ROOT.resolve()


def prune_reconciliation_file_handlers(logs_dir: Path) -> None:
    """
    Remove root FileHandlers pointing under logs_dir that look like conciliacion_*.log
    to avoid unbounded handler growth on repeated UI runs (Streamlit/Tk reruns).
    """
    try:
        logs_abs = str(logs_dir.resolve()).lower()
    except OSError:
        return
    root = logging.getLogger()
    for h in list(root.handlers):
        if not isinstance(h, logging.FileHandler):
            continue
        bf = str(getattr(h, "baseFilename", "")).lower()
        if logs_abs in bf.replace("\\", "/") and "conciliacion_" in bf:
            try:
                h.close()
            except Exception:
                pass
            root.removeHandler(h)


@dataclass
class AccountJob:
    account: str
    ledger_path: Path


@dataclass
class RunConfig:
    salida: Path
    jobs: list[AccountJob]
    sql_csv: Path | None = None
    famafa_compras: Path | None = None
    famafa_compras_by_account: dict[str, Path] | None = None
    famafa_ventas: Path | None = None
    fecha_desde: str | None = None
    fecha_hasta: str | None = None
    amount_tolerance_1279: float = 0.0


@dataclass
class AccountRunResult:
    account: str
    ok: bool
    output: Path | None = None
    error: str | None = None
    error_code: str | None = None
    metrics: dict[str, Any] = field(default_factory=dict)


@dataclass
class RunValidationResult:
    global_errors: list[str] = field(default_factory=list)
    account_errors: dict[str, list[str]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return bool(self.global_errors) or any(self.account_errors.values())

    def flat_errors(self) -> list[str]:
        out = list(self.global_errors)
        for acc in sorted(self.account_errors):
            out.extend(self.account_errors[acc])
        return out


def _famafa_compras_for(cfg: RunConfig, account: str) -> Path | None:
    if cfg.famafa_compras_by_account and account in cfg.famafa_compras_by_account:
        return cfg.famafa_compras_by_account[account]
    return cfg.famafa_compras


def validate_run_config(
    cfg: RunConfig,
    *,
    lang: str = "es",
    include_precheck: bool = True,
) -> RunValidationResult:
    from ui.i18n import account_label, t
    from ingestion.validate_inputs import validate_account_inputs, validate_1279_dates

    result = RunValidationResult()
    if not cfg.jobs:
        result.global_errors.append(t("val_no_jobs", lang))
    for j in cfg.jobs:
        if not j.ledger_path.is_file():
            result.account_errors.setdefault(j.account, []).append(
                t(
                    "val_ledger_missing",
                    lang,
                    label=account_label(j.account, lang),
                    path=str(j.ledger_path),
                )
            )
    if any(j.account == "1279" for j in cfg.jobs):
        if not cfg.sql_csv or not cfg.sql_csv.is_file():
            result.global_errors.append(t("val_sql_required", lang))
        if not (cfg.fecha_desde and str(cfg.fecha_desde).strip()):
            result.global_errors.append(t("val_fecha_desde", lang))
        if not (cfg.fecha_hasta and str(cfg.fecha_hasta).strip()):
            result.global_errors.append(t("val_fecha_hasta", lang))
        if cfg.fecha_desde and cfg.fecha_hasta:
            drep = validate_1279_dates(
                cfg.fecha_desde,
                cfg.fecha_hasta,
                sql_path=cfg.sql_csv if include_precheck else None,
            )
            for e in drep.errors:
                result.global_errors.append(t("val_date_invalid", lang, detail=e))
            for w in drep.warnings:
                result.warnings.append(t("val_date_warn", lang, detail=w))
    if any(j.account in ("469", "1280") for j in cfg.jobs):
        for j in cfg.jobs:
            if j.account not in ("469", "1280"):
                continue
            fc = _famafa_compras_for(cfg, j.account)
            if fc is None or not fc.is_file():
                result.account_errors.setdefault(j.account, []).append(
                    t("val_fc_required", lang, label=account_label(j.account, lang))
                )
    if any(j.account == "2874" for j in cfg.jobs):
        if not cfg.famafa_ventas or not cfg.famafa_ventas.is_file():
            result.global_errors.append(t("val_fv_required", lang))

    if include_precheck and not result.has_errors:
        for job in cfg.jobs:
            rep = validate_account_inputs(
                job.account,
                ledger_path=job.ledger_path,
                sql_csv=cfg.sql_csv,
                famafa_compras=_famafa_compras_for(cfg, job.account),
                famafa_ventas=cfg.famafa_ventas,
                fecha_desde=cfg.fecha_desde,
                fecha_hasta=cfg.fecha_hasta,
            )
            for e in rep.errors:
                result.account_errors.setdefault(job.account, []).append(
                    t("val_precheck_error", lang, detail=e)
                )
            for w in rep.warnings:
                result.warnings.append(t("val_precheck_warn", lang, detail=w))

    cfg._warnings = list(result.warnings)  # type: ignore[attr-defined]
    return result


def run_batch(
    cfg: RunConfig,
    *,
    verbose: bool = False,
    console_log: bool = False,
    ui_source: str = "desktop",
    skip_input_validation: bool = False,
    run_id: str | None = None,
) -> tuple[str, Path, Path, list[AccountRunResult]]:
    """
    Run all jobs under one audit run_id.

    Returns (run_id, log_path, audit_path, results).
    """
    ensure_src_on_path()
    from datetime import datetime, timezone

    from ingestion.validate_inputs import validate_account_inputs
    from pipeline.errors import audit_error_fields, error_from_exception, format_user_message
    from pipeline.logging_audit import setup_run_logging
    from pipeline.run_manifest import build_run_manifest, write_run_manifest
    from pipeline.run_reconciliation import run_account

    salida = cfg.salida.resolve()
    started_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    salida.mkdir(parents=True, exist_ok=True)
    logs_sub = salida / "logs"
    prune_reconciliation_file_handlers(logs_sub)

    run_id, log_path, audit_path, audit = setup_run_logging(
        salida,
        console=console_log,
        verbose=verbose,
        run_id=run_id,
    )
    audit.record(
        "ui_run_start",
        "ok",
        source=ui_source,
        salida=str(salida),
        accounts=[j.account for j in cfg.jobs],
    )

    results: list[AccountRunResult] = []
    try:
        for job in cfg.jobs:
            if not skip_input_validation:
                rep = validate_account_inputs(
                    job.account,
                    ledger_path=job.ledger_path,
                    sql_csv=cfg.sql_csv,
                    famafa_compras=_famafa_compras_for(cfg, job.account),
                    famafa_ventas=cfg.famafa_ventas,
                    fecha_desde=cfg.fecha_desde,
                    fecha_hasta=cfg.fecha_hasta,
                )
                if rep.errors:
                    from pipeline.errors import ErrorCode, ReconciliationError

                    raise ReconciliationError(ErrorCode.E_VALIDATION, "; ".join(rep.errors))
                for warn in rep.warnings:
                    logging.getLogger("conciliation").warning(
                        "[%s] Advertencia previa: %s", job.account, warn
                    )
            out_xlsx = salida / f"CUADRE_{job.account}_reconciliacion.xlsx"
            kw: dict[str, Any] = {
                "sql_csv": cfg.sql_csv,
                "famafa_compras": _famafa_compras_for(cfg, job.account),
                "famafa_ventas": cfg.famafa_ventas,
                "fecha_desde": cfg.fecha_desde,
                "fecha_hasta": cfg.fecha_hasta,
                "amount_tolerance_1279": cfg.amount_tolerance_1279,
                "output": out_xlsx,
                "audit": audit,
            }
            try:
                path = run_account(job.account, job.ledger_path, **kw)
                metrics = _read_account_metrics(audit_path, job.account)
                results.append(
                    AccountRunResult(account=job.account, ok=True, output=path, metrics=metrics)
                )
                audit.record("ui_job_ok", "ok", account=job.account, output=str(path))
            except Exception as e:
                code, msg = error_from_exception(e)
                err = format_user_message(code, msg)
                results.append(
                    AccountRunResult(
                        account=job.account,
                        ok=False,
                        error=err,
                        error_code=code.value,
                        metrics={},
                    )
                )
                audit.record(
                    "ui_job_failed",
                    "failed",
                    account=job.account,
                    **audit_error_fields(e),
                )
                logging.getLogger("conciliation").error("[%s] %s", job.account, err)
        n_ok = sum(1 for r in results if r.ok)
        audit.record(
            "ui_run_complete",
            "ok" if n_ok == len(results) else "failed",
            outputs=[str(r.output) for r in results if r.output],
            error_count=len(results) - n_ok,
            jobs=len(results),
            ok_count=n_ok,
        )
        ended_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        manifest = build_run_manifest(
            run_id=run_id,
            source=ui_source,
            salida=salida,
            accounts=[j.account for j in cfg.jobs],
            results=results,
            log_path=log_path,
            audit_path=audit_path,
            started_at=started_at,
            ended_at=ended_at,
            inputs={
                "sql_csv": str(cfg.sql_csv) if cfg.sql_csv else None,
                "famafa_compras": str(cfg.famafa_compras) if cfg.famafa_compras else None,
                "famafa_ventas": str(cfg.famafa_ventas) if cfg.famafa_ventas else None,
                "fecha_desde": cfg.fecha_desde,
                "fecha_hasta": cfg.fecha_hasta,
                "amount_tolerance_1279": cfg.amount_tolerance_1279,
            },
        )
        write_run_manifest(salida / "logs" / f"run_manifest_{run_id}.json", manifest)
    finally:
        audit.close()

    return run_id, log_path, audit_path, results


def _read_account_metrics(audit_path: Path, account: str) -> dict[str, Any]:
    """Best-effort: match_complete + last integrity_check for this account from JSONL."""
    if not audit_path.is_file():
        return {}
    metrics: dict[str, Any] = {}
    try:
        for line in audit_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get("account") != account:
                continue
            stage = row.get("stage")
            if stage == "match_complete":
                metrics.update(
                    {
                        "matched_rows": row.get("matched_rows"),
                        "unmatched_ledger_rows": row.get("unmatched_ledger_rows"),
                        "unmatched_system_rows": row.get("unmatched_system_rows"),
                    }
                )
            elif stage == "integrity_check":
                metrics["integrity_ok"] = bool(row.get("integrity_ok"))
                issues = row.get("integrity_issues")
                if isinstance(issues, list):
                    metrics["integrity_issues"] = issues
    except Exception:
        return metrics
    if "integrity_ok" not in metrics:
        metrics["integrity_ok"] = True
    return metrics

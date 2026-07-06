"""End-to-end reconciliation CLI for accounts 1279, 469, 1280, 2874."""

from __future__ import annotations

import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import Callable

import pandas as pd

from ingestion.ledger_parser import parse_ledger
from ingestion.system_imports import SystemFileCache, load_system_file
from ingestion.validate_inputs import validate_account_inputs
from reconcile.matcher import match_amount_only_one_to_one, match_exact_one_to_one
from reporting.cuadre_writer import write_cuadre_workbook
from rules.account_rules import (
    add_ledger_match_amount,
    filter_famafa_1280,
    filter_famafa_2874,
    filter_famafa_469,
    filter_ledger_account_1279,
    filter_sql_account_1279,
)
from pipeline.errors import ErrorCode, ReconciliationError, audit_error_fields
from pipeline.logging_audit import AuditTrail
from qa.integrity_check import run_integrity_checks

logger = logging.getLogger(__name__)


def _build_locked_fallback_path(path: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return path.with_name(f"{path.stem}_{stamp}{path.suffix}")


def _write_workbook_resilient(
    out_path: Path,
    *,
    account: str,
    matched: pd.DataFrame,
    unmatched_ledger: pd.DataFrame,
    unmatched_system: pd.DataFrame,
    ledger_side: str,
    audit_fn: Callable[..., None],
) -> Path:
    try:
        write_cuadre_workbook(
            out_path,
            account,
            matched,
            unmatched_ledger,
            unmatched_system,
            ledger_side=ledger_side,
        )
        return out_path
    except PermissionError:
        fallback = _build_locked_fallback_path(out_path)
        msg = (
            f"Archivo de salida bloqueado: {out_path.name}. "
            f"Reintentando con archivo alternativo: {fallback.name}"
        )
        logger.warning("[%s] %s", account, msg)
        audit_fn(
            "excel_write_locked",
            "warning",
            error_code=ErrorCode.E_FILE_LOCK.value,
            path=str(out_path),
            fallback_path=str(fallback),
            message=msg,
        )
        write_cuadre_workbook(
            fallback,
            account,
            matched,
            unmatched_ledger,
            unmatched_system,
            ledger_side=ledger_side,
        )
        audit_fn("excel_write_retry_ok", "ok", path=str(fallback), original_path=str(out_path))
        return fallback


def run_account(
    account: str,
    ledger_path: Path,
    *,
    sql_csv: Path | None = None,
    famafa_compras: Path | None = None,
    famafa_ventas: Path | None = None,
    fecha_desde: str | None = None,
    fecha_hasta: str | None = None,
    amount_tolerance_1279: float = 0.0,
    match_469_amount_only: bool = False,
    output: Path | None = None,
    audit: AuditTrail | None = None,
    system_cache: SystemFileCache | None = None,
) -> Path:
    account = account.strip()
    ledger_path = ledger_path.resolve()
    out_path = (output or Path("output") / f"CUADRE_{account}_reconciliacion.xlsx").resolve()

    def _audit(stage: str, status: str = "ok", **kw: object) -> None:
        if audit is not None:
            kw.pop("account", None)
            audit.record(stage, status, account=account, **kw)

    _audit(
        "account_start",
        "ok",
        ledger=str(ledger_path),
        output=str(out_path),
        sql_csv=str(sql_csv) if sql_csv else None,
        famafa_compras=str(famafa_compras) if famafa_compras else None,
        famafa_ventas=str(famafa_ventas) if famafa_ventas else None,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        amount_tolerance_1279=amount_tolerance_1279,
        match_469_amount_only=match_469_amount_only,
    )
    logger.info("[%s] Inicio de conciliacion", account)

    try:
        pre = validate_account_inputs(
            account,
            ledger_path=ledger_path,
            sql_csv=sql_csv,
            famafa_compras=famafa_compras,
            famafa_ventas=famafa_ventas,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
        )
        for warn in pre.warnings:
            logger.warning("[%s] Advertencia previa: %s", account, warn)
            _audit("precheck_warning", "ok", warning=warn)
        if pre.errors:
            raise ReconciliationError(ErrorCode.E_VALIDATION, "; ".join(pre.errors))

        logger.info("[%s] Etapa: parsear_mayor ruta=%s", account, ledger_path)
        ledger_raw = parse_ledger(ledger_path, account)
        n_ledger = len(ledger_raw)
        _audit(
            "ledger_parsed",
            "ok",
            rows_total=n_ledger,
            path=str(ledger_path),
        )
        logger.info("[%s] Mayor parseado: %s filas", account, n_ledger)

        if account == "1279":
            if not sql_csv:
                raise ValueError("La cuenta 1279 requiere sql_csv")
            if amount_tolerance_1279 < 0:
                raise ValueError("amount_tolerance_1279 debe ser >= 0")
            side = "Debito"
            fd = pd.Timestamp(fecha_desde) if fecha_desde else None
            fh = pd.Timestamp(fecha_hasta) if fecha_hasta else None
            n_leg_before = len(ledger_raw)
            ledger_raw = filter_ledger_account_1279(
                ledger_raw,
                fecha_desde=fd,
                fecha_hasta=fh,
            )
            _audit(
                "ledger_date_filtered",
                "ok",
                rows_before=n_leg_before,
                rows_after=len(ledger_raw),
                fecha_desde=str(fd.date()) if fd is not None else None,
                fecha_hasta=str(fh.date()) if fh is not None else None,
            )
            logger.info(
                "[%s] Mayor filtrado por fecha: %s -> %s filas",
                account,
                n_leg_before,
                len(ledger_raw),
            )
            logger.info("[%s] Etapa: cargar_sql ruta=%s", account, sql_csv)
            sql_df = load_system_file(sql_csv, "sql", cache=system_cache)
            n_sql_raw = len(sql_df)
            logger.info("[%s] Etapa: filtrar_sql fecha_desde=%s fecha_hasta=%s", account, fd, fh)
            system_df = filter_sql_account_1279(sql_df, fecha_desde=fd, fecha_hasta=fh)
            _audit(
                "system_filtered",
                "ok",
                source="sql",
                rows_raw=n_sql_raw,
                rows_after_rules=len(system_df),
                path=str(sql_csv.resolve()),
            )
            logger.info(
                "[%s] SQL cargado %s filas, despues de reglas %s filas",
                account,
                n_sql_raw,
                len(system_df),
            )
        elif account == "469":
            if not famafa_compras:
                raise ValueError("La cuenta 469 requiere famafa_compras")
            side = "Debito"
            logger.info("[%s] Etapa: cargar_famafa_compras ruta=%s", account, famafa_compras)
            raw = load_system_file(famafa_compras, "famafa", cache=system_cache)
            n_raw = len(raw)
            system_df = filter_famafa_469(raw)
            _audit(
                "system_filtered",
                "ok",
                source="famafa_compras",
                rows_raw=n_raw,
                rows_after_rules=len(system_df),
                path=str(famafa_compras.resolve()),
            )
            logger.info(
                "[%s] FAMAFA compras %s filas, despues de reglas %s filas",
                account,
                n_raw,
                len(system_df),
            )
        elif account == "1280":
            if not famafa_compras:
                raise ValueError("La cuenta 1280 requiere famafa_compras")
            side = "Debito"
            logger.info("[%s] Etapa: cargar_famafa_compras ruta=%s", account, famafa_compras)
            raw = load_system_file(famafa_compras, "famafa", cache=system_cache)
            n_raw = len(raw)
            system_df = filter_famafa_1280(raw)
            _audit(
                "system_filtered",
                "ok",
                source="famafa_compras",
                rows_raw=n_raw,
                rows_after_rules=len(system_df),
                path=str(famafa_compras.resolve()),
            )
            logger.info(
                "[%s] FAMAFA compras %s filas, despues de reglas %s filas",
                account,
                n_raw,
                len(system_df),
            )
        elif account == "2874":
            if not famafa_ventas:
                raise ValueError("La cuenta 2874 requiere famafa_ventas")
            side = "Credito"
            logger.info("[%s] Etapa: cargar_famafa_ventas ruta=%s", account, famafa_ventas)
            raw = load_system_file(famafa_ventas, "famafa", cache=system_cache)
            n_raw = len(raw)
            system_df = filter_famafa_2874(raw)
            _audit(
                "system_filtered",
                "ok",
                source="famafa_ventas",
                rows_raw=n_raw,
                rows_after_rules=len(system_df),
                path=str(famafa_ventas.resolve()),
            )
            logger.info(
                "[%s] FAMAFA ventas %s filas, despues de reglas %s filas",
                account,
                n_raw,
                len(system_df),
            )
        else:
            raise ValueError(f"Cuenta no soportada: {account}")

        logger.info("[%s] Etapa: monto_conciliacion_mayor lado=%s", account, side)
        ledger_m = add_ledger_match_amount(ledger_raw, side)
        ledger_m = ledger_m.copy()
        if "Fecha" not in ledger_m.columns:
            raise ValueError(
                "El mayor debe contener la columna 'Fecha' tras el parseo para conciliar por fecha"
            )
        ledger_m["_match_date"] = pd.to_datetime(ledger_m["Fecha"], errors="coerce").dt.normalize()
        n_leg_match = len(ledger_m)
        _audit(
            "ledger_match_side",
            "ok",
            side=side,
            rows_with_amount=n_leg_match,
        )
        logger.info("[%s] Filas mayor con monto %s: %s", account, side, n_leg_match)

        amount_tolerance = amount_tolerance_1279 if account == "1279" else 0.0
        use_amount_only = account == "469" and match_469_amount_only
        match_mode = "amount_only" if use_amount_only else "amount_and_date"
        logger.info(
            "[%s] Etapa: conciliar_1_a_1 modo=%s tolerancia_monto=%s",
            account,
            match_mode,
            amount_tolerance,
        )
        if use_amount_only:
            matched, u_leg, u_sys = match_amount_only_one_to_one(
                ledger_m,
                system_df,
                amount_tolerance=amount_tolerance,
            )
        else:
            matched, u_leg, u_sys = match_exact_one_to_one(
                ledger_m,
                system_df,
                amount_tolerance=amount_tolerance,
            )
        n_m, n_ul, n_us = len(matched), len(u_leg), len(u_sys)
        _audit(
            "match_complete",
            "ok",
            matched_rows=n_m,
            unmatched_ledger_rows=n_ul,
            unmatched_system_rows=n_us,
            amount_tolerance=amount_tolerance,
            match_mode=match_mode,
        )
        logger.info(
            "[%s] Conciliacion: conciliadas=%s pendientes_mayor=%s pendientes_sistema=%s",
            account,
            n_m,
            n_ul,
            n_us,
        )

        n_ledger_rows = len(ledger_m)
        n_system_rows = len(system_df)
        partition = run_integrity_checks(
            ledger_rows=n_ledger_rows,
            system_rows=n_system_rows,
            matched=n_m,
            unmatched_ledger=n_ul,
            unmatched_system=n_us,
        )
        if partition.ok:
            _audit(
                "integrity_check",
                "ok",
                integrity_ok=True,
                integrity_issues=[],
                ledger_rows=n_ledger_rows,
                system_rows=n_system_rows,
            )
        else:
            _audit(
                "integrity_check",
                "failed",
                integrity_ok=False,
                integrity_issues=list(partition.issues),
                ledger_rows=n_ledger_rows,
                system_rows=n_system_rows,
            )
            logger.warning(
                "[%s] Integridad (particion): %s",
                account,
                ", ".join(partition.issues),
            )

        out_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info("[%s] Etapa: escribir_excel ruta=%s", account, out_path)
        _audit("excel_write_start", "ok", path=str(out_path))
        out_path = _write_workbook_resilient(
            out_path,
            account=account,
            matched=matched,
            unmatched_ledger=u_leg,
            unmatched_system=u_sys,
            ledger_side=side,
            audit_fn=_audit,
        )
        _audit("excel_write_complete", "ok", path=str(out_path))
        expected_rows = n_m + n_ul + n_us
        full = run_integrity_checks(
            ledger_rows=n_ledger_rows,
            system_rows=n_system_rows,
            matched=n_m,
            unmatched_ledger=n_ul,
            unmatched_system=n_us,
            output_path=out_path,
            account=account,
        )
        _audit(
            "integrity_check",
            "ok" if full.ok else "failed",
            integrity_ok=full.ok,
            integrity_issues=list(full.issues),
            expected_excel_rows=expected_rows,
            output_path=str(out_path),
        )
        if not full.ok:
            logger.warning(
                "[%s] Integridad (final): %s",
                account,
                ", ".join(full.issues),
            )
        _audit("account_complete", "ok", output=str(out_path), integrity_ok=full.ok)
        logger.info("[%s] Finalizado: %s", account, out_path)
        return out_path

    except ReconciliationError as e:
        _audit("account_failed", "failed", **audit_error_fields(e))
        logger.error("[%s] [%s] %s", account, e.code.value, e.message)
        raise
    except ValueError as e:
        _audit("account_failed", "failed", **audit_error_fields(e))
        logger.error("[%s] Error de validacion: %s", account, e)
        raise
    except Exception as e:
        _audit("account_failed", "failed", **audit_error_fields(e))
        logger.exception("[%s] Error durante la conciliacion", account)
        raise


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Multi-account financial reconciliation")
    p.add_argument("--account", required=True, choices=["1279", "469", "1280", "2874"])
    p.add_argument("--ledger", required=True, type=Path, help="Path to mayorpc .txt for this account")
    p.add_argument("--sql-csv", type=Path, help="SQL extract CSV (required for 1279)")
    p.add_argument("--famafa-compras", type=Path, help="FAMAFA Compras CSV (469, 1280)")
    p.add_argument("--famafa-ventas", type=Path, help="FAMAFA Ventas CSV (2874)")
    p.add_argument("--fecha-desde", help="Inclusive lower bound for 1279 Fecha_Cont (YYYY-MM-DD)")
    p.add_argument("--fecha-hasta", help="Inclusive upper bound for 1279 Fecha_Cont (YYYY-MM-DD)")
    p.add_argument(
        "--amount-tolerance-1279",
        type=float,
        default=0.0,
        help=(
            "Optional amount tolerance for 1279 matching (same-date still required). "
            "Example: 0.01 allows cent-level differences."
        ),
    )
    p.add_argument("--output", type=Path, help="Output .xlsx path")
    p.add_argument(
        "--log-dir",
        type=Path,
        default=Path("logs"),
        help="Directory for logs/ subfolder (conciliacion_*.log and audit_*.jsonl). Default: ./logs",
    )
    p.add_argument("--quiet-console", action="store_true", help="File log only, no extra console handler")
    p.add_argument("--verbose", "-v", action="store_true", help="More detailed logging")
    return p


def main() -> None:
    args = build_arg_parser().parse_args()
    from pipeline.logging_audit import setup_run_logging

    log_dir = args.log_dir.resolve()
    log_dir.mkdir(parents=True, exist_ok=True)
    _rid, log_path, audit_path, audit = setup_run_logging(
        log_dir,
        console=not args.quiet_console,
        verbose=args.verbose,
    )
    log = logging.getLogger("conciliation")
    try:
        audit.record(
            "cli_run_start",
            "ok",
            account=args.account,
            ledger=str(args.ledger.resolve()),
        )
        log.info("CLI run_id=%s log=%s audit=%s", _rid, log_path, audit_path)
        run_account(
            args.account,
            args.ledger,
            sql_csv=args.sql_csv,
            famafa_compras=args.famafa_compras,
            famafa_ventas=args.famafa_ventas,
            fecha_desde=args.fecha_desde,
            fecha_hasta=args.fecha_hasta,
            amount_tolerance_1279=args.amount_tolerance_1279,
            output=args.output,
            audit=audit,
        )
        audit.record("cli_run_complete", "ok", account=args.account)
    except BaseException:
        audit.record("cli_run_complete", "failed", account=args.account)
        raise
    finally:
        audit.close()


if __name__ == "__main__":
    main()

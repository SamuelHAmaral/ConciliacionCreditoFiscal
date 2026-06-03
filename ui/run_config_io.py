"""Serialize RunConfig for GUI subprocess workers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ui.services import AccountJob, RunConfig


def run_config_to_dict(
    cfg: RunConfig,
    *,
    verbose: bool = False,
    skip_input_validation: bool = True,
    uat_verify: bool = False,
    models_root: Path | None = None,
    ui_source: str = "desktop_tk",
) -> dict[str, Any]:
    famafa_by: dict[str, str] | None = None
    if cfg.famafa_compras_by_account:
        famafa_by = {k: str(v.resolve()) for k, v in cfg.famafa_compras_by_account.items()}
    return {
        "salida": str(cfg.salida.resolve()),
        "jobs": [{"account": j.account, "ledger_path": str(j.ledger_path.resolve())} for j in cfg.jobs],
        "sql_csv": str(cfg.sql_csv.resolve()) if cfg.sql_csv else None,
        "famafa_compras": str(cfg.famafa_compras.resolve()) if cfg.famafa_compras else None,
        "famafa_compras_by_account": famafa_by,
        "famafa_ventas": str(cfg.famafa_ventas.resolve()) if cfg.famafa_ventas else None,
        "fecha_desde": cfg.fecha_desde,
        "fecha_hasta": cfg.fecha_hasta,
        "amount_tolerance_1279": cfg.amount_tolerance_1279,
        "verbose": verbose,
        "skip_input_validation": skip_input_validation,
        "uat_verify": uat_verify,
        "models_root": str(models_root.resolve()) if models_root else None,
        "ui_source": ui_source,
    }


def run_config_from_dict(data: dict[str, Any]) -> RunConfig:
    famafa_by: dict[str, Path] | None = None
    raw_by = data.get("famafa_compras_by_account")
    if raw_by:
        famafa_by = {str(k): Path(v) for k, v in raw_by.items()}
    jobs = [AccountJob(account=j["account"], ledger_path=Path(j["ledger_path"])) for j in data["jobs"]]
    return RunConfig(
        salida=Path(data["salida"]),
        jobs=jobs,
        sql_csv=Path(data["sql_csv"]) if data.get("sql_csv") else None,
        famafa_compras=Path(data["famafa_compras"]) if data.get("famafa_compras") else None,
        famafa_compras_by_account=famafa_by,
        famafa_ventas=Path(data["famafa_ventas"]) if data.get("famafa_ventas") else None,
        fecha_desde=data.get("fecha_desde"),
        fecha_hasta=data.get("fecha_hasta"),
        amount_tolerance_1279=float(data.get("amount_tolerance_1279") or 0.0),
    )


def write_request_json(path: Path, payload: dict[str, Any]) -> Path:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def read_result_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

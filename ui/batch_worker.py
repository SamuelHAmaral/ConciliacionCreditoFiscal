"""GUI batch reconciliation worker (subprocess entry)."""

from __future__ import annotations

import json
import traceback
from datetime import datetime
from pathlib import Path

from qa.uat_compare import UATVariance, compare_with_golden, write_variance_csv
from ui.run_config_io import run_config_from_dict
from ui.services import run_batch


def _uat_row_to_dict(row: UATVariance) -> dict:
    return {
        "account": row.account,
        "model_path": str(row.model_path) if row.model_path else None,
        "output_path": str(row.output_path),
        "model_total": row.model_total,
        "output_total": row.output_total,
        "model_matched": row.model_matched,
        "output_matched": row.output_matched,
        "delta_total": row.delta_total,
        "delta_matched": row.delta_matched,
        "status": row.status,
        "detail": row.detail,
    }


def _write_result(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def run_from_request(request_path: Path) -> int:
    """Execute batch job described by request JSON; return process exit code."""
    request_path = request_path.resolve()
    data = json.loads(request_path.read_text(encoding="utf-8"))

    result_path = Path(data["result_path"])
    run_id = str(data["run_id"])
    cfg = run_config_from_dict(data["config"])

    _write_result(
        result_path,
        {
            "ok": False,
            "phase": "starting",
            "run_id": run_id,
            "log_path": str(cfg.salida / "logs" / f"conciliacion_{run_id}.log"),
            "audit_path": str(cfg.salida / "logs" / f"audit_{run_id}.jsonl"),
        },
    )

    try:
        _write_result(
            result_path,
            {
                "ok": False,
                "phase": "reconciling",
                "run_id": run_id,
                "log_path": str(cfg.salida / "logs" / f"conciliacion_{run_id}.log"),
                "audit_path": str(cfg.salida / "logs" / f"audit_{run_id}.jsonl"),
            },
        )
        rid, log_path, audit_path, results = run_batch(
            cfg,
            verbose=bool(data.get("verbose")),
            console_log=False,
            ui_source=str(data.get("ui_source") or "desktop_tk_subprocess"),
            skip_input_validation=bool(data.get("skip_input_validation", True)),
            run_id=run_id,
        )
        qa_rows: list[dict] = []
        qa_report_path: str | None = None
        if data.get("uat_verify"):
            _write_result(
                result_path,
                {
                    "ok": False,
                    "phase": "uat",
                    "run_id": run_id,
                    "log_path": str(log_path),
                    "audit_path": str(audit_path),
                },
            )
            outputs = {r.account: r.output for r in results if r.ok and r.output}
            models_root = Path(data["models_root"]) if data.get("models_root") else None
            if models_root and models_root.is_dir():
                variances = compare_with_golden(outputs, models_root=models_root)
                qa_rows = [_uat_row_to_dict(row) for row in variances]
                stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                qa_report_path = str(
                    write_variance_csv(
                        variances,
                        cfg.salida / "logs" / f"qa_variance_{stamp}.csv",
                    )
                )

        _write_result(
            result_path,
            {
                "ok": True,
                "phase": "done",
                "run_id": rid,
                "log_path": str(log_path),
                "audit_path": str(audit_path),
                "results": [
                    {
                        "account": r.account,
                        "ok": r.ok,
                        "output": str(r.output) if r.output else None,
                        "error": r.error,
                        "error_code": r.error_code,
                        "metrics": r.metrics,
                    }
                    for r in results
                ],
                "qa_rows": qa_rows,
                "qa_report_path": qa_report_path,
            },
        )
        return 0
    except Exception as exc:
        _write_result(
            result_path,
            {
                "ok": False,
                "phase": "failed",
                "run_id": run_id,
                "error": str(exc),
                "traceback": traceback.format_exc(),
            },
        )
        return 1

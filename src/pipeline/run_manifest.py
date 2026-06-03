"""Build and write run_manifest.json artifacts for reconciliation runs."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def build_run_manifest(
    *,
    run_id: str,
    source: str,
    salida: Path,
    accounts: list[str],
    results: list[Any],
    log_path: Path,
    audit_path: Path,
    inputs: dict[str, Any] | None = None,
    started_at: str | None = None,
    ended_at: str | None = None,
    extra_artifacts: list[str] | None = None,
) -> dict[str, Any]:
    started = started_at or _iso_now()
    ended = ended_at or _iso_now()
    account_rows: list[dict[str, Any]] = []
    for r in results:
        row: dict[str, Any] = {
            "account": getattr(r, "account", ""),
            "ok": bool(getattr(r, "ok", False)),
            "output": str(r.output) if getattr(r, "output", None) else None,
            "error": getattr(r, "error", None),
            "error_code": getattr(r, "error_code", None),
            "metrics": getattr(r, "metrics", {}) or {},
        }
        account_rows.append(row)

    outputs = [row["output"] for row in account_rows if row.get("output")]
    artifacts = [str(log_path), str(audit_path), *outputs]
    if extra_artifacts:
        artifacts.extend(extra_artifacts)

    return {
        "run_id": run_id,
        "source": source,
        "started_at": started,
        "ended_at": ended,
        "salida": str(salida),
        "inputs": inputs or {},
        "accounts_planned": accounts,
        "accounts": account_rows,
        "summary": {
            "jobs": len(account_rows),
            "ok_count": sum(1 for row in account_rows if row["ok"]),
            "error_count": sum(1 for row in account_rows if not row["ok"]),
        },
        "artifacts": artifacts,
    }


def write_run_manifest(path: Path, manifest: dict[str, Any]) -> Path:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return path

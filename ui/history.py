"""Scan audit JSONL files and build run history summaries for the UI."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class AuditRunSummary:
    run_id: str
    audit_path: Path
    started_ts: str | None
    ended_ts: str | None
    source: str | None
    accounts: list[str]
    status: str
    ok_count: int | None
    job_count: int | None
    outputs: list[str]
    errors: list[str]


def _parse_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return rows
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def summarize_audit_file(audit_path: Path) -> AuditRunSummary | None:
    """Build one summary from a single audit_*.jsonl file."""
    stem = audit_path.stem
    if not stem.startswith("audit_"):
        return None
    run_id = stem[len("audit_") :]
    rows = _parse_jsonl(audit_path)
    if not rows:
        return AuditRunSummary(
            run_id=run_id,
            audit_path=audit_path,
            started_ts=None,
            ended_ts=None,
            source=None,
            accounts=[],
            status="unknown",
            ok_count=None,
            job_count=None,
            outputs=[],
            errors=[],
        )

    started_ts = rows[0].get("ts")
    ended_ts = rows[-1].get("ts")
    source = None
    accounts: list[str] = []
    outputs: list[str] = []
    errors: list[str] = []
    status = "ok"
    ok_count: int | None = None
    job_count: int | None = None

    for r in rows:
        st = r.get("stage")
        if st == "ui_run_start":
            source = r.get("source") or source
            acc = r.get("accounts")
            if isinstance(acc, list):
                accounts = [str(x) for x in acc]
        elif st == "easy_run_start":
            source = "easy_run"
            acc = r.get("accounts")
            if isinstance(acc, list):
                accounts = [str(x) for x in acc]
        elif st in ("ui_run_complete", "easy_run_complete", "cli_run_complete"):
            ended_ts = r.get("ts") or ended_ts
            if r.get("status") == "failed":
                status = "failed"
            outs = r.get("outputs")
            if isinstance(outs, list):
                outputs.extend(str(x) for x in outs)
            if isinstance(r.get("ok_count"), int):
                ok_count = r["ok_count"]
            if isinstance(r.get("jobs"), int):
                job_count = r["jobs"]
            ec = r.get("error_count")
            if isinstance(ec, int) and ec > 0:
                status = "failed"
        elif st in ("account_failed", "easy_run_job_failed", "ui_job_failed"):
            status = "failed"
            if r.get("error"):
                errors.append(f"{r.get('account','?')}: {r['error']}")
        elif st == "account_complete" and r.get("output"):
            outputs.append(str(r["output"]))

    # de-dupe outputs
    outputs = list(dict.fromkeys(outputs))

    return AuditRunSummary(
        run_id=run_id,
        audit_path=audit_path,
        started_ts=started_ts,
        ended_ts=ended_ts,
        source=source,
        accounts=accounts,
        status=status,
        ok_count=ok_count if isinstance(ok_count, int) else None,
        job_count=job_count if isinstance(job_count, int) else None,
        outputs=outputs,
        errors=errors,
    )


def list_audit_files(logs_dir: Path) -> list[Path]:
    if not logs_dir.is_dir():
        return []
    files = sorted(
        logs_dir.glob("audit_*.jsonl"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return files


def build_history(logs_dir: Path, *, limit: int = 50) -> list[AuditRunSummary]:
    out: list[AuditRunSummary] = []
    for p in list_audit_files(logs_dir)[:limit]:
        s = summarize_audit_file(p)
        if s:
            out.append(s)
    return out


def find_log_for_run(logs_dir: Path, run_id: str) -> Path | None:
    p = logs_dir / f"conciliacion_{run_id}.log"
    return p if p.is_file() else None

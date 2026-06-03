"""Per-run file logging and JSON Lines audit trail for reconciliation."""

from __future__ import annotations

import json
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, TextIO

AUDIT_LOGGER = "conciliation"


@dataclass
class AuditTrail:
    """Append-only JSON Lines audit file (one object per line)."""

    path: Path
    run_id: str
    _fh: TextIO | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = open(self.path, "a", encoding="utf-8")

    def close(self) -> None:
        if self._fh:
            self._fh.close()
            self._fh = None

    def record(self, stage: str, status: str, **fields: Any) -> None:
        row: dict[str, Any] = {
            "ts": datetime.now().astimezone().replace(microsecond=0).isoformat(),
            "run_id": self.run_id,
            "stage": stage,
            "status": status,
        }
        for k, v in fields.items():
            if isinstance(v, Path):
                row[k] = str(v.resolve())
            elif v is not None:
                row[k] = v
        line = json.dumps(row, ensure_ascii=False, default=str)
        if self._fh:
            self._fh.write(line + "\n")
            self._fh.flush()


def setup_run_logging(
    log_dir: Path,
    *,
    console: bool = True,
    run_id: str | None = None,
    verbose: bool = False,
) -> tuple[str, Path, Path, AuditTrail]:
    """
    Attach a detailed file log and optional console log under ``log_dir/logs/``.

    Returns ``(run_id, log_file_path, audit_jsonl_path, audit_trail)``.
    """
    log_dir = log_dir.resolve()
    logs_sub = log_dir / "logs"
    logs_sub.mkdir(parents=True, exist_ok=True)

    rid = run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = logs_sub / f"conciliacion_{rid}.log"
    audit_path = logs_sub / f"audit_{rid}.jsonl"

    audit = AuditTrail(audit_path, rid)
    audit.record("logging_init", "ok", log_file=str(log_path), message="Auditoria iniciada")

    fmt_file = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    fmt_console = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-5s | %(message)s",
        datefmt="%H:%M:%S",
    )

    root = logging.getLogger()
    root.setLevel(logging.DEBUG if verbose else logging.INFO)

    log_abs = str(log_path.resolve())
    for h in root.handlers:
        if isinstance(h, logging.FileHandler):
            if str(getattr(h, "baseFilename", "")).lower() == log_abs.lower():
                break
    else:
        fh = logging.FileHandler(log_path, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt_file)
        root.addHandler(fh)

    if console:
        has_stdout = any(
            isinstance(h, logging.StreamHandler) and getattr(h, "stream", None) is sys.stdout
            for h in root.handlers
        )
        if not has_stdout:
            ch = logging.StreamHandler(sys.stdout)
            ch.setLevel(logging.INFO)
            ch.setFormatter(fmt_console)
            root.addHandler(ch)

    log = logging.getLogger(AUDIT_LOGGER)
    log.info("Log file: %s", log_path)
    log.info("Audit file: %s", audit_path)
    return rid, log_path, audit_path, audit

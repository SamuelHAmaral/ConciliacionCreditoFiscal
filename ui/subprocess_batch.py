"""Launch reconciliation in a child process (keeps Tk responsive on Windows)."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from ui.run_config_io import run_config_to_dict, write_request_json
from ui.services import RunConfig

_CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


@dataclass
class BatchSubprocessJob:
    run_id: str
    log_path: Path
    audit_path: Path
    result_path: Path
    request_path: Path
    process: subprocess.Popen[int]


def make_run_id() -> str:
    return f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:6]}"


def batch_worker_command(project_root: Path, request_path: Path) -> list[str]:
    """Build argv for the batch worker child process."""
    if getattr(sys, "frozen", False):
        return [sys.executable, "--gui-batch-worker", str(request_path)]
    worker = project_root / "scripts" / "gui_batch_worker.py"
    return [sys.executable, str(worker), "--request", str(request_path)]


def start_batch_subprocess(
    project_root: Path,
    cfg: RunConfig,
    *,
    verbose: bool = False,
    skip_input_validation: bool = True,
    uat_verify: bool = False,
    models_root: Path | None = None,
) -> BatchSubprocessJob:
    run_id = make_run_id()
    logs_dir = cfg.salida.resolve() / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / f"conciliacion_{run_id}.log"
    audit_path = logs_dir / f"audit_{run_id}.jsonl"
    result_path = logs_dir / f"gui_batch_{run_id}.json"
    request_path = logs_dir / f"gui_batch_{run_id}_request.json"

    payload = {
        "run_id": run_id,
        "result_path": str(result_path),
        "verbose": verbose,
        "skip_input_validation": skip_input_validation,
        "uat_verify": uat_verify,
        "models_root": str(models_root.resolve()) if models_root else None,
        "ui_source": "desktop_tk_subprocess",
        "config": run_config_to_dict(
            cfg,
            verbose=verbose,
            skip_input_validation=skip_input_validation,
            uat_verify=uat_verify,
            models_root=models_root,
            ui_source="desktop_tk_subprocess",
        ),
    }
    write_request_json(request_path, payload)

    cmd = batch_worker_command(project_root, request_path)
    proc = subprocess.Popen(
        cmd,
        cwd=str(project_root),
        creationflags=_CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    return BatchSubprocessJob(
        run_id=run_id,
        log_path=log_path,
        audit_path=audit_path,
        result_path=result_path,
        request_path=request_path,
        process=proc,
    )

"""Resolve whether golden-model UAT should run (developer / QA only)."""

from __future__ import annotations

import os
from pathlib import Path

from ui.settings import load_settings


def resolve_run_uat(app_root: Path) -> bool:
    env = os.getenv("RECONCILIATION_RUN_UAT", "").strip().lower()
    if env in ("1", "true", "yes", "on"):
        return True
    settings = load_settings(app_root)
    if settings.get("run_uat", "").strip() == "1":
        return True
    if settings.get("verify_calculations", "").strip() == "1":
        return True
    return False

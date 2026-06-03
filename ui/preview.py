"""Lightweight Excel preview for Streamlit (first N rows per sheet)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

SHEET_NAMES = ("Partidas Conciliadas", "Pendientes en Mayor", "Pendientes en Sistema")


def preview_workbook(path: Path, *, nrows: int = 30) -> dict[str, pd.DataFrame]:
    """
    Read up to ``nrows`` from each known sheet. Missing sheets are skipped.
    """
    path = path.resolve()
    out: dict[str, pd.DataFrame] = {}
    if not path.is_file():
        return out
    try:
        xl = pd.ExcelFile(path, engine="openpyxl")
    except Exception:
        return out
    for name in SHEET_NAMES:
        if name not in xl.sheet_names:
            continue
        try:
            df = pd.read_excel(xl, sheet_name=name, nrows=nrows, engine="openpyxl")
            out[name] = df
        except Exception:
            continue
    return out


def workbook_meta(path: Path) -> dict[str, Any]:
    path = path.resolve()
    meta: dict[str, Any] = {"path": str(path), "size_bytes": None, "sheets": []}
    if not path.is_file():
        return meta
    try:
        meta["size_bytes"] = path.stat().st_size
        xl = pd.ExcelFile(path, engine="openpyxl")
        meta["sheets"] = list(xl.sheet_names)
    except Exception:
        pass
    return meta

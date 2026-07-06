"""Read Fecha_Cont span from SQL extracts (account 1279)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from ingestion.system_imports import (
    load_sql_excel,
    load_sql_extract,
    to_sql_fecha_cont_series,
)

_EXCEL_SUFFIXES = {".xlsx", ".xls", ".xlsm"}
_DATE_IN_NAME = re.compile(r"(\d{4})-(\d{2})-(\d{2})")


@dataclass(frozen=True)
class SqlFechaCoverage:
    fecha_desde: str
    fecha_hasta: str
    distinct_days: int
    row_count: int | None = None


def _norm(name: str) -> str:
    return " ".join(str(name).strip().lower().split())


def _find_fecha_cont_column(df: pd.DataFrame) -> str | None:
    for cand in ("Fecha_Cont", "Fecha Cont", "fecha_cont"):
        for c in df.columns:
            if _norm(c) == _norm(cand):
                return c
    return None


def _load_sql_df(sql_path: Path) -> pd.DataFrame:
    if sql_path.suffix.lower() in _EXCEL_SUFFIXES:
        return load_sql_excel(sql_path)
    return load_sql_extract(sql_path)


def read_sql_fecha_cont_range(
    sql_path: Path,
) -> tuple[pd.Timestamp | None, pd.Timestamp | None, int]:
    """Return min/max Fecha_Cont and distinct day count from the full SQL extract."""
    path = Path(sql_path)
    if not path.is_file():
        return None, None, 0
    try:
        df = _load_sql_df(path)
    except Exception:
        return None, None, 0
    if df.empty:
        return None, None, 0
    col = _find_fecha_cont_column(df)
    if col is None:
        return None, None, 0
    dt = to_sql_fecha_cont_series(df[col]).dropna()
    if dt.empty:
        return None, None, 0
    norm = dt.dt.normalize()
    return norm.min(), norm.max(), int(norm.nunique())


def infer_fecha_range_from_sql_filename(
    sql_path: Path | None,
) -> tuple[str | None, str | None]:
    """Infer a single-day hint from the SQL filename (e.g. Cuenta1279_2026-04-30)."""
    if sql_path is None:
        return None, None
    m = _DATE_IN_NAME.search(Path(sql_path).name)
    if not m:
        return None, None
    day = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return day, day


def infer_fecha_range_from_sql(sql_path: Path | None) -> tuple[str | None, str | None]:
    """Prefer Fecha_Cont min/max in the file; fall back to the filename date."""
    if sql_path is None:
        return None, None
    path = Path(sql_path)
    s_min, s_max, _ = read_sql_fecha_cont_range(path)
    if s_min is not None and s_max is not None:
        return s_min.strftime("%Y-%m-%d"), s_max.strftime("%Y-%m-%d")
    return infer_fecha_range_from_sql_filename(path)


def infer_last_sql_day(sql_path: Path | None) -> str | None:
    """Return the last Fecha_Cont day in the SQL file (or filename fallback)."""
    if sql_path is None:
        return None
    path = Path(sql_path)
    _, s_max, _ = read_sql_fecha_cont_range(path)
    if s_max is not None:
        return pd.Timestamp(s_max).strftime("%Y-%m-%d")
    _, infer_fh = infer_fecha_range_from_sql_filename(path)
    return infer_fh


def sql_fecha_coverage(sql_path: Path | None) -> SqlFechaCoverage | None:
    """Structured SQL date span for UI hints and auto-fill."""
    if sql_path is None:
        return None
    path = Path(sql_path)
    if not path.is_file():
        return None
    s_min, s_max, n_days = read_sql_fecha_cont_range(path)
    if s_min is None or s_max is None:
        return None
    row_count: int | None
    try:
        row_count = len(_load_sql_df(path))
    except Exception:
        row_count = None
    return SqlFechaCoverage(
        fecha_desde=s_min.strftime("%Y-%m-%d"),
        fecha_hasta=s_max.strftime("%Y-%m-%d"),
        distinct_days=n_days,
        row_count=row_count,
    )

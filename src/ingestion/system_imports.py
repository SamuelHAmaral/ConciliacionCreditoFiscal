"""Pandas loaders and normalization for SQL and FAMAFA CSV exports."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Literal

import pandas as pd

SystemSource = Literal["sql", "famafa"]

logger = logging.getLogger(__name__)


def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [str(c).strip().replace("\ufeff", "") for c in out.columns]
    return out


def parse_european_decimal(value: Any) -> float:
    """Parse numbers like '1.090.095,00' or '216,00' to float."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return float("nan")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    s = str(value).strip().replace(" ", "")
    if s == "" or s.lower() in ("nan", "none", "-"):
        return float("nan")
    # Already US-style
    if re.fullmatch(r"-?\d+\.\d+", s):
        return float(s)
    if "," in s:
        whole, frac = s.rsplit(",", 1)
        whole = whole.replace(".", "").replace(",", "")
        frac = re.sub(r"\D", "", frac)
        sign = -1 if whole.startswith("-") else 1
        whole = whole.lstrip("-+")
        if whole == "":
            whole = "0"
        return sign * float(f"{whole}.{frac}")
    # Integer with thousand dots only
    s2 = s.replace(".", "")
    try:
        return float(s2)
    except ValueError:
        return float("nan")


def to_datetime_series(series: pd.Series, *, dayfirst: bool = True) -> pd.Series:
    """Convert mixed date strings to datetime64[ns]."""
    return pd.to_datetime(series, dayfirst=dayfirst, errors="coerce")


def parse_sql_compact_fecha(value: Any) -> pd.Timestamp | pd.NaT:
    """
    Parse SQL export dates stored as compact D(M)MYYYY integers (e.g. 2942026 = 29/04/2026).
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return pd.NaT
    if isinstance(value, pd.Timestamp):
        return value.normalize() if not pd.isna(value) else pd.NaT
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return pd.NaT
        try:
            v = int(float(s))
        except ValueError:
            return pd.to_datetime(value, dayfirst=True, errors="coerce")
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        v = int(value)
    else:
        return pd.to_datetime(value, dayfirst=True, errors="coerce")

    s = str(v)
    if len(s) < 7:
        return pd.NaT
    year = int(s[-4:])
    rest = s[:-4]
    if len(rest) == 3:
        day = int(rest[:2]) if int(rest[:2]) <= 31 else int(rest[0])
        month = int(rest[2]) if int(rest[:2]) <= 31 else int(rest[1:3])
    elif len(rest) == 4:
        day, month = int(rest[:2]), int(rest[2:4])
    elif len(rest) == 2:
        day, month = int(rest[0]), int(rest[1])
    else:
        return pd.NaT
    try:
        return pd.Timestamp(year=year, month=month, day=day).normalize()
    except ValueError:
        return pd.NaT


def to_sql_fecha_cont_series(series: pd.Series) -> pd.Series:
    """Coerce Fecha_Cont from SQL exports (compact ints or standard strings)."""
    if pd.api.types.is_datetime64_any_dtype(series):
        return pd.to_datetime(series, errors="coerce").dt.normalize()
    if pd.api.types.is_numeric_dtype(series):
        return series.map(parse_sql_compact_fecha)
    parsed = series.map(parse_sql_compact_fecha)
    if parsed.notna().sum() >= max(1, int(0.5 * len(series))):
        return parsed
    return to_datetime_series(series, dayfirst=True).dt.normalize()


def _detect_excel_header_row(path: Path, markers: tuple[str, ...], *, max_rows: int = 20) -> int:
    """Return 0-based row index where expected column headers appear."""
    preview = pd.read_excel(path, header=None, nrows=max_rows)
    marker_keys = {re.sub(r"\s+", " ", m.strip().lower()) for m in markers}
    for i in range(len(preview)):
        row_vals = {
            re.sub(r"\s+", " ", str(v).strip().lower())
            for v in preview.iloc[i].tolist()
            if str(v).strip() and str(v).lower() != "nan"
        }
        if marker_keys & row_vals:
            return int(i)
    return 0


def load_sql_extract(
    filepath: str | Path,
    *,
    encoding: str | None = None,
    sep: str = ",",
    **read_csv_kw: Any,
) -> pd.DataFrame:
    """
    Load SQL export CSV with robust defaults (UTF-8 / latin-1 fallback).
    """
    path = Path(filepath)
    encodings = ([encoding] if encoding else []) + ["utf-8-sig", "utf-8", "latin-1"]
    last_err: Exception | None = None
    for enc in encodings:
        try:
            df = pd.read_csv(path, encoding=enc, sep=sep, **read_csv_kw)
            df = normalize_column_names(df)
            logger.info("Loaded SQL extract %s rows=%s encoding=%s", path.name, len(df), enc)
            return df
        except (UnicodeDecodeError, UnicodeError) as e:
            last_err = e
            continue
    if last_err:
        raise last_err
    raise RuntimeError(f"Could not read {path}")


def load_famafa_csv(
    filepath: str | Path,
    *,
    encoding: str | None = None,
    sep: str = ",",
    **read_csv_kw: Any,
) -> pd.DataFrame:
    """Load FAMAFA / PowerBI CSV export."""
    path = Path(filepath)
    encodings = ([encoding] if encoding else []) + ["utf-8-sig", "utf-8", "latin-1"]
    last_err: Exception | None = None
    for enc in encodings:
        try:
            df = pd.read_csv(path, encoding=enc, sep=sep, **read_csv_kw)
            df = normalize_column_names(df)
            logger.info("Loaded FAMAFA %s rows=%s encoding=%s", path.name, len(df), enc)
            return df
        except (UnicodeDecodeError, UnicodeError) as e:
            last_err = e
            continue
    if last_err:
        raise last_err
    raise RuntimeError(f"Could not read {path}")


def load_famafa_excel(
    filepath: str | Path,
    *,
    sheet_name: str | int = 0,
    **read_excel_kw: Any,
) -> pd.DataFrame:
    """Load FAMAFA / PowerBI Excel export (.xlsx)."""
    path = Path(filepath)
    header_row = _detect_excel_header_row(
        path,
        ("Tipo Comprobante", "IVA 10", "Nro. Identific."),
    )
    df = pd.read_excel(path, sheet_name=sheet_name, header=header_row, **read_excel_kw)
    df = normalize_column_names(df)
    logger.info("Loaded FAMAFA Excel %s rows=%s header_row=%s", path.name, len(df), header_row)
    return df


def load_sql_excel(
    filepath: str | Path,
    *,
    sheet_name: str | int = 0,
    **read_excel_kw: Any,
) -> pd.DataFrame:
    """Load SQL extract from Excel when the export is .xlsx instead of CSV."""
    path = Path(filepath)
    header_row = _detect_excel_header_row(
        path,
        ("Fecha_Cont", "IVA ML", "Nro. de Documento"),
    )
    df = pd.read_excel(path, sheet_name=sheet_name, header=header_row, **read_excel_kw)
    df = normalize_column_names(df)
    logger.info("Loaded SQL Excel %s rows=%s header_row=%s", path.name, len(df), header_row)
    return df


_EXCEL_SUFFIXES = {".xlsx", ".xls", ".xlsm"}


def load_system_file(
    filepath: str | Path,
    source: SystemSource,
    *,
    sheet_name: str | int = 0,
    **kwargs: Any,
) -> pd.DataFrame:
    """
    Load SQL or FAMAFA export from CSV or Excel (.xlsx / .xls).

    Parameters
    ----------
    source:
        ``sql`` for account 1279 extracts; ``famafa`` for PowerBI / FAMAFA exports.
    """
    path = Path(filepath)
    suffix = path.suffix.lower()
    if suffix in _EXCEL_SUFFIXES:
        if source == "sql":
            return load_sql_excel(path, sheet_name=sheet_name, **kwargs)
        return load_famafa_excel(path, sheet_name=sheet_name, **kwargs)
    if source == "sql":
        return load_sql_extract(path, **kwargs)
    return load_famafa_csv(path, **kwargs)

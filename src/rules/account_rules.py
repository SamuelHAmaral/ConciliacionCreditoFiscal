"""Account-specific filters and routing for reconciliation."""

from __future__ import annotations

import logging
import re
from typing import Any

import pandas as pd

from config.account_config import account_profile, timbrado_valor_for
from ingestion.system_imports import (
    parse_european_decimal,
    to_datetime_series,
    to_sql_fecha_cont_series,
)

logger = logging.getLogger(__name__)


def _find_column(df: pd.DataFrame, *candidates: str) -> str | None:
    norm_map = {re.sub(r"\s+", " ", str(c).strip().lower()): c for c in df.columns}
    for cand in candidates:
        key = re.sub(r"\s+", " ", cand.strip().lower())
        if key in norm_map:
            return norm_map[key]
    return None


def _require_col(df: pd.DataFrame, *candidates: str) -> str:
    c = _find_column(df, *candidates)
    if c is None:
        raise KeyError(f"Missing column matching one of {candidates!r}; have {list(df.columns)}")
    return c


def _profile_filter(account: str, key: str, default: Any) -> Any:
    prof = account_profile(account)
    filters = prof.get("filters") if isinstance(prof.get("filters"), dict) else {}
    return filters.get(key, default)


def _match_candidates_for(account: str, default: tuple[str, ...]) -> tuple[str, ...]:
    prof = account_profile(account)
    base = list(default)
    col = str(prof.get("match_column", "")).strip()
    if col and col not in base:
        base.insert(0, col)
    return tuple(base)


def _coerce_numeric_series(s: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(s):
        return pd.to_numeric(s, errors="coerce")
    return s.map(parse_european_decimal)


def normalize_timbrado(value: Any) -> str:
    """Normalize timbrado for string-safe comparison (e.g. 12345678 vs '12345678')."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    if isinstance(value, bool):
        return str(int(value))
    if isinstance(value, (int, float)):
        f = float(value)
        if abs(f - round(f)) < 1e-9:
            return str(int(round(f)))
        return str(value).strip()
    s = str(value).strip()
    if re.fullmatch(r"-?\d+\.0+", s):
        return str(int(float(s)))
    return s


def _require_fecha_column(df: pd.DataFrame) -> str:
    c = _find_column(
        df,
        "Fecha Comprobante",
        "Fecha comprobante",
        "Fecha Emision",
        "Fecha emision",
        "Fecha de emision",
        "Fecha Contabilizacion",
        "Fecha contabilizacion",
        "Fecha_Cont",
        "Fecha Cont",
        "Fecha",
    )
    if c is None:
        raise KeyError(
            "FAMAFA export must include a date column for strict reconciliation "
            "(e.g. Fecha Comprobante, Fecha, Fecha_Cont). "
            f"Columns present: {list(df.columns)}"
        )
    return c


def filter_ledger_account_1279(
    df: pd.DataFrame,
    *,
    fecha_desde: pd.Timestamp | None = None,
    fecha_hasta: pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Account 1279: restrict mayor rows to the same calendar window as SQL."""
    if "Fecha" not in df.columns:
        raise KeyError("Ledger missing 'Fecha' column")
    out = df.copy()
    dates = pd.to_datetime(out["Fecha"], errors="coerce").dt.normalize()
    n0 = len(out)
    if fecha_desde is not None:
        out = out[dates >= pd.Timestamp(fecha_desde).normalize()]
        dates = dates.loc[out.index]
    if fecha_hasta is not None:
        out = out[dates <= pd.Timestamp(fecha_hasta).normalize()]
    logger.info("1279 ledger date filter: %s -> %s rows", n0, len(out))
    return out.reset_index(drop=True)


def filter_sql_account_1279(
    df: pd.DataFrame,
    *,
    fecha_desde: pd.Timestamp | None = None,
    fecha_hasta: pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Account 1279: SQL extract filtered by Fecha_Cont and required columns."""
    df = df.copy()
    fec_col = _require_col(df, "Fecha_Cont", "Fecha Cont", "fecha_cont")
    df[fec_col] = to_sql_fecha_cont_series(df[fec_col])
    n0 = len(df)
    if fecha_desde is not None:
        df = df[df[fec_col] >= pd.Timestamp(fecha_desde)]
    if fecha_hasta is not None:
        df = df[df[fec_col] <= pd.Timestamp(fecha_hasta)]
    logger.info("1279 SQL date filter: %s -> %s rows", n0, len(df))

    col_doc = _find_column(df, "Nro. de Documento", "Nro de Documento", "Nro Documento")
    col_nombre = _find_column(df, "Nombre")
    col_fact = _find_column(df, "Num_Factura", "Num Factura", "Nro Factura")
    col_imponible = _find_column(df, "Imponible ML sin IVA", "Imponible ML sin iva")
    col_iva = _find_column(df, "IVA ML", "Iva ML")

    keep = [fec_col]
    for c in (col_doc, col_nombre, col_fact, col_imponible, col_iva):
        if c and c not in keep:
            keep.append(c)
    out = df[keep].copy()
    out["_match_date"] = pd.to_datetime(out[fec_col], errors="coerce").dt.normalize()
    iva_col = _require_col(out, "IVA ML", "Iva ML")
    out["_match_amount"] = _coerce_numeric_series(out[iva_col])
    out = out[out["_match_amount"].notna() & (out["_match_amount"] != 0)]
    return out.reset_index(drop=True)


def _famafa_base(df: pd.DataFrame, account: str) -> tuple[pd.DataFrame, str, str | None, str]:
    out = df.copy()
    tcol = _require_col(out, "Tipo Comprobante", "Tipo comprobante")
    out[tcol] = pd.to_numeric(out[tcol], errors="coerce")
    tim = _find_column(out, "Nro. Timbrado", "Nro Timbrado", "Nro timbrado")
    iva = _require_col(out, *_match_candidates_for(account, ("IVA 10", "Iva 10", "IVA10")))
    out[iva] = _coerce_numeric_series(out[iva])
    if tim:
        out[tim] = out[tim]  # keep raw for display; filters use normalize_timbrado
    return out, tcol, tim, iva


def _attach_famafa_match_date(out: pd.DataFrame) -> pd.DataFrame:
    fec = _require_fecha_column(out)
    out = out.copy()
    out["_match_date"] = to_datetime_series(out[fec], dayfirst=True).dt.normalize()
    return out


def filter_famafa_469(df: pd.DataFrame) -> pd.DataFrame:
    """469: Tipo 109, exclude configured timbrado (default 12345678), exclude IVA 10 == 0."""
    out, tcol, tim, iva = _famafa_base(df, "469")
    tipo = int(_profile_filter("469", "tipo_comprobante", 109))
    tim_rule = str(_profile_filter("469", "timbrado_rule", "exclude")).strip().lower()
    exclude_t = timbrado_valor_for("469")
    n0 = len(out)
    out = out[out[tcol] == tipo]
    if tim:
        tnorm = out[tim].map(normalize_timbrado)
        if tim_rule in ("include", "only", "solo_igual"):
            out = out[tnorm == exclude_t]
        else:
            out = out[tnorm != exclude_t]
    out = out[out[iva] != 0]
    out = out[out[iva].notna()]
    logger.info("469 FAMAFA rules: %s -> %s rows", n0, len(out))
    out = out.copy()
    out["_match_amount"] = out[iva].astype(float)
    return _attach_famafa_match_date(out).reset_index(drop=True)


def filter_famafa_1280(df: pd.DataFrame) -> pd.DataFrame:
    """1280: Tipo 109, only configured timbrado (default 12345678), exclude IVA 10 == 0."""
    out, tcol, tim, iva = _famafa_base(df, "1280")
    if not tim:
        raise KeyError("1280 requires Nro. Timbrado column")
    tipo = int(_profile_filter("1280", "tipo_comprobante", 109))
    tim_rule = str(_profile_filter("1280", "timbrado_rule", "include")).strip().lower()
    include_t = timbrado_valor_for("1280")
    n0 = len(out)
    out = out[out[tcol] == tipo]
    tnorm = out[tim].map(normalize_timbrado)
    if tim_rule in ("exclude", "excluir_igual"):
        out = out[tnorm != include_t]
    else:
        out = out[tnorm == include_t]
    out = out[out[iva] != 0]
    out = out[out[iva].notna()]
    logger.info("1280 FAMAFA rules: %s -> %s rows", n0, len(out))
    out = out.copy()
    out["_match_amount"] = out[iva].astype(float)
    return _attach_famafa_match_date(out).reset_index(drop=True)


def filter_famafa_2874(df: pd.DataFrame) -> pd.DataFrame:
    """2874: Tipo 110, exclude IVA 10 == 0 (Ventas)."""
    out, tcol, _tim, iva = _famafa_base(df, "2874")
    tipo = int(_profile_filter("2874", "tipo_comprobante", 110))
    n0 = len(out)
    out = out[out[tcol] == tipo]
    out = out[out[iva] != 0]
    out = out[out[iva].notna()]
    logger.info("2874 FAMAFA rules: %s -> %s rows", n0, len(out))
    out = out.copy()
    out["_match_amount"] = out[iva].astype(float)
    return _attach_famafa_match_date(out).reset_index(drop=True)


def add_ledger_match_amount(df: pd.DataFrame, side: str) -> pd.DataFrame:
    out = df.copy()
    side_l = side.strip().lower()
    if side_l == "debito":
        out["_match_amount"] = out["Debito"]
    elif side_l == "credito":
        out["_match_amount"] = out["Credito"]
    else:
        raise ValueError("side must be 'Debito' or 'Credito'")
    out = out[out["_match_amount"].notna() & (out["_match_amount"] != 0)]
    return out.reset_index(drop=True)

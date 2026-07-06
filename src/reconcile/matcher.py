"""Exact amount + date reconciliation with strict 1-to-1 pairing."""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)
_FLOAT_EPS = 1e-9


def _stable_sort(df: pd.DataFrame, amount_col: str, date_col: str) -> pd.DataFrame:
    out = df.copy()
    out["_orig_idx"] = range(len(out))
    return out.sort_values([amount_col, date_col, "_orig_idx"], kind="mergesort", na_position="last")


def _date_key(value: Any) -> pd.Timestamp | None:
    if value is None:
        return None
    ts = pd.Timestamp(value)
    if pd.isna(ts):
        return None
    return ts.normalize()


def match_exact_one_to_one(
    ledger_df: pd.DataFrame,
    system_df: pd.DataFrame,
    *,
    ledger_amount_col: str = "_match_amount",
    system_amount_col: str = "_match_amount",
    ledger_date_col: str = "_match_date",
    system_date_col: str = "_match_date",
    ledger_prefix: str = "Ledger",
    system_prefix: str = "System",
    amount_tolerance: float = 0.0,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Pair rows where ledger amount equals system amount and dates match exactly,
    consuming each row at most once.

    When ``amount_tolerance`` is greater than zero, amounts are considered a match
    if ``abs(ledger_amount - system_amount) <= amount_tolerance``.

    Rows with missing amount or missing/invalid date do not participate in matching
    and remain in the unmatched outputs.

    Returns (matched, unmatched_ledger, unmatched_system).
    """
    if ledger_amount_col not in ledger_df.columns:
        raise KeyError(f"Ledger missing {ledger_amount_col}")
    if system_amount_col not in system_df.columns:
        raise KeyError(f"System missing {system_amount_col}")
    if ledger_date_col not in ledger_df.columns:
        raise KeyError(f"Ledger missing {ledger_date_col} (required for strict date match)")
    if system_date_col not in system_df.columns:
        raise KeyError(f"System missing {system_date_col} (required for strict date match)")
    if amount_tolerance < 0:
        raise ValueError("amount_tolerance must be >= 0")

    ld = ledger_df.copy()
    sy = system_df.copy()
    ld["_lid"] = range(len(ld))
    sy["_sid"] = range(len(sy))

    ld = _stable_sort(ld, ledger_amount_col, ledger_date_col)
    sy = _stable_sort(sy, system_amount_col, system_date_col)

    matched_pairs: list[tuple[int, int]] = []
    all_dates = sorted(
        set(ld[ledger_date_col].map(_date_key).dropna().tolist())
        & set(sy[system_date_col].map(_date_key).dropna().tolist())
    )
    for date_key in all_dates:
        lsub = ld[ld[ledger_date_col].map(_date_key) == date_key].copy()
        ssub = sy[sy[system_date_col].map(_date_key) == date_key].copy()
        lsub[ledger_amount_col] = pd.to_numeric(lsub[ledger_amount_col], errors="coerce")
        ssub[system_amount_col] = pd.to_numeric(ssub[system_amount_col], errors="coerce")
        lsub = lsub[lsub[ledger_amount_col].notna()].sort_values(
            [ledger_amount_col, "_orig_idx"], kind="mergesort"
        )
        ssub = ssub[ssub[system_amount_col].notna()].sort_values(
            [system_amount_col, "_orig_idx"], kind="mergesort"
        )
        li = lsub[["_lid", ledger_amount_col]].values.tolist()
        si = ssub[["_sid", system_amount_col]].values.tolist()
        i = 0
        j = 0
        while i < len(li) and j < len(si):
            lid, lam_raw = li[i]
            sid, sam_raw = si[j]
            lam = float(lam_raw)
            sam = float(sam_raw)
            diff = lam - sam
            if abs(diff) <= (amount_tolerance + _FLOAT_EPS):
                matched_pairs.append((int(lid), int(sid)))
                i += 1
                j += 1
            elif diff < -(amount_tolerance + _FLOAT_EPS):
                i += 1
            else:
                j += 1

    matched_lids = {p[0] for p in matched_pairs}
    matched_sids = {p[1] for p in matched_pairs}

    unmatched_ld = ld[~ld["_lid"].isin(matched_lids)].drop(
        columns=["_lid", "_orig_idx"],
        errors="ignore",
    )
    unmatched_sy = sy[~sy["_sid"].isin(matched_sids)].drop(
        columns=["_sid", "_orig_idx"],
        errors="ignore",
    )

    matched_rows: list[dict[str, Any]] = []
    ld_by_id = ld.set_index("_lid")
    sy_by_id = sy.set_index("_sid")
    for lid, sid in matched_pairs:
        lr = ld_by_id.loc[lid]
        sr = sy_by_id.loc[sid]
        row: dict[str, Any] = {}
        for c in ld.columns:
            if c in ("_lid", "_orig_idx"):
                continue
            row[f"{ledger_prefix}_{c}"] = lr[c]
        for c in sy.columns:
            if c in ("_sid", "_orig_idx"):
                continue
            row[f"{system_prefix}_{c}"] = sr[c]
        lam = float(lr[ledger_amount_col])
        sam = float(sr[system_amount_col])
        row["Difference"] = lam - sam
        matched_rows.append(row)

    matched_df = pd.DataFrame(matched_rows)
    logger.info(
        "Match summary: matched=%s unmatched_ledger=%s unmatched_system=%s",
        len(matched_df),
        len(unmatched_ld),
        len(unmatched_sy),
    )
    return matched_df, unmatched_ld, unmatched_sy


def _round_amount(value: Any) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


def match_amount_only_one_to_one(
    ledger_df: pd.DataFrame,
    system_df: pd.DataFrame,
    *,
    ledger_amount_col: str = "_match_amount",
    system_amount_col: str = "_match_amount",
    ledger_prefix: str = "Ledger",
    system_prefix: str = "System",
    amount_tolerance: float = 0.0,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Pair rows where ledger amount equals system amount (ignoring dates),
    consuming each row at most once within each amount bucket.
    """
    if ledger_amount_col not in ledger_df.columns:
        raise KeyError(f"Ledger missing {ledger_amount_col}")
    if system_amount_col not in system_df.columns:
        raise KeyError(f"System missing {system_amount_col}")
    if amount_tolerance < 0:
        raise ValueError("amount_tolerance must be >= 0")

    ld = ledger_df.copy()
    sy = system_df.copy()
    ld["_lid"] = range(len(ld))
    sy["_sid"] = range(len(sy))
    ld["_orig_idx"] = range(len(ld))
    sy["_orig_idx"] = range(len(sy))
    ld["_amt_key"] = ld[ledger_amount_col].map(_round_amount)
    sy["_amt_key"] = sy[system_amount_col].map(_round_amount)

    matched_pairs: list[tuple[int, int]] = []
    ledger_valid = ld[ld["_amt_key"].notna()].sort_values(["_amt_key", "_orig_idx"], kind="mergesort")
    system_valid = sy[sy["_amt_key"].notna()].sort_values(["_amt_key", "_orig_idx"], kind="mergesort")

    for amt_key, lsub in ledger_valid.groupby("_amt_key", sort=False):
        ssub = system_valid[system_valid["_amt_key"] == amt_key].copy()
        if ssub.empty:
            continue
        li = lsub[["_lid", ledger_amount_col]].values.tolist()
        si = ssub[["_sid", system_amount_col]].values.tolist()
        i = 0
        j = 0
        while i < len(li) and j < len(si):
            lid, lam_raw = li[i]
            sid, sam_raw = si[j]
            lam = float(lam_raw)
            sam = float(sam_raw)
            diff = lam - sam
            if abs(diff) <= (amount_tolerance + _FLOAT_EPS):
                matched_pairs.append((int(lid), int(sid)))
                i += 1
                j += 1
            elif diff < -(amount_tolerance + _FLOAT_EPS):
                i += 1
            else:
                j += 1

    matched_lids = {p[0] for p in matched_pairs}
    matched_sids = {p[1] for p in matched_pairs}
    unmatched_ld = ld[~ld["_lid"].isin(matched_lids)].drop(
        columns=["_lid", "_orig_idx", "_amt_key"],
        errors="ignore",
    )
    unmatched_sy = sy[~sy["_sid"].isin(matched_sids)].drop(
        columns=["_sid", "_orig_idx", "_amt_key"],
        errors="ignore",
    )

    matched_rows: list[dict[str, Any]] = []
    ld_by_id = ld.set_index("_lid")
    sy_by_id = sy.set_index("_sid")
    for lid, sid in matched_pairs:
        lr = ld_by_id.loc[lid]
        sr = sy_by_id.loc[sid]
        row: dict[str, Any] = {}
        for c in ld.columns:
            if c in ("_lid", "_orig_idx", "_amt_key"):
                continue
            row[f"{ledger_prefix}_{c}"] = lr[c]
        for c in sy.columns:
            if c in ("_sid", "_orig_idx", "_amt_key"):
                continue
            row[f"{system_prefix}_{c}"] = sr[c]
        lam = float(lr[ledger_amount_col])
        sam = float(sr[system_amount_col])
        row["Difference"] = lam - sam
        matched_rows.append(row)

    matched_df = pd.DataFrame(matched_rows)
    logger.info(
        "Amount-only match summary: matched=%s unmatched_ledger=%s unmatched_system=%s",
        len(matched_df),
        len(unmatched_ld),
        len(unmatched_sy),
    )
    return matched_df, unmatched_ld, unmatched_sy

# -*- coding: utf-8 -*-
"""
Diagnose 469 unmatched rows: amount-only vs date mismatch vs duplicate keys.

Usage (you are usually already in reconciliation_engine):

  py -3 scripts/diagnose_469_unmatched.py

Optional explicit paths:

  py -3 scripts/diagnose_469_unmatched.py ^
    --ledger "D:\path\mayorpc 469.txt" ^
    --famafa "D:\path\FAMAFA COMPRAS 469.xlsx"

Large FAMAFA files (~60k+ rows) can take 1-3 minutes to load; progress is printed.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))

import pandas as pd  # noqa: E402

from ingestion.ledger_parser import parse_ledger  # noqa: E402
from ingestion.system_imports import load_famafa_excel  # noqa: E402
from reconcile.matcher import match_exact_one_to_one  # noqa: E402
from rules.account_rules import add_ledger_match_amount, filter_famafa_469  # noqa: E402


def _round_amt(x) -> float:
    return round(float(x), 2)


def _insumos_root() -> Path:
    hits = list(_ROOT.parent.glob("Automatiz*conciliaciones"))
    if not hits:
        raise FileNotFoundError(
            "No 'Automatiz*conciliaciones' folder next to reconciliation_engine. "
            "Use --ledger and --famafa to point at your files."
        )
    return hits[0]


def _default_469_paths() -> tuple[Path, Path]:
    folder = next(p for p in _insumos_root().iterdir() if p.is_dir() and "469" in p.name)
    return folder / "mayorpc 469.txt", folder / "FAMAFA COMPRAS 469.xlsx"


def _dates_by_amount(df: pd.DataFrame) -> dict[float, set[pd.Timestamp]]:
    out: dict[float, set[pd.Timestamp]] = defaultdict(set)
    for amt, dt in zip(df["_match_amount"], df["_match_date"]):
        if pd.isna(amt) or pd.isna(dt):
            continue
        out[_round_amt(amt)].add(dt)
    return out


def _count_date_mismatch(
    df: pd.DataFrame,
    other_dates: dict[float, set[pd.Timestamp]],
    other_amts: Counter,
) -> int:
    n = 0
    for amt, dt in zip(df["_match_amount"], df["_match_date"]):
        if pd.isna(amt) or pd.isna(dt):
            continue
        a = _round_amt(amt)
        if a not in other_amts:
            continue
        if dt not in other_dates.get(a, ()):
            n += 1
    return n


def run_diagnosis(ledger_path: Path, famafa_path: Path) -> None:
    print(f"Ledger: {ledger_path}")
    print(f"FAMAFA: {famafa_path}")
    print("Parsing ledger...")
    ledger = parse_ledger(ledger_path, account_num="469")
    print(f"  {len(ledger)} rows")

    print("Loading FAMAFA Excel (large files may take 1-3 minutes)...")
    fam = load_famafa_excel(famafa_path)
    print(f"  {len(fam)} raw rows; applying 469 filters...")
    sys_df = filter_famafa_469(fam)
    print(f"  {len(sys_df)} rows after rules")

    leg = add_ledger_match_amount(ledger, "Debito")
    leg["_match_date"] = pd.to_datetime(leg["Fecha"], errors="coerce").dt.normalize()

    print("Matching (amount + date, 1:1)...")
    matched, u_leg, u_sys = match_exact_one_to_one(leg, sys_df)

    leg_amts = Counter(_round_amt(x) for x in u_leg["_match_amount"] if pd.notna(x))
    sys_amts = Counter(_round_amt(x) for x in u_sys["_match_amount"] if pd.notna(x))
    common_amts = set(leg_amts) & set(sys_amts)

    amt_only_pairs = sum(min(leg_amts[a], sys_amts[a]) for a in common_amts)
    amt_only_leg = sum(leg_amts[a] for a in common_amts)
    amt_only_sys = sum(sys_amts[a] for a in common_amts)

    leg_keys = Counter(
        (_round_amt(r["_match_amount"]), r["_match_date"])
        for _, r in u_leg.iterrows()
        if pd.notna(r["_match_amount"]) and pd.notna(r["_match_date"])
    )
    sys_keys = Counter(
        (_round_amt(r["_match_amount"]), r["_match_date"])
        for _, r in u_sys.iterrows()
        if pd.notna(r["_match_amount"]) and pd.notna(r["_match_date"])
    )
    shared_keys = set(leg_keys) & set(sys_keys)
    key_leftover_leg = sum(min(leg_keys[k], sys_keys[k]) for k in shared_keys)
    multi_key_count = sum(1 for k in shared_keys if leg_keys[k] > 1 or sys_keys[k] > 1)

    print("Analyzing date mismatches...")
    sys_dates_by_amt = _dates_by_amount(u_sys)
    leg_dates_by_amt = _dates_by_amount(u_leg)
    dm_leg = _count_date_mismatch(u_leg, sys_dates_by_amt, sys_amts)
    dm_sys = _count_date_mismatch(u_sys, leg_dates_by_amt, leg_amts)

    leg_set = set(_round_amt(x) for x in u_leg["_match_amount"] if pd.notna(x))
    near_sys = sum(
        1
        for _, r in u_sys.iterrows()
        if (_round_amt(r["_match_amount"]) - 1) in leg_set or (_round_amt(r["_match_amount"]) + 1) in leg_set
    )

    leg_only_rows = sum(leg_amts[a] for a in leg_amts if a not in sys_amts)
    sys_only_rows = sum(sys_amts[a] for a in sys_amts if a not in leg_amts)

    print()
    print("=== 469 unmatched diagnostics ===")
    print(f"matched={len(matched)} unmatched_ledger={len(u_leg)} unmatched_system={len(u_sys)}")
    print()
    print(f"Amount exists on BOTH sides (any date): {len(common_amts)} distinct amounts")
    print(f"  ledger rows: {amt_only_leg}  system rows: {amt_only_sys}  (pairable by amount only: {amt_only_pairs})")
    print(f"Same amount but date NOT on other side: ledger={dm_leg}  system={dm_sys}")
    print(f"Same (amount, date) key still unmatched (1:1 leftovers): ledger~={key_leftover_leg}  keys with duplicates: {multi_key_count}")
    print(f"System rows with ledger amount +/-1: {near_sys}")
    print(f"Ledger rows with no system amount match: {leg_only_rows}")
    print(f"System rows with no ledger amount match: {sys_only_rows}")
    print()
    print("Top amount overlaps (amount, ledger_n, system_n):")
    top = sorted(
        ((a, leg_amts[a], sys_amts[a]) for a in common_amts),
        key=lambda t: min(t[1], t[2]),
        reverse=True,
    )[:10]
    for row in top:
        print(f"  {row}")
    print()
    print("Interpretation: if 'date NOT on other side' is high, mayor Fecha vs FAMAFA Fecha Emision is the bottleneck.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Diagnose 469 unmatched reconciliation rows.")
    parser.add_argument("--ledger", type=Path, help="Path to mayorpc 469.txt")
    parser.add_argument("--famafa", type=Path, help="Path to FAMAFA COMPRAS 469.xlsx")
    args = parser.parse_args()

    if args.ledger and args.famafa:
        ledger_path, famafa_path = args.ledger, args.famafa
    elif args.ledger or args.famafa:
        parser.error("Provide both --ledger and --famafa, or neither to use the sample folder.")
    else:
        ledger_path, famafa_path = _default_469_paths()

    if not ledger_path.is_file():
        raise FileNotFoundError(f"Ledger not found: {ledger_path}")
    if not famafa_path.is_file():
        raise FileNotFoundError(f"FAMAFA not found: {famafa_path}")

    run_diagnosis(ledger_path.resolve(), famafa_path.resolve())


if __name__ == "__main__":
    main()

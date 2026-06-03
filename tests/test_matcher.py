"""Tests for 1-to-1 matcher (amount + date)."""

import pandas as pd

from reconcile.matcher import match_exact_one_to_one


def _d(s: str) -> pd.Timestamp:
    return pd.Timestamp(s)


def test_one_to_one_duplicate_amounts():
    d = _d("2026-04-01")
    ledger = pd.DataFrame(
        {
            "Debito": [500.0, 500.0, 500.0],
            "x": [1, 2, 3],
            "_match_amount": [500.0, 500.0, 500.0],
            "_match_date": [d, d, d],
        }
    )
    system = pd.DataFrame(
        {
            "IVA": [500.0, 500.0],
            "y": ["a", "b"],
            "_match_amount": [500.0, 500.0],
            "_match_date": [d, d],
        }
    )
    matched, u_leg, u_sys = match_exact_one_to_one(ledger, system)
    assert len(matched) == 2
    assert len(u_leg) == 1
    assert len(u_sys) == 0


def test_no_overlap():
    d = _d("2026-04-01")
    ledger = pd.DataFrame({"_match_amount": [1.0, 2.0], "_match_date": [d, d]})
    system = pd.DataFrame({"_match_amount": [3.0, 4.0], "_match_date": [d, d]})
    matched, u_leg, u_sys = match_exact_one_to_one(ledger, system)
    assert matched.empty
    assert len(u_leg) == 2
    assert len(u_sys) == 2


def test_same_amount_different_date_no_match():
    ledger = pd.DataFrame(
        {"_match_amount": [100.0], "_match_date": [_d("2026-04-01")]}
    )
    system = pd.DataFrame(
        {"_match_amount": [100.0], "_match_date": [_d("2026-04-15")]}
    )
    matched, u_leg, u_sys = match_exact_one_to_one(ledger, system)
    assert matched.empty
    assert len(u_leg) == 1
    assert len(u_sys) == 1


def test_single_pair_match():
    d = _d("2026-04-01")
    ledger = pd.DataFrame({"_match_amount": [250.5], "_match_date": [d], "k": [1]})
    system = pd.DataFrame({"_match_amount": [250.5], "_match_date": [d], "z": [9]})
    matched, u_leg, u_sys = match_exact_one_to_one(ledger, system)
    assert len(matched) == 1
    assert matched.iloc[0]["Difference"] == 0.0
    assert u_leg.empty and u_sys.empty


def test_amount_tolerance_allows_small_difference():
    d = _d("2026-04-30")
    ledger = pd.DataFrame({"_match_amount": [100.00], "_match_date": [d]})
    system = pd.DataFrame({"_match_amount": [100.01], "_match_date": [d]})
    matched, u_leg, u_sys = match_exact_one_to_one(
        ledger,
        system,
        amount_tolerance=0.01,
    )
    assert len(matched) == 1
    assert len(u_leg) == 0
    assert len(u_sys) == 0


def test_amount_tolerance_still_requires_same_date():
    ledger = pd.DataFrame({"_match_amount": [100.00], "_match_date": [_d("2026-04-01")]})
    system = pd.DataFrame({"_match_amount": [100.01], "_match_date": [_d("2026-04-02")]})
    matched, u_leg, u_sys = match_exact_one_to_one(
        ledger,
        system,
        amount_tolerance=0.01,
    )
    assert matched.empty
    assert len(u_leg) == 1
    assert len(u_sys) == 1


def test_amount_tolerance_negative_rejected():
    d = _d("2026-04-01")
    ledger = pd.DataFrame({"_match_amount": [1.0], "_match_date": [d]})
    system = pd.DataFrame({"_match_amount": [1.0], "_match_date": [d]})
    try:
        match_exact_one_to_one(ledger, system, amount_tolerance=-0.01)
        assert False, "Expected ValueError for negative tolerance"
    except ValueError:
        assert True

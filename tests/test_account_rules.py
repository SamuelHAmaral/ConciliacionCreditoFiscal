"""Tests for account rules."""

from pathlib import Path

import pandas as pd

from ingestion.system_imports import load_famafa_csv, load_sql_extract
from rules.account_rules import (
    add_ledger_match_amount,
    filter_famafa_1280,
    filter_famafa_2874,
    filter_famafa_469,
    filter_sql_account_1279,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_filter_sql_1279_date_window():
    df = load_sql_extract(FIXTURES / "minimal_sql.csv")
    out = filter_sql_account_1279(
        df,
        fecha_desde=pd.Timestamp("2026-04-01"),
        fecha_hasta=pd.Timestamp("2026-04-30"),
    )
    assert len(out) == 3
    assert set(out["_match_amount"].tolist()) == {1000.0, 500.0, 200.0}
    assert "_match_date" in out.columns
    assert out["_match_date"].notna().all()


def test_filter_famafa_469():
    df = load_famafa_csv(FIXTURES / "minimal_famafa_compras.csv")
    out = filter_famafa_469(df)
    assert len(out) == 1
    assert out.iloc[0]["_match_amount"] == 100.0
    assert "_match_date" in out.columns


def test_filter_famafa_1280_timbrado():
    df = load_famafa_csv(FIXTURES / "minimal_famafa_compras.csv")
    out = filter_famafa_1280(df)
    assert len(out) == 1
    assert out.iloc[0]["_match_amount"] == 50.0
    assert "_match_date" in out.columns


def test_filter_famafa_2874():
    df = load_famafa_csv(FIXTURES / "minimal_famafa_ventas.csv")
    out = filter_famafa_2874(df)
    assert len(out) == 1
    assert out.iloc[0]["_match_amount"] == 300.0
    assert "_match_date" in out.columns


def test_normalize_timbrado_string_and_numeric():
    from rules.account_rules import normalize_timbrado

    assert normalize_timbrado("12345678") == "12345678"
    assert normalize_timbrado(12345678) == "12345678"
    assert normalize_timbrado(12345678.0) == "12345678"


def test_add_ledger_match_amount():
    ledger = pd.DataFrame(
        {
            "Debito": [100.0, None],
            "Credito": [None, 200.0],
        }
    )
    d = add_ledger_match_amount(ledger, "Debito")
    assert len(d) == 1
    c = add_ledger_match_amount(ledger, "Credito")
    assert len(c) == 1

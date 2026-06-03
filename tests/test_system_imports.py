"""Tests for European decimal parsing."""

import pandas as pd
import pytest

from ingestion.system_imports import (
    load_system_file,
    parse_european_decimal,
    parse_sql_compact_fecha,
    to_datetime_series,
)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("1.090.095,00", 1_090_095.0),
        ("216,00", 216.0),
        ("0,00", 0.0),
    ],
)
def test_parse_european_decimal(raw, expected):
    assert parse_european_decimal(raw) == expected


def test_parse_european_decimal_empty():
    assert pd.isna(parse_european_decimal(""))
    assert pd.isna(parse_european_decimal(None))


def test_to_datetime_series():
    s = pd.Series(["01/04/2026", "15/04/2026"])
    d = to_datetime_series(s)
    assert d.dt.day.iloc[0] == 1


def test_parse_sql_compact_fecha():
    ts = parse_sql_compact_fecha(2942026)
    assert ts == pd.Timestamp("2026-04-29")
    ts2 = parse_sql_compact_fecha(3042026)
    assert ts2 == pd.Timestamp("2026-04-30")


def test_load_system_file_csv(tmp_path):
    p = tmp_path / "t.csv"
    p.write_text("Fecha_Cont,IVA ML\n2026-04-01,10\n", encoding="utf-8")
    df = load_system_file(p, "sql")
    assert len(df) == 1
    assert "IVA ML" in df.columns

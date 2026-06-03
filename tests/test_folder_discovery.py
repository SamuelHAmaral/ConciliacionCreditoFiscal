"""Tests for folder discovery."""

from pathlib import Path

import pytest

from ingestion.folder_discovery import discover_inputs, infer_fecha_range_from_sql

_WS = Path(__file__).resolve().parents[2].parent
_INSUMOS = _WS / "Automatizaci\u00f3n conciliaciones"


@pytest.mark.skipif(not _INSUMOS.is_dir(), reason="Sample insumos folder missing")
def test_discover_sample_folder():
    d = discover_inputs(_INSUMOS)
    assert "1279" in d.ledgers or "469" in d.ledgers
    if d.sql_1279:
        fd, fh = infer_fecha_range_from_sql(d.sql_1279)
        assert fd == fh
        assert fd is not None


def test_infer_fecha_from_sql_name():
    p = Path("SQL - Cuenta1279_2026-04-30.xlsx")
    assert infer_fecha_range_from_sql(p) == ("2026-04-30", "2026-04-30")

"""Tests for system file load cache."""

from pathlib import Path
from unittest.mock import patch

import pandas as pd

from ingestion.system_imports import load_system_file


def test_load_system_file_cache_reuses_parse(tmp_path: Path) -> None:
    path = tmp_path / "famafa.csv"
    path.write_text("Tipo Comprobante,IVA 10,Fecha Emision\n109,100,01/04/2026\n", encoding="utf-8")
    cache: dict = {}
    calls = {"n": 0}
    original = pd.read_csv

    def counting_read_csv(*args, **kwargs):
        calls["n"] += 1
        return original(*args, **kwargs)

    with patch("ingestion.system_imports.pd.read_csv", side_effect=counting_read_csv):
        df1 = load_system_file(path, "famafa", cache=cache)
        df2 = load_system_file(path, "famafa", cache=cache)
    assert len(df1) == 1
    assert len(df2) == 1
    assert calls["n"] == 1

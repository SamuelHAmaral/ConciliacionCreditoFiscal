"""Tests for UAT compare helpers."""

from pathlib import Path

import pandas as pd

from qa.uat_compare import compare_with_golden, write_variance_csv


def test_compare_with_golden_missing_model(tmp_path: Path):
    out = tmp_path / "CUADRE_469_reconciliacion.xlsx"
    pd.DataFrame({"D\u00e9bitos": [100], "IVA 10": [100], "CRUCE": [0]}).to_excel(
        out, sheet_name="469", index=False
    )
    rows = compare_with_golden({"469": out}, models_root=tmp_path / "missing")
    assert len(rows) == 1
    assert rows[0].status == "missing_model"


def test_write_variance_csv(tmp_path: Path):
    out = tmp_path / "CUADRE_469_reconciliacion.xlsx"
    pd.DataFrame({"D\u00e9bitos": [100], "IVA 10": [100], "CRUCE": [0]}).to_excel(
        out, sheet_name="469", index=False
    )
    rows = compare_with_golden({"469": out}, models_root=tmp_path / "missing")
    report = write_variance_csv(rows, tmp_path / "logs" / "variance.csv")
    assert report.exists()

"""Tests for UAT compare helpers."""

from pathlib import Path

import pandas as pd

from qa.uat_compare import (
    compare_with_golden,
    count_engine_output,
    count_model_rows,
    write_variance_csv,
)


def _write_engine_cuadre(path: Path, account: str, *, banner: bool = False) -> None:
    rows: list[list[object]] = []
    if banner:
        rows.extend([["Banner"]] * 4)
    rows.append(
        [
            "Cuenta",
            "Fecha Mayor",
            "Débitos",
            "Fecha Sistema",
            "IVA 10",
            "CRUCE",
        ]
    )
    rows.append([account, "2026-04-30", 100.0, "2026-04-30", 100.0, 0])
    rows.append([account, "2026-04-30", 50.0, None, None, None])
    rows.append([account, None, None, "2026-04-30", 25.0, None])
    pd.DataFrame(rows).to_excel(path, sheet_name=account, index=False, header=False)


def _write_model_cuadre(path: Path, account: str) -> None:
    pd.DataFrame(
        {
            "Cuenta": [account, account],
            "Fecha": ["2026-04-30", "2026-04-30"],
            "Débitos": [100.0, 50.0],
            "Fecha.1": ["2026-04-30", None],
            "IVA 10": [100.0, None],
            "CRUCE": [0, None],
        }
    ).to_excel(path, sheet_name=account, index=False)


def test_compare_with_golden_missing_model(tmp_path: Path):
    out = tmp_path / "CUADRE_469_reconciliacion.xlsx"
    _write_engine_cuadre(out, "469")
    rows = compare_with_golden({"469": out}, models_root=tmp_path / "missing")
    assert len(rows) == 1
    assert rows[0].status == "missing_model"


def test_count_engine_output_with_banner(tmp_path: Path):
    out = tmp_path / "CUADRE_469_reconciliacion.xlsx"
    _write_engine_cuadre(out, "469", banner=True)
    counts = count_engine_output(out, "469")
    assert counts["total"] == 3
    assert counts["matched_cruce_zero"] == 1


def test_compare_with_golden_uses_run_metrics(tmp_path: Path):
    out = tmp_path / "CUADRE_469_reconciliacion.xlsx"
    model_dir = tmp_path / "469"
    model_dir.mkdir()
    model_path = model_dir / "CUADRE 469.xlsx"
    _write_engine_cuadre(out, "469", banner=True)
    _write_model_cuadre(model_path, "469")

    rows = compare_with_golden(
        {"469": out},
        models_root=tmp_path,
        output_metrics={"469": {"matched_rows": 1, "unmatched_ledger_rows": 1, "unmatched_system_rows": 1}},
    )
    assert len(rows) == 1
    assert rows[0].status == "ok"
    assert rows[0].output_matched == 1
    assert rows[0].model_matched == 1


def test_compare_with_golden_detects_variance(tmp_path: Path):
    out = tmp_path / "CUADRE_469_reconciliacion.xlsx"
    model_dir = tmp_path / "469"
    model_dir.mkdir()
    model_path = model_dir / "CUADRE 469.xlsx"
    _write_engine_cuadre(out, "469", banner=True)
    _write_model_cuadre(model_path, "469")

    rows = compare_with_golden(
        {"469": out},
        models_root=tmp_path,
        output_metrics={"469": {"matched_rows": 0, "unmatched_ledger_rows": 2, "unmatched_system_rows": 1}},
    )
    assert rows[0].status == "variance"
    assert rows[0].delta_matched == -1


def test_count_model_rows_side_by_side(tmp_path: Path):
    model_path = tmp_path / "CUADRE 469.xlsx"
    _write_model_cuadre(model_path, "469")
    counts = count_model_rows(model_path, "469")
    assert counts["total"] == 2
    assert counts["matched"] == 1


def test_write_variance_csv(tmp_path: Path):
    out = tmp_path / "CUADRE_469_reconciliacion.xlsx"
    _write_engine_cuadre(out, "469")
    rows = compare_with_golden({"469": out}, models_root=tmp_path / "missing")
    report = write_variance_csv(rows, tmp_path / "logs" / "variance.csv")
    assert report.exists()

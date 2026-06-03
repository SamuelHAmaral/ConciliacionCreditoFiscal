"""Tests for internal integrity checks."""

from __future__ import annotations

from pathlib import Path

import pytest

from qa.integrity_check import (
    ISSUE_EXCEL_ROWS,
    ISSUE_LEDGER_PARTITION,
    ISSUE_SYSTEM_PARTITION,
    check_excel_row_count,
    check_match_partition,
    count_cuadre_data_rows,
    run_integrity_checks,
)


def test_check_match_partition_ok() -> None:
    assert check_match_partition(100, 80, 50, 50, 30) == []


def test_check_match_partition_ledger_mismatch() -> None:
    issues = check_match_partition(100, 80, 50, 40, 30)
    assert ISSUE_LEDGER_PARTITION in issues


def test_check_match_partition_system_mismatch() -> None:
    issues = check_match_partition(100, 80, 50, 50, 20)
    assert ISSUE_SYSTEM_PARTITION in issues


def test_run_integrity_checks_ok() -> None:
    result = run_integrity_checks(
        ledger_rows=10,
        system_rows=8,
        matched=5,
        unmatched_ledger=5,
        unmatched_system=3,
    )
    assert result.ok
    assert result.issues == ()


def test_check_excel_row_count(tmp_path: Path) -> None:
    xlsxwriter = pytest.importorskip("xlsxwriter")
    path = tmp_path / "CUADRE_469_reconciliacion.xlsx"
    book = xlsxwriter.Workbook(str(path))
    ws = book.add_worksheet("469")
    ws.write(4, 0, "Cuenta")
    ws.write(4, 1, "Debitos")
    ws.write(5, 0, "469")
    ws.write(5, 1, 100.0)
    book.close()
    assert count_cuadre_data_rows(path, "469") == 1
    assert check_excel_row_count(path, "469", 1) == []
    assert ISSUE_EXCEL_ROWS in check_excel_row_count(path, "469", 2)

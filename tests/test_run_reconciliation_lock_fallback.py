"""Regression tests for locked-output fallback on Excel write."""

from pathlib import Path

import pandas as pd

from pipeline import run_reconciliation as rr


def test_write_workbook_resilient_uses_timestamp_fallback(monkeypatch):
    calls: list[Path] = []
    events: list[tuple[str, str]] = []

    def fake_writer(
        output_path: str | Path,
        account: str,
        matched: pd.DataFrame,
        unmatched_ledger: pd.DataFrame,
        unmatched_system: pd.DataFrame,
        *,
        ledger_side: str = "Debito",
    ) -> None:
        p = Path(output_path)
        calls.append(p)
        if len(calls) == 1:
            raise PermissionError("[Errno 13] Permission denied")

    monkeypatch.setattr(rr, "write_cuadre_workbook", fake_writer)

    out = Path("C:/tmp/CUADRE_1279_reconciliacion.xlsx")
    got = rr._write_workbook_resilient(
        out,
        account="1279",
        matched=pd.DataFrame(),
        unmatched_ledger=pd.DataFrame(),
        unmatched_system=pd.DataFrame(),
        ledger_side="Debito",
        audit_fn=lambda stage, status="ok", **_: events.append((stage, status)),
    )

    assert len(calls) == 2
    assert calls[0] == out
    assert calls[1] != out
    assert calls[1].suffix.lower() == ".xlsx"
    assert calls[1].name.startswith("CUADRE_1279_reconciliacion_")
    assert got == calls[1]
    assert ("excel_write_locked", "warning") in events
    assert ("excel_write_retry_ok", "ok") in events

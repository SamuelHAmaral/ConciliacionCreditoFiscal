"""Internal integrity checks (row conservation, Excel row count)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

ISSUE_LEDGER_PARTITION = "ledger_partition"
ISSUE_SYSTEM_PARTITION = "system_partition"
ISSUE_EXCEL_ROWS = "excel_rows"


@dataclass(frozen=True)
class IntegrityResult:
    ok: bool
    issues: tuple[str, ...]


def check_match_partition(
    ledger_rows: int,
    system_rows: int,
    matched: int,
    unmatched_ledger: int,
    unmatched_system: int,
) -> list[str]:
    """Acceptance A4: every ledger/system row is matched or pending exactly once."""
    issues: list[str] = []
    if matched + unmatched_ledger != ledger_rows:
        issues.append(ISSUE_LEDGER_PARTITION)
    if matched + unmatched_system != system_rows:
        issues.append(ISSUE_SYSTEM_PARTITION)
    return issues


def count_cuadre_data_rows(path: Path, account: str) -> int:
    """Count data rows on the main CUADRE sheet (below banner + header)."""
    xl = pd.ExcelFile(path)
    sheet = account if account in xl.sheet_names else xl.sheet_names[0]
    df = pd.read_excel(path, sheet_name=sheet, header=4)
    if df.empty:
        return 0
    return int(len(df.dropna(how="all")))


def check_excel_row_count(path: Path, account: str, expected_rows: int) -> list[str]:
    if not path.is_file():
        return [ISSUE_EXCEL_ROWS]
    try:
        actual = count_cuadre_data_rows(path, account)
    except Exception:
        return [ISSUE_EXCEL_ROWS]
    if actual != expected_rows:
        return [ISSUE_EXCEL_ROWS]
    return []


def run_integrity_checks(
    *,
    ledger_rows: int,
    system_rows: int,
    matched: int,
    unmatched_ledger: int,
    unmatched_system: int,
    output_path: Path | None = None,
    account: str = "",
) -> IntegrityResult:
    issues = check_match_partition(
        ledger_rows,
        system_rows,
        matched,
        unmatched_ledger,
        unmatched_system,
    )
    expected = matched + unmatched_ledger + unmatched_system
    if output_path is not None and account:
        issues.extend(check_excel_row_count(output_path, account, expected))
    return IntegrityResult(ok=not issues, issues=tuple(issues))

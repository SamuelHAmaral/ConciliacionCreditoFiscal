"""Write reconciliation workbooks (Matched + two exception sheets)."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
import xlsxwriter
from xlsxwriter.utility import xl_col_to_name

logger = logging.getLogger(__name__)


def _find_amount_col_indices(columns: list[str]) -> tuple[int | None, int | None]:
    """Return (ledger_amount_idx, system_amount_idx) for _match_amount columns."""
    leg_i: int | None = None
    sys_i: int | None = None
    for i, c in enumerate(columns):
        if c == "Ledger__match_amount" or (c.startswith("Ledger_") and c.endswith("_match_amount")):
            leg_i = i
        if c == "System__match_amount" or (c.startswith("System_") and c.endswith("_match_amount")):
            sys_i = i
    return leg_i, sys_i


def write_reconciliation_workbook(
    output_path: str | Path,
    matched: pd.DataFrame,
    unmatched_ledger: pd.DataFrame,
    unmatched_system: pd.DataFrame,
    *,
    account_label: str = "",
) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(path, engine="xlsxwriter") as writer:
        book = writer.book
        assert isinstance(book, xlsxwriter.Workbook)
        fmt_header = book.add_format({"bold": True, "bg_color": "#D9E1F2", "border": 1})
        fmt_num = book.add_format({"num_format": "#,##0.00", "border": 1})
        fmt_text = book.add_format({"border": 1})

        def write_sheet(
            sheet_name: str,
            df: pd.DataFrame,
            *,
            with_difference_formula: bool = False,
        ) -> None:
            safe = sheet_name[:31]
            out_df = df.copy()
            if out_df.empty:
                note = f"(no rows) {account_label}".strip()
                out_df = pd.DataFrame({"Note": [note or "(no rows)"]})
                with_difference_formula = False

            ws = book.add_worksheet(safe)
            writer.sheets[safe] = ws

            cols = [c for c in out_df.columns if c != "Difference"] if with_difference_formula else list(
                out_df.columns
            )
            leg_amt_i, sys_amt_i = (
                _find_amount_col_indices(cols) if with_difference_formula else (None, None)
            )
            add_diff = bool(
                with_difference_formula and leg_amt_i is not None and sys_amt_i is not None and len(cols) > 0
            )

            header_count = len(cols) + (1 if add_diff else 0)
            for c in range(len(cols)):
                ws.write(0, c, cols[c], fmt_header)
            if add_diff:
                ws.write(0, len(cols), "Diferencia", fmt_header)

            for r in range(len(out_df)):
                for c, col in enumerate(cols):
                    val = out_df.iloc[r][col]
                    is_num = pd.api.types.is_numeric_dtype(out_df[col])
                    fmt = fmt_num if is_num else fmt_text
                    if pd.isna(val):
                        ws.write(r + 1, c, "", fmt_text)
                    else:
                        ws.write(r + 1, c, val, fmt)
                if add_diff and leg_amt_i is not None and sys_amt_i is not None:
                    excel_row = r + 2
                    col_leg = xl_col_to_name(leg_amt_i)
                    col_sys = xl_col_to_name(sys_amt_i)
                    formula = f"={col_leg}{excel_row}-{col_sys}{excel_row}"
                    ws.write_formula(r + 1, len(cols), formula, fmt_num)

            for c in range(header_count):
                if c < len(cols):
                    col_name = cols[c]
                    series = out_df[col_name].astype(str)
                    maxlen = int(series.map(len).max()) if len(series) else 10
                    maxlen = max(maxlen, len(str(col_name))) + 2
                    is_num = pd.api.types.is_numeric_dtype(out_df[col_name])
                else:
                    maxlen = 14
                    is_num = True
                col_fmt = fmt_num if is_num else fmt_text
                ws.set_column(c, c, min(maxlen, 55), col_fmt)

        write_sheet("Partidas Conciliadas", matched.copy(), with_difference_formula=True)
        write_sheet("Pendientes en Mayor", unmatched_ledger)
        write_sheet("Pendientes en Sistema", unmatched_system)

    logger.info("Wrote workbook %s", path)

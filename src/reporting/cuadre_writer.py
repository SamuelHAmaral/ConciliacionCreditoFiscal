"""Write CUADRE-style reconciliation workbooks (side-by-side layout)."""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any
from uuid import uuid4

import pandas as pd
import xlsxwriter
from output_es.messages import (
    CUADRE_TOTAL_AMOUNT_MATCHED,
    CUADRE_TOTAL_PENDING,
    CUADRE_TOTAL_RECORDS_MATCHED,
    cuadre_banner_title,
)
from xlsxwriter.utility import xl_col_to_name

logger = logging.getLogger(__name__)

# Display headers (Unicode escapes for stable source encoding)
_HDR_DESCRIPCION = "Descripci\u00f3n"
_HDR_DEBITOS = "D\u00e9bitos"
_HDR_CREDITOS = "Cr\u00e9ditos"
_HDR_RAZON = "Raz\u00f3n Social"

_LEDGER_FIELDS: list[tuple[str, str]] = [
    ("Cuenta", "Cuenta"),
    ("Fecha", "Fecha Mayor"),
    ("Ag", "Ag"),
    ("Asiento", "Asiento"),
    ("Descripcion", _HDR_DESCRIPCION),
    ("Debito", _HDR_DEBITOS),
    ("Credito", _HDR_CREDITOS),
]

_SYSTEM_1279: list[tuple[str, tuple[str, ...]]] = [
    ("Nro. de Documento", ("Nro. de Documento", "Nro de Documento", "Nro Documento")),
    ("Nombre", ("Nombre",)),
    ("Num_Factura", ("Num_Factura", "Num Factura", "Nro Factura")),
    ("Imponible ML sin IVA", ("Imponible ML sin IVA", "Imponible ML sin iva")),
    ("IVA ML", ("IVA ML", "Iva ML")),
    ("Fecha_sistema", ("Fecha_Cont", "Fecha Cont", "fecha_cont")),
]

_SYSTEM_FAMAFA: list[tuple[str, tuple[str, ...]]] = [
    ("Nro. Identific.", ("Nro. Identific.", "Nro Identific")),
    (_HDR_RAZON, (_HDR_RAZON, "Razon Social")),
    ("Fecha_sistema", ("Fecha Comprobante", "Fecha comprobante", "Fecha Emision", "Fecha de emision", "Fecha")),
    ("Nro. Comprobante", ("Nro. Comprobante", "Nro Comprobante")),
    ("Imponible 10", ("Imponible 10", "Imponible10", "Grav. 10 IVA")),
    ("IVA 10", ("IVA 10", "Iva 10", "IVA10")),
]

_HEADER_DISPLAY: dict[str, str] = {
    "Fecha_sistema": "Fecha Sistema",
    "_spacer": "",
}

_DATE_DISPLAY_COLUMNS = {
    "Fecha Mayor",
    "Fecha Sistema",
    "Fecha_Cont",
    "Fecha Emision",
    "Fecha Comprobante",
}


def _norm_key(name: str) -> str:
    return re.sub(r"\s+", " ", str(name).strip().lower())


def _pick_value(row: pd.Series, candidates: tuple[str, ...], *, prefix: str = "") -> Any:
    index_map = {_norm_key(c): c for c in row.index}
    for cand in candidates:
        keys = [cand]
        if prefix:
            keys.insert(0, f"{prefix}{cand}")
        for k in keys:
            nk = _norm_key(k)
            if nk in index_map:
                val = row[index_map[nk]]
                if pd.notna(val):
                    return val
    for cand in candidates:
        nk = _norm_key(cand)
        if nk in index_map:
            return row[index_map[nk]]
    return None


def _ledger_part(row: pd.Series, *, prefix: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}
    for src, label in _LEDGER_FIELDS:
        out[label] = _pick_value(row, (src,), prefix=prefix)
    out["_spacer"] = None
    out["GS."] = "GS."
    return out


def _system_part(row: pd.Series, account: str, *, prefix: str = "") -> dict[str, Any]:
    spec = _SYSTEM_1279 if account == "1279" else _SYSTEM_FAMAFA
    out: dict[str, Any] = {}
    for label, candidates in spec:
        out[label] = _pick_value(row, candidates, prefix=prefix)
    return out


def _layout_for_account(account: str, ledger_side: str) -> tuple[list[str], str, str]:
    ledger_headers = [lbl for _, lbl in _LEDGER_FIELDS] + ["_spacer", "GS."]
    if account == "1279":
        system_headers = [lbl for lbl, _ in _SYSTEM_1279]
        amount_ledger = _HDR_DEBITOS
        amount_system = "IVA ML"
    else:
        system_headers = [lbl for lbl, _ in _SYSTEM_FAMAFA]
        amount_ledger = _HDR_CREDITOS if account == "2874" else _HDR_DEBITOS
        amount_system = "IVA 10"
    headers = ledger_headers + system_headers + ["CRUCE"]
    return headers, amount_ledger, amount_system


def _row_from_matched(row: pd.Series, account: str) -> dict[str, Any]:
    combined: dict[str, Any] = {}
    combined.update(_ledger_part(row, prefix="Ledger_"))
    combined.update(_system_part(row, account, prefix="System_"))
    combined["CRUCE"] = None
    return combined


def _row_from_ledger(row: pd.Series, account: str) -> dict[str, Any]:
    combined: dict[str, Any] = {}
    combined.update(_ledger_part(row))
    for label, _ in (_SYSTEM_1279 if account == "1279" else _SYSTEM_FAMAFA):
        combined[label] = None
    combined["CRUCE"] = None
    return combined


def _row_from_system(row: pd.Series, account: str) -> dict[str, Any]:
    combined: dict[str, Any] = {}
    for _, lbl in _LEDGER_FIELDS:
        combined[lbl] = None
    combined["_spacer"] = None
    combined["GS."] = None
    combined.update(_system_part(row, account))
    combined["CRUCE"] = None
    return combined


def _sort_key_amount(row: dict[str, Any], amount_col: str) -> float:
    v = row.get(amount_col)
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return float("inf")
    try:
        return float(v)
    except (TypeError, ValueError):
        return float("inf")


def _summary_metrics(
    matched: pd.DataFrame,
    unmatched_ledger: pd.DataFrame,
    unmatched_system: pd.DataFrame,
    amount_col: str,
) -> tuple[int, float, int]:
    matched_rows = len(matched)
    pending_rows = len(unmatched_ledger) + len(unmatched_system)
    total_amount = 0.0
    if not matched.empty and amount_col in matched.columns:
        total_amount = float(pd.to_numeric(matched[amount_col], errors="coerce").fillna(0.0).sum())
    return matched_rows, total_amount, pending_rows


def _format_excel_date_text(value: Any) -> str:
    """Return date as DD/MM/YYYY text or empty string."""
    if value is None or (not isinstance(value, pd.Series) and pd.isna(value)):
        return ""
    dt = pd.to_datetime(value, errors="coerce", dayfirst=True)
    if pd.isna(dt):
        return ""
    return dt.strftime("%d/%m/%Y")


def build_cuadre_dataframe(
    account: str,
    matched: pd.DataFrame,
    unmatched_ledger: pd.DataFrame,
    unmatched_system: pd.DataFrame,
    *,
    ledger_side: str,
) -> tuple[pd.DataFrame, pd.DataFrame | None]:
    """Build main CUADRE rows and optional 1279 system-only sheet."""
    headers, amount_ledger, _ = _layout_for_account(account, ledger_side)

    matched_rows: list[dict[str, Any]] = []
    if not matched.empty:
        for _, r in matched.iterrows():
            matched_rows.append(_row_from_matched(r, account))
        matched_rows.sort(key=lambda r: _sort_key_amount(r, amount_ledger))

    ledger_rows = [_row_from_ledger(r, account) for _, r in unmatched_ledger.iterrows()]
    system_rows = [_row_from_system(r, account) for _, r in unmatched_system.iterrows()]

    all_rows = matched_rows + ledger_rows + system_rows
    main_df = pd.DataFrame(all_rows, columns=headers) if all_rows else pd.DataFrame(columns=headers)

    hoja1: pd.DataFrame | None = None
    if account == "1279" and system_rows:
        sys_headers = [lbl for lbl, _ in _SYSTEM_1279]
        hoja1 = pd.DataFrame(
            [{k: r.get(k) for k in sys_headers} for r in system_rows],
            columns=sys_headers,
        )

    return main_df, hoja1


def _publish_atomic(temp_path: Path, final_path: Path) -> None:
    """Atomically replace final_path with completed temp file (same directory)."""
    os.replace(temp_path, final_path)


def _temp_workbook_path(final_path: Path) -> Path:
    return final_path.with_name(f".{final_path.name}.{os.getpid()}.{uuid4().hex}.part")


def write_cuadre_workbook(
    output_path: str | Path,
    account: str,
    matched: pd.DataFrame,
    unmatched_ledger: pd.DataFrame,
    unmatched_system: pd.DataFrame,
    *,
    ledger_side: str = "Debito",
) -> None:
    final_path = Path(output_path)
    final_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = _temp_workbook_path(final_path)

    main_df, hoja1 = build_cuadre_dataframe(
        account,
        matched,
        unmatched_ledger,
        unmatched_system,
        ledger_side=ledger_side,
    )
    headers, amount_ledger, amount_system = _layout_for_account(account, ledger_side)
    sheet_name = account[:31]

    try:
        with pd.ExcelWriter(temp_path, engine="xlsxwriter") as writer:
            book = writer.book
            assert isinstance(book, xlsxwriter.Workbook)
            fmt_header = book.add_format({"bold": True, "bg_color": "#D9E1F2", "border": 1})
            fmt_num = book.add_format({"num_format": "#,##0.00", "border": 1})
            fmt_text = book.add_format({"border": 1})
            fmt_banner_title = book.add_format({"bold": True, "bg_color": "#BDD7EE", "border": 1})
            fmt_banner_label = book.add_format({"bold": True, "bg_color": "#E2EFDA", "border": 1})
            fmt_banner_value = book.add_format({"bg_color": "#E2EFDA", "border": 1, "num_format": "#,##0.00"})
            fmt_cruce_ok = book.add_format({"num_format": "#,##0.00", "bg_color": "#E2F0D9", "border": 1})
            fmt_cruce_warn = book.add_format({"num_format": "#,##0.00", "bg_color": "#FCE4D6", "border": 1})

            matched_rows, matched_amount, pending_rows = _summary_metrics(
                matched,
                unmatched_ledger,
                unmatched_system,
                "Ledger_Credito" if account == "2874" else "Ledger_Debito",
            )

            def write_cuadre_sheet(
                ws_name: str,
                df: pd.DataFrame,
                *,
                with_cruce: bool,
                sheet_headers: list[str] | None = None,
            ) -> None:
                safe = ws_name[:31]
                ws = book.add_worksheet(safe)
                writer.sheets[safe] = ws

                cols = sheet_headers if sheet_headers is not None else headers
                leg_i = cols.index(amount_ledger) if amount_ledger in cols else None
                sys_i = cols.index(amount_system) if amount_system in cols else None
                cruce_i = cols.index("CRUCE") if "CRUCE" in cols else None
                start_header_row = 0
                data_start_row = 1
                if with_cruce:
                    start_header_row = 4
                    data_start_row = start_header_row + 1
                    last_col = len(cols) - 1
                    ws.merge_range(
                        0, 0, 0, last_col, cuadre_banner_title(account), fmt_banner_title
                    )
                    ws.write(1, 0, CUADRE_TOTAL_RECORDS_MATCHED, fmt_banner_label)
                    ws.write(1, 1, matched_rows, fmt_banner_value)
                    ws.write(2, 0, CUADRE_TOTAL_AMOUNT_MATCHED, fmt_banner_label)
                    ws.write(2, 1, matched_amount, fmt_banner_value)
                    ws.write(3, 0, CUADRE_TOTAL_PENDING, fmt_banner_label)
                    ws.write(3, 1, pending_rows, fmt_banner_value)
                for c, h in enumerate(cols):
                    label = _HEADER_DISPLAY.get(h, h)
                    ws.write(start_header_row, c, label, fmt_header)

                numeric_cols = {amount_ledger, amount_system, "Imponible 10", "Imponible ML sin IVA"}
                for r in range(len(df)):
                    for c, col in enumerate(cols):
                        if col == "CRUCE":
                            continue
                        val = df.at[r, col] if col in df.columns else None
                        is_date_col = col in _DATE_DISPLAY_COLUMNS or col == "Fecha_sistema"
                        is_num = col in numeric_cols
                        fmt = fmt_num if is_num and val is not None and not pd.isna(val) else fmt_text
                        if val is None or (not isinstance(val, pd.Series) and pd.isna(val)):
                            ws.write(r + data_start_row, c, "", fmt_text)
                        elif is_date_col:
                            ws.write(r + data_start_row, c, _format_excel_date_text(val), fmt_text)
                        else:
                            ws.write(r + data_start_row, c, val, fmt)

                    if with_cruce and cruce_i is not None and leg_i is not None and sys_i is not None:
                        excel_row = r + data_start_row + 1
                        formula = (
                            f"={xl_col_to_name(leg_i)}{excel_row}-{xl_col_to_name(sys_i)}{excel_row}"
                        )
                        ws.write_formula(r + data_start_row, cruce_i, formula, fmt_num)

                if with_cruce:
                    ws.freeze_panes(data_start_row, 0)
                    if cruce_i is not None and len(df) > 0:
                        first = data_start_row
                        last = data_start_row + len(df) - 1
                        ws.conditional_format(
                            first,
                            cruce_i,
                            last,
                            cruce_i,
                            {"type": "cell", "criteria": "==", "value": 0, "format": fmt_cruce_ok},
                        )
                        ws.conditional_format(
                            first,
                            cruce_i,
                            last,
                            cruce_i,
                            {"type": "cell", "criteria": "!=", "value": 0, "format": fmt_cruce_warn},
                        )

                for c, col in enumerate(cols):
                    maxlen = max(len(str(col)), 10)
                    if len(df) > 0 and col in df.columns:
                        # fillna before astype(str): pandas 3 can leave float NaN after astype(str)
                        col_len = df[col].fillna("").astype(str).str.len().max()
                        maxlen = max(maxlen, int(col_len) + 2)
                    is_num = col in numeric_cols or col == "CRUCE"
                    ws.set_column(c, c, min(maxlen, 56), fmt_num if is_num else fmt_text)

            if main_df.empty:
                main_df = pd.DataFrame({h: [] for h in headers})

            write_cuadre_sheet(sheet_name, main_df, with_cruce=True)

            if hoja1 is not None and not hoja1.empty:
                write_cuadre_sheet(
                    "Hoja1",
                    hoja1,
                    with_cruce=False,
                    sheet_headers=list(hoja1.columns),
                )

        _publish_atomic(temp_path, final_path)
    except Exception:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)
        raise
    else:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)

    logger.info("Wrote CUADRE workbook %s account=%s rows=%s", final_path, account, len(main_df))

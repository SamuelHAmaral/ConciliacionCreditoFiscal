"""Parse Itau-style mayor / ledger text exports into a normalized DataFrame."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

# Lines that look like data: date, agency, asiento, tail
_ROW_HEAD = re.compile(
    r"^\s*(?P<fecha>\d{1,2}/\d{1,2}/\d{2,4})\s+"
    r"(?P<ag>\d{2})\s+"
    r"(?P<asiento>\d+)\s+"
    r"(?P<tail>.+?)\s*$"
)

# European-style amounts (thousands with dot, decimals with comma)
_AMOUNT = re.compile(r"\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2}")

# Transfer and balance-transfer variants to ignore as internal moves
_TRANSFER_SALDO = re.compile(
    r"(?:\b(?:transfer(?:encia|encias)?|transf\.?|traspaso|traslado)\b.*\bsaldos?\b)|"
    r"(?:\bsaldos?\b.*\b(?:transfer(?:encia|encias)?|transf\.?|traspaso|traslado)\b)",
    re.IGNORECASE,
)

_SKIP_SUBSTRINGS = (
    "Banco Itau",
    "IMPRIMIR MAYOR",
    "Page",
    "SALDO ANTERIOR",
    "SUB TOTAL",
    "Cuenta B.C.P.",
    "CUENTA:",
    "Cuenta Superior",
    "Fecha  Ag Asiento",
    "Desde ",
    "Hasta ",
    "----",
)

# Single amount in tail: debit amounts usually start before this index in the tail string
_TAIL_SINGLE_DEBIT_MAX_START = 80


def _parse_eu_amount(token: str) -> float:
    token = token.strip()
    if "," in token:
        whole, frac = token.rsplit(",", 1)
        whole = whole.replace(".", "")
        return float(f"{whole}.{frac}")
    return float(token.replace(".", ""))


def _extract_amounts(tail: str) -> tuple[float | None, float | None]:
    """
    From the tail after asiento, extract debit and credit using column layout.
    Two trailing amounts: first is Debito, second is Credito (left-to-right).
    One amount: classify by start index of the match in the tail string.
    """
    tail = tail.rstrip()
    if tail.endswith("GS"):
        tail = tail[:-2].rstrip()
    if tail.endswith("GS."):
        tail = tail[:-3].rstrip()

    matches = list(_AMOUNT.finditer(tail))
    if not matches:
        return None, None
    if len(matches) >= 2:
        d = _parse_eu_amount(matches[0].group())
        c = _parse_eu_amount(matches[1].group())
        return d, c
    m = matches[0]
    val = _parse_eu_amount(m.group())
    start = m.start()
    if start < _TAIL_SINGLE_DEBIT_MAX_START:
        return val, None
    return None, val


def _parse_cuenta_from_header(lines: list[str]) -> str | None:
    for line in lines[:400]:
        m = re.search(r"CUENTA:\s*(\d+)", line, re.IGNORECASE)
        if m:
            return m.group(1)
    return None


def _should_skip_line(line: str) -> bool:
    if not line.strip():
        return True
    for sub in _SKIP_SUBSTRINGS:
        if sub in line and _ROW_HEAD.match(line) is None:
            return True
    if _ROW_HEAD.match(line) is None:
        return True
    return False


def parse_ledger(filepath: str | Path, account_num: str | int) -> pd.DataFrame:
    """
    Read a mayor-style .txt ledger and return a clean DataFrame.

    Columns: Cuenta, Fecha, Ag, Asiento, Descripcion, Debito, Credito, _source_line
    """
    path = Path(filepath)
    account_str = str(account_num).strip()
    text = path.read_text(encoding="latin-1", errors="replace")
    lines = text.splitlines()

    file_cuenta = _parse_cuenta_from_header(lines)
    if file_cuenta and file_cuenta != account_str:
        logger.warning(
            "Ledger %s header CUENTA=%s does not match requested account_num=%s",
            path.name,
            file_cuenta,
            account_str,
        )

    rows: list[dict[str, Any]] = []
    for idx, raw in enumerate(lines, start=1):
        if _should_skip_line(raw):
            continue
        m = _ROW_HEAD.match(raw)
        if not m:
            continue
        fecha = m.group("fecha")
        ag = m.group("ag")
        asiento = m.group("asiento")
        tail = m.group("tail")
        desc_part = tail
        amt_matches = list(_AMOUNT.finditer(tail))
        if amt_matches:
            desc_part = tail[: amt_matches[0].start()].rstrip()
        desc_part = re.sub(r"\s+T\s*$", "", desc_part, flags=re.IGNORECASE).rstrip()
        desc_norm = " ".join(desc_part.split())

        if _TRANSFER_SALDO.search(desc_norm):
            continue

        debito, credito = _extract_amounts(tail)
        rows.append(
            {
                "Cuenta": account_str,
                "Fecha": fecha,
                "Ag": ag,
                "Asiento": asiento,
                "Descripcion": desc_norm,
                "Debito": debito,
                "Credito": credito,
                "_source_line": idx,
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        logger.warning("No ledger rows parsed from %s", path)
        return df

    df["Fecha"] = pd.to_datetime(df["Fecha"], dayfirst=True, format="mixed", errors="coerce")
    for col in ("Debito", "Credito"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["Asiento"] = df["Asiento"].astype(str)
    logger.info("Parsed ledger %s: %s data rows", path.name, len(df))
    return df

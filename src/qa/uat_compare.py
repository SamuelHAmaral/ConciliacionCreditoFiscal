"""Reusable helpers to compare engine CUADRE outputs vs manual reference models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

_MODEL_GLOBS: dict[str, str] = {
    "1279": "CUADRE 1279*.xlsx",
    "469": "CUADRE 469*.xlsx",
    "1280": "CUADRE 1280*.xlsx",
    "2874": "CUADRE 2874*.xlsx",
}


@dataclass
class UATVariance:
    account: str
    model_path: Path | None
    output_path: Path
    model_total: int
    output_total: int
    model_matched: int
    output_matched: int
    delta_total: int
    delta_matched: int
    status: str
    detail: str


def find_model(account: str, root: Path) -> Path | None:
    pattern = _MODEL_GLOBS[account]
    hits: list[Path] = []
    if root.is_dir():
        for sub in root.iterdir():
            if sub.is_dir() and account in sub.name:
                hits.extend(sub.glob(pattern))
        if not hits:
            hits = list(root.rglob(pattern))
    return max(hits, key=lambda p: p.stat().st_mtime) if hits else None


def _find_cuadre_header_row(path: Path, sheet: str) -> int:
    raw = pd.read_excel(path, sheet_name=sheet, header=None, nrows=12)
    for i in range(len(raw)):
        cells = [str(x).strip() for x in raw.iloc[i].tolist() if pd.notna(x)]
        if "Cuenta" in cells and any(
            c in cells for c in ("Débitos", "Debitos", "Créditos", "Creditos")
        ):
            return i
    return 0


def _load_cuadre_sheet(path: Path, account: str) -> pd.DataFrame:
    xl = pd.ExcelFile(path)
    sheet = account if account in xl.sheet_names else xl.sheet_names[0]
    header = _find_cuadre_header_row(path, sheet)
    df = pd.read_excel(path, sheet_name=sheet, header=header)
    df.columns = [str(c).strip() for c in df.columns]
    return df


def _count_cuadre_sections(df: pd.DataFrame, account: str) -> dict[str, int]:
    if df.empty:
        return {"total": 0, "matched": 0, "pend_ledger": 0, "pend_system": 0}
    ledger_amt = "Créditos" if account == "2874" else "Débitos"
    sys_amt = "IVA ML" if account == "1279" else "IVA 10"
    has_leg = df[ledger_amt].notna() if ledger_amt in df.columns else pd.Series([False] * len(df))
    has_sys = df[sys_amt].notna() if sys_amt in df.columns else pd.Series([False] * len(df))
    matched = int((has_leg & has_sys).sum())
    pend_leg = int((has_leg & ~has_sys).sum())
    pend_sys = int((~has_leg & has_sys).sum())
    return {
        "total": matched + pend_leg + pend_sys,
        "matched": matched,
        "pend_ledger": pend_leg,
        "pend_system": pend_sys,
    }


def count_model_rows(model_path: Path, account: str) -> dict[str, int]:
    df = _load_cuadre_sheet(model_path, account)
    return _count_cuadre_sections(df, account)


def count_engine_output(path: Path, account: str) -> dict[str, int]:
    df = _load_cuadre_sheet(path, account)
    sections = _count_cuadre_sections(df, account)
    return {"total": sections["total"], "matched_cruce_zero": sections["matched"]}


def _engine_counts(
    path: Path,
    account: str,
    metrics: dict[str, Any] | None,
) -> dict[str, int]:
    if metrics:
        matched = int(metrics.get("matched_rows") or 0)
        pend_leg = int(metrics.get("unmatched_ledger_rows") or 0)
        pend_sys = int(metrics.get("unmatched_system_rows") or 0)
        return {"total": matched + pend_leg + pend_sys, "matched": matched}
    sections = _count_cuadre_sections(_load_cuadre_sheet(path, account), account)
    return {"total": sections["total"], "matched": sections["matched"]}


def compare_with_golden(
    outputs_by_account: dict[str, Path],
    *,
    models_root: Path,
    output_metrics: dict[str, dict[str, Any]] | None = None,
) -> list[UATVariance]:
    rows: list[UATVariance] = []
    metrics = output_metrics or {}
    for account, out in outputs_by_account.items():
        model = find_model(account, models_root) if models_root.is_dir() else None
        engine = _engine_counts(out, account, metrics.get(account))
        if model is None:
            rows.append(
                UATVariance(
                    account=account,
                    model_path=None,
                    output_path=out,
                    model_total=0,
                    output_total=engine["total"],
                    model_matched=0,
                    output_matched=engine["matched"],
                    delta_total=engine["total"],
                    delta_matched=engine["matched"],
                    status="missing_model",
                    detail="No se encontro modelo CUADRE de referencia",
                )
            )
            continue
        model_sections = count_model_rows(model, account)
        rows.append(
            UATVariance(
                account=account,
                model_path=model,
                output_path=out,
                model_total=model_sections["total"],
                output_total=engine["total"],
                model_matched=model_sections["matched"],
                output_matched=engine["matched"],
                delta_total=engine["total"] - model_sections["total"],
                delta_matched=engine["matched"] - model_sections["matched"],
                status="ok"
                if engine["matched"] == model_sections["matched"]
                else "variance",
                detail="",
            )
        )
    return rows


def write_variance_csv(rows: list[UATVariance], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = [
        {
            "account": r.account,
            "status": r.status,
            "model_path": str(r.model_path) if r.model_path else "",
            "output_path": str(r.output_path),
            "model_total": r.model_total,
            "output_total": r.output_total,
            "delta_total": r.delta_total,
            "model_matched": r.model_matched,
            "output_matched": r.output_matched,
            "delta_matched": r.delta_matched,
            "detail": r.detail,
        }
        for r in rows
    ]
    pd.DataFrame(payload).to_csv(output_path, index=False, encoding="utf-8")
    return output_path

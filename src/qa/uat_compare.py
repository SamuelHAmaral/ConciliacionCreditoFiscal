"""Reusable UAT compare helpers for engine vs golden CUADRE outputs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

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
    for sub in root.iterdir():
        if sub.is_dir() and account in sub.name:
            hits.extend(sub.glob(pattern))
    if not hits:
        hits = list(root.rglob(pattern))
    return max(hits, key=lambda p: p.stat().st_mtime) if hits else None


def count_model_rows(model_path: Path, account: str) -> dict[str, int]:
    xl = pd.ExcelFile(model_path)
    sheet = account if account in xl.sheet_names else xl.sheet_names[0]
    df = pd.read_excel(model_path, sheet_name=sheet, header=0)
    if df.empty:
        return {"total": 0, "matched_cruce_zero": 0}
    cruce_col = next((c for c in df.columns if str(c).strip().upper() == "CRUCE"), None)
    matched = 0
    if cruce_col is not None:
        cruce = pd.to_numeric(df[cruce_col], errors="coerce")
        matched = int((cruce == 0).sum())
    return {"total": len(df), "matched_cruce_zero": matched}


def count_engine_output(path: Path, account: str) -> dict[str, int]:
    xl = pd.ExcelFile(path)
    sheet = account if account in xl.sheet_names else xl.sheet_names[0]
    df = pd.read_excel(path, sheet_name=sheet, header=0)
    if df.empty:
        return {"total": 0, "matched_cruce_zero": 0}
    ledger_amt = "Cr\u00e9ditos" if account == "2874" else "D\u00e9bitos"
    has_ledger = df[ledger_amt].notna() if ledger_amt in df.columns else pd.Series([False] * len(df))
    sys_amt = "IVA ML" if account == "1279" else "IVA 10"
    has_system = df[sys_amt].notna() if sys_amt in df.columns else pd.Series([False] * len(df))
    matched_rows = int((has_ledger & has_system).sum())
    return {"total": len(df), "matched_cruce_zero": matched_rows}


def compare_with_golden(
    outputs_by_account: dict[str, Path],
    *,
    models_root: Path,
) -> list[UATVariance]:
    rows: list[UATVariance] = []
    for account, out in outputs_by_account.items():
        model = find_model(account, models_root) if models_root.is_dir() else None
        if model is None:
            rows.append(
                UATVariance(
                    account=account,
                    model_path=None,
                    output_path=out,
                    model_total=0,
                    output_total=0,
                    model_matched=0,
                    output_matched=0,
                    delta_total=0,
                    delta_matched=0,
                    status="missing_model",
                    detail="No se encontro modelo CUADRE de referencia",
                )
            )
            continue
        m = count_model_rows(model, account)
        e = count_engine_output(out, account)
        rows.append(
            UATVariance(
                account=account,
                model_path=model,
                output_path=out,
                model_total=m["total"],
                output_total=e["total"],
                model_matched=m["matched_cruce_zero"],
                output_matched=e["matched_cruce_zero"],
                delta_total=e["total"] - m["total"],
                delta_matched=e["matched_cruce_zero"] - m["matched_cruce_zero"],
                status="ok"
                if e["total"] == m["total"] and e["matched_cruce_zero"] == m["matched_cruce_zero"]
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

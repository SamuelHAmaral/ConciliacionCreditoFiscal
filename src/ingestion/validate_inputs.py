"""Pre-run fail-fast validation for reconciliation inputs."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import pandas as pd

from config.account_config import required_columns_for
from ingestion.folder_discovery import infer_fecha_range_from_sql
from ingestion.system_imports import (
    load_famafa_csv,
    load_famafa_excel,
    load_sql_excel,
    load_sql_extract,
    to_sql_fecha_cont_series,
)

_EXCEL_SUFFIXES = {".xlsx", ".xls", ".xlsm"}


@dataclass
class ValidationReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def extend(self, other: "ValidationReport") -> None:
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)


def _norm(name: str) -> str:
    return " ".join(str(name).strip().lower().split())


def _is_missing(df: pd.DataFrame, required: Iterable[str]) -> list[str]:
    have = {_norm(c) for c in df.columns}
    missing: list[str] = []
    for col in required:
        if _norm(col) not in have:
            missing.append(col)
    return missing


def _load_preview(path: Path, source: str, *, nrows: int = 5) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if source == "sql":
        if suffix in _EXCEL_SUFFIXES:
            return load_sql_excel(path, nrows=nrows)
        return load_sql_extract(path, nrows=nrows)
    if suffix in _EXCEL_SUFFIXES:
        return load_famafa_excel(path, nrows=nrows)
    return load_famafa_csv(path, nrows=nrows)


def _read_period_sample(
    sql_path: Path,
    *,
    nrows: int = 2000,
) -> tuple[pd.Timestamp | None, pd.Timestamp | None]:
    suffix = sql_path.suffix.lower()
    if suffix in _EXCEL_SUFFIXES:
        sample = load_sql_excel(sql_path, nrows=nrows)
    else:
        sample = load_sql_extract(sql_path, nrows=nrows)
    if sample.empty:
        return None, None
    col = None
    for cand in ("Fecha_Cont", "Fecha Cont", "fecha_cont"):
        for c in sample.columns:
            if _norm(c) == _norm(cand):
                col = c
                break
        if col:
            break
    if col is None:
        return None, None
    dt = to_sql_fecha_cont_series(sample[col]).dropna()
    if dt.empty:
        return None, None
    return dt.min(), dt.max()


def validate_1279_dates(
    fecha_desde: str | None,
    fecha_hasta: str | None,
    *,
    sql_path: Path | None = None,
) -> ValidationReport:
    report = ValidationReport()
    if not fecha_desde:
        report.errors.append("1279: fecha_desde es obligatoria (AAAA-MM-DD).")
        return report
    if not fecha_hasta:
        report.errors.append("1279: fecha_hasta es obligatoria (AAAA-MM-DD).")
        return report
    try:
        fd = pd.Timestamp(fecha_desde).normalize()
    except Exception:
        report.errors.append(f"1279: fecha_desde invalida '{fecha_desde}'. Use AAAA-MM-DD.")
        return report
    try:
        fh = pd.Timestamp(fecha_hasta).normalize()
    except Exception:
        report.errors.append(f"1279: fecha_hasta invalida '{fecha_hasta}'. Use AAAA-MM-DD.")
        return report
    if fd > fh:
        report.errors.append("1279: fecha_desde debe ser menor o igual que fecha_hasta.")
        return report
    if sql_path:
        infer_fd, infer_fh = infer_fecha_range_from_sql(sql_path)
        if infer_fd and infer_fh:
            try:
                if pd.Timestamp(infer_fd).normalize() > fh or pd.Timestamp(infer_fh).normalize() < fd:
                    report.warnings.append(
                        "1279: el rango elegido no coincide con la pista de fecha del nombre del archivo SQL."
                    )
            except Exception:
                pass
        try:
            s_min, s_max = _read_period_sample(sql_path)
            if s_min and s_max and (fh < s_min or fd > s_max):
                report.warnings.append(
                    f"1279: el rango {fd.date()}..{fh.date()} no solapa la muestra SQL "
                    f"{s_min.date()}..{s_max.date()}."
                )
        except Exception as exc:
            report.warnings.append(f"1279: no se pudo revisar la muestra de fechas SQL ({exc}).")
    return report


def validate_account_inputs(
    account: str,
    *,
    ledger_path: Path,
    sql_csv: Path | None = None,
    famafa_compras: Path | None = None,
    famafa_ventas: Path | None = None,
    fecha_desde: str | None = None,
    fecha_hasta: str | None = None,
) -> ValidationReport:
    report = ValidationReport()
    if not ledger_path.is_file():
        report.errors.append(f"{account}: no se encontro el archivo mayor: {ledger_path}")
        return report

    if account == "1279":
        if sql_csv is None or not sql_csv.is_file():
            report.errors.append("1279: se requiere archivo SQL.")
            return report
        date_rep = validate_1279_dates(fecha_desde, fecha_hasta, sql_path=sql_csv)
        report.extend(date_rep)
        if date_rep.errors:
            return report
        try:
            df = _load_preview(sql_csv, "sql")
        except Exception as exc:
            report.errors.append(f"1279: no se pudo leer vista previa del SQL: {exc}")
            return report
        required = required_columns_for("1279", "sql")
        missing = _is_missing(df, required)
        if missing:
            report.errors.append(
                f"1279: faltan columnas SQL {missing}. Columnas encontradas: {list(df.columns)}"
            )
    elif account in ("469", "1280"):
        if famafa_compras is None or not famafa_compras.is_file():
            report.errors.append(f"{account}: se requiere archivo FAMAFA Compras.")
            return report
        try:
            df = _load_preview(famafa_compras, "famafa")
        except Exception as exc:
            report.errors.append(f"{account}: no se pudo leer vista previa FAMAFA Compras: {exc}")
            return report
        required = required_columns_for(account, "famafa")
        missing = _is_missing(df, required)
        if missing:
            report.errors.append(
                f"{account}: faltan columnas FAMAFA Compras {missing}. "
                f"Columnas encontradas: {list(df.columns)}"
            )
    elif account == "2874":
        if famafa_ventas is None or not famafa_ventas.is_file():
            report.errors.append("2874: se requiere archivo FAMAFA Ventas.")
            return report
        try:
            df = _load_preview(famafa_ventas, "famafa")
        except Exception as exc:
            report.errors.append(f"2874: no se pudo leer vista previa FAMAFA Ventas: {exc}")
            return report
        required = required_columns_for("2874", "famafa")
        missing = _is_missing(df, required)
        if missing:
            report.errors.append(
                f"2874: faltan columnas FAMAFA Ventas {missing}. "
                f"Columnas encontradas: {list(df.columns)}"
            )
    else:
        report.errors.append(f"Cuenta no soportada: {account}")
    return report

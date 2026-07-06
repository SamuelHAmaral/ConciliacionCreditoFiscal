"""Pre-run fail-fast validation for reconciliation inputs."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import pandas as pd

from config.account_config import required_columns_for
from ingestion.ledger_parser import parse_ledger
from ingestion.sql_fecha_range import infer_fecha_range_from_sql, read_sql_fecha_cont_range
from ingestion.system_imports import (
    SystemFileCache,
    load_system_file,
    to_datetime_series,
)


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


def _load_preview(
    path: Path,
    source: str,
    *,
    nrows: int = 5,
    cache: SystemFileCache | None = None,
) -> pd.DataFrame:
    return load_system_file(path, source, nrows=nrows, cache=cache)  # type: ignore[arg-type]


def _ledger_date_span(ledger_path: Path, account: str) -> tuple[pd.Timestamp | None, pd.Timestamp | None]:
    try:
        df = parse_ledger(ledger_path, account)
    except Exception:
        return None, None
    if df.empty or "Fecha" not in df.columns:
        return None, None
    dt = pd.to_datetime(df["Fecha"], errors="coerce", dayfirst=True).dropna()
    if dt.empty:
        return None, None
    norm = dt.dt.normalize()
    return norm.min(), norm.max()


def _system_date_span(system_path: Path) -> tuple[pd.Timestamp | None, pd.Timestamp | None]:
    try:
        df = load_system_file(system_path, "famafa")
    except Exception:
        return None, None
    if df.empty:
        return None, None
    date_col = None
    for cand in ("Fecha Emision", "Fecha Comprobante", "Fecha Emisión"):
        for c in df.columns:
            if _norm(c) == _norm(cand):
                date_col = c
                break
        if date_col:
            break
    if date_col is None:
        return None, None
    dt = to_datetime_series(df[date_col]).dropna()
    if dt.empty:
        return None, None
    norm = dt.dt.normalize()
    return norm.min(), norm.max()


def validate_ledger_date_coverage(
    account: str,
    ledger_path: Path,
    *,
    fecha_desde: str | None = None,
    fecha_hasta: str | None = None,
    system_path: Path | None = None,
) -> list[str]:
    warnings: list[str] = []
    leg_min, leg_max = _ledger_date_span(ledger_path, account)
    if leg_min is None or leg_max is None:
        return warnings

    if account == "1279" and fecha_desde and fecha_hasta:
        try:
            fd = pd.Timestamp(fecha_desde).normalize()
            fh = pd.Timestamp(fecha_hasta).normalize()
            if leg_min < fd or leg_max > fh:
                warnings.append(
                    f"{account}: el mayor abarca {leg_min.date()}..{leg_max.date()}, "
                    f"mas amplio que el rango elegido {fd.date()}..{fh.date()}. "
                    f"Las filas fuera del rango quedaran como pendientes en el mayor."
                )
        except Exception:
            pass

    if account in ("469", "1280", "2874") and system_path and system_path.is_file():
        sys_min, sys_max = _system_date_span(system_path)
        if sys_min is not None and sys_max is not None:
            if leg_max < sys_min or leg_min > sys_max:
                warnings.append(
                    f"{account}: las fechas del mayor ({leg_min.date()}..{leg_max.date()}) "
                    f"no solapan FAMAFA ({sys_min.date()}..{sys_max.date()})."
                )
            elif leg_min < sys_min or leg_max > sys_max:
                warnings.append(
                    f"{account}: el mayor ({leg_min.date()}..{leg_max.date()}) "
                    f"se extiende fuera del rango FAMAFA ({sys_min.date()}..{sys_max.date()})."
                )
    return warnings


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
            s_min, s_max, n_days_sql = read_sql_fecha_cont_range(sql_path)
            if s_min is not None and s_max is not None:
                s_min = pd.Timestamp(s_min).normalize()
                s_max = pd.Timestamp(s_max).normalize()
                if fh < s_min or fd > s_max:
                    report.warnings.append(
                        f"1279: el rango {fd.date()}..{fh.date()} no solapa el SQL "
                        f"{s_min.date()}..{s_max.date()}."
                    )
                elif fd < s_min or fh > s_max:
                    requested_days = (fh - fd).days + 1
                    report.warnings.append(
                        f"1279: el extracto SQL abarca {s_min.date()}..{s_max.date()} "
                        f"({n_days_sql} dia(s) con datos), mas estrecho que el rango "
                        f"elegido {fd.date()}..{fh.date()} ({requested_days} dia(s)). "
                        f"Ajuste Desde/Hasta o use un SQL del periodo completo; "
                        f"de lo contrario habra pendientes extra en el mayor."
                    )
        except Exception as exc:
            report.warnings.append(f"1279: no se pudo revisar las fechas del SQL ({exc}).")
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
    system_cache: SystemFileCache | None = None,
) -> ValidationReport:
    report = ValidationReport()
    if not ledger_path.is_file():
        report.errors.append(f"{account}: no se encontro el archivo mayor: {ledger_path}")
        return report

    system_path: Path | None = None
    if account == "1279":
        system_path = sql_csv
    elif account in ("469", "1280"):
        system_path = famafa_compras
    elif account == "2874":
        system_path = famafa_ventas

    for warn in validate_ledger_date_coverage(
        account,
        ledger_path,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        system_path=system_path,
    ):
        report.warnings.append(warn)

    if account == "1279":
        if sql_csv is None or not sql_csv.is_file():
            report.errors.append("1279: se requiere archivo SQL.")
            return report
        date_rep = validate_1279_dates(fecha_desde, fecha_hasta, sql_path=sql_csv)
        report.extend(date_rep)
        if date_rep.errors:
            return report
        try:
            df = _load_preview(sql_csv, "sql", cache=system_cache)
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
            df = _load_preview(famafa_compras, "famafa", cache=system_cache)
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
            df = _load_preview(famafa_ventas, "famafa", cache=system_cache)
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

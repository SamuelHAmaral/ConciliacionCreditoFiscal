"""Discover reconciliation inputs under a folder of mayor / SQL / FAMAFA files.

Looks for mayorpc*.txt (or any .txt whose header is ``CUENTA: 1279|469|1280|2874``),
SQL*, FAMAFA COMPRAS* (shared by 469 and 1280), FAMAFA VENTAS*. Subfolders named
``Cuenta 469...`` still work; Skipper uploads are usually a flat dump of original names.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# MANTENIMIENTO — si cambia el numero de cuenta, actualizar tambien:
#   config/accounts.yml, src/config/account_config.py (_DEFAULT_ACCOUNTS),
#   ui/i18n.py, src/pipeline/run_reconciliation.py (choices= y elif account ==),
#   src/rules/account_rules.py, config/skipper_job.json, docs/MANTENIMIENTO.md.
# 469 y 1280 comparten FAMAFA COMPRAS (ramas elif acc in ("469", "1280") abajo).
ACCOUNTS = ("1279", "469", "1280", "2874")
_INSUMOS_DIR_NAME = "Automatizaci\u00f3n conciliaciones"


@dataclass
class DiscoveredInputs:
    root: Path
    ledgers: dict[str, Path] = field(default_factory=dict)
    sql_1279: Path | None = None
    famafa_compras: dict[str, Path] = field(default_factory=dict)
    famafa_ventas: Path | None = None
    fecha_desde: str | None = None
    fecha_hasta: str | None = None


def _account_from_path(path: Path) -> str | None:
    text = path.as_posix().lower()
    for acc in ACCOUNTS:
        if f"cuenta {acc}" in text or f"cuenta{acc}" in text:
            return acc
        if re.search(rf"\D{acc}\D", path.name.lower()) or path.name.lower().endswith(f"{acc}.txt"):
            return acc
    name = path.name.lower().replace(" ", "")
    for acc in ACCOUNTS:
        if acc in name:
            return acc
    return None


def _pick_newest(paths: list[Path]) -> Path | None:
    if not paths:
        return None
    return max(paths, key=lambda p: p.stat().st_mtime)


def _find_in_dir(directory: Path, pattern: str) -> list[Path]:
    if not directory.is_dir():
        return []
    return list(directory.glob(pattern))


from ingestion.ledger_parser import peek_ledger_account
from ingestion.sql_fecha_range import infer_fecha_range_from_sql


def discover_inputs(root: str | Path) -> DiscoveredInputs:
    """Scan *root* and Cuenta * subfolders for mayor, SQL, and FAMAFA files."""
    base = Path(root).resolve()
    out = DiscoveredInputs(root=base)

    if not base.is_dir():
        logger.warning("Discovery root not found: %s", base)
        return out

    for p in base.rglob("mayorpc*.txt"):
        acc = _account_from_path(p)
        if acc:
            out.ledgers.setdefault(acc, p)

    for p in base.rglob("*.txt"):
        if p.name.lower().startswith("mayorpc"):
            continue
        acc = _account_from_path(p) or peek_ledger_account(p)
        if acc in ACCOUNTS:
            out.ledgers.setdefault(acc, p)

    for sub in sorted(base.iterdir()):
        if not sub.is_dir():
            continue
        acc = _account_from_path(sub)
        if not acc:
            continue

        mayor = _pick_newest(_find_in_dir(sub, "mayorpc*.txt"))
        if mayor and acc not in out.ledgers:
            out.ledgers[acc] = mayor

        if acc == "1279":
            sql_files = (
                _find_in_dir(sub, "SQL*.xlsx")
                + _find_in_dir(sub, "SQL*.csv")
                + _find_in_dir(sub, "*1279*.xlsx")
            )
            picked = _pick_newest(sql_files)
            if picked:
                out.sql_1279 = picked
        elif acc in ("469", "1280"):
            compras = (
                _find_in_dir(sub, "FAMAFA COMPRAS*.xlsx")
                + _find_in_dir(sub, "FAMAFA COMPRAS*.csv")
                + _find_in_dir(sub, "FAMAFA*.xlsx")
            )
            picked = _pick_newest(compras)
            if picked:
                out.famafa_compras[acc] = picked
        elif acc == "2874":
            ventas = (
                _find_in_dir(sub, "FAMAFA VENTAS*.xlsx")
                + _find_in_dir(sub, "FAMAFA*.xlsx")
                + _find_in_dir(sub, "FAMAFA*.csv")
            )
            picked = _pick_newest(ventas)
            if picked:
                out.famafa_ventas = picked

    if out.sql_1279 is None:
        sql_files = list(base.rglob("SQL*.xlsx")) + list(base.rglob("SQL*.csv"))
        out.sql_1279 = _pick_newest(sql_files)

    for acc in ("469", "1280"):
        if acc in out.famafa_compras:
            continue
        named = list(base.rglob(f"FAMAFA COMPRAS*{acc}*.xlsx")) + list(
            base.rglob(f"FAMAFA COMPRAS*{acc}*.csv")
        )
        picked = _pick_newest(named)
        if picked:
            out.famafa_compras[acc] = picked

    generic_compras = [
        p
        for p in list(base.rglob("FAMAFA COMPRAS*.xlsx")) + list(base.rglob("FAMAFA COMPRAS*.csv"))
        if "ventas" not in p.name.lower()
    ]
    shared_compras = _pick_newest(generic_compras)
    if shared_compras is not None:
        for acc in ("469", "1280"):
            out.famafa_compras.setdefault(acc, shared_compras)

    if out.famafa_ventas is None:
        ventas = list(base.rglob("FAMAFA VENTAS*.xlsx")) + list(base.rglob("FAMAFA VENTAS*.csv"))
        out.famafa_ventas = _pick_newest(ventas)

    fd, fh = infer_fecha_range_from_sql(out.sql_1279)
    out.fecha_desde = fd
    out.fecha_hasta = fh

    logger.info(
        "Discovered root=%s ledgers=%s sql=%s compras=%s ventas=%s",
        base.name,
        list(out.ledgers.keys()),
        out.sql_1279.name if out.sql_1279 else None,
        list(out.famafa_compras.keys()),
        out.famafa_ventas.name if out.famafa_ventas else None,
    )
    return out


def default_workspace_folder(project_root: Path) -> Path:
    """Sibling insumos folder next to reconciliation_engine."""
    ws = project_root.parent
    return ws / _INSUMOS_DIR_NAME

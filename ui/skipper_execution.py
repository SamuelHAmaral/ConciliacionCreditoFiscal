"""Map Skipper attachments and form fields onto the headless RunConfig.

Skipper UI uploads individual files. Cabo stores an *upload name* on disk;
the execution JSON has *original name* (`file_original_names`). This module
copies files to original names, then folder_discovery pairs:

  mayorpc 1279.txt + SQL*              -> cuenta 1279
  mayorpc 469.txt  + FAMAFA COMPRAS*   -> cuenta 469 (amount-only match)
  mayorpc 1280.txt + same Compras file -> cuenta 1280
  mayorpc 2874.txt + FAMAFA VENTAS*    -> cuenta 2874

CUADRE modelo / CRUCE docx / Limpia_mayores are not inputs.
See docs/COMO_FUNCIONA.md.
"""

from __future__ import annotations

import logging
import re
import shutil
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ingestion.folder_discovery import ACCOUNTS, discover_inputs
from ingestion.ledger_parser import peek_ledger_account
from ingestion.sql_fecha_range import infer_last_sql_day
from ui.services import AccountJob, RunConfig

logger = logging.getLogger(__name__)

# Sale de folder_discovery.ACCOUNTS. Si cambia el numero de cuenta, toque esa tupla
# (docs/MANTENIMIENTO.md). 469 y 1280 siguen compartiendo FAMAFA COMPRAS mas abajo.
DEFAULT_ACCOUNTS = list(ACCOUNTS)
_TRUTHY = {"1", "true", "yes", "y", "si", "sí", "on"}


@dataclass
class SkipperJobParams:
    fecha_desde: str | None = None
    fecha_hasta: str | None = None
    solo_ultimo_dia_sql: bool = False
    match_469_amount_only: bool = False
    accounts: list[str] = field(default_factory=lambda: list(DEFAULT_ACCOUNTS))
    amount_tolerance_1279: float = 0.01


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _looks_truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in _TRUTHY


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_accounts(value: Any) -> list[str]:
    if value is None or value == "":
        return list(DEFAULT_ACCOUNTS)
    if isinstance(value, (list, tuple)):
        parts = [str(v).strip() for v in value]
    else:
        parts = [p.strip() for p in str(value).replace(";", ",").split(",")]
    wanted = [p for p in parts if p]
    return wanted or list(DEFAULT_ACCOUNTS)


def _parse_tolerance(value: Any, default: float = 0.01) -> float:
    if value is None or value == "":
        return default
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed >= 0 else default


def _other_fields(payload: dict[str, Any]) -> dict[str, Any]:
    data = _as_dict(payload.get("data"))
    other = _as_dict(data.get("other")) or _as_dict(payload.get("other"))
    merged: dict[str, Any] = dict(payload)
    merged.update(data)
    merged.update(other)
    return merged


def params_from_execution(payload: dict[str, Any] | None) -> SkipperJobParams:
    """Read Skipper form fields from an execution payload (`data.other`)."""
    fields = _other_fields(payload or {})
    return SkipperJobParams(
        fecha_desde=_optional_str(fields.get("fecha_desde")),
        fecha_hasta=_optional_str(fields.get("fecha_hasta")),
        solo_ultimo_dia_sql=_looks_truthy(fields.get("solo_ultimo_dia_sql")),
        match_469_amount_only=_looks_truthy(fields.get("match_469_amount_only")),
        accounts=_parse_accounts(fields.get("accounts")),
        amount_tolerance_1279=_parse_tolerance(fields.get("amount_tolerance_1279")),
    )


_ORIGINAL_KEYS = (
    "original_name",
    "originalName",
    "original name",
    "nombre_original",
    "nombreOriginal",
    "client_filename",
    "fileOriginalName",
)
_UPLOAD_KEYS = (
    "upload_name",
    "uploadName",
    "upload name",
    "nombre_upload",
    "nombreUpload",
    "stored_name",
    "saved_name",
    "server_filename",
    "fileUploadName",
    "storage_name",
)
_UPLOAD_FALLBACK_KEYS = ("name", "filename", "file_name", "path", "file")
_ATTACHMENT_LIST_KEYS = ("attachments", "files", "documents", "adjuntos", "uploads")
_UPLOAD_TO_ORIGINAL_KEYS = ("file_original_names", "fileOriginalNames")
_ORIGINAL_TO_UPLOAD_KEYS = ("reversed_attachment_names", "reversedAttachmentNames")


def _basename_safe(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip().replace("\\", "/")
    if not text:
        return None
    name = Path(text).name
    if not name or name in {".", ".."}:
        return None
    if re.search(r"[\x00-\x1f]", name):
        return None
    return name


def _first_key(record: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    lower = {str(k).strip().lower(): v for k, v in record.items()}
    for key in keys:
        raw = record.get(key)
        if raw is None:
            raw = lower.get(key.lower())
        name = _basename_safe(raw)
        if name:
            return name
    return None


def _pair_from_record(record: dict[str, Any]) -> tuple[str, str] | None:
    original = _first_key(record, _ORIGINAL_KEYS)
    if not original:
        return None
    upload = _first_key(record, _UPLOAD_KEYS) or _first_key(record, _UPLOAD_FALLBACK_KEYS)
    if not upload:
        upload = original
    return upload, original


def _pairs_from_name_map(mapping: dict[str, Any], *, reversed_map: bool) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for left, right in mapping.items():
        upload = _basename_safe(right if reversed_map else left)
        original = _basename_safe(left if reversed_map else right)
        if upload and original:
            pairs.append((upload, original))
    return pairs


def attachment_name_pairs(payload: dict[str, Any] | None) -> list[tuple[str, str]]:
    """Collect (upload_name, original_name) from a Skipper execution JSON."""
    pairs: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()

    def _add_pair(pair: tuple[str, str] | None) -> None:
        if pair and pair not in seen:
            seen.add(pair)
            pairs.append(pair)

    def _add_maps(node: dict[str, Any]) -> None:
        for key in _UPLOAD_TO_ORIGINAL_KEYS:
            raw = node.get(key)
            if isinstance(raw, dict):
                for pair in _pairs_from_name_map(raw, reversed_map=False):
                    _add_pair(pair)
        for key in _ORIGINAL_TO_UPLOAD_KEYS:
            raw = node.get(key)
            if isinstance(raw, dict):
                for pair in _pairs_from_name_map(raw, reversed_map=True):
                    _add_pair(pair)

    def _add(record: dict[str, Any]) -> None:
        _add_maps(record)
        _add_pair(_pair_from_record(record))

    def _walk(node: Any, depth: int = 0) -> None:
        if depth > 8 or node is None:
            return
        if isinstance(node, dict):
            _add(node)
            for key in _ATTACHMENT_LIST_KEYS:
                if key in node:
                    _walk(node[key], depth + 1)
            data = node.get("data")
            if isinstance(data, dict):
                _walk(data, depth + 1)
            if depth < 3:
                for value in node.values():
                    if isinstance(value, (dict, list)):
                        _walk(value, depth + 1)
        elif isinstance(node, list):
            for item in node:
                _walk(item, depth + 1)

    _walk(payload or {})
    return pairs


def _unique_dest(dest_dir: Path, original_name: str) -> Path:
    target = dest_dir / original_name
    if not target.exists():
        return target
    stem, suffix = Path(original_name).stem, Path(original_name).suffix
    n = 2
    while True:
        candidate = dest_dir / f"{stem} ({n}){suffix}"
        if not candidate.exists():
            return candidate
        n += 1


def stage_original_names(root: Path, payload: dict[str, Any] | None) -> Path | None:
    """Copy Cabo files into ``_named`` using Skipper original names when present."""
    pairs = attachment_name_pairs(payload)
    upload_to_original = {upload: original for upload, original in pairs}
    files = [p for p in root.iterdir() if p.is_file() and p.suffix.lower() != ".zip"]
    if not files:
        return None
    if not pairs and _has_mayorpc(root):
        return None

    dest = root / "_named"
    dest.mkdir(parents=True, exist_ok=True)
    copied = 0
    used_originals: set[str] = set()
    for src in files:
        original = (
            upload_to_original.get(src.name)
            or next((orig for up, orig in pairs if src.name.lower() == up.lower()), None)
        )
        if original is None:
            acc = peek_ledger_account(src) if src.suffix.lower() == ".txt" else None
            if acc in ACCOUNTS:
                original = f"mayorpc {acc}.txt"
            else:
                original = src.name
        if original in used_originals:
            target = _unique_dest(dest, original)
        else:
            target = dest / original
            used_originals.add(original)
        if src.resolve() != target.resolve():
            shutil.copy2(src, target)
        copied += 1
        logger.info("Adjunto %s -> %s", src.name, target.name)
    return dest if copied else None


def _has_mayorpc(root: Path) -> bool:
    return next(root.rglob("mayorpc*.txt"), None) is not None


def _safe_extract_zip(archive: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    dest_resolved = dest.resolve()
    with zipfile.ZipFile(archive) as zf:
        for info in zf.infolist():
            target = (dest / info.filename).resolve()
            if dest_resolved not in target.parents and target != dest_resolved:
                raise ValueError(f"Unsafe zip path: {info.filename}")
        zf.extractall(dest)


def prepare_insumos_dir(
    attachment_dir: str | Path,
    payload: dict[str, Any] | None = None,
) -> Path:
    """Return a folder Scan-ready for discover_inputs.

    Skipper UI uploads individual files with an original name and an upload name.
    Cabo may store the upload name on disk; we copy to original names first.
    If there is no mayorpc yet, extract a ZIP if Cabo left one.
    """
    root = Path(attachment_dir).expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Attachment folder not found: {root}")

    named = stage_original_names(root, payload)
    if named is not None and (_has_mayorpc(named) or next(named.glob("*.txt"), None)):
        return named

    if _has_mayorpc(root):
        return root

    zips = sorted(
        [p for p in root.iterdir() if p.is_file() and p.suffix.lower() == ".zip"],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not zips:
        return named or root
    dest = root / "_extracted"
    _safe_extract_zip(zips[0], dest)
    return dest


def _share_famafa_compras(by_account: dict[str, Path]) -> dict[str, Path]:
    shared = by_account.get("469") or by_account.get("1280")
    if shared is None:
        return dict(by_account)
    out = dict(by_account)
    out.setdefault("469", shared)
    out.setdefault("1280", shared)
    return out


def run_config_from_insumos(
    insumos: str | Path,
    salida: str | Path,
    params: SkipperJobParams | None = None,
) -> RunConfig | None:
    """Build RunConfig from a discovered insumos folder. None if no mayor files."""
    params = params or SkipperJobParams()
    discovered = discover_inputs(insumos)
    jobs: list[AccountJob] = []
    for acc in params.accounts:
        mayor = discovered.ledgers.get(acc)
        if mayor is not None and mayor.is_file():
            jobs.append(AccountJob(account=acc, ledger_path=mayor))
    if not jobs:
        return None

    fecha_desde = params.fecha_desde or discovered.fecha_desde
    fecha_hasta = params.fecha_hasta or discovered.fecha_hasta
    if params.solo_ultimo_dia_sql:
        last = infer_last_sql_day(discovered.sql_1279)
        if last:
            fecha_desde = last
            fecha_hasta = last

    famafa = _share_famafa_compras(discovered.famafa_compras)
    return RunConfig(
        salida=Path(salida),
        jobs=jobs,
        sql_csv=discovered.sql_1279,
        famafa_compras=famafa.get("469") or famafa.get("1280"),
        famafa_compras_by_account=famafa or None,
        famafa_ventas=discovered.famafa_ventas,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        amount_tolerance_1279=params.amount_tolerance_1279,
        match_469_amount_only=params.match_469_amount_only,
    )

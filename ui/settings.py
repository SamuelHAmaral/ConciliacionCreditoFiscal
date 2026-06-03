"""Persist last-used folders for the desktop app."""

from __future__ import annotations

import json
import logging
import os
import shutil
from pathlib import Path

from ui.app_identity import APP_NAME, LEGACY_APP_FOLDER_NAMES
from ui.i18n import DEFAULT_LANGUAGE, normalize_language
from ui.theme import normalize_appearance
from ui.window_presets import normalize_window_preset

logger = logging.getLogger(__name__)

_SETTINGS_DEFAULTS: dict[str, str] = {
    "language": DEFAULT_LANGUAGE,
}


def _finalize_settings(data: dict[str, str]) -> dict[str, str]:
    merged = {**_SETTINGS_DEFAULTS, **data}
    merged["language"] = normalize_language(merged.get("language"))
    return merged


def _portable_settings_base() -> Path:
    local = os.getenv("LOCALAPPDATA", "").strip()
    if local:
        return Path(local)
    return Path.home()


def _migrate_settings_dir(base: Path, target: Path) -> None:
    if target.is_dir():
        return
    for legacy_name in LEGACY_APP_FOLDER_NAMES:
        legacy = base / legacy_name
        if not legacy.is_dir():
            continue
        try:
            legacy.rename(target)
            logger.info("Renamed settings folder %s -> %s", legacy, target)
            return
        except OSError:
            try:
                target.mkdir(parents=True, exist_ok=True)
                src = legacy / "settings.json"
                if src.is_file():
                    shutil.copy2(src, target / "settings.json")
                logger.info("Copied settings from %s to %s", legacy, target)
                return
            except OSError as e:
                logger.warning("Could not migrate settings from %s: %s", legacy, e)


def _portable_settings_dir() -> Path:
    base = _portable_settings_base()
    target = base / APP_NAME
    _migrate_settings_dir(base, target)
    return target


def settings_path(app_root: Path) -> Path:
    return _portable_settings_dir() / "settings.json"


def _legacy_settings_candidates(app_root: Path) -> list[Path]:
    cands: list[Path] = []
    if app_root.is_dir():
        cands.append(app_root / ".conciliacion_settings.json")
    cands.append(Path.home() / ".conciliacion_credito_fiscal.json")
    cands.append(Path.home() / ".conciliacion_amaral.json")
    return cands


def _load_json(path: Path) -> dict[str, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return {str(k): str(v) for k, v in data.items()}
    return {}


def _migrate_legacy_settings(app_root: Path, target: Path) -> dict[str, str]:
    for legacy in _legacy_settings_candidates(app_root):
        if not legacy.is_file():
            continue
        try:
            data = _load_json(legacy)
            if not data:
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(data, indent=2), encoding="utf-8")
            logger.info("Migrated settings from %s to %s", legacy, target)
            return _finalize_settings(data)
        except Exception as e:
            logger.warning("Could not migrate settings %s: %s", legacy, e)
    return _finalize_settings({})


def load_settings(app_root: Path) -> dict[str, str]:
    path = settings_path(app_root)
    if not path.is_file():
        return _migrate_legacy_settings(app_root, path)
    try:
        return _finalize_settings(_load_json(path))
    except Exception as e:
        logger.warning("Could not read settings %s: %s", path, e)
    return _finalize_settings({})


def save_settings(app_root: Path, **values: object) -> None:
    path = settings_path(app_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    current = load_settings(app_root)
    for key, val in values.items():
        sval = str(val)
        if key == "language":
            current[key] = normalize_language(sval)
        elif key == "appearance":
            current[key] = normalize_appearance(sval)
        elif key == "window_preset":
            current[key] = normalize_window_preset(sval)
        elif sval.strip():
            current[key] = sval.strip()
    try:
        path.write_text(json.dumps(current, indent=2), encoding="utf-8")
    except OSError as e:
        logger.warning("Could not save settings %s: %s", path, e)

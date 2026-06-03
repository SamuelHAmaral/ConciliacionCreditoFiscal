"""Resolve and apply the desktop window / taskbar icon."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from ui.brand_icon import BRAND_LOGO_NAMES, ResolvedIcons, resolve_icons

logger = logging.getLogger(__name__)

WINDOWS_APP_USER_MODEL_ID = "ConciliacionCreditoFiscal.Desktop.1.0"


def _assets_dirs(app_root: Path) -> list[Path]:
    dirs = [app_root / "desktop" / "assets", app_root / "assets"]
    if getattr(sys, "frozen", False):
        meipass = Path(getattr(sys, "_MEIPASS", app_root))
        dirs.insert(0, meipass / "desktop" / "assets")
        dirs.insert(1, meipass / "assets")
    return dirs


def _resolve_from_dirs(dirs: list[Path]) -> ResolvedIcons | None:
    for assets in dirs:
        if assets.is_dir():
            resolved = resolve_icons(assets)
            if resolved is not None:
                return resolved
    return None


def brand_logo_path(app_root: Path) -> Path | None:
    resolved = _resolve_from_dirs(_assets_dirs(app_root))
    return resolved.brand_png if resolved else None


def default_icon_path(app_root: Path) -> Path | None:
    resolved = _resolve_from_dirs(_assets_dirs(app_root))
    return resolved.ico if resolved else None


def default_icon_png_path(app_root: Path) -> Path | None:
    """128px PNG tuned for Tk iconphoto (not the full 1080px source)."""
    resolved = _resolve_from_dirs(_assets_dirs(app_root))
    return resolved.photo_png if resolved else None


def init_windows_app_identity() -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(WINDOWS_APP_USER_MODEL_ID)
    except Exception as exc:
        logger.debug("SetCurrentProcessExplicitAppUserModelID failed: %s", exc)


def _set_windows_hwnd_icons(window: object, ico_path: str) -> None:
    """Load best embedded size from .ico (cx/cy=0 lets Windows pick)."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        user32 = ctypes.windll.user32
        wid = int(window.winfo_id())  # type: ignore[attr-defined]
        hwnd = user32.GetParent(wid)
        if not hwnd:
            hwnd = wid
        lr_loadfromfile = 0x0010
        image_icon = 1
        wm_seticon = 0x0080
        icon_small, icon_big = 0, 1
        for slot in (icon_small, icon_big):
            hicon = user32.LoadImageW(0, ico_path, image_icon, 0, 0, lr_loadfromfile)
            if hicon:
                user32.SendMessageW(hwnd, wm_seticon, slot, hicon)
    except Exception as exc:
        logger.debug("WM_SETICON failed: %s", exc)


def apply_window_icon(window: object, app_root: Path) -> None:
    resolved = _resolve_from_dirs(_assets_dirs(app_root))
    if resolved is None:
        logger.warning(
            "No brand logo in desktop/assets. Add one of: %s",
            ", ".join(BRAND_LOGO_NAMES),
        )
        return

    ico_path = str(resolved.ico)
    photo_path = str(resolved.photo_png)

    def _set() -> None:
        try:
            window.iconbitmap(default=ico_path)  # type: ignore[attr-defined]
            window.iconbitmap(ico_path)  # type: ignore[attr-defined]
        except Exception as exc:
            logger.debug("iconbitmap failed: %s", exc)
        try:
            import tkinter as tk

            photo = tk.PhotoImage(file=photo_path)
            window.iconphoto(True, photo)  # type: ignore[attr-defined]
            setattr(window, "_amaral_icon_photo", photo)
        except Exception as exc:
            logger.debug("iconphoto failed for %s: %s", photo_path, exc)
        _set_windows_hwnd_icons(window, ico_path)

    _set()
    try:
        after = getattr(window, "after", None)
        if callable(after):
            after(250, _set)
    except Exception:
        pass

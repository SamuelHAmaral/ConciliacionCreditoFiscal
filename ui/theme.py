"""CustomTkinter theme bootstrap and palettes for desktop app."""

from __future__ import annotations

from dataclasses import dataclass
import platform

import customtkinter as ctk  # type: ignore[reportMissingImports]

DEFAULT_APPEARANCE = "light"

_dpi_awareness_done = False
_last_ctk_appearance: str | None = None


@dataclass(frozen=True)
class ThemeColors:
    bg: str
    surface: str
    card: str
    input_bg: str
    border: str
    text: str
    text_muted: str
    primary: str
    primary_hover: str
    success: str
    error: str
    accent_light: str
    secondary_hover: str


LIGHT_THEME = ThemeColors(
    bg="#eef2f7",
    surface="#ffffff",
    card="#eef1f6",
    input_bg="#ffffff",
    border="#d4dbe5",
    text="#1f2937",
    text_muted="#6b7280",
    primary="#0f4ba5",
    primary_hover="#0b3f8c",
    success="#1f8b4c",
    error="#c43d32",
    accent_light="#e3ebf7",
    secondary_hover="#d8e4f6",
)

DARK_THEME = ThemeColors(
    bg="#12151c",
    surface="#1c222d",
    card="#262e3d",
    input_bg="#151a24",
    border="#3a4558",
    text="#eceff4",
    text_muted="#9ca6b8",
    primary="#4d8fdb",
    primary_hover="#3f7fcc",
    success="#34d399",
    error="#f07070",
    accent_light="#2e3648",
    secondary_hover="#3d4a61",
)


def normalize_appearance(value: str | None) -> str:
    key = (value or "").strip().lower()
    if key in ("dark", "1", "true", "yes"):
        return "dark"
    return "light"


def get_theme_colors(appearance: str | None) -> ThemeColors:
    return DARK_THEME if normalize_appearance(appearance) == "dark" else LIGHT_THEME


def _enable_windows_dpi_awareness() -> None:
    global _dpi_awareness_done
    if _dpi_awareness_done or platform.system() != "Windows":
        return
    _dpi_awareness_done = True
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            import ctypes

            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def apply_theme(appearance: str | None = None) -> ThemeColors:
    """Apply global CustomTkinter look-and-feel and return the active palette."""
    global _last_ctk_appearance
    _enable_windows_dpi_awareness()
    mode = normalize_appearance(appearance)
    if _last_ctk_appearance != mode:
        ctk.set_appearance_mode("dark" if mode == "dark" else "light")
        ctk.set_default_color_theme("blue")
        ctk.set_widget_scaling(1.0)
        ctk.set_window_scaling(1.0)
        _last_ctk_appearance = mode
    return get_theme_colors(mode)


def make_primary_button(parent: ctk.CTkBaseClass, colors: ThemeColors, **kwargs: object) -> ctk.CTkButton:
    """Create primary dashboard action button."""
    return ctk.CTkButton(
        parent,
        fg_color=colors.primary,
        hover_color=colors.primary_hover,
        text_color="#ffffff",
        corner_radius=10,
        font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
        height=40,
        **kwargs,  # type: ignore[arg-type]
    )

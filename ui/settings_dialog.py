"""Settings modal (language, theme) for the desktop GUI."""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import customtkinter as ctk

from ui.i18n import (
    DEFAULT_LANGUAGE,
    LANG_DISPLAY_CHOICES,
    language_code_from_display,
    language_display_for,
    normalize_language,
    t,
)
from ui.theme import ThemeColors, normalize_appearance
from ui.window_icon import apply_window_icon

if TYPE_CHECKING:
    from desktop.conciliation_gui import ConciliationApp


@dataclass
class SettingsResult:
    language: str
    appearance: str


def show_settings_dialog(
    parent: ctk.CTk,
    app: "ConciliationApp",
    *,
    app_root: Path,
    lang: str,
    appearance: str,
    colors: ThemeColors,
) -> SettingsResult | None:
    """Show settings modal; return choices if the user applied, else None."""
    dlg = ctk.CTkToplevel(parent)
    apply_window_icon(dlg, app_root)  # once; avoids title-bar flicker on the main window
    dlg.title(t("settings_title", lang))
    dlg.geometry("420x260")
    dlg.resizable(False, False)
    dlg.transient(parent)
    dlg.grab_set()
    dlg.configure(fg_color=colors.surface)

    result: dict[str, SettingsResult | None] = {"value": None}

    pad = ctk.CTkFrame(dlg, fg_color="transparent")
    pad.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

    ctk.CTkLabel(
        pad,
        text=t("settings_title", lang),
        font=ctk.CTkFont("Segoe UI", 18, "bold"),
        text_color=colors.text,
    ).pack(anchor="w", pady=(0, 16))

    ctk.CTkLabel(pad, text=t("settings_language", lang), anchor="w", text_color=colors.text).pack(
        fill="x", pady=(0, 4)
    )
    var_lang = tk.StringVar(value=language_display_for(normalize_language(lang or DEFAULT_LANGUAGE)))
    lang_menu = ctk.CTkOptionMenu(pad, variable=var_lang, values=list(LANG_DISPLAY_CHOICES), width=280)
    lang_menu.pack(fill="x", pady=(0, 14))

    ctk.CTkLabel(pad, text=t("settings_appearance", lang), anchor="w", text_color=colors.text).pack(
        fill="x", pady=(0, 4)
    )
    var_dark = tk.BooleanVar(value=normalize_appearance(appearance) == "dark")
    dark_switch = ctk.CTkSwitch(pad, text="", variable=var_dark, onvalue=True, offvalue=False)
    dark_switch.pack(anchor="w", pady=(0, 20))

    btn_row = ctk.CTkFrame(pad, fg_color="transparent")
    btn_row.pack(fill="x")

    def on_cancel() -> None:
        dlg.destroy()

    def on_apply() -> None:
        result["value"] = SettingsResult(
            language=language_code_from_display(var_lang.get()),
            appearance="dark" if var_dark.get() else "light",
        )
        dlg.destroy()

    ctk.CTkButton(
        btn_row,
        text=t("settings_cancel", lang),
        fg_color=colors.accent_light,
        text_color=colors.text,
        hover_color=colors.secondary_hover,
        command=on_cancel,
        width=120,
    ).pack(side="left", padx=(0, 8))
    ctk.CTkButton(
        btn_row,
        text=t("settings_apply", lang),
        fg_color=colors.primary,
        hover_color=colors.primary_hover,
        text_color="#ffffff",
        command=on_apply,
        width=120,
    ).pack(side="left")

    dlg.wait_window()
    return result["value"]

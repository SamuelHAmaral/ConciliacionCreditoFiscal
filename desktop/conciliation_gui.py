"""
Conciliacion financiera - UI de escritorio (CustomTkinter dashboard).

Uso: doble clic en ConciliacionGUI.bat o ejecutar desktop/conciliation_gui.py
"""

from __future__ import annotations

import json
import logging
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import TypeVar

if getattr(sys, "frozen", False):
    _MEIPASS = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    _ROOT = Path(sys.executable).resolve().parent
    sys.path.insert(0, str(_MEIPASS))
else:
    _ROOT = Path(__file__).resolve().parents[1]
    if str(_ROOT) not in sys.path:
        sys.path.insert(0, str(_ROOT))
    _SRC = _ROOT / "src"
    if str(_SRC) not in sys.path:
        sys.path.insert(0, str(_SRC))


def _batch_worker_request_argv() -> Path | None:
    argv = sys.argv[1:]
    if argv and argv[0] == "--gui-batch-worker" and len(argv) >= 2:
        return Path(argv[1])
    return None


_batch_request = _batch_worker_request_argv()
if _batch_request is not None:
    from ui.batch_worker import run_from_request  # noqa: E402

    raise SystemExit(run_from_request(_batch_request))

import customtkinter as ctk

from ingestion.folder_discovery import DiscoveredInputs, discover_inputs  # noqa: E402
from ui.i18n import (  # noqa: E402
    DEFAULT_LANGUAGE,
    account_label,
    file_types,
    mayor_file_types,
    normalize_language,
    t,
)
from ui.run_config_io import read_result_json  # noqa: E402
from ui.services import (  # noqa: E402
    AccountJob,
    AccountRunResult,
    RunConfig,
    ensure_src_on_path,
    project_root,
    validate_run_config,
)
from ui.subprocess_batch import BatchSubprocessJob, start_batch_subprocess  # noqa: E402
from ui.validation_dialog import show_validation_dialog  # noqa: E402
from ui.settings import load_settings, save_settings, settings_path  # noqa: E402
from ui.uat_flags import resolve_run_uat  # noqa: E402
from ui.activity_log import format_audit_activity  # noqa: E402
from ui.settings_dialog import SettingsResult, show_settings_dialog  # noqa: E402
from ui.theme import ThemeColors, apply_theme, make_primary_button, normalize_appearance  # noqa: E402
from ui.widget_theme import apply_widget_theme  # noqa: E402
from ui.window_icon import apply_window_icon, init_windows_app_identity  # noqa: E402
from ui.window_presets import (  # noqa: E402
    DEFAULT_WINDOW_PRESET,
    format_window_geometry,
    get_window_preset,
    parse_window_geometry,
)
from qa.uat_compare import UATVariance  # noqa: E402

ACCOUNTS = ("1279", "469", "1280", "2874")
_MAX_LOG_LINES = 1200
_LOG_POLL_MS = 200
_LOG_BATCH_MAX = 60

_T = TypeVar("_T")


class _TkLogHandler(logging.Handler):
    """Thread-safe forwarder from logging records to a queue."""

    def __init__(self, log_queue: "queue.Queue[str]") -> None:
        super().__init__(level=logging.INFO)
        self._queue = log_queue

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
        except Exception:
            msg = record.getMessage()
        try:
            self._queue.put_nowait(msg)
        except queue.Full:
            # Drop excess logs to protect UI responsiveness under bursts.
            pass


def _truncate_path(path: str, max_len: int = 72) -> str:
    p = path.strip().strip('"')
    if not p or len(p) <= max_len:
        return p
    parts = Path(p).parts
    if len(parts) >= 2:
        tail = str(Path(parts[-2]) / parts[-1])
        if len(tail) <= max_len - 4:
            return f"...{tail}"
    name = parts[-1] if parts else p
    if len(name) <= max_len - 4:
        return f"...{name}"
    return p[: max_len - 3] + "..."


def _attach_tooltip(widget: ctk.CTkBaseClass, text: str, *, colors: ThemeColors) -> None:
    widget._tooltip_text = text  # type: ignore[attr-defined]
    if getattr(widget, "_tooltip_bound", False):
        return
    widget._tooltip_bound = True  # type: ignore[attr-defined]
    tip: tk.Toplevel | None = None

    def show(_: object) -> None:
        nonlocal tip
        tip_text = getattr(widget, "_tooltip_text", "")
        if not tip_text:
            return
        x = widget.winfo_rootx() + 16
        y = widget.winfo_rooty() + widget.winfo_height() + 4
        tip = tk.Toplevel(widget)
        tip.wm_overrideredirect(True)
        tip.wm_geometry(f"+{x}+{y}")
        lbl = tk.Label(
            tip,
            text=tip_text,
            background=colors.surface,
            foreground=colors.text,
            relief=tk.SOLID,
            borderwidth=1,
            font=("Segoe UI", 9),
            padx=6,
            pady=3,
        )
        lbl.pack()

    def hide(_: object) -> None:
        nonlocal tip
        if tip is not None:
            tip.destroy()
            tip = None

    widget.bind("<Enter>", show)
    widget.bind("<Leave>", hide)


def _browse_file(var: tk.StringVar, title: str, filetypes: list[tuple[str, str]]) -> None:
    p = filedialog.askopenfilename(title=title, filetypes=filetypes)
    if p:
        var.set(p)


def _browse_dir(var: tk.StringVar, title: str) -> None:
    initial = var.get().strip().strip('"')
    initialdir = initial if initial and Path(initial).is_dir() else None
    p = filedialog.askdirectory(title=title, initialdir=initialdir)
    if p:
        var.set(p)


class ConciliationApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        settings_file = settings_path(_ROOT)
        saved = load_settings(_ROOT)
        self._lang = normalize_language(saved.get("language", DEFAULT_LANGUAGE))
        if not settings_file.is_file():
            save_settings(_ROOT, language=self._lang)
        self._appearance = normalize_appearance(saved.get("appearance"))
        self._window_preset = DEFAULT_WINDOW_PRESET
        self._colors = apply_theme(self._appearance)
        self.configure(fg_color=self._colors.bg)

        default_out = saved.get("salida") or str((_ROOT / "Resultados conciliacion").resolve())
        if getattr(sys, "frozen", False) and "salida" not in saved:
            default_out = str((Path(sys.executable).resolve().parent / "Resultados conciliacion").resolve())

        self.var_salida = tk.StringVar(value=default_out)
        self.var_insumos = tk.StringVar(value=saved.get("insumos", ""))
        self.var_sql = tk.StringVar()
        self.var_fc = tk.StringVar()
        self.var_fv = tk.StringVar()
        self.var_fd = tk.StringVar(value=saved.get("fecha_desde", "2026-04-01"))
        self.var_fh = tk.StringVar(value=saved.get("fecha_hasta", "2026-04-30"))
        self.var_tol_1279 = tk.StringVar(value=saved.get("amount_tolerance_1279", "0.01"))
        self.var_verbose = tk.BooleanVar(value=False)

        self._ledger_vars: dict[str, tk.StringVar] = {a: tk.StringVar() for a in ACCOUNTS}
        self._secondary_buttons: list[ctk.CTkButton] = []
        self._ghost_buttons: list[ctk.CTkButton] = []
        self._include_vars: dict[str, tk.BooleanVar] = {a: tk.BooleanVar(value=False) for a in ACCOUNTS}
        self._famafa_compras_by_account: dict[str, Path] | None = None
        self._status_state: dict[str, str] = {a: "idle" for a in ACCOUNTS}
        self._folder_loaded = False
        self._running = False
        self._spinner_angle = 0
        self._spinner_tick_id: str | None = None
        self._run_status_tick_id: str | None = None
        self._run_status_phase = 0

        self._path_entries: dict[str, ctk.CTkEntry] = {}
        self._status_dot_canvases: dict[str, tk.Canvas] = {}
        self._status_text_labels: dict[str, ctk.CTkLabel] = {}
        self._status_name_labels: dict[str, ctk.CTkLabel] = {}
        self._browse_buttons: list[ctk.CTkButton] = []
        self._summary_rows_var = tk.StringVar(value="")
        self._summary_match_var = tk.StringVar(value="")
        self._summary_pending_var = tk.StringVar(value="")
        self._summary_pending_ledger_var = tk.StringVar(value="")
        self._summary_pending_system_var = tk.StringVar(value="")
        self._summary_details_var = tk.StringVar(value="")
        self._run_status_var = tk.StringVar(value="")
        self._summary_details_visible = False
        self._controls_while_running: list[ctk.CTkBaseClass] = []
        self._live_log_handler: _TkLogHandler | None = None
        self._log_queue: queue.Queue[str] = queue.Queue(maxsize=5000)
        self._log_poll_id: str | None = None
        self._batch_job: BatchSubprocessJob | None = None
        self._batch_poll_id: str | None = None
        self._log_file_offset: int = 0
        self._audit_file_offset: int = 0
        self._active_run_cfg: RunConfig | None = None
        self._run_job_total = 0

        self._build()
        apply_widget_theme(self._shell, self._colors)
        apply_window_icon(self, _ROOT)
        self._apply_window_geometry(center=True, force_resize=True)
        self._bind_layout_refresh()
        self._apply_language()
        self._wire_path_traces()
        self.bind("<Return>", self._on_run_key)
        ensure_src_on_path()

        if self.var_insumos.get().strip():
            self.after(150, lambda: self._start_folder_scan(self.var_insumos.get().strip(), quiet=True))
        self._refresh_status_board()

    def tr(self, key: str, **kwargs: str) -> str:
        return t(key, self._lang, **kwargs)

    def _wire_path_traces(self) -> None:
        for k, v in (
            ("salida", self.var_salida),
            ("insumos", self.var_insumos),
            ("sql", self.var_sql),
            ("fc", self.var_fc),
            ("fv", self.var_fv),
        ):
            v.trace_add("write", lambda *_args, key=k: self._sync_path_entry(key))
        for acc in ACCOUNTS:
            self._ledger_vars[acc].trace_add("write", lambda *_args, a=acc: self._sync_path_entry(f"ledger_{a}"))
        for key in self._path_entries:
            self._sync_path_entry(key)

    def _sync_discovered_paths(self) -> None:
        for key in ("sql", "fc", "fv"):
            self._sync_path_entry(key)
        for acc in ACCOUNTS:
            self._sync_path_entry(f"ledger_{acc}")

    def _sync_path_entry(self, key: str) -> None:
        entry = self._path_entries.get(key)
        if entry is None:
            return
        if key == "salida":
            full = self.var_salida.get()
        elif key == "insumos":
            full = self.var_insumos.get()
        elif key == "sql":
            full = self.var_sql.get()
        elif key == "fc":
            full = self.var_fc.get()
        elif key == "fv":
            full = self.var_fv.get()
        elif key.startswith("ledger_"):
            acc = key.split("_", 1)[1]
            full = self._ledger_vars[acc].get()
        else:
            full = ""
        entry.configure(state="normal")
        entry.delete(0, tk.END)
        entry.insert(0, _truncate_path(full))
        entry.configure(state="disabled")
        _attach_tooltip(entry, full, colors=self._colors)

    def _build(self) -> None:
        self._shell = ctk.CTkFrame(self, fg_color=self._colors.bg)
        self._shell.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)
        root = self._shell
        root.grid_columnconfigure(0, weight=1)
        root.grid_rowconfigure(0, weight=1)

        body = ctk.CTkFrame(root, fg_color="transparent")
        body.grid(row=0, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=4)
        body.grid_rowconfigure(0, weight=1)

        self.left_card = ctk.CTkScrollableFrame(
            body,
            fg_color=self._colors.surface,
            corner_radius=12,
            border_width=1,
            border_color=self._colors.border,
        )
        self.left_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self._build_left_card(self.left_card)

        self.right_card = ctk.CTkFrame(
            body,
            fg_color=self._colors.surface,
            corner_radius=12,
            border_width=1,
            border_color=self._colors.border,
        )
        self.right_card.grid(row=0, column=1, sticky="nsew")
        self._build_right_card(self.right_card)

    def _subtle_card_fg(self) -> str:
        return self._colors.card

    def _make_folder_button(self, parent: ctk.CTkFrame, command: Callable[[], None]) -> ctk.CTkButton:
        btn = ctk.CTkButton(
            parent,
            text="📁",
            width=40,
            fg_color="transparent",
            border_width=1,
            border_color=self._colors.border,
            text_color=self._colors.text,
            hover_color=self._colors.accent_light,
            command=command,
        )
        self._browse_buttons.append(btn)
        return btn

    def _build_left_card(self, parent: ctk.CTkFrame) -> None:
        parent.grid_columnconfigure(0, weight=1)

        card_pad = {"padx": 14, "sticky": "ew"}

        self.lbl_panel_inputs = ctk.CTkLabel(
            parent, text="", font=ctk.CTkFont("Segoe UI", 18, "bold")
        )
        self.lbl_panel_inputs.grid(row=0, column=0, sticky="w", padx=14, pady=(12, 10))

        self.paths_box = ctk.CTkFrame(parent, fg_color="transparent")
        self.paths_box.grid(row=1, column=0, **card_pad, pady=(0, 8))
        self.paths_box.grid_columnconfigure(1, weight=1)

        self.lbl_output = ctk.CTkLabel(self.paths_box, text="", anchor="w")
        self.lbl_output.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 4))
        self.entry_salida = ctk.CTkEntry(self.paths_box)
        self.entry_salida.grid(row=1, column=1, sticky="ew", padx=(0, 8), pady=(0, 10))
        self._path_entries["salida"] = self.entry_salida
        self.btn_output = self._make_folder_button(self.paths_box, self._pick_output_folder)
        self.btn_output.grid(row=1, column=2, sticky="e", pady=(0, 10))

        self.lbl_input = ctk.CTkLabel(self.paths_box, text="", anchor="w")
        self.lbl_input.grid(row=2, column=0, columnspan=3, sticky="w", pady=(0, 4))
        self.entry_insumos = ctk.CTkEntry(self.paths_box)
        self.entry_insumos.grid(row=3, column=1, sticky="ew", padx=(0, 8))
        self._path_entries["insumos"] = self.entry_insumos
        self.btn_input = self._make_folder_button(self.paths_box, self._pick_insumos_folder)
        self.btn_input.grid(row=3, column=2, sticky="e")

        self.dates_box = ctk.CTkFrame(parent, fg_color=self._subtle_card_fg(), corner_radius=6)
        self.dates_box.grid(row=2, column=0, **card_pad, pady=(0, 8))
        self.dates_box.grid_columnconfigure(1, weight=1)
        self.dates_box.grid_columnconfigure(3, weight=1)
        self.lbl_dates = ctk.CTkLabel(self.dates_box, text="", anchor="w")
        self.lbl_dates.grid(row=0, column=0, columnspan=4, sticky="ew", padx=10, pady=(10, 6))
        self.lbl_from = ctk.CTkLabel(self.dates_box, text="")
        self.lbl_from.grid(row=1, column=0, sticky="w", padx=(10, 8), pady=(0, 10))
        self.entry_fd = ctk.CTkEntry(self.dates_box, textvariable=self.var_fd)
        self.entry_fd.grid(row=1, column=1, sticky="ew", padx=(0, 12), pady=(0, 10))
        self.lbl_to = ctk.CTkLabel(self.dates_box, text="")
        self.lbl_to.grid(row=1, column=2, sticky="w", padx=(0, 8), pady=(0, 10))
        self.entry_fh = ctk.CTkEntry(self.dates_box, textvariable=self.var_fh)
        self.entry_fh.grid(row=1, column=3, sticky="ew", padx=(0, 10), pady=(0, 10))

        self.advanced_box = ctk.CTkFrame(parent, fg_color=self._colors.card, corner_radius=6)
        self.advanced_box.grid(row=3, column=0, **card_pad, pady=(0, 8))
        self.advanced_box.grid_columnconfigure(1, weight=1)
        self.lbl_adv_section = ctk.CTkLabel(self.advanced_box, text="", anchor="w")
        self.lbl_adv_section.grid(row=0, column=0, columnspan=3, sticky="ew", padx=10, pady=(10, 6))
        self._build_advanced(self.advanced_box)

        run_box = ctk.CTkFrame(parent, fg_color="transparent")
        run_box.grid(row=4, column=0, **card_pad, pady=(8, 0))
        run_box.grid_columnconfigure(0, weight=1)

        options_frame = ctk.CTkFrame(run_box, fg_color="transparent")
        options_frame.grid(row=0, column=0, sticky="ew", padx=(10, 0), pady=(0, 10))
        options_frame.grid_columnconfigure(0, weight=1)
        self.switch_verbose = ctk.CTkSwitch(options_frame, text="", variable=self.var_verbose)
        self.switch_verbose.grid(row=0, column=0, sticky="w", pady=(0, 6))

        self.btn_run = make_primary_button(run_box, self._colors, text="", command=self._on_run)
        self.btn_run.configure(
            height=44,
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
        )
        self.btn_run.grid(row=1, column=0, sticky="ew", pady=(0, 12))

        self._controls_while_running.extend(
            [
                self.btn_output,
                self.btn_input,
                self.switch_verbose,
                self.entry_fd,
                self.entry_fh,
            ]
        )

    def _build_advanced(self, parent: ctk.CTkFrame) -> None:
        parent.grid_columnconfigure(1, weight=1)
        parent.grid_columnconfigure(2, minsize=40)
        pad_x = 10
        row_pady = 6

        self.lbl_adv_mayor = ctk.CTkLabel(parent, text="", anchor="w")
        self.lbl_adv_mayor.grid(
            row=1, column=0, columnspan=3, sticky="ew", padx=pad_x, pady=(0, 6)
        )

        def add_file_row(
            row: int, lbl: ctk.CTkLabel, entry: ctk.CTkEntry, browse_btn: ctk.CTkButton
        ) -> int:
            lbl.grid(row=row, column=0, sticky="w", padx=(pad_x, 8), pady=row_pady)
            entry.grid(row=row, column=1, sticky="ew", padx=(0, 8), pady=row_pady)
            browse_btn.grid(row=row, column=2, sticky="e", padx=(0, pad_x), pady=row_pady)
            return row + 1

        self.lbl_sql = ctk.CTkLabel(parent, text="", anchor="w")
        e_sql = ctk.CTkEntry(parent)
        self._path_entries["sql"] = e_sql
        b_sql = self._make_folder_button(parent, self._browse_sql)
        next_row = add_file_row(2, self.lbl_sql, e_sql, b_sql)

        self.lbl_fc = ctk.CTkLabel(parent, text="", anchor="w")
        e_fc = ctk.CTkEntry(parent)
        self._path_entries["fc"] = e_fc
        b_fc = self._make_folder_button(parent, self._browse_fc)
        next_row = add_file_row(next_row, self.lbl_fc, e_fc, b_fc)

        self.lbl_fv = ctk.CTkLabel(parent, text="", anchor="w")
        e_fv = ctk.CTkEntry(parent)
        self._path_entries["fv"] = e_fv
        b_fv = self._make_folder_button(parent, self._browse_fv)
        next_row = add_file_row(next_row, self.lbl_fv, e_fv, b_fv)

        self.lbl_tol_1279 = ctk.CTkLabel(parent, text="", anchor="w")
        self.entry_tol_1279 = ctk.CTkEntry(parent, textvariable=self.var_tol_1279)
        self.lbl_tol_1279.grid(row=next_row, column=0, sticky="w", padx=(pad_x, 8), pady=row_pady)
        self.entry_tol_1279.grid(row=next_row, column=1, sticky="ew", padx=(0, 8), pady=row_pady)
        ctk.CTkFrame(parent, width=40, height=1, fg_color="transparent").grid(
            row=next_row, column=2, padx=(0, pad_x), pady=row_pady
        )
        next_row += 1

        self.chk_include: dict[str, ctk.CTkCheckBox] = {}
        self.lbl_mayor_paths: dict[str, ctk.CTkEntry] = {}
        for i, acc in enumerate(ACCOUNTS):
            row_pad = (row_pady, 10) if i == len(ACCOUNTS) - 1 else row_pady
            chk = ctk.CTkCheckBox(
                parent,
                text=account_label(acc, self._lang),
                variable=self._include_vars[acc],
                command=self._on_include_changed,
            )
            chk.grid(row=next_row, column=0, sticky="w", padx=(pad_x, 4), pady=row_pad)
            self.chk_include[acc] = chk
            ent = ctk.CTkEntry(parent)
            ent.grid(row=next_row, column=1, sticky="ew", padx=(0, 8), pady=row_pad)
            self._path_entries[f"ledger_{acc}"] = ent
            self.lbl_mayor_paths[acc] = ent
            btn = self._make_folder_button(parent, lambda a=acc: self._browse_mayor(a))
            btn.grid(row=next_row, column=2, sticky="e", padx=(0, pad_x), pady=row_pad)
            self._controls_while_running.append(btn)
            next_row += 1

        self._controls_while_running.extend([b_sql, b_fc, b_fv, self.entry_tol_1279])

    def _build_right_card(self, parent: ctk.CTkFrame) -> None:
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(4, weight=1)
        card_pad = {"padx": 14, "sticky": "ew"}
        summary_item_pady = (3, 3)
        card_fg = self._subtle_card_fg()

        self.lbl_right_title = ctk.CTkLabel(
            parent, text="", font=ctk.CTkFont("Segoe UI", 18, "bold")
        )
        self.lbl_right_title.grid(row=0, column=0, sticky="w", padx=14, pady=(12, 8))

        self.btn_settings = ctk.CTkButton(
            parent,
            text="\u2699",
            width=40,
            height=40,
            font=ctk.CTkFont(size=20),
            fg_color=self._colors.accent_light,
            text_color=self._colors.text,
            hover_color=self._colors.secondary_hover,
            corner_radius=10,
            command=self._open_settings,
        )
        self.btn_settings.grid(row=0, column=0, sticky="e", padx=14, pady=(10, 8))
        _attach_tooltip(self.btn_settings, self.tr("settings_gear_tooltip"), colors=self._colors)
        self._controls_while_running.append(self.btn_settings)

        self.status_board = ctk.CTkFrame(parent, fg_color=card_fg, corner_radius=6)
        self.status_board.grid(row=1, column=0, **card_pad, pady=(0, 8))
        self.status_board.grid_columnconfigure(1, weight=1)
        self.lbl_status_summary = ctk.CTkLabel(self.status_board, text="")
        self.lbl_status_summary.grid(row=0, column=0, columnspan=3, sticky="w", padx=10, pady=(10, 8))
        for i, acc in enumerate(ACCOUNTS, start=1):
            dot = tk.Canvas(self.status_board, width=12, height=12, highlightthickness=0, bg=card_fg)
            dot.grid(row=i, column=0, padx=(10, 8), pady=5, sticky="w")
            txt = ctk.CTkLabel(self.status_board, text=account_label(acc, self._lang), anchor="w")
            txt.grid(row=i, column=1, sticky="w", pady=5)
            st = ctk.CTkLabel(self.status_board, text="")
            st.grid(row=i, column=2, sticky="e", padx=(8, 10), pady=5)
            self._status_dot_canvases[acc] = dot
            self._status_name_labels[acc] = txt
            self._status_text_labels[acc] = st

        self.summary_box = ctk.CTkFrame(parent, fg_color=card_fg, corner_radius=6)
        self.summary_box.grid(row=2, column=0, **card_pad, pady=(0, 8))
        self.summary_box.grid_remove()
        self.lbl_summary_title = ctk.CTkLabel(self.summary_box, text="", font=ctk.CTkFont("Segoe UI", 13, "bold"))
        self.lbl_summary_title.pack(anchor="w", padx=10, pady=(10, 4))
        ctk.CTkLabel(self.summary_box, textvariable=self._summary_rows_var).pack(
            anchor="w", padx=10, pady=summary_item_pady
        )
        ctk.CTkLabel(self.summary_box, textvariable=self._summary_match_var).pack(
            anchor="w", padx=10, pady=summary_item_pady
        )
        ctk.CTkLabel(self.summary_box, textvariable=self._summary_pending_var).pack(
            anchor="w", padx=10, pady=summary_item_pady
        )
        ctk.CTkLabel(self.summary_box, textvariable=self._summary_pending_ledger_var).pack(
            anchor="w", padx=10, pady=summary_item_pady
        )
        ctk.CTkLabel(self.summary_box, textvariable=self._summary_pending_system_var).pack(
            anchor="w", padx=10, pady=summary_item_pady
        )
        self.btn_summary_details = ctk.CTkButton(
            self.summary_box,
            text="",
            fg_color=self._colors.bg,
            text_color=self._colors.text,
            hover_color=self._colors.secondary_hover,
            command=self._toggle_summary_details,
            height=28,
            width=140,
        )
        self.btn_summary_details.pack(anchor="w", padx=10, pady=(8, 4))
        self._secondary_buttons.append(self.btn_summary_details)
        self.lbl_summary_details = ctk.CTkLabel(
            self.summary_box,
            textvariable=self._summary_details_var,
            justify="left",
            anchor="w",
            wraplength=440,
        )
        self.lbl_summary_details.pack(anchor="w", padx=10, pady=(0, 10))
        self.lbl_summary_details.pack_forget()

        self.progress_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.progress_frame.grid(row=3, column=0, **card_pad, pady=(0, 8))
        self.progress_frame.grid_columnconfigure(1, weight=1)
        self._spinner_canvas = tk.Canvas(
            self.progress_frame,
            width=18,
            height=18,
            highlightthickness=0,
            bg=self._colors.surface,
        )
        self.lbl_run_status = ctk.CTkLabel(
            self.progress_frame, textvariable=self._run_status_var, anchor="w"
        )
        self.progress = ctk.CTkProgressBar(self.progress_frame, height=10)
        self.progress.set(0)
        self.progress.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        self.progress.grid_remove()
        self.progress_frame.grid_remove()

        self.log_wrapper = ctk.CTkFrame(parent, fg_color=card_fg, corner_radius=6)
        self.log_wrapper.grid(row=4, column=0, sticky="nsew", padx=14, pady=(0, 10))
        self.log_wrapper.grid_columnconfigure(0, weight=1)
        self.log_wrapper.grid_rowconfigure(0, weight=1)
        self.txt = ctk.CTkTextbox(self.log_wrapper, font=ctk.CTkFont("Segoe UI", 11))
        self.txt.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        self.txt.configure(state="disabled")

        self.btn_open_output = ctk.CTkButton(
            parent,
            text="",
            fg_color="transparent",
            border_width=1,
            border_color=self._colors.border,
            text_color=self._colors.text,
            hover_color=self._colors.accent_light,
            command=self._open_salida,
            height=48,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            corner_radius=10,
        )
        self.btn_open_output.grid(row=5, column=0, **card_pad, pady=(0, 12))
        self._ghost_buttons.append(self.btn_open_output)
        self._controls_while_running.append(self.btn_open_output)

    def _toggle_summary_details(self) -> None:
        self._summary_details_visible = not self._summary_details_visible
        if self._summary_details_visible:
            self.lbl_summary_details.pack(anchor="w", padx=10, pady=(0, 8))
        else:
            self.lbl_summary_details.pack_forget()
        self._apply_language()

    def _open_settings(self) -> None:
        if self._running:
            return
        res = show_settings_dialog(
            self,
            self,
            app_root=_ROOT,
            lang=self._lang,
            appearance=self._appearance,
            colors=self._colors,
        )
        if res is None:
            return
        self._apply_settings(res)

    def _apply_settings(self, res: SettingsResult) -> None:
        prev_appearance = self._appearance
        self._lang = normalize_language(res.language)
        self._appearance = normalize_appearance(res.appearance)
        save_settings(
            _ROOT,
            language=self._lang,
            appearance=self._appearance,
        )
        if self._appearance != prev_appearance:
            self._apply_theme()
        self._apply_language()
        _attach_tooltip(self.btn_settings, self.tr("settings_gear_tooltip"), colors=self._colors)
        folder = self.var_insumos.get().strip()
        if folder:
            self._apply_folder(folder, quiet=True)

    def _apply_window_geometry(
        self,
        preset_id: str | None = None,
        *,
        force_resize: bool = True,
        center: bool = False,
    ) -> None:
        preset = get_window_preset(preset_id or self._window_preset)
        self._window_preset = preset.preset_id
        self.minsize(preset.min_width, preset.min_height)
        self.update_idletasks()
        sw = int(self.winfo_screenwidth())
        sh = int(self.winfo_screenheight())
        current = parse_window_geometry(self.geometry())
        geo = format_window_geometry(
            preset,
            screen_width=sw,
            screen_height=sh,
            current=current,
            center=center,
            force_resize=force_resize,
        )
        self.geometry(geo)
        self.update_idletasks()

    def _bind_layout_refresh(self) -> None:
        self.bind("<Configure>", self._on_window_configure, add="+")

    def _on_window_configure(self, event: tk.Event) -> None:
        if event.widget is not self:
            return
        self._update_summary_wraplength()

    def _update_summary_wraplength(self) -> None:
        try:
            w = max(220, self.right_card.winfo_width() - 48)
            self.lbl_summary_details.configure(wraplength=w)
        except tk.TclError:
            pass

    def _apply_theme(self) -> None:
        self._colors = apply_theme(self._appearance)
        self.configure(fg_color=self._colors.bg)
        self._shell.configure(fg_color=self._colors.bg)
        self.left_card.configure(fg_color=self._colors.surface, border_color=self._colors.border)
        self.right_card.configure(fg_color=self._colors.surface, border_color=self._colors.border)
        card_fg = self._colors.card
        self.dates_box.configure(fg_color=card_fg)
        self.advanced_box.configure(fg_color=card_fg)
        for btn in self._browse_buttons:
            btn.configure(
                fg_color="transparent",
                border_color=self._colors.border,
                text_color=self._colors.text,
                hover_color=self._colors.accent_light,
            )
        self.status_board.configure(fg_color=card_fg)
        self.log_wrapper.configure(fg_color=card_fg)
        self.summary_box.configure(fg_color=card_fg)
        self.btn_settings.configure(
            fg_color=self._colors.accent_light,
            text_color=self._colors.text,
            hover_color=self._colors.secondary_hover,
        )
        self.btn_run.configure(
            fg_color=self._colors.primary,
            hover_color=self._colors.primary_hover,
            text_color="#ffffff",
            height=44,
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
        )
        for btn in self._secondary_buttons:
            btn.configure(
                fg_color=self._colors.accent_light,
                text_color=self._colors.text,
                hover_color=self._colors.secondary_hover,
            )
        for btn in self._ghost_buttons:
            btn.configure(
                fg_color="transparent",
                border_width=1,
                border_color=self._colors.border,
                text_color=self._colors.text,
                hover_color=self._colors.accent_light,
            )
        self.btn_summary_details.configure(
            fg_color=self._colors.accent_light,
            text_color=self._colors.text,
            hover_color=self._colors.secondary_hover,
        )
        for switch in (self.switch_verbose,):
            switch.configure(
                text_color=self._colors.text,
                progress_color=self._colors.primary,
                button_color="#f4f6f8",
                button_hover_color="#ffffff",
                fg_color=self._colors.border,
            )
        for dot in self._status_dot_canvases.values():
            dot.configure(bg=card_fg)
        self._spinner_canvas.configure(bg=self._colors.surface)
        if self._running:
            self._draw_run_spinner()
        apply_widget_theme(self._shell, self._colors)
        self._refresh_status_board()
        self._update_summary_wraplength()

    def _apply_language(self) -> None:
        self.title(self.tr("app_title"))
        self.lbl_panel_inputs.configure(text=self.tr("panel_inputs"))
        _attach_tooltip(self.btn_output, self.tr("btn_choose_output"), colors=self._colors)
        _attach_tooltip(self.btn_input, self.tr("btn_choose_input"), colors=self._colors)
        for btn in getattr(self, "_browse_buttons", []):
            _attach_tooltip(btn, self.tr("btn_browse"), colors=self._colors)
        self.lbl_output.configure(text=self.tr("step1_frame"))
        self.lbl_input.configure(text=self.tr("step2_frame"))
        self.lbl_dates.configure(text=self.tr("date_section"))
        self.lbl_from.configure(text=self.tr("date_from"))
        self.lbl_to.configure(text=self.tr("date_to"))
        self.switch_verbose.configure(text=self.tr("verbose_log"))
        self.lbl_adv_section.configure(text=self.tr("adv_section"))
        self.btn_run.configure(text=self.tr("btn_run") if not self._running else self.tr("btn_run_busy"))
        self.btn_open_output.configure(text=self.tr("btn_open_output"))
        self.lbl_right_title.configure(text=self.tr("log_frame").strip())
        self.lbl_status_summary.configure(
            text=self.tr("status_summary", ready=str(self._ready_count()), total=str(len(ACCOUNTS)))
            if self._folder_loaded
            else ""
        )
        self.lbl_summary_title.configure(text=self.tr("summary_title"))
        self.btn_summary_details.configure(
            text=self.tr("hide_details") if self._summary_details_visible else self.tr("show_details")
        )
        self.lbl_adv_mayor.configure(text=self.tr("adv_mayor"))
        self.lbl_sql.configure(text=self.tr("adv_sql"))
        self.lbl_fc.configure(text=self.tr("adv_fc"))
        self.lbl_fv.configure(text=self.tr("adv_fv"))
        self.lbl_tol_1279.configure(text=self.tr("adv_tol_1279"))
        for acc in ACCOUNTS:
            self.chk_include[acc].configure(text=account_label(acc, self._lang))
            if acc in self._status_name_labels:
                self._status_name_labels[acc].configure(text=account_label(acc, self._lang))
        _attach_tooltip(self.btn_settings, self.tr("settings_gear_tooltip"), colors=self._colors)
        self._refresh_status_board()

    def _ready_count(self) -> int:
        return sum(1 for a in ACCOUNTS if self._status_state[a] == "ready")

    def _refresh_status_board(self) -> None:
        if self._folder_loaded:
            self.lbl_status_summary.configure(
                text=self.tr("status_summary", ready=str(self._ready_count()), total=str(len(ACCOUNTS)))
            )
        else:
            self.lbl_status_summary.configure(text="")
        for acc in ACCOUNTS:
            state = self._status_state[acc]
            dot = self._status_dot_canvases[acc]
            st = self._status_text_labels[acc]
            dot.delete("all")
            if state == "ready":
                color = self._colors.success
                text = self.tr("status_ready")
            elif state == "error":
                color = self._colors.error
                text = self.tr("status_not_found")
            elif state == "running":
                color = self._colors.primary
                text = self.tr("btn_run_busy")
            else:
                color = self._colors.text_muted
                text = self.tr("status_not_loaded")
            dot.create_oval(1, 1, 11, 11, fill=color, outline=color)
            st.configure(text=text)

    def _draw_run_spinner(self) -> None:
        c = self._spinner_canvas
        c.delete("all")
        pad = 2
        size = 16
        c.create_arc(
            pad,
            pad,
            size,
            size,
            start=self._spinner_angle,
            extent=300,
            outline=self._colors.primary,
            width=2,
            style=tk.ARC,
        )

    def _animate_run_spinner(self) -> None:
        if not self._running:
            self._spinner_tick_id = None
            return
        self._spinner_angle = (self._spinner_angle + 28) % 360
        self._draw_run_spinner()
        self._spinner_tick_id = self.after(70, self._animate_run_spinner)

    def _show_run_progress_ui(self) -> None:
        self.progress_frame.grid()
        self._spinner_canvas.grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.lbl_run_status.grid(row=0, column=1, sticky="ew")
        self.progress.grid()
        if self._spinner_tick_id is None:
            self._animate_run_spinner()

    def _hide_run_progress_ui(self) -> None:
        if self._spinner_tick_id is not None:
            self.after_cancel(self._spinner_tick_id)
            self._spinner_tick_id = None
        self.progress.grid_remove()
        self.progress_frame.grid_remove()

    def _set_progress_value(self, value: float) -> None:
        try:
            self.progress.set(min(max(float(value), 0.0), 1.0))
        except (tk.TclError, ValueError):
            pass

    def _count_finished_jobs(self) -> int:
        return sum(
            1
            for acc in ACCOUNTS
            if self._include_vars[acc].get() and self._status_state[acc] in ("ready", "error")
        )

    def _refresh_run_progress(self) -> None:
        if not self._running:
            return
        total = max(self._run_job_total, 1)
        done = self._count_finished_jobs()
        phase: str | None = None
        job = self._batch_job
        if job is not None and job.result_path.is_file():
            try:
                phase = str(read_result_json(job.result_path).get("phase") or "")
            except (OSError, json.JSONDecodeError):
                phase = None
        if phase == "uat":
            value = 0.92
        elif phase in ("done", "failed"):
            value = 1.0
        elif phase == "starting":
            value = 0.12
        elif job is None:
            value = 0.06
        else:
            value = 0.12 + 0.78 * (done / total)
        self._set_progress_value(value)

    def _set_running_ui(self, running: bool, *, status_tick: bool = True) -> None:
        self._running = running
        self.btn_run.configure(state="disabled" if running else "normal")
        for ctrl in self._controls_while_running:
            ctrl.configure(state="disabled" if running else "normal")
        if running:
            self._set_progress_value(0.0)
            self._show_run_progress_ui()
            if status_tick:
                self._run_status_phase = 0
                self._tick_running_status()
        else:
            self._set_progress_value(0.0)
            self._hide_run_progress_ui()
            if self._run_status_tick_id is not None:
                self.after_cancel(self._run_status_tick_id)
                self._run_status_tick_id = None
            self._run_status_var.set("")
        self.btn_run.configure(text=self.tr("btn_run_busy") if running else self.tr("btn_run"))

    def _tick_running_status(self) -> None:
        if not self._running:
            self._run_status_var.set("")
            self._run_status_tick_id = None
            return
        msgs = (
            self.tr("run_status_preparing"),
            self.tr("run_status_matching"),
            self.tr("run_status_writing"),
        )
        self._run_status_var.set(msgs[self._run_status_phase % len(msgs)])
        self._run_status_phase += 1
        self._run_status_tick_id = self.after(1200, self._tick_running_status)

    def _on_include_changed(self) -> None:
        self._update_dates_visibility()

    def _update_dates_visibility(self) -> None:
        if self._include_vars["1279"].get() and self._ledger_vars["1279"].get().strip():
            self.dates_box.grid()
        else:
            self.dates_box.grid_remove()

    def _pick_output_folder(self) -> None:
        _browse_dir(self.var_salida, self.tr("dialog_output_dir"))

    def _browse_sql(self) -> None:
        _browse_file(self.var_sql, self.tr("dialog_sql"), file_types(self._lang))

    def _browse_fc(self) -> None:
        _browse_file(self.var_fc, self.tr("dialog_fc"), file_types(self._lang))

    def _browse_fv(self) -> None:
        _browse_file(self.var_fv, self.tr("dialog_fv"), file_types(self._lang))

    def _browse_mayor(self, acc: str) -> None:
        _browse_file(self._ledger_vars[acc], self.tr("dialog_mayor", label=account_label(acc, self._lang)), mayor_file_types(self._lang))
        self._update_dates_visibility()

    def _pick_insumos_folder(self) -> None:
        default = self.var_insumos.get().strip() or str((project_root().parent / "Automatización conciliaciones").resolve())
        folder = filedialog.askdirectory(
            title=self.tr("dialog_input_dir"),
            initialdir=default if Path(default).is_dir() else None,
        )
        if folder:
            self.var_insumos.set(folder)
            self._start_folder_scan(folder)

    def _set_status(self, acc: str, state: str) -> None:
        self._status_state[acc] = state
        self._refresh_status_board()

    def _start_folder_scan(self, folder: str, *, quiet: bool = False) -> None:
        path = Path(folder).resolve()
        if not path.is_dir():
            if not quiet:
                messagebox.showerror(self.tr("err_generic"), self.tr("err_folder_missing", path=str(path)))
            return
        if not quiet:
            self._clear_log()
            self._log(self.tr("log_folder_scanning"))

        def work() -> None:
            discovered = discover_inputs(path)
            self.after(0, lambda: self._apply_discovered(discovered, quiet=quiet))

        threading.Thread(target=work, daemon=True).start()

    def _apply_folder(self, folder: str, *, quiet: bool = False) -> None:
        """Synchronous folder apply (tests); GUI uses _start_folder_scan."""
        path = Path(folder).resolve()
        if not path.is_dir():
            if not quiet:
                messagebox.showerror(self.tr("err_generic"), self.tr("err_folder_missing", path=str(path)))
            return
        self._apply_discovered(discover_inputs(path), quiet=quiet)

    def _apply_discovered(self, discovered: DiscoveredInputs, *, quiet: bool = False) -> None:
        path = discovered.root
        self._famafa_compras_by_account = dict(discovered.famafa_compras)
        self._folder_loaded = True

        for acc in ACCOUNTS:
            self._include_vars[acc].set(False)
            self._status_state[acc] = "idle"

        for acc, led in discovered.ledgers.items():
            self._ledger_vars[acc].set(str(led.resolve()))
            self._include_vars[acc].set(True)
            self._set_status(acc, "ready")

        self.var_sql.set(str(discovered.sql_1279.resolve()) if discovered.sql_1279 else "")
        self.var_fv.set(str(discovered.famafa_ventas.resolve()) if discovered.famafa_ventas else "")
        if discovered.famafa_compras.get("469"):
            self.var_fc.set(str(discovered.famafa_compras["469"].resolve()))
        elif discovered.famafa_compras.get("1280"):
            self.var_fc.set(str(discovered.famafa_compras["1280"].resolve()))

        if "1279" in discovered.ledgers and not discovered.sql_1279:
            self._set_status("1279", "error")
        for acc in ("469", "1280"):
            if acc in discovered.ledgers and not discovered.famafa_compras.get(acc):
                self._set_status(acc, "error")
        if "2874" in discovered.ledgers and not discovered.famafa_ventas:
            self._set_status("2874", "error")

        if discovered.fecha_desde:
            self.var_fd.set(discovered.fecha_desde)
        if discovered.fecha_hasta:
            self.var_fh.set(discovered.fecha_hasta)

        self._sync_discovered_paths()
        self._update_dates_visibility()
        save_settings(
            _ROOT,
            insumos=str(path),
            salida=self.var_salida.get(),
            fecha_desde=self.var_fd.get(),
            fecha_hasta=self.var_fh.get(),
            language=self._lang,
            appearance=self._appearance,
        )
        if not quiet:
            self._clear_log()
            self._log(self.tr("log_folder_loaded", path=str(path)))
            self._log(self.tr("log_accounts_ready", n=str(sum(1 for a in ACCOUNTS if self._include_vars[a].get())), total=str(len(ACCOUNTS))))

    def _log(self, msg: str) -> None:
        self._append_log_lines([msg])

    def _append_log_lines(self, lines: list[str], *, scroll: bool = True) -> None:
        if not lines:
            return
        self.txt.configure(state="normal")
        self.txt.insert("end", "\n".join(lines) + "\n")
        if scroll:
            self.txt.see("end")
        try:
            end_index = self.txt.index("end-1c")
            line_count = int(str(end_index).split(".")[0])
            if line_count > _MAX_LOG_LINES:
                trim_to = line_count - _MAX_LOG_LINES
                self.txt.delete("1.0", f"{trim_to}.0")
        except (tk.TclError, ValueError):
            pass
        self.txt.configure(state="disabled")

    def _clear_log(self) -> None:
        self.txt.configure(state="normal")
        self.txt.delete("1.0", "end")
        self.txt.configure(state="disabled")

    def _attach_live_log_handler(self) -> None:
        if self._live_log_handler is not None:
            return
        handler = _TkLogHandler(self._log_queue)
        handler.setLevel(logging.INFO)
        handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
        root = logging.getLogger()
        root.addHandler(handler)
        self._live_log_handler = handler
        if self._log_poll_id is None:
            self._log_poll_id = self.after(_LOG_POLL_MS, self._poll_live_logs)

    def _poll_live_logs(self) -> None:
        lines: list[str] = []
        for _ in range(_LOG_BATCH_MAX):
            try:
                lines.append(self._log_queue.get_nowait())
            except queue.Empty:
                break
        if lines:
            self._append_log_lines(lines, scroll=True)
        self._log_poll_id = self.after(_LOG_POLL_MS, self._poll_live_logs)

    def _flush_live_logs(self) -> None:
        lines: list[str] = []
        while True:
            try:
                lines.append(self._log_queue.get_nowait())
            except queue.Empty:
                break
        if lines:
            self._append_log_lines(lines)

    def _detach_live_log_handler(self) -> None:
        if self._log_poll_id is not None:
            self.after_cancel(self._log_poll_id)
            self._log_poll_id = None
        self._flush_live_logs()
        if self._live_log_handler is None:
            return
        root = logging.getLogger()
        try:
            root.removeHandler(self._live_log_handler)
        finally:
            self._live_log_handler.close()
            self._live_log_handler = None

    def _stop_batch_monitor(self) -> None:
        if self._batch_poll_id is not None:
            self.after_cancel(self._batch_poll_id)
            self._batch_poll_id = None
        self._batch_job = None
        self._log_file_offset = 0
        self._audit_file_offset = 0

    def _begin_batch_monitor(self, job: BatchSubprocessJob) -> None:
        self._stop_batch_monitor()
        self._batch_job = job
        self._log_file_offset = 0
        self._audit_file_offset = 0
        cfg = self._active_run_cfg
        self._run_job_total = len(cfg.jobs) if cfg else 1
        self._set_progress_value(0.1)
        self._poll_batch_progress()

    def _tail_log_file(self, path: Path) -> None:
        if not self.var_verbose.get():
            return
        if not path.is_file():
            return
        try:
            with path.open("r", encoding="utf-8", errors="replace") as fh:
                fh.seek(self._log_file_offset)
                chunk = fh.read()
                self._log_file_offset = fh.tell()
        except OSError:
            return
        if not chunk:
            return
        lines = [ln for ln in chunk.splitlines() if ln.strip()]
        if lines:
            self._append_log_lines(lines, scroll=True)

    def _tail_audit_file(self, path: Path) -> None:
        if not path.is_file():
            return
        try:
            with path.open("r", encoding="utf-8", errors="replace") as fh:
                fh.seek(self._audit_file_offset)
                chunk = fh.read()
                self._audit_file_offset = fh.tell()
        except OSError:
            return
        if not chunk:
            return
        for line in chunk.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            acc = row.get("account")
            stage = row.get("stage")
            if isinstance(acc, str):
                if stage == "ui_job_ok":
                    self._set_status(acc, "ready")
                    self._refresh_run_progress()
                elif stage == "ui_job_failed":
                    self._set_status(acc, "error")
                    self._refresh_run_progress()
            if not self.var_verbose.get():
                msg = format_audit_activity(row, lang=self._lang)
                if msg:
                    self._append_log_lines([msg], scroll=True)

    def _poll_batch_progress(self) -> None:
        job = self._batch_job
        if job is None:
            return
        self._tail_log_file(job.log_path)
        self._tail_audit_file(job.audit_path)
        if job.result_path.is_file():
            try:
                phase = read_result_json(job.result_path).get("phase")
                if phase == "uat":
                    self._run_status_var.set(self.tr("run_status_uat"))
            except (OSError, json.JSONDecodeError):
                pass
        self._refresh_run_progress()
        if job.process.poll() is None:
            self._batch_poll_id = self.after(150, self._poll_batch_progress)

    def _uat_from_dict(self, row: dict) -> UATVariance:
        return UATVariance(
            account=str(row["account"]),
            model_path=Path(row["model_path"]) if row.get("model_path") else None,
            output_path=Path(row["output_path"]),
            model_total=int(row.get("model_total") or 0),
            output_total=int(row.get("output_total") or 0),
            model_matched=int(row.get("model_matched") or 0),
            output_matched=int(row.get("output_matched") or 0),
            delta_total=int(row.get("delta_total") or 0),
            delta_matched=int(row.get("delta_matched") or 0),
            status=str(row.get("status") or ""),
            detail=str(row.get("detail") or ""),
        )

    def _result_from_dict(self, row: dict) -> AccountRunResult:
        out = row.get("output")
        return AccountRunResult(
            account=str(row["account"]),
            ok=bool(row.get("ok")),
            output=Path(out) if out else None,
            error=row.get("error"),
            error_code=row.get("error_code"),
            metrics=row.get("metrics") or {},
        )

    def _finalize_batch(self, job: BatchSubprocessJob, returncode: int) -> None:
        self._tail_log_file(job.log_path)
        self._tail_audit_file(job.audit_path)
        self._set_progress_value(1.0)
        self._stop_batch_monitor()
        if not job.result_path.is_file():
            self._finish_run_error(
                RuntimeError(self.tr("err_worker_no_result", path=str(job.result_path)))
            )
            return
        data = read_result_json(job.result_path)
        if returncode != 0 or not data.get("ok"):
            err = data.get("error") or f"Worker exit code {returncode}"
            self._finish_run_error(RuntimeError(str(err)))
            return
        cfg = self._active_run_cfg
        if cfg is None:
            self._finish_run_error(RuntimeError("Run configuration unavailable after batch"))
            return
        results = [self._result_from_dict(r) for r in data.get("results") or []]
        qa_rows = [self._uat_from_dict(r) for r in data.get("qa_rows") or []]
        qa_report = Path(data["qa_report_path"]) if data.get("qa_report_path") else None
        self._finish_run_success(
            cfg=cfg,
            run_id=str(data.get("run_id") or job.run_id),
            log_path=Path(data.get("log_path") or job.log_path),
            results=results,
            qa_rows=qa_rows,
            qa_report_path=qa_report,
        )

    def _collect_jobs(self) -> list[AccountJob]:
        jobs: list[AccountJob] = []
        for acc in ACCOUNTS:
            if not self._include_vars[acc].get():
                continue
            p = self._ledger_vars[acc].get().strip().strip('"')
            if p:
                jobs.append(AccountJob(account=acc, ledger_path=Path(p).expanduser().resolve()))
        return jobs

    def _collect_cfg(self) -> RunConfig | None:
        sal = self.var_salida.get().strip().strip('"')
        if not sal:
            return None
        salida = Path(sal).expanduser().resolve()
        jobs = self._collect_jobs()
        has_1279 = any(j.account == "1279" for j in jobs)
        tol_raw = self.var_tol_1279.get().strip() or "0.01"
        try:
            tol_1279 = float(tol_raw)
        except ValueError as e:
            raise ValueError(self.tr("err_tol_invalid")) from e
        if tol_1279 < 0:
            raise ValueError(self.tr("err_tol_negative"))

        def p(s: str) -> Path | None:
            s = s.strip().strip('"')
            return Path(s).expanduser().resolve() if s else None

        return RunConfig(
            salida=salida,
            jobs=jobs,
            sql_csv=p(self.var_sql.get()),
            famafa_compras=p(self.var_fc.get()),
            famafa_compras_by_account=self._famafa_compras_by_account,
            famafa_ventas=p(self.var_fv.get()),
            fecha_desde=self.var_fd.get().strip() or None,
            fecha_hasta=self.var_fh.get().strip() or None,
            amount_tolerance_1279=tol_1279 if has_1279 else 0.0,
        )

    def _show_summary(self, results: list[object]) -> None:
        ok_n = sum(1 for r in results if getattr(r, "ok", False))
        total = len(results)
        matched = 0
        pending = 0
        pending_ledger = 0
        pending_system = 0
        details_rows: list[str] = []
        for r in results:
            metrics = getattr(r, "metrics", {}) or {}
            m = int(metrics.get("matched_rows") or 0)
            ul = int(metrics.get("unmatched_ledger_rows") or 0)
            us = int(metrics.get("unmatched_system_rows") or 0)
            matched += m
            pending += ul + us
            pending_ledger += ul
            pending_system += us
            label = account_label(getattr(r, "account", ""), self._lang)
            integrity = (
                self.tr("summary_integrity_ok")
                if metrics.get("integrity_ok", True)
                else self.tr("summary_integrity_failed")
            )
            details_rows.append(
                self.tr(
                    "summary_account_line",
                    label=label,
                    matched=str(m),
                    ledger=str(ul),
                    system=str(us),
                    integrity=integrity,
                )
            )
        self._summary_rows_var.set(self.tr("summary_rows", ok=str(ok_n), total=str(total)))
        self._summary_match_var.set(self.tr("summary_matched", n=str(matched)))
        self._summary_pending_var.set(self.tr("summary_unmatched", n=str(pending)))
        self._summary_pending_ledger_var.set(self.tr("summary_pending_ledger", n=str(pending_ledger)))
        self._summary_pending_system_var.set(self.tr("summary_pending_system", n=str(pending_system)))
        self._summary_details_var.set("\n".join(details_rows))
        self._summary_details_visible = False
        self.lbl_summary_details.pack_forget()
        self.summary_box.grid()

    def _call_on_ui_and_wait(self, fn: Callable[[], _T]) -> _T:
        """Run *fn* on the Tk main loop from a worker thread and block until it returns."""
        result: list[_T] = []
        done = threading.Event()

        def wrapper() -> None:
            try:
                result.append(fn())
            finally:
                done.set()

        self.after(0, wrapper)
        done.wait()
        return result[0]

    def _finish_run_cancelled(self) -> None:
        self._stop_batch_monitor()
        self._detach_live_log_handler()
        self._set_running_ui(False)
        self._active_run_cfg = None

    def _finish_run_error(self, exc: BaseException) -> None:
        self._stop_batch_monitor()
        self._detach_live_log_handler()
        self._set_running_ui(False)
        self._active_run_cfg = None
        self._log(f"ERROR: {exc}")
        messagebox.showerror(self.tr("err_generic"), str(exc))

    def _defer_log_lines(
        self,
        lines: list[str],
        *,
        start: int = 0,
        chunk: int = 10,
        on_done: Callable[[], None] | None = None,
    ) -> None:
        end = min(start + chunk, len(lines))
        if start < end:
            self._append_log_lines(lines[start:end], scroll=(end >= len(lines)))
        if end < len(lines):
            self.after(40, lambda: self._defer_log_lines(lines, start=end, chunk=chunk, on_done=on_done))
        elif on_done is not None:
            on_done()

    def _finish_run_success(
        self,
        cfg: RunConfig,
        *,
        run_id: str,
        log_path: Path,
        results: list[AccountRunResult],
        qa_rows: list[UATVariance],
        qa_report_path: Path | None,
    ) -> None:
        self._stop_batch_monitor()
        self._detach_live_log_handler()
        self._set_running_ui(False)
        self._active_run_cfg = None
        self._show_summary(results)
        ok_n = sum(1 for r in results if r.ok)
        for r in results:
            if r.ok and r.output:
                self._set_status(r.account, "ready")
            elif r.error:
                self._set_status(r.account, "error")

        verbose = self.var_verbose.get()
        if verbose:
            lines = [
                self.tr("log_done", ok=str(ok_n), total=str(len(results))),
                self.tr("log_file", path=str(log_path)),
                self.tr(
                    "log_manifest",
                    path=str(cfg.salida / "logs" / f"run_manifest_{run_id}.json"),
                ),
            ]
            for r in results:
                label = account_label(r.account, self._lang)
                if r.ok and r.output:
                    lines.append(self.tr("log_account_ok", label=label, name=r.output.name))
                elif r.error:
                    lines.append(self.tr("log_account_err", label=label, err=r.error or ""))
            if qa_rows:
                lines.append(self.tr("log_qa_header"))
                for row in qa_rows:
                    if row.status == "missing_model":
                        lines.append(
                            self.tr(
                                "log_qa_missing_model",
                                account=row.account,
                                detail=row.detail,
                            )
                        )
                    else:
                        lines.append(
                            self.tr(
                                "log_qa_row",
                                account=row.account,
                                dt=str(row.delta_total),
                                dm=str(row.delta_matched),
                                status=row.status,
                            )
                        )
                if qa_report_path:
                    lines.append(self.tr("log_qa_report", path=str(qa_report_path)))
        else:
            lines = [
                self.tr("activity_run_done", ok=str(ok_n), total=str(len(results))),
                self.tr("activity_log_saved"),
            ]
            for r in results:
                label = account_label(r.account, self._lang)
                if r.error:
                    lines.append(self.tr("activity_account_err", label=label, err=r.error or ""))

        def show_dialog() -> None:
            if ok_n:
                messagebox.showinfo(
                    self.tr("msg_success_title"),
                    self.tr("msg_success", n=str(ok_n), path=str(cfg.salida)),
                )
            else:
                messagebox.showwarning(self.tr("msg_warn_title"), self.tr("msg_warn_none"))

        self._defer_log_lines(lines, on_done=show_dialog)

    def _on_run_key(self, _event: object) -> str:
        if self._running:
            return "break"
        self._on_run()
        return "break"

    def _on_run(self) -> None:
        if self._running:
            return
        try:
            cfg = self._collect_cfg()
        except ValueError as e:
            messagebox.showerror(self.tr("err_generic"), str(e))
            return
        if cfg is None:
            messagebox.showerror(self.tr("err_generic"), self.tr("err_output_required"))
            return
        if not cfg.jobs:
            messagebox.showerror(self.tr("err_generic"), self.tr("err_no_accounts"))
            return

        save_settings(
            _ROOT,
            salida=self.var_salida.get(),
            insumos=self.var_insumos.get(),
            fecha_desde=self.var_fd.get(),
            fecha_hasta=self.var_fh.get(),
            amount_tolerance_1279=self.var_tol_1279.get(),
            language=self._lang,
            appearance=self._appearance,
        )

        self._set_running_ui(True, status_tick=False)
        self._clear_log()
        self._log(self.tr("log_validating"))
        self._run_status_var.set(self.tr("run_status_validating"))
        self._set_progress_value(0.05)

        def work() -> None:
            try:
                validation = validate_run_config(cfg, lang=self._lang, include_precheck=True)
                proceed = self._call_on_ui_and_wait(
                    lambda: show_validation_dialog(self, self, validation, lang=self._lang)
                )
                if not proceed:
                    self.after(0, self._finish_run_cancelled)
                    return

                ui_ready = threading.Event()

                def prepare() -> None:
                    self._active_run_cfg = cfg
                    self.summary_box.grid_remove()
                    self._clear_log()
                    self._log(self.tr("log_running"))
                    if self.var_verbose.get():
                        self._log(self.tr("log_output", path=str(cfg.salida)))
                    for acc in ACCOUNTS:
                        if self._include_vars[acc].get():
                            self._status_state[acc] = "running"
                    self._refresh_status_board()
                    self._run_job_total = len(cfg.jobs)
                    self._refresh_run_progress()
                    self._run_status_phase = 0
                    self._tick_running_status()
                    ui_ready.set()

                self.after(0, prepare)
                ui_ready.wait()

                models_root: Path | None = None
                insumos = self.var_insumos.get().strip().strip('"')
                if insumos:
                    models_root = Path(insumos).expanduser()
                job = start_batch_subprocess(
                    _ROOT,
                    cfg,
                    verbose=self.var_verbose.get(),
                    skip_input_validation=True,
                    uat_verify=resolve_run_uat(_ROOT),
                    models_root=models_root,
                )
                self.after(0, lambda: self._begin_batch_monitor(job))
                returncode = job.process.wait()
                self.after(0, lambda: self._finalize_batch(job, returncode))
            except Exception as e:
                self.after(0, lambda: self._finish_run_error(e))

        threading.Thread(target=work, daemon=True).start()

    def _open_salida(self) -> None:
        sal = self.var_salida.get().strip().strip('"')
        if not sal:
            messagebox.showinfo(self.tr("info_title"), self.tr("info_output_first"))
            return
        p = Path(sal).expanduser().resolve()
        p.mkdir(parents=True, exist_ok=True)
        try:
            if sys.platform == "win32":
                os.startfile(str(p))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.run(["open", str(p)], check=False)
            else:
                subprocess.run(["xdg-open", str(p)], check=False)
        except OSError as e:
            messagebox.showerror(self.tr("err_generic"), str(e))


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Conciliacion de credito fiscal (escritorio)")
    parser.add_argument(
        "--run-uat",
        action="store_true",
        help="Comparar salida con modelos CUADRE dorados en insumos (desarrollo/QA)",
    )
    args, _unknown = parser.parse_known_args()
    if args.run_uat:
        os.environ["RECONCILIATION_RUN_UAT"] = "1"
    init_windows_app_identity()
    app = ConciliationApp()
    app.mainloop()


if __name__ == "__main__":
    main()

"""UI strings for desktop app (Spanish default, English optional)."""

from __future__ import annotations

DEFAULT_LANGUAGE = "es"
OUTPUT_LANGUAGE = "es"
SUPPORTED_LANGUAGES = ("es", "en")

# key -> {es, en}
_MESSAGES: dict[str, dict[str, str]] = {
    "app_title": {
        "es": "Conciliacion de credito fiscal",
        "en": "Tax credit reconciliation",
    },
    "header_title": {
        "es": "Conciliacion de credito fiscal",
        "en": "Tax credit reconciliation",
    },
    "header_steps": {
        "es": "1) Elija donde guardar los Excel  |  2) Cargue la carpeta del mes  |  3) Genere la conciliacion",
        "en": "1) Choose output folder  |  2) Load month folder  |  3) Run reconciliation",
    },
    "header_steps_short": {
        "es": "Guarde los Excel, cargue la carpeta del mes y genere la conciliacion.",
        "en": "Save Excel output, load the month folder, and run reconciliation.",
    },
    "language_label": {"es": "Idioma:", "en": "Language:"},
    "panel_inputs": {"es": "Insumos", "en": "Inputs"},
    "step_prog_1": {"es": "Salida", "en": "Output"},
    "step_prog_2": {"es": "Mes", "en": "Month"},
    "step_prog_3": {"es": "Ejecutar", "en": "Run"},
    "step1_frame": {"es": " Paso 1 - Carpeta de salida (resultados) ", "en": " Step 1 - Output folder (results) "},
    "step1_help": {
        "es": "Aqui se guardan los archivos CUADRE_*.xlsx y la carpeta logs con el registro de cada ejecucion.",
        "en": "CUADRE_*.xlsx files and the logs folder are saved here.",
    },
    "btn_choose_output": {"es": "Elegir carpeta de salida...", "en": "Choose output folder..."},
    "dialog_output_dir": {
        "es": "Carpeta donde guardar los Excel generados",
        "en": "Folder to save generated Excel files",
    },
    "step2_frame": {"es": " Paso 2 - Archivos del mes ", "en": " Step 2 - Month files "},
    "step2_help": {
        "es": "Seleccione la carpeta del mes con mayorpc, SQL y/o exportes FAMAFA (Compras y Ventas). "
        "Ejemplo: Automatizacion conciliaciones",
        "en": "Select the month folder with mayorpc, SQL and/or FAMAFA exports (Purchases and Sales). "
        "Example: Automatizacion conciliaciones",
    },
    "btn_choose_input": {"es": "Elegir carpeta de archivos...", "en": "Choose input folder..."},
    "dialog_input_dir": {
        "es": "Carpeta con archivos del mes",
        "en": "Month input folder",
    },
    "status_summary": {"es": "{ready} de {total} listos", "en": "{ready} of {total} ready"},
    "status_ready": {"es": "Listo", "en": "Ready"},
    "status_not_loaded": {"es": "(sin cargar)", "en": "(not loaded)"},
    "status_not_found": {"es": "(no encontrado)", "en": "(not found)"},
    "status_missing_sql": {"es": "Falta archivo SQL", "en": "Missing SQL file"},
    "status_missing_fc": {"es": "Falta FAMAFA Compras", "en": "Missing FAMAFA Purchases"},
    "status_missing_fv": {"es": "Falta FAMAFA Ventas", "en": "Missing FAMAFA Sales"},
    "status_mayor": {"es": "Mayor: {name}", "en": "Ledger: {name}"},
    "status_mayor_sql": {"es": "Mayor + SQL: {name}", "en": "Ledger + SQL: {name}"},
    "status_mayor_famafa": {"es": "Mayor + FAMAFA: {name}", "en": "Ledger + FAMAFA: {name}"},
    "adv_section": {
        "es": "Archivos por tipo de conciliacion",
        "en": "Files by reconciliation type",
    },
    "step3_frame": {"es": " Paso 3 - Ejecutar ", "en": " Step 3 - Run "},
    "date_section": {
        "es": "NC emitidas (SQL) — rango de fechas",
        "en": "Issued credit notes (SQL) — date range",
    },
    "date_from": {"es": "Desde", "en": "From"},
    "date_to": {"es": "Hasta", "en": "To"},
    "sql_date_hint": {
        "es": "SQL: {desde} – {hasta} ({days} dia(s){rows_part})",
        "en": "SQL: {desde} – {hasta} ({days} day(s){rows_part})",
    },
    "sql_date_hint_empty": {
        "es": "Seleccione un archivo SQL para ver el rango de fechas.",
        "en": "Select a SQL file to see its date range.",
    },
    "btn_use_sql_dates": {
        "es": "Usar fechas del SQL",
        "en": "Use SQL date range",
    },
    "btn_solo_ultimo_dia": {
        "es": "Solo ultimo dia SQL",
        "en": "SQL last day only",
    },
    "log_sql_last_day_applied": {
        "es": "Rango 1279: solo ultimo dia SQL ({day})",
        "en": "1279 range: SQL last day only ({day})",
    },
    "sql_date_hint_preset": {
        "es": " Sugiera 'Solo ultimo dia SQL' si concilia como el modelo manual.",
        "en": " Try 'SQL last day only' if matching the manual model.",
    },
    "sql_date_rows_suffix": {
        "es": ", {count} filas",
        "en": ", {count} rows",
    },
    "log_sql_dates_applied": {
        "es": "Rango 1279 actualizado desde SQL: {desde} – {hasta}",
        "en": "1279 range updated from SQL: {desde} – {hasta}",
    },
    "verbose_log": {"es": "Log detallado", "en": "Detailed log"},
    "btn_browse": {"es": "Examinar...", "en": "Browse..."},
    "btn_run": {"es": "Generar conciliacion", "en": "Run reconciliation"},
    "btn_run_busy": {"es": "Generando...", "en": "Running..."},
    "run_status_validating": {"es": "Validando archivos...", "en": "Validating files..."},
    "run_status_preparing": {"es": "Preparando insumos...", "en": "Preparing input files..."},
    "log_validating": {"es": "Validando insumos antes de conciliar...", "en": "Validating inputs before reconciliation..."},
    "log_folder_scanning": {"es": "Buscando archivos en la carpeta...", "en": "Scanning folder for input files..."},
    "run_status_matching": {"es": "Conciliando registros...", "en": "Matching records..."},
    "run_status_writing": {"es": "Escribiendo CUADRE...", "en": "Writing CUADRE workbook..."},
    "run_status_uat": {"es": "Verificando calculos (UAT)...", "en": "Verifying calculations (UAT)..."},
    "run_progress_counter": {
        "es": "Cuenta {current} de {total}",
        "en": "Account {current} of {total}",
    },
    "summary_title": {"es": "Resumen final", "en": "Final summary"},
    "summary_rows": {"es": "Tipos completados: {ok}/{total}", "en": "Completed types: {ok}/{total}"},
    "summary_matched": {"es": "Filas conciliadas: {n}", "en": "Matched rows: {n}"},
    "summary_unmatched": {"es": "Filas pendientes: {n}", "en": "Unmatched rows: {n}"},
    "summary_pending_ledger": {"es": "Pendientes en Mayor: {n}", "en": "Pending in Ledger: {n}"},
    "summary_pending_system": {"es": "Pendientes en Sistema: {n}", "en": "Pending in System: {n}"},
    "summary_integrity_ok": {"es": "Integridad: OK", "en": "Integrity: OK"},
    "summary_integrity_failed": {"es": "Integridad: revise filas", "en": "Integrity: check rows"},
    "summary_model_title": {
        "es": "Comparacion vs modelo CUADRE",
        "en": "Comparison vs golden CUADRE model",
    },
    "summary_model_ok": {
        "es": "{label}: {engine} conciliadas = modelo ({model})",
        "en": "{label}: {engine} matched = model ({model})",
    },
    "summary_model_variance": {
        "es": "{label}: {engine} conciliadas vs {model} modelo (delta {delta:+d})",
        "en": "{label}: {engine} matched vs {model} model (delta {delta:+d})",
    },
    "summary_model_missing": {
        "es": "{label}: sin modelo CUADRE de referencia",
        "en": "{label}: no golden CUADRE model found",
    },
    "summary_account_line": {
        "es": "{label}: {matched} / {ledger} / {system} — {integrity}",
        "en": "{label}: {matched} / {ledger} / {system} — {integrity}",
    },
    "show_details": {"es": "Expandir detalles", "en": "Expand details"},
    "hide_details": {"es": "Ocultar detalles", "en": "Hide details"},
    "show_log": {"es": "Mostrar actividad", "en": "Show activity"},
    "hide_log": {"es": "Ocultar actividad", "en": "Hide activity"},
    "btn_open_output": {"es": "Abrir carpeta de salida", "en": "Open output folder"},
    "btn_open_cuadre": {"es": "Abrir CUADRE", "en": "Open CUADRE"},
    "err_cuadre_missing": {
        "es": "No se encontro el archivo CUADRE para {label}.",
        "en": "CUADRE file not found for {label}.",
    },
    "opt_469_amount_only": {
        "es": "469: cruce solo por importe (modo manual)",
        "en": "469: match by amount only (manual mode)",
    },
    "log_frame": {"es": " Actividad ", "en": " Activity "},
    "adv_sql": {"es": "SQL / Excel (NC emitidas)", "en": "SQL / Excel (issued credit notes)"},
    "adv_fc": {"es": "FAMAFA Compras", "en": "FAMAFA Purchases"},
    "adv_fv": {"es": "FAMAFA Ventas", "en": "FAMAFA Sales"},
    "adv_tol_1279": {
        "es": "Tolerancia de monto 1279 (ej. 0.01)",
        "en": "1279 amount tolerance (e.g. 0.01)",
    },
    "adv_mayor": {"es": "Mayor por tipo de conciliacion (.txt)", "en": "Ledger per reconciliation type (.txt)"},
    "dialog_sql": {"es": "Archivo SQL / Excel", "en": "SQL / Excel file"},
    "dialog_fc": {"es": "FAMAFA Compras", "en": "FAMAFA Purchases"},
    "dialog_fv": {"es": "FAMAFA Ventas", "en": "FAMAFA Sales"},
    "dialog_mayor": {"es": "Mayor - {label}", "en": "Ledger - {label}"},
    "file_csv_excel": {"es": "CSV / Excel", "en": "CSV / Excel"},
    "file_all": {"es": "Todos", "en": "All files"},
    "file_mayor": {"es": "Mayor texto", "en": "Ledger text"},
    "err_folder_missing": {"es": "No existe la carpeta:\n{path}", "en": "Folder does not exist:\n{path}"},
    "err_output_required": {
        "es": "Indique donde guardar los archivos Excel (Paso 1).",
        "en": "Choose where to save Excel files (Step 1).",
    },
    "err_no_accounts": {
        "es": "No hay conciliaciones listas.\n\nUse Paso 2: Elegir carpeta de archivos...",
        "en": "No reconciliations ready.\n\nUse Step 2: Choose input folder...",
    },
    "err_validation_title": {"es": "Revise los archivos", "en": "Check input files"},
    "warn_validation_title": {"es": "Advertencias de validacion", "en": "Validation warnings"},
    "warn_continue": {
        "es": "Se detectaron advertencias:\n\n{details}\n\nPuede continuar, pero revise el periodo y los archivos.\n\nDesea continuar?",
        "en": "Validation warnings were detected:\n\n{details}\n\nYou can continue, but review period and files.\n\nContinue anyway?",
    },
    "err_generic": {"es": "Error", "en": "Error"},
    "err_worker_no_result": {
        "es": "El proceso de conciliacion no genero resultado: {path}",
        "en": "Reconciliation process did not produce a result file: {path}",
    },
    "err_tol_invalid": {
        "es": "La tolerancia de monto 1279 debe ser numerica (ej. 0.01).",
        "en": "1279 amount tolerance must be numeric (e.g. 0.01).",
    },
    "err_tol_negative": {
        "es": "La tolerancia de monto 1279 debe ser mayor o igual a 0.",
        "en": "1279 amount tolerance must be greater than or equal to 0.",
    },
    "info_output_first": {
        "es": "Primero elija la carpeta de salida (Paso 1).",
        "en": "Choose the output folder first (Step 1).",
    },
    "info_title": {"es": "Info", "en": "Info"},
    "log_folder_loaded": {"es": "Carpeta cargada: {path}", "en": "Folder loaded: {path}"},
    "log_accounts_ready": {
        "es": "Tipos listos: {n} de {total}",
        "en": "Reconciliation types ready: {n} of {total}",
    },
    "log_running": {"es": "Generando conciliacion...", "en": "Running reconciliation..."},
    "activity_run_start": {
        "es": "Iniciando {n} tipos de conciliacion...",
        "en": "Starting {n} reconciliation types...",
    },
    "activity_account_start": {"es": "Conciliando {label}...", "en": "Reconciling {label}..."},
    "activity_account_done": {
        "es": "{label}: {matched} conciliadas, {pending} pendientes",
        "en": "{label}: {matched} matched, {pending} pending",
    },
    "activity_integrity_ok": {
        "es": "{label}: integridad de filas OK",
        "en": "{label}: row integrity OK",
    },
    "activity_integrity_failed": {
        "es": "{label}: integridad — revise el CUADRE",
        "en": "{label}: integrity issue — review CUADRE",
    },
    "activity_account_ok": {"es": "{label}: listo", "en": "{label}: done"},
    "activity_account_err": {"es": "{label}: {err}", "en": "{label}: {err}"},
    "activity_run_done": {
        "es": "Proceso finalizado ({ok}/{total} tipos).",
        "en": "Process finished ({ok}/{total} types).",
    },
    "activity_log_saved": {
        "es": "Registro completo en la carpeta logs de salida.",
        "en": "Full log saved in the output logs folder.",
    },
    "activity_unknown_error": {"es": "Error desconocido", "en": "Unknown error"},
    "log_output": {"es": "Salida: {path}", "en": "Output: {path}"},
    "log_done": {"es": "Finalizado ({ok}/{total} tipos).", "en": "Finished ({ok}/{total} types)."},
    "log_file": {"es": "Log: {path}", "en": "Log: {path}"},
    "log_manifest": {"es": "Manifiesto: {path}", "en": "Manifest: {path}"},
    "log_account_ok": {"es": "  {label}: {name}", "en": "  {label}: {name}"},
    "log_account_err": {"es": "  {label}: ERROR: {err}", "en": "  {label}: ERROR: {err}"},
    "log_qa_header": {"es": "Comparacion vs modelo CUADRE:", "en": "Comparison vs golden CUADRE model:"},
    "log_qa_row_friendly": {
        "es": "  {label}: motor {engine} / modelo {model} conciliadas ({status})",
        "en": "  {label}: engine {engine} / model {model} matched ({status})",
    },
    "log_qa_missing_model": {
        "es": "  Cuenta {account}: SIN MODELO ({detail})",
        "en": "  Account {account}: MODEL MISSING ({detail})",
    },
    "log_qa_row": {
        "es": "  Cuenta {account}: estado={status}, delta_total={dt}, delta_conciliadas={dm}",
        "en": "  Account {account}: status={status}, delta_total={dt}, delta_matched={dm}",
    },
    "log_qa_report": {"es": "Reporte QA: {path}", "en": "QA report: {path}"},
    "msg_success_title": {"es": "Listo", "en": "Done"},
    "msg_success": {
        "es": "Se generaron {n} archivo(s) en:\n{path}\n\nUse Abrir carpeta de salida para ver los Excel.",
        "en": "Generated {n} file(s) in:\n{path}\n\nUse Open output folder to view Excel files.",
    },
    "msg_warn_title": {"es": "Atencion", "en": "Warning"},
    "msg_warn_none": {
        "es": "Ninguna conciliacion termino correctamente. Revise Actividad.",
        "en": "No reconciliation completed successfully. Check Activity.",
    },
    "val_no_jobs": {
        "es": "Seleccione al menos un tipo con su archivo mayor (mayorpc).",
        "en": "Select at least one reconciliation type with its ledger file (mayorpc).",
    },
    "val_ledger_missing": {
        "es": "{label}: no existe el archivo mayor: {path}",
        "en": "{label}: ledger file not found: {path}",
    },
    "val_sql_required": {
        "es": "NC emitidas (SQL) requiere un archivo SQL valido (CSV o Excel).",
        "en": "Issued credit notes (SQL) requires a valid SQL file (CSV or Excel).",
    },
    "val_fecha_desde": {
        "es": "NC emitidas (SQL) requiere fecha_desde (YYYY-MM-DD).",
        "en": "Issued credit notes (SQL) requires fecha_desde (YYYY-MM-DD).",
    },
    "val_fecha_hasta": {
        "es": "NC emitidas (SQL) requiere fecha_hasta (YYYY-MM-DD).",
        "en": "Issued credit notes (SQL) requires fecha_hasta (YYYY-MM-DD).",
    },
    "val_fc_required": {
        "es": "{label} requiere archivo FAMAFA Compras (CSV o Excel).",
        "en": "{label} requires FAMAFA Purchases file (CSV or Excel).",
    },
    "val_fv_required": {
        "es": "NC recibidas (Ventas) requiere archivo FAMAFA Ventas (CSV o Excel).",
        "en": "Received credit notes (Sales) requires FAMAFA Sales file (CSV or Excel).",
    },
    "val_date_invalid": {"es": "{detail}", "en": "{detail}"},
    "val_date_warn": {"es": "{detail}", "en": "{detail}"},
    "val_precheck_error": {"es": "{detail}", "en": "{detail}"},
    "val_precheck_warn": {"es": "{detail}", "en": "{detail}"},
    "validation_errors_intro": {
        "es": "Corrija los siguientes problemas antes de ejecutar:",
        "en": "Fix the following issues before running:",
    },
    "validation_warnings_intro": {
        "es": "Se detectaron advertencias. Puede continuar o cancelar:",
        "en": "Warnings were detected. You can continue or cancel:",
    },
    "validation_ok": {"es": "Cerrar", "en": "Close"},
    "validation_cancel": {"es": "Cancelar", "en": "Cancel"},
    "validation_continue": {"es": "Continuar", "en": "Continue"},
    "validation_section_general": {"es": "=== General ===", "en": "=== General ==="},
    "validation_section_account": {"es": "=== {label} ===", "en": "=== {label} ==="},
    "validation_section_warnings": {"es": "=== Advertencias ===", "en": "=== Warnings ==="},
    "settings_title": {"es": "Configuracion", "en": "Settings"},
    "settings_language": {"es": "Idioma de la interfaz", "en": "Interface language"},
    "settings_appearance": {"es": "Modo oscuro", "en": "Dark mode"},
    "settings_apply": {"es": "Aplicar", "en": "Apply"},
    "settings_cancel": {"es": "Cancelar", "en": "Cancel"},
    "settings_gear_tooltip": {"es": "Configuracion (idioma, tema)", "en": "Settings (language, theme)"},
}

_ACCOUNT_LABELS: dict[str, dict[str, str]] = {
    "1279": {
        "es": "NC emitidas (SQL)",
        "en": "Issued credit notes (SQL)",
    },
    "469": {
        "es": "IVA compras (FAMAFA Compras)",
        "en": "Purchase VAT (FAMAFA Purchases)",
    },
    "1280": {
        "es": "Retenciones exterior (FAMAFA Compras)",
        "en": "Foreign withholding (FAMAFA Purchases)",
    },
    "2874": {
        "es": "NC recibidas (FAMAFA Ventas)",
        "en": "Received credit notes (FAMAFA Sales)",
    },
}


_LANG_ES_DISPLAY = "Espa\u00f1ol"

LANG_DISPLAY_CHOICES = (_LANG_ES_DISPLAY, "English")
LANG_FROM_DISPLAY: dict[str, str] = {
    _LANG_ES_DISPLAY: "es",
    "Espanol": "es",
    "es": "es",
    "English": "en",
    "en": "en",
}
LANG_TO_DISPLAY: dict[str, str] = {"es": _LANG_ES_DISPLAY, "en": "English"}


def normalize_language(lang: str | None) -> str:
    if not lang or not str(lang).strip():
        return DEFAULT_LANGUAGE
    raw = str(lang).strip()
    if raw in LANG_FROM_DISPLAY:
        return LANG_FROM_DISPLAY[raw]
    low = raw.lower()
    if low in LANG_FROM_DISPLAY:
        return LANG_FROM_DISPLAY[low]
    if low.startswith("en"):
        return "en"
    return DEFAULT_LANGUAGE


def language_display_for(code: str | None) -> str:
    return LANG_TO_DISPLAY.get(normalize_language(code), _LANG_ES_DISPLAY)


def language_code_from_display(display: str) -> str:
    return LANG_FROM_DISPLAY.get(display, "es")


def t(key: str, lang: str = DEFAULT_LANGUAGE, **kwargs: str) -> str:
    lang = normalize_language(lang)
    entry = _MESSAGES.get(key, {})
    text = entry.get(lang) or entry.get("es") or key
    if kwargs:
        return text.format(**kwargs)
    return text


def account_label(account: str, lang: str = DEFAULT_LANGUAGE) -> str:
    lang = normalize_language(lang)
    entry = _ACCOUNT_LABELS.get(account, {})
    return entry.get(lang) or entry.get("es") or account


def account_label_output(account: str) -> str:
    """Account label for Excel, logs, and manifests (always Spanish)."""
    return account_label(account, OUTPUT_LANGUAGE)


def missing_message_keys(lang: str = "en") -> list[str]:
    """Return keys missing a translation for *lang* (for tests)."""
    lang = normalize_language(lang)
    missing: list[str] = []
    for key, entry in _MESSAGES.items():
        if lang not in entry and "es" not in entry:
            missing.append(key)
        elif lang not in entry:
            missing.append(key)
    return missing


def file_types(lang: str = DEFAULT_LANGUAGE) -> list[tuple[str, str]]:
    return [
        (t("file_csv_excel", lang), "*.csv;*.xlsx;*.xls"),
        (t("file_all", lang), "*.*"),
    ]


def mayor_file_types(lang: str = DEFAULT_LANGUAGE) -> list[tuple[str, str]]:
    return [
        (t("file_mayor", lang), "*.txt"),
        (t("file_all", lang), "*.*"),
    ]

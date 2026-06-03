# -*- mode: python ; coding: utf-8 -*-
"""
Spec PyInstaller: aplicacion de escritorio Windows (CustomTkinter).

Desde la carpeta reconciliation_engine:

    powershell -ExecutionPolicy Bypass -File scripts/build_exe.ps1

O (usa el Python actual; puede analizar muchos paquetes del sistema)::

    py -3 -m pip install -r requirements.txt -r requirements-build.txt
    py -3 -m PyInstaller scripts/conciliation.spec --clean

Salida: dist/ConciliacionCreditoFiscal/ConciliacionCreditoFiscal.exe
"""

import os

block_cipher = None

APP_NAME = "ConciliacionCreditoFiscal"

ROOT = os.path.abspath(os.path.join(os.path.dirname(SPEC), ".."))
SCRIPT = os.path.join(ROOT, "desktop", "conciliation_gui.py")
ICON = os.path.join(ROOT, "desktop", "assets", "app_icon.ico")

# Heavy packages often present in a global Python install; this app does not need them.
_EXCLUDES = [
    "torch",
    "torchvision",
    "torchaudio",
    "tensorflow",
    "tensorboard",
    "keras",
    "jax",
    "jaxlib",
    "scipy",
    "sklearn",
    "matplotlib",
    "IPython",
    "jupyter",
    "jupyterlab",
    "notebook",
    "nltk",
    "cv2",
    "av",
    "sqlalchemy",
    "django",
    "flask",
    "fastapi",
    "pytest",
    "numba",
    "llvmlite",
    "bokeh",
    "plotly",
    "sympy",
    "statsmodels",
    "pyarrow",
    "polars",
    "dask",
    "xarray",
    "transformers",
    "sentencepiece",
    "tiktoken",
    "openai",
    "langchain",
]

a = Analysis(
    [SCRIPT],
    pathex=[ROOT, os.path.join(ROOT, "src")],
    binaries=[],
    datas=[
        (os.path.join(ROOT, "config"), "config"),
        (os.path.join(ROOT, "desktop", "assets"), os.path.join("desktop", "assets")),
    ],
    hiddenimports=[
        "pipeline.run_reconciliation",
        "pipeline.logging_audit",
        "pipeline.errors",
        "ingestion.ledger_parser",
        "ingestion.system_imports",
        "ingestion.folder_discovery",
        "ingestion.validate_inputs",
        "rules.account_rules",
        "reconcile.matcher",
        "reporting.excel_writer",
        "reporting.cuadre_writer",
        "output_es",
        "output_es.messages",
        "config.account_config",
        "qa.integrity_check",
        "qa.uat_compare",
        "ui.app_identity",
        "ui.services",
        "ui.settings",
        "ui.i18n",
        "ui.uat_flags",
        "ui.activity_log",
        "ui.brand_icon",
        "ui.window_icon",
        "ui.settings_dialog",
        "ui.run_config_io",
        "ui.subprocess_batch",
        "ui.batch_worker",
        "ui.validation_dialog",
        "ui.widget_theme",
        "ui.window_presets",
        "customtkinter",
        "PIL",
        "PIL.Image",
        "PIL.ImageDraw",
        "yaml",
        "xlsxwriter",
        "openpyxl",
        "pandas",
        "numpy",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=_EXCLUDES,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON if os.path.isfile(ICON) else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=APP_NAME,
)

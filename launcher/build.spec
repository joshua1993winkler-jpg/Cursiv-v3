# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller build spec for Cursiv Launcher.

Usage (from repo root):
    pyinstaller launcher/build.spec

Output: dist/Cursiv/Cursiv.exe  (one-dir bundle, windowed)
"""

import sys
from pathlib import Path

ROOT = Path(SPECPATH).parent          # repo root (one level above launcher/)
LAUNCHER = ROOT / "launcher"
CURSIV   = ROOT / "cursiv_v215"
SERVICES = ROOT / "services"

block_cipher = None

# ── Data files bundled into the exe ──────────────────────────────────────────
datas = [
    # Icons
    (str(LAUNCHER / "resources" / "icons"), "launcher/resources/icons"),
    # cursiv_v215 package (everything — models, prompts, templates)
    (str(CURSIV), "cursiv_v215"),
    # Services (guardian_service standalone runner)
    (str(SERVICES), "services"),
]

# ── Hidden imports that PyInstaller static analysis misses ───────────────────
hiddenimports = [
    # cursiv_v215 sub-packages
    "cursiv_v215",
    "cursiv_v215.ui",
    "cursiv_v215.ui.chat_app",
    "cursiv_v215.ui.chat_cli",
    "cursiv_v215.core",
    "cursiv_v215.core.agent",
    "cursiv_v215.core.constitution",
    "cursiv_v215.core.memory",
    "cursiv_v215.core.rate_limiter",
    "cursiv_v215.core.scan_display",
    "cursiv_v215.core.strand",
    "cursiv_v215.guardian",
    "cursiv_v215.guardian.access_gate",
    "cursiv_v215.guardian.decoys",
    "cursiv_v215.guardian.obfuscation",
    "cursiv_v215.guardian.temple_guardian",
    "bcrypt",
    "cursiv_v215.memory",
    "cursiv_v215.runtime",
    "cursiv_v215.runtime.config",
    "cursiv_v215.runtime.db",
    "cursiv_v215.runtime.evolution_engine",
    "cursiv_v215.runtime.guardian",
    "cursiv_v215.runtime.metrics",
    "cursiv_v215.academy",
    "cursiv_v215.cli",
    "cursiv_v215.council",
    "cursiv_v215.dugout",
    "cursiv_v215.forge",
    "cursiv_v215.knowledge",
    "cursiv_v215.nexus",
    "cursiv_v215.obsidian",
    "cursiv_v215.weave",
    # launcher
    "cursiv_launcher",
    "login_dialog",
    "tray",
    # PyQt6
    "PyQt6",
    "PyQt6.QtWidgets",
    "PyQt6.QtCore",
    "PyQt6.QtGui",
    "PyQt6.sip",
    # Windows / system
    "win32api",
    "win32con",
    "win32gui",
    "win32event",
    "win32serviceutil",
    "win32service",
    "servicemanager",
    "psutil",
    "anthropic",
    "openai",
    "httpx",
    "PIL",
]

a = Analysis(
    [str(LAUNCHER / "main.py")],
    pathex=[str(ROOT), str(LAUNCHER)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter", "matplotlib", "scipy", "pandas", "IPython",
        # Heavy ML libs — not needed by launcher/chat UI; load separately at runtime
        "torch", "torchvision", "torchaudio",
        "tensorflow", "keras", "jax",
        "bitsandbytes",
        "transformers", "tokenizers", "datasets",
        "sentence_transformers",
        "sklearn", "xgboost", "lightgbm",
        "cv2", "skimage",
        # Jupyter / dev tools
        "notebook", "ipykernel", "ipywidgets",
        # Unused stdlib
        "unittest", "doctest", "pdb",
    ],
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
    name="Cursiv",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,                          # no terminal window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(LAUNCHER / "resources" / "icons" / "cursiv.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Cursiv",                          # output: dist\Cursiv\
)

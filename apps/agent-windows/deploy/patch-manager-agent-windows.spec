# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

project_root = Path(SPEC).resolve().parent.parent
agent_root = project_root / "agent"

a = Analysis(
    [str(agent_root / "service.py")],
    pathex=[str(agent_root)],
    binaries=[],
    datas=[],
    hiddenimports=[
        "api_client",
        "config",
        "executor",
        "inventory",
        "logger",
        "main",
        # pywin32 — necessario para Windows Service
        "win32service",
        "win32serviceutil",
        "win32event",
        "win32api",
        "win32con",
        "win32timezone",
        "servicemanager",
        "pywintypes",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="PatchManagerAgentWindows",
    debug=False,
    bootloader_ignore_signals=True,
    strip=False,
    upx=True,
    console=True,
)

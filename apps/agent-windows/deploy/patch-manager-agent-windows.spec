# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

project_root = Path(SPEC).resolve().parent.parent
agent_root = project_root / "agent"

a = Analysis(
    [str(agent_root / "main.py")],
    pathex=[str(agent_root)],
    binaries=[],
    datas=[],
    hiddenimports=["api_client", "config", "executor", "inventory", "logger"],
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
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
)

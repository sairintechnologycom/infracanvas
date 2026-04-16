# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for InfraCanvas CLI standalone binary."""

import os
from pathlib import Path

block_cipher = None

# Include security rules YAML files and viewer template
datas = [
    ('infracanvas/security/rules', 'infracanvas/security/rules'),
]

# Check if viewer dist exists (for HTML export template)
viewer_dist = Path('../viewer/dist')
if viewer_dist.exists():
    datas.append(('../viewer/dist', 'viewer/dist'))

a = Analysis(
    ['infracanvas/main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'infracanvas.parser.hcl',
        'infracanvas.parser.azure',
        'infracanvas.parser.plan',
        'infracanvas.parser.state',
        'infracanvas.parser.module',
        'infracanvas.parser.references',
        'infracanvas.graph.builder',
        'infracanvas.graph.models',
        'infracanvas.security.engine',
        'infracanvas.security.loader',
        'infracanvas.security.scorer',
        'infracanvas.security.staleness',
        'infracanvas.cost.estimator',
        'infracanvas.drift.analyzer',
        'infracanvas.export.html',
        'infracanvas.export.json',
        'infracanvas.export.scorecard',
        'infracanvas.config',
        'hcl2',
        'yaml',
        'pydantic',
        'typer',
        'rich',
        'networkx',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='infracanvas',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

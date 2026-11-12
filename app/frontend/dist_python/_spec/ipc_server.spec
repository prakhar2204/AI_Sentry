# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['D:/AI_Sentry/app/backend/ipc_server.py'],
    pathex=['D:/AI_Sentry/app/backend'],
    binaries=[],
    datas=[('D:/AI_Sentry/app/backend', 'backend')],
    hiddenimports=['core.manifest', 'core.engine_interface', 'core.engine_runner', 'core.mock_engine', 'core.scorer', 'core.recommender', 'core.report_generator', 'core.normalizer', 'core.adapters', 'core.adapters.garak_adapter', 'core.adapters.pyrit_adapter', 'core.validator', 'core.estimator', 'core.export_handler', 'json', 'pathlib', 'dataclasses', 'enum', 'uuid', 'time', 'datetime', 'httpx', 'certifi', 'anyio', 'sniffio', 'h11'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pytest', 'hypothesis', 'mypy', 'ruff', 'respx'],
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
    name='ipc_server',
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

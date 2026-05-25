# PyInstaller spec for Pacefinder.
# Builds a single-file (Linux) or .app bundle (macOS) from listener.py.
# Invoked by .github/workflows/release.yml on every release tag.
#
#   pyinstaller pacefinder.spec --clean --noconfirm
#
# Mac App Store signing/packaging happens in CI after this spec runs.

import os
import platform
import sys
from pathlib import Path

IS_MAC   = sys.platform == "darwin"
APP_NAME = "Pacefinder"
ENTRY    = "listener.py"

# Bundle every Python module not directly imported by listener.py so
# PyInstaller's dependency walker doesn't miss the lazily-loaded router pages.
hiddenimports = [
    "platformdirs",
    "db.store",
    "net.api", "net.perf", "net.router", "net.server", "net.sysinfo",
    "net.pages.admin", "net.pages.cars", "net.pages.circuits",
    "net.pages.dashboard", "net.pages.debug", "net.pages.events",
    "net.pages.home", "net.pages.sessions", "net.pages.setup",
    "net.pages.telemetry",
    "parsers.acc", "parsers.f1", "parsers.forza",
    "reference.loader",
    "session.manager", "session.protocol", "session.watchdog",
]

# Reference CSVs (data/) and the static asset tree (static/) must travel with
# the bundle — both are read at runtime via Path(__file__).parent / "<dir>".
datas = [
    ("data",   "data"),
    ("static", "static"),
]

block_cipher = None

a = Analysis(
    [ENTRY],
    pathex=[os.path.abspath(".")],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "test", "unittest", "pydoc"],
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
    name=APP_NAME.lower(),
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=not IS_MAC,           # .app needs windowed; Linux ELF stays console
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,        # signed in CI, not here
    entitlements_file=None,        # applied in CI codesign step
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=APP_NAME.lower(),
)

if IS_MAC:
    app = BUNDLE(
        coll,
        name=f"{APP_NAME}.app",
        icon="packaging/icons/pacefinder.icns" if Path("packaging/icons/pacefinder.icns").exists() else None,
        bundle_identifier="app.pacefinder.macos",
        # CFBundleShortVersionString must be three integers per Apple; use the
        # SHORT env var (PACEFINDER_VERSION with any -rcN suffix stripped) for
        # plist fields, and the full tag for filenames elsewhere.
        version=os.environ.get("PACEFINDER_VERSION_SHORT", os.environ.get("PACEFINDER_VERSION", "0.7.1")),
        info_plist={
            "CFBundleName":               APP_NAME,
            "CFBundleDisplayName":        APP_NAME,
            "CFBundleShortVersionString": os.environ.get("PACEFINDER_VERSION_SHORT", os.environ.get("PACEFINDER_VERSION", "0.7.1")),
            "CFBundleVersion":            os.environ.get("PACEFINDER_BUILD", "1"),
            "LSApplicationCategoryType":  "public.app-category.utilities",
            "LSMinimumSystemVersion":     "12.0",
            "LSUIElement":                False,
            "NSHighResolutionCapable":    True,
            "NSHumanReadableCopyright":   "© Woest Endeavours / Estetika",
        },
    )

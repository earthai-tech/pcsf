# PyInstaller spec of PCSF Studio: one-folder, windowed build.
#
# Build through installers/build.py, which also runs the frozen
# self-test; directly:
#
#   pyinstaller --noconfirm installers/pyinstaller/pcsf-studio.spec
#
# Output: dist/pcsf-studio/ (pcsf-studio.exe on Windows).
# Optional readers (netCDF4 for EMC files, triangle for MARE2DEM)
# are bundled when installed in the build environment.

import importlib.util
import os
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

ROOT = Path(SPECPATH).resolve().parents[1]  # noqa: F821 (PyInstaller)
ASSETS = ROOT / "installers" / "assets"

datas = collect_data_files(
    "pcsf",
    includes=["datasets/**/*", "schemas/*.json",
              "studio/resources/*", "py.typed"],
)
hidden = [
    "pcsf.adapters.emc",
    "pcsf.adapters.mare2dem",
    "pcsf.adapters.modem",
    "pcsf.adapters.occam2d",
]
for optional in ("netCDF4", "cftime", "triangle"):
    if importlib.util.find_spec(optional) is not None:
        hidden.append(optional)

# Qt modules PCSF Studio never uses; excluding them keeps the bundle
# small (QtWebEngine alone is about 200 MB).
excludes = [
    "tkinter",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebEngineQuick",
    "PySide6.Qt3DCore",
    "PySide6.Qt3DRender",
    "PySide6.QtMultimedia",
    "PySide6.QtQuick",
    "PySide6.QtQml",
    "PySide6.QtPdf",
    "PySide6.QtCharts",
    "PySide6.QtDataVisualization",
    "PySide6.QtBluetooth",
    "PySide6.QtLocation",
    "PySide6.QtPositioning",
    "PySide6.QtSensors",
    "PySide6.QtSerialPort",
    "PySide6.QtWebSockets",
    "IPython",
    "jupyter",
    "pytest",
]

a = Analysis(  # noqa: F821 (PyInstaller)
    [str(Path(SPECPATH) / "pcsf_studio_launcher.py")],  # noqa: F821
    pathex=[str(ROOT / "src")],
    datas=datas,
    hiddenimports=hidden,
    excludes=excludes,
    noarchive=False,
)
if sys.platform == "win32":
    # Qt 6 uses the ICU of Windows (System32\icuuc.dll); a conda ICU
    # of the same name in the bundle would shadow it.
    a.binaries = [
        b for b in a.binaries
        if not Path(b[0]).name.lower().startswith("icu")
    ]
pyz = PYZ(a.pure)  # noqa: F821 (PyInstaller)
icon = ASSETS / ("pcsf-studio.ico" if sys.platform == "win32"
                 else "pcsf-studio.png")
exe = EXE(  # noqa: F821 (PyInstaller)
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="pcsf-studio",
    # PCSF_STUDIO_CONSOLE=1 builds a console executable, to read
    # tracebacks while debugging a bundle.
    console=os.environ.get("PCSF_STUDIO_CONSOLE") == "1",
    icon=str(icon),
)
coll = COLLECT(  # noqa: F821 (PyInstaller)
    exe,
    a.binaries,
    a.datas,
    name="pcsf-studio",
)

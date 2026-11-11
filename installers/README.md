# PCSF Studio installers

Installers of PCSF Studio that need no Python installation.

| Platform | File | Tool |
|---|---|---|
| Windows | `pcsf-studio-<version>-setup.exe` | PyInstaller + Inno Setup 6 |
| Linux | `pcsf-studio-<version>-x86_64.AppImage` | PyInstaller + appimagetool |
| Linux | `pcsf-studio-<version>-linux.sh` (installs in `~/.local`) | PyInstaller + makeself |

## Build

```bash
installers/build.sh --setup          # Linux, macOS, Git Bash
```

```powershell
powershell -ExecutionPolicy Bypass -File installers\build.ps1 -Setup
```

`--setup`/`-Setup` installs the build requirements into the chosen
Python (`PYTHON=...` or `-Python ...`; use a dedicated environment,
not a base installation whose DLLs could enter the bundle). Both
scripts run `build.py`; directly:

```bash
pip install -e ".[studio,emc,mare2dem]" pyinstaller
python installers/build.py
```

`build.py` freezes the application into `dist/pcsf-studio/`
(`pyinstaller/pcsf-studio.spec`), runs the frozen executable with
`--self-test` (every bundled dataset is opened, drawn and converted)
and stops if it fails, then packages the bundle with the tools found
on the machine; a missing tool is reported as skipped. Options:
`--skip-freeze` reuses an existing bundle, `--no-package` stops after
the self-test.

The workflow `.github/workflows/studio-installers.yml` runs the same
script on Windows and Ubuntu 22.04 for every `v*` tag and attaches
the installers to the release; run it by hand from the Actions tab to
get them as artifacts.

## Files

- `pyinstaller/`: spec and entry script (one-folder, windowed; Qt
  modules the Studio does not use are excluded).
- `windows/pcsf-studio.iss`: Inno Setup script. Per-user install by
  default, Start Menu entry, optional desktop icon and `.pcsf`/`.pcsm`
  association. The version comes from `pcsf._version`.
- `linux/`: `package.sh` (AppImage and makeself), `install.sh` (run by
  the `.sh` installer) and the desktop entry.
- `assets/`: icons, rendered by `make_icon.py` from the SVG logo
  `src/pcsf/studio/resources/pcsf-studio.svg`.

macOS is not packaged yet; `pip install "pcsf[studio]"` works there.

#!/usr/bin/env bash
# Build the PCSF Studio executable and installers (Linux, macOS, or
# Git Bash on Windows).
#
#   installers/build.sh                 freeze, self-test, package
#   installers/build.sh --no-package    freeze and self-test only
#   installers/build.sh --setup         first install the build
#                                       requirements into $PYTHON
#
# PYTHON selects the interpreter of the build environment, e.g.
#   PYTHON=~/miniforge3/envs/pcsf-venv/bin/python installers/build.sh
# Output: dist/pcsf-studio/ (the executable folder) and the
# installers in dist/ (see installers/README.md).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="${PYTHON:-$(command -v python3 || command -v python)}"
if [ -z "$PYTHON" ]; then
  echo "no Python found; set PYTHON" >&2
  exit 2
fi

ARGS=()
SETUP=0
for a in "$@"; do
  if [ "$a" = "--setup" ]; then SETUP=1; else ARGS+=("$a"); fi
done

cd "$ROOT"
if [ "$SETUP" = 1 ]; then
  "$PYTHON" -m pip install -e ".[studio,emc,mare2dem]" pyinstaller
fi
"$PYTHON" -c "import PySide6, PyInstaller" 2>/dev/null || {
  echo "PySide6 or PyInstaller missing in $PYTHON; rerun with --setup" >&2
  exit 2
}
echo "building with $("$PYTHON" -c 'import sys; print(sys.executable)')"
exec "$PYTHON" installers/build.py ${ARGS[@]+"${ARGS[@]}"}

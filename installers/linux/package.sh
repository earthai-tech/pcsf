#!/usr/bin/env bash
# Package the PCSF Studio bundle for Linux.
#
#   installers/linux/package.sh VERSION BUNDLE_DIR OUT_DIR
#
# BUNDLE_DIR is the PyInstaller one-folder build (dist/pcsf-studio).
# Writes, when the tool is on PATH (or APPIMAGETOOL / MAKESELF point
# to it):
#   OUT_DIR/pcsf-studio-VERSION-x86_64.AppImage   (appimagetool)
#   OUT_DIR/pcsf-studio-VERSION-linux.sh           (makeself)
# The .sh installs into ~/.local/opt/pcsf-studio, with a launcher in
# ~/.local/bin and a desktop entry; no root rights are needed.
set -euo pipefail

VERSION="$1"
BUNDLE="$(cd "$2" && pwd)"
OUT="$(mkdir -p "$3" && cd "$3" && pwd)"
HERE="$(cd "$(dirname "$0")" && pwd)"
ICON="$HERE/../assets/pcsf-studio.png"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

# ------------------------------------------------------------ AppImage
APPIMAGETOOL="${APPIMAGETOOL:-$(command -v appimagetool || true)}"
if [ -n "$APPIMAGETOOL" ]; then
  APPDIR="$WORK/PCSF_Studio.AppDir"
  mkdir -p "$APPDIR/usr/lib"
  cp -a "$BUNDLE" "$APPDIR/usr/lib/pcsf-studio"
  cp "$ICON" "$APPDIR/pcsf-studio.png"
  cp "$HERE/pcsf-studio.desktop" "$APPDIR/pcsf-studio.desktop"
  cat > "$APPDIR/AppRun" <<'EOF'
#!/usr/bin/env bash
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/lib/pcsf-studio/pcsf-studio" "$@"
EOF
  chmod +x "$APPDIR/AppRun"
  ARCH=x86_64 "$APPIMAGETOOL" --no-appstream "$APPDIR" \
    "$OUT/pcsf-studio-$VERSION-x86_64.AppImage"
else
  echo "skip: appimagetool not found"
fi

# ----------------------------------------------------------- makeself
MAKESELF="${MAKESELF:-$(command -v makeself || command -v makeself.sh || true)}"
if [ -n "$MAKESELF" ]; then
  PAYLOAD="$WORK/payload"
  mkdir -p "$PAYLOAD"
  cp -a "$BUNDLE" "$PAYLOAD/pcsf-studio"
  cp "$ICON" "$PAYLOAD/pcsf-studio.png"
  cp "$HERE/pcsf-studio.desktop" "$PAYLOAD/pcsf-studio.desktop"
  cp "$HERE/install.sh" "$PAYLOAD/install.sh"
  chmod +x "$PAYLOAD/install.sh"
  "$MAKESELF" --nox11 "$PAYLOAD" "$OUT/pcsf-studio-$VERSION-linux.sh" \
    "PCSF Studio $VERSION" ./install.sh
else
  echo "skip: makeself not found"
fi

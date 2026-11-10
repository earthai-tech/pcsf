#!/usr/bin/env bash
# Installer run by the self-extracting pcsf-studio-VERSION-linux.sh.
# Installs for the current user only:
#   ~/.local/opt/pcsf-studio/           the application
#   ~/.local/bin/pcsf-studio            launcher
#   ~/.local/share/applications/        desktop entry
#   ~/.local/share/icons/hicolor/256x256/apps/pcsf-studio.png
# Remove with: rm -rf ~/.local/opt/pcsf-studio ~/.local/bin/pcsf-studio
#   ~/.local/share/applications/pcsf-studio.desktop
set -euo pipefail

PREFIX="${PCSF_STUDIO_PREFIX:-$HOME/.local}"
APP="$PREFIX/opt/pcsf-studio"
rm -rf "$APP"
mkdir -p "$PREFIX/opt" "$PREFIX/bin" "$PREFIX/share/applications" \
  "$PREFIX/share/icons/hicolor/256x256/apps"
cp -a pcsf-studio "$APP"
ln -sf "$APP/pcsf-studio" "$PREFIX/bin/pcsf-studio"
cp pcsf-studio.png "$PREFIX/share/icons/hicolor/256x256/apps/"
sed "s|^Exec=.*|Exec=$APP/pcsf-studio %f|" pcsf-studio.desktop \
  > "$PREFIX/share/applications/pcsf-studio.desktop"
echo "PCSF Studio installed in $APP"
echo "Start it with: pcsf-studio (make sure $PREFIX/bin is on PATH)"

#!/usr/bin/env bash
# Remove the flatpak artefacts; nothing else.
#
# Scoped to the Linux build on purpose: dist-pyinstaller, dist-installer and
# dist belong to the Windows and macOS paths, so the three stay independent.
set -euo pipefail

APP_ID="uk.codecrafter.SkillsViewer"
BUNDLE="skillsviewer.flatpak"

echo "Uninstalling ${APP_ID}"
if flatpak list --user 2>/dev/null | grep -q "${APP_ID}"; then
    flatpak uninstall --user -y "${APP_ID}"
else
    echo "  Not installed, skipping."
fi

echo "Removing the build artefacts"
rm -f "${BUNDLE}" "${APP_ID}.yml"
rm -rf .flatpak-build .flatpak-repo .flatpak-builder .flatpak-wheels packaging

echo "Done."

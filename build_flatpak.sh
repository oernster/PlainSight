#!/usr/bin/env bash
# Build Skills Viewer as a flatpak bundle.
#
# Fully offline: the wheels are fetched on the host before the build, so the
# sandbox needs no network at build time and the application asks for none at
# runtime. The manifest and the packaging helpers are generated here, so only
# this script is committed.
set -euo pipefail

APP_ID="uk.codecrafter.SkillsViewer"
APP_NAME="Skills Viewer"
COMMAND_NAME="skillsviewer"
APP_VERSION="$(tr -d '[:space:]' < VERSION)"

RUNTIME="org.freedesktop.Platform"
SDK="org.freedesktop.Sdk"
RUNTIME_VERSION="25.08"
PYTHON_DIR="python3.13"
PYTHON_TAG="3.13"

BUNDLE="skillsviewer.flatpak"
BUILD_DIR=".flatpak-build"
REPO_DIR=".flatpak-repo"
WHEELS_DIR=".flatpak-wheels"
PACKAGING_DIR="packaging"
MANIFEST="${APP_ID}.yml"

ICON_SIZES=(16 24 32 48 64 96 128 256 512)

section() {
    if command -v tput > /dev/null 2>&1; then
        printf '\n%s%s%s\n' "$(tput bold)" "$1" "$(tput sgr0)"
    else
        printf '\n%s\n' "$1"
    fi
}

install_if_missing() {
    local tool="$1"
    command -v "${tool}" > /dev/null 2>&1 && return 0
    section "Installing ${tool}"
    if command -v apt > /dev/null 2>&1; then sudo apt install -y "${tool}"
    elif command -v dnf > /dev/null 2>&1; then sudo dnf install -y "${tool}"
    elif command -v pacman > /dev/null 2>&1; then sudo pacman -S --noconfirm "${tool}"
    elif command -v zypper > /dev/null 2>&1; then sudo zypper install -y "${tool}"
    else
        echo "Install ${tool} and run this again." >&2
        exit 1
    fi
}

section "Checking the tools"
install_if_missing flatpak
install_if_missing flatpak-builder

section "Runtime"
flatpak remote-add --if-not-exists --user flathub \
    https://dl.flathub.org/repo/flathub.flatpakrepo
flatpak install --user --noninteractive flathub \
    "${RUNTIME}//${RUNTIME_VERSION}" "${SDK}//${RUNTIME_VERSION}"

section "Fetching the wheels on the host"
rm -rf "${WHEELS_DIR}"
pip download --only-binary :all: --python-version "${PYTHON_TAG}" \
    --implementation cp --platform manylinux_2_34_x86_64 \
    -d "${WHEELS_DIR}" -r requirements.txt

section "Writing the packaging helpers"
rm -rf "${PACKAGING_DIR}"
mkdir -p "${PACKAGING_DIR}"

cat > "${PACKAGING_DIR}/${COMMAND_NAME}" <<'LAUNCHER'
#!/bin/sh
SITE="/app/lib/python3.13/site-packages"
export PYTHONPATH="${SITE}:/app/share/skillsviewer${PYTHONPATH:+:$PYTHONPATH}"
export QT_PLUGIN_PATH="${SITE}/PySide6/Qt/plugins"
export QT_QPA_PLATFORM_PLUGIN_PATH="${SITE}/PySide6/Qt/plugins/platforms"
if [ -n "$WAYLAND_DISPLAY" ] && [ -z "$FORCE_X11" ]; then
    export QT_QPA_PLATFORM=wayland
else
    export QT_QPA_PLATFORM=xcb
fi
exec python3 /app/share/skillsviewer/main.py "$@"
LAUNCHER
chmod 755 "${PACKAGING_DIR}/${COMMAND_NAME}"

cat > "${PACKAGING_DIR}/${APP_ID}.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=${APP_NAME}
Comment=A reader for the skills used by Claude AI
Exec=${COMMAND_NAME}
Icon=${APP_ID}
Terminal=false
Categories=Utility;Development;TextEditor;
DESKTOP

cat > "${PACKAGING_DIR}/${APP_ID}.metainfo.xml" <<METAINFO
<?xml version="1.0" encoding="UTF-8"?>
<component type="desktop-application">
  <id>${APP_ID}</id>
  <name>${APP_NAME}</name>
  <summary>A reader for the skills used by Claude AI</summary>
  <metadata_license>CC0-1.0</metadata_license>
  <project_license>GPL-3.0-only AND LGPL-3.0-only</project_license>
  <developer id="uk.codecrafter"><name>Oliver Ernster</name></developer>
  <description>
    <p>
      Skills Viewer finds the Claude skills on your machine, lists them,
      renders the one you pick and hands editing to an editor you choose. It
      is not a text editor and it never writes to a skill.
    </p>
  </description>
  <launchable type="desktop-id">${APP_ID}.desktop</launchable>
  <releases><release version="${APP_VERSION}"/></releases>
</component>
METAINFO

section "Writing the manifest"
{
cat <<MANIFEST_HEAD
app-id: ${APP_ID}
runtime: ${RUNTIME}
runtime-version: "${RUNTIME_VERSION}"
sdk: ${SDK}
command: ${COMMAND_NAME}

build-options:
  strip: true
  no-debuginfo: true

finish-args:
  - --share=ipc
  - --socket=fallback-x11
  - --socket=wayland
  - --device=dri
  - --filesystem=home

modules:
  - name: python-deps
    buildsystem: simple
    build-commands:
      - python3 -m ensurepip --upgrade
      - pip3 install --no-cache-dir --no-index --find-links wheels --prefix=/app -r requirements.txt
    sources:
      - type: dir
        path: ${WHEELS_DIR}
        dest: wheels
      - type: file
        path: requirements.txt

  - name: skillsviewer
    buildsystem: simple
    build-commands:
      - install -d /app/share/skillsviewer
      - cp -r main.py skillsviewer assets VERSION LICENSE LICENSE-GPL-3.0.txt /app/share/skillsviewer/
      - install -Dm755 ${PACKAGING_DIR}/${COMMAND_NAME} /app/bin/${COMMAND_NAME}
      - install -Dm644 ${PACKAGING_DIR}/${APP_ID}.desktop /app/share/applications/${APP_ID}.desktop
      - install -Dm644 ${PACKAGING_DIR}/${APP_ID}.metainfo.xml /app/share/metainfo/${APP_ID}.metainfo.xml
MANIFEST_HEAD
for size in "${ICON_SIZES[@]}"; do
cat <<ICON_LINE
      - install -Dm644 assets/skillsviewer_icon_${size}.png /app/share/icons/hicolor/${size}x${size}/apps/${APP_ID}.png
ICON_LINE
done
cat <<MANIFEST_TAIL
    sources:
      - type: dir
        path: .
MANIFEST_TAIL
} > "${MANIFEST}"

section "Building"
rm -rf "${BUILD_DIR}" "${REPO_DIR}"
flatpak-builder --user --install-deps-from=flathub --force-clean \
    --repo="${REPO_DIR}" "${BUILD_DIR}" "${MANIFEST}"

section "Bundling"
flatpak build-bundle --runtime-repo=https://dl.flathub.org/repo/flathub.flatpakrepo \
    "${REPO_DIR}" "${BUNDLE}" "${APP_ID}"

section "Done"
echo "  ${BUNDLE}"
echo "  install it with: flatpak install --user ${BUNDLE}"

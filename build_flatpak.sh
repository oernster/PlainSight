#!/usr/bin/env bash
# Build PlainSight as a flatpak bundle.
#
# Fully offline: the wheels are fetched on the host before the build, so the
# sandbox needs no network at build time and the application asks for none at
# runtime. The manifest and the packaging helpers are generated here, so only
# this script is committed.
set -euo pipefail

APP_ID="uk.codecrafter.PlainSight"
APP_NAME="PlainSight"
COMMAND_NAME="plainsight"
APP_VERSION="$(tr -d '[:space:]' < VERSION)"

RUNTIME="org.freedesktop.Platform"
SDK="org.freedesktop.Sdk"
RUNTIME_VERSION="25.08"
PYTHON_DIR="python3.13"
PYTHON_TAG="3.13"
# Most specific first. pip matches the platform tags it is GIVEN and does not
# expand a manylinux tag down to the older ones it is compatible with, so one
# tag here silently means "only wheels built for exactly this". Measured on
# 2026-09-06: PySide6 publishes manylinux_2_34, while lxml, which python-docx
# brings in, publishes only manylinux_2_28 and manylinux2014, so asking for
# 2_34 alone failed the whole resolve with no matching distribution for lxml
# and the build never reached flatpak-builder. The runtime is newer than every
# one of these, so an older wheel runs there perfectly well.
WHEEL_PLATFORMS=(manylinux_2_34_x86_64 manylinux_2_28_x86_64 manylinux2014_x86_64)

BUNDLE="plainsight.flatpak"
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
platform_flags=()
for platform in "${WHEEL_PLATFORMS[@]}"; do
    platform_flags+=(--platform "${platform}")
done
pip download --only-binary :all: --python-version "${PYTHON_TAG}" \
    --implementation cp "${platform_flags[@]}" \
    -d "${WHEELS_DIR}" -r requirements.txt

section "Writing the packaging helpers"
rm -rf "${PACKAGING_DIR}"
mkdir -p "${PACKAGING_DIR}"

# The interpreter directory is interpolated so it cannot drift from
# PYTHON_DIR; everything below it is written literally, so the runtime's own
# variables reach the launcher unexpanded.
{
printf '#!/bin/sh\n'
printf 'SITE="/app/lib/%s/site-packages"\n' "${PYTHON_DIR}"
cat <<'LAUNCHER'
export PYTHONPATH="${SITE}:/app/share/plainsight${PYTHONPATH:+:$PYTHONPATH}"
export QT_PLUGIN_PATH="${SITE}/PySide6/Qt/plugins"
export QT_QPA_PLATFORM_PLUGIN_PATH="${SITE}/PySide6/Qt/plugins/platforms"
if [ -n "$WAYLAND_DISPLAY" ] && [ -z "$FORCE_X11" ]; then
    export QT_QPA_PLATFORM=wayland
else
    export QT_QPA_PLATFORM=xcb
fi
exec python3 /app/share/plainsight/main.py "$@"
LAUNCHER
} > "${PACKAGING_DIR}/${COMMAND_NAME}"
chmod 755 "${PACKAGING_DIR}/${COMMAND_NAME}"

cat > "${PACKAGING_DIR}/${APP_ID}.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=${APP_NAME}
Comment=A reader for your documents
Exec=${COMMAND_NAME}
Icon=${APP_ID}
Terminal=false
Categories=Utility;Development;Viewer;
DESKTOP

cat > "${PACKAGING_DIR}/${APP_ID}.metainfo.xml" <<METAINFO
<?xml version="1.0" encoding="UTF-8"?>
<component type="desktop-application">
  <id>${APP_ID}</id>
  <name>${APP_NAME}</name>
  <summary>A reader for your documents</summary>
  <metadata_license>CC0-1.0</metadata_license>
  <project_license>GPL-3.0-only AND LGPL-3.0-only</project_license>
  <developer id="uk.codecrafter"><name>Oliver Ernster</name></developer>
  <description>
    <p>
      PlainSight walks a folder of Markdown, text, HTML, Word and PDF
      files, shows it as the tree it is on disk and renders the one you pick.
      It reads nothing until you choose a folder. It is not a text editor and
      it never writes to a document.
    </p>
  </description>
  <content_rating type="oars-1.1"/>
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
  # The update check asks GitHub for the latest release. Without this the
  # sandbox refuses the call and every check reports itself unreachable.
  - --share=network
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

  - name: plainsight
    buildsystem: simple
    build-commands:
      - install -d /app/share/plainsight
      - cp -r main.py plainsight assets VERSION LICENSE LICENSE-GPL-3.0.txt LICENSE-LGPL-3.0.txt /app/share/plainsight/
      - install -Dm755 ${PACKAGING_DIR}/${COMMAND_NAME} /app/bin/${COMMAND_NAME}
      - install -Dm644 ${PACKAGING_DIR}/${APP_ID}.desktop /app/share/applications/${APP_ID}.desktop
      - install -Dm644 ${PACKAGING_DIR}/${APP_ID}.metainfo.xml /app/share/metainfo/${APP_ID}.metainfo.xml
MANIFEST_HEAD
for size in "${ICON_SIZES[@]}"; do
cat <<ICON_LINE
      - install -Dm644 assets/plainsight_icon_${size}.png /app/share/icons/hicolor/${size}x${size}/apps/${APP_ID}.png
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

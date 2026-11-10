#!/bin/sh
# Build the single-file flatpak bundle build/toots.flatpak.
#   tools/export.sh && tools/build_flatpak.sh
# Needs flatpak-builder (or the org.flatpak.Builder flatpak) and the Flathub
# remote. Set FLATPAK_BUILDER to choose the builder command, and
# FLATPAK_SCOPE=--system to install the runtime system-wide (CI containers).
set -eu
root=$(cd "$(dirname "$0")/.." && pwd)
app_id=io.github.tsloughter.Toots
if [ -n "${FLATPAK_BUILDER:-}" ]; then
    builder=$FLATPAK_BUILDER
elif command -v flatpak-builder >/dev/null 2>&1; then
    builder=flatpak-builder
else
    builder="flatpak run org.flatpak.Builder"
fi
test -x "$root/build/toots.x86_64" || { echo "run tools/export.sh first" >&2; exit 1; }

$builder ${FLATPAK_SCOPE:---user} --force-clean --disable-rofiles-fuse --install-deps-from=flathub \
    --state-dir="$root/build/flatpak-state" --repo="$root/build/flatpak-repo" \
    "$root/build/flatpak-app" "$root/flatpak/$app_id.yml"
flatpak build-bundle --runtime-repo=https://dl.flathub.org/repo/flathub.flatpakrepo \
    "$root/build/flatpak-repo" "$root/build/toots.flatpak" "$app_id"
ls -lh "$root/build/toots.flatpak"

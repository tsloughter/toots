#!/bin/sh
# Export the standalone Linux build to build/toots.x86_64 (game data embedded).
#   tools/export.sh
# Needs Godot 4.7 with its export templates installed. Set GODOT to use a
# different binary, e.g. GODOT=/path/to/Godot_v4.7.2-stable_linux.x86_64
set -eu
root=$(cd "$(dirname "$0")/.." && pwd)
godot=${GODOT:-flatpak run org.godotengine.Godot}
mkdir -p "$root/build"
touch "$root/build/.gdignore"          # keep Godot from scanning build output
$godot --headless --path "$root" --import
$godot --headless --path "$root" --export-release "Linux" "$root/build/toots.x86_64"
test -s "$root/build/toots.x86_64" || { echo "export failed: no build/toots.x86_64" >&2; exit 1; }
chmod +x "$root/build/toots.x86_64"
ls -lh "$root/build/toots.x86_64"

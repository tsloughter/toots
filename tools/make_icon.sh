#!/bin/sh
# Rebuild the app icon (needs Blender and ffmpeg).
#   tools/make_icon.sh
# Writes flatpak/icons/toots-{512,256,128,64}.png and the project's icon.png.
set -eu
root=$(cd "$(dirname "$0")/.." && pwd)
blender=${BLENDER:-flatpak run org.blender.Blender}
$blender -b --python "$root/blender/make_icon.py" >/dev/null

# Round the corners of the 1024px background (inset 62px, radius 210px),
# then lay Toots over the top unclipped.
mask="255*lte(hypot(max(abs(X-512)-240,0),max(abs(Y-512)-240,0)),210)"
ffmpeg -y -loglevel error -i "$root/blender/preview/icon_bg.png" -i "$root/blender/preview/icon_fg.png" \
    -filter_complex "[0]format=rgba,geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='$mask'[bg];[bg][1]overlay=format=auto" \
    "$root/blender/preview/icon_1024.png"
for size in 512 256 128 64; do
    ffmpeg -y -loglevel error -i "$root/blender/preview/icon_1024.png" \
        -vf "scale=$size:$size:flags=lanczos" "$root/flatpak/icons/toots-$size.png"
done
cp "$root/flatpak/icons/toots-256.png" "$root/icon.png"
echo "icons written to flatpak/icons/ and icon.png"

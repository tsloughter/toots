#!/usr/bin/env python3
"""Fetch just the Linux x86_64 release export template for a Godot version.

    tools/fetch_export_template.py 4.7.2 ~/.local/share/godot/export_templates

Godot publishes all templates as one 1.3 GB archive. This reads only the part
of it we need (about 70 MB) using HTTP range requests, and writes
<dest>/<version>.stable/linux_release.x86_64 plus version.txt.
"""
import io
import os
import shutil
import sys
import urllib.request
import zipfile

WANTED = ("templates/linux_release.x86_64", "templates/version.txt")


class HttpFile(io.RawIOBase):
    """A read-only, seekable view of a remote file."""

    def __init__(self, url):
        probe = urllib.request.urlopen(urllib.request.Request(url, headers={"Range": "bytes=0-0"}))
        self.url = probe.url                      # follow the redirect once, reuse the final URL
        self.size = int(probe.headers["Content-Range"].split("/")[1])
        self.pos = 0

    def seekable(self):
        return True

    def readable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, offset, whence=io.SEEK_SET):
        self.pos = {io.SEEK_SET: 0, io.SEEK_CUR: self.pos, io.SEEK_END: self.size}[whence] + offset
        return self.pos

    def readinto(self, buf):
        if self.pos >= self.size:
            return 0
        end = min(self.pos + len(buf), self.size) - 1
        req = urllib.request.Request(self.url, headers={"Range": "bytes=%d-%d" % (self.pos, end)})
        data = urllib.request.urlopen(req).read()
        buf[:len(data)] = data
        self.pos += len(data)
        return len(data)


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    version, dest = sys.argv[1], os.path.expanduser(sys.argv[2])
    url = ("https://github.com/godotengine/godot/releases/download/"
           "%s-stable/Godot_v%s-stable_export_templates.tpz" % (version, version))
    out_dir = os.path.join(dest, version + ".stable")
    os.makedirs(out_dir, exist_ok=True)
    remote = io.BufferedReader(HttpFile(url), buffer_size=8 << 20)
    with zipfile.ZipFile(remote) as archive:
        for member in WANTED:
            target = os.path.join(out_dir, os.path.basename(member))
            with archive.open(member) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst, 1 << 20)
            print("%s (%.1f MB)" % (target, os.path.getsize(target) / 1e6))


if __name__ == "__main__":
    main()

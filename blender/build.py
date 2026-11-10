"""Build game models from the procedural scripts in this folder.

    flatpak run org.blender.Blender -b --python blender/build.py -- [names...]

With no names, everything is rebuilt. Each asset is exported to models/<name>.glb,
rendered to blender/preview/<name>.png and saved as blender/blend/<name>.blend.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402

ASSETS = {}


def asset(name, **preview_args):
    def deco(fn):
        ASSETS[name] = (fn, preview_args)
        return fn
    return deco


@asset("hero", view=(-0.45, -1.0, 0.25), zoom=1.35)
def _hero():
    import hero
    return hero.build()


import critters  # noqa: E402
import scenery  # noqa: E402

critters.register(asset)
scenery.register(asset)


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    no_preview = "--no-preview" in args
    names = [a for a in args if not a.startswith("--")] or list(ASSETS)
    unknown = [n for n in names if n not in ASSETS]
    if unknown:
        sys.exit("build.py: no such asset: %s\navailable: %s" % (", ".join(unknown), ", ".join(ASSETS)))
    for name in names:
        fn, pv = ASSETS[name]
        lib.reset()
        root = fn()
        lib.export(root, name)
        if not no_preview:
            lib.preview(root, name, **pv)


main()

"""Render the app icon: Toots in front of his mountains.

    tools/make_icon.sh        (runs this, then composites and resizes with ffmpeg)

Two passes are written to blender/preview/: icon_bg.png (sky and peaks, opaque)
and icon_fg.png (Toots alone, transparent). The shell script rounds the corners
of the background and lays Toots over it, so his fur can spill past the frame.
"""
import math
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
import hero  # noqa: E402
import scenery  # noqa: E402

SIZE = 1024

lib.reset()
toots = hero.build()
toots.rotation_euler = (0, 0, math.radians(14))
toots.location = (0.02, 0, -0.08)
peaks = scenery.mountain(1, [(0, 0, 1.0, 1.15), (0.55, 0.1, 0.62, 0.7), (-0.6, 0.05, 0.5, 0.65)])()
peaks.location = (0.25, 8.0, -0.42)
peaks.scale = (1.45, 1.45, 1.75)
hill = scenery.hill(4)()
hill.location = (-0.2, 5.0, -0.62)
hill.scale = (1.5, 1.0, 0.75)

sc = bpy.context.scene
cam_d = bpy.data.cameras.new("IconCam")
cam_d.type = "ORTHO"
cam_d.ortho_scale = 1.95
cam = bpy.data.objects.new("IconCam", cam_d)
cam.location = (0, -10, 0.62)
cam.rotation_euler = (math.radians(90), 0, 0)
sc.collection.objects.link(cam)
sc.camera = cam
for name, rot, energy in (("Key", (50, 0, -35), 4.0), ("Rim", (60, 0, 150), 3.0)):
    light = bpy.data.lights.new(name, "SUN")
    light.energy = energy
    ob = bpy.data.objects.new(name, light)
    ob.rotation_euler = [math.radians(a) for a in rot]
    sc.collection.objects.link(ob)
world = bpy.data.worlds.new("World")
try:
    world.use_nodes = True
except Exception:
    pass
bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
bg.inputs[0].default_value = lib.hexcol("#6db3ee")
sc.world = world
sc.render.engine = "BLENDER_EEVEE"
sc.render.resolution_x = sc.render.resolution_y = SIZE
sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_mode = "RGBA"
sc.view_settings.view_transform = "Standard"


def render(name, show_hero, transparent):
    for o in lib.hierarchy(toots):
        o.hide_render = not show_hero
    for o in lib.hierarchy(peaks) + lib.hierarchy(hill):
        o.hide_render = show_hero
    sc.render.film_transparent = transparent
    sc.render.filepath = os.path.join(lib.PREVIEW, name + ".png")
    bpy.ops.render.render(write_still=True)


os.makedirs(lib.PREVIEW, exist_ok=True)
render("icon_bg", False, False)
render("icon_fg", True, True)

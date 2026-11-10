"""Rocky Mountain wildlife that would rather Toots went somewhere else.

All critters face -Y in Blender (+Z in Godot) with feet at z=0. Legs and wings
are separate objects (leg_*, wing_*) so the game can animate them.
"""
import math
import random
from mathutils import Matrix, Vector
from lib import Part, mat, empty, align


def eyes(part, x, y, z, r=0.03, white=False):
    black = mat("eye_black", "#060606", 0.1)
    shine = mat("eye_shine", "#ffffff", 0.2, emit=1.0)
    for sx in (-1, 1):
        if white:
            part.sphere(mat("eye_white", "#f4f1e6", 0.3), loc=(sx * x, y + r * 0.3, z), scale=r * 1.35, segs=10, rings=8)
        part.sphere(black, loc=(sx * x, y, z), scale=r, segs=10, rings=8)
        part.sphere(shine, loc=(sx * (x + r * 0.2), y - r * 0.75, z + r * 0.4), scale=r * 0.3, segs=6, rings=4)


def marmot():
    root = empty("marmot")
    fur = mat("marmot_fur", "#8a6038", 0.9)
    dark = mat("marmot_dark", "#4e3420", 0.9)
    belly = mat("marmot_belly", "#d6a652", 0.9)
    nose = mat("nose_black", "#0c0a0a", 0.3)
    tooth = mat("tooth_white", "#f7f2df", 0.3)
    b = Part("body")
    b.sphere(fur, loc=(0, 0.06, 0.27), scale=(0.25, 0.34, 0.24), segs=20, rings=12)
    b.sphere(belly, loc=(0, 0.0, 0.2), scale=(0.21, 0.3, 0.19), segs=16, rings=10)
    b.sphere(fur, loc=(0, -0.27, 0.4), scale=(0.17, 0.17, 0.155), segs=18, rings=12)       # head
    b.sphere(belly, loc=(0, -0.385, 0.35), scale=(0.105, 0.08, 0.075), segs=14, rings=8)    # muzzle
    for sx in (-1, 1):
        b.sphere(belly, loc=(sx * 0.1, -0.33, 0.34), scale=(0.07, 0.07, 0.06), segs=10, rings=8)   # cheeks
        b.sphere(dark, loc=(sx * 0.12, -0.2, 0.535), scale=(0.045, 0.03, 0.045), segs=10, rings=6)  # ears
    b.sphere(nose, loc=(0, -0.46, 0.375), scale=(0.035, 0.022, 0.024), segs=10, rings=6)
    for sx in (-1, 1):
        b.box(tooth, loc=(sx * 0.017, -0.455, 0.305), scale=(0.015, 0.008, 0.03), bevel=0.005)
    eyes(b, 0.085, -0.4, 0.44, 0.028)
    b.sphere(dark, loc=(0, 0.45, 0.2), scale=(0.07, 0.2, 0.06), rot=(-20, 0, 0), segs=12, rings=8)   # tail
    b.finish(parent=root)
    for nm, x, y in (("leg_FL", 0.14, -0.16), ("leg_FR", -0.14, -0.16),
                     ("leg_BL", 0.16, 0.22), ("leg_BR", -0.16, 0.22)):
        p = Part(nm)
        p.sphere(dark, loc=(x, y - 0.04, 0.05), scale=(0.065, 0.1, 0.05), segs=10, rings=6)
        p.finish(origin=(x, y, 0.14), parent=root)
    return root


def ram():
    root = empty("ram")
    coat = mat("ram_coat", "#9c7a54", 0.9)
    coat_d = mat("ram_coat_dark", "#6e5238", 0.9)
    white = mat("ram_white", "#efe8da", 0.9)
    horn = mat("ram_horn", "#cdb489", 0.6)
    horn_d = mat("ram_horn_dark", "#8f7a58", 0.6)
    hoof = mat("hoof", "#1d1a18", 0.5)
    nose = mat("nose_black", "#0c0a0a", 0.3)
    b = Part("body")
    b.sphere(coat, loc=(0, 0.08, 0.78), scale=(0.3, 0.52, 0.31), power=0.85, segs=22, rings=14)
    b.sphere(white, loc=(0, 0.1, 0.66), scale=(0.25, 0.42, 0.2), segs=16, rings=10)          # belly
    b.sphere(white, loc=(0, 0.5, 0.82), scale=(0.24, 0.14, 0.24), segs=16, rings=10)         # rump patch
    b.sphere(coat_d, loc=(0, 0.63, 0.86), scale=(0.04, 0.05, 0.07), segs=8, rings=6)         # tail
    b.sphere(coat, loc=(0, -0.38, 0.98), scale=(0.2, 0.25, 0.27), rot=(35, 0, 0), segs=16, rings=10)   # neck
    b.sphere(coat, loc=(0, -0.56, 1.18), scale=(0.17, 0.2, 0.17), segs=18, rings=12)         # skull
    b.sphere(coat, loc=(0, -0.74, 1.08), scale=(0.115, 0.2, 0.11), rot=(-28, 0, 0), segs=14, rings=10)  # muzzle
    b.sphere(white, loc=(0, -0.845, 1.005), scale=(0.1, 0.1, 0.085), rot=(-28, 0, 0), segs=12, rings=8)
    b.sphere(nose, loc=(0, -0.925, 1.0), scale=(0.06, 0.03, 0.022), rot=(-28, 0, 0), power=0.7, segs=8, rings=6)
    b.box(nose, loc=(0, -0.93, 0.955), scale=(0.006, 0.02, 0.03), rot=(-28, 0, 0))
    eyes(b, 0.125, -0.7, 1.2, 0.034, white=True)
    # the big curl: tapered open torus beside the head, thick end on the skull.
    # The right horn is the left one reflected in x; rotating the start angle
    # instead would run the taper the other way round the curl.
    horn_m = align((0.225, -0.4, 1.2), (1, 0.0, 0.25), up=(0, 0, 1))
    for sx in (-1, 1):
        b.sphere(coat_d, loc=(sx * 0.2, -0.47, 1.16), scale=(0.07, 0.03, 0.045), rot=(0, sx * 20, 0), segs=8, rings=6)  # ears
        b.torus(horn, R=0.2, r=0.085, arc=300, taper=0.22, segs=22, tube=8,
                rot=(0, 0, 60), matrix=Matrix.Diagonal((sx, 1, 1, 1)) @ horn_m, scale=(1, 1, 1.15))
    b.finish(parent=root)
    for nm, x, y in (("leg_FL", 0.17, -0.27), ("leg_FR", -0.17, -0.27),
                     ("leg_BL", 0.17, 0.42), ("leg_BR", -0.17, 0.42)):
        p = Part(nm)
        p.sphere(coat, loc=(x, y, 0.56), scale=(0.1, 0.12, 0.16), segs=10, rings=8)
        p.cone(coat_d, loc=(x, y, 0.08), r1=0.05, r2=0.07, depth=0.5, segs=8)
        p.cone(hoof, loc=(x, y - 0.01, 0.0), r1=0.065, r2=0.055, depth=0.1, segs=8)
        p.finish(origin=(x, y, 0.62), parent=root)
    return root


def porcupine():
    rng = random.Random(3)
    root = empty("porcupine")
    fur = mat("porc_fur", "#3a2c22", 0.95)
    face = mat("porc_face", "#5a4636", 0.9)
    quill = mat("porc_quill", "#e9dfc2", 0.5)
    quill_d = mat("porc_quill_dark", "#2a211b", 0.6)
    nose = mat("nose_black", "#0c0a0a", 0.3)
    b = Part("body")
    b.sphere(fur, loc=(0, 0.05, 0.27), scale=(0.3, 0.4, 0.27), segs=20, rings=12)
    samples = b.sample_surface(420, rng)
    b.sphere(face, loc=(0, -0.36, 0.2), scale=(0.15, 0.15, 0.13), segs=16, rings=10)
    b.sphere(face, loc=(0, -0.48, 0.17), scale=(0.08, 0.07, 0.065), segs=12, rings=8)
    b.sphere(nose, loc=(0, -0.545, 0.18), scale=(0.035, 0.022, 0.026), segs=8, rings=6)
    for sx in (-1, 1):
        b.sphere(fur, loc=(sx * 0.11, -0.3, 0.31), scale=(0.035, 0.025, 0.035), segs=8, rings=6)
    eyes(b, 0.085, -0.46, 0.24, 0.024)
    for p, n in samples:
        if n.z < -0.15 or (p.y < -0.22 and p.z < 0.38):
            continue
        d = (n + Vector((0, 0.9, 0.35)) * 0.55).normalized()
        L = rng.uniform(0.2, 0.36)
        m = align(p - n * 0.02, d)
        b.cone(quill_d, r1=0.02, r2=0.012, depth=L * 0.55, segs=5, matrix=m, caps=False, smooth=False)
        b.cone(quill, loc=(0, 0, L * 0.55), r1=0.012, r2=0.0, depth=L * 0.45, segs=5, matrix=m, caps=False, smooth=False)
    b.finish(parent=root)
    for nm, x, y in (("leg_FL", 0.17, -0.2), ("leg_FR", -0.17, -0.2),
                     ("leg_BL", 0.18, 0.24), ("leg_BR", -0.18, 0.24)):
        p = Part(nm)
        p.sphere(face, loc=(x, y - 0.03, 0.045), scale=(0.06, 0.09, 0.045), segs=10, rings=6)
        p.finish(origin=(x, y, 0.12), parent=root)
    return root


def eagle():
    root = empty("eagle")
    brown = mat("eagle_brown", "#3b2a1e", 0.85)
    brown_l = mat("eagle_brown_light", "#5a4230", 0.85)
    white = mat("eagle_white", "#f3f1ea", 0.8)
    yellow = mat("eagle_yellow", "#f2b632", 0.45)
    b = Part("body")
    b.sphere(brown, loc=(0, 0.02, 0), scale=(0.16, 0.34, 0.15), segs=18, rings=12)
    b.sphere(white, loc=(0, -0.34, 0.07), scale=(0.115, 0.13, 0.11), segs=16, rings=10)       # head
    b.cone(yellow, loc=(0, -0.43, 0.06), r1=0.05, r2=0.03, depth=0.1, rot=(90, 0, 0), segs=8)   # beak
    b.sphere(yellow, loc=(0, -0.545, 0.035), scale=(0.03, 0.035, 0.045), segs=8, rings=6)       # hook
    # stern eagle eyes with a brow
    eyes(b, 0.085, -0.41, 0.1, 0.022)
    for sx in (-1, 1):
        b.box(white, loc=(sx * 0.08, -0.41, 0.135), scale=(0.045, 0.045, 0.012), rot=(0, sx * 25, sx * -15), bevel=0.004)
        b.sphere(yellow, loc=(sx * 0.07, 0.05, -0.16), scale=(0.035, 0.07, 0.03), segs=8, rings=6)   # talons
    for i in range(5):                                                                           # tail fan
        a = (i - 2) * 13
        b.box(white, loc=(math.sin(math.radians(a)) * 0.22, 0.33 + math.cos(math.radians(a)) * 0.22, 0.0),
              scale=(0.045, 0.16, 0.012), rot=(0, 0, -a), bevel=0.005)
    b.finish(parent=root)
    for sx, side in ((1, "L"), (-1, "R")):
        w = Part("wing_" + side)
        w.sphere(brown, loc=(sx * 0.36, 0.02, 0.02), scale=(0.34, 0.2, 0.035), segs=16, rings=8)
        w.sphere(brown_l, loc=(sx * 0.3, -0.05, 0.035), scale=(0.26, 0.11, 0.03), segs=14, rings=8)
        for i in range(6):                                                                       # primaries
            a = -35 + i * 17
            ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
            w.box(brown, loc=(sx * (0.62 + ca * 0.16), 0.03 + sa * 0.16, 0.02),
                  scale=(0.17, 0.038, 0.01), rot=(0, 0, sx * a), bevel=0.004)
        for i in range(5):                                                                       # secondaries
            w.box(brown, loc=(sx * (0.16 + i * 0.1), 0.2, 0.015), scale=(0.045, 0.11, 0.01), bevel=0.004)
        w.finish(origin=(sx * 0.1, 0.0, 0.05), parent=root)
    return root


def register(asset):
    asset("marmot", view=(-0.9, -1.0, 0.35), zoom=1.4)(marmot)
    asset("ram", view=(-1.0, -0.45, 0.15), zoom=1.3)(ram)
    asset("porcupine", view=(-0.9, -1.0, 0.4), zoom=1.4)(porcupine)
    asset("eagle", view=(-0.6, -1.0, 0.6), zoom=1.4)(eagle)

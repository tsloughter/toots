"""Toots: the shaggy black Rocky Mountain monster with the big teeth.

Blender front is -Y (becomes +Z in Godot). Feet at z=0, about 1.25 tall.
Parts are separate objects with origins at the joints so the game can swing
them procedurally: body, arm_L, arm_R, leg_L, leg_R.
"""
import random
from mathutils import Vector
from lib import Part, blob, mat, empty, align, TRS


def build():
    rng = random.Random(7)
    fur = [mat("fur_dark", "#131316", 0.95), mat("fur_mid", "#1d1d23", 0.95),
           mat("fur_tip", "#2b2b34", 0.9)]
    felt = mat("felt", "#4a4a55", 1.0)
    felt_rim = mat("felt_rim", "#2c2c34", 1.0)
    glass = mat("eye_glass", "#aab0ba", 0.08)
    pupil = mat("eye_pupil", "#050506", 0.1)
    shine = mat("eye_shine", "#ffffff", 0.2, emit=1.0)
    nose_m = mat("nose", "#08080a", 0.18)
    hole = mat("mouth_dark", "#020202", 1.0)
    tooth = mat("tooth", "#f0dfa6", 0.3)
    gum = mat("gum", "#5a2530", 0.6)

    root = empty("hero")

    # ---- body: boxy pillow, a touch wider at the head, ear bumps on the corners
    def body_shape(p):
        p.sphere(fur[0], loc=(0, 0, 0.64), scale=(0.47, 0.31, 0.52), power=0.72, segs=32, rings=20)
        p.sphere(fur[0], loc=(0, 0, 0.88), scale=(0.50, 0.30, 0.26), power=0.75, segs=32, rings=16)
        for sx in (-1, 1):
            p.sphere(fur[0], loc=(sx * 0.37, 0.0, 1.10), scale=(0.17, 0.14, 0.16), segs=20, rings=12)

    body = blob("body", body_shape, voxel=0.03, smooth_iter=10, faces=1800)
    body.mats = [fur[0]]
    bvh = body.bvh()

    def surf(x, z):
        hit, n, _, _ = bvh.ray_cast(Vector((x, -3, z)), Vector((0, 1, 0)))
        return hit, n

    eye_pos = [(-0.265, 0.84), (0.265, 0.84)]
    mouth_z, mouth_w = 0.615, 0.44

    def fur_scale(p, n):
        # keep the face readable: no long fur over eyes, nose and mouth
        if n.y < -0.25:
            for ex, ez in eye_pos:
                if (p.x - ex) ** 2 + (p.z - ez) ** 2 < 0.165 ** 2:
                    return 0.0
            if abs(p.x) < mouth_w / 2 + 0.03 and abs(p.z - mouth_z) < 0.115:
                return 0.0
            if abs(p.x) < 0.07 and abs(p.z - 0.80) < 0.06:
                return 0.0
            if abs(p.x) < 0.46 and 0.5 < p.z < 1.0:
                return 0.55
        return 1.0

    samples = body.sample_surface(1500, rng)

    # ---- eyes: felt disc with a stitched rim, sleepy glass eye, heavy lid
    for i, (ex, ez) in enumerate(eye_pos):
        sx = -1 if ex < 0 else 1
        hit, n = surf(ex, ez)
        m = align(hit, n)
        body.cone(felt, r1=0.135, r2=0.13, depth=0.022, segs=24, matrix=m)
        body.torus(felt_rim, R=0.132, r=0.017, loc=(0, 0, 0.018), segs=28, tube=8, matrix=m)
        body.sphere(glass, loc=(0, -0.005, 0.02), scale=(0.078, 0.078, 0.055), matrix=m)
        body.sphere(pupil, loc=(-sx * 0.012, -0.022, 0.05), scale=(0.04, 0.04, 0.03), matrix=m)
        body.sphere(shine, loc=(-sx * 0.03, -0.004, 0.071), scale=0.011, segs=8, rings=6, matrix=m)
        # droopy lid: outer corner hangs lower
        body.sphere(felt_rim, loc=(0, -0.005, 0.022), scale=(0.086, 0.086, 0.064),
                    rot=(0, 0, -sx * 20), cut=((0, -0.12, 0), (0, -1, 0.0)), matrix=m)

    # ---- nose: shiny plastic button with nostrils
    hit, n = surf(0, 0.80)
    m = align(hit, n)
    body.sphere(nose_m, loc=(0, 0, 0.012), scale=(0.062, 0.046, 0.04), power=0.8, matrix=m)
    for sx in (-1, 1):
        body.sphere(hole, loc=(sx * 0.024, -0.008, 0.045), scale=(0.011, 0.011, 0.008), segs=8, rings=6, matrix=m)
    body.sphere(hole, loc=(0, 0.02, 0.046), scale=(0.009, 0.009, 0.007), segs=8, rings=6, matrix=m)

    # ---- mouth: dark slot, gums, and the famous teeth
    hit, n = surf(0, mouth_z)
    m = align(hit, n)
    body.sphere(hole, loc=(0, 0, -0.015), scale=(mouth_w / 2 + 0.01, 0.085, 0.04), power=0.6, matrix=m)
    body.sphere(gum, loc=(0, 0.062, -0.004), scale=(mouth_w / 2 - 0.005, 0.022, 0.03), power=0.7, matrix=m)
    body.sphere(gum, loc=(0, -0.064, -0.004), scale=(mouth_w / 2 - 0.015, 0.02, 0.03), power=0.7, matrix=m)

    def teeth(count, z, w, h, up):
        span = mouth_w - 0.04
        step = span / count
        for i in range(count):
            x = -span / 2 + step * (i + 0.5)
            hx, hn = surf(x, z)
            tm = align(hx, hn)
            tw = step * 0.5 * rng.uniform(0.84, 0.98)
            th = h * rng.uniform(0.82, 1.1)
            # middle teeth are the big ones
            th *= 1.0 + 0.22 * (1 - abs(i + 0.5 - count / 2) / (count / 2))
            off = (th - h) * (-0.5 if up else 0.5)
            body.sphere(tooth, loc=(0, off, 0.012), scale=(tw, th, w), power=0.55,
                        rot=(0, 0, rng.uniform(-7, 7)), segs=12, rings=8, matrix=tm)

    teeth(6, mouth_z + 0.04, 0.032, 0.046, True)
    teeth(7, mouth_z - 0.044, 0.028, 0.034, False)

    body.tufts(samples, fur, rng, length=(0.11, 0.22), radius=(0.032, 0.05), droop=0.75,
               scale_fn=fur_scale)
    body.finish(parent=root)

    # ---- limbs
    def limb(name, loc, scale, origin, count, droop):
        def shape(p):
            p.sphere(fur[0], loc=loc, scale=scale, power=0.85, segs=20, rings=12)
        part = blob(name, shape, voxel=0.03, smooth_iter=4, faces=260)
        part.mats = [fur[0]]
        part.tufts(part.sample_surface(count, rng), fur, rng, length=(0.08, 0.16),
                   radius=(0.028, 0.042), droop=droop)
        part.finish(origin=origin, parent=root)

    for sx, side in ((-1, "R"), (1, "L")):
        limb("arm_" + side, (sx * 0.60, 0, 0.50), (0.21, 0.125, 0.125), (sx * 0.44, 0, 0.53), 150, 0.6)
        limb("leg_" + side, (sx * 0.20, 0, 0.12), (0.15, 0.16, 0.14), (sx * 0.20, 0, 0.24), 110, 0.35)

    return root

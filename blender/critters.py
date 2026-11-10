"""Rocky Mountain wildlife that would rather Toots went somewhere else.

All critters face -Y in Blender (+Z in Godot) with feet at z=0. Legs and wings
are separate objects (leg_*, wing_*) so the game can animate them.
"""
import math
import random
import bmesh
from mathutils import Matrix, Vector
from lib import Part, blob, mat, empty, align, TRS, vertex_colours


def eyes(part, x, y, z, r=0.03, white=False):
    black = mat("eye_black", "#060606", 0.1)
    shine = mat("eye_shine", "#ffffff", 0.2, emit=1.0)
    for sx in (-1, 1):
        if white:
            part.sphere(mat("eye_white", "#f4f1e6", 0.3), loc=(sx * x, y + r * 0.3, z), scale=r * 1.35, segs=10, rings=8)
        part.sphere(black, loc=(sx * x, y, z), scale=r, segs=10, rings=8)
        part.sphere(shine, loc=(sx * (x + r * 0.2), y - r * 0.75, z + r * 0.4), scale=r * 0.3, segs=6, rings=4)


def seg(part, material, a, b, r1, r2, segs=8):
    """Tapered limb segment from point a to point b."""
    a, b = Vector(a), Vector(b)
    part.cone(material, r1=r1, r2=r2, depth=(b - a).length, segs=segs, matrix=align(a, b - a))


def web(part, material, matrix, radius, half_angle, toes, z=0.016, thick=0.009, scallop=0.14):
    """Webbing between toes: a thin fan along local -Y from the heel at the
    matrix origin, its edge dipping in between each pair of toes."""
    tmp = bmesh.new()
    n = (toes - 1) * 3
    outline = [(0.0, 0.035)]
    for i in range(n + 1):
        a = math.radians(-half_angle + 2 * half_angle * i / n)
        r = radius * (1 - scallop * abs(math.sin(math.pi * i / 3)))
        outline.append((math.sin(a) * r, -math.cos(a) * r))
    top = [tmp.verts.new((x, y, z)) for x, y in outline]
    bot = [tmp.verts.new((x, y, z - thick)) for x, y in outline]
    tmp.faces.new(top)
    tmp.faces.new(list(reversed(bot)))
    for i in range(len(top)):
        j = (i + 1) % len(top)
        tmp.faces.new((top[j], top[i], bot[i], bot[j]))
    bmesh.ops.recalc_face_normals(tmp, faces=tmp.faces)
    part.merge(tmp, matrix, material, smooth=False)


def paw(part, skin, claw, matrix, angles, reach, r, webbed=False, claw_len=2.4):
    """Clawed toes fanned out along local -Y from the wrist / heel."""
    if webbed:
        web(part, skin, matrix, reach * 0.93, max(angles) + 5, len(angles))
    for a in angles:
        m = matrix @ TRS(rot=(0, 0, a))
        part.sphere(skin, loc=(0, -reach * 0.56, r * 1.25), scale=(r, reach * 0.47, r * 0.95),
                    segs=8, rings=6, matrix=m)
        part.cone(claw, loc=(0, -reach * 0.96, r * 1.3), r1=r * 0.62, r2=0.0, depth=r * claw_len,
                  rot=(104, 0, 0), segs=5, matrix=m, caps=False)


def paddle(part, materials, y0, length, width, rings=14, around=14):
    """A beaver's tail: flat scaly paddle running back along +Y, thick and
    raised where it leaves the body, thin and resting on the ground at the tip.
    The faces alternate between the two materials, which reads as scales."""
    mi = [part._mi(m) for m in materials]

    def ring(t):
        w = 0.3 + 0.7 * min(t / 0.42, 1.0) ** 0.8          # narrow stalk, then the blade
        if t > 0.72:
            w *= math.sqrt(max(1.0 - ((t - 0.72) / 0.28) ** 2, 0.0))
        w *= width
        th = 0.012 + 0.03 * (1 - t) ** 1.5
        zc = 0.022 + 0.07 * (1 - t) ** 2
        out = []
        for j in range(around):
            b = 2 * math.pi * j / around
            c, s = math.cos(b), math.sin(b)
            out.append(part.bm.verts.new((math.copysign(abs(c) ** 0.65, c) * w,
                                          y0 + length * t, zc + s * th)))
        return out

    prev = ring(0.0)
    for i in range(1, rings + 1):
        last = i == rings
        cur = [part.bm.verts.new((0, y0 + length, 0.022))] * around if last else ring(i / rings)
        for j in range(around):
            k = (j + 1) % around
            vs = (prev[j], cur[j], prev[k]) if last else (prev[j], cur[j], cur[k], prev[k])
            f = part.bm.faces.new(vs)
            f.material_index = mi[(i + j) % 2]
            f.smooth = True
        prev = cur


def beaver():
    rng = random.Random(11)
    crng = random.Random(5)          # colour dither, kept apart from the fur shapes
    root = empty("beaver")
    coat_mats = [mat("beaver_fur_light", "#a9592a", 0.85), mat("beaver_fur", "#7c4321", 0.9),
                 mat("beaver_fur_dark", "#502c17", 0.9), mat("beaver_fur_wet", "#2c190e", 0.8)]
    tan = mat("beaver_muzzle", "#b1946f", 0.9)
    skin = mat("beaver_skin", "#3a2c29", 0.65)
    claw = mat("beaver_claw", "#d2c4ab", 0.4)
    scales = [mat("beaver_tail", "#4b4649", 0.55), mat("beaver_tail_dark", "#3d383d", 0.6)]
    nose_m = mat("beaver_nose", "#2b2427", 0.25)
    hole = mat("mouth_dark", "#020202", 1.0)
    tooth = mat("beaver_tooth", "#e8902c", 0.3)
    black = mat("eye_black", "#060606", 0.1)
    shine = mat("eye_shine", "#ffffff", 0.2, emit=1.0)
    whisker = mat("beaver_whisker", "#e6dccb", 0.5)

    # ---- fur: sunlit auburn over the head and back, dark and wet-looking
    # low down, all of it combed back towards the tail
    back = Vector((0, 0.85, -0.52)).normalized()

    def flow(p, n):
        t = back - n * back.dot(n)
        return t.normalized() if t.length > 0.05 else Vector((0, 0, -1))

    def band(p, noise=0.0):
        h = (p.z - 0.07) / 0.36 + max(0.0, -p.y - 0.2) * 1.3 + noise
        return 0 if h > 1.1 else 1 if h > 0.82 else 2 if h > 0.5 else 3

    PALETTES = ([0, 0, 0, 1], [0, 1, 1, 2], [1, 2, 2, 3], [2, 3, 3])

    def coat(p, n):
        return [coat_mats[i] for i in PALETTES[band(p, crng.uniform(-0.24, 0.24))]]

    def undercoat(part):
        # the skin under the tufts, a shade darker than the fur over it
        part.mats = list(coat_mats)
        for f in part.bm.faces:
            f.material_index = min(band(f.calc_center_median()) + 1, 3)

    def furry(part, samples, length, radius, scale_fn=None, materials=coat):
        part.tufts(samples, materials, rng, length=length, radius=radius, droop=1.0,
                   scale_fn=scale_fn, flow=flow, lift=0.38)
        for v in part.bm.verts:          # nothing hangs through the ground
            v.co.z = max(v.co.z, 0.004)

    # ---- body: pear shaped, heavy in the rump
    def body_shape(p):
        m = coat_mats[0]
        p.sphere(m, loc=(0, 0.16, 0.265), scale=(0.25, 0.27, 0.235), segs=24, rings=16)    # rump
        p.sphere(m, loc=(0, -0.05, 0.26), scale=(0.225, 0.25, 0.215), segs=24, rings=16)   # barrel
        p.sphere(m, loc=(0, -0.2, 0.265), scale=(0.18, 0.17, 0.18), segs=20, rings=12)     # shoulders
        p.sphere(m, loc=(0, 0.39, 0.125), scale=(0.105, 0.13, 0.075), segs=16, rings=10)   # tail root

    body = blob("body", body_shape, voxel=0.03, smooth_iter=8, tris=1800)
    samples = body.sample_surface(820, rng)
    body.decimate(900)
    undercoat(body)
    furry(body, samples, (0.075, 0.14), (0.024, 0.037),
          scale_fn=lambda p, n: 0.0 if n.z < -0.85 else 0.6 if p.y > 0.4 else 1.0)
    body.finish(origin=(0, 0, 0.26), parent=root)

    # ---- head: blunt and broad, small eyes set high, tiny ears far back
    def head_shape(p):
        m = coat_mats[0]
        p.sphere(m, loc=(0, -0.37, 0.37), scale=(0.15, 0.16, 0.14), segs=24, rings=16)       # skull
        p.sphere(m, loc=(0, -0.485, 0.32), scale=(0.092, 0.085, 0.078), segs=20, rings=12)   # muzzle
        p.sphere(m, loc=(0, -0.455, 0.262), scale=(0.058, 0.06, 0.04), segs=16, rings=10)    # chin
        for sx in (-1, 1):
            p.sphere(m, loc=(sx * 0.082, -0.43, 0.315), scale=(0.074, 0.08, 0.07), segs=16, rings=10)  # cheeks

    head = blob("head", head_shape, voxel=0.02, smooth_iter=6, tris=1240)
    bvh = head.bvh()
    samples = head.sample_surface(330, rng)
    head.decimate(620)
    undercoat(head)
    for f in head.bm.faces:
        c = f.calc_center_median()
        if c.y < -0.44 and c.z < 0.35:
            f.material_index = head._mi(tan)

    def surf(origin, direction):
        hit, n, _, _ = bvh.ray_cast(Vector(origin), Vector(direction).normalized())
        return hit, n

    skull = Vector((0, -0.37, 0.37))
    bare = []                           # (centre, radius) spots the fur keeps clear of

    eye_parts = []
    for sx, side in ((1, "L"), (-1, "R")):
        d = Vector((sx * 0.8, -0.56, 0.4)).normalized()
        hit, n = surf(skull + d, -d)
        bare.append((hit, 0.06))
        head.sphere(skin, scale=(0.037, 0.037, 0.012), segs=12, rings=6, matrix=align(hit, n))   # socket
        e = Part("eye_" + side)
        e.sphere(black, loc=(0, 0, 0.004), scale=(0.027, 0.027, 0.021), segs=12, rings=8, matrix=align(hit, n))
        e.sphere(shine, loc=tuple(hit + n * 0.021 + Vector((0, -0.009, 0.009))), scale=0.0075, segs=6, rings=4)
        eye_parts.append((e, hit.copy()))

        d = Vector((sx * 0.8, 0.42, 0.62)).normalized()                                       # ears
        hit, n = surf(skull + d, -d)
        bare.append((hit + n * 0.02, 0.062))
        c = hit + n * 0.032
        head.sphere(coat_mats[2], loc=tuple(c), scale=(0.05, 0.022, 0.052), rot=(0, 0, sx * 28), segs=10, rings=8)
        head.sphere(skin, loc=tuple(c + Vector((sx * 0.007, -0.013, 0.0))), scale=(0.033, 0.013, 0.035),
                    rot=(0, 0, sx * 28), segs=8, rings=6)

        for i in range(3):                                                                    # whiskers
            d = Vector((sx * 0.75, -0.6, -0.3 + 0.13 * i)).normalized()
            hit, n = surf(Vector((0, -0.45, 0.32)) + d, -d)
            out = Vector((sx * 0.9, -0.3, -0.28 + 0.2 * i))
            head.cone(whisker, r1=0.0045, r2=0.0, depth=rng.uniform(0.1, 0.13), segs=3,
                      matrix=align(hit - n * 0.005, out), caps=False, smooth=False)

    hit, n = surf((0, -3, 0.347), (0, 1, 0))                                                   # nose
    nose_at = hit.copy()
    bare.append((hit, 0.062))
    m = align(hit, n)
    head.sphere(nose_m, loc=(0, 0.004, 0.004), scale=(0.047, 0.034, 0.028), power=0.85, segs=14, rings=10, matrix=m)
    for sx in (-1, 1):
        head.sphere(hole, loc=(sx * 0.019, -0.004, 0.026), scale=(0.009, 0.011, 0.007), segs=8, rings=6, matrix=m)

    hit, n = surf((0, -3, 0.275), (0, 1, 0))                                                   # mouth and incisors
    bare.append((hit, 0.05))
    m = align(hit, n)
    head.sphere(hole, loc=(0, -0.022, 0.0), scale=(0.036, 0.026, 0.012), segs=12, rings=8, matrix=m)
    for sx in (-1, 1):
        head.sphere(tooth, loc=(sx * 0.0135, -0.008, 0.011), scale=(0.0125, 0.029, 0.009), power=0.55,
                    rot=(0, 0, sx * 3), segs=10, rings=8, matrix=m)

    def face_fur(p, n):
        for c, r in bare:
            if (p - c).length < r:
                return 0.0
        return 0.55 if p.y < -0.44 else 1.0

    def face_coat(p, n):
        if p.y < -0.45 and p.z < 0.345 and (p - nose_at).length < 0.14:
            return [tan, tan, coat_mats[0]]
        return coat(p, n)

    furry(head, samples, (0.05, 0.09), (0.02, 0.03), scale_fn=face_fur, materials=face_coat)
    head_ob = head.finish(origin=(0, -0.27, 0.31), parent=root)
    for e, at in eye_parts:
        e.finish(origin=tuple(at), parent=head_ob)

    # ---- legs: furry upper leg, bare forearm, clawed fingers; the hind
    # feet are the big webbed paddles it swims with
    for sx, side in ((1, "L"), (-1, "R")):
        p = Part("leg_F" + side)
        p.sphere(coat_mats[1], loc=(sx * 0.16, -0.2, 0.145), scale=(0.062, 0.078, 0.088), segs=12, rings=8)
        samples = [s for s in p.sample_surface(46, rng) if s[1].x * sx > -0.4]
        seg(p, skin, (sx * 0.165, -0.21, 0.11), (sx * 0.172, -0.236, 0.03), 0.038, 0.027)
        m = TRS((sx * 0.172, -0.236, 0.0), rot=(0, 0, sx * 12))
        p.sphere(skin, loc=(0, -0.008, 0.022), scale=(0.035, 0.042, 0.022), segs=10, rings=6, matrix=m)
        paw(p, skin, claw, m, (-36, -12, 12, 36), 0.085, 0.0105)
        furry(p, samples, (0.04, 0.08), (0.02, 0.03))
        p.finish(origin=(sx * 0.155, -0.2, 0.17), parent=root)

        p = Part("leg_B" + side)
        p.sphere(coat_mats[2], loc=(sx * 0.2, 0.2, 0.165), scale=(0.095, 0.15, 0.145), rot=(-18, 0, 0), segs=14, rings=10)
        samples = [s for s in p.sample_surface(86, rng) if s[1].x * sx > -0.4]
        m = TRS((sx * 0.225, 0.2, 0.0), rot=(0, 0, sx * 14))
        p.sphere(skin, loc=(0, 0.0, 0.032), scale=(0.042, 0.055, 0.032), segs=10, rings=6, matrix=m)   # heel
        paw(p, skin, claw, m, (-30, -15, 0, 15, 30), 0.21, 0.014, webbed=True)
        furry(p, samples, (0.05, 0.1), (0.022, 0.034))
        p.finish(origin=(sx * 0.2, 0.2, 0.17), parent=root)

    tail = Part("tail")
    paddle(tail, scales, y0=0.4, length=0.44, width=0.135)
    tail.finish(origin=(0, 0.42, 0.08), parent=root)
    return vertex_colours(root)


def horn(part, materials, centre, normal, R, r, start, arc, segs=42, around=8,
         tighten=0.22, flare=0.07):
    """A bighorn's curl: a tapering tube wound round `centre` in the plane
    facing `normal`, starting `start` degrees forward of straight up and
    sweeping back, down and round to the front. The curl tightens and flares
    outwards towards the tip, and every other ring is raised and darker,
    which gives the growth ridges."""
    mi = [part._mi(m) for m in materials]
    N = Vector(normal).normalized()
    up = Vector((0, 0, 1))
    V = (up - N * up.dot(N)).normalized()
    B = Vector((0, 1, 0))
    B = (B - N * B.dot(N)).normalized()

    def line(t):
        a = math.radians(start + arc * t)
        return Vector(centre) + (V * math.cos(a) + B * math.sin(a)) * R * (1 - tighten * t) + N * flare * t * t

    def ring(i):
        t = i / segs
        tan = (line(t + 0.004) - line(t - 0.004)).normalized()
        e2 = (N - tan * N.dot(tan)).normalized()
        e1 = e2.cross(tan)
        rr = r * (1 - 0.88 * t ** 1.15) * (1.07 if i % 2 else 0.95)
        c = line(t)
        return [part.bm.verts.new(c + e1 * math.cos(2 * math.pi * j / around) * rr * 1.12
                                  + e2 * math.sin(2 * math.pi * j / around) * rr * 0.92)
                for j in range(around)]

    prev = ring(0)
    for i in range(1, segs + 1):
        cur = ring(i)
        for j in range(around):
            k = (j + 1) % around
            f = part.bm.faces.new((prev[j], prev[k], cur[k], cur[j]))
            f.material_index = mi[(i // 2) % 2]
            f.smooth = True
        prev = cur
    part.bm.faces.new(list(reversed(prev))).material_index = mi[0]


def hoof(part, material, x, y, toe=0.024):
    """Cloven hoof standing on the ground at (x, y), toes pointing along -Y."""
    for s in (-1, 1):
        part.cone(material, loc=(x + s * toe, y, 0.009), r1=0.036, r2=0.025, depth=0.085,
                  rot=(-14, 0, s * 7), segs=6, scale=(0.72, 1.25, 1.0))
        part.sphere(material, loc=(x + s * toe, y + 0.045, 0.1), scale=0.012, segs=6, rings=4)   # dewclaw


def ram():
    rng = random.Random(23)
    crng = random.Random(9)          # colour dither, kept apart from the fur shapes
    root = empty("ram")
    coat = [mat("ram_coat_light", "#a08a70", 0.9), mat("ram_coat", "#917a63", 0.9),
            mat("ram_coat_dark", "#7a6551", 0.9), mat("ram_coat_shadow", "#574538", 0.9)]
    white = mat("ram_white", "#ece5d8", 0.9)
    face = [mat("ram_face", "#8f857c", 0.9), mat("ram_face_dark", "#6c625b", 0.9)]
    horns = [mat("ram_horn", "#cdb88c", 0.6), mat("ram_horn_dark", "#b6a177", 0.65)]
    hoof_m = mat("hoof", "#1d1a18", 0.5)
    nose_m = mat("nose_black", "#0c0a0a", 0.3)
    amber = mat("ram_eye", "#b47a22", 0.12)
    black = mat("eye_black", "#060606", 0.1)
    shine = mat("eye_shine", "#ffffff", 0.2, emit=1.0)

    back = Vector((0, 0.8, -0.6)).normalized()

    def flow(p, n):
        t = back - n * back.dot(n)
        return t.normalized() if t.length > 0.05 else Vector((0, 0, -1))

    def furry(part, samples, materials, length, radius, scale_fn=None):
        # a short dense coat, lying flat and combed back
        part.tufts(samples, materials, rng, length=length, radius=radius, droop=1.0,
                   scale_fn=scale_fn, flow=flow, lift=0.24, jitter=0.2)

    def paint(part, colours):
        # the hide under the tufts takes the darkest shade of the fur over it
        for f in part.bm.faces:
            f.material_index = part._mi(colours(f.calc_center_median(), f.normal, 0.0)[-1])

    # ---- body: deep chest, level back, white rump patch
    def body_coat(p, n, d):
        if p.y > 0.5 + d and p.z > 0.6:
            return [white]
        if n.z < -0.55 and p.y > -0.1:
            return [coat[0], white]
        if p.z < 0.7 + d and p.y < -0.05:
            return [coat[2], coat[3]]                    # dark brisket
        h = (p.z - 0.6) / 0.5 + d * 4
        if h > 0.72:
            return [coat[0], coat[0], coat[1]]
        return [coat[0], coat[1], coat[1], coat[2]] if h > 0.3 else [coat[1], coat[2]]

    def dither(colours, amount=0.05):
        return lambda p, n: colours(p, n, crng.uniform(-amount, amount))

    def body_shape(p):
        m = coat[0]
        p.sphere(m, loc=(0, -0.2, 0.82), scale=(0.265, 0.3, 0.3), segs=24, rings=16)     # chest
        p.sphere(m, loc=(0, 0.1, 0.81), scale=(0.28, 0.36, 0.285), segs=24, rings=16)    # barrel
        p.sphere(m, loc=(0, 0.4, 0.83), scale=(0.265, 0.27, 0.275), segs=24, rings=16)   # rump
        p.sphere(m, loc=(0, -0.3, 0.95), scale=(0.19, 0.2, 0.2), segs=20, rings=12)      # withers

    body = blob("body", body_shape, voxel=0.035, smooth_iter=8, tris=2200)
    samples = body.sample_surface(1000, rng)
    body.decimate(1100)
    body.mats = []
    body.bm.normal_update()
    paint(body, body_coat)
    furry(body, samples, dither(body_coat), (0.065, 0.11), (0.032, 0.05),
          scale_fn=lambda p, n: 0.0 if n.z < -0.9 else 0.7 if n.z < -0.4 else 1.0)
    body.finish(origin=(0, 0.1, 0.82), parent=root)

    # ---- head and neck in one piece, hinged at the shoulders so the game
    # can drop the horns for a charge
    skull = Vector((0, -0.62, 1.2))
    nose_tip = Vector((0, -0.94, 1.0))

    def head_shape(p):
        m = coat[0]
        p.sphere(m, loc=(0, -0.35, 0.94), scale=(0.2, 0.2, 0.23), segs=20, rings=12)      # neck base
        p.sphere(m, loc=(0, -0.46, 1.06), scale=(0.165, 0.17, 0.2), segs=20, rings=12)    # neck
        p.sphere(m, loc=(0, -0.56, 1.17), scale=(0.14, 0.15, 0.15), segs=20, rings=12)    # poll
        p.sphere(m, loc=tuple(skull), scale=(0.13, 0.16, 0.135), segs=20, rings=12)
        p.sphere(m, scale=(0.088, 0.092, 0.2), segs=16, rings=12,
                 matrix=align((0, -0.77, 1.105), (0, -0.85, -0.52)))                       # muzzle
        p.sphere(m, scale=(0.062, 0.05, 0.14), segs=14, rings=10,
                 matrix=align((0, -0.75, 1.045), (0, -0.9, -0.43)))                        # jaw

    def head_coat(p, n, d):
        if (p - nose_tip).length < 0.09 + d * 0.4:
            return [white]
        if p.y < -0.6 + d:
            return [face[0], face[0], face[1]]
        if p.y < -0.5:
            return [coat[1], face[0]]
        if n.y < -0.3 and p.z < 1.08:
            return [coat[1], coat[2], coat[2]]           # darker ruff down the front of the neck
        return [coat[0], coat[1], coat[1], coat[2]]

    head = blob("head", head_shape, voxel=0.025, smooth_iter=6, tris=1600)
    bvh = head.bvh()
    samples = head.sample_surface(440, rng)
    head.decimate(800)
    head.mats = []
    head.bm.normal_update()
    paint(head, head_coat)

    def surf(origin, direction):
        hit, n, _, _ = bvh.ray_cast(Vector(origin), Vector(direction).normalized())
        return hit, n

    bare = []                           # (centre, radius) spots the fur keeps clear of
    extras = []                         # (part, origin) hung off the head once it exists
    for sx, side in ((1, "L"), (-1, "R")):
        d = Vector((sx * 0.8, -0.52, 0.16)).normalized()
        hit, n = surf(skull + d, -d)
        bare.append((hit, 0.055))
        m = align(hit, n)
        head.sphere(face[1], scale=(0.042, 0.042, 0.012), segs=12, rings=6, matrix=m)     # socket
        e = Part("eye_" + side)
        e.sphere(amber, loc=(0, 0, 0.004), scale=(0.03, 0.03, 0.021), segs=12, rings=8, matrix=m)
        e.sphere(black, loc=(0, 0, 0.017), scale=(0.018, 0.0075, 0.01), segs=8, rings=6, matrix=m)   # level pupil
        e.sphere(shine, loc=tuple(hit + n * 0.024 + Vector((0, -0.01, 0.011))), scale=0.007, segs=6, rings=4)
        extras.append((e, hit.copy()))

        base = Vector((sx * 0.105, -0.535, 1.205))                                         # ears
        bare.append((base, 0.05))
        out = Vector((sx * 0.92, 0.3, 0.22))
        e = Part("ear_" + side)
        m = align(base, out, up=(0, -1, 0.3))
        e.sphere(coat[2], loc=(0, 0, 0.075), scale=(0.036, 0.018, 0.075), segs=10, rings=8, matrix=m)
        e.sphere(face[1], loc=(0, 0.008, 0.078), scale=(0.022, 0.012, 0.055), segs=8, rings=6, matrix=m)
        extras.append((e, base))

        # horns: bases nearly meet on top of the skull, the curls lean out below
        N = Vector((sx, 0, 0.4)).normalized()
        centre = Vector((sx * 0.15, -0.485, 1.14))
        bare.append((Vector((sx * 0.085, -0.57, 1.31)), 0.1))
        horn(head, horns, centre, N, R=0.2, r=0.086, start=-25, arc=292)

    hit, n = surf((0, -3, 1.01), (0, 1, 0))                                                # nose
    bare.append((hit, 0.05))
    m = align(hit, n)
    head.sphere(nose_m, loc=(0, 0.004, 0.0), scale=(0.034, 0.02, 0.012), segs=10, rings=6, matrix=m)
    for sx in (-1, 1):
        head.sphere(nose_m, loc=(sx * 0.024, 0.014, 0.002), scale=(0.015, 0.009, 0.01),
                    rot=(0, 0, sx * 35), segs=8, rings=6, matrix=m)
    head.box(nose_m, loc=(0, -0.024, 0.0), scale=(0.005, 0.02, 0.006), matrix=m)           # split lip
    hit, n = surf((0, -3, 0.962), (0, 1, 0))
    head.sphere(nose_m, scale=(0.04, 0.006, 0.006), segs=8, rings=4, matrix=align(hit, n))   # mouth

    def head_fur(p, n):
        for c, r in bare:
            if (p - c).length < r:
                return 0.0
        if p.y < -0.6:
            return 0.42                                  # short on the face
        return 1.25 if n.y < -0.3 and p.z < 1.08 else 1.0

    furry(head, samples, dither(head_coat, 0.03), (0.055, 0.095), (0.026, 0.04), scale_fn=head_fur)
    head_ob = head.finish(origin=(0, -0.33, 0.93), parent=root)
    for e, at in extras:
        e.finish(origin=tuple(at), parent=head_ob)

    # ---- legs: a furred upper leg hinged at the body, and a slim cannon
    # bone on its own hinge (shin_*) so knees and hocks can fold
    def leg_coat(p, n, d):
        if p.y > 0.52 + d:
            return [white]                               # the rump patch runs down the back of the thigh
        return [coat[1], coat[2], coat[2], coat[3]]

    for sx, side in ((1, "L"), (-1, "R")):
        x = sx * 0.165
        knee = Vector((x, -0.28, 0.34))
        p = Part("leg_F" + side)
        p.sphere(coat[1], loc=(sx * 0.175, -0.27, 0.66), scale=(0.085, 0.12, 0.17), segs=12, rings=8)
        seg(p, coat[2], (sx * 0.17, -0.275, 0.6), knee, 0.08, 0.054)
        samples = [s for s in p.sample_surface(80, rng) if s[1].x * sx > -0.5 and s[0].z > 0.36]
        p.sphere(coat[2], loc=tuple(knee), scale=(0.056, 0.058, 0.06), segs=10, rings=8)
        furry(p, samples, dither(leg_coat), (0.05, 0.09), (0.024, 0.036))
        leg = p.finish(origin=(sx * 0.16, -0.27, 0.68), parent=root)

        p = Part("shin_F" + side)
        fet = Vector((x, -0.285, 0.105))
        seg(p, coat[3], knee, fet, 0.048, 0.04)
        p.sphere(coat[3], loc=tuple(fet), scale=(0.047, 0.052, 0.05), segs=10, rings=8)
        hoof(p, hoof_m, x, -0.3)
        p.finish(origin=tuple(knee), parent=leg)

        x = sx * 0.17
        hock = Vector((x, 0.5, 0.38))
        p = Part("leg_B" + side)
        p.sphere(coat[1], loc=(sx * 0.18, 0.38, 0.73), scale=(0.11, 0.17, 0.2), segs=14, rings=10)   # haunch
        seg(p, coat[2], (sx * 0.175, 0.4, 0.62), hock, 0.088, 0.052)                                 # gaskin
        samples = [s for s in p.sample_surface(120, rng) if s[1].x * sx > -0.5 and s[0].z > 0.4]
        p.sphere(coat[2], loc=tuple(hock), scale=(0.053, 0.062, 0.06), segs=10, rings=8)
        furry(p, samples, dither(leg_coat), (0.05, 0.1), (0.026, 0.04))
        leg = p.finish(origin=(x, 0.4, 0.74), parent=root)

        p = Part("shin_B" + side)
        fet = Vector((x, 0.465, 0.105))
        seg(p, coat[3], hock, fet, 0.049, 0.04)
        seg(p, white, hock + Vector((0, 0.034, -0.02)), fet + Vector((0, 0.026, 0.01)), 0.022, 0.018, segs=6)   # pale back edge
        p.sphere(coat[3], loc=tuple(fet), scale=(0.047, 0.052, 0.05), segs=10, rings=8)
        hoof(p, hoof_m, x, 0.45)
        p.finish(origin=tuple(hock), parent=leg)

    tail = Part("tail")
    tail.sphere(coat[3], loc=(0, 0.69, 0.85), scale=(0.035, 0.03, 0.075), rot=(12, 0, 0), segs=8, rings=6)
    tail.finish(origin=(0, 0.66, 0.91), parent=root)
    return vertex_colours(root)


def porcupine():
    rng = random.Random(3)
    crng = random.Random(17)         # colour dither, kept apart from the fur shapes
    root = empty("porcupine")
    under = mat("porc_under", "#241b17", 0.95)
    dark = [mat("porc_fur", "#4a372b", 0.95), mat("porc_fur_dark", "#30231c", 0.95)]
    straw = mat("porc_straw", "#d9bf7c", 0.8)
    cream = mat("porc_cream", "#efe5c0", 0.8)
    tan = mat("porc_tan", "#a98c59", 0.85)
    rust = [mat("porc_rust", "#b3672e", 0.85), mat("porc_rust_dark", "#8a4a23", 0.9)]
    quill = mat("porc_quill", "#eadfb9", 0.6)
    quill_tip = mat("porc_quill_dark", "#1d1713", 0.6)
    snout = mat("porc_snout", "#5c4334", 0.8)
    nose_m = mat("porc_nose", "#171112", 0.3)
    hole = mat("mouth_dark", "#020202", 1.0)
    tooth = mat("porc_tooth", "#e2892b", 0.3)
    claw = mat("porc_claw", "#5b5556", 0.4)
    black = mat("eye_black", "#060606", 0.1)
    shine = mat("eye_shine", "#ffffff", 0.2, emit=1.0)

    back = Vector((0, 0.9, -0.42)).normalized()

    def flow(p, n):
        t = back - n * back.dot(n)
        return t.normalized() if t.length > 0.05 else Vector((0, 0, -1))

    def grounded(part):
        for v in part.bm.verts:          # nothing hangs through the ground
            v.co.z = max(v.co.z, 0.004)

    def guard_hair(part, samples, materials, length, scale_fn=None, lift=0.8, radius=(0.012, 0.02)):
        # long thin hairs standing off the body and sweeping back
        part.tufts(samples, materials, rng, length=length, radius=radius, droop=0.9,
                   scale_fn=scale_fn, flow=flow, lift=lift, jitter=0.25)
        grounded(part)

    def quills(part, samples, length, sink=0.07):
        # white shafts with dark tips, raked back; rooted well inside the body
        # so the game can push them out to bristle
        rake = Vector((0, 0.9, 0.38))
        for p, n in samples:
            d = (n + rake * 0.6).normalized()
            L = rng.uniform(*length) + sink
            m = align(p - d * sink, d)
            part.cone(quill, r1=0.012, r2=0.009, depth=L * 0.74, segs=3, matrix=m, caps=False, smooth=False)
            part.cone(quill_tip, loc=(0, 0, L * 0.74), r1=0.009, r2=0.0, depth=L * 0.26, segs=3,
                      matrix=m, caps=False, smooth=False)

    # ---- body: a low hunched dome of dark underfur
    def body_shape(p):
        p.sphere(under, loc=(0, 0.08, 0.25), scale=(0.27, 0.35, 0.23), segs=24, rings=16)
        p.sphere(under, loc=(0, -0.17, 0.225), scale=(0.21, 0.22, 0.195), segs=20, rings=12)   # shoulders
        p.sphere(under, loc=(0, 0.36, 0.17), scale=(0.15, 0.15, 0.13), segs=16, rings=10)      # tail root

    def body_coat(p, n):
        d = crng.uniform(-0.05, 0.05)
        if p.z < 0.2 + d:
            return [straw, straw, cream, tan]            # pale skirt along the flanks
        if p.y < -0.1 + d:
            return [straw, cream, straw, rust[0]]        # yellow mantle over the shoulders
        if p.y < 0.22 + d * 2:
            return [rust[0], rust[0], rust[1], straw]    # rusty saddle
        return [dark[0], dark[1], tan, straw]            # dark rump, where the quills show

    body = blob("body", body_shape, voxel=0.03, smooth_iter=8, tris=1600)
    body.mats = [under]
    q_samples = [s for s in body.sample_surface(620, rng) if s[1].z > -0.05]
    h_samples = body.sample_surface(640, rng)
    body.decimate(800)
    guard_hair(body, h_samples, body_coat, (0.13, 0.23), lift=0.7,
               scale_fn=lambda p, n: 0.0 if n.z < -0.7 else 0.55 if p.z < 0.15 else 0.75 if p.y > 0.2 else 1.0)
    body.finish(origin=(0, 0.05, 0.25), parent=root)

    q = Part("quills")
    quills(q, [s for s in q_samples if s[0].y > 0.02 or rng.random() < 0.3], (0.1, 0.17))
    q.finish(origin=(0, 0.05, 0.25), parent=root)

    # ---- head: small dark face under a crest of pale hair
    skull = Vector((0, -0.36, 0.215))

    def head_shape(p):
        p.sphere(under, loc=tuple(skull), scale=(0.135, 0.15, 0.125), segs=20, rings=12)
        p.sphere(under, loc=(0, -0.475, 0.185), scale=(0.085, 0.08, 0.075), segs=16, rings=12)   # muzzle
        for sx in (-1, 1):
            p.sphere(under, loc=(sx * 0.07, -0.42, 0.18), scale=(0.07, 0.075, 0.065), segs=14, rings=10)   # cheeks

    head = blob("head", head_shape, voxel=0.02, smooth_iter=6, tris=1040)
    head.mats = [dark[1]]
    bvh = head.bvh()
    samples = head.sample_surface(300, rng)
    head.decimate(520)
    for f in head.bm.faces:
        if f.calc_center_median().y < -0.46:
            f.material_index = head._mi(snout)

    def surf(origin, direction):
        hit, n, _, _ = bvh.ray_cast(Vector(origin), Vector(direction).normalized())
        return hit, n

    bare = []
    eye_parts = []
    for sx, side in ((1, "L"), (-1, "R")):
        d = Vector((sx * 0.8, -0.55, 0.36)).normalized()
        hit, n = surf(skull + d, -d)
        bare.append((hit, 0.045))
        head.sphere(under, scale=(0.03, 0.03, 0.01), segs=10, rings=6, matrix=align(hit, n))
        e = Part("eye_" + side)
        e.sphere(black, loc=(0, 0, 0.004), scale=(0.021, 0.021, 0.017), segs=10, rings=8, matrix=align(hit, n))
        e.sphere(shine, loc=tuple(hit + n * 0.017 + Vector((0, -0.007, 0.007))), scale=0.006, segs=6, rings=4)
        eye_parts.append((e, hit.copy()))

        d = Vector((sx * 0.85, 0.3, 0.5)).normalized()                                          # ears
        hit, n = surf(skull + d, -d)
        head.sphere(dark[1], loc=tuple(hit + n * 0.018), scale=(0.035, 0.018, 0.035), rot=(0, 0, sx * 25), segs=8, rings=6)

        for i in range(3):                                                                       # whiskers
            d = Vector((sx * 0.75, -0.6, -0.25 + 0.13 * i)).normalized()
            hit, n = surf(Vector((0, -0.45, 0.19)) + d, -d)
            out = Vector((sx * 0.9, -0.35, -0.25 + 0.2 * i))
            head.cone(tan, r1=0.004, r2=0.0, depth=rng.uniform(0.09, 0.12), segs=3,
                      matrix=align(hit - n * 0.005, out), caps=False, smooth=False)

    hit, n = surf((0, -3, 0.205), (0, 1, 0))                                                    # nose
    bare.append((hit, 0.055))
    m = align(hit, n)
    head.sphere(nose_m, loc=(0, 0.004, 0.003), scale=(0.04, 0.03, 0.024), power=0.85, segs=12, rings=8, matrix=m)
    for sx in (-1, 1):
        head.sphere(hole, loc=(sx * 0.016, -0.003, 0.022), scale=(0.008, 0.009, 0.006), segs=8, rings=6, matrix=m)
    hit, n = surf((0, -3, 0.148), (0, 1, 0))                                                    # incisors
    bare.append((hit, 0.035))
    m = align(hit, n)
    head.sphere(hole, loc=(0, -0.012, 0.0), scale=(0.026, 0.018, 0.009), segs=10, rings=6, matrix=m)
    for sx in (-1, 1):
        head.sphere(tooth, loc=(sx * 0.0095, -0.004, 0.008), scale=(0.009, 0.019, 0.007), power=0.55,
                    segs=8, rings=6, matrix=m)

    def crest(p, n):
        return p.y > -0.41 and n.z > 0.05

    def head_coat(p, n):
        if crest(p, n):
            return [straw, cream, straw, tan]
        return [snout, dark[0]] if p.y < -0.46 else [dark[0], dark[1]]

    def head_fur(p, n):
        for c, r in bare:
            if (p - c).length < r:
                return 0.0
        return 1.0 if crest(p, n) else 0.26               # short on the face, long behind it

    guard_hair(head, samples, head_coat, (0.12, 0.2), scale_fn=head_fur, radius=(0.014, 0.022))
    head_ob = head.finish(origin=(0, -0.27, 0.22), parent=root)
    for e, at in eye_parts:
        e.finish(origin=tuple(at), parent=head_ob)

    # ---- legs: short, dark and shaggy, with long climbing claws
    def leg_fur(part, samples):
        part.tufts(samples, dark, rng, length=(0.04, 0.08), radius=(0.02, 0.03), droop=1.0,
                   flow=flow, lift=0.5, jitter=0.25)
        grounded(part)

    for sx, side in ((1, "L"), (-1, "R")):
        p = Part("leg_F" + side)
        p.sphere(dark[1], loc=(sx * 0.18, -0.24, 0.115), scale=(0.062, 0.075, 0.085), segs=12, rings=8)
        samples = [s for s in p.sample_surface(40, rng) if s[1].x * sx > -0.4]
        seg(p, dark[1], (sx * 0.185, -0.25, 0.09), (sx * 0.195, -0.275, 0.03), 0.042, 0.032)
        m = TRS((sx * 0.195, -0.275, 0.0), rot=(0, 0, sx * 14))
        p.sphere(under, loc=(0, -0.012, 0.022), scale=(0.04, 0.048, 0.022), segs=10, rings=6, matrix=m)
        paw(p, under, claw, m, (-33, -11, 11, 33), 0.085, 0.011, claw_len=4.2)
        leg_fur(p, samples)
        p.finish(origin=(sx * 0.17, -0.24, 0.14), parent=root)

        p = Part("leg_B" + side)
        p.sphere(dark[1], loc=(sx * 0.21, 0.2, 0.125), scale=(0.08, 0.115, 0.105), segs=12, rings=8)
        samples = [s for s in p.sample_surface(52, rng) if s[1].x * sx > -0.4]
        m = TRS((sx * 0.23, 0.2, 0.0), rot=(0, 0, sx * 16))
        p.sphere(under, loc=(0, -0.03, 0.022), scale=(0.045, 0.075, 0.022), segs=10, rings=6, matrix=m)   # long sole
        paw(p, under, claw, m, (-32, -16, 0, 16, 32), 0.13, 0.011, claw_len=3.6)
        leg_fur(p, samples)
        p.finish(origin=(sx * 0.2, 0.2, 0.14), parent=root)

    # ---- tail: a heavy club, pale along the sides and bristling on top
    tail = Part("tail")
    seg(tail, under, (0, 0.38, 0.15), (0, 0.7, 0.075), 0.105, 0.06, segs=10)
    tail.sphere(under, loc=(0, 0.7, 0.075), scale=(0.06, 0.07, 0.055), segs=10, rings=8)
    samples = [s for s in tail.sample_surface(210, rng) if s[0].y > 0.42]
    quills(tail, [s for s in samples[:90] if s[1].z > 0.0], (0.07, 0.12), sink=0.03)
    guard_hair(tail, samples[90:], lambda p, n: [dark[0], dark[1], tan] if abs(n.x) < 0.45 and n.z > 0 else [straw, straw, tan, cream],
               (0.1, 0.17), scale_fn=lambda p, n: 0.0 if n.z < -0.6 else 1.0, lift=0.6)
    tail.finish(origin=(0, 0.38, 0.15), parent=root)
    return vertex_colours(root)


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
    asset("beaver", view=(-0.9, -1.0, 0.35), zoom=1.3)(beaver)
    asset("ram", view=(-1.0, -0.45, 0.15), zoom=1.3)(ram)
    asset("porcupine", view=(-0.9, -1.0, 0.4), zoom=1.4)(porcupine)
    asset("eagle", view=(-0.6, -1.0, 0.6), zoom=1.4)(eagle)

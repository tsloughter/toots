"""Rocky Mountain scenery, platforms and pickups.

Ground/ledge pieces: top surface at z=0, gameplay plane at y=0, camera side is -Y.
"""
import math
import random
import bmesh
from mathutils import Vector, noise
from lib import Part, mat, empty, align, face_key, TRS


def fbm(v, octaves=4):
    total, amp, freq = 0.0, 0.5, 1.0
    for _ in range(octaves):
        total += amp * noise.noise(v * freq)
        amp *= 0.5
        freq *= 2.0
    return total


def rock_chunk(part, materials, rng, loc=(0, 0, 0), scale=(1, 1, 1), rough=0.28, subdiv=2,
               rot=(0, 0, 0), cut_top=False):
    tmp = bmesh.new()
    bmesh.ops.create_icosphere(tmp, subdivisions=subdiv, radius=1.0)
    seed = Vector((rng.uniform(-50, 50), rng.uniform(-50, 50), rng.uniform(-50, 50)))
    for v in tmp.verts:
        v.co *= 1.0 + rough * 2.0 * fbm(v.co * 1.3 + seed, 3)
    if cut_top:
        geom = list(tmp.verts) + list(tmp.edges) + list(tmp.faces)
        bmesh.ops.bisect_plane(tmp, geom=geom, plane_co=(0, 0, 0), plane_no=(0, 0, 1), clear_outer=True)
        # the cut runs straight through the icosphere's equator verts and leaves
        # doubled verts and zero-area faces along it: weld them before capping
        bmesh.ops.remove_doubles(tmp, verts=tmp.verts, dist=1e-6)
        bmesh.ops.holes_fill(tmp, edges=[e for e in tmp.edges if e.is_boundary])
    groups = {}
    for f in sorted(tmp.faces, key=face_key):
        groups.setdefault(rng.choice(materials), []).append(f)
    m = TRS(loc, rot, scale)
    # merge per material so each face keeps its tone
    for material, faces in groups.items():
        t2 = bmesh.new()
        vmap = {}
        for f in faces:
            vs = []
            for v in f.verts:
                if v not in vmap:
                    vmap[v] = t2.verts.new(v.co)
                vs.append(vmap[v])
            t2.faces.new(vs)
        part.merge(t2, m, material, smooth=False)
    tmp.free()


def rock_mats():
    return [mat("rock_a", "#8a8d92", 0.95), mat("rock_b", "#74777d", 0.95), mat("rock_c", "#9b9c9a", 0.95)]


def rock(seed, squash=0.7):
    def fn():
        rng = random.Random(seed)
        root = empty("rock")
        p = Part("rock_mesh")
        rock_chunk(p, rock_mats(), rng, loc=(0, 0, 0.32), scale=(0.6, 0.5, 0.6 * squash))
        rock_chunk(p, rock_mats(), rng, loc=(0.45, 0.1, 0.16), scale=(0.3, 0.3, 0.26), subdiv=1)
        p.finish(parent=root)
        return root
    return fn


def pine(seed, height=3.2, tiers=5, snowy=False):
    def fn():
        rng = random.Random(seed)
        root = empty("pine")
        p = Part("pine_mesh")
        bark = mat("bark", "#4a3423", 0.95)
        greens = [mat("pine_a", "#1f4a2c", 0.9), mat("pine_b", "#28593a", 0.9), mat("pine_c", "#173d27", 0.9)]
        snow = mat("snow", "#f4f8fc", 0.6)
        p.cone(bark, r1=0.14, r2=0.06, depth=height * 0.5, segs=6, smooth=False)
        z = height * 0.2
        for i in range(tiers):
            t = i / (tiers - 1)
            r = (0.95 - 0.68 * t) * height * 0.3
            d = height * 0.34 * (1.0 - 0.3 * t)
            g = greens[i % 3]
            p.cone(g, loc=(rng.uniform(-0.03, 0.03), rng.uniform(-0.03, 0.03), z), r1=r, r2=0.0, depth=d,
                   segs=7, rot=(rng.uniform(-4, 4), rng.uniform(-4, 4), rng.uniform(0, 50)), smooth=False)
            if snowy:
                p.cone(snow, loc=(0, 0, z + d * 0.45), r1=r * 0.56, r2=0.0, depth=d * 0.56, segs=7,
                       rot=(0, 0, rng.uniform(0, 50)), smooth=False)
            z += d * 0.52
        p.finish(parent=root)
        return root
    return fn


def mountain(seed, peaks, snowline=0.52, treeline=0.2):
    """Jagged low-poly massif about 2 units across; scale it up in the game."""
    def fn():
        rng = random.Random(seed)
        off = Vector((seed * 13.7, seed * 7.1, seed * 3.3))
        root = empty("mountain")
        p = Part("mountain_mesh")
        snow = mat("snow", "#f4f8fc", 0.6)
        rock_l = mat("mtn_rock_light", "#7f8794", 0.95)
        rock_d = mat("mtn_rock_dark", "#5f6876", 0.95)
        forest = mat("mtn_forest", "#2a4d3a", 0.95)
        forest_d = mat("mtn_forest_dark", "#213f32", 0.95)
        N = 34
        span = 1.3

        def height(x, y):
            v = 0.0
            for px, py, ph, pr in peaks:
                d = math.hypot(x - px, (y - py) * 1.25) / pr
                v = max(v, ph * max(0.0, 1.0 - d) ** 1.2)
            q = Vector((x * 2.6, y * 2.6, 0.0)) + off
            ridge = 1.0 - abs(noise.noise(q * 1.7))
            return v * (0.72 + 0.4 * ridge + 0.5 * fbm(q, 4))

        grid = []
        for j in range(N + 1):
            row = []
            for i in range(N + 1):
                x = -span + 2 * span * i / N + rng.uniform(-0.02, 0.02)
                y = -span + 2 * span * j / N + rng.uniform(-0.02, 0.02)
                row.append(p.bm.verts.new((x, y, max(0.0, height(x, y)))))
            grid.append(row)
        for j in range(N):
            for i in range(N):
                a, b, c, d = grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]
                tris = ((a, b, c), (a, c, d)) if (i + j) % 2 else ((a, b, d), (b, c, d))
                for t in tris:
                    if max(v.co.z for v in t) <= 0.004:
                        continue
                    f = p.bm.faces.new(t)
                    f.smooth = False
                    f.normal_update()
                    cz = sum(v.co.z for v in t) / 3
                    cx = sum(v.co.x for v in t) / 3
                    wob = 0.07 * noise.noise(Vector((cx * 5, cz * 5, seed)))
                    if cz > snowline + wob and f.normal.z > 0.42:
                        m = snow
                    elif cz < treeline + wob:
                        m = forest if rng.random() < 0.6 else forest_d
                    else:
                        m = rock_l if rng.random() < 0.55 else rock_d
                    f.material_index = p._mi(m)
        for v in list(p.bm.verts):
            if not v.link_faces:
                p.bm.verts.remove(v)
        p.finish(parent=root)
        return root
    return fn


def hill(seed):
    """Forested foothill for the middle distance."""
    def fn():
        rng = random.Random(seed)
        root = empty("hill")
        p = Part("hill_mesh")
        greens = [mat("hill_a", "#2f5a3c", 0.95), mat("hill_b", "#28503a", 0.95), mat("hill_c", "#38683f", 0.95)]
        rock_chunk(p, greens, rng, loc=(0, 0, -0.1), scale=(1.0, 0.7, 0.55), rough=0.2, subdiv=3)
        geom = list(p.bm.verts) + list(p.bm.edges) + list(p.bm.faces)
        bmesh.ops.bisect_plane(p.bm, geom=geom, plane_co=(0, 0, 0), plane_no=(0, 0, -1), clear_outer=True)
        # stud it with tiny trees so it reads as forest
        dark = [mat("pine_a", "#1f4a2c", 0.9), mat("pine_c", "#173d27", 0.9)]
        for pt, n in p.sample_surface(140, rng):
            if n.z < 0.35 or pt.z < 0.03:
                continue
            p.cone(rng.choice(dark), loc=pt, r1=0.035, r2=0.0, depth=rng.uniform(0.1, 0.16), segs=5, smooth=False)
        p.finish(parent=root)
        return root
    return fn


def cloud(seed):
    def fn():
        rng = random.Random(seed)
        root = empty("cloud")
        p = Part("cloud_mesh")
        white = mat("cloud", "#ffffff", 1.0, emit=0.25)
        x = -0.9
        for i in range(5):
            r = rng.uniform(0.35, 0.6) * (1.0 - 0.25 * abs(i - 2))
            p.sphere(white, loc=(x, rng.uniform(-0.1, 0.1), r * 0.55), scale=(r * 1.2, r * 0.8, r * 0.8), segs=12, rings=8)
            x += r * 1.0
        p.sphere(white, loc=(-0.1, 0, 0.12), scale=(1.15, 0.45, 0.2), segs=12, rings=6)
        p.finish(parent=root)
        return root
    return fn


GRASS = ("grass", "#5fa043", 0.95)
GRASS_D = ("grass_dark", "#4a8738", 0.95)
DIRT = ("dirt", "#6b4a30", 0.95)


def fringe(part, grass_mats, rng, x0, x1, y, z, teeth_w=0.33):
    """Zig-zag grass hanging over the front edge."""
    n = max(2, round((x1 - x0) / teeth_w))
    w = (x1 - x0) / n
    for i in range(n):
        a = x0 + i * w
        d = rng.uniform(0.14, 0.34)
        vs = [part.bm.verts.new((a, y, z)), part.bm.verts.new((a + w * rng.uniform(0.35, 0.65), y - 0.02, z - d)),
              part.bm.verts.new((a + w, y, z))]
        f = part.bm.faces.new(vs)
        f.material_index = part._mi(rng.choice(grass_mats))
        f.smooth = False


def ground(seed, depth=18.0, front=-2.0, back=7.0):
    """2-wide cliff tile. Edges at x=+-1 are undisplaced so tiles butt together."""
    def fn():
        rng = random.Random(seed)
        root = empty("ground")
        p = Part("ground_mesh")
        grass = [mat(*GRASS), mat(*GRASS_D)]
        dirt = mat(*DIRT)
        rocks = [mat("cliff_a", "#7d7770", 0.95), mat("cliff_b", "#6c6761", 0.95), mat("cliff_c", "#8b857c", 0.95)]
        strata = mat("cliff_strata", "#59544f", 0.95)
        # grass cap with a slightly bumpy top behind the walk line
        p.box(grass[0], loc=(0, (front + back) / 2 - 0.1, -0.11), scale=(1.0, (back - front) / 2 + 0.1, 0.11))
        fringe(p, grass, rng, -1.0, 1.0, front - 0.21, -0.2)
        p.box(dirt, loc=(0, (front + back) / 2 - 0.03, -0.42), scale=(1.0, (back - front) / 2 + 0.03, 0.2))
        # rock face
        cols, rows = 4, 14
        top = -0.6
        off = Vector((seed * 9.1, 0, seed * 4.7))
        verts = []
        for j in range(rows + 1):
            z = top - (depth + top) * (j / rows) ** 1.25
            row = []
            for i in range(cols + 1):
                x = -1.0 + 2.0 * i / cols
                edge = 1.0 - abs(x)
                bulge = (0.3 + 0.9 * fbm(Vector((x * 1.1, 0, z * 0.45)) + off, 3)) * min(1.0, edge * 2.2)
                jx = rng.uniform(-0.12, 0.12) if 0 < i < cols else 0.0
                row.append(p.bm.verts.new((x + jx, front - max(0.0, bulge) * 0.75, z)))
            verts.append(row)
        for j in range(rows):
            band = strata if rng.random() < 0.18 else None
            for i in range(cols):
                a, b, c, d = verts[j][i], verts[j][i + 1], verts[j + 1][i + 1], verts[j + 1][i]
                for t in (((a, d, c), (a, c, b)) if (i + j) % 2 else ((a, d, b), (d, c, b))):
                    f = p.bm.faces.new(t)
                    f.smooth = False
                    f.material_index = p._mi(band or rng.choice(rocks))
        # shelf from the top of the bulging face back to the wall, so you can't
        # see down behind it (the face is a single-sided sheet)
        lip = [v if abs(v.co.y - front) < 1e-6 else p.bm.verts.new((v.co.x, front, top)) for v in verts[0]]
        for i in range(cols):
            ring = list(dict.fromkeys((verts[0][i], verts[0][i + 1], lip[i + 1], lip[i])))
            if len(ring) >= 3:
                f = p.bm.faces.new(ring)
                f.smooth = False
                f.material_index = p._mi(rocks[1])
        # plain sides (only seen at the lip of a hole)
        for sx in (-1, 1):
            p.box(rocks[1], loc=(sx * 0.995, (front + back) / 2, (top - depth) / 2),
                  scale=(0.005, (back - front) / 2, (depth + top) / 2))
        p.finish(parent=root)
        return root
    return fn


def ledge(width, seed):
    """Floating grass-topped slab, `width` units wide."""
    def fn():
        rng = random.Random(seed)
        root = empty("ledge")
        p = Part("ledge_mesh")
        grass = [mat(*GRASS), mat(*GRASS_D)]
        rocks = [mat("cliff_a", "#7d7770", 0.95), mat("cliff_b", "#6c6761", 0.95), mat("cliff_c", "#8b857c", 0.95)]
        hw = width / 2
        p.box(grass[0], loc=(0, 0, -0.09), scale=(hw, 1.25, 0.09), bevel=0.04)
        fringe(p, grass, rng, -hw + 0.05, hw - 0.05, -1.26, -0.15, teeth_w=0.3)
        rock_chunk(p, rocks, rng, loc=(0, 0, -0.16), scale=(hw * 0.96, 1.15, 0.75), rough=0.22, subdiv=2, cut_top=True)
        rock_chunk(p, rocks, rng, loc=(rng.uniform(-0.3, 0.3) * hw, 0.1, -0.5), scale=(hw * 0.5, 0.7, 0.75),
                   rough=0.25, subdiv=2, cut_top=True)
        p.finish(parent=root)
        return root
    return fn


def berry():
    root = empty("berry")
    p = Part("berry_mesh")
    skin = mat("huckleberry", "#4b2f9e", 0.25, emit=0.25)
    crown = mat("huckleberry_crown", "#2a1a5e", 0.5)
    leaf = mat("leaf", "#4f9a3c", 0.7)
    p.sphere(skin, loc=(0, 0, 0), scale=0.2, segs=16, rings=12)
    p.sphere(mat("berry_shine", "#cfc4ff", 0.2, emit=0.6), loc=(-0.07, -0.13, 0.09), scale=(0.04, 0.03, 0.05), segs=8, rings=6)
    p.cone(crown, loc=(0, 0, 0.17), r1=0.07, r2=0.09, depth=0.05, segs=5, smooth=False)
    p.cone(mat("bark", "#4a3423", 0.95), loc=(0, 0, 0.2), r1=0.015, r2=0.012, depth=0.1, segs=5, rot=(0, 15, 0))
    p.sphere(leaf, loc=(0.1, 0, 0.3), scale=(0.11, 0.05, 0.015), rot=(0, -25, 0), segs=10, rings=6)
    p.finish(parent=root)
    return root


def beans():
    root = empty("beans")
    p = Part("beans_mesh")
    tin = mat("tin", "#c9ccd2", 0.25, metal=0.9)
    label = mat("bean_label", "#c7402a", 0.6)
    cream = mat("bean_cream", "#f3e3b8", 0.6)
    bean = mat("bean_brown", "#8a4a22", 0.35)
    p.cone(tin, loc=(0, 0, -0.26), r1=0.2, r2=0.2, depth=0.52, segs=20)
    p.cone(label, loc=(0, 0, -0.2), r1=0.205, r2=0.205, depth=0.4, segs=20, caps=False)
    p.cone(cream, loc=(0, 0, -0.09), r1=0.208, r2=0.208, depth=0.18, segs=20, caps=False)
    for z in (-0.26, 0.24):
        p.torus(tin, loc=(0, 0, z), R=0.2, r=0.016, segs=20, tube=6)
    # a fat bean on the label, front and back
    for sy in (-1, 1):
        p.sphere(bean, loc=(0, sy * 0.2, 0.0), scale=(0.1, 0.035, 0.06), rot=(0, 20, 0), segs=12, rings=8)
        p.sphere(cream, loc=(0.01, sy * 0.225, 0.02), scale=(0.035, 0.012, 0.018), rot=(0, 20, 0), segs=8, rings=6)
    p.finish(parent=root)
    return root


def summit():
    """Goal: a cairn with a flag on the summit."""
    rng = random.Random(11)
    root = empty("summit")
    p = Part("cairn")
    rm = rock_mats()
    z = 0.0
    for i, s in enumerate((0.55, 0.45, 0.36, 0.27, 0.19)):
        rock_chunk(p, rm, rng, loc=(rng.uniform(-0.05, 0.05), rng.uniform(-0.05, 0.05), z + s * 0.4),
                   scale=(s, s * 0.9, s * 0.45), subdiv=1, rough=0.2, rot=(0, 0, rng.uniform(0, 90)))
        z += s * 0.72
    wood = mat("wood", "#7a5a3a", 0.9)
    p.cone(wood, loc=(0, 0.05, 0.3), r1=0.045, r2=0.035, depth=3.4, segs=8)
    p.sphere(mat("gold", "#f5c542", 0.3, metal=0.8), loc=(0, 0.05, 3.74), scale=0.08, segs=10, rings=8)
    p.finish(parent=root)
    f = Part("flag")
    red = mat("flag_red", "#d83a2e", 0.8)
    white = mat("flag_white", "#f6f2e8", 0.8)
    # wavy pennant made of strips so the game can wiggle the whole thing
    n = 10
    for i in range(n):
        t0, t1 = i / n, (i + 1) / n
        w0, w1 = math.sin(t0 * 7) * 0.07 * t0, math.sin(t1 * 7) * 0.07 * t1
        h0, h1 = 0.38 * (1 - t0 * 0.75), 0.38 * (1 - t1 * 0.75)
        o = Vector((0.04, 0.05, 3.3))
        vs = [f.bm.verts.new(o + Vector(c)) for c in ((t0 * 1.3, w0, -h0), (t1 * 1.3, w1, -h1),
                                                     (t1 * 1.3, w1, h1), (t0 * 1.3, w0, h0))]
        for order in (vs, list(reversed(vs))):
            try:
                face = f.bm.faces.new(order)
            except ValueError:
                face = f.bm.faces.new([f.bm.verts.new(v.co + Vector((0, 0.002, 0))) for v in order])
            face.material_index = f._mi(white if i in (2, 3) else red)
            face.smooth = True
    f.finish(origin=(0.04, 0.05, 3.3), parent=root)
    return root


def signpost():
    """Checkpoint trail marker."""
    root = empty("signpost")
    p = Part("post")
    wood = mat("wood", "#7a5a3a", 0.9)
    wood_d = mat("wood_dark", "#5e432b", 0.9)
    p.cone(wood_d, r1=0.07, r2=0.06, depth=1.5, segs=7, smooth=False)
    p.box(wood, loc=(0.12, -0.05, 1.2), scale=(0.5, 0.03, 0.16), bevel=0.02)
    p.cone(wood, loc=(0.62, -0.05, 1.2), r1=0.2, r2=0.0, depth=0.22, segs=3, rot=(0, 90, 0), scale=(0.8, 0.15, 1), smooth=False)
    p.finish(parent=root)
    m = Part("marker")
    m.box(mat("marker_off", "#9aa0a6", 0.6), loc=(0, -0.09, 1.2), scale=(0.11, 0.012, 0.11), rot=(0, 45, 0))
    m.finish(parent=root)
    return root


def register(asset):
    asset("rock_a", zoom=1.3)(rock(1))
    asset("rock_b", zoom=1.3)(rock(2, squash=1.1))
    asset("pine_a", zoom=1.2)(pine(1, 3.4, 5))
    asset("pine_b", zoom=1.2)(pine(2, 2.4, 4))
    asset("pine_snow", zoom=1.2)(pine(3, 3.8, 6, snowy=True))
    asset("mountain_a", view=(0.0, -1.0, 0.18), zoom=1.3)(mountain(1, [(0, 0, 1.0, 1.15), (0.55, 0.1, 0.62, 0.7), (-0.6, 0.05, 0.5, 0.65)]))
    asset("mountain_b", view=(0.0, -1.0, 0.18), zoom=1.3)(mountain(2, [(-0.35, 0, 0.9, 0.95), (0.4, 0.05, 0.98, 0.9)], snowline=0.5))
    asset("mountain_c", view=(0.0, -1.0, 0.18), zoom=1.3)(mountain(3, [(0.1, 0, 0.72, 1.2), (-0.65, 0.1, 0.52, 0.6), (0.75, 0, 0.45, 0.55)], snowline=0.46))
    asset("hill", view=(0.0, -1.0, 0.3), zoom=1.3)(hill(4))
    asset("cloud_a", zoom=1.2)(cloud(1))
    asset("cloud_b", zoom=1.2)(cloud(5))
    asset("ground_a", view=(-0.5, -1.0, 0.4), zoom=1.0)(ground(1))
    asset("ground_b", view=(-0.5, -1.0, 0.4), zoom=1.0)(ground(2))
    asset("ground_c", view=(-0.5, -1.0, 0.4), zoom=1.0)(ground(3))
    asset("ledge_2", view=(-0.4, -1.0, 0.4))(ledge(2, 21))
    asset("ledge_3", view=(-0.4, -1.0, 0.4))(ledge(3, 22))
    asset("ledge_4", view=(-0.4, -1.0, 0.4))(ledge(4, 23))
    asset("berry", zoom=1.3)(berry)
    asset("beans", zoom=1.3)(beans)
    asset("summit", view=(-0.3, -1.0, 0.2))(summit)
    asset("signpost", view=(-0.3, -1.0, 0.2), zoom=1.2)(signpost)

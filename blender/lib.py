"""Small procedural-modeling toolkit used by the asset scripts in this folder.

Everything is built with bmesh so it runs headless:
    flatpak run org.blender.Blender -b --python blender/build.py -- hero marmot
"""
import bpy
import bmesh
import math
import os
import random
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS = os.path.join(ROOT, "models")
PREVIEW = os.path.join(ROOT, "blender", "preview")
BLENDS = os.path.join(ROOT, "blender", "blend")


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def hexcol(h):
    h = h.lstrip("#")
    rgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return (lin[0], lin[1], lin[2], 1.0)


def mat(name, color, rough=0.85, metal=0.0, emit=0.0):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    col = hexcol(color)
    bsdf.inputs["Base Color"].default_value = col
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if emit > 0:
        bsdf.inputs["Emission Color"].default_value = col
        bsdf.inputs["Emission Strength"].default_value = emit
    m.diffuse_color = col
    # exported as single-sided, so Godot can cull back faces (and a face wound
    # the wrong way shows up as a hole in the preview instead of going unnoticed)
    m.use_backface_culling = True
    return m


def face_key(f):
    """Sort key that depends only on where a face is, not on when it was made.

    bmesh primitives and operators don't hand their faces back in the same
    order from one call to the next. Anything that walks faces while drawing
    random numbers should walk them sorted by this, or no two builds match."""
    return sorted(tuple(round(c, 6) for c in v.co) for v in f.verts)


def TRS(loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1)):
    """rot is XYZ euler in degrees."""
    if isinstance(scale, (int, float)):
        scale = (scale, scale, scale)
    r = (Matrix.Rotation(math.radians(rot[2]), 4, "Z")
         @ Matrix.Rotation(math.radians(rot[1]), 4, "Y")
         @ Matrix.Rotation(math.radians(rot[0]), 4, "X"))
    s = Matrix.Diagonal((scale[0], scale[1], scale[2], 1.0))
    return Matrix.Translation(loc) @ r @ s


def align(point, normal, up=(0, 0, 1)):
    """Matrix placing local +Z along `normal` at `point`, local +Y near `up`."""
    z = Vector(normal).normalized()
    u = Vector(up)
    x = u.cross(z)
    if x.length < 1e-5:
        x = Vector((1, 0, 0))
    x.normalize()
    y = z.cross(x)
    m = Matrix((x, y, z)).transposed().to_4x4()
    m.translation = Vector(point)
    return m


class Part:
    """Accumulates primitives into one mesh with several material slots."""

    def __init__(self, name):
        self.name = name
        self.bm = bmesh.new()
        self.mats = []

    # -- internals ---------------------------------------------------------
    def _mi(self, material):
        if material not in self.mats:
            self.mats.append(material)
        return self.mats.index(material)

    def merge(self, tmp, matrix, material, smooth=True):
        mi = self._mi(material)
        vmap = {}
        for v in tmp.verts:
            vmap[v] = self.bm.verts.new(matrix @ v.co)
        flip = matrix.determinant() < 0
        for f in sorted(tmp.faces, key=face_key):
            vs = [vmap[v] for v in f.verts]
            if flip:
                vs.reverse()
            try:
                nf = self.bm.faces.new(vs)
            except ValueError:
                continue
            nf.material_index = mi
            nf.smooth = smooth
        tmp.free()

    # -- primitives --------------------------------------------------------
    def sphere(self, material, loc=(0, 0, 0), scale=(1, 1, 1), rot=(0, 0, 0),
               segs=16, rings=10, power=1.0, cut=None, matrix=None, smooth=True):
        """Ellipsoid. power<1 makes it boxier. cut=(co, no) removes the side
        the normal points to (in unit-sphere space)."""
        tmp = bmesh.new()
        bmesh.ops.create_uvsphere(tmp, u_segments=segs, v_segments=rings, radius=1.0)
        if power != 1.0:
            for v in tmp.verts:
                v.co = Vector([math.copysign(abs(c) ** power, c) for c in v.co])
        if cut:
            geom = list(tmp.verts) + list(tmp.edges) + list(tmp.faces)
            bmesh.ops.bisect_plane(tmp, geom=geom, plane_co=Vector(cut[0]),
                                   plane_no=Vector(cut[1]), clear_outer=True)
            edges = [e for e in tmp.edges if e.is_boundary]
            if edges:
                bmesh.ops.holes_fill(tmp, edges=edges)
        m = TRS(loc, rot, scale)
        if matrix is not None:
            m = matrix @ m
        self.merge(tmp, m, material, smooth)

    def box(self, material, loc=(0, 0, 0), scale=(1, 1, 1), rot=(0, 0, 0),
            matrix=None, smooth=False, bevel=0.0):
        tmp = bmesh.new()
        bmesh.ops.create_cube(tmp, size=2.0)
        m = TRS(loc, rot, scale)
        if bevel > 0:
            # bevel in final space: bake the scale first
            s = Matrix.Diagonal((*Vector(scale if not isinstance(scale, (int, float)) else (scale,) * 3), 1.0))
            bmesh.ops.transform(tmp, matrix=s, verts=tmp.verts)
            bmesh.ops.bevel(tmp, geom=list(tmp.edges), offset=bevel, segments=2,
                            profile=0.5, affect="EDGES")
            m = TRS(loc, rot, (1, 1, 1))
        if matrix is not None:
            m = matrix @ m
        self.merge(tmp, m, material, smooth)

    def cone(self, material, loc=(0, 0, 0), r1=1.0, r2=0.0, depth=1.0, rot=(0, 0, 0),
             segs=12, matrix=None, smooth=True, scale=(1, 1, 1), caps=True):
        """Cone / cylinder along local Z, base at z=0, top at z=depth."""
        tmp = bmesh.new()
        bmesh.ops.create_cone(tmp, cap_ends=caps, cap_tris=False, segments=segs,
                              radius1=r1, radius2=r2, depth=depth)
        bmesh.ops.translate(tmp, verts=tmp.verts, vec=(0, 0, depth / 2))
        m = TRS(loc, rot, scale)
        if matrix is not None:
            m = matrix @ m
        self.merge(tmp, m, material, smooth)

    def torus(self, material, loc=(0, 0, 0), R=1.0, r=0.25, rot=(0, 0, 0),
              segs=24, tube=8, matrix=None, arc=360.0, scale=(1, 1, 1), taper=1.0):
        """Torus in local XY plane. arc<360 gives an open horn-like sweep,
        taper scales the tube radius towards the end of the arc."""
        tmp = bmesh.new()
        closed = arc >= 359.9
        n = segs if closed else segs + 1
        rings = []
        for i in range(n):
            t = i / segs
            a = math.radians(arc) * t
            rr = r * (1.0 + (taper - 1.0) * t)
            ring = []
            for j in range(tube):
                b = 2 * math.pi * j / tube
                x = (R + rr * math.cos(b)) * math.cos(a)
                y = (R + rr * math.cos(b)) * math.sin(a)
                ring.append(tmp.verts.new((x, y, rr * math.sin(b))))
            rings.append(ring)
        for i in range(segs):
            a, b = rings[i], rings[(i + 1) % n]
            for j in range(tube):
                tmp.faces.new((a[j], b[j], b[(j + 1) % tube], a[(j + 1) % tube]))
        if not closed:
            # end caps, wound to face out of the tube
            tmp.faces.new(rings[0])
            tmp.faces.new(list(reversed(rings[-1])))
        m = TRS(loc, rot, scale)
        if matrix is not None:
            m = matrix @ m
        self.merge(tmp, m, material, True)

    # -- surface helpers ---------------------------------------------------
    def bvh(self):
        self.bm.verts.ensure_lookup_table()
        self.bm.faces.ensure_lookup_table()
        self.bm.normal_update()
        return BVHTree.FromBMesh(self.bm)

    def sample_surface(self, count, rng):
        """Area-weighted random (point, normal) samples."""
        self.bm.normal_update()
        tris = self.bm.calc_loop_triangles()
        areas, total = [], 0.0
        for t in tris:
            a, b, c = (l.vert.co for l in t)
            total += (b - a).cross(c - a).length * 0.5
            areas.append(total)
        out = []
        import bisect
        for _ in range(count):
            i = min(bisect.bisect_left(areas, rng.random() * total), len(tris) - 1)
            a, b, c = (l.vert.co for l in tris[i])
            u, v = rng.random(), rng.random()
            if u + v > 1:
                u, v = 1 - u, 1 - v
            out.append((a + (b - a) * u + (c - a) * v, tris[i][0].face.normal.copy()))
        return out

    def tufts(self, samples, materials, rng, length=(0.1, 0.2), radius=(0.03, 0.045),
              droop=0.6, scale_fn=None, smooth=False):
        """Shaggy fur: little curved spikes drooping with gravity."""
        down = Vector((0, 0, -1))
        for p, n in samples:
            k = 1.0 if scale_fn is None else scale_fn(p, n)
            if k <= 0:
                continue
            L = rng.uniform(*length) * k
            r = rng.uniform(*radius) * (0.6 + 0.4 * k)
            mi = self._mi(rng.choice(materials))
            jit = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1))) * 0.35
            d1 = (n + down * droop * 0.5 + jit * 0.5).normalized()
            d2 = (n * 0.45 + down * droop + jit).normalized()
            base_m = align(p - n * 0.012, n)
            mid_c = p + d1 * L * 0.5
            mid_m = align(mid_c, d1)
            tip = self.bm.verts.new(mid_c + d2 * L * 0.6)
            ang0 = rng.uniform(0, 6.28)
            b, m = [], []
            for j in range(3):
                a = ang0 + j * 2.0944
                b.append(self.bm.verts.new(base_m @ Vector((math.cos(a) * r, math.sin(a) * r, 0))))
                m.append(self.bm.verts.new(mid_m @ Vector((math.cos(a) * r * 0.62, math.sin(a) * r * 0.62, 0))))
            for j in range(3):
                k2 = (j + 1) % 3
                f = self.bm.faces.new((b[j], b[k2], m[k2], m[j]))
                f.material_index = mi
                f.smooth = smooth
                f = self.bm.faces.new((m[j], m[k2], tip))
                f.material_index = mi
                f.smooth = smooth

    def transform(self, matrix):
        bmesh.ops.transform(self.bm, matrix=matrix, verts=self.bm.verts)

    # -- output ------------------------------------------------------------
    def finish(self, origin=(0, 0, 0), parent=None):
        bmesh.ops.translate(self.bm, verts=self.bm.verts, vec=-Vector(origin))
        me = bpy.data.meshes.new(self.name)
        self.bm.normal_update()
        self.bm.to_mesh(me)
        self.bm.free()
        for m in self.mats:
            me.materials.append(m)
        ob = bpy.data.objects.new(self.name, me)
        bpy.context.scene.collection.objects.link(ob)
        ob.location = Vector(origin)
        if parent is not None:
            ob.parent = parent
            ob.location = Vector(origin) - parent.location
        return ob


def blob(name, build, voxel=0.035, smooth_iter=8, faces=1400):
    """Union the primitives added by build(part) into one smooth blobby mesh
    (voxel remesh + smooth + decimate) and return it as a new Part."""
    src = Part(name + "_src")
    build(src)
    m = mat("_tmp", "#ffffff")
    src.mats = [m]
    ob = src.finish()
    r = ob.modifiers.new("remesh", "REMESH")
    r.mode = "VOXEL"
    r.voxel_size = voxel
    s = ob.modifiers.new("smooth", "SMOOTH")
    s.factor = 0.8
    s.iterations = smooth_iter
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev)
    if faces and len(me.polygons) > faces:
        tmp_ob = bpy.data.objects.new("_dec", me)
        bpy.context.scene.collection.objects.link(tmp_ob)
        d = tmp_ob.modifiers.new("dec", "DECIMATE")
        d.ratio = faces / len(me.polygons)
        dg = bpy.context.evaluated_depsgraph_get()
        me2 = bpy.data.meshes.new_from_object(tmp_ob.evaluated_get(dg))
        bpy.data.objects.remove(tmp_ob)
        me = me2
    bpy.data.objects.remove(ob)
    out = Part(name)
    out.bm.from_mesh(me)
    for f in out.bm.faces:
        f.smooth = True
    return out


def empty(name):
    e = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(e)
    return e


def hierarchy(root):
    out = [root]
    for c in root.children:
        out.extend(hierarchy(c))
    return out


def export(root, name):
    os.makedirs(MODELS, exist_ok=True)
    for o in bpy.context.scene.objects:
        o.select_set(False)
    for o in hierarchy(root):
        o.select_set(True)
    bpy.context.view_layer.objects.active = root
    path = os.path.join(MODELS, name + ".glb")
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True,
                              export_apply=True, export_yup=True, export_animations=False)
    tris = sum(len(o.data.loop_triangles) if o.type == "MESH" and not o.data.calc_loop_triangles() else 0
               for o in hierarchy(root))
    print("EXPORTED %s (%d tris)" % (path, tris))


def preview(root, name, view=(-0.55, -1.0, 0.35), zoom=1.0, sky="#8fc0e8", res=(720, 720)):
    """Render a quick look-dev PNG and save the .blend next to it."""
    os.makedirs(PREVIEW, exist_ok=True)
    os.makedirs(BLENDS, exist_ok=True)
    sc = bpy.context.scene
    bpy.context.view_layer.update()
    lo = Vector((1e9, 1e9, 1e9))
    hi = -lo
    for o in hierarchy(root):
        if o.type != "MESH":
            continue
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            lo = Vector(map(min, lo, w))
            hi = Vector(map(max, hi, w))
    center = (lo + hi) / 2
    size = max((hi - lo).length, 0.1)
    cam_d = bpy.data.cameras.new("PreviewCam")
    cam_d.lens = 60
    cam = bpy.data.objects.new("PreviewCam", cam_d)
    sc.collection.objects.link(cam)
    cam.location = center + Vector(view).normalized() * size * 2.1 / zoom
    cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.camera = cam
    for nm, rot, energy in (("Key", (50, 0, -35), 4.0), ("Rim", (60, 0, 150), 2.5)):
        ld = bpy.data.lights.new(nm, "SUN")
        ld.energy = energy
        lo_ = bpy.data.objects.new(nm, ld)
        lo_.rotation_euler = [math.radians(a) for a in rot]
        sc.collection.objects.link(lo_)
    w = bpy.data.worlds.new("World")
    try:
        w.use_nodes = True
    except Exception:
        pass
    bg = next((n for n in w.node_tree.nodes if n.type == "BACKGROUND"), None)
    if bg:
        bg.inputs[0].default_value = hexcol(sky)
        bg.inputs[1].default_value = 1.0
    sc.world = w
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.filepath = os.path.join(PREVIEW, name + ".png")
    sc.view_settings.view_transform = "Standard"
    bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(BLENDS, name + ".blend"))

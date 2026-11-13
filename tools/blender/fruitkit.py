"""Juice Dojo fruit kit: toon-shaded 3D fruit built procedurally in Blender 4.2.

Run inside Blender (the live MCP session or headless):
    exec(open(r"<repo>/tools/blender/fruitkit.py").read()); build("H1")
    blender -b --factory-startup --python tools/blender/fruitkit.py -- H1,L2 build,render

Look: cartoon but 3D - every surface is flat cel bands (Shader to RGB -> constant ramp) times the
fruit's own colour pattern, a hard specular blob, a light rim, and an inverted-hull black outline
(solidify, flipped normals). Each fruit is a closed mesh; its HALVES are the same mesh bisected in 3D
with the cut face capped in an INSIDE material (flesh, seeds, rind), so the slice is real geometry.

Renders (render step): art/blender/frames/<ID>/<clip>_<NN>.png, transparent, square.
  whole : a tumble of N frames about a tilted axis (the game picks the frame by its own spin)
  half  : the left half, cut face toward camera, tumbling the same way
"""
import math
import os
import sys

import bpy
import bmesh
from mathutils import Vector, Matrix

try:
    ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
except NameError:  # exec()'d in the live session
    ROOT = os.path.join(os.path.expanduser("~"), "Documents", "juicedojo")
FRAMES = os.path.join(ROOT, "art", "blender", "frames")
RES = 256
N_FRAMES = 16
SCENE = "Dojo"


# ---------------------------------------------------------------- scene
def scene():
    if bpy.context.window:
        sc = bpy.data.scenes.get(SCENE) or bpy.data.scenes.new(SCENE)
        bpy.context.window.scene = sc
    else:                                   # headless: build into the one scene the context has
        sc = bpy.context.scene
        sc.name = SCENE
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            sc.render.engine = eng
            break
        except TypeError:
            pass
    sc.render.resolution_x = sc.render.resolution_y = RES
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = True
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.render.filter_size = 1.2
    try:
        sc.eevee.taa_render_samples = 16
    except AttributeError:
        pass
    if not sc.world:
        sc.world = bpy.data.worlds.new("DojoWorld")
    sc.world.use_nodes = True
    bg = next(n for n in sc.world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.35, 0.33, 0.32, 1)
    bg.inputs[1].default_value = 0.6
    cam = bpy.data.objects.get("DojoCam")
    if not cam:
        cam = bpy.data.objects.new("DojoCam", bpy.data.cameras.new("DojoCam"))
        sc.collection.objects.link(cam)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 2.7
    cam.location = (0, -10, 0)
    cam.rotation_euler = (math.radians(90), 0, 0)
    sc.camera = cam
    key = bpy.data.objects.get("DojoKey")
    if not key:
        key = bpy.data.objects.new("DojoKey", bpy.data.lights.new("DojoKey", "SUN"))
        sc.collection.objects.link(key)
    key.data.energy = 4.0
    key.data.angle = math.radians(8)
    key.rotation_euler = (math.radians(50), math.radians(-35), math.radians(-30))   # from upper left, front
    return sc


def clear_fruit():
    for ob in list(bpy.data.objects):
        if ob.get("fruitkit"):
            bpy.data.objects.remove(ob, do_unlink=True)


# ---------------------------------------------------------------- materials
def _n(nt, kind, x, y, **inputs):
    n = nt.nodes.new(kind)
    n.location = (x, y)
    for k, v in inputs.items():
        n.inputs[k].default_value = v
    return n


def outline_mat():
    m = bpy.data.materials.get("fk_outline")
    if m:
        return m
    m = bpy.data.materials.new("fk_outline")
    m.use_nodes = True
    m.use_backface_culling = True
    nt = m.node_tree
    nt.nodes.clear()
    out = _n(nt, "ShaderNodeOutputMaterial", 300, 0)
    em = _n(nt, "ShaderNodeEmission", 0, 0)
    em.inputs["Color"].default_value = (0.03, 0.02, 0.025, 1)
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    return m


def toon(name, colour_fn, shade=(0.42, 0.78, 1.06), spec=0.6, rim=0.35, glow=0.0):
    """colour_fn(nt) -> an output socket giving the surface colour. The light makes 3 flat bands."""
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    L = nt.links.new
    out = _n(nt, "ShaderNodeOutputMaterial", 1400, 0)
    col = colour_fn(nt)
    dif = _n(nt, "ShaderNodeBsdfDiffuse", -200, 300)
    s2r = _n(nt, "ShaderNodeShaderToRGB", 0, 300)
    L(dif.outputs[0], s2r.inputs[0])
    bw = _n(nt, "ShaderNodeRGBToBW", 180, 300)
    L(s2r.outputs[0], bw.inputs[0])
    ramp = _n(nt, "ShaderNodeValToRGB", 340, 300)
    cr = ramp.color_ramp
    cr.interpolation = "EASE"          # flat bands with a short soft edge between them
    stops = [(0.0, shade[0]), (0.16, shade[0]), (0.24, shade[1]), (0.52, shade[1]), (0.58, shade[2])]
    for i, (p, v) in enumerate(stops):
        e = cr.elements[i] if i < 2 else cr.elements.new(p)
        e.position = p
        e.color = (v,) * 3 + (1,)
    L(bw.outputs[0], ramp.inputs[0])
    mul = _n(nt, "ShaderNodeMix", 640, 200)
    mul.data_type = "RGBA"
    mul.blend_type = "MULTIPLY"
    mul.inputs[0].default_value = 1.0
    L(col, mul.inputs[6])
    L(ramp.outputs[0], mul.inputs[7])
    last = mul.outputs[2]
    # hard specular blob
    if spec > 0:
        gl = _n(nt, "ShaderNodeBsdfGlossy", -200, -100)
        gl.inputs["Roughness"].default_value = 0.25
        s2 = _n(nt, "ShaderNodeShaderToRGB", 0, -100)
        L(gl.outputs[0], s2.inputs[0])
        bw2 = _n(nt, "ShaderNodeRGBToBW", 180, -100)
        L(s2.outputs[0], bw2.inputs[0])
        r2 = _n(nt, "ShaderNodeValToRGB", 340, -100)
        r2.color_ramp.interpolation = "CONSTANT"
        r2.color_ramp.elements[0].color = (0, 0, 0, 1)
        r2.color_ramp.elements[1].position = 0.55
        r2.color_ramp.elements[1].color = (spec,) * 3 + (1,)
        L(bw2.outputs[0], r2.inputs[0])
        add = _n(nt, "ShaderNodeMix", 900, 100)
        add.data_type = "RGBA"
        add.blend_type = "SCREEN"
        add.inputs[0].default_value = 1.0
        L(last, add.inputs[6])
        L(r2.outputs[0], add.inputs[7])
        last = add.outputs[2]
    # rim light (facing ratio), a thin bright band on the silhouette's lit side
    if rim > 0:
        lw = _n(nt, "ShaderNodeLayerWeight", 340, -350)
        lw.inputs["Blend"].default_value = 0.35
        r3 = _n(nt, "ShaderNodeValToRGB", 520, -350)
        r3.color_ramp.interpolation = "CONSTANT"
        r3.color_ramp.elements[0].color = (0, 0, 0, 1)
        r3.color_ramp.elements[1].position = 0.6
        r3.color_ramp.elements[1].color = (rim,) * 3 + (1,)
        L(lw.outputs["Facing"], r3.inputs[0])
        add2 = _n(nt, "ShaderNodeMix", 1100, 0)
        add2.data_type = "RGBA"
        add2.blend_type = "ADD"
        add2.inputs[0].default_value = 1.0
        L(last, add2.inputs[6])
        L(r3.outputs[0], add2.inputs[7])
        last = add2.outputs[2]
    em = _n(nt, "ShaderNodeEmission", 1250, 0)
    em.inputs["Strength"].default_value = 1.0 + glow
    L(last, em.inputs["Color"])
    L(em.outputs[0], out.inputs["Surface"])
    return m


def flat(rgb):
    def f(nt):
        n = _n(nt, "ShaderNodeRGB", 300, 0)
        n.outputs[0].default_value = tuple(rgb) + (1,)
        return n.outputs[0]
    return f


def coord(nt, x=-900, y=0):
    tc = _n(nt, "ShaderNodeTexCoord", x, y)
    return tc.outputs["Object"]


def ramp_of(nt, fac, stops, x=0, y=0, interp="CONSTANT"):
    r = _n(nt, "ShaderNodeValToRGB", x, y)
    cr = r.color_ramp
    cr.interpolation = interp
    for i, (p, c) in enumerate(stops):
        e = cr.elements[i] if i < 2 else cr.elements.new(p)
        e.position = p
        e.color = tuple(c) + (1,)
    nt.links.new(fac, r.inputs[0])
    return r.outputs[0]


def radius_xz(nt, x=-700, y=0):
    """Distance from the fruit's axis in the cut plane (object X=0 plane -> use Y,Z)."""
    co = coord(nt, x - 300, y)
    sep = _n(nt, "ShaderNodeSeparateXYZ", x, y)
    nt.links.new(co, sep.inputs[0])
    comb = _n(nt, "ShaderNodeCombineXYZ", x + 150, y)
    nt.links.new(sep.outputs["Y"], comb.inputs["Y"])
    nt.links.new(sep.outputs["Z"], comb.inputs["Z"])
    ln = _n(nt, "ShaderNodeVectorMath", x + 300, y)
    ln.operation = "LENGTH"
    nt.links.new(comb.outputs[0], ln.inputs[0])
    return ln.outputs["Value"], sep


def seeds(nt, base_col, seed_col, scale=6.0, size=0.12, inner=0.0, outer=1.0, x=0, y=-400):
    """Dark seeds: voronoi cell distance < size, within a band of radius."""
    co = coord(nt, x - 600, y)
    vor = _n(nt, "ShaderNodeTexVoronoi", x - 400, y)
    vor.inputs["Scale"].default_value = scale
    nt.links.new(co, vor.inputs["Vector"])
    lt = _n(nt, "ShaderNodeMath", x - 200, y)
    lt.operation = "LESS_THAN"
    lt.inputs[1].default_value = size
    nt.links.new(vor.outputs["Distance"], lt.inputs[0])
    r, _ = radius_xz(nt, x - 900, y - 250)
    band = ramp_of(nt, r, [(0.0, (0, 0, 0)), (inner, (1, 1, 1)), (outer, (0, 0, 0))], x - 400, y - 250)
    mul = _n(nt, "ShaderNodeMath", x, y)
    mul.operation = "MULTIPLY"
    nt.links.new(lt.outputs[0], mul.inputs[0])
    bwb = _n(nt, "ShaderNodeRGBToBW", x - 150, y - 250)
    nt.links.new(band, bwb.inputs[0])
    nt.links.new(bwb.outputs[0], mul.inputs[1])
    mix = _n(nt, "ShaderNodeMix", x + 200, y)
    mix.data_type = "RGBA"
    nt.links.new(mul.outputs[0], mix.inputs[0])
    nt.links.new(base_col, mix.inputs[6])
    sc = _n(nt, "ShaderNodeRGB", x, y - 150)
    sc.outputs[0].default_value = tuple(seed_col) + (1,)
    nt.links.new(sc.outputs[0], mix.inputs[7])
    return mix.outputs[2]


# ---------------------------------------------------------------- meshes
def tag(ob):
    ob["fruitkit"] = True
    return ob


def sphere(name, scale=(1, 1, 1), segs=48, rings=32):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=rings, radius=1.0)
    bmesh.ops.scale(bm, vec=Vector(scale), verts=bm.verts)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    for p in me.polygons:
        p.use_smooth = True
    return tag(ob)


def deform(ob, fn):
    for v in ob.data.vertices:
        v.co = fn(Vector(v.co))


def add_mat(ob, m):
    ob.data.materials.append(m)
    return len(ob.data.materials) - 1


def outline(ob, width=0.05):
    """Inverted hull: a solidified shell, normals flipped, outline material on the back faces."""
    idx = add_mat(ob, outline_mat())
    mod = ob.modifiers.new("outline", "SOLIDIFY")
    mod.thickness = width
    mod.offset = 1.0
    mod.use_flip_normals = True
    mod.use_rim = False
    mod.material_offset = idx
    mod.material_offset_rim = idx
    return mod


def join(parts, name):
    bpy.ops.object.select_all(action="DESELECT")
    for p in parts:
        p.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = name
    return ob


# ---------------------------------------------------------------- fruit
def mat_watermelon():
    def skin(nt):
        co = coord(nt)
        sep = _n(nt, "ShaderNodeSeparateXYZ", -700, 0)
        nt.links.new(co, sep.inputs[0])
        ang = _n(nt, "ShaderNodeMath", -500, 0)          # angle around the long (X) axis
        ang.operation = "ARCTAN2"
        nt.links.new(sep.outputs["Z"], ang.inputs[0])
        nt.links.new(sep.outputs["Y"], ang.inputs[1])
        noi = _n(nt, "ShaderNodeTexNoise", -700, -250)
        noi.inputs["Scale"].default_value = 3.0
        noi.inputs["Detail"].default_value = 3.0
        nt.links.new(co, noi.inputs["Vector"])
        wob = _n(nt, "ShaderNodeMath", -350, -100)
        wob.operation = "MULTIPLY_ADD"
        wob.inputs[1].default_value = 0.9
        nt.links.new(noi.outputs["Fac"], wob.inputs[0])
        nt.links.new(ang.outputs[0], wob.inputs[2])
        st = _n(nt, "ShaderNodeMath", -200, 0)
        st.operation = "SINE"
        mul = _n(nt, "ShaderNodeMath", -350, 100)
        mul.operation = "MULTIPLY"
        mul.inputs[1].default_value = 7.0
        nt.links.new(wob.outputs[0], mul.inputs[0])
        nt.links.new(mul.outputs[0], st.inputs[0])
        return ramp_of(nt, st.outputs[0], [(0.0, (0.05, 0.22, 0.05)), (0.45, (0.30, 0.62, 0.12))], -50, 0)
    return toon("fk_H1_skin", skin)


def mat_watermelon_in():
    def inside(nt):
        r, _ = radius_xz(nt, -900, 0)
        base = ramp_of(nt, r, [(0.0, (0.95, 0.12, 0.16)), (0.80, (1.0, 0.62, 0.62)), (0.86, (0.92, 0.95, 0.78)),
                               (0.93, (0.22, 0.55, 0.12))], -300, 0)
        return seeds(nt, base, (0.06, 0.03, 0.03), scale=7.0, size=0.17, inner=0.3, outer=0.72)
    return toon("fk_H1_in", inside, shade=(0.75, 0.92, 1.0), spec=0.35, rim=0.0)


def build_H1():
    ob = sphere("H1", (1.18, 0.98, 0.98))
    add_mat(ob, mat_watermelon())
    add_mat(ob, mat_watermelon_in())
    return ob


FRUIT = {"H1": build_H1}
NO_HALF = set()
_more = os.path.join(os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.path.join(ROOT, "tools", "blender"), "fruits_more.py")
exec(open(_more, encoding="utf-8").read(), globals())


# ---------------------------------------------------------------- halves
def make_half(ob, side=1):
    """Bisect `ob` (modifiers excluded) through the YZ plane and cap the cut with the INSIDE material."""
    me = ob.data.copy()
    h = bpy.data.objects.new(ob.name + ("_halfR" if side > 0 else "_halfL"), me)
    bpy.context.scene.collection.objects.link(h)
    tag(h)
    bm = bmesh.new()
    bm.from_mesh(me)
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    res = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, 0, 0), plane_no=(side, 0, 0),
                                 clear_inner=False, clear_outer=True)
    cut_edges = [e for e in res["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
    fill = bmesh.ops.holes_fill(bm, edges=cut_edges, sides=0) if cut_edges else {"faces": []}
    for f in fill.get("faces", []):
        f.material_index = 1          # slot 1 is always the fruit's INSIDE material
        f.smooth = False
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(me)
    bm.free()
    outline(h)
    return h


# ---------------------------------------------------------------- entry points
def build(ID):
    scene()
    clear_fruit()
    ob = FRUIT[ID]()
    normalize(ob, 1.2)
    half = None
    if ID not in NO_HALF:
        half = make_half(ob, -1)
        half.hide_render = half.hide_viewport = True
    outline(ob)
    return ob, half


def tumble(ob, i, n, tilt=25):
    """Frame i of n: a full turn about an axis tilted toward the camera."""
    a = 2 * math.pi * i / n
    ob.rotation_mode = "QUATERNION"
    axis = Vector((math.sin(math.radians(tilt)), 0, math.cos(math.radians(tilt))))
    ob.rotation_quaternion = Matrix.Rotation(a, 4, axis).to_quaternion()


def render(ID, clips=("whole", "half"), n=N_FRAMES):
    sc = scene()
    ob = bpy.data.objects[ID]
    half = bpy.data.objects.get(ID + "_halfL")
    out = os.path.join(FRAMES, ID)
    os.makedirs(out, exist_ok=True)
    for clip in clips:
        tgt = ob if clip == "whole" else half
        if tgt is None:
            continue
        for o in (ob, half):
            if o:
                o.hide_render = o is not tgt
        for i in range(n):
            if clip == "whole":
                tumble(tgt, i, n)
            else:
                # cut face (-X side... the kept half faces +X after the cut on side -1) toward camera
                base = Matrix.Rotation(math.radians(90), 4, "Z")      # cut normal +X -> -Y (camera)
                spin = Matrix.Rotation(2 * math.pi * i / n, 4, "Y")    # roll in the picture plane
                wob = Matrix.Rotation(math.radians(28) * math.sin(2 * math.pi * i / n), 4, "Z")
                tgt.rotation_mode = "QUATERNION"
                tgt.rotation_quaternion = (spin @ wob @ base).to_quaternion()
            sc.render.filepath = os.path.join(out, f"{clip}_{i:02d}.png")
            bpy.ops.render.render(write_still=True, scene=sc.name)
    print("rendered", ID, clips)


def preview(ID):
    """Whole fruit left, its half (cut face to camera) right - for looking at in the viewport."""
    ob, half = build(ID)
    if half is None:
        return ob, None
    half.hide_viewport = half.hide_render = False
    ob.location = (-1.35, 0, 0)
    tumble(ob, 1, 16)
    half.location = (1.35, 0, 0)
    half.rotation_mode = "QUATERNION"
    half.rotation_quaternion = (Matrix.Rotation(math.radians(20), 4, "Y") @ Matrix.Rotation(math.radians(90), 4, "Z")).to_quaternion()
    bpy.context.scene.camera.data.ortho_scale = 5.6
    bpy.context.scene.render.resolution_x = 2 * RES
    return ob, half


ALL = ["H1", "H2", "H3", "H4", "L1", "L2", "L3", "L4", "SC", "BOMB", "PW2", "PW3", "PW5", "FRZ", "JM"]


def gallery(ids=ALL, per_row=5):
    """Every fruit with its half beside it, for one look through the camera."""
    import traceback
    scene()
    clear_fruit()
    rows = (len(ids) + per_row - 1) // per_row
    for k, I in enumerate(ids):
        try:
            ob = FRUIT[I]()
            normalize(ob, 1.2)
            half = make_half(ob, -1) if I not in NO_HALF else None
            outline(ob)
            col, row = k % per_row, k // per_row
            x, z = col * 5.4 - (per_row - 1) * 2.7 - 1.3, (rows - 1) * 1.35 - row * 2.7
            ob.location = (x, 0, z)
            tumble(ob, 1, 16)
            if half:
                half.location = (x + 2.6, 0, z)
                half.rotation_mode = "QUATERNION"
                half.rotation_quaternion = (Matrix.Rotation(math.radians(20), 4, "Y") @ Matrix.Rotation(math.radians(90), 4, "Z")).to_quaternion()
        except Exception:
            print(I, "FAIL", traceback.format_exc()[-600:])
    sc = bpy.context.scene
    sc.camera.data.ortho_scale = 5.5 * per_row
    sc.render.resolution_x = 320 * per_row
    sc.render.resolution_y = int(320 * rows * 2.7 / 5.5)


if __name__ == "__main__" and "--" in sys.argv:  # headless
    args = sys.argv[sys.argv.index("--") + 1:]
    ids = ALL if not args or args[0] == "all" else args[0].split(",")
    steps = args[1].split(",") if len(args) > 1 else ["build", "render"]
    for I in ids:
        if "build" in steps:
            build(I)
        if "render" in steps:
            render(I)

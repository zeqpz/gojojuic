"""Juice Dojo fruit kit: glossy pre-rendered 3D fruit built procedurally in Blender 5.x (Cycles).

Run inside Blender (the live MCP session or headless):
    exec(open(r"<repo>/tools/blender/fruitkit.py").read()); build("H1")
    blender -b --factory-startup --python tools/blender/fruitkit.py -- H1,L2 build,render
    blender -b --factory-startup --python tools/blender/fruitkit.py -- all gallery        # art/blender/gallery.png
    blender -b --factory-startup --python tools/blender/fruitkit.py -- BOMB build,track   # the fuse spark track

Look (2026-11-18, "old style casino" pass): pre-rendered arcade CGI in the spirit of 2010s fish-table and fruit-machine
symbols. Every surface is a Principled BSDF: the fruit's own colour pattern, hyper-saturated; a lacquer clear coat
over the skin (smooth even where the skin has pores, dimples or fibres in its bump), so each fruit shows a big soft
key highlight (the reflection of the key softbox) plus a hard hot spot (a tiny specular-only light); subsurface on the
thin-skinned fruit for an inner glow; real metal for the golden star fruit, the Gold Melon and the bomb's brass. No
outlines, no cel bands. Lights: a warm-white key softbox from the upper left front, a cool fill from the right, a warm
bounce from below, and two coloured rims from behind (amber right, cyan left) that cut every silhouette out of the
dark wood; a dim studio-gradient world for the metal to reflect. AgX + Punchy look, then a saturation lift.

Each fruit is a closed mesh; its HALVES are the same mesh bisected in 3D with the cut face capped in an INSIDE
material (flesh, seeds, rind), glossy and wet, so the slice is real geometry.

Renders (render step): art/blender/frames/<ID>/<clip>_<NN>.png, transparent, square, RES px.
  whole : a 64-frame tumble (one full turn) about a tilted axis; the game crossfades between frames
  wob   : the right half, cut face toward camera, rocking +-28 deg (24 frames; the roll is done in 2D in the game)
  openR : the right half opening on a slice: from its place in the whole fruit (cut face edge-on) to cut face
          toward camera (8 frames, eased); frame 0 of openR + openL together is exactly the whole fruit
  openL : the left half, the same, the other way
"""
import math
import os
import sys

import bpy
import bmesh
from mathutils import Vector, Matrix, Quaternion

try:
    ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
except NameError:  # exec()'d in the live session
    ROOT = os.path.join(os.path.expanduser("~"), "Documents", "gojojuic")
FRAMES = os.path.join(ROOT, "art", "blender", "frames")
RES = 256
N_WHOLE = 64
N_WOB = 24
N_OPEN = 8
SAMPLES = 48
MBLUR = float(os.environ.get("FK_MBLUR", 0.0))   # tumble motion-blur shutter in frames (0 = off); see render()
SCENE = "Dojo"
VIEW, LOOK, EXPOSURE = "Standard", "None", -0.2   # Standard keeps the jewel colours (AgX/Filmic go pastel)


# ---------------------------------------------------------------- scene
def _try(obj, attr, val):
    try:
        setattr(obj, attr, val)
        return True
    except (AttributeError, TypeError, ValueError):
        return False


def _gpu():
    try:
        p = bpy.context.preferences.addons["cycles"].preferences
    except KeyError:
        return False
    for kind in ("OPTIX", "CUDA", "HIP", "ONEAPI"):
        try:
            p.compute_device_type = kind
            p.refresh_devices()
        except Exception:
            continue
        gpus = [d for d in p.devices if d.type == kind]
        if gpus:
            for d in p.devices:
                d.use = d.type == kind
            return True
    return False


def light(name, kind, loc, energy, colour, size=1.0, size_y=None, target=(0, 0, 0), diffuse=True, specular=True, shape="RECTANGLE"):
    ob = bpy.data.objects.get(name)
    if not ob:
        ob = bpy.data.objects.new(name, bpy.data.lights.new(name, kind))
        bpy.context.scene.collection.objects.link(ob)
    L = ob.data
    L.energy = energy
    L.color = colour
    if kind == "AREA":
        L.shape = shape
        L.size = size
        L.size_y = size_y or size
    else:
        L.shadow_soft_size = size
    ob.location = loc
    d = Vector(target) - Vector(loc)
    ob.rotation_mode = "QUATERNION"
    ob.rotation_quaternion = d.to_track_quat("-Z", "Y")
    _try(ob, "visible_camera", False)
    _try(ob, "visible_diffuse", diffuse)
    _try(ob, "visible_glossy", specular)
    return ob


def scene():
    if bpy.context.window:
        sc = bpy.data.scenes.get(SCENE) or bpy.data.scenes.new(SCENE)
        bpy.context.window.scene = sc
    else:                                   # headless: build into the one scene the context has
        sc = bpy.context.scene
        sc.name = SCENE
    sc.render.engine = "CYCLES"
    cy = sc.cycles
    cy.device = "GPU" if _gpu() else "CPU"
    cy.samples = SAMPLES
    _try(cy, "use_adaptive_sampling", True)
    _try(cy, "adaptive_threshold", 0.015)
    _try(cy, "use_denoising", True)
    _try(cy, "denoiser", "OPTIX" if cy.device == "GPU" else "OPENIMAGEDENOISE")
    _try(cy, "denoising_input_passes", "RGB_ALBEDO_NORMAL")
    for attr, val in (("max_bounces", 8), ("diffuse_bounces", 2), ("glossy_bounces", 3), ("transmission_bounces", 8),
                      ("transparent_max_bounces", 8), ("caustics_reflective", False), ("caustics_refractive", False),
                      ("blur_glossy", 1.0), ("filter_width", 1.5)):
        _try(cy, attr, val)
    _try(sc.render, "use_persistent_data", True)
    sc.render.resolution_x = sc.render.resolution_y = RES
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = True
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.render.image_settings.color_depth = "8"
    vs = sc.view_settings
    vs.view_transform = os.environ.get("FK_VIEW", VIEW)
    for look in (os.environ.get("FK_LOOK", LOOK), "AgX - " + os.environ.get("FK_LOOK", LOOK), "None"):
        if _try(vs, "look", look):
            break
    vs.exposure = float(os.environ.get("FK_EXPO", EXPOSURE))
    vs.gamma = 1.0
    sc.render.use_motion_blur = False
    # world: a dim studio gradient (bright ceiling, warm horizon, dark floor) - lights nothing much, but the
    # metal and the clear coat reflect it, so a gold fruit is never a black mirror
    if not sc.world:
        sc.world = bpy.data.worlds.new("DojoWorld")
    w = sc.world
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = _n(nt, "ShaderNodeOutputWorld", 800, 0)
    bg = _n(nt, "ShaderNodeBackground", 600, 0)
    tc = _n(nt, "ShaderNodeTexCoord", -400, 0)
    sep = _n(nt, "ShaderNodeSeparateXYZ", -200, 0)
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    r = _n(nt, "ShaderNodeValToRGB", 100, 0)
    r.color_ramp.interpolation = "EASE"
    stops = [(0.0, (0.05, 0.035, 0.03)), (0.46, (0.20, 0.13, 0.08)), (0.52, (0.55, 0.42, 0.30)),
             (0.62, (0.30, 0.30, 0.34)), (1.0, (0.85, 0.85, 0.9))]
    for i, (p, c) in enumerate(stops):
        e = r.color_ramp.elements[i] if i < 2 else r.color_ramp.elements.new(p)
        e.position = p
        e.color = c + (1,)
    mr = _n(nt, "ShaderNodeMapRange", -50, 0)          # Generated Z in the world is the direction's z (-1..1)
    mr.inputs["From Min"].default_value = -1.0
    mr.inputs["From Max"].default_value = 1.0
    nt.links.new(sep.outputs["Z"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], r.inputs[0])
    nt.links.new(r.outputs[0], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 0.45
    nt.links.new(bg.outputs[0], out.inputs["Surface"])

    cam = bpy.data.objects.get("DojoCam")
    if not cam:
        cam = bpy.data.objects.new("DojoCam", bpy.data.cameras.new("DojoCam"))
        sc.collection.objects.link(cam)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 2.7
    cam.location = (0, -10, 0)
    cam.rotation_euler = (math.radians(90), 0, 0)
    sc.camera = cam
    old = bpy.data.objects.get("DojoKey")               # the old toon sun
    if old and old.data.type == "SUN":
        bpy.data.objects.remove(old, do_unlink=True)
    # the rig (camera looks along +Y: -Y is toward it, +X right, +Z up)
    light("DojoKey", "AREA", (-3.4, -4.6, 3.8), 950, (1.0, 0.96, 0.9), 2.8, 2.2, shape="ELLIPSE")  # big softbox, upper left front
    light("DojoHot", "POINT", (-2.6, -5.2, 2.9), 160, (1.0, 1.0, 1.0), 0.04, diffuse=False)  # the sharp hot spot only
    light("DojoFill", "AREA", (4.6, -4.4, -0.6), 240, (0.62, 0.76, 1.0), 4.0, 4.0, shape="ELLIPSE")    # cool fill, right
    light("DojoBounce", "AREA", (0.4, -2.6, -4.6), 150, (1.0, 0.62, 0.34), 5.0, 2.0, shape="ELLIPSE")  # warm wood bounce, below
    light("DojoRimR", "AREA", (3.0, 4.4, 2.2), 2200, (1.0, 0.58, 0.18), 1.0, 3.6)         # amber rim, back right top
    light("DojoRimL", "AREA", (-3.4, 4.2, -0.6), 1800, (0.22, 0.58, 1.0), 1.0, 3.6)       # cyan rim, back left
    # reflector cards, switched on only while a metal fruit renders (each fruit renders on its own): big soft
    # specular-only panels the gold and the lacquered iron mirror, so polished metal reads bright gold, not a dark mirror
    on = CURRENT[0] in METAL
    for name, loc, e, c, sx, sy in (("DojoCardTop", (-0.6, -1.5, 6.0), 650, (1.0, 0.95, 0.85), 9.0, 6.0),
                                    ("DojoCardFront", (-1.5, -7.0, 0.6), 420, (1.0, 0.92, 0.78), 8.0, 4.0),
                                    ("DojoCardSide", (6.5, -2.0, 0.4), 380, (1.0, 0.78, 0.45), 4.0, 8.0)):
        card = light(name, "AREA", loc, e if on else 0.0, c, sx, sy, diffuse=False, shape="ELLIPSE")
        card.hide_render = not on
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


def _inp(node, name, v, nt=None):
    s = node.inputs.get(name)
    if s is None:
        print("fruitkit: no input", name, "on", node.bl_idname)
        return
    if isinstance(v, bpy.types.NodeSocket):
        nt.links.new(v, s)
    else:
        s.default_value = v


def gloss(name, colour_fn, rough=0.34, coat=0.9, coat_rough=0.035, spec=0.55, metal=0.0, sss=0.0,
          sss_rad=(1.0, 0.4, 0.25), sss_scale=0.08, trans=0.0, ior=1.45, sheen=0.0, sheen_tint=(1, 1, 1),
          glow=0.0, bump=None, bump_str=0.25, bump_dist=0.02, rough_fn=None, sat=1.12, val=1.0, coat_tint=(1, 1, 1),
          aniso=0.0, dome=0.0, coat_bump=False):
    """A glossy CGI surface. colour_fn(nt) -> colour socket; bump(nt) -> height socket (skin only: the clear
    coat stays smooth over it, the lacquered-candy look); rough_fn(nt) -> roughness socket."""
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = _n(nt, "ShaderNodeOutputMaterial", 1400, 0)
    bs = _n(nt, "ShaderNodeBsdfPrincipled", 1000, 0)
    col = colour_fn(nt)
    hs = _n(nt, "ShaderNodeHueSaturation", 700, 300)
    hs.inputs["Saturation"].default_value = sat
    hs.inputs["Value"].default_value = val
    nt.links.new(col, hs.inputs["Color"])
    col = hs.outputs["Color"]
    _inp(bs, "Base Color", col, nt)
    _inp(bs, "Metallic", metal)
    _inp(bs, "Roughness", rough_fn(nt) if rough_fn else rough, nt)
    _inp(bs, "IOR", ior)
    _inp(bs, "Specular IOR Level", spec)
    if coat > 0:
        _inp(bs, "Coat Weight", coat)
        _inp(bs, "Coat Roughness", coat_rough)
        _inp(bs, "Coat IOR", 1.5)
        _inp(bs, "Coat Tint", tuple(coat_tint) + (1,))
    if sss > 0:
        _inp(bs, "Subsurface Weight", sss)
        _inp(bs, "Subsurface Radius", Vector(sss_rad))
        _inp(bs, "Subsurface Scale", sss_scale)
    if trans > 0:
        _inp(bs, "Transmission Weight", trans)
    if sheen > 0:
        _inp(bs, "Sheen Weight", sheen)
        _inp(bs, "Sheen Roughness", 0.4)
        _inp(bs, "Sheen Tint", tuple(sheen_tint) + (1,))
    if aniso > 0:
        _inp(bs, "Anisotropic", aniso)
    if glow > 0:
        _inp(bs, "Emission Color", col, nt)
        _inp(bs, "Emission Strength", glow)
    nrm = None
    if dome:
        # a cut face is a flat plane: tilt its shading normal like a shallow lens (height -r^2 over the cut), so it
        # shades from centre to rim and catches the key in its wet coat instead of reading as a flat disc
        r, _ = radius_xz(nt, 100, -1500)
        d = _n(nt, "ShaderNodeBump", 500, -1500)
        d.inputs["Strength"].default_value = 1.0
        d.inputs["Distance"].default_value = dome
        nt.links.new(mnode(nt, "MULTIPLY", mnode(nt, "MULTIPLY", r, r, 300, -1500), -1.0, 400, -1500), d.inputs["Height"])
        nrm = d.outputs["Normal"]
        nt.links.new(nrm, bs.inputs["Coat Normal"])
    if bump:
        b = _n(nt, "ShaderNodeBump", 700, -300)
        b.inputs["Strength"].default_value = bump_str
        b.inputs["Distance"].default_value = bump_dist
        nt.links.new(bump(nt), b.inputs["Height"])
        if nrm is not None:
            nt.links.new(nrm, b.inputs["Normal"])
        nrm = b.outputs["Normal"]
    if nrm is not None:
        nt.links.new(nrm, bs.inputs["Normal"])
        if coat_bump:                                  # pores that show in the hot spot too
            nt.links.new(nrm, bs.inputs["Coat Normal"])
    nt.links.new(bs.outputs[0], out.inputs["Surface"])
    return m


def inside_gloss(name, colour_fn, glow=0.0, sss_rad=(1.0, 0.5, 0.3), bump=None, **kw):
    """A cut face: wet and juicy - saturated, glossy, a little translucent, a fine fibre bump under a wet coat."""
    kw.setdefault("rough", 0.22)
    kw.setdefault("coat", 0.75)
    kw.setdefault("coat_rough", 0.06)
    kw.setdefault("sss", 0.25)
    kw.setdefault("sss_scale", 0.05)
    kw.setdefault("sat", 1.25)
    kw.setdefault("val", 0.95)
    kw.setdefault("dome", 0.12)
    if bump is None:
        bump = lambda nt: noise(nt, 26.0, 4.0, x=200, y=-900)
    return gloss(name, colour_fn, glow=glow, sss_rad=sss_rad, bump=bump, bump_str=kw.pop("bump_str", 0.12), **kw)


def flat(rgb):
    def f(nt):
        n = _n(nt, "ShaderNodeRGB", 300, 0)
        n.outputs[0].default_value = tuple(rgb) + (1,)
        return n.outputs[0]
    return f


def coord(nt, x=-900, y=0, kind="Object"):
    tc = _n(nt, "ShaderNodeTexCoord", x, y)
    return tc.outputs[kind]


def ramp_of(nt, fac, stops, x=0, y=0, interp="LINEAR"):
    r = _n(nt, "ShaderNodeValToRGB", x, y)
    cr = r.color_ramp
    cr.interpolation = interp
    for i, (p, c) in enumerate(stops):
        e = cr.elements[i] if i < 2 else cr.elements.new(p)
        e.position = p
        e.color = (tuple(c) if not isinstance(c, (int, float)) else (c, c, c)) + (1,)
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


def smooth_lt(nt, v, edge, soft, x=0, y=0):
    """1 where v < edge, fading out over `soft` (a soft-edged LESS_THAN)."""
    mr = _n(nt, "ShaderNodeMapRange", x, y)
    mr.interpolation_type = "SMOOTHSTEP"
    mr.inputs["From Min"].default_value = edge - soft
    mr.inputs["From Max"].default_value = edge
    mr.inputs["To Min"].default_value = 1.0
    mr.inputs["To Max"].default_value = 0.0
    nt.links.new(v, mr.inputs["Value"])
    return mr.outputs["Result"]


def seeds(nt, base_col, seed_col, scale=6.0, size=0.12, inner=0.0, outer=1.0, x=0, y=-400, stretch=(1, 1, 1)):
    """Dark glossy seeds: voronoi cell distance < size, within a band of radius."""
    co = coord(nt, x - 800, y)
    mp = _n(nt, "ShaderNodeVectorMath", x - 600, y)
    mp.operation = "MULTIPLY"
    mp.inputs[1].default_value = stretch
    nt.links.new(co, mp.inputs[0])
    vor = _n(nt, "ShaderNodeTexVoronoi", x - 400, y)
    vor.inputs["Scale"].default_value = scale
    nt.links.new(mp.outputs[0], vor.inputs["Vector"])
    lt = smooth_lt(nt, vor.outputs["Distance"], size, size * 0.35, x - 200, y)
    r, _ = radius_xz(nt, x - 900, y - 250)
    band = ramp_of(nt, r, [(0.0, 0.0), (max(0.001, inner - 0.02), 0.0), (inner + 0.02, 1.0), (outer - 0.02, 1.0), (outer + 0.02, 0.0)],
                   x - 400, y - 250)
    bwb = _n(nt, "ShaderNodeRGBToBW", x - 150, y - 250)
    nt.links.new(band, bwb.inputs[0])
    mul = _n(nt, "ShaderNodeMath", x, y)
    mul.operation = "MULTIPLY"
    nt.links.new(lt, mul.inputs[0])
    nt.links.new(bwb.outputs[0], mul.inputs[1])
    mix = _n(nt, "ShaderNodeMix", x + 200, y)
    mix.data_type = "RGBA"
    nt.links.new(mul.outputs[0], mix.inputs[0])
    nt.links.new(base_col, mix.inputs[6])
    sc = _n(nt, "ShaderNodeRGB", x, y - 150)
    sc.outputs[0].default_value = tuple(seed_col) + (1,)
    nt.links.new(sc.outputs[0], mix.inputs[7])
    return mix.outputs[2]


def noise(nt, scale, detail=2.0, stretch=(1, 1, 1), x=-600, y=-300, rough=0.5, kind="Object", distort=0.0):
    co = coord(nt, x - 400, y, kind)
    mp = _n(nt, "ShaderNodeVectorMath", x - 200, y)
    mp.operation = "MULTIPLY"
    mp.inputs[1].default_value = stretch
    nt.links.new(co, mp.inputs[0])
    n = _n(nt, "ShaderNodeTexNoise", x, y)
    n.inputs["Scale"].default_value = scale
    n.inputs["Detail"].default_value = detail
    n.inputs["Roughness"].default_value = rough
    if distort:
        n.inputs["Distortion"].default_value = distort
    nt.links.new(mp.outputs[0], n.inputs["Vector"])
    return n.outputs["Fac"]


def pores(nt, scale=48.0, x=-600, y=-1100):
    """Citrus pores: little round dimples (voronoi F1 distance, low at the cell centres)."""
    co = coord(nt, x - 300, y)
    v = _n(nt, "ShaderNodeTexVoronoi", x, y)
    v.inputs["Scale"].default_value = scale
    nt.links.new(co, v.inputs["Vector"])
    return smooth_lt(nt, v.outputs["Distance"], 0.32, 0.22, x + 200, y)


# ---------------------------------------------------------------- meshes
def tag(ob):
    ob["fruitkit"] = True
    return ob


def _uv(me):
    if "UVMap" not in me.uv_layers:
        me.uv_layers.new(name="UVMap")
    return me.uv_layers["UVMap"]


def sphere(name, scale=(1, 1, 1), segs=64, rings=48):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=rings, radius=1.0)
    bmesh.ops.scale(bm, vec=Vector(scale), verts=bm.verts)
    bm.to_mesh(me)
    bm.free()
    _uv(me)
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


def outline(ob, width=0.042):
    """(The toon look's inverted-hull outline - gone in the glossy look; kept so old calls still run.)"""
    return None


def join(parts, name):
    bpy.ops.object.select_all(action="DESELECT")
    for p in parts:
        p.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = name
    return ob


# ---------------------------------------------------------------- watermelon (H1) - the rest live in fruits_more.py
def melon_stripes(nt, dark, light, n_str=7.0, mottle=0.35):
    """Jagged dark stripes round the long (X) axis."""
    co = coord(nt)
    sep = _n(nt, "ShaderNodeSeparateXYZ", -700, 0)
    nt.links.new(co, sep.inputs[0])
    ang = _n(nt, "ShaderNodeMath", -500, 0)
    ang.operation = "ARCTAN2"
    nt.links.new(sep.outputs["Z"], ang.inputs[0])
    nt.links.new(sep.outputs["Y"], ang.inputs[1])
    warp = noise(nt, 2.6, 4.0, x=-700, y=-250)
    fine = noise(nt, 9.0, 6.0, x=-700, y=-500, rough=0.65)
    w = _n(nt, "ShaderNodeMath", -350, -100)
    w.operation = "MULTIPLY_ADD"
    w.inputs[1].default_value = 0.9
    nt.links.new(warp, w.inputs[0])
    nt.links.new(ang.outputs[0], w.inputs[2])
    w2 = _n(nt, "ShaderNodeMath", -250, -150)
    w2.operation = "MULTIPLY_ADD"
    w2.inputs[1].default_value = 0.22
    nt.links.new(fine, w2.inputs[0])
    nt.links.new(w.outputs[0], w2.inputs[2])
    mul = _n(nt, "ShaderNodeMath", -150, 100)
    mul.operation = "MULTIPLY"
    mul.inputs[1].default_value = n_str
    nt.links.new(w2.outputs[0], mul.inputs[0])
    st = _n(nt, "ShaderNodeMath", -50, 0)
    st.operation = "SINE"
    nt.links.new(mul.outputs[0], st.inputs[0])
    base = ramp_of(nt, st.outputs[0], [(0.0, dark), (0.30, dark), (0.42, tuple(0.5 * (a + b) for a, b in zip(dark, light))), (0.52, light)], 100, 0)
    # a mottle in the light bands
    mot = noise(nt, 14.0, 3.0, x=-200, y=-700)
    return mix_col(nt, mnode(nt, "MULTIPLY", mot, mottle, 150, -700), base, tuple(c * 0.75 for c in light), 300, -200)


def mat_watermelon():
    return gloss("fk_H1_skin", lambda nt: melon_stripes(nt, (0.010, 0.10, 0.018), (0.20, 0.55, 0.06)),
                 rough=0.32, coat=0.85, sss=0.05, bump=lambda nt: noise(nt, 18.0, 4.0, x=200, y=-900), bump_str=0.08)


def mat_watermelon_in():
    def inside(nt):
        r, _ = radius_xz(nt, -900, 0)
        base = ramp_of(nt, r, [(0.0, (0.95, 0.04, 0.10)), (0.62, (1.0, 0.14, 0.18)), (0.80, (1.0, 0.50, 0.50)),
                               (0.85, (0.95, 0.96, 0.78)), (0.90, (0.55, 0.85, 0.30)), (0.93, (0.05, 0.30, 0.05))], -300, 0)
        return seeds(nt, base, (0.03, 0.015, 0.015), scale=7.0, size=0.15, inner=0.3, outer=0.72, stretch=(1, 1, 1.6))
    return inside_gloss("fk_H1_in", inside, sss_rad=(1.0, 0.25, 0.2))


def build_H1():
    ob = sphere("H1", (1.18, 0.98, 0.98))
    add_mat(ob, mat_watermelon())
    add_mat(ob, mat_watermelon_in())
    return ob


FRUIT = {"H1": build_H1}
NO_HALF = set()
METAL = {"SC", "JM", "BOMB"}
_more = os.path.join(os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.path.join(ROOT, "tools", "blender"), "fruits_more.py")
exec(open(_more, encoding="utf-8").read(), globals())


# ---------------------------------------------------------------- halves
def make_half(ob, side=1):
    """Bisect `ob` through the YZ plane and cap the cut with the INSIDE material."""
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
    return h


# ---------------------------------------------------------------- entry points
CURRENT = [""]          # the fruit being built/rendered (scene() switches the metal cards by it)


def build(ID):
    CURRENT[0] = ID
    scene()
    clear_fruit()
    ob = FRUIT[ID]()
    normalize(ob, 1.2)
    half = None
    parts = [ob]
    if ID not in NO_HALF:
        half = make_half(ob, -1)                       # keeps x > 0: the RIGHT half, its cut face toward -X
        other = make_half(ob, +1)                      # keeps x < 0: the LEFT half, its cut face toward +X
        for h in (half, other):
            h.hide_render = h.hide_viewport = True
        parts += [half, other]
    return ob, half


TILT = 25


def tumble_q(i, n, tilt=TILT):
    """Frame i of n: a full turn about an axis tilted toward the camera. Quaternion(axis, angle) stays continuous
    past half a turn (no sign flip), so keyframes between frames interpolate cleanly for motion blur."""
    axis = Vector((math.sin(math.radians(tilt)), 0, math.cos(math.radians(tilt))))
    return Quaternion(axis, 2 * math.pi * i / n)


def tumble(ob, i, n, tilt=TILT):
    ob.rotation_mode = "QUATERNION"
    ob.rotation_quaternion = tumble_q(i, n, tilt)


def _ease(t):
    return 1 - (1 - t) ** 3


F0 = 10                 # scene frame of clip frame 0 (keeps motion-blur keys off negative frames)


def _key_tumble(ob, n):
    prefs = bpy.context.preferences.edit
    old = prefs.keyframe_new_interpolation_type
    prefs.keyframe_new_interpolation_type = "LINEAR"
    ob.animation_data_clear()
    ob.rotation_mode = "QUATERNION"
    for i in range(-2, n + 3):
        ob.rotation_quaternion = tumble_q(i, n)
        ob.keyframe_insert("rotation_quaternion", frame=F0 + i)
    prefs.keyframe_new_interpolation_type = old


def render(ID, clips=("whole", "wob", "openR", "openL")):
    CURRENT[0] = ID
    sc = scene()
    ob = bpy.data.objects[ID]
    hr = bpy.data.objects.get(ID + "_halfL")           # make_half(ob, -1): the right half (x > 0)
    hl = bpy.data.objects.get(ID + "_halfR")           # make_half(ob, +1): the left half (x < 0)
    out = os.path.join(FRAMES, ID)
    os.makedirs(out, exist_ok=True)
    for f in os.listdir(out):                          # a clean set of the clips being rendered
        if f.endswith(".png") and f.split("_")[0] in clips:
            os.remove(os.path.join(out, f))
    plan = {"whole": (ob, N_WHOLE), "wob": (hr, N_WOB), "openR": (hr, N_OPEN), "openL": (hl, N_OPEN)}
    for clip in clips:
        tgt, n = plan[clip]
        if tgt is None:
            continue
        for o in (ob, hr, hl):
            if o:
                o.hide_render = o is not tgt
        tgt.rotation_mode = "QUATERNION"
        blur = clip == "whole" and MBLUR > 0
        sc.render.use_motion_blur = blur
        if blur:
            sc.render.motion_blur_shutter = MBLUR
            _try(sc.render, "motion_blur_position", "CENTER")
            _key_tumble(tgt, n)
        else:
            tgt.animation_data_clear()
        for i in range(n):
            sc.frame_set(F0 + i)
            if clip == "whole":
                if not blur:
                    tumble(tgt, i, n)
            elif clip == "wob":     # cut face to camera (+90 about Z), rocking
                a = math.radians(90) + math.radians(28) * math.sin(2 * math.pi * i / n)
                tgt.rotation_quaternion = Matrix.Rotation(a, 4, "Z").to_quaternion()
            else:                   # opening: from its place in the whole fruit to cut face toward camera
                k = _ease(i / (n - 1))
                a = math.radians(90 if clip == "openR" else -90) * k
                tgt.rotation_quaternion = Matrix.Rotation(a, 4, "Z").to_quaternion()
            sc.render.filepath = os.path.join(out, f"{clip}_{i:02d}.png")
            bpy.ops.render.render(write_still=True, scene=sc.name)
        if blur:
            tgt.animation_data_clear()
            sc.render.use_motion_blur = False
    print("rendered", ID, clips)


def preview(ID):
    """Whole fruit left, its half (cut face to camera) right - for looking at in the viewport."""
    ob, half = build(ID)
    if half is None:
        return ob, None
    half.hide_viewport = half.hide_render = False
    ob.location = (-1.35, 0, 0)
    tumble(ob, 4, 64)
    half.location = (1.35, 0, 0)
    half.rotation_mode = "QUATERNION"
    half.rotation_quaternion = (Matrix.Rotation(math.radians(20), 4, "Y") @ Matrix.Rotation(math.radians(90), 4, "Z")).to_quaternion()
    bpy.context.scene.camera.data.ortho_scale = 5.6
    bpy.context.scene.render.resolution_x = 2 * RES
    return ob, half


ALL = ["H1", "H2", "H3", "H4", "L1", "L2", "L3", "L4", "SC", "BOMB", "PW2", "PW3", "PW5", "FRZ", "JM"]


def gallery(ids=ALL, per_row=5):
    """Every fruit with its half beside it, for one look through the camera. (The lights are placed for one fruit at
    the origin, so the gallery is lit a little differently from the frames - use it for colour, not final judgement.)"""
    import traceback
    scene()
    clear_fruit()
    rows = (len(ids) + per_row - 1) // per_row
    for k, I in enumerate(ids):
        try:
            ob = FRUIT[I]()
            normalize(ob, 1.2)
            half = make_half(ob, -1) if I not in NO_HALF else None
            col, row = k % per_row, k // per_row
            x, z = col * 5.4 - (per_row - 1) * 2.7 - 1.3, (rows - 1) * 1.35 - row * 2.7
            ob.location = (x, 0, z)
            tumble(ob, 4, 64)
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


def track(ID="BOMB"):
    """Where the bomb's fuse spark is in every frame of the whole tumble, for the game's live spark FX:
    art/blender/frames/<ID>/track.json = {"fuse": [[u, v, vis], ...]} - u, v the spark's centre in the tile
    (0..1, y down), vis 0 when the bomb's body is in front of it. pack_sprites.py copies it into meta.json."""
    import json
    sc = scene()
    ob = bpy.data.objects[ID]
    ob.animation_data_clear()
    me = ob.data
    mats = [m.name if m else "" for m in me.materials]
    def centre(pred):
        vs = {v for p in me.polygons if pred(mats[p.material_index]) for v in p.vertices}
        return sum((me.vertices[v].co for v in vs), Vector()) / len(vs), vs
    spark, _ = centre(lambda n: n.startswith("fk_spark"))
    body, bv = centre(lambda n: n.startswith("fk_BOMB_skin"))
    br = max((me.vertices[v].co - body).length for v in bv)
    ortho = sc.camera.data.ortho_scale
    out = []
    for i in range(N_WHOLE):
        tumble(ob, i, N_WHOLE)
        bpy.context.view_layer.update()
        M = ob.matrix_world
        w, b = M @ spark, M @ body
        d = math.hypot(w.x - b.x, w.z - b.z)
        front = b.y - math.sqrt(max(0.0, br * br - d * d))   # the body's near surface on the spark's line of sight
        vis = 1.0 if d >= br * 0.98 or w.y < front else 0.0  # (the camera looks along +Y: smaller y is nearer)
        out.append([round(w.x / ortho + 0.5, 4), round(0.5 - w.z / ortho, 4), vis])
    path = os.path.join(FRAMES, ID, "track.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        json.dump({"fuse": out}, fh)
    print("track ->", path, sum(1 for o in out if o[2]), "of", len(out), "visible")


def look(ID, out=None):
    """Two stills lit exactly like the frames: the whole fruit (tumble frame 6 of 64) and its half, cut face to
    camera -> art/blender/frames/_look/<ID>_w.png / <ID>_h.png (git-ignored), for judging the look quickly."""
    sc = scene()
    out = out or os.path.join(FRAMES, "_look")
    os.makedirs(out, exist_ok=True)
    ob = bpy.data.objects[ID]
    hr = bpy.data.objects.get(ID + "_halfL")
    for o in (ob, hr, bpy.data.objects.get(ID + "_halfR")):
        if o:
            o.hide_render = True
            o.animation_data_clear()
    shots = [(ob, "w")] + ([(hr, "h")] if hr else [])
    for tgt, suffix in shots:
        tgt.hide_render = False
        tgt.rotation_mode = "QUATERNION"
        if suffix == "w":
            tumble(tgt, 6, 64)
        else:
            tgt.rotation_quaternion = (Matrix.Rotation(math.radians(14), 4, "Y") @ Matrix.Rotation(math.radians(90), 4, "Z")).to_quaternion()
        sc.render.filepath = os.path.join(out, f"{ID}_{suffix}.png")
        bpy.ops.render.render(write_still=True, scene=sc.name)
        tgt.hide_render = True


def gallery_render(path=None, ids=ALL):
    gallery(ids)
    sc = bpy.context.scene
    sc.render.filepath = path or os.path.join(ROOT, "art", "blender", "gallery.png")
    bpy.ops.render.render(write_still=True, scene=sc.name)
    print("gallery ->", sc.render.filepath)


if __name__ == "__main__" and "--" in sys.argv:  # headless
    args = sys.argv[sys.argv.index("--") + 1:]
    ids = ALL if not args or args[0] == "all" else args[0].split(",")
    steps = args[1].split(",") if len(args) > 1 else ["build", "render"]
    clips = tuple(args[2].split(",")) if len(args) > 2 else ("whole", "wob", "openR", "openL")
    if "gallery" in steps:
        gallery_render(ids=ids)
        ids = []
    for I in ids:
        if "build" in steps:
            build(I)
        if "render" in steps:
            render(I, clips)
        if "track" in steps:
            track(I)
        if "look" in steps:
            look(I)

# Fruit builders 2..15 for fruitkit.py (exec'd into the same namespace by fruitkit.py).
# Every builder returns ONE joined mesh object named after its ID, with material slot 0 = skin and
# slot 1 = inside (the material the cut face gets); extra slots after that are decorations.
# Every part carries a "UVMap" layer (sphere/cyl/stem make it): leaves and stems use it for veins and fibres.


# ---------------------------------------------------------------- shape helpers
def sph_deform(ob, fn):
    """fn(v, r, theta, phi) -> new vector; theta = polar angle from +Z, phi = azimuth."""
    for v in ob.data.vertices:
        c = Vector(v.co)
        r = c.length or 1e-6
        th = math.acos(max(-1.0, min(1.0, c.z / r)))
        ph = math.atan2(c.y, c.x)
        v.co = fn(c, r, th, ph)


def leaf(name, length=0.7, width=0.26, bend=0.25, fold=0.35, segs=24, rings=18):
    """A pointed leaf along +Z from the origin, curled back (bend) and folded along its midrib (fold).
    UV: u across the blade (0.5 = midrib), v from base (0) to tip (1)."""
    ob = sphere(name, (width, width * 0.16, length / 2), segs, rings)
    me = ob.data
    uvs = {}
    for v in me.vertices:
        c = Vector(v.co)
        t = (c.z / (length / 2) + 1) / 2                      # 0 base .. 1 tip
        taper = math.sin(math.pi * min(1.0, t * 0.95 + 0.05)) ** 0.8
        u = c.x / width                                       # -1 .. 1 across
        uvs[v.index] = (0.5 + 0.5 * u, t)
        x = c.x * taper
        y = c.y * taper + bend * t * t + fold * width * abs(u) * taper
        v.co = Vector((x, y, c.z + length / 2))
    uv = _uv(me)
    for lp in me.loops:
        uv.data[lp.index].uv = uvs[lp.vertex_index]
    return ob


def stem(name, r0=0.055, r1=0.035, h=0.32, bend=0.08, segs=16, rings=8, flare=1.8):
    """A curved, tapering stem along +Z with a flared base. UV v runs base -> tip."""
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    layers = []
    for j in range(rings + 1):
        t = j / rings
        r = r0 + (r1 - r0) * t
        if t < 0.18:
            r *= 1 + (flare - 1) * (1 - t / 0.18) ** 2
        cx = bend * t * t
        layers.append([(bm.verts.new((cx + r * math.cos(2 * math.pi * k / segs), r * math.sin(2 * math.pi * k / segs), h * t)), k / segs, t)
                       for k in range(segs)])
    for j in range(rings):
        for k in range(segs):
            a, b = layers[j][k], layers[j][(k + 1) % segs]
            c, d = layers[j + 1][(k + 1) % segs], layers[j + 1][k]
            f = bm.faces.new((a[0], b[0], c[0], d[0]))
            for lp, (vv, u, t) in zip(f.loops, (a, b, c, d)):
                lp[uvl].uv = (u if not (vv is b[0] or vv is c[0]) or k + 1 < segs else 1.0, t)
    top = bm.faces.new([p[0] for p in layers[-1]])
    bot = bm.faces.new([p[0] for p in layers[0]][::-1])
    for f in (top, bot):
        for lp in f.loops:
            lp[uvl].uv = (0.5, 1.0 if f is top else 0.0)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    for p in me.polygons:
        p.use_smooth = True
    return tag(ob)


def cyl(name, r, h, verts=24, taper=0.85):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=verts, radius1=r, radius2=r * taper, depth=h)
    bm.to_mesh(me)
    bm.free()
    _uv(me)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    for p in me.polygons:
        p.use_smooth = True
    return tag(ob)


def torus(name, R, r, segs=48, rsegs=16):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    vs = [[bm.verts.new(((R + r * math.cos(b)) * math.cos(a), (R + r * math.cos(b)) * math.sin(a), r * math.sin(b)))
           for b in (2 * math.pi * j / rsegs for j in range(rsegs))] for a in (2 * math.pi * i / segs for i in range(segs))]
    for i in range(segs):
        for j in range(rsegs):
            bm.faces.new((vs[i][j], vs[(i + 1) % segs][j], vs[(i + 1) % segs][(j + 1) % rsegs], vs[i][(j + 1) % rsegs]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(me)
    bm.free()
    _uv(me)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    for p in me.polygons:
        p.use_smooth = True
    return tag(ob)


def place(ob, loc=(0, 0, 0), rot=(0, 0, 0), scale=1.0):
    """Bake a transform into the mesh (rot in degrees, XYZ euler)."""
    from mathutils import Euler
    M = Matrix.Translation(loc) @ Euler([math.radians(a) for a in rot], "XYZ").to_matrix().to_4x4() @ Matrix.Scale(scale, 4)
    ob.data.transform(M)
    return ob


def normalize(ob, R=1.2):
    m = max(v.co.length for v in ob.data.vertices)
    ob.data.transform(Matrix.Scale(R / m, 4))


# ---------------------------------------------------------------- node helpers
def angle_about(nt, axis="Z", x=-700, y=0):
    co = coord(nt, x - 300, y)
    sep = _n(nt, "ShaderNodeSeparateXYZ", x, y)
    nt.links.new(co, sep.inputs[0])
    a, b = {"Z": ("Y", "X"), "X": ("Z", "Y")}[axis]
    at = _n(nt, "ShaderNodeMath", x + 200, y)
    at.operation = "ARCTAN2"
    nt.links.new(sep.outputs[a], at.inputs[0])
    nt.links.new(sep.outputs[b], at.inputs[1])
    return at.outputs[0], sep


def mnode(nt, op, a, b=None, x=0, y=0):
    n = _n(nt, "ShaderNodeMath", x, y)
    n.operation = op
    for i, v in enumerate((a, b)):
        if v is None:
            continue
        if isinstance(v, (int, float)):
            n.inputs[i].default_value = v
        else:
            nt.links.new(v, n.inputs[i])
    return n.outputs[0]


def mix_col(nt, fac, a, b, x=0, y=0, blend="MIX"):
    n = _n(nt, "ShaderNodeMix", x, y)
    n.data_type = "RGBA"
    n.blend_type = blend
    for i, v in ((0, fac), (6, a), (7, b)):
        if isinstance(v, (int, float)):
            n.inputs[i].default_value = v
        elif isinstance(v, tuple):
            n.inputs[i].default_value = tuple(v) + (1,) if len(v) == 3 else v
        else:
            nt.links.new(v, n.inputs[i])
    return n.outputs[2]


def rgb(nt, c, x=-200, y=-700):
    n = _n(nt, "ShaderNodeRGB", x, y)
    n.outputs[0].default_value = tuple(c) + (1,)
    return n.outputs[0]


def uv_sep(nt, x=-900, y=600):
    sep = _n(nt, "ShaderNodeSeparateXYZ", x + 200, y)
    nt.links.new(coord(nt, x, y, "UV"), sep.inputs[0])
    return sep.outputs["X"], sep.outputs["Y"]


def leaf_veins(nt):
    """0..1 vein mask from the leaf UV: a midrib and paired side veins sweeping toward the tip."""
    u, v = uv_sep(nt)
    du = mnode(nt, "ABSOLUTE", mnode(nt, "SUBTRACT", u, 0.5))
    mid = smooth_lt(nt, du, 0.035, 0.02, -300, 700)
    s = mnode(nt, "SINE", mnode(nt, "MULTIPLY", mnode(nt, "SUBTRACT", v, mnode(nt, "MULTIPLY", du, 0.55)), 44.0))
    side = mnode(nt, "MULTIPLY", mnode(nt, "GREATER_THAN", s, 0.88), mnode(nt, "GREATER_THAN", du, 0.04))
    return mnode(nt, "MAXIMUM", mid, mnode(nt, "MULTIPLY", side, 0.7)), v


def leaf_mat(name="fk_leaf", base=(0.06, 0.40, 0.05), tip=(0.30, 0.70, 0.10), vein=(0.55, 0.85, 0.30)):
    def colour(nt):
        veins, v = leaf_veins(nt)
        body = ramp_of(nt, v, [(0.0, base), (1.0, tip)], 100, 400)
        return mix_col(nt, veins, body, vein, 300, 300)
    return gloss(name, colour, rough=0.3, coat=0.7, coat_rough=0.05, sss=0.2, sss_rad=(0.4, 1.0, 0.2), sat=1.15,
                 bump=lambda nt: mnode(nt, "MULTIPLY", leaf_veins(nt)[0], -1.0, 200, -900), bump_str=0.35)


def stem_mat(name="fk_stem", base=(0.30, 0.17, 0.06), tip=(0.42, 0.32, 0.10)):
    def colour(nt):
        u, v = uv_sep(nt)
        fib = noise(nt, 6.0, 4.0, (12, 1, 1), x=-300, y=100, kind="UV")
        b = ramp_of(nt, v, [(0.0, base), (1.0, tip)], 100, 300)
        return mix_col(nt, mnode(nt, "MULTIPLY", fib, 0.5), b, tuple(c * 0.55 for c in base), 300, 200)
    return gloss(name, colour, rough=0.45, coat=0.4, sat=1.05,
                 bump=lambda nt: noise(nt, 6.0, 4.0, (12, 1, 1), x=200, y=-900, kind="UV"), bump_str=0.4)


def citrus_inside(name, flesh, pith=(1.0, 0.98, 0.9), rind=(1.0, 0.55, 0.05), n_seg=10, glow=0.0):
    """Segments with pale membranes, juice-sac grain, a white pith ring and the rind."""
    def inside(nt):
        r, _ = radius_xz(nt, -900, 300)
        sac = noise(nt, 30.0, 3.0, x=-500, y=500)
        fl = mix_col(nt, mnode(nt, "MULTIPLY", sac, 0.45), flesh, tuple(min(1.0, c * 1.25 + 0.1) for c in flesh), -500, 300)
        base = ramp_of(nt, r, [(0.0, pith), (0.07, flesh), (0.83, flesh), (0.86, pith), (0.90, pith), (0.93, rind)], -300, 300)
        base = mix_col(nt, mnode(nt, "MULTIPLY", smooth_lt(nt, r, 0.83, 0.05, -350, 600), mnode(nt, "GREATER_THAN", r, 0.07)), base, fl, -100, 300)
        a, _ = angle_about(nt, "X", -900, -100)
        s = mnode(nt, "ABSOLUTE", mnode(nt, "SINE", mnode(nt, "MULTIPLY", a, n_seg / 2, -500, -100), None, -350, -100), None, -200, -100)
        line = mnode(nt, "MULTIPLY", smooth_lt(nt, s, 0.06, 0.04, -50, -100), mnode(nt, "LESS_THAN", r, 0.84, -50, -250), 100, -150)
        return mix_col(nt, line, base, pith, 300, 0)
    return inside_gloss(name, inside, glow=glow, sss_rad=(1.0, 0.6, 0.2), sss=0.35,
                        bump=lambda nt: noise(nt, 30.0, 3.0, x=200, y=-900), bump_str=0.18)


def inside_mat(name, stops, seed=None, glow=0.0, sss_rad=(1.0, 0.5, 0.3), **kw):
    """Cut-face material: radial bands (radius 0 centre .. ~0.95 rim) plus optional seeds."""
    def inside(nt):
        r, _ = radius_xz(nt, -900, 0)
        base = ramp_of(nt, r, stops, -300, 0)
        if seed:
            return seeds(nt, base, seed[0], scale=seed[1], size=seed[2], inner=seed[3], outer=seed[4])
        return base
    return inside_gloss(name, inside, glow=glow, sss_rad=sss_rad, **kw)


def stem_leaf(prefix, top=0.95, leaf_len=0.55, stem_h=0.30, leaf_rot=(0, 62, 30), leaf_m=None, stem_m=None):
    st = stem(prefix + "_stem", 0.05, 0.032, stem_h, bend=0.07)
    place(st, (0.0, 0, top - 0.08), (0, 10, 0))
    add_mat(st, stem_m or stem_mat())
    lf = leaf(prefix + "_leaf", length=leaf_len, width=0.21, bend=0.14)
    place(lf, (0.02, 0, top), leaf_rot)
    add_mat(lf, leaf_m or leaf_mat())
    return [st, lf]


# ---------------------------------------------------------------- fruit
def build_H2():
    """Pineapple: raised diamond eyes, a gold-to-amber body and a fan of veined crown leaves."""
    body = sphere("H2", (0.74, 0.74, 0.92))
    sph_deform(body, lambda c, r, th, ph: c * (1 + 0.04 * abs(math.sin(ph * 8 + c.z * 9) * math.sin(ph * 8 - c.z * 9)) ** 0.6))

    def eyes(nt):
        a, sep = angle_about(nt, "Z")
        z = sep.outputs["Z"]
        u = mnode(nt, "SINE", mnode(nt, "ADD", mnode(nt, "MULTIPLY", a, 8), mnode(nt, "MULTIPLY", z, 9)))
        v = mnode(nt, "SINE", mnode(nt, "SUBTRACT", mnode(nt, "MULTIPLY", a, 8), mnode(nt, "MULTIPLY", z, 9)))
        return mnode(nt, "ABSOLUTE", mnode(nt, "MULTIPLY", u, v))

    def skin(nt):
        d = eyes(nt)
        return ramp_of(nt, d, [(0.0, (0.22, 0.09, 0.01)), (0.07, (0.62, 0.30, 0.03)), (0.2, (0.95, 0.58, 0.06)),
                               (0.5, (1.0, 0.80, 0.18)), (0.8, (0.85, 0.72, 0.15))], 450, 0)
    add_mat(body, gloss("fk_H2_skin", skin, rough=0.38, coat=0.75, sss=0.08, bump=eyes, bump_str=0.55, bump_dist=0.03))
    add_mat(body, inside_mat("fk_H2_in", [(0.0, (1.0, 0.95, 0.62)), (0.16, (1.0, 0.86, 0.28)), (0.80, (1.0, 0.78, 0.16)),
                                          (0.86, (0.95, 0.62, 0.10)), (0.92, (0.55, 0.30, 0.05))],
                             sss_rad=(1.0, 0.8, 0.3), bump=lambda nt: noise(nt, 14.0, 3.0, (1, 4, 4), x=200, y=-900)))
    green = leaf_mat("fk_H2_leaf", base=(0.04, 0.30, 0.10), tip=(0.22, 0.62, 0.14), vein=(0.30, 0.70, 0.28))
    parts = []
    for i in range(14):
        ring = i % 3
        lf = leaf(f"H2_l{i}", length=0.55 + 0.32 * (ring == 0) + 0.12 * (i % 2), width=0.13, bend=0.18, fold=0.5)
        place(lf, (0, 0, 0.8), (10 + 22 * ring, 0, i * (360 / 14) + 11 * (i % 2)))
        add_mat(lf, green)
        parts.append(lf)
    ob = join([body] + parts, "H2")
    ob.data.transform(Matrix.Translation((0, 0, -0.22)))
    return ob


def build_H3():
    """Dragon fruit: hot magenta skin, curled scales going leaf-green at the tips; white flesh, black seeds."""
    body = sphere("H3", (0.8, 0.8, 1.0))
    add_mat(body, gloss("fk_H3_skin", lambda nt: ramp_of(nt, noise(nt, 1.6, 2.0), [(0.0, (0.80, 0.02, 0.36)), (0.5, (0.95, 0.10, 0.50)), (0.75, (1.0, 0.25, 0.62))]),
                        rough=0.3, coat=0.9, sss=0.12, sss_rad=(1.0, 0.2, 0.5), bump=lambda nt: noise(nt, 10.0, 3.0, x=200, y=-900), bump_str=0.08))
    add_mat(body, inside_mat("fk_H3_in", [(0.0, (0.80, 0.78, 0.76)), (0.86, (0.74, 0.70, 0.72)), (0.9, (1.0, 0.45, 0.70)), (0.94, (0.90, 0.10, 0.45))],
                             seed=((0.02, 0.015, 0.02), 16.0, 0.11, 0.02, 0.82), sss_rad=(1.0, 0.9, 0.9)))
    scale_m = gloss("fk_H3_scale", lambda nt: ramp_of(nt, uv_sep(nt)[1], [(0.0, (0.92, 0.06, 0.45)), (0.5, (1.0, 0.25, 0.58)),
                                                                           (0.72, (0.70, 0.75, 0.25)), (0.9, (0.35, 0.78, 0.12))]),
                    rough=0.3, coat=0.85, sss=0.25, sss_rad=(1.0, 0.4, 0.4))
    parts = []
    rows = [(-0.6, 6, 0), (-0.15, 7, 25), (0.32, 6, 10), (0.72, 5, 40)]
    for zi, (z, n, off) in enumerate(rows):
        for i in range(n):
            ph = off + i * 360 / n
            rr = 0.8 * math.sqrt(max(0.05, 1 - z * z))
            lf = leaf(f"H3_s{zi}_{i}", length=0.46, width=0.16, bend=0.12, fold=0.3, segs=20, rings=14)
            add_mat(lf, scale_m)
            P = Vector((rr * math.cos(math.radians(ph)), rr * math.sin(math.radians(ph)), z))
            N = Vector((P.x / 0.64, P.y / 0.64, P.z)).normalized()          # ellipsoid normal
            T = (Vector((0, 0, 1)) - N * N.z).normalized()
            D = (T * math.cos(math.radians(38)) + N * math.sin(math.radians(38))).normalized()
            X = T.cross(N).normalized()
            Y = D.cross(X).normalized()
            R = Matrix((X, Y, D)).transposed().to_4x4()
            lf.data.transform(Matrix.Translation(P * 0.96) @ R)
            parts.append(lf)
    return join([body] + parts, "H3")


def build_H4():
    """Coconut: shaggy brown fibre with a lacquer sheen, three dark eyes; snow-white meat round a pearly centre."""
    body = sphere("H4", (1.0, 1.0, 0.94))
    sph_deform(body, lambda c, r, th, ph: c * (1 + 0.025 * math.sin(ph * 3) + 0.012 * math.sin(ph * 23 + th * 7)))
    fib = lambda nt: noise(nt, 6.0, 8.0, (1, 1, 0.22), x=200, y=-900, rough=0.65, distort=0.4)
    add_mat(body, gloss("fk_H4_skin", lambda nt: ramp_of(nt, noise(nt, 6.0, 8.0, (1, 1, 0.22), rough=0.65, distort=0.4),
                                                          [(0.0, (0.14, 0.06, 0.02)), (0.42, (0.32, 0.16, 0.06)), (0.6, (0.55, 0.32, 0.14)), (0.75, (0.72, 0.48, 0.24))]),
                        rough=0.5, coat=0.45, coat_rough=0.12, sheen=0.4, sheen_tint=(1.0, 0.8, 0.6), bump=fib, bump_str=0.5))
    add_mat(body, inside_mat("fk_H4_in", [(0.0, (0.50, 0.66, 0.80)), (0.58, (0.62, 0.74, 0.84)), (0.62, (0.84, 0.82, 0.78)),
                                          (0.83, (0.78, 0.75, 0.68)), (0.86, (0.35, 0.18, 0.06)), (0.95, (0.25, 0.12, 0.04))],
                             sss_rad=(0.9, 0.95, 1.0), rough=0.15))
    eye = gloss("fk_H4_eye", flat((0.05, 0.025, 0.01)), rough=0.35, coat=0.6)
    parts = []
    for i in range(3):
        a = math.radians(90 + i * 120)
        e = sphere(f"H4_e{i}", (0.1, 0.1, 0.05), 20, 12)
        place(e, (0.22 * math.cos(a), 0.22 * math.sin(a), 0.9))
        add_mat(e, eye)
        parts.append(e)
    return join([body] + parts, "H4")


def citrus_skin(name, base, deep, light, pore_scale=46.0, glow=0.0):
    def colour(nt):
        n = noise(nt, 1.6, 2.0)
        c = ramp_of(nt, n, [(0.35, base), (0.7, light)])
        return mix_col(nt, mnode(nt, "MULTIPLY", pores(nt, pore_scale), 0.2), c, deep, 300, -200)
    return gloss(name, colour, rough=0.3, coat=0.75, coat_rough=0.05, sss=0.15, sss_rad=(1.0, 0.5, 0.1), glow=glow,
                 bump=lambda nt: mnode(nt, "MULTIPLY", pores(nt, pore_scale, 0, -1300), -1.0, 300, -1300), bump_str=1.0, bump_dist=0.03, coat_bump=True)


def build_L1():
    """Orange: deep glossy orange with pores, a stem and a leaf."""
    body = sphere("L1", (1, 1, 0.96))
    add_mat(body, citrus_skin("fk_L1_skin", (1.0, 0.36, 0.0), (0.80, 0.18, 0.0), (1.0, 0.46, 0.02), 34.0))
    add_mat(body, citrus_inside("fk_L1_in", (1.0, 0.45, 0.02), rind=(1.0, 0.40, 0.0)))
    return join([body] + stem_leaf("L1", top=0.93), "L1")


def build_L2():
    """Apple: candy-glossy red with gold streaks and lenticels; cream flesh, brown pips."""
    body = sphere("L2", (1, 1, 0.9))

    def f(c, r, th, ph):
        d2 = c.x * c.x + c.y * c.y
        z = c.z - 0.32 * math.exp(-d2 / 0.06) * (1 if c.z > 0 else 0.5)
        k = 1 + 0.08 * max(0.0, c.z)
        return Vector((c.x * k, c.y * k, z))
    sph_deform(body, f)

    def skin(nt):
        st = noise(nt, 2.0, 4.0, (5, 5, 0.35))
        c = ramp_of(nt, st, [(0.0, (0.45, 0.0, 0.02)), (0.45, (0.80, 0.02, 0.04)), (0.66, (0.95, 0.12, 0.05)), (0.8, (1.0, 0.45, 0.08))])
        dots = smooth_lt(nt, _vor(nt, 34.0), 0.08, 0.04, -200, -900)
        return mix_col(nt, mnode(nt, "MULTIPLY", dots, 0.6), c, (1.0, 0.75, 0.40), 300, -200)
    add_mat(body, gloss("fk_L2_skin", skin, rough=0.22, coat=1.0, coat_rough=0.025, sss=0.1, sss_rad=(1.0, 0.2, 0.15)))
    add_mat(body, inside_mat("fk_L2_in", [(0.0, (1.0, 0.84, 0.45)), (0.2, (1.0, 0.94, 0.66)), (0.88, (1.0, 0.92, 0.62)), (0.92, (1.0, 0.82, 0.55)), (0.95, (0.80, 0.02, 0.05))],
                             seed=((0.25, 0.10, 0.03), 5.0, 0.12, 0.08, 0.26), sss_rad=(1.0, 0.9, 0.6)))
    return join([body] + stem_leaf("L2", top=0.6, leaf_rot=(0, 70, 40)), "L2")


def _vor(nt, scale, x=-600, y=-900):
    co = coord(nt, x - 300, y)
    v = _n(nt, "ShaderNodeTexVoronoi", x, y)
    v.inputs["Scale"].default_value = scale
    nt.links.new(co, v.inputs["Vector"])
    return v.outputs["Distance"]


def build_L3():
    """Lemon: bright lemon-yellow, pored, pointed ends."""
    body = sphere("L3", (0.74, 0.74, 1.0))

    def f(c, r, th, ph):
        t = abs(c.z)
        k = 1 - 0.2 * t ** 3
        z = c.z * (1 + (0.18 * (t - 0.85) / 0.15 if t > 0.85 else 0))
        return Vector((c.x * k, c.y * k, z))
    sph_deform(body, f)
    add_mat(body, citrus_skin("fk_L3_skin", (1.0, 0.78, 0.0), (0.90, 0.55, 0.0), (1.0, 0.88, 0.10), 38.0))
    add_mat(body, citrus_inside("fk_L3_in", (1.0, 0.90, 0.25), rind=(1.0, 0.80, 0.02), n_seg=9))
    body.data.transform(Matrix.Rotation(math.radians(70), 4, "Y"))
    return body


def build_L4():
    """Kiwi: fuzzy brown with a soft sheen; emerald flesh, a cream core, a ring of black seeds."""
    body = sphere("L4", (0.82, 0.82, 1.0))
    add_mat(body, gloss("fk_L4_skin", lambda nt: ramp_of(nt, noise(nt, 14.0, 8.0, rough=0.6),
                                                          [(0.0, (0.12, 0.055, 0.018)), (0.5, (0.26, 0.13, 0.045)), (0.68, (0.40, 0.24, 0.09))]),
                        rough=0.55, coat=0.4, coat_rough=0.1, sheen=0.6, sheen_tint=(0.75, 0.5, 0.28),
                        bump=lambda nt: noise(nt, 40.0, 4.0, x=200, y=-900), bump_str=0.3))
    def kiwi_in(nt):
        r, _ = radius_xz(nt, -900, 0)
        base = ramp_of(nt, r, [(0.0, (0.80, 0.80, 0.55)), (0.14, (0.66, 0.82, 0.28)), (0.24, (0.30, 0.78, 0.02)),
                               (0.82, (0.18, 0.62, 0.0)), (0.86, (0.50, 0.80, 0.25)), (0.9, (0.38, 0.24, 0.10))], -300, 0)
        # a ring of short black dashes pointing out from the core, a little irregular
        a, _ = angle_about(nt, "X", -900, -400)
        jit = noise(nt, 6.0, 2.0, x=-700, y=-700)
        ray = mnode(nt, "ABSOLUTE", mnode(nt, "SINE", mnode(nt, "ADD", mnode(nt, "MULTIPLY", a, 17.0), mnode(nt, "MULTIPLY", jit, 3.0))))
        dash = smooth_lt(nt, mnode(nt, "SUBTRACT", 1.0, ray), 0.22, 0.08, -300, -400)
        rr = mnode(nt, "ADD", r, mnode(nt, "MULTIPLY", jit, 0.08))
        band = mnode(nt, "MULTIPLY", mnode(nt, "GREATER_THAN", rr, 0.22), mnode(nt, "LESS_THAN", rr, 0.44))
        return mix_col(nt, mnode(nt, "MULTIPLY", dash, band), base, (0.02, 0.02, 0.01), 200, 0)
    add_mat(body, inside_gloss("fk_L4_in", kiwi_in, sss_rad=(0.4, 1.0, 0.2), sss=0.3))
    body.data.transform(Matrix.Rotation(math.radians(60), 4, "Y"))
    return body


GOLD = (1.0, 0.68, 0.22)


def build_SC():
    """Golden star fruit: a rounded 5-point star prism along X in polished gold; the cut shows a glowing star."""
    me = bpy.data.meshes.new("SC")
    bm = bmesh.new()
    prof = []
    for k in range(10):
        a = math.pi / 2 + k * math.pi / 5
        rr = 1.0 if k % 2 == 0 else 0.5
        prof.append((rr * math.cos(a), rr * math.sin(a)))
    rings = 14
    layers = []
    for j in range(rings + 1):
        x = -1.0 + 2.0 * j / rings
        s = math.sqrt(max(0.0, 1 - abs(x) ** 2.4)) * 0.92 + 0.08
        layers.append([bm.verts.new((x * 1.25, py * s, pz * s)) for py, pz in prof])
    for j in range(rings):
        for k in range(10):
            bm.faces.new((layers[j][k], layers[j][(k + 1) % 10], layers[j + 1][(k + 1) % 10], layers[j + 1][k]))
    bm.faces.new(layers[0][::-1])
    bm.faces.new(layers[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=1, use_grid_fill=True, smooth=1.0)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=1, use_grid_fill=True, smooth=1.0)
    bm.to_mesh(me)
    bm.free()
    _uv(me)
    ob = tag(bpy.data.objects.new("SC", me))
    bpy.context.scene.collection.objects.link(ob)
    for p in me.polygons:
        p.use_smooth = True
    add_mat(ob, gloss("fk_SC_skin", lambda nt: ramp_of(nt, noise(nt, 3.0, 2.0), [(0.3, (1.0, 0.60, 0.16)), (0.7, (1.0, 0.76, 0.30))]),
                      metal=1.0, rough=0.17, coat=0.6, coat_rough=0.03, glow=0.06, sat=1.1))
    add_mat(ob, inside_mat("fk_SC_in", [(0.0, (1.0, 0.96, 0.62)), (0.15, (1.0, 0.86, 0.25)), (0.75, (1.0, 0.76, 0.10))],
                           seed=((0.45, 0.25, 0.02), 6.0, 0.12, 0.12, 0.3), glow=0.35, sss_rad=(1.0, 0.8, 0.2)))
    return ob


def build_BOMB():
    """Black-iron bomb, lacquered, with a brass collar and a twisted fuse ending in a spark."""
    body = sphere("BOMB", (1, 1, 1))
    iron = lambda nt: ramp_of(nt, noise(nt, 4.0, 3.0), [(0.3, (0.028, 0.03, 0.04)), (0.7, (0.05, 0.055, 0.07))])
    add_mat(body, gloss("fk_BOMB_skin", iron, metal=0.55, rough=0.32, coat=1.0, coat_rough=0.03, spec=0.6,
                        bump=lambda nt: mnode(nt, "MULTIPLY", _vor(nt, 5.0, 0, -1200), 1.0, 200, -1200), bump_str=0.06))
    add_mat(body, gloss("fk_BOMB_skin_in", flat((0.03, 0.03, 0.04)), metal=0.5, rough=0.4))
    brass = gloss("fk_brass", lambda nt: ramp_of(nt, noise(nt, 8.0, 3.0), [(0.3, (0.85, 0.55, 0.18)), (0.7, (1.0, 0.72, 0.30))]),
                  metal=1.0, rough=0.22, coat=0.5, coat_rough=0.05)
    cap = cyl("BOMB_cap", 0.34, 0.26, 40, taper=0.88)
    place(cap, (0, 0, 0.98))
    add_mat(cap, brass)
    lip = torus("BOMB_lip", 0.30, 0.045)
    place(lip, (0, 0, 1.11))
    add_mat(lip, brass)
    base = torus("BOMB_ring", 0.35, 0.04)
    place(base, (0, 0, 0.87))
    add_mat(base, brass)
    rope = gloss("fk_fuse", lambda nt: ramp_of(nt, mnode(nt, "SINE", mnode(nt, "ADD", mnode(nt, "MULTIPLY", uv_sep(nt)[1], 60.0),
                                                                                 mnode(nt, "MULTIPLY", uv_sep(nt)[0], 6.283))),
                                                 [(0.0, (0.45, 0.32, 0.16)), (0.8, (0.88, 0.74, 0.48))]),
                 rough=0.6, coat=0.2, sheen=0.5)
    fuse = []
    pts = [Vector((0.0, 0, 1.0)), Vector((0.05, 0, 1.3)), Vector((0.2, 0, 1.5)), Vector((0.42, 0, 1.6)), Vector((0.6, 0, 1.58))]
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        seg = stem(f"BOMB_f{i}", 0.08, 0.075, (b - a).length + 0.08, bend=0.0, segs=14, rings=4, flare=1.0)
        d = (b - a).normalized()
        q = Vector((0, 0, 1)).rotation_difference(d)
        seg.data.transform(Matrix.Translation(a - d * 0.04) @ q.to_matrix().to_4x4())
        add_mat(seg, rope)
        fuse.append(seg)
    spark = sphere("BOMB_spark", (0.2, 0.2, 0.2), 24, 16)
    sph_deform(spark, lambda c, r, th, ph: c * (1 + 1.1 * max(0.0, math.sin(ph * 4) * math.sin(th * 4)) ** 2))
    place(spark, (0.66, 0, 1.6))
    sm = bpy.data.materials.get("fk_spark") or bpy.data.materials.new("fk_spark")
    sm.use_nodes = True
    nt = sm.node_tree
    nt.nodes.clear()
    o = _n(nt, "ShaderNodeOutputMaterial", 300, 0)
    em = _n(nt, "ShaderNodeEmission", 0, 0)
    em.inputs["Color"].default_value = (1.0, 0.55, 0.10, 1)
    em.inputs["Strength"].default_value = 3.0
    nt.links.new(em.outputs[0], o.inputs["Surface"])
    add_mat(spark, sm)
    ob = join([body, cap, lip, base, spark] + fuse, "BOMB")
    ob.data.transform(Matrix.Translation((0, 0, -0.25)))
    return ob


def _zgrad(nt):
    """0 at the bottom-right .. 1 at the top-left of the object: a soft blush across the fruit."""
    co = coord(nt, -900, 200)
    dp = _n(nt, "ShaderNodeVectorMath", -700, 200)
    dp.operation = "DOT_PRODUCT"
    dp.inputs[1].default_value = (-0.45, 0.0, 0.9)
    nt.links.new(co, dp.inputs[0])
    return mnode(nt, "ADD", mnode(nt, "MULTIPLY", dp.outputs["Value"], 0.5, -550, 200), 0.5, -400, 200)


def build_peach(ID, skin_a, skin_b, flesh, sss_rad):
    """A multiplier peach: jewel-tinted, candy-glossy, a little inner glow; flesh in its tint, a pitted stone."""
    body = sphere(ID, (1, 1, 0.97))

    def f(c, r, th, ph):
        ang = math.atan2(c.x, c.y)                            # 0 on the +Y meridian (the cleft)
        cleft = 0.08 * math.exp(-(ang * ang) / 0.02) * math.sin(th)
        return c * (1 - cleft)
    sph_deform(body, f)
    add_mat(body, gloss(f"fk_{ID}_skin", lambda nt: ramp_of(nt, _zgrad(nt), [(0.0, skin_a), (0.45, skin_a), (0.9, skin_b)]),
                        rough=0.3, coat=1.0, coat_rough=0.03, sss=0.3, sss_rad=sss_rad, sss_scale=0.1, sheen=0.3, glow=0.1, sat=1.15))

    def stone(nt):
        r, _ = radius_xz(nt, -900, 0)
        base = ramp_of(nt, r, [(0.0, (0.40, 0.16, 0.06)), (0.28, (0.55, 0.26, 0.10)), (0.31, (0.95, 0.80, 0.55)), (0.34, flesh),
                               (0.86, flesh), (0.93, skin_a)], -300, 0)
        return mix_col(nt, mnode(nt, "MULTIPLY", noise(nt, 18.0, 4.0, x=-400, y=-500), smooth_lt(nt, r, 0.3, 0.02, -200, -500)), base, (0.28, 0.10, 0.04), 100, -300)
    add_mat(body, inside_gloss(f"fk_{ID}_in", stone, glow=0.25, sss_rad=sss_rad))
    ob = join([body] + stem_leaf(ID, top=0.9, leaf_rot=(0, 55, -20)), ID)
    ob.data.transform(Matrix.Rotation(math.radians(-35), 4, "Z"))
    return ob


def build_PW2():
    return build_peach("PW2", (0.0, 0.16, 1.0), (0.0, 0.78, 1.0), (0.22, 0.62, 1.0), (0.3, 0.6, 1.0))


def build_PW3():
    return build_peach("PW3", (0.36, 0.0, 0.95), (0.95, 0.35, 1.0), (0.70, 0.28, 1.0), (0.8, 0.4, 1.0))


def build_PW5():
    return build_peach("PW5", (0.95, 0.03, 0.06), (1.0, 0.72, 0.08), (1.0, 0.58, 0.10), (1.0, 0.4, 0.2))


def build_FRZ():
    """Frost grapes: icy translucent globes with frosted patches and a frosted stem."""
    def ice(nt):
        lw = _n(nt, "ShaderNodeLayerWeight", -600, 400)
        lw.inputs["Blend"].default_value = 0.35
        body = ramp_of(nt, noise(nt, 2.5, 2.0), [(0.35, (0.0, 0.40, 1.0)), (0.65, (0.10, 0.66, 1.0))])
        frost = mnode(nt, "MULTIPLY", lw.outputs["Facing"], mnode(nt, "ADD", mnode(nt, "MULTIPLY", noise(nt, 30.0, 3.0, x=-600, y=700), 0.6), 0.4))
        return mix_col(nt, ramp_of(nt, frost, [(0.25, 0.0), (0.75, 0.9)], 0, 400), body, (0.88, 0.97, 1.0), 300, 0)
    skin = gloss("fk_FRZ_skin", ice, rough=0.12, coat=1.0, coat_rough=0.02, trans=0.12, ior=1.31, sss=0.5,
                 sss_rad=(0.3, 0.8, 1.0), sss_scale=0.12, glow=0.16, sat=1.2,
                 bump=lambda nt: noise(nt, 40.0, 3.0, x=200, y=-900), bump_str=0.1)
    inside = inside_mat("fk_FRZ_in", [(0.0, (0.80, 0.96, 1.0)), (0.5, (0.45, 0.82, 1.0)), (0.9, (0.15, 0.62, 1.0))], glow=0.22,
                        sss_rad=(0.5, 0.85, 1.0))
    spots = [(0, 0, 0.55), (-0.4, 0, 0.5), (0.4, 0, 0.5), (0, 0.34, 0.5), (0, -0.34, 0.5), (-0.21, 0.05, 0.1), (0.21, -0.05, 0.1),
             (0, 0.3, 0.12), (0, -0.3, 0.12), (-0.2, -0.15, -0.28), (0.2, 0.15, -0.28), (0, 0, -0.62), (-0.42, 0.18, 0.12), (0.42, -0.18, 0.12)]
    grapes = []
    for i, p in enumerate(spots):
        g = sphere(f"FRZ_{i}", (0.34, 0.34, 0.37), 40, 28)
        place(g, p)
        add_mat(g, skin)
        add_mat(g, inside)
        grapes.append(g)
    st = stem("FRZ_stem", 0.055, 0.04, 0.5, bend=0.1)
    place(st, (0, 0, 0.75), (0, 15, 0))
    add_mat(st, stem_mat("fk_FRZ_stem", base=(0.55, 0.62, 0.70), tip=(0.85, 0.92, 1.0)))
    add_mat(st, inside)
    return join(grapes + [st], "FRZ")


def build_JM():
    """Gold Melon: a watermelon in polished gold - bright and deep gold stripes; golden glowing flesh inside."""
    body = sphere("JM", (1.18, 0.98, 0.98))
    add_mat(body, gloss("fk_JM_skin", lambda nt: melon_stripes(nt, (1.0, 0.70, 0.14), (0.55, 0.20, 0.0), mottle=0.0),
                        metal=0.72, rough=0.24, coat=0.8, coat_rough=0.03, glow=0.08, sat=1.15))

    def inside(nt):
        r, _ = radius_xz(nt, -900, 0)
        base = ramp_of(nt, r, [(0.0, (1.0, 0.30, 0.0)), (0.62, (1.0, 0.42, 0.0)), (0.80, (1.0, 0.62, 0.08)),
                               (0.85, (1.0, 0.97, 0.80)), (0.90, (1.0, 0.80, 0.30)), (0.93, (0.75, 0.42, 0.05))], -300, 0)
        return seeds(nt, base, (0.10, 0.04, 0.01), scale=7.0, size=0.15, inner=0.3, outer=0.72, stretch=(1, 1, 1.6))
    add_mat(body, inside_gloss("fk_JM_in", inside, glow=0.15, sss_rad=(1.0, 0.5, 0.1), val=0.9))
    return body


FRUIT.update({"H2": build_H2, "H3": build_H3, "H4": build_H4, "L1": build_L1, "L2": build_L2, "L3": build_L3,
              "L4": build_L4, "SC": build_SC, "BOMB": build_BOMB, "PW2": build_PW2, "PW3": build_PW3,
              "PW5": build_PW5, "FRZ": build_FRZ, "JM": build_JM})
NO_HALF.update({"BOMB"})

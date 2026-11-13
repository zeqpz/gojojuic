# Fruit builders 2..15 for fruitkit.py (exec'd into the same namespace by fruitkit.py).
# Every builder returns ONE joined mesh object named after its ID, with material slot 0 = skin and
# slot 1 = inside (the material the cut face gets); extra slots after that are decorations.


# ---------------------------------------------------------------- shape helpers
def sph_deform(ob, fn):
    """fn(v, r, theta, phi) -> new vector; theta = polar angle from +Z, phi = azimuth."""
    for v in ob.data.vertices:
        c = Vector(v.co)
        r = c.length or 1e-6
        th = math.acos(max(-1.0, min(1.0, c.z / r)))
        ph = math.atan2(c.y, c.x)
        v.co = fn(c, r, th, ph)


def leaf(name, length=0.7, width=0.26, bend=0.25):
    """A pointed, slightly curled leaf along +Z from the origin."""
    ob = sphere(name, (width, width * 0.28, length / 2), 16, 12)

    def f(c, r, th, ph):
        t = (c.z / (length / 2) + 1) / 2                      # 0 base .. 1 tip
        taper = math.sin(math.pi * min(1.0, t * 0.95 + 0.05)) ** 0.8
        return Vector((c.x * taper, c.y * taper + bend * t * t, c.z + length / 2))
    sph_deform(ob, f)
    return ob


def cyl(name, r, h, verts=16):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=verts, radius1=r, radius2=r * 0.85, depth=h)
    bm.to_mesh(me)
    bm.free()
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


def mix_col(nt, fac, a, b, x=0, y=0):
    n = _n(nt, "ShaderNodeMix", x, y)
    n.data_type = "RGBA"
    for i, v in ((0, fac), (6, a), (7, b)):
        if isinstance(v, (int, float)):
            n.inputs[i].default_value = v
        elif isinstance(v, tuple):
            n.inputs[i].default_value = tuple(v) + (1,) if len(v) == 3 else v
        else:
            nt.links.new(v, n.inputs[i])
    return n.outputs[2]


def noise(nt, scale, detail=2.0, stretch=(1, 1, 1), x=-600, y=-300):
    co = coord(nt, x - 400, y)
    mp = _n(nt, "ShaderNodeVectorMath", x - 200, y)
    mp.operation = "MULTIPLY"
    mp.inputs[1].default_value = stretch
    nt.links.new(co, mp.inputs[0])
    n = _n(nt, "ShaderNodeTexNoise", x, y)
    n.inputs["Scale"].default_value = scale
    n.inputs["Detail"].default_value = detail
    nt.links.new(mp.outputs[0], n.inputs["Vector"])
    return n.outputs["Fac"]


def rgb(nt, c, x=-200, y=-700):
    n = _n(nt, "ShaderNodeRGB", x, y)
    n.outputs[0].default_value = tuple(c) + (1,)
    return n.outputs[0]


def dots(nt, base_rgb, dot_rgb, scale=18, size=0.15):
    co = coord(nt, -800, -500)
    v = _n(nt, "ShaderNodeTexVoronoi", -600, -500)
    v.inputs["Scale"].default_value = scale
    nt.links.new(co, v.inputs["Vector"])
    f = mnode(nt, "LESS_THAN", v.outputs["Distance"], size, -400, -500)
    return mix_col(nt, f, base_rgb, dot_rgb, -200, -500)


def citrus_inside(name, flesh, pith=(1.0, 0.98, 0.9), rind=(1.0, 0.55, 0.05), n_seg=10):
    def inside(nt):
        r, _ = radius_xz(nt, -900, 300)
        base = ramp_of(nt, r, [(0.0, pith), (0.07, flesh), (0.84, flesh), (0.86, pith), (0.92, rind)], -300, 300)
        a, _ = angle_about(nt, "X", -900, -100)
        s = mnode(nt, "ABSOLUTE", mnode(nt, "SINE", mnode(nt, "MULTIPLY", a, n_seg / 2, -500, -100), None, -350, -100), None, -200, -100)
        line = mnode(nt, "MULTIPLY", mnode(nt, "LESS_THAN", s, 0.07, -50, -100), mnode(nt, "LESS_THAN", r, 0.84, -50, -250), 100, -150)
        return mix_col(nt, line, base, pith, 300, 0)
    return toon(name, inside, shade=(0.75, 0.92, 1.0), spec=0.35, rim=0)


def inside_mat(name, stops, seed=None, glow=0.0):
    """Cut-face material: radial bands (radius 0 centre .. ~0.95 rim) plus optional seeds."""
    def inside(nt):
        r, _ = radius_xz(nt, -900, 0)
        base = ramp_of(nt, r, stops, -300, 0)
        if seed:
            return seeds(nt, base, seed[0], scale=seed[1], size=seed[2], inner=seed[3], outer=seed[4])
        return base
    return toon(name, inside, shade=(0.78, 0.94, 1.02), spec=0.35, rim=0, glow=glow)


LEAF_GREEN = (0.25, 0.62, 0.14)


def stem_leaf(prefix, top=0.95, leaf_len=0.55, stem_h=0.28, leaf_rot=(0, 62, 30)):
    st = cyl(prefix + "_stem", 0.05, stem_h)
    place(st, (0.0, 0, top + stem_h / 2 - 0.06), (0, 12, 0))
    add_mat(st, toon("fk_stem", flat((0.35, 0.22, 0.10))))
    lf = leaf(prefix + "_leaf", length=leaf_len, width=0.2, bend=0.15)
    place(lf, (0.02, 0, top), leaf_rot)
    add_mat(lf, toon("fk_leaf", flat(LEAF_GREEN)))
    return [st, lf]


# ---------------------------------------------------------------- fruit
def build_H2():
    body = sphere("H2", (0.74, 0.74, 0.92))
    sph_deform(body, lambda c, r, th, ph: c * (1 + 0.035 * abs(math.sin(ph * 8 + c.z * 9) * math.sin(ph * 8 - c.z * 9))))

    def skin(nt):
        a, sep = angle_about(nt, "Z")
        z = sep.outputs["Z"]
        u = mnode(nt, "SINE", mnode(nt, "ADD", mnode(nt, "MULTIPLY", a, 8), mnode(nt, "MULTIPLY", z, 9)))
        v = mnode(nt, "SINE", mnode(nt, "SUBTRACT", mnode(nt, "MULTIPLY", a, 8), mnode(nt, "MULTIPLY", z, 9)))
        d = mnode(nt, "ABSOLUTE", mnode(nt, "MULTIPLY", u, v))
        return ramp_of(nt, d, [(0.0, (0.45, 0.22, 0.05)), (0.08, (0.85, 0.52, 0.10)), (0.45, (1.0, 0.80, 0.22))], 450, 0)
    add_mat(body, toon("fk_H2_skin", skin))
    add_mat(body, inside_mat("fk_H2_in", [(0.0, (1.0, 0.96, 0.70)), (0.16, (1.0, 0.86, 0.30)), (0.84, (1.0, 0.80, 0.22)), (0.9, (0.70, 0.40, 0.08))]))
    green = toon("fk_leaf", flat(LEAF_GREEN))
    parts = []
    for i in range(12):
        lf = leaf(f"H2_l{i}", length=0.55 + 0.3 * (i % 3 == 0) + 0.12 * (i % 2), width=0.13, bend=0.16)
        place(lf, (0, 0, 0.8), (14 + 24 * (i % 3), 0, i * 30 + 11 * (i % 2)))
        add_mat(lf, green)
        parts.append(lf)
    ob = join([body] + parts, "H2")
    ob.data.transform(Matrix.Translation((0, 0, -0.22)))
    return ob


def build_H3():
    body = sphere("H3", (0.8, 0.8, 1.0))
    add_mat(body, toon("fk_H3_skin", lambda nt: ramp_of(nt, noise(nt, 1.6, 1.0), [(0.0, (0.90, 0.12, 0.48)), (0.5, (0.96, 0.22, 0.56)), (0.7, (1.0, 0.30, 0.62))], 0, 0, "LINEAR")))
    add_mat(body, inside_mat("fk_H3_in", [(0.0, (0.98, 0.97, 0.95)), (0.86, (0.97, 0.94, 0.95)), (0.9, (0.98, 0.32, 0.62))],
                             seed=((0.05, 0.04, 0.05), 16.0, 0.11, 0.02, 0.82)))
    pink = toon("fk_H3_scale", flat((0.98, 0.28, 0.6)))
    tip = toon("fk_H3_tip", flat((0.50, 0.82, 0.22)))
    parts = []
    rows = [(-0.6, 6, 0), (-0.15, 7, 25), (0.32, 6, 10), (0.72, 5, 40)]
    for zi, (z, n, off) in enumerate(rows):
        for i in range(n):
            ph = off + i * 360 / n
            rr = 0.8 * math.sqrt(max(0.05, 1 - z * z))
            lf = leaf(f"H3_s{zi}_{i}", length=0.46, width=0.16, bend=0.1)
            add_mat(lf, pink)
            add_mat(lf, tip)
            for p in lf.data.polygons:
                if p.center.z > 0.3:
                    p.material_index = 1
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
    body = sphere("H4", (1.0, 1.0, 0.94))
    sph_deform(body, lambda c, r, th, ph: c * (1 + 0.025 * math.sin(ph * 3)))
    add_mat(body, toon("fk_H4_skin", lambda nt: ramp_of(nt, noise(nt, 6.0, 6.0, (1, 1, 0.25)),
                                                         [(0.0, (0.30, 0.17, 0.08)), (0.45, (0.45, 0.27, 0.12)), (0.62, (0.62, 0.42, 0.22))], 0, 0, "LINEAR")))
    add_mat(body, inside_mat("fk_H4_in", [(0.0, (0.80, 0.90, 0.96)), (0.6, (0.86, 0.94, 0.98)), (0.64, (1.0, 1.0, 0.97)),
                                          (0.84, (0.98, 0.97, 0.92)), (0.87, (0.40, 0.24, 0.10))]))
    eye = toon("fk_H4_eye", flat((0.12, 0.07, 0.04)))
    parts = []
    for i in range(3):
        a = math.radians(90 + i * 120)
        e = sphere(f"H4_e{i}", (0.1, 0.1, 0.05), 12, 8)
        place(e, (0.22 * math.cos(a), 0.22 * math.sin(a), 0.9))
        add_mat(e, eye)
        parts.append(e)
    return join([body] + parts, "H4")


def build_L1():
    body = sphere("L1", (1, 1, 0.96))
    add_mat(body, toon("fk_L1_skin", lambda nt: dots(nt, rgb(nt, (1.0, 0.52, 0.04)), rgb(nt, (0.90, 0.40, 0.02), -200, -850), 22, 0.18)))
    add_mat(body, citrus_inside("fk_L1_in", (1.0, 0.62, 0.12)))
    return join([body] + stem_leaf("L1", top=0.93), "L1")


def build_L2():
    body = sphere("L2", (1, 1, 0.9))

    def f(c, r, th, ph):
        d2 = c.x * c.x + c.y * c.y
        z = c.z - 0.32 * math.exp(-d2 / 0.06) * (1 if c.z > 0 else 0.5)
        k = 1 + 0.08 * max(0.0, c.z)
        return Vector((c.x * k, c.y * k, z))
    sph_deform(body, f)
    add_mat(body, toon("fk_L2_skin", lambda nt: ramp_of(nt, noise(nt, 1.4, 1.0, (3, 3, 0.4)),
                                                         [(0.0, (0.80, 0.04, 0.07)), (0.55, (0.90, 0.08, 0.10)), (0.75, (0.98, 0.36, 0.16))], 0, 0, "LINEAR")))
    add_mat(body, inside_mat("fk_L2_in", [(0.0, (0.98, 0.92, 0.72)), (0.2, (1.0, 0.97, 0.82)), (0.9, (1.0, 0.96, 0.80)), (0.93, (0.85, 0.06, 0.08))],
                             seed=((0.30, 0.15, 0.05), 5.0, 0.12, 0.08, 0.26)))
    return join([body] + stem_leaf("L2", top=0.6, leaf_rot=(0, 70, 40)), "L2")


def build_L3():
    body = sphere("L3", (0.74, 0.74, 1.0))

    def f(c, r, th, ph):
        t = abs(c.z)
        k = 1 - 0.2 * t ** 3
        z = c.z * (1 + (0.18 * (t - 0.85) / 0.15 if t > 0.85 else 0))
        return Vector((c.x * k, c.y * k, z))
    sph_deform(body, f)
    add_mat(body, toon("fk_L3_skin", lambda nt: dots(nt, rgb(nt, (1.0, 0.86, 0.08)), rgb(nt, (0.92, 0.74, 0.04), -200, -850), 24, 0.17)))
    add_mat(body, citrus_inside("fk_L3_in", (1.0, 0.95, 0.45), rind=(1.0, 0.85, 0.08), n_seg=9))
    body.data.transform(Matrix.Rotation(math.radians(70), 4, "Y"))
    return body


def build_L4():
    body = sphere("L4", (0.82, 0.82, 1.0))
    add_mat(body, toon("fk_L4_skin", lambda nt: ramp_of(nt, noise(nt, 14.0, 6.0),
                                                         [(0.0, (0.38, 0.25, 0.12)), (0.5, (0.52, 0.36, 0.18)), (0.65, (0.62, 0.48, 0.28))], 0, 0, "LINEAR")))
    add_mat(body, inside_mat("fk_L4_in", [(0.0, (0.98, 1.0, 0.85)), (0.18, (0.78, 0.92, 0.42)), (0.24, (0.42, 0.78, 0.10)),
                                          (0.85, (0.36, 0.72, 0.08)), (0.9, (0.45, 0.32, 0.15))],
                             seed=((0.05, 0.05, 0.03), 14.0, 0.14, 0.2, 0.36)))
    body.data.transform(Matrix.Rotation(math.radians(60), 4, "Y"))
    return body


def build_SC():
    """Star fruit: a rounded 5-point star prism along X, so the cut shows the star."""
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
    bm.to_mesh(me)
    bm.free()
    ob = tag(bpy.data.objects.new("SC", me))
    bpy.context.scene.collection.objects.link(ob)
    for p in me.polygons:
        p.use_smooth = True
    add_mat(ob, toon("fk_SC_skin", flat((1.0, 0.80, 0.10)), shade=(0.55, 0.85, 1.1), spec=0.8, rim=0.6, glow=0.25))
    add_mat(ob, inside_mat("fk_SC_in", [(0.0, (1.0, 0.98, 0.75)), (0.15, (1.0, 0.9, 0.35)), (0.75, (1.0, 0.86, 0.25))],
                           seed=((0.45, 0.30, 0.05), 6.0, 0.12, 0.12, 0.3), glow=0.2))
    return ob


def build_BOMB():
    body = sphere("BOMB", (1, 1, 1))
    add_mat(body, toon("fk_BOMB_skin", flat((0.16, 0.17, 0.24)), shade=(0.45, 0.9, 1.45), spec=0.85, rim=0.5))
    add_mat(body, toon("fk_BOMB_skin", flat((0.13, 0.14, 0.20))))
    cap = cyl("BOMB_cap", 0.32, 0.26, 24)
    place(cap, (0, 0, 0.98))
    add_mat(cap, toon("fk_metal", flat((0.62, 0.62, 0.66)), spec=0.9, rim=0.3))
    fuse = []
    pts = [Vector((0.0, 0, 1.0)), Vector((0.05, 0, 1.3)), Vector((0.2, 0, 1.5)), Vector((0.42, 0, 1.6)), Vector((0.6, 0, 1.58))]
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        seg = cyl(f"BOMB_f{i}", 0.085, (b - a).length + 0.08, 12)
        d = (b - a).normalized()
        q = Vector((0, 0, 1)).rotation_difference(d)
        seg.data.transform(Matrix.Translation((a + b) / 2) @ q.to_matrix().to_4x4())
        add_mat(seg, toon("fk_fuse", flat((0.80, 0.68, 0.45))))
        fuse.append(seg)
    spark = sphere("BOMB_spark", (0.2, 0.2, 0.2), 16, 12)
    sph_deform(spark, lambda c, r, th, ph: c * (1 + 1.1 * max(0.0, math.sin(ph * 4) * math.sin(th * 4)) ** 2))
    place(spark, (0.66, 0, 1.6))
    add_mat(spark, toon("fk_spark", flat((1.0, 0.75, 0.2)), shade=(1, 1, 1), spec=0, rim=0, glow=2.0))
    ob = join([body, cap, spark] + fuse, "BOMB")
    ob.data.transform(Matrix.Translation((0, 0, -0.25)))
    return ob


def _zgrad(nt):
    """0 at the bottom-right .. 1 at the top-left of the object: a soft blush across the fruit."""
    co = coord(nt, -900, 200)
    dp = _n(nt, "ShaderNodeVectorMath", -700, 200)
    dp.operation = "DOT_PRODUCT"
    dp.inputs[1].default_value = (-0.45, 0.0, 0.9)
    nt.links.new(co, dp.inputs[0])
    return mnode(nt, "MULTIPLY_ADD", dp.outputs["Value"], 0.5, -500, 200) if False else mnode(nt, "ADD", mnode(nt, "MULTIPLY", dp.outputs["Value"], 0.5, -550, 200), 0.5, -400, 200)


def build_peach(ID, skin_a, skin_b, flesh):
    body = sphere(ID, (1, 1, 0.97))

    def f(c, r, th, ph):
        ang = math.atan2(c.x, c.y)                            # 0 on the +Y meridian (the cleft)
        cleft = 0.08 * math.exp(-(ang * ang) / 0.02) * math.sin(th)
        return c * (1 - cleft)
    sph_deform(body, f)
    add_mat(body, toon(f"fk_{ID}_skin", lambda nt: ramp_of(nt, _zgrad(nt), [(0.0, skin_a), (0.45, skin_a), (0.85, skin_b)], 0, 0, "LINEAR"),
                       shade=(0.5, 0.85, 1.12), spec=0.7, rim=0.6, glow=0.35))
    add_mat(body, inside_mat(f"fk_{ID}_in", [(0.0, (0.45, 0.22, 0.10)), (0.3, (0.55, 0.30, 0.12)), (0.33, flesh), (0.88, flesh), (0.93, skin_a)], glow=0.2))
    ob = join([body] + stem_leaf(ID, top=0.9, leaf_rot=(0, 55, -20)), ID)
    ob.data.transform(Matrix.Rotation(math.radians(-35), 4, "Z"))
    return ob


def build_PW2():
    return build_peach("PW2", (0.10, 0.38, 1.0), (0.45, 0.85, 1.0), (0.78, 0.92, 1.0))


def build_PW3():
    return build_peach("PW3", (0.50, 0.10, 0.95), (0.88, 0.50, 1.0), (0.95, 0.82, 1.0))


def build_PW5():
    return build_peach("PW5", (0.95, 0.10, 0.12), (1.0, 0.78, 0.15), (1.0, 0.88, 0.62))


def build_FRZ():
    skin = toon("fk_FRZ_skin", lambda nt: ramp_of(nt, noise(nt, 9.0, 4.0), [(0.0, (0.35, 0.72, 1.0)), (0.55, (0.62, 0.88, 1.0)), (0.66, (0.96, 0.99, 1.0))], 0, 0, "LINEAR"),
                shade=(0.55, 0.88, 1.12), spec=0.9, rim=0.6, glow=0.2)
    inside = inside_mat("fk_FRZ_in", [(0.0, (0.88, 0.97, 1.0)), (0.5, (0.70, 0.90, 1.0)), (0.9, (0.55, 0.85, 1.0))], glow=0.2)
    spots = [(0, 0, 0.55), (-0.4, 0, 0.5), (0.4, 0, 0.5), (0, 0.34, 0.5), (0, -0.34, 0.5), (-0.21, 0.05, 0.1), (0.21, -0.05, 0.1),
             (0, 0.3, 0.12), (0, -0.3, 0.12), (-0.2, -0.15, -0.28), (0.2, 0.15, -0.28), (0, 0, -0.62), (-0.42, 0.18, 0.12), (0.42, -0.18, 0.12)]
    grapes = []
    for i, p in enumerate(spots):
        g = sphere(f"FRZ_{i}", (0.34, 0.34, 0.37), 24, 16)
        place(g, p)
        add_mat(g, skin)
        add_mat(g, inside)
        grapes.append(g)
    st = cyl("FRZ_stem", 0.05, 0.45)
    place(st, (0, 0, 0.98), (0, 15, 0))
    add_mat(st, toon("fk_stem", flat((0.35, 0.22, 0.10))))
    add_mat(st, inside)
    return join(grapes + [st], "FRZ")


def build_JM():
    body = sphere("JM", (1.18, 0.98, 0.98))

    def skin(nt):
        a, _ = angle_about(nt, "X")
        w = mnode(nt, "SINE", mnode(nt, "ADD", mnode(nt, "MULTIPLY", a, 7.0), mnode(nt, "MULTIPLY", noise(nt, 3.0), 5.0)))
        return ramp_of(nt, w, [(0.0, (0.78, 0.48, 0.05)), (0.45, (1.0, 0.86, 0.30))], 0, 0)
    add_mat(body, toon("fk_JM_skin", skin, shade=(0.5, 0.85, 1.15), spec=0.95, rim=0.7, glow=0.35))
    add_mat(body, mat_watermelon_in())
    return body


FRUIT.update({"H2": build_H2, "H3": build_H3, "H4": build_H4, "L1": build_L1, "L2": build_L2, "L3": build_L3,
              "L4": build_L4, "SC": build_SC, "BOMB": build_BOMB, "PW2": build_PW2, "PW3": build_PW3,
              "PW5": build_PW5, "FRZ": build_FRZ, "JM": build_JM})
NO_HALF.update({"BOMB"})

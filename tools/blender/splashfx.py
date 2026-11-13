"""Juice Dojo splash FX: a metaball juice burst, rendered as a short transparent frame sequence.

    blender -b --factory-startup --python tools/blender/splashfx.py -- [variants=3] [frames=18]

Every droplet is its own metaball object in one family, so drops that are close melt together into a liquid sheet
and pull apart into beads as they fly - real-looking juice without a fluid sim. A fat core blob at the cut splits
into a fan of droplets (more of them flung sideways, along the blade) that fly out under gravity, stretch along their
flight (ellipsoid elements turned to their velocity) and shrink as they thin out. Shaded as glossy liquid in
greyscale, so the game tints each burst to its fruit's juice and keeps the gloss.
Writes art/blender/splash/burst<V>_<NN>.png (pack with tools/pack_splash.py).
"""
import math
import os
import random
import sys

import bpy
from mathutils import Vector, Euler

try:
    ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
except NameError:
    ROOT = os.path.join(os.path.expanduser("~"), "Documents", "juicedojo")
OUT = os.path.join(ROOT, "art", "blender", "splash")
RES = 384
FPS = 30


def scene():
    sc = bpy.context.scene
    sc.name = "Splash"
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            sc.render.engine = eng
            break
        except TypeError:
            pass
    sc.render.resolution_x = sc.render.resolution_y = RES
    sc.render.film_transparent = True
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.view_settings.view_transform = "Standard"
    sc.render.fps = FPS
    try:
        sc.eevee.taa_render_samples = 24
    except AttributeError:
        pass
    sc.world = sc.world or bpy.data.worlds.new("SplashWorld")
    sc.world.use_nodes = True
    bg = next(n for n in sc.world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (.55, .55, .58, 1)
    bg.inputs[1].default_value = .8
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
    sc.collection.objects.link(cam)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 5.2
    cam.location = (0, -10, .1)
    cam.rotation_euler = (math.radians(90), 0, 0)
    sc.camera = cam
    for name, rot, energy in (("Key", (50, -35, -30), 5.0), ("Rim", (-60, 40, 160), 3.0)):
        L = bpy.data.objects.new(name, bpy.data.lights.new(name, "SUN"))
        L.data.energy = energy
        L.data.angle = math.radians(4)
        L.rotation_euler = [math.radians(a) for a in rot]
        sc.collection.objects.link(L)
    return sc


def liquid_mat():
    m = bpy.data.materials.new("Juice")
    m.use_nodes = True
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (.86, .86, .86, 1)
    bsdf.inputs["Roughness"].default_value = .06
    for nm in ("Specular IOR Level", "Specular"):
        if nm in bsdf.inputs:
            bsdf.inputs[nm].default_value = .8
    if "Coat Weight" in bsdf.inputs:
        bsdf.inputs["Coat Weight"].default_value = .6
    return m


def burst(seed, frames):
    rng = random.Random(seed)
    sc = bpy.context.scene
    mat = liquid_mat()
    mb = bpy.data.metaballs.new("Juice")
    mb.resolution = .09
    mb.render_resolution = .07         # a 384 px sprite: finer meshing only costs time
    mb.threshold = .55
    mb.materials.append(mat)
    drops = []

    def add(r, kind="ELLIPSOID"):
        data = mb if not drops else bpy.data.metaballs.new("Juice")
        if drops:
            data.resolution, data.render_resolution, data.threshold = mb.resolution, mb.render_resolution, mb.threshold
            data.materials.append(mat)
        e = data.elements.new(type=kind)
        e.radius = r
        ob = bpy.data.objects.new("Juice" if not drops else f"Juice.{len(drops):03d}", data)
        sc.collection.objects.link(ob)
        drops.append(ob)
        return ob

    G = 6.5
    core = add(1.05, "BALL")
    parts = []
    n = 34
    n = 26
    for i in range(n):
        # a fan of droplets: most flung along the blade (sideways), the rest every way, a little up
        side = rng.random() < .6
        a = (rng.choice([0, math.pi]) + rng.gauss(0, .45)) if side else rng.uniform(0, 2 * math.pi)
        sp = rng.uniform(2.4, 6.2) if side else rng.uniform(1.4, 4.2)
        v = Vector((math.cos(a) * sp, 0, math.sin(a) * sp * .8 + rng.uniform(.4, 2.2)))
        r0 = rng.uniform(.28, .62) * (1.25 if sp < 3 else 1)
        delay = rng.uniform(0, .05)
        parts.append((add(r0, "BALL"), v, r0, delay))
    T = frames / FPS
    for f in range(frames):
        t = f / FPS
        sc.frame_set(f + 1)
        k = t / T
        core.scale = [max(.001, (1 - k * 1.25)) * (1 + .35 * math.sin(k * 9) * (1 - k))] * 3
        core.keyframe_insert("scale", frame=f + 1)
        for ob, v, r0, delay in parts:
            tt = max(0, t - delay)
            p = Vector((v.x * tt, 0, v.z * tt - .5 * G * tt * tt))
            vel = Vector((v.x, 0, v.z - G * tt))
            ob.location = p
            # stretched along its flight, thinning as it goes
            stretch = 1 + min(1.8, vel.length / 4.0)
            thin = max(.42, (1 - tt / (T * 1.4))) ** .5
            ob.rotation_euler = Euler((0, -math.atan2(vel.z, vel.x), 0))
            ob.scale = (stretch * thin, thin, thin / (stretch ** .35))
            ob.keyframe_insert("location", frame=f + 1)
            ob.keyframe_insert("rotation_euler", frame=f + 1)
            ob.keyframe_insert("scale", frame=f + 1)
    sc.frame_start, sc.frame_end = 1, frames


def render(v, frames):
    sc = bpy.context.scene
    os.makedirs(OUT, exist_ok=True)
    for f in range(frames):
        sc.frame_set(f + 1)
        sc.render.filepath = os.path.join(OUT, f"burst{v}_{f:02d}.png")
        bpy.ops.render.render(write_still=True)
    print("rendered burst", v)


if __name__ == "__main__" and "--" in sys.argv:
    args = sys.argv[sys.argv.index("--") + 1:]
    variants = int(args[0]) if args else 3
    frames = int(args[1]) if len(args) > 1 else 18
    for v in range(1, variants + 1):
        scene()
        burst(1000 + v * 17, frames)
        render(v, frames)

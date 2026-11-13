"""Juice Dojo bomb explosion: a volumetric fireball rendered as a short transparent frame sequence.

    blender -b --factory-startup --python tools/blender/explosion.py -- [frames=22]

No simulation: a sphere of volume whose density is 4D noise (animated through W, so it boils) shaped by a soft
round falloff. It blows out fast (eased scale), burns white-yellow at the core and orange-red at the edges, then
cools - the emission dies away - into dark rolling smoke that thins out. Writes art/blender/explosion/boom_<NN>.png
(pack with tools/pack_splash.py).
"""
import math
import os
import sys

import bpy

try:
    ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
except NameError:
    ROOT = os.path.join(os.path.expanduser("~"), "Documents", "juicedojo")
OUT = os.path.join(ROOT, "art", "blender", "explosion")
RES = 384


def N(nt, kind, x=0, y=0, **ins):
    n = nt.nodes.new(kind)
    n.location = (x, y)
    for k, v in ins.items():
        n.inputs[k].default_value = v
    return n


def build(frames):
    sc = bpy.context.scene
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
    sc.view_settings.view_transform = "Standard"   # saturated fire (AgX washes it to beige)
    ee = sc.eevee
    for attr, val in (("taa_render_samples", 32), ("volumetric_tile_size", "4"), ("volumetric_samples", 96),
                      ("volumetric_start", 1.0), ("volumetric_end", 30.0), ("use_volumetric_shadows", True)):
        try:
            setattr(ee, attr, val)
        except (AttributeError, TypeError):
            pass
    sc.world = sc.world or bpy.data.worlds.new("W")
    sc.world.use_nodes = True
    bg = next(n for n in sc.world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (.3, .3, .32, 1)
    bg.inputs[1].default_value = .25
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
    sc.collection.objects.link(cam)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 6.4
    cam.location = (0, -12, 0)
    cam.rotation_euler = (math.radians(90), 0, 0)
    sc.camera = cam
    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN"))
    sun.data.energy = 3
    sun.rotation_euler = (math.radians(45), math.radians(-30), 0)
    sc.collection.objects.link(sun)

    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=4, radius=1)
    ball = bpy.context.active_object
    ball.name = "Fireball"
    m = bpy.data.materials.new("Fire")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = N(nt, "ShaderNodeOutputMaterial", 900, 0)
    vol = N(nt, "ShaderNodeVolumePrincipled", 650, 0)
    nt.links.new(vol.outputs[0], out.inputs["Volume"])
    tc = N(nt, "ShaderNodeTexCoord", -900, 0)
    noise = N(nt, "ShaderNodeTexNoise", -600, 100)
    noise.noise_dimensions = "4D"
    noise.inputs["Scale"].default_value = 2.3
    noise.inputs["Detail"].default_value = 6.0
    noise.inputs["Roughness"].default_value = .6
    nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
    # the field: a round falloff pushed in and out by the noise, so the edge billows in lobes instead of a ball
    ln = N(nt, "ShaderNodeVectorMath", -600, -200)
    ln.operation = "LENGTH"
    nt.links.new(tc.outputs["Object"], ln.inputs[0])
    inv = N(nt, "ShaderNodeMath", -420, -200)
    inv.operation = "MULTIPLY_ADD"                # (1 - r) * 1.6  ==  r * -1.6 + 1.6
    inv.inputs[1].default_value, inv.inputs[2].default_value = -1.6, 1.6
    nt.links.new(ln.outputs["Value"], inv.inputs[0])
    bil = N(nt, "ShaderNodeMath", -420, 100)
    bil.operation = "MULTIPLY_ADD"                # (n - .5) * 1.5  ==  n * 1.5 - .75
    bil.inputs[1].default_value, bil.inputs[2].default_value = 1.5, -.75
    nt.links.new(noise.outputs["Fac"], bil.inputs[0])
    field = N(nt, "ShaderNodeMath", -220, 0)
    field.operation = "ADD"
    nt.links.new(inv.outputs[0], field.inputs[0])
    nt.links.new(bil.outputs[0], field.inputs[1])
    shape = field
    dens_ramp = N(nt, "ShaderNodeValToRGB", 50, 200)
    dens_ramp.color_ramp.interpolation = "EASE"
    dens_ramp.color_ramp.elements[0].position = .0
    dens_ramp.color_ramp.elements[0].color = (0, 0, 0, 1)
    dens_ramp.color_ramp.elements[1].position = .45
    dens_ramp.color_ramp.elements[1].color = (1, 1, 1, 1)
    nt.links.new(shape.outputs[0], dens_ramp.inputs[0])
    dmul = N(nt, "ShaderNodeMath", 300, 200)
    dmul.operation = "MULTIPLY"
    nt.links.new(dens_ramp.outputs[0], dmul.inputs[0])
    dmul.inputs[1].default_value = 14.0          # density scale (animated: thins as it ends)
    nt.links.new(dmul.outputs[0], vol.inputs["Density"])
    # fire colour from the field: deep red at the wispy edge, orange, yellow, white-hot in the core
    fire = N(nt, "ShaderNodeValToRGB", 50, -150)
    cr = fire.color_ramp
    cr.elements[0].position, cr.elements[0].color = .05, (.25, .015, 0, 1)
    cr.elements[1].position, cr.elements[1].color = 1.0, (1, 1, .92, 1)
    e = cr.elements.new(.3); e.color = (1, .22, .02, 1)
    e = cr.elements.new(.55); e.color = (1, .55, .08, 1)
    e = cr.elements.new(.78); e.color = (1, .85, .35, 1)
    nt.links.new(shape.outputs[0], fire.inputs[0])
    nt.links.new(fire.outputs[0], vol.inputs["Emission Color"])
    emul = N(nt, "ShaderNodeMath", 300, -150)
    emul.operation = "MULTIPLY"
    hot = N(nt, "ShaderNodeMath", 150, -300)
    hot.operation = "POWER"                       # the core burns far hotter than the edge
    hot.inputs[1].default_value = 2.2
    nt.links.new(shape.outputs[0], hot.inputs[0])
    nt.links.new(hot.outputs[0], emul.inputs[0])
    emul.inputs[1].default_value = 90.0          # emission strength (animated: the fire cools)
    nt.links.new(emul.outputs[0], vol.inputs["Emission Strength"])
    vol.inputs["Color"].default_value = (.2, .19, .18, 1)   # the smoke left behind: near black
    vol.inputs["Anisotropy"].default_value = .2
    ball.data.materials.append(m)
    import random
    rng = random.Random(7)
    lobes = []
    for i in range(5):
        a = rng.uniform(0, 2 * math.pi)
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=1)
        lb = bpy.context.active_object
        lb.data.materials.append(m)
        lb.parent = ball
        r = rng.uniform(.5, .72)
        lb.location = (math.cos(a) * .55, rng.uniform(-.2, .2), math.sin(a) * .5 + .1)
        lb.scale = (r, r, r)
        lobes.append(lb)

    for f in range(frames):
        k = f / (frames - 1)
        fr = f + 1
        s = .35 + 2.0 * (1 - (1 - k) ** 3)                  # blows out fast, then drifts
        ball.scale = (s, s, s)
        ball.location = (0, 0, .5 * k * k)                  # the smoke rises a little
        ball.keyframe_insert("scale", frame=fr)
        ball.keyframe_insert("location", frame=fr)
        noise.inputs["W"].default_value = k * 1.8
        noise.inputs["W"].keyframe_insert("default_value", frame=fr)
        emul.inputs[1].default_value = 600 * max(0, 1 - k / .6) ** 1.3
        emul.inputs[1].keyframe_insert("default_value", frame=fr)
        # thin while it burns (so the fire glows through), thickest as it turns to smoke, then thinning away
        dmul.inputs[1].default_value = (4 + 9 * min(1, k / .45)) * (1 - max(0, (k - .5) / .5)) ** 1.6 + .01
        dmul.inputs[1].keyframe_insert("default_value", frame=fr)
    sc.frame_start, sc.frame_end = 1, frames


def render(frames):
    sc = bpy.context.scene
    os.makedirs(OUT, exist_ok=True)
    for f in range(frames):
        sc.frame_set(f + 1)
        sc.render.filepath = os.path.join(OUT, f"boom_{f:02d}.png")
        bpy.ops.render.render(write_still=True)
    print("rendered explosion")


if __name__ == "__main__" and "--" in sys.argv:
    args = sys.argv[sys.argv.index("--") + 1:]
    frames = int(args[0]) if args else 22
    build(frames)
    render(frames)

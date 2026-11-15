"""Process the Sketchfab scene.gltf packages in frontend/raw_downloads/ into stage-ready GLBs.

Per slot: import -> drop importer helpers -> flatten hierarchy + apply transforms ->
strip baked pose clips -> decimate (>25k tris) -> centre/ground/scale/face -Y ->
rig if static (humanoid armature + automatic weights) -> bake a seamless 4 s `Idle`
(arms relaxed, breathing, sway, head micro-turn; pelvis/root untouched = zero drift) -> export raw GLB.

Compression (resize to <=1024, KTX2, quantize, meshopt) runs afterwards via gltf-transform.

Usage (Blender's Python, e.g. `pip install bpy==5.1.2`):
  python3 process_raw.py <raw_dir> <out_dir> [slot ...] [--probe]
"""
import json
import math
import os
import re
import sys

import bpy
import numpy as np
from mathutils import Euler, Matrix, Vector

FPS = 30
NFR = 120  # 4.0 s loop; frame 0 == frame 120

# Joint positions (metres, after normalisation; character faces -Y, its left is +X)
# for the two static meshes, read off normalised ortho renders.
STATIC_RIGS = {
    '02_smash': None,     # filled below
    '03_fortnite': None,
}

CFG = {
    '01_cs2': dict(height=1.84, rig=dict(
        spine=['spine_0_68', 'spine_1_67', 'spine_2_66', 'spine_3_61'], neck='neck_0_3', head='head_0_0',
        clav=('clavicle_l_31', 'clavicle_r_59'), upper=('arm_upper_l_30', 'arm_upper_r_58'),
        fore=('arm_lower_l_27', 'arm_lower_r_55')), arm_down=20, elbow=10),
    '02_smash': dict(height=1.65, rig=None, arm_down=62, elbow=12),
    '03_fortnite': dict(height=1.84, rig=None, arm_down=6, elbow=8),
    '04_fifa': dict(height=1.84, rig=dict(
        spine=['Spine1_5', 'Spine2_6', 'Spine3_7', 'Spine4_10'], neck='Neck_11', head='Head_12',
        clav=('L_Clavicle_144', 'R_Clavicle_179'), upper=('L_Shoulder_145', 'R_Shoulder_180'),
        fore=('L_Elbow_146', 'R_Elbow_181')), arm_down=4, elbow=6),
    '05_halo': dict(height=1.84, rig=dict(
        spine=['ValveBiped.Bip01_Spine_01', 'ValveBiped.Bip01_Spine1_02', 'ValveBiped.Bip01_Spine2_03',
               'ValveBiped.Bip01_Spine4_04'],
        neck='ValveBiped.Bip01_Neck1_05', head='ValveBiped.Bip01_Head1_06',
        clav=('ValveBiped.Bip01_L_Clavicle_012', 'ValveBiped.Bip01_R_Clavicle_07'),
        upper=('ValveBiped.Bip01_L_UpperArm_013', 'ValveBiped.Bip01_R_UpperArm_08'),
        fore=('ValveBiped.Bip01_L_Forearm_014', 'ValveBiped.Bip01_R_Forearm_09')), arm_down=22, elbow=10),
}

TRI_LIMIT = 25000
TRI_TARGET = 20000


# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------

def meshes():
    return [o for o in bpy.context.scene.objects if o.type == 'MESH']


def tri_count():
    return sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in meshes())


def world_bounds():
    dg = bpy.context.evaluated_depsgraph_get()
    lo = np.full(3, np.inf)
    hi = np.full(3, -np.inf)
    for ob in meshes():
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        co = np.empty(len(me.vertices) * 3, np.float32)
        me.vertices.foreach_get('co', co)
        co = co.reshape(-1, 3)
        M = np.array(ob.matrix_world)
        w = co @ M[:3, :3].T + M[:3, 3]
        lo = np.minimum(lo, w.min(0))
        hi = np.maximum(hi, w.max(0))
        ev.to_mesh_clear()
    return lo, hi


def select_only(objs, active=None):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = active or (objs[0] if objs else None)


def import_clean(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.fps = FPS
    sc.frame_start, sc.frame_end = 0, NFR
    bpy.ops.import_scene.gltf(filepath=path)
    arm = next((o for o in sc.objects if o.type == 'ARMATURE'), None)
    # importer's bone-display helper
    for o in list(sc.objects):
        if o.type == 'MESH' and o.name.startswith('Icosphere') and not o.vertex_groups:
            bpy.data.objects.remove(o, do_unlink=True)
    # Make the pose shown on import the new bind pose. Sketchfab rigs often have a
    # rest pose that differs from the skinned bind (unit-scaled FBX/Source exports),
    # so: bake the current deformation into the meshes, apply the pose as rest,
    # then re-attach the armature modifier below.
    if arm:
        sc.frame_set(0)
        for m in [o for o in sc.objects if o.type == 'MESH']:
            for mod in list(m.modifiers):
                if mod.type == 'ARMATURE':
                    if m.data.shape_keys:
                        select_only([m])
                        bpy.ops.object.shape_key_remove(all=True)
                    select_only([m])
                    bpy.ops.object.modifier_apply(modifier=mod.name)
        select_only([arm])
        bpy.ops.object.mode_set(mode='POSE')
        bpy.ops.pose.select_all(action='SELECT')
        bpy.ops.pose.armature_apply(selected=False)
        bpy.ops.object.mode_set(mode='OBJECT')
    # drop all imported clips / poses -> bind pose
    if arm:
        arm.animation_data_clear()
        for pb in arm.pose.bones:
            pb.location = (0, 0, 0)
            pb.rotation_quaternion = (1, 0, 0, 0)
            pb.rotation_euler = (0, 0, 0)
            pb.scale = (1, 1, 1)
    for o in sc.objects:
        o.animation_data_clear()
    for a in list(bpy.data.actions):
        bpy.data.actions.remove(a)
    # flatten hierarchy, keep world transforms
    keep = [o for o in sc.objects if o.type in ('MESH', 'ARMATURE')]
    mw = {o.name: o.matrix_world.copy() for o in keep}
    for o in keep:
        o.parent = None
        o.matrix_world = mw[o.name]
    for o in list(sc.objects):
        if o.type not in ('MESH', 'ARMATURE'):
            bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    select_only(keep, arm or keep[0])
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    if arm:
        for m in [o for o in sc.objects if o.type == 'MESH' and o.vertex_groups]:
            mod = m.modifiers.new('Armature', 'ARMATURE')
            mod.object = arm
    return arm


def decimate_if_needed():
    total = tri_count()
    if total <= TRI_LIMIT:
        return total, total
    ratio = TRI_TARGET / total
    for ob in meshes():
        if ob.data.shape_keys:
            select_only([ob])
            bpy.ops.object.shape_key_remove(all=True)
        mod = ob.modifiers.new('Decimate', 'DECIMATE')
        mod.decimate_type = 'COLLAPSE'
        mod.ratio = ratio
        mod.use_collapse_triangulate = True
        select_only([ob])
        bpy.ops.object.modifier_move_to_index(modifier=mod.name, index=0)
        bpy.ops.object.modifier_apply(modifier=mod.name)
    return total, tri_count()


def normalise(height, arm):
    lo, hi = world_bounds()
    s = height / (hi[2] - lo[2])
    cx, cy = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2
    M = Matrix.Scale(s, 4) @ Matrix.Translation((-cx, -cy, -lo[2]))
    objs = meshes() + ([arm] if arm else [])
    for o in objs:
        o.matrix_world = M @ o.matrix_world
    bpy.context.view_layer.update()
    select_only(objs, arm or objs[0])
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return s


# ----------------------------------------------------------------------------
# static-mesh rig
# ----------------------------------------------------------------------------

PARENT = {
    'hips': 'root', 'spine': 'hips', 'chest': 'spine', 'neck': 'chest', 'head': 'neck',
    'shoulder.L': 'chest', 'upperarm.L': 'shoulder.L', 'forearm.L': 'upperarm.L', 'hand.L': 'forearm.L',
    'shoulder.R': 'chest', 'upperarm.R': 'shoulder.R', 'forearm.R': 'upperarm.R', 'hand.R': 'forearm.R',
    'thigh.L': 'hips', 'shin.L': 'thigh.L', 'foot.L': 'shin.L',
    'thigh.R': 'hips', 'shin.R': 'thigh.R', 'foot.R': 'shin.R',
}


def fill_unweighted(arm):
    """Bone-heat can fail on non-manifold parts: give every unweighted vertex to its nearest bone."""
    segs = [(b.name, Vector(b.head_local), Vector(b.tail_local)) for b in arm.data.bones if b.use_deform]

    def nearest(p):
        best, bd = None, 1e9
        for n, h, t in segs:
            d = t - h
            u = max(0.0, min(1.0, (p - h).dot(d) / max(d.length_squared, 1e-9)))
            dist = (h + d * u - p).length
            if dist < bd:
                best, bd = n, dist
        return best

    fixed = 0
    for m in meshes():
        if not any(md.type == 'ARMATURE' for md in m.modifiers):
            md = m.modifiers.new('Armature', 'ARMATURE')
            md.object = arm
        if m.parent != arm:
            mw = m.matrix_world.copy()
            m.parent = arm
            m.matrix_world = mw
        groups = {g.index: g.name for g in m.vertex_groups}
        for v in m.data.vertices:
            if sum(g.weight for g in v.groups if g.group in groups and g.weight > 0) > 1e-4:
                continue
            n = nearest(m.matrix_world @ v.co)
            vg = m.vertex_groups.get(n) or m.vertex_groups.new(name=n)
            vg.add([v.index], 1.0, 'REPLACE')
            fixed += 1
    print('fill_unweighted: assigned', fixed, 'vertices')


def build_rig(j):
    """j: joint dict in metres (left side; right is mirrored)."""
    J = {}
    J['hips'] = ((0, j['hip_y'], j['hip_z']), (0, j['hip_y'], j['spine_z']))
    J['spine'] = ((0, j['hip_y'], j['spine_z']), (0, j['chest_y'], j['chest_z']))
    J['chest'] = ((0, j['chest_y'], j['chest_z']), (0, j['neck_y'], j['neck_z']))
    J['neck'] = ((0, j['neck_y'], j['neck_z']), (0, j['head_y'], j['head_z']))
    J['head'] = ((0, j['head_y'], j['head_z']), (0, j['head_y'], j['top_z']))
    for s, sx in (('L', 1), ('R', -1)):
        def m(p):
            return (sx * p[0], p[1], p[2])
        J[f'shoulder.{s}'] = (m((0.03, j['neck_y'], j['sh'][2])), m(j['sh']))
        J[f'upperarm.{s}'] = (m(j['sh']), m(j['el']))
        J[f'forearm.{s}'] = (m(j['el']), m(j['wr']))
        J[f'hand.{s}'] = (m(j['wr']), m(j['hd']))
        J[f'thigh.{s}'] = (m(j['hp']), m(j['kn']))
        J[f'shin.{s}'] = (m(j['kn']), m(j['an']))
        J[f'foot.{s}'] = (m(j['an']), m(j['to']))
    ad = bpy.data.armatures.new('Rig')
    arm = bpy.data.objects.new('Rig', ad)
    bpy.context.scene.collection.objects.link(arm)
    select_only([arm])
    bpy.ops.object.mode_set(mode='EDIT')
    eb = ad.edit_bones
    r = eb.new('root')
    r.head, r.tail = (0, 0, 0), (0, 0.15, 0)
    for n in ['hips', 'spine', 'chest', 'neck', 'head', 'shoulder.L', 'upperarm.L', 'forearm.L', 'hand.L',
              'shoulder.R', 'upperarm.R', 'forearm.R', 'hand.R', 'thigh.L', 'shin.L', 'foot.L',
              'thigh.R', 'shin.R', 'foot.R']:
        b = eb.new(n)
        b.head, b.tail = Vector(J[n][0]), Vector(J[n][1])
        b.parent = eb[PARENT[n]]
        if n.startswith(('upperarm', 'forearm', 'hand', 'shin', 'foot', 'spine', 'chest', 'neck', 'head')):
            b.use_connect = (b.head - b.parent.tail).length < 1e-4
        b.align_roll(Vector((0, -1, 0)) if not n.startswith(('shoulder', 'foot')) else Vector((0, 0, 1)))
    eb['root'].use_deform = False
    bpy.ops.object.mode_set(mode='OBJECT')
    ms = meshes()
    select_only(ms + [arm], arm)
    try:
        bpy.ops.object.parent_set(type='ARMATURE_AUTO')
    except RuntimeError as e:
        print('auto weights failed, using envelopes:', e)
        bpy.ops.object.parent_set(type='ARMATURE_ENVELOPE')
    fill_unweighted(arm)
    names = {'spine': ['spine', 'chest'], 'neck': 'neck', 'head': 'head', 'clav': ('shoulder.L', 'shoulder.R'),
             'upper': ('upperarm.L', 'upperarm.R'), 'fore': ('forearm.L', 'forearm.R')}
    return arm, names


# ----------------------------------------------------------------------------
# Idle
# ----------------------------------------------------------------------------

def wrot(pb, rx=0.0, ry=0.0, rz=0.0):
    """Rotation about world axes (deg) in the bone's rest frame: rx pitch fwd, ry roll toward +X, rz yaw toward +X."""
    R = pb.bone.matrix_local.to_3x3()
    Rw = Euler((math.radians(rx), math.radians(ry), math.radians(rz)), 'XYZ').to_matrix()
    return (R.inverted() @ Rw @ R).to_quaternion()


def bake_idle(arm, names, arm_down, elbow):
    pbs = arm.pose.bones
    arm.animation_data_create()
    act = bpy.data.actions.new('Idle')
    arm.animation_data.action = act
    for pb in pbs:
        pb.rotation_mode = 'QUATERNION'
    spine = [pbs[n] for n in names['spine']]
    neck, head = pbs[names['neck']], pbs[names['head']]
    side = lambda pb: 1.0 if (arm.matrix_world @ pb.bone.head_local).x > 0 else -1.0
    TAU = 2 * math.pi
    for f in range(0, NFR + 1, 2):
        t = (f % NFR) / NFR
        br = math.sin(TAU * t)                # one breath per loop
        sw = math.sin(TAU * t + 0.6)          # weight-shift sway
        hd = math.sin(TAU * t + 2.0)          # head micro-turn
        n = len(spine)
        for pb in spine:
            pb.rotation_quaternion = wrot(pb, rx=-1.3 * br / n * 2, ry=0.7 * sw / n * 2)
            pb.keyframe_insert('rotation_quaternion', frame=f)
        neck.rotation_quaternion = wrot(neck, rx=0.6 * br, rz=1.2 * hd)
        neck.keyframe_insert('rotation_quaternion', frame=f)
        head.rotation_quaternion = wrot(head, rx=0.8 * br + 0.8 * math.sin(2 * TAU * t), ry=-0.6 * sw, rz=2.2 * hd)
        head.keyframe_insert('rotation_quaternion', frame=f)
        for c in names['clav']:
            pb = pbs[c]
            sx = side(pb)
            pb.rotation_quaternion = wrot(pb, ry=sx * -1.4 * (br + 1) / 2)  # shrug up on inhale
            pb.keyframe_insert('rotation_quaternion', frame=f)
        for u in names['upper']:
            pb = pbs[u]
            sx = side(pb)
            pb.rotation_quaternion = wrot(pb, rx=-1.5 * sw * sx, ry=sx * (arm_down + 1.2 * br))
            pb.keyframe_insert('rotation_quaternion', frame=f)
        for fo in names['fore']:
            pb = pbs[fo]
            sx = side(pb)
            pb.rotation_quaternion = wrot(pb, rx=-(elbow + 1.5 * math.sin(TAU * t + 1.0 + sx)))
            pb.keyframe_insert('rotation_quaternion', frame=f)
    return act


def posed_extent(frames=range(0, NFR + 1, 10)):
    out = []
    for f in frames:
        bpy.context.scene.frame_set(f)
        out.append(world_bounds())
    bpy.context.scene.frame_set(0)
    return out


def export(arm, path):
    select_only(meshes() + [arm], arm)
    bpy.context.scene.frame_set(0)
    bpy.ops.export_scene.gltf(
        filepath=path, export_format='GLB', use_selection=True, export_yup=True,
        export_animations=True, export_animation_mode='ACTIONS', export_force_sampling=True,
        export_optimize_animation_size=True, export_frame_range=False, export_anim_single_armature=True,
        export_skins=True, export_def_bones=False, export_morph=False, export_materials='EXPORT',
        export_image_format='AUTO', export_cameras=False, export_lights=False, export_apply=False,
    )


def ortho_grid(path, lo, hi, res=800):
    """Front ortho render with a 5 cm grid overlay for picking joint positions."""
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.display.shading.color_type = 'TEXTURE'
    cd = bpy.data.cameras.new('c')
    cd.type = 'ORTHO'
    size = 2.0
    cd.ortho_scale = size
    cam = bpy.data.objects.new('c', cd)
    sc.collection.objects.link(cam)
    cam.location = (0, -10, 1.0)
    cam.rotation_euler = (math.radians(90), 0, 0)
    sc.camera = cam
    sc.render.resolution_x = sc.render.resolution_y = res
    sc.render.film_transparent = False
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    cam.location = (10, 0, 1.0)
    cam.rotation_euler = (math.radians(90), 0, math.radians(90))
    sc.render.filepath = path.replace('.png', '_side.png')
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam)


def preview(path):
    """Front + three-quarter workbench renders at frame 0 and 60 (sanity check of rig + Idle)."""
    from PIL import Image  # noqa
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.display.shading.color_type = 'TEXTURE'
    sc.render.resolution_x, sc.render.resolution_y = 360, 520
    cd = bpy.data.cameras.new('c')
    cd.lens = 50
    cam = bpy.data.objects.new('c', cd)
    sc.collection.objects.link(cam)
    sc.camera = cam
    shots = []
    for i, (loc, f) in enumerate((((0, -4.6, 1.0), 0), ((-3.0, -3.5, 1.1), 60))):
        sc.frame_set(f)
        cam.location = loc
        cam.rotation_euler = (Vector((0, 0, 0.92)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
        p = path.replace('.png', f'_{i}.png')
        sc.render.filepath = p
        bpy.ops.render.render(write_still=True)
        shots.append(p)
    bpy.data.objects.remove(cam)
    sc.frame_set(0)
    ims = [Image.open(p) for p in shots]
    m = Image.new('RGB', (sum(i.width for i in ims), ims[0].height))
    x = 0
    for im in ims:
        m.paste(im, (x, 0))
        x += im.width
    m.save(path)


def process(slot, raw_dir, out_dir, probe=False):
    cfg = CFG[slot]
    arm = import_clean(os.path.join(raw_dir, slot, 'scene.gltf'))
    t0, t1 = decimate_if_needed()
    s = normalise(cfg['height'], arm)
    info = dict(slot=slot, tris_in=int(t0), tris_out=int(t1), scale=round(float(s), 6))
    if probe:
        lo, hi = world_bounds()
        ortho_grid(os.path.join(out_dir, f'{slot}_grid.png'), lo, hi)
        print('PROBE', json.dumps(info))
        return info
    if arm is None:
        arm, names = build_rig(STATIC_RIGS[slot])
    else:
        names = cfg['rig']
        for m in meshes():
            m.parent = arm
            m.matrix_parent_inverse.identity()
    bake_idle(arm, names, cfg['arm_down'], cfg['elbow'])
    ext = posed_extent()
    info.update(
        bones=len(arm.data.bones),
        posed_height=[round(float(min(e[1][2] for e in ext)), 3), round(float(max(e[1][2] for e in ext)), 3)],
        ground=round(float(min(e[0][2] for e in ext)), 4),
        materials=len({m.name for o in meshes() for m in o.data.materials if m}),
    )
    preview(os.path.join(out_dir, f'{slot}_pose.png'))
    export(arm, os.path.join(out_dir, f'{slot}.raw.glb'))
    info['raw_bytes'] = os.path.getsize(os.path.join(out_dir, f'{slot}.raw.glb'))
    print('INFO', json.dumps(info))
    return info


# Joint tables for the static meshes (metres, normalised space, left side).
STATIC_RIGS['02_smash'] = None
STATIC_RIGS['03_fortnite'] = None
try:
    from static_rigs import RIGS  # noqa: E402
    STATIC_RIGS.update(RIGS)
except ImportError:
    pass

if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    raw_dir, out_dir, slots = args[0], args[1], args[2:] or list(CFG)
    os.makedirs(out_dir, exist_ok=True)
    for slot in slots:
        process(slot, raw_dir, out_dir, probe='--probe' in sys.argv)

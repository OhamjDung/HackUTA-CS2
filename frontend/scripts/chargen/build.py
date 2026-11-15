import json
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, '/home/claude/gen')
import core  # noqa: E402
from chars import CHARS, std_pose  # noqa: E402

OUT = '/home/claude/build'
TARGET_H = 1.85


def fcurves(action):
    try:
        from bpy_extras import anim_utils
        for slot in action.slots:
            cb = anim_utils.action_get_channelbag_for_slot(action, slot)
            if cb:
                yield from cb.fcurves
    except Exception:
        yield from action.fcurves


def rescale(arm, mesh, s):
    mesh.data.transform(Matrix.Scale(s, 4))
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='EDIT')
    for b in arm.data.edit_bones:
        b.head *= s
        b.tail *= s
    bpy.ops.object.mode_set(mode='OBJECT')
    for fc in fcurves(arm.animation_data.action):
        if fc.data_path.endswith('.location'):
            for k in fc.keyframe_points:
                k.co.y *= s
                k.handle_left.y *= s
                k.handle_right.y *= s
            fc.update()


def build(cid, render=True, views=('front', 'side')):
    fname, fn = CHARS[cid]
    os.makedirs(OUT, exist_ok=True)
    core.reset_scene()
    pal, p, J, B, rig, P = fn()
    mat = pal.material(OUT, cid)
    mesh = B.to_object(f'{cid}_body', mat)
    arm = core.build_armature(J, rig)
    bpy.ops.object.mode_set(mode='OBJECT')
    mesh.parent = arm
    mod = mesh.modifiers.new('Armature', 'ARMATURE')
    mod.object = arm
    arm.animation_data_create()
    core.animate(arm, std_pose(P))
    core.bake(arm)
    bounds = core.posed_bounds(mesh, frames=range(0, core.NFR + 1, 10))
    hmax = max(b[1][2] for b in bounds)
    s = TARGET_H / hmax
    rescale(arm, mesh, s)
    bounds = core.posed_bounds(mesh, frames=range(0, core.NFR + 1, 5))
    info = dict(
        id=cid, file=fname, tris=B.tri_count(), scale_applied=round(float(s), 4),
        height_min=round(float(min(b[1][2] for b in bounds)), 4), height_max=round(float(max(b[1][2] for b in bounds)), 4),
        ground_min=round(float(min(b[0][2] for b in bounds)), 4),
        bones=len([b for b in arm.data.bones if b.use_deform]),
        actions=[a.name for a in bpy.data.actions],
    )
    # export
    bpy.ops.object.select_all(action='DESELECT')
    arm.select_set(True)
    mesh.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.context.scene.frame_set(0)
    path = os.path.join(OUT, f'{fname}.raw.glb')
    bpy.ops.export_scene.gltf(
        filepath=path, export_format='GLB', use_selection=True, export_yup=True,
        export_animations=True, export_animation_mode='ACTIONS', export_def_bones=True,
        export_force_sampling=True, export_frame_range=False, export_anim_single_armature=True,
        export_skins=True, export_morph=False, export_materials='EXPORT', export_image_format='AUTO',
        export_tangents=False, export_cameras=False, export_lights=False, export_apply=False,
    )
    info['raw_bytes'] = os.path.getsize(path)
    if render:
        for v in views:
            if v == 'front':
                core.preview(os.path.join(OUT, f'{cid}_front.png'), frame=0)
            elif v == 'side':
                core.preview(os.path.join(OUT, f'{cid}_side.png'), frame=60, cam_loc=(-3.2, -2.4, 1.5))
            elif v == 'cf':
                core.preview(os.path.join(OUT, f'{cid}_cf.png'), frame=0, cam_loc=(0, -2.6, 1.3), res=520)
            elif v == 'c3':
                core.preview(os.path.join(OUT, f'{cid}_c3.png'), frame=0, cam_loc=(-1.9, -1.9, 1.3), res=520)
            elif v == 'cs':
                core.preview(os.path.join(OUT, f'{cid}_cs.png'), frame=0, cam_loc=(-2.7, 0.0, 1.2), res=520)
            elif v == 'back':
                core.preview(os.path.join(OUT, f'{cid}_back.png'), frame=30, cam_loc=(2.0, 3.4, 1.6))
    print('INFO', json.dumps(info))
    return info


if __name__ == '__main__':
    ids = sys.argv[1:] or list(CHARS)
    render = True
    views = ('front', 'side')
    if '--close' in ids:
        ids.remove('--close')
        views = ('cf', 'c3', 'cs')
    if '--norender' in ids:
        ids.remove('--norender')
        render = False
    for cid in ids:
        build(cid, render=render, views=views)

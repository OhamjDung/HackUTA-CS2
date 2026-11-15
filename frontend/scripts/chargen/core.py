"""Procedural rigged-character core for Blender (bpy 5.x).

Conventions (Blender space): Z up, character faces -Y (exports to glTF +Z forward),
character's left side is +X. All rest-pose coordinates are in metres.
"""
import math
import os

import bmesh
import bpy
import numpy as np
from mathutils import Euler, Matrix, Quaternion, Vector

FPS = 30
NFR = 120  # 4 s seamless loop (frame 0 == frame NFR)
GRID = 8   # palette cells per side
CELL = 32  # px per cell -> 256x256 textures

# ----------------------------------------------------------------------------
# Scene
# ----------------------------------------------------------------------------

def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.fps = FPS
    sc.frame_start = 0
    sc.frame_end = NFR


# ----------------------------------------------------------------------------
# Palette material (1 material: BaseColor + ORM + Emissive textures)
# ----------------------------------------------------------------------------

def hex_rgb(h):
    h = h.lstrip('#')
    return [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]


class Palette:
    def __init__(self, entries):
        # entries: name -> (hex, roughness, metallic, emission 0..1)
        self.names = list(entries.keys())
        self.entries = entries
        assert len(self.names) <= GRID * GRID

    def uv(self, name):
        i = self.names.index(name)
        cx, cy = i % GRID, i // GRID
        return ((cx + 0.5) / GRID, (cy + 0.5) / GRID)

    def build_images(self, outdir, tag):
        n = GRID * CELL
        base = np.zeros((n, n, 4), np.float32)
        orm = np.zeros((n, n, 4), np.float32)
        emi = np.zeros((n, n, 4), np.float32)
        base[..., 3] = orm[..., 3] = emi[..., 3] = 1.0
        orm[..., 0] = 1.0
        orm[..., 1] = 0.8
        for i, name in enumerate(self.names):
            hx, rough, metal, em = self.entries[name]
            cx, cy = i % GRID, i // GRID
            sl = (slice(cy * CELL, (cy + 1) * CELL), slice(cx * CELL, (cx + 1) * CELL))
            rgb = hex_rgb(hx)
            base[sl[0], sl[1], :3] = rgb
            orm[sl[0], sl[1], 1] = rough
            orm[sl[0], sl[1], 2] = metal
            emi[sl[0], sl[1], :3] = [c * em for c in rgb]
        imgs = {}
        for key, arr, cs in (('base', base, 'sRGB'), ('orm', orm, 'Non-Color'), ('emissive', emi, 'sRGB')):
            img = bpy.data.images.new(f'{tag}_{key}', n, n, alpha=False)
            img.colorspace_settings.name = cs
            img.pixels.foreach_set(arr.ravel())
            path = os.path.join(outdir, f'{tag}_{key}.png')
            img.filepath_raw = path
            img.file_format = 'PNG'
            img.save()
            imgs[key] = img
        return imgs

    def material(self, outdir, tag):
        imgs = self.build_images(outdir, tag)
        mat = bpy.data.materials.new(f'{tag}_mat')
        mat.use_nodes = True
        nt = mat.node_tree
        nt.nodes.clear()
        out = nt.nodes.new('ShaderNodeOutputMaterial')
        bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
        nt.links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
        t_base = nt.nodes.new('ShaderNodeTexImage'); t_base.image = imgs['base']
        t_orm = nt.nodes.new('ShaderNodeTexImage'); t_orm.image = imgs['orm']
        t_emi = nt.nodes.new('ShaderNodeTexImage'); t_emi.image = imgs['emissive']
        for t in (t_base, t_orm, t_emi):
            t.interpolation = 'Closest'
        sep = nt.nodes.new('ShaderNodeSeparateColor')
        nt.links.new(t_base.outputs['Color'], bsdf.inputs['Base Color'])
        nt.links.new(t_orm.outputs['Color'], sep.inputs['Color'])
        nt.links.new(sep.outputs['Green'], bsdf.inputs['Roughness'])
        nt.links.new(sep.outputs['Blue'], bsdf.inputs['Metallic'])
        nt.links.new(t_emi.outputs['Color'], bsdf.inputs['Emission Color'])
        bsdf.inputs['Emission Strength'].default_value = 1.0
        return mat


# ----------------------------------------------------------------------------
# Mesh builder: parts -> one skinned mesh with rigid / two-bone-blended weights
# ----------------------------------------------------------------------------

def _mat_from(loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1)):
    r = Euler([math.radians(a) for a in rot], 'XYZ').to_matrix().to_4x4()
    s = Matrix.Diagonal((*scale, 1.0))
    return Matrix.Translation(Vector(loc)) @ r @ s


class Builder:
    def __init__(self, palette):
        self.pal = palette
        self.verts = []
        self.faces = []   # (vert indices, uv, smooth)
        self.weights = []  # per vertex: dict bone -> w

    # -- low level ------------------------------------------------------------
    def _add_bm(self, bm, M, bone, col, smooth, blend=None):
        """blend: (parent_bone, predicate(local_co)->bool, w_parent)."""
        base = len(self.verts)
        uv = self.pal.uv(col)
        for v in bm.verts:
            w = {bone: 1.0}
            if blend and blend[1](v.co):
                w = {bone: 1.0 - blend[2], blend[0]: blend[2]}
            self.verts.append(M @ v.co)
            self.weights.append(w)
        for f in bm.faces:
            self.faces.append(([base + v.index for v in f.verts], uv, smooth))
        bm.free()

    @staticmethod
    def _bevel(bm, amt, segs):
        if amt <= 0:
            return
        bmesh.ops.bevel(bm, geom=list(bm.edges) + list(bm.verts), offset=amt,
                        segments=segs, affect='EDGES', profile=0.5, clamp_overlap=True)

    # -- primitives -----------------------------------------------------------
    def box(self, center, size, bone, col, rot=(0, 0, 0), bevel=0.0, segs=1,
            smooth=False, taper=None):
        """taper: (sx_top, sy_top) multipliers applied to +Z face verts."""
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        if taper:
            for v in bm.verts:
                if v.co.z > 0:
                    v.co.x *= taper[0]
                    v.co.y *= taper[1]
        for v in bm.verts:
            v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
        self._bevel(bm, bevel, segs)
        bm.verts.index_update()
        self._add_bm(bm, _mat_from(center, rot), bone, col, smooth)

    def ellipsoid(self, center, radii, bone, col, rot=(0, 0, 0), seg=(16, 10),
                  smooth=True, cut_below=None):
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=seg[0], v_segments=seg[1], radius=1.0)
        if cut_below is not None:  # delete verts with local z < cut_below (hemisphere)
            bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < cut_below - 1e-4],
                             context='VERTS')
            edges = [e for e in bm.edges if e.is_boundary]
            if edges:
                bmesh.ops.edgeloop_fill(bm, edges=edges)
        for v in bm.verts:
            v.co = Vector((v.co.x * radii[0], v.co.y * radii[1], v.co.z * radii[2]))
        bm.verts.index_update()
        self._add_bm(bm, _mat_from(center, rot), bone, col, smooth)

    def cyl(self, p1, p2, r1, r2, bone, col, seg=12, smooth=True, blend=None,
            sides_scale=(1.0, 1.0)):
        """Tapered cylinder p1->p2. blend=(parent_bone, w) blends the p1 ring."""
        p1, p2 = Vector(p1), Vector(p2)
        d = p2 - p1
        L = d.length
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg,
                              radius1=r1, radius2=r2, depth=L)
        for v in bm.verts:
            v.co.x *= sides_scale[0]
            v.co.y *= sides_scale[1]
        bm.verts.index_update()
        q = Vector((0, 0, 1)).rotation_difference(d.normalized())
        M = Matrix.Translation((p1 + p2) / 2) @ q.to_matrix().to_4x4()
        bl = None
        if blend:
            bl = (blend[0], lambda co: co.z < 0, blend[1])
        self._add_bm(bm, M, bone, col, smooth, bl)

    def ico(self, center, r, bone, col, subdiv=2, smooth=False, colfn=None):
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=r)
        bm.verts.index_update()
        if colfn is None:
            self._add_bm(bm, Matrix.Translation(Vector(center)), bone, col, smooth)
            return
        base = len(self.verts)
        for v in bm.verts:
            self.verts.append(Vector(center) + v.co)
            self.weights.append({bone: 1.0})
        for f in bm.faces:
            c = f.calc_center_median().normalized()
            self.faces.append(([base + v.index for v in f.verts], self.pal.uv(colfn(c)), smooth))
        bm.free()

    def prism(self, center, radius, depth, bone, col, sides=6, rot=(0, 0, 0), smooth=False):
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=sides,
                              radius1=radius, radius2=radius, depth=depth)
        bm.verts.index_update()
        self._add_bm(bm, _mat_from(center, rot), bone, col, smooth)

    def custom(self, verts, faces, bone, col, M=None, smooth=False):
        bm = bmesh.new()
        vs = [bm.verts.new(v) for v in verts]
        for f in faces:
            bm.faces.new([vs[i] for i in f])
        bm.verts.index_update()
        self._add_bm(bm, M or Matrix.Identity(4), bone, col, smooth)

    # -- finalize -------------------------------------------------------------
    def to_object(self, name, mat):
        me = bpy.data.meshes.new(name)
        me.from_pydata([tuple(v) for v in self.verts], [], [f[0] for f in self.faces])
        me.update()
        uvl = me.uv_layers.new(name='UVMap')
        for poly, (_, uv, smooth) in zip(me.polygons, self.faces):
            poly.use_smooth = smooth
            for li in poly.loop_indices:
                uvl.data[li].uv = uv
        me.materials.append(mat)
        ob = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(ob)
        groups = {}
        for vi, w in enumerate(self.weights):
            for b, wt in w.items():
                if b not in groups:
                    groups[b] = ob.vertex_groups.new(name=b)
                groups[b].add([vi], wt, 'REPLACE')
        return ob

    def tri_count(self):
        return sum(len(f[0]) - 2 for f in self.faces)


# ----------------------------------------------------------------------------
# Skeleton
# ----------------------------------------------------------------------------

BASE_PROPS = dict(
    ankle_z=0.085, knee_z=0.50, hipj_z=0.92, hip_z=0.97, spine_z=1.10, chest_z=1.24,
    neck_z=1.47, head_z=1.57, head_h=0.25, sh_z=1.43, sh_x=0.20, el_z=1.14, wr_z=0.87,
    hand_l=0.16, hip_x=0.095, foot_l=0.17,
)


def joints(p):
    J = {}
    J['hips'] = (Vector((0, 0, p['hip_z'])), Vector((0, 0, p['spine_z'])))
    J['spine'] = (Vector((0, 0, p['spine_z'])), Vector((0, 0, p['chest_z'])))
    J['chest'] = (Vector((0, 0, p['chest_z'])), Vector((0, 0, p['neck_z'])))
    J['neck'] = (Vector((0, 0, p['neck_z'])), Vector((0, 0, p['head_z'])))
    J['head'] = (Vector((0, 0, p['head_z'])), Vector((0, 0, p['head_z'] + p['head_h'])))
    for s, sx in (('L', 1), ('R', -1)):
        sh = Vector((sx * p['sh_x'], 0.0, p['sh_z']))
        el = Vector((sx * (p['sh_x'] + 0.025), 0.035, p['el_z']))
        wr = Vector((sx * (p['sh_x'] + 0.045), 0.0, p['wr_z']))
        hd = Vector((sx * (p['sh_x'] + 0.05), -0.005, p['wr_z'] - p['hand_l']))
        J[f'shoulder.{s}'] = (Vector((sx * 0.05, 0.0, p['sh_z'])), sh)
        J[f'upperarm.{s}'] = (sh, el)
        J[f'forearm.{s}'] = (el, wr)
        J[f'hand.{s}'] = (wr, hd)
        hj = Vector((sx * p['hip_x'], 0.0, p['hipj_z']))
        kn = Vector((sx * p['hip_x'], -0.035, p['knee_z']))
        an = Vector((sx * p['hip_x'], 0.0, p['ankle_z']))
        to = Vector((sx * p['hip_x'], -p['foot_l'], 0.03))
        J[f'thigh.{s}'] = (hj, kn)
        J[f'shin.{s}'] = (kn, an)
        J[f'foot.{s}'] = (an, to)
    return J


PARENT = {
    'hips': 'root', 'spine': 'hips', 'chest': 'spine', 'neck': 'chest', 'head': 'neck',
    'shoulder.L': 'chest', 'upperarm.L': 'shoulder.L', 'forearm.L': 'upperarm.L', 'hand.L': 'forearm.L',
    'shoulder.R': 'chest', 'upperarm.R': 'shoulder.R', 'forearm.R': 'upperarm.R', 'hand.R': 'forearm.R',
    'thigh.L': 'hips', 'shin.L': 'thigh.L', 'foot.L': 'shin.L',
    'thigh.R': 'hips', 'shin.R': 'thigh.R', 'foot.R': 'shin.R',
}


def _signed_angle(u, v, normal):
    a = u.angle(v)
    if u.cross(v).angle(normal) < 1:
        a = -a
    return a


def _pole_angle(base_head, base_tail, base_x, ik_tail, pole):
    pole_normal = (ik_tail - base_head).cross(pole - base_head)
    proj = pole_normal.cross(base_tail - base_head)
    return _signed_angle(base_x, proj, base_tail - base_head)


def build_armature(J, rig):
    """rig: dict with
        hand_targets: {'L': (pos, parent_bone), 'R': ...}
        elbow_poles:  {'L': (pos, parent), ...}
        knee_poles:   {'L': pos, ...}
        props: [(name, head, tail, parent)]  deforming prop bones
    """
    arm_data = bpy.data.armatures.new('Armature')
    arm = bpy.data.objects.new('Armature', arm_data)
    bpy.context.scene.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    eb = arm_data.edit_bones

    def nb(name, h, t, parent=None, deform=True, roll=0.0, connect=False):
        b = eb.new(name)
        b.head, b.tail = Vector(h), Vector(t)
        b.roll = roll
        b.use_deform = deform
        if parent:
            b.parent = eb[parent]
            b.use_connect = connect
        return b

    nb('root', (0, 0, 0), (0, 0.12, 0))
    order = ['hips', 'spine', 'chest', 'neck', 'head']
    for s in 'LR':
        order += [f'shoulder.{s}', f'upperarm.{s}', f'forearm.{s}', f'hand.{s}',
                  f'thigh.{s}', f'shin.{s}', f'foot.{s}']
    for n in order:
        h, t = J[n]
        nb(n, h, t, PARENT[n])
        if n.startswith(('upperarm', 'forearm', 'hand', 'shin', 'foot')):
            eb[n].use_connect = True
    # roll: limbs keep X axis pointing sideways for predictable IK
    for n in order:
        eb[n].align_roll(Vector((0, -1, 0)) if n.startswith(('thigh', 'shin', 'upperarm', 'forearm', 'hand'))
                         else Vector((0, -1, 0)) if n in ('hips', 'spine', 'chest', 'neck', 'head') else Vector((0, 0, 1)))
    for name, h, t, parent in rig.get('props', []):
        nb(name, h, t, parent)

    # control bones (non-deform)
    for s in 'LR':
        a, toe = J[f'foot.{s}']
        nb(f'ik_foot.{s}', a, toe, 'root', deform=False)
        eb[f'ik_foot.{s}'].roll = eb[f'foot.{s}'].roll
        kp = Vector(rig['knee_poles'][s])
        nb(f'pole_knee.{s}', kp, kp + Vector((0, -0.08, 0)), 'root', deform=False)
        if s in rig['hand_targets']:
            pos, par = rig['hand_targets'][s]
            pos = Vector(pos)
            w, hd = J[f'hand.{s}']
            nb(f'ik_hand.{s}', pos, pos + (hd - w), par, deform=False)
            ep, epar = rig['elbow_poles'][s]
            ep = Vector(ep)
            nb(f'pole_elbow.{s}', ep, ep + Vector((0, 0.08, 0)), epar, deform=False)

    # pole angles from rest geometry
    poles = {}
    for s in 'LR':
        th, sh = eb[f'thigh.{s}'], eb[f'shin.{s}']
        poles[f'knee.{s}'] = _pole_angle(th.head.copy(), th.tail.copy(), th.x_axis.copy(), sh.tail.copy(),
                                         eb[f'pole_knee.{s}'].head.copy())
        if s in rig['hand_targets']:
            ua, fa = eb[f'upperarm.{s}'], eb[f'forearm.{s}']
            poles[f'elbow.{s}'] = _pole_angle(ua.head.copy(), ua.tail.copy(), ua.x_axis.copy(), fa.tail.copy(),
                                              eb[f'pole_elbow.{s}'].head.copy())
    bpy.ops.object.mode_set(mode='POSE')

    pbs = arm.pose.bones
    for s in 'LR':
        c = pbs[f'shin.{s}'].constraints.new('IK')
        c.target, c.subtarget = arm, f'ik_foot.{s}'
        c.pole_target, c.pole_subtarget = arm, f'pole_knee.{s}'
        c.pole_angle = poles[f'knee.{s}']
        c.chain_count = 2
        c.use_stretch = False
        c2 = pbs[f'foot.{s}'].constraints.new('COPY_ROTATION')
        c2.target, c2.subtarget = arm, f'ik_foot.{s}'
        if s in rig['hand_targets']:
            c = pbs[f'forearm.{s}'].constraints.new('IK')
            c.target, c.subtarget = arm, f'ik_hand.{s}'
            c.pole_target, c.pole_subtarget = arm, f'pole_elbow.{s}'
            c.pole_angle = poles[f'elbow.{s}']
            c.chain_count = 2
            c.use_stretch = False
            if rig.get('hand_rot', {}).get(s) is not None:
                c3 = pbs[f'hand.{s}'].constraints.new('COPY_ROTATION')
                c3.target, c3.subtarget = arm, f'ik_hand.{s}'
    for pb in pbs:
        pb.rotation_mode = 'QUATERNION'
    return arm


# ----------------------------------------------------------------------------
# Posing helpers (world-axis rotations conjugated into bone-local space)
# ----------------------------------------------------------------------------

def world_rot_to_local(pb, rx=0.0, ry=0.0, rz=0.0):
    """Rotation about world axes (deg): rx=pitch forward, ry=lean to char-left(+X), rz=turn to char-left."""
    R = pb.bone.matrix_local.to_3x3()
    Rw = Euler((math.radians(rx), math.radians(ry), math.radians(rz)), 'XYZ').to_matrix()
    return (R.inverted() @ Rw @ R).to_quaternion()


def world_vec_to_local(pb, d):
    R = pb.bone.matrix_local.to_3x3()
    return R.inverted() @ Vector(d)


def animate(arm, pose_fn, step=2):
    """pose_fn(t in [0,1)) -> dict bone -> {'rot':(rx,ry,rz), 'loc':(dx,dy,dz)} in world axes."""
    pbs = arm.pose.bones
    keyed = set()
    for f in range(0, NFR + 1, step):
        t = (f % NFR) / NFR
        pose = pose_fn(t)
        for name, tr in pose.items():
            pb = pbs[name]
            if 'rot' in tr:
                pb.rotation_quaternion = world_rot_to_local(pb, *tr['rot'])
                pb.keyframe_insert('rotation_quaternion', frame=f)
            if 'loc' in tr:
                pb.location = world_vec_to_local(pb, tr['loc'])
                pb.keyframe_insert('location', frame=f)
            keyed.add(name)
    act = arm.animation_data.action
    act.name = 'Idle'
    calibrate_poles(arm)
    return act


def _perp(p, a, b):
    ab = (b - a).normalized()
    v = p - a
    return (v - ab * v.dot(ab)).normalized()


def calibrate_poles(arm, frame=0):
    """Pick each IK pole_angle so the knee/elbow bends toward its pole bone."""
    sc = bpy.context.scene
    sc.frame_set(frame)
    for pb in arm.pose.bones:
        for c in pb.constraints:
            if c.type != 'IK' or not c.pole_subtarget:
                continue

            def score(a):
                c.pole_angle = a
                bpy.context.view_layer.update()
                root = pb.parent.head.copy()
                mid = pb.head.copy()
                tip = pb.tail.copy()
                pole = arm.pose.bones[c.pole_subtarget].head.copy()
                return _perp(mid, root, tip).dot(_perp(pole, root, tip))

            best = max((math.radians(d) for d in range(-180, 180, 10)), key=score)
            best = max((best + math.radians(d) for d in range(-10, 11, 1)), key=score)
            c.pole_angle = best
    bpy.context.view_layer.update()


def bake(arm):
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.pose.select_all(action='SELECT')
    bpy.ops.nla.bake(frame_start=0, frame_end=NFR, step=1, only_selected=True,
                     visual_keying=True, clear_constraints=True, clear_parents=False,
                     use_current_action=True, bake_types={'POSE'})
    bpy.ops.object.mode_set(mode='OBJECT')
    act = arm.animation_data.action
    act.name = 'Idle'
    for a in list(bpy.data.actions):
        if a != act:
            bpy.data.actions.remove(a)
    return act


def posed_bounds(mesh_ob, frames=(0, 30, 60, 90)):
    dg = bpy.context.evaluated_depsgraph_get()
    out = []
    for f in frames:
        bpy.context.scene.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        ev = mesh_ob.evaluated_get(dg)
        me = ev.to_mesh()
        co = np.empty(len(me.vertices) * 3, np.float32)
        me.vertices.foreach_get('co', co)
        co = co.reshape(-1, 3)
        out.append((co.min(0), co.max(0)))
        ev.to_mesh_clear()
    bpy.context.scene.frame_set(0)
    return out


# ----------------------------------------------------------------------------
# Preview render (matches the frontend camera: three [0,1.5,4] -> blender (0,-4,1.5))
# ----------------------------------------------------------------------------

def preview(path, frame=0, cam_loc=(0, -4, 1.5), target=(0, 0, 0.95), res=420):
    sc = bpy.context.scene
    sc.frame_set(frame)
    cam_data = bpy.data.cameras.new('cam')
    cam_data.sensor_fit = 'VERTICAL'
    cam_data.angle = math.radians(45)
    cam = bpy.data.objects.new('cam', cam_data)
    sc.collection.objects.link(cam)
    cam.location = cam_loc
    d = Vector(target) - Vector(cam_loc)
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    sc.camera = cam
    if 'key' not in bpy.data.objects:
        for name, rot, energy, col in (('key', (50, 0, -30), 3.5, (1, 0.97, 0.92)),
                                       ('rim', (110, 0, 160), 4.0, (0.6, 0.8, 1.0)),
                                       ('fill', (70, 0, 60), 1.0, (1, 1, 1))):
            ld = bpy.data.lights.new(name, 'SUN')
            ld.energy = energy
            ld.color = col
            lo = bpy.data.objects.new(name, ld)
            lo.rotation_euler = [math.radians(a) for a in rot]
            sc.collection.objects.link(lo)
        world = bpy.data.worlds.new('w')
        world.use_nodes = True
        world.node_tree.nodes['Background'].inputs[0].default_value = (0.02, 0.02, 0.025, 1)
        world.node_tree.nodes['Background'].inputs[1].default_value = 0.4
        sc.world = world
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = 24
    sc.cycles.device = 'CPU'
    sc.render.resolution_x = res
    sc.render.resolution_y = int(res * 1.2)
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam)

"""Five original characters, each echoing its game slot's genre silhouette."""
import math
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, '/home/claude/gen')
import core  # noqa: E402
from core import Builder, Palette, BASE_PROPS, joints  # noqa: E402

TAU = 2 * math.pi
V = Vector


def S(t, n=1, ph=0.0):
    return math.sin(TAU * n * t + ph)


def frame_from_dir(d, up=(0, 0, 1)):
    x = V(d).normalized()
    z = V(up) - x * x.dot(V(up))
    z.normalize()
    y = z.cross(x)
    M = Matrix((x, y, z)).transposed()
    return M


def place(origin, d, up=(0, 0, 1)):
    return Matrix.Translation(V(origin)) @ frame_from_dir(d, up).to_4x4()


# ----------------------------------------------------------------------------
# Shared body
# ----------------------------------------------------------------------------

def body(B, J, p, c, o):
    """c: colour names; o: options."""
    hz = p['head_z']
    # torso
    B.box((0, 0.0, p['hipj_z'] + 0.035), (2 * p['hip_x'] + 0.15 * o.get('hip_w', 1), 0.215, 0.20),
          'hips', c['pants'], bevel=0.04, segs=2, smooth=True)
    B.box((0, 0.0, p['spine_z'] + 0.02), (o.get('waist_w', 0.29), 0.195, 0.16),
          'spine', c['top'], bevel=0.04, segs=2, smooth=True)
    cw = o.get('chest_w', 0.37)
    B.box((0, 0.0, (p['chest_z'] + p['neck_z']) / 2 - 0.005), (cw, o.get('chest_d', 0.225), p['neck_z'] - p['chest_z'] + 0.05),
          'chest', c['top'], bevel=0.05, segs=2, smooth=True, taper=(1.0 + o.get('chest_taper', 0.0), 1.0))
    # neck/head
    B.cyl((0, 0, p['neck_z'] - 0.04), (0, 0, hz + 0.05), 0.056 * o.get('neck_r', 1), 0.05 * o.get('neck_r', 1),
          'neck', c.get('neck', c['skin']), seg=12, blend=('chest', 0.5))
    if not o.get('no_head'):
        hs = o.get('head_s', 1.0)
        hc = V((0, -0.01, hz + 0.115 * hs))
        B.ellipsoid(hc, (0.092 * hs, 0.104 * hs, 0.12 * hs), 'head', c['skin'], seg=(18, 12))
        if not o.get('no_face'):
            for sx in (1, -1):
                B.ellipsoid(hc + V((sx * 0.036 * hs, -0.094 * hs, 0.012 * hs)), (0.014 * hs, 0.008, 0.017 * hs),
                            'head', 'eye', seg=(8, 6))
                B.box(hc + V((sx * 0.037 * hs, -0.096 * hs, 0.042 * hs)), (0.034 * hs, 0.012, 0.010),
                      'head', c.get('brow', c.get('hair', 'eye')), rot=(0, -sx * 8, 0))
                B.ellipsoid(hc + V((sx * 0.091 * hs, 0.0, 0.0)), (0.014, 0.024, 0.03), 'head', c['skin'], seg=(8, 6))
            B.box(hc + V((0, -0.104 * hs, -0.01 * hs)), (0.022, 0.03, 0.04), 'head', c['skin'],
                  bevel=0.008, smooth=True, taper=(0.6, 0.4))
            B.box(hc + V((0, -0.09 * hs, -0.058 * hs)), (0.036 * hs, 0.01, 0.007), 'head', 'mouth')
    lr = o.get('limb_r', 1.0)
    for s, sx in (('L', 1), ('R', -1)):
        sh, el = J[f'upperarm.{s}']
        wr = J[f'forearm.{s}'][1]
        B.ellipsoid(sh, (0.075 * lr, 0.075 * lr, 0.075 * lr), f'upperarm.{s}', c['sleeve'], seg=(12, 8))
        B.cyl(sh, el, 0.056 * lr, 0.048 * lr, f'upperarm.{s}', c['sleeve'], blend=(f'shoulder.{s}', 0.5))
        B.ellipsoid(el, (0.048 * lr,) * 3, f'forearm.{s}', c['forearm'], seg=(10, 8))
        B.cyl(el, wr, 0.046 * lr, 0.037 * lr, f'forearm.{s}', c['forearm'], blend=(f'upperarm.{s}', 0.5))
        hsz = o.get('hand_s', 1.0)
        fist = o.get('fist', True)
        size = (0.075, 0.09, 0.10) if fist else (0.045, 0.085, 0.15)
        size = tuple(v * hsz for v in size)
        B.box(wr + V((sx * 0.004, -0.006, -size[2] / 2 - 0.012)), size, f'hand.{s}', c['hands'],
              bevel=0.018 * hsz, segs=2, smooth=True)
        # legs
        hj, kn = J[f'thigh.{s}']
        an = J[f'shin.{s}'][1]
        x = sx * p['hip_x']
        B.cyl(hj + V((0, 0, 0.04)), kn, 0.082 * lr, 0.06 * lr, f'thigh.{s}', c['pants'], blend=('hips', 0.5))
        B.ellipsoid(kn, (0.058 * lr,) * 3, f'shin.{s}', c['pants'], seg=(10, 8))
        B.cyl(kn, an, 0.056 * lr, 0.043 * lr, f'shin.{s}', c['shin'], blend=(f'thigh.{s}', 0.5))
        bs = o.get('boot_s', 1.0)
        B.cyl(an + V((0, 0, -0.03)), an + V((0, 0, 0.12 * bs)), 0.05 * bs, 0.052 * bs, f'shin.{s}', c['boots'])
        B.box((x, -0.045, 0.048), (0.10 * bs, 0.25 * bs, 0.09), f'foot.{s}', c['boots'], bevel=0.025, segs=2, smooth=True)
        B.box((x, -0.045, 0.012), (0.106 * bs, 0.258 * bs, 0.024), f'foot.{s}', c['sole'], bevel=0.006)


def std_pose(P):
    """Builds an idle pose function from stance params P."""
    def fn(t):
        br = S(t, P.get('breath_n', 1))
        sway = S(t, 1, 0.4)
        bob = S(t, P.get('bob_n', 1), 0.9)
        crouch = P.get('crouch', 0.0)
        hr = P.get('hips_rot', (0, 0, 0))
        sr = P.get('spine_rot', (0, 0, 0))
        cr = P.get('chest_rot', (0, 0, 0))
        nr = P.get('neck_rot', (0, 0, 0))
        hdr = P.get('head_rot', (0, 0, 0))
        b_amp = P.get('breath', 1.6)
        s_amp = P.get('sway', 1.2)
        out = {
            'hips': {'loc': (0, 0, -crouch + P.get('bob', 0.006) * bob - 0.004 * abs(sway)),
                     'rot': (hr[0], hr[1] + s_amp * sway, hr[2] + 0.6 * s_amp * S(t, 1, 1.2))},
            'spine': {'rot': (sr[0] - 0.5 * b_amp * br, sr[1] - 0.5 * s_amp * sway, sr[2])},
            'chest': {'rot': (cr[0] - b_amp * br, cr[1] - 0.5 * s_amp * sway, cr[2] - 0.5 * s_amp * S(t, 1, 1.2))},
            'neck': {'rot': (nr[0] + 0.4 * b_amp * br, nr[1], nr[2])},
            'head': {'rot': (hdr[0] + 0.6 * b_amp * br + 1.2 * S(t, 2, 0.3), hdr[1] + 0.8 * sway,
                             hdr[2] + P.get('head_yaw', 3.0) * S(t, 1, 2.0))},
            'shoulder.L': {'rot': (0, -1.4 * b_amp * (br + 1) / 2, 0)},
            'shoulder.R': {'rot': (0, 1.4 * b_amp * (br + 1) / 2, 0)},
        }
        for s in 'LR':
            fp = P.get('feet', {}).get(s, ((0, 0, 0), 0))
            out[f'ik_foot.{s}'] = {'loc': fp[0], 'rot': (0, 0, fp[1])}
        for name, extra in P.get('extra', {}).items():
            out[name] = extra(t) if callable(extra) else extra
        return out
    return fn


# ----------------------------------------------------------------------------
# Props
# ----------------------------------------------------------------------------

def carbine(B, M, bone, body_c, furn_c, lens_c, accent_c):
    def box(c, s, col, rot=(0, 0, 0), bev=0.006):
        B.box(c, s, bone, col, rot=rot, bevel=bev)
        # move the last part into prop space
    start = len(B.verts)
    box((0.06, 0, 0.035), (0.30, 0.055, 0.075), body_c)
    box((0.06, 0, 0.079), (0.28, 0.03, 0.012), body_c, bev=0.002)
    box((0.30, 0, 0.035), (0.20, 0.062, 0.066), furn_c)
    box((0.30, 0.0, 0.035), (0.12, 0.066, 0.012), accent_c, bev=0.002)
    B.cyl((0.40, 0, 0.04), (0.57, 0, 0.04), 0.011, 0.011, bone, body_c, seg=8)
    B.cyl((0.57, 0, 0.04), (0.62, 0, 0.04), 0.018, 0.018, bone, body_c, seg=8, smooth=False)
    box((0.11, 0, -0.06), (0.05, 0.03, 0.14), furn_c, rot=(0, 14, 0))
    box((-0.01, 0, -0.045), (0.035, 0.036, 0.095), furn_c, rot=(0, -16, 0))
    box((0.31, 0, -0.035), (0.03, 0.03, 0.07), furn_c)
    B.cyl((-0.09, 0, 0.045), (-0.24, 0, 0.035), 0.016, 0.016, bone, body_c, seg=8)
    box((-0.27, 0, 0.02), (0.055, 0.045, 0.13), furn_c, bev=0.01)
    B.cyl((-0.01, 0, 0.115), (0.15, 0, 0.115), 0.022, 0.022, bone, body_c, seg=10, smooth=False)
    B.cyl((0.15, 0, 0.115), (0.16, 0, 0.115), 0.024, 0.024, bone, lens_c, seg=10, smooth=False)
    for i in range(start, len(B.verts)):
        B.verts[i] = M @ B.verts[i]


def battle_rifle(B, M, bone, body_c, dark_c, glow_c, accent_c):
    start = len(B.verts)
    b = lambda c, s, col, rot=(0, 0, 0), bev=0.01: B.box(c, s, bone, col, rot=rot, bevel=bev)
    b((0.10, 0, 0.04), (0.46, 0.085, 0.11), body_c, bev=0.015)
    b((0.10, 0, 0.105), (0.30, 0.05, 0.03), dark_c)
    b((0.06, 0.0, 0.04), (0.20, 0.09, 0.014), glow_c, bev=0.002)
    b((0.40, 0, 0.05), (0.20, 0.07, 0.07), dark_c)
    B.cyl((0.50, 0, 0.055), (0.66, 0, 0.055), 0.016, 0.016, bone, dark_c, seg=8)
    b((0.15, 0, -0.06), (0.07, 0.045, 0.14), dark_c, rot=(0, 10, 0))
    b((-0.02, 0, -0.045), (0.04, 0.045, 0.10), dark_c, rot=(0, -14, 0))
    b((0.38, 0, -0.02), (0.035, 0.035, 0.07), dark_c)
    b((-0.23, 0, 0.03), (0.16, 0.075, 0.12), body_c, bev=0.02)
    b((-0.23, 0.0, 0.03), (0.12, 0.08, 0.02), accent_c, bev=0.003)
    b((0.12, 0, 0.14), (0.10, 0.03, 0.03), glow_c, bev=0.004)
    for i in range(start, len(B.verts)):
        B.verts[i] = M @ B.verts[i]


def to_local_grip(M, p):
    return M @ V(p)


# ----------------------------------------------------------------------------
# Characters
# ----------------------------------------------------------------------------

def char_cs2():
    pal = Palette({
        'skin': ('#c99a7a', 0.6, 0.0, 0), 'eye': ('#141414', 0.3, 0.0, 0), 'mouth': ('#5a2f2a', 0.7, 0, 0),
        'fabric': ('#2c3646', 0.85, 0.0, 0), 'slate': ('#4c5868', 0.8, 0.0, 0), 'vest': ('#3a4352', 0.75, 0.05, 0),
        'pouch': ('#566273', 0.8, 0.0, 0), 'helmet': ('#323d4b', 0.45, 0.35, 0), 'lens': ('#ff9330', 0.08, 0.6, 0.55),
        'bala': ('#1a1d22', 0.9, 0.0, 0), 'glove': ('#1f2227', 0.7, 0.0, 0), 'boot': ('#191a1d', 0.65, 0.0, 0),
        'sole': ('#0e0e10', 0.9, 0.0, 0), 'orange': ('#ff7a1a', 0.5, 0.0, 0.35), 'gun': ('#1d1f23', 0.35, 0.75, 0),
        'gunfurn': ('#35393f', 0.6, 0.15, 0), 'strap': ('#232a34', 0.85, 0, 0),
    })
    p = dict(BASE_PROPS)
    J = joints(p)
    B = Builder(pal)
    c = dict(skin='bala', top='fabric', sleeve='fabric', forearm='fabric', hands='glove', pants='slate',
             shin='slate', boots='boot', sole='sole', neck='bala', brow='bala')
    body(B, J, p, c, dict(chest_w=0.38, no_face=True))
    hz = p['head_z']
    hc = V((0, -0.01, hz + 0.115))
    # helmet + visor
    B.ellipsoid(hc + V((0, 0.008, 0.035)), (0.118, 0.13, 0.11), 'head', 'helmet', seg=(18, 10), cut_below=-0.05)
    for sx in (1, -1):
        B.box(hc + V((sx * 0.115, -0.01, 0.03)), (0.02, 0.10, 0.025), 'head', 'gun', bevel=0.004)
    B.box(hc + V((0, 0.0, 0.055)), (0.03, 0.27, 0.012), 'head', 'orange', bevel=0.003)
    for sx in (1, -1):
        B.box(hc + V((sx * 0.106, 0.01, -0.025)), (0.035, 0.09, 0.09), 'head', 'strap', bevel=0.012, segs=2, smooth=True)
    B.box(hc + V((0, -0.112, 0.012)), (0.17, 0.03, 0.05), 'head', 'lens', bevel=0.01, segs=2, smooth=True)
    B.box(hc + V((0, -0.118, 0.012)), (0.18, 0.015, 0.016), 'head', 'strap')
    B.box(hc + V((0, -0.125, 0.085)), (0.04, 0.025, 0.035), 'head', 'gun', bevel=0.005)
    B.cyl((0, 0, p['neck_z'] - 0.04), (0, 0, hz + 0.03), 0.075, 0.068, 'neck', 'bala', seg=14)
    # plate carrier
    B.box((0, -0.005, 1.31), (0.42, 0.29, 0.31), 'chest', 'vest', bevel=0.03, segs=1)
    for i, x in enumerate((-0.11, 0.0, 0.11)):
        B.box((x, -0.155, 1.235), (0.09, 0.05, 0.11), 'chest', 'pouch', bevel=0.012)
    B.box((0.13, -0.155, 1.37), (0.07, 0.04, 0.08), 'chest', 'pouch', bevel=0.01)
    B.box((0, 0.155, 1.30), (0.30, 0.04, 0.26), 'chest', 'pouch', bevel=0.012)  # back panel
    for sx in (1, -1):
        B.box((sx * 0.13, 0.0, 1.475), (0.07, 0.27, 0.03), 'chest', 'vest', bevel=0.008)
    B.box((0, -0.005, 1.10), (0.33, 0.23, 0.07), 'spine', 'strap', bevel=0.01)  # belt
    B.box((-0.12, -0.12, 1.10), (0.06, 0.05, 0.07), 'spine', 'pouch', bevel=0.008)
    # armband, knee pads, holster
    sh, el = J['upperarm.L']
    B.cyl(sh.lerp(el, 0.55), sh.lerp(el, 0.75), 0.054, 0.051, 'upperarm.L', 'orange', seg=12)
    for s in 'LR':
        kn = J[f'shin.{s}'][0]
        B.box(kn + V((0, -0.05, -0.02)), (0.09, 0.04, 0.11), f'shin.{s}', 'gunfurn', bevel=0.015, segs=2, smooth=True)
    hj, kn = J['thigh.R']
    B.box(hj.lerp(kn, 0.35) + V((-0.075, 0.0, 0)), (0.04, 0.09, 0.16), 'thigh.R', 'strap', bevel=0.01)

    # rifle: low-ready across chest, muzzle down-left
    grip = V((-0.08, -0.27, 1.12))
    d = V((0.70, -0.35, -0.45)).normalized()
    M = place(grip, d, up=(0, 0.3, 1))
    carbine(B, M, 'prop', 'gun', 'gunfurn', 'lens', 'orange')
    fore = M @ V((0.31, 0, -0.04))
    rig = dict(
        props=[('prop', grip, grip + d * 0.1, 'chest')],
        hand_targets={'R': (grip + V((-0.035, 0.05, 0.05)), 'prop'), 'L': (fore + V((0.02, 0.05, 0.05)), 'prop')},
        elbow_poles={'R': (V((-0.55, 0.3, 0.9)), 'chest'), 'L': (V((0.6, 0.2, 0.85)), 'chest')},
        knee_poles={'L': (0.15, -0.8, 0.5), 'R': (-0.15, -0.8, 0.5)},
    )
    P = dict(crouch=0.07, hips_rot=(6, 0, -14), spine_rot=(6, 0, 5), chest_rot=(4, 0, 5), head_rot=(-8, 0, 7),
             feet={'L': ((0.06, -0.13, 0), 8), 'R': ((-0.07, 0.15, 0), -28)},
             breath=1.4, sway=1.0, head_yaw=4.0)
    return pal, p, J, B, rig, P


def char_smash():
    pal = Palette({
        'skin': ('#f0b98f', 0.55, 0.0, 0), 'eye': ('#141019', 0.3, 0, 0), 'mouth': ('#7a2c2c', 0.6, 0, 0),
        'red': ('#e0242f', 0.55, 0.0, 0), 'blue': ('#1f4fe0', 0.6, 0.0, 0), 'gold': ('#ffc21a', 0.3, 0.8, 0),
        'hair': ('#2a1a12', 0.7, 0.0, 0), 'band': ('#f4f4f4', 0.6, 0, 0), 'glove': ('#e0242f', 0.4, 0.0, 0),
        'cuff': ('#f4f4f4', 0.6, 0, 0), 'boot': ('#3b2416', 0.5, 0.0, 0), 'sole': ('#f4f4f4', 0.8, 0, 0),
        'belt': ('#111111', 0.6, 0, 0),
    })
    p = dict(BASE_PROPS)
    p.update(sh_x=0.215, head_h=0.28, neck_z=1.45, head_z=1.53)
    J = joints(p)
    B = Builder(pal)
    c = dict(skin='skin', top='red', sleeve='skin', forearm='skin', hands='glove', pants='blue', shin='blue',
             boots='boot', sole='sole', hair='hair')
    body(B, J, p, c, dict(chest_w=0.42, chest_taper=0.12, head_s=1.22, hand_s=1.55, boot_s=1.25, limb_r=1.15,
                          waist_w=0.30))
    hz = p['head_z']
    hs = 1.22
    hc = V((0, -0.01, hz + 0.115 * hs))
    # spiky hair
    B.ellipsoid(hc + V((0, 0.012, 0.045)), (0.118, 0.13, 0.11), 'head', 'hair', seg=(16, 10), cut_below=-0.15)
    import random
    rnd = random.Random(7)
    for i in range(9):
        a = -0.9 + i * 0.22
        base = hc + V((math.sin(a) * 0.07, 0.03 + math.cos(a) * 0.03, 0.12))
        tip = base + V((math.sin(a) * 0.08, 0.10 + rnd.uniform(-0.02, 0.03), 0.06 + rnd.uniform(0, 0.04)))
        B.cyl(base, tip, 0.045, 0.004, 'head', 'hair', seg=6, smooth=False)
    # headband + tails
    B.cyl(hc + V((0, 0, 0.035)), hc + V((0, 0, 0.075)), 0.124, 0.12, 'head', 'band', seg=18, sides_scale=(1, 1.1))
    knot = hc + V((0, 0.13, 0.05))
    B.box(knot + V((0.04, 0.05, -0.04)), (0.03, 0.12, 0.03), 'head', 'band', rot=(-35, 0, 18))
    B.box(knot + V((-0.03, 0.07, -0.07)), (0.03, 0.14, 0.03), 'head', 'band', rot=(-50, 0, -14))
    # sleeveless top: red chest already; gold belt + cuffs
    B.box((0, -0.002, p['spine_z'] - 0.02), (0.33, 0.22, 0.07), 'spine', 'gold', bevel=0.012)
    B.box((0, -0.115, p['spine_z'] - 0.02), (0.09, 0.02, 0.06), 'spine', 'belt', bevel=0.005)
    for s in 'LR':
        el, wr = J[f'forearm.{s}']
        B.cyl(el.lerp(wr, 0.65), wr + (wr - el).normalized() * 0.01, 0.05, 0.05, f'forearm.{s}', 'cuff', seg=12)
        sh, _ = J[f'upperarm.{s}']
        B.ellipsoid(sh + V((0, 0, 0.02)), (0.09, 0.085, 0.06), f'shoulder.{s}', 'red', seg=(12, 8))
    # fighting stance: orthodox, fists up
    rig = dict(
        hand_targets={'L': (V((0.14, -0.35, 1.44)), 'chest'), 'R': (V((-0.15, -0.27, 1.45)), 'chest')},
        elbow_poles={'L': (V((0.45, -0.25, 0.75)), 'chest'), 'R': (V((-0.45, -0.1, 0.75)), 'chest')},
        knee_poles={'L': (0.35, -0.9, 0.5), 'R': (-0.35, -0.9, 0.5)},
    )
    P = dict(crouch=0.14, hips_rot=(8, 0, -20), spine_rot=(6, 0, 2), chest_rot=(5, 0, 2), head_rot=(-10, 0, 16),
             feet={'L': ((0.13, -0.20, 0), -12), 'R': ((-0.15, 0.18, 0), -40)},
             breath=1.6, sway=1.2, bob=0.018, bob_n=2, breath_n=2, head_yaw=3.0)
    return pal, p, J, B, rig, P


def char_fortnite():
    pal = Palette({
        'skin': ('#e3a77c', 0.55, 0.0, 0), 'eye': ('#141019', 0.3, 0, 0), 'mouth': ('#7a3a30', 0.6, 0, 0),
        'purple': ('#6b2fd1', 0.6, 0.0, 0), 'purple2': ('#4a1f99', 0.65, 0.0, 0), 'cyan': ('#22d8f0', 0.35, 0.0, 0.85),
        'gold': ('#f6b40e', 0.28, 0.85, 0), 'char': ('#29253a', 0.75, 0.0, 0), 'hair': ('#ff6b2c', 0.6, 0, 0),
        'boot': ('#1f1b2b', 0.6, 0.0, 0), 'scarf': ('#16b5a6', 0.75, 0, 0), 'steel': ('#8aa0b8', 0.25, 0.9, 0),
        'wood': ('#3a2b45', 0.6, 0.0, 0), 'glove': ('#29253a', 0.6, 0, 0),
    })
    p = dict(BASE_PROPS)
    p.update(knee_z=0.52, hipj_z=0.95, hip_z=1.0, spine_z=1.12, chest_z=1.26, neck_z=1.48, head_z=1.56, head_h=0.27,
             sh_z=1.44, sh_x=0.205)
    J = joints(p)
    B = Builder(pal)
    c = dict(skin='skin', top='purple', sleeve='purple', forearm='purple2', hands='glove', pants='char',
             shin='char', boots='boot', sole='cyan', hair='hair')
    body(B, J, p, c, dict(chest_w=0.39, chest_taper=0.08, head_s=1.12, hand_s=1.25, boot_s=1.12, limb_r=1.05))
    hz = p['head_z']
    hs = 1.12
    hc = V((0, -0.01, hz + 0.115 * hs))
    # swoopy hair
    B.ellipsoid(hc + V((0, 0.01, 0.04)), (0.112, 0.124, 0.105), 'head', 'hair', seg=(16, 10), cut_below=-0.2)
    B.box(hc + V((0.02, -0.07, 0.12)), (0.17, 0.12, 0.07), 'head', 'hair', rot=(25, -10, 12), bevel=0.03, segs=2, smooth=True)
    B.box(hc + V((-0.03, 0.02, 0.15)), (0.13, 0.15, 0.06), 'head', 'hair', rot=(-15, 12, 0), bevel=0.025, segs=2, smooth=True)
    # jacket details: cyan seams, gold pads
    B.box((0, -0.118, 1.35), (0.025, 0.02, 0.27), 'chest', 'cyan', bevel=0.004)
    B.box((0, -0.002, p['spine_z'] - 0.03), (0.31, 0.215, 0.06), 'spine', 'gold', bevel=0.01)
    for s, sx in (('L', 1), ('R', -1)):
        sh = J[f'upperarm.{s}'][0]
        B.box(sh + V((sx * 0.03, 0, 0.045)), (0.15, 0.17, 0.045), f'shoulder.{s}', 'gold', rot=(0, -sx * 12, 0),
              bevel=0.02, segs=2, smooth=True)
        B.box(sh + V((sx * 0.03, 0, 0.07)), (0.11, 0.03, 0.012), f'shoulder.{s}', 'cyan', rot=(0, -sx * 12, 0))
        kn = J[f'shin.{s}'][0]
        B.box(kn + V((0, -0.05, -0.01)), (0.10, 0.04, 0.12), f'shin.{s}', 'gold', bevel=0.02, segs=2, smooth=True)
        el, wr = J[f'forearm.{s}']
        B.cyl(el.lerp(wr, 0.55), wr, 0.05, 0.045, f'forearm.{s}', 'cyan', seg=12)
    # scarf: ring + trailing tail
    B.cyl((0, -0.005, p['neck_z'] - 0.02), (0, -0.005, p['neck_z'] + 0.06), 0.105, 0.085, 'neck', 'scarf', seg=14)
    B.box((0.06, -0.12, p['neck_z'] - 0.07), (0.07, 0.03, 0.16), 'chest', 'scarf', rot=(8, 0, 10), bevel=0.01)
    B.box((-0.05, 0.13, p['neck_z'] - 0.10), (0.08, 0.025, 0.22), 'chest', 'scarf', rot=(-14, 0, -12), bevel=0.01)
    # back bling: hex emblem
    B.prism((0, 0.19, 1.30), 0.17, 0.05, 'chest', 'gold', sides=6, rot=(90, 0, 30))
    B.prism((0, 0.218, 1.30), 0.11, 0.02, 'chest', 'cyan', sides=6, rot=(90, 0, 30))
    B.prism((0, 0.232, 1.30), 0.05, 0.02, 'chest', 'purple', sides=6, rot=(90, 0, 30))
    B.box((0, 0.15, 1.35), (0.30, 0.05, 0.04), 'chest', 'char', bevel=0.01)
    # pickaxe over right shoulder
    hand = V((-0.13, -0.24, 1.18))
    top = V((-0.24, 0.20, 1.66))
    d = (top - hand).normalized()
    start = len(B.verts)
    L = (top - hand).length
    B.cyl((0, 0, -0.18), (0, 0, L + 0.04), 0.019, 0.019, 'prop', 'wood', seg=8)
    B.cyl((0, 0, -0.20), (0, 0, -0.17), 0.026, 0.026, 'prop', 'gold', seg=8)
    B.box((0, 0, L), (0.05, 0.06, 0.07), 'prop', 'gold', bevel=0.01)
    B.box((0, 0.13, L - 0.03), (0.035, 0.24, 0.05), 'prop', 'steel', rot=(-14, 0, 0), bevel=0.008)
    B.box((0, -0.12, L - 0.035), (0.035, 0.20, 0.05), 'prop', 'steel', rot=(16, 0, 0), bevel=0.008)
    B.box((0, 0.25, L - 0.075), (0.03, 0.06, 0.05), 'prop', 'cyan', rot=(-40, 0, 0))
    B.box((0, -0.22, L - 0.075), (0.03, 0.05, 0.05), 'prop', 'cyan', rot=(40, 0, 0))
    q = V((0, 0, 1)).rotation_difference(d)
    M = Matrix.Translation(hand) @ q.to_matrix().to_4x4() @ Matrix.Rotation(math.radians(-90), 4, 'Z')
    for i in range(start, len(B.verts)):
        B.verts[i] = M @ B.verts[i]
    rig = dict(
        props=[('prop', hand, hand + d * 0.1, 'chest')],
        hand_targets={'R': (hand + V((-0.03, 0.03, -0.06)), 'prop'), 'L': (V((0.23, 0.0, 1.03)), 'hips')},
        elbow_poles={'R': (V((-0.6, 0.1, 1.0)), 'chest'), 'L': (V((0.7, 0.05, 1.2)), 'chest')},
        knee_poles={'L': (0.4, -0.8, 0.5), 'R': (-0.4, -0.8, 0.5)},
    )
    P = dict(crouch=0.02, hips_rot=(0, -5, 10), spine_rot=(-3, 3, -4), chest_rot=(-3, 3, -6), head_rot=(-4, -4, -10),
             feet={'L': ((0.11, -0.04, 0), 18), 'R': ((-0.10, 0.03, 0), -14)},
             breath=1.8, sway=1.4, head_yaw=4.0)
    return pal, p, J, B, rig, P


def char_fifa():
    pal = Palette({
        'skin': ('#e6b996', 0.55, 0.0, 0), 'eye': ('#1e2a36', 0.3, 0, 0), 'mouth': ('#8a4a40', 0.6, 0, 0),
        'sky': ('#6cb4ee', 0.7, 0.0, 0), 'navy': ('#1b2a55', 0.7, 0.0, 0), 'white': ('#f3f4f6', 0.75, 0.0, 0),
        'hair': ('#4a3020', 0.75, 0.0, 0), 'boot': ('#121417', 0.35, 0.1, 0), 'stud': ('#e8ff3a', 0.4, 0, 0.3),
        'ballw': ('#f7f7f7', 0.45, 0.0, 0), 'ballk': ('#15171b', 0.45, 0.0, 0),
    })
    p = dict(BASE_PROPS)
    p.update(knee_z=0.51, hipj_z=0.94, hip_z=0.99, spine_z=1.11, chest_z=1.25, neck_z=1.48, head_z=1.57)
    J = joints(p)
    B = Builder(pal)
    c = dict(skin='skin', top='sky', sleeve='skin', forearm='skin', hands='skin', pants='white', shin='sky',
             boots='boot', sole='stud', hair='hair')
    body(B, J, p, c, dict(chest_w=0.38, chest_taper=0.05, fist=False, waist_w=0.28))
    hz = p['head_z']
    hc = V((0, -0.01, hz + 0.115))
    B.ellipsoid(hc + V((0, 0.012, 0.03)), (0.098, 0.11, 0.105), 'head', 'hair', seg=(16, 10), cut_below=0.05)
    B.box(hc + V((0, -0.06, 0.11)), (0.15, 0.06, 0.04), 'head', 'hair', rot=(20, 0, 0), bevel=0.015, segs=2, smooth=True)
    # kit details: collar, sleeve cuffs, shorts hem, sock bands
    B.cyl((0, 0, p['neck_z'] - 0.035), (0, 0, p['neck_z'] + 0.015), 0.075, 0.068, 'chest', 'navy', seg=14)
    B.box((0, -0.002, p['spine_z'] - 0.03), (0.30, 0.205, 0.10), 'spine', 'sky', bevel=0.03, segs=2, smooth=True)
    for s, sx in (('L', 1), ('R', -1)):
        sh, el = J[f'upperarm.{s}']
        B.cyl(sh, sh.lerp(el, 0.47), 0.066, 0.062, f'upperarm.{s}', 'sky', seg=12, blend=(f'shoulder.{s}', 0.5))
        B.cyl(sh.lerp(el, 0.42), sh.lerp(el, 0.5), 0.067, 0.066, f'upperarm.{s}', 'navy', seg=12)
        B.ellipsoid(sh + V((0, 0, 0.0)), (0.08, 0.08, 0.08), f'upperarm.{s}', 'sky', seg=(12, 8))
        kn, an = J[f'shin.{s}']
        B.cyl(kn.lerp(an, 0.0) + V((0, 0, 0.02)), kn.lerp(an, 0.12), 0.06, 0.059, f'shin.{s}', 'white', seg=12)
        hj, knee = J[f'thigh.{s}']
        B.cyl(hj.lerp(knee, 0.40), hj.lerp(knee, 0.46), 0.092, 0.09, f'thigh.{s}', 'navy', seg=12)
        B.cyl(hj + V((0, 0, 0.03)), hj.lerp(knee, 0.43), 0.095, 0.092, f'thigh.{s}', 'white', seg=12,
              blend=('hips', 0.5))
    B.box((0.0, -0.118, 1.36), (0.05, 0.012, 0.05), 'chest', 'navy', bevel=0.004)  # crest
    for i in range(3):
        B.box((-0.10 + i * 0.1, -0.117, 1.28), (0.012, 0.012, 0.012), 'chest', 'white')
    # ball under right foot
    ico = [V(v).normalized() for v in [(-1, 1.618, 0), (1, 1.618, 0), (-1, -1.618, 0), (1, -1.618, 0),
                                         (0, -1, 1.618), (0, 1, 1.618), (0, -1, -1.618), (0, 1, -1.618),
                                         (1.618, 0, -1), (1.618, 0, 1), (-1.618, 0, -1), (-1.618, 0, 1)]]
    colfn = lambda n: 'ballk' if max(n.dot(i) for i in ico) > 0.95 else 'ballw'
    ball_c = V((-0.13, -0.33, 0.11))
    B.ico(ball_c, 0.11, 'root', 'ballw', subdiv=3, smooth=True, colfn=colfn)
    rig = dict(
        hand_targets={'L': (V((0.20, -0.0, 1.03)), 'hips'), 'R': (V((-0.20, -0.0, 1.03)), 'hips')},
        elbow_poles={'L': (V((0.6, 0.3, 1.2)), 'chest'), 'R': (V((-0.6, 0.3, 1.2)), 'chest')},
        knee_poles={'L': (0.25, -0.8, 0.5), 'R': (-0.25, -0.8, 0.6)},
    )
    sole_to_ankle = p['ankle_z']
    foot_r = ((ball_c.x + 0.095), ball_c.y + 0.03 - 0.0, 0.22 + sole_to_ankle - p['ankle_z'] + 0.005)
    P = dict(crouch=0.015, hips_rot=(0, -6, 6), spine_rot=(-5, 3, 0), chest_rot=(-6, 2, -2), head_rot=(-2, 0, -4),
             feet={'L': ((0.0, 0.02, 0), 10), 'R': ((foot_r[0], foot_r[1], foot_r[2]), -8)},
             breath=1.9, sway=0.9, head_yaw=5.0)
    return pal, p, J, B, rig, P


def char_halo():
    pal = Palette({
        'suit': ('#1b1e23', 0.8, 0.1, 0), 'armor': ('#56687f', 0.3, 0.75, 0), 'armor2': ('#71839a', 0.35, 0.7, 0),
        'crimson': ('#b3202c', 0.45, 0.3, 0), 'visor': ('#38e6ff', 0.08, 0.6, 0.9), 'gun': ('#2a2e34', 0.35, 0.7, 0),
        'gundark': ('#17191c', 0.5, 0.4, 0), 'glow': ('#38e6ff', 0.2, 0.0, 1.0), 'sole': ('#101113', 0.9, 0, 0),
        'skin': ('#1b1e23', 0.8, 0.1, 0), 'eye': ('#000000', 0.5, 0, 0), 'mouth': ('#000000', 0.5, 0, 0),
    })
    p = dict(BASE_PROPS)
    p.update(sh_x=0.235, head_h=0.27, hip_x=0.105)
    J = joints(p)
    B = Builder(pal)
    c = dict(skin='suit', top='suit', sleeve='suit', forearm='suit', hands='suit', pants='suit', shin='suit',
             boots='armor', sole='sole')
    body(B, J, p, c, dict(chest_w=0.40, no_head=True, limb_r=1.18, hand_s=1.2, boot_s=1.28, neck_r=1.25))
    hz = p['head_z']
    hc = V((0, -0.005, hz + 0.12))
    # helmet: angular
    B.box(hc + V((0, 0.0, 0.01)), (0.22, 0.25, 0.24), 'head', 'armor', bevel=0.05, segs=1, taper=(0.82, 0.88))
    B.box(hc + V((0, -0.11, 0.0)), (0.17, 0.06, 0.085), 'head', 'visor', rot=(-8, 0, 0), bevel=0.025, segs=2, smooth=True)
    B.box(hc + V((0, -0.125, -0.085)), (0.12, 0.05, 0.06), 'head', 'armor2', bevel=0.015, taper=(1.2, 1))
    B.box(hc + V((0, 0.0, 0.125)), (0.04, 0.22, 0.03), 'head', 'armor2', bevel=0.008)
    for sx in (1, -1):
        B.box(hc + V((sx * 0.11, 0.015, -0.03)), (0.04, 0.12, 0.10), 'head', 'armor2', bevel=0.012)
        B.box(hc + V((sx * 0.128, 0.03, -0.02)), (0.012, 0.05, 0.03), 'head', 'crimson')
    # chest plate & abs
    B.box((0, -0.01, 1.35), (0.47, 0.30, 0.25), 'chest', 'armor', bevel=0.04, taper=(1.08, 1.0))
    B.box((0, -0.16, 1.37), (0.30, 0.03, 0.12), 'chest', 'armor2', rot=(-10, 0, 0), bevel=0.012)
    B.box((0, -0.168, 1.29), (0.12, 0.02, 0.03), 'chest', 'crimson', bevel=0.004)
    B.box((0, 0.16, 1.32), (0.36, 0.10, 0.32), 'chest', 'armor2', bevel=0.03)  # back pack
    B.box((0, 0.215, 1.38), (0.20, 0.02, 0.04), 'chest', 'glow', bevel=0.004)
    for i in range(2):
        B.box((0, -0.115, 1.15 - i * 0.06), (0.24 - i * 0.03, 0.04, 0.05), 'spine', 'armor2', bevel=0.012)
    B.box((0, -0.0, 0.98), (0.36, 0.25, 0.10), 'hips', 'armor', bevel=0.025)
    B.box((0, -0.13, 0.90), (0.12, 0.04, 0.12), 'hips', 'armor2', bevel=0.015, taper=(0.6, 1))
    # pauldrons, gauntlets, thighs, knees, shins
    for s, sx in (('L', 1), ('R', -1)):
        sh, el = J[f'upperarm.{s}']
        B.box(sh + V((sx * 0.035, 0, 0.03)), (0.20, 0.23, 0.12), f'upperarm.{s}', 'armor', rot=(0, -sx * 25, 0),
              bevel=0.035, segs=1)
        B.box(sh + V((sx * 0.07, -0.0, -0.035)), (0.13, 0.20, 0.07), f'upperarm.{s}', 'armor2', rot=(0, -sx * 35, 0),
              bevel=0.02)
        B.box(sh + V((sx * 0.11, -0.0, 0.03)), (0.02, 0.13, 0.05), f'upperarm.{s}', 'crimson', rot=(0, -sx * 25, 0))
        el, wr = J[f'forearm.{s}']
        B.box(el.lerp(wr, 0.55), (0.11, 0.12, 0.2), f'forearm.{s}', 'armor', bevel=0.025, taper=(0.85, 0.85))
        hj, kn = J[f'thigh.{s}']
        B.box(hj.lerp(kn, 0.45) + V((sx * 0.01, -0.025, 0)), (0.16, 0.10, 0.26), f'thigh.{s}', 'armor', bevel=0.03,
              taper=(1.1, 1.0))
        kn, an = J[f'shin.{s}']
        B.box(kn + V((0, -0.06, 0.0)), (0.11, 0.07, 0.12), f'shin.{s}', 'armor2', bevel=0.025)
        B.box(kn.lerp(an, 0.5) + V((0, -0.025, 0)), (0.12, 0.11, 0.30), f'shin.{s}', 'armor', bevel=0.03,
              taper=(1.1, 1.1))
    # rifle at port arms
    grip = V((-0.08, -0.30, 1.06))
    d = V((0.62, -0.18, 0.62)).normalized()
    M = place(grip, d, up=(0, -1, 0.1))
    battle_rifle(B, M, 'prop', 'gun', 'gundark', 'glow', 'crimson')
    fore = M @ V((0.38, 0, -0.03))
    rig = dict(
        props=[('prop', grip, grip + d * 0.1, 'chest')],
        hand_targets={'R': (grip + V((-0.05, 0.03, -0.0)), 'prop'), 'L': (fore + V((0.02, 0.05, -0.03)), 'prop')},
        elbow_poles={'R': (V((-0.6, 0.2, 0.8)), 'chest'), 'L': (V((0.7, 0.1, 1.0)), 'chest')},
        knee_poles={'L': (0.2, -0.8, 0.5), 'R': (-0.2, -0.8, 0.5)},
    )
    P = dict(crouch=0.035, hips_rot=(3, 0, -6), spine_rot=(4, 0, 0), chest_rot=(3, 0, 3), head_rot=(-3, 0, 2),
             feet={'L': ((0.04, -0.06, 0), 14), 'R': ((-0.04, 0.06, 0), -16)},
             breath=1.2, sway=0.8, head_yaw=6.0)
    return pal, p, J, B, rig, P


CHARS = {
    'cs2': ('01_cs2_blockout', char_cs2),
    'smash': ('02_smash_blockout', char_smash),
    'fortnite': ('03_fortnite_blockout', char_fortnite),
    'fifa': ('04_fifa_blockout', char_fifa),
    'halo': ('05_halo_blockout', char_halo),
}

import * as THREE from 'three';
import type { CharacterId } from '@/types';

/**
 * Runtime pose layer (axis-free skeletal staging).
 *
 * The shipped GLBs come from four rig families (Mixamo, SAS-custom, Daz, ValveBiped)
 * with different rest orientations, so no local-axis assumptions are safe. Every
 * offset here is computed in WORLD space and converted into the bone's local
 * frame at bind time (and each frame for oscillators), which makes the same pose
 * code correct on all four families:
 *
 * - aim: rotate the joint so the joint->child segment points at a world direction.
 *   Applied as `bone.quaternion.multiply(offsetLocal)` AFTER `mixer.update()`,
 *   so the baked Idle motion is preserved and only biased toward the stance.
 *   No drift: the mixer rewrites the base rotation every frame.
 * - yaw: world-Y rotation (head scans) — needs no bone-direction knowledge.
 *
 * Only above-the-hips bones are ever posed (arms, head). Pelvis/legs/root are
 * never touched, so feet stay exactly where the baked loop puts them.
 */

interface BoneTargets {
  upperArmL: string;
  upperArmR: string;
  forearmL: string;
  forearmR: string;
  head: string;
}

const RIGS: Record<CharacterId, BoneTargets> = {
  // Static rigs (artist-built; exporter strips dots): root/hips/spine/chest/neck/
  // head, upperarmL, forearmL, ...
  smash: {
    upperArmL: 'upperarm.L',
    upperArmR: 'upperarm.R',
    forearmL: 'forearm.L',
    forearmR: 'forearm.R',
    head: 'head',
  },
  fortnite: {
    upperArmL: 'upperarm.L',
    upperArmR: 'upperarm.R',
    forearmL: 'forearm.L',
    forearmR: 'forearm.R',
    head: 'head',
  },
  // SAS custom: arm_upper_l_30, arm_lower_l_27, head_0_0 (twists excluded by anchor).
  cs2: {
    upperArmL: 'arm_upper_l',
    upperArmR: 'arm_upper_r',
    forearmL: 'arm_lower_l',
    forearmR: 'arm_lower_r',
    head: 'head_0',
  },
  // Daz Genesis: L_Shoulder, L_Elbow, Head_12 (twists/helpers excluded by anchor).
  fifa: {
    upperArmL: 'L_Shoulder',
    upperArmR: 'R_Shoulder',
    forearmL: 'L_Elbow',
    forearmR: 'R_Elbow',
    head: 'Head',
  },
  // ValveBiped (dots are stripped by the exporter; normalization handles it):
  // ValveBipedBip01_L_UpperArm_013, ValveBipedBip01_L_Forearm_014, ...Head1_06.
  halo: {
    upperArmL: 'ValveBiped.Bip01_L_UpperArm',
    upperArmR: 'ValveBiped.Bip01_R_UpperArm',
    forearmL: 'ValveBiped.Bip01_L_Forearm',
    forearmR: 'ValveBiped.Bip01_R_Forearm',
    head: 'ValveBiped.Bip01_Head1',
  },
};

const escapeRegExp = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

/**
 * Normalizes a bone name for matching: the glTF exporter strips `.` separators
 * (`upperarm.L` → `upperarmL`, `ValveBiped.Bip01_...` → `ValveBipedBip01_...`),
 * so dots are removed from both sides before the anchored comparison.
 */
const normBone = (s: string) => s.replace(/\./g, '').toLowerCase();

/** Anchored match that rejects `_twistN`/`_helper`/`Pad` siblings. */
function findBone(root: THREE.Object3D, pattern: string): THREE.Object3D | null {
  const re = new RegExp(`^${escapeRegExp(normBone(pattern))}(_\\d+)?$`);
  let found: THREE.Object3D | null = null;
  root.traverse((o) => {
    if (found || !o.name || !re.test(normBone(o.name))) return;
    found = o;
  });
  return found;
}

/** First skeletal child that is not a twist/helper/doodad bone. */
function aimChild(bone: THREE.Object3D): THREE.Object3D | null {
  const kids = bone.children.filter(
    (c) => c.name && !/twist|helper|ndl|_pad|weapon|attachment/i.test(c.name),
  );
  return kids[0] ?? bone.children[0] ?? null;
}

export interface AimPose {
  bone: THREE.Object3D;
  child: THREE.Object3D;
  base: THREE.Quaternion;
  /** Static world-space aim direction (character faces +Z, +Y up, +X = its left). */
  dir: THREE.Vector3;
  /** Optional pump: dir wobbles along pumpDir at pumpFreq Hz. Zero = static. */
  pumpAmp: number;
  pumpDir: THREE.Vector3;
  pumpFreq: number;
  pumpPhase: number;
}

export interface YawPose {
  bone: THREE.Object3D;
  base: THREE.Quaternion;
  amp: number;
  freq: number;
  phase: number;
}

export interface CharacterPose {
  aims: AimPose[];
  yaws: YawPose[];
  /** Restore local quats on unmount (shared cached scene must not keep offsets). */
  restore: () => void;
}

const _pq = new THREE.Quaternion();
const _pqInv = new THREE.Quaternion();
const _baseInv = new THREE.Quaternion();
const _q = new THREE.Quaternion();
const _q2 = new THREE.Quaternion();
const _v1 = new THREE.Vector3();
const _v2 = new THREE.Vector3();
const _v3 = new THREE.Vector3();
const Y_AXIS = new THREE.Vector3(0, 1, 0);

/** Mirror a character-space aim direction for right-side bones. */
const mirror = (d: THREE.Vector3, left: boolean) =>
  new THREE.Vector3(left ? Math.abs(d.x) : -Math.abs(d.x), d.y, d.z).normalize();

interface ArmTargets {
  upper: THREE.Vector3;
  fore: THREE.Vector3;
  forePump: number;
  forePumpFreq: number;
  /** Optional per-side overrides (character space, no mirroring applied). */
  upperL?: THREE.Vector3;
  upperR?: THREE.Vector3;
  foreL?: THREE.Vector3;
  foreR?: THREE.Vector3;
}

/** Per-character stance aims (character space: +X = character's left). */
const STANCES: Record<CharacterId, ArmTargets> = {
  // Relaxed combat-ready: arms cradle inward across the torso, forearms forward.
  cs2: {
    upper: new THREE.Vector3(0.3, -1, 0.45),
    fore: new THREE.Vector3(0.1, -0.3, 0.9),
    forePump: 0,
    forePumpFreq: 0,
  },
  // Brawler guard: lead fist forward at chest height, rear fist high at the
  // chin, elbows tucked — asymmetric so it reads as a stance, not a shrug.
  // Rhythmic 2×/loop pump on both forearms.
  smash: {
    upper: new THREE.Vector3(0.7, -0.5, 0.5),
    fore: new THREE.Vector3(0.3, 0.5, 0.8),
    forePump: 0.12,
    forePumpFreq: 0.5,
    upperL: new THREE.Vector3(0.75, -0.5, 0.55),
    upperR: new THREE.Vector3(0.55, -0.6, 0.3),
    foreL: new THREE.Vector3(0.35, 0.35, 0.9),
    foreR: new THREE.Vector3(0.5, 0.75, 0.5),
  },
  // Alert idle: arms hang, soft elbows slightly forward.
  fortnite: {
    upper: new THREE.Vector3(0.16, -1, 0.12),
    fore: new THREE.Vector3(0.12, -1, 0.3),
    forePump: 0,
    forePumpFreq: 0,
  },
  // Relaxed athletic: soft arms, gentle bend.
  fifa: {
    upper: new THREE.Vector3(0.18, -1, 0.1),
    fore: new THREE.Vector3(0.12, -1, 0.22),
    forePump: 0,
    forePumpFreq: 0,
  },
  // Heavy guard: arms angled down-in, forearms forward.
  halo: {
    upper: new THREE.Vector3(0.3, -1, 0.3),
    fore: new THREE.Vector3(0.15, -0.5, 0.75),
    forePump: 0,
    forePumpFreq: 0,
  },
};

/** Head scan: yaw amplitude (rad), frequency (Hz), phase. 4 s Idle loop = 0.25 Hz. */
const HEAD_YAW: Record<CharacterId, { amp: number; freq: number; phase: number }> = {
  cs2: { amp: 0.07, freq: 0.25, phase: 0 }, // ±4° tactical scan
  smash: { amp: 0.035, freq: 0.25, phase: 1.2 }, // cheerful micro-nod energy
  fortnite: { amp: 0.105, freq: 0.25, phase: Math.PI / 2 }, // ±6° alert look
  fifa: { amp: 0.05, freq: 0.25, phase: 0.6 },
  halo: { amp: 0.05, freq: 1 / 6, phase: 0 }, // slow visor pan
};

/**
 * Binds the pose layer. Call once after the first `mixer.update(0)` so base
 * quats reflect the clip's frame 0. Safe to call when bones are missing —
 * unmatched roles are simply skipped.
 */
export function bindCharacterPose(id: CharacterId, scene: THREE.Object3D): CharacterPose {
  const rig = RIGS[id];
  const stance = STANCES[id];
  const aims: AimPose[] = [];
  const yaws: YawPose[] = [];

  const addAim = (
    pattern: string,
    dir: THREE.Vector3,
    left: boolean,
    pumpAmp = 0,
    pumpFreq = 0,
    /** True when dir is already in character space (no mirror). */
    absolute = false,
  ) => {
    const bone = findBone(scene, pattern);
    if (!bone) return;
    const child = aimChild(bone);
    if (!child) return;
    aims.push({
      bone,
      child,
      base: bone.quaternion.clone(),
      dir: absolute ? dir.clone().normalize() : mirror(dir, left),
      pumpAmp,
      pumpDir: new THREE.Vector3(0, 0.35, 0.1).normalize(),
      pumpFreq,
      pumpPhase: 0,
    });
  };

  addAim(rig.upperArmL, stance.upperL ?? stance.upper, true, 0, 0, stance.upperL !== undefined);
  addAim(rig.upperArmR, stance.upperR ?? stance.upper, false, 0, 0, stance.upperR !== undefined);
  addAim(rig.forearmL, stance.foreL ?? stance.fore, true, stance.forePump, stance.forePumpFreq, stance.foreL !== undefined);
  addAim(rig.forearmR, stance.foreR ?? stance.fore, false, stance.forePump, stance.forePumpFreq, stance.foreR !== undefined);

  const headBone = findBone(scene, rig.head);
  if (headBone) {
    const h = HEAD_YAW[id];
    yaws.push({ bone: headBone, base: headBone.quaternion.clone(), amp: h.amp, freq: h.freq, phase: h.phase });
  }

  return {
    aims,
    yaws,
    restore() {
      for (const a of aims) a.bone.quaternion.copy(a.base);
      for (const y of yaws) y.bone.quaternion.copy(y.base);
    },
  };
}

const TAU = Math.PI * 2;

/** Apply after `mixer.update()`. `t` = seconds (use the R3F clock). */
export function applyCharacterPose(pose: CharacterPose, t: number): void {
  for (const a of pose.aims) {
    a.bone.updateWorldMatrix(true, false);
    a.child.updateWorldMatrix(false, false);
    _v1.copy(a.child.getWorldPosition(_v2)).sub(a.bone.getWorldPosition(_v3));
    if (_v1.lengthSq() < 1e-12) continue;
    _v1.normalize();
    _v2.copy(a.dir);
    if (a.pumpAmp > 0 && a.pumpFreq > 0) {
      _v2.addScaledVector(a.pumpDir, a.pumpAmp * Math.sin(TAU * a.pumpFreq * t + a.pumpPhase)).normalize();
    }
    a.bone.parent?.getWorldQuaternion(_pq);
    _q.setFromUnitVectors(_v1, _v2);
    // offsetLocal = base⁻¹ · parent⁻¹ · qAim · parent · base (temps, no allocs)
    _baseInv.copy(a.base).invert();
    _pqInv.copy(_pq).invert();
    _q2.copy(_baseInv).multiply(_pqInv).multiply(_q).multiply(_pq).multiply(a.base);
    a.bone.quaternion.multiply(_q2);
  }
  for (const y of pose.yaws) {
    y.bone.parent?.getWorldQuaternion(_pq);
    _q.setFromAxisAngle(Y_AXIS, y.amp * Math.sin(TAU * y.freq * t + y.phase));
    _baseInv.copy(y.base).invert();
    _pqInv.copy(_pq).invert();
    _q2.copy(_baseInv).multiply(_pqInv).multiply(_q).multiply(_pq).multiply(y.base);
    y.bone.quaternion.multiply(_q2);
  }
}

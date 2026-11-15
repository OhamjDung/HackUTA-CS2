import * as THREE from 'three';
import type { CharacterId } from '@/types';

/**
 * Presence layer: small, anatomically safe life on top of the artist's Idle
 * clip. Applied every frame after `mixer.update()`.
 *
 * Deliberately restrained. Arms and legs are never touched (the clip owns
 * them, so no limb can clip through the body), and every rotation is a few
 * degrees at most:
 *
 * - Breath: the chest lifts ~1.2° on a 4.5 s cycle; clavicles rise slightly.
 * - Weight shift: the lower spine rolls ~1° with a slow, irregular rhythm and
 *   the chest counter-rolls, so the head stays level (how people actually stand).
 * - Head: follows the cursor within ±11° yaw / ±5° pitch, slowly, split across
 *   neck and head; when the cursor is away it makes small idle glances.
 *
 * Rotations are WORLD-space (`q = parent⁻¹ · qW · parent · q`) about
 * character-space axes rotated by the root quaternion, so one implementation is
 * correct on all four rig families (SAS, Rigify-style, Daz, ValveBiped).
 */

interface BoneNames {
  spineLow: string[];
  chest: string[];
  neck: string[];
  head: string;
  clavicles: string[];
}

const RIGS: Record<CharacterId, BoneNames> = {
  cs2: {
    spineLow: ['spine_0', 'spine_1'],
    chest: ['spine_2', 'spine_3'],
    neck: ['neck_0'],
    head: 'head_0',
    clavicles: ['clavicle_l', 'clavicle_r'],
  },
  smash: { spineLow: ['spine'], chest: ['chest'], neck: ['neck'], head: 'head', clavicles: ['shoulder.L', 'shoulder.R'] },
  fortnite: { spineLow: ['spine'], chest: ['chest'], neck: ['neck'], head: 'head', clavicles: ['shoulder.L', 'shoulder.R'] },
  fifa: {
    spineLow: ['Spine1', 'Spine2'],
    chest: ['Spine3', 'Spine4'],
    neck: ['Neck'],
    head: 'Head',
    clavicles: ['L_Clavicle', 'R_Clavicle'],
  },
  halo: {
    spineLow: ['ValveBiped.Bip01_Spine', 'ValveBiped.Bip01_Spine1'],
    chest: ['ValveBiped.Bip01_Spine2', 'ValveBiped.Bip01_Spine4'],
    neck: ['ValveBiped.Bip01_Neck1'],
    head: 'ValveBiped.Bip01_Head1',
    clavicles: ['ValveBiped.Bip01_L_Clavicle', 'ValveBiped.Bip01_R_Clavicle'],
  },
};

/** Temperament: tempo and amplitude per character (heavy armour moves slower). */
const TEMPERAMENT: Record<CharacterId, { tempo: number; amp: number }> = {
  cs2: { tempo: 1, amp: 1 },
  smash: { tempo: 1.15, amp: 1.2 },
  fortnite: { tempo: 1.05, amp: 1.1 },
  fifa: { tempo: 1, amp: 1 },
  halo: { tempo: 0.8, amp: 0.8 },
};

const norm = (s: string) => s.replace(/\./g, '').toLowerCase();
const esc = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

function find(root: THREE.Object3D, pattern: string): THREE.Object3D | null {
  const re = new RegExp(`^${esc(norm(pattern))}(_\\d+)?$`);
  let hit: THREE.Object3D | null = null;
  root.traverse((o) => {
    if (!hit && o.name && re.test(norm(o.name))) hit = o;
  });
  return hit;
}

export interface Presence {
  id: CharacterId;
  spineLow: THREE.Object3D[];
  chest: THREE.Object3D[];
  neck: THREE.Object3D[];
  head: THREE.Object3D | null;
  clavicles: THREE.Object3D[];
  lookYaw: number;
  lookPitch: number;
  saved: Map<THREE.Object3D, THREE.Quaternion>;
}

export function bindPresence(id: CharacterId, scene: THREE.Object3D): Presence {
  const r = RIGS[id];
  const pick = (names: string[]) => names.map((n) => find(scene, n)).filter(Boolean) as THREE.Object3D[];
  const p: Presence = {
    id,
    spineLow: pick(r.spineLow),
    chest: pick(r.chest),
    neck: pick(r.neck),
    head: find(scene, r.head),
    clavicles: pick(r.clavicles),
    lookYaw: 0,
    lookPitch: 0,
    saved: new Map(),
  };
  for (const b of [...p.spineLow, ...p.chest, ...p.neck, ...p.clavicles, p.head]) {
    if (b) p.saved.set(b, b.quaternion.clone());
  }
  return p;
}

export function restorePresence(p: Presence) {
  p.saved.forEach((q, b) => b.quaternion.copy(q));
}

const _pq = new THREE.Quaternion();
const _pqInv = new THREE.Quaternion();
const _qw = new THREE.Quaternion();
const _axis = new THREE.Vector3();
const X = new THREE.Vector3(1, 0, 0);
const Y = new THREE.Vector3(0, 1, 0);
const Z = new THREE.Vector3(0, 0, 1);

function rotateWorld(bone: THREE.Object3D, axis: THREE.Vector3, angle: number, rootQ: THREE.Quaternion) {
  if (Math.abs(angle) < 1e-6) return;
  _axis.copy(axis).applyQuaternion(rootQ);
  _qw.setFromAxisAngle(_axis, angle);
  if (bone.parent) bone.parent.getWorldQuaternion(_pq);
  else _pq.identity();
  _pqInv.copy(_pq).invert();
  bone.quaternion.premultiply(_pq).premultiply(_qw).premultiply(_pqInv);
}

const TAU = Math.PI * 2;
const DEG = Math.PI / 180;

export interface PresenceInput {
  t: number;
  dt: number;
  /** Cursor relative to the character, roughly −1..1 (x right, y up). */
  lookX: number;
  lookY: number;
  rootQ: THREE.Quaternion;
  calm: boolean;
}

export function applyPresence(p: Presence, i: PresenceInput) {
  const k = TEMPERAMENT[p.id];
  const m = (i.calm ? 0.3 : 1) * k.amp;
  const t = i.t * k.tempo;

  // Breath: smooth asymmetric curve (quicker inhale, longer exhale).
  const phase = (t / 4.5) % 1;
  const breath = phase < 0.4 ? Math.sin((phase / 0.4) * (Math.PI / 2)) : Math.cos(((phase - 0.4) / 0.6) * (Math.PI / 2));
  // Weight shift: two incommensurate slow waves, so it never looks like a metronome.
  const sway = 0.7 * Math.sin(TAU * 0.09 * t) + 0.3 * Math.sin(TAU * 0.23 * t + 1.7);

  const nLow = Math.max(1, p.spineLow.length);
  for (const b of p.spineLow) rotateWorld(b, Z, (1.0 * DEG * sway * m) / nLow, i.rootQ);
  const nChest = Math.max(1, p.chest.length);
  for (const b of p.chest) {
    rotateWorld(b, X, (-1.2 * DEG * breath * m) / nChest, i.rootQ);
    rotateWorld(b, Z, (-0.7 * DEG * sway * m) / nChest, i.rootQ);
  }
  p.clavicles.forEach((b, idx) => {
    rotateWorld(b, Z, (idx === 0 ? -1 : 1) * 0.6 * DEG * breath * m, i.rootQ);
  });

  // Head: slow follow within a small cone, plus idle glances.
  const glance = i.calm ? 0 : 3 * DEG * Math.sin(TAU * 0.05 * i.t) * Math.sin(TAU * 0.13 * i.t + 0.4);
  const yawT = THREE.MathUtils.clamp(i.lookX, -1, 1) * 11 * DEG + glance;
  const pitchT = THREE.MathUtils.clamp(-i.lookY, -1, 1) * 5 * DEG;
  const s = 1 - Math.exp(-i.dt * 2.4);
  p.lookYaw += (yawT - p.lookYaw) * s;
  p.lookPitch += (pitchT - p.lookPitch) * s;
  const parts = [...p.neck, ...(p.head ? [p.head] : [])];
  if (!parts.length) return;
  const w = 1 / parts.length;
  for (const b of parts) {
    rotateWorld(b, Y, p.lookYaw * w, i.rootQ);
    rotateWorld(b, X, p.lookPitch * w, i.rootQ);
  }
}

// Generates the five proxy blockout .glb files listed in AGENTS.md
// (public/models/01_cs2_blockout.glb … 05_halo_blockout.glb).
//
// Dependency-free: builds a minimal valid glTF 2.0 binary (JSON + BIN chunks)
// with a merged vertex-colored box humanoid per character. No animations —
// CharacterModel applies a procedural idle bob (see idleAnimationName note in
// lib/constants.ts). Run with: npm run gen-models

import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..', 'public', 'models');

const FACES = [
  // [normal, 4 corner offsets (unit cube centered on origin)]
  [[0, 0, 1], [[-0.5, -0.5, 0.5], [0.5, -0.5, 0.5], [0.5, 0.5, 0.5], [-0.5, 0.5, 0.5]]],
  [[0, 0, -1], [[0.5, -0.5, -0.5], [-0.5, -0.5, -0.5], [-0.5, 0.5, -0.5], [0.5, 0.5, -0.5]]],
  [[1, 0, 0], [[0.5, -0.5, 0.5], [0.5, -0.5, -0.5], [0.5, 0.5, -0.5], [0.5, 0.5, 0.5]]],
  [[-1, 0, 0], [[-0.5, -0.5, -0.5], [-0.5, -0.5, 0.5], [-0.5, 0.5, 0.5], [-0.5, 0.5, -0.5]]],
  [[0, 1, 0], [[-0.5, 0.5, 0.5], [0.5, 0.5, 0.5], [0.5, 0.5, -0.5], [-0.5, 0.5, -0.5]]],
  [[0, -1, 0], [[-0.5, -0.5, -0.5], [0.5, -0.5, -0.5], [0.5, -0.5, 0.5], [-0.5, -0.5, 0.5]]],
];

// Box part: size [sx,sy,sz], center offset [x,y,z], linear color [r,g,b]
function pushBox(arrays, size, offset, color) {
  const base = arrays.positions.length / 3;
  for (const [n, corners] of FACES) {
    const start = arrays.positions.length / 3;
    for (const c of corners) {
      arrays.positions.push(
        offset[0] + c[0] * size[0],
        offset[1] + c[1] * size[1],
        offset[2] + c[2] * size[2],
      );
      arrays.normals.push(...n);
      arrays.colors.push(...color);
    }
    arrays.indices.push(start, start + 1, start + 2, start, start + 2, start + 3);
  }
  return base;
}

function buildHumanoid(proportions, palette) {
  const arrays = { positions: [], normals: [], colors: [], indices: [] };
  const legH = proportions.legH;
  const torsoH = proportions.torsoH;
  const hipY = legH;
  // legs
  pushBox(arrays, [0.16, legH, 0.18], [-0.12, legH / 2, 0], palette.legs);
  pushBox(arrays, [0.16, legH, 0.18], [0.12, legH / 2, 0], palette.legs);
  // pelvis
  pushBox(arrays, [0.42, 0.16, 0.26], [0, hipY + 0.08, 0], palette.accent);
  // torso
  pushBox(arrays, [0.5, torsoH, 0.3], [0, hipY + 0.16 + torsoH / 2, 0], palette.torso);
  const shoulderY = hipY + 0.16 + torsoH - 0.06;
  // arms
  pushBox(arrays, [0.14, proportions.armL, 0.16], [-0.34, shoulderY - proportions.armL / 2, 0], palette.torso);
  pushBox(arrays, [0.14, proportions.armL, 0.16], [0.34, shoulderY - proportions.armL / 2, 0], palette.torso);
  // head
  pushBox(arrays, [0.26, 0.3, 0.28], [0, shoulderY + 0.1 + 0.15, 0], palette.head);
  // visor accent stripe
  pushBox(arrays, [0.27, 0.07, 0.29], [0, shoulderY + 0.12, 0.005], palette.accent);
  return arrays;
}

const ROSTER = [
  {
    file: '01_cs2_blockout.glb',
    proportions: { legH: 0.8, torsoH: 0.62, armL: 0.62 },
    palette: { legs: [0.16, 0.15, 0.14], torso: [0.25, 0.24, 0.22], head: [0.35, 0.3, 0.24], accent: [0.85, 0.08, 0.12] },
  },
  {
    file: '02_smash_blockout.glb',
    proportions: { legH: 0.62, torsoH: 0.72, armL: 0.7 },
    palette: { legs: [0.05, 0.12, 0.35], torso: [0.08, 0.2, 0.6], head: [0.9, 0.75, 0.5], accent: [1.0, 0.75, 0.1] },
  },
  {
    file: '03_fortnite_blockout.glb',
    proportions: { legH: 0.72, torsoH: 0.58, armL: 0.58 },
    palette: { legs: [0.25, 0.05, 0.45], torso: [0.4, 0.1, 0.7], head: [0.95, 0.8, 0.6], accent: [0.1, 0.9, 0.85] },
  },
  {
    file: '04_fifa_blockout.glb',
    proportions: { legH: 0.85, torsoH: 0.55, armL: 0.55 },
    palette: { legs: [0.02, 0.25, 0.08], torso: [0.9, 0.9, 0.9], head: [0.6, 0.45, 0.32], accent: [0.02, 0.35, 0.12] },
  },
  {
    file: '05_halo_blockout.glb',
    proportions: { legH: 0.78, torsoH: 0.66, armL: 0.66 },
    palette: { legs: [0.3, 0.32, 0.25], torso: [0.45, 0.48, 0.35], head: [0.2, 0.22, 0.18], accent: [0.95, 0.7, 0.2] },
  },
];

function buildGlb(arrays) {
  const positions = new Float32Array(arrays.positions);
  const normals = new Float32Array(arrays.normals);
  const colors = new Float32Array(arrays.colors);
  const indices = new Uint16Array(arrays.indices);

  const bin = Buffer.concat([
    Buffer.from(positions.buffer),
    Buffer.from(normals.buffer),
    Buffer.from(colors.buffer),
    Buffer.from(indices.buffer),
  ]);

  let min = [Infinity, Infinity, Infinity];
  let max = [-Infinity, -Infinity, -Infinity];
  for (let i = 0; i < arrays.positions.length; i += 3) {
    for (let a = 0; a < 3; a++) {
      min[a] = Math.min(min[a], arrays.positions[i + a]);
      max[a] = Math.max(max[a], arrays.positions[i + a]);
    }
  }

  const posOff = 0;
  const nrmOff = positions.byteLength;
  const colOff = nrmOff + normals.byteLength;
  const idxOff = colOff + colors.byteLength;

  const json = {
    asset: { version: '2.0', generator: 'faze-blockout-gen' },
    scene: 0,
    scenes: [{ nodes: [0] }],
    nodes: [{ mesh: 0, name: 'blockout' }],
    meshes: [{
      name: 'blockout',
      primitives: [{
        attributes: { POSITION: 0, NORMAL: 1, COLOR_0: 2 },
        indices: 3,
        material: 0,
      }],
    }],
    materials: [{
      name: 'blockout-vc',
      pbrMetallicRoughness: { baseColorFactor: [1, 1, 1, 1], metallicFactor: 0.1, roughnessFactor: 0.8 },
    }],
    accessors: [
      { bufferView: 0, componentType: 5126, count: positions.length / 3, type: 'VEC3', min, max },
      { bufferView: 1, componentType: 5126, count: normals.length / 3, type: 'VEC3' },
      { bufferView: 2, componentType: 5126, count: colors.length / 3, type: 'VEC3' },
      { bufferView: 3, componentType: 5123, count: indices.length, type: 'SCALAR' },
    ],
    bufferViews: [
      { buffer: 0, byteOffset: posOff, byteLength: positions.byteLength, target: 34962 },
      { buffer: 0, byteOffset: nrmOff, byteLength: normals.byteLength, target: 34962 },
      { buffer: 0, byteOffset: colOff, byteLength: colors.byteLength, target: 34962 },
      { buffer: 0, byteOffset: idxOff, byteLength: indices.byteLength, target: 34963 },
    ],
    buffers: [{ byteLength: bin.byteLength }],
  };

  const jsonBytes = Buffer.from(JSON.stringify(json), 'utf8');
  const jsonPad = (4 - (jsonBytes.length % 4)) % 4;
  const binPad = (4 - (bin.length % 4)) % 4;
  const total = 12 + 8 + jsonBytes.length + jsonPad + 8 + bin.length + binPad;

  const out = Buffer.alloc(total);
  let o = 0;
  out.writeUInt32LE(0x46546c67, o); o += 4; // 'glTF'
  out.writeUInt32LE(2, o); o += 4;
  out.writeUInt32LE(total, o); o += 4;
  out.writeUInt32LE(jsonBytes.length + jsonPad, o); o += 4;
  out.writeUInt32LE(0x4e4f534a, o); o += 4; // 'JSON'
  jsonBytes.copy(out, o); o += jsonBytes.length;
  out.fill(0x20, o, o + jsonPad); o += jsonPad;
  out.writeUInt32LE(bin.length + binPad, o); o += 4;
  out.writeUInt32LE(0x004e4942, o); o += 4; // 'BIN'
  bin.copy(out, o);
  return out;
}

mkdirSync(root, { recursive: true });
for (const entry of ROSTER) {
  const arrays = buildHumanoid(entry.proportions, entry.palette);
  const glb = buildGlb(arrays);
  writeFileSync(join(root, entry.file), glb);
  console.log(`wrote ${entry.file} (${(glb.length / 1024).toFixed(1)} KB, ${arrays.indices.length / 3} tris)`);
}

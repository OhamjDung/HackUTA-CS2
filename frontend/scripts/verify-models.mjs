// Asset gatekeeper for the 3D artist's drop (read-only — never modifies .glb files).
// Inspects frontend/public/models/01_cs2_blockout.glb … 05_halo_blockout.glb and
// prints a pass/fail table:
//   - file size (< 2.0 MB each, < 10.0 MB total)
//   - ≥1 animation clip, preferably named `Idle`
//   - skinning: SKIN records and/or JOINTS_0 vertex attributes
//   - EXT_meshopt_compression or KHR_mesh_quantization in extensionsUsed
// Status: PASS (rigged + compressed), PROXY (current un-rigged blockouts),
// FAIL (oversize, unreadable, or rigged-but-uncompressed).
// Exit code is 1 only on FAIL. Run with: npm run verify:models

import { existsSync, readFileSync, statSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const MODELS_DIR = join(
  dirname(fileURLToPath(import.meta.url)),
  '..',
  'public',
  'models',
);

const FILES = [
  '01_cs2_blockout.glb',
  '02_smash_blockout.glb',
  '03_fortnite_blockout.glb',
  '04_fifa_blockout.glb',
  '05_halo_blockout.glb',
];

const MAX_FILE_BYTES = 2_000_000; // 2.0 MB per file
const MAX_TOTAL_BYTES = 10_000_000; // 10.0 MB total budget

const GLB_MAGIC = 0x46546c67; // 'glTF'
const JSON_CHUNK = 0x4e4f534a; // 'JSON'

/** Read-only parse: header + JSON chunk, no writes, no side effects. */
function readGlbJson(path) {
  const buf = readFileSync(path);
  if (buf.length < 12) throw new Error('file smaller than GLB header');
  if (buf.readUInt32LE(0) !== GLB_MAGIC) throw new Error('bad magic, not a GLB');
  const version = buf.readUInt32LE(4);
  if (version !== 2) throw new Error(`unsupported glTF version ${version}`);
  let offset = 12;
  while (offset + 8 <= buf.length) {
    const length = buf.readUInt32LE(offset);
    const type = buf.readUInt32LE(offset + 4);
    if (type === JSON_CHUNK) {
      return JSON.parse(buf.subarray(offset + 8, offset + 8 + length).toString('utf8'));
    }
    offset += 8 + length;
  }
  throw new Error('GLB has no JSON chunk');
}

function hasJoints(json) {
  for (const mesh of json.meshes ?? []) {
    for (const prim of mesh.primitives ?? []) {
      if (prim.attributes && 'JOINTS_0' in prim.attributes) return true;
    }
  }
  return false;
}

function inspect(file) {
  const path = join(MODELS_DIR, file);
  if (!existsSync(path)) {
    return { file, size: '—', anims: '—', skins: '—', joints: '—', compr: '—', status: 'FAIL', note: 'missing file' };
  }
  const bytes = statSync(path).size;
  const size = `${(bytes / 1_000_000).toFixed(2)}MB`;
  if (bytes > MAX_FILE_BYTES) {
    return { file, size, anims: '—', skins: '—', joints: '—', compr: '—', status: 'FAIL', note: 'over 2.0MB' };
  }
  let json;
  try {
    json = readGlbJson(path);
  } catch (err) {
    return { file, size, anims: '—', skins: '—', joints: '—', compr: '—', status: 'FAIL', note: String(err.message).slice(0, 60) };
  }

  const animNames = (json.animations ?? []).map((a) => a.name ?? '(unnamed)');
  const anims = animNames.length === 0 ? '0' : `${animNames.length}:${animNames.includes('Idle') ? 'Idle✓' : animNames[0]}`;
  const skins = String((json.skins ?? []).length);
  const joints = hasJoints(json) ? 'yes' : 'no';
  const used = json.extensionsUsed ?? [];
  const compressed = used.includes('EXT_meshopt_compression') || used.includes('KHR_mesh_quantization');
  const compr = compressed ? used.filter((e) => e.includes('meshopt') || e.includes('quant')).join(',') : 'no';

  const rigged = animNames.length > 0 && ((json.skins ?? []).length > 0 || hasJoints(json));
  let status;
  let note;
  if (!rigged) {
    status = 'PROXY';
    note = 'un-rigged blockout (no clips/skins yet)';
  } else if (!compressed) {
    status = 'FAIL';
    note = 'rigged but missing meshopt/quantization';
  } else {
    status = 'PASS';
    note = 'rigged + compressed';
  }
  return { file, size, anims, skins, joints, compr, status, note };
}

const rows = FILES.map(inspect);
const totalBytes = FILES.reduce((sum, f) => {
  const p = join(MODELS_DIR, f);
  return existsSync(p) ? sum + statSync(p).size : sum;
}, 0);

const widths = { file: 24, size: 8, anims: 14, skins: 6, joints: 7, compr: 24, status: 6 };
const head = ['file', 'size', 'anims', 'skins', 'joints', 'compr', 'status'];
const line = (cells) =>
  cells.map((c, i) => String(c).slice(0, widths[head[i]]).padEnd(widths[head[i]])).join(' | ');

console.log(`\nmodels: ${MODELS_DIR}`);
console.log(line(head));
console.log(head.map((h) => '-'.repeat(widths[h])).join('-+-'));
for (const r of rows) console.log(line([r.file, r.size, r.anims, r.skins, r.joints, r.compr, r.status]) + `  # ${r.note}`);
console.log(`\ntotal: ${(totalBytes / 1_000_000).toFixed(2)}MB / 10.00MB budget`);

const failed = rows.filter((r) => r.status === 'FAIL');
if (totalBytes > MAX_TOTAL_BYTES) {
  console.log('FAIL: total exceeds 10.0MB budget');
  process.exit(1);
}
if (failed.length > 0) {
  console.log(`FAIL: ${failed.length} file(s) need attention (see table)`);
  process.exit(1);
}
if (rows.some((r) => r.status === 'PROXY')) {
  console.log('OK: proxies in place — re-run after the artist drop for PASS.');
} else {
  console.log('OK: all 5 artist models PASS.');
}

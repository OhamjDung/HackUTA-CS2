import assert from 'node:assert/strict';
import test from 'node:test';
import { readFile } from 'node:fs/promises';
import { modeHref, resolveMode, validModeParams } from '../lib/mode/contract.ts';

test('URL mode is explicit and invalid or absent values fall back to FaZe', () => {
  assert.equal(resolveMode('odyssey'), 'odyssey');
  assert.equal(resolveMode('faze'), 'faze');
  assert.equal(resolveMode('future'), 'faze');
  assert.equal(resolveMode(undefined), 'faze');
});

test('destination validation removes cross-mode identifiers', () => {
  const incoming = new URLSearchParams('mode=faze&bot=donk&scene=mirage-mid&tab=upload&tracking=1');
  assert.equal(validModeParams('odyssey', '/play', incoming).toString(), 'mode=odyssey');
  assert.equal(validModeParams('faze', '/play', incoming).toString(), 'mode=faze&bot=donk&scene=mirage-mid');
});

test('route-specific parameters survive only on routes that support them', () => {
  const incoming = new URLSearchParams('bot=odysseus&scene=legendary&tab=famous');
  assert.equal(modeHref('/scenes', 'odyssey', incoming), '/scenes?mode=odyssey&tab=famous&bot=odysseus');
  assert.equal(modeHref('/leaderboard', 'odyssey', incoming), '/leaderboard?mode=odyssey');
});

test('Melantho survives Odyssey navigation', () => {
  assert.equal(modeHref('/play', 'odyssey', { bot: 'melantho' }), '/play?mode=odyssey&bot=melantho');
});

test('Odyssey boundary has no direct dependency on the WebGPU pipeline', async () => {
  const [home, odyssey] = await Promise.all([
    readFile(new URL('../app/page.tsx', import.meta.url), 'utf8'),
    readFile(new URL('../modes/odyssey/OdysseyExperience.tsx', import.meta.url), 'utf8'),
  ]);
  assert.match(home, /dynamic\(\(\) => import\('\@\/components\/faze\/FazeHome'\)\)/);
  assert.doesNotMatch(odyssey, /CharacterCanvas|AssetManager|three\/|three['"]/);
});


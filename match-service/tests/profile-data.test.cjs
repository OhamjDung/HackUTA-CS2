// Run with node --test tests/profile-data.test.cjs.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const { heatBins, quirkValue } = require('../demo/profile.js');

test('heat bins weight known time rather than sample counts and do not extend the tail', () => {
  const heat = heatBins([{ path: [[0, 10, 10], [0.125, 10, 10], [2, 100, 10], [3, 100, 10]] }]);
  assert.equal(heat.seconds, 3);
  assert.deepEqual(heat.bins, [{ x: 0, y: 0, seconds: 2 }, { x: 96, y: 0, seconds: 1 }]);
});

test('heat bins handle empty routes, negative coordinates and invalid intervals', () => {
  assert.deepEqual(heatBins([]).bins, []);
  const heat = heatBins([{ path: [[0, -1, -1], [1, NaN, 2], [2, 0, 0], [2, 0, 0]] }]);
  assert.equal(heat.seconds, 1);
  assert.equal(heat.bins[0].x, -96);
});

test('missing measurements stay distinct from measured zero', () => {
  assert.equal(quirkValue('still_share', 0), '0.0%');
  assert.equal(quirkValue('still_share', null), '—');
  assert.equal(quirkValue('jumps_per_min', undefined), '—');
});

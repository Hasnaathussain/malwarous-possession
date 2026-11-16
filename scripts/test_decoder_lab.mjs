import test from 'node:test';
import assert from 'node:assert/strict';
import {argmaxPath, decodeViterbi, generateEvidence, scorePath} from '../website/sandbox.js';

function exhaustiveObjective(rows, penalty) {
  let best = -Infinity;
  const labels = ['H', 'A', 'D'];
  function visit(path) {
    if (path.length === rows.length) {
      best = Math.max(best, scorePath(rows, path, penalty));
      return;
    }
    for (const label of labels) visit([...path, label]);
  }
  visit([]);
  return best;
}

test('Viterbi objective equals exhaustive search over small deterministic sequences', () => {
  for (let seed = 1; seed <= 6; seed++) {
    const rows = Array.from({length: 6}, (_, frame) =>
      Array.from({length: 3}, (_, state) => Math.sin(seed * 3 + frame * 1.7 + state * .91) * 4));
    for (const penalty of [0, .5, 3, 10]) {
      const decoded = decodeViterbi(rows, penalty);
      assert.ok(Math.abs(decoded.objective - exhaustiveObjective(rows, penalty)) < 1e-9);
      assert.equal(decoded.objective, scorePath(rows, decoded.path, penalty));
    }
  }
});

test('zero penalty recovers frame argmax and ties have deterministic order', () => {
  const rows = [[2, 1, 0], [0, 3, 1], [0, 0, 4], [1, 3, 2]];
  assert.deepEqual(decodeViterbi(rows, 0).path, argmaxPath(rows));
  assert.deepEqual(decodeViterbi([[0, 0, 0], [0, 0, 0]], 10).path, ['H', 'H']);
  assert.deepEqual(decodeViterbi([], 10), {path: [], objective: 0});
});

test('persistence removes a weak twitch while preserving sufficiently strong short evidence', () => {
  const rows = generateEvidence({preset: 'short-regain', regainLength: 3, noise: 0});
  const raw = argmaxPath(rows), persistent = decodeViterbi(rows, 10).path;
  assert.equal(raw[7], 'H');
  assert.equal(persistent[7], 'A');
  assert.deepEqual(persistent.slice(13, 16), ['H', 'H', 'H']);
  assert.ok(decodeViterbi(rows, 10).objective >= scorePath(rows, raw, 10));
});

test('synthetic presets are deterministic, finite and leave input evidence unchanged', () => {
  for (const preset of ['short-regain', 'occlusion', 'stoppage']) {
    const rows = generateEvidence({preset, noise: 45});
    const copy = structuredClone(rows);
    assert.deepEqual(rows, generateEvidence({preset, noise: 45}));
    assert.equal(rows.length, 36);
    assert.ok(rows.every(row => row.length === 3 && row.every(Number.isFinite)));
    decodeViterbi(rows, 10);
    assert.deepEqual(rows, copy);
  }
});

test('invalid evidence, costs and state paths fail instead of producing a misleading result', () => {
  for (const bad of [-1, NaN, Infinity]) assert.throws(() => decodeViterbi([[0, 1, 2]], bad));
  for (const bad of [null, [[0, 1]], [[0, NaN, 1]], [[0, 1, Infinity]]]) {
    assert.throws(() => decodeViterbi(bad, 1));
  }
  assert.throws(() => scorePath([[0, 1, 2]], ['X'], 10));
  assert.throws(() => scorePath([[0, 1, 2]], [], 10));
});

const {smoothEvidence} = await import('../website/sandbox.js');
test('illustrative emission smoothing truncates edges, preserves radius zero and validates radius', () => {
 const source=[[0,6,3],[6,0,3],[0,6,3]];
 assert.deepEqual(smoothEvidence(source,0),source);
 assert.deepEqual(smoothEvidence(source,1),[[3,3,3],[2,4,3],[3,3,3]]);
 assert.deepEqual(source,[[0,6,3],[6,0,3],[0,6,3]]);
 assert.throws(()=>smoothEvidence(source,-1));
 assert.throws(()=>smoothEvidence(source,.5));
});

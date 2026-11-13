import test from 'node:test';
import assert from 'node:assert/strict';
import { answerText, numericPreview, researchError } from '../src/lib/content.mjs';

test('render only the answer after provider control fragments', () => {
  assert.equal(answerText('private preamble</think>Final answer'), 'Final answer');
  assert.equal(answerText('prefix<think>unfinished'), 'prefix');
  assert.equal(answerText('A normal response'), 'A normal response');
  assert.equal(answerText(null), '');
});
test('preview supports fractions and negatives without executing text', () => {
  assert.deepEqual(numericPreview('1/2, -3; 4\n5'), [.5, -3, 4, 5]);
  assert.deepEqual(numericPreview('NaN, Infinity, 1/0, evil()'), []);
  assert.equal(numericPreview(Array(200).fill('1').join(',')).length, 100);
});

test('provider errors become actionable messages without raw payloads', () => {
  assert.match(researchError("Error code: 401 Key is blocked"), /server credentials/);
  assert.match(researchError("429 quota"), /limit/);
  assert.doesNotMatch(researchError("secret stack trace"), /secret/);
});

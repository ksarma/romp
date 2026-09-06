import { test, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { createRequire } from 'node:module';

import { evaluate as guard } from './track-guard.mjs';
import {
  findVaultRoot,
  storePathFor,
  loadStore,
  saveStore,
  ensureStore,
  recordAgentEdit,
  fingerprintOf,
  addThreadEditTurn,
  isTrackedFile,
  trackedPaths,
  setTracked,
  writeTrackedPaths,
  readConfig,
  configPathFor,
} from '../store-io.mjs';

const engine = createRequire(import.meta.url)('../engine.js');
const sha = (s) => createHash('sha256').update(String(s), 'utf8').digest('hex');

let vault;
let note;

beforeEach(() => {
  vault = fs.mkdtempSync(path.join(os.tmpdir(), 'tc-vault-'));
  fs.mkdirSync(path.join(vault, '.obsidian'), { recursive: true });
  note = path.join(vault, 'note.md');
  delete process.env.TRACKCHANGES_ROOT; // force the .obsidian walk
});

afterEach(() => {
  try { fs.rmSync(vault, { recursive: true, force: true }); } catch { /* ignore */ }
});

function payload(tool, file) {
  return JSON.stringify({ tool_name: tool, tool_input: { file_path: file } });
}

// ── store-io units (v3 op-log) ──────────────────────────────────────

test('findVaultRoot locates the .obsidian root', () => {
  fs.writeFileSync(note, 'hi');
  assert.equal(findVaultRoot(note), path.resolve(vault));
});

test('findVaultRoot resolves a code repo via .git (not just .obsidian)', () => {
  const repo = fs.mkdtempSync(path.join(os.tmpdir(), 'tc-repo-'));
  fs.mkdirSync(path.join(repo, '.git'), { recursive: true });
  const f = path.join(repo, 'src', 'mod.py');
  fs.mkdirSync(path.dirname(f), { recursive: true });
  fs.writeFileSync(f, 'x = 1\n');
  assert.equal(findVaultRoot(f), path.resolve(repo));
  try { fs.rmSync(repo, { recursive: true, force: true }); } catch { /* ignore */ }
});

test('ensureStore returns an empty v3 store in the committed .trackchanges dir', () => {
  fs.writeFileSync(note, 'original text');
  const store = ensureStore(vault, note, 'original text');
  assert.equal(store.v, 3);
  assert.deepEqual(store.suggestions, []);
  assert.deepEqual(store.comments, []);
  const sp = storePathFor(vault, note);
  assert.ok(sp.includes(`${path.sep}.trackchanges${path.sep}`));
});

test('recordAgentEdit records an attributed op and persists a v3 store', () => {
  fs.writeFileSync(note, 'hello world');
  recordAgentEdit(vault, note, 'hello world', { from: 6, to: 11, insert: 'planet' }, 'alpha', 2);
  const store = loadStore(storePathFor(vault, note));
  assert.equal(store.v, 3);
  assert.equal(store.suggestions.length, 1);
  const s = store.suggestions[0];
  assert.equal(s.author, 'alpha');
  assert.equal(s.kind, 'sub');
  assert.equal(s.oldText, 'world');
  assert.equal(s.newText, 'planet');
  assert.match(store.id, /^[0-9a-f-]{36}$/);
  // fingerprint is over the NEW current text ("hello planet"), so an unedited
  // move is an exact match.
  assert.equal(store.fingerprint.hash, sha('hello planet'));
  assert.equal(store.fingerprint.size, 'hello planet'.length);
});

test('a second agent edit stacks a second attributed op; the id is stable', () => {
  fs.writeFileSync(note, 'hello world');
  recordAgentEdit(vault, note, 'hello world', { from: 6, to: 11, insert: 'planet' }, 'alpha', 2);
  const first = loadStore(storePathFor(vault, note));
  // second agent edits a different word, against the post-first-edit text
  recordAgentEdit(vault, note, 'hello planet', { from: 0, to: 5, insert: 'HELLO' }, 'beta', 3);
  const store = loadStore(storePathFor(vault, note));
  assert.equal(store.id, first.id, 'id is stable across saves');
  const authors = store.suggestions.map((s) => s.author).sort();
  assert.deepEqual(authors, ['alpha', 'beta'], 'both agents keep their own attribution');
});

// Regression: the read-after-write race that deleted an agent's suggestion when
// the note was open in Obsidian. The CLI writes the note + sidecar atomically (both
// in NEW-text coords). Obsidian's editor buffer lags that disk write by an async
// tick, so a reload MUST re-anchor against the on-disk (NEW) text — re-anchoring
// against the stale pre-edit buffer cannot locate the op and drops it, after which a
// transient-empty save erased the sidecar. This pins both halves of that invariant.
test('a freshly-recorded op survives reload against the DISK text but is dropped against STALE text', () => {
  const pre = 'These instruments generate contrast from instrinsic physical properties.';
  fs.writeFileSync(note, pre);
  const from = pre.indexOf('instrinsic');
  const to = from + 'instrinsic'.length;
  const cur = pre.slice(0, from) + 'intrinsic' + pre.slice(to);
  fs.writeFileSync(note, cur);                                   // CLI writes the note (NEW text)
  recordAgentEdit(vault, note, pre, { from, to, insert: 'intrinsic' }, 'FRO', 7); // + sidecar
  const sp = storePathFor(vault, note);

  // The fixed reloadActive path: re-anchor against the on-disk NEW text → op kept.
  const good = loadStore(sp, cur);
  assert.equal(good.suggestions.length, 1, 'op preserved when re-anchored against disk text');
  assert.equal(good.suggestions[0].newText, 'intrinsic');
  assert.equal(good.suggestions[0].author, 'FRO');

  // The old buggy path: re-anchor against the STALE pre-edit buffer → op dropped.
  const bad = loadStore(sp, pre);
  assert.equal(bad.suggestions.length, 0, 'op dropped when re-anchored against the stale editor buffer');
});

test('fingerprintOf hashes the CURRENT note text (CLI ⇄ plugin agree)', () => {
  assert.equal(fingerprintOf('hello planet').hash, sha('hello planet'));
  assert.equal(fingerprintOf('hello planet').size, 'hello planet'.length);
  assert.equal(fingerprintOf('').hash, sha(''));
});

test('addThreadEditTurn folds a responding edit into a thread by id', () => {
  fs.writeFileSync(note, 'hello world');
  const sp = storePathFor(vault, note);
  const store = ensureStore(vault, note, 'hello world');
  store.comments.push({ id: 'T1', author: 'agent', ts: 1, body: 'fix this', replies: [], anchor: { quote: 'world' } });
  saveStore(vault, sp, store, 'hello world');

  assert.equal(addThreadEditTurn(vault, note, 'T1', 'agent', 'world', 'planet', 2, 'hello world'), true);
  const turn = loadStore(sp, 'hello world').comments.find((c) => c.id === 'T1').replies[0];
  assert.deepEqual(
    { kind: turn.kind, author: turn.author, oldText: turn.oldText, newText: turn.newText },
    { kind: 'edit', author: 'agent', oldText: 'world', newText: 'planet' },
  );
  assert.equal(addThreadEditTurn(vault, note, 'NOPE', 'agent', 'a', 'b', 3, 'hello world'), false);
});

test('loadStore migrates a v1 snapshot store to v3 ops on read', () => {
  const sp = storePathFor(vault, note);
  fs.mkdirSync(path.dirname(sp), { recursive: true });
  const v1 = { v: 1, path: 'note.md', baseline: 'the cat sat',
    edits: [{ author: 'alpha', ts: 1, text: 'the big cat sat' }], comments: [] };
  fs.writeFileSync(sp, JSON.stringify(v1));
  const store = loadStore(sp, 'the big cat sat');
  assert.equal(store.v, 3);
  assert.ok(store.suggestions.length >= 1);
  assert.ok(store.suggestions.every((s) => s.author === 'alpha'));
});

test('the tracked-path list defaults empty and scopes tracking per file/folder', () => {
  const fileA = path.join(vault, 'note.md');
  const fileB = path.join(vault, 'Drafts', 'idea.md');

  assert.equal(readConfig(vault), null);
  assert.deepEqual(trackedPaths(vault), []);
  assert.equal(isTrackedFile(vault, fileA), false);

  setTracked(vault, 'note.md', true);
  assert.equal(isTrackedFile(vault, fileA), true);
  assert.equal(isTrackedFile(vault, fileB), false);
  assert.equal(readConfig(vault).v, 2);
  assert.ok(configPathFor(vault).endsWith(`${path.sep}.trackchanges${path.sep}config.json`));

  setTracked(vault, 'Drafts/', true);
  assert.equal(isTrackedFile(vault, fileB), true);

  setTracked(vault, 'note.md', false);
  assert.equal(isTrackedFile(vault, fileA), false);
  assert.equal(isTrackedFile(vault, fileB), true);
  writeTrackedPaths(vault, ['Drafts/', 'Drafts/']);
  assert.deepEqual(trackedPaths(vault), ['Drafts/']);
});

test('engine.isTracked: exact file, folder prefix, and the non-matches', () => {
  const list = ['Drafts/', 'Notes/idea.md'];
  assert.equal(engine.isTracked(list, 'Notes/idea.md'), true);
  assert.equal(engine.isTracked(list, 'Drafts/x.md'), true);
  assert.equal(engine.isTracked(list, 'Drafts/sub/y.md'), true);
  assert.equal(engine.isTracked(list, './Drafts/x.md'), true);
  assert.equal(engine.isTracked(list, 'Notes/other.md'), false);
  assert.equal(engine.isTracked(list, 'DraftsArchive/x.md'), false);
  assert.equal(engine.isTracked([], 'Notes/idea.md'), false);
  assert.equal(engine.isTracked(null, 'a.md'), false);
});

// ── the track-guard PreToolUse hook (unchanged) ─────────────────────

test('guard blocks a raw edit on a TRACKED file, pointing at track-edit', () => {
  fs.writeFileSync(note, 'tools are slow');
  setTracked(vault, 'note.md', true);
  const reason = guard(payload('Edit', note));
  assert.ok(reason && /track-edit/.test(reason), 'tracked file → block naming track-edit');
});

test('guard allows an UNTRACKED file (the default) — no block', () => {
  fs.writeFileSync(note, 'x');
  assert.equal(guard(payload('Edit', note)), null);
  setTracked(vault, 'other.md', true);
  assert.equal(guard(payload('Edit', note)), null);
});

test('guard covers Write and MultiEdit, ignores non-editing tools', () => {
  setTracked(vault, 'note.md', true);
  assert.ok(guard(payload('Write', note)));
  assert.ok(guard(payload('MultiEdit', note)));
  assert.equal(guard(payload('Read', note)), null);
});

test('guard blocks a file tracked via a folder/ entry', () => {
  const sub = path.join(vault, 'Drafts', 'idea.md');
  fs.mkdirSync(path.dirname(sub), { recursive: true });
  fs.writeFileSync(sub, 'x');
  setTracked(vault, 'Drafts/', true);
  assert.ok(guard(payload('Edit', sub)));
});

test('guard ignores a file outside any vault (no root, no config)', () => {
  const outside = fs.mkdtempSync(path.join(os.tmpdir(), 'tc-bare-'));
  const f = path.join(outside, 'loose.md');
  fs.writeFileSync(f, 'x');
  assert.equal(findVaultRoot(f), null);
  assert.equal(guard(payload('Edit', f)), null);
  try { fs.rmSync(outside, { recursive: true, force: true }); } catch { /* ignore */ }
});

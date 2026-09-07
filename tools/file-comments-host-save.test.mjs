// Slice 5 pins for tools/file-comments-host.mjs: the `save` verb, the editor's Save over a file
// with pending changes (plans/file-review.md, Slice 5). The editor holds
// the new text and the change records it remapped as the person typed; save checks every record
// against the text, writes the sidecar and the file together in track-edit's order, logs the edit
// and the decisions made in the editor, and prunes an emptied sidecar. Same hermetic harness as
// file-comments-host.test.mjs: the synthetic `notes-api` world under a scratch directory, the
// script driven as the kernel drives it, every change recorded by the REAL vendored track-edit,
// and the editor's remap done with the engine's own ingestHumanChanges / acceptSuggestion /
// rejectSuggestion, the calls the vendored track-cm field makes.
// Run: node --test tools/file-comments-host-save.test.mjs
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

import { storePathFor, saveStore, fingerprintOf, writeTrackedPaths } from '../vendor/track-changents/store-io.mjs';
import {
  statNs, logPathFor, applyEdits, editDiff, fitRecords, BadRequest,
  TEXT_MAX_BYTES, EDIT_DIFF_MAX_LINES, EDIT_DIFF_MAX_BYTES,
} from './file-comments-host.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const HOST = path.join(REPO, 'tools', 'file-comments-host.mjs');
const VENDOR = path.join(REPO, 'vendor', 'track-changents');
const FIX = path.join(REPO, 'tests', 'fixtures', 'file_comments');
const engine = createRequire(import.meta.url)(path.join(VENDOR, 'engine.js'));

const SID = '11111111-2222-3333-4444-555555555555';
const NS_RE = /^\d+$/;
const ISO_RE = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/;
const HUNK_RE = /^@@ -\d+(,\d+)? \+\d+(,\d+)? @@$/;

let SCRATCH;
before(() => { SCRATCH = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-fc-host-save-')); });
after(() => { try { fs.rmSync(SCRATCH, { recursive: true, force: true }); } catch { /* ignore */ } });

let worlds = 0;
function world() {
  const home = path.join(SCRATCH, `w${++worlds}`, 'home');
  const root = path.join(home, 'notes-api');
  fs.mkdirSync(path.join(root, '.git'), { recursive: true });
  fs.mkdirSync(path.join(root, 'docs'));
  fs.copyFileSync(path.join(FIX, 'report.md'), path.join(root, 'docs', 'report.md'));
  fs.copyFileSync(path.join(FIX, 'index.md'), path.join(root, 'index.md'));
  const looseDir = path.join(home, 'loose');
  fs.mkdirSync(looseDir);
  fs.copyFileSync(path.join(FIX, 'report.md'), path.join(looseDir, 'report.md'));
  return {
    home, root, looseDir,
    report: path.join(root, 'docs', 'report.md'),
    index: path.join(root, 'index.md'),
    loose: path.join(looseDir, 'report.md'),
    text: fs.readFileSync(path.join(FIX, 'report.md'), 'utf8'),
  };
}

function env(w, extra) {
  const e = { ...process.env, FILE_COMMENTS_HOME: w.home, ...(extra || {}) };
  delete e.TRACKCHANGES_ROOT;
  if (!extra || !('ROMP_SID' in extra)) { delete e.ROMP_SID; delete e.ROMP_SESSION_NAME; }
  return e;
}
function host(w, req) {
  const r = spawnSync(process.execPath, [HOST], { input: JSON.stringify(req), encoding: 'utf8', env: env(w) });
  let json = null;
  try { json = JSON.parse(r.stdout); } catch { json = null; }
  return { code: r.status, stdout: r.stdout, stderr: r.stderr, json };
}
function ok(w, req) {
  const r = host(w, req);
  assert.equal(r.code, 0, `exit ${r.code}: ${r.stderr}`);
  assert.ok(r.json && r.json.ok === true, `expected ok:true, got ${r.stdout}`);
  assert.equal(r.json.verb, req.verb);
  return r.json;
}
function refused(w, req, code) {
  const r = host(w, req);
  assert.equal(r.code, 0, `a refusal exits 0; got ${r.code}: ${r.stderr}`);
  assert.ok(r.json && r.json.ok === false, `expected ok:false, got ${r.stdout}`);
  assert.equal(r.json.code, code, r.json.error);
  assert.equal(typeof r.json.error, 'string');
  return r.json;
}
// A caller bug: exit 2 with the reason on stderr and nothing on stdout.
function crashed(w, req, re) {
  const r = host(w, req);
  assert.equal(r.code, 2, `expected a BadRequest crash, got exit ${r.code}: ${r.stdout}`);
  assert.match(r.stderr, re);
  assert.equal(r.stdout, '');
}
function cli(w, name, args) {
  return spawnSync(process.execPath, [path.join(VENDOR, 'cli', `track-${name}.mjs`), ...args],
    { encoding: 'utf8', env: env(w, { ROMP_SESSION_NAME: 'web', ROMP_SID: SID }) });
}
function cliOk(w, name, args) {
  const r = cli(w, name, args);
  assert.equal(r.status, 0, `track-${name} failed: ${r.stderr}`);
  return r;
}
function status(w, file, args) { return ok(w, { verb: 'status', path: file, args: args || {} }); }
function fenceFor(st) { return { storeMtimeNs: st.storeMtimeNs == null ? '' : st.storeMtimeNs }; }
function fileFenceFor(st) { return { ...fenceFor(st), fileMtimeNs: st.fileMtimeNs }; }
// A tracked edit by the session, then the status the panel would hold afterwards.
function edit(w, file, oldText, newText) {
  cliOk(w, 'edit', ['--file', file, '--old', oldText, '--new', newText]);
  return status(w, file);
}
function hunkFor(st, oldText) {
  const h = st.hunks.find((x) => x.oldText === oldText);
  assert.ok(h, `no hunk with oldText ${JSON.stringify(oldText)} among ${JSON.stringify(st.hunks.map((x) => x.oldText))}`);
  return h;
}
function recordFor(st, id) {
  const s = st.store.suggestions.find((x) => String(x.id) === String(id));
  assert.ok(s, `no record ${id}`);
  return s;
}
// The editor's Save: the buffer's text, the field's records, the ledger.
function save(w, file, st, content, suggestions, accepted, rejected) {
  return ok(w, { verb: 'save', path: file, args: { content, suggestions, accepted: accepted || [], rejected: rejected || [] }, fence: fileFenceFor(st) });
}
function saveReq(file, st, content, suggestions, accepted, rejected) {
  return { verb: 'save', path: file, args: { content, suggestions, accepted: accepted || [], rejected: rejected || [] }, fence: fileFenceFor(st) };
}
const decision = (h) => ({ id: h.id, oldText: h.oldText, newText: h.newText });
// What the editor's field does when the person types: every record mapped through the change.
function typed(text, records, from, to, insert) {
  return { content: text.slice(0, from) + insert + text.slice(to), records: engine.ingestHumanChanges(records, [{ from, to, insert }]) };
}
function readSidecar(sp) { return JSON.parse(fs.readFileSync(sp, 'utf8')); }
function fileBytes(p) { try { return fs.readFileSync(p); } catch { return null; } }
function readLogLines(lp) { return fs.readFileSync(lp, 'utf8').split('\n').filter(Boolean).map((l) => JSON.parse(l)); }
function fits(text, h) { return text.slice(h.curFrom, h.curTo) === h.newText; }
// The disk after a refused save: the file, the sidecar and the log exactly as they were.
function untouched(w, before) {
  assert.deepEqual(fileBytes(before.file), before.fileBytes, 'the file is untouched');
  assert.deepEqual(fileBytes(before.storePath), before.sidecar, 'the sidecar is untouched');
  assert.deepEqual(fileBytes(logPathFor(before.storePath)), before.log, 'the log is untouched');
}
function snapshot(file, storePath) {
  return { file, storePath, fileBytes: fileBytes(file), sidecar: fileBytes(storePath), log: fileBytes(logPathFor(storePath)) };
}

// ── the pure pieces ─────────────────────────────────────────────────

test('editDiff writes the shape the kernel logs for a direct edit (difflib, zero context), newline-terminated, capped', () => {
  // The five shapes Python's difflib.unified_diff(n=0) produces, re-taken with the kernel's
  // add-a-newline rule for a last line without one.
  assert.deepEqual(editDiff('a\nb\nc\n', 'a\nB\nc\nd', 'x.md'),
    { diff: '--- a/x.md\n+++ b/x.md\n@@ -2 +2 @@\n-b\n+B\n@@ -3,0 +4 @@\n+d\n', truncated: false });
  assert.deepEqual(editDiff('x\n', '', 'x.md'), { diff: '--- a/x.md\n+++ b/x.md\n@@ -1 +0,0 @@\n-x\n', truncated: false });
  assert.deepEqual(editDiff('', 'y\n', 'x.md'), { diff: '--- a/x.md\n+++ b/x.md\n@@ -0,0 +1 @@\n+y\n', truncated: false });
  assert.deepEqual(editDiff('a\nb\n', 'a\nb\n', 'x.md'), { diff: '', truncated: false });
  assert.deepEqual(editDiff('a\nb\nc\nd\ne\n', 'a\nc\nd\nE\ne\nf\n', 'x.md'),
    { diff: '--- a/x.md\n+++ b/x.md\n@@ -2 +1,0 @@\n-b\n@@ -4,0 +4 @@\n+E\n@@ -5,0 +6 @@\n+f\n', truncated: false });
  // The line cap counts the header lines, as the kernel's does.
  const many = editDiff('', 'line\n'.repeat(EDIT_DIFF_MAX_LINES + 100), 'x.md');
  assert.equal(many.truncated, true);
  assert.equal(many.diff.split('\n').length - 1, EDIT_DIFF_MAX_LINES);
  // The byte cap cuts before the line that would cross it.
  const wide = editDiff('', 'x'.repeat(EDIT_DIFF_MAX_BYTES + 100) + '\n', 'x.md');
  assert.equal(wide.truncated, true);
  assert.ok(Buffer.byteLength(wide.diff) <= EDIT_DIFF_MAX_BYTES);
  assert.equal(wide.diff, '--- a/x.md\n+++ b/x.md\n@@ -0,0 +1 @@\n');
  // A wholesale replacement past the alignment budget is still one valid hunk, cut by the cap.
  const a = Array.from({ length: 3000 }, (_, i) => `old ${i}\n`).join('');
  const b = Array.from({ length: 3000 }, (_, i) => `new ${i}\n`).join('');
  const bulk = editDiff(a, b, 'x.md');
  assert.equal(bulk.truncated, true);
  assert.match(bulk.diff.split('\n')[2], HUNK_RE);
  assert.equal(bulk.diff.split('\n')[2], '@@ -1,3000 +1,3000 @@');
});

test('fitRecords keeps a record whose text sits at its offset, rebuilt in recordAgentEdit\'s shape, and names the first that does not fit', () => {
  const c = 'Hello brave new world.';
  const good = { id: 'a', author: 'web', authorId: SID, ts: 5, kind: 'del', from: 6, newText: 'brave ', oldText: '', anchor: { quote: 'stale', prefix: '', suffix: '' }, detached: true };
  const r = fitRecords(c, [good]);
  assert.equal(r.misfit, null);
  assert.deepEqual(r.records, [{ id: 'a', author: 'web', authorId: SID, ts: 5, kind: 'ins', from: 6, newText: 'brave ', oldText: '', anchor: { quote: 'brave ', prefix: 'Hello ', suffix: 'new world.' } }]);
  assert.deepEqual(Object.keys(r.records[0]), ['id', 'author', 'authorId', 'ts', 'kind', 'from', 'newText', 'oldText', 'anchor'], 'recordAgentEdit\'s key order');
  // A deletion point carries prefix and suffix and an empty quote, as recordAgentEdit writes it.
  const del = fitRecords(c, [{ id: 'd', author: 'web', ts: 1, from: 6, newText: '', oldText: 'gone ' }]);
  assert.deepEqual(del.records[0].anchor, { quote: '', prefix: 'Hello ', suffix: 'brave new world.' });
  assert.equal(del.records[0].kind, 'del');
  // Misfits, each naming its id: the text moved, an offset outside the text, a record that
  // changes nothing, and two spans that overlap (the later one in document order is named).
  assert.deepEqual(fitRecords(c, [{ ...good, newText: 'bravo ' }]).misfit, { id: 'a', why: 'the text at 6..12 is not the change\'s text' });
  assert.match(fitRecords(c, [{ ...good, from: 99, newText: '', oldText: 'x' }]).misfit.why, /outside the text \(22 characters\)/);
  assert.match(fitRecords(c, [{ ...good, from: 1.5 }]).misfit.why, /outside the text/);
  assert.match(fitRecords(c, [{ ...good, newText: '', oldText: '' }]).misfit.why, /neither adds nor removes/);
  assert.match(fitRecords(c, [{ ...good, newText: 7 }]).misfit.why, /not strings/);
  const ov = fitRecords(c, [{ id: 'b', author: 'web', ts: 1, from: 8, newText: 'ave', oldText: 'zz' }, good]);
  assert.deepEqual(ov.misfit, { id: 'b', why: 'it overlaps change a' });
  // A deletion point inside another change's span is the engine's rule: never an overlap.
  const inside = fitRecords(c, [good, { id: 'd', author: 'web', ts: 1, from: 8, newText: '', oldText: 'gone' }]);
  assert.equal(inside.misfit, null);
  assert.deepEqual(inside.records.map((x) => x.id), ['a', 'd']);
  // Not a record at all, or one id twice: a caller bug.
  assert.throws(() => fitRecords(c, [null]), BadRequest);
  assert.throws(() => fitRecords(c, [{ from: 0, newText: 'H', oldText: '' }]), BadRequest);
  assert.throws(() => fitRecords(c, [good, { ...good, from: 0, newText: 'Hello' }]), BadRequest);
});

// ── the happy path ──────────────────────────────────────────────────

test('save writes the file and the remapped sidecar together, resolves the comments bound to what was decided, and logs the edit and the accept', () => {
  const w = world();
  writeTrackedPaths(w.root, ['docs/report.md']);
  edit(w, w.report, 'cut p95 latency by 40%', 'reduced p95 latency by 35%');
  let st = edit(w, w.report, 'shipping the cache in v1.2', 'shipping the cache in v1.3');
  const cur = fs.readFileSync(w.report, 'utf8');
  const A = hunkFor(st, 'cut p95 latency by 40%');
  const B = hunkFor(st, 'shipping the cache in v1.2');
  st = ok(w, { verb: 'comment', path: w.report, args: { suggestionId: A.id, note: 'Keep the number.' }, fence: fenceFor(st) });
  st = ok(w, { verb: 'comment', path: w.report, args: { note: 'Overall fine.' }, fence: fenceFor(st) });
  const [bound, whole] = st.store.comments;
  assert.equal(bound.suggestionId, A.id);
  assert.equal(whole.suggestionId, undefined);
  const recordB = recordFor(st, B.id);
  const logPath = logPathFor(st.storePath);
  assert.equal(fs.existsSync(logPath), false);

  // In the editor: accept A (the field drops it), then type " (draft)" into the title above B.
  const field = engine.acceptSuggestion(st.store.suggestions, A.id).suggestions;
  const at = cur.indexOf('# Latency report') + '# Latency report'.length;
  const { content, records } = typed(cur, field, at, at, ' (draft)');
  assert.equal(records.length, 1);
  assert.equal(records[0].from, recordB.from + ' (draft)'.length, 'the field remapped B below the insertion');

  const r = save(w, w.report, st, content, records, [decision(A)], []);
  assert.equal(r.logged, true);
  assert.equal(fs.readFileSync(w.report, 'utf8'), content);
  assert.match(r.fileMtimeNs, NS_RE);
  assert.equal(r.fileMtimeNs, statNs(w.report));
  assert.notEqual(r.fileMtimeNs, st.fileMtimeNs);
  assert.equal(r.storeMtimeNs, statNs(st.storePath));
  assert.notEqual(r.storeMtimeNs, st.storeMtimeNs);
  assert.equal(r.storePath, st.storePath);
  // The sidecar: the remapped record in recordAgentEdit's shape, its anchor unchanged because the
  // text around it is, the fingerprint over the new text, the comments kept with the bound one resolved.
  const disk = readSidecar(st.storePath);
  assert.equal(disk.v, 3);
  assert.deepEqual(disk.fingerprint, fingerprintOf(content));
  assert.equal(disk.suggestions.length, 1);
  const s = disk.suggestions[0];
  assert.deepEqual(Object.keys(s), ['id', 'author', 'authorId', 'ts', 'kind', 'from', 'newText', 'oldText', 'anchor']);
  assert.equal(s.id, B.id);
  assert.equal(s.author, 'web');
  assert.equal(s.authorId, SID);
  assert.equal(s.ts, recordB.ts);
  assert.equal(s.kind, 'sub');
  assert.equal(s.from, recordB.from + ' (draft)'.length);
  assert.equal(content.slice(s.from, s.from + s.newText.length), 'shipping the cache in v1.3');
  assert.equal(s.oldText, 'shipping the cache in v1.2');
  assert.deepEqual(s.anchor, recordB.anchor, 'an unmoved record keeps its anchor byte for byte');
  assert.deepEqual(s.anchor, engine.makeAnchor(content, s.from, s.from + s.newText.length));
  assert.deepEqual(disk.comments.map((c) => [c.id, c.resolved, c.body]), [[bound.id, true, 'Keep the number.'], [whole.id, false, 'Overall fine.']]);
  // The reply is the status the panel holds next.
  assert.deepEqual(r.hunks, engine.toHunks(r.store.suggestions));
  assert.equal(r.hunks.length, 1);
  assert.equal(r.hunks[0].id, B.id);
  assert.equal(r.hunks[0].curFrom, B.curFrom + ' (draft)'.length);
  assert.ok(fits(content, r.hunks[0]));
  assert.deepEqual(r.store.comments.map((c) => c.resolved), [true, false]);
  assert.deepEqual(r.trackedBy, { kind: 'file', entry: 'docs/report.md' });
  assert.equal('accepted' in r, false);
  assert.equal('rejected' in r, false);
  // The log: one edit entry in the kernel's direct-edit shape, then the accept; no reject.
  assert.deepEqual(r.log.map((e) => e.kind), ['edit', 'accept']);
  assert.deepEqual(readLogLines(logPath), r.log);
  const [e, acc] = r.log;
  assert.equal(e.author, 'you');
  assert.match(e.ts, ISO_RE);
  assert.deepEqual(Object.keys(e), ['ts', 'kind', 'author', 'mtimeBeforeNs', 'mtimeAfterNs', 'bytesBefore', 'bytesAfter', 'diff', 'truncated']);
  assert.equal(e.mtimeBeforeNs, st.fileMtimeNs);
  assert.equal(e.mtimeAfterNs, r.fileMtimeNs);
  assert.equal(e.bytesBefore, Buffer.byteLength(cur, 'utf8'));
  assert.equal(e.bytesAfter, Buffer.byteLength(content, 'utf8'));
  assert.equal(e.bytesAfter, e.bytesBefore + ' (draft)'.length);
  assert.equal(e.truncated, false);
  assert.equal(e.diff, '--- a/report.md\n+++ b/report.md\n@@ -1 +1 @@\n-# Latency report\n+# Latency report (draft)\n');
  assert.equal(acc.author, 'you');
  assert.match(acc.ts, ISO_RE);
  assert.deepEqual(acc.changes, [{ id: A.id, oldText: 'cut p95 latency by 40%', newText: 'reduced p95 latency by 35%' }]);
  assert.deepEqual(r.unsent, { comments: [bound.id, whole.id], replies: [], accepted: 1, rejected: 0, watermark: null });
  // The session's next track-edit reads the host's sidecar against the new file: nothing was lost,
  // and B still sits where the sidecar says.
  const st2 = edit(w, w.report, 'Cold starts remain slow', 'Cold starts stay slow');
  assert.equal(st2.hunks.length, 2);
  assert.ok(st2.hunks.some((h) => h.id === B.id));
  const text2 = fs.readFileSync(w.report, 'utf8');
  for (const h of st2.hunks) assert.ok(fits(text2, h), `${h.id} fits`);
  assert.deepEqual(st2.store.comments.map((c) => c.resolved), [true, false]);
  assert.equal(st2.store.detached.length, 0);
});

test('a reject made in the editor arrives as content with the old text back; an accept and a reject in one save log both, and an emptied sidecar is pruned', () => {
  const w = world();
  writeTrackedPaths(w.root, ['docs/report.md']);
  edit(w, w.report, 'cut p95 latency by 40%', 'reduced p95 latency by 35%');
  const st = edit(w, w.report, 'shipping the cache in v1.2', 'shipping the cache in v1.3');
  const cur = fs.readFileSync(w.report, 'utf8');
  const A = hunkFor(st, 'cut p95 latency by 40%');
  const B = hunkFor(st, 'shipping the cache in v1.2');
  // In the editor: accept A, then reject B (the engine's reverse edit lands in the buffer).
  let field = engine.acceptSuggestion(st.store.suggestions, A.id).suggestions;
  const res = engine.rejectSuggestion(field, B.id);
  field = res.suggestions;
  const content = applyEdits(cur, [res.edit]);
  assert.deepEqual(field, []);
  assert.ok(content.includes('reduced p95 latency by 35%') && content.includes('shipping the cache in v1.2'));

  const r = save(w, w.report, st, content, field, [decision(A)], [decision(B)]);
  assert.equal(fs.readFileSync(w.report, 'utf8'), content);
  assert.equal(r.logged, true);
  assert.equal(r.store, null, 'nothing pending and no comments: pruned');
  assert.equal(r.storeMtimeNs, null);
  assert.deepEqual(r.hunks, []);
  assert.equal(fs.existsSync(st.storePath), false);
  assert.equal(r.fileMtimeNs, statNs(w.report));
  assert.deepEqual(r.log.map((e) => e.kind), ['edit', 'accept', 'reject']);
  const [e, acc, rej] = r.log;
  assert.match(e.diff, /^--- a\/report\.md\n\+\+\+ b\/report\.md\n@@ -\d+ \+\d+ @@\n-We recommend shipping the cache in v1\.3\.\n\+We recommend shipping the cache in v1\.2\.\n$/);
  assert.deepEqual(acc.changes, [decision(A)]);
  assert.deepEqual(rej.changes, [{ id: B.id, oldText: 'shipping the cache in v1.2', newText: 'shipping the cache in v1.3' }]);
  assert.deepEqual(r.unsent, { comments: [], replies: [], accepted: 1, rejected: 1, watermark: null });
  // The log outlives the sidecar, and the next status derives the same unsent counts from it.
  assert.equal(readLogLines(logPathFor(st.storePath)).length, 3);
  const st2 = status(w, w.report);
  assert.equal(st2.store, null);
  assert.deepEqual(st2.unsent, r.unsent);
  // A sidecar with no changes but a comment is kept.
  const w2 = world();
  writeTrackedPaths(w2.root, ['docs/report.md']);
  let s2 = edit(w2, w2.report, 'cut p95 latency by 40%', 'reduced p95 latency by 35%');
  s2 = ok(w2, { verb: 'comment', path: w2.report, args: { note: 'Overall fine.' }, fence: fenceFor(s2) });
  const h2 = s2.hunks[0];
  const r2 = save(w2, w2.report, s2, fs.readFileSync(w2.report, 'utf8'), [], [decision(h2)], []);
  assert.ok(r2.store, 'a comment keeps the sidecar');
  assert.deepEqual(r2.store.suggestions, []);
  assert.equal(r2.store.comments.length, 1);
  assert.equal(r2.storeMtimeNs, statNs(s2.storePath));
  assert.deepEqual(readSidecar(s2.storePath).fingerprint, fingerprintOf(fs.readFileSync(w2.report, 'utf8')));
});

test('a change remapped below an insertion above it validates and is written where the editor put it, and track-edit carries on from there', () => {
  const w = world();
  writeTrackedPaths(w.root, ['docs/report.md']);
  const st = edit(w, w.report, 'shipping the cache in v1.2', 'shipping the cache in v1.3');
  const cur = fs.readFileSync(w.report, 'utf8');
  const B = st.hunks[0];
  const preface = 'Preface.\n\n';
  const { content, records } = typed(cur, st.store.suggestions, 0, 0, preface);
  const r = save(w, w.report, st, content, records, [], []);
  assert.equal(fs.readFileSync(w.report, 'utf8'), content);
  assert.equal(r.hunks.length, 1);
  assert.equal(r.hunks[0].id, B.id);
  assert.equal(r.hunks[0].curFrom, B.curFrom + preface.length);
  assert.ok(fits(content, r.hunks[0]));
  const disk = readSidecar(st.storePath);
  assert.equal(disk.suggestions[0].from, B.curFrom + preface.length);
  assert.deepEqual(disk.fingerprint, fingerprintOf(content));
  assert.deepEqual(r.log.map((e) => e.kind), ['edit']);
  assert.equal(r.log[0].diff, `--- a/report.md\n+++ b/report.md\n@@ -0,0 +1,2 @@\n+Preface.\n+\n`);
  // The CLI reads the host's sidecar against the new file and adds to it.
  const st2 = edit(w, w.report, 'cut p95 latency by 40%', 'reduced p95 latency by 40%');
  assert.equal(st2.hunks.length, 2);
  const text2 = fs.readFileSync(w.report, 'utf8');
  for (const h of st2.hunks) assert.ok(fits(text2, h), `${h.id} fits`);
  assert.equal(st2.store.detached.length, 0);
});

test('save is a write even when the content equals the file and the records equal the sidecar: a new inode, an edit entry with an empty diff', () => {
  const w = world();
  writeTrackedPaths(w.root, ['docs/report.md']);
  const st = edit(w, w.report, 'shipping the cache in v1.2', 'shipping the cache in v1.3');
  const cur = fs.readFileSync(w.report, 'utf8');
  const ino = fs.statSync(w.report).ino;
  const before = readSidecar(st.storePath);
  const r = save(w, w.report, st, cur, st.store.suggestions, [], []);
  assert.notEqual(fs.statSync(w.report).ino, ino, 'the file was replaced');
  assert.equal(fs.readFileSync(w.report, 'utf8'), cur);
  assert.equal(r.fileMtimeNs, statNs(w.report));
  assert.equal(r.storeMtimeNs, statNs(st.storePath));
  const disk = readSidecar(st.storePath);
  assert.deepEqual(disk.suggestions, before.suggestions, 'the same records, byte for byte');
  assert.deepEqual(disk.fingerprint, before.fingerprint);
  assert.deepEqual(r.log.map((e) => e.kind), ['edit']);
  assert.equal(r.log[0].diff, '');
  assert.equal(r.log[0].truncated, false);
  assert.equal(r.log[0].bytesBefore, r.log[0].bytesAfter);
  assert.equal(r.log[0].mtimeBeforeNs, st.fileMtimeNs);
  assert.equal(r.log[0].mtimeAfterNs, r.fileMtimeNs);
  assert.equal(r.logged, true);
});

test('a big edit logs a truncated diff within the caps', () => {
  const w = world();
  writeTrackedPaths(w.root, ['docs/report.md']);
  const st = status(w, w.report);
  const content = w.text + 'appended line\n'.repeat(EDIT_DIFF_MAX_LINES + 50);
  const r = ok(w, saveReq(w.report, st, content, []));
  const e = r.log[0];
  assert.equal(e.kind, 'edit');
  assert.equal(e.truncated, true);
  assert.equal(e.diff.split('\n').length - 1, EDIT_DIFF_MAX_LINES);
  assert.ok(Buffer.byteLength(e.diff) <= EDIT_DIFF_MAX_BYTES);
  assert.equal(fs.readFileSync(w.report, 'utf8'), content);
});

// ── refusals: nothing written ───────────────────────────────────────

test('desync refuses a record whose text no longer sits at its offset, one outside the text, and two that overlap, naming the id, and writes nothing', () => {
  const w = world();
  writeTrackedPaths(w.root, ['docs/report.md']);
  const st = edit(w, w.report, 'shipping the cache in v1.2', 'shipping the cache in v1.3');
  const cur = fs.readFileSync(w.report, 'utf8');
  const B = st.hunks[0];
  const rec = recordFor(st, B.id);
  const before = snapshot(w.report, st.storePath);
  // The person's text moved on but the records did not (the editor's field is out of step).
  const moved = cur.replace('shipping the cache in v1.3', 'shipping the cache in v2.0');
  let r = refused(w, saveReq(w.report, st, moved, st.store.suggestions), 'desync');
  assert.ok(r.error.includes(`change ${B.id} `), r.error);
  assert.ok(r.error.includes('~/notes-api/docs/report.md'), r.error);
  assert.equal(r.error.includes(w.home), false);
  assert.match(r.error, /is not the change's text/);
  untouched(w, before);
  // An offset past the end.
  r = refused(w, saveReq(w.report, st, cur, [{ ...rec, from: cur.length + 1 }]), 'desync');
  assert.match(r.error, /outside the text/);
  untouched(w, before);
  // A second span starting inside the first: the later one is named.
  const inside = { ...rec, id: 'c1', from: rec.from + 2, newText: cur.slice(rec.from + 2, rec.from + 5), oldText: 'zz' };
  r = refused(w, saveReq(w.report, st, cur, [rec, inside]), 'desync');
  assert.ok(r.error.includes('change c1 '), r.error);
  assert.match(r.error, new RegExp(`overlaps change ${B.id.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}`));
  untouched(w, before);
  assert.deepEqual(Object.keys(r).sort(), ['code', 'error', 'ok']);
  // A deletion point inside the change's span is not an overlap. The point must be rooted, though:
  // a save takes no record whose id is in neither the sidecar nor the comments log and is no
  // fragment (`<id>~n`, the engine's split scheme) of one. Under a fresh id the same point refuses
  // `desync` and writes nothing (file-comments-host-scope.test.mjs pins that rule in full); as a
  // fragment of the change it is written and reloads in place.
  const shape = { author: 'web', authorId: SID, ts: 1700000000000, kind: 'del', from: rec.from + 3, newText: '', oldText: 'gone', anchor: null };   // a fragment carries its parent's author and session id, as the engine's split copies them
  r = refused(w, saveReq(w.report, st, cur, [rec, { id: 'd1', ...shape }]), 'desync');
  assert.match(r.error, /^change d1 was never pending in ~\/notes-api\/docs\/report\.md: /);
  untouched(w, before);
  const point = { id: `${rec.id}~1`, ...shape };
  const r2 = ok(w, saveReq(w.report, st, cur, [rec, point]));
  assert.deepEqual(readSidecar(st.storePath).suggestions.map((s) => s.id), [rec.id, point.id]);
  assert.deepEqual(r2.hunks.map((h) => [h.id, h.kind]), [[rec.id, 'sub'], [point.id, 'del']]);
  assert.equal(r2.store.detached.length, 0);
});

test('save fences on both mtimes and refuses before any write: a moved sidecar, a moved file, "" over an existing sidecar; a missing key or a malformed request is a crash', () => {
  const w = world();
  writeTrackedPaths(w.root, ['docs/report.md']);
  const st = edit(w, w.report, 'shipping the cache in v1.2', 'shipping the cache in v1.3');
  const cur = fs.readFileSync(w.report, 'utf8');
  const recs = st.store.suggestions;
  const before = snapshot(w.report, st.storePath);
  const later = new Date(Date.now() + 60_000);
  // The sidecar moved (an agent's track-edit, or another browser).
  fs.utimesSync(st.storePath, later, later);
  let r = refused(w, saveReq(w.report, st, cur, recs), 'store-moved');
  assert.match(r.error, /the comments for ~\/notes-api\/docs\/report\.md changed on disk/);
  untouched(w, { ...before, sidecar: fileBytes(st.storePath) });
  const st2 = status(w, w.report);
  // The file moved while the sidecar did not.
  fs.utimesSync(w.report, later, later);
  r = refused(w, saveReq(w.report, st2, cur, recs), 'file-moved');
  assert.match(r.error, /the file ~\/notes-api\/docs\/report\.md changed on disk/);
  assert.deepEqual(fileBytes(w.report), before.fileBytes);
  assert.deepEqual(fileBytes(st.storePath), fileBytes(st2.storePath));
  assert.equal(fs.existsSync(logPathFor(st.storePath)), false, 'a refused save logs nothing');
  const st3 = status(w, w.report);
  // "" says no sidecar may exist; one does.
  r = refused(w, { ...saveReq(w.report, st3, cur, recs), fence: { storeMtimeNs: '', fileMtimeNs: st3.fileMtimeNs } }, 'store-moved');
  assert.match(r.error, /appeared on disk/);
  // Caller bugs: a missing fence key, "" with records or decisions (there was nothing to remap or
  // decide), a decision naming a record still being saved, an id decided twice, malformed lists,
  // and content that is not a string. Each is a crash with the reason on stderr, not a refusal.
  crashed(w, { ...saveReq(w.report, st3, cur, recs), fence: { storeMtimeNs: st3.storeMtimeNs } }, /fence\.fileMtimeNs is required for save/);
  crashed(w, { ...saveReq(w.report, st3, cur, recs), fence: { fileMtimeNs: st3.fileMtimeNs } }, /fence\.storeMtimeNs is required for save/);
  crashed(w, { ...saveReq(w.report, st3, cur, recs), fence: null }, /fence\.storeMtimeNs is required/);
  crashed(w, { ...saveReq(w.report, st3, cur, recs, [decision(st3.hunks[0])]) }, /still among the suggestions being saved/);
  crashed(w, { ...saveReq(w.report, st3, cur, [], [decision(st3.hunks[0])], [decision(st3.hunks[0])]) }, /decided twice/);
  crashed(w, { verb: 'save', path: w.report, args: { content: cur, suggestions: recs }, fence: fileFenceFor(st3) }, /save needs accepted/);
  crashed(w, { verb: 'save', path: w.report, args: { content: cur, suggestions: recs, accepted: [], rejected: {} }, fence: fileFenceFor(st3) }, /save needs rejected/);
  crashed(w, { verb: 'save', path: w.report, args: { content: cur, suggestions: recs, accepted: [{ id: st3.hunks[0].id }], rejected: [] }, fence: fileFenceFor(st3) }, /needs oldText and newText/);
  crashed(w, { verb: 'save', path: w.report, args: { content: 7, suggestions: recs, accepted: [], rejected: [] }, fence: fileFenceFor(st3) }, /save needs content/);
  crashed(w, { verb: 'save', path: w.report, args: { content: cur, accepted: [], rejected: [] }, fence: fileFenceFor(st3) }, /save needs suggestions/);
  crashed(w, { verb: 'save', path: w.report, args: { content: cur, suggestions: [recs[0], recs[0]], accepted: [], rejected: [] }, fence: fileFenceFor(st3) }, /appears twice/);
  assert.deepEqual(fileBytes(w.report), before.fileBytes);
  assert.deepEqual(fileBytes(st.storePath), fileBytes(st2.storePath));
  assert.equal(fs.existsSync(logPathFor(st.storePath)), false);
  // With no sidecar, "" and records or decisions cannot go together.
  const w2 = world();
  writeTrackedPaths(w2.root, ['docs/report.md']);
  const s0 = status(w2, w2.report);
  assert.equal(s0.storeMtimeNs, null);
  crashed(w2, saveReq(w2.report, s0, w2.text, recs), /no sidecar takes no suggestions/);
  crashed(w2, saveReq(w2.report, s0, w2.text, [], [{ id: 'x', oldText: 'a', newText: 'b' }]), /no sidecar takes no accepted or rejected/);
  assert.equal(fs.existsSync(storePathFor(w2.root, w2.report)), false);
  assert.equal(fs.existsSync(logPathFor(storePathFor(w2.root, w2.report))), false);
  assert.deepEqual(fileBytes(w2.report), Buffer.from(w2.text));
  // The fresh fence goes through, and the save then lands.
  const r3 = save(w, w.report, st3, cur, recs);
  assert.equal(r3.hunks.length, 1);
});

test('too-large content, content UTF-8 cannot hold, and a file that is not UTF-8 on disk each refuse before any write', () => {
  const w = world();
  writeTrackedPaths(w.root, ['docs/report.md']);
  const st = edit(w, w.report, 'shipping the cache in v1.2', 'shipping the cache in v1.3');
  const cur = fs.readFileSync(w.report, 'utf8');
  const recs = st.store.suggestions;
  const before = snapshot(w.report, st.storePath);
  // Past the cap: refused before the records are even checked against it.
  let r = refused(w, saveReq(w.report, st, 'x'.repeat(TEXT_MAX_BYTES + 1), recs), 'too-large');
  assert.ok(r.error.includes('~/notes-api/docs/report.md'), r.error);
  untouched(w, before);
  // A lone surrogate (JSON carries it; UTF-8 cannot): the file would not hold what was typed.
  r = refused(w, saveReq(w.report, st, cur + '\ud800', recs), 'not-text');
  assert.match(r.error, /cannot encode/);
  untouched(w, before);
  // A NUL would make the file binary to every tracking tool from then on.
  r = refused(w, saveReq(w.report, st, cur + '\0', recs), 'not-text');
  assert.match(r.error, /NUL/);
  untouched(w, before);
  // A file whose bytes are not UTF-8: the editor's text is a lossy decode of it.
  const notes = path.join(w.root, 'docs', 'notes.md');
  const bytes = Buffer.concat([Buffer.from('Hello world.\n'), Buffer.from([0xff, 0xfe]), Buffer.from('\nMore.\n')]);
  fs.writeFileSync(notes, bytes);
  const decoded = bytes.toString('utf8');
  const sp = storePathFor(w.root, notes);
  const op = { id: '1700000000000-0', author: 'web', authorId: SID, ts: 1700000000000, kind: 'sub', from: 0, oldText: 'Hi', newText: 'Hello', anchor: engine.makeAnchor(decoded, 0, 5) };
  saveStore(w.root, sp, { v: 3, path: 'docs/notes.md', suggestions: [op], comments: [] }, decoded);
  const sn = status(w, notes);
  const sidecar = fileBytes(sp);
  r = refused(w, saveReq(notes, sn, decoded, sn.store.suggestions), 'not-text');
  assert.ok(r.error.includes('~/notes-api/docs/notes.md'), r.error);
  assert.match(r.error, /not UTF-8 text, so it cannot be saved/);
  assert.deepEqual(fileBytes(notes), bytes);
  assert.deepEqual(fileBytes(sp), sidecar);
  assert.equal(fs.existsSync(logPathFor(sp)), false);
});

test('a save whose file write fails puts the prior sidecar bytes back, changes nothing, logs nothing, and refuses unreadable with the OS text',
  { skip: typeof process.getuid === 'function' && process.getuid() === 0 ? 'root ignores directory modes' : false }, () => {
    const w = world();
    writeTrackedPaths(w.root, ['docs/report.md']);
    const st = edit(w, w.report, 'shipping the cache in v1.2', 'shipping the cache in v1.3');
    const cur = fs.readFileSync(w.report, 'utf8');
    const B = st.hunks[0];
    const { content, records } = typed(cur, st.store.suggestions, 0, 0, 'Preface.\n');
    const sidecarBytes = fileBytes(st.storePath);
    const docs = path.dirname(w.report);
    const listing = fs.readdirSync(docs).sort();
    // writeFileAtomic creates its temp file beside the file, so a read-only directory fails the
    // file write after the sidecar was saved: the case the rollback exists for.
    fs.chmodSync(docs, 0o555);
    let r;
    try {
      r = refused(w, saveReq(w.report, st, content, records), 'unreadable');
    } finally {
      fs.chmodSync(docs, 0o755);
    }
    assert.match(r.error, /EACCES|EPERM/);
    assert.ok(r.error.includes('~/notes-api/docs/report.md'), r.error);
    assert.equal(r.error.includes(w.home), false);
    assert.match(r.error, /put back/);
    assert.deepEqual(fileBytes(st.storePath), sidecarBytes, 'the prior sidecar bytes are back');
    assert.equal(fs.readFileSync(w.report, 'utf8'), cur, 'the file is untouched');
    assert.deepEqual(fs.readdirSync(docs).sort(), listing, 'no temp file left beside the file');
    assert.equal(fs.existsSync(logPathFor(st.storePath)), false, 'a refused save logs nothing');
    assert.deepEqual(fs.readdirSync(path.dirname(st.storePath)).sort(), ['config.json', path.basename(st.storePath)], 'no restore temp left in .trackchanges');
    // The store is whole: a reload sees the same change, and the same save then succeeds.
    const st2 = status(w, w.report);
    assert.deepEqual(st2.hunks, st.hunks);
    assert.equal(st2.storeMtimeNs, statNs(st.storePath));
    const r2 = save(w, w.report, st2, content, records);
    assert.equal(r2.hunks[0].id, B.id);
    assert.equal(fs.readFileSync(w.report, 'utf8'), content);
  });

// ── no sidecar yet ──────────────────────────────────────────────────

test('a "" fence with no records writes the file and, for a tracked file, the edit entry but never a sidecar; a file with no root gets no landmark and logged:false', () => {
  // A tracked file with no sidecar yet: the log lands beside config.json, no sidecar appears.
  const w = world();
  writeTrackedPaths(w.root, ['docs/report.md']);
  const st = status(w, w.report);
  assert.equal(st.storeMtimeNs, null);
  const sp = storePathFor(w.root, w.report);
  const content = w.text + 'Appendix.\n';
  const r = ok(w, saveReq(w.report, st, content, []));
  assert.equal(fs.readFileSync(w.report, 'utf8'), content);
  assert.equal(fs.existsSync(sp), false, 'nothing to hold: no sidecar is created');
  assert.equal(r.store, null);
  assert.equal(r.storeMtimeNs, null);
  assert.deepEqual(r.hunks, []);
  assert.equal(r.storePath, sp);
  assert.equal(r.logged, true);
  assert.equal(r.fileMtimeNs, statNs(w.report));
  const n = engine.splitLinesKeep(w.text).length;
  assert.deepEqual(r.log.map((e) => [e.kind, e.diff, e.truncated]), [['edit', `--- a/report.md\n+++ b/report.md\n@@ -${n},0 +${n + 1} @@\n+Appendix.\n`, false]]);
  assert.deepEqual(readLogLines(logPathFor(sp)), r.log);
  assert.deepEqual(r.unsent, { comments: [], replies: [], accepted: 0, rejected: 0, watermark: null });
  // A second save with the same "" fence is fine: still no sidecar, a second edit entry.
  const r2 = ok(w, saveReq(w.report, r, content + 'More.\n', []));
  assert.equal(fs.existsSync(sp), false);
  assert.deepEqual(r2.log.map((e) => e.kind), ['edit', 'edit']);
  // A file with no landmark above it: the file is written, nothing is created, logged:false.
  const s2 = status(w, w.loose);
  assert.equal(s2.root, null);
  const r3 = ok(w, saveReq(w.loose, s2, w.text + 'Appendix.\n', []));
  assert.equal(fs.readFileSync(w.loose, 'utf8'), w.text + 'Appendix.\n');
  assert.equal(r3.root, null);
  assert.equal(r3.storePath, null);
  assert.equal(r3.logged, false);
  assert.deepEqual(r3.log, []);
  assert.equal(fs.existsSync(path.join(w.looseDir, '.trackchanges')), false, 'no landmark for a plain save');
  assert.equal(r3.fileMtimeNs, statNs(w.loose));
  // A file under a root that has no .trackchanges/ yet, neither tracked nor commented: the file
  // is written and nothing else happens — no edit entry, no log file, no .trackchanges/ created
  // for it. An `edit` entry is for a file that already has a sidecar, a comments log, or a tracked
  // flag (the plan's rule, the one log-edit follows); a save that created the log would make every
  // later plain save of the file logged too, for a file nobody tracked.
  const w2 = world();
  const s3 = status(w2, w2.index);
  assert.equal(s3.root, w2.root);
  assert.equal(fs.existsSync(path.join(w2.root, '.trackchanges')), false);
  const text2 = fs.readFileSync(w2.index, 'utf8') + '\nAppendix.\n';
  const r4 = ok(w2, saveReq(w2.index, s3, text2, []));
  assert.equal(fs.readFileSync(w2.index, 'utf8'), text2, 'the file is written');
  assert.equal(r4.fileMtimeNs, statNs(w2.index));
  assert.equal(r4.logged, false);
  assert.deepEqual(r4.log, []);
  assert.equal(r4.trackedBy, null);
  assert.equal(r4.store, null);
  assert.equal(fs.existsSync(path.join(w2.root, '.trackchanges')), false, 'nothing is created for a file the log has no business with');
});

// The rule save follows for its edit entry is log-edit's, so a save from the editor and a plain
// saveFile of the same file at the same moment log alike: the file is logged when it already has
// a sidecar, a comments log, or a tracked flag, and never otherwise. The untracked, uncommented
// case is the request a browser sends when its status predates a peer's toggle-off (the client
// decides the route from the status it holds); the host does not take its word for it.
test('save logs an edit only for a file with a sidecar, a log, or a tracked flag — the rule log-edit follows — and creates no log otherwise', () => {
  const summary = { mtimeBeforeNs: '1', mtimeAfterNs: '2', bytesBefore: 10, bytesAfter: 12, diff: '@@ -1 +1 @@\n-a\n+b\n', truncated: false };
  const w = world();
  const lp = logPathFor(storePathFor(w.root, w.index));
  // Neither tracked nor commented: log-edit would not log it, and neither does save.
  const c0 = ok(w, { verb: 'log-edit', path: w.index, args: { summary } });
  assert.equal(c0.logged, false);
  assert.equal(fs.existsSync(path.join(w.root, '.trackchanges')), false);
  const s0 = status(w, w.index);
  const t1 = fs.readFileSync(w.index, 'utf8') + '\nOne.\n';
  const r1 = ok(w, saveReq(w.index, s0, t1, []));
  assert.equal(fs.readFileSync(w.index, 'utf8'), t1);
  assert.equal(r1.logged, false);
  assert.deepEqual(r1.log, []);
  assert.equal(fs.existsSync(lp), false, 'no log is created');
  assert.equal(fs.existsSync(path.join(w.root, '.trackchanges')), false);
  // The save changed nothing about the file's standing: a later plain save is still not logged.
  const c1 = ok(w, { verb: 'log-edit', path: w.index, args: { summary } });
  assert.equal(c1.logged, false);
  assert.equal(fs.existsSync(lp), false);
  // Tracked flag: logged. Then the flag is removed the way a CLI, a hand edit, or a sibling
  // file's folder toggle removes it — no entry lands on this file's log — and the log alone
  // keeps the file the log's business, so the next save is logged too.
  writeTrackedPaths(w.root, ['index.md']);
  const s1 = status(w, w.index);
  assert.deepEqual(s1.trackedBy, { kind: 'file', entry: 'index.md' });
  const t2 = t1 + 'Two.\n';
  const r2 = ok(w, saveReq(w.index, s1, t2, []));
  assert.equal(r2.logged, true);
  assert.deepEqual(r2.log.map((e) => e.kind), ['edit']);
  assert.equal(fs.existsSync(storePathFor(w.root, w.index)), false, 'no sidecar is created');
  writeTrackedPaths(w.root, []);
  const s2 = status(w, w.index);
  assert.equal(s2.trackedBy, null);
  assert.equal(s2.storeMtimeNs, null);
  assert.deepEqual(s2.log.map((e) => e.kind), ['edit'], 'the log survives the untrack');
  const t3 = t2 + 'Three.\n';
  const r3 = ok(w, saveReq(w.index, s2, t3, []));
  assert.equal(r3.logged, true);
  assert.equal(r3.trackedBy, null);
  assert.deepEqual(r3.log.map((e) => e.kind), ['edit', 'edit']);
  assert.deepEqual(readLogLines(lp).map((e) => e.kind), ['edit', 'edit']);
  assert.equal(fs.readFileSync(w.index, 'utf8'), t3);
  // A sidecar alone (an untracked file with a whole-file comment) is logged as well.
  const other = path.join(w.root, 'docs', 'other.md');
  fs.writeFileSync(other, 'Some text.\n');
  const so = status(w, other);
  assert.equal(so.trackedBy, null);
  const co = ok(w, { verb: 'comment', path: other, args: { note: 'whole-file note' }, fence: fenceFor(so) });
  assert.ok(co.store, 'the comment made a sidecar');
  const s4 = status(w, other);
  const r4 = ok(w, saveReq(other, s4, 'Some text.\nMore.\n', s4.store.suggestions));
  assert.equal(r4.logged, true);
  assert.equal(r4.trackedBy, null);
  assert.deepEqual(r4.log.map((e) => e.kind), ['edit']);
  assert.equal(readSidecar(co.storePath).comments.length, 1, 'the comment is kept');
});

// The window the rule above closes. The panel decides the route (save through this host, or the
// kernel's saveFile) from the status it holds, and the config is polled, so a save can arrive with
// a status that said tracked after the flag is gone; save fences on the sidecar and the file, not
// the config, so nothing refuses it. The flag can leave with no entry on this file's log — a
// sibling file's panel turning the covering folder off (the set-tracked entry lands on the
// sibling's log), a hand edit of config.json — and then the file has no sidecar, no log, and no
// flag: logged from the status, the save would have created the file's log, and every later plain
// save of it would be logged too. The host reads the disk as it is at the save.
test('a save whose status predates a toggle-off that left no entry on this file\'s log is written, not logged, and creates no log; the mirror, a status predating a toggle-on, is logged', () => {
  const w = world();
  // Tracked by a folder entry covering docs/: the status at Edit says so; no sidecar, no log yet.
  writeTrackedPaths(w.root, ['docs/']);
  const atEdit = status(w, w.report);
  assert.deepEqual(atEdit.trackedBy, { kind: 'folder', entry: 'docs/' });
  assert.equal(atEdit.storeMtimeNs, null);
  const lp = logPathFor(storePathFor(w.root, w.report));
  assert.equal(fs.existsSync(lp), false);
  // A sibling file's panel turns the folder off: the entry lands on that file's log, none on this one.
  const other = path.join(w.root, 'docs', 'other.md');
  fs.writeFileSync(other, 'Some text.\n');
  const so = status(w, other);
  assert.deepEqual(so.trackedBy, { kind: 'folder', entry: 'docs/' });
  const off = ok(w, { verb: 'set-tracked', path: other, args: { on: false }, fence: { configMtimeNs: so.configMtimeNs } });
  assert.equal(off.trackedBy, null);
  assert.deepEqual(off.log.map((e) => [e.kind, e.on, e.entry]), [['set-tracked', false, 'docs/']]);
  assert.equal(fs.existsSync(lp), false, 'the sibling\'s toggle leaves no entry on this file\'s log');
  assert.equal(status(w, w.report).trackedBy, null);
  const tc = path.join(w.root, '.trackchanges');
  const listing = fs.readdirSync(tc).sort();
  assert.deepEqual(listing, ['config.json', path.basename(logPathFor(so.storePath))]);
  // The editor's Save, fenced on the status at Edit: not refused (save has no config fence), the
  // file written, and the log left alone — the disk, not the browser's status, says whether the
  // log has business with the file.
  const content = w.text + 'Appendix.\n';
  const r = ok(w, saveReq(w.report, atEdit, content, []));
  assert.equal(fs.readFileSync(w.report, 'utf8'), content, 'the file is written');
  assert.equal(r.fileMtimeNs, statNs(w.report));
  assert.equal(r.logged, false);
  assert.deepEqual(r.log, []);
  assert.equal(r.trackedBy, null);
  assert.equal(r.store, null);
  assert.equal(r.storeMtimeNs, null);
  assert.equal(fs.existsSync(lp), false, 'no log is created for a file nobody tracks');
  assert.deepEqual(fs.readdirSync(tc).sort(), listing, 'nothing new in .trackchanges/');
  // The plain-saveFile rule agrees afterwards: the file is still not the log's business.
  const summary = { mtimeBeforeNs: '1', mtimeAfterNs: '2', bytesBefore: 10, bytesAfter: 12, diff: '@@ -1 +1 @@\n-a\n+b\n', truncated: false };
  assert.equal(ok(w, { verb: 'log-edit', path: w.report, args: { summary } }).logged, false);
  assert.equal(fs.existsSync(lp), false);
  // The same with a file entry removed by a hand edit of config.json.
  const w2 = world();
  writeTrackedPaths(w2.root, ['docs/report.md']);
  const s2 = status(w2, w2.report);
  assert.deepEqual(s2.trackedBy, { kind: 'file', entry: 'docs/report.md' });
  writeTrackedPaths(w2.root, []);
  const r2 = ok(w2, saveReq(w2.report, s2, w2.text + 'Appendix.\n', []));
  assert.equal(fs.readFileSync(w2.report, 'utf8'), w2.text + 'Appendix.\n');
  assert.equal(r2.logged, false);
  assert.deepEqual(r2.log, []);
  assert.equal(r2.trackedBy, null);
  assert.deepEqual(fs.readdirSync(path.join(w2.root, '.trackchanges')), ['config.json'], 'no log is created');
  // The mirror: a status taken before the flag was written, the save after — logged, because the
  // disk says tracked now. The fence still holds: no sidecar then, none now.
  const w3 = world();
  const s3 = status(w3, w3.report);
  assert.equal(s3.trackedBy, null);
  assert.equal(s3.root, w3.root);
  writeTrackedPaths(w3.root, ['docs/report.md']);
  const r3 = ok(w3, saveReq(w3.report, s3, w3.text + 'Appendix.\n', []));
  assert.equal(fs.readFileSync(w3.report, 'utf8'), w3.text + 'Appendix.\n');
  assert.equal(r3.logged, true);
  assert.deepEqual(r3.trackedBy, { kind: 'file', entry: 'docs/report.md' });
  assert.deepEqual(r3.log.map((e) => e.kind), ['edit']);
  assert.deepEqual(readLogLines(logPathFor(storePathFor(w3.root, w3.report))).map((e) => e.kind), ['edit']);
  assert.equal(fs.existsSync(storePathFor(w3.root, w3.report)), false, 'still no sidecar');
});

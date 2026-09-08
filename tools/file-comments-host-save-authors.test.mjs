// Pins for tools/file-comments-host.mjs from the Slice 5 review (plans/file-review.md, Slice 5;
// Security posture): a `save`'s change records are checked against the change they are rooted in, not
// only against `content` and for the id's rooting.
//   * A record rooted in a change the sidecar holds must name that change's author and session id
//     (`author`, `authorId`): one under another author or session refuses `desync` by id, every such
//     record named in the caller's order, and nothing is written. Before this the host rebuilt the
//     sidecar's record from the author and authorId the client sent, so a save could re-file the
//     session's change under another session's name — the name the next Reject's log entry and the
//     session's trace would then carry.
//   * The records a real editor derives still land: a fragment the engine splits off (`X~1`) carries
//     its parent's author and session id, and two changes a deletion between them made adjacent merge
//     under the earlier id with the CONCATENATED texts — so the texts are the editor's word (equality
//     against the sidecar's texts would refuse the engine's own merge) and only the author pair is
//     compared.
// Same hermetic harness as file-comments-host-save-guards.test.mjs: the synthetic `notes-api` world
// under a scratch directory, the script driven as the kernel drives it, changes recorded by the REAL
// vendored track-edit, and the editor's remap done with the engine's own calls.
// Run: node --test tools/file-comments-host-save-authors.test.mjs
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

import { writeTrackedPaths } from '../vendor/track-changents/store-io.mjs';
import { logPathFor } from './file-comments-host.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const HOST = path.join(REPO, 'tools', 'file-comments-host.mjs');
const VENDOR = path.join(REPO, 'vendor', 'track-changents');
const FIX = path.join(REPO, 'tests', 'fixtures', 'file_comments');
const engine = createRequire(import.meta.url)(path.join(VENDOR, 'engine.js'));

const SID = '11111111-2222-3333-4444-555555555555';
const OTHER = '22222222-3333-4444-5555-666666666666';   // another session's id, as synthetic as the first

let SCRATCH;
before(() => { SCRATCH = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-fc-host-authors-')); });
after(() => { try { fs.rmSync(SCRATCH, { recursive: true, force: true }); } catch { /* ignore */ } });

let worlds = 0;
function world() {
  const home = path.join(SCRATCH, `w${++worlds}`, 'home');
  const root = path.join(home, 'notes-api');
  fs.mkdirSync(path.join(root, '.git'), { recursive: true });
  fs.mkdirSync(path.join(root, 'docs'));
  fs.copyFileSync(path.join(FIX, 'report.md'), path.join(root, 'docs', 'report.md'));
  return { home, root, report: path.join(root, 'docs', 'report.md'), text: fs.readFileSync(path.join(FIX, 'report.md'), 'utf8') };
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
function cliOk(w, name, args) {
  const r = spawnSync(process.execPath, [path.join(VENDOR, 'cli', `track-${name}.mjs`), ...args],
    { encoding: 'utf8', env: env(w, { ROMP_SESSION_NAME: 'web', ROMP_SID: SID }) });
  assert.equal(r.status, 0, `track-${name} failed: ${r.stderr}`);
  return r;
}
function status(w, file) { return ok(w, { verb: 'status', path: file, args: {} }); }
function fenceFor(st) { return { storeMtimeNs: st.storeMtimeNs == null ? '' : st.storeMtimeNs }; }
function fileFenceFor(st) { return { ...fenceFor(st), fileMtimeNs: st.fileMtimeNs }; }
function edit(w, file, oldText, newText) {
  cliOk(w, 'edit', ['--file', file, '--old', oldText, '--new', newText]);
  return status(w, file);
}
function recordFor(st, id) {
  const s = st.store.suggestions.find((x) => String(x.id) === String(id));
  assert.ok(s, `no record ${id}`);
  return s;
}
function saveReq(file, st, content, suggestions, accepted, rejected) {
  return { verb: 'save', path: file, args: { content, suggestions, accepted: accepted || [], rejected: rejected || [] }, fence: fileFenceFor(st) };
}
// What the editor's field does when the person types: every record mapped through the change.
function typed(text, records, from, to, insert) {
  return { content: text.slice(0, from) + insert + text.slice(to), records: engine.ingestHumanChanges(records, [{ from, to, insert }]) };
}
function readSidecar(sp) { return JSON.parse(fs.readFileSync(sp, 'utf8')); }
function fileBytes(p) { try { return fs.readFileSync(p); } catch { return null; } }
function snapshot(file, storePath) {
  return { file, storePath, fileBytes: fileBytes(file), sidecar: fileBytes(storePath), log: fileBytes(logPathFor(storePath)) };
}
function untouched(before) {
  assert.deepEqual(fileBytes(before.file), before.fileBytes, 'the file is untouched');
  assert.deepEqual(fileBytes(before.storePath), before.sidecar, 'the sidecar is untouched');
  assert.deepEqual(fileBytes(before.storePath && logPathFor(before.storePath)), before.log, 'the log is untouched');
}
const who = (s) => [String(s.id), s.author, s.authorId];
const TAIL = ', so the records being saved are not that file\'s; nothing was changed — reload and retry';
const oneMsg = (id) => `change ${id} is not the change ~/notes-api/docs/report.md holds under that id (its author or session differs)${TAIL}`;
const manyMsg = (ids) => `changes ${ids.join(', ')} are not the changes ~/notes-api/docs/report.md holds under those ids (their author or session differs)${TAIL}`;

// ── a record under another author or session refuses ────────────────

test('a save whose record names another author or session than the sidecar\'s change refuses desync by id, names every such record in the caller\'s order, and writes nothing', () => {
  const w = world();
  writeTrackedPaths(w.root, ['docs/report.md']);
  const st = edit(w, w.report, 'cut p95 latency by 40%', 'reduced p95 latency by 35%');
  const cur = fs.readFileSync(w.report, 'utf8');
  const X = st.hunks[0];
  const rec = recordFor(st, X.id);
  assert.deepEqual(who(rec), [String(X.id), 'web', SID], 'the CLI recorded the change under the session');
  const before = snapshot(w.report, st.storePath);
  assert.equal(before.log, null, 'no comments log yet');
  // The finding's record: the session's own change, re-submitted with the file's own text at its
  // offset (so it fits), under another session's name and id, with an old text the session never
  // replaced and a ts of its own. The author pair is what refuses it; a refusal, not a crash, so the
  // viewer shows the reason and keeps the buffer.
  let r = refused(w, saveReq(w.report, st, cur, [{ ...rec, author: 'api', authorId: OTHER, oldText: 'PLANTED', ts: 1 }]), 'desync');
  assert.equal(r.error, oneMsg(X.id));
  assert.equal(r.error.includes(w.home), false);
  assert.equal(r.error.includes(OTHER), false, 'no session id in the text');
  assert.deepEqual(Object.keys(r).sort(), ['code', 'error', 'ok']);
  untouched(before);
  // Each half of the pair alone: another name under the same id; another id under the same name; no
  // id at all where the sidecar's record has one.
  r = refused(w, saveReq(w.report, st, cur, [{ ...rec, author: 'api' }]), 'desync');
  assert.equal(r.error, oneMsg(X.id));
  untouched(before);
  r = refused(w, saveReq(w.report, st, cur, [{ ...rec, authorId: OTHER }]), 'desync');
  assert.equal(r.error, oneMsg(X.id));
  untouched(before);
  const { authorId: dropped, ...noId } = rec;
  assert.equal(dropped, SID);
  r = refused(w, saveReq(w.report, st, cur, [noId]), 'desync');
  assert.equal(r.error, oneMsg(X.id));
  untouched(before);
  // Fragments are checked against the change they descend from. The person types inside the change:
  // the engine splits it into X and X~1 and copies the pair onto both. Planted on the fragment alone,
  // the fragment is named; on both, both, in the caller's order.
  const at = rec.from + 'reduced '.length;
  const split = typed(cur, [rec], at, at, 'the ');
  assert.deepEqual(split.records.map(who), [[String(X.id), 'web', SID], [`${X.id}~1`, 'web', SID]], 'the engine\'s split inherits the pair');
  const [left, right] = split.records;
  r = refused(w, saveReq(w.report, st, split.content, [left, { ...right, authorId: OTHER }]), 'desync');
  assert.equal(r.error, oneMsg(`${X.id}~1`));
  untouched(before);
  r = refused(w, saveReq(w.report, st, split.content, [{ ...right, author: 'api' }, { ...left, author: 'api' }]), 'desync');
  assert.equal(r.error, manyMsg([`${X.id}~1`, X.id]));
  untouched(before);
  // The editor's own re-mint of a fragment (X~2, editor-chunk's freshIds) is rooted in X by the prefix
  // rule alone and compared against X.
  r = refused(w, saveReq(w.report, st, split.content, [left, { ...right, id: `${X.id}~2`, author: 'api' }]), 'desync');
  assert.equal(r.error, oneMsg(`${X.id}~2`));
  untouched(before);
  // A misnamed record beside a decision refuses the whole save: nothing is logged, nothing decided.
  r = refused(w, saveReq(w.report, st, split.content, [{ ...left, author: 'api' }], [{ id: right.id, oldText: right.oldText, newText: right.newText }], []), 'desync');
  assert.equal(r.error, oneMsg(X.id));
  untouched(before);
  // Nothing the refusals claimed reached the disk: status lists the change under the session that
  // made it, with the old text the session replaced, no log exists, and the panel's Reject puts back
  // that text — never a planted one.
  const st2 = status(w, w.report);
  assert.deepEqual(st2.store.suggestions.map((s) => [...who(s), s.oldText]), [[String(X.id), 'web', SID, 'cut p95 latency by 40%']]);
  assert.deepEqual(st2.log, []);
  assert.deepEqual(st2.unsent, { comments: [], replies: [], accepted: 0, rejected: 0, watermark: null });
  assert.equal(fs.existsSync(logPathFor(st.storePath)), false, 'no log was created for a refused save');
  const rj = ok(w, { verb: 'reject-all', path: w.report, args: {}, fence: fileFenceFor(st2) });
  const text = fs.readFileSync(w.report, 'utf8');
  assert.ok(text.includes('cut p95 latency by 40%') && !text.includes('PLANTED'), 'the session\'s own old text is back');
  assert.deepEqual(rj.log.map((e) => e.kind), ['reject']);
  assert.deepEqual(rj.log[0].changes, [{ id: X.id, oldText: 'cut p95 latency by 40%', newText: 'reduced p95 latency by 35%' }]);
});

// ── the records a real editor derives still land ────────────────────

test('the records a real editor derives still land: a split fragment under its parent\'s author and session id, and two changes merged by a deletion between them under the earlier id with the concatenated texts', () => {
  // (a) Typing inside a change: X and X~1, both under the session's pair, save as pending; the
  // sidecar holds both under that pair.
  const w = world();
  writeTrackedPaths(w.root, ['docs/report.md']);
  const st = edit(w, w.report, 'cut p95 latency by 40%', 'reduced p95 latency by 35%');
  const cur = fs.readFileSync(w.report, 'utf8');
  const X = st.hunks[0];
  const rec = recordFor(st, X.id);
  const at = rec.from + 'reduced '.length;
  const split = typed(cur, st.store.suggestions, at, at, 'the ');
  const r1 = ok(w, saveReq(w.report, st, split.content, split.records));
  assert.equal(fs.readFileSync(w.report, 'utf8'), split.content);
  assert.deepEqual(readSidecar(st.storePath).suggestions.map(who), [[String(X.id), 'web', SID], [`${X.id}~1`, 'web', SID]]);
  assert.deepEqual(r1.hunks.map((h) => h.id), [X.id, `${X.id}~1`]);
  assert.deepEqual(r1.log.map((e) => e.kind), ['edit']);
  // (b) Two changes with text between them; the person deletes that text. The engine maps the second
  // onto the end of the first and coalesces them (same author, adjacent) into ONE record under the
  // first's id, its oldText and newText the two concatenated and its ts the earlier — a record whose
  // texts equal neither sidecar record's. It saves: the author pair is what the host compares, and
  // that pair is the first record's.
  const w2 = world();
  writeTrackedPaths(w2.root, ['docs/report.md']);
  edit(w2, w2.report, 'cut', 'reduced');
  const s2 = edit(w2, w2.report, 'after enabling', 'by enabling');
  const cur2 = fs.readFileSync(w2.report, 'utf8');
  assert.ok(cur2.includes('The api session reduced p95 latency by 40% by enabling the response cache.'));
  const [A, B] = [...s2.store.suggestions].sort((x, y) => x.from - y.from);
  assert.equal(s2.store.suggestions.length, 2);
  assert.deepEqual([A.oldText, A.newText, B.oldText, B.newText], ['cut', 'reduced', 'after enabling', 'by enabling']);
  const aEnd = A.from + A.newText.length;
  const merged = typed(cur2, s2.store.suggestions, aEnd, B.from, '');
  assert.equal(merged.records.length, 1, 'coalesced into one');
  const m = merged.records[0];
  assert.deepEqual(who(m), [String(A.id), 'web', SID]);
  assert.equal(m.oldText, 'cutafter enabling');
  assert.equal(m.newText, 'reducedby enabling');
  assert.notEqual(m.oldText, A.oldText, 'the merged texts equal no sidecar record\'s: an equality check would refuse the engine\'s own merge');
  assert.equal(m.ts, Math.min(A.ts, B.ts));
  const r2 = ok(w2, saveReq(w2.report, s2, merged.content, merged.records));
  assert.equal(fs.readFileSync(w2.report, 'utf8'), merged.content);
  assert.deepEqual(readSidecar(s2.storePath).suggestions.map((s) => [...who(s), s.oldText, s.newText]), [[String(A.id), 'web', SID, 'cutafter enabling', 'reducedby enabling']]);
  assert.deepEqual(r2.hunks.map((h) => h.id), [A.id]);
  assert.deepEqual(r2.log.map((e) => e.kind), ['edit']);
  // The merged record under another session's id is still refused: the pair is compared by root.
  const before = snapshot(w2.report, s2.storePath);
  const r3 = refused(w2, { ...saveReq(w2.report, r2, merged.content, [{ ...m, authorId: OTHER }]), fence: fileFenceFor(r2) }, 'desync');
  assert.equal(r3.error, oneMsg(A.id));
  untouched(before);
});

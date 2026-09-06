// Pins for tools/file-comments-host.mjs from the Slice 5 review (plans/file-review.md, Slice 5;
// Consent, trace, routing): the guards on the `save` verb's request and its target.
//   * The ledger of decisions is checked against the disk, not only its shape: an accepted or
//     rejected id must be rooted in a change the sidecar holds or the comments log already records
//     as decided (the id, or a `<id>~n` fragment of it); a ghost id refuses `no-change` by id and
//     nothing is written. Before this the host logged a client's ghost as a `reject` entry, counted
//     it in `unsent`, and the kernel told the session it had rejected a change it never made.
//   * The decisions a real editor produces still land: a split fragment (`X~1`) decided while the
//     other half stays pending; an id re-decided after an undo in an editor kept alive past a landed
//     save (the log reads accept, then reject); a fragment of a change the log alone remembers; and
//     the same after the earlier save pruned the sidecar.
//   * `save` takes no config fence, on purpose: it writes the sidecar and the file and fences on
//     both; config.json it only reads, at the save, to decide whether the edit is logged. The same
//     fence on set-tracked, the verb that writes config.json, refuses `config-moved`.
//   * A file past the text cap on disk is refused `too-large` on the stat, before its bytes are
//     read: a file past Node's 2 GiB read limit answers `too-large`, not `unreadable`, and one past
//     V8's string limit answers `too-large` instead of crashing the host.
// Same hermetic harness as file-comments-host-save.test.mjs: the synthetic `notes-api` world under a
// scratch directory, the script driven as the kernel drives it, changes recorded by the REAL vendored
// track-edit, and the editor's remap done with the engine's own calls.
// Run: node --test tools/file-comments-host-save-guards.test.mjs
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

import { storePathFor, saveStore, writeTrackedPaths } from '../vendor/track-changents/store-io.mjs';
import { statNs, logPathFor, applyEdits, human, TEXT_MAX_BYTES } from './file-comments-host.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const HOST = path.join(REPO, 'tools', 'file-comments-host.mjs');
const VENDOR = path.join(REPO, 'vendor', 'track-changents');
const FIX = path.join(REPO, 'tests', 'fixtures', 'file_comments');
const engine = createRequire(import.meta.url)(path.join(VENDOR, 'engine.js'));

const SID = '11111111-2222-3333-4444-555555555555';

let SCRATCH;
before(() => { SCRATCH = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-fc-host-guards-')); });
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
function crashed(w, req, re) {
  const r = host(w, req);
  assert.equal(r.code, 2, `expected a BadRequest crash, got exit ${r.code}: ${r.stdout}`);
  assert.match(r.stderr, re);
  assert.equal(r.stdout, '');
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
const decision = (h) => ({ id: h.id, oldText: h.oldText, newText: h.newText });
const ghost = (id) => ({ id, oldText: 'never there', newText: '' });
// What the editor's field does when the person types: every record mapped through the change.
function typed(text, records, from, to, insert) {
  return { content: text.slice(0, from) + insert + text.slice(to), records: engine.ingestHumanChanges(records, [{ from, to, insert }]) };
}
function readSidecar(sp) { return JSON.parse(fs.readFileSync(sp, 'utf8')); }
function fileBytes(p) { try { return fs.readFileSync(p); } catch { return null; } }
function readLogLines(lp) { return fs.readFileSync(lp, 'utf8').split('\n').filter(Boolean).map((l) => JSON.parse(l)); }
function snapshot(file, storePath) {
  return { file, storePath, fileBytes: fileBytes(file), sidecar: fileBytes(storePath), log: fileBytes(logPathFor(storePath)) };
}
function untouched(before) {
  assert.deepEqual(fileBytes(before.file), before.fileBytes, 'the file is untouched');
  assert.deepEqual(fileBytes(before.storePath), before.sidecar, 'the sidecar is untouched');
  assert.deepEqual(fileBytes(logPathFor(before.storePath)), before.log, 'the log is untouched');
}
const esc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

// ── the ledger is checked against the disk ──────────────────────────

test('a save whose ledger names a change the sidecar never held refuses no-change by id and writes nothing: no log entry, no count for the session or the Send', () => {
  const w = world();
  writeTrackedPaths(w.root, ['docs/report.md']);
  const st = edit(w, w.report, 'cut p95 latency by 40%', 'reduced p95 latency by 35%');
  const cur = fs.readFileSync(w.report, 'utf8');
  const X = st.hunks[0];
  const recs = st.store.suggestions;
  const before = snapshot(w.report, st.storePath);
  assert.equal(before.log, null, 'no comments log yet');
  // The finding's request: the file's own text, the sidecar's own records, and a rejected id that
  // never existed. A refusal (exit 0, ok:false), not a crash, so the panel shows the text.
  let r = refused(w, saveReq(w.report, st, cur, recs, [], [ghost('ghost-9')]), 'no-change');
  assert.equal(r.error, 'change ghost-9 is no longer pending in ~/notes-api/docs/report.md — reload and retry');
  assert.equal(r.error.includes(w.home), false);
  assert.deepEqual(Object.keys(r).sort(), ['code', 'error', 'ok']);
  untouched(before);
  // The same for accepted.
  r = refused(w, saveReq(w.report, st, cur, recs, [ghost('ghost-10')], []), 'no-change');
  assert.match(r.error, /^change ghost-10 is no longer pending/);
  untouched(before);
  // A ghost beside a real decision refuses the whole save, naming only the ghosts: the real
  // change stays pending, the ghosts are not logged.
  r = refused(w, saveReq(w.report, st, cur, [], [decision(X)], [ghost('ghost-1'), ghost('ghost-2')]), 'no-change');
  assert.match(r.error, /^changes ghost-1, ghost-2 are no longer pending in ~\/notes-api\/docs\/report\.md — reload and retry$/);
  assert.equal(r.error.includes(String(X.id)), false, 'the real decision is not named');
  untouched(before);
  // Nothing the ghosts claimed reaches the log-derived state: the next status counts nothing
  // decided, the log is empty, and the change is still pending in the sidecar.
  const st2 = status(w, w.report);
  assert.deepEqual(st2.unsent, { comments: [], replies: [], accepted: 0, rejected: 0, watermark: null });
  assert.deepEqual(st2.log, []);
  assert.equal(fs.existsSync(logPathFor(st.storePath)), false, 'no log was created for a refused save');
  assert.deepEqual(st2.hunks.map((h) => h.id), [X.id]);
  assert.deepEqual(readSidecar(st.storePath).suggestions.map((s) => s.id), [X.id]);
  // The boundary with the caller-bug crash the save suite pins: with NO sidecar and NO log nothing
  // was ever pending, so any decision is a malformed request (exit 2); once a sidecar or a log
  // exists, an unrooted id is the disk refusing, not the request's shape.
  const w2 = world();
  writeTrackedPaths(w2.root, ['docs/report.md']);
  const s0 = status(w2, w2.report);
  assert.equal(s0.storeMtimeNs, null);
  crashed(w2, saveReq(w2.report, s0, w2.text, [], [], [ghost('ghost-9')]), /no sidecar takes no accepted or rejected/);
  assert.equal(fs.existsSync(logPathFor(storePathFor(w2.root, w2.report))), false);
  assert.deepEqual(fileBytes(w2.report), Buffer.from(w2.text));
});

test('the decisions a real editor produces still land: a split fragment, a re-decision after a landed save, a fragment of a change only the log remembers, and the same after the sidecar was pruned', () => {
  // (a) The person types inside a change: the engine splits it into X (left) and X~1 (right), an
  // id the sidecar never held. Accepting X~1 while X stays pending saves.
  const w = world();
  writeTrackedPaths(w.root, ['docs/report.md']);
  let st = edit(w, w.report, 'cut p95 latency by 40%', 'reduced p95 latency by 35%');
  st = ok(w, { verb: 'comment', path: w.report, args: { note: 'Overall fine.' }, fence: fenceFor(st) });   // keeps the sidecar alive through (b)
  const cur = fs.readFileSync(w.report, 'utf8');
  const X = st.hunks[0];
  const rec = recordFor(st, X.id);
  const at = rec.from + 'reduced '.length;
  const split = typed(cur, [rec], at, at, 'the ');
  assert.deepEqual(split.records.map((s) => [s.id, s.newText]), [[X.id, 'reduced '], [`${X.id}~1`, 'p95 latency by 35%']], 'the engine\'s split');
  const acc = engine.acceptSuggestion(split.records, `${X.id}~1`).suggestions;
  assert.deepEqual(acc.map((s) => s.id), [X.id]);
  const frag = split.records[1];
  const r1 = ok(w, saveReq(w.report, st, split.content, acc, [decision({ id: frag.id, oldText: frag.oldText, newText: frag.newText })], []));
  assert.equal(fs.readFileSync(w.report, 'utf8'), split.content);
  assert.deepEqual(r1.log.map((e) => e.kind), ['edit', 'accept']);
  assert.deepEqual(r1.log[1].changes, [{ id: `${X.id}~1`, oldText: '', newText: 'p95 latency by 35%' }]);
  assert.deepEqual(readSidecar(st.storePath).suggestions.map((s) => [s.id, s.newText]), [[X.id, 'reduced ']]);
  assert.deepEqual(r1.hunks.map((h) => h.id), [X.id]);
  assert.equal(r1.unsent.accepted, 1);
  // (b) Undo past the landed save takes the typing and the accept back; the person then accepts X
  // itself, saves (the sidecar drops X), undoes THAT accept and rejects X instead. The second save
  // names an id the sidecar no longer holds; the log knows it, and afterwards reads accept, reject.
  const r2 = ok(w, { ...saveReq(w.report, r1, cur, [], [decision(X)], []), fence: fileFenceFor(r1) });
  assert.deepEqual(r2.store.suggestions, [], 'X accepted: gone from the sidecar');
  assert.equal(r2.store.comments.length, 1, 'the comment keeps the sidecar');
  assert.deepEqual(r2.log.map((e) => e.kind), ['edit', 'accept', 'edit', 'accept']);
  const rej = engine.rejectSuggestion([rec], X.id);
  const reverted = applyEdits(cur, [rej.edit]);
  assert.ok(reverted.includes('cut p95 latency by 40%') && !reverted.includes('reduced p95 latency by 35%'));
  const r3 = ok(w, { ...saveReq(w.report, r2, reverted, rej.suggestions, [], [decision(X)]), fence: fileFenceFor(r2) });
  assert.equal(fs.readFileSync(w.report, 'utf8'), reverted);
  assert.deepEqual(r3.log.map((e) => e.kind), ['edit', 'accept', 'edit', 'accept', 'edit', 'reject']);
  assert.deepEqual(r3.log[5].changes, [decision(X)]);
  assert.deepEqual(r3.store.suggestions, []);
  assert.equal(r3.unsent.accepted, 2);
  assert.equal(r3.unsent.rejected, 1);
  // (c) Undo the reject (the text and X come back), type inside X again and reject the fragment.
  // The editor's ledger already holds X~1, so its id rule re-mints the new fragment as X~2
  // (editor-chunk.ts freshIds): an id neither the sidecar nor the log has ever seen, rooted in X —
  // which only the log remembers now — by the `<id>~n` prefix rule alone.
  const again = typed(cur, [rec], at, at, 'the ');
  assert.equal(again.records[1].id, `${X.id}~1`, 'the engine alone mints X~1 again');
  again.records[1] = { ...again.records[1], id: `${X.id}~2` };
  const rejFrag = engine.rejectSuggestion(again.records, `${X.id}~2`);
  const content4 = applyEdits(again.content, [rejFrag.edit]);
  assert.deepEqual(rejFrag.suggestions.map((s) => [s.id, s.newText]), [[X.id, 'reduced ']]);
  assert.equal(content4.slice(rec.from, rec.from + 'reduced '.length), 'reduced ');
  const r4 = ok(w, { ...saveReq(w.report, r3, content4, rejFrag.suggestions, [], [{ id: `${X.id}~2`, oldText: '', newText: 'p95 latency by 35%' }]), fence: fileFenceFor(r3) });
  assert.equal(fs.readFileSync(w.report, 'utf8'), content4);
  assert.deepEqual(r4.log.map((e) => e.kind).slice(6), ['edit', 'reject']);
  assert.deepEqual(r4.log[7].changes[0].id, `${X.id}~2`);
  assert.deepEqual(readSidecar(st.storePath).suggestions.map((s) => s.id), [X.id], 'the left half is pending again, under its own id');
  assert.deepEqual(readLogLines(logPathFor(st.storePath)), r4.log);
  // A ghost beside these is still refused: the roots are the sidecar's and the log's ids, nothing else.
  const rg = refused(w, { ...saveReq(w.report, r4, content4, rejFrag.suggestions, [ghost('ghost-9')], []), fence: fileFenceFor(r4) }, 'no-change');
  assert.match(rg.error, /^change ghost-9 is no longer pending/);
  assert.deepEqual(readLogLines(logPathFor(st.storePath)), r4.log, 'nothing appended');
  // (d) The earlier save pruned the sidecar (nothing pending, no comment): the re-decision arrives
  // under a "" fence with no sidecar, and the log alone roots it — written and logged, no sidecar
  // minted. A ghost in that state refuses no-change, not the no-sidecar crash: something WAS pending.
  const w2 = world();
  writeTrackedPaths(w2.root, ['docs/report.md']);
  const s2 = edit(w2, w2.report, 'cut p95 latency by 40%', 'reduced p95 latency by 35%');
  const cur2 = fs.readFileSync(w2.report, 'utf8');
  const Y = s2.hunks[0];
  const recY = recordFor(s2, Y.id);
  const p1 = ok(w2, saveReq(w2.report, s2, cur2, [], [decision(Y)], []));
  assert.equal(p1.store, null, 'pruned');
  assert.equal(p1.storeMtimeNs, null);
  assert.equal(fs.existsSync(s2.storePath), false);
  const rejY = engine.rejectSuggestion([recY], Y.id);
  const revertedY = applyEdits(cur2, [rejY.edit]);
  const p2 = ok(w2, { ...saveReq(w2.report, p1, revertedY, [], [], [decision(Y)]), fence: { storeMtimeNs: '', fileMtimeNs: p1.fileMtimeNs } });
  assert.equal(fs.readFileSync(w2.report, 'utf8'), revertedY);
  assert.equal(p2.store, null, 'still no sidecar');
  assert.equal(fs.existsSync(s2.storePath), false);
  assert.deepEqual(p2.log.map((e) => e.kind), ['edit', 'accept', 'edit', 'reject']);
  assert.deepEqual(p2.log[3].changes, [decision(Y)]);
  assert.deepEqual(p2.unsent, { comments: [], replies: [], accepted: 1, rejected: 1, watermark: null });
  const g = refused(w2, { ...saveReq(w2.report, p2, revertedY, [], [], [ghost('ghost-9')]), fence: { storeMtimeNs: '', fileMtimeNs: p2.fileMtimeNs } }, 'no-change');
  assert.match(g.error, /^change ghost-9 is no longer pending/);
  assert.equal(fs.readFileSync(w2.report, 'utf8'), revertedY);
  assert.deepEqual(readLogLines(logPathFor(s2.storePath)), p2.log);
});

// ── no config fence, on purpose ─────────────────────────────────────

test('save takes no config fence: a stale configMtimeNs is not read and the log route is the disk\'s at the save; the same fence on set-tracked, which writes config.json, refuses config-moved', () => {
  const w = world();
  writeTrackedPaths(w.root, ['docs/report.md']);
  const st = status(w, w.report);
  assert.match(String(st.configMtimeNs), /^\d+$/);
  assert.notEqual(st.configMtimeNs, '1');
  // A config fence that can match nothing on disk: the save lands (fenced on the sidecar and the
  // file, the two things it writes), logged because the disk says tracked.
  const content = w.text + 'Appendix.\n';
  const r = ok(w, { ...saveReq(w.report, st, content, []), fence: { ...fileFenceFor(st), configMtimeNs: '1' } });
  assert.equal(fs.readFileSync(w.report, 'utf8'), content);
  assert.equal(r.logged, true);
  assert.deepEqual(r.log.map((e) => e.kind), ['edit']);
  // set-tracked with the same fence: the verb that writes config.json is the one fenced on it.
  const moved = refused(w, { verb: 'set-tracked', path: w.report, args: { on: false }, fence: { configMtimeNs: '1' } }, 'config-moved');
  assert.match(moved.error, /the tracking setting for ~\/notes-api\/docs\/report\.md changed on disk/);
  assert.deepEqual(status(w, w.report).trackedBy, { kind: 'file', entry: 'docs/report.md' }, 'the toggle changed nothing');
  // The window the fence would not close either: the flag leaves config.json under an edit (a hand
  // edit; no entry on this file's log), and the save fenced on the status at Edit — its config
  // fence correct THEN — is written from the disk's state: not logged, no log created. A config
  // fence would only have refused once and, with the records unchanged, been retried to the same
  // outcome; the host reads the disk rather than the client's memory of it.
  const w2 = world();
  writeTrackedPaths(w2.root, ['docs/report.md']);
  const atEdit = status(w2, w2.report);
  assert.deepEqual(atEdit.trackedBy, { kind: 'file', entry: 'docs/report.md' });
  writeTrackedPaths(w2.root, []);
  assert.notEqual(statNs(path.join(w2.root, '.trackchanges', 'config.json')), atEdit.configMtimeNs, 'the config moved');
  const r2 = ok(w2, { ...saveReq(w2.report, atEdit, w2.text + 'Appendix.\n', []), fence: { ...fileFenceFor(atEdit), configMtimeNs: atEdit.configMtimeNs } });
  assert.equal(fs.readFileSync(w2.report, 'utf8'), w2.text + 'Appendix.\n');
  assert.equal(r2.logged, false);
  assert.deepEqual(r2.log, []);
  assert.equal(r2.trackedBy, null);
  assert.equal(fs.existsSync(logPathFor(storePathFor(w2.root, w2.report))), false, 'no log for a file nobody tracks');
});

// ── too-large on the stat, before the read ──────────────────────────

// A sparse file: the size the stat reports without the blocks behind it, so a file past every
// read limit costs nothing to make. Probed first with 64 MiB; a filesystem that allocates the
// bytes instead (no sparse support) skips the case rather than writing gigabytes.
function sparseOk(dir) {
  const probe = path.join(dir, 'sparse-probe');
  fs.writeFileSync(probe, '');
  fs.truncateSync(probe, 64 * 1024 * 1024);
  const st = fs.statSync(probe);
  fs.unlinkSync(probe);
  return st.size === 64 * 1024 * 1024 && Number(st.blocks) * 512 < 1024 * 1024;
}
function sparse(p, size) {
  fs.writeFileSync(p, '');
  fs.truncateSync(p, size);
  assert.equal(fs.statSync(p).size, size);
}

test('save and reject refuse too-large on the stat, before the file is read: a file past Node\'s 2 GiB read limit answers too-large (not unreadable), one past V8\'s string limit answers too-large (no crash), and nothing is written', (t) => {
  const w = world();
  if (!sparseOk(path.join(w.root, 'docs'))) { t.skip('this filesystem does not hold sparse files'); return; }
  writeTrackedPaths(w.root, ['docs/']);
  // Past Node's readFileSync limit: read first, the host answered `unreadable` with Node's own
  // "greater than 2 GiB" text for a file whose size the stat already refused.
  const huge = path.join(w.root, 'docs', 'huge.md');
  const HUGE = 2306867200;
  sparse(huge, HUGE);
  const s0 = status(w, huge);                                   // status stats (no sidecar): the same door, no read
  assert.deepEqual(s0.trackedBy, { kind: 'folder', entry: 'docs/' });
  const r = refused(w, saveReq(huge, s0, 'tiny\n', []), 'too-large');
  assert.equal(r.error, `cannot save ~/notes-api/docs/huge.md: the file on disk is ${human(HUGE)}, past the ${human(TEXT_MAX_BYTES)} text cap the viewer loads; nothing was changed`);
  assert.equal(r.error.includes('GiB'), false, 'not Node\'s read-limit text');
  assert.equal(fs.statSync(huge).size, HUGE, 'the file is untouched');
  assert.equal(fs.existsSync(logPathFor(storePathFor(w.root, huge))), false);
  // Between V8's string limit and Node's read limit: read first, the host crashed (exit 1,
  // ERR_STRING_TOO_LONG, the kernel's host-error) after loading the bytes.
  const big = path.join(w.root, 'docs', 'big.md');
  const BIG = 600 * 1024 * 1024;
  sparse(big, BIG);
  const s1 = status(w, big);
  const r1 = refused(w, saveReq(big, s1, 'tiny\n', []), 'too-large');
  assert.equal(r1.error, `cannot save ~/notes-api/docs/big.md: the file on disk is ${human(BIG)}, past the ${human(TEXT_MAX_BYTES)} text cap the viewer loads; nothing was changed`);
  assert.equal(fs.statSync(big).size, BIG);
  // reject and reject-all take the same door. A sidecar exists here (the realistic case), but the
  // refusal comes before it is consulted: the fence values are whatever the disk says.
  const sp = storePathFor(w.root, huge);
  saveStore(w.root, sp, { v: 3, path: 'docs/huge.md', suggestions: [], comments: [] }, '');
  const sidecar = fileBytes(sp);
  const fence = { storeMtimeNs: statNs(sp), fileMtimeNs: statNs(huge) };
  const r2 = refused(w, { verb: 'reject-all', path: huge, args: {}, fence }, 'too-large');
  assert.equal(r2.error, `cannot write ~/notes-api/docs/huge.md: the file on disk is ${human(HUGE)}, past the ${human(TEXT_MAX_BYTES)} text cap the viewer loads; nothing was changed`);
  const r3 = refused(w, { verb: 'reject', path: huge, args: { ids: ['1700000000000-0'] }, fence }, 'too-large');
  assert.equal(r3.code, 'too-large');
  assert.deepEqual(fileBytes(sp), sidecar, 'the sidecar is untouched');
  assert.equal(fs.statSync(huge).size, HUGE);
  assert.equal(fs.existsSync(logPathFor(sp)), false);
  // The sidecar-only verbs read the file whole as the CLIs do (the plan: every verb reads the file
  // as text; too-large is for the verbs that write it), so the door is theirs to answer as before:
  // this pins that the stat-first refusal is scoped to the writing verbs and did not widen.
  const a = host(w, { verb: 'accept-all', path: huge, args: {}, fence: { storeMtimeNs: statNs(sp) } });
  assert.equal(a.code, 0);
  assert.equal(a.json && a.json.ok, false);
  assert.notEqual(a.json.code, 'too-large', 'accept-all is not a writing verb and does not refuse on the size');
});

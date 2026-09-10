// The about follow-on (plans/file-review.md, "The about follow-on (2026-09-10)" under Slice 2; decision 45) at the
// host: a comment names the changes it is about with `changeIds`, the person's own pick, stored as the third romp-only
// additive field after `target` and `anchorAt` (docs/adr/0002). Pinned here, over the real host script as a child
// process and the real vendored CLIs where the plan asks for them:
//   * `comment` takes `changeIds` with an anchor (a passage comment about the changes its selection overlaps) and
//     without one (Comment on this change on a deletion, whose text is not in the file): the object's shape and key
//     order, the id rule (the anchor's offset; the first named change's current offset with no anchor), the ids kept
//     as strings, once each;
//   * every id must name a change the sidecar holds, pending or detached; a request naming one it does not refuses
//     `no-change` with the missing ids alone in the line, and writes nothing;
//   * the old request branch is gone: `suggestionId` in a request is a caller bug (exit 2, a plain sentence), as is a
//     `changeIds` of the wrong shape; romp never writes `suggestionId`;
//   * a stored `suggestionId` is still READ, as the change that answered the comment (a sidecar from before this
//     follow-on, or one `track-edit --thread` wrote): `decidedFor` collects it beside every `changeIds` entry, so a
//     comment about an accepted change keeps the change's texts from the log;
//   * the field survives the vendored CLIs (track-reply writes the object back whole) and every decision (accept
//     leaves the comment as loaded: requireCommentsUntouched).
// Hermetic: the synthetic notes-api world under a scratch directory (tests/fixtures/file_comments/), as the sibling
// modules build it. Run: node --test tools/file-comments-host-about.test.mjs
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

import { storePathFor } from '../vendor/track-changents/store-io.mjs';
import { decidedFor, logPathFor } from './file-comments-host.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const HOST = path.join(REPO, 'tools', 'file-comments-host.mjs');
const VENDOR = path.join(REPO, 'vendor', 'track-changents');
const FIX = path.join(REPO, 'tests', 'fixtures', 'file_comments');
const engine = createRequire(import.meta.url)(path.join(VENDOR, 'engine.js'));

const SID = '11111111-2222-3333-4444-555555555555';

let SCRATCH;
before(() => { SCRATCH = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-fc-about-')); });
after(() => { try { fs.rmSync(SCRATCH, { recursive: true, force: true }); } catch { /* ignore */ } });

// ── the world (the main module's, copied) ───────────────────────────
let worlds = 0;
function world() {
  const home = path.join(SCRATCH, `w${++worlds}`, 'home');
  const root = path.join(home, 'notes-api');
  fs.mkdirSync(path.join(root, '.git'), { recursive: true });
  fs.mkdirSync(path.join(root, 'docs'));
  fs.copyFileSync(path.join(FIX, 'report.md'), path.join(root, 'docs', 'report.md'));
  fs.copyFileSync(path.join(FIX, 'index.md'), path.join(root, 'index.md'));
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
  return r.json;
}
/** A caller bug: the host exits 2 with one line on stderr and nothing on stdout. */
function bug(w, req, re) {
  const r = host(w, req);
  assert.equal(r.code, 2, `a caller bug exits 2; got ${r.code}: ${r.stderr}`);
  assert.equal(r.stdout, '');
  assert.match(r.stderr, re);
  return r;
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
function status(w, file) { return ok(w, { verb: 'status', path: file, args: {} }); }
function fenceFor(st) { return { storeMtimeNs: st.storeMtimeNs == null ? '' : st.storeMtimeNs }; }
function edit(w, file, oldText, newText) {
  cliOk(w, 'edit', ['--file', file, '--old', oldText, '--new', newText]);
  return status(w, file);
}
function hunkFor(st, oldText) {
  const h = st.hunks.find((x) => x.oldText === oldText);
  assert.ok(h, `no hunk with oldText ${JSON.stringify(oldText)}`);
  return h;
}
function anchorAt(text, quote) {
  const i = text.indexOf(quote);
  assert.ok(i >= 0, `fixture lacks ${JSON.stringify(quote)}`);
  return { anchor: engine.makeAnchor(text, i, i + quote.length), hintOffset: i, idx: i };
}
function comment(w, file, st, args) { return ok(w, { verb: 'comment', path: file, args, fence: fenceFor(st) }); }
function accept(w, file, st, ids) { return ok(w, { verb: 'accept', path: file, args: { ids }, fence: fenceFor(st) }); }
function readSidecar(sp) { return JSON.parse(fs.readFileSync(sp, 'utf8')); }
const fileBytes = (p) => { try { return fs.readFileSync(p); } catch { return null; } };

// ── the field ───────────────────────────────────────────────────────

test('comment {anchor, changeIds}: a passage comment about the changes its selection overlaps, the field after anchorAt, the ids as strings once each', () => {
  const w = world();
  edit(w, w.report, 'cut p95 latency by 40%', 'reduced p95 latency by 40%');
  const st = edit(w, w.report, 'shipping the cache in v1.2', 'shipping the cache in v1.3');
  const a = hunkFor(st, 'cut p95 latency by 40%'), b = hunkFor(st, 'shipping the cache in v1.2');
  const cur = fs.readFileSync(w.report, 'utf8');
  const sel = anchorAt(cur, 'reduced p95 latency');
  const r = comment(w, w.report, st, { anchor: sel.anchor, hintOffset: sel.hintOffset, changeIds: [a.id, b.id, a.id], note: '  Both of these read as one claim.  ' });
  const c = readSidecar(r.storePath).comments[0];
  assert.deepEqual(Object.keys(c), ['id', 'author', 'ts', 'anchor', 'anchorAt', 'changeIds', 'body', 'replies', 'resolved'], 'the third additive field, after the anchor and its position');
  assert.deepEqual(c.changeIds, [String(a.id), String(b.id)], 'as strings, once each, in the order named');
  assert.equal(c.anchorAt, sel.idx);
  assert.equal(c.id, `${c.ts}-${sel.idx}`, 'a passage comment keeps the passage id rule');
  assert.equal(c.author, 'you');
  assert.equal(c.body, 'Both of these read as one claim.');
  assert.deepEqual(c.replies, []);
  assert.equal(c.resolved, false);
  assert.equal('suggestionId' in c, false, 'romp never writes suggestionId');
  assert.deepEqual(r.store.comments[0], c, 'the reply is the sidecar as written');
  assert.deepEqual(r.unsent.comments, [c.id]);
  assert.equal(r.hunks.length, 2, 'the changes stay pending: a comment decides nothing');
  assert.deepEqual(r.decided, {}, 'nothing to remember while both are in the sidecar');
});

test('comment {changeIds} with no anchor: a comment about a change whose text is not in the file (a deletion), its id from the first named change\'s current offset', () => {
  const w = world();
  const st = edit(w, w.report, 'remain ', '');   // a deletion: a point in the text, nothing to select
  assert.equal(st.hunks.length, 1);
  const d = st.hunks[0];
  assert.equal(d.kind, 'del');
  const r = comment(w, w.report, st, { changeIds: [d.id], note: 'Why drop the word?' });
  const c = readSidecar(r.storePath).comments[0];
  assert.deepEqual(Object.keys(c), ['id', 'author', 'ts', 'changeIds', 'body', 'replies', 'resolved']);
  assert.deepEqual(c.changeIds, [d.id]);
  assert.equal(c.id, `${c.ts}-${d.curFrom}`, 'the change\'s point names the place, where the other hosts put a comment whose suggestionId names the change');
  assert.equal('anchor' in c, false);
  assert.equal('anchorAt' in c, false);
  assert.equal('target' in c, false);
});

test('a detached change can be named too: the sidecar holds it, unplaced, and the comment takes its last place for the id', () => {
  const w = world();
  const st = edit(w, w.report, 'cut p95 latency by 40%', 'reduced p95 latency by 40%');
  const sp = storePathFor(w.root, w.report);
  const disk = readSidecar(sp);
  disk.detached = [{ id: '1700000000000-9', author: 'web', ts: 1700000000000, kind: 'sub', from: 7, oldText: 'zzz', newText: 'qqq', anchor: { quote: 'qqq', prefix: '', suffix: '' } }];
  fs.writeFileSync(sp, JSON.stringify(disk, null, 2));
  const st2 = status(w, w.report);
  assert.equal(st2.store.detached.length, 1);
  assert.equal(st2.hunks.length, 1, 'a detached op is not a pending change');
  const r = comment(w, w.report, st2, { changeIds: ['1700000000000-9', st.hunks[0].id], note: 'Where did this text go?' });
  const c = r.store.comments[0];
  assert.deepEqual(c.changeIds, ['1700000000000-9', st.hunks[0].id]);
  assert.equal(c.id, `${c.ts}-7`, 'the first named change is the detached one, at its last place');
  assert.deepEqual(r.decided, {}, 'a detached change is the sidecar\'s to describe, never the log\'s');
});

// ── the refusals ────────────────────────────────────────────────────

test('an id naming no pending or detached change refuses no-change with the missing ids alone, and writes nothing', () => {
  const w = world();
  const st = edit(w, w.report, 'cut p95 latency by 40%', 'reduced p95 latency by 40%');
  const id = st.hunks[0].id;
  const bytes = fileBytes(st.storePath);
  let r = refused(w, { verb: 'comment', path: w.report, args: { changeIds: ['nope'], note: 'hi' }, fence: fenceFor(st) }, 'no-change');
  assert.ok(r.error.includes('nope') && r.error.includes('~/notes-api/docs/report.md'), r.error);
  r = refused(w, { verb: 'comment', path: w.report, args: { changeIds: [id, 'nope', 'gone'], note: 'hi' }, fence: fenceFor(st) }, 'no-change');
  assert.ok(r.error.includes('nope') && r.error.includes('gone') && !r.error.includes(id), 'the missing ids alone: ' + r.error);
  assert.match(r.error, /^changes nope, gone are no longer pending in /, 'one plain line');
  const cur = fs.readFileSync(w.report, 'utf8');
  const sel = anchorAt(cur, 'reduced p95 latency');
  refused(w, { verb: 'comment', path: w.report, args: { anchor: sel.anchor, hintOffset: sel.hintOffset, changeIds: ['nope'], note: 'hi' }, fence: fenceFor(st) }, 'no-change');
  assert.deepEqual(fileBytes(st.storePath), bytes, 'nothing written');
  assert.equal(fs.existsSync(logPathFor(st.storePath)), false);
  assert.deepEqual(status(w, w.report).store.comments, []);
  // an accepted change is no longer pending under its id
  const r1 = accept(w, w.report, st, [id]);
  r = refused(w, { verb: 'comment', path: w.report, args: { changeIds: [id], note: 'Again?' }, fence: fenceFor(r1) }, 'no-change');
  assert.ok(r.error.includes(id), r.error);
  // and with no sidecar at all every id is missing
  const w2 = world();
  refused(w2, { verb: 'comment', path: w2.report, args: { changeIds: ['x'], note: 'hi' }, fence: { storeMtimeNs: '' } }, 'no-change');
  assert.equal(fs.existsSync(path.join(w2.root, '.trackchanges')), false, 'a refused comment creates nothing');
});

test('the old request branch is gone: suggestionId in a request is a caller bug, a plain sentence, nothing written; so is a changeIds of the wrong shape', () => {
  const w = world();
  const st = edit(w, w.report, 'cut p95 latency by 40%', 'reduced p95 latency by 40%');
  const id = st.hunks[0].id;
  const bytes = fileBytes(st.storePath);
  const r = bug(w, { verb: 'comment', path: w.report, args: { suggestionId: id, note: 'n' }, fence: fenceFor(st) }, /suggestionId is not accepted: a comment names the changes it is about with changeIds/);
  assert.equal(r.stderr.split('\n')[0], 'file-comments-host: BadRequest: suggestionId is not accepted: a comment names the changes it is about with changeIds', 'the first line is the plain sentence');
  bug(w, { verb: 'comment', path: w.report, args: { suggestionId: id, changeIds: [id], note: 'n' }, fence: fenceFor(st) }, /suggestionId is not accepted/);
  bug(w, { verb: 'comment', path: w.report, args: { changeIds: id, note: 'n' }, fence: fenceFor(st) }, /changeIds must be a non-empty array of change ids/);
  bug(w, { verb: 'comment', path: w.report, args: { changeIds: [], note: 'n' }, fence: fenceFor(st) }, /changeIds must be a non-empty array of change ids/);
  bug(w, { verb: 'comment', path: w.report, args: { changeIds: [id, ''], note: 'n' }, fence: fenceFor(st) }, /every change id in changeIds must be a non-empty string/);
  bug(w, { verb: 'comment', path: w.report, args: { changeIds: [{ id }], note: 'n' }, fence: fenceFor(st) }, /every change id in changeIds must be a non-empty string/);
  assert.deepEqual(fileBytes(st.storePath), bytes, 'nothing written');
  assert.deepEqual(status(w, w.report).store.comments, []);
});

// ── the read side: decided, the CLIs, the decisions ─────────────────

test('decidedFor collects the changes a comment names in changeIds and the legacy suggestionId alike, for the ones the sidecar no longer holds', () => {
  const entries = [
    { kind: 'reject', changes: [{ id: 'x', oldText: 'a', newText: '' }] },
    { kind: 'accept', changes: [{ id: 'x', oldText: 'a', newText: 'b' }, { id: 'y', oldText: '', newText: 'n' }, { id: 'z', oldText: 'q', newText: '' }] },
  ];
  const about = (ids, extra = {}) => ({ id: 'c1', author: 'you', ts: 1, body: 'k', changeIds: ids, replies: [], resolved: false, ...extra });
  const legacy = (id) => ({ id: 'c2', author: 'you', ts: 2, body: 'k', suggestionId: id, replies: [], resolved: false });
  assert.deepEqual(decidedFor({ suggestions: [], comments: [about(['x', 'y'])] }, entries),
    { x: { decision: 'accepted', oldText: 'a', newText: 'b' }, y: { decision: 'accepted', oldText: '', newText: 'n' } }, 'every named change, the NEWEST entry each');
  assert.deepEqual(decidedFor({ suggestions: [{ id: 'x' }], comments: [about(['x', 'y'])] }, entries), { y: { decision: 'accepted', oldText: '', newText: 'n' } }, 'a pending one is the sidecar\'s');
  assert.deepEqual(decidedFor({ suggestions: [], detached: [{ id: 'y' }], comments: [about(['x', 'y'])] }, entries), { x: { decision: 'accepted', oldText: 'a', newText: 'b' } }, 'a detached one too');
  assert.deepEqual(decidedFor({ suggestions: [], comments: [about(['x']), legacy('z')] }, entries),
    { x: { decision: 'accepted', oldText: 'a', newText: 'b' }, z: { decision: 'accepted', oldText: 'q', newText: '' } }, 'both fields read, on the same sidecar');
  assert.deepEqual(decidedFor({ suggestions: [], comments: [about(['x'], { suggestionId: 'z' })] }, entries),
    { x: { decision: 'accepted', oldText: 'a', newText: 'b' }, z: { decision: 'accepted', oldText: 'q', newText: '' } }, 'and both on one comment');
  assert.deepEqual(decidedFor({ suggestions: [], comments: [about(['w'])] }, entries), {}, 'no entry for the id: nothing claimed');
  assert.deepEqual(decidedFor({ suggestions: [], comments: [about(['', null, 7])] }, [{ kind: 'accept', changes: [{ id: 7, oldText: 'a', newText: 'b' }] }]),
    { 7: { decision: 'accepted', oldText: 'a', newText: 'b' } }, 'read defensively: an empty or null id claims nothing, a numeric one matches by string');
  assert.deepEqual(decidedFor({ suggestions: [], comments: [{ id: 'c3', author: 'you', ts: 3, body: 'k', changeIds: 'x', replies: [], resolved: false }] }, entries), {}, 'a hand-edited field of the wrong shape claims nothing');
});

test('over the wire: a comment about a change keeps the change\'s texts through accept (`decided`), survives track-reply, and accept leaves it as loaded', () => {
  const w = world();
  const st = edit(w, w.report, 'cut p95 latency by 40%', 'reduced p95 latency by 40%');
  const h = st.hunks[0];
  const r = comment(w, w.report, st, { changeIds: [h.id], note: 'Say cut, not reduced.' });
  const c = r.store.comments[0];
  // the session answers in words: the CLI loads and saves the whole object, the field with it
  cliOk(w, 'reply', ['--file', w.report, '--thread', c.id, '--note', 'Kept as cut.']);
  const after = readSidecar(r.storePath).comments[0];
  assert.deepEqual({ ...after, replies: [] }, c, 'the field survives the CLI\'s write');
  assert.equal(after.replies.length, 1);
  assert.equal(after.replies[0].author, 'web');
  // accept drops the change and leaves the comment as loaded, the field included, open
  const st2 = status(w, w.report);
  const r2 = accept(w, w.report, st2, [h.id]);
  assert.deepEqual(r2.accepted, [h.id]);
  assert.deepEqual(r2.hunks, []);
  assert.ok(fs.existsSync(r2.storePath), 'a comment keeps the sidecar');
  const disk = readSidecar(r2.storePath);
  assert.deepEqual(disk.comments, [after], 'as loaded, field for field');
  assert.equal(disk.comments[0].resolved, false, 'a decision never resolves a comment (decision 42)');
  assert.deepEqual(disk.comments[0].changeIds, [h.id]);
  assert.deepEqual(r2.decided, { [h.id]: { decision: 'accepted', oldText: 'cut p95 latency by 40%', newText: 'reduced p95 latency by 40%' } }, 'the texts ride `decided` the moment the sidecar drops the change');
  assert.deepEqual(status(w, w.report).decided, r2.decided);
  // …and track-reply still reaches the comment after the accept
  cliOk(w, 'reply', ['--file', w.report, '--thread', c.id, '--note', 'Thanks.']);
  assert.equal(readSidecar(r2.storePath).comments[0].replies.length, 2);
});

// Decision 42's self-check in tools/file-comments-host.mjs: a decision — accept, accept-all, reject,
// reject-all, and the decisions a save carries from the editor — never touches a comment, and
// requireCommentsUntouched holds the sidecar a decision STAGES to the comments as loaded, field for
// field apart from `anchorAt`, on the staged bytes read back before the rename that lands them. The
// seen slice's review (2026-09-09) found the first version checking before the stage, so it compared
// the store with itself and could refuse nothing; these tests drive the exported pieces (a real stage
// into a scratch project, then a comment changed in every way a regression could change one), the
// carve-out (a refresh that adds or moves anchorAt is not a change), the ordering (a check on a store
// nothing has staged throws), and the verbs end to end (a stale anchorAt refreshed by an accept-all, a
// reject-all and a save, each leaving every other field as loaded and refusing nothing). Same hermetic
// harness as file-comments-host.test.mjs: the synthetic `notes-api` world under a scratch directory,
// the script driven as the kernel drives it, changes recorded by the REAL vendored track-edit.
// Run: node --test tools/file-comments-host-untouched.test.mjs
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

import { storePathFor, loadStore, saveStore, writeTrackedPaths } from '../vendor/track-changents/store-io.mjs';
import {
  commentsApartFromAnchorAt, requireCommentsUntouched, stageSidecar, discardSidecar, Refusal,
} from './file-comments-host.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const HOST = path.join(REPO, 'tools', 'file-comments-host.mjs');
const VENDOR = path.join(REPO, 'vendor', 'track-changents');
const FIX = path.join(REPO, 'tests', 'fixtures', 'file_comments');
const engine = createRequire(import.meta.url)(path.join(VENDOR, 'engine.js'));

const SID = '11111111-2222-3333-4444-555555555555';

let SCRATCH;
before(() => { SCRATCH = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-fc-host-untouched-')); });
after(() => { try { fs.rmSync(SCRATCH, { recursive: true, force: true }); } catch { /* ignore */ } });

// ── the world (file-comments-host.test.mjs) ─────────────────────────
let worlds = 0;
function world() {
  const home = path.join(SCRATCH, `w${++worlds}`, 'home');
  const root = path.join(home, 'notes-api');
  fs.mkdirSync(path.join(root, '.git'), { recursive: true });
  fs.mkdirSync(path.join(root, 'docs'));
  fs.copyFileSync(path.join(FIX, 'report.md'), path.join(root, 'docs', 'report.md'));
  fs.copyFileSync(path.join(FIX, 'index.md'), path.join(root, 'index.md'));
  return {
    home, root,
    report: path.join(root, 'docs', 'report.md'),
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
function fileFenceFor(st) { return { ...fenceFor(st), fileMtimeNs: st.fileMtimeNs }; }
function comment(w, file, st, args) { return ok(w, { verb: 'comment', path: file, args, fence: fenceFor(st) }); }
function acceptAll(w, file, st) { return ok(w, { verb: 'accept-all', path: file, args: {}, fence: fenceFor(st) }); }
function rejectAll(w, file, st) { return ok(w, { verb: 'reject-all', path: file, args: {}, fence: fileFenceFor(st) }); }
function save(w, file, st, content, suggestions, accepted, rejected) {
  return ok(w, { verb: 'save', path: file, args: { content, suggestions, accepted: accepted || [], rejected: rejected || [] }, fence: fileFenceFor(st) });
}
function edit(w, file, oldText, newText) {
  cliOk(w, 'edit', ['--file', file, '--old', oldText, '--new', newText]);
  return status(w, file);
}
function hunkFor(st, oldText) {
  const h = st.hunks.find((x) => x.oldText === oldText);
  assert.ok(h, `no hunk with oldText ${JSON.stringify(oldText)} among ${JSON.stringify(st.hunks.map((x) => x.oldText))}`);
  return h;
}
const decision = (h) => ({ id: h.id, oldText: h.oldText, newText: h.newText });
// What the editor's field does when the person types: every record mapped through the change.
function typed(text, records, from, to, insert) {
  return { content: text.slice(0, from) + insert + text.slice(to), records: engine.ingestHumanChanges(records, [{ from, to, insert }]) };
}
// The anchor the browser would build from a selection, plus the selection's start as the hint.
function anchorAt(text, quote, nth) {
  let i = -1;
  for (let k = 0; k <= (nth || 0); k++) i = text.indexOf(quote, i + 1);
  assert.ok(i >= 0, `fixture lacks occurrence ${nth} of ${JSON.stringify(quote)}`);
  return { anchor: engine.makeAnchor(text, i, i + quote.length), hintOffset: i, idx: i };
}
function readSidecar(sp) { return JSON.parse(fs.readFileSync(sp, 'utf8')); }
const byId = (cs, id) => cs.find((c) => c.id === id);
const apart = commentsApartFromAnchorAt;

// ── the pieces ──────────────────────────────────────────────────────

test('commentsApartFromAnchorAt: anchorAt added, moved or removed reads the same; any other difference — a field, a reply, the count, the order — does not', () => {
  const a = { id: 'c1', author: 'you', ts: 1, anchor: { quote: 'cut p95 latency by 40%', prefix: 'The api session ', suffix: ' after enabling the r' }, anchorAt: 40, body: 'Say reduced.', replies: [], resolved: false };
  const b = { id: 'c2', author: 'you', ts: 2, suggestionId: 'x1', body: 'Keep the number.', replies: [], resolved: false };
  const { anchorAt: _at, ...noAt } = a;   // eslint-disable-line no-unused-vars
  assert.equal(apart([a, b]), apart([{ ...a, anchorAt: 57 }, b]), 'moved');
  assert.equal(apart([a, b]), apart([noAt, b]), 'removed');
  assert.equal(apart([noAt, b]), apart([{ ...noAt, anchorAt: 3 }, b]), 'added, wherever the key lands');
  assert.equal(apart([noAt, { ...b, anchorAt: 0 }]), apart([noAt, b]), 'on a comment that never had one');
  const changed = [
    ['resolved', { ...b, resolved: true }],
    ['the body', { ...b, body: 'Keep the number!' }],
    ['the binding', (() => { const { suggestionId: _s, ...rest } = b; return rest; })()],   // eslint-disable-line no-unused-vars
    ['the author', { ...b, author: 'web' }],
    ['the time', { ...b, ts: 3 }],
    ['a reply', { ...b, replies: [{ author: 'web', ts: 4, kind: 'note', note: 'Done.' }] }],
    ['a field added', { ...b, sent: true }],
  ];
  for (const [what, b2] of changed) assert.notEqual(apart([a, b]), apart([a, b2]), what);
  assert.notEqual(apart([a, b]), apart([{ ...a, anchor: { ...a.anchor, quote: 'CUT p95 latency by 40%' } }, b]), 'the anchor itself');
  assert.notEqual(apart([a, b]), apart([b, a]), 'the order');
  assert.notEqual(apart([a, b]), apart([a]), 'a comment dropped');
  assert.notEqual(apart([a, b]), apart([a, b, { id: 'c3', body: 'New.' }]), 'a comment added');
  // The empty and the malformed pass through; the check compares strings, so both sides agree.
  assert.equal(apart(undefined), '[]');
  assert.equal(apart([]), '[]');
  assert.equal(apart([null, 7]), '[null,7]');
});

// A project the exported stage can write into: the fixture text, one sidecar with four comments in
// the shapes the host and the CLIs write (comment key order as file-comments-host-anchors pins it):
// a passage comment whose anchorAt is STALE (three short of where its passage sits), a passage
// comment the CLI wrote (no anchorAt at all), a change comment bound by suggestionId, and a
// whole-file comment.
let projects = 0;
function project() {
  const root = path.join(SCRATCH, `p${++projects}`);
  fs.mkdirSync(path.join(root, 'docs'), { recursive: true });
  const file = path.join(root, 'docs', 'report.md');
  const text = fs.readFileSync(path.join(FIX, 'report.md'), 'utf8');
  fs.writeFileSync(file, text);
  const cut = anchorAt(text, 'cut p95 latency by 40%', 0);
  const cold = anchorAt(text, 'Cold starts remain slow', 0);
  const comments = [
    { id: 'c1', author: 'you', ts: 1, anchor: cut.anchor, anchorAt: cut.idx - 3, body: 'Say reduced.', replies: [], resolved: false },
    { id: 'c2', author: 'web', ts: 2, anchor: cold.anchor, body: 'Still?', replies: [], resolved: false },
    { id: 'c3', author: 'you', ts: 3, suggestionId: 'x1', body: 'Keep the number.', replies: [{ author: 'web', ts: 4, kind: 'note', note: 'Will do.' }], resolved: false },
    { id: 'c4', author: 'you', ts: 5, body: 'Overall fine.', replies: [], resolved: true },
  ];
  const storePath = storePathFor(root, file);
  saveStore(root, storePath, { v: 3, path: 'docs/report.md', suggestions: [], comments, detached: [] }, text);
  return { root, file, text, storePath, cutAt: cut.idx, coldAt: cold.idx, disk: fs.readFileSync(storePath) };
}
const ctx = { shown: '~/notes-api/docs/report.md' };

test('a stage that only refreshes anchorAt passes the check: the staged bytes carry the moved and the added positions, the sidecar on disk is untouched until the rename, and the stage is the caller\'s to discard', () => {
  const p = project();
  const store = loadStore(p.storePath, p.text);
  const loaded = apart(store.comments);
  assert.equal(store.comments[0].anchorAt, p.cutAt - 3, 'the fixture: stale');
  assert.equal('anchorAt' in store.comments[1], false, 'the fixture: the CLI wrote none');
  const staged = stageSidecar(p.root, p.storePath, store, p.text);
  assert.notEqual(staged, p.storePath);
  assert.ok(staged.startsWith(`${p.storePath}.romp-fc-`) && staged.endsWith('.tmp'), staged);
  assert.doesNotThrow(() => requireCommentsUntouched(ctx, store, loaded, 'accept'));
  const bytes = readSidecar(staged);
  assert.equal(bytes.comments[0].anchorAt, p.cutAt, 'the stale position refreshed');
  assert.equal(bytes.comments[1].anchorAt, p.coldAt, 'the missing position added');
  assert.equal('anchorAt' in bytes.comments[2], false);
  assert.equal('anchorAt' in bytes.comments[3], false);
  assert.notEqual(JSON.stringify(bytes.comments), JSON.stringify(readSidecar(p.storePath).comments), 'the staged comments differ from the loaded ones — in anchorAt alone');
  assert.equal(apart(bytes.comments), loaded);
  assert.deepEqual(fs.readFileSync(p.storePath), p.disk, 'nothing landed');
  discardSidecar(staged);
  assert.equal(fs.existsSync(staged), false);
  // Discarded, the stage is gone and the check has nothing to read: a check outside its window is
  // a program fault, never a quiet pass.
  assert.throws(() => requireCommentsUntouched(ctx, store, loaded, 'accept'), (e) => !(e instanceof Refusal) && e.code === 'ENOENT');
});

test('a comment changed between the load and the stage, in any field, refuses internal with the refusal\'s words; the stage is left for the caller to discard and nothing lands', () => {
  const p = project();
  const faults = [
    ['resolved set', (cs) => { cs[2].resolved = true; }],
    ['resolved cleared', (cs) => { cs[3].resolved = false; }],
    ['the binding dropped', (cs) => { delete cs[2].suggestionId; }],
    ['the binding changed', (cs) => { cs[2].suggestionId = 'x2'; }],
    ['a reply appended', (cs) => { cs[0].replies.push({ author: 'web', ts: 6, kind: 'note', note: 'Done.' }); }],
    ['a reply dropped', (cs) => { cs[2].replies.pop(); }],
    ['the body changed', (cs) => { cs[3].body = 'Overall fine!'; }],
    ['the author changed', (cs) => { cs[1].author = 'you'; }],
    ['the time changed', (cs) => { cs[0].ts = 9; }],
    ['the anchor changed', (cs) => { cs[0].anchor.quote = cs[0].anchor.quote.toUpperCase(); }],
    ['a field added', (cs) => { cs[3].sent = true; }],
    ['a comment dropped', (cs) => { cs.pop(); }],
    ['a comment added', (cs) => { cs.push({ id: 'c5', author: 'you', ts: 7, body: 'New.', replies: [], resolved: false }); }],
    ['the order changed', (cs) => { cs.reverse(); }],
  ];
  for (const [name, mutate] of faults) {
    for (const verb of ['accept', 'accept-all', 'reject', 'reject-all', 'save']) {
      const store = loadStore(p.storePath, p.text);
      const loaded = apart(store.comments);
      mutate(store.comments);   // the regression: a decision's step touching a comment
      const staged = stageSidecar(p.root, p.storePath, store, p.text);
      assert.throws(() => requireCommentsUntouched(ctx, store, loaded, verb), (e) => {
        assert.ok(e instanceof Refusal, `${name}, ${verb}: a Refusal, not a crash`);
        assert.equal(e.code, 'internal', `${name}, ${verb}`);
        assert.equal(e.message, `the ${verb} would have changed a comment in ~/notes-api/docs/report.md, which a decision never does; nothing was changed — reload and retry`);
        return true;
      });
      assert.ok(fs.existsSync(staged), `${name}, ${verb}: the check discards nothing itself`);
      discardSidecar(staged);
      assert.deepEqual(fs.readFileSync(p.storePath), p.disk, `${name}, ${verb}: nothing landed`);
    }
  }
});

test('the check is about the bytes: a change to the store after the stage is not in them, never lands, and is not refused', () => {
  const p = project();
  const store = loadStore(p.storePath, p.text);
  const loaded = apart(store.comments);
  const staged = stageSidecar(p.root, p.storePath, store, p.text);
  store.comments[2].resolved = true;
  assert.doesNotThrow(() => requireCommentsUntouched(ctx, store, loaded, 'save'));
  assert.equal(readSidecar(staged).comments[2].resolved, false);
  discardSidecar(staged);
});

test('a check on a store nothing has staged throws (a program fault, not a refusal): the first version compared the store with itself before the stage, and that cannot come back quietly; no sidecar is nothing to check', () => {
  const store = { comments: [{ id: 'c1', body: 'x' }] };
  assert.throws(() => requireCommentsUntouched(ctx, store, apart(store.comments), 'accept-all'),
    (e) => !(e instanceof Refusal) && /requireCommentsUntouched before the stage: the accept-all has staged nothing to check/.test(e.message));
  assert.doesNotThrow(() => requireCommentsUntouched(ctx, null, null, 'save'));
});

// ── the verbs, end to end ───────────────────────────────────────────
// Each scene leaves a comment with a position the decision's own refresh must move — the carve-out
// exercised for real, with the check in its place — and asserts the sidecar after equals the sidecar
// before apart from anchorAt, with anchorAt where the refresh puts it.

test('accept-all: a passage comment left stale by a track-edit above it and a CLI comment with no position both gain the refreshed anchorAt; the bound, the whole-file and every other field are as loaded; nothing is refused', () => {
  const w = world();
  let st = edit(w, w.report, 'shipping the cache in v1.2', 'shipping the cache in v1.3');   // X, below the passage
  const X = hunkFor(st, 'shipping the cache in v1.2');
  const cur = fs.readFileSync(w.report, 'utf8');
  const cut = anchorAt(cur, 'cut p95 latency by 40%', 0);
  const cold = anchorAt(cur, 'Cold starts remain slow', 0);
  st = comment(w, w.report, st, { anchor: cut.anchor, note: 'Say reduced.', hintOffset: cut.hintOffset });
  const passage = st.store.comments[0];
  assert.equal(passage.anchorAt, cut.idx);
  st = comment(w, w.report, st, { note: 'Overall fine.' });
  const whole = st.store.comments[1];
  st = comment(w, w.report, st, { suggestionId: X.id, note: 'Which version?' });
  const bound = st.store.comments[2];
  cliOk(w, 'comment', ['--file', w.report, '--anchor', 'Cold starts remain slow', '--note', 'Still?']);
  st = status(w, w.report);
  const fromCli = st.store.comments.find((c) => c.author === 'web' && c.anchor);
  assert.equal('anchorAt' in fromCli, false, 'the CLI writes no anchorAt');
  // Y: two lines land above every passage, through the CLI (a sidecar write the host did not make).
  const inserted = 'Added line one.\nAdded line two.\n';
  cliOk(w, 'edit', ['--file', w.report, '--old', '# Latency report\n', '--new', `# Latency report\n${inserted}`]);
  st = status(w, w.report);
  assert.equal(st.hunks.length, 2);
  assert.equal(byId(st.store.comments, passage.id).anchorAt, cut.idx, 'stale: the CLI wrote the object back as it was');
  const before = readSidecar(st.storePath);

  const r = acceptAll(w, w.report, st);
  assert.equal(r.accepted.length, 2);
  assert.deepEqual(r.hunks, []);
  const disk = readSidecar(r.storePath);
  assert.equal(disk.comments.length, 4);
  assert.equal(apart(disk.comments), apart(before.comments), 'every comment as loaded apart from anchorAt');
  assert.notEqual(JSON.stringify(disk.comments), JSON.stringify(before.comments), 'and anchorAt did change: the carve-out was exercised');
  assert.equal(byId(disk.comments, passage.id).anchorAt, cut.idx + inserted.length, 'the stale position refreshed');
  assert.equal(byId(disk.comments, fromCli.id).anchorAt, cold.idx + inserted.length, 'the missing position added');
  assert.equal(byId(disk.comments, bound.id).resolved, false, 'a decision never resolves a comment');
  assert.equal(byId(disk.comments, bound.id).suggestionId, X.id, 'the binding stays on disk');
  assert.deepEqual(byId(disk.comments, whole.id), whole, 'the whole-file comment is untouched');
  assert.deepEqual(r.store.comments, disk.comments);
});

test('reject-all: the reversal moves the passage back; the comment bound to the rejected change is as loaded; nothing is refused', () => {
  const w = world();
  const inserted = 'Added line one.\nAdded line two.\n';
  cliOk(w, 'edit', ['--file', w.report, '--old', '# Latency report\n', '--new', `# Latency report\n${inserted}`]);
  let st = status(w, w.report);
  const Y = st.hunks[0];
  const moved = fs.readFileSync(w.report, 'utf8');
  const cut = anchorAt(moved, 'cut p95 latency by 40%', 0);
  st = comment(w, w.report, st, { anchor: cut.anchor, note: 'Say reduced.', hintOffset: cut.hintOffset });
  const passage = st.store.comments[0];
  assert.equal(passage.anchorAt, cut.idx);
  st = comment(w, w.report, st, { suggestionId: Y.id, note: 'Not these.' });
  const bound = st.store.comments[1];
  const before = readSidecar(st.storePath);

  const r = rejectAll(w, w.report, st);
  assert.deepEqual(r.rejected, [Y.id]);
  assert.equal(fs.readFileSync(w.report, 'utf8'), w.text, 'the insertion is gone');
  const disk = readSidecar(r.storePath);
  assert.equal(apart(disk.comments), apart(before.comments), 'every comment as loaded apart from anchorAt');
  assert.equal(byId(disk.comments, passage.id).anchorAt, cut.idx - inserted.length, 'the position follows the passage back');
  assert.equal(byId(before.comments, passage.id).anchorAt, cut.idx);
  assert.equal(byId(disk.comments, bound.id).resolved, false);
  assert.equal(byId(disk.comments, bound.id).suggestionId, Y.id, 'the binding stays, though the change is gone');
  assert.deepEqual(r.store.comments, disk.comments);
});

test('save carrying an accept: the person\'s edit above moves the passage; the comment bound to the accepted change is as loaded; nothing is refused', () => {
  const w = world();
  writeTrackedPaths(w.root, ['docs/report.md']);
  let st = edit(w, w.report, 'cut p95 latency by 40%', 'reduced p95 latency by 35%');
  const cur = fs.readFileSync(w.report, 'utf8');
  const A = hunkFor(st, 'cut p95 latency by 40%');
  const ship = anchorAt(cur, 'shipping the cache in v1.2', 0);
  st = comment(w, w.report, st, { anchor: ship.anchor, note: 'Which version?', hintOffset: ship.hintOffset });
  const passage = st.store.comments[0];
  assert.equal(passage.anchorAt, ship.idx);
  st = comment(w, w.report, st, { suggestionId: A.id, note: 'Keep the number.' });
  const bound = st.store.comments[1];
  const before = readSidecar(st.storePath);
  // In the editor: accept A (the field drops it), then type " (draft)" into the title above.
  const field = engine.acceptSuggestion(st.store.suggestions, A.id).suggestions;
  const at = cur.indexOf('# Latency report') + '# Latency report'.length;
  const { content, records } = typed(cur, field, at, at, ' (draft)');
  assert.deepEqual(records, []);

  const r = save(w, w.report, st, content, records, [decision(A)], []);
  assert.equal(r.logged, true);
  assert.equal(fs.readFileSync(w.report, 'utf8'), content);
  assert.deepEqual(r.log.map((e) => e.kind), ['edit', 'accept']);
  const disk = readSidecar(st.storePath);
  assert.equal(apart(disk.comments), apart(before.comments), 'every comment as loaded apart from anchorAt');
  assert.equal(byId(disk.comments, passage.id).anchorAt, ship.idx + ' (draft)'.length, 'the position follows the typed text');
  assert.equal(byId(before.comments, passage.id).anchorAt, ship.idx);
  assert.equal(byId(disk.comments, bound.id).resolved, false, 'a decision taken in the editor never resolves a comment either');
  assert.equal(byId(disk.comments, bound.id).suggestionId, A.id);
  assert.deepEqual(r.store.comments, disk.comments);
});

// ── the placement ───────────────────────────────────────────────────

test('every decision verb checks after its stage and before the log append or the rename: accept, reject and save each call requireCommentsUntouched between stageSidecar and the step that lands anything, and none lands its sidecar in one step', () => {
  const src = fs.readFileSync(HOST, 'utf8');
  const body = (name) => {
    let i = src.indexOf(`\nfunction ${name}(`);
    if (i < 0) i = src.indexOf(`\nexport function ${name}(`);
    assert.ok(i >= 0, name);
    const j = src.indexOf('\nfunction ', i + 1);
    return src.slice(i, j < 0 ? src.length : j);
  };
  const ascending = (name, s, needles) => {
    const at = needles.map((n) => { const i = s.indexOf(n); assert.ok(i >= 0, `${name}: ${n}`); return i; });
    for (let k = 1; k < at.length; k++) assert.ok(at[k - 1] < at[k], `${name}: ${needles[k - 1]} before ${needles[k]}`);
  };
  ascending('doAccept', body('doAccept'), [
    'const loadedComments = commentsApartFromAnchorAt(store.comments);',
    'store.suggestions = (all ? engine.acceptAll(',
    'staged = stageSidecar(root, paths.storePath, store, file.text);',
    "requireCommentsUntouched(ctx, store, loadedComments, all ? 'accept-all' : 'accept');",
    'discardSidecar(staged);',
    "appendLog(paths.logPath, logEntry('accept'",
    'commitSidecar(staged, paths.storePath);',
  ]);
  ascending('doReject', body('doReject'), [
    'const loadedComments = commentsApartFromAnchorAt(store.comments);',
    'store.suggestions = res.suggestions;',
    'staged = stageSidecar(root, paths.storePath, store, newText);',
    "requireCommentsUntouched(ctx, store, loadedComments, all ? 'reject-all' : 'reject');",
    'discardSidecar(staged);',
    'commitSidecar(staged, paths.storePath);',
    "appendLog(paths.logPath, logEntry('reject'",
  ]);
  ascending('doSave', body('doSave'), [
    'loadedComments = commentsApartFromAnchorAt(store.comments);',
    'store.suggestions = fit.records;',
    'staged = stageSidecar(root, paths.storePath, store, a.content);',
    "requireCommentsUntouched(ctx, store, loadedComments, 'save');",
    'discardSidecar(staged);',
    'commitSidecar(staged, paths.storePath);',
    'appendLog(paths.logPath, e);',
  ]);
  for (const name of ['doAccept', 'doReject', 'doSave']) assert.ok(!body(name).includes('landSidecar('), `${name} stages, checks and lands in three steps`);
  assert.ok(!src.includes('c.resolved = true;'), 'no decision sets resolved');
  // The check reads the staged bytes back, never the store in memory.
  const check = body('requireCommentsUntouched');
  assert.ok(check.includes('const at = store[STAGED];'));
  assert.ok(check.includes("JSON.parse(fs.readFileSync(at, 'utf8'))"));
  assert.ok(check.includes('commentsApartFromAnchorAt(staged.comments) !== loadedComments'));
  assert.ok(!check.includes('commentsApartFromAnchorAt(store.comments)'));
  assert.ok(body('stageSidecar').includes('store[STAGED] = tmp;'), 'the stage stamps where the bytes are');
});

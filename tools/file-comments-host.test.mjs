// Conformance tests for tools/file-comments-host.mjs, the host script behind the Files pane's
// comments panel (plans/file-review.md, "Host script conformance" under Tests; the Slice 1 verbs
// and Slice 2's accept, accept-all, reject, reject-all and change comments).
// Hermetic: every test builds the synthetic `notes-api` world under a scratch directory (from
// tests/fixtures/file_comments/) and drives the script as the kernel does, a child process with
// one JSON request on stdin. Where the plan asks for it, the REAL vendored CLIs run as child
// processes too, so "a sidecar written by track-comment, replied to by the host script, read by
// track-reply" is exactly that, and every change a test decides was recorded by track-edit.
// Run: node --test tools/file-comments-host.test.mjs
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

import {
  storePathFor, loadStore, saveStore, fingerprintOf, readConfig, writeTrackedPaths,
} from '../vendor/track-changents/store-io.mjs';
import { addComment } from '../vendor/track-changents/cli/track-comment.mjs';
import {
  deriveUnsent, decidedFor, writeFileAtomic, checkTooLarge, locateExact, statNs, logPathFor, Refusal,
  applyEdits, TEXT_MAX_BYTES, LOG_TAIL,
} from './file-comments-host.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const HOST = path.join(REPO, 'tools', 'file-comments-host.mjs');
const VENDOR = path.join(REPO, 'vendor', 'track-changents');
const FIX = path.join(REPO, 'tests', 'fixtures', 'file_comments');
const engine = createRequire(import.meta.url)(path.join(VENDOR, 'engine.js'));

const SID = '11111111-2222-3333-4444-555555555555';
const NS_RE = /^\d+$/;

let SCRATCH;
before(() => { SCRATCH = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-fc-host-')); });
after(() => { try { fs.rmSync(SCRATCH, { recursive: true, force: true }); } catch { /* ignore */ } });

// ── the world ───────────────────────────────────────────────────────
// <scratch>/wN/home/            FILE_COMMENTS_HOME: "~" in every text the script prints
//   notes-api/.git/             the landmark that makes notes-api a project
//   notes-api/index.md          links to docs/report (tracking inheritance)
//   notes-api/docs/report.md    the commented file
//   loose/report.md             a file with no landmark above it
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

// The kernel's call: node <script>, the request on stdin, one JSON object back.
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

// The real vendored CLIs, run as an agent session named `web` would run them.
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
function configFenceFor(st) { return { configMtimeNs: st.configMtimeNs == null ? '' : st.configMtimeNs }; }

// The anchor the browser would build from a selection: the engine's makeAnchor at the nth
// occurrence of the quote, plus the selection's start offset as the hint.
function anchorAt(text, quote, nth) {
  let i = -1;
  for (let k = 0; k <= (nth || 0); k++) i = text.indexOf(quote, i + 1);
  assert.ok(i >= 0, `fixture lacks occurrence ${nth} of ${JSON.stringify(quote)}`);
  return { anchor: engine.makeAnchor(text, i, i + quote.length), hintOffset: i, idx: i };
}

function comment(w, file, st, args) {
  return ok(w, { verb: 'comment', path: file, args, fence: fenceFor(st) });
}
function readSidecar(sp) { return JSON.parse(fs.readFileSync(sp, 'utf8')); }
function readLogLines(lp) {
  return fs.readFileSync(lp, 'utf8').split('\n').filter(Boolean).map((l) => JSON.parse(l));
}
function fileBytes(p) { try { return fs.readFileSync(p); } catch { return null; } }
const emptyUnsent = { comments: [], replies: [], accepted: 0, rejected: 0, watermark: null };

// ── protocol and status ─────────────────────────────────────────────

test('status on a clean file with no landmark answers the null shape and writes nothing', () => {
  const w = world();
  const r = status(w, w.loose);
  assert.equal(r.root, null);
  assert.equal(r.storePath, null);
  assert.equal(r.trackedBy, null);
  assert.equal(r.store, null);
  assert.deepEqual(r.hunks, []);
  assert.deepEqual(r.unsent, emptyUnsent);
  assert.deepEqual(r.log, []);
  assert.equal(r.logTruncated, false);
  assert.equal(r.storeMtimeNs, null);
  assert.equal(r.configMtimeNs, null);
  assert.equal(r.agentTooling, 'absent');
  assert.match(r.fileMtimeNs, NS_RE);
  assert.equal(r.fileMtimeNs, fs.statSync(w.loose, { bigint: true }).mtimeNs.toString());
  assert.equal(fs.existsSync(path.join(w.looseDir, '.trackchanges')), false);
  assert.equal('baseline' in r, false);
});

test('status under a .git root names the root and the sidecar path storePathFor gives, and writes nothing', () => {
  const w = world();
  const r = status(w, w.report);
  assert.equal(r.root, w.root);
  assert.equal(r.storePath, storePathFor(w.root, w.report));
  assert.equal(path.basename(r.storePath), 'docs%2Freport.md.json');
  assert.equal(r.store, null);
  assert.equal(r.storeMtimeNs, null);
  assert.equal(r.configMtimeNs, null);
  assert.equal(r.trackedBy, null);
  assert.equal(fs.existsSync(path.join(w.root, '.trackchanges')), false);
});

test('agentTooling reports the linked track-reply.mjs under the home directory', () => {
  const w = world();
  assert.equal(status(w, w.report).agentTooling, 'absent');
  fs.mkdirSync(path.join(w.home, '.claude', 'hooks'), { recursive: true });
  fs.symlinkSync(path.join(VENDOR, 'cli', 'track-reply.mjs'), path.join(w.home, '.claude', 'hooks', 'track-reply.mjs'));
  assert.equal(status(w, w.report).agentTooling, 'present');
});

test('a refusal is {ok:false, code, error} on stdout with exit 0, and names the tilde-collapsed path', () => {
  const w = world();
  const r = host(w, { verb: 'comment', path: w.report, args: { note: 'x' }, fence: { storeMtimeNs: '12345' } });
  assert.equal(r.code, 0);
  assert.deepEqual(Object.keys(r.json).sort(), ['code', 'error', 'ok']);
  assert.equal(r.json.ok, false);
  assert.equal(r.json.code, 'store-moved');
  assert.ok(r.json.error.includes('~/notes-api/docs/report.md'), r.json.error);
  assert.equal(r.json.error.includes(w.home), false);
  assert.equal(r.stdout.trim().split('\n').length, 1, 'exactly one JSON object on stdout');
});

test('a missing file refuses unreadable with the OS error, tilde-collapsed', () => {
  const w = world();
  const r = refused(w, { verb: 'status', path: path.join(w.root, 'docs', 'gone.md') }, 'unreadable');
  assert.ok(r.error.includes('~/notes-api/docs/gone.md'), r.error);
  assert.ok(/ENOENT/.test(r.error), r.error);
  assert.equal(r.error.includes(w.home), false);
});

test('a malformed request crashes: non-zero exit, reason on stderr, nothing on stdout', () => {
  const w = world();
  const bad = spawnSync(process.execPath, [HOST], { input: '{not json', encoding: 'utf8', env: env(w) });
  assert.notEqual(bad.status, 0);
  assert.equal(bad.stdout, '');
  assert.match(bad.stderr, /not JSON/);

  const unknown = host(w, { verb: 'explode', path: w.report });
  assert.notEqual(unknown.code, 0);
  assert.equal(unknown.stdout, '');
  assert.match(unknown.stderr, /unknown verb/);

  // A mutating verb without its fence is a caller bug, never a silent write.
  const noFence = host(w, { verb: 'comment', path: w.report, args: { note: 'x' } });
  assert.notEqual(noFence.code, 0);
  assert.match(noFence.stderr, /fence\.storeMtimeNs is required/);
  assert.equal(fs.existsSync(path.join(w.root, '.trackchanges')), false);

  const noNote = host(w, { verb: 'comment', path: w.report, args: { note: '  ' }, fence: { storeMtimeNs: '' } });
  assert.notEqual(noNote.code, 0);
  assert.match(noNote.stderr, /note is required/);
  assert.equal(fs.existsSync(path.join(w.root, '.trackchanges')), false);
});

// ── comment ─────────────────────────────────────────────────────────

test('the first comment on a file with no landmark creates .trackchanges/ beside it, exactly where storePathFor puts the sidecar', () => {
  const w = world();
  const st = status(w, w.loose);
  const r = comment(w, w.loose, st, { note: 'Please expand the findings.' });
  const dir = path.dirname(w.loose);
  assert.equal(r.root, dir);
  assert.equal(r.storePath, storePathFor(dir, w.loose));
  assert.ok(fs.existsSync(path.join(dir, '.trackchanges')));
  assert.ok(fs.existsSync(r.storePath));
  assert.match(r.storeMtimeNs, NS_RE);
  assert.equal(r.storeMtimeNs, fs.statSync(r.storePath, { bigint: true }).mtimeNs.toString());
  // From now on status and the CLIs resolve the same root with no TRACKCHANGES_ROOT.
  assert.equal(status(w, w.loose).root, dir);
  cliOk(w, 'comment', ['--file', w.loose, '--anchor', 'shipping the cache in v1.2', '--note', 'Which cache do you mean?']);
  const disk = readSidecar(r.storePath);
  assert.equal(disk.comments.length, 2);
  assert.equal(disk.comments[1].author, 'web');
  assert.equal(disk.path, 'report.md');
});

test('a whole-file comment has addComment\'s shape minus the anchor: id `${now}-0`, author you, no authorId, no target', () => {
  const w = world();
  const r = comment(w, w.report, status(w, w.report), { note: '  Tighten the summary.  ' });
  assert.equal(r.store.comments.length, 1);
  const c = readSidecar(r.storePath).comments[0];
  assert.deepEqual(Object.keys(c), ['id', 'author', 'ts', 'body', 'replies', 'resolved']);
  assert.match(c.id, /^\d+-0$/);
  assert.equal(c.author, 'you');
  assert.equal(typeof c.ts, 'number');
  assert.equal(c.id, `${c.ts}-0`);
  assert.equal(c.body, 'Tighten the summary.');
  assert.deepEqual(c.replies, []);
  assert.equal(c.resolved, false);
  assert.equal('anchor' in c, false);
  assert.equal('target' in c, false);
  assert.equal('authorId' in c, false);
  // The seed is track-comment's: v 3, the project-relative path, and a fingerprint over the text.
  const disk = readSidecar(r.storePath);
  assert.equal(disk.v, 3);
  assert.equal(disk.path, 'docs/report.md');
  assert.deepEqual(disk.fingerprint, fingerprintOf(w.text));
  assert.deepEqual(disk.suggestions, []);
  assert.equal(r.unsent.comments.length, 1);
  assert.equal(r.unsent.comments[0], c.id);
});

test('a passage comment deep-equals addComment\'s object for the same quote and note apart from id and ts; v stays 3 and the fingerprint matches', () => {
  const w = world();
  const quote = 'cut p95 latency by 40%';
  const { anchor, hintOffset, idx } = anchorAt(w.text, quote, 0);
  const r = comment(w, w.report, status(w, w.report), { anchor, note: 'Say which percentile window.', hintOffset });
  const got = readSidecar(r.storePath).comments[0];

  const seed = { v: 3, path: 'docs/report.md', suggestions: [], comments: [] };
  const now = 1700000000000;
  assert.equal(addComment(seed, w.text, quote, 'Say which percentile window.', 'you', now, null).error, undefined);
  const want = seed.comments[0];
  assert.deepEqual(Object.keys(got), Object.keys(want));
  assert.deepEqual({ ...got, id: 'x', ts: 0 }, { ...want, id: 'x', ts: 0 });
  assert.equal(got.id, `${got.ts}-${idx}`);
  assert.deepEqual(got.anchor, engine.makeAnchor(w.text, idx, idx + quote.length));

  const disk = readSidecar(r.storePath);
  assert.equal(disk.v, 3);
  assert.deepEqual(disk.fingerprint, fingerprintOf(w.text));
  assert.equal(fs.readFileSync(w.report, 'utf8'), w.text, 'the file is untouched');
  // The status reply carries the same store and no baseline unless asked.
  const st = status(w, w.report);
  assert.deepEqual(st.store.comments[0], got);
  assert.equal(st.storeMtimeNs, r.storeMtimeNs);
});

test('a sidecar written by track-comment, replied to by the host script, read by track-reply keeps every field', () => {
  const w = world();
  cliOk(w, 'comment', ['--file', w.report, '--anchor', 'shipping the cache in v1.2', '--note', 'Which cache do you mean?']);
  const sp = storePathFor(w.root, w.report);
  const before = readSidecar(sp);
  assert.equal(before.comments.length, 1);
  const agentComment = before.comments[0];
  assert.equal(agentComment.author, 'web');
  assert.equal(agentComment.authorId, SID);

  const st = status(w, w.report);
  assert.equal(st.store.comments[0].id, agentComment.id);
  const r = ok(w, { verb: 'reply', path: w.report, args: { commentId: agentComment.id, note: 'The response cache.' }, fence: fenceFor(st) });
  const mid = readSidecar(sp);
  assert.equal(mid.v, 3);
  assert.equal(mid.id, before.id, 'the store id is kept');
  assert.deepEqual(mid.fingerprint, before.fingerprint);
  assert.deepEqual({ ...mid.comments[0], replies: [] }, { ...agentComment, replies: [] });
  assert.equal(mid.comments[0].replies.length, 1);
  const you = mid.comments[0].replies[0];
  assert.deepEqual(Object.keys(you), ['author', 'ts', 'body']);
  assert.equal(you.author, 'you');
  assert.equal(you.body, 'The response cache.');
  assert.equal(r.store.comments[0].replies[0].body, 'The response cache.');

  // track-reply then reads the host's sidecar and adds its own turn; nothing is lost.
  cliOk(w, 'reply', ['--file', w.report, '--thread', agentComment.id, '--note', 'Done, and the table is updated.']);
  const after = readSidecar(sp);
  assert.equal(after.v, 3);
  assert.deepEqual(after.fingerprint, fingerprintOf(w.text));
  assert.deepEqual({ ...after.comments[0], replies: [] }, { ...agentComment, replies: [] });
  assert.deepEqual(after.comments[0].replies[0], you);
  assert.deepEqual(after.comments[0].replies[1], { author: 'web', authorId: SID, ts: after.comments[0].replies[1].ts, body: 'Done, and the table is updated.' });
  assert.deepEqual(after.suggestions, []);
  assert.deepEqual(after.detached, []);
});

test('a passage the host commented on is replied to by track-reply and its anchor survives unchanged', () => {
  const w = world();
  const { anchor, hintOffset } = anchorAt(w.text, 'cut p95 latency by 40%', 0);
  const r = comment(w, w.report, status(w, w.report), { anchor, note: 'Which window?', hintOffset });
  const c = readSidecar(r.storePath).comments[0];
  cliOk(w, 'reply', ['--file', w.report, '--thread', c.id, '--note', 'The p95 over the last week.']);
  const after = readSidecar(r.storePath).comments[0];
  assert.deepEqual({ ...after, replies: [] }, { ...c, replies: [] });
  assert.equal(after.replies[0].author, 'web');
  assert.equal(after.replies[0].body, 'The p95 over the last week.');
});

test('a quote that occurs several times with different surroundings anchors to the selected one, even with a stale hint', () => {
  const w = world();
  const { anchor, hintOffset, idx } = anchorAt(w.text, 'retry on timeout', 2);
  // Two lines land above the passage between the selection and Enter: the offset is stale, the
  // context is not, and the third occurrence is still the one commented on.
  const inserted = 'Added line one.\nAdded line two.\n';
  fs.writeFileSync(w.report, inserted + w.text);
  const r = comment(w, w.report, status(w, w.report), { anchor, note: 'One retry is enough.', hintOffset });
  const c = readSidecar(r.storePath).comments[0];
  const newText = fs.readFileSync(w.report, 'utf8');
  assert.equal(c.id, `${c.ts}-${idx + inserted.length}`);
  assert.equal(newText.slice(idx + inserted.length, idx + inserted.length + 'retry on timeout'.length), 'retry on timeout');
  assert.deepEqual(c.anchor, engine.makeAnchor(newText, idx + inserted.length, idx + inserted.length + 'retry on timeout'.length));
  assert.equal(engine.locateAnchor(newText, c.anchor).from, idx + inserted.length, 'a hintless reader places it there too');
});

test('an ambiguous anchor (identical surroundings) refuses anchor-ambiguous and writes nothing', () => {
  const w = world();
  const first = anchorAt(w.text, 'Ship it.', 0);
  const second = anchorAt(w.text, 'Ship it.', 1);
  assert.deepEqual(first.anchor, second.anchor, 'the fixture\'s two occurrences share their context');
  const r = refused(w, { verb: 'comment', path: w.report, args: { anchor: second.anchor, note: 'Not yet.', hintOffset: second.hintOffset }, fence: { storeMtimeNs: '' } }, 'anchor-ambiguous');
  assert.ok(r.error.includes('~/notes-api/docs/report.md'), r.error);
  assert.equal(fs.existsSync(path.join(w.root, '.trackchanges')), false);
  assert.deepEqual(locateExact(w.text, second.anchor, second.hintOffset), { error: 'anchor-ambiguous' });
  // Selecting the FIRST occurrence is refused too: the hint would pick it now, but a later reader
  // has no hint and would place the comment on whichever copy the engine picks then.
  refused(w, { verb: 'comment', path: w.report, args: { anchor: first.anchor, note: 'Not yet.', hintOffset: first.hintOffset }, fence: { storeMtimeNs: '' } }, 'anchor-ambiguous');
  assert.deepEqual(locateExact(w.text, first.anchor, first.hintOffset), { error: 'anchor-ambiguous' });
  assert.deepEqual(locateExact(w.text, first.anchor, undefined), { error: 'anchor-ambiguous' });
});

test('a passage that is gone refuses anchor-not-found, also when only its surroundings survive', () => {
  const w = world();
  const missing = { quote: 'cut p99 latency', prefix: '', suffix: '' };
  refused(w, { verb: 'comment', path: w.report, args: { anchor: missing, note: 'x' }, fence: { storeMtimeNs: '' } }, 'anchor-not-found');
  // The quote is edited away but its prefix and suffix remain: the engine's fallback finds the
  // region between them, which is a relocation, not the passage, so the comment is refused.
  const { anchor, hintOffset } = anchorAt(w.text, 'cut p95 latency by 40%', 0);
  fs.writeFileSync(w.report, w.text.replace('cut p95 latency by 40%', 'cut p95 latency by 35%'));
  const cur = fs.readFileSync(w.report, 'utf8');
  assert.ok(engine.locateAnchor(cur, anchor), 'the engine relocates by context');
  const r = refused(w, { verb: 'comment', path: w.report, args: { anchor, note: 'x', hintOffset }, fence: { storeMtimeNs: '' } }, 'anchor-not-found');
  assert.ok(r.error.includes('~/notes-api/docs/report.md'), r.error);
  assert.equal(fs.existsSync(path.join(w.root, '.trackchanges')), false);
});

test('whole-file and target comments round-trip through store-io unchanged', () => {
  const w = world();
  let st = status(w, w.report);
  const target = { kind: 'image', region: { x: 0.12, y: 0.4, w: 0.35, h: 0.2 }, hash: 'a'.repeat(64) };
  let r = comment(w, w.report, st, { note: 'Crop the chart.', target });
  st = status(w, w.report);
  r = comment(w, w.report, st, { note: 'Whole file: add a date.' });
  const sp = r.storePath;
  const written = readSidecar(sp);
  assert.equal(written.comments.length, 2);
  assert.deepEqual(written.comments[0].target, target);
  assert.equal('anchor' in written.comments[0], false);
  assert.match(written.comments[0].id, /^\d+-0$/);
  assert.equal('target' in written.comments[1], false);

  // store-io loads (normalizing and rebasing) and writes the whole object back: both survive.
  const loaded = loadStore(sp, w.text);
  saveStore(w.root, sp, loaded, w.text);
  const again = readSidecar(sp);
  assert.deepEqual(again.comments, written.comments);
  assert.equal(again.v, 3);
  // ...and the host's own next write keeps them too, with a reply into the target comment.
  st = status(w, w.report);
  assert.deepEqual(st.store.comments[0].target, target);
  r = ok(w, { verb: 'reply', path: w.report, args: { commentId: written.comments[0].id, note: 'Cropped.' }, fence: fenceFor(st) });
  const final = readSidecar(sp);
  assert.deepEqual(final.comments[0].target, target);
  assert.deepEqual({ ...final.comments[1] }, written.comments[1]);
  assert.equal(r.store.comments[0].replies[0].body, 'Cropped.');
});

// ── fences ──────────────────────────────────────────────────────────

test('the sidecar fence: "" when it exists, a stale value, and the current value', () => {
  const w = world();
  const r1 = comment(w, w.report, status(w, w.report), { note: 'first' });
  const bytes = fileBytes(r1.storePath);
  const gone = refused(w, { verb: 'comment', path: w.report, args: { note: 'second' }, fence: { storeMtimeNs: '' } }, 'store-moved');
  assert.match(gone.error, /appeared on disk/);
  assert.deepEqual(fileBytes(r1.storePath), bytes, 'nothing written on a "" fence over an existing sidecar');
  const stale = refused(w, { verb: 'comment', path: w.report, args: { note: 'second' }, fence: { storeMtimeNs: '1' } }, 'store-moved');
  assert.match(stale.error, /changed on disk/);
  assert.deepEqual(fileBytes(r1.storePath), bytes, 'nothing written on a stale fence');
  const r2 = ok(w, { verb: 'comment', path: w.report, args: { note: 'second' }, fence: { storeMtimeNs: r1.storeMtimeNs } });
  assert.equal(r2.store.comments.length, 2);
  assert.notEqual(r2.storeMtimeNs, r1.storeMtimeNs);
  assert.equal(r2.storeMtimeNs, statNs(r2.storePath));
  // A sidecar that vanished under a non-empty fence: the third variant of the same refusal.
  fs.unlinkSync(r2.storePath);
  const removed = refused(w, { verb: 'comment', path: w.report, args: { note: 'third' }, fence: { storeMtimeNs: r2.storeMtimeNs } }, 'store-moved');
  assert.match(removed.error, /disappeared from disk/);
  assert.equal(fs.existsSync(r2.storePath), false);
  // reply and resolve carry the same fence.
  refused(w, { verb: 'reply', path: w.report, args: { commentId: 'x', note: 'y' }, fence: { storeMtimeNs: '7' } }, 'store-moved');
  refused(w, { verb: 'resolve', path: w.report, args: { commentId: 'x', on: true }, fence: { storeMtimeNs: '7' } }, 'store-moved');
});

test('a v:4 sidecar refuses unsupported-version on every verb and is never replaced', () => {
  const w = world();
  const sp = storePathFor(w.root, w.report);
  fs.mkdirSync(path.dirname(sp));
  fs.copyFileSync(path.join(FIX, 'sidecar-v4.json'), sp);
  const bytes = fileBytes(sp);
  const mt = statNs(sp);
  const r = refused(w, { verb: 'status', path: w.report }, 'unsupported-version');
  assert.ok(r.error.includes('~/notes-api/docs/report.md'), r.error);
  refused(w, { verb: 'comment', path: w.report, args: { note: 'x' }, fence: { storeMtimeNs: mt } }, 'unsupported-version');
  refused(w, { verb: 'reply', path: w.report, args: { commentId: '1', note: 'x' }, fence: { storeMtimeNs: mt } }, 'unsupported-version');
  refused(w, { verb: 'resolve', path: w.report, args: { commentId: '1', on: true }, fence: { storeMtimeNs: mt } }, 'unsupported-version');
  refused(w, { verb: 'set-tracked', path: w.report, args: { on: true, scope: 'file' }, fence: { configMtimeNs: '' } }, 'unsupported-version');
  const fileNs = statNs(w.report);
  refused(w, { verb: 'accept', path: w.report, args: { ids: ['1'] }, fence: { storeMtimeNs: mt } }, 'unsupported-version');
  refused(w, { verb: 'accept-all', path: w.report, args: {}, fence: { storeMtimeNs: mt } }, 'unsupported-version');
  refused(w, { verb: 'reject', path: w.report, args: { ids: ['1'] }, fence: { storeMtimeNs: mt, fileMtimeNs: fileNs } }, 'unsupported-version');
  refused(w, { verb: 'reject-all', path: w.report, args: {}, fence: { storeMtimeNs: mt, fileMtimeNs: fileNs } }, 'unsupported-version');
  refused(w, { verb: 'comment', path: w.report, args: { suggestionId: '1', note: 'x' }, fence: { storeMtimeNs: mt } }, 'unsupported-version');
  assert.deepEqual(fileBytes(sp), bytes);
  assert.equal(fs.readFileSync(w.report, 'utf8'), w.text);
  assert.deepEqual(fs.readdirSync(path.dirname(sp)), [path.basename(sp)], 'no temp file, no config, no log');
});

test('an unparseable sidecar refuses corrupt on every verb and is never replaced', () => {
  const w = world();
  const sp = storePathFor(w.root, w.report);
  fs.mkdirSync(path.dirname(sp));
  fs.copyFileSync(path.join(FIX, 'sidecar-corrupt.txt'), sp);
  const bytes = fileBytes(sp);
  const mt = statNs(sp);
  const r = refused(w, { verb: 'status', path: w.report }, 'corrupt');
  assert.ok(r.error.includes('~/notes-api/.trackchanges/docs%2Freport.md.json'), r.error);
  refused(w, { verb: 'comment', path: w.report, args: { note: 'x' }, fence: { storeMtimeNs: mt } }, 'corrupt');
  refused(w, { verb: 'reply', path: w.report, args: { commentId: '1', note: 'x' }, fence: { storeMtimeNs: mt } }, 'corrupt');
  const fileNs = statNs(w.report);
  refused(w, { verb: 'accept', path: w.report, args: { ids: ['1700000000000-4'] }, fence: { storeMtimeNs: mt } }, 'corrupt');
  refused(w, { verb: 'accept-all', path: w.report, args: {}, fence: { storeMtimeNs: mt } }, 'corrupt');
  refused(w, { verb: 'reject', path: w.report, args: { ids: ['1700000000000-4'] }, fence: { storeMtimeNs: mt, fileMtimeNs: fileNs } }, 'corrupt');
  refused(w, { verb: 'reject-all', path: w.report, args: {}, fence: { storeMtimeNs: mt, fileMtimeNs: fileNs } }, 'corrupt');
  refused(w, { verb: 'comment', path: w.report, args: { suggestionId: '1700000000000-4', note: 'x' }, fence: { storeMtimeNs: mt } }, 'corrupt');
  assert.deepEqual(fileBytes(sp), bytes);
  assert.equal(fs.readFileSync(w.report, 'utf8'), w.text);
  assert.deepEqual(fs.readdirSync(path.dirname(sp)), [path.basename(sp)]);
  // The vendored track-comment would have replaced it (survey item A2); the host never does.
});

// ── reply and resolve ───────────────────────────────────────────────

test('reply and resolve refuse no-comment for an id the live sidecar lacks, and never create a sidecar', () => {
  const w = world();
  // No sidecar at all: the fence is "" and the answer is no-comment, with nothing created.
  const r0 = refused(w, { verb: 'reply', path: w.loose, args: { commentId: '1-0', note: 'hi' }, fence: { storeMtimeNs: '' } }, 'no-comment');
  assert.ok(r0.error.includes('1-0') && r0.error.includes('~/loose/report.md'), r0.error);
  assert.equal(fs.existsSync(path.join(w.looseDir, '.trackchanges')), false);
  refused(w, { verb: 'resolve', path: w.report, args: { commentId: '1-0', on: true }, fence: { storeMtimeNs: '' } }, 'no-comment');
  assert.equal(fs.existsSync(path.join(w.root, '.trackchanges')), false);
  // A sidecar with other comments: still no-comment, bytes untouched.
  const r1 = comment(w, w.report, status(w, w.report), { note: 'real' });
  const bytes = fileBytes(r1.storePath);
  refused(w, { verb: 'reply', path: w.report, args: { commentId: 'nope', note: 'hi' }, fence: { storeMtimeNs: r1.storeMtimeNs } }, 'no-comment');
  refused(w, { verb: 'resolve', path: w.report, args: { commentId: 'nope', on: true }, fence: { storeMtimeNs: r1.storeMtimeNs } }, 'no-comment');
  assert.deepEqual(fileBytes(r1.storePath), bytes);
  assert.equal(fs.existsSync(r1.storePath + '.superseded'), false);
});

test('resolve toggles the flag and keeps the comment and every other field', () => {
  const w = world();
  const { anchor, hintOffset } = anchorAt(w.text, 'cut p95 latency by 40%', 0);
  let r = comment(w, w.report, status(w, w.report), { anchor, note: 'Which window?', hintOffset });
  const c = readSidecar(r.storePath).comments[0];
  r = ok(w, { verb: 'resolve', path: w.report, args: { commentId: c.id, on: true }, fence: fenceFor(r) });
  let disk = readSidecar(r.storePath);
  assert.equal(disk.comments.length, 1);
  assert.deepEqual(disk.comments[0], { ...c, resolved: true });
  assert.equal(r.store.comments[0].resolved, true);
  r = ok(w, { verb: 'resolve', path: w.report, args: { commentId: c.id, on: false }, fence: fenceFor(r) });
  disk = readSidecar(r.storePath);
  assert.deepEqual(disk.comments[0], c);
  assert.equal(disk.v, 3);
  assert.deepEqual(disk.fingerprint, fingerprintOf(w.text));
  // Resolving is not something to send: unsent lists the comment only for its own ts.
  assert.deepEqual(r.unsent.comments, [c.id]);
  assert.deepEqual(r.unsent.replies, []);
});

// ── set-tracked ─────────────────────────────────────────────────────

test('set-tracked file on writes config.json through setTracked, fenced on configMtimeNs, and track-config agrees', () => {
  const w = world();
  assert.equal(cli(w, 'config', ['--file', w.report]).status, 1, 'off before');
  const st = status(w, w.report);
  const r = ok(w, { verb: 'set-tracked', path: w.report, args: { on: true, scope: 'file' }, fence: configFenceFor(st) });
  assert.deepEqual(readConfig(w.root), { v: 2, tracked: ['docs/report.md'] });
  assert.deepEqual(r.trackedBy, { kind: 'file', entry: 'docs/report.md' });
  assert.match(r.configMtimeNs, NS_RE);
  assert.equal(r.configMtimeNs, statNs(path.join(w.root, '.trackchanges', 'config.json')));
  assert.equal(r.store, null, 'tracking writes no sidecar');
  assert.equal(r.storeMtimeNs, null);
  const tc = cli(w, 'config', ['--file', w.report]);
  assert.equal(tc.status, 0);
  assert.equal(tc.stdout.trim(), 'on');
  assert.equal(status(w, w.report).trackedBy.kind, 'file');
  // The log gained exactly one entry, the toggle.
  assert.equal(r.log.length, 1);
  const e = r.log[0];
  assert.equal(e.kind, 'set-tracked');
  assert.equal(e.author, 'you');
  assert.equal(e.on, true);
  assert.equal(e.scope, 'file');
  assert.equal(e.entry, 'docs/report.md');
  assert.match(e.ts, /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/);
  assert.deepEqual(readLogLines(logPathFor(r.storePath)), [e]);
  // ...and off removes the entry and logs again.
  const r2 = ok(w, { verb: 'set-tracked', path: w.report, args: { on: false }, fence: configFenceFor(r) });
  assert.deepEqual(readConfig(w.root), { v: 2, tracked: [] });
  assert.equal(r2.trackedBy, null);
  assert.equal(r2.log.length, 2);
  assert.deepEqual({ ...r2.log[1], ts: 'T' }, { ts: 'T', kind: 'set-tracked', author: 'you', on: false, scope: 'file', entry: 'docs/report.md' });
  assert.equal(cli(w, 'config', ['--file', w.report]).status, 1);
});

test('set-tracked folder writes <dir>/ relative to the root, covers siblings, and off removes that entry while keeping untracked', () => {
  const w = world();
  fs.mkdirSync(path.join(w.root, '.trackchanges'));
  fs.writeFileSync(path.join(w.root, '.trackchanges', 'config.json'), JSON.stringify({ v: 2, tracked: [], untracked: ['docs/private/'] }) + '\n');
  const sibling = path.join(w.root, 'docs', 'other.md');
  fs.writeFileSync(sibling, '# Other\n');
  const st = status(w, w.report);
  assert.match(st.configMtimeNs, NS_RE);
  const r = ok(w, { verb: 'set-tracked', path: w.report, args: { on: true, scope: 'folder' }, fence: configFenceFor(st) });
  assert.deepEqual(readConfig(w.root), { v: 2, tracked: ['docs/'], untracked: ['docs/private/'] });
  assert.deepEqual(r.trackedBy, { kind: 'folder', entry: 'docs/' });
  assert.deepEqual(status(w, sibling).trackedBy, { kind: 'folder', entry: 'docs/' });
  assert.equal(cli(w, 'config', ['--file', sibling]).stdout.trim(), 'on');
  // A file that does not exist yet under the folder will be tracked when the session writes it.
  const future = path.join(w.root, 'docs', 'later.md');
  assert.equal(cli(w, 'config', ['--file', future]).stdout.trim(), 'on');
  const r2 = ok(w, { verb: 'set-tracked', path: w.report, args: { on: false }, fence: configFenceFor(r) });
  assert.deepEqual(readConfig(w.root), { v: 2, tracked: [], untracked: ['docs/private/'] });
  assert.equal(r2.trackedBy, null);
  assert.deepEqual(r2.log.map((e) => [e.kind, e.on, e.scope, e.entry]), [['set-tracked', true, 'folder', 'docs/'], ['set-tracked', false, 'folder', 'docs/']]);
});

test('set-tracked folder on a file at the root refuses folder-is-root and writes nothing', () => {
  const w = world();
  const r = refused(w, { verb: 'set-tracked', path: w.index, args: { on: true, scope: 'folder' }, fence: { configMtimeNs: '' } }, 'folder-is-root');
  assert.ok(r.error.includes('~/notes-api/index.md'), r.error);
  assert.equal(fs.existsSync(path.join(w.root, '.trackchanges', 'config.json')), false);
});

test('a file tracked only through a parent note reports inherited, and off refuses tracked-inherited naming the parent', () => {
  const w = world();
  writeTrackedPaths(w.root, ['index.md']);
  const cfgBytes = fileBytes(path.join(w.root, '.trackchanges', 'config.json'));
  assert.equal(cli(w, 'config', ['--file', w.report]).stdout.trim(), 'on', 'the CLIs see the inheritance');
  const st = status(w, w.report);
  assert.deepEqual(st.trackedBy, { kind: 'inherited', entry: 'index.md' });
  const r = refused(w, { verb: 'set-tracked', path: w.report, args: { on: false }, fence: configFenceFor(st) }, 'tracked-inherited');
  assert.ok(r.error.includes('~/notes-api/index.md'), r.error);
  assert.ok(r.error.includes('~/notes-api/docs/report.md'), r.error);
  assert.deepEqual(fileBytes(path.join(w.root, '.trackchanges', 'config.json')), cfgBytes);
  assert.equal(fs.existsSync(logPathFor(st.storePath)), false, 'a refused toggle logs nothing');
  // Turning it on explicitly for the file is allowed and then reads as a file entry.
  const r2 = ok(w, { verb: 'set-tracked', path: w.report, args: { on: true, scope: 'file' }, fence: configFenceFor(st) });
  assert.deepEqual(r2.trackedBy, { kind: 'file', entry: 'docs/report.md' });
  assert.deepEqual(readConfig(w.root).tracked, ['index.md', 'docs/report.md']);
});

test('the config fence: "" when config.json exists and a stale value both refuse config-moved with nothing written', () => {
  const w = world();
  writeTrackedPaths(w.root, ['index.md']);
  const cfg = path.join(w.root, '.trackchanges', 'config.json');
  const bytes = fileBytes(cfg);
  refused(w, { verb: 'set-tracked', path: w.report, args: { on: true, scope: 'file' }, fence: { configMtimeNs: '' } }, 'config-moved');
  refused(w, { verb: 'set-tracked', path: w.report, args: { on: true, scope: 'file' }, fence: { configMtimeNs: '42' } }, 'config-moved');
  assert.deepEqual(fileBytes(cfg), bytes);
  assert.equal(fs.existsSync(logPathFor(storePathFor(w.root, w.report))), false);
  const noFence = host(w, { verb: 'set-tracked', path: w.report, args: { on: true, scope: 'file' } });
  assert.notEqual(noFence.code, 0);
  assert.match(noFence.stderr, /fence\.configMtimeNs is required/);
  assert.deepEqual(fileBytes(cfg), bytes);
});

test('set-tracked on a file with no landmark creates .trackchanges/ beside it; off on an untracked one creates nothing', () => {
  const w = world();
  const dir = path.dirname(w.loose);
  const r0 = ok(w, { verb: 'set-tracked', path: w.loose, args: { on: false }, fence: { configMtimeNs: '' } });
  assert.equal(r0.root, null);
  assert.equal(fs.existsSync(path.join(dir, '.trackchanges')), false);
  const r = ok(w, { verb: 'set-tracked', path: w.loose, args: { on: true, scope: 'file' }, fence: { configMtimeNs: '' } });
  assert.equal(r.root, dir);
  assert.deepEqual(readConfig(dir), { v: 2, tracked: ['report.md'] });
  assert.deepEqual(r.trackedBy, { kind: 'file', entry: 'report.md' });
  assert.equal(cli(w, 'config', ['--file', w.loose]).stdout.trim(), 'on');
  refused(w, { verb: 'set-tracked', path: w.loose, args: { on: true, scope: 'folder' }, fence: configFenceFor(r) }, 'folder-is-root');
});

// ── the comments log ────────────────────────────────────────────────

const summary = (diff) => ({ mtimeBeforeNs: '1', mtimeAfterNs: '2', bytesBefore: 10, bytesAfter: 12, diff: diff || '@@ -1 +1 @@\n-a\n+b\n', truncated: false });

test('log-edit answers logged:false and creates nothing when the file has no sidecar, log, or tracked flag', () => {
  const w = world();
  const r = ok(w, { verb: 'log-edit', path: w.report, args: { summary: summary() } });
  assert.equal(r.logged, false);
  assert.equal(r.root, w.root);
  assert.equal(fs.existsSync(path.join(w.root, '.trackchanges')), false);
  const r2 = ok(w, { verb: 'log-edit', path: w.loose, args: { summary: summary() } });
  assert.equal(r2.logged, false);
  assert.equal(r2.root, null);
  assert.equal(fs.existsSync(path.join(w.looseDir, '.trackchanges')), false);
});

test('log-edit appends one edit entry for a tracked file, a file with a sidecar, and a file with a log', () => {
  const w = world();
  // tracked flag only
  writeTrackedPaths(w.root, ['docs/report.md']);
  const lp = logPathFor(storePathFor(w.root, w.report));
  const r = ok(w, { verb: 'log-edit', path: w.report, args: { summary: { ...summary(), kind: 'sneaky', extra: 1 } } });
  assert.equal(r.logged, true);
  assert.deepEqual(r.log.map((e) => ({ ...e, ts: 'T' })), [{ ts: 'T', kind: 'edit', author: 'you', ...summary() }]);
  assert.equal(fs.existsSync(storePathFor(w.root, w.report)), false, 'no sidecar is created');
  // sidecar only (another file, untracked)
  const other = path.join(w.root, 'docs', 'other.md');
  fs.writeFileSync(other, 'Some text.\n');
  const c = comment(w, other, status(w, other), { note: 'note' });
  const r2 = ok(w, { verb: 'log-edit', path: other, args: { summary: summary() } });
  assert.equal(r2.logged, true);
  assert.equal(r2.log.length, 1);
  assert.equal(readSidecar(c.storePath).comments.length, 1, 'the sidecar is untouched');
  // log only: untrack the first file; its log still exists, so the next edit is logged too.
  writeTrackedPaths(w.root, []);
  const r3 = ok(w, { verb: 'log-edit', path: w.report, args: { summary: summary('second') } });
  assert.equal(r3.logged, true);
  const lines = readLogLines(lp);
  assert.equal(lines.length, 2);
  assert.equal(lines[1].diff, 'second');
});

test('log-edit still records the edit when the sidecar is corrupt, and says so beside the refusal', () => {
  const w = world();
  const sp = storePathFor(w.root, w.report);
  fs.mkdirSync(path.dirname(sp));
  fs.copyFileSync(path.join(FIX, 'sidecar-corrupt.txt'), sp);
  const r = refused(w, { verb: 'log-edit', path: w.report, args: { summary: summary() } }, 'corrupt');
  assert.equal(r.logged, true);
  assert.equal(readLogLines(logPathFor(sp)).length, 1);
});

test('log-send appends the message as sent; the log is only ever appended to', () => {
  const w = world();
  let st = status(w, w.report);
  const c1 = comment(w, w.report, st, { note: 'one' }).store.comments[0];
  const lp = logPathFor(storePathFor(w.root, w.report));
  const send = {
    sid: SID, sessionName: 'web',
    comments: [{ id: c1.id, desc: 'on this file', body: 'one' }],
    accepted: 0, rejected: 0, queued: false, watermark: c1.ts,
  };
  const r = ok(w, { verb: 'log-send', path: w.report, args: send });
  assert.equal(r.logged, true);
  assert.equal(r.log.length, 1);
  assert.deepEqual({ ...r.log[0], ts: 'T' }, { ts: 'T', kind: 'send', author: 'you', ...send });
  assert.deepEqual(r.unsent, { comments: [], replies: [], accepted: 0, rejected: 0, watermark: c1.ts });
  const bytes1 = fileBytes(lp);

  st = status(w, w.report);
  ok(w, { verb: 'set-tracked', path: w.report, args: { on: true, scope: 'file' }, fence: configFenceFor(st) });
  const bytes2 = fileBytes(lp);
  assert.ok(bytes2.length > bytes1.length && bytes2.subarray(0, bytes1.length).equals(bytes1), 'earlier bytes are a prefix');
  ok(w, { verb: 'log-edit', path: w.report, args: { summary: summary() } });
  const bytes3 = fileBytes(lp);
  assert.ok(bytes3.subarray(0, bytes2.length).equals(bytes2));
  assert.deepEqual(readLogLines(lp).map((e) => e.kind), ['send', 'set-tracked', 'edit']);
  // Comments and replies never go to the log; they live in the sidecar.
  st = status(w, w.report);
  comment(w, w.report, st, { note: 'two' });
  assert.deepEqual(readLogLines(lp).map((e) => e.kind), ['send', 'set-tracked', 'edit']);
});

test('log-send on a file with no landmark creates .trackchanges/ beside it (a mutating verb other than log-edit)', () => {
  const w = world();
  const r = ok(w, { verb: 'log-send', path: w.loose, args: { sid: SID, comments: [], accepted: 0, rejected: 0, queued: true, watermark: null } });
  assert.equal(r.root, path.dirname(w.loose));
  assert.equal(r.logged, true);
  assert.equal(r.log[0].queued, true);
  assert.equal(r.log[0].watermark, null);
  assert.equal('sessionName' in r.log[0], false);
});

test('the unsent derivation from the log matches a hand computation', () => {
  const w = world();
  let st = status(w, w.report);
  const c1 = comment(w, w.report, st, { note: 'c1' }).store.comments[0];
  st = status(w, w.report);
  const a1 = anchorAt(w.text, 'cut p95 latency by 40%', 0);
  const c2 = comment(w, w.report, st, { anchor: a1.anchor, note: 'c2', hintOffset: a1.hintOffset }).store.comments[1];
  // An agent's comment and reply never count as unsent.
  cliOk(w, 'comment', ['--file', w.report, '--anchor', 'shipping the cache in v1.2', '--note', 'agent asks']);
  cliOk(w, 'reply', ['--file', w.report, '--thread', c1.id, '--note', 'agent answers c1']);
  st = status(w, w.report);
  let r = ok(w, { verb: 'reply', path: w.report, args: { commentId: c1.id, note: 'you reply to c1' }, fence: fenceFor(st) });
  const r1 = r.store.comments.find((c) => c.id === c1.id).replies.find((x) => x.author === 'you');
  assert.deepEqual(r.unsent, { comments: [c1.id, c2.id], replies: [{ commentId: c1.id, ts: r1.ts }], accepted: 0, rejected: 0, watermark: null });

  // The send carries everything; its watermark is the largest ts among what it carried.
  const W = Math.max(c1.ts, c2.ts, r1.ts);
  r = ok(w, { verb: 'log-send', path: w.report, args: { sid: SID, comments: [{ id: c1.id, desc: 'on this file', body: 'c1\n\nyou reply to c1' }, { id: c2.id, desc: 'on "cut p95 latency by 40%"', body: 'c2' }], accepted: 0, rejected: 0, queued: false, watermark: W } });
  assert.deepEqual(r.unsent, { comments: [], replies: [], accepted: 0, rejected: 0, watermark: W });

  // New work after the send is unsent; the old is not.
  st = status(w, w.report);
  const c3 = comment(w, w.report, st, { note: 'c3' }).store.comments.find((c) => c.body === 'c3');
  st = status(w, w.report);
  r = ok(w, { verb: 'reply', path: w.report, args: { commentId: c2.id, note: 'you reply to c2' }, fence: fenceFor(st) });
  const r2 = r.store.comments.find((c) => c.id === c2.id).replies[0];
  assert.ok(c3.ts > W && r2.ts > W, 'later timestamps');
  assert.deepEqual(r.unsent, { comments: [c3.id], replies: [{ commentId: c2.id, ts: r2.ts }], accepted: 0, rejected: 0, watermark: W });

  // A later send that carried only decisions (watermark null) keeps the earlier watermark.
  r = ok(w, { verb: 'log-send', path: w.report, args: { sid: SID, comments: [], accepted: 0, rejected: 0, queued: false, watermark: null } });
  assert.deepEqual(r.unsent, { comments: [c3.id], replies: [{ commentId: c2.id, ts: r2.ts }], accepted: 0, rejected: 0, watermark: W });
  // Hand computation over the same inputs.
  const entries = readLogLines(logPathFor(r.storePath));
  assert.deepEqual(deriveUnsent(r.store, entries), r.unsent);
});

test('deriveUnsent counts accepts and rejects only after the last send and reads the whole log', () => {
  const store = { comments: [{ id: 'a', author: 'you', ts: 5, replies: [{ author: 'you', ts: 6 }, { author: 'web', ts: 7 }] }, { id: 'b', author: 'web', ts: 8, replies: [] }] };
  const entries = [
    { kind: 'send', watermark: 3 },
    { kind: 'accept', changes: [{ id: 'x' }, { id: 'y' }] },
    { kind: 'send', watermark: 4 },
    { kind: 'reject', changes: [{ id: 'z' }] },
    { kind: 'accept', changes: [{ id: 'q' }] },
    { kind: 'edit' },
  ];
  assert.deepEqual(deriveUnsent(store, entries), { comments: ['a'], replies: [{ commentId: 'a', ts: 6 }], accepted: 1, rejected: 1, watermark: 4 });
  assert.deepEqual(deriveUnsent(store, []), { comments: ['a'], replies: [{ commentId: 'a', ts: 6 }], accepted: 0, rejected: 0, watermark: null });
  assert.deepEqual(deriveUnsent(null, entries).comments, []);
  assert.deepEqual(deriveUnsent(store, [{ kind: 'send', watermark: 6 }]), { comments: [], replies: [], accepted: 0, rejected: 0, watermark: 6 });
});

test('the log reply is the last 200 entries oldest first with logTruncated, while unsent reads every entry', () => {
  const w = world();
  const st = status(w, w.report);
  const c = comment(w, w.report, st, { note: 'late' }).store.comments[0];
  const lp = logPathFor(st.storePath);
  const total = LOG_TAIL + 5;
  const lines = [];
  for (let i = 1; i <= total; i++) {
    // Only the FIRST entry carries a watermark covering the comment: a tail-only reader would
    // wrongly report the comment unsent.
    lines.push(JSON.stringify({ ts: new Date(i * 1000).toISOString(), kind: 'send', author: 'you', sid: SID, comments: [], accepted: 0, rejected: 0, queued: false, watermark: i === 1 ? c.ts : null, n: i }));
  }
  fs.writeFileSync(lp, lines.join('\n') + '\n');
  const r = status(w, w.report);
  assert.equal(r.log.length, LOG_TAIL);
  assert.equal(r.logTruncated, true);
  assert.equal(r.log[0].n, 6);
  assert.equal(r.log[LOG_TAIL - 1].n, total);
  assert.deepEqual(r.unsent, { comments: [], replies: [], accepted: 0, rejected: 0, watermark: c.ts });
  assert.equal(fileBytes(lp).toString(), lines.join('\n') + '\n', 'reading never rewrites');
});

test('a decision older than the log tail still reaches the panel: `decided` carries, from the WHOLE log, the accept or reject of every change a comment is bound to that the sidecar no longer holds', () => {
  const w = world();
  // a change, a comment bound to it, the change accepted: the accept entry names the id with its texts
  const st1 = edit(w, w.report, 'cut p95 latency by 40%', 'reduced p95 latency by 40%');
  const h = hunkFor(st1, 'cut p95 latency by 40%');
  const st2 = comment(w, w.report, st1, { suggestionId: h.id, note: 'Say cut, not reduced.' });
  assert.deepEqual(st2.decided, {}, 'the change is pending: nothing to remember for it');
  const st3 = accept(w, w.report, st2, [h.id]);
  assert.deepEqual(st3.decided, { [h.id]: { decision: 'accepted', oldText: 'cut p95 latency by 40%', newText: 'reduced p95 latency by 40%' } }, 'decided the moment the sidecar drops the change');
  assert.equal(st3.log.filter((e) => e.kind === 'accept').length, 1, '…and the tail carries the entry itself while it is recent');
  // then LOG_TAIL + 5 sends: the accept entry falls out of the tail the reply carries, and stays on disk
  const lp = logPathFor(st3.storePath);
  const lines = [];
  for (let i = 1; i <= LOG_TAIL + 5; i++) {
    lines.push(JSON.stringify({ ts: new Date(i * 1000).toISOString(), kind: 'send', author: 'you', sid: SID, comments: [], accepted: 0, rejected: 0, queued: false, watermark: null, n: i }));
  }
  fs.appendFileSync(lp, lines.join('\n') + '\n');
  const r = status(w, w.report);
  assert.equal(r.logTruncated, true);
  assert.equal(r.log.filter((e) => e.kind === 'accept').length, 0, 'the tail no longer holds the accept');
  assert.deepEqual(r.decided, { [h.id]: { decision: 'accepted', oldText: 'cut p95 latency by 40%', newText: 'reduced p95 latency by 40%' } }, 'the decision rides `decided`, read off the whole log');
  const c = r.store.comments.find((x) => x.suggestionId === h.id);
  assert.ok(c && c.resolved, 'the bound comment stays in the sidecar (resolved), which is why the panel needs the texts');
  // the pure derivation, on the edges: a pending or detached change is the sidecar's to describe, never the log's
  const entries = [{ kind: 'reject', changes: [{ id: 'x', oldText: 'a', newText: '' }] }, { kind: 'accept', changes: [{ id: 'x', oldText: 'a', newText: 'b' }, { id: 'y', oldText: '', newText: 'n' }] }];
  const bound = (id) => ({ id: 'c1', author: 'you', ts: 1, body: 'k', suggestionId: id, replies: [], resolved: false });
  assert.deepEqual(decidedFor({ suggestions: [], comments: [bound('x')] }, entries), { x: { decision: 'accepted', oldText: 'a', newText: 'b' } }, 'the NEWEST entry for the id');
  assert.deepEqual(decidedFor({ suggestions: [{ id: 'x' }], comments: [bound('x')] }, entries), {}, 'pending: the sidecar holds it');
  assert.deepEqual(decidedFor({ suggestions: [], detached: [{ id: 'x' }], comments: [bound('x')] }, entries), {}, 'detached: the sidecar holds it');
  assert.deepEqual(decidedFor({ suggestions: [], comments: [bound('y'), { id: 'c2', author: 'you', ts: 2, body: 'p', replies: [], resolved: false }] }, entries), { y: { decision: 'accepted', oldText: '', newText: 'n' } }, 'only bound comments ask; a plain comment adds nothing');
  assert.deepEqual(decidedFor({ suggestions: [], comments: [bound('z')] }, entries), {}, 'no entry for the id: nothing claimed');
  assert.deepEqual(decidedFor(null, entries), {}, 'no sidecar: nothing bound');
  assert.deepEqual(decidedFor({ suggestions: [], comments: [bound('x')] }, [{ kind: 'accept', changes: [{ id: 'x', oldText: 7 }] }, null, { kind: 'edit' }]), { x: { decision: 'accepted', oldText: '', newText: '' } }, 'a hand-edited entry reads defensively');
});

test('an unreadable log line is skipped with a note on stderr, never rewritten', () => {
  const w = world();
  const st = status(w, w.report);
  comment(w, w.report, st, { note: 'x' });
  const lp = logPathFor(st.storePath);
  const raw = JSON.stringify({ ts: 't', kind: 'edit', author: 'you' }) + '\n{torn\n';
  fs.writeFileSync(lp, raw);
  const r = host(w, { verb: 'status', path: w.report });
  assert.equal(r.code, 0);
  assert.equal(r.json.log.length, 1);
  assert.match(r.stderr, /1 unreadable line/);
  assert.equal(fs.readFileSync(lp, 'utf8'), raw);
});

// ── helpers the later slices write through ──────────────────────────

test('writeFileAtomic writes through a symlink, preserves the mode, and leaves no temp file', () => {
  const w = world();
  const target = path.join(w.root, 'docs', 'real.md');
  fs.writeFileSync(target, 'old\n');
  fs.chmodSync(target, 0o640);
  const link = path.join(w.root, 'docs', 'link.md');
  fs.symlinkSync(target, link);
  const before = fs.readdirSync(path.join(w.root, 'docs'));
  const ns = writeFileAtomic(link, 'new\n');
  assert.match(ns, NS_RE);
  assert.equal(fs.readFileSync(target, 'utf8'), 'new\n');
  assert.ok(fs.lstatSync(link).isSymbolicLink(), 'the symlink is intact');
  assert.equal(fs.statSync(target).mode & 0o777, 0o640);
  assert.deepEqual(fs.readdirSync(path.join(w.root, 'docs')).sort(), before.sort(), 'no temp file left');
  assert.equal(ns, statNs(target));
});

test('checkTooLarge refuses too-large above the kernel\'s 2 MB cap and passes below it', () => {
  assert.doesNotThrow(() => checkTooLarge('~/x.md', 'a'.repeat(TEXT_MAX_BYTES)));
  assert.throws(() => checkTooLarge('~/x.md', 'a'.repeat(TEXT_MAX_BYTES + 1)), (e) => e instanceof Refusal && e.code === 'too-large' && e.message.includes('~/x.md'));
  // Byte length, not character count: a multi-byte text trips it sooner.
  assert.throws(() => checkTooLarge('~/x.md', 'é'.repeat(TEXT_MAX_BYTES / 2 + 1)), (e) => e.code === 'too-large');
});

// ── the session's changes as seen through status ────────────────────

test('hunks are engine.toHunks over a track-edit change, and baseline arrives only when asked', () => {
  const w = world();
  writeTrackedPaths(w.root, ['docs/report.md']);
  cliOk(w, 'edit', ['--file', w.report, '--old', 'cut p95 latency by 40%', '--new', 'reduced p95 latency by 40%']);
  const cur = fs.readFileSync(w.report, 'utf8');
  assert.notEqual(cur, w.text);
  const st = status(w, w.report);
  assert.equal('baseline' in st, false);
  assert.equal(st.hunks.length, 1);
  assert.equal(st.hunks[0].author, 'web');
  assert.equal(st.hunks[0].kind, 'sub');
  assert.equal(st.hunks[0].oldText, 'cut p95 latency by 40%');
  assert.equal(st.hunks[0].newText, 'reduced p95 latency by 40%');
  assert.deepEqual(st.hunks, engine.toHunks(st.store.suggestions));
  assert.equal(st.store.suggestions[0].authorId, SID);
  const withBase = status(w, w.report, { baseline: true });
  assert.equal(withBase.baseline, w.text);
  assert.equal(withBase.baseline, engine.baselineOf(cur, withBase.store.suggestions));
  assert.deepEqual(withBase.trackedBy, { kind: 'file', entry: 'docs/report.md' });
  // A comment on the changed file keeps the change: one load-mutate-write, the rebase included.
  const r = comment(w, w.report, st, { note: 'Keep the number.' });
  assert.equal(r.store.suggestions.length, 1);
  assert.equal(r.hunks.length, 1);
  assert.deepEqual(readSidecar(r.storePath).fingerprint, fingerprintOf(cur));
});

test('a binary file takes a whole-file comment; the fingerprint is the CLIs\' UTF-8 reading and the bytes are untouched', () => {
  const w = world();
  const png = path.join(w.root, 'docs', 'chart.png');
  const bytes = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a, 0x00, 0x00, 0x00, 0x0d, 0xff, 0xfe, 0x80, 0x00]);
  fs.writeFileSync(png, bytes);
  const st = status(w, w.report);
  assert.equal(st.root, w.root);
  const r = ok(w, { verb: 'comment', path: png, args: { note: 'Axis labels are cut off.' }, fence: { storeMtimeNs: '' } });
  assert.deepEqual(fileBytes(png), bytes);
  const disk = readSidecar(r.storePath);
  assert.deepEqual(disk.fingerprint, fingerprintOf(fs.readFileSync(png, 'utf8')));
  assert.equal(disk.path, 'docs/chart.png');
  assert.match(disk.comments[0].id, /^\d+-0$/);
  // track-reply answers it like any other comment, and the bytes stay the same.
  cliOk(w, 'reply', ['--file', png, '--thread', disk.comments[0].id, '--note', 'Regenerated with wider margins.']);
  assert.deepEqual(fileBytes(png), bytes);
  assert.equal(readSidecar(r.storePath).comments[0].replies[0].author, 'web');
});

// ── accept and reject (Slice 2) ─────────────────────────────────────
// Every change these tests decide was recorded by the REAL track-edit, as the `web` session
// records them; the host then decides it the way the panel's buttons ask.

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
// The fence the panel sends for the verbs that write the file: the sidecar's mtime and the file's.
function fileFenceFor(st) { return { ...fenceFor(st), fileMtimeNs: st.fileMtimeNs }; }
function accept(w, file, st, ids) { return ok(w, { verb: 'accept', path: file, args: { ids }, fence: fenceFor(st) }); }
function acceptAll(w, file, st) { return ok(w, { verb: 'accept-all', path: file, args: {}, fence: fenceFor(st) }); }
function reject(w, file, st, ids) { return ok(w, { verb: 'reject', path: file, args: { ids }, fence: fileFenceFor(st) }); }
function rejectAll(w, file, st) { return ok(w, { verb: 'reject-all', path: file, args: {}, fence: fileFenceFor(st) }); }
// The reply after pruneIfClean removed the sidecar: the client's absent state.
function absentShape(r) {
  assert.equal(r.store, null);
  assert.equal(r.storeMtimeNs, null);
  assert.deepEqual(r.hunks, []);
}
const ISO_RE = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/;

test('accept removes the change from the sidecar only: the file keeps its text, the survivor keeps its place, and the next track-edit is a separate change', () => {
  const w = world();
  writeTrackedPaths(w.root, ['docs/report.md']);
  edit(w, w.report, 'cut p95 latency by 40%', 'reduced p95 latency by 40%');
  const st = edit(w, w.report, 'shipping the cache in v1.2', 'shipping the cache in v1.3');
  const cur = fs.readFileSync(w.report, 'utf8');
  assert.deepEqual(st.hunks.map((h) => h.kind), ['sub', 'sub']);
  const a = hunkFor(st, 'cut p95 latency by 40%');
  const b = hunkFor(st, 'shipping the cache in v1.2');
  const r = accept(w, w.report, st, [a.id]);
  assert.deepEqual(r.accepted, [a.id]);
  assert.equal('rejected' in r, false);
  assert.equal(fs.readFileSync(w.report, 'utf8'), cur, 'accept never touches the file');
  assert.equal(r.fileMtimeNs, st.fileMtimeNs);
  // The survivor keeps its place in the text (accept moves nothing) while its baseline span
  // moves: the accepted text is baseline now, so nothing precedes it and baseFrom equals curFrom.
  assert.equal(r.hunks.length, 1);
  assert.deepEqual({ ...r.hunks[0], baseFrom: 0, baseTo: 0 }, { ...b, baseFrom: 0, baseTo: 0 });
  assert.equal(r.hunks[0].baseFrom, b.curFrom);
  assert.equal(r.hunks[0].baseTo, b.curFrom + b.oldText.length);
  assert.deepEqual(r.store.suggestions.map((s) => s.id), [b.id]);
  assert.notEqual(r.storeMtimeNs, st.storeMtimeNs);
  assert.equal(r.storeMtimeNs, statNs(r.storePath));
  const disk = readSidecar(r.storePath);
  assert.equal(disk.v, 3);
  assert.deepEqual(disk.fingerprint, fingerprintOf(cur));
  assert.deepEqual(disk.suggestions.map((s) => s.id), [b.id]);
  assert.equal(disk.suggestions[0].authorId, SID, 'the survivor is the CLI\'s record, untouched');
  // The session's next edit over the accepted passage is a change of its own with the accepted
  // text as its baseline, not a revision folded into the old one: accepting is how a session's
  // later revisions become separate changes.
  const st2 = edit(w, w.report, 'reduced p95 latency by 40%', 'reduced p95 latency by 42%');
  assert.equal(st2.hunks.length, 2);
  const again = hunkFor(st2, 'reduced p95 latency by 40%');
  assert.equal(again.newText, 'reduced p95 latency by 42%');
  assert.notEqual(again.id, a.id);
});

test('accept-all with nothing else in the sidecar prunes it and replies the absent shape; a comment or a detached op keeps it', () => {
  const w = world();
  edit(w, w.report, 'cut p95 latency by 40%', 'reduced p95 latency by 40%');
  const st = edit(w, w.report, 'shipping the cache in v1.2', 'shipping the cache in v1.3');
  const ids = st.hunks.map((h) => h.id);
  const sp = st.storePath;
  const cur = fs.readFileSync(w.report, 'utf8');
  const r = acceptAll(w, w.report, st);
  assert.deepEqual(r.accepted, ids);
  absentShape(r);
  assert.equal(fs.existsSync(sp), false, 'pruneIfClean removed the sidecar');
  assert.equal(r.storePath, sp, 'the path is still named, so the client keeps watching it');
  assert.equal(r.root, w.root);
  assert.equal(fs.readFileSync(w.report, 'utf8'), cur);
  assert.deepEqual(r.log.map((e) => e.kind), ['accept']);
  assert.equal(r.log[0].changes.length, 2);
  assert.deepEqual(r.unsent, { comments: [], replies: [], accepted: 2, rejected: 0, watermark: null });
  // The log outlives the prune: status answers the absent state with the counts still unsent.
  const st2 = status(w, w.report);
  absentShape(st2);
  assert.equal(st2.unsent.accepted, 2);
  assert.deepEqual(fs.readdirSync(path.dirname(sp)), [path.basename(logPathFor(sp))]);

  // A comment, bound or not, keeps the sidecar: suggestions [] and the comment, nothing pruned.
  const w2 = world();
  const s2 = edit(w2, w2.report, 'cut p95 latency by 40%', 'reduced p95 latency by 40%');
  const withComment = comment(w2, w2.report, s2, { note: 'Fine as it is.' });
  const r2 = acceptAll(w2, w2.report, withComment);
  assert.ok(fs.existsSync(r2.storePath));
  assert.deepEqual(r2.store.suggestions, []);
  assert.deepEqual(r2.hunks, []);
  assert.equal(r2.store.comments.length, 1);
  assert.equal(r2.store.comments[0].resolved, false, 'a comment not bound to the change is left as it was');
  assert.match(r2.storeMtimeNs, NS_RE);
  assert.deepEqual(readSidecar(r2.storePath).fingerprint, fingerprintOf(fs.readFileSync(w2.report, 'utf8')));

  // A detached op (a change the load-time rebase could not re-place) keeps it too, pruneIfClean's
  // own rule; accept-all decides the pending changes and preserves the detached one for review.
  const w3 = world();
  const s3 = edit(w3, w3.report, 'cut p95 latency by 40%', 'reduced p95 latency by 40%');
  const disk = readSidecar(s3.storePath);
  disk.detached = [{ id: '1700000000000-9', author: 'web', ts: 1700000000000, kind: 'sub', from: 0, oldText: 'zzz', newText: 'qqq', anchor: { quote: 'qqq', prefix: '', suffix: '' } }];
  fs.writeFileSync(s3.storePath, JSON.stringify(disk, null, 2));
  const s3b = status(w3, w3.report);
  assert.equal(s3b.store.detached.length, 1);
  assert.equal(s3b.hunks.length, 1, 'a detached op is not a pending change');
  const r3 = acceptAll(w3, w3.report, s3b);
  assert.deepEqual(r3.accepted, [s3b.hunks[0].id]);
  assert.ok(fs.existsSync(r3.storePath));
  assert.deepEqual(r3.store.suggestions, []);
  assert.equal(r3.store.detached.length, 1, 'a detached op is preserved, never dropped by accept');
});

test('a file created by track-edit is one whole-file insertion: one ins hunk that swallows later same-author edits, and its accept clears the sidecar', () => {
  const w = world();
  writeTrackedPaths(w.root, ['docs/']);
  const created = path.join(w.root, 'docs', 'summary.md');
  const content = '# Summary\n\nThe cache cut p95 latency by 40%.\n';
  cliOk(w, 'edit', ['--file', created, '--old', '', '--new', content]);
  assert.equal(fs.readFileSync(created, 'utf8'), content);
  const st = status(w, created);
  assert.equal(st.hunks.length, 1);
  const h = st.hunks[0];
  assert.equal(h.kind, 'ins');
  assert.equal(h.curFrom, 0);
  assert.equal(h.curTo, content.length);
  assert.equal(h.oldText, '');
  assert.equal(h.newText, content);
  assert.equal(h.baseFrom, 0);
  assert.equal(h.baseTo, 0);
  assert.equal(h.author, 'web');
  assert.equal(status(w, created, { baseline: true }).baseline, '', 'the baseline of a created file is the empty text');
  // A second edit by the same session inside the insertion coalesces into it: still one change.
  cliOk(w, 'edit', ['--file', created, '--old', '40%', '--new', '41%']);
  const revised = content.replace('40%', '41%');
  const st2 = status(w, created);
  assert.equal(st2.hunks.length, 1);
  assert.equal(st2.hunks[0].id, h.id);
  assert.equal(st2.hunks[0].newText, revised);
  assert.equal(st2.hunks[0].oldText, '');
  const r = accept(w, created, st2, [h.id]);
  assert.deepEqual(r.accepted, [h.id]);
  absentShape(r);
  assert.equal(fs.existsSync(st.storePath), false);
  assert.equal(fs.readFileSync(created, 'utf8'), revised);
  assert.deepEqual(r.log.map((e) => ({ kind: e.kind, changes: e.changes })), [{ kind: 'accept', changes: [{ id: h.id, oldText: '', newText: revised }] }]);
  // After the accept the session's next edit is its own change with the accepted text as baseline.
  const st3 = edit(w, created, '41%', '42%');
  assert.equal(st3.hunks.length, 1);
  assert.equal(st3.hunks[0].kind, 'sub');
  assert.equal(st3.hunks[0].oldText, '41%');

  // Rejecting a whole-file insertion writes the engine's baseline, the empty text: the file stays,
  // empty, and the emptied sidecar is pruned.
  const w2 = world();
  const created2 = path.join(w2.root, 'docs', 'summary.md');
  cliOk(w2, 'edit', ['--file', created2, '--old', '', '--new', content]);
  const r2 = rejectAll(w2, created2, status(w2, created2));
  assert.equal(fs.readFileSync(created2, 'utf8'), '');
  absentShape(r2);
  assert.equal(r2.fileMtimeNs, statNs(created2));
});

test('reject applies the engine\'s reverse edits: the subset\'s baseline lands in the file, survivors are remapped, and the reply carries the fresh file mtime', () => {
  const w = world();
  writeTrackedPaths(w.root, ['docs/report.md']);
  edit(w, w.report, 'cut p95 latency by 40%', 'reduced p95 latency by 35%');
  edit(w, w.report, 'Cold starts remain slow on the first request of the day.\n', '');
  const st = edit(w, w.report, 'shipping the cache in v1.2', 'shipping the cache in v1.3');
  const cur = fs.readFileSync(w.report, 'utf8');
  assert.deepEqual(st.hunks.map((h) => h.kind), ['sub', 'del', 'sub'], 'D1: the engine\'s three kinds');
  const [a, b, c] = st.hunks;
  assert.equal(b.curFrom, b.curTo, 'a deletion is a point in the current text');
  assert.equal(b.newText, '');
  assert.equal(a.oldText, 'cut p95 latency by 40%');
  const ops = st.store.suggestions;
  const want = engine.baselineOf(cur, ops.filter((s) => s.id === a.id || s.id === b.id));
  assert.notEqual(want, cur);
  assert.notEqual(want, w.text, 'the subset\'s baseline still carries the third change');

  const r = reject(w, w.report, st, [b.id, a.id]);
  assert.deepEqual(r.rejected, [a.id, b.id], 'document order, whatever order the caller used');
  assert.equal('accepted' in r, false);
  const after = fs.readFileSync(w.report, 'utf8');
  assert.equal(after, want);
  assert.ok(after.includes('cut p95 latency by 40%') && after.includes('Cold starts remain slow'), 'the rejected changes are undone');
  assert.ok(after.includes('shipping the cache in v1.3'), 'the survivor\'s text stays');
  assert.match(r.fileMtimeNs, NS_RE);
  assert.equal(r.fileMtimeNs, statNs(w.report));
  assert.notEqual(r.fileMtimeNs, st.fileMtimeNs);
  assert.equal(r.hunks.length, 1);
  const c2 = r.hunks[0];
  assert.equal(c2.id, c.id);
  assert.equal(c2.newText, c.newText);
  assert.equal(c2.oldText, c.oldText);
  assert.equal(after.slice(c2.curFrom, c2.curTo), c2.newText, 'remapped into the new text');
  const shift = (a.oldText.length - a.newText.length) + (b.oldText.length - b.newText.length);
  assert.equal(c2.curFrom, c.curFrom + shift);
  assert.deepEqual(r.store.suggestions.map((s) => s.id), [c.id]);
  assert.equal(r.storeMtimeNs, statNs(r.storePath));
  const disk = readSidecar(r.storePath);
  assert.equal(disk.v, 3);
  assert.deepEqual(disk.fingerprint, fingerprintOf(after), 'the fingerprint describes the new file');
  assert.equal(disk.suggestions[0].authorId, SID);
  // The CLI reads the host's sidecar against the new file and adds to it: nothing was lost.
  const st2 = edit(w, w.report, 'Cold starts remain slow', 'Cold starts stay slow');
  assert.equal(st2.hunks.length, 2);
  // Reject-all from here restores the fixture and, with nothing else in the sidecar, prunes it.
  const r2 = rejectAll(w, w.report, st2);
  assert.deepEqual(r2.rejected, st2.hunks.map((h) => h.id));
  assert.equal(fs.readFileSync(w.report, 'utf8'), w.text);
  absentShape(r2);
  assert.equal(fs.existsSync(r.storePath), false);
  assert.equal(r2.fileMtimeNs, statNs(w.report));
  assert.deepEqual(r2.log.map((e) => [e.kind, e.changes.length]), [['reject', 2], ['reject', 2]]);
  assert.deepEqual(r2.unsent, { comments: [], replies: [], accepted: 0, rejected: 4, watermark: null });
});

test('a reject whose file write fails puts the prior sidecar bytes back, changes nothing, logs nothing, and refuses unreadable with the OS text',
  { skip: typeof process.getuid === 'function' && process.getuid() === 0 ? 'root ignores directory modes' : false }, () => {
    const w = world();
    const st = edit(w, w.report, 'cut p95 latency by 40%', 'reduced p95 latency by 40%');
    const cur = fs.readFileSync(w.report, 'utf8');
    const sidecarBytes = fileBytes(st.storePath);
    const docs = path.dirname(w.report);
    const listing = fs.readdirSync(docs).sort();
    // writeFileAtomic creates its temp file beside the file, so a read-only directory fails the
    // file write after the sidecar was saved: the case the rollback exists for.
    fs.chmodSync(docs, 0o555);
    let r;
    try {
      r = refused(w, { verb: 'reject-all', path: w.report, args: {}, fence: fileFenceFor(st) }, 'unreadable');
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
    assert.equal(fs.existsSync(logPathFor(st.storePath)), false, 'a refused reject logs nothing');
    assert.deepEqual(fs.readdirSync(path.dirname(st.storePath)), [path.basename(st.storePath)], 'no restore temp left in .trackchanges');
    // The store is whole: a reload sees the same change, and the reject then succeeds.
    const st2 = status(w, w.report);
    assert.deepEqual(st2.hunks, st.hunks);
    assert.equal(st2.storeMtimeNs, statNs(st.storePath));
    const r2 = rejectAll(w, w.report, st2);
    assert.deepEqual(r2.rejected, [st.hunks[0].id]);
    assert.equal(fs.readFileSync(w.report, 'utf8'), w.text);
  });

test('accept and reject fences: "" over an existing sidecar, a stale sidecar mtime, a stale or "" file mtime, and a missing key', () => {
  const w = world();
  const st = edit(w, w.report, 'cut p95 latency by 40%', 'reduced p95 latency by 40%');
  const id = st.hunks[0].id;
  const cur = fs.readFileSync(w.report, 'utf8');
  const bytes = fileBytes(st.storePath);
  const unchanged = () => {
    assert.deepEqual(fileBytes(st.storePath), bytes);
    assert.equal(fs.readFileSync(w.report, 'utf8'), cur);
    assert.equal(fs.existsSync(logPathFor(st.storePath)), false);
  };
  const decisions = [['accept', { ids: [id] }], ['accept-all', {}], ['reject', { ids: [id] }], ['reject-all', {}]];
  for (const [verb, args] of decisions) {
    const fileNs = { fileMtimeNs: st.fileMtimeNs };
    const gone = refused(w, { verb, path: w.report, args, fence: { storeMtimeNs: '', ...fileNs } }, 'store-moved');
    assert.match(gone.error, /appeared on disk/);
    const stale = refused(w, { verb, path: w.report, args, fence: { storeMtimeNs: '1', ...fileNs } }, 'store-moved');
    assert.match(stale.error, /changed on disk/);
    assert.ok(stale.error.includes('~/notes-api/docs/report.md'), stale.error);
    unchanged();
  }
  for (const [verb, args] of decisions.slice(2)) {
    const stale = refused(w, { verb, path: w.report, args, fence: { storeMtimeNs: st.storeMtimeNs, fileMtimeNs: '1' } }, 'file-moved');
    assert.ok(stale.error.includes('~/notes-api/docs/report.md'), stale.error);
    assert.match(stale.error, /changed on disk/);
    refused(w, { verb, path: w.report, args, fence: { storeMtimeNs: st.storeMtimeNs, fileMtimeNs: '' } }, 'file-moved');
    // A missing file fence is a caller bug: a crash before any disk check, never a write.
    const missing = host(w, { verb, path: w.report, args, fence: { storeMtimeNs: st.storeMtimeNs } });
    assert.notEqual(missing.code, 0);
    assert.equal(missing.stdout, '');
    assert.match(missing.stderr, /fence\.fileMtimeNs is required/);
    unchanged();
  }
  const noStore = host(w, { verb: 'accept', path: w.report, args: { ids: [id] } });
  assert.notEqual(noStore.code, 0);
  assert.match(noStore.stderr, /fence\.storeMtimeNs is required/);
  const noIds = host(w, { verb: 'accept', path: w.report, args: {}, fence: fenceFor(st) });
  assert.notEqual(noIds.code, 0);
  assert.match(noIds.stderr, /needs ids/);
  const emptyIds = host(w, { verb: 'reject', path: w.report, args: { ids: [] }, fence: fileFenceFor(st) });
  assert.notEqual(emptyIds.code, 0);
  assert.match(emptyIds.stderr, /needs ids/);
  const badId = host(w, { verb: 'accept', path: w.report, args: { ids: [''] }, fence: fenceFor(st) });
  assert.notEqual(badId.code, 0);
  unchanged();
  // A raw edit moves only the file's mtime: reject refuses file-moved with the sidecar fence still
  // good, while accept, which never writes the file, does not fence on it and proceeds.
  fs.writeFileSync(w.report, cur + '\n');
  const raw = refused(w, { verb: 'reject-all', path: w.report, args: {}, fence: fileFenceFor(st) }, 'file-moved');
  assert.match(raw.error, /changed on disk/);
  assert.deepEqual(fileBytes(st.storePath), bytes);
  const r = accept(w, w.report, st, [id]);
  assert.deepEqual(r.accepted, [id]);
  // A track-edit moves both; the sidecar fence answers first.
  const w2 = world();
  const s1 = edit(w2, w2.report, 'cut p95 latency by 40%', 'reduced p95 latency by 40%');
  edit(w2, w2.report, 'shipping the cache in v1.2', 'shipping the cache in v1.3');
  refused(w2, { verb: 'reject-all', path: w2.report, args: {}, fence: fileFenceFor(s1) }, 'store-moved');
  refused(w2, { verb: 'accept', path: w2.report, args: { ids: [s1.hunks[0].id] }, fence: fenceFor(s1) }, 'store-moved');
});

test('comment {suggestionId} writes a change comment with no anchor and no target, track-reply answers it, and accept keeps it as resolved', () => {
  const w = world();
  const st = edit(w, w.report, 'cut p95 latency by 40%', 'reduced p95 latency by 40%');
  const h = st.hunks[0];
  const r = ok(w, { verb: 'comment', path: w.report, args: { suggestionId: h.id, note: '  Keep the exact number.  ' }, fence: fenceFor(st) });
  const c = readSidecar(r.storePath).comments[0];
  assert.deepEqual(Object.keys(c), ['id', 'author', 'ts', 'suggestionId', 'body', 'replies', 'resolved']);
  assert.equal(c.suggestionId, h.id);
  assert.equal(typeof c.ts, 'number');
  assert.equal(c.id, `${c.ts}-${h.curFrom}`);
  assert.equal(c.author, 'you');
  assert.equal(c.body, 'Keep the exact number.');
  assert.deepEqual(c.replies, []);
  assert.equal(c.resolved, false);
  assert.equal('anchor' in c, false);
  assert.equal('target' in c, false);
  assert.equal('authorId' in c, false);
  assert.deepEqual(r.store.comments[0], c);
  assert.equal(r.hunks.length, 1, 'the change stays pending');
  assert.deepEqual(r.unsent.comments, [c.id]);
  assert.equal(fs.readFileSync(w.report, 'utf8').includes('reduced p95'), true, 'the file is untouched');
  // The session answers it with track-reply; the binding survives the CLI's load and save.
  cliOk(w, 'reply', ['--file', w.report, '--thread', c.id, '--note', 'Kept.']);
  const after = readSidecar(r.storePath).comments[0];
  assert.deepEqual({ ...after, replies: [] }, c);
  assert.equal(after.replies.length, 1);
  assert.equal(after.replies[0].author, 'web');
  assert.equal(after.replies[0].body, 'Kept.');
  // Accept marks it resolved and keeps every field; the comment keeps the sidecar alive.
  const st2 = status(w, w.report);
  const r2 = accept(w, w.report, st2, [h.id]);
  assert.deepEqual(r2.accepted, [h.id]);
  assert.deepEqual(r2.hunks, []);
  assert.ok(fs.existsSync(r2.storePath), 'a bound comment keeps the sidecar');
  const disk = readSidecar(r2.storePath);
  assert.deepEqual(disk.suggestions, []);
  assert.deepEqual(disk.comments, [{ ...after, resolved: true }]);
  assert.equal(disk.comments[0].suggestionId, h.id, 'the binding stays, so the id a sent message named still answers');
  assert.deepEqual(r2.store.comments, disk.comments);
  // ...and track-reply still reaches it after the accept.
  cliOk(w, 'reply', ['--file', w.report, '--thread', c.id, '--note', 'Thanks.']);
  assert.equal(readSidecar(r2.storePath).comments[0].replies.length, 2);
  // A change comment on an accepted (no longer pending) change refuses no-change.
  refused(w, { verb: 'comment', path: w.report, args: { suggestionId: h.id, note: 'Again?' }, fence: fenceFor(status(w, w.report)) }, 'no-change');
  // Anchor or target beside suggestionId is a caller bug.
  const both = host(w, { verb: 'comment', path: w.report, args: { suggestionId: h.id, anchor: { quote: 'x' }, note: 'n' }, fence: fenceFor(status(w, w.report)) });
  assert.notEqual(both.code, 0);
  assert.match(both.stderr, /takes no anchor/);
});

test('accept resolves every comment bound by suggestionId, anchor or not, and leaves unbound comments alone', () => {
  const w = world();
  const { anchor, hintOffset } = anchorAt(w.text, 'cut p95 latency by 40%', 0);
  let st = comment(w, w.report, status(w, w.report), { anchor, note: 'Say reduced, not cut.', hintOffset });
  const passage = st.store.comments[0];
  st = comment(w, w.report, st, { note: 'Add a date.' });
  const whole = st.store.comments[1];
  // The session answers the passage comment with a tracked edit bound to it: the comment keeps
  // its anchor and gains the change's id (store-io's addThreadEditTurn), the shape the plan's
  // contract section describes.
  cliOk(w, 'edit', ['--file', w.report, '--thread', passage.id, '--old', 'cut p95 latency by 40%', '--new', 'reduced p95 latency by 40%']);
  st = edit(w, w.report, 'shipping the cache in v1.2', 'shipping the cache in v1.3');
  assert.equal(st.hunks.length, 2);
  const answered = st.store.comments.find((c) => c.id === passage.id);
  assert.deepEqual(answered.anchor, passage.anchor, 'the passage comment keeps its anchor');
  assert.equal(answered.suggestionId, hunkFor(st, 'cut p95 latency by 40%').id);
  assert.equal(answered.replies[0].kind, 'edit');
  // Accepting only the OTHER change resolves nothing.
  const other = hunkFor(st, 'shipping the cache in v1.2');
  let r = accept(w, w.report, st, [other.id]);
  assert.deepEqual(r.store.comments.map((c) => c.resolved), [false, false]);
  // accept-all resolves the bound one and keeps both.
  r = acceptAll(w, w.report, r);
  assert.deepEqual(r.accepted, [answered.suggestionId]);
  assert.equal(r.store.comments.length, 2);
  const byId = Object.fromEntries(r.store.comments.map((c) => [c.id, c]));
  assert.equal(byId[passage.id].resolved, true);
  assert.deepEqual(byId[passage.id].anchor, passage.anchor);
  assert.equal(byId[passage.id].suggestionId, answered.suggestionId);
  assert.deepEqual(byId[passage.id].replies, answered.replies);
  assert.deepEqual(byId[whole.id], whole, 'the whole-file comment is untouched');
  assert.ok(fs.existsSync(r.storePath));
  assert.deepEqual(readSidecar(r.storePath).comments, r.store.comments);
  assert.deepEqual(r.hunks, []);
});

test('a change that is no longer pending refuses no-change by id, after the fence has had its say', () => {
  const w = world();
  // Nothing pending at all: no sidecar under a "" fence, on a project file and on a loose file.
  let r = refused(w, { verb: 'accept', path: w.report, args: { ids: ['1700000000000-4'] }, fence: { storeMtimeNs: '' } }, 'no-change');
  assert.ok(r.error.includes('1700000000000-4') && r.error.includes('~/notes-api/docs/report.md'), r.error);
  r = refused(w, { verb: 'accept-all', path: w.report, args: {}, fence: { storeMtimeNs: '' } }, 'no-change');
  assert.match(r.error, /no changes are pending/);
  refused(w, { verb: 'reject', path: w.report, args: { ids: ['x'] }, fence: { storeMtimeNs: '', fileMtimeNs: statNs(w.report) } }, 'no-change');
  refused(w, { verb: 'reject-all', path: w.report, args: {}, fence: { storeMtimeNs: '', fileMtimeNs: statNs(w.report) } }, 'no-change');
  refused(w, { verb: 'comment', path: w.loose, args: { suggestionId: 'x', note: 'hi' }, fence: { storeMtimeNs: '' } }, 'no-change');
  refused(w, { verb: 'accept-all', path: w.loose, args: {}, fence: { storeMtimeNs: '' } }, 'no-change');
  refused(w, { verb: 'reject-all', path: w.loose, args: {}, fence: { storeMtimeNs: '', fileMtimeNs: statNs(w.loose) } }, 'no-change');
  assert.equal(fs.existsSync(path.join(w.root, '.trackchanges')), false, 'a refused decision creates nothing');
  assert.equal(fs.existsSync(path.join(w.looseDir, '.trackchanges')), false);
  assert.equal(fs.readFileSync(w.report, 'utf8'), w.text);

  // A pending change beside an unknown id: the whole request refuses and nothing is decided.
  const st = edit(w, w.report, 'cut p95 latency by 40%', 'reduced p95 latency by 40%');
  const id = st.hunks[0].id;
  const bytes = fileBytes(st.storePath);
  r = refused(w, { verb: 'accept', path: w.report, args: { ids: [id, 'nope'] }, fence: fenceFor(st) }, 'no-change');
  assert.ok(r.error.includes('nope') && !r.error.includes(id), r.error);
  refused(w, { verb: 'reject', path: w.report, args: { ids: ['nope'] }, fence: fileFenceFor(st) }, 'no-change');
  refused(w, { verb: 'comment', path: w.report, args: { suggestionId: 'nope', note: 'hi' }, fence: fenceFor(st) }, 'no-change');
  assert.deepEqual(fileBytes(st.storePath), bytes);
  assert.equal(fs.existsSync(logPathFor(st.storePath)), false);
  assert.deepEqual(status(w, w.report).hunks, st.hunks);

  // Decided once, the id is gone: a second accept with the fresh fence refuses by id.
  const r1 = accept(w, w.report, st, [id]);
  r = refused(w, { verb: 'accept', path: w.report, args: { ids: [id] }, fence: fenceFor(r1) }, 'no-change');
  assert.ok(r.error.includes(id), r.error);

  // A track-edit landing mid-round: the fence answers first (store-moved); after a reload, an id
  // that coalesced into an adjacent change by the same author is no longer pending under its name.
  const w2 = world();
  const s1 = edit(w2, w2.report, 'p95', 'p90');
  const idA = s1.hunks[0].id;
  cliOk(w2, 'edit', ['--file', w2.report, '--old', 'cut ', '--new', 'reduced ']);
  refused(w2, { verb: 'accept', path: w2.report, args: { ids: [idA] }, fence: fenceFor(s1) }, 'store-moved');
  const s2 = status(w2, w2.report);
  assert.equal(s2.hunks.length, 1, 'the adjacent edits coalesced into one change');
  assert.notEqual(s2.hunks[0].id, idA);
  assert.equal(s2.hunks[0].newText, 'reduced p90');
  assert.equal(s2.hunks[0].oldText, 'cut p95');
  r = refused(w2, { verb: 'accept', path: w2.report, args: { ids: [idA] }, fence: fenceFor(s2) }, 'no-change');
  assert.ok(r.error.includes(idA), r.error);
  refused(w2, { verb: 'reject', path: w2.report, args: { ids: [idA] }, fence: fileFenceFor(s2) }, 'no-change');
  refused(w2, { verb: 'comment', path: w2.report, args: { suggestionId: idA, note: 'x' }, fence: fenceFor(s2) }, 'no-change');
  // ...and the coalesced change decides under its own id.
  assert.deepEqual(accept(w2, w2.report, s2, [s2.hunks[0].id]).accepted, [s2.hunks[0].id]);
});

test('each accept and reject appends one log entry with the ids and their texts, and the unsent counts run until the next log-send', () => {
  const w = world();
  edit(w, w.report, 'cut p95 latency by 40%', 'reduced p95 latency by 40%');
  edit(w, w.report, 'Cold starts remain slow on the first request of the day.\n', '');
  let st = edit(w, w.report, 'shipping the cache in v1.2', 'shipping the cache in v1.3');
  const [a, b, c] = st.hunks;
  const lp = logPathFor(st.storePath);
  let r = accept(w, w.report, st, [c.id]);
  let lines = readLogLines(lp);
  assert.equal(lines.length, 1);
  assert.deepEqual({ ...lines[0], ts: 'T' }, { ts: 'T', kind: 'accept', author: 'you', changes: [{ id: c.id, oldText: 'shipping the cache in v1.2', newText: 'shipping the cache in v1.3' }] });
  assert.match(lines[0].ts, ISO_RE);
  assert.deepEqual(r.log, lines);
  assert.deepEqual(r.unsent, { comments: [], replies: [], accepted: 1, rejected: 0, watermark: null });
  r = reject(w, w.report, r, [a.id, b.id]);
  lines = readLogLines(lp);
  assert.equal(lines.length, 2);
  assert.deepEqual({ ...lines[1], ts: 'T' }, {
    ts: 'T', kind: 'reject', author: 'you', changes: [
      { id: a.id, oldText: 'cut p95 latency by 40%', newText: 'reduced p95 latency by 40%' },
      { id: b.id, oldText: 'Cold starts remain slow on the first request of the day.\n', newText: '' },
    ],
  });
  assert.match(lines[1].ts, ISO_RE);
  absentShape(r);
  assert.deepEqual(r.unsent, { comments: [], replies: [], accepted: 1, rejected: 2, watermark: null });
  assert.deepEqual(deriveUnsent(r.store, lines), r.unsent);
  // The send carries the counts; after it they are spent.
  r = ok(w, { verb: 'log-send', path: w.report, args: { sid: SID, sessionName: 'web', comments: [], accepted: 1, rejected: 2, queued: false, watermark: null } });
  assert.deepEqual(r.unsent, { comments: [], replies: [], accepted: 0, rejected: 0, watermark: null });
  assert.deepEqual(readLogLines(lp).map((e) => e.kind), ['accept', 'reject', 'send']);
  // A decision after the send counts again; the earlier lines are the same bytes.
  const before = fileBytes(lp);
  st = edit(w, w.report, 'cut p95 latency by 40%', 'trimmed p95 latency by 40%');
  r = acceptAll(w, w.report, st);
  assert.deepEqual(r.unsent, { comments: [], replies: [], accepted: 1, rejected: 0, watermark: null });
  const after = fileBytes(lp);
  assert.ok(after.length > before.length && after.subarray(0, before.length).equals(before), 'the log is only appended to');
  assert.deepEqual(readLogLines(lp).map((e) => e.kind), ['accept', 'reject', 'send', 'accept']);
});

test('reject refuses not-text before any write on a file whose bytes are not UTF-8; accept, which writes no file, proceeds', () => {
  const w = world();
  const notes = path.join(w.root, 'docs', 'notes.md');
  const bytes = Buffer.concat([Buffer.from('Hello world.\n'), Buffer.from([0xff, 0xfe]), Buffer.from('\nMore.\n')]);
  fs.writeFileSync(notes, bytes);
  const decoded = bytes.toString('utf8');
  const sp = storePathFor(w.root, notes);
  const op = { id: '1700000000000-0', author: 'web', authorId: SID, ts: 1700000000000, kind: 'sub', from: 0, oldText: 'Hi', newText: 'Hello', anchor: engine.makeAnchor(decoded, 0, 5) };
  saveStore(w.root, sp, { v: 3, path: 'docs/notes.md', suggestions: [op], comments: [] }, decoded);
  const st = status(w, notes);
  assert.equal(st.hunks.length, 1);
  assert.equal(st.hunks[0].id, op.id);
  const sidecar = fileBytes(sp);
  const r = refused(w, { verb: 'reject-all', path: notes, args: {}, fence: fileFenceFor(st) }, 'not-text');
  assert.ok(r.error.includes('~/notes-api/docs/notes.md'), r.error);
  assert.match(r.error, /not UTF-8 text/);
  refused(w, { verb: 'reject', path: notes, args: { ids: [op.id] }, fence: fileFenceFor(st) }, 'not-text');
  assert.deepEqual(fileBytes(notes), bytes, 'the bytes are untouched');
  assert.deepEqual(fileBytes(sp), sidecar, 'the sidecar is untouched');
  assert.equal(fs.existsSync(logPathFor(sp)), false);
  const r2 = acceptAll(w, notes, st);
  assert.deepEqual(r2.accepted, [op.id]);
  assert.deepEqual(fileBytes(notes), bytes);
});

test('reject refuses too-large before any write when the restored text would exceed the 2 MB cap', () => {
  const w = world();
  const big = path.join(w.root, 'docs', 'big.md');
  const filler = 'x'.repeat(TEXT_MAX_BYTES - 100) + '\n';
  const chunk = 'REMOVE THIS CHUNK ' + 'y'.repeat(500) + '\n';
  // The baseline is over the cap; the file after the session's deletion is under it.
  fs.writeFileSync(big, 'head\n' + chunk + filler);
  cliOk(w, 'edit', ['--file', big, '--old', chunk, '--new', '']);
  const cur = fs.readFileSync(big, 'utf8');
  assert.ok(Buffer.byteLength(cur, 'utf8') <= TEXT_MAX_BYTES);
  const st = status(w, big);
  assert.equal(st.hunks.length, 1);
  assert.equal(st.hunks[0].kind, 'del');
  const sidecar = fileBytes(st.storePath);
  const r = refused(w, { verb: 'reject-all', path: big, args: {}, fence: fileFenceFor(st) }, 'too-large');
  assert.ok(r.error.includes('~/notes-api/docs/big.md'), r.error);
  assert.equal(fs.readFileSync(big, 'utf8'), cur);
  assert.deepEqual(fileBytes(st.storePath), sidecar);
  assert.equal(fs.existsSync(logPathFor(st.storePath)), false);
  assert.equal(st.fileMtimeNs, statNs(big));
});

test('applyEdits applies the engine\'s reverse edits highest offset first and throws on one that does not fit', () => {
  assert.equal(applyEdits('abcdef', [{ from: 4, to: 6, insert: 'X' }, { from: 1, to: 2, insert: '' }]), 'acdX');
  assert.equal(applyEdits('abc', [{ from: 3, insert: 'd' }]), 'abcd');
  assert.equal(applyEdits('abc', []), 'abc');
  assert.throws(() => applyEdits('abc', [{ from: 2, to: 4, insert: '' }]), /does not fit/);
  assert.throws(() => applyEdits('abc', [{ from: -1, to: 0, insert: '' }]), /does not fit/);
  assert.throws(() => applyEdits('abc', [{ from: 2, to: 1, insert: '' }]), /does not fit/);
  assert.throws(() => applyEdits('abc', [{ from: 1.5, to: 2, insert: '' }]), /does not fit/);
  // Ascending order would shift the second edit onto moved text: refused, not applied.
  assert.throws(() => applyEdits('abcdef', [{ from: 0, to: 1, insert: 'ZZ' }, { from: 2, to: 3, insert: '' }]), /does not fit/);
  // Applying every reverse edit is the engine's baseline, for the whole set and for a subset.
  const cur = 'The cat sat on the mat.';
  const ops = [
    { id: 'a', author: 'web', ts: 1, kind: 'sub', from: 4, oldText: 'dog', newText: 'cat' },
    { id: 'b', author: 'web', ts: 2, kind: 'del', from: 12, oldText: 'quietly ', newText: '' },
    { id: 'c', author: 'api', ts: 3, kind: 'ins', from: 19, oldText: '', newText: 'mat' },
  ];
  assert.equal(applyEdits(cur, engine.rejectAll(ops).edits), 'The dog sat quietly on the .');
  assert.equal(applyEdits(cur, engine.rejectAll(ops).edits), engine.baselineOf(cur, ops));
  const some = engine.rejectSuggestions(ops, ['a', 'c']);
  assert.equal(applyEdits(cur, some.edits), engine.baselineOf(cur, ops.filter((o) => o.id !== 'b')));
  assert.equal(applyEdits(cur, some.edits), 'The dog sat on the .');
  assert.deepEqual(some.suggestions.map((s) => [s.id, s.from]), [['b', 12]], 'the survivor keeps its place when nothing before it moved');
});

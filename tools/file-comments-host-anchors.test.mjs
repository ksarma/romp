// The anchors follow-on (2026-09-07; plans/file-review.md, The contract and The host script): a
// passage comment on text that recurs must anchor reliably. Two changes to the host script are pinned
// here. (1) The stored anchor's context widens until it locates uniquely: makeAnchor at the located
// position with 24 characters, then 48, ... up to ANCHOR_CTX_CAP, stopping at the first width whose
// anchor has one best hit in the whole text, so a passage unique at 24 keeps track-comment's anchor
// and a passage that recurs with the same 24 characters around each copy is told from the others by
// more of its surroundings, in the three fields every host reads. Past the cap the anchor is saved at
// the cap, never refused. (2) The comment carries `anchorAt`, the offset the anchor located at, the
// second romp-only field after `target`: set at creation, refreshed on every sidecar write the host
// makes for each comment whose anchor locates, with the stored position itself as the tie-break where
// copies tie (so a comment on one of several identical paragraphs follows that copy through edits
// above, however many host writes apart), left as it was where the anchor is gone or ties with no
// stored position, never added to a comment without an anchor, and written back whole by the vendored
// CLIs. A tie the client's hint settles is placed; only a tie with no hint refuses `anchor-ambiguous`.
// Hermetic, the file-comments-host.test.mjs way: the synthetic notes-api world under a scratch
// directory, the host as a child process with one JSON request on stdin, and the REAL vendored CLIs
// as child processes where a test says the session did something. Synthetic fixtures only.
// Run: node --test tools/file-comments-host-anchors.test.mjs
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

import { loadStore, saveStore } from '../vendor/track-changents/store-io.mjs';
import { locateExact, uniqueAnchor, ANCHOR_CTX, ANCHOR_CTX_STEP, ANCHOR_CTX_CAP } from './file-comments-host.mjs';
import { tinyPng } from '../tests/fixtures/file_comments/tiny-png.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const HOST = path.join(REPO, 'tools', 'file-comments-host.mjs');
const VENDOR = path.join(REPO, 'vendor', 'track-changents');
const FIX = path.join(REPO, 'tests', 'fixtures', 'file_comments');
const engine = createRequire(import.meta.url)(path.join(VENDOR, 'engine.js'));

const SID = '11111111-2222-3333-4444-555555555555';

let SCRATCH;
before(() => { SCRATCH = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-fc-anchors-')); });
after(() => { try { fs.rmSync(SCRATCH, { recursive: true, force: true }); } catch { /* ignore */ } });

// ── the world ───────────────────────────────────────────────────────
// The fixture report has a line repeated four times ("- retry on timeout", told apart at 24
// characters by the heading above and below the list) and a sentence repeated in two paragraphs
// ("Ship it.", whose 24 characters either side are the same in both; the "## Day 1" / "## Day 2"
// headings lie 48 characters back). A third file, repeat.md, is generated: one paragraph over a
// thousand characters long, three times, so a phrase in its middle has identical surroundings for
// more than ANCHOR_CTX_CAP characters on both sides of every copy.
const PARA = ('The quick brown fox jumps over the lazy dog. '.repeat(12)
  + 'Here is the marker phrase to comment on. '
  + 'Pack my box with five dozen liquor jugs. '.repeat(12)).trim();
const REPEAT = `# Repeats\n\n${PARA}\n\n${PARA}\n\n${PARA}\n`;
const MARKER = 'the marker phrase';
assert.ok(PARA.indexOf(MARKER) > ANCHOR_CTX_CAP && PARA.length - PARA.indexOf(MARKER) - MARKER.length > ANCHOR_CTX_CAP,
  'the fixture: the phrase sits more than the cap from both ends of its paragraph');

let worlds = 0;
function world() {
  const home = path.join(SCRATCH, `w${++worlds}`, 'home');
  const root = path.join(home, 'notes-api');
  fs.mkdirSync(path.join(root, '.git'), { recursive: true });
  fs.mkdirSync(path.join(root, 'docs'));
  fs.copyFileSync(path.join(FIX, 'report.md'), path.join(root, 'docs', 'report.md'));
  fs.writeFileSync(path.join(root, 'docs', 'repeat.md'), REPEAT);
  return {
    home, root,
    report: path.join(root, 'docs', 'report.md'),
    repeat: path.join(root, 'docs', 'repeat.md'),
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
  return r.json;
}
// The real vendored CLIs, run as an agent session named `web` would run them.
function cliOk(w, name, args) {
  const r = spawnSync(process.execPath, [path.join(VENDOR, 'cli', `track-${name}.mjs`), ...args],
    { encoding: 'utf8', env: env(w, { ROMP_SESSION_NAME: 'web', ROMP_SID: SID }) });
  assert.equal(r.status, 0, `track-${name} failed: ${r.stderr}`);
  return r;
}
function status(w, file) { return ok(w, { verb: 'status', path: file, args: {} }); }
function fenceFor(st) { return { storeMtimeNs: st.storeMtimeNs == null ? '' : st.storeMtimeNs }; }
function comment(w, file, args) { return ok(w, { verb: 'comment', path: file, args, fence: fenceFor(status(w, file)) }); }
function readSidecar(sp) { return JSON.parse(fs.readFileSync(sp, 'utf8')); }

// The anchor the browser sends: the engine's 24 characters at the nth occurrence, and the selection's
// start offset as the hint.
function nth(text, quote, n) {
  let i = -1;
  for (let k = 0; k <= n; k++) i = text.indexOf(quote, i + 1);
  assert.ok(i >= 0, `fixture lacks occurrence ${n} of ${JSON.stringify(quote)}`);
  return i;
}
function fromBrowser(text, quote, n) {
  const idx = nth(text, quote, n);
  return { anchor: engine.makeAnchor(text, idx, idx + quote.length), hintOffset: idx, idx };
}
// One best hit, at `at`: the engine's earliest and latest tied hits agree there.
function locatesOnlyAt(text, anchor, at) {
  return engine.locateAnchor(text, anchor, 0).from === at && engine.locateAnchor(text, anchor, text.length).from === at;
}
const ctxOf = (anchor) => [anchor.prefix.length, anchor.suffix.length];

// ── the widening ────────────────────────────────────────────────────

test('the constants: 24 characters to start, 24 more at a time, a cap of 480', () => {
  assert.equal(ANCHOR_CTX, 24);
  assert.equal(ANCHOR_CTX_STEP, 24);
  assert.equal(ANCHOR_CTX_CAP, 480);
});

test('uniqueAnchor keeps 24 characters where that is unique, widens one step where the copies share their 24, and stops at the cap where they share more', () => {
  const w = world();
  // "retry on timeout", third of four identical lines: the headings above and below the list are
  // within 24 characters, so the engine's default anchor already has one best hit.
  const retry = nth(w.text, 'retry on timeout', 2);
  const u1 = uniqueAnchor(w.text, retry, retry + 'retry on timeout'.length);
  assert.equal(u1.unique, true);
  assert.deepEqual(u1.anchor, engine.makeAnchor(w.text, retry, retry + 'retry on timeout'.length), 'track-comment\'s own anchor');
  assert.deepEqual(ctxOf(u1.anchor), [24, 24]);
  // "Ship it.", second of two: the same 24 characters either side; the heading 48 back tells them apart.
  const ship = nth(w.text, 'Ship it.', 1);
  const at24 = engine.makeAnchor(w.text, ship, ship + 'Ship it.'.length);
  assert.equal(locatesOnlyAt(w.text, at24, ship), false, 'at 24 the two copies tie');
  const u2 = uniqueAnchor(w.text, ship, ship + 'Ship it.'.length);
  assert.equal(u2.unique, true);
  assert.deepEqual(u2.anchor, engine.makeAnchor(w.text, ship, ship + 'Ship it.'.length, 48), 'one step wider, no more');
  assert.equal(u2.anchor.prefix.length, 48);
  assert.ok(u2.anchor.prefix.includes('2\n\nThe tests'), 'the prefix now reaches into "## Day 2"');
  assert.ok(u2.anchor.suffix.length <= 48, 'the suffix is what the file has left');
  assert.equal(locatesOnlyAt(w.text, u2.anchor, ship), true);
  // the first copy widens the same way and lands on itself
  const ship0 = nth(w.text, 'Ship it.', 0);
  const u0 = uniqueAnchor(w.text, ship0, ship0 + 'Ship it.'.length);
  assert.deepEqual([u0.unique, ctxOf(u0.anchor)], [true, [48, 48]]);
  assert.equal(locatesOnlyAt(w.text, u0.anchor, ship0), true);
  // the marker phrase in the second of three identical paragraphs: tied at every width to the cap
  const m = nth(REPEAT, MARKER, 1);
  const u3 = uniqueAnchor(REPEAT, m, m + MARKER.length);
  assert.equal(u3.unique, false);
  assert.deepEqual(ctxOf(u3.anchor), [ANCHOR_CTX_CAP, ANCHOR_CTX_CAP]);
  assert.deepEqual(u3.anchor, engine.makeAnchor(REPEAT, m, m + MARKER.length, ANCHOR_CTX_CAP), 'saved at the cap');
  assert.equal(locatesOnlyAt(REPEAT, u3.anchor, m), false, 'still a tie: the stored position is what tells the copies apart');
  assert.equal(engine.locateAnchor(REPEAT, u3.anchor, m).from, m, 'and with that position as the hint the engine picks this copy');
});

test('locateExact: one best hit locates whatever the hint; a tie is settled by the hint; a tie with no hint is anchor-ambiguous; a relocation is anchor-not-found', () => {
  const w = world();
  const retry = fromBrowser(w.text, 'retry on timeout', 2);
  assert.deepEqual(locateExact(w.text, retry.anchor, undefined), { from: retry.idx, to: retry.idx + 'retry on timeout'.length });
  assert.deepEqual(locateExact(w.text, retry.anchor, 0), { from: retry.idx, to: retry.idx + 'retry on timeout'.length }, 'a hint elsewhere does not move a lone best hit');
  const first = fromBrowser(w.text, 'Ship it.', 0);
  const second = fromBrowser(w.text, 'Ship it.', 1);
  assert.deepEqual(first.anchor, second.anchor);
  assert.deepEqual(locateExact(w.text, second.anchor, second.hintOffset), { from: second.idx, to: second.idx + 8 });
  assert.deepEqual(locateExact(w.text, first.anchor, first.hintOffset), { from: first.idx, to: first.idx + 8 });
  assert.deepEqual(locateExact(w.text, first.anchor, first.hintOffset + 3), { from: first.idx, to: first.idx + 8 }, 'nearest wins: a hint a few characters off still picks its copy');
  assert.deepEqual(locateExact(w.text, second.anchor, undefined), { error: 'anchor-ambiguous' });
  assert.deepEqual(locateExact(w.text, second.anchor, null), { error: 'anchor-ambiguous' });
  assert.deepEqual(locateExact(w.text, second.anchor, NaN), { error: 'anchor-ambiguous' });
  assert.deepEqual(locateExact(w.text, second.anchor, 0), { from: first.idx, to: first.idx + 8 }, 'a hint of 0 is a hint');
  // the quote edited away: the engine relocates between the surviving context, which is not a match
  const edited = w.text.replace('cut p95 latency by 40%', 'cut p95 latency by 35%');
  const gone = fromBrowser(w.text, 'cut p95 latency by 40%', 0);
  assert.ok(engine.locateAnchor(edited, gone.anchor));
  assert.deepEqual(locateExact(edited, gone.anchor, gone.hintOffset), { error: 'anchor-not-found' });
});

// ── the comment verb ────────────────────────────────────────────────

test('a comment on the second copy of a sentence lands there with the hint, stores the widened anchor and anchorAt, and a hintless reader places it there', () => {
  const w = world();
  const second = fromBrowser(w.text, 'Ship it.', 1);
  const r = comment(w, w.report, { anchor: second.anchor, note: 'Not yet.', hintOffset: second.hintOffset });
  const c = readSidecar(r.storePath).comments[0];
  assert.equal(c.id, `${c.ts}-${second.idx}`);
  assert.equal(c.anchorAt, second.idx);
  assert.deepEqual(Object.keys(c), ['id', 'author', 'ts', 'anchor', 'anchorAt', 'ordinal', 'copies', 'section', 'body', 'replies', 'resolved'], 'the position, then the copy fields (the tie-break, 2026-09-11)');
  assert.equal(c.anchor.quote, 'Ship it.');
  assert.deepEqual(c.anchor, engine.makeAnchor(w.text, second.idx, second.idx + 8, 48), 'widened one step: the browser\'s 24 tied, 48 does not');
  assert.equal(locatesOnlyAt(w.text, c.anchor, second.idx), true, 'unique from both ends');
  assert.equal(engine.locateAnchor(w.text, c.anchor).from, second.idx, 'the other hosts, with no hint, place it on the selected copy');
  assert.deepEqual(r.store.comments[0], c, 'the reply carries the stored comment as written');
  // the first copy, in the same file: lands on itself, widened the same way
  const first = fromBrowser(w.text, 'Ship it.', 0);
  const r2 = comment(w, w.report, { anchor: first.anchor, note: 'Ship it now.', hintOffset: first.hintOffset });
  const c2 = readSidecar(r2.storePath).comments[1];
  assert.equal(c2.anchorAt, first.idx);
  assert.deepEqual(ctxOf(c2.anchor), [48, 48]);
  assert.equal(engine.locateAnchor(w.text, c2.anchor).from, first.idx);
  assert.equal(fs.readFileSync(w.report, 'utf8'), w.text, 'the file is untouched');
});

test('a passage unique at 24 characters keeps the anchor track-comment would write, and its anchorAt', () => {
  const w = world();
  const retry = fromBrowser(w.text, 'retry on timeout', 2);
  const r = comment(w, w.report, { anchor: retry.anchor, note: 'One retry is enough.', hintOffset: retry.hintOffset });
  const c = readSidecar(r.storePath).comments[0];
  assert.deepEqual(c.anchor, retry.anchor, 'not widened: 24 was already unique');
  assert.equal(c.anchorAt, retry.idx);
  assert.equal(c.id, `${c.ts}-${retry.idx}`);
});

test('identical regions past the cap: the comment is saved at the cap with anchorAt, not refused; without a hint the tie refuses anchor-ambiguous and writes nothing', () => {
  const w = world();
  const m = fromBrowser(REPEAT, MARKER, 1);
  // no hint: nothing can pick a copy
  const bad = refused(w, { verb: 'comment', path: w.repeat, args: { anchor: m.anchor, note: 'Which copy?' }, fence: { storeMtimeNs: '' } }, 'anchor-ambiguous');
  assert.ok(bad.error.includes('~/notes-api/docs/repeat.md') && bad.error.includes('position was not sent'), bad.error);
  assert.equal(fs.existsSync(path.join(w.root, '.trackchanges')), false, 'nothing written');
  // the hint: saved on the second copy, the anchor at the cap, the position beside it
  const r = comment(w, w.repeat, { anchor: m.anchor, note: 'Say it once.', hintOffset: m.hintOffset });
  const c = readSidecar(r.storePath).comments[0];
  assert.equal(c.id, `${c.ts}-${m.idx}`);
  assert.equal(c.anchorAt, m.idx);
  assert.deepEqual(ctxOf(c.anchor), [ANCHOR_CTX_CAP, ANCHOR_CTX_CAP]);
  assert.deepEqual(c.anchor, engine.makeAnchor(REPEAT, m.idx, m.idx + MARKER.length, ANCHOR_CTX_CAP));
  assert.notEqual(engine.locateAnchor(REPEAT, c.anchor, 0).from, engine.locateAnchor(REPEAT, c.anchor, REPEAT.length).from, 'the anchor alone still ties');
  assert.equal(engine.locateAnchor(REPEAT, c.anchor, c.anchorAt).from, m.idx, 'the stored position picks the copy');
  // the third copy too, in the same file, with its own position
  const third = fromBrowser(REPEAT, MARKER, 2);
  const r2 = comment(w, w.repeat, { anchor: third.anchor, note: 'And here.', hintOffset: third.hintOffset });
  const cs = readSidecar(r2.storePath).comments;
  assert.deepEqual(cs.map((x) => x.anchorAt), [m.idx, third.idx]);
  assert.equal(engine.locateAnchor(REPEAT, cs[1].anchor, cs[1].anchorAt).from, third.idx);
});

// ── the stored position over time ───────────────────────────────────

test('anchorAt survives track-reply and a track-edit elsewhere in the file (the vendored CLIs write the whole object back)', () => {
  const w = world();
  const first = fromBrowser(w.text, 'Ship it.', 0);
  const r = comment(w, w.report, { anchor: first.anchor, note: 'Ship it now.', hintOffset: first.hintOffset });
  const before = readSidecar(r.storePath).comments[0];
  assert.equal(before.anchorAt, first.idx);
  // the session replies with the vendored CLI
  cliOk(w, 'reply', ['--file', w.report, '--thread', before.id, '--note', 'Shipping.']);
  const replied = readSidecar(r.storePath).comments[0];
  assert.equal(replied.anchorAt, first.idx);
  assert.deepEqual(replied.anchor, before.anchor);
  assert.deepEqual(replied.replies.map((x) => [x.author, x.body]), [['web', 'Shipping.']]);
  assert.deepEqual(Object.keys(replied), Object.keys(before), 'no field dropped, none added');
  // the session edits BELOW the passage with the vendored CLI: the position is still right, and kept
  cliOk(w, 'edit', ['--file', w.report, '--old', '## Day 2', '--new', '## Day 2 (rerun)']);
  const edited = readSidecar(r.storePath).comments[0];
  assert.equal(edited.anchorAt, first.idx);
  assert.deepEqual(edited.anchor, before.anchor);
  const now = fs.readFileSync(w.report, 'utf8');
  assert.equal(now.slice(edited.anchorAt, edited.anchorAt + 8), 'Ship it.');
  assert.equal(readSidecar(r.storePath).suggestions.length, 1, 'the edit is a pending change');
});

test('a track-edit above the passage leaves anchorAt stale until the next host write, which refreshes it and leaves the anchor as it was', () => {
  const w = world();
  const second = fromBrowser(w.text, 'Ship it.', 1);
  const r = comment(w, w.report, { anchor: second.anchor, note: 'Not yet.', hintOffset: second.hintOffset });
  const before = readSidecar(r.storePath).comments[0];
  // two lines land above, through the vendored CLI (a sidecar write the host did not make)
  const inserted = 'Added line one.\nAdded line two.\n';
  cliOk(w, 'edit', ['--file', w.report, '--old', '# Latency report\n', '--new', `# Latency report\n${inserted}`]);
  const moved = fs.readFileSync(w.report, 'utf8');
  assert.equal(moved.slice(second.idx + inserted.length, second.idx + inserted.length + 8), 'Ship it.');
  assert.equal(readSidecar(r.storePath).comments[0].anchorAt, second.idx, 'the CLI wrote the object back as it was');
  const st = status(w, w.report);
  assert.equal(st.store.comments[0].anchorAt, second.idx, 'a read never rewrites the sidecar: status shows the stale position');
  // the next host write — a resolve, which touches nothing about the anchor — refreshes it
  const r2 = ok(w, { verb: 'resolve', path: w.report, args: { commentId: before.id, on: true }, fence: fenceFor(st) });
  const after = readSidecar(r2.storePath).comments[0];
  assert.equal(after.anchorAt, second.idx + inserted.length);
  assert.deepEqual(after.anchor, before.anchor, 'prefix, quote and suffix untouched');
  assert.equal(after.resolved, true);
  assert.equal(r2.store.comments[0].anchorAt, second.idx + inserted.length, 'the reply carries the refreshed position');
  assert.equal(engine.locateAnchor(moved, after.anchor, after.anchorAt).from, after.anchorAt);
});

test('a tied anchor (past the cap) has its anchorAt refreshed with the stored position as the tie-break, so the comment follows its copy through edits above', () => {
  const w = world();
  const m = fromBrowser(REPEAT, MARKER, 1);
  const r = comment(w, w.repeat, { anchor: m.anchor, note: 'Say it once.', hintOffset: m.hintOffset });
  const c = readSidecar(r.storePath).comments[0];
  assert.equal(locatesOnlyAt(REPEAT, c.anchor, m.idx), false, 'the fixture: the anchor alone ties at the cap');
  // The copies sit one paragraph apart. Each line the session adds above moves every copy down by
  // less than half that spacing, so a position refreshed at every host write stays nearest the chosen
  // copy, while the position the comment was made with is nearest the FIRST copy once two lines are
  // in: a refresh that skipped tied anchors let the highlight drift to the wrong paragraph.
  const spacing = nth(REPEAT, MARKER, 2) - nth(REPEAT, MARKER, 1);
  const line = `${'Added above. '.repeat(23).trimEnd()}\n`;
  assert.ok(line.length < spacing / 2 && 2 * line.length > spacing / 2,
    `the fixture: a ${line.length}-character line, one short of half the spacing (${spacing}), two past it`);
  let at = m.idx;
  for (const step of [1, 2]) {
    cliOk(w, 'edit', ['--file', w.repeat, '--old', '# Repeats\n', '--new', `# Repeats\n${line}`]);
    at += line.length;
    const text = fs.readFileSync(w.repeat, 'utf8');
    assert.equal(nth(text, MARKER, 1), at, 'the chosen copy moved down by the line');
    assert.equal(readSidecar(r.storePath).comments[0].anchorAt, at - line.length, 'the CLI wrote the object back as it was');
    // the person replies: a host write, whose refresh locates with the stored position as the hint
    const r2 = ok(w, { verb: 'reply', path: w.repeat, args: { commentId: c.id, note: `Still once (${step}).` }, fence: fenceFor(status(w, w.repeat)) });
    const after = readSidecar(r2.storePath).comments[0];
    assert.equal(after.anchorAt, at, `refreshed on the write after insertion ${step}`);
    assert.deepEqual(after.anchor, c.anchor, 'the anchor itself is untouched');
    assert.equal(after.replies.length, step);
    assert.equal(r2.store.comments[0].anchorAt, at, 'the reply carries the refreshed position');
    assert.equal(engine.locateAnchor(text, after.anchor, after.anchorAt).from, at, 'the painter, hinted by it, lands on the chosen copy');
  }
  // the drift the refresh prevents: the position the comment was made with now picks the first copy
  const text = fs.readFileSync(w.repeat, 'utf8');
  assert.equal(engine.locateAnchor(text, c.anchor, m.idx).from, nth(text, MARKER, 0), 'left as made, the position would paint the first copy');
});

test('the refresh leaves a position it cannot better: a passage the session rewrote keeps its last known anchorAt, and a tied anchor with no stored position (a comment track-comment wrote) gains none, where one on a unique passage does', () => {
  const w = world();
  // the session comments through the vendored CLI: 24 characters at the first occurrence, no anchorAt
  cliOk(w, 'comment', ['--file', w.report, '--anchor', 'Cold starts remain slow', '--note', 'Still?']);
  cliOk(w, 'comment', ['--file', w.repeat, '--anchor', MARKER, '--note', 'Which copy?']);
  const cold = nth(w.text, 'Cold starts remain slow', 0);
  const st1 = status(w, w.report);
  const st2 = status(w, w.repeat);
  assert.equal('anchorAt' in st1.store.comments[0], false, 'the CLI writes no anchorAt');
  assert.equal('anchorAt' in st2.store.comments[0], false);
  assert.deepEqual(ctxOf(st2.store.comments[0].anchor), [24, 24]);
  assert.equal(locatesOnlyAt(REPEAT, st2.store.comments[0].anchor, nth(REPEAT, MARKER, 0)), false, 'the fixture: the CLI anchor ties across the copies');
  // the person comments on the report passage the session is about to rewrite; this host write also
  // gives the CLI comment on a unique passage its position
  const gone = fromBrowser(w.text, 'cut p95 latency by 40%', 0);
  const r = ok(w, { verb: 'comment', path: w.report, args: { anchor: gone.anchor, note: 'Source?', hintOffset: gone.hintOffset }, fence: fenceFor(st1) });
  const [cliCold, mine] = readSidecar(r.storePath).comments;
  assert.equal(cliCold.anchorAt, cold, 'a unique anchor with no stored position is placed');
  assert.equal(mine.anchorAt, gone.idx);
  // the session rewrites the passage: the next host write finds the quote gone and keeps the position
  cliOk(w, 'edit', ['--file', w.report, '--old', 'cut p95 latency by 40%', '--new', 'cut p95 latency by 35%']);
  const edited = fs.readFileSync(w.report, 'utf8');
  assert.deepEqual(locateExact(edited, mine.anchor, mine.anchorAt), { error: 'anchor-not-found' }, 'the fixture: the quote is gone');
  const r2 = ok(w, { verb: 'resolve', path: w.report, args: { commentId: mine.id, on: true }, fence: fenceFor(status(w, w.report)) });
  const after = readSidecar(r2.storePath).comments[1];
  assert.equal(after.anchorAt, gone.idx, 'kept: the last known position');
  assert.deepEqual(after.anchor, mine.anchor);
  assert.equal(after.resolved, true);
  // a host write on repeat.md: the CLI comment's tie has no stored position to settle it, so none is added
  const r3 = ok(w, { verb: 'comment', path: w.repeat, args: { note: 'Say it once, anywhere.' }, fence: fenceFor(st2) });
  const cs = readSidecar(r3.storePath).comments;
  assert.equal(cs.length, 2);
  assert.equal('anchorAt' in cs[0], false, 'a tie with no stored position is not placed by the refresh');
  assert.equal('anchorAt' in cs[1], false, 'the whole-file comment has no anchor');
});

test('comments without an anchor never gain anchorAt: whole-file, about a change, and standalone region comments, across later writes', () => {
  const w = world();
  const r1 = comment(w, w.report, { note: 'Tighten the summary.' });
  cliOk(w, 'edit', ['--file', w.report, '--old', 'Cold starts remain slow', '--new', 'Cold starts stay slow']);
  const st1 = status(w, w.report);
  const change = st1.hunks[0];
  assert.ok(change, 'the edit is a pending change');
  const r2 = ok(w, { verb: 'comment', path: w.report, args: { changeIds: [change.id], note: 'Keep "remain".' }, fence: fenceFor(st1) });
  const png = path.join(w.root, 'docs', 'chart.png');
  fs.writeFileSync(png, tinyPng(40, 90, 200));
  const r3 = ok(w, { verb: 'comment', path: png, args: { note: 'Label the axes.', target: { kind: 'image', region: { x: 0.1, y: 0.2, w: 0.3, h: 0.4 } } }, fence: { storeMtimeNs: '' } });
  // a passage comment beside them, so the refresh has something to do on the report
  const retry = fromBrowser(fs.readFileSync(w.report, 'utf8'), 'retry on timeout', 1);
  const r4 = ok(w, { verb: 'comment', path: w.report, args: { anchor: retry.anchor, note: 'Once.', hintOffset: retry.hintOffset }, fence: fenceFor(r2) });
  for (const c of readSidecar(r4.storePath).comments) {
    if (c.anchor) assert.equal(c.anchorAt, retry.idx);
    else assert.equal('anchorAt' in c, false, `no anchorAt on ${c.changeIds ? 'a comment about a change' : 'a whole-file comment'}`);
  }
  const rc = readSidecar(r3.storePath).comments[0];
  assert.equal('anchorAt' in rc, false, 'no anchorAt on a region comment with no anchor');
  assert.equal('anchor' in rc, false);
  // a later write on each file: still none
  const r5 = ok(w, { verb: 'resolve', path: w.report, args: { commentId: r1.store.comments[0].id, on: true }, fence: fenceFor(r4) });
  assert.deepEqual(readSidecar(r5.storePath).comments.map((c) => 'anchorAt' in c), [false, false, true]);
  const r6 = ok(w, { verb: 'reply', path: png, args: { commentId: rc.id, note: 'Both axes.' }, fence: fenceFor(r3) });
  assert.equal('anchorAt' in readSidecar(r6.storePath).comments[0], false);
});

test('the sidecar round-trips through store-io with anchorAt kept and nothing else changed', () => {
  const w = world();
  const second = fromBrowser(w.text, 'Ship it.', 1);
  const r = comment(w, w.report, { anchor: second.anchor, note: 'Not yet.', hintOffset: second.hintOffset });
  const disk = readSidecar(r.storePath);
  const loaded = loadStore(r.storePath, w.text);
  assert.deepEqual(loaded.comments, disk.comments, 'the load keeps the field');
  const again = path.join(path.dirname(r.storePath), 'again.json');
  saveStore(w.root, again, loaded, w.text);
  const saved = readSidecar(again);
  assert.deepEqual(saved.comments, disk.comments, 'and so does a save by the store layer');
  assert.equal(saved.v, 3);
  assert.deepEqual(saved.fingerprint, disk.fingerprint);
});

// ── the painter's raw contract (Slice 5 of plans/markdown-viewer.md, items 2 and 8) ─────────────────
// Since Slice 5 the Rendered paint reads a code quote raw and a table quote with its cell delimiters
// as blanks, at PAINT time (the owner's ruling of 2026-09-09: the plan's "strip cell delimiters from a
// table quote" is a paint-time rule); the stored quote stays the exact source slice, asterisks and pipe
// included, which is what locateExact and uniqueAnchor have read byte for byte since the anchors
// follow-on. Neither case below failed before Slice 5: they are regression guards on the contract the
// painter now relies on, and their titles say so. The passages are the ones the painter's browser leg
// drags over (ui/webview/anchor-map-fixtures/wrappers-plain.md, synthetic); the note here is synthetic
// too and holds each once, so no width of context is needed and no hint settles anything.
const PAINTED = [
  '# Painted',
  '',
  'Intro paragraph one with several words in it.',
  '',
  '```python',
  'total = a * b * 2',
  'name_ = under_score  # trailing comment',
  '```',
  '',
  '| Col A | Col B |',
  '|-------|-------|',
  '| cell one | cell two |',
  '| cell three | cell four |',
  '',
  'Final paragraph here.',
  '',
].join('\n');
function paintedWorld() {
  const w = world();
  w.note = path.join(w.root, 'docs', 'note.md');
  fs.writeFileSync(w.note, PAINTED);
  return w;
}
// The comment verb over one passage of the note: the stored comment, checked against the source slice.
function commentOnPassage(w, quote, note) {
  assert.equal(PAINTED.indexOf(quote), PAINTED.lastIndexOf(quote), `the fixture holds ${JSON.stringify(quote)} once`);
  const at = PAINTED.indexOf(quote);
  assert.ok(at >= 0, `the fixture holds ${JSON.stringify(quote)}`);
  const browser = engine.makeAnchor(PAINTED, at, at + quote.length);
  assert.equal(browser.quote, quote, 'the browser\'s anchor quotes the source slice as it is');
  const r = comment(w, w.note, { anchor: browser, note, hintOffset: at });
  const c = readSidecar(r.storePath).comments[readSidecar(r.storePath).comments.length - 1];
  assert.equal(c.anchor.quote, quote, 'the stored quote is the exact source slice');
  assert.deepEqual(c.anchor, browser, 'unique at 24: the browser\'s anchor is stored as it came');
  assert.equal(c.anchorAt, at);
  assert.equal(c.id, `${c.ts}-${at}`);
  assert.deepEqual(Object.keys(c), ['id', 'author', 'ts', 'anchor', 'anchorAt', 'ordinal', 'copies', 'section', 'body', 'replies', 'resolved'], 'the position, then the copy fields (the tie-break, 2026-09-11)');
  assert.deepEqual([c.ordinal, c.copies, c.section], [1, 1, 'Painted'], 'the copy fields: 1 of 1 under the note\'s one heading (the fixture holds the quote once, asserted above; the fence\'s `# trailing comment` is code, not a heading)');
  assert.equal(PAINTED.slice(c.anchorAt, c.anchorAt + c.anchor.quote.length), quote, 'the position names the slice');
  assert.equal(engine.locateAnchor(PAINTED, c.anchor).from, at, 'a hintless reader lands on it too');
  assert.deepEqual(r.store.comments[r.store.comments.length - 1], c, 'the reply carries the stored comment as written');
  assert.equal(fs.readFileSync(w.note, 'utf8'), PAINTED, 'the file is untouched');
  return { c, at };
}

test('regression guard, green before Slice 5: a code line holding `*` is located byte for byte by uniqueAnchor and locateExact, and the comment verb stores that slice, asterisks kept, with anchorAt', () => {
  const w = paintedWorld();
  const quote = 'total = a * b * 2';
  const at = PAINTED.indexOf(quote);
  const fenceOpen = PAINTED.indexOf('```python'), fenceClose = PAINTED.indexOf('```', fenceOpen + 3);
  assert.ok(fenceOpen < at && at + quote.length < fenceClose, 'the fixture: the line sits inside the fence');
  const u = uniqueAnchor(PAINTED, at, at + quote.length);
  assert.equal(u.unique, true);
  assert.equal(u.anchor.quote, quote, 'the quote keeps its asterisks (the painter\'s old strip lost them; the host never did)');
  assert.deepEqual(ctxOf(u.anchor), [24, 24]);
  assert.deepEqual(locateExact(PAINTED, u.anchor, undefined), { from: at, to: at + quote.length });
  assert.deepEqual(locateExact(PAINTED, engine.makeAnchor(PAINTED, at, at + quote.length), at), { from: at, to: at + quote.length });
  // a quote that opens with the comment marker the old strip read as a heading: located from its `#`
  const tail = '# trailing comment';
  const tailAt = PAINTED.indexOf(tail);
  assert.deepEqual(locateExact(PAINTED, engine.makeAnchor(PAINTED, tailAt, tailAt + tail.length), undefined), { from: tailAt, to: tailAt + tail.length });
  // through the comment verb, as the panel saves it from the Raw view
  const { c } = commentOnPassage(w, quote, 'Why times two?');
  assert.ok(c.anchor.quote.includes(' * '), 'the stored quote holds the operator as written');
  assert.equal(c.body, 'Why times two?');
});

test('regression guard, green before Slice 5: a table quote across two cells is located byte for byte with its pipe, and the comment verb stores the slice, pipe kept, with anchorAt', () => {
  const w = paintedWorld();
  const quote = 'cell one | cell two';
  const at = PAINTED.indexOf(quote);
  const rowStart = PAINTED.lastIndexOf('\n', at) + 1, rowEnd = PAINTED.indexOf('\n', at);
  assert.equal(PAINTED.slice(rowStart, rowEnd), '| cell one | cell two |', 'the fixture: the quote spans the row\'s two cells');
  const u = uniqueAnchor(PAINTED, at, at + quote.length);
  assert.equal(u.unique, true);
  assert.equal(u.anchor.quote, quote, 'the pipe is part of the stored quote (the painter reads it as a blank at paint time; the store never strips it)');
  assert.deepEqual(locateExact(PAINTED, u.anchor, undefined), { from: at, to: at + quote.length });
  assert.deepEqual(locateExact(PAINTED, engine.makeAnchor(PAINTED, at, at + quote.length), at), { from: at, to: at + quote.length });
  // one cell alone locates the same way
  const cell = 'cell three';
  const cellAt = PAINTED.indexOf(cell);
  assert.deepEqual(locateExact(PAINTED, engine.makeAnchor(PAINTED, cellAt, cellAt + cell.length), undefined), { from: cellAt, to: cellAt + cell.length });
  const { c } = commentOnPassage(w, quote, 'One cell would do.');
  assert.ok(c.anchor.quote.includes('|'), 'the stored quote holds the delimiter as written');
  // and a second comment in the same sidecar, on the code line, sits beside it with its own position
  const { c: c2, at: codeAt } = commentOnPassage(w, 'total = a * b * 2', 'Why times two?');
  assert.notEqual(c2.anchorAt, c.anchorAt);
  assert.equal(c2.anchorAt, codeAt);
  assert.equal(readSidecar(path.join(w.root, '.trackchanges', 'docs%2Fnote.md.json')).comments.length, 2);
});

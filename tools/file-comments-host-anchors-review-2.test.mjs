// The anchors follow-on's second review (2026-09-08; plans/file-review.md, The contract and the host
// paragraph). Four properties the host must hold, each one a bug this pins against:
// (1) uniqueAnchor's widening loop is BOUNDED. It tests each width with one whole-anchor scan, not two
//     context-slicing engine scans over every occurrence of the quote, so a comment on a short line
//     that recurs 10^5+ times (a 2 MB file of a repeated line) is placed in well under the kernel's
//     10 s deadline instead of running tens of seconds and being killed with nothing saved.
// (2) A UTF-8 BOM file: a tied selection carrying its offset is PLACED, not refused. The browser's
//     offset indexes the fetch's BOM-stripped text and this script's text keeps the BOM, so the offset
//     is mapped into this text (browserHint) before the exact check; without it every tie was refused
//     `anchor-moved` ("the text moved") for the correct selection, forever.
// (3) A reject that reverts TWO OR MORE changes in one write follows a tied passage back, exercising the
//     cumulative shift in appliedShifts (`+ shift`): every reject in the round-1 suites reverts exactly
//     one change, so that term went untested.
// (4) The refresh's per-write budget bounds the CLASSIFICATION scan too (fullMatches, one whole-text pass
//     per distinct anchor), not only the engine's scoring, so thousands of CLI-written passage comments
//     with distinct anchors do not hold every write past the kernel's deadline; past the budget the
//     comments keep their stored position and stderr says so.
// Hermetic, the anchors suites' way: a synthetic notes-api world under a scratch directory, the host as a
// child process with one JSON request on stdin, the REAL vendored CLIs where a test says the session did
// something. Synthetic fixtures only; no real session data.
// Run: node --test tools/file-comments-host-anchors-review-2.test.mjs
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

import { locateExact, uniqueAnchor, ANCHOR_CTX_CAP, REFRESH_SCAN_BUDGET } from './file-comments-host.mjs';
import { fingerprintOf } from '../vendor/track-changents/store-io.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const HOST = path.join(REPO, 'tools', 'file-comments-host.mjs');
const VENDOR = path.join(REPO, 'vendor', 'track-changents');
const FIX = path.join(REPO, 'tests', 'fixtures', 'file_comments');
const engine = createRequire(import.meta.url)(path.join(VENDOR, 'engine.js'));

const SID = '11111111-2222-3333-4444-555555555555';

let SCRATCH;
before(() => { SCRATCH = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-fc-anchors-r2-')); });
after(() => { try { fs.rmSync(SCRATCH, { recursive: true, force: true }); } catch { /* ignore */ } });

// ── the world ───────────────────────────────────────────────────────
const PARA = ('The quick brown fox jumps over the lazy dog. '.repeat(12)
  + 'Here is the marker phrase to comment on. '
  + 'Pack my box with five dozen liquor jugs. '.repeat(12)).trim();
const MARKER = 'the marker phrase';

let worlds = 0;
function world() {
  const home = path.join(SCRATCH, `w${++worlds}`, 'home');
  const root = path.join(home, 'notes-api');
  fs.mkdirSync(path.join(root, '.git'), { recursive: true });
  fs.mkdirSync(path.join(root, 'docs'));
  fs.copyFileSync(path.join(FIX, 'report.md'), path.join(root, 'docs', 'report.md'));
  return {
    home, root, docs: path.join(root, 'docs'),
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
  const t0 = Date.now();
  const r = spawnSync(process.execPath, [HOST], { input: JSON.stringify(req), encoding: 'utf8', env: env(w), maxBuffer: 256 * 1024 * 1024 });
  let json = null;
  try { json = JSON.parse(r.stdout); } catch { json = null; }
  return { code: r.status, stdout: r.stdout, stderr: r.stderr, json, ms: Date.now() - t0 };
}
function ok(w, req) {
  const r = host(w, req);
  assert.equal(r.code, 0, `exit ${r.code}: ${r.stderr}`);
  assert.ok(r.json && r.json.ok === true, `expected ok:true, got ${r.stdout.slice(0, 400)}`);
  assert.equal(r.json.verb, req.verb);
  return r;
}
function refused(w, req, code) {
  const r = host(w, req);
  assert.equal(r.code, 0, `a refusal exits 0; got ${r.code}: ${r.stderr}`);
  assert.ok(r.json && r.json.ok === false, `expected ok:false, got ${r.stdout.slice(0, 400)}`);
  assert.equal(r.json.code, code, r.json.error);
  return r.json;
}
function cliOk(w, name, args) {
  const r = spawnSync(process.execPath, [path.join(VENDOR, 'cli', `track-${name}.mjs`), ...args],
    { encoding: 'utf8', env: env(w, { ROMP_SESSION_NAME: 'web', ROMP_SID: SID }) });
  assert.equal(r.status, 0, `track-${name} failed: ${r.stderr}`);
  return r;
}
function status(w, file) { return ok(w, { verb: 'status', path: file, args: {} }).json; }
function fenceFor(st) { return { storeMtimeNs: st.storeMtimeNs == null ? '' : st.storeMtimeNs }; }
function fileFenceFor(st) { return { ...fenceFor(st), fileMtimeNs: st.fileMtimeNs }; }
function comment(w, file, args) { return ok(w, { verb: 'comment', path: file, args, fence: fenceFor(status(w, file)) }).json; }
function readSidecar(sp) { return JSON.parse(fs.readFileSync(sp, 'utf8')); }
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
const ctxOf = (a) => [a.prefix.length, a.suffix.length];

// ── (1) uniqueAnchor's widening loop is bounded ──────────────────────

test('uniqueAnchor on a 2 MB file of a repeated short line stops fast at the cap, and the comment verb places the note well inside the kernel\'s deadline', () => {
  const w = world();
  // 'ok\n' repeated to just under the viewer's 2 MiB cap: a short quote that recurs ~600k times, so every
  // widening step ties. The pre-fix loop ran engine.locateAnchor twice per step, each scoring 600k
  // occurrences against up to 480 characters of context, and took tens of seconds; the kernel kills the
  // host at 10 s. The whole-anchor test is one native scan per step that stops at the second hit.
  const unit = 'ok\n';
  const count = Math.floor((2 * 1024 * 1024 - 200) / unit.length);
  const text = unit.repeat(count);
  assert.ok(text.length < 2 * 1024 * 1024 && text.length > 1.6 * 1024 * 1024, `the fixture: ${text.length} bytes`);
  const data = path.join(w.docs, 'data.txt');
  fs.writeFileSync(data, text);
  // uniqueAnchor alone: fast, tied to the cap (no width is unique on a file of identical lines).
  const at = 3 * 100000;   // an 'ok' deep inside the file, more than the cap from both ends
  const t0 = Date.now();
  const u = uniqueAnchor(text, at, at + 2);
  const uMs = Date.now() - t0;
  assert.equal(u.unique, false, 'every width ties on a file of identical lines');
  assert.deepEqual(ctxOf(u.anchor), [ANCHOR_CTX_CAP, ANCHOR_CTX_CAP], 'saved at the cap');
  assert.ok(uMs < 5000, `uniqueAnchor took ${uMs} ms (the unbounded loop ran tens of seconds)`);
  // the whole comment verb through the host: the tie is settled by the browser's offset, and the note is
  // saved at the cap with its position, in well under the kernel's 10 s deadline.
  const b = fromBrowser(text, 'ok', 200);
  const r = ok(w, { verb: 'comment', path: data, args: { anchor: b.anchor, note: 'Say it once.', hintOffset: b.hintOffset }, fence: { storeMtimeNs: '' } });
  assert.ok(r.ms < 5000, `the comment verb took ${r.ms} ms`);
  const c = readSidecar(r.json.storePath).comments[0];
  assert.equal(c.anchorAt, b.idx);
  assert.deepEqual(ctxOf(c.anchor), [ANCHOR_CTX_CAP, ANCHOR_CTX_CAP], 'a passage still tied at the cap is saved at the cap');
});

// ── (2) a UTF-8 BOM file: a tied selection with its offset is placed ─

test('a tied comment on a BOM-prefixed file is placed, its offset mapped past the BOM, not refused "the text moved"', () => {
  const w = world();
  // report.md prefixed with a UTF-8 BOM. The browser reads the fetch's BOM-stripped text (the raw
  // fixture); this script reads the file with the BOM kept, so its offsets are the browser's plus one.
  const bomText = '﻿' + w.text;
  const bom = path.join(w.docs, 'bom.md');
  fs.writeFileSync(bom, bomText);
  const second = fromBrowser(w.text, 'Ship it.', 1);           // the browser's anchor and offset, BOM-stripped coordinates
  assert.deepEqual(second.anchor, fromBrowser(w.text, 'Ship it.', 0).anchor, 'the fixture: the two copies share their 24 characters (a tie)');
  const r = comment(w, bom, { anchor: second.anchor, note: 'Not yet.', hintOffset: second.hintOffset });
  const c = readSidecar(r.storePath).comments[0];
  assert.equal(c.anchorAt, second.idx + 1, 'placed on the selected copy, its offset mapped past the one-character BOM');
  assert.equal(c.id, `${c.ts}-${second.idx + 1}`);
  assert.equal(c.anchor.quote, 'Ship it.');
  assert.equal(bomText.slice(c.anchorAt, c.anchorAt + 8), 'Ship it.', 'the stored position names the copy in this script\'s own text');
  assert.deepEqual(readSidecar(r.storePath).fingerprint, fingerprintOf(bomText), 'the sidecar keeps the BOM: its fingerprint equals the CLIs\'');
  // the reply says the text keeps a BOM, so the panel can map the stored position back into the view's coordinates
  // (viewAt) before it judges which copy it names: without the bit, a position naming the chosen copy missed it by
  // one on every BOM file and the copy was painted as a guess (the consolidation, 2026-09-08)
  assert.equal(r.bom, true, 'the comment reply carries the bit');
  assert.equal(status(w, bom).bom, true, 'and so does status');
  // the first copy, selected instead: its own offset, mapped the same way
  const first = fromBrowser(w.text, 'Ship it.', 0);
  const r2 = comment(w, bom, { anchor: first.anchor, note: 'Ship it now.', hintOffset: first.hintOffset });
  assert.equal(readSidecar(r2.storePath).comments[1].anchorAt, first.idx + 1);
  // the same request on the file WITHOUT the BOM: the offset is not shifted (the control that isolates the BOM)
  const plain = path.join(w.docs, 'plain.md');
  fs.writeFileSync(plain, w.text);
  const r3 = comment(w, plain, { anchor: second.anchor, note: 'Not yet.', hintOffset: second.hintOffset });
  assert.equal(readSidecar(r3.storePath).comments[0].anchorAt, second.idx, 'no BOM: the browser\'s offset is this text\'s offset');
  assert.equal(r3.bom, false, 'no BOM: the reply says so, as a value, never absent');
  assert.equal(status(w, plain).bom, false);
});

test('a unique passage on a BOM-prefixed file is unaffected (the exact check never consults the offset for a lone hit)', () => {
  const w = world();
  const bomText = '﻿' + w.text;
  const bom = path.join(w.docs, 'bom.md');
  fs.writeFileSync(bom, bomText);
  const uniq = fromBrowser(w.text, 'cut p95 latency by 40%', 0);
  assert.equal(w.text.indexOf('cut p95 latency by 40%', uniq.idx + 1), -1, 'the fixture: the quote occurs once');
  const r = comment(w, bom, { anchor: uniq.anchor, note: 'Source?', hintOffset: uniq.hintOffset });
  const c = readSidecar(r.storePath).comments[0];
  assert.equal(c.anchorAt, uniq.idx + 1, 'located past the BOM');
  assert.equal(bomText.slice(c.anchorAt, c.anchorAt + uniq.anchor.quote.length), 'cut p95 latency by 40%');
});

// ── (3) a reject reverting two changes follows a tied passage back ───

test('a reject that reverts two changes in one write follows a tied passage back through the cumulative shift', () => {
  const w = world();
  // three identical paragraphs, each under its own heading so an insertion between two has a unique --old;
  // the marker still sits more than the cap from both ends of its paragraph, so the copies tie at the cap.
  const HEADED = `# Repeats\n\n${PARA}\n\n## Second\n\n${PARA}\n\n## Third\n\n${PARA}\n`;
  const repeat = path.join(w.docs, 'repeat.md');
  fs.writeFileSync(repeat, HEADED);
  const m = fromBrowser(HEADED, MARKER, 1);                    // the second of three copies (under ## Second)
  const r = comment(w, repeat, { anchor: m.anchor, note: 'Say it once.', hintOffset: m.hintOffset });
  const c = readSidecar(r.storePath).comments[0];
  assert.equal(c.anchorAt, m.idx);
  assert.notEqual(engine.locateAnchor(HEADED, c.anchor, 0).from, engine.locateAnchor(HEADED, c.anchor, HEADED.length).from, 'the fixture: the anchor alone ties');
  // two insertions above the chosen copy, both large, not adjacent (two pending changes, not coalesced):
  // one after '# Repeats\n' (above both the first and the chosen copy), one after '## Second\n\n' (above
  // the chosen copy only). The finding's sizes, so the top insertion exceeds the gap the cumulative shift
  // must bridge past the mid insertion.
  const top = `${'Top line added above the first paragraph. '.repeat(15)}`.slice(0, 608).replace(/.$/, '\n');
  const mid = `${'Middle line added under the second heading. '.repeat(8)}`.slice(0, 305).replace(/.$/, '\n');
  assert.ok(top.length === 608 && mid.length === 305);
  cliOk(w, 'edit', ['--file', repeat, '--old', '# Repeats\n', '--new', `# Repeats\n${top}`]);
  cliOk(w, 'edit', ['--file', repeat, '--old', '## Second\n\n', '--new', `## Second\n\n${mid}`]);
  const moved = fs.readFileSync(repeat, 'utf8');
  assert.equal(nth(moved, MARKER, 1), m.idx + top.length + mid.length, 'the chosen copy moved down by both insertions');
  // the person replies: the refresh follows the chosen copy through both pending insertions
  const r2 = ok(w, { verb: 'reply', path: repeat, args: { commentId: c.id, note: 'Still once.' }, fence: fenceFor(status(w, repeat)) }).json;
  assert.equal(r2.store.comments[0].anchorAt, m.idx + top.length + mid.length, 'followed through both');
  // the person rejects BOTH insertions in one write: the text is HEADED again, and the position follows
  // the two reversals back — the cumulative shift (appliedShifts' `+ shift`) puts the mid reversal's end
  // in the coordinates the top reversal already moved, so the chosen copy is found where it started.
  const st = status(w, repeat);
  assert.equal(st.hunks.length, 2, 'two pending changes');
  const ids = st.hunks.map((h) => h.id);
  const r3 = ok(w, { verb: 'reject', path: repeat, args: { ids }, fence: fileFenceFor(st) }).json;
  assert.equal(fs.readFileSync(repeat, 'utf8'), HEADED, 'both insertions reverted');
  assert.equal(r3.store.comments[0].anchorAt, m.idx, 'back on the chosen copy: the cumulative shift carried it there');
  assert.equal(readSidecar(r.storePath).comments[0].anchorAt, m.idx);
  assert.equal(engine.locateAnchor(HEADED, c.anchor, r3.store.comments[0].anchorAt).from, m.idx, 'the painter, hinted by it, lands on the chosen copy');
});

// ── (4) the classification scan is budgeted per write ────────────────

test('a sidecar of thousands of distinct-anchor comments on a 2 MB file refreshes well inside the kernel\'s deadline, keeps every position, and stderr says how many were left unscanned', () => {
  const w = world();
  // a 2 MB prose file; the quote the hand-written comments name never appears, so each is a whole-text
  // pass that finds nothing (fullMatches). With N distinct anchors that is N passes over the file; the
  // budget caps how many run in one write, and the rest keep their stored position.
  const sentence = 'The committee reviews the quarterly numbers and files a short note for the record. ';
  const count = Math.floor((2 * 1024 * 1024 - 200) / sentence.length);
  const text = `# Log\n\n${sentence.repeat(count)}`;
  assert.ok(text.length > 1.8 * 1024 * 1024 && text.length < 2 * 1024 * 1024, `the fixture: ${text.length} bytes`);
  const big = path.join(w.docs, 'big.md');
  fs.writeFileSync(big, text);
  const r = comment(w, big, { note: 'Overall.' });            // seed the sidecar with a whole-file comment
  const QUOTE = 'ZZZ-absent-passage-ZZZ';
  assert.equal(text.indexOf(QUOTE), -1, 'the fixture: the quote is nowhere in the text');
  const N = 6000;
  const disk = readSidecar(r.storePath);
  const positions = [];
  for (let i = 0; i < N; i++) {
    const at = 100 + i;
    positions.push(at);
    disk.comments.push({ id: `1700000000000-${i}`, author: 'you', ts: 1700000000000 + i, anchor: { prefix: `edited-${i} `, quote: QUOTE, suffix: ` case-${i}` }, anchorAt: at, body: `Note ${i}.`, replies: [], resolved: false });
  }
  fs.writeFileSync(r.storePath, JSON.stringify(disk));
  // one pass over these N distinct anchors, unbudgeted, is ~N whole-text scans and held the write past
  // the kernel's 10 s deadline. Budgeted, it completes fast and the comments keep their stored position.
  const st = status(w, big);
  const res = ok(w, { verb: 'resolve', path: big, args: { commentId: disk.comments[0].id, on: true }, fence: fenceFor(st) });
  assert.ok(res.ms < 5000, `the resolve took ${res.ms} ms`);
  assert.deepEqual(res.json.store.comments.slice(1).map((c) => c.anchorAt), positions, 'every position kept: none of these anchors located');
  assert.match(res.stderr, /comment\(s\) kept their stored position: locating them would scan past the refresh's budget for one write/);
  assert.ok(2 * N * text.length > REFRESH_SCAN_BUDGET, 'the fixture: N whole-text passes would far exceed the budget');
});

// The tie-break review's second round (2026-09-11) against the host, tools/file-comments-host.mjs: each finding on the
// host reproduced against the real host as a child process (the file-comments-host-tiebreak-review.test.mjs way: the
// synthetic notes-api world under a scratch directory, a raw write where the person or an editor did something, the
// real vendored CLI where a session did) or against the exported helpers, and closed here.
//   * fullMatches memoized a result the budget cut short under the key every caller uses, and locateStored answered
//     null off it to its readers without a budget; passageFigure read `.error` off the null, so every write on a file
//     holding a src-less region comment whose scan the budget had cut died with a TypeError (the kernel's host-error)
//     until the sidecar was edited by hand. Now a cut result serves no caller without a budget: the scan runs whole and
//     the whole result replaces it, and the budgeted callers after it have it for free. The stale position the case
//     places from lands on a line above the run, off the quote: the third round made a position the quote itself sits
//     at the passage's own (locateStored's `position`), which reaches no tie rule, and the fixture's first form, the
//     quote at every offset of a text of one character, could then reach none.
//   * The heading regex and the front-matter key regex paired a lazy quantifier with a trailing whitespace class and
//     backtracked quadratically over a run of whitespace inside a line: a heading line of 120k spaces held a `comment`
//     on a 120 KB file 13 s, past the kernel's 10 s deadline. Now both take the line greedily, for the same words.
//   * placedFor charged the engine's placing of every comment whose whole anchor sits nowhere, a verdict it drops, so
//     about a hundred such comments on a near-cap file spent the budget on a status and every tied comment behind them
//     in the store lost its confirmed verdict, with nothing on stderr. Now locateStored under a budget answers a
//     nowhere anchor unplaced after the classification pass alone.
//   * refreshAnchorAts judged a null store (a save on a tracked file with no sidecar) through markdownOf, whose note for
//     a library caller's unjudged store then went out on every such save, and the kernel logged it. Now the refresh
//     returns before judging when there is no store.
//   * Two branches were guarded by no test: stampCopy writing nothing when the position is not among the whole matches
//     (a comment the refresh carried to the quote's other occurrence keeps its copy fields), and markdownOf leaving an
//     unjudged store's heading path as it is, with its note once per process. Both are driven here.
// Synthetic fixtures only. Run: node --test tools/file-comments-host-tiebreak-review-2.test.mjs
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { performance } from 'node:perf_hooks';
import { spawnSync } from 'node:child_process';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { createRequire } from 'node:module';

import { sectionAt, locateStored, fullMatches, ANCHOR_CTX_CAP, REFRESH_SCAN_BUDGET, REFRESH_PASS_DIVISOR, TEXT_MAX_BYTES } from './file-comments-host.mjs';
import { writeTrackedPaths } from '../vendor/track-changents/store-io.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const HOST = path.join(REPO, 'tools', 'file-comments-host.mjs');
const VENDOR = path.join(REPO, 'vendor', 'track-changents');
const engine = createRequire(import.meta.url)(path.join(VENDOR, 'engine.js'));

const SID = '11111111-2222-3333-4444-555555555555';
// The host's cap on the copies one scan enumerates, not exported; the memo key locateStored's scans live under.
const REFRESH_COPIES_MAX = 65_536;
assert.ok(fs.readFileSync(HOST, 'utf8').includes('const REFRESH_COPIES_MAX = 65_536;'), 'the cap as the host has it');

let SCRATCH;
before(() => { SCRATCH = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-fc-tiebreak-review-2-')); });
after(() => { try { fs.rmSync(SCRATCH, { recursive: true, force: true }); } catch { /* ignore */ } });

// ── the world ───────────────────────────────────────────────────────
// The tie-break suites' fixture: one paragraph over a thousand characters long, three times, each under its own
// heading, with the marker phrase more than ANCHOR_CTX_CAP from both ends of every copy, so every anchor on it ties at
// the cap.
const PARA = ('The quick brown fox jumps over the lazy dog. '.repeat(12)
  + 'Here is the marker phrase to comment on. '
  + 'Pack my box with five dozen liquor jugs. '.repeat(12)).trim();
const MARKER = 'the marker phrase';
const OPENING = '# Report\n\nA short opening line that occurs once.\n\n';
const TIED = `${OPENING}## First pass\n\n${PARA}\n\n## Second pass\n\n${PARA}\n\n## Third pass\n\n${PARA}\n`;
const REGION = { x: 0.12, y: 0.4, w: 0.35, h: 0.2 };

let worlds = 0;
function world() {
  const home = path.join(SCRATCH, `w${++worlds}`, 'home');
  const root = path.join(home, 'notes-api');
  fs.mkdirSync(path.join(root, '.git'), { recursive: true });
  fs.mkdirSync(path.join(root, 'docs'));
  fs.writeFileSync(path.join(root, 'docs', 'tied.md'), TIED);
  fs.writeFileSync(path.join(root, 'docs', 'tied.txt'), TIED);
  return { home, root, docs: path.join(root, 'docs'), tied: path.join(root, 'docs', 'tied.md'), txt: path.join(root, 'docs', 'tied.txt') };
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
function writeSidecar(sp, obj) { fs.writeFileSync(sp, JSON.stringify(obj, null, 2)); }
function nth(text, quote, n) {
  let i = -1;
  for (let k = 0; k <= n; k++) i = text.indexOf(quote, i + 1);
  assert.ok(i >= 0, `fixture lacks occurrence ${n} of ${JSON.stringify(quote)}`);
  return i;
}
// The anchor the browser sends: the engine's 24 characters at the nth occurrence, and the selection's start as the hint.
function fromBrowser(text, quote, n) {
  const idx = nth(text, quote, n);
  return { anchor: engine.makeAnchor(text, idx, idx + quote.length), hintOffset: idx, idx };
}
const copyFields = (c) => [c.ordinal, c.copies, c.section];
const PASSAGE_KEYS = ['id', 'author', 'ts', 'anchor', 'anchorAt', 'ordinal', 'copies', 'section', 'body', 'replies', 'resolved'];
const keptNotes = (stderr) => [...stderr.matchAll(/file-comments-host: (\d+) comment\(s\) (?:whose anchor sits in whole nowhere in the text )?kept their stored position/g)].map((m) => Number(m[1]));
const UNJUDGED = "file-comments-host: the store carries no judgment of the file's kind, so no heading path was written; every store this script loads or seeds is judged from the file's name";
// A raw write: the person's editor, or a write outside the tracked path; nothing records it.
function rawWrite(file, text) { fs.writeFileSync(file, text); }
// A near-cap markdown report of `n` sections, one distinct paragraph each, and the quote unique to each paragraph.
function sections(n) {
  const filler = 'The body of this section says the same thing in the same words, which is what a filler does. '.repeat(23);
  const quotes = [];
  let text = '# Big\n\n';
  for (let i = 0; i < n; i++) {
    quotes.push(`Paragraph ${i} of the report`);
    text += `## Section ${i}\n\n${quotes[i]} says something particular. ${filler}\n\n`;
  }
  return { text, quotes };
}
function timed(fn) {
  const t0 = performance.now();
  const v = fn();
  return [v, performance.now() - t0];
}

// ── a classification the budget cut short serves no reader without a budget ──

test('fullMatches: a result the budget cut short answers the budgeted callers and no caller without a budget, which runs the scan whole and leaves the whole result for the rest; locateStored without a budget places the comment off it', () => {
  // the run: the whole anchor at the cap sits at every offset of it but the last 960, 29,040 copies, under
  // REFRESH_COPIES_MAX. The line above it holds no `a`, so the stale position on it is off the quote: a position the
  // quote itself sits at names the passage (locateStored's `position`, the review's third round) and reaches no tie
  // rule, so a text of the one character alone, the fixture's first form, could reach none from any position inside it
  const head = 'The line the person put here, on no record.\n';
  const RUN = 30000;
  const flat = head + 'a'.repeat(RUN);
  const stale = 5;   // a stored position the write above left on the line
  const anchor = engine.makeAnchor(flat, head.length + 15000, head.length + 15001, ANCHOR_CTX_CAP);
  assert.equal(anchor.quote, 'a');
  assert.equal(flat.indexOf(anchor.quote), head.length, 'the fixture: the quote occurs nowhere on the line');
  assert.ok(stale < head.length, 'the fixture: the stale position is on the line, off the quote');
  const needle = anchor.prefix + anchor.quote + anchor.suffix;
  const copies = RUN - needle.length + 1;
  const pass = Math.ceil(flat.length / REFRESH_PASS_DIVISOR);
  const budget = { left: pass + needle.length * 100, skipped: 0, unscanned: 0 };   // room for a hundred hits, not the rest
  const cut = fullMatches(flat, anchor, REFRESH_COPIES_MAX, budget);
  assert.equal(cut.cut, true, 'the fixture: cut short by the budget');
  assert.ok(cut.hits.length >= 100 && cut.hits.length < copies, `the fixture: ${cut.hits.length} of ${copies} enumerated`);
  assert.equal(budget.left, 0, 'the budget is spent');
  // the budgeted callers get the cut result back, and are charged nothing more (the stage's pass after the measure's)
  const again = { left: REFRESH_SCAN_BUDGET, skipped: 0, unscanned: 0 };
  assert.equal(fullMatches(flat, anchor, REFRESH_COPIES_MAX, again), cut, 'the memo, for a caller with a budget');
  assert.equal(again.left, REFRESH_SCAN_BUDGET, 'nothing charged for the memo');
  assert.equal(locateStored(flat, { anchor, anchorAt: stale }, false, again), null, 'under a budget: nothing known');
  // a caller without one (locateStored for passageFigure and doRetarget): the scan runs whole
  const whole = fullMatches(flat, anchor, REFRESH_COPIES_MAX);
  assert.equal(whole.cut, undefined, 'not cut');
  assert.equal(whole.more, false);
  assert.equal(whole.hits.length, copies, 'every copy');
  assert.equal(fullMatches(flat, anchor, REFRESH_COPIES_MAX, again), whole, 'and the whole result now serves the budgeted callers too');
  assert.equal(again.left, REFRESH_SCAN_BUDGET, 'for free');
  // locateStored without a budget: the tie is broken, never null (before the fix: null, and passageFigure read .error off it)
  const nearest = engine.locateAnchor(flat, anchor, stale).from;
  assert.equal(nearest, whole.hits[0], 'the fixture: the engine\'s pick from the stale position is the first copy');
  const loc = locateStored(flat, { anchor, anchorAt: stale }, false);
  assert.deepEqual(loc, { from: nearest, to: nearest + 1, confirmed: false, by: 'nearest' }, 'the nearest copy, a guess');
  assert.deepEqual(locateStored(flat, { anchor, anchorAt: stale, ordinal: 3, copies }, false), { from: whole.hits[2], to: whole.hits[2] + 1, confirmed: true, by: 'ordinal' }, 'the fields tell, once the copies are counted');
  assert.deepEqual(locateStored(flat, { anchor, anchorAt: stale, ordinal: 3, copies }, false, again), { from: whole.hits[2], to: whole.hits[2] + 1, confirmed: true, by: 'ordinal' }, 'and so they do for the budgeted reader (placedFor) off the whole memo');
  assert.equal(again.left, REFRESH_SCAN_BUDGET);
  // a position inside the run, where the quote itself sits (the fixture's first form): the passage is there, and no
  // tie rule is reached, whatever the fields say (the review's third round; before it the rules ran on this state)
  const onQuote = head.length + 5;
  assert.ok(flat.startsWith(anchor.quote, onQuote) && !whole.hits.includes(onQuote), 'the fixture: the quote at the position, and no whole copy there');
  assert.deepEqual(locateStored(flat, { anchor, anchorAt: onQuote }, false), { from: onQuote, to: onQuote + 1, confirmed: true, by: 'position' }, 'the quote at the position: the position, and the tie rules are not reached');
  assert.deepEqual(locateStored(flat, { anchor, anchorAt: onQuote, ordinal: 3, copies }, false), { from: onQuote, to: onQuote + 1, confirmed: true, by: 'position' }, 'and the fields do not move it off the quote');
});

test('a src-less region comment on a passage whose whole anchor sits at more copies than one write\'s budget enumerates: after a raw write above it every write on the file lands (before the fix: a TypeError off a null placement, the kernel\'s host-error, until the sidecar was edited by hand)', () => {
  const w = world();
  const line = '![](f.png)\n';
  const count = 60000;
  const text = `# Figures\n\n${line.repeat(count)}`;
  assert.ok(Buffer.byteLength(text, 'utf8') < TEXT_MAX_BYTES, 'the fixture: under the text cap');
  const big = path.join(w.docs, 'figures.md');
  fs.writeFileSync(big, text);
  const r = comment(w, big, { note: 'Overall.' });
  const at = text.indexOf(line, text.length >> 1);   // a copy in the middle, the cap's context on both sides
  const anchor = engine.makeAnchor(text, at, at + '![](f.png)'.length, ANCHOR_CTX_CAP);
  const needle = anchor.prefix + anchor.quote + anchor.suffix;
  const copies = fullMatches(text, anchor, REFRESH_COPIES_MAX).hits.length;
  assert.ok(copies > 50000 && copies < REFRESH_COPIES_MAX, `the fixture: ${copies} whole copies, under the copies cap`);
  assert.ok(Math.ceil(text.length / REFRESH_PASS_DIVISOR) + copies * needle.length > REFRESH_SCAN_BUDGET, 'the fixture: enumerating them costs more than one write\'s budget, so the refresh\'s scan is cut');
  // another writer left a region comment on the passage in the contract's src-less shape: the host names its figure from the passage
  const disk = readSidecar(r.storePath);
  disk.comments.push({ id: 'region-1', author: 'web', ts: 1700000000001, anchor, anchorAt: at, target: { kind: 'image', region: REGION }, body: 'On this figure.', replies: [], resolved: false });
  writeSidecar(r.storePath, disk);
  let st = status(w, big);
  assert.equal(st.derivedSrcs['region-1'], 'f.png', 'the fixture: the position names its copy, and the passage names the figure');
  // a raw write puts a line above every copy: the position names none of them now
  const moved = `# Figures\n\nA line the person added.\n\n${line.repeat(count)}`;
  rawWrite(big, moved);
  st = status(w, big);
  assert.equal(st.derivedSrcs['region-1'], 'f.png', 'a read places the passage first (no budgeted scan precedes it) and names the figure');
  const guess = engine.locateAnchor(moved, anchor, at).from;
  assert.deepEqual(st.placed, { 'region-1': { at: guess, confirmed: false, by: 'nearest' } }, 'the tie the position no longer settles: the nearest copy, a guess');
  // the writes: the refresh's budgeted scan is cut and memoized, and the reply's figure reader then asks without a budget
  const res = ok(w, { verb: 'comment', path: big, args: { note: 'On the whole file, again.' }, fence: fenceFor(st) });
  assert.equal(res.json.store.comments.length, 3, 'the comment landed');
  assert.equal(res.json.derivedSrcs['region-1'], 'f.png', 'the figure named off the whole scan');
  assert.deepEqual(res.json.placed, { 'region-1': { at: guess, confirmed: false, by: 'nearest' } }, 'the verdict, off the whole result the budgeted reader now has for free');
  assert.deepEqual(keptNotes(res.stderr), [1], 'the refresh kept the position for the budget, and said so once');
  assert.ok(!/TypeError/.test(res.stderr), res.stderr);
  assert.ok(res.ms < 8000, `the comment took ${res.ms} ms`);
  st = status(w, big);
  const rep = ok(w, { verb: 'reply', path: big, args: { commentId: 'region-1', note: 'Noted.' }, fence: fenceFor(st) });
  assert.equal(rep.json.store.comments[1].replies.length, 1, 'the reply landed');
  assert.equal(readSidecar(r.storePath).comments[1].anchorAt, at, 'the position stands: a tie after an edit nobody recorded');
  assert.equal('ordinal' in readSidecar(r.storePath).comments[1], false, 'no copy fields: the position names no copy, so none are stamped');
});

// ── the budgeted reader charges nothing for the engine's verdict it drops ──

test('locateStored under a budget answers a whole anchor that sits nowhere unplaced after one classification pass, charging nothing for the engine\'s verdict the reply\'s placed map drops; without a budget the engine places it', () => {
  const nowhere = { quote: MARKER, prefix: 'context an editor rewrote before ', suffix: ' and rewrote after' };
  assert.deepEqual(fullMatches(TIED, nowhere, 10).hits, [], 'the fixture: the whole anchor sits nowhere');
  const at = nth(TIED, MARKER, 1);
  const budget = { left: REFRESH_SCAN_BUDGET, skipped: 0, unscanned: 0 };
  assert.deepEqual(locateStored(TIED, { anchor: nowhere, anchorAt: at }, true, budget), { by: 'engine' }, 'unplaced: the engine\'s to place, and the budgeted reader carries no engine verdict');
  assert.equal(REFRESH_SCAN_BUDGET - budget.left, Math.ceil(TIED.length / REFRESH_PASS_DIVISOR), 'one classification pass, and nothing for the engine\'s two locates (eight passes before the fix)');
  assert.equal(budget.skipped, 0, 'not counted as skipped: no engine scan was asked for');
  const loc = locateStored(TIED, { anchor: nowhere, anchorAt: at }, true);
  assert.equal(loc.by, 'engine');
  assert.equal(loc.from, engine.locateAnchor(TIED, nowhere, at).from, 'without a budget the engine places it by the position');
  assert.equal(loc.confirmed, false, 'three occurrences of the quote score alike: a guess');
});

test('a status on a near-cap file with more context-edited comments than the old charge admitted still confirms a tied comment behind them from its ordinal, with nothing on stderr (before the fix: no entry, the budget spent on engine verdicts the map drops)', () => {
  const w = world();
  const { text: body, quotes } = sections(800);
  const tail = `## Tied A\n\n${PARA}\n\n## Tied B\n\n${PARA}\n`;
  const text = body + tail;
  assert.ok(text.length < TEXT_MAX_BYTES && text.length > 1.5 * 1024 * 1024, `the fixture: ${text.length} bytes`);
  const pass = Math.ceil(text.length / REFRESH_PASS_DIVISOR);
  // the old charge for a comment whose whole anchor sits nowhere: the classification pass, the quote count's pass and
  // the engine's two locates at three passes each, about eight passes; this many spent the budget before the tied
  // comment at the end of the store was reached. Now each costs the classification pass alone.
  const n = Math.ceil(REFRESH_SCAN_BUDGET / (8 * pass)) + 3;
  assert.ok(n < quotes.length && n * pass < REFRESH_SCAN_BUDGET / 4, `the fixture: ${n} comments, a pass each`);
  const big = path.join(w.docs, 'big.md');
  fs.writeFileSync(big, text);
  const r = comment(w, big, { note: 'Overall.' });
  const disk = readSidecar(r.storePath);
  for (let i = 0; i < n; i++) {
    const at = text.indexOf(quotes[i]);
    assert.equal(text.indexOf(quotes[i], at + 1), -1, 'the fixture: the quote occurs once');
    disk.comments.push({ id: `1700000000000-${at}-${i}`, author: 'you', ts: 1700000000000 + i, anchor: { quote: quotes[i], prefix: 'Context an editor rewrote ', suffix: ' and rewrote after' }, anchorAt: at, body: `Note ${i}.`, replies: [], resolved: false });
  }
  const copies = [nth(text, MARKER, 0), nth(text, MARKER, 1)];
  const tied = { id: 'tied', author: 'you', ts: 1700000009999, anchor: engine.makeAnchor(text, copies[1], copies[1] + MARKER.length, ANCHOR_CTX_CAP), anchorAt: copies[1] - 7, ordinal: 2, copies: 2, section: 'Big > Tied B', body: 'Say it once.', replies: [], resolved: false };
  assert.deepEqual(fullMatches(text, tied.anchor, 10).hits, copies, 'the fixture: two whole copies, tied at the cap');
  disk.comments.push(tied);
  writeSidecar(r.storePath, disk);
  const st = host(w, { verb: 'status', path: big, args: {} });
  assert.equal(st.code, 0, st.stderr);
  assert.ok(st.json && st.json.ok, st.stdout.slice(0, 200));
  assert.deepEqual(st.json.placed, { tied: { at: copies[1], confirmed: true, by: 'ordinal' } }, 'the tied comment behind the pile keeps its confirmed verdict');
  assert.equal(st.stderr, '', 'nothing said on a read');
  assert.ok(st.ms < 3000, `the status took ${st.ms} ms`);
});

// ── a save with no sidecar says nothing ─────────────────────────────

test('a save on a tracked file with no sidecar, or on a file with no root, says nothing on stderr: there is no store for the refresh to judge, so the note for a library caller\'s unjudged store is not written; a file whose sidecar holds a passage comment says nothing either', () => {
  const w = world();
  writeTrackedPaths(w.root, ['docs/tied.md']);
  let st = status(w, w.tied);
  assert.equal(st.storeMtimeNs, null, 'the fixture: tracked, no sidecar');
  const r = ok(w, { verb: 'save', path: w.tied, args: { content: `${TIED}Appendix.\n`, suggestions: [], accepted: [], rejected: [] }, fence: fileFenceFor(st) });
  assert.equal(r.json.store, null);
  assert.equal(r.json.logged, true);
  assert.equal(r.stderr, '', 'nothing said');
  // a second save, still no sidecar
  const r2 = ok(w, { verb: 'save', path: w.tied, args: { content: `${TIED}Appendix.\nMore.\n`, suggestions: [], accepted: [], rejected: [] }, fence: fileFenceFor(r.json) });
  assert.equal(r2.stderr, '');
  // a loose file with no root above it
  const loose = path.join(w.home, 'loose.md');
  fs.writeFileSync(loose, TIED);
  st = status(w, loose);
  assert.equal(st.root, null);
  const r3 = ok(w, { verb: 'save', path: loose, args: { content: `${TIED}Appendix.\n`, suggestions: [], accepted: [], rejected: [] }, fence: fileFenceFor(st) });
  assert.equal(r3.json.root, null);
  assert.equal(r3.stderr, '');
  // the control: a sidecar this script loads is judged from the file's name, and its passage comment is stamped in silence
  const m = fromBrowser(TIED, MARKER, 1);
  const rc = comment(w, w.txt, { anchor: m.anchor, note: 'In a text file.', hintOffset: m.hintOffset });
  assert.deepEqual(copyFields(readSidecar(rc.storePath).comments[0]), [2, 3, '']);
  st = status(w, w.txt);
  const r4 = ok(w, { verb: 'save', path: w.txt, args: { content: `${TIED}Appendix.\n`, suggestions: [], accepted: [], rejected: [] }, fence: fileFenceFor(st) });
  assert.deepEqual(copyFields(r4.json.store.comments[0]), [2, 3, ''], 'stamped from the judgment at load');
  assert.equal(r4.stderr, '');
});

// ── stampCopy writes nothing where the position is not among the whole matches ──

test('a comment the refresh carries to the quote\'s other occurrence (a tracked edit inside the chosen copy\'s surroundings) keeps its copy fields, since its position is then not among the whole anchor\'s matches; the reject carries it back with the fields refreshed', () => {
  const w = world();
  const m = fromBrowser(TIED, MARKER, 1);
  const r = comment(w, w.tied, { anchor: m.anchor, note: 'Say it once.', hintOffset: m.hintOffset });
  const c = readSidecar(r.storePath).comments[0];
  assert.deepEqual(copyFields(c), [2, 3, 'Report > Second pass']);
  assert.equal(c.anchorAt, m.idx);
  // the session inserts two characters inside the chosen copy's 480-character prefix; the heading makes the --old unique
  const head = `## Second pass\n\n${PARA.slice(0, 100)}`;
  assert.equal(TIED.indexOf(head), TIED.lastIndexOf(head), 'the fixture: unique --old');
  cliOk(w, 'edit', ['--file', w.tied, '--old', head, '--new', `${head}X `]);
  const edited = fs.readFileSync(w.tied, 'utf8');
  assert.equal(nth(edited, MARKER, 1), m.idx + 2, 'the fixture: the quote moved by two');
  assert.deepEqual(fullMatches(edited, c.anchor, 10).hits, [nth(edited, MARKER, 0), nth(edited, MARKER, 2)], 'the fixture: the other two copies are whole, the edited one is not');
  let st = status(w, w.tied);
  assert.equal(st.hunks.length, 1, 'one pending change');
  const r2 = ok(w, { verb: 'reply', path: w.tied, args: { commentId: c.id, note: 'Still once.' }, fence: fenceFor(st) });
  const after = readSidecar(r2.json.storePath).comments[0];
  assert.equal(after.anchorAt, m.idx + 2, 'followed: the recorded change carried the position to where it left the quote');
  assert.deepEqual(copyFields(after), [2, 3, 'Report > Second pass'], 'the fields stand: the position is not among the whole matches, so nothing is written (without the guard: 0 of 2)');
  assert.deepEqual(Object.keys(after), PASSAGE_KEYS, 'the slots keep their order');
  assert.deepEqual(r2.json.store.comments[0].anchorAt, m.idx + 2);
  // the person rejects the change: the text is TIED again, the position follows back, and the fields are refreshed there
  st = status(w, w.tied);
  const r3 = ok(w, { verb: 'reject', path: w.tied, args: { ids: [st.hunks[0].id] }, fence: fileFenceFor(st) });
  assert.equal(fs.readFileSync(w.tied, 'utf8'), TIED);
  const back = readSidecar(r3.json.storePath).comments[0];
  assert.equal(back.anchorAt, m.idx, 'back on the chosen copy');
  assert.deepEqual(copyFields(back), [2, 3, 'Report > Second pass']);
});

// ── an unjudged store: the heading path left, and the note once ─────

test('a library caller\'s store, which this script neither loaded nor seeded, has its ordinal and count refreshed and its heading path left as it is (judging the file from anything but its name would have rewritten it), and stderr says so once per process', () => {
  const dir = path.join(SCRATCH, 'lib');
  const root = path.join(dir, 'notes-api');
  fs.mkdirSync(path.join(root, 'docs'), { recursive: true });
  const file = path.join(root, 'docs', 'intro.md');
  fs.writeFileSync(file, '# Intro\n\nHere is the passage to comment on.\n');
  const script = path.join(dir, 'library-caller.mjs');
  fs.writeFileSync(script, [
    "import fs from 'node:fs';",
    "import { createRequire } from 'node:module';",
    `import { stageSidecar, discardSidecar } from ${JSON.stringify(pathToFileURL(HOST).href)};`,
    `import { loadStore, saveStore, storePathFor } from ${JSON.stringify(pathToFileURL(path.join(VENDOR, 'store-io.mjs')).href)};`,
    `const engine = createRequire(import.meta.url)(${JSON.stringify(path.join(VENDOR, 'engine.js'))});`,
    'const [root, file] = process.argv.slice(2);',
    "const text = fs.readFileSync(file, 'utf8');",
    "const at = text.indexOf('the passage');",
    "const anchor = engine.makeAnchor(text, at, at + 'the passage'.length);",
    'const storePath = storePathFor(root, file);',
    "saveStore(root, storePath, { v: 3, path: 'docs/intro.md', suggestions: [], comments: [{ id: 'c1', author: 'you', ts: 1, anchor, anchorAt: at, ordinal: 7, copies: 9, section: 'Stale > Path', body: 'Note.', replies: [], resolved: false }], detached: [] }, text);",
    'const out = [];',
    'for (let i = 0; i < 2; i++) {',
    '  const staged = stageSidecar(root, storePath, loadStore(storePath, text), text);',
    "  const c = JSON.parse(fs.readFileSync(staged, 'utf8')).comments[0];",
    '  out.push([c.ordinal, c.copies, c.section]);',
    '  discardSidecar(staged);',
    '}',
    'process.stdout.write(JSON.stringify(out));',
    '',
  ].join('\n'));
  const r = spawnSync(process.execPath, [script, root, file], { encoding: 'utf8' });
  assert.equal(r.status, 0, r.stderr);
  assert.deepEqual(JSON.parse(r.stdout), [[1, 1, 'Stale > Path'], [1, 1, 'Stale > Path']], 'the ordinal and the count refreshed, the heading path left');
  const lines = r.stderr.split('\n').filter(Boolean);
  assert.deepEqual(lines, [UNJUDGED], 'the note, once per process, and nothing else');
});

// ── the heading and front-matter regexes cost linear time ───────────

test('sectionAt: a run of whitespace inside a heading line or a front-matter line costs linear time (the lazy regexes backtracked quadratically: 80k spaces cost five seconds), and the words read as before', () => {
  const run = ' '.repeat(80000);
  const [sec, ms] = timed(() => { const t = `# a${run}b\n\nbody\n`; return sectionAt(t, t.indexOf('body'), true); });
  assert.equal(sec, 'a b', 'the run collapses to one space');
  assert.ok(ms < 1000, `a heading line with 80k spaces inside took ${ms} ms`);
  const [secT, msT] = timed(() => { const t = `#\ta${'\t'.repeat(80000)}b\t\n\nbody\n`; return sectionAt(t, t.indexOf('body'), true); });
  assert.equal(secT, 'a b');
  assert.ok(msT < 1000, `tabs: ${msT} ms`);
  // a front-matter body line with the run and no colon is not a key: the block is not front matter, and its hash line is a heading
  const [sec2, ms2] = timed(() => { const t = `---\ntitle: x\nnote${run}here\n# probe\n---\n\nbody\n`; return sectionAt(t, t.indexOf('# probe'), true); });
  assert.equal(sec2, 'probe', 'not front matter: the probe line is a heading');
  assert.ok(ms2 < 1000, `a front-matter line with 80k spaces took ${ms2} ms`);
  // the run before the colon: a key still, so the block is front matter and the probe line is a YAML comment
  const [sec3, ms3] = timed(() => { const t = `---\ntitle: x\nnote${run}: here\n# probe\n---\n\nbody\n`; return sectionAt(t, t.indexOf('# probe'), true); });
  assert.equal(sec3, '', 'front matter: the probe line is no heading');
  assert.ok(ms3 < 1000, `${ms3} ms`);
  // the words, as the first cut read them
  const words = (line) => { const t = `${line}\n\nbody\n`; return sectionAt(t, t.indexOf('body'), true); };
  assert.equal(words('# Title   '), 'Title', 'trailing whitespace dropped');
  assert.equal(words('# Title ##   '), 'Title', 'closing hashes and the whitespace after them dropped');
  assert.equal(words('# Title #'), 'Title');
  assert.equal(words('# Title#'), 'Title#', 'a hash with no space before it is part of the words');
  assert.equal(words('#\tTabbed\t'), 'Tabbed');
  assert.equal(words('# a   b'), 'a b', 'inner whitespace collapsed');
  assert.equal(words('   # Indented three'), 'Indented three');
  assert.equal(words('    # four'), '', 'four spaces: a code block, not a heading');
  assert.equal(words('#######  seven'), '', 'seven hashes: no heading');
  assert.equal(words('#hashtag'), '', 'no space after the marks: no heading');
  assert.equal(words('##'), '', 'marks alone: a heading with no words');
  assert.equal(words('# A\n\n## B'), 'A > B');
  // the front-matter key test, line by line as the viewer's: the probe line is a YAML comment inside a block and a heading outside one
  const fm = (line) => { const t = `---\n${line}\n# probe\n---\n\nbody\n`; return sectionAt(t, t.indexOf('# probe'), true) === ''; };
  assert.equal(fm('key: value'), true);
  assert.equal(fm('key:'), true, 'a colon at the end of the line');
  assert.equal(fm('key :  value'), true, 'whitespace before the colon');
  assert.equal(fm('"quoted key" : v'), true);
  assert.equal(fm("'single': v"), true);
  assert.equal(fm('Über: x'), true, 'a key in any script');
  assert.equal(fm('日本語: x'), true);
  assert.equal(fm('_under: x'), true);
  assert.equal(fm('key:value'), false, 'a colon with no whitespace after it is no key');
  assert.equal(fm('"quoted":value'), false);
  assert.equal(fm('- item'), false, 'a sequence item with no key above');
  assert.equal(fm(':x'), false, 'an indicator first');
  assert.equal(fm('See the notes.'), false, 'prose');
  assert.equal(fm('a: b\n  nested: c\n- item'), true, 'a nested line and an item under a key');
});

test('a comment on a 120 KB markdown file whose heading line carries 120k spaces lands well inside the kernel\'s deadline with the capped heading path (13 s before the fix, and the kernel killed the host at 10 s)', () => {
  const w = world();
  const text = `# Report${' '.repeat(120000)}end\n\nA unique passage to comment on.\n`;
  const wide = path.join(w.docs, 'wide.md');
  fs.writeFileSync(wide, text);
  const m = fromBrowser(text, 'unique passage', 0);
  const st = status(w, wide);
  const res = ok(w, { verb: 'comment', path: wide, args: { anchor: m.anchor, note: 'Wide.', hintOffset: m.hintOffset }, fence: fenceFor(st) });
  const c = readSidecar(res.json.storePath).comments[0];
  assert.deepEqual(copyFields(c), [1, 1, 'Report end'], 'the heading\'s words, the run collapsed');
  assert.ok(res.ms < 5000, `the comment took ${res.ms} ms`);
  const st2 = status(w, wide);
  const res2 = ok(w, { verb: 'resolve', path: wide, args: { commentId: c.id, on: true }, fence: fenceFor(st2) });
  assert.ok(res2.ms < 5000, `the resolve took ${res2.ms} ms`);
  assert.deepEqual(copyFields(res2.json.store.comments[0]), [1, 1, 'Report end']);
});

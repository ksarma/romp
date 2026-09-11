// The recurring-passage tie-break, the review's third round (2026-09-11; plans/file-review.md, decision 51). Five findings
// on the host, each pinned here against the real host as a child process or its exported readers:
//   * a comment whose position the refresh carried to the quote's own occurrence (a tracked edit inside the chosen
//     copy's context) had the tie rules run over the OTHER whole copies, and with two copies under one heading the
//     section rule confirmed the second, which the panel painted plainly as the copy chosen while the reply's own
//     anchorAt named the first. A position the quote alone sits at names the passage now (locateStored's `position`,
//     quoteSitsAt), the reply's placed map carries no entry for it, and the panel paints as before the tie-break. The
//     same state held from the tracked edit to the next host write, with the disk's position two characters stale
//     and no quote at it: while every change is on record, a verdict the recorded changes carry elsewhere is not
//     forwarded either (placedFor, carriedTo), and one they carry to the same copy is, so a tracked insertion above
//     keeps its confirmation in that window. The panel's half of that split (the nearest whole copy in the dashed cue
//     with the stored-position words, nothing at the quote) is driven in
//     ui/webview/file-comments-host-tiebreak-review-3-panel.test.ts, over the stand-in and over this scenario's real reply;
//   * the ordinal rule confirmed a copy under another heading after an unrecorded edit that kept the count (one copy
//     deleted, one pasted): the ordinal now yields where the stored heading path names other copies and not its own,
//     and the tie is a guess; a heading renamed or deleted above the copies still leaves the ordinal confirmed;
//   * creation wrote REFRESH_COPIES_MAX itself as `copies` for a passage whole at more places than that, a count the
//     refresh's stamping pass refuses to write; nothing is written at creation either now;
//   * the front-matter reader closed a block on YAML's `...` while the viewer's test (md-config.ts, FRONT_MATTER_RE)
//     closes on `---` alone, so a heading in such a block was shown to the person and absent from the stored path;
//   * the section rule filtered every enumerated copy per comment and the nearest pick walked them all, so a status on
//     a few thousand tied comments sharing one anchor at REFRESH_COPIES_MAX ran past the kernel's 10 s deadline: the
//     copies are grouped by heading path once per anchor (copiesUnder, charged once) and the nearest is a binary search.
// Hermetic, the tiebreak module's way: the synthetic notes-api world under a scratch directory, the host as a child
// process, the real vendored track-edit CLI where the session did something, a raw write where the person did.
// Synthetic fixtures only.
// Run: node --test tools/file-comments-host-tiebreak-review-3.test.mjs
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

import { sectionAt, locateStored, fullMatches, uniqueAnchor, ANCHOR_CTX_CAP, REFRESH_SCAN_BUDGET, REFRESH_PASS_DIVISOR } from './file-comments-host.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const HOST = path.join(REPO, 'tools', 'file-comments-host.mjs');
const VENDOR = path.join(REPO, 'vendor', 'track-changents');
const engine = createRequire(import.meta.url)(path.join(VENDOR, 'engine.js'));
const hostSrc = fs.readFileSync(HOST, 'utf8');

const SID = '11111111-2222-3333-4444-555555555555';
const COPIES_MAX = 65_536;
assert.ok(hostSrc.includes('const REFRESH_COPIES_MAX = 65_536;'), 'the fixture: the copies cap this module counts against');

let SCRATCH;
before(() => { SCRATCH = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-fc-tiebreak-r3-')); });
after(() => { try { fs.rmSync(SCRATCH, { recursive: true, force: true }); } catch { /* ignore */ } });

// ── the world ───────────────────────────────────────────────────────
const PARA = ('The quick brown fox jumps over the lazy dog. '.repeat(12)
  + 'Here is the marker phrase to comment on. '
  + 'Pack my box with five dozen liquor jugs. '.repeat(12)).trim();
const MARKER = 'the marker phrase';
assert.ok(PARA.indexOf(MARKER) > ANCHOR_CTX_CAP && PARA.length - PARA.indexOf(MARKER) - MARKER.length > ANCHOR_CTX_CAP,
  'the fixture: the phrase sits more than the cap from both ends of its paragraph');
const OPENING = '# Report\n\nA short opening line that occurs once.\n\n';
const TIED = `${OPENING}## First pass\n\n${PARA}\n\n## Second pass\n\n${PARA}\n\n## Third pass\n\n${PARA}\n`;
// two copies under one heading and a third under another: the state the first finding needs
const ALPHA = `${OPENING}## Alpha\n\n${PARA}\n\n${PARA}\n\n## Beta\n\n${PARA}\n`;
// two copies under two headings: the second finding's first probe
const TWO = `${OPENING}## First pass\n\n${PARA}\n\n## Second pass\n\n${PARA}\n`;

let worlds = 0;
function world() {
  const home = path.join(SCRATCH, `w${++worlds}`, 'home');
  const root = path.join(home, 'notes-api');
  fs.mkdirSync(path.join(root, '.git'), { recursive: true });
  fs.mkdirSync(path.join(root, 'docs'));
  fs.writeFileSync(path.join(root, 'docs', 'tied.md'), TIED);
  fs.writeFileSync(path.join(root, 'docs', 'alpha.md'), ALPHA);
  fs.writeFileSync(path.join(root, 'docs', 'two.md'), TWO);
  const docs = path.join(root, 'docs');
  return { home, root, docs, tied: path.join(docs, 'tied.md'), alpha: path.join(docs, 'alpha.md'), two: path.join(docs, 'two.md') };
}
function env(w, extra) {
  const e = { ...process.env, FILE_COMMENTS_HOME: w.home, ...(extra || {}) };
  delete e.TRACKCHANGES_ROOT;
  if (!extra || !('ROMP_SID' in extra)) { delete e.ROMP_SID; delete e.ROMP_SESSION_NAME; }
  return e;
}
function host(w, req) {
  const t0 = performance.now();
  const r = spawnSync(process.execPath, [HOST], { input: JSON.stringify(req), encoding: 'utf8', env: env(w), maxBuffer: 64 * 1024 * 1024 });
  let json = null;
  try { json = JSON.parse(r.stdout); } catch { json = null; }
  return { code: r.status, stdout: r.stdout, stderr: r.stderr, json, ms: performance.now() - t0 };
}
function ok(w, req) {
  const r = host(w, req);
  assert.equal(r.code, 0, `exit ${r.code}: ${r.stderr}`);
  assert.ok(r.json && r.json.ok === true, `expected ok:true, got ${r.stdout.slice(0, 300)}`);
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
function comment(w, file, args) { return ok(w, { verb: 'comment', path: file, args, fence: fenceFor(status(w, file)) }).json; }
function readSidecar(sp) { return JSON.parse(fs.readFileSync(sp, 'utf8')); }
function writeSidecar(sp, obj) { fs.writeFileSync(sp, JSON.stringify(obj, null, 2)); }
function rawWrite(file, text) { fs.writeFileSync(file, text); }
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
const copyFields = (c) => [c.ordinal, c.copies, c.section];
const span = (at, confirmed, by) => ({ from: at, to: at + MARKER.length, confirmed, by });
const fresh = () => ({ left: REFRESH_SCAN_BUDGET, skipped: 0, unscanned: 0 });

// ── the position at the quote: the refresh's own state ──────────────

test('a comment the refresh carried to the quote\'s own occurrence, two copies under its heading: the reply carries the position on the first copy and no placed entry, not the second copy confirmed by section (before the fix the panel painted the second plainly); locateStored answers the position', () => {
  const w = world();
  const m = fromBrowser(ALPHA, MARKER, 0);
  const r = comment(w, w.alpha, { anchor: m.anchor, note: 'Say it once.', hintOffset: m.hintOffset });
  const c = readSidecar(r.storePath).comments[0];
  assert.deepEqual(copyFields(c), [1, 3, 'Report > Alpha']);
  assert.equal(c.anchorAt, m.idx);
  // the session inserts two characters inside the first copy's 480-character prefix; the heading makes the --old unique
  const head = `## Alpha\n\n${PARA.slice(0, 100)}`;
  assert.equal(ALPHA.indexOf(head), ALPHA.lastIndexOf(head), 'the fixture: unique --old');
  cliOk(w, 'edit', ['--file', w.alpha, '--old', head, '--new', `${head}X `]);
  const edited = fs.readFileSync(w.alpha, 'utf8');
  const quoteAt = m.idx + 2;
  assert.equal(nth(edited, MARKER, 0), quoteAt, 'the fixture: the quote moved by two');
  const whole = fullMatches(edited, c.anchor, 10).hits;
  assert.deepEqual(whole, [nth(edited, MARKER, 1), nth(edited, MARKER, 2)], 'the fixture: the other two copies are whole, the edited one is not');
  assert.equal(sectionAt(edited, whole[0], true), 'Report > Alpha', 'the fixture: exactly one whole copy under the stored heading, the one the section rule confirmed before the fix');
  // a status before any host write: the stale position (the quote sits two characters on) and no entry
  let st = status(w, w.alpha);
  assert.equal(st.store.comments[0].anchorAt, m.idx, 'a read rewrites nothing');
  assert.deepEqual(st.placed, {}, 'no verdict on another copy: the recorded edit carries the stale position to the quote inside the first copy, not to the second (before the fix: the second copy, confirmed by section, from the tracked edit to the next write)');
  // a write: the refresh carries the position to the quote (the recorded change vouches), the fields stand, no entry
  const r2 = ok(w, { verb: 'reply', path: w.alpha, args: { commentId: c.id, note: 'Still once.' }, fence: fenceFor(st) }).json;
  const after = readSidecar(r2.storePath).comments[0];
  assert.equal(after.anchorAt, quoteAt, 'followed: the recorded change carried the position to where it left the quote');
  assert.deepEqual(copyFields(after), [1, 3, 'Report > Alpha'], 'the fields stand: the position is not among the whole matches');
  assert.deepEqual(r2.placed, {}, 'the write\'s reply: no entry either (before the fix: the second copy, confirmed by section)');
  // the ground for the dropped entry, pinned: the engine the panel's locateComment wraps scores a whole copy over the
  // edited one, and from the position, carried or stale, picks the second copy under the heading, not the quote at the
  // position; the panel's paint of that pick (dashed, the stored-position words, nothing at the quote) is driven in
  // ui/webview/file-comments-host-tiebreak-review-3-panel.test.ts over this scenario's real reply
  assert.equal(engine.locateAnchor(edited, c.anchor, quoteAt).from, whole[0], 'from the carried position: the second copy under the heading');
  assert.equal(engine.locateAnchor(edited, c.anchor, m.idx).from, whole[0], 'from the stale one: the same');
  assert.notEqual(whole[0], quoteAt, 'a copy other than the one the host places the comment on');
  st = status(w, w.alpha);
  assert.deepEqual(st.placed, {}, 'and every later status the same');
  // the one reader of a stored anchor (passageFigure, doRetarget): the position's own occurrence, never a whole copy
  // elsewhere; under a budget (placedFor) the same, after the one classification pass, which is charged once
  const budget = fresh();
  assert.deepEqual(locateStored(edited, after, true, budget), span(quoteAt, true, 'position'), 'under a budget: the position, after the one classification pass');
  assert.equal(REFRESH_SCAN_BUDGET - budget.left, Math.ceil(edited.length / REFRESH_PASS_DIVISOR) + 2 * (c.anchor.prefix.length + MARKER.length + c.anchor.suffix.length), 'one pass and two hits, nothing for the rules');
  assert.deepEqual(locateStored(edited, after, true), span(quoteAt, true, 'position'), 'without one the same');
  // the same anchor with a position that names nothing at all still takes the rules (the section, here): the guard is
  // for the quote at the position, not for every stale one
  assert.deepEqual(locateStored(edited, { ...after, anchorAt: 3 }, true), span(whole[0], true, 'section'));
  // and a whole anchor that sits nowhere stays the engine's, whatever the position holds (the second round's pin)
  const nowhere = { quote: MARKER, prefix: 'context an editor rewrote before ', suffix: ' and rewrote after' };
  assert.deepEqual(locateStored(edited, { anchor: nowhere, anchorAt: quoteAt }, true, fresh()), { by: 'engine' });
  assert.equal(locateStored(edited, { anchor: nowhere, anchorAt: quoteAt }, true).by, 'engine');
});

test('quoteSitsAt: a raw edit of one copy\'s surroundings that leaves the quote at its position, with a third copy pasted (the count unchanged, the ordinal onto the pasted copy): the position, and no entry (before the fix: the pasted copy, confirmed by ordinal); a position outside the text or negative sits nowhere', () => {
  const w = world();
  const m = fromBrowser(TWO, MARKER, 1);
  const r = comment(w, w.two, { anchor: m.anchor, note: 'Say it once.', hintOffset: m.hintOffset });
  const c = readSidecar(r.storePath).comments[0];
  assert.deepEqual(copyFields(c), [2, 2, 'Report > Second pass']);
  // one raw write: a word changed inside the second copy's suffix, and the paragraph pasted under a third heading
  const edited = TWO.slice(0, m.idx) + TWO.slice(m.idx).replace('Pack my box', 'Pack my crate') + `\n## Third pass\n\n${PARA}\n`;
  rawWrite(w.two, edited);
  const whole = fullMatches(edited, c.anchor, 10).hits;
  assert.deepEqual(whole, [nth(edited, MARKER, 0), nth(edited, MARKER, 2)], 'the fixture: the first and the pasted copy are whole, the count is two, as stored');
  assert.ok(edited.startsWith(MARKER, m.idx), 'the fixture: the quote still sits at the position');
  const st = status(w, w.two);
  assert.deepEqual(st.placed, {}, 'the position names the quote: no entry');
  assert.deepEqual(locateStored(edited, c, true), span(m.idx, true, 'position'));
  // the whole anchor at the position wins over the quote alone there (the first case of position), and a malformed position sits nowhere
  assert.deepEqual(locateStored(TWO, c, true), span(m.idx, true, 'position'));
  for (const at of [-5, edited.length + 1, 1.5]) {
    const loc = locateStored(edited, { ...c, anchorAt: at }, true);
    assert.notEqual(loc.by, 'position', `a position of ${at} sits nowhere`);
  }
});

test('the recorded window: a tracked insertion above every copy leaves the disk\'s position stale until the next write, and the status\'s verdict stands, the ordinal\'s copy confirmed, since the recorded change carries the position to that copy; after a raw write the changes vouch for nothing and every verdict is carried as before', () => {
  const w = world();
  const m = fromBrowser(TIED, MARKER, 1);
  const r = comment(w, w.tied, { anchor: m.anchor, note: 'Say it once.', hintOffset: m.hintOffset });
  const c = readSidecar(r.storePath).comments[0];
  // longer than half the gap between copies, so nearest-wins from the stale position would pick the first copy
  const gap = nth(TIED, MARKER, 1) - nth(TIED, MARKER, 0);
  const para = `${'The session added this paragraph, on record. '.repeat(14).trim()}\n\n`;
  assert.ok(para.length > gap / 2 && para.length < gap, 'the fixture: longer than half the gap, shorter than the gap');
  cliOk(w, 'edit', ['--file', w.tied, '--old', '# Report\n\n', '--new', `# Report\n\n${para}`]);
  const above = fs.readFileSync(w.tied, 'utf8');
  assert.equal(engine.locateAnchor(above, c.anchor, c.anchorAt).from, nth(above, MARKER, 0), 'the fixture: nearest-wins from the stale position picks the first copy');
  const st = status(w, w.tied);
  assert.equal(st.store.comments[0].anchorAt, m.idx, 'a read rewrites nothing');
  assert.deepEqual(st.placed, { [c.id]: { at: nth(above, MARKER, 1), confirmed: true, by: 'ordinal' } }, 'the ordinal\'s copy, where the recorded insertion carries the position too: confirmed, in the window');
  // the write carries the position there, and the reply agrees with the status
  const r2 = ok(w, { verb: 'reply', path: w.tied, args: { commentId: c.id, note: 'Still once.' }, fence: fenceFor(st) }).json;
  assert.equal(readSidecar(r2.storePath).comments[0].anchorAt, m.idx + para.length);
  assert.deepEqual(r2.placed, {}, 'the position names its copy now');
});

// ── the ordinal against the section ─────────────────────────────────

test('the ordinal yields to a stored heading path that names other copies and not its own: a copy deleted and one pasted keep the count and move the ordinal onto a copy under another heading, and the tie is a guess (before the fix: confirmed by ordinal); a heading renamed or deleted above leaves the ordinal confirmed; a heading inserted above the ordinal\'s copy while another keeps the stored path is a guess too', () => {
  const w = world();
  const m = fromBrowser(TIED, MARKER, 1);
  const r = comment(w, w.tied, { anchor: m.anchor, note: 'Say it once.', hintOffset: m.hintOffset });
  const c = readSidecar(r.storePath).comments[0];
  assert.deepEqual(copyFields(c), [2, 3, 'Report > Second pass']);
  // one raw write: the first section replaced by a short line (so no copy lands on the stale position), a fourth appended
  const swapped = TIED.replace(`## First pass\n\n${PARA}\n\n`, 'A short line the person added.\n\n') + `\n## Fourth pass\n\n${PARA}\n`;
  const whole = fullMatches(swapped, c.anchor, 10).hits;
  assert.equal(whole.length, 3, 'the fixture: the count is unchanged');
  assert.equal(sectionAt(swapped, whole[1], true), 'Report > Third pass', 'the fixture: the ordinal\'s copy is now the one under Third pass');
  assert.equal(sectionAt(swapped, whole[0], true), 'Report > Second pass', 'the fixture: exactly one copy under the stored heading, the right one');
  assert.ok(!swapped.startsWith(MARKER, c.anchorAt) && !whole.includes(c.anchorAt), 'the fixture: the stale position names no copy and holds no quote');
  rawWrite(w.tied, swapped);
  const st = status(w, w.tied);
  const nearest = engine.locateAnchor(swapped, c.anchor, c.anchorAt).from;
  assert.deepEqual(st.placed, { [c.id]: { at: nearest, confirmed: false, by: 'nearest' } }, 'the two fields disagree: a guess, on the copy nearest the position (the engine\'s own pick)');
  assert.deepEqual(locateStored(swapped, c, true), span(nearest, false, 'nearest'));
  // the ordinal stands where the stored path names no copy at all: a heading renamed, or deleted
  const renamed = TIED.replace('## Second pass', '## Second look');
  assert.deepEqual(locateStored(renamed, { ...c, anchorAt: 0 }, true), span(nth(renamed, MARKER, 1), true, 'ordinal'), 'renamed: the path is gone, the ordinal\'s copy confirmed');
  const deleted = TIED.replace('## Second pass\n\n', '');
  assert.deepEqual(locateStored(deleted, { ...c, anchorAt: 0 }, true), span(nth(deleted, MARKER, 1), true, 'ordinal'), 'deleted: the same');
  // and where the path names the ordinal's copy among others
  const twin = TIED.replace('## Third pass\n\n', '');
  assert.equal(sectionAt(twin, nth(twin, MARKER, 2), true), 'Report > Second pass', 'the fixture: two copies under the stored heading');
  assert.deepEqual(locateStored(twin, { ...c, anchorAt: 0 }, true), span(nth(twin, MARKER, 1), true, 'ordinal'), 'the ordinal\'s copy is under the stored path, among others: confirmed');
  // a heading inserted above the ordinal's copy while another copy keeps the stored path: the fields disagree, a guess
  const inserted = TIED.replace(`## Second pass\n\n${PARA}\n\n## Third pass`, `## Second pass\n\n### Sub\n\n${PARA}\n\n## Second pass`);
  assert.deepEqual(fullMatches(inserted, c.anchor, 10).hits.map((h) => sectionAt(inserted, h, true)), ['Report > First pass', 'Report > Second pass > Sub', 'Report > Second pass']);
  assert.equal(locateStored(inserted, { ...c, anchorAt: 0 }, true).by, 'nearest', 'a lost confirmation, on purpose: the safe side of a tie the fields read two ways');
  assert.equal(locateStored(inserted, { ...c, anchorAt: 0 }, true).confirmed, false);
  // a non-markdown file and a markdown file with no headings: every copy is under the empty path, and the ordinal is never contradicted
  assert.deepEqual(locateStored(swapped, { ...c, section: '' }, false), span(whole[1], true, 'ordinal'), 'not markdown: the ordinal, as before');
  const flatMd = `${PARA}\n\n${PARA}\n\n${PARA}\n`;
  const fm = nth(flatMd, MARKER, 1);
  const flatAnchor = engine.makeAnchor(flatMd, fm, fm + MARKER.length, ANCHOR_CTX_CAP);
  assert.deepEqual(locateStored(`One line above.\n\n${flatMd}`, { anchor: flatAnchor, anchorAt: fm, ordinal: 2, copies: 3, section: '' }, true), span(fm + 'One line above.\n\n'.length, true, 'ordinal'), 'no headings: the ordinal');
});

// ── creation past the copies cap ────────────────────────────────────

test('a comment created through the host on a passage whole at more places than REFRESH_COPIES_MAX carries no copy fields (before the fix: the cap as the count, and an ordinal among the first that many), a later write adds none, and on a later text of exactly that many copies the tie is a guess, where the false count would have confirmed', () => {
  const w = world();
  const flat = 'a'.repeat(100000);
  const flatPath = path.join(w.docs, 'flat.md');
  fs.writeFileSync(flatPath, flat);
  const m = fromBrowser(flat, 'a', 50000);
  const r = comment(w, flatPath, { anchor: m.anchor, note: 'This one.', hintOffset: 50000 });
  const c = readSidecar(r.storePath).comments[0];
  const widened = uniqueAnchor(flat, 50000, 50001);
  assert.equal(widened.unique, false, 'the fixture: tied at the cap');
  const needle = widened.anchor.prefix + 'a' + widened.anchor.suffix;
  assert.ok(flat.length - needle.length + 1 > COPIES_MAX, `the fixture: ${flat.length - needle.length + 1} whole copies, past the cap`);
  assert.equal(c.anchorAt, 50000);
  assert.deepEqual(Object.keys(c), ['id', 'author', 'ts', 'anchor', 'anchorAt', 'body', 'replies', 'resolved'], 'no ordinal, copies or section: no count is known past the cap');
  assert.deepEqual(r.placed, {}, 'the position names its copy');
  // a later write keeps it so (the stamping pass refuses the state too)
  const st = status(w, flatPath);
  const r2 = ok(w, { verb: 'resolve', path: flatPath, args: { commentId: c.id, on: true }, fence: fenceFor(st) }).json;
  const after = readSidecar(r2.storePath).comments[0];
  assert.deepEqual(Object.keys(after), ['id', 'author', 'ts', 'anchor', 'anchorAt', 'body', 'replies', 'resolved']);
  assert.equal(after.resolved, true);
  // the text trimmed to exactly REFRESH_COPIES_MAX whole copies, the position past the end: a fieldless comment is a guess
  const trimmed = 'a'.repeat(COPIES_MAX + needle.length - 1);
  assert.equal(fullMatches(trimmed, c.anchor, COPIES_MAX).more, false, 'the fixture: exactly the cap, not past it');
  const stale = { ...after, anchorAt: trimmed.length };
  const loc = locateStored(trimmed, stale, true);
  assert.equal(loc.by, 'nearest');
  assert.equal(loc.confirmed, false);
  // what the false count would have done: the cap equals the count now, and the ordinal rule confirms a copy from a count that was never real
  assert.deepEqual(locateStored(trimmed, { ...stale, ordinal: 49521, copies: COPIES_MAX, section: '' }, true).by, 'ordinal', 'the hazard the fix removes');
  // a unique passage is still 1 of 1 with its heading path: the stamp at creation stands where the count is known
  const u = fromBrowser(TIED, 'A short opening line', 0);
  const ru = comment(w, w.tied, { anchor: u.anchor, note: 'Once.', hintOffset: u.hintOffset });
  assert.deepEqual(copyFields(readSidecar(ru.storePath).comments[0]), [1, 1, 'Report']);
});

// ── the front-matter closer ─────────────────────────────────────────

test('sectionAt closes a front-matter block on --- alone, as the viewer\'s test does: a block closed only by YAML\'s document-end marker is body, and the heading in it is the passage\'s path (before the fix: skipped, and the path was empty while the person saw the heading)', () => {
  const dots = '---\ntitle: x\n## Sub\n...\n\nthe passage\n';
  assert.equal(sectionAt(dots, dots.indexOf('the passage'), true), 'Sub', 'the heading the viewer renders is the path');
  assert.equal(sectionAt(dots, dots.indexOf('title:'), true), '', 'nothing above the first line');
  const dashes = '---\ntitle: x\n## Sub\n---\n\nthe passage\n';
  assert.equal(sectionAt(dashes, dashes.indexOf('the passage'), true), '', 'the same block closed by --- is front matter, and the hash line in it is no heading');
  const both = '---\ntitle: x\n...\n## Sub\n---\n\nthe passage\n';
  assert.equal(sectionAt(both, both.indexOf('the passage'), true), 'Sub', 'a ... line is no closer, and the block it fails to close is no front matter (a heading between two rules is not a YAML mapping), so the heading is read');
  const closed = '---\ntitle: x\nmore: y\n...\nlast: z\n---\n\nthe passage\n';
  assert.equal(sectionAt(closed, closed.indexOf('the passage'), true), '', 'a ... line inside a mapping the later --- closes is a body line of the block');
  // the two readers, by their source: the viewer's regex names --- as the closer and no dots, and so does the host's reader
  const viewer = fs.readFileSync(path.join(REPO, 'ui', 'webview', 'md-config.ts'), 'utf8');
  const re = /const FRONT_MATTER_RE = (\/.*\/);/.exec(viewer);
  assert.ok(re, 'the viewer\'s FRONT_MATTER_RE');
  assert.ok(re[1].includes('---[ \\t]*(?:\\n+|$)') && !re[1].includes('\\.\\.\\.'), 'closed by --- alone');
  const reader = hostSrc.slice(hostSrc.indexOf('function frontMatterLines('), hostSrc.indexOf('\n}\n', hostSrc.indexOf('function frontMatterLines(')));
  assert.ok(reader.includes('if (/^---[ \\t]*$/.test(lines[i])) { close = i; break; }'), 'the host closes on a --- line');
  assert.ok(!reader.includes('\\.\\.\\.'), 'and on no other');
});

// ── the reply's cost per tied comment ───────────────────────────────

// A stale tied comment on the one-character passage of the repeated-line file, its position on the newline (no copy,
// no quote), the fields as a stale count and the empty path: the state that ran the section rule per comment.
function staleComment(i) {
  return { id: `c-${i}`, author: 'web', ts: 1700000000000 + i, anchor: { quote: 'x', prefix: '', suffix: '' }, anchorAt: 1, ordinal: 1, copies: 2, section: '', body: `Note ${i}.`, replies: [], resolved: false };
}

test('a status on a markdown file of REFRESH_COPIES_MAX one-character copies with two thousand stale tied comments sharing the anchor answers well inside the kernel\'s deadline, every guess on the copy nearest its position (4.8 s before the fix, 16 s at four thousand); the grouping by heading path is charged once per anchor, and a budget it does not fit answers nothing known', () => {
  const w = world();
  const text = 'x\n'.repeat(COPIES_MAX);
  const rep = path.join(w.docs, 'rep.md');
  fs.writeFileSync(rep, text);
  const r = comment(w, rep, { note: 'Overall.' });
  const disk = readSidecar(r.storePath);
  const N = 2000;
  for (let i = 0; i < N; i++) disk.comments.push(staleComment(i));
  writeSidecar(r.storePath, disk);
  const st = host(w, { verb: 'status', path: rep, args: {} });
  assert.equal(st.code, 0, st.stderr);
  assert.ok(st.json && st.json.ok, st.stdout.slice(0, 200));
  assert.ok(st.ms < 3000, `the status took ${st.ms} ms`);
  assert.equal(Object.keys(st.json.placed).length, N, 'every stale comment has a verdict');
  for (let i = 0; i < N; i++) assert.deepEqual(st.json.placed[`c-${i}`], { at: 0, confirmed: false, by: 'nearest' }, `comment ${i}: nearest to the newline at 1, the earlier of the copies at 0 and 2`);
  // a write on the same sidecar lands too: the text is as the sidecar's writer left it, so the refresh asks the recorded
  // changes (none) for every comment, and the two replies it builds ask them again (27 s before the fix: a set of the
  // 65,536 copies built per comment, in movedCopy)
  const res = host(w, { verb: 'resolve', path: rep, args: { commentId: 'c-7', on: true }, fence: fenceFor(st.json) });
  assert.equal(res.code, 0, res.stderr);
  assert.ok(res.json && res.json.ok, res.stdout.slice(0, 200));
  assert.ok(res.ms < 5000, `the resolve took ${res.ms} ms`);
  assert.equal(res.json.store.comments[8].resolved, true);
  // the charge: one classification pass and its hits, then the grouping once, and nothing for the next comment on the anchor
  const budget = fresh();
  const anchor = { quote: 'x', prefix: '', suffix: '' };
  assert.deepEqual(locateStored(text, staleComment(0), true, budget), { from: 0, to: 1, confirmed: false, by: 'nearest' });
  const pass = Math.ceil(text.length / REFRESH_PASS_DIVISOR);
  assert.equal(REFRESH_SCAN_BUDGET - budget.left, pass + COPIES_MAX + COPIES_MAX, 'the pass, a character per hit, a compare per hit for the grouping');
  assert.deepEqual(locateStored(text, staleComment(1), true, budget), { from: 0, to: 1, confirmed: false, by: 'nearest' });
  assert.equal(REFRESH_SCAN_BUDGET - budget.left, pass + 2 * COPIES_MAX, 'the next comment on the anchor is free');
  // a budget the grouping does not fit: the scan fits, the grouping does not, and the comment answers nothing known
  const tight = { left: pass + COPIES_MAX + 100, skipped: 0, unscanned: 0 };
  assert.equal(locateStored(text, { ...staleComment(2), anchor: { quote: 'x', prefix: '\n', suffix: '' } }, true, tight), null, 'nothing known, rather than a walk the budget did not admit');
  assert.ok(tight.left < 100 + 2, 'the scan was charged');
  // the section rule off the grouping: two copies under a heading and one under another, a status confirms the one
  const sectioned = `# Top\n\n## A\n\n${PARA}\n\n${PARA}\n\n## B\n\n${PARA}\n`;
  const sm = nth(sectioned, MARKER, 2);
  const sa = engine.makeAnchor(sectioned, sm, sm + MARKER.length, ANCHOR_CTX_CAP);
  assert.deepEqual(locateStored(sectioned, { anchor: sa, anchorAt: 3, ordinal: 3, copies: 2, section: 'Top > B' }, true, fresh()), span(sm, true, 'section'));
  assert.deepEqual(locateStored(sectioned, { anchor: sa, anchorAt: 3, ordinal: 1, copies: 2, section: 'Top > A' }, true, fresh()), span(nth(sectioned, MARKER, 0), false, 'nearest'), 'two under the stored path: nearest, a guess');
  // the nearest is the linear pick at every position, the earlier of two at one distance
  const hits = fullMatches(text, anchor, COPIES_MAX).hits;
  const linear = (at) => { let best = hits[0]; for (const h of hits) if (Math.abs(h - at) < Math.abs(best - at)) best = h; return best; };
  for (const at of [1, 3, 5, 999, 1001, 65535, 100001, text.length - 1, text.length]) {
    assert.equal(locateStored(text, { anchor, anchorAt: at }, true).from, linear(at), `nearest at ${at}`);
  }
});

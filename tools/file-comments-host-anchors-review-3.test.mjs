// The anchors follow-on's third review (2026-09-08; plans/file-review.md, The contract and the host
// paragraph). Five properties of the refresh (refreshAnchorAts) the host must hold, each a bug this pins:
// (1) A whole anchor that sits at ONE place is not, by that alone, the passage. Two copies tied past the
//     cap, a comment on the second: an edit inside the second copy's surroundings that leaves its text
//     intact breaks the whole anchor there and leaves the first copy whole, and the refresh moved the
//     position to the first copy — the one the person never chose — and the next write made it permanent
//     (hits.includes then vouched for the wrong copy). Now the position moves to the one whole place only
//     when nothing else can be the passage (no position yet, or the quote occurs nowhere else), and
//     otherwise where the recorded changes vouch: after an edit nobody recorded it stands; after a tracked
//     edit it follows the quote to where the change left it, and back through the change's reject.
// (2) A save counts the changes the editor accepted among the ops it settles: their shift was forgotten
//     (only the save's own edit was stamped), so a tied position an accepted insertion had carried past
//     its copy never followed, while the same insertion accepted through the accept verb was followed.
//     A typed edit and an accepted change in one save compose.
// (3) The classification scan is charged at its own cost and against one budget per write, and a comment
//     whose whole anchor still sits at its position costs no scan: a near-cap file with dozens of unique
//     passage comments has every position refreshed by one save (25 per pass before, the rest stale on
//     every write, the same ones each time); CLI-written comments all gain their position in one write;
//     past the budget the note on stderr goes out once with the right count, and the next write takes up
//     where this one stopped.
// (4) The per-hit cost of a whole anchor that sits at nearly every offset is charged too: 400 cap-width
//     comments on a text of one repeated character complete a write in well under the kernel's 10 s
//     deadline (13 s before), whether their positions hold or not.
// (5) fullMatches with a budget charges the pass and its hits and cuts with `cut` when the budget is
//     spent; without one its result is what it was.
// Hermetic, the anchors suites' way: a synthetic notes-api world under a scratch directory, the host as a
// child process with one JSON request on stdin, the REAL vendored CLIs where a test says the session did
// something. Synthetic fixtures only; no real session data.
// Run: node --test tools/file-comments-host-anchors-review-3.test.mjs
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

import { fullMatches, uniqueAnchor, ANCHOR_CTX_CAP, REFRESH_SCAN_BUDGET, REFRESH_PASS_DIVISOR } from './file-comments-host.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const HOST = path.join(REPO, 'tools', 'file-comments-host.mjs');
const VENDOR = path.join(REPO, 'vendor', 'track-changents');
const FIX = path.join(REPO, 'tests', 'fixtures', 'file_comments');
const engine = createRequire(import.meta.url)(path.join(VENDOR, 'engine.js'));

const SID = '11111111-2222-3333-4444-555555555555';

let SCRATCH;
before(() => { SCRATCH = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-fc-anchors-r3-')); });
after(() => { try { fs.rmSync(SCRATCH, { recursive: true, force: true }); } catch { /* ignore */ } });

// ── the world ───────────────────────────────────────────────────────
// PARA: one paragraph over a thousand characters long with "the marker phrase" more than the cap from
// both its ends, so copies of it tie at the cap however many there are.
const PARA = ('The quick brown fox jumps over the lazy dog. '.repeat(12)
  + 'Here is the marker phrase to comment on. '
  + 'Pack my box with five dozen liquor jugs. '.repeat(12)).trim();
const MARKER = 'the marker phrase';
const REPEAT = `# Repeats\n\n${PARA}\n\n${PARA}\n\n${PARA}\n`;
// two copies, the second under a heading of its own so an edit inside it has a unique --old
const TWO = `# Repeats\n\n${PARA}\n\n## Second\n\n${PARA}\n`;

let worlds = 0;
function world() {
  const home = path.join(SCRATCH, `w${++worlds}`, 'home');
  const root = path.join(home, 'notes-api');
  fs.mkdirSync(path.join(root, '.git'), { recursive: true });
  fs.mkdirSync(path.join(root, 'docs'));
  fs.copyFileSync(path.join(FIX, 'report.md'), path.join(root, 'docs', 'report.md'));
  fs.writeFileSync(path.join(root, 'docs', 'repeat.md'), REPEAT);
  fs.writeFileSync(path.join(root, 'docs', 'two.md'), TWO);
  return {
    home, root, docs: path.join(root, 'docs'),
    report: path.join(root, 'docs', 'report.md'),
    repeat: path.join(root, 'docs', 'repeat.md'),
    two: path.join(root, 'docs', 'two.md'),
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
// The anchor the browser sends: the engine's 24 characters at the nth occurrence, and the selection's
// start offset as the hint.
function fromBrowser(text, quote, n) {
  const idx = nth(text, quote, n);
  return { anchor: engine.makeAnchor(text, idx, idx + quote.length), hintOffset: idx, idx };
}
function ties(text, anchor) { return engine.locateAnchor(text, anchor, 0).from !== engine.locateAnchor(text, anchor, text.length).from; }
// One stderr line of the refresh's note about comments that kept their position, and its count.
function keptNotes(stderr) {
  return [...stderr.matchAll(/file-comments-host: (\d+) comment\(s\) (?:whose anchor sits in whole nowhere in the text )?kept their stored position/g)].map((m) => Number(m[1]));
}

// ── (1) one whole place is not, by that alone, the passage ──────────

test('two copies tied past the cap: an edit nobody recorded inside the chosen copy\'s surroundings leaves the position, never moves it to the other copy, and the revert leaves it too', () => {
  const w = world();
  const m = fromBrowser(TWO, MARKER, 1);
  const first = nth(TWO, MARKER, 0);
  const r = comment(w, w.two, { anchor: m.anchor, note: 'Say it once.', hintOffset: m.hintOffset });
  const c = readSidecar(r.storePath).comments[0];
  assert.equal(c.anchorAt, m.idx);
  assert.deepEqual([c.anchor.prefix.length, c.anchor.suffix.length], [ANCHOR_CTX_CAP, ANCHOR_CTX_CAP], 'the fixture: tied at the cap');
  assert.deepEqual(fullMatches(TWO, c.anchor, 10).hits, [first, m.idx], 'the fixture: both copies whole');
  // a direct edit 8 characters before the passage, inside the chosen copy's prefix, leaving the quote intact
  const at2 = TWO.indexOf('Here is the marker', m.idx - 20);
  assert.equal(at2 + 'Here is '.length, m.idx, 'the fixture: the edit sits right before the passage');
  const edited = TWO.slice(0, at2) + 'Here, then, is ' + TWO.slice(at2 + 'Here is '.length);
  fs.writeFileSync(w.two, edited);
  assert.equal(nth(edited, MARKER, 1), m.idx + 7, 'the fixture: the quote moved by seven');
  assert.deepEqual(fullMatches(edited, c.anchor, 10).hits, [first], 'the fixture: only the first copy is whole now');
  let st = status(w, w.two);
  const r2 = ok(w, { verb: 'reply', path: w.two, args: { commentId: c.id, note: 'Still once.' }, fence: fenceFor(st) }).json;
  assert.equal(r2.store.comments[0].anchorAt, m.idx, 'kept: the one whole copy is the OTHER copy, and nothing recorded the edit');
  assert.equal(readSidecar(r.storePath).comments[0].anchorAt, m.idx);
  assert.notEqual(r2.store.comments[0].anchorAt, first, 'never the copy the person did not choose');
  // the edit is reverted: both copies whole again, and the position names the chosen one
  fs.writeFileSync(w.two, TWO);
  st = status(w, w.two);
  const r3 = ok(w, { verb: 'resolve', path: w.two, args: { commentId: c.id, on: true }, fence: fenceFor(st) }).json;
  assert.equal(r3.store.comments[0].anchorAt, m.idx, 'still the chosen copy');
  assert.deepEqual(r3.store.comments[0].anchor, c.anchor, 'the anchor itself is untouched');
});

test('two copies tied past the cap: a tracked edit inside the chosen copy\'s surroundings carries the position to where the change left the quote, and its reject carries it back', () => {
  const w = world();
  const m = fromBrowser(TWO, MARKER, 1);
  const first = nth(TWO, MARKER, 0);
  const r = comment(w, w.two, { anchor: m.anchor, note: 'Say it once.', hintOffset: m.hintOffset });
  const c = readSidecar(r.storePath).comments[0];
  // the session inserts two characters 440 before the passage, inside the chosen copy's 480-character
  // prefix; the heading makes the --old unique to the second copy
  const head = `## Second\n\n${PARA.slice(0, 100)}`;
  assert.equal(TWO.indexOf(head), TWO.lastIndexOf(head), 'the fixture: unique --old');
  cliOk(w, 'edit', ['--file', w.two, '--old', head, '--new', `${head}X `]);
  const moved = fs.readFileSync(w.two, 'utf8');
  assert.equal(nth(moved, MARKER, 1), m.idx + 2, 'the fixture: the quote moved by two');
  assert.deepEqual(fullMatches(moved, c.anchor, 10).hits, [first], 'the fixture: only the first copy is whole');
  assert.equal(engine.locateAnchor(moved, c.anchor, m.idx).from, first, 'the fixture: a scorer alone picks the first copy');
  let st = status(w, w.two);
  assert.equal(st.hunks.length, 1, 'one pending change');
  const r2 = ok(w, { verb: 'reply', path: w.two, args: { commentId: c.id, note: 'Still once.' }, fence: fenceFor(st) }).json;
  assert.equal(r2.store.comments[0].anchorAt, m.idx + 2, 'followed: the recorded change carried the position exactly here, and the quote sits here');
  assert.equal(readSidecar(r.storePath).comments[0].anchorAt, m.idx + 2);
  assert.deepEqual(readSidecar(r.storePath).comments[0].anchor, c.anchor, 'the anchor itself is untouched');
  // the person rejects the change: the text is TWO again, both copies whole, and the position follows back
  st = status(w, w.two);
  const r3 = ok(w, { verb: 'reject', path: w.two, args: { ids: [st.hunks[0].id] }, fence: fileFenceFor(st) }).json;
  assert.equal(fs.readFileSync(w.two, 'utf8'), TWO);
  assert.equal(r3.store.comments[0].anchorAt, m.idx, 'back on the chosen copy');
});

test('one whole place still takes the position where nothing else can be the passage: a quote that occurs once, or a comment with no position; and a unique anchor whose quote recurs follows a tracked edit above', () => {
  const w = world();
  // (a) a unique quote, moved by an edit nobody recorded: the one whole place is the passage
  const uniq = fromBrowser(w.text, 'cut p95 latency by 40%', 0);
  assert.equal(w.text.indexOf(uniq.anchor.quote, uniq.idx + 1), -1, 'the fixture: the quote occurs once');
  const r = comment(w, w.report, { anchor: uniq.anchor, note: 'Source?', hintOffset: uniq.hintOffset });
  const c = readSidecar(r.storePath).comments[0];
  assert.equal(c.anchorAt, uniq.idx);
  const raw = 'A line nobody recorded.\n';
  fs.writeFileSync(w.report, w.text.replace('# Latency report\n', `# Latency report\n${raw}`));
  let st = status(w, w.report);
  const r2 = ok(w, { verb: 'resolve', path: w.report, args: { commentId: c.id, on: true }, fence: fenceFor(st) }).json;
  assert.equal(r2.store.comments[0].anchorAt, uniq.idx + raw.length, 'refreshed: no other occurrence of the quote exists');
  // (b) "Ship it." recurs, told apart at 48; a tracked edit above moves both copies: the recorded change vouches
  fs.writeFileSync(w.report, w.text);
  st = status(w, w.report);
  const second = fromBrowser(w.text, 'Ship it.', 1);
  const r3 = ok(w, { verb: 'comment', path: w.report, args: { anchor: second.anchor, note: 'Not yet.', hintOffset: second.hintOffset }, fence: fenceFor(st) }).json;
  const ship = readSidecar(r3.storePath).comments[1];
  assert.equal(ship.anchorAt, second.idx);
  assert.ok(ship.anchor.prefix.length === 48 && !ties(w.text, ship.anchor), 'the fixture: widened once, and unique there');
  const para = `${'Reviewed by the api session. '.repeat(3)}Numbers unchanged.\n`;
  cliOk(w, 'edit', ['--file', w.report, '--old', '# Latency report\n', '--new', `# Latency report\n${para}`]);
  const moved = fs.readFileSync(w.report, 'utf8');
  assert.ok(para.length > (second.idx - nth(w.text, 'Ship it.', 0)) / 2, 'the fixture: the insertion is longer than half the gap between the copies');
  st = status(w, w.report);
  const r4 = ok(w, { verb: 'resolve', path: w.report, args: { commentId: ship.id, on: true }, fence: fenceFor(st) }).json;
  assert.equal(r4.store.comments[1].anchorAt, second.idx + para.length, 'followed through the pending insertion');
  assert.equal(engine.locateAnchor(moved, ship.anchor, 0).from, second.idx + para.length, 'the fixture: the one whole place');
  // (c) a comment the CLI wrote, with no position, on a passage whose quote recurs: the one whole place is taken
  cliOk(w, 'comment', ['--file', w.report, '--anchor', 'Cold starts remain slow', '--note', 'Still?']);
  st = status(w, w.report);
  assert.equal('anchorAt' in st.store.comments[2], false, 'the CLI writes no position');
  const r5 = ok(w, { verb: 'resolve', path: w.report, args: { commentId: ship.id, on: false }, fence: fenceFor(st) }).json;
  assert.equal(r5.store.comments[2].anchorAt, moved.indexOf('Cold starts remain slow'), 'placed at the one whole place');
});

// ── (2) a save settles the changes the editor accepted ──────────────

test('save: an insertion above a tied passage accepted in the editor carries the position to the chosen copy, as the accept verb does; a typed edit in the same save composes with it', () => {
  const w = world();
  const m = fromBrowser(REPEAT, MARKER, 1);
  const spacing = nth(REPEAT, MARKER, 2) - nth(REPEAT, MARKER, 1);
  const r = comment(w, w.repeat, { anchor: m.anchor, note: 'Say it once.', hintOffset: m.hintOffset });
  const c = readSidecar(r.storePath).comments[0];
  assert.ok(ties(REPEAT, c.anchor), 'the fixture: tied at the cap');
  // the session inserts a preamble above, longer than half the spacing, so a position left as made is
  // nearer the FIRST copy
  const preamble = `${'Preamble the session added above the repeats. '.repeat(20)}`.slice(0, Math.floor(spacing / 2) + 20) + '\n';
  assert.ok(preamble.length > spacing / 2 && preamble.length < spacing);
  cliOk(w, 'edit', ['--file', w.repeat, '--old', '# Repeats\n', '--new', `# Repeats\n${preamble}`]);
  const moved = fs.readFileSync(w.repeat, 'utf8');
  assert.equal(nth(moved, MARKER, 1), m.idx + preamble.length);
  assert.equal(engine.locateAnchor(moved, c.anchor, m.idx).from, nth(moved, MARKER, 0), 'the fixture: the stale position paints the first copy');
  let st = status(w, w.repeat);
  assert.equal(st.hunks.length, 1);
  const h = st.hunks[0];
  // the person accepts the change in the editor and saves without typing: the record leaves the field,
  // the content is the file as it is, and the decision names the texts
  const saved = ok(w, { verb: 'save', path: w.repeat, args: { content: moved, suggestions: [], accepted: [{ id: h.id, oldText: h.oldText, newText: h.newText }], rejected: [] }, fence: fileFenceFor(st) }).json;
  assert.deepEqual(saved.hunks, [], 'the change is settled');
  assert.equal(fs.readFileSync(w.repeat, 'utf8'), moved, 'the text stands');
  assert.equal(saved.store.comments[0].anchorAt, m.idx + preamble.length, 'the chosen copy: the accepted insertion is a settled op the save counts');
  assert.equal(readSidecar(r.storePath).comments[0].anchorAt, m.idx + preamble.length);
  // a later write finds the position on its copy and leaves it
  st = status(w, w.repeat);
  const r2 = ok(w, { verb: 'resolve', path: w.repeat, args: { commentId: c.id, on: true }, fence: fenceFor(st) }).json;
  assert.equal(r2.store.comments[0].anchorAt, m.idx + preamble.length);

  // the same again with a typed line in the same save: the two shifts compose
  const w2 = world();
  const rr = comment(w2, w2.repeat, { anchor: m.anchor, note: 'Say it once.', hintOffset: m.hintOffset });
  cliOk(w2, 'edit', ['--file', w2.repeat, '--old', '# Repeats\n', '--new', `# Repeats\n${preamble}`]);
  const moved2 = fs.readFileSync(w2.repeat, 'utf8');
  const st2 = status(w2, w2.repeat);
  const h2 = st2.hunks[0];
  const typed = 'Typed in the editor, above everything.\n';
  const content = moved2.replace('# Repeats\n', `# Repeats\n${typed}`);
  const saved2 = ok(w2, { verb: 'save', path: w2.repeat, args: { content, suggestions: [], accepted: [{ id: h2.id, oldText: h2.oldText, newText: h2.newText }], rejected: [] }, fence: fileFenceFor(st2) }).json;
  assert.equal(fs.readFileSync(w2.repeat, 'utf8'), content);
  assert.equal(saved2.store.comments[0].anchorAt, m.idx + preamble.length + typed.length, 'the chosen copy, through the accepted insertion and the typed line together');
  assert.equal(readSidecar(rr.storePath).comments[0].anchorAt, m.idx + preamble.length + typed.length);
});

// ── (3) the classification scan's cost, one budget per write, and no scan for a passage in place ──

// A prose file near the viewer's cap in which every paragraph carries a passage of its own.
function bigProse(paragraphs, target) {
  const filler = 'The committee reviews the quarterly numbers and files a short note for the record. ';
  const per = Math.floor(target / paragraphs);
  const parts = [];
  for (let i = 0; i < paragraphs; i++) {
    const passage = `Passage number ${i} sits here, said once in the whole file.`;
    let para = `${passage} ${filler}`;
    while (para.length < per - filler.length) para += filler;
    parts.push(para.trim());
  }
  return { text: `# Big\n\n${parts.join('\n\n')}\n`, passages: parts.map((_, i) => `Passage number ${i} sits here`) };
}
// A comment in the host's own shape on a unique passage, its position exact for `text`.
function hostComment(text, quote, i) {
  const at = text.indexOf(quote);
  assert.ok(at >= 0 && text.indexOf(quote, at + 1) === -1, `the fixture: ${quote} occurs once`);
  return { id: `1700000000000-${at}`, author: 'you', ts: 1700000000000 + i, anchor: engine.makeAnchor(text, at, at + quote.length), anchorAt: at, body: `Note ${i}.`, replies: [], resolved: false };
}

test('a save that inserts a line above 64 unique passage comments on a near-cap file refreshes every position in that one write, with no note on stderr', () => {
  const w = world();
  const { text, passages } = bigProse(64, 1.75 * 1024 * 1024);
  assert.ok(text.length > 1.7 * 1024 * 1024 && text.length < 2 * 1024 * 1024, `the fixture: ${text.length} bytes`);
  assert.ok(64 > REFRESH_SCAN_BUDGET / text.length, 'the fixture: more passages than the budget admitted at one text length per anchor');
  const big = path.join(w.docs, 'big.md');
  fs.writeFileSync(big, text);
  const r = comment(w, big, { note: 'Overall.' });
  const disk = readSidecar(r.storePath);
  disk.comments.push(...passages.map((q, i) => hostComment(text, q, i)));
  fs.writeFileSync(r.storePath, JSON.stringify(disk));
  const line = 'One line the person typed above everything.\n';
  const content = text.replace('# Big\n', `# Big\n${line}`);
  const st = status(w, big);
  const res = ok(w, { verb: 'save', path: big, args: { content, suggestions: [], accepted: [], rejected: [] }, fence: fileFenceFor(st) });
  assert.ok(res.ms < 5000, `the save took ${res.ms} ms`);
  const after = res.json.store.comments.slice(1);
  assert.deepEqual(after.map((c) => c.anchorAt), passages.map((q) => content.indexOf(q)), 'every position refreshed, the last as surely as the first');
  assert.deepEqual(keptNotes(res.stderr), [], 'nothing kept for the budget');
  assert.deepEqual(readSidecar(r.storePath).comments.slice(1).map((c) => c.anchorAt), after.map((c) => c.anchorAt), 'the reply was measured with the positions the sidecar got');
});

test('60 CLI-written passage comments on a near-cap tracked file all gain their position on one reply', () => {
  const w = world();
  const { text, passages } = bigProse(60, 1.9 * 1024 * 1024);
  const big = path.join(w.docs, 'big.md');
  fs.writeFileSync(big, text);
  const r = comment(w, big, { note: 'Overall.' });
  const disk = readSidecar(r.storePath);
  for (let i = 0; i < 60; i++) {
    const at = text.indexOf(passages[i]);
    disk.comments.push({ id: `1700000000000-${at}-${i}`, author: 'web', authorId: SID, ts: 1700000000000 + i, anchor: engine.makeAnchor(text, at, at + passages[i].length), body: `Note ${i}.`, replies: [], resolved: false });
  }
  fs.writeFileSync(r.storePath, JSON.stringify(disk));
  const st = status(w, big);
  assert.equal(st.store.comments.filter((c) => 'anchorAt' in c).length, 0, 'the CLI comments carry no position');
  const res = ok(w, { verb: 'reply', path: big, args: { commentId: disk.comments[1].id, note: 'Noted.' }, fence: fenceFor(st) });
  assert.ok(res.ms < 5000, `the reply took ${res.ms} ms`);
  assert.deepEqual(res.json.store.comments.slice(1).map((c) => c.anchorAt), passages.map((q) => text.indexOf(q)), 'all sixty placed');
  assert.deepEqual(keptNotes(res.stderr), []);
});

test('past the budget the note goes out once per write with the count of positions left stale, and the next write refreshes those, so no position stays stale for good', () => {
  const w = world();
  // more distinct anchors whose passages moved than one write's budget scans: every one costs a pass
  // (the whole anchor no longer sits at its position), and the budget admits a bounded number of them
  const { text, passages } = bigProse(1200, 1.9 * 1024 * 1024);
  const perWrite = Math.floor(REFRESH_SCAN_BUDGET / Math.ceil(text.length / REFRESH_PASS_DIVISOR));
  assert.ok(perWrite > 100 && perWrite < 1200, `the fixture: ${perWrite} passes fit one write`);
  const big = path.join(w.docs, 'big.md');
  fs.writeFileSync(big, text);
  const r = comment(w, big, { note: 'Overall.' });
  const disk = readSidecar(r.storePath);
  disk.comments.push(...passages.map((q, i) => hostComment(text, q, i)));
  fs.writeFileSync(r.storePath, JSON.stringify(disk));
  const line = 'One line the person typed above everything.\n';
  const content = text.replace('# Big\n', `# Big\n${line}`);
  let st = status(w, big);
  const res = ok(w, { verb: 'save', path: big, args: { content, suggestions: [], accepted: [], rejected: [] }, fence: fileFenceFor(st) });
  assert.ok(res.ms < 5000, `the save took ${res.ms} ms`);
  const want = passages.map((q) => content.indexOf(q));
  const after = res.json.store.comments.slice(1).map((c) => c.anchorAt);
  const stale = after.filter((at, i) => at !== want[i]).length;
  assert.ok(stale > 0 && stale < 1200, `the fixture: ${stale} of 1200 left stale by the budget`);
  assert.deepEqual(keptNotes(res.stderr), [stale], 'one note, counting exactly the positions left stale (the measure\'s pass and the stage\'s pass share the budget)');
  assert.deepEqual(readSidecar(r.storePath).comments.slice(1).map((c) => c.anchorAt), after, 'the reply carries what the sidecar got');
  // the next writes: the refreshed positions sit on their passages and cost nothing, so each write's
  // budget goes to the ones left stale (two passes each here — the whole anchor's, then the quote's, since
  // nothing recorded says where the passage went and the quote must be seen to occur once), until none is
  let left = stale;
  for (let n = 0; left > 0; n++) {
    assert.ok(n < 6, `the fixture: ${left} still stale after ${n} more writes`);
    st = status(w, big);
    const res2 = ok(w, { verb: 'resolve', path: big, args: { commentId: disk.comments[1].id, on: n % 2 === 0 }, fence: fenceFor(st) });
    assert.ok(res2.ms < 5000, `the resolve took ${res2.ms} ms`);
    const now = res2.json.store.comments.slice(1).map((c) => c.anchorAt);
    const still = now.filter((at, i) => at !== want[i]).length;
    assert.ok(still < left, `progress: ${still} stale after this write, ${left} before`);
    assert.deepEqual(keptNotes(res2.stderr), still ? [still] : [], 'the note counts what this write left stale, once');
    left = still;
  }
  assert.deepEqual(status(w, big).store.comments.slice(1).map((c) => c.anchorAt), want, 'every position current');
});

// ── (4) a whole anchor at nearly every offset ───────────────────────

test('400 cap-width comments on a text of one repeated character: a write completes well inside the kernel\'s deadline whether the positions hold or not', () => {
  const w = world();
  const text = 'a'.repeat(100000);
  const flat = path.join(w.docs, 'flat.txt');
  fs.writeFileSync(flat, text);
  const r = comment(w, flat, { note: 'Overall.' });
  const mk = (i, at) => ({ id: `1700000000000-${i}`, author: 'you', ts: 1700000000000 + i, anchor: engine.makeAnchor(text, at, at + 1 + i, ANCHOR_CTX_CAP), anchorAt: at, body: `Note ${i}.`, replies: [], resolved: false });
  // (a) every position holds its anchor (the shape the comment verb itself writes on such a file): no scan at all
  const disk = readSidecar(r.storePath);
  for (let i = 0; i < 400; i++) disk.comments.push(mk(i, 50000));
  assert.equal(uniqueAnchor(text, 50000, 50001).unique, false, 'the fixture: tied at the cap');
  fs.writeFileSync(r.storePath, JSON.stringify(disk));
  let st = status(w, flat);
  const res = ok(w, { verb: 'resolve', path: flat, args: { commentId: disk.comments[1].id, on: true }, fence: fenceFor(st) });
  assert.ok(res.ms < 3000, `the resolve took ${res.ms} ms (13 s before)`);
  assert.deepEqual(res.json.store.comments.slice(1).map((c) => c.anchorAt), new Array(400).fill(50000), 'every position kept');
  assert.deepEqual(keptNotes(res.stderr), [], 'nothing was scanned, so nothing was kept for the budget');
  // (b) positions that hold no whole anchor (too near the start for the prefix): the hits are charged as they
  // are enumerated, the budget cuts the first scan, and the rest are not scanned; every position is kept
  const disk2 = readSidecar(r.storePath);
  for (const c of disk2.comments.slice(1)) c.anchorAt = 100;
  fs.writeFileSync(r.storePath, JSON.stringify(disk2));
  st = status(w, flat);
  const res2 = ok(w, { verb: 'resolve', path: flat, args: { commentId: disk.comments[1].id, on: false }, fence: fenceFor(st) });
  assert.ok(res2.ms < 3000, `the resolve took ${res2.ms} ms`);
  assert.deepEqual(res2.json.store.comments.slice(1).map((c) => c.anchorAt), new Array(400).fill(100), 'every position kept');
  assert.deepEqual(keptNotes(res2.stderr), [400], 'one note: every comment kept its position for the budget');
});

// ── (5) fullMatches with a budget ───────────────────────────────────

test('fullMatches charges a budget the pass and each hit, cuts with `cut` when it is spent, and without a budget answers as before', () => {
  const text = 'a'.repeat(100000);
  const anchor = engine.makeAnchor(text, 50000, 50001, ANCHOR_CTX_CAP);
  const needle = anchor.prefix + anchor.quote + anchor.suffix;
  assert.equal(needle.length, 961);
  // no budget: at most `max` hits, `more` past them, no `cut` key
  assert.deepEqual(fullMatches(text, anchor, 3), { hits: [480, 481, 482], more: true });
  // a budget that admits the pass and exactly ten hits
  const pass = Math.ceil(text.length / REFRESH_PASS_DIVISOR);
  const budget = { left: pass + 10 * needle.length };
  const r = fullMatches(text, anchor, 65536, budget);
  assert.deepEqual(r.hits, [480, 481, 482, 483, 484, 485, 486, 487, 488, 489]);
  assert.equal(r.more, true);
  assert.equal(r.cut, true);
  assert.equal(budget.left, 0, 'spent to the last unit, never below zero');
  // a budget that admits everything: the whole enumeration, no cut, and the cost is the pass plus the hits
  const all = { left: 10 ** 9 };
  const r2 = fullMatches(text, { ...anchor, suffix: anchor.suffix + 'a' }, 65536, all);   // a distinct key, so no memo
  assert.equal(r2.hits.length, 65536);
  assert.equal(r2.more, true, 'cut at REFRESH_COPIES_MAX');
  assert.equal('cut' in r2, false);
  assert.equal(10 ** 9 - all.left, pass + 65536 * 962);
  // the pass alone, for a needle that sits nowhere
  const none = { left: 10 ** 9 };
  assert.deepEqual(fullMatches(text, { quote: 'b', prefix: 'a', suffix: 'a' }, 65536, none), { hits: [], more: false });
  assert.equal(10 ** 9 - none.left, pass);
});

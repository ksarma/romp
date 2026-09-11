// The anchors follow-on's review (2026-09-07; plans/file-review.md, The contract and the host paragraph):
// what the host does with an OFFSET, on creation and on refresh, is exact or it is not done.
// (1) The comment verb's hint settles a tie only when it points at one of the tied copies in the text
// the host read. The browser's hintOffset is an offset into the text it DISPLAYED; when the file moved
// between the selection and Enter, nearest-wins from that offset picked a copy by coincidence, and once
// the shift passed half the gap between two copies the note was saved on the other copy, its widened
// anchor and anchorAt built around it for every later reader. Now such a request refuses
// `anchor-ambiguous`, naming the moved text, and writes nothing; the note stays in the composer.
// (2) The refresh moves a tied anchor's anchorAt only to the one copy the recorded changes can have
// carried it to — the pending ops, the ops a write settles, the edits a write applies — never to the
// nearest copy, and only while the text is as the sidecar's last writer left it; a change nobody
// recorded leaves it as it is. Before, a tied anchor was never refreshed,
// and the highlight drifted to the wrong paragraph after a tracked insertion above; a refresh by
// nearest-wins would have stored the same wrong copy.
// (3) hintOf is behavior, not text: status tells a src-less region comment's figure from its stored
// position where the anchor ties, and retarget re-places it.
// (4) The refresh is bounded: a write on a near-cap file of repeated text with hundreds of cap-width tied
// comments completes well inside the kernel's 10 s deadline (the whole anchor is searched for once per
// comment, and the engine scans only for an anchor that sits in whole nowhere, under REFRESH_SCAN_BUDGET).
// (5) The reply's measure counts the bytes the refresh adds.
// Known limit, not tested as a refusal: an insertion above that is itself two more copies of a repeated
// line puts a copy under the stale offset with the same surroundings; no reader can tell that copy from
// the selected one, and the panel's own follow of the passage (file-comments.ts, followPassage) is what
// keeps the offset current when the panel saw the edit.
// Hermetic, the anchors test's way: a synthetic notes-api world under a scratch directory, the host as a
// child process, the REAL vendored CLIs where a test says the session did something. Synthetic only.
// Run: node --test tools/file-comments-host-anchors-exact.test.mjs
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

import { locateExact, uniqueAnchor, fullMatches, ANCHOR_CTX_CAP, REFRESH_SCAN_BUDGET, REPLY_MAX_BYTES } from './file-comments-host.mjs';
import { tinyPng, sha256 } from '../tests/fixtures/file_comments/tiny-png.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const HOST = path.join(REPO, 'tools', 'file-comments-host.mjs');
const VENDOR = path.join(REPO, 'vendor', 'track-changents');
const FIX = path.join(REPO, 'tests', 'fixtures', 'file_comments');
const engine = createRequire(import.meta.url)(path.join(VENDOR, 'engine.js'));
const hostSource = fs.readFileSync(HOST, 'utf8');

const SID = '11111111-2222-3333-4444-555555555555';

let SCRATCH;
before(() => { SCRATCH = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-fc-anchors-exact-')); });
after(() => { try { fs.rmSync(SCRATCH, { recursive: true, force: true }); } catch { /* ignore */ } });

// ── the world ───────────────────────────────────────────────────────
// report.md: "Ship it." twice with the same 24 characters either side (366 and 475). repeat.md: one
// paragraph over a thousand characters long, three times, so "the marker phrase" has identical
// surroundings for more than ANCHOR_CTX_CAP characters on both sides of every copy.
const PARA = ('The quick brown fox jumps over the lazy dog. '.repeat(12)
  + 'Here is the marker phrase to comment on. '
  + 'Pack my box with five dozen liquor jugs. '.repeat(12)).trim();
const REPEAT = `# Repeats\n\n${PARA}\n\n${PARA}\n\n${PARA}\n`;
const MARKER = 'the marker phrase';

let worlds = 0;
function world() {
  const home = path.join(SCRATCH, `w${++worlds}`, 'home');
  const root = path.join(home, 'notes-api');
  fs.mkdirSync(path.join(root, '.git'), { recursive: true });
  fs.mkdirSync(path.join(root, 'docs'));
  fs.copyFileSync(path.join(FIX, 'report.md'), path.join(root, 'docs', 'report.md'));
  fs.writeFileSync(path.join(root, 'docs', 'repeat.md'), REPEAT);
  return {
    home, root, docs: path.join(root, 'docs'),
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
// The anchor the browser sends: the engine's 24 characters at the nth occurrence, and the selection's
// start offset as the hint.
function fromBrowser(text, quote, n) {
  const idx = nth(text, quote, n);
  return { anchor: engine.makeAnchor(text, idx, idx + quote.length), hintOffset: idx, idx };
}
function noStore(w) { assert.equal(fs.existsSync(path.join(w.root, '.trackchanges')), false, 'nothing was written'); }
function ties(text, anchor) { return engine.locateAnchor(text, anchor, 0).from !== engine.locateAnchor(text, anchor, text.length).from; }

// ── (1) the comment verb's offset settles a tie only where it sits on a copy ──

test('locateExact: with exact, a tied hint that sits on no tied copy is anchor-moved; without it the stored position\'s nearest-wins rule stands', () => {
  const w = world();
  const first = fromBrowser(w.text, 'Ship it.', 0);
  const second = fromBrowser(w.text, 'Ship it.', 1);
  assert.deepEqual(first.anchor, second.anchor, 'the fixture: the copies share their 24 characters');
  assert.deepEqual(locateExact(w.text, second.anchor, second.hintOffset, { exact: true }), { from: second.idx, to: second.idx + 8 }, 'on the copy: placed');
  assert.deepEqual(locateExact(w.text, first.anchor, first.hintOffset, { exact: true }), { from: first.idx, to: first.idx + 8 });
  assert.deepEqual(locateExact(w.text, second.anchor, second.hintOffset + 3, { exact: true }), { error: 'anchor-moved' }, 'three characters off a copy: refused');
  assert.deepEqual(locateExact(w.text, second.anchor, second.hintOffset - 60, { exact: true }), { error: 'anchor-moved' });
  assert.deepEqual(locateExact(w.text, second.anchor, second.hintOffset + 3), { from: second.idx, to: second.idx + 8 }, 'the stored position\'s rule: nearest wins');
  assert.deepEqual(locateExact(w.text, second.anchor, undefined, { exact: true }), { error: 'anchor-ambiguous' }, 'no hint is no hint, exact or not');
  // one best hit: the hint is never consulted, exact or not
  const retry = fromBrowser(w.text, 'retry on timeout', 2);
  assert.deepEqual(locateExact(w.text, retry.anchor, 0, { exact: true }), { from: retry.idx, to: retry.idx + 'retry on timeout'.length });
  assert.deepEqual(locateExact(w.text, retry.anchor, retry.idx + 200, { exact: true }), { from: retry.idx, to: retry.idx + 'retry on timeout'.length });
});

test('comment: a tie whose offset points into text that moved refuses anchor-ambiguous naming the move and writes nothing; the fresh offset then lands on the selected copy', () => {
  const w = world();
  const second = fromBrowser(w.text, 'Ship it.', 1);
  const gap = second.idx - nth(w.text, 'Ship it.', 0);
  // Between the selection and Enter a session writes a paragraph above both copies, longer than half
  // the gap between them: the selection's offset is now nearer the FIRST copy.
  const para = `${'Reviewed by the api session. '.repeat(3)}Numbers unchanged.\n`;
  assert.ok(para.length > gap / 2, `the fixture: a ${para.length}-character paragraph, past half the ${gap}-character gap`);
  const moved = w.text.replace('# Latency report\n', `# Latency report\n${para}`);
  fs.writeFileSync(w.report, moved);
  assert.equal(engine.locateAnchor(moved, second.anchor, second.hintOffset).from, nth(moved, 'Ship it.', 0), 'the fixture: nearest-wins from the stale offset picks the first copy');
  const r = refused(w, { verb: 'comment', path: w.report, args: { anchor: second.anchor, note: 'Not yet.', hintOffset: second.hintOffset }, fence: { storeMtimeNs: '' } }, 'anchor-ambiguous');
  assert.ok(r.error.includes('~/notes-api/docs/report.md') && r.error.includes('the text moved after it was selected') && r.error.includes('select it again'), r.error);
  assert.ok(!r.error.includes('position was not sent'), 'the message names the moved text, not a missing offset');
  noStore(w);
  // a shift of ten characters: nearest-wins would have landed right, and the request is still refused,
  // since the offset sits on no copy and a guess that happens to be right is still a guess
  const small = w.text.replace('# Latency report\n', '# Latency report\nReviewed.\n');
  fs.writeFileSync(w.report, small);
  assert.equal(engine.locateAnchor(small, second.anchor, second.hintOffset).from, nth(small, 'Ship it.', 1));
  refused(w, { verb: 'comment', path: w.report, args: { anchor: second.anchor, note: 'Not yet.', hintOffset: second.hintOffset }, fence: { storeMtimeNs: '' } }, 'anchor-ambiguous');
  noStore(w);
  // the panel reloads, the person selects the second copy again: the offset sits on it, and it lands
  fs.writeFileSync(w.report, moved);
  const fresh = fromBrowser(moved, 'Ship it.', 1);
  assert.deepEqual(fresh.anchor, second.anchor, 'the same 24 characters; only the offset differs');
  const saved = comment(w, w.report, { anchor: fresh.anchor, note: 'Not yet.', hintOffset: fresh.hintOffset });
  const c = readSidecar(saved.storePath).comments[0];
  assert.equal(c.anchorAt, fresh.idx);
  assert.equal(c.id, `${c.ts}-${fresh.idx}`);
  assert.equal(engine.locateAnchor(moved, c.anchor).from, fresh.idx, 'the widened anchor names the selected copy for a hintless reader');
});

test('comment: an offset that still holds a copy of the quote, but not one of the tied copies, is refused too (the checklist)', () => {
  const w = world();
  const item = '- [ ] fill in\n';
  const text = `# Checklist\n\n${item.repeat(6)}\nTail.\n`;
  const list = path.join(w.docs, 'checklist.md');
  fs.writeFileSync(list, text);
  const chosen = fromBrowser(text, item, 3);
  assert.equal(chosen.idx, 55);
  assert.ok(ties(text, chosen.anchor), 'the fixture: the 24-character anchor ties across items');
  assert.deepEqual(locateExact(text, chosen.anchor, chosen.hintOffset, { exact: true }), { from: 55, to: 69 }, 'unmoved, the offset sits on its copy');
  // a session's plain edit inserts a 28-character line above
  const line = 'Reviewed by the api session\n';
  assert.equal(line.length, 28);
  const moved = text.replace('# Checklist\n\n', `# Checklist\n\n${line}`);
  fs.writeFileSync(list, moved);
  assert.ok(moved.startsWith(item, 55), 'the fixture: the quote still sits at the stale offset');
  const nearest = engine.locateAnchor(moved, chosen.anchor, chosen.hintOffset).from;
  assert.notEqual(nearest, 55, 'the fixture: the item at the stale offset is not among the tied best hits');
  assert.notEqual(nearest, 55 + 28, 'the fixture: nearest-wins picks a copy other than the selected one');
  refused(w, { verb: 'comment', path: list, args: { anchor: chosen.anchor, note: 'This one.', hintOffset: chosen.hintOffset }, fence: { storeMtimeNs: '' } }, 'anchor-ambiguous');
  noStore(w);
  const fresh = fromBrowser(moved, item, 3);
  const saved = comment(w, list, { anchor: fresh.anchor, note: 'This one.', hintOffset: fresh.hintOffset });
  assert.equal(readSidecar(saved.storePath).comments[0].anchorAt, 55 + 28);
});

test('comment on a tracked file: the tracked edit refuses store-moved, and the retry with the same offset refuses anchor-ambiguous rather than placing the note on the nearer copy', () => {
  const w = world();
  const whole = comment(w, w.report, { note: 'Overall fine.' });   // a sidecar exists, so the session's edit is a change
  const second = fromBrowser(w.text, 'Ship it.', 1);
  const fence = fenceFor(status(w, w.report));
  const para = `${'Reviewed by the api session. '.repeat(3)}Numbers unchanged.\n`;
  cliOk(w, 'edit', ['--file', w.report, '--old', '# Latency report\n', '--new', `# Latency report\n${para}`]);
  const moved = fs.readFileSync(w.report, 'utf8');
  const args = { anchor: second.anchor, note: 'Not yet.', hintOffset: second.hintOffset };
  refused(w, { verb: 'comment', path: w.report, args, fence }, 'store-moved');
  // the panel's retry: the same args against the fence it just fetched
  const r = refused(w, { verb: 'comment', path: w.report, args, fence: fenceFor(status(w, w.report)) }, 'anchor-ambiguous');
  assert.ok(r.error.includes('the text moved after it was selected'), r.error);
  assert.deepEqual(readSidecar(whole.storePath).comments.map((c) => c.body), ['Overall fine.'], 'nothing added');
  assert.equal(engine.locateAnchor(moved, second.anchor, second.hintOffset).from, nth(moved, 'Ship it.', 0), 'the fixture: the guess would have been the first copy');
});

// ── (2) the refresh follows a tied anchor's copy only where the recorded changes vouch for it ──

// The pending change's row, for the accept and reject verbs.
function hunks(w, file) { return status(w, file).hunks; }

test('a tied anchor follows its copy through a tracked insertion above longer than half the copy spacing, back through its reject, and through an edit accepted with no write between', () => {
  const w = world();
  const m = fromBrowser(REPEAT, MARKER, 1);
  const spacing = nth(REPEAT, MARKER, 2) - nth(REPEAT, MARKER, 1);
  const r = comment(w, w.repeat, { anchor: m.anchor, note: 'Say it once.', hintOffset: m.hintOffset });
  const c = readSidecar(r.storePath).comments[0];
  assert.equal(c.anchorAt, m.idx);
  assert.ok(ties(REPEAT, c.anchor), 'the fixture: the anchor alone ties at the cap');
  // the session inserts a paragraph above, longer than half the spacing: nearest-wins from the
  // position the comment was made with now picks the FIRST copy
  const para = `${'Inserted above the repeats. '.repeat(20)}`.slice(0, spacing / 2 + 5).padEnd(Math.floor(spacing / 2) + 5, 'x') + '\n';
  assert.ok(para.length > spacing / 2, `the fixture: ${para.length} characters, past half of ${spacing}`);
  cliOk(w, 'edit', ['--file', w.repeat, '--old', '# Repeats\n', '--new', `# Repeats\n${para}`]);
  const moved = fs.readFileSync(w.repeat, 'utf8');
  assert.equal(nth(moved, MARKER, 1), m.idx + para.length);
  assert.equal(engine.locateAnchor(moved, c.anchor, m.idx).from, nth(moved, MARKER, 0), 'the fixture: the stale position paints the first copy');
  assert.equal(readSidecar(r.storePath).comments[0].anchorAt, m.idx, 'the CLI wrote the object back as it was');
  // the person replies: the host write refreshes the position through the pending insertion, exactly
  let st = status(w, w.repeat);
  const r2 = ok(w, { verb: 'reply', path: w.repeat, args: { commentId: c.id, note: 'Still once.' }, fence: fenceFor(st) }).json;
  assert.equal(r2.store.comments[0].anchorAt, m.idx + para.length, 'the chosen copy, not the nearest to the stale position');
  assert.equal(readSidecar(r.storePath).comments[0].anchorAt, m.idx + para.length);
  assert.deepEqual(readSidecar(r.storePath).comments[0].anchor, c.anchor, 'the anchor itself is untouched');
  assert.equal(engine.locateAnchor(moved, c.anchor, m.idx + para.length).from, m.idx + para.length, 'the painter, hinted by it, lands on the chosen copy');
  // the person rejects the insertion: the text moves back, and so does the position
  st = status(w, w.repeat);
  assert.equal(st.hunks.length, 1);
  const r3 = ok(w, { verb: 'reject', path: w.repeat, args: { ids: [st.hunks[0].id] }, fence: fileFenceFor(st) }).json;
  assert.equal(fs.readFileSync(w.repeat, 'utf8'), REPEAT);
  assert.equal(r3.store.comments[0].anchorAt, m.idx, 'back where it was: the reversal is a recorded shift');
  // the session inserts again and the person accepts at once, with no host write between: the record
  // leaves the sidecar in that very write, and the refresh reads its shift before it goes
  cliOk(w, 'edit', ['--file', w.repeat, '--old', '# Repeats\n', '--new', `# Repeats\n${para}`]);
  assert.equal(readSidecar(r.storePath).comments[0].anchorAt, m.idx, 'stale again');
  st = status(w, w.repeat);
  const r4 = ok(w, { verb: 'accept', path: w.repeat, args: { ids: [st.hunks[0].id] }, fence: fenceFor(st) }).json;
  assert.deepEqual(r4.hunks, [], 'the change is settled');
  assert.equal(fs.readFileSync(w.repeat, 'utf8'), moved, 'accept keeps the text');
  assert.equal(r4.store.comments[0].anchorAt, m.idx + para.length, 'followed through the accepted insertion');
  assert.equal(readSidecar(r.storePath).comments[0].anchorAt, m.idx + para.length);
});

test('two tracked insertions above with no host write between are followed together; an edit nobody recorded leaves the position as it is; changes above spanning a whole copy leave it too', () => {
  const w = world();
  // the paragraphs under headings of their own, so an edit between two of them has a unique --old; the
  // marker still sits more than the cap from both ends of its paragraph, so the copies still tie
  const HEADED = `# Repeats\n\n${PARA}\n\n## Second\n\n${PARA}\n\n## Third\n\n${PARA}\n`;
  fs.writeFileSync(w.repeat, HEADED);
  const m = fromBrowser(HEADED, MARKER, 1);
  const spacing = nth(HEADED, MARKER, 2) - nth(HEADED, MARKER, 1);
  const r = comment(w, w.repeat, { anchor: m.anchor, note: 'Say it once.', hintOffset: m.hintOffset });
  const c = readSidecar(r.storePath).comments[0];
  assert.ok(ties(HEADED, c.anchor), 'the fixture: tied at the cap');
  // one insertion at the top and one under the second heading, above the chosen copy: two records
  // (not adjacent, so not coalesced), both above the chosen copy, only the first above the first copy
  const top = `${'Top line added. '.repeat(20).trimEnd()}\n`;
  const mid = `${'Middle line added. '.repeat(20).trimEnd()}\n\n`;
  assert.ok(top.length + mid.length > spacing / 2 && top.length < spacing / 2 && mid.length < spacing / 2);
  cliOk(w, 'edit', ['--file', w.repeat, '--old', '# Repeats\n', '--new', `# Repeats\n${top}`]);
  cliOk(w, 'edit', ['--file', w.repeat, '--old', '## Second\n\n', '--new', `## Second\n\n${mid}`]);
  const moved = fs.readFileSync(w.repeat, 'utf8');
  assert.equal(nth(moved, MARKER, 1), m.idx + top.length + mid.length, 'the chosen copy moved by both');
  assert.equal(nth(moved, MARKER, 0), nth(HEADED, MARKER, 0) + top.length, 'the first copy by the top line only');
  let st = status(w, w.repeat);
  assert.equal(st.hunks.length, 2, 'two pending changes');
  const r2 = ok(w, { verb: 'resolve', path: w.repeat, args: { commentId: c.id, on: true }, fence: fenceFor(st) }).json;
  assert.equal(r2.store.comments[0].anchorAt, m.idx + top.length + mid.length, 'followed through both');
  // a direct write to the file above the passage: the text is no longer as the sidecar's last writer
  // left it, so no recorded change vouches for where the copies went, and the position stands (a
  // reader's nearest-wins from it is a display-time inference, not a stored fact)
  const raw = `${'Raw line nobody recorded. '.repeat(10).trimEnd()}\n`;
  fs.writeFileSync(w.repeat, moved.replace('# Repeats\n', `# Repeats\n${raw}`));
  const rawMoved = fs.readFileSync(w.repeat, 'utf8');
  st = status(w, w.repeat);
  const r3 = ok(w, { verb: 'resolve', path: w.repeat, args: { commentId: c.id, on: false }, fence: fenceFor(st) }).json;
  assert.equal(r3.store.comments[0].anchorAt, m.idx + top.length + mid.length, 'kept: nothing recorded the shift');
  assert.equal(engine.locateAnchor(rawMoved, c.anchor, r3.store.comments[0].anchorAt).from, nth(rawMoved, MARKER, 1), 'and the painter still lands on the chosen copy while the drift is under half the spacing');
});

test('a tracked insertion above at least a copy\'s spacing long can have carried the position to two copies, so the refresh leaves it', () => {
  const w = world();
  const m = fromBrowser(REPEAT, MARKER, 1);
  const spacing = nth(REPEAT, MARKER, 2) - nth(REPEAT, MARKER, 1);
  const r = comment(w, w.repeat, { anchor: m.anchor, note: 'Say it once.', hintOffset: m.hintOffset });
  const c = readSidecar(r.storePath).comments[0];
  const wide = `${'Wide paragraph added above. '.repeat(60)}`.slice(0, spacing + 30) + '\n';
  assert.ok(wide.length > spacing);
  cliOk(w, 'edit', ['--file', w.repeat, '--old', '# Repeats\n', '--new', `# Repeats\n${wide}`]);
  const moved = fs.readFileSync(w.repeat, 'utf8');
  assert.equal(nth(moved, MARKER, 1), m.idx + wide.length);
  const st = status(w, w.repeat);
  const r2 = ok(w, { verb: 'reply', path: w.repeat, args: { commentId: c.id, note: 'Which now?' }, fence: fenceFor(st) }).json;
  assert.equal(r2.store.comments[0].anchorAt, m.idx, 'kept: the first copy and the chosen one both lie within the recorded shift');
  assert.equal(readSidecar(r.storePath).comments[0].anchorAt, m.idx);
});

test('save: the person\'s own edit above a tied passage moves the stored position by exactly the edit', () => {
  const w = world();
  const m = fromBrowser(REPEAT, MARKER, 1);
  const spacing = nth(REPEAT, MARKER, 2) - nth(REPEAT, MARKER, 1);
  const r = comment(w, w.repeat, { anchor: m.anchor, note: 'Say it once.', hintOffset: m.hintOffset });
  const c = readSidecar(r.storePath).comments[0];
  const typedIn = `${'Typed in the editor above the repeats. '.repeat(20)}`.slice(0, Math.floor(spacing / 2) + 40) + '\n';
  assert.ok(typedIn.length > spacing / 2);
  const content = REPEAT.replace('# Repeats\n', `# Repeats\n${typedIn}`);
  const st = status(w, w.repeat);
  const saved = ok(w, { verb: 'save', path: w.repeat, args: { content, suggestions: [], accepted: [], rejected: [] }, fence: fileFenceFor(st) }).json;
  assert.equal(fs.readFileSync(w.repeat, 'utf8'), content);
  assert.equal(saved.store.comments[0].anchorAt, m.idx + typedIn.length, 'the chosen copy, through the save\'s own edit');
  assert.equal(readSidecar(r.storePath).comments[0].anchorAt, m.idx + typedIn.length);
  assert.equal(engine.locateAnchor(content, c.anchor, m.idx).from, nth(content, MARKER, 0), 'the fixture: the stale position would have painted the first copy');
});

test('fullMatches names the engine\'s best hits exactly where the whole anchor sits somewhere: one is the one best hit, several are the tie, at the file\'s bounds too', () => {
  const w = world();
  for (const [quote, n] of [['retry on timeout', 2], ['Ship it.', 1], ['Ship it.', 0], ['# Latency report', 0], ['nightly run.\n', 1]]) {
    const b = fromBrowser(w.text, quote, n);
    for (const ctx of [24, 48, 480]) {
      const anchor = engine.makeAnchor(w.text, b.idx, b.idx + quote.length, ctx);
      const { hits, more } = fullMatches(w.text, anchor, 1000);
      assert.equal(more, false);
      assert.ok(hits.includes(b.idx));
      const first = engine.locateAnchor(w.text, anchor, 0).from, last = engine.locateAnchor(w.text, anchor, w.text.length).from;
      assert.equal(hits[0], first, `${quote}@${ctx}: the earliest whole match is the engine's earliest best hit`);
      assert.equal(hits[hits.length - 1], last, `${quote}@${ctx}: the latest is its latest`);
      assert.equal(hits.length === 1, !ties(w.text, anchor), `${quote}@${ctx}: one whole match is one best hit`);
    }
  }
  const m = nth(REPEAT, MARKER, 1);
  const cap = uniqueAnchor(REPEAT, m, m + MARKER.length);
  assert.equal(cap.unique, false);
  assert.deepEqual(fullMatches(REPEAT, cap.anchor, 1000), { hits: [nth(REPEAT, MARKER, 0), m, nth(REPEAT, MARKER, 2)], more: false });
  assert.deepEqual(fullMatches(REPEAT, cap.anchor, 2), { hits: [nth(REPEAT, MARKER, 0), m], more: true }, 'cut at max');
  assert.deepEqual(fullMatches(REPEAT, { quote: 'nowhere at all', prefix: '', suffix: '' }, 10), { hits: [], more: false });
  // a context edited away: no whole match, and the engine's scoring decides (the refresh's third case)
  const second = fromBrowser(w.text, 'Ship it.', 1);
  const wide = engine.makeAnchor(w.text, second.idx, second.idx + 8, 48);
  const edited = w.text.replace('## Day 2', '## Day Two');
  assert.deepEqual(fullMatches(edited, wide, 10).hits, [], 'the widened prefix no longer sits before the copy');
  assert.deepEqual(locateExact(edited, wide, undefined), { error: 'anchor-ambiguous' }, 'both copies now score by their suffix alone: the engine\'s own tie');
  assert.deepEqual(locateExact(edited, wide, second.idx + 2), { from: second.idx + 2, to: second.idx + 10 }, 'which a stored position settles, nearest wins');
  const edited2 = edited.replace('nightly run.\n\n## Day Two', 'nightly run!\n\n## Day Two');
  assert.deepEqual(fullMatches(edited2, wide, 10).hits, []);
  assert.deepEqual(locateExact(edited2, wide, undefined), { from: second.idx + 2, to: second.idx + 10 }, 'the first copy\'s suffix broken too: the second outscores it, and the engine places it with no hint');
});

// ── (3) hintOf is behavior: the stored position tells a src-less region comment's figure where the anchor ties ──

test('status tells the figure of a src-less region comment on a tied anchor from its stored position, and retarget re-places it; without the position both refuse anchor-ambiguous', () => {
  const w = world();
  const FIG = tinyPng(1, 2, 3);
  fs.writeFileSync(path.join(w.docs, 'fig.png'), FIG);
  const EMBED = '![chart](fig.png)';
  const para = `${'The quick brown fox jumps over the lazy dog. '.repeat(12)}${EMBED}${' Pack my box with five dozen liquor jugs. '.repeat(12)}`.trim();
  const text = `# Figures\n\n${para}\n\n${para}\n\n${para}\n`;
  const md = path.join(w.docs, 'figs.md');
  fs.writeFileSync(md, text);
  const e = fromBrowser(text, EMBED, 1);
  assert.ok(ties(text, e.anchor), 'the fixture: the embed lines tie');
  const region = { x: 0.12, y: 0.4, w: 0.35, h: 0.2 };
  const r = comment(w, md, { anchor: e.anchor, note: 'Label the axes.', hintOffset: e.hintOffset, target: { kind: 'image', region, src: 'fig.png' } });
  const c = readSidecar(r.storePath).comments[0];
  assert.equal(c.anchorAt, e.idx);
  assert.deepEqual([c.anchor.prefix.length, c.anchor.suffix.length], [ANCHOR_CTX_CAP, ANCHOR_CTX_CAP], 'tied at the cap');
  assert.ok(ties(text, c.anchor), 'the stored anchor alone still ties');
  // another writer leaves the target with no src (the contract's own shape)
  const disk = readSidecar(r.storePath);
  delete disk.comments[0].target.src;
  fs.writeFileSync(r.storePath, JSON.stringify(disk, null, 2) + '\n');
  let st = status(w, md);
  assert.equal(st.derivedSrcs[c.id], 'fig.png', 'told from the passage the stored position picks');
  assert.deepEqual(st.embeddedHashes, { 'fig.png': sha256(FIG) });
  assert.deepEqual(st.derivedSrcReasons, {});
  assert.equal(st.store.comments[0].target.src, 'fig.png');
  assert.equal('src' in readSidecar(r.storePath).comments[0].target, false, 'a read never rewrites the sidecar');
  const region2 = { x: 0.5, y: 0.5, w: 0.2, h: 0.2 };
  const re = ok(w, { verb: 'retarget', path: md, args: { commentId: c.id, target: { kind: 'image', region: region2 } }, fence: fenceFor(st) }).json;
  assert.deepEqual(re.store.comments[0].target, { kind: 'image', region: region2, hash: sha256(FIG), src: 'fig.png' }, 'the re-place takes the figure the stored position\'s passage embeds');
  st = status(w, md);
  const re2 = ok(w, { verb: 'retarget', path: md, args: { commentId: c.id, target: { kind: 'image', region, src: 'fig.png' } }, fence: fenceFor(st) }).json;
  assert.deepEqual(re2.store.comments[0].target.region, region);
  // with no stored position the copy fields settle the tie (the tie-break, 2026-09-11): the ordinal's copy, the count
  // being unchanged, tells the figure on both read paths
  const disk1 = readSidecar(r.storePath);
  delete disk1.comments[0].anchorAt;
  delete disk1.comments[0].target.src;
  assert.deepEqual([disk1.comments[0].ordinal, disk1.comments[0].copies], [2, 3], 'the fixture: the host wrote the copy fields');
  fs.writeFileSync(r.storePath, JSON.stringify(disk1, null, 2) + '\n');
  st = status(w, md);
  assert.equal(st.derivedSrcs[c.id], 'fig.png', 'told from the copy the ordinal names');
  assert.deepEqual(st.placed, { [c.id]: { at: e.idx, confirmed: true, by: 'ordinal' } });
  ok(w, { verb: 'retarget', path: md, args: { commentId: c.id, target: { kind: 'image', region: region2 } }, fence: fenceFor(st) });
  // the contrast that pins the refusal: with no stored position and no copy fields the tie cannot be settled on
  // either read path
  const disk2 = readSidecar(r.storePath);
  delete disk2.comments[0].anchorAt;
  for (const k of ['ordinal', 'copies', 'section']) delete disk2.comments[0][k];
  delete disk2.comments[0].target.src;
  fs.writeFileSync(r.storePath, JSON.stringify(disk2, null, 2) + '\n');
  st = status(w, md);
  assert.deepEqual(st.placed, {}, 'a refused tie has no entry');
  assert.equal(st.derivedSrcs[c.id], undefined);
  assert.deepEqual(st.embeddedHashes, {});
  assert.match(st.derivedSrcReasons[c.id], /anchor-ambiguous/);
  assert.equal(st.store.comments[0].target.src, undefined);
  refused(w, { verb: 'retarget', path: md, args: { commentId: c.id, target: { kind: 'image', region: region2 } }, fence: fenceFor(st) }, 'anchor-ambiguous');
  refused(w, { verb: 'retarget', path: md, args: { commentId: c.id, target: { kind: 'image', region: region2, src: 'fig.png' } }, fence: fenceFor(st) }, 'anchor-ambiguous');
});

// ── (4) the refresh is bounded ──────────────────────────────────────

// A comment in the host's own shape, for a sidecar built by hand.
function hostComment(text, quote, at, i) {
  return { id: `1700000000000-${at}`, author: 'you', ts: 1700000000000 + i, anchor: engine.makeAnchor(text, at, at + quote.length, ANCHOR_CTX_CAP), anchorAt: at, body: `Note ${i}.`, replies: [], resolved: false };
}

test('a write on a near-cap file of repeated text with 300 cap-width tied comments completes well inside the kernel\'s deadline, with every position kept; after a direct edit above, still', () => {
  const w = world();
  const para = `${'Every paragraph of this file is the same, and each one holds the marker sentence. '.repeat(11)}Here is the marker phrase to comment on. ${'The rest of the paragraph is the same too. '.repeat(3)}`.trim();
  const body = `${para}\n\n`;
  const count = Math.floor((2 * 1024 * 1024 - 200) / body.length);
  const text = `# Big\n\n${body.repeat(count)}`;
  assert.ok(text.length < 2 * 1024 * 1024 && text.length > 1.8 * 1024 * 1024, `the fixture: ${text.length} bytes, under the viewer's cap`);
  const big = path.join(w.docs, 'big.md');
  fs.writeFileSync(big, text);
  const r = comment(w, big, { note: 'Overall.' });
  const first = nth(text, MARKER, 0);
  const u = uniqueAnchor(text, first, first + MARKER.length);
  assert.equal(u.unique, false, 'the fixture: every copy shares more than the cap on both sides');
  const positions = [];
  for (let k = 0; k < 300; k++) positions.push(first + k * body.length);
  const disk = readSidecar(r.storePath);
  disk.comments.push(...positions.map((at, i) => hostComment(text, MARKER, at, i)));
  assert.deepEqual(disk.comments[1].anchor, u.anchor, 'the anchor the host stores at the cap');
  fs.writeFileSync(r.storePath, JSON.stringify(disk, null, 2) + '\n');
  let st = status(w, big);
  const res = ok(w, { verb: 'resolve', path: big, args: { commentId: disk.comments[1].id, on: true }, fence: fenceFor(st) });
  // The pre-review host ran two engine scans per comment here, each scoring every copy against 960
  // characters of context, and was killed by the kernel at 10 s from about 290 comments on.
  assert.ok(res.ms < 5000, `the resolve took ${res.ms} ms`);
  assert.deepEqual(res.json.store.comments.slice(1).map((c) => c.anchorAt), positions, 'every position sits on its copy and is kept');
  assert.equal(res.json.store.comments[1].resolved, true);
  // a direct write above every copy: no record says how far the copies moved, every position stands
  fs.writeFileSync(big, text.replace('# Big\n', '# Big\nA line nobody recorded.\n'));
  st = status(w, big);
  const res2 = ok(w, { verb: 'resolve', path: big, args: { commentId: disk.comments[1].id, on: false }, fence: fenceFor(st) });
  assert.ok(res2.ms < 5000, `the resolve took ${res2.ms} ms`);
  assert.deepEqual(res2.json.store.comments.slice(1).map((c) => c.anchorAt), positions, 'kept');
});

test('the engine scans only for anchors that sit in whole nowhere, under a per-write budget: past it the rest keep their position and stderr says so, while one that fits is placed', () => {
  const w = world();
  const line = '2026-01-01T00:00:00Z INFO retry on timeout, attempt 1 of 3\n';
  const count = Math.floor((2 * 1024 * 1024 - 100) / line.length);
  const text = `HEADER retry on timeout, attempt 1 of 3\n${line.repeat(count)}`;
  const log = path.join(w.docs, 'run.log');
  fs.writeFileSync(log, text);
  const r = comment(w, log, { note: 'Overall.' });
  const quote = 'retry on timeout, attempt 1 of 3';
  const occurrences = count + 1;
  const dear = { quote, prefix: 'x'.repeat(ANCHOR_CTX_CAP), suffix: 'y'.repeat(ANCHOR_CTX_CAP) };   // sits in whole nowhere; the engine would score every occurrence
  assert.ok(2 * occurrences * (2 * ANCHOR_CTX_CAP + 1) > REFRESH_SCAN_BUDGET, 'the fixture: one such scan alone is past the budget');
  const cheap = { quote, prefix: 'HEADER ', suffix: 'NOPE' };   // sits in whole nowhere too; the header's copy outscores the rest by its prefix
  const disk = readSidecar(r.storePath);
  for (let i = 0; i < 12; i++) disk.comments.push({ id: `1700000000000-${i}`, author: 'you', ts: 1700000000000 + i, anchor: dear, anchorAt: 100 + i, body: `Dear ${i}.`, replies: [], resolved: false });
  disk.comments.push({ id: '1700000000000-cheap', author: 'you', ts: 1700000000100, anchor: cheap, anchorAt: 500, body: 'Cheap.', replies: [], resolved: false });
  fs.writeFileSync(r.storePath, JSON.stringify(disk, null, 2) + '\n');
  const st = status(w, log);
  const res = ok(w, { verb: 'resolve', path: log, args: { commentId: disk.comments[0].id, on: true }, fence: fenceFor(st) });
  assert.ok(res.ms < 5000, `the resolve took ${res.ms} ms`);
  const after = res.json.store.comments;
  assert.deepEqual(after.slice(1, 13).map((c) => c.anchorAt), disk.comments.slice(1, 13).map((c) => c.anchorAt), 'past the budget: kept');
  assert.equal(after[13].anchorAt, 7, 'within it: placed by the engine at the header\'s copy');
  assert.match(res.stderr, /12 comment\(s\) whose anchor sits in whole nowhere in the text kept their stored position/);
  assert.equal(readSidecar(r.storePath).comments[13].anchorAt, 7);
});

// ── (5) the reply's measure counts the bytes the refresh adds ────────

test('a sidecar of CLI-written comments within the slack of the reply cap refuses a write too-large once the refresh\'s anchorAt fields are counted, instead of landing a reply the kernel discards', () => {
  assert.ok(hostSource.includes('const REPLY_SLACK = 64 * 1024;'), 'the slack this test is sized against');
  const SLACK = 64 * 1024;
  const w = world();
  const text = `# Small\n\n${'Filler so the passage sits past offset one hundred. '.repeat(3)}The passage to comment on sits here once.\n`;
  const quote = 'The passage to comment on';
  const at = text.indexOf(quote);
  assert.ok(at >= 100 && text.indexOf(quote, at + 1) === -1, 'the fixture: one occurrence, a three-digit offset');
  const small = path.join(w.docs, 'small.md');
  fs.writeFileSync(small, text);
  const r = comment(w, small, { note: 'Overall.' });
  const N = 5000;
  const cli = (i, body) => ({ id: `1700000000000-${at}-${i}`, author: 'web', authorId: SID, ts: 1700000000000 + i, anchor: engine.makeAnchor(text, at, at + quote.length), body, replies: [], resolved: false });
  const disk = readSidecar(r.storePath);
  const F0 = 2500;
  for (let i = 0; i < N; i++) disk.comments.push(cli(i, 'a'.repeat(F0)));
  fs.writeFileSync(r.storePath, JSON.stringify(disk, null, 2) + '\n');
  // size the store so a status reply sits just under the line the check measures against: a byte of
  // body is a byte of reply, so the first measure gives the body every comment needs, the second the pad
  const line = REPLY_MAX_BYTES - SLACK - 4096;
  let s1 = host(w, { verb: 'status', path: small, args: {} });
  assert.equal(s1.json && s1.json.ok, true, s1.stderr);
  const F = F0 + Math.floor((line - Buffer.byteLength(s1.stdout, 'utf8')) / N);
  assert.ok(F > 0, `the fixture: ${F} bytes of body per comment`);
  for (let i = 1; i <= N; i++) disk.comments[i].body = 'a'.repeat(F);
  fs.writeFileSync(r.storePath, JSON.stringify(disk, null, 2) + '\n');
  s1 = host(w, { verb: 'status', path: small, args: {} });
  const pad = line - Buffer.byteLength(s1.stdout, 'utf8');
  assert.ok(pad >= 0 && pad < N, `the fixture: ${pad} bytes to pad`);
  disk.comments[1].body = 'a'.repeat(F) + 'b'.repeat(pad);
  fs.writeFileSync(r.storePath, JSON.stringify(disk, null, 2) + '\n');
  s1 = host(w, { verb: 'status', path: small, args: {} });
  const bytes = Buffer.byteLength(s1.stdout, 'utf8');
  assert.ok(Math.abs(bytes - line) <= 64, `the fixture: a status reply of ${bytes} bytes, ${line - bytes} under the check's line`);
  assert.ok(bytes + N * 15 > REPLY_MAX_BYTES, 'the fixture: the anchorAt fields the refresh adds carry the reply past the cap');
  assert.equal(s1.json.store.comments.filter((c) => 'anchorAt' in c).length, 0, 'the CLI comments carry no position (and the whole-file one never does)');
  const before = fs.readFileSync(r.storePath);
  const rr = refused(w, { verb: 'reply', path: small, args: { commentId: disk.comments[1].id, note: 'Noted.' }, fence: fenceFor(s1.json) }, 'too-large');
  assert.ok(rr.error.includes('nothing was changed'), rr.error);
  assert.deepEqual(fs.readFileSync(r.storePath), before, 'byte-identical: the write did not land');
});

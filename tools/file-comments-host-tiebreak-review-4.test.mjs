// The recurring-passage tie-break, the review's fourth round (2026-09-11; plans/file-review.md, decision 51). Four
// findings on the host, each pinned here against the real host as a child process or its exported readers:
//   * the third round's `position` for a stored position the QUOTE ALONE sits at pre-empted the fields for a bare
//     occurrence of the quoted words: a raw insertion above of exactly the gap between a passing mention and the
//     commented copy landed the stale position on the mention, the host read the mention as the passage, forwarded no
//     verdict, and the panel painted a guess with its cue where the ordinal (the count unchanged) had confirmed the
//     copy. quoteSitsAt asks for one side of the anchor's context whole beside the quote now: a passage still at its
//     position with its context edited keeps a side, a bare mention has none, and the rules run as for any stale
//     position. The cost, stated in the record and pinned here: a raw edit of BOTH sides around the quoted words is a
//     position no rule takes, and the copies whole elsewhere fall to the rules;
//   * the note on `position` said the panel paints the nearest whole copy as a guess for a passage whose context was
//     edited; with exactly two copies the one still whole is the engine's one best hit and the panel paints it plainly,
//     on the copy the person never commented, as it has since the anchors follow-on. The host answers the position to
//     its own readers and forwards no verdict either way; the note says so now, and this module holds the host's side;
//   * the ordinal yields where the stored heading path names other copies and not its own (the third round's rule, now
//     recorded in decision 51): a raw write that swaps two heading texts leaves the ordinal's copy under another path
//     than the stored one, and the tie is a guess, not the ordinal's copy confirmed;
//   * the reply's map (placedFor, carriedTo) walked every pending change for every whole copy of every tied comment,
//     uncharged, on every verb including a status: a sidecar of ten thousand pending insertions and twenty stale tied
//     comments on a file of REFRESH_COPIES_MAX one-character copies held a status 18 s, past the kernel's 10 s
//     deadline, after which the file's comments could not be opened at all. The walk reads the changes off one sorted
//     index (boundsIndex, two binary searches per copy) and is charged to the budget, and a walk that does not fit is
//     nothing known.
// Hermetic, the tiebreak module's way: the synthetic notes-api world under a scratch directory, the host as a child
// process, the real vendored track-edit CLI where the session did something, a raw write where the person did.
// Synthetic fixtures only.
// Run: node --test tools/file-comments-host-tiebreak-review-4.test.mjs
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

import { locateStored, fullMatches, movedCopy, sectionAt, ANCHOR_CTX_CAP, REFRESH_SCAN_BUDGET } from './file-comments-host.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const HOST = path.join(REPO, 'tools', 'file-comments-host.mjs');
const VENDOR = path.join(REPO, 'vendor', 'track-changents');
const engine = createRequire(import.meta.url)(path.join(VENDOR, 'engine.js'));
const { fingerprintOf } = await import(path.join(VENDOR, 'store-io.mjs'));
const hostSrc = fs.readFileSync(HOST, 'utf8');

const SID = '11111111-2222-3333-4444-555555555555';
const COPIES_MAX = 65_536;
assert.ok(hostSrc.includes('const REFRESH_COPIES_MAX = 65_536;'), 'the fixture: the copies cap this module counts against');

let SCRATCH;
before(() => { SCRATCH = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-fc-tiebreak-r4-')); });
after(() => { try { fs.rmSync(SCRATCH, { recursive: true, force: true }); } catch { /* ignore */ } });

// -- the world --
const PARA = ('The quick brown fox jumps over the lazy dog. '.repeat(12)
  + 'Here is the marker phrase to comment on. '
  + 'Pack my box with five dozen liquor jugs. '.repeat(12)).trim();
const MARKER = 'the marker phrase';
assert.ok(PARA.indexOf(MARKER) > ANCHOR_CTX_CAP && PARA.length - PARA.indexOf(MARKER) - MARKER.length > ANCHOR_CTX_CAP,
  'the fixture: the phrase sits more than the cap from both ends of its paragraph');
const OPENING = '# Report\n\nA short opening line that occurs once.\n\n';
const MENTION = 'A bare mention of the marker phrase in passing.\n\n';
// two copies under two headings, with a passing mention of the quoted words between them
const TWO = `${OPENING}## Alpha\n\n${PARA}\n\n${MENTION}## Bravo\n\n${PARA}\n`;
// two copies under one heading: the state the note on `position` describes
const PAIR = `${OPENING}## Findings\n\n${PARA}\n\n${PARA}\n`;

let worlds = 0;
function world(files) {
  const home = path.join(SCRATCH, `w${++worlds}`, 'home');
  const root = path.join(home, 'notes-api');
  fs.mkdirSync(path.join(root, '.git'), { recursive: true });
  fs.mkdirSync(path.join(root, 'docs'));
  const out = { home, root, docs: path.join(root, 'docs') };
  for (const [name, text] of Object.entries(files)) {
    out[name] = path.join(out.docs, `${name}.md`);
    fs.writeFileSync(out[name], text);
  }
  return out;
}
function env(w, extra) {
  const e = { ...process.env, FILE_COMMENTS_HOME: w.home, ...(extra || {}) };
  delete e.TRACKCHANGES_ROOT;
  if (!extra || !('ROMP_SID' in extra)) { delete e.ROMP_SID; delete e.ROMP_SESSION_NAME; }
  return e;
}
function host(w, req) {
  const t0 = performance.now();
  const r = spawnSync(process.execPath, [HOST], { input: JSON.stringify(req), encoding: 'utf8', env: env(w), maxBuffer: 256 * 1024 * 1024 });
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

// -- the quote at a stale position: a side of its context, or a bare mention --

test('a raw insertion above of exactly the gap between a passing mention of the quoted words and the commented copy lands the stale position on the mention: the fields decide (the ordinal, the count unchanged), confirmed, and the reply carries it (before the fix: the mention was the passage, no verdict, and the panel painted a guess); one character shorter, the same', () => {
  const w = world({ two: TWO });
  const m = fromBrowser(TWO, MARKER, 2);
  const r = comment(w, w.two, { anchor: m.anchor, note: 'Say it once.', hintOffset: m.hintOffset });
  const c = readSidecar(r.storePath).comments[0];
  assert.deepEqual(copyFields(c), [2, 2, 'Report > Bravo']);
  assert.equal(c.anchorAt, m.idx);
  const bare = nth(TWO, MARKER, 1);
  const gap = m.idx - bare;
  const line = `${'x'.repeat(gap - 1)}\n`;
  const now = line + TWO;
  rawWrite(w.two, now);
  const whole = fullMatches(now, c.anchor, 10).hits;
  assert.deepEqual(whole, [nth(now, MARKER, 0), nth(now, MARKER, 2)], 'the fixture: both copies whole, moved alike');
  assert.equal(nth(now, MARKER, 1), c.anchorAt, 'the fixture: the stale position is on the mention');
  assert.ok(!now.startsWith(c.anchor.prefix, c.anchorAt - c.anchor.prefix.length) && !now.startsWith(c.anchor.suffix, c.anchorAt + MARKER.length), 'the fixture: neither side of the context sits beside the mention');
  assert.deepEqual(locateStored(now, c, true), span(whole[1], true, 'ordinal'), 'the ordinal\'s copy, confirmed: the mention is no passage');
  assert.deepEqual(locateStored(now, c, true, fresh()), span(whole[1], true, 'ordinal'), 'under a budget the same');
  const st = status(w, w.two);
  assert.equal(st.store.comments[0].anchorAt, m.idx, 'a read rewrites nothing');
  assert.deepEqual(st.placed, { [c.id]: { at: whole[1], confirmed: true, by: 'ordinal' } }, 'the reply carries the confirmed copy (before the fix: no entry)');
  // the control: an insertion one character shorter leaves the position one short of the mention, and the fields
  // decided already; the coincidence alone flipped the verdict before the fix
  rawWrite(w.two, line.slice(1) + TWO);
  assert.deepEqual(status(w, w.two).placed, { [c.id]: { at: whole[1] - 1, confirmed: true, by: 'ordinal' } });
  // the engine's own view of the mention: a bare occurrence scores under a whole copy, and its pick from the stale
  // position is a whole copy, never the mention
  assert.notEqual(engine.locateAnchor(now, c.anchor, c.anchorAt).from, c.anchorAt);
});

test('quoteSitsAt asks for one side of the context: a raw edit of the suffix (the prefix whole) or of the prefix at the same length (the suffix whole) keeps the position; a side the anchor lacks counts for nothing; a raw edit of both sides around the quoted words is the stated cost, a position no rule takes, and the copies whole elsewhere fall to the rules', () => {
  const m = fromBrowser(TWO, MARKER, 2);
  const c = { anchor: engine.makeAnchor(TWO, m.idx, m.idx + MARKER.length, ANCHOR_CTX_CAP), anchorAt: m.idx, ordinal: 2, copies: 2, section: 'Report > Bravo' };
  assert.deepEqual(fullMatches(TWO, c.anchor, 10).hits, [nth(TWO, MARKER, 0), m.idx], 'the fixture: the anchor at the cap ties on the two copies, not the mention');
  // the suffix edited: the prefix still sits before the quote
  const suffixEdited = TWO.slice(0, m.idx) + TWO.slice(m.idx).replace('Pack my box', 'Pack my crate');
  assert.deepEqual(fullMatches(suffixEdited, c.anchor, 10).hits, [nth(TWO, MARKER, 0)], 'the fixture: one copy whole');
  assert.deepEqual(locateStored(suffixEdited, c, true), span(m.idx, true, 'position'), 'the passage, not the other copy');
  // the prefix edited at the same length: the suffix still sits after the quote
  const before = TWO.slice(0, m.idx);
  const lastDog = before.lastIndexOf('dog.');
  const prefixEdited = `${before.slice(0, lastDog)}cat.${before.slice(lastDog + 4)}${TWO.slice(m.idx)}`;
  assert.ok(prefixEdited.startsWith(MARKER, m.idx) && prefixEdited.startsWith(c.anchor.suffix, m.idx + MARKER.length), 'the fixture: the quote and its suffix at the position');
  assert.deepEqual(locateStored(prefixEdited, c, true), span(m.idx, true, 'position'));
  // both sides edited: the quote alone sits at the position, and the copy still whole is the engine's one best hit
  const bothEdited = prefixEdited.slice(0, m.idx) + prefixEdited.slice(m.idx).replace('Pack my box', 'Pack my crate');
  assert.ok(bothEdited.startsWith(MARKER, m.idx), 'the fixture: the quote alone at the position');
  const other = nth(TWO, MARKER, 0);
  assert.deepEqual(locateStored(bothEdited, c, true), span(other, true, 'whole'), 'the cost the record states: the other copy, as after any edit that leaves one copy whole');
  assert.deepEqual(locateStored(bothEdited, { ...c, anchorAt: 3 }, true), span(other, true, 'whole'), 'the same as from a position holding nothing');
  // a side the anchor lacks: a quote at the very start of the file has no prefix, and the empty prefix vouches for nothing
  const flat = `${MARKER} opens the file.\n\n${PARA}\n\n${PARA}\n`;
  const edge = { anchor: { quote: MARKER, prefix: '', suffix: ' opens the file.' }, anchorAt: nth(flat, MARKER, 1) };
  assert.equal(fullMatches(flat, edge.anchor, 10).hits.length, 1, 'the fixture: the anchor sits whole at the file\'s start only');
  assert.ok(flat.startsWith(MARKER, edge.anchorAt) && !flat.startsWith(edge.anchor.suffix, edge.anchorAt + MARKER.length), 'the fixture: the quote alone at the stored position');
  assert.deepEqual(locateStored(flat, edge, true), { from: 0, to: MARKER.length, confirmed: true, by: 'whole' }, 'the empty side counts for nothing: the one whole copy');
  // and a malformed position sits nowhere, as before
  for (const at of [-5, TWO.length + 1, 1.5]) assert.notEqual(locateStored(suffixEdited, { ...c, anchorAt: at }, true).by, 'position', `a position of ${at} sits nowhere`);
});

// -- two copies under one heading: the host's side of the note on `position` --

test('two copies under one heading and a tracked edit inside the first copy\'s suffix: the reply keeps the position on the first copy, forwards no verdict, and every reader of the stored anchor answers the position; the engine\'s one best hit is the second copy, the paint the note on `position` now describes for exactly two copies', () => {
  const w = world({ pair: PAIR });
  const m = fromBrowser(PAIR, MARKER, 0);
  const r = comment(w, w.pair, { anchor: m.anchor, note: 'Say it once.', hintOffset: m.hintOffset });
  const c = readSidecar(r.storePath).comments[0];
  assert.deepEqual(copyFields(c), [1, 2, 'Report > Findings']);
  assert.equal(c.anchorAt, m.idx);
  // the session edits the first copy's suffix; the heading makes the --old unique
  const head = `## Findings\n\n${PARA.slice(0, PARA.indexOf('Pack my box') + 'Pack my box'.length)}`;
  assert.equal(PAIR.indexOf(head), PAIR.lastIndexOf(head), 'the fixture: unique --old');
  cliOk(w, 'edit', ['--file', w.pair, '--old', head, '--new', head.replace('Pack my box', 'Pack my crate')]);
  const edited = fs.readFileSync(w.pair, 'utf8');
  assert.equal(nth(edited, MARKER, 0), m.idx, 'the fixture: the quote did not move');
  const whole = fullMatches(edited, c.anchor, 10).hits;
  assert.deepEqual(whole, [nth(edited, MARKER, 1)], 'the fixture: the second copy alone is whole');
  // the recorded window: no verdict, and the position stands
  let st = status(w, w.pair);
  assert.deepEqual(st.placed, {}, 'no verdict: the position names the passage');
  assert.equal(st.store.comments[0].anchorAt, m.idx);
  // the write: the refresh keeps the position (the recorded change vouches for the quote where it is), the fields stand
  const r2 = ok(w, { verb: 'reply', path: w.pair, args: { commentId: c.id, note: 'Still once.' }, fence: fenceFor(st) }).json;
  const after = readSidecar(r2.storePath).comments[0];
  assert.equal(after.anchorAt, m.idx);
  assert.deepEqual(copyFields(after), [1, 2, 'Report > Findings']);
  assert.deepEqual(r2.placed, {});
  st = status(w, w.pair);
  assert.deepEqual(st.placed, {});
  assert.deepEqual(locateStored(edited, after, true), span(m.idx, true, 'position'), 'the reader: the first copy');
  assert.deepEqual(locateStored(edited, after, true, fresh()), span(m.idx, true, 'position'), 'under a budget the same');
  // the panel's engine, with the stored position as its hint: one best hit, the second copy; the note says the panel
  // paints it plainly for exactly two copies (a tie, and so a guess with its cue, needs two copies still whole)
  assert.equal(engine.locateAnchor(edited, c.anchor, m.idx).from, whole[0], 'the engine\'s one best hit: the other copy');
  assert.equal(engine.locateAnchor(edited, c.anchor, 0).from, engine.locateAnchor(edited, c.anchor, edited.length).from, 'and no tie among best hits');
  // the note itself
  const note = hostSrc.slice(hostSrc.indexOf('// Place a STORED passage comment'), hostSrc.indexOf('export function locateStored('));
  assert.ok(note.includes('with exactly two copies the') && note.includes('paints it plainly, on the copy the person never'), 'the note states the two-copy paint');
  assert.ok(!note.includes('paints the nearest whole copy as a guess, the cue\n//     from before the tie-break;'), 'and no longer says a guess for every count');
});

// -- the ordinal against the section: the yield, recorded --

test('a raw write that swaps two heading texts leaves the ordinal\'s copy under another path than the stored one while the count is unchanged: the two fields disagree and the tie is a guess on the nearest copy (decision 51 records the yield); the same write with the headings left alone confirms the ordinal\'s copy', () => {
  const w = world({ two: TWO });
  const m = fromBrowser(TWO, MARKER, 2);
  const r = comment(w, w.two, { anchor: m.anchor, note: 'Say it once.', hintOffset: m.hintOffset });
  const c = readSidecar(r.storePath).comments[0];
  assert.deepEqual(copyFields(c), [2, 2, 'Report > Bravo']);
  const line = 'A new line above.\n';
  const swapped = line + TWO.replace('## Alpha', '## TMP').replace('## Bravo', '## Alpha').replace('## TMP', '## Bravo');
  const whole = fullMatches(swapped, c.anchor, 10).hits;
  assert.equal(whole.length, 2, 'the fixture: the count is unchanged');
  assert.deepEqual(whole.map((h) => sectionAt(swapped, h, true)), ['Report > Bravo', 'Report > Alpha'], 'the fixture: the stored path names the first copy now, and the ordinal\'s copy is under the other');
  assert.ok(!swapped.startsWith(MARKER, c.anchorAt), 'the fixture: the stale position holds no quote');
  rawWrite(w.two, swapped);
  const nearest = engine.locateAnchor(swapped, c.anchor, c.anchorAt).from;
  assert.deepEqual(status(w, w.two).placed, { [c.id]: { at: nearest, confirmed: false, by: 'nearest' } }, 'a guess');
  assert.deepEqual(locateStored(swapped, c, true), span(nearest, false, 'nearest'));
  const kept = line + TWO;
  rawWrite(w.two, kept);
  assert.deepEqual(status(w, w.two).placed, { [c.id]: { at: nth(kept, MARKER, 2), confirmed: true, by: 'ordinal' } }, 'the headings left alone: the ordinal\'s copy, confirmed');
});

// -- the walk over the copies the recorded changes can have carried a position to --

// A stale tied comment on the one-character passage of the repeated-line file, its position on the newline (no copy,
// no quote), the fields as a stale count and the empty path: the state that runs the tie rules and then the walk.
function staleComment(i) {
  return { id: `c-${i}`, author: 'web', ts: 1700000000000 + i, anchor: { quote: 'x', prefix: '', suffix: '' }, anchorAt: 1, ordinal: 7, copies: COPIES_MAX, section: '', body: `Note ${i}.`, replies: [], resolved: false };
}
// A pending insertion of one character every fourth offset, as the sidecar records it (store-io's shape), with the
// fingerprint of the text as written so every change is on record (TEXT_AS_WRITTEN).
function pendingInsertion(text, k) {
  const from = 4 * k;
  return { id: `op-${k}`, author: 'web', ts: 1700000000000 + k, kind: 'insert', from, newText: 'x', oldText: '', anchor: { quote: 'x', prefix: text.slice(Math.max(0, from - 24), from), suffix: text.slice(from + 1, from + 25) } };
}
function seed(w, file, text, N, B) {
  const r = comment(w, file, { note: 'Overall.' });
  const disk = readSidecar(r.storePath);
  for (let k = 0; k < B; k++) disk.suggestions.push(pendingInsertion(text, k));
  for (let i = 0; i < N; i++) disk.comments.push(staleComment(i));
  disk.fingerprint = fingerprintOf(text);
  fs.writeFileSync(r.storePath, JSON.stringify(disk));
  return r.storePath;
}

test('a status on a file of REFRESH_COPIES_MAX one-character copies with ten thousand pending insertions on record and twenty stale tied comments answers well inside the kernel\'s deadline (18 s before the fix, and the kernel killed the host), and so does a write on the same sidecar and a status with two thousand such comments; the changes carry every stale position to one copy other than the verdict\'s, so no verdict is forwarded, and with no pending change every verdict is', () => {
  const text = 'x\n'.repeat(COPIES_MAX);
  const w = world({});
  const rep = path.join(w.docs, 'rep.md');
  fs.writeFileSync(rep, text);
  seed(w, rep, text, 20, 10000);
  const st = host(w, { verb: 'status', path: rep, args: {} });
  assert.equal(st.code, 0, st.stderr);
  assert.ok(st.json && st.json.ok, st.stdout.slice(0, 200));
  assert.ok(st.ms < 4000, `the status took ${st.ms} ms`);
  assert.equal(st.json.store.suggestions.length, 10000, 'the fixture: every pending change survived the load');
  assert.deepEqual(st.json.placed, {}, 'the recorded insertions carry the stale position to the copy after the first one, not to the guess (the earlier of the two copies beside the newline), so the verdict is dropped for the next write to settle');
  const res = host(w, { verb: 'resolve', path: rep, args: { commentId: 'c-7', on: true }, fence: fenceFor(st.json) });
  assert.equal(res.code, 0, res.stderr);
  assert.ok(res.json && res.json.ok, res.stdout.slice(0, 200));
  assert.ok(res.ms < 6000, `the resolve took ${res.ms} ms`);
  assert.equal(res.json.store.comments[8].resolved, true);
  // two thousand such comments, the same changes
  const w2 = world({});
  const rep2 = path.join(w2.docs, 'rep.md');
  fs.writeFileSync(rep2, text);
  seed(w2, rep2, text, 2000, 10000);
  const st2 = host(w2, { verb: 'status', path: rep2, args: {} });
  assert.equal(st2.code, 0, st2.stderr);
  assert.ok(st2.json && st2.json.ok, st2.stdout.slice(0, 200));
  assert.ok(st2.ms < 6000, `the status took ${st2.ms} ms`);
  // no pending change: the changes carry the position nowhere but where it is, and every verdict is forwarded, as
  // before; the stored count equals the count now, so the verdict is the ordinal's copy (the seventh), confirmed
  const w3 = world({});
  const rep3 = path.join(w3.docs, 'rep.md');
  fs.writeFileSync(rep3, text);
  seed(w3, rep3, text, 20, 0);
  const st3 = host(w3, { verb: 'status', path: rep3, args: {} });
  assert.equal(st3.code, 0, st3.stderr);
  assert.ok(st3.ms < 4000, `the status took ${st3.ms} ms`);
  assert.equal(Object.keys(st3.json.placed).length, 20);
  for (let i = 0; i < 20; i++) assert.deepEqual(st3.json.placed[`c-${i}`], { at: 12, confirmed: true, by: 'ordinal' }, `comment ${i}: the seventh copy, confirmed and forwarded`);
  assert.deepEqual(locateStored(text, staleComment(0), true), { from: 12, to: 13, confirmed: true, by: 'ordinal' }, 'the verdict the ten thousand insertions had dropped: they carry the position to the copy at 2, not to the seventh');
});

test('movedCopy reads the changes off one sorted index and charges the budget a compare per change to build it and a compare per copy inside the changes\' window per call; a budget the walk does not fit answers undefined, nothing known; the index is built once per bounds list; the one reachable copy is the same the walk of every change found', () => {
  const hits = Array.from({ length: COPIES_MAX }, (_, i) => 2 * i);   // the whole copies of 'x' in 'x\n' repeated
  const B = 10000;
  const boundsOf = () => Array.from({ length: B }, (_, k) => ({ end: 4 * k + 1, lo: 0, hi: 1 }));   // shiftBounds' rows for pendingInsertion
  // the walk of every change per copy, as before the fix, for the answer
  const linear = (cands, at, bounds) => {
    const out = [];
    for (const p of cands) {
      let lo = 0; let hi = 0;
      for (const b of bounds) if (b.end <= p) { lo += b.lo; hi += b.hi; }
      const d = p - at;
      if (d >= lo && d <= hi) out.push(p);
    }
    return out;
  };
  const bounds = boundsOf();
  assert.deepEqual(linear(hits, 1, bounds), [2], 'the fixture: the changes carry the position on the newline to the copy after it and to no other');
  // the window: the sums reach 10000 at most, never below 0, so the copies looked at are those within [1, 10001]: 5000
  const window = hits.filter((p) => p >= 1 && p <= 1 + B).length;
  assert.equal(window, 5000);
  const budget = fresh();
  assert.equal(movedCopy(hits, 1, bounds, undefined, budget), 2, 'the one copy');
  assert.equal(REFRESH_SCAN_BUDGET - budget.left, B + window, 'a compare per change for the index, a compare per copy in the window');
  assert.equal(movedCopy(hits, 1, bounds, undefined, budget), 2, 'again, the same list');
  assert.equal(REFRESH_SCAN_BUDGET - budget.left, B + 2 * window, 'the index is memoized on the list: the window alone');
  // a fresh list is indexed afresh; a budget short of the index, or of the window, answers nothing known
  assert.equal(movedCopy(hits, 1, boundsOf(), undefined, { left: B - 1, skipped: 0, unscanned: 0 }), undefined, 'short of the index');
  const tight = { left: B + window - 1, skipped: 0, unscanned: 0 };
  assert.equal(movedCopy(hits, 1, boundsOf(), undefined, tight), undefined, 'short of the window');
  assert.equal(tight.left, window - 1, 'the index was charged before the window was refused');
  const exact = { left: B + window, skipped: 0, unscanned: 0 };
  assert.equal(movedCopy(hits, 1, boundsOf(), undefined, exact), 2, 'exactly enough');
  assert.equal(exact.left, 0);
  // no pending change: an empty index, and the window is the position itself
  const none = fresh();
  assert.equal(movedCopy(hits, 1, [], undefined, none), null, 'no copy at the position: none');
  assert.equal(none.left, REFRESH_SCAN_BUDGET, 'nothing to look at, nothing charged');
  assert.equal(movedCopy(hits, 2, [], undefined, none), 2, 'the copy at the position itself');
  assert.equal(REFRESH_SCAN_BUDGET - none.left, 1);
  // the quote's other occurrences are asked only when no whole copy is reachable, and walked the same way
  assert.equal(movedCopy(hits, 1, [{ end: 0, lo: -1, hi: 0 }], [1, 3], fresh()), 0, 'a change before the position that can have carried it back by one: the whole copy at 0 is reachable, and the occurrences are not asked');
  assert.equal(movedCopy(hits, 3, [{ end: 0, lo: 0, hi: 4 }], [3, 5], fresh()), null, 'the whole copies at 4 and 6 are reachable: several, none');
  const few = [100, 200];   // whole copies, and the quote's other occurrences between them
  assert.equal(movedCopy(few, 140, [{ end: 0, lo: 0, hi: 15 }], [150, 160], fresh()), 150, 'no whole copy within the bounds: the one occurrence there');
  assert.equal(movedCopy(few, 140, [{ end: 0, lo: 0, hi: 25 }], [150, 160], fresh()), null, 'two occurrences within the bounds: none');
  assert.equal(movedCopy(few, 140, [{ end: 0, lo: 0, hi: 15 }], undefined, fresh()), null, 'and with no occurrences to ask: none');
  const spareBudget = { left: 1, skipped: 0, unscanned: 0 };   // the index (one change), no room for the occurrences' window
  assert.equal(movedCopy(few, 140, [{ end: 0, lo: 0, hi: 15 }], [150, 160], spareBudget), undefined, 'the occurrences\' walk is charged too, and refused short of the budget');
  // the shift the changes can have given a copy is the running sum of every change ending at or before it, not each
  // change alone: two changes, the first taking, the second giving, and the copies past both within their sum
  const mixed = [{ end: 10, lo: -4, hi: 0 }, { end: 20, lo: 0, hi: 6 }];
  assert.deepEqual(linear(hits, 101, mixed), [98, 100, 102, 104, 106], 'the fixture: five copies within [-4, +6] of the position');
  assert.equal(movedCopy(hits, 101, mixed, undefined, fresh()), null, 'several reachable: none is the one');
  assert.equal(movedCopy(hits, 101, [{ end: 10, lo: -4, hi: 0 }, { end: 200, lo: 0, hi: 6 }], undefined, fresh()), null, 'the second change ends past the copies, so only the first counts for them: 98 and 100 within [-4, 0], several');
  assert.equal(movedCopy(hits, 101, [{ end: 10, lo: -2, hi: 0 }, { end: 200, lo: 0, hi: 6 }], undefined, fresh()), 100, 'within [-2, 0]: the one copy at 100');
});

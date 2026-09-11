// The recurring-passage tie-break (2026-09-11; plans/file-review.md, The contract, the anchors follow-on note and
// decision 51). The user saw a comment on a passage that recurs painted as a guess: the anchor matched several copies
// and the stored position named none of them, because the file had changed under the panel in a way the host never
// recorded (a raw write, an editor save), so the copy nearest the stale position was highlighted, dashed, with the
// "passage recurs" tag. Three romp-only fields written beside `anchorAt` let the host tell the copy without a
// position: `ordinal` (the 1-based index of the copy among the whole anchor's matches at the moment of the write),
// `copies` (how many matches there were then; the ordinal means nothing without it, so the pair is written together)
// and `section` (the heading path above the passage, the nearest preceding markdown headings from the top level
// down joined with " > "; empty for a file without headings or a non-markdown file). All three are written at
// creation and refreshed on every host write for a comment whose position names its copy, the way `anchorAt` is.
// When the host must choose among several copies and the position names none (locateStored, which every reader of a
// stored anchor in this script goes through, and the `placed` map every reply carries for the panel), the rules run
// in order: the count of copies unchanged since the fields were written, the ordinal's copy, confirmed; else exactly
// one copy under the stored section, confirmed; else the nearest copy to the position, a guess, as before (and a tie
// with no position at all still refuses, as before: the panel paints the first copy as a guess itself). Hermetic, the file-comments-host-anchors.test.mjs way: the synthetic notes-api world under a
// scratch directory, the host as a child process, the REAL vendored CLIs where the session did something, a raw write
// where the person or an editor did. Synthetic fixtures only.
// Run: node --test tools/file-comments-host-tiebreak.test.mjs
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

import { sectionAt, locateStored, commentsApartFromAnchorAt, isMarkdownPath, ANCHOR_CTX_CAP } from './file-comments-host.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const HOST = path.join(REPO, 'tools', 'file-comments-host.mjs');
const VENDOR = path.join(REPO, 'vendor', 'track-changents');
const engine = createRequire(import.meta.url)(path.join(VENDOR, 'engine.js'));

const SID = '11111111-2222-3333-4444-555555555555';

let SCRATCH;
before(() => { SCRATCH = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-fc-tiebreak-')); });
after(() => { try { fs.rmSync(SCRATCH, { recursive: true, force: true }); } catch { /* ignore */ } });

// ── the world ───────────────────────────────────────────────────────
// One paragraph over a thousand characters long, three times, each under its own heading: the marker phrase in its
// middle has identical surroundings for more than ANCHOR_CTX_CAP characters on both sides of every copy, so every
// anchor on it ties at the cap, and only the heading above each copy tells them apart to a reader.
const PARA = ('The quick brown fox jumps over the lazy dog. '.repeat(12)
  + 'Here is the marker phrase to comment on. '
  + 'Pack my box with five dozen liquor jugs. '.repeat(12)).trim();
const MARKER = 'the marker phrase';
assert.ok(PARA.indexOf(MARKER) > ANCHOR_CTX_CAP && PARA.length - PARA.indexOf(MARKER) - MARKER.length > ANCHOR_CTX_CAP,
  'the fixture: the phrase sits more than the cap from both ends of its paragraph');
const OPENING = '# Report\n\nA short opening line that occurs once.\n\n';
const TIED = `${OPENING}## First pass\n\n${PARA}\n\n## Second pass\n\n${PARA}\n\n## Third pass\n\n${PARA}\n`;
const UNIQUE = 'opening line that occurs once';
// a markdown file with no headings at all
const PLAIN = `Alpha line.\n\nThe unique passage here.\n\nOmega line.\n`;

let worlds = 0;
function world() {
  const home = path.join(SCRATCH, `w${++worlds}`, 'home');
  const root = path.join(home, 'notes-api');
  fs.mkdirSync(path.join(root, '.git'), { recursive: true });
  fs.mkdirSync(path.join(root, 'docs'));
  fs.writeFileSync(path.join(root, 'docs', 'tied.md'), TIED);
  fs.writeFileSync(path.join(root, 'docs', 'tied.txt'), TIED);
  fs.writeFileSync(path.join(root, 'docs', 'plain.md'), PLAIN);
  return { home, root, tied: path.join(root, 'docs', 'tied.md'), txt: path.join(root, 'docs', 'tied.txt'), plain: path.join(root, 'docs', 'plain.md') };
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
const PASSAGE_KEYS = ['id', 'author', 'ts', 'anchor', 'anchorAt', 'ordinal', 'copies', 'section', 'body', 'replies', 'resolved'];

// ── the section helper ──────────────────────────────────────────────

test('sectionAt: the heading path from the top level down, a lower level closed by a later heading of a higher one, a heading line under itself; not a heading: a line inside a fenced block, a hash line inside a front-matter block (closed by --- or ..., and opening no section for the passage after it), a hash with no space; closing hashes and extra spaces stripped; empty for no headings and for a non-markdown file', () => {
  const text = [
    '---', 'title: Front matter', '# not a heading: inside the front matter', '---', '',
    'After the front matter, before any heading.', '',
    '# Alpha  ', '', 'Under alpha.', '', '## Beta ##', '', 'Under beta.', '', '### Gamma', '', 'Under gamma.', '',
    '```', '# a comment in code', '```', '', 'Still under gamma.', '', '##   Delta   with   spaces', '', 'Under delta.', '',
    '#hashtag is not a heading', '', 'Still under delta.', '', '# Omega', '', 'Under omega.', '',
  ].join('\n');
  const at = (needle) => { const i = text.indexOf(needle); assert.ok(i >= 0, needle); return i; };
  assert.equal(sectionAt(text, at('title: Front'), true), '', 'inside the front matter: nothing above');
  assert.equal(sectionAt(text, at('# not a heading'), true), '', 'the hash line inside the front matter is not a heading, not even under itself');
  const closingRule = text.indexOf('\n---\n') + 1;
  assert.equal(text.slice(closingRule, closingRule + 3), '---', 'the fixture: the closing rule of the front matter');
  assert.equal(sectionAt(text, closingRule, true), '', 'the closing rule of the front matter: still nothing above');
  assert.equal(sectionAt(text, at('After the front matter'), true), '', 'a passage after the front matter and before the first heading: the hash line inside the block opened no section');
  assert.equal(sectionAt(text, at('Under alpha.'), true), 'Alpha');
  assert.equal(sectionAt(text, at('Under beta.'), true), 'Alpha > Beta', 'the closing hashes stripped');
  assert.equal(sectionAt(text, at('Under gamma.'), true), 'Alpha > Beta > Gamma');
  assert.equal(sectionAt(text, at('Still under gamma.'), true), 'Alpha > Beta > Gamma', 'the fenced line is code, not a heading');
  assert.equal(sectionAt(text, at('Under delta.'), true), 'Alpha > Delta with spaces', 'a level 2 heading closes Beta and Gamma; spaces collapsed');
  assert.equal(sectionAt(text, at('Still under delta.'), true), 'Alpha > Delta with spaces', '#hashtag is not a heading');
  assert.equal(sectionAt(text, at('Under omega.'), true), 'Omega', 'a new top level closes everything');
  assert.equal(sectionAt(text, at('# Omega') + 2, true), 'Omega', 'a passage on the heading line itself is under that heading');
  assert.equal(sectionAt(text, at('# Alpha'), true), 'Alpha', 'the heading from its first character');
  assert.equal(sectionAt(text, 0, true), '', 'the top of the file');
  const dots = '---\ntitle: Dots\n# not a heading: inside a block the document-end marker closes\n...\n\nAfter a front matter closed by three dots.\n\n# Alpha\n\nUnder alpha.\n';
  assert.equal(sectionAt(dots, dots.indexOf('After a front matter'), true), '', 'a front matter closed by the YAML document-end marker is skipped the same way');
  assert.equal(sectionAt(dots, dots.indexOf('Under alpha.'), true), 'Alpha', 'and the headings after it are read');
  assert.equal(sectionAt(PLAIN, PLAIN.indexOf('unique'), true), '', 'a markdown file with no headings');
  assert.equal(sectionAt(text, at('Under gamma.'), false), '', 'a non-markdown file: no heading path however the text reads');
  assert.equal(sectionAt(TIED, nth(TIED, MARKER, 1), true), 'Report > Second pass');
  assert.equal(sectionAt(TIED, nth(TIED, MARKER, 2), true), 'Report > Third pass');
  for (const [p, md] of [['docs/report.md', true], ['/x/y/NOTES.MD', true], ['a.markdown', true], ['docs/tied.txt', false], ['README', false], ['a.md.bak', false], ['', false], [null, false]]) {
    assert.equal(isMarkdownPath(p), md, `isMarkdownPath(${JSON.stringify(p)})`);
  }
});

// ── creation ────────────────────────────────────────────────────────

test('a comment on the second of three tied copies is written with ordinal 2 of 3 copies and its heading path, after anchorAt and before the body; one on a unique passage with 1 of 1; the reply carries the comment as written', () => {
  const w = world();
  const m = fromBrowser(TIED, MARKER, 1);
  const r = comment(w, w.tied, { anchor: m.anchor, note: 'Say it once.', hintOffset: m.hintOffset });
  const c = readSidecar(r.storePath).comments[0];
  assert.deepEqual(Object.keys(c), PASSAGE_KEYS);
  assert.equal(c.anchorAt, m.idx);
  assert.deepEqual(copyFields(c), [2, 3, 'Report > Second pass']);
  assert.deepEqual(r.store.comments[0], c, 'the reply carries the stored comment as written');
  assert.equal(engine.locateAnchor(TIED, c.anchor, 0).from, nth(TIED, MARKER, 0), 'the fixture: the anchor alone ties at the cap');
  // the first and the third copies, in the same file
  const first = fromBrowser(TIED, MARKER, 0);
  const third = fromBrowser(TIED, MARKER, 2);
  const c1 = readSidecar(comment(w, w.tied, { anchor: first.anchor, note: 'First.', hintOffset: first.hintOffset }).storePath).comments[1];
  const c3 = readSidecar(comment(w, w.tied, { anchor: third.anchor, note: 'Third.', hintOffset: third.hintOffset }).storePath).comments[2];
  assert.deepEqual(copyFields(c1), [1, 3, 'Report > First pass']);
  assert.deepEqual(copyFields(c3), [3, 3, 'Report > Third pass']);
  // a unique passage: 1 of 1, under the top heading alone
  const u = fromBrowser(TIED, UNIQUE, 0);
  const cu = readSidecar(comment(w, w.tied, { anchor: u.anchor, note: 'Once.', hintOffset: u.hintOffset }).storePath).comments[3];
  assert.deepEqual(Object.keys(cu), PASSAGE_KEYS);
  assert.deepEqual(copyFields(cu), [1, 1, 'Report']);
  // a comment about a change, and a whole-file comment, gain none of the three (no anchor)
  const rf = comment(w, w.tied, { note: 'On the whole file.' });
  const cf = readSidecar(rf.storePath).comments[4];
  assert.deepEqual(Object.keys(cf), ['id', 'author', 'ts', 'body', 'replies', 'resolved']);
});

test('a non-markdown file: ordinal and copies are written and the section is empty; a markdown file with no headings has an empty section too', () => {
  const w = world();
  const m = fromBrowser(TIED, MARKER, 2);
  const c = readSidecar(comment(w, w.txt, { anchor: m.anchor, note: 'In a text file.', hintOffset: m.hintOffset }).storePath).comments[0];
  assert.deepEqual(Object.keys(c), PASSAGE_KEYS, 'the section is written, empty, so a reader can tell "no headings" from "an older host"');
  assert.deepEqual(copyFields(c), [3, 3, '']);
  const u = fromBrowser(PLAIN, 'unique passage', 0);
  const cp = readSidecar(comment(w, w.plain, { anchor: u.anchor, note: 'No headings here.', hintOffset: u.hintOffset }).storePath).comments[0];
  assert.deepEqual(copyFields(cp), [1, 1, '']);
});

// ── the refresh ─────────────────────────────────────────────────────

test('the refresh: a tracked insertion above leaves the three fields stale until the next host write, which moves anchorAt and keeps 2 of 3 under the same heading; a heading renamed above refreshes the section; a comment track-comment wrote gains all three with its position', () => {
  const w = world();
  const m = fromBrowser(TIED, MARKER, 1);
  const r = comment(w, w.tied, { anchor: m.anchor, note: 'Say it once.', hintOffset: m.hintOffset });
  const c = readSidecar(r.storePath).comments[0];
  // the session inserts a line above through the CLI: a sidecar write the host did not make writes the object back whole
  const line = 'Added above, on record.\n';
  cliOk(w, 'edit', ['--file', w.tied, '--old', '# Report\n', '--new', `# Report\n${line}`]);
  const stale = readSidecar(r.storePath).comments[0];
  assert.equal(stale.anchorAt, m.idx, 'the CLI wrote the object back as it was');
  assert.deepEqual(copyFields(stale), [2, 3, 'Report > Second pass']);
  let st = status(w, w.tied);
  assert.equal(st.store.comments[0].anchorAt, m.idx, 'a read never rewrites the sidecar');
  // the next host write refreshes the position, and the copy fields with it
  const r2 = ok(w, { verb: 'reply', path: w.tied, args: { commentId: c.id, note: 'Still once.' }, fence: fenceFor(st) });
  const after = readSidecar(r2.storePath).comments[0];
  assert.equal(after.anchorAt, m.idx + line.length, 'followed through the recorded insertion');
  assert.deepEqual(copyFields(after), [2, 3, 'Report > Second pass'], 'the same copy of the same count, under the same heading');
  assert.deepEqual(Object.keys(after), PASSAGE_KEYS, 'refreshed in place: no key moves');
  // the session renames the heading above the copy: the section follows on the next write
  cliOk(w, 'edit', ['--file', w.tied, '--old', '## Second pass', '--new', '## Second look']);
  assert.equal(readSidecar(r2.storePath).comments[0].section, 'Report > Second pass', 'stale until a host write');
  st = status(w, w.tied);
  const r3 = ok(w, { verb: 'resolve', path: w.tied, args: { commentId: c.id, on: true }, fence: fenceFor(st) });
  const renamed = readSidecar(r3.storePath).comments[0];
  assert.deepEqual(copyFields(renamed), [2, 3, 'Report > Second look']);
  assert.equal(renamed.anchorAt, m.idx + line.length, 'the rename is the same length: the position stands');
  assert.equal(r3.store.comments[0].section, 'Report > Second look', 'the reply carries the refreshed fields');
  // a comment the session wrote with track-comment (no anchorAt, no copy fields) on the unique opening line
  cliOk(w, 'comment', ['--file', w.tied, '--anchor', UNIQUE, '--note', 'Once, says the session.']);
  const cli = readSidecar(r3.storePath).comments[1];
  assert.deepEqual(Object.keys(cli).filter((k) => ['anchorAt', 'ordinal', 'copies', 'section'].includes(k)), [], 'the CLI writes the contract\'s shape alone');
  st = status(w, w.tied);
  const r4 = ok(w, { verb: 'resolve', path: w.tied, args: { commentId: c.id, on: false }, fence: fenceFor(st) });
  const gained = readSidecar(r4.storePath).comments[1];
  const text = fs.readFileSync(w.tied, 'utf8');
  assert.equal(gained.anchorAt, text.indexOf(UNIQUE), 'placed: a unique anchor with no position');
  assert.deepEqual(copyFields(gained), [1, 1, 'Report']);
  assert.equal(gained.author, 'web');
  assert.equal(gained.authorId, SID);
});

test('a decision after the fields were added or refreshed by its stage lands: the untouched check carves the copy fields out with anchorAt, and nothing else', () => {
  const w = world();
  const m = fromBrowser(TIED, MARKER, 1);
  const r = comment(w, w.tied, { anchor: m.anchor, note: 'Say it once.', hintOffset: m.hintOffset });
  // an older host's sidecar: the comment carries anchorAt and none of the three; a tracked insertion above is pending
  const sc = readSidecar(r.storePath);
  for (const k of ['ordinal', 'copies', 'section']) delete sc.comments[0][k];
  fs.writeFileSync(r.storePath, JSON.stringify(sc, null, 2));
  const line = 'Added above, on record.\n';
  cliOk(w, 'edit', ['--file', w.tied, '--old', '# Report\n', '--new', `# Report\n${line}`]);
  let st = status(w, w.tied);
  assert.equal(st.hunks.length, 1);
  assert.equal('ordinal' in st.store.comments[0], false, 'the fixture: the fields are absent');
  // the accept's stage refreshes the position and adds the three fields; the check between the stage and the rename
  // must not read that as a comment the decision changed
  const r2 = ok(w, { verb: 'accept', path: w.tied, args: { ids: [st.hunks[0].id] }, fence: fenceFor(st) });
  assert.deepEqual(r2.hunks, [], 'the change is settled');
  const c = readSidecar(r2.storePath).comments[0];
  assert.equal(c.anchorAt, m.idx + line.length);
  assert.deepEqual(copyFields(c), [2, 3, 'Report > Second pass'], 'added by the stage');
  // the carve-out itself: the four position fields read the same added, moved or removed; anything else does not
  const a = { id: 'c1', author: 'you', ts: 1, anchor: { quote: 'q', prefix: 'p', suffix: 's' }, anchorAt: 40, ordinal: 2, copies: 3, section: 'A > B', body: 'Say it.', replies: [], resolved: false };
  const apart = commentsApartFromAnchorAt;
  const { anchorAt: _at, ordinal: _o, copies: _n, section: _s, ...bare } = a;   // eslint-disable-line no-unused-vars
  assert.equal(apart([a]), apart([bare]), 'removed');
  assert.equal(apart([a]), apart([{ ...a, anchorAt: 57, ordinal: 1, copies: 2, section: 'A' }]), 'moved');
  assert.equal(apart([bare]), apart([{ ...bare, section: '' }]), 'added');
  assert.notEqual(apart([a]), apart([{ ...a, body: 'Say it!' }]), 'the body');
  assert.notEqual(apart([a]), apart([{ ...a, sent: true }]), 'a field added');
});

// ── the tie-break ───────────────────────────────────────────────────

// A raw write: the person's editor, or a write outside the tracked path. Nothing records it, so the position stored
// with the comment names no copy afterwards and the recorded changes vouch for nothing (refreshAnchorAts stands down).
function rawWrite(file, text) { fs.writeFileSync(file, text); }

test('the tie-break on a reply after a raw write, in order: the count unchanged takes the ordinal\'s copy, confirmed; the count changed and one copy under the stored heading takes it, confirmed; two copies under it fall back to the nearest, a guess; a position naming a copy has no entry; a read rewrites nothing', () => {
  const w = world();
  const m = fromBrowser(TIED, MARKER, 1);
  const r = comment(w, w.tied, { anchor: m.anchor, note: 'Say it once.', hintOffset: m.hintOffset });
  const c = readSidecar(r.storePath).comments[0];
  const bytes = fs.readFileSync(r.storePath);
  // (a) a paragraph inserted above by a raw write, longer than half the gap between copies: nearest-wins from the
  // stale position would pick the FIRST copy; the count is still three, so the ordinal names the second
  const gap = nth(TIED, MARKER, 1) - nth(TIED, MARKER, 0);
  const para = `${'The person added this paragraph in an editor. '.repeat(14).trim()}\n\n`;
  assert.ok(para.length > gap / 2 && para.length < gap, 'the fixture: longer than half the gap, shorter than the gap');
  const above = OPENING + para + TIED.slice(OPENING.length);
  rawWrite(w.tied, above);
  assert.equal(engine.locateAnchor(above, c.anchor, c.anchorAt).from, nth(above, MARKER, 0), 'the fixture: nearest-wins from the stale position picks the first copy');
  let st = status(w, w.tied);
  assert.equal(st.store.comments[0].anchorAt, m.idx, 'the stored position is stale and stands');
  assert.deepEqual(st.placed, { [c.id]: { at: nth(above, MARKER, 1), confirmed: true, by: 'ordinal' } }, 'the second copy, confirmed by the ordinal');
  assert.ok(fs.readFileSync(r.storePath).equals(bytes), 'a read never rewrites the sidecar');
  // (b) a fourth copy added above under a heading of its own (with a line of its own, so no copy lands on the stale
  // position by the shift): the count changed, and the stored heading path names exactly one copy, the one that
  // was the second
  const fourth = OPENING + `## Zeroth pass\n\nA line the person added before the copy.\n\n${PARA}\n\n` + TIED.slice(OPENING.length);
  assert.equal(engine.locateAnchor(fourth, c.anchor, 0).from === c.anchorAt || fourth.startsWith(c.anchor.quote, c.anchorAt), false, 'the fixture: the stale position names no copy');
  rawWrite(w.tied, fourth);
  st = status(w, w.tied);
  assert.deepEqual(st.placed, { [c.id]: { at: nth(fourth, MARKER, 2), confirmed: true, by: 'section' } }, 'the copy under Second pass, now the third, confirmed by its heading path');
  // (c) a second copy under the SAME heading and a short line above: the count changed, two copies lie under the
  // stored path, and the nearest to the stale position is what is left, a guess
  const line = 'One short line above.\n\n';
  const twin = OPENING + line + TIED.slice(OPENING.length, TIED.indexOf('## Third pass')) + `${PARA}\n\n` + TIED.slice(TIED.indexOf('## Third pass'));
  rawWrite(w.tied, twin);
  assert.equal(sectionAt(twin, nth(twin, MARKER, 1), true), 'Report > Second pass');
  assert.equal(sectionAt(twin, nth(twin, MARKER, 2), true), 'Report > Second pass', 'the fixture: two copies under the stored heading');
  st = status(w, w.tied);
  assert.deepEqual(st.placed, { [c.id]: { at: nth(twin, MARKER, 1), confirmed: false, by: 'nearest' } }, 'nearest to the stale position; right here, but a guess');
  // (d) the file as written: the position names its copy, and the reply has no entry for the comment
  rawWrite(w.tied, TIED);
  st = status(w, w.tied);
  assert.deepEqual(st.placed, {}, 'no tie to break');
  assert.ok(fs.readFileSync(r.storePath).equals(bytes), 'still not rewritten');
});

test('without the fields (an older host\'s comment) the fallback is the nearest copy, a guess; with no position at all the tie is refused as before, so no entry; a comment whose anchor is unique, or whose position names a copy, has no entry; the ordinal is trusted only with its count and within it', () => {
  const w = world();
  const m = fromBrowser(TIED, MARKER, 1);
  const r = comment(w, w.tied, { anchor: m.anchor, note: 'Say it once.', hintOffset: m.hintOffset });
  const u = fromBrowser(TIED, UNIQUE, 0);
  comment(w, w.tied, { anchor: u.anchor, note: 'Once.', hintOffset: u.hintOffset });
  const first = fromBrowser(TIED, MARKER, 0);
  comment(w, w.tied, { anchor: first.anchor, note: 'First.', hintOffset: first.hintOffset });
  const sc = readSidecar(r.storePath);
  const [c, cu, c1] = sc.comments;
  for (const k of ['ordinal', 'copies', 'section']) delete sc.comments[0][k];      // an older host's comment: a position, no copy fields
  const { anchorAt: _a, ordinal: _o, copies: _n, section: _s, ...shape } = c1;   // eslint-disable-line no-unused-vars
  sc.comments.push({ ...shape, id: 'cli-1', body: 'Which copy?' });   // track-comment's shape: no position and no copy fields
  sc.comments.push({ ...c, id: 'bad-1', ordinal: 5, copies: 3, body: 'An ordinal past its count.' });
  sc.comments.push({ ...c, id: 'bad-2', ordinal: 2, copies: '3', body: 'A count of the wrong shape.' });
  sc.comments.push({ ...c, id: 'bad-3', ordinal: 2, copies: 3, section: 7, body: 'A section of the wrong shape, with a good ordinal.' });
  fs.writeFileSync(r.storePath, JSON.stringify(sc, null, 2));
  const line = 'One short line above.\n\n';
  const moved = OPENING + line + TIED.slice(OPENING.length);
  rawWrite(w.tied, moved);
  const st = status(w, w.tied);
  const second = nth(moved, MARKER, 1);
  assert.deepEqual(st.placed, {
    [c.id]: { at: second, confirmed: false, by: 'nearest' },
    [c1.id]: { at: nth(moved, MARKER, 0), confirmed: true, by: 'ordinal' },
    'bad-1': { at: second, confirmed: false, by: 'nearest' },
    'bad-2': { at: second, confirmed: false, by: 'nearest' },
    'bad-3': { at: second, confirmed: true, by: 'ordinal' },
  }, 'the unique passage has no entry; the first copy\'s comment, with its fields, is confirmed; a malformed field claims nothing');
  assert.equal(cu.id in st.placed, false);
  assert.equal('cli-1' in st.placed, false, 'no position and no fields: the tie is refused, as locateExact refuses a hintless tie, and the panel paints the first copy as a guess itself');
});

test('locateStored, the one reader of a stored anchor: the position naming a copy, the one whole copy, the rules in order, the engine on an anchor whole nowhere, and the refusals; passageFigure and retarget go through it', () => {
  const m = nth(TIED, MARKER, 1);
  const anchor = engine.makeAnchor(TIED, m, m + MARKER.length, ANCHOR_CTX_CAP);
  const span = (at) => ({ from: at, to: at + MARKER.length });
  const stored = { anchor, anchorAt: m, ordinal: 2, copies: 3, section: 'Report > Second pass' };
  assert.deepEqual(locateStored(TIED, stored, true), { ...span(m), confirmed: true, by: 'position' }, 'the position names its copy');
  const line = 'One short line above.\n\n';
  const moved = OPENING + line + TIED.slice(OPENING.length);
  assert.deepEqual(locateStored(moved, stored, true), { ...span(m + line.length), confirmed: true, by: 'ordinal' });
  const fourth = OPENING + `## Zeroth pass\n\nA line the person added before the copy.\n\n${PARA}\n\n` + TIED.slice(OPENING.length);
  assert.deepEqual(locateStored(fourth, stored, true), { ...span(nth(fourth, MARKER, 2)), confirmed: true, by: 'section' });
  assert.deepEqual(locateStored(fourth, { ...stored, section: '' }, false), { ...span(nth(fourth, MARKER, 1)), confirmed: false, by: 'nearest' }, 'a non-markdown file: every copy is under the empty path, so the section rule never confirms');
  assert.deepEqual(locateStored(moved, { anchor, anchorAt: m }, true), { ...span(m + line.length), confirmed: false, by: 'nearest' });
  assert.deepEqual(locateStored(moved, { anchor }, true), { error: 'anchor-ambiguous' }, 'no position, no fields: refused, as before');
  assert.deepEqual(locateStored(moved, { anchor, ordinal: 2, copies: 3 }, true), { ...span(m + line.length), confirmed: true, by: 'ordinal' }, 'the fields settle a tie with no position too');
  // one whole copy: the other two copies' surroundings edited away leave the engine one best hit, whatever the position
  const others = TIED.replace('## First pass\n\n' + PARA, '## First pass\n\nGone.').replace('## Third pass\n\n' + PARA, '## Third pass\n\nGone too.');
  assert.deepEqual(locateStored(others, { anchor, anchorAt: 0 }, true), { ...span(nth(others, MARKER, 0)), confirmed: true, by: 'whole' });
  // whole nowhere: the quote stands with its context edited at the one copy left; the engine places it by its scoring
  const edited = others.replace('Here is the marker phrase', 'Here, then, is the marker phrase');
  const at = edited.indexOf(MARKER);
  assert.deepEqual(locateStored(edited, { anchor, anchorAt: 0 }, true), { ...span(at), confirmed: true, by: 'engine' });
  assert.deepEqual(locateStored(TIED.replace(/the marker phrase/g, 'the marked phrase'), stored, true), { error: 'anchor-not-found' });
  // the host's own readers of a stored anchor go through it
  const src = fs.readFileSync(HOST, 'utf8');
  const fn = (name) => { const a = src.indexOf(`function ${name}(`); assert.ok(a >= 0, name); return src.slice(a, src.indexOf('\n}\n', a)); };
  assert.ok(fn('passageFigure').includes('const loc = locateStored(text, { ...c, anchor }, ctx.markdown);'), 'the figure a passage embeds is read at the copy the tie-break names');
  assert.ok(fn('doRetarget').includes('const loc = locateStored(text, { ...c, anchor: validateAnchor(c.anchor) }, ctx.markdown);'), 'and so is a re-place');
  assert.ok(!/locateExact\(text, [a-zA-Z.()]*anchor[a-zA-Z.()]*, hintOf\(c\)\)/.test(src), 'no reader locates a stored anchor by nearest-wins alone any more');
});

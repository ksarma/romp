// The tie-break's review (2026-09-11) against the host, tools/file-comments-host.mjs: each finding on the host reproduced
// against the real host as a child process, the file-comments-host-tiebreak.test.mjs way (the synthetic notes-api world
// under a scratch directory, a raw write where the person or an editor did something), and closed here.
//   * The refresh judged whether the file is markdown from the sidecar JSON's own `path` field while creation and every
//     read judged from the file's name; a sidecar whose `path` was stale or absent had `section` overwritten with '' on
//     the next host write, and a read then took the '' for the heading path of the copies above every heading and
//     confirmed one of those. Now every stamp and every read judge from the file's name (the judgment stamped on the
//     store at load, MARKDOWN_FILE, for the refresh).
//   * headings() read no heading on a CRLF file (a CR at the end of every line failed the ATX regex), missed the first
//     line of a BOM file (a heading, a front-matter rule, a fence) behind the U+FEFF this script keeps, and took any
//     leading `---` for an open front-matter block, so a notes file opening with a thematic break had every heading
//     swallowed. Now the lines are read as the viewer renders them, and a front-matter block is one by the viewer's own
//     test (ui/webview/md-config.ts: closed, not blank after the opener, a YAML mapping).
//   * locateStored's nearest fallback ran the engine's whole scan per comment, uncharged and unmemoized, on every reply:
//     a status on a file of repeated text with 400 stale comments took 13 s, past the kernel's 10 s deadline, so the
//     file's comments could not be opened. Now the nearest copy is read off the whole matches already enumerated, and a
//     tie past REFRESH_COPIES_MAX is charged to the budget like the engine's placing of a nowhere anchor.
//   * The stamping pass skipped a comment's copy fields past the budget silently, on every write, the same comments
//     each time. Now the comments without the fields are stamped first and stderr says how many were left, once per write.
//   * `section` had no bound, so nine CLI-written comments under a heading line of a megabyte made every write refuse
//     `too-large`. Now a heading's text is capped (SECTION_HEADING_CAP) at the stamp and at the read alike.
//   * The engine-placed stamp (1 of 1 where the anchor sits in whole nowhere) and `placed` on a write verb's reply were
//     guarded by source pins alone; both are driven here.
// Synthetic fixtures only. Run: node --test tools/file-comments-host-tiebreak-review.test.mjs
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

import { sectionAt, locateStored, uniqueAnchor, fullMatches, SECTION_HEADING_CAP, ANCHOR_CTX_CAP, REFRESH_SCAN_BUDGET, REFRESH_PASS_DIVISOR, TEXT_MAX_BYTES } from './file-comments-host.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const HOST = path.join(REPO, 'tools', 'file-comments-host.mjs');
const VENDOR = path.join(REPO, 'vendor', 'track-changents');
const engine = createRequire(import.meta.url)(path.join(VENDOR, 'engine.js'));

let SCRATCH;
before(() => { SCRATCH = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-fc-tiebreak-review-')); });
after(() => { try { fs.rmSync(SCRATCH, { recursive: true, force: true }); } catch { /* ignore */ } });

// ── the world ───────────────────────────────────────────────────────
// The tie-break test's fixture: one paragraph over a thousand characters long, three times, each under its own heading,
// with the marker phrase more than ANCHOR_CTX_CAP from both ends of every copy, so every anchor on it ties at the cap.
const PARA = ('The quick brown fox jumps over the lazy dog. '.repeat(12)
  + 'Here is the marker phrase to comment on. '
  + 'Pack my box with five dozen liquor jugs. '.repeat(12)).trim();
const MARKER = 'the marker phrase';
const OPENING = '# Report\n\nA short opening line that occurs once.\n\n';
const TIED = `${OPENING}## First pass\n\n${PARA}\n\n## Second pass\n\n${PARA}\n\n## Third pass\n\n${PARA}\n`;
const BOM = '﻿';
const crlf = (t) => t.replace(/\n/g, '\r\n');

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
function env(w) {
  const e = { ...process.env, FILE_COMMENTS_HOME: w.home };
  delete e.TRACKCHANGES_ROOT;
  delete e.ROMP_SID;
  delete e.ROMP_SESSION_NAME;
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
function status(w, file) { return ok(w, { verb: 'status', path: file, args: {} }).json; }
function fenceFor(st) { return { storeMtimeNs: st.storeMtimeNs == null ? '' : st.storeMtimeNs }; }
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
// A comment in this script's own shape, for a sidecar built by hand: the anchor at the cap, or at `ctx` characters.
function hostComment(text, quote, at, i, ctx, fields) {
  return { id: `1700000000000-${at}-${i}`, author: 'you', ts: 1700000000000 + i, anchor: engine.makeAnchor(text, at, at + quote.length, ctx == null ? ANCHOR_CTX_CAP : ctx), anchorAt: at, ...(fields || {}), body: `Note ${i}.`, replies: [], resolved: false };
}
const copyFields = (c) => [c.ordinal, c.copies, c.section];
const PASSAGE_KEYS = ['id', 'author', 'ts', 'anchor', 'anchorAt', 'ordinal', 'copies', 'section', 'body', 'replies', 'resolved'];
// The stamping pass's stderr note and its count, and the position notes' counts (the anchors review's wording).
const UNSTAMPED = /file-comments-host: (\d+) comment\(s\) kept the copy fields they had, or none: counting the copies of their passage would scan past the refresh's budget for one write/g;
const unstampedNotes = (stderr) => [...stderr.matchAll(UNSTAMPED)].map((m) => Number(m[1]));
const keptNotes = (stderr) => [...stderr.matchAll(/file-comments-host: (\d+) comment\(s\) (?:whose anchor sits in whole nowhere in the text )?kept their stored position/g)].map((m) => Number(m[1]));
// A raw write: the person's editor, or a write outside the tracked path; nothing records it.
function rawWrite(file, text) { fs.writeFileSync(file, text); }

// ── the section helper reads the file as the viewer renders it ──────

test('sectionAt: a CRLF file\'s headings are read (the CR is not part of the line) and its front matter skipped; a BOM file\'s first line is read (a heading, a front-matter rule, a fence); the offsets count the text as it is', () => {
  assert.equal(sectionAt('# Title\r\n\r\nbody\r\n', 11, true), 'Title', 'a CRLF heading');
  const ab = '# A\r\n\r\n## B\r\n\r\nbody\r\n';
  assert.equal(sectionAt(ab, ab.indexOf('body'), true), 'A > B', 'a CRLF heading path');
  assert.equal(sectionAt(ab, ab.indexOf('## B'), true), 'A > B', 'a heading line under itself, from its first character');
  assert.equal(sectionAt(ab, ab.indexOf('## B') - 2, true), 'A', 'the offset of the CRLF pair before it is still under A');
  const fm = '---\r\ntitle: x\r\n# not a heading\r\n---\r\n\r\nbody\r\n';
  assert.equal(sectionAt(fm, fm.indexOf('body'), true), '', 'a CRLF front-matter block is skipped, its hash line no heading');
  assert.equal(sectionAt(crlf(TIED), nth(crlf(TIED), MARKER, 1), true), 'Report > Second pass', 'the tied fixture in CRLF reads as in LF');
  // BOM: the first line
  assert.equal(sectionAt(`${BOM}# Title\n\nbody\n`, 10, true), 'Title', 'a heading on the first line behind the BOM');
  assert.equal(sectionAt(`${BOM}# Report\n\n## Second\n\nbody\n`, 22, true), 'Report > Second', 'the top level is kept');
  assert.equal(sectionAt(`${BOM}${TIED}`, nth(`${BOM}${TIED}`, MARKER, 1), true), 'Report > Second pass', 'the tied fixture behind a BOM reads as without');
  const bfm = `${BOM}---\ntitle: x\n# yaml comment\n---\n\nbody\n`;
  assert.equal(sectionAt(bfm, bfm.indexOf('body'), true), '', 'a front-matter block behind the BOM is recognised, its comment line no heading');
  const bfence = `${BOM}\`\`\`\n# in code\n\`\`\`\n\nbody\n`;
  assert.equal(sectionAt(bfence, bfence.indexOf('body'), true), '', 'a fence opening on the first line behind the BOM is a fence');
  assert.equal(sectionAt(`${BOM}#hashtag\n\nbody\n`, 12, true), '', 'a hash run with no space is still no heading');
});

test('sectionAt: a file opening with a thematic break is not front matter (a blank line after the opener, prose between two rules, no closing rule), so its headings are read; a YAML mapping between two rules is front matter, closed by --- or ...; the same as the viewer\'s test', () => {
  const t1 = '---\n\n# Title\n\n## Part\n\nBody text here.\n';
  assert.equal(sectionAt(t1, t1.indexOf('Body'), true), 'Title > Part', 'a rule then a blank line is a break, not an opener (pandoc\'s rule)');
  const t2 = '---\n# Title\n\n## Part\n\nBody\n';
  assert.equal(sectionAt(t2, t2.indexOf('Body'), true), 'Title > Part', 'an opener never closed is a break');
  const t3 = '---\n\n# Title\n\nbody\n\n---\n\nmore\n';
  assert.equal(sectionAt(t3, t3.indexOf('more'), true), 'Title', 'a rule, a heading, a rule: the heading is read and the second rule closes nothing');
  const t4 = '---\nSome prose here.\n---\n\n# Title\n\nbody\n';
  assert.equal(sectionAt(t4, t4.indexOf('body'), true), 'Title', 'prose between two rules is not a YAML mapping');
  assert.equal(sectionAt(t4, t4.indexOf('Some'), true), '', 'and nothing is above the prose');
  const t5 = '---\ntitle: x\ntags:\n  - a\n# a comment\nkey two: "quoted"\n---\n\n# Title\n\nbody\n';
  assert.equal(sectionAt(t5, t5.indexOf('body'), true), 'Title', 'a YAML mapping between two rules is front matter, and the heading after it is read');
  assert.equal(sectionAt(t5, t5.indexOf('title:'), true), '', 'inside it, nothing above');
  assert.equal(sectionAt(t5, t5.indexOf('# a comment'), true), '', 'its comment line is no heading');
  const t6 = '---\ntitle: Dots\n# not a heading\n...\n\n# Alpha\n\nUnder alpha.\n';
  assert.equal(sectionAt(t6, t6.indexOf('Under'), true), 'Alpha', 'YAML\'s document-end marker still closes a block');
  assert.equal(sectionAt(t6, t6.indexOf('# not'), true), '', 'and the block\'s hash line is no heading');
  const t7 = '---\n---\n\n# Title\n\nbody\n';
  assert.equal(sectionAt(t7, t7.indexOf('body'), true), 'Title', 'an empty block is front matter, as the viewer folds it');
  assert.equal(sectionAt('---', 0, true), '', 'a file of one rule');
  assert.equal(sectionAt('---\n', 0, true), '', 'a file of one rule and a newline');
});

test('sectionAt: a heading\'s text is capped at SECTION_HEADING_CAP characters at the stamp and the read alike, by code point; a heading under the cap is whole', () => {
  const long = 'w'.repeat(1000);
  const big = `# ${long}\n\nbody\n\n## Sub\n\nmore\n`;
  assert.equal(sectionAt(big, big.indexOf('body'), true), 'w'.repeat(SECTION_HEADING_CAP));
  const words = `# ${'word '.repeat(300).trim()}\n\nbody\n`;
  assert.equal(sectionAt(words, words.indexOf('body'), true), 'word '.repeat(40).trim(), 'the whitespace the cut leaves at the end is dropped');
  assert.equal(sectionAt(big, big.indexOf('more'), true), `${'w'.repeat(SECTION_HEADING_CAP)} > Sub`, 'the path joins the capped text');
  const faces = `# ${'\u{1F600}'.repeat(300)}\n\nbody\n`;
  const capped = sectionAt(faces, faces.indexOf('body'), true);
  assert.equal(Array.from(capped).length, SECTION_HEADING_CAP, 'counted by code point');
  assert.ok(!/[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]/.test(capped), 'no lone surrogate at the cut');
  const under = `# ${'w'.repeat(SECTION_HEADING_CAP)}\n\nbody\n`;
  assert.equal(sectionAt(under, under.indexOf('body'), true), 'w'.repeat(SECTION_HEADING_CAP), 'at the cap: whole');
  assert.equal(SECTION_HEADING_CAP, 200);
});

// ── markdown by the file's name, never the sidecar's path field ─────

test('the refresh judges markdown-ness from the file, not the sidecar JSON\'s path field: with the field removed or naming a text file, a host write keeps the heading path, and a later tie is confirmed on the right copy; a text file\'s sidecar naming a markdown path still stamps no heading path', () => {
  const w = world();
  const m = fromBrowser(TIED, MARKER, 1);
  const r = comment(w, w.tied, { anchor: m.anchor, note: 'Say it once.', hintOffset: m.hintOffset });
  const c = readSidecar(r.storePath).comments[0];
  assert.deepEqual(copyFields(c), [2, 3, 'Report > Second pass']);
  // the sidecar's informational path removed (a foreign writer, a hand edit): the next host write refreshes the fields
  const sc = readSidecar(r.storePath);
  assert.equal(sc.path, 'docs/tied.md', 'the fixture: the field as seeded');
  delete sc.path;
  writeSidecar(r.storePath, sc);
  let st = status(w, w.tied);
  let res = ok(w, { verb: 'reply', path: w.tied, args: { commentId: c.id, note: 'Still.' }, fence: fenceFor(st) });
  let after = readSidecar(res.json.storePath).comments[0];
  assert.deepEqual(copyFields(after), [2, 3, 'Report > Second pass'], 'the heading path stands: the file is markdown by its name');
  assert.deepEqual(Object.keys(after), PASSAGE_KEYS);
  assert.equal('path' in readSidecar(res.json.storePath), false, 'the host does not restore the field: it is not the host\'s to judge by');
  // the field naming a text file
  const sc2 = readSidecar(r.storePath);
  sc2.path = 'docs/tied.txt';
  writeSidecar(r.storePath, sc2);
  st = status(w, w.tied);
  res = ok(w, { verb: 'resolve', path: w.tied, args: { commentId: c.id, on: true }, fence: fenceFor(st) });
  after = readSidecar(res.json.storePath).comments[0];
  assert.deepEqual(copyFields(after), [2, 3, 'Report > Second pass']);
  // a raw write puts a fourth copy above every heading: before the fix the stored '' matched that copy's heading path
  // alone and confirmed it by section; the stored path names the copy under Second pass, now the third
  const top = `${PARA}\n\n${TIED}`;
  rawWrite(w.tied, top);
  st = status(w, w.tied);
  assert.equal(sectionAt(top, nth(top, MARKER, 0), true), '', 'the fixture: the new copy sits above every heading');
  assert.deepEqual(st.placed, { [c.id]: { at: nth(top, MARKER, 2), confirmed: true, by: 'section' } }, 'the copy under the stored heading path, confirmed');
  // the other way: a text file's sidecar claiming a markdown path stamps '' still
  const mt = fromBrowser(TIED, MARKER, 1);
  const rt = comment(w, w.txt, { anchor: mt.anchor, note: 'In a text file.', hintOffset: mt.hintOffset });
  const ct = readSidecar(rt.storePath).comments[0];
  assert.deepEqual(copyFields(ct), [2, 3, '']);
  const sct = readSidecar(rt.storePath);
  sct.path = 'docs/tied.md';
  writeSidecar(rt.storePath, sct);
  st = status(w, w.txt);
  res = ok(w, { verb: 'reply', path: w.txt, args: { commentId: ct.id, note: 'Still text.' }, fence: fenceFor(st) });
  assert.deepEqual(copyFields(readSidecar(res.json.storePath).comments[0]), [2, 3, ''], 'a text file by its name: no heading path');
});

// ── CRLF and BOM files end to end ───────────────────────────────────

test('a CRLF markdown file: the comment is written with its heading path, and after a raw write that changed the count the one copy under it is confirmed by section; a BOM file keeps its top heading, and the section confirms whether the editor kept the BOM or dropped it', () => {
  const w = world();
  // CRLF
  const T = crlf(TIED);
  const cr = path.join(w.docs, 'tied-crlf.md');
  fs.writeFileSync(cr, T);
  const m = fromBrowser(T, MARKER, 1);
  const r = comment(w, cr, { anchor: m.anchor, note: 'On a CRLF file.', hintOffset: m.hintOffset });
  const c = readSidecar(r.storePath).comments[0];
  assert.deepEqual(copyFields(c), [2, 3, 'Report > Second pass'], 'the heading path of a CRLF file');
  assert.equal(c.anchorAt, m.idx);
  const fourthCR = crlf(`${OPENING}## Zeroth pass\n\nA line the person added before the copy.\n\n${PARA}\n\n${TIED.slice(OPENING.length)}`);
  rawWrite(cr, fourthCR);
  let st = status(w, cr);
  assert.deepEqual(st.placed, { [c.id]: { at: nth(fourthCR, MARKER, 2), confirmed: true, by: 'section' } }, 'the count changed: the copy under Second pass, confirmed by its heading path');
  // BOM: the browser's offsets are into the text without it (the fetch strips it); the host keeps it and maps the hint
  const bm = path.join(w.docs, 'tied-bom.md');
  fs.writeFileSync(bm, `${BOM}${TIED}`);
  const mb = fromBrowser(TIED, MARKER, 1);
  const rb = comment(w, bm, { anchor: mb.anchor, note: 'On a BOM file.', hintOffset: mb.hintOffset });
  const cb = readSidecar(rb.storePath).comments[0];
  assert.equal(rb.bom, true, 'the reply says the text keeps a BOM');
  assert.equal(cb.anchorAt, mb.idx + 1, 'the position is into this script\'s text, one past the view\'s');
  assert.deepEqual(copyFields(cb), [2, 3, 'Report > Second pass'], 'the top heading, on the first line behind the BOM, is in the path');
  const fourth = `${OPENING}## Zeroth pass\n\nA line the person added before the copy.\n\n${PARA}\n\n${TIED.slice(OPENING.length)}`;
  rawWrite(bm, fourth);   // the editor's save dropped the BOM
  st = status(w, bm);
  assert.equal(st.bom, false);
  assert.deepEqual(st.placed, { [cb.id]: { at: nth(fourth, MARKER, 2), confirmed: true, by: 'section' } }, 'the BOM gone: the stored path still names the copy');
  rawWrite(bm, `${BOM}${fourth}`);   // or kept it
  st = status(w, bm);
  assert.equal(st.bom, true);
  assert.deepEqual(st.placed, { [cb.id]: { at: nth(fourth, MARKER, 2) + 1, confirmed: true, by: 'section' } }, 'the BOM kept: the same copy, one offset on');
});

// ── the engine-placed stamp, and placed on a write's reply ──────────

test('a comment whose anchor sits in whole nowhere is placed by the engine and stamped 1 of 1 there on the next write, so when a raw write later restores whole copies around it the tie is a guess, never the old ordinal\'s copy confirmed', () => {
  const w = world();
  const m = fromBrowser(TIED, MARKER, 1);
  const r = comment(w, w.tied, { anchor: m.anchor, note: 'Say it once.', hintOffset: m.hintOffset });
  const c = readSidecar(r.storePath).comments[0];
  assert.deepEqual(copyFields(c), [2, 3, 'Report > Second pass']);
  // a raw write removes the other two copies, puts a line above, and edits the survivor's context
  const edited = `${OPENING}One short line above.\n\n${TIED.slice(OPENING.length)}`
    .replace(`## First pass\n\n${PARA}`, '## First pass\n\nGone.')
    .replace(`## Third pass\n\n${PARA}`, '## Third pass\n\nGone too.')
    .replace('Here is the marker phrase', 'Here, then, is the marker phrase');
  assert.equal(fullMatches(edited, c.anchor, 2).hits.length, 0, 'the fixture: the whole anchor sits nowhere');
  rawWrite(w.tied, edited);
  let st = status(w, w.tied);
  assert.deepEqual(st.placed, {}, 'the engine places it: no tie, no entry');
  const res = ok(w, { verb: 'reply', path: w.tied, args: { commentId: c.id, note: 'Still once.' }, fence: fenceFor(st) });
  const stamped = readSidecar(res.json.storePath).comments[0];
  assert.equal(stamped.anchorAt, edited.indexOf(MARKER), 'moved to the engine\'s one best hit');
  assert.deepEqual(copyFields(stamped), [1, 1, 'Report > Second pass'], 'stamped 1 of 1 where the engine placed it');
  // a raw write restores three whole copies under Zeroth, First and Third around the context-edited one
  const restored = `${OPENING}## Zeroth pass\n\n${PARA}\n\n## First pass\n\n${PARA}\n\n${edited.slice(edited.indexOf('## Second pass'), edited.indexOf('## Third pass'))}## Third pass\n\n${PARA}\n`;
  assert.equal(fullMatches(restored, c.anchor, 8).hits.length, 3, 'the fixture: three whole copies again, none of them the commented one');
  rawWrite(w.tied, restored);
  st = status(w, w.tied);
  const guess = engine.locateAnchor(restored, c.anchor, stamped.anchorAt).from;
  assert.deepEqual(st.placed, { [c.id]: { at: guess, confirmed: false, by: 'nearest' } }, 'a guess: the count changed from 1 and no whole copy lies under Second pass');
  assert.notEqual(st.placed[c.id].confirmed, true, 'never the second whole copy confirmed by an ordinal of 2 in 3');
});

test('every write\'s reply carries the placed map the status carries, so the panel, which takes each write\'s reply as its status, keeps a confirmed copy painted plainly', () => {
  const w = world();
  const m = fromBrowser(TIED, MARKER, 1);
  const r = comment(w, w.tied, { anchor: m.anchor, note: 'Say it once.', hintOffset: m.hintOffset });
  const c = readSidecar(r.storePath).comments[0];
  const gap = nth(TIED, MARKER, 1) - nth(TIED, MARKER, 0);
  const para = `${'The person added this paragraph in an editor. '.repeat(14).trim()}\n\n`;
  assert.ok(para.length > gap / 2 && para.length < gap, 'the fixture: longer than half the gap, shorter than the gap');
  rawWrite(w.tied, OPENING + para + TIED.slice(OPENING.length));
  let st = status(w, w.tied);
  const want = { [c.id]: { at: nth(OPENING + para + TIED.slice(OPENING.length), MARKER, 1), confirmed: true, by: 'ordinal' } };
  assert.deepEqual(st.placed, want, 'the fixture: confirmed by the ordinal on a status');
  const rep = ok(w, { verb: 'reply', path: w.tied, args: { commentId: c.id, note: 'Noted.' }, fence: fenceFor(st) }).json;
  assert.deepEqual(rep.placed, want, 'the reply verb\'s reply');
  st = status(w, w.tied);
  const res = ok(w, { verb: 'resolve', path: w.tied, args: { commentId: c.id, on: true }, fence: fenceFor(st) }).json;
  assert.deepEqual(res.placed, want, 'the resolve verb\'s reply');
  const cm = ok(w, { verb: 'comment', path: w.tied, args: { note: 'On the whole file.' }, fence: fenceFor(status(w, w.tied)) }).json;
  assert.deepEqual(cm.placed, want, 'the comment verb\'s reply');
});

// ── the nearest fallback costs no scan ──────────────────────────────

test('the nearest copy is read off the whole matches, the engine\'s own pick (nearest the position, the earlier of two at one distance); a tie past REFRESH_COPIES_MAX under a budget answers nothing', () => {
  const m = nth(TIED, MARKER, 1);
  const anchor = engine.makeAnchor(TIED, m, m + MARKER.length, ANCHOR_CTX_CAP);
  const moved = `${OPENING}One short line above.\n\n${TIED.slice(OPENING.length)}`;
  const copies = [0, 1, 2].map((k) => nth(moved, MARKER, k));
  const mid = Math.floor((copies[0] + copies[1]) / 2);
  for (const at of [0, 5, copies[0] - 1, copies[0] + 1, mid - 1, mid, mid + 1, copies[1] + 5, copies[2] + 40, moved.length]) {
    const loc = locateStored(moved, { anchor, anchorAt: at }, true);
    assert.equal(loc.by, 'nearest');
    assert.equal(loc.confirmed, false);
    assert.equal(loc.from, engine.locateAnchor(moved, anchor, at).from, `the engine's pick from ${at}`);
  }
  assert.equal((copies[0] + copies[1]) % 2 === 0 ? locateStored(moved, { anchor, anchorAt: mid }, true).from : copies[0], copies[0], 'at one distance from two copies: the earlier');
  // past the cap: a whole anchor at nearly every offset of a text of one character
  const flat = 'a'.repeat(100000);
  const cli = engine.makeAnchor(flat, 50000, 50001);
  const budget = { left: REFRESH_SCAN_BUDGET, skipped: 0, unscanned: 0 };
  assert.equal(locateStored(flat, { anchor: cli, anchorAt: 5 }, false, budget), null, 'nothing known, rather than the engine\'s scan of every occurrence');
  assert.ok(budget.left < REFRESH_SCAN_BUDGET, 'the classification was charged');
  const loc = locateStored(flat, { anchor: cli, anchorAt: 5 }, false);
  assert.deepEqual(loc, { from: engine.locateAnchor(flat, cli, 5).from, to: engine.locateAnchor(flat, cli, 5).from + 1, confirmed: false, by: 'nearest' }, 'without a budget (one comment: passageFigure, retarget) the engine answers');
});

test('a status on a file of repeated text with hundreds of stale tied comments answers well inside the kernel\'s deadline, with every guess on the copy nearest its position; on a text of one character the tie past the cap has no entry and the reply is as quick', () => {
  const w = world();
  // (a) a near-cap file of one paragraph repeated, 300 comments whose positions sit 7 characters into their copy
  const para = `${'Every paragraph of this file is the same, and each one holds the marker sentence. '.repeat(11)}Here is the marker phrase to comment on. ${'The rest of the paragraph is the same too. '.repeat(3)}`.trim();
  const body = `${para}\n\n`;
  const count = Math.floor((TEXT_MAX_BYTES - 200) / body.length);
  const text = `# Big\n\n${body.repeat(count)}`;
  assert.ok(text.length < TEXT_MAX_BYTES && text.length > 1.8 * 1024 * 1024, `the fixture: ${text.length} bytes`);
  const big = path.join(w.docs, 'big.md');
  fs.writeFileSync(big, text);
  const r = comment(w, big, { note: 'Overall.' });
  const first = nth(text, MARKER, 0);
  assert.equal(uniqueAnchor(text, first, first + MARKER.length).unique, false, 'the fixture: tied at the cap');
  const disk = readSidecar(r.storePath);
  const copies = [];
  for (let k = 0; k < 300; k++) copies.push(first + k * body.length);
  disk.comments.push(...copies.map((at, i) => ({ ...hostComment(text, MARKER, at, i), anchorAt: at + 7 })));   // the anchor at the copy, the position 7 characters into it
  for (const c of disk.comments.slice(1)) c.anchor = disk.comments[1].anchor;   // one anchor: every copy's context is the same
  fs.writeFileSync(r.storePath, JSON.stringify(disk));
  const st = host(w, { verb: 'status', path: big, args: {} });
  assert.equal(st.code, 0, st.stderr);
  assert.ok(st.json && st.json.ok, st.stdout.slice(0, 200));
  assert.ok(st.ms < 3000, `the status took ${st.ms} ms (the review measured 13 s on 400 such comments before the fix)`);
  const placed = st.json.placed;
  assert.equal(Object.keys(placed).length, 300, 'every stale comment has a verdict');
  for (const [i, c] of disk.comments.slice(1).entries()) assert.deepEqual(placed[c.id], { at: copies[i], confirmed: false, by: 'nearest' }, `comment ${i}`);
  // (b) a text of one character: the whole anchor sits at nearly every offset
  const flat = 'a'.repeat(100000);
  const flatPath = path.join(w.docs, 'flat.txt');
  fs.writeFileSync(flatPath, flat);
  const rf = comment(w, flatPath, { note: 'Overall.' });
  const df = readSidecar(rf.storePath);
  for (let i = 0; i < 400; i++) df.comments.push(hostComment(flat, 'a', 5, i, 24));   // track-comment's width, a position holding no whole anchor
  fs.writeFileSync(rf.storePath, JSON.stringify(df));
  const sf = host(w, { verb: 'status', path: flatPath, args: {} });
  assert.equal(sf.code, 0, sf.stderr);
  assert.ok(sf.json && sf.json.ok, sf.stdout.slice(0, 200));
  assert.ok(sf.ms < 3000, `the status took ${sf.ms} ms (13 s before the fix)`);
  assert.deepEqual(sf.json.placed, {}, 'past REFRESH_COPIES_MAX the tie is left to the panel\'s own guess, as a scan the budget refused is');
  const res = host(w, { verb: 'resolve', path: flatPath, args: { commentId: df.comments[1].id, on: true }, fence: fenceFor(sf.json) });
  assert.equal(res.code, 0, res.stderr);
  assert.ok(res.json && res.json.ok, res.stdout.slice(0, 200));
  assert.ok(res.ms < 3000, `the resolve took ${res.ms} ms (27 s before the fix: the estimate and the final reply)`);
  assert.equal(res.json.store.comments[1].resolved, true);
});

// ── the stamping pass past the budget ───────────────────────────────

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

test('past the budget the stamping pass leaves the same comments on every write and stderr says how many, once per write; the comments without the fields are stamped before those with them, so a sidecar gains fields where it has none first', () => {
  const w = world();
  const { text, quotes } = sections(900);
  assert.ok(text.length < TEXT_MAX_BYTES && text.length > 1.7 * 1024 * 1024, `the fixture: ${text.length} bytes`);
  const perWrite = Math.floor(REFRESH_SCAN_BUDGET / Math.ceil(text.length / REFRESH_PASS_DIVISOR));
  assert.ok(perWrite > 500 && perWrite < 900, `the fixture: ${perWrite} passes fit one write, fewer than the 900 seated anchors`);
  const big = path.join(w.docs, 'big.md');
  fs.writeFileSync(big, text);
  const r = comment(w, big, { note: 'Overall.' });
  const disk = readSidecar(r.storePath);
  // 800 comments with stale fields first in the store, then 100 without any (the CLI's, an older host's), every one seated
  const stale = { ordinal: 1, copies: 1, section: 'Stale > Path' };
  quotes.forEach((q, i) => disk.comments.push(hostComment(text, q, text.indexOf(q), i, 24, i < 800 ? stale : null)));
  fs.writeFileSync(r.storePath, JSON.stringify(disk));
  let st = status(w, big);
  const res = ok(w, { verb: 'reply', path: big, args: { commentId: disk.comments[1].id, note: 'Noted.' }, fence: fenceFor(st) });
  assert.ok(res.ms < 5000, `the reply took ${res.ms} ms`);
  const after = readSidecar(res.json.storePath).comments.slice(1);
  const bare = after.slice(800);
  assert.deepEqual(bare.map((c) => copyFields(c)), quotes.slice(800).map((q, k) => [1, 1, `Big > Section ${800 + k}`]), 'every comment without the fields gained them');
  assert.deepEqual(bare.map((c) => Object.keys(c)), bare.map(() => [...PASSAGE_KEYS.filter((k) => !['ordinal', 'copies', 'section'].includes(k)), 'ordinal', 'copies', 'section']), 'where JSON puts a new key on a comment from before the fields');
  const left = after.filter((c) => c.section === 'Stale > Path');
  assert.ok(left.length > 100 && left.length < 800, `the fixture: ${left.length} of the 800 with stale fields were left for the budget, more than the hundred that were bare`);
  assert.deepEqual(after.slice(0, 800).filter((c) => c.section !== 'Stale > Path').map((c) => c.section), after.slice(0, 800).filter((c) => c.section !== 'Stale > Path').map((c) => `Big > Section ${quotes.indexOf(c.anchor.quote)}`), 'the rest were refreshed');
  assert.deepEqual(unstampedNotes(res.stderr), [left.length], 'one note, counting exactly the comments whose stamp the budget refused (the measure\'s pass and the stage\'s pass share the budget)');
  assert.deepEqual(keptNotes(res.stderr), [], 'no position was kept: every one sits on its passage');
  assert.deepEqual(after.map((c) => c.anchorAt), quotes.map((q) => text.indexOf(q)), 'every position kept');
  // the next write: every comment has the fields now, so the budget is spent in store order alone; it admits the same
  // number of passes, the hundred that were bare (last in the store) keep the fields the first write gave them, and the
  // stale tail moves down by a hundred
  st = status(w, big);
  const res2 = ok(w, { verb: 'resolve', path: big, args: { commentId: disk.comments[1].id, on: true }, fence: fenceFor(st) });
  const after2 = readSidecar(res2.json.storePath).comments.slice(1);
  const stale2 = after2.map((c) => c.section === 'Stale > Path');
  assert.equal(stale2.filter(Boolean).length, left.length - 100, 'the same number of stamps, in store order alone: a hundred more of the stale ones refreshed');
  assert.deepEqual(stale2.slice(800), new Array(100).fill(false), 'the hundred keep the fields the first write gave them');
  assert.deepEqual(after2.slice(800).map((c) => copyFields(c)), bare.map((c) => copyFields(c)));
  assert.deepEqual(unstampedNotes(res2.stderr), [left.length], 'the same count of stamps refused (the budget admits the same passes), told once');
  // and the write after: the same comments are left while the sidecar keeps this shape
  st = status(w, big);
  const res3 = ok(w, { verb: 'resolve', path: big, args: { commentId: disk.comments[1].id, on: false }, fence: fenceFor(st) });
  const after3 = readSidecar(res3.json.storePath).comments.slice(1);
  assert.deepEqual(after3.map((c) => c.section === 'Stale > Path'), stale2, 'the budget is spent in store order, so the same comments are left on every write while the sidecar keeps this shape');
  assert.deepEqual(unstampedNotes(res3.stderr), [left.length], 'told once per write');
});

test('the note counts the budget\'s refusals alone: a tie past REFRESH_COPIES_MAX whose scan ran whole is left by the copies cap with no note, one whose scan the budget cut is counted', () => {
  const w = world();
  const flat = 'a'.repeat(100000);
  const flatPath = path.join(w.docs, 'flat.txt');
  fs.writeFileSync(flatPath, flat);
  const r = comment(w, flatPath, { note: 'Overall.' });
  // (a) track-comment's width: the whole anchor is 49 characters, its 65,536 hits are enumerated within the budget, and the
  // count is past the cap, so no fields are written and nothing is said
  const disk = readSidecar(r.storePath);
  for (let i = 0; i < 400; i++) disk.comments.push(hostComment(flat, 'a', 50000, i, 24));
  fs.writeFileSync(r.storePath, JSON.stringify(disk));
  let st = status(w, flatPath);
  const res = ok(w, { verb: 'resolve', path: flatPath, args: { commentId: disk.comments[1].id, on: true }, fence: fenceFor(st) });
  assert.ok(res.ms < 3000, `the resolve took ${res.ms} ms`);
  assert.deepEqual(res.json.store.comments.slice(1).map((c) => 'ordinal' in c), new Array(400).fill(false), 'no count is known past the cap');
  assert.deepEqual(unstampedNotes(res.stderr), [], 'the copies cap, not the budget');
  assert.deepEqual(keptNotes(res.stderr), []);
  // (b) the cap's width: 961 characters a hit, and the budget cuts the first scan short of the cap; every comment is counted
  const disk2 = readSidecar(r.storePath);
  for (const c of disk2.comments.slice(1)) c.anchor = engine.makeAnchor(flat, 50000, 50001, ANCHOR_CTX_CAP);
  fs.writeFileSync(r.storePath, JSON.stringify(disk2));
  st = status(w, flatPath);
  const res2 = ok(w, { verb: 'resolve', path: flatPath, args: { commentId: disk.comments[1].id, on: false }, fence: fenceFor(st) });
  assert.ok(res2.ms < 3000, `the resolve took ${res2.ms} ms`);
  assert.deepEqual(res2.json.store.comments.slice(1).map((c) => 'ordinal' in c), new Array(400).fill(false));
  assert.deepEqual(unstampedNotes(res2.stderr), [400], 'every comment kept its fields for the budget, said once');
  assert.deepEqual(keptNotes(res2.stderr), [], 'every position holds its anchor, so none was kept for the budget');
});

// ── the section cap end to end ──────────────────────────────────────

test('nine CLI-shaped comments under a heading line of nearly two megabytes: every write lands (the base host refused too-large from the section bytes alone), and each section is the capped heading', () => {
  const w = world();
  const heading = `# ${'word '.repeat(380000).trim()}\n\n`;
  const passages = [];
  let text = heading;
  for (let i = 0; i < 9; i++) { passages.push(`Passage number ${i} stands alone here.`); text += `${passages[i]}\n\n`; }
  assert.ok(text.length < TEXT_MAX_BYTES && text.length > 1.8 * 1024 * 1024, `the fixture: ${text.length} bytes`);
  const big = path.join(w.docs, 'big.md');
  fs.writeFileSync(big, text);
  const r = comment(w, big, { note: 'Overall.' });
  const disk = readSidecar(r.storePath);
  passages.forEach((q, i) => {
    const at = text.indexOf(q);
    disk.comments.push({ id: `1700000000000-${i}`, author: 'web', ts: 1700000000000 + i, anchor: engine.makeAnchor(text, at, at + q.length), body: `Note ${i}.`, replies: [], resolved: false });
  });
  fs.writeFileSync(r.storePath, JSON.stringify(disk));
  const st = status(w, big);
  const res = ok(w, { verb: 'resolve', path: big, args: { commentId: disk.comments[1].id, on: true }, fence: fenceFor(st) });
  assert.equal(res.json.store.comments[1].resolved, true, 'the write landed');
  const want = 'word '.repeat(40).trim();   // the first 200 characters of the heading, the cut's trailing space dropped
  assert.equal(want.length, SECTION_HEADING_CAP - 1, 'the fixture: the capped heading');
  for (const c of res.json.store.comments.slice(1)) {
    assert.deepEqual(copyFields(c), [1, 1, want]);
    assert.equal(c.anchorAt, text.indexOf(c.anchor.quote));
  }
  assert.ok(res.stdout.length < 64 * 1024, `the reply is ${res.stdout.length} bytes`);
  assert.deepEqual(unstampedNotes(res.stderr), []);
});

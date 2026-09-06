// Region-comment pins for tools/file-comments-host.mjs (plans/file-review.md, Slice 3; the Slices
// 3 and 4 contract, section E): a comment's `target.hash` is the host's sha256 of the figure's
// BYTES (never the client's value, never a hash of the lossy text), an embedded figure's `src`
// resolves against the commented file's directory and must be a regular file inside the project
// root, every reply carries the current hash to compare with (`fileHash` on an image or PDF,
// `embeddedHashes` per src on a text file, null for unknown), and `retarget` re-places a region
// and recomputes the hash without a log entry. Same hermetic harness as
// file-comments-host.test.mjs: the synthetic `notes-api` world under a scratch directory, the
// script driven as the kernel drives it; the figures are tiny PNGs generated from bytes at run
// time (tests/fixtures/file_comments/tiny-png.mjs), so no picture is ever committed.
// Run: node --test tools/file-comments-host-regions.test.mjs
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

import { storePathFor } from '../vendor/track-changents/store-io.mjs';
import { MEDIA_EXTENSIONS, FILE_HASH_CAP, EMBEDDED_HASH_CAP, logPathFor } from './file-comments-host.mjs';
import { tinyPng, sha256 } from '../tests/fixtures/file_comments/tiny-png.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const HOST = path.join(REPO, 'tools', 'file-comments-host.mjs');
const VENDOR = path.join(REPO, 'vendor', 'track-changents');
const FIX = path.join(REPO, 'tests', 'fixtures', 'file_comments');
const engine = createRequire(import.meta.url)(path.join(VENDOR, 'engine.js'));

const SID = '11111111-2222-3333-4444-555555555555';
const HEX64 = /^[0-9a-f]{64}$/;

// The bytes of every figure the world starts with, and the "regenerated" bytes a test swaps in.
const LATENCY = tinyPng(40, 90, 200);
const ERRORS = tinyPng(200, 60, 40);
const CHART = tinyPng(20, 160, 90);
const BANNER = tinyPng(255, 255, 255);
const REGENERATED = tinyPng(41, 90, 200);
const PDF = Buffer.from('%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF\n', 'latin1');
const SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="4" height="4"><rect width="4" height="4" fill="#9cd2ff"/></svg>\n';

let SCRATCH;
before(() => { SCRATCH = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-fc-host-regions-')); });
after(() => { try { fs.rmSync(SCRATCH, { recursive: true, force: true }); } catch { /* ignore */ } });

// ── the world ───────────────────────────────────────────────────────
// <scratch>/wN/home/                    FILE_COMMENTS_HOME: "~" in every text the script prints
//   notes-api/.git/                     the landmark that makes notes-api a project
//   notes-api/docs/report.md            a text file with no figures
//   notes-api/docs/figures.md           the fixture with embedded figures
//   notes-api/docs/figs/latency.png     embedded twice
//   notes-api/docs/figs/errors.png      embedded once
//   notes-api/docs/chart.png            a standalone image
//   notes-api/docs/report.pdf           a standalone PDF (bytes only; nothing parses it)
//   notes-api/docs/diagram.svg          an SVG, which the viewer shows as an image
//   shared/banner.png                   a figure ABOVE the project root
//   loose/figures.md                    a markdown file with no landmark above it
//   loose/figs/latency.png              a figure beside it
let worlds = 0;
function world() {
  const home = path.join(SCRATCH, `w${++worlds}`, 'home');
  const root = path.join(home, 'notes-api');
  const docs = path.join(root, 'docs');
  fs.mkdirSync(path.join(root, '.git'), { recursive: true });
  fs.mkdirSync(path.join(docs, 'figs'), { recursive: true });
  fs.copyFileSync(path.join(FIX, 'report.md'), path.join(docs, 'report.md'));
  fs.copyFileSync(path.join(FIX, 'figures.md'), path.join(docs, 'figures.md'));
  fs.writeFileSync(path.join(docs, 'figs', 'latency.png'), LATENCY);
  fs.writeFileSync(path.join(docs, 'figs', 'errors.png'), ERRORS);
  fs.writeFileSync(path.join(docs, 'chart.png'), CHART);
  fs.writeFileSync(path.join(docs, 'report.pdf'), PDF);
  fs.writeFileSync(path.join(docs, 'diagram.svg'), SVG);
  fs.mkdirSync(path.join(home, 'shared'));
  fs.writeFileSync(path.join(home, 'shared', 'banner.png'), BANNER);
  const looseDir = path.join(home, 'loose');
  fs.mkdirSync(path.join(looseDir, 'figs'), { recursive: true });
  fs.writeFileSync(path.join(looseDir, 'figures.md'),
    '# Loose figures\n\nAbove this folder:\n\n![banner](../shared/banner.png)\n\nBeside it:\n\n![p95 latency](figs/latency.png)\n');
  fs.writeFileSync(path.join(looseDir, 'figs', 'latency.png'), LATENCY);
  return {
    home, root, docs, looseDir,
    report: path.join(docs, 'report.md'),
    figures: path.join(docs, 'figures.md'),
    figText: fs.readFileSync(path.join(FIX, 'figures.md'), 'utf8'),
    latency: path.join(docs, 'figs', 'latency.png'),
    errors: path.join(docs, 'figs', 'errors.png'),
    chart: path.join(docs, 'chart.png'),
    pdf: path.join(docs, 'report.pdf'),
    svg: path.join(docs, 'diagram.svg'),
    banner: path.join(home, 'shared', 'banner.png'),
    loose: path.join(looseDir, 'figures.md'),
    looseText: fs.readFileSync(path.join(looseDir, 'figures.md'), 'utf8'),
  };
}

// The caps are cleared from the inherited environment first, so only a test that sets them
// through `extra` runs under anything but the defaults.
function env(w, extra) {
  const e = { ...process.env, FILE_COMMENTS_HOME: w.home };
  delete e.TRACKCHANGES_ROOT;
  delete e.FILE_COMMENTS_HASH_CAP;
  delete e.FILE_COMMENTS_EMBEDDED_HASH_CAP;
  Object.assign(e, extra || {});
  if (!extra || !('ROMP_SID' in extra)) { delete e.ROMP_SID; delete e.ROMP_SESSION_NAME; }
  return e;
}

// The kernel's call: node <script>, the request on stdin, one JSON object back. `extra` adds
// environment (the hash caps under test).
function host(w, req, extra) {
  const r = spawnSync(process.execPath, [HOST], { input: JSON.stringify(req), encoding: 'utf8', env: env(w, extra) });
  let json = null;
  try { json = JSON.parse(r.stdout); } catch { json = null; }
  return { code: r.status, stdout: r.stdout, stderr: r.stderr, json };
}
function ok(w, req, extra) {
  const r = host(w, req, extra);
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
// A malformed request: exit 2, nothing on stdout, the reason on stderr.
function crashed(w, req, re) {
  const r = host(w, req);
  assert.equal(r.code, 2, `a BadRequest exits 2; got ${r.code} with stdout ${r.stdout}`);
  assert.equal(r.stdout, '');
  assert.match(r.stderr, re);
  return r;
}

// The real vendored track-reply, run as an agent session named `web` would run it.
function cliOk(w, name, args) {
  const r = spawnSync(process.execPath, [path.join(VENDOR, 'cli', `track-${name}.mjs`), ...args],
    { encoding: 'utf8', env: env(w, { ROMP_SESSION_NAME: 'web', ROMP_SID: SID }) });
  assert.equal(r.status, 0, `track-${name} failed: ${r.stderr}`);
  return r;
}

function status(w, file, extra) { return ok(w, { verb: 'status', path: file, args: {} }, extra); }
function fenceFor(st) { return { storeMtimeNs: st.storeMtimeNs == null ? '' : st.storeMtimeNs }; }
function comment(w, file, st, args) { return ok(w, { verb: 'comment', path: file, args, fence: fenceFor(st) }); }
function retarget(w, file, st, args) { return ok(w, { verb: 'retarget', path: file, args, fence: fenceFor(st) }); }
function readSidecar(sp) { return JSON.parse(fs.readFileSync(sp, 'utf8')); }
function fileBytes(p) { try { return fs.readFileSync(p); } catch { return null; } }

// The anchor the browser builds from a selection of the embed line: the engine's makeAnchor at
// the nth occurrence of the token's source text, plus the selection's start offset as the hint.
function anchorAt(text, quote, nth) {
  let i = -1;
  for (let k = 0; k <= (nth || 0); k++) i = text.indexOf(quote, i + 1);
  assert.ok(i >= 0, `fixture lacks occurrence ${nth} of ${JSON.stringify(quote)}`);
  return { anchor: engine.makeAnchor(text, i, i + quote.length), hintOffset: i, idx: i };
}
const LATENCY_EMBED = '![p95 latency](figs/latency.png)';
const ERRORS_EMBED = '![error rate](figs/errors.png)';
const REGION = { x: 0.12, y: 0.4, w: 0.35, h: 0.2 };
const REGION2 = { x: 0.5, y: 0.5, w: 0.25, h: 0.1 };

// A region comment on an embedded figure: the embed line's anchor plus the target naming its src.
function embedded(w, st, quote, nth, src, note, extraTarget) {
  const { anchor, hintOffset } = anchorAt(w.figText, quote, nth);
  return comment(w, w.figures, st, { anchor, hintOffset, note, target: { kind: 'image', region: REGION, src, ...(extraTarget || {}) } });
}

// ── the hash on comment ─────────────────────────────────────────────

test('a region comment on a standalone image stores the sha256 of its bytes in the contract\'s shape — never the client\'s hash, never a hash of the lossy text', () => {
  const w = world();
  const st = status(w, w.chart);
  const r = comment(w, w.chart, st, { note: 'Crop to the plotted area.', target: { kind: 'image', region: REGION, hash: 'a'.repeat(64) } });
  const c = readSidecar(r.storePath).comments[0];
  const expected = sha256(CHART);
  assert.match(expected, HEX64);
  assert.deepEqual(c.target, { kind: 'image', region: REGION, hash: expected });
  assert.deepEqual(Object.keys(c.target), ['kind', 'region', 'hash']);
  // The CLIs' UTF-8 reading of a png is lossy (every invalid sequence becomes U+FFFD); a hash over
  // that text is a different value, and the host never stores it.
  assert.notEqual(c.target.hash, sha256(Buffer.from(fs.readFileSync(w.chart, 'utf8'), 'utf8')));
  assert.equal('anchor' in c, false);
  assert.equal('src' in c.target, false);
  assert.match(c.id, /^\d+-0$/);
  assert.equal(c.author, 'you');
  assert.equal('authorId' in c, false);
  // The reply is the status the panel holds next: the file's current hash beside the comment, and
  // no embeddedHashes on a media file. The bytes are untouched.
  assert.equal(r.fileHash, expected);
  assert.equal('embeddedHashes' in r, false);
  assert.deepEqual(fileBytes(w.chart), CHART);
  assert.equal(r.store.comments[0].target.hash, expected);
});

test('the region is kept to four decimals, a pdf target carries its page, and an SVG is hashed as bytes like any image', () => {
  const w = world();
  let r = comment(w, w.chart, status(w, w.chart), {
    note: 'Rounded.', target: { kind: 'image', region: { x: 0.123456, y: 0.99996, w: 0.00005, h: 1 } },
  });
  assert.deepEqual(readSidecar(r.storePath).comments[0].target.region, { x: 0.1235, y: 1, w: 0.0001, h: 1 });

  r = comment(w, w.pdf, status(w, w.pdf), { note: 'Page two, the table.', target: { kind: 'pdf', page: 2, region: REGION } });
  const c = readSidecar(r.storePath).comments[0];
  assert.deepEqual(c.target, { kind: 'pdf', region: REGION, page: 2, hash: sha256(PDF) });
  assert.deepEqual(Object.keys(c.target), ['kind', 'region', 'page', 'hash']);
  assert.equal(r.fileHash, sha256(PDF));
  assert.deepEqual(fileBytes(w.pdf), PDF);

  r = comment(w, w.svg, status(w, w.svg), { note: 'The rect is too pale.', target: { kind: 'image', region: REGION } });
  assert.equal(readSidecar(r.storePath).comments[0].target.hash, sha256(Buffer.from(SVG, 'utf8')));
  assert.equal(r.fileHash, sha256(Buffer.from(SVG, 'utf8')));
});

test('a malformed target crashes as a BadRequest (exit 2, nothing on stdout) and writes nothing', () => {
  const w = world();
  const { anchor, hintOffset } = anchorAt(w.figText, LATENCY_EMBED, 0);
  const bad = [
    [{ target: 'x' }, /target must be an object/],
    [{ target: { kind: 'gif', region: REGION } }, /target\.kind must be "image" or "pdf"/],
    [{ target: { kind: 'image' } }, /target\.region must be an object/],
    [{ target: { kind: 'image', region: { x: 0, y: 0, w: 0, h: 0.5 } } }, /w and \.h must be greater than 0/],
    [{ target: { kind: 'image', region: { x: 0, y: 0, w: 0.5, h: 0.00001 } } }, /w and \.h must be greater than 0/],
    [{ target: { kind: 'image', region: { x: 1.5, y: 0, w: 0.5, h: 0.5 } } }, /target\.region\.x must be a number between 0 and 1/],
    [{ target: { kind: 'image', region: { x: 0, y: -0.1, w: 0.5, h: 0.5 } } }, /target\.region\.y must be a number/],
    [{ target: { kind: 'image', region: { x: 0, y: 0, w: 'half', h: 0.5 } } }, /target\.region\.w must be a number/],
    [{ target: { kind: 'image', region: { x: 0, y: 0, w: 0.5, h: NaN } } }, /target\.region\.h must be a number/],   // NaN does not survive JSON: it arrives as null, still not a number
    [{ target: { kind: 'pdf', region: REGION } }, /target\.page must be a positive integer/],
    [{ target: { kind: 'pdf', page: 0, region: REGION } }, /target\.page must be a positive integer/],
    [{ target: { kind: 'pdf', page: 1.5, region: REGION } }, /target\.page must be a positive integer/],
    [{ target: { kind: 'pdf', page: '2', region: REGION } }, /target\.page must be a positive integer/],
    [{ target: { kind: 'image', page: 1, region: REGION } }, /an image target takes no page/],
    [{ target: { kind: 'image', region: REGION, src: 'figs/latency.png' } }, /target\.src names an embedded figure, which needs the anchor/],
    [{ target: { kind: 'image', region: REGION, src: 7 }, anchor, hintOffset }, /target\.src must be a non-empty string/],
    [{ target: { kind: 'image', region: REGION }, anchor, hintOffset }, /needs target\.src/],
  ];
  for (const [args, re] of bad) {
    const file = 'anchor' in args ? w.figures : w.chart;
    crashed(w, { verb: 'comment', path: file, args: { note: 'A note.', ...args }, fence: { storeMtimeNs: '' } }, re);
  }
  assert.equal(fs.existsSync(path.join(w.root, '.trackchanges')), false, 'no sidecar directory was created');
  assert.deepEqual(fileBytes(w.chart), CHART);
});

// ── embedded figures ────────────────────────────────────────────────

test('a region on an embedded figure carries the embed line\'s anchor, src as written, and the sha256 of the figure\'s bytes; track-reply keeps both', () => {
  const w = world();
  const st = status(w, w.figures);
  assert.deepEqual(st.embeddedHashes, {}, 'no sidecar yet: nothing to hash');
  assert.equal('fileHash' in st, false);
  const r = embedded(w, st, LATENCY_EMBED, 0, 'figs/latency.png', 'The y axis needs a label.', { hash: 'client-guess' });
  const sp = r.storePath;
  assert.equal(sp, storePathFor(w.root, w.figures), 'the comment lives in the markdown file\'s sidecar, not the figure\'s');
  const c = readSidecar(sp).comments[0];
  const { idx } = anchorAt(w.figText, LATENCY_EMBED, 0);
  assert.deepEqual(c.anchor, engine.makeAnchor(w.figText, idx, idx + LATENCY_EMBED.length));
  assert.equal(c.anchor.quote, LATENCY_EMBED);
  assert.equal(c.id, `${c.ts}-${idx}`);
  assert.deepEqual(c.target, { kind: 'image', region: REGION, hash: sha256(LATENCY), src: 'figs/latency.png' });
  assert.deepEqual(Object.keys(c.target), ['kind', 'region', 'hash', 'src']);
  assert.notEqual(c.target.hash, sha256(Buffer.from(w.figText, 'utf8')), 'the figure\'s bytes, not the markdown\'s');
  // The reply carries the figure's current hash under the src as written, and no fileHash.
  assert.deepEqual(r.embeddedHashes, { 'figs/latency.png': sha256(LATENCY) });
  assert.equal('fileHash' in r, false);
  // track-reply answers it; anchor and target survive, and neither file changed.
  cliOk(w, 'reply', ['--file', w.figures, '--thread', c.id, '--note', 'Labeled.']);
  const after = readSidecar(sp).comments[0];
  assert.deepEqual({ ...after, replies: [] }, { ...c, replies: [] });
  assert.equal(after.replies[0].author, 'web');
  assert.deepEqual(fileBytes(w.latency), LATENCY);
  assert.equal(fs.readFileSync(w.figures, 'utf8'), w.figText);
});

test('an embedded figure\'s src must resolve to a regular file inside the project root; anything else refuses unreadable and writes nothing', () => {
  const w = world();
  const st = status(w, w.figures);
  const escape = path.join(w.docs, 'figs', 'escape.png');
  fs.symlinkSync(w.banner, escape);
  const fifo = path.join(w.docs, 'figs', 'pipe.png');
  const mkfifo = spawnSync('mkfifo', [fifo]);
  const cases = [
    ['../../shared/banner.png', /outside the project root/],       // exists, above the root
    ['../../../nowhere/banner.png', /cannot be resolved/],          // above the root and absent
    ['figs/missing.png', /cannot be resolved/],
    ['figs', /is not a regular file/],                              // a directory
    ['figs/escape.png', /outside the project root/],                // a symlink that leaves the root
    ['https://example.com/notes-api/logo.png', /is a URL, not a file in the project/],
    ['data:image/png;base64,iVBORw0KGgo=', /is a URL/],
  ];
  if (mkfifo.status === 0) cases.push(['figs/pipe.png', /is not a regular file/]);
  for (const [src, re] of cases) {
    const { anchor, hintOffset } = anchorAt(w.figText, LATENCY_EMBED, 0);
    const r = refused(w, {
      verb: 'comment', path: w.figures, fence: fenceFor(st),
      args: { anchor, hintOffset, note: 'On the figure.', target: { kind: 'image', region: REGION, src } },
    }, 'unreadable');
    assert.match(r.error, re, src);
    assert.ok(r.error.includes(src) && r.error.includes('~/notes-api/docs/figures.md'), r.error);
    assert.ok(r.error.endsWith('nothing was changed'), r.error);
  }
  assert.equal(fs.existsSync(path.join(w.root, '.trackchanges')), false);
  // A symlink that stays inside the root is fine: the hash is of the file it names.
  const inside = path.join(w.docs, 'figs', 'alias.png');
  fs.symlinkSync(w.errors, inside);
  const { anchor, hintOffset } = anchorAt(w.figText, ERRORS_EMBED, 0);
  const r = comment(w, w.figures, st, { anchor, hintOffset, note: 'Via the alias.', target: { kind: 'image', region: REGION, src: 'figs/alias.png' } });
  assert.equal(readSidecar(r.storePath).comments[0].target.hash, sha256(ERRORS));
  assert.equal(readSidecar(r.storePath).comments[0].target.src, 'figs/alias.png');
});

test('a loose markdown file\'s root-to-be is its own directory: a figure above it refuses and creates no landmark; one beside it is hashed and the landmark appears', () => {
  const w = world();
  assert.equal(status(w, w.loose).root, null);
  let a = anchorAt(w.looseText, '![banner](../shared/banner.png)', 0);
  const r = refused(w, {
    verb: 'comment', path: w.loose, fence: { storeMtimeNs: '' },
    args: { anchor: a.anchor, hintOffset: a.hintOffset, note: 'Too wide.', target: { kind: 'image', region: REGION, src: '../shared/banner.png' } },
  }, 'unreadable');
  assert.match(r.error, /outside the project root ~\/loose/);
  assert.equal(fs.existsSync(path.join(w.looseDir, '.trackchanges')), false);

  a = anchorAt(w.looseText, LATENCY_EMBED, 0);
  const okr = ok(w, {
    verb: 'comment', path: w.loose, fence: { storeMtimeNs: '' },
    args: { anchor: a.anchor, hintOffset: a.hintOffset, note: 'Label the axis.', target: { kind: 'image', region: REGION, src: 'figs/latency.png' } },
  });
  assert.equal(okr.root, w.looseDir);
  assert.equal(okr.storePath, storePathFor(w.looseDir, w.loose));
  assert.equal(readSidecar(okr.storePath).comments[0].target.hash, sha256(LATENCY));
  assert.deepEqual(okr.embeddedHashes, { 'figs/latency.png': sha256(LATENCY) });
});

// ── what a reply carries ────────────────────────────────────────────

test('a text file\'s replies carry embeddedHashes: one per distinct src its region comments name, null for a figure that cannot be read, {} with none', () => {
  const w = world();
  let st = status(w, w.figures);
  embedded(w, st, LATENCY_EMBED, 0, 'figs/latency.png', 'First chart, first embed.');
  st = status(w, w.figures);
  embedded(w, st, LATENCY_EMBED, 1, 'figs/latency.png', 'First chart, second embed.');
  st = status(w, w.figures);
  let r = embedded(w, st, ERRORS_EMBED, 0, 'figs/errors.png', 'Second chart.');
  // Two srcs across three comments, in order of first appearance.
  assert.deepEqual(r.embeddedHashes, { 'figs/latency.png': sha256(LATENCY), 'figs/errors.png': sha256(ERRORS) });
  assert.deepEqual(Object.keys(r.embeddedHashes), ['figs/latency.png', 'figs/errors.png']);
  assert.equal(r.store.comments.length, 3);
  assert.equal('fileHash' in r, false);

  // The figure is regenerated: its hash flips while every comment keeps the hash it was drawn on
  // (the panel's stale verdict is that comparison). A deleted figure is null — unknown, not stale.
  fs.writeFileSync(w.latency, REGENERATED);
  fs.unlinkSync(w.errors);
  st = status(w, w.figures);
  assert.deepEqual(st.embeddedHashes, { 'figs/latency.png': sha256(REGENERATED), 'figs/errors.png': null });
  for (const c of st.store.comments.slice(0, 2)) assert.equal(c.target.hash, sha256(LATENCY));
  assert.equal(st.store.comments[2].target.hash, sha256(ERRORS));
  // A src that now points outside the root is null too, with a note on stderr, never a refusal.
  fs.writeFileSync(w.errors, ERRORS);
  fs.unlinkSync(w.latency);
  fs.symlinkSync(w.banner, w.latency);
  const raw = host(w, { verb: 'status', path: w.figures, args: {} });
  assert.deepEqual(raw.json.embeddedHashes, { 'figs/latency.png': null, 'figs/errors.png': sha256(ERRORS) });
  assert.match(raw.stderr, /figs\/latency\.png .* was not hashed: .*outside the project root/);

  // A text file whose comments name no figure, and one with no sidecar, answer {}.
  r = comment(w, w.report, status(w, w.report), { note: 'Whole file.' });
  assert.deepEqual(r.embeddedHashes, {});
  assert.deepEqual(status(w, w.report).embeddedHashes, {});
});

test('the embedded budget: figures are hashed until the call would pass the cap, then null; the caps are the kernel\'s numbers', () => {
  const w = world();
  let st = status(w, w.figures);
  embedded(w, st, LATENCY_EMBED, 0, 'figs/latency.png', 'One.');
  st = status(w, w.figures);
  embedded(w, st, ERRORS_EMBED, 0, 'figs/errors.png', 'Two.');
  const size = LATENCY.length;
  assert.equal(ERRORS.length, size);
  // Exactly one figure's worth: the first (by first appearance) is hashed and the second is past it.
  let r = status(w, w.figures, { FILE_COMMENTS_EMBEDDED_HASH_CAP: String(size) });
  assert.deepEqual(r.embeddedHashes, { 'figs/latency.png': sha256(LATENCY), 'figs/errors.png': null });
  r = status(w, w.figures, { FILE_COMMENTS_EMBEDDED_HASH_CAP: String(size - 1) });
  assert.deepEqual(r.embeddedHashes, { 'figs/latency.png': null, 'figs/errors.png': null });
  r = status(w, w.figures, { FILE_COMMENTS_EMBEDDED_HASH_CAP: String(2 * size) });
  assert.deepEqual(r.embeddedHashes, { 'figs/latency.png': sha256(LATENCY), 'figs/errors.png': sha256(ERRORS) });
  assert.equal(EMBEDDED_HASH_CAP, 200_000_000);
  // The kernel's _MEDIA_MAX_BYTES is a power-of-two 50 MiB (so its 413 reads "50.0 MB"), not the
  // 50,000,000 the host carried through Slice 3; file-comments-host-caps.test.mjs reads the constant
  // out of kernel.py and pins the two equal byte for byte, so this literal must agree with both.
  assert.equal(FILE_HASH_CAP, 50 * 1024 * 1024);
});

test('a media file\'s replies carry fileHash — the sha256 of its bytes, null above the cap — and no embeddedHashes', () => {
  const w = world();
  for (const [file, bytes] of [[w.chart, CHART], [w.pdf, PDF], [w.svg, Buffer.from(SVG, 'utf8')]]) {
    const st = status(w, file);
    assert.equal(st.fileHash, sha256(bytes), file);
    assert.equal('embeddedHashes' in st, false, file);
    assert.equal(st.store, null, 'status read nothing but the bytes: no sidecar was created');
  }
  const size = CHART.length;
  assert.equal(status(w, w.chart, { FILE_COMMENTS_HASH_CAP: String(size) }).fileHash, sha256(CHART));
  assert.equal(status(w, w.chart, { FILE_COMMENTS_HASH_CAP: String(size - 1) }).fileHash, null);
  assert.equal(status(w, w.chart, { FILE_COMMENTS_HASH_CAP: '0' }).fileHash, null);
  // The cap is status's alone: a comment on the same file still stamps the full hash.
  const r = ok(w, { verb: 'comment', path: w.chart, args: { note: 'Over the cap.', target: { kind: 'image', region: REGION } }, fence: { storeMtimeNs: '' } },
    { FILE_COMMENTS_HASH_CAP: '0' });
  assert.equal(r.fileHash, null);
  assert.equal(r.store.comments[0].target.hash, sha256(CHART));
  // A text file: the other key, never fileHash.
  const st = status(w, w.report);
  assert.equal('fileHash' in st, false);
  assert.deepEqual(st.embeddedHashes, {});
  assert.equal(fs.existsSync(logPathFor(storePathFor(w.root, w.report))), false);
});

// ── retarget ────────────────────────────────────────────────────────

test('retarget replaces a region comment\'s target and recomputes the hash after the bytes change, appends no log entry, and keeps everything else', () => {
  const w = world();
  let st = status(w, w.chart);
  let r = comment(w, w.chart, st, { note: 'Crop to the plotted area.', target: { kind: 'image', region: REGION } });
  const sp = r.storePath;
  const id = r.store.comments[0].id;
  st = status(w, w.chart);
  ok(w, { verb: 'reply', path: w.chart, args: { commentId: id, note: 'And drop the legend.' }, fence: fenceFor(st) });
  const before = readSidecar(sp);
  assert.equal(before.comments[0].target.hash, sha256(CHART));

  // The figure is regenerated: the reply's fileHash and the comment's hash disagree (stale).
  fs.writeFileSync(w.chart, REGENERATED);
  st = status(w, w.chart);
  assert.equal(st.fileHash, sha256(REGENERATED));
  assert.notEqual(st.store.comments[0].target.hash, st.fileHash);

  // Re-placed: the new rectangle over the bytes as they are now, the client's hash ignored.
  r = retarget(w, w.chart, st, { commentId: id, target: { kind: 'image', region: REGION2, hash: 'stale-guess' } });
  const after = readSidecar(sp);
  assert.deepEqual(after.comments[0].target, { kind: 'image', region: REGION2, hash: sha256(REGENERATED) });
  assert.equal(r.fileHash, sha256(REGENERATED));
  assert.equal(r.store.comments[0].target.hash, r.fileHash, 'current again');
  assert.deepEqual({ ...after.comments[0], target: null }, { ...before.comments[0], target: null }, 'id, author, ts, body, replies, resolved unchanged');
  assert.equal(after.comments[0].replies.length, 1);
  assert.equal(after.comments.length, 1);
  assert.deepEqual(after.suggestions, before.suggestions);
  assert.equal(after.v, 3);
  assert.equal(fs.existsSync(logPathFor(sp)), false, 'a re-placed rectangle is not a decision: no log entry');
  assert.deepEqual(r.unsent.comments, [id], 'still unsent, as before');
  assert.equal(r.storeMtimeNs, String(fs.statSync(sp, { bigint: true }).mtimeNs));
  assert.deepEqual(fileBytes(w.chart), REGENERATED);
});

test('retarget refusals: the sidecar fence, no-comment, and a BadRequest for a comment without a region or a target that does not fit; nothing written', () => {
  const w = world();
  let st = status(w, w.chart);
  let r = comment(w, w.chart, st, { note: 'On the region.', target: { kind: 'image', region: REGION } });
  const sp = r.storePath;
  const regionId = r.store.comments[0].id;
  st = status(w, w.chart);
  r = comment(w, w.chart, st, { note: 'On the whole file.' });
  const wholeId = r.store.comments[1].id;
  st = status(w, w.chart);
  const bytes = fs.readFileSync(sp);
  const fresh = { commentId: regionId, target: { kind: 'image', region: REGION2 } };

  refused(w, { verb: 'retarget', path: w.chart, args: fresh, fence: { storeMtimeNs: '' } }, 'store-moved');
  refused(w, { verb: 'retarget', path: w.chart, args: fresh, fence: { storeMtimeNs: '1' } }, 'store-moved');
  crashed(w, { verb: 'retarget', path: w.chart, args: fresh }, /fence\.storeMtimeNs is required for retarget/);
  const nc = refused(w, { verb: 'retarget', path: w.chart, args: { ...fresh, commentId: 'no-such' }, fence: fenceFor(st) }, 'no-comment');
  assert.ok(nc.error.includes('no-such') && nc.error.includes('~/notes-api/docs/chart.png'), nc.error);
  crashed(w, { verb: 'retarget', path: w.chart, args: { ...fresh, commentId: wholeId }, fence: fenceFor(st) }, /has no region to re-place/);
  crashed(w, { verb: 'retarget', path: w.chart, args: { commentId: regionId }, fence: fenceFor(st) }, /retarget needs target/);
  crashed(w, { verb: 'retarget', path: w.chart, args: { target: fresh.target }, fence: fenceFor(st) }, /commentId is required/);
  crashed(w, { verb: 'retarget', path: w.chart, args: { commentId: regionId, target: { kind: 'gif', region: REGION2 } }, fence: fenceFor(st) }, /target\.kind must be/);
  crashed(w, { verb: 'retarget', path: w.chart, args: { commentId: regionId, target: { kind: 'image', region: REGION2, src: 'chart.png' } }, fence: fenceFor(st) },
    /target\.src names an embedded figure/);
  assert.deepEqual(fs.readFileSync(sp), bytes, 'the sidecar is byte-identical after every refusal');
  assert.equal(fs.existsSync(logPathFor(sp)), false);
  // A file with no sidecar at all: no-comment, and no sidecar appears.
  refused(w, { verb: 'retarget', path: w.pdf, args: fresh, fence: { storeMtimeNs: '' } }, 'no-comment');
  assert.equal(fs.existsSync(storePathFor(w.root, w.pdf)), false);
});

test('retarget on an embedded figure keeps needing src and hashes the figure as it is now; the anchor stays', () => {
  const w = world();
  let st = status(w, w.figures);
  let r = embedded(w, st, LATENCY_EMBED, 0, 'figs/latency.png', 'The y axis needs a label.');
  const sp = r.storePath;
  const c = r.store.comments[0];
  fs.writeFileSync(w.latency, REGENERATED);
  st = status(w, w.figures);
  assert.deepEqual(st.embeddedHashes, { 'figs/latency.png': sha256(REGENERATED) });
  crashed(w, { verb: 'retarget', path: w.figures, args: { commentId: c.id, target: { kind: 'image', region: REGION2 } }, fence: fenceFor(st) },
    /needs target\.src/);
  const bad = refused(w, { verb: 'retarget', path: w.figures, args: { commentId: c.id, target: { kind: 'image', region: REGION2, src: '../../shared/banner.png' } }, fence: fenceFor(st) },
    'unreadable');
  assert.match(bad.error, /outside the project root/);
  assert.deepEqual(readSidecar(sp).comments[0], c, 'unchanged after the refusals');
  r = retarget(w, w.figures, st, { commentId: c.id, target: { kind: 'image', region: REGION2, src: 'figs/latency.png' } });
  const after = readSidecar(sp).comments[0];
  assert.deepEqual(after.target, { kind: 'image', region: REGION2, hash: sha256(REGENERATED), src: 'figs/latency.png' });
  assert.deepEqual(after.anchor, c.anchor);
  assert.equal(after.id, c.id);
  assert.deepEqual(r.embeddedHashes, { 'figs/latency.png': sha256(REGENERATED) });
  assert.equal(fs.existsSync(logPathFor(sp)), false);
});

// ── the media set ───────────────────────────────────────────────────

test('MEDIA_EXTENSIONS mirrors the kernel\'s _PREVIEW_MIME: the _IMG_MIME keys plus .pdf', () => {
  const src = fs.readFileSync(path.join(REPO, 'kernel', 'kernel.py'), 'utf8');
  const m = /_IMG_MIME = \{([^}]*)\}/.exec(src);
  assert.ok(m, 'kernel.py defines _IMG_MIME as a dict literal');
  const exts = [...m[1].matchAll(/"\.(\w+)":/g)].map((x) => x[1]);
  assert.ok(exts.length >= 5, `read ${exts.length} image extensions from the kernel`);
  assert.match(src, /_PREVIEW_MIME = dict\(_IMG_MIME, \*\*\{"\.pdf": "application\/pdf"\}\)/);
  assert.deepEqual(new Set([...exts, 'pdf']), MEDIA_EXTENSIONS);
});

// ── the src is decoded as the viewer decodes it ─────────────────────

test('an embedded src is decoded before it is resolved, as the viewer decodes it: %20 names a space, a malformed escape reads as written, and the stored src and the embeddedHashes key stay as the embed wrote them', () => {
  const w = world();
  fs.writeFileSync(path.join(w.docs, 'figs', 'p95 latency.png'), LATENCY);
  fs.writeFileSync(path.join(w.docs, 'figs', '100%.png'), ERRORS);
  fs.writeFileSync(path.join(w.docs, 'figs', 'a%20b.png'), CHART);   // a NAME that holds an escape: the viewer never shows it
  const md = path.join(w.docs, 'spaced.md');
  const text = '# Spaced\n\n![p95](figs/p95%20latency.png)\n\n![all](figs/100%.png)\n\n![literal](figs/a%20b.png)\n';
  fs.writeFileSync(md, text);
  const st = status(w, md);
  // Markdown spells the space as %20 and the panel sends the destination as written (E1); the file
  // the viewer loaded is the one with the space, and that is the one hashed.
  let a = anchorAt(text, '![p95](figs/p95%20latency.png)', 0);
  const r = comment(w, md, st, { anchor: a.anchor, hintOffset: a.hintOffset, note: 'Crop to the plot.', target: { kind: 'image', region: REGION, src: 'figs/p95%20latency.png' } });
  const c = readSidecar(r.storePath).comments[0];
  assert.equal(c.target.src, 'figs/p95%20latency.png', 'stored as written');
  assert.equal(c.target.hash, sha256(LATENCY), 'the bytes of the file the viewer showed');
  assert.deepEqual(r.embeddedHashes, { 'figs/p95%20latency.png': sha256(LATENCY) }, 'keyed as written, so the panel finds it');
  // A malformed escape is read as written, which is also what the viewer loads.
  a = anchorAt(text, '![all](figs/100%.png)', 0);
  const r2 = comment(w, md, r, { anchor: a.anchor, hintOffset: a.hintOffset, note: 'All of it.', target: { kind: 'image', region: REGION, src: 'figs/100%.png' } });
  assert.equal(readSidecar(r2.storePath).comments[1].target.hash, sha256(ERRORS));
  assert.deepEqual(r2.embeddedHashes, { 'figs/p95%20latency.png': sha256(LATENCY), 'figs/100%.png': sha256(ERRORS) });
  // A file whose name literally holds %20 is one the viewer resolves to "a b.png" and never shows, so there
  // is no figure to draw on; the host reads the same path and refuses instead of hashing a picture nobody saw.
  a = anchorAt(text, '![literal](figs/a%20b.png)', 0);
  const bad = refused(w, {
    verb: 'comment', path: md, fence: fenceFor(r2),
    args: { anchor: a.anchor, hintOffset: a.hintOffset, note: 'x', target: { kind: 'image', region: REGION, src: 'figs/a%20b.png' } },
  }, 'unreadable');
  assert.match(bad.error, /figs\/a b\.png cannot be resolved/);
  assert.equal(readSidecar(r2.storePath).comments.length, 2);
});

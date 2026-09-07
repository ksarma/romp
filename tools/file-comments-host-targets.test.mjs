// Target pins for tools/file-comments-host.mjs (plans/file-review.md, Slice 3, "The contract",
// "Security posture"): what the host checks about a region's target BEFORE it hashes anything, and
// what a reply says when a hash could not be taken. The regions test covers the happy path and the
// resolution of a src; this module covers the checks the Slice 3 review found missing:
//   * an anchored region's `src` must be a figure the anchored passage embeds (`figure-mismatch`),
//     and a re-place keeps the comment's figure — else the rectangle paints on one figure while the
//     stale check follows another, and any client gets a hash of any in-root file it names; a stored
//     target with no src (the contract's shape) is read by its passage: status hashes the figure the
//     passage tells, and a re-place takes only that figure;
//   * the target's `kind` must be what the named file's extension says, and a region with no anchor
//     must be on an image or a PDF — a `pdf` target on a png, or a standalone region on a markdown
//     file, is a caller bug and is not written;
//   * the region lies inside the unit square (x + w and y + h at most 1 at four decimals);
//   * the bytes a write verb hashes are capped at what the viewer shows (FILE_HASH_CAP): a figure
//     past it refuses `too-large` at once instead of pinning the host until the kernel's deadline;
//   * an absolute src is held to the same root containment as a relative one, in both directions;
//   * every null hash in a reply travels with its reason (fileHashReason, embeddedHashReasons), so
//     the panel can tell a deleted figure from one that left the root from one past the budget.
// Same hermetic harness as file-comments-host-regions.test.mjs: the synthetic `notes-api` world
// under a scratch directory, tiny PNGs generated at run time, the script driven as the kernel drives
// it. Run: node --test tools/file-comments-host-targets.test.mjs
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';
import { createHash } from 'node:crypto';

import { storePathFor } from '../vendor/track-changents/store-io.mjs';
import { FILE_HASH_CAP, imageEmbeds, mediaKind, humanBytes, validateTarget, BadRequest } from './file-comments-host.mjs';
import { tinyPng, sha256 } from '../tests/fixtures/file_comments/tiny-png.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const HOST = path.join(REPO, 'tools', 'file-comments-host.mjs');
const VENDOR = path.join(REPO, 'vendor', 'track-changents');
const FIX = path.join(REPO, 'tests', 'fixtures', 'file_comments');
const engine = createRequire(import.meta.url)(path.join(VENDOR, 'engine.js'));

const LATENCY = tinyPng(10, 20, 30);
const ERRORS = tinyPng(200, 30, 30);
const CHART = tinyPng(0, 120, 60);
const BANNER = tinyPng(255, 255, 255);
const PDF = Buffer.from('%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF\n', 'latin1');
const SECRET = Buffer.from('-----BEGIN SYNTHETIC KEY-----\nnot a key, a fixture\n-----END SYNTHETIC KEY-----\n');

let SCRATCH;
before(() => { SCRATCH = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-fc-host-targets-')); });
after(() => { try { fs.rmSync(SCRATCH, { recursive: true, force: true }); } catch { /* ignore */ } });

// <scratch>/wN/home/                  FILE_COMMENTS_HOME: "~" in every text the script prints
//   notes-api/.git/                   the landmark that makes notes-api a project
//   notes-api/secret.bin              an in-root file that is not a figure
//   notes-api/docs/report.md          a text file with no figures
//   notes-api/docs/figures.md         the fixture with embedded figures
//   notes-api/docs/figs/latency.png   embedded twice
//   notes-api/docs/figs/errors.png    embedded once
//   notes-api/docs/chart.png          a standalone image
//   notes-api/docs/report.pdf         a standalone PDF (bytes only)
//   shared/banner.png                 a figure ABOVE the project root
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
  fs.writeFileSync(path.join(root, 'secret.bin'), SECRET);
  fs.mkdirSync(path.join(home, 'shared'));
  fs.writeFileSync(path.join(home, 'shared', 'banner.png'), BANNER);
  return {
    home, root, docs,
    report: path.join(docs, 'report.md'),
    figures: path.join(docs, 'figures.md'),
    figText: fs.readFileSync(path.join(FIX, 'figures.md'), 'utf8'),
    latency: path.join(docs, 'figs', 'latency.png'),
    errors: path.join(docs, 'figs', 'errors.png'),
    chart: path.join(docs, 'chart.png'),
    pdf: path.join(docs, 'report.pdf'),
    secret: path.join(root, 'secret.bin'),
    banner: path.join(home, 'shared', 'banner.png'),
  };
}

function env(w, extra) {
  const e = { ...process.env, FILE_COMMENTS_HOME: w.home };
  delete e.TRACKCHANGES_ROOT;
  delete e.FILE_COMMENTS_HASH_CAP;
  delete e.FILE_COMMENTS_EMBEDDED_HASH_CAP;
  delete e.ROMP_SID;
  delete e.ROMP_SESSION_NAME;
  Object.assign(e, extra || {});
  return e;
}
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
  return r.json;
}
function refused(w, req, code) {
  const r = host(w, req);
  assert.equal(r.code, 0, `a refusal exits 0; got ${r.code}: ${r.stderr}`);
  assert.ok(r.json && r.json.ok === false, `expected ok:false, got ${r.stdout}`);
  assert.equal(r.json.code, code, r.json.error);
  return r.json;
}
function crashed(w, req, re) {
  const r = host(w, req);
  assert.equal(r.code, 2, `a BadRequest exits 2; got ${r.code} with stdout ${r.stdout}`);
  assert.equal(r.stdout, '');
  assert.match(r.stderr, re);
  return r;
}
function status(w, file, extra) { return ok(w, { verb: 'status', path: file, args: {} }, extra); }
function fenceFor(st) { return { storeMtimeNs: st.storeMtimeNs == null ? '' : st.storeMtimeNs }; }
function readSidecar(sp) { return JSON.parse(fs.readFileSync(sp, 'utf8')); }
function anchorAt(text, quote, nth) {
  let i = -1;
  for (let k = 0; k <= (nth || 0); k++) i = text.indexOf(quote, i + 1);
  assert.ok(i >= 0, `fixture lacks occurrence ${nth} of ${JSON.stringify(quote)}`);
  return { anchor: engine.makeAnchor(text, i, i + quote.length), hintOffset: i };
}
const LATENCY_EMBED = '![p95 latency](figs/latency.png)';
const ERRORS_EMBED = '![error rate](figs/errors.png)';
const REGION = { x: 0.12, y: 0.4, w: 0.35, h: 0.2 };
const REGION2 = { x: 0.5, y: 0.5, w: 0.25, h: 0.1 };
// A comment request on `file` whose anchor is the nth occurrence of `quote` in `text`.
function anchored(w, file, text, quote, nth, st, target, note) {
  const { anchor, hintOffset } = anchorAt(text, quote, nth);
  return { verb: 'comment', path: file, fence: fenceFor(st), args: { anchor, hintOffset, note: note || 'On the figure.', target } };
}
function noSidecar(w) { assert.equal(fs.existsSync(path.join(w.root, '.trackchanges')), false, 'nothing was written'); }

// ── the src must be a figure the anchored passage embeds ────────────

test('a src the anchored passage does not embed refuses figure-mismatch and hashes nothing: the passage\'s own figures are named, an in-root file that is no figure is never hashed', () => {
  const w = world();
  const st = status(w, w.figures);
  // The latency line, with the errors figure named: the rectangle would paint on one and the stale check follow the other.
  let r = refused(w, anchored(w, w.figures, w.figText, LATENCY_EMBED, 0, st, { kind: 'image', region: REGION, src: 'figs/errors.png' }), 'figure-mismatch');
  assert.match(r.error, /anchored to in ~\/notes-api\/docs\/figures\.md embeds figs\/latency\.png, not figs\/errors\.png/);
  assert.ok(r.error.endsWith('nothing was changed'), r.error);
  // A file in the root that is no figure, and would have been hashed for whoever asked: not named, not hashed.
  r = refused(w, anchored(w, w.figures, w.figText, LATENCY_EMBED, 0, st, { kind: 'image', region: REGION, src: '../secret.bin' }), 'figure-mismatch');
  assert.equal(JSON.stringify(r).includes(sha256(SECRET)), false, 'no hash of the named file leaves the host');
  // A passage with no embed at all.
  r = refused(w, anchored(w, w.figures, w.figText, 'Error rates over the same window:', 0, st, { kind: 'image', region: REGION, src: 'figs/errors.png' }), 'figure-mismatch');
  assert.match(r.error, /embeds no figure, so nothing there is figs\/errors\.png/);
  noSidecar(w);
  // The same src on the passage that embeds it is the ordinary case.
  const good = ok(w, anchored(w, w.figures, w.figText, ERRORS_EMBED, 0, st, { kind: 'image', region: REGION, src: 'figs/errors.png' }));
  assert.equal(good.store.comments[0].target.hash, sha256(ERRORS));
  assert.deepEqual(good.embeddedHashes, { 'figs/errors.png': sha256(ERRORS) });
});

test('the passage may be wider than the embed, and every embed form the panel reads counts: inline, reference-style through its definition, and a raw img tag', () => {
  const w = world();
  const md = path.join(w.docs, 'forms.md');
  const text = '# Forms\n\nThe latency chart, then the rest:\n\n![p95 latency](figs/latency.png)\n\n'
    + 'Errors by reference: ![error rate][errs] and in html: <img src="figs/latency.png" alt="again">\n\n'
    + '```\n![fenced](figs/errors.png)\n```\n\n[errs]: figs/errors.png\n';
  fs.writeFileSync(md, text);
  let st = status(w, md);
  // A whole paragraph and the embed line together: the passage embeds the figure, so the src stands.
  let r = ok(w, anchored(w, md, text, 'The latency chart, then the rest:\n\n![p95 latency](figs/latency.png)', 0, st, { kind: 'image', region: REGION, src: 'figs/latency.png' }));
  assert.equal(r.store.comments[0].target.src, 'figs/latency.png');
  // Reference-style: the destination sits in a definition elsewhere in the file, and that is the src the panel sends.
  st = status(w, md);
  r = ok(w, anchored(w, md, text, '![error rate][errs]', 0, st, { kind: 'image', region: REGION, src: 'figs/errors.png' }));
  assert.equal(r.store.comments[1].target.hash, sha256(ERRORS));
  st = status(w, md);
  refused(w, anchored(w, md, text, '![error rate][errs]', 0, st, { kind: 'image', region: REGION, src: 'errs' }), 'figure-mismatch');
  // A raw <img>: the attribute as written.
  r = ok(w, anchored(w, md, text, '<img src="figs/latency.png" alt="again">', 0, st, { kind: 'image', region: REGION, src: 'figs/latency.png' }));
  assert.equal(r.store.comments.length, 3);
  // An embed inside fenced code renders as text: it embeds nothing.
  st = status(w, md);
  refused(w, anchored(w, md, text, '![fenced](figs/errors.png)', 0, st, { kind: 'image', region: REGION, src: 'figs/errors.png' }), 'figure-mismatch');
  assert.equal(readSidecar(r.storePath).comments.length, 3);
});

test('imageEmbeds reads the panel\'s four forms with the destination as written and skips fenced code, so the host and the panel name the same figures', () => {
  const text = 'a ![one](figs/a.png "t") b ![two](<figs/b c.png>) c ![three][ref] d ![ref] e <img alt=x src=\'figs/e.png\'>\n'
    + '~~~\n![no](figs/f.png)\n~~~\n[ref]: figs/d.png\n![none][missing]\n';
  const embeds = imageEmbeds(text);
  assert.deepEqual(embeds.map((e) => [text.slice(e.start, e.end), e.dest]), [
    ['![one](figs/a.png "t")', 'figs/a.png'],
    ['![two](<figs/b c.png>)', 'figs/b c.png'],
    ['![three][ref]', 'figs/d.png'],
    ['![ref]', 'figs/d.png'],
    ['<img alt=x src=\'figs/e.png\'>', 'figs/e.png'],
  ]);
  assert.deepEqual(imageEmbeds('no figures here'), []);
});

// ── retarget keeps the figure ───────────────────────────────────────

test('retarget keeps the comment\'s figure: another src is a caller bug and nothing is written; a stored target without a src takes one only from the passage it is anchored to', () => {
  const w = world();
  let st = status(w, w.figures);
  let r = ok(w, anchored(w, w.figures, w.figText, LATENCY_EMBED, 0, st, { kind: 'image', region: REGION, src: 'figs/latency.png' }));
  const sp = r.storePath;
  const c = r.store.comments[0];
  st = status(w, w.figures);
  const bytes = fs.readFileSync(sp);
  crashed(w, { verb: 'retarget', path: w.figures, fence: fenceFor(st), args: { commentId: c.id, target: { kind: 'image', region: REGION2, src: 'figs/errors.png' } } },
    /retarget keeps the figure: comment \S+ is on figs\/latency\.png, and target\.src names figs\/errors\.png/);
  crashed(w, { verb: 'retarget', path: w.figures, fence: fenceFor(st), args: { commentId: c.id, target: { kind: 'image', region: REGION2, src: '../secret.bin' } } },
    /retarget keeps the figure/);
  assert.deepEqual(fs.readFileSync(sp), bytes, 'byte-identical after the refusals');
  // Another writer left the target with an anchor and no src (the contract's own shape): status tells the figure
  // from the anchored passage and hashes it under that src, so the stale check has something to compare against
  // (derivedSrcsFor; the plan-shape module pins the reply's store in full), and it does not rewrite the disk — so
  // the re-place below still meets a stored target with no src, and its new src must be what the passage embeds.
  const disk = readSidecar(sp);
  delete disk.comments[0].target.src;
  fs.writeFileSync(sp, JSON.stringify(disk, null, 2) + '\n');
  st = status(w, w.figures);
  assert.deepEqual(st.embeddedHashes, { 'figs/latency.png': sha256(LATENCY) }, 'the figure the passage tells is hashed under its src');
  assert.equal(st.derivedSrcs[c.id], 'figs/latency.png', 'the reply says the src is the passage\'s telling, not the disk\'s');
  assert.deepEqual(st.derivedSrcReasons, {});
  assert.equal('src' in readSidecar(sp).comments[0].target, false, 'a read never rewrites the sidecar');
  refused(w, { verb: 'retarget', path: w.figures, fence: fenceFor(st), args: { commentId: c.id, target: { kind: 'image', region: REGION2, src: 'figs/errors.png' } } }, 'figure-mismatch');
  r = ok(w, { verb: 'retarget', path: w.figures, fence: fenceFor(st), args: { commentId: c.id, target: { kind: 'image', region: REGION2, src: 'figs/latency.png' } } });
  assert.deepEqual(r.store.comments[0].target, { kind: 'image', region: REGION2, hash: sha256(LATENCY), src: 'figs/latency.png' });
  assert.deepEqual(r.store.comments[0].anchor, c.anchor);
});

// ── the kind and the standalone form are checked against the file ───

test('a target\'s kind must be what the named file is, and a region with no anchor must be on an image or a PDF: nothing is written for a pdf target on a png or a standalone region on markdown', () => {
  const w = world();
  const fence = { storeMtimeNs: '' };
  crashed(w, { verb: 'comment', path: w.chart, fence, args: { note: 'x', target: { kind: 'pdf', page: 7, region: REGION } } }, /target\.kind is "pdf" but ~\/notes-api\/docs\/chart\.png is an image/);
  crashed(w, { verb: 'comment', path: w.pdf, fence, args: { note: 'x', target: { kind: 'image', region: REGION } } }, /target\.kind is "image" but ~\/notes-api\/docs\/report\.pdf is a PDF/);
  crashed(w, { verb: 'comment', path: w.report, fence, args: { note: 'x', target: { kind: 'image', region: REGION } } },
    /a region with no anchor is on the file itself, and ~\/notes-api\/docs\/report\.md is not an image or a PDF/);
  // An embedded src whose extension the viewer never shows as media, and one embedded as a pdf: the kind check reads the src.
  const md = path.join(w.docs, 'kinds.md');
  const text = '# Kinds\n\n<img src="../secret.bin">\n\n![doc](report.pdf)\n\n![chart](chart.png)\n';
  fs.writeFileSync(md, text);
  const st = status(w, md);
  crashed(w, anchored(w, md, text, '<img src="../secret.bin">', 0, st, { kind: 'image', region: REGION, src: '../secret.bin' }), /the figure \.\.\/secret\.bin in ~\/notes-api\/docs\/kinds\.md is not an image or a PDF by its extension/);
  crashed(w, anchored(w, md, text, '![doc](report.pdf)', 0, st, { kind: 'image', region: REGION, src: 'report.pdf' }), /target\.kind is "image" but the figure report\.pdf in ~\/notes-api\/docs\/kinds\.md is a PDF/);
  noSidecar(w);
  // The matching kinds are written, with the page for the pdf.
  let r = ok(w, anchored(w, md, text, '![chart](chart.png)', 0, st, { kind: 'image', region: REGION, src: 'chart.png' }));
  assert.equal(r.store.comments[0].target.hash, sha256(CHART));
  r = ok(w, anchored(w, md, text, '![doc](report.pdf)', 0, r, { kind: 'pdf', page: 2, region: REGION, src: 'report.pdf' }));
  assert.deepEqual(r.store.comments[1].target, { kind: 'pdf', region: REGION, page: 2, hash: sha256(PDF), src: 'report.pdf' });
  assert.equal(mediaKind('x.PDF'), 'pdf');
  assert.equal(mediaKind('x.jpeg'), 'image');
  assert.equal(mediaKind('x.bin'), null);
  assert.equal(mediaKind('noext'), null);
});

// ── the region lies inside the unit square ──────────────────────────

test('a region that lies partly or wholly off the image is refused on comment and on retarget; one that reaches the edge exactly is kept', () => {
  const w = world();
  const off = [
    { x: 0.9, y: 0.9, w: 0.5, h: 0.5 },     // partly off
    { x: 1, y: 1, w: 1, h: 1 },             // wholly off
    { x: 1, y: 0, w: 0.0001, h: 0.5 },      // starts at the right edge
    { x: 0, y: 0.99996, w: 0.5, h: 0.0001 }, // y rounds to 1
  ];
  for (const region of off) {
    assert.throws(() => validateTarget({ kind: 'image', region }, false), (e) => e instanceof BadRequest && /must lie inside the image/.test(e.message), JSON.stringify(region));
    crashed(w, { verb: 'comment', path: w.chart, fence: { storeMtimeNs: '' }, args: { note: 'x', target: { kind: 'image', region } } }, /target\.region must lie inside the image: x \+ w and y \+ h must not exceed 1/);
  }
  noSidecar(w);
  const edge = { x: 0.9999, y: 0.5, w: 0.0001, h: 0.5 };
  assert.deepEqual(validateTarget({ kind: 'image', region: edge }, false).region, edge);
  let st = status(w, w.chart);
  let r = ok(w, { verb: 'comment', path: w.chart, fence: fenceFor(st), args: { note: 'At the edge.', target: { kind: 'image', region: edge } } });
  const c = r.store.comments[0];
  assert.deepEqual(c.target.region, edge);
  st = status(w, w.chart);
  const bytes = fs.readFileSync(r.storePath);
  crashed(w, { verb: 'retarget', path: w.chart, fence: fenceFor(st), args: { commentId: c.id, target: { kind: 'image', region: off[0] } } }, /must lie inside the image/);
  assert.deepEqual(fs.readFileSync(r.storePath), bytes);
  r = ok(w, { verb: 'retarget', path: w.chart, fence: fenceFor(st), args: { commentId: c.id, target: { kind: 'image', region: { x: 0, y: 0, w: 1, h: 1 } } } });
  assert.deepEqual(r.store.comments[0].target.region, { x: 0, y: 0, w: 1, h: 1 });
});

// ── the write verbs hash no more than the viewer shows ──────────────

test('comment and retarget hash under the viewer\'s cap: a figure past FILE_HASH_CAP refuses too-large with its size, nothing written, while one at the cap is hashed', () => {
  const w = world();
  // A sparse file: the size is what the check reads, and no bytes are written to disk for it.
  const big = path.join(w.docs, 'figs', 'big.png');
  fs.writeFileSync(big, '');
  fs.truncateSync(big, FILE_HASH_CAP + 1);
  const md = path.join(w.docs, 'big.md');
  const text = '# Big\n\n![big](figs/big.png)\n';
  fs.writeFileSync(md, text);
  let st = status(w, md);
  let r = refused(w, anchored(w, md, text, '![big](figs/big.png)', 0, st, { kind: 'image', region: REGION, src: 'figs/big.png' }), 'too-large');
  assert.match(r.error, /the figure figs\/big\.png in ~\/notes-api\/docs\/big\.md is 50\.0 MB, more than the 50\.0 MB the viewer shows/);
  assert.ok(r.error.endsWith('nothing was changed'), r.error);
  assert.equal(humanBytes(FILE_HASH_CAP + 1), '50.0 MB', 'the kernel\'s 50 MiB cap (file-comments-host-caps.test.mjs), as its own 413 prints it');
  noSidecar(w);
  // A standalone image past the cap: the same refusal, and status on it answers null with the reason.
  const bigImg = path.join(w.docs, 'huge.png');
  fs.writeFileSync(bigImg, '');
  fs.truncateSync(bigImg, FILE_HASH_CAP + 1);
  st = status(w, bigImg);
  assert.equal(st.fileHash, null);
  assert.match(st.fileHashReason, /huge\.png is 50\.0 MB, past the 50\.0 MB checked on each open/);
  r = refused(w, { verb: 'comment', path: bigImg, fence: fenceFor(st), args: { note: 'x', target: { kind: 'image', region: REGION } } }, 'too-large');
  assert.match(r.error, /~\/notes-api\/docs\/huge\.png is 50\.0 MB, more than the 50\.0 MB the viewer shows/);
  noSidecar(w);
  // At the cap exactly: hashed (the viewer shows a file of exactly its cap), on comment and on retarget.
  fs.truncateSync(bigImg, FILE_HASH_CAP);
  const zeros = createHash('sha256').update(Buffer.alloc(FILE_HASH_CAP)).digest('hex');
  st = status(w, bigImg);
  assert.equal(st.fileHash, zeros);
  assert.equal(st.fileHashReason, null);
  r = ok(w, { verb: 'comment', path: bigImg, fence: fenceFor(st), args: { note: 'x', target: { kind: 'image', region: REGION } } });
  const c = r.store.comments[0];
  assert.equal(c.target.hash, zeros);
  fs.truncateSync(bigImg, FILE_HASH_CAP + 1);
  st = status(w, bigImg);
  r = refused(w, { verb: 'retarget', path: bigImg, fence: fenceFor(st), args: { commentId: c.id, target: { kind: 'image', region: REGION2 } } }, 'too-large');
  assert.equal(readSidecar(storePathFor(w.root, bigImg)).comments[0].target.region.x, REGION.x, 'unchanged');
});

// ── an absolute src is contained like a relative one ────────────────

test('an absolute src inside the root is accepted and stored as written; one outside the root refuses unreadable, the home path tilde-collapsed in the text', () => {
  const w = world();
  const md = path.join(w.docs, 'abs.md');
  const inside = w.latency;                                       // /…/home/notes-api/docs/figs/latency.png
  const outside = w.banner;                                       // /…/home/shared/banner.png
  assert.ok(path.isAbsolute(inside) && path.isAbsolute(outside));
  const text = `# Absolute\n\n![in](${inside})\n\n![out](${outside})\n`;
  fs.writeFileSync(md, text);
  const st = status(w, md);
  const r = ok(w, anchored(w, md, text, `![in](${inside})`, 0, st, { kind: 'image', region: REGION, src: inside }));
  const c = r.store.comments[0];
  assert.equal(c.target.hash, sha256(LATENCY));
  assert.equal(c.target.src, inside, 'stored as the embed writes it');
  assert.deepEqual(r.embeddedHashes, { [inside]: sha256(LATENCY) });
  assert.deepEqual(r.embeddedHashReasons, {});
  const bad = refused(w, anchored(w, md, text, `![out](${outside})`, 0, r, { kind: 'image', region: REGION, src: outside }), 'unreadable');
  assert.match(bad.error, /~\/shared\/banner\.png is outside the project root ~\/notes-api/);
  assert.equal(bad.error.includes(w.home), false, 'no raw home path in the text');
  assert.equal(JSON.stringify(bad).includes(sha256(BANNER)), false);
  assert.equal(readSidecar(r.storePath).comments.length, 1);
});

// ── every null hash travels with its reason ─────────────────────────

test('a reply names why a figure\'s hash is null — deleted, moved out of the root, or past the budget — in embeddedHashReasons, keyed by src; fileHashReason does the same for a media file', () => {
  const w = world();
  let st = status(w, w.figures);
  assert.deepEqual(st.embeddedHashReasons, {}, 'nothing to hash, nothing to explain');
  assert.equal('fileHashReason' in st, false, 'a text file carries the embedded pair only');
  let r = ok(w, anchored(w, w.figures, w.figText, LATENCY_EMBED, 0, st, { kind: 'image', region: REGION, src: 'figs/latency.png' }));
  r = ok(w, anchored(w, w.figures, w.figText, ERRORS_EMBED, 0, r, { kind: 'image', region: REGION, src: 'figs/errors.png' }));
  assert.deepEqual(r.embeddedHashReasons, {}, 'both hashed: no reasons');
  // Deleted: the reason names the figure and the OS's ENOENT.
  fs.unlinkSync(w.errors);
  const raw = host(w, { verb: 'status', path: w.figures, args: {} });
  st = raw.json;
  assert.deepEqual(st.embeddedHashes, { 'figs/latency.png': sha256(LATENCY), 'figs/errors.png': null });
  assert.deepEqual(Object.keys(st.embeddedHashReasons), ['figs/errors.png']);
  assert.match(st.embeddedHashReasons['figs/errors.png'], /^the figure figs\/errors\.png in ~\/notes-api\/docs\/figures\.md was not hashed: .*ENOENT/);
  assert.equal(st.embeddedHashReasons['figs/errors.png'].includes(w.home), false, 'tilde-collapsed');
  assert.match(raw.stderr, /figs\/errors\.png .* was not hashed/, 'the same reason on stderr, which the kernel keeps on a failure');
  // Moved out of the root: a different reason under the same key.
  fs.writeFileSync(w.errors, ERRORS);
  fs.unlinkSync(w.latency);
  fs.symlinkSync(w.banner, w.latency);
  st = status(w, w.figures);
  assert.deepEqual(st.embeddedHashes, { 'figs/latency.png': null, 'figs/errors.png': sha256(ERRORS) });
  assert.match(st.embeddedHashReasons['figs/latency.png'], /is outside the project root/);
  assert.equal('figs/errors.png' in st.embeddedHashReasons, false);
  // Past the budget: the size and the budget, so this reads differently from a missing figure.
  fs.unlinkSync(w.latency);
  fs.writeFileSync(w.latency, LATENCY);
  st = status(w, w.figures, { FILE_COMMENTS_EMBEDDED_HASH_CAP: String(LATENCY.length) });
  assert.deepEqual(st.embeddedHashes, { 'figs/latency.png': sha256(LATENCY), 'figs/errors.png': null });
  assert.match(st.embeddedHashReasons['figs/errors.png'], /^the figure figs\/errors\.png \(\d+ bytes\) was not checked: the figures ~\/notes-api\/docs\/figures\.md's comments name are checked up to \d+ bytes together, and this one would pass it$/);
  // A media file: fileHashReason null when hashed, the reason when not.
  st = status(w, w.chart);
  assert.equal(st.fileHash, sha256(CHART));
  assert.equal(st.fileHashReason, null);
  assert.equal('embeddedHashReasons' in st, false);
  st = status(w, w.chart, { FILE_COMMENTS_HASH_CAP: String(CHART.length - 1) });
  assert.equal(st.fileHash, null);
  assert.match(st.fileHashReason, /^~\/notes-api\/docs\/chart\.png is \d+ bytes, past the \d+ bytes checked on each open, so whether it changed since its regions were drawn could not be checked$/);
  // Unreadable at this moment (a writer's race): the reason carries the OS text, tilde-collapsed.
  fs.unlinkSync(w.chart);
  fs.mkdirSync(w.chart);
  const dir = host(w, { verb: 'status', path: w.chart, args: {} });
  assert.equal(dir.json.ok, false, 'a directory at the path is unreadable before any hash: the reason field is for the race after that check');
  fs.rmdirSync(w.chart);
  fs.writeFileSync(w.chart, CHART);
  assert.equal(status(w, w.chart).fileHashReason, null);
});

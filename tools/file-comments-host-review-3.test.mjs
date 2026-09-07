// Slice 3 review pins for tools/file-comments-host.mjs (plans/file-review.md, "The contract" and
// "Slice 3: region comments on images"), two rules the rest of the host suite left unpinned:
//   * the figure's fence. `comment` with a target and `retarget` hash the figure's bytes as they are
//     at the write, and before this module fenced on the sidecar's mtime alone: a figure regenerated
//     between the drag and Enter was stamped with the NEW bytes' hash, every reply's fileHash /
//     embeddedHashes[src] equalled it, and the panel read a rectangle drawn on the old picture as
//     current on the new one — the one write the hash exists to catch (a regenerated figure marks
//     its region comments stale), missed at the moment it is made; a markdown file's own mtime
//     cannot fence a figure embedded in it. Now `fence.figureHash` — the hash the last reply carried
//     for that figure — is checked against the very bytes stamped, and a mismatch refuses
//     `figure-changed` with nothing written (no sidecar, no landmark beside a loose file). A request
//     naming no hash is taken as before: a caller has none for a figure no reply has hashed yet. A
//     hash this script never emitted is a caller bug, checked before any disk read; a figureHash on
//     a comment with no target is one too; `too-large` answers first, there being no hash to compare.
//   * passageFigure's "exactly one DISTINCT destination": a passage that embeds one figure twice (or
//     in two forms) still tells that figure, so a comment in the contract's src-less shape on it is
//     hashed, and a re-place naming no src lands — the plan-shape module covers two DIFFERENT figures,
//     none, and a gone passage, so the dedupe could be dropped with every test green.
// Same hermetic harness as file-comments-host-plan-shape.test.mjs: the synthetic `notes-api` world
// under a scratch directory, tiny PNGs generated at run time, the script driven as the kernel drives
// it. Run: node --test tools/file-comments-host-review-3.test.mjs
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

import { storePathFor } from '../vendor/track-changents/store-io.mjs';
import { FILE_HASH_CAP, logPathFor, statNs } from './file-comments-host.mjs';
import { tinyPng, sha256 } from '../tests/fixtures/file_comments/tiny-png.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const HOST = path.join(REPO, 'tools', 'file-comments-host.mjs');
const VENDOR = path.join(REPO, 'vendor', 'track-changents');
const FIX = path.join(REPO, 'tests', 'fixtures', 'file_comments');
const engine = createRequire(import.meta.url)(path.join(VENDOR, 'engine.js'));

const LATENCY = tinyPng(10, 20, 30);
const LATENCY_AGAIN = tinyPng(11, 22, 33);    // the figure regenerated: other bytes, same name
const LATENCY_THIRD = tinyPng(12, 24, 36);    // and again
const ERRORS = tinyPng(200, 30, 30);
const CHART = tinyPng(0, 120, 60);
const CHART_AGAIN = tinyPng(1, 120, 60);
const CHART_THIRD = tinyPng(2, 120, 60);

let SCRATCH;
before(() => { SCRATCH = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-fc-host-review-3-')); });
after(() => { try { fs.rmSync(SCRATCH, { recursive: true, force: true }); } catch { /* ignore */ } });

// <scratch>/wN/home/                  FILE_COMMENTS_HOME: "~" in every text the script prints
//   notes-api/.git/                   the landmark that makes notes-api a project
//   notes-api/docs/figures.md         the fixture with embedded figures (latency.png twice, on two lines)
//   notes-api/docs/figs/latency.png
//   notes-api/docs/figs/errors.png
//   notes-api/docs/chart.png          a standalone image
let worlds = 0;
function world() {
  const home = path.join(SCRATCH, `w${++worlds}`, 'home');
  const root = path.join(home, 'notes-api');
  const docs = path.join(root, 'docs');
  fs.mkdirSync(path.join(root, '.git'), { recursive: true });
  fs.mkdirSync(path.join(docs, 'figs'), { recursive: true });
  fs.copyFileSync(path.join(FIX, 'figures.md'), path.join(docs, 'figures.md'));
  fs.writeFileSync(path.join(docs, 'figs', 'latency.png'), LATENCY);
  fs.writeFileSync(path.join(docs, 'figs', 'errors.png'), ERRORS);
  fs.writeFileSync(path.join(docs, 'chart.png'), CHART);
  return {
    home, root, docs,
    figures: path.join(docs, 'figures.md'),
    figText: fs.readFileSync(path.join(FIX, 'figures.md'), 'utf8'),
    latency: path.join(docs, 'figs', 'latency.png'),
    errors: path.join(docs, 'figs', 'errors.png'),
    chart: path.join(docs, 'chart.png'),
  };
}

function env(w) {
  const e = { ...process.env, FILE_COMMENTS_HOME: w.home };
  delete e.TRACKCHANGES_ROOT;
  delete e.FILE_COMMENTS_HASH_CAP;
  delete e.FILE_COMMENTS_EMBEDDED_HASH_CAP;
  delete e.ROMP_SID;
  delete e.ROMP_SESSION_NAME;
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
  return Object.assign(r.json, { stderr: r.stderr });
}
function refused(w, req, code) {
  const r = host(w, req);
  assert.equal(r.code, 0, `a refusal exits 0; got ${r.code}: ${r.stderr}`);
  assert.ok(r.json && r.json.ok === false, `expected ok:false, got ${r.stdout}`);
  assert.equal(r.json.code, code, r.json.error);
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
function status(w, file) { return ok(w, { verb: 'status', path: file, args: {} }); }
function fenceFor(st) { return { storeMtimeNs: st.storeMtimeNs == null ? '' : st.storeMtimeNs }; }
function readSidecar(sp) { return JSON.parse(fs.readFileSync(sp, 'utf8')); }
function writeSidecar(sp, obj) { fs.writeFileSync(sp, JSON.stringify(obj, null, 2) + '\n'); }
function anchorAt(text, quote, nth) {
  let i = -1;
  for (let k = 0; k <= (nth || 0); k++) i = text.indexOf(quote, i + 1);
  assert.ok(i >= 0, `fixture lacks occurrence ${nth} of ${JSON.stringify(quote)}`);
  return { anchor: engine.makeAnchor(text, i, i + quote.length), hintOffset: i };
}
const LATENCY_EMBED = '![p95 latency](figs/latency.png)';
const REGION = { x: 0.12, y: 0.4, w: 0.35, h: 0.2 };
const REGION2 = { x: 0.5, y: 0.5, w: 0.25, h: 0.1 };
// The panel's request: a region on `file` anchored at the nth occurrence of `quote`, naming its src.
function panelComment(file, text, quote, nth, st, src, note) {
  const { anchor, hintOffset } = anchorAt(text, quote, nth);
  return { verb: 'comment', path: file, fence: fenceFor(st), args: { anchor, hintOffset, note: note || 'On the figure.', target: { kind: 'image', region: REGION, src } } };
}
// A region on a standalone image: no anchor, no src.
function standaloneComment(file, st, note) {
  return { verb: 'comment', path: file, fence: fenceFor(st), args: { note: note || 'This spike.', target: { kind: 'image', region: REGION } } };
}
// The re-place the panel sends for a card whose target carries no src: a target with no src.
function replaceNoSrc(file, st, id, region) {
  return { verb: 'retarget', path: file, fence: fenceFor(st), args: { commentId: id, target: { kind: 'image', region: region || REGION2 } } };
}
// A sidecar rewritten into the contract's shape: the named comments lose their `src`.
function stripSrc(sp, ids) {
  const disk = readSidecar(sp);
  for (const c of disk.comments) if (!ids || ids.includes(c.id)) delete c.target.src;
  writeSidecar(sp, disk);
  return disk;
}
const withFigure = (req, st, figureHash) => ({ ...req, fence: { ...fenceFor(st), figureHash } });
const CHANGED_RE = /changed on disk since it was shown — reload to see it as it is now, then draw the region again; nothing was changed$/;

// ── the figure's fence: a standalone image ──────────────────────────

test('a region comment fenced on the hash the person saw refuses figure-changed when the image was regenerated between the drag and Enter, writing nothing; fenced on the re-issued status\'s hash it lands with that hash; retarget is held to the same rule', () => {
  const w = world();
  const sp = storePathFor(w.root, w.chart);
  let st = status(w, w.chart);
  assert.equal(st.fileHash, sha256(CHART), 'the hash the panel holds for the picture it shows');
  // Regenerated after the picture was shown and before Enter: the host must not stamp these bytes as
  // the ones the person drew on.
  fs.writeFileSync(w.chart, CHART_AGAIN);
  const ref = refused(w, withFigure(standaloneComment(w.chart, st), st, st.fileHash), 'figure-changed');
  assert.match(ref.error, /^~\/notes-api\/docs\/chart\.png changed on disk/);
  assert.match(ref.error, CHANGED_RE);
  assert.equal(fs.existsSync(sp), false, 'a refused first comment mints no sidecar');
  assert.equal(fs.existsSync(logPathFor(sp)), false);
  // The panel re-issues status, shows the new picture, and the person draws again: the fence is the
  // new hash, the write lands, and what is stamped is what was shown.
  st = status(w, w.chart);
  assert.equal(st.fileHash, sha256(CHART_AGAIN));
  let r = ok(w, withFigure(standaloneComment(w.chart, st), st, st.fileHash));
  const id = r.store.comments[0].id;
  assert.deepEqual(r.store.comments[0].target, { kind: 'image', region: REGION, hash: sha256(CHART_AGAIN) });
  assert.equal(r.fileHash, r.store.comments[0].target.hash, 'current, and truthfully so');
  // A re-place after the figure changed again under the panel: the panel's hash is the last reply's,
  // the bytes are newer, and the re-place refuses rather than stamp them unseen.
  const bytes = fs.readFileSync(sp);
  fs.writeFileSync(w.chart, CHART_THIRD);
  const again = refused(w, withFigure(replaceNoSrc(w.chart, r, id), r, r.fileHash), 'figure-changed');
  assert.match(again.error, CHANGED_RE);
  assert.deepEqual(fs.readFileSync(sp), bytes, 'byte-identical after the refusal');
  st = status(w, w.chart);
  assert.equal(st.fileHash, sha256(CHART_THIRD));
  assert.equal(st.store.comments[0].target.hash, sha256(CHART_AGAIN), 'stale on the status, as the panel shows it');
  r = ok(w, withFigure(replaceNoSrc(w.chart, st, id), st, st.fileHash));
  assert.deepEqual(r.store.comments[0].target, { kind: 'image', region: REGION2, hash: sha256(CHART_THIRD) });
  assert.equal(r.fileHash, r.store.comments[0].target.hash);
  assert.deepEqual(r.log, [], 'a re-placed rectangle is not a decision');
  // A fence equal to the bytes is a fence, not a bypass: a hash of the right shape that is not the
  // bytes' refuses, whatever else is right.
  st = status(w, w.chart);
  refused(w, withFigure(standaloneComment(w.chart, st, 'Another.'), st, sha256(CHART)), 'figure-changed');
  assert.equal(readSidecar(sp).comments.length, 1);
});

test('a refused figure-changed on a loose image creates no .trackchanges/ beside it: the fence is checked before the landmark, like every refusal', () => {
  const w = world();
  const looseDir = path.join(w.home, 'loose');
  fs.mkdirSync(looseDir);
  const chart = path.join(looseDir, 'chart.png');
  fs.writeFileSync(chart, CHART);
  const st = status(w, chart);
  assert.equal(st.root, null);
  assert.equal(st.fileHash, sha256(CHART));
  fs.writeFileSync(chart, CHART_AGAIN);
  refused(w, withFigure(standaloneComment(chart, st), st, st.fileHash), 'figure-changed');
  assert.deepEqual(fs.readdirSync(looseDir), ['chart.png'], 'no landmark, no sidecar');
  // The same request with the current hash creates the landmark and lands.
  const st2 = status(w, chart);
  const r = ok(w, withFigure(standaloneComment(chart, st2), st2, st2.fileHash));
  assert.equal(r.root, looseDir);
  assert.equal(r.store.comments[0].target.hash, sha256(CHART_AGAIN));
});

// ── the figure's fence: a figure embedded in a markdown file ────────

test('an embedded figure regenerated between the drag and Enter refuses figure-changed under the embeddedHashes[src] fence while the markdown\'s own mtime never moved; a re-place in the contract\'s shape (no src) fences the figure its passage tells', () => {
  const w = world();
  let st = status(w, w.figures);
  assert.deepEqual(st.embeddedHashes, {}, 'no region comment yet names a figure, so the panel has no hash for one');
  // The first region on latency.png: the caller has no hash to give, and the write is taken as before.
  let r = ok(w, panelComment(w.figures, w.figText, LATENCY_EMBED, 0, st, 'figs/latency.png'));
  const sp = r.storePath;
  const first = r.store.comments[0].id;
  assert.deepEqual(r.embeddedHashes, { 'figs/latency.png': sha256(LATENCY) }, 'from here the panel holds the figure\'s hash');
  const mdNs = r.fileMtimeNs;
  // A second region on the same figure's other embed line, the figure regenerated between the drag
  // and Enter. The markdown did not change, so no fence on IT could have caught this.
  fs.writeFileSync(w.latency, LATENCY_AGAIN);
  const bytes = fs.readFileSync(sp);
  const second = panelComment(w.figures, w.figText, LATENCY_EMBED, 1, r, 'figs/latency.png', 'Appendix copy.');
  const ref = refused(w, withFigure(second, r, r.embeddedHashes['figs/latency.png']), 'figure-changed');
  assert.match(ref.error, /^the figure figs\/latency\.png in ~\/notes-api\/docs\/figures\.md changed on disk/);
  assert.match(ref.error, CHANGED_RE);
  assert.deepEqual(fs.readFileSync(sp), bytes, 'nothing written');
  assert.equal(statNs(w.figures), mdNs, 'the markdown\'s mtime is unmoved: the figure needs a fence of its own');
  // The re-issued status flips the first comment stale and carries the new hash; fenced on it, the
  // second comment lands with the bytes the panel now shows.
  st = status(w, w.figures);
  assert.equal(st.embeddedHashes['figs/latency.png'], sha256(LATENCY_AGAIN));
  assert.equal(st.store.comments[0].target.hash, sha256(LATENCY), 'the first comment reads stale now');
  r = ok(w, withFigure(second, st, st.embeddedHashes['figs/latency.png']));
  assert.equal(r.store.comments[1].target.hash, sha256(LATENCY_AGAIN));
  assert.equal(r.store.comments[1].target.src, 'figs/latency.png');
  // The contract's shape on the first comment: a re-place naming no src takes the passage's figure,
  // and the fence is checked against that figure's bytes like any other.
  stripSrc(sp, [first]);
  st = status(w, w.figures);
  assert.equal(st.derivedSrcs[first], 'figs/latency.png');
  fs.writeFileSync(w.latency, LATENCY_THIRD);
  const before = fs.readFileSync(sp);
  refused(w, withFigure(replaceNoSrc(w.figures, st, first), st, st.embeddedHashes['figs/latency.png']), 'figure-changed');
  assert.deepEqual(fs.readFileSync(sp), before);
  st = status(w, w.figures);
  r = ok(w, withFigure(replaceNoSrc(w.figures, st, first), st, st.embeddedHashes['figs/latency.png']));
  assert.deepEqual(r.store.comments[0].target, { kind: 'image', region: REGION2, hash: sha256(LATENCY_THIRD), src: 'figs/latency.png' });
  assert.deepEqual(r.embeddedHashes, { 'figs/latency.png': sha256(LATENCY_THIRD) });
});

// ── the fence's shape, and where it stands among the refusals ───────

test('fence.figureHash that is not a sha256 hex is a caller bug before any disk read; one on a comment with no target is too; a request naming none is taken as before; too-large answers before figure-changed', () => {
  const w = world();
  const sp = storePathFor(w.root, w.chart);
  let st = status(w, w.chart);
  // Not the shape this script emits: a crash, nothing written — even on a path that does not exist,
  // which shows the shape is checked before the file is opened.
  const ghost = path.join(w.docs, 'ghost.png');
  for (const bad of ['', 'abc', 'A'.repeat(64), sha256(CHART).toUpperCase(), 42, {}, []]) {
    crashed(w, { ...standaloneComment(w.chart, st), fence: { ...fenceFor(st), figureHash: bad } }, /fence\.figureHash must be the sha256 hex a reply carried/);
    crashed(w, { verb: 'comment', path: ghost, fence: { storeMtimeNs: '', figureHash: bad }, args: standaloneComment(ghost, st).args }, /fence\.figureHash must be/);
    crashed(w, { verb: 'retarget', path: w.chart, fence: { ...fenceFor(st), figureHash: bad }, args: { commentId: 'x', target: { kind: 'image', region: REGION } } }, /fence\.figureHash must be/);
  }
  assert.equal(fs.existsSync(sp), false);
  // A figure fence on a comment with no region: a caller bug, on a media file and on a text file.
  crashed(w, { verb: 'comment', path: w.chart, fence: { ...fenceFor(st), figureHash: st.fileHash }, args: { note: 'On the whole file.' } }, /fence\.figureHash fences the figure a region is on, and this comment has no target/);
  const stMd = status(w, w.figures);
  const { anchor, hintOffset } = anchorAt(w.figText, 'Error rates over the same window:', 0);
  crashed(w, { verb: 'comment', path: w.figures, fence: { ...fenceFor(stMd), figureHash: sha256(ERRORS) }, args: { anchor, hintOffset, note: 'A passage.' } }, /has no target/);
  assert.equal(fs.existsSync(storePathFor(w.root, w.figures)), false);
  // No fence at all: the write lands, as it did before this fence existed — the caller had no hash.
  fs.writeFileSync(w.chart, CHART_AGAIN);
  const r = ok(w, standaloneComment(w.chart, st));
  assert.equal(r.store.comments[0].target.hash, sha256(CHART_AGAIN), 'unfenced, the bytes as they are now');
  // A figure past the viewer's cap has no hash to compare: too-large, before the fence is consulted.
  const big = path.join(w.docs, 'big.png');
  fs.writeFileSync(big, '');
  fs.truncateSync(big, FILE_HASH_CAP + 1);
  const tooBig = refused(w, { verb: 'comment', path: big, fence: { storeMtimeNs: '', figureHash: sha256(CHART) }, args: standaloneComment(big, st).args }, 'too-large');
  assert.match(tooBig.error, /more than the 50\.0 MB the viewer shows/);
  assert.equal(fs.existsSync(storePathFor(w.root, big)), false);
});

// ── passageFigure: one destination embedded twice is one figure ─────

test('a passage that embeds one figure twice — two embeds, or two forms — tells that figure: a comment in the contract\'s shape on it is hashed under the src, nothing is left unknown, and a re-place naming no src lands', () => {
  const w = world();
  const md = path.join(w.docs, 'same.md');
  const twice = 'Same chart, two sizes: ![a](figs/latency.png) ![b](figs/latency.png)';
  const forms = 'Both forms: ![c](figs/errors.png) <img src="figs/errors.png" width="80">';
  const text = `# Same\n\n${twice}\n\n${forms}\n`;
  fs.writeFileSync(md, text);
  let st = status(w, md);
  let r = ok(w, panelComment(md, text, twice, 0, st, 'figs/latency.png'));
  const sp = r.storePath;
  const onTwice = r.store.comments[0].id;
  st = status(w, md);
  r = ok(w, panelComment(md, text, forms, 0, st, 'figs/errors.png', 'On the errors chart.'));
  const onForms = r.store.comments[1].id;
  const disk = stripSrc(sp);
  for (const c of disk.comments) assert.deepEqual(Object.keys(c.target), ['kind', 'region', 'hash'], 'the contract\'s shape');
  const bytes = fs.readFileSync(sp);

  st = status(w, md);
  assert.deepEqual(st.derivedSrcs, { [onTwice]: 'figs/latency.png', [onForms]: 'figs/errors.png' }, 'one distinct destination each, however many times it is embedded');
  assert.deepEqual(st.derivedSrcReasons, {}, 'nothing is "cannot be told"');
  assert.doesNotMatch(JSON.stringify(st) + st.stderr, /embeds figs\/latency\.png, figs\/latency\.png/, 'the same figure twice is not two figures');
  assert.equal(st.store.comments[0].target.src, 'figs/latency.png');
  assert.equal(st.store.comments[1].target.src, 'figs/errors.png');
  assert.deepEqual(st.embeddedHashes, { 'figs/latency.png': sha256(LATENCY), 'figs/errors.png': sha256(ERRORS) }, 'hashed under the src, so the stale check has its figure');
  assert.deepEqual(st.embeddedHashReasons, {});
  assert.deepEqual(fs.readFileSync(sp), bytes, 'a read never rewrites the sidecar');

  // The panel's re-place on such a card names no src: the passage's one figure is taken.
  r = ok(w, replaceNoSrc(md, st, onTwice, REGION2));
  assert.deepEqual(r.store.comments[0].target, { kind: 'image', region: REGION2, hash: sha256(LATENCY), src: 'figs/latency.png' });
  st = status(w, md);
  r = ok(w, replaceNoSrc(md, st, onForms, REGION2));
  assert.deepEqual(r.store.comments[1].target, { kind: 'image', region: REGION2, hash: sha256(ERRORS), src: 'figs/errors.png' });
  assert.deepEqual(r.derivedSrcs, {}, 'both srcs stored now');
  assert.deepEqual(r.derivedSrcReasons, {});
});

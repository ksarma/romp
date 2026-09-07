// The plan states what the Slice 3 build stores and reads, and the host still does it
// (plans/file-review.md: "The contract", the `fileComments` op, "Slice 3: region comments on
// images", "Security posture", "Risks", "Tests", decision 13).
//
// The Slice 3 build stored a fifth target key, `src`, and had the host resolve and hash a figure
// path the CLIENT names, two departures from the plan that its commit messages and the host's own
// header recorded while the plan kept the four-key shape and said the host acts only on paths the
// kernel resolved (review finding, 2026-09-06). Decision 13 makes the plan the source for the later
// README offer that documents `target` to the other hosts, and Security posture is what a review of
// the host reads, so a reader of either wrote the wrong shape and the wrong read surface. The plan
// now says both, and this module keeps it saying what the host does: every statement the plan
// makes about the target's keys, the verbs, the refusal codes, the caps and the bound on the figure
// read is checked against tools/file-comments-host.mjs (the exported shape check for behavior, the
// source text for the codes and the reply fields, the constants for the caps); the figure fence
// (`fence.figureHash`, `figure-changed`) against the host, the kernel's pass-through and whether
// the panel sends it; and the poll's figures against the panel model, so a change to one side
// without the other fails here. Synthetic: no session data, only the repo's own text.
// Run: node --test tools/file-review-plan.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { validateTarget, FILE_HASH_CAP, EMBEDDED_HASH_CAP } from './file-comments-host.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const read = (...parts) => fs.readFileSync(path.join(REPO, ...parts), 'utf8');

const plan = read('plans', 'file-review.md');
const host = read('tools', 'file-comments-host.mjs');
const kernel = read('kernel', 'kernel.py');
const panel = read('ui', 'webview', 'file-comments.ts');
const model = read('ui', 'webview', 'file-comments-model.ts');

// The text between two headings, hard wraps collapsed so an assertion survives a rewrap.
function section(from, to) {
  const a = plan.indexOf(from);
  assert.ok(a >= 0, `heading ${JSON.stringify(from)} not found in the plan`);
  const b = plan.indexOf(to, a + from.length);
  assert.ok(b > a, `heading ${JSON.stringify(to)} not found after ${JSON.stringify(from)}`);
  return plan.slice(a, b).replace(/\s+/g, ' ');
}
const contract = section('## The contract: the track-changents sidecar', '## Kernel: two ops and a host script');
const op = section('## Kernel: two ops and a host script', '### The message to the session');
const ux = section('### Commenting from either view, and in every format', '### The viewer seam');
const slice3 = section('### Slice 3: region comments on images', '### Slice 4: PDFs rendered in the viewer');
const posture = section('## Security posture', '## Doctrines this respects');
const risks = section('## Risks', '## Tests');
const tests = section('## Tests', '## Docs');
const decisions = section('## Decisions', '## Open questions for the user');

const mb = (n) => `${n / 1_000_000} MB`;
// the viewer's cap is the kernel's _MEDIA_MAX_BYTES, a power-of-two 50 MiB (file-comments-host-caps.test.mjs), which the plan
// and the kernel's own 413 both call 50 MB
const mib = (n) => `${n / (1024 * 1024)} MB`;
const region = { x: 0.1, y: 0.2, w: 0.3, h: 0.4 };

// ── the target's shape ──────────────────────────────────────────────

test('the contract states the five-key shape, and the host validates exactly those keys in that order', () => {
  assert.ok(contract.includes('`target: {kind: "image"|"pdf", region: {x, y, w, h}, page?, hash, src?}`'), 'the contract names src? after hash');
  assert.ok(!contract.includes('page?, hash}`'), 'the four-key shape the plan first stated is gone');
  // Behavior: an embedded figure's target takes src; a standalone one refuses it; the keys the
  // shape check hands on are the plan's, in the plan's order, with hash stamped between page and src.
  assert.deepEqual(Object.keys(validateTarget({ kind: 'image', region, src: 'figs/a.png' }, true)), ['kind', 'region', 'src']);
  assert.deepEqual(Object.keys(validateTarget({ kind: 'pdf', region, page: 2, src: 'figs/a.pdf' }, true)), ['kind', 'region', 'page', 'src']);
  assert.deepEqual(Object.keys(validateTarget({ kind: 'image', region }, false)), ['kind', 'region']);
  assert.throws(() => validateTarget({ kind: 'image', region, src: 'figs/a.png' }, false), /anchor/);
  assert.throws(() => validateTarget({ kind: 'image', region }, true), /src/);
  assert.ok(/out\.hash = hashed\.hash;\s*\n\s*if \(target\.src != null\) out\.src = target\.src;/.test(host), 'stampTarget writes hash, then src, last');
  assert.ok(slice3.includes('`{kind, region, page?, hash, src?}` in that key order'));
});

test('the contract says the host, not the client, computes the hash, and that the src-less shape is read', () => {
  assert.ok(contract.includes('The host script, never the client, computes `hash`'));
  assert.ok(contract.includes('names no `src`'));
  assert.ok(contract.includes('never writes the sidecar on a read'));
  assert.ok(host.includes('function derivedSrcsFor('), 'the host still derives a src-less target\'s figure from its passage');
  // "exactly one distinct figure": passageFigure dedupes the passage's destinations before counting.
  assert.ok(contract.includes('embeds exactly one distinct figure (one figure embedded twice still tells)'));
  assert.ok(slice3.includes('several distinct ones (one figure embedded twice still tells)'));
  const pf = host.slice(host.indexOf('function passageFigure('), host.indexOf('function namesFigureByPassage('));
  assert.ok(/new Set\(embeds[\s\S]*?dests\.length === 1/.test(pf), 'passageFigure counts distinct destinations');
  assert.ok(contract.includes('in the five-key shape above'), 'the README offer (decision 13) documents the shape as built');
  assert.ok(decisions.includes('The Slice 3 build stores a fifth key, `src`'));
});

// ── the op: reply fields, verbs, codes ──────────────────────────────

test('every hash field the reply listing names is one the host sets, and the paragraph explains each', () => {
  const fields = ['fileHash', 'fileHashReason', 'embeddedHashes', 'embeddedHashReasons', 'derivedSrcs', 'derivedSrcReasons'];
  for (const f of fields) {
    assert.ok(op.includes(`${f}?`), `the reply listing names ${f}?`);
    assert.ok(host.includes(`out.${f} =`), `the host sets out.${f}`);
    assert.ok(op.includes(`\`${f}\``), `the field paragraph explains ${f}`);
  }
  assert.ok(op.includes('Null is unknown, never stale'));
});

test('the verb list names retarget, and the codes list names Slice 3\'s three refusals the host raises', () => {
  assert.ok(op.includes('Slice 3: `retarget {commentId, target}`'));
  assert.ok(host.includes('function doRetarget('));
  assert.ok(op.includes('not appended to the comments log'));
  for (const code of ['figure-mismatch', 'no-figure', 'figure-changed']) {
    assert.ok(op.includes(`\`${code}\``), `the codes paragraph names ${code}`);
    assert.ok(host.includes(`'${code}'`), `the host names ${code}`);
  }
  // Where each is raised: figure-mismatch and figure-changed directly; no-figure is passageFigure's
  // code, raised through it by retarget (`new Refusal(f.code`).
  assert.ok(host.includes("new Refusal('figure-mismatch'"));
  assert.ok(host.includes("new Refusal('figure-changed'"));
  assert.ok(host.includes("code: 'no-figure'") && host.includes('new Refusal(f.code'));
});

// ── the figure fence ────────────────────────────────────────────────

test('the op names fence.figureHash, optional, checked by the host when carried and passed through whole by the kernel', () => {
  assert.ok(op.includes('configMtimeNs?: str|"", figureHash?: str}'), 'the request shape carries figureHash?');
  assert.ok(op.includes('`comment` with a `target` and `retarget`, also fence on the figure\'s bytes through `figureHash`'));
  assert.ok(op.includes('This key is optional where the mtime keys are not'));
  assert.ok(op.includes('`figure-changed` is not retried'));
  assert.ok(host.includes('function figureFence('), 'the host reads the fence');
  assert.ok(/const v = ctx\.fence\.figureHash;\s*\n\s*if \(v == null\) return null;/.test(host), 'absent is allowed');
  assert.ok(/if \(figureHash != null && hashed\.hash !== figureHash\) \{\s*\n\s*throw new Refusal\('figure-changed'/.test(host), 'a carried hash is compared with the bytes stamped');
  assert.ok(kernel.includes('"fence": fence if isinstance(fence, dict) else None'), 'the kernel forwards the fence object whole, so the key reaches the host');
  assert.ok(!/fence\[["']storeMtimeNs["']\]/.test(kernel), 'the kernel does not pick fence keys');
});

test('the build note says the panel sends figureHash on comment-with-target and retarget, and the panel source agrees', () => {
  assert.ok(slice3.includes('when the request\'s fence carries `figureHash`, `figure-changed` unless the bytes hashed are the ones it names'));
  assert.ok(slice3.includes('the same fence applies'), 'retarget is held to the fence too');
  assert.ok(slice3.includes('The panel sends `figureHash` on `comment` with a target and on `retarget`'), 'the build note states the panel side');
  assert.ok(slice3.includes('none when the status holds none'), '…and the case it cannot arm');
  assert.ok(slice3.includes('A `figure-changed` refusal is never retried'), '…and that the refusal is final for that write');
  assert.equal(slice3.includes('sends the three mtime keys only, so none of its requests is fenced this way yet'), false, 'the unarmed-fence sentence is gone');
  // the panel: the two verbs, the hash from the status the model reads (figureFenceHash), no retry on figure-changed
  assert.ok(/const FIGURE_VERBS = new Set\(\["comment", "retarget"\]\);/.test(panel), 'the verbs that write about a figure');
  assert.ok(/const fh = FIGURE_VERBS\.has\(verb\) && args\.target \? figureFenceHash\(s, args\.target as Target\) : null;\s*\n\s*if \(fh\) fence\.figureHash = fh;/.test(panel), 'the fence carries the hash the status holds, and only then');
  assert.ok(/else if \(e\.code === FIGURE_CHANGED\) \{[^}]*this\.ctx\.reload\(\);\s*\n\s*await this\.refresh\(\);\s*\n\s*\}/.test(panel), 'figure-changed: re-read the view and the comments, no retry');
  assert.ok(!/MOVED = new Set\(\[[^\]]*figure-changed/.test(panel), 'figure-changed is not a moved fence: a retry would stamp the new bytes');
  assert.ok(/export function figureFenceHash\(/.test(model));
  assert.ok(/const v = target\.src \? \(s\.embeddedHashes && typeof s\.embeddedHashes === "object" \? s\.embeddedHashes\[target\.src\] : undefined\) : s\.fileHash;/.test(model), 'fileHash for a standalone picture, embeddedHashes[src] for an embedded one — the reading regionState compares with');
});

// ── the poll: open region comments only ─────────────────────────────

test('the plan counts the poll\'s figures as the OPEN region comments\' figures, as the model does', () => {
  assert.ok(slice3.includes('every figure a text file\'s open region comments name'));
  assert.ok(slice3.includes('a figure only resolved comments name is not watched'));
  assert.ok(risks.includes('plus one per figure the file\'s open region comments name (Slice 3)'), 'the poll\'s cost counts the open comments\' figures');
  const ft = model.slice(model.indexOf('export function figureTargets('));
  assert.ok(/if \(!c \|\| c\.resolved\) continue;/.test(ft.slice(0, ft.indexOf('\n}\n') + 1)), 'figureTargets skips resolved comments');
});

test('the poll\'s figure baseline is the status reply\'s embeddedMtimes, in the plan, the host and the panel alike', () => {
  assert.ok(slice3.includes('the reply carries each named figure\'s mtime from the read its hash came from (`embeddedMtimes`, by src, absent where the figure could not be read), which seeds the poll\'s baseline for it'), 'the build note states the baseline');
  assert.ok(risks.includes('takes its baseline from every `fileCommentsResult` (the file\'s `fileMtimeNs`, the figures\' `embeddedMtimes`)'), 'the Risks bullet counts the figures among what a reply re-baselines');
  assert.ok(/out\.embeddedMtimes = eh\.mtimes;/.test(host), 'the host puts the mtimes on every text-file reply');
  assert.ok(/mtimes\[src\] = r\.mtimeNs;/.test(host), '…from the same read as the hash, whatever the hash');
  assert.ok(/const st = fs\.fstatSync\(fd, \{ bigint: true \}\);/.test(host), 'nanoseconds need a bigint stat: a double rounds two adjacent writes onto one value');
  assert.ok(/export function figureBaseline\(/.test(model));
  assert.ok(/this\.figureBase = figureBaseline\(s, this\.ctx\.path, this\.figureBase\);/.test(panel), 'applyStatus seeds the figures\' baseline from the reply, beside pollBaseline');
});

// ── Slice 3's build note and the UX paragraph ───────────────────────

test('Slice 3 carries a build note whose caps are the host\'s constants and the kernel\'s media cap', () => {
  assert.ok(slice3.includes('The Slice 3 build (2026-09-06), host side'));
  assert.ok(slice3.includes(`\`too-large\` past the ${mib(FILE_HASH_CAP)} the viewer shows`));
  assert.ok(slice3.includes(`one ${mb(EMBEDDED_HASH_CAP)} budget per call`));
  const m = /^_MEDIA_MAX_BYTES = ([0-9_]+) \* ([0-9_]+) \* ([0-9_]+)/m.exec(kernel);
  assert.ok(m, 'the kernel names its media cap');
  assert.equal(Number(m[1]) * Number(m[2]) * Number(m[3]), FILE_HASH_CAP, 'the write-verb cap is the most the viewer shows');
  assert.ok(slice3.includes('`target {kind: "image", region, hash, src?}`'), 'the acceptance line carries src?');
  assert.ok(slice3.includes('`kernel.py` is unchanged'));
});

test('the UX paragraph no longer says region comments are still to arrive', () => {
  assert.ok(!ux.includes('arrive in Slices 3 and 4'));
  assert.ok(ux.includes('on images from Slice 3'));
});

// ── Security posture: the read surface and its bound ────────────────

test('Security posture states the client-named figure path, that it is only read, and every check the host makes', () => {
  assert.ok(posture.includes('the one class of path it resolves itself'), 'the kernel-resolved-paths sentence is qualified');
  assert.ok(posture.includes('From Slice 3 the host also reads one class of path the kernel did not resolve'));
  assert.ok(posture.includes("the figure a region comment's `target.src` names (the Slice 3 build, 2026-09-06)"));
  assert.ok(posture.includes('The client names that path on `comment` and on `retarget`'));
  assert.ok(posture.includes('It is only ever read, to hash it'));
  // Each bound the posture names, against the host's resolveSrc / hashRegular / stampTarget.
  assert.ok(posture.includes('refused when it is a URL') && /is a URL, not a file in the project/.test(host));
  assert.ok(posture.includes('confirmed by realpath to lie inside the project root') && host.includes('fs.realpathSync(rootDir)'));
  assert.ok(posture.includes('not out through a symlink'));
  assert.ok(posture.includes('to be a regular file, opened non-blocking') && host.includes('fs.constants.O_NONBLOCK'));
  assert.ok(posture.includes('a figure the anchored passage embeds (`figure-mismatch`)') && host.includes('function checkEmbedNamesSrc('));
  assert.ok(posture.includes(`under the ${mib(FILE_HASH_CAP)} the viewer shows, refused before a byte is read`));
  assert.ok(posture.includes(`one ${mb(EMBEDDED_HASH_CAP)} budget per call`));
  assert.ok(posture.includes('decoded as the viewer decodes it') && host.includes('function decodeSrc('));
});

test('Security posture says the reply hashes what the sidecar holds, on status, and states the trade', () => {
  // The reply-side read has no figure-mismatch gate: embeddedHashesFor hashes every stored src.
  const eh = host.slice(host.indexOf('function embeddedHashesFor('), host.indexOf('// ── regions: the embeds a passage holds'));
  assert.ok(eh.includes('hashRegular(resolveSrc(ctx, rootDir, src), budget)'));
  assert.ok(!eh.includes('checkEmbedNamesSrc'), 'the reply does not check the passage (the posture says so)');
  assert.ok(posture.includes('On a reply the host hashes every in-root regular file the sidecar\'s srcs name, of any extension'));
  assert.ok(posture.includes('runs on `status` too, outside the consent gate'));
  assert.ok(posture.includes('can learn the sha256 of any regular file inside the project root by naming it there, never its bytes'));
  assert.ok(posture.includes('the Risks bullet on figure paths names the trade'));
  assert.ok(risks.includes('**A figure path the client names** (Slice 3)'));
  assert.ok(risks.includes('refusing such srcs on a reply is the follow-up'));
});

// ── Tests: the plan names the modules that exist ────────────────────

test('the Tests section names Slice 3\'s host modules and this pin, and they exist', () => {
  for (const f of ['file-comments-host-regions.test.mjs', 'file-comments-host-targets.test.mjs', 'file-comments-host-embeds.test.mjs', 'file-comments-host-plan-shape.test.mjs', 'file-comments-host-review-3.test.mjs', 'file-review-plan.test.mjs']) {
    assert.ok(fs.existsSync(path.join(HERE, f)), `${f} exists`);
  }
  assert.ok(tests.includes('`tools/file-comments-host-regions.test.mjs`, `-targets`, `-embeds`, `-plan-shape`, `-review-3`'));
  assert.ok(tests.includes('the figure fence: `figure-changed`'), 'the Tests section says what the review-3 module pins');
  assert.ok(read('tools', 'file-comments-host-review-3.test.mjs').includes("'figure-changed'"), 'and it pins figure-changed');
  assert.ok(tests.includes('`tools/file-review-plan.test.mjs`'));
});

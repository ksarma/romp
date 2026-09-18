// The Slice 5 build note's pointers at decision 52 (2026-09-18; plans/markdown-viewer.md, the Slice 5 note's item 4).
// The note recorded two divergences between the anchor map's reader and the DOM: an inline `<textarea>` left open, which
// the reader read to its block's end where the parser read on, and an `<annotation-xml>` whose encoding value carries a
// blank with a `<b>` left open inside it, where the reader read `ma8 y8` against a DOM showing `ma8 x y8`. Decision 52 of
// plans/file-review.md renders an inline start tag with no end tag in its block as its own characters on both sides, so
// both are agreements now and anchor-map-html-text-browser.test.ts holds them among its shapes, its recorded divergences
// the `/>` forms alone. The plan keeps a slice's history as written and marks a superseded sentence with a pointer in
// place ("history since ..."), the form the Slice 5 and Slice 8 notes use elsewhere; this module holds the four pointers
// to the record they cite and to the test module they describe, so a later move of either shape is seen here.
// Synthetic: the repo's own text only. Run: node --test tools/markdown-viewer-plan-decision52-pointers.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const read = (...parts) => fs.readFileSync(path.join(REPO, ...parts), 'utf8');
const flat = (s) => s.replace(/\s+/g, ' ');

const viewerPlan = read('plans', 'markdown-viewer.md');
const reviewPlan = flat(read('plans', 'file-review.md'));
const browserSuite = read('ui', 'webview', 'anchor-map-html-text-browser.test.ts');
// The reader's comment is hard-wrapped with a `//` on every line; the markers are dropped before the flatten.
const map = flat(read('ui', 'webview', 'anchor-map.ts').replace(/\r?\n[ \t]*\/\/ ?/g, ' '));

// The Slice 5 build note, hard wraps collapsed so an assertion survives a rewrap.
function slice5() {
  const from = '### Slice 5: comments anchor on real notes';
  const to = '### Slice 6: reaching a section without scrolling';
  const a = viewerPlan.indexOf(from);
  assert.ok(a >= 0, `heading ${JSON.stringify(from)} not found in the plan`);
  const b = viewerPlan.indexOf(to, a + from.length);
  assert.ok(b > a, `heading ${JSON.stringify(to)} not found after ${JSON.stringify(from)}`);
  return flat(viewerPlan.slice(a, b));
}

const POINTERS = [
  // :3061, the reader's rule for an RCDATA element left open across blocks
  'is read to its block\'s end where the parser reads on (history since decision 52 of plans/file-review.md, 2026-09-18, for the start tag written in prose with no end tag in its block, which is literal text on both sides now, md-literal-tags.ts; the divergence is left to a `<textarea/>` or a `<plaintext/>` written with the self-closing syntax, which the parser opens);',
  // :3087, the ma8 breakout sentence
  'the breakout class as recorded (round 7 allowed the blanks and dropped the block\'s rest; history since decision 52 of plans/file-review.md, 2026-09-18: the `<b>` with no end tag in its block is literal text inside the dropped math on both sides, so the DOM shows `ma8 y8` as the reader does, and anchor-map-html-text-browser.test.ts holds the shape as an agreement, its recorded divergences the `/>` forms alone);',
  // :3182, the browser suite's round-5 entry in the tests roster
  'the plan\'s recorded open-textarea divergence pinned on both sides (history since decision 52 of plans/file-review.md, 2026-09-18: the open `<textarea>` is literal text on both sides and one of the module\'s agreed shapes, its recorded divergences the `/>` forms alone);',
  // :3196, the suite's round-8 entry in the tests roster
  'the reader\'s `ma8 y8` against the DOM\'s `ma8 x y8` (history since decision 52 of plans/file-review.md, 2026-09-18: an agreed shape now, `ma8 y8` on both sides), each red over a git archive of 99e7e2d0c)',
];

test('the Slice 5 note marks its two recorded divergences as history since decision 52, in place, at all four sentences', () => {
  const note = slice5();
  for (const p of POINTERS) assert.ok(note.includes(p), `pointer missing from the Slice 5 note: ${p.slice(0, 80)}`);
  // The sentences the pointers annotate are still there as written: history is marked, not rewritten.
  assert.ok(note.includes('an RCDATA element left open across blocks (`<textarea>`, `<plaintext>`) is read to its block\'s end where the parser reads on'));
  assert.ok(note.includes('`ma8 y8` against a DOM showing `ma8 x y8`, the breakout class as recorded'));
  assert.ok(note.includes('the reader\'s `ma8 y8` against the DOM\'s `ma8 x y8`'));
  assert.equal((note.match(/history since decision 52 of plans\/file-review\.md, 2026-09-18/g) || []).length, 4, 'four pointers, one per sentence');
});

test('the pointers use plain prose: no em dash', () => {
  for (const p of POINTERS) assert.ok(!p.includes('\u2014'), 'em dash');
});

test('decision 52 says what the pointers cite: the two Slice 5 divergences are agreements, the `/>` forms keep theirs', () => {
  assert.ok(reviewPlan.includes('Two divergences the Slice 5 build note of plans/markdown-viewer.md recorded (item 4) are agreements now: an inline `<textarea>` left open, and an `<annotation-xml>` whose encoding value carries a blank with a `<b>` left open inside it; the `/>` forms keep the divergence, since the self-closing syntax stays HTML.'));
});

// The browser suite's SHAPES entries are agreements (reader and DOM read the same `shown`); its RECORDED entries are
// divergences pinned on both sides. The two shapes the pointers describe must stand among the agreements, and RECORDED
// must hold neither: an open `<textarea>` there or an `ma8` entry would make the pointers false.
function block(name) {
  const a = browserSuite.indexOf(`const ${name}`);
  assert.ok(a >= 0, `${name} not found in the browser suite`);
  const b = browserSuite.indexOf('\n];', a);
  assert.ok(b > a, `${name} has no closing bracket`);
  return browserSuite.slice(a, b);
}

test('the browser suite holds the open textarea and the ma8 shape as agreements, and records only the `/>` forms', () => {
  const shapes = block('SHAPES');
  assert.ok(shapes.includes('src: "Lead <textarea>open *x* tail\\n", quotes: [{ from: "Lead", to: "tail", shown: "Lead <textarea>open x tail" }]'),
    'the open textarea is a SHAPES entry whose shown text keeps the start tag as characters');
  assert.ok(shapes.includes('src: "ma8 <math><annotation-xml encoding=\\"text/html \\"><b>x</math> y8\\n", quotes: [{ from: "ma8", to: "y8", shown: "ma8 y8" }]'),
    'the ma8 shape is a SHAPES entry showing `ma8 y8`');
  const recorded = block('RECORDED');
  assert.ok(!recorded.includes('ma8'), 'RECORDED holds no ma8 entry');
  const srcs = [...recorded.matchAll(/src: "((?:[^"\\]|\\.)*)"/g)].map((m) => m[1]);
  assert.ok(srcs.length > 0, 'RECORDED has entries');
  for (const src of srcs) {
    for (const tag of src.matchAll(/<(textarea|plaintext|title|noscript)(\/?)>/g)) {
      assert.equal(tag[2], '/', `a RECORDED src opens <${tag[1]}> without the self-closing syntax: ${src}`);
    }
  }
  const doc = browserSuite.slice(0, browserSuite.indexOf('const RECORDED'));
  assert.ok(doc.includes('The `/>` forms keep the divergence: the self-closing syntax stays HTML, which the parser opens.'),
    'RECORDED\'s doc comment says the `/>` forms are what it keeps');
});

test('the reader\'s comment in anchor-map.ts says the same as the RCDATA pointer', () => {
  assert.ok(map.includes('an RCDATA element left open across blocks (a `<textarea/>` or a `<plaintext/>` written with the self-closing syntax, which the parser opens; a start tag with no end tag in its block is literal text since decision 52, md-literal-tags.ts) is read to its block\'s end where the parser reads on'));
});

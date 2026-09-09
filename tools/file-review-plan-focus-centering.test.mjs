// The focus follow-on's paragraph (plans/file-review.md, Slice 2) records when centerOn gives up centering the mark and
// scrolls the least that shows the card's end instead. The verification review (2026-09-09) found the record narrowing
// that fallback to a focused card taller than the track, while the code takes it whenever the card's end would fall past
// the track's box with the mark at the body's center — with the card level with its mark, a card taller than half the
// body's height less the footer's and the gap, well short of the track's height — and the panel tests drive an open card
// that fits the track through it. This module holds the corrected account to centerOn's condition and to the fixtures'
// geometry, so the two cannot drift apart again. Synthetic: only the repo's own text.
// Run: node --test tools/file-review-plan-focus-centering.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const read = (...p) => fs.readFileSync(path.join(REPO, ...p), 'utf8');
const plan = read('plans', 'file-review.md');
const panel = read('ui', 'webview', 'file-comments.ts');
const layout = read('ui', 'webview', 'card-layout.ts');
const focusTest = read('ui', 'webview', 'file-comments-focus.test.ts');
const fixesTest = read('ui', 'webview', 'file-comments-margin-fixes.test.ts');

// The text between two markers, hard wraps collapsed so an assertion survives a rewrap.
function between(from, to) {
  const a = plan.indexOf(from);
  assert.ok(a >= 0, `${JSON.stringify(from)} not found in the plan`);
  const b = plan.indexOf(to, a + from.length);
  assert.ok(b > a, `${JSON.stringify(to)} not found after ${JSON.stringify(from)}`);
  return plan.slice(a, b).replace(/\s+/g, ' ');
}
const note = between('The focus follow-on (2026-09-08):', 'The anchors follow-on (2026-09-07):');
const centerOn = (() => {
  const a = panel.indexOf('private centerOn(key: string): boolean {');
  assert.ok(a >= 0, 'the panel has centerOn');
  return panel.slice(a, panel.indexOf('\n  }\n', a));
})();

/** The numbers a `const A = 1, B = 2, ...` line declares, by name; TRACK is derived, so it is computed as the line does. */
function geometry(src, name) {
  const m = src.match(/^const ROW = .*TRACK = BODY_VIEW - OFFSET - FOOTER;/m);
  assert.ok(m, name + ': the fixture geometry line');
  const g = {};
  for (const [, k, v] of m[0].matchAll(/(\w+) = (\d+)/g)) g[k] = Number(v);
  g.TRACK = g.BODY_VIEW - g.OFFSET - g.FOOTER;
  return g;
}
const gapDecl = layout.match(/export const CARD_GAP = (\d+);/);
assert.ok(gapDecl, 'card-layout.ts declares CARD_GAP');
const CARD_GAP = Number(gapDecl[1]);

test('the paragraph states the fallback\'s trigger as centerOn tests it: the card\'s end past the track\'s box with the mark centered, not the card\'s height against the track\'s', () => {
  assert.ok(note.includes('the least-scroll fallback stays for a focused card taller than the track has room for below the centered mark'));
  assert.ok(note.includes('where the card\'s end would fall past the track\'s box with the mark at the body\'s center, the body scrolls the least that shows the card\'s end, and the mark lands above the center with the card whole and level beside it'));
  assert.ok(note.includes('so the fallback fires for an open card that fits the track with room to spare, not only for a card taller than the track'));
  // the code: the centered scroll, the least scroll that shows the card's end, and the comparison between the two
  assert.ok(centerOn.includes('let want = markY - view / 2;'), 'the centered scroll');
  assert.ok(centerOn.includes('const showCard = p.top + p.height + CARD_GAP - track.clientHeight;'), 'the least scroll that shows the card\'s end');
  assert.ok(centerOn.includes('if (showCard > want) want = Math.min(showCard, markY - CARD_GAP);'), 'the fallback, taken on that comparison');
  assert.ok(!/p\.height\s*>=?\s*track\.clientHeight/.test(centerOn), 'and not on the card\'s height against the track\'s');
  // the margin note's rule, which the paragraph now defers to, says the same
  const margin = between('The margin-layout follow-on (2026-09-07), panel side.', 'The focus follow-on (2026-09-08):');
  assert.ok(margin.includes('Where centering the mark would leave the card\'s end past the track\'s box (an open card, a pushed one), the body scrolls the least that shows the card\'s end, as far as keeps the mark\'s top in view'));
});

test('the room the paragraph names is the condition\'s, in the fixtures\' geometry: half the body less the footer and the gap, short of the track, and an open card that fits the track is past it', () => {
  for (const [name, src] of [['file-comments-focus.test.ts', focusTest], ['file-comments-margin-fixes.test.ts', fixesTest]]) {
    const g = geometry(src, name);
    // with the card level with its mark (p.top = desired, markY = desired + OFFSET), showCard > want reads
    // h > TRACK - CARD_GAP + OFFSET - BODY_VIEW / 2, which with TRACK = BODY_VIEW - OFFSET - FOOTER is the paragraph's room
    const fromCondition = g.TRACK - CARD_GAP + g.OFFSET - g.BODY_VIEW / 2;
    const room = g.BODY_VIEW / 2 - g.FOOTER - CARD_GAP;
    assert.equal(fromCondition, room, name + ': the paragraph\'s room is the condition\'s threshold');
    assert.ok(room < g.TRACK, name + ': short of the track (' + room + ' vs ' + g.TRACK + ')');
    assert.ok(g.OPEN + CARD_GAP <= g.TRACK, name + ': the open card fits the track with the gap');
    assert.ok(g.OPEN > room, name + ': and is taller than the room, so it takes the fallback');
    assert.ok(g.TALL + CARD_GAP > g.TRACK, name + ': the tall card does not fit the track');
  }
  // the numbers the paragraph quotes are the focus fixtures'
  const quoted = note.match(/in the focus fixtures' geometry (\d+)px, against a (\d+)px track/);
  assert.ok(quoted, 'the paragraph quotes the room and the track in the focus fixtures\' geometry');
  const g = geometry(focusTest, 'file-comments-focus.test.ts');
  assert.equal(Number(quoted[1]), g.BODY_VIEW / 2 - g.FOOTER - CARD_GAP);
  assert.equal(Number(quoted[2]), g.TRACK);
  // the two panel tests the paragraph credits drive the open card through the fallback and assert the least-scroll landing
  assert.ok(note.includes('`file-comments-focus.test.ts` and `file-comments-margin-fixes.test.ts` both drive a fitting card through it'));
  assert.ok(focusTest.includes('assert.ok(showCard > markY - BODY_VIEW / 2, "the fixture: the card\'s end needs more scroll than the mark\'s center");'));
  assert.ok(focusTest.includes('assert.equal(body.scrollTop, showCard, "the least scroll that shows the card\'s end");'));
  assert.ok(fixesTest.includes('assert.ok(OPEN + 8 <= TRACK, "the fixture: an open card and the gap fit the track");'));
  assert.ok(fixesTest.includes('assert.ok(showCard > center, "the fixture: the card\'s end needs more scroll than the mark\'s center: " + showCard + " vs " + center);'));
  assert.ok(fixesTest.includes('assert.equal(body.scrollTop, showCard, "the least scroll that shows the card\'s end");'));
});

test('the card taller than the track is recorded as the cap\'s case alone: the head cut by the excess, the scroll capped where the mark\'s top would leave the body\'s box', () => {
  assert.ok(note.includes('A focused card taller than the track has its head cut by the excess alone, the scroll capped where the mark\'s top would leave the body\'s box'));
  assert.ok(centerOn.includes('Math.min(showCard, markY - CARD_GAP)'), 'the cap: the mark\'s top a gap under the body\'s top');
  assert.ok(fixesTest.includes('assert.equal(TRACK_BOX.top - box.top, Math.min(excess, OFFSET - 8), "clipped at the head by the excess alone: "'), 'the margin-fixes test measures the cut');
});

test('the paragraph\'s Tests sentence and the Tests section\'s bullet name this module', () => {
  const me = 'tools/file-review-plan-focus-centering.test.mjs';
  assert.ok(note.includes('`' + me + '`'));
  const tests = between('## Tests', '## Docs');
  const bulletAt = tests.indexOf('- The focus follow-on (2026-09-08): `card-layout.test.ts` gains the focus rule');
  assert.ok(bulletAt >= 0, 'the Tests section has the focus bullet');
  const bullet = tests.slice(bulletAt, tests.indexOf(' - The todo-file follow-on', bulletAt));
  assert.ok(bullet.includes('`' + me + '` holds the paragraph\'s account of the centering fallback'));
  assert.ok(fs.existsSync(path.join(REPO, me)));
});

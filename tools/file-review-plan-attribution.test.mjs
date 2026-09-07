// The plan's margin-layout note (plans/file-review.md, the Slice 2 section) records two things a later
// reader must be able to tell apart: what the user asked for, and what the build made of it. The note
// as first written folded the build's design into the ask (margin-aligned cards the way document
// editors lay out comments, each card level with its passage, overlaps pushed down and never up) and
// dropped the ask's hedges (when possible; trying to center near the passage), so the plan read as if
// the user had required the layout it got (review finding, 2026-09-07). The plan presents itself as
// the record of the user's rulings, so a maintainer answering "why is the card not centered on its
// passage?" would have found the plan saying the user asked for what was built. This module holds the
// note to the record: the ask carries its hedges and none of the design; the design is the build's
// reading, described to the user so it could be redirected, and not yet confirmed; and Open questions
// names it as awaiting the user's word. Synthetic: no session data, only the repo's own text; the user
// is paraphrased, never quoted. Run: node --test tools/file-review-plan-attribution.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const plan = fs.readFileSync(path.join(REPO, 'plans', 'file-review.md'), 'utf8');

// The text between two headings, hard wraps collapsed so an assertion survives a rewrap.
function section(from, to) {
  const a = plan.indexOf(from);
  assert.ok(a >= 0, `heading ${JSON.stringify(from)} not found in the plan`);
  const b = plan.indexOf(to, a + from.length);
  assert.ok(b > a, `heading ${JSON.stringify(to)} not found after ${JSON.stringify(from)}`);
  return plan.slice(a, b).replace(/\s+/g, ' ');
}
const slice2 = section('### Slice 2: the session\'s changes as accept/reject cards and inline marks', '### Slice 3: region comments on images');
const open = section('## Open questions for the user', '## Upstream');
const tests = section('## Tests', '## Docs');

// The note's record, from its label to the build's own account ("Built:"), split at the sentence
// that turns from the ask to the layout.
const LABEL = 'The margin-layout follow-on (2026-09-07), panel side.';
const TURN = ' The layout is the build\'s reading of that ask';
const noteAt = slice2.indexOf(LABEL);
assert.ok(noteAt >= 0, 'the note is in the Slice 2 section');
const builtAt = slice2.indexOf(' Built: ', noteAt);
assert.ok(builtAt > noteAt, 'the note turns to what was built');
const record = slice2.slice(noteAt, builtAt);
const turnAt = record.indexOf(TURN);
assert.ok(turnAt > 0, 'the record names the layout as the build\'s reading');
const ask = record.slice(LABEL.length, turnAt);
const design = record.slice(turnAt);

test('the ask is recorded as the user made it, hedges included', () => {
  assert.ok(ask.includes('The user, after walking the loop, asked whether comments could move with the window when possible'), 'a wish with its hedge, not a requirement');
  assert.ok(ask.includes('each trying to stay centered near the place in the text it was left as the reader scrolls'), 'centering near the passage, which the build did not do');
  assert.ok(ask.includes('at least for markdown'));
});

test('the ask carries none of the build\'s design', () => {
  for (const phrase of ['margin', 'document editor', 'level with', 'pushed down', 'never up', 'leader', 'card']) {
    assert.ok(!ask.toLowerCase().includes(phrase), `the ask clause names "${phrase}", which is the build's, not the user's`);
  }
  assert.ok(!slice2.includes('asked that comment cards follow the text'), 'the earlier wording, which put the design inside the ask, is gone');
});

test('the layout is the build\'s reading, offered for redirection, not yet confirmed', () => {
  assert.ok(design.includes('The build described the design to the user as the work began, so the user could redirect it early if it was not what the ask meant'));
  assert.ok(design.includes('the user has not yet said whether it is'));
  assert.ok(design.includes('laid out as margin-aligned cards the way document editors lay out comments'));
  assert.ok(design.includes('each card\'s top level with its passage rather than centered on it'), 'the note says where the build departs from the ask');
  assert.ok(design.includes('pushed down in order and never up'));
  assert.ok(design.includes('the passage centered only on a click'));
});

test('Open questions names the layout as awaiting the user\'s word, and the Tests section names this pin', () => {
  assert.ok(open.includes('The margin layout (the follow-on note under Slice 2) awaits the user\'s word: it is the build\'s reading of the ask, not a ruling, and the walk answers it'));
  assert.ok(!open.includes('None remain.'), 'the section no longer says every question is ruled on');
  assert.ok(tests.includes('`tools/file-review-plan-attribution.test.mjs` holds the margin-layout note to the record'));
});

// The plan's filter follow-on note records the second review round's two fixes and names every suite the
// follow-on's tests live in; the panel does what the sentences say, and the tree holds no suite the plan omits.
//
// The second review round (2026-09-07) changed two panel behaviors — the anchor the track slot's loader
// and refusal are moved above when no filter row is offered, and Show changes inline's title under
// Comments — and added two suites, ui/webview/file-comments-filter-fixes.test.ts and
// ui/webview/feed-css-kind-cue.test.ts, while the note under Slice 2 (plans/file-review.md, "The filter
// follow-on (2026-09-07)") and the Tests section's bullet said neither behavior and named neither file
// (review finding, 2026-09-07). The existing pins (tools/file-review-plan.test.mjs,
// tools/file-review-plan-filter-review.test.mjs, ui/webview/file-review-docs.test.ts) hold the files the
// plan names to the tree — every named file exists — and never the tree to the plan, so a suite the plan
// omits fails nothing, and a reader following the inventory to the suite that drives the no-filter-row
// anchor or the sheets' kind-cue comment finds no file named. The plan now says both, and this module
// holds it there: the note's second-round sentences to the panel's source (the anchor's fallback, set
// between the rows' build and the move; the title read from the filter, the button offered all the same);
// the note and the Tests bullet name the two suites and this pin, each exists, and the suites drive what
// the sentences say; and the inventory is held to the tree the other way — every
// ui/webview/file-comments-filter*.test.ts in the tree is named in both places, so the next round's suite
// cannot land unrecorded. Synthetic: only the repo's own text.
// Run: node --test tools/file-review-plan-filter-fixes.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const read = (...parts) => fs.readFileSync(path.join(REPO, ...parts), 'utf8');

const plan = read('plans', 'file-review.md');
const panel = read('ui', 'webview', 'file-comments.ts');

// A span of the plan, hard wraps collapsed so an assertion survives a rewrap.
function section(from, to) {
  const a = plan.indexOf(from);
  assert.ok(a >= 0, `heading ${JSON.stringify(from)} not found in the plan`);
  const b = plan.indexOf(to, a + from.length);
  assert.ok(b > a, `heading ${JSON.stringify(to)} not found after ${JSON.stringify(from)}`);
  return plan.slice(a, b).replace(/\s+/g, ' ');
}
// The follow-on note: from its lead to the blank line (the Tests bullet later opens with the same words;
// the first hit is the note under Slice 2).
const noteAt = plan.indexOf('The filter follow-on (2026-09-07):');
assert.ok(noteAt >= 0, 'the follow-on note is in the plan');
const note = plan.slice(noteAt, plan.indexOf('\n\n', noteAt)).replace(/\s+/g, ' ');
const tests = section('## Tests', '## Docs');
// The Tests section's bullet for the follow-on: from its lead to the next bullet or the section's end.
const bulletAt = tests.indexOf('- The filter follow-on (2026-09-07):');
assert.ok(bulletAt >= 0, 'the Tests section carries the follow-on\'s bullet');
const bulletEnd = tests.indexOf(' - ', bulletAt + 2);
const bullet = tests.slice(bulletAt, bulletEnd === -1 ? undefined : bulletEnd);
// The panel's head builder, where the rows are built and the track slot's are moved.
const head = panel.slice(panel.indexOf('private renderHead('), panel.indexOf('private renderComposer('));
assert.ok(head.length > 0, 'renderHead precedes renderComposer in the panel');

test('the note says with no filter row the track slot\'s rows go above the head\'s other rows, and the panel sets that anchor between the rows\' build and the move', () => {
  assert.ok(note.includes('The second review round (2026-09-07) settled two more.'), 'the note opens the second round\'s sentences');
  assert.ok(note.includes('With no filter row to stand above (a file with nothing to filter, or no status) the track slot\'s loader and refusal are inserted above the head\'s other rows, the status refusal\'s, the poll\'s and the editor\'s, rather than appended after them'));
  // built, anchored, moved — in that order: an insertBefore with a null anchor appends, which is the bug the round fixed
  const built = head.indexOf('for (const n of [this.loader("track"), this.errRow("track"), this.errRow("head"), this.errRow("poll"), this.errRow("edit")]) if (n) head.appendChild(n);');
  const anchored = head.indexOf('if (!filterRow) filterRow = (Array.from(head.childNodes) as HTMLElement[]).find((n) => n.nodeType === 1 && ["head", "poll", "edit"].includes(n.dataset.slot || "")) || null;');
  const moved = head.indexOf('if (n.nodeType === 1 && (n as HTMLElement).dataset.slot === "track") underToggles(n as HTMLElement);');
  assert.ok(built >= 0, 'the head\'s rows are built in one pass');
  assert.ok(anchored > built, 'with no filter row, the anchor is the first of the head\'s other rows, set after the rows are built');
  assert.ok(moved > anchored, 'and the track slot\'s rows are moved above it after the anchor is set');
  assert.ok(head.includes('const underToggles = (n: HTMLElement): void => { head.insertBefore(n, filterRow); };'), 'the move is an insertBefore the anchor');
});

test('the note says Show changes inline stays offered under Comments with a title that reads the filter, and the panel\'s title does', () => {
  assert.ok(note.includes('Under Comments the read view paints no change mark whatever Show changes inline says, so the toggle stays offered (its setting is shared with All, Changes and the other panels) and its title says the filter hides the marks and that the setting governs All and Changes, never that the text carries marks it does not.'));
  assert.match(head, /const withheld = this\.activeFilter\(\) === "comments";\n\s+i\.title = withheld\n/, 'the title branches on the filter, and the button is built either way');
  assert.ok(head.includes('"Comments above hides the change marks with the change cards; under All or Changes the session\'s changes are marked in the text. Click to read the file without the marks there too"'), 'the ON title under Comments names the filter and the two states the setting governs');
  assert.ok(head.includes('"The marks are off, and Comments above hides them with the change cards; click to mark the session\'s changes in the text under All or Changes"'), 'the OFF title under Comments does the same');
  assert.ok(head.includes('"The session\'s changes are marked in the text, insertions tinted and deletions struck; click to read the file without the marks"'), 'under All or Changes the title claims the marks the text carries');
});

test('the note and the Tests bullet name the second round\'s two suites and this pin, each exists, and the suites drive what the sentences say', () => {
  for (const rel of ['ui/webview/file-comments-filter-fixes.test.ts', 'ui/webview/feed-css-kind-cue.test.ts', 'tools/file-review-plan-filter-fixes.test.mjs']) {
    assert.ok(note.includes('`' + rel + '`'), 'the note names ' + rel);
    assert.ok(bullet.includes('`' + rel + '`'), 'the Tests bullet names ' + rel);
    assert.ok(fs.existsSync(path.join(REPO, rel)), rel + ' exists');
  }
  assert.ok(bullet.includes('drives the second round\'s cases the same way'), 'the bullet says the fixes suite drives the round over the same stand-in');
  assert.ok(bullet.includes('byte-equal across the two sheets'), 'the bullet says the kind-cue pin holds both sheets');
  const fixes = read('ui', 'webview', 'file-comments-filter-fixes.test.ts');
  for (const phrase of ['no status, so no filter row', 'with cards the same rows stand above the filter\'s row', '\'Nothing decided\' row', 'the line names the card and the rectangle', 'comes to ride a change card', 'Show changes inline under Comments: the toggle stays']) {
    assert.ok(fixes.includes(phrase), 'the fixes suite drives: ' + phrase);
  }
  const cue = read('ui', 'webview', 'feed-css-kind-cue.test.ts');
  assert.ok(cue.includes('styled\\s+like \\.fc-note \\(--dim, 0\\.86em\\)'), 'the kind-cue pin holds the comment to the rule, the tokens and the size');
  assert.ok(cue.includes('assert.equal(kindCueComment(CHAT), kindCueComment(FEED)'), 'and styles.css\'s comment byte-equal to feed.css\'s');
});

test('the inventory is held to the tree: every file-comments-filter suite under ui/webview is named in the note and in the Tests bullet', () => {
  const suites = fs.readdirSync(path.join(REPO, 'ui', 'webview')).filter((f) => /^file-comments-filter.*\.test\.ts$/.test(f)).sort();
  assert.ok(suites.length >= 3, 'the follow-on\'s driven suites are in the tree: ' + suites.join(', '));
  for (const f of suites) {
    const rel = 'ui/webview/' + f;
    assert.ok(note.includes('`' + rel + '`'), 'the note\'s Tests sentence names ' + rel + ' — a suite the follow-on gained is recorded where the next reader looks');
    assert.ok(bullet.includes('`' + rel + '`'), 'the Tests bullet names ' + rel);
  }
  assert.ok(bullet.includes('every suite named `file-comments-filter…` under `ui/webview` is named here and in the note'), 'the bullet says this pin holds the inventory to the tree');
});

// The anchors follow-on's second review (2026-09-08) found the plan behind the slice in two places. The
// painting paragraph under Commenting from either view still named three states (located, context,
// detached) after the review's round 2 had added a fourth to the panel: a comment located at its quote on a
// copy the stored position does not vouch for — the anchor ties and the position names none of the tied
// copies, or the comment has none — is painted in the dashed ring the text-changed state wears, with a
// "passage recurs" tag and the card's words (copyUnsure), never as the copy that was chosen; the
// follow-on note and the contract said the tie-break keeps the highlight on the chosen copy without that
// condition. And the Raw acceptance criterion on a quote that occurs twice stated one outcome of two lines
// inserted between the selection and the save — anchors to the selected occurrence — while the system meets it
// only when the panel painted the edit before the save (followPassage moves the offset from a repaint); the
// save first sends the selection-time offset, which sits on no copy, and the host refuses anchor-ambiguous with
// the note kept rather than place it on the nearest copy. The plan now states the fourth state, the
// condition on the tie-break and both outcomes; this module holds each sentence to the source that makes it
// true: the panel's paint pass, copyUnsure and its words, the tag and the note on the card; the host's
// locateExact on the Raw criterion's own fixture, driven the way the comment verb drives it; the panel's
// follow, Save and refusal handling; and the webview modules the note names. Synthetic: the repo's own text
// and fixtures, no session data.
// Run: node --test tools/file-review-plan-anchors-states.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { locateExact } from './file-comments-host.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const read = (...parts) => fs.readFileSync(path.join(REPO, ...parts), 'utf8');
const exists = (...parts) => fs.existsSync(path.join(REPO, ...parts));

const plan = read('plans', 'file-review.md');
const flat = plan.replace(/\s+/g, ' ');
const host = read('tools', 'file-comments-host.mjs');
const panel = read('ui', 'webview', 'file-comments.ts');

// The text between two headings, hard wraps collapsed so an assertion survives a rewrap.
function section(from, to) {
  const a = plan.indexOf(from);
  assert.ok(a >= 0, `heading ${JSON.stringify(from)} not found in the plan`);
  const b = plan.indexOf(to, a + from.length);
  assert.ok(b > a, `heading ${JSON.stringify(to)} not found after ${JSON.stringify(from)}`);
  return plan.slice(a, b).replace(/\s+/g, ' ');
}
const contract = section('## The contract: the track-changents sidecar', '## Kernel: two ops and a host script');
const ux = section('### Commenting from either view, and in every format', '### The viewer seam');
const note = section('### Slice 2: the session', '### Slice 3: region comments on images');
const tests = section('## Tests', '## Docs');

// A function's source, from its `function name(` to the first line that is a lone closing brace.
function fn(src, name) {
  const a = src.indexOf(`function ${name}(`);
  assert.ok(a >= 0, `${name} is defined`);
  const b = src.indexOf('\n}\n', a);
  assert.ok(b > a, `${name} closes`);
  return src.slice(a, b);
}
// A class method's source, from `private name(` to the first line that is a closing brace at the method's indent.
function method(src, name) {
  const a = src.indexOf(`private ${name}(`);
  assert.ok(a >= 0, `${name} is a method`);
  const b = src.indexOf('\n  }\n', a);
  assert.ok(b > a, `${name} closes`);
  return src.slice(a, b);
}

// ── the painting paragraph: four states, and the panel's fourth ─────

test('the painting paragraph names four states and says when a copy is a guess; the plan says "three states" nowhere', () => {
  assert.ok(ux.includes("Painting distinguishes four states after the engine locates a comment's anchor in the current text, with the comment's stored `anchorAt` as the tie-break"));
  assert.ok(ux.includes("located at the quote on a copy the comment vouches for, the anchor's one best hit or a tied copy the stored position names, painted normally"));
  assert.ok(ux.includes('located at the quote on a guessed copy, painted in the dashed ring the text-changed state wears, with a "passage recurs" tag on the card and, on the open card, a line saying the copy is the nearest to the stored position, or the first, and not a confirmed one'));
  assert.ok(ux.includes('quote gone but its context found (`engine.js:793-800`), painted over the between-context region in a text-changed style with a card; neither found, shown as a card only, marked detached in the panel'));
  assert.ok(ux.includes('A copy is guessed when the anchor ties and the stored position names none of the tied copies, or the comment has no position (`copyUnsure`)'));
  assert.ok(ux.includes('is a guess and is shown as one, never as the copy that was chosen'));
  assert.ok(!flat.includes('Painting distinguishes three states'), 'the pre-review count is gone');
});

test('the panel paints the fourth state as the paragraph says: copyUnsure on a located mark, the dashed ring, the title, the tag and the words', () => {
  // the paint pass asks copyUnsure of every located comment, and a guessed copy wears the context class over the located one
  assert.ok(panel.includes('const unsure = loc.state === "located" && !!loc.range && this.copyUnsure(src, card, at, loc.range.start);'), 'asked of a located comment, at the copy the engine returned, with the stored position in the view\'s coordinates');
  // the position the engine and copyUnsure read is the stored one mapped into the view's coordinates (viewAt): the
  // host keeps a BOM the fetch strips, and the status says whether it does (bom), the host's own word on its text
  assert.ok(panel.includes('const at = this.viewAt(card);') && panel.includes('const loc = locateComment(src, card.anchor, at);'), 'the hint is the mapped position');
  const view = method(panel, 'viewAt');
  assert.ok(view.includes('if (card.anchorAt === null) return undefined;') && view.includes('return this.status && this.status.bom ? card.anchorAt - 1 : card.anchorAt;'), 'one character on a BOM file, as the status says; 0 is a position');
  assert.ok(read('ui', 'webview', 'file-comments-model.ts').includes('bom?: boolean;'), 'the status type carries the bit');
  assert.ok(/bom: typeof text === 'string' && text\.charCodeAt\(0\) === 0xFEFF,/.test(host), 'the host answers it on every reply');
  assert.ok(ux.includes('so the reply says whether it does (`bom`) and the panel maps the position into the view\'s coordinates by it (`viewAt`) before the engine takes it as the hint and before the copy is judged'), 'the painting paragraph says so');
  assert.ok(panel.includes('if (unsure) this.unsureCopies.add(card.id);'), 'remembered for the card');
  assert.ok(panel.includes('const cls = "fc-hl" + (loc.state === "context" ? " fc-hl-context" : "");'), 'the context state\'s class');
  assert.ok(panel.includes('if (unsure) m.classList.add("fc-hl-context");'), 'a guessed copy wears the same dashed ring');
  // ...and the sheets say so where they define the ring (both, byte-equal in the panel block: file-comments.test.ts)
  for (const sheet of ['styles.css', 'feed.css']) {
    assert.ok(read('ui', 'webview', sheet).replace(/\s+/g, ' ').includes('wears a dashed ring, and so does a located copy the panel cannot confirm as the one chosen (file-comments.ts copyUnsure: the passage recurs and the stored position names none of the copies)'), `${sheet} names the guessed copy as a wearer of fc-hl-context`);
  }
  assert.ok(panel.includes('const title = unsure ? unsureMarkTitle(card) : "Open the comment on this passage";'), 'the mark says it is not confirmed');
  // the title branches on whether a position is stored, on the same test as the card's words (the third review: the
  // title claimed a stored position on a comment `track-comment` wrote, whose card said it stores none)
  const markTitle = fn(panel, 'unsureMarkTitle');
  assert.ok(markTitle.includes('"Open the comment; this passage recurs, and "') && markTitle.includes('c.anchorAt === null'), 'the same branch as copyUnsureWords');
  assert.ok(markTitle.includes('"the comment stores no position to tell the copies apart, so this is the first copy"'), 'no position: the first copy');
  assert.ok(markTitle.includes('"this copy is the nearest to the comment\'s stored position"') && markTitle.includes('", not a confirmed one"'), 'a position naming none: the nearest, and never a confirmed one');
  assert.ok(panel.includes('if (img) { frameImage(img, unsure ? cls + " fc-hl-context" : cls, { act: "fcopen", id: card.id }); this.mark(img); painted = true; }'), 'a framed figure too');
  // copyUnsure: a position that names the copy is the choice; a tie is the anchor's earliest and latest best hits differing
  const unsure = method(panel, 'copyUnsure');
  assert.ok(unsure.includes('if (!card.anchor || stored === at) return false;'), 'a position naming the painted copy is the choice recorded');
  assert.ok(unsure.includes('const first = locateComment(src, card.anchor, 0);') && unsure.includes('const last = locateComment(src, card.anchor, src.length);'), 'the host\'s own test for a tie');
  assert.ok(unsure.includes('return last.state === "located" && !!last.range && last.range.start !== first.range.start;'), 'one best hit is the anchor\'s own answer');
  // the card: a "passage recurs" tag with the words as its title, and the words on the open card
  assert.ok(panel.includes('if (this.unsureCopies.has(c.id)) { const t = el("span", "fc-tag", "passage recurs"); t.title = copyUnsureWords(c); head.appendChild(t); }'), 'the tag');
  assert.ok(panel.includes('if (this.unsureCopies.has(c.id)) card.appendChild(el("div", "fc-note", copyUnsureWords(c)));'), 'the line on the open card');
  const words = fn(panel, 'copyUnsureWords');
  assert.ok(words.includes('"the comment stores no position to tell the copies apart, so the first copy is highlighted"'), 'no position: the first copy');
  assert.ok(words.includes('"the position stored with the comment names none of the copies as the file is now, so the copy nearest that position is highlighted"'), 'a position naming none: the nearest');
  assert.ok(words.includes('" — not a confirmed one."'), 'and never a confirmed one');
});

// ── the contract and the follow-on note: the tie-break holds while the position names a copy ──

test('the contract and the follow-on note condition the tie-break on the position naming a copy, and the note names the modules that drive the painted states', () => {
  assert.ok(contract.includes('so a passage that recurs with identical surroundings wider than the anchor\'s context stays on the copy that was chosen while the position names one of the copies; a copy the position does not name is painted as a guess, never as the chosen one'));
  assert.ok(note.includes('so the highlight stays on the copy that was chosen even where the anchor alone cannot tell, while the position names a tied copy; where it names none, or the comment has no position, the copy the engine returns is a guess, and the panel paints it as one: the dashed ring the text-changed state wears, a "passage recurs" tag and the card\'s words (`copyUnsure`'));
  assert.ok(note.includes('the painted states in `ui/webview/file-comments-anchors-unsure.test.ts`'));
  assert.ok(note.includes('and `-region-tied` (the region composer\'s tied and elsewhere pairs); and `tools/file-review-plan-anchors-states.test.mjs`'));
  assert.ok(tests.includes('`tools/file-review-plan-anchors-states.test.mjs` pins the painting paragraph\'s four states'));
  for (const f of [['ui', 'webview', 'file-comments-anchors-unsure.test.ts'], ['ui', 'webview', 'file-comments-region-tied.test.ts'], ['tools', 'file-review-plan-anchors-states.test.mjs']]) {
    assert.ok(exists(...f), `${f.join('/')} exists`);
  }
  // the unsure module drives the four cases the paragraph describes: a position naming none after an edit in the
  // chosen copy's context, after an unrecorded insertion above, no position at all, and the two plain paints
  const drive = read('ui', 'webview', 'file-comments-anchors-unsure.test.ts');
  assert.ok(drive.includes("an edit inside the chosen copy's context: the stored position names none of the tied copies, so the engine's pick is painted in the dashed cue"));
  assert.ok(drive.includes('a long insertion above that nothing recorded: the stored position is stale, names no copy, and the nearest copy is painted as a guess'));
  assert.ok(drive.includes('a comment with no stored position on a passage that recurs: the first copy is painted as a guess'));
  assert.ok(drive.includes('the position naming a tied copy, and a unique passage with an outdated position, paint plainly with no tag'));
});

// ── the Raw criterion: both outcomes, on its own fixture ────────────

test('the Raw criterion states both outcomes of an insertion between the selection and the save, and the old unconditional wording is gone', () => {
  assert.ok(ux.includes('- Raw: a quote that occurs twice, with the same 24 characters around each copy so only the offset can tell them apart, anchors to the selected occurrence, including when two lines are inserted above the passage between the selection and the save, provided the panel painted the edited text before the save (the poll\'s reload, Reload, a refresh: `followPassage` moves the pending pair with its copy, exactly, and Save sends the moved offset, which the host finds on the selected copy).'));
  assert.ok(ux.includes('When the save comes before the panel has shown the edit, the offset sent indexes the old text and sits on no copy, and the host refuses `anchor-ambiguous` with a message that says the text moved, writes nothing, and the note stays in the composer to be placed by selecting the passage again, never on the nearest copy'));
  assert.ok(!flat.includes('between the selection and the save.'), 'the criterion no longer states one outcome unconditionally');
  assert.ok(note.includes('The Raw acceptance criterion on a quote that occurs twice states both outcomes of lines inserted between the selection and the save: the note lands on the selected copy when the panel painted the edit before the save, since the follow moves the offset only from a repaint (`retargetComposer`, on `onRendered`), and is refused with the note kept when the save came first'));
});

test('on the Raw fixture, the host places the moved offset on the selected copy and refuses the selection-time one, as the criterion states', () => {
  const text = read('ui', 'webview', 'anchor-map-fixtures', 'handlers-crlf.py');
  const needle = 'return respond(404, "missing")';
  const first = text.indexOf(needle), second = text.indexOf(needle, first + 1);
  assert.ok(first >= 0 && second > first && text.indexOf(needle, second + 1) === -1, 'the fixture holds the passage twice');
  const at24 = (i) => ({ quote: needle, prefix: text.slice(i - 24, i), suffix: text.slice(i + needle.length, i + needle.length + 24) });
  const anchor = at24(second);
  assert.deepEqual(anchor, at24(first), 'the copies tie at 24: only the offset can tell them apart');
  const span = (i) => ({ from: i, to: i + needle.length });
  // a save with no edit in between: the selection's start sits on the second copy, and the host places it there
  assert.deepEqual(locateExact(text, anchor, second, { exact: true }), span(second));
  assert.deepEqual(locateExact(text, anchor, undefined, { exact: true }), { error: 'anchor-ambiguous' }, 'no offset: a tie the request cannot settle');
  // two lines inserted above the passage, between the copies, between the selection and the save
  const at = text.indexOf('def put_note');
  assert.ok(first < at && at < second, 'the insertion lands between the copies');
  const inserted = '# reviewed\r\n# twice\r\n';
  const edited = text.slice(0, at) + inserted + text.slice(at);
  const moved = second + inserted.length;
  assert.equal(edited.slice(moved, moved + needle.length), needle);
  // (a) the panel painted the edit before the save: the follow shifts the pair by the edit's length (followPassage,
  // pinned below), Save builds the anchor over the edited text at the moved pair and sends its start, and the host
  // places it on the selected copy
  const followed = { quote: needle, prefix: edited.slice(moved - 24, moved), suffix: edited.slice(moved + needle.length, moved + needle.length + 24) };
  assert.deepEqual(locateExact(edited, followed, moved, { exact: true }), span(moved), 'placed on the selected copy');
  // (b) the save came first: the selection-time offset indexes the old text and sits on no copy now; the engine's
  // nearest-wins from it would pick the selected copy here (the insertion is shorter than the gap), by luck
  // the host does not take
  assert.deepEqual(locateExact(edited, anchor, second), span(moved), 'nearest-wins, right by luck: what a stored position keeps');
  assert.deepEqual(locateExact(edited, anchor, second, { exact: true }), { error: 'anchor-moved' }, 'the comment verb\'s exact locate refuses');
  // the same stale request under an insertion above both copies longer than half the gap: nearest-wins picks the
  // copy that was not selected, which is why the refusal is the same
  const above = '# ' + 'reviewed '.repeat(9) + '\r\n';
  assert.ok(above.length > (second - first) / 2 && above.length < second - first, 'longer than half the gap, shorter than the gap');
  const shifted = above + text;
  assert.deepEqual(locateExact(shifted, anchor, second), span(first + above.length), 'nearest-wins picks the other copy');
  assert.deepEqual(locateExact(shifted, anchor, second, { exact: true }), { error: 'anchor-moved' });
  // the verb: the exact locate on the request's offset, and anchor-moved surfaced as the anchor-ambiguous refusal
  // whose message says the text moved
  assert.ok(/locateExact\(text, anchor, browserHint\(text, args\.hintOffset\), \{ exact: true \}\)/.test(host), 'buildComment locates exactly, on the request\'s offset');
  assert.ok(/if \(built\.error === 'anchor-moved'\) \{\s*\n\s*throw new Refusal\('anchor-ambiguous', `\$\{what\} occurs more than once in \$\{ctx\.shown\}[^`]*\$\{moved\} no longer says which copy was meant — \$\{again\}`\);/.test(host), 'the refusal names the moved text, in the words of the gesture (a passage selected, a region drawn)');
  assert.ok(host.includes(`"the text moved after it was selected, so the selection's position"`) && host.includes(`'reload and select it again'`), 'a passage: the text moved after it was selected; select it again');
  assert.ok(host.includes(`"the text moved after the region was drawn, so the region's position"`) && host.includes(`'reload and draw the region again'`), 'a region on an embedded figure: drawn, so draw it again');
  // the panel: the follow runs from a repaint (a paint or a reflow alike; only the paint pass is skipped on a
  // reflow) and shifts a passage after the edit's span by the edit's length; Save sends the pair's start; a
  // refusal keeps the note where it was typed
  assert.ok(panel.includes('ctx.onRendered((why) => { this.hideFloat(); this.retargetComposer(); if (why === "reflow") { this.trimBlanks(); this.scheduleLayout(); } else this.paintAll(); });'), 'the follow runs when the body is repainted, on a paint and on a reflow alike (a reflow also re-measures the marks\' collapsed blanks, anchor-map.ts trimCollapsedMarks)');
  assert.ok(/const f = followPassage\(c\.text, c\.range, src\);\s*\n\s*if \(f\.state === "moved"\) \{ c\.range = f\.range; c\.text = src; c\.tied = false; \}/.test(panel), 'retargetComposer moves the pair with its copy');
  const follow = fn(panel, 'followPassage');
  assert.ok(follow.includes('if (range.start >= oldLen - s) { const d = newLen - oldLen; return { state: "moved", range: { start: range.start + d, end: range.end + d } }; }'), 'a passage after the edit shifts by its length, exactly');
  assert.ok(panel.includes('if (c.range && src !== null) { args.anchor = makeAnchor(src, c.range); args.hintOffset = c.range.start; }'), 'Save sends the pair\'s start');
  assert.ok(panel.includes('if (r) this.closeComposer();'), 'a refusal keeps the note in the composer');
});

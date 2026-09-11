// The tie-break's review, third round (2026-09-11): the record behind the second round's panel fixes. That round changed
// the words a REGION comment's card carries when its embed line ties (they end with the recourse a region has, a NEW
// region drawn on the figure meant, with a mouse: REGION_CONFIRM in ui/webview/file-comments.ts) and took the Reveal
// off its card, since reveal() for a region scrolls to its picture and never switches to Raw, and Re-place sends the
// rectangle alone while the host keeps the anchor, its position and its copy fields (doRetarget). It also put what a
// passage comment's save does on the open card as a line of its own (SAVE_FROM_COPY_NOTE), where touch can read it. The
// commit said so; the record did not: decision 51 and the anchors follow-on note (plans/file-review.md) said every
// guessed copy's card words end with "Reveal it and save again from the right copy to confirm." and that the card offers
// that Reveal, which is true of a passage comment alone, and the Tests section named neither of the round's two new
// modules. This module holds the corrected sentences to the code that makes them true and the round's modules to the
// tree. Synthetic: the repo's own text, no session data.
// Run: node --test tools/file-review-plan-tiebreak-review-3.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const read = (...parts) => fs.readFileSync(path.join(REPO, ...parts), 'utf8');
const exists = (...parts) => fs.existsSync(path.join(REPO, ...parts));

const plan = read('plans', 'file-review.md');
const host = read('tools', 'file-comments-host.mjs');
const panel = read('ui', 'webview', 'file-comments.ts');
const regionModule = read('ui', 'webview', 'file-comments-tiebreak-region.test.ts');

// The text between two headings, hard wraps collapsed so an assertion survives a rewrap.
function section(from, to) {
  const a = plan.indexOf(from);
  assert.ok(a >= 0, `heading ${JSON.stringify(from)} not found in the plan`);
  const b = plan.indexOf(to, a + from.length);
  assert.ok(b > a, `heading ${JSON.stringify(to)} not found after ${JSON.stringify(from)}`);
  return plan.slice(a, b).replace(/\s+/g, ' ');
}
const ux = section('### Commenting from either view, and in every format', '### The viewer seam');
const note = section('### Slice 2: the session', '### Slice 3: region comments on images');
const tests = section('## Tests', '## Docs');
const decisions = section('## Decisions (the user, 2026-09-05 and 2026-09-06)', '## Open questions for the user');
const decision51 = decisions.slice(decisions.indexOf('51. **'));

// A function's source, from its `function name(` to the first line that is a lone closing brace; a method's from its
// signature at the class's indent to the first closing brace at that indent.
function fn(src, name) {
  const a = src.indexOf(`function ${name}(`);
  assert.ok(a >= 0, `${name} is defined`);
  const b = src.indexOf('\n}\n', a);
  assert.ok(b > a, `${name} closes`);
  return src.slice(a, b);
}
function method(src, signature) {
  const a = src.indexOf(`\n  ${signature}`);
  assert.ok(a >= 0, `${signature} is a method`);
  const b = src.indexOf('\n  }\n', a);
  assert.ok(b > a, `${signature} closes`);
  return src.slice(a, b);
}
// A string constant's value, as the panel writes it in one literal.
function constant(src, name) {
  const m = src.match(new RegExp(`const ${name} = "((?:[^"\\\\]|\\\\.)*)";`));
  assert.ok(m, `${name} is one string literal`);
  return m[1];
}

const REGION_SENTENCE_IN_NOTE = "That is a passage comment's card: a region comment whose embed line ties is guessed by the same rules, and since Reveal for a region scrolls to its picture, never to Raw, and Re-place keeps the anchor, its position and its fields, its words end with the recourse a region has, a new region drawn on the figure meant, with a mouse, and its card offers no Reveal (the review's second round, 2026-09-11; decision 51 says why).";
const REGION_SENTENCE_IN_UX = "A region comment on an embed line that recurs is in the same state, its rectangle on the figure nearest the hint; its words end with the recourse a region has, a new region drawn on the figure meant, with a mouse (Reveal for a region scrolls to its picture, never to Raw, and Re-place keeps the anchor and its fields), and its card offers no Reveal (the review's second round, 2026-09-11).";
const ROUND_MODULES = ['tools/file-comments-host-tiebreak-review-2.test.mjs', 'ui/webview/file-comments-tiebreak-region.test.ts', 'tools/file-review-plan-tiebreak-review-3.test.mjs'];

// ── the record ──────────────────────────────────────────────────────

test('decision 51, the note and the painting paragraph scope the Reveal sentence to a passage comment and say a region comment\'s words end with the recourse a region has while its card offers no Reveal', () => {
  // the passage sentence stands, now scoped, and the region's end is announced beside it
  assert.ok(decision51.includes('and a guessed one as before, for a passage comment with the card\'s words now ending "Reveal it and save again from the right copy to confirm." and for a region comment with the card\'s words ending in the recourse a region has, said below.'));
  assert.ok(!decision51.includes('guessed one as before, with the card\'s words now ending'), 'the unscoped sentence, false of a region comment, is gone');
  // why the passage's recourse is not a region's, and what the region's is
  assert.ok(decision51.includes("A region comment on an embed line that recurs is guessed by the same rules (the host stamps and places every anchored comment, and the panel's `copyUnsure` asks the same of a rectangle, which `paintRegions` puts on the figure nearest the hint by `regionImageFor`), but the passage's recourse is not open to it: Reveal for a region scrolls to its picture and never switches to Raw, and Re-place sends the rectangle alone, so the host keeps the anchor, its position and its copy fields (`doRetarget` writes `target` back and nothing else), and the one thing that places a comment on the figure meant is a new region drawn on it, with a mouse."));
  assert.ok(decision51.includes('Its words end with that in place of the Reveal sentence (`REGION_CONFIRM`: draw a new region on the figure you mean, and this comment keeps its tag until you resolve it; Re-place redraws the rectangle on the figure shown and does not move the comment to another figure; drawing a region needs a mouse), and its card offers no Reveal: Reply, Resolve and Re-place on a pointer that draws, Reply and Resolve on a coarse one, where the words naming the mouse keep the card from dead-ending (the review\'s second round, 2026-09-11:'));
  // the passage card's own second-round change
  assert.ok(decision51.includes("The same round put what the passage's save does on the open card as a line of its own under the words that ask for it (`SAVE_FROM_COPY_NOTE`, the sentence the Reveal's title carries), since a button's title never reaches touch; a region's words carry their own."));
  // the note and the painting paragraph agree, in one sentence each
  assert.ok(note.includes(REGION_SENTENCE_IN_NOTE));
  assert.ok(note.includes('and whose card offers that Reveal (the review\'s first round, 2026-09-11). ' + REGION_SENTENCE_IN_NOTE), 'the region sentence follows the passage sentence it scopes');
  assert.ok(ux.includes(REGION_SENTENCE_IN_UX));
  assert.ok(ux.includes('never plainly on a copy the host did not vouch for in the text shown. ' + REGION_SENTENCE_IN_UX), 'after the confirmed place the view moved past');
});

// ── the panel ───────────────────────────────────────────────────────

test('the panel: a region comment\'s guessed-copy words end with REGION_CONFIRM, whose sentences say what the record says; a passage comment\'s end with the Reveal sentence', () => {
  const words = fn(panel, 'copyUnsureWords');
  const region = words.indexOf('if (c.target) return state + ", not a confirmed one. " + REGION_CONFIRM;');
  const passage = words.indexOf('return state + ", not a confirmed one. Reveal it and save again from the right copy to confirm.";');
  assert.ok(region >= 0, 'a comment with a target ends with the region\'s recourse');
  assert.ok(passage > region, 'and every other comment, after that test, with the Reveal sentence');
  const confirm = constant(panel, 'REGION_CONFIRM');
  assert.ok(confirm.startsWith('To confirm the copy, draw a new region on the figure you mean; this comment keeps its tag until you resolve it.'), 'the recourse and what the tag does');
  assert.ok(confirm.includes('Re-place redraws the rectangle on the figure shown and does not move the comment to another figure.'), 'what Re-place does instead');
  assert.ok(confirm.endsWith('Drawing a region needs a mouse.'), 'and the pointer it takes, so a coarse pointer\'s card does not dead-end');
  assert.ok(!confirm.includes('Reveal') && !/save/i.test(confirm), 'a region\'s words name neither the Reveal nor a save');
  // the tag's title carries the same words, so the mark and the card agree for a region as for a passage
  assert.ok(panel.includes('copyUnsureWords(c)'), 'the words are rendered from one function');
});

test('the panel: the open card\'s save line and the guessed copy\'s Reveal are a passage comment\'s alone, and reveal() for a region scrolls to its picture and returns before the switch to Raw', () => {
  assert.ok(panel.includes('if (this.unsureCopies.has(c.id)) card.appendChild(el("div", "fc-note", copyUnsureWords(c)));'), 'the words, for both card kinds');
  assert.ok(panel.includes('if (this.unsureCopies.has(c.id) && !c.target) card.appendChild(el("div", "fc-note", SAVE_FROM_COPY_NOTE));'), 'the save line, for a passage comment');
  assert.ok(panel.includes('const SAVE_FROM_COPY_NOTE = "A" + SAVE_FROM_COPY.slice(1) + ".";'), 'the line is the Reveal title\'s sentence');
  const a = panel.indexOf('if (c.anchor && loc && loc.range && !loc.painted) {');
  const b = panel.indexOf('} else if (', a);
  assert.ok(a >= 0 && b > a, 'Reveal for an unpainted passage, else...');
  const cond = panel.slice(b, panel.indexOf('{', b));
  assert.ok(cond.includes('!c.target') && cond.includes('this.unsureCopies.has(c.id)'), '...for a guessed copy of a comment with no target');
  const reveal = method(panel, 'reveal(key: string): void {');
  const branch = reveal.slice(reveal.indexOf('if (card && card.target) {'), reveal.indexOf('const loc = this.located.get(key);'));
  assert.ok(branch.length > 0, 'a region branch before the passage path');
  assert.ok(branch.includes('const img = this.regionImageFor(card);') && branch.includes('img.scrollIntoView({ block: "center" }); return;'), 'it scrolls to the picture and returns');
  assert.ok(!branch.includes('revealInRaw'), 'and never switches to Raw');
});

// ── the host ────────────────────────────────────────────────────────

test('the host: a re-place writes the target back and nothing else, so the anchor, its position and its copy fields stand', () => {
  const retarget = fn(host, 'doRetarget');
  assert.ok(retarget.includes('return (s) => { findComment(s, id).target = target; };'), 'the one write');
  assert.ok(!/\.(anchor|anchorAt|ordinal|copies|section)\s*=[^=]/.test(retarget), 'no other field of the comment is assigned');
});

// ── the modules ─────────────────────────────────────────────────────

test('the Tests section says what the second round\'s modules drive; decision 51, the note and the Tests section name them and they exist; no em dash in the new sentences', () => {
  assert.ok(tests.includes("From the same round, `tools/file-comments-host-tiebreak-review-2.test.mjs` drives the real host as a child process, or its exported helpers, over the round's findings on the host: a scan the budget cut serves no caller without a budget (`fullMatches`, so `passageFigure` and `doRetarget` read no null from `locateStored`)"));
  assert.ok(tests.includes("`ui/webview/file-comments-tiebreak-region.test.ts` drives both card kinds over the rendered stand-in and a Raw body: a region on the second of two embeds whose title an unrecorded write edited has its rectangle on the guessed figure and the tag, its words end with the region's recourse (a new region, with a mouse; what Re-place does instead), and its card offers Reply, Resolve and Re-place on a pointer that draws, Reply and Resolve on a coarse one, and no Reveal in either view; a passage comment on the same line, guessed, carries the words that ask for the save and a line under them saying what the save does (the Reveal's title ends with the same words, and Reveal switches to Raw at the guessed copy), and a passage whose position names its copy carries neither."));
  assert.ok(tests.includes("`tools/file-review-plan-tiebreak-review-3.test.mjs` holds the record's account of the second round (the region card's words and its missing Reveal, the passage card's line, the round's modules) to the panel (`copyUnsureWords`, `REGION_CONFIRM`, `renderCard`, `reveal`), the host (`doRetarget`) and the tree."));
  for (const m of ROUND_MODULES) {
    assert.ok(exists(...m.split('/')), `${m} exists`);
    for (const [name, text] of [['decision 51', decision51], ['the note', note], ['the Tests section', tests]]) assert.ok(text.includes(`\`${m}\``), `${name} names ${m}`);
  }
  const decisionTail = decision51.slice(decision51.indexOf('A region comment on an embed line that recurs'), decision51.indexOf('The contract named two fields'));
  const testsSentences = tests.slice(tests.indexOf('From the same round, `tools/file-comments-host-tiebreak-review-2.test.mjs`'), tests.indexOf('`tools/file-review-plan-attribution.test.mjs`'));
  for (const [name, text] of [['decision 51\'s region record', decisionTail], ['the note\'s sentence', REGION_SENTENCE_IN_NOTE], ['the painting paragraph\'s sentence', REGION_SENTENCE_IN_UX], ['the Tests sentences', testsSentences]]) {
    assert.ok(text.length > 0, `${name} found`);
    assert.ok(!text.includes('\u2014'), `${name} has no em dash`);
  }
});

test('the region module drives what the record says of it: the panel\'s REGION_CONFIRM word for word, no Reveal on a fine pointer, a coarse one and in Raw, and the passage card\'s save line', () => {
  assert.equal(constant(regionModule, 'REGION_CONFIRM'), constant(panel, 'REGION_CONFIRM'), 'the module holds the panel\'s words, so a change to either fails here');
  assert.ok(regionModule.includes('assert.equal(revealOf(card), null);'), 'no Reveal on the region card');
  assert.ok(regionModule.includes('assert.deepEqual(buttonsOf(card), ["Reply", "Resolve", "Re-place"]'), 'a pointer that draws: Re-place, no Reveal');
  assert.ok(regionModule.includes('assert.deepEqual(buttonsOf(card), ["Reply", "Resolve"]'), 'a coarse pointer, and Raw: neither');
  assert.ok(regionModule.includes('mode: "raw"'), 'the Raw leg');
  assert.ok(regionModule.includes('coarse = true;'), 'the coarse-pointer leg');
  assert.ok(regionModule.includes('assert.deepEqual(notesOf(card), [UNSURE_POSITION, SAVE_FROM_COPY_NOTE]'), 'the passage card: the ask, then what the save does');
  assert.equal(constant(regionModule, 'SAVE_FROM_COPY_NOTE'), 'A' + constant(panel, 'SAVE_FROM_COPY').slice(1) + '.', 'the module\'s save line is the panel\'s');
});

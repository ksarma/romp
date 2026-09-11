// The recurring-passage tie-break (2026-09-11; plans/file-review.md decision 51, the contract, the host paragraph, the
// painting paragraph and the anchors follow-on note; docs/adr/0002; docs/guide.md). The user saw a comment on a passage
// that recurs painted as a guess after an edit nobody recorded moved every copy past the stored position. The host now
// writes `ordinal`, `copies` and `section` beside `anchorAt` and breaks the tie by them, in order, before falling back
// to the nearest copy; the panel paints a copy the host confirmed plainly, and the guessed copy's words end by saying
// how to confirm it. This module holds each record to the source that makes it true: the plan's sentences to the host
// (locateStored's order, stampCopy, buildComment's fields, the store's markdown judgment stamped at load or seed and
// read by the refresh, the two readers, the reply's `placed`, the decisions' carve-out), the panel (placedAt, the
// paint pass's hint, the words), the model (the fields and the verdict type), the ADR's field list and the guide's
// sentence; and the test modules the note names to the tree. Synthetic: the repo's own text and fixtures, no session
// data.
// Run: node --test tools/file-review-plan-tiebreak.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { sectionAt, locateStored, fullMatches, ANCHOR_CTX_CAP } from './file-comments-host.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const read = (...parts) => fs.readFileSync(path.join(REPO, ...parts), 'utf8');
const exists = (...parts) => fs.existsSync(path.join(REPO, ...parts));

const plan = read('plans', 'file-review.md');
const flat = plan.replace(/\s+/g, ' ');
const host = read('tools', 'file-comments-host.mjs');
const panel = read('ui', 'webview', 'file-comments.ts');
const model = read('ui', 'webview', 'file-comments-model.ts');
const adr = read('docs', 'adr', '0002-file-comments-in-the-track-changents-sidecar.md').replace(/\s+/g, ' ');
const guide = read('docs', 'guide.md').replace(/\s+/g, ' ');

// The text between two headings, hard wraps collapsed so an assertion survives a rewrap.
function section(from, to) {
  const a = plan.indexOf(from);
  assert.ok(a >= 0, `heading ${JSON.stringify(from)} not found in the plan`);
  const b = plan.indexOf(to, a + from.length);
  assert.ok(b > a, `heading ${JSON.stringify(to)} not found after ${JSON.stringify(from)}`);
  return plan.slice(a, b).replace(/\s+/g, ' ');
}
const contract = section('## The contract: the track-changents sidecar', '## Kernel: two ops and a host script');
const op = section('## Kernel: two ops and a host script', '## UX');
const ux = section('### Commenting from either view, and in every format', '### The viewer seam');
const note = section('### Slice 2: the session', '### Slice 3: region comments on images');
const tests = section('## Tests', '## Docs');
const decisions = section('## Decisions (the user, 2026-09-05 and 2026-09-06)', '## Open questions for the user');

// A function's source, from its `function name(` to the first line that is a lone closing brace; a method's from
// `private name(` to the first closing brace at the method's indent.
function fn(src, name) {
  const a = src.indexOf(`function ${name}(`);
  assert.ok(a >= 0, `${name} is defined`);
  const b = src.indexOf('\n}\n', a);
  assert.ok(b > a, `${name} closes`);
  return src.slice(a, b);
}
function method(src, name) {
  const a = src.indexOf(`private ${name}(`);
  assert.ok(a >= 0, `${name} is a method`);
  const b = src.indexOf('\n  }\n', a);
  assert.ok(b > a, `${name} closes`);
  return src.slice(a, b);
}
function inOrder(src, needles, what) {
  let from = 0;
  for (const n of needles) {
    const i = src.indexOf(n, from);
    assert.ok(i >= 0, `${what}: ${JSON.stringify(n)} follows the previous step`);
    from = i + n.length;
  }
}

// ── decision 51 ─────────────────────────────────────────────────────

test('decision 51 records the report, the yes, the three fields, the rules in order, the third field\'s reason and the tests', () => {
  assert.ok(decisions.includes("51. **A recurring passage's copy is confirmed by its ordinal, then by its heading path, before the position's nearest copy is guessed** (2026-09-11)."));
  assert.ok(decisions.includes('The user reported a comment on a passage that occurs more than once painted as a guess: the anchor matched several copies with the same surroundings, and the position stored with the comment named none of them as the file stood, so the copy nearest that position was highlighted, dashed, with the "passage recurs" tag.'));
  assert.ok(decisions.includes("a raw write outside the tracked path, since closed by decision 47's Bash guard; an editor save"));
  assert.ok(decisions.includes('The user said yes to breaking the tie from what the comment itself records.'));
  assert.ok(decisions.includes('`ordinal`, the 1-based index of the copy among the whole anchor\'s matches at that moment (1 when unique); `copies`, how many matches there were then; and `section`, the heading path above the passage, the text of the nearest preceding markdown headings from the top level down joined with " > ", empty for a file without headings or a non-markdown file.'));
  // the rules as the review's third round qualified them (the yield to a disagreeing heading path; decision 51 says why)
  assert.ok(decisions.includes("the rules run in order: the count of copies unchanged since the fields were written, the ordinal's copy, confirmed, unless the stored heading path names other copies and not the ordinal's, when the two fields disagree and the tie is a guess (the review's third round, 2026-09-11, said below); else, the count changed, exactly one copy under the stored heading path, that copy, confirmed; else the copy nearest the position, a guess, as before."));
  assert.ok(!decisions.includes("the ordinal's copy, confirmed; else exactly one copy under the stored heading path"), 'the unconditional first cut is gone');
  assert.ok(decisions.includes('with the card\'s words now ending "Reveal it and save again from the right copy to confirm."'));
  assert.ok(decisions.includes('The contract named two fields; `copies` is the third, since the first rule compares the count of copies with the count at the time the ordinal was written, and the ordinal alone does not carry it.'));
  assert.ok(decisions.includes('Setext headings (a line underlined with `=` or `-`) are not read as headings, a tie with no position still refuses'));
  assert.ok(decisions.includes('docs/adr/0002: six additive fields now'));
  for (const m of ['tools/file-comments-host-tiebreak.test.mjs', 'ui/webview/file-comments-tiebreak.test.ts', 'ui/webview/file-comments-tiebreak-browser.test.ts', 'tools/file-review-plan-tiebreak.test.mjs', 'tests/test_guide_files_comments_anchors.py']) {
    assert.ok(decisions.includes(`\`${m}\``), `decision 51 names ${m}`);
    assert.ok(exists(...m.split('/')), `${m} exists`);
  }
  assert.ok(!flat.includes('five additive fields'), 'the plan does not count five');
});

// ── the contract, the host paragraph and the host ───────────────────

test('the contract names the three fields beside anchorAt with their rule, and the host writes them at creation, refreshes them with the position and carves them out of the decisions\' check', () => {
  assert.ok(contract.includes('Three more romp-only fields sit beside `anchorAt` since the tie-break (2026-09-11, decision 51): `ordinal: <number>` and `copies: <number>`, the copy\'s 1-based index among the whole anchor\'s matches and their count at the moment of the write, and `section: <string>`, the heading path above the passage in a markdown file'));
  assert.ok(contract.includes("the ordinal's copy while the count of copies is unchanged, unless the stored heading path names other copies and not the ordinal's, when the two fields disagree and the tie is a guess (the same round; decision 51 says why); else, the count changed, the one copy under the stored heading path; confirmed either way; else the nearest copy to the position, a guess. Every reply carries the verdicts (`placed`, per comment id), except that while every change to the text is on record a verdict the recorded changes carry to another place is left to the next write's refresh (the same round), and the panel paints a confirmed copy plainly. The other editors and the CLIs write the whole object back, so the six fields survive them."));
  // creation: the three fields spread in place after the position, from the same stamp the refresh uses
  assert.ok(/anchor: stored\.anchor,\s*\n\s*anchorAt: loc\.from,\s*\n\s*\.\.\.copy,\s*\n\s*\.\.\.about,/.test(host), 'after the position, before the about spread');
  assert.ok(fn(host, 'buildComment').includes('stampCopy(copy, text, loc.from, stored.unique ? [loc.from] : fullMatches(text, stored.anchor, REFRESH_COPIES_MAX).hits, !!(opts && opts.markdown));'), 'an anchor made unique is 1 of 1 with no further scan');
  const stamp = fn(host, 'stampCopy');
  inOrder(stamp, ['const k = hits.indexOf(at);', 'if (k < 0) return;', 'c.ordinal = k + 1;', 'c.copies = hits.length;', 'if (markdown === undefined) return;', 'c.section = sectionAt(text, at, markdown);'], 'stampCopy');
  assert.ok(stamp.includes('if (markdown === undefined) return;'), 'a store with no judgment of the file\'s kind keeps its heading path, rather than have the file judged from anything but its name');
  // the refresh: every comment whose position names its copy once the pass is done, under the same budget
  const refresh = fn(host, 'refreshAnchorAts');
  assert.ok(refresh.includes('const seated = [];') && refresh.includes('const markdown = markdownOf(store);'), 'the seated comments, and whether the file is markdown from the judgment stamped on the store');
  assert.ok(!host.includes('isMarkdownPath(store'), 'the sidecar JSON\'s own path field never judges the file (the review, 2026-09-11)');
  const judged = fn(host, 'markdownOf');
  assert.ok(judged.includes('const m = store ? store[MARKDOWN_FILE] : undefined;') && judged.includes("if (typeof m === 'boolean') return m;") && judged.includes('return undefined;'), 'the judgment is the boolean stamped under the symbol, else none');
  assert.ok(host.includes("const MARKDOWN_FILE = Symbol('romp.markdownFile');"), 'a symbol key, so saveStore\'s JSON never carries it');
  assert.equal((host.match(/store\[MARKDOWN_FILE\] = ctx\.markdown;/g) || []).length, 2, 'stamped from the request path\'s name at load and at seed');
  assert.ok(/case 'ok': \{[^]*?store\[MARKDOWN_FILE\] = ctx\.markdown;\s*\n\s*return store;/.test(host), 'the load stamps the store it returns');
  assert.ok(host.includes('if (!store) { store = seedStore(pathsToBe.rel); store[MARKDOWN_FILE] = ctx.markdown; }'), 'a seeded store is stamped where it is made');
  inOrder(refresh, ['for (const c of seated) {', "if (c[ENGINE_PLACED]) { delete c[ENGINE_PLACED]; stampCopy(c, text, at, [at], markdown); continue; }", 'if (!affordableScan(budget, text, c.anchor)) continue;', 'stampCopy(c, text, at, hits, markdown);'], 'the stamping pass');
  assert.ok(op.includes('The refresh stamps the three fields on every comment whose position names its copy once its pass is done (`stampCopy`), under the same budget, and the decisions\' self-check carves them out with `anchorAt`.'));
  assert.ok(fn(host, 'commentsApartFromAnchorAt').includes('const { anchorAt, ordinal, copies, section, ...rest } = c;'), 'the carve-out');
  // the section helper: markdown by the file's name, ATX headings outside fences, no setext
  assert.ok(fn(host, 'isMarkdownPath').includes("return ext === 'md' || ext === 'markdown';"));
  const heads = fn(host, 'headings');
  assert.ok(heads.includes('const fences = fencedRanges(text);') && heads.includes('!inFencedRange(fences, at)'), 'a fenced line is not a heading');
  assert.ok(heads.includes("/^ {0,3}(#{1,6})(?:[ \\t]+([\\s\\S]*))?$/"), 'ATX headings, the rest of the line taken whole');
  assert.ok(!heads.includes('(.*?)') && !heads.includes('[ \\t]*$/.exec'), 'no lazy tail before an end anchor: the first cut\'s backtracked quadratically over a run of whitespace inside the line (the review\'s second round, 2026-09-11)');
  assert.ok(heads.includes(".replace(/(^|[ \\t])#+[ \\t]*$/, '').trim().replace(/\\s+/g, ' ')"), 'closing hashes, trailing whitespace and inner runs dropped by the trim, so the words read as the first cut read them');
  assert.ok(fn(host, 'sectionAt').includes("if (!markdown || typeof text !== 'string' || typeof offset !== 'number') return '';"), 'empty for a non-markdown file');
});

test('the host paragraph states locateStored\'s order, and the host takes the rules in that order for every reader of a stored anchor and for the reply\'s placed map', () => {
  // the paragraph as the review's third and fourth rounds left it: the position the quote names with one side of its
  // context comes first, and the ordinal yields to a disagreeing heading path (the fourth round's module pins the rest of it)
  assert.ok(op.includes("Every reader of a stored anchor in the host (the figure a passage names, a re-place, the reply's `placed`) goes through `locateStored` since the tie-break (2026-09-11, decision 51): the position first, where the whole anchor still sits at it, and where the quote sits at it with one side of its context whole beside it while the whole anchor sits elsewhere (`quoteSitsAt`: the passage whose surroundings on the other side were edited"));
  assert.ok(op.includes("then, when the whole anchor sits at several places and the position names none, the copy fields, `ordinal` while `copies` equals the count of matches now, unless the stored `section` names other matches and not the ordinal's, when the two fields disagree and neither confirms (the same round); else, the count changed, the one match under the stored `section`; both confirmed; else the match nearest the position, a guess, and a tie with no position refuses `anchor-ambiguous` as before; an anchor whole nowhere is the engine's."));
  // The source's order, one line per step (the review's third round, 2026-09-11, rewrote the fields' step: the copies
  // under the stored heading path are read off one grouping per anchor, copiesUnder, and the ordinal's copy is
  // confirmed only where that path names no copy or names its own; a path naming other copies and not the ordinal's
  // is two fields that disagree, and neither confirms, so the tie falls to the nearest copy, a guess). A pin of the
  // line before the rewrite kept this module red for a round: the lines below are the host's as it stands, and the
  // block after them holds the order by what locateStored answers, whatever the lines become.
  const locate = fn(host, 'locateStored');
  inOrder(locate, [
    "if (at !== undefined && sitsAt(text, anchor, at)) return span(at, true, 'position');",
    'if (budget && !affordableScan(budget, text, anchor)) return null;',
    'const { hits, more, cut } = fullMatches(text, anchor, REFRESH_COPIES_MAX, budget);',
    'if (hits.length === 0) {',
    "if (at !== undefined && quoteSitsAt(text, anchor, at)) return span(at, true, 'position');",
    "if (hits.length === 1 && !more) return span(hits[0], true, 'whole');",
    'if (!more) {',
    'const o = ordinalOf(c);',
    'const s = sectionOf(c);',
    'const under = s !== null && markdown ? copiesUnder(text, anchor, hits, markdown, s, budget) : [];',
    'if (under === null) return null;',
    'if (o && o.copies === hits.length) {',
    'const pick = hits[o.ordinal - 1];',
    "if (!under.length || sectionAt(text, pick, markdown) === s) return span(pick, true, 'ordinal');",
    '} else if (under.length === 1) {',
    "return span(under[0], true, 'section');",
    "if (at === undefined) return { error: 'anchor-ambiguous' };",
    "if (!more) return span(nearestOf(hits, at), false, 'nearest');",
    "return span(engine.locateAnchor(text, anchor, at).from, false, 'nearest');",
  ], 'locateStored');
  assert.ok(!locate.includes('hits.filter('), 'the copies under a heading path come from the grouping, not a filter of every copy per comment (the review\'s third round, 2026-09-11)');
  assert.ok(fn(host, 'ordinalOf').includes('if (!c || !Number.isInteger(c.ordinal) || !Number.isInteger(c.copies) || c.ordinal < 1 || c.copies < c.ordinal) return null;'), 'the pair is read together, defensively');
  assert.ok(fn(host, 'passageFigure').includes('const loc = locateStored(text, { ...c, anchor }, ctx.markdown);'), 'the figure a passage names');
  assert.ok(fn(host, 'doRetarget').includes('const loc = locateStored(text, { ...c, anchor: validateAnchor(c.anchor) }, ctx.markdown);'), 'a re-place');
  assert.ok(host.includes('placed: media ? {} : placedFor(store, text, ctx.markdown),'), 'every reply carries the verdicts');
  const placed = fn(host, 'placedFor');
  assert.ok(placed.includes('const loc = locateStored(text, c, markdown, refreshBudget);') && placed.includes("if (!loc || loc.error || loc.by === 'position' || loc.by === 'whole' || loc.by === 'engine') continue;"), 'a tie the position names none of, and nothing else');
  assert.ok(placed.includes('out[String(c.id)] = { at: loc.from, confirmed: loc.confirmed, by: loc.by };'));
  // behaviour, on the repo's fixture: the second "Ship it." sits under Day 2, and a heading path tells the copies apart
  const text = read('tests', 'fixtures', 'file_comments', 'report.md');
  const first = text.indexOf('Ship it.'), second = text.indexOf('Ship it.', first + 1);
  assert.equal(sectionAt(text, first, true), 'Latency report > Day 1');
  assert.equal(sectionAt(text, second, true), 'Latency report > Day 2');
  assert.equal(sectionAt(text, second, false), '', 'a non-markdown file has no heading path');
  const cap = { quote: 'Ship it.', prefix: text.slice(Math.max(0, second - ANCHOR_CTX_CAP), second), suffix: text.slice(second + 8, second + 8 + ANCHOR_CTX_CAP) };
  assert.deepEqual(locateStored(text, { anchor: cap, anchorAt: second, ordinal: 2, copies: 2, section: 'Latency report > Day 2' }, true), { from: second, to: second + 8, confirmed: true, by: 'position' });
  // behaviour, on a synthetic tied text: three copies of one paragraph under three headings, the position (0) naming
  // none. The rules answer in the order the paragraph states, and the third round's yield holds: a stored heading
  // path that names another copy and not the ordinal's makes the tie a guess.
  const para = 'The retry on timeout was observed across every run of the suite, and it held. Nothing else moved.';
  const tied = `# Report\n\n## First pass\n\n${para}\n\n## Second pass\n\n${para}\n\n## Third pass\n\n${para}\n`;
  const quote = 'it held.';
  const q0 = tied.indexOf(quote);
  const anchor = { quote, prefix: tied.slice(q0 - 24, q0), suffix: tied.slice(q0 + quote.length, q0 + quote.length + 20) };
  const copies = fullMatches(tied, anchor, 10).hits;
  assert.equal(copies.length, 3, 'the fixture: the whole anchor sits at three places');
  assert.deepEqual(copies.map((h) => sectionAt(tied, h, true)), ['Report > First pass', 'Report > Second pass', 'Report > Third pass'], 'the fixture: one copy under each heading');
  const verdict = (k, confirmed, by) => ({ from: copies[k], to: copies[k] + quote.length, confirmed, by });
  assert.deepEqual(locateStored(tied, { anchor, anchorAt: 0, ordinal: 2, copies: 3, section: 'Report > Second pass' }, true), verdict(1, true, 'ordinal'), 'the count unchanged and the path its own: the ordinal\'s copy, confirmed');
  assert.deepEqual(locateStored(tied, { anchor, anchorAt: 0, ordinal: 2, copies: 3 }, true), verdict(1, true, 'ordinal'), 'the count unchanged and no path stored: the ordinal\'s copy, confirmed');
  assert.deepEqual(locateStored(tied, { anchor, anchorAt: 0, ordinal: 3, copies: 2, section: 'Report > Third pass' }, true), verdict(2, true, 'section'), 'the count changed: the one copy under the stored path, confirmed');
  assert.deepEqual(locateStored(tied, { anchor, ordinal: 3, copies: 2, section: 'Report > Third pass' }, true), verdict(2, true, 'section'), 'the same with no position at all: the fields answer before the refusal');
  assert.deepEqual(locateStored(tied, { anchor, anchorAt: 0, ordinal: 1, copies: 3, section: 'Report > Third pass' }, true), verdict(0, false, 'nearest'), 'the count unchanged but the path names another copy and not the ordinal\'s: the fields disagree, a guess on the nearest');
  assert.deepEqual(locateStored(tied, { anchor, anchorAt: 0, ordinal: 3, copies: 2 }, true), verdict(0, false, 'nearest'), 'the count changed and no path: the nearest copy, a guess');
  assert.deepEqual(locateStored(tied, { anchor, anchorAt: 0, ordinal: 3, copies: 2, section: 'Report > Third pass' }, false), verdict(0, false, 'nearest'), 'a non-markdown file: the path never confirms, so a guess');
  assert.deepEqual(locateStored(tied, { anchor, ordinal: 3, copies: 2 }, true), { error: 'anchor-ambiguous' }, 'no position and no rule that settles it: refused, as before');
  assert.deepEqual(locateStored(tied, { anchor }, true), { error: 'anchor-ambiguous' }, 'no position and no fields (a comment the CLI made): refused, as before');
});

// ── the painting paragraph, the note, the panel and the model ───────

test('the painting paragraph and the note state the confirmed paint and the words, and the panel paints a confirmed copy plainly from the status and ends the guessed copy\'s words with the sentence', () => {
  assert.ok(ux.includes("Since the tie-break (2026-09-11, decision 51) the status carries the host's verdict for every such comment (`placed`): a copy the host confirmed from the fields stored with the comment (the ordinal's copy while the count of copies is unchanged, unless the stored heading path names other copies and not that one; else, the count changed, the one copy under the stored heading path; decision 51 has the rules) is the painter's hint in place of the stale position (`placedAt`), so it is painted as the chosen one, with no dashed ring and no tag; a guessed verdict, or none (a tie whose verdict the recorded changes carry elsewhere has none until the next write settles it, and a position the quote sits at with one side of its context whole beside it has none, the panel painting that comment by its own engine as before the tie-break; the review's third round, 2026-09-11, and its fourth), paints as before, and the card's words end by saying how to confirm the copy."));
  assert.ok(note.includes('The tie-break (2026-09-11, decision 51) closes the case the refresh leaves open: after an edit nobody recorded, the position names no copy and the changes vouch for nothing, so the copy nearest the stale position was painted as a guess for good.'));
  assert.ok(note.includes('else the nearest, a guess, whose words on the card end with "Reveal it and save again from the right copy to confirm."'));
  assert.ok(panel.includes('const at = this.placedAt(card) ?? this.viewAt(card);'), 'the hint');
  const placedAt = method(panel, 'placedAt');
  assert.ok(placedAt.includes('const p = this.status && this.status.placed && typeof this.status.placed === "object" ? this.status.placed[card.id] : undefined;'));
  assert.ok(placedAt.includes('if (!p || typeof p !== "object" || p.confirmed !== true || typeof p.at !== "number" || !Number.isFinite(p.at)) return undefined;'), 'a confirmed verdict of the right shape alone');
  assert.ok(placedAt.includes('return this.status!.bom ? p.at - 1 : p.at;'), 'mapped past a BOM like anchorAt');
  assert.ok(fn(panel, 'copyUnsureWords').includes('", not a confirmed one. Reveal it and save again from the right copy to confirm."'), 'the words end with the sentence');
  assert.ok(!/\u2014 not a confirmed one\./.test(panel), 'the em dash ending is gone');
  assert.ok(model.includes('anchorAt?: number; ordinal?: number; copies?: number; section?: string;'), 'the store comment carries the fields');
  assert.ok(model.includes('export type Placed = { at: number; confirmed: boolean; by: "ordinal" | "section" | "nearest" };'), 'the verdict type');
  assert.ok(model.includes('placed?: Record<string, Placed> | null;'), 'on the status');
});

// ── the ADR, the guide and the Tests section ────────────────────────

test('the ADR counts six additive fields and names the three new ones; the guide says what places a comment again and what saving again from the right copy does; the Tests section names this module', () => {
  assert.ok(adr.includes('Under that rule the sidecar now carries six additive fields on a comment: `target` (a region), `anchorAt`'));
  assert.ok(adr.includes('and `ordinal`, `copies` and `section` (the copy\'s index among the anchor\'s matches and their count, and the heading path above the passage, which place a comment once its position no longer names a copy; the tie-break, 2026-09-11)'));
  assert.ok(!adr.includes('three additive fields'), 'the old count is gone');
  assert.ok(guide.includes("When the file has changed around that occurrence, the comment's own record of where it was, which copy it is and the heading above it places it again. When none of those can tell which copy the comment meant, its highlight is dashed and the card carries a **passage recurs** tag: the copy shown is a guess, and the card says so. Saving the comment again from the right copy, as the card asks, adds a new card on that copy with no tag; the old card keeps its tag, so resolve it once the new one is saved."), 'the guide\'s sentence, as the review reworded it');
  assert.ok(!guide.includes('saving it again from the right copy confirms it'), 'the earlier wording promised a confirmation of the same comment, which no verb performs (the review, 2026-09-11)');
  assert.ok(tests.includes('`tools/file-review-plan-tiebreak.test.mjs` pins decision 51 and the tie-break\'s sentences here against the host (`locateStored`, `stampCopy`, the fields), the panel (`placedAt`, the words), the model, the ADR\'s six fields and the guide\'s sentence, and the tie-break modules against the tree.'));
  // no em dash in the tie-break's records
  for (const [name, text] of [['decision 51', decisions.slice(decisions.indexOf('51. **'))], ['the ADR bullet', adr.slice(adr.indexOf('six additive'), adr.indexOf('- A romp-only field'))], ['the guide sentence', guide.slice(guide.indexOf('When the file has changed around that occurrence'), guide.indexOf('When the session has'))]]) {
    assert.ok(!text.includes('\u2014'), `${name} has no em dash`);
  }
});

// The marks' drag rule (plans/file-review.md: the surface section's inline-marks sentence, the Tests bullet and decision
// 41, 2026-09-09). The slice's review found the records saying that a plain click or a tap on any change mark or comment
// highlight opens its card, which the code as first built did not do while a selection stood elsewhere in the body: the
// guard read any selection with both ends in the body as a drag's, on the premise that a press collapses a standing
// selection, and a press on a deletion's struck label (generated text under user-select: none), on a region rectangle
// (the figure overlay cancels the press) or on a mark inside an author's link collapses nothing, so those clicks did
// nothing until the selection was dropped. The fix reads the selection against the clicked mark (endInside, both ends,
// the mark's edges included) and takes the press pulse back on a click it stands down. This module holds each statement
// the records make to the text that makes it true: the plan's three passages, the guard's shape (the clicked control,
// both ends, no body containment), the mechanics the decision gives for the marks whose press collapses nothing (the
// sheets' user-select rule and generated text, the overlay's cancelled press), the pulse taken back, and the two modules
// the records name with the cases they credit them with. Open questions carries nothing of it: the build answered the
// question. Synthetic: only the repo's own text.
// Run: node --test tools/file-review-plan-markclick.test.mjs
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
const regions = read('ui', 'webview', 'file-comments-regions.ts');
const actions = read('ui', 'webview', 'actions.ts');
const unit = read('ui', 'webview', 'file-comments-markclick.test.ts');
const browser = read('ui', 'webview', 'file-comments-markclick-browser.test.ts');
const controls = read('ui', 'webview', 'file-comments-markclick-controls.test.ts');
const controlsBrowser = read('ui', 'webview', 'file-comments-markclick-controls-browser.test.ts');
const sheets = [['styles.css', read('ui', 'webview', 'styles.css')], ['feed.css', read('ui', 'webview', 'feed.css')]];

// The text between two headings, hard wraps collapsed so an assertion survives a rewrap.
function section(from, to) {
  const a = plan.indexOf(from);
  assert.ok(a >= 0, `heading ${JSON.stringify(from)} not found in the plan`);
  const b = plan.indexOf(to, a + from.length);
  assert.ok(b > a, `heading ${JSON.stringify(to)} not found after ${JSON.stringify(from)}`);
  return plan.slice(a, b).replace(/\s+/g, ' ');
}
// The inline marks' rule lives in the UX section's account of the surface, not under the Slice 2 build section.
const surface = section('### The surface, in its Slice 2 state', '### Commenting from either view, and in every format');
const tests = section('## Tests', '## Docs');
const decisions = section('## Decisions', '## Open questions for the user');
const open = section('## Open questions for the user', '## Upstream');

// Decision 41 on this branch; a sibling branch adds decisions of its own, and whichever lands second renumbers, so the
// decision is found by its title, never by its number.
const D_TITLE = '**A comment can be made inside a tracked change without replying to the change** (2026-09-09).';
const dAt = decisions.indexOf(D_TITLE);
assert.ok(dAt >= 0, 'the decision is in the Decisions section');
const next = /\d+\. \*\*/.exec(decisions.slice(dAt + D_TITLE.length));   // the decision after it, when one follows
const decision = next ? decisions.slice(dAt, dAt + D_TITLE.length + next.index) : decisions.slice(dAt);

// ── the records: what the plan says ─────────────────────────────────────────────────────────────────────────

test('the surface sentence: a click or a tap on a mark opens its card whatever selection stands elsewhere, and the guard reads the clicked mark', () => {
  assert.ok(surface.includes('A comment can be made inside a change without replying to it (2026-09-09): a click or a tap on a change mark or a comment highlight opens its card, whatever selection stands elsewhere in the body, and a selection made by dragging inside one leaves a comment on those words, since the click that ends a drag is not a tap (the panel\'s `dragClick`, which reads the selection against the clicked mark alone; decision 41).'));
});

test('decision 41 records the guard against the clicked mark, the review that narrowed it, the marks whose press collapses nothing, the edge tolerance and the pulse', () => {
  assert.ok(decision.includes('In the `fcchange` and `fcopen` handlers a click arriving with a non-collapsed selection whose anchor and focus both lie inside the clicked mark does nothing (`dragClick`)'));
  assert.ok(decision.includes('A plain click or a tap on a mark opens the card as before: its click arrives with the selection collapsed, or standing with no end inside the clicked mark, and the guard yields only to a selection whose ends both lie inside that mark, whatever the control\'s press did to a standing selection'), 'the plain click is explained by the guard\'s line, not by a collapse at the press');
  assert.ok(!/collapses (a|the) (standing )?selection at the press, so it opens the card/.test(decision), 'no collapse-at-press premise stands for any control: a comment highlight inside an author\'s link keeps a standing selection through its press (the browser leg\'s second test)');
  assert.ok(!decision.includes('both lie in the viewer\'s body does nothing'), 'the body-wide guard is no longer the rule');
  assert.ok(decision.includes('The guard reads the clicked mark rather than the whole body since the slice\'s review (2026-09-09, with a real mouse in Chromium and Firefox, Rendered and Raw).'));
  assert.ok(decision.includes('a press on a deletion\'s struck label (generated text under `user-select: none`), on a region rectangle (the figure overlay cancels its `pointerdown`, and with it the mousedown that would have collapsed one), on a mark inside an author\'s link (a draggable anchor) or on a framed picture collapses nothing, so with words selected in another paragraph a click on any of them opened nothing until the selection was dropped.'));
  assert.ok(decision.includes('Read against the mark, the guard yields only to the drag\'s own selection: a drag that ends on the mark it began in puts both ends inside it, a drag that leaves the mark fires its click on the common ancestor and never on the mark, a selection standing elsewhere or spanning the mark from outside has no end inside it, and no selection end can lie inside a deletion\'s point or a rectangle, so those clicks open the card whatever stands selected.'));
  assert.ok(decision.includes('With the panel closed the marks are painted too, and a drag inside one behaves as a drag over any passage does then: no panel opens and no card, since the Comment float is the open panel\'s; a plain click on the mark opens both.'));
  assert.ok(decision.includes('An engine may report a drag\'s end at the mark\'s edge as a point in the mark\'s parent or in the neighbouring text rather than in the mark; `endInside` takes both as the mark\'s.'));
  assert.ok(decision.includes('The click stood down shows nothing: the press pulse the delegate put on the mark before the handler ran comes off in the same task (`actions.ts`).'));
  assert.ok(decision.includes('`file-comments-markclick.test.ts` and `file-comments-markclick-controls.test.ts` drive the guard over the stand-in; `file-comments-markclick-browser.test.ts` and `file-comments-markclick-controls-browser.test.ts` drag a real mouse in Chromium and Firefox, Rendered and Raw: inside an insertion\'s mark, and, with words selected in another paragraph, on a deletion\'s label, the marks inside a link, a region rectangle and a framed figure.'));
});

test('Open questions carries nothing of the marks\' drag rule: the build answered it', () => {
  assert.ok(!/drag rule|dragClick|struck label|region rectangle/.test(open), 'the narrowing was built, not left to the user');
});

test('the Tests bullet names the stand-in\'s cases, the browser leg\'s second test, the controls modules and this module, and the four modules exist with the cases credited', () => {
  assert.ok(tests.includes('The marks\' drag rule (2026-09-09, decision 41): `ui/webview/file-comments-markclick.test.ts` drives the `fcchange` and `fcopen` handlers over the behavior suite\'s stand-in with the live selection faked per case (inside the mark, elsewhere in the body with none of it in the mark, collapsed, none, in the aside, one end out; the pointer\'s click with `detail` 1 and the keyboard\'s activation through the row\'s keydown with 0, as browsers dispatch them);'));
  assert.ok(tests.includes('its second test per engine selects words in another paragraph and clicks a deletion\'s struck label, and in Rendered an insertion\'s mark and a comment highlight inside an author\'s link, marks whose press collapses no selection: each opens its card and scrolls as with no selection (in Raw the link\'s label is plain text, whose press collapses the selection, the control).'));
  assert.ok(tests.includes('`ui/webview/file-comments-markclick-controls.test.ts` drives the guard as read against the clicked mark over the stand-in: a selection standing elsewhere in the body, or spanning the mark from outside, leaves the click a click for a change mark, a deletion\'s point and a comment highlight; the drag\'s own click still opens nothing and leaves no press pulse; a drag\'s end reported at the mark\'s edge is the mark\'s and one past it is not; and with the panel closed a drag inside a mark opens no panel and no card while a plain click opens both.'));
  assert.ok(tests.includes('`ui/webview/file-comments-markclick-controls-browser.test.ts` makes that state with a real mouse over the real viewer and panel in Chromium and Firefox: with words selected in another paragraph a click on a deletion\'s label, on a mark inside an author\'s link, on a region rectangle and on a framed figure opens its card; a drag inside an insertion\'s mark opens nothing and leaves no pulse; a drag ending at the mark\'s last character is the drag\'s; a tap on the deletion label with a selection standing opens the card (Chromium\'s touch); and with the panel closed the label and the frame open the panel and the card, the drag neither.'));
  assert.ok(tests.includes('`tools/file-review-plan-markclick.test.mjs` holds this bullet, the surface sentence and decision 41 to the panel, the sheets, the overlay and the four modules.'));
  for (const f of ['file-comments-markclick.test.ts', 'file-comments-markclick-browser.test.ts', 'file-comments-markclick-controls.test.ts', 'file-comments-markclick-controls-browser.test.ts']) {
    assert.ok(fs.existsSync(path.join(REPO, 'ui', 'webview', f)), `${f} exists`);
  }
  // the controls modules' cases, as the bullet credits them
  assert.ok(/test\("a change mark: a selection standing elsewhere in the body, none of it in the mark, is not this click's drag — the card opens/.test(controls), 'a selection elsewhere leaves the click a click');
  assert.ok(/test\("a deletion's point \(its label CSS-generated, so its press collapses nothing\): the click with a selection standing elsewhere opens its card/.test(controls), 'the deletion\'s point');
  assert.ok(/test\("a change mark: a selection spanning the mark from outside .* is not its drag — the card opens/.test(controls), 'a selection spanning the mark from outside');
  assert.ok(/test\("the drag's own click \(both ends inside the mark\) still opens nothing: no card, no scroll, no focus change — and no press pulse/.test(controls), 'the drag\'s own click, no pulse');
  assert.ok(/test\("a drag's end reported at the mark's edge .* is the mark's; one past the edge is not/.test(controls), 'the edge tolerance');
  assert.ok(/test\("with the panel closed the marks are painted, and a drag inside one behaves as a drag over any passage does then: no panel opens, no card; a plain click on the mark opens both/.test(controls), 'the panel-closed ruling');
  assert.ok(controlsBrowser.includes("with words selected in another paragraph a click on a deletion's label, on a mark inside an author's link, on a region rectangle and on a framed figure opens its card; a drag inside an insertion's mark still opens nothing and leaves no press pulse; the panel closed, the label and the frame open the panel and the card, the drag neither"), 'the controls browser leg\'s test');
  assert.ok(/a tap on the deletion label with\s*\/\/ a selection standing \(Chromium, a touch screen\) opens the card/.test(controlsBrowser), 'the tap case is in the leg\'s account');
  assert.ok(/const elsewhere = \(m: El\): Sel =>/.test(unit), 'the stand-in fakes a selection standing elsewhere in the body, none of it in the mark');
  assert.ok(/test\("a change mark: a selection standing elsewhere in the body, /.test(unit), 'the change mark\'s case');
  assert.ok(/test\("a comment highlight: a selection standing elsewhere in the body, /.test(unit), 'the comment highlight\'s case');
  assert.ok(browser.includes('a selection standing elsewhere in the body leaves a click on a mark a click'), 'the browser leg\'s second test');
  assert.ok(browser.includes("a deletion's label, whose press collapses no selection (user-select none)"), 'it clicks the deletion\'s label');
  assert.ok(browser.includes("an insertion's mark and a comment's highlight inside an author's link"), 'and the marks inside a link');
});

// ── the code: what makes each statement true ──────────────────────────────────────────────────────────────────

test('the guard reads the clicked control, both selection ends inside it or at its edges, and takes the pulse back: no body containment', () => {
  assert.ok(panel.includes('fcchange: (x, ev) => { ev.preventDefault(); if (this.dragClick(ev)) return; this.openPanel(); this.showCard("chg:" + x.dataset.id!); },'));
  assert.ok(panel.includes('fcopen: (x, ev) => { ev.preventDefault(); if (this.dragClick(ev)) return; this.openPanel(); this.showCard(this.cardKey(x.dataset.id!)); },'));
  const guard = /private dragClick\(ev: Event\): boolean \{\n([\s\S]*?)\n  \}/.exec(panel);
  assert.ok(guard, 'dragClick');
  const body = guard[1];
  assert.ok(body.includes('if ((ev as MouseEvent).detail === 0) return false;'), 'a click with no pointer behind it is never a drag\'s');
  assert.ok(body.includes('if (!sel || sel.isCollapsed || !sel.anchorNode || !sel.focusNode) return false;'), 'a collapsed selection, or none, opens the card');
  assert.ok(body.includes('const x = at && typeof at.closest === "function" ? at.closest("[data-act]") : null;'), 'the control the click landed on, resolved as the delegate resolves it');
  assert.ok(body.includes('if (!x || !endInside(x, sel.anchorNode, sel.anchorOffset) || !endInside(x, sel.focusNode, sel.focusOffset)) return false;'), 'both ends inside the clicked mark, or the click is a click');
  assert.ok(body.includes('x.classList.remove("romp-acted");'), 'the pulse comes off the mark the handler stands down on');
  assert.ok(!body.includes('this.ctx.body()'), 'the body is not the line: a selection standing elsewhere in it leaves the click a click');
  // endInside: the mark's edges as the engines report them (the parent at the mark's index or the next; the neighbouring
  // text's end or start)
  const inside = /function endInside\(x: Element, node: Node, offset: number\): boolean \{\n([\s\S]*?)\n\}/.exec(panel);
  assert.ok(inside, 'endInside');
  assert.ok(inside[1].includes('if (x.contains(node)) return true;'));
  assert.ok(inside[1].includes('if (node === p) { const i = Array.prototype.indexOf.call(p.childNodes, x); return offset === i || offset === i + 1; }'), 'a point in the parent at the mark\'s start or end');
  assert.ok(inside[1].includes('if (node === x.previousSibling) return offset === (node as Text).length;'), 'the end of the text before the mark');
  assert.ok(inside[1].includes('if (node === x.nextSibling) return offset === 0;'), 'the start of the text after it');
  assert.ok(/handler that STANDS DOWN on a click it was routed/.test(actions), 'actions.ts says a handler that stands down takes the pulse back');
});

test('a deletion\'s struck label is generated text under user-select: none in both sheets, so a press on it collapses no selection', () => {
  for (const [name, css] of sheets) {
    assert.ok(/\.fc-del \{[^}]*user-select: none;/.test(css), `${name}: .fc-del is user-select: none`);
    assert.ok(/\.fc-del::before \{ content: attr\(data-fc-text\); text-decoration: line-through;/.test(css), `${name}: the struck text is CSS-generated, no text node for a selection end`);
  }
});

test('a region rectangle\'s press is cancelled by the overlay, so no mousedown collapses a standing selection', () => {
  const down = /o\.addEventListener\("pointerdown", \(ev: PointerEvent\) => \{\n([\s\S]*?)\n    \}\);/.exec(regions);
  assert.ok(down, 'the overlay\'s pointerdown handler');
  assert.ok(down[1].includes('ev.preventDefault();'), 'the press\'s default is cancelled: no selection starts behind the overlay, and no mousedown follows');
  assert.ok(down[1].includes('if (this.hooks.onPress) this.hooks.onPress();'), 'the panel\'s press hook runs, hiding the float as hideFloatOnDown does for a mousedown');
});

// A figure opens in detail (plans/markdown-viewer.md, "Follow-on: Link navigation", L3): the source pins beside the browser
// leg (file-figure-open-browser.test.ts, which lays the control out and clicks it in Chromium). What is pinned here is the shape
// the browser leg cannot read off a page: the control's one path into the DOM (decideFigureControl: after figureAnchor's climb,
// never a wrapper, found by its mark, skipped inside a gate's placeholder), what it opens (figureTarget: the model's figurePath
// for a file of the session, a tab for an http source, nothing for a `data:` one), where it is decided (mdBlock's file arm after
// the anchors; the body's `load` and `error` capture pair for a figure the browser answers for later), how a click on it or on a bare figure is routed
// (a listener of its own beside the links', with the guards for a link, a panel mark, the open panel and a drag-select), the
// label lookup that steps past it, the two text walks that skip it, the glyph, and the sheets' rules under `screen`, read as rules through ui/webview/css-rules.mjs. Every pin
// reads the tree's own source, so a rename here fails loudly. Synthetic values only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { cssRules, renderRule, underScreen } from "./css-rules.mjs";

const web = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const VIEW = web("file-view.ts");
const ICONS = web("icons.ts");
const ANCHOR = web("anchor-map.ts");
const READER = web("reader-place.ts");
const SHEETS: Array<[string, string]> = [["styles.css", web("styles.css")], ["feed.css", web("feed.css")]];
/** The text from one anchor to the next, both present. */
const between = (src: string, from: string, to: string): string => {
  const a = src.indexOf(from); assert.ok(a >= 0, from + " present");
  const b = src.indexOf(to, a); assert.ok(b > a, to + " present after " + from);
  return src.slice(a, b);
};

test("the control: one decision (decideFigureControl) puts a button of the bar's glyph dress after figureAnchor's climb, marked, titled Open the picture, never inside a gate's placeholder, never twice, and only for a figure with something to open (figureWantsControl)", () => {
  const fn = between(VIEW, "function decideFigureControl(img: Element, filePath: string): void {", "function addFigureControls(");
  const want = between(VIEW, "function figureWantsControl(img: Element, anchor: Element, filePath: string): boolean {", "function decideFigureControl(");
  assert.match(want, /if \(img\.closest\('\[data-act="' \+ GATE_ACT \+ '"\]'\)\) return false;/, "a gated figure waits for its load");
  assert.match(want, /if \(figureTarget\(img, filePath\) === null\) return false;/, "none for a figure with nothing to open");
  assert.match(fn, /const anchor = figureAnchor\(img\);\n\s*const standing = figureControlAfter\(anchor\);\n\s*const want = figureWantsControl\(img, anchor, filePath\);\n\s*if \(standing\) \{ if \(!want\) removeFigureControl\(standing\); return; \}\n\s*if \(!want\) return;/, "one control per figure: the verdict against the one standing, added when missing and wanted, removed when standing and unwanted (the removal hands the keyboard on first, removeFigureControl)");
  assert.match(fn, /el\("button", "fileview-btn fileview-icon " \+ FIGOPEN_CLASS\)/, "the bar's glyph dress and the control's own class");
  assert.match(fn, /b\.type = "button"; const glyph = figureControlGlyph\(\); if \(glyph\) b\.appendChild\(glyph\); b\.dataset\.icon = "1";/, "the icon family's drawing, cloned into the control (never an innerHTML write on the control: it stands under the Rendered box during the render, and file-view-figures-gate-adopt.test.ts records a live re-parse there as a red; the author's closing pass after the file review's round 5, records-1)");
  const glyphFn = between(VIEW, "function figureControlGlyph(): Node | null {", "/**");
  assert.match(glyphFn, /const holder = el\("span"\); holder\.innerHTML = ICON_EXPAND; figureGlyph = holder\.firstElementChild \?\? null;/, "the glyph parsed once onto a holder that enters no document");
  assert.match(glyphFn, /return figureGlyph \? figureGlyph\.cloneNode\(true\) : null;/, "and cloned per control");
  assert.doesNotMatch(fn.slice(0, fn.indexOf("/** The control's glyph")), /innerHTML|outerHTML|insertAdjacentHTML/, "no markup write in the decision itself");
  assert.match(fn, /b\.setAttribute\(FIGOPEN_MARK, ""\);/, "the mark it is found by");
  assert.match(fn, /b\.title = FIGURE_OPEN_TITLE; b\.setAttribute\("aria-label", FIGURE_OPEN_TITLE\);/, "the words in the title and the aria-label");
  assert.match(fn, /parent\.insertBefore\(b, anchor\.nextSibling\);/, "the anchor's next sibling: a sibling, never a wrapper");
  assert.doesNotMatch(fn, /tabIndex|tabindex/, "a button is in the tab order as it is: nothing takes it out");
  assert.match(VIEW, /\nconst FIGOPEN_MARK = "data-fv-figopen";\n/); assert.match(VIEW, /\nconst FIGOPEN_CLASS = "fv-figopen";\n/);
  assert.match(VIEW, /\nexport const FIGURE_OPEN_TITLE = "Open the picture";\n/);
  assert.match(ICONS, /^export const ICON_EXPAND = svg\(/m, "the glyph in icons.ts");
  assert.match(VIEW, /import \{ [^}]*ICON_EXPAND \} from "\.\/icons";/, "imported beside the bar's glyphs");
  // found by the mark alone: the sanitizer keeps an author's class and never a data-* attribute
  const after = between(VIEW, "function figureControlAfter(anchor: Element): HTMLElement | null {", "/**");
  assert.match(after, /hasAttribute\(FIGOPEN_MARK\)/); assert.doesNotMatch(after, /FIGOPEN_CLASS|classList/);
});

test("what it opens (figureTarget): the model's figurePath for a source on the session's disk, a tab's address for an http or protocol-relative source, null otherwise; rewriteFigureSrcs keeps its own join, which the model test pins as the same", () => {
  assert.match(VIEW, /import \{ headVerdict, mtimeMoved, ABSENT, figurePath \} from "\.\/file-comments-model";/, "the model's join, not a fourth copy");
  const fn = between(VIEW, "function figureTarget(img: Element, filePath: string): FigureTarget | null {", "/** The control a click landed on");
  assert.match(fn, /const dest = chosenSource\(img\);/, "the candidate the browser chose, as the author wrote it (chosenSource: currentSrc mapped to the authored candidate; the src by pictureDest's rule when the browser chose it or has not picked)");
  assert.match(fn, /const p = figurePath\(filePath, dest\);\n\s*if \(p !== null\) return \{ kind: "file", path: p \};/);
  assert.match(fn, /if \(\/\^https\?:\/i\.test\(dest\) \|\| dest\.startsWith\("\/\/"\)\) return \{ kind: "web", href: absUrl\(dest\) \};/, "an http source: a tab, resolved as the browser resolved the fetch");
  assert.match(fn, /return null;\n\}/, "a data: URL or any other scheme: nothing to open");
});

test("where it is decided: mdBlock's file arm after the anchors are sorted; a figure the browser answers for after the paint through one capture-phase load and error pair on the body, armed per open and dropped with the viewer; a URL document adds none", () => {
  const md = between(VIEW, "function mdBlock(text: string, doc?: MdDocLoc): HTMLElement {", "\n}\n");
  const fileArm = between(md, 'if (doc && doc.kind === "file") {', "} else {");
  assert.ok(fileArm.indexOf("linkMarkdownAnchors(box, doc.path);") < fileArm.indexOf("addFigureControls(box, doc.path);"), "after the anchors: a link holding the figure is sorted before the control goes in after it");
  assert.equal((md.match(/addFigureControls\(/g) || []).length, 1, "the file arm alone: a URL document's figures get no control");
  const arm = between(VIEW, "function armFigureControls(body: HTMLElement, filePath: string): () => void {", "\n}\n");
  assert.match(arm, /const img = figureOf\(e\); if \(img && figureState\(img\) !== "standin"\) decideFigureControl\(img, filePath\);/, "figureOf's rule: an img of the box outside a placeholder, carrying the browser's record");
  assert.match(arm, /body\.addEventListener\("load", decide, true\);\n\s*body\.addEventListener\("error", decide, true\);/, "capture: an img's load and error do not bubble");
  assert.match(arm, /return \(\) => \{ body\.removeEventListener\("load", decide, true\); body\.removeEventListener\("error", decide, true\); \};/);
  assert.equal((arm.match(/addEventListener\(/g) || []).length, 2, "one pair, nothing per paint or per img");
  assert.match(VIEW, /ctx\.onClose\(armFigureLabels\(body\)\);\n(?:\s*\/\/[^\n]*\n)*\s*ctx\.onClose\(armFigureControls\(body, path\)\);/, "armed beside the labels' listeners, dropped through the same close hooks");
  // the label lookup steps past the control, and the label is inserted where it reads it back
  assert.match(VIEW, /const n = \(figureControlAfter\(anchor\) \|\| anchor\)\.nextSibling;/, "figureLabelAfter reads past the control");
  assert.match(VIEW, /parent\.insertBefore\(label, \(figureControlAfter\(anchor\) \|\| anchor\)\.nextSibling\);/, "the label goes after the control");
});

test("the click: a listener of its own on the body beside the links'; the control's click is the figure's own; a bare figure's click yields to a link, a panel mark, the open panel and a drag-select; a remote picture is a tab, a modified click the /file URL in a tab (stopped before the row), a plain one the viewer through openFigureInViewer with no target; a click another listener already answered stands down first", () => {
  const listeners = VIEW.split('body.addEventListener("click", (ev) => {');
  assert.equal(listeners.length, 3, "two click listeners on the viewer's body: the links' and the figures'");
  const fig = listeners[2].split("\n  });\n")[0];
  assert.match(fig, /^\s*if \(ev\.defaultPrevented\) return;\n\s*const t = ev\.target as Element \| null;\n\s*const control = figureControlOf\(t, body\);/m, "a click another listener already answered (the gate listener's restore of a placeholder's img) stands down before anything is read");
  assert.match(fig, /const control = figureControlOf\(t, body\);\n\s*if \(control\) \{ const img = figureOfControl\(control\); if \(img\) openFigure\(img, ev\); return; \}/, "the control first, wherever it stands");
  assert.match(fig, /const img = bareFigureOf\(t, body\);\n\s*if \(!img \|\| linkOf\(t\)\) return;/, "a figure inside a link: the author's link (the links listener)");
  assert.match(fig, /if \(panelMark\(t\) && !wantsOwnTab\(ev\)\) return;\n\s*if \(asideOpen && !wantsOwnTab\(ev\)\) return;\n\s*if \(selectionOpenIn\(box\)\) return;\n\s*openFigure\(img, ev\);/, "the mark's card, the open panel's offer and drag, a drag-select: each keeps the plain click");
  const open = between(VIEW, "const openFigure = (img: Element, ev: MouseEvent): void => {", "\n  };\n");
  assert.match(open, /const target = figureTarget\(img, path\);\n\s*if \(!target\) return;/);
  assert.match(open, /if \(wantsOwnTab\(ev\)\) ev\.stopPropagation\(\);/, "a modified click stops before the row's delegate, as a link's does");
  assert.match(open, /if \(target\.kind === "web"\) \{ openUrlTab\(target\.href\); return; \}/, "a remote picture: a tab, never the viewer");
  assert.match(open, /if \(wantsOwnTab\(ev\) && openFileTab\(target\.path, sid \|\| null\)\) return;/, "the /file URL in a tab; a blocked popup falls through");
  assert.match(open, /openFigureInViewer\(target\.path, sid \|\| null\);/, "the viewer through the figure's own door, with no target: the trail's push, and no Recent row (file-view-figure-recent-browser.test.ts)");
  assert.match(VIEW, /\nfunction openFigureInViewer\(path: string, sid: string \| null\): void \{\n  trailNext = "push";\n  try \{ openFileView\(path, sid, \{ at: null \}\); \} finally \{ trailNext = null; \}\n\}\n/, "the door: the tag set and cleared as openFromViewer sets and clears it, openFileView itself and not the host's opener");
  assert.doesNotMatch(fig + open, /ev\.stopPropagation\(\)(?!;\s*\/\/ a modified)/, "a plain click is never stopped");
  // the links' listener is as it was: its pins in file-view-links.test.ts read the first listener's text
  const links = listeners[1].split("\n  });\n")[0];
  assert.match(links, /const x = linkOf\(t\);\n\s*if \(!x\) return;/);
  assert.doesNotMatch(links, /figure/, "the links' listener knows nothing of figures");
});

/** Number words for the docstring's count, derived from the list it counts (extra6-3): a local table, since the tools pins' table
 *  (tools/markdown-viewer-plan-linknav.test.mjs NUMBER_WORDS) is an .mjs module a .ts test does not import. */
const NUMBER_WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve"];

test("SOURCE-TEXT pins of the two text-read control lists (anchor-map.ts's CONTROL_CLASSES entry and isFigureCompanion in holdsContent; reader-place.ts's CONTROL_CLASSES entry, its docstring's count word and the partition's two addends derived from the lists): each entry is defensive, inert while the control has no text node of its own, so no glyph-only scene reds on it; the executed subjects are isFigureCompanion (anchor-map.test.ts: the control at the box's top level is no block's node) and the entries under a labelled control (anchor-map.test.ts's caption case, md-config-figure-gate-place.test.ts's labelled scene), while md-config's glyph-only scenes hold the pairing and the place beside the control; the structural read's exclusion of both companions (reader-place.ts blockElementsOf, at the root's level and a wrapper's) is pinned by execution alone, in file-view-place-blocks.test.ts, since a source pin on where it stands satisfied nothing a driven case does not", () => {
  const classes = between(ANCHOR, "const CONTROL_CLASSES = [", "];");
  assert.match(classes, /"fv-figerr",[^\n]*\n\s*"fv-figopen",/, "anchor-map.ts: after the label, the last entry");
  assert.match(ANCHOR, /const isFigureCompanion = \(n: DNode\): boolean => hasClass\(n, "fv-figerr"\) \|\| hasClass\(n, "fv-figopen"\);/, "the two companions of a figure");
  assert.match(ANCHOR, /const holdsContent = \(n: DNode\): boolean => isElement\(n\) \? !blankMark\(n\) && !isFigureCompanion\(n\) : isText\(n\) && stripWs\(n\.data\) !== "";/, "left out of the top-level nodes, as the label is");
  assert.doesNotMatch(ANCHOR, /isFigureLabel/, "the label-only predicate is gone: one predicate for both");
  // reader-place.ts: the count word compared to the list's own length, never to a literal (the file review's round 8, extra6-3:
  // a literal "seven" stayed green under an eighth entry). The list is read off its own line, a statement at column 0, so a comment
  // quoting it elsewhere is not what is counted.
  const list = /^const CONTROL_CLASSES = \[([^\]]*)\];$/m.exec(READER);
  assert.ok(list, "reader-place.ts declares CONTROL_CLASSES on one line at column 0");
  const entries: string[] = list![1].match(/"[a-z-]+"/g) || [];
  assert.ok(entries.length > 0, "reader-place.ts's CONTROL_CLASSES parses to its entries");
  const word = NUMBER_WORDS[entries.length];
  assert.ok(word, "a number word for " + entries.length + " entries");
  assert.match(READER, new RegExp("These " + word + " are in anchor-map\\.ts's CONTROL_CLASSES"), "the count in the comment follows the list: " + entries.length + " entries, so \"These " + word + "\"");
  // the partition's two addends, derived as the sum is (the file review's round 10, regression-2: "the other five" and "The last
  // two" had stayed typed beside the derived "These seven", the shape round 8's ruling named, a derived sum over typed addends):
  // the companions' list is read off its own line, its length is one addend, the difference the other, and each is held to
  // the docstring's word, the comment's wraps joined first so a wrap between "The last" and its word is read through
  const companionList = /^const FIGURE_COMPANION_CLASSES = \[([^\]]*)\];$/m.exec(READER);
  assert.ok(companionList, "reader-place.ts declares FIGURE_COMPANION_CLASSES on one line at column 0");
  const companions: string[] = companionList![1].match(/"[a-z-]+"/g) || [];
  assert.ok(companions.length > 0 && companions.every((c) => entries.includes(c)), "the companions are a subset of CONTROL_CLASSES, so the docstring's partition is of that list: " + companions.join(", "));
  const last = NUMBER_WORDS[companions.length], other = NUMBER_WORDS[entries.length - companions.length];
  assert.ok(last && other, "number words for " + companions.length + " companions and " + (entries.length - companions.length) + " others");
  const doc = READER.replace(/\n \*  /g, " ");
  assert.match(doc, new RegExp("The last " + last + ", a figure's companions, stand at a level BESIDE a block's element"), "the companions' addend follows FIGURE_COMPANION_CLASSES: " + companions.length + ", so \"The last " + last + "\"");
  assert.match(doc, new RegExp("the other " + other + " are a block's element"), "the rest's addend is the difference: " + (entries.length - companions.length) + ", so \"the other " + other + "\"");
  assert.ok(entries.includes('"fv-figopen"'), "the control's class is in reader-place.ts's text-read list, beside the label's (the list's contents; the labelled scene in md-config-figure-gate-place.test.ts is what executes it)");
});

/** The bound of the closed set over the control's sheet rules, stated in its assertion messages (the author's closing pass after the
 *  file review's round 10, mechanism-2). */
const BOUND = " (the population is the rules whose selector names the control's class; a rule whose selector would match the control's element without naming the class is outside what this set closes, a bound stated here and in the plan's L3, not read";

test("the sheets: the control rests transparent over the figure's corner with a zero-width margin box, positioned above the layer's overlay; every rule naming the control's class that reveals it (the pointer over the figure or the control, a keyboard focus, a device with no hover) is under screen, so print shows none of it and the print block carries no line for it; the population the set closes is the rules whose selector names the class, a bound stated, not read", () => {
  for (const [name, css] of SHEETS) {
    assert.match(css, /\n\.fileview-md \.fv-figopen \{ position: relative; z-index: 1; vertical-align: top; margin: 0 6px 0 -28px; top: 6px; padding: 3px; background: var\(--bg\); opacity: 0; \}\n/, name + ": the rest");
    assert.match(css, /\n\.fileview-md \.fv-figopen-left \{ float: left; \}\n\.fileview-md \.fv-figopen-right \{ float: right; margin: 0 -28px 0 6px; \}\n/, name + ": the float twins");
    assert.match(css, /\n@media screen \{ \.fileview-md :hover \+ \.fv-figopen, \.fileview-md \.fv-figopen:hover, \.fileview-md \.fv-figopen:focus-visible \{ opacity: 1; \} \}\n/, name + ": the reveal, screen only");
    assert.match(css, /\n@media screen and \(hover: none\) \{ \.fileview-md \.fv-figopen \{ opacity: 0\.8; \} \}/, name + ": no hover keeps it visible, screen only");
    const print = css.slice(css.indexOf("\n@media print {"), css.indexOf("\n}", css.indexOf("\n@media print {")));
    assert.doesNotMatch(print, /fv-figopen/, name + ": the print block names it nowhere");
    // the closed set over the control's rules, read as RULES (ui/webview/css-rules.mjs, the reader this home shares with
    // tools/markdown-viewer-plan-linknav.test.mjs: brace-matched over the comment-stripped sheet, each rule with the at-rules
    // enclosing it), so a rule written the sheets' own way, indented inside an at-rule block or on a grouped selector wrapped
    // across lines, is in the population (the file review's round 10, correctness-1 with tests-1 and ui-1: the set had been
    // keyed on lines at column zero carrying the class and a brace, and a reveal in either shape stood outside it with every
    // pin green). Outside a screen-only at-rule exactly the rest, the hover background and the float twins; under one the
    // reveal and the no-hover rule (the file review's round 8, fresh-4: the guard before the set matched two opacity spellings,
    // so a reveal spelled any other way outside screen passed it). The population is the rules whose SELECTOR names the
    // control's class: a rule whose selector would match the control's element without naming the class (`.fileview-md img +
    // button`, an attribute selector, a universal) is outside what the set closes, in both homes; the bound is stated here, in
    // the plan's L3 and in the reader's header rather than read, since reading it means matching selectors against the
    // element (the author's closing pass after the file review's round 10, mechanism-2).
    const control = cssRules(css).filter((r) => /fv-figopen/.test(r.selector));
    assert.deepEqual(control.filter((r) => !underScreen(r.chain)).map(renderRule), [
      ".fileview-md .fv-figopen { position: relative; z-index: 1; vertical-align: top; margin: 0 6px 0 -28px; top: 6px; padding: 3px; background: var(--bg); opacity: 0; }",
      ".fileview-md .fv-figopen:hover { background: var(--bg) linear-gradient(var(--accent-wash), var(--accent-wash)); }",
      ".fileview-md .fv-figopen-left { float: left; }", ".fileview-md .fv-figopen-right { float: right; margin: 0 -28px 0 6px; }",
    ], name + ": the rules naming the control outside a screen-only at-rule, however the sheet writes them, are exactly the rest, the hover background and the float twins; any other rule naming the class there is one a print would apply" + BOUND + ")");
    assert.deepEqual(control.filter((r) => underScreen(r.chain)).map(renderRule), [
      "@media screen { .fileview-md :hover + .fv-figopen, .fileview-md .fv-figopen:hover, .fileview-md .fv-figopen:focus-visible { opacity: 1; } }",
      "@media screen and (hover: none) { .fileview-md .fv-figopen { opacity: 0.8; } }",
    ], name + ": the rules under a screen-only at-rule are the reveal and the no-hover rule");
  }
});

test("the reader the closed set stands on reads rules, not lines: the three shapes the line-keyed set missed or read are in the population alike, an indented reveal under an at-rule other than screen, a grouped selector wrapped across lines and a column-zero rule, each read as a rule outside screen; a rule indented inside a multi-line @media screen block is under screen as a one-line one is; a brace in a comment is no rule (the file review's round 10, correctness-1 with tests-1 and ui-1)", () => {
  const sheet = [
    "/* a comment naming .fv-figopen { */",
    ".fileview-md .fv-figopen { opacity: 0; }",
    "@media (min-width: 1px) {",
    "  .fileview-md .fv-figopen { opacity: 1; }   /* indented under an at-rule a print matches too */",
    "}",
    ".fileview-md .fv-figerr,",
    ".fileview-md .fv-figopen { opacity: 1; }",
    "@media screen {",
    "  .fileview-md .fv-figopen:focus-visible { opacity: 1; }",
    "}",
    "@media screen and (hover: none) { .fileview-md .fv-figopen { opacity: 0.8; } }",
  ].join("\n");
  const control = cssRules(sheet).filter((r) => /fv-figopen/.test(r.selector));
  assert.deepEqual(control.filter((r) => !underScreen(r.chain)).map(renderRule), [
    ".fileview-md .fv-figopen { opacity: 0; }",
    "@media (min-width: 1px) { .fileview-md .fv-figopen { opacity: 1; } }",
    ".fileview-md .fv-figerr, .fileview-md .fv-figopen { opacity: 1; }",
  ], "the column-zero rule, the indented reveal under (min-width: 1px) and the grouped selector's continuation-line reveal are rules outside screen; the comment's brace is none");
  assert.deepEqual(control.filter((r) => underScreen(r.chain)).map(renderRule), [
    "@media screen { .fileview-md .fv-figopen:focus-visible { opacity: 1; } }",
    "@media screen and (hover: none) { .fileview-md .fv-figopen { opacity: 0.8; } }",
  ], "the indented rule inside the multi-line screen block and the one-line screen rule are under screen");
});

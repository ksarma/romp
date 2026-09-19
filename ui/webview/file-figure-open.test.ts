// A figure opens in detail (plans/markdown-viewer.md, "Follow-on: Link navigation", L3): the source pins beside the browser
// leg (file-figure-open-browser.test.ts, which lays the control out and clicks it in Chromium). What is pinned here is the shape
// the browser leg cannot read off a page: the control's one path into the DOM (ensureFigureControl: after figureAnchor's climb,
// never a wrapper, found by its mark, skipped inside a gate's placeholder), what it opens (figureTarget: the model's figurePath
// for a file of the session, a tab for an http source, nothing for a `data:` one), where it is added (mdBlock's file arm after
// the anchors; the body's `load` capture listener for a figure loaded later), how a click on it or on a bare figure is routed
// (a listener of its own beside the links', with the guards for a link, a panel mark, the open panel and a drag-select), the
// label lookup that steps past it, the two text walks that skip it, the glyph, and the sheets' rules under `screen`. Every pin
// reads the tree's own source, so a rename here fails loudly. Synthetic values only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

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

test("the control: one builder (ensureFigureControl) puts a button of the bar's glyph dress after figureAnchor's climb, marked, titled Open the picture, never inside a gate's placeholder, never twice, and only for a figure with something to open", () => {
  const fn = between(VIEW, "function ensureFigureControl(img: Element, filePath: string): void {", "function addFigureControls(");
  assert.match(fn, /if \(img\.closest\('\[data-act="' \+ GATE_ACT \+ '"\]'\)\) return;/, "a gated figure waits for its load");
  assert.match(fn, /const anchor = figureAnchor\(img\);\n\s*if \(figureControlAfter\(anchor\)\) return;\n\s*if \(figureTarget\(img, filePath\) === null\) return;/, "one control per figure, and none for a figure with nothing to open");
  assert.match(fn, /el\("button", "fileview-btn fileview-icon " \+ FIGOPEN_CLASS\)/, "the bar's glyph dress and the control's own class");
  assert.match(fn, /b\.type = "button"; b\.innerHTML = ICON_EXPAND; b\.dataset\.icon = "1";/, "the icon family's drawing");
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

test("where it is added: mdBlock's file arm after the anchors are sorted; a figure loaded after the paint through one capture-phase load listener on the body, armed per open and dropped with the viewer; a URL document adds none", () => {
  const md = between(VIEW, "function mdBlock(text: string, doc?: MdDocLoc): HTMLElement {", "\n}\n");
  const fileArm = between(md, 'if (doc && doc.kind === "file") {', "} else {");
  assert.ok(fileArm.indexOf("linkMarkdownAnchors(box, doc.path);") < fileArm.indexOf("addFigureControls(box, doc.path);"), "after the anchors: a link holding the figure is sorted before the control goes in after it");
  assert.equal((md.match(/addFigureControls\(/g) || []).length, 1, "the file arm alone: a URL document's figures get no control");
  const arm = between(VIEW, "function armFigureControls(body: HTMLElement, filePath: string): () => void {", "\n}\n");
  assert.match(arm, /const img = figureOf\(e\); if \(img\) ensureFigureControl\(img, filePath\);/, "figureOf's rule: an img of the box outside a placeholder");
  assert.match(arm, /body\.addEventListener\("load", onLoad, true\);/, "capture: an img's load does not bubble");
  assert.match(arm, /return \(\) => \{ body\.removeEventListener\("load", onLoad, true\); \};/);
  assert.equal((arm.match(/addEventListener\(/g) || []).length, 1, "one listener, nothing per paint or per img");
  assert.match(VIEW, /ctx\.onClose\(armFigureLabels\(body\)\);\n(?:\s*\/\/[^\n]*\n)*\s*ctx\.onClose\(armFigureControls\(body, path\)\);/, "armed beside the labels' listeners, dropped through the same close hooks");
  // the label lookup steps past the control, and the label is inserted where it reads it back
  assert.match(VIEW, /const n = \(figureControlAfter\(anchor\) \|\| anchor\)\.nextSibling;/, "figureLabelAfter reads past the control");
  assert.match(VIEW, /parent\.insertBefore\(label, \(figureControlAfter\(anchor\) \|\| anchor\)\.nextSibling\);/, "the label goes after the control");
});

test("the click: a listener of its own on the body beside the links'; the control's click is the figure's own; a bare figure's click yields to a link, a panel mark, the open panel and a drag-select; a remote picture is a tab, a modified click the /file URL in a tab (stopped before the row), a plain one the viewer through openFromViewer with no target", () => {
  const listeners = VIEW.split('body.addEventListener("click", (ev) => {');
  assert.equal(listeners.length, 3, "two click listeners on the viewer's body: the links' and the figures'");
  const fig = listeners[2].split("\n  });\n")[0];
  assert.match(fig, /const control = figureControlOf\(t, body\);\n\s*if \(control\) \{ const img = figureOfControl\(control\); if \(img\) openFigure\(img, ev\); return; \}/, "the control first, wherever it stands");
  assert.match(fig, /const img = bareFigureOf\(t, body\);\n\s*if \(!img \|\| linkOf\(t\)\) return;/, "a figure inside a link: the author's link (the links listener)");
  assert.match(fig, /if \(panelMark\(t\) && !wantsOwnTab\(ev\)\) return;\n\s*if \(asideOpen && !wantsOwnTab\(ev\)\) return;\n\s*if \(selectionOpenIn\(box\)\) return;\n\s*openFigure\(img, ev\);/, "the mark's card, the open panel's offer and drag, a drag-select: each keeps the plain click");
  const open = between(VIEW, "const openFigure = (img: Element, ev: MouseEvent): void => {", "\n  };\n");
  assert.match(open, /const target = figureTarget\(img, path\);\n\s*if \(!target\) return;/);
  assert.match(open, /if \(wantsOwnTab\(ev\)\) ev\.stopPropagation\(\);/, "a modified click stops before the row's delegate, as a link's does");
  assert.match(open, /if \(target\.kind === "web"\) \{ openUrlTab\(target\.href\); return; \}/, "a remote picture: a tab, never the viewer");
  assert.match(open, /if \(wantsOwnTab\(ev\) && openFileTab\(target\.path, sid \|\| null\)\) return;/, "the /file URL in a tab; a blocked popup falls through");
  assert.match(open, /openFromViewer\("push", target\.path, sid \|\| null, null\);/, "the viewer, with no target: the trail's push");
  assert.doesNotMatch(fig + open, /ev\.stopPropagation\(\)(?!;\s*\/\/ a modified)/, "a plain click is never stopped");
  // the links' listener is as it was: its pins in file-view-links.test.ts read the first listener's text
  const links = listeners[1].split("\n  });\n")[0];
  assert.match(links, /const x = linkOf\(t\);\n\s*if \(!x\) return;/);
  assert.doesNotMatch(links, /figure/, "the links' listener knows nothing of figures");
});

test("the two text walks skip the control as they skip the failed figure's label, and the Rendered pairing leaves it out of the top-level nodes beside an html-block figure", () => {
  const classes = between(ANCHOR, "const CONTROL_CLASSES = [", "];");
  assert.match(classes, /"fv-figerr",[^\n]*\n\s*"fv-figopen",/, "anchor-map.ts: after the label, the last entry");
  assert.match(ANCHOR, /const isFigureCompanion = \(n: DNode\): boolean => hasClass\(n, "fv-figerr"\) \|\| hasClass\(n, "fv-figopen"\);/, "the two companions of a figure");
  assert.match(ANCHOR, /const holdsContent = \(n: DNode\): boolean => isElement\(n\) \? !blankMark\(n\) && !isFigureCompanion\(n\) : isText\(n\) && stripWs\(n\.data\) !== "";/, "left out of the top-level nodes, as the label is");
  assert.doesNotMatch(ANCHOR, /isFigureLabel/, "the label-only predicate is gone: one predicate for both");
  assert.match(READER, /const CONTROL_CLASSES = \["code-copy", "katex", "md-fnback", "md-frontmatter-head", "fv-gate", "fv-figerr", "fv-figopen"\];/, "reader-place.ts: the seventh control");
  assert.match(READER, /These seven are in anchor-map\.ts's CONTROL_CLASSES/, "the count in the comment follows the list");
});

test("the sheets: the control rests transparent over the figure's corner with a zero-width margin box, positioned above the layer's overlay; every reveal (the pointer over the figure or the control, a keyboard focus, a device with no hover) is under screen, so print shows none of it and the print block carries no line for it", () => {
  for (const [name, css] of SHEETS) {
    assert.match(css, /\n\.fileview-md \.fv-figopen \{ position: relative; z-index: 1; vertical-align: top; margin: 0 6px 0 -28px; top: 6px; padding: 3px; background: var\(--bg\); opacity: 0; \}\n/, name + ": the rest");
    assert.match(css, /\n\.fileview-md \.fv-figopen-left \{ float: left; \}\n\.fileview-md \.fv-figopen-right \{ float: right; margin: 0 -28px 0 6px; \}\n/, name + ": the float twins");
    assert.match(css, /\n@media screen \{ \.fileview-md :hover \+ \.fv-figopen, \.fileview-md \.fv-figopen:hover, \.fileview-md \.fv-figopen:focus-visible \{ opacity: 1; \} \}\n/, name + ": the reveal, screen only");
    assert.match(css, /\n@media screen and \(hover: none\) \{ \.fileview-md \.fv-figopen \{ opacity: 0\.8; \} \}/, name + ": no hover keeps it visible, screen only");
    const print = css.slice(css.indexOf("\n@media print {"), css.indexOf("\n}", css.indexOf("\n@media print {")));
    assert.doesNotMatch(print, /fv-figopen/, name + ": the print block names it nowhere");
    // one rest rule, revealed by nothing outside screen
    const heads = css.split("\n").filter((l) => /fv-figopen/.test(l) && /\{/.test(l) && !l.startsWith("   ") && !l.startsWith("/*"));
    for (const h of heads) if (/opacity: (1|0\.8)/.test(h)) assert.match(h, /^@media screen/, name + ": a reveal outside screen: " + h);
  }
});

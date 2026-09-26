// A figure opens in detail (plans/markdown-viewer.md, "Follow-on: Link navigation", L3): the source pins beside the browser
// leg (file-figure-open-browser.test.ts, which lays the control out and clicks it in Chromium). What is pinned here is the shape
// the browser leg cannot read off a page: the control's one path into the DOM (decideFigureControl: after figureAnchor's climb,
// never a wrapper, found by its mark, skipped inside a gate's placeholder), what it opens (figureTarget: the model's figurePath
// for a file of the session, a tab for an http source, nothing for a `data:` one), where it is decided (mdBlock's file arm after
// the anchors; the body's `load` and `error` capture pair for a figure the browser answers for later), how a click on it or on a bare figure is routed
// (a listener of its own beside the links', with the guards for a link, a panel mark, the open panel and a drag-select), the
// label lookup that steps past it, the two text walks that skip it, the glyph, and the sheets' rules under `screen`, read as rules through ui/webview/css-rules.mjs in every sheet a page of either host loads (ui/webview/host-sheets.mjs derives that set from the page assembly). Every pin
// reads the tree's own source, so a rename here fails loudly. Synthetic values only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { cssRules, renderRule, underScreen } from "./css-rules.mjs";
import { hostSheets } from "./host-sheets.mjs";
import { codeOnly } from "../test-code-only";   // the comment stripper the count pin and the Mouse-call census read through (the compiler's ranges; file-view-seam.test.ts self-checks it)
import * as ts from "typescript";   // the Mouse-call census's compiler walk (mouseCalls; the test build keeps typescript a runtime require, esbuild.js testBuild)

const ROOT = path.resolve(process.cwd(), "..");
const web = (f: string) => fs.readFileSync(path.join(ROOT, "ui", "webview", f), "utf8");
const VIEW = web("file-view.ts");
const ICONS = web("icons.ts");
const ANCHOR = web("anchor-map.ts");
const READER = web("reader-place.ts");
/** Every sheet a page of either host loads, derived from the page assembly (ui/webview/host-sheets.mjs: the kernel's page
 *  functions' linked bundles, live-read sheets and inlined constants, the style blocks the helpers they call write into their
 *  HTML at serve time, and the extension's webview links), and the two among them the
 *  viewer's dress is written in, byte-mirrored, the chat's and the feed's: the closed set's full expected value holds in each of
 *  those two, and every other sheet holds no rule naming the control (the file review's round 10, correctness-1 with
 *  regression-5: the set had been closed over the pair while the Files page loads files-pane.css after styles.css, so a reveal
 *  written there stood outside it with every pin green, and a listing of ui/webview would not have read the sheets the kernel
 *  inlines from its own source). */
const SHEETS = hostSheets(ROOT);
const DRESSING = ["ui/webview/styles.css", "ui/webview/feed.css"];
/** The text from one anchor to the next, both present. */
const between = (src: string, from: string, to: string): string => {
  const a = src.indexOf(from); assert.ok(a >= 0, from + " present");
  const b = src.indexOf(to, a); assert.ok(b > a, to + " present after " + from);
  return src.slice(a, b);
};

test("the control: one decision (decideFigureControl) puts a button of the bar's glyph dress after figureAnchor's climb, marked, titled Open the picture for a file of the session and, for a picture from the web, naming its host and the new tab with the web class and the outbound glyph (dressFigureControl, keyed on figureTarget's kind at every decision, a standing control's included), never inside a gate's placeholder, never twice, and only for a figure with something to open (figureWantsControl); sentence pins on the source's spelling, whose property file-figure-open-browser.test.ts executes in its outbound case", () => {
  const fn = between(VIEW, "function decideFigureControl(img: Element, filePath: string): void {", "function addFigureControls(");
  const want = between(VIEW, "function figureWantsControl(img: Element, anchor: Element, filePath: string): boolean {", "function decideFigureControl(");
  assert.match(want, /if \(img\.closest\('\[data-act="' \+ GATE_ACT \+ '"\]'\)\) return false;/, "a gated figure waits for its load");
  assert.match(want, /if \(figureTarget\(img, filePath\) === null\) return false;/, "none for a figure with nothing to open");
  assert.match(fn, /const anchor = figureAnchor\(img\);\n\s*const standing = figureControlAfter\(anchor\);\n\s*const want = figureWantsControl\(img, anchor, filePath\);\n\s*const target = figureTarget\(img, filePath\);[^\n]*\n\s*dressFigureTitle\(img, target\);\n\s*dressFigureMark\(img, want\);\n\s*if \(standing\) \{ if \(!want\) removeFigureControl\(standing\); else dressFigureControl\(standing, target\); return; \}\n\s*if \(!want\) return;/, "one control per figure: the verdict against the one standing, added when missing and wanted, removed when standing and unwanted (the removal hands the keyboard on first, removeFigureControl), and a standing wanted one RE-DRESSED from the target read at this decision (the file review's round 11, ui-1 with extra8-1: a <picture> re-selecting between a local and a remote candidate flips the kind with no add or remove); the picture's own title decided before the control's verdict, so a remote picture under the floor carries its address too, and the picture's own mark right after it, from the verdict, for the picture no control stands on (the file review's round 12, fresh-1 with tests-2; the executed read of both is file-figure-open-browser.test.ts's under-the-floor case; a sentence pin)");
  assert.match(fn, /el\("button", "fileview-btn fileview-icon " \+ FIGOPEN_CLASS\)/, "the bar's glyph dress and the control's own class");
  assert.match(fn, /b\.type = "button"; b\.dataset\.icon = "1";\n\s*b\.setAttribute\(FIGOPEN_MARK, ""\);\n\s*dressFigureControl\(b, target\);/, "the dress (words, class, glyph) applied by the one function that re-applies it to a standing control");
  const dressFn = between(VIEW, "function dressFigureControl(b: HTMLElement, target: FigureTarget | null): void {", "/** The picture's own title");
  assert.match(dressFn, /const glyph = figureControlGlyph\(web\); if \(drawn\) drawn\.remove\(\); if \(glyph\) b\.appendChild\(glyph\);/, "the icon family's drawing for the kind, cloned into the control and swapped when the kind it was drawn for differs (never an innerHTML write on the control: it stands under the Rendered box during the render, and file-view-figures-gate-adopt.test.ts records a live re-parse there as a red; the author's closing pass after the file review's round 5, records-1)");
  assert.match(dressFn, /if \(!drawn \|\| b\.classList\.contains\(FIGOPEN_WEB_CLASS\) !== web\)/, "the web class on the control is the record of the kind its glyph was drawn for");
  assert.match(dressFn, /b\.classList\.toggle\(FIGOPEN_WEB_CLASS, web\);/, "the class the sheets dress, keyed on the kind");
  const glyphFn = between(VIEW, "function figureControlGlyph(web = false): Node | null {", "/**");
  assert.match(glyphFn, /const holder = el\("span"\); holder\.innerHTML = ICON_EXPAND \+ ICON_OUTBOUND; figureGlyph = holder\.firstElementChild \?\? null; figureWebGlyph = figureGlyph \? figureGlyph\.nextElementSibling : null;/, "the two drawings parsed once, in one write, onto a holder that enters no document, and read through firstElementChild and nextElementSibling, never children[], which a stand-in document answers with an element that has no cloneNode (file-view-seam.test.ts holds the file's re-parse count; a sentence pin)");
  assert.match(glyphFn, /return drawing \? drawing\.cloneNode\(true\) : null;/, "and cloned per control");
  assert.doesNotMatch(fn.slice(0, fn.indexOf("/** The control's glyph")), /innerHTML|outerHTML|insertAdjacentHTML/, "no markup write in the decision itself");
  assert.match(fn, /b\.setAttribute\(FIGOPEN_MARK, ""\);/, "the mark it is found by");
  assert.match(dressFn, /const words = target !== null && target\.kind === "web" \? \(figureSourceCredentialed\(target\.src\) \? FIGURE_OPEN_WEB_WITHHELD : figureOpenWebTitle\(targetHost\(target\.href\)\)\) : FIGURE_OPEN_TITLE;\n\s*if \(b\.title !== words\) \{ b\.title = words; b\.setAttribute\("aria-label", words\); \}/, "the words in the title and the aria-label, keyed on the target's kind: for a picture from the web the new tab and the host, or the new tab and the withheld address when the source the target carries appears to carry a sign-in (the one rule, figureSourceCredentialed, read before targetHost's parse, which can name a sign-in part as a host and a port; the file review's round 15, tests-1 with extra9-3; at that rule's stated cost, a harmless address with an at sign after its scheme (https://cdn/img/a@2x.png) withheld too); the one word set for a file (a sentence pin on the spelling: the property is held by file-view-outline.test.ts's sign-in table, which reads the control's title property and aria-label over the paint)");
  assert.match(VIEW, /\nexport function figureOpenWebTitle\(host: string\): string \{ return "Open the picture in a new tab at " \+ host; \}\n/, "the web words name the host and the new tab");
  assert.match(VIEW, /\nexport const FIGURE_ADDRESS_WITHHELD = "address withheld because it appears to carry a sign-in";\n/, "the words in a withheld address's place, one phrase every surface frames in its own words (a sentence pin on the spelling)");
  assert.match(VIEW, /\nexport const FIGURE_OPEN_WEB_WITHHELD = "Open the picture in a new tab \(" \+ FIGURE_ADDRESS_WITHHELD \+ "\)";\n/, "the control's own frame around it: the open and the new tab, and no host (a sentence pin on the spelling)");
  assert.match(VIEW, /\nfunction targetHost\(href: string\): string \{\n\s*try \{ return new URL\(href\)\.host; \} catch \{ return authorityCut\(href\); \}\n\}\n/, "the host the parse names, with its port, and a refused address cut at its authority: it prints the parse, which reads some sign-in spellings as a host and a port, so the words line reads the sign-in rule first (a sentence pin on the spelling: the property is held by file-view-outline.test.ts's sign-in table and its refused rows)");
  assert.match(VIEW, /\nconst FIGOPEN_WEB_CLASS = FIGOPEN_CLASS \+ "-web";\n/);
  // the picture's own title for the two gestures with no control: the address on its own line after the author's title, kept under a mark and restored
  const titleFn = between(VIEW, "function dressFigureTitle(img: Element, target: FigureTarget | null): void {", "/** The control's glyph");
  assert.match(titleFn, /const web = target !== null && target\.kind === "web" && figureLinkOf\(img\) === null && figureFoldOf\(img\) === null;/, "a web target whose click is the figure's own, by the TWO predicates the click listener yields on (figureLinkOf from the img over FIGURE_LINK_SET, and figureFoldOf, a summary that toggles a fold), so the line stands wherever the plain click opens the tab, inside a dead link or a named anchor too, and is withheld inside a link whose click another gesture owns (the file review's round 12, correctness-1 with ui-1: read as any anchor, the line was withheld where the click still opened) and inside a fold's own summary, whose click the fold takes (the file review's round 14, fresh-1: the line stood there while the click toggled the fold; a sentence pin, whose property file-figure-open-browser.test.ts's fold cases execute)");
  // the one predicate of a link's owning a figure's click, exported, and its closed set: an anchor with an href, the links listener's URL and section links, a path link
  assert.match(VIEW, /\nexport const FIGURE_LINK_SET = 'a\[href\], a\.' \+ URL_LINK_CLASS \+ ', a\.' \+ FRAG_LINK_CLASS \+ ', \[data-act="openpath"\]';\n/, "the link set, one selector, built from the link classes the links listener reads (a sentence pin: the set's spelling)");
  assert.match(VIEW, /\nexport function figureLinkOf\(from: Element\): Element \| null \{\n  return from\.closest\(FIGURE_LINK_SET\);\n\}\n/, "closest over the set from the element given: the img for the click and the title, the parent of figureAnchor's climb for the control (a sentence pin)");
  assert.equal((VIEW.match(/closest\('a, \[data-act="openpath"\]'\)/g) || []).length, 0, "no reader keeps a set of its own: the any-anchor selector is gone from the file (a property pin: its count is zero)");
  assert.equal((VIEW.match(/closest\("a\[href\]"\)/g) || []).length, 0, "and so is the click listener's private a[href] read (a property pin: its count is zero)");
  assert.equal((codeOnly(VIEW).match(/figureLinkOf\(/g) || []).length, 4, "the predicate's definition and its three readers, the click listener, dressFigureTitle and linkAbove, read the one predicate (a property pin: the count of its calls over the CODE alone, comments stripped by ui/test-code-only.ts, so a comment naming the call neither satisfies nor reds it; red when a reader spells a set of its own, re-derived when a reader joins; the file review's round 13, extra7-1: over the raw text the count stood at four with a reader replaced by a private closest() beside a comment naming the call)");
  // the other owner of a figure's click: a summary that toggles a fold, a sibling of the set and not a member (the file review's round 14, fresh-1)
  assert.match(VIEW, /\nexport function figureFoldOf\(from: Element\): Element \| null \{\n  const box = from\.closest\("\.fileview-md"\);\n  const s = from\.closest\("summary"\);\n  if \(!box \|\| !s \|\| !box\.contains\(s\)\) return null;\n  const d = s\.parentElement;\n  if \(!d \|\| d\.localName !== "details"\) return null;\n  for \(let c = d\.firstElementChild; c; c = c\.nextElementSibling\) if \(c\.localName === "summary"\) return c === s \? s : null;\n  return null;\n\}\n/, "the summary that toggles a fold: closest('summary') bounded to the Rendered box, a details element's own first summary child, else null, so a stray summary outside a details and a later summary of one are none (a sentence pin on the predicate's spelling; the fold cases in file-figure-open-browser.test.ts execute it, the stray summary among their controls)");
  const setLine = /\nexport const FIGURE_LINK_SET = [^\n]*/.exec(VIEW);
  assert.ok(setLine, "FIGURE_LINK_SET's line found");
  assert.doesNotMatch(setLine![0], /summary/, "the summary is not a member of FIGURE_LINK_SET (a property pin over the set's line)");
  const linkAboveFn = between(VIEW, "function linkAbove(anchor: Element): Element | null {", "\n}\n");
  assert.doesNotMatch(codeOnly(linkAboveFn), /figureFoldOf|summary/, "linkAbove reads no summary, so a picture inside a fold's summary keeps its control, whose click opens it and toggles nothing (a property pin over linkAbove's code)");
  assert.equal((codeOnly(VIEW).match(/figureFoldOf\(/g) || []).length, 4, "the fold predicate's definition and its three readers, the click listener, dressFigureTitle and dressFigureMark (a property pin: the count of its calls over the CODE alone, re-derived when a reader joins; linkAbove is not one)");
  assert.match(titleFn, /const t = target as \{ href: string; src: string \};\n\s*const title = \(author \? author \+ "\\n" : ""\) \+ figureWebTitleLine\(figureSourceCredentialed\(t\.src\) \? FIGURE_ADDRESS_WITHHELD : shownAddress\(t\.href\)\);/, "the author's title first, the address line after it on its own line: the withheld address when the source the target carries appears to carry a sign-in, else the resolved address's origin (a sentence pin on the spelling: the property is held by file-view-outline.test.ts's sign-in table over the paint)");
  assert.match(titleFn, /if \(held === null\) img\.setAttribute\(FIGTITLE_MARK, author\);/, "the author's title kept under the mark while the line stands");
  assert.match(titleFn, /\} else if \(held !== null\) \{\n\s*if \(held\) img\.setAttribute\("title", held\); else img\.removeAttribute\("title"\);\n\s*img\.removeAttribute\(FIGTITLE_MARK\);/, "restored, and the mark taken off, when the candidate is local again");
  assert.match(VIEW, /\nexport function figureWebTitleLine\(address: string\): string \{ return "Opens in a new tab: " \+ address; \}\n/);
  assert.match(VIEW, /\nconst FIGTITLE_MARK = "data-fv-figtitle";\n/);
  // the picture's own outbound mark for a web picture with no control (the file review's round 12, fresh-1): the title's population less
  // the pictures a control stands on; the executed read is the browser leg's under-the-floor case (on hover, and at rest under touch emulation)
  assert.match(VIEW, /\nconst FIGWEB_MARK = "data-fv-figweb";\n/, "the mark's attribute (a sentence pin)");
  const markFn = between(VIEW, "function dressFigureMark(img: Element, want: boolean): void {", "\n}\n");
  assert.match(markFn, /if \(!want && img\.hasAttribute\(FIGTITLE_MARK\) && figureFoldOf\(img\) === null\) img\.setAttribute\(FIGWEB_MARK, ""\);\n\s*else img\.removeAttribute\(FIGWEB_MARK\);/, "the mark on the picture whose title carries the line, on which no control stands and which no fold's own summary holds (figureFoldOf, the file review's round 14, fresh-1, as ruled: the title's read already withholds FIGTITLE_MARK inside such a summary, so this read has no red of its own on the page and holds the mark's population in its own words, and the fold case's mark cell reds only when both reads go); taken off otherwise (a sentence pin; the removal is executed in file-view-figure-floor-browser.test.ts's narrow-and-widen case, a relayed remote twin of the 761 by 76 figure marked under the floor and bare again beside its returned control at the wide width, read under touch emulation; the target-turns-local road, a <picture> re-selecting from a remote to a local candidate, stays under this pin alone: file-figure-open-browser.test.ts's <picture> has a 300 by 200 remote candidate that never wears the mark)");
  assert.match(fn, /parent\.insertBefore\(b, anchor\.nextSibling\);/, "the anchor's next sibling: a sibling, never a wrapper");
  assert.doesNotMatch(fn, /tabIndex|tabindex/, "a button is in the tab order as it is: nothing takes it out");
  assert.match(VIEW, /\nconst FIGOPEN_MARK = "data-fv-figopen";\n/); assert.match(VIEW, /\nconst FIGOPEN_CLASS = "fv-figopen";\n/);
  assert.match(VIEW, /\nexport const FIGURE_OPEN_TITLE = "Open the picture";\n/);
  assert.match(ICONS, /^export const ICON_EXPAND = svg\(/m, "the glyph in icons.ts");
  assert.match(ICONS, /^export const ICON_OUTBOUND = svg\('<path /m, "the outbound glyph in icons.ts, the bar's family: a box with an arrow leaving it");
  assert.match(VIEW, /import \{ [^}]*ICON_EXPAND, ICON_OUTBOUND \} from "\.\/icons";/, "both imported beside the bar's glyphs");
  // found by the mark alone: the sanitizer keeps an author's class and never a data-* attribute
  const after = between(VIEW, "function figureControlAfter(anchor: Element): HTMLElement | null {", "/**");
  assert.match(after, /hasAttribute\(FIGOPEN_MARK\)/); assert.doesNotMatch(after, /FIGOPEN_CLASS|classList/);
});

test("what it opens (figureTarget): the model's figurePath for a source on the session's disk, a tab's address for an http or protocol-relative source, null otherwise; rewriteFigureSrcs keeps its own join, which the model test pins as the same", () => {
  assert.match(VIEW, /import \{ headVerdict, mtimeMoved, ABSENT, figurePath \} from "\.\/file-comments-model";/, "the model's join, not a fourth copy");
  const fn = between(VIEW, "function figureTarget(img: Element, filePath: string): FigureTarget | null {", "/** The control a click landed on");
  assert.match(fn, /const dest = chosenSource\(img\);/, "the candidate the browser chose, as the author wrote it (chosenSource: currentSrc mapped to the authored candidate; the src by pictureDest's rule when the browser chose it or has not picked)");
  assert.match(fn, /const p = figurePath\(filePath, dest\);\n\s*if \(p !== null\) return \{ kind: "file", path: p \};/);
  assert.match(fn, /if \(\/\^https\?:\/i\.test\(dest\) \|\| dest\.startsWith\("\/\/"\)\) return \{ kind: "web", href: absUrl\(dest\), src: dest \};/, "an http source: a tab, resolved as the browser resolved the fetch, with the source as the author wrote it beside it, which the words read for the sign-in rule");
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
  assert.match(fig, /const img = bareFigureOf\(t, body\);\n\s*if \(!img \|\| figureLinkOf\(img\)\) return;/, "a figure inside a link whose click is the link's: the one predicate (figureLinkOf over FIGURE_LINK_SET: the links listener's three, and an anchor with an href it leaves to the browser); a dead link and a named anchor are not in the set, and the click stays the figure's (a sentence pin)");
  assert.match(fig, /if \(!img \|\| figureLinkOf\(img\)\) return;[^\n]*\n\s*if \(figureFoldOf\(img\)\) return;[^\n]*\n\s*if \(panelMark\(t\) && !wantsOwnTab\(ev\)\) return;/, "a figure inside a fold's own summary: the fold takes the click, plain or modified, right after a link's yield and before the modifier-keyed yields (the file review's round 14, fresh-1; a sentence pin, whose property file-figure-open-browser.test.ts's fold cases execute)");
  assert.match(fig, /if \(panelMark\(t\) && !wantsOwnTab\(ev\)\) return;\n\s*if \(asideOpen && !wantsOwnTab\(ev\)\) return;\n\s*if \(selectionOpenIn\(box\)\) return;\n\s*openFigure\(img, ev\);/, "the mark's card, the open panel's offer and drag, a drag-select: each keeps the plain click");
  const open = between(VIEW, "const openFigure = (img: Element, ev: MouseEvent): void => {", "\n  };\n");
  assert.match(open, /const target = figureTarget\(img, path\);\n\s*if \(!target\) return;/);
  assert.match(open, /if \(wantsOwnTab\(ev\)\) ev\.stopPropagation\(\);/, "a modified click stops before the row's delegate, as a link's does");
  assert.match(open, /if \(target\.kind === "web"\) \{ if \(webGestureShown\(img, ev\)\) openUrlTab\(target\.href\); return; \}/, "a remote picture: a tab, never the viewer, and only through the one gate (the file review's round 16, extra5-1; a sentence pin, whose property file-view-outline.test.ts's gate guards and file-figure-open-browser.test.ts's gate cells execute)");
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
  // the partition's two addends, derived as the sum is (the file review's round 9, regression-2: "the other five" and "The last
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

/** The bounds of the closed set over the control's sheet rules, stated in its assertion messages: the selector bound (the author's
 *  closing pass after the file review's round 10, mechanism-2) and the sheet bounds beside it (the file review's round 10,
 *  regression-5; restated to name only what is truly outside the read since the fixes for the file review's round 11, extra7-1
 *  with tests-1, kernel-1 and extra6-1: the pane spinner's block, served with its pages, had been excused as one added after
 *  serving). */
const BOUND = " (the population is the rules whose selector names the control's class in every sheet a page of either host loads, derived from the page assembly by ui/webview/host-sheets.mjs, the pages' linked bundles, live-read sheets, inlined constants and the style blocks the helpers they call write into their HTML at serve time, and the extension's webview links; outside what this set closes, bounds stated here and in the plan's L3, not read: a rule whose selector would match the control's element without naming the class, katex's vendored sheet that styles.css and feed.css import, the rules a template writes into its own page (the settings page's transparent background, the too-large notice's body rule, the extension's zoom rule), and the style element a script creates after the page is served (palette.ts's and shortcuts-modal.ts's elements, the timeline view's own, the shim's notices' cssText)";

test("the sheets: the control rests transparent over the figure's corner with a zero-width margin box, positioned above the layer's overlay; every rule naming the control's class that reveals it (the pointer over the figure or the control, a keyboard focus, a device with no hover) is under screen, so print shows none of it and the print block carries no line for it; the population the set closes is the rules whose selector names the class in every sheet a page of either host loads, the chat's and the feed's carrying the dress and every other sheet none, the sheets derived and the bounds stated, not read; the picture's own mark for a web picture with no control is a second set, derived by its attribute over the same sheets, under screen alone and in the outbound dress's own token, the one the control's dashed border wears at rest; both at-rest rules under (hover: none) or (any-pointer: coarse), screen on both queries", () => {
  for (const d of DRESSING) assert.ok(SHEETS.some((s) => s.name === d), d + " is a sheet a page loads: the viewer's dress is written there (a renamed or unlinked sheet fails here, never silently)");
  assert.ok(SHEETS.some((s) => s.name.startsWith("kernel/kernel.py ")), "the population is wider than a listing of ui/webview: the sheets the kernel inlines from its own source (THEME_CSS, into every page that takes no arguments, and the pane spinner's block, _pane_spin's with _LOADER_CSS, into the four pages that call it) are in it, so a rule written there is read; a derivation reading the directory alone passes this set with a reveal there (the file review's round 10, regression-5)");
  assert.ok(SHEETS.some((s) => s.name === "kernel/kernel.py _pane_spin"), "the pane spinner's block is a sheet of the population: the style block the helper _pane_spin writes into the served HTML of the pages that call it (the chat, the feed, the sessions pane and the waiting pane), _LOADER_CSS folded in served order (the file review's round 11, extra6-1 with extra7-1, kernel-1 and tests-1: the block had stood outside the read with every pin green, excused by a bound sentence that called it one added after serving; a property pin over the derivation)");
  assert.equal(SHEETS.length, 11, "eleven sheets: the .css files under ui/webview, the two constants the kernel inlines from its own source and the pane spinner's block, the eleventh (a property pin over the derivation's count: a twelfth or a tenth is a change to the page assembly to be read here, and a separate entry for _LOADER_CSS would count the same served text twice)");
  for (const { name, css, loadedBy } of SHEETS) {
    if (!DRESSING.includes(name)) {
      // the sheet dimension of the closed set (the file review's round 10, correctness-1 with regression-5): every sheet a page loads
      // that is not one of the two the dress is written in holds no rule naming the control, the Files page's own sheet among them,
      // read live into that page after styles.css so a rule there wins on order and applies in print
      assert.deepEqual(cssRules(css).filter((r) => /fv-figopen/.test(r.selector)).map(renderRule), [], name + " (loaded by " + loadedBy.join(", ") + "): no rule naming the control, however the sheet writes it; the dress is written in the chat's and the feed's sheets alone, and a rule here would apply on the pages that load this sheet" + BOUND + ")");
      assert.deepEqual(cssRules(css).filter((r) => /data-fv-figweb/.test(r.selector)).map(renderRule), [], name + " (loaded by " + loadedBy.join(", ") + "): no rule naming the picture's own mark either, the same two sheets carrying it (the file review's round 12, fresh-1)");
      continue;
    }
    assert.match(css, /\n\.fileview-md \.fv-figopen \{ position: relative; z-index: 1; vertical-align: top; margin: 0; margin-inline: -28px 6px; top: 6px; padding: 3px; background: var\(--bg\); opacity: 0; \}\n/, name + ": the rest, its margins logical, -28px at the line's start and 6px at its end, so in a right-to-left block the control stands over the picture's top-left corner as it stands over the top-right in left-to-right text (the file review's round 15, ui-2: with the physical margins it stood 6px outside the picture's left edge there; a sentence pin on the rule's spelling, the closed set below holds the property, and the laid-out read is file-figure-open-browser.test.ts's right-to-left case)");
    assert.match(css, /\n\.fileview-md \.fv-figopen-left \{ float: left; margin: 0 6px 0 -28px; \}\n\.fileview-md \.fv-figopen-right \{ float: right; margin: 0 -28px 0 6px; \}\n/, name + ": the float twins, each with physical margins of its own, since an author's align is physical: a left float that took the rest's logical margins stood off its corner in a right-to-left block (the file review's round 15, ui-2; a sentence pin on the rules' spelling)");
    assert.match(css, /\n\.fileview-md \.fv-figopen-web \{ border-style: dashed; \}\n/, name + ": the web control's dress, the gate's dashed border for a figure from another host (the file review's round 11, ui-1 with extra8-1; a sentence pin on the rule's spelling, and the closed set below holds the property over the parsed rules)");
    assert.match(css, /\n@media screen \{ \.fileview-md :hover \+ \.fv-figopen, \.fileview-md \.fv-figopen:hover, \.fileview-md \.fv-figopen:focus-visible, \.fileview-md \.fv-figopen-web:focus \{ opacity: 1; \} \}\n/, name + ": the reveal, screen only, any focus on the web control among its members (the file review's round 14, ui-1 with extra9-1: after a mouse press the web control held a focus :focus-visible does not match, unpainted on a fine pointer; a sentence pin on the rule's spelling, the closed set below holds the property, and the painted read is file-figure-open-browser.test.ts's script-focus case)");
    assert.match(css, /\n@media screen and \(hover: none\), screen and \(any-pointer: coarse\) \{ \.fileview-md \.fv-figopen \{ opacity: 0\.8; \} \}/, name + ": no hover, or a coarse pointer beside a hovering one, keeps it visible, screen written on both queries (the file review's round 13, extra7-2: `hover` is the primary pointer's, and a touchscreen laptop's hovers; a sentence pin on the at-rule's spelling, the closed set below holds the property)");
    assert.match(css, /\n@media screen and \(hover: none\), screen and \(any-pointer: coarse\) \{ \.fileview-md \.fv-figopen-web \{ opacity: 1; \} \}/, name + ": the web control at rest at full opacity, after the 0.8 rule and of its specificity, so it wins: at 0.8 the picture under the control showed through its background and its dashed line, the dress it shares with the mark (the painted-contrast ask of 2026-09-23: at 0.8 the line read 2.46:1 on a VS Code editor ground of #404040 over the leg's picture, and fell under 3:1 from #282828 over the worst picture; a sentence pin, the painted read is file-figure-open-browser.test.ts's paintedRatio and the composed one theme-parity.test.ts's)");
    assert.match(css, /\n@media screen \{ \.fileview-md \.fv-figopen-web:focus-visible \{ outline-offset: 2px; \} \}/, name + ": the web control's focus ring 2px off its border, so its dashed line shows under a keyboard focus: drawn where the browser draws it, the ring covered the border row and the row inside it, and at 1px off the border row still (the painted-contrast ask of 2026-09-23; a sentence pin on the rule's spelling, the closed set below holds the property, and the painted read is file-figure-open-browser.test.ts's fine-pointer case)");
    assert.match(css, /\n@media screen \{ \.fileview-md \.fv-figopen-web:active \{ transform: none; \} \}/, name + ": the button family's press cue (a scale to 0.96) off on the web control alone: the release that opens the tab comes while it is held, so the pressed state is one a gesture opens the tab from, and under the cue its 1px dashed line spread over two pixel rows, its modal colour at 1.59:1 dark and 1.39:1 light against the control's own ground (the painted-contrast ask of 2026-09-23, the maintainer's ruling; a sentence pin on the rule's spelling, the closed set below holds the property, and the painted read is file-figure-open-browser.test.ts's pressedLegible in its three painted cases)");
    assert.match(css, /\n@media screen \{ \.fileview-md \.fv-figopen-web, \.fileview-md img\[data-fv-figweb\] \{ -webkit-tap-highlight-color: transparent; \} \}/, name + ": no browser tap highlight on the web control or the mark: in a finger's tap that opens the tab, while the control matches :active, a phone's default highlight (rgba(51, 181, 229, 0.4)) painted over the control and took its line to 2.578:1 dark and 2.531:1 light against its own ground; the mark takes no highlight today, since nothing from it up to the root shows a hand cursor, and wears the rule so a pointer cursor given it later brings none (the tap-highlight ruling of 2026-09-24; a sentence pin on the rule's spelling, the closed sets below hold the property, and the painted read is file-figure-open-browser.test.ts's tap cases, each frame of the tap on the phone, under CDP touch and on the touchscreen laptop)");
    assert.match(css, /\n@media screen \{ \.fileview-md a\.fv-dead:has\(\.fv-figopen-web\), \.fileview-md a\.fv-dead:has\(img\[data-fv-figweb\]\) \{ opacity: 1; color: color-mix\(in srgb, currentColor 70%, transparent\); \} \}/, name + ": a dead link holding the outbound dress (the web control after a captioned picture, or the mark) dims by colour, not by opacity, which dimmed the dress to 2.47:1 dark and 2.40:1 light for the control at rest over the leg's picture (with the control's own 0.8) and 2.82:1 light for the mark, while a tap, a click and Enter open the tab from inside it (a sentence pin on the rule's spelling; the closed sets below hold the property)");
    const print = css.slice(css.indexOf("\n@media print {"), css.indexOf("\n}", css.indexOf("\n@media print {")));
    assert.doesNotMatch(print, /fv-figopen/, name + ": the print block names it nowhere");
    // the picture's own outbound mark for a web picture with no control (the file review's round 12, fresh-1): a second closed set,
    // DERIVED from the parsed rules by the attribute the decision sets (data-fv-figweb, file-view.ts dressFigureMark), never a typed
    // count; its selector names the img's mark and not the control's class, so it stands outside the set below by that set's own bound
    // and is held here in full, and byte-equal across the two sheets by fileview-parity.test.ts's heads; the executed read is
    // file-figure-open-browser.test.ts's two under-the-floor cases (on hover on a fine pointer, and at rest under touch emulation
    // with no hover ever over the picture, a case of its own so the leg's red over the undressed picture reaches the at-rest read).
    // Since the file review's round 14 (correctness-2 with extra5-1 and extra5-2) both outline rules carry the ring of var(--bg)
    // under the outline, 3px, and a margin stands at rest under screen on every pointer, the set's first member, 3px up and down, the
    // ring's width, and 3px plus 0.3em across the line, measured per axis so the ring covers no neighbouring ink at the picture's own
    // text size, and where the picture is in smaller text than an italic or bold italic f glued before it, that f's ink only within
    // the bound the sheets' comment states (the two margin rulings of 2026-09-24); the executed reads are the leg's worst dash-to-ring
    // read (paintedRatio's mark branch), its neighbour pin (ringCoversNoNeighbour, which holds one such picture to that bound) and its
    // line pin (ringClearsTheLines)
    const mark = cssRules(css).filter((r) => /data-fv-figweb/.test(r.selector));
    assert.deepEqual(mark.filter((r) => !underScreen(r.chain)).map(renderRule), [], name + ": no rule naming the mark outside a screen-only at-rule: a print, where hover is none, would show the at-rest dress (a property pin over the derived population)");
    assert.deepEqual(mark.filter((r) => underScreen(r.chain)).map(renderRule), [
      "@media screen { .fileview-md .fv-figopen-web, .fileview-md img[data-fv-figweb] { -webkit-tap-highlight-color: transparent; } }",
      "@media screen { .fileview-md img[data-fv-figweb] { margin: 3px calc(3px + 0.3em); } }",
      "@media screen { .fileview-md img[data-fv-figweb]:hover { outline: 1px dashed var(--outbound-line); outline-offset: 1px; box-shadow: 0 0 0 3px var(--bg); } }",
      "@media screen and (hover: none), screen and (any-pointer: coarse) { .fileview-md img[data-fv-figweb] { outline: 1px dashed var(--outbound-line); outline-offset: 1px; box-shadow: 0 0 0 3px var(--bg); } }",
      "@media screen { .fileview-md a.fv-dead:has(.fv-figopen-web), .fileview-md a.fv-dead:has(img[data-fv-figweb]) { opacity: 1; color: color-mix(in srgb, currentColor 70%, transparent); } }",
    ], name + ": the rules naming the mark are exactly the tap rule it shares with the web control (no browser tap highlight; the tap-highlight ruling of 2026-09-24), the margin at rest on every pointer, the hover rule and the at-rest rule where hover is none or any pointer is coarse, the control's dashed dress as an outline (an outline and not a border: a border on the img widens its box) over a ring of var(--bg) 3px wide, so both sides of every dash and the gaps read the page's own ground whatever stands behind the picture, the margin 3px up and down and 3px plus 0.3em across the line so the ring covers no neighbouring ink at the picture's own text size, and an italic or bold italic f's ink before a picture in smaller text only within the bound the sheets' comment states (the file review's round 14, correctness-2 with extra5-1 and extra5-2: inside a highlight the dark theme's dashes read 2.40:1 against its tint, and a 2px ring left the line's outer side on it; the margin ruling of 2026-09-24: at the ring's width across the line an italic f lost the ink it paints past its own box to the ring; the second margin ruling that day: at a fixed 7px an italic f in a heading and at a larger text size lost it too, and at 2px up and down the ring covered a key's bottom row on the line above), and the dead link holding the dress, whose dimming moves off opacity so the dress inside it paints at the token's ratio (the painted-contrast ask of 2026-09-23; a property pin over the derived population, its count never typed)");
    assert.doesNotMatch(print, /data-fv-figweb/, name + ": the print block names the mark nowhere");
    // one colour token for the two dresses (the owner's call with that ruling): the mark's outline wears the token the control's dashed
    // border wears at rest, the outbound dress's own (the file review's round 13, ui-1 with extra6-1: the button family's hairline it
    // wore before read at 1.35:1 dark and 1.25:1 light on a 20 px badge), read off the web control's rest rule and never typed here;
    // the token's ratio over the page is theme-parity.test.ts's pair, and the leg's touch cases read it off the paint
    const rest = cssRules(css).find((r) => r.selector === ".fileview-md .fv-figopen-web:not(:hover)");
    const token = rest && /^border-color: var\((--[\w-]+)\);$/.exec(rest.body.trim());
    assert.ok(token, name + ": the web control's rest rule and its border token, scoped off :hover so .fileview-btn:hover's accent border still wins on the control (the two rules share a specificity and this one is later in the sheet; a property pin: the token is read off the rule and never typed here)");
    assert.notEqual(token![1], "--card-border", name + ": the token is the dress's own, not the button family's 10 percent hairline (a property pin over the derived token: the one name it may not be)");
    const onImg = mark.filter((r) => r.selector.split(",").every((sel) => /img\[data-fv-figweb\](?::hover)?$/.test(sel.trim())));   // the rules whose subject is the picture, not the dead link holding it
    assert.ok(onImg.length > 0, name + ": the rules dressing the picture itself are read (a derivation guard: an empty set is a broken read, not a clean sheet)");
    const outlined = onImg.filter((r) => /(?:^|;\s*)outline:/.test(r.body.trim()));   // the outline rules, not the margin that keeps their ring off neighbouring ink at the picture's own text size (the file review's round 14, correctness-2)
    assert.ok(outlined.length > 0, name + ": the outline rules on the picture are read (a derivation guard: an empty set is a broken read, not a clean sheet)");
    for (const r of outlined) assert.match(r.body, new RegExp("outline: 1px dashed var\\(" + token![1] + "\\);"), name + ": the mark's outline wears " + token![1] + ", the token the control's dashed border wears at rest, so the two dresses are one colour (a property pin: the token derived from the control's rest rule)");
    // the closed set over the control's rules, read as RULES (ui/webview/css-rules.mjs, the reader this home shares with
    // tools/markdown-viewer-plan-linknav.test.mjs: brace-matched over the comment-stripped sheet, each rule with the at-rules
    // enclosing it), so a rule written the sheets' own way, indented inside an at-rule block or on a grouped selector wrapped
    // across lines, is in the population (the file review's round 9, correctness-1 with tests-1 and ui-1: the set had been
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
      ".fileview-md .fv-figopen { position: relative; z-index: 1; vertical-align: top; margin: 0; margin-inline: -28px 6px; top: 6px; padding: 3px; background: var(--bg); opacity: 0; }",
      ".fileview-md .fv-figopen:hover { background: var(--bg) linear-gradient(var(--accent-wash), var(--accent-wash)); }",
      ".fileview-md .fv-figopen-left { float: left; margin: 0 6px 0 -28px; }", ".fileview-md .fv-figopen-right { float: right; margin: 0 -28px 0 6px; }",
      ".fileview-md .fv-figopen-web { border-style: dashed; }",
      ".fileview-md .fv-figopen-web:not(:hover) { border-color: var(--outbound-line); }",
    ], name + ": the rules naming the control outside a screen-only at-rule, however the sheet writes them, are exactly the rest, the hover background, the float twins, the web dress and its rest colour; any other rule naming the class there is one a print would apply; a property pin over the parsed rules, the set's membership however the sheet writes it" + BOUND + ")");
    assert.deepEqual(control.filter((r) => underScreen(r.chain)).map(renderRule), [
      "@media screen { .fileview-md :hover + .fv-figopen, .fileview-md .fv-figopen:hover, .fileview-md .fv-figopen:focus-visible, .fileview-md .fv-figopen-web:focus { opacity: 1; } }",
      "@media screen and (hover: none), screen and (any-pointer: coarse) { .fileview-md .fv-figopen { opacity: 0.8; } }",
      "@media screen and (hover: none), screen and (any-pointer: coarse) { .fileview-md .fv-figopen-web { opacity: 1; } }",
      "@media screen { .fileview-md .fv-figopen-web:focus-visible { outline-offset: 2px; } }",
      "@media screen { .fileview-md .fv-figopen-web:active { transform: none; } }",
      "@media screen { .fileview-md .fv-figopen-web, .fileview-md img[data-fv-figweb] { -webkit-tap-highlight-color: transparent; } }",
      "@media screen { .fileview-md a.fv-dead:has(.fv-figopen-web), .fileview-md a.fv-dead:has(img[data-fv-figweb]) { opacity: 1; color: color-mix(in srgb, currentColor 70%, transparent); } }",
    ], name + ": the rules under a screen-only at-rule are the reveal (the web control's under any focus among it), the at-rest rule (no hover, or any coarse pointer), the web control's full opacity at rest, its focus ring off its border, its press cue off, the browser's tap highlight off on it and on the mark (the tap-highlight ruling of 2026-09-24) and the dead link holding the dress, whose selector names the class inside :has() (a property pin over the parsed rules)");
  }
});

test("the reader the closed set stands on reads rules, not lines: the three shapes the line-keyed set missed or read are in the population alike, an indented reveal under an at-rule other than screen, a grouped selector wrapped across lines and a column-zero rule, each read as a rule outside screen; a rule indented inside a multi-line @media screen block is under screen as a one-line one is; a brace in a comment is no rule (the file review's round 9, correctness-1 with tests-1 and ui-1)", () => {
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
    "@media screen and (hover: none), screen and (any-pointer: coarse) { .fileview-md .fv-figopen { opacity: 0.8; } }",
  ].join("\n");
  const control = cssRules(sheet).filter((r) => /fv-figopen/.test(r.selector));
  assert.deepEqual(control.filter((r) => !underScreen(r.chain)).map(renderRule), [
    ".fileview-md .fv-figopen { opacity: 0; }",
    "@media (min-width: 1px) { .fileview-md .fv-figopen { opacity: 1; } }",
    ".fileview-md .fv-figerr, .fileview-md .fv-figopen { opacity: 1; }",
  ], "the column-zero rule, the indented reveal under (min-width: 1px) and the grouped selector's continuation-line reveal are rules outside screen; the comment's brace is none");
  assert.deepEqual(control.filter((r) => underScreen(r.chain)).map(renderRule), [
    "@media screen { .fileview-md .fv-figopen:focus-visible { opacity: 1; } }",
    "@media screen and (hover: none), screen and (any-pointer: coarse) { .fileview-md .fv-figopen { opacity: 0.8; } }",
  ], "the indented rule inside the multi-line screen block and the one-line screen rule, a query list with screen on both members, are under screen");
});

/** One Playwright Mouse call as mouseCalls reads it: the method's name, and the call's argument list as written. */
type MouseCall = { method: string; args: string };
/** Every call of a Mouse method in one module's text, read by the compiler (the file review's round 14, tests-1 with extra6-3: the
 *  read before it matched an identifier character, `.mouse.`, a name and a paren on one line, so a receiver ending in `]`, `!` or
 *  `)`, optional chaining, a line break before `.mouse` or before the method, a string-literal key and a space before the paren
 *  each carried a modifiers key unseen, and its `.mouse.` prefilter skipped such a file before any read ran). The module's code
 *  alone (codeOnly strips its comments) is parsed, and every call whose callee, looked through parentheses, a non-null assertion,
 *  `as`, `satisfies` and a type assertion, is a member of a member named `mouse`, each member a property access (`.name` or
 *  `?.name`) or an element access keyed by a string literal (`["name"]`, in either position: `page["mouse"].click(...)` and
 *  `page.mouse["click"](...)`), is one call, its arguments the source text between the call's parens. A string, a template and a
 *  regex literal are one token each to the parser, so a quoted `.mouse.click(` is no call. Outside the read, the bound the census
 *  pin's title states and does not resolve: a Mouse reached through an element access whose key is computed (not a literal), a
 *  Mouse or one of its methods reached through an alias (`const m = page.mouse; m.click(...)`, `const c = page.mouse.click;
 *  c(...)`) or through a destructured binding (`const { mouse } = page; mouse.click(...)`, `const { click } = page.mouse;
 *  click(...)`), whose call has a bare name for its callee, and a Mouse method invoked indirectly, in six forms: by `call` (`page.mouse.click.call(page.mouse, ...)`), by `apply`, by
 *  `bind` (`page.mouse.click.bind(page.mouse)(...)`), through a comma expression (`(0, page.mouse.click)(...)`), by
 *  `Reflect.apply(page.mouse.click, page.mouse, [...])`, and as a method of a function parameter named mouse that is passed
 *  `page.mouse` (`mouse.click(...)` inside the function): for call and apply the member before the method is `click`, not
 *  `mouse`; for bind the call that carries the arguments has for its callee the bound function, a call's result and no member; the
 *  comma form and Reflect.apply call no member of `mouse` at all, and the parameter is a bare name, so none is read.
 *  Each is an unseen-passing plant below, a limit stated as read and not a closure (the file review's round 15, extra6-3). Null when the text holds no word `mouse` at all: the prefilter is as wide as the read, so
 *  no spelling the read counts can be skipped by it. */
function mouseCalls(raw: string): MouseCall[] | null {
  if (!/\bmouse\b/.test(raw)) return null;
  const code = codeOnly(raw);
  const sf = ts.createSourceFile("mouse-calls.ts", code, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);
  const bare = (e: ts.Expression): ts.Expression => { for (;;) { if (ts.isParenthesizedExpression(e) || ts.isNonNullExpression(e) || ts.isAsExpression(e) || ts.isSatisfiesExpression(e) || ts.isTypeAssertionExpression(e)) e = e.expression; else return e; } };
  const member = (e: ts.Expression): { name: string; of: ts.Expression } | null => {
    if (ts.isPropertyAccessExpression(e)) return { name: e.name.text, of: e.expression };
    if (ts.isElementAccessExpression(e) && ts.isStringLiteralLike(e.argumentExpression)) return { name: e.argumentExpression.text, of: e.expression };
    return null;
  };
  const out: MouseCall[] = [];
  const visit = (n: ts.Node): void => {
    if (ts.isCallExpression(n)) {
      const callee = member(bare(n.expression));
      const receiver = callee ? member(bare(callee.of)) : null;
      if (callee && receiver && receiver.name === "mouse") out.push({ method: callee.name, args: code.slice(n.arguments.pos, n.arguments.end) });
    }
    ts.forEachChild(n, visit);
  };
  visit(sf);
  return out;
}
test("no call of Playwright's Mouse under ui/webview carries a modifiers key: mouse.click, dblclick, down, up, move and wheel take no modifiers option (playwright-core's Mouse interface) and drop one silently, so a modified click there is the key held around the click (keyboard.down, mouse.click, keyboard.up), as file-figure-open-browser.test.ts's Ctrl-clicks are; a property pin over the tree, the files derived by reading the directory and each module read by the compiler (mouseCalls): every call whose callee is a member of a member named mouse, through parentheses, a non-null assertion, as, satisfies and a type assertion, each member a property access, optional or not, or an element access keyed by a string literal, its arguments read as written; outside the read, bounds this pin states and does not resolve: a Mouse reached through a computed key, a Mouse or one of its methods reached through an alias or a destructured binding, and a Mouse method invoked indirectly in six forms, by call, apply or bind, through a comma expression, by Reflect.apply, or as a method of a function parameter named mouse that is passed page.mouse (each an unseen-passing plant in the plant cases below; the file review's round 15, extra6-3: the title had named three shapes while the six indirect forms passed unseen too), and an options object bound to a name elsewhere, or spread in, and passed to the call (the file review's round 13, extra6-2: clickPicture's Ctrl form passed the option to mouse.click and dispatched a plain click, green because the plain click opened the same tab; its round 14, tests-1 with extra6-3: the read before the compiler walk saw only an identifier character, .mouse., a name and a paren on one line, and a prefilter skipped a file spelled otherwise)", (t) => {
  const dir = path.join(ROOT, "ui", "webview");
  const files = fs.readdirSync(dir).filter((f) => f.endsWith(".ts")).sort();
  const calls: { file: string; method: string }[] = [];
  const hits: string[] = [];
  for (const f of files) {
    // the compiler's calls, not a text match: a quoted `.mouse.` in a message or in this file's own plant literals is one literal token and no call
    const read = mouseCalls(fs.readFileSync(path.join(dir, f), "utf8"));
    if (read === null) continue;
    for (const c of read) {
      calls.push({ file: f, method: c.method });
      if (/\bmodifiers\b/.test(c.args)) hits.push(f + ": mouse." + c.method + "(" + c.args.replace(/\s+/g, " ") + ")");
    }
  }
  const clicks = calls.filter((c) => c.method === "click");
  t.diagnostic("Mouse census: " + calls.length + " calls over " + new Set(calls.map((c) => c.file)).size + " files, " + clicks.length + " of them mouse.click");
  // derivation guards, never counts: a shrunken census is a broken read, not a clean tree
  assert.ok(clicks.length >= 20, "the derivation found the legs' mouse.click calls (a derivation guard: fewer than twenty is a broken read, not a clean tree): " + clicks.length);
  assert.ok(clicks.some((c) => c.file === "file-figure-open-browser.test.ts"), "the derivation reaches the leg whose Ctrl-click helper the finding named");
  assert.deepEqual(hits, [], "no Mouse call carries a modifiers key: the option is dropped, and a Ctrl-click that dispatches as a plain one passes wherever the plain click does the same");
});
/** Synthetic module text for the census's plants (never a file under ui/webview): a declare line and one statement in a function. */
const mousePlant = (statement: string): string => "declare const page: any, pages: any[], ctx: any, key: string;\nexport async function plant(): Promise<void> {\n  " + statement + "\n}\n";
const MODS = '{ modifiers: ["Control"] }';
/** A plant's read: the calls mouseCalls counts in it and, of those, the ones whose arguments carry a modifiers key. */
const plantRead = (statement: string): [number, number] => { const got = mouseCalls(mousePlant(statement)) || []; return [got.length, got.filter((c) => /\bmodifiers\b/.test(c.args)).length]; };
test("the Mouse census's armed plants: each receiver shape the file review's round 14 named, one Mouse call carrying a literal modifiers key, is read as one call with the key: a receiver ending in ], ! or ) (a parenthesised as, a call's result), optional chaining before or after mouse, a line break before .mouse or before the method, a string-literal key for the method or for mouse, and whitespace before the call's paren (the file review's round 14, tests-1 with extra6-3: the read before the compiler walk counted none of them, its prefilter skipping four; a property pin over synthetic text, the read mouseCalls, red at the read before it)", () => {
  const ARMED: Array<[string, string]> = [
    ["a receiver ending in ]", "await pages[0].mouse.click(1, 2, " + MODS + ");"],
    ["a receiver ending in !", "await page!.mouse.click(1, 2, " + MODS + ");"],
    ["a receiver ending in ), a parenthesised as", "await (page as any).mouse.click(1, 2, " + MODS + ");"],
    ["a receiver ending in ), a call's result", "await (await ctx.newPage()).mouse.click(1, 2, " + MODS + ");"],
    ["optional chaining before mouse", "await page?.mouse.click(1, 2, " + MODS + ");"],
    ["optional chaining after mouse", "await page.mouse?.click(1, 2, " + MODS + ");"],
    ["a line break before .mouse", "await page\n    .mouse.click(1, 2, " + MODS + ");"],
    ["a line break before the method", "await page.mouse\n    .click(1, 2, " + MODS + ");"],
    ["a string-literal key for the method", 'await page.mouse["click"](1, 2, ' + MODS + ");"],
    ["a string-literal key for mouse", 'await page["mouse"].click(1, 2, ' + MODS + ");"],
    ["whitespace before the call's paren", "await page.mouse.click (1, 2, " + MODS + ");"],
  ];
  assert.deepEqual(ARMED.map(([shape, statement]) => [shape, ...plantRead(statement)]), ARMED.map(([shape]) => [shape, 1, 1]), "each plant read as one Mouse call carrying the key, [shape, calls, calls with the key] (a property pin over the read)");
});
test("the Mouse census's controls: the direct call and a quoted modifiers key are read as one call with the key, by this read and by the one before it; a quoted mention of .mouse.click( with a modifiers key in a string, a template or a regex literal, with no identifier character before the dot, is no call (the file review's round 14, tests-1 with extra6-3: controls, green at the read before the compiler walk by design, whose identifier-before rule counts no quoted mention, and each quoted mention red under a widened regex that leaves the literals in; a property pin over synthetic text)", () => {
  const COUNTED: Array<[string, string]> = [
    ["the direct call", "await page.mouse.click(1, 2, " + MODS + ");"],
    ["a quoted modifiers key", 'await page.mouse.click(1, 2, { "modifiers": ["Control"] });'],
  ];
  const QUOTED: Array<[string, string]> = [
    ["a string literal", "const note = \".mouse.click(1, 2, { modifiers: ['Control'] })\"; void note;"],
    ["a template literal", "const note = `.mouse.click(1, 2, { modifiers: [\"Control\"] })`; void note;"],
    ["a regex literal", "const re = /.mouse.click(1, 2, { modifiers: 1 })/; void re;"],
  ];
  assert.deepEqual(COUNTED.map(([shape, statement]) => [shape, ...plantRead(statement)]), COUNTED.map(([shape]) => [shape, 1, 1]), "the direct call and a quoted key, each one call with the key (a property pin over the read)");
  assert.deepEqual(QUOTED.map(([shape, statement]) => [shape, ...plantRead(statement)]), QUOTED.map(([shape]) => [shape, 0, 0]), "a quoted mention, no call (a property pin over the read)");
});
test("the Mouse census's bound, recorded: a Mouse reached through an alias, a destructured binding, or an element access whose key is computed, for mouse or for the method, a Mouse method reached through an alias or a destructured binding (named since a verifier of the fixes for the file review's round 15 planted them), and a Mouse method invoked indirectly in six forms, by call, by apply, by bind, through a comma expression, by Reflect.apply, and as a method of a function parameter named mouse passed page.mouse, each carries a modifiers key unseen, each plant read as no call at all, the bound the census pin's title states (the file review's round 14, tests-1 with extra6-3, as ruled: the first four stay outside the read, named in the title with an unseen-passing plant; the file review's round 15, extra6-3: the six indirect forms, a true limit stated as read; bound-recording plants, green at the read before the compiler walk by design, which saw none of them either, and at the head round 15 read, whose read is this one; a red here means the read now sees the shape and the title names a bound it no longer has; a property pin over synthetic text)", () => {
  const BOUND: Array<[string, string]> = [
    ["an alias", "const m = page.mouse; await m.click(1, 2, " + MODS + ");"],
    ["a destructured binding", "const { mouse } = page; await mouse.click(1, 2, " + MODS + ");"],
    ["a method alias", "const c = page.mouse.click; await c(1, 2, " + MODS + ");"],
    ["a destructured method", "const { click } = page.mouse; await click(1, 2, " + MODS + ");"],
    ["a computed key for mouse", "await page[key].click(1, 2, " + MODS + ");"],
    ["a computed key for the method", "await page.mouse[key](1, 2, " + MODS + ");"],
    ["call", "await page.mouse.click.call(page.mouse, 1, 2, " + MODS + ");"],
    ["apply", "await page.mouse.click.apply(page.mouse, [1, 2, " + MODS + "]);"],
    ["bind", "await page.mouse.click.bind(page.mouse)(1, 2, " + MODS + ");"],
    ["a comma expression", "await (0, page.mouse.click)(1, 2, " + MODS + ");"],
    ["Reflect.apply", "await Reflect.apply(page.mouse.click, page.mouse, [1, 2, " + MODS + "]);"],
    ["a function parameter named mouse passed page.mouse", "const press = async (mouse: any) => { await mouse.click(1, 2, " + MODS + "); }; await press(page.mouse);"],
  ];
  assert.deepEqual(BOUND.map(([shape, statement]) => [shape, plantRead(statement)]), BOUND.map(([shape]) => [shape, [0, 0]]), "each shape outside the read, [shape, [calls read, calls read with the key]] (a property pin recording the bound)");
});

// ── the dimming classes, both ways (the file review's round 16, extra5-2) ── The sheets say every state from which a gesture opens a web
// picture's tab paints its outbound dress at 3:1 or better; an author's span of a page class around the picture (tag-chip-off at 0.45)
// dimmed the dress under it while a tap still opened the tab, and no rule of a sheet undoes an ancestor's opacity. So file-view.ts
// drops every class the sheets dim from the author's markup around each figure of a file document (dropDimmingClasses over
// SHEET_DIM_CLASSES), and the list is held here to every sheet a page of either host loads (SHEETS, hostSheets), derived by the rule
// SHEET_DIM_CLASSES's docstring states and compared both ways: a class the sheets dim that the list lacks, and a listed class they no
// longer dim, each named. The derivation's reads are armed by planted rules in the same test. The open leg
// (file-figure-open-browser.test.ts) reads the drop's effect by pixels and file-view-outline.test.ts runs it over the stand-in.
/** `s` split at `ch` where no parenthesis, bracket or quote is open. */
function splitTop(s: string, ch: string): string[] {
  const out: string[] = [];
  let depth = 0, cur = "", quote: string | null = null;
  for (const c of s) {
    if (quote) { cur += c; if (c === quote) quote = null; continue; }
    if (c === '"' || c === "'") { quote = c; cur += c; continue; }
    if (c === "(" || c === "[") depth++;
    else if (c === ")" || c === "]") depth--;
    if (c === ch && depth === 0) { out.push(cur); cur = ""; } else cur += c;
  }
  out.push(cur);
  return out;
}
/** The properties a declaration block sets that dim what they apply to: an opacity under 1 (one it cannot read as a number, a var() or a
 *  calc(), counted as under, the safe side), a visibility other than visible (or inherit, initial, unset, revert), a filter or a clip-path
 *  other than none, and an animation naming keyframes that set one of those (`keyframes`). */
function dimsOf(body: string, keyframes: ReadonlySet<string>): string[] {
  const hits: string[] = [];
  for (const d of splitTop(body, ";")) {
    const at = d.indexOf(":");
    if (at < 0) continue;
    const p = d.slice(0, at).trim().toLowerCase(), v = d.slice(at + 1).trim().toLowerCase().replace("!important", "").trim();
    if (p === "opacity") { const m = /^([0-9.]+)(%?)$/.exec(v); if (!m || parseFloat(m[1]) / (m[2] ? 100 : 1) < 1) hits.push("opacity " + v); }
    else if (p === "visibility") { if (!["visible", "inherit", "initial", "unset", "revert"].includes(v)) hits.push("visibility " + v); }
    else if (p === "filter" || p === "-webkit-filter" || p === "clip-path" || p === "-webkit-clip-path") { if (v !== "none") hits.push(p + " " + v); }
    else if (p === "animation" || p === "animation-name") { for (const k of v.split(/[\s,]+/)) if (keyframes.has(k)) hits.push("animation " + k); }
  }
  return hits;
}
const keyframesOf = (chain: string[]): string | undefined => chain.map((c) => (/^@(?:-webkit-)?keyframes\s+(\S+)/i.exec(c) || [])[1]).find(Boolean);
/** `sel` with every :not(...) and :has(...) taken out, their arguments with them. */
function withoutNotHas(sel: string): string {
  let s = sel;
  for (let m = /:(?:not|has)\(/.exec(s); m; m = /:(?:not|has)\(/.exec(s)) {
    let i = m.index + m[0].length, depth = 1;
    for (; i < s.length && depth; i++) { if (s[i] === "(") depth++; else if (s[i] === ")") depth--; }
    s = s.slice(0, m.index) + s.slice(i);
  }
  return s;
}
/** Every class the sheets dim by SHEET_DIM_CLASSES's rule, each with the rules that dim it (sheet, selector, what dims): the keyframes
 *  that dim first, then each rule outside a keyframes block that dims, and from each of its selectors the subject's classes (the last
 *  compound's, outside :not() and :has()), or the other compounds' where the subject names none, and the other compounds' too where the
 *  subject names only classes the control wears (`control`). */
function dimmingClasses(sheets: Array<{ name: string; css: string }>, control: ReadonlySet<string>): Map<string, string[]> {
  const rules = sheets.flatMap((s) => cssRules(s.css).map((r) => ({ ...r, sheet: s.name })));
  const keyframes = new Set<string>();
  for (const r of rules) { const k = keyframesOf(r.chain); if (k && dimsOf(r.body, new Set()).length) keyframes.add(k); }
  const out = new Map<string, string[]>();
  const add = (c: string, why: string): void => { out.set(c, [...(out.get(c) || []), why]); };
  const CLASS = /\.(-?[_a-zA-Z][_a-zA-Z0-9-]*)/g;
  for (const r of rules) {
    if (keyframesOf(r.chain)) continue;
    const hits = dimsOf(r.body, keyframes);
    if (!hits.length) continue;
    for (const one of splitTop(r.selector, ",")) {
      const sel = one.trim(), compounds = withoutNotHas(sel).trim().split(/\s*[>+~]\s*|\s+/).filter(Boolean);
      const subject = [...(compounds[compounds.length - 1] || "").matchAll(CLASS)].map((m) => m[1]);
      const others = compounds.slice(0, -1).flatMap((c) => [...c.matchAll(CLASS)].map((m) => m[1]));
      const why = r.sheet + ": " + sel + " (" + hits.join(", ") + ")";
      for (const c of subject.length ? subject : others) add(c, why);
      if (subject.length && subject.every((c) => control.has(c))) for (const c of others) add(c, why + ", above the control");
    }
  }
  return out;
}
/** The list's drift from the sheets: the classes they dim that the list lacks, each with its first rule, and the listed classes they do not dim. */
function dimDrift(derived: Map<string, string[]>, listed: ReadonlySet<string>): { missing: string[]; stale: string[] } {
  return { missing: [...derived.keys()].filter((c) => !listed.has(c)).sort().map((c) => c + " (" + derived.get(c)![0] + ")"), stale: [...listed].filter((c) => !derived.has(c)).sort() };
}
/** SHEET_DIM_CLASSES read off file-view.ts's source: one array of string literals inside `new Set([` and `]);`. */
function listedDimClasses(): Set<string> {
  const m = /\nconst SHEET_DIM_CLASSES: ReadonlySet<string> = new Set\(\[\n([\s\S]*?)\n\]\);\n/.exec(VIEW);
  assert.ok(m, "file-view.ts holds SHEET_DIM_CLASSES as one array of string literals (a sentence pin on the shape this read takes)");
  const names: unknown[] = JSON.parse("[" + m![1] + "]");
  assert.ok(names.every((n) => typeof n === "string"), "every member a string literal");
  assert.equal(new Set(names).size, names.length, "no class listed twice");
  return new Set(names as string[]);
}
/** The classes the figure control wears, read off decideFigureControl's element and the class constants: the button's two family
 *  classes, FIGOPEN_CLASS, its float twins and FIGOPEN_WEB_CLASS. */
function controlClasses(): Set<string> {
  const base = /\nconst FIGOPEN_CLASS = "([\w-]+)";\n/.exec(VIEW), web = /\nconst FIGOPEN_WEB_CLASS = FIGOPEN_CLASS \+ "(-[\w-]+)";\n/.exec(VIEW);
  const made = /el\("button", "([\w -]+?) " \+ FIGOPEN_CLASS\)/.exec(VIEW);
  assert.ok(base && web && made && VIEW.includes('if (align === "left" || align === "right") b.classList.add(FIGOPEN_CLASS + "-" + align);'), "the control's classes: its element, the two class constants and the float twins, read off file-view.ts (a sentence pin on the spellings the read takes)");
  return new Set([...made![1].split(" "), base![1], base![1] + "-left", base![1] + "-right", base![1] + web![1]]);
}
test("the dimming classes, a two-way pin (the file review's round 16, extra5-2): SHEET_DIM_CLASSES in file-view.ts, the classes dropDimmingClasses takes off the author's markup around a figure, equals the classes every sheet a page of either host loads dims, derived by the rule its docstring states (an opacity under 1, one not read as a number counted as under, a visibility other than visible, a filter or a clip-path other than none, or an animation whose keyframes set one; the subject's classes outside :not() and :has(), else the other compounds', and the other compounds' too above the control's own classes); each class the sheets dim that the list lacks, and each listed class they no longer dim, is named; the derivation's reads are armed by planted rules, one per property, the keyframes and the clause above the control, and by a class taken off the list and one put on it, each named in the drift, with controls of the same properties that dim nothing (a property pin over the derived set against the list; red at every head before the list, whose literal it reads, and red with a class taken off the list and with a dimming rule added to a sheet under a class the list lacks)", () => {
  const listed = listedDimClasses(), control = controlClasses();
  const derived = dimmingClasses(SHEETS, control);
  assert.ok(derived.size >= 200, "the derivation reads the sheets: " + derived.size + " classes (a derivation that reads nothing is red; a property pin over the derived set's size)");
  const drift = dimDrift(derived, listed);
  assert.deepEqual(drift.missing, [], "each class a sheet dims that SHEET_DIM_CLASSES lacks, with the rule that dims it: add it to the list, in the same change as the rule (a property pin over the derived set against the list)");
  assert.deepEqual(drift.stale, [], "each class SHEET_DIM_CLASSES lists that no sheet dims now: take it off the list, in the same change as the rule (a property pin over the derived set against the list)");
  // the reads armed, in this run: each planted rule's class is named missing, the controls' are not, and the list's own drift in both
  // directions is named
  const planted = { name: "planted", css: ".plant-op { opacity: 0.5; } .plant-var { opacity: var(--x); } .plant-vis { visibility: hidden; } .plant-filter { filter: grayscale(1); } .plant-clip { clip-path: inset(50%); } @keyframes plant-kf { from { opacity: 0; } to { opacity: 1; } } .plant-anim { animation: plant-kf 1s ease; } .plant-above .fv-figopen { opacity: 0.6; } .plant-keep { opacity: 1; } .plant-keep-vis { visibility: visible; } .plant-keep-filter { filter: none; } .plant-sub span { opacity: 0.4; }" };
  assert.ok(control.has("fv-figopen") && listed.has("fv-figopen"), "the control's own class is one the control wears and one the list holds (the planted rule above it is read by the clause above the control alone)");
  const withPlant = dimDrift(dimmingClasses([...SHEETS, planted], control), listed).missing.map((m) => m.split(" ")[0]);
  assert.deepEqual(withPlant, ["plant-above", "plant-anim", "plant-clip", "plant-filter", "plant-op", "plant-sub", "plant-var", "plant-vis"], "a planted sheet's dimming classes are named missing, the rule above the control's class and the one whose subject names no class among them, and its controls (an opacity of 1, a visible visibility, a filter of none) are not (a property pin over the drift)");
  const cut = new Set(listed); cut.delete("tag-chip-off");
  assert.deepEqual(dimDrift(derived, cut).missing.map((m) => m.split(" ")[0]), ["tag-chip-off"], "a class taken off the list is named missing (a property pin over the drift)");
  assert.deepEqual(dimDrift(derived, new Set([...listed, "plant-never-dims"])).stale, ["plant-never-dims"], "a class put on the list that no sheet dims is named (a property pin over the drift)");
});

// ── the classes that let a press pass through, both ways (the file review's round 16, extra5-1, the covered sign) ── The one gate's hit
// test (file-view.ts signUncovered, elementFromPoint) reads the element a press would reach, so an author's element of a page class that
// sets pointer-events none (locate-toast: fixed, opaque) painted over the web control while the gate read the control uncovered and the
// tab opened. file-view.ts takes every such class off a file document's author markup (dropPressThrough over
// SHEET_PRESS_THROUGH_CLASSES), and the list is held here to every sheet a page of either host loads (SHEETS), derived by the rule the
// list's docstring states and compared both ways, as the dimming classes are above, with one more read: a rule that sets the property
// with no class to take (its subject and its other compounds name none) and no id in its subject reaches author markup that no drop of a
// class undoes, and is named. The open leg reads the drop's effect on the gate and file-view-outline.test.ts runs it over the stand-in.
/** The declarations of a block that let a press pass through what they apply to: pointer-events at any value but auto (one it cannot
 *  read, a var(), counted, the safe side), and an animation naming keyframes that set such a value (`keyframes`). */
function pressThroughOf(body: string, keyframes: ReadonlySet<string>): string[] {
  const hits: string[] = [];
  for (const d of splitTop(body, ";")) {
    const at = d.indexOf(":");
    if (at < 0) continue;
    const p = d.slice(0, at).trim().toLowerCase(), v = d.slice(at + 1).trim().toLowerCase().replace("!important", "").trim();
    if (p === "pointer-events") { if (v !== "auto") hits.push("pointer-events " + v); }
    else if (p === "animation" || p === "animation-name") { for (const k of v.split(/[\s,]+/)) if (keyframes.has(k)) hits.push("animation " + k); }
  }
  return hits;
}
/** Every class the sheets let a press pass through by SHEET_PRESS_THROUGH_CLASSES's rule, each with its rules (sheet, selector, what
 *  sets it), and the rules whose selector yields no class and names no id in its subject (`untaken`). */
function pressThroughClasses(sheets: Array<{ name: string; css: string }>): { classes: Map<string, string[]>; untaken: string[] } {
  const rules = sheets.flatMap((s) => cssRules(s.css).map((r) => ({ ...r, sheet: s.name })));
  const keyframes = new Set<string>();
  for (const r of rules) { const k = keyframesOf(r.chain); if (k && pressThroughOf(r.body, new Set()).length) keyframes.add(k); }
  const classes = new Map<string, string[]>(), untaken: string[] = [];
  const CLASS = /\.(-?[_a-zA-Z][_a-zA-Z0-9-]*)/g;
  for (const r of rules) {
    if (keyframesOf(r.chain)) continue;
    const hits = pressThroughOf(r.body, keyframes);
    if (!hits.length) continue;
    for (const one of splitTop(r.selector, ",")) {
      const sel = one.trim(), compounds = withoutNotHas(sel).trim().split(/\s*[>+~]\s*|\s+/).filter(Boolean);
      const last = compounds[compounds.length - 1] || "";
      const subject = [...last.matchAll(CLASS)].map((m) => m[1]);
      const others = compounds.slice(0, -1).flatMap((c) => [...c.matchAll(CLASS)].map((m) => m[1]));
      const why = r.sheet + ": " + sel + " (" + hits.join(", ") + ")";
      const got = subject.length ? subject : others;
      for (const c of got) classes.set(c, [...(classes.get(c) || []), why]);
      if (!got.length && !/#-?[_a-zA-Z]/.test(last)) untaken.push(why);
    }
  }
  return { classes, untaken };
}
/** SHEET_PRESS_THROUGH_CLASSES read off file-view.ts's source: one array of string literals inside `new Set([` and `]);`. */
function listedPressThroughClasses(): Set<string> {
  const m = /\nconst SHEET_PRESS_THROUGH_CLASSES: ReadonlySet<string> = new Set\(\[\n([\s\S]*?)\n\]\);\n/.exec(VIEW);
  assert.ok(m, "file-view.ts holds SHEET_PRESS_THROUGH_CLASSES as one array of string literals (a sentence pin on the shape this read takes)");
  const names: unknown[] = JSON.parse("[" + m![1] + "]");
  assert.ok(names.every((n) => typeof n === "string"), "every member a string literal");
  assert.equal(new Set(names).size, names.length, "no class listed twice");
  return new Set(names as string[]);
}
test("the classes that let a press pass through, a two-way pin (the file review's round 16, extra5-1, the covered sign): SHEET_PRESS_THROUGH_CLASSES in file-view.ts, the classes dropPressThrough takes off every author element of a file document, equals the classes every sheet a page of either host loads sets pointer-events on at any value but auto (one not read counted), directly or by an animation whose keyframes do, derived by the rule its docstring states (the subject's classes outside :not() and :has(), else the other compounds'); each class the sheets set it on that the list lacks, and each listed class they no longer set it on, is named, and so is each rule that sets it with no class to take and no id in its subject, whose reach no drop of a class undoes; no listed class is one the markdown renderers write before the sanitizer (md-config.ts's and math.ts's class constants and a dead wikilink's fv-dead), which the drop over every element would strip; the derivation's reads are armed by planted rules, a declaration, a var(), a pseudo-element, a subject that names no class, a :not() whose argument is not taken, the keyframes, and an element-keyed and an attribute-keyed rule named as untaken beside an id-keyed one that is not, and by a class taken off the list and one put on it, each named in the drift, with controls of auto that let nothing through (a property pin over the derived set against the list; red at every head before the list, whose literal it reads, and red with a class taken off the list and with a rule added to a sheet under a class the list lacks)", () => {
  const listed = listedPressThroughClasses();
  const { classes: derived, untaken } = pressThroughClasses(SHEETS);
  assert.ok(derived.size >= 30, "the derivation reads the sheets: " + derived.size + " classes (a derivation that reads nothing is red; a property pin over the derived set's size)");
  const drift = dimDrift(derived, listed);
  assert.deepEqual(drift.missing, [], "each class a sheet lets a press pass through that SHEET_PRESS_THROUGH_CLASSES lacks, with the rule that does it: add it to the list, in the same change as the rule (a property pin over the derived set against the list)");
  assert.deepEqual(drift.stale, [], "each class SHEET_PRESS_THROUGH_CLASSES lists that no sheet lets a press pass through now: take it off the list, in the same change as the rule (a property pin over the derived set against the list)");
  assert.deepEqual(untaken, [], "each rule that sets pointer-events with no class for the drop to take and no id in its subject, which reaches an author's element no drop of a class undoes: key it on a class the list then takes, or take the property off (a property pin over the sheets' rules)");
  const RENDERED = new Set<string>(["fv-dead", ...[web("md-config.ts"), web("math.ts")].flatMap((src) => [...src.matchAll(/\nexport const \w+_CLASS = "([\w-]+)";/g)].map((m) => m[1]))]);
  assert.ok(RENDERED.has("fv-wikilink") && RENDERED.has("md-math-inline") && RENDERED.size >= 10, "the renderers' class constants read off md-config.ts and math.ts (a sentence pin on the spelling the read takes): " + [...RENDERED].join(" "));
  assert.deepEqual([...listed].filter((c) => RENDERED.has(c)), [], "no listed class is one a markdown renderer writes before the sanitizer, which the drop over every element would strip from the viewer's own markup (a property pin over the two sets)");
  const planted = { name: "planted", css: ".plant-pe { pointer-events: none; } .plant-var { pointer-events: var(--x); } .plant-psd::after { pointer-events: none; } .plant-sub span { pointer-events: none; } .plant-not:not(.plant-neg) { pointer-events: none; } @keyframes plant-kf { from { pointer-events: none; } } .plant-anim { animation: plant-kf 1s; } .plant-keep { pointer-events: auto; } .plant-keep-imp { pointer-events: auto !important; } aside { pointer-events: none; } [data-plant] { pointer-events: none; } #plant-id { pointer-events: none; }" };
  const withPlant = pressThroughClasses([...SHEETS, planted]);
  assert.deepEqual(dimDrift(withPlant.classes, listed).missing.map((m) => m.split(" ")[0]), ["plant-anim", "plant-not", "plant-pe", "plant-psd", "plant-sub", "plant-var"], "a planted sheet's classes are named missing, the pseudo-element's, the one above a subject that names no class and the animation's among them, and neither the :not() argument nor the controls of auto are (a property pin over the drift)");
  assert.deepEqual(withPlant.untaken, ["planted: aside (pointer-events none)", "planted: [data-plant] (pointer-events none)"], "the element-keyed and the attribute-keyed plants are named as untaken, and the id-keyed one is not (a property pin over the read)");
  const cut = new Set(listed); cut.delete("locate-toast");
  assert.deepEqual(dimDrift(derived, cut).missing.map((m) => m.split(" ")[0]), ["locate-toast"], "a class taken off the list is named missing (a property pin over the drift)");
  assert.deepEqual(dimDrift(derived, new Set([...listed, "plant-never-passes"])).stale, ["plant-never-passes"], "a class put on the list that no sheet lets a press pass through is named (a property pin over the drift)");
});

// ── the classes that would raise author content to the control's stacking level, both ways (the file review's round 16, extra5-1, the
// covered sign) ── The picture's control rests positioned at z-index 1 (the dressing sheets' `.fileview-md .fv-figopen` rule), and that
// z-index, not its place in the document, keeps it above the author elements the sheets leave at z-index auto or 0, wherever no stacking
// context stands around the picture (the next pin's list, and the table's shift, which is no translate). An author's element of a page
// class that gives it a z-index at or above the control's is left at or above the control, so file-view.ts takes every such class off a
// file document's author markup (dropStackClasses over SHEET_STACK_CLASSES), and the list is held here to every sheet a page of either
// host loads (SHEETS), derived by the rule the list's docstring states and compared both ways, as the press-through classes are above,
// with the same read for a rule that gives the z-index with no class to take (its subject and its other compounds name none) and no id
// in its subject, which reaches author markup no drop of a class undoes, and is named. The open leg reads the drop's effect on the gate
// and file-view-outline.test.ts runs it over the stand-in.
/** The declarations of a block that leave what they apply to at or above the control's stacking level: a z-index at or above the
 *  control's (one the reader cannot read as an integer, a var(), counted, the safe side; auto, initial, inherit, unset and revert are
 *  not, they resolve to auto), and an animation naming keyframes that set such a z-index (`keyframes`). */
function stacksOf(body: string, keyframes: ReadonlySet<string>): string[] {
  const hits: string[] = [];
  for (const d of splitTop(body, ";")) {
    const at = d.indexOf(":");
    if (at < 0) continue;
    const p = d.slice(0, at).trim().toLowerCase(), v = d.slice(at + 1).trim().toLowerCase().replace("!important", "").trim();
    if (p === "z-index") { const m = /^(-?\d+)$/.exec(v); if (!m) { if (!["auto", "initial", "inherit", "unset", "revert"].includes(v)) hits.push("z-index " + v); } else if (parseInt(m[1], 10) >= CONTROL_Z) hits.push("z-index " + v); }
    else if (p === "animation" || p === "animation-name") { for (const k of v.split(/[\s,]+/)) if (keyframes.has(k)) hits.push("animation " + k); }
  }
  return hits;
}
/** The control's own stacking level, read off the dressing sheets: the z-index of the rule whose subject is the control's class
 *  (`.fileview-md .fv-figopen`), which every listed class is measured at or above. */
const CONTROL_Z = ((): number => {
  for (const s of SHEETS) for (const r of cssRules(s.css)) if (/\.fv-figopen\s*$/.test(r.selector.trim())) { const m = /(?:^|;)\s*z-index\s*:\s*(-?\d+)/.exec(r.body); if (m) return parseInt(m[1], 10); }
  throw new Error("the control's z-index rule (.fileview-md .fv-figopen) is not in the sheets");
})();
/** Every class the sheets would raise to the control's stacking level or past it by SHEET_STACK_CLASSES's rule, each with its rules
 *  (sheet, selector, what raises it), and the rules whose selector yields no class and names no id in its subject (`untaken`). */
function stackClasses(sheets: Array<{ name: string; css: string }>): { classes: Map<string, string[]>; untaken: string[] } {
  const rules = sheets.flatMap((s) => cssRules(s.css).map((r) => ({ ...r, sheet: s.name })));
  const keyframes = new Set<string>();
  for (const r of rules) { const k = keyframesOf(r.chain); if (k && stacksOf(r.body, new Set()).length) keyframes.add(k); }
  const classes = new Map<string, string[]>(), untaken: string[] = [];
  const CLASS = /\.(-?[_a-zA-Z][_a-zA-Z0-9-]*)/g;
  for (const r of rules) {
    if (keyframesOf(r.chain)) continue;
    const hits = stacksOf(r.body, keyframes);
    if (!hits.length) continue;
    for (const one of splitTop(r.selector, ",")) {
      const sel = one.trim(), compounds = withoutNotHas(sel).trim().split(/\s*[>+~]\s*|\s+/).filter(Boolean);
      const last = compounds[compounds.length - 1] || "";
      const subject = [...last.matchAll(CLASS)].map((m) => m[1]);
      const others = compounds.slice(0, -1).flatMap((c) => [...c.matchAll(CLASS)].map((m) => m[1]));
      const why = r.sheet + ": " + sel + " (" + hits.join(", ") + ")";
      const got = subject.length ? subject : others;
      for (const c of got) classes.set(c, [...(classes.get(c) || []), why]);
      if (!got.length && !/#-?[_a-zA-Z]/.test(last)) untaken.push(why);
    }
  }
  return { classes, untaken };
}
/** SHEET_STACK_CLASSES read off file-view.ts's source: one array of string literals inside `new Set([` and `]);`. */
function listedStackClasses(): Set<string> {
  const m = /\nconst SHEET_STACK_CLASSES: ReadonlySet<string> = new Set\(\[\n([\s\S]*?)\n\]\);\n/.exec(VIEW);
  assert.ok(m, "file-view.ts holds SHEET_STACK_CLASSES as one array of string literals (a sentence pin on the shape this read takes)");
  const names: unknown[] = JSON.parse("[" + m![1] + "]");
  assert.ok(names.every((n) => typeof n === "string"), "every member a string literal");
  assert.equal(new Set(names).size, names.length, "no class listed twice");
  return new Set(names as string[]);
}
test("the classes that would raise author content to the control's stacking level, a two-way pin (the file review's round 16, extra5-1, the covered sign): SHEET_STACK_CLASSES in file-view.ts, the classes dropStackClasses takes off every author element of a file document, equals the classes every sheet a page of either host loads gives a z-index at or above the control's (one not read counted), directly or by an animation, and no rule gives the z-index with no class to take and no id in its subject; the control's own z-index read off the sheets", () => {
  const listed = listedStackClasses();
  assert.equal(CONTROL_Z, 1, "the control rests at z-index 1 (read off the dressing sheets' .fv-figopen rule)");
  const { classes: derived, untaken } = stackClasses(SHEETS);
  assert.ok(derived.size >= 40, "the derivation reads the sheets: " + derived.size + " classes (a derivation that reads nothing is red; a property pin over the derived set's size)");
  const drift = dimDrift(derived, listed);
  assert.deepEqual(drift.missing, [], "each class a sheet would raise to the control's stacking level that SHEET_STACK_CLASSES lacks, with the rule that does it: add it to the list, in the same change as the rule (a property pin over the derived set against the list)");
  assert.deepEqual(drift.stale, [], "each class SHEET_STACK_CLASSES lists that no sheet raises now: take it off the list, in the same change as the rule (a property pin over the derived set against the list)");
  assert.deepEqual(untaken, [], "each rule that gives a z-index at or above the control's with no class for the drop to take and no id in its subject, which reaches an author's element no drop of a class undoes: key it on a class the list then takes, or take the z-index off (a property pin over the sheets' rules)");
  const RENDERED = new Set<string>(["fv-dead", ...[web("md-config.ts"), web("math.ts")].flatMap((src) => [...src.matchAll(/\nexport const \w+_CLASS = "([\w-]+)";/g)].map((m) => m[1]))]);
  assert.deepEqual([...listed].filter((c) => RENDERED.has(c)), [], "no listed class is one a markdown renderer writes before the sanitizer, which the drop over every element would strip from the viewer's own markup (a property pin over the two sets)");
  const planted = { name: "planted", css: ".plant-z { z-index: 5; } .plant-z1 { z-index: 1; } .plant-z0 { z-index: 0; } .plant-zneg { z-index: -1; } .plant-zauto { z-index: auto; } .plant-zvar { z-index: var(--x); } .plant-zpsd::after { z-index: 3; } .plant-zsub span { z-index: 2; } .plant-znot:not(.plant-zneg2) { z-index: 4; } @keyframes plant-zkf { from { z-index: 9; } } .plant-zanim { animation: plant-zkf 1s; } aside { z-index: 7; } [data-plant] { z-index: 8; } #plant-id { z-index: 6; }" };
  const withPlant = stackClasses([...SHEETS, planted]);
  assert.deepEqual(dimDrift(withPlant.classes, listed).missing.map((m) => m.split(" ")[0]), ["plant-z", "plant-z1", "plant-zanim", "plant-znot", "plant-zpsd", "plant-zsub", "plant-zvar"], "a planted sheet's raising classes are named missing, the one at the control's own z-index, the pseudo-element's, the one above a subject that names no class and the animation's among them, and neither a z-index below the control (0, negative, auto), the :not() argument, nor the controls are (a property pin over the drift)");
  assert.deepEqual(withPlant.untaken, ["planted: aside (z-index 7)", "planted: [data-plant] (z-index 8)"], "the element-keyed and the attribute-keyed plants are named as untaken, and the id-keyed one is not (a property pin over the read)");
  const cut = new Set(listed); cut.delete("ctx-text");
  assert.deepEqual(dimDrift(derived, cut).missing.map((m) => m.split(" ")[0]), ["ctx-text"], "a class taken off the list is named missing (a property pin over the drift)");
  assert.deepEqual(dimDrift(derived, new Set([...listed, "plant-never-stacks"])).stale, ["plant-never-stacks"], "a class put on the list that no sheet raises is named (a property pin over the drift)");
});

// ── the classes that would make an element around a picture a stacking context, both ways (the file review's round 17, extra9-1, and the
// coordinator's decision 4 on it) ── A stacking context around a picture holds its control's z-index 1 inside it, and the z-index then
// keeps the control above nothing outside that context, so file-view.ts takes off each figure and every element above it the page
// classes the sheets would make a stacking context there (dropStackClasses over SHEET_CONTEXT_CLASSES), and the list is held here to
// every sheet a page of either host loads (SHEETS), derived by the rule its docstring states and compared both ways, as the lists
// above are. The same derivation names each rule with no class in its subject that would make a stacking context of an element that
// could hold a picture's control, keyed on nothing but the viewer's own chrome, the fileview family (the Rendered box fileview-md and
// every element above it in the viewer and the page, fileview-body, fileview, fileview-open, fileview-pane, whose classes no drop takes,
// since the drops run inside the sanitizer's body): such a rule reaches every author element of its shape, and no drop of a class undoes
// it. The viewer's own `.fileview-md > table` rule was one while the table's shift was a translate (red at 0ab74924c by that rule, and by
// the absent list); the shift is a position and a left now. The census's bound: a rule keyed on another class of the page's body, which
// stands above the viewer, would reach author markup too, and it reads no such class. The open leg and the engines leg read the drop's
// effect on the gate in three engines, and file-view-outline.test.ts runs it over the stand-in.
/** The declarations of a block that make what they apply to a stacking context, by SHEET_CONTEXT_CLASSES's rule: a transform, translate,
 *  rotate, scale or perspective, a filter, backdrop-filter, clip-path, mask, mask-image, mask-border, mask-box-image, view-transition-name
 *  or offset-path other than none, each under its -webkit- name too; an opacity under 1 (one not read as a number counted); a
 *  mix-blend-mode other than normal; an isolation other than auto; contain with layout or paint, strict or content (a value naming
 *  neither, size, inline-size and style alone, counted out); a content-visibility other than visible; a position other than static,
 *  relative and absolute (fixed, sticky, one not read); a z-index other than auto; a will-change naming one of these or a value not
 *  read; and an animation naming keyframes that set one (`keyframes`). initial, unset, revert and revert-layer count as none; container-type
 *  is no such property. */
function contextOf(body: string, keyframes: ReadonlySet<string>): string[] {
  const NONE_TAKERS = ["transform", "translate", "rotate", "scale", "perspective", "filter", "backdrop-filter", "clip-path", "mask", "mask-image", "mask-border", "mask-box-image", "view-transition-name", "offset-path"];
  const WILL = [...NONE_TAKERS, "opacity", "mix-blend-mode", "isolation", "contain", "content-visibility", "position", "z-index"];
  const hits: string[] = [];
  for (const d of splitTop(body, ";")) {
    const at = d.indexOf(":");
    if (at < 0) continue;
    const p = d.slice(0, at).trim().toLowerCase().replace(/^-webkit-/, ""), v = d.slice(at + 1).trim().toLowerCase().replace("!important", "").trim();
    if (["initial", "unset", "revert", "revert-layer"].includes(v)) continue;
    if (NONE_TAKERS.includes(p)) { if (v !== "none") hits.push(p + " " + v); }
    else if (p === "opacity") { const m = /^([0-9.]+)(%?)$/.exec(v); if (!m || parseFloat(m[1]) / (m[2] ? 100 : 1) < 1) hits.push("opacity " + v); }
    else if (p === "mix-blend-mode") { if (v !== "normal") hits.push(p + " " + v); }
    else if (p === "isolation") { if (v !== "auto") hits.push(p + " " + v); }
    else if (p === "contain") { if (v !== "none" && !/^(?:size|inline-size|style|\s)+$/.test(v)) hits.push(p + " " + v); }
    else if (p === "content-visibility") { if (v !== "visible") hits.push(p + " " + v); }
    else if (p === "position") { if (!["static", "relative", "absolute"].includes(v)) hits.push(p + " " + v); }
    else if (p === "z-index") { if (v !== "auto") hits.push("z-index " + v); }
    else if (p === "will-change") { if (v !== "auto" && v.split(/\s*,\s*/).some((x) => WILL.includes(x.replace(/^-webkit-/, "")) || !/^[a-z-]+$/.test(x))) hits.push(p + " " + v); }
    else if (p === "animation" || p === "animation-name") { for (const k of v.split(/[\s,]+/)) if (keyframes.has(k)) hits.push("animation " + k); }
  }
  return hits;
}
/** A subject compound on a pseudo-element, whose box holds no picture. */
const PSEUDO_ELEMENT = /::?(?:before|after|marker|placeholder|selection|backdrop|first-line|first-letter|file-selector-button|cue|-webkit-[\w-]+|-moz-[\w-]+)/i;
/** The tags whose element can hold no picture's control: the void elements, and every tag the sanitizer removes (md-sanitize.ts
 *  MD_FORBID_TAGS, read off its source), with the body and the root, which no author markup is. */
const HOLDS_NOTHING = ((): Set<string> => {
  const m = /export const MD_FORBID_TAGS: readonly string\[\] = \[([\s\S]*?)\];/.exec(web("md-sanitize.ts"));
  assert.ok(m, "md-sanitize.ts holds MD_FORBID_TAGS as one array literal (a sentence pin on the shape this read takes)");
  const forbid: string[] = JSON.parse("[" + m![1].trim().replace(/,\s*$/, "") + "]");
  assert.ok(forbid.includes("button") && forbid.includes("form"), "the sanitizer's forbidden tags read: " + forbid.join(" "));
  return new Set([...forbid, "img", "input", "br", "hr", "wbr", "area", "col", "embed", "source", "track", "meta", "link", "base", "param", "body", "html"]);
})();
/** Every class the sheets would make a stacking context around a picture by SHEET_CONTEXT_CLASSES's rule, before the other lists are
 *  taken out, each with its rules (sheet, selector, what makes it one), and apart from them the rules whose subject names no class,
 *  holds a control, names no id and is keyed on nothing but the viewer's own chrome, the fileview family (`reach`), which give the list
 *  no class since no drop could take one; a rule under print media, or on a pseudo-element, left out. */
function contextClasses(sheets: Array<{ name: string; css: string }>): { classes: Map<string, string[]>; reach: string[] } {
  const rules = sheets.flatMap((s) => cssRules(s.css).map((r) => ({ ...r, sheet: s.name })));
  const keyframes = new Set<string>();
  for (const r of rules) { const k = keyframesOf(r.chain); if (k && contextOf(r.body, new Set()).length) keyframes.add(k); }
  const classes = new Map<string, string[]>(), reach: string[] = [];
  const CLASS = /\.(-?[_a-zA-Z][_a-zA-Z0-9-]*)/g;
  for (const r of rules) {
    if (keyframesOf(r.chain)) continue;
    if (r.chain.some((c) => /^@media\s+print\b/i.test(c))) continue;
    const hits = contextOf(r.body, keyframes);
    if (!hits.length) continue;
    for (const one of splitTop(r.selector, ",")) {
      const sel = one.trim(), compounds = withoutNotHas(sel).trim().split(/\s*[>+~]\s*|\s+/).filter(Boolean);
      const last = compounds[compounds.length - 1] || "";
      if (PSEUDO_ELEMENT.test(last)) continue;
      const subject = [...last.matchAll(CLASS)].map((m) => m[1]);
      const others = compounds.slice(0, -1).flatMap((c) => [...c.matchAll(CLASS)].map((m) => m[1]));
      const why = r.sheet + ": " + sel + " (" + hits.join(", ") + ")";
      const tag = (/^([a-zA-Z][\w-]*)/.exec(last) || [])[1];
      if (!subject.length && !(tag && HOLDS_NOTHING.has(tag.toLowerCase())) && !/#-?[_a-zA-Z]/.test(last) && others.every((c) => /^fileview(?:-|$)/.test(c))) { reach.push(why); continue; }   // no class a drop could take: named, not listed
      for (const c of subject.length ? subject : others) classes.set(c, [...(classes.get(c) || []), why]);
    }
  }
  return { classes, reach };
}
/** SHEET_CONTEXT_CLASSES read off file-view.ts's source: one array of string literals inside `new Set([` and `]);`. */
function listedContextClasses(): Set<string> {
  const m = /\nconst SHEET_CONTEXT_CLASSES: ReadonlySet<string> = new Set\(\[\n([\s\S]*?)\n\]\);\n/.exec(VIEW);
  assert.ok(m, "file-view.ts holds SHEET_CONTEXT_CLASSES as one array of string literals (a sentence pin on the shape this read takes)");
  const names: unknown[] = JSON.parse("[" + m![1] + "]");
  assert.ok(names.every((n) => typeof n === "string"), "every member a string literal");
  assert.equal(new Set(names).size, names.length, "no class listed twice");
  return new Set(names as string[]);
}
/** The derived classes less the ones the other three lists take (SHEET_STACK_CLASSES and SHEET_PRESS_THROUGH_CLASSES off every element,
 *  SHEET_DIM_CLASSES off a figure's ancestors). */
const contextKept = (classes: Map<string, string[]>, others: ReadonlySet<string>): Map<string, string[]> => new Map([...classes].filter(([c]) => !others.has(c)));
test("the classes that would make an element around a picture a stacking context, a two-way pin (the file review's round 17, extra9-1, and the coordinator's decision 4 on it): SHEET_CONTEXT_CLASSES in file-view.ts, the classes dropStackClasses takes off each figure and every element above it, equals the classes every sheet a page of either host loads would make a stacking context, whatever state pseudo-class the rule's subject carries (a transform, a filter, a clip-path or a mask other than none, an opacity under 1, a blend, an isolation, a paint or layout containment, a content-visibility, a fixed or sticky position, a z-index other than auto, a will-change naming one, or an animation whose keyframes set one; container-type none of them), derived by the rule its docstring states (the subject's classes outside :not() and :has(), else the other compounds'; a pseudo-element's rule and a print rule left out), less the classes the other three lists take; each class that the list lacks and each listed class the sheets no longer make one is named, and so is each rule with no class in its subject that would make a stacking context of an element that could hold a control, keyed on nothing but the viewer's own chrome, whose reach no drop of a class undoes; no listed class is one the markdown renderers write before the sanitizer; the derivation's reads are armed by planted rules, one per property, a hover, the keyframes, a subject that names no class, and the classless shapes named as reaching beside the ones that are not, with controls that make no stacking context, and by a class taken off the list and one put on it (a property pin over the derived set against the list; red at 0ab74924c, where the list was absent and the viewer's `.fileview-md > table` rule, a translate, is named as reaching)", () => {
  const listed = listedContextClasses();
  const others = new Set([...listedStackClasses(), ...listedPressThroughClasses(), ...listedDimClasses()]);
  const { classes, reach } = contextClasses(SHEETS);
  assert.ok(classes.size >= 200, "the derivation reads the sheets: " + classes.size + " classes before the other lists are taken out (a derivation that reads nothing is red; a property pin over the derived set's size)");
  const derived = contextKept(classes, others);
  const drift = dimDrift(derived, listed);
  assert.deepEqual(drift.missing, [], "each class a sheet would make a stacking context around a picture that SHEET_CONTEXT_CLASSES lacks, with the rule that does it: add it to the list, in the same change as the rule (a property pin over the derived set against the list)");
  assert.deepEqual(drift.stale, [], "each class SHEET_CONTEXT_CLASSES lists that no sheet makes a stacking context now, or that another list now takes: take it off the list, in the same change (a property pin over the derived set against the list)");
  assert.deepEqual([...listed].filter((c) => others.has(c)), [], "no listed class is one another list already takes (a property pin over the four lists)");
  assert.deepEqual(reach, [], "each rule that would make a stacking context of an element that could hold a picture's control, with no class in its subject, no id, and keyed on nothing but the viewer's own chrome, which reaches every author element of its shape and no drop of a class undoes: take the property off, or key it where a drop reaches (a property pin over the sheets' rules)");
  const RENDERED = new Set<string>(["fv-dead", ...[web("md-config.ts"), web("math.ts")].flatMap((src) => [...src.matchAll(/\nexport const \w+_CLASS = "([\w-]+)";/g)].map((m) => m[1]))]);
  assert.deepEqual([...listed].filter((c) => RENDERED.has(c)), [], "no listed class is one a markdown renderer writes before the sanitizer, which the drop would strip from the viewer's own markup (a property pin over the two sets)");
  const planted = { name: "planted", css: ".plant-tf { transform: rotate(1deg); } .plant-none { transform: none; } .plant-wk { -webkit-transform: scale(2); } .plant-op { opacity: 0.5; } .plant-op1 { opacity: 1; } .plant-var { opacity: var(--x); } .plant-sticky { position: sticky; } .plant-rel { position: relative; } .plant-z0 { z-index: 0; } .plant-zauto { z-index: auto; } .plant-wc { will-change: transform; } .plant-wccolor { will-change: color; } .plant-ct { container-type: inline-size; } .plant-contain { contain: paint; } .plant-csize { contain: size style; } .plant-iso { isolation: isolate; } .plant-blend { mix-blend-mode: multiply; } .plant-mask { mask-image: linear-gradient(black, transparent); } .plant-cv { content-visibility: auto; } .plant-init { transform: initial; } .plant-hover:hover { transform: scale(1.1); } .plant-psd::after { transform: rotate(1deg); } @media print { .plant-print { transform: rotate(1deg); } } @keyframes plant-kf { from { transform: rotate(0deg); } } .plant-anim { animation: plant-kf 1s; } .plant-sub span { filter: blur(1px); } .fileview-md > section { translate: 10px 0; } .fileview-body div { opacity: 0.9; } [data-plant] { filter: blur(1px); } img { transform: rotate(1deg); } button { opacity: 0.5; } #plant-id { transform: rotate(1deg); } .plant-kept aside { transform: rotate(1deg); }" };
  const withPlant = contextClasses([...SHEETS, planted]);
  assert.deepEqual(dimDrift(contextKept(withPlant.classes, others), listed).missing.map((m) => m.split(" ")[0]), ["plant-anim", "plant-blend", "plant-contain", "plant-cv", "plant-hover", "plant-iso", "plant-kept", "plant-mask", "plant-op", "plant-sticky", "plant-sub", "plant-tf", "plant-var", "plant-wc", "plant-wk", "plant-z0"], "a planted sheet's classes are named missing, one per property, the -webkit- name, the hover's, the animation's and a subject that names no class among them, and neither a transform of none or initial, an opacity of 1, a relative position, a z-index of auto, a will-change of color, a container-type, a size and style containment, a pseudo-element's rule nor a print rule is (a property pin over the drift)");
  assert.deepEqual(withPlant.reach, ["planted: .fileview-md > section (translate 10px 0)", "planted: .fileview-body div (opacity 0.9)", "planted: [data-plant] (filter blur(1px))"], "the rules keyed on the viewer's own chrome with a classless subject, and an attribute-keyed one, are named as reaching, and the void img, the button the sanitizer removes, the id-keyed rule and a classless subject under a class a drop can take are not (a property pin over the read)");
  const cut = new Set(listed); cut.delete("romp-lightbox-img");
  assert.deepEqual(dimDrift(derived, cut).missing.map((m) => m.split(" ")[0]), ["romp-lightbox-img"], "a class taken off the list is named missing (a property pin over the drift)");
  assert.deepEqual(dimDrift(derived, new Set([...listed, "plant-never-contexts"])).stale, ["plant-never-contexts"], "a class put on the list that no sheet makes a stacking context is named (a property pin over the drift)");
});

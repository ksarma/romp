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
  assert.match(dressFn, /const words = target !== null && target\.kind === "web" \? figureOpenWebTitle\(targetHost\(target\.href\)\) : FIGURE_OPEN_TITLE;\n\s*if \(b\.title !== words\) \{ b\.title = words; b\.setAttribute\("aria-label", words\); \}/, "the words in the title and the aria-label, keyed on the target's kind: the host and the tab for a picture from the web, the one word set for a file");
  assert.match(VIEW, /\nexport function figureOpenWebTitle\(host: string\): string \{ return "Open the picture in a new tab at " \+ host; \}\n/, "the web words name the host and the new tab");
  assert.match(VIEW, /\nfunction targetHost\(href: string\): string \{\n\s*try \{ return new URL\(href\)\.host; \} catch \{ return href; \}\n\}\n/, "the host alone, never the address with its credentials");
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
  assert.match(titleFn, /const title = \(author \? author \+ "\\n" : ""\) \+ figureWebTitleLine\(shownAddress\(\(target as \{ href: string \}\)\.href\)\);/, "the author's title first, the address line after it on its own line");
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
  assert.match(fig, /const img = bareFigureOf\(t, body\);\n\s*if \(!img \|\| figureLinkOf\(img\)\) return;/, "a figure inside a link whose click is the link's: the one predicate (figureLinkOf over FIGURE_LINK_SET: the links listener's three, and an anchor with an href it leaves to the browser); a dead link and a named anchor are not in the set, and the click stays the figure's (a sentence pin)");
  assert.match(fig, /if \(!img \|\| figureLinkOf\(img\)\) return;[^\n]*\n\s*if \(figureFoldOf\(img\)\) return;[^\n]*\n\s*if \(panelMark\(t\) && !wantsOwnTab\(ev\)\) return;/, "a figure inside a fold's own summary: the fold takes the click, plain or modified, right after a link's yield and before the modifier-keyed yields (the file review's round 14, fresh-1; a sentence pin, whose property file-figure-open-browser.test.ts's fold cases execute)");
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
    assert.match(css, /\n\.fileview-md \.fv-figopen \{ position: relative; z-index: 1; vertical-align: top; margin: 0 6px 0 -28px; top: 6px; padding: 3px; background: var\(--bg\); opacity: 0; \}\n/, name + ": the rest");
    assert.match(css, /\n\.fileview-md \.fv-figopen-left \{ float: left; \}\n\.fileview-md \.fv-figopen-right \{ float: right; margin: 0 -28px 0 6px; \}\n/, name + ": the float twins");
    assert.match(css, /\n\.fileview-md \.fv-figopen-web \{ border-style: dashed; \}\n/, name + ": the web control's dress, the gate's dashed border for a figure from another host (the file review's round 11, ui-1 with extra8-1; a sentence pin on the rule's spelling, and the closed set below holds the property over the parsed rules)");
    assert.match(css, /\n@media screen \{ \.fileview-md :hover \+ \.fv-figopen, \.fileview-md \.fv-figopen:hover, \.fileview-md \.fv-figopen:focus-visible, \.fileview-md \.fv-figopen-web:focus \{ opacity: 1; \} \}\n/, name + ": the reveal, screen only, any focus on the web control among its members (the file review's round 14, ui-1 with extra9-1: after a mouse press the web control held a focus :focus-visible does not match, unpainted on a fine pointer; a sentence pin on the rule's spelling, the closed set below holds the property, and the painted read is file-figure-open-browser.test.ts's script-focus case)");
    assert.match(css, /\n@media screen and \(hover: none\), screen and \(any-pointer: coarse\) \{ \.fileview-md \.fv-figopen \{ opacity: 0\.8; \} \}/, name + ": no hover, or a coarse pointer beside a hovering one, keeps it visible, screen written on both queries (the file review's round 13, extra7-2: `hover` is the primary pointer's, and a touchscreen laptop's hovers; a sentence pin on the at-rule's spelling, the closed set below holds the property)");
    assert.match(css, /\n@media screen and \(hover: none\), screen and \(any-pointer: coarse\) \{ \.fileview-md \.fv-figopen-web \{ opacity: 1; \} \}/, name + ": the web control at rest at full opacity, after the 0.8 rule and of its specificity, so it wins: at 0.8 the picture under the control showed through its background and its dashed line, the dress it shares with the mark (the painted-contrast ask of 2026-09-23: at 0.8 the line read 2.46:1 on a VS Code editor ground of #404040 over the leg's picture, and fell under 3:1 from #282828 over the worst picture; a sentence pin, the painted read is file-figure-open-browser.test.ts's paintedRatio and the composed one theme-parity.test.ts's)");
    assert.match(css, /\n@media screen \{ \.fileview-md \.fv-figopen-web:focus-visible \{ outline-offset: 2px; \} \}/, name + ": the web control's focus ring 2px off its border, so its dashed line shows under a keyboard focus: drawn where the browser draws it, the ring covered the border row and the row inside it, and at 1px off the border row still (the painted-contrast ask of 2026-09-23; a sentence pin on the rule's spelling, the closed set below holds the property, and the painted read is file-figure-open-browser.test.ts's fine-pointer case)");
    assert.match(css, /\n@media screen \{ \.fileview-md \.fv-figopen-web:active \{ transform: none; \} \}/, name + ": the button family's press cue (a scale to 0.96) off on the web control alone: the release that opens the tab comes while it is held, so the pressed state is one a gesture opens the tab from, and under the cue its 1px dashed line spread over two pixel rows, its modal colour at 1.59:1 dark and 1.39:1 light against the control's own ground (the painted-contrast ask of 2026-09-23, the maintainer's ruling; a sentence pin on the rule's spelling, the closed set below holds the property, and the painted read is file-figure-open-browser.test.ts's pressedLegible in its three painted cases)");
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
    // under the outline, 3px, and a margin stands at rest under screen on every pointer, the set's first member, 1px up and down and
    // 7px across the line, measured per axis so the ring covers no neighbouring ink (the margin ruling of 2026-09-24); the executed reads
    // are the leg's worst dash-to-ring read (paintedRatio's mark branch) and its neighbour pin (ringCoversNoNeighbour)
    const mark = cssRules(css).filter((r) => /data-fv-figweb/.test(r.selector));
    assert.deepEqual(mark.filter((r) => !underScreen(r.chain)).map(renderRule), [], name + ": no rule naming the mark outside a screen-only at-rule: a print, where hover is none, would show the at-rest dress (a property pin over the derived population)");
    assert.deepEqual(mark.filter((r) => underScreen(r.chain)).map(renderRule), [
      "@media screen { .fileview-md img[data-fv-figweb] { margin: 1px 7px; } }",
      "@media screen { .fileview-md img[data-fv-figweb]:hover { outline: 1px dashed var(--outbound-line); outline-offset: 1px; box-shadow: 0 0 0 3px var(--bg); } }",
      "@media screen and (hover: none), screen and (any-pointer: coarse) { .fileview-md img[data-fv-figweb] { outline: 1px dashed var(--outbound-line); outline-offset: 1px; box-shadow: 0 0 0 3px var(--bg); } }",
      "@media screen { .fileview-md a.fv-dead:has(.fv-figopen-web), .fileview-md a.fv-dead:has(img[data-fv-figweb]) { opacity: 1; color: color-mix(in srgb, currentColor 70%, transparent); } }",
    ], name + ": the rules naming the mark are exactly the margin at rest on every pointer, the hover rule and the at-rest rule where hover is none or any pointer is coarse, the control's dashed dress as an outline (an outline and not a border: a border on the img widens its box) over a ring of var(--bg) 3px wide, so both sides of every dash and the gaps read the page's own ground whatever stands behind the picture, the margin 1px up and down and 7px across the line so the ring covers no neighbouring ink (the file review's round 14, correctness-2 with extra5-1 and extra5-2: inside a highlight the dark theme's dashes read 2.40:1 against its tint, and a 2px ring left the line's outer side on it; the margin ruling of 2026-09-24: at the ring's width across the line an italic f lost the ink it paints past its own box to the ring), and the dead link holding the dress, whose dimming moves off opacity so the dress inside it paints at the token's ratio (the painted-contrast ask of 2026-09-23; a property pin over the derived population, its count never typed)");
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
    const outlined = onImg.filter((r) => /(?:^|;\s*)outline:/.test(r.body.trim()));   // the outline rules, not the margin that keeps their ring off the neighbours (the file review's round 14, correctness-2)
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
      ".fileview-md .fv-figopen { position: relative; z-index: 1; vertical-align: top; margin: 0 6px 0 -28px; top: 6px; padding: 3px; background: var(--bg); opacity: 0; }",
      ".fileview-md .fv-figopen:hover { background: var(--bg) linear-gradient(var(--accent-wash), var(--accent-wash)); }",
      ".fileview-md .fv-figopen-left { float: left; }", ".fileview-md .fv-figopen-right { float: right; margin: 0 -28px 0 6px; }",
      ".fileview-md .fv-figopen-web { border-style: dashed; }",
      ".fileview-md .fv-figopen-web:not(:hover) { border-color: var(--outbound-line); }",
    ], name + ": the rules naming the control outside a screen-only at-rule, however the sheet writes them, are exactly the rest, the hover background, the float twins, the web dress and its rest colour; any other rule naming the class there is one a print would apply; a property pin over the parsed rules, the set's membership however the sheet writes it" + BOUND + ")");
    assert.deepEqual(control.filter((r) => underScreen(r.chain)).map(renderRule), [
      "@media screen { .fileview-md :hover + .fv-figopen, .fileview-md .fv-figopen:hover, .fileview-md .fv-figopen:focus-visible, .fileview-md .fv-figopen-web:focus { opacity: 1; } }",
      "@media screen and (hover: none), screen and (any-pointer: coarse) { .fileview-md .fv-figopen { opacity: 0.8; } }",
      "@media screen and (hover: none), screen and (any-pointer: coarse) { .fileview-md .fv-figopen-web { opacity: 1; } }",
      "@media screen { .fileview-md .fv-figopen-web:focus-visible { outline-offset: 2px; } }",
      "@media screen { .fileview-md .fv-figopen-web:active { transform: none; } }",
      "@media screen { .fileview-md a.fv-dead:has(.fv-figopen-web), .fileview-md a.fv-dead:has(img[data-fv-figweb]) { opacity: 1; color: color-mix(in srgb, currentColor 70%, transparent); } }",
    ], name + ": the rules under a screen-only at-rule are the reveal (the web control's under any focus among it), the at-rest rule (no hover, or any coarse pointer), the web control's full opacity at rest, its focus ring off its border, its press cue off and the dead link holding the dress, whose selector names the class inside :has() (a property pin over the parsed rules)");
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
 *  pin's title states and does not resolve: a Mouse reached through an element access whose key is computed (not a literal), through
 *  an alias (`const m = page.mouse; m.click(...)`) or through a destructured binding (`const { mouse } = page; mouse.click(...)`),
 *  each an unseen-passing plant below. Null when the text holds no word `mouse` at all: the prefilter is as wide as the read, so
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
test("no call of Playwright's Mouse under ui/webview carries a modifiers key: mouse.click, dblclick, down, up, move and wheel take no modifiers option (playwright-core's Mouse interface) and drop one silently, so a modified click there is the key held around the click (keyboard.down, mouse.click, keyboard.up), as file-figure-open-browser.test.ts's Ctrl-clicks are; a property pin over the tree, the files derived by reading the directory and each module read by the compiler (mouseCalls): every call whose callee is a member of a member named mouse, through parentheses, a non-null assertion, as, satisfies and a type assertion, each member a property access, optional or not, or an element access keyed by a string literal, its arguments read as written; outside the read, bounds this pin states and does not resolve: a Mouse reached through a computed key, an alias or a destructured binding (each an unseen-passing plant in the plant cases below), and an options object bound to a name elsewhere, or spread in, and passed to the call (the file review's round 13, extra6-2: clickPicture's Ctrl form passed the option to mouse.click and dispatched a plain click, green because the plain click opened the same tab; its round 14, tests-1 with extra6-3: the read before the compiler walk saw only an identifier character, .mouse., a name and a paren on one line, and a prefilter skipped a file spelled otherwise)", (t) => {
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
test("the Mouse census's bound, recorded: a Mouse reached through an alias, a destructured binding, or an element access whose key is computed, for mouse or for the method, carries a modifiers key unseen, each plant passing with no call read that carries it, the bound the census pin's title states (the file review's round 14, tests-1 with extra6-3, as ruled: these stay outside the read, named in the title with an unseen-passing plant; bound-recording plants, green at the read before the compiler walk by design, which saw none of them either; a red here means the read now sees the shape and the title names a bound it no longer has; a property pin over synthetic text)", () => {
  const BOUND: Array<[string, string]> = [
    ["an alias", "const m = page.mouse; await m.click(1, 2, " + MODS + ");"],
    ["a destructured binding", "const { mouse } = page; await mouse.click(1, 2, " + MODS + ");"],
    ["a computed key for mouse", "await page[key].click(1, 2, " + MODS + ");"],
    ["a computed key for the method", "await page.mouse[key](1, 2, " + MODS + ");"],
  ];
  assert.deepEqual(BOUND.map(([shape, statement]) => [shape, plantRead(statement)[1]]), BOUND.map(([shape]) => [shape, 0]), "each shape outside the read, [shape, calls read with the key] (a property pin recording the bound)");
});

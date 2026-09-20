// The figure control over the shapes the first review of the link-navigation follow-on (plans/markdown-viewer.md, L3) found
// it wrong on: the source pins beside the Chromium leg (file-view-figure-shapes-browser.test.ts, which lays the shapes out and
// clicks them). Three defects, one rule each: (1) a protocol-relative source (`//host/pic.svg`) reached the model's join
// before the web test, and figurePath reads any `/`-led source as an absolute path of the disk, so the web arm was dead and
// the control opened the viewer on the kernel's /file route at that path (a 404 and a bogus entry on the trail) in place of
// a tab: figureTarget now tests the web address FIRST; (2) a figure inside a link that holds more than the figure (text
// beside it, `[![alt](src) caption](target)`) had its control INSIDE the author's link, because figureAnchor climbs a link
// only when it holds the figure alone, and one click on the button fired the links listener (the link's open) and the
// figure listener (the picture's open), two opens and a phantom entry on the trail: no control goes inside a link
// (linkAbove); and the bare figure's own click yields to an anchor with an href too (a web address of the markdown carries
// no class, so linkOf read none and the plain click opened the tab AND the picture); (3) a figure under 48px on either side
// (a badge, an inline icon) wore a control the sheets' fixed margins laid over its neighbours, transparent, taking the click
// meant for the badge's link or the prose before the icon: a floor (FIGOPEN_MIN_PX) read from the loaded figure. Since the
// file review the control is decided from the figure's CURRENT state by one function (decideFigureControl, the verdict
// figureWantsControl over figureState) at the paint, at the load and the error, and at each change of the figure's OWN
// laid-out box (watchFigureBoxes, one ResizeObserver per open over the figures of the Rendered box; the file review's round 2:
// decided from the width watch's repaint alone, a text-size step, which reflows the 80ch column at a constant body width,
// never re-decided), so a fetching or a failed figure wears none and opens nothing (figureTarget refuses both states), a figure
// the column narrowed under the floor loses its control and one it widened past gets it back (read once, at the load, a figure
// the pane narrowed to 323 by 32 kept a control that hung over it, file-view-figure-floor-browser.test.ts; the other states in
// file-view-figure-state-browser.test.ts); a control removed while it holds the keyboard hands it to the viewer's body first
// (removeFigureControl). (2)'s exclusion reads ANY anchor above the figure (linkAbove), a dead link too.
// Every pin reads the tree's own source, so a rename fails loudly; the leg executes each rule in a browser. Synthetic values
// only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const VIEW = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "file-view.ts"), "utf8");
/** The text from one anchor to the next, both present. */
const between = (src: string, from: string, to: string): string => {
  const a = src.indexOf(from); assert.ok(a >= 0, from + " present");
  const b = src.indexOf(to, a); assert.ok(b > a, to + " present after " + from);
  return src.slice(a, b);
};
/** `lines` stand in `src` in this order (each sought after the one before it: a line that recurs, `return null;`, is read at its place). */
const inOrder = (src: string, lines: string[], what: string): void => {
  let last = -1;
  for (const l of lines) {
    const at = src.indexOf(l, last + 1);
    assert.ok(at > last, what + ": " + l + " in order");
    last = at;
  }
};

test("figureTarget reads the web address before the model's join, so a protocol-relative source is a tab (figurePath would read it as an absolute path of the disk)", () => {
  const fn = between(VIEW, "function figureTarget(img: Element, filePath: string): FigureTarget | null {", "\n}\n");
  inOrder(fn, [
    "const dest = chosenSource(img);",
    "if (dest === null) return null;",
    'if (/^https?:/i.test(dest) || dest.startsWith("//")) return { kind: "web", href: absUrl(dest) };',
    "const p = figurePath(filePath, dest);",
    'if (p !== null) return { kind: "file", path: p };',
    "return null;",
  ], "figureTarget");
  assert.match(fn, /figurePath reads a protocol-relative source \(`\/\/host\/pic\.svg`\) as an\n\s*\/\/ absolute path of the disk/, "the comment says why the order matters");
});

test("the one decision: figureWantsControl reads the figure's state by one rule (figureHasPicture: a control only for a state with a picture to name, loaded or a stand-in; fetching, failed and any later state get none), then the floor, the target and any link above; decideFigureControl adds or removes against the control standing, handing the keyboard to the viewer's body before a removal; the floor is 48px on either side, read from the loaded picture's rendered box (or its own size when not laid out); linkAbove is any anchor; the load, the error and the figures' own ResizeObserver all run the decision, a 0 by 0 report runs none, and the width watch's repaint runs none; figureTarget refuses on the same rule", () => {
  const want = between(VIEW, "function figureWantsControl(img: Element, anchor: Element, filePath: string): boolean {", "function decideFigureControl(");
  inOrder(want, [
    "if (img.closest('[data-act=\"' + GATE_ACT + '\"]')) return false;",
    "const state = figureState(img);",
    "if (!figureHasPicture(state)) return false;",
    "if (figureTooSmall(img)) return false;",
    "if (figureTarget(img, filePath) === null) return false;",
    "return linkAbove(anchor) === null;",
  ], "figureWantsControl");
  const decide = between(VIEW, "function decideFigureControl(img: Element, filePath: string): void {", "function addFigureControls(");
  inOrder(decide, [
    "const anchor = figureAnchor(img);",
    "const standing = figureControlAfter(anchor);",
    "const want = figureWantsControl(img, anchor, filePath);",
    "if (standing) { if (!want) removeFigureControl(standing); return; }",
    "if (!want) return;",
    'const b = el("button", "fileview-btn fileview-icon " + FIGOPEN_CLASS) as HTMLButtonElement;',
    "parent.insertBefore(b, anchor.nextSibling);",
  ], "decideFigureControl: the verdict against the control standing, one place that adds or removes");
  // the removal hands the keyboard on first (the file review's round 2, ui-4): the holder read before the control goes, the
  // viewer body's takeKeyboard (registered per open) called after it, with the ring the holder wore
  const remove = between(VIEW, "function removeFigureControl(control: HTMLElement): void {", "\n}\n");
  inOrder(remove, ["const a = document.activeElement;", "const held = !!a && control.contains(a);", "const ring = held ? ringOf(a) : false;", "control.remove();", "if (take) take(ring);"], "removeFigureControl: the keyboard read before the removal and handed to the viewer's body after it");
  assert.match(VIEW, /\nconst keyboardTakers = new WeakMap<HTMLElement, \(ring\?: boolean\) => void>\(\);\n/, "the per-open register of the body's takeKeyboard");
  assert.match(VIEW, /keyboardTakers\.set\(body, takeKeyboard\);[^\n]*\n\s*closeHooks\.push\(\(\) => \{ keyboardTakers\.delete\(body\); \}\);/, "registered once per open where takeKeyboard is defined, dropped with the viewer");
  assert.equal((VIEW.match(/setAttribute\(FIGOPEN_MARK, ""\)/g) || []).length, 1, "one place mints a control");
  assert.doesNotMatch(VIEW, /function ensureFigureControl|function dropFigureControl/, "the add-only builder and the drop arm are gone: one decision");
  const state = between(VIEW, "function figureState(img: Element): FigureState {", "\n}\n");
  inOrder(state, ['if (typeof i.complete !== "boolean") return "standin";', 'if (!i.complete) return "fetching";', 'return i.naturalWidth > 0 ? "loaded" : "failed";'], "figureState: the browser's own record on the element");
  // the one rule both readers refuse on, a rule over the states and not a list of the two refused: the domain is the four
  // values of FigureState, the allowance names the two with a picture to name, and any value outside it (a state the type gains
  // later) falls on the refusing side with no edit to either reader
  assert.match(VIEW, /\ntype FigureState = "standin" \| "fetching" \| "loaded" \| "failed";\n/, "the domain: four states");
  const rule = between(VIEW, "function figureHasPicture(state: FigureState): boolean {", "\n}\n");
  assert.match(rule, /\n\s*return state === "loaded" \|\| state === "standin";$/, "the allowance: loaded (the browser answered with a picture) or a stand-in (no browser to ask); every other value refused");
  assert.doesNotMatch(VIEW, /state === "fetching" \|\| state === "failed"/, "no reader lists the refused states");
  assert.match(VIEW, /\nconst FIGOPEN_MIN_PX = 48;\n/, "the floor: the control's 22px box, its 6px inset and as much figure again");
  const small = between(VIEW, "function figureTooSmall(img: Element): boolean {", "\n}\n");
  assert.match(small, /const b = figureBox\(img\);\n\s*return b !== null && \(b\.w < FIGOPEN_MIN_PX \|\| b\.h < FIGOPEN_MIN_PX\);/, "under the floor on EITHER side (a badge is wide and short)");
  const box = between(VIEW, "function figureBox(img: Element): { w: number; h: number } | null {", "\n}\n");
  assert.match(box, /if \(figureState\(img\) !== "loaded"\) return null;/, "a loaded figure alone has a box to measure: the fetching and failed verdicts are figureWantsControl's, a stand-in has no picture to ask");
  assert.match(box, /const r = typeof i\.getBoundingClientRect === "function" \? i\.getBoundingClientRect\(\) : null;\n\s*return r && r\.width > 0 && r\.height > 0 \? \{ w: r\.width, h: r\.height \} : \{ w: i\.naturalWidth, h: i\.naturalHeight \};/,
    "the rendered box when laid out (an author's width attribute counts), else the picture's own size (a detached box)");
  const above = between(VIEW, "function linkAbove(anchor: Element): Element | null {", "\n}\n");
  assert.match(above, /const p = anchor\.parentElement;\n\s*return p \? p\.closest\('a, \[data-act="openpath"\]'\) : null;/,
    "ANY anchor above the anchor (a link holding the figure alone IS the anchor and is not read): with an href or without one (a dead link, a named target), or a path link whose href mark time took off");
  // the load and the error re-run the decision: one capture-phase pair per open
  const arm = between(VIEW, "function armFigureControls(body: HTMLElement, filePath: string): () => void {", "\n}\n");
  assert.match(arm, /const decide = \(e: Event\): void => \{ const img = figureOf\(e\); if \(img && figureState\(img\) !== "standin"\) decideFigureControl\(img, filePath\); \};/, "the events' road into the decision, for an element carrying the browser's record (a stand-in stays as the paint decided it)");
  assert.match(arm, /body\.addEventListener\("load", decide, true\);\n\s*body\.addEventListener\("error", decide, true\);/, "the load and the error, both capture (neither bubbles)");
  // each figure's OWN box re-runs it (the file review's round 2): one ResizeObserver per open over the figures of the Rendered
  // box, re-armed at each text paint (never at a reflow, whose figures are the same nodes), dropped with the viewer; the
  // observer hears every reflow of the figure, the body's width and a text-size step alike, so no road calls the decision
  // itself; absent ResizeObserver (a stand-in outside a browser) nothing is armed and the paint's decision stands
  const watch = between(VIEW, "function watchFigureBoxes(body: HTMLElement, filePath: string, onRendered: (cb: (why?: FileViewRenderWhy) => void) => void): (() => void) | null {", "\n}\n");
  inOrder(watch, [
    'if (typeof ResizeObserver !== "function") return null;',
    "const ro = new ResizeObserver((entries) => {",
    "if (e.contentRect.width === 0 || e.contentRect.height === 0) continue;",
    'if (img.isConnected && figureState(img) !== "standin") decideFigureControl(img, filePath);',
    'body.querySelectorAll(".fileview-md img").forEach((img) => { ro.observe(img); });',
    'onRendered((why) => { if (why !== "reflow") rearm(); });',
    "rearm();",
    "return () => { ro.disconnect(); };",
  ], "watchFigureBoxes: the guard, the observer over the figures, the 0 by 0 report skipped before the decision, the re-arm at each paint, the drop");
  // a 0 by 0 report is a box not laid out (the viewer hidden, a gated placeholder's img), not a figure's size: decided over it,
  // figureBox fell back to the natural size and a hidden figure under the floor at its real width gained a control while hidden and
  // lost it at the show; file-view-figure-floor-browser.test.ts drives the hide and the show
  assert.match(watch, /A 0 by 0 report is a box that is not laid out, not a figure's size/, "the comment says what the report is");
  assert.match(VIEW, /const figureWatch = watchFigureBoxes\(body, path, ctx\.onRendered\);\n\s*if \(figureWatch\) ctx\.onClose\(figureWatch\);/, "armed once per open beside the load and error pair, dropped through the close hooks");
  const paint = between(VIEW, "function addFigureControls(box: HTMLElement, filePath: string): void {", "\n}\n");
  assert.match(paint, /box\.querySelectorAll\("img"\)\.forEach\(\(img\) => \{ decideFigureControl\(img, filePath\); \}\);/, "the paint runs the same decision (a stand-in's only one)");
  // the width watch's repaint decides no figure: a call there ran on one road of two (the file review's round 2), and the
  // figures' observer hears that reflow as it hears the text-size step's
  const repaint = between(VIEW, "const repaint = () => {", "\n  };\n");
  inOrder(repaint, ["if (seenWidth === paintedWidth) return;", "paintedWidth = seenWidth;", "if (!textShowing()) return;", "if (unmeasurable()) return;", "landRemembered(); landTarget();", "retakeAfterHide();"], "the repaint as it was before the figures had a decision of their own");
  assert.doesNotMatch(repaint, /igureControl/, "no figure decision in the width watch's repaint");
  assert.doesNotMatch(VIEW, /refigureControls/, "the width-only road is gone");
  // the target waits for the browser's answer too, and refuses a failed figure as the control does (the file review's round 2,
  // regression-3 with extra5-4): a plain click on a fetching or a failed figure opens nothing, and the two readers agree
  const target = between(VIEW, "function figureTarget(img: Element, filePath: string): FigureTarget | null {", "\n}\n");
  inOrder(target, ["const state = figureState(img);", "if (!figureHasPicture(state)) return null;", "const dest = chosenSource(img);"], "figureTarget: a target only for a state with a picture to name, read before the candidate (no candidate before the browser has picked, nothing to open after a failure, nothing for a state the type gains later)");
});

test("the sheets' figure-control comment names the builder that exists (decideFigureControl), not the one the one decision replaced", () => {
  const web = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
  for (const name of ["styles.css", "feed.css"]) {
    const css = web(name);
    assert.doesNotMatch(css, /ensureFigureControl|dropFigureControl/, name + ": no name of the retired builder or drop arm");
    assert.match(css, /file-view\.ts\n\s+decideFigureControl\): a glyph button of the bar's family/, name + ": the comment names decideFigureControl");
  }
});

test("the figure listener: the bare figure's plain click yields to an anchor with an href as it yields to the links listener's links; the control's branch and the pinned guards stand as they were", () => {
  const listeners = VIEW.split('body.addEventListener("click", (ev) => {');
  assert.equal(listeners.length, 3, "two click listeners on the viewer's body: the links' and the figures'");
  const fig = listeners[2].split("\n  });\n")[0];
  inOrder(fig, [
    "const control = figureControlOf(t, body);",
    "const img = bareFigureOf(t, body);",
    "if (!img || linkOf(t)) return;",
    'if (img.closest("a[href]")) return;',
    "if (panelMark(t) && !wantsOwnTab(ev)) return;",
    "if (asideOpen && !wantsOwnTab(ev)) return;",
    "if (selectionOpenIn(box)) return;",
    "openFigure(img, ev);",
  ], "the figure listener");
  assert.doesNotMatch(fig, /ev\.stopPropagation\(\)/, "a plain click is never stopped here");
  // the links listener is as it was (file-view-links.test.ts pins its text): the fix is in the DOM (no control inside a link) and in the figure listener's yield
  const links = listeners[1].split("\n  });\n")[0];
  assert.doesNotMatch(links, /figure/, "the links' listener knows nothing of figures");
});

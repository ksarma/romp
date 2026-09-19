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
// meant for the badge's link or the prose before the icon: a floor (FIGOPEN_MIN_PX), read at the picture's load (the paint
// adds the control before the size is known; the load, armFigureControls, removes one on a figure under the floor) and again
// at each change of the body's width (refigureControls, from the width watch's repaint: a figure the column narrowed under
// the floor loses its control and one it widened past gets it back; read once, at the load, a figure the pane narrowed to
// 323 by 32 kept a control that hung over it, file-view-figure-floor-browser.test.ts).
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

test("ensureFigureControl: a figure under the floor gets no control and loses one added before its load; a figure inside a link the climb did not leave gets none; the floor is 48px on either side, read from the loaded picture's rendered box (or its own size when not laid out), at its load and again from the width watch's repaint at each change of the body's width", () => {
  const fn = between(VIEW, "function ensureFigureControl(img: Element, filePath: string): void {", "function addFigureControls(");
  inOrder(fn, [
    "if (img.closest('[data-act=\"' + GATE_ACT + '\"]')) return;",
    "if (figureTooSmall(img)) { dropFigureControl(img); return; }",
    "const anchor = figureAnchor(img);",
    "if (figureControlAfter(anchor)) return;",
    "if (figureTarget(img, filePath) === null) return;",
    "if (linkAbove(anchor)) return;",
    'const b = el("button", "fileview-btn fileview-icon " + FIGOPEN_CLASS) as HTMLButtonElement;',
    "parent.insertBefore(b, anchor.nextSibling);",
  ], "ensureFigureControl");
  assert.match(VIEW, /\nconst FIGOPEN_MIN_PX = 48;\n/, "the floor: the control's 22px box, its 6px inset and as much figure again");
  const small = between(VIEW, "function figureTooSmall(img: Element): boolean {", "\n}\n");
  assert.match(small, /const b = figureBox\(img\);\n\s*return b !== null && \(b\.w < FIGOPEN_MIN_PX \|\| b\.h < FIGOPEN_MIN_PX\);/, "under the floor on EITHER side (a badge is wide and short)");
  const box = between(VIEW, "function figureBox(img: Element): { w: number; h: number } | null {", "\n}\n");
  assert.match(box, /if \(typeof i\.complete !== "boolean" \|\| !i\.complete \|\| !\(i\.naturalWidth > 0\) \|\| typeof i\.getBoundingClientRect !== "function"\) return null;/,
    "unknown until the picture has loaded (the paint runs before the load; a failed picture has no size; a stand-in outside a browser has none)");
  assert.match(box, /const r = i\.getBoundingClientRect\(\);\n\s*return r\.width > 0 && r\.height > 0 \? \{ w: r\.width, h: r\.height \} : \{ w: i\.naturalWidth, h: i\.naturalHeight \};/,
    "the rendered box when laid out (an author's width attribute counts), else the picture's own size (a detached box at paint)");
  const drop = between(VIEW, "function dropFigureControl(img: Element): void {", "\n}\n");
  assert.match(drop, /const c = figureControlAfter\(figureAnchor\(img\)\);\n\s*if \(c\) c\.remove\(\);/, "the control after the anchor, found by its mark, removed");
  const above = between(VIEW, "function linkAbove(anchor: Element): Element | null {", "\n}\n");
  assert.match(above, /const p = anchor\.parentElement;\n\s*return p \? p\.closest\('a\[href\], \[data-act="openpath"\]'\) : null;/,
    "a link ABOVE the anchor (a link holding the figure alone IS the anchor and is not read): an anchor with an href, or a path link whose href mark time took off");
  // the load re-reads the figure: the one listener armed per open calls the same builder, which now measures
  const arm = between(VIEW, "function armFigureControls(body: HTMLElement, filePath: string): () => void {", "\n}\n");
  assert.match(arm, /const img = figureOf\(e\); if \(img\) ensureFigureControl\(img, filePath\);/, "the load's road into the builder, where the floor is read");
  // the width's report re-reads every figure of the box through the same builder, from the repaint the width watch folds into a frame
  const refigure = between(VIEW, "function refigureControls(body: HTMLElement, filePath: string): void {", "\n}\n");
  assert.match(refigure, /body\.querySelectorAll\("\.fileview-md img"\)\.forEach\(\(img\) => \{ ensureFigureControl\(img, filePath\); \}\);/, "every figure of the Rendered box, the same builder");
  const repaint = between(VIEW, "const repaint = () => {", "\n  };\n");
  inOrder(repaint, ["if (seenWidth === paintedWidth) return;", "paintedWidth = seenWidth;", "if (!textShowing()) return;", "if (unmeasurable()) return;", "landRemembered(); landTarget();", "retakeAfterHide();", "refigureControls(body, path);"], "the repaint: the re-read once the width moved, over a text view with a box, after the seat (the control is a zero-width inline box and moves no layout)");
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

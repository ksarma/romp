// A figure's open reads the candidate the browser chose (plans/markdown-viewer.md, "Follow-on: Link navigation", L3 and L6;
// the review's round 2): the source pins beside the browser leg (file-view-figure-chosen-browser.test.ts, which drives a
// <picture> figure, a srcset figure and a remote <picture> through the real viewer in Chromium). Before the fix figureTarget
// read pictureDest alone (data-fv-src, else src), the img's own src as written, and never `currentSrc`, so for a `<picture>`
// whose `<source>` the browser took, or an img whose srcset candidate it took, the control and the plain click opened the
// fallback src: a local file the paint never requested (L3's "the picture opened is the one shown" did not hold) or, for a
// remote figure, a tab at an address the page never fetched (L6's "as the report's paint did" did not hold). The mapping from
// currentSrc to the authored candidate already stood in failedSource, the failed figure's label reader; it is now one reader,
// chosenSource, under both names. Every pin reads the tree's own source, so a rename here fails loudly. Synthetic values only.
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
/** `lines` stand in `src` in this order (each sought after the one before it). */
const inOrder = (src: string, lines: string[], what: string): void => {
  let last = -1;
  for (const l of lines) {
    const at = src.indexOf(l, last + 1);
    assert.ok(at > last, what + ": " + l + " in order");
    last = at;
  }
};
/** A doc comment's text with its line wraps joined, so a sentence wrapped across lines is read as one. */
const flat = (s: string): string => s.replace(/\n \*\s+/g, " ").replace(/\s+/g, " ");

test("figureTarget reads the candidate the browser chose (chosenSource), first in its body, and never the src alone (pictureDest) or currentSrc a second time: the web arm and the model's join then read that candidate", () => {
  const fn = between(VIEW, "function figureTarget(img: Element, filePath: string): FigureTarget | null {", "\n}\n");
  inOrder(fn, [
    "const dest = chosenSource(img);",
    "if (dest === null) return null;",
    'if (/^https?:/i.test(dest) || dest.startsWith("//")) return { kind: "web", href: absUrl(dest), src: dest };',
    "const p = figurePath(filePath, dest);",
    'if (p !== null) return { kind: "file", path: p };',
    "return null;",
  ], "figureTarget");
  assert.doesNotMatch(fn, /pictureDest\(/, "the src alone is no reading of the target: a <picture> or a srcset figure would open its fallback, a file the paint never requested");
  assert.doesNotMatch(fn, /\.currentSrc\b/, "the browser's answer is read in one place, chosenSource, never here");
});

test("chosenSource is the one reader of the browser's answer: currentSrc matched against the srcset carriers (the picture's sources, then the img) and named by the authored candidate rewriteFigureSrcs kept (FV_SRCSET); the img's own src, or no currentSrc, by pictureDest's rule; failedSource is that reader under the label's name, and the label's text still reads it there", () => {
  const cs = between(VIEW, "function chosenSource(img: Element): string | null {", "\n}\n");
  inOrder(cs, [
    'const cur = (img as HTMLImageElement).currentSrc || "";',
    'if (!cur || cur === absUrl(img.getAttribute("src") || "")) return pictureDest(img);',
    'const picture = img.closest("picture");',
    'const carriers: Element[] = picture ? [...Array.from(picture.querySelectorAll("source")), img] : [img];',
    'const now = parseSrcset(c.getAttribute("srcset") || "");',
    'const was = c.hasAttribute(FV_SRCSET) ? parseSrcset(c.getAttribute(FV_SRCSET) || "") : now;',
    "for (let i = 0; i < now.length; i++) if (absUrl(now[i].url) === cur) return (was[i] ?? now[i]).url;",
    "return pictureDest(img);",
  ], "chosenSource");
  assert.doesNotMatch(cs, /fetch\(|new Image\(|\.src = /, "no second request: the answer is read off the element");
  assert.match(VIEW, /\nfunction failedSource\(img: Element\): string \| null \{\n  const chosen = chosenSource\(img\);\n  if \(chosen \|\| img\.hasAttribute\("src"\)\) return chosen;\n  return img\.getAttribute\(HEAL_RECORD\) \|\| chosen;\n\}\n/, "failedSource delegates: the failed figure's label names the candidate the open would take, and only when that names nothing and the img has no src, the chat page's heal record of the address it parked (the file review's round 15, fresh-1; a sentence pin on the spelling, and file-view-figure-error.test.ts's parked cells hold the property through the listener)");
  assert.match(VIEW, /const src = failedSource\(img\);\n\s*return FIGURE_FAILED \+ " " \+ \(src \? shownSource\(src\) : FIGURE_NO_SOURCE\)/, "the label's text reads it under that name");
  assert.equal((VIEW.match(/\bchosenSource\(img\)/g) || []).length, 2, "two callers and no third: the target (figureTarget) and the label (through failedSource)");
  assert.equal((VIEW.match(/HTMLImageElement\)\.currentSrc\b/g) || []).length, 1, "the property is read in chosenSource alone (the doc's mention of it is prose)");
  assert.equal((VIEW.match(/^[^/*\n]*\.currentSrc\b/gm) || []).length, 1, "no code line outside it reads currentSrc");
});

test("the reader's doc names what it makes true of the records (L3: the picture opened is the one shown; L6: the open's request is the paint's) and the paint-time reading (the control's existence from the src, its target read again at the click)", () => {
  const doc = flat(between(VIEW, "/** The candidate the browser chose for a figure, as the author wrote it", "function chosenSource("));
  assert.ok(doc.includes("so the picture opened is the one shown and its request is the one the paint made"), "L3 and L6 at the reader: " + doc);
  assert.ok(doc.includes("in a browser a figure the browser has not answered for is fetching, figureState, and figureTarget names nothing for it until its load or its error"), "the fetching figure's reading is stated: no control and no open before the browser has picked");
  const head = between(VIEW, "// What the control opens (figureTarget): the candidate the browser chose for the figure", "type FigureTarget =").replace(/\n\/\/ ?/g, " ");
  assert.ok(head.includes("so a `<picture>` or a srcset figure opens the picture shown and not the fallback src the browser never asked for"), "the section header says what the reader is for");
});

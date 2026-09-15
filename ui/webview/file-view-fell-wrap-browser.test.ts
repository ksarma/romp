// The failure dress breaks a long unbroken token inside its box, in headless Chromium over the REAL viewer
// (plans/markdown-viewer.md Slice 7, item 1, and its review's round 4). renderFellLine puts the error's message into a bare
// `div.fileview-err` line above the Raw rows, and that message is not the viewer's to shape: a library quoting an attribute
// value or a URL can put a token of a hundred characters with no break opportunity in it. The dress's rule had no wrapping
// declaration (only `.fileview-err-hint` carried `word-break: break-all`), so at phone width the token ran past the line's
// box, the body's scroll width grew by the token's overflow and the pane gained a horizontal scrollbar under the sentence,
// the rows under it wrapping as before. Now the rule carries `overflow-wrap: anywhere` in both sheets
// (fileview-parity.test.ts holds the head byte-equal): the token breaks at the box's edge and the body's scroll width is
// its client width. The same dress dresses the fetch chain's pane (a 404 naming a long path overflowed by the same
// mechanism on main 462ad3ccf), the note bar and the empty-file line; the declaration reaches them all, and every scene
// here is the RENDER_FELL line, the new wearer whose content the slice does not control. Each surface under its own sheet
// (the chat modal: styles.css; the feed modal: feed.css; the Files pane: styles.css with files-pane.css), since the
// declaration must stand in both sheets to reach the feed page. The render is made to throw at the swap, one of item 1's
// four sources: Element.prototype's replaceChildren, patched before the open (openViewer's `before`, since the viewer's
// body does not exist until the open), throws the message under test when the body is handed a `.fileview-md` node, so
// the first paint's catch paints the line; the fallback rows' own swap passes through. The wait is for the line itself
// (openViewer's `waitFor`), never a timer. Red over a git archive of 9c4fceac5 (the rule without the declaration: the
// computed overflow-wrap "normal", the line and the body 470 px wider than their boxes at 380 px in the chat and feed
// modals and 449 px in the Files pane, whose body is the pane's full width; with the declaration all three read 0 and the
// line grows from 90 to 125 px in the modal as the token takes more lines); the control scene with ordinary words fits on
// both trees. Skips LOUDLY without a playwright browser (CI installs none), as
// the other legs do. Synthetic values only: an invented report, /repo/notes-api paths, the placeholder sid, an invented
// failure message.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { inBrowser, openViewer, REPORT, UI } from "./real-viewer-leg";
import type { Mode } from "./real-viewer-leg";

/** The line's exported sentence, read off the viewer's source (contract C5), so the leg follows the constant. */
const RENDER_FELL = (/^export const RENDER_FELL = "([^"]+)";$/m.exec(fs.readFileSync(path.join(UI, "file-view.ts"), "utf8")) || [])[1];

const F = "```";
const DOC = ["# Report", "", "An intro paragraph before the fence.", "", F + "python", "def f(x):", "    return x + 1", F, "", "A paragraph after the fence.", ""].join("\n");
/** A message of ordinary words: the control, which fits at every width with or without the declaration. */
const WORDS = "synthetic render failure with ordinary words that wrap at any width of the pane";
/** A 120-character token with no break opportunity (a quoted attribute value, say), wider than a 380 px surface. */
const TOKEN = "a".repeat(40) + "b".repeat(40) + "c".repeat(40);

/** Make the Rendered swap throw `why`: the body's replaceChildren, handed a `.fileview-md` node, throws; every other swap (the
 *  fallback rows' among them) passes through. Installed on the prototype before the open, since the body does not exist yet. */
const throwAtSwap = (why: string) => (page: any): Promise<void> => page.evaluate((w0: string) => {
  const w = window as any;
  const orig = Element.prototype.replaceChildren;
  w.__threw = 0;
  Element.prototype.replaceChildren = function (this: Element, ...nodes: (Node | string)[]): void {
    if (this.classList.contains("fileview-body") && nodes.some((n) => n instanceof Element && n.classList.contains("fileview-md"))) { w.__threw++; throw new Error(w0); }
    return orig.apply(this, nodes);
  };
}, why);

type Seen = { first: string | null; line: string; threw: number; bodyOverflowX: number; lineOverflowX: number; wrap: string; rows: number; lineH: number };
/** What the page shows: the body's first child, the line's text, how many swaps threw, the body's and the line's horizontal
 *  overflow (scroll width past client width), the line's computed overflow-wrap, the Raw rows under it and the line's height. */
const seen = (page: any): Promise<Seen> => page.evaluate(() => {
  const w = window as any;
  const body = document.querySelector(".fileview-body") as HTMLElement;
  const line = body.querySelector(":scope > .fileview-err") as HTMLElement | null;
  return {
    first: body.firstElementChild ? body.firstElementChild.className : null,
    line: line ? line.textContent || "" : "",
    threw: w.__threw,
    bodyOverflowX: body.scrollWidth - body.clientWidth,
    lineOverflowX: line ? line.scrollWidth - line.clientWidth : -1,
    wrap: line ? getComputedStyle(line).overflowWrap : "",
    rows: body.querySelectorAll("code.hljs .fv-cl").length,
    lineH: line ? Math.round(line.getBoundingClientRect().height) : -1,
  };
});

/** The surface at 380 by 600, the report open in it, the swap made to throw `why`: the RENDER_FELL line stands over the rows. */
async function scene(browser: any, mode: Mode, why: string): Promise<Seen> {
  const { page, errors } = await openViewer(browser, mode, 380, 600, { docs: { [REPORT]: DOC }, before: throwAtSwap(why), waitFor: ".fileview-body > .fileview-err" });
  const s = await seen(page);
  await page.close();
  assert.deepEqual(errors, [], mode + ": no uncaught page error");
  assert.ok(s.threw >= 1, mode + ": the swap threw (the scene's premise)");
  assert.equal(s.first, "fileview-err", mode + ": the RENDER_FELL line is the body's first child");
  assert.equal(s.line, RENDER_FELL + " (" + why + ").", mode + ": the line carries the sentence and the message");
  assert.ok(s.rows > 0, mode + ": the file's text as Raw rows under it");
  return s;
}

test("in a browser at 380 px: a render failure whose message is one 120-character token breaks inside the line's box on the chat modal, the feed modal and the Files pane (overflow-wrap: anywhere reaches the dress from each surface's sheet), so the body's scroll width is its client width; ordinary words fit as before", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const words = await scene(browser, "chat", WORDS);
    assert.equal(words.lineOverflowX, 0, "the control: ordinary words fit in the line's box (on both trees)");
    assert.equal(words.bodyOverflowX, 0, "the control: the body's scroll width is its client width");
    for (const mode of ["chat", "feed", "pane"] as Mode[]) {
      const s = await scene(browser, mode, TOKEN);
      assert.equal(s.wrap, "anywhere", mode + ": the dress's overflow-wrap reaches the line from this surface's sheet (before: normal)");
      assert.equal(s.lineOverflowX, 0, mode + ": the token breaks inside the line's box (before: the token's width past the box, 470 px in the modals and 449 in the pane at 380)");
      assert.equal(s.bodyOverflowX, 0, mode + ": the body's scroll width is its client width: no horizontal scrollbar under the sentence");
      if (mode === "chat") assert.ok(s.lineH > words.lineH, "chat: the token line stands taller than the words line (it wrapped onto more lines rather than being clipped): " + s.lineH + " vs " + words.lineH);
    }
  });
});

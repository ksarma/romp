// Copy on a fence hands the clipboard the fence's text as the NOTE holds it, in headless Chromium over the real viewer (Slice 3
// of plans/markdown-viewer.md; the slice's review, round 1). mdBlock captured the code element's textContent for Copy, and that
// text is marked's: the lexer turned every leading run of tabs into four spaces a tab before it cut the fence, so a Makefile
// recipe copied from the rendered note pasted back space-indented (make: "missing separator"), a tab-indented Python fence too,
// while the Raw view of the same note showed the tabs. The fence pass now takes Copy's text from fence-source.ts, which reads
// the fence's lines back out of the note. Measured on the Files pane (styles.css and files-pane.css) and the feed (feed.css):
// the clipboard write is intercepted and the three fences' copies compared with the note's own bytes; the rendered text keeps
// marked's spaces (the display is untouched, and the sheet's tab-size measures them the same). Synthetic note, the harness's
// paths and sid; skips loudly without a browser, as the other legs do.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, REPORT, type Mode } from "./real-viewer-leg";

const F = "```";
const NOTE = ["# Build notes", "", "The recipe below is tab-indented, as make requires.", "",
  F + "makefile", "all:", "\tgo build ./...", "\t\techo done", F, "",
  "- item one holds a fence", "", "  " + F + "python", "  \treturn 1", "  " + F, "", "- item two is plain prose", "",
  F, "a\tb\tc", "x\ty", F, "",
  "Tail paragraph.", ""].join("\n");
/** What each fence's Copy must hand the clipboard: the note's bytes, in the renderer's shape (one trailing newline). */
const EXPECTED = ["all:\n\tgo build ./...\n\t\techo done\n", "\treturn 1\n", "a\tb\tc\nx\ty\n"];
/** What the rendered text reads: marked's four spaces for a leading tab (the display is not what changed). */
const RENDERED = ["all:\n    go build ./...\n        echo done\n", "    return 1\n", "a\tb\tc\nx\ty\n"];

for (const mode of ["pane", "feed"] as Mode[]) {
  test(`in a browser, the real viewer, ${mode}: Copy on a fence copies the note's tabs, not marked's spaces; the rendered text keeps the spaces`, { timeout: 90000 }, async (t) => {
    await inBrowser(t, async (browser) => {
      const { page, errors } = await openViewer(browser, mode, 1000, 800, { docs: { [REPORT]: NOTE } });
      const out = await page.evaluate(async () => {
        const w = window as any;
        w.__copied = [];
        Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText: (s: string) => { w.__copied.push(s); return Promise.resolve(); } } });
        const pres = Array.from(document.querySelectorAll(".fileview-md pre")) as HTMLElement[];
        const texts = pres.map((p) => { const code = p.querySelector("code") as HTMLElement; return Array.from(code.querySelectorAll(":scope > .cl")).map((r) => r.textContent).join("\n") + "\n"; });
        for (const p of pres) (p.querySelector(":scope > .code-copy") as HTMLElement).click();
        await new Promise((r) => requestAnimationFrame(() => r(null)));
        return { texts, copied: w.__copied as string[] };
      });
      assert.deepEqual(errors, [], mode + ": no script error");
      assert.equal(out.copied.length, 3, mode + ": three fences, three copies");
      assert.deepEqual(out.texts, RENDERED, mode + ": the rendered rows read marked's text, spaces for the leading tabs");
      assert.deepEqual(out.copied, EXPECTED, mode + ": Copy hands the clipboard the note's bytes (before the fix: the rendered text, spaces for tabs)");
      await page.close();
    });
  });
}

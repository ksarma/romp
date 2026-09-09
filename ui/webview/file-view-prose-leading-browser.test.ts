// The note's prose leading, in headless Chromium over the REAL viewer (Slice 3 of plans/markdown-viewer.md, "a document
// type scale"; the slice's review, round 2). `.fileview-md` set the face and the size and no line-height, so a paragraph
// took each page's body value: styles.css's 1.6 on the Files pane and in the chat modal, feed.css's 1.5 on the feed. The
// same note was set 23.92px a line on two surfaces and 22.425 on the third at the 13px default (27.51 against 25.79 at
// 115 percent): a paragraph 6 percent taller, a hundred of them 450px, depending on where the note was opened from. The
// root now declares 1.5 (GitHub's) in both sheets, byte-equal (fileview-parity.test.ts holds the rule). Measured here on
// the three surfaces at 900px and the pane at 380, at 100 percent and after one A+ press: a paragraph's computed
// line-height is 1.5 times its font size, its box is that times its line count, and the same paragraph wraps to the same
// lines and stands the same height on the three surfaces at 900. A node test pins the declaration in both sheets, so the
// reason is in the file the sheets are read from. Skips loudly without a browser. Synthetic values only: the harness's
// report and paths, the placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { inBrowser, openViewer, frames, REPORT, LONG, UI, type Mode } from "./real-viewer-leg";

type Cell = { scale: string; fontSize: number; lineHeight: number; rootLineHeight: number; bodyLineHeight: number; height: number; lines: number; width: number };
/** The fifth paragraph of the report: its font size and line-height as computed, its box, and the lines it wraps to. */
function measure(): Cell {
  const cs = (e: Element) => getComputedStyle(e);
  const root = document.querySelector(".fileview-md") as HTMLElement;
  const p = root.querySelectorAll("p")[4] as HTMLElement;
  const r = p.getBoundingClientRect();
  const rng = document.createRange(); rng.selectNodeContents(p);
  const tops = new Set(Array.from(rng.getClientRects()).map((x) => Math.round(x.top)));
  return { scale: cs(root).getPropertyValue("--fv-scale").trim() || "1", fontSize: parseFloat(cs(p).fontSize), lineHeight: parseFloat(cs(p).lineHeight),
    rootLineHeight: parseFloat(cs(root).lineHeight), bodyLineHeight: parseFloat(cs(document.body).lineHeight), height: r.height, lines: tops.size, width: r.width };
}
const stepUp = async (page: any) => {
  await page.click('button[aria-label="Larger text"]');
  await page.waitForFunction(() => getComputedStyle(document.querySelector(".fileview-md")!).getPropertyValue("--fv-scale").trim() === "1.15", null, { timeout: 5000 });
  await frames(page, 2);
};
const near = (a: number, b: number, what: string, tol: number) => assert.ok(Math.abs(a - b) <= tol, `${what}: ${a} vs ${b}`);

function checkLeading(m: Cell, at: string) {
  near(m.lineHeight / m.fontSize, 1.5, at + ": a prose line is 1.5 times the prose size (before: the body's 1.6 on the pane and the chat)", 0.002);
  assert.equal(m.rootLineHeight, m.lineHeight, at + ": the paragraph's leading is the root's own declaration, not an inherited value");
  assert.ok(m.lines >= 2, at + `: the paragraph wraps (${m.lines} lines at ${m.width}px), so its box measures the leading`);
  near(m.height / m.lines, m.lineHeight, at + ": each of its lines is the computed line-height", 0.1);
}

test("in a browser, the real viewer: a paragraph's leading is 1.5 times the prose size on the pane, the chat and the feed, at 100 and 115 percent, and the same paragraph is the same height on the three (before: 23.92px a line on the pane and the chat against 22.425 on the feed)", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const at900: Record<string, Cell[]> = {};
    for (const [mode, width] of [["pane", 900], ["chat", 900], ["feed", 900], ["pane", 380]] as [Mode, number][]) {
      const cell = `${mode} ${width}px`;
      const { page, errors } = await openViewer(browser, mode, width, 700, { docs: { [REPORT]: LONG } });
      const a = await page.evaluate(measure);
      assert.equal(a.scale, "1", cell + ": the scene opens at 100 percent");
      checkLeading(a, cell + " at 100 percent");
      await stepUp(page);
      const b = await page.evaluate(measure);
      assert.equal(b.scale, "1.15", cell + ": one A+ press");
      checkLeading(b, cell + " at 115 percent");
      assert.ok(b.lineHeight > a.lineHeight, cell + ": the leading scales with the text (" + a.lineHeight + " to " + b.lineHeight + ")");
      assert.deepEqual(errors, [], cell + ": no script error");
      if (width === 900) at900[mode] = [a, b];
      await page.close();
    }
    // the three surfaces at the same width: the pane's and the chat's body is 1.6 and the feed's 1.5 (the two bodies' own
    // rules), and the note is the same height on all three once the root declares its own
    for (const [i, pct] of [[0, "100"], [1, "115"]] as [number, string][]) {
      const [pane, chat, feed] = [at900.pane[i], at900.chat[i], at900.feed[i]];
      assert.equal(pane.bodyLineHeight, chat.bodyLineHeight, "the pane and the chat share styles.css's body");
      assert.notEqual(pane.bodyLineHeight, feed.bodyLineHeight, "the feed's body sets its own line-height (the premise: inherited, the note differed by surface)");
      assert.equal(pane.lines, chat.lines, `at ${pct} percent the paragraph wraps to the same lines on the pane and the chat (${pane.lines}, ${chat.lines})`);
      assert.equal(pane.lines, feed.lines, `...and on the feed (${feed.lines})`);
      near(pane.height, feed.height, `at ${pct} percent the paragraph is the same height on the pane and the feed`, 0.1);
      near(chat.height, feed.height, `...and on the chat and the feed`, 0.1);
      near(pane.lineHeight, feed.lineHeight, `at ${pct} percent a line is the same on the pane and the feed`, 0.01);
    }
  });
});

/** The rule's declarations: from the head's first occurrence through the first `}` (fileview-parity.test.ts's reader). */
const ruleOf = (css: string, head: string): string => { const i = css.indexOf(head); assert.ok(i >= 0, head + " is in the sheet"); return css.slice(i, css.indexOf("}", i) + 1); };

test("both sheets: .fileview-md declares line-height 1.5, the one rule, byte-equal", () => {
  const chat = fs.readFileSync(path.join(UI, "styles.css"), "utf8"), feed = fs.readFileSync(path.join(UI, "feed.css"), "utf8");
  for (const [name, css] of [["styles.css", chat], ["feed.css", feed]] as const) {
    const rule = ruleOf(css, ".fileview-md {");
    assert.match(rule, /; line-height: 1\.5; /, name + ": the prose leading is the root's own, GitHub's 1.5, not the body's (1.6 in styles.css, 1.5 in feed.css)");
  }
  assert.equal(ruleOf(chat, ".fileview-md {"), ruleOf(feed, ".fileview-md {"), "the rule mirrors exactly (the viewer mounts in both documents)");
});

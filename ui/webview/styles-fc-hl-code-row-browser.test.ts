// A highlight mark inside a Rendered code row keeps the row's columns in line, over the REAL viewer and the REAL Comments panel in
// headless Chromium (plans/markdown-viewer.md Slice 8, item 2; the review's round 1). A fence's rows are monospace columns, and the
// sheets' `.fc-hl` and `.fc-presel` rules give a mark 2 px of side padding, which inside a `<pre>` row pushed the marked characters and
// every character after them 2 px right (4 px past a mid-line mark): a commented line stood out of line with the rows above and below it
// (measured at cd3a06501: column 7 at +2.02 px and columns 14 and 19 at +4.02 after a mark over `ghijkl`, every column +2.00 under a
// whole-row mark). Both sheets now zero the horizontal padding inside `.fileview-md pre` (fileview-parity.test.ts pins the head
// byte-equal). Here a synthetic note with a three-row fence is opened in the Rendered view through real-viewer-leg.ts, on the Files
// pane at 900 px and in the chat modal, with two comments served: one on `ghijkl` in the first row, one on the whole third row. Once
// the panel paints, every column's x is read per row through a Range over the character (the second row, unmarked, is the reference),
// and the marks' computed padding, wash and ring are read; then a REAL drag over `mnopqr` in the second row opens the composer, whose
// pending target paints a `.fc-presel` mark there, and the columns are read again. Skips LOUDLY without a playwright browser (CI
// installs none), as the other browser legs do. Synthetic values only: an invented note, /repo/notes-api paths, the placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openPanel, frames, pageHtml, ORIGIN, REPORT, SID, MT, STATUS, type Mode } from "./real-viewer-leg";
import { makeAnchor } from "./anchor-map";

const ROW = "abcdef ghijkl mnopqr";
const NOTE = "Intro paragraph here.\n\n```\n" + ROW + "\n" + ROW + "\n" + ROW + "\n```\n\nAfter paragraph here.\n";
const T0 = 1757145600000;
const BODY = "Check this line against the spec.";
const COLS = [0, 7, 14, 19];                 // the first character, the marked word's first, the word after it, the row's last
const TOL = 0.1;                             // Chromium's sub-pixel spread over identical rows measures 0.02 px

/** The `k`th occurrence of `needle` in `s`. */
function nth(s: string, needle: string, k: number): number {
  let i = -1;
  for (let n = 0; n <= k; n++) { i = s.indexOf(needle, i + 1); assert.ok(i >= 0, "the note holds occurrence " + k + " of " + JSON.stringify(needle)); }
  return i;
}
/** A comment in the host's shape on occurrence `k` of `quote`: the exact source slice, its context, its position. */
function comment(quote: string, k: number, n: number): Record<string, unknown> {
  const at = nth(NOTE, quote, k);
  return { id: (T0 + n) + "-" + at, author: "you", ts: T0 + n, body: BODY, anchor: makeAnchor(NOTE, { start: at, end: at + quote.length }), anchorAt: at, replies: [], resolved: false };
}
const MID = comment("ghijkl", 0, 1);         // the first row's middle word
const WHOLE = comment(ROW, 2, 2);            // the third row entire
const id = (c: Record<string, unknown>): string => c.id as string;
const status = { ...STATUS, store: { ...STATUS.store, comments: [MID, WHOLE] }, storeMtimeNs: "1757145600000000061", unsent: { comments: [], replies: [], accepted: 0, rejected: 0, watermark: null } };

const markPainted = (page: any, cid: string): Promise<unknown> =>
  page.waitForFunction((c: string) => !!document.querySelector('.fileview-md [data-act="fcopen"][data-id="' + c + '"]'), cid, { timeout: 10000 });

type MarkRead = { cls: string; text: string; padLeft: string; padRight: string; shadow: string; background: string };
type Read = { texts: string[]; heights: number[]; x: Record<string, (number | null)[]>; marks: MarkRead[] };
/** In the page: the fence's rows, each column's x per row (the left edge of the character's own box), the marks' computed style. */
function readRows(cols: number[]): Read {
  const rows = Array.from(document.querySelectorAll(".fileview-md pre .cl")) as HTMLElement[];
  const charX = (row: HTMLElement, col: number): number | null => {
    const w = document.createTreeWalker(row, NodeFilter.SHOW_TEXT);
    let seen = 0;
    for (let t = w.nextNode() as Text | null; t; t = w.nextNode() as Text | null) {
      if (seen + t.data.length > col) { const r = document.createRange(); r.setStart(t, col - seen); r.setEnd(t, col - seen + 1); return Math.round(r.getBoundingClientRect().left * 100) / 100; }
      seen += t.data.length;
    }
    return null;
  };
  const x: Record<string, (number | null)[]> = {};
  for (const col of cols) x["col" + col] = rows.map((r) => charX(r, col));
  const marks = (Array.from(document.querySelectorAll(".fileview-md pre mark")) as HTMLElement[]).map((m) => {
    const cs = getComputedStyle(m);
    return { cls: m.className, text: m.textContent || "", padLeft: cs.paddingLeft, padRight: cs.paddingRight, shadow: cs.boxShadow, background: cs.backgroundColor };
  });
  return { texts: rows.map((r) => r.textContent || ""), heights: rows.map((r) => Math.round(r.getBoundingClientRect().height * 100) / 100), x, marks };
}
/** The spread of a column's x over the rows: its widest minus its narrowest. */
const spread = (xs: (number | null)[]): number => { const v = xs.filter((n): n is number => typeof n === "number"); return Math.round((Math.max(...v) - Math.min(...v)) * 100) / 100; };
function assertInLine(r: Read, what: string): void {
  assert.equal(r.texts.length, 3, what + ": the fence's three rows");
  assert.deepEqual(r.texts, [ROW, ROW, ROW], what + ": each row's text whole");
  for (const col of COLS) {
    const xs = r.x["col" + col];
    assert.ok(xs.every((n) => typeof n === "number"), what + ": column " + col + " read on every row: " + JSON.stringify(xs));
    assert.ok(spread(xs) <= TOL, what + ": column " + col + " in line across the rows (before: a mark's 2 px side padding moved it 2 or 4 px): " + JSON.stringify(xs));
  }
  assert.ok(spread(r.heights) <= TOL, what + ": the rows' heights equal: " + JSON.stringify(r.heights));
}
function assertMark(m: MarkRead | undefined, cls: string, text: string, what: string): void {
  assert.ok(m, what + ": the " + cls + " mark over " + JSON.stringify(text) + " stands");
  assert.equal(m!.text, text, what + ": the mark's text");
  assert.equal(m!.padLeft + " " + m!.padRight, "0px 0px", what + ": no horizontal padding on a mark inside a fence row");
  assert.notEqual(m!.shadow, "none", what + ": the ring stands");
  assert.notEqual(m!.background, "rgba(0, 0, 0, 0)", what + ": the wash stands");
}

type Points = { sx: number; sy: number; ex: number; ey: number };
/** In the page: the boxes of `word`'s first and last characters in fence row `row`. */
function pointsInRow(spec: { row: number; word: string }): Points {
  const row = document.querySelectorAll(".fileview-md pre .cl")[spec.row] as HTMLElement;
  const w = document.createTreeWalker(row, NodeFilter.SHOW_TEXT);
  for (let t = w.nextNode() as Text | null; t; t = w.nextNode() as Text | null) {
    const j = t.data.indexOf(spec.word);
    if (j < 0) continue;
    const rect = (off: number) => { const r = document.createRange(); r.setStart(t!, off); r.setEnd(t!, off + 1); return r.getBoundingClientRect(); };
    const a = rect(j), b = rect(j + spec.word.length - 1);
    return { sx: a.left + Math.min(1.5, a.width / 3), sy: a.top + a.height / 2, ex: b.right - Math.min(1.5, b.width / 3), ey: b.top + b.height / 2 };
  }
  throw new Error("the row holds no " + spec.word);
}
/** A real drag over the word in the row, the float, its click; the composer's pending target paints the presel mark. */
async function dragToComposer(page: any, row: number, word: string): Promise<string> {
  await page.evaluate(() => { getSelection()!.removeAllRanges(); });
  const pts: Points = await page.evaluate(pointsInRow, { row, word });
  await frames(page, 1);
  await page.mouse.move(pts.sx, pts.sy);
  await page.mouse.down();
  await page.mouse.move((pts.sx + pts.ex) / 2, (pts.sy + pts.ey) / 2, { steps: 3 });
  await page.mouse.move(pts.ex, pts.ey, { steps: 6 });
  await page.mouse.up();
  await frames(page, 2);
  const selected: string = await page.evaluate(() => String(getSelection()));
  await page.waitForFunction(() => { const f = document.querySelector(".fc-float") as HTMLElement | null; return !!f && !f.hidden; }, null, { timeout: 5000 });
  await page.click(".fc-float");
  await page.waitForFunction(() => !!document.querySelector(".fileview-md pre .fc-presel"), null, { timeout: 5000 });
  await frames(page, 2);
  return selected;
}

test("in a browser, the real viewer and panel on the Files pane at 900 px and in the chat modal: a comment's mark over a word in a fence row and one over a whole row leave every column in line with the unmarked row (before: 2 px, and 4 px past a mid-line mark), the marks keep their wash and ring with no side padding, and the composer's pending target painted by a real drag on a row leaves the columns in line too", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const [mode, width] of [["pane", 900], ["chat", 1000]] as [Mode, number][]) {
      const what = mode + " " + width + "px";
      const page = await browser.newPage({ viewport: { width, height: 700 } });
      const errors: string[] = [];
      page.on("pageerror", (e: Error) => { errors.push(e.message); });
      const html = pageHtml(mode, { [REPORT]: NOTE }, MT);
      await page.route((u: URL) => u.href.startsWith(ORIGIN), (route: any) => route.fulfill({ status: 200, contentType: "text/html", body: html }));
      await page.goto(ORIGIN + "/");
      await page.evaluate(([p, sid, st]: [string, string, unknown]) => { (window as any).__status = st; (window as any).FV.openFileView(p, sid, null); }, [REPORT, SID, status]);
      await page.waitForFunction(() => document.querySelectorAll(".fileview-md pre .cl").length === 3, null, { timeout: 10000 });
      await frames(page, 2);
      await openPanel(page);
      await markPainted(page, id(MID));
      await markPainted(page, id(WHOLE));
      await frames(page, 2);
      // the served comments' marks: the columns in line, the marks whole
      const r0: Read = await page.evaluate(readRows, COLS);
      assertInLine(r0, what + ", two comments painted");
      assert.equal(r0.marks.length, 2, what + ": two marks in the fence: " + JSON.stringify(r0.marks.map((m) => m.text)));
      assertMark(r0.marks.find((m) => m.text === "ghijkl"), "fc-hl", "ghijkl", what);
      assertMark(r0.marks.find((m) => m.text === ROW), "fc-hl", ROW, what);
      // the composer's pending target on the unmarked row: a real drag, the float, the presel mark; the columns still in line
      const selected = await dragToComposer(page, 1, "mnopqr");
      assert.equal(selected.trim(), "mnopqr", what + ": the drag selected the word: " + JSON.stringify(selected));
      const r1: Read = await page.evaluate(readRows, COLS);
      assertInLine(r1, what + ", the composer pending on the second row");
      const presel = r1.marks.find((m) => m.cls.split(/\s+/).includes("fc-presel"));
      assertMark(presel, "fc-presel", "mnopqr", what);
      assert.deepEqual(errors, [], what + ": no page errors");
      await page.close();
    }
  });
});

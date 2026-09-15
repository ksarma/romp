// The Raw view's rows over a file with CR, CRLF or mixed line endings, in headless Chromium over the REAL viewer
// (plans/markdown-viewer.md, Slice 7, item 7: "Raw splits rows on CR, CRLF and LF"; real-viewer-leg.ts serves the page with
// the Raw preference written first). Before Slice 7 codeBlock split the text on "\n" alone and set the rows through innerHTML,
// so a CR-only file was ONE `.fv-cl` row whose CRs the HTML parser turned into breaks inside it, a CRLF file's rows each ended
// in a "\r" the parser rewrote, and the seam's scrollToOffset counted LF alone, so every offset in a CR-only file landed on row
// 0. Now wrapNumberedHtml and the gutter count split on a CRLF, a lone CR or an LF (RAW_ROW_SPLIT), so a three-line CR-only
// file gives three rows numbered 1 to 3, a CRLF file one row per line and no phantom trailing row, a mixed file one row per
// line, no row's text carries a "\r" or an "\n", and scrollToOffset finds the row through the anchor map's verified row map
// (rawRowForOffset), which the leg asks directly through the bundle whether the rows match the file's text. The row numbers
// are CSS counters (`.fv-cl::before { counter-increment: fvln; content: counter(fvln) }`): getComputedStyle answers the
// computed `content`, which for a counter is the unresolved `counter(fvln)` in every engine, so the leg pins the rule through
// it (the content and the increment on every row, the reset on the pre) and reads the DIGITS the way Chromium exposes
// generated text, through the DevTools protocol's accessibility tree (the `::before` pseudo-element's StaticText). Skips
// LOUDLY without a playwright browser (CI installs none), as the other legs do. Before Slice 7: one row for the CR-only file
// (red at the first count over a git archive of the base with the leg copied in). Synthetic values only: invented lines,
// /repo/notes-api paths, the placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, frames, REPORT } from "./real-viewer-leg";

const CR3 = "a\rb\rc\r";
const CRLF3 = "a\r\nb\r\nc\r\n";
const MIXED = "one\rtwo\r\nthree\nfour\n";
/** Two hundred CR-ended lines: enough rows that a scroll to the middle is a scroll (the first rows leave the body's box). */
const CR_LONG = Array.from({ length: 200 }, (_, i) => "line " + (i + 1) + " of the CR file").join("\r") + "\r";

type Rows = { count: number; texts: string[]; contents: string[]; increments: string[]; reset: string; mode: string; text: string | null; mapped: number | null; mapRows: number | null };
/** The rows as painted: their count, each row's text, the computed `content` and `counter-increment` of each row's ::before, the
 *  pre's counter-reset, the seam's mode() and text(); and the anchor map's own word on them through the bundle: how many rows
 *  rawRows verifies against the text (null when it refuses) and which row rawRowForOffset answers for `offset` (its index, null
 *  when the map refuses). */
const readRows = (page: any, offset: number): Promise<Rows> => page.evaluate((off: number) => {
  const w = window as any;
  const code = document.querySelector(".fileview-body code.hljs") as HTMLElement;
  const rows = Array.from(code.querySelectorAll(".fv-cl")) as HTMLElement[];
  const pre = code.closest("pre") as HTMLElement;
  const src = w.__seam.text();
  const verified = w.FV.rawRows(code, src) as Element[] | null;
  const hit = w.FV.rawRowForOffset(code, src, off) as Element | null;
  return {
    count: rows.length, texts: rows.map((r) => r.textContent || ""),
    contents: rows.map((r) => getComputedStyle(r, "::before").content), increments: rows.map((r) => getComputedStyle(r, "::before").counterIncrement),
    reset: getComputedStyle(pre).counterReset, mode: w.__seam.mode(), text: src,
    mapped: hit ? rows.indexOf(hit as HTMLElement) : null, mapRows: verified ? verified.length : null,
  };
}, offset);

/** The digits each row's `::before` shows, read off Chromium's accessibility tree through the DevTools protocol: the row's
 *  `before` pseudo-element (DOM.describeNode lists it) has an accessibility node whose StaticText children carry the generated
 *  text; null for a row with no ::before. */
async function counterDigits(page: any): Promise<Array<string | null>> {
  const cdp = await page.context().newCDPSession(page);
  try {
    await cdp.send("DOM.enable"); await cdp.send("Accessibility.enable");
    const { root } = await cdp.send("DOM.getDocument", { depth: 0 });
    const { nodeIds } = await cdp.send("DOM.querySelectorAll", { nodeId: root.nodeId, selector: ".fileview-body code.hljs .fv-cl" });
    const { nodes } = await cdp.send("Accessibility.getFullAXTree");
    const byId = new Map<string, any>(nodes.map((n: any) => [n.nodeId, n]));
    const out: Array<string | null> = [];
    for (const nodeId of nodeIds) {
      const { node } = await cdp.send("DOM.describeNode", { nodeId, depth: 0 });
      const before = (node.pseudoElements || []).find((p: any) => p.pseudoType === "before");
      if (!before) { out.push(null); continue; }
      const ax = nodes.find((n: any) => n.backendDOMNodeId === before.backendNodeId);
      const texts: string[] = [];
      const walk = (n: any) => { if (!n) return; if (n.role && n.role.value === "StaticText" && n.name) texts.push(String(n.name.value)); for (const id of n.childIds || []) walk(byId.get(id)); };
      walk(ax);
      out.push(texts.join(""));
    }
    return out;
  } finally { await cdp.detach(); }
}

type Scrolled = { inBody: boolean; firstAbove: boolean; scrollTop: number; scrolls: number };
/** Row `i`'s box against the body's after a scroll: whether it lies within the body's box, whether the first row has left it above,
 *  the body's scrollTop. */
const rowPlace = (page: any, i: number): Promise<Scrolled> => page.evaluate((k: number) => {
  const body = document.querySelector(".fileview-body") as HTMLElement;
  const rows = Array.from(body.querySelectorAll("code.hljs .fv-cl")) as HTMLElement[];
  const b = body.getBoundingClientRect(), r = rows[k].getBoundingClientRect(), f = rows[0].getBoundingClientRect();
  return { inBody: r.top >= b.top - 0.5 && r.bottom <= b.bottom + 0.5 && r.height > 0, firstAbove: f.bottom < b.top, scrollTop: body.scrollTop, scrolls: rows.length };
}, i);

test("in a browser: a three-line CR-only file gives three Raw rows numbered 1 to 3 (before Slice 7: one row), a CRLF file one row per line and no phantom trailing row, a mixed file one row per line; no row's text carries a CR or an LF; the anchor map verifies the rows against the text and finds the row for an offset; __seam.scrollToOffset(4) on the CR-only file scrolls the third row into the body; pane and feed", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const mode of ["pane", "feed"] as const) {
      const { page, errors } = await openViewer(browser, mode, 700, 500, { docs: { [REPORT]: CR3 }, raw: true });
      let r = await readRows(page, 4);
      assert.equal(r.count, 3, mode + ": three rows for three CR-ended lines (before Slice 7: one row holding the three CRs)");
      assert.deepEqual(r.texts, ["a", "b", "c"], mode + ": one line per row, the CRs consumed between them");
      assert.ok(r.texts.every((x) => !/[\r\n]/.test(x)), mode + ": no row's text carries a CR or an LF");
      assert.deepEqual(r.contents, ["counter(fvln)", "counter(fvln)", "counter(fvln)"], mode + ": every row's ::before is the counter (the computed content, unresolved by design)");
      assert.deepEqual(r.increments, ["fvln 1", "fvln 1", "fvln 1"], mode + ": each row counts one");
      assert.equal(r.reset, "fvln 0", mode + ": the pre resets the counter, so the rows read 1, 2, 3");
      assert.deepEqual(await counterDigits(page), ["1", "2", "3"], mode + ": the digits the rows show (Chromium's accessibility tree carries the generated text)");
      assert.equal(r.mode, "raw", mode + ": the Raw view"); assert.equal(r.text, CR3, mode + ": text() is the file's text, CRs and all");
      assert.equal(r.mapRows, 3, mode + ": the anchor map verified the three rows against the text (the CR consumed as the ending between rows)");
      assert.equal(r.mapped, 2, mode + ": rawRowForOffset(4), the offset of \"c\", is the third row");
      await page.evaluate(() => { (window as any).__seam.scrollToOffset(4); });
      await frames(page, 2);
      const p = await rowPlace(page, 2);
      assert.ok(p.inBody, mode + ": the third row's box lies within the body's after scrollToOffset(4) (before Slice 7: the LF count gave row 0 of one row)");
      assert.deepEqual(errors, [], mode + ": no uncaught page error");
      await page.close();
    }
    // a CRLF file: a CRLF is one ending (tried first), so three rows and no phantom fourth
    const crlf = await openViewer(browser, "pane", 700, 500, { docs: { [REPORT]: CRLF3 }, raw: true });
    let r = await readRows(crlf.page, CRLF3.indexOf("c"));
    assert.equal(r.count, 3, "CRLF: three rows, no phantom trailing row (a CRLF is one ending)");
    assert.deepEqual(r.texts, ["a", "b", "c"], "CRLF: one line per row, no CR left at a row's end");
    assert.ok(r.texts.every((x) => !/[\r\n]/.test(x)), "CRLF: no row's text carries a CR or an LF");
    assert.deepEqual(await counterDigits(crlf.page), ["1", "2", "3"], "CRLF: numbered 1 to 3");
    assert.equal(r.mapRows, 3, "CRLF: the map verifies the rows"); assert.equal(r.mapped, 2, "CRLF: the offset of \"c\" is the third row");
    assert.deepEqual(crlf.errors, []);
    await crlf.page.close();
    // a mixed file: CR, CRLF and LF endings in one text, one row per line
    const mixed = await openViewer(browser, "pane", 700, 500, { docs: { [REPORT]: MIXED }, raw: true });
    r = await readRows(mixed.page, MIXED.indexOf("three"));
    assert.equal(r.count, 4, "mixed: four rows for four lines");
    assert.deepEqual(r.texts, ["one", "two", "three", "four"], "mixed: one line per row whatever ended it");
    assert.ok(r.texts.every((x) => !/[\r\n]/.test(x)), "mixed: no row's text carries a CR or an LF");
    assert.deepEqual(await counterDigits(mixed.page), ["1", "2", "3", "4"], "mixed: numbered 1 to 4");
    assert.equal(r.mapRows, 4, "mixed: the map verifies the rows"); assert.equal(r.mapped, 2, "mixed: the offset of \"three\" is the third row");
    assert.deepEqual(mixed.errors, []);
    await mixed.page.close();
  });
});

test("in a browser: a two-hundred-line CR-only file gives two hundred rows and __seam.scrollToOffset on the hundred-and-fiftieth line's offset scrolls that row into the body, the first rows leaving it above (a scroll that is a scroll; before Slice 7: one row, and the LF count gave row 0)", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openViewer(browser, "pane", 700, 500, { docs: { [REPORT]: CR_LONG }, raw: true });
    const off = CR_LONG.indexOf("line 150 of");
    const r = await readRows(page, off);
    assert.equal(r.count, 200, "two hundred rows (before Slice 7: one)");
    assert.equal(r.texts[0], "line 1 of the CR file"); assert.equal(r.texts[149], "line 150 of the CR file"); assert.equal(r.texts[199], "line 200 of the CR file");
    assert.ok(r.texts.every((x) => !/[\r\n]/.test(x)), "no row's text carries a CR or an LF");
    assert.equal(r.mapRows, 200, "the map verifies every row"); assert.equal(r.mapped, 149, "rawRowForOffset answers the hundred-and-fiftieth row");
    const before = await rowPlace(page, 149);
    assert.equal(before.inBody, false, "before the scroll the row is below the body's box"); assert.equal(before.scrollTop, 0);
    await page.evaluate((n: number) => { (window as any).__seam.scrollToOffset(n); }, off);
    await frames(page, 2);
    const after = await rowPlace(page, 149);
    assert.ok(after.inBody, "the row's box lies within the body's after the scroll");
    assert.ok(after.firstAbove, "the first row has left the body above: the body scrolled"); assert.ok(after.scrollTop > 0);
    const digits = await counterDigits(page);
    assert.equal(digits[0], "1"); assert.equal(digits[149], "150"); assert.equal(digits[199], "200");
    assert.deepEqual(errors, [], "no uncaught page error");
    await page.close();
  });
});

// The reader's place at the edge of a CLOSED `<details>`, in headless Chromium over the REAL module (plans/markdown-viewer.md
// Slice 5, item 1b; the Slice 5 review, round 1; reader-place.ts boxOf and readRendered). The rule: the fold's summary is
// a row of the wrapper's block's own and is passed over, and a closed details reads the block after it. Chromium 151 lays
// a shut fold out in a way the rule's first build did not expect: the content of a closed `<details>` is skipped through
// its `::details-content` pseudo-element's content-visibility: hidden, and a skipped element KEEPS a box on a forced read
// (getBoundingClientRect answers a full rect and one client rect, the hidden blocks stacked from where the fold would
// open, so the first hidden paragraph's box coincides with the block after the fold's); only checkVisibility() says the
// element is not shown. Read by its rect alone, the hidden paragraph was the place, and the Raw switch seated the fold's
// hidden source at the edge (paragraph 11's row at +27 with `<summary>` above it, for a reader who had paragraph 16 in
// view). Now boxOf asks checkVisibility where the browser offers it, so:
//   - the fold's summary 3px past the edge reads the block after the fold, and the Raw switch puts that block's own row
//     where the block was, the fold's own rows above it (the closing tag's row is the top row, not the fold's hidden text);
//     and the way back is exact: the Raw top row is then the closing tag's (`</details>`, 9px above the edge), whose block
//     renders no element of its own, and readPlace reads it as the block after it, as a blank row between blocks is read
//     (before, with the read side alone fixed, the closing block was the place and its seat walked back through the
//     fold's unshown paragraphs to the wrapper's refused block, seated nothing, and the numeric scrollTop stood, off by
//     the fold's source height: paragraph 20 on top at 900px, 370px off; paragraph 19 at 380px, 553px off);
//   - from Raw, the closing tag's row 9px above the edge switched to Rendered puts the block after the fold where its
//     own row was, the fold shut or open (before: shut, no seat, the numeric scrollTop 360px off; open, the last nested
//     paragraph's box seated at the row's depth, so the block after the fold landed 14px low at 900px);
//   - a Raw row of the fold's hidden source switched to Rendered, the fold shut, seats the block after the fold where its
//     own row was: the Raw view shows the fold's text whatever the Rendered view's fold state, so the place read there
//     carries the block after the fold with its row's top (reader-place.ts Place.after), and the seat stands on it when
//     the kept block is not shown (the review's round 2; round 1 had the refusal, ruling 2's, and it made the round
//     trip from a shut fold whose summary WRAPS lose 361px at 900 and 562 at 380: the Raw seat put the block after the
//     fold where the reader had it, well below the edge, so the fold's hidden rows filled the rows above and the top
//     Raw row was the last hidden paragraph, whose seat was refused, and the numeric scrollTop stood in a view shorter
//     by the fold's whole source; before round 1: the phantom box was seated, two blocks past the fold). A fold the
//     person OPENED before the switch is open again after it (file-view.ts's fold keeper restores it before the seat),
//     so the same row then seats its own paragraph, shown, at the row's depth;
//   - the round trip from a shut fold whose summary wraps to two lines at 900px and more at 380 is exact, the fold's
//     hidden rows on top of Raw between (the round-2 scene above);
//   - a block of two closing tags (`</details>\n</div>`, `</details></div>`, one html block to marked) reads as the block
//     after it from either row, as one closing tag alone did since round 1 (before round 2: its own place, whose seat put
//     the last nested paragraph at the row, the block after it 21 to 110px low);
//   - a comment's Raw row renders nothing too and reads as the block after it: inside a wrapper (before: its own place,
//     seated through the block before it, 71px off), and right after the opener (before: no seat, the walk back reaching
//     the wrapper's refused block).
// Two pane widths for the first scene and the wrapped summary, so the fold sits in a wide and a narrow column. Legs
// await frames, never a timer. Skips LOUDLY without a playwright browser.
// Synthetic values only: an invented report, /repo/notes-api paths, the placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, frames, PARA, REPORT } from "./real-viewer-leg";

const near = (a: number, b: number, what: string, tol = 1.5) => assert.ok(Math.abs(a - b) <= tol, `${what}: ${a} vs ${b}`);
const paras = (a: number, b: number) => Array.from({ length: b - a + 1 }, (_, i) => PARA(a + i)).join("\n\n");
/** paragraphs 1 to 10, a closed details holding paragraphs 11 to 15 after its summary, paragraphs 16 to 30 */
const fold = (open: boolean) => "# Report\n\n" + paras(1, 10) + "\n\n<details" + (open ? " open" : "") + ">\n<summary>Closed one</summary>\n\n" + paras(11, 15) + "\n\n</details>\n\n" + paras(16, 30) + "\n";
const DOC = fold(false);
const HIDDEN_ROW = /^(<summary>|Paragraph 1[1-5]:)/;
/** the same, with a summary long enough to wrap: three or four lines at 900px, many more at 380 */
const LONG_SUMMARY = "A rather long summary line that wraps onto several rows in a narrow pane, so that the title of the fold is tall enough to push the block after it well below the edge, and long enough again that the fold title takes three or four lines in a wide column, the way a section title with a subtitle and a date does in a report";
const foldLong = "# Report\n\n" + paras(1, 10) + "\n\n<details>\n<summary>" + LONG_SUMMARY + "</summary>\n\n" + paras(11, 15) + "\n\n</details>\n\n" + paras(16, 30) + "\n";
/** a centred div holding paragraphs 6 to 8 and an open details holding 9 to 11, both closed by `closers` (one block), then 15 to 25 */
const nested = (closers: string) => "# Report\n\n" + paras(1, 5) + "\n\n<div align=\"center\">\n\n" + paras(6, 8) + "\n\n<details open>\n<summary>Inner fold</summary>\n\n" + paras(9, 11) + "\n\n" + closers + "\n\n" + paras(15, 25) + "\n";
/** a centred div holding paragraphs 6 and 7, a comment, paragraphs 8 and 9 */
const commented = "# Report\n\n" + paras(1, 5) + "\n\n<div align=\"center\">\n\n" + paras(6, 7) + "\n\n<!-- a note to self -->\n\n" + paras(8, 9) + "\n\n</div>\n\n" + paras(10, 20) + "\n";
/** a centred div whose first nested block is a comment, then paragraphs 6 to 8 */
const commentFirst = "# Report\n\n" + paras(1, 5) + "\n\n<div align=\"center\">\n\n<!-- a note to self -->\n\n" + paras(6, 8) + "\n\n</div>\n\n" + paras(9, 20) + "\n";

const click = async (page: any, label: string) => { await page.locator("#romp-fileview .fileview-btn", { hasText: new RegExp("^" + label + "$") }).click(); await frames(page, 3); };
/** The first top-level element of the Rendered view ending below the body's top edge: its tag and its top. */
const topElement = (page: any) => page.evaluate(() => {
  const body = document.querySelector(".fileview-body")!; const br = body.getBoundingClientRect();
  for (const e of Array.from(body.querySelectorAll(".fileview-md > *"))) { const r = e.getBoundingClientRect(); if (r.bottom > br.top + 0.5) return { tag: e.tagName, top: Math.round((r.top - br.top) * 10) / 10 }; }
  return null;
});
/** The first Raw row ending below the body's top edge: its text, its top and the body's scrollTop; null when no Raw view shows. */
const rowAtTop = (page: any) => page.evaluate(() => {
  const body = document.querySelector(".fileview-body")!; const br = body.getBoundingClientRect();
  for (const r of Array.from(body.querySelectorAll("code.hljs .fv-cl"))) { const rr = r.getBoundingClientRect(); if (rr.bottom > br.top + 0.5) return { text: (r.textContent || "").trim().slice(0, 48), top: Math.round((rr.top - br.top) * 10) / 10, scrollTop: body.scrollTop }; }
  return null;
});
/** The box of the first element under the body matching `sel` whose text includes `text`, from the body's top edge. */
const box = (page: any, sel: string, text: string) => page.evaluate(([s, t]: [string, string]) => {
  const body = document.querySelector(".fileview-body")!; const br = body.getBoundingClientRect();
  const el = Array.from(body.querySelectorAll(s)).find((e) => (e.textContent || "").includes(t)); if (!el) return null;
  const r = el.getBoundingClientRect(); return { top: Math.round((r.top - br.top) * 10) / 10, bottom: Math.round((r.bottom - br.top) * 10) / 10, scrollTop: body.scrollTop };
}, [sel, text]);
/** Scroll so that element's top sits `extra` px above the body's top edge. */
const scrollInto = (page: any, sel: string, text: string, extra = 0) => page.evaluate(([s, t, x]: [string, string, number]) => {
  const body = document.querySelector(".fileview-body")!;
  const el = Array.from(body.querySelectorAll(s)).find((e) => (e.textContent || "").includes(t))!;
  body.scrollTop += el.getBoundingClientRect().top - body.getBoundingClientRect().top + x;
}, [sel, text, extra]);
/** Scroll so the Raw row whose text includes `text` has its top `above` px above the body's top edge. */
const rowToEdge = (page: any, text: string, above = 0) => page.evaluate(([t, a]: [string, number]) => {
  const body = document.querySelector(".fileview-body")!;
  const row = Array.from(body.querySelectorAll("code.hljs .fv-cl")).find((r) => (r.textContent || "").includes(t))!;
  body.scrollTop += row.getBoundingClientRect().top - body.getBoundingClientRect().top + a;
}, [text, above]);
/** Trap every script write of the body's scrollTop from now on (the viewer's seat is one; the browser's own scrolls are not
 *  writes), so a switch can be shown to have seated nothing. Installed after the scene's own scroll. */
const trapWrites = (page: any) => page.evaluate(() => {
  const body = document.querySelector(".fileview-body") as HTMLElement;
  const proto = Object.getOwnPropertyDescriptor(Element.prototype, "scrollTop")!;
  (window as any).__writes = [];
  Object.defineProperty(body, "scrollTop", { get() { return proto.get!.call(this); }, set(v) { (window as any).__writes.push(v); proto.set!.call(this, v); }, configurable: true });
});
const writes = (page: any): Promise<number[]> => page.evaluate(() => (window as any).__writes as number[]);
/** How the browser laid the fold out: whether the details is closed, the first hidden paragraph's rect against the block after
 *  the fold's, its client rects, and checkVisibility for the hidden paragraph, the summary and the block after. */
const foldShape = (page: any) => page.evaluate(() => {
  const md = document.querySelector(".fileview-md")!;
  const det = md.querySelector("details")!, sum = det.querySelector("summary")!;
  const ps = Array.from(md.querySelectorAll("p"));
  const hidden = ps.find((p) => (p.textContent || "").startsWith("Paragraph 11:"))!, after = ps.find((p) => (p.textContent || "").startsWith("Paragraph 16:"))!;
  const h = hidden.getBoundingClientRect(), a = after.getBoundingClientRect();
  const r = (x: number) => Math.round(x * 10) / 10;
  return {
    closed: !det.hasAttribute("open"), insideDetails: det.contains(hidden) && !det.contains(after),
    hidden: { top: r(h.top), bottom: r(h.bottom), rects: hidden.getClientRects().length, visible: hidden.checkVisibility() },
    after: { top: r(a.top), bottom: r(a.bottom), visible: after.checkVisibility() },
    summaryVisible: sum.checkVisibility(),
  };
});

test("in a browser, the real module: a closed details' summary 3px past the edge reads the block after the fold (the fold's paragraphs keep boxes in Chromium, the first coinciding with that block's, but are not shown): the Raw switch puts that block's own row where the block was, the fold's own rows above it, not the fold's hidden text at the edge (before: paragraph 11's row at the edge under `<summary>`, for a reader who had paragraph 16 in view), and the way back, from the closing tag's row on top, puts the block where it was (the closing row reads as the block after it; before: no seat, and the numeric scrollTop off by the fold's source height)", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const width of [900, 380]) {
      const what = `pane ${width}`;
      const { page, errors } = await openViewer(browser, "pane", width, 600, { docs: { [REPORT]: DOC } });
      const shape = await foldShape(page);
      assert.ok(shape.closed && shape.insideDetails, what + `: the fixture: paragraph 11 is nested in a closed details, paragraph 16 follows it (got ${JSON.stringify(shape)})`);
      assert.deepEqual([shape.hidden.visible, shape.after.visible, shape.summaryVisible], [false, true, true], what + `: the fixture: checkVisibility is false for the fold's content alone (got ${JSON.stringify(shape)})`);
      // Chromium's layout of a shut fold, the premise of this scene: if a browser stops laying skipped content out, the hidden
      // paragraph has no rect, the rect rule alone passes it over, and this scene no longer exercises the phantom
      assert.ok(shape.hidden.rects >= 1 && Math.abs(shape.hidden.top - shape.after.top) <= 0.5 && Math.abs(shape.hidden.bottom - shape.after.bottom) <= 0.5, what + `: the fixture: the hidden paragraph keeps a box coinciding with paragraph 16's, as Chromium 151 lays a closed details out (got ${JSON.stringify(shape)})`);
      await scrollInto(page, ".fileview-md summary", "Closed one", 3); await frames(page, 2);
      const summary = (await box(page, ".fileview-md summary", "Closed one"))!;
      near(summary.top, -3, what + ": the scene starts with the summary 3px past the edge", 1);
      const before = (await box(page, ".fileview-md > p", "Paragraph 16:"))!;
      assert.ok(before.top > 0 && before.top < 60, what + `: paragraph 16, the block after the fold, is the first block below the edge (top ${before.top})`);
      await click(page, "Raw");
      const row = (await rowAtTop(page))!;
      assert.ok(row, what + ": the Raw view painted");
      assert.ok(!HIDDEN_ROW.test(row.text), what + `: the Raw top row is not the fold's hidden text or its summary (got ${JSON.stringify(row.text)} at scrollTop ${row.scrollTop}; before: paragraph 11's row seated at the edge, the summary's row above it)`);
      const p16 = (await box(page, "code.hljs .fv-cl", "Paragraph 16:"))!;
      near(p16.top, before.top, what + `: paragraph 16's own row is where the paragraph was (the top row is ${JSON.stringify(row.text)}; before: paragraph 11's row there)`, 1);
      assert.equal(row.text, "</details>", what + ": the closing tag's row is the top row, 9px above the edge: the scene the way back reads from");
      await click(page, "Rendered");
      const back = (await box(page, ".fileview-md > p", "Paragraph 16:"))!;
      near(back.top, before.top, what + `: back in Rendered paragraph 16 is where it was (the closing row read as the block after it; with the closing block as the place its seat was refused and the numeric scrollTop stood, paragraph ${width === 900 ? 20 : 19} on top)`);
      const top = (await topElement(page))!;
      assert.equal(top.tag, "DETAILS", what + `: the shut fold is the top element again, its summary straddling the edge (got ${JSON.stringify(top)})`);
      assert.deepEqual(errors, [], what + ": no script error");
      await page.close();
    }
  });
});

test("in a browser, the real module: from Raw, the closing tag's row of a details 9px above the edge switched to Rendered puts the block after the fold where its own row was, the fold shut or open (the closing row renders nothing and reads as the block after it; before: shut, no seat, the wrapper's block refused on the walk back, the block after 360px off; open, the last nested paragraph's box seated at the row's depth, the block after 14px low)", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const open of [false, true]) {
      const what = open ? "open fold" : "shut fold";
      const { page, errors } = await openViewer(browser, "pane", 900, 600, { docs: { [REPORT]: fold(open) }, raw: true });
      await rowToEdge(page, "</details>", 9); await frames(page, 2);
      const row = (await rowAtTop(page))!;
      assert.equal(row.text, "</details>", what + `: the scene starts on the closing tag's row (got ${JSON.stringify(row.text)})`);
      near(row.top, -9, what + ": 9px above the edge", 1);
      const p16Row = (await box(page, "code.hljs .fv-cl", "Paragraph 16:"))!;
      assert.ok(p16Row.top > 0 && p16Row.top < 60, what + `: paragraph 16's row is the first block's row below the edge (top ${p16Row.top})`);
      await click(page, "Rendered");
      const back = (await box(page, ".fileview-md > p", "Paragraph 16:"))!;
      near(back.top, p16Row.top, what + `: paragraph 16 is where its row was (before: ${open ? "paragraph 15's box seated at the row's depth, paragraph 16 at 40.7 for 27" : "no seat, the numeric scrollTop standing, paragraph 16 at -333 for 27"})`);
      const shape = await foldShape(page);
      assert.equal(shape.closed, !open, what + ": the fold is as the source says");
      assert.deepEqual(errors, [], what + ": no script error");
      await page.close();
    }
  });
});

test("in a browser, the real module: a Raw row of a closed details' hidden source 3px above the edge switched to Rendered seats the block after the fold where its own row was (the place read in Raw carries it, Place.after, and the paragraph itself is not shown; before: no seat, the wrapper's block refused on the walk back, and the numeric scrollTop stood); the same row with the fold OPENED by the person before the switch (the fold keeper restores it before the seat) seats the paragraph itself, shown, at the row's depth", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    // the fold shut: the block after it, paragraph 16, where its row was
    const { page, errors } = await openViewer(browser, "pane", 900, 600, { docs: { [REPORT]: DOC }, raw: true });
    await rowToEdge(page, "Paragraph 13:", 3); await frames(page, 2);
    const row = (await rowAtTop(page))!;
    assert.ok(row.text.startsWith("Paragraph 13:"), `the scene starts on paragraph 13's row, inside the fold's source (got ${JSON.stringify(row.text)})`);
    near(row.top, -3, "3px above the edge", 1);
    const p16Row = (await box(page, "code.hljs .fv-cl", "Paragraph 16:"))!;
    assert.ok(p16Row.top > 60, `the fixture: paragraph 16's row is well below the edge, the fold's hidden rows between (top ${p16Row.top})`);
    await trapWrites(page);
    await click(page, "Rendered");
    const shape = await foldShape(page);
    assert.ok(shape.closed && !shape.hidden.visible, `the fold is shut in Rendered (got ${JSON.stringify(shape)})`);
    assert.equal((await writes(page)).length, 1, `the viewer seated once across the switch (before: no write; the fold's hidden paragraph has no layout and the walk back reached the wrapper's refused block)`);
    const p16 = (await box(page, ".fileview-md > p", "Paragraph 16:"))!;
    near(p16.top, p16Row.top, "paragraph 16, the block after the fold, is where its own row was (before: the numeric scrollTop standing, paragraph 16 about 360px off)");
    assert.deepEqual(errors, [], "no script error");
    await page.close();
    // the fold OPENED by the person in Rendered, then Raw, then back: the keeper restores the fold open, paragraph 13 is shown, and
    // the row seats its own paragraph (the carried block after the fold unused)
    const o = await openViewer(browser, "pane", 900, 600, { docs: { [REPORT]: DOC } });
    await o.page.locator(".fileview-md summary", { hasText: "Closed one" }).click(); await frames(o.page, 2);
    assert.equal((await foldShape(o.page)).closed, false, "the fixture: the person opened the fold");
    await click(o.page, "Raw");
    await rowToEdge(o.page, "Paragraph 13:", 3); await frames(o.page, 2);
    const row2 = (await rowAtTop(o.page))!;
    assert.ok(row2.text.startsWith("Paragraph 13:"), `the scene starts on paragraph 13's row (got ${JSON.stringify(row2.text)})`);
    const rowBox = (await box(o.page, "code.hljs .fv-cl", "Paragraph 13:"))!;
    await click(o.page, "Rendered");
    const shape2 = await foldShape(o.page);
    assert.equal(shape2.closed, false, `the fold is open again after the paint (got ${JSON.stringify(shape2)})`);
    const p13 = (await box(o.page, ".fileview-md details > p", "Paragraph 13:"))!;
    // the row's depth as a fraction of the row's height, scaled to the paragraph's height (seatedTop); the browser snaps the write
    near(p13.top, rowBox.top * (p13.bottom - p13.top) / (rowBox.bottom - rowBox.top), "paragraph 13 itself, shown, at the row's depth scaled by its height over the row's (the carried block after the fold is not used when the kept block is shown)", 2);
    const top = (await topElement(o.page))!;
    assert.equal(top.tag, "DETAILS", `the open fold is the top element, paragraph 13 partway in (got ${JSON.stringify(top)})`);
    assert.deepEqual(o.errors, [], "no script error");
    await o.page.close();
  });
});

test("in a browser, the real module: Rendered to Raw to Rendered from a SHUT fold whose summary wraps (two lines at 900px, more at 380) is exact: the Rendered read passes over the summary and names the block after the fold, well below the edge; the Raw seat puts that block's row there, so the fold's hidden rows fill the rows above it and the top Raw row is one of them; the way back reads that row as its own block carrying the block after the fold, finds the block not shown and stands on the carried one where its row was (before: the hidden row's seat was refused, the numeric scrollTop stood in a view shorter by the fold's source, and the reader landed 361px down at 900 and 562 at 380)", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const width of [900, 380]) {
      const what = `pane ${width}`;
      const { page, errors } = await openViewer(browser, "pane", width, 700, { docs: { [REPORT]: foldLong } });
      const shape = await foldShape(page);
      assert.ok(shape.closed && shape.insideDetails && !shape.hidden.visible, what + `: the fixture: a shut fold holding paragraphs 11 to 15 (got ${JSON.stringify(shape)})`);
      await scrollInto(page, ".fileview-md summary", "A rather long summary", 0); await frames(page, 2);
      const summary = (await box(page, ".fileview-md summary", "A rather long summary"))!;
      near(summary.top, 0, what + ": the scene starts with the summary's top at the edge", 1);
      assert.ok(summary.bottom - summary.top > 40, what + `: the fixture: the summary wraps (height ${summary.bottom - summary.top})`);
      const before = (await box(page, ".fileview-md > p", "Paragraph 16:"))!;
      assert.ok(before.top > 60, what + `: the fixture: the block after the fold sits well below the edge (top ${before.top})`);
      await click(page, "Raw");
      const row = (await rowAtTop(page))!;
      const closerRow = (await box(page, "code.hljs .fv-cl", "</details>"))!;
      assert.ok(closerRow.top > 20 && (HIDDEN_ROW.test(row.text) || row.text === "") && !row.text.startsWith("<summary>"), what + `: the fixture: the closing row is below the edge, so the top Raw row is inside the fold's hidden source, a paragraph's or a blank between two, the scene the way back reads from (got ${JSON.stringify(row.text)} at ${row.top}, the closer at ${closerRow.top})`);
      const p16Row = (await box(page, "code.hljs .fv-cl", "Paragraph 16:"))!;
      near(p16Row.top, before.top, what + ": paragraph 16's own row is where the paragraph was", 1);
      await click(page, "Rendered");
      const back = (await box(page, ".fileview-md > p", "Paragraph 16:"))!;
      near(back.top, before.top, what + `: back in Rendered paragraph 16 is where it was (before: no seat, paragraph 16 ${width === 900 ? 361 : 562}px up)`);
      const sum2 = (await box(page, ".fileview-md summary", "A rather long summary"))!;
      near(sum2.top, 0, what + ": the summary's top is at the edge again", 1.5);
      const top = (await topElement(page))!;
      assert.equal(top.tag, "DETAILS", what + `: the shut fold is the top element again (got ${JSON.stringify(top)})`);
      assert.deepEqual(errors, [], what + ": no script error");
      await page.close();
    }
  });
});

test("in a browser, the real module: from Raw, a block of two closing tags (`</details>` then `</div>` on consecutive lines, or on one line: one html block) at the top edge switched to Rendered puts the block after it where its own row was, from either row (before: the block was its own place, its seat put the last nested paragraph at the row, and the block after it landed 21px low at 900 and 110 at 380)", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const [closers, rows] of [["</details>\n</div>", ["</details>", "</div>"]], ["</details></div>", ["</details></div>"]]] as const) {
      for (const rowText of rows) {
        const what = JSON.stringify(closers) + " from the " + JSON.stringify(rowText) + " row";
        const { page, errors } = await openViewer(browser, "pane", 900, 600, { docs: { [REPORT]: nested(closers) }, raw: true });
        await rowToEdge(page, rowText, 0); await frames(page, 2);
        const row = (await rowAtTop(page))!;
        assert.equal(row.text, rowText, what + `: the scene starts on the closing row (got ${JSON.stringify(row.text)})`);
        const p15Row = (await box(page, "code.hljs .fv-cl", "Paragraph 15:"))!;
        assert.ok(p15Row.top > 0 && p15Row.top < 80, what + `: paragraph 15's row is the first block's row below the edge (top ${p15Row.top})`);
        await click(page, "Rendered");
        const p15 = (await box(page, ".fileview-md > p", "Paragraph 15:"))!;
        near(p15.top, p15Row.top, what + ": paragraph 15 is where its row was (before: paragraph 11, the last nested one, at the edge and paragraph 15 at 74.8)");
        const shape = await page.evaluate(() => { const md = document.querySelector(".fileview-md")!; const div = md.querySelector(":scope > div")!, det = div.querySelector("details")!; return { divKids: div.children.length, detOpen: det.hasAttribute("open"), p15Top: !!md.querySelector(":scope > p:nth-of-type(9)") }; });
        assert.ok(shape.divKids >= 4 && shape.detOpen, what + `: the fixture: the div nests its paragraphs and the open details (got ${JSON.stringify(shape)})`);
        assert.deepEqual(errors, [], what + ": no script error");
        await page.close();
      }
    }
  });
});

test("in a browser, the real module: from Raw, an html comment's row inside a wrapper at the top edge switched to Rendered puts the block after it where its own row was (before: the comment was its own place and the seat put the block BEFORE it at the row, 71px off), and a comment right after the opener puts the first nested block where its row was (before: no seat, the walk back reaching the wrapper's refused block)", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const [what, doc, after] of [["a comment between nested paragraphs", commented, "Paragraph 8:"], ["a comment right after the opener", commentFirst, "Paragraph 6:"]] as const) {
      const { page, errors } = await openViewer(browser, "pane", 900, 600, { docs: { [REPORT]: doc }, raw: true });
      await rowToEdge(page, "<!-- a note to self -->", 0); await frames(page, 2);
      const row = (await rowAtTop(page))!;
      assert.equal(row.text, "<!-- a note to self -->", what + `: the scene starts on the comment's row (got ${JSON.stringify(row.text)})`);
      const afterRow = (await box(page, "code.hljs .fv-cl", after))!;
      assert.ok(afterRow.top > 0 && afterRow.top < 60, what + `: the block after the comment has its row just below the edge (top ${afterRow.top})`);
      await click(page, "Rendered");
      const el = (await box(page, ".fileview-md div > p", after))!;
      near(el.top, afterRow.top, what + `: ${after} is where its row was`);
      assert.deepEqual(errors, [], what + ": no script error");
      await page.close();
    }
  });
});

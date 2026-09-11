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
//   - a Raw row of the fold's hidden source switched to Rendered seats nothing: its block is not shown, the fold's blocks
//     before it are not shown, and the wrapper's own block is refused (the owner's ruling 2), so the viewer writes no
//     scrollTop and the body is left to the browser (before: the phantom box was seated, two blocks past the fold).
// Two pane widths for the first scene, so the fold sits in a wide and a narrow column. A refusal is pinned as what the
// viewer does (a setter trap on the body's scrollTop records every script write), never as where the body lands. Legs
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

test("in a browser, the real module: a Raw row of a closed details' hidden source switched to Rendered seats nothing (the paragraph is not shown, the fold's paragraphs before it are not shown, and the wrapper's own block is refused, ruling 2), so the viewer writes no scrollTop and the body is the browser's (before: the paragraph's phantom box was seated, two blocks past the fold)", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openViewer(browser, "pane", 900, 600, { docs: { [REPORT]: DOC }, raw: true });
    await rowToEdge(page, "Paragraph 13:", 3); await frames(page, 2);
    const row = (await rowAtTop(page))!;
    assert.ok(row.text.startsWith("Paragraph 13:"), `the scene starts on paragraph 13's row, inside the fold's source (got ${JSON.stringify(row.text)})`);
    near(row.top, -3, "3px above the edge", 1);
    await trapWrites(page);
    await click(page, "Rendered");
    const shape = await foldShape(page);
    assert.ok(shape.closed && !shape.hidden.visible, `the fold is shut in Rendered (got ${JSON.stringify(shape)})`);
    assert.deepEqual(await writes(page), [], `the viewer wrote no scrollTop across the switch: the fold's hidden paragraph has no layout for the place and nothing before it inside the fold lends a box (the wrapper's block is refused), so no seat (before: one write, the phantom box seated)`);
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});

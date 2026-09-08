// The reader's place at BLOCK level, in headless Chromium over the REAL module (plans/markdown-viewer.md Slice 2;
// reader-place.ts; the Slice 2 review's findings on the first cut, which kept a block's top-edge offset and read a Raw
// row as its own place). Each scene puts the reader somewhere the first cut lost them and reads where they land:
//   - partway into a tall block (a 120-line code block, a 60-row table, an html block of twelve paragraphs, a 600px
//     figure, with the Comments aside open too): Rendered, Raw, Rendered comes back within a line (the first cut came
//     back to the block's first line, 900px up the code block; put the table's first Raw row 1300px above the edge,
//     past its last row; and, with the aside open, skipped the wrapped figure for the paragraph after it and threw the
//     reader to the document's top);
//   - a blank Raw row at the top: the paragraph after it is seated where its first text was (the first cut seated the
//     paragraph BEFORE it); the bottom of the document round-trips;
//   - scrollTop 0 comes back to 0 (the views pad differently; the first cut came back to 4);
//   - a `<div hidden>` below the reader, on the search's path: the place holds (the first cut read a block far below);
//   - an html block of two sibling tags before the rewritten block: the replacement is seated (the first cut stepped
//     to the html block's second tag); partway into the two-tag block, the round trip comes back;
//   - a replacement shorter than the reader's depth shows below the edge as the block did; two paragraphs rewritten
//     with twenty inserted above land on the replacement (the first cut fell to the edit's start, at the top); a
//     paragraph or a code block the session appended to keeps its depth in pixels.
// Legs await frames and paint counts, never a timer. Skips LOUDLY without a playwright browser, as the other legs do.
// Synthetic values only: an invented report, /repo/notes-api paths, the placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, openPanel, frames, paintsReach, topBlock, putAtTop, PARA, LONG, REPORT, MT2, type Mode } from "./real-viewer-leg";

const near = (a: number, b: number, what: string, tol = 1.5) => assert.ok(Math.abs(a - b) <= tol, `${what}: ${a} vs ${b}`);
const paras = (a: number, b: number) => Array.from({ length: b - a + 1 }, (_, i) => PARA(a + i)).join("\n\n");
const svg = (w: number, h: number) => "data:image/svg+xml;utf8," + encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}"><rect width="${w}" height="${h}" fill="steelblue"/></svg>`);
const CODE = "```python\n" + Array.from({ length: 120 }, (_, i) => (i === 0 ? "def f1(x):  # line 1 of a long code block" : `    return x + ${i + 1}`)).join("\n") + "\n```";
const TABLE = "| id | name | value |\n|---|---|---|\n" + Array.from({ length: 60 }, (_, i) => `| ${i + 1} | row ${i + 1} | value of row ${i + 1} |`).join("\n");
const HTML12 = "<div>\n" + Array.from({ length: 12 }, (_, i) => `<p>Inner ${i + 1}: ` + "some text inside an html block that wraps once or twice. ".repeat(3) + "</p>").join("\n") + "\n</div>";
const HTML2 = "<p>Html A: a first raw html paragraph, kept by the sanitizer, long enough to wrap once in the pane at nine hundred pixels wide.</p>\n<p>Html B: a second raw html paragraph on the very next line, one html block together with the first, also long enough to wrap.</p>";
const INSERTED = Array.from({ length: 20 }, (_, i) => `Inserted ${i + 1}: new text a session wrote above the reader's place, long enough to wrap once or twice in a narrow pane.`).join("\n\n");
/** The report with block `n` replaced by `block` (a paragraph by default), and, with `above`, twenty paragraphs inserted under the heading. */
const report = (replace: Record<number, string> = {}, above = false) => "# Report\n\n" + (above ? INSERTED + "\n\n" : "")
  + Array.from({ length: 100 }, (_, i) => (i + 1 in replace ? replace[i + 1] : PARA(i + 1))).join("\n\n") + "\n";
const REWRITE = (n: number) => `Rewritten ${n}: the session replaced this paragraph with a shorter one.`;

/** The box of the first element under the body matching `sel` whose text includes `text`, from the body's top edge. */
const box = (page: any, sel: string, text: string) => page.evaluate(([s, t]: [string, string]) => {
  const body = document.querySelector(".fileview-body")!; const br = body.getBoundingClientRect();
  const el = Array.from(body.querySelectorAll(s)).find((e) => (e.textContent || "").includes(t) || (t === "" && true));
  if (!el) return null; const r = el.getBoundingClientRect();
  return { top: Math.round((r.top - br.top) * 10) / 10, bottom: Math.round((r.bottom - br.top) * 10) / 10, height: Math.round(r.height * 10) / 10, scrollTop: body.scrollTop };
}, [sel, text]);
/** Scroll so that element's top sits `extra` px above the body's top edge. */
const scrollInto = (page: any, sel: string, text: string, extra = 0) => page.evaluate(([s, t, x]: [string, string, number]) => {
  const body = document.querySelector(".fileview-body")!;
  const el = Array.from(body.querySelectorAll(s)).find((e) => (e.textContent || "").includes(t))!;
  body.scrollTop += el.getBoundingClientRect().top - body.getBoundingClientRect().top + x;
}, [sel, text, extra]);
const scrollTopOf = (page: any): Promise<number> => page.evaluate(() => document.querySelector(".fileview-body")!.scrollTop);
/** The first Raw row ending below the body's top edge: its text and top. */
const rowAtTop = (page: any) => page.evaluate(() => {
  const body = document.querySelector(".fileview-body")!; const br = body.getBoundingClientRect();
  for (const r of Array.from(body.querySelectorAll("code.hljs .fv-cl"))) { const rr = r.getBoundingClientRect(); if (rr.bottom > br.top + 0.5) return { text: (r.textContent || "").trim().slice(0, 24), top: Math.round((rr.top - br.top) * 10) / 10 }; }
  return null;
});
const click = async (page: any, label: string) => { await page.locator("#romp-fileview .fileview-btn", { hasText: new RegExp("^" + label + "$") }).click(); await frames(page, 3); };
const reload = async (page: any, text: string) => {
  const paints: number = await page.evaluate(() => (window as any).__paints);
  await page.evaluate(([p, t, m]: [string, string, string]) => { (window as any).__docs[p] = t; (window as any).__mtime = m; (window as any).__seam.reload(); }, [REPORT, text, MT2]);
  await paintsReach(page, paints + 1);
  await frames(page, 2);
};
const imagesDone = (page: any) => page.waitForFunction(() => Array.from(document.querySelectorAll(".fileview-md img")).every((i) => (i as HTMLImageElement).complete), null, { timeout: 10000 });

test("in a browser, the real module: partway into a tall code block, table or html block, Rendered to Raw shows the same lines and Rendered again comes back within a line, pane 900 and 380", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const width of [900, 380]) {
      // the code block: the reader 900px in, about line 50
      let { page, errors } = await openViewer(browser, "pane", width, 600, { docs: { [REPORT]: "# Report\n\n" + paras(1, 20) + "\n\n" + CODE + "\n\n" + paras(21, 60) + "\n" } });
      await scrollInto(page, ".fileview-md > pre", "def f1", 900); await frames(page, 2);
      const pre0 = (await box(page, ".fileview-md > pre", "def f1"))!;
      near(pre0.top, -900, `code ${width}: the scene starts 900px into the block`, 2);
      await click(page, "Raw");
      const row = (await rowAtTop(page))!;
      assert.match(row.text, /^return x \+ (4[7-9]|5[0-3])$/, `code ${width}: the Raw top row is about line 50 (got ${JSON.stringify(row.text)}; the block's first line and the fence are 900px up)`);
      await click(page, "Rendered");
      const pre1 = (await box(page, ".fileview-md > pre", "def f1"))!;
      near(pre1.top, pre0.top, `code ${width}: back in Rendered the block sits where it sat (the first cut: its first line at the edge, 900px lost)`, 30);
      assert.deepEqual(errors, [], `code ${width}: no script error`);
      await page.close();
      // the table: row 45 at the edge
      ({ page, errors } = await openViewer(browser, "pane", width, 600, { docs: { [REPORT]: "# Report\n\n" + paras(1, 22) + "\n\n" + TABLE + "\n\n" + paras(23, 60) + "\n" } }));
      await scrollInto(page, ".fileview-md table tr", "value of row 45"); await frames(page, 2);
      const r45 = (await box(page, ".fileview-md table tr", "value of row 45"))!;
      near(r45.top, 0, `table ${width}: row 45 at the edge`, 1);
      await click(page, "Raw");
      const trow = (await rowAtTop(page))!;
      assert.match(trow.text, /^\| (4[2-8]) \| row/, `table ${width}: the Raw top row is about row 45 (got ${JSON.stringify(trow.text)}; the first cut put the table's first row 1300px above the edge, past its last row)`);
      await click(page, "Rendered");
      const r45b = (await box(page, ".fileview-md table tr", "value of row 45"))!;
      near(r45b.top, r45.top, `table ${width}: row 45 back near the edge (the first cut landed the reader below the table)`, 45);
      assert.deepEqual(errors, [], `table ${width}: no script error`);
      await page.close();
    }
    // the html block of twelve paragraphs: Inner 6 at the edge
    const { page, errors } = await openViewer(browser, "pane", 900, 600, { docs: { [REPORT]: "# Report\n\n" + paras(1, 22) + "\n\n" + HTML12 + "\n\n" + paras(23, 60) + "\n" } });
    await scrollInto(page, ".fileview-md > div > p", "Inner 6:"); await frames(page, 2);
    const i6 = (await box(page, ".fileview-md > div > p", "Inner 6:"))!;
    await click(page, "Raw");
    const hrow = (await rowAtTop(page))!;
    assert.match(hrow.text, /^<p>Inner [5-7]:/, `html block: the Raw top row is about Inner 6 (got ${JSON.stringify(hrow.text)})`);
    await click(page, "Rendered");
    const i6b = (await box(page, ".fileview-md > div > p", "Inner 6:"))!;
    near(i6b.top, i6.top, "html block: Inner 6 back near the edge (the first cut: Inner 1 on top, Inner 6 at 234)", 30);
    assert.deepEqual(errors, [], "html block: no script error");
    await page.close();
  });
});

test("in a browser, the real module: 400px into a 600px figure, the round trip comes back to the figure at the same depth, with the Comments aside closed and open (open, the aside's regions layer wraps the picture in a span of its own)", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const DOC = "# Report\n\n" + `<img class="fig" src="${svg(600, 600)}" width="600" height="600">\n\n` + paras(1, 40) + "\n";
    for (const panel of [false, true]) {
      const cell = `aside ${panel ? "open" : "closed"}`;
      const { page, errors } = await openViewer(browser, "pane", 900, 600, { docs: { [REPORT]: DOC } });
      await imagesDone(page);
      if (panel) await openPanel(page);
      await scrollInto(page, "img.fig", "", 400); await frames(page, 2);
      const fig0 = (await box(page, "img.fig", ""))!, p1 = (await box(page, ".fileview-md > p", "Paragraph 1:"))!;
      near(fig0.top, -400, cell + ": the scene starts 400px into the figure", 2);
      await click(page, "Raw");
      const rawRow = (await rowAtTop(page))!;
      assert.match(rawRow.text, /^<img class="fig"/, cell + `: the figure's own Raw row is the top row (got ${JSON.stringify(rawRow.text)}; the first cut scrolled 400px of other rows past it, or seated the heading)`);
      await click(page, "Rendered");
      const fig1 = (await box(page, "img.fig", ""))!, p1b = (await box(page, ".fileview-md > p", "Paragraph 1:"))!;
      near(fig1.top, fig0.top, cell + ": the figure back at the same depth (the first cut: 427px on with the aside closed, the document's top with it open)", 8);
      near(p1b.top, p1.top, cell + ": paragraph 1 where it was", 8);
      assert.deepEqual(errors, [], cell + ": no script error");
      await page.close();
    }
  });
});

test("in a browser, the real module: a blank Raw row at the top seats the paragraph after it where its first text was, pane and chat; the bottom of the document round-trips to the same height", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const mode of ["pane", "chat"] as const) {
      const { page, errors } = await openViewer(browser, mode, 900, 600);
      await putAtTop(page, "Paragraph 40:"); await frames(page, 2);
      await click(page, "Raw");
      // the blank row right after paragraph 40's row, at the body's top edge
      await page.evaluate(() => {
        const body = document.querySelector(".fileview-body")!; const rows = Array.from(body.querySelectorAll("code.hljs .fv-cl"));
        const k = rows.findIndex((e) => (e.textContent || "").indexOf("Paragraph 40:") === 0); const blank = rows[k + 1];
        if ((blank.textContent || "").trim()) throw new Error("the row after paragraph 40 is not blank");
        body.scrollTop += blank.getBoundingClientRect().top - body.getBoundingClientRect().top;
      });
      await frames(page, 3);
      const top = (await rowAtTop(page))!;
      assert.equal(top.text, "", mode + ": the blank row is the top row");
      const p41raw = (await box(page, "code.hljs .fv-cl", "Paragraph 41:"))!;
      assert.ok(p41raw.top > 10 && p41raw.top < 30, mode + `: paragraph 41's row is the first text, one row down (${p41raw.top})`);
      await click(page, "Rendered");
      const p41 = (await box(page, ".fileview-md > p", "Paragraph 41:"))!;
      near(p41.top, p41raw.top, mode + ": paragraph 41 seated where its first text was (the first cut seated paragraph 40 at the edge, paragraph 41 at 48)", 2);
      assert.deepEqual(errors, [], mode + ": no script error");
      await page.close();
    }
    // the bottom of the document, where the last paragraph is cut by the clamp: the round trip comes back from EITHER view, on
    // the chat modal and the pane. From the SHORTER view the taller one seats the block wherever the shorter one showed it.
    // From the TALLER view (Rendered since Slice 3 of plans/markdown-viewer.md: 15px prose in an 80ch column against 12px rows
    // at the pane's width; Raw before it) the seat into the shorter one is clamped at its end, and the way back seats the
    // place the reader had, held across the clamp (file-view.ts seat), not the block the clamp showed: the Slice 3 tree read
    // the clamped body back and came back one paragraph early, the top block changed and its edge 65 to 107px lower (the
    // Slice 3 review); before the slice the same clamp drifted the other direction by up to 264px.
    for (const [mode, raw] of [["chat", false], ["chat", true], ["pane", false], ["pane", true]] as [Mode, boolean][]) {
      const cell = `bottom, ${mode}, from ${raw ? "Raw" : "Rendered"}`;
      const { page, errors } = await openViewer(browser, mode, 900, 600, { raw });
      await page.evaluate(() => { const b = document.querySelector(".fileview-body")!; b.scrollTop = b.scrollHeight; }); await frames(page, 3);
      const before = (await topBlock(page))!;
      assert.equal(before.view, raw ? "raw" : "rendered", cell + ": the scene opens in the view named");
      await click(page, raw ? "Rendered" : "Raw"); await click(page, raw ? "Raw" : "Rendered");
      const after = (await topBlock(page))!;
      assert.equal(after.text, before.text, cell + ": the same top block (the Slice 3 tree: Paragraph 93 for 94 from Rendered)");
      near(after.top, before.top, cell + ": at the same height (the first cut moved it 54px; the Slice 3 tree 65 to 107px from Rendered)");
      near(after.scrollTop, before.scrollTop, cell + ": the same scrollTop", 1);
      assert.deepEqual(errors, [], cell + ": no script error");
      await page.close();
    }
  });
});

test("in a browser, the real module: at scrollTop 0 the Rendered/Raw round trip comes back to scrollTop 0 with the heading under its own padding, pane and chat; Raw first too", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const mode of ["pane", "chat"] as const) {
      const { page, errors } = await openViewer(browser, mode, 900, 600);
      const h0 = (await box(page, ".fileview-md > h1", "Report"))!;
      assert.equal(h0.scrollTop, 0);
      await click(page, "Raw");
      assert.equal(await scrollTopOf(page), 0, mode + ": Raw at the top");
      await click(page, "Rendered");
      const h1 = (await box(page, ".fileview-md > h1", "Report"))!;
      assert.equal(h1.scrollTop, 0, mode + ": back at scrollTop 0 (the first cut: 4)");
      assert.equal(h1.top, h0.top, mode + ": the heading under the Rendered view's own padding");
      assert.deepEqual(errors, [], mode + ": no script error");
      await page.close();
    }
    const { page, errors } = await openViewer(browser, "pane", 900, 600, { raw: true });
    assert.equal(await scrollTopOf(page), 0);
    await click(page, "Rendered");
    assert.equal(await scrollTopOf(page), 0, "raw first: Rendered at the top");
    assert.equal((await box(page, ".fileview-md > h1", "Report"))!.top, 14, "the heading under the 14px padding");
    await click(page, "Raw");
    assert.equal(await scrollTopOf(page), 0, "and Raw at the top again");
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});

test("in a browser, the real module: a `<div hidden>` below the reader on the search's path does not move the place: the round trip and a reload that grows a paragraph between keep paragraph 20", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    // 102 top-level children: the heading, 100 paragraphs, the hidden div after paragraph 50 (child index 51, the search's first probe)
    const withHidden = (grow30: boolean) => "# Report\n\n" + Array.from({ length: 100 }, (_, i) => {
      let p = PARA(i + 1);
      if (grow30 && i + 1 === 30) p += " " + "more words a session added to paragraph thirty so it wraps three lines further down the column ".repeat(3).trim() + ".";
      return i + 1 === 50 ? p + "\n\n<div hidden>hidden note text</div>" : p;
    }).join("\n\n") + "\n";
    const { page, errors } = await openViewer(browser, "pane", 900, 600, { docs: { [REPORT]: withHidden(false) } });
    const info = await page.evaluate(() => { const kids = Array.from(document.querySelector(".fileview-md")!.children); const hi = kids.findIndex((k) => k.hasAttribute("hidden")); const r = kids[hi].getBoundingClientRect(); return { kids: kids.length, hi, zero: r.width === 0 && r.height === 0 }; });
    assert.deepEqual(info, { kids: 102, hi: 51, zero: true }, "the fixture: 102 children, the hidden div at 51 with no box");
    await putAtTop(page, "Paragraph 20:"); await frames(page, 2);
    const before = (await topBlock(page))!;
    assert.equal(before.text, "Paragraph 20:");
    await click(page, "Raw");
    const raw = (await topBlock(page))!;
    assert.equal(raw.text, "Paragraph 20:", "Raw: paragraph 20's row on top (the first cut: a blank row 1000px on)");
    await click(page, "Rendered");
    const back = (await topBlock(page))!;
    assert.equal(back.text, "Paragraph 20:", "back: paragraph 20 (the first cut: paragraph 27)");
    near(back.top, before.top, "at the same height");
    await reload(page, withHidden(true));
    const grown = (await topBlock(page))!;
    assert.equal(grown.text, "Paragraph 20:", "after a reload that grew paragraph 30: still paragraph 20 (the first cut: paragraph 21)");
    near(grown.top, before.top, "at the same height after the reload");
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});

test("in a browser, the real module: an html block of two sibling tags right before the rewritten block: the replacement is seated, not the block's second tag; partway into the two-tag block, the round trip comes back", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const before = report({ 39: HTML2 });
    for (const above of [false, true]) {
      const cell = above ? "rewritten, twenty inserted above" : "rewritten in place";
      const { page, errors } = await openViewer(browser, "pane", 900, 600, { docs: { [REPORT]: before } });
      await putAtTop(page, "Paragraph 40:"); await frames(page, 2);
      const b = (await topBlock(page))!;
      assert.equal(b.text, "Paragraph 40:");
      await reload(page, report({ 39: HTML2, 40: REWRITE(40) }, above));
      const a = (await topBlock(page))!;
      assert.equal(a.text, "Rewritten 40:", cell + ": the replacement on top (the first cut: the html block's second tag, Html B)");
      near(a.top, b.top, cell + ": at the same height");
      assert.deepEqual(errors, [], cell + ": no script error");
      await page.close();
    }
    // Html B at the edge, Html A above it: one block partway in, kept through the round trip
    const { page, errors } = await openViewer(browser, "pane", 900, 600, { docs: { [REPORT]: before } });
    await scrollInto(page, ".fileview-md > p", "Html B:"); await frames(page, 2);
    const hb = (await box(page, ".fileview-md > p", "Html B:"))!;
    await click(page, "Raw");
    const row = (await rowAtTop(page))!;
    assert.match(row.text, /^<p>Html B:/, `the Raw top row is Html B's line (got ${JSON.stringify(row.text)})`);
    await click(page, "Rendered");
    const hb2 = (await box(page, ".fileview-md > p", "Html B:"))!;
    near(hb2.top, hb.top, "Html B back at the edge", 5);
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});

test("in a browser, the real module: a replacement shorter than the reader's depth shows below the edge as the block did; paragraphs 39 and 40 rewritten with twenty inserted above land on the replacement; a paragraph and a code block the session appended to keep their depth in pixels", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    // 30px into paragraph 40 (two lines at 900px), replaced by one line
    let { page, errors } = await openViewer(browser, "pane", 900, 600);
    await putAtTop(page, "Paragraph 40:"); await page.evaluate(() => { document.querySelector(".fileview-body")!.scrollTop += 30; }); await frames(page, 2);
    const p40 = (await box(page, ".fileview-md > p", "Paragraph 40:"))!;
    near(p40.top, -30, "the scene starts 30px into paragraph 40", 1);
    await reload(page, report({ 40: REWRITE(40) }));
    const rw = (await box(page, ".fileview-md > p", "Rewritten 40:"))!;
    assert.ok(rw.height < 25, `the replacement is one line (${rw.height})`);
    // as much of the replacement shows below the edge as showed of paragraph 40, and no further down than the edge: a
    // one-line replacement shorter than what showed sits at the edge, whole (three lines showed 42px at 900px since Slice 3 of
    // plans/markdown-viewer.md made the paragraph three lines; two lines showed 12px before, which the replacement matched)
    near(rw.bottom, Math.min(p40.bottom, rw.height), "the replacement's bottom where paragraph 40's was, or at the edge when it is shorter than what showed (the first cut: wholly above the edge, unseen)", 2);
    assert.equal((await topBlock(page))!.text, "Rewritten 40:", "the replacement is the top block");
    assert.deepEqual(errors, [], "shorter: no script error");
    await page.close();
    // paragraphs 39 and 40 rewritten, twenty inserted above: the block after (41) places the replacement
    ({ page, errors } = await openViewer(browser, "pane", 900, 600));
    await putAtTop(page, "Paragraph 40:"); await frames(page, 2);
    const b0 = (await topBlock(page))!;
    await reload(page, report({ 39: REWRITE(39), 40: REWRITE(40) }, true));
    const a0 = (await topBlock(page))!;
    assert.equal(a0.text, "Rewritten 40:", "the rewritten paragraph 40 on top (the first cut: Inserted 1, the document's top)");
    near(a0.top, b0.top, "at the same height");
    assert.deepEqual(errors, [], "two rewritten: no script error");
    await page.close();
    // a paragraph the session appended a sentence to: the reader 30px in stays 30px in (not the same fraction of a taller block)
    ({ page, errors } = await openViewer(browser, "pane", 900, 600));
    await putAtTop(page, "Paragraph 40:"); await page.evaluate(() => { document.querySelector(".fileview-body")!.scrollTop += 30; }); await frames(page, 2);
    const p40a = (await box(page, ".fileview-md > p", "Paragraph 40:"))!;
    await reload(page, report({ 40: PARA(40) + " " + "And a sentence the session appended to the paragraph under the reader's eye, long enough to wrap. ".repeat(4).trim() }));
    const p40b = (await box(page, ".fileview-md > p", "Paragraph 40:"))!;
    assert.ok(p40b.height > p40a.height + 40, `paragraph 40 grew (${p40a.height} to ${p40b.height})`);
    near(p40b.top, p40a.top, "its top edge stays 30px above the edge", 1.5);
    assert.deepEqual(errors, [], "appended paragraph: no script error");
    await page.close();
    // a code block the session appended ninety lines to: line 5 stays at the edge
    const code = (n: number) => "```text\n" + Array.from({ length: n }, (_, i) => `line ${i + 1} of the block: alpha beta gamma`).join("\n") + "\n```";
    ({ page, errors } = await openViewer(browser, "pane", 900, 600, { docs: { [REPORT]: "# Report\n\n" + paras(1, 5) + "\n\n" + code(10) + "\n\n" + paras(6, 40) + "\n" } }));
    await scrollInto(page, ".fileview-md > pre", "line 1 of", 90); await frames(page, 2);
    const pre0 = (await box(page, ".fileview-md > pre", "line 1 of"))!;
    near(pre0.top, -90, "the scene starts 90px into the block", 1);
    await reload(page, "# Report\n\n" + paras(1, 5) + "\n\n" + code(100) + "\n\n" + paras(6, 40) + "\n");
    const pre1 = (await box(page, ".fileview-md > pre", "line 1 of"))!;
    assert.ok(pre1.height > pre0.height * 5, "the block grew tenfold");
    near(pre1.top, pre0.top, "the block's top stays 90px above the edge: the same line at the edge", 1.5);
    assert.deepEqual(errors, [], "appended code: no script error");
    await page.close();
  });
});

// A figure that failed to load says so beside itself, in headless Chromium over the REAL viewer (plans/markdown-viewer.md
// Slice 7, item 2; real-viewer-leg.ts serves the page, and its `serve` hook answers the browser's own requests for the note's
// figures at the kernel's /file route: a missing file with the kernel's 404, a text file named as a figure with a 200 the
// decoder refuses, an svg with image/svg+xml, which loads). The two failures fire the img's `error` event with no status on it,
// and the viewer's capture-phase listener parks `span.fv-figerr[data-fv-figerr]` after each img naming FIGURE_FAILED, the
// authored src and the alt; the loaded figure gets none; the heading holding a failed figure keeps an Outline row reading
// the alt and the heading's words alone. Under styles.css (the Files pane and the chat modal) and feed.css the label wears
// unit B's rule (inline-flex, a dashed border) and has a box. On the pane: a Raw switch from the failed figure's paragraph at
// the top seats on that paragraph's row (reader-place.ts skips the label as a control, so the paragraph still pairs with its
// source; before the skip the label's words made the pairing refuse); with the Comments panel open every figure takes a
// regions layer (the count equals the img count, the wrap holding THE img), each label stands after its figure's wrap, and a
// comment on the paragraph holding a failed figure paints its highlight (anchor-map.ts skips the label as a control). In the
// chat modal the page's own heal (preview.ts installMdImgHeal, installed before the open through RVL's `before` hook, with
// render.ts's romp:wsup drivers) re-fetches every failed figure on a dispatched romp:wsup; each fails again and its one label
// is rewritten, never doubled. Every wait is for the figures' own settling (`complete`) or the panel's paint, never a timer.
// Skips LOUDLY without a playwright browser (CI installs none), as the other legs do. Before item 2: no label anywhere (red at
// the first label assertion over a git archive of the base, whose real-viewer-leg has no `serve` hook either). Synthetic
// values only: an invented report, /repo/notes-api paths, the placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, openPanel, frames, topBlock, putAtTop, PARA, ROOT, REPORT, type Mode, type Served } from "./real-viewer-leg";

const FIGS = ROOT + "/docs/figs/";
const SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 20" width="40" height="20"><rect width="40" height="20" fill="#888"/></svg>';
/** The kernel's /file answers for the note's figures, as the browser asks for them (the page's fetch stub never sees an <img>'s request). */
const serve = (u: URL): Served | null => {
  if (u.pathname !== "/file") return null;
  const p = u.searchParams.get("path") || "";
  if (p === FIGS + "bad.png") return { status: 200, type: "text/plain; charset=utf-8", body: "not a picture: a text file named as one" };
  if (p === FIGS + "ok.svg") return { status: 200, type: "image/svg+xml", body: SVG };
  return { status: 404, type: "text/plain; charset=utf-8", body: "not found: " + p };
};
const LEAD = Array.from({ length: 30 }, (_, i) => PARA(i + 1)).join("\n\n");
const TAIL = Array.from({ length: 30 }, (_, i) => PARA(i + 31)).join("\n\n");
/** The note: thirty paragraphs, then a paragraph holding a missing figure, one holding a text file named as a figure (no alt), one
 *  holding an svg that loads, a heading holding a missing figure, and thirty more paragraphs (so the body scrolls far enough on
 *  either side for the figure's paragraph to reach the top edge). */
const NOTE = "# Report\n\n" + LEAD + "\n\nFigure one: ![p95](figs/missing.png) shows the week.\n\nBad bytes: ![](figs/bad.png) here.\n\nGood: ![ok](figs/ok.svg) loads.\n\n## ![Figure 3](figs/missing.png) detail\n\n" + TAIL + "\n";
const T0 = 1757145600000;
/** A stored comment on the paragraph holding the missing figure (the shape file-view-print-marks-browser.test.ts seeds). */
const COMMENTS = [{ id: T0 + "-1", author: "you", ts: T0, body: "Note on the figure's paragraph.", anchor: { quote: "shows the week", prefix: ") ", suffix: "." }, replies: [], resolved: false }];

type Fig = { dest: string | null; alt: string | null; complete: boolean; natural: number; label: string | null; labelClass: string | null; display: string | null; border: string | null; width: number; parent: string; hasOnerror: boolean };
/** Every figure of the Rendered box in order, with the label standing after it (or after the regions layer's wrap around it) when one
 *  does; `parent` is the block the author put the figure in, read through the layer's wrap when the panel has wrapped it. */
const figures = (page: any): Promise<{ figs: Fig[]; labels: number }> => page.evaluate(() => {
  const md = document.querySelector(".fileview-md") as HTMLElement;
  const figs = (Array.from(md.querySelectorAll("img")) as HTMLImageElement[]).map((i) => {
    const anchor = i.parentElement && i.parentElement.classList.contains("fc-imgwrap") ? i.parentElement : i;
    const n = anchor.nextSibling as Element | null;
    const lab = n && n.nodeType === 1 && n.hasAttribute("data-fv-figerr") ? n as HTMLElement : null;
    const cs = lab ? getComputedStyle(lab) : null;
    return { dest: i.getAttribute("data-fv-src"), alt: i.getAttribute("alt"), complete: i.complete, natural: i.naturalWidth, label: lab ? lab.textContent : null, labelClass: lab ? lab.className : null,
      display: cs ? cs.display : null, border: cs ? cs.borderTopStyle : null, width: lab ? lab.getBoundingClientRect().width : 0, parent: anchor.parentElement ? anchor.parentElement.tagName : "", hasOnerror: i.onerror !== null };
  });
  return { figs, labels: md.querySelectorAll("[data-fv-figerr]").length };
});
/** Wait until every figure of the box has settled (loaded or failed): the img's own `complete`, never a timer. */
const settled = (page: any): Promise<unknown> => page.waitForFunction(() => { const imgs = Array.from(document.querySelectorAll(".fileview-md img")) as HTMLImageElement[]; return imgs.length >= 4 && imgs.every((i) => i.complete); }, null, { timeout: 15000 });
const FAILED = "Image failed to load:";   // FIGURE_FAILED (file-view.ts, contract C5)

function assertLabels(figs: Fig[], labels: number, what: string): void {
  assert.equal(figs.length, 4, what + ": four figures");
  assert.equal(labels, 3, what + ": three labels in the box, one per failed figure (before item 2: none)");
  assert.deepEqual(figs.map((f) => f.label), [FAILED + " figs/missing.png (p95)", FAILED + " figs/bad.png", null, FAILED + " figs/missing.png (Figure 3)"],
    what + ": the missing file's label names its authored src and alt; the text file's names its src alone (no alt); the svg that loaded has none; the heading's names its alt");
  assert.deepEqual(figs.map((f) => f.natural > 0), [false, false, true, false], what + ": the svg alone decoded");
  assert.ok(figs.every((f) => f.complete), what + ": every figure settled");
  assert.ok(figs.every((f) => !f.hasOnerror), what + ": img.onerror is never set (the chat page's heal skips an img with one)");
  assert.deepEqual(figs.map((f) => f.parent), ["P", "P", "P", "H2"], what + ": every img stands where the author put it");
  for (const f of figs.filter((x) => x.label !== null)) {
    assert.equal(f.labelClass, "fv-figerr", what + ": the label wears fv-figerr");
    assert.equal(f.display, "inline-flex", what + ": the sheet dresses it (unit B's rule under .fileview-md)");
    assert.equal(f.border, "dashed", what + ": in the gate's shape, a dashed border");
    assert.ok(f.width > 20, what + ": the label has a box: " + f.width);
  }
}

test("in a browser: a missing figure and a text file named as a figure each wear a label naming their authored src (and the alt when there is one), the svg that loads wears none, the img stays untouched, the heading's Outline row reads the alt and the words alone; on the pane a Raw switch from the failed figure's paragraph seats on its row; with the Comments panel open every figure takes a layer, the labels follow the wraps and a comment on the failed figure's paragraph paints; under styles.css (pane, chat) and feed.css", { timeout: 300000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const mode of ["pane", "chat", "feed"] as Mode[]) {
      const { page, errors } = await openViewer(browser, mode, 900, 700, { docs: { [REPORT]: NOTE }, serve });
      await settled(page);
      await frames(page, 2);
      const first = await figures(page);
      assertLabels(first.figs, first.labels, mode);
      if (mode === "pane") {
        // the Outline: the heading holding the failed figure reads its alt and its words, never the label's (headingWords skips the mark)
        const rows = await page.evaluate(() => {
          const btn = (Array.from(document.querySelectorAll(".fileview-acts button")) as HTMLButtonElement[]).find((b) => b.textContent === "Outline")!;
          btn.click();
          const rows = Array.from(document.querySelectorAll(".fileview-outline-row")).map((r) => r.textContent);
          btn.click();
          return rows;
        });
        assert.deepEqual(rows, ["Report", "Figure 3 detail"], "the Outline's rows: the h1, and the h2 as its figure's alt plus its words, without the label");
        assert.equal(await page.evaluate(() => !!document.querySelector(".fileview-outline")), false, "the popover closed again");
        // the Raw switch from the failed figure's paragraph at the top: the reader's place pairs the paragraph with its source
        // (the label is a control the place skips) and seats its Raw row at the top
        await putAtTop(page, "Figure one");
        const before = await topBlock(page);
        assert.ok(before && before.view === "rendered" && before.text.startsWith("Figure one"), "the failed figure's paragraph at the top: " + JSON.stringify(before));
        await page.evaluate(() => { (Array.from(document.querySelectorAll(".fileview-acts button")) as HTMLButtonElement[]).find((b) => b.textContent === "Raw")!.click(); });
        await page.waitForFunction(() => !!document.querySelector(".fileview-body .fv-cl"), null, { timeout: 10000 });
        await frames(page, 2);
        const after = await topBlock(page);
        assert.ok(after && after.view === "raw", "the Raw view: " + JSON.stringify(after));
        assert.ok(after!.text.startsWith("Figure one:"), "the paragraph's own row at the top (the label's words did not break the pairing): " + JSON.stringify(after));
        await page.evaluate(() => { (Array.from(document.querySelectorAll(".fileview-acts button")) as HTMLButtonElement[]).find((b) => b.textContent === "Rendered")!.click(); });
        await page.waitForFunction(() => !!document.querySelector(".fileview-md > p"), null, { timeout: 10000 });
        await settled(page);
        await frames(page, 2);
        const again = await figures(page);
        assertLabels(again.figs, again.labels, "pane, after the round trip (the listener is the open's, not the paint's)");
        // the Comments panel over the failed figures: a layer per figure, the labels after the wraps, a highlight in the paragraph
        await page.evaluate((cs: unknown[]) => { const s = (window as any).__status; s.store.comments = cs; s.unsent.comments = (cs as Array<{ id: string }>).map((c) => c.id); }, COMMENTS);
        await openPanel(page);
        await page.waitForFunction(() => document.querySelectorAll(".fileview-md .fc-hl:not(img)").length > 0, null, { timeout: 10000 });
        await frames(page, 2);
        const panel = await page.evaluate(() => {
          const md = document.querySelector(".fileview-md") as HTMLElement;
          const imgs = Array.from(md.querySelectorAll("img")) as HTMLImageElement[];
          const wraps = Array.from(md.querySelectorAll(".fc-imgwrap"));
          const p = imgs[0].closest("p")!;
          const mark = p.querySelector(".fc-hl:not(img)") as HTMLElement | null;
          return {
            imgs: imgs.length, wraps: wraps.length, wrapped: imgs.every((i) => !!i.parentElement && i.parentElement.classList.contains("fc-imgwrap")),
            labels: md.querySelectorAll("[data-fv-figerr]").length,
            afterWrap: imgs.filter((_, k) => k !== 2).every((i) => { const n = i.parentElement!.nextSibling as Element | null; return !!n && n.nodeType === 1 && n.hasAttribute("data-fv-figerr"); }),
            inWrap: wraps.some((w) => w.querySelector("[data-fv-figerr]")),
            markText: mark ? mark.textContent : null, markWidth: mark ? mark.getBoundingClientRect().width : 0,
          };
        });
        assert.equal(panel.wraps, panel.imgs, "a regions layer per figure: the wrap count equals the img count (renderedImages() lists the failed figures too)");
        assert.equal(panel.imgs, 4); assert.ok(panel.wrapped, "the layer wraps THE img");
        assert.equal(panel.labels, 3, "the labels stand");
        assert.ok(panel.afterWrap, "each failed figure's label is its wrap's next sibling now (the wrap went in before the img and took it)");
        assert.equal(panel.inWrap, false, "no label inside a wrap");
        assert.equal(panel.markText, "shows the week", "the comment on the paragraph holding the failed figure painted its highlight (the map skips the label as a control)");
        assert.ok(panel.markWidth > 0, "…with a box");
        const post = await figures(page);
        assertLabels(post.figs, post.labels, "pane, panel open");
      }
      assert.deepEqual(errors, [], mode + ": no uncaught page error");
      await page.close();
    }
  });
});

test("in a browser, the chat modal: the page's heal (installMdImgHeal, before the open) registers each failed figure at its error event and a dispatched romp:wsup re-fetches them; each fails again and its one label is rewritten in place, never doubled", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const before = async (page: any): Promise<void> => {
      await page.evaluate(() => {
        const w = window as any;
        w.__imgErrors = 0;
        document.addEventListener("error", (e) => { const t = e.target as Element | null; if (t && t.nodeType === 1 && t.tagName === "IMG") w.__imgErrors++; }, true);
        w.FV.installMdImgHeal();                                                            // render.ts installs it once at load
        window.addEventListener("romp:wsup", () => { w.FV.retryFailedPreviews(); w.FV.refreshSettledPreviews(); });   // render.ts's romp:wsup line, less the path-image heal
      });
    };
    const { page, errors } = await openViewer(browser, "chat", 900, 700, { docs: { [REPORT]: NOTE }, serve, before });
    await settled(page);
    await frames(page, 2);
    const first = await figures(page);
    assertLabels(first.figs, first.labels, "chat, first paint");
    const e1: number = await page.evaluate(() => (window as any).__imgErrors);
    assert.equal(e1, 3, "three error events, one per failed figure");
    await page.evaluate(() => { window.dispatchEvent(new Event("romp:wsup")); });   // the kernel's socket came back: the heal re-fetches every failed picture
    await page.waitForFunction((n: number) => (window as any).__imgErrors >= n, e1 + 3, { timeout: 15000 });   // each retry failed again: the events, never a timer
    await settled(page);
    await frames(page, 2);
    const e2: number = await page.evaluate(() => (window as any).__imgErrors);
    assert.equal(e2, 6, "three retries, three more errors");
    const second = await figures(page);
    assertLabels(second.figs, second.labels, "chat, after the heal's retry");
    assert.deepEqual(second.figs.map((f) => f.label), first.figs.map((f) => f.label), "the same three labels, rewritten in place");
    assert.deepEqual(errors, [], "no uncaught page error");
    await page.close();
  });
});

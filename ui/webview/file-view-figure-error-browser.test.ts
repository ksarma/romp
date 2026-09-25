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
// render.ts's romp:wsup drivers) PARKS each failed figure at the same error event the viewer labels (T291c, upstream's model:
// the src leaves into data-md-src, the img wears md-img-failed, the browser shows the alt text; md-img-park.test.ts is the
// twin), and a dispatched romp:wsup probes each parked URL off the DOM through a detached Image; the probes fail again, no
// error reaches an img on the page, and the three labels stand unchanged, never rewritten or doubled. Every wait is for the
// figures' own settling (`complete`), the probes' own events or the panel's paint, never a timer.
// Skips LOUDLY without a playwright browser (in CI the Test step runs before the job's Chromium install, so the leg skips there; the launch is real-viewer-leg.ts's inBrowser, the shared helper), as the other legs do. Before item 2: no label anywhere (red at
// the first label assertion over a git archive of the base, whose real-viewer-leg has no `serve` hook either). Synthetic
// values only: an invented report, /repo/notes-api paths, the placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as http from "node:http";
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
 *  does, read past the figure's "Open the picture" control when that stands at the anchor's side (the link-navigation follow-on's L3:
 *  a local figure wears one, and the viewer's figureLabelAfter reads past it the same way); `parent` is the block the author put the
 *  figure in, read through the layer's wrap when the panel has wrapped it. */
const figures = (page: any): Promise<{ figs: Fig[]; labels: number }> => page.evaluate(() => {
  const md = document.querySelector(".fileview-md") as HTMLElement;
  const figs = (Array.from(md.querySelectorAll("img")) as HTMLImageElement[]).map((i) => {
    const anchor = i.parentElement && i.parentElement.classList.contains("fc-imgwrap") ? i.parentElement : i;
    let n = anchor.nextSibling as Element | null;
    if (n && n.nodeType === 1 && n.hasAttribute("data-fv-figopen")) n = n.nextSibling as Element | null;
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
            afterWrap: imgs.filter((_, k) => k !== 2).every((i) => { let n = i.parentElement!.nextSibling as Element | null; if (n && n.nodeType === 1 && n.hasAttribute("data-fv-figopen")) n = n.nextSibling as Element | null; return !!n && n.nodeType === 1 && n.hasAttribute("data-fv-figerr"); }),   // past the figure's Open control, which stands right after the wrap
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

type Park = { src: boolean; parked: boolean; mdSrc: string | null; mdRoute: string | null; mdPath: string | null; alt: string | null };
/** Every figure of the Rendered box in order, as the page's heal leaves it: whether a `src` attribute stands, whether it wears
 *  md-img-failed, the URL parked in data-md-src (the /file URL the browser asked for) with its route and its `path`, and the alt. */
const parks = (page: any): Promise<Park[]> => page.evaluate(() => (Array.from(document.querySelectorAll(".fileview-md img")) as HTMLImageElement[]).map((i) => {
  const u = i.getAttribute("data-md-src");
  let mdRoute: string | null = null, mdPath: string | null = null;
  if (u) { try { const url = new URL(u); mdRoute = url.pathname; mdPath = url.searchParams.get("path"); } catch { mdRoute = u; } }
  return { src: i.hasAttribute("src"), parked: i.classList.contains("md-img-failed"), mdSrc: u, mdRoute, mdPath, alt: i.getAttribute("alt") };
}));

test("in a browser, the chat modal: the page's heal (installMdImgHeal, before the open) parks each failed figure at its error event beside the viewer's label (no src, md-img-failed, the URL in data-md-src; the svg that loaded is untouched), and a dispatched romp:wsup probes each parked URL off the DOM: the probes fail again, no error reaches an img on the page, the figures stay parked as they were and the three labels stand, the same elements with the same words, never rewritten or doubled", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const before = async (page: any): Promise<void> => {
      await page.evaluate(() => {
        const w = window as any;
        w.__imgErrors = 0;
        document.addEventListener("error", (e) => { const t = e.target as Element | null; if (t && t.nodeType === 1 && t.tagName === "IMG") w.__imgErrors++; }, true);
        // the heal's probes are `new Image()` (preview.ts probeMdImgUrl, the bundle's one Image constructor): a counting wrapper around
        // the real constructor records each probe and its settling (its own load or error), so the wait below is for the probes'
        // events, never a timer; the probes stay real elements and the page is otherwise as the chat page has it
        const RealImage = w.Image;
        w.__probes = [];
        w.Image = function () { const i = new RealImage(); i.__settled = false; i.addEventListener("load", () => { i.__settled = true; }); i.addEventListener("error", () => { i.__settled = true; }); w.__probes.push(i); return i; };
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
    // the park (preview.ts parkMdImg, at the same error event the viewer's body listener labels; document's capture listener runs
    // first): the failed figure keeps no src, wears md-img-failed and carries the /file URL the browser asked for in data-md-src;
    // the svg that loaded is untouched; the alt text stands on every img, the browser's own caption beside the viewer's label
    const p1 = await parks(page);
    assert.deepEqual(p1.map((p) => p.src), [false, false, true, false], "first paint: the three failed figures are parked, no src attribute (the browser fetches nothing and shows the alt text); the svg keeps its src");
    assert.deepEqual(p1.map((p) => p.parked), [true, true, false, true], "…each wears md-img-failed");
    assert.deepEqual(p1.map((p) => p.mdRoute), ["/file", "/file", null, "/file"], "…and data-md-src keeps the URL the browser asked for, at the kernel's /file route");
    assert.deepEqual(p1.map((p) => p.mdPath), [FIGS + "missing.png", FIGS + "bad.png", null, FIGS + "missing.png"], "…naming the figure's path, for the heal");
    assert.deepEqual(p1.map((p) => p.alt), first.figs.map((f) => f.alt), "the alt text is untouched by the park");
    assert.equal(await page.evaluate(() => (window as any).__probes.length), 0, "no probe before a kernel message or a reconnect: the listener parks and arms the budget alone");
    await page.evaluate(() => { Array.from(document.querySelectorAll(".fileview-md [data-fv-figerr]")).forEach((l, k) => { (l as any).__mark = k + 1; }); });   // the three label elements, numbered in order
    // the kernel's socket came back: render.ts's line runs both drivers, and each probes OFF the DOM (retryFailedPreviews: the bounded
    // per-message probe of a URL the kernel serves; refreshSettledPreviews: the reconnect probe of every remembered URL). The dispatch
    // is synchronous, so the probes exist when it returns; how many each driver fires per URL is md-img-park.test.ts's claim
    const fired: { src: string; connected: boolean }[] = await page.evaluate(() => { window.dispatchEvent(new Event("romp:wsup")); return (window as any).__probes.map((p: HTMLImageElement) => ({ src: p.src, connected: p.isConnected })); });
    const parkedUrls = Array.from(new Set(p1.map((p) => p.mdSrc).filter((u): u is string => !!u))).sort();
    assert.equal(parkedUrls.length, 2, "two parked URLs: missing.png (twice on the page) and bad.png");
    assert.deepEqual(Array.from(new Set(fired.map((f) => f.src))).sort(), parkedUrls, "the heal probes each parked URL, and nothing else");
    assert.ok(fired.length >= parkedUrls.length && fired.every((f) => !f.connected), "every probe is a detached Image, off the DOM: " + fired.length + " probes");
    await page.waitForFunction(() => { const w = window as any; return w.__probes.length > 0 && w.__probes.every((p: any) => p.__settled); }, null, { timeout: 15000 });   // the probes' own load or error events, never a timer
    await settled(page);
    await frames(page, 2);
    const loaded: number = await page.evaluate(() => (window as any).__probes.filter((p: any) => p.naturalWidth > 0).length);
    assert.equal(loaded, 0, "every probe failed again (the 404, and the text file the decoder refuses)");
    const e2: number = await page.evaluate(() => (window as any).__imgErrors);
    assert.equal(e2, 3, "no further error event on an img of the page: a probe is detached, so its error never reaches document or the viewer's body listener, and a parked img has no src to re-fetch (under the retired in-DOM re-fetch: three more here)");
    const p2 = await parks(page);
    assert.deepEqual(p2, p1, "a failed probe changes nothing on the page: each failed figure stays parked exactly as it was, the svg untouched");
    const second = await figures(page);
    assertLabels(second.figs, second.labels, "chat, after the heal's probes");
    assert.deepEqual(second.figs.map((f) => f.label), first.figs.map((f) => f.label), "the same three labels, the same words");
    const marks: number[] = await page.evaluate(() => Array.from(document.querySelectorAll(".fileview-md [data-fv-figerr]")).map((l) => (l as any).__mark || 0));
    assert.deepEqual(marks, [1, 2, 3], "…the same three label elements in place, none replaced and none added: no second in-DOM error reached the viewer's listener, so nothing rewrote or doubled them");
    assert.deepEqual(errors, [], "no uncaught page error");
    await page.close();
  });
});

// ── the Slice 7 review's round 1: the source the label names, and where it goes beside a link ─────────────────────────────
/** A real 1x1 PNG, for a figure that IS there: the browser decodes it (naturalWidth 1). */
const PNG = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==", "base64");
/** Every /file ask the browser made, by its figs/ leaf. */
const asked: string[] = [];
/** The kernel's answers for the round 1 note: plot.png is there (the PNG), everything else 404s. */
const serve2 = (u: URL): Served | null => {
  if (u.pathname !== "/file") return null;
  const p = u.searchParams.get("path") || "";
  asked.push(p.startsWith(FIGS) ? p.slice(FIGS.length) : p);
  if (p === FIGS + "plot.png") return { status: 200, type: "image/png", body: PNG as unknown as string };
  return { status: 404, type: "text/plain; charset=utf-8", body: "not found: " + p };
};
/** An inline image whose payload the decoder refuses: the PNG signature, then base64 that decodes to nothing a decoder accepts. */
const INLINE = "data:image/png;base64,iVBORw0KGgo" + "A".repeat(3000);
/** The note: a <picture> whose webp source the browser picks (missing) over an img src that is there; an img with its own srcset
 *  (both candidates missing, the 1x picked on a 1x display) over the same src; an inline data: figure the decoder refuses; a
 *  linked figure (missing); the file that is there as a plain figure, the control. */
const NOTE2 = ["# Report", "",
  '<picture><source srcset="figs/dark.webp" type="image/webp"><img src="figs/plot.png" alt="plot"></picture>', "",
  '<img srcset="figs/missing-2x.png 2x, figs/missing-1x.png 1x" src="figs/plot.png" alt="dense">', "",
  "Inline: ![inline](" + INLINE + ") pasted.", "",
  "After the inline figure: this paragraph follows it.", "",
  "Link: [![linked](figs/missing5.png)](https://example.com/x) tail.", "",
  "Plain: ![plain](figs/plot.png) loads.", ""].join("\n");
type Fig2 = { alt: string | null; asked: string; natural: number; label: string | null; labelParent: string | null; inLink: boolean; cursor: string | null; display: string | null; labelHeight: number; labelWidth: number };
/** Every figure of the box in order: the leaf of the URL the browser asked for (currentSrc), whether it decoded, and the label standing
 *  after its anchor (the img, its <picture>, or the <a> holding it alone) with where it sits and how it is drawn. */
const figures2 = (page: any): Promise<{ figs: Fig2[]; labels: number }> => page.evaluate((figs: string) => {
  const md = document.querySelector(".fileview-md") as HTMLElement;
  const leaf = (u: string): string => { const m = /[?&]path=([^&]*)/.exec(u); if (m) { const p = decodeURIComponent(m[1]); return p.startsWith(figs) ? p.slice(figs.length) : p; } return u.slice(0, 22); };
  const out = (Array.from(md.querySelectorAll("img")) as HTMLImageElement[]).map((i) => {
    let anchor: Element = i;
    for (let p = anchor.parentElement; p && (p.localName === "picture" || p.classList.contains("fc-imgwrap") || (p.localName === "a" && p.children.length === 1)); p = anchor.parentElement) anchor = p;
    let n = anchor.nextSibling as Element | null;
    if (n && n.nodeType === 1 && n.hasAttribute("data-fv-figopen")) n = n.nextSibling as Element | null;   // past the figure's Open control (L3)
    const lab = n && n.nodeType === 1 && n.hasAttribute("data-fv-figerr") ? n as HTMLElement : null;
    const cs = lab ? getComputedStyle(lab) : null; const r = lab ? lab.getBoundingClientRect() : null;
    return { alt: i.getAttribute("alt"), asked: leaf(i.currentSrc || ""), natural: i.naturalWidth, label: lab ? lab.textContent : null, labelParent: lab ? lab.parentElement!.localName : null,
      inLink: !!lab && !!lab.closest("a"), cursor: cs ? cs.cursor : null, display: cs ? cs.display : null, labelHeight: r ? r.height : 0, labelWidth: r ? r.width : 0 };
  });
  return { figs: out, labels: md.querySelectorAll("[data-fv-figerr]").length };
}, FIGS);

test("in a browser (the Slice 7 review's round 1): a <picture>'s label names the source candidate the browser asked for and an img's its srcset candidate, never the src the browser skipped (a file that is there); an inline data: figure's label is its head with an ellipsis, one line tall, not the payload; a linked figure's label stands after the link, not inside it, with no pointer; the plain figure of the same file loads with no label; the sheet dresses every label", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    asked.length = 0;
    const { page, errors } = await openViewer(browser, "pane", 900, 700, { docs: { [REPORT]: NOTE2 }, serve: serve2 });
    await page.waitForFunction(() => { const imgs = Array.from(document.querySelectorAll(".fileview-md img")) as HTMLImageElement[]; return imgs.length >= 5 && imgs.every((i) => i.complete); }, null, { timeout: 15000 });
    await frames(page, 2);
    const { figs, labels } = await figures2(page);
    assert.equal(figs.length, 5, "five figures"); assert.equal(labels, 4, "four labels, one per failed figure; none on the plain figure that loaded");
    assert.deepEqual(figs.map((f) => f.alt), ["plot", "dense", "inline", "linked", "plain"]);
    // what the browser asked for: the picture's source, the img's 1x candidate, the inline bytes, the linked file, the plain file
    assert.deepEqual(figs.map((f) => f.asked), ["dark.webp", "missing-1x.png", "data:image/png;base64,", "missing5.png", "plot.png"], "currentSrc names the one candidate the browser fetched for each: " + JSON.stringify(figs.map((f) => f.asked)));
    assert.ok(asked.includes("dark.webp") && asked.includes("missing-1x.png") && asked.includes("missing5.png") && asked.includes("plot.png"), "the kernel was asked for each: " + JSON.stringify(asked));
    assert.equal(asked.includes("missing-2x.png"), false, "the 2x candidate was never asked for on a 1x display");
    assert.deepEqual(figs.map((f) => f.natural > 0), [false, false, false, false, true], "the plain figure alone decoded: the picture's and the srcset img's src is that same file, and the browser never fell back to it");
    // the labels name what failed
    assert.equal(figs[0].label, FAILED + " figs/dark.webp (plot)", "the picture's label names the source candidate the browser asked for, by its authored spelling (before: figs/plot.png, present and decodable, the file the browser never requested for it)");
    assert.equal(figs[1].label, FAILED + " figs/missing-1x.png (dense)", "the srcset img's label names its chosen candidate (before: figs/plot.png)");
    assert.equal(figs[2].label, FAILED + " data:image/png;base64,… (inline)", "the inline figure's label is the data: head with an ellipsis (before: the whole 3033-character URI)");
    assert.ok(figs[2].labelHeight < 60, "…one line or two tall, not a column of base64: " + figs[2].labelHeight + " px (before: 666 px at this width)");
    assert.equal(figs[3].label, FAILED + " figs/missing5.png (linked)", "the linked figure's label");
    assert.equal(figs[3].inLink, false, "…stands outside the link (before: inside it, a click on it followed the link)");
    assert.equal(figs[3].labelParent, "p", "…as the paragraph's child after the link");
    assert.notEqual(figs[3].cursor, "pointer", "…and wears no pointer: " + figs[3].cursor);
    assert.equal(figs[4].label, null, "the plain figure of the file that is there wears no label");
    for (const f of figs.filter((x) => x.label !== null)) { assert.equal(f.display, "inline-flex", "the sheet dresses the label: " + f.alt); assert.ok(f.labelWidth > 20, "…with a box: " + f.alt); }
    assert.deepEqual(errors, [], "no uncaught page error");
    await page.close();
  });
});

// ── a credential in the label's words, and in a loaded picture's title (the file review's round 14, correctness-1 with extra5-3) ─
// Chromium never requests a source carrying a user:pass@, an ftp: source or one the URL parser refuses, so each fails and its
// label is where such a source would show; before the round-14 fix the label printed every source but a data: one as written,
// and a loaded picture's title kept its query and fragment. A second local http server on another port stands for the remote
// hosts: the page reaches it as http://example.test, https://example.test and https://bucket.example.test through a context
// route that relays the bytes (file-figure-open-browser.test.ts's shape), answering /ok.svg with a picture and every other path
// with a 404, and the hosts are on figureHosts before the open, so no figure is gated. CI skips this leg (the Test step runs
// before the job's Chromium install), so file-view-figure-error.test.ts holds the rule on the label builder and through the
// listener over the stand-in, which CI runs. Every planted value is assembled at run time: no credential-shaped literal here.
/** The remote server: every request logged by its path, /ok.svg a 300 by 200 picture, anything else a 404. */
function remoteServer(log: string[]): Promise<{ port: number; close: () => Promise<void> }> {
  return new Promise((resolve) => {
    const s = http.createServer((req, res) => {
      log.push((req.method || "") + " " + (req.url || ""));
      if ((req.url || "").split("?")[0] === "/ok.svg") { res.writeHead(200, { "Content-Type": "image/svg+xml" }); res.end('<svg xmlns="http://www.w3.org/2000/svg" width="300" height="200"><rect width="300" height="200" fill="#333"/></svg>'); return; }
      res.writeHead(404, { "Content-Type": "text/plain" }); res.end("not found");
    });
    s.listen(0, "127.0.0.1", () => { const a = s.address() as { port: number }; resolve({ port: a.port, close: () => new Promise((r) => s.close(() => r())) }); });
  });
}
/** The remote server's answer for `p`, read over loopback from node (the relay's other half). */
const fromRemote = (port: number, p: string): Promise<{ status: number; type: string; body: string }> => new Promise((resolve, reject) => {
  http.get({ host: "127.0.0.1", port, path: p }, (res) => { let b = ""; res.on("data", (c) => { b += c; }); res.on("end", () => resolve({ status: res.statusCode || 0, type: String(res.headers["content-type"] || ""), body: b })); }).on("error", reject);
});

test("in a browser: a failed figure's label never prints a path, a userinfo, a query or a fragment for a source with a scheme other than data:, or a protocol-relative one: a source with a sign-in part (an http userinfo, a userinfo plus a query, a protocol-relative one in HTML and in markdown, a srcset candidate the browser chose, an ftp source, an out-of-range port, a tab inside the scheme, a refused source whose password holds a / or a ?) shows the withheld address and no part of itself (the file review's round 15, correctness-1), and any other (a query token, an S3 presigned pair, a fragment's access token, an out-of-range port with a query alone) its origin alone, a refused one cut at its authority (the same round's extra9-2); a loaded picture's title shows its origin alone, and a data: head and a workspace path print as they did (a property pin over the page, red at the head the round read, where each label printed its path and the title kept its path)", { timeout: 300000 }, async (t) => {
  const TOK = "tok" + "en", UI = "u" + "ser" + ":" + "p" + "w" + String(4 * 4) + "@";
  const V = (k: string): string => k + "TOK" + String(k.length * 37);
  const S3C = "AKID" + "EXAMPLE" + "%2F20260923%2Fus-east-1%2Fs3%2Faws4_request", S3S = "abc" + "def0123456789" + "fedcba";
  const W = "address withheld because it appears to carry a sign-in";   // the words in a withheld address's place (file-view.ts FIGURE_ADDRESS_WITHHELD), a literal so the expected text never moves with the product
  /** [case, the paragraph's figure, the label's words (null for the loaded picture, which wears none)] */
  const cases: Array<[string, string, string | null]> = [
    ["an http userinfo", '<img src="http://' + UI + 'example.test/a.svg" alt="">', W],
    ["an https query token", '<img src="https://example.test/b.svg?' + TOK + "=" + V("QB") + '" alt="">', "https://example.test"],
    ["an S3 presigned pair", '<img src="https://bucket.example.test/fig.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&amp;X-Amz-Credential=' + S3C + "&amp;X-Amz-Signature=" + S3S + '" alt="">', "https://bucket.example.test"],
    ["a fragment's access token", '<img src="http://example.test/f.svg#access_' + "token=" + V("FR") + '" alt="">', "http://example.test"],
    ["a userinfo plus a query", '<img src="http://' + UI + "example.test/c.svg?" + TOK + "=" + V("UQ") + '" alt="">', W],
    ["a protocol-relative userinfo plus a query", '<img src="//' + UI + "example.test/r.svg?" + TOK + "=" + V("PR") + '" alt="">', W],
    ["a srcset 1x candidate with a userinfo plus a query", '<img src="figs/fallback.png" srcset="http://' + UI + "example.test/s.svg?" + TOK + "=" + V("SS") + ' 1x" alt="">', W],
    ["an ftp userinfo plus a query", '<img src="ftp://' + UI + "example.test/g.svg?" + TOK + "=" + V("FT") + '" alt="">', W],
    ["an out-of-range port with a userinfo plus a query", '<img src="http://' + UI + "example.test:99999/u.svg?" + TOK + "=" + V("UP") + '" alt="">', W],
    ["an out-of-range port with a query alone, cut at its authority", '<img src="http://example.test:99999/v.svg?' + TOK + "=" + V("UV") + '" alt="">', "http://example.test:99999"],
    ["a markdown protocol-relative userinfo plus a query", "![](//" + UI + "example.test/m.svg?" + TOK + "=" + V("MD") + ")", W],
    ["a tab inside the scheme", '<img src="ht&#9;tp://' + UI + "example.test/t.svg?" + TOK + "=" + V("TB") + '" alt="">', W],
    ["a refused source whose password holds a /", '<img src="http://u' + "ser:p/" + V("SL") + '@example.test/x1.png" alt="">', W],
    ["a refused source whose password holds a ?", '<img src="http://u' + "ser:p?" + V("QM") + '@example.test/x2.png" alt="">', W],
    ["a loaded picture whose address carries a query and a fragment", '<img src="https://example.test/ok.svg?' + TOK + "=" + V("LQ") + "#access_" + "token=" + V("LF") + '" alt="loaded">', null],
    ["a control, a data: source", '<img src="data:image/png;base64,' + "A".repeat(40) + '" alt="">', "data:image/png;base64,…"],
    ["a control, a workspace path with a query-looking tail", "![](figs/q.png?x=1)", "figs/q.png?x=1"],
  ];
  const planted = ["user:", "pw16", S3C, S3S, "X-Amz-", "access_", "?" + TOK, ...["QB", "FR", "UQ", "PR", "SS", "FT", "UP", "UV", "MD", "TB", "SL", "QM", "LQ", "LF"].map(V)];
  const note = "# Report\n\n" + cases.map(([n, h], i) => "Case " + i + " (" + n + "): " + h + " end.").join("\n\n") + "\n";
  const served: string[] = [];
  const remote = await remoteServer(served);
  try {
    await inBrowser(t, async (browser) => {
      const before = async (pg: any): Promise<void> => {
        await pg.context().route((u: URL) => u.hostname === "example.test" || u.hostname === "bucket.example.test", async (route: any) => {
          const a = await fromRemote(remote.port, new URL(route.request().url()).pathname);
          return route.fulfill({ status: a.status, contentType: a.type, body: a.body });
        });
        await pg.evaluate(() => { localStorage.setItem("romp:settings", JSON.stringify({ figureHosts: ["example.test", "bucket.example.test"] })); });   // no figure gated: each is fetched, or refused by the browser, at the paint
      };
      const { page, errors } = await openViewer(browser, "pane", 900, 700, { docs: { [REPORT]: note }, serve, before });
      await page.waitForFunction((n: number) => { const imgs = Array.from(document.querySelectorAll(".fileview-md img")) as HTMLImageElement[]; return imgs.length === n && imgs.every((i) => i.complete); }, cases.length, { timeout: 15000 });
      await frames(page, 3);
      const rows: Array<{ label: string | null; title: string | null; natural: number; visible: string }> = await page.evaluate(() => (Array.from(document.querySelectorAll(".fileview-md > p")) as HTMLElement[]).filter((p) => /^Case \d+/.test(p.textContent || "")).map((p) => {
        const i = p.querySelector("img") as HTMLImageElement | null;
        const lab = p.querySelector("[data-fv-figerr]") as HTMLElement | null;
        return { label: lab ? lab.textContent : null, title: i ? i.getAttribute("title") : null, natural: i ? i.naturalWidth : -1, visible: p.innerText || "" };
      }));
      t.diagnostic("remote requests " + JSON.stringify(served));
      assert.equal(rows.length, cases.length, "one paragraph per case");
      assert.deepEqual(rows.map((r) => r.label), cases.map(([, , w]) => (w === null ? null : FAILED + " " + w)),
        "each failed figure's label: the withheld address for a source with a sign-in part, the origin alone for the rest (a refused one cut at its authority), the data: head and the workspace path as they were, and the loaded picture none (a property pin over the label's text)");
      const loaded = rows[cases.length - 3];
      assert.ok(loaded.natural > 0, "the loaded case decoded, relayed from the remote server: " + JSON.stringify(served));
      assert.equal(loaded.title, "Opens in a new tab: https://example.test", "the loaded picture's title is its origin alone: no path, no query, no fragment (a property pin over the title attribute)");
      const leaks: string[] = [];
      rows.forEach((r, k) => { for (const x of planted) for (const [where, text] of [["label", r.label], ["title", r.title], ["visible text", r.visible]] as const) if ((text || "").includes(x)) leaks.push(cases[k][0] + ": the " + where + " carries " + JSON.stringify(x)); });
      assert.deepEqual(leaks, [], "no planted value in a label, a title or a paragraph's visible text (a property pin)");
      assert.deepEqual(errors, [], "no uncaught page error");
      await page.close();
    });
  } finally { await remote.close(); }
});

// ── the chat modal's heal and the label (the file review's round 15, fresh-1) ───────────────────────────────────────────────
// On the chat modal the page's heal (preview.ts installMdImgHeal, a capture listener on the document) parks a failed img before
// the viewer's listener on the body reads it: the resolved src goes into data-md-src and the src leaves. Before the fix the label
// of every failed web picture whose address was its own src read "the source is empty"; failedSource now reads the heal's record
// when the candidate names nothing and the img has no src. The cells: a plain web source, a query-bearing one and a standard
// userinfo one (red before the fix by "the source is empty"; after it the origin for the first two and the withheld address for
// the third); a same-scheme source written without slashes on the http page and on a page opened at https://notes-api.test
// (openViewer's origin), which the heal records resolved against that base (red before the fix by the missing withheld wording, as
// nothing of the address printed there); and, as controls green before the fix and after it, a srcset candidate and a
// <picture> source from the web, whose label names the candidate's origin once the browser has chosen again after the heal
// removed the src (each img's error events counted, and the label read after its last one). Four empty destinations join them
// (the file review's round 16, correctness-1): `![diagram]()`, `<img src="">` and `<img src="   ">` on the http page and the first on
// the https one. The heal parks each as it parks any failed img, recording img.src, which for an empty or blank src is the page's
// base address, and the label read that record as the page's own origin; failedSource now leaves a record equal to that address
// unread, so the label says the source is empty (red at the head that round read, the web cells its controls). Every planted value
// is assembled at run time.
test("in a browser, the chat modal with the page's heal: a failed web picture whose address is its own src is labelled from the heal's record, its origin alone or the withheld address, never 'the source is empty', a same-scheme source written without slashes withheld on an http and on an https base, and a srcset and a <picture> source from the web still named by the candidate's origin after the browser chooses again (the file review's round 15, fresh-1: the heal parked the img before the viewer read it); and an empty markdown destination, an empty src and a blank src, which the heal parks recording the page's base address, say 'the source is empty' and name no origin, on the http page and on the https one (the file review's round 16, correctness-1: red at the head that round read by the page's origin in each; the web cells are its controls, green there by design) (a property pin over the label's text)", { timeout: 120000 }, async (t) => {
  const TOK = "tok" + "en", UI = "u" + "ser" + ":" + "p" + "w" + String(4 * 4) + "@";
  const V = (k: string): string => k + "TOK" + String(k.length * 37);
  const W = "address withheld because it appears to carry a sign-in";   // FIGURE_ADDRESS_WITHHELD as a literal, so the expected text never moves with the product
  const EMPTY = "the source is empty (diagram)";   // FIGURE_NO_SOURCE and the alt, a literal for the same reason
  /** [cell, the paragraph's figure, the page's origin ("http" or "https"), the label's words, whether the cell is a control] */
  const cells: Array<[string, string, "http" | "https", string, boolean]> = [
    ["a plain web source", '<img src="https://example.test/missing.svg" alt="">', "http", "https://example.test", false],
    ["a query-bearing web source", '<img src="https://example.test/q.svg?' + TOK + "=" + V("HQ") + '" alt="">', "http", "https://example.test", false],
    ["a standard userinfo", '<img src="http://' + UI + 'example.test/u.svg" alt="">', "http", W, false],
    ["http: written without slashes on the http page", '<img src="http:' + UI + 'example.test/h.png" alt="">', "http", W, false],
    ["https: written without slashes on a page at https://notes-api.test", '<img src="https:' + UI + 'example.test/s.png" alt="">', "https", W, false],
    ["a srcset candidate from the web (a control)", '<img src="figs/fallback.png" srcset="https://example.test/ss.svg 1x" alt="">', "http", "https://example.test", true],
    ["a <picture> source from the web (a control)", '<picture><source srcset="https://example.test/pic.svg"><img src="figs/fallback2.png" alt=""></picture>', "http", "https://example.test", true],
    // the empty destinations (the file review's round 16, correctness-1): the heal parks them too, recording img.src, the page's base
    // address for an empty or blank src, and the label says the source is empty, as it did before the heal's record was read
    ["an empty markdown destination on the http page", "![diagram]()", "http", EMPTY, false],
    ["an empty src on the http page", '<img src="" alt="diagram">', "http", EMPTY, false],
    ["a blank src on the http page", '<img src="   " alt="diagram">', "http", EMPTY, false],
    ["an empty markdown destination on a page at https://notes-api.test", "![diagram]()", "https", EMPTY, false],
  ];
  const planted = ["user:", "pw16", "?" + TOK, V("HQ")];
  const served: string[] = [];
  const remote = await remoteServer(served);
  try {
    await inBrowser(t, async (browser) => {
      for (const scheme of ["http", "https"] as const) {
        const mine = cells.filter(([, , s]) => s === scheme);
        const note = "# Report\n\n" + mine.map(([n, h], i) => "Case " + i + " (" + n + "): " + h + " end.").join("\n\n") + "\n";
        const before = async (pg: any): Promise<void> => {
          await pg.context().route((u: URL) => u.hostname === "example.test", async (route: any) => {
            const a = await fromRemote(remote.port, new URL(route.request().url()).pathname);
            return route.fulfill({ status: a.status, contentType: a.type, body: a.body });
          });
          await pg.evaluate(() => {
            const w = window as any;
            localStorage.setItem("romp:settings", JSON.stringify({ figureHosts: ["example.test"] }));   // no figure gated: each is fetched at the paint
            w.__errs = new Map();   // each img's error events, counted on the document before the heal's listener runs
            document.addEventListener("error", (e) => { const i = e.target as Element | null; if (i && i.nodeType === 1 && i.tagName === "IMG") w.__errs.set(i, (w.__errs.get(i) || 0) + 1); }, true);
            w.FV.installMdImgHeal();   // render.ts installs it once at load, before any turn paints
          });
        };
        const { page, errors } = await openViewer(browser, "chat", 900, 700, { docs: { [REPORT]: note }, serve, before, origin: scheme + "://notes-api.test" });
        try {
          assert.equal(await page.evaluate(() => document.baseURI), scheme + "://notes-api.test/", "the page's base is " + scheme + "://notes-api.test/");
          // every img has failed and been parked, and a srcset or <picture> img has had its second error, the browser's choice after the heal removed its src
          const wants = mine.map(([, h]) => (/srcset=/.test(h) ? 2 : 1));
          await page.waitForFunction((w: number[]) => { const imgs = Array.from(document.querySelectorAll(".fileview-md img")); const m = (window as any).__errs as Map<Element, number>; return imgs.length === w.length && imgs.every((i, k) => (m.get(i) || 0) >= w[k] && i.classList.contains("md-img-failed")); }, wants, { timeout: 15000 });
          await frames(page, 3);
          const rows: Array<{ label: string | null; errs: number; parked: boolean; src: boolean; mdSrc: string | null; visible: string }> = await page.evaluate(() => (Array.from(document.querySelectorAll(".fileview-md > p")) as HTMLElement[]).filter((p) => /^Case \d+/.test(p.textContent || "")).map((p) => {
            const i = p.querySelector("img") as HTMLImageElement;
            const lab = p.querySelector("[data-fv-figerr]") as HTMLElement | null;
            return { label: lab ? lab.textContent : null, errs: ((window as any).__errs as Map<Element, number>).get(i) || 0, parked: i.classList.contains("md-img-failed"), src: i.hasAttribute("src"), mdSrc: i.getAttribute("data-md-src"), visible: p.innerText || "" };
          }));
          t.diagnostic(scheme + " page: " + JSON.stringify(rows.map((r, k) => ({ cell: mine[k][0], label: r.label, errs: r.errs, parked: r.parked, src: r.src, mdSrcHost: r.mdSrc ? new URL(r.mdSrc).host : null }))));
          assert.equal(rows.length, mine.length, "one paragraph per cell");
          // the precondition: the heal parked each failed img (no src, md-img-failed, the resolved address in data-md-src)
          assert.deepEqual(rows.map((r) => [r.parked, r.src, !!r.mdSrc]), mine.map(() => [true, false, true]), "the heal parked every failed figure before the label was read");
          // FAILS BEFORE the fix: the five cells that are not controls read FIGURE_FAILED + " the source is empty"; and at the head the
          // file review's round 16 read, the four empty destinations read FIGURE_FAILED + " http://notes-api.test (diagram)" (or https), the
          // page's own origin (correctness-1)
          assert.deepEqual(rows.map((r, k) => (mine[k][4] ? null : r.label)), mine.map(([, , , w, control]) => (control ? null : FAILED + " " + w)), "each label names the heal's record as any address is named, the origin alone or the withheld address (a property pin over the label's text)");
          // the controls, green before the fix by design: the label names the candidate the browser chose, from its origin on (the path
          // after it printed before the origin cut), never the fallback src and never the empty source
          for (const [k, r] of rows.entries()) if (mine[k][4]) assert.ok((r.label || "").startsWith(FAILED + " " + mine[k][3]) && !/fallback|the source is empty/.test(r.label || ""), mine[k][0] + ": after its " + r.errs + " error events the label names the candidate's origin, not the fallback src or the empty source: " + JSON.stringify(r.label));
          const leaks: string[] = [];
          rows.forEach((r, k) => { for (const x of planted) for (const [where, text] of [["label", r.label], ["visible text", r.visible]] as const) if ((text || "").includes(x)) leaks.push(mine[k][0] + ": the " + where + " carries " + JSON.stringify(x)); });
          assert.deepEqual(leaks, [], "no planted value in a label or a paragraph's visible text (a property pin)");
          assert.deepEqual(errors, [], "no uncaught page error");
        } finally { await page.close(); }
      }
    });
  } finally { await remote.close(); }
});

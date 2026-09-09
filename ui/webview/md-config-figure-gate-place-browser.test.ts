// The reader's place across a Rendered/Raw round trip when the top-visible block is an html block holding a GATED figure,
// in headless Chromium over the REAL viewer bundle (reader-place.ts ownedElements and noteText; figure-gate.ts;
// plans/markdown-viewer.md Slice 4, decision 8; the Slice 4 review). The gate wraps a picture on a host outside the
// gear's list in a `span.fv-gate` placeholder labelled "Image from host. Click to load.", the viewer's text; an html
// block's pairing is trusted only when its source, parsed by DOMParser, reads the same text as the rendered elements, and
// that compare read the label through textContent against a parse of `<p><img src="https://remote.test/a.png">` reading
// nothing. So the block was refused: with the placeholder 20px past the body's top edge the Raw click seated nothing
// (Chromium's own scroll anchoring moved the body, in the review's measurement to a row fourteen paragraphs on) and the
// return seated that row, not the figure. The rendered side is read as the anchor map reads it now, the controls skipped.
// Scenes, the Files pane at 900x600, a report of eighty paragraphs with the figure after the fortieth, the reader 20px
// into the figure's block:
//   - the gated `<p><img>` html block and a gated bare `<img>` line (its top-level element is the placeholder itself): the
//     Raw top row is the block's own source line and the return puts the block back where it was, within a pixel and a
//     half; the seat wrote the body's scrollTop on both switches; the page requested nothing from the gated host;
//   - two controls, each a place before the fix: the same html block on github.com (in the default list, loads on open)
//     and the gated picture written as a markdown image (a paragraph, no parse to compare).
// Legs await frames, never a timer. Skips LOUDLY without a playwright browser, as the other legs do. Synthetic values only:
// an invented report, /repo/notes-api paths, the placeholder sid, hosts under .test.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, frames, PARA, REPORT } from "./real-viewer-leg";

const near = (a: number, b: number, what: string, tol = 1.5) => assert.ok(Math.abs(a - b) <= tol, `${what}: ${a} vs ${b}`);
const paras = (a: number, b: number) => Array.from({ length: b - a + 1 }, (_, i) => PARA(a + i)).join("\n\n");
const FIG = 41;   // the figure's index among .fileview-md's children: the heading, then paragraphs 1 to 40
const SVG_IMG = '<svg xmlns="http://www.w3.org/2000/svg" width="120" height="80"><rect width="120" height="80" fill="#4682b4"/></svg>';

const click = async (page: any, label: string) => { await page.locator("#romp-fileview .fileview-btn", { hasText: new RegExp("^" + label + "$") }).click(); await frames(page, 3); };
/** The box of the Rendered view's `i`th top-level element from the body's top edge, with the body's scrollTop. */
const blockBox = (page: any, i: number) => page.evaluate((k: number) => {
  const body = document.querySelector(".fileview-body")!; const br = body.getBoundingClientRect();
  const el = document.querySelector(".fileview-md")!.children[k]; const r = el.getBoundingClientRect();
  return { tag: el.tagName, cls: el.className, top: Math.round((r.top - br.top) * 10) / 10, bottom: Math.round((r.bottom - br.top) * 10) / 10, scrollTop: body.scrollTop };
}, i);
/** Scroll so the `i`th top-level element's top sits `extra` px above the body's top edge. */
const scrollInto = (page: any, i: number, extra: number) => page.evaluate(([k, x]: [number, number]) => {
  const body = document.querySelector(".fileview-body")!;
  const el = document.querySelector(".fileview-md")!.children[k];
  body.scrollTop += el.getBoundingClientRect().top - body.getBoundingClientRect().top + x;
}, [i, extra]);
/** The first Raw row ending below the body's top edge: its text and the body's scrollTop; null when no Raw view shows. */
const rowAtTop = (page: any) => page.evaluate(() => {
  const body = document.querySelector(".fileview-body")!; const br = body.getBoundingClientRect();
  for (const r of Array.from(body.querySelectorAll("code.hljs .fv-cl"))) { const rr = r.getBoundingClientRect(); if (rr.bottom > br.top + 0.5) return { text: (r.textContent || "").trim().slice(0, 40), scrollTop: body.scrollTop }; }
  return null;
});
/** Every picture in the view loaded with a size (a broken one is `complete` too, at its alt text's box). */
const imagesLoaded = (page: any) => page.waitForFunction(() => Array.from(document.querySelectorAll(".fileview-md img")).every((i) => (i as HTMLImageElement).complete && (i as HTMLImageElement).naturalWidth > 0), null, { timeout: 10000 });
/** Trap every script write of the body's scrollTop from now on (the viewer's seat is one; the browser's own scrolls are not
 *  writes), so a refused switch can be told from a seated one. Installed after the scene's own scroll. */
const trapWrites = (page: any) => page.evaluate(() => {
  const body = document.querySelector(".fileview-body") as HTMLElement;
  const proto = Object.getOwnPropertyDescriptor(Element.prototype, "scrollTop")!;
  (window as any).__writes = [];
  Object.defineProperty(body, "scrollTop", { get() { return proto.get!.call(this); }, set(v) { (window as any).__writes.push(v); proto.set!.call(this, v); }, configurable: true });
});
const writes = (page: any): Promise<number[]> => page.evaluate(() => (window as any).__writes as number[]);

test("in a browser, the real module: a gated figure's html block at the body's top edge keeps the reader's place across a Raw and back round trip (as a <p><img> block and as a bare <img> line), the placeholder's label skipped from the block's text; the ungated block and the markdown image round-trip as before, and the gated host is never requested", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const SHAPES: Array<[string, string, string, boolean]> = [
      // what, the figure's source, the host it names, gated
      ["a gated <p><img> html block", `<p><img src="https://remote.test/a.png" width="120" height="80" alt="fig"></p>`, "remote.test", true],
      ["a gated bare <img> line", `<img src="https://remote.test/a.png" width="120" height="80" alt="fig">`, "remote.test", true],
      ["the same html block on github.com, in the default list", `<p><img src="https://github.com/u/r/raw/main/a.png" width="120" height="80" alt="fig"></p>`, "github.com", false],
      ["the gated picture as a markdown image", "![fig](https://remote.test/a.png)", "remote.test", true],
    ];
    for (const [what, fig, host, gatedShape] of SHAPES) {
      const DOC = "# Report\n\n" + paras(1, 40) + "\n\n" + fig + "\n\n" + paras(41, 80) + "\n";
      // the figure hosts are answered from memory, and recorded, from before the page exists: a route installed after the
      // open would miss the listed host's request on open, and a picture that failed there (its alt text's 22px box) and
      // loaded on the repaint (80px) changes the block's height between the two views, which is another scene
      const ctx = await browser.newContext({ viewport: { width: 900, height: 600 } });
      const requested: string[] = [];
      await ctx.route((u: URL) => u.hostname === "remote.test" || u.hostname === "github.com", (route: any) => { requested.push(route.request().url()); route.fulfill({ status: 200, contentType: "image/svg+xml", body: SVG_IMG }); });
      const { page, errors } = await openViewer(ctx, "pane", 900, 600, { docs: { [REPORT]: DOC } });
      // the scene: the figure's block (or the placeholder that IS the block's element) with its top 20px past the edge
      const gates: number = await page.evaluate(() => document.querySelectorAll("#romp-fileview .fv-gate").length);
      assert.equal(gates, gatedShape ? 1 : 0, what + ": the fixture is " + (gatedShape ? "gated" : "not gated"));
      if (!gatedShape) await imagesLoaded(page);
      await scrollInto(page, FIG, 20); await frames(page, 2);
      const before = await blockBox(page, FIG);
      near(before.top, -20, what + ": the scene starts with the block 20px past the edge", 1);
      assert.ok(before.bottom > 0, what + ": and reaching below it");
      await trapWrites(page);
      await click(page, "Raw");
      const row = await rowAtTop(page);
      assert.ok(row, what + ": the Raw view painted");
      assert.equal(row!.text, fig.slice(0, 40), what + `: the Raw top row is the figure's own source line (got ${JSON.stringify(row!.text)})`);
      await click(page, "Rendered");
      const back = await blockBox(page, FIG);
      near(back.top, before.top, what + ": back in Rendered the block is where it was (before the fix the return landed paragraphs away)");
      const w = await writes(page);
      assert.equal(w.length, 2, what + `: the seat wrote the body's scrollTop once per switch (a refused place writes nothing; got ${JSON.stringify(w)})`);
      if (gatedShape) assert.deepEqual(requested, [], what + ": nothing left the page for the gated host");
      else assert.equal(requested.length, 1, what + ": the listed host's picture loaded on open");
      assert.deepEqual(errors, [], what + ": no script error");
      await ctx.close();
    }
  });
});

// The viewer's hold for a note with math (iOS item 6, 2026-10-02): KaTeX is an on-demand chunk (math-chunk.ts), and a Rendered
// paint whose block holds a formula still waiting for it is not swapped in. The body keeps the romp loader on an open, the chunk
// is fetched once, and the renderer's arrival paints, so the note's first paint is its final one: one paint, the hooks once,
// KaTeX in place, and the anchor map, the reader's place and the comment paint never meet a waiting formula. A note with no
// math fetches no chunk and paints at once; a chunk that fails to load paints the note with each formula as its source. The
// real viewer in Chromium through the shared harness (real-viewer-leg.ts), its bundle built WITHOUT KaTeX (bundleViewer(false))
// and loaded by src as the kernel's pages load theirs, so the chunk's URL derives from that tag as on a page (chunk-url.ts);
// the chunk is the shipped build of math-chunk.ts (math-chunk-leg.ts chunkBundle), held until the leg lets it go.
// `window.__paints` counts the seam's onRendered. Synthetic values only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, bundleViewer, frames, paintsReach, REPORT } from "./real-viewer-leg";
import { chunkBundle, gate, type Gate } from "./math-chunk-leg";

const NOTE = "# Ratios\n\nThe ratio $\\frac{a}{b}$ holds.\n\n$$\\sum_{i=0}^{n} i^2$$\n\nAfter the formula.\n";
const PLAIN = "# Plain\n\nNo formula here, and $HOME stays literal.\n";
const OTHER = "/repo/notes-api/docs/plain.md";

/** The viewer opened in the Files pane over `docs` with its bundle by src; the chunk's URL answered under `chunk`, held by `g`. */
async function open(browser: any, docs: Record<string, string>, chunk: "serve" | "404", g: Gate | null, requests: string[]) {
  return openViewer(browser, "pane", 900, 700, {
    docs, bundleSrc: "/dist/files.js?v=3", waitFor: ".fileview-body",
    serve: (u) => (u.pathname === "/dist/files.js" ? { status: 200, type: "text/javascript", body: bundleViewer(false) } : null),
    before: async (page) => {
      await page.route((u: URL) => u.pathname === "/dist/math-chunk.js", async (route: any) => {
        requests.push(new URL(route.request().url()).pathname + new URL(route.request().url()).search);
        if (g) await g.promise;
        const c = chunkBundle();
        if (chunk === "404" || "error" in c) return route.fulfill({ status: 404, contentType: "text/plain", body: "not found" });
        return route.fulfill({ status: 200, contentType: "text/javascript", body: c.js });
      });
    },
  });
}

type Body = { loader: boolean; md: boolean; katex: number; waiting: number; src: string[]; paints: number };
const bodyNow = (page: any): Promise<Body> => page.evaluate(() => {
  const b = document.querySelector(".fileview-body")!;
  return { loader: !!b.querySelector(".fileview-load"), md: !!b.querySelector(".fileview-md"), katex: b.querySelectorAll(".katex").length,
    waiting: document.querySelectorAll(".md-math-inline, .md-math-display").length,
    src: Array.from(b.querySelectorAll("code.md-math-src")).map((c) => ((c.closest("pre") || c) as HTMLElement).getAttribute("title") || ""),
    paints: (window as any).__paints - (window as any).__reflows };
});

test("chromium: a note with math, opened before the math renderer is in, keeps the romp loader until the chunk lands, then paints once with KaTeX in place", { timeout: 60000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const g = gate(); const requests: string[] = [];
    const { page, errors } = await open(browser, { [REPORT]: NOTE }, "serve", g, requests);
    await page.waitForFunction(() => !!document.querySelector('script[src*="math-chunk.js"]'), null, { timeout: 10000 });
    await frames(page, 4);
    let b = await bodyNow(page);
    assert.deepEqual(requests, ["/dist/math-chunk.js?v=3"], "one request, beside the bundle and with its ?v= token");
    assert.deepEqual([b.loader, b.md, b.paints, b.waiting], [true, false, 0, 0], "held: the loader stands, nothing is painted, no waiting formula reaches the page: " + JSON.stringify(b));
    g.open();
    await paintsReach(page, 1);
    await frames(page, 6);
    b = await bodyNow(page);
    assert.deepEqual([b.loader, b.md, b.katex, b.waiting, b.src.length], [false, true, 2, 0, 0], "the arrival paints the note, both formulas laid out: " + JSON.stringify(b));
    assert.equal(b.paints, 1, "exactly one paint: the first paint is the final one");
    assert.equal(requests.length, 1);
    assert.deepEqual(errors, []);
  });
});

test("chromium: a note with no math fetches no chunk and paints at once; a note with math opened after it in the same page does fetch it", { timeout: 60000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const requests: string[] = [];
    const { page, errors } = await open(browser, { [REPORT]: PLAIN, [OTHER]: NOTE }, "serve", null, requests);
    await paintsReach(page, 1);
    await page.evaluate(() => fetch("/version").then(() => null));
    await frames(page, 4);
    const b = await bodyNow(page);
    assert.deepEqual([b.md, b.loader, b.paints], [true, false, 1], "painted at once: " + JSON.stringify(b));
    assert.deepEqual(requests, [], "no chunk for a note with no formula");
    assert.equal(await page.evaluate(() => document.querySelectorAll('script[src*="math-chunk"]').length), 0);
    // the instrument, proven in the same page: a note with math asks for the chunk and renders once it lands
    await page.evaluate((p: string) => { (window as any).FV.openFileView(p, null, null); }, OTHER);
    await page.waitForFunction(() => document.querySelectorAll(".fileview-body .katex").length === 2, null, { timeout: 15000 });
    assert.deepEqual(requests, ["/dist/math-chunk.js?v=3"]);
    assert.deepEqual(errors, []);
  });
});

test("chromium: a chunk that fails to load paints the note once, each formula as its source with the failure in its title", { timeout: 60000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const requests: string[] = [];
    const { page, errors } = await open(browser, { [REPORT]: NOTE }, "404", null, requests);
    await paintsReach(page, 1);
    await frames(page, 6);
    const b = await bodyNow(page);
    assert.deepEqual([b.loader, b.md, b.katex, b.waiting], [false, true, 0, 0], JSON.stringify(b));
    assert.deepEqual(b.src, ["Not rendered: the math renderer failed to load; reload the page to try again.", "Not rendered: the math renderer failed to load; reload the page to try again."]);
    assert.equal(b.paints, 1, "one paint");
    assert.equal(requests.length, 1);
    assert.deepEqual(errors, []);
  });
});

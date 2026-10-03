// The viewer's hold for a note with math (iOS item 6, 2026-10-02): KaTeX is an on-demand chunk (math-chunk.ts), and a Rendered
// paint whose block holds a formula still waiting for it is not swapped in. The body keeps the romp loader on an open, the chunk
// is fetched once, and the renderer's arrival paints, so the note's first paint is its final one: one paint, the hooks once,
// KaTeX in place, and the anchor map, the reader's place and the comment paint never meet a waiting formula. A note with no
// math fetches no chunk and paints at once; a chunk that fails to load paints the note with each formula as its source. The
// real viewer in Chromium through the shared harness (real-viewer-leg.ts), its bundle built WITHOUT KaTeX (bundleViewer(false))
// and loaded by src as the kernel's pages load theirs, so the chunk's URL derives from that tag as on a page (chunk-url.ts);
// the chunk is the shipped build of math-chunk.ts (math-chunk-leg.ts chunkBundle), held until the leg lets it go.
// An open's target waits with the held paint: a math note opened at a heading or at an offset before the chunk lands raises no
// notice while the loader stands and lands on its target at the arrival's paint (file-view.ts landTarget stands down while a
// paint is held; the arrival runs it after its paint), and a Raw pick that ends the hold first lands the offset in the rows.
// Before, the landing spent the target over the loader: the heading raised 'No section named' and both opens sat at the note's
// top once the chunk was in.
// `window.__paints` counts the seam's onRendered. Synthetic values only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, bundleViewer, frames, paintsReach, REPORT, PARA } from "./real-viewer-leg";
import { chunkBundle, gate, type Gate } from "./math-chunk-leg";

const NOTE = "# Ratios\n\nThe ratio $\\frac{a}{b}$ holds.\n\n$$\\sum_{i=0}^{n} i^2$$\n\nAfter the formula.\n";
const PLAIN = "# Plain\n\nNo formula here, and $HOME stays literal.\n";
const OTHER = "/repo/notes-api/docs/plain.md";

/** The viewer opened in the Files pane over `docs` with its bundle by src; the chunk's URL answered under `chunk`, held by `g`;
 *  `openOpts` is openFileView's third argument (an `at` target). */
async function open(browser: any, docs: Record<string, string>, chunk: "serve" | "404", g: Gate | null, requests: string[], openOpts: Record<string, unknown> | null = null) {
  return openViewer(browser, "pane", 900, 700, {
    docs, bundleSrc: "/dist/files.js?v=3", waitFor: ".fileview-body", openOpts,
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

// A note long enough that its target sits screens below the top, one inline formula at its head: the hold's case for a target.
const FILLER = Array.from({ length: 40 }, (_, i) => PARA(i + 1)).join("\n\n");
const TARGETED = "# Ratios\n\nThe ratio $\\frac{a}{b}$ holds.\n\n" + FILLER + "\n\n## Second\n\nTarget paragraph here.\n\n" + FILLER + "\n";
const TARGET_OFFSET = TARGETED.indexOf("Target paragraph here.");

type Landing = { loader: boolean; notice: string | null; scrollTop: number; clientHeight: number; heading: number | null; target: { top: number; bottom: number } | null; katex: number; paints: number };
const landing = (page: any): Promise<Landing> => page.evaluate(() => {
  const b = document.querySelector(".fileview-body") as HTMLElement;
  const bar = document.getElementById("fileview-save-err");
  const bt = b.getBoundingClientRect().top;
  const h = Array.from(b.querySelectorAll("h2")).find((x) => (x.textContent || "").includes("Second")) as HTMLElement | undefined;
  const p = Array.from(b.querySelectorAll("p")).find((x) => (x.textContent || "").includes("Target paragraph")) as HTMLElement | undefined;
  return { loader: !!b.querySelector(".fileview-load"), notice: bar ? bar.textContent : null, scrollTop: b.scrollTop, clientHeight: b.clientHeight,
    heading: h ? Math.round(h.getBoundingClientRect().top - bt) : null,
    target: p ? { top: Math.round(p.getBoundingClientRect().top - bt), bottom: Math.round(p.getBoundingClientRect().bottom - bt) } : null,
    katex: b.querySelectorAll(".katex").length, paints: (window as any).__paints - (window as any).__reflows };
});

for (const [name, at] of [["a heading", { heading: "#second" }], ["an offset", { offset: TARGET_OFFSET }]] as const) {
  test(`chromium: a math note opened at ${name} before the math renderer is in raises no notice while held and lands on its target at the arrival's paint`, { timeout: 60000 }, async (t) => {
    await inBrowser(t, async (browser) => {
      assert.ok(TARGET_OFFSET > 0);
      const g = gate(); const requests: string[] = [];
      const { page, errors } = await open(browser, { [REPORT]: TARGETED }, "serve", g, requests, { at });
      await page.waitForFunction(() => !!document.querySelector('script[src*="math-chunk.js"]'), null, { timeout: 10000 });
      await frames(page, 6);   // the frames a spent heading or offset would have run in (spendHeading's, scrollToSourceOffset's)
      const held = await landing(page);
      assert.deepEqual([held.loader, held.paints, held.notice], [true, 0, null], "held: the loader stands and no notice speaks for a target the paint has not reached: " + JSON.stringify(held));
      g.open();
      await paintsReach(page, 1);
      await frames(page, 6);
      const b = await landing(page);
      assert.deepEqual([b.loader, b.katex, b.paints, b.notice], [false, 1, 1, null], "one paint, the formula laid out, no notice: " + JSON.stringify(b));
      assert.ok(b.scrollTop > 0, "the note no longer sits at its top: " + JSON.stringify(b));
      if ("heading" in at) {
        assert.ok(b.heading !== null && b.heading >= 0 && b.heading < 60, "the section's heading at the top of the body, as the synchronous fill lands it: " + JSON.stringify(b));
      } else {
        assert.ok(b.target !== null && b.target.top >= 0 && b.target.bottom <= b.clientHeight, "the offset's block in view: " + JSON.stringify(b));
      }
      assert.equal(requests.length, 1);
      assert.deepEqual(errors, []);
    });
  });
}

test("chromium: a Raw pick while a math note opened at an offset is held paints the rows and lands the offset there; the arrival changes nothing after it", { timeout: 60000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const g = gate(); const requests: string[] = [];
    const { page, errors } = await open(browser, { [REPORT]: TARGETED }, "serve", g, requests, { at: { offset: TARGET_OFFSET } });
    await page.waitForFunction(() => !!document.querySelector('script[src*="math-chunk.js"]'), null, { timeout: 10000 });
    await frames(page, 6);
    assert.equal((await landing(page)).loader, true, "held");
    await page.locator(".fileview-seg button", { hasText: "Raw" }).click();
    await frames(page, 6);
    const rows = (): Promise<{ rows: number; scrollTop: number; target: { top: number; bottom: number } | null; clientHeight: number; notice: string | null }> => page.evaluate(() => {
      const b = document.querySelector(".fileview-body") as HTMLElement;
      const bt = b.getBoundingClientRect().top;
      const r = Array.from(b.querySelectorAll(".fv-cl")).find((x) => (x.textContent || "").includes("Target paragraph here.")) as HTMLElement | undefined;
      const bar = document.getElementById("fileview-save-err");
      return { rows: b.querySelectorAll(".fv-cl").length, scrollTop: b.scrollTop, clientHeight: b.clientHeight, notice: bar ? bar.textContent : null,
        target: r ? { top: Math.round(r.getBoundingClientRect().top - bt), bottom: Math.round(r.getBoundingClientRect().bottom - bt) } : null };
    });
    const raw = await rows();
    assert.ok(raw.rows > 0 && raw.notice === null, "the rows are painted, no notice: " + JSON.stringify(raw));
    assert.ok(raw.target !== null && raw.target.top >= 0 && raw.target.bottom <= raw.clientHeight, "the offset's row in view: " + JSON.stringify(raw));
    g.open();
    await page.waitForFunction(() => (window as any).__rompKatex !== undefined, null, { timeout: 10000 });
    await frames(page, 6);
    const after = await rows();
    assert.deepEqual([after.scrollTop, after.rows, after.notice], [raw.scrollTop, raw.rows, null], "the arrival repaints nothing over the Raw view: " + JSON.stringify(after));
    assert.equal(requests.length, 1);
    assert.deepEqual(errors, []);
  });
});

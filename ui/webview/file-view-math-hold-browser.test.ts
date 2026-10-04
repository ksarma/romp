// The viewer's hold for a note with math (iOS item 6, 2026-10-02): KaTeX is an on-demand chunk (math-chunk.ts), and a Rendered
// paint whose block holds a formula still waiting for it is not swapped in. The body keeps the romp loader on an open, the chunk
// is fetched once, and the renderer's arrival paints, so the note's first paint is its final one: one paint, the hooks once,
// KaTeX in place, and the anchor map, the reader's place and the comment paint never meet a waiting formula. A note with no
// math fetches no chunk and paints at once; a chunk that fails to load paints the note with each formula as its source, and
// after it the next Rendered paint asks again, paints at once while the retry is out, and the served retry repaints the note
// once with the reader's place kept (math.ts: a failed load is retried, the review's round 1). The
// real viewer in Chromium through the shared harness (real-viewer-leg.ts), its bundle built WITHOUT KaTeX (bundleViewer(false))
// and loaded by src as the kernel's pages load theirs, so the chunk's URL derives from that tag as on a page (chunk-url.ts);
// the chunk is the shipped build of math-chunk.ts (math-chunk-leg.ts chunkBundle), held until the leg lets it go.
// A Rendered pick held over rows (held open, Raw, then Rendered; or a saved Raw preference, then Rendered with the chunk not yet
// fetched) puts the romp loader up over the rows, hidden and inert under it, in both viewers, and the arrival paints once with the
// place kept (file-view.ts holdOverBody; the review's round 1). The URL viewer opened at a #fragment on a math note holds the same
// way and lands the heading at the arrival's paint (its settle handler's repaint, otherwise run by no CI leg).
// An open's target waits with the held paint: a math note opened at a heading or at an offset before the chunk lands raises no
// notice while the loader stands and lands on its target at the arrival's paint (file-view.ts landTarget stands down while a
// paint is held; the arrival runs it after its paint), and a Raw pick that ends the hold first lands the offset in the rows.
// Before, the landing spent the target over the loader: the heading raised 'No section named' and both opens sat at the note's
// top once the chunk was in.
// A takeover of the body ends the hold (the review's round 2, correctness-1): a reload answered 404 while a paint is held paints its
// pane, and the renderer's arrival, a success or a failure, leaves the pane standing with the seam's error() keeping its sentence
// (before, the arrival painted the last text over it); the editor entered while held stays through the arrival, and its Cancel
// lands the open's offset in the Raw rows, as an exit before the arrival does (before, the arrival spent the offset into the editor).
// `window.__paints` counts the seam's onRendered. Synthetic values only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, bundleViewer, frames, paintsReach, topBlock, putAtTop, REPORT, PARA, ORIGIN } from "./real-viewer-leg";
import { chunkBundle, gate, type Gate } from "./math-chunk-leg";

const NOTE = "# Ratios\n\nThe ratio $\\frac{a}{b}$ holds.\n\n$$\\sum_{i=0}^{n} i^2$$\n\nAfter the formula.\n";
const PLAIN = "# Plain\n\nNo formula here, and $HOME stays literal.\n";
const OTHER = "/repo/notes-api/docs/plain.md";

type Answer = "serve" | "404";
/** The viewer opened in the Files pane over `docs` with its bundle by src; the chunk's URL answered under `chunk` (one answer, or
 *  one per request in order, the last repeating), every answer held by `g` and the n-th by `more.gates[n]`; `openOpts` is
 *  openFileView's third argument (an `at` target). `more` passes openViewer's url, urls, raw, waitFor and before through (the
 *  URL viewer, a saved Raw preference, a page global installed before the open). */
async function open(browser: any, docs: Record<string, string>, chunk: Answer | Answer[], g: Gate | null, requests: string[], openOpts: Record<string, unknown> | null = null,
  more: { gates?: (Gate | null)[]; url?: string; urls?: Record<string, string>; raw?: boolean; waitFor?: string; before?: (page: any) => Promise<void> } = {}) {
  return openViewer(browser, "pane", 900, 700, {
    docs, bundleSrc: "/dist/files.js?v=3", waitFor: more.waitFor || ".fileview-body", openOpts, url: more.url, urls: more.urls, raw: more.raw,
    // the editor's chunk is answered with a 404, so Edit opens the plain fallback editor (the editor-entry scene) and never runs the page as a script
    serve: (u) => (u.pathname === "/dist/files.js" ? { status: 200, type: "text/javascript", body: bundleViewer(false) }
      : u.pathname === "/dist/editor-chunk.js" ? { status: 404, type: "text/plain", body: "not found" } : null),
    before: async (page) => {
      await page.route((u: URL) => u.pathname === "/dist/math-chunk.js", async (route: any) => {
        const n = requests.length;
        requests.push(new URL(route.request().url()).pathname + new URL(route.request().url()).search);
        const answer = Array.isArray(chunk) ? chunk[Math.min(n, chunk.length - 1)] : chunk;
        if (g) await g.promise;
        const held = more.gates && more.gates[n];
        if (held) await held.promise;
        const c = chunkBundle();
        if (answer === "404" || "error" in c) return route.fulfill({ status: 404, contentType: "text/plain", body: "not found" });
        return route.fulfill({ status: 200, contentType: "text/javascript", body: c.js });
      });
      if (more.before) await more.before(page);
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

// The viewer's body as a reader sees it, for both viewers: whether the romp loader is on screen in it, whether the Raw rows show
// (and whether they are inert), the pressed buttons, the Rendered root and its KaTeX roots, and how many Rendered roots have been
// put into the page (countRoots, installed before the open; the URL viewer fires no seam paint, so a root is its paint).
const URL_PATH = "/notes-api/docs/report.md";
type Over = { loader: boolean; rowsShown: boolean; inert: boolean; pressed: string[]; md: boolean; katex: number; src: number; roots: number };
const overNow = (page: any): Promise<Over> => page.evaluate(() => {
  const b = document.querySelector(".fileview-body") as HTMLElement;
  const br = b.getBoundingClientRect();
  const load = b.querySelector(".fileview-load") as HTMLElement | null;
  const lr = load ? load.getBoundingClientRect() : null;
  const row = b.querySelector(".fv-cl") as HTMLElement | null;
  return { loader: !!lr && lr.height > 0 && lr.bottom > br.top && lr.top < br.bottom, rowsShown: !!row && getComputedStyle(row).visibility !== "hidden",
    inert: !!row && !!row.closest("[inert]"), pressed: Array.from(document.querySelectorAll(".fileview-seg button.on, .fileview-acts button.on")).map((x) => x.textContent || ""),
    md: !!b.querySelector(".fileview-md"), katex: b.querySelectorAll(".katex").length, src: b.querySelectorAll("code.md-math-src").length, roots: (window as any).__mdRoots };
});
/** Counts the `.fileview-md` roots put into the page (one per Rendered paint; the URL viewer fires no seam paint): installed before the open. */
const countRoots = async (page: any): Promise<void> => {
  await page.evaluate(() => {
    (window as any).__mdRoots = 0;
    new MutationObserver((recs) => { for (const r of recs) r.addedNodes.forEach((n) => { if (n instanceof HTMLElement && n.classList.contains("fileview-md")) (window as any).__mdRoots++; }); })
      .observe(document.body, { childList: true, subtree: true });
  });
};
const button = (page: any, label: string) => page.locator("#romp-fileview button.fileview-btn", { hasText: new RegExp("^" + label + "$") }).click();

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
    assert.deepEqual(b.src, ["Not rendered: the math renderer failed to load.", "Not rendered: the math renderer failed to load."]);
    assert.equal(b.paints, 1, "one paint");
    assert.equal(requests.length, 1, "the failure's own repaint of the held paint, inside the settle, uses no retry");
    assert.deepEqual(errors, []);
  });
});

// A note long enough that its target sits screens below the top, one inline formula at its head: the hold's case for a target.
const FILLER = Array.from({ length: 40 }, (_, i) => PARA(i + 1)).join("\n\n");
const TARGETED = "# Ratios\n\nThe ratio $\\frac{a}{b}$ holds.\n\n" + FILLER + "\n\n## Second\n\nTarget paragraph here.\n\n" + FILLER + "\n";
const TARGET_OFFSET = TARGETED.indexOf("Target paragraph here.");
// the same note with a second formula in its first paragraph: a paint that meets two formulas while a retry is out (the retry scene)
const TARGETED2 = TARGETED.replace("The ratio $\\frac{a}{b}$ holds.", "The ratio $\\frac{a}{b}$ holds, and $c^2$ with it.");

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

for (const viewer of ["file", "url"] as const) {
  test(`chromium: ${viewer === "file" ? "the Files pane's viewer" : "the URL viewer"}: after a failed load the next Rendered paint asks again and paints at once while the retry is out (no loader, the source shown); the retry, served, repaints the note once with KaTeX, the reader's place kept`, { timeout: 60000 }, async (t) => {
    await inBrowser(t, async (browser) => {
      const retry = gate(); const requests: string[] = [];
      const { page, errors } = await open(browser, { [REPORT]: TARGETED2 }, ["404", "serve"], null, requests, null, {
        gates: [null, retry], before: countRoots, ...(viewer === "url" ? { url: URL_PATH, urls: { [ORIGIN + URL_PATH]: TARGETED2 } } : {}),
      });
      await page.waitForFunction(() => !!document.querySelector(".fileview-body .fileview-md code.md-math-src"), null, { timeout: 15000 });
      await frames(page, 6);
      let b = await overNow(page);
      assert.deepEqual([b.loader, b.md, b.katex, b.roots], [false, true, 0, 1], "the failed load painted the note once, its formulas as source: " + JSON.stringify(b));
      assert.equal(requests.length, 1, "the failure's own repaint used no retry");
      await putAtTop(page, "Paragraph 20");
      await frames(page, 2);
      const before = await topBlock(page);
      await button(page, "Raw");
      await frames(page, 4);
      await button(page, "Rendered");
      await frames(page, 4);
      b = await overNow(page);
      assert.deepEqual([b.loader, b.md, b.katex, b.roots, b.src], [false, true, 0, 2, 2], "the Rendered paint stands at once, both formulas as source: nothing waits on the retry, the second formula met after the first used it included: " + JSON.stringify(b));
      assert.equal(requests.length, 2, "that paint's fill used the retry the failure armed");
      const during = await topBlock(page);
      assert.equal(during && during.text, before && before.text, "the place came back across Raw and Rendered: " + JSON.stringify([before, during]));
      retry.open();
      await page.waitForFunction(() => document.querySelectorAll(".fileview-body .katex").length === 2, null, { timeout: 15000 });
      await frames(page, 6);
      b = await overNow(page);
      assert.deepEqual([b.loader, b.katex, b.roots], [false, 2, 3], "the served retry laid both formulas out by one repaint of the note, so the hooks ran over them: " + JSON.stringify(b));
      assert.equal(await page.evaluate(() => document.querySelectorAll(".fileview-body code.md-math-src").length), 0, "no source left");
      const after = await topBlock(page);
      assert.ok(after !== null && before !== null && after.text === before.text && Math.abs(after.top - before.top) <= 1, "the reader's place kept across the repaint: " + JSON.stringify([before, after]));
      assert.equal(requests.length, 2);
      assert.deepEqual(errors, []);
    });
  });
}

// ── a Rendered pick held over rows (the review's round 1, ui-1): the loader goes up over the rows, which are hidden and inert, and
// the arrival paints once with the place kept; in the Files pane's viewer (openFileView) and the URL viewer (openUrlView) ──


for (const viewer of ["file", "url"] as const) {
  for (const route of ["held open, Raw, then Rendered", "saved Raw, cold chunk, Rendered"] as const) {
    test(`chromium: ${viewer === "file" ? "the Files pane's viewer" : "the URL viewer"}, ${route}: the loader stands over the hidden, inert rows while the paint is held, then one paint lays the note out with KaTeX, the place kept`, { timeout: 60000 }, async (t) => {
      await inBrowser(t, async (browser) => {
        const g = gate(); const requests: string[] = [];
        const saved = route.startsWith("saved");
        const { page, errors } = await open(browser, { [REPORT]: TARGETED }, "serve", g, requests, null, {
          raw: saved, before: countRoots, waitFor: saved ? ".fileview-body .fv-cl" : ".fileview-body",
          ...(viewer === "url" ? { url: URL_PATH, urls: { [ORIGIN + URL_PATH]: TARGETED } } : {}),
        });
        if (!saved) {
          await page.waitForFunction(() => !!document.querySelector('script[src*="math-chunk.js"]'), null, { timeout: 10000 });
          await frames(page, 4);
          assert.equal((await overNow(page)).loader, true, "held at the open: the open's loader");
          await button(page, "Raw");
          await page.waitForFunction(() => !!document.querySelector(".fileview-body .fv-cl"), null, { timeout: 10000 });
        } else {
          await frames(page, 4);
          assert.deepEqual(requests, [], "a saved Raw preference paints rows and fetches no chunk");
        }
        await frames(page, 2);
        await putAtTop(page, "Paragraph 20");
        await frames(page, 2);
        const before = await topBlock(page);
        assert.ok(before && before.view === "raw" && before.text.startsWith("Paragraph 20"), "the rows, Paragraph 20 at the top: " + JSON.stringify(before));
        const rootsBefore = (await overNow(page)).roots;
        await button(page, "Rendered");
        await page.waitForFunction(() => !!document.querySelector('script[src*="math-chunk.js"]'), null, { timeout: 10000 });
        await frames(page, 4);
        const held = await overNow(page);
        assert.deepEqual([held.loader, held.rowsShown, held.inert, held.md, held.roots], [true, false, true, false, rootsBefore],
          "held: the loader up, the rows under it hidden and inert, nothing painted: " + JSON.stringify(held));
        assert.ok(held.pressed.includes("Rendered") && !held.pressed.includes("Raw"), "under the pressed Rendered button: " + JSON.stringify(held));
        g.open();
        await page.waitForFunction(() => document.querySelectorAll(".fileview-body .katex").length === 1, null, { timeout: 15000 });
        await frames(page, 6);
        const after = await overNow(page);
        assert.deepEqual([after.loader, after.md, after.katex, after.roots - rootsBefore], [false, true, 1, 1], "one paint, the formula laid out, the loader gone: " + JSON.stringify(after));
        const top = await topBlock(page);
        assert.ok(top && top.view === "rendered" && top.text === before!.text && Math.abs(top.top - before!.top) <= 2, "the place kept across the held pick: " + JSON.stringify([before, top]));
        assert.equal(requests.length, 1);
        assert.deepEqual(errors, []);
      });
    });
  }
}

test("chromium: the URL viewer opened at a #fragment on a math note before the renderer is in keeps the loader, then paints once at the arrival with KaTeX, the heading at the body's top", { timeout: 60000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const g = gate(); const requests: string[] = [];
    const href = URL_PATH + "#second";
    const { page, errors } = await open(browser, { [REPORT]: TARGETED }, "serve", g, requests, null, {
      url: href, urls: { [ORIGIN + href]: TARGETED }, before: countRoots, waitFor: ".fileview-body",
    });
    await page.waitForFunction(() => !!document.querySelector('script[src*="math-chunk.js"]'), null, { timeout: 10000 });
    await frames(page, 6);
    const held = await overNow(page);
    assert.deepEqual([held.loader, held.md, held.roots], [true, false, 0], "held: the loader stands and no root is painted: " + JSON.stringify(held));
    g.open();
    await page.waitForFunction(() => document.querySelectorAll(".fileview-body .katex").length === 1, null, { timeout: 15000 });
    await frames(page, 8);
    const after = await overNow(page);
    assert.deepEqual([after.loader, after.md, after.katex, after.roots], [false, true, 1, 1], "the arrival repaints once (openUrlView's settle handler), the formula laid out, the loader gone: " + JSON.stringify(after));
    const l = await landing(page);
    assert.ok(l.heading !== null && l.heading >= 0 && l.heading < 60, "the fragment's heading at the body's top: " + JSON.stringify(l));
    assert.deepEqual(requests, ["/dist/math-chunk.js?v=3"], "one request");
    assert.deepEqual(errors, []);
  });
});

// ── a takeover of the body ends the hold (the review's round 2, correctness-1): the fetch chain's failure pane and the editor's entry ──

for (const answer of ["serve", "404"] as const) {
  test(`chromium: a reload answered 404 while a math note's paint is held paints its pane, and the renderer's arrival (${answer === "serve" ? "the chunk served" : "the chunk answered 404"}) leaves the pane standing, the seam's error() keeping its sentence`, { timeout: 60000 }, async (t) => {
    await inBrowser(t, async (browser) => {
      const g = gate(); const requests: string[] = [];
      const { page, errors } = await open(browser, { [REPORT]: NOTE }, answer, g, requests, null, {
        before: async (pg: any) => {
          // the chunk's script error, heard in the capture phase before math.ts's own onerror runs in the same dispatch: the 404's arrival
          await pg.evaluate(() => { document.addEventListener("error", (e) => { const s = e.target as HTMLScriptElement; if (s && s.src && s.src.includes("math-chunk.js")) (window as any).__chunkErrs = ((window as any).__chunkErrs || 0) + 1; }, true); });
        },
      });
      await page.waitForFunction(() => !!document.querySelector('script[src*="math-chunk.js"]'), null, { timeout: 10000 });
      await frames(page, 4);
      assert.deepEqual([(await bodyNow(page)).loader, (await bodyNow(page)).paints], [true, 0], "held at the open: the loader stands");
      await page.evaluate((p: string) => { delete (window as any).__docs[p]; (window as any).__seam.reload(); }, REPORT);
      await page.waitForFunction(() => !!document.querySelector(".fileview-body > .fileview-err"), null, { timeout: 10000 });
      const pane = (): Promise<{ pane: string | null; error: string | null; md: boolean; loader: boolean; katex: number; src: number }> => page.evaluate(() => {
        const b = document.querySelector(".fileview-body")!;
        const e = b.querySelector(":scope > .fileview-err");
        return { pane: e ? e.textContent : null, error: (window as any).__seam.error(), md: !!b.querySelector(".fileview-md"), loader: !!b.querySelector(".fileview-load"),
          katex: b.querySelectorAll(".katex").length, src: b.querySelectorAll("code.md-math-src").length };
      });
      const before = await pane();
      assert.ok(before.error && before.pane !== null && before.pane.includes(before.error) && !before.md && !before.loader, "the reload's 404 paints its pane over the held loader, and error() answers its sentence: " + JSON.stringify(before));
      g.open();
      if (answer === "serve") await page.waitForFunction(() => (window as any).__rompKatex !== undefined, null, { timeout: 10000 });
      else await page.waitForFunction(() => (window as any).__chunkErrs === 1, null, { timeout: 10000 });
      await frames(page, 8);
      const after = await pane();
      assert.deepEqual(after, before, "the arrival paints nothing over the pane: the pane stands, error() keeps its sentence, no text, no loader, no formula: " + JSON.stringify([before, after]));
      assert.equal(requests.length, 1);
      assert.deepEqual(errors, []);
    });
  });
}

test("chromium: the editor entered while a math note opened at an offset is held keeps the body through the renderer's arrival, and its Cancel lands the open's offset in the Raw rows", { timeout: 60000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const g = gate(); const requests: string[] = [];
    const { page, errors } = await open(browser, { [REPORT]: TARGETED }, "serve", g, requests, { at: { offset: TARGET_OFFSET } });
    await page.waitForFunction(() => !!document.querySelector('script[src*="math-chunk.js"]'), null, { timeout: 10000 });
    await frames(page, 6);
    assert.equal((await landing(page)).loader, true, "held at the open");
    await page.locator('#romp-fileview button[aria-label="Edit"]').click();
    await page.waitForFunction(() => !!document.querySelector(".fileview-body > textarea.fileview-editor"), null, { timeout: 10000 });   // the plain fallback editor: the editor's chunk answers 404
    await frames(page, 4);
    g.open();
    await page.waitForFunction(() => (window as any).__rompKatex !== undefined, null, { timeout: 10000 });
    await frames(page, 8);
    const ed = await page.evaluate(() => { const b = document.querySelector(".fileview-body")!; return { editor: !!b.querySelector(":scope > textarea.fileview-editor"), md: !!b.querySelector(".fileview-md"), loader: !!b.querySelector(".fileview-load"), rows: b.querySelectorAll(".fv-cl").length }; });
    assert.deepEqual(ed, { editor: true, md: false, loader: false, rows: 0 }, "the editor holds the body through the arrival: " + JSON.stringify(ed));
    await page.locator("#romp-fileview button.fileview-btn", { hasText: /^Cancel$/ }).click();
    await page.waitForFunction(() => !!document.querySelector(".fileview-body .fv-cl"), null, { timeout: 10000 });
    await frames(page, 6);
    const raw = await page.evaluate(() => {
      const b = document.querySelector(".fileview-body") as HTMLElement;
      const bt = b.getBoundingClientRect().top;
      const r = Array.from(b.querySelectorAll(".fv-cl")).find((x) => (x.textContent || "").includes("Target paragraph here.")) as HTMLElement | undefined;
      return { scrollTop: b.scrollTop, clientHeight: b.clientHeight, target: r ? { top: Math.round(r.getBoundingClientRect().top - bt), bottom: Math.round(r.getBoundingClientRect().bottom - bt) } : null };
    });
    assert.ok(raw.scrollTop > 0 && raw.target !== null && raw.target.top >= 0 && raw.target.bottom <= raw.clientHeight, "the Cancel's Raw paint lands the open's offset: its row in view: " + JSON.stringify(raw));
    assert.equal(requests.length, 1);
    assert.deepEqual(errors, []);
  });
});

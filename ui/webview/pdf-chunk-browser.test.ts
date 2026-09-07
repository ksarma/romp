// The BUILT chunk in a real engine (plans/file-review.md, Slice 4): what pdf-chunk.test.ts's fakes cannot
// show, because it takes a layout engine and the IntersectionObserver spec's own clipping rules —
//   - the observer's margin reaches a page BELOW the viewer's fold once its root is the scroller. The pages
//     live in `.fileview-body { overflow: auto }`; a rootMargin expands only the root's box, and an ancestor
//     between root and page clips without it, so with the implicit (viewport) root the margin was inert: a
//     page drew only once inside the body's visible box and was evicted the moment it left (2026-09-06).
//   - an undrawn or evicted canvas (0×0) keeps the page's box, since it carries the page's aspect-ratio, so
//     an overlay placed on it covers the page, not a 0-tall band, and scrolling to a region lands on it;
//   - a page pdf.js cannot read is loud IN the page, with no canvas left to take a region comment.
// Skips BY NAME without playwright's chromium (CI installs none; `npx playwright install chromium`). The chunk
// and its worker are built here from source with esbuild, into out-tests/, so the test never trusts a stale
// dist/. The viewer's rules for the elements involved are read from styles.css, the sheet the viewer loads.
//
// Fixtures are synthetic: hand-built PDFs of blank pages (tools/pdf-smoke.test.mjs's generator, copied so its
// own tests do not ride along), the origin TESTHOST, no recorded document.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";

const PKG = process.cwd();                                   // vscode-extension, where npm test runs
const ROOT = path.resolve(PKG, "..");
const OUT = path.join(PKG, "out-tests", "pdf-chunk-browser");
const req = createRequire(path.join(PKG, "package.json"));   // runtime requires: esbuild must not bundle playwright

let chromium: any = null;
let SKIP: string | false = false;
try {
  chromium = req("playwright").chromium;
  const exe: string = chromium.executablePath();
  if (!exe || !fs.existsSync(exe)) SKIP = "playwright's chromium is not installed here (`npx playwright install chromium` in vscode-extension); the built-chunk browser test did not run";
} catch {
  SKIP = "playwright is not installed under vscode-extension/node_modules (run `npm ci` there); the built-chunk browser test did not run";
}

/** A minimal PDF of blank US-letter pages with a correct xref; `badPage` replaces that page's object with a
 *  bare integer — a damaged page object pdf.js opens around but cannot read when asked for it. */
function minimalPdf(pageCount: number, badPage: number | null = null): Buffer {
  const objs = ["<< /Type /Catalog /Pages 2 0 R >>"];
  const kids = Array.from({ length: pageCount }, (_, i) => `${3 + i} 0 R`).join(" ");
  objs.push(`<< /Type /Pages /Kids [${kids}] /Count ${pageCount} >>`);
  for (let i = 0; i < pageCount; i++) objs.push(badPage === i + 1 ? "42" : "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>");
  let out = "%PDF-1.4\n";
  const offsets: number[] = [];
  objs.forEach((body, i) => { offsets.push(Buffer.byteLength(out, "latin1")); out += `${i + 1} 0 obj\n${body}\nendobj\n`; });
  const xref = Buffer.byteLength(out, "latin1");
  out += `xref\n0 ${objs.length + 1}\n0000000000 65535 f \n`;
  for (const o of offsets) out += `${String(o).padStart(10, "0")} 00000 n \n`;
  out += `trailer\n<< /Size ${objs.length + 1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`;
  return Buffer.from(out, "latin1");
}

/** The viewer's own rules for the elements the chunk lives in, from the sheet the viewer loads. */
function viewerRules(): string {
  const css = fs.readFileSync(path.join(ROOT, "ui", "webview", "styles.css"), "utf8");
  const rules = css.match(/^\.fileview-(?:body|pdfhost|pdf|pdf-page|pdf-canvas) \{[^}]*\}/gm) || [];
  assert.equal(rules.length, 5, "styles.css has one rule for each of .fileview-body, -pdfhost, -pdf, -pdf-page, -pdf-canvas");
  assert.match(rules.join("\n"), /\.fileview-body \{[^}]*overflow: auto/, "the body is the scroller this test is about");
  return rules.join("\n");
}

async function buildChunk(): Promise<void> {
  await req("esbuild").build({
    entryPoints: [
      path.join(ROOT, "ui", "webview", "pdf-chunk.ts"),
      { in: path.join(PKG, "node_modules", "pdfjs-dist", "build", "pdf.worker.mjs"), out: "pdf-worker" },
    ],
    nodePaths: [path.join(PKG, "node_modules")],
    bundle: true, format: "iife", platform: "browser", target: "es2020", outdir: OUT, logLevel: "silent",
  });
}

// the viewer's shape: .fileview (clips) > .fileview-body (scrolls; sized here as a pane would size it) > the host
const BODY_H = 600, BODY_W = 700;
const HTML = (rules: string) => `<!doctype html><html><head><meta charset="utf-8"><style>
${rules}
.fileview { overflow: hidden; }
.fileview-body { height: ${BODY_H}px; width: ${BODY_W}px; }
</style></head><body>
<div class="fileview"><div class="fileview-body" id="body"><div class="fileview-pdfhost" id="host"></div></div></div>
<script>
  // record the root every observer is created with, before the chunk loads
  window.__roots = [];
  const IO = window.IntersectionObserver;
  window.IntersectionObserver = class extends IO {
    constructor(cb, opts) { super(cb, opts); window.__roots.push(opts && opts.root ? opts.root.id || opts.root.tagName : null); }
  };
</script>
<script src="/dist/pdf-chunk.js?v=1725300000"></script>
</body></html>`;

interface Snap { index: number; w: number; h: number; box: number; wrapBox: number; top: number; err: string | null; hasCanvas: boolean }
const SNAP = `(() => Array.from(document.querySelectorAll(".fileview-pdf-page")).map((wr) => {
  const c = wr.querySelector("canvas"); const e = wr.querySelector(".fileview-err");
  return { index: Number(wr.dataset.page), w: c ? c.width : -1, h: c ? c.height : -1, box: c ? c.getBoundingClientRect().height : -1,
    wrapBox: wr.getBoundingClientRect().height, top: wr.offsetTop, err: e ? e.textContent : null, hasCanvas: !!c };
}))()`;

test("in Chromium: the observer's root is the scroller, a page below the fold is pre-drawn, a far page is evicted (keeping the page's box) and redrawn on return, and a page pdf.js cannot read is loud in place", { skip: SKIP }, async () => {
  await buildChunk();
  const html = HTML(viewerRules());
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage({ viewport: { width: 900, height: 900 } });
    const logs: string[] = [];
    page.on("console", (m: any) => logs.push(m.text()));
    page.on("pageerror", (e: Error) => logs.push("pageerror: " + e.message));
    await page.route("http://TESTHOST/**", (route: any) => {
      const u = new URL(route.request().url());
      if (u.pathname === "/view.html") return route.fulfill({ contentType: "text/html", body: html });
      const f = path.join(OUT, path.basename(u.pathname));
      if (u.pathname.startsWith("/dist/") && fs.existsSync(f)) return route.fulfill({ contentType: "application/javascript", body: fs.readFileSync(f) });
      return route.fulfill({ status: 404, body: "" });
    });
    await page.goto("http://TESTHOST/view.html");
    await page.waitForFunction(() => !!(window as any).__rompPdf, null, { timeout: 10000 });

    const render = (b64: string) => page.evaluate(async (b64: string) => {
      const bin = atob(b64); const u8 = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
      const w = window as any;
      if (w.__h) w.__h.dispose();
      w.__pages = []; w.__errs = [];
      const h = await w.__rompPdf.render(u8.buffer, document.getElementById("host"), {
        onPage: (p: { index: number }) => w.__pages.push(p.index),
        onPageError: (e: unknown) => w.__errs.push(e),
      });
      w.__h = h;
      return { pages: h.pages as number, roots: w.__roots as (string | null)[] };
    }, b64);
    const snap = (): Promise<Snap[]> => page.evaluate(SNAP);
    const drawnCount = (i: number) => page.evaluate((i: number) => (window as any).__pages.filter((x: number) => x === i).length, i);
    const waitDrawn = (i: number, times = 1) => page.waitForFunction(([i, n]: [number, number]) => (window as any).__pages.filter((x: number) => x === i).length >= n, [i, times], { timeout: 10000 });
    const waitEvicted = (i: number) => page.waitForFunction((i: number) => { const c = document.querySelector('canvas[data-page="' + i + '"]') as HTMLCanvasElement | null; return !!c && c.width === 0; }, i, { timeout: 10000 });
    const scrollTo = (top: number) => page.evaluate((t: number) => { document.getElementById("body")!.scrollTop = t; }, top);

    // ── six pages in a 600px body: the observer's root is the body, and page 2 — below the fold — is pre-drawn
    const six = await render(minimalPdf(6).toString("base64"));
    assert.equal(six.pages, 6);
    assert.deepEqual(six.roots, ["body"], "the observer was created with .fileview-body as its root, not the viewport");
    await waitDrawn(2);
    let s = await snap();
    assert.equal(s.length, 6);
    assert.ok(s[1].top > BODY_H, `page 2 begins below the body's visible box (top ${s[1].top} > ${BODY_H}) — and drew anyway: the margin reaches it`);
    assert.ok(s[1].top < 2 * BODY_H, "…because it begins within one body height of the fold");
    assert.ok(s[0].w > 0 && s[1].w > 0, "pages 1 and 2 have bitmaps");
    for (const p of s.slice(2)) {
      assert.equal(p.w, 0, `page ${p.index}, beyond the margin, has no bitmap`); assert.equal(p.h, 0);
      assert.ok(p.wrapBox > 800, "the shell has the page's extent");
      assert.ok(Math.abs(p.box - p.wrapBox) < 1, `an undrawn canvas keeps the page's box (${p.box} vs ${p.wrapBox}), not a 0-tall one`);
    }
    assert.ok(Math.abs(s[0].box - s[0].wrapBox) < 1, "a drawn canvas fills its wrapper");
    assert.equal(logs.filter((l) => l.startsWith("pageerror")).length, 0, logs.join("\n"));

    // ── scrolled so page 3 tops the body: page 1 (a body height above) is evicted and keeps its box; 3 and 4 draw; 5, 6 wait
    await scrollTo(s[2].top);
    await waitDrawn(3); await waitDrawn(4); await waitEvicted(1);
    s = await snap();
    assert.equal(s[0].w, 0, "page 1 gave its bitmap back");
    assert.ok(Math.abs(s[0].box - s[0].wrapBox) < 1, "…and its canvas box is still the page's, so an overlay on it still covers the page");
    assert.ok(s[1].w > 0, "page 2, within a body height above, is kept");
    assert.ok(s[2].w > 0 && s[3].w > 0, "pages 3 and 4 drawn");
    assert.equal(s[4].w, 0); assert.equal(s[5].w, 0);

    // ── back to the top: page 1 redraws (onPage again), page 4 — now beyond the margin — is evicted
    await scrollTo(0);
    await waitDrawn(1, 2); await waitEvicted(4);
    s = await snap();
    assert.ok(s[0].w > 0, "page 1 drawn again");
    assert.equal(await drawnCount(1), 2, "onPage fired for page 1 twice: the first draw and the redraw on return");
    assert.equal(s[3].w, 0);
    assert.equal(await drawnCount(2), 1, "page 2 never left the margin: one draw, no churn at the fold");

    // ── a PDF whose page 2 is a bare integer: the document opens, page 1 draws, page 2 is loud in its wrapper
    const bad = await render(minimalPdf(3, 2).toString("base64"));
    assert.ok(bad.pages >= 2, "pdf.js opens it (it may drop the pages after the damaged one from the count)");
    await page.waitForFunction(() => (window as any).__errs.length >= 1, null, { timeout: 10000 });
    const errs: { index: number; message: string }[] = await page.evaluate(() => (window as any).__errs);
    assert.equal(errs.length, 1); assert.equal(errs[0].index, 2);
    assert.ok(errs[0].message.length > 0, "pdf.js's message rides along");
    s = await snap();
    assert.ok(s[0].w > 0, "page 1 drew");
    assert.equal(s[1].hasCanvas, false, "page 2 has no canvas: nothing for a region comment to land on");
    assert.equal(s[1].err, "Page 2 did not render — " + errs[0].message, "the failure is in the page, naming it, in pdf.js's words");
    assert.ok(s[1].wrapBox > 800, "the failed page keeps its extent");
    assert.equal(await page.evaluate(() => (window as any).__pages.includes(2)), false, "no onPage for a page that did not draw");
  } finally {
    await browser.close();
  }
});

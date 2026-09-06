// The PDF chunk's REDRAW AT A NEW WIDTH (plans/file-review.md, Slice 4; the review of 2026-09-06). The pages
// are width-fit: a canvas is drawn for the root's width, and CSS keeps it the right size when that width changes
// (a pane resized, the narrow-layout flip), scaled from the old bitmap — soft. The chunk's ResizeObserver on the
// root is the sharpening: every page ON SCREEN with a bitmap drawn for another width is redrawn at the new one,
// onPage fires again with the same canvas (the header's "a redraw at a new width"), and the rest redraw when
// they next scroll in. Nothing executed that path before: the chunk's other tests delete ResizeObserver or hold
// the width constant, so the callback's body could be removed with every suite green.
//
// Two legs. NODE: makeRender over a stand-in pdf.js and a fake DOM, the observer fired by hand — which pages are
// redrawn (visible and drawn), which are not (undrawn, evicted, out of the window), the same width twice as a
// no-op, a zero width as a no-op, and the observer disconnected on dispose. CHROMIUM (skips by name without
// playwright's chromium): the built chunk, the viewer's own rules, and a REAL ResizeObserver — the body narrowed
// under a two-page document and widened back, each page redrawn once per change at the root's new width into the
// same canvas, with no draw from the observer's initial observation. Fixtures are synthetic: blank pages, TESTHOST.
import { test, beforeEach } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { makeRender, type PdfLib, type PageInfo } from "./pdf-chunk";

// ── a fake DOM: what the chunk touches of an element, and nothing else ──────────────────────────

class FakeEl {
  tagName: string;
  className = "";
  dataset: Record<string, string> = {};
  style: Record<string, string> = {};
  children: FakeEl[] = [];
  parentElement: FakeEl | null = null;
  textContent = "";
  clientWidth = 0;                            // a plain field: the test lays the root out by setting it
  width = 300; height = 150;
  constructor(tag: string) { this.tagName = tag.toUpperCase(); }
  appendChild(c: FakeEl): FakeEl { c.remove(); c.parentElement = this; this.children.push(c); return c; }
  remove(): void {
    const p = this.parentElement;
    if (p) { p.children.splice(p.children.indexOf(this), 1); this.parentElement = null; }
  }
  querySelector(sel: string): FakeEl | null {
    const [tag, cls] = sel.split(".");
    for (const c of this.children) {
      if ((!tag || c.tagName === tag.toUpperCase()) && (!cls || c.className.split(" ").includes(cls))) return c;
      const deep = c.querySelector(sel);
      if (deep) return deep;
    }
    return null;
  }
}
const el = (tag: string) => new FakeEl(tag);
const asEl = (e: FakeEl) => e as unknown as HTMLElement;
function viewerTree(): { container: FakeEl; body: FakeEl } {
  const view = el("div"); view.className = "fileview"; view.style.overflow = "hidden";
  const body = el("div"); body.className = "fileview-body"; body.style.overflow = "auto";
  const container = el("div"); container.className = "fileview-pdfhost";
  view.appendChild(body); body.appendChild(container);
  return { container, body };
}
const styleOf = (e: Element) => {
  const st = (e as unknown as FakeEl).style;
  return { overflowY: st.overflowY || st.overflow || "visible" };
};

// ── a fake pdf.js: blank US-letter pages that draw on request ───────────────────────────────────

interface FakeLib { lib: PdfLib; calls: { getPage: number[]; renders: number[]; destroyed: number } }
function fakeLib(pages: number): FakeLib {
  const calls = { getPage: [] as number[], renders: [] as number[], destroyed: 0 };
  class Cancelled extends Error {}
  const lib = {
    GlobalWorkerOptions: { workerSrc: "http://TESTHOST:29855/dist/pdf-worker.js" },
    RenderingCancelledException: Cancelled,
    getDocument: () => ({
      promise: Promise.resolve({
        numPages: pages,
        getPage: async (i: number) => {
          calls.getPage.push(i);
          return {
            getViewport: ({ scale }: { scale: number }) => ({ width: 612 * scale, height: 792 * scale }),
            render: () => {
              calls.renders.push(i);
              let cancel = () => {};
              const promise = new Promise<void>((res, rej) => {
                const t = setTimeout(res, 1);
                cancel = () => { clearTimeout(t); rej(new Cancelled("cancelled")); };
              });
              return { promise, cancel: () => cancel() };
            },
          };
        },
      }),
      destroy: async () => { calls.destroyed++; },
    }),
  };
  return { lib: lib as unknown as PdfLib, calls };
}

// ── the two observers, fired by hand ────────────────────────────────────────────────────────────

class FakeIO {
  static instances: FakeIO[] = [];
  targets: FakeEl[] = [];
  constructor(public cb: (entries: unknown[], io: FakeIO) => void, public opts: { root?: unknown; rootMargin?: string }) { FakeIO.instances.push(this); }
  observe(t: FakeEl): void { this.targets.push(t); }
  disconnect(): void {}
  fire(states: Array<[FakeEl, boolean]>): void { this.cb(states.map(([target, isIntersecting]) => ({ target, isIntersecting })), this); }
}
class FakeRO {
  static instances: FakeRO[] = [];
  targets: FakeEl[] = [];
  disconnected = false;
  constructor(public cb: () => void) { FakeRO.instances.push(this); }
  observe(t: FakeEl): void { this.targets.push(t); }
  disconnect(): void { this.disconnected = true; }
  /** The browser's notification: the observed element's size changed (or, at observe time, was first measured). */
  fire(): void { this.cb(); }
}

async function until(cond: () => boolean, what: string): Promise<void> {
  for (let i = 0; i < 2000; i++) { if (cond()) return; await new Promise((r) => setTimeout(r, 1)); }
  assert.fail("timed out waiting for " + what);
}
const settle = () => new Promise((r) => setTimeout(r, 15));   // long enough for any queued draw (1 ms each) to have landed
const canvasOf = (wrap: FakeEl) => wrap.querySelector("canvas.fileview-pdf-canvas")!;
const brief = (d: PageInfo[]) => d.map((p) => [p.index, p.width]);

beforeEach(() => {
  (globalThis as any).document = { createElement: el };
  (globalThis as any).getComputedStyle = styleOf;
  (globalThis as any).IntersectionObserver = FakeIO;
  (globalThis as any).ResizeObserver = FakeRO;
  FakeIO.instances.length = 0; FakeRO.instances.length = 0;
});

test("a width change redraws the pages on screen at the new width — the same canvas, onPage again — and none of the rest; the same width again, or no width, redraws nothing; dispose disconnects", async () => {
  const { lib, calls } = fakeLib(5);
  const { container } = viewerTree();
  const drawn: PageInfo[] = [];
  const h = await makeRender(lib)(new ArrayBuffer(16), asEl(container), { onPage: (p) => drawn.push(p) });
  const root = container.children[0];
  const wraps = root.children;
  assert.equal(FakeRO.instances.length, 1, "one ResizeObserver for the document");
  const ro = FakeRO.instances[0];
  assert.deepEqual(ro.targets, [root], "it watches the root the pages are fit to");
  const io = FakeIO.instances[0];
  // an unlaid-out root (0 wide) draws page 1 at the page's natural width
  assert.deepEqual(brief(drawn), [[1, 612]]);
  const c1 = canvasOf(wraps[0]);
  // pages 1 and 2 on screen, 3–5 beyond the margin: page 2 draws, at the same (natural) width
  io.fire([[wraps[0], true], [wraps[1], true], [wraps[2], false], [wraps[3], false], [wraps[4], false]]);
  await until(() => drawn.length >= 2, "page 2's first draw");
  assert.deepEqual(brief(drawn), [[1, 612], [2, 612]]);

  // the observer's first notification, at the width already drawn for: nothing to sharpen
  ro.fire();
  await settle();
  assert.equal(drawn.length, 2, "no redraw at an unchanged width");

  // ── the root is laid out 800 wide (a pane resized, the narrow-layout flip): the two pages on screen redraw at 800
  root.clientWidth = 800;
  ro.fire();
  await until(() => drawn.length >= 4, "the redraws of pages 1 and 2 at the new width");
  assert.deepEqual(brief(drawn), [[1, 612], [2, 612], [1, 800], [2, 800]], "the pages on screen, in page order, at the new width");
  assert.equal(drawn[2].canvas, c1 as unknown as HTMLCanvasElement, "the same canvas element: an overlay keyed on it holds");
  assert.equal(c1.width, 800, "the backing store is the new width (ratio 1 under node)");
  assert.equal(Math.round(c1.height), Math.round(800 * 792 / 612));
  for (const w of wraps.slice(2)) assert.equal(canvasOf(w).width, 0, "a page beyond the margin has no bitmap to sharpen and is left alone");
  const fetched = calls.getPage.length;

  // the same width again (the observer can report a change in height alone): a no-op
  ro.fire();
  await settle();
  assert.equal(drawn.length, 4, "no redraw when the width is the one already drawn for");
  assert.equal(calls.renders.length, 4);
  assert.equal(calls.getPage.length, fetched, "the page proxies are kept; a redraw asks pdf.js for nothing but pixels");

  // a page scrolling in AFTER the change draws at the current width — no sharpening pass is needed for it
  io.fire([[wraps[2], true]]);
  await until(() => drawn.length >= 5, "page 3's draw");
  assert.deepEqual(brief(drawn)[4], [3, 800]);

  // an evicted page has no bitmap: a width change skips it, and it draws at the new width on return
  io.fire([[wraps[1], false]]);
  assert.equal(canvasOf(wraps[1]).width, 0, "page 2 gave its bitmap back");
  root.clientWidth = 700;
  ro.fire();
  await until(() => drawn.length >= 7, "pages 1 and 3 at 700");
  assert.deepEqual(brief(drawn).slice(5), [[1, 700], [3, 700]], "the pages on screen with a bitmap — page 2, evicted, is not among them");
  assert.equal(canvasOf(wraps[1]).width, 0);
  io.fire([[wraps[1], true]]);
  await until(() => drawn.length >= 8, "page 2's return");
  assert.deepEqual(brief(drawn)[7], [2, 700], "drawn at the current width on return");

  // the root measured at no width (hidden, or detached mid-render): nothing to fit to, nothing redrawn
  root.clientWidth = 0;
  ro.fire();
  await settle();
  assert.equal(drawn.length, 8, "no redraw at a zero width");
  assert.equal(c1.width, 700, "the bitmaps are kept as they were");

  // dispose: the observer is disconnected, and a late notification draws nothing
  h.dispose();
  assert.ok(ro.disconnected, "dispose disconnects the ResizeObserver");
  root.clientWidth = 900;
  ro.fire();
  await settle();
  assert.equal(drawn.length, 8); assert.equal(calls.renders.length, 8);
});

test("without a ResizeObserver the chunk renders and no observer is asked for; with one, it is created after the pages exist and before the first draw resolves", async () => {
  delete (globalThis as any).ResizeObserver;
  const { lib } = fakeLib(1);
  const { container } = viewerTree();
  const h = await makeRender(lib)(new ArrayBuffer(16), asEl(container));
  assert.equal(FakeRO.instances.length, 0);
  assert.equal(h.pages, 1);
  h.dispose();
  // with one: the root is observed by the time render() resolves (page 1 drawn) — a width change during the
  // first draw is caught, not missed
  (globalThis as any).ResizeObserver = FakeRO;
  const t2 = viewerTree();
  let observedWhenResolved: FakeEl[] | null = null;
  const h2 = await makeRender(fakeLib(1).lib)(new ArrayBuffer(16), asEl(t2.container));
  observedWhenResolved = FakeRO.instances[0]?.targets ?? null;
  assert.deepEqual(observedWhenResolved, [t2.container.children[0]]);
  h2.dispose();
});

// ── in Chromium: a real ResizeObserver, the body narrowed under the pages and widened back ──────

const PKG = process.cwd();                                   // vscode-extension, where npm test runs
const ROOT = path.resolve(PKG, "..");
const req = createRequire(path.join(PKG, "package.json"));   // runtime requires: esbuild must not bundle playwright
let chromium: any = null;
let SKIP: string | false = false;
try {
  chromium = req("playwright").chromium;
  const exe: string = chromium.executablePath();
  if (!exe || !fs.existsSync(exe)) SKIP = "playwright's chromium is not installed here (`npx playwright install chromium` in vscode-extension); the resize browser test did not run";
} catch {
  SKIP = "playwright is not installed under vscode-extension/node_modules (run `npm ci` there); the resize browser test did not run";
}

/** A minimal PDF of blank US-letter pages with a correct xref (the generator the other chunk tests copy). */
function minimalPdf(pageCount: number): Buffer {
  const objs = ["<< /Type /Catalog /Pages 2 0 R >>"];
  const kids = Array.from({ length: pageCount }, (_, i) => `${3 + i} 0 R`).join(" ");
  objs.push(`<< /Type /Pages /Kids [${kids}] /Count ${pageCount} >>`);
  for (let i = 0; i < pageCount; i++) objs.push("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>");
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
  return rules.join("\n");
}
/** The chunk and pdf.js's worker, built as esbuild.js builds them, in memory (no dist/ trusted, nothing on disk). */
function bundle(entry: string): string {
  const r = req("esbuild").buildSync({
    entryPoints: [entry], bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(PKG, "node_modules")], logLevel: "silent",
  });
  return r.outputFiles[0].text as string;
}

// the viewer's shape: .fileview (clips) > .fileview-body (scrolls; sized as a pane would size it) > the host. Two
// pages: both within the body's one-height margin at every width used, so a width change redraws exactly both.
const BODY_H = 600, WIDE = 700, NARROW = 500;
const HTML = (rules: string) => `<!doctype html><html><head><meta charset="utf-8"><style>
${rules}
body { margin: 0; }
.fileview { overflow: hidden; }
.fileview-body { height: ${BODY_H}px; width: ${WIDE}px; }
</style></head><body>
<div class="fileview"><div class="fileview-body" id="body"><div class="fileview-pdfhost" id="host"></div></div></div>
<script src="/dist/pdf-chunk.js?v=1725300000"></script>
</body></html>`;

interface Drawn { index: number; width: number; same: boolean }
interface Snap { rootWidth: number; dpr: number; canvases: Array<{ index: number; w: number; h: number }>; drawn: Drawn[] }
const SNAP = `(() => {
  const root = document.querySelector(".fileview-pdf");
  return { rootWidth: root ? root.clientWidth : -1, dpr: window.devicePixelRatio,
    canvases: Array.from(document.querySelectorAll("canvas.fileview-pdf-canvas")).map((c) => ({ index: Number(c.dataset.page), w: c.width, h: c.height })),
    drawn: window.__drawn };
})()`;

test("in Chromium: narrowing the body under two drawn pages redraws each once at the root's new width into the same canvas, widening it back redraws them again, and the observer's first notification draws nothing", { skip: SKIP }, async () => {
  const chunkJs = bundle(path.join(ROOT, "ui", "webview", "pdf-chunk.ts"));
  const workerJs = bundle(path.join(PKG, "node_modules", "pdfjs-dist", "build", "pdf.worker.mjs"));
  const html = HTML(viewerRules());
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage({ viewport: { width: 900, height: 900 } });
    const errors: string[] = [];
    page.on("pageerror", (e: Error) => errors.push("pageerror: " + e.message));
    await page.route("http://TESTHOST/**", (route: any) => {
      const u = new URL(route.request().url());
      const js = (b: string) => route.fulfill({ status: 200, contentType: "application/javascript", body: b });
      if (u.pathname === "/view.html") return route.fulfill({ contentType: "text/html", body: html });
      if (u.pathname === "/dist/pdf-chunk.js") return js(chunkJs);
      if (u.pathname === "/dist/pdf-worker.js") return js(workerJs);
      return route.fulfill({ status: 404, body: "" });
    });
    await page.goto("http://TESTHOST/view.html");
    await page.waitForFunction(() => !!(window as any).__rompPdf, null, { timeout: 10000 });
    const pages = await page.evaluate(async (b64: string) => {
      const bin = atob(b64); const u8 = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
      const w = window as any;
      w.__drawn = [];
      const h = await w.__rompPdf.render(u8.buffer, document.getElementById("host"), {
        onPage: (p: { index: number; width: number; canvas: HTMLCanvasElement }) => w.__drawn.push({
          index: p.index, width: p.width, same: p.canvas === document.querySelector('.fileview-pdf-page[data-page="' + p.index + '"] canvas'),
        }),
      });
      w.__h = h;
      return h.pages as number;
    }, minimalPdf(2).toString("base64"));
    assert.equal(pages, 2);
    const drawnOf = (i: number) => page.evaluate((i: number) => (window as any).__drawn.filter((d: any) => d.index === i).length, i);
    const waitDrawn = (i: number, times: number) => page.waitForFunction(([i, n]: [number, number]) => (window as any).__drawn.filter((d: any) => d.index === i).length >= n, [i, times], { timeout: 10000 });
    const snap = (): Promise<Snap> => page.evaluate(SNAP);
    const setWidth = (px: number) => page.evaluate((px: number) => { document.getElementById("body")!.style.width = px + "px"; }, px);

    // ── both pages drawn once at the wide root; the observer's initial notification added no draw
    await waitDrawn(2, 1);
    await page.waitForTimeout(100);                         // room for a spurious redraw to show up, if there were one
    let s = await snap();
    const wide = s.rootWidth;
    assert.ok(wide > 0 && wide < WIDE, `the root is laid out inside the ${WIDE}px body (${wide}px)`);
    assert.deepEqual(s.drawn.map((d) => [d.index, Math.round(d.width), d.same]), [[1, wide, true], [2, wide, true]], "one draw each, at the root's width, into the page's own canvas");
    assert.deepEqual(s.canvases.map((c) => [c.index, c.w]), [[1, Math.round(wide * s.dpr)], [2, Math.round(wide * s.dpr)]]);

    // ── the body narrows (a pane resized): the root's width changes, both pages redraw once at the new width
    await setWidth(NARROW);
    await waitDrawn(1, 2); await waitDrawn(2, 2);
    await page.waitForTimeout(100);
    s = await snap();
    const narrow = s.rootWidth;
    assert.ok(narrow > 0 && narrow < wide, `the root narrowed (${wide} → ${narrow})`);
    assert.deepEqual(s.drawn.slice(2).map((d) => [d.index, Math.round(d.width), d.same]), [[1, narrow, true], [2, narrow, true]], "the redraws: the same canvases, at the new width, once each");
    assert.deepEqual(s.canvases.map((c) => [c.index, c.w]), [[1, Math.round(narrow * s.dpr)], [2, Math.round(narrow * s.dpr)]], "the backing stores are the new width — sharp, not CSS-scaled from the old bitmap");
    assert.equal(await drawnOf(1), 2); assert.equal(await drawnOf(2), 2);

    // ── and back: redrawn again at the wide width
    await setWidth(WIDE);
    await waitDrawn(1, 3); await waitDrawn(2, 3);
    await page.waitForTimeout(100);
    s = await snap();
    assert.equal(s.rootWidth, wide);
    assert.deepEqual(s.drawn.slice(4).map((d) => [d.index, Math.round(d.width), d.same]), [[1, wide, true], [2, wide, true]]);
    assert.deepEqual(s.canvases.map((c) => [c.index, c.w]), [[1, Math.round(wide * s.dpr)], [2, Math.round(wide * s.dpr)]]);
    assert.equal(s.drawn.length, 6, "no draw beyond one per page per width change");

    // ── dispose: a later width change draws nothing
    await page.evaluate(() => (window as any).__h.dispose());
    await setWidth(NARROW);
    await page.waitForTimeout(150);
    assert.equal(await page.evaluate(() => (window as any).__drawn.length), 6);
    assert.deepEqual(errors, [], errors.join("\n"));
  } finally {
    await browser.close();
  }
});

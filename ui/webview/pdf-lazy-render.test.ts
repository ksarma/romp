// The PDF renderer chunk, EXECUTED (plans/file-review.md, Slice 4; the 2026-09-06 review). pdf-lazy.test.ts pins
// the chunk's source and runs render()'s two refusals; this file runs render() past them, on synthetic PDFs, and
// checks the DOM the Comments panel depends on with the panel's OWN lookups — file-view's pdfPages()
// (`.fileview-pdf .fileview-pdf-page`) and file-comments' regionImages() (`canvas.fileview-pdf-canvas` inside each
// wrapper), both read from their sources, so a renamed selector moves this test rather than leaving it green. The
// gap it closes: a canvas appended to the root instead of its page wrapper, or wrappers never attached, left every
// pin and every stub-driven test green while regionImages() found nothing — no overlay, no region comment on any
// page, and no error (paintRegions returns on an empty list).
//
// Two legs. NODE (runs in CI): makeRender over pdf.js's legacy build — the one pdf.js supports under Node; the
// modern build the chunk ships imports iterator helpers Node 22 lacks — drawing into @napi-rs/canvas (pdf.js's own
// optional dependency, which npm ci installs) through a DOM stand-in of a few lines whose querySelector is real
// enough for the panel's two selectors. Pixels are read back, so the page's fill landing in the wrapper's canvas is
// the proof, not the element's class. BROWSER (skips loudly without playwright + Chromium; CI installs no browsers):
// the production bundles — pdf-chunk.ts and pdf.js's worker built as esbuild.js builds them — served over a fake
// origin with a ?v= token, laid out as the viewer lays them out (a scrolling .fileview-body around the host), in
// headless Chromium: the worker fetched at the URL derived from the chunk's own tag, token and all; page 1 drawn
// before render() resolves; page 2 drawn only once scrolled within the scroller's margin; dispose() emptying the host.
//
// What a wrapper holds, in both legs: its canvas, and — while a draw is pending with no bitmap — the romp loader over it
// (div.fileview-load.fileview-pdf-page-load, the chunk's cue(); pdf-chunk-page-cue.test.ts owns its timing) and nothing
// else. A drawn page's wrapper is its canvas alone: the cue leaves with the bitmap. The cue's swirl resolves through
// mediaSrc() — /media on the page origin with no host-injected base — so the browser leg serves the extension's own
// swirl there, as the kernel does: an unserved swirl is a console error, and the leg asserts a clean console.
//
// Synthetic fixtures only: the PDFs are built here as bytes (blank pages with one filled rectangle each, a
// hand-built cross-reference table), never a recorded document — tools/pdf-smoke.test.mjs builds its fixture the
// same way, and is not imported because importing a test file registers its tests here too.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";
import type { PdfLib, PageInfo, PageError } from "./pdf-chunk";

const EXT = process.cwd();                                        // npm test runs in vscode-extension
const UI = path.resolve(EXT, "..", "ui", "webview");
const requireExt = createRequire(path.join(EXT, "package.json"));  // resolves from the extension's node_modules
const W = (f: string) => fs.readFileSync(path.join(UI, f), "utf8");
const VIEW = W("file-view.ts");
const COMMENTS = W("file-comments.ts");
const LEGACY = path.join(EXT, "node_modules", "pdfjs-dist", "legacy", "build", "pdf.mjs");

/** The chunk, loaded on first use rather than at import: its module imports pdf.js's modern build, which cannot load
 *  on a Node below pdfjs-dist's floor — pdf-lazy.test.ts's floor test names that; the legs here skip past it. */
const chunk = () => require("./pdf-chunk") as typeof import("./pdf-chunk");
const PDFJS_LOADS = typeof (globalThis as any).Iterator !== "undefined" && typeof (Promise as any).withResolvers === "function";
const BELOW_FLOOR = "pdf.js cannot load on Node " + process.versions.node + " — pdf-lazy.test.ts's floor test names the floor; this leg skips";

// ── the panel's lookups, from the sources that own them ──────────────────────────────────────────
/** file-view's pdfPages(): the wrappers the panel keys its overlays on, as it finds them in the viewer's body. */
function pagesSelector(): string {
  const m = VIEW.match(/pdfPages: \(\) => \([^\n]*?querySelectorAll\("([^"]+)"\)/);
  assert.ok(m, "file-view's pdfPages() lookup moved — re-anchor");
  return m![1];
}
/** file-comments' regionImages(): the canvas it looks for INSIDE each wrapper — no canvas, no overlay, no notice. */
function canvasSelector(): string {
  const m = COMMENTS.match(/regionImages\(\)[\s\S]{0,800}?pages\.map\(\(pg\) => pg\.querySelector\("([^"]+)"\)\)/);
  assert.ok(m, "file-comments' regionImages() per-page canvas lookup moved — re-anchor");
  return m![1];
}

// ── the fixture: a valid PDF from bytes, one filled rectangle per page ────────────────────────────
type PageSpec = { box: [number, number, number, number]; content?: string };
/** `pages` in order, each on its own MediaBox with an optional content stream; `kids` overrides the page tree's
 *  Kids (object numbers) so a test can name an object that is not there. The xref table is correct: pdf.js would
 *  reconstruct a broken one, which is not what these tests lean on. */
function syntheticPdf(pages: PageSpec[], kids?: number[]): Uint8Array {
  const objs = ["<< /Type /Catalog /Pages 2 0 R >>"];
  const pageIds: number[] = [];
  const bodies: Array<{ id: number; contentId: number | null; p: PageSpec }> = [];
  let next = 3;
  for (const p of pages) { const id = next++; const contentId = p.content ? next++ : null; pageIds.push(id); bodies.push({ id, contentId, p }); }
  const kidIds = kids || pageIds;
  objs.push(`<< /Type /Pages /Kids [${kidIds.map((i) => i + " 0 R").join(" ")}] /Count ${kidIds.length} >>`);
  for (const { contentId, p } of bodies) {
    objs.push(`<< /Type /Page /Parent 2 0 R /MediaBox [${p.box.join(" ")}]${contentId ? ` /Contents ${contentId} 0 R` : ""} >>`);
    if (contentId) objs.push(`<< /Length ${Buffer.byteLength(p.content!, "latin1")} >>\nstream\n${p.content}\nendstream`);
  }
  let out = "%PDF-1.4\n";
  const offsets: number[] = [];
  objs.forEach((body, i) => { offsets.push(Buffer.byteLength(out, "latin1")); out += `${i + 1} 0 obj\n${body}\nendobj\n`; });
  const xref = Buffer.byteLength(out, "latin1");
  out += `xref\n0 ${objs.length + 1}\n0000000000 65535 f \n`;
  for (const o of offsets) out += `${String(o).padStart(10, "0")} 00000 n \n`;
  out += `trailer\n<< /Size ${objs.length + 1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`;
  return new Uint8Array(Buffer.from(out, "latin1"));
}
// page 1: US letter, portrait, black over its top-left quarter; page 2: landscape, blue over its bottom-right quarter.
// Different boxes and different corners, so a canvas drawn with the wrong page, or one page drawn twice, shows.
const LETTER: PageSpec = { box: [0, 0, 612, 792], content: "0 0 0 rg 0 396 306 396 re f" };
const LANDSCAPE: PageSpec = { box: [0, 0, 792, 612], content: "0 0 1 rg 396 0 396 306 re f" };
const TWO_PAGES = () => syntheticPdf([LETTER, LANDSCAPE]);
/** render() takes an ArrayBuffer: the fixture's own (a fresh Uint8Array over a Buffer copy owns its whole buffer). */
const bufferOf = (u: Uint8Array): ArrayBuffer => u.buffer as ArrayBuffer;
const HOST_WIDTH = 800;                                  // the host's laid-out width: pages draw width-fit to it
const H1 = Math.round(HOST_WIDTH * 792 / 612);           // 1035: page 1's CSS height at that width
const H2 = Math.round(HOST_WIDTH * 612 / 792);           // 618: page 2's
const BLACK = "0,0,0,255", BLUE = "0,0,255,255", WHITE = "255,255,255,255";
/** A wrapper's children as `TAG.class.class` — the shape both legs assert a wrapper's contents in. */
const CANVAS_KID = "CANVAS.fileview-pdf-canvas";
const CUE_KID = "DIV.fileview-load.fileview-pdf-page-load";
const kidsOf = (w: { childNodes: ArrayLike<{ tagName: string; className: string }> }): string[] =>
  Array.from(w.childNodes, (c) => [c.tagName, ...c.className.split(/\s+/).filter(Boolean)].join("."));

/** An event the test waits for, with a backstop so a draw that never comes fails by name instead of hanging. */
function awaited<T>(what: string, arm: (fire: (v: T) => void) => void): Promise<T> {
  return new Promise<T>((res, rej) => {
    const t = setTimeout(() => rej(new Error(what + " did not happen within 10 s")), 10000);
    arm((v) => { clearTimeout(t); res(v); });
  });
}

// ── the node leg: makeRender over the legacy build, a DOM stand-in, real pixels ───────────────────
// The stand-in models what render() and the panel's lookups touch: createElement, className/dataset/style, the tree
// (appendChild, remove, parentNode), clientWidth (the nearest laid-out ancestor's width; 0 detached, as a browser
// reports an element not in the document), textContent, and querySelector(All) for `tag.class` compounds joined
// by the descendant combinator — anything else throws, so a lookup the stand-in cannot honour is loud, not false.
class El {
  readonly tagName: string;
  className = "";
  textContent = "";
  dataset: Record<string, string> = {};
  style: Record<string, string> = {};
  childNodes: El[] = [];
  parentNode: El | null = null;
  /** the width layout gives this box — set on the host; inherited by what is inside it */
  layoutWidth?: number;
  constructor(tag: string) { this.tagName = tag.toUpperCase(); }
  get parentElement(): El | null { return this.parentNode; }
  get firstChild(): El | null { return this.childNodes[0] || null; }
  appendChild(c: El): El { c.remove(); c.parentNode = this; this.childNodes.push(c); return c; }
  remove(): void { const p = this.parentNode; if (p) { p.childNodes.splice(p.childNodes.indexOf(this), 1); this.parentNode = null; } }
  get clientWidth(): number { for (let n: El | null = this; n; n = n.parentNode) if (n.layoutWidth !== undefined) return n.layoutWidth; return 0; }
  *descendants(): Generator<El> { for (const c of this.childNodes) { yield c; yield* c.descendants(); } }
  querySelectorAll(sel: string): El[] {
    const parts = sel.trim().split(/\s+/);
    const out: El[] = [];
    for (const d of this.descendants()) {
      if (!matches(d, parts[parts.length - 1])) continue;
      let i = parts.length - 2;
      for (let a = d.parentNode; i >= 0 && a && a !== this; a = a.parentNode) if (matches(a, parts[i])) i--;
      if (i < 0) out.push(d);
    }
    return out;
  }
  querySelector(sel: string): El | null { return this.querySelectorAll(sel)[0] || null; }
}
function matches(el: El, compound: string): boolean {
  const m = /^([a-zA-Z]*)((?:\.[\w-]+)*)$/.exec(compound);
  if (!m) throw new Error("the DOM stand-in does not understand the selector " + JSON.stringify(compound) + " — extend it");
  if (m[1] && el.tagName !== m[1].toUpperCase()) return false;
  const classes = el.className.split(/\s+/);
  return m[2].split(".").filter(Boolean).every((c) => classes.includes(c));
}
/** A canvas whose pixels are @napi-rs/canvas's. The size the chunk assigns is recorded as assigned (0×0 is the chunk's
 *  "no bitmap"; the library cannot hold a 0-sized surface, so the backing store resizes only for a real size). */
class CanvasEl extends El {
  private napi: any;
  private w = 300; private h = 150;                       // the element default, as a browser's
  constructor(create: (w: number, h: number) => any) { super("canvas"); this.napi = create(300, 150); }
  get width(): number { return this.w; }
  set width(v: number) { this.w = v; if (v > 0) this.napi.width = v; }
  get height(): number { return this.h; }
  set height(v: number) { this.h = v; if (v > 0) this.napi.height = v; }
  getContext(kind: string, opts?: unknown): any { return this.napi.getContext(kind, opts); }
}
const pixel = (c: CanvasEl, x: number, y: number): string => Array.from(c.getContext("2d").getImageData(x, y, 1, 1).data as Uint8ClampedArray).join(",");

type Rendering = { render: ReturnType<typeof import("./pdf-chunk").makeRender>; body: El; host: El; restore(): void };
/** The legacy build, a fake document installed for the chunk, and a viewer-shaped tree: .fileview-body > .fileview-pdfhost
 *  (the host render() is given, HOST_WIDTH wide). Returns null (after skipping) where the leg cannot run. */
async function nodeLeg(t: { skip(msg: string): void }): Promise<Rendering | null> {
  if (!PDFJS_LOADS) { t.skip(BELOW_FLOOR); return null; }
  let napi: any = null;
  try { napi = requireExt("@napi-rs/canvas"); } catch { napi = null; }
  if (!napi) {
    const why = "@napi-rs/canvas is not installed under vscode-extension — pdf.js's optional dependency, which npm ci installs where a prebuilt binary exists; the node leg cannot draw without it";
    // on the platform CI runs (the lockfile carries its binary) a missing addon is a broken install, not a skip
    if (process.platform === "linux" && process.arch === "x64") assert.fail(why);
    t.skip(why); return null;
  }
  const doc = { currentScript: null, querySelectorAll: () => [] as never[], createElement: (tag: string) => (tag === "canvas" ? new CanvasEl(napi.createCanvas) : new El(tag)) };
  const g = globalThis as any;
  const had = "document" in g, before = g.document;
  g.document = doc;
  // the legacy module by its own file URL: pdf.js's default worker path (./pdf.worker.mjs) and its require of
  // @napi-rs/canvas both resolve relative to that file, so nothing is configured — the smoke test's arrangement
  const legacy = (await import(pathToFileURL(LEGACY).href)) as PdfLib;
  const render = chunk().makeRender(legacy);
  const body = new El("div"); body.className = "fileview-body";
  const host = new El("div"); host.className = "fileview-pdfhost"; host.layoutWidth = HOST_WIDTH; body.appendChild(host);
  return { render, body, host, restore: () => { if (had) g.document = before; else delete g.document; } };
}

test("node: render() builds the DOM the panel reads — each wrapper pdfPages() finds holds the canvas regionImages() looks for, and the page's pixels are in it", async (t) => {
  const leg = await nodeLeg(t);
  if (!leg) return;
  try {
    const { render, body, host } = leg;
    const drawn: PageInfo[] = [];
    let onSecond: ((p: PageInfo) => void) | null = null;
    const second = awaited<PageInfo>("page 2's draw", (fire) => { onSecond = fire; });
    const h = await render(bufferOf(TWO_PAGES()), host as unknown as HTMLElement, { onPage: (p) => { drawn.push(p); if (p.index === 2) onSecond!(p); } });
    assert.equal(h.pages, 2);
    // one root in the container: div.fileview-pdf, the seam's mediaElement() and the sheet's rules
    assert.equal(host.childNodes.length, 1, "render() appends exactly one element to its container");
    const root = host.firstChild!;
    assert.equal(root.className, "fileview-pdf");
    // the wrappers, as file-view's pdfPages() finds them in the body
    const wrappers = body.querySelectorAll(pagesSelector());
    assert.equal(wrappers.length, 2, "pdfPages()'s lookup finds one wrapper per page");
    assert.deepEqual(wrappers.map((w) => w.dataset.page), ["1", "2"], "numbered from 1, in page order, as the wire's target.page is");
    for (const w of wrappers) {
      assert.equal(w.parentNode, root, "each wrapper is a child of the root");
      assert.equal(w.style.position, "relative", "the overlay's anchor: inline, load-bearing");
    }
    // what each wrapper holds at resolve: page 1 drawn, so its canvas alone (the loader left with the bitmap); page 2
    // asked eagerly (no observer under node) and still drawing, so its canvas with the loader over it — nothing else
    assert.deepEqual(kidsOf(wrappers[0]), [CANVAS_KID], "a drawn page's wrapper holds its canvas and nothing else");
    assert.deepEqual(kidsOf(wrappers[1]), [CANVAS_KID, CUE_KID], "a pending page's wrapper holds its canvas, first, and the loader over it");
    // the canvases, as file-comments' regionImages() finds them INSIDE each wrapper — the contract the stubs restate
    const canvases = wrappers.map((w) => w.querySelector(canvasSelector()) as CanvasEl | null);
    assert.ok(canvases.every(Boolean), "regionImages()'s lookup finds a canvas in every wrapper");
    for (let i = 0; i < 2; i++) {
      assert.equal(canvases[i]!.parentNode, wrappers[i], "the canvas is the wrapper's own child");
      assert.equal(canvases[i]!.dataset.page, wrappers[i].dataset.page, "the canvas carries its page's number (pageOf)");
    }
    // page 1 was drawn before the promise resolved, into ITS canvas, at the host's laid-out width
    assert.deepEqual(drawn.map((p) => p.index), [1], "onPage fired for page 1 alone before render() resolved");
    assert.equal(drawn[0].canvas, canvases[0] as unknown as HTMLCanvasElement, "onPage hands the panel the same canvas the lookup finds");
    assert.equal(drawn[0].width, HOST_WIDTH); assert.equal(Math.round(drawn[0].height), H1);
    assert.equal(canvases[0]!.width, HOST_WIDTH, "width-fit to the container: the root was attached before the first draw read its width");
    assert.equal(canvases[0]!.height, H1);
    assert.equal(canvases[1]!.width + "x" + canvases[1]!.height, "0x0", "a page not yet drawn has no bitmap: 0×0, never the element default");
    assert.equal(pixel(canvases[0]!, 10, 10), BLACK, "page 1's fill is in page 1's canvas");
    assert.equal(pixel(canvases[0]!, HOST_WIDTH - 10, H1 - 15), WHITE);
    assert.equal(wrappers[0].style.aspectRatio, "612 / 792");
    // no observer under node: every page draws — page 2 into its own canvas, at its own aspect
    const p2 = await second;
    assert.deepEqual(drawn.map((p) => p.index), [1, 2]);
    assert.deepEqual(kidsOf(wrappers[1]), [CANVAS_KID], "page 2's bitmap is in: its loader is gone, the canvas alone remains");
    assert.equal(p2.canvas, canvases[1] as unknown as HTMLCanvasElement);
    assert.equal(p2.width, HOST_WIDTH); assert.equal(Math.round(p2.height), H2);
    assert.equal(canvases[1]!.width, HOST_WIDTH); assert.equal(canvases[1]!.height, H2);
    assert.equal(wrappers[1].style.aspectRatio, "792 / 612", "the shell took page 1's aspect until page 2 was read; drawn, it has its own");
    assert.equal(canvases[1]!.style.aspectRatio, "792 / 612");
    assert.equal(pixel(canvases[1]!, HOST_WIDTH - 20, H2 - 20), BLUE, "page 2's fill is in page 2's canvas");
    assert.equal(pixel(canvases[1]!, 10, 10), WHITE);
    // dispose: the root and everything in it leaves the container; the lookups find nothing; a second call is inert
    h.dispose();
    assert.equal(host.childNodes.length, 0, "dispose() removes the root");
    assert.equal(body.querySelectorAll(pagesSelector()).length, 0);
    h.dispose();
  } finally { leg.restore(); }
});

test("node: a later page pdf.js cannot read keeps its wrapper, loses its canvas — regionImages() finds one canvas fewer — and says so in place, once", async (t) => {
  const leg = await nodeLeg(t);
  if (!leg) return;
  const warn = console.warn; const warned: string[] = [];
  console.warn = (...a: unknown[]) => { warned.push(a.map(String).join(" ")); };
  try {
    const { render, body, host } = leg;
    const errors: PageError[] = [];
    let onError: ((e: PageError) => void) | null = null;
    const failed = awaited<PageError>("page 2's failure", (fire) => { onError = fire; });
    // the page tree names a second kid that is not there: page 1 opens, page 2 cannot be read
    const h = await render(bufferOf(syntheticPdf([LETTER], [3, 99])), host as unknown as HTMLElement, { onPageError: (e) => { errors.push(e); onError!(e); } });
    assert.equal(h.pages, 2, "the document says two pages, so two shells");
    const e = await failed;
    assert.equal(e.index, 2);
    assert.ok(e.message.length > 0, "pdf.js's own message");
    const wrappers = body.querySelectorAll(pagesSelector());
    assert.equal(wrappers.length, 2, "the failed page keeps its wrapper, so the pages after it keep their places");
    const canvases = wrappers.map((w) => w.querySelector(canvasSelector()));
    assert.ok(canvases[0], "page 1's canvas is there");
    assert.equal(canvases[1], null, "page 2's canvas is gone: a page that will never have a bitmap takes no region comment");
    const note = wrappers[1].querySelector(".fileview-err");
    assert.ok(note, "the failure is shown in the wrapper, in the viewer's error dress");
    assert.equal(note!.textContent, "Page 2 did not render — " + e.message);
    assert.equal(errors.length, 1, "onPageError fired once");
    assert.equal(warned.filter((w) => w.startsWith("pdf-chunk: page 2 did not render")).length, 1, "the chunk warned once, by page");
    h.dispose();
    assert.equal(host.childNodes.length, 0);
  } finally { console.warn = warn; leg.restore(); }
});

// ── the browser leg: the production bundles in Chromium ─────────────────────────────────────────
let pw: any = null;
try { pw = requireExt("playwright"); } catch { pw = null; }
/** The webview build's options for one entry (esbuild.js's `webview`: iife, browser, es2020), as waiting-pane-browser.test.ts builds. */
function webviewBundle(entry: string): string {
  const esbuild = requireExt("esbuild");
  const r = esbuild.buildSync({
    entryPoints: [entry], bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent",
  });
  return r.outputFiles[0].text as string;
}
const V = "?v=1725300000";
// the viewer's layout around the host: a scrolling body 500px tall (styles.css: .fileview-body { overflow: auto }),
// so page 2 (1035px down) starts outside the scroller's box and its one-height margin
const VIEW_HTML = `<!DOCTYPE html><html><head><meta charset=utf-8><style>body{margin:0}.fileview-body{overflow:auto;height:500px;width:900px}.fileview-pdfhost{width:${HOST_WIDTH}px}.fileview-pdf-canvas{display:block;width:100%;height:auto}</style></head>
<body><div id=body class=fileview-body><div id=host class=fileview-pdfhost></div></div><script src="/dist/pdf-chunk.js${V}"></script></body></html>`;

test("chromium: the built chunk and worker — the worker fetched at the chunk's URL with its token, pages as the panel reads them, page 1 before resolve, page 2 once scrolled near, dispose", async (t) => {
  if (!pw) { t.skip("playwright is not installed under vscode-extension — the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw.chromium.launch(); }
  catch (e) { t.skip("no playwright chromium on this box — the browser leg needs it (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  try {
    const chunkJs = webviewBundle(path.join(UI, "pdf-chunk.ts"));
    const workerJs = webviewBundle(path.join(EXT, "node_modules", "pdfjs-dist", "build", "pdf.worker.mjs"));
    // the loader's swirl, as the kernel serves it at /media on the page origin — the URL mediaSrc() resolves to with no
    // host-injected base; a page cue whose swirl 404s is a console error, and the leg ends on a clean console
    const swirl = fs.readFileSync(path.join(EXT, "media", "romp-swirl-glyph.svg"));
    const page = await browser.newPage({ viewport: { width: 1000, height: 700 } });
    const errors: string[] = [], served: string[] = [];
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    page.on("console", (m: any) => { if (m.type() === "error" || m.type() === "warning") errors.push("console." + m.type() + ": " + m.text()); });
    await page.route("http://romp.test/**", (route: any) => {
      const u = new URL(route.request().url());
      served.push(u.pathname + u.search);
      const js = (b: string) => route.fulfill({ status: 200, contentType: "application/javascript", body: b });
      if (u.pathname === "/view") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: VIEW_HTML });
      if (u.pathname === "/dist/pdf-chunk.js") return js(chunkJs);
      if (u.pathname === "/dist/pdf-worker.js") return js(workerJs);
      if (u.pathname === "/media/romp-swirl-glyph.svg") return route.fulfill({ status: 200, contentType: "image/svg+xml", body: swirl });
      return route.fulfill({ status: 404, body: "" });
    });
    await page.goto("http://romp.test/view");
    const first = await page.evaluate(async ([b64, pagesSel, canvasSel]: string[]) => {
      const bin = atob(b64); const u8 = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
      const w = window as any;
      const drawn: Array<{ index: number; width: number; height: number; same: boolean }> = []; w.__drawn = drawn;
      const body = document.getElementById("body")!, host = document.getElementById("host")!;
      const wrapperOf = (i: number) => body.querySelectorAll(pagesSel)[i - 1];
      const h = await w.__rompPdf.render(u8.buffer, host, { onPage: (p: any) => drawn.push({ index: p.index, width: p.width, height: p.height, same: p.canvas === wrapperOf(p.index)?.querySelector(canvasSel) }) });
      w.__handle = h;
      const wrappers = Array.from(body.querySelectorAll(pagesSel)) as HTMLElement[];
      const canvases = wrappers.map((pg) => pg.querySelector(canvasSel) as HTMLCanvasElement | null);
      const px = (c: HTMLCanvasElement, x: number, y: number) => Array.from(c.getContext("2d")!.getImageData(x, y, 1, 1).data).join(",");
      // each wrapper's children as TAG.class.class (kidsOf's shape, restated here: the page has no access to the test's scope)
      const kidOf = (c: Node) => [(c as HTMLElement).tagName, ...String((c as HTMLElement).className).split(/\s+/).filter(Boolean)].join(".");
      const kids = (p: HTMLElement) => Array.from(p.childNodes, kidOf);
      w.__kids = kids;
      // page 2's wrapper, watched from before the scroll: every child added or removed, in order — the loader going up
      // when the observer asks for its draw and coming down as the bitmap lands (records arrive on microtasks, so the
      // log is complete before the draw's onPage is seen from outside)
      const log2: string[][] = []; w.__log2 = log2;
      new MutationObserver((recs) => {
        for (const r of recs) { for (const n of Array.from(r.addedNodes)) log2.push(["add", kidOf(n)]); for (const n of Array.from(r.removedNodes)) log2.push(["remove", kidOf(n)]); }
      }).observe(wrappers[1], { childList: true });
      return {
        pages: h.pages as number, hostChildren: host.childNodes.length, rootClass: (host.firstChild as HTMLElement).className,
        wrappers: wrappers.map((p) => p.dataset.page + " " + getComputedStyle(p).position + " " + p.style.aspectRatio + " " + Math.round(p.getBoundingClientRect().height)),
        canvases: canvases.map((c) => c && (c.dataset.page + " " + c.width + "x" + c.height + " " + Math.round(c.getBoundingClientRect().width))),
        kids: wrappers.map(kids),
        dpr: window.devicePixelRatio, drawn: drawn.slice(),
        p1: [px(canvases[0]!, 10, 10), px(canvases[0]!, canvases[0]!.width - 10, canvases[0]!.height - 15)],
      };
    }, [Buffer.from(TWO_PAGES()).toString("base64"), pagesSelector(), canvasSelector()]);
    const dpr = first.dpr as number;
    assert.equal(first.pages, 2);
    assert.equal(first.hostChildren, 1); assert.equal(first.rootClass, "fileview-pdf");
    // the worker: fetched once, from the chunk's own directory, with the chunk's token — derived from the tag, not configured
    assert.deepEqual(served.filter((s) => s.includes("pdf-worker")), ["/dist/pdf-worker.js" + V], "the worker rode the chunk's URL, ?v= and all");
    // page 1's cue went up before its draw: its swirl was fetched where mediaSrc() points with no injected base — the
    // page origin's /media, the kernel's route (once at least; a later cue's identical <img> may come from the image cache)
    assert.ok(served.includes("/media/romp-swirl-glyph.svg"), "the loader's swirl was fetched from /media on the page origin; served: " + served.join(" "));
    // the shells, as the panel reads them: both wrappers at page 1's aspect until page 2 is read, page 1's canvas drawn at the host's width
    assert.deepEqual(first.wrappers, ["1 relative 612 / 792 " + H1, "2 relative 612 / 792 " + H1]);
    assert.deepEqual(first.canvases, ["1 " + Math.round(HOST_WIDTH * dpr) + "x" + Math.round(H1 * dpr) + " " + HOST_WIDTH, "2 0x0 " + HOST_WIDTH],
      "page 1 drawn (backing store at the display's ratio), page 2 an empty 0×0 canvas the width of the page");
    // page 1 drawn (its loader left with the bitmap); page 2 beyond the scroller's margin with nothing pending, so no
    // loader over it yet: each wrapper holds its canvas alone
    assert.deepEqual(first.kids, [[CANVAS_KID], [CANVAS_KID]], "each wrapper holds its canvas and nothing else: page 1 drawn, page 2 not yet asked");
    assert.deepEqual(first.drawn, [{ index: 1, width: HOST_WIDTH, height: HOST_WIDTH * 792 / 612, same: true }], "page 1 before resolve, into the canvas the lookup finds; page 2 is outside the scroller's margin");
    assert.deepEqual(first.p1, [BLACK, WHITE]);
    // scroll the BODY (the viewer's scroller, the observer's root) by a fixed 600px: page 2 comes within the margin
    // and draws, and page 1 (0–1035) stays inside the window (100–1600), so no eviction and redraw of page 1 can
    // interleave — scrolling to the bottom would take page 1 out, then bring it back when page 2's shell shrinks to
    // its own aspect and the scroll clamps, and the redraw's onPage is the chunk working, not what this asserts
    await page.evaluate(() => { document.getElementById("body")!.scrollTop = 600; });
    await page.waitForFunction(() => (window as any).__drawn.some((d: any) => d.index === 2), null, { timeout: 10000 });
    const second = await page.evaluate(([pagesSel, canvasSel]: string[]) => {
      const w = window as any;
      const wrappers = Array.from(document.getElementById("body")!.querySelectorAll(pagesSel)) as HTMLElement[];
      const c = wrappers[1].querySelector(canvasSel) as HTMLCanvasElement;
      const px = (x: number, y: number) => Array.from(c.getContext("2d")!.getImageData(x, y, 1, 1).data).join(",");
      return { drawn: w.__drawn, aspect2: wrappers[1].style.aspectRatio, size2: c.width + "x" + c.height, p2: [px(c.width - 20, c.height - 20), px(10, 10)], kids2: w.__kids(wrappers[1]) as string[], log2: w.__log2 as string[][] };
    }, [pagesSelector(), canvasSelector()]);
    assert.deepEqual(second.drawn.map((d: any) => [d.index, d.same]), [[1, true], [2, true]], "page 2 drew once, into the canvas its wrapper holds; page 1 was not redrawn");
    assert.deepEqual(second.log2, [["add", CUE_KID], ["remove", CUE_KID]], "page 2 wore the loader from the moment its draw was asked until its bitmap landed, and nothing else came or went");
    assert.deepEqual(second.kids2, [CANVAS_KID], "page 2's bitmap is in: the loader it wore while drawing is gone, the canvas alone remains");
    assert.equal(second.aspect2, "792 / 612", "drawn, page 2's shell has its own aspect");
    assert.equal(second.size2, Math.round(HOST_WIDTH * dpr) + "x" + Math.round(H2 * dpr));
    assert.deepEqual(second.p2, [BLUE, WHITE], "page 2's fill is in page 2's canvas");
    // dispose empties the host; nothing errored or warned in the page along the way
    assert.equal(await page.evaluate(() => { (window as any).__handle.dispose(); return document.getElementById("host")!.childNodes.length; }), 0);
    assert.deepEqual(errors, [], "no page error, no console error or warning");
  } finally { await browser.close(); }
});

// The file viewer's PDF RENDERER (plans/file-review.md, Slice 4): pdf.js drawing each page into a
// canvas of its own, so a page has coordinates the viewer can put a region comment on — the browser's
// own PDF frame gives a page neither coordinates nor a selection. This module is its OWN esbuild entry
// (dist/pdf-chunk.js), with pdf.js's parser as a second asset beside it (dist/pdf-worker.js), loaded on
// demand by file-view.ts the first time a PDF opens — people who never open one download nothing, and
// the main chat/feed/files bundles stay byte-stable (they import nothing from here; the contract is the
// window global at the bottom, exactly as editor-chunk.ts does it). No plugin API (the 2026-08-20
// doctrine): what this module exposes is the one render() call below, curated for the viewer. pdf.js's
// annotation, form, text-layer, printing and scripting machinery stay out.
//
// THE CAPS ARE LOUD, AND THERE ARE TWO: render() refuses bytes over `maxBytes` (25 MB by default) with an
// Error naming the size and the cap, before pdf.js sees a byte; and it refuses a page COUNT over `maxPages`
// (5,000 by default) with an Error naming the count and the cap, once pdf.js has opened the document and
// before a single page shell exists. The caller shows the frame instead and says why; nothing here
// degrades quietly. The second cap exists because bytes do not bound pages: pdf.js reads the count from the
// page tree's /Count and checks only that the LAST page resolves (a nested Pages node is skipped by its own
// /Count on the way), so a PDF of a few hundred bytes can declare millions of pages, open, and draw page 1 —
// while the shells below are built synchronously, two elements and one observed target per page, so an
// unchecked count would hold the pane's thread for a minute or exhaust its memory before the first paint. A
// real document rarely approaches the cap (even a text-only PDF at the byte cap runs to thousands of pages,
// not millions), and 5,000 shells build in well under a second; over it, the person gets the browser's
// frame and the refusal's message.
//
// THE WORKER: pdf.js parses in a Worker it creates from `GlobalWorkerOptions.workerSrc`. That URL is
// derived at load from this chunk's OWN <script src> — same directory, same ?v= token — so a rebuilt
// kernel serves a matching worker, and the kernel's /dist route (which types by suffix) serves it as
// JavaScript because esbuild emits it as pdf-worker.js, not .mjs. No script tag to derive from means
// render() throws, again by name.
//
// THE BOUNDARY: a PDF is untrusted input — sessions download PDFs into the trees the viewer shows, and the person
// opens them — and this module parses it on the dashboard's authenticated origin (pdf.js in that same-origin
// Worker, the pages painted on the main thread), where the browser's own PDF viewer would have parsed it in a
// process of its own. Pixels are the only sink: pdf.js's core alone is imported, never pdfjs-dist/web, so no text
// layer, annotation layer, form field, link or script from the file reaches the DOM; getDocument is handed bytes,
// never a URL, so pdf.js fetches nothing; and the installed build has no eval path. Those properties are stated
// under "Security posture" in plans/file-review.md and held against this file and the installed package by
// ui/webview/file-review-posture.test.ts. Upgrading pdfjs-dist re-verifies the no-eval property (it belongs to the
// installed version, not to the API) and restates it there if the answer changes; anything that would let PDF
// content become DOM — a text layer over a page, clickable links — widens the sink list and is stated there first.
//
// PUBLIC API — the window global `__rompPdf`:
//
//   render(bytes: ArrayBuffer, container: HTMLElement, opts?: {
//     maxBytes?: number;                                   // default DEFAULT_MAX_BYTES (25 MB)
//     maxPages?: number;                                   // default DEFAULT_MAX_PAGES (5,000)
//     onPage?: (page: { index: number; canvas: HTMLCanvasElement; width: number; height: number }) => void;
//     onPageError?: (page: { index: number; message: string }) => void;
//   }) => Promise<{ pages: number; dispose(): void }>
//
//   Appends ONE root element (div.fileview-pdf) to `container`, holding one wrapper per page
//   (div.fileview-pdf-page, `position: relative`, data-page 1-based, sized to the page's aspect so the
//   scroller has its full extent before any pixel is drawn) with one canvas each (canvas.fileview-pdf-canvas,
//   data-page too, CSS width 100%, the page's aspect-ratio too so its box is the page's whether or not a
//   bitmap is in it). A canvas with no bitmap is 0×0 — from the start, and again after an eviction — so an
//   overlay reading its backing store as the page's natural size sees "unknown", never a stray default; and a
//   canvas with a bitmap holds a COMPLETE one. The draw is STAGED (paint): pdf.js draws each page into a canvas of
//   its own, off the DOM, and the page's canvas takes the finished bitmap in one synchronous step — sized, then
//   filled, with nothing else running on the main thread between — so no reader of it (the panel cutting a card's
//   crop, an overlay measuring it) ever finds it sized and empty, and a sharpening redraw keeps the old bitmap on
//   screen, CSS-scaled, until the new one replaces it. Drawing in place did neither: assigning a canvas's width or
//   height resets its bitmap, and pdf.js fills its target white before the first operator runs (a microtask in,
//   the operators following in animation frames), so every draw blanked the page for its whole length, a redraw
//   flashed white, and a crop cut meanwhile was blank and kept (the review, 2026-09-06; pdf-chunk-staged-draw.test.ts).
//   A page whose draw is PENDING — asked of the pump, queued behind the draws ahead of it or in flight — with no
//   bitmap to show meanwhile carries the romp loader over its sheet (div.fileview-load.fileview-pdf-page-load: the
//   viewer's own loader markup on the viewer's own classes, absolutely positioned over the wrapper, pointer-events
//   none so the panel's overlay under it still takes the pointer), from the moment the draw is asked until the
//   bitmap lands, the page fails (the notice takes its place) or the page is evicted; never for a sharpening
//   redraw, whose scaled bitmap is already on screen, and never on a failed page, whose wait nothing will end.
//   Before it, an undrawn sheet was a white sheet — indistinguishable from an empty page or a quiet failure for
//   as long as a heavy page took to draw, and behind the serial pump a page on screen waited on pages off it
//   with no cue at all (the review, 2026-09-06; ui/CLAUDE.md's loading-state rule). Pending pages are the pages
//   inside the observer's margin, so a long document animates a few of these, never thousands. The wordmark's
//   colour is the sheet's to set for the white ground (as .fileview-pdf-page .fileview-err does for the notice).
//   Pages are drawn width-fit to the root, lazily as they scroll within one height of the SCROLLER — the
//   nearest ancestor of `container` that scrolls (scrollRootFor; the viewport when none does) is the
//   IntersectionObserver's root, because a margin on the implicit root never reaches a page clipped by a
//   scrolling ancestor: with the viewer's `.fileview-body { overflow: auto }` in between, an implicit-root
//   observer drew a page only once it was inside the body's visible box and evicted it the moment it left
//   (found 2026-09-06). Every page draws eagerly when the observer is absent. A page that scrolls beyond
//   that margin drops its bitmap and redraws on return, so a long document costs the memory of the pages
//   near the reader, not of all of them. onPage fires after EVERY draw of a page — the first, a redraw on
//   return, a redraw at a new width — with the canvas (the same element for the page's whole life) and its
//   CSS size; an overlay that positions by fractions of that size stays correct without listening for
//   resizes. The promise resolves once the first page is drawn (or at once for a page-less document — a
//   /Count of zero or below reports `pages: 0`, so the caller's page-less path runs and no blank root is
//   mounted); it rejects for bytes over the cap, a page count over the cap, a missing worker URL, or anything
//   pdf.js refuses to open (a corrupt file, a password), each with pdf.js's or this module's own message —
//   and in every one of those cases nothing of this module's is in the container and the Worker pdf.js made for
//   the attempt is terminated (getDocument starts one per call, and pdf.js's own failure path only rejects, so
//   without that a refused open held a live Worker per attempt for the tab's life). A LATER page pdf.js cannot read or
//   draw (a damaged page object) is loud in place: its wrapper keeps the page's extent and shows the
//   failure (div.fileview-err naming the page and pdf.js's message), its canvas is removed — a page that
//   will never have a bitmap must not take a region comment, and the panel keys its overlays on the canvas —
//   onPageError fires once with the message, and the page is not retried. dispose() cancels the draws in
//   flight, releases the document, and removes the root.
//
// LOADING IT — for file-view.ts to copy (the editor chunk's loader with the names changed; keep the
// structural type inline, since `import type` from here would still be an import for the lazy-discipline
// pin to catch):
//
//   let pdfChunk: Promise<{ render: (bytes: ArrayBuffer, container: HTMLElement, opts?: object) =>
//     Promise<{ pages: number; dispose(): void }> }> | null = null;
//   const pdfChunkLoad = () => pdfChunk || (pdfChunk = new Promise((res, rej) => {
//     const w = window as any;
//     if (w.__rompPdf) return res(w.__rompPdf);
//     const self = Array.from(document.querySelectorAll("script[src]"))
//       .map((n) => (n as HTMLScriptElement).src).find((u) => /\/(render|feed|files)\.js/.test(u));
//     if (!self) return rej(new Error("no bundle script tag to derive the PDF chunk URL from"));
//     const sc = document.createElement("script");
//     sc.src = self.replace(/\/(render|feed|files)\.js/, "/pdf-chunk.js");
//     sc.onload = () => { const p = (window as any).__rompPdf; p ? res(p) : rej(new Error("PDF chunk loaded but did not register")); };
//     sc.onerror = () => { pdfChunk = null; rej(new Error("the PDF renderer failed to load")); };
//     document.head.appendChild(sc);
//   }));
//
// NOT SHIPPED YET (follow-ups, each a dist asset of its own): pdf.js's standard-font files (a PDF that
// does not embed Helvetica or Times falls back to a system font, with a console warning), its CMaps (some
// CJK text), and the OpenJPEG wasm (JPEG 2000 images render blank). Pages still render without them.
//
// TESTING IT: `render` is `makeRender(pdfjsLib)` over the modern build imported below, which is what the
// browsers run. That build needs a newer engine than the Node the tests run on, and pdf.js supports only
// its legacy build under Node — so a test hands makeRender the legacy build (or a stand-in) and drives the
// same pump, observer and failure paths against it; the browser test loads the built chunk as shipped. Their canvases
// are stand-ins — record-only fakes, or elements over @napi-rs/canvas in the legacy-build legs — and the staged draw's
// copy reads its source through the stage's own context's `.canvas` (the stage itself in a browser), which is what
// lets a stand-in over the library hand drawImage the library's surface, the one source it takes.
import * as pdfjsLib from "pdfjs-dist";
import type { PDFDocumentProxy, PDFPageProxy, RenderTask } from "pdfjs-dist";
import { mediaSrc } from "./media";   // the loader's swirl: the host-injected media base, as every asset URL resolves

/** The default bytes cap: a PDF over this is refused, not rendered (the plan's stated cap). */
export const DEFAULT_MAX_BYTES = 25 * 1024 * 1024;

/** The default page-count cap: a PDF declaring more pages than this is refused once pdf.js has opened it and
 *  before any page shell is built. Bytes do not bound this (see the header): the count comes from the page
 *  tree's /Count, which pdf.js does not verify beyond resolving the last page. Every page costs two elements and
 *  an observed target up front, built synchronously, so the count is what bounds that work. */
export const DEFAULT_MAX_PAGES = 5000;

/** Largest canvas backing store this module allocates per page, in device pixels: under every current
 *  engine's canvas limit (Safari's is the lowest at 16.7 M), so a poster-sized page draws softer rather
 *  than not at all. */
export const MAX_CANVAS_PIXELS = 16 * 1024 * 1024;

export interface PageInfo { index: number; canvas: HTMLCanvasElement; width: number; height: number }
export interface PageError { index: number; message: string }
export interface RenderOpts { maxBytes?: number; maxPages?: number; onPage?: (page: PageInfo) => void; onPageError?: (page: PageError) => void }
export interface RenderHandle { pages: number; dispose(): void }
/** What render() uses of pdf.js: the modern build in production, the legacy build (the one pdf.js supports
 *  under Node) or a stand-in in a test — see makeRender. */
export type PdfLib = Pick<typeof pdfjsLib, "getDocument" | "GlobalWorkerOptions" | "RenderingCancelledException">;

/** Bytes for a human, at the precision that matters at each size (pure; the cap message uses it). */
export function fmtBytes(n: number): string {
  if (n >= 1024 * 1024) return (n / (1024 * 1024)).toFixed(1) + " MB";
  if (n >= 1024) return Math.round(n / 1024) + " KB";
  return n + " bytes";
}

/** The refusal's exact text: the size AND the cap, so the person knows how far over they are (pure). */
export function capMessage(size: number, cap: number): string {
  return `this PDF is ${fmtBytes(size)}, over the ${fmtBytes(cap)} cap for rendering pages in the viewer`;
}

/** An integer with thousands separators, locale-independent (pure; the page-cap message uses it, and a test
 *  can pin the text on any machine). */
export function fmtCount(n: number): string {
  return String(n).replace(/\B(?=(\d{3})+$)/g, ",");
}

/** The page-count refusal, in the byte cap's shape: the count AND the cap (pure). "Has" is the file's own
 *  claim — the count is what its page tree declares, which is all any viewer can report before reading
 *  every page. */
export function pageCapMessage(count: number, cap: number): string {
  return `this PDF has ${fmtCount(count)} pages, over the ${fmtCount(cap)}-page cap for rendering pages in the viewer`;
}

/** The worker's URL from the chunk's own: the same directory and the same ?v= token, so the kernel's
 *  cache-bust token (and a rebuilt kernel's new one) reaches the worker too. null when the src is not
 *  this chunk's (pure, so a test can run it against each hosting page's URL shape). */
export function workerUrlFor(chunkSrc: string): string | null {
  return /\/pdf-chunk\.js/.test(chunkSrc) ? chunkSrc.replace(/\/pdf-chunk\.js/, "/pdf-worker.js") : null;
}

/** The device-pixel scale to draw a page at: the display's ratio, reduced so width × height in device
 *  pixels stays under `maxPixels` (pure). */
export function backingScale(cssWidth: number, cssHeight: number, dpr: number, maxPixels = MAX_CANVAS_PIXELS): number {
  const want = Math.max(1, dpr || 1);
  const area = Math.max(1, cssWidth) * Math.max(1, cssHeight);
  return Math.min(want, Math.sqrt(maxPixels / area));
}

/** The element the pages scroll inside — the nearest ancestor of `el` whose vertical overflow scrolls
 *  (auto, scroll, or the legacy overlay) — or null for the viewport when none does, or when the scroller is
 *  the document's own body or root (the implicit root covers those). This is the IntersectionObserver's
 *  `root`: a rootMargin expands the ROOT's box only, and a scrolling ancestor between the root and a page
 *  clips the page without it, so with the implicit root the margin never reached a page below the
 *  viewer's own fold. `styleOf` is the computed style, injectable so a test can run this against a fake
 *  tree; absent a getComputedStyle (no window) the answer is the viewport. */
export function scrollRootFor(
  el: Element | null | undefined,
  styleOf: (e: Element) => { overflowY: string } | null = (e) => (typeof getComputedStyle === "function" ? getComputedStyle(e) : null),
): Element | null {
  for (let a = el ? el.parentElement : null; a; a = a.parentElement) {
    const doc = a.ownerDocument;
    if (doc && (a === doc.body || a === doc.documentElement)) return null;
    const st = styleOf(a);
    if (st && /^(auto|scroll|overlay)$/.test(st.overflowY)) return a;
  }
  return null;
}

// The chunk's own <script> — document.currentScript while a classic script runs, else the tag whose src
// names this file — is where the worker's URL comes from, at load, before any render() call.
function ownScriptSrc(): string | null {
  if (typeof document === "undefined") return null;
  const cur = document.currentScript as HTMLScriptElement | null;
  if (cur && cur.src && /\/pdf-chunk\.js/.test(cur.src)) return cur.src;
  return Array.from(document.querySelectorAll("script[src]"))
    .map((n) => (n as HTMLScriptElement).src).find((u) => /\/pdf-chunk\.js/.test(u)) || null;
}
{
  const own = ownScriptSrc();
  const url = own ? workerUrlFor(own) : null;
  if (url) pdfjsLib.GlobalWorkerOptions.workerSrc = url;
}

interface Page {
  index: number;                 // 1-based, as PDFs number pages and as the wire's `target.page` does
  wrap: HTMLElement;
  canvas: HTMLCanvasElement;
  proxy: PDFPageProxy | null;
  task: RenderTask | null;       // the draw in flight, cancellable
  drawnAt: number;               // CSS width the bitmap was drawn for; 0 = no bitmap
  visible: boolean;              // inside the observer's window (always true without an observer)
  queued: boolean;
  failed: boolean;               // pdf.js could not read or draw it: the notice is in the wrapper, no retry
  cue: HTMLElement | null;       // the romp loader over the sheet while a draw is pending with no bitmap (cue / uncue)
}

/** render() over a given pdf.js — the modern build for the shipped chunk (`render` below), the legacy build
 *  or a stand-in for a test. The parameter shadows the module's import on purpose: the body is written
 *  once, against `pdfjsLib`. */
export function makeRender(pdfjsLib: PdfLib) {
  return async function render(bytes: ArrayBuffer, container: HTMLElement, opts: RenderOpts = {}): Promise<RenderHandle> {
    const cap = opts.maxBytes ?? DEFAULT_MAX_BYTES;
    if (bytes.byteLength > cap) throw new Error(capMessage(bytes.byteLength, cap));
    if (!pdfjsLib.GlobalWorkerOptions.workerSrc) {
      throw new Error("the PDF renderer could not locate its worker: no pdf-chunk.js script tag to derive pdf-worker.js from");
    }
    // a copy: pdf.js transfers the buffer it is given to the worker, which would detach the caller's
    const task = pdfjsLib.getDocument({ data: new Uint8Array(bytes.slice(0)) });
    let doc: PDFDocumentProxy;
    // a refused open (corrupt bytes, a password) releases the Worker getDocument started for it: pdf.js's failure
    // path only rejects, and the caller has no handle to release it with, so without this every attempt on such a
    // file (each opening of the Comments panel renders again) left one more Worker running
    try { doc = await task.promise; } catch (e) { void task.destroy(); throw e; }
    // the count is the page tree's /Count, which pdf.js does not verify (the header): over the cap it is refused
    // HERE, before a shell exists or the container is touched, and the document and its worker are released.
    // Below zero (an integer pdf.js accepts) it is no pages, so the caller's page-less path runs, not a blank root.
    const pageCap = opts.maxPages ?? DEFAULT_MAX_PAGES;
    if (doc.numPages > pageCap) { void task.destroy(); throw new Error(pageCapMessage(doc.numPages, pageCap)); }
    const n = Math.max(0, doc.numPages);
    const root = document.createElement("div");
    root.className = "fileview-pdf";

    // every page's shell up front, at the first page's aspect until its own is known (pdf.js's viewer
    // does the same) — so the scroller has its full extent and the observer has elements to watch
    let aspect = "612 / 792";
    if (n > 0) {
      try {
        const vp = (await doc.getPage(1)).getViewport({ scale: 1 });
        aspect = `${vp.width} / ${vp.height}`;
      } catch (e) { void task.destroy(); throw e; }   // nothing of ours is in the container yet
    }
    const pages: Page[] = [];
    const byEl = new Map<Element, Page>();
    for (let i = 1; i <= n; i++) {
      const wrap = document.createElement("div");
      wrap.className = "fileview-pdf-page";
      wrap.dataset.page = String(i);
      wrap.style.position = "relative";       // the overlay's anchor: load-bearing, so inline, not the sheet's
      wrap.style.aspectRatio = aspect;
      const canvas = document.createElement("canvas");
      canvas.className = "fileview-pdf-canvas";
      canvas.dataset.page = String(i);
      canvas.style.display = "block";
      canvas.style.width = "100%";            // width-fit: the bitmap is drawn at the root's width, and a
      canvas.style.height = "auto";           // width change scales it at once; the redraw that sharpens it replaces
                                              // the bitmap only once drawn (paint's staging), never blanking it first
      canvas.style.aspectRatio = aspect;      // the box is the page's with or without a bitmap: an overlay placed on
      canvas.width = 0; canvas.height = 0;    // it before the draw, or after an eviction, covers the page, not a 0-tall
                                              // or default-sized band. No bitmap is 0×0, never the element default.
      wrap.appendChild(canvas);
      root.appendChild(wrap);
      const p: Page = { index: i, wrap, canvas, proxy: null, task: null, drawnAt: 0, visible: false, queued: false, failed: false, cue: null };
      pages.push(p);
      byEl.set(wrap, p);
    }
    container.appendChild(root);                // attached before the first draw: width-fit reads its width

    let disposed = false;
    const fitWidth = () => root.clientWidth || 0;
    // The romp loader over a sheet whose draw is pending and which has no bitmap meanwhile (the header; ui/CLAUDE.md's
    // loading-state rule): the viewer's own loader markup — swirl, wordmark, three accent dots — on the classes both
    // sheets style for the viewer's loader, absolutely positioned over the wrapper (whose position: relative anchors
    // it, as it anchors the panel's overlay). It goes up in want(), the event that asks for the draw — queued behind
    // the pump or in flight, the sheet is waiting either way — and comes down at the one event that ends the wait:
    // the bitmap landing (paint), the page failing (fail: the notice takes its place) or the page leaving the margin
    // (drop: nothing is pending for it any more). A sharpening redraw gets none, its scaled bitmap being on screen,
    // and a failed page gets none, nothing ever ending that wait. pointer-events: none so the panel's region overlay,
    // a sibling under it during a redraw, still takes the pointer.
    const cue = (p: Page) => {
      if (p.cue || p.drawnAt || p.failed) return;
      const load = document.createElement("div");
      load.className = "fileview-load fileview-pdf-page-load";
      load.style.position = "absolute"; load.style.inset = "0"; load.style.pointerEvents = "none";
      const swirl = document.createElement("img");
      swirl.src = mediaSrc("romp-swirl-glyph.svg"); swirl.alt = "";
      const word = document.createElement("span");
      word.textContent = "romp";
      load.appendChild(swirl); load.appendChild(word);
      for (let i = 0; i < 3; i++) { const dot = document.createElement("i"); dot.className = "fileview-dot"; load.appendChild(dot); }
      p.wrap.appendChild(load);
      p.cue = load;
    };
    const uncue = (p: Page) => { if (p.cue) { p.cue.remove(); p.cue = null; } };
    // one draw at a time, first asked first drawn: keeps the main thread answering scrolls and bounds
    // the bitmaps in flight
    const queue: Page[] = [];
    let pumping = false;
    const want = (p: Page) => { if (!p.queued) { p.queued = true; queue.push(p); } cue(p); void pump(); };
    async function pump(): Promise<void> {
      if (pumping) return;
      pumping = true;
      try {
        while (queue.length && !disposed) {
          const p = queue.shift()!;
          p.queued = false;
          if (!p.visible || p.failed) continue;
          try { await paint(p); } catch (e) {
            if (!(e instanceof pdfjsLib.RenderingCancelledException) && !disposed) fail(p, e);
          }
        }
      } finally { pumping = false; }
    }
    // a page pdf.js cannot read or draw, after the first (whose failure rejects render() below): loud in place.
    // The wrapper keeps the page's extent (the pages after it stay where they were) and shows the failure in the
    // viewer's error dress; the canvas goes, since no bitmap will come and a page with none must not take a
    // region comment (the panel arms its overlays on the canvases it finds); the caller hears it once; no retry,
    // a damaged page object fails the same way every time.
    const fail = (p: Page, e: unknown) => {
      p.failed = true;
      p.task = null;
      uncue(p);                                  // the notice takes the loader's place: this wait is over
      const message = String((e && (e as Error).message) || e);
      console.warn("pdf-chunk: page " + p.index + " did not render:", e);
      p.canvas.remove();
      const note = document.createElement("div");
      note.className = "fileview-err fileview-pdf-page-err";
      note.textContent = "Page " + p.index + " did not render — " + message;
      p.wrap.appendChild(note);
      opts.onPageError?.({ index: p.index, message });
    };
    async function paint(p: Page): Promise<void> {
      const proxy = p.proxy || (p.proxy = await doc.getPage(p.index));
      // evicted while getPage was in flight (there was no task for drop to cancel then): no bitmap for a page off
      // screen. The proxy is kept, so the page draws at once on return.
      if (disposed || !p.visible) return;
      const base = proxy.getViewport({ scale: 1 });
      const cssW = fitWidth() || base.width;    // an unlaid-out root (0 wide) draws at the page's natural size
      if (p.drawnAt === cssW) { uncue(p); return; }   // already sharp at this width (or a 0-wide page: nothing to draw, so nothing to wait for)
      const vp = proxy.getViewport({ scale: cssW / base.width });
      const dpr = backingScale(vp.width, vp.height, typeof window !== "undefined" ? window.devicePixelRatio : 1);
      p.wrap.style.aspectRatio = `${base.width} / ${base.height}`;
      p.canvas.style.aspectRatio = p.wrap.style.aspectRatio;
      // STAGED (the header): pdf.js draws into a canvas of its own, off the DOM, and the page's canvas takes the finished
      // bitmap in one synchronous step below — so it is 0×0 or complete, never sized and empty, and a redraw keeps the
      // old bitmap on screen until the new one is in. Drawn in place, the page was blank for the length of every draw:
      // assigning width or height resets a canvas's bitmap, and pdf.js fills its target white before its first operator
      // runs (a microtask in, the operators in animation frames). The panel, reading a sized canvas as a drawn page, cut
      // a blank crop from that window and kept it; every width change flashed every page on screen (the review, 2026-09-06).
      const stage = document.createElement("canvas");
      stage.width = Math.round(vp.width * dpr);
      stage.height = Math.round(vp.height * dpr);
      const task = proxy.render({ canvas: stage, viewport: vp, transform: dpr === 1 ? undefined : [dpr, 0, 0, dpr, 0, 0] });
      p.task = task;
      try {
        await task.promise;
        // evicted as the draw landed: drop() cancelled a task pdf.js had already finished, so it resolved all the same.
        // No bitmap for a page beyond the margin — drawnAt stays 0, and the page draws again on return.
        if (disposed || !p.visible) return;
        const drawn = stage.getContext("2d");
        if (!drawn) throw new Error("the staging canvas gave no 2d context after the draw");
        p.canvas.width = stage.width;            // sized, then filled, with nothing yielding between: from here to the
        p.canvas.height = stage.height;          // drawImage the main thread runs nothing else, so no reader sees a sized, empty canvas
        // the context attributes pdf.js gave this canvas when it drew into it directly: opaque (a page is), and marked for
        // readback — what is taken from this canvas is its pixels (the panel's crops), and a plain context has Chromium
        // warn on the console at every getImageData
        const ctx = p.canvas.getContext("2d", { alpha: false, willReadFrequently: true });
        if (!ctx) throw new Error("the page's canvas gave no 2d context");
        ctx.drawImage(drawn.canvas, 0, 0);       // drawn.canvas: the stage itself (a test's stand-in hands over the surface behind it)
      } finally {
        if (p.task === task) p.task = null;
        stage.width = 0; stage.height = 0;       // the staging store is released now, not when the collector gets to it
      }
      p.drawnAt = cssW;
      uncue(p);                                  // the bitmap is in: the loader gives way to pixels, before the caller hears of them
      opts.onPage?.({ index: p.index, canvas: p.canvas, width: vp.width, height: vp.height });
    }
    const drop = (p: Page) => {                  // release a far-away page's bitmap; the wrapper keeps its extent
      p.task?.cancel(); p.task = null;
      if (p.canvas.width || p.canvas.height) { p.canvas.width = 0; p.canvas.height = 0; }
      p.drawnAt = 0;
      uncue(p);                                  // nothing is pending for a page beyond the margin (it is cued again on return)
    };

    // lazily as they scroll into view — one height of the SCROLLER as margin, so the next page is ready before
    // it shows; the same observer evicts what scrolls beyond that. The root is the scroller the pages live in
    // (scrollRootFor: the viewer's body), not the implicit viewport: a rootMargin expands only the root's box,
    // and the body's clip would otherwise make the margin inert. Without the observer, every page.
    let io: IntersectionObserver | null = null;
    if (typeof IntersectionObserver !== "undefined") {
      io = new IntersectionObserver((entries) => {
        for (const e of entries) {
          const p = byEl.get(e.target);
          if (!p) continue;
          p.visible = e.isIntersecting;
          if (p.visible) want(p); else drop(p);
        }
      }, { root: scrollRootFor(container), rootMargin: "100% 0px" });
    } else {
      for (const p of pages) p.visible = true;
    }
    // a width change redraws the pages on screen at the new width (the CSS scaling has already kept them
    // the right size; this is the sharpening) — the rest redraw when they next scroll in
    let ro: ResizeObserver | null = null;
    if (typeof ResizeObserver !== "undefined") {
      ro = new ResizeObserver(() => {
        const w = fitWidth();
        if (!w) return;
        for (const p of pages) if (p.visible && p.drawnAt && p.drawnAt !== w) want(p);
      });
      ro.observe(root);
    }

    // the first page is drawn before resolving, so the caller removes its loader over a drawn page, not over
    // empty shells. A page pdf.js cannot draw rejects render() and leaves NOTHING behind — the caller's fallback (the frame)
    // must not share the container with a stray root or a live worker.
    if (pages.length) {
      cue(pages[0]);                             // its sheet waits like any other's (a caller's own loader sits above the pages)
      pages[0].visible = true;
      try { await paint(pages[0]); } catch (e) { io?.disconnect(); ro?.disconnect(); void task.destroy(); root.remove(); throw e; }
    }
    if (io) for (const p of pages) io.observe(p.wrap);
    else for (const p of pages) want(p);

    return {
      pages: n,
      dispose() {
        if (disposed) return;
        disposed = true;
        io?.disconnect(); ro?.disconnect();
        queue.length = 0;
        for (const p of pages) { p.task?.cancel(); p.task = null; }
        void task.destroy();                   // the document and its worker (pdf.js 6 puts destroy on the loading task)
        root.remove();
      },
    };
  };
}

/** The shipped render(): over the modern pdf.js build the browsers run. */
export const render = makeRender(pdfjsLib);

// The mount contract with file-view.ts: a window global, NOT an import — an import would drag pdf.js
// into the main render bundle and break the lazy discipline this chunk exists for.
// (guarded: the test bundle imports the pure helpers under node, where there is no window)
if (typeof window !== "undefined") (window as any).__rompPdf = { render, DEFAULT_MAX_BYTES };

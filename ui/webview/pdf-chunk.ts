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
// THE SIZE CAP IS LOUD: render() refuses bytes over `maxBytes` (25 MB by default) with an Error naming
// the size and the cap, before pdf.js sees a byte. The caller shows the frame instead and says why;
// nothing here degrades quietly.
//
// THE WORKER: pdf.js parses in a Worker it creates from `GlobalWorkerOptions.workerSrc`. That URL is
// derived at load from this chunk's OWN <script src> — same directory, same ?v= token — so a rebuilt
// kernel serves a matching worker, and the kernel's /dist route (which types by suffix) serves it as
// JavaScript because esbuild emits it as pdf-worker.js, not .mjs. No script tag to derive from means
// render() throws, again by name.
//
// PUBLIC API — the window global `__rompPdf`:
//
//   render(bytes: ArrayBuffer, container: HTMLElement, opts?: {
//     maxBytes?: number;                                   // default DEFAULT_MAX_BYTES (25 MB)
//     onPage?: (page: { index: number; canvas: HTMLCanvasElement; width: number; height: number }) => void;
//   }) => Promise<{ pages: number; dispose(): void }>
//
//   Appends ONE root element (div.fileview-pdf) to `container`, holding one wrapper per page
//   (div.fileview-pdf-page, `position: relative`, data-page 1-based, sized to the page's aspect so the
//   scroller has its full extent before any pixel is drawn) with one canvas each (canvas.fileview-pdf-canvas,
//   data-page too, CSS width 100%). Pages are drawn width-fit to the root, lazily as they scroll within a
//   viewport of the visible area (IntersectionObserver; every page eagerly when the observer is absent), and
//   a page that scrolls far away drops its bitmap and redraws on return, so a long document costs the
//   memory of the pages near the reader, not of all of them. onPage fires after EVERY draw of a page — the
//   first, a redraw on return, a redraw at a new width — with the canvas (the same element for the page's
//   whole life) and its CSS size; an overlay that positions by fractions of that size stays correct without
//   listening for resizes. The promise resolves once the first page is drawn (or at once for a page-less
//   document); it rejects for bytes over the cap, a missing worker URL, or anything pdf.js refuses to open
//   (a corrupt file, a password), each with pdf.js's or this module's own message. dispose() cancels the
//   draws in flight, releases the document, and removes the root.
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
import * as pdfjsLib from "pdfjs-dist";
import type { PDFDocumentProxy, PDFPageProxy, RenderTask } from "pdfjs-dist";

/** The default bytes cap: a PDF over this is refused, not rendered (the plan's stated cap). */
export const DEFAULT_MAX_BYTES = 25 * 1024 * 1024;

/** Largest canvas backing store this module allocates per page, in device pixels: under every current
 *  engine's canvas limit (Safari's is the lowest at 16.7 M), so a poster-sized page draws softer rather
 *  than not at all. */
export const MAX_CANVAS_PIXELS = 16 * 1024 * 1024;

export interface PageInfo { index: number; canvas: HTMLCanvasElement; width: number; height: number }
export interface RenderOpts { maxBytes?: number; onPage?: (page: PageInfo) => void }
export interface RenderHandle { pages: number; dispose(): void }

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
}

export async function render(bytes: ArrayBuffer, container: HTMLElement, opts: RenderOpts = {}): Promise<RenderHandle> {
  const cap = opts.maxBytes ?? DEFAULT_MAX_BYTES;
  if (bytes.byteLength > cap) throw new Error(capMessage(bytes.byteLength, cap));
  if (!pdfjsLib.GlobalWorkerOptions.workerSrc) {
    throw new Error("the PDF renderer could not locate its worker: no pdf-chunk.js script tag to derive pdf-worker.js from");
  }
  // a copy: pdf.js transfers the buffer it is given to the worker, which would detach the caller's
  const task = pdfjsLib.getDocument({ data: new Uint8Array(bytes.slice(0)) });
  const doc: PDFDocumentProxy = await task.promise;
  const n = doc.numPages;
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
    canvas.style.height = "auto";           // width change scales it at once (a redraw sharpens it after)
    wrap.appendChild(canvas);
    root.appendChild(wrap);
    const p: Page = { index: i, wrap, canvas, proxy: null, task: null, drawnAt: 0, visible: false, queued: false };
    pages.push(p);
    byEl.set(wrap, p);
  }
  container.appendChild(root);                // attached before the first draw: width-fit reads its width

  let disposed = false;
  const fitWidth = () => root.clientWidth || 0;
  // one draw at a time, first asked first drawn: keeps the main thread answering scrolls and bounds
  // the bitmaps in flight
  const queue: Page[] = [];
  let pumping = false;
  const want = (p: Page) => { if (!p.queued) { p.queued = true; queue.push(p); } void pump(); };
  async function pump(): Promise<void> {
    if (pumping) return;
    pumping = true;
    try {
      while (queue.length && !disposed) {
        const p = queue.shift()!;
        p.queued = false;
        if (!p.visible) continue;
        try { await paint(p); } catch (e) {
          if (!(e instanceof pdfjsLib.RenderingCancelledException)) console.warn("pdf-chunk: page " + p.index + " did not render:", e);
        }
      }
    } finally { pumping = false; }
  }
  async function paint(p: Page): Promise<void> {
    const proxy = p.proxy || (p.proxy = await doc.getPage(p.index));
    if (disposed) return;
    const base = proxy.getViewport({ scale: 1 });
    const cssW = fitWidth() || base.width;    // an unlaid-out root (0 wide) draws at the page's natural size
    if (p.drawnAt === cssW) return;           // already sharp at this width
    const vp = proxy.getViewport({ scale: cssW / base.width });
    const dpr = backingScale(vp.width, vp.height, typeof window !== "undefined" ? window.devicePixelRatio : 1);
    p.wrap.style.aspectRatio = `${base.width} / ${base.height}`;
    p.canvas.width = Math.round(vp.width * dpr);
    p.canvas.height = Math.round(vp.height * dpr);
    const task = proxy.render({ canvas: p.canvas, viewport: vp, transform: dpr === 1 ? undefined : [dpr, 0, 0, dpr, 0, 0] });
    p.task = task;
    try { await task.promise; } finally { if (p.task === task) p.task = null; }
    if (disposed) return;
    p.drawnAt = cssW;
    opts.onPage?.({ index: p.index, canvas: p.canvas, width: vp.width, height: vp.height });
  }
  const drop = (p: Page) => {                  // release a far-away page's bitmap; the wrapper keeps its extent
    p.task?.cancel(); p.task = null;
    if (p.canvas.width || p.canvas.height) { p.canvas.width = 0; p.canvas.height = 0; }
    p.drawnAt = 0;
  };

  // lazily as they scroll into view — one viewport height of margin so the next page is ready before
  // it shows; the same observer evicts what scrolls beyond that. Without the observer, every page.
  let io: IntersectionObserver | null = null;
  if (typeof IntersectionObserver !== "undefined") {
    io = new IntersectionObserver((entries) => {
      for (const e of entries) {
        const p = byEl.get(e.target);
        if (!p) continue;
        p.visible = e.isIntersecting;
        if (p.visible) want(p); else drop(p);
      }
    }, { rootMargin: "100% 0px" });
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

  // the first page is drawn before resolving, so the caller's loader gives way to pixels, not shells. A
  // page pdf.js cannot draw rejects render() and leaves NOTHING behind — the caller's fallback (the frame)
  // must not share the container with a stray root or a live worker.
  if (pages.length) {
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
}

// The mount contract with file-view.ts: a window global, NOT an import — an import would drag pdf.js
// into the main render bundle and break the lazy discipline this chunk exists for.
// (guarded: the test bundle imports the pure helpers under node, where there is no window)
if (typeof window !== "undefined") (window as any).__rompPdf = { render, DEFAULT_MAX_BYTES };

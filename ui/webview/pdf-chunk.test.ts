// The PDF chunk's BEHAVIOUR, executed (plans/file-review.md, Slice 4). pdf-lazy.test.ts pins the lazy
// discipline, the worker URL and the cap, and pins the browser-only parts at source; this file runs them:
// makeRender over a stand-in pdf.js and a fake DOM drives the real pump, the observer's wiring, eviction and
// the per-page failure path under node, where there is no browser and pdf.js's modern build does not run.
// One test runs the same paths against pdf.js's LEGACY build (the one it supports under node) and a real
// malformed PDF, so the stand-in's idea of a failing page is checked against pdf.js's own. What only a
// layout engine can show — the margin reaching a page below the viewer's fold once the root is the
// scroller, a 0×0 canvas keeping the page's box — is pdf-chunk-browser.test.ts.
//
// Fixtures are synthetic: a hand-built PDF of blank pages (tools/pdf-smoke.test.mjs's generator, copied so
// its own tests do not ride along), TESTHOST, no recorded document.
import { test, beforeEach } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";
import { makeRender, scrollRootFor, type PdfLib, type PageInfo, type PageError } from "./pdf-chunk";

// ── a fake DOM: what the chunk touches of an element, and nothing else ──────────────────────────

class FakeEl {
  tagName: string;
  className = "";
  dataset: Record<string, string> = {};
  style: Record<string, string> = {};
  children: FakeEl[] = [];
  parentElement: FakeEl | null = null;
  textContent = "";
  clientWidth = 0;
  width = 300; height = 150;                 // a canvas's element default, which the chunk must not leave in place
  ownerDocument: { body: FakeEl; documentElement: FakeEl } | undefined = undefined;
  private backing: unknown = null;
  constructor(tag: string) { this.tagName = tag.toUpperCase(); }
  appendChild(c: FakeEl): FakeEl { c.remove(); c.parentElement = this; this.children.push(c); return c; }
  remove(): void {
    const p = this.parentElement;
    if (p) { p.children.splice(p.children.indexOf(this), 1); this.parentElement = null; }
  }
  /** `tag`, `.class`, or `tag.class` — the selectors the panel and this file use on the chunk's DOM. */
  querySelector(sel: string): FakeEl | null {
    const [tag, cls] = sel.split(".");
    for (const c of this.children) {
      if ((!tag || c.tagName === tag.toUpperCase()) && (!cls || c.className.split(" ").includes(cls))) return c;
      const deep = c.querySelector(sel);
      if (deep) return deep;
    }
    return null;
  }
  /** A canvas's 2D context, for the legacy-pdf.js test: @napi-rs/canvas at the element's current size. */
  getContext(kind: string): unknown {
    if (!this.backing) {
      const napi = createRequire(path.join(NODE_MODULES, "x.js"))("@napi-rs/canvas");
      this.backing = napi.createCanvas(Math.max(1, this.width), Math.max(1, this.height));
    }
    return (this.backing as { getContext(k: string): unknown }).getContext(kind);
  }
}
const NODE_MODULES = path.resolve(process.cwd(), "node_modules");
const el = (tag: string) => new FakeEl(tag);
const asEl = (e: FakeEl) => e as unknown as HTMLElement;

/** The viewer's tree around the chunk's container: .fileview { overflow: hidden } > .fileview-body { overflow:
 *  auto } > .fileview-pdfhost (the container). Returns the pieces a test asserts on. */
function viewerTree(): { container: FakeEl; body: FakeEl; view: FakeEl } {
  const view = el("div"); view.className = "fileview"; view.style.overflow = "hidden";
  const body = el("div"); body.className = "fileview-body"; body.style.overflow = "auto";
  const container = el("div"); container.className = "fileview-pdfhost";
  view.appendChild(body); body.appendChild(container);
  return { container, body, view };
}
const styleOf = (e: Element) => {
  const st = (e as unknown as FakeEl).style;
  return { overflowY: st.overflowY || st.overflow || "visible" };
};

// ── a fake pdf.js: documents whose pages draw, or refuse, on request ────────────────────────────

interface FakeLib { lib: PdfLib; calls: { getPage: number[]; renders: number[]; destroyed: number; cancelled: number } }
function fakeLib(spec: { pages: number; fail?: number[]; message?: string }): FakeLib {
  const calls = { getPage: [] as number[], renders: [] as number[], destroyed: 0, cancelled: 0 };
  class Cancelled extends Error {}
  const lib = {
    GlobalWorkerOptions: { workerSrc: "http://TESTHOST:29855/dist/pdf-worker.js" },
    RenderingCancelledException: Cancelled,
    getDocument: () => ({
      promise: Promise.resolve({
        numPages: spec.pages,
        getPage: async (i: number) => {
          calls.getPage.push(i);
          if (spec.fail?.includes(i)) throw new Error(spec.message ?? "Page dictionary kid reference points to wrong type of object.");
          return {
            getViewport: ({ scale }: { scale: number }) => ({ width: 612 * scale, height: 792 * scale }),
            render: () => {
              calls.renders.push(i);
              let cancel = () => {};
              const promise = new Promise<void>((res, rej) => {
                const t = setTimeout(res, 1);                          // a draw takes a tick, as pdf.js's does
                cancel = () => { clearTimeout(t); calls.cancelled++; rej(new Cancelled("cancelled")); };
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

// ── a fake IntersectionObserver the test fires by hand ──────────────────────────────────────────

class FakeIO {
  static instances: FakeIO[] = [];
  targets: FakeEl[] = [];
  disconnected = false;
  constructor(public cb: (entries: unknown[], io: FakeIO) => void, public opts: { root?: unknown; rootMargin?: string }) { FakeIO.instances.push(this); }
  observe(t: FakeEl): void { this.targets.push(t); }
  disconnect(): void { this.disconnected = true; }
  /** Entries for the given wrappers: intersecting or not. */
  fire(states: Array<[FakeEl, boolean]>): void { this.cb(states.map(([target, isIntersecting]) => ({ target, isIntersecting })), this); }
}

/** Wait for a condition the pump reaches on its own ticks; fails loudly rather than hanging. */
async function until(cond: () => boolean, what: string): Promise<void> {
  for (let i = 0; i < 2000; i++) { if (cond()) return; await new Promise((r) => setTimeout(r, 1)); }
  assert.fail("timed out waiting for " + what);
}
const bytes = () => new ArrayBuffer(16);
const canvasOf = (wrap: FakeEl) => wrap.querySelector("canvas.fileview-pdf-canvas");
const pagesOf = (container: FakeEl) => container.children[0].children;

beforeEach(() => {
  (globalThis as any).document = { createElement: el };
  (globalThis as any).getComputedStyle = styleOf;
  delete (globalThis as any).IntersectionObserver;
  delete (globalThis as any).ResizeObserver;
  FakeIO.instances.length = 0;
});

// ── scrollRootFor: the observer's root is the scroller the pages live in ───────────────────────

test("scrollRootFor finds the nearest ancestor that scrolls vertically, and nothing when none does", () => {
  const { container, body, view } = viewerTree();
  assert.equal(scrollRootFor(asEl(container), styleOf), body, "the viewer's body (overflow: auto) is the scroller");
  assert.equal(scrollRootFor(asEl(body), styleOf), null, "above the body nothing scrolls (.fileview clips; a clip is not a scroller)");
  body.style.overflow = ""; body.style.overflowY = "scroll";
  assert.equal(scrollRootFor(asEl(container), styleOf), body, "overflow-y: scroll counts");
  body.style.overflowY = "overlay";
  assert.equal(scrollRootFor(asEl(container), styleOf), body, "the legacy overlay value counts");
  body.style.overflowY = "hidden";
  assert.equal(scrollRootFor(asEl(container), styleOf), null, "hidden clips without scrolling: the viewport is right for it");
  view.style.overflow = "auto"; body.style.overflowY = "visible";
  assert.equal(scrollRootFor(asEl(container), styleOf), view, "the nearest scrolling ancestor, however far up");
  assert.equal(scrollRootFor(null, styleOf), null);
  assert.equal(scrollRootFor(asEl(container), () => null), null, "no computed style (no window) → the viewport");
});

test("scrollRootFor stops at the document's body and root: the implicit root already covers a scrolling page", () => {
  const html = el("html"); const docBody = el("body"); docBody.style.overflow = "auto";
  const ownerDocument = { body: docBody, documentElement: html };
  const container = el("div");
  html.appendChild(docBody); docBody.appendChild(container);
  for (const e of [html, docBody, container]) e.ownerDocument = ownerDocument;
  assert.equal(scrollRootFor(asEl(container), styleOf), null);
});

// ── the observer: created on the scroller with the margin, driving draws and evictions ──────────

test("the observer's root is the viewer's scroller; a page draws when it intersects, gives its bitmap back when it leaves, and redraws on return on the same canvas", async () => {
  (globalThis as any).IntersectionObserver = FakeIO;
  const { lib, calls } = fakeLib({ pages: 6 });
  const { container, body } = viewerTree();
  const drawn: PageInfo[] = [];
  const h = await makeRender(lib)(bytes(), asEl(container), { onPage: (p) => drawn.push(p) });
  assert.equal(h.pages, 6);
  assert.equal(FakeIO.instances.length, 1, "one observer for the document");
  const io = FakeIO.instances[0];
  assert.equal(io.opts.root, body, "the root is the .fileview-body the pages scroll in — the margin is measured there, not on the viewport");
  assert.equal(io.opts.rootMargin, "100% 0px", "one scroller height of margin");
  const wraps = pagesOf(container);
  assert.equal(wraps.length, 6);
  assert.deepEqual(io.targets, wraps, "every page's wrapper is watched");
  // the first page is drawn before resolve; the rest are shells with NO bitmap (0×0, never the 300×150 element
  // default an overlay would read as the page's size) whose canvas box still has the page's aspect
  assert.deepEqual(drawn.map((p) => p.index), [1]);
  for (const w of wraps.slice(1)) {
    const c = canvasOf(w)!;
    assert.equal(c.width, 0); assert.equal(c.height, 0);
    assert.equal(c.style.aspectRatio, "612 / 792", "the canvas carries the page's aspect, so its box is the page's with no bitmap in it");
    assert.equal(w.style.aspectRatio, "612 / 792");
  }
  const c1 = canvasOf(wraps[0])!;
  assert.ok(c1.width > 0 && c1.height > 0, "page 1 has its bitmap");
  assert.equal(drawn[0].canvas, c1 as unknown as HTMLCanvasElement);

  // pages 1 and 2 in the window (page 2 below the fold but within the margin): page 2 draws, 3–6 stay shells
  io.fire([[wraps[0], true], [wraps[1], true], [wraps[2], false], [wraps[3], false], [wraps[4], false], [wraps[5], false]]);
  await until(() => drawn.length >= 2, "page 2's draw");
  assert.deepEqual(drawn.map((p) => p.index), [1, 2]);
  assert.ok(canvasOf(wraps[1])!.width > 0);
  assert.equal(canvasOf(wraps[2])!.width, 0, "a page beyond the margin is not drawn");

  // the reader scrolls on: page 1 leaves the window and gives its bitmap back; 3 and 4 enter and draw, in order
  io.fire([[wraps[0], false], [wraps[2], true], [wraps[3], true]]);
  assert.equal(c1.width, 0, "evicted at once: the bitmap is released"); assert.equal(c1.height, 0);
  assert.equal(c1.style.aspectRatio, "612 / 792", "…and the canvas box stays the page's, so an overlay on it still covers the page");
  await until(() => drawn.length >= 4, "pages 3 and 4");
  assert.deepEqual(drawn.map((p) => p.index), [1, 2, 3, 4], "one draw at a time, first asked first drawn");
  assert.deepEqual(calls.renders, [1, 2, 3, 4]);

  // back up: page 1 redraws — same canvas element, onPage again, so an overlay keyed on the element holds
  const fetched = calls.getPage.length;
  io.fire([[wraps[0], true]]);
  await until(() => drawn.length >= 5, "page 1's redraw");
  assert.equal(drawn[4].index, 1);
  assert.equal(drawn[4].canvas, c1 as unknown as HTMLCanvasElement, "the same element for the page's whole life");
  assert.ok(c1.width > 0);
  assert.equal(calls.getPage.length, fetched, "the page proxy is kept across an eviction; only the bitmap is redone");

  h.dispose();
  assert.ok(io.disconnected);
  assert.equal(calls.destroyed, 1);
  assert.equal(container.children.length, 0, "dispose removes the root");
});

test("without an IntersectionObserver every page draws, eagerly and in order", async () => {
  const { lib, calls } = fakeLib({ pages: 3 });
  const { container } = viewerTree();
  const drawn: number[] = [];
  const h = await makeRender(lib)(bytes(), asEl(container), { onPage: (p) => drawn.push(p.index) });
  await until(() => drawn.length >= 3, "all three pages");
  assert.deepEqual(drawn, [1, 2, 3]);
  assert.deepEqual(calls.renders, [1, 2, 3]);
  for (const w of pagesOf(container)) assert.ok(canvasOf(w)!.width > 0);
  h.dispose();
});

// ── a page pdf.js cannot read or draw: loud in place, no canvas, told once, not retried ─────────

test("a later page pdf.js refuses is loud in its wrapper — the failure named with the page — its canvas removed, onPageError fired once, and never retried", async () => {
  (globalThis as any).IntersectionObserver = FakeIO;
  const { lib, calls } = fakeLib({ pages: 3, fail: [2] });
  const { container } = viewerTree();
  const drawn: number[] = []; const errors: PageError[] = []; const warned: string[] = [];
  const warn = console.warn;
  console.warn = (...a: unknown[]) => { warned.push(a.map(String).join(" ")); };
  try {
    const h = await makeRender(lib)(bytes(), asEl(container), { onPage: (p) => drawn.push(p.index), onPageError: (e) => errors.push(e) });
    assert.equal(h.pages, 3, "render() resolves: page 1 drew, the document is open");
    const io = FakeIO.instances[0];
    const wraps = pagesOf(container);
    io.fire(wraps.map((w) => [w, true] as [FakeEl, boolean]));
    await until(() => drawn.includes(3), "page 3, drawn past the failed page 2");
    assert.deepEqual(drawn, [1, 3], "the failed page fires no onPage");
    // the wrapper: still the page's extent, holding the notice in the viewer's error dress; the canvas gone
    const w2 = wraps[1];
    assert.equal(w2.dataset.page, "2");
    assert.equal(w2.style.aspectRatio, "612 / 792", "the pages after it stay where they were");
    assert.equal(canvasOf(w2), null, "no canvas: a page that will never have a bitmap takes no region comment (the panel keys its overlays on the canvases it finds)");
    const note = w2.querySelector(".fileview-err")!;
    assert.ok(note, "the failure is IN the page, not only on the console");
    assert.equal(note.textContent, "Page 2 did not render — Page dictionary kid reference points to wrong type of object.");
    assert.ok(note.className.split(" ").includes("fileview-pdf-page-err"));
    assert.deepEqual(errors, [{ index: 2, message: "Page dictionary kid reference points to wrong type of object." }], "the caller hears it, once");
    assert.equal(warned.length, 1, "the console keeps its trace too");
    assert.match(warned[0], /pdf-chunk: page 2 did not render/);
    // the pages beside it are untouched
    assert.ok(canvasOf(wraps[0])!.width > 0); assert.ok(canvasOf(wraps[2])!.width > 0);
    // scrolled away and back: no retry — a damaged page object fails the same way every time
    const asked = calls.getPage.filter((i) => i === 2).length;
    io.fire([[w2, false]]); io.fire([[w2, true]]);
    await new Promise((r) => setTimeout(r, 10));
    assert.equal(calls.getPage.filter((i) => i === 2).length, asked, "not asked of pdf.js again");
    assert.equal(errors.length, 1); assert.equal(warned.length, 1);
    assert.equal(w2.children.length, 1, "one notice, not one per scroll");
    h.dispose();
  } finally { console.warn = warn; }
});

test("a FIRST page pdf.js refuses still rejects render() with nothing left behind — the caller's frame fallback is the notice there", async () => {
  const { lib, calls } = fakeLib({ pages: 2, fail: [1], message: "Bad page object" });
  const { container } = viewerTree();
  const errors: PageError[] = [];
  await assert.rejects(makeRender(lib)(bytes(), asEl(container), { onPageError: (e) => errors.push(e) }), /Bad page object/);
  assert.equal(container.children.length, 0, "no root in the container");
  assert.equal(calls.destroyed, 1, "the document and its worker released");
  assert.deepEqual(errors, [], "the rejection is the signal; onPageError is for pages after the first");
});

test("dispose during a draw in flight: the cancel is not a failure, nothing is marked failed, nothing is painted after", async () => {
  const { lib, calls } = fakeLib({ pages: 2 });
  const { container } = viewerTree();
  const drawn: number[] = []; const errors: PageError[] = [];
  const h = await makeRender(lib)(bytes(), asEl(container), { onPage: (p) => drawn.push(p.index), onPageError: (e) => errors.push(e) });
  const wraps = pagesOf(container);
  await until(() => calls.renders.includes(2), "page 2's draw to start");   // eager (no observer): queued behind page 1
  h.dispose();
  assert.equal(calls.cancelled, 1, "the draw in flight is cancelled");
  await new Promise((r) => setTimeout(r, 10));
  assert.deepEqual(drawn, [1], "page 2 never fires onPage");
  assert.deepEqual(errors, [], "a cancelled draw is not a failed page");
  assert.equal(wraps[1].querySelector(".fileview-err"), null);
  assert.equal(calls.destroyed, 1);
});

// ── the same, against pdf.js's legacy build and a real malformed PDF ────────────────────────────

const LEGACY = path.join(NODE_MODULES, "pdfjs-dist", "legacy", "build", "pdf.mjs");
const LEGACY_WORKER = path.join(NODE_MODULES, "pdfjs-dist", "legacy", "build", "pdf.worker.mjs");
const NAPI = path.join(NODE_MODULES, "@napi-rs", "canvas", "package.json");
const SKIP_LEGACY = fs.existsSync(LEGACY) && fs.existsSync(LEGACY_WORKER) && fs.existsSync(NAPI)
  ? false
  : "pdfjs-dist's legacy build or @napi-rs/canvas is not installed under vscode-extension/node_modules (run `npm ci` there); the real-pdf.js page-failure test did not run";

/** A minimal PDF of blank US-letter pages with a correct xref (tools/pdf-smoke.test.mjs's generator); `badPage`
 *  replaces that page's object with a bare integer — a damaged page object pdf.js opens around (the document
 *  loads, the pages before it read) but cannot read when asked for it. */
function minimalPdf(pageCount: number, badPage: number | null = null): ArrayBuffer {
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
  const b = Buffer.from(out, "latin1");
  return b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength);
}

test("pdf.js (legacy build) on a PDF whose page 2 is a bare integer: the document opens, page 1 draws, page 2's failure lands in its wrapper with pdf.js's own words", { skip: SKIP_LEGACY }, async () => {
  const legacy = (await import(pathToFileURL(LEGACY).href)) as unknown as PdfLib;
  legacy.GlobalWorkerOptions.workerSrc = pathToFileURL(LEGACY_WORKER).href;   // node: pdf.js runs its parser on the main thread from this file
  const { container } = viewerTree();
  const drawn: number[] = []; const errors: PageError[] = [];
  const warn = console.warn;
  console.warn = () => {};
  try {
    const h = await makeRender(legacy)(minimalPdf(3, 2), asEl(container), { onPage: (p) => drawn.push(p.index), onPageError: (e) => errors.push(e) });
    assert.ok(h.pages >= 2, "pdf.js opens the document (it may drop the pages after the damaged one from the count)");
    await until(() => errors.length >= 1, "page 2's failure");
    assert.deepEqual(drawn.filter((i) => i === 1), [1], "page 1 drew");
    assert.equal(errors[0].index, 2);
    assert.match(errors[0].message, /wrong type of object|page/i, "pdf.js's message, not this module's");
    const w2 = pagesOf(container)[1];
    assert.equal(canvasOf(w2), null);
    const note = w2.querySelector(".fileview-err")!;
    assert.equal(note.textContent, "Page 2 did not render — " + errors[0].message);
    assert.ok(canvasOf(pagesOf(container)[0])!.width > 0, "page 1 has its bitmap");
    h.dispose();
  } finally { console.warn = warn; }
});

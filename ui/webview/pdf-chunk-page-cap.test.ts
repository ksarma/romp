// The PDF chunk's PAGE-COUNT cap (plans/file-review.md, Slice 4; the review of 2026-09-06). The byte cap does
// not bound pages: pdf.js reads the count from the page tree's /Count and checks only that the LAST page
// resolves — a nested Pages node is skipped by its own /Count on the way — so a PDF of a few hundred bytes can
// declare millions of pages, open, and draw page 1. render() then built one wrapper and one canvas per declared
// page synchronously and observed every wrapper, which held the pane's thread for a minute or exhausted its
// memory before the first paint, with no refusal anywhere (the byte cap was far away, and file-view checks only
// `pages === 0`). Now render() refuses a count over `maxPages` (DEFAULT_MAX_PAGES) by name once pdf.js has opened
// the document and before a shell exists, releasing the document; the caller's catch shows the frame and says
// why. A count BELOW zero — an integer pdf.js also accepts — is no pages, so the caller's page-less path runs
// instead of a blank root reaching the pane.
//
// Two legs: makeRender over a stand-in pdf.js (the count, the order of the checks, what is and is not touched),
// and the same against pdf.js's LEGACY build (the one it supports under Node) on a hand-built 529-byte PDF whose
// page tree declares 2,000,000 pages — the document this cap exists for — so the stand-in's idea of pdf.js is
// checked against pdf.js's own. Fixtures are synthetic: blank pages, TESTHOST, no recorded document.
import { test, beforeEach } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";
import { makeRender, pageCapMessage, capMessage, fmtCount, DEFAULT_MAX_PAGES, DEFAULT_MAX_BYTES, type PdfLib } from "./pdf-chunk";

// ── a fake DOM: what the chunk touches of an element, with every creation counted ───────────────

class FakeEl {
  tagName: string;
  className = "";
  dataset: Record<string, string> = {};
  style: Record<string, string> = {};
  children: FakeEl[] = [];
  parentElement: FakeEl | null = null;
  textContent = "";
  clientWidth = 0;
  width = 300; height = 150;
  private backing: unknown = null;
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
  /** A canvas's 2D context, for the legacy-pdf.js leg: @napi-rs/canvas at the element's current size. */
  getContext(kind: string): unknown {
    if (!this.backing) {
      const napi = createRequire(path.join(NODE_MODULES, "x.js"))("@napi-rs/canvas");
      this.backing = napi.createCanvas(Math.max(1, this.width), Math.max(1, this.height));
    }
    return (this.backing as { getContext(k: string): unknown }).getContext(kind);
  }
}
const NODE_MODULES = path.resolve(process.cwd(), "node_modules");
let created = 0;                                          // every document.createElement, so a refusal can prove it made nothing
const el = (tag: string) => { created++; return new FakeEl(tag); };
const asEl = (e: FakeEl) => e as unknown as HTMLElement;
function viewerTree(): { container: FakeEl; body: FakeEl } {
  const view = new FakeEl("div"); view.className = "fileview"; view.style.overflow = "hidden";
  const body = new FakeEl("div"); body.className = "fileview-body"; body.style.overflow = "auto";
  const container = new FakeEl("div"); container.className = "fileview-pdfhost";
  view.appendChild(body); body.appendChild(container);
  return { container, body };
}
const styleOf = (e: Element) => {
  const st = (e as unknown as FakeEl).style;
  return { overflowY: st.overflowY || st.overflow || "visible" };
};
/** A container render() must never reach for: every property read throws (pdf-lazy.test.ts's probe). */
const untouchable = () => new Proxy({}, {
  get(_t, k) { throw new Error("render() touched the container (" + String(k) + ") for a document it should have refused"); },
}) as unknown as HTMLElement;

// ── a fake pdf.js whose document declares any page count ────────────────────────────────────────

interface FakeLib { lib: PdfLib; calls: { getDocument: number; getPage: number[]; renders: number[]; destroyed: number } }
function fakeLib(numPages: number): FakeLib {
  const calls = { getDocument: 0, getPage: [] as number[], renders: [] as number[], destroyed: 0 };
  class Cancelled extends Error {}
  const lib = {
    GlobalWorkerOptions: { workerSrc: "http://TESTHOST:29855/dist/pdf-worker.js" },
    RenderingCancelledException: Cancelled,
    getDocument: () => {
      calls.getDocument++;
      return {
        promise: Promise.resolve({
          numPages,
          getPage: async (i: number) => {
            calls.getPage.push(i);
            return {
              getViewport: ({ scale }: { scale: number }) => ({ width: 612 * scale, height: 792 * scale }),
              render: () => {
                calls.renders.push(i);
                return { promise: new Promise<void>((res) => setTimeout(res, 1)), cancel: () => {} };
              },
            };
          },
        }),
        destroy: async () => { calls.destroyed++; },
      };
    },
  };
  return { lib: lib as unknown as PdfLib, calls };
}

/** An IntersectionObserver that only registers targets (as a browser's does until layout): with it present the
 *  chunk draws page 1 and waits, so a document at the cap builds its shells without drawing thousands of pages. */
class ObserveOnlyIO {
  static instances: ObserveOnlyIO[] = [];
  targets: unknown[] = [];
  constructor() { ObserveOnlyIO.instances.push(this); }
  observe(t: unknown): void { this.targets.push(t); }
  disconnect(): void {}
}
const bytes = (n = 16) => new ArrayBuffer(n);

beforeEach(() => {
  (globalThis as any).document = { createElement: el };
  (globalThis as any).getComputedStyle = styleOf;
  delete (globalThis as any).IntersectionObserver;
  delete (globalThis as any).ResizeObserver;
  ObserveOnlyIO.instances.length = 0;
  created = 0;
});

// ── the message: the count AND the cap, in the byte cap's shape ────────────────────────────────

test("the page-cap refusal names the count and the cap with thousands separators, in the byte cap's shape; the default cap is 5,000", () => {
  assert.equal(DEFAULT_MAX_PAGES, 5000);
  assert.equal(pageCapMessage(2000000, DEFAULT_MAX_PAGES), "this PDF has 2,000,000 pages, over the 5,000-page cap for rendering pages in the viewer");
  assert.equal(pageCapMessage(5001, 5000), "this PDF has 5,001 pages, over the 5,000-page cap for rendering pages in the viewer");
  assert.equal(pageCapMessage(4, 3), "this PDF has 4 pages, over the 3-page cap for rendering pages in the viewer");
  // the same tail as the byte cap's, so the two refusals read as one family in the caller's notice
  const tail = " for rendering pages in the viewer";
  assert.ok(capMessage(26 * 1024 * 1024, DEFAULT_MAX_BYTES).endsWith(tail));
  assert.ok(pageCapMessage(6000, DEFAULT_MAX_PAGES).endsWith(tail));
  // the separators are locale-independent: the same text on every machine
  assert.equal(fmtCount(0), "0");
  assert.equal(fmtCount(999), "999");
  assert.equal(fmtCount(1000), "1,000");
  assert.equal(fmtCount(2147483647), "2,147,483,647");
});

// ── the refusal: after pdf.js opens the document, before a shell exists or the container is touched ─

test("a count over the cap is refused by name once pdf.js has opened the document — no element made, no page read, the container untouched — and the document is released", async () => {
  for (const count of [2000000, 2147483647, DEFAULT_MAX_PAGES + 1]) {
    created = 0;
    const { lib, calls } = fakeLib(count);
    await assert.rejects(makeRender(lib)(bytes(), untouchable()),
      (e: unknown) => e instanceof Error && e.message === pageCapMessage(count, DEFAULT_MAX_PAGES), "the exact message for " + count);
    assert.equal(calls.getDocument, 1, "pdf.js opened the document: the count is only knowable after that");
    assert.equal(created, 0, "no shell was built for " + count + " pages — not the root, not one wrapper");
    assert.deepEqual(calls.getPage, [], "no page was read: the count is refused before page 1's aspect is asked for");
    assert.equal(calls.destroyed, 1, "the document and its worker are released");
  }
});

test("the byte cap comes first: over both, the refusal names the bytes and pdf.js never opens the file", async () => {
  const { lib, calls } = fakeLib(2000000);
  await assert.rejects(makeRender(lib)(bytes(DEFAULT_MAX_BYTES + 1), untouchable()), /over the 25\.0 MB cap/);
  assert.equal(calls.getDocument, 0);
  assert.equal(created, 0);
});

test("strictly over: a document exactly at the cap builds every shell and renders; `maxPages` sets the cap", async () => {
  (globalThis as any).IntersectionObserver = ObserveOnlyIO;
  // at the default cap: 5,000 shells, page 1 drawn, the observer watching every wrapper
  const at = fakeLib(DEFAULT_MAX_PAGES);
  const { container } = viewerTree();
  const drawn: number[] = [];
  const h = await makeRender(at.lib)(bytes(), asEl(container), { onPage: (p) => drawn.push(p.index) });
  assert.equal(h.pages, DEFAULT_MAX_PAGES);
  assert.equal(container.children[0].children.length, DEFAULT_MAX_PAGES, "one wrapper per page");
  assert.equal(ObserveOnlyIO.instances[0].targets.length, DEFAULT_MAX_PAGES, "every wrapper observed");
  assert.deepEqual(drawn, [1]);
  h.dispose();
  assert.equal(container.children.length, 0);
  // a caller's own cap: 3 pages under a cap of 3 render; 4 do not, and the message carries the caller's numbers
  const three = fakeLib(3);
  const t2 = viewerTree();
  const h3 = await makeRender(three.lib)(bytes(), asEl(t2.container), { maxPages: 3 });
  assert.equal(h3.pages, 3);
  h3.dispose();
  const four = fakeLib(4);
  await assert.rejects(makeRender(four.lib)(bytes(), untouchable(), { maxPages: 3 }),
    (e: unknown) => e instanceof Error && e.message === "this PDF has 4 pages, over the 3-page cap for rendering pages in the viewer");
  assert.equal(four.calls.destroyed, 1);
});

// ── a count below zero: no pages, so the caller's page-less path runs ─────────────────────────────

test("a count below zero — an integer pdf.js accepts — resolves as a page-less document: `pages: 0`, an empty root, no page read", async () => {
  const { lib, calls } = fakeLib(-1);
  const { container } = viewerTree();
  const h = await makeRender(lib)(bytes(), asEl(container));
  assert.equal(h.pages, 0, "file-view's `h.pages === 0` path disposes this and shows the frame, told why; -1 slipped past it into a blank root");
  assert.equal(container.children.length, 1, "the root, as for any page-less document");
  assert.equal(container.children[0].children.length, 0, "…holding no shells");
  assert.deepEqual(calls.getPage, []);
  h.dispose();
  assert.equal(container.children.length, 0);
  assert.equal(calls.destroyed, 1);
});

// ── the same against pdf.js's legacy build, on the document this cap exists for ─────────────────

const LEGACY = path.join(NODE_MODULES, "pdfjs-dist", "legacy", "build", "pdf.mjs");
const LEGACY_WORKER = path.join(NODE_MODULES, "pdfjs-dist", "legacy", "build", "pdf.worker.mjs");
const NAPI = path.join(NODE_MODULES, "@napi-rs", "canvas", "package.json");
const SKIP_LEGACY = fs.existsSync(LEGACY) && fs.existsSync(LEGACY_WORKER) && fs.existsSync(NAPI)
  ? false
  : "pdfjs-dist's legacy build or @napi-rs/canvas is not installed under vscode-extension/node_modules (run `npm ci` there); the real-pdf.js page-cap tests did not run";

/** A PDF from its objects, with a correct xref (the generator the other chunk tests copy). */
function pdfOf(objs: string[]): ArrayBuffer {
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
const PAGE = (parent: number) => `<< /Type /Page /Parent ${parent} 0 R /MediaBox [0 0 612 792] >>`;
/** The hostile page tree: the top-level Pages holds [A, B] and declares `count`; A is a Pages node with ONE page
 *  and a /Count of count − 1, B is a page. pdf.js's last-page check asks for page count − 1, skips A by its /Count
 *  and lands on B; page 1 is A's page. Two real pages, `count` declared. */
const hostilePdf = (count: number) => pdfOf([
  "<< /Type /Catalog /Pages 2 0 R >>",
  `<< /Type /Pages /Kids [3 0 R 4 0 R] /Count ${count} >>`,
  `<< /Type /Pages /Parent 2 0 R /Kids [5 0 R] /Count ${count - 1} >>`,
  PAGE(2),
  PAGE(3),
]);
/** An honest page tree of `count` blank pages, or one whose /Count is `declared` over the same kids. */
const plainPdf = (count: number, declared = count) => pdfOf([
  "<< /Type /Catalog /Pages 2 0 R >>",
  `<< /Type /Pages /Kids [${Array.from({ length: count }, (_, i) => `${3 + i} 0 R`).join(" ")}] /Count ${declared} >>`,
  ...Array.from({ length: count }, () => PAGE(2)),
]);

async function legacyLib(): Promise<PdfLib> {
  const legacy = (await import(pathToFileURL(LEGACY).href)) as unknown as PdfLib;
  legacy.GlobalWorkerOptions.workerSrc = pathToFileURL(LEGACY_WORKER).href;   // node: pdf.js runs its parser on the main thread from this file
  return legacy;
}
/** pdf.js's own count for the bytes, read directly — the mechanism the cap answers, pinned so a change in pdf.js is
 *  loud here rather than a silent narrowing of what these tests prove. */
async function pdfjsCount(legacy: PdfLib, data: ArrayBuffer): Promise<number> {
  const t = legacy.getDocument({ data: new Uint8Array(data.slice(0)) });
  try { return (await t.promise).numPages; } finally { void t.destroy(); }
}

test("pdf.js (legacy build) opens a 529-byte PDF declaring 2,000,000 pages and reports that count; render() refuses it by name with the container untouched", { skip: SKIP_LEGACY }, async () => {
  const legacy = await legacyLib();
  const warn = console.warn;
  console.warn = () => {};
  try {
    const hostile = hostilePdf(2000000);
    assert.ok(hostile.byteLength < 1024, `the document is ${hostile.byteLength} bytes — nowhere near the byte cap`);
    assert.equal(await pdfjsCount(legacy, hostile), 2000000,
      "pdf.js takes the top-level /Count on faith once the last page resolves (a nested Pages node is skipped by its own /Count). " +
      "If this fails, pdf.js now validates the count: the cap still stands, re-anchor this pin");
    await assert.rejects(makeRender(legacy)(hostile, untouchable()),
      (e: unknown) => e instanceof Error && e.message === pageCapMessage(2000000, DEFAULT_MAX_PAGES));
    assert.equal(created, 0, "no shell was built");
    // the largest count a 32-bit /Count can carry opens the same way and is refused the same way
    const max = hostilePdf(2147483647);
    assert.equal(await pdfjsCount(legacy, max), 2147483647);
    await assert.rejects(makeRender(legacy)(max, untouchable()), /2,147,483,647 pages, over the 5,000-page cap/);
    assert.equal(created, 0);
  } finally { console.warn = warn; }
});

test("pdf.js (legacy build): an honest two-page PDF renders under the default cap and is refused under a cap of 1, naming both numbers", { skip: SKIP_LEGACY }, async () => {
  const legacy = await legacyLib();
  const warn = console.warn;
  console.warn = () => {};
  try {
    const two = plainPdf(2);
    const { container } = viewerTree();
    const h = await makeRender(legacy)(two, asEl(container));
    assert.equal(h.pages, 2);
    assert.equal(container.children[0].children.length, 2);
    assert.ok(container.children[0].children[0].querySelector("canvas.fileview-pdf-canvas")!.width > 0, "page 1 drew");
    h.dispose();
    created = 0;
    await assert.rejects(makeRender(legacy)(two, untouchable(), { maxPages: 1 }),
      (e: unknown) => e instanceof Error && e.message === "this PDF has 2 pages, over the 1-page cap for rendering pages in the viewer");
    assert.equal(created, 0);
  } finally { console.warn = warn; }
});

test("pdf.js (legacy build) opens a PDF whose /Count is -1 with numPages -1; render() resolves it as page-less, so the caller's page-less path runs", { skip: SKIP_LEGACY }, async () => {
  const legacy = await legacyLib();
  const warn = console.warn;
  console.warn = () => {};
  try {
    const neg = plainPdf(1, -1);
    assert.equal(await pdfjsCount(legacy, neg), -1, "pdf.js's integer check admits a negative count; its last-page check returns early for counts of 1 or below");
    const { container } = viewerTree();
    const h = await makeRender(legacy)(neg, asEl(container));
    assert.equal(h.pages, 0);
    assert.equal(container.children.length, 1);
    assert.equal(container.children[0].children.length, 0);
    h.dispose();
    assert.equal(container.children.length, 0);
  } finally { console.warn = warn; }
});

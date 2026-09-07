// A PDF page drawn with an image pdf.js could not decode is LOUD in the sheet (plans/file-review.md, Slice 4; the
// 2026-09-06 review, second pass). The chunk ships pdf.js without its wasm decoders, so a JPEG 2000, JBIG2 or CCITT fax
// image (the encodings scanned PDFs are made of) fails in the worker and is dropped: pdf.js warns on the WORKER's
// console, where no one is looking, and paints nothing where the image was — the page resolved, onPage fired,
// onPageError never did, and a scanned page was an empty white sheet that took region comments and said nothing
// (the review's probe: every pixel of an 800×1035 page white; the header's own paragraph conceded it). pdf.js exposes
// no event for a dropped image, but its page object store — the record its canvas renderer paints each image from —
// holds every image the page paints once the draw is done, and a decode it gave up on is resolved there as null.
// The chunk reads that store after each draw (droppedImages) and puts a notice band over the top of the sheet, in the
// error dress, naming the page and the count, once for the page's life; the canvas stays, since the rest of the page
// is drawn. Three legs. STAND-IN: a fake pdf.js whose page proxies carry a store — the band on a page with a null, its
// text, its geometry (absolute, top, pointer-events none, the sheet's ground), none on a clean page, no second band on
// a redraw, one console warning. LEGACY pdf.js under Node over synthetic PDFs carrying one image each with the three
// filters (a JPX codestream header pdf.js reads the size from, then hands to the decoder it has not got; CCITT G4
// bytes; JBIG2 bytes) and one plain page: the store contract holds against the installed build — null per dropped
// image, a band on each of the three, the page white where the image was, and none on the plain page. CHROMIUM
// (skips by name without playwright's chromium): the production bundles over the same fixture, so the null reaches
// the store through a real Worker's messages as it does through Node's loopback. Fixtures are synthetic throughout:
// hand-built PDFs, invented image bytes, TESTHOST.
import { test, beforeEach } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";
import { makeRender, droppedImages, droppedImagesMessage, type PdfLib } from "./pdf-chunk";

const EXT = process.cwd();                                        // vscode-extension, where npm test runs
const ROOT = path.resolve(EXT, "..");
const requireExt = createRequire(path.join(EXT, "package.json"));
const CHUNK = fs.readFileSync(path.join(ROOT, "ui", "webview", "pdf-chunk.ts"), "utf8");

// ── pure: the count and the band's text ──────────────────────────────────────────────────────────

test("droppedImages counts the nulls in a page's object store, and nothing where there is no store", () => {
  assert.equal(droppedImages({ objs: [["img_p0_1", null], ["img_p0_2", { width: 4 }], ["pattern_p0_3", [1, 2]]] }), 1);
  assert.equal(droppedImages({ objs: [["img_p0_1", null], ["img_p0_2", null]] }), 2);
  assert.equal(droppedImages({ objs: [["img_p0_1", { width: 4 }]] }), 0);
  assert.equal(droppedImages({ objs: [] }), 0);
  assert.equal(droppedImages({}), 0, "a stand-in page with no store");
  // an iterable, not an array: pdf.js's PDFObjects is a generator
  function* store(): Generator<unknown[]> { yield ["img_p0_1", null]; yield ["img_p0_2", undefined]; }
  assert.equal(droppedImages({ objs: store() }), 1, "null alone is pdf.js's mark for a dropped image; an unresolved entry is not yielded at all");
});

test("the band's text names the page, the count, what this view cannot draw, and where the whole page is", () => {
  assert.equal(droppedImagesMessage(3, 1),
    "Page 3: 1 image could not be decoded and is left blank. This view has no JPEG 2000, JBIG2, or fax (CCITT) decoder yet; the browser's own PDF viewer shows the whole page.");
  assert.equal(droppedImagesMessage(12, 2),
    "Page 12: 2 images could not be decoded and are left blank. This view has no JPEG 2000, JBIG2, or fax (CCITT) decoder yet; the browser's own PDF viewer shows the whole page.");
  for (const t of [droppedImagesMessage(1, 1), droppedImagesMessage(1, 3)]) {
    assert.doesNotMatch(t, /\b(chunk|canvas|worker|wasm|objs|pdf\.js|romp|card|panel)\b/i, "the person's words: no build or DOM machinery, no romp nouns");
    assert.doesNotMatch(t, /—/, "no em dash in copy the person reads");
  }
});

// ── a fake DOM: what the chunk touches of an element ─────────────────────────────────────────────

class FakeEl {
  tagName: string;
  className = "";
  dataset: Record<string, string> = {};
  style: Record<string, string> = {};
  children: FakeEl[] = [];
  parentElement: FakeEl | null = null;
  textContent = "";
  /** the width layout gives this box — set on the host; inherited by what is inside it (the chunk fits pages to its root's) */
  layoutWidth?: number;
  get clientWidth(): number { for (let n: FakeEl | null = this; n; n = n.parentElement) if (n.layoutWidth !== undefined) return n.layoutWidth; return 0; }
  private _w = 300; private _h = 150;             // a canvas's element default, which the chunk must not leave in place
  get width(): number { return this._w; }
  set width(v: number) { this._w = v; }
  get height(): number { return this._h; }
  set height(v: number) { this._h = v; }
  constructor(tag: string) { this.tagName = tag.toUpperCase(); }
  appendChild(c: FakeEl): FakeEl { c.remove(); c.parentElement = this; this.children.push(c); return c; }
  remove(): void { const p = this.parentElement; if (p) { p.children.splice(p.children.indexOf(this), 1); this.parentElement = null; } }
  querySelectorAll(sel: string): FakeEl[] {
    const [tag, ...cls] = sel.split(".");
    const out: FakeEl[] = [];
    const walk = (e: FakeEl) => { for (const c of e.children) { if ((!tag || c.tagName === tag.toUpperCase()) && cls.every((k) => c.className.split(" ").includes(k))) out.push(c); walk(c); } };
    walk(this);
    return out;
  }
  querySelector(sel: string): FakeEl | null { return this.querySelectorAll(sel)[0] || null; }
  /** A 2d context that records nothing: the staged copy reads `.canvas` off it and draws into the page's canvas. */
  getContext(): { canvas: FakeEl; drawImage(): void } { return { canvas: this, drawImage() {} }; }
}
const el = (tag: string) => new FakeEl(tag);
const asEl = (e: FakeEl) => e as unknown as HTMLElement;
/** Each child of a wrapper as TAG.class.class. */
const kidsOf = (w: FakeEl) => w.children.map((c) => [c.tagName, ...c.className.split(/\s+/).filter(Boolean)].join("."));

// ── a fake pdf.js whose pages carry an object store ─────────────────────────────────────────────

interface FakeLib { lib: PdfLib; renders: number[] }
/** `stores[i]` is page i+1's object store after its draw: pdf.js's PDFObjects, as [objId, data] pairs. */
function fakeLib(stores: unknown[][][]): FakeLib {
  const renders: number[] = [];
  class Cancelled extends Error {}
  const lib = {
    GlobalWorkerOptions: { workerSrc: "http://TESTHOST:29855/dist/pdf-worker.js" },
    RenderingCancelledException: Cancelled,
    getDocument: () => ({
      promise: Promise.resolve({
        numPages: stores.length,
        getPage: async (i: number) => ({
          objs: stores[i - 1],
          getViewport: ({ scale }: { scale: number }) => ({ width: 612 * scale, height: 792 * scale }),
          render: () => { renders.push(i); return { promise: new Promise<void>((res) => setTimeout(res, 1)), cancel() {} }; },
        }),
      }),
      destroy: async () => {},
    }),
  };
  return { lib: lib as unknown as PdfLib, renders };
}
class FakeRO {
  static last: FakeRO | null = null;
  constructor(public cb: () => void) { FakeRO.last = this; }
  observe(): void {}
  disconnect(): void {}
}
async function until(cond: () => boolean, what: string): Promise<void> {
  for (let i = 0; i < 2000; i++) { if (cond()) return; await new Promise((r) => setTimeout(r, 1)); }
  assert.fail("timed out waiting for " + what);
}
const g = globalThis as any;
beforeEach(() => {
  g.document = { createElement: el };
  delete g.IntersectionObserver;                 // no observer: every page draws
  g.ResizeObserver = FakeRO;
  delete g.Worker;
});

test("stand-in: a page whose store holds a null wears the band over its canvas, once; a clean page does not; a redraw adds no second band; one warning", async () => {
  const warn = console.warn; const warned: string[] = [];
  console.warn = (...a: unknown[]) => { warned.push(a.map(String).join(" ")); };
  try {
    const { lib, renders } = fakeLib([
      [["img_p0_1", null], ["img_p0_2", { width: 64 }]],       // page 1: one of two images dropped
      [["img_p1_1", { width: 64 }]],                            // page 2: clean
      [["img_p2_1", null], ["img_p2_2", null]],                 // page 3: both dropped
    ]);
    const host = el("div"); host.className = "fileview-pdfhost"; host.layoutWidth = 800;
    const drawn: number[] = [];
    const h = await makeRender(lib)(new ArrayBuffer(16), asEl(host), { onPage: (p) => drawn.push(p.index) });
    assert.equal(h.pages, 3);
    await until(() => drawn.length >= 3, "every page's draw");
    const wrappers = host.querySelectorAll("div.fileview-pdf-page");
    assert.equal(wrappers.length, 3);
    // page 1: its canvas, then the band; the canvas stays (the rest of the page is drawn and may take a region comment)
    assert.deepEqual(kidsOf(wrappers[0]), ["CANVAS.fileview-pdf-canvas", "DIV.fileview-err.fileview-pdf-page-warn"]);
    const band = wrappers[0].querySelector("div.fileview-pdf-page-warn")!;
    assert.equal(band.textContent, droppedImagesMessage(1, 1));
    assert.equal(band.style.position, "absolute", "over the sheet, not in its flow: the wrapper's box stays the page's");
    assert.equal(band.style.top, "0"); assert.equal(band.style.left, "0"); assert.equal(band.style.right, "0");
    assert.equal(band.style.pointerEvents, "none", "the panel's overlay takes the pointer through it");
    assert.equal(band.style.background, "inherit", "the sheet's own ground, so it reads over a bitmap");
    assert.ok(wrappers[0].querySelector("canvas")!.width > 0, "page 1 has its bitmap");
    // page 2: canvas alone
    assert.deepEqual(kidsOf(wrappers[1]), ["CANVAS.fileview-pdf-canvas"]);
    // page 3: the plural
    assert.equal(wrappers[2].querySelector("div.fileview-pdf-page-warn")!.textContent, droppedImagesMessage(3, 2));
    assert.deepEqual(warned.filter((w) => w.startsWith("pdf-chunk: Page")), ["pdf-chunk: " + droppedImagesMessage(1, 1), "pdf-chunk: " + droppedImagesMessage(3, 2)], "one warning per page with a loss");
    // a width change redraws the pages: the store is read again and the band is not added twice
    assert.equal(wrappers[0].querySelector("canvas")!.width, 800, "drawn width-fit to the host");
    host.layoutWidth = 600;
    const before = renders.length;
    FakeRO.last!.cb();
    await until(() => renders.length >= before + 3 && drawn.length >= 6, "the sharpening redraws");
    assert.equal(host.querySelectorAll("div.fileview-pdf-page-warn").length, 2, "still one band per page with a loss");
    assert.equal(wrappers[0].querySelector("canvas")!.width, 600, "redrawn at the new width");
    assert.deepEqual(kidsOf(wrappers[0]), ["CANVAS.fileview-pdf-canvas", "DIV.fileview-err.fileview-pdf-page-warn"]);
    assert.equal(warned.filter((w) => w.startsWith("pdf-chunk: Page")).length, 2, "and no second warning");
    h.dispose();
    assert.equal(host.children.length, 0);
  } finally { console.warn = warn; }
});

test("the chunk reads the store after the draw, before the bitmap is declared in, and dresses the band as the failed page's notice", () => {
  const code = CHUNK.split("\n").filter((l) => !l.trim().startsWith("//")).join("\n");
  assert.match(code, /if \(!p\.warned\) \{ const dropped = droppedImages\(proxy\); if \(dropped\) warnDropped\(p, dropped\); \}[^\n]*\n\s*p\.drawnAt = cssW;/,
    "after the staged copy, once per page, before drawnAt marks the bitmap in");
  assert.match(code, /note\.className = "fileview-err fileview-pdf-page-warn";/, "the error dress the sheets colour for a white ground, plus a hook of its own");
  assert.match(code, /if \(page\.objs\) for \(const \[, data\] of page\.objs\) if \(data === null\) n\+\+;/, "null is the mark, from pdf.js's own store");
  assert.doesNotMatch(code, /getOperatorList/, "no second evaluation of the page to find its images: the store the draw filled is read");
});

// ── the fixture: one image XObject per page, in the encodings pdf.js decodes only through wasm ────

/** A JPX codestream's opening: SOC, then a SIZ segment pdf.js reads the size and component count from (the header
 *  it parses before decoding), then a few bytes and EOC. A decodable image would carry a COD, QCD and tiles here;
 *  the decoder pdf.js has not got never sees them, so a header is enough to reach the failure the review found. */
function jpxHeader(w: number, h: number, comps: number): Buffer {
  const b: number[] = [0xff, 0x4f, 0xff, 0x51];
  const u16 = (v: number) => b.push((v >> 8) & 0xff, v & 0xff);
  const u32 = (v: number) => b.push((v >>> 24) & 0xff, (v >> 16) & 0xff, (v >> 8) & 0xff, v & 0xff);
  u16(38 + 3 * comps); u16(0);                    // Lsiz, Rsiz
  u32(w); u32(h); u32(0); u32(0);                 // Xsiz Ysiz XOsiz YOsiz
  u32(w); u32(h); u32(0); u32(0);                 // XTsiz YTsiz XTOsiz YTOsiz
  u16(comps);
  for (let i = 0; i < comps; i++) b.push(7, 1, 1);   // Ssiz (8 bits unsigned), XRsiz, YRsiz
  b.push(0xff, 0x52, 0x00, 0x0c, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0);   // a COD segment's worth of bytes, then
  b.push(0xff, 0xd9);                             // EOC
  return Buffer.from(b);
}
type Img = { filter: string; cs: string; bpc: number; parms?: string; data: Buffer };
const IMAGES: Record<string, Img> = {
  jpx: { filter: "JPXDecode", cs: "DeviceRGB", bpc: 8, data: jpxHeader(64, 64, 3) },
  ccitt: { filter: "CCITTFaxDecode", cs: "DeviceGray", bpc: 1, parms: "<< /K -1 /Columns 64 /Rows 64 >>", data: Buffer.from([0x00, 0x10, 0x01, 0x00, 0x10, 0x01, 0x00, 0x08]) },
  jbig2: { filter: "JBIG2Decode", cs: "DeviceGray", bpc: 1, data: Buffer.from([0x00, 0x00, 0x00, 0x01, 0x30, 0x00, 0x01, 0x00, 0x00, 0x00, 0x13]) },
};
/** A PDF of US-letter pages, each painting one image over the whole page (`null` for a page with a filled rectangle
 *  and no image), with a correct xref. */
function scanPdf(pages: Array<Img | null>): Buffer {
  const objs: Buffer[] = [Buffer.from("<< /Type /Catalog /Pages 2 0 R >>")];
  const kids: number[] = [];
  let next = 3;
  const bodies: Buffer[] = [];
  for (const img of pages) {
    const pageId = next++, contentId = next++, imgId = img ? next++ : 0;
    kids.push(pageId);
    const content = img ? "q 612 0 0 792 0 0 cm /Im1 Do Q" : "0 0 0 rg 0 396 306 396 re f";
    bodies.push(Buffer.from(`<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents ${contentId} 0 R${img ? ` /Resources << /XObject << /Im1 ${imgId} 0 R >> >>` : ""} >>`));
    bodies.push(Buffer.from(`<< /Length ${content.length} >>\nstream\n${content}\nendstream`));
    if (img) {
      const head = `<< /Type /XObject /Subtype /Image /Width 64 /Height 64 /ColorSpace /${img.cs} /BitsPerComponent ${img.bpc} /Filter /${img.filter}${img.parms ? ` /DecodeParms ${img.parms}` : ""} /Length ${img.data.length} >>\nstream\n`;
      bodies.push(Buffer.concat([Buffer.from(head, "latin1"), img.data, Buffer.from("\nendstream", "latin1")]));
    }
  }
  objs.push(Buffer.from(`<< /Type /Pages /Kids [${kids.map((k) => k + " 0 R").join(" ")}] /Count ${kids.length} >>`), ...bodies);
  const parts: Buffer[] = [Buffer.from("%PDF-1.5\n", "latin1")];
  let len = parts[0].length;
  const offsets: number[] = [];
  objs.forEach((body, i) => {
    offsets.push(len);
    const chunk = Buffer.concat([Buffer.from(`${i + 1} 0 obj\n`, "latin1"), body, Buffer.from("\nendobj\n", "latin1")]);
    parts.push(chunk); len += chunk.length;
  });
  let xref = `xref\n0 ${objs.length + 1}\n0000000000 65535 f \n`;
  for (const o of offsets) xref += `${String(o).padStart(10, "0")} 00000 n \n`;
  xref += `trailer\n<< /Size ${objs.length + 1} /Root 1 0 R >>\nstartxref\n${len}\n%%EOF\n`;
  parts.push(Buffer.from(xref, "latin1"));
  return Buffer.concat(parts);
}
/** Pages 1–3 carry a JPX, a CCITT and a JBIG2 image; page 4 a black rectangle over its top-left quarter and no image. */
const FIXTURE = () => scanPdf([IMAGES.jpx, IMAGES.ccitt, IMAGES.jbig2, null]);
const bufferOf = (b: Buffer): ArrayBuffer => b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength) as ArrayBuffer;

// ── the installed pdf.js: the three filters decode only through wasm, and a dropped image is a null in the store ──

const WORKER_SRC = fs.readFileSync(path.join(EXT, "node_modules", "pdfjs-dist", "build", "pdf.worker.mjs"), "utf8");
const MAIN_SRC = fs.readFileSync(path.join(EXT, "node_modules", "pdfjs-dist", "build", "pdf.mjs"), "utf8");

test("in the installed pdf.js: JPX, JBIG2 and CCITT images decode only through wasm loaded from wasmUrl, a failed decode is sent as null, and the store yields it — the header's paragraph and this test's premise", () => {
  assert.match(WORKER_SRC, /class JpxImage extends WasmImage \{\s*_filename = "openjpeg\.wasm";/, "JPEG 2000 through OpenJPEG's wasm");
  assert.match(WORKER_SRC, /class JBig2CCITTFaxImage extends WasmImage \{\s*_filename = "jbig2\.wasm";/, "JBIG2 and CCITT through one wasm");
  assert.match(WORKER_SRC, /class CCITTFaxStream extends DecodeStream \{[\s\S]*?JBig2CCITTFaxImage\.instance\.decode\(/, "CCITT fax goes through it");
  assert.match(WORKER_SRC, /class Jbig2Stream extends DecodeStream \{[\s\S]*?JBig2CCITTFaxImage\.instance\.decode\(/, "so does JBIG2");
  assert.match(WORKER_SRC, /`\$\{WasmImage\.#wasmUrl\}\$\{this\._filename\}`/, "the wasm is fetched from wasmUrl, which the chunk does not set (guide-pdf.test.ts pins the omission)");
  // the failure path: warn on the worker's console, then the image sent as null — the mark the chunk reads
  assert.match(WORKER_SRC, /warn\(`Unable to decode image "\$\{objId\}": "\$\{reason\}"\.`\);[\s\S]{0,200}?return this\._sendImgData\(objId, null, cacheGlobally\);/);
  assert.match(MAIN_SRC, /messageHandler\.on\("obj", \(\[id, pageIndex, type, imageData\]\) => \{[\s\S]*?pageProxy\.objs\.resolve\(id, imageData\);/, "the main thread resolves the page's store with what it was sent, null included");
  assert.match(MAIN_SRC, /class PDFObjects \{[\s\S]*?\*\[Symbol\.iterator\]\(\) \{[\s\S]*?yield \[objId, data\];/, "the store iterates [objId, data] over resolved entries");
  // the header names all three encodings, not JPEG 2000 alone (the omission the review found)
  const header = CHUNK.split("\n").filter((l) => l.startsWith("//")).join("\n");
  for (const name of ["JPEG 2000", "JBIG2", "CCITT"]) assert.ok(header.includes(name), "the header names " + name);
});

// ── legacy pdf.js under Node: the fixture, the store, the bands, the white ────────────────────────

const LEGACY = path.join(EXT, "node_modules", "pdfjs-dist", "legacy", "build", "pdf.mjs");
const LEGACY_WORKER = path.join(EXT, "node_modules", "pdfjs-dist", "legacy", "build", "pdf.worker.mjs");
let napi: any = null;
try { napi = requireExt("@napi-rs/canvas"); } catch { napi = null; }
const SKIP_LEGACY = fs.existsSync(LEGACY) && fs.existsSync(LEGACY_WORKER) && napi
  ? false
  : "pdfjs-dist's legacy build or @napi-rs/canvas is not installed under vscode-extension/node_modules (run `npm ci` there); the real-pdf.js dropped-image test did not run";
/** A canvas whose pixels are @napi-rs/canvas's (pdf-lazy-render.test.ts's shape). */
class CanvasEl extends FakeEl {
  private napi: any;
  private w = 300; private h = 150;
  constructor() { super("canvas"); this.napi = napi.createCanvas(300, 150); }
  get width(): number { return this.w; }
  set width(v: number) { this.w = v; if (v > 0) this.napi.width = v; }
  get height(): number { return this.h; }
  set height(v: number) { this.h = v; if (v > 0) this.napi.height = v; }
  getContext(kind = "2d", opts?: unknown): any { return this.napi.getContext(kind, opts); }
}
const pixel = (c: CanvasEl, x: number, y: number): string => Array.from(c.getContext("2d").getImageData(x, y, 1, 1).data as Uint8ClampedArray).join(",");

test("pdf.js (legacy build): a page with a JPX, CCITT or JBIG2 image draws white where the image was and wears the band; a page with none does not", { skip: SKIP_LEGACY }, async () => {
  const legacy = (await import(pathToFileURL(LEGACY).href)) as unknown as PdfLib;
  legacy.GlobalWorkerOptions.workerSrc = pathToFileURL(LEGACY_WORKER).href;   // node: pdf.js runs its parser on the main thread from this file
  g.document = { createElement: (tag: string) => (tag === "canvas" ? new CanvasEl() : el(tag)) };
  const warn = console.warn; const warned: string[] = [];
  console.warn = (...a: unknown[]) => { warned.push(a.map(String).join(" ")); };
  // pdf.js's own account of each dropped image ("Warning: Unable to decode image …", console.warn from the parser running
  // on this thread) lands in `warned` with the chunk's: kept off the test's output, and read below as the console-only
  // signal the band replaces
  try {
    const host = el("div"); host.className = "fileview-pdfhost"; host.layoutWidth = 400;
    const drawn: number[] = []; const errors: unknown[] = [];
    const h = await makeRender(legacy)(bufferOf(FIXTURE()), asEl(host), { onPage: (p) => drawn.push(p.index), onPageError: (e) => errors.push(e) });
    assert.equal(h.pages, 4);
    await until(() => new Set(drawn).size >= 4, "every page's draw");
    assert.deepEqual(errors, [], "no page FAILED: the loss is inside pages that drew, which is the whole problem");
    const wrappers = host.querySelectorAll("div.fileview-pdf-page");
    assert.equal(wrappers.length, 4);
    for (const [i, name] of [[0, "JPX"], [1, "CCITT"], [2, "JBIG2"]] as const) {
      const w = wrappers[i];
      const band = w.querySelector("div.fileview-pdf-page-warn");
      assert.ok(band, `page ${i + 1} (${name}): the band is on the sheet`);
      assert.equal(band!.textContent, droppedImagesMessage(i + 1, 1));
      assert.deepEqual(kidsOf(w), ["CANVAS.fileview-pdf-canvas", "DIV.fileview-err.fileview-pdf-page-warn"], `page ${i + 1}: canvas, then band`);
      const c = w.querySelector("canvas") as CanvasEl;
      assert.equal(c.width, 400, `page ${i + 1} drew`);
      assert.equal(pixel(c, 200, 250), "255,255,255,255", `page ${i + 1} (${name}): white where the image covers the page — the silent blank the band now names`);
    }
    const plain = wrappers[3];
    assert.deepEqual(kidsOf(plain), ["CANVAS.fileview-pdf-canvas"], "page 4 has no image and no band");
    assert.equal(pixel(plain.querySelector("canvas") as CanvasEl, 10, 10), "0,0,0,255", "page 4's rectangle is drawn");
    assert.equal(warned.filter((x) => x.startsWith("pdf-chunk: Page")).length, 3, "one warning per page with a loss");
    // pdf.js's only word on each: a console warning naming the decoder it could not initialise, which is why the band exists
    const dropped = warned.filter((x) => /Unable to decode image/.test(x));
    assert.equal(dropped.length, 3, "one pdf.js warning per dropped image; seen: " + JSON.stringify(warned));
    assert.match(dropped[0], /img_p0_1.*OpenJPEG failed to initialize/, "JPX: OpenJPEG's wasm, not shipped");
    assert.match(dropped[1], /img_p1_1.*JBig2 failed to initialize/, "CCITT: the JBIG2/CCITT wasm, not shipped");
    assert.match(dropped[2], /img_p2_1.*JBig2 failed to initialize/, "JBIG2: the same wasm");
    assert.ok(warned.some((x) => /Ensure that the `wasmUrl` API parameter is provided/.test(x)), "…because no wasmUrl is configured (the guide's stated omission)");
    h.dispose();
  } finally { console.warn = warn; }
});

// ── in Chromium: the production bundles over the same fixture ────────────────────────────────────

const OUT = path.join(EXT, "out-tests", "pdf-chunk-dropped-images");
let chromium: any = null;
let SKIP: string | false = false;
try {
  chromium = requireExt("playwright").chromium;
  const exe: string = chromium.executablePath();
  if (!exe || !fs.existsSync(exe)) SKIP = "playwright's chromium is not installed here (`npx playwright install chromium` in vscode-extension); the dropped-image browser test did not run";
} catch {
  SKIP = "playwright is not installed under vscode-extension/node_modules (run `npm ci` there); the dropped-image browser test did not run";
}
async function buildChunk(): Promise<void> {
  await requireExt("esbuild").build({
    entryPoints: [
      path.join(ROOT, "ui", "webview", "pdf-chunk.ts"),
      { in: path.join(EXT, "node_modules", "pdfjs-dist", "build", "pdf.worker.mjs"), out: "pdf-worker" },
    ],
    nodePaths: [path.join(EXT, "node_modules")],
    bundle: true, format: "iife", platform: "browser", target: "es2020", outdir: OUT, logLevel: "silent",
  });
}
/** The viewer's rules for the elements involved, from the sheet the viewer loads: the sheet's white and the dress. */
function viewerRules(): string {
  const css = fs.readFileSync(path.join(ROOT, "ui", "webview", "styles.css"), "utf8");
  const rules = css.match(/^\.fileview-(?:pdf|pdf-page|pdf-canvas|err|pdf-page \.fileview-err) \{[^}]*\}/gm) || [];
  assert.ok(rules.length >= 4, "styles.css has the sheet's rules: " + rules.length);
  return rules.join("\n");
}
// the body is tall enough (2000px, plus the observer's one-height margin) that all four ~900px pages draw and none is
// evicted, so every canvas holds its bitmap when the pixels are read
const HTML = (rules: string) => `<!doctype html><html><head><meta charset="utf-8"><style>:root{--warn:#c90;--warn-on-white:#8a5a00;--shadow-modal:none}${rules}
.fileview-body{overflow:auto;height:2000px;width:700px}</style></head><body>
<div class="fileview"><div class="fileview-body" id="body"><div class="fileview-pdfhost" id="host"></div></div></div>
<script src="/dist/pdf-chunk.js?v=1725300000"></script>
</body></html>`;

test("in Chromium: the built chunk over the fixture — the null reaches the store through a real Worker, the bands are on pages 1–3 over white sheets, page 4 is clean", { skip: SKIP }, async () => {
  await buildChunk();
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage({ viewport: { width: 900, height: 2200 } });
    const logs: string[] = [];
    page.on("console", (m: any) => logs.push(m.type() + ": " + m.text()));
    page.on("pageerror", (e: Error) => logs.push("pageerror: " + e.message));
    const html = HTML(viewerRules());
    await page.route("http://TESTHOST/**", (route: any) => {
      const u = new URL(route.request().url());
      if (u.pathname === "/view.html") return route.fulfill({ contentType: "text/html", body: html });
      const f = path.join(OUT, path.basename(u.pathname));
      if (u.pathname.startsWith("/dist/") && fs.existsSync(f)) return route.fulfill({ contentType: "application/javascript", body: fs.readFileSync(f) });
      return route.fulfill({ status: 404, body: "" });
    });
    await page.goto("http://TESTHOST/view.html");
    await page.waitForFunction(() => !!(window as any).__rompPdf, null, { timeout: 10000 });
    const r = await page.evaluate(async (b64: string) => {
      const bin = atob(b64); const u8 = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
      const w = window as any; w.__drawn = []; w.__errs = [];
      const h = await w.__rompPdf.render(u8.buffer, document.getElementById("host"), { onPage: (p: any) => w.__drawn.push(p.index), onPageError: (e: unknown) => w.__errs.push(e) });
      w.__h = h;
      return h.pages as number;
    }, FIXTURE().toString("base64"));
    assert.equal(r, 4);
    await page.waitForFunction(() => new Set((window as any).__drawn).size >= 4, null, { timeout: 15000 });
    const snap = await page.evaluate(() => {
      const wrappers = Array.from(document.querySelectorAll(".fileview-pdf-page")) as HTMLElement[];
      return wrappers.map((wr) => {
        const c = wr.querySelector("canvas") as HTMLCanvasElement | null;
        const band = wr.querySelector(".fileview-pdf-page-warn") as HTMLElement | null;
        const px = c && c.width ? Array.from(c.getContext("2d")!.getImageData(Math.floor(c.width / 2), Math.floor(c.height / 2), 1, 1).data).join(",") : null;
        const kids = Array.from(wr.childNodes, (n) => [(n as HTMLElement).tagName, ...String((n as HTMLElement).className).split(/\s+/).filter(Boolean)].join("."));
        const wb = wr.getBoundingClientRect(), cb = c ? c.getBoundingClientRect() : null;
        return {
          kids, px, text: band ? band.textContent : null,
          bandTop: band ? Math.round(band.getBoundingClientRect().top - wb.top) : null,
          bandBg: band ? getComputedStyle(band).backgroundColor : null,
          bandColor: band ? getComputedStyle(band).color : null,
          boxIsCanvas: cb ? Math.abs(cb.height - wb.height) < 1 : false,
          errs: (window as any).__errs.length,
        };
      });
    });
    assert.equal(snap[0].errs, 0, "no page failed");
    const BAND = "DIV.fileview-err.fileview-pdf-page-warn";
    for (const [i, name] of [[0, "JPX"], [1, "CCITT"], [2, "JBIG2"]] as const) {
      const s = snap[i];
      assert.deepEqual(s.kids, ["CANVAS.fileview-pdf-canvas", BAND], `page ${i + 1} (${name}): canvas, then the band`);
      assert.equal(s.text, droppedImagesMessage(i + 1, 1));
      assert.equal(s.px, "255,255,255,255", `page ${i + 1} (${name}): white at the centre of a page the image was to cover`);
      assert.equal(s.bandTop, 0, "the band sits at the top of the sheet");
      assert.equal(s.bandBg, "rgb(255, 255, 255)", "on the sheet's own white (inherited), so it reads over a bitmap");
      assert.equal(s.bandColor, "rgb(138, 90, 0)", "in the dress the sheets colour for a white ground (--warn-on-white)");
      assert.equal(s.boxIsCanvas, true, "the band adds nothing to the wrapper's box: the overlay's geometry is the page's");
    }
    assert.deepEqual(snap[3].kids, ["CANVAS.fileview-pdf-canvas"], "page 4: no image, no band");
    assert.equal(snap[3].px, "255,255,255,255", "page 4's centre is white too — its rectangle is in the top-left quarter; the band, not the pixels, is what tells the pages apart");
    assert.equal(logs.filter((l) => l.startsWith("pageerror")).length, 0, logs.join("\n"));
    assert.equal(logs.filter((l) => /^warning: pdf-chunk: Page/.test(l)).length, 3, "one warning per page with a loss:\n" + logs.join("\n"));
    await page.evaluate(() => (window as any).__h.dispose());
  } finally {
    await browser.close();
  }
});

// The PDF chunk's STAGED DRAW (plans/file-review.md, Slice 4; the review of 2026-09-06). paint() drew each page in
// place: it sized the page's canvas for the new width and handed that canvas to pdf.js. Both steps blank a canvas —
// assigning its width or height resets the bitmap, and pdf.js fills its target white before the first operator runs
// (the fill in a microtask, the operators in animation frames) — so from the moment a draw started until its last
// operator ran, the page on screen was a SIZED, EMPTY canvas. Every sharpening redraw flashed white (the header's
// "scaled bitmap stays on screen" was false), and the panel, which reads a canvas with a size as a drawn page, cut a
// blank crop from that window and kept it under a key nothing changes on a redraw or an eviction; a redraw then
// cancelled by eviction left the card showing that blank where the region's picture belonged, until the page drew
// again. Now pdf.js draws into a STAGING canvas off the DOM, and the page's canvas takes the finished bitmap in one
// synchronous step — sized, then filled, with nothing else running between — so a page's canvas is 0×0 or complete,
// never sized and empty; a redraw keeps the old bitmap until the new one is in; a cancelled draw reaches the page's
// canvas only through drop(), which zeroes it.
//
// Two legs. NODE: makeRender over a stand-in pdf.js whose draws the test holds and releases (so "in flight" is a state
// held still), and a fake DOM whose canvases record every size assignment and every drawImage — the render target is a
// canvas that is not the page's and not in the DOM; the page's canvas is untouched while a first draw or a redraw is in
// flight; sizing and filling land together when the draw does; the stage is released after; a redraw cancelled by
// eviction ends with the page's canvas 0×0 and no copy; a cancellation arriving after pdf.js finished (the task resolves
// all the same) copies nothing, and the page draws again on return; a page canvas with no 2d context fails loudly in
// place. Source pins hold the shape (the target, the contiguity of size and fill) and the header's statement of the
// trust boundary. CHROMIUM (skips by name without playwright's chromium): the built chunk over real pdf.js on a heavy
// page with a red square at its centre, a frame sampler reading the page canvas's size and centre pixel through a
// sharpening redraw — every frame is the old bitmap or the new, never a sized canvas with a blank centre — and an
// eviction mid-redraw leaving the canvas 0×0 with no onPage, then a redraw on return. Fixtures are synthetic:
// hand-built PDFs of blank pages, TESTHOST.
import { test, beforeEach } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { makeRender, type PdfLib, type PageInfo, type PageError } from "./pdf-chunk";

const PKG = process.cwd();                                   // vscode-extension, where npm test runs
const ROOT = path.resolve(PKG, "..");
const UI = path.join(ROOT, "ui", "webview");
const CHUNK = fs.readFileSync(path.join(UI, "pdf-chunk.ts"), "utf8");

// ── a fake DOM whose canvases record what is done to them ───────────────────────────────────────

/** One thing done to a canvas: a size assigned, or a copy into it (with the source). */
interface Op { el: FakeEl; op: "width" | "height" | "drawImage"; value?: number; src?: FakeEl }
const ops: Op[] = [];

class FakeEl {
  tagName: string;
  className = "";
  dataset: Record<string, string> = {};
  style: Record<string, string> = {};
  children: FakeEl[] = [];
  parentElement: FakeEl | null = null;
  textContent = "";
  src = ""; alt: string | undefined = undefined;   // an <img>'s, as the cue sets them
  /** the width layout gives this box — set on the container; inherited by what is inside it (the chunk reads its root's) */
  layoutWidth?: number;
  get clientWidth(): number { for (let n: FakeEl | null = this; n; n = n.parentElement) if (n.layoutWidth !== undefined) return n.layoutWidth; return 0; }
  private w = 300; private h = 150;                // a canvas's element default, which the chunk must not leave in place
  /** set on a page's canvas by the loud-failure test: its getContext answers null, as a browser's does when it cannot */
  contextless = false;
  constructor(tag: string) { this.tagName = tag.toUpperCase(); }
  get width(): number { return this.w; }
  set width(v: number) { this.w = v; ops.push({ el: this, op: "width", value: v }); }
  get height(): number { return this.h; }
  set height(v: number) { this.h = v; ops.push({ el: this, op: "height", value: v }); }
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
  /** A canvas's 2D context: `.canvas` is the element, as a browser's is; drawImage records its source. */
  getContext(kind: string): { canvas: FakeEl; drawImage(src: FakeEl, x: number, y: number): void } | null {
    if (kind !== "2d" || this.tagName !== "CANVAS" || this.contextless) return null;
    return { canvas: this, drawImage: (src) => { ops.push({ el: this, op: "drawImage", src }); } };
  }
}
const el = (tag: string) => new FakeEl(tag);
const asEl = (e: FakeEl) => e as unknown as HTMLElement;
/** The viewer's tree around the chunk's container, the host laid out `width` wide. */
function viewerTree(width = 800): { container: FakeEl } {
  const view = el("div"); view.className = "fileview"; view.style.overflow = "hidden";
  const body = el("div"); body.className = "fileview-body"; body.style.overflow = "auto";
  const container = el("div"); container.className = "fileview-pdfhost"; container.layoutWidth = width;
  view.appendChild(body); body.appendChild(container);
  return { container };
}
const styleOf = (e: Element) => {
  const st = (e as unknown as FakeEl).style;
  return { overflowY: st.overflowY || st.overflow || "visible" };
};
/** What was done to `e` since `from`, as "op:value" (a copy as "drawImage"). */
const opsOn = (e: FakeEl, from = 0) => ops.slice(from).filter((o) => o.el === e).map((o) => (o.op === "drawImage" ? "drawImage" : o.op + ":" + o.value));
const H = (w: number) => Math.round(w * 792 / 612);       // a US-letter page's canvas height at width w (ratio 1 under node)

// ── a fake pdf.js whose draws the test holds and releases, recording the canvas each is handed ──

interface FakeLib {
  lib: PdfLib;
  calls: { getPage: number[]; renders: number[]; targets: FakeEl[]; cancelled: number; destroyed: number };
  inFlight: (i: number) => boolean;
  release: (i: number) => void;
}
function fakeLib(pages: number): FakeLib {
  const calls = { getPage: [] as number[], renders: [] as number[], targets: [] as FakeEl[], cancelled: 0, destroyed: 0 };
  const gates = new Map<number, () => void>();
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
            render: ({ canvas }: { canvas: FakeEl }) => {
              calls.renders.push(i); calls.targets.push(canvas);
              let cancel = () => {};
              const promise = new Promise<void>((res, rej) => {
                gates.set(i, res);
                // as pdf.js's: a cancel after the draw finished rejects a settled promise, which stays resolved
                cancel = () => { gates.delete(i); calls.cancelled++; rej(new Cancelled("cancelled")); };
              });
              return { promise, cancel: () => cancel() };
            },
          };
        },
      }),
      destroy: async () => { calls.destroyed++; },
    }),
  };
  return {
    lib: lib as unknown as PdfLib, calls,
    inFlight: (i) => gates.has(i),
    release: (i) => { const g = gates.get(i); assert.ok(g, `page ${i} has no draw in flight to release`); gates.delete(i); g!(); },
  };
}

class FakeIO {
  static instances: FakeIO[] = [];
  constructor(public cb: (entries: unknown[], io: FakeIO) => void) { FakeIO.instances.push(this); }
  observe(): void {}
  disconnect(): void {}
  fire(states: Array<[FakeEl, boolean]>): void { this.cb(states.map(([target, isIntersecting]) => ({ target, isIntersecting })), this); }
}
class FakeRO {
  static instances: FakeRO[] = [];
  constructor(public cb: () => void) { FakeRO.instances.push(this); }
  observe(): void {}
  disconnect(): void {}
  fire(): void { this.cb(); }
}

async function until(cond: () => boolean, what: string): Promise<void> {
  for (let i = 0; i < 2000; i++) { if (cond()) return; await new Promise((r) => setTimeout(r, 1)); }
  assert.fail("timed out waiting for " + what);
}
const settle = () => new Promise((r) => setTimeout(r, 10));
const canvasOf = (wrap: FakeEl) => wrap.querySelector("canvas.fileview-pdf-canvas");
const pagesOf = (container: FakeEl) => container.children[0].children;

beforeEach(() => {
  (globalThis as any).document = { createElement: el };
  (globalThis as any).getComputedStyle = styleOf;
  delete (globalThis as any).IntersectionObserver;
  delete (globalThis as any).ResizeObserver;
  delete (globalThis as any).window;
  FakeIO.instances.length = 0; FakeRO.instances.length = 0;
  ops.length = 0;
});

/** Start a render whose first page's draw is held; resolves once that draw is in flight, carrying the render's promise
 *  in an object (an async function returning it bare would adopt it and wait on the very draw the test means to release). */
async function startHeld(f: FakeLib, container: FakeEl, opts: { onPage?: (p: PageInfo) => void; onPageError?: (e: PageError) => void } = {}): Promise<{ pending: Promise<{ pages: number; dispose(): void }> }> {
  const pending = makeRender(f.lib)(new ArrayBuffer(16), asEl(container), opts);
  pending.catch(() => {});
  await until(() => f.inFlight(1), "page 1's draw to start");
  return { pending };
}

// ── the first draw ──────────────────────────────────────────────────────────────────────────────

test("a first draw: pdf.js is handed a staging canvas that is not the page's and not in the DOM; the page's canvas stays 0×0 while the draw is in flight, then is sized and filled in one step from the stage, which is released", async () => {
  const f = fakeLib(2);
  const { container } = viewerTree(800);
  const drawn: PageInfo[] = [];
  const { pending } = await startHeld(f, container, { onPage: (p) => drawn.push(p) });
  const c1 = canvasOf(pagesOf(container)[0])!;
  const stage = f.calls.targets[0];
  assert.notEqual(stage, c1, "pdf.js draws into a canvas of its own, not the page's");
  assert.equal(stage.tagName, "CANVAS");
  assert.equal(stage.parentElement, null, "the stage is not in the DOM: nothing on screen shows it drawing");
  assert.deepEqual([stage.width, stage.height], [800, H(800)], "the stage is sized for the draw, width-fit to the root");
  assert.deepEqual([c1.width, c1.height], [0, 0], "the page's canvas has no bitmap and no size while the draw is in flight: a reader sees 'not drawn', never sized-and-empty");
  assert.deepEqual(opsOn(c1).filter((o) => o !== "width:0" && o !== "height:0"), [], "nothing was done to the page's canvas beyond its 0×0 shell");

  const from = ops.length;
  f.release(1);
  const h = await pending;
  assert.deepEqual(ops.slice(from).map((o) => (o.op === "drawImage" ? "drawImage" : o.op + ":" + o.value)),
    ["width:800", "height:" + H(800), "drawImage", "width:0", "height:0"],
    "when the draw lands: the page's canvas sized then filled, nothing between, and the stage zeroed after");
  assert.deepEqual(ops.slice(from, from + 3).map((o) => o.el), [c1, c1, c1], "the three steps are the page canvas's");
  assert.equal(ops[from + 2].src, stage, "filled from the stage pdf.js drew into");
  assert.deepEqual(ops.slice(from + 3).map((o) => o.el), [stage, stage], "the zeroing is the stage's: its store is released, not left for the collector");
  assert.deepEqual([c1.width, c1.height], [800, H(800)]);
  assert.equal(drawn.length, 1); assert.equal(drawn[0].canvas, c1 as unknown as HTMLCanvasElement); assert.equal(drawn[0].width, 800);
  h.dispose();
});

// ── a sharpening redraw ─────────────────────────────────────────────────────────────────────────

test("a sharpening redraw: the page's canvas keeps the old bitmap, untouched, while the redraw is in flight into a fresh stage; the new bitmap replaces it in one step when the draw lands", async () => {
  (globalThis as any).ResizeObserver = FakeRO;
  const f = fakeLib(1);
  const { container } = viewerTree(800);
  const drawn: PageInfo[] = [];
  const { pending } = await startHeld(f, container, { onPage: (p) => drawn.push(p) });
  f.release(1);
  const h = await pending;
  const c1 = canvasOf(pagesOf(container)[0])!;
  assert.deepEqual([c1.width, c1.height], [800, H(800)]);

  // the root narrows: the observer asks page 1 to redraw at 500
  container.layoutWidth = 500;
  const from = ops.length;
  FakeRO.instances[0].fire();
  await until(() => f.inFlight(1), "page 1's redraw to start");
  assert.equal(f.calls.targets.length, 2);
  const stage2 = f.calls.targets[1];
  assert.notEqual(stage2, c1); assert.notEqual(stage2, f.calls.targets[0], "a stage per draw");
  assert.deepEqual([stage2.width, stage2.height], [500, H(500)]);
  assert.deepEqual(opsOn(c1, from), [], "the page's canvas is untouched while the redraw is in flight");
  assert.deepEqual([c1.width, c1.height], [800, H(800)], "…so the old bitmap is what is on screen, CSS-scaled, not a blank");

  f.release(1);
  await until(() => drawn.length === 2, "page 1 redrawn");
  assert.deepEqual(opsOn(c1, from), ["width:500", "height:" + H(500), "drawImage"], "sized and filled together as the redraw lands");
  assert.equal(ops.slice(from).find((o) => o.op === "drawImage")!.src, stage2);
  assert.deepEqual([stage2.width, stage2.height], [0, 0], "the stage released");
  assert.equal(drawn[1].canvas, c1 as unknown as HTMLCanvasElement, "the same element: an overlay keyed on it holds");
  assert.equal(drawn[1].width, 500);
  h.dispose();
});

// ── cancellation ────────────────────────────────────────────────────────────────────────────────

test("a redraw cancelled by eviction: the page's canvas is zeroed by drop() and nothing is copied into it — no kept blank, no onPage, no failure — and the page draws again at the current width on return", async () => {
  (globalThis as any).IntersectionObserver = FakeIO;
  (globalThis as any).ResizeObserver = FakeRO;
  const f = fakeLib(2);
  const { container } = viewerTree(800);
  const drawn: PageInfo[] = []; const errors: PageError[] = [];
  const { pending } = await startHeld(f, container, { onPage: (p) => drawn.push(p), onPageError: (e) => errors.push(e) });
  f.release(1);
  const h = await pending;
  const wraps = pagesOf(container);
  const c1 = canvasOf(wraps[0])!;
  const io = FakeIO.instances[0];
  io.fire([[wraps[0], true], [wraps[1], false]]);

  container.layoutWidth = 500;
  FakeRO.instances[0].fire();
  await until(() => f.inFlight(1), "page 1's redraw to start");
  const stage2 = f.calls.targets[1];
  const from = ops.length;
  // page 1 leaves the margin mid-redraw
  io.fire([[wraps[0], false]]);
  assert.equal(f.calls.cancelled, 1, "the draw in flight is cancelled");
  assert.deepEqual([c1.width, c1.height], [0, 0], "drop() gave the bitmap back: no bitmap, and no size for a reader to mistake for one");
  await settle();
  assert.deepEqual(opsOn(c1, from), ["width:0", "height:0"], "drop()'s zeroing is the only thing done to the page's canvas: no copy from a cancelled draw");
  assert.deepEqual([stage2.width, stage2.height], [0, 0], "the cancelled draw's stage is released too");
  assert.equal(drawn.length, 1, "no onPage for a draw that did not land");
  assert.deepEqual(errors, [], "a cancelled draw is not a failed page");

  // on return: a fresh draw at the current width, into a fresh stage, landing as any draw does
  io.fire([[wraps[0], true]]);
  await until(() => f.inFlight(1), "page 1's draw on return");
  assert.equal(f.calls.targets.length, 3);
  f.release(1);
  await until(() => drawn.length === 2, "page 1 drawn on return");
  assert.deepEqual([c1.width, c1.height], [500, H(500)]);
  assert.equal(drawn[1].width, 500);
  h.dispose();
});

test("a cancellation arriving after pdf.js finished: the task resolves all the same, but a page no longer in the margin takes no bitmap — the canvas stays 0×0, no onPage — and it draws again on return", async () => {
  (globalThis as any).IntersectionObserver = FakeIO;
  const f = fakeLib(2);
  const { container } = viewerTree(800);
  const drawn: PageInfo[] = []; const errors: PageError[] = [];
  const { pending } = await startHeld(f, container, { onPage: (p) => drawn.push(p), onPageError: (e) => errors.push(e) });
  f.release(1);
  const h = await pending;
  const wraps = pagesOf(container);
  const c2 = canvasOf(wraps[1])!;
  const io = FakeIO.instances[0];
  io.fire([[wraps[1], true]]);
  await until(() => f.inFlight(2), "page 2's draw to start");
  const from = ops.length;
  // the draw finishes and, in the same turn, the observer reports the page gone: drop() cancels a task already complete
  f.release(2);
  io.fire([[wraps[1], false]]);
  assert.equal(f.calls.cancelled, 1);
  await settle();
  assert.deepEqual(opsOn(c2, from), [], "no size, no copy: the finished bitmap is not put on a page beyond the margin");
  assert.deepEqual([c2.width, c2.height], [0, 0]);
  assert.deepEqual(drawn.map((p) => p.index), [1], "no onPage for page 2");
  assert.deepEqual(errors, []);
  assert.deepEqual([f.calls.targets[1].width, f.calls.targets[1].height], [0, 0], "its stage released");

  io.fire([[wraps[1], true]]);
  await until(() => f.inFlight(2), "page 2's draw on return — drawnAt stayed 0, so it is asked again");
  f.release(2);
  await until(() => drawn.length === 2, "page 2 drawn");
  assert.deepEqual([c2.width, c2.height], [800, H(800)]);
  assert.deepEqual(opsOn(c2, from), ["width:800", "height:" + H(800), "drawImage"]);
  h.dispose();
});

// ── a canvas with no 2d context ─────────────────────────────────────────────────────────────────

test("a page whose canvas gives no 2d context fails loudly in place — the notice names the reason, onPageError fires, the canvas goes — rather than keeping a sized, empty canvas", async () => {
  (globalThis as any).IntersectionObserver = FakeIO;
  const f = fakeLib(2);
  const { container } = viewerTree(800);
  const drawn: PageInfo[] = []; const errors: PageError[] = [];
  const { pending } = await startHeld(f, container, { onPage: (p) => drawn.push(p), onPageError: (e) => errors.push(e) });
  f.release(1);
  const h = await pending;
  const wraps = pagesOf(container);
  const c2 = canvasOf(wraps[1])!;
  c2.contextless = true;
  FakeIO.instances[0].fire([[wraps[1], true]]);
  await until(() => f.inFlight(2), "page 2's draw to start");
  f.release(2);
  await until(() => errors.length === 1, "page 2's failure");
  assert.equal(errors[0].index, 2);
  assert.match(errors[0].message, /no 2d context/);
  assert.equal(canvasOf(wraps[1]), null, "the canvas is gone: a page with no bitmap must not take a region comment");
  assert.equal(wraps[1].children.length, 1);
  assert.equal(wraps[1].children[0].className, "fileview-err fileview-pdf-page-err");
  assert.match(wraps[1].children[0].textContent, /^Page 2 did not render — .*no 2d context/);
  assert.deepEqual(drawn.map((p) => p.index), [1]);
  h.dispose();
});

// ── the source: the shape, and the header's statement of the boundary ───────────────────────────

test("at source: the render target is the stage, the page's canvas is sized and filled with no await between, a page gone by the time the draw lands takes no bitmap, and the stage is released in the finally", () => {
  const code = CHUNK.split("\n").filter((l) => !l.trim().startsWith("//")).join("\n");
  assert.match(code, /const stage = document\.createElement\("canvas"\);/);
  assert.match(code, /proxy\.render\(\{ canvas: stage, viewport: vp, transform: dpr === 1 \? undefined : \[dpr, 0, 0, dpr, 0, 0\] \}\)/, "pdf.js draws into the stage");
  assert.doesNotMatch(code, /render\(\{ canvas: p\.canvas/, "never into the page's canvas, which pdf.js would blank");
  assert.match(code, /await task\.promise;\n\s*if \(disposed \|\| !p\.visible\) return;/, "a page evicted as the draw landed takes no bitmap");
  const swap = /p\.canvas\.width = stage\.width;[^\n]*\n\s*p\.canvas\.height = stage\.height;[^\n]*\n\s*const ctx = p\.canvas\.getContext\("2d", \{ alpha: false, willReadFrequently: true \}\);\n\s*if \(!ctx\) throw new Error\([^)]*\);\n\s*ctx\.drawImage\(drawn\.canvas, 0, 0\);/.exec(code);
  assert.ok(swap, "sized (width, height), then filled, in adjacent statements — the context with the attributes pdf.js gave the canvas when it drew into it");
  assert.doesNotMatch(swap![0], /await/, "nothing yields between the sizing and the fill");
  assert.match(code, /\} finally \{\n\s*if \(p\.task === task\) p\.task = null;\n\s*stage\.width = 0; stage\.height = 0;/, "the stage is released on every path");
  assert.doesNotMatch(code, /setTimeout|setInterval/, "no timer anywhere in the chunk");
});

test("the header states the trust boundary in the terms the plan's Docs section promises: untrusted input parsed on the dashboard's origin, pixels the only sink, the properties held under Security posture, an upgrade re-verifying them", () => {
  const header: string[] = [];
  for (const l of CHUNK.split("\n")) { if (l.startsWith("//") || l.trim() === "") header.push(l); else break; }
  const h = header.join("\n").replace(/\n\/\/ ?/g, " ");
  assert.match(h, /THE BOUNDARY:/, "a paragraph of its own, findable by a session about to touch pdf.js");
  assert.match(h, /a PDF is untrusted input/);
  assert.match(h, /on the dashboard's authenticated origin/);
  assert.match(h, /Pixels are the only sink/);
  assert.match(h, /never pdfjs-dist\/web/);
  assert.match(h, /getDocument is handed bytes,\s+never a URL/);
  assert.match(h, /no eval path/);
  assert.match(h, /"Security posture" in plans\/file-review\.md/, "where the properties live");
  assert.match(h, /ui\/webview\/file-review-posture\.test\.ts/, "and what holds them to the code");
  assert.match(h, /Upgrading pdfjs-dist re-verifies the no-eval property/);
  assert.match(h, /widens the sink list and is stated there first/);
});

// ── in Chromium: the built chunk over real pdf.js, sampled frame by frame through a redraw ───────

const req = createRequire(path.join(PKG, "package.json"));   // runtime requires: esbuild must not bundle playwright
let chromium: any = null;
let SKIP: string | false = false;
try {
  chromium = req("playwright").chromium;
  const exe: string = chromium.executablePath();
  if (!exe || !fs.existsSync(exe)) SKIP = "playwright's chromium is not installed here (`npx playwright install chromium` in vscode-extension); the staged-draw browser test did not run";
} catch {
  SKIP = "playwright is not installed under vscode-extension/node_modules (run `npm ci` there); the staged-draw browser test did not run";
}

/** A PDF of US-letter pages with a correct xref, each page an optional content stream. */
function syntheticPdf(contents: Array<string | null>): Buffer {
  const objs = ["<< /Type /Catalog /Pages 2 0 R >>"];
  const pageIds: number[] = []; const bodies: Array<{ contentId: number | null; content: string | null }> = [];
  let next = 3;
  for (const c of contents) { pageIds.push(next++); const contentId = c ? next++ : null; bodies.push({ contentId, content: c }); }
  objs.push(`<< /Type /Pages /Kids [${pageIds.map((i) => i + " 0 R").join(" ")}] /Count ${pageIds.length} >>`);
  for (const { contentId, content } of bodies) {
    objs.push(`<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]${contentId ? ` /Contents ${contentId} 0 R` : ""} >>`);
    if (contentId) objs.push(`<< /Length ${Buffer.byteLength(content!, "latin1")} >>\nstream\n${content}\nendstream`);
  }
  let out = "%PDF-1.4\n";
  const offsets: number[] = [];
  objs.forEach((body, i) => { offsets.push(Buffer.byteLength(out, "latin1")); out += `${i + 1} 0 obj\n${body}\nendobj\n`; });
  const xref = Buffer.byteLength(out, "latin1");
  out += `xref\n0 ${objs.length + 1}\n0000000000 65535 f \n`;
  for (const o of offsets) out += `${String(o).padStart(10, "0")} 00000 n \n`;
  out += `trailer\n<< /Size ${objs.length + 1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`;
  return Buffer.from(out, "latin1");
}
/** A page that takes a while to draw — `n` tiny black rectangles scattered over it — with a red square at its centre,
 *  drawn last so the centre pixel is red whatever the rectangles cover. */
function heavyRedCentre(n: number): string {
  const parts = ["0 0 0 rg"];
  for (let i = 0; i < n; i++) parts.push(`${(i * 37) % 600} ${(i * 91) % 780} 2 2 re f`);
  parts.push("1 0 0 rg 206 296 200 200 re f");
  return parts.join("\n");
}
const HEAVY_RECTS = 150000;
const RED = "255,0,0,255";

/** The viewer's own rules for the elements the chunk lives in, from the sheet the viewer loads. */
function viewerRules(): string {
  const css = fs.readFileSync(path.join(UI, "styles.css"), "utf8");
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

// the viewer's shape: .fileview (clips) > .fileview-body (scrolls; sized as a pane would size it) > the host. Four
// pages, so page 1 can be scrolled beyond the body's one-height margin; page 1 is the heavy one
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

interface Frame { t: number; w: number; h: number; px: string | null }
interface Drawn { index: number; width: number; t: number }

test("in Chromium: through a sharpening redraw of a heavy page every sampled frame shows the old bitmap or the new, never a sized canvas with a blank centre; an eviction mid-redraw leaves the canvas 0×0 with no onPage; the page redraws on return", { skip: SKIP }, async (t) => {
  const chunkJs = bundle(path.join(UI, "pdf-chunk.ts"));
  const workerJs = bundle(path.join(PKG, "node_modules", "pdfjs-dist", "build", "pdf.worker.mjs"));
  const html = HTML(viewerRules());
  const pdf = syntheticPdf([heavyRedCentre(HEAVY_RECTS), null, null, null]);
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage({ viewport: { width: 900, height: 900 } });
    const errors: string[] = [];
    page.on("pageerror", (e: Error) => errors.push("pageerror: " + e.message));
    await page.route("http://TESTHOST/**", (route: any) => {
      const u = new URL(route.request().url());
      const js = (b: string) => route.fulfill({ status: 200, contentType: "application/javascript", body: b });
      if (u.pathname === "/view.html") return route.fulfill({ contentType: "text/html", body: html });
      if (u.pathname === "/doc.pdf") return route.fulfill({ contentType: "application/pdf", body: pdf });
      if (u.pathname === "/dist/pdf-chunk.js") return js(chunkJs);
      if (u.pathname === "/dist/pdf-worker.js") return js(workerJs);
      return route.fulfill({ status: 404, body: "" });
    });
    await page.goto("http://TESTHOST/view.html");
    await page.waitForFunction(() => !!(window as any).__rompPdf, null, { timeout: 10000 });

    // armed BEFORE render(): a frame sampler reading page 1's canvas — its backing size and its centre pixel — every
    // animation frame, and a log of every onPage with its time
    const info = await page.evaluate(async () => {
      const w = window as any;
      const frames: Frame[] = []; const drawn: Drawn[] = [];
      w.__frames = frames; w.__drawn = drawn;
      const centre = (c: HTMLCanvasElement): string | null => {
        if (!c.width || !c.height) return null;
        const d = c.getContext("2d")!.getImageData(Math.floor(c.width / 2), Math.floor(c.height / 2), 1, 1).data;
        return Array.from(d).join(",");
      };
      const tick = () => {
        const c = document.querySelector('canvas.fileview-pdf-canvas[data-page="1"]') as HTMLCanvasElement | null;
        if (c && frames.length < 20000) frames.push({ t: performance.now(), w: c.width, h: c.height, px: centre(c) });
        if (!w.__stop) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
      const bytes = await (await fetch("/doc.pdf")).arrayBuffer();
      const h = await w.__rompPdf.render(bytes, document.getElementById("host"), {
        onPage: (p: { index: number; width: number }) => drawn.push({ index: p.index, width: p.width, t: performance.now() }),
      });
      w.__h = h;
      return { pages: h.pages as number, dpr: window.devicePixelRatio, rootWidth: (document.querySelector(".fileview-pdf") as HTMLElement).clientWidth };
    });
    assert.equal(info.pages, 4);
    const state = (): Promise<{ frames: Frame[]; drawn: Drawn[]; canvasW: number[] }> => page.evaluate(() => {
      const w = window as any;
      return { frames: w.__frames as Frame[], drawn: w.__drawn as Drawn[], canvasW: Array.from(document.querySelectorAll("canvas.fileview-pdf-canvas")).map((c) => (c as HTMLCanvasElement).width) };
    });
    const drawnOf = (s: { drawn: Drawn[] }, i: number) => s.drawn.filter((d) => d.index === i);
    const now = () => page.evaluate(() => performance.now()) as Promise<number>;
    const setWidth = (px: number) => page.evaluate((px: number) => { document.getElementById("body")!.style.width = px + "px"; }, px);

    // ── page 1 drawn once, red at the centre; before that draw landed its canvas was 0×0 in every frame (never sized and empty)
    let s = await state();
    const wide = Math.round(info.rootWidth * info.dpr);
    assert.equal(drawnOf(s, 1).length, 1);
    assert.deepEqual([s.canvasW[0] > 0, s.canvasW[0]], [true, wide], "page 1's backing store is the root's width at the display's ratio");
    const first = drawnOf(s, 1)[0].t;
    const before = s.frames.filter((f) => f.t < first);
    for (const f of before) assert.deepEqual([f.w, f.h], [0, 0], `before the first draw landed the canvas was 0×0, not sized and empty (frame at ${Math.round(f.t)} ms: ${f.w}×${f.h})`);
    const after = s.frames.filter((f) => f.t >= first);
    for (const f of after) assert.equal(f.px, RED, `after the draw landed the centre is red (frame at ${Math.round(f.t)} ms: ${f.w}×${f.h} ${f.px})`);

    // ── the body narrows: page 1 redraws. Every frame between the change and the landing is the OLD bitmap (its
    // width, red centre); every frame after is the new. No frame is a sized canvas with a blank centre.
    const t0 = await now();
    await setWidth(NARROW);
    await page.waitForFunction(() => ((window as any).__drawn as Drawn[]).filter((d) => d.index === 1).length >= 2, null, { timeout: 60000 });
    s = await state();
    const second = drawnOf(s, 1)[1];
    const narrow = s.canvasW[0];
    assert.ok(narrow > 0 && narrow < wide, `the backing store narrowed (${wide} → ${narrow})`);
    const during = s.frames.filter((f) => f.t >= t0 && f.t < second.t);
    assert.ok(during.length >= 2, `frames were sampled while the redraw was in flight (${HEAVY_RECTS} rectangles; the redraw took ${Math.round(second.t - t0)} ms) — got ${during.length}`);
    t.diagnostic(`the redraw of the heavy page took ${Math.round(second.t - t0)} ms from the width change; ${during.length} frames sampled in flight`);
    for (const f of during) assert.deepEqual([f.w, f.px], [wide, RED], `while the redraw was in flight the old bitmap stayed (frame at ${Math.round(f.t - t0)} ms after the change: ${f.w}×${f.h} ${f.px})`);
    const landed = s.frames.filter((f) => f.t >= second.t);
    for (const f of landed) assert.deepEqual([f.w, f.px], [narrow, RED], `once landed, the new bitmap (frame: ${f.w}×${f.h} ${f.px})`);
    assert.deepEqual(errors, [], errors.join("\n"));

    // ── the body widens again and, a frame later — the redraw in flight on the heavy page — page 1 is scrolled beyond
    // the margin: the draw is cancelled, the canvas is 0×0, no onPage; no frame showed a sized, blank canvas
    const t1 = await now();
    await setWidth(WIDE);
    await page.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r))));
    const mid = await state();
    assert.equal(drawnOf(mid, 1).length, 2, "the redraw has not landed yet: a heavy page takes longer than two frames");
    await page.evaluate(() => { document.getElementById("body")!.scrollTop = 2400; });
    await page.waitForFunction(() => (document.querySelector('canvas.fileview-pdf-canvas[data-page="1"]') as HTMLCanvasElement).width === 0, null, { timeout: 20000 });
    await page.waitForTimeout(Math.max(300, Math.round(2 * (second.t - t0))));   // room for the cancelled draw to have landed, if it were going to
    s = await state();
    assert.equal(drawnOf(s, 1).length, 2, "no onPage from the cancelled redraw");
    assert.equal(s.canvasW[0], 0, "page 1 beyond the margin holds no bitmap");
    for (const f of s.frames.filter((f) => f.t >= t1)) {
      assert.ok((f.w === 0 && f.h === 0) || (f.w === narrow && f.px === RED), `after the widening: the old bitmap or nothing, never a sized blank (frame at ${Math.round(f.t - t1)} ms: ${f.w}×${f.h} ${f.px})`);
    }

    // ── back to the top: page 1 draws again at the wide width, its centre red once more
    await page.evaluate(() => { document.getElementById("body")!.scrollTop = 0; });
    await page.waitForFunction(() => ((window as any).__drawn as Drawn[]).filter((d) => d.index === 1).length >= 3, null, { timeout: 60000 });
    s = await state();
    assert.equal(s.canvasW[0], wide);
    const last = s.frames[s.frames.length - 1];
    assert.deepEqual([last.w, last.px], [wide, RED]);
    for (const f of s.frames) assert.ok(f.w === 0 || f.px === RED, `no frame anywhere in the run was a sized canvas with a blank centre (frame at ${Math.round(f.t)} ms: ${f.w}×${f.h} ${f.px})`);
    await page.evaluate(() => { (window as any).__stop = true; (window as any).__h.dispose(); });
    assert.deepEqual(errors, [], errors.join("\n"));
  } finally {
    await browser.close();
  }
});

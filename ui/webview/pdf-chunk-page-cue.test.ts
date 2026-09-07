// The PDF chunk's PER-PAGE WAIT CUE (plans/file-review.md, Slice 4; the review of 2026-09-06). A page shell is a
// white sheet holding a 0×0 canvas until its bitmap is drawn, and the pump draws one page at a time — so a heavy
// page scrolled into view (or jumped to: a reload with the panel open, a card's Reveal) sat as a white sheet with
// no cue for as long as it took, indistinguishable from an empty page or a quiet failure, and a page on screen
// waited behind pages off it with no cue at all. The viewer's own loader covers only the wait for page 1
// (file-view.ts removes it once render() resolves). ui/CLAUDE.md's loading-state rule: the romp loader, never a
// blank. Now: from the moment a draw is asked for a page with no bitmap (want: queued or in flight) until the one
// event that ends the wait — the bitmap landing, the page failing, the page leaving the margin — the wrapper
// carries div.fileview-load.fileview-pdf-page-load, the viewer's own loader markup over the sheet.
//
// Two legs. NODE: makeRender over a stand-in pdf.js whose draws the test releases by hand (so "in flight" and
// "queued behind" are states the test holds still and inspects), a fake DOM, the observer fired by hand — the cue's
// life on every path: the first page's draw, pages entering the margin together, eviction while drawn, while queued
// and while in flight, a sharpening redraw (no cue: the bitmap is on screen), a failed page (no cue: the notice
// stands alone), no observer (eager draws), the host-injected media base, and parity with file-view.ts's loader
// markup read from its source. CHROMIUM (skips by name without playwright's chromium; CI installs none): the built
// chunk under the viewer's own rules, a MutationObserver logging every cue added and removed per wrapper (exact,
// whatever the timing) and a frame sampler measuring the cue over its sheet while a deliberately heavy page draws.
//
// Fixtures are synthetic: hand-built PDFs of blank pages, one filled with tens of thousands of tiny rectangles to
// make its draw take long enough to watch; TESTHOST; no recorded document.
import { test, beforeEach } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { makeRender, type PdfLib, type PageInfo, type PageError } from "./pdf-chunk";

const PKG = process.cwd();                                   // vscode-extension, where npm test runs
const ROOT = path.resolve(PKG, "..");
const UI = path.join(ROOT, "ui", "webview");
const read = (f: string) => fs.readFileSync(path.join(UI, f), "utf8");
const CHUNK = read("pdf-chunk.ts");
const VIEW = read("file-view.ts");
const CUE = ".fileview-pdf-page-load";

// ── a fake DOM: what the chunk touches of an element, and nothing else ──────────────────────────

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
  width = 300; height = 150;                 // a canvas's element default, which the chunk must not leave in place
  /** A canvas's 2D context, as the chunk's staged draw uses one: the stage's, whose `.canvas` it copies from, and the
   *  page's, which it copies into. Nothing here has pixels — the stand-in pdf.js draws none — so the copy is a no-op. */
  getContext(kind: string): { canvas: FakeEl; drawImage(): void } | null {
    return kind === "2d" && this.tagName === "CANVAS" ? { canvas: this, drawImage: () => {} } : null;
  }
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
}
const el = (tag: string) => new FakeEl(tag);
const asEl = (e: FakeEl) => e as unknown as HTMLElement;

/** The viewer's tree around the chunk's container: .fileview { overflow: hidden } > .fileview-body { overflow:
 *  auto } > .fileview-pdfhost (the container), the host laid out 800 wide. */
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

// ── a fake pdf.js whose draws the test holds and releases: "in flight" and "queued" stand still ──

interface FakeLib {
  lib: PdfLib;
  calls: { getPage: number[]; renders: number[]; destroyed: number; cancelled: number };
  /** whether page i's draw is in flight (started, not yet released) */
  inFlight: (i: number) => boolean;
  /** finish page i's draw */
  release: (i: number) => void;
}
function fakeLib(spec: { pages: number; fail?: number[]; message?: string }): FakeLib {
  const calls = { getPage: [] as number[], renders: [] as number[], destroyed: 0, cancelled: 0 };
  const gates = new Map<number, () => void>();
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
                gates.set(i, res);
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

// ── observers the test fires by hand ────────────────────────────────────────────────────────────

class FakeIO {
  static instances: FakeIO[] = [];
  targets: FakeEl[] = [];
  disconnected = false;
  constructor(public cb: (entries: unknown[], io: FakeIO) => void, public opts: { root?: unknown; rootMargin?: string }) { FakeIO.instances.push(this); }
  observe(t: FakeEl): void { this.targets.push(t); }
  disconnect(): void { this.disconnected = true; }
  fire(states: Array<[FakeEl, boolean]>): void { this.cb(states.map(([target, isIntersecting]) => ({ target, isIntersecting })), this); }
}
class FakeRO {
  static instances: FakeRO[] = [];
  constructor(public cb: () => void) { FakeRO.instances.push(this); }
  observe(): void {}
  disconnect(): void {}
  fire(): void { this.cb(); }
}

/** Wait for a condition the pump reaches on its own ticks; fails loudly rather than hanging. */
async function until(cond: () => boolean, what: string): Promise<void> {
  for (let i = 0; i < 2000; i++) { if (cond()) return; await new Promise((r) => setTimeout(r, 1)); }
  assert.fail("timed out waiting for " + what);
}
const bytes = () => new ArrayBuffer(16);
const canvasOf = (wrap: FakeEl) => wrap.querySelector("canvas.fileview-pdf-canvas");
const cueOf = (wrap: FakeEl) => wrap.querySelector(CUE);
const pagesOf = (container: FakeEl) => container.children[0].children;
/** The wrappers carrying a cue, by page number — the shape every step below asserts on. */
const cued = (container: FakeEl) => pagesOf(container).filter((w) => cueOf(w)).map((w) => Number(w.dataset.page));

beforeEach(() => {
  (globalThis as any).document = { createElement: el };
  (globalThis as any).getComputedStyle = styleOf;
  delete (globalThis as any).IntersectionObserver;
  delete (globalThis as any).ResizeObserver;
  delete (globalThis as any).window;
  FakeIO.instances.length = 0;
  FakeRO.instances.length = 0;
});

/** Start a render whose first page's draw is held; resolves once that draw is in flight, carrying the render's own
 *  promise in an object (an async function returning it bare would adopt it, and the test would wait on the very
 *  draw it means to release). */
async function startHeld(f: FakeLib, container: FakeEl, opts: { onPage?: (p: PageInfo) => void; onPageError?: (e: PageError) => void } = {}): Promise<{ pending: Promise<{ pages: number; dispose(): void }> }> {
  const pending = makeRender(f.lib)(bytes(), asEl(container), opts);
  pending.catch(() => {});                                  // a test that expects the rejection awaits it itself
  await until(() => f.inFlight(1), "page 1's draw to start");
  return { pending };
}

/** The cue as the viewer's loader: its classes, its placement over the sheet, and the markup file-view.ts puts up. */
function assertLoader(wrap: FakeEl): FakeEl {
  const load = cueOf(wrap);
  assert.ok(load, "page " + wrap.dataset.page + " carries the cue");
  assert.deepEqual(load!.className.split(" "), ["fileview-load", "fileview-pdf-page-load"],
    "the viewer's loader class (both sheets style it) plus the page hook, as the notice has .fileview-pdf-page-err");
  assert.equal(load!.style.position, "absolute"); assert.equal(load!.style.inset, "0");
  assert.equal(load!.style.pointerEvents, "none", "the panel's overlay under it still takes the pointer");
  assert.deepEqual(load!.children.map((c) => c.tagName), ["IMG", "SPAN", "I", "I", "I"], "swirl, wordmark, three dots");
  const [img, word, ...dots] = load!.children;
  assert.equal(img.src, "/media/romp-swirl-glyph.svg"); assert.equal(img.alt, "");
  assert.equal(word.textContent, "romp");
  for (const d of dots) assert.equal(d.className, "fileview-dot");
  assert.equal(wrap.children[0].tagName, "CANVAS", "the canvas stays the wrapper's first child; the cue sits over it");
  return load!;
}

// ── the cue's life, held still at each state ────────────────────────────────────────────────────

test("a page's sheet carries the romp loader from the moment its draw is asked — page 1's first draw, pages entering the margin together, queued behind the pump or in flight — until its bitmap lands; no page beyond the margin has one", async () => {
  (globalThis as any).IntersectionObserver = FakeIO;
  const f = fakeLib({ pages: 6 });
  const { container } = viewerTree();
  const drawn: number[] = [];
  const seenAtDraw: Array<{ index: number; cue: boolean }> = [];
  const { pending } = await startHeld(f, container, { onPage: (p) => { drawn.push(p.index); seenAtDraw.push({ index: p.index, cue: !!cueOf(pagesOf(container)[p.index - 1]) }); } });
  // page 1's draw is in flight and render() has not resolved: its sheet already carries the loader; the others, unasked, do not
  const wraps = pagesOf(container);
  assert.equal(wraps.length, 6);
  assert.deepEqual(cued(container), [1], "page 1 alone: the only draw asked so far");
  assertLoader(wraps[0]);
  f.release(1);
  const h = await pending;
  assert.equal(h.pages, 6);
  assert.deepEqual(drawn, [1]);
  assert.deepEqual(cued(container), [], "page 1's bitmap is in: the loader gave way; pages 2–6 are shells with nothing pending");
  assert.deepEqual(wraps.map((w) => w.children.length), [1, 1, 1, 1, 1, 1], "each wrapper holds its canvas alone until a draw is asked");

  // pages 2, 3 and 4 enter the margin at once: all three are cued in the same tick — page 2 goes in flight, 3 and 4 wait
  // behind it in the pump, and a page waiting behind others is exactly the page that had no cue before
  const io = FakeIO.instances[0];
  io.fire([[wraps[1], true], [wraps[2], true], [wraps[3], true], [wraps[4], false], [wraps[5], false]]);
  assert.deepEqual(cued(container), [2, 3, 4], "cued synchronously with the observer's entry, before any draw starts or lands");
  for (const w of wraps.slice(1, 4)) assertLoader(w);
  await until(() => f.inFlight(2), "page 2's draw to start");
  assert.deepEqual(f.calls.renders, [1, 2], "one draw at a time: 3 and 4 are queued, not drawing — and cued all the same");
  assert.deepEqual(cued(container), [2, 3, 4]);

  f.release(2);
  await until(() => drawn.includes(2), "page 2's draw");
  assert.deepEqual(cued(container), [3, 4], "page 2's loader went with its bitmap landing; the queued pages keep theirs");
  assert.ok(canvasOf(wraps[1])!.width > 0);
  await until(() => f.inFlight(3), "page 3's draw to start");
  f.release(3);
  await until(() => f.inFlight(4), "page 4's draw to start");
  assert.deepEqual(cued(container), [4]);
  f.release(4);
  await until(() => drawn.includes(4), "page 4's draw");
  assert.deepEqual(cued(container), [], "every asked draw landed: no loader anywhere");
  assert.deepEqual(seenAtDraw, [1, 2, 3, 4].map((index) => ({ index, cue: false })), "onPage fires AFTER the loader is gone: the caller sees pixels, not the cue");
  assert.deepEqual(wraps.map((w) => w.children.length), [1, 1, 1, 1, 1, 1], "canvas alone again in every wrapper");
  h.dispose();
});

test("eviction: a drawn page leaving the margin has no cue (nothing is pending) and is cued again on return until the redraw lands; a page evicted while queued loses its cue at once and never draws; a page evicted mid-draw loses its cue with the cancelled draw", async () => {
  (globalThis as any).IntersectionObserver = FakeIO;
  const f = fakeLib({ pages: 6 });
  const { container } = viewerTree();
  const drawn: number[] = [];
  const { pending } = await startHeld(f, container, { onPage: (p) => drawn.push(p.index) });
  f.release(1);
  const h = await pending;
  const io = FakeIO.instances[0];
  const wraps = pagesOf(container);
  io.fire([[wraps[1], true]]);
  await until(() => f.inFlight(2), "page 2's draw"); f.release(2);
  await until(() => drawn.includes(2), "page 2 drawn");

  // drawn page 2 leaves: bitmap released, no cue — an evicted page is not waiting for anything
  io.fire([[wraps[1], false]]);
  assert.equal(canvasOf(wraps[1])!.width, 0, "evicted");
  assert.deepEqual(cued(container), []);
  // …and comes back: no bitmap, a draw asked → cued, until the redraw lands
  io.fire([[wraps[1], true]]);
  assert.deepEqual(cued(container), [2], "on return the sheet waits again, and says so");
  await until(() => f.inFlight(2), "page 2's redraw"); f.release(2);
  await until(() => drawn.filter((i) => i === 2).length === 2, "page 2 redrawn");
  assert.deepEqual(cued(container), []);

  // pages 5 and 6 enter; 5 goes in flight, 6 is queued behind it and cued; 6 leaves before its turn: cue gone at once, no draw
  io.fire([[wraps[4], true], [wraps[5], true]]);
  assert.deepEqual(cued(container), [5, 6]);
  await until(() => f.inFlight(5), "page 5's draw");
  io.fire([[wraps[5], false]]);
  assert.deepEqual(cued(container), [5], "the queued page's cue went the moment it left the margin");
  f.release(5);
  await until(() => drawn.includes(5), "page 5 drawn");
  await new Promise((r) => setTimeout(r, 10));
  assert.ok(!f.calls.renders.includes(6), "page 6, gone before its turn, was never drawn");
  assert.deepEqual(cued(container), []);
  assert.equal(wraps[5].children.length, 1, "its wrapper holds its canvas alone");

  // page 3 enters and goes in flight, then leaves mid-draw: the draw is cancelled, the cue goes with it
  io.fire([[wraps[2], true]]);
  await until(() => f.inFlight(3), "page 3's draw");
  assert.deepEqual(cued(container), [3]);
  const cancelled = f.calls.cancelled;
  io.fire([[wraps[2], false]]);
  assert.equal(f.calls.cancelled, cancelled + 1, "the draw in flight is cancelled");
  assert.deepEqual(cued(container), [], "no cue on a page whose draw was cancelled by its own eviction");
  assert.equal(canvasOf(wraps[2])!.width, 0);
  await new Promise((r) => setTimeout(r, 10));
  assert.deepEqual(cued(container), [], "…and the cancellation did not bring one back");
  assert.ok(!drawn.includes(3));
  h.dispose();
});

test("a sharpening redraw shows no cue: the page's scaled bitmap is on screen the whole time", async () => {
  (globalThis as any).IntersectionObserver = FakeIO;
  (globalThis as any).ResizeObserver = FakeRO;
  const f = fakeLib({ pages: 2 });
  const { container } = viewerTree();
  container.layoutWidth = 800;
  const drawn: PageInfo[] = [];
  const { pending } = await startHeld(f, container, { onPage: (p) => drawn.push(p) });
  f.release(1);
  const h = await pending;
  const wraps = pagesOf(container);
  assert.equal(drawn[0].width, 800, "drawn width-fit to the root");
  // the root narrows: the observer asks page 1 (visible, drawn for 800) to redraw at 500
  container.layoutWidth = 500;
  FakeRO.instances[0].fire();
  await until(() => f.inFlight(1), "page 1's redraw to start");
  assert.deepEqual(cued(container), [], "in flight at the new width, but no cue: the old bitmap, CSS-scaled, is showing");
  assert.ok(canvasOf(wraps[0])!.width > 0);
  f.release(1);
  await until(() => drawn.length === 2, "page 1 redrawn");
  assert.equal(drawn[1].width, 500);
  assert.deepEqual(cued(container), []);
  h.dispose();
});

test("a page pdf.js refuses: cued while asked, then the notice takes the loader's place — the wrapper holds the notice alone — and a scroll away and back brings no cue, since nothing will ever end that wait", async () => {
  (globalThis as any).IntersectionObserver = FakeIO;
  const f = fakeLib({ pages: 3, fail: [2] });
  const { container } = viewerTree();
  const errors: PageError[] = [];
  const warn = console.warn;
  console.warn = () => {};
  try {
    const { pending } = await startHeld(f, container, { onPageError: (e) => errors.push(e) });
    f.release(1);
    const h = await pending;
    const io = FakeIO.instances[0];
    const wraps = pagesOf(container);
    io.fire([[wraps[1], true]]);
    assert.deepEqual(cued(container), [2], "asked, so cued — the chunk cannot know yet that pdf.js will refuse");
    await until(() => errors.length === 1, "page 2's failure");
    assert.deepEqual(cued(container), [], "the notice replaced the loader");
    assert.equal(wraps[1].children.length, 1, "one notice and nothing else — no canvas, no loader");
    assert.ok(wraps[1].children[0].className.split(" ").includes("fileview-pdf-page-err"));
    io.fire([[wraps[1], false]]); io.fire([[wraps[1], true]]);
    assert.deepEqual(cued(container), [], "a failed page is never cued again: no draw will come");
    assert.equal(wraps[1].children.length, 1);
    h.dispose();
  } finally { console.warn = warn; }
});

test("without an observer every page is asked eagerly behind page 1 — so every undrawn page is cued the instant render() resolves, and each loses its cue as its own draw lands", async () => {
  const f = fakeLib({ pages: 3 });
  const { container } = viewerTree();
  const drawn: number[] = [];
  const { pending } = await startHeld(f, container, { onPage: (p) => drawn.push(p.index) });
  f.release(1);
  const h = await pending;
  assert.deepEqual(cued(container), [2, 3], "page 2 in flight, page 3 queued: both waiting, both say so");
  await until(() => f.inFlight(2), "page 2's draw"); f.release(2);
  await until(() => drawn.includes(2), "page 2 drawn");
  assert.deepEqual(cued(container), [3]);
  await until(() => f.inFlight(3), "page 3's draw"); f.release(3);
  await until(() => drawn.includes(3), "page 3 drawn");
  assert.deepEqual(cued(container), []);
  h.dispose();
});

test("dispose during a cued draw takes the root, cue and all, and marks nothing failed", async () => {
  const f = fakeLib({ pages: 2 });
  const { container } = viewerTree();
  const errors: PageError[] = [];
  const { pending } = await startHeld(f, container, { onPageError: (e) => errors.push(e) });
  f.release(1);
  const h = await pending;
  await until(() => f.inFlight(2), "page 2's draw");
  assert.deepEqual(cued(container), [2]);
  h.dispose();
  assert.equal(container.children.length, 0, "the root and its cue left the container");
  await new Promise((r) => setTimeout(r, 10));
  assert.deepEqual(errors, [], "a cancelled draw is not a failed page");
});

test("the cue's swirl resolves through the media base the host injects (window.__rompMediaBase), as every asset URL does — the VS Code webview has no /media route", async () => {
  (globalThis as any).window = { __rompMediaBase: "https://file+.vscode-resource.vscode-cdn.net/ext/media" };
  const f = fakeLib({ pages: 1 });
  const { container } = viewerTree();
  const { pending } = await startHeld(f, container);
  const load = cueOf(pagesOf(container)[0])!;
  assert.equal(load.children[0].src, "https://file+.vscode-resource.vscode-cdn.net/ext/media/romp-swirl-glyph.svg");
  f.release(1);
  (await pending).dispose();
  assert.match(CHUNK, /^import \{ mediaSrc \} from "\.\/media";/m, "through media.ts, not a literal path");
  assert.match(CHUNK, /swirl\.src = mediaSrc\("romp-swirl-glyph\.svg"\);/);
});

// ── parity with the viewer's loader, and the sheets that style it ───────────────────────────────

test("the cue is the viewer's own loader: the markup file-view.ts puts up for the body, on classes BOTH sheets style", () => {
  // file-view's loader literal — swirl, wordmark, three dots — is what the chunk builds element by element
  const lit = VIEW.match(/wait\.innerHTML = '(<img src="\/media\/romp-swirl-glyph\.svg" alt=""><span>romp<\/span>)'\s*\n\s*\+ '((?:<i class="fileview-dot"><\/i>){3})';/);
  assert.ok(lit, "file-view.ts's pages loader literal moved — re-anchor, and check the chunk's cue still mirrors it");
  assert.match(CHUNK, /load\.className = "fileview-load fileview-pdf-page-load";/);
  assert.match(CHUNK, /const swirl = document\.createElement\("img"\);\n\s*swirl\.src = mediaSrc\("romp-swirl-glyph\.svg"\); swirl\.alt = "";/);
  assert.match(CHUNK, /const word = document\.createElement\("span"\);\n\s*word\.textContent = "romp";/);
  assert.match(CHUNK, /for \(let i = 0; i < 3; i\+\+\) \{ const dot = document\.createElement\("i"\); dot\.className = "fileview-dot"; load\.appendChild\(dot\); \}/);
  // the rules the cue leans on exist in both sheets the viewer mounts under (fileview-parity.test.ts keeps them twins)
  for (const sheet of ["styles.css", "feed.css"]) {
    const css = read(sheet);
    assert.match(css, /^\.fileview-load \{ display: flex; align-items: center; justify-content: center;/m, sheet + ": the loader's rule");
    assert.match(css, /^\.fileview-load img \{[^}]*animation: fileview-spin/m, sheet + ": the swirl spins");
    assert.match(css, /^\.fileview-dot \{[^}]*background: var\(--accent\);/m, sheet + ": accent dots");
    assert.match(css, /^\.fileview-pdf-page \{ background: #fff;/m, sheet + ": the white sheet the cue sits on");
  }
});

test("the cue goes up in want() — the event that asks for the draw — and comes down at the events that end the wait, never on a timer", () => {
  assert.match(CHUNK, /const want = \(p: Page\) => \{ if \(!p\.queued\) \{ p\.queued = true; queue\.push\(p\); \} cue\(p\); void pump\(\); \};/);
  assert.match(CHUNK, /if \(p\.cue \|\| p\.drawnAt \|\| p\.failed\) return;/, "never over a bitmap (a sharpening redraw), never on a failed page");
  assert.match(CHUNK, /p\.drawnAt = cssW;\n\s*uncue\(p\);\s*\/\/[^\n]*\n\s*opts\.onPage\?\.\(/, "down when the bitmap lands, before onPage");
  assert.match(CHUNK, /p\.failed = true;\n\s*p\.task = null;\n\s*uncue\(p\);/, "down when the page fails");
  assert.match(CHUNK, /p\.drawnAt = 0;\n\s*uncue\(p\);/, "down when the page is evicted");
  assert.match(CHUNK, /cue\(pages\[0\]\);[^\n]*\n\s*pages\[0\]\.visible = true;\n\s*try \{ await race\(paint\(pages\[0\]\)\); \}/, "page 1's first draw too, cued before the paint that ends it");
  assert.doesNotMatch(CHUNK, /setTimeout|setInterval/, "no timer anywhere in the chunk");
});

// ── the built chunk in Chromium: the cue over a heavy page's sheet, logged and measured ──────────

const req = createRequire(path.join(PKG, "package.json"));
let chromium: any = null;
let SKIP: string | false = false;
try {
  chromium = req("playwright").chromium;
  const exe: string = chromium.executablePath();
  if (!exe || !fs.existsSync(exe)) SKIP = "playwright's chromium is not installed here (`npx playwright install chromium` in vscode-extension); the built-chunk cue test did not run";
} catch {
  SKIP = "playwright is not installed under vscode-extension/node_modules (run `npm ci` there); the built-chunk cue test did not run";
}
const OUT = path.join(PKG, "out-tests", "pdf-chunk-page-cue");

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
/** A page that takes a while to draw: `n` tiny filled rectangles scattered over it (deterministic). */
function heavyContent(n: number): string {
  const parts = ["0 0 0 rg"];
  for (let i = 0; i < n; i++) parts.push(`${(i * 37) % 600} ${(i * 91) % 780} 2 2 re f`);
  return parts.join("\n");
}
const HEAVY_RECTS = 150000;

/** The viewer's own rules for the elements involved, from the sheet the viewer loads. */
function viewerRules(): string {
  const css = read("styles.css");
  const rules = css.match(/^\.fileview-(?:body|pdfhost|pdf|pdf-page|pdf-canvas|load|load img|dot|dot:nth-of-type\(\d\)) \{[^}]*\}/gm) || [];
  assert.equal(rules.length, 10, "styles.css has one rule for each of .fileview-body, -pdfhost, -pdf, -pdf-page, -pdf-canvas, -load, -load img, -dot, -dot:nth-of-type(2), (3)");
  const frames = css.match(/^@keyframes fileview-(?:spin|pulse) \{.*\}\s*\}$/gm) || [];
  assert.equal(frames.length, 2, "the loader's two keyframes");
  return rules.concat(frames).join("\n");
}

async function buildChunk(): Promise<void> {
  await req("esbuild").build({
    entryPoints: [
      path.join(UI, "pdf-chunk.ts"),
      { in: path.join(PKG, "node_modules", "pdfjs-dist", "build", "pdf.worker.mjs"), out: "pdf-worker" },
    ],
    nodePaths: [path.join(PKG, "node_modules")],
    bundle: true, format: "iife", platform: "browser", target: "es2020", outdir: OUT, logLevel: "silent",
  });
}

const BODY_H = 600, BODY_W = 700;
const HTML = (rules: string) => `<!doctype html><html><head><meta charset="utf-8"><style>
:root { --accent: #9cd2ff; --dim: #b8b8b8; --shadow-modal: none; }
${rules}
.fileview { overflow: hidden; }
.fileview-body { height: ${BODY_H}px; width: ${BODY_W}px; }
</style></head><body>
<div class="fileview"><div class="fileview-body" id="body"><div class="fileview-pdfhost" id="host"></div></div></div>
<script src="/dist/pdf-chunk.js?v=1725300000"></script>
</body></html>`;

interface LogEntry { page: number; kind: "add" | "remove"; canvasW: number }
interface Sample { page: number; covers: boolean; display: string; position: string; pointerEvents: string; kids: number; swirl: string | null; word: string | null; dots: number; spin: string }

test("in Chromium: a heavy page entering the margin carries the loader over its sheet — logged on every add and removal, measured over the sheet while it draws — and loses it exactly as its bitmap lands; evicted pages get none until they return", { skip: SKIP }, async () => {
  await buildChunk();
  const html = HTML(viewerRules());
  const pdf = syntheticPdf([null, heavyContent(HEAVY_RECTS), null, null, null]);   // page 2 is the heavy one; 1 and 3–5 blank
  const swirl = fs.readFileSync(path.join(PKG, "media", "romp-swirl-glyph.svg"));
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage({ viewport: { width: 900, height: 900 } });
    const errors: string[] = [];
    page.on("pageerror", (e: Error) => errors.push("pageerror: " + e.message));
    await page.route("http://TESTHOST/**", (route: any) => {
      const u = new URL(route.request().url());
      if (u.pathname === "/view.html") return route.fulfill({ contentType: "text/html", body: html });
      if (u.pathname === "/doc.pdf") return route.fulfill({ contentType: "application/pdf", body: pdf });
      if (u.pathname === "/media/romp-swirl-glyph.svg") return route.fulfill({ contentType: "image/svg+xml", body: swirl });
      const f = path.join(OUT, path.basename(u.pathname));
      if (u.pathname.startsWith("/dist/") && fs.existsSync(f)) return route.fulfill({ contentType: "application/javascript", body: fs.readFileSync(f) });
      return route.fulfill({ status: 404, body: "" });
    });
    await page.goto("http://TESTHOST/view.html");
    await page.waitForFunction(() => !!(window as any).__rompPdf, null, { timeout: 10000 });

    // the recorder, armed BEFORE render(): a MutationObserver logs every cue added to or removed from a wrapper with the
    // canvas's backing width at that moment (exact, whatever the timing); a frame sampler measures each live cue
    const info = await page.evaluate(async (cueSel: string) => {
      const w = window as any;
      const host = document.getElementById("host")!;
      const log: LogEntry[] = []; const samples: Sample[] = []; const pages: number[] = [];
      w.__log = log; w.__samples = samples; w.__pages = pages;
      const isCue = (n: Node) => n.nodeType === 1 && (n as Element).matches(cueSel);
      const at = (t: Node) => { const wr = (t as Element).closest(".fileview-pdf-page") as HTMLElement | null; const c = wr?.querySelector("canvas") as HTMLCanvasElement | null; return { page: wr ? Number(wr.dataset.page) : -1, canvasW: c ? c.width : -1 }; };
      new MutationObserver((recs) => {
        for (const r of recs) {
          for (const n of Array.from(r.addedNodes)) if (isCue(n)) log.push({ kind: "add", ...at(r.target) });
          for (const n of Array.from(r.removedNodes)) if (isCue(n)) log.push({ kind: "remove", ...at(r.target) });
        }
      }).observe(host, { childList: true, subtree: true });
      const tick = () => {
        for (const c of Array.from(document.querySelectorAll(cueSel)) as HTMLElement[]) {
          const wr = c.parentElement!; const a = c.getBoundingClientRect(), b = wr.getBoundingClientRect(); const cs = getComputedStyle(c);
          const img = c.querySelector("img");
          if (samples.length < 5000) samples.push({
            page: Number(wr.dataset.page),
            covers: Math.abs(a.top - b.top) < 1 && Math.abs(a.left - b.left) < 1 && Math.abs(a.width - b.width) < 1 && Math.abs(a.height - b.height) < 1,
            display: cs.display, position: cs.position, pointerEvents: cs.pointerEvents, kids: c.children.length,
            swirl: img ? img.getAttribute("src") : null, word: c.querySelector("span")?.textContent ?? null,
            dots: c.querySelectorAll("i.fileview-dot").length, spin: img ? getComputedStyle(img).animationName : "",
          });
        }
        if (!w.__stop) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
      const bytes = await (await fetch("/doc.pdf")).arrayBuffer();
      const t0 = performance.now();
      const h = await w.__rompPdf.render(bytes, host, { onPage: (p: { index: number }) => pages.push(p.index) });
      w.__h = h;
      return { pages: h.pages as number, resolvedAfterMs: performance.now() - t0, bodyH: document.getElementById("body")!.clientHeight,
        top2: (document.querySelector('.fileview-pdf-page[data-page="2"]') as HTMLElement).offsetTop,
        top3: (document.querySelector('.fileview-pdf-page[data-page="3"]') as HTMLElement).offsetTop };
    }, CUE);
    assert.equal(info.pages, 5);
    assert.ok(info.top2 > info.bodyH && info.top2 < 2 * info.bodyH, `page 2 begins below the fold but within the margin (top ${info.top2}, body ${info.bodyH})`);
    assert.ok(info.top3 > 2 * info.bodyH, `page 3 begins beyond the margin (top ${info.top3})`);

    // page 2, heavy, was asked the moment the observer saw it inside the margin and takes a while: wait for its bitmap
    await page.waitForFunction(() => (window as any).__pages.includes(2), null, { timeout: 60000 });
    const state = async (): Promise<{ log: LogEntry[]; samples: Sample[]; pages: number[]; cues: number; canvasW: number[] }> => page.evaluate((cueSel: string) => {
      const w = window as any;
      return { log: w.__log as LogEntry[], samples: w.__samples as Sample[], pages: w.__pages as number[], cues: document.querySelectorAll(cueSel).length,
        canvasW: Array.from(document.querySelectorAll("canvas.fileview-pdf-canvas")).map((c) => (c as HTMLCanvasElement).width) };
    }, CUE);
    let s = await state();
    assert.deepEqual(s.pages, [1, 2], "pages 1 and 2 drawn, page 3 beyond the margin not");
    const of = (log: LogEntry[], p: number) => log.filter((e) => e.page === p);
    assert.deepEqual(of(s.log, 1).map((e) => e.kind), ["add", "remove"], "page 1: cued for its first draw, uncued when it landed");
    assert.ok(of(s.log, 1)[1].canvasW > 0, "…its bitmap was in when the cue went");
    assert.deepEqual(of(s.log, 2).map((e) => e.kind), ["add", "remove"], "page 2: one cue for its one draw");
    assert.ok(of(s.log, 2)[1].canvasW > 0, "…removed with the bitmap in, not before");
    for (const p of [3, 4, 5]) assert.deepEqual(of(s.log, p), [], `page ${p}, beyond the margin with nothing pending, was never cued`);
    assert.equal(s.cues, 0, "nothing pending now: no cue anywhere");
    // the frames sampled while page 2 drew: the loader covered its sheet, in the viewer's dress, pointer-transparent
    const heavy = s.samples.filter((x) => x.page === 2);
    assert.ok(heavy.length >= 1, `the sampler caught page 2's cue while it drew (${HEAVY_RECTS} rectangles; render() resolved after ${Math.round(info.resolvedAfterMs)} ms) — got ${heavy.length} frames`);
    for (const x of heavy) {
      assert.equal(x.covers, true, "the cue's box is the sheet's box");
      assert.equal(x.position, "absolute"); assert.equal(x.pointerEvents, "none");
      assert.equal(x.display, "flex", "the viewer's .fileview-load rule applies");
      assert.equal(x.kids, 5); assert.equal(x.swirl, "/media/romp-swirl-glyph.svg"); assert.equal(x.word, "romp"); assert.equal(x.dots, 3);
      assert.equal(x.spin, "fileview-spin", "the swirl spins under the viewer's rule");
    }
    assert.equal(errors.length, 0, errors.join("\n"));

    // scrolled so page 3 tops the body: page 1 is evicted with nothing pending (no cue); 3 and 4 enter, are cued, draw, uncue
    await page.evaluate((t: number) => { document.getElementById("body")!.scrollTop = t; }, info.top3);
    await page.waitForFunction(() => { const p = (window as any).__pages as number[]; return p.includes(3) && p.includes(4); }, null, { timeout: 20000 });
    await page.waitForFunction(() => (document.querySelector('canvas[data-page="1"]') as HTMLCanvasElement).width === 0, null, { timeout: 20000 });
    s = await state();
    assert.deepEqual(of(s.log, 1).map((e) => e.kind), ["add", "remove"], "page 1's eviction added no cue: it is not waiting for anything");
    for (const p of [3, 4]) {
      const k = of(s.log, p).map((e) => e.kind);
      assert.deepEqual(k, ["add", "remove"], `page ${p} entering the margin: cued, then uncued as it drew`);
      assert.ok(of(s.log, p)[1].canvasW > 0);
    }
    assert.equal(s.cues, 0);

    // back to the top: page 1 returns with no bitmap — cued again until its redraw lands
    await page.evaluate(() => { document.getElementById("body")!.scrollTop = 0; });
    await page.waitForFunction(() => ((window as any).__pages as number[]).filter((i) => i === 1).length >= 2, null, { timeout: 20000 });
    s = await state();
    assert.deepEqual(of(s.log, 1).map((e) => e.kind), ["add", "remove", "add", "remove"], "page 1: a second cue for its redraw on return");
    assert.ok(of(s.log, 1)[3].canvasW > 0);
    assert.equal(s.cues, 0);
    await page.evaluate(() => { (window as any).__stop = true; (window as any).__h.dispose(); });
    assert.equal(await page.evaluate(() => document.getElementById("host")!.childNodes.length), 0);
  } finally {
    await browser.close();
  }
});

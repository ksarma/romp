// The PDF chunk's ABORT of an unsettled render() (plans/file-review.md, Slice 4; the review's consolidation of
// 2026-09-06). render() yields no handle until page 1 is drawn, and pdf.js puts no deadline on opening a document
// or drawing a page, so an attempt that never settles — a Worker stuck in a pathological content stream — left the
// caller nothing to release: file-view.ts's deadline showed the frame and retired the attempt while the Worker ran on
// at full CPU for the tab's life, one more per attempt on that file. The caller's side landed first: every attempt
// is handed an AbortSignal (`opts.signal`), aborted wherever an unsettled attempt is retired (file-view-pdf-lifecycle
// .test.ts holds that against a stub that honors the abort). The chunk's side is held HERE, against the real render():
// while the promise is pending, an abort terminates the Worker at once (terminate() is synchronous; pdf.js's own
// destroy waits on a reply a hung Worker never sends), destroys the loading task, cancels a first-page draw in
// flight, leaves nothing of the chunk's in the container, and rejects with the signal's reason; a signal already
// aborted when render() is called starts nothing; and once the promise has resolved the signal is spent — a later
// abort does nothing, and dispose() is the release. One leg: makeRender over a stand-in pdf.js the test holds at each
// of render()'s awaits (the open, the first getPage, the first draw) and a Worker constructor it controls, plus the
// cross-file pin that the caller passes what the chunk reads. Synthetic throughout: TESTHOST, blank pages, invented
// bytes.
import { test, beforeEach } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { makeRender, abortReason, type PdfLib, type PageInfo } from "./pdf-chunk";

const web = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const SRC = "http://TESTHOST:29855/dist/pdf-worker.js?v=1725300000";

// ── a fake DOM: what the chunk touches of an element ─────────────────────────────────────────────

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
  /** A canvas's 2D context, as the staged draw uses one: the stage's, copied from, and the page's, copied into. */
  getContext(kind: string): { canvas: FakeEl; drawImage(): void } | null {
    return kind === "2d" && this.tagName === "CANVAS" ? { canvas: this, drawImage: () => {} } : null;
  }
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
let created = 0;
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
/** A container render() must never reach for on an attempt that never opened: every property read throws. */
const untouchable = () => new Proxy({}, {
  get(_t, k) { throw new Error("render() touched the container (" + String(k) + ") for an attempt that never opened"); },
}) as unknown as HTMLElement;

// ── a Worker constructor the test controls ──────────────────────────────────────────────────────

class FakeWorker {
  static made: FakeWorker[] = [];
  terminated = 0;
  constructor(public url: string, public opts: { type: string }) { FakeWorker.made.push(this); }
  addEventListener(): void {}
  terminate(): void { this.terminated++; }
}

// ── a fake pdf.js held at each of render()'s awaits until the test lets it go ──────────────────

interface Held<T> { promise: Promise<T>; release(v: T): void }
const held = <T>(): Held<T> => { let release!: (v: T) => void; const promise = new Promise<T>((r) => { release = r; }); return { promise, release }; };
interface Fake {
  lib: PdfLib;
  opts: { workerSrc: string; workerPort: unknown };
  calls: { getDocument: number; getPage: number[]; renders: number[]; cancelled: number; destroyed: number };
  /** the open: released by hand (`hang: true` holds it) */
  open: Held<unknown>;
  /** each getPage(i), held when `holdPages` names it */
  pages: Map<number, Held<unknown>>;
  /** each draw, held when `holdDraws` names its page */
  draws: Map<number, Held<void>>;
  /** pdf.js's destroy promise: settles when the test says, as a Worker's reply would */
  destroyDone: Held<void>;
}
function fakeLib(spec: { numPages: number; hang?: boolean; holdPages?: number[]; holdDraws?: number[] }): Fake {
  const opts = { workerSrc: SRC, workerPort: null as unknown };
  const calls = { getDocument: 0, getPage: [] as number[], renders: [] as number[], cancelled: 0, destroyed: 0 };
  class Cancelled extends Error {}
  const f: Fake = { lib: null as unknown as PdfLib, opts, calls, open: held(), pages: new Map(), draws: new Map(), destroyDone: held() };
  const proxy = (i: number) => ({
    getViewport: ({ scale }: { scale: number }) => ({ width: 612 * scale, height: 792 * scale }),
    render: () => {
      calls.renders.push(i);
      let cancel = () => {};
      const promise = new Promise<void>((res, rej) => {
        cancel = () => { calls.cancelled++; rej(new Cancelled("cancelled")); };
        if (spec.holdDraws?.includes(i)) { const h = held<void>(); f.draws.set(i, h); void h.promise.then(res); }
        else setTimeout(res, 1);
      });
      return { promise, cancel: () => cancel() };
    },
  });
  const doc = {
    numPages: spec.numPages,
    getPage: (i: number) => {
      calls.getPage.push(i);
      if (!spec.holdPages?.includes(i)) return Promise.resolve(proxy(i));
      const h = held<unknown>(); f.pages.set(i, h);
      return h.promise.then(() => proxy(i));
    },
  };
  f.lib = {
    GlobalWorkerOptions: opts,
    RenderingCancelledException: Cancelled,
    getDocument: () => {
      calls.getDocument++;
      if (!spec.hang) f.open.release(doc);
      return {
        promise: f.open.promise,
        destroy: () => { calls.destroyed++; return f.destroyDone.promise; },
      };
    },
  } as unknown as PdfLib;
  return f;
}
const tick = (ms = 5) => new Promise((r) => setTimeout(r, ms));
/** The rejection of `p` as a value, or "resolved". */
const outcome = (p: Promise<unknown>) => p.then(() => "resolved" as const, (e: unknown) => ({ rejected: e }));
class Reason { constructor(public why: string) {} }

const g = globalThis as any;
beforeEach(() => {
  FakeWorker.made = [];
  g.Worker = FakeWorker;
  g.document = { createElement: el };
  g.getComputedStyle = styleOf;
  delete g.IntersectionObserver;
  delete g.ResizeObserver;
  created = 0;
});

// ── the reason ─────────────────────────────────────────────────────────────────────────────────

test("abortReason is the signal's own reason — the caller's, or the engine's AbortError when abort() had none — and an Error of the chunk's only for a stand-in signal with neither", () => {
  const own = new AbortController(); const why = new Reason("the panel closed");
  own.abort(why);
  assert.equal(abortReason(own.signal), why, "the caller's reason, the same object");
  const bare = new AbortController(); bare.abort();
  const r = abortReason(bare.signal) as { name?: string };
  assert.equal(r && r.name, "AbortError", "abort() with no reason: the engine's AbortError, which is what file-view.ts's abort() yields");
  const fallback = abortReason({ aborted: true, reason: undefined } as unknown as AbortSignal) as Error;
  assert.ok(fallback instanceof Error && /aborted/.test(fallback.message), "a signal with no reason at all still rejects with something readable");
});

// ── before any work ─────────────────────────────────────────────────────────────────────────────

test("a signal already aborted when render() is called starts nothing: no Worker, no getDocument, the container untouched, the rejection the signal's reason", async () => {
  const f = fakeLib({ numPages: 1 });
  const ctl = new AbortController(); const why = new Reason("retired before the chunk loaded");
  ctl.abort(why);
  const r = await outcome(makeRender(f.lib)(new ArrayBuffer(8), untouchable(), { signal: ctl.signal }));
  assert.deepEqual(r, { rejected: why });
  assert.equal(FakeWorker.made.length, 0, "no Worker was started for an attempt already retired");
  assert.equal(f.calls.getDocument, 0, "pdf.js was not asked");
  assert.equal(created, 0);
});

// ── during the open ─────────────────────────────────────────────────────────────────────────────

test("aborted while the open hangs (a Worker that answers nothing): the Worker is terminated AT ONCE, before pdf.js's destroy settles; the task is destroyed once; render() rejects with the reason; nothing is created", async () => {
  const f = fakeLib({ numPages: 1, hang: true });
  const ctl = new AbortController(); const why = new Reason("the deadline");
  const attempt = outcome(makeRender(f.lib)(new ArrayBuffer(8), untouchable(), { signal: ctl.signal }));
  await tick();
  assert.equal(FakeWorker.made.length, 1); assert.equal(f.calls.getDocument, 1);
  const w = FakeWorker.made[0];
  assert.equal(w.terminated, 0, "the Worker lives while the attempt does");
  ctl.abort(why);
  assert.equal(w.terminated, 1, "terminated synchronously in the abort: pdf.js's destroy would wait on a reply this Worker never sends");
  assert.deepEqual(await attempt, { rejected: why }, "render() rejects with the signal's reason, not a message of the chunk's");
  assert.equal(f.calls.destroyed, 1, "the loading task destroyed once, all the same (pdf.js's own bookkeeping)");
  assert.equal(created, 0, "no root, no shell");
  // pdf.js's destroy settling later (it will not, for a hung Worker; here it does) adds no second terminate
  f.destroyDone.release();
  await tick();
  assert.equal(w.terminated, 1, "release() is idempotent: the adopt path's release after the destroy is inert");
});

// ── during the first getPage ────────────────────────────────────────────────────────────────────

test("aborted while the first page is being read (before a shell exists): the Worker terminated, the task destroyed, nothing in the container; the page answering later builds nothing", async () => {
  const f = fakeLib({ numPages: 3, holdPages: [1] });
  const { container } = viewerTree();
  const ctl = new AbortController(); const why = new Reason("the panel closed under the loader");
  const attempt = outcome(makeRender(f.lib)(new ArrayBuffer(8), asEl(container), { signal: ctl.signal }));
  await tick();
  assert.deepEqual(f.calls.getPage, [1], "held at the aspect's getPage(1)");
  const w = FakeWorker.made[0];
  ctl.abort(why);
  assert.equal(w.terminated, 1);
  assert.deepEqual(await attempt, { rejected: why });
  assert.equal(f.calls.destroyed, 1);
  assert.equal(container.children.length, 0, "nothing of the chunk's in the container");
  const before = created;
  f.pages.get(1)!.release(null);
  await tick();
  assert.equal(created, before, "the late answer builds no shells");
  assert.equal(container.children.length, 0);
  assert.deepEqual(f.calls.renders, [], "and draws nothing");
});

// ── during the first draw ───────────────────────────────────────────────────────────────────────

test("aborted while page 1 draws (the root already in the container): the draw is cancelled, the root removed, the Worker terminated, the task destroyed, no onPage, and the rejection is the reason", async () => {
  const f = fakeLib({ numPages: 2, holdDraws: [1] });
  const { container } = viewerTree();
  const pages: PageInfo[] = [];
  const ctl = new AbortController(); const why = new Reason("a reload over the loader");
  const attempt = outcome(makeRender(f.lib)(new ArrayBuffer(8), asEl(container), { signal: ctl.signal, onPage: (p) => pages.push(p) }));
  await tick();
  assert.deepEqual(f.calls.renders, [1], "page 1's draw is in flight");
  assert.equal(container.children.length, 1, "the root is in the container for the first draw: width-fit reads its width");
  assert.equal(container.children[0].children.length, 2, "…with both shells");
  const w = FakeWorker.made[0];
  ctl.abort(why);
  assert.equal(w.terminated, 1, "terminated at once");
  assert.deepEqual(await attempt, { rejected: why });
  assert.equal(f.calls.cancelled, 1, "the draw in flight was cancelled");
  assert.equal(container.children.length, 0, "the root is gone: the caller's fallback never shares the container with a stray root");
  assert.equal(f.calls.destroyed, 1);
  assert.deepEqual(pages, [], "no onPage for a draw that was cancelled");
  // the draw landing later (pdf.js resolves a cancelled task it had already finished) changes nothing
  f.draws.get(1)!.release();
  await tick(20);
  assert.deepEqual(pages, [], "still nothing: the attempt is over");
  assert.deepEqual(f.calls.renders, [1], "no second draw was queued");
});

// ── after the resolve ───────────────────────────────────────────────────────────────────────────

test("never after the mount: once render() has resolved the signal is spent — an abort terminates nothing and destroys nothing — and dispose() is the release", async () => {
  const f = fakeLib({ numPages: 1 });
  const { container } = viewerTree();
  const ctl = new AbortController();
  const h = await makeRender(f.lib)(new ArrayBuffer(8), asEl(container), { signal: ctl.signal });
  assert.equal(h.pages, 1);
  const w = FakeWorker.made[0];
  assert.equal(w.terminated, 0);
  ctl.abort(new Reason("too late"));
  await tick();
  assert.equal(w.terminated, 0, "the Worker lives on under the handle");
  assert.equal(f.calls.destroyed, 0, "the document is not released by a spent signal");
  assert.equal(container.children.length, 1, "the pages stay");
  h.dispose();
  assert.equal(f.calls.destroyed, 1, "dispose() is the release");
  f.destroyDone.release();
  await tick();
  assert.equal(w.terminated, 1, "…and the Worker goes once pdf.js's destroy settles, as ever");
  assert.equal(container.children.length, 0);
});

test("no signal: render() is what it was — a Worker, a document, a handle, dispose() the release", async () => {
  const f = fakeLib({ numPages: 1 });
  const { container } = viewerTree();
  const h = await makeRender(f.lib)(new ArrayBuffer(8), asEl(container));
  assert.equal(h.pages, 1);
  assert.equal(FakeWorker.made.length, 1); assert.equal(f.calls.destroyed, 0);
  h.dispose();
  assert.equal(f.calls.destroyed, 1);
});

// ── the two sides of the contract, pinned together ──────────────────────────────────────────────

test("source: the caller passes `signal` and the chunk reads it — the option in RenderOpts and the header's API block, the listener's terminate-first order, and the listener off before the handle is returned", () => {
  const CHUNK = web("pdf-chunk.ts");
  const VIEW = web("file-view.ts");
  assert.match(CHUNK, /export interface RenderOpts \{[^\n]*\bsignal\?: AbortSignal;/, "the option is typed");
  assert.match(CHUNK, /^\/\/\s+signal\?: AbortSignal;/m, "…and in the header's PUBLIC API block, where file-view.ts's inline type is copied from");
  assert.match(CHUNK, /if \(signal\?\.aborted\) throw abortReason\(signal\);/, "already aborted: nothing starts");
  assert.match(CHUNK, /onAbort = \(\) => \{ disposed = true; owned\?\.release\(\); rej\(abortReason\(signal\)\); \};/,
    "the listener: the attempt marked over, the Worker terminated (synchronous), then the race rejected — in that order");
  assert.match(CHUNK, /if \(signal\) signal\.removeEventListener\("abort", onAbort\);[^\n]*\n\s*return \{\n\s*pages: n,/,
    "the listener comes off at the resolve, before the handle exists: a spent signal reaches nothing");
  // the caller's side, as file-view-pdf-lifecycle.test.ts holds it in behavior: one AbortController per attempt, its signal into render()
  assert.match(VIEW, /const attempt = new AbortController\(\);\n\s*pdfAttempt = attempt;/);
  assert.match(VIEW, /signal: attempt\.signal,/, "file-view.ts passes the signal the chunk now reads");
});

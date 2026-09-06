// The PDF chunk's EVICTION DURING A PAGE FETCH (plans/file-review.md, Slice 4; the review of 2026-09-06). paint()
// has one await before it allocates a bitmap: the first-ever `doc.getPage(i)`, a worker round trip. The observer's
// eviction (drop) cancels the draw in flight — but during that await there is no draw yet, so an eviction landing
// then cancelled nothing, and paint resumed as if the page were still in the window: it sized the canvas, drew an
// invisible page, recorded it as drawn and fired onPage for a page nobody sees. The header promises that a page
// beyond the margin holds no bitmap; that page held one (some 13 MB at dpr 2 for a letter page 800 px wide) until
// it next entered and left, and a scroll through a long document hits this once per page that crosses the margin
// within one round trip. paint() now re-checks visibility after the fetch and stops; the page proxy is kept, so
// the page draws at once when it returns.
//
// One leg: makeRender over a stand-in pdf.js whose getPage the test holds and releases by hand, the observer fired
// by hand. Evicted during the fetch: nothing drawn, no onPage, a 0×0 canvas, and one draw on return without a second
// fetch. Evicted and back before the fetch answers: one draw. Evicted during the draw itself (the path that already
// worked): cancelled, not failed. Disposed during the fetch: nothing drawn, nothing failed. Synthetic: blank pages,
// TESTHOST.
import { test, beforeEach } from "node:test";
import * as assert from "node:assert/strict";
import { makeRender, type PdfLib, type PageInfo, type PageError } from "./pdf-chunk";

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

// ── a fake pdf.js whose getPage answers when the test says so ───────────────────────────────────

interface FakeLib {
  lib: PdfLib;
  calls: { getPage: number[]; renders: number[]; destroyed: number; cancelled: number };
  /** Answer a held getPage(i). */
  release(i: number): void;
}
/** `hold`: pages whose getPage waits for release(); `slow`: pages whose draw takes 30 ms instead of 1. */
function fakeLib(spec: { pages: number; hold?: number[]; slow?: number[] }): FakeLib {
  const calls = { getPage: [] as number[], renders: [] as number[], destroyed: 0, cancelled: 0 };
  const pending = new Map<number, () => void>();
  class Cancelled extends Error {}
  const proxy = (i: number) => ({
    getViewport: ({ scale }: { scale: number }) => ({ width: 612 * scale, height: 792 * scale }),
    render: () => {
      calls.renders.push(i);
      let cancel = () => {};
      const promise = new Promise<void>((res, rej) => {
        const t = setTimeout(res, spec.slow?.includes(i) ? 30 : 1);
        cancel = () => { clearTimeout(t); calls.cancelled++; rej(new Cancelled("cancelled")); };
      });
      return { promise, cancel: () => cancel() };
    },
  });
  const lib = {
    GlobalWorkerOptions: { workerSrc: "http://TESTHOST:29855/dist/pdf-worker.js" },
    RenderingCancelledException: Cancelled,
    getDocument: () => ({
      promise: Promise.resolve({
        numPages: spec.pages,
        getPage: (i: number) => {
          calls.getPage.push(i);
          if (!spec.hold?.includes(i)) return Promise.resolve(proxy(i));
          return new Promise((res) => { pending.set(i, () => res(proxy(i))); });
        },
      }),
      destroy: async () => { calls.destroyed++; },
    }),
  };
  const release = (i: number) => {
    const r = pending.get(i);
    assert.ok(r, "getPage(" + i + ") is not in flight");
    pending.delete(i); r!();
  };
  return { lib: lib as unknown as PdfLib, calls, release };
}

class FakeIO {
  static instances: FakeIO[] = [];
  targets: FakeEl[] = [];
  constructor(public cb: (entries: unknown[], io: FakeIO) => void, public opts: { root?: unknown; rootMargin?: string }) { FakeIO.instances.push(this); }
  observe(t: FakeEl): void { this.targets.push(t); }
  disconnect(): void {}
  fire(states: Array<[FakeEl, boolean]>): void { this.cb(states.map(([target, isIntersecting]) => ({ target, isIntersecting })), this); }
}

async function until(cond: () => boolean, what: string): Promise<void> {
  for (let i = 0; i < 2000; i++) { if (cond()) return; await new Promise((r) => setTimeout(r, 1)); }
  assert.fail("timed out waiting for " + what);
}
const settle = (ms = 15) => new Promise((r) => setTimeout(r, ms));   // long enough for any queued 1 ms draw to have landed
const canvasOf = (wrap: FakeEl) => wrap.querySelector("canvas.fileview-pdf-canvas")!;
const pagesOf = (container: FakeEl) => container.children[0].children;
const bytes = () => new ArrayBuffer(16);

beforeEach(() => {
  (globalThis as any).document = { createElement: el };
  (globalThis as any).getComputedStyle = styleOf;
  (globalThis as any).IntersectionObserver = FakeIO;
  delete (globalThis as any).ResizeObserver;
  FakeIO.instances.length = 0;
});

test("a page evicted while its getPage is in flight is not drawn — no bitmap, no onPage — and draws once on return without a second fetch; evicted and back before the answer, it draws once; evicted during the draw itself, the draw is cancelled, not failed", async () => {
  const { lib, calls, release } = fakeLib({ pages: 4, hold: [2, 3], slow: [4] });
  const { container } = viewerTree();
  const drawn: PageInfo[] = []; const errors: PageError[] = [];
  const h = await makeRender(lib)(bytes(), asEl(container), { onPage: (p) => drawn.push(p), onPageError: (e) => errors.push(e) });
  assert.equal(h.pages, 4);
  const io = FakeIO.instances[0];
  const wraps = pagesOf(container);
  assert.deepEqual(drawn.map((p) => p.index), [1], "page 1 drew before resolve; the rest are shells");
  const c2 = canvasOf(wraps[1]);

  // ── page 2 enters the margin: its fetch goes out and is held (a worker round trip)
  io.fire([[wraps[1], true]]);
  await until(() => calls.getPage.includes(2), "page 2's fetch");
  assert.equal(c2.width, 0, "no bitmap yet: the fetch has not answered");
  // ── it leaves before the answer: there is no draw to cancel, so the eviction itself changes nothing visible…
  io.fire([[wraps[1], false]]);
  assert.equal(calls.cancelled, 0, "nothing was in flight to cancel");
  // ── …and when the fetch answers, the page is NOT drawn: it is off screen
  release(2);
  await settle();
  assert.deepEqual(calls.renders, [1], "page 2 was not drawn (before the fix: drawn at full width for nobody)");
  assert.equal(c2.width, 0, "its canvas holds no bitmap"); assert.equal(c2.height, 0);
  assert.deepEqual(drawn.map((p) => p.index), [1], "no onPage for a page nobody sees (the panel would have repainted every overlay for it)");
  assert.deepEqual(errors, [], "not a failure either");
  // ── back in the window: one draw, from the proxy already fetched
  io.fire([[wraps[1], true]]);
  await until(() => drawn.length >= 2, "page 2's draw on return");
  assert.deepEqual(drawn.map((p) => p.index), [1, 2]);
  assert.ok(c2.width > 0, "drawn now that it is on screen");
  assert.equal(drawn[1].canvas, c2 as unknown as HTMLCanvasElement);
  assert.equal(calls.getPage.filter((i) => i === 2).length, 1, "the proxy was kept across the eviction: no second fetch");

  // ── page 3: enters, leaves and RE-ENTERS before its fetch answers — drawn exactly once, not zero times, not twice
  io.fire([[wraps[2], true]]);
  await until(() => calls.getPage.includes(3), "page 3's fetch");
  io.fire([[wraps[2], false]]);
  io.fire([[wraps[2], true]]);
  release(3);
  await until(() => drawn.length >= 3, "page 3's draw");
  await settle();
  assert.deepEqual(calls.renders, [1, 2, 3], "page 3 drawn once: the re-entry's request found the page already queued or drawn");
  assert.deepEqual(drawn.map((p) => p.index), [1, 2, 3]);
  assert.ok(canvasOf(wraps[2]).width > 0);
  assert.equal(calls.getPage.filter((i) => i === 3).length, 1);

  // ── page 4 (control, the path that already held): evicted during the DRAW — cancelled, no bitmap, not failed
  io.fire([[wraps[3], true]]);
  await until(() => calls.renders.includes(4), "page 4's draw to start");
  io.fire([[wraps[3], false]]);
  assert.equal(calls.cancelled, 1, "the draw in flight is cancelled");
  await settle(40);
  assert.deepEqual(drawn.map((p) => p.index), [1, 2, 3], "no onPage for the cancelled draw");
  assert.deepEqual(errors, [], "a cancelled draw is not a failed page");
  assert.equal(wraps[3].querySelector(".fileview-err"), null);
  assert.equal(canvasOf(wraps[3]).width, 0, "the eviction released the bitmap the cancelled draw had sized");

  h.dispose();
  assert.equal(calls.destroyed, 1);
});

test("dispose during a page's fetch: when it answers, nothing is drawn and nothing is marked failed", async () => {
  const { lib, calls, release } = fakeLib({ pages: 2, hold: [2] });
  const { container } = viewerTree();
  const drawn: number[] = []; const errors: PageError[] = [];
  const h = await makeRender(lib)(bytes(), asEl(container), { onPage: (p) => drawn.push(p.index), onPageError: (e) => errors.push(e) });
  const io = FakeIO.instances[0];
  const wraps = pagesOf(container);
  io.fire([[wraps[1], true]]);
  await until(() => calls.getPage.includes(2), "page 2's fetch");
  h.dispose();
  release(2);
  await settle();
  assert.deepEqual(calls.renders, [1]);
  assert.deepEqual(drawn, [1]);
  assert.deepEqual(errors, []);
  assert.equal(calls.destroyed, 1);
});

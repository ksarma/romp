// The viewer's text size and its fluid measure (the user 2026-09-07: the rendered markdown had to be zoomable, and
// a table did not follow the Files pane when the pane was resized). The size is a fixed table of steps (TEXT_SIZES,
// file-view.ts) that the A− / A+ buttons, the percentage readout (the reset) and Ctrl/Cmd + wheel over the body all
// land on; the chosen step rides the viewer root as `data-fv-text`, and the sheets turn it into the one property the
// text views read (--fv-scale). It persists per browser like the Rendered/Raw choice. Every reflow of a text view with
// its text unchanged (a step, the body's width changing) fires the seam's onRendered, the event the comments panel
// re-measures on; the stand-in's ResizeObserver plays the layout's report. Executable over the seam test's DOM
// stand-in against the REAL module, plus source and sheet pins, and a browser leg (headless Chromium, skipped
// loudly without one) that lays out a wide table, a long code line and an unbreakable string at two pane widths and
// two sizes and requires the page never to widen. Synthetic fixtures only: the notes-api world, placeholder ids.
import { test, type TestContext } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import type { FileViewActionCtx } from "./file-view";

const requireCjs = createRequire(__filename);
const web = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const VIEW = web("file-view.ts");
const PANEL = web("file-comments.ts");
const SHEETS: ReadonlyArray<readonly [string, string]> = [["styles.css", web("styles.css")], ["feed.css", web("feed.css")]];

// ── a DOM stand-in: the seam test's (file-view-seam.test.ts), verbatim: ancestry, ids, attributes, events with
// capture and bubbling, a small selector engine. Each suite inlines its own (the repo's idiom). ──
class Ev {
  target: El | Txt | null = null;
  currentTarget: El | null = null;
  defaultPrevented = false;
  stopped = false;
  key: string; ctrlKey: boolean; metaKey: boolean;
  constructor(public type: string, init: { key?: string; ctrlKey?: boolean; metaKey?: boolean } = {}) {
    this.key = init.key || ""; this.ctrlKey = !!init.ctrlKey; this.metaKey = !!init.metaKey;
  }
  preventDefault(): void { this.defaultPrevented = true; }
  stopPropagation(): void { this.stopped = true; }
}
type Listener = (ev: Ev) => void;
type Reg = { type: string; cb: Listener; capture: boolean; once: boolean };
const optsOf = (o?: boolean | { capture?: boolean; once?: boolean }) =>
  typeof o === "boolean" ? { capture: o, once: false } : { capture: !!(o && o.capture), once: !!(o && o.once) };
const kebab = (k: string) => k.replace(/[A-Z]/g, (c) => "-" + c.toLowerCase());
class Txt {
  nodeType = 3;
  parentNode: El | null = null;
  constructor(public data: string) {}
  get textContent(): string { return this.data; }
  get parentElement(): El | null { return this.parentNode; }
  // the change painters (Slice 2) split a row's text at a change's edges, as the comment painters do
  splitText(off: number): Txt {
    const tail = new Txt(this.data.slice(off));
    this.data = this.data.slice(0, off);
    const p = this.parentNode;
    if (p) { const i = p.childNodes.indexOf(this); p.childNodes.splice(i + 1, 0, tail); tail.parentNode = p; }
    return tail;
  }
}
type Compound = { tag: string | null; id: string | null; classes: string[]; attrs: Array<[string, string | null]> };
/** Comma groups of descendant chains (`A B`), each link a compound `tag#id.class[attr="v"]`. */
function parseSel(sel: string): Compound[][] {
  return sel.split(",").map((g) => g.trim()).filter(Boolean).map((g) => g.split(/\s+/).map((s) => {
    const m = /^([a-zA-Z][\w-]*)?(#[\w-]+)?((?:\.[\w-]+)*)((?:\[[\w-]+(?:="[^"]*")?\])*)$/.exec(s);
    if (!m) throw new Error("stand-in: unsupported selector " + s);
    const classes = (m[3].match(/\.[\w-]+/g) || []).map((c) => c.slice(1));
    const attrs: Array<[string, string | null]> = [];
    for (const a of m[4].match(/\[[^\]]+\]/g) || []) { const am = /^\[([\w-]+)(?:="([^"]*)")?\]$/.exec(a)!; attrs.push([am[1], am[2] ?? null]); }
    return { tag: m[1] ? m[1].toUpperCase() : null, id: m[2] ? m[2].slice(1) : null, classes, attrs };
  }));
}
class El {
  nodeType = 1;
  tagName: string;
  parentNode: El | null = null;
  childNodes: Array<El | Txt> = [];
  attrs = new Map<string, string>();
  listeners: Reg[] = [];
  hidden = false; disabled = false; title = ""; type = ""; value = ""; placeholder = ""; spellcheck = true; wrap = "";
  src = ""; alt = ""; href = ""; download = ""; target = ""; rel = "";
  innerHTML = "";
  style: Record<string, string> = {};
  onclick: ((ev: Ev) => void) | null = null;
  scrolled = 0;                                  // scrollIntoView calls (scrollToOffset's visible effect)
  constructor(tag: string) { this.tagName = tag.toUpperCase(); }
  get id(): string { return this.attrs.get("id") || ""; }
  set id(v: string) { this.attrs.set("id", v); }
  get isConnected(): boolean { return doc.body.contains(this); }
  get ownerDocument(): typeof doc { return doc; }
  get parentElement(): El | null { return this.parentNode; }
  get firstChild(): El | Txt | null { return this.childNodes[0] || null; }
  get className(): string { return this.attrs.get("class") || ""; }
  set className(v: string) { this.attrs.set("class", v); }
  get classes(): string[] { return this.className.split(/\s+/).filter(Boolean); }
  classList = {
    add: (...c: string[]) => { const s = new Set(this.classes); for (const x of c) s.add(x); this.className = [...s].join(" "); },
    remove: (...c: string[]) => { const s = new Set(this.classes); for (const x of c) s.delete(x); this.className = [...s].join(" "); },
    toggle: (c: string, on?: boolean) => { const want = on === undefined ? !this.classes.includes(c) : on; if (want) this.classList.add(c); else this.classList.remove(c); },
    contains: (c: string) => this.classes.includes(c),
  };
  dataset: Record<string, string> = new Proxy({} as Record<string, string>, {
    get: (_, k) => this.attrs.get("data-" + kebab(String(k))) as string,
    set: (_, k, v) => { this.attrs.set("data-" + kebab(String(k)), String(v)); return true; },
    has: (_, k) => this.attrs.has("data-" + kebab(String(k))),
    deleteProperty: (_, k) => { this.attrs.delete("data-" + kebab(String(k))); return true; },
  });
  get textContent(): string { return this.childNodes.map((c) => c.textContent).join(""); }
  set textContent(v: string) { for (const c of this.childNodes) c.parentNode = null; this.childNodes = []; if (v !== "") this.appendChild(new Txt(v)); }
  private detach(n: El | Txt): void { const p = n.parentNode; if (p) { const i = p.childNodes.indexOf(n); if (i >= 0) p.childNodes.splice(i, 1); n.parentNode = null; } }
  appendChild<T extends El | Txt>(n: T): T { this.detach(n); this.childNodes.push(n); n.parentNode = this; return n; }
  prepend(...ns: Array<El | Txt>): void { for (const n of ns.slice().reverse()) { this.detach(n); this.childNodes.unshift(n); n.parentNode = this; } }
  insertBefore<T extends El | Txt>(n: T, ref: El | Txt | null): T {
    if (!ref) return this.appendChild(n);
    this.detach(n);
    const i = this.childNodes.indexOf(ref);
    this.childNodes.splice(i < 0 ? this.childNodes.length : i, 0, n); n.parentNode = this; return n;
  }
  removeChild<T extends El | Txt>(n: T): T { this.detach(n); return n; }
  replaceChildren(...c: Array<El | Txt>): void { for (const x of this.childNodes) x.parentNode = null; this.childNodes = []; for (const x of c) this.appendChild(x); }
  remove(): void { this.detach(this); }
  normalize(): void {   // unpainting a mark leaves adjacent text nodes; join them, as the browser does
    const out: Array<El | Txt> = [];
    for (const c of this.childNodes) {
      if (c instanceof Txt) { if (!c.data) { c.parentNode = null; continue; } const last = out[out.length - 1]; if (last instanceof Txt) { last.data += c.data; c.parentNode = null; continue; } }
      else c.normalize();
      out.push(c);
    }
    this.childNodes = out;
  }
  setAttribute(k: string, v: string): void { this.attrs.set(k, v); }
  getAttribute(k: string): string | null { return this.attrs.has(k) ? (this.attrs.get(k) as string) : null; }
  hasAttribute(k: string): boolean { return this.attrs.has(k); }
  removeAttribute(k: string): void { this.attrs.delete(k); }
  contains(n: El | Txt | null): boolean { for (let x: El | Txt | null = n; x; x = x.parentNode) if (x === this) return true; return false; }
  private fits(c: Compound): boolean {
    return (!c.tag || c.tag === this.tagName) && (!c.id || c.id === this.id) && c.classes.every((k) => this.classes.includes(k))
      && c.attrs.every(([a, v]) => this.attrs.has(a) && (v === null || this.attrs.get(a) === v));
  }
  matches(sel: string): boolean {
    return parseSel(sel).some((chain) => {
      if (!this.fits(chain[chain.length - 1])) return false;
      let k = chain.length - 2;
      for (let a: El | null = this.parentNode; a && k >= 0; a = a.parentNode) if (a.fits(chain[k])) k--;
      return k < 0;
    });
  }
  closest(sel: string): El | null { for (let x: El | null = this; x; x = x.parentNode) if (x.matches(sel)) return x; return null; }
  querySelectorAll(sel: string): El[] {
    const out: El[] = [];
    const visit = (n: El) => { for (const c of n.childNodes) if (c instanceof El) { if (c.matches(sel)) out.push(c); visit(c); } };
    visit(this);
    return out;
  }
  querySelector(sel: string): El | null { return this.querySelectorAll(sel)[0] || null; }
  addEventListener(type: string, cb: Listener, o?: boolean | { capture?: boolean; once?: boolean }): void { this.listeners.push({ type, cb, ...optsOf(o) }); }
  removeEventListener(type: string, cb: Listener, o?: boolean | { capture?: boolean }): void {
    const cap = optsOf(o).capture;
    this.listeners = this.listeners.filter((l) => !(l.type === type && l.cb === cb && l.capture === cap));
  }
  dispatchEvent(ev: Ev): boolean { return dispatch(this, ev); }
  click(): void { this.dispatchEvent(new Ev("click")); }
  focus(): void { doc.activeElement = this; }
  blur(): void { if (doc.activeElement === this) doc.activeElement = null; }
  scrollIntoView(): void { this.scrolled++; }
  getBoundingClientRect(): { left: number; top: number; right: number; bottom: number; width: number; height: number } { return { left: 0, top: 0, right: 0, bottom: 0, width: 0, height: 0 }; }
  get offsetWidth(): number { return 0; }
}
const doc = {
  listeners: [] as Reg[],
  body: null as unknown as El,
  head: null as unknown as El,
  hidden: false,
  activeElement: null as El | null,
  createElement: (tag: string) => new El(tag),
  createTextNode: (s: string) => new Txt(s),
  getElementById: (id: string): El | null => doc.body.querySelector("#" + id),
  querySelectorAll: (sel: string): El[] => doc.body.querySelectorAll(sel),
  addEventListener(type: string, cb: Listener, o?: boolean | { capture?: boolean; once?: boolean }): void { doc.listeners.push({ type, cb, ...optsOf(o) }); },
  removeEventListener(type: string, cb: Listener, o?: boolean | { capture?: boolean }): void {
    const cap = optsOf(o).capture;
    doc.listeners = doc.listeners.filter((l) => !(l.type === type && l.cb === cb && l.capture === cap));
  },
  contains: (n: El | Txt | null) => doc.body.contains(n),
};
doc.body = new El("body"); doc.head = new El("head");
/** The DOM event path: document capture, ancestors' capture root→target, target and ancestors' bubble, document bubble. */
function dispatch(target: El | Txt, ev: Ev): boolean {
  ev.target = target;
  const chain: El[] = [];
  for (let n: El | null = target instanceof El ? target : target.parentNode; n; n = n.parentNode) chain.push(n);
  const run = (owner: { listeners: Reg[] }, capture: boolean, node: El | null): boolean => {
    for (const l of owner.listeners.slice()) {
      if (l.type !== ev.type || l.capture !== capture) continue;
      if (l.once) owner.listeners = owner.listeners.filter((x) => x !== l);
      ev.currentTarget = node; l.cb.call(node, ev);
      if (ev.stopped) return true;
    }
    if (node && !capture && ev.type === "click" && node.onclick) node.onclick(ev);
    return false;
  };
  if (run(doc, true, null)) return !ev.defaultPrevented;
  for (let i = chain.length - 1; i >= 0; i--) if (run(chain[i], true, chain[i])) return !ev.defaultPrevented;
  for (const n of chain) if (run(n, false, n)) return !ev.defaultPrevented;
  run(doc, false, null);
  return !ev.defaultPrevented;
}
const win: any = new EventTarget();
win.parent = win; win.innerWidth = 1200; win.innerHeight = 800;
win.getSelection = () => null;
win.confirm = () => true;
win.postMessage = () => { /* our own window: nothing listens here */ };
(globalThis as any).window = win;
(globalThis as any).document = doc;
const store = new Map<string, string>();
(globalThis as any).localStorage = {
  getItem: (k: string) => (store.has(k) ? store.get(k)! : null),
  setItem: (k: string, v: string) => { store.set(k, String(v)); },
  removeItem: (k: string) => { store.delete(k); },
};
// The editing substrate the viewer's editorChunk() resolves from: a buffer with the two callbacks the viewer wires.
win.__rompEditor = {
  mount(host: El, opts: { text: string; onChange: () => void; onSave: () => void }) {
    host.appendChild(new Txt(opts.text));
    return { value: () => opts.text, focus() { /* inert */ }, destroy() { /* inert */ } };
  },
};
// The layout's report of a size change, as the viewer hears it: a ResizeObserver stand-in that records what each
// observer watches and lets a test deliver a report with a width. The figure layer (file-comments-regions.ts) builds
// observers of its own through the same global; `report` targets the body alone.
type Observer = { cb: (entries: Array<{ contentRect: { width: number } }>) => void; targets: El[] };
const observers: Observer[] = [];
(globalThis as any).ResizeObserver = class {
  targets: El[] = [];
  constructor(public cb: Observer["cb"]) { observers.push(this); }
  observe(t: El): void { this.targets.push(t); }
  unobserve(t: El): void { this.targets = this.targets.filter((x) => x !== t); }
  disconnect(): void { this.targets = []; const i = observers.indexOf(this); if (i >= 0) observers.splice(i, 1); }
};
const watching = (t: El): Observer[] => observers.filter((o) => o.targets.includes(t));
const report = (t: El, width: number): void => { for (const o of watching(t)) o.cb([{ contentRect: { width } }]); };

// ── the kernel's /file, /version and /sessions, as the viewer fetches them ──────────────────────────
type Served = { bytes: string | Uint8Array; type: string; mtimeNs: string };
const disk: Record<string, Served> = {};
(globalThis as any).fetch = async (url: string) => {
  if (url.startsWith("/version")) return { json: async () => ({ fileEditing: true }) };   // consent already given
  if (url.startsWith("/sessions")) return { json: async () => [{ id: SID, name: "api", bg: "#123456", fg: "#ffffff" }] };
  const p = decodeURIComponent((/[?&]path=([^&]*)/.exec(url) || [])[1] || "");
  const f = disk[p];
  const headers = { get: (h: string) => (f ? (h === "Content-Type" ? f.type : h === "X-Romp-Mtime-Ns" ? f.mtimeNs : h === "X-Romp-Text-Utf8" ? "1" : null) : null) };
  if (!f) return { ok: false, status: 404, headers, text: async () => "no such file: " + p };
  return {
    ok: true, status: 200, headers,
    text: async () => String(f.bytes),
    blob: async () => new Blob([f.bytes as unknown as BlobPart], { type: f.type }),
  };
};

// ── fixtures: the notes-api world ──────────────────────────────────────────────────────────────────
const SID = "11111111-2222-3333-4444-555555555555";
const ROOT = "/repo/notes-api";
const REPORT = ROOT + "/docs/report.md";
const APP = ROOT + "/src/app.py";
const PLOT = ROOT + "/docs/plot.png";
const DOC = "# Report\n\n## Findings\nThe api session cut p95 latency by 40%.\n\n| run | p95 |\n| --- | --- |\n| a | 120 |\n";
const PY = "def main():\n    return 0\n";
const MT = "1757145600000000001";
const SIZE_KEY = "romp:fileviewTextSize";

// ── the probe: an action whose only job is to keep the ctx the viewer hands it and count its paints ──
let seam: FileViewActionCtx | null = null;
let paints = 0;
let fvMod: typeof import("./file-view") | null = null;
async function mod(): Promise<typeof import("./file-view")> {
  if (fvMod) return fvMod;
  fvMod = await import("./file-view");
  fvMod.initFileView(() => { /* the WS poster: the panel's asks go nowhere here */ });
  fvMod.registerFileViewAction({ id: "size-probe", mount(ctx) { seam = ctx; ctx.onRendered(() => { paints++; }); return null; } });
  return fvMod;
}
const settle = async () => { for (let i = 0; i < 8; i++) await new Promise<void>((r) => setImmediate(r)); };
type Open = { fv: typeof import("./file-view"); ctx: FileViewActionCtx; wrap: El; root: El; body: El; down: El; up: El; reset: El; btn: (label: string) => El };
/** Open `p` and wait for the fetch; the stored size is the caller's (set before the call), the format the default. */
async function open(p: string, t: TestContext, wait = true): Promise<Open> {
  const fv = await mod();
  disk[REPORT] = { bytes: DOC, type: "text/plain; charset=utf-8", mtimeNs: MT };
  disk[APP] = { bytes: PY, type: "text/plain; charset=utf-8", mtimeNs: MT };
  disk[PLOT] = { bytes: new Uint8Array([0x89, 0x50, 0x4e, 0x47]), type: "image/png", mtimeNs: MT };
  store.delete("romp:fileviewFmt");
  paints = 0; seam = null;
  assert.equal(fv.openFileView(p, SID), true, "the open happened");
  t.after(() => { fv.closeFileView(); store.delete(SIZE_KEY); });
  if (wait) await settle();
  const wrap = doc.getElementById("romp-fileview")!;
  const root = wrap.querySelector(".fileview")!;
  const body = wrap.querySelector(".fileview-body")!;
  const acts = wrap.querySelector(".fileview-acts")!;
  const btn = (label: string) => { const b = acts.querySelectorAll("button").find((x) => x.textContent === label); assert.ok(b, "the " + label + " button"); return b!; };
  const reset = acts.querySelector(".fileview-size-reset")!;
  assert.ok(reset, "the readout / reset button");
  assert.ok(seam, "the probe action was mounted with the ctx");
  return { fv, ctx: seam!, wrap, root, body, down: btn("A−"), up: btn("A+"), reset, btn };
}
const size = (o: Open): string | null => o.root.getAttribute("data-fv-text");
const wheel = (init: { dy: number; ctrl?: boolean; meta?: boolean; mode?: number }): Ev =>
  Object.assign(new Ev("wheel", { ctrlKey: !!init.ctrl, metaKey: !!init.meta }), { deltaY: init.dy, deltaMode: init.mode ?? 0 });

// ── the pure table ─────────────────────────────────────────────────────────────────────────────────

test("TEXT_SIZES: a bounded, ascending table of percentages holding the default; stepTextSize walks it and clamps at both ends", async () => {
  const { TEXT_SIZES, TEXT_SIZE_DEFAULT, stepTextSize } = await mod();
  assert.equal(TEXT_SIZES[0], 70); assert.equal(TEXT_SIZES[TEXT_SIZES.length - 1], 200);
  assert.ok(TEXT_SIZES.includes(TEXT_SIZE_DEFAULT) && TEXT_SIZE_DEFAULT === 100, "100 is a step and the default");
  for (let i = 1; i < TEXT_SIZES.length; i++) assert.ok(TEXT_SIZES[i] > TEXT_SIZES[i - 1], "ascending");
  assert.equal(stepTextSize(100, 1), 115); assert.equal(stepTextSize(100, -1), 90);
  assert.equal(stepTextSize(200, 1), 200, "the top clamps"); assert.equal(stepTextSize(70, -1), 70, "the bottom clamps");
  assert.equal(stepTextSize(175, 1), 200); assert.equal(stepTextSize(80, -1), 70);
  assert.equal(stepTextSize(123, 1), 115, "a value off the table steps from the default");
  // every step is reachable from the default by clicks, and the walk never leaves the table
  let at = 100; const seen = new Set<number>([at]);
  for (let i = 0; i < 20; i++) { at = stepTextSize(at, 1); seen.add(at); assert.ok(TEXT_SIZES.includes(at)); }
  for (let i = 0; i < 20; i++) { at = stepTextSize(at, -1); seen.add(at); assert.ok(TEXT_SIZES.includes(at)); }
  assert.equal(seen.size, TEXT_SIZES.length);
});

test("parseTextSize: a stored step comes back; absent, garbage, a number off the table, or a multiplier read as the default (parseFmt's contract)", async () => {
  const { parseTextSize } = await mod();
  assert.equal(parseTextSize("115"), 115); assert.equal(parseTextSize(" 200 "), 200); assert.equal(parseTextSize("70"), 70);
  assert.equal(parseTextSize(null), 100); assert.equal(parseTextSize(undefined), 100); assert.equal(parseTextSize(""), 100);
  assert.equal(parseTextSize("huge"), 100); assert.equal(parseTextSize("{\"pct\":115}"), 100);
  assert.equal(parseTextSize("110"), 100, "a size the table does not hold is not invented");
  assert.equal(parseTextSize("1.15"), 100, "a multiplier is not a percentage");
  assert.equal(parseTextSize("-100"), 100); assert.equal(parseTextSize("1e9"), 100);
});

test("foldWheel: a notch is a step, a pinch's small deltas fold up to one, a reversal starts over, lines and pages are normalized, up is larger", async () => {
  const { foldWheel, WHEEL_STEP_PX } = await mod();
  assert.deepEqual(foldWheel({ deltaY: -100, deltaMode: 0 }, 0), { acc: 0, dir: 1 }, "a Chrome notch up: larger at once");
  assert.deepEqual(foldWheel({ deltaY: 100, deltaMode: 0 }, 0), { acc: 0, dir: -1 }, "a notch down: smaller");
  assert.deepEqual(foldWheel({ deltaY: -3, deltaMode: 1 }, 0), { acc: 0, dir: 1 }, "three lines (Firefox) is a notch");
  assert.deepEqual(foldWheel({ deltaY: 1, deltaMode: 2 }, 0), { acc: 0, dir: -1 }, "a page is more than a notch");
  // a pinch: -15 px per event; the third crosses the threshold, and the sum clears
  let r = foldWheel({ deltaY: -15, deltaMode: 0 }, 0); assert.deepEqual(r, { acc: -15, dir: 0 });
  r = foldWheel({ deltaY: -15, deltaMode: 0 }, r.acc); assert.deepEqual(r, { acc: -30, dir: 0 });
  r = foldWheel({ deltaY: -15, deltaMode: 0 }, r.acc); assert.deepEqual(r, { acc: 0, dir: 1 });
  assert.ok(WHEEL_STEP_PX > 30 && WHEEL_STEP_PX <= 100, "a notch (about 100 px) is at least one step, a pinch's event (a few px) is not");
  // a reversal does not pay off the other way's remainder first
  r = foldWheel({ deltaY: -30, deltaMode: 0 }, 0); assert.equal(r.acc, -30);
  r = foldWheel({ deltaY: 10, deltaMode: 0 }, r.acc); assert.deepEqual(r, { acc: 10, dir: 0 });
  assert.deepEqual(foldWheel({ deltaY: 0, deltaMode: 0 }, -20), { acc: -20, dir: 0 }, "a horizontal-only event changes nothing");
});

// ── the control over the real openFileView ─────────────────────────────────────────────────────────

test("a markdown file opens at the default: A− / A+ up, the readout hidden, the root at 100; each click steps, stores, and acknowledges in the same tick; the ends disable", async (t) => {
  const { TEXT_SIZES } = await mod();
  const o = await open(REPORT, t);
  assert.equal(size(o), "100", "the root carries the step the sheets read");
  assert.equal(o.down.hidden, false); assert.equal(o.up.hidden, false);
  assert.equal(o.reset.hidden, true, "nothing to reset at the default, so nothing is said");
  assert.equal(o.down.getAttribute("aria-label"), "Smaller text"); assert.equal(o.up.getAttribute("aria-label"), "Larger text");
  o.up.click();
  assert.equal(size(o), "115", "one step, synchronously");
  assert.equal(o.reset.hidden, false); assert.equal(o.reset.textContent, "115%", "the readout is the acknowledgement");
  assert.equal(store.get(SIZE_KEY), "115", "stored as the percentage, under the viewer's own key");
  o.down.click(); o.down.click();
  assert.equal(size(o), "90"); assert.equal(o.reset.textContent, "90%"); assert.equal(store.get(SIZE_KEY), "90");
  for (let i = 0; i < 12; i++) o.up.click();
  assert.equal(size(o), "200", "clamped at the top however many clicks");
  assert.equal(o.up.disabled, true, "the top end reads as reached"); assert.equal(o.down.disabled, false);
  for (let i = 0; i < 12; i++) o.down.click();
  assert.equal(size(o), "70"); assert.equal(o.down.disabled, true); assert.equal(o.up.disabled, false);
  assert.equal(store.get(SIZE_KEY), String(TEXT_SIZES[0]));
  assert.deepEqual(o.down.classes, ["fileview-btn", "fileview-size"], "wears the row's one button treatment");
  assert.ok(o.reset.classes.includes("fileview-btn"), "the readout is a button, the reset");
});

test("the readout resets to the default and hides; a reset at the default is a no-op that repaints nothing", async (t) => {
  const o = await open(REPORT, t);
  o.up.click(); o.up.click();
  assert.equal(size(o), "130"); assert.equal(paints, 3, "the open's paint and two reflows");
  o.reset.click();
  assert.equal(size(o), "100"); assert.equal(o.reset.hidden, true); assert.equal(store.get(SIZE_KEY), "100");
  assert.equal(paints, 4, "the reset is a reflow too");
  assert.equal(o.up.disabled, false); assert.equal(o.down.disabled, false);
  const before = paints;
  o.reset.click();
  assert.equal(paints, before, "nothing changed, nothing fired");
});

test("persistence: the size survives a close and a fresh open, is applied before the bytes land, and a foreign stored value opens at the default", async (t) => {
  const first = await open(REPORT, t);
  first.up.click(); first.up.click(); first.up.click();
  assert.equal(size(first), "150");
  first.fv.closeFileView();
  assert.equal(doc.getElementById("romp-fileview"), null);
  const again = await open(REPORT, t, false);                        // no settle: the loader still holds the body
  assert.equal(size(again), "150", "the stored step is on the root at open, before the fetch");
  assert.equal(again.reset.textContent, "150%"); assert.equal(again.reset.hidden, false);
  await settle();
  assert.equal(size(again), "150", "the paint keeps it");
  again.fv.closeFileView();
  store.set(SIZE_KEY, "purple");
  const third = await open(REPORT, t);
  assert.equal(size(third), "100", "a corrupt entry costs the preference, never the viewer");
  assert.equal(third.reset.hidden, true);
  third.fv.closeFileView();
  store.set(SIZE_KEY, "80");
  const fourth = await open(APP, t);
  assert.equal(size(fourth), "80", "one size for every file this browser opens, a .py included");
  assert.equal(fourth.down.hidden, false, "a non-markdown text file has the control: the Raw view scales too");
});

test("Ctrl/Cmd + wheel over the body steps the size and takes the gesture from the page zoom; a plain wheel scrolls; small deltas fold; a media body leaves the browser its zoom", async (t) => {
  const o = await open(REPORT, t);
  const md = o.body.querySelector(".fileview-md")!;
  let ev = wheel({ dy: -100, ctrl: true });
  md.dispatchEvent(ev);
  assert.equal(size(o), "115", "a notch up with Ctrl: larger");
  assert.equal(ev.defaultPrevented, true, "the page zoom is prevented: the gesture is the viewer's here");
  ev = wheel({ dy: 100, meta: true });
  md.dispatchEvent(ev);
  assert.equal(size(o), "100", "Cmd works the same"); assert.equal(ev.defaultPrevented, true);
  ev = wheel({ dy: -100 });
  md.dispatchEvent(ev);
  assert.equal(size(o), "100", "no modifier: not the gesture"); assert.equal(ev.defaultPrevented, false, "…and the wheel scrolls as ever");
  for (const dy of [-15, -15]) md.dispatchEvent(wheel({ dy, ctrl: true }));
  assert.equal(size(o), "100", "a pinch's first events fold");
  md.dispatchEvent(wheel({ dy: -15, ctrl: true }));
  assert.equal(size(o), "115", "…and the third crosses the threshold");
  md.dispatchEvent(wheel({ dy: -3, ctrl: true, mode: 1 }));
  assert.equal(size(o), "130", "three lines is a notch");
  assert.equal(store.get(SIZE_KEY), "130", "the wheel stores like the buttons");
  // the bar is not the text: a wheel over the action row is not the gesture
  const acts = o.wrap.querySelector(".fileview-acts")!;
  ev = wheel({ dy: -100, ctrl: true }); acts.dispatchEvent(ev);
  assert.equal(size(o), "130"); assert.equal(ev.defaultPrevented, false);
  o.fv.closeFileView(); store.delete(SIZE_KEY);
  // an image body: nothing reads the property, so the browser keeps its zoom
  const pic = await open(PLOT, t);
  assert.equal(pic.ctx.mode(), "media");
  ev = wheel({ dy: -100, ctrl: true }); pic.body.dispatchEvent(ev);
  assert.equal(size(pic), "100"); assert.equal(ev.defaultPrevented, false, "not prevented: the page zoom stays the browser's");
});

test("click-safe: the three buttons are built once per open, never rebuilt by a paint; a Raw/Rendered flip and a step keep the same nodes", async (t) => {
  const o = await open(REPORT, t);
  const nodes = [o.down, o.reset, o.up];
  o.btn("Raw").click();
  assert.equal(o.ctx.mode(), "raw");
  assert.deepEqual([o.btn("A−"), o.wrap.querySelector(".fileview-size-reset"), o.btn("A+")], nodes, "the same elements after the Raw paint");
  o.up.click();
  assert.deepEqual([o.btn("A−"), o.wrap.querySelector(".fileview-size-reset"), o.btn("A+")], nodes, "…and after a step");
  assert.equal(size(o), "115", "the Raw view is scaled by the same property (.fileview-pre reads it)");
  o.btn("Rendered").click();
  assert.equal(size(o), "115", "the flip back keeps the size");
  // source: the control is declared before renderBody, outside it, with direct listeners (the format toggles' idiom)
  const at = (s: string) => { const i = VIEW.indexOf(s); assert.ok(i >= 0, s); return i; };
  assert.ok(at('const sizeDown = el("button", "fileview-btn fileview-size")') < at("const renderBody = () => {"), "built once per open, before the paint function");
  assert.equal((VIEW.match(/sizeDown\.addEventListener\("click", \(\) => setTextSize\(stepTextSize\(sizePct, -1\)\)\);/g) || []).length, 1, "the listener hangs on the node built once");
  const paint = VIEW.slice(at("const renderBody = () => {"), VIEW.indexOf("\n  };", at("const renderBody = () => {")));
  assert.doesNotMatch(paint, /addEventListener/, "the paint function wires nothing: it only syncs the control's hidden state");
  assert.match(paint, /sizeDown\.hidden = sizeHidden; sizeUp\.hidden = sizeHidden;/, "…which it does, every paint");
  assert.match(VIEW, /sizeUp\.addEventListener\("click", \(\) => setTextSize\(stepTextSize\(sizePct, 1\)\)\);/);
  assert.match(VIEW, /sizeReset\.addEventListener\("click", \(\) => setTextSize\(TEXT_SIZE_DEFAULT\)\);/);
  assert.match(VIEW, /body\.addEventListener\("wheel", \(e: WheelEvent\) => \{[\s\S]*?\}, \{ passive: false \}\);/, "the wheel listener is non-passive so the page zoom can be prevented");
  assert.doesNotMatch(VIEW, /e\.key === "\+"|e\.key === "-"|e\.key === "="/, "no keyboard zoom chord: Ctrl+plus/minus stay the browser's");
});

test("the control hides over a media body and in edit mode, and comes back with the read view", async (t) => {
  const pic = await open(PLOT, t);
  assert.equal(pic.down.hidden, true); assert.equal(pic.up.hidden, true); assert.equal(pic.reset.hidden, true);
  pic.fv.closeFileView();
  store.set(SIZE_KEY, "115");
  const o = await open(REPORT, t);
  assert.equal(o.down.hidden, false); assert.equal(o.reset.hidden, false, "off the default, the readout shows");
  o.btn("Edit").click();
  await settle();
  assert.equal(o.ctx.editing(), true, "edit mode");
  assert.equal(o.down.hidden, true); assert.equal(o.up.hidden, true); assert.equal(o.reset.hidden, true, "the editor keeps its own size");
  const md = o.body;
  const ev = wheel({ dy: -100, ctrl: true }); md.dispatchEvent(ev);
  assert.equal(size(o), "115", "the wheel stands down in edit mode"); assert.equal(ev.defaultPrevented, false);
  o.btn("Cancel").click();
  assert.equal(o.ctx.editing(), false);
  assert.equal(o.down.hidden, false); assert.equal(o.reset.hidden, false, "back with the read view");
});

// ── the re-measure: every reflow of a text view fires the seam's onRendered ────────────────────────

test("a size step fires onRendered once (the panel re-runs its paint pass over the moved text); a clamped step fires nothing", async (t) => {
  const o = await open(REPORT, t);
  assert.equal(paints, 1, "the open's paint");
  o.up.click();
  assert.equal(paints, 2, "the step is a reflow: one paint event, at once");
  o.body.querySelector(".fileview-md")!.dispatchEvent(wheel({ dy: -100, ctrl: true }));
  assert.equal(paints, 3, "the wheel's step too");
  for (let i = 0; i < 10; i++) o.up.click();
  assert.equal(size(o), "200");
  const at = paints;
  o.up.click();
  assert.equal(paints, at, "at the end of the table nothing changed, so nothing fired (no move without new information)");
  // the panel's side of the contract: its onRendered hides the floating Comment button (placed by a passage that has
  // moved) and re-runs the paint pass that wraps the highlights around the text again
  assert.match(PANEL, /ctx\.onRendered\(\(\) => \{ this\.float\.hidden = true; [^\n]*this\.paintAll\(\); \}\);/, "file-comments.ts answers onRendered with paintAll");
  assert.match(VIEW, /onRendered\(cb: \(\) => void\): void;/);
  assert.match(VIEW, /Also after a text view REFLOWS with its text unchanged: a text-size step/, "the seam's doc names the reflow triggers");
});

test("the body's width: a ResizeObserver on the body fires onRendered when the width changes, not for its first report, a same-width report, or a media body; it leaves with the viewer", async (t) => {
  const o = await open(REPORT, t);
  assert.equal(watching(o.body).length, 1, "one observer on the body, the width's own event (never a timer)");
  assert.equal(paints, 1);
  report(o.body, 900);
  assert.equal(paints, 1, "the observe() call's own first report describes no change");
  report(o.body, 600);
  assert.equal(paints, 2, "the pane narrowed: the text reflowed, the panel re-measures");
  report(o.body, 600);
  assert.equal(paints, 2, "the body grew taller with the same width: no text moved sideways");
  report(o.body, 1000);
  assert.equal(paints, 3, "wider again");
  o.btn("Edit").click();
  await settle();
  const inEdit = paints;
  report(o.body, 700);
  assert.equal(paints, inEdit, "the editor holds the body: its layout is its own");
  o.btn("Cancel").click();
  const body = o.body;
  o.fv.closeFileView();
  assert.equal(watching(body).length, 0, "disconnected with the viewer (the seam's onClose)");
  store.delete(SIZE_KEY);
  const pic = await open(PLOT, t);
  const before = paints;
  report(pic.body, 500); report(pic.body, 300);
  assert.equal(paints, before, "a media body has its own observers (the figure layer's, the chunk's)");
  assert.match(VIEW, /if \(typeof ResizeObserver !== "undefined"\) \{\n\s*let lastWidth = -1;/, "guarded like the figure layer's sizer: no observer, no width event");
  assert.doesNotMatch(VIEW, /setTimeout\([^)]*fireRendered|debounce/, "no timer approximates the resize");
});

// ── the sheets: one property, read by every text size; the fluid measure ───────────────────────────

const ruleOf = (css: string, head: string): string => { const at = css.indexOf(head); assert.ok(at >= 0, head + " present"); return css.slice(at, css.indexOf("}", at) + 1); };
const decls = (rule: string): string[] => rule.slice(rule.indexOf("{") + 1, -1).split(";").map((d) => d.trim()).filter(Boolean);

test("both sheets: the step table maps every TEXT_SIZES entry to --fv-scale on the viewer root, and nothing else; the text views read the one property", async () => {
  const { TEXT_SIZES } = await mod();
  for (const [name, css] of SHEETS) {
    for (const n of TEXT_SIZES) {
      const rule = ruleOf(css, `.fileview[data-fv-text="${n}"] {`);
      assert.deepEqual(decls(rule), [`--fv-scale: ${n / 100}`], name + ": step " + n + " is exactly the property");
    }
    const steps = css.match(/\.fileview\[data-fv-text="\d+"\]/g) || [];
    assert.equal(steps.length, TEXT_SIZES.length, name + ": no step the table does not hold");
    // the readers: the prose (em of its parent, so the page's size times the scale), its code, the Raw view's rows and gutter
    assert.ok(decls(ruleOf(css, ".fileview-md {")).includes("font-size: calc(1em * var(--fv-scale, 1))"), name + ": the prose reads it");
    assert.ok(!decls(ruleOf(css, ".fileview-md {")).some((d) => d.startsWith("max-width")), name + ": the root is fluid to the pane (the measure moved to the prose blocks)");
    assert.ok(decls(ruleOf(css, ".fileview-md pre code {")).includes("font-size: calc(12px * var(--fv-scale, 1))"), name + ": fenced code reads it");
    assert.ok(decls(ruleOf(css, ".fileview-pre {")).includes("font-size: calc(12px * var(--fv-scale, 1))"), name + ": the Raw rows read it");
    assert.ok(decls(ruleOf(css, ".fileview-gutter {")).includes("font-size: calc(12px * var(--fv-scale, 1))"), name + ": the gutter reads it, in lockstep with the rows");
    assert.ok(decls(ruleOf(css, ".fileview-md h1 {")).includes("font-size: 1.3em"), name + ": headings stay em of the prose, so they scale with it");
    assert.ok(decls(ruleOf(css, ".fileview-md :not(pre) > code {")).includes("font-size: 0.92em"), name + ": inline code stays em of the prose");
    assert.ok(decls(ruleOf(css, ".fileview-md .fc-overlay {")).includes("font-size: var(--fs)"), name + ": a figure's region chip keeps the page's size, not the text's");
    // no other rule reads the property: the bar, the aside, the editor keep the page's size
    const readers = (css.match(/^[^\n{]*\{[^}]*var\(--fv-scale[^}]*\}/gm) || []).map((r) => r.slice(0, r.indexOf("{")).trim());
    assert.deepEqual(readers.sort(), [".fileview-gutter", ".fileview-md", ".fileview-md > :not(table):not(pre)", ".fileview-md pre code", ".fileview-pre"].sort(), name + ": the readers, exactly");
  }
});

test("both sheets: the measure sits on the prose blocks and scales with the text; a table takes the pane and scrolls in its own box with whole words; the new rules are byte-equal across the sheets", () => {
  for (const [name, css] of SHEETS) {
    assert.deepEqual(decls(ruleOf(css, ".fileview-md > :not(table):not(pre) {")), ["max-width: calc(860px * var(--fv-scale, 1))"], name + ": the measure, a max that grows with the size (860px today, the same characters per line at every size)");
    assert.deepEqual(decls(ruleOf(css, ".fileview-md table {")),
      ["border-collapse: collapse", "margin: 0.6em 0", "display: block", "width: max-content", "max-width: 100%", "overflow-x: auto", "overflow-wrap: normal"],
      name + ": a table is a block as wide as its content up to the column, scrolling inside beyond it, whole words kept");
    assert.ok(decls(ruleOf(css, ".fileview-md {")).includes("overflow-wrap: anywhere"), name + ": prose still breaks an unbreakable string");
    assert.ok(decls(ruleOf(css, ".fileview-md pre {")).includes("overflow-x: auto"), name + ": a code block scrolls in its own box");
    assert.ok(decls(ruleOf(css, ".fileview-md pre code {")).includes("white-space: pre-wrap"), name + ": …and wraps first");
    assert.deepEqual(decls(ruleOf(css, ".fileview-md img {")), ["max-width: 100%"], name + ": a picture shrinks to the column");
  }
  const [chat, feed] = SHEETS.map(([, css]) => css);
  for (const head of [".fileview-md {", ".fileview-md > :not(table):not(pre) {", ".fileview-md table {", ".fileview-md pre code {", ".fileview-pre {", ".fileview-gutter {", ".fileview-md img {"]) {
    assert.equal(ruleOf(chat, head), ruleOf(feed, head), head + " mirrors exactly (the viewer mounts in both documents)");
  }
  const block = (css: string) => css.slice(css.indexOf("/* ── text size and measure"), css.indexOf("/* Rendered markdown ("));
  assert.ok(block(chat).length > 200, "the block with its rationale");
  assert.equal(block(chat), block(feed), "the step table and its comment mirror exactly");
});

// ── the browser leg: a real layout at two pane widths and two sizes ────────────────────────────────
let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

const PANE_CSS = web("files-pane.css");
const LONG = "unbreakable".repeat(6);
const ROWS = Array.from({ length: 3 }, (_, i) => `<tr><td>row ${i} alpha beta gamma delta</td><td>a fairly long cell of prose that keeps going on for a while</td><td>${LONG}</td><td>another long cell with many words in it to widen the table</td><td>five</td><td>six more text here</td></tr>`).join("");
const MD = `<h1 id=h1>Report</h1><p id=p>Prose ${"lorem ipsum ".repeat(40)}</p>
<table id=t><thead><tr><th>one</th><th>two</th><th>three</th><th>four</th><th>five</th><th>six</th></tr></thead><tbody>${ROWS}</tbody></table>
<pre id=pre><code>${"const x = 1; ".repeat(30)}</code></pre>
<p id=lw>${"x".repeat(140)}</p>
<p><img id=im width=900 height=200 src="data:image/svg+xml,${encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="900" height="200"><rect width="900" height="200" fill="#369"/></svg>')}"></p>`;
/** The viewer as openFileView builds it, in pane mode (the /files page: styles.css then files-pane.css) or as the modal
 *  over the feed (feed.css alone, the browser over the feed's document). */
const PAGE = (mode: "pane" | "feed") => `<!DOCTYPE html><html><head><meta charset=utf-8><style>${mode === "pane" ? web("styles.css") + "\n" + PANE_CSS : web("feed.css")}</style></head>
<body class="${mode === "pane" ? "fileview-pane" : "fileview-open"}"><div id="romp-fileview"><div class="fileview" id="root"><div class="fileview-bar"><div class="fileview-name"><span class="fileview-dir">/repo/notes-api/docs/</span><span class="fileview-base">report.md</span></div><div class="fileview-acts"><button class="fileview-btn">Rendered</button><button class="fileview-btn">Raw</button><button class="fileview-btn">A−</button><button class="fileview-btn">A+</button><button class="fileview-btn">✕</button></div></div>
<div class="fileview-main"><div class="fileview-body" id="body"><div class="fileview-md" id="md">${MD}</div></div></div></div></div></body></html>`;
type Lay = { bodyClient: number; bodyScroll: number; docScroll: number; win: number; md: number; p: number; t: number; tClient: number; tScroll: number; pre: number; lw: number; img: number; mdFont: string; h1Font: string; preFont: string };
const layout = (page: any): Promise<Lay> => page.evaluate(() => {
  const q = (s: string) => document.querySelector(s) as HTMLElement;
  const w = (s: string) => q(s).getBoundingClientRect().width;
  const body = q("#body");
  return { bodyClient: body.clientWidth, bodyScroll: body.scrollWidth, docScroll: document.documentElement.scrollWidth, win: innerWidth,
    md: w("#md"), p: w("#p"), t: w("#t"), tClient: q("#t").clientWidth, tScroll: q("#t").scrollWidth, pre: w("#pre"), lw: w("#lw"), img: w("#im"),
    mdFont: getComputedStyle(q("#md")).fontSize, h1Font: getComputedStyle(q("#h1")).fontSize, preFont: getComputedStyle(q("#pre code")).fontSize };
});
async function inBrowser(t: any, body: (browser: any) => Promise<void>): Promise<void> {
  if (!pw) { t.skip("playwright is not installed under vscode-extension, and the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw.chromium.launch(); }
  catch (e) { t.skip("no playwright browser on this box, and the browser leg needs one (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  try { await body(browser); } finally { await browser.close(); }
}
const near = (a: number, b: number, what: string) => assert.ok(Math.abs(a - b) < 1, what + ": " + a + " vs " + b);

test("in a browser: the page never widens; the prose keeps its measure and the table takes the pane; at 150% the measure and every text size grow together; narrow, the table scrolls in its own box", async (t) => {
  await inBrowser(t, async (browser) => {
    for (const mode of ["pane", "feed"] as const) {
      const page = await browser.newPage({ viewport: { width: 1000, height: 900 } });
      const errors: string[] = [];
      page.on("pageerror", (e: Error) => { errors.push(e.message); });
      await page.setContent(PAGE(mode));
      const inset = mode === "pane" ? 0 : 1000 * 0.05 + 2;                 // the modal is 95% of the pane inside a 1px border
      // 1000px wide, the default size
      let l = await layout(page);
      assert.equal(l.bodyScroll, l.bodyClient, mode + " @1000: the body does not scroll sideways");
      assert.equal(l.docScroll, l.win, mode + " @1000: the page is the window");
      assert.equal(l.mdFont, "13px", mode + ": the page's size at 100%, byte for byte"); assert.equal(l.preFont, "12px"); assert.equal(l.h1Font, "16.9px");
      near(l.p, 860, mode + " @1000: the prose measure is 860px at 100%");
      assert.ok(l.t > 860 && l.t <= l.bodyClient - 36 + 0.5, mode + " @1000: the table takes the pane (" + l.t + "), past the prose measure, inside the padding");
      assert.equal(l.tScroll, l.tClient, mode + " @1000: room enough, so the table does not scroll");
      near(l.md, l.bodyClient, mode + " @1000: the root is the body's width");
      assert.ok(l.img <= 860 + 0.5 && l.lw <= 860 + 0.5, mode + ": a picture and an unbreakable string stay in the measure");
      // 150%: the one property, read by every text size and the measure
      await page.evaluate(() => { document.getElementById("root")!.dataset.fvText = "150"; });
      l = await layout(page);
      assert.equal(l.mdFont, "19.5px", mode + " @150%: the prose"); assert.equal(l.h1Font, "25.35px", mode + " @150%: the heading, 1.3em of it"); assert.equal(l.preFont, "18px", mode + " @150%: fenced code");
      near(l.p, Math.min(1290, l.bodyClient - 36), mode + " @150%: the measure is 860 × 1.5, capped by the pane");
      assert.equal(l.bodyScroll, l.bodyClient, mode + " @150%: still no sideways scroll");
      // 420px: a phone-wide pane
      await page.setViewportSize({ width: 420, height: 900 });
      l = await layout(page);
      assert.equal(l.bodyScroll, l.bodyClient, mode + " @420: the body does not scroll sideways");
      assert.equal(l.docScroll, l.win, mode + " @420: the page is the window");
      near(l.t, l.bodyClient - 36, mode + " @420: the table is the column");
      assert.ok(l.tScroll > l.tClient + 100, mode + " @420: the unbreakable cell scrolls inside the table's own box (" + l.tScroll + " in " + l.tClient + ")");
      assert.ok(l.pre <= l.bodyClient - 36 + 0.5 && l.lw <= l.bodyClient - 36 + 0.5 && l.img <= l.bodyClient - 36 + 0.5, mode + " @420: code, the long string and the picture fit the column");
      near(l.p, l.bodyClient - 36, mode + " @420: the prose follows the pane below its measure");
      assert.ok(inset >= 0);
      assert.deepEqual(errors, [], "no script error in the page");
      await page.close();
    }
  });
});

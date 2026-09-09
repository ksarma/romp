// The viewer's text size and its fluid measure (the user 2026-09-07: the rendered markdown had to be zoomable, and
// a table did not follow the Files pane when the pane was resized). The size is a fixed table of steps (TEXT_SIZES,
// file-view.ts) that the A− / A+ buttons, the percentage readout (the reset) and Ctrl/Cmd + wheel over the body all
// land on; the chosen step rides the viewer root as `data-fv-text`, and the sheets turn it into the one property the
// text views read (--fv-scale). It persists per browser like the Rendered/Raw choice. Every reflow of a text view with
// its text unchanged (a step, the body's width changing) fires the seam's onRendered, the event the comments panel
// re-measures on; the stand-in's ResizeObserver plays the layout's report and its requestAnimationFrame the frame the
// reports fold into. Executable over the seam test's DOM stand-in against the REAL module, plus source and sheet pins,
// and two browser legs (headless Chromium, skipped loudly without one): the sheets over a static page, laying out a
// wide table, a long code line, an unbreakable string and a bare picture at two pane widths and two sizes, and the
// real module bundled into a page (the bar's geometry with a kernel-answered row, the fixed readout slot, the dimmed
// end, the kept focus, the selection guard), and the page's own inlining of a note holding `</script>` (scriptLiteral,
// the shared leg page's escape; the Slice 2 review, round 3: a bare JSON.stringify here would let such a note end the
// harness script before the fetch stub). Synthetic fixtures only: the notes-api world, placeholder ids.
import { test, type TestContext } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import type { FileViewActionCtx } from "./file-view";
import { scriptLiteral } from "./real-viewer-leg";

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
  style: Record<string, any> = { setProperty: (k: string, v: string) => { this.style[k] = v; } };   // CSSOM's write, for the body's --fv-body-w
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
// The frame the reports fold into: requestAnimationFrame callbacks queue until a test runs the frame, so a burst of
// reports can be delivered inside one frame and the repaints counted across it.
let frameSeq = 0;
const frames = new Map<number, () => void>();
(globalThis as any).requestAnimationFrame = (cb: () => void): number => { frames.set(++frameSeq, cb); return frameSeq; };
(globalThis as any).cancelAnimationFrame = (id: number): void => { frames.delete(id); };
const frame = (): void => { const run = [...frames.values()]; frames.clear(); for (const cb of run) cb(); };

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
/** The readout's slot is empty at the default (the sheet's visibility: hidden on this class): nothing to reset, nothing said. */
const blank = (o: Open): boolean => o.reset.classes.includes("fileview-size-default");
/** An end of the table: aria-disabled (dimmed by the sheet, focus kept), never the disabled property. */
const atEnd = (b: El): boolean => b.getAttribute("aria-disabled") === "true";
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

test("a markdown file opens at the default: A− / A+ up, the readout's slot empty, the root at 100; each click steps, stores, and acknowledges in the same tick; the ends dim and go inert", async (t) => {
  const { TEXT_SIZES } = await mod();
  const o = await open(REPORT, t);
  assert.equal(size(o), "100", "the root carries the step the sheets read");
  assert.equal(o.down.hidden, false); assert.equal(o.up.hidden, false);
  assert.equal(o.reset.hidden, false, "the readout's slot is in the row from the start, so A− never moves when it fills");
  assert.equal(blank(o), true, "nothing to reset at the default, so nothing is said: the slot is empty");
  assert.equal(o.down.getAttribute("aria-label"), "Smaller text"); assert.equal(o.up.getAttribute("aria-label"), "Larger text");
  o.up.click();
  assert.equal(size(o), "115", "one step, synchronously");
  assert.equal(blank(o), false); assert.equal(o.reset.textContent, "115%", "the readout is the acknowledgement");
  assert.equal(store.get(SIZE_KEY), "115", "stored as the percentage, under the viewer's own key");
  o.down.click(); o.down.click();
  assert.equal(size(o), "90"); assert.equal(o.reset.textContent, "90%"); assert.equal(store.get(SIZE_KEY), "90");
  for (let i = 0; i < 12; i++) o.up.click();
  assert.equal(size(o), "200", "clamped at the top however many clicks");
  assert.equal(atEnd(o.up), true, "the top end reads as reached: aria-disabled, which the sheet dims"); assert.equal(atEnd(o.down), false);
  assert.equal(o.up.disabled, false, "never the disabled property: a button that disables under keyboard focus drops the focus");
  let at = paints;
  o.up.click();
  assert.equal(size(o), "200"); assert.equal(paints, at, "a press on the end is the no-op it looks: no step, no paint");
  for (let i = 0; i < 12; i++) o.down.click();
  assert.equal(size(o), "70"); assert.equal(atEnd(o.down), true); assert.equal(atEnd(o.up), false); assert.equal(o.down.disabled, false);
  at = paints;
  o.down.click();
  assert.equal(size(o), "70"); assert.equal(paints, at);
  assert.equal(store.get(SIZE_KEY), String(TEXT_SIZES[0]));
  assert.deepEqual(o.down.classes, ["fileview-btn", "fileview-size"], "wears the row's one button treatment");
  assert.ok(o.reset.classes.includes("fileview-btn"), "the readout is a button, the reset");
});

test("the readout resets to the default and hides; a reset at the default is a no-op that repaints nothing", async (t) => {
  const o = await open(REPORT, t);
  o.up.click(); o.up.click();
  assert.equal(size(o), "130"); assert.equal(paints, 3, "the open's paint and two reflows");
  o.reset.click();
  assert.equal(size(o), "100"); assert.equal(blank(o), true, "back at the default the slot empties"); assert.equal(store.get(SIZE_KEY), "100");
  assert.equal(paints, 4, "the reset is a reflow too");
  assert.equal(atEnd(o.up), false); assert.equal(atEnd(o.down), false);
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
  assert.equal(size(again), "150", "the stored step is on the root at open, before the fetch, so the first paint is at size");
  assert.equal(again.reset.textContent, "150%");
  assert.equal(again.down.hidden, true); assert.equal(again.reset.hidden, true, "the control waits for the bytes: whether this is a text file is the kernel's verdict, in the fetch's headers");
  await settle();
  assert.equal(size(again), "150", "the paint keeps it");
  assert.equal(again.down.hidden, false); assert.equal(again.reset.hidden, false); assert.equal(blank(again), false);
  again.fv.closeFileView();
  store.set(SIZE_KEY, "purple");
  const third = await open(REPORT, t);
  assert.equal(size(third), "100", "a corrupt entry costs the preference, never the viewer");
  assert.equal(blank(third), true);
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
  assert.equal(o.down.hidden, false); assert.equal(o.reset.hidden, false); assert.equal(blank(o), false, "off the default, the readout says the size");
  o.btn("Edit").click();
  await settle();
  assert.equal(o.ctx.editing(), true, "edit mode");
  assert.equal(o.down.hidden, true); assert.equal(o.up.hidden, true); assert.equal(o.reset.hidden, true, "the editor keeps its own size");
  const md = o.body;
  const ev = wheel({ dy: -100, ctrl: true }); md.dispatchEvent(ev);
  assert.equal(size(o), "115", "the wheel stands down in edit mode"); assert.equal(ev.defaultPrevented, false);
  o.btn("Cancel").click();
  assert.equal(o.ctx.editing(), false);
  assert.equal(o.down.hidden, false); assert.equal(o.reset.hidden, false); assert.equal(blank(o), false, "back with the read view");
});

test("the control shows only once a text body is KNOWN: hidden beside the loader, shown when a text file's bytes land, never shown for a picture", async (t) => {
  // the kernel's Content-Type is the verdict, and it lands with the bytes (fetchFile applies both in one step); before
  // that a .png opened over a slow link showed A−, 130% and A+ beside the loader and took them away when the picture came
  store.set(SIZE_KEY, "130");
  const o = await open(REPORT, t, false);
  assert.equal(o.down.hidden, true); assert.equal(o.up.hidden, true); assert.equal(o.reset.hidden, true, "the loader holds the body: not yet a text view");
  assert.equal(size(o), "130", "the step is on the root already, so the first paint is at size");
  await settle();
  assert.equal(o.down.hidden, false); assert.equal(o.up.hidden, false); assert.equal(o.reset.hidden, false); assert.equal(o.reset.textContent, "130%");
  o.fv.closeFileView();
  const pic = await open(PLOT, t, false);
  assert.equal(pic.down.hidden, true, "a picture: hidden for the load");
  await settle();
  assert.equal(pic.ctx.mode(), "media");
  assert.equal(pic.down.hidden, true); assert.equal(pic.up.hidden, true); assert.equal(pic.reset.hidden, true, "...and after it: nothing there reads the property");
  assert.match(VIEW, /const sizeHidden = !textShowing\(\);/, "one gate for the control and for the reflow triggers: a text view showing");
  assert.match(VIEW, /sizeDown\.hidden = true; sizeReset\.hidden = true; sizeUp\.hidden = true;\s*\/\/ until renderBody knows a text body/);
});

test("an end of the table keeps the keyboard focus: the button is aria-disabled, never `disabled`; its press is the no-op it looks", async (t) => {
  // Chromium moves document.activeElement to the body when the focused element disables: the ring vanished on the third
  // Enter and a fourth did nothing with no visible reason (review 2026-09-07). The browser leg below presses the real keys.
  const o = await open(REPORT, t);
  o.down.focus();
  o.down.click(); o.down.click(); o.down.click();
  assert.equal(size(o), "70"); assert.equal(atEnd(o.down), true);
  assert.equal(o.down.disabled, false, "focusable still"); assert.equal(doc.activeElement, o.down, "focus where the person left it");
  const at = paints;
  o.down.click();
  assert.equal(size(o), "70"); assert.equal(paints, at, "the fourth press changes nothing and paints nothing");
  o.up.click();
  assert.equal(size(o), "80"); assert.equal(atEnd(o.down), false, "one step up and A− is live again");
  assert.doesNotMatch(VIEW, /sizeDown\.disabled = |sizeUp\.disabled = /, "never the disabled property");
  assert.match(VIEW, /const atEnd = \(b: HTMLButtonElement, end: boolean\) => \{ if \(end\) b\.setAttribute\("aria-disabled", "true"\); else b\.removeAttribute\("aria-disabled"\); \};/);
});

test("a press on the title bar settles no selection: with a passage selected in the body, a click on A+ steps the size and runs no selection hook (no re-seed of the quote chip, no re-fetch for its label)", async (t) => {
  const o = await open(REPORT, t);
  let hooked = 0;
  o.ctx.onSelection(() => { hooked++; });
  const md = o.body.querySelector(".fileview-md")!;
  win.getSelection = () => ({ isCollapsed: false, anchorNode: md, toString: () => "cut p95 latency" });
  t.after(() => { win.getSelection = () => null; });
  md.dispatchEvent(new Ev("mouseup"));
  assert.equal(hooked, 1, "a lift over the body settles the selection: the hooks run");
  o.up.dispatchEvent(new Ev("mouseup")); o.up.click();
  assert.equal(size(o), "115", "the step happened"); assert.equal(hooked, 1, "...and the press on A+ ran no hook");
  o.reset.dispatchEvent(new Ev("mouseup")); o.reset.click();
  assert.equal(size(o), "100"); assert.equal(hooked, 1);
  o.btn("Raw").dispatchEvent(new Ev("mouseup"));
  assert.equal(hooked, 1, "the guard is the bar's: every button in it (the selection listener predates the control)");
  o.wrap.querySelector(".fileview-main")!.dispatchEvent(new Ev("mouseup"));
  assert.equal(hooked, 2, "a drag that ends over the viewer's margins or the aside still settles: the listener stays on the viewer root");
  md.dispatchEvent(new Ev("touchend"));
  assert.equal(hooked, 3, "the phone's lift too");
  // the overshoot (round 2): a drag that starts in the body and is released over the bar's path, or its padding, is a
  // selection like any other; the round-1 guard read the whole bar and swallowed it (no Comment button, no chip)
  o.wrap.querySelector(".fileview-name")!.dispatchEvent(new Ev("mouseup"));
  assert.equal(hooked, 4, "released over the bar's path, the drag settles: the gate is the control under the lift, not the bar");
  o.wrap.querySelector(".fileview-dir")!.dispatchEvent(new Ev("mouseup"));
  assert.equal(hooked, 5, "...the directory link is a span, not a control");
  o.wrap.querySelector(".fileview-bar")!.dispatchEvent(new Ev("mouseup"));
  assert.equal(hooked, 6, "...and the bar's own padding");
  assert.match(VIEW, /const onSelect = \(ev: Event\) => \{\n\s*if \(editing\) return;[^\n]*\n(?:\s*\/\/[^\n]*\n)*\s*const at = ev\.target as Element \| null;\n\s*if \(at && bar\.contains\(at\) && typeof at\.closest === "function" && at\.closest\("button, a"\)\) return;/, "the gate: a control (a button, the GitHub anchor) inside the bar");
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
  assert.match(PANEL, /ctx\.onRendered\(\(\) => \{ this\.hideFloat\(\); [^\n]*this\.paintAll\(\); \}\);/, "file-comments.ts answers onRendered with paintAll");
  assert.match(VIEW, /onRendered\(cb: \(\) => void\): void;/);
  assert.match(VIEW, /Also after a text view REFLOWS with its text unchanged: a text-size step/, "the seam's doc names the reflow triggers");
  // both reflow triggers fire through the wrapper that keeps a standing selection across the panel's re-wrap (round 2:
  // a selection over a highlight lost the end inside the mark); the body-replacing paints keep nothing
  assert.equal((VIEW.match(/if \(textShowing\(\)\) \{ fireRenderedKeepingSelection\(\); seat\(/g) || []).length, 2, "the step and the width's frame, each seating the reader's place after the selection is put back (Slice 2 of plans/markdown-viewer.md)");
  assert.doesNotMatch(VIEW, /if \(textShowing\(\)\) fireRendered\(\);/);
  assert.match(VIEW, /sel\.setBaseAndExtent\(a\[0\], a\[1\], f\[0\], f\[1\]\)/, "put back anchor then focus: the direction is kept");
  // round 3: the ends go back only when the paint cost the selection one (the browser's own record is exact where the
  // offsets are not), never for a figure alone; round 5: that guard reads the captured text, not the offsets alone (a
  // selection of one line break from a highlight's end has coincident offsets too, and it IS rebuilt)
  assert.match(VIEW, /sel\.toString\(\) === kept\.text\) return;/, "a selection the paint left standing is not touched");
  assert.match(VIEW, /if \(kept\.a\.at === kept\.f\.at && kept\.text === ""\) return;/, "no text in the selection: no restore");
  assert.doesNotMatch(VIEW, /if \(kept\.a\.at === kept\.f\.at\) return;/, "coincident offsets alone never skip the restore");
  // round 4: each end is kept with its node, offset, text offset and the side of a text-node boundary it sat on; an end whose
  // node came through the paint at the same text offset goes back to it, and only an end whose node is gone is mapped from
  // its offset, the side of a boundary chosen by the side kept (a point inside a text node has none: its role decides)
  assert.match(VIEW, /a: keepPoint\(body, sel\.anchorNode, sel\.anchorOffset\), f: keepPoint\(body, sel\.focusNode, sel\.focusOffset\)/, "both ends kept before the hooks run");
  assert.match(VIEW, /side: boundarySide\(node, offset\)/, "the side bit is captured with the point");
  assert.match(VIEW, /return offset >= \(node as Text\)\.data\.length \? "end" : offset === 0 \? "start" : null;/, "a text node's end, start, or inside");
  assert.match(VIEW, /const a = pointBack\(body, kept\.a, kept\.a\.at < kept\.f\.at\); const f = pointBack\(body, kept\.f, kept\.f\.at < kept\.a\.at\)/, "anchor and focus put back through one path");
  assert.match(VIEW, /k\.node\.isConnected && root\.contains\(k\.node\) && k\.offset <= nodeLength\(k\.node\) && textOffset\(root, k\.node, k\.offset\) === k\.at\) return \[k\.node, k\.offset\];/, "a node that stands at the same text offset is reused as it was");
  assert.match(VIEW, /return textPoint\(root, k\.at, k\.side === null \? earlier : k\.side === "start"\);/, "a gone node: the offset mapped, the boundary side from the side kept");
  assert.match(VIEW, /start \? seen \+ t\.data\.length > n : seen \+ t\.data\.length >= n/, "strict for the start side, the boundary's later node");
});

test("the body's width: a ResizeObserver on the body fires onRendered once per animation frame when the width changed; not for its first report, a same-width report, a width back where it was, or a media body; it leaves with the viewer", async (t) => {
  const o = await open(REPORT, t);
  assert.equal(watching(o.body).length, 2, "two observers on the body, each a size's own event (never a timer): the viewer's width observer here, and the comments panel's margin sizer (file-comments.ts installLayout), which re-places the cards when the body's box changes");
  assert.equal(paints, 1);
  report(o.body, 900); frame();
  assert.equal(paints, 1, "the observe() call's own first report describes no change");
  report(o.body, 600);
  assert.equal(paints, 1, "the report asks for a frame; the repaint is the frame's, not the report's");
  assert.equal(frames.size, 1, "one frame requested");
  frame();
  assert.equal(paints, 2, "the pane narrowed: the text reflowed, the panel re-measures, once");
  report(o.body, 600); frame();
  assert.equal(paints, 2, "the body grew taller with the same width: no text moved sideways");
  // a burst inside one frame (a drag's reports, several observers' entries): one paint pass, not four
  report(o.body, 590); report(o.body, 580); report(o.body, 570); report(o.body, 560);
  assert.equal(frames.size, 1, "one frame for the burst"); assert.equal(paints, 2);
  frame();
  assert.equal(paints, 3, "one repaint for the four reports");
  // moved and came back within the frame: the width the frame finds is the one last painted over
  report(o.body, 700); report(o.body, 560); frame();
  assert.equal(paints, 3, "nothing moved sideways by the frame, so nothing fired");
  report(o.body, 1000); frame();
  assert.equal(paints, 4, "wider again");
  o.btn("Edit").click();
  await settle();
  const inEdit = paints;
  report(o.body, 700); frame();
  assert.equal(paints, inEdit, "the editor holds the body: its layout is its own");
  o.btn("Cancel").click();
  report(o.body, 800);                                  // a frame pending as the viewer closes
  assert.equal(frames.size, 1);
  const body = o.body;
  o.fv.closeFileView();
  assert.equal(watching(body).length, 0, "disconnected with the viewer (the seam's onClose)");
  assert.equal(frames.size, 0, "...and its pending frame cancelled with it");
  store.delete(SIZE_KEY);
  const pic = await open(PLOT, t);
  const before = paints;
  report(pic.body, 500); report(pic.body, 300); frame();
  assert.equal(paints, before, "a media body has its own observers (the figure layer's, the chunk's)");
  assert.match(VIEW, /if \(typeof ResizeObserver !== "undefined"\) \{\n\s*let paintedWidth = -1;/, "guarded like the figure layer's sizer: no observer, no width event");
  assert.match(VIEW, /if \(typeof requestAnimationFrame === "function"\) frame = requestAnimationFrame\(repaint\); else repaint\(\);/, "the frame is the fold; without one the report is the frame");
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
    // the readers: the prose (1.15 times the page's size, times the scale: 15px at the 13px default, Slice 3 of
    // plans/markdown-viewer.md), its code, the Raw view's rows and gutter
    assert.ok(decls(ruleOf(css, ".fileview-md {")).includes("font-size: calc(var(--fs) * 1.15 * var(--fv-scale, 1))"), name + ": the prose reads it, at the document size over the page's");
    assert.ok(!decls(ruleOf(css, ".fileview-md {")).some((d) => d.startsWith("max-width")), name + ": the root is fluid to the pane (the measure is its inline padding)");
    assert.ok(decls(ruleOf(css, ".fileview-md pre code {")).includes("font-size: calc(12px * var(--fv-scale, 1))"), name + ": fenced code reads it");
    assert.ok(decls(ruleOf(css, ".fileview-pre {")).includes("font-size: calc(12px * var(--fv-scale, 1))"), name + ": the Raw rows read it");
    assert.ok(decls(ruleOf(css, ".fileview-gutter {")).includes("font-size: calc(12px * var(--fv-scale, 1))"), name + ": the gutter reads it, in lockstep with the rows");
    assert.ok(decls(ruleOf(css, ".fileview-md h1 {")).includes("font-size: 2em"), name + ": headings stay em of the prose, so they scale with it (GitHub's 2em h1 since Slice 3 of plans/markdown-viewer.md)");
    assert.ok(decls(ruleOf(css, ".fileview-md :not(pre) > code {")).includes("font-size: 0.92em"), name + ": inline code stays em of the prose");
    assert.ok(decls(ruleOf(css, ".fileview-md .fc-overlay {")).includes("font-size: var(--fs)"), name + ": a figure's region chip keeps the page's size, not the text's");
    // no other rule reads the property: the bar, the aside, the editor keep the page's size
    const readers = (css.match(/^[^\n{]*\{[^}]*var\(--fv-scale[^}]*\}/gm) || []).map((r) => r.slice(0, r.indexOf("{")).trim());
    assert.deepEqual(readers.sort(), [".fileview-gutter", ".fileview-md", ".fileview-md pre code", ".fileview-pre"].sort(), name + ": the readers, exactly (the 860px measure rule and the direct-child media cap that scaled it went with Slice 3 of plans/markdown-viewer.md: the measure is 80ch of the root's own font, which the scale moves)");
  }
});

test("both sheets: the measure is the root's inline padding, a centred column of 80ch that scales with the text; a table may leave the column up to the body's inset and scrolls in its own box with whole words; a picture always fits its column; the new rules are byte-equal across the sheets", () => {
  for (const [name, css] of SHEETS) {
    // Slice 3 of plans/markdown-viewer.md (decision 4): the 860px cap on every block became the root's own inline padding,
    // at least 18px a side and half of what the body is wider than 80ch beyond that; ch is the root's own zero glyph, so
    // the column is eighty characters at every --fv-scale and in either face, and every child sits in it
    const root = decls(ruleOf(css, ".fileview-md {"));
    assert.ok(root.includes("padding-inline: max(18px, round(down, calc((100% - 80ch) / 2), 1px))"), name + ": the measure, the root's inline padding, in whole pixels (a fractional edge met a Chromium drag-selection quirk)");
    assert.ok(root.indexOf("padding: 14px 18px") >= 0 && root.indexOf("padding: 14px 18px") < root.findIndex((d) => d.startsWith("padding-inline")), name + ": the plain 18px stands first, the fallback for a browser without round()");
    const bare = css.replace(/\/\*[\s\S]*?\*\//g, "");
    assert.doesNotMatch(bare, /\.fileview-md > :where\(:not\(table\)\)|860px/, name + ": no per-block cap and no 860px constant in any rule (the comments may tell the history)");
    assert.doesNotMatch(css, /\.fileview-md > :not\(/, name + ": no block-cap rule at any specificity");
    assert.deepEqual(decls(ruleOf(css, ".fileview-md img {")), ["max-width: 100%"], name + ": a picture shrinks to its column");
    assert.doesNotMatch(css, /\.fileview-md > img, \.fileview-md > svg/, name + ": the direct-child media cap went with the constant (100% of the column is the measure for a direct child too)");
    assert.deepEqual(decls(ruleOf(css, ":where(.fileview-md) svg, :where(.fileview-md) canvas, :where(.fileview-md) video {")), ["max-width: 100%"], name + ": media a note draws itself shrinks to its column like a picture, at zero class specificity so KaTeX's own svg rule wins (md-sanitize-wide-media-browser.test.ts lays it out)");
    assert.deepEqual(decls(ruleOf(css, ':where(.fileview-md :is(img, svg, canvas, video)[width]:not([width$="%"])) {')), ["height: auto"], name + ": a pixel-sized one keeps its ratio as it shrinks (a sized <img> too, since Slice 2 of plans/markdown-viewer.md); a percentage-width one keeps the author's height (the cap never shrinks it), and the whole selector sits inside :where so its two attribute tests add no specificity over KaTeX's svg rule");
    // the table's cap is the BODY's width less the root's 18px inset (--fv-body-w: the body's content width, written on the body
    // by the viewer's ResizeObserver), and a table wider than the column is moved left by half the excess (a percentage in
    // translate is of the table's own width; half the body less the padding is half the column), so it grows out of the column
    // evenly, into both gutters, and a table no wider than the column is not moved at all (the min); with the property unset
    // the cap falls back to the column and the shift to none. file-view-typescale-browser.test.ts lays the three widths out
    assert.deepEqual(decls(ruleOf(css, ".fileview-md table {")),
      ["border-collapse: collapse", "margin: 0.6em 0", "display: block", "width: max-content", "max-width: 100%", "overflow-x: auto", "overflow-wrap: normal"],
      name + ": a table is a block as wide as its content up to its container, scrolling inside beyond it, whole words kept (a table in a quote or a list item stays in it)");
    assert.deepEqual(decls(ruleOf(css, ".fileview-md > table {")),
      ["max-width: calc(var(--fv-body-w, calc(100% + 36px)) - 36px)", "translate: min(0px, round(calc(var(--fv-body-w, calc(100% + 36px)) / 2 - max(18px, round(down, (var(--fv-body-w, calc(100% + 36px)) - 80ch) / 2, 1px)) - 50%), 1px))"],
      name + ": a table of the page's own is capped at the body's inset and centred on the column once wider than it (with the property unset both read the stand-in: the cap is the column and the shift none)");
    assert.deepEqual(decls(ruleOf(css, ".fileview-body {")), ["flex: 1 1 auto", "min-height: 0", "overflow: auto"], name + ": the body reserves no scrollbar gutter and is no size container (review round 2 of Slice 3 of plans/markdown-viewer.md: the gutter was a blank strip beside every body that does not scroll; the cap reads the observer's width instead)");
    assert.ok(decls(ruleOf(css, ".fileview-md {")).includes("overflow-wrap: anywhere"), name + ": prose still breaks an unbreakable string");
    assert.ok(decls(ruleOf(css, ".fileview-md pre {")).includes("overflow-x: auto"), name + ": a code block scrolls in its own box");
    assert.ok(decls(ruleOf(css, ".fileview-md pre code {")).includes("white-space: pre-wrap"), name + ": …and wraps first");
  }
  const [chat, feed] = SHEETS.map(([, css]) => css);
  for (const head of [".fileview-md {", ".fileview-md table {", ".fileview-md > table {", ".fileview-md pre code {", ".fileview-pre {", ".fileview-gutter {", ".fileview-md img {", ":where(.fileview-md) svg, :where(.fileview-md) canvas, :where(.fileview-md) video {", ':where(.fileview-md :is(img, svg, canvas, video)[width]:not([width$="%"])) {', ".fileview-body {"]) {
    assert.equal(ruleOf(chat, head), ruleOf(feed, head), head + " mirrors exactly (the viewer mounts in both documents)");
  }
  const block = (css: string) => css.slice(css.indexOf("/* ── text size and measure"), css.indexOf("/* Rendered markdown ("));
  assert.ok(block(chat).length > 200, "the block with its rationale");
  assert.equal(block(chat), block(feed), "the step table and its comment mirror exactly");
});

test("both sheets: the title bar wraps and the action row shrinks and wraps to the right edge; a disabled or aria-disabled bar button is dimmed with an inert hover; the readout is a fixed slot, empty at the default", () => {
  for (const [name, css] of SHEETS) {
    // the modal's one-line bar clipped Download, Copy path and the close button off the card below about 600px once the
    // control's three buttons joined the row (.fileview is overflow: hidden); the pane variant had wrapped already
    const bar = decls(ruleOf(css, ".fileview-bar {"));
    assert.ok(bar.includes("flex-wrap: wrap") && bar.includes("gap: 6px 10px"), name + ": the bar wraps, 6px between its lines");
    // the wrap is the BAR's (round 2): the Files pane's Recent rows wear .fileview-name and the file browser's action row
    // .fileview-acts outside any bar, and the base rules keep the plain flex they had before the control
    assert.deepEqual(decls(ruleOf(css, ".fileview-bar .fileview-name {")), ["flex: 1 1 0", "min-width: 12em"], name + ": in the bar the path keeps 12em and takes the rest of a wide bar");
    const nm = decls(ruleOf(css, ".fileview-name {"));
    assert.ok(nm.includes("flex: 1 1 auto") && nm.includes("min-width: 0"), name + ": the class alone shrinks freely (a Recent row in a 200px pane)");
    const barActs = decls(ruleOf(css, ".fileview-bar .fileview-acts {"));
    for (const d of ["flex: 0 1 auto", "min-width: 0", "margin-left: auto", "flex-wrap: wrap", "justify-content: flex-end"]) assert.ok(barActs.includes(d), name + ": in the bar the action row " + d);
    assert.deepEqual(decls(ruleOf(css, ".fileview-acts {")), ["flex: 0 0 auto", "display: flex", "align-items: center", "gap: 6px"], name + ": the class alone is one rigid row (the browser's bar never wraps)");
    assert.ok(!decls(ruleOf(css, ".fb-bar {")).some((d) => d.startsWith("flex-wrap")), name + ": .fb-bar has no wrap of its own");
    // one disabled dress for every bar button: the GitHub unit's no-link state (disabled) and the control's ends (aria-disabled)
    assert.deepEqual(decls(ruleOf(css, '.fileview-btn:disabled, .fileview-btn[aria-disabled="true"] {')), ["opacity: 0.55", "cursor: default"], name + ": dimmed, default cursor");
    assert.deepEqual(decls(ruleOf(css, '.fileview-btn:disabled:hover, .fileview-btn[aria-disabled="true"]:hover {')), ["border-color: var(--card-border)", "color: var(--fg)", "background: transparent"], name + ": the hover is inert (the rest colours, not the accent)");
    assert.deepEqual(decls(ruleOf(css, '.fileview-btn:disabled:active, .fileview-btn[aria-disabled="true"]:active {')), ["transform: none"], name + ": no press pulse");
    assert.doesNotMatch(css, /\.fileview-gh \.fileview-btn:disabled/, name + ": the GitHub unit's disabled rules are the bar's now, not its own");
    // the readout: one width whatever it says, and an empty box (not none) at the default
    assert.deepEqual(decls(ruleOf(css, ".fileview-size-reset {")), ["min-width: 5.5em", "box-sizing: border-box", "text-align: center", "font-variant-numeric: tabular-nums"], name + ": a slot of one width");
    assert.deepEqual(decls(ruleOf(css, ".fileview-size-reset.fileview-size-default {")), ["visibility: hidden"], name + ": the empty slot keeps its box and leaves the tab order");
  }
  const [chat, feed] = SHEETS.map(([, css]) => css);
  for (const head of [".fileview-bar {", ".fileview-name {", ".fileview-acts {", ".fileview-bar .fileview-name {", ".fileview-bar .fileview-acts {", ".fileview-size-reset {", ".fileview-size-reset.fileview-size-default {"]) assert.equal(ruleOf(chat, head), ruleOf(feed, head), head + " mirrors exactly");
  const pane = web("files-pane.css").replace(/\/\*[\s\S]*?\*\//g, "");
  assert.doesNotMatch(pane, /\.fileview-bar|\.fileview-acts|\.fileview-name/, "the pane sheet adds nothing to the bar: the wrap is the base rules' (browse-route.test.ts measures the pane at 320 and 360px)");
});

// ── the browser legs ──────────────────────────────────────────────────────────────────────────────
// (1) the sheets over a static page: a real layout at two pane widths and two sizes, both sheets; (2) the REAL module
// bundled into a page (esbuild, as browse-route.test.ts bundles the Files pane): the bar's geometry with the row a
// kernel-answered markdown file shows, a bare <img> line, the code block's measure, the dimmed end, the fixed slot,
// the kept focus, the selection guard. Both skip loudly without playwright or a browser (CI installs none).
let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

const PANE_CSS = web("files-pane.css");
const LONG = "unbreakable".repeat(5);
const SVG = (w: number) => `data:image/svg+xml,${encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="200"><rect width="${w}" height="200" fill="#369"/></svg>`)}`;
const ROWS = Array.from({ length: 3 }, (_, i) => `<tr><td>row ${i} alpha beta gamma delta</td><td>a fairly long cell of prose that keeps going on for a while</td><td>${LONG}</td><td>another long cell with many words in it to widen the table</td><td>five</td><td>six more text here</td></tr>`).join("");
const MD = `<h1 id=h1>Report</h1><p id=p>Prose ${"lorem ipsum ".repeat(40)}</p>
<table id=t><thead><tr><th>one</th><th>two</th><th>three</th><th>four</th><th>five</th><th>six</th></tr></thead><tbody>${ROWS}</tbody></table>
<pre id=pre><code>${"const x = 1; ".repeat(30)}</code></pre>
<pre id=pre2><code>const y = 2;</code></pre>
<p id=lw>${"x".repeat(140)}</p>
<p><img id=im width=900 height=200 src="${SVG(900)}"></p>
<img id=im2 width=1600 height=200 src="${SVG(1600)}">`;
/** The viewer as openFileView builds it, in pane mode (the /files page: styles.css then files-pane.css) or as the modal
 *  over the feed (feed.css alone, the browser over the feed's document). */
const PAGE = (mode: "pane" | "feed") => `<!DOCTYPE html><html><head><meta charset=utf-8><style>${mode === "pane" ? web("styles.css") + "\n" + PANE_CSS : web("feed.css")}</style></head>
<body class="${mode === "pane" ? "fileview-pane" : "fileview-open"}"><div id="romp-fileview"><div class="fileview" id="root"><div class="fileview-bar"><div class="fileview-name"><span class="fileview-dir">/repo/notes-api/docs/</span><span class="fileview-base">report.md</span></div><div class="fileview-acts"><button class="fileview-btn">Rendered</button><button class="fileview-btn">Raw</button><button class="fileview-btn">A−</button><button class="fileview-btn">A+</button><button class="fileview-btn">✕</button></div></div>
<div class="fileview-main"><div class="fileview-body" id="body"><div class="fileview-md" id="md">${MD}</div></div></div></div></div>
<script>/* the viewer's one write (file-view.ts, the width observer): the body's content width, for the pane-wide table's cap */
new ResizeObserver(function (es) { document.getElementById("body").style.setProperty("--fv-body-w", es[es.length - 1].contentRect.width + "px"); }).observe(document.getElementById("body"));</script></body></html>`;
type Lay = { bodyClient: number; gutter: number; bodyScroll: number; docScroll: number; win: number; md: number; p: number; t: number; tClient: number; tScroll: number; pre: number; preScroll: number; preClient: number; pre2: number; lw: number; img: number; img2: number; mdFont: string; h1Font: string; preFont: string };
const layout = (page: any): Promise<Lay> => page.evaluate(async () => {
  await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));   // the width observer's report lands before a frame paints
  const q = (s: string) => document.querySelector(s) as HTMLElement;
  const w = (s: string) => q(s).getBoundingClientRect().width;
  const body = q("#body");
  return { bodyClient: body.clientWidth, gutter: body.offsetWidth - body.clientWidth, bodyScroll: body.scrollWidth, docScroll: document.documentElement.scrollWidth, win: innerWidth,
    md: w("#md"), p: w("#p"), t: w("#t"), tClient: q("#t").clientWidth, tScroll: q("#t").scrollWidth, pre: w("#pre"), preScroll: q("#pre").scrollWidth, preClient: q("#pre").clientWidth, pre2: w("#pre2"), lw: w("#lw"), img: w("#im"), img2: w("#im2"),
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
/** What every cell of the static leg requires: the page is the window, the body does not scroll sideways, and every block
 *  that could widen it (code, the unbreakable string, both pictures) lies inside the column (the root's 18px padding a side). */
const fits = (l: Lay, cell: string) => {
  assert.equal(l.bodyScroll, l.bodyClient, cell + ": the body does not scroll sideways");
  assert.equal(l.docScroll, l.win, cell + ": the page is the window");
  const col = l.bodyClient - 36 + 0.5;
  assert.ok(l.pre <= col && l.pre2 <= col && l.lw <= col && l.img <= col, cell + ": code, the long string and the image paragraph fit the column");
  assert.ok(l.img2 <= col, cell + ": the bare <img> line fits the column too (" + l.img2 + " in " + (l.bodyClient - 36) + "): its own cap outranks the measure");
  assert.ok(l.preScroll <= l.preClient + 1, cell + ": the long code line wraps inside its block");
};

/** The column's width in the root's own ch, and where it sits: the root's content box (its padding is the measure). */
const column = (page: any) => page.evaluate(() => {
  const md = document.getElementById("md")!; const cs = getComputedStyle(md); const r = md.getBoundingClientRect();
  const sp = document.createElement("span"); sp.style.whiteSpace = "nowrap"; sp.textContent = "0".repeat(40); md.appendChild(sp);
  const ch = sp.getBoundingClientRect().width / 40; sp.remove();
  const body = document.getElementById("body")!.getBoundingClientRect();
  const p = document.getElementById("p")!.getBoundingClientRect();
  return { ch, chars: p.width / ch, leftGap: p.left - body.left, rightGap: body.right - p.right - (document.getElementById("body")!.offsetWidth - document.getElementById("body")!.clientWidth), padL: parseFloat(cs.paddingLeft), padR: parseFloat(cs.paddingRight), fontDoc: cs.fontFamily };
});

test("in a browser: the page never widens at 1000 and 420px, at 100% and 150%, in both sheets; the prose and the code blocks keep the measure, an 80ch column centred in the body, and a wide table leaves it evenly up to the body's inset; at 150% the measure and every text size grow together; narrow, the table scrolls in its own box", async (t) => {
  await inBrowser(t, async (browser) => {
    for (const mode of ["pane", "feed"] as const) {
      const page = await browser.newPage({ viewport: { width: 1000, height: 900 } });
      const errors: string[] = [];
      page.on("pageerror", (e: Error) => { errors.push(e.message); });
      await page.setContent(PAGE(mode));
      const inset = mode === "pane" ? 0 : 1000 * 0.05 + 2;                 // the modal is 95% of the pane inside a 1px border
      const step = (n: number) => page.evaluate((n: number) => { document.getElementById("root")!.dataset.fvText = String(n); }, n);
      // 1000px wide, the default size
      let l = await layout(page);
      // the body reserves nothing beside its content: round 1's `scrollbar-gutter: stable` (a table's 100cqi against the column's
      // 100%) was a blank strip beside every body that does not scroll, and went in round 2; the cap reads the body's width off
      // its ResizeObserver instead (file-view-scrollbar-browser.test.ts measures it with the scrollbar drawn; this page runs
      // under playwright's --hide-scrollbars, where a scrollbar takes no room either)
      assert.equal(l.gutter, 0, mode + " @1000: no scrollbar gutter is reserved");
      near(l.bodyClient, 1000 - inset, mode + " @1000: the body is the pane, less the modal's inset");
      fits(l, mode + " @1000/100");
      // the document size: 1.15 times the page's 13px, GitHub's 2em h1 of it, fenced code at 12px (Slice 3 of plans/markdown-viewer.md)
      assert.equal(l.mdFont, "14.95px", mode + ": the document size at 100%, byte for byte"); assert.equal(l.preFont, "12px"); assert.equal(l.h1Font, "29.9px");
      let c = await column(page);
      assert.ok(Math.abs(c.chars - 80) < 0.5, mode + " @1000: the prose measure is 80ch of the root's own font at 100% (" + c.chars.toFixed(1) + "ch of " + c.ch.toFixed(2) + "px)");
      assert.ok(l.p >= 80 * c.ch - 0.5 && l.p < 80 * c.ch + 2, mode + " @1000: ...in pixels, eighty zero glyphs, at most the two pixels the padding's rounding down leaves (" + l.p + " vs " + (80 * c.ch).toFixed(1) + ")");
      assert.ok(Math.abs(c.leftGap - c.rightGap) < 1, mode + " @1000: the column is centred in the body (gaps " + c.leftGap.toFixed(1) + " / " + c.rightGap.toFixed(1) + ")");
      near(c.padL, c.padR, mode + " @1000: the root's inline padding is the measure, both sides alike");
      near(l.pre, l.p, mode + " @1000: a code block keeps the measure"); near(l.pre2, l.p, mode + " @1000: ...a two-line snippet too, no pane-wide box");
      assert.ok(l.t > l.p + 20 && l.t <= l.bodyClient - 36 + 0.5, mode + " @1000: the table leaves the column (" + l.t + " vs " + l.p + "), inside the body's 18px inset");
      // a max-content table is as wide as its content to the layout unit; scrollWidth and clientWidth snap a fractional width
      // two ways (913 vs 912 at the document size, when the unbreakable cell was 66 characters), so the pixel of slack the code
      // block's check has applies here too. The unbreakable cell is 55 characters: the table's min-content (the unbreakable cell
      // plus each column's longest word) has to fit the body less its 36px inset
      assert.ok(l.tScroll <= l.tClient + 1, mode + " @1000: room enough, so the table does not scroll (" + l.tScroll + " in " + l.tClient + ")");
      near(l.md, l.bodyClient, mode + " @1000: the root is the body's width");
      assert.ok(l.img <= l.p + 0.5 && l.lw <= l.p + 0.5 && l.img2 <= l.p + 0.5, mode + ": both pictures and an unbreakable string stay in the measure");
      // 150%: the one property, read by every text size and the measure
      await step(150);
      l = await layout(page);
      fits(l, mode + " @1000/150");
      assert.equal(l.mdFont, "22.425px", mode + " @150%: the prose"); assert.equal(l.h1Font, "44.85px", mode + " @150%: the heading, 2em of it"); assert.equal(l.preFont, "18px", mode + " @150%: fenced code");
      c = await column(page);
      assert.ok(l.p >= Math.min(80 * c.ch, l.bodyClient - 36) - 0.5 && l.p < Math.min(80 * c.ch, l.bodyClient - 36) + 2, mode + " @150%: the measure is 80ch of the grown glyph, capped by the pane (" + l.p + ")");
      assert.ok(Math.abs(c.leftGap - c.rightGap) < 1, mode + " @150%: still centred");
      near(l.pre, l.p, mode + " @150%: the code block's measure grows with the prose's");
      // 420px, a phone-wide pane, at BOTH sizes (the leg once shrank the pane at 150% only)
      await page.setViewportSize({ width: 420, height: 900 });
      for (const n of [100, 150]) {
        await step(n);
        l = await layout(page);
        fits(l, mode + " @420/" + n);
        near(l.bodyClient, 420 - (mode === "pane" ? 0 : 420 * 0.05 + 2), mode + " @420/" + n + ": the body is the pane, less the modal's inset");
        near(l.t, l.bodyClient - 36, mode + " @420/" + n + ": the table is the column");
        assert.ok(l.tScroll > l.tClient + 100, mode + " @420/" + n + ": the unbreakable cell scrolls inside the table's own box (" + l.tScroll + " in " + l.tClient + ")");
        near(l.p, l.bodyClient - 36, mode + " @420/" + n + ": the prose follows the pane below its measure");
        near(l.img2, l.bodyClient - 36, mode + " @420/" + n + ": the 1600px banner is the column");
      }
      assert.deepEqual(errors, [], "no script error in the page");
      await page.close();
    }
  });
});

/** The two surfaces that wear the bar's classes OUTSIDE a bar, as their modules build them: the file browser's bar
 *  (file-browse.ts: #romp-filebrowse, the backdrop > .filebrowse, the card > fb-bar > fb-crumbs + fileview-acts > [Hidden, close];
 *  the id and the class are two elements since the 2026-09-04 redress) under a deep crumb trail, in each document's sheets; and, in the pane document, the Files pane's Recent row (files.ts: fs-row > fileview-name + fileview-sess). */
const CRUMBS = ["/", "repo", "notes-api", "services", "api", "internal", "handlers", "v2", "tests", "fixtures", "golden"];
const OUTSIDE_PAGE = (mode: "pane" | "chat" | "feed") => `<!DOCTYPE html><html><head><meta charset=utf-8><style>${mode === "feed" ? web("feed.css") : mode === "pane" ? web("styles.css") + "\n" + PANE_CSS : web("styles.css")}</style></head>
<body class="filebrowse-open${mode === "pane" ? " fileview-pane" : ""}"><div id="romp-filebrowse"><div class="filebrowse"><div class="fb-bar"><div class="fb-crumbs" id="fb-crumbs">${CRUMBS.map((c, i) => (i ? '<span class="fb-crumb-sep">/</span>' : "") + '<span class="fb-crumb">' + c + "</span>").join("")}</div><div class="fileview-acts"><button class="fileview-btn" id="hid">Hidden</button><button class="fileview-btn fileview-close" id="close">✕</button></div></div><div class="fb-list"></div></div></div>
${mode === "pane" ? '<div id="files-empty"><div class="fs-recent"><div class="fs-row" id="row"><div class="fileview-name"><span class="fileview-dir">/repo/notes-api/services/api/docs/</span><span class="fileview-base">report.md</span></div><span class="fileview-sess" id="sess">web</span></div></div></div>' : ""}</body></html>`;

test("in a browser: the file browser's bar stays one line at 320, 360, 480 and 1000px in every document, its two buttons holding their width while the crumb trail ellipsizes; the Files pane's Recent row keeps its session chip inside at 200, 240 and 320px", async (t) => {
  // round 2: round 1's base rules reached both surfaces (Hidden and the close button stacked at 320-480px under a long
  // trail; a 200px pane's Recent row overflowed under the name's 12em and pushed its chip past the row)
  await inBrowser(t, async (browser) => {
    for (const mode of ["pane", "chat", "feed"] as const) {
      const page = await browser.newPage({ viewport: { width: 1000, height: 600 } });
      const errors: string[] = [];
      page.on("pageerror", (e: Error) => { errors.push(e.message); });
      await page.setContent(OUTSIDE_PAGE(mode));
      const barOf = () => page.evaluate(() => {
        const bar = document.querySelector(".fb-bar") as HTMLElement; const crumbs = document.getElementById("fb-crumbs")!; const acts = document.querySelector(".fb-bar .fileview-acts") as HTMLElement;
        const hid = document.getElementById("hid")!.getBoundingClientRect(); const close = document.getElementById("close")!.getBoundingClientRect();
        return { barH: bar.getBoundingClientRect().height, hidTop: hid.top, closeTop: close.top, closeLeft: close.left, closeRight: close.right, acts: acts.getBoundingClientRect().width,
          crumbsClient: crumbs.clientWidth, crumbsScroll: crumbs.scrollWidth, barOver: bar.scrollWidth - bar.clientWidth, wrap: getComputedStyle(acts).flexWrap, win: innerWidth };
      });
      const wide = await barOf();
      assert.equal(wide.win, 1000);
      assert.equal(wide.hidTop, wide.closeTop, mode + " @1000: Hidden and the close button share a line");
      for (const w of [480, 360, 320]) {
        await page.setViewportSize({ width: w, height: 600 });
        const m = await barOf();
        const cell = mode + " @" + w;
        assert.equal(m.hidTop, m.closeTop, cell + ": Hidden and the close button share a line");
        near(m.barH, wide.barH, cell + ": the bar is the height it has at 1000px (one line, not two)");
        near(m.acts, wide.acts, cell + ": the action row holds its width");
        assert.equal(m.wrap, "nowrap", cell + ": the row does not wrap");
        assert.ok(m.closeLeft >= 0 && m.closeRight <= w + 0.5, cell + `: the close button lies inside the pane: x ${m.closeLeft}-${m.closeRight}`);
        assert.ok(m.crumbsScroll > m.crumbsClient, cell + ": the crumb trail is what gives up room, ellipsized (" + m.crumbsScroll + " in " + m.crumbsClient + ")");
        assert.equal(m.barOver, 0, cell + ": the bar overflows nothing");
      }
      if (mode === "pane") {
        for (const w of [320, 240, 200]) {
          await page.setViewportSize({ width: w, height: 600 });
          const r = await page.evaluate(() => {
            const row = document.getElementById("row")!; const rr = row.getBoundingClientRect(); const sess = document.getElementById("sess")!.getBoundingClientRect();
            const name = row.querySelector(".fileview-name") as HTMLElement;
            return { rowOver: row.scrollWidth - row.clientWidth, rowLeft: rr.left, rowRight: rr.right, sessLeft: sess.left, sessRight: sess.right,
              nameMin: getComputedStyle(name).minWidth, base: (name.querySelector(".fileview-base") as HTMLElement).getBoundingClientRect().width };
          });
          const cell = "pane, the Recent row @" + w;
          assert.equal(r.rowOver, 0, cell + ": the row overflows nothing");
          assert.ok(r.sessLeft >= r.rowLeft - 0.5 && r.sessRight <= r.rowRight + 0.5, cell + `: the session chip lies inside the row: x ${r.sessLeft}-${r.sessRight} in ${r.rowLeft}-${r.rowRight}`);
          assert.equal(r.nameMin, "0px", cell + ": the name shrinks freely, no 12em floor outside the bar");
          assert.ok(r.base > 40, cell + ": the filename keeps its width (" + r.base + "): only the directory gives up room");
        }
      }
      assert.deepEqual(errors, [], mode + ": no script error");
      await page.close();
    }
  });
});

// ── the real module in a page ──────────────────────────────────────────────────────────────────────
const UI = path.resolve(process.cwd(), "..", "ui", "webview");
let viewerBundle: string | null = null;
function bundleViewer(): string {
  if (viewerBundle) return viewerBundle;
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    stdin: { contents: 'export { initFileView, openFileView, closeFileView, registerFileViewAction } from "./file-view"; export { paintRendered, paintRaw } from "./anchor-map";', resolveDir: UI, loader: "ts", sourcefile: "text-size-leg.ts" },
    bundle: true, write: false, format: "iife", globalName: "FV", platform: "browser", target: "es2020",
    nodePaths: [path.resolve(process.cwd(), "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent",
  });
  viewerBundle = r.outputFiles[0].text as string;
  return viewerBundle;
}
const ORIGIN = "http://notes-api.test";   // a synthetic origin: the viewer's localStorage needs one (about:blank's is opaque and throws)
// a README with every figure form marked emits: a bare <img> line (a CommonMark HTML block, so a DIRECT child of the root),
// an image paragraph, a centred figure; a two-line snippet and a long code line; a small table
// a short markdown file for the Raw view's rows: an empty row (no text node) between a heading and a two-line snippet
const SNIPPET = ROOT + "/docs/snippet.md";
const SNIPPET_MD = "# Notes\n\ndef main():\n    return 1\n\nDone.\n";
// a short markdown file for the Rendered view's hard break: a paragraph of two lines around a <br> (two trailing spaces)
const BREAK = ROOT + "/docs/break.md";
const BREAK_MD = "# Notes\n\nfirst line  \nsecond line of prose here\n\nDone.\n";
// a note holding a script element and `</script>` in a code span: an HTML tokenizer ends script data at the first
// `</script` whatever the JavaScript around it, so the file table is inlined with `<` as `\u003c` (scriptLiteral, as the
// shared leg page does; file-view-leg-page-browser.test.ts pins the shared page's escape)
const SCRIPTED = ROOT + "/docs/scripted.md";
const SCRIPTED_MD = "# Report\n\nA paragraph before the script.\n\n<script>alert(1)</script>\n\n`</script>` inside a code span, and `<!--` before it.\n\nAfter the script.\n";
const README = `<img src="${SVG(1600)}" width="1600" height="200">\n\n# Report\n\nProse ${"lorem ipsum ".repeat(60)}\n\n![plot](${SVG(1600)})\n\n<div align="center"><img src="${SVG(1600)}" width="1600" height="200"></div>\n\n\`\`\`\nconst x = 1;\nconst y = 2;\n\`\`\`\n\n\`\`\`\n${"const z = 1; ".repeat(20)}\n\`\`\`\n\n| run | p95 |\n| --- | --- |\n| a | 120 |\n`;
/** The file table the page inlines (scriptLiteral: `<` as `\u003c`, so SCRIPTED's `</script>` cannot end the script). */
const DOCS: Record<string, string> = { [REPORT]: README, [SNIPPET]: SNIPPET_MD, [BREAK]: BREAK_MD, [SCRIPTED]: SCRIPTED_MD };
/** The page a viewer surface is: the chat modal (styles.css), the feed modal (feed.css) or the Files pane (styles.css +
 *  files-pane.css under body.fileview-pane), the bundle, a fetch that serves the README with the kernel's headers, and two
 *  registered actions standing in for Comments and the GitHub unit (both mount once the kernel answers; the row is measured
 *  with them, its widest ordinary form). The probe action counts the seam's paints and selection hooks. Opened with ?hl=1,
 *  a third action paints a comment highlight over the first paragraph the panel's way (file-comments.ts paintAll: every
 *  onRendered unwraps the marks, normalizes the text and re-wraps them through the real painter). A test may install
 *  window.__disturb, which the probe runs from its onRendered with the body: a stand-in for a paint that moves a text node
 *  the selection stands in. */
const REAL_PAGE = (mode: "chat" | "feed" | "pane") => `<!DOCTYPE html><html><head><meta charset=utf-8><style>${mode === "feed" ? web("feed.css") : mode === "pane" ? web("styles.css") + "\n" + PANE_CSS : web("styles.css")}</style></head>
<body class="${mode === "pane" ? "fileview-pane" : ""}"><script>${bundleViewer()}</script><script>
window.__docs = ${scriptLiteral(DOCS)};
window.fetch = async function (url) {
  url = String(url);
  if (url.indexOf("/version") === 0) return new Response(JSON.stringify({ fileEditing: true }), { headers: { "Content-Type": "application/json" } });
  if (url.indexOf("/sessions") === 0) return new Response("[]", { headers: { "Content-Type": "application/json" } });
  var m = /[?&]path=([^&]*)/.exec(url); var p = m ? decodeURIComponent(m[1]) : "";
  var text = window.__docs[p];
  if (text === undefined) return new Response("no such file: " + p, { status: 404 });
  return new Response(text, { status: 200, headers: { "Content-Type": "text/plain; charset=utf-8", "X-Romp-Mtime-Ns": "${MT}", "X-Romp-Text-Utf8": "1" } });
};
window.__paints = 0; window.__sels = 0;
FV.initFileView(function () {});
FV.registerFileViewAction({ id: "probe", mount: function (ctx) {
  ctx.onRendered(function () { window.__paints++; if (window.__disturb) window.__disturb(ctx.body()); }); ctx.onSelection(function () { window.__sels++; });
  var b = document.createElement("button"); b.className = "fileview-btn"; b.type = "button"; b.textContent = "Comments"; return b; } });
FV.registerFileViewAction({ id: "gh", mount: function () {
  var s = document.createElement("span"); s.className = "fileview-gh";
  var b = document.createElement("button"); b.className = "fileview-btn"; b.type = "button"; b.textContent = "GitHub"; b.disabled = true;
  var why = document.createElement("span"); why.className = "fileview-gh-why"; why.textContent = "not committed yet";
  s.appendChild(b); s.appendChild(why); return s; } });
window.__hl = location.search.indexOf("hl=1") >= 0; window.__marks = 0; window.__afterMarks = null;
FV.registerFileViewAction({ id: "marks", mount: function (ctx) {
  window.__repaintMarks = function () {
    var body = ctx.body(); var src = ctx.text(); var rendered = ctx.mode() === "rendered";
    var root = body.querySelector(rendered ? ".fileview-md" : "code.hljs");
    if (src === null || !root) return 0;
    Array.prototype.slice.call(body.querySelectorAll(".fc-hl")).forEach(function (n) { var p = n.parentNode; while (n.firstChild) p.insertBefore(n.firstChild, n); p.removeChild(n); p.normalize(); });
    var spec = window.__hlSpec || { find: "lorem ipsum", len: 60 };   // the passage: the README's first paragraph unless the test chose one
    var at = src.indexOf(spec.find);
    if (at < 0) return 0;
    var range = { start: at, end: at + spec.len };
    var out = rendered ? FV.paintRendered(root, src, range, "fc-hl", { act: "fcopen", id: "c1" }) : FV.paintRaw(root, src, range, "fc-hl", { act: "fcopen", id: "c1" });
    return out ? out.length : 0;
  };
  // __afterMarks: the browser's own record of the selection once the repaint has moved the mark's text node, before the
  // viewer puts the ends back (the hooks run inside fireRenderedKeepingSelection, the restore after them)
  if (window.__hl) ctx.onRendered(function () { window.__marks = window.__repaintMarks(); var s = getSelection(); window.__afterMarks = s ? s.toString() : null; });
  return null; } });
</script></body></html>`;
type Real = { page: any; errors: string[] };
type HlSpec = { find: string; len: number };
/** Opens the README rendered, or `doc` (in the Raw view when `raw`: the Rendered/Raw key is written first, the way a
 *  person's earlier choice would stand). `hl` paints a highlight through the marks action on every paint: over the
 *  README's first paragraph when `true`, over the passage a spec names. */
async function openReal(browser: any, mode: "chat" | "feed" | "pane", width: number, size?: number, hl: boolean | HlSpec = false, doc?: { path: string; raw: boolean }): Promise<Real> {
  const page = await browser.newPage({ viewport: { width, height: 900 } });
  const errors: string[] = [];
  page.on("pageerror", (e: Error) => { errors.push(e.message); });
  await page.route((u: URL) => u.href.startsWith(ORIGIN), (route: any) => route.fulfill({ status: 200, contentType: "text/html", body: REAL_PAGE(mode) }));
  await page.goto(ORIGIN + (hl ? "/?hl=1" : "/"));
  if (typeof hl === "object") await page.evaluate((spec: HlSpec) => { (window as any).__hlSpec = spec; }, hl);
  if (size !== undefined) await page.evaluate((s: number) => { localStorage.setItem("romp:fileviewTextSize", String(s)); }, size);
  if (doc?.raw) await page.evaluate(() => { localStorage.setItem("romp:fileviewFmt", JSON.stringify({ md: "raw" })); });
  await page.evaluate((p: string) => { (window as any).FV.openFileView(p, null); }, doc ? doc.path : REPORT);
  if (doc?.raw) await page.waitForFunction(() => !!document.querySelector(".fileview-body .fv-cl"), null, { timeout: 10000 });
  else if (doc) await page.waitForFunction(() => !!document.querySelector(".fileview-md > p"), null, { timeout: 10000 });
  else await page.waitForFunction(() => !!document.querySelector(".fileview-md > pre"), null, { timeout: 10000 });
  return { page, errors };
}
const SEL = { down: 'button[aria-label="Smaller text"]', up: 'button[aria-label="Larger text"]', reset: ".fileview-size-reset", root: ".fileview" };
const rectOf = (page: any, sel: string) => page.evaluate((s: string) => { const r = (document.querySelector(s) as HTMLElement).getBoundingClientRect(); return { left: r.left, right: r.right, top: r.top, bottom: r.bottom, width: r.width }; }, sel);
const sizeOf = (page: any) => page.evaluate((s: string) => (document.querySelector(s) as HTMLElement).dataset.fvText, SEL.root);

test("the real-module page inlines its file table with `<` escaped: two script elements whatever the notes hold, the table parsing back to the same texts (a bare JSON.stringify let a note's `</script>` end the harness script before the fetch stub)", () => {
  const count = (s: string, re: RegExp) => (s.match(re) || []).length;
  const bundle = bundleViewer();
  for (const mode of ["chat", "feed", "pane"] as const) {
    const html = REAL_PAGE(mode);
    // the bundle's own text is subtracted: esbuild output may hold the strings
    assert.equal(count(html, /<script[\s>]/g) - count(bundle, /<script[\s>]/g), 2, mode + ": two script elements open");
    assert.equal(count(html, /<\/script/g) - count(bundle, /<\/script/g), 2, mode + ": and two close, the note's own `</script>` escaped");
    const m = /\nwindow\.__docs = (.*);\nwindow\.fetch = /.exec(html);
    assert.ok(m, mode + ": the table is inlined on its line");
    assert.ok(!/<|-->/.test(m![1]), mode + ": no `<` or `-->` in the literal");
    assert.deepEqual(JSON.parse(m![1]), DOCS, mode + ": the literal reads back as the table");
  }
});

test("in a browser, the real module: a note holding a script element and `</script>` in a code span opens through the page's fetch stub, the sanitizer dropping the script", async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openReal(browser, "chat", 900, undefined, false, { path: SCRIPTED, raw: false });
    const seen = await page.evaluate(([p, text]: [string, string]) => ({
      stubbed: String(window.fetch).indexOf("__docs") >= 0,
      table: (window as any).__docs[p] === text,
      first: (document.querySelector(".fileview-md p") as HTMLElement).textContent,
      scripts: document.querySelectorAll(".fileview-md script").length,
      paints: (window as any).__paints as number,
    }), [SCRIPTED, SCRIPTED_MD]);
    assert.equal(seen.stubbed, true, "the fetch stub survived the inlined table");
    assert.equal(seen.table, true, "the note in the table, byte for byte");
    assert.equal(seen.first, "A paragraph before the script.", "the note's own first paragraph, not the harness page");
    assert.equal(seen.scripts, 0, "no script element under the rendered note");
    assert.ok(seen.paints >= 1, "the seam painted");
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});

test("in a browser, the real module: a bare <img> line, an image paragraph and a centred figure fit the column at 380 and 640px, at 100% and 200%, wrapped by the figure layer or not; wide, the pictures and the code blocks keep the measure", async (t) => {
  await inBrowser(t, async (browser) => {
    for (const mode of ["pane", "feed"] as const) for (const width of [380, 640]) for (const size of [100, 200]) {
      const cell = `${mode} ${width}px @${size}%`;
      const { page, errors } = await openReal(browser, mode, width, size);
      const m = await page.evaluate(() => {
        const body = document.querySelector(".fileview-body") as HTMLElement;
        const imgs = Array.from(document.querySelectorAll(".fileview-md img")) as HTMLElement[];
        return { bodyClient: body.clientWidth, bodyScroll: body.scrollWidth, docScroll: document.documentElement.scrollWidth, win: innerWidth,
          imgs: imgs.map((i) => ({ w: i.getBoundingClientRect().width, parent: i.parentElement!.className || i.parentElement!.tagName, maxW: getComputedStyle(i).maxWidth })) };
      });
      assert.equal(await sizeOf(page), String(size), cell + ": the stored step is on the root");
      assert.equal(m.imgs.length, 3, cell + ": the three figure forms rendered");
      assert.equal(m.imgs[0].parent, "fileview-md", cell + ": the bare <img> line is a direct child of the root (marked's HTML block)");
      assert.equal(m.bodyScroll, m.bodyClient, cell + ": the body does not scroll sideways (" + m.bodyScroll + " in " + m.bodyClient + ")");
      assert.equal(m.docScroll, m.win, cell + ": the page is the window");
      for (const i of m.imgs) assert.ok(i.w <= m.bodyClient - 36 + 0.5, cell + ": a " + i.parent + " picture fits the column: " + i.w + " in " + (m.bodyClient - 36));
      near(m.imgs[0].w, m.imgs[1].w, cell + ": the bare line and the image paragraph lay out alike");
      // the figure layer's wrapper (the comments panel open, or a region comment on the picture) around the bare line: the
      // same width, so opening the panel moves no figure (the flap the review measured: 860px closed, the column open)
      const m2 = await page.evaluate(() => {
        const md = document.querySelector(".fileview-md") as HTMLElement;
        const img = md.querySelector(":scope > img") as HTMLElement;
        const before = img.getBoundingClientRect().width;
        const wrap = document.createElement("span"); wrap.className = "fc-imgwrap"; img.replaceWith(wrap); wrap.appendChild(img);
        const body = document.querySelector(".fileview-body") as HTMLElement;
        return { before, after: img.getBoundingClientRect().width, bodyClient: body.clientWidth, bodyScroll: body.scrollWidth };
      });
      near(m2.before, m2.after, cell + ": wrapped, the picture keeps its width");
      assert.equal(m2.bodyScroll, m2.bodyClient, cell + ": ...and the body still does not scroll");
      assert.deepEqual(errors, [], cell + ": no script error");
      await page.close();
    }
    // a wide pane at 100%: prose, code and every picture share the measure; nothing spans the 1400px
    const { page, errors } = await openReal(browser, "pane", 1400, 100);
    const c = await page.evaluate(() => {
      const w = (e: Element) => e.getBoundingClientRect().width;
      return { p: w(document.querySelector(".fileview-md > p")!), pres: (Array.from(document.querySelectorAll(".fileview-md > pre")) as HTMLElement[]).map((p) => ({ w: w(p), scroll: p.scrollWidth, client: p.clientWidth })),
        imgs: Array.from(document.querySelectorAll(".fileview-md img")).map(w), md: w(document.querySelector(".fileview-md")!) };
    });
    assert.ok(c.md > 1300, "the root is fluid to the pane: " + c.md);
    const ch = await page.evaluate(() => { const md = document.querySelector(".fileview-md") as HTMLElement; const sp = document.createElement("span"); sp.style.whiteSpace = "nowrap"; sp.textContent = "0".repeat(40); md.appendChild(sp); const w = sp.getBoundingClientRect().width / 40; sp.remove(); return w; });
    assert.ok(c.p >= 80 * ch - 0.5 && c.p < 80 * ch + 2, "the prose measure at 1400px: 80ch of the root's own font, at most two pixels over from the rounding (" + (c.p / ch).toFixed(1) + "ch, " + c.p + "px)");
    assert.equal(c.pres.length, 2);
    for (const pre of c.pres) { near(pre.w, c.p, "a code block keeps the measure: no 1364px box for a two-line snippet"); assert.ok(pre.scroll <= pre.client + 1, "...and a long line wraps inside it"); }
    for (const i of c.imgs) assert.ok(i <= c.p + 0.5 && i > c.p - 60, "a picture takes the measure at most, in every form the markdown used: " + i);
    assert.deepEqual(errors, []);
    await page.close();
  });
});

test("in a browser, the real module: the bar wraps, so the close button and every action stay inside the card at 380, 420, 480 and 600px in the chat and feed modals, with the kernel-answered row, at the default and with the readout showing", async (t) => {
  await inBrowser(t, async (browser) => {
    for (const mode of ["chat", "feed"] as const) for (const width of [380, 420, 480, 600]) for (const size of [100, 115]) {
      const cell = `${mode} ${width}px @${size}%`;
      const { page, errors } = await openReal(browser, mode, width, size);
      const m = await page.evaluate(() => {
        const root = document.querySelector(".fileview") as HTMLElement;
        const bar = root.querySelector(".fileview-bar") as HTMLElement;
        // the buttons that render: a hidden one, or one inside a hidden unit (the module's own GitHub action, mounted and
        // waiting for a kernel that never answers here), has no box; the readout's empty slot (visibility) keeps its box
        const btns = (Array.from(bar.querySelectorAll(".fileview-acts .fileview-btn")) as HTMLElement[]).filter((b) => b.getClientRects().length > 0);
        const box = (e: Element) => { const b = e.getBoundingClientRect(); return { left: b.left, right: b.right, top: b.top, bottom: b.bottom }; };
        return { labels: btns.map((b) => b.textContent), root: box(root), minLeft: Math.min(...btns.map((b) => box(b).left)), maxRight: Math.max(...btns.map((b) => box(b).right)),
          close: box(bar.querySelector(".fileview-close")!), main: box(root.querySelector(".fileview-main")!), barOver: bar.scrollWidth - bar.clientWidth,
          name: (bar.querySelector(".fileview-name") as HTMLElement).getBoundingClientRect().width, nameFont: parseFloat(getComputedStyle(bar.querySelector(".fileview-name")!).fontSize) };
      });
      for (const l of ["Rendered", "Raw", "A−", "A+", "Edit", "Comments", "GitHub", "Download", "Copy path", "✕"]) assert.ok(m.labels.includes(l), cell + ": the row measured is the kernel-answered one, with " + l + ": " + m.labels.join(","));
      assert.ok(m.close.left >= m.root.left - 0.5 && m.close.right <= m.root.right + 0.5, cell + `: the close button lies inside the card: x ${m.close.left}-${m.close.right} in ${m.root.left}-${m.root.right}`);
      assert.ok(m.minLeft >= m.root.left - 0.5 && m.maxRight <= m.root.right + 0.5, cell + `: every action lies inside the card: x ${m.minLeft}-${m.maxRight} in ${m.root.left}-${m.root.right}`);
      assert.ok(m.close.bottom <= m.main.top + 0.5, cell + ": the wrapped actions sit above the body, not over it");
      assert.equal(m.barOver, 0, cell + ": the bar overflows nothing");
      assert.ok(m.name >= 12 * m.nameFont - 1, cell + ": the path keeps its 12em: " + m.name);
      assert.deepEqual(errors, [], cell + ": no script error");
      await page.close();
    }
  });
});

test("in a browser, the real module: A− and A+ never move when the readout appears (a second press at the same point steps again); an end is dimmed, hover-inert and keeps the keyboard focus; a press on the bar with a passage selected runs no selection hook", async (t) => {
  await inBrowser(t, async (browser) => {
    for (const mode of ["pane", "feed"] as const) {
      const { page, errors } = await openReal(browser, mode, 900);
      const rects = () => page.evaluate((q: typeof SEL) => {
        const r = (s: string) => { const b = (document.querySelector(s) as HTMLElement).getBoundingClientRect(); return { left: b.left, top: b.top, width: b.width }; };
        return { down: r(q.down), up: r(q.up), reset: r(q.reset), vis: getComputedStyle(document.querySelector(q.reset)!).visibility, text: document.querySelector(q.reset)!.textContent };
      }, SEL);
      const r0 = await rects();
      assert.equal(await sizeOf(page), "100"); assert.equal(r0.vis, "hidden", mode + ": the slot is empty at the default");
      assert.ok(r0.reset.width > 40, mode + ": ...and has its width already: " + r0.reset.width);
      const at = { x: r0.down.left + 6, y: r0.down.top + 6 };   // a point inside A−, kept for the second press
      await page.mouse.click(at.x, at.y);
      let r1 = await rects();
      assert.equal(await sizeOf(page), "90"); assert.equal(r1.vis, "visible", mode + ": the readout appears"); assert.equal(r1.text, "90%");
      near(r1.down.left, r0.down.left, mode + ": A− did not move"); near(r1.up.left, r0.up.left, mode + ": A+ did not move"); near(r1.reset.left, r0.reset.left, mode + ": the slot was there all along");
      await page.mouse.click(at.x, at.y);
      assert.equal(await sizeOf(page), "80", mode + ": the second press at the same point is a second step, not the reset");
      r1 = await rects();
      const w80 = r1.reset.width;
      for (let i = 0; i < 12; i++) await page.mouse.click(r0.up.left + 6, r0.up.top + 6);
      const r2 = await rects();
      assert.equal(await sizeOf(page), "200"); assert.equal(r2.text, "200%");
      near(r2.reset.width, w80, mode + ": the slot is one width for '80%' and '200%'"); near(r2.down.left, r0.down.left, mode + ": A− still where it was"); near(r2.up.left, r0.up.left, mode + ": A+ too");
      // the end: aria-disabled and focusable, dimmed, default cursor, hover inert, a press changes and paints nothing
      const dress = () => page.evaluate((q: typeof SEL) => {
        const b = document.querySelector(q.up) as HTMLButtonElement; const c = getComputedStyle(b); const d = getComputedStyle(document.querySelector(q.down) as HTMLElement);
        return { opacity: c.opacity, cursor: c.cursor, color: c.color, border: c.borderColor, bg: c.backgroundColor, restColor: d.color, restBorder: d.borderColor, aria: b.getAttribute("aria-disabled"), disabled: b.disabled };
      }, SEL);
      let d = await dress();
      assert.equal(d.aria, "true", mode + ": A+ says the end"); assert.equal(d.disabled, false, mode + ": ...without the disabled property");
      assert.equal(d.opacity, "0.55", mode + ": dimmed"); assert.equal(d.cursor, "default", mode + ": no pointer cursor");
      await page.mouse.move(r2.up.left + 6, r2.up.top + 6);
      // the button was hovered in the accent when the twelfth press made it the end, and .fileview-btn transitions its
      // colours over 0.12s: wait for the transition's end (the settled value is the assertion; a live hover never settles there)
      await page.waitForFunction((q: typeof SEL) => {
        const c = getComputedStyle(document.querySelector(q.up)!); const d = getComputedStyle(document.querySelector(q.down)!);
        return c.color === d.color && c.borderColor === d.borderColor && c.backgroundColor === "rgba(0, 0, 0, 0)";
      }, SEL, { timeout: 2000 }).catch(() => { /* the assertions below say what it settled at */ });
      d = await dress();
      assert.equal(d.color, d.restColor, mode + ": hovered, the end keeps the rest colour, not the accent"); assert.equal(d.border, d.restBorder, mode + ": ...and the rest border"); assert.equal(d.bg, "rgba(0, 0, 0, 0)", mode + ": ...and no wash");
      const paints0 = await page.evaluate(() => (window as any).__paints);
      await page.mouse.click(r2.up.left + 6, r2.up.top + 6);
      assert.equal(await sizeOf(page), "200", mode + ": a press on the end changes nothing");
      assert.equal(await page.evaluate(() => (window as any).__paints), paints0, mode + ": ...and paints nothing");
      // the keyboard: Enter on a focused A− three times from the default reaches the end with the focus still on it
      await page.mouse.click(r2.reset.left + 6, r2.reset.top + 6);
      assert.equal(await sizeOf(page), "100", mode + ": the readout resets");
      await page.focus(SEL.down);
      for (let i = 0; i < 3; i++) await page.keyboard.press("Enter");
      const f = await page.evaluate((q: typeof SEL) => ({ focused: document.activeElement === document.querySelector(q.down), aria: document.querySelector(q.down)!.getAttribute("aria-disabled"), active: document.activeElement!.tagName }), SEL);
      assert.equal(await sizeOf(page), "70"); assert.equal(f.aria, "true");
      assert.equal(f.focused, true, mode + ": the focus stays on A− at the end (a disabled button would have dropped it to " + f.active + ")");
      await page.keyboard.press("Enter");
      assert.equal(await sizeOf(page), "70", mode + ": a fourth Enter does nothing, under a ring on a dimmed button");
      // a passage selected by a real drag, then a press on A+: the size steps, the hooks stay quiet. The drag starts 2px into
      // the paragraph: at certain sub-pixel offsets from a fractional left edge (4px into the first glyph at 70% here, 5 and 12px
      // at 100%) headless Chromium leaves the drag's selection collapsed, a hit-test rounding quirk of the harness's mouse
      // events, not the viewer's (measured 2026-09-08, Slice 3 of plans/markdown-viewer.md, when the centred column moved the
      // edge to 183.97px); 2px selects at every size and surface measured
      const pBox = await rectOf(page, ".fileview-md > p");
      await page.mouse.move(pBox.left + 2, pBox.top + 8); await page.mouse.down(); await page.mouse.move(pBox.left + 220, pBox.top + 8, { steps: 5 }); await page.mouse.up();
      const s1 = await page.evaluate(() => ({ sels: (window as any).__sels, chars: getSelection()!.toString().length }));
      assert.ok(s1.chars > 0, mode + ": a passage is selected (" + s1.chars + " chars)"); assert.equal(s1.sels, 1, mode + ": the lift over the body ran the selection hooks once");
      const up = await rectOf(page, SEL.up);
      await page.mouse.click(up.left + 6, up.top + 6);
      const s2 = await page.evaluate(() => ({ sels: (window as any).__sels, chars: getSelection()!.toString().length }));
      assert.equal(await sizeOf(page), "80", mode + ": the step happened");
      assert.equal(s2.sels, 1, mode + ": the press on A+ ran no hook (no re-seed, no re-fetch)"); assert.ok(s2.chars > 0, mode + ": the selection stands");
      // the overshoot (round 2): a drag that starts in the body and is released over the bar's path (selecting back to the
      // file's first line) settles like any other; the round-1 guard read the whole bar and swallowed it
      // the standing selection goes first: a mousedown on selected text starts a text drag-and-drop, not a selection
      await page.evaluate(() => { getSelection()!.removeAllRanges(); document.addEventListener("mouseup", (e) => { (window as any).__lastUp = (e.target as Element).className; }, true); });
      const p2 = await rectOf(page, ".fileview-md > p"); const nameBox = await rectOf(page, ".fileview-name");
      await page.mouse.move(p2.left + 2, p2.top + 8); await page.mouse.down(); await page.mouse.move(nameBox.left + 30, (nameBox.top + nameBox.bottom) / 2, { steps: 6 }); await page.mouse.up();
      const s3 = await page.evaluate(() => ({ sels: (window as any).__sels, chars: getSelection()!.toString().length, lastUp: (window as any).__lastUp as string, anchorInBody: !!document.querySelector(".fileview-body")!.contains(getSelection()!.anchorNode) }));
      assert.match(s3.lastUp, /fileview-(dir|base|name)/, mode + ": the lift landed on the bar's path: " + s3.lastUp);
      assert.ok(s3.chars > 0 && s3.anchorInBody, mode + ": a passage anchored in the body is selected (" + s3.chars + " chars)");
      assert.equal(s3.sels, 2, mode + ": released over the bar's path, the drag settles: the hooks ran");
      await page.mouse.click(up.left + 6, up.top + 6);
      const s4 = await page.evaluate(() => ({ sels: (window as any).__sels, lastUp: (window as any).__lastUp as string }));
      assert.equal(await sizeOf(page), "90", mode + ": A+ stepped again"); assert.match(s4.lastUp, /fileview-btn/);
      assert.equal(s4.sels, 2, mode + ": ...and the press on the control ran no hook");
      assert.deepEqual(errors, [], mode + ": no script error");
      await page.close();
    }
  });
});

test("in a browser, the real module: a selection overlapping a comment highlight survives a size step and a pane resize, forwards and backwards; the panel's repaint alone (unwrap, normalize, re-wrap) truncates it", async (t) => {
  // round 2, against the base: file-comments.ts answers onRendered with paintAll, which re-wraps every highlight, and a
  // selection with an end inside a mark lost that end with the mark's node (58 characters to 21 after one A+, 45 to 7
  // after a 900 to 800px resize). The viewer keeps the selection's ends as text offsets across the pass.
  await inBrowser(t, async (browser) => {
    for (const mode of ["pane", "feed"] as const) {
      const { page, errors } = await openReal(browser, mode, 900, undefined, true);
      assert.ok((await page.evaluate(() => (window as any).__marks as number)) >= 1, mode + ": the marks action painted a highlight over the first paragraph");
      /** Select from 5 characters into the highlight's own text node to 30 characters into the text after it, or the reverse. */
      const pick = (backwards: boolean) => page.evaluate((backwards: boolean) => {
        const mark = document.querySelector(".fileview-md .fc-hl") as HTMLElement;
        const inMark = mark.firstChild as Text; const after = mark.nextSibling as Text;
        if (!inMark || inMark.nodeType !== 3 || !after || after.nodeType !== 3 || after.data.length < 40) throw new Error("the paragraph's shape around the mark: " + (inMark && inMark.nodeType) + " / " + (after && after.nodeType));
        const sel = getSelection()!;
        if (backwards) sel.setBaseAndExtent(after, 30, inMark, 5); else sel.setBaseAndExtent(inMark, 5, after, 30);
        (window as any).__m0 = mark;
        return sel.toString();
      }, backwards);
      const read = () => page.evaluate(() => {
        const sel = getSelection()!; const m0 = (window as any).__m0 as Element; const a = sel.anchorNode; const f = sel.focusNode;
        const back = !!a && !!f && (a === f ? sel.anchorOffset > sel.focusOffset : !!(a.compareDocumentPosition(f) & Node.DOCUMENT_POSITION_PRECEDING));
        return { text: sel.toString(), back, oldMarkGone: !m0.isConnected, marks: document.querySelectorAll(".fileview-md .fc-hl").length, paints: (window as any).__paints as number };
      });
      const text0 = await pick(false);
      assert.ok(text0.length > 60 && text0.indexOf("lorem") >= 0, mode + ": a selection from inside the mark past its end: " + text0.length + " chars");
      // the mechanism, bare: the marks action's own repaint (unwrap, normalize, re-wrap), with no viewer around it
      await page.evaluate(() => { (window as any).__marks = (window as any).__repaintMarks(); });
      const bare = await read();
      assert.ok(bare.oldMarkGone && bare.marks >= 1, mode + ": the repaint replaced the mark");
      assert.notEqual(bare.text, text0, mode + ": ...and the selection did not survive it on its own (" + bare.text.length + " of " + text0.length + " chars): the round-2 measurement, reproduced");
      // the same repaint through the viewer's step: the selection stands, every character of it
      assert.equal(await pick(false), text0);
      let up = await rectOf(page, SEL.up);
      await page.mouse.click(up.left + 6, up.top + 6);
      assert.equal(await sizeOf(page), "115", mode + ": the step happened");
      let r = await read();
      assert.ok(r.oldMarkGone && r.marks >= 1, mode + ": the step's paint re-wrapped the highlight");
      assert.equal(r.text, text0, mode + ": the selection over the highlight survives the step, the same " + text0.length + " characters");
      assert.equal(r.back, false, mode + ": ...forwards, as made");
      // the pane's width: the frame's repaint keeps it too
      const paints0 = r.paints;
      await page.evaluate(() => { (window as any).__m0 = document.querySelector(".fileview-md .fc-hl"); });
      await page.setViewportSize({ width: 800, height: 900 });
      await page.waitForFunction((n: number) => (window as any).__paints > n, paints0, { timeout: 5000 });
      r = await read();
      assert.ok(r.oldMarkGone && r.marks >= 1, mode + ": the resize's paint re-wrapped the highlight");
      assert.equal(r.text, text0, mode + ": the selection survives the resize");
      // backwards (the anchor after the focus, a drag made leftwards): the direction is kept across the step
      assert.equal(await pick(true), text0);
      up = await rectOf(page, SEL.up);
      await page.mouse.click(up.left + 6, up.top + 6);
      assert.equal(await sizeOf(page), "130");
      r = await read();
      assert.equal(r.text, text0, mode + ": a backwards selection survives the step too");
      assert.equal(r.back, true, mode + ": ...with its direction kept (the anchor after the focus)");
      assert.deepEqual(errors, [], mode + ": no script error");
      await page.close();
    }
  });
});

test("in a browser, the real module: a selection holding a picture alone (anchor (p,0), focus (p,1) around the img, a drag across a figure) keeps both ends across a size step and a pane resize while the paint re-wraps a highlight elsewhere", async (t) => {
  // round 3: both ends of such a selection have ONE text offset, and putting them back from it collapsed the selection
  // after every reflow, though the paint touched nothing near the figure and the browser had kept it. The viewer now
  // leaves a selection the paint left standing alone, and never rebuilds one whose two offsets coincide.
  await inBrowser(t, async (browser) => {
    for (const mode of ["pane", "feed"] as const) {
      const { page, errors } = await openReal(browser, mode, 900, undefined, true);
      assert.ok((await page.evaluate(() => (window as any).__marks as number)) >= 1, mode + ": a highlight stands over the first paragraph");
      const pick = () => page.evaluate(() => {
        const img = document.querySelector(".fileview-md > p > img") as HTMLElement; const p = img.parentElement as HTMLElement;
        if (p.childNodes.length !== 1) throw new Error("the image paragraph holds " + p.childNodes.length + " nodes");
        (window as any).__p = p; (window as any).__m0 = document.querySelector(".fileview-md .fc-hl");
        getSelection()!.setBaseAndExtent(p, 0, p, 1);
        return getSelection()!.toString();
      });
      const read = () => page.evaluate(() => {
        const sel = getSelection()!; const p = (window as any).__p as Node; const m0 = (window as any).__m0 as Element;
        return { collapsed: sel.isCollapsed, ranges: sel.rangeCount, anchor: sel.anchorNode === p ? sel.anchorOffset : "elsewhere", focus: sel.focusNode === p ? sel.focusOffset : "elsewhere",
          text: sel.toString(), oldMarkGone: !m0.isConnected, marks: document.querySelectorAll(".fileview-md .fc-hl").length, paints: (window as any).__paints as number };
      });
      assert.equal(await pick(), "", mode + ": a selection around the picture holds no text");
      let r = await read();
      assert.deepEqual([r.collapsed, r.anchor, r.focus], [false, 0, 1], mode + ": ...and is not collapsed: the figure is what it holds");
      const up = await rectOf(page, SEL.up);
      await page.mouse.click(up.left + 6, up.top + 6);
      assert.equal(await sizeOf(page), "115", mode + ": the step happened");
      r = await read();
      assert.ok(r.oldMarkGone && r.marks >= 1, mode + ": the step's paint re-wrapped the highlight");
      assert.deepEqual([r.collapsed, r.anchor, r.focus, r.text], [false, 0, 1, ""], mode + ": the selection around the picture keeps both ends across the step (a restore from one offset collapsed it)");
      const paints0 = r.paints;
      await page.evaluate(() => { (window as any).__m0 = document.querySelector(".fileview-md .fc-hl"); });
      await page.setViewportSize({ width: 800, height: 900 });
      await page.waitForFunction((n: number) => (window as any).__paints > n, paints0, { timeout: 5000 });
      r = await read();
      assert.ok(r.oldMarkGone && r.marks >= 1, mode + ": the resize's paint re-wrapped the highlight");
      assert.deepEqual([r.collapsed, r.anchor, r.focus, r.text], [false, 0, 1, ""], mode + ": ...and the selection keeps both ends across the resize");
      assert.deepEqual(errors, [], mode + ": no script error");
      await page.close();
    }
  });
});

test("in a browser, the real module, the Raw view: a drag from a row's first column to the end of a later row, and a triple-clicked row, copy byte-identical text after a size step and a pane resize; a paint that wraps the end's text node still puts the start back at its row, not the end of the row above", async (t) => {
  // round 3: the rows (.fv-cl) carry no newline text and an empty row has no text node, so a start at a row's first
  // column has the same offset as the end of the last non-empty row above it, and the restore's boundary rule put it
  // there: the copied text gained a leading newline and lost its trailing one, and the anchor moved lines up.
  await inBrowser(t, async (browser) => {
    for (const mode of ["pane", "feed"] as const) {
      const { page, errors } = await openReal(browser, mode, 900, undefined, false, { path: SNIPPET, raw: true });
      const rows = await page.evaluate(() => Array.from(document.querySelectorAll(".fileview-body .fv-cl")).map((r) => ({ text: r.textContent, textNodes: document.createTreeWalker(r, NodeFilter.SHOW_TEXT).nextNode() ? 1 : 0 })));
      assert.deepEqual(rows.map((r: any) => r.text), ["# Notes", "", "def main():", "    return 1", "", "Done."], mode + ": the six rows");
      assert.equal(rows[1].textNodes, 0, mode + ": the empty row holds no text node, so the third row's first column shares its offset with the first row's end");
      const read = () => page.evaluate(() => {
        const sel = getSelection()!; const rows = Array.from(document.querySelectorAll(".fileview-body .fv-cl"));
        const rowOf = (n: Node | null) => rows.findIndex((r) => !!n && r.contains(n));
        return { text: sel.toString(), anchorRow: rowOf(sel.anchorNode), focusRow: rowOf(sel.focusNode), anchorOffset: sel.anchorOffset, focusOffset: sel.focusOffset, paints: (window as any).__paints as number };
      });
      const rect = (i: number) => page.evaluate((i: number) => { const r = (document.querySelectorAll(".fileview-body .fv-cl .fv-ct")[i] as HTMLElement).getBoundingClientRect(); return { left: r.left, right: r.right, top: r.top, bottom: r.bottom }; }, i);
      const survives = async (what: string, before: { text: string; anchorRow: number; focusRow: number; anchorOffset: number; focusOffset: number }) => {
        const up = await rectOf(page, SEL.up);
        const size0 = Number(await sizeOf(page));
        await page.mouse.click(up.left + 6, up.top + 6);
        assert.ok(Number(await sizeOf(page)) > size0, mode + ": the step happened");
        let r = await read();
        assert.equal(r.text, before.text, mode + ": " + what + " copies the same bytes after the step");
        assert.deepEqual([r.anchorRow, r.anchorOffset, r.focusRow, r.focusOffset], [before.anchorRow, before.anchorOffset, before.focusRow, before.focusOffset], mode + ": " + what + " keeps both ends where they were (no restore moved the anchor a row up)");
        const paints0 = r.paints; const w = (await page.viewportSize()).width;
        await page.setViewportSize({ width: w - 100, height: 900 });
        await page.waitForFunction((n: number) => (window as any).__paints > n, paints0, { timeout: 5000 });
        r = await read();
        assert.equal(r.text, before.text, mode + ": " + what + " copies the same bytes after the resize");
        assert.deepEqual([r.anchorRow, r.anchorOffset, r.focusRow, r.focusOffset], [before.anchorRow, before.anchorOffset, before.focusRow, before.focusOffset], mode + ": " + what + " keeps both ends across the resize");
      };
      // a drag from the first column of "def main():" to past the end of "    return 1"
      const r3 = await rect(2); const r4 = await rect(3);
      await page.mouse.move(r3.left + 1, (r3.top + r3.bottom) / 2); await page.mouse.down(); await page.mouse.move(r4.right - 2, (r4.top + r4.bottom) / 2, { steps: 6 }); await page.mouse.up();
      const drag = await read();
      assert.equal(drag.text, "def main():\n    return 1", mode + ": the drag selected the two rows");
      assert.equal(drag.anchorRow, 2, mode + ": ...anchored in the third row");
      await survives("the drag", drag);
      // a triple-click on the third row
      await page.evaluate(() => { getSelection()!.removeAllRanges(); });
      const r3b = await rect(2);
      await page.mouse.click(r3b.left + 20, (r3b.top + r3b.bottom) / 2, { clickCount: 3 });
      const triple = await read();
      assert.equal(triple.text, "def main():\n", mode + ": the triple-click selected the row, its newline included");
      assert.deepEqual([triple.anchorRow, triple.anchorOffset, triple.focusRow, triple.focusOffset], [2, 0, 3, 0], mode + ": ...from the row's first column to the next row's (the end has the offset of the row's own end)");
      await survives("the triple-clicked row", triple);
      // the restore itself, forced: a paint that wraps the end's text node in a new element (a mark painted over it: the
      // node is removed and the wrapper inserted at its index, so the browser's live range ends before the wrapper) costs
      // the browser's selection that end, and the viewer puts both ends back from their offsets. The start's offset is
      // also the first row's end; it must land at the third row's first column.
      await page.evaluate(() => {
        const rows = document.querySelectorAll(".fileview-body .fv-cl");
        const first = (r: Element) => document.createTreeWalker(r, NodeFilter.SHOW_TEXT).nextNode() as Text;
        const last = (r: Element) => { const w = document.createTreeWalker(r, NodeFilter.SHOW_TEXT); let t: Node | null = null; for (let n = w.nextNode(); n; n = w.nextNode()) t = n; return t as Text; };
        const t3 = first(rows[2]); const t4 = last(rows[3]);
        getSelection()!.setBaseAndExtent(t3, 0, t4, t4.data.length);
        (window as any).__disturb = (body: HTMLElement) => {
          const t = last(body.querySelectorAll(".fv-cl")[3]); const s = document.createElement("span");
          t.replaceWith(s); s.appendChild(t);
          (window as any).__disturbed = getSelection()!.toString();   // the browser's own record, once its end's node moved
        };
      });
      const forced = await read();
      assert.equal(forced.text, "def main():\n    return 1", mode + ": the drag's shape, set directly");
      const up = await rectOf(page, SEL.up);
      await page.mouse.click(up.left + 6, up.top + 6);
      const r = await read();
      const disturbed = await page.evaluate(() => (window as any).__disturbed as string);
      assert.ok(typeof disturbed === "string" && disturbed !== forced.text && !disturbed.endsWith("return 1"), mode + ": the paint cost the browser's selection its end: " + JSON.stringify(disturbed));
      assert.equal(r.text, "def main():\n    return 1", mode + ": put back from offsets, the selection copies the same bytes (the start at the third row, not the first row's end)");
      assert.deepEqual([r.anchorRow, r.anchorOffset, r.focusRow], [2, 0, 3], mode + ": the anchor is the third row's first column");
      await page.evaluate(() => { (window as any).__disturb = null; });
      assert.deepEqual(errors, [], mode + ": no script error");
      await page.close();
    }
  });
});

test("in a browser, the real module: an end on a text-less line boundary keeps its side through a forced restore — a drag begun after a row's last glyph (Raw) or before a <br> (Rendered) into a highlight keeps its leading newline and its anchor line; a triple-clicked row (Raw) or line (Rendered) whose whole text is highlighted from column 0 keeps its trailing newline; a drag from the end of a highlighted word to the next row's first column (Raw), the newline alone, keeps it; plain prose, a collapsed caret and no selection are left as they are", async (t) => {
  // round 4: the Raw view's rows carry no newline text and a <br> is none either, so the end of one line's text and the
  // first column of the next share ONE offset. Round 3 chose the side by the end's role, and a forced restore (the other
  // end inside a re-wrapped highlight) moved a START that sat after a row's last glyph to the next row's first character
  // (the leading newline lost, the anchor a line down) and an END at a row's first column (a triple-click's) to the end of
  // the row above (the trailing newline lost). Each end now keeps its own node and offset and goes back to them when the
  // node came through the paint; only an end whose node is gone is mapped, and by the side it sat on.
  // round 5: a selection of the newline alone, from the end of a highlight's text (the row's last word, after a prefix)
  // to the next row's first column, has ONE offset for both ends like the picture-only selection, and round 3's guard
  // against rebuilding such a pair skipped its restore too: after the repaint moved the start out of the mark's node,
  // Chrome showed and copied the highlighted word with the newline. The guard now fires only for a selection holding no
  // text; this one holds "\n", and the side bits put its start back at the new mark's end.
  await inBrowser(t, async (browser) => {
    for (const mode of ["pane", "feed"] as const) {
      const read = (page: any) => page.evaluate(() => {
        const sel = getSelection()!; const a = sel.anchorNode; const f = sel.focusNode;
        const rows = Array.from(document.querySelectorAll(".fileview-body .fv-cl"));
        const rowOf = (n: Node | null) => rows.findIndex((r) => !!n && r.contains(n));
        const kind = (n: Node | null) => (!n ? "none" : n.nodeType === 3 ? "text" : (n as Element).tagName.toLowerCase());
        // the Rendered view's line: 1 at or before the <br>'s start, 2 after it, 0 outside its paragraph
        const br = document.querySelector(".fileview-md br");
        const lineOf = (n: Node | null, o: number) => { if (!br || !n || !br.parentNode!.contains(n)) return 0; const p = br.parentNode!; const r = document.createRange(); r.setStart(n, o); r.setEnd(n, o); return r.comparePoint(p, Array.prototype.indexOf.call(p.childNodes, br)) >= 0 ? 1 : 2; };
        const mark = document.querySelector(".fileview-body .fc-hl");
        return { text: sel.toString(), collapsed: sel.isCollapsed, ranges: sel.rangeCount,
          anchorKind: kind(a), anchorOffset: sel.anchorOffset, anchorRow: rowOf(a), anchorLine: lineOf(a, sel.anchorOffset), anchorInMark: !!a && !!mark && mark.contains(a),
          focusKind: kind(f), focusOffset: sel.focusOffset, focusRow: rowOf(f), focusLine: lineOf(f, sel.focusOffset), focusInMark: !!f && !!mark && mark.contains(f),
          afterMarks: (window as any).__afterMarks as string | null, marks: document.querySelectorAll(".fileview-body .fc-hl").length, paints: (window as any).__paints as number };
      });
      type Shape = Awaited<ReturnType<typeof read>>;
      const ends = (r: Shape) => [r.anchorKind, r.anchorOffset, r.anchorRow, r.anchorLine, r.focusKind, r.focusOffset, r.focusRow, r.focusLine];
      /** A step and then a resize, each paint re-wrapping the highlight the selection ends in: the browser's own record
       *  loses that end (__afterMarks, read inside the paint, differs), and the viewer's restore brings the selection
       *  back to the same bytes with both ends exactly where they were. */
      const forced = async (page: any, what: string, before: Shape) => {
        for (const trigger of ["step", "resize"] as const) {
          const paints0 = (await read(page)).paints;
          if (trigger === "step") {
            const up = await rectOf(page, SEL.up); const size0 = Number(await sizeOf(page));
            await page.mouse.click(up.left + 6, up.top + 6);
            assert.ok(Number(await sizeOf(page)) > size0, mode + ": " + what + ": the step happened");
          } else {
            const w = (await page.viewportSize()).width;
            await page.setViewportSize({ width: w - 100, height: 900 });
          }
          await page.waitForFunction((n: number) => (window as any).__paints > n, paints0, { timeout: 5000 });
          const r = await read(page);
          assert.ok(r.marks >= 1, mode + ": " + what + ": the " + trigger + "'s paint re-wrapped the highlight");
          assert.ok(typeof r.afterMarks === "string" && r.afterMarks !== before.text, mode + ": " + what + ": the " + trigger + "'s repaint cost the browser's selection an end (the restore was forced): " + JSON.stringify(r.afterMarks) + " vs " + JSON.stringify(before.text));
          assert.equal(r.text, before.text, mode + ": " + what + " copies the same bytes after the " + trigger);
          assert.deepEqual(ends(r), ends(before), mode + ": " + what + " keeps both ends exactly where they were after the " + trigger);
        }
      };
      const rowRect = (page: any, i: number) => page.evaluate((i: number) => { const r = (document.querySelectorAll(".fileview-body .fv-cl")[i] as HTMLElement).getBoundingClientRect(); return { left: r.left, right: r.right, top: r.top, bottom: r.bottom }; }, i);
      const markRect = (page: any) => rectOf(page, ".fileview-body .fc-hl");
      const mid = (r: { top: number; bottom: number }) => (r.top + r.bottom) / 2;

      // (1) Raw: a drag begun after the last glyph of "def main():" into the highlighted "    return 1" below
      {
        const { page, errors } = await openReal(browser, mode, 900, undefined, { find: "    return 1", len: 12 }, { path: SNIPPET, raw: true });
        assert.ok((await read(page)).marks >= 1, mode + ": a highlight stands over the fourth row");
        const r2 = await rowRect(page, 2); const m = await markRect(page);
        await page.mouse.move(r2.right - 10, mid(r2)); await page.mouse.down(); await page.mouse.move(m.left + m.width / 2, mid(m), { steps: 6 }); await page.mouse.up();
        const drag = await read(page);
        assert.ok(drag.text.startsWith("\n    ") && drag.text.length > 5, mode + ": the drag begins with the row break: " + JSON.stringify(drag.text));
        assert.deepEqual([drag.anchorKind, drag.anchorOffset, drag.anchorRow, drag.focusRow, drag.focusInMark], ["text", 11, 2, 3, true], mode + ": anchored at the end of the third row's text, the focus inside the highlight");
        await forced(page, "the drag from the row's end", drag);
        assert.deepEqual(errors, [], mode + ": no script error");
        await page.close();
      }
      // (2) Raw: a triple-click on "def main():", highlighted whole from column 0; the end is the next row's first column
      {
        const { page, errors } = await openReal(browser, mode, 900, undefined, { find: "def main():", len: 11 }, { path: SNIPPET, raw: true });
        assert.ok((await read(page)).marks >= 1, mode + ": a highlight stands over the third row");
        const m = await markRect(page);
        await page.mouse.click(m.left + 20, mid(m), { clickCount: 3 });
        const triple = await read(page);
        assert.equal(triple.text, "def main():\n", mode + ": the triple-click selected the row, its newline included");
        assert.deepEqual([triple.anchorOffset, triple.anchorRow, triple.anchorInMark, triple.focusOffset, triple.focusRow], [0, 2, true, 0, 3], mode + ": from the highlight's first character to the next row's first column");
        await forced(page, "the triple-clicked row", triple);
        assert.deepEqual(errors, [], mode + ": no script error");
        await page.close();
      }
      // (3) Rendered: a drag begun after "first line", before the <br>, into the highlighted "second line" below it
      {
        const { page, errors } = await openReal(browser, mode, 900, undefined, { find: "second line", len: 11 }, { path: BREAK, raw: false });
        const shape = await page.evaluate(() => { const p = document.querySelector(".fileview-md br")!.parentElement!; return Array.from(p.childNodes).map((n) => (n.nodeType === 3 ? "text" : (n as Element).tagName.toLowerCase())); });
        assert.deepEqual(shape, ["text", "br", "mark", "text"], mode + ": the paragraph: the first line, the break, the highlighted start of the second line, its rest");
        const first = await page.evaluate(() => { const r = document.createRange(); r.selectNodeContents(document.querySelector(".fileview-md br")!.parentElement!.firstChild!); const b = r.getBoundingClientRect(); return { left: b.left, right: b.right, top: b.top, bottom: b.bottom }; });
        const m = await markRect(page);
        await page.mouse.move(first.right + 40, mid(first)); await page.mouse.down(); await page.mouse.move(m.left + m.width / 2, mid(m), { steps: 6 }); await page.mouse.up();
        const drag = await read(page);
        assert.ok(drag.text.startsWith("\nsec") && drag.text.length > 3, mode + ": the drag begins with the break: " + JSON.stringify(drag.text));
        assert.deepEqual([drag.anchorLine, drag.focusLine, drag.focusInMark], [1, 2, true], mode + ": anchored on the first line, the focus inside the highlight on the second");
        await forced(page, "the drag from before the <br>", drag);
        assert.deepEqual(errors, [], mode + ": no script error");
        await page.close();
      }
      // (4) Rendered: a triple-click on "first line", highlighted whole; the end is the second line's start, past the <br>.
      // Then, on the same page, the shapes the restore must leave alone.
      {
        const { page, errors } = await openReal(browser, mode, 900, undefined, { find: "first line", len: 10 }, { path: BREAK, raw: false });
        const m = await markRect(page);
        await page.mouse.click(m.left + 10, mid(m), { clickCount: 3 });
        const triple = await read(page);
        assert.equal(triple.text, "first line\n", mode + ": the triple-click selected the line, its break included");
        assert.deepEqual([triple.anchorOffset, triple.anchorLine, triple.anchorInMark, triple.focusLine], [0, 1, true, 2], mode + ": from the highlight's first character to the second line's start");
        await forced(page, "the triple-clicked line", triple);
        // plain prose away from the highlight: the paint leaves it standing, and the viewer does not touch it (the same node)
        const step = async () => { const paints0 = (await read(page)).paints; const up = await rectOf(page, SEL.up); await page.mouse.click(up.left + 6, up.top + 6); await page.waitForFunction((n: number) => (window as any).__paints > n, paints0, { timeout: 5000 }); };
        const same = () => page.evaluate(() => { const s = getSelection()!; return s.anchorNode === (window as any).__n && s.focusNode === (window as any).__n; });
        await page.evaluate(() => { const done = Array.from(document.querySelectorAll(".fileview-md p")).pop()!.firstChild as Text; (window as any).__n = done; getSelection()!.setBaseAndExtent(done, 1, done, 4); });
        let r = await read(page);
        assert.equal(r.text, "one", mode + ": plain prose selected");
        await step();
        r = await read(page);
        assert.deepEqual([r.text, r.anchorOffset, r.focusOffset, r.afterMarks, await same()], ["one", 1, 4, "one", true], mode + ": plain prose stands through the step, in its own node, untouched");
        // a collapsed caret: nothing to keep, nothing moved
        await page.evaluate(() => { const done = (window as any).__n as Text; getSelection()!.setBaseAndExtent(done, 2, done, 2); });
        await step();
        r = await read(page);
        assert.deepEqual([r.collapsed, r.anchorOffset, r.focusOffset, await same()], [true, 2, 2, true], mode + ": a collapsed caret stays where it was");
        // no selection at all
        await page.evaluate(() => { getSelection()!.removeAllRanges(); });
        await step();
        r = await read(page);
        assert.deepEqual([r.ranges, r.marks >= 1], [0, true], mode + ": no selection: none after the paint either, the highlight re-wrapped");
        assert.deepEqual(errors, [], mode + ": no script error");
        await page.close();
      }
      // (5) Raw: a drag from the end of the highlighted "main():" (the third row's last text, after its "def " prefix) to
      // the fourth row's first column: the newline alone, both ends on one offset (round 5)
      {
        const { page, errors } = await openReal(browser, mode, 900, undefined, { find: "main():", len: 7 }, { path: SNIPPET, raw: true });
        assert.ok((await read(page)).marks >= 1, mode + ": a highlight stands over the third row's last word");
        const r2 = await rowRect(page, 2);
        const c3 = await page.evaluate(() => { const r = (document.querySelectorAll(".fileview-body .fv-cl")[3].querySelector(".fv-ct") as HTMLElement).getBoundingClientRect(); return { left: r.left, top: r.top, bottom: r.bottom }; });
        await page.mouse.move(r2.right - 10, mid(r2)); await page.mouse.down(); await page.mouse.move(c3.left + 1, mid(c3), { steps: 6 }); await page.mouse.up();
        const drag = await read(page);
        assert.equal(drag.text, "\n", mode + ": the drag holds the row break alone");
        assert.deepEqual([drag.anchorKind, drag.anchorOffset, drag.anchorRow, drag.anchorInMark, drag.focusKind, drag.focusOffset, drag.focusRow], ["text", 7, 2, true, "span", 0, 3], mode + ": anchored at the end of the highlight's text, the focus at the next row's first column (its cell, before the text)");
        await forced(page, "the newline from the highlight's end", drag);
        assert.deepEqual(errors, [], mode + ": no script error");
        await page.close();
      }
    }
  });
});

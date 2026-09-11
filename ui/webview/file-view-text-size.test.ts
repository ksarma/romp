// The viewer's text size, and a rendered-markdown layout that follows the viewer's width. A− and A+ in the title
// bar step every text view through a fixed table of sizes (70 to 200 percent): a markdown file's Rendered and Raw
// views, every other text file's code view, the SVG Source view, and a document opened from a link on the
// dashboard's own address. The percentage between them, shown once the size is off the default, is the reset;
// Ctrl/Cmd + wheel over the body steps the same table. The chosen step rides the viewer root as data-fv-text and
// the sheets turn it into the one property every text size reads (--fv-scale); it persists per browser like the
// Rendered/Raw choice. Run FOR REAL over openFileView and openUrlView against a DOM stand-in (a tree, attributes
// and dataset, bubbling events, a small selector matcher, localStorage, a fetch answering the kernel's headers),
// plus pins over both sheets and an optional browser leg (headless Chromium through a child driver, skipped where
// no browser is installed; CI installs none). Synthetic fixtures only.
// This fork carries more than the offer landed: the seam's reflow contract (a step and the body's width fire onRendered as a
// reflow through the stand-in's ResizeObserver and requestAnimationFrame), the Files pane's Recent row, and the real module
// bundled into a page (the bar's geometry with a kernel-answered row, the readout's fixed slot, the kept focus, the selection
// guard, a selection across the comments panel's highlight, the page's escape of a note holding `</script>`: scriptLiteral),
// plus the stand-in's projection (ui/test-dom-shim.ts). The stand-in hides its edges with the shared rule (hideEdges).
import { test, type TestContext } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { marked } from "marked";   // the browser leg renders a synthetic task list through the real marked for mdBlock's task stamp
import { inspect } from "node:util";
import { assertHiddenEvent, hideEdges, sameNodes, staysEnumerable } from "../test-dom-shim";
import type { FileViewActionCtx } from "./file-view";
import { scriptLiteral } from "./real-viewer-leg";

const requireCjs = createRequire(__filename);

const web = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const VIEW = web("file-view.ts");
const PANEL = web("file-comments.ts");
const SHEETS: ReadonlyArray<readonly [string, string]> = [["styles.css", web("styles.css")], ["feed.css", web("feed.css")]];

// ── a DOM stand-in: the members the viewer touches, with a tree and bubbling events ─────────────────
class Ev {
  target: El | null = null;
  currentTarget: El | null = null;
  defaultPrevented = false;
  stopped = false;
  ctrlKey: boolean; metaKey: boolean; deltaY: number; deltaMode: number; key: string;
  constructor(public type: string, init: { ctrlKey?: boolean; metaKey?: boolean; deltaY?: number; deltaMode?: number; key?: string } = {}) {
    this.ctrlKey = !!init.ctrlKey; this.metaKey = !!init.metaKey;
    this.deltaY = init.deltaY ?? 0; this.deltaMode = init.deltaMode ?? 0; this.key = init.key ?? "";
    hideEdges(this);
  }
  preventDefault(): void { this.defaultPrevented = true; }
  stopPropagation(): void { this.stopped = true; }
}
type Listener = (ev: Ev) => void;
type Part = { tag: string; id: string; classes: string[]; attrs: Array<[string, string | null]>; known: boolean };
const kebab = (k: string) => k.replace(/[A-Z]/g, (c) => "-" + c.toLowerCase());
/** One compound selector (`tag#id.class[attr="v"]`); a shape the matcher does not know fits nothing. */
function part(s: string): Part {
  const m = /^([a-zA-Z][\w-]*|\*)?(#[\w-]+)?((?:\.[\w-]+)*)((?:\[[^\]]+\])*)$/.exec(s);
  if (!m) return { tag: "", id: "", classes: [], attrs: [], known: false };
  const attrs: Array<[string, string | null]> = [];
  let known = true;
  for (const a of m[4].match(/\[[^\]]+\]/g) || []) {
    const am = /^\[([\w-]+)(?:="([^"]*)")?\]$/.exec(a);
    if (am) attrs.push([am[1], am[2] ?? null]); else known = false;
  }
  return { tag: (m[1] || "").toLowerCase(), id: m[2] ? m[2].slice(1) : "", classes: (m[3].match(/\.[\w-]+/g) || []).map((c) => c.slice(1)), attrs, known };
}
class El {
  parentNode: El | null = null;
  childNodes: Array<El | string> = [];
  title = ""; hidden = false; type = ""; disabled = false; tabIndex = -1; innerHTML = "";
  href = ""; target = ""; rel = ""; spellcheck = true; value = ""; src = ""; alt = ""; download = "";
  style: Record<string, string> = {};
  onclick: ((ev: Ev) => void) | null = null;
  private attrs = new Map<string, string>();
  private listeners: Array<{ type: string; fn: Listener; once: boolean; passive: boolean | undefined }> = [];
  constructor(public tagName: string) { hideEdges(this); }   // the edges (parentNode, childNodes, the listener table) hide with the shared rule
  get id(): string { return this.attrs.get("id") ?? ""; }
  set id(v: string) { this.attrs.set("id", v); }
  get className(): string { return this.attrs.get("class") ?? ""; }
  set className(v: string) { this.attrs.set("class", v.trim()); }
  private get classes(): string[] { return this.className.split(/\s+/).filter(Boolean); }
  classList = {
    add: (...c: string[]) => { const s = new Set(this.classes); for (const x of c) s.add(x); this.className = [...s].join(" "); },
    remove: (...c: string[]) => { const s = new Set(this.classes); for (const x of c) s.delete(x); this.className = [...s].join(" "); },
    toggle: (c: string, on?: boolean): boolean => { const want = on ?? !this.classes.includes(c); if (want) this.classList.add(c); else this.classList.remove(c); return want; },
    contains: (c: string) => this.classes.includes(c),
  };
  /** data-* through dataset, the way the viewer writes its root attribute (camelCase to kebab-case, as the DOM does). */
  dataset: Record<string, string | undefined> = new Proxy({} as Record<string, string | undefined>, {
    get: (_, k) => this.attrs.get("data-" + kebab(String(k))),
    set: (_, k, v) => { this.attrs.set("data-" + kebab(String(k)), String(v)); return true; },
    has: (_, k) => this.attrs.has("data-" + kebab(String(k))),
    deleteProperty: (_, k) => { this.attrs.delete("data-" + kebab(String(k))); return true; },
  });
  get textContent(): string { return this.childNodes.map((c) => (typeof c === "string" ? c : c.textContent)).join(""); }
  set textContent(v: string) { this.replaceChildren(...(v === "" ? [] : [v])); }
  /** Element children only, in order. */
  get children(): El[] { return this.childNodes.filter((c): c is El => c instanceof El); }
  get isConnected(): boolean { let n: El = this; while (n.parentNode) n = n.parentNode; return n === docBody; }
  private adopt(c: El | string): void { if (c instanceof El) { c.remove(); c.parentNode = this; } }
  appendChild<T extends El>(c: T): T { this.adopt(c); this.childNodes.push(c); return c; }
  prepend(...cs: Array<El | string>): void { for (const c of cs) this.adopt(c); this.childNodes.unshift(...cs); }
  insertBefore<T extends El>(c: T, ref: El | null): T {
    if (ref && !this.childNodes.includes(ref)) throw new Error("insertBefore: the reference node is not a child of this node");
    this.adopt(c);
    const i = ref ? this.childNodes.indexOf(ref) : -1;
    if (i < 0) this.childNodes.push(c); else this.childNodes.splice(i, 0, c);
    return c;
  }
  replaceChildren(...cs: Array<El | string>): void {
    for (const c of this.childNodes) if (c instanceof El) c.parentNode = null;
    this.childNodes = [];
    for (const c of cs) this.adopt(c);
    this.childNodes = [...cs];
  }
  remove(): void {
    const p = this.parentNode;
    if (!p) return;
    const i = p.childNodes.indexOf(this);
    if (i >= 0) p.childNodes.splice(i, 1);
    this.parentNode = null;
  }
  contains(n: El | null): boolean { for (let x: El | null = n; x; x = x.parentNode) if (x === this) return true; return false; }
  setAttribute(k: string, v: string): void { this.attrs.set(k, v); }
  removeAttribute(k: string): void { this.attrs.delete(k); }
  getAttribute(k: string): string | null { return this.attrs.get(k) ?? null; }
  hasAttribute(k: string): boolean { return this.attrs.has(k); }
  addEventListener(type: string, fn: Listener, opts?: boolean | { once?: boolean; passive?: boolean; capture?: boolean }): void {
    this.listeners.push({ type, fn, once: typeof opts === "object" && !!opts.once, passive: typeof opts === "object" ? opts.passive : undefined });
  }
  /** The `passive` option each listener of `type` on this element was registered with (undefined where none was given). */
  passiveOf(type: string): Array<boolean | undefined> { return this.listeners.filter((l) => l.type === type).map((l) => l.passive); }
  removeEventListener(type: string, fn: Listener): void { this.listeners = this.listeners.filter((l) => !(l.type === type && l.fn === fn)); }
  /** Bubble `ev` from this element to the root: each element's listeners in registration order, then its onclick for a click. */
  dispatchEvent(ev: Ev): boolean {
    ev.target = this;
    for (let n: El | null = this; n && !ev.stopped; n = n.parentNode) {
      ev.currentTarget = n;
      for (const l of n.listeners.slice()) {
        if (l.type !== ev.type) continue;
        if (l.once) n.listeners = n.listeners.filter((x) => x !== l);
        l.fn.call(n, ev);
      }
      if (ev.type === "click" && n.onclick) n.onclick(ev);
    }
    return !ev.defaultPrevented;
  }
  click(): void { this.dispatchEvent(new Ev("click")); }
  focus(): void { doc.activeElement = this; }
  scrollIntoView(): void { /* inert */ }
  private fits(p: Part): boolean {
    if (!p.known) return false;
    if (p.tag && p.tag !== "*" && p.tag !== this.tagName.toLowerCase()) return false;
    if (p.id && p.id !== this.id) return false;
    if (!p.classes.every((c) => this.classes.includes(c))) return false;
    return p.attrs.every(([a, v]) => this.attrs.has(a) && (v === null || this.attrs.get(a) === v));
  }
  /** Comma groups of descendant chains, each link a compound. */
  matches(sel: string): boolean {
    return sel.split(",").some((group) => {
      const chain = group.trim().split(/\s+/).filter(Boolean).map(part);
      if (!chain.length || !this.fits(chain[chain.length - 1])) return false;
      let k = chain.length - 2;
      for (let a = this.parentNode; a && k >= 0; a = a.parentNode) if (a.fits(chain[k])) k--;
      return k < 0;
    });
  }
  closest(sel: string): El | null { for (let n: El | null = this; n; n = n.parentNode) if (n.matches(sel)) return n; return null; }
  querySelectorAll(sel: string): El[] {
    const out: El[] = [];
    const walk = (n: El) => { for (const c of n.children) { if (c.matches(sel)) out.push(c); walk(c); } };
    walk(this);
    return out;
  }
  querySelector(sel: string): El | null { return this.querySelectorAll(sel)[0] ?? null; }
}
const docBody = new El("body");
const docKeys: Listener[] = [];                  // the viewer's document keydown handlers, one per open
const doc = {
  body: docBody,
  activeElement: null as El | null,
  createElement: (tag: string) => new El(tag),
  createTextNode: (s: string) => s,
  getElementById: (id: string): El | null => docBody.querySelector("#" + id),
  querySelectorAll: (sel: string): El[] => docBody.querySelectorAll(sel),   // no bundle <script src>: the editor chunk cannot load
  addEventListener: (type: string, fn: Listener) => { if (type === "keydown") docKeys.push(fn); },
  removeEventListener: (type: string, fn: Listener) => { const i = docKeys.indexOf(fn); if (i >= 0) docKeys.splice(i, 1); },
};
const win: any = new EventTarget();
win.parent = win;
win.confirm = () => true;                       // the discard ask, when a dirty buffer is about to go
win.getSelection = () => null;
const posted: unknown[] = [];                   // what the viewer posts to its own window: the quote seed
win.postMessage = (m: unknown) => { posted.push(m); };
(globalThis as any).window = win;
(globalThis as any).document = doc;
const store = new Map<string, string>();
const writes: Array<[string, string]> = [];     // every localStorage write, so a no-op press is shown to store nothing
(globalThis as any).localStorage = {
  getItem: (k: string) => (store.has(k) ? store.get(k)! : null),
  setItem: (k: string, v: string) => { store.set(k, String(v)); writes.push([k, String(v)]); },
  removeItem: (k: string) => { store.delete(k); },
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

// ── fixtures: a notes-api world, synthetic throughout ──────────────────────────────────────────────
const SID = "77777777-8888-9999-aaaa-bbbbbbbbbbbb";
const ROOT = "/tmp/notes-api";
const REPORT = ROOT + "/docs/report.md";
const APP = ROOT + "/src/app.py";
const PLOT = ROOT + "/docs/plot.png";
const PAPER = ROOT + "/docs/paper.pdf";
const FIG = ROOT + "/docs/fig.svg";
const DOC = "# Report\n\n## Findings\nThe api session cut p95 latency by 40%.\n\n| run | p95 |\n| --- | --- |\n| a | 120 |\n";
const PY = "def main():\n    return 0\n";
const SVG_XML = '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"><rect width="10" height="10"/></svg>';
const HREF = "http://notes-api.test/reports/run-1/evidence.md";
const URL_DOC = "# Evidence\n\nThe web session's report.\n";
const MT = "1700000000000000000";
const SIZE_KEY = "romp:fileviewTextSize";
type Served = { bytes: string | Uint8Array; type: string };
const disk: Record<string, Served> = {
  [REPORT]: { bytes: DOC, type: "text/plain; charset=utf-8" },
  [APP]: { bytes: PY, type: "text/plain; charset=utf-8" },
  [PLOT]: { bytes: new Uint8Array([0x89, 0x50, 0x4e, 0x47]), type: "image/png" },
  [PAPER]: { bytes: new Uint8Array([0x25, 0x50, 0x44, 0x46]), type: "application/pdf" },
  [FIG]: { bytes: SVG_XML, type: "image/svg+xml" },
};
const fileReads: string[] = [];                 // every /file fetch by path: the quote seed's fresh read shows up here
// The fetches the viewer makes: the kernel's /file (Content-Type is its verdict: text, a picture, a PDF, an SVG),
// its /version (editing already allowed, so no consent popup), and a same-origin document for the URL viewer,
// answered as a real Response so the streamed, capped read runs as it does in a browser.
(globalThis as any).fetch = (url: string) => {
  if (url.startsWith("/version")) return Promise.resolve({ json: () => Promise.resolve({ fileEditing: true }) });
  if (/^https?:/.test(url)) return Promise.resolve(new Response(URL_DOC, { status: 200, headers: { "Content-Type": "text/markdown; charset=utf-8" } }));
  const p = decodeURIComponent((/[?&]path=([^&]*)/.exec(url) || [])[1] || "");
  fileReads.push(p);
  const f = disk[p];
  const headers = { get: (h: string) => (f ? (h === "Content-Type" ? f.type : h === "X-Romp-Mtime-Ns" ? MT : h === "X-Romp-Text-Utf8" ? "1" : null) : null) };
  if (!f) return Promise.resolve({ ok: false, status: 404, headers, text: () => Promise.resolve("no such file: " + p) });
  return Promise.resolve({
    ok: true, status: 200, headers,
    text: () => Promise.resolve(String(f.bytes)),
    blob: () => Promise.resolve(new Blob([f.bytes as unknown as BlobPart], { type: f.type })),
  });
};
/** Let every pending promise chain run: the fetch settles, a blob decodes, the editor chunk's rejection reaches its catch. */
const settle = async () => { for (let i = 0; i < 8; i++) await new Promise<void>((r) => setImmediate(r)); };

// the probe: an action whose only job is to keep the ctx the viewer hands it and count the seam's paints (onRendered)
let seam: FileViewActionCtx | null = null;
let paints = 0;
let bound: Promise<typeof import("./file-view")> | null = null;
function view(): Promise<typeof import("./file-view")> {
  if (!bound) bound = import("./file-view").then((fv) => {
    fv.initFileView(() => { /* the WS poster: nothing asks the kernel here */ });
    fv.registerFileViewAction({ id: "size-probe", mount(ctx) { seam = ctx; ctx.onRendered(() => { paints++; }); return null; } });
    return fv;
  });
  return bound;
}
type Card = { fv: typeof import("./file-view"); ctx?: FileViewActionCtx; wrap: El; root: El; bar: El; acts: El; body: El; down: El; reset: El; up: El; btn: (label: string) => El };
/** The card up now, with the control's three buttons held by reference (they are built once per open). */
function card(fv: typeof import("./file-view")): Card {
  const wrap = doc.getElementById("romp-fileview");
  assert.ok(wrap, "a viewer is up");
  const root = wrap!.children[0];
  assert.equal(root.className, "fileview");
  const bar = root.children[0];
  assert.equal(bar.className, "fileview-bar");
  const body = root.querySelector(".fileview-body")!;   // inside .fileview-main beside the comments aside in the local viewer; the root's child in the URL viewer
  assert.ok(body, "the body");
  const acts = bar.children.find((c) => c.classList.contains("fileview-acts"))!;
  const btn = (label: string) => { const b = acts.children.find((c) => c.tagName === "button" && c.textContent === label); assert.ok(b, "the " + label + " button"); return b!; };
  const reset = acts.children.find((c) => c.classList.contains("fileview-size-reset"));
  assert.ok(reset, "the readout between A− and A+ (the reset)");
  return { fv, wrap: wrap!, root, bar, acts, body, down: btn("A−"), reset: reset!, up: btn("A+"), btn };
}
/** Open `p` for the fixture session; `wait` lets the bytes land. The stored size is the caller's, set before the call. */
async function openFile(t: TestContext, p: string, wait = true): Promise<Card> {
  const fv = await view();
  paints = 0; seam = null;
  fv.openFileView(p, SID);
  t.after(() => { fv.closeFileView(); store.clear(); });
  if (wait) await settle();
  assert.ok(seam, "the probe action was mounted with the ctx");
  return { ...card(fv), ctx: seam! };
}
const size = (o: Card): string | null => o.root.getAttribute("data-fv-text");
/** The readout's slot is empty at the default (the sheet hides this class by visibility): nothing to reset, nothing said. */
const blank = (o: Card): boolean => o.reset.classList.contains("fileview-size-default");
/** An end of the table: aria-disabled (dimmed by the sheet, focus kept), never the disabled property. */
const atEnd = (b: El): boolean => b.getAttribute("aria-disabled") === "true";
const wheel = (init: { dy: number; ctrl?: boolean; meta?: boolean; mode?: number }): Ev =>
  new Ev("wheel", { ctrlKey: !!init.ctrl, metaKey: !!init.meta, deltaY: init.dy, deltaMode: init.mode ?? 0 });
const labels = (acts: El): string[] => acts.children.map((c) => c.textContent);

// ── the pure table ─────────────────────────────────────────────────────────────────────────────────

test("TEXT_SIZES is a bounded, ascending table of percentages holding the default; stepTextSize walks it and clamps at both ends", async () => {
  const { TEXT_SIZES, TEXT_SIZE_DEFAULT, stepTextSize } = await view();
  assert.equal(TEXT_SIZES[0], 70); assert.equal(TEXT_SIZES[TEXT_SIZES.length - 1], 200);
  assert.equal(TEXT_SIZE_DEFAULT, 100); assert.ok(TEXT_SIZES.includes(100), "the default is a step of the table");
  for (let i = 1; i < TEXT_SIZES.length; i++) assert.ok(TEXT_SIZES[i] > TEXT_SIZES[i - 1], "ascending");
  assert.equal(stepTextSize(100, 1), 115); assert.equal(stepTextSize(100, -1), 90);
  assert.equal(stepTextSize(200, 1), 200, "the top clamps"); assert.equal(stepTextSize(70, -1), 70, "the bottom clamps");
  assert.equal(stepTextSize(175, 1), 200); assert.equal(stepTextSize(80, -1), 70);
  assert.equal(stepTextSize(123, 1), 115, "a value off the table steps from the default");
  assert.equal(stepTextSize(123, -1), 90);
  // every step is reachable from the default by presses, and the walk never leaves the table
  let at = 100; const seen = new Set<number>([at]);
  for (let i = 0; i < 20; i++) { at = stepTextSize(at, 1); seen.add(at); assert.ok(TEXT_SIZES.includes(at)); }
  for (let i = 0; i < 20; i++) { at = stepTextSize(at, -1); seen.add(at); assert.ok(TEXT_SIZES.includes(at)); }
  assert.equal(seen.size, TEXT_SIZES.length);
});

test("parseTextSize returns a stored step; absent, garbage, a size off the table or a multiplier read as the default", async () => {
  const { parseTextSize } = await view();
  assert.equal(parseTextSize("115"), 115); assert.equal(parseTextSize(" 200 "), 200); assert.equal(parseTextSize("70"), 70);
  assert.equal(parseTextSize(null), 100); assert.equal(parseTextSize(undefined), 100); assert.equal(parseTextSize(""), 100);
  assert.equal(parseTextSize("huge"), 100); assert.equal(parseTextSize('{"pct":115}'), 100);
  assert.equal(parseTextSize("110"), 100, "a size the table does not hold is not invented");
  assert.equal(parseTextSize("1.15"), 100, "a multiplier is not a percentage");
  assert.equal(parseTextSize("-100"), 100); assert.equal(parseTextSize("1e9"), 100);
});

test("foldWheel: a notch is one step, a pinch's small deltas add up to one, a reversal starts over, lines and pages are normalized, wheel-up is larger", async () => {
  const { foldWheel, WHEEL_STEP_PX } = await view();
  assert.deepEqual(foldWheel({ deltaY: -100, deltaMode: 0 }, 0), { acc: 0, dir: 1 }, "a notch up (Chrome, about 100 pixels): larger at once");
  assert.deepEqual(foldWheel({ deltaY: 100, deltaMode: 0 }, 0), { acc: 0, dir: -1 }, "a notch down: smaller");
  assert.deepEqual(foldWheel({ deltaY: -3, deltaMode: 1 }, 0), { acc: 0, dir: 1 }, "three lines (deltaMode 1) is a notch");
  assert.deepEqual(foldWheel({ deltaY: 1, deltaMode: 2 }, 0), { acc: 0, dir: -1 }, "a page (deltaMode 2) is more than a notch");
  // a pinch reports as a burst of ctrlKey wheel events a few pixels each: the third crosses the threshold and the sum clears
  let r = foldWheel({ deltaY: -15, deltaMode: 0 }, 0); assert.deepEqual(r, { acc: -15, dir: 0 });
  r = foldWheel({ deltaY: -15, deltaMode: 0 }, r.acc); assert.deepEqual(r, { acc: -30, dir: 0 });
  r = foldWheel({ deltaY: -15, deltaMode: 0 }, r.acc); assert.deepEqual(r, { acc: 0, dir: 1 });
  assert.ok(WHEEL_STEP_PX > 30 && WHEEL_STEP_PX <= 100, "a notch is at least one step; a pinch's single event is not");
  // a reversal does not pay off the other way's remainder first
  r = foldWheel({ deltaY: -30, deltaMode: 0 }, 0); assert.equal(r.acc, -30);
  r = foldWheel({ deltaY: 10, deltaMode: 0 }, r.acc); assert.deepEqual(r, { acc: 10, dir: 0 });
  assert.deepEqual(foldWheel({ deltaY: 0, deltaMode: 0 }, -20), { acc: -20, dir: 0 }, "a horizontal-only event changes nothing");
});

// ── the control over the real openFileView ─────────────────────────────────────────────────────────

test("a markdown file opens at the default: A− and A+ after the format toggles, the readout slot empty, the root at 100; each press steps, stores and acknowledges in the same tick; an end reads as reached and a press there changes nothing", async (t) => {
  const { TEXT_SIZES } = await view();
  const o = await openFile(t, REPORT);
  assert.equal(size(o), "100", "the root carries the step the sheets read");
  assert.equal(o.down.hidden, false); assert.equal(o.up.hidden, false);
  assert.equal(o.reset.hidden, false, "the readout's slot is in the row from the start, so A− never moves when it fills");
  assert.equal(blank(o), true, "nothing to reset at the default, so nothing is said: the slot is empty");
  assert.equal(o.down.getAttribute("aria-label"), "Smaller text"); assert.equal(o.up.getAttribute("aria-label"), "Larger text");
  const row = labels(o.acts);
  assert.ok(row.indexOf("Raw") < row.indexOf("A−") && row.indexOf("A−") < row.indexOf("A+") && row.indexOf("A+") < row.indexOf("Edit"),
    "the control sits after Rendered and Raw and before Edit: " + row.join(" | "));
  assert.equal(o.acts.children.indexOf(o.reset), o.acts.children.indexOf(o.down) + 1, "the readout sits between A− and A+");
  o.up.click();
  assert.equal(size(o), "115", "one step, synchronously");
  assert.equal(blank(o), false); assert.equal(o.reset.textContent, "115%", "the readout is the acknowledgement");
  assert.equal(store.get(SIZE_KEY), "115", "stored as the percentage, under the viewer's own key");
  o.down.click(); o.down.click();
  assert.equal(size(o), "90"); assert.equal(o.reset.textContent, "90%"); assert.equal(store.get(SIZE_KEY), "90");
  for (let i = 0; i < 12; i++) o.up.click();
  assert.equal(size(o), "200", "clamped at the top however many presses");
  assert.equal(atEnd(o.up), true, "the top end reads as reached: aria-disabled, which the sheet dims"); assert.equal(atEnd(o.down), false);
  assert.equal(o.up.disabled, false, "never the disabled property: a button that disables under keyboard focus drops the focus");
  let n = writes.length;
  o.up.click();
  assert.equal(size(o), "200"); assert.equal(writes.length, n, "a press on the end changes nothing and stores nothing");
  for (let i = 0; i < 12; i++) o.down.click();
  assert.equal(size(o), "70"); assert.equal(atEnd(o.down), true); assert.equal(atEnd(o.up), false); assert.equal(o.down.disabled, false);
  n = writes.length;
  o.down.click();
  assert.equal(size(o), "70"); assert.equal(writes.length, n);
  assert.equal(store.get(SIZE_KEY), String(TEXT_SIZES[0]));
  assert.equal(o.down.className, "fileview-btn fileview-size", "wears the row's one button treatment");
  assert.ok(o.reset.classList.contains("fileview-btn"), "the readout is a button: the reset");
});

test("the readout resets to the default and empties; a reset at the default stores nothing", async (t) => {
  const o = await openFile(t, REPORT);
  o.up.click(); o.up.click();
  assert.equal(size(o), "130");
  o.reset.click();
  assert.equal(size(o), "100"); assert.equal(blank(o), true, "back at the default the slot empties"); assert.equal(store.get(SIZE_KEY), "100");
  assert.equal(atEnd(o.up), false); assert.equal(atEnd(o.down), false);
  const n = writes.length;
  o.reset.click();
  assert.equal(writes.length, n, "nothing changed, nothing stored");
});

test("persistence: the size survives a close and a fresh open, is on the root before the bytes land, and a foreign stored value opens at the default", async (t) => {
  const first = await openFile(t, REPORT);
  first.up.click(); first.up.click(); first.up.click();
  assert.equal(size(first), "150");
  first.fv.closeFileView();
  assert.equal(doc.getElementById("romp-fileview"), null);
  const again = await openFile(t, REPORT, false);                    // no settle: the loader still holds the body
  assert.equal(size(again), "150", "the stored step is on the root at open, before the fetch, so the first paint is at size");
  assert.equal(again.reset.textContent, "150%");
  assert.equal(again.down.hidden, true); assert.equal(again.reset.hidden, true); assert.equal(again.up.hidden, true,
    "the control waits for the bytes: whether this is a text file is the kernel's verdict, in the fetch's headers");
  await settle();
  assert.equal(size(again), "150", "the paint keeps it");
  assert.equal(again.down.hidden, false); assert.equal(again.reset.hidden, false); assert.equal(blank(again), false);
  again.fv.closeFileView();
  store.set(SIZE_KEY, "purple");
  const third = await openFile(t, REPORT);
  assert.equal(size(third), "100", "a corrupt entry costs the preference, never the viewer");
  assert.equal(blank(third), true);
  third.fv.closeFileView();
  store.set(SIZE_KEY, "80");
  const fourth = await openFile(t, APP);
  assert.equal(size(fourth), "80", "one size for every file this browser opens, a .py included");
  assert.equal(fourth.down.hidden, false, "a non-markdown text file has the control: its code view scales too");
  assert.equal(fourth.reset.textContent, "80%");
});

test("Ctrl/Cmd + wheel over the body steps the size and takes the gesture from the page zoom; a plain wheel scrolls; a pinch's deltas add up; the bar is not the text; a picture leaves the browser its zoom", async (t) => {
  const o = await openFile(t, REPORT);
  const md = o.body.querySelector(".fileview-md")!;
  assert.ok(md, "the rendered body");
  let ev = wheel({ dy: -100, ctrl: true });
  md.dispatchEvent(ev);
  assert.equal(size(o), "115", "a notch up with Ctrl: larger");
  assert.equal(ev.defaultPrevented, true, "the page zoom is prevented: the gesture is the viewer's here");
  ev = wheel({ dy: 100, meta: true });
  md.dispatchEvent(ev);
  assert.equal(size(o), "100", "Cmd works the same"); assert.equal(ev.defaultPrevented, true);
  ev = wheel({ dy: -100 });
  md.dispatchEvent(ev);
  assert.equal(size(o), "100", "no modifier: not the gesture"); assert.equal(ev.defaultPrevented, false, "and the wheel scrolls as ever");
  for (const dy of [-15, -15]) md.dispatchEvent(wheel({ dy, ctrl: true }));
  assert.equal(size(o), "100", "a pinch's first events add up");
  md.dispatchEvent(wheel({ dy: -15, ctrl: true }));
  assert.equal(size(o), "115", "and the third crosses the threshold");
  md.dispatchEvent(wheel({ dy: -3, ctrl: true, mode: 1 }));
  assert.equal(size(o), "130", "three lines is a notch");
  assert.equal(store.get(SIZE_KEY), "130", "the wheel stores like the buttons");
  assert.equal(o.reset.textContent, "130%", "and the readout follows");
  ev = wheel({ dy: -100, ctrl: true });
  o.acts.dispatchEvent(ev);
  assert.equal(size(o), "130", "a wheel over the action row is not the gesture"); assert.equal(ev.defaultPrevented, false);
  o.fv.closeFileView(); store.delete(SIZE_KEY);
  const pic = await openFile(t, PLOT);
  ev = wheel({ dy: -100, ctrl: true });
  pic.body.dispatchEvent(ev);
  assert.equal(size(pic), "100", "a picture: nothing there reads the property");
  assert.equal(ev.defaultPrevented, false, "not prevented: the page zoom stays the browser's");
});

test("click-safe: the three buttons are built once per open and never rebuilt by a paint; a Rendered/Raw flip and a step keep the same nodes", async (t) => {
  const o = await openFile(t, REPORT);
  const nodes = [o.down, o.reset, o.up];
  o.btn("Raw").click();
  assert.equal(o.body.children[0].className, "fileview-code", "the Raw paint");
  sameNodes([o.btn("A−"), o.acts.querySelector(".fileview-size-reset"), o.btn("A+")], nodes, "the same elements after the Raw paint");   // by identity (ui/test-dom-shim.ts sameNodes)
  o.up.click();
  sameNodes([o.btn("A−"), o.acts.querySelector(".fileview-size-reset"), o.btn("A+")], nodes, "and after a step");
  assert.equal(size(o), "115", "the Raw view is scaled by the same property (.fileview-pre reads it)");
  o.btn("Rendered").click();
  assert.equal(size(o), "115", "the flip back keeps the size");
  // source: the control is declared before renderBody, outside it, with direct listeners (the format toggles' idiom)
  const at = (s: string) => { const i = VIEW.indexOf(s); assert.ok(i >= 0, s); return i; };
  const openFn = VIEW.split("export function openFileView")[1].split("function offersDownload")[0];
  assert.ok(openFn.indexOf("textSizeControl(") >= 0 && openFn.indexOf("textSizeControl(") < openFn.indexOf("const renderBody = () => {"), "built once per open, before the paint function");
  const paint = openFn.slice(openFn.indexOf("const renderBody = () => {"), openFn.indexOf("\n  };", openFn.indexOf("const renderBody = () => {")));
  assert.doesNotMatch(paint, /addEventListener/, "the paint function wires nothing: it only syncs the control's hidden state");
  assert.match(paint, /\.sync\(\);/, "which it does, every paint");
  assert.deepEqual(o.body.passiveOf("wheel").filter((p) => p === false), [false], "the size gesture's wheel listener is the body's one non-passive wheel listener, so the page zoom can be prevented (the comments panel's margin layout adds a passive one, file-comments.ts installLayout)");
  assert.doesNotMatch(VIEW, /e\.key === "\+"|e\.key === "-"|e\.key === "="/, "no keyboard zoom chord: Ctrl+plus/minus stay the browser's");
  assert.ok(at("function textSizeControl(") < at("export function openFileView"), "one builder, declared once, for both viewers");
});

test("the control is absent for a picture and a PDF, present for the SVG Source view, hidden in edit mode and back on exit", async (t) => {
  const pic = await openFile(t, PLOT);
  assert.equal(pic.down.hidden, true); assert.equal(pic.up.hidden, true); assert.equal(pic.reset.hidden, true, "a picture has no text to size");
  pic.fv.closeFileView();
  const pdf = await openFile(t, PAPER);
  assert.equal(pdf.down.hidden, true); assert.equal(pdf.up.hidden, true); assert.equal(pdf.reset.hidden, true, "a PDF: the browser's viewer owns its text");
  pdf.fv.closeFileView();
  const svg = await openFile(t, FIG);
  assert.equal(svg.down.hidden, true, "an SVG shown as a picture: no text yet");
  svg.btn("Source").click();
  await settle();
  assert.equal(svg.body.children[0].className, "fileview-code", "the Source view is up");
  assert.equal(svg.down.hidden, false); assert.equal(svg.up.hidden, false); assert.equal(svg.reset.hidden, false, "the Source view is a text view and has the control");
  const ev = wheel({ dy: -100, ctrl: true });
  svg.body.dispatchEvent(ev);
  assert.equal(size(svg), "115", "and the wheel steps it"); assert.equal(ev.defaultPrevented, true);
  svg.fv.closeFileView(); store.delete(SIZE_KEY);
  store.set(SIZE_KEY, "115");
  const o = await openFile(t, REPORT);
  assert.equal(o.down.hidden, false); assert.equal(blank(o), false, "off the default, the readout says the size");
  o.btn("Edit").click();
  await settle();
  assert.equal(o.btn("Cancel").hidden, false, "edit mode");
  assert.equal(o.down.hidden, true); assert.equal(o.up.hidden, true); assert.equal(o.reset.hidden, true, "the editor keeps its own size");
  const ev2 = wheel({ dy: -100, ctrl: true });
  o.body.dispatchEvent(ev2);
  assert.equal(size(o), "115", "the wheel stands down in edit mode"); assert.equal(ev2.defaultPrevented, false);
  o.btn("Cancel").click();
  assert.equal(o.btn("Cancel").hidden, true);
  assert.equal(o.down.hidden, false); assert.equal(o.reset.hidden, false); assert.equal(o.up.hidden, false); assert.equal(blank(o), false, "back with the read view");
});

test("the control shows only once a text body is KNOWN: hidden beside the loader, shown when a text file's bytes land, never for a picture", async (t) => {
  store.set(SIZE_KEY, "130");
  const o = await openFile(t, REPORT, false);
  assert.equal(o.down.hidden, true); assert.equal(o.up.hidden, true); assert.equal(o.reset.hidden, true, "the loader holds the body: not yet a text view");
  assert.equal(size(o), "130", "the step is on the root already, so the first paint is at size");
  await settle();
  assert.equal(o.down.hidden, false); assert.equal(o.up.hidden, false); assert.equal(o.reset.hidden, false); assert.equal(o.reset.textContent, "130%");
  o.fv.closeFileView();
  const pic = await openFile(t, PLOT, false);
  assert.equal(pic.down.hidden, true, "a picture: hidden for the load");
  await settle();
  assert.equal(pic.body.children[0].className, "fileview-imgbox", "the picture landed");
  assert.equal(pic.down.hidden, true); assert.equal(pic.up.hidden, true); assert.equal(pic.reset.hidden, true, "and after it: nothing there reads the property");
});

test("a press on a bar control settles no selection: with a passage selected in the body, A+ steps the size and neither re-reads the file nor re-seeds the quote chip; a lift on the bar's path or padding still settles", async (t) => {
  const composer = new El("textarea");             // this document holds the composer, so a selection seeds its chip
  composer.id = "composer-input";
  docBody.appendChild(composer);
  t.after(() => { composer.remove(); win.getSelection = () => null; });
  const o = await openFile(t, REPORT);
  const md = o.body.querySelector(".fileview-md")!;
  win.getSelection = () => ({ isCollapsed: false, anchorNode: md, toString: () => "cut p95 latency" });
  const reads = () => fileReads.filter((p) => p === REPORT).length;
  const seeds = () => posted.filter((m) => (m as { type?: string }).type === "editorSelection").length;
  let r = reads(), s = seeds();
  md.dispatchEvent(new Ev("mouseup"));
  await settle();
  assert.equal(reads(), r + 1, "a lift over the body settles the selection: the label's line is minted against a fresh read");
  assert.equal(seeds(), s + 1, "and the quote chip is seeded");
  r = reads(); s = seeds();
  o.up.dispatchEvent(new Ev("mouseup")); o.up.click();
  await settle();
  assert.equal(size(o), "115", "the step happened");
  assert.equal(reads(), r, "and the press on A+ read nothing"); assert.equal(seeds(), s, "and seeded nothing");
  o.reset.dispatchEvent(new Ev("mouseup")); o.reset.click();
  await settle();
  assert.equal(size(o), "100"); assert.equal(reads(), r); assert.equal(seeds(), s);
  o.btn("Raw").dispatchEvent(new Ev("mouseup"));
  await settle();
  assert.equal(reads(), r, "every button in the bar: the format toggles too");
  // the overshoot: a drag that starts in the body and is released over the bar's path or its padding is a selection like any other
  o.bar.children.find((c) => c.classList.contains("fileview-name"))!.dispatchEvent(new Ev("mouseup"));
  await settle();
  assert.equal(reads(), r + 1, "released over the bar's path, the drag settles: the gate is the control under the lift, not the bar");
  assert.equal(seeds(), s + 1);
  o.bar.dispatchEvent(new Ev("mouseup"));
  await settle();
  assert.equal(reads(), r + 2, "and the bar's own padding");
  assert.equal(seeds(), s + 2);
});

// Fork-only, beside upstream's twin above (which settles by mouseup over the body and the bar alone): the two settle points
// the fork wired and upstream never received. The phone's selection ends in a touchend with no mouseup, and a drag that
// starts in the body can be released over the aside or the margins beside the body, the `.fileview-main` row, where
// only a listener on the viewer root hears it. Executed, not pinned: the first assertion goes red when the touchend
// binding is removed, the second when the mouseup listener moves from the root to the body (file-view.test.ts pins the
// two addEventListener lines, which is a pin, not a test). Re-added in the 4d-3 fold's fixer round 2 (review round 1,
// tests-1) after the fold retired the fork's pre-offer body of this subject with these two steps inside it.
test("a lift settles a selection wherever it ends inside the viewer: a touchend over the body (the phone's lift, no mouseup) and a mouseup released over the body row (the aside, the margins) each re-read the file and re-seed the quote chip", async (t) => {
  const composer = new El("textarea");             // this document holds the composer, so a selection seeds its chip
  composer.id = "composer-input";
  docBody.appendChild(composer);
  t.after(() => { composer.remove(); win.getSelection = () => null; });
  const o = await openFile(t, REPORT);
  const md = o.body.querySelector(".fileview-md")!;
  win.getSelection = () => ({ isCollapsed: false, anchorNode: md, toString: () => "cut p95 latency" });
  const reads = () => fileReads.filter((p) => p === REPORT).length;
  const seeds = () => posted.filter((m) => (m as { type?: string }).type === "editorSelection").length;
  const r = reads(), s = seeds();
  md.dispatchEvent(new Ev("touchend"));
  await settle();
  assert.equal(reads(), r + 1, "the phone's lift: a touchend over the body settles the selection (a touch ends with no mouseup), so the label's line is minted against a fresh read");
  assert.equal(seeds(), s + 1, "and the quote chip is seeded");
  const main = o.root.querySelector(".fileview-main")!;
  assert.ok(main && main.contains(o.body), "the body row holds the body (and the aside, when the comments panel asks for one)");
  main.dispatchEvent(new Ev("mouseup"));
  await settle();
  assert.equal(reads(), r + 2, "released over the row itself, beside the body: the listener sits on the viewer root, not the body, so the drag settles");
  assert.equal(seeds(), s + 2, "and the chip is seeded again");
});

// ── the re-measure: every reflow of a text view fires the seam's onRendered (the comments panel re-places its cards) ──

test("a size step fires onRendered once, as a reflow (the panel re-places its cards over the moved text and keeps its marks); a clamped step fires nothing", async (t) => {
  const o = await openFile(t, REPORT);
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
  // moved) and, told the call is a REFLOW (`why`), re-places its cards over the moved text and leaves its marks standing,
  // since the nodes are the same (2026-09-09: the whole paint pass ran here once per frame of a pane drag, unwrapping and
  // re-wrapping every mark, and stalled the dashboard on a big reviewed file; file-view-reflow-browser.test.ts); a paint
  // proper still runs the pass
  assert.match(PANEL, /ctx\.onRendered\(\(why\) => \{ this\.hideFloat\(\); [^\n]*if \(why === "reflow"\) \{ this\.trimBlanks\(\); this\.scheduleLayout\(\); \} else this\.paintAll\(\); \}\);/, "file-comments.ts answers a reflow with trimBlanks (the marks' collapsed blanks re-measured at the new size) and scheduleLayout, and a paint with paintAll");
  assert.match(VIEW, /onRendered\(cb: \(why\?: FileViewRenderWhy\) => void\): void;/);
  assert.match(VIEW, /Also after a text view REFLOWS with its text unchanged \(`why` "reflow"\): a text-size step/, "the seam's doc names the reflow triggers");
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
  const o = await openFile(t, REPORT);
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
  const pic = await openFile(t, PLOT);
  const before = paints;
  report(pic.body, 500); report(pic.body, 300); frame();
  assert.equal(paints, before, "a media body has its own observers (the figure layer's, the chunk's)");
  assert.match(VIEW, /let paintedWidth = -1;[^\n]*\n\s*let seenWidth = -1;/, "the frame's bookkeeping sits beside the watch it hangs on (watchBodyWidth's onWidth)");
  assert.match(VIEW, /if \(typeof ResizeObserver === "function"\) \{/, "guarded like the figure layer's sizer, inside watchBodyWidth: no observer, no width event");
  assert.match(VIEW, /if \(typeof requestAnimationFrame === "function"\) frame = requestAnimationFrame\(repaint\); else repaint\(\);/, "the frame is the fold; without one the report is the frame");
  assert.doesNotMatch(VIEW, /setTimeout\([^)]*fireRendered|debounce/, "no timer approximates the resize");
});

// ── the URL viewer: the same size for a document opened from a link on the dashboard's own address ──

test("openUrlView carries the stored step on its root and mounts the same control; a step there is the one size every document honours", async (t) => {
  const fv = await view();
  store.set(SIZE_KEY, "130");
  fv.openUrlView(HREF);
  t.after(() => { fv.closeFileView(); store.clear(); });
  const o = card(fv);
  assert.equal(size(o), "130", "the stored step is on the root before the document lands");
  assert.equal(o.down.hidden, true); assert.equal(o.reset.hidden, true); assert.equal(o.up.hidden, true, "hidden beside the loader");
  const row = labels(o.acts);
  assert.ok(row.indexOf("Raw") < row.indexOf("A−") && row.indexOf("A+") < row.indexOf("Open ↗"), "after Rendered and Raw, before the link out: " + row.join(" | "));
  await settle();
  assert.equal(o.body.children[0].className, "fileview-md", "the document rendered");
  assert.equal(o.down.hidden, false); assert.equal(o.reset.hidden, false); assert.equal(o.up.hidden, false);
  assert.equal(o.reset.textContent, "130%"); assert.equal(blank(o), false);
  o.up.click();
  assert.equal(size(o), "150"); assert.equal(store.get(SIZE_KEY), "150", "stored under the same key as a local file's");
  const ev = wheel({ dy: -100, ctrl: true });
  o.body.querySelector(".fileview-md")!.dispatchEvent(ev);
  assert.equal(size(o), "175", "Ctrl + wheel steps here too"); assert.equal(ev.defaultPrevented, true);
  assert.deepEqual(o.body.passiveOf("wheel"), [false], "non-passive here too: the page zoom can be prevented");
  const plain = wheel({ dy: -100 });
  o.body.dispatchEvent(plain);
  assert.equal(size(o), "175"); assert.equal(plain.defaultPrevented, false, "a plain wheel scrolls");
  o.btn("Raw").click();
  assert.equal(o.body.children[0].className, "fileview-code");
  assert.deepEqual([o.btn("A−"), o.acts.querySelector(".fileview-size-reset"), o.btn("A+")], [o.down, o.reset, o.up], "the same nodes across the Raw paint");
  fv.closeFileView();
  const local = await openFile(t, REPORT);
  assert.equal(size(local), "175", "a local file opened next honours the size the document set");
});

// ── the sheets: one property, read by every text size; the measure that follows the size ────────────

/** The rule whose selector opens a line as `head`. */
const ruleOf = (css: string, head: string): string => { const at = css.indexOf("\n" + head); assert.ok(at >= 0, head + " present"); return css.slice(at + 1, css.indexOf("}", at) + 1); };
const decls = (rule: string): string[] => rule.slice(rule.indexOf("{") + 1, -1).split(";").map((d) => d.trim()).filter(Boolean);

test("both sheets: the step table maps every TEXT_SIZES entry to --fv-scale on the viewer root and nothing else; exactly the text views read the one property", async () => {
  const { TEXT_SIZES } = await view();
  for (const [name, css] of SHEETS) {
    for (const n of TEXT_SIZES) {
      assert.deepEqual(decls(ruleOf(css, `.fileview[data-fv-text="${n}"] {`)), [`--fv-scale: ${n / 100}`], name + ": step " + n + " is exactly the property");
    }
    assert.equal((css.match(/\.fileview\[data-fv-text="\d+"\]/g) || []).length, TEXT_SIZES.length, name + ": no step the table does not hold");
    assert.equal((css.match(/--fv-scale:/g) || []).length, TEXT_SIZES.length, name + ": nothing else sets the property");
    // the readers: the prose (the page's size times the document's 1.15, times the scale), fenced code, the Raw view's rows and gutter
    const root = decls(ruleOf(css, ".fileview-md {"));
    assert.ok(root.includes("font-size: calc(var(--fs) * 1.15 * var(--fv-scale, 1))"), name + ": the prose reads it");
    assert.ok(!root.some((d) => d.startsWith("max-width")), name + ": the root is fluid to the viewer (the measure is its inline padding)");
    assert.ok(root.includes("padding-inline: max(18px, round(down, calc((100% - 80ch) / 2), 1px))"), name + ": the measure is 80 of the root's own ch, centred as whole-pixel padding, never under 18px");
    const plain = root.indexOf("padding-inline: max(18px, calc((100% - 80ch) / 2))"), rounded = root.findIndex((d) => d.startsWith("padding-inline: max(18px, round("));
    assert.ok(plain >= 0 && plain < rounded, name + ": a plain calc() fallback is declared first, for an engine without round()");
    assert.ok(root.includes("line-height: 1.5") && root.includes("font-family: var(--font-doc)") && root.includes("contain: layout"), name + ": the leading and the face are the document's own, and nothing inside can widen the body");
    assert.ok(decls(ruleOf(css, ".fileview-md pre code {")).includes("font-size: calc(12px * var(--fv-scale, 1))"), name + ": fenced code reads it");
    assert.ok(decls(ruleOf(css, ".fileview-pre {")).includes("font-size: calc(12px * var(--fv-scale, 1))"), name + ": the Raw rows read it");
    assert.ok(decls(ruleOf(css, ".fileview-gutter {")).includes("font-size: calc(12px * var(--fv-scale, 1))"), name + ": the gutter reads it, in lockstep with the rows");
    assert.ok(decls(ruleOf(css, ".fileview-md h1 {")).includes("font-size: 2em"), name + ": headings stay em of the prose, so they scale with it");
    assert.ok(decls(ruleOf(css, ".fileview-md h2 {")).includes("font-size: 1.5em") && decls(ruleOf(css, ".fileview-md h3 {")).includes("font-size: 1.25em"), name + ": the ladder is 2 / 1.5 / 1.25 / 1em");
    assert.ok(decls(ruleOf(css, ".fileview-md :not(pre) > code {")).includes("font-size: 0.92em"), name + ": inline code stays em of the prose");
    assert.ok(decls(ruleOf(css, ".fileview-md .fc-overlay {")).includes("font-size: var(--fs)"), name + ": a figure's region chip keeps the page's size, not the text's");
    assert.ok(decls(ruleOf(css, ".fileview-editor {")).includes("font-size: 12px"), name + ": the editor keeps the page's size");
    assert.ok(decls(ruleOf(css, ".fileview-btn {")).includes("font-size: 0.82em"), name + ": the bar's buttons keep the page's size");
    // no other rule reads the property: the title bar, its buttons and the editor keep the page's size
    const readers = (css.match(/^[^\n{]*\{[^}]*var\(--fv-scale[^}]*\}/gm) || []).map((r) => r.slice(0, r.indexOf("{")).trim());
    assert.deepEqual(readers.sort(), [".fileview-gutter", ".fileview-md", ".fileview-md pre code", ".fileview-pre"].sort(), name + ": the readers, exactly");
  }
});

test("both sheets: the measure is the root's own inline padding; a table takes the body's width and scrolls on its own with whole words; a picture fits the column; byte-equal across the sheets", () => {
  for (const [name, css] of SHEETS) {
    assert.doesNotMatch(css, /\.fileview-md > :where\(/, name + ": no per-child measure rule remains (the root's padding is the measure)");
    assert.doesNotMatch(css, /\.fileview-md > :not\(/, name + ": nor a specificity-bearing one");
    assert.doesNotMatch(css, /860px/, name + ": the fixed cap is gone");
    assert.deepEqual(decls(ruleOf(css, ".fileview-md img {")), ["max-width: 100%"], name + ": a picture shrinks to its column (the root's content box)");
    assert.deepEqual(decls(ruleOf(css, ":where(.fileview-md) svg, :where(.fileview-md) canvas, :where(.fileview-md) video {")), ["max-width: 100%"], name + ": the media a file draws itself (svg, canvas, video) shrink to the column too, at element specificity");
    assert.deepEqual(decls(ruleOf(css, ':where(.fileview-md :is(img, svg, canvas, video)[width]:not([width$="%"])) {')), ["height: auto"], name + ": a pixel-sized one keeps its ratio as it shrinks (a sized <img> too, since Slice 2 of plans/markdown-viewer.md); a percentage-width one keeps the author's height (the cap never shrinks it), and the whole selector sits inside :where so its two attribute tests add no specificity over KaTeX's svg rule");
    // with the column the root's own content box there is no measure for a top-level medium's cap to outrank: the general
    // caps above hold a bare <img> line or an inline <svg> block, direct children of the root, to the column by themselves
    assert.equal(css.indexOf("\n.fileview-md > img {"), -1, name + ": a bare top-level picture needs no rule of its own now that the column is the root's box");
    assert.doesNotMatch(css, /\.fileview-md > :is\(img/, name + ": nor does a top-level svg, canvas or video block");
    assert.deepEqual(decls(ruleOf(css, ".fileview-md table {")),
      ["border-collapse: collapse", "margin: 0.6em 0", "display: block", "width: max-content", "max-width: 100%", "overflow-x: auto", "overflow-wrap: normal"],
      name + ": a table is a block as wide as its columns need up to its container, scrolling inside beyond it, whole words kept");
    // a table of the page's own may grow out of the column, evenly into both gutters, up to the body's content width less
    // the root's 18px inset (--fv-body-w, written by the viewer's width observer on each top-level table); unset, both
    // declarations read the column and the shift is none
    const top = decls(ruleOf(css, ".fileview-md > table {"));
    assert.equal(top[0], "max-width: calc(var(--fv-body-w, calc(100% + 36px)) - 36px)", name + ": the cap is the body less the inset, the column before the first report");
    assert.equal(top[1], "translate: min(0px, round(calc(var(--fv-body-w, calc(100% + 36px)) / 2 - max(18px, round(down, (var(--fv-body-w, calc(100% + 36px)) - 80ch) / 2, 1px)) - 50%), 1px))", name + ": the shift left is half of what the table exceeds the column by, whole pixels, never right");
    assert.equal(top.length, 2);
    assert.match(css, /^@property --fv-body-w \{ syntax: "\*"; inherits: false; \}$/m, name + ": the property is registered non-inherited, so a write restyles the tables alone");
    assert.deepEqual(decls(ruleOf(css, ".fileview-body {")), ["flex: 1 1 auto", "min-height: 0", "overflow: auto"], name + ": the body reserves no scrollbar gutter and is no size container (review round 2 of Slice 3 of plans/markdown-viewer.md: the gutter was a blank strip beside every body that does not scroll; the cap reads the observer's width instead)");
    assert.ok(decls(ruleOf(css, ".fileview-md {")).includes("overflow-wrap: anywhere"), name + ": prose still breaks an unbreakable string");
    assert.ok(decls(ruleOf(css, ".fileview-md pre {")).includes("overflow-x: auto"), name + ": a code block scrolls on its own");
    assert.ok(decls(ruleOf(css, ".fileview-md pre code {")).includes("white-space: pre-wrap"), name + ": and wraps first");
  }
  const [chat, feed] = SHEETS.map(([, css]) => css);
  for (const head of [".fileview-md {", ".fileview-md table {", ".fileview-md > table {", ".fileview-md pre code {", ".fileview-pre {", ".fileview-gutter {", ".fileview-md img {"]) {
    assert.equal(ruleOf(chat, head), ruleOf(feed, head), head + " mirrors exactly (the viewer mounts in both documents)");
  }
  const block = (css: string) => { const a = css.indexOf("/* ── text size and measure"); const b = css.indexOf("/* Rendered markdown ("); assert.ok(a >= 0 && b > a, "the step-table block precedes the prose block"); return css.slice(a, b); };
  assert.ok(block(chat).length > 200, "the block with its rationale");
  assert.equal(block(chat), block(feed), "the step table and its comment mirror exactly");
});

test("both sheets: the title bar wraps and its action row shrinks and wraps to the right edge while the bare classes stay as they were; a disabled or aria-disabled bar button is dimmed with an inert hover; the readout is a fixed slot, empty at the default", () => {
  for (const [name, css] of SHEETS) {
    const bar = decls(ruleOf(css, ".fileview-bar {"));
    assert.ok(bar.includes("flex-wrap: wrap") && bar.includes("gap: 6px 10px"), name + ": the bar wraps, 6px between its lines");
    assert.deepEqual(decls(ruleOf(css, ".fileview-bar .fileview-name {")), ["flex: 1 1 0", "min-width: 12em"], name + ": in the bar the path keeps 12em and takes the rest of a wide bar");
    const nm = decls(ruleOf(css, ".fileview-name {"));
    assert.ok(nm.includes("flex: 1 1 auto") && nm.includes("min-width: 0"), name + ": the class alone shrinks freely");
    const barActs = decls(ruleOf(css, ".fileview-bar .fileview-acts {"));
    for (const d of ["flex: 0 1 auto", "min-width: 0", "margin-left: auto", "flex-wrap: wrap", "justify-content: flex-end"]) assert.ok(barActs.includes(d), name + ": in the bar the action row " + d);
    assert.deepEqual(decls(ruleOf(css, ".fileview-acts {")), ["flex: 0 0 auto", "display: flex", "align-items: center", "gap: 6px"], name + ": the class alone is one rigid row (the file browser's bar wears it outside any title bar)");
    assert.ok(!decls(ruleOf(css, ".fb-bar {")).some((d) => d.startsWith("flex-wrap")), name + ": .fb-bar has no wrap of its own");
    // one disabled dress for every bar button: the GitHub unit's no-link state (disabled) and the control's ends (aria-disabled)
    assert.deepEqual(decls(ruleOf(css, '.fileview-btn:disabled, .fileview-btn[aria-disabled="true"] {')), ["opacity: 0.55", "cursor: default"], name + ": dimmed, default cursor");
    assert.deepEqual(decls(ruleOf(css, '.fileview-btn:disabled:hover, .fileview-btn[aria-disabled="true"]:hover {')), ["border-color: var(--card-border)", "color: var(--fg)", "background: transparent"], name + ": the hover is inert (the rest colours, not the accent)");
    assert.deepEqual(decls(ruleOf(css, '.fileview-btn:disabled:active, .fileview-btn[aria-disabled="true"]:active {')), ["transform: none"], name + ": no press pulse");
    assert.doesNotMatch(css, /\.fileview-gh \.fileview-btn:disabled/, name + ": the GitHub unit's disabled rules are the bar's now, not its own");
    // the readout: one width whatever it says, and an empty slot (not none) at the default
    assert.deepEqual(decls(ruleOf(css, ".fileview-size-reset {")), ["min-width: 5.5em", "box-sizing: border-box", "text-align: center", "font-variant-numeric: tabular-nums"], name + ": a slot of one width");
    assert.deepEqual(decls(ruleOf(css, ".fileview-size-reset.fileview-size-default {")), ["visibility: hidden"], name + ": the empty slot keeps its width and leaves the tab order");
  }
  const [chat, feed] = SHEETS.map(([, css]) => css);
  for (const head of [".fileview-bar {", ".fileview-name {", ".fileview-acts {", ".fileview-bar .fileview-name {", ".fileview-bar .fileview-acts {",
    '.fileview-btn:disabled, .fileview-btn[aria-disabled="true"] {', ".fileview-size-reset {", ".fileview-size-reset.fileview-size-default {"]) {
    assert.equal(ruleOf(chat, head), ruleOf(feed, head), head + " mirrors exactly");
  }
});

// ── the browser leg: a real layout over each sheet, through a child driver ─────────────────────────
// The layout claims the sheet pins cannot show (the page never widens, a wide table scrolls on its own, a table in a
// quote or a list item keeps the prose width, the action row drops below the path and the close button stays on the
// card, A− and A+ hold still when the readout fills, the file browser's bar keeps one line) are
// measured in headless Chromium. The measurement runs in a standalone driver (the test bundle is CommonJS without
// top-level await, and esbuild must never try to bundle playwright); the driver exits 3 without playwright or a
// browser, and the leg skips loudly there.
const LONG = "unbreakable".repeat(5);   // wide enough to push the table past the column at 1000px, narrow enough that the body still holds it
const SVG = (w: number) => `data:image/svg+xml,${encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="120"><rect width="${w}" height="120" fill="#369"/></svg>`)}`;
const ROWS = Array.from({ length: 3 }, (_, i) => `<tr><td>row ${i} alpha beta gamma delta</td><td>a fairly long cell of prose that keeps going on for a while</td><td>${LONG}</td><td>another long cell with many words in it to widen the table</td><td>five</td><td>six more text here</td></tr>`).join("");
/** A six-column table whose columns want more than the prose measure: at the top level, inside a quote and inside a list item. */
const TABLE = (id: string) => `<table id="${id}"><thead><tr><th>one</th><th>two</th><th>three</th><th>four</th><th>five</th><th>six</th></tr></thead><tbody>${ROWS}</tbody></table>`;
const ROW = (t: string) => `<span class="cl"><span class="ct">${t}</span></span>`;
const MD = `<h1 id="h1">Report</h1><h2 id="h2">Findings</h2><h3 id="h3">Detail</h3><p id="p">Prose ${"lorem ipsum ".repeat(40)}</p>
${TABLE("t")}
<blockquote id="bq"><p>A quoted note with a table of its own.</p>${TABLE("tq")}</blockquote>
<ul><li>A first item.</li><li id="li">An item with a table of its own.${TABLE("tl")}</li></ul>
<pre id="pre"><code>${"const x = 1; ".repeat(30)}</code></pre>
<pre id="pre2"><code>const y = 2;</code></pre>
<pre id="pre3"><code style="--ln-digits: 1">${ROW("a")}${ROW("")}${ROW("b")}</code></pre>
<pre id="pre4"><code style="--ln-digits: 5">${ROW("a")}</code></pre>
<pre id="pre5" class="has-copy"><code>z</code><button class="code-copy" id="copy">Copy</button></pre>
<ul><li id="task" class="task-list-item"><input type="checkbox" disabled> A task</li></ul>
<p id="lw">${"x".repeat(140)}</p>
<p><img id="im" width="900" height="120" src="${SVG(900)}"></p>
<img id="im2" width="1600" height="120" src="${SVG(1600)}">
<svg id="sv" xmlns="http://www.w3.org/2000/svg" width="1600" height="120" viewBox="0 0 1600 120"><rect width="1600" height="120" fill="#693"/></svg>`;
const sheet = (css: string) => `<!DOCTYPE html><html><head><meta charset="utf-8"><style>${css}</style></head>`;
/** The modal as openFileView builds it, over a rendered markdown body. */
const LAYOUT_PAGE = (css: string) => sheet(css) + `<body class="fileview-open"><div id="romp-fileview"><div class="fileview" id="root"><div class="fileview-bar"><div class="fileview-name"><span class="fileview-dir">/tmp/notes-api/docs/</span><span class="fileview-base">report.md</span></div><div class="fileview-acts"><button class="fileview-btn on">Rendered</button><button class="fileview-btn">Raw</button><button class="fileview-btn fileview-size">A−</button><button class="fileview-btn fileview-size fileview-size-reset fileview-size-default">100%</button><button class="fileview-btn fileview-size">A+</button><button class="fileview-btn fileview-close">✕</button></div></div>
<div class="fileview-body" id="body"><div class="fileview-md" id="md">${MD}</div></div></div></div></body></html>`;
const LAYOUT_MEASURE = `(() => {
  const q = (s) => document.querySelector(s);
  const w = (s) => q(s).getBoundingClientRect().width;
  const fz = (s) => parseFloat(getComputedStyle(q(s)).fontSize);
  const body = q("#body"), t = q("#t"), tq = q("#tq"), tl = q("#tl"), pre = q("#pre"), md = q("#md"), cs = getComputedStyle(md);
  const probe = document.createElement("span"); probe.textContent = "0".repeat(80); probe.style.whiteSpace = "nowrap"; probe.style.position = "absolute";
  md.appendChild(probe); const ch80 = probe.getBoundingClientRect().width; probe.remove();
  const rows = Array.from(q("#pre3 code").children).map((r) => r.getBoundingClientRect().height);
  const ctOff = (s) => q(s + " .ct").getBoundingClientRect().left - q(s + " code").getBoundingClientRect().left;
  const r = (s) => q(s).getBoundingClientRect();
  return { win: innerWidth, docScroll: document.documentElement.scrollWidth, bodyClient: body.clientWidth, bodyScroll: body.scrollWidth,
    padL: parseFloat(cs.paddingLeft), padR: parseFloat(cs.paddingRight), ch80, pLeft: r("#p").left, pRight: r("#p").right, tLeft: r("#t").left, tRight: r("#t").right,
    h2Font: fz("#h2"), h3Font: fz("#h3"), rows, ct1: ctOff("#pre3"), ct5: ctOff("#pre4"),
    taskStyle: getComputedStyle(q("#task")).listStyleType, taskScheme: getComputedStyle(q("#task input")).colorScheme,
    md: w("#md"), p: w("#p"), t: w("#t"), tClient: t.clientWidth, tScroll: t.scrollWidth, pre: w("#pre"), preClient: pre.clientWidth, preScroll: pre.scrollWidth,
    bq: w("#bq"), tq: w("#tq"), tqClient: tq.clientWidth, tqScroll: tq.scrollWidth, li: w("#li"), tl: w("#tl"), tlClient: tl.clientWidth, tlScroll: tl.scrollWidth,
    pre2: w("#pre2"), lw: w("#lw"), img: w("#im"), img2: w("#im2"), svg: w("#sv"), mdFont: fz("#md"), h1Font: fz("#h1"), codeFont: fz("#pre code") };
})()`;
/** The print sheet over the same page: what leaves, what turns black, what a table becomes. */
const PRINT_MEASURE = `(() => {
  const q = (s) => document.querySelector(s); const cs = (s) => getComputedStyle(q(s));
  return { bar: cs(".fileview-bar").display, copy: cs("#copy").display, md: cs("#md").color, h1: cs("#h1").color, code: cs("#pre code").color, dim: cs("#h1").borderBottomColor,
    table: cs("#t").display, bodyBg: getComputedStyle(document.body).backgroundColor, rootBg: getComputedStyle(document.documentElement).backgroundColor,
    bodyOverflow: cs("#body").overflowY, scheme: cs("#task input").colorScheme, tWidth: q("#t").getBoundingClientRect().width, bodyW: q("#body").clientWidth, docH: document.documentElement.scrollHeight, winH: innerHeight };
})()`;
/** The bar a kernel-answered markdown file shows: the format toggles, the control, Edit, the GitHub unit with its caption,
 *  Download, Copy path and the close button, behind a deep path and a session chip. */
const BAR_PAGE = (css: string) => sheet(css) + `<body class="fileview-open"><div id="romp-fileview"><div class="fileview" id="root"><div class="fileview-bar" id="bar"><div class="fileview-name" id="name"><span class="fileview-dir">/tmp/notes-api/services/api/internal/handlers/</span><span class="fileview-base">report.md</span></div><span class="fileview-sess">api</span><div class="fileview-acts" id="acts"><button class="fileview-btn on">Rendered</button><button class="fileview-btn">Raw</button><button class="fileview-btn fileview-size" id="down">A−</button><button class="fileview-btn fileview-size fileview-size-reset fileview-size-default" id="reset">100%</button><button class="fileview-btn fileview-size" id="up">A+</button><button class="fileview-btn">Edit</button><span class="fileview-gh"><span class="fileview-gh-why">not committed (staged only)</span><button class="fileview-btn" disabled>GitHub ↗</button></span><button class="fileview-btn">Download</button><button class="fileview-btn">Copy path</button><button class="fileview-btn fileview-close" id="close">✕</button></div></div>
<div class="fileview-body" id="body"><div class="fileview-md"><p>Prose.</p></div></div></div></div></body></html>`;
const BAR_MEASURE = `(() => {
  const r = (id) => { const b = document.getElementById(id).getBoundingClientRect(); return { l: b.left, r: b.right, t: b.top, b: b.bottom, w: b.width }; };
  const cs = (id) => getComputedStyle(document.getElementById(id));
  return { win: innerWidth, card: r("root"), bar: r("bar"), name: r("name"), acts: r("acts"), close: r("close"), down: r("down"), up: r("up"), reset: r("reset"),
    resetVis: cs("reset").visibility, nameFont: parseFloat(cs("name").fontSize), barPadRight: parseFloat(cs("bar").paddingRight) };
})()`;
const READOUT_ON = `(() => { const b = document.getElementById("reset"); b.classList.remove("fileview-size-default"); b.textContent = "115%"; })()`;
const READOUT_OFF = `(() => { const b = document.getElementById("reset"); b.classList.add("fileview-size-default"); b.textContent = "100%"; })()`;
/** The file browser's bar (file-browse.ts): the crumb trail and, wearing .fileview-acts outside any title bar, Hidden and the close button. */
const CRUMBS = ["/", "tmp", "notes-api", "services", "api", "internal", "handlers", "v2", "tests", "fixtures", "golden"];
const FB_PAGE = (css: string) => sheet(css) + `<body class="filebrowse-open"><div id="romp-filebrowse"><div class="filebrowse"><div class="fb-bar" id="fbbar"><div class="fb-crumbs" id="fb-crumbs">${CRUMBS.map((c, i) => (i ? '<span class="fb-crumb-sep">/</span>' : "") + '<span class="fb-crumb">' + c + "</span>").join("")}</div><div class="fileview-acts" id="acts"><button class="fileview-btn" id="hid">Hidden</button><button class="fileview-btn fileview-close" id="fbclose">✕</button></div></div><div class="fb-list"></div></div></div></body></html>`;
const FB_MEASURE = `(() => {
  const g = (id) => document.getElementById(id);
  const bar = g("fbbar"), crumbs = g("fb-crumbs"), acts = g("acts"), hid = g("hid").getBoundingClientRect(), close = g("fbclose").getBoundingClientRect();
  return { win: innerWidth, barH: bar.getBoundingClientRect().height, barOver: bar.scrollWidth - bar.clientWidth, hidTop: hid.top, closeTop: close.top, closeLeft: close.left, closeRight: close.right,
    acts: acts.getBoundingClientRect().width, wrap: getComputedStyle(acts).flexWrap, crumbsClient: crumbs.clientWidth, crumbsScroll: crumbs.scrollWidth };
})()`;
// mdBlock's task stamp, run in the page over marked's own output for a synthetic document, sanitized as mdBlock sanitizes
// it (the shared sanitizer, md-sanitize.ts, bundled from the source with esbuild and added to the page as a script; the
// body it returns is adopted the way mdBlock adopts it) and then stamped by the statement lifted from mdBlock. marked
// emits a task item's checkbox as the li's first node (inside its first paragraph in a loose list); a checkbox an author's
// raw HTML puts after the item's text matches the stamp's :first-child selector (elements alone count) and must not make a
// task item of the item. A tight list, a numbered one, a loose one (every item of a loose list is a paragraph, the mid-item
// case included), an enabled box (the sanitizer makes it disabled before the stamp sees it, so it opens its item like
// marked's own), a raw disabled box that opens its item, and an author's own class.
const STAMP_MD = [
  "- [ ] open task", "- [x] done task", "- plain item", '- text then <input type="checkbox" disabled> mid-item',
  '- **bold** then <input type="checkbox" disabled> after bold', '- <input type="checkbox"> enabled first', '- <input type="checkbox" disabled> raw first',
  "", "1. [ ] numbered task", "", "- [ ] loose task", "", "  with a second paragraph", "", '- loose text then <input type="checkbox" disabled> loose mid-item',
  "", '<ul><li class="task-list-item"><input type="checkbox" disabled> an author item</li></ul>', "",
].join("\n");
/** The real sanitizer for the page: md-sanitize.ts and the DOMPurify under it, bundled from the source (esbuild and the
 *  packages resolve from the extension package, as the test bundle itself was built), exposing sanitizeMd on the window. */
function sanitizerJs(): string {
  const requireExt = createRequire(path.resolve(process.cwd(), "package.json"));
  const esbuild = requireExt("esbuild");
  const r = esbuild.buildSync({
    stdin: { contents: 'import { sanitizeMd } from "./md-sanitize"; (window as any).sanitizeMd = sanitizeMd;', resolveDir: path.resolve(process.cwd(), "..", "ui", "webview"), loader: "ts", sourcefile: "fv-textsize-sanitizer-entry.ts" },
    bundle: true, write: false, format: "iife", platform: "browser", target: "es2020", nodePaths: [path.resolve(process.cwd(), "node_modules")], logLevel: "silent",
  });
  return r.outputFiles[0].text as string;
}
const STAMP_CODE = (() => { const at = VIEW.indexOf("box.querySelectorAll('li > input"); return at < 0 ? "" : VIEW.slice(at, VIEW.indexOf("\n  });", at) + 6); })();
const STAMP_PAGE = (css: string) => sheet(css) + `<body class="fileview-open"><div id="romp-fileview"><div class="fileview" id="root"><div class="fileview-body" id="body"><div class="fileview-md" id="md"></div></div></div></div></body></html>`;
const STAMP_PREP = `(() => { const box = document.getElementById("md"); box.replaceChildren(...Array.from(sanitizeMd(${JSON.stringify(marked.parse(STAMP_MD) as string)}).childNodes)); ${STAMP_CODE} })()`;
const STAMP_MEASURE = `(() => Array.from(document.querySelectorAll("#md li")).map((li) => {
  const input = li.querySelector("input"), lr = li.getBoundingClientRect();
  return { text: (li.textContent || "").replace(/\\s+/g, " ").trim(), stamped: li.classList.contains("task-list-item"), bullet: getComputedStyle(li).listStyleType,
    input: input ? { disabled: input.disabled, checked: input.checked, marginLeft: parseFloat(getComputedStyle(input).marginLeft), left: input.getBoundingClientRect().left - lr.left, scheme: getComputedStyle(input).colorScheme } : null };
}))()`;
type Step = { width?: number; size?: number; prep?: string; media?: string; measure?: string; tag: string };
type Case = { name: string; html: string; width: number; measure: string; steps: Step[]; inline?: string[] };   // inline: script text added to the page after its HTML
type Rows = Record<string, { rows: Array<{ step: Step; got: any }>; errors: string[] }>;
/** A step, and the body's content width written on each top-level table the way the viewer's width observer writes it
 *  (file-view.ts watchBodyWidth: --fv-body-w on the tables themselves, after every paint and every width change); the
 *  page here carries no script, so the prep stands in for the observer. */
const step = (n: number) => `(() => { document.getElementById("root").dataset.fvText = "${n}"; const w = document.getElementById("body").clientWidth + "px"; for (const t of document.querySelectorAll("#md > table")) t.style.setProperty("--fv-body-w", w); })()`;
function cases(): Case[] {
  const out: Case[] = [];
  const sanitizer = sanitizerJs();
  for (const [name, css] of SHEETS) {
    out.push({ name: "layout/" + name, html: LAYOUT_PAGE(css), width: 1000, measure: LAYOUT_MEASURE, steps: [
      { size: 100, prep: step(100), tag: "@1000/100" }, { size: 150, prep: step(150), tag: "@1000/150" },
      { width: 420, size: 100, prep: step(100), tag: "@420/100" }, { size: 150, prep: step(150), tag: "@420/150" },
      { width: 1000, size: 100, prep: step(100), media: "print", measure: PRINT_MEASURE, tag: "@1000 print" },
    ] });
    const bar: Step[] = [];
    for (const w of [380, 420, 480, 600, 1000, 1400]) { bar.push({ width: w, prep: READOUT_OFF, tag: "@" + w + " default" }); bar.push({ prep: READOUT_ON, tag: "@" + w + " readout" }); }
    out.push({ name: "bar/" + name, html: BAR_PAGE(css), width: 1000, measure: BAR_MEASURE, steps: bar });
    out.push({ name: "fb/" + name, html: FB_PAGE(css), width: 1000, measure: FB_MEASURE, steps: [1000, 480, 360, 320].map((w) => ({ width: w, tag: "@" + w })) });
    out.push({ name: "stamp/" + name, html: STAMP_PAGE(css), width: 1000, measure: STAMP_MEASURE, inline: [sanitizer], steps: [{ prep: STAMP_PREP, tag: "stamp" }] });
  }
  return out;
}
// The driver: playwright out of the extension package's node_modules, exit 3 when it or a browser is missing.
const DRIVER = `
import { createRequire } from "node:module";
import fs from "node:fs";
const require = createRequire(process.env.EXT_PKG);
let chromium;
try { chromium = require("playwright").chromium; } catch (e) { process.exit(3); }
let browser;
try { browser = await chromium.launch(); } catch (e) { process.exit(3); }
const spec = JSON.parse(fs.readFileSync(process.env.SPEC_PATH, "utf8"));
const out = {};
for (const c of spec) {
  const page = await browser.newPage({ viewport: { width: c.width, height: 900 } });
  const errors = [];
  page.on("pageerror", (e) => { errors.push(e.message); });
  await page.setContent(c.html);
  for (const s of c.inline || []) await page.addScriptTag({ content: s });
  const rows = [];
  for (const s of c.steps) {
    if (s.width) await page.setViewportSize({ width: s.width, height: 900 });
    if (s.prep) await page.evaluate(s.prep);
    if (s.media) await page.emulateMedia({ media: s.media });
    rows.push({ step: s, got: await page.evaluate(s.measure || c.measure) });
  }
  out[c.name] = { rows, errors };
  await page.close();
}
fs.writeSync(1, "RESULT:" + JSON.stringify(out) + "\\n");
await browser.close();
process.exit(0);
`;
function measure(): Rows | null {
  const os = require("node:os");
  const cp = require("node:child_process");
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "fv-textsize-"));
  const driver = path.join(dir, "driver.mjs"); fs.writeFileSync(driver, DRIVER);
  const specPath = path.join(dir, "spec.json"); fs.writeFileSync(specPath, JSON.stringify(cases()));
  try {
    const p = cp.spawnSync(process.execPath, [driver], { encoding: "utf8", timeout: 180000, maxBuffer: 64 * 1024 * 1024,   // the running node, never PATH
      env: { ...process.env, EXT_PKG: path.resolve(process.cwd(), "package.json"), SPEC_PATH: specPath } });
    if (p.status === 3) return null;                                  // no playwright / no browser here
    if (p.status !== 0) throw new Error("layout driver failed: " + String(p.stderr || p.stdout || p.error || "").slice(-800));
    const line = (p.stdout || "").split("\n").find((l: string) => l.startsWith("RESULT:"));
    if (!line) throw new Error("layout driver printed no result: " + (p.stdout || "").slice(-400));
    return JSON.parse(line.slice("RESULT:".length));
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
}
const m = measure();
const skip = m ? false : "no Playwright browser here (CI installs none); the layout claims rest on the sheet pins above";
const near = (a: number, b: number, what: string) => assert.ok(Math.abs(a - b) < 1, what + ": " + a + " vs " + b);

test("in a browser: the page never widens at 1000 and 420px, at 100% and 150%, in both sheets; prose and code keep the measure (80 of the root's ch, centred, whole pixels) and a table grows evenly out of the column up to the body while a table in a quote or a list item keeps the prose width; the heading ladder and the fence rows measure; at 150% every text size and the measure grow together; narrow, a table scrolls on its own; in print the file alone prints black on white", { skip }, () => {
  for (const [name] of SHEETS) {
    const c = m!["layout/" + name];
    assert.deepEqual(c.errors, [], name + ": no script error in the page");
    const at = (tag: string) => c.rows.find((r) => r.step.tag === tag)!.got;
    for (const r of c.rows.filter((x) => !x.step.media)) {
      const l = r.got, cell = name + " " + r.step.tag;
      assert.equal(l.bodyScroll, l.bodyClient, cell + ": the body does not scroll sideways");
      assert.equal(l.docScroll, l.win, cell + ": the page is the window");
      const col = l.bodyClient - 36 + 0.5;                            // the root's 18px padding a side
      assert.ok(l.pre <= col && l.pre2 <= col && l.lw <= col && l.img <= col, cell + ": code, the long string and the image paragraph fit the column");
      assert.ok(l.img2 <= col, cell + ": the bare <img> line fits the column too (" + l.img2 + " in " + (l.bodyClient - 36) + "): its own cap outranks the measure");
      assert.ok(l.svg <= col, cell + ": a wide inline svg block, a direct child of the root, fits the column too (" + l.svg + " in " + (l.bodyClient - 36) + "): the element-level media cap holds it to the root's content box");
      assert.ok(l.preScroll <= l.preClient + 1, cell + ": the long code line wraps inside its block");
      near(l.md, l.bodyClient, cell + ": the root is the body's width");
      assert.ok(l.bq <= l.p + 0.5 && l.tq <= l.bq + 0.5 && l.li <= l.p + 0.5 && l.tl <= l.li + 0.5,
        cell + ": a quote and a list item keep the prose width and the table inside each keeps to it (quote " + l.bq + ", its table " + l.tq + "; item " + l.li + ", its table " + l.tl + "; prose " + l.p + ")");
    }
    const base = at("@1000/100"), big = at("@1000/150");
    for (const r of c.rows.filter((x) => !x.step.media)) {
      const l = r.got, cell = name + " " + r.step.tag;
      // the measure: 80 of the root's own ch, centred as inline padding rounded down to whole pixels, never under 18px; when the
      // column cannot hold 80ch the padding is its 18px floor and the prose follows the viewer
      const want = Math.min(l.ch80, l.bodyClient - 36);
      assert.ok(l.p >= want - 0.5 && l.p <= want + 2.5, cell + ": the prose measure is 80ch or the column (" + l.p + ", 80ch " + l.ch80 + ", column " + (l.bodyClient - 36) + ")");
      near(l.p, l.bodyClient - l.padL - l.padR, cell + ": the measure is the root's content box, laid as its inline padding");
      assert.equal(l.padL, l.padR, cell + ": centred (" + l.padL + " / " + l.padR + ")");
      assert.ok(Number.isInteger(l.padL) && l.padL >= 18, cell + ": whole pixels, never under 18px (" + l.padL + ")");
      near(l.pre, l.p, cell + ": a code block keeps the measure"); near(l.pre2, l.p, cell + ": a two-line snippet too, no viewer-wide block");
      assert.ok(l.tq <= l.p + 0.5 && l.tl <= l.p + 0.5, cell + ": the same table in a quote (" + l.tq + ") or a list item (" + l.tl + ") keeps the prose measure");
      assert.ok(l.img <= l.p + 0.5 && l.lw <= l.p + 0.5 && l.img2 <= l.p + 0.5 && l.svg <= l.p + 0.5, cell + ": both pictures, the inline svg and an unbreakable string stay in the measure");
      // the ladder, em of the prose: 2 / 1.5 / 1.25
      near(l.h1Font, l.mdFont * 2, cell + ": h1 is 2em of the prose"); near(l.h2Font, l.mdFont * 1.5, cell + ": h2 is 1.5em"); near(l.h3Font, l.mdFont * 1.25, cell + ": h3 is 1.25em");
      // the fence rows: a text row, a blank row and the last row are each one line-height of the code; the gutter's basis
      // follows the fence's digit count (2.5em of the gutter's own 0.92em for one digit, plus the 0.85em gap)
      assert.equal(l.rows.length, 3);
      for (const h of l.rows) near(h, l.codeFont * 1.5, cell + ": a row is the code's line-height (" + l.rows.join(", ") + ")");
      near(l.ct1, l.codeFont * 0.92 * 3.35, cell + ": the one-digit gutter is 2.5em plus the gap (" + l.ct1 + ")");
      assert.ok(l.ct5 > l.ct1 + 3, cell + ": a five-digit fence's gutter is wider than a one-digit fence's (" + l.ct5 + " vs " + l.ct1 + ")");
      // a task item: no bullet beside the box, the box drawn for the page's scheme (no theme class here: dark)
      assert.equal(l.taskStyle, "none", cell + ": a task item has no bullet"); assert.equal(l.taskScheme, "dark", cell + ": the box follows the page's scheme");
    }
    // at 1000px and 100% the column holds 80ch with room to spare, and a table wider than the column grows out of it evenly
    assert.ok(base.padL > 18, name + " @1000/100: room to spare (" + base.padL + "px a side)");
    assert.ok(base.t > base.p + 1 && base.t <= base.bodyClient - 36 + 0.5, name + " @1000/100: the table grows out of the column (" + base.t + " past " + base.p + "), inside the body's inset");
    assert.equal(base.tScroll, base.tClient, name + " @1000/100: room enough, so the table does not scroll");
    assert.ok(Math.abs((base.pLeft - base.tLeft) - (base.tRight - base.pRight)) <= 1.5, name + " @1000/100: evenly into both gutters (" + (base.pLeft - base.tLeft) + " left, " + (base.tRight - base.pRight) + " right)");
    assert.ok(Math.abs(base.mdFont - 13 * 1.15) < 0.05, name + " @100%: the prose is 1.15 times the page's 13px (" + base.mdFont + ")");
    assert.equal(base.codeFont, 12, name + " @100%: fenced code at 12px, the size it had");
    near(big.mdFont, base.mdFont * 1.5, name + " @150%: the prose"); assert.equal(big.codeFont, 18, name + " @150%: fenced code");
    assert.ok(big.ch80 > base.ch80 * 1.4, name + " @150%: the measure's unit grows with the text (" + big.ch80 + " from " + base.ch80 + ")");
    for (const tag of ["@420/100", "@420/150"]) {
      const l = at(tag), cell = name + " " + tag;
      assert.equal(l.padL, 18, cell + ": the inset floor holds when the column cannot hold 80ch");
      near(l.t, l.bodyClient - 36, cell + ": the table is the column");
      assert.ok(l.tScroll > l.tClient + 100, cell + ": the unbreakable cell scrolls inside the table (" + l.tScroll + " in " + l.tClient + ")");
      near(l.p, l.bodyClient - 36, cell + ": the prose follows the viewer below its measure");
      near(l.img2, l.bodyClient - 36, cell + ": the wide banner is the column");
      near(l.svg, l.bodyClient - 36, cell + ": the wide inline svg is the column");
    }
    for (const tag of ["@1000/150", "@420/100", "@420/150"]) {
      const l = at(tag), cell = name + " " + tag;
      assert.ok(l.tqScroll > l.tqClient + 100 && l.tlScroll > l.tlClient + 100,
        cell + ": a nested table its quote or item cannot hold scrolls inside itself (" + l.tqScroll + " in " + l.tqClient + "; " + l.tlScroll + " in " + l.tlClient + ")");
    }
    // print: the file alone, black on white, as many pages as it needs
    const print = at("@1000 print"), cell = name + " print";
    assert.equal(print.bar, "none", cell + ": the title bar leaves"); assert.equal(print.copy, "none", cell + ": the Copy buttons leave");
    for (const [k, v] of Object.entries({ md: print.md, h1: print.h1, code: print.code, rule: print.dim })) assert.equal(v, "rgb(0, 0, 0)", cell + ": " + k + " in black");
    assert.equal(print.bodyBg, "rgb(255, 255, 255)", cell + ": the page is white"); assert.equal(print.rootBg, "rgb(255, 255, 255)", cell + ": the canvas too");
    assert.equal(print.table, "table", cell + ": a table is a table again"); assert.equal(print.scheme, "light", cell + ": the task box is drawn light");
    assert.equal(print.bodyOverflow, "visible", cell + ": the body does not clip to one screen"); assert.ok(print.docH > print.winH, cell + ": the document runs past one window's height (" + print.docH + " over " + print.winH + ")");
    assert.ok(print.tWidth > 0 && print.tWidth <= print.bodyW - 36 + 0.5, cell + ": the wide table keeps the body's room less the inset (" + print.tWidth + " in " + print.bodyW + ")");
  }
});

test("in a browser: from 380 to 1400px in both modals the close button and every action stay on the card; the path keeps 12em and the action row ends at the bar's edge; up to 600px the row drops to the line below the path and at 1400 the two share a line; A− and A+ hold still when the readout fills after the first press", { skip }, () => {
  for (const [name] of SHEETS) {
    const c = m!["bar/" + name];
    assert.deepEqual(c.errors, [], name + ": no script error in the page");
    for (let i = 0; i < c.rows.length; i += 2) {
      const off = c.rows[i].got, on = c.rows[i + 1].got, cell = name + " " + c.rows[i].step.tag.split(" ")[0];
      for (const [g, what] of [[off, "at the default"], [on, "with the readout showing"]] as Array<[any, string]>) {
        const inside = g.close.l >= g.card.l - 0.5 && g.close.r <= g.card.r + 0.5 && g.close.t >= g.card.t - 0.5 && g.close.b <= g.card.b + 0.5;
        assert.ok(inside, cell + " " + what + ": the close button lies inside the card (close " + JSON.stringify(g.close) + ", card " + JSON.stringify(g.card) + ")");
        assert.ok(g.name.w >= 12 * g.nameFont - 0.5, cell + " " + what + ": the path keeps 12em (" + g.name.w + "px at " + g.nameFont + "px)");
        near(g.acts.r, g.bar.r - g.barPadRight, cell + " " + what + ": the action row ends at the bar's right edge");
        // the bar's own wrap: three more buttons no longer fit beside a deep path below about 600px, so the row drops to
        // the line below (the row's own wrap alone would keep it beside the path, squeezed into a column); wide, one line
        if (g.win <= 600) assert.ok(g.acts.t >= g.name.b - 0.5, cell + " " + what + ": the action row is the line below the path (row top " + g.acts.t + ", path bottom " + g.name.b + ")");
        if (g.win >= 1400) assert.ok(g.acts.t < g.name.b - 0.5 && g.acts.b > g.name.t + 0.5, cell + " " + what + ": room for both, so the path and the action row share a line");
      }
      assert.equal(off.resetVis, "hidden", cell + ": at the default the readout's slot is empty by visibility");
      assert.ok(off.reset.w > 20, cell + ": and keeps its width (" + off.reset.w + "px)");
      assert.equal(on.resetVis, "visible", cell + ": off the default the readout shows");
      near(off.down.l, on.down.l, cell + ": A− does not move when the readout fills"); near(off.down.t, on.down.t, cell + ": A− stays on its line");
      near(off.up.l, on.up.l, cell + ": A+ does not move when the readout fills"); near(off.up.t, on.up.t, cell + ": A+ stays on its line");
    }
  }
});

test("in a browser: the file browser's bar stays one line at 320, 360, 480 and 1000px in both sheets, its two buttons holding their width while the crumb trail gives up room", { skip }, () => {
  for (const [name] of SHEETS) {
    const c = m!["fb/" + name];
    assert.deepEqual(c.errors, [], name + ": no script error in the page");
    const wide = c.rows[0].got;
    assert.equal(wide.win, 1000);
    for (const r of c.rows) {
      const g = r.got, cell = name + " " + r.step.tag;
      assert.equal(g.hidTop, g.closeTop, cell + ": Hidden and the close button share a line");
      near(g.barH, wide.barH, cell + ": the bar is the height it has at 1000px (one line, not two)");
      near(g.acts, wide.acts, cell + ": the action row holds its width");
      assert.equal(g.wrap, "nowrap", cell + ": the row does not wrap");
      assert.ok(g.closeLeft >= 0 && g.closeRight <= g.win + 0.5, cell + ": the close button lies inside the window: x " + g.closeLeft + " to " + g.closeRight);
      assert.equal(g.barOver, 0, cell + ": the bar overflows nothing");
      if (g.win < 1000) assert.ok(g.crumbsScroll > g.crumbsClient, cell + ": the crumb trail is what gives up room (" + g.crumbsScroll + " in " + g.crumbsClient + ")");
    }
  }
});

test("in a browser: mdBlock's task stamp over marked's own output, sanitized as mdBlock sanitizes it, in both sheets: a disabled checkbox that opens its item (a tight list, a numbered one, a loose one's first paragraph, an author's raw box) makes a task item with no bullet and the box pulled into the gutter; an author's enabled box is made inert by the sanitizer and opens its item too; a box after the item's text leaves the item and its bullet as the file wrote them; an author's own class is kept", { skip }, () => {
  assert.ok(STAMP_CODE, "the stamp statement is lifted from the source");
  assert.match(VIEW, /box\.replaceChildren\(\.\.\.Array\.from\(sanitizeMd\(dirty, mintHeadingIds\)\.childNodes\)\);/, "mdBlock adopts the shared sanitizer's body, as the page here does (the heading ids minted inside the call, before the math fill)");
  type Row = { text: string; stamped: boolean; bullet: string; input: { disabled: boolean; checked: boolean; marginLeft: number; left: number; scheme: string } | null };
  for (const [name] of SHEETS) {
    const c = m!["stamp/" + name];
    assert.deepEqual(c.errors, [], name + ": no script error in the page");
    const rows = c.rows[0].got as Row[];
    assert.equal(rows.length, 11, name + ": every item of the document is in the page (" + rows.map((r) => r.text).join(" | ") + ")");
    const item = (start: string) => { const r = rows.find((x) => x.text.startsWith(start)); assert.ok(r, name + ": an item starting " + JSON.stringify(start)); return r!; };
    for (const start of ["open task", "done task", "numbered task", "loose task", "enabled first", "raw first", "an author item"]) {
      const r = item(start), cell = name + " " + JSON.stringify(start);
      assert.equal(r.stamped, true, cell + ": a task item");
      assert.equal(r.bullet, "none", cell + ": no bullet beside the box");
      assert.ok(r.input && r.input.disabled, cell + ": the disabled box survived the sanitize");
      assert.ok(r.input!.marginLeft < -13, cell + ": the box is pulled into the gutter (" + r.input!.marginLeft + ")");
      assert.ok(r.input!.left < 0, cell + ": the box sits before the item's edge, where the bullet was (" + r.input!.left + ")");
      assert.equal(r.input!.scheme, "dark", cell + ": drawn for the page's scheme (no theme class here: dark)");
    }
    assert.equal(item("done task").input!.checked, true, name + ": a checked box stays checked");
    // an author's enabled box is made inert by the sanitizer (md-sanitize.ts keeps marked's checkbox as the one control a note
    // carries, disabled), so by the time the stamp runs it is a disabled box opening its item, and a task item like the rest
    assert.equal(item("enabled first").input!.disabled, true, name + ": the sanitizer disabled the author's enabled box before the stamp");
    for (const start of ["plain item", "text then", "bold then", "loose text then"]) {
      const r = item(start), cell = name + " " + JSON.stringify(start);
      assert.equal(r.stamped, false, cell + ": not a task item");
      assert.equal(r.bullet, "disc", cell + ": the bullet stays");
      if (start !== "plain item") {
        assert.ok(r.input, cell + ": the sanitize kept the author's box");
        assert.ok(r.input!.marginLeft >= 0 && r.input!.left >= 0, cell + ": the box keeps the control's own margin, inside the item, not pulled into the gutter (" + r.input!.marginLeft + ", " + r.input!.left + ")");
        assert.ok(r.input!.left > 20, cell + ": the box sits after the item's text, where the file put it (" + r.input!.left + ")");
      }
    }
  }
});


// ── the fork's browser legs: the sheets over a static page in every document (the Files pane's Recent row among them), then the
// REAL module bundled into a page. Playwright out of the extension's node_modules; skipped LOUDLY without a browser (CI installs none). ──
let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }
const PANE_CSS = web("files-pane.css");
async function inBrowser(t: any, body: (browser: any) => Promise<void>): Promise<void> {
  if (!pw) { t.skip("playwright is not installed under vscode-extension, and the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw.chromium.launch(); }
  catch (e) { t.skip("no playwright browser on this box, and the browser leg needs one (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  try { await body(browser); } finally { await browser.close(); }
}

/** The two surfaces that wear the bar's classes OUTSIDE a bar, as their modules build them: the file browser's bar
 *  (file-browse.ts: #romp-filebrowse, the backdrop > .filebrowse, the card > fb-bar > fb-crumbs + fileview-acts > [Hidden, close];
 *  the id and the class are two elements since the 2026-09-04 redress) under a deep crumb trail, in each document's sheets; and, in the pane document, the Files pane's Recent row (files.ts: fs-row > fileview-name + fileview-sess). */
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

const TALL_SVG = (w: number) => `data:image/svg+xml,${encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="200"><rect width="${w}" height="200" fill="#369"/></svg>`)}`;   // the README's pictures (the static leg's SVG above is 120px tall)
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
const README = `<img src="${TALL_SVG(1600)}" width="1600" height="200">\n\n# Report\n\nProse ${"lorem ipsum ".repeat(60)}\n\n![plot](${TALL_SVG(1600)})\n\n<div align="center"><img src="${TALL_SVG(1600)}" width="1600" height="200"></div>\n\n\`\`\`\nconst x = 1;\nconst y = 2;\n\`\`\`\n\n\`\`\`\n${"const z = 1; ".repeat(20)}\n\`\`\`\n\n| run | p95 |\n| --- | --- |\n| a | 120 |\n`;
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

// ── the stand-in's projection (ui/test-dom-shim.ts): a node inspects as its primitives, never as the tree ─────────────
test("a stand-in node enumerates its primitives alone, so a failing assertion's dump shows neither parentNode nor childNodes", () => {
  const root = new El("div"); root.className = "row";
  const child = root.appendChild(new El("span")); child.textContent = "alpha"; const tail = root.appendChild(new El("span")); tail.textContent = "beta";
  for (const n of [root, child, tail]) {
    for (const k of Object.keys(n)) assert.ok(staysEnumerable((n as any)[k]), k + " is enumerable and holds a " + typeof (n as any)[k]);
    const dump = inspect(n, { compact: false, customInspect: false, depth: 1000, maxArrayLength: Infinity, showHidden: false, showProxy: false, sorted: true, getters: true });
    assert.ok(!dump.includes("parentNode") && !dump.includes("childNodes"), "the dump holds no edge: " + dump);
  }
  assert.ok(child.parentNode === root && root.childNodes[0] === child && root.textContent === "alphabeta", "the tree is reachable as before");
  // the file's own Ev hides target and currentTarget the same way (hideEdges(this) at the end of its constructor)
  assertHiddenEvent(new Ev("click"), root, child);
});

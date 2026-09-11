// The focus follow-on's review (2026-09-08; plans/file-review.md, "The focus follow-on (2026-09-08)" under the margin-layout
// note), over the review stand-in file-comments-focus.test.ts drives — copied here with ONE change: focus() lands only on an
// element that is rendered (no hidden ancestor), as the browsers have it, which is what let the second finding through the
// stand-in. Three findings, each pinned: a focus written in the LIST layout (a mark or a head clicked there, where no pass
// runs) is spent by the list's own pass and never anchors the margin layout when the columns come back (a resize is not a
// click: nothing would center the card, and the cards above it moved from their marks — a tall card up past its mark, and
// the cards the chain cannot fit above the focused card below it, where the reach rule lays them (card-layout-reach.test.ts;
// as first built, before that rule, past the track's start, where no scroll reaches a card)); the keyboard stays on Show
// more / Show less across the render its Enter causes and across any re-render, though the row is rendered hidden until the
// pass shows it (render refocuses once more after the pass), and goes to the card's head, never the body, where the row
// stays hidden (the list layout); and a folded run of turns shows its END — the newest turn, the session's latest answer —
// scrolled to its last row, the sheets' fade at its first lines, instead of the oldest turns with the newest cut. A
// re-render here is the viewer's repaint (a reload, a mode switch), which runs the render a status does: a status reply
// after the open answers no ask the panel has posted, so it is dropped and renders nothing. Synthetic fixtures only: the
// notes-api world, placeholder ids.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inspect } from "node:util";
import * as fs from "node:fs";
import * as path from "node:path";
import type { FileViewActionCtx, TrackedEdit } from "./file-view";
import type { Status, StoreComment, Hunk } from "./file-comments-model";
import { layoutCards } from "./card-layout";
import { assertHiddenEvent, hideEdges, staysEnumerable } from "../test-dom-shim";

const web = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const SRC = web("file-comments.ts");

// ── a DOM stand-in: ancestry, attributes, events with capture and bubbling, a small selector engine ──
class Ev {
  target: El | Txt | null = null;
  currentTarget: El | null = null;
  defaultPrevented = false;
  stopped = false;
  key: string; ctrlKey: boolean; metaKey: boolean;   // the save is Ctrl+Enter or Cmd+Enter since the composer follow-on (composerKeyAction)
  constructor(public type: string, init: { key?: string; ctrlKey?: boolean; metaKey?: boolean } = {}) { this.key = init.key || ""; this.ctrlKey = !!init.ctrlKey; this.metaKey = !!init.metaKey; hideEdges(this); }
  preventDefault(): void { this.defaultPrevented = true; }
  stopPropagation(): void { this.stopped = true; }
}
type Listener = (ev: Ev) => void;
type Reg = { type: string; cb: Listener; capture: boolean };
const kebab = (k: string) => k.replace(/[A-Z]/g, (c) => "-" + c.toLowerCase());
class Txt {
  nodeType = 3;
  parentNode!: El | null;
  constructor(public data: string) {
    Object.defineProperty(this, "parentNode", { value: null, writable: true, enumerable: false, configurable: true });
    hideEdges(this);
  }
  get textContent(): string { return this.data; }
  get length(): number { return this.data.length; }
  get parentElement(): El | null { return this.parentNode; }
  splitText(off: number): Txt {
    const tail = new Txt(this.data.slice(off));
    this.data = this.data.slice(0, off);
    const p = this.parentNode;
    if (p) { const i = p.childNodes.indexOf(this); p.childNodes.splice(i + 1, 0, tail); tail.parentNode = p; }
    return tail;
  }
}
type Compound = { tag: string | null; classes: string[]; attrs: Array<[string, string | null]> };
// an attribute value may hold a quote or a backslash escaped with a backslash, as CSS.escape (or the panel's own
// fallback) writes it: `[data-id="x\"]"]` names the id `x"]`
const ATTR = /\[([\w-]+)(?:="((?:[^"\\]|\\.)*)")?\]/g;
const unescapeCss = (v: string): string => v.replace(/\\(.)/g, "$1");
function parseSel(sel: string): Compound[][] {
  return sel.split(",").map((g) => g.trim()).filter(Boolean).map((g) => g.split(/\s+/).map((s) => {
    const m = /^([a-zA-Z][\w-]*)?((?:\.[\w-]+)*)((?:\[[\w-]+(?:="(?:[^"\\]|\\.)*")?\])*)$/.exec(s);
    if (!m) throw new Error("stand-in: unsupported selector " + s);
    const classes = (m[2].match(/\.[\w-]+/g) || []).map((c) => c.slice(1));
    const attrs: Array<[string, string | null]> = [];
    for (const a of m[3].matchAll(ATTR)) attrs.push([a[1], a[2] === undefined ? null : unescapeCss(a[2])]);
    return { tag: m[1] ? m[1].toUpperCase() : null, classes, attrs };
  }));
}
type Rect = { left: number; top: number; right: number; bottom: number; width: number; height: number };
const R = (left: number, top: number, width: number, height: number): Rect => ({ left, top, width, height, right: left + width, bottom: top + height });
const ZERO = R(0, 0, 0, 0);
/** An element's inline style as the layout writes it: plain properties, and the custom property through setProperty. */
class Style {
  [k: string]: unknown;
  setProperty(k: string, v: string): void { this[k] = v; }
  removeProperty(k: string): void { delete this[k]; }
  getPropertyValue(k: string): string { return typeof this[k] === "string" ? (this[k] as string) : ""; }
}
class El {
  nodeType = 1;
  tagName: string;
  parentNode!: El | null;
  childNodes!: Array<El | Txt>;
  attrs = new Map<string, string>();
  listeners: Reg[] = [];
  hidden = false; disabled = false; readOnly = false; title = ""; type = ""; value = ""; checked = false; placeholder = "";
  innerHTML = "";
  style = new Style();
  /** a picture's natural size and load state, a canvas's bitmap size (0×0: not drawn) */
  naturalWidth = 0; naturalHeight = 0; complete: boolean | undefined = undefined; width = 0; height = 0;
  /** the client rect a test gives the element outright (a picture, a page shell); the measurement table otherwise */
  rect: Rect | null = null;
  private st = 0;
  // the edges are created hidden and hideEdges hides the rest: a node inspects as its own projection (ui/test-dom-shim.ts)
  constructor(tag: string) {
    this.tagName = tag.toUpperCase();
    Object.defineProperty(this, "parentNode", { value: null, writable: true, enumerable: false, configurable: true });
    Object.defineProperty(this, "childNodes", { value: [], writable: true, enumerable: false, configurable: true });
    hideEdges(this);
  }
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
  /** As the browser has it: a tabindex attribute, else 0 for a button or input, else -1 (not focusable). */
  get tabIndex(): number { return this.attrs.has("tabindex") ? Number(this.attrs.get("tabindex")) : (this.tagName === "BUTTON" || this.tagName === "INPUT" ? 0 : -1); }
  set tabIndex(v: number) { this.attrs.set("tabindex", String(v)); }
  dataset: Record<string, string> = new Proxy({} as Record<string, string>, {
    get: (_, k) => this.attrs.get("data-" + kebab(String(k))) as string,
    set: (_, k, v) => { this.attrs.set("data-" + kebab(String(k)), String(v)); return true; },
    has: (_, k) => this.attrs.has("data-" + kebab(String(k))),
    deleteProperty: (_, k) => { this.attrs.delete("data-" + kebab(String(k))); return true; },
  });
  get textContent(): string { return this.childNodes.map((c) => c.textContent).join(""); }
  set textContent(v: string) { for (const c of this.childNodes.slice()) this.detach(c); if (v !== "") this.appendChild(new Txt(v)); }
  /** A node leaves its parent; if it held the focus (itself or a descendant), the focus fixup rule moves it to the body. */
  private detach(n: El | Txt): void {
    const p = n.parentNode;
    if (p) { const i = p.childNodes.indexOf(n); if (i >= 0) p.childNodes.splice(i, 1); n.parentNode = null; }
    if (n instanceof El && doc.activeElement && n.contains(doc.activeElement)) doc.activeElement = doc.body;
  }
  appendChild<T extends El | Txt>(n: T): T { if (n.parentNode) n.parentNode.detach(n); this.childNodes.push(n); n.parentNode = this; return n; }
  insertBefore<T extends El | Txt>(n: T, ref: El | Txt | null): T {
    if (!ref) return this.appendChild(n);
    if (n.parentNode) n.parentNode.detach(n);
    const i = this.childNodes.indexOf(ref);
    this.childNodes.splice(i < 0 ? this.childNodes.length : i, 0, n); n.parentNode = this; return n;
  }
  removeChild<T extends El | Txt>(n: T): T { this.detach(n); return n; }
  replaceChildren(...c: Array<El | Txt>): void { for (const x of this.childNodes.slice()) this.detach(x); for (const x of c) this.appendChild(x); }
  remove(): void { if (this.parentNode) this.parentNode.detach(this); }
  normalize(): void {
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
    return (!c.tag || c.tag === this.tagName) && c.classes.every((k) => this.classes.includes(k))
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
  addEventListener(type: string, cb: Listener, opts?: boolean | { capture?: boolean }): void {
    this.listeners.push({ type, cb, capture: typeof opts === "boolean" ? opts : !!(opts && opts.capture) });
  }
  removeEventListener(type: string, cb: Listener, opts?: boolean | { capture?: boolean }): void {
    const cap = typeof opts === "boolean" ? opts : !!(opts && opts.capture);
    this.listeners = this.listeners.filter((l) => !(l.type === type && l.cb === cb && l.capture === cap));
  }
  dispatchEvent(ev: Ev): boolean { return dispatch(this, ev); }
  click(): void { this.dispatchEvent(new Ev("click")); }
  /** Focus lands only on a focusable, enabled, RENDERED element: a div with no tabindex ignores focus(), as the browser does,
   *  and so does a button in a hidden row — an element that is not being rendered (`display: none`) takes no focus, and
   *  focus() on it is a no-op. The focus stand-in ignored the row, which is how the keyboard's drop to the body went unseen. */
  rendered(): boolean { for (let x: El | null = this; x; x = x.parentNode) if (x.hidden) return false; return true; }
  focus(): void { if (this.tabIndex >= 0 && !this.disabled && this.rendered()) doc.activeElement = this; }
  blur(): void { if (doc.activeElement === this) doc.activeElement = doc.body; }
  scrollIntoView(): void { scrolledInto.push(this); }
  getBoundingClientRect(): Rect { return this.rect || (cur ? cur.measure(this) : ZERO); }
  get offsetWidth(): number { return 0; }
  /** The scroll position, clamped to the scroller's range as the browser clamps it: a write past the end lands at the
   *  end (and changes nothing when the scroller is already there), and a range that shrinks pulls the position back. */
  get scrollHeight(): number { return cur ? cur.scrollHeightOf(this) : 0; }
  get clientHeight(): number { return cur ? cur.clientHeightOf(this) : 0; }
  get scrollTop(): number { return Math.min(this.st, Math.max(0, this.scrollHeight - this.clientHeight)); }
  set scrollTop(v: number) { this.st = Math.max(0, Math.min(v, Math.max(0, this.scrollHeight - this.clientHeight))); }
  getContext(): { drawImage(): void } | null { return this.tagName === "CANVAS" ? { drawImage: () => { /* inert */ } } : null; }
  setPointerCapture(): void { /* inert */ }
  releasePointerCapture(): void { /* inert */ }
}
const scrolledInto: El[] = [];
const doc = {
  listeners: [] as Reg[],
  body: null as unknown as El,
  hidden: false,
  activeElement: null as El | null,
  createElement: (tag: string) => new El(tag),
  createTextNode: (s: string) => new Txt(s),
  getElementById: () => null,
  addEventListener(type: string, cb: Listener, opts?: boolean | { capture?: boolean }): void {
    doc.listeners.push({ type, cb, capture: typeof opts === "boolean" ? opts : !!(opts && opts.capture) });
  },
  removeEventListener(type: string, cb: Listener, opts?: boolean | { capture?: boolean }): void {
    const cap = typeof opts === "boolean" ? opts : !!(opts && opts.capture);
    doc.listeners = doc.listeners.filter((l) => !(l.type === type && l.cb === cb && l.capture === cap));
  },
  contains: (n: El | Txt | null) => doc.body.contains(n),
};
doc.body = new El("body");
doc.activeElement = doc.body;
function dispatch(target: El | Txt, ev: Ev): boolean {
  ev.target = target;
  const chain: El[] = [];
  for (let n: El | null = target instanceof El ? target : target.parentNode; n; n = n.parentNode) chain.push(n);
  const run = (ls: Reg[], capture: boolean, node: El | null): boolean => {
    for (const l of ls.slice()) {
      if (l.type !== ev.type || l.capture !== capture) continue;
      ev.currentTarget = node; l.cb.call(node, ev);
      if (ev.stopped) return true;
    }
    return false;
  };
  if (run(doc.listeners, true, null)) return !ev.defaultPrevented;
  for (let i = chain.length - 1; i >= 0; i--) if (run(chain[i].listeners, true, chain[i])) return !ev.defaultPrevented;
  if (ev.type === "load") { run(target instanceof El ? target.listeners : [], false, target as El); return true; }   // a load does not bubble: the target's own listeners alone
  for (const n of chain) if (run(n.listeners, false, n)) return !ev.defaultPrevented;
  run(doc.listeners, false, null);
  return !ev.defaultPrevented;
}
const win: any = new EventTarget();
win.parent = win; win.innerWidth = 1200; win.innerHeight = 800; win.devicePixelRatio = 1;
win.getSelection = () => null;
win.confirm = () => true;
(globalThis as any).window = win;
(globalThis as any).document = doc;

// The stand-in's nodes inspect as their own projection: hideEdges (ui/test-dom-shim.ts) makes every own property that
// holds an object, and every accessor, non-enumerable, so a failing assertion's dump of a node is a few lines and not
// the whole tree (a dump that walked parentNode up to the body grew to tens of GB before the box killed it, 2026-09-09).
test("stand-in: a node enumerates and inspects as its own projection, never the tree", () => {
  const root = doc.createElement("div");
  const kid = root.appendChild(doc.createElement("span"));
  kid.className = "fc-x"; kid.dataset.id = "k1"; kid.addEventListener("click", () => { /* inert */ });
  const leaf = kid.appendChild(doc.createTextNode("leaf"));
  for (const n of [root, kid, leaf]) {
    const own = n as unknown as Record<string, unknown>;
    assert.ok(Object.keys(own).every((k) => staysEnumerable(own[k])), "only primitives enumerate on " + n.constructor.name + ": " + Object.keys(own).join(", "));
    const dump = inspect(n, { compact: false, customInspect: false, depth: 1000, maxArrayLength: Infinity, showHidden: false, showProxy: false, sorted: true, getters: true });
    assert.ok(!dump.includes("parentNode") && !dump.includes("childNodes"), "the dump is the node's own projection:\n" + dump);
  }
  // the file's own Ev hides target and currentTarget the same way (hideEdges(this) at the end of its constructor)
  assertHiddenEvent(new Ev("click"), root, kid);
});
(globalThis as any).fetch = async () => ({ status: 404, headers: { get: () => null }, json: async () => [] });
// the layout's environment: the sheet's verdict on the fold, the frame queue, the observers
let narrow = false;
(globalThis as any).getComputedStyle = (el: El) => ({ flexDirection: el.classList.contains("fileview-main") && narrow ? "column" : "row" });
const frames: Array<() => void> = [];
(globalThis as any).requestAnimationFrame = (cb: () => void): number => { frames.push(cb); return frames.length; };
(globalThis as any).cancelAnimationFrame = (): void => { /* inert */ };
const flush = (): void => { for (const f of frames.splice(0)) f(); };
class RO {
  static all: RO[] = [];
  targets = new Set<El>();
  constructor(public cb: () => void) { RO.all.push(this); }
  observe(t: El): void { this.targets.add(t); }
  unobserve(t: El): void { this.targets.delete(t); }
  disconnect(): void { this.targets.clear(); }
}
(globalThis as any).ResizeObserver = RO;
/** Every observer holding `t` fires, then the frame runs: what a resize of that box does. */
const resized = (t: El): void => { for (const ro of RO.all) if (ro.targets.has(t)) ro.cb(); flush(); };
const resize = (): void => { for (const ro of RO.all) if (ro.targets.size) ro.cb(); };
const watched = (): Set<El> => { const s = new Set<El>(); for (const ro of RO.all) for (const t of ro.targets) s.add(t); return s; };
class IO {
  static all: IO[] = [];
  targets = new Set<El>();
  constructor(public cb: (entries: unknown[]) => void, public opts: unknown) { IO.all.push(this); }
  observe(t: El): void { this.targets.add(t); }
  unobserve(t: El): void { this.targets.delete(t); }
  disconnect(): void { this.targets.clear(); }
}
(globalThis as any).IntersectionObserver = IO;
const realSetInterval = globalThis.setInterval;
(globalThis as any).setInterval = (fn: () => void, ms: number) => { const t = realSetInterval(fn, ms); (t as any).unref?.(); return t; };
const tick = () => new Promise<void>((r) => setImmediate(r));

// ── fixtures: the notes-api world ──────────────────────────────────────────────────────────────────
const SID = "11111111-2222-3333-4444-555555555555";
const ABS = "/repo/notes-api/docs/report.md";
const ROOT = "/repo/notes-api";
const T0 = 1757145600000;
const QUOTE = "shipping the cache in v1.2";
// one logical line per row of the Raw view, each ROW px tall in the measurement table. Row 3 is a long paragraph the
// session inserted whole (the change whose card is TALL open: its text is a long part, folded in the margin layout); row
// 5 holds the passage comment under it; blank rows between the later lines make each its own paragraph
const LONG = "The api session rewrote the findings as one long paragraph about the cache, the latency budget, the plan for the next release and the reasons the team settled on it, going on for several sentences more than the one line it replaced, so that its card shows far more text than fits beside the passage.";
const LINES = ["# Report", "", "## Findings", LONG, "", "We recommend " + QUOTE + ".", "", "More text here."];
for (let i = 8; i < 33; i++) LINES.push(i % 2 ? "Line " + i + " of the report." : "");
LINES.push("The closing line of the report.");                    // row 33
const DOC = LINES.join("\n") + "\n";
const ROWS = LINES.length;                                       // 34
const passage: StoreComment = {   // row 5
  id: T0 + "-118", author: "you", ts: T0, body: "Which cache? Say which.",
  anchor: { quote: QUOTE, prefix: "We recommend ", suffix: "." }, replies: [], resolved: false,
};
const findings: StoreComment = {   // row 2, the heading above the change
  id: (T0 - 60000) + "-40", author: "you", ts: T0 - 60000, body: "Findings before methods?",
  anchor: { quote: "Findings", prefix: "## ", suffix: "\n" + LONG.slice(0, 20) }, replies: [], resolved: false,
};
const whole: StoreComment = { id: (T0 - 120000) + "-0", author: "you", ts: T0 - 120000, body: "Add a summary at the top.", replies: [], resolved: false };
const closing: StoreComment = {   // row 33, the last line
  id: (T0 + 5000) + "-9", author: "you", ts: T0 + 5000, body: "End on the recommendation, not on this.",
  anchor: { quote: "The closing line of the report", prefix: "", suffix: "." }, replies: [], resolved: false,
};
// row 7 ("More text here."): a comment with a run of six turns under it. The run is a long part (its text is well past
// LONG_PART), folded in the margin layout; the comment's own body is short and fits. Only the turns test puts it in the store
const TURN = (i: number): string => "Turn " + i + " of the run: the api session answers about the cache, the latency budget and what it will change next.";
const talked: StoreComment = {
  id: (T0 + 9000) + "-7", author: "you", ts: T0 + 9000, body: "Which cache is this about?",
  anchor: { quote: "More text here", prefix: "", suffix: "." }, resolved: false,
  replies: Array.from({ length: 6 }, (_, i) => ({ author: "api", ts: T0 + 10000 + i * 1000, body: TURN(i + 1) })),
};
const LONG_AT = DOC.indexOf(LONG);
const hunk: Hunk = { id: "h1", author: "api", ts: T0 - 30000, kind: "ins", curFrom: LONG_AT, curTo: LONG_AT + LONG.length, baseFrom: LONG_AT, baseTo: LONG_AT, oldText: "", newText: LONG, anchor: null };   // row 3
const CHG = "chg:h1";
function status(over: Partial<Status> = {}): Status {
  return {
    verb: "status", root: ROOT, storePath: ROOT + "/.trackchanges/docs%2Freport.md.json", trackedBy: { kind: "file", entry: "docs/report.md" }, agentTooling: "present",
    fileMtimeNs: "1757145600000000001", storeMtimeNs: "1757145600000000002", configMtimeNs: "1757145600000000003",
    store: { v: 3, path: "docs/report.md", suggestions: [], comments: [whole, findings, passage, closing] },
    hunks: [hunk], log: [],
    unsent: { comments: [passage.id], replies: [], accepted: 0, rejected: 0, watermark: null },
    ...over,
  };
}

// ── the viewer stand-in: the body row, the seam as closures, a measurement table ───────────────────
// Geometry: the body's box is at viewport y=100, BODY_VIEW tall; the header stands OFFSET tall above the track and the
// footer FOOTER tall below it, so the track's box is TRACK tall; row i's text sits at 100 + ROW·i − scrollTop; a card is
// CARD tall closed and OPEN tall open — except the change card, whose long part makes it TALL open and folded (eight lines
// of it) and WHOLE once Show more is pressed. A long part (LONG_PART: more than 200 characters) measures PART_ALL of
// content in a box of PART_CAP until its card wears fc-more; a short part fits its box.
const ROW = 60, OFFSET = 60, FOOTER = 40, CARD = 40, OPEN = 120, TALL = 200, WHOLE = 400, BODY_VIEW = 260, TRACK = BODY_VIEW - OFFSET - FOOTER;   // TRACK 160
const PART_ALL = 400, PART_CAP = 100, LONG_PART = 200;
type World = {
  ctx: FileViewActionCtx; posted: any[]; main: El; body: El; code: El;
  hooks: { rendered: Array<() => void>; close: Array<() => void> };
  editing: boolean; viewMtime: string;
  content: number;
  measure(el: El): Rect; scrollHeightOf(el: El): number; clientHeightOf(el: El): number;
  repaint(): void; close(): void;
  aside(): El; track(): El; list(): El; card(key: string): El | null; top(key: string): number | null;
};
let cur: World | null = null;
function rows(code: El, src: string): void {
  const lines = src.split("\n");
  if (lines.length && lines[lines.length - 1] === "") lines.pop();
  code.replaceChildren(...lines.map((ln) => {
    const cl = new El("span"); cl.className = "fv-cl";
    const ct = new El("span"); ct.className = "fv-ct";
    if (ln) ct.appendChild(new Txt(ln));
    cl.appendChild(ct);
    return cl;
  }));
}
const isLongPart = (el: El): boolean => el.classList.contains("fc-clip") && el.textContent.length > LONG_PART;
const cardOf = (el: El): El | null => el.closest(".fc-card");
function textWorld(): World {
  const body = new El("div"); body.className = "fileview-body";
  const wrap = new El("div"); wrap.className = "fileview-code";
  const pre = new El("pre"); pre.className = "fileview-pre fileview-wrap";
  const code = new El("code"); code.className = "hljs";
  pre.appendChild(code); wrap.appendChild(pre); body.appendChild(wrap);
  const main = new El("div"); main.className = "fileview-main";
  main.appendChild(body);
  doc.body.replaceChildren(main);
  const w = {
    posted: [] as any[], main, body, code, hooks: { rendered: [] as Array<() => void>, close: [] as Array<() => void> }, editing: false,
    viewMtime: "1757145600000000001", content: ROW * ROWS,
  } as World;
  rows(code, DOC);
  const pad = (): number => parseFloat((body.style.paddingBottom as string) || "0") || 0;
  w.scrollHeightOf = (el) => {
    if (el === body) return Math.max(w.content + pad(), BODY_VIEW);
    if (el.classList.contains("fc-sec-cards")) { const l = el.childNodes.find((n) => n instanceof El) as El | undefined; return Math.max(l ? parseFloat((l.style.height as string) || "0") || 0 : 0, TRACK); }
    if (el.classList.contains("fc-clip")) return isLongPart(el) ? PART_ALL : 20;
    return 0;
  };
  w.clientHeightOf = (el) => {
    if (el === body) return BODY_VIEW;
    if (el.classList.contains("fc-sec-cards")) return TRACK;
    if (el.classList.contains("fc-clip")) { const c = cardOf(el); return isLongPart(el) && !(c && c.classList.contains("fc-more")) ? PART_CAP : el.scrollHeight; }
    return 0;
  };
  w.measure = (el: El): Rect => {
    if (el === body) return R(0, 100, 400, BODY_VIEW);
    if (el.classList.contains("fc-sec-cards")) return R(400, 100 + OFFSET, 340, TRACK);
    if (el.classList.contains("fc-card")) {
      const open = el.classList.contains("open");
      const h = !open ? CARD : el.dataset.id === CHG ? (el.classList.contains("fc-more") ? WHOLE : TALL) : OPEN;
      return R(412, 0, 316, h);
    }
    if (el.classList.contains("fc-hl") || el.classList.contains("fc-ins") || el.classList.contains("fc-del")) {
      const row = el.closest(".fv-cl");
      const i = row ? w.code.querySelectorAll(".fv-cl").indexOf(row) : -1;
      return i < 0 ? ZERO : R(20, 100 + ROW * i - body.scrollTop, 50, 20);
    }
    if (el.parentNode && el.parentNode.classList.contains("fc-cards")) return R(412, 0, 316, 20);   // a loader, a row, a fold button
    return ZERO;
  };
  w.aside = () => main.querySelector(".fileview-aside")!;
  w.track = () => w.aside().querySelector(".fc-sec-cards")!;
  w.list = () => w.track().querySelector(".fc-cards")!;
  w.card = (key) => w.aside().querySelectorAll(".fc-card").find((c) => c.dataset.id === key) || null;
  w.top = (key) => { const c = w.card(key); const t = c ? c.style.top : undefined; return typeof t === "string" ? parseFloat(t) : null; };
  w.repaint = () => { for (const cb of w.hooks.rendered) cb(); };
  w.close = () => { for (const cb of w.hooks.close.splice(0)) cb(); if (cur === w) cur = null; };
  const noop = () => { /* inert */ };
  w.ctx = {
    path: ABS, sid: SID, todoId: null,
    body: () => w.body as unknown as HTMLElement, mode: () => "raw", text: () => DOC, mtimeNs: () => w.viewMtime, media: () => null, mediaElement: () => null, renderedImages: () => [], pdfPages: () => [],
    identity: () => ({ name: "api", color: null }),
    onRendered: (cb) => { w.hooks.rendered.push(cb); }, onSelection: noop, onSaved: noop, onClose: (cb) => { w.hooks.close.push(cb); },
    post: (m) => { w.posted.push(m); }, ensureEditingAllowed: async () => true, setEditBlocked: noop, editing: () => w.editing, setTrackedEdit: (_t: TrackedEdit | null) => { /* inert */ }, guardClose: noop,
    aside: (node) => { w.main.querySelector(".fileview-aside")?.remove(); if (node) { const n = node as unknown as El; n.classList.add("fileview-aside"); w.main.appendChild(n); } },
    setMode: noop, scrollToOffset: noop, reload: noop,
  };
  cur = w;
  return w;
}
type Posted = Record<string, any>;
type Ctx = { after(fn: () => void): void };
async function open(t: Ctx, w: World, s: Status = status(), from: { narrow?: boolean } = {}) {
  t.after(() => w.close());                            // a failing assertion must not leave the panel alive (its deadline timers would hold the process)
  narrow = !!from.narrow; frames.length = 0; RO.all.length = 0; IO.all.length = 0; scrolledInto.length = 0; doc.activeElement = doc.body;
  const fc = await import("./file-comments");
  const unit = fc.fileCommentsAction.mount(w.ctx) as unknown as El;
  const button = unit.childNodes[0] as El;
  const last = (): Posted => w.posted[w.posted.length - 1];
  const reply = async (data: Record<string, unknown>) => { win.dispatchEvent(new MessageEvent("message", { data })); await tick(); await tick(); };
  const ok = (o: Status = s) => reply({ type: "fileCommentsResult", reqId: last().reqId, ...o });
  await ok();                                          // the probe's status
  button.click();                                      // open: the aside mounts, the panel re-asks
  await ok();
  return { w, fc, button, ok, last };
}
// the desired top of a mark on row i in the track's content: the row's top in the body's content, less the header's height
const desired = (i: number): number => ROW * i - OFFSET;
const actIn = (root: El, a: string): El | null => root.querySelectorAll("[data-act]").find((x) => x.dataset.act === a) || null;
const headOf = (w: World, key: string): El => w.card(key)!.querySelector(".fc-card-head")!;
const markOf = (w: World, key: string): El => key.startsWith("chg:")
  ? w.body.querySelectorAll('[data-act="fcchange"]').find((m) => m.dataset.id === key.slice(4))!
  : w.body.querySelectorAll(".fc-hl").find((m) => m.dataset.id === key)!;
/** The viewport box a card's placed top gives it: the track's top, plus its top in the track's content, less the track's scroll. */
const cardBox = (w: World, key: string): { top: number; bottom: number } => { const top = 100 + OFFSET + w.top(key)! - w.track().scrollTop; return { top, bottom: top + w.card(key)!.getBoundingClientRect().height }; };
const TRACK_BOX = { top: 100 + OFFSET, bottom: 100 + OFFSET + TRACK };
const BODY_BOX = { top: 100, bottom: 100 + BODY_VIEW };
const inBox = (box: { top: number; bottom: number }, of: { top: number; bottom: number }): boolean => box.top >= of.top && box.bottom <= of.bottom;
/** The fold of a card: its Show more row, the button's label, and which parts the pass marked cut. */
const foldOf = (w: World, key: string): { row: El | null; hidden: boolean | null; label: string | null; clipped: string[]; parts: number; more: boolean } => {
  const card = w.card(key)!;
  const row = card.querySelector(".fc-clip-row");
  const b = row ? row.querySelector("button") : null;
  const parts = card.querySelectorAll(".fc-clip");
  return { row, hidden: row ? row.hidden : null, label: b ? b.textContent : null, clipped: parts.filter((p) => p.dataset.clipped === "1").map((p) => p.className), parts: parts.length, more: card.classList.contains("fc-more") };
};
// the layout the fixture gives: the change card open and folded is TALL (200) at row 3's height, over row 5's passage
const PUSHED = desired(3) + TALL + 8;                            // 328: where the push-down rule puts the passage's card under the open change card
const LIFTED = desired(5) - TALL - 8;                            // 32: where the change card goes when the passage is the focus
// where a focus on the passage sends the cards the chain cannot fit above it, the heading's card and then the loose card:
// below the focused card, from its end (card-layout.ts: no card past the track's start; card-layout-reach.test.ts has the rule)
const BELOW_FOCUS = desired(5) + OPEN + 8;                        // 368: the heading's card, wearing the leader up to its mark
const BELOW_FOCUS_LOOSE = BELOW_FOCUS + CARD + 8;                 // 416: the loose card after it

/** The sheets' fade for a cut run of turns: at its FIRST lines, against the last-lines fade of every other cut part. */
const RUN_FADE = ".fc-margin .fc-card:not(.fc-more) .fc-replies.fc-clip[data-clipped] { -webkit-mask-image: linear-gradient(to top, black 65%, transparent); mask-image: linear-gradient(to top, black 65%, transparent); }";

// ── the list layout has no focus ──────────────────────────────────────────────────────────────────

test("a mark clicked in the list layout does not anchor the margin layout when the columns come back: a resize is not a click, so the cards lie by the push-down rule, the loose card at the track's start", async (t) => {
  const { w } = await open(t, textWorld());
  narrow = true; resize(); flush();
  assert.ok(!w.aside().classList.contains("fc-margin"), "the list layout");
  markOf(w, CHG).click(); await tick();                // the change card opens in the list...
  markOf(w, passage.id).click(); await tick();         // ...and the passage's: each click wrote a focus the list has no pass to spend
  assert.ok(w.card(CHG)!.classList.contains("open") && w.card(passage.id)!.classList.contains("open"));
  narrow = false; resize(); flush();                   // the columns come back: a resize, not a click
  assert.ok(w.aside().classList.contains("fc-margin"), "the margin layout");
  // what the messages below say a focus left on the passage would have done, held to the layout rule over this scene: the
  // change card up to LIFTED, the heading's card and the loose card below the focused card, no card past the start
  const leaked = Object.fromEntries(layoutCards([
    { key: whole.id, desired: null, height: CARD }, { key: findings.id, desired: desired(2), height: CARD }, { key: CHG, desired: desired(3), height: TALL },
    { key: passage.id, desired: desired(5), height: OPEN }, { key: closing.id, desired: desired(33), height: CARD },
  ], 8, passage.id).placed.map((p) => [p.key, p.top]));
  assert.deepEqual(leaked, { [CHG]: LIFTED, [passage.id]: desired(5), [findings.id]: BELOW_FOCUS, [whole.id]: BELOW_FOCUS_LOOSE, [closing.id]: desired(33) }, "the fixture: where a focus left on the passage would lay the cards");
  assert.ok(Object.values(leaked).every((top) => top >= 0), "the fixture: none of them past the start (the reach rule)");
  assert.equal(w.top(CHG), desired(3), "the change card is level with its mark (a focus left on the passage put it at " + LIFTED + ")");
  assert.equal(w.top(passage.id), PUSHED, "the passage's card under it: the push-down rule");
  assert.equal(w.card(passage.id)!.dataset.pushed, "1");
  assert.equal(w.top(whole.id), 8, "the loose card at the track's start (a focus left on the passage put it at " + BELOW_FOCUS_LOOSE + ", below the focused card)");
  assert.equal(w.top(findings.id), desired(2), "the heading's card level with its mark (a focus left on the passage put it at " + BELOW_FOCUS + ", below the focused card)");
  assert.equal(w.aside().querySelectorAll(".fc-card").filter((c) => c.dataset.pulled === "1").length, 0, "no card moved up past its mark");
  // a click IN the margin layout is the focus, as before
  markOf(w, passage.id).click(); await tick();
  assert.equal(w.top(CHG), LIFTED);
  w.close();
});

test("the same for a head click in the list layout, and for a panel that opened in the list layout: the first margin pass has no focus", async (t) => {
  const { w } = await open(t, textWorld(), status(), { narrow: true });
  assert.ok(!w.aside().classList.contains("fc-margin"), "opened in the list layout");
  headOf(w, CHG).click(); await tick();
  headOf(w, passage.id).click(); await tick();
  assert.ok(w.card(CHG)!.classList.contains("open") && w.card(passage.id)!.classList.contains("open"));
  narrow = false; resize(); flush();
  assert.ok(w.aside().classList.contains("fc-margin"));
  assert.equal(w.top(CHG), desired(3));
  assert.equal(w.top(passage.id), PUSHED);
  assert.equal(w.top(whole.id), 8);
  assert.equal(w.top(findings.id), desired(2));
  w.close();
});

// ── the keyboard on Show more ─────────────────────────────────────────────────────────────────────

test("the keyboard stays on Show more: Enter opens the part whole and the fresh Show less holds the focus; a re-render keeps it; Show less the same; in the list layout, where the row is hidden, the keyboard goes to the card's head, not the body, and the next render brings it back to the toggle once the columns show the row", async (t) => {
  const { w } = await open(t, textWorld());
  markOf(w, CHG).click(); await tick();
  const toggle = (): El => foldOf(w, CHG).row!.querySelector("button")!;
  const b = toggle();
  assert.equal(foldOf(w, CHG).hidden, false);
  b.focus();
  assert.equal(doc.activeElement, b, "the fixture: the shown toggle takes the keyboard");
  b.click(); await tick();                             // Enter on a focused button is a click
  assert.notEqual(toggle(), b, "the render rebuilt the row");
  assert.equal(toggle().textContent, "Show less");
  assert.equal(doc.activeElement, toggle(), "the keyboard is on the fresh toggle, not the body");
  // a re-render while the keyboard is on it (the viewer repainted)
  const fresh = toggle();
  w.repaint(); await tick();
  assert.notEqual(toggle(), fresh, "the fixture: the repaint rebuilt the row");
  assert.equal(toggle().textContent, "Show less");
  assert.equal(doc.activeElement, toggle(), "kept across a re-render");
  // Show less: the row is rendered hidden again until the pass finds the part cut
  toggle().click(); await tick();
  assert.equal(toggle().textContent, "Show more");
  assert.equal(foldOf(w, CHG).hidden, false);
  assert.equal(doc.activeElement, toggle(), "on the fresh Show more");
  w.repaint(); await tick();
  assert.equal(doc.activeElement, toggle(), "kept across a re-render, folded");
  // the fold to the list: no pass shows the row there, so the toggle cannot hold the keyboard; the card's head does
  narrow = true; resize(); flush();
  assert.ok(!w.aside().classList.contains("fc-margin"));
  assert.equal(foldOf(w, CHG).hidden, true);
  assert.equal(doc.activeElement, headOf(w, CHG), "the nearest place: the card's head, not the body");
  // the columns come back: the pass shows the row (no render), and the next render puts the keyboard back on the toggle it left
  narrow = false; resize(); flush();
  assert.equal(foldOf(w, CHG).hidden, false);
  assert.equal(doc.activeElement, headOf(w, CHG), "a resize renders nothing: the head keeps it");
  w.repaint(); await tick();
  assert.equal(doc.activeElement, toggle(), "the render brings the keyboard back to the toggle");
  w.close();
});

test("a card head keeps the keyboard across Enter and a re-render as it did: the second refocus is a no-op when the first landed", async (t) => {
  const { w } = await open(t, textWorld());
  headOf(w, passage.id).click(); await tick();
  headOf(w, passage.id).focus();
  assert.equal(doc.activeElement, headOf(w, passage.id));
  headOf(w, passage.id).click(); await tick();         // a fold
  assert.ok(!w.card(passage.id)!.classList.contains("open"));
  assert.equal(doc.activeElement, headOf(w, passage.id), "the fresh head holds it");
  const head = headOf(w, passage.id);
  w.repaint(); await tick();
  assert.notEqual(headOf(w, passage.id), head, "the fixture: the repaint rebuilt the card");
  assert.equal(doc.activeElement, headOf(w, passage.id));
  w.close();
});

// ── a folded run of turns shows its end ───────────────────────────────────────────────────────────

test("a folded run of turns shows its end: the box scrolled to its last row — the newest turn — and marked cut, which the sheets fade at its first lines; the comment's short body is untouched; Show more shows the run whole from its start; the list layout folds nothing", async (t) => {
  const s = status({ store: { v: 3, path: "docs/report.md", suggestions: [], comments: [whole, findings, passage, closing, talked] } });
  const { w } = await open(t, textWorld(), s);
  markOf(w, talked.id).click(); await tick();
  const card = w.card(talked.id)!;
  assert.ok(card.classList.contains("open"));
  const turns = card.querySelector(".fc-replies")!;
  assert.ok(turns.classList.contains("fc-clip"));
  assert.ok(turns.textContent.length > LONG_PART, "the fixture: the run is a long part");
  assert.equal(turns.querySelectorAll(".fc-reply").length, 6);
  assert.equal(turns.querySelectorAll(".fc-reply")[5].textContent.includes(TURN(6)), true, "the newest turn is the last row");
  assert.equal(turns.scrollHeight, PART_ALL); assert.equal(turns.clientHeight, PART_CAP);
  assert.equal(turns.dataset.clipped, "1", "the pass found the cap cut it");
  assert.equal(turns.scrollTop, PART_ALL - PART_CAP, "scrolled to its end: the last row is in the box (before: 0, the oldest turns)");
  for (const f of ["styles.css", "feed.css"]) {
    const css = web(f);
    assert.ok(css.includes(RUN_FADE), f + ": the cut run's fade at its first lines");
    assert.ok(css.indexOf(RUN_FADE) > css.indexOf(".fc-margin .fc-card:not(.fc-more) .fc-clip[data-clipped] {"), f + ": after the last-lines fade it overrides");
  }
  const body = card.querySelector(".fc-body.fc-clip")!;   // the comment's own body: short, not cut, at its start
  assert.equal(body.dataset.clipped, undefined); assert.equal(body.scrollTop, 0);
  let f = foldOf(w, talked.id);
  assert.equal(f.hidden, false); assert.equal(f.label, "Show more");
  assert.deepEqual(f.clipped, ["fc-replies fc-clip"]);
  // Show more: whole, from the start, not marked cut (so no fade)
  f.row!.querySelector("button")!.click(); await tick();
  assert.ok(w.card(talked.id)!.classList.contains("fc-more"));
  const shown = w.card(talked.id)!.querySelector(".fc-replies")!;
  assert.equal(shown.dataset.clipped, undefined);
  assert.equal(shown.scrollTop, 0);
  // Show less: folded to its end again
  foldOf(w, talked.id).row!.querySelector("button")!.click(); await tick();
  const again = w.card(talked.id)!.querySelector(".fc-replies")!;
  assert.equal(again.dataset.clipped, "1");
  assert.equal(again.scrollTop, PART_ALL - PART_CAP);
  // the scroll is the pass's, written every time it finds the run cut (a fresh render's box starts at 0)
  again.scrollTop = 0; resize(); flush();
  assert.equal(again.scrollTop, PART_ALL - PART_CAP, "the pass scrolled it to its end again");
  // the list layout: no pass, nothing cut, the run at its start
  narrow = true; resize(); flush();
  assert.ok(!w.aside().classList.contains("fc-margin"));
  const listed = w.card(talked.id)!.querySelector(".fc-replies")!;
  assert.equal(listed.dataset.clipped, undefined); assert.equal(listed.scrollTop, 0);
  w.close();
});

// ── at source ─────────────────────────────────────────────────────────────────────────────────────

test("at source: the list layout's pass clears the focus before it returns; render refocuses before the pass and once more after it; the pass keeps a run of turns at its end", () => {
  assert.match(SRC, /if \(!margin\) \{\n(?:\s*\/\/[^\n]*\n)*\s*this\.focusCard = null;\n\s*if \(flipped\) \{ this\.layoutOff\(\); if \(!fromRender\) this\.render\(\); \}\n\s*return;\n\s*\}/, "the list branch of placeCards");
  assert.match(SRC, /if \(keep\) this\.refocus\(keep, want, false\);\n\s*this\.afterRender\(\);[^\n]*\n(?:\s*\/\/[^\n]*\n)*\s*if \(keep\) this\.refocus\(keep, want, true\);/, "the refocus after the pass");
  assert.match(SRC, /const take = \(n: HTMLElement\): boolean => \{ n\.focus\(\{ preventScroll: true \}\); return document\.activeElement === n; \};/, "refocus reads whether the focus took");
  assert.match(SRC, /if \(part\.classList\.contains\("fc-replies"\)\) this\.keepEnd\(part, over\);/, "the run of turns");
  assert.match(SRC, /private keepEnd\(part: HTMLElement, cut: boolean\): void \{\n\s*if \(cut\) part\.scrollTop = part\.scrollHeight;\n\s*else if \(part\.scrollTop\) part\.scrollTop = 0;/, "scrolled to its end when cut, back to its start when not");
  assert.ok(!SRC.includes("mask-image"), "the fade is the sheets', not an inline style");
});

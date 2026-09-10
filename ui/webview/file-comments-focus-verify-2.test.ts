// The focus follow-on's verification review, second round (2026-09-09; plans/file-review.md, "The focus follow-on
// (2026-09-08)" under the margin-layout note), over the stand-in file-comments-focus-review.test.ts drives (focus() lands only
// on a rendered element, as the browsers have it). Three findings, each pinned by the behavior it changes or the gap it
// closes. A gesture on a LOOSE card the reach rule laid below the focused card — its head, its Show more, the save of a
// whole-file comment — leaves the layout where it was: the pass keeps the focus it laid the cards on last (laidOn), since a
// loose card has no mark to be laid level with and the rule takes a focus with no mark as none, so writing it unmade the
// layout: the clicked card jumped to the track's start out of the box with nothing scrolling after it, the card the person
// was reviewing fell under the tall card again, off its mark. The save leaves the scroll where it was too (decision 43,
// 2026-09-09: a save never moves the view; this round had it bring the card into the track's box), and the line at the
// panel's foot says which side of the box the card is on, its click bringing the card into the box where it stands
// (fcsavedgo: scrollCard, showLoose). The keyboard's memory of a control a render could not land on
// (Show less hidden by the fold to the list layout; a busy Accept or Reject) holds for as long as the control is in the list
// and the keyboard stays where the panel put it, however many renders pass meanwhile — a repaint, a status — so the render
// after the columns come back returns the keyboard to the toggle, and the refusal that keeps a card returns it to the
// button (before: the memory lasted one render). And the focus clears with the panel's close, driven: a reopen lays the
// cards by the push-down rule, not on the card clicked before the close. Synthetic fixtures only: the notes-api world,
// placeholder ids.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inspect } from "node:util";
import * as fs from "node:fs";
import * as path from "node:path";
import type { FileViewActionCtx, TrackedEdit } from "./file-view";
import type { Status, StoreComment, Hunk } from "./file-comments-model";
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
      const h = !open ? CARD : el.querySelectorAll(".fc-clip").some(isLongPart) ? (el.classList.contains("fc-more") ? WHOLE : TALL) : OPEN;   // any card with a long part (file-comments-focus.test.ts's rule): the loose card with the long body here
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
  const refuse = (code: string, error: string) => reply({ type: "fileCommentsFailed", reqId: last().reqId, verb: last().verb, code, error });   // a write refused: the card stays
  return { w, fc, button, ok, last, refuse };
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


// ── the save of a whole-file comment (file-comments-margin-fixes.test.ts's drive) ─────────────────
const NOTE = "Add a glossary at the end, please.";
const NS9 = "1757145600000000009";
const fileComment = (id: string, body: string = NOTE): StoreComment => ({ id, author: "you", ts: parseInt(id, 10), body, replies: [], resolved: false });   // ts from the id's stamp: the loose group sorts by it
/** Comment on this file, a note typed, the save chord: the `comment` request is out. */
async function saveFileComment(w: World, last: () => Posted): Promise<El> {
  actIn(w.aside(), "fcfile")!.click();
  const composer = w.aside().querySelector(".fc-composer")!;
  assert.equal(composer.hidden, false, "the composer is up");
  const input = composer.querySelector(".fc-input")!;
  input.value = NOTE;
  input.dispatchEvent(new Ev("keydown", { key: "Enter", ctrlKey: true }));
  await tick();
  assert.equal(last().verb, "comment", "the comment went out");
  assert.equal(last().args.anchor, undefined, "a whole-file comment: no anchor");
  return composer;
}
// a whole-file comment whose body is a long part (past LONG_PART): its card TALL open and folded, WHOLE after Show more
const LONG_BODY = "The report needs a summary at the top that says what was measured, on which release, what the cache bought in latency and what it cost in memory, and what the team decided to ship, so that a reader who stops after the first screen still leaves with the findings.";
const wholeLong: StoreComment = { ...whole, body: LONG_BODY };
const withWholeLong = (): Status => status({ store: { v: 3, path: "docs/report.md", suggestions: [], comments: [wholeLong, findings, passage, closing] } });
/** The cards the pass moved up past their marks (data-pulled), by key. */
const pulled = (w: World): string[] => w.aside().querySelectorAll(".fc-card").filter((c) => c.dataset.pulled === "1").map((c) => c.dataset.id);

// ── a gesture on a loose card below the focus moves nothing ──────────────────────────────────────

test("a head click on a loose card the reach rule laid below the focused card opens it where it stands: the focus stays on the card the person was reviewing, level with its mark, the tall card stays up out of its way, nothing scrolls, and the opened card is in the track's box; a fold by its head the same; a marked card's mark takes the focus after, as ever", async (t) => {
  const { w } = await open(t, textWorld());
  const body = w.body, track = w.track();
  markOf(w, CHG).click(); await tick();
  markOf(w, passage.id).click(); await tick();
  assert.equal(w.top(passage.id), desired(5), "the passage's card is the focus, level with its highlight");
  assert.equal(w.top(CHG), LIFTED, "the tall change card moved up out of its way");
  assert.equal(w.top(findings.id), BELOW_FOCUS, "the heading's card below the focused card");
  assert.equal(w.top(whole.id), BELOW_FOCUS_LOOSE, "the loose card after it: the reach rule");
  // the reader scrolls the loose card into the track's box, with room under it for the card to open
  const at = 400;
  assert.ok(at >= BELOW_FOCUS_LOOSE + OPEN + 8 - TRACK && at <= BELOW_FOCUS_LOOSE - 8, "the fixture: the scroll shows the loose card whole, closed and open");
  body.scrollTop = at; body.dispatchEvent(new Ev("scroll"));
  assert.equal(track.scrollTop, at, "the track with it");
  assert.ok(inBox(cardBox(w, whole.id), TRACK_BOX), "the fixture: the loose card is in the track's box: " + JSON.stringify(cardBox(w, whole.id)));
  // its head: the card opens where it stands
  headOf(w, whole.id).click(); await tick();
  assert.ok(w.card(whole.id)!.classList.contains("open"), "opened");
  assert.equal(w.card(whole.id)!.getBoundingClientRect().height, OPEN);
  assert.equal(w.top(whole.id), BELOW_FOCUS_LOOSE, "where it stood (before: 8, the track's start, out of the box)");
  assert.equal(w.top(passage.id), desired(5), "the focus is still the passage's card, level with its highlight (before: " + PUSHED + ", under the tall card again)");
  assert.equal(w.card(passage.id)!.dataset.pushed, undefined, "not pushed");
  assert.equal(w.top(CHG), LIFTED, "the tall card stays up (before: " + desired(3) + ", back over the highlight)");
  assert.equal(w.top(findings.id), BELOW_FOCUS, "the heading's card where it was");
  assert.equal(body.scrollTop, at, "nothing scrolled: a head click on a loose card moves nothing"); assert.equal(track.scrollTop, at);
  assert.ok(inBox(cardBox(w, whole.id), TRACK_BOX), "the opened card is in the track's box, head and all: " + JSON.stringify(cardBox(w, whole.id)));
  assert.deepEqual(pulled(w), [], "no card moved up past its mark");
  // a fold by its head: the same
  headOf(w, whole.id).click(); await tick();
  assert.ok(!w.card(whole.id)!.classList.contains("open"), "folded");
  assert.equal(w.top(whole.id), BELOW_FOCUS_LOOSE); assert.equal(w.top(passage.id), desired(5)); assert.equal(w.top(CHG), LIFTED);
  assert.equal(body.scrollTop, at); assert.equal(track.scrollTop, at);
  // a marked card's mark after: the focus moves to it as before, and the loose card goes back to the start with the group
  markOf(w, CHG).click(); await tick();
  assert.equal(w.top(CHG), desired(3), "the change card is the focus: level with its mark");
  assert.equal(w.top(passage.id), PUSHED, "the passage's card yields");
  assert.equal(w.top(whole.id), 8, "the loose card at the track's start: nothing above the focus needs its room");
  w.close();
});

test("with no focus, a head click on a loose card at the track's start moves nothing, as before", async (t) => {
  const { w } = await open(t, textWorld());
  const body = w.body;
  assert.equal(w.top(whole.id), 8);
  headOf(w, whole.id).click(); await tick();
  assert.ok(w.card(whole.id)!.classList.contains("open"));
  assert.equal(w.top(whole.id), 8, "at the start still");
  assert.equal(w.top(findings.id), 8 + OPEN + 8, "the heading's card pushed under the open loose card: the push-down rule");
  assert.equal(body.scrollTop, 0, "nothing scrolled");
  w.close();
});

test("Show more on a loose card laid below the focused card shows its text whole where it stands: the card wears fc-more and grows in place, the focus and the scroll stay (before: the card to the track's start with its Show less below the box, the reviewed card under the tall card); Show less folds it there", async (t) => {
  const { w } = await open(t, textWorld(), withWholeLong());
  const body = w.body, track = w.track();
  markOf(w, CHG).click(); await tick();
  markOf(w, passage.id).click(); await tick();
  assert.equal(w.top(passage.id), desired(5)); assert.equal(w.top(CHG), LIFTED);
  assert.equal(w.top(wholeLong.id), BELOW_FOCUS_LOOSE, "the loose card below the focused card");
  const at = 400;
  body.scrollTop = at; body.dispatchEvent(new Ev("scroll"));
  assert.ok(inBox(cardBox(w, wholeLong.id), TRACK_BOX), "the fixture: the loose card is in the track's box");
  // opened by its head: TALL, its long body cut at the cap, Show more at its foot; where it stood
  headOf(w, wholeLong.id).click(); await tick();
  let f = foldOf(w, wholeLong.id);
  assert.equal(w.card(wholeLong.id)!.getBoundingClientRect().height, TALL, "the fixture: the body is a long part, folded");
  assert.deepEqual(f.clipped, ["fc-body fc-clip"]); assert.equal(f.hidden, false); assert.equal(f.label, "Show more");
  assert.equal(w.top(wholeLong.id), BELOW_FOCUS_LOOSE, "where it stood");
  assert.equal(w.top(passage.id), desired(5), "the focus kept"); assert.equal(w.top(CHG), LIFTED);
  assert.equal(body.scrollTop, at, "nothing scrolled");
  assert.equal(cardBox(w, wholeLong.id).top, TRACK_BOX.top + BELOW_FOCUS_LOOSE - at, "its head where it was, in the box");
  // Show more: whole, in place
  f.row!.querySelector("button")!.click(); await tick();
  f = foldOf(w, wholeLong.id);
  assert.equal(f.more, true, "the card wears fc-more"); assert.equal(f.label, "Show less"); assert.deepEqual(f.clipped, []);
  assert.equal(w.card(wholeLong.id)!.getBoundingClientRect().height, WHOLE);
  assert.equal(w.top(wholeLong.id), BELOW_FOCUS_LOOSE, "where it stood (before: 8, the track's start)");
  assert.equal(w.top(passage.id), desired(5), "the focus is still the passage's card (before: " + PUSHED + ")");
  assert.equal(w.card(passage.id)!.dataset.pushed, undefined);
  assert.equal(w.top(CHG), LIFTED, "the tall card stays up (before: " + desired(3) + ")");
  assert.equal(body.scrollTop, at, "nothing scrolled: a loose card has no mark to center"); assert.equal(track.scrollTop, at);
  assert.equal(w.top(closing.id), desired(33), "the fixture: the whole card ends above the closing line's mark, which keeps its card level");
  // Show less: folded again, in place
  f.row!.querySelector("button")!.click(); await tick();
  f = foldOf(w, wholeLong.id);
  assert.equal(f.more, false); assert.equal(f.label, "Show more"); assert.deepEqual(f.clipped, ["fc-body fc-clip"]);
  assert.equal(w.card(wholeLong.id)!.getBoundingClientRect().height, TALL);
  assert.equal(w.top(wholeLong.id), BELOW_FOCUS_LOOSE); assert.equal(w.top(passage.id), desired(5)); assert.equal(w.top(CHG), LIFTED);
  assert.equal(body.scrollTop, at);
  w.close();
});

test("a whole-file comment saved while a card is the focus: the new card joins the loose group's end below the focused card, the focus and the tall card's lift are kept, and nothing scrolls (decision 43): the line at the foot says the card is below, and its click brings the card into the track's box where it stands, on both scrollers at once, and ends the line (before decision 43 the save itself made that scroll; before this round: the save wrote the loose card as the focus, the layout fell back to the push-down rule and the scroll went to the group at the track's start)", async (t) => {
  const { w, ok, last } = await open(t, textWorld());
  const body = w.body, track = w.track();
  markOf(w, CHG).click(); await tick();
  markOf(w, passage.id).click(); await tick();
  assert.equal(w.top(passage.id), desired(5)); assert.equal(w.top(CHG), LIFTED); assert.equal(w.top(whole.id), BELOW_FOCUS_LOOSE);
  const before = body.scrollTop;
  assert.equal(before, desired(5) + OPEN + 8 - TRACK, "the fixture: the highlight's click scrolled to show the focused card's end");
  assert.equal(actIn(w.aside(), "fcsavedgo"), null, "the fixture: no saved line before the save");
  const composer = await saveFileComment(w, last);
  const fresh = fileComment(T0 + 5000 + "-0");
  await ok(status({ verb: "comment", storeMtimeNs: NS9, store: { v: 3, path: "docs/report.md", suggestions: [], comments: [whole, findings, passage, closing, fresh] } }));
  assert.ok(w.card(fresh.id), "the new card is rendered");
  const freshTop = BELOW_FOCUS_LOOSE + CARD + 8;      // 464: the loose group's end, below the focused card, in the list's order
  assert.equal(w.top(fresh.id), freshTop, "loose, after the other loose card below the focused card (before: " + (8 + CARD + 8) + ", at the track's start)");
  assert.equal(w.top(passage.id), desired(5), "the focus kept: the passage's card level with its highlight (before: " + (8 + 2 * (CARD + 8) + TALL + 8) + ")");
  assert.equal(w.card(passage.id)!.dataset.pushed, undefined);
  assert.equal(w.top(CHG), LIFTED, "the tall card still up");
  assert.equal(w.top(whole.id), BELOW_FOCUS_LOOSE);
  assert.equal(w.top(findings.id), BELOW_FOCUS);
  // the card is below the track's box, and the save leaves it there: the scroll as it was, on both scrollers
  const want = freshTop + CARD + 8 - TRACK;           // 352: the least scroll that shows the card's end — what the line's click scrolls to
  assert.ok(want > before, "the fixture: the new card's end is past the box");
  assert.equal(body.scrollTop, before, "the body did not move: a save never scrolls (decision 43; before it: " + want + ", the least scroll that showed the card's end)");
  assert.equal(track.scrollTop, before, "nor the track");
  assert.ok(!inBox(cardBox(w, fresh.id), TRACK_BOX), "the fixture: the card stands out of the track's box, past its end: " + JSON.stringify(cardBox(w, fresh.id)));
  assert.deepEqual(scrolledInto, [], "no scrollIntoView in the margin layout");
  assert.equal(composer.hidden, true, "the composer closed");
  // the line at the panel's foot says where the card is, in the acknowledgment's position
  const line = actIn(w.aside(), "fcsavedgo");
  assert.ok(line, "the line is in the panel: a comment's save renders it itself (the composer's close re-renders the composer alone)");
  assert.equal(line!.textContent, "Saved · the card is below", "the side the card stands on: past the box's end");
  assert.ok(w.aside().querySelector(".fc-sec-send")!.contains(line!), "in the Send section, where the acknowledgment stands");
  // its click: the card into the track's box where it stands, on both scrollers at once, the layout untouched, and the line is over
  line!.click(); await tick();
  assert.equal(body.scrollTop, want, "the body: the least scroll that shows the card's end (showLoose)");
  assert.equal(track.scrollTop, want, "the track with it, at once");
  assert.ok(inBox(cardBox(w, fresh.id), TRACK_BOX), "the card is in the track's box: " + JSON.stringify(cardBox(w, fresh.id)));
  assert.equal(w.top(fresh.id), freshTop, "where it stood: a loose card is shown, not moved");
  assert.equal(w.top(passage.id), desired(5), "the focus is still the passage's card, level with its highlight: a loose card cannot take the pass's focus (laidOn)");
  assert.equal(w.top(CHG), LIFTED, "the tall card still up");
  assert.deepEqual(scrolledInto, [], "both scrollers written, no scrollIntoView");
  assert.equal(actIn(w.aside(), "fcsavedgo"), null, "the line is over");
  w.close();
});

// ── the focus clears with the panel's close ───────────────────────────────────────────────────────

test("the focus clears with the panel's close: a reopen lays the cards by the push-down rule, the cards open as they were, nothing moved up past its mark (a focus kept across the close anchored the first pass on the passage's card, the change card up at " + LIFTED + " and the loose card below the focus, with nothing centered)", async (t) => {
  const { w, button, ok } = await open(t, textWorld());
  markOf(w, CHG).click(); await tick();
  markOf(w, passage.id).click(); await tick();
  assert.equal(w.top(CHG), LIFTED, "the passage's card is the focus");
  const aside = w.aside();
  button.click();                                      // close: the layout ends with the panel (layoutOff)
  assert.ok(!aside.classList.contains("fc-margin"), "the margin layout ended");
  assert.equal(w.main.querySelector(".fileview-aside"), null, "the aside is gone");
  button.click(); await ok();                          // reopen: the panel re-asks, and its first pass lays the fresh cards
  assert.ok(w.aside().classList.contains("fc-margin"), "the margin layout is back");
  assert.ok(w.card(CHG)!.classList.contains("open") && w.card(passage.id)!.classList.contains("open"), "the fixture: the cards are open as they were (the expand state outlives the close)");
  assert.equal(w.top(CHG), desired(3), "no focus: the change card is level with its mark (a stale focus: " + LIFTED + ")");
  assert.equal(w.top(passage.id), PUSHED, "the passage's card under it by the push-down rule (a stale focus: " + desired(5) + ")");
  assert.equal(w.card(passage.id)!.dataset.pushed, "1");
  assert.equal(w.top(whole.id), 8, "the loose card at the track's start (a stale focus: " + BELOW_FOCUS_LOOSE + ")");
  assert.equal(w.top(findings.id), desired(2), "the heading's card level with its mark (a stale focus: " + BELOW_FOCUS + ")");
  assert.deepEqual(pulled(w), [], "no card moved up past its mark");
  // a click in the reopened panel is the focus, as before
  markOf(w, passage.id).click(); await tick();
  assert.equal(w.top(CHG), LIFTED);
  w.close();
});

// ── the keyboard's memory holds across the renders that cannot land it ────────────────────────────

test("the toggle is remembered for as long as the columns stay narrow: a repaint and a status while the list layout holds leave the keyboard on the card's head, and the render after the columns come back puts it on Show less, where Enter folds the text (before: the memory lasted one render, and the keyboard stayed on the head, where Enter folds the card)", async (t) => {
  const { w, ok } = await open(t, textWorld());
  markOf(w, CHG).click(); await tick();
  headOf(w, closing.id).click(); await tick();         // the closing line's card open: its Resolve is the ask the status below answers (a status answering no ask renders nothing)
  const toggle = (): El => foldOf(w, CHG).row!.querySelector("button")!;
  toggle().focus();
  assert.equal(doc.activeElement, toggle(), "the fixture: the shown toggle takes the keyboard");
  toggle().click(); await tick();                      // Enter on a focused button is a click
  assert.equal(toggle().textContent, "Show less"); assert.equal(doc.activeElement, toggle(), "on the fresh Show less");
  // the fold to the list: the row is hidden there, so the keyboard goes to the card's head
  narrow = true; resize(); flush();
  assert.ok(!w.aside().classList.contains("fc-margin"));
  assert.equal(foldOf(w, CHG).hidden, true);
  assert.equal(doc.activeElement, headOf(w, CHG), "the list layout: the card's head");
  // a repaint while the columns are narrow
  const head1 = headOf(w, CHG);
  w.repaint(); await tick();
  assert.notEqual(headOf(w, CHG), head1, "the fixture: the repaint rebuilt the card");
  assert.equal(doc.activeElement, headOf(w, CHG), "the head still, after the repaint");
  // a status while the columns are narrow: Resolve on the closing line's card, answered with the store holding it resolved
  actIn(w.card(closing.id)!, "fcresolve")!.click(); await tick();   // the busy render
  assert.equal(doc.activeElement, headOf(w, CHG), "the head still, after the busy render");
  const head2 = headOf(w, CHG);
  await ok(status({ verb: "resolve", storeMtimeNs: "1757145600000000005", store: { v: 3, path: "docs/report.md", suggestions: [], comments: [whole, findings, passage, { ...closing, resolved: true }] } }));
  assert.notEqual(headOf(w, CHG), head2, "the fixture: the status rebuilt the cards");
  assert.equal(w.card(closing.id), null, "the fixture: the resolved card left the list");
  assert.equal(doc.activeElement, headOf(w, CHG), "the head still, after the status");
  assert.equal(foldOf(w, CHG).hidden, true, "the fixture: the row is still hidden in the list");
  // the columns come back: the pass shows the row (no render), and the next render puts the keyboard back on the toggle
  narrow = false; resize(); flush();
  assert.ok(w.aside().classList.contains("fc-margin"));
  assert.equal(foldOf(w, CHG).hidden, false);
  assert.equal(doc.activeElement, headOf(w, CHG), "a resize renders nothing: the head keeps it");
  w.repaint(); await tick();
  assert.equal(toggle().textContent, "Show less");
  assert.equal(doc.activeElement, toggle(), "the render brings the keyboard back to Show less (before: the head, the memory dropped by the first render while the columns were narrow)");
  // Enter there folds the text, not the card
  toggle().click(); await tick();
  assert.ok(w.card(CHG)!.classList.contains("open"), "the card is still open");
  assert.equal(toggle().textContent, "Show more"); assert.equal(foldOf(w, CHG).more, false, "the text folded");
  assert.equal(doc.activeElement, toggle(), "and the keyboard is on the fresh Show more");
  w.close();
});

test("a busy Reject is remembered across a repaint during its round trip: the keyboard goes to the card's head while the button is disabled, stays there through the repaint, and returns to Reject when the refusal keeps the card (before: the repaint dropped the memory, and the keyboard stayed on the head)", async (t) => {
  const { w, last, refuse } = await open(t, textWorld());
  markOf(w, CHG).click(); await tick();
  const reject = (): El => actIn(w.card(CHG)!, "fcreject")!;
  reject().focus();
  assert.equal(doc.activeElement, reject(), "the fixture: Reject takes the keyboard");
  reject().click(); await tick();                      // the round trip: Reject disabled and relabeled meanwhile
  assert.equal(last().verb, "reject", "the fixture: the reject went out");
  assert.ok(reject().disabled, "the fixture: Reject is busy");
  assert.equal(doc.activeElement, headOf(w, CHG), "the nearest place: the card's head");
  const head = headOf(w, CHG);
  w.repaint(); await tick();                           // a repaint mid-round-trip
  assert.notEqual(headOf(w, CHG), head, "the fixture: the repaint rebuilt the card");
  assert.ok(reject().disabled, "still busy");
  assert.equal(doc.activeElement, headOf(w, CHG), "the head still");
  await refuse("write-failed", "the sidecar is read-only");   // the refusal keeps the card, and Reject is back
  assert.ok(!reject().disabled, "the fixture: Reject is enabled again");
  assert.ok(w.card(CHG), "the fixture: the card stays");
  assert.equal(doc.activeElement, reject(), "the keyboard returns to Reject (before: the head)");
  w.close();
});

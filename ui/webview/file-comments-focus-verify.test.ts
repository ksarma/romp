// The focus follow-on's verification review (2026-09-09; plans/file-review.md, "The focus follow-on (2026-09-08)" under the
// margin-layout note), driven over the review stand-in file-comments-focus.test.ts uses: three gaps in the follow-on's
// coverage, each closed with the behavior it pins. The card a save landed in becomes the FOCUS (landSaved, focusOn): a
// reply saved on an OPEN card that is not the focus — pushed under the tall change card whose mark was clicked after the
// card opened — lands level with its mark, not where the push-down rule left it, a viewport below its mark (the other save
// tests open the card by its head first, which sets the focus before the save, so they held with the save's own setter
// removed); since decision 43 the save scrolls nothing, and the line at the panel's foot brings the card into view on a
// click (scrollCard). A comment bound to a change folds on its OWN card (the about follow-on, 2026-09-10; before it the
// change card hosted the comment, and this module drove the hosted run's fold through the change card's one row): its run
// of turns is marked cut, scrolled to its end and lifted by its own Show more, while the change card folds its own text
// alone and counts the comment in a tag, on a change whose own text is long and on a short change, whose card offers no
// toggle while the comment's does. And
// the fold's choice survives a re-render a STATUS drives (an ask answered with the store), not only the viewer's repaint
// the earlier modules used. The stand-in and the notes-api world are file-comments-focus.test.ts's, copied as the other
// focus modules copy them. Synthetic fixtures only: invented prose, placeholder ids.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inspect } from "node:util";
import * as fs from "node:fs";
import * as path from "node:path";
import type { FileViewActionCtx, TrackedEdit } from "./file-view";
import type { Status, StoreComment, Hunk } from "./file-comments-model";
import { hideEdges, staysEnumerable } from "../test-dom-shim";

const web = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const SRC = web("file-comments.ts");

// ── a DOM stand-in: ancestry, attributes, events with capture and bubbling, a small selector engine ──
class Ev {
  target: El | Txt | null = null;
  currentTarget: El | null = null;
  defaultPrevented = false;
  stopped = false;
  key: string; ctrlKey: boolean; metaKey: boolean;   // the save is Ctrl+Enter or Cmd+Enter since the composer follow-on (composerKeyAction)
  constructor(public type: string, init: { key?: string; ctrlKey?: boolean; metaKey?: boolean } = {}) { this.key = init.key || ""; this.ctrlKey = !!init.ctrlKey; this.metaKey = !!init.metaKey; }
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
  /** Focus lands only on a focusable, enabled element — a div with no tabindex ignores focus(), as the browser does. */
  focus(): void { if (this.tabIndex >= 0 && !this.disabled) doc.activeElement = this; }
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
// 5 holds the passage comment under it; blank rows between the later lines make each its own paragraph, and row 11 is the
// short change when the bound-comment fold tests put it in the store (withBound)
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
// a comment bound to the change by the legacy field (suggestionId "h1"): its own card, tagged "answered by a change", and
// the change card counts it (the about follow-on, 2026-09-10; before it the change card hosted the comment). A short body
// and a run of three turns, the run a long part of its own. Only the bound-comment fold tests put it in the store
// (withBound), so the other tests' numbers stand
const onChange: StoreComment = {
  id: (T0 + 2000) + "-3", author: "you", ts: T0 + 2000, body: "Cut this to the finding itself.", suggestionId: "h1", resolved: false,
  replies: [
    { author: "api", ts: T0 + 2100, body: "The paragraph carries the reasons the team weighed; cutting it loses why the plan changed." },
    { author: "you", ts: T0 + 2200, body: "Keep the reasons in a footnote, then; the finding should read in one breath." },
    { author: "api", ts: T0 + 2300, body: "Done in the next revision: the finding in one sentence, the reasons in a footnote under it." },
  ],
};
// a second change, a SHORT one: row 11's line, inserted whole by the session. Its card's own text fits the cap, so its card
// offers no toggle, while the comment bound to it folds its run of turns on its own card and offers one
const SHORT_LINE = "Line 11 of the report.";
const SHORT_AT = DOC.indexOf(SHORT_LINE);
const onShort: StoreComment = { ...onChange, id: (T0 + 3000) + "-11", ts: T0 + 3000, suggestionId: "h2", body: "Is this line needed at all?" };
const LONG_AT = DOC.indexOf(LONG);
const hunk: Hunk = { id: "h1", author: "api", ts: T0 - 30000, kind: "ins", curFrom: LONG_AT, curTo: LONG_AT + LONG.length, baseFrom: LONG_AT, baseTo: LONG_AT, oldText: "", newText: LONG, anchor: null };   // row 3
const CHG = "chg:h1";
const hunk2: Hunk = { id: "h2", author: "api", ts: T0 - 20000, kind: "ins", curFrom: SHORT_AT, curTo: SHORT_AT + SHORT_LINE.length, baseFrom: SHORT_AT, baseTo: SHORT_AT, oldText: "", newText: SHORT_LINE, anchor: null };   // row 11
const CHG2 = "chg:h2";
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
/** The status with the two bound comments and the short change in the store too (the bound-comment fold tests). */
const withBound = (storeMtimeNs: string, comments: StoreComment[] = [whole, findings, passage, closing, onChange, onShort], verb = "status"): Status =>
  status({ verb, store: { v: 3, path: "docs/report.md", suggestions: [], comments }, hunks: [hunk, hunk2], storeMtimeNs });

// ── the viewer stand-in: the body row, the seam as closures, a measurement table ───────────────────
// Geometry: the body's box is at viewport y=100, BODY_VIEW tall; the header stands OFFSET tall above the track and the
// footer FOOTER tall below it, so the track's box is TRACK tall; row i's text sits at 100 + ROW·i − scrollTop; a card is
// CARD tall closed and OPEN tall open, except a card with a long part (the change card's old and new text; a bound
// comment's run of turns, in the bound-comment fold tests), which is TALL open and folded (eight lines of the part)
// and WHOLE once Show more is pressed. A long part (LONG_PART: more than 200 characters) measures PART_ALL of content in
// a box of PART_CAP until its card wears fc-more — the table's reading of the sheet's cap; a short part fits its box.
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
      const h = !open ? CARD : el.querySelectorAll(".fc-clip").some(isLongPart) ? (el.classList.contains("fc-more") ? WHOLE : TALL) : OPEN;
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
async function open(t: Ctx, w: World, s: Status = status()) {
  t.after(() => w.close());                            // a failing assertion must not leave the panel alive (its deadline timers would hold the process)
  narrow = false; frames.length = 0; RO.all.length = 0; IO.all.length = 0; scrolledInto.length = 0; doc.activeElement = doc.body;
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

// ── the save's focus ──────────────────────────────────────────────────────────────────────────────

test("a reply saved on an open card that is NOT the focus makes that card the focus: level with its mark, the tall change card above moved up — not left where the push-down rule had it, a viewport below its mark — and nothing scrolled (decision 43); the line at the foot says below, and its click centers the card (the save's landSaved sets the focus; no earlier gesture on this path does)", async (t) => {
  const { w, ok, last } = await open(t, textWorld());
  const body = w.body, track = w.track();
  markOf(w, CHG).click(); await tick();                // the change card open, the focus; the passage's card pushed under it
  assert.equal(w.top(passage.id), PUSHED);
  headOf(w, passage.id).click(); await tick();         // the passage's card opened by its head: the focus, level
  assert.equal(w.top(passage.id), desired(5));
  markOf(w, CHG).click(); await tick();                // the change mark again: its card the focus; the OPEN passage card back under it
  assert.equal(w.top(CHG), desired(3));
  assert.ok(w.card(passage.id)!.classList.contains("open"), "the fixture: the passage's card is open");
  assert.equal(w.top(passage.id), PUSHED, "the fixture: open and not the focus, it is pushed under the tall card");
  assert.equal(w.card(passage.id)!.dataset.pushed, "1");
  // Reply on the passage's card: the box opens in the card. Reply is not a head click, so the focus stays the change card's
  actIn(w.card(passage.id)!, "fcreply")!.click(); await tick();
  const composer = w.aside().querySelector(".fc-composer")!;
  assert.equal(composer.hidden, false);
  assert.equal(w.top(passage.id), PUSHED, "Reply moved nothing");
  assert.equal(w.top(CHG), desired(3));
  body.scrollTop = 0; body.dispatchEvent(new Ev("scroll"));   // the reader looked at the top of the text meanwhile
  assert.equal(track.scrollTop, 0);
  const input = composer.querySelector(".fc-input")!;
  input.value = "The write-through one.";
  input.dispatchEvent(new Ev("keydown", { key: "Enter", ctrlKey: true }));   // the save chord
  await tick();
  assert.equal(last().verb, "reply");
  assert.equal(last().args.commentId, passage.id);
  const replied: StoreComment = { ...passage, replies: [{ author: "you", ts: T0 + 6000, body: "The write-through one." }] };
  await ok(status({ verb: "reply", store: { v: 3, path: "docs/report.md", suggestions: [], comments: [whole, findings, replied, closing] }, storeMtimeNs: "1757145600000000005" }));
  assert.ok(w.card(passage.id)!.classList.contains("open"), "the card stays open with its reply");
  assert.equal(w.card(passage.id)!.getBoundingClientRect().height, OPEN, "the fixture: the card with its one short turn fits the track");
  assert.equal(w.top(passage.id), desired(5), "the saved card is the focus: level with its mark (the push-down rule alone left it at " + PUSHED + ")");
  assert.equal(w.card(passage.id)!.dataset.pushed, undefined, "not pushed");
  assert.equal(w.top(CHG), LIFTED, "the change card moved up: its end a gap above the focused card");
  assert.equal(body.scrollTop, 0, "and nothing scrolled: a save never moves the view (decision 43; before it, the save brought the text to the card's mark)");
  assert.equal(track.scrollTop, 0);
  let box = cardBox(w, passage.id), mark = markOf(w, passage.id).getBoundingClientRect();
  assert.equal(box.top, mark.top, "the card and its highlight are level, past the boxes together");
  assert.ok(!inBox(box, TRACK_BOX), "the card is out of the track's box: " + JSON.stringify(box));
  assert.equal(composer.hidden, true, "the composer closed after");
  const line = actIn(w.aside(), "fcsavedgo")!;
  assert.equal(line.textContent, "Saved · the card is below", "the line at the foot says where it is");
  line.click(); await tick();
  const showCard = desired(5) + OPEN + 8 - TRACK;
  assert.equal(body.scrollTop, showCard, "the line's click brings the text to the card's mark: the least scroll that shows the card's end (scrollCard, the card the focus already)");
  assert.equal(track.scrollTop, showCard, "the track came along");
  box = cardBox(w, passage.id); mark = markOf(w, passage.id).getBoundingClientRect();
  assert.ok(inBox(box, TRACK_BOX), "the whole card is in the track's box: " + JSON.stringify(box));
  assert.ok(inBox(mark, BODY_BOX), "the highlight is in the body's box: " + JSON.stringify(mark));
  assert.equal(box.top, mark.top, "and the two are level");
  assert.deepEqual(scrolledInto, [], "a marked card is centered, not scrollIntoView'd");
  assert.equal(actIn(w.aside(), "fcsavedgo"), null, "the line is over");
  w.close();
});

// ── the bound comment's fold: on its own card ──────────────────────────────────────────────────────

test("a comment bound to a change folds on its OWN card (the about follow-on): its run of turns is marked cut and scrolled to its end, and the card's own Show more lifts it; the change card folds its own text alone, counts the comment in a '1 comment' tag and hosts nothing: on a change whose own text is long, and on a short change, whose card offers no toggle while the comment's card does", async (t) => {
  const { w } = await open(t, textWorld(), withBound("1757145600000000002"));
  const runText = onChange.replies!.map((r) => r.body!).join("");
  assert.ok(runText.length > LONG_PART && onChange.body.length <= LONG_PART && LONG.length > LONG_PART && SHORT_LINE.length <= LONG_PART, "the fixture: the bound comment's run is a long part and its body is not; the first change's text is long, the second's short");
  // every comment is its own card: the bound comment keeps one, tagged as answered by the change, and the change card counts
  // it (before the about follow-on, 2026-09-10, the change card hosted the comment and no card of its own stood in the list)
  for (const [c, id] of [[onChange, "h1"], [onShort, "h2"]] as Array<[StoreComment, string]>) {
    const card = w.card(c.id);
    assert.ok(!!card, "the comment bound to " + id + " has a card of its own");
    assert.equal(card!.querySelector(".fc-kind")!.title, "A comment the session answered with a change", "the legacy binding's title: answered, not about (the review, 2026-09-10)");
    assert.ok(card!.querySelector(".fc-ref")!.textContent.startsWith("added "), "its reference is the change's words");
    const tag = card!.querySelector(".fc-about")!;
    assert.equal(tag.textContent, "answered by a change", "the legacy binding's tag");
    assert.equal(tag.dataset.refs, id);
    assert.ok(tag.title.startsWith("The session answered this comment with: added ") && tag.title.endsWith("(pending)"), tag.title);
    const count = w.card("chg:" + id)!.querySelector(".fc-about-count")!;
    assert.equal(count.textContent, "1 comment", "the change card counts the comment about it");
    assert.equal(count.dataset.act, "fcaboutfirst"); assert.equal(count.dataset.id, id);
    assert.equal(count.title, "Show the comment about this change");
  }
  assert.equal(w.aside().querySelectorAll(".fc-hosted").length, 0, "no comment is drawn inside a change card");
  const partsOf = (key: string): El[] => w.card(key)!.querySelectorAll(".fc-clip");
  const runOf = (key: string): El => w.card(key)!.querySelector(".fc-replies")!;
  const toggle = (key: string): void => { foldOf(w, key).row!.querySelector("button")!.click(); };
  // the long change: its own text is the one part its card folds; nothing of the comment's is among its parts
  markOf(w, CHG).click(); await tick();
  let f = foldOf(w, CHG);
  assert.equal(f.parts, 1, "the change's text alone: the comment's body and run are on the comment's own card");
  assert.deepEqual(partsOf(CHG).map((x) => x.className), ["fc-body fc-diff fc-clip"]);
  assert.deepEqual(f.clipped, ["fc-body fc-diff fc-clip"], "the pass found the cap cut the change's text");
  assert.equal(f.hidden, false, "Show more shows"); assert.equal(f.label, "Show more"); assert.equal(f.more, false);
  assert.equal(w.card(CHG)!.getBoundingClientRect().height, TALL);
  // Show more on the change card lifts the change's text, and nothing else
  toggle(CHG); await tick();
  f = foldOf(w, CHG);
  assert.equal(f.more, true, "the card wears fc-more"); assert.deepEqual(f.clipped, [], "no fade on the part"); assert.equal(f.label, "Show less");
  assert.equal(w.card(CHG)!.getBoundingClientRect().height, WHOLE);
  // the comment's own card, opened by its head: its run of turns is cut, its body fits, and its own row shows
  headOf(w, onChange.id).click(); await tick();
  let g = foldOf(w, onChange.id);
  assert.equal(g.parts, 2, "the comment's body and its run of turns");
  assert.deepEqual(partsOf(onChange.id).map((x) => x.className), ["fc-body fc-clip", "fc-replies fc-clip"]);
  assert.deepEqual(g.clipped, ["fc-replies fc-clip"], "the pass found the cap cut the run; the body fits");
  assert.equal(g.hidden, false, "Show more shows on the comment's card"); assert.equal(g.label, "Show more"); assert.equal(g.more, false);
  assert.equal(runOf(onChange.id).clientHeight, PART_CAP, "the run's box is the cap");
  assert.equal(runOf(onChange.id).scrollTop, PART_ALL - PART_CAP, "the run shows its end: the newest turn");
  assert.equal(w.card(onChange.id)!.getBoundingClientRect().height, TALL);
  assert.equal(foldOf(w, CHG).more, true, "the change card's choice is its own: still whole");
  // the comment's Show more lifts its run; the change card is not touched
  toggle(onChange.id); await tick();
  g = foldOf(w, onChange.id);
  assert.equal(g.more, true); assert.deepEqual(g.clipped, []); assert.equal(g.label, "Show less");
  assert.equal(runOf(onChange.id).clientHeight, runOf(onChange.id).scrollHeight, "the run's box is its content");
  assert.equal(runOf(onChange.id).scrollTop, 0, "the run whole stands at its start");
  assert.equal(w.card(onChange.id)!.getBoundingClientRect().height, WHOLE);
  // Show less on the comment's card: folded again, the run at its end again
  toggle(onChange.id); await tick();
  g = foldOf(w, onChange.id);
  assert.equal(g.more, false); assert.deepEqual(g.clipped, ["fc-replies fc-clip"]); assert.equal(g.label, "Show more");
  assert.equal(runOf(onChange.id).scrollTop, PART_ALL - PART_CAP);
  assert.equal(foldOf(w, CHG).more, true, "the comment's fold left the change card whole");
  // Show less on the change card folds its text again
  toggle(CHG); await tick();
  f = foldOf(w, CHG);
  assert.equal(f.more, false); assert.deepEqual(f.clipped, ["fc-body fc-diff fc-clip"]); assert.equal(f.label, "Show more");
  assert.equal(w.card(CHG)!.getBoundingClientRect().height, TALL);
  // the short change: its text fits, and nothing of the comment's is on its card, so it offers no toggle. Before the about
  // follow-on the bound comment's run was the one part cut on this card and the row showed for it alone; the run now folds
  // on the comment's own card, which offers the row
  markOf(w, CHG2).click(); await tick();
  f = foldOf(w, CHG2);
  assert.equal(f.parts, 1); assert.deepEqual(f.clipped, [], "the change's own text fits");
  assert.equal(f.hidden, true, "no Show more on a card with nothing cut"); assert.equal(f.more, false);
  assert.equal(w.card(CHG2)!.getBoundingClientRect().height, OPEN);
  headOf(w, onShort.id).click(); await tick();
  g = foldOf(w, onShort.id);
  assert.equal(g.parts, 2);
  assert.deepEqual(g.clipped, ["fc-replies fc-clip"], "the run alone is cut: the body fits");
  assert.equal(g.hidden, false, "Show more shows for the run"); assert.equal(g.label, "Show more"); assert.equal(g.more, false);
  assert.equal(runOf(onShort.id).scrollTop, PART_ALL - PART_CAP, "scrolled to its end");
  assert.equal(w.card(onShort.id)!.getBoundingClientRect().height, TALL, "the card is folded at the run's cap");
  toggle(onShort.id); await tick();
  g = foldOf(w, onShort.id);
  assert.equal(g.more, true); assert.deepEqual(g.clipped, []); assert.equal(g.label, "Show less");
  assert.equal(runOf(onShort.id).scrollTop, 0);
  assert.equal(w.card(onShort.id)!.getBoundingClientRect().height, WHOLE);
  assert.equal(foldOf(w, CHG2).hidden, true, "the short change's card still offers no toggle");
  w.close();
});

// ── a status's re-render ──────────────────────────────────────────────────────────────────────────

test("the fold's choice survives a re-render a STATUS drives: after Show more, an ask answered with the store (Resolve on another card) rebuilds the cards and the change card still wears fc-more and reads Show less, the bound comment's own card too; after Show less, the next status leaves both folded, the comment's run scrolled to its end again", async (t) => {
  const { w, ok } = await open(t, textWorld(), withBound("1757145600000000002"));
  const run = (): El => w.card(onChange.id)!.querySelector(".fc-replies")!;   // the bound comment's run of turns, on its own card (the about follow-on)
  headOf(w, closing.id).click(); await tick();          // the two cards the asks below go through, opened for their Resolve (a closed card has no buttons)
  headOf(w, passage.id).click(); await tick();
  markOf(w, CHG).click(); await tick();                // the change card open, the focus
  foldOf(w, CHG).row!.querySelector("button")!.click(); await tick();   // Show more
  assert.equal(foldOf(w, CHG).more, true);
  headOf(w, onChange.id).click(); await tick();        // the comment's own card open: its run cut, at its end
  assert.deepEqual(foldOf(w, onChange.id).clipped, ["fc-replies fc-clip"]);
  assert.equal(run().scrollTop, PART_ALL - PART_CAP);
  foldOf(w, onChange.id).row!.querySelector("button")!.click(); await tick();   // Show more there too
  assert.equal(foldOf(w, onChange.id).more, true);
  const before = w.card(CHG)!; const beforeC = w.card(onChange.id)!;
  // an ask answered with a status: Resolve on the closing line's card, the store holding it resolved, the render a status runs
  actIn(w.card(closing.id)!, "fcresolve")!.click(); await tick();
  await ok(withBound("1757145600000000005", [whole, findings, passage, { ...closing, resolved: true }, onChange, onShort], "resolve"));
  assert.ok(w.card(CHG) !== before && w.card(onChange.id) !== beforeC, "the fixture: the status rebuilt the cards");
  let f = foldOf(w, CHG);
  assert.equal(f.more, true, "the choice survives the status's render: keyed by the card (openBodies)");
  assert.equal(f.label, "Show less"); assert.deepEqual(f.clipped, []);
  assert.equal(w.card(CHG)!.getBoundingClientRect().height, WHOLE);
  let g = foldOf(w, onChange.id);
  assert.equal(g.more, true, "the comment card's choice survives it too, under its own key");
  assert.equal(g.label, "Show less"); assert.deepEqual(g.clipped, []);
  assert.equal(w.card(onChange.id)!.getBoundingClientRect().height, WHOLE);
  assert.equal(run().scrollTop, 0, "the run whole, at its start");
  // Show less on both, then another status: folded stays folded, and the fresh render's run (its box starts at 0) is at its
  // end again
  foldOf(w, CHG).row!.querySelector("button")!.click(); await tick();
  foldOf(w, onChange.id).row!.querySelector("button")!.click(); await tick();
  assert.equal(foldOf(w, CHG).more, false); assert.equal(foldOf(w, onChange.id).more, false);
  const folded = w.card(CHG)!; const foldedC = w.card(onChange.id)!;
  actIn(w.card(passage.id)!, "fcresolve")!.click(); await tick();
  await ok(withBound("1757145600000000006", [whole, findings, { ...passage, resolved: true }, { ...closing, resolved: true }, onChange, onShort], "resolve"));
  assert.ok(w.card(CHG) !== folded && w.card(onChange.id) !== foldedC, "the fixture: rebuilt again");
  f = foldOf(w, CHG);
  assert.equal(f.more, false); assert.equal(f.label, "Show more");
  assert.deepEqual(f.clipped, ["fc-body fc-diff fc-clip"], "the pass marked the fresh part cut");
  assert.equal(w.card(CHG)!.getBoundingClientRect().height, TALL);
  g = foldOf(w, onChange.id);
  assert.equal(g.more, false); assert.equal(g.label, "Show more");
  assert.deepEqual(g.clipped, ["fc-replies fc-clip"], "the comment card's fresh run is marked cut");
  assert.equal(run().scrollTop, PART_ALL - PART_CAP, "the fresh render's run is scrolled to its end");
  assert.equal(w.card(onChange.id)!.getBoundingClientRect().height, TALL);
  w.close();
});

test("vocabulary: this module's own prose says file comment and run of turns; the word CONTEXT.md sets aside for a forked side session appears nowhere in it, nor the banned sessions-pane word, nor a home path", () => {
  const SELF = web("file-comments-focus-verify.test.ts").split("\n").filter((l) => !l.includes("assert.doesNotMatch(SELF")).join("\n");
  assert.doesNotMatch(SELF, /\bthreads?\b/i, "a comment with replies is a file comment with a run of turns (CONTEXT.md, File comment: Avoid)");
  assert.doesNotMatch(SELF, /fleet/i, "no new identifiers or prose in the old word for the sessions pane");
  assert.doesNotMatch(SELF, /\/home\/[a-z]/, "no absolute home paths");
});

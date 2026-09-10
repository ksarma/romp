// Reveal runs ONE margin pass per click (the review of the merge audit's fixes, round 2, 2026-09-09; plans/file-review.md,
// "The focus follow-on (2026-09-08)" under the margin-layout note: a pass runs after the switch where the switch painted
// nothing). revealInRaw writes the focus, asks the viewer for Raw, and runs a pass itself where the switch ran none — a file
// with no Rendered view is Raw already, and the seam's setMode returns without a paint. Its guard read the pass's memory
// (laidOn), and so ran the pass again after a switch whose own pass HAD run but found the revealed card loose and fell to
// the focus it had: with Show changes inline off Raw paints no mark for a change card, so every change card's Reveal
// measured and wrote the whole margin twice — every card's and mark's box read again, the tops, the list's height and the
// body's padding written again, to the same values (file-comments-reveal-arms-focus.test.ts pins that nothing moves). The
// guard now keys on the placement (`placed`): every pass ends by writing a new one, so the placement of before still
// standing after the switch is the switch having run no pass. Held here by behaviour, with the passes counted: the switch's
// pass is the only one on a markdown file, with the marks off (a change card, the deletion's card, from Raw and from
// Rendered) as with them on (the note's card in Rendered); and on a file with no Rendered view the pass revealInRaw runs
// itself is the only one. The stand-in is file-comments-reveal-arms-focus.test.ts's, with one addition: the global
// getComputedStyle counts its calls. The pass reads it first (marginMode, the sheet's verdict on the fold) and placeCards
// is the module's only caller of the global — the composer's two readers go through window.getComputedStyle, which the
// stand-in's window lacks, and the PDF chunk's reader never runs over a markdown file — so the calls are the passes, all
// of them synchronous here (the frame queue is never flushed). Synthetic fixtures only: the notes-api world, placeholder ids.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inspect } from "node:util";
import * as fs from "node:fs";
import * as path from "node:path";
import type { FileViewActionCtx, TrackedEdit } from "./file-view";
import type { Status, StoreComment, Hunk } from "./file-comments-model";
import { hideEdges, staysEnumerable } from "../test-dom-shim";

// ── a DOM stand-in: ancestry, attributes, events with capture and bubbling, a small selector engine ──
class Ev {
  target: El | Txt | null = null;
  currentTarget: El | null = null;
  defaultPrevented = false;
  stopped = false;
  key: string; ctrlKey: boolean; metaKey: boolean;
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
  naturalWidth = 0; naturalHeight = 0; complete: boolean | undefined = undefined; width = 0; height = 0;
  rect: Rect | null = null;
  private st = 0;
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
  focus(): void { if (this.tabIndex >= 0 && !this.disabled) doc.activeElement = this; }
  blur(): void { if (doc.activeElement === this) doc.activeElement = doc.body; }
  scrollIntoView(): void { scrolledInto.push(this); }
  getBoundingClientRect(): Rect { return this.rect || (cur ? cur.measure(this) : ZERO); }
  get offsetWidth(): number { return 0; }
  /** The scroll position, clamped to the scroller's range as the browser clamps it. */
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
  if (ev.type === "load") { run(target instanceof El ? target.listeners : [], false, target as El); return true; }
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
(globalThis as any).fetch = async () => ({ status: 404, headers: { get: () => null }, json: async () => [] });
// the layout's environment: the sheet's verdict on the fold (the columns, always: every drive here is in the margin
// layout), the frame queue, the observers
(globalThis as any).getComputedStyle = () => ({ flexDirection: "row" });
const frames: Array<() => void> = [];
(globalThis as any).requestAnimationFrame = (cb: () => void): number => { frames.push(cb); return frames.length; };
(globalThis as any).cancelAnimationFrame = (): void => { /* inert */ };
class RO {
  static all: RO[] = [];
  targets = new Set<El>();
  constructor(public cb: () => void) { RO.all.push(this); }
  observe(t: El): void { this.targets.add(t); }
  unobserve(t: El): void { this.targets.delete(t); }
  disconnect(): void { this.targets.clear(); }
}
(globalThis as any).ResizeObserver = RO;
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
// one logical line per row of the Raw view, each ROW px tall in the measurement table (the audit stand-in's world, with
// one row changed). Row 3 is a long paragraph the session inserted whole (the change whose card is TALL open); row 5
// holds the passage comment; row 7 carries the deletion's point; row 9 is an HTML comment block, a note to the session,
// which the Rendered view drops (marked emits the comment and the browser shows nothing), so a comment on its words has
// no highlight there — its card is loose in Rendered, with Reveal — while the Raw view shows the row and paints it
const LONG = "The api session rewrote the findings as one long paragraph about the cache, the latency budget, the plan for the next release and the reasons the team settled on it, going on for several sentences more than the one line it replaced, so that its card shows far more text than fits beside the passage.";
const NOTE = "<!-- api: the cache numbers need a second look before the release -->";
const LINES = ["# Report", "", "## Findings", LONG, "", "We recommend " + QUOTE + ".", "", "More text here.", "", NOTE];
for (let i = 10; i < 33; i++) LINES.push(i % 2 ? "Line " + i + " of the report." : "");
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
/** The comment on the HTML comment block (row 9): a short body, and with `talked` a short run of two turns under it, so
 *  its open card is taller than one with the body alone (MID in the table) while nothing on it is long enough to fold. */
const NOTE_ID = (T0 + 9000) + "-9";
const noteOn = (talked: boolean): StoreComment => ({
  id: NOTE_ID, author: "you", ts: T0 + 9000, body: "Which numbers, and against which run?",
  anchor: { quote: "the cache numbers need a second look", prefix: "<!-- api: ", suffix: " before the release" }, resolved: false,
  replies: talked ? [
    { author: "api", ts: T0 + 9100, body: "The p95 and the p99, against the staging run." },
    { author: "you", ts: T0 + 9200, body: "Then name the run in the note." },
  ] : [],
});
const LONG_AT = DOC.indexOf(LONG);
const hunk: Hunk = { id: "h1", author: "api", ts: T0 - 30000, kind: "ins", curFrom: LONG_AT, curTo: LONG_AT + LONG.length, baseFrom: LONG_AT, baseTo: LONG_AT, oldText: "", newText: LONG, anchor: null };   // row 3
const CHG = "chg:h1";
// the deletion's point on row 7: its card offers Reveal whatever the view paints (renderChange: a deletion's mark is a point)
const DEL = "chg:h2";
const DEL_AT = DOC.indexOf("More text here.") + "More text ".length;
const del: Hunk = { id: "h2", author: "api", ts: T0 - 20000, kind: "del", curFrom: DEL_AT, curTo: DEL_AT, baseFrom: DEL_AT, baseTo: DEL_AT + 6, oldText: "right ", newText: "", anchor: null };
function status(talked = false): Status {
  return {
    verb: "status", root: ROOT, storePath: ROOT + "/.trackchanges/docs%2Freport.md.json", trackedBy: { kind: "file", entry: "docs/report.md" }, agentTooling: "present",
    fileMtimeNs: "1757145600000000001", storeMtimeNs: "1757145600000000002", configMtimeNs: "1757145600000000003",
    store: { v: 3, path: "docs/report.md", suggestions: [], comments: [whole, findings, passage, closing, noteOn(talked)] },
    hunks: [hunk, del], log: [],
    unsent: { comments: [passage.id], replies: [], accepted: 0, rejected: 0, watermark: null },
  };
}

// ── the viewer stand-in: the body row, the seam as file-view.ts has it, a measurement table ─────────
// Geometry (the audit stand-in's): the body's box is at viewport y=100, BODY_VIEW tall; the header stands OFFSET tall
// above the track and the footer FOOTER tall below it, so the track's box is TRACK tall; row i's text sits at
// 100 + ROW·i − scrollTop in either view (a Rendered block carries its row); a card is CARD tall closed and OPEN tall
// open — MID with a short run of turns under its body, and with a long part (the change card's text) TALL folded and
// WHOLE once Show more is pressed. A long part (more than LONG_PART characters) measures PART_ALL of content in a box
// of PART_CAP until its card wears fc-more; a short part fits its box.
const ROW = 60, OFFSET = 60, FOOTER = 40, CARD = 40, OPEN = 120, MID = 150, TALL = 200, WHOLE = 400, BODY_VIEW = 260, TRACK = BODY_VIEW - OFFSET - FOOTER;   // TRACK 160
const PART_ALL = 400, PART_CAP = 100, LONG_PART = 200;
type View = "raw" | "rendered";
type Scroll = { offset: number; view: View; rows: boolean };
type World = {
  ctx: FileViewActionCtx; posted: any[]; main: El; body: El;
  hooks: { rendered: Array<() => void>; close: Array<() => void> };
  editing: boolean; viewMtime: string; content: number;
  modes: string[]; scrolls: Scroll[]; paints: number;
  view(): View;
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
/** marked's rendering of DOC, built by hand: one element per block in order, holding the block's text and carrying its
 *  row; a blank line is no block, and the HTML comment block renders nothing (the browser shows a comment as nothing). */
function renderedDoc(box: El): void {
  const out: El[] = [];
  LINES.forEach((ln, i) => {
    if (!ln || ln.startsWith("<!--")) return;
    const e = new El(ln.startsWith("## ") ? "h2" : ln.startsWith("# ") ? "h1" : "p");
    e.dataset.row = String(i);
    e.appendChild(new Txt(ln.replace(/^#+ /, "")));
    out.push(e);
  });
  box.replaceChildren(...out);
}
const isLongPart = (el: El): boolean => el.classList.contains("fc-clip") && el.textContent.length > LONG_PART;
const cardOf = (el: El): El | null => el.closest(".fc-card");
/** The row a mark stands in: its Raw row's index, or the row its Rendered block carries. */
const rowOf = (el: El): number => {
  const cl = el.closest(".fv-cl");
  if (cl && cl.parentNode) return cl.parentNode.childNodes.indexOf(cl);
  const blk = el.closest("[data-row]");
  return blk ? Number(blk.dataset.row) : -1;
};
type Opts = { md?: boolean; view?: View };
/** The viewer over DOC: `md` false for a file with no Rendered view (the seam's setMode returns without a paint, as
 *  file-view.ts's does when the file is not markdown); `view` the view showing at first. */
function viewer(over: Opts = {}): World {
  const md = over.md !== false;
  let view: View = over.view || "raw";
  const body = new El("div"); body.className = "fileview-body";
  const main = new El("div"); main.className = "fileview-main";
  main.appendChild(body);
  doc.body.replaceChildren(main);
  const paintBody = (): void => {
    if (view === "raw") {
      const wrap = new El("div"); wrap.className = "fileview-code";
      const pre = new El("pre"); pre.className = "fileview-pre fileview-wrap";
      const code = new El("code"); code.className = "hljs";
      pre.appendChild(code); wrap.appendChild(pre);
      rows(code, DOC);
      body.replaceChildren(wrap);
    } else {
      const box = new El("div"); box.className = "fileview-md";
      renderedDoc(box);
      body.replaceChildren(box);
    }
  };
  paintBody();
  const w = {
    posted: [] as any[], main, body, hooks: { rendered: [] as Array<() => void>, close: [] as Array<() => void> }, editing: false,
    viewMtime: "1757145600000000001", content: ROW * ROWS, modes: [] as string[], scrolls: [] as Scroll[], paints: 0,
    view: () => view,
  } as World;
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
      const h = !open ? CARD : el.querySelectorAll(".fc-clip").some(isLongPart) ? (el.classList.contains("fc-more") ? WHOLE : TALL) : el.querySelector(".fc-replies") ? MID : OPEN;
      return R(412, 0, 316, h);
    }
    if (el.classList.contains("fc-hl") || el.classList.contains("fc-ins") || el.classList.contains("fc-del")) {
      const i = rowOf(el);
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
  w.repaint = () => { w.paints++; for (const cb of w.hooks.rendered) cb(); };
  w.close = () => { for (const cb of w.hooks.close.splice(0)) cb(); if (cur === w) cur = null; };
  const noop = () => { /* inert */ };
  w.ctx = {
    path: ABS, sid: SID, todoId: null,
    body: () => w.body as unknown as HTMLElement, mode: () => view, text: () => DOC, mtimeNs: () => w.viewMtime, media: () => null, mediaElement: () => null, renderedImages: () => [], pdfPages: () => [],
    identity: () => ({ name: "api", color: null }),
    onRendered: (cb) => { w.hooks.rendered.push(cb); }, onSelection: noop, onSaved: noop, onClose: (cb) => { w.hooks.close.push(cb); },
    post: (m) => { w.posted.push(m); }, ensureEditingAllowed: async () => true, setEditBlocked: noop, editing: () => w.editing, setTrackedEdit: (_t: TrackedEdit | null) => { /* inert */ }, guardClose: noop,
    aside: (node) => { w.main.querySelector(".fileview-aside")?.remove(); if (node) { const n = node as unknown as El; n.classList.add("fileview-aside"); w.main.appendChild(n); } },
    // the seam, as file-view.ts has it: `if (!isMd || editing) return; fmt.md = mode; saveFmt(fmt); renderBody();` — renderBody
    // swaps the body synchronously and fires onRendered, the panel's paint pass
    setMode: (m) => { w.modes.push(m); if (!md) return; view = m as View; paintBody(); w.repaint(); },
    // and its scroll: the `.fv-cl` at the count of line ends before the offset, clamped to the last row, centered — over a
    // Rendered body there are no rows and nothing moves. The table's centering: the row's middle at the body's
    scrollToOffset: (n) => {
      const code = body.querySelector("code.hljs");
      w.scrolls.push({ offset: n, view, rows: !!code });
      if (!code) return;
      const all = code.querySelectorAll(".fv-cl");
      if (!all.length) return;
      const line = (DOC.slice(0, Math.max(0, n)).match(/\n/g) || []).length;
      body.scrollTop = rowCentered(Math.min(line, all.length - 1));
    },
    reload: noop,
  };
  cur = w;
  return w;
}
/** Where scrollToOffset's centering of row i leaves the body: the row's middle at the body's middle. */
const rowCentered = (i: number): number => ROW * i + ROW / 2 - BODY_VIEW / 2;
type Posted = Record<string, any>;
type Ctx = { after(fn: () => void): void };
async function open(t: Ctx, w: World, s: Status = status()) {
  t.after(() => w.close());                            // a failing assertion must not leave the panel alive (its deadline timers would hold the process)
  frames.length = 0; RO.all.length = 0; IO.all.length = 0; scrolledInto.length = 0; doc.activeElement = doc.body;
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
const marksOf = (w: World, key: string): El[] => key.startsWith("chg:")
  ? w.body.querySelectorAll('[data-act="fcchange"]').filter((m) => m.dataset.id === key.slice(4))
  : w.body.querySelectorAll(".fc-hl").filter((m) => m.dataset.id === key);
const markOf = (w: World, key: string): El => { const m = marksOf(w, key)[0]; assert.ok(m, key + " has a mark in the " + w.view() + " view"); return m; };
/** The viewport box a card's placed top gives it: the track's top, plus its top in the track's content, less the track's scroll. */
const cardBox = (w: World, key: string): { top: number; bottom: number } => { const top = 100 + OFFSET + w.top(key)! - w.track().scrollTop; return { top, bottom: top + w.card(key)!.getBoundingClientRect().height }; };
const TRACK_BOX = { top: 100 + OFFSET, bottom: 100 + OFFSET + TRACK };
const inBox = (box: { top: number; bottom: number }, of: { top: number; bottom: number }): boolean => box.top >= of.top && box.bottom <= of.bottom;
/** Where centerOn leaves the body for a card placed at `top` in the track's content, `height` tall: the mark's top at the
 *  body's middle, or — where that leaves the card's end past the track's box — the least scroll that shows the card's
 *  end, as far as keeps the mark's top a gap under the body's top (the panel's centerOn, in the table's geometry). */
const settled = (top: number, height: number): number => {
  const markY = top + OFFSET;
  let want = markY - BODY_VIEW / 2;
  const showCard = top + height + 8 - TRACK;
  if (showCard > want) want = Math.min(showCard, markY - 8);
  return want;
};
/** The revealed card's landing, all of it: level with its Raw mark, not pushed, the body where centerOn leaves it and the
 *  track with the body, the card's end in the track's box (its head too, for a card the track has room for). */
function landed(w: World, key: string, height: number, why: string): void {
  const top = w.top(key)!;
  const card = w.card(key)!, mark = markOf(w, key);
  assert.equal(card.dataset.pushed, undefined, why + ": not pushed");
  assert.equal(card.getBoundingClientRect().height, height, why + ": the card's height as the table has it");
  const scroll = settled(top, height);
  assert.equal(w.body.scrollTop, scroll, why + ": the body scrolled the least that shows the card's end, " + scroll);
  assert.equal(w.track().scrollTop, scroll, why + ": the track with it");
  const box = cardBox(w, key);
  assert.equal(box.top, mark.getBoundingClientRect().top, why + ": the card is level with its mark");
  assert.ok(box.bottom <= TRACK_BOX.bottom, why + ": the card's end is in the track's box: " + JSON.stringify(box) + " in " + JSON.stringify(TRACK_BOX));
  if (height + 8 <= TRACK) assert.ok(inBox(box, TRACK_BOX), why + ": the card is whole in the track's box: " + JSON.stringify(box));
}

// ── the pass count ──────────────────────────────────────────────────────────────────────────────────────────────────
let passes = 0;
(globalThis as any).getComputedStyle = () => { passes++; return { flexDirection: "row" }; };
/** The passes `act` ran, counted to the end of the tick that follows it. */
async function passesOver(act: () => void): Promise<number> { const n = passes; act(); await tick(); return passes - n; }
type Laid = { key: string | undefined; top: unknown; pushed: string | undefined; pulled: string | undefined; push: string; pull: string };
/** Everything the pass writes: each card's top and leaders, the list's height, the body's end padding. */
function layoutOf(w: World): { cards: Laid[]; height: unknown; pad: unknown } {
  const cards = w.list().querySelectorAll(".fc-card").map((c): Laid => ({ key: c.dataset.id, top: c.style.top, pushed: c.dataset.pushed, pulled: c.dataset.pulled, push: c.style.getPropertyValue("--fc-push"), pull: c.style.getPropertyValue("--fc-pull") }));
  return { cards, height: w.list().style.height, pad: w.body.style.paddingBottom };
}
/** The switch, watched: what the switch's own pass left, read inside setMode before reveal() goes on. */
function watchSwitch(w: World): Array<{ view: View; laid: ReturnType<typeof layoutOf>; passes: number }> {
  const seen: Array<{ view: View; laid: ReturnType<typeof layoutOf>; passes: number }> = [];
  const real = w.ctx.setMode;
  w.ctx.setMode = (m) => { const n = passes; real(m); seen.push({ view: w.view(), laid: layoutOf(w), passes: passes - n }); };
  return seen;
}

// ── Show changes inline off: the switch's pass finds the card loose and falls to the focus it had; no second pass ──────

/** The marks off, the passage's card the focus from its highlight, `key`'s card (a change card: loose with the marks off)
 *  opened by its head, then its Reveal, from `view`. The switch's own pass is the one pass of the click. */
async function revealWithMarksOff(t: Ctx, key: string, view: View): Promise<World> {
  const w = viewer({ view });
  await open(t, w);
  actIn(w.aside(), "fcinline")!.click(); await tick();   // Show changes inline off: no change mark in either view
  assert.equal(marksOf(w, key).length, 0, "no mark for " + key + " in " + view);
  markOf(w, passage.id).click(); await tick();          // the passage's card the focus from its highlight
  assert.equal(w.top(passage.id), desired(5), "the passage's card is level with its highlight");
  headOf(w, key).click(); await tick();                 // the change card opened by its head: loose, so the focus stays the passage's
  assert.ok(w.card(key)!.classList.contains("open"));
  assert.ok(actIn(w.card(key)!, "fcreveal"), key + "'s card offers Reveal with the marks off");
  const before = layoutOf(w);
  const paints = w.paints;
  const seen = watchSwitch(w);
  const ran = await passesOver(() => actIn(w.card(key)!, "fcreveal")!.click());
  assert.deepEqual(w.modes, ["raw"], "Reveal asked for Raw once");
  assert.equal(w.paints, paints + 1, "the switch painted the body once (Raw over " + view + ": the seam re-renders, as file-view.ts's setMode does on a markdown file)");
  assert.equal(seen.length, 1);
  assert.equal(seen[0].passes, 1, "the switch's own pass ran, inside setMode");
  assert.equal(ran, 1, "and it was the click's only pass (before the fix: a second, after the switch, over the same body and cards)");
  assert.equal(marksOf(w, key).length, 0, "Raw paints no mark for it either");
  assert.deepEqual(layoutOf(w), seen[0].laid, "nothing after the switch's pass wrote a top, a leader, the list's height or the body's padding");
  assert.equal(w.top(passage.id), desired(5), "the switch's pass kept the focus it had: the passage's card level with its highlight");
  // from Raw the switch re-renders the view the cards were laid over, so the pass reads what the last one read and lays them
  // where it did; from Rendered the switch paints the note's Raw highlight (row 9, an HTML comment block Rendered drops), new
  // information the pass acts on — the note's card, loose in Rendered, is pushed under the chain in Raw — so the layout before
  // the click is not the one after, and the claims are the pass count and the after-switch equality above
  if (view === "raw") assert.deepEqual(layoutOf(w).cards.map((c) => [c.key, c.top, c.pushed]), before.cards.map((c) => [c.key, c.top, c.pushed]), "the cards stand where the pass laid them before the click");
  else assert.equal(w.card(NOTE_ID)!.dataset.pushed, "1", "the note's card, loose in Rendered, is pushed under the chain in Raw: the switch's pass read its new highlight");
  return w;
}

test("with Show changes inline off, from Raw: Reveal on the change card runs one pass, the switch's own, which finds the card loose and keeps the focus it had; no pass runs after the switch (before the fix: the whole margin measured and written a second time, to the same values); the row is centered and wears the landing cue", async (t) => {
  const w = await revealWithMarksOff(t, CHG, "raw");
  assert.deepEqual(w.scrolls, [{ offset: LONG_AT, view: "raw", rows: true }], "the scroll went to the change's start");
  assert.equal(w.body.scrollTop, rowCentered(3), "the row's centering stands: no mark for centerOn to settle on");
  const cued = w.body.querySelectorAll(".fc-landing");
  assert.equal(cued.length, 1, "one row wears the landing cue");
  assert.equal(rowOf(cued[0]), 3, "the row the scroll centered");
  w.close();
});

test("with Show changes inline off, from Rendered: the same one pass — the switch to Raw paints, its pass falls to the focus it had, and none runs after it", async (t) => {
  const w = await revealWithMarksOff(t, CHG, "rendered");
  assert.equal(w.view(), "raw");
  assert.deepEqual(w.scrolls, [{ offset: LONG_AT, view: "raw", rows: true }], "the scroll went to the change's start, over the Raw rows");
  w.close();
});

test("with Show changes inline off, the deletion's card (Reveal offered whatever the view paints): one pass, the switch's", async (t) => {
  const w = await revealWithMarksOff(t, DEL, "raw");
  assert.deepEqual(w.scrolls, [{ offset: DEL_AT, view: "raw", rows: true }], "the scroll went to the deletion's point");
  const cued = w.body.querySelectorAll(".fc-landing");
  assert.equal(cued.length, 1, "the point's row wears the landing cue: with the marks off there is no mark for it");
  assert.equal(rowOf(cued[0]), 7);
  w.close();
});

// ── where a pass IS to run after the switch, and where the switch's pass lays the card: one pass, either way ──────────

test("a file with no Rendered view (the seam's setMode returns without a paint): the pass revealInRaw runs itself is the click's only pass, and it lays the revealed card level with its point", async (t) => {
  const w = viewer({ md: false });
  await open(t, w);
  headOf(w, DEL).click(); await tick();                // opened by its head: the focus for now, level with its point
  markOf(w, CHG).click(); await tick();                // the change card the focus from its mark
  actIn(w.card(CHG)!, "fcclip")!.click(); await tick();   // Show more: WHOLE
  assert.equal(w.top(CHG), desired(3), "the unfolded change card is the focus, at its mark");
  assert.equal(w.card(DEL)!.dataset.pushed, "1", "the deletion's card is pushed under it");
  const paints = w.paints;
  const seen = watchSwitch(w);
  const ran = await passesOver(() => actIn(w.card(DEL)!, "fcreveal")!.click());
  assert.deepEqual(w.modes, ["raw"], "Reveal asked for Raw once");
  assert.equal(w.paints, paints, "the seam painted nothing: the file has no Rendered view");
  assert.equal(seen[0].passes, 0, "so the switch ran no pass");
  assert.equal(ran, 1, "revealInRaw ran the one pass itself, after the switch");
  assert.equal(w.top(DEL), desired(7), "which laid the revealed card level with its point");
  assert.equal(w.card(DEL)!.dataset.pushed, undefined, "not pushed");
  landed(w, DEL, OPEN, "after Reveal on the deletion's card");
  w.close();
});

test("the comment's branch, Rendered, a comment on an HTML comment block (loose in Rendered, marked in Raw): the switch's own pass lays the card level with its Raw highlight, and it is the click's only pass — the fix skips the pass after the switch where the switch's pass laid the card too, not only where it fell to the focus it had", async (t) => {
  const w = viewer({ view: "rendered" });
  await open(t, w);
  assert.equal(marksOf(w, NOTE_ID).length, 0, "the note's passage has no Rendered mark");
  headOf(w, NOTE_ID).click(); await tick();            // opened by its head: a loose card, so the pass keeps the focus it had
  markOf(w, CHG).click(); await tick();                // the change card the focus from its Rendered mark
  actIn(w.card(CHG)!, "fcclip")!.click(); await tick();   // Show more: WHOLE
  assert.equal(w.top(CHG), desired(3), "the unfolded change card is the focus, at its mark");
  assert.notEqual(w.top(NOTE_ID), desired(9), "the note's card is loose in Rendered: not at its Raw row's height");
  const paints = w.paints;
  const seen = watchSwitch(w);
  const ran = await passesOver(() => actIn(w.card(NOTE_ID)!, "fcreveal")!.click());
  assert.deepEqual(w.modes, ["raw"], "Reveal asked for Raw once");
  assert.equal(w.paints, paints + 1, "the switch painted Raw");
  assert.equal(seen[0].passes, 1, "and its pass ran inside setMode");
  assert.equal(seen[0].laid.cards.find((c) => c.key === NOTE_ID)!.top, desired(9) + "px", "which laid the note's card level with its Raw highlight (the focus written before the switch)");
  assert.equal(ran, 1, "the click's only pass");
  assert.equal(w.top(NOTE_ID), desired(9), "the card stands level after Reveal");
  landed(w, NOTE_ID, OPEN, "after Reveal on the note's card");
  w.close();
});

test("vocabulary: this module's own prose says a change's old and new text, file comment and run of turns; the words CONTEXT.md sets aside — the short word for a change's text (Change: Avoid) and the one for a forked side session (File comment: Avoid) — appear nowhere in it, nor the banned sessions-pane word, nor a home path", () => {
  const SELF = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "file-comments-reveal-one-pass.test.ts"), "utf8").split("\n").filter((l) => !l.includes("assert.doesNotMatch(SELF")).join("\n");
  assert.doesNotMatch(SELF, /\bdiffs?\b/i, "the folded part of a change card is the change's old and new text (CONTEXT.md, Change: Avoid)");
  assert.doesNotMatch(SELF, /\bthreads?\b/i, "a comment with replies is a file comment with a run of turns (CONTEXT.md, File comment: Avoid)");
  assert.doesNotMatch(SELF, /fleet/i, "no new identifiers or prose in the old word for the sessions pane");
  assert.doesNotMatch(SELF, /\/home\/[a-z]/, "no absolute home paths");
});

test("the stand-in's nodes inspect as their projection: no enumerable edge, so a failing assertion's dump cannot walk the tree", () => {
  const root = doc.createElement("div");
  const kid = doc.createElement("span");
  root.appendChild(kid);
  kid.appendChild(doc.createTextNode("leaf"));
  root.setAttribute("data-x", "1"); root.classList.add("c");
  for (const n of [root, kid, kid.firstChild as Txt]) {
    assert.ok(Object.keys(n).every((k) => staysEnumerable((n as unknown as Record<string, unknown>)[k])), "only primitives stay enumerable on " + n.constructor.name);
    const dump = inspect(n, { compact: false, customInspect: false, depth: 1000, maxArrayLength: Infinity, showHidden: false, showProxy: false, sorted: true, getters: true });
    assert.ok(!dump.includes("parentNode") && !dump.includes("childNodes"), "no edge in the dump: " + dump);
  }
});

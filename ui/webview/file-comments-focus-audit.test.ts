// The focus follow-on's merge audit (2026-09-09; plans/file-review.md, "The focus follow-on (2026-09-08)" under the
// margin-layout note), over the review stand-in file-comments-focus.test.ts drives: the panel's stand-ins for what the
// audit's real-viewer leg (file-view-focus-seat-browser.test.ts) and its panel-alone leg measure in an engine. Reveal arms
// the focus: with a tall change card unfolded as the focus and another card pushed under it, Reveal on that card writes the
// focus BEFORE the switch to Raw, so the pass the viewer's setMode runs synchronously lays the card level with its Raw mark
// and the scroll that follows centers a card already in place (before: reveal() set no focus, the pass kept the tall card,
// and the revealed card stayed under it, outside the track's box while its passage was centered). The fold to the list
// layout clears what the margin pass wrote on the list and the cards it kept: with a reply's box standing in a card the
// rebuild grafts around the box and keeps the live list, so the inline height the pass gave the list (as tall as the body's
// range) stayed on it in the list layout and the aside scrolled through a screen and more of empty space under the cards
// (before: layoutOff cleared the sheet's class, the body's padding and the placement, not the list's height nor the cards'
// tops). Synthetic fixtures only: the notes-api world, placeholder ids.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import type { FileViewActionCtx, TrackedEdit } from "./file-view";
import type { Status, StoreComment, Hunk } from "./file-comments-model";

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
  parentNode: El | null = null;
  constructor(public data: string) {}
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
  parentNode: El | null = null;
  childNodes: Array<El | Txt> = [];
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
  constructor(tag: string) { this.tagName = tag.toUpperCase(); }
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
// 5 holds the passage comment under it; blank rows between the later lines make each its own paragraph, and rows 7 and 9
// carry the essay and the talked comment when the comment-fold test puts them in the store
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
// two comments with long parts of their own, for the comment card's fold (renderCard's fc-more is not renderChange's): the
// essay's BODY runs past the cap, and the talked comment's short body carries a RUN OF TURNS that does. Only the comment-fold test
// puts them in the store (withLong), so the other tests' numbers stand
const LONG_BODY = "This paragraph needs the numbers behind it: the latency budget it cites, the cache hit rate the api session measured, the release the plan names and the reasons the team settled on it, each with a pointer to where a reader can check it, or the claim reads as opinion.";
const essay: StoreComment = {   // row 7
  id: (T0 + 7000) + "-7", author: "you", ts: T0 + 7000, body: LONG_BODY,
  anchor: { quote: "More text here", prefix: "", suffix: "." }, replies: [], resolved: false,
};
const talked: StoreComment = {   // row 9: a comment with a run of three turns under it (the name the focus-review module gives the shape)
  id: (T0 + 9000) + "-9", author: "you", ts: T0 + 9000, body: "Is this line still current?",
  anchor: { quote: "Line 9 of the report", prefix: "", suffix: "." }, resolved: false,
  replies: [
    { author: "api", ts: T0 + 9100, body: "It is: the numbers came from the run on the release branch, not the draft's." },
    { author: "you", ts: T0 + 9200, body: "Then say so in the line itself, with the branch and the date of the run." },
    { author: "api", ts: T0 + 9300, body: "Done in the next revision; the branch and the date are in the sentence now." },
  ],
};
// a second comment on row 5, later than the passage's, on the words before QUOTE. Only the leader test puts it in the store
// (withRec): two cards want the same top, so the later one is pushed under the first — and as the focus it holds the top and
// moves the first UP past its mark, the case the leader down is drawn for
const rec: StoreComment = {
  id: (T0 + 1000) + "-5", author: "you", ts: T0 + 1000, body: "Recommend, or require?",
  anchor: { quote: "We recommend", prefix: "", suffix: " " + QUOTE }, replies: [], resolved: false,
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
/** The status with the later comment on row 5 in the store too (the leader test). */
const withRec = (storeMtimeNs: string): Status => status({ store: { v: 3, path: "docs/report.md", suggestions: [], comments: [whole, findings, passage, closing, rec] }, storeMtimeNs });
/** The status with the essay and the talked comment in the store too (the comment-fold test); `comments` and `verb` for
 *  the reply that answers a Resolve or Reopen there, the render a status drives. */
const withLong = (storeMtimeNs: string, comments: StoreComment[] = [whole, findings, passage, closing, essay, talked], verb = "status"): Status =>
  status({ verb, store: { v: 3, path: "docs/report.md", suggestions: [], comments }, storeMtimeNs });

// ── the viewer stand-in: the body row, the seam as closures, a measurement table ───────────────────
// Geometry: the body's box is at viewport y=100, BODY_VIEW tall; the header stands OFFSET tall above the track and the
// footer FOOTER tall below it, so the track's box is TRACK tall; row i's text sits at 100 + ROW·i − scrollTop; a card is
// CARD tall closed and OPEN tall open — except a card with a long part (the change card's old and new text; the essay's
// body and the talked comment's run of turns, in the comment-fold test), which is TALL open and folded (eight lines of the part)
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

// ── the audit's fixture: a deletion's point on row 7, whose card offers Reveal whatever the view paints ──────────────
const DEL = "chg:h2";
const DEL_AT = DOC.indexOf("More text here.") + "More text ".length;   // row 7: the session took a word out here
const del: Hunk = { id: "h2", author: "api", ts: T0 - 20000, kind: "del", curFrom: DEL_AT, curTo: DEL_AT, baseFrom: DEL_AT, baseTo: DEL_AT + 6, oldText: "right ", newText: "", anchor: null };
const withDel = (): Status => status({ hunks: [hunk, del] });
// the push chain under the change card: the passage's card (row 5, closed) is pushed under it, and the deletion's card (row 7)
// under that — 376 with the change card folded (TALL), 576 with it unfolded (WHOLE)
const CHAINED = desired(3) + TALL + 8 + CARD + 8;                  // 376
const UNDER = desired(3) + WHOLE + 8 + CARD + 8;                  // 576

// ── Reveal arms the focus ─────────────────────────────────────────────────────────────────────────

test("Reveal arms the focus: the deletion's card opened by its head, then the change card the focus from its mark and unfolded with Show more, the deletion's card pushed under it; Reveal on the deletion's card writes the focus before the switch to Raw, so the pass the switch runs lays the card level with its point, not pushed, and it stands there after (before: the pass kept the tall card as the focus and the revealed card stayed under it)", async (t) => {
  const w = textWorld();
  // the viewer's setMode: the body re-rendered synchronously and its onRendered pass run over it — what that pass laid is
  // read HERE, before reveal() goes on to the scroll, since the scroll reads the card where the pass put it
  const seen: Array<{ top: number | null; pushed: string | undefined }> = [];
  w.ctx.setMode = () => { w.repaint(); const c = w.card(DEL); seen.push({ top: w.top(DEL), pushed: c ? c.dataset.pushed : undefined }); };
  await open(t, w, withDel());
  assert.equal(w.top(DEL), desired(7), "the deletion's card is level with its point");
  headOf(w, DEL).click(); await tick();                // opened by its head (the audit's order): the focus for now, level with its point
  assert.ok(w.card(DEL)!.classList.contains("open"));
  assert.ok(actIn(w.card(DEL)!, "fcreveal"), "the deletion's card offers Reveal");
  assert.equal(w.top(DEL), desired(7));
  markOf(w, CHG).click(); await tick();                // the change card open from its mark: the focus now, TALL and folded
  assert.equal(w.top(DEL), CHAINED, "the deletion's card is pushed under the passage's card, itself pushed under the folded change card");
  actIn(w.card(CHG)!, "fcclip")!.click(); await tick();   // Show more: WHOLE, the focus still, the chain under it longer
  assert.equal(w.top(CHG), desired(3), "the unfolded change card is the focus, at its mark");
  assert.equal(w.top(DEL), UNDER, "the deletion's card is pushed further under the unfolded change card");
  assert.equal(w.card(DEL)!.dataset.pushed, "1");
  actIn(w.card(DEL)!, "fcreveal")!.click(); await tick();
  assert.equal(seen.length, 1, "Reveal switched the view once");
  assert.equal(seen[0].top, desired(7), "the pass the switch ran laid the revealed card level with its point (before: " + UNDER + ", under the tall card)");
  assert.equal(seen[0].pushed, undefined, "and not pushed");
  assert.equal(w.top(DEL), desired(7), "the card stands level after Reveal");
  assert.equal(w.card(DEL)!.dataset.pushed, undefined);
  // the tall card cannot fit above the focus (its top would be past the track's start): laid below it, by the reach rule
  assert.equal(w.top(CHG), desired(7) + OPEN + 8, "the unfolded change card is laid below the focus, not past the start");
  w.close();
});

// ── the fold to the list layout clears what the margin pass wrote ─────────────────────────────────

test("the fold to the list layout while a reply's box stands in a card clears what the margin pass wrote on the list and the kept card: no inline height on the list, no top, no leader (before: the rebuild grafted around the box and kept the live list and the card with the pass's height, top and leader, so the aside scrolled through empty space under the cards); the columns size and place them again", async (t) => {
  const { w } = await open(t, textWorld());
  headOf(w, passage.id).click(); await tick();          // the passage's card open by its head: the focus for now
  markOf(w, CHG).click(); await tick();                 // the change card the focus from its mark: the passage's card pushed under it
  assert.equal(w.top(passage.id), PUSHED, "the passage's card is pushed under the tall card");
  assert.equal(w.card(passage.id)!.dataset.pushed, "1");
  actIn(w.card(passage.id)!, "fcreply")!.click(); await tick();   // Reply: the box stands in the card (placeComposer), and Reply is no head click, so the focus stays
  const box = w.aside().querySelector(".fc-composer")!;
  assert.equal(box.hidden, false, "the composer is up");
  const list = w.list(), card = w.card(passage.id)!;
  assert.ok(card.contains(box), "the reply's box stands in the card");
  assert.match(String(list.style.height), /px$/, "the margin pass sized the list: " + list.style.height);
  assert.equal(card.style.top, PUSHED + "px");
  assert.equal(card.style.getPropertyValue("--fc-push"), (PUSHED - desired(5)) + "px", "the leader's length");
  narrow = true; resize(); flush();                     // the columns fold: the pass finds the list layout, layoutOff, then the render, which grafts around the box
  assert.ok(!w.aside().classList.contains("fc-margin"), "the list layout");
  assert.equal(w.list(), list, "the render kept the live list (the graft around the reply's box)");
  assert.equal(w.card(passage.id), card, "and the card the box stands in");
  assert.ok(card.contains(box), "the box still stands in it");
  assert.equal(list.style.height, "", "no inline height on the list in the list layout");
  assert.equal(card.style.top, "", "no inline top on the kept card");
  assert.equal(card.dataset.pushed, undefined, "no leader up");
  assert.equal(card.dataset.pulled, undefined, "no leader down");
  assert.equal(card.style.getPropertyValue("--fc-push"), "", "no leader length");
  assert.equal(card.style.getPropertyValue("--fc-pull"), "");
  narrow = false; resize(); flush();                    // the columns come back: the pass sizes the list and places the cards again, with no focus (the fold cleared it)
  assert.ok(w.aside().classList.contains("fc-margin"), "the margin layout is back");
  assert.match(String(w.list().style.height), /px$/, "the pass sized the list again");
  assert.equal(w.top(CHG), desired(3), "the push-down rule: the change card at its mark");
  assert.equal(w.top(passage.id), PUSHED, "the passage's card under it again");
  assert.equal(w.card(passage.id)!.dataset.pushed, "1");
  w.close();
});

test("at source: layoutOff clears the list's inline height and each child's top and leader after the focus and the pass's memory, in that order (the plan's pin holds the two clears adjacent)", () => {
  assert.ok(/private layoutOff\(\): void \{[\s\S]*?this\.focusCard = null;[^\n]*\n\s*this\.laidOn = null;[\s\S]*?list\.style\.height = "";[\s\S]*?node\.style\.top = ""; delete node\.dataset\.pushed; delete node\.dataset\.pulled;\n\s*node\.style\.removeProperty\("--fc-push"\); node\.style\.removeProperty\("--fc-pull"\);/.test(SRC), "layoutOff: the list's height, then each child's top, leaders and their lengths");
});

test("at source: reveal() switches through one place that writes the focus in the margin layout before setMode, on the change branch and the comment's, and runs the pass itself where the switch ran none, read from the placement (the review of the audit's fixes, round 2: the guard on laidOn ran the margin twice for a change card's Reveal with the marks off)", () => {
  assert.ok(/private revealInRaw\(key: string\): void \{\n\s*if \(this\.margin\) this\.focusCard = key;[^\n]*\n\s*const placed = this\.placed;[^\n]*\n\s*this\.ctx\.setMode\("raw"\);\n\s*if \(this\.margin && this\.placed === placed\) this\.placeCards\(false\);/.test(SRC), "the focus, the placement read, the switch, then the pass where the switch wrote no new placement");
  assert.doesNotMatch(SRC.split("private revealInRaw(key: string): void {")[1].split("\n  }\n")[0], /laidOn !== key/, "the guard on the pass's memory is gone: it ran a pass wherever the last one had not laid the cards on the card");
  assert.equal((SRC.match(/this\.revealInRaw\(key\);/g) || []).length, 2, "both branches of reveal() switch through it");
});

test("vocabulary: this module's own prose says a change's old and new text, file comment and run of turns; the words CONTEXT.md sets aside — the short word for a change's text (Change: Avoid) and the one for a forked side session (File comment: Avoid) — appear nowhere in it, nor the banned sessions-pane word, nor a home path", () => {
  const SELF = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "file-comments-focus-audit.test.ts"), "utf8").split("\n").filter((l) => !l.includes("assert.doesNotMatch(SELF")).join("\n");
  assert.doesNotMatch(SELF, /\bdiffs?\b/i, "the folded part of a change card is the change's old and new text (CONTEXT.md, Change: Avoid)");
  assert.doesNotMatch(SELF, /\bthreads?\b/i, "a comment with replies is a file comment with a run of turns (CONTEXT.md, File comment: Avoid)");
  assert.doesNotMatch(SELF, /fleet/i, "no new identifiers or prose in the old word for the sessions pane");
  assert.doesNotMatch(SELF, /\/home\/[a-z]/, "no absolute home paths");
});

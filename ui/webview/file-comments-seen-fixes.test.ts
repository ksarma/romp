// The seen follow-on's review fixes (plans/file-review.md, decisions 41 and 43, "The seen follow-on (2026-09-09)" under
// Slice 2; the review of 2026-09-09), driven over the stand-in file-comments-arrivals-fixes.test.ts drives (copied here, as
// the sibling modules copy it: a press carries a button, so the row's hold arms; the panel's own box and the cards in flow
// are measured for the list layout), with one more thing measured: the composer's box in the list layout's flow, above the
// cards while it is up. What the fixes pin: the send accepts what the confirm SHOWED — the press that sends is a gesture
// that marks the card the last wheel scrolled in seen, and before this the send read the live set after that mark, so it
// accepted a change while the box read disabled and unchecked with "nothing is accepted until you look"; the confirm's count
// row follows a gesture with the option's words; a wheel over the saved line ends it, a press or a touch move on it does not;
// the list layout re-reads the line's side at the aside's scroll, at a render, and once more after the composer's close
// lifted the cards; the line stands under the header in the list layout, where the person who saved is looking, and in the
// Send section in the margin layout; the panel's close ends the line; doSend's contract names no accept-all. Synthetic
// fixtures only: the notes-api world, placeholder ids, the session names "api" and "web".
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inspect } from "node:util";
import { hideEdges, staysEnumerable } from "../test-dom-shim";
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
  button: number;                                     // a press's button, 0 the primary as a pointer event defaults it: pressHold arms on that one alone
  constructor(public type: string, init: { key?: string; ctrlKey?: boolean; metaKey?: boolean; button?: number } = {}) { this.key = init.key || ""; this.ctrlKey = !!init.ctrlKey; this.metaKey = !!init.metaKey; this.button = init.button === undefined ? 0 : init.button; hideEdges(this); }
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
  constructor(tag: string) {
    this.tagName = tag.toUpperCase();
    // the tree's edges are non-enumerable, so a node inspects as its own projection and a failing assertion's dump
    // stays small (ui/test-dom-shim.ts says why); assignments later keep them hidden
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
  /** As the browser has it: a tabindex attribute, else 0 for a button, an input or a textarea, else -1 (not focusable). */
  get tabIndex(): number { return this.attrs.has("tabindex") ? Number(this.attrs.get("tabindex")) : (this.tagName === "BUTTON" || this.tagName === "INPUT" || this.tagName === "TEXTAREA" ? 0 : -1); }
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
// the list layout's geometry (narrow): the aside's box at LIST_TOP, LIST_VIEW tall, holding three closed cards; `listScroll` is
// how far the person scrolled it (the table moves the cards up by it); `noteContent` is the note box's scroll height
const LIST_TOP = 360, LIST_VIEW = 120;
let listScroll = 0;
// the composer's box in the list layout's flow: in the panel's slot before the cards (placeComposer) while it is up, BOX tall,
// so the cards stand that much lower until it closes (a hidden box takes no room: .fc-composer[hidden] is display none). A
// reply's box stands inside its card and is not counted, as the sibling's table does not count it.
const BOX = 100;
const boxAbove = (w: World): number => { const box = w.aside().querySelector(".fc-composer"); return box && !box.hidden && box.parentNode === w.aside() ? BOX : 0; };
let noteContent = 0;
type World = {
  ctx: FileViewActionCtx; posted: any[]; main: El; body: El; code: El;
  hooks: { rendered: Array<() => void>; close: Array<() => void>; saved: Array<(info: { mtimeNs: string; logged: boolean }) => void> };
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
    posted: [] as any[], main, body, code, hooks: { rendered: [] as Array<() => void>, close: [] as Array<() => void>, saved: [] as Array<(info: { mtimeNs: string; logged: boolean }) => void> }, editing: false,
    viewMtime: "1757145600000000001", content: ROW * ROWS,
  } as World;
  rows(code, DOC);
  const pad = (): number => parseFloat((body.style.paddingBottom as string) || "0") || 0;
  w.scrollHeightOf = (el) => {
    if (el === body) return Math.max(w.content + pad(), BODY_VIEW);
    if (el.classList.contains("fc-send-note")) return noteContent;   // the note box's content, as the test sets it
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
  const cardHeight = (el: El): number => {
    const open = el.classList.contains("open");
    return !open ? CARD : el.querySelectorAll(".fc-clip").some(isLongPart) ? (el.classList.contains("fc-more") ? WHOLE : TALL) : OPEN;
  };
  w.measure = (el: El): Rect => {
    if (el === body) return R(0, 100, 400, BODY_VIEW);
    if (el.classList.contains("fc-panel")) return R(0, LIST_TOP, 400, LIST_VIEW);   // the aside: under the body in the narrow column (the list layout reads its box)
    if (el.classList.contains("fc-sec-cards")) return R(400, 100 + OFFSET, 340, TRACK);
    if (el.classList.contains("fc-card")) {
      if (narrow) {   // the list layout: the cards in flow, one under the other from the aside's top, less the aside's scroll — under the composer's box while it stands in the slot (boxAbove)
        let y = boxAbove(w);
        for (const c of w.aside().querySelectorAll(".fc-card")) { if (c === el) break; y += cardHeight(c); }
        return R(0, LIST_TOP + y - listScroll, 400, cardHeight(el));
      }
      return R(412, 0, 316, cardHeight(el));
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
    onRendered: (cb) => { w.hooks.rendered.push(cb); }, onSelection: noop, onSaved: (cb) => { w.hooks.saved.push(cb); }, onClose: (cb) => { w.hooks.close.push(cb); },
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
  frames.length = 0; RO.all.length = 0; IO.all.length = 0; scrolledInto.length = 0; doc.activeElement = doc.body; listScroll = 0; noteContent = 0;   // `narrow` is the test's: set before open
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

// ── the session's answer: what arrives while the person reads ─────────────────────────────────────
const apiReply = (c: StoreComment, ts: number, body: string): StoreComment => ({ ...c, replies: [...(c.replies || []), { author: "api", authorId: SID, ts, body }] });
const findingsR = apiReply(findings, T0 + 20000, "Findings first: the methods are in the appendix.");   // row 2
const passageR = apiReply(passage, T0 + 21000, "The query cache; the sentence now says so.");           // row 5
const line9: StoreComment = {   // row 9: a comment of the session's own
  id: (T0 + 30000) + "-3", author: "api", authorId: SID, ts: T0 + 30000, body: "Is this line still the plan?",
  anchor: { quote: "Line 9 of the report", prefix: "", suffix: "." }, replies: [], resolved: false,
};
const mine2: StoreComment = {   // row 11: the person's own comment, saved from another tab meanwhile — never an arrival
  id: (T0 + 32000) + "-4", author: "you", ts: T0 + 32000, body: "Cite the run.",
  anchor: { quote: "Line 11 of the report", prefix: "", suffix: "." }, replies: [], resolved: false,
};
const MORE = "More text here.";
const MORE_AT = DOC.indexOf(MORE);
const hunk2: Hunk = { id: "h2", author: "api", ts: T0 + 31000, kind: "ins", curFrom: MORE_AT, curTo: MORE_AT + MORE.length, baseFrom: MORE_AT, baseTo: MORE_AT, oldText: "", newText: MORE, anchor: null };   // row 7
const CHG2 = "chg:h2";
/** The status the session's answer lands in: two replies, a comment and a change of the session's, and a comment of the person's. */
const arrived = (over: Partial<Status> = {}): Status => status({
  verb: "resolve", store: { v: 3, path: "docs/report.md", suggestions: [], comments: [whole, findingsR, passageR, closing, line9, mine2] },
  hunks: [hunk, hunk2], storeMtimeNs: "1757145600000000004", ...over,
});
const lineOf = (w: World): El | null => actIn(w.aside(), "fcarrivals");
const isNew = (el: El | null | undefined): boolean => !!el && el.dataset.new === "1";
/** A gesture of the person's, as the stand-in can make it: the event dispatched on an element in the body row. */
const gesture = (el: El, type: string): void => { el.dispatchEvent(new Ev(type)); };
const scrollBody = (w: World, to: number): void => { w.body.scrollTop = to; w.body.dispatchEvent(new Ev("scroll")); };
/** The session's answer landing: the panel re-asks status the way the viewer's onSaved makes it (no gesture, nothing in the
 *  layout touched), and the answer is the status with the session's entries. */
async function land(w: World, ok: (s: Status) => Promise<void>, s: Status): Promise<void> {
  for (const cb of w.hooks.saved) cb({ mtimeNs: w.viewMtime, logged: true });
  await tick();
  await ok({ ...s, verb: "status" });
}
const ARRIVED = "api made 1 change, 1 comment and 2 replies since you last looked";

/** The press's release, as the browser ends it: a pointerup at the window (pressHold's release target), then the zero timer
 *  the hold runs the parked change on (after the click, which dispatches synchronously with the release). */
const release = async (): Promise<void> => { win.dispatchEvent(new Event("pointerup")); await new Promise<void>((r) => setTimeout(r, 0)); await tick(); };
const acceptLabel = (w: World): string | null => { const cb = w.aside().querySelector('input[data-opt="accept"]'); return cb ? cb.parentNode!.textContent : null; };
const noteBox = (w: World): El => w.aside().querySelector(".fc-confirm .fc-send-note")!;
const typeNote = (w: World, text: string, content = 0): void => { const b = noteBox(w); b.value = text; noteContent = content; b.dispatchEvent(new Ev("input")); };
const NO_UNSENT = { comments: [], replies: [], accepted: 0, rejected: 0, watermark: null };
const lastOf = (w: World, type: string): Posted | undefined => w.posted.slice().reverse().find((m) => m.type === type);
const filterButton = (w: World, key: string): El => w.aside().querySelectorAll('[data-act="fcfilter"]').find((b) => b.dataset.key === key)!;
// ── the fixtures of the seen-only accept (file-comments-send-seen.test.ts, copied) ─────────────────
// A second change the first status holds (row 11), seen with everything in it; the row-7 change (hunk2) lands later as an
// arrival whose card stands below the track's box while the text is at its top — unseen until a gesture finds it in view
const L11 = "Line 11 of the report.";
const L11_AT = DOC.indexOf(L11);
const hunkB: Hunk = { id: "hb", author: "api", ts: T0 - 25000, kind: "ins", curFrom: L11_AT, curTo: L11_AT + L11.length, baseFrom: L11_AT, baseTo: L11_AT, oldText: "", newText: L11, anchor: null };
const L13 = "Line 13 of the report.";
const L13_AT = DOC.indexOf(L13);
const hunkC: Hunk = { id: "hc", author: "api", ts: T0 + 33000, kind: "ins", curFrom: L13_AT, curTo: L13_AT + L13.length, baseFrom: L13_AT, baseTo: L13_AT, oldText: "", newText: L13, anchor: null };
const sug = (...hs: Hunk[]) => hs.map((h) => ({ id: h.id, authorId: SID }));
const COMMENTS = [whole, findings, passage, closing];
/** The panel's first status: two pending changes, both seen with it. */
const twoSeen = (over: Partial<Status> = {}): Status => status({ store: { v: 3, path: "docs/report.md", suggestions: sug(hunk, hunkB), comments: COMMENTS }, hunks: [hunk, hunkB], ...over });
/** The session's third change landing while the person reads: an arrival, its card below the box. */
const oneUnseen = (over: Partial<Status> = {}): Status => status({ store: { v: 3, path: "docs/report.md", suggestions: sug(hunk, hunkB, hunk2), comments: COMMENTS }, hunks: [hunk, hunkB, hunk2], storeMtimeNs: "1757145600000000004", ...over });
/** After the accept of the two seen changes: the third still pending, the decisions unsent. */
const afterAccept = (): Status => status({ store: { v: 3, path: "docs/report.md", suggestions: sug(hunk2), comments: COMMENTS }, hunks: [hunk2], storeMtimeNs: "1757145600000000005",
  unsent: { comments: [passage.id], replies: [], accepted: 2, rejected: 0, watermark: null } });
/** A first status with nothing pending, and the session's two changes landing after it: all unseen. */
const nonePending = (): Status => status({ store: { v: 3, path: "docs/report.md", suggestions: [], comments: COMMENTS }, hunks: [] });
const twoUnseen = (): Status => status({ store: { v: 3, path: "docs/report.md", suggestions: sug(hunk2, hunkC), comments: COMMENTS }, hunks: [hunk2, hunkC], storeMtimeNs: "1757145600000000004" });
const acceptBox = (w: World): El => w.aside().querySelector('input[data-opt="accept"]')!;
const acceptWords = (w: World): string => acceptBox(w).parentNode!.textContent;
const verbs = (w: World): string[] => w.posted.filter((m) => m.type === "fileComments").map((m) => m.verb);
const sentOk = async (w: World): Promise<void> => {
  const m = w.posted[w.posted.length - 1];
  assert.equal(m.type, "fileCommentsSend", "a send is outstanding");
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsSent", reqId: m.reqId, queued: false } }));
  await tick(); await tick();
};
const sendButton = (w: World): El => actIn(w.aside(), "fcsendgo")!;
/** The confirm's count row, as the list shows it: the "A accepted, R rejected" items (one at most). */
const countRows = (w: World): string[] => w.aside().querySelectorAll(".fc-confirm li").map((li) => li.textContent).filter((x) => /accepted/.test(x));
const ALL_UNSEEN = "accept the pending changes you have seen (all 2 pending changes are unseen; nothing is accepted until you look)";
/** The Send pressed as a pointer presses it: a primary pointerdown on the button (the row's hold arms first, then the
 *  gesture marks what is on screen seen and parks the option's rewrite under the hold), the pointerup at the window, then the
 *  click — which the browser dispatches with the release, BEFORE the hold's zero timer runs the parked change. */
async function pressSend(w: World): Promise<void> {
  const b = sendButton(w);
  b.dispatchEvent(new Ev("pointerdown", { button: 0 }));
  win.dispatchEvent(new Event("pointerup"));
  b.click(); await tick();
  await new Promise<void>((r) => setTimeout(r, 0)); await tick();   // the hold's parked change runs now, against whatever the send left
}
/** Every pending change unseen, the confirm up with its box off, and the card of the row-7 change scrolled into the track's box
 *  by the last wheel: on screen, seen by no gesture yet — the state the press finds. */
async function unseenInView(t: Ctx): Promise<{ w: World; ok: (s?: Status) => Promise<void>; last: () => Posted }> {
  const { w, ok, last } = await open(t, textWorld(), nonePending());
  await land(w, ok, twoUnseen());
  actIn(w.aside(), "fcsend")!.click();
  assert.equal(acceptBox(w).disabled, true, "the fixture: nothing seen, the box is off");
  gesture(w.body, "wheel"); scrollBody(w, 340);          // the wheel, then the scroll it starts: row 7's card is in the box [340, 500) now, seen by no gesture
  assert.equal(acceptWords(w), ALL_UNSEEN, "the fixture: the words at the press");
  assert.equal(acceptBox(w).disabled, true); assert.equal(acceptBox(w).checked, false);
  assert.deepEqual(countRows(w), [], "and no count row");
  assert.ok(isNew(w.card(CHG2)), "the fixture: the card on screen is an arrival still");
  return { w, ok, last };
}

// ── the send accepts what the confirm showed ──────────────────────────────────────────────────────

test("the disabled box binds the send: the card the last wheel scrolled in is on screen at the Send press — the press marks it seen, the option keeps its words through the hold, and the send accepts nothing, as the box said (before: the send read the seen set after the press's own mark and accepted the change while the box read disabled and unchecked); the next confirm counts it seen", async (t) => {
  const { w, ok, last } = await unseenInView(t);
  const before = verbs(w).length;
  const b = sendButton(w);
  b.dispatchEvent(new Ev("pointerdown", { button: 0 }));   // the press: a gesture — the card on screen is seen, the option's rewrite parked under the hold
  assert.ok(!isNew(w.card(CHG2)), "seen by the press");
  assert.equal(acceptWords(w), ALL_UNSEEN, "the words the person read stand through the press");
  assert.equal(acceptBox(w).disabled, true);
  win.dispatchEvent(new Event("pointerup"));
  b.click(); await tick();
  assert.equal(verbs(w).length, before, "no accept: the box said nothing is accepted");
  assert.equal(last().type, "fileCommentsSend");
  assert.equal(last().accepted, 0);
  await new Promise<void>((r) => setTimeout(r, 0)); await tick();   // the hold's parked change: the confirm is down, nothing to write
  await sentOk(w);
  await ok(twoUnseen());
  assert.ok(w.card(CHG2) && w.card("chg:hc"), "both changes still pending");
  assert.ok(!isNew(w.card(CHG2)) && isNew(w.card("chg:hc")), "the one the press saw is seen; the other is not");
  actIn(w.aside(), "fcsend")!.click();
  assert.equal(acceptWords(w), "accept the 1 pending change you have seen (1 unseen stays pending)", "the next confirm counts it");
  assert.equal(acceptBox(w).checked, true, "checked: the default was kept while the box was off");
  assert.deepEqual(countRows(w), ["1 accepted, 0 rejected"]);
  w.close();
});

test("the chord in the note box: the key that sends is the send's own press — it marks the card on screen seen and leaves the option as read, and the send accepts nothing, as the box said", async (t) => {
  const { w, last } = await unseenInView(t);
  const before = verbs(w).length;
  noteBox(w).dispatchEvent(new Ev("keydown", { key: "Enter", ctrlKey: true })); await tick();
  assert.ok(!isNew(w.card(CHG2)), "seen by the key");
  assert.equal(verbs(w).length, before, "no accept");
  assert.equal(last().type, "fileCommentsSend");
  assert.equal(last().accepted, 0);
  await sentOk(w);
  w.close();
});

test("a click with no press before it (a synthesized activation): the send's own gesture leaves the option as read too, and the send accepts nothing", async (t) => {
  const { w, last } = await unseenInView(t);
  const before = verbs(w).length;
  sendButton(w).click(); await tick();
  assert.ok(!isNew(w.card(CHG2)), "seen by the send's gesture");
  assert.equal(verbs(w).length, before, "no accept");
  assert.equal(last().type, "fileCommentsSend");
  assert.equal(last().accepted, 0);
  await sentOk(w);
  w.close();
});

test("the checked box binds the send the same way: two seen and a third the last wheel scrolled in — the confirm lists two, the press marks the third seen, and the send accepts the two the list named (before: all three)", async (t) => {
  const { w, ok, last } = await open(t, textWorld(), twoSeen());
  await land(w, ok, oneUnseen());
  actIn(w.aside(), "fcsend")!.click();
  gesture(w.body, "wheel"); scrollBody(w, 340);          // row 7's card in the box, seen by no gesture yet
  assert.equal(acceptWords(w), "accept the 2 pending changes you have seen (1 unseen stays pending)", "the fixture: the words at the press");
  assert.deepEqual(countRows(w), ["2 accepted, 0 rejected"], "the list at the press");
  await pressSend(w);
  const acc = w.posted.filter((m) => m.type === "fileComments" && m.verb === "accept").pop()!;
  assert.deepEqual(acc.args, { ids: ["h1", "hb"] }, "the two the list named, not the one the press marked seen");
  await ok({ ...afterAccept(), accepted: ["h1", "hb"] } as unknown as Status);
  assert.equal(last().type, "fileCommentsSend");
  assert.equal(last().accepted, 2, "the message says what the confirm said");
  await sentOk(w);
  await ok(afterAccept());
  assert.ok(w.card(CHG2), "the third is still pending");
  assert.ok(!isNew(w.card(CHG2)), "and seen: the press found it on screen");
  w.close();
});

test("a gesture the person could read lands: a wheel while the confirm is up moves the change to the seen side in the words, the count row and the send alike — three listed, three accepted", async (t) => {
  const { w, ok } = await open(t, textWorld(), twoSeen());
  await land(w, ok, oneUnseen());
  actIn(w.aside(), "fcsend")!.click();
  scrollBody(w, 340); gesture(w.body, "wheel");          // the card in the box, then the gesture that sees it
  assert.equal(acceptWords(w), "accept the 3 pending changes you have seen");
  assert.deepEqual(countRows(w), ["3 accepted, 0 rejected"], "the row follows in place (before: still 2 accepted)");
  await pressSend(w);
  const acc = w.posted.filter((m) => m.type === "fileComments" && m.verb === "accept").pop()!;
  assert.deepEqual(acc.args, { ids: ["h1", "hb", "h2"] });
  w.close();
});

// ── the confirm's count row follows a gesture ─────────────────────────────────────────────────────

test("from nothing seen: the first change a gesture brings into view turns the box on AND writes the count row that was not there; under a press the row waits for the release with the words", async (t) => {
  const { w, ok } = await open(t, textWorld(), nonePending());
  await land(w, ok, twoUnseen());
  actIn(w.aside(), "fcsend")!.click();
  assert.deepEqual(countRows(w), [], "nothing to state: no row");
  scrollBody(w, 340);                                   // row 7's card in the box [340, 500); row 13's is not
  w.body.dispatchEvent(new Ev("pointerdown", { button: 0 }));   // a press in the text: seen, the lines parked
  assert.ok(!isNew(w.card(CHG2)), "seen at the press");
  assert.equal(acceptWords(w), ALL_UNSEEN, "the words wait for the release (the hold)");
  assert.deepEqual(countRows(w), [], "and so does the row");
  await release();
  assert.equal(acceptWords(w), "accept the 1 pending change you have seen (1 unseen stays pending)");
  assert.equal(acceptBox(w).disabled, false);
  assert.deepEqual(countRows(w), ["1 accepted, 0 rejected"], "the row appeared with the words");
  assert.equal(w.aside().querySelectorAll(".fc-confirm li.fc-counts").length, 1, "one row");
  actIn(w.aside(), "fcsendcancel")!.click();
  actIn(w.aside(), "fcsend")!.click();
  assert.deepEqual(countRows(w), ["1 accepted, 0 rejected"], "the re-render agrees");
  w.close();
});

test("the row goes with the box: unchecked, the re-render drops it; the in-place path writes none while the box is unchecked", async (t) => {
  const { w, ok } = await open(t, textWorld(), twoSeen());
  await land(w, ok, oneUnseen());
  actIn(w.aside(), "fcsend")!.click();
  const cb = acceptBox(w);
  cb.checked = false; dispatch(cb, new Ev("change"));
  assert.deepEqual(countRows(w), [], "unchecked: no decisions to state");
  scrollBody(w, 340); gesture(w.body, "wheel");
  assert.equal(acceptWords(w), "accept the 3 pending changes you have seen", "the words follow");
  assert.equal(acceptBox(w).checked, false, "their choice stands");
  assert.deepEqual(countRows(w), [], "no row: the box is off");
  w.close();
});

// ── the saved line (decision 43): the gestures that end it, and the list layout ───────────────────
/** The focus-verify module's scene (file-comments-arrivals.test.ts saveReply): the change card open as the focus with the
 *  passage's card pushed under it, a reply typed in the passage's card, the text at its top. */
async function saveReply(t: Ctx): Promise<{ w: World; body: El; track: El; ok: (s?: Status) => Promise<void>; button: El }> {
  const { w, ok, last, button } = await open(t, textWorld());
  const body = w.body, track = w.track();
  markOf(w, CHG).click(); await tick();
  headOf(w, passage.id).click(); await tick();
  markOf(w, CHG).click(); await tick();
  assert.equal(w.top(passage.id), PUSHED, "the fixture: the passage's card is open, not the focus, pushed under the tall card");
  actIn(w.card(passage.id)!, "fcreply")!.click(); await tick();
  scrollBody(w, 0);
  const input = w.aside().querySelector(".fc-composer .fc-input")!;
  input.value = "The write-through one.";
  input.dispatchEvent(new Ev("keydown", { key: "Enter", ctrlKey: true }));
  await tick();
  assert.equal(last().verb, "reply");
  await ok(status({ verb: "reply", store: { v: 3, path: "docs/report.md", suggestions: [], comments: [whole, findings, replied, closing] }, storeMtimeNs: "1757145600000000005" }));
  return { w, body, track, ok, button };
}
const replied: StoreComment = { ...passage, replies: [{ author: "you", ts: T0 + 6000, body: "The write-through one." }] };
const SHOW_CARD = desired(5) + OPEN + 8 - TRACK;        // 208: the least scroll that shows the saved card's end (what the line's click scrolls to)
const savedOf = (w: World): El | null => actIn(w.aside(), "fcsavedgo");

test("a wheel over the saved line ends it: a wheel is the scroll the line says it goes with, not a press; a press or a touch move on the line keeps it, and the click after a touch move still shows the card", async (t) => {
  let { w, body } = await saveReply(t);
  assert.equal(savedOf(w)!.textContent, "Saved · the card is below");
  gesture(savedOf(w)!, "pointerdown");                  // a primary press on the line: the row's hold arms
  assert.equal(savedOf(w)!.textContent, "Saved · the card is below", "a press on the line keeps it");
  await release();                                      // the release: the parked re-read finds the card below still
  assert.equal(savedOf(w)!.textContent, "Saved · the card is below", "and it stands after the release");
  gesture(savedOf(w)!, "touchmove");
  assert.equal(savedOf(w)!.textContent, "Saved · the card is below", "a touch move on it too: a jittery tap moves");
  savedOf(w)!.click(); await tick();
  assert.equal(body.scrollTop, SHOW_CARD, "the click after the touch move: the card into view");
  assert.equal(savedOf(w), null, "and the line is over");
  w.close();
  ({ w, body } = await saveReply(t));
  assert.equal(savedOf(w)!.textContent, "Saved · the card is below");
  gesture(savedOf(w)!, "wheel");
  assert.equal(savedOf(w), null, "a wheel over the line ends it (before: the line stood, as at a press)");
  assert.equal(body.scrollTop, 0, "the line's end scrolls nothing");
  w.close();
});

test("the panel's close ends the line: closed and reopened, a status landing shows the list afresh, with no line about the save made before the close", async (t) => {
  const { w, ok, button } = await saveReply(t);
  assert.equal(savedOf(w)!.textContent, "Saved · the card is below");
  button.click();                                       // close: the aside goes
  assert.equal(w.main.querySelector(".fileview-aside"), null);
  button.click();                                       // reopen: the panel re-asks status
  await ok(status({ store: { v: 3, path: "docs/report.md", suggestions: [], comments: [whole, findings, replied, closing] }, storeMtimeNs: "1757145600000000005" }));
  assert.ok(w.card(passage.id), "the fixture: the card is in the reopened list");
  assert.equal(savedOf(w), null, "no line: the save was before the close (closePanel clears the latch)");
  w.close();
});

const storeWith = (comments: StoreComment[], detached: unknown[] = []) => ({ v: 3, path: "docs/report.md", suggestions: [], comments, ...(detached.length ? { detached } : {}) });
async function saveReplyInList(t: Ctx, scrolled: number): Promise<{ w: World; ok: (s?: Status) => Promise<void> }> {
  narrow = true;
  const w = textWorld();
  const { ok, last } = await open(t, w);
  headOf(w, passage.id).click(); await tick();          // the passage's card open: the fourth card, 120 tall
  actIn(w.card(passage.id)!, "fcreply")!.click(); await tick();
  listScroll = scrolled;
  const input = w.aside().querySelector(".fc-composer .fc-input")!;
  input.value = "The write-through one.";
  input.dispatchEvent(new Ev("keydown", { key: "Enter", ctrlKey: true })); await tick();
  assert.equal(last().verb, "reply");
  scrolledInto.length = 0;                              // the composer's opening scrolled its box and the mark into view: what follows is the save's
  await ok(status({ verb: "reply", store: storeWith([whole, findings, replied, closing]), storeMtimeNs: "1757145600000000005" }));
  return { w, ok };
}
const cardsScrolledInto = (): string[] => scrolledInto.filter((c) => c.classList.contains("fc-card")).map((c) => c.dataset.id);
const asideScroll = (w: World, to: number): void => { listScroll = to; w.aside().dispatchEvent(new Ev("scroll")); };

test("the list layout: the aside's scroll re-reads the line's side — the words follow the card against the aside's box, and the line ends when the card comes whole into it (before: nothing re-read a scroll there, and the words stood stale until the next gesture)", async (t) => {
  try {
    const { w } = await saveReplyInList(t, 0);          // three closed cards fill the box [360, 480): the open passage card is 480..600
    assert.equal(savedOf(w)!.textContent, "Saved · the card is below");
    asideScroll(w, 60);                                   // 420..540: its top in the box, its end past it
    assert.equal(savedOf(w)!.textContent, "Saved · the card is below", "not whole in the box yet");
    asideScroll(w, 200);                                  // 280..400: past the box's top
    assert.equal(savedOf(w)!.textContent, "Saved · the card is above", "the words follow the side, in place");
    asideScroll(w, 120);                                  // 360..480: whole in the box
    assert.equal(savedOf(w), null, "the card came into view through the scroll: the line is over");
    assert.deepEqual(cardsScrolledInto(), [], "nothing scrolled by the panel");
    w.close();
  } finally { narrow = false; }
});

test("the list layout: a render that brings the saved card whole into the aside's box ends the line — the session's answer lands with no gesture and the cards above it are gone (afterRender's re-read; before: untested)", async (t) => {
  try {
    const { w, ok } = await saveReplyInList(t, 0);
    assert.equal(savedOf(w)!.textContent, "Saved · the card is below");
    w.viewMtime = "1757145600000000009";                  // a save of the file's own since: the viewer's onSaved re-asks (a mtime the panel's reply did not carry)
    await land(w, ok, status({ hunks: [], store: storeWith([replied]), storeMtimeNs: "1757145600000000006" }));
    const r = w.card(passage.id)!.getBoundingClientRect();
    assert.deepEqual([r.top, r.bottom], [LIST_TOP, LIST_TOP + LIST_VIEW], "the fixture: the card alone, open, fills the box");
    assert.equal(savedOf(w), null, "the card came into view through the render: the line is over");
    w.close();
  } finally { narrow = false; }
});

/** A whole-file comment saved in the list layout with the aside scrolled by `scrolled`: the composer's box in the slot above the
 *  cards while it is up (boxAbove), the fresh card the last in the list (the comments in the order of their timestamps). */
async function saveFileCommentInList(t: Ctx, scrolled: number): Promise<{ w: World; fresh: StoreComment; composer: El }> {
  narrow = true;
  const w = textWorld();
  const { ok, last } = await open(t, w);
  actIn(w.aside(), "fcfile")!.click();
  const composer = w.aside().querySelector(".fc-composer")!;
  assert.equal(composer.hidden, false, "the composer is up");
  assert.equal(composer.parentNode, w.aside(), "in the panel's slot, above the cards");
  listScroll = scrolled;
  const input = composer.querySelector(".fc-input")!;
  input.value = "Add the run's date.";
  input.dispatchEvent(new Ev("keydown", { key: "Enter", ctrlKey: true })); await tick();
  assert.equal(last().verb, "comment");
  scrolledInto.length = 0;
  const fresh: StoreComment = { id: (T0 + 50000) + "-0", author: "you", ts: T0 + 50000, body: "Add the run's date.", replies: [], resolved: false };
  await ok(status({ verb: "comment", store: storeWith([whole, findings, passage, closing, fresh]), storeMtimeNs: "1757145600000000005" }));
  return { w, fresh, composer };
}

test("the list layout: the fresh card lands in the aside's box while the composer's box still stands above the cards, and the box's close lifts it above the box — the side is read once more after the close, and the line says the card is above (before: no line, and nothing re-read after the close)", async (t) => {
  try {
    const { w, fresh, composer } = await saveFileCommentInList(t, 250);
    assert.equal(composer.hidden, true, "the composer closed");
    const r = w.card(fresh.id)!.getBoundingClientRect();
    assert.deepEqual([r.top, r.bottom], [LIST_TOP - 50, LIST_TOP - 10], "the fixture: the sixth card in flow (200 down), lifted by the box's " + BOX + " at the close, stands above the box: with the box it read " + (LIST_TOP + 50) + ".." + (LIST_TOP + 90) + ", whole in it");
    const line = savedOf(w);
    assert.ok(line, "the line is in the panel");
    assert.equal(line!.textContent, "Saved · the card is above");
    assert.deepEqual(cardsScrolledInto(), [], "nothing scrolled (decision 43)");
    line!.click(); await tick();
    assert.deepEqual(cardsScrolledInto(), [fresh.id], "the click: the card into view");
    assert.equal(savedOf(w), null);
    w.close();
  } finally { narrow = false; }
});

test("the list layout: the line stands under the header, where the composer was, not in the Send section at the scroller's foot below the very card it points at; its click works from there", async (t) => {
  try {
    const { w, fresh } = await saveFileCommentInList(t, 0);
    const r = w.card(fresh.id)!.getBoundingClientRect();
    assert.ok(r.top >= LIST_TOP + LIST_VIEW, "the fixture: the fresh card is below the box: " + r.top);
    const line = savedOf(w);
    assert.ok(line, "the line is in the panel");
    assert.equal(line!.textContent, "Saved · the card is below");
    assert.ok(w.aside().querySelector(".fc-sec-head")!.contains(line!), "under the header");
    assert.ok(!w.aside().querySelector(".fc-sec-send")!.contains(line!), "not at the foot (before: there, below every card)");
    const order = w.aside().querySelectorAll("div, button");   // the scroller's flow, in document order
    assert.ok(order.indexOf(line!) >= 0 && order.indexOf(line!) < order.indexOf(w.aside().querySelector(".fc-card")!), "before the first card in the scroller's flow");
    assert.deepEqual(line!.classes, ["fc-note", "fc-sent", "fc-saved"], "in the same dress");
    assert.equal(w.aside().querySelectorAll('[data-act="fcsavedgo"]').length, 1, "the one line");
    line!.click(); await tick();
    assert.deepEqual(cardsScrolledInto(), [fresh.id]);
    assert.equal(savedOf(w), null, "and the line is over");
    w.close();
  } finally { narrow = false; }
});

test("the margin layout keeps the line in the Send section, the acknowledgment's position at the panel's foot", async (t) => {
  const { w } = await saveReply(t);
  const line = savedOf(w)!;
  assert.ok(w.aside().querySelector(".fc-sec-send")!.contains(line), "in the Send section");
  assert.ok(!w.aside().querySelector(".fc-sec-head")!.contains(line));
  w.close();
});

// ── at source ─────────────────────────────────────────────────────────────────────────────────────
test("at source: the send reads the split over the seen set the confirm showed (confirmSeen), written by the render and by syncAcceptOption, and left alone by the send's own press (sendPress: doSend's gesture, the key that sends); the count row is written by both paths through countsRow", () => {
  const send = SRC.slice(SRC.indexOf("async doSend(): Promise<void> {"), SRC.indexOf("private async sendOnce("));
  assert.match(send, /this\.sendPress = true;\n\s*this\.gesture\(\);[^\n]*\n\s*this\.sendPress = false;/, "the send's gesture is the send's own press");
  assert.ok(send.includes("const acceptIds = this.sendOpts.accept ? this.pendingSplit(s).seen.map((h) => String(h.id)) : [];"));
  const split = SRC.slice(SRC.indexOf("private pendingSplit("), SRC.indexOf("private acceptOption("));
  assert.ok(split.includes("return partitionPending(s.hunks || [], this.confirmSeen || this.seenKeys);"), "the split over the confirm's set while one is up");
  const sync = SRC.slice(SRC.indexOf("private syncAcceptOption("), SRC.indexOf("private countsRow("));
  assert.match(sync, /if \(this\.sendPress\) return;\n\s*this\.confirmSeen = new Set\(this\.seenKeys \|\| \[\]\);\n\s*const split = this\.pendingSplit\(s\);/, "the in-place write refreshes the set first, and the send's press writes nothing");
  assert.ok(sync.includes("if (ul) this.countsRow(ul, sendCounts(sendParts(s), this.sendOpts.accept, split.seen.length));"), "the count row with the option, from the same split");
  assert.ok(SRC.includes("this.confirmSeen = this.sendConfirm && s && !this.sending ? new Set(this.seenKeys || []) : null;"), "the render's set, none with no confirm");
  assert.match(SRC, /const counts = sendCounts\(parts, this\.sendOpts\.accept, split\.seen\.length\);[\s\S]*?this\.countsRow\(ul, counts\);/, "the render's row through the same writer, from the render's split");
  const counts = SRC.slice(SRC.indexOf("private countsRow("), SRC.indexOf("private todoOpts("));
  assert.ok(counts.includes('li.textContent = counts.accepted + " accepted, " + counts.rejected + " rejected";'));
  assert.ok(counts.includes("if (!counts.accepted && !counts.rejected) { if (li) li.remove(); return; }"), "no row with nothing to state");
  const gesture = SRC.slice(SRC.indexOf("gesture(ev?: Event): void {"), SRC.indexOf("private entryShown("));
  assert.ok(gesture.includes('const press = !!kb && ((on("fcsendgo") && (kb.key === "Enter" || kb.key === " ")) || (t === this.noteBox && composerKeyAction(kb) === "save"));'), "the key that sends");
  assert.ok(gesture.includes('&& (!ev || ev.type !== "wheel");'), "a wheel presses nothing: it ends the saved line");
  assert.ok(gesture.includes('const over = this.savedOut !== null && !on("fcsavedgo");'), "the latch's exemption stands for a press");
  assert.doesNotMatch(gesture, /setTimeout|setInterval|Date\.now/, "no timer");
});

test("at source: the list layout's re-reads — the aside's scroll, the render (afterRender) and the composer's close (landClosed) — and the line's place: the head in the list layout, the Send section in the margin layout; the close of the panel clears the latch", () => {
  assert.ok(SRC.includes('this.root.addEventListener("scroll", () => { if (this.savedOut && !this.margin) this.reflect(); }, { passive: true });'), "the aside's scroll");
  assert.ok(SRC.includes("if (this.savedOut && !this.margin) this.reflect();   // the list layout: the saved line follows the cards as this render laid them"), "afterRender's re-read");
  assert.match(SRC, /if \(hid \|\| \(lined && c\.kind !== "reply"\)\) this\.render\(\);[^\n]*\n\s*if \(r && !lined && !hid && !this\.margin\) this\.landClosed\(c, had, r, note\);/, "after the close, the list layout reads once more");
  const closed = SRC.slice(SRC.indexOf("private landClosed("), SRC.indexOf("// ── the arrivals (the arrivals follow-on"));
  assert.ok(closed.length > 0 && closed.length < 3000, "the slice is landClosed alone");
  assert.doesNotMatch(closed, /scrollCard|scrollBoth|scrollIntoView|scrollTop|centerOn|showLoose|setTimeout/, "no scroll, no timer: the side and the line only");
  assert.ok(closed.includes("this.savedOut = { key, side };"), "latched the way landSaved latches");
  assert.ok(!closed.includes("sentNote"), "the acknowledgment keeps its place in the list layout, whose line stands under the header and not in its position (the review, 2026-09-09)");
  assert.match(SRC, /const saved = this\.savedLineHead\(\);\n\s*if \(saved\) head\.appendChild\(saved\);\n\s*return head;/, "renderHead: the list layout's line, last in the head");
  assert.match(SRC, /private savedLine\(\): HTMLElement \| null \{\n\s*return this\.margin \? this\.savedButton\(\) : null;/, "renderSend's savedLine: the margin layout's");
  assert.match(SRC, /private savedLineHead\(\): HTMLElement \| null \{\n\s*return this\.margin \? null : this\.savedButton\(\);/, "the head's: the list layout's");
  assert.match(SRC, /const saved = this\.savedLine\(\);[^\n]*\n\s*if \(saved\) box\.appendChild\(saved\);/, "renderSend appends what savedLine gives");
  const close = SRC.slice(SRC.indexOf("  closePanel(): void {"), SRC.indexOf("this.stopPoll();", SRC.indexOf("  closePanel(): void {")));
  assert.ok(close.includes("this.savedOut = null;"), "the latch goes with the panel's close");
});

test("at source: doSend's contract and the comments around it name the by-id accept, never an accept-all from the send", () => {
  const doc = SRC.slice(SRC.indexOf("// ── Send to session"), SRC.indexOf("async doSend(): Promise<void> {"));
  assert.ok(doc.includes("never an accept-all"), "the docblock says what the send does not do");
  assert.doesNotMatch(doc, /then accept-all when asked|the accept-all just decided|which accept-all removes/, "the old sequence is gone from the contract");
  assert.ok(!SRC.includes("Send's accept-all"), "no comment names the send's decision by the retired verb");
});

test("vocabulary: this module's own prose says a change's old and new text, file comment and run of turns; the words CONTEXT.md sets aside appear nowhere in it, nor the banned sessions-pane word, nor a home path", () => {
  const SELF = web("file-comments-seen-fixes.test.ts").split("\n").filter((l) => !l.includes("assert.doesNotMatch(SELF")).join("\n");
  assert.doesNotMatch(SELF, /\bdiffs?\b/i, "the folded part of a change card is the change's old and new text (CONTEXT.md, Change: Avoid)");
  assert.doesNotMatch(SELF, /\bthreads?\b/i, "a comment with replies is a file comment with a run of turns (CONTEXT.md, File comment: Avoid)");
  assert.doesNotMatch(SELF, /fleet/i, "no new identifiers or prose in the old word for the sessions pane");
  assert.doesNotMatch(SELF, /\/home\/[a-z]/, "no absolute home paths");
});

// The stand-in's nodes inspect as their own projection, never as the tree: every edge (parentNode, childNodes, the
// attribute map, the listener table, style, dataset, classList) is non-enumerable, so a failing assertion's dump of a
// node is a few lines, not the whole document (ui/test-dom-shim.ts says why; ui/test-dom-shim.test.ts keeps the ratchet).
test("stand-in: a node enumerates its primitives alone and inspects without its edges", () => {
  const root = doc.createElement("div");
  const kid = root.appendChild(doc.createElement("span"));
  kid.appendChild(doc.createTextNode("leaf"));
  kid.setAttribute("data-id", "k1");
  for (const n of [root, kid, kid.firstChild!]) {
    const o = n as unknown as Record<string, unknown>;
    assert.ok(Object.keys(o).every((k) => staysEnumerable(o[k])), "only primitives enumerate on " + n.constructor.name + ": " + Object.keys(o).join(","));
    const dump = inspect(n, { compact: false, customInspect: false, depth: 1000, maxArrayLength: Infinity, showHidden: false, showProxy: false, sorted: true, getters: true });
    assert.ok(!dump.includes("parentNode") && !dump.includes("childNodes"), "no edge in the dump of " + n.constructor.name);
  }
  assert.equal(kid.parentNode, root); assert.equal(root.childNodes.length, 1); assert.equal(kid.textContent, "leaf");
});

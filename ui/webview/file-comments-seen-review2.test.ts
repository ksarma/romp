// The seen follow-on's second review round (plans/file-review.md, decisions 41 and 43, "The seen follow-on (2026-09-09)" under
// Slice 2; the review of 2026-09-09, round 2), driven over the stand-in file-comments-seen-fixes.test.ts drives (copied here,
// as the sibling modules copy it). What the round pins, behaviorally where the first round left source pins alone: Enter or
// Space on the confirm's Send is the send's own press, and the send accepts nothing the box did not say (before: held by a
// source pin alone); a key or a touch move after the landing ends the saved line, as the guide's sentence says; a Tab or a
// modifier pressed alone is no gesture, so the keyboard can reach the line, and the line's activation leaves the keyboard on
// the card it showed, not on the body; the margin layout's line sticks to the Send section's bottom edge, so it is on screen
// with the confirm up; the list layout's save leaves the send acknowledgment in place (the line stands under the header
// there); a send with the track box checked stands down on a seen change grown between the press and set-tracked's reply,
// as the no-track path does. Synthetic fixtures only: the notes-api world, placeholder ids, the session names "api" and "web".
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

// ── the saved line's scene (file-comments-seen-fixes.test.ts saveReply, copied) ─────────────────────
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

// ── the key that sends (decision 41): Enter or Space on the confirm's Send ────────────────────────
// The browser activates a button on Enter's keydown and on Space's keyup, both after the row's capture keydown listener, so a
// keydown then a click is the order the engine dispatches; the stand-in's click() runs no keydown of its own.
for (const key of ["Enter", " "]) {
  test(`${key === " " ? "Space" : "Enter"} on the confirm's Send is the send's own press: the key marks the card on screen seen and leaves the option as the person read it, and the send accepts nothing, as the disabled box said (before: pinned at source alone — without the clause the key's gesture rewrote the option at once, and the send accepted the change the box said stays pending)`, async (t) => {
    const { w, last } = await unseenInView(t);
    const before = verbs(w).length;
    const b = sendButton(w);
    b.dispatchEvent(new Ev("keydown", { key }));
    assert.ok(!isNew(w.card(CHG2)), "seen by the key");
    assert.equal(acceptWords(w), ALL_UNSEEN, "the words the person read stand through the key");
    assert.equal(acceptBox(w).disabled, true); assert.equal(acceptBox(w).checked, false);
    assert.deepEqual(countRows(w), [], "and no count row");
    b.click(); await tick();
    assert.equal(verbs(w).length, before, "no accept: the box said nothing is accepted");
    assert.equal(last().type, "fileCommentsSend");
    assert.equal(last().accepted, 0);
    await sentOk(w);
    w.close();
  });
}

// ── the saved line (decision 43): every kind of gesture ends it ───────────────────────────────────
test("a key after the landing ends the saved line, and so does a touch move — the guide's 'scroll, click, tap, or key' held behaviorally (before: the gesture-kind loop fired them BEFORE the reply landed, and only a source pin held the two); the end scrolls nothing", async (t) => {
  let { w, body } = await saveReply(t);
  assert.equal(savedOf(w)!.textContent, "Saved · the card is below");
  w.aside().dispatchEvent(new Ev("keydown", { key: "ArrowDown" }));   // an arrow in the panel
  assert.equal(savedOf(w), null, "a key ends the line");
  assert.equal(body.scrollTop, 0, "and scrolls nothing");
  w.close();
  ({ w, body } = await saveReply(t));
  body.dispatchEvent(new Ev("keydown", { key: "PageDown" }));   // a page key in the text
  assert.equal(savedOf(w), null, "a key in the text ends it too");
  w.close();
  ({ w, body } = await saveReply(t));
  body.dispatchEvent(new Ev("touchmove"));
  assert.equal(savedOf(w), null, "a touch move ends the line");
  assert.equal(body.scrollTop, 0);
  w.close();
});

// ── the keyboard's way to the line (NAV_KEYS) ─────────────────────────────────────────────────────
test("a Tab or a modifier pressed alone is no gesture: the line stands through the Tab that brings the keyboard to it and through a Shift or Ctrl held for a chord (before: every key ended it, so no keyboard could reach the button); a key ON the line keeps it, its click shows the card, and the keyboard lands on that card's head, not on the body", async (t) => {
  const { w, body } = await saveReply(t);
  const send = actIn(w.aside(), "fcsend")!;
  send.focus();
  assert.equal(doc.activeElement, send, "the fixture: the keyboard is on Send to session, the stop before the line");
  for (const key of ["Tab", "Shift", "Control", "Alt", "Meta", "AltGraph"]) {
    send.dispatchEvent(new Ev("keydown", { key }));
    assert.equal(savedOf(w)?.textContent, "Saved · the card is below", key + " ends nothing");
  }
  assert.equal(body.scrollTop, 0, "nothing scrolled");
  const line = savedOf(w)!;
  line.focus();                                         // the browser's Tab lands here, the next stop after Send
  assert.equal(doc.activeElement, line, "the fixture: the line is focusable");
  line.dispatchEvent(new Ev("keydown", { key: "Enter" }));
  assert.equal(savedOf(w), line, "Enter on the line itself keeps it: its click is what it is for");
  line.click(); await tick();                            // the browser's activation of the button on Enter
  assert.equal(body.scrollTop, SHOW_CARD, "the click: the card into view");
  assert.equal(savedOf(w), null, "and the line is over");
  assert.equal(doc.activeElement, headOf(w, passage.id), "the keyboard is on the card the line showed (before: the removed node took it to the body)");
  w.close();
});

test("a Tab marks no arrival seen either — the next real key does (the gesture rule is one for both lines)", async (t) => {
  const { w, ok } = await open(t, textWorld(), nonePending());
  await land(w, ok, twoUnseen());
  scrollBody(w, 340);                                   // row 7's card in the box [340, 500), seen by no gesture
  assert.ok(isNew(w.card(CHG2)), "the fixture: an arrival on screen");
  w.body.dispatchEvent(new Ev("keydown", { key: "Tab" }));
  assert.ok(isNew(w.card(CHG2)), "a Tab is no gesture");
  w.body.dispatchEvent(new Ev("keydown", { key: "Shift" }));
  assert.ok(isNew(w.card(CHG2)), "nor a modifier alone");
  w.body.dispatchEvent(new Ev("keydown", { key: "ArrowDown" }));
  assert.ok(!isNew(w.card(CHG2)), "an arrow is: seen");
  w.close();
});

test("a pointer click on the line (the hold's path): the line leaves after the release, and the keyboard it held goes to the card as well", async (t) => {
  const { w, body } = await saveReply(t);
  const line = savedOf(w)!;
  line.focus();                                         // a click focuses the button in most engines
  gesture(line, "pointerdown");
  win.dispatchEvent(new Event("pointerup"));
  line.click(); await tick();
  assert.equal(body.scrollTop, SHOW_CARD, "the card into view");
  await new Promise<void>((r) => setTimeout(r, 0)); await tick();   // the hold's parked change: the line leaves
  assert.equal(savedOf(w), null);
  assert.equal(doc.activeElement, headOf(w, passage.id), "the keyboard is on the card's head");
  w.close();
});

// ── the margin layout's line sticks to the Send section's bottom edge ─────────────────────────────
/** A whole-file comment saved in the margin layout with the text scrolled down and the Send confirm up (`confirm`): the fresh
 *  card is loose at the top of the track, above the box. */
async function saveFileCommentInMargin(t: Ctx, confirm: boolean): Promise<{ w: World; fresh: StoreComment }> {
  const w = textWorld();
  const { ok, last } = await open(t, w);
  if (confirm) { actIn(w.aside(), "fcsend")!.click(); assert.ok(w.aside().querySelector(".fc-confirm"), "the fixture: the confirm is up"); }
  scrollBody(w, 600);
  actIn(w.aside(), "fcfile")!.click();
  const input = w.aside().querySelector(".fc-composer .fc-input")!;
  input.value = "Add the run's date.";
  input.dispatchEvent(new Ev("keydown", { key: "Enter", ctrlKey: true })); await tick();
  assert.equal(last().verb, "comment");
  const fresh: StoreComment = { id: (T0 + 50000) + "-0", author: "you", ts: T0 + 50000, body: "Add the run's date.", replies: [], resolved: false };
  await ok(status({ verb: "comment", store: { v: 3, path: "docs/report.md", suggestions: [], comments: [whole, findings, passage, closing, fresh] }, storeMtimeNs: "1757145600000000005" }));
  return { w, fresh };
}

test("the margin layout's line is stuck to the Send section's bottom edge — position sticky at bottom 0 over the panel's background, inline — so it is on screen while the section scrolls inside itself with the confirm up (before: it stood after the confirm, past the section's box, and every scroll that would show it ended it); the confirm stays up through the save; the list layout's line under the header carries no such style", async (t) => {
  const { w } = await saveFileCommentInMargin(t, true);
  const line = savedOf(w);
  assert.ok(line, "the line is in the panel");
  assert.equal(line!.textContent, "Saved · the card is above");
  assert.ok(w.aside().querySelector(".fc-confirm"), "the confirm is still up");
  const send = w.aside().querySelector(".fc-send")!;
  assert.ok(send.contains(line!), "in the Send box");
  assert.ok(send.childNodes.indexOf(line!) > send.childNodes.indexOf(send.querySelector(".fc-confirm")!), "after the confirm, in the acknowledgment's position");
  assert.equal(line!.style.position, "sticky");
  assert.equal(line!.style.bottom, "0");
  assert.equal(line!.style.background, "var(--bg)", "the panel's background, over the rows behind it");
  assert.deepEqual(line!.classes, ["fc-note", "fc-sent", "fc-saved"], "in the same dress");
  w.close();
  const plain = await saveFileCommentInMargin(t, false);
  assert.equal(savedOf(plain.w)!.style.position, "sticky", "without the confirm as well: one line, one place");
  plain.w.close();
  narrow = true;
  try {
    const lw = textWorld();
    const { ok, last } = await open(t, lw);
    actIn(lw.aside(), "fcfile")!.click();
    const input = lw.aside().querySelector(".fc-composer .fc-input")!;
    input.value = "Add the run's date.";
    input.dispatchEvent(new Ev("keydown", { key: "Enter", ctrlKey: true })); await tick();
    assert.equal(last().verb, "comment");
    const fresh: StoreComment = { id: (T0 + 50000) + "-0", author: "you", ts: T0 + 50000, body: "Add the run's date.", replies: [], resolved: false };
    await ok(status({ verb: "comment", store: { v: 3, path: "docs/report.md", suggestions: [], comments: [whole, findings, passage, closing, fresh] }, storeMtimeNs: "1757145600000000005" }));
    const head = savedOf(lw);
    assert.ok(head && lw.aside().querySelector(".fc-sec-head")!.contains(head), "the fixture: the list layout's line, under the header");
    assert.equal(head!.style.position, undefined, "no inline place: the head is the scroller's top");
    lw.close();
  } finally { narrow = false; }
});

// ── the list layout's save keeps the send acknowledgment ──────────────────────────────────────────
/** Nothing pending, one unsent comment: a send carries the comment alone and accepts nothing. */
const unsentOnly = (): Status => status({ hunks: [], store: { v: 3, path: "docs/report.md", suggestions: [], comments: COMMENTS } });
const ackOf = (w: World): El | null => w.aside().querySelectorAll(".fc-sent").find((n) => !n.classList.contains("fc-saved")) || null;
/** Send to session, the confirm's Send, the kernel's acknowledgment, and the status the send re-asks: the acknowledgment stands. */
async function sendOnce(w: World, ok: (s?: Status) => Promise<void>, last: () => Posted): Promise<void> {
  actIn(w.aside(), "fcsend")!.click();
  actIn(w.aside(), "fcsendgo")!.click(); await tick();
  assert.equal(last().type, "fileCommentsSend", "the fixture: the send went");
  await sentOk(w);
  assert.equal(last().verb, "status", "the send re-asks status");
  await ok(unsentOnly());
  assert.match(ackOf(w)!.textContent, /^Sent to api at /, "the fixture: the acknowledgment stands");
}
async function saveFileComment(w: World, ok: (s?: Status) => Promise<void>, last: () => Posted): Promise<StoreComment> {
  actIn(w.aside(), "fcfile")!.click();
  const input = w.aside().querySelector(".fc-composer .fc-input")!;
  input.value = "Add the run's date.";
  input.dispatchEvent(new Ev("keydown", { key: "Enter", ctrlKey: true })); await tick();
  assert.equal(last().verb, "comment");
  const fresh: StoreComment = { id: (T0 + 50000) + "-0", author: "you", ts: T0 + 50000, body: "Add the run's date.", replies: [], resolved: false };
  await ok(status({ verb: "comment", hunks: [], store: { v: 3, path: "docs/report.md", suggestions: [], comments: [whole, findings, passage, closing, fresh] }, storeMtimeNs: "1757145600000000005" }));
  return fresh;
}

test("the list layout: a save whose card lands out of view raises the line under the header and LEAVES the send acknowledgment at the foot (before: cleared, for a position the line never took there — and only when the card landed out of view)", async (t) => {
  narrow = true;
  try {
    const w = textWorld();
    const { ok, last } = await open(t, w, unsentOnly());
    await sendOnce(w, ok, last);
    const fresh = await saveFileComment(w, ok, last);
    const r = w.card(fresh.id)!.getBoundingClientRect();
    assert.ok(r.top >= LIST_TOP + LIST_VIEW, "the fixture: the fresh card is below the box: " + r.top);
    const line = savedOf(w);
    assert.ok(line && line.textContent === "Saved · the card is below", "the line");
    assert.ok(w.aside().querySelector(".fc-sec-head")!.contains(line!), "under the header");
    const ack = ackOf(w);
    assert.ok(ack, "the acknowledgment stands (before: gone)");
    assert.match(ack!.textContent, /^Sent to api at /);
    assert.ok(w.aside().querySelector(".fc-sec-send")!.contains(ack!), "at the foot, where it was");
    w.close();
  } finally { narrow = false; }
});

test("the margin layout: the line takes the acknowledgment's position, and the acknowledgment gives way to it as before", async (t) => {
  const w = textWorld();
  const { ok, last } = await open(t, w, unsentOnly());
  await sendOnce(w, ok, last);
  scrollBody(w, 600);                                   // the loose card the save adds stands above the box
  const fresh = await saveFileComment(w, ok, last);
  assert.ok(w.card(fresh.id), "the fixture: the card is in the list");
  const line = savedOf(w);
  assert.ok(line && line.textContent === "Saved · the card is above", "the line");
  assert.ok(w.aside().querySelector(".fc-sec-send")!.contains(line!), "in the Send section");
  assert.equal(ackOf(w), null, "the acknowledgment gave way: the position is the line's");
  w.close();
});

// ── the track path's accept stands down on a change grown since the press ─────────────────────────
const TRACKED = { kind: "file", entry: "docs/report.md" } as const;
const TAIL = " And a sentence the person never saw.";
const grownH1: Hunk = { ...hunk, newText: LONG + TAIL, curTo: hunk.curTo + TAIL.length };
/** An untracked file with two pending changes, both seen with the first status. */
const untracked = (): Status => twoSeen({ trackedBy: null });
const trackBox = (w: World): El => w.aside().querySelector('input[data-opt="track"]')!;
const sendErr = (w: World): string | null => { const r = w.aside().querySelectorAll(".fc-err").find((x) => x.dataset.slot === "send"); return r ? r.querySelector("span")!.textContent : null; };   // the words, without the row's ✕

test("the track box checked and a seen change grown between the press and set-tracked's reply: the accept stands down with the 'Nothing decided' row and nothing is sent, as the no-track path does (before: the accept took its baseline from set-tracked's fresh status, read the grown change as unchanged, accepted it unread, and the message said so)", async (t) => {
  const { w, ok, last } = await open(t, textWorld(), untracked());
  actIn(w.aside(), "fcsend")!.click();
  assert.equal(trackBox(w).checked, true, "the fixture: tracking goes on with the send (decision 8)");
  assert.equal(acceptWords(w), "accept the 2 pending changes you have seen");
  assert.equal(acceptBox(w).checked, true);
  actIn(w.aside(), "fcsendgo")!.click(); await tick();
  assert.equal(last().verb, "set-tracked", "the sequence: set-tracked first");
  assert.deepEqual(last().args, { on: true, scope: "file" });
  // the session's track-edit coalesced into h1 meanwhile: set-tracked's reply carries the grown change under the same id
  await ok(twoSeen({ verb: "set-tracked", trackedBy: TRACKED, hunks: [grownH1, hunkB], storeMtimeNs: "1757145600000000007", configMtimeNs: "1757145600000000008" }));
  assert.equal(last().verb, "set-tracked", "no accept went out after it");
  assert.ok(!verbs(w).includes("accept"), "no accept");
  assert.equal(lastOf(w, "fileCommentsSend"), undefined, "and nothing was sent");
  assert.equal(sendErr(w), "Nothing decided: the session edited this change after you clicked, and it now reads differently. Look it over and try again.", "the row under Send says why");
  assert.ok(w.aside().querySelector(".fc-confirm"), "the confirm stands, for the next press");
  w.close();
});

test("the same send with the changes as the confirm showed them goes through: set-tracked, then the accept by the two ids, then the message with the reply's count and tracked true", async (t) => {
  const { w, ok, last } = await open(t, textWorld(), untracked());
  actIn(w.aside(), "fcsend")!.click();
  actIn(w.aside(), "fcsendgo")!.click(); await tick();
  assert.equal(last().verb, "set-tracked");
  await ok(twoSeen({ verb: "set-tracked", trackedBy: TRACKED, storeMtimeNs: "1757145600000000007", configMtimeNs: "1757145600000000008" }));
  assert.equal(last().verb, "accept", "then the accept");
  assert.deepEqual(last().args, { ids: ["h1", "hb"] });
  assert.equal(sendErr(w), null, "no row");
  await ok({ ...afterAccept(), verb: "accept", accepted: ["h1", "hb"] } as unknown as Status);
  assert.equal(last().type, "fileCommentsSend");
  assert.equal(last().accepted, 2);
  assert.equal(last().tracked, true);
  await sentOk(w);
  w.close();
});

// ── at source ─────────────────────────────────────────────────────────────────────────────────────
test("at source: NAV_KEYS return before the gesture's work; the line's removal goes through removeLine; the margin layout's line carries the sticky place and its card's key; landSaved clears the acknowledgment in the margin layout alone; doSend checks the accept against the confirm's status once set-tracked has applied a fresh one", () => {
  assert.ok(SRC.includes('const NAV_KEYS = new Set(["Tab", "Shift", "Control", "Alt", "AltGraph", "Meta"]);'));
  const gesture = SRC.slice(SRC.indexOf("gesture(ev?: Event): void {"), SRC.indexOf("private entryShown("));
  assert.match(gesture, /const kb = ev && ev\.type === "keydown" \? \(ev as KeyboardEvent\) : null;\n\s*if \(kb && NAV_KEYS\.has\(kb\.key\)\) return;/, "before anything is marked or ended");
  assert.ok(gesture.indexOf("NAV_KEYS.has(kb.key)") < gesture.indexOf('const over = this.savedOut !== null && !on("fcsavedgo");'));
  const lines = SRC.slice(SRC.indexOf("private reflectLines(): void {"), SRC.indexOf("private markNew(): void {"));
  assert.ok(lines.includes("if (!this.savedOut) { if (line) this.removeLine(line); }"));
  assert.match(lines, /private removeLine\(line: HTMLElement\): void \{\n\s*const held = document\.activeElement === line;\n\s*line\.remove\(\);\n\s*if \(held\) this\.focusNear\(\{ act: "fcsavedgo", card: line\.dataset\.id \}\);/);
  const button = SRC.slice(SRC.indexOf("private savedButton(): HTMLElement | null {"), SRC.indexOf("private syncSendGo("));
  assert.ok(button.includes("b.dataset.id = this.savedOut.key;"));
  assert.ok(button.includes('if (this.margin) { b.style.position = "sticky"; b.style.bottom = "0"; b.style.background = "var(--bg)"; }'));
  const land = SRC.slice(SRC.indexOf("private landSaved("), SRC.indexOf("private cardWhere("));
  assert.match(land, /this\.savedOut = \{ key, side \};\n(?:\s*\/\/[^\n]*\n)*\s*if \(this\.margin\) this\.sentNote = null;/);
  const closed = SRC.slice(SRC.indexOf("private landClosed("), SRC.indexOf("// ── the arrivals (the arrivals follow-on"));
  assert.ok(!closed.includes("sentNote"), "the list layout's landing leaves the acknowledgment");
  const send = SRC.slice(SRC.indexOf("async doSend(): Promise<void> {"), SRC.indexOf("private async sendOnce("));
  assert.match(send, /tracked = !!r\.trackedBy;\n(?:\s*\/\/[^\n]*\n)*\s*const grown = changedSince\(seenChanges\(s, \{ ids: acceptIds \}\), r\.hunks \|\| \[\]\);\n\s*if \(grown\.length\) \{ this\.errors\.set\("send", \{ text: changedRowText\(grown\.length\), reload: false \}\); return; \}/, "against the press-time status, before the accept");
  assert.ok(send.indexOf("const grown = changedSince(") < send.indexOf('const a = await this.mutate("accept", { ids: acceptIds }, "send");'));
});

test("vocabulary: this module's own prose says a change's old and new text, file comment and run of turns; the words CONTEXT.md sets aside appear nowhere in it, nor the banned sessions-pane word, nor a home path", () => {
  const SELF = web("file-comments-seen-review2.test.ts").split("\n").filter((l) => !l.includes("assert.doesNotMatch(SELF")).join("\n");
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

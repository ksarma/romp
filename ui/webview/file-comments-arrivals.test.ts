// The arrivals follow-on (plans/file-review.md, "The arrivals follow-on (2026-09-09)" under Slice 2), driven over the review
// stand-in file-comments-focus.test.ts drives (copied here, as the sibling focus modules copy it). Two rules, both from the
// user's reports of 2026-09-09. The NOTICE: the user sent comments, the session answered with eleven changes and seven
// replies while they kept commenting, and nothing said so until the next Send accepted the changes by default. The panel now
// keeps the set of entries the person has seen (a change, a comment, a reply), files a status's entries by another author
// that are not in it as arrivals, and while any stand shows one line under the header naming them — a button that shows the
// first of them — with a dot on each arrival's card and marks; seen is a gesture of the person's (a pointer press, a key, a
// wheel, a touch move, a save, a send) finding the card on screen, never a timer; the person's own writes and the panel's
// first status are never arrivals; the Send confirm's accept option accepts the pending changes the person has seen and
// counts the arrived ones as unseen, left pending (the seen follow-on's words, decision 41). THE SAVE: the save used to
// scroll the text to the saved card whatever the person had done meanwhile, then stood down when a gesture of theirs came
// between Save and the reply; since decision 43 (the seen follow-on) it never scrolls — the saved card is the focus for the
// layout, and when it lands out of view the acknowledgment's position at the panel's foot says which side it is on, a button
// whose click brings the card into view; the line ends at the person's next gesture or when the card comes into view.
// The numbers a real engine measures are file-comments-arrivals-browser.test.ts.
// Synthetic fixtures only: the notes-api world, placeholder ids, the session names "api" and "web".
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
  button: number | undefined;                          // a press's button when a test gives one: pressHold arms on the primary (0) alone, so the row's hold engages only where a test asks for it
  constructor(public type: string, init: { key?: string; ctrlKey?: boolean; metaKey?: boolean; button?: number } = {}) { this.key = init.key || ""; this.ctrlKey = !!init.ctrlKey; this.metaKey = !!init.metaKey; this.button = init.button; }
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

// ── the notice ────────────────────────────────────────────────────────────────────────────────────

test("a status bringing entries by another author the person has not seen shows the line under the header, in the model's words, and dots on the arrivals' cards and marks; the person's own comment in the same status, the entries of the first status and the cards already seen carry none", async (t) => {
  const { w, ok } = await open(t, textWorld());
  assert.equal(lineOf(w), null, "the panel's first status is all seen: no line");
  assert.ok(!w.aside().querySelectorAll(".fc-card").some(isNew), "no dot on a card of the first status");
  await land(w, ok, arrived());
  const line = lineOf(w);
  assert.ok(line, "the line is under the header");
  assert.equal(line!.textContent, ARRIVED);
  assert.equal(line!.tagName, "BUTTON", "a button, through the delegate");
  assert.ok(w.aside().querySelector(".fc-head")!.contains(line!), "in the head section");
  assert.ok(isNew(w.card(findings.id)), "the card of the comment the session replied to");
  assert.ok(isNew(w.card(passage.id)), "and the other");
  assert.ok(isNew(w.card(CHG2)), "the session's new change");
  assert.ok(isNew(w.card(line9.id)), "the session's own comment");
  assert.ok(!isNew(w.card(mine2.id)), "the person's own comment, saved elsewhere: not an arrival");
  assert.ok(!isNew(w.card(whole.id)) && !isNew(w.card(CHG)), "nothing the first status held");
  assert.ok(isNew(markOf(w, passage.id)), "the highlight wears the dot too");
  assert.ok(isNew(markOf(w, CHG2)), "and the change's mark");
  assert.ok(!isNew(markOf(w, CHG)), "a seen change's mark does not");
  w.close();
});

test("seen is a gesture, never time: a wheel marks the arrivals whose cards are in the track's box seen — the dots come off in place and the line's count drops — and leaves the ones below; the text scrolled on, the next gesture marks what is in the box then; when none is left the line goes", async (t) => {
  const { w, ok } = await open(t, textWorld());
  await land(w, ok, arrived());
  assert.equal(w.body.scrollTop, 0);
  // the geometry: the track's box at scroll 0 holds the tops in [0, 160): the loose card, the findings' card (60) and the first
  // change (120); the passage's card (240), the second change (360) and the session's comment (480) are below it
  assert.equal(w.top(findings.id), desired(2)); assert.equal(w.top(passage.id), desired(5)); assert.equal(w.top(CHG2), desired(7)); assert.equal(w.top(line9.id), desired(9));
  assert.ok(desired(2) < TRACK && desired(5) >= TRACK, "the fixture: one arrival in the box, the rest below");
  for (let i = 0; i < 5; i++) await tick();             // time passes: nothing changes
  assert.equal(lineOf(w)!.textContent, ARRIVED, "waiting marks nothing seen");
  assert.ok(isNew(w.card(findings.id)));
  gesture(w.body, "wheel");                             // the person scrolls: what was on screen before the scroll is seen
  assert.equal(lineOf(w)!.textContent, "api made 1 change, 1 comment and 1 reply since you last looked", "the reply on the card in the box is seen");
  assert.ok(!isNew(w.card(findings.id)), "its dot came off, in place");
  assert.ok(!isNew(markOf(w, findings.id)), "and the highlight's");
  assert.ok(isNew(w.card(passage.id)) && isNew(w.card(CHG2)) && isNew(w.card(line9.id)), "the cards below the box keep theirs");
  // the text scrolled on (the wheel's own effect, the lock carrying the track): the passage's card is in the box, the change is not
  scrollBody(w, 200);
  assert.equal(w.track().scrollTop, 200);
  assert.ok(isNew(w.card(passage.id)), "scrolling in marks nothing: the gesture after does");
  gesture(w.aside().querySelector(".fc-input") || w.aside(), "keydown");   // a key in the panel
  assert.equal(lineOf(w)!.textContent, "api made 1 change and 1 comment since you last looked");
  assert.ok(!isNew(w.card(passage.id)) && !isNew(markOf(w, passage.id)));
  assert.ok(isNew(w.card(CHG2)), "the change at 360 is not in [200, 360)");
  scrollBody(w, 340);                                   // [340, 500): the change and the session's comment
  gesture(w.body, "pointerdown");
  assert.equal(lineOf(w), null, "every arrival seen: the line is gone");
  assert.ok(!w.aside().querySelectorAll(".fc-card").some(isNew), "no dot left");
  assert.ok(!isNew(markOf(w, CHG2)));
  w.close();
});

test("a touch move is a gesture too; a status landing after the arrivals were seen re-marks nothing, a status without the entry drops the arrival, and a re-render keeps the seen set", async (t) => {
  const { w, ok } = await open(t, textWorld());
  await land(w, ok, arrived());
  gesture(w.body, "touchmove");                         // the findings' reply, in the box, is seen
  assert.equal(lineOf(w)!.textContent, "api made 1 change, 1 comment and 1 reply since you last looked");
  // a poll's status with the same entries: nothing new, the seen stay seen, the line unchanged
  await land(w, ok, arrived({ verb: "resolve", storeMtimeNs: "1757145600000000005" }));
  assert.equal(lineOf(w)!.textContent, "api made 1 change, 1 comment and 1 reply since you last looked");
  assert.ok(!isNew(w.card(findings.id)), "seen stays seen across a status");
  assert.ok(isNew(w.card(passage.id)));
  // the change decided elsewhere: gone from the status, it is no arrival
  await land(w, ok, arrived({ hunks: [hunk], storeMtimeNs: "1757145600000000006" }));
  assert.equal(lineOf(w)!.textContent, "api made 1 comment and 1 reply since you last looked");
  assert.equal(w.card(CHG2), null);
  // the viewer's repaint (a Raw/Rendered switch, a reload) rebuilds the marks and the cards: the dots and the line stand
  w.repaint();
  assert.equal(lineOf(w)!.textContent, "api made 1 comment and 1 reply since you last looked");
  assert.ok(isNew(w.card(passage.id)) && isNew(markOf(w, passage.id)) && isNew(w.card(line9.id)));
  w.close();
});

test("the line's click shows the first arrival in the list's order as the focus — opened, level with its mark, the mark centered — and its own press marks nothing seen, so the line stands through the click; the gesture after marks the shown card seen", async (t) => {
  const { w, ok } = await open(t, textWorld());
  const body = w.body;
  await land(w, ok, arrived());
  gesture(body, "wheel");                               // the findings' reply seen; the passage's card (240) is the first arrival left in the list's order
  scrollBody(w, 200);                                   // the passage's card is in the box now: a press elsewhere would mark it seen
  const line = lineOf(w)!;
  const words = line.textContent;
  gesture(line, "pointerdown");                         // the press on the line itself
  assert.equal(lineOf(w)!.textContent, words, "the line's own press marks nothing");
  assert.ok(isNew(w.card(passage.id)), "the card it is about to show keeps its dot");
  line.click(); await tick();
  assert.ok(w.card(passage.id)!.classList.contains("open"), "the first arrival's card opened");
  assert.equal(w.top(passage.id), desired(5), "the focus: level with its highlight");
  const markY = desired(5) + OFFSET, showCard = desired(5) + OPEN + 8 - TRACK;
  assert.ok(showCard > markY - BODY_VIEW / 2, "the fixture: the card's end needs more scroll than the mark's center");
  assert.equal(body.scrollTop, showCard, "the mark toward the center, the card's end in the box (centerOn)");
  assert.ok(lineOf(w), "the line stays after the click");
  assert.equal(lineOf(w)!.textContent, words, "with the same words: the glance is not lost to the click");
  assert.ok(isNew(w.card(passage.id)), "the shown card keeps its dot until the next gesture");
  gesture(body, "wheel");                               // the next gesture: the shown card is seen
  assert.ok(!isNew(w.card(passage.id)));
  assert.equal(lineOf(w)!.textContent, "api made 1 change and 1 comment since you last looked");
  w.close();
});

test("the Send confirm's accept option counts an arrived pending change as unseen, left pending, and its default is untouched; the words follow the arrivals as they are seen", async (t) => {
  const { w, ok } = await open(t, textWorld());
  actIn(w.aside(), "fcsend")!.click();
  let cb = w.aside().querySelector('input[data-opt="accept"]')!;
  assert.equal(cb.parentNode!.textContent, "accept the 1 pending change you have seen", "no arrivals: the first status's change is seen, and nothing is unseen");
  assert.equal(cb.checked, true, "checked by default (decision 8)");
  actIn(w.aside(), "fcsendcancel")!.click();
  await land(w, ok, arrived());
  actIn(w.aside(), "fcsend")!.click();
  cb = w.aside().querySelector('input[data-opt="accept"]')!;
  assert.equal(cb.parentNode!.textContent, "accept the 1 pending change you have seen (1 unseen stays pending)", "the arrived change is the unseen one");
  assert.equal(cb.checked, true, "the words changed, the default did not");
  assert.equal(cb.disabled, false, "a change is seen, so the box can be checked");
  // the change seen: the option says so without a render
  scrollBody(w, 340); gesture(w.body, "wheel");
  assert.equal(w.aside().querySelector('input[data-opt="accept"]')!.parentNode!.textContent, "accept the 2 pending changes you have seen");
  w.close();
});

test("the seen set lives with the panel: closed and reopened on the same file, the arrivals stand and a status landing on the reopen brings the session's later entries as arrivals, not as a fresh file's first status", async (t) => {
  const { w, ok, button } = await open(t, textWorld());
  await land(w, ok, arrived());
  gesture(w.body, "wheel");
  const words = lineOf(w)!.textContent;
  button.click();                                       // close: the aside goes
  assert.equal(w.main.querySelector(".fileview-aside"), null);
  button.click();                                       // reopen: the panel re-asks status
  const later = arrived({ verb: "status", storeMtimeNs: "1757145600000000007", store: { v: 3, path: "docs/report.md", suggestions: [], comments: [whole, findingsR, passageR, apiReply(closing, T0 + 40000, "Ended on the recommendation."), line9, mine2] } });
  await ok(later);
  assert.ok(lineOf(w), "the arrivals from before the close stand");
  assert.notEqual(lineOf(w)!.textContent, words, "and the reply that landed meanwhile joins them");
  assert.equal(lineOf(w)!.textContent, "api made 1 change, 1 comment and 2 replies since you last looked");
  assert.ok(!isNew(w.card(findings.id)), "what was seen before the close stays seen");
  assert.ok(isNew(w.card(closing.id)), "the reply that landed while the panel was closed");
  w.close();
});

// ── a save never moves the view (decision 43): the line at the foot says where the card is ───────
/** The focus-verify module's scene: the change card open as the focus with the passage's card pushed under it, a reply
 *  typed in the passage's card, the text at its top; `during` runs between Save and the reply. */
async function saveReply(t: Ctx, during: (w: World) => void): Promise<{ w: World; body: El; track: El }> {
  const { w, ok, last } = await open(t, textWorld());
  const body = w.body, track = w.track();
  markOf(w, CHG).click(); await tick();
  headOf(w, passage.id).click(); await tick();
  markOf(w, CHG).click(); await tick();
  assert.equal(w.top(passage.id), PUSHED, "the fixture: the passage's card is open, not the focus, pushed under the tall card");
  actIn(w.card(passage.id)!, "fcreply")!.click(); await tick();
  scrollBody(w, 0);
  const input = w.aside().querySelector(".fc-composer .fc-input")!;
  input.value = "The write-through one.";
  input.dispatchEvent(new Ev("keydown", { key: "Enter", ctrlKey: true }));   // the save chord: a gesture, then the save
  await tick();
  assert.equal(last().verb, "reply");
  during(w);
  const replied: StoreComment = { ...passage, replies: [{ author: "you", ts: T0 + 6000, body: "The write-through one." }] };
  await ok(status({ verb: "reply", store: { v: 3, path: "docs/report.md", suggestions: [], comments: [whole, findings, replied, closing] }, storeMtimeNs: "1757145600000000005" }));
  return { w, body, track };
}
const SHOW_CARD = desired(5) + OPEN + 8 - TRACK;        // 208: the least scroll that shows the saved card's end (centerOn's choice here: what the line's click scrolls to; before decision 43, what the save scrolled to)
const savedOf = (w: World): El | null => actIn(w.aside(), "fcsavedgo");
/** The press released: the window's pointerup, then the hold's zero timer (pressHold runs the parked change after the click). */
const release = async (): Promise<void> => { win.dispatchEvent(new Event("pointerup")); await new Promise<void>((r) => setTimeout(r, 0)); await tick(); };

test("nothing happened between Save and the reply, and the saved card is out of view below the track's box: the save scrolls nothing (before decision 43: to the card), the card is the focus, level with its mark where it is, and the acknowledgment's position says the card is below — a button in the Send section, in the acknowledgment's dress", async (t) => {
  const { w, body, track } = await saveReply(t, () => { /* the person waited */ });
  assert.equal(body.scrollTop, 0, "the text stayed at its top (before: " + SHOW_CARD + ")");
  assert.equal(track.scrollTop, 0);
  assert.equal(w.top(passage.id), desired(5), "the saved card is the focus: level");
  assert.equal(w.top(CHG), LIFTED, "the change card moved up out of its way");
  assert.deepEqual(scrolledInto, []);
  const line = savedOf(w);
  assert.ok(line, "the line is in the panel");
  assert.equal(line!.textContent, "Saved · the card is below");
  assert.equal(line!.tagName, "BUTTON", "a button, through the delegate");
  assert.deepEqual(line!.classes, ["fc-note", "fc-sent", "fc-saved"], "in the acknowledgment's dress, .fc-note on it as on the acknowledgment (the Send section's tiers count it as the acknowledgment, not as growth)");
  assert.equal(line!.title, "Show the card");
  assert.ok(w.aside().querySelector(".fc-sec-send")!.contains(line!), "in the Send section, where the acknowledgment stands");
  assert.equal(w.aside().querySelectorAll(".fc-sent").length, 1, "the one line in that position");
  assert.equal(w.aside().querySelector(".fc-composer")!.hidden, true, "the composer closed as before");
  w.close();
});

for (const [kind, on] of [["wheel", "body"], ["pointerdown", "body"], ["keydown", "input"], ["touchmove", "body"]] as Array<[string, "body" | "input"]>) {
  test(`a ${kind} ${on === "body" ? "in the text" : "in the composer"} between Save and the reply: the save scrolls nothing, the saved card is the focus for the layout — level with its mark where it is — and the line says where it is all the same, the gesture having come before the save landed`, async (t) => {
    const { w, body, track } = await saveReply(t, (w) => { gesture(on === "body" ? w.body : w.aside().querySelector(".fc-composer .fc-input")!, kind); });
    assert.equal(body.scrollTop, 0, "the text stayed where the person had it");
    assert.equal(track.scrollTop, 0);
    assert.equal(w.top(passage.id), desired(5), "the saved card is the focus all the same: level with its mark");
    assert.equal(w.card(passage.id)!.dataset.pushed, undefined);
    assert.equal(w.top(CHG), LIFTED, "the change card moved up out of its way");
    assert.deepEqual(scrolledInto, []);
    assert.equal(savedOf(w)!.textContent, "Saved · the card is below", "the line stands: the gesture was before the landing, not after it");
    assert.equal(w.aside().querySelector(".fc-composer")!.hidden, true, "the composer closed as before");
    w.close();
  });
}

test("the line's click: its own press ends nothing (the click is what it is for), and the click scrolls the card into view through the focus rule — the mark toward the center, the card's end in the box, on both scrollers — and the line is over", async (t) => {
  const { w, body, track } = await saveReply(t, () => { /* the person waited */ });
  const line = savedOf(w)!;
  gesture(line, "pointerdown");                         // the press on the line itself
  assert.ok(savedOf(w), "the line's own press keeps it");
  assert.equal(savedOf(w)!.textContent, "Saved · the card is below");
  line.click(); await tick();
  assert.equal(body.scrollTop, SHOW_CARD, "the click scrolled the text to the card: the least scroll that shows its end (centerOn)");
  assert.equal(track.scrollTop, SHOW_CARD, "the track with it");
  assert.ok(inBox(cardBox(w, passage.id), TRACK_BOX), "the card is whole in the track's box: " + JSON.stringify(cardBox(w, passage.id)));
  assert.equal(w.top(passage.id), desired(5), "the focus still: level");
  assert.deepEqual(scrolledInto, [], "the margin layout: both scrollers, never scrollIntoView");
  assert.equal(savedOf(w), null, "the line is over");
  w.close();
});

test("the line is over at the person's next gesture — a wheel: in place, with no render and no scroll — and under a held press only at the release, through the row's hold: a line leaving the Send section moves the Send button under the pointer", async (t) => {
  let { w, body } = await saveReply(t, () => { /* the person waited */ });
  const send = w.aside().querySelector(".fc-send")!;
  assert.ok(savedOf(w));
  gesture(body, "wheel");
  assert.equal(savedOf(w), null, "gone in place");
  assert.equal(w.aside().querySelector(".fc-send"), send, "no render: the same Send box");
  assert.equal(body.scrollTop, 0, "and the line's end moved nothing");
  w.close();
  ({ w, body } = await saveReply(t, () => { /* the person waited */ }));
  assert.ok(savedOf(w));
  actIn(w.aside(), "fcsend")!.dispatchEvent(new Ev("pointerdown", { button: 0 }));   // a primary press on the Send button above the line: the hold engages
  assert.ok(savedOf(w), "held: the line stays through the press");
  await release();
  assert.equal(savedOf(w), null, "at the release, it is over");
  w.close();
});

test("the line follows the card between renders and ends when the card comes into view with no gesture behind it (the lock's write, a centering): the words turn to above once the text is past the card, and the line goes once the box holds the card", async (t) => {
  const { w, body } = await saveReply(t, () => { /* the person waited */ });
  assert.ok(savedOf(w));
  scrollBody(w, 100);                                   // [100, 260): the card at 240..360 is still past the box's end
  assert.equal(savedOf(w)!.textContent, "Saved · the card is below", "not in the box yet: the line stands");
  scrollBody(w, 600);                                   // [600, 760): the card is above the box now
  assert.equal(savedOf(w)!.textContent, "Saved · the card is above", "the words follow the card's side, in place");
  scrollBody(w, SHOW_CARD);                             // [208, 368) holds the card whole
  assert.equal(savedOf(w), null, "the card came into view: the line is over");
  assert.equal(body.scrollTop, SHOW_CARD, "and the line's end moved nothing");
  w.close();
});

test("a whole-file comment saved with the text scrolled down: the card is loose at the top of the track, above the box — nothing scrolls (before: the text came to the card), the line says above, and its click brings the card into the box by the least scroll that shows it, on both scrollers", async (t) => {
  const { w, ok, last } = await open(t, textWorld());
  const body = w.body, track = w.track();
  scrollBody(w, 600);
  assert.equal(track.scrollTop, 600, "the reader is well down the text");
  actIn(w.aside(), "fcfile")!.click(); await tick();
  const input = w.aside().querySelector(".fc-composer .fc-input")!;
  input.value = "Add a summary at the top.";
  input.dispatchEvent(new Ev("keydown", { key: "Enter", ctrlKey: true })); await tick();
  assert.equal(last().verb, "comment");
  assert.equal(last().args.anchor, undefined, "a whole-file comment: no anchor");
  const fresh: StoreComment = { id: (T0 + 5000) + "-0", author: "you", ts: T0 + 5000, body: "Add a summary at the top.", replies: [], resolved: false };
  await ok(status({ verb: "comment", store: { v: 3, path: "docs/report.md", suggestions: [], comments: [whole, findings, passage, closing, fresh] }, storeMtimeNs: "1757145600000000005" }));
  const top = 8 + (CARD + 8);                           // 56: under the one loose card at the top of the track
  assert.equal(w.top(fresh.id), top, "loose: under the whole-file card at the top of the track, in the list's order");
  assert.equal(body.scrollTop, 600, "nothing scrolled (before: " + (top - 8) + ", the least scroll that showed the card)");
  assert.equal(track.scrollTop, 600);
  assert.equal(w.aside().querySelector(".fc-composer")!.hidden, true, "the composer closed");
  assert.equal(savedOf(w)!.textContent, "Saved · the card is above", "a comment's save renders the line itself: the composer's close re-renders the composer alone");
  savedOf(w)!.click(); await tick();
  assert.equal(body.scrollTop, top - 8, "the click: the least scroll that shows the card (showLoose), on the body");
  assert.equal(track.scrollTop, top - 8, "and on the track, at once");
  assert.ok(inBox(cardBox(w, fresh.id), TRACK_BOX), "the card is in the track's box: " + JSON.stringify(cardBox(w, fresh.id)));
  assert.deepEqual(scrolledInto, []);
  assert.equal(savedOf(w), null, "the line is over");
  w.close();
});

test("the saved card already whole in the track's box: no scroll and no line; the card is the focus", async (t) => {
  const { w, ok, last } = await open(t, textWorld());
  const body = w.body;
  headOf(w, passage.id).click(); await tick();          // the passage's card open, the focus, level at 240
  actIn(w.card(passage.id)!, "fcreply")!.click(); await tick();
  scrollBody(w, 220);                                   // the person's text: the box [220, 380) holds the open card, 240..360
  assert.equal(w.top(passage.id), desired(5));
  const input = w.aside().querySelector(".fc-composer .fc-input")!;
  input.value = "The write-through one.";
  input.dispatchEvent(new Ev("keydown", { key: "Enter", ctrlKey: true })); await tick();
  assert.equal(last().verb, "reply");
  const replied: StoreComment = { ...passage, replies: [{ author: "you", ts: T0 + 6000, body: "The write-through one." }] };
  await ok(status({ verb: "reply", store: { v: 3, path: "docs/report.md", suggestions: [], comments: [whole, findings, replied, closing] }, storeMtimeNs: "1757145600000000005" }));
  assert.equal(body.scrollTop, 220, "a card whole in view: nothing to scroll to, nothing to say");
  assert.equal(w.top(passage.id), desired(5), "still the focus, level");
  assert.equal(savedOf(w), null, "no line for a card in view");
  w.close();
});

// ── at source ─────────────────────────────────────────────────────────────────────────────────────
test("at source: the gestures are the constructor's capture listeners on the body row (pointerdown, keydown, wheel, touchmove), the save and the send; the seen set and the arrivals are read in applyStatus and seeded in render; the save never scrolls — landSaved sets the focus and raises the line, with no scroll call in it and no timer in the line's code", () => {
  assert.match(SRC, /for \(const ev of \["pointerdown", "keydown"\]\) row\.addEventListener\(ev, \(e\) => this\.gesture\(e\), true\);/);
  assert.match(SRC, /for \(const ev of \["wheel", "touchmove"\]\) row\.addEventListener\(ev, \(e\) => this\.gesture\(e\), \{ capture: true, passive: true \}\);/);
  assert.match(SRC, /this\.gesture\(\);\s*\/\/ a send is a gesture/);
  assert.match(SRC, /this\.status = s;\n\s*this\.noteArrivals\(s\);/, "every status lands through applyStatus, and the arrivals are read there");
  assert.match(SRC, /if \(this\.seenKeys === null && s\) this\.seenKeys = new Set\(statusEntries\(s\)\.map\(\(e\) => e\.key\)\);/, "the first render with a status seeds the set");
  assert.doesNotMatch(SRC.slice(SRC.indexOf("gesture(ev?: Event): void {"), SRC.indexOf("private entryShown(")), /setTimeout|setInterval|Date\.now/, "no timer in the gesture");
  assert.match(SRC, /this\.gesture\(\);\n\s*let r: Status \| null;/, "the save counts itself as a gesture and samples no count: nothing stands down, since nothing scrolls (decision 43)");
  assert.doesNotMatch(SRC, /this\.gestures/, "the count went with the scroll it judged");
  assert.match(SRC, /const lined = r !== null && this\.landSaved\(c, had, r, note\);[^\n]*\n\s*if \(r\) this\.closeComposer\(\);[^\n]*\n\s*if \(hid \|\| \(lined && c\.kind !== "reply"\)\) this\.render\(\);/, "the landing when the reply lands, before the composer closes; a comment's save renders the line itself");
  const land = SRC.slice(SRC.indexOf("private landSaved("), SRC.indexOf("private cardWhere("));
  assert.match(land, /const saved = c\.kind === "reply" \? c\.commentId : savedCommentId\(had, r, note\);\n\s*if \(saved === null\) return false;\n\s*const key = this\.cardKey\(saved\);\n\s*if \(this\.margin\) this\.focusOn\(key\);\n\s*const side = this\.cardWhere\(key\);\n\s*if \(side === null\) return false;[^\n]*\n\s*this\.savedOut = \{ key, side \};\n(?:\s*\/\/[^\n]*\n)*\s*if \(this\.margin\) this\.sentNote = null;/, "the side is read once the status has landed and LATCHED: a render swaps in a list the pass has not sized, so the track's scroll reads 0 mid-render; the acknowledgment gives way in the margin layout alone, where the line takes its position (the list layout's stands under the header)");
  assert.doesNotMatch(land, /scrollCard|scrollBoth|scrollIntoView|scrollTop|centerOn|showLoose/, "a save never scrolls (decision 43)");
  const lines = SRC.slice(SRC.indexOf("private reflect(): void {"), SRC.indexOf("private markNew(): void {")) + SRC.slice(SRC.indexOf("private savedLine(): HTMLElement | null {"), SRC.indexOf("private syncSendGo("));
  assert.doesNotMatch(lines, /setTimeout|setInterval|Date\.now/, "no timer in the line's code: it ends on a gesture, a pass or a scroll that finds the card in view");
  assert.doesNotMatch(SRC.slice(SRC.indexOf("private savedLine(): HTMLElement | null {"), SRC.indexOf("private syncSendGo(")), /cardWhere|scrollTop|getBoundingClientRect/, "the render draws the latched side and reads no geometry (the field's comment says why)");
  assert.match(SRC, /if \(this\.savedOut\) this\.reflect\(\);\s*\/\/ the saved line follows the placement/, "the pass re-reads the side where the geometry is settled");
  assert.match(SRC, /else this\.writeScroll\(this\.ctx\.body\(\), this\.sections\.cards\.scrollTop, "track"\);\n\s*if \(this\.savedOut\) this\.reflect\(\);/, "and so does a scroll, after the mirror's write");
  assert.match(SRC, /fcsavedgo: \(\) => \{ const out = this\.savedOut; this\.savedOut = null; if \(out\) this\.scrollCard\(out\.key\); this\.reflect\(\); \},/, "the line's click: scrollCard, and the line is over");
  assert.match(SRC, /if \(this\.hold\) void this\.hold\.defer\(\(\) => this\.reflectLines\(\)\); else this\.reflectLines\(\);/, "the lines change through the hold");
});

test("vocabulary: this module's own prose says a change's old and new text, file comment and run of turns; the words CONTEXT.md sets aside appear nowhere in it, nor the banned sessions-pane word, nor a home path", () => {
  const SELF = web("file-comments-arrivals.test.ts").split("\n").filter((l) => !l.includes("assert.doesNotMatch(SELF")).join("\n");
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

// The focus follow-on (plans/file-review.md, "The focus follow-on (2026-09-08)" under the margin-layout note), driven over
// the review stand-in (file-comments-margin-fixes.test.ts's: clamped scroll positions, a footer under the track, room for
// an open card): the panel's FOCUS — the card the person last acted on, which the pass anchors the layout on (card-layout.ts)
// so that it sits level with its mark and the cards above it move up out of the way — set by a highlight click, a change
// mark, a head click that opens a card, a reference link and Show more (which also centers the mark, as opening a card
// does); NOT by a fold, which moves nothing, of the focus or of any other card; cleared when the card leaves the status
// and when the layout folds to the list; the leader a card moved up past its mark draws down to it; a card the chain
// cannot fit above the focus laid below it, never past the track's start (the follow-on's review, 2026-09-08;
// card-layout-reach.test.ts has the rule); and the fold of a
// tall card (a long part clipped in the margin layout with Show more at the card's foot — a change's old and new text, a
// comment's body, a run of turns — the choice keyed so it survives a re-render, nothing clipped in the list). The numbers
// a real engine measures are file-comments-focus-browser.test.ts. Synthetic fixtures only: the notes-api world,
// placeholder ids.
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
/** The status with the essay and the talked comment in the store too (the comment-fold test). */
const withLong = (storeMtimeNs: string): Status => status({ store: { v: 3, path: "docs/report.md", suggestions: [], comments: [whole, findings, passage, closing, essay, talked] }, storeMtimeNs });

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

// ── the defect, and the focus that fixes it ───────────────────────────────────────────────────────

test("a tall open change card above a comment: clicking the comment's highlight makes its card the focus — level with the highlight, both in view — and the change card moves up by the least that clears it, instead of the comment's card sitting a viewport below", async (t) => {
  const { w } = await open(t, textWorld());
  const body = w.body, track = w.track();
  assert.ok(TALL + 8 > TRACK && OPEN + 8 <= TRACK, "the fixture: the folded change card does not fit the track, an open comment card does");
  assert.equal(w.top(CHG), desired(3), "the change card, closed, is level with its mark");
  assert.equal(w.top(passage.id), desired(5), "and the passage's card with its highlight");
  // the change mark: its card opens as the focus, TALL, level with the mark; the passage's card is pushed under it
  markOf(w, CHG).click(); await tick();
  assert.ok(w.card(CHG)!.classList.contains("open"));
  assert.equal(w.top(CHG), desired(3), "the open change card keeps its mark's height");
  assert.equal(w.top(passage.id), PUSHED, "the passage's card is pushed under the tall card: the push-down rule");
  assert.equal(w.card(passage.id)!.dataset.pushed, "1");
  // the defect's click: the comment's highlight
  body.scrollTop = 0; body.dispatchEvent(new Ev("scroll"));
  markOf(w, passage.id).click(); await tick();
  assert.ok(w.card(passage.id)!.classList.contains("open"), "the comment's card opened");
  assert.equal(w.top(passage.id), desired(5), "the focused card is level with its highlight (before: " + PUSHED + ", a viewport below)");
  assert.equal(w.card(passage.id)!.dataset.pushed, undefined, "not pushed");
  assert.equal(w.top(CHG), LIFTED, "the change card moved up: its end a gap above the focused card");
  assert.equal(w.card(CHG)!.dataset.pulled, undefined, "no leader down: its mark is inside its box (" + LIFTED + ".." + (LIFTED + TALL) + " holds " + desired(3) + ")");
  // the centering: the mark toward the body's center, the card's end in the track's box
  const markY = desired(5) + OFFSET, showCard = desired(5) + OPEN + 8 - TRACK;
  assert.ok(showCard > markY - BODY_VIEW / 2, "the fixture: the card's end needs more scroll than the mark's center");
  assert.equal(body.scrollTop, showCard, "the least scroll that shows the card's end");
  assert.equal(track.scrollTop, showCard, "the track came along");
  const box = cardBox(w, passage.id), mark = markOf(w, passage.id).getBoundingClientRect();
  assert.ok(inBox(box, TRACK_BOX), "the whole card is in the track's box: " + JSON.stringify(box));
  assert.ok(inBox(mark, BODY_BOX), "the highlight is in the body's box: " + JSON.stringify(mark));
  assert.equal(box.top, mark.top, "and the two are level");
  // the cards below the focus follow the push-down rule from its end, as before
  assert.equal(w.top(closing.id), desired(33), "a card far below is untouched");
  // the heading's card (row 2) had to clear the moved change card and has no room to above it (its top would be past the
  // track's start, where no scroll reaches a card): it stands below the focused card instead, by the push-down rule from
  // the focus's end and wearing the leader up to its mark; the loose card at the top of the track, with no room left
  // either, follows it (card-layout.ts: no card past the start — the focus follow-on's review, 2026-09-08)
  assert.ok(LIFTED - CARD - 8 < 0, "the fixture: the heading's card does not fit between the start and the moved change card");
  assert.equal(w.top(findings.id), desired(5) + OPEN + 8, "the heading's card below the focused card, not past the start");
  assert.equal(w.card(findings.id)!.dataset.pushed, "1", "a leader up to its mark");
  assert.equal(w.top(whole.id), desired(5) + OPEN + 8 + CARD + 8, "the loose card after it");
  assert.equal(w.card(whole.id)!.dataset.pushed, undefined, "a loose card is never pushed");
  w.close();
});

test("the focus follows the person: a head click that opens a card, a reference link and Show more each make that card the focus; a fold (a head click on an open card, Show less) moves nothing", async (t) => {
  const { w } = await open(t, textWorld());
  const body = w.body, track = w.track();
  markOf(w, CHG).click(); await tick();                // the change card open, the focus
  assert.equal(w.top(passage.id), PUSHED);
  // a head click that opens
  headOf(w, passage.id).click(); await tick();
  assert.equal(w.top(passage.id), desired(5), "the opened card is the focus: level");
  assert.equal(w.top(CHG), LIFTED);
  // a head click that folds it: the focus stays, and nothing moves but the card's own end
  headOf(w, passage.id).click(); await tick();
  assert.ok(!w.card(passage.id)!.classList.contains("open"));
  assert.equal(w.top(passage.id), desired(5), "still the focus, still level");
  assert.equal(w.top(CHG), LIFTED, "the change card did not fall back");
  // the reference link on the change card (goTo): the change card is the focus again, level with its mark; the passage's
  // card, no longer the focus, is pushed under it as the push-down rule has it
  actIn(w.card(CHG)!, "fcgoto")!.click();
  assert.equal(w.top(CHG), desired(3), "the reference's card is the focus: level");
  assert.equal(w.top(passage.id), PUSHED, "the passage's card yields");
  assert.equal(w.card(passage.id)!.dataset.pushed, "1");
  // the passage's reference link, from its closed card
  actIn(w.card(passage.id)!, "fcgoto")!.click();
  assert.equal(w.top(passage.id), desired(5));
  assert.equal(w.top(CHG), LIFTED);
  // Show more on the change card: the card the focus, WHOLE tall, level; the passage's card under it; and its mark
  // centered, as opening a card by its head is (fcclip sets expandIntent, afterRender centers) — the whole card is taller
  // than the track, so centerOn's fallback: the least scroll that keeps the mark's top in view, a gap under the body's top,
  // with the head cut by the excess. From the top first, so that the centering shows against it, and its absence too
  const f = foldOf(w, CHG);
  assert.equal(f.hidden, false, "the folded change card offers Show more");
  body.scrollTop = 0; body.dispatchEvent(new Ev("scroll"));
  f.row!.querySelector("button")!.click(); await tick();
  assert.equal(w.top(CHG), desired(3), "Show more makes the card the focus");
  assert.equal(w.card(CHG)!.getBoundingClientRect().height, WHOLE);
  assert.equal(w.top(passage.id), desired(3) + WHOLE + 8, "the passage's card under the whole card");
  const markY = desired(3) + OFFSET, showWhole = desired(3) + WHOLE + 8 - TRACK, markGap = markY - 8;
  assert.ok(showWhole > markGap && markGap > markY - BODY_VIEW / 2, "the fixture: the whole card's end needs more scroll than keeps the mark's top in view, and that more than centers the mark");
  assert.equal(body.scrollTop, markGap, "Show more centered its mark: the whole card is taller than the track, so the mark's top a gap under the body's top (before: 0, the text where it was)");
  assert.equal(track.scrollTop, markGap, "the track came along");
  assert.equal(markOf(w, CHG).getBoundingClientRect().top, BODY_BOX.top + 8, "the mark is a gap under the body's top edge");
  assert.equal(cardBox(w, CHG).top, BODY_BOX.top + 8, "and the card level with it, its head cut by the track's header");
  // Show less: a fold; the focus stays on the change card, and the text does not move
  foldOf(w, CHG).row!.querySelector("button")!.click(); await tick();
  assert.equal(w.top(CHG), desired(3));
  assert.equal(w.top(passage.id), PUSHED);
  assert.equal(body.scrollTop, markGap, "a fold scrolls nothing");
  assert.equal(track.scrollTop, markGap);
  w.close();
});

test("a fold of a card that is NOT the focus moves nothing: with the change card the focus and the passage's card open under it, a head click that folds the passage's card leaves the change card at its mark, the folded card under it and the text where it was", async (t) => {
  const { w } = await open(t, textWorld());
  const body = w.body, track = w.track();
  headOf(w, passage.id).click(); await tick();         // the passage's card opened by its head: the focus
  assert.equal(w.top(passage.id), desired(5));
  markOf(w, CHG).click(); await tick();                // the change mark: its card the focus, TALL at its mark; the open passage card pushed under it
  assert.equal(w.top(CHG), desired(3));
  assert.equal(w.top(passage.id), PUSHED);
  assert.equal(w.card(passage.id)!.dataset.pushed, "1");
  assert.ok(w.card(passage.id)!.classList.contains("open"), "the passage's card is open and not the focus");
  const bodyAt = body.scrollTop, trackAt = track.scrollTop;
  assert.ok(bodyAt > 0, "the fixture: the change mark's click scrolled the text, so a scroll on the fold would show against it");
  // the fold, by the head: a dismissal, not an act on the card — the head-click listener leaves the focus where it is
  headOf(w, passage.id).click(); await tick();
  assert.ok(!w.card(passage.id)!.classList.contains("open"), "folded");
  assert.equal(w.top(CHG), desired(3), "the change card is still the focus, level with its mark (a fold that took the focus would lift it to " + LIFTED + ")");
  assert.equal(w.top(passage.id), PUSHED, "the folded card stays under it (a fold that took the focus would lay it at " + desired(5) + ")");
  assert.equal(w.card(passage.id)!.dataset.pushed, "1");
  assert.equal(body.scrollTop, bodyAt, "the text did not move");
  assert.equal(track.scrollTop, trackAt, "nor the track");
  w.close();
});

test("the leader of a card moved up past its own mark runs DOWN to the mark's height (data-pulled, --fc-pull), as a pushed card's runs up", async (t) => {
  const { w } = await open(t, textWorld(), withRec("1757145600000000002"));
  // two cards want row 5's top: the passage's card takes it, and the later comment's is pushed under it with the leader up
  assert.equal(w.top(passage.id), desired(5), "the passage's card is level: nothing above it");
  assert.equal(w.top(rec.id), desired(5) + CARD + 8, "the later card under it");
  assert.equal(w.card(rec.id)!.dataset.pushed, "1", "a leader up to the shared mark");
  markOf(w, rec.id).click(); await tick();             // the later comment the focus: it holds the top, and the passage's card must clear it
  assert.equal(w.top(rec.id), desired(5), "the focus: level with its highlight");
  const up = desired(5) - 8 - CARD;                    // 192: the passage's card ends a gap above the focused card, and so above its own mark
  assert.ok(up >= 0, "the fixture: the moved card stands inside the track (a card the chain would move past the start goes below the focus instead: card-layout-reach.test.ts)");
  assert.equal(w.top(passage.id), up, "the passage's card moved up past its mark");
  const pull = desired(5) - (up + CARD);               // 8: its mark is a gap under its end
  assert.equal(w.card(passage.id)!.dataset.pulled, "1", "a leader down to its mark");
  assert.equal(w.card(passage.id)!.style.getPropertyValue("--fc-pull"), pull + "px");
  assert.equal(w.card(passage.id)!.dataset.pushed, undefined, "no leader up");
  assert.equal(w.card(rec.id)!.dataset.pulled, undefined, "the focused card is level: no leader");
  assert.equal(w.card(rec.id)!.dataset.pushed, undefined);
  // the focus leaves: the passage's card is level again and the leader is gone, the later card pushed under it as before
  markOf(w, passage.id).click(); await tick();         // the passage's highlight makes its card the focus, and opens it
  assert.equal(w.top(passage.id), desired(5));
  assert.equal(w.card(passage.id)!.dataset.pulled, undefined);
  assert.equal(w.card(passage.id)!.style.getPropertyValue("--fc-pull"), "");
  assert.equal(w.top(rec.id), desired(5) + OPEN + 8, "the later card under the open passage card");
  assert.equal(w.card(rec.id)!.dataset.pushed, "1");
  w.close();
});

test("the focus clears when the list no longer holds its card: a status without the comment lays the cards by the push-down rule, and the comment's return does not bring the focus back", async (t) => {
  const { w, ok } = await open(t, textWorld());
  markOf(w, CHG).click(); await tick();
  markOf(w, passage.id).click(); await tick();
  assert.equal(w.top(CHG), LIFTED, "the passage is the focus");
  // a write's reply is a status (mutate): Resolve on the passage's card, answered with a store that no longer holds the comment
  actIn(w.card(passage.id)!, "fcresolve")!.click(); await tick();
  const without = status({ store: { v: 3, path: "docs/report.md", suggestions: [], comments: [whole, findings, closing] }, storeMtimeNs: "1757145600000000005" });
  await ok(without);
  assert.equal(w.card(passage.id), null, "the passage's card is gone");
  assert.equal(w.top(CHG), desired(3), "no focus: the change card is level with its mark again");
  // the comment is back with the next reply (Accept on the change card, answered with the full store): no gesture named it
  actIn(w.card(CHG)!, "fcaccept")!.click(); await tick();
  await ok(status({ storeMtimeNs: "1757145600000000006" }));
  assert.ok(w.card(passage.id), "its card is back");
  assert.equal(w.top(CHG), desired(3), "the focus did not come back with it");
  assert.equal(w.top(passage.id), PUSHED, "the push-down rule: under the tall card");
  w.close();
});

test("the focus clears on the fold to the list layout: the columns come back with the push-down rule", async (t) => {
  const { w } = await open(t, textWorld());
  markOf(w, CHG).click(); await tick();
  markOf(w, passage.id).click(); await tick();
  assert.equal(w.top(CHG), LIFTED);
  narrow = true; resize(); flush();                    // the row's size changed: the observers' pass reads the fold
  assert.ok(!w.aside().classList.contains("fc-margin"), "the list layout");
  narrow = false; resize(); flush();
  assert.ok(w.aside().classList.contains("fc-margin"), "the margin layout is back");
  assert.equal(w.top(CHG), desired(3), "no focus after the fold");
  assert.equal(w.top(passage.id), PUSHED);
  w.close();
});

// ── the fold of a tall card ───────────────────────────────────────────────────────────────────────

test("in the margin layout a long part is clipped: the pass marks it cut and shows Show more at the card's foot; a card whose parts fit offers no toggle; Show more shows the part whole and reads Show less, keyed so a re-render keeps it; Show less folds it again", async (t) => {
  const { w } = await open(t, textWorld());
  assert.equal(foldOf(w, CHG).row, null, "a closed card has no parts and no row");
  markOf(w, CHG).click(); await tick();
  let f = foldOf(w, CHG);
  assert.equal(f.parts, 1, "the change's old and new text is the card's one part");
  assert.deepEqual(f.clipped, ["fc-body fc-diff fc-clip"], "the pass found the cap cut it");
  assert.equal(f.hidden, false, "Show more shows");
  assert.equal(f.label, "Show more");
  assert.equal(f.more, false);
  assert.equal(f.row!.querySelector("button")!.getAttribute("aria-expanded"), "false");
  assert.equal(f.row!.querySelector("button")!.className, "fileview-btn", "the panel's button, through the delegate root");
  assert.equal(f.row!.querySelector("button")!.dataset.act, "fcclip");
  // a card whose parts fit: the row stays hidden
  headOf(w, passage.id).click(); await tick();
  const short = foldOf(w, passage.id);
  assert.equal(short.parts, 1); assert.deepEqual(short.clipped, []); assert.equal(short.hidden, true, "nothing cut: no toggle");
  // Show more (the head click re-rendered the list: the row is read afresh)
  foldOf(w, CHG).row!.querySelector("button")!.click(); await tick();
  f = foldOf(w, CHG);
  assert.equal(f.more, true, "the card wears fc-more: the sheet lifts the cap");
  assert.deepEqual(f.clipped, [], "no fade");
  assert.equal(f.hidden, false); assert.equal(f.label, "Show less");
  assert.equal(f.row!.querySelector("button")!.getAttribute("aria-expanded"), "true");
  // a re-render keeps the choice: the viewer repainted (a reload, a mode switch), which runs the same render a status does
  w.repaint(); await tick();
  f = foldOf(w, CHG);
  assert.equal(f.more, true, "kept across the re-render"); assert.equal(f.label, "Show less");
  // Show less
  f.row!.querySelector("button")!.click(); await tick();
  f = foldOf(w, CHG);
  assert.equal(f.more, false); assert.deepEqual(f.clipped, ["fc-body fc-diff fc-clip"]); assert.equal(f.label, "Show more");
  w.close();
});

test("the list layout clips nothing: after the fold the rows are hidden and no part is marked cut; the columns fold the tall part again", async (t) => {
  const { w } = await open(t, textWorld());
  markOf(w, CHG).click(); await tick();
  assert.deepEqual(foldOf(w, CHG).clipped, ["fc-body fc-diff fc-clip"]);
  narrow = true; resize(); flush();
  assert.ok(!w.aside().classList.contains("fc-margin"));
  let f = foldOf(w, CHG);
  assert.ok(w.card(CHG)!.classList.contains("open"), "the card is still open in the list");
  assert.equal(f.hidden, true, "no Show more in the list");
  assert.deepEqual(f.clipped, [], "no part marked cut");
  narrow = false; resize(); flush();
  f = foldOf(w, CHG);
  assert.deepEqual(f.clipped, ["fc-body fc-diff fc-clip"], "folded again in the margin");
  assert.equal(f.hidden, false);
  w.close();
});

test("the comment card's fold (renderCard's fc-more, apart from the change card's): a body and a run of turns longer than the cap are cut and offer Show more; Show more lifts the cap — the card wears fc-more, the part's box is its content, the card is WHOLE and the card under it yields — and makes the card the focus, its mark centered; a status keeps it; Show less folds it again", async (t) => {
  const { w } = await open(t, textWorld(), withLong("1757145600000000002"));
  const body = w.body, track = w.track();
  assert.ok(LONG_BODY.length > LONG_PART && talked.replies!.map((r) => r.body!).join("").length > LONG_PART && talked.body.length <= LONG_PART, "the fixture: the essay's body and the talked comment's run of turns are long parts; the talked comment's body is not");
  assert.equal(w.top(essay.id), desired(7)); assert.equal(w.top(talked.id), desired(9));
  const partOf = (key: string, cls: string): El => w.card(key)!.querySelectorAll(".fc-clip").find((p) => p.className === cls)!;
  // the essay's body: opened by its head, the card is TALL and folded, its body cut at the cap
  headOf(w, essay.id).click(); await tick();
  let f = foldOf(w, essay.id);
  assert.equal(f.parts, 1, "the body is the card's one part");
  assert.deepEqual(f.clipped, ["fc-body fc-clip"], "the pass found the cap cut the body");
  assert.equal(f.hidden, false); assert.equal(f.label, "Show more"); assert.equal(f.more, false);
  assert.equal(partOf(essay.id, "fc-body fc-clip").clientHeight, PART_CAP, "the body's box is the cap");
  assert.equal(w.card(essay.id)!.getBoundingClientRect().height, TALL);
  assert.equal(w.top(talked.id), desired(7) + TALL + 8, "the talked comment's card under the folded card");
  // Show more: the card wears fc-more, so the sheet lifts the cap (the table: the part's box is its content), the card is
  // WHOLE and the talked comment's card yields by that much; the card is the focus and its mark is centered — taller than the
  // track, so the fallback: the mark's top a gap under the body's top. From the top first, so that the centering shows
  body.scrollTop = 0; body.dispatchEvent(new Ev("scroll"));
  f.row!.querySelector("button")!.click(); await tick();
  f = foldOf(w, essay.id);
  assert.equal(f.more, true, "the card wears fc-more (without it the sheet still cuts the body at eight lines, under a button reading Show less)");
  assert.deepEqual(f.clipped, [], "no fade"); assert.equal(f.hidden, false); assert.equal(f.label, "Show less");
  assert.equal(f.row!.querySelector("button")!.getAttribute("aria-expanded"), "true");
  const bodyPart = partOf(essay.id, "fc-body fc-clip");
  assert.equal(bodyPart.clientHeight, bodyPart.scrollHeight, "the body's box is its content: the cap is lifted");
  assert.equal(w.card(essay.id)!.getBoundingClientRect().height, WHOLE);
  assert.equal(w.top(essay.id), desired(7), "the focus: level with its highlight");
  assert.equal(w.top(talked.id), desired(7) + WHOLE + 8, "the talked comment's card under the whole card");
  const markGap = desired(7) + OFFSET - 8;
  assert.ok(desired(7) + WHOLE + 8 - TRACK > markGap, "the fixture: the whole card's end needs more scroll than keeps the mark's top in view");
  assert.equal(body.scrollTop, markGap, "Show more centered the mark: the least-scroll fallback for a card taller than the track (before: 0)");
  assert.equal(track.scrollTop, markGap, "the track came along");
  // a re-render keeps the choice: the viewer repainted (a reload, a mode switch), which runs the same render a status does
  w.repaint(); await tick();
  f = foldOf(w, essay.id);
  assert.equal(f.more, true, "kept across the re-render"); assert.equal(f.label, "Show less");
  assert.equal(w.card(essay.id)!.getBoundingClientRect().height, WHOLE);
  // Show less: folded again, and the text does not move
  f.row!.querySelector("button")!.click(); await tick();
  f = foldOf(w, essay.id);
  assert.equal(f.more, false); assert.deepEqual(f.clipped, ["fc-body fc-clip"]); assert.equal(f.label, "Show more");
  assert.equal(partOf(essay.id, "fc-body fc-clip").clientHeight, PART_CAP, "capped again");
  assert.equal(w.card(essay.id)!.getBoundingClientRect().height, TALL);
  assert.equal(w.top(talked.id), desired(7) + TALL + 8);
  assert.equal(body.scrollTop, markGap, "a fold scrolls nothing");
  // the talked comment's run of turns: its short body fits; the run is the part the cap cuts
  headOf(w, essay.id).click(); await tick();           // the essay folded by its head, out of the talked comment's way
  headOf(w, talked.id).click(); await tick();
  f = foldOf(w, talked.id);
  assert.equal(f.parts, 2, "the body and the run of turns");
  assert.deepEqual(f.clipped, ["fc-replies fc-clip"], "the run is cut; the short body is not");
  assert.equal(f.hidden, false); assert.equal(f.label, "Show more"); assert.equal(f.more, false);
  assert.equal(partOf(talked.id, "fc-replies fc-clip").clientHeight, PART_CAP);
  assert.equal(w.card(talked.id)!.getBoundingClientRect().height, TALL);
  f.row!.querySelector("button")!.click(); await tick();
  f = foldOf(w, talked.id);
  assert.equal(f.more, true, "the card wears fc-more"); assert.deepEqual(f.clipped, []); assert.equal(f.label, "Show less");
  const run = partOf(talked.id, "fc-replies fc-clip");
  assert.equal(run.clientHeight, run.scrollHeight, "the run's box is its content");
  assert.equal(w.card(talked.id)!.getBoundingClientRect().height, WHOLE);
  w.close();
});

// ── at source: the sheets and the panel ───────────────────────────────────────────────────────────

test("at source: every long part wears fc-clip, the row is rendered hidden, the pass reads the fold before the heights and passes the focus to the layout; the sheets cap and fade under fc-margin alone, in both files", () => {
  assert.match(SRC, /card\.appendChild\(el\("div", "fc-body fc-clip", c\.body\)\);/, "a comment's body");
  assert.match(SRC, /const rs = el\("div", "fc-replies fc-clip"\);/, "a run of turns");
  assert.match(SRC, /diff\.classList\.add\("fc-clip"\);/, "a change's old and new text");
  assert.match(SRC, /row\.appendChild\(el\("div", "fc-body fc-clip", c\.body\)\);/, "a hosted comment's body");
  assert.match(SRC, /this\.moveRows\(kids\(\)\);\n\s*this\.clipCards\(kids\(\)\);/, "the fold read before the cards are measured");
  assert.match(SRC, /const out = layoutCards\(items, CARD_GAP, this\.focusCard\);/, "the focus reaches the pure rule");
  assert.match(SRC, /if \(this\.focusCard !== null && !nodes\.has\(this\.focusCard\)\) this\.focusCard = null;/, "cleared when the list has no card for it");
  assert.match(SRC, /private layoutOff\(\): void \{[\s\S]*?this\.focusCard = null;/, "cleared when the layout ends");
  assert.match(SRC, /if \(this\.margin\) this\.layoutOff\(\);\n\s*this\.focusCard = null;\n\s*for \(const l of this\.regionLayers/, "and with the panel");
  for (const f of ["styles.css", "feed.css"]) {
    const css = web(f);
    assert.ok(css.includes(".fc-margin .fc-card:not(.fc-more) .fc-clip { max-height: 8lh; overflow: hidden; }"), f + ": the cap, eight of the part's lines, under fc-margin alone");
    assert.ok(css.includes(".fc-margin .fc-card:not(.fc-more) .fc-clip[data-clipped] { -webkit-mask-image: linear-gradient(to bottom, black 65%, transparent); mask-image: linear-gradient(to bottom, black 65%, transparent); }"), f + ": the fade on a cut part");
    assert.ok(css.includes(".fc-clip-row[hidden] { display: none; }"), f + ": the hidden row takes no room");
    assert.ok(css.includes(".fc-margin .fc-card[data-pulled]::after { content: \"\"; position: absolute; left: -7px; top: 100%; height: var(--fc-pull, 0px);"), f + ": the leader down");
  }
});

test("vocabulary: this module's own prose says file comment and run of turns; the word CONTEXT.md sets aside for a forked side session appears nowhere in it (the fixture with turns is `talked`, the name file-comments-focus-review.test.ts gives the same shape), nor the banned sessions-pane word, nor a home path", () => {
  // file-comments.test.ts and file-comments-changes.test.ts scan themselves the same way: a test module is new prose too,
  // and its assertion messages print to the person on failure. The scan sets its own guard lines aside.
  const SELF = web("file-comments-focus.test.ts").split("\n").filter((l) => !l.includes("assert.doesNotMatch(SELF")).join("\n");
  assert.doesNotMatch(SELF, /\bthreads?\b/i, "a comment with replies is a file comment with a run of turns (CONTEXT.md, File comment: Avoid)");
  assert.doesNotMatch(SELF, /fleet/i, "no new identifiers or prose in the old word for the sessions pane");
  assert.doesNotMatch(SELF, /\/home\/[a-z]/, "no absolute home paths");
});

// The seen-only accept (plans/file-review.md, decision 41 and "The seen follow-on (2026-09-09)" under Slice 2), driven over
// the review stand-in file-comments-arrivals.test.ts drives (copied here, as the sibling modules copy it). The Send confirm's
// accept option accepted every pending change, seen or not; the arrivals follow-on named the ones the person had not seen,
// and the user's ruling of the same day keeps the box but never accepts an unseen change. Built: the confirm's option names
// the pending changes the person has SEEN (a change whose card or mark was on screen at one of their gestures, or that the
// panel's first status held) and the unseen ones it leaves pending; the send accepts the seen ones BY ID through the same
// accept the card's button uses, never an accept-all; with nothing seen the box is unchecked and disabled and the send
// accepts nothing; the count in the message is the accept reply's; a change seen by a gesture while the confirm is up moves
// to the seen side in place and on the re-render. The numbers a real engine measures are
// file-comments-send-seen-browser.test.ts. Synthetic fixtures only: the notes-api world, placeholder ids, the session
// names "api" and "web".
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

// ── the seen-only accept ──────────────────────────────────────────────────────────────────────────
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

test("two seen and one unseen: the option names the two it accepts and the one it leaves, checked by default; the send accepts the two BY ID (no accept-all), the message counts what the reply accepted, and the third is still pending in the status after", async (t) => {
  const { w, ok, last } = await open(t, textWorld(), twoSeen());
  await land(w, ok, oneUnseen());
  assert.equal(lineOf(w)!.textContent, "api made 1 change since you last looked", "the fixture: the third change is an arrival");
  actIn(w.aside(), "fcsend")!.click();
  assert.equal(acceptWords(w), "accept the 2 pending changes you have seen (1 unseen stays pending)");
  assert.equal(acceptBox(w).checked, true, "checked by default (decision 8)");
  assert.equal(acceptBox(w).disabled, false);
  assert.ok(w.aside().querySelectorAll(".fc-confirm li").some((li) => li.textContent === "2 accepted, 0 rejected"), "the list counts the two the send will accept");
  actIn(w.aside(), "fcsendgo")!.click(); await tick();
  const acc = last();
  assert.equal(acc.type, "fileComments");
  assert.equal(acc.verb, "accept", "the accept the card's button uses (before: accept-all)");
  assert.deepEqual(acc.args, { ids: ["h1", "hb"] }, "the seen changes' ids, in the hunks' order; the unseen one is not among them");
  assert.ok(!verbs(w).includes("accept-all"), "no accept-all from the send");
  await ok({ ...afterAccept(), accepted: ["h1", "hb"] } as unknown as Status);
  const msg = last();
  assert.equal(msg.type, "fileCommentsSend", "then the send");
  assert.equal(msg.accepted, 2, "what the reply accepted");
  assert.equal(msg.rejected, 0);
  await sentOk(w);
  await ok(afterAccept());
  assert.ok(w.card(CHG2), "the unseen change's card is still in the list");
  assert.equal(w.card(CHG), null, "the seen one's is gone");
  assert.equal(w.card("chg:hb"), null);
  assert.ok(isNew(w.card(CHG2)), "and it is still an arrival, its dot on");
  assert.match(w.aside().querySelector(".fc-sent")!.textContent, /^Sent to api at [^·]+$/);
  w.close();
});

test("the message's count is the reply's, not the confirm's: a reply listing one accepted change makes a message that says one", async (t) => {
  const { w, ok, last } = await open(t, textWorld(), twoSeen());
  await land(w, ok, oneUnseen());
  actIn(w.aside(), "fcsend")!.click();
  actIn(w.aside(), "fcsendgo")!.click(); await tick();
  assert.deepEqual(last().args, { ids: ["h1", "hb"] });
  await ok({ ...afterAccept(), accepted: ["h1"] } as unknown as Status);
  assert.equal(last().type, "fileCommentsSend");
  assert.equal(last().accepted, 1, "the reply's count (the confirm said 2)");
  await sentOk(w);
  w.close();
});

test("every pending change unseen: the option says so, the box is unchecked and disabled, and the send makes no accept call; the message carries the log's own decisions only", async (t) => {
  const { w, ok, last } = await open(t, textWorld(), nonePending());
  await land(w, ok, twoUnseen());
  assert.equal(lineOf(w)!.textContent, "api made 2 changes since you last looked");
  actIn(w.aside(), "fcsend")!.click();
  assert.equal(acceptWords(w), "accept the pending changes you have seen (all 2 pending changes are unseen; nothing is accepted until you look)");
  assert.equal(acceptBox(w).checked, false, "unchecked (before: checked, and the send accepted both)");
  assert.equal(acceptBox(w).disabled, true, "and disabled: there is nothing it may accept");
  assert.ok(!w.aside().querySelectorAll(".fc-confirm li").some((li) => li.textContent.includes("accepted")), "the list counts no accept");
  const before = verbs(w).length;
  actIn(w.aside(), "fcsendgo")!.click(); await tick();
  assert.equal(verbs(w).length, before, "no accept, no accept-all: the send goes straight out");
  const msg = last();
  assert.equal(msg.type, "fileCommentsSend");
  assert.equal(msg.accepted, 0);
  await sentOk(w);
  await ok(twoUnseen());
  assert.ok(w.card(CHG2) && w.card("chg:hc"), "both changes still pending");
  w.close();
});

test("the option's default is the person's choice: unchecked by them, the send accepts nothing even with seen changes", async (t) => {
  const { w, ok, last } = await open(t, textWorld(), twoSeen());
  actIn(w.aside(), "fcsend")!.click();
  assert.equal(acceptWords(w), "accept the 2 pending changes you have seen", "nothing unseen: no parenthesis");
  const cb = acceptBox(w);
  cb.checked = false; dispatch(cb, new Ev("change"));
  const before = verbs(w).length;
  actIn(w.aside(), "fcsendgo")!.click(); await tick();
  assert.equal(verbs(w).length, before, "no accept");
  assert.equal(last().type, "fileCommentsSend");
  assert.equal(last().accepted, 0);
  await sentOk(w);
  await ok(twoSeen());
  w.close();
});

test("a change seen by a gesture while the confirm is up moves to the seen side: the option's words and count follow in place, and the confirm re-rendered says the same", async (t) => {
  const { w, ok } = await open(t, textWorld(), twoSeen());
  await land(w, ok, oneUnseen());
  actIn(w.aside(), "fcsend")!.click();
  assert.equal(acceptWords(w), "accept the 2 pending changes you have seen (1 unseen stays pending)");
  scrollBody(w, 340); gesture(w.body, "wheel");        // the row-7 change's card is in the box now: seen by the wheel
  assert.equal(acceptWords(w), "accept the 3 pending changes you have seen", "in place, no render");
  assert.equal(acceptBox(w).checked, true);
  assert.equal(lineOf(w), null, "the arrivals line went with it");
  actIn(w.aside(), "fcsendcancel")!.click();
  actIn(w.aside(), "fcsend")!.click();
  assert.equal(acceptWords(w), "accept the 3 pending changes you have seen", "the re-render agrees");
  actIn(w.aside(), "fcsendgo")!.click(); await tick();
  assert.deepEqual(w.posted[w.posted.length - 1].args, { ids: ["h1", "hb", "h2"] }, "the send accepts all three");
  await ok({ ...status({ store: { v: 3, path: "docs/report.md", suggestions: [], comments: COMMENTS }, hunks: [], storeMtimeNs: "1757145600000000005", unsent: { comments: [passage.id], replies: [], accepted: 3, rejected: 0, watermark: null } }), accepted: ["h1", "hb", "h2"] } as unknown as Status);
  assert.equal(w.posted[w.posted.length - 1].accepted, 3);
  await sentOk(w);
  w.close();
});

test("with nothing seen, the first change a gesture brings into view turns the disabled box on, checked (the default) — in place and on the re-render; the send then accepts that one alone", async (t) => {
  const { w, ok, last } = await open(t, textWorld(), nonePending());
  await land(w, ok, twoUnseen());
  actIn(w.aside(), "fcsend")!.click();
  assert.equal(acceptBox(w).disabled, true);
  scrollBody(w, 340); gesture(w.body, "wheel");        // row 7's card is in the box; row 13's is not
  assert.equal(acceptWords(w), "accept the 1 pending change you have seen (1 unseen stays pending)", "in place");
  assert.equal(acceptBox(w).disabled, false, "the box comes on");
  assert.equal(acceptBox(w).checked, true, "checked: decision 8's default, kept while the box was off");
  actIn(w.aside(), "fcsendcancel")!.click();
  actIn(w.aside(), "fcsend")!.click();
  assert.equal(acceptWords(w), "accept the 1 pending change you have seen (1 unseen stays pending)");
  assert.equal(acceptBox(w).disabled, false);
  assert.equal(acceptBox(w).checked, true);
  actIn(w.aside(), "fcsendgo")!.click(); await tick();
  assert.equal(last().verb, "accept");
  assert.deepEqual(last().args, { ids: ["h2"] });
  await ok({ ...status({ store: { v: 3, path: "docs/report.md", suggestions: sug(hunkC), comments: COMMENTS }, hunks: [hunkC], storeMtimeNs: "1757145600000000005", unsent: { comments: [passage.id], replies: [], accepted: 1, rejected: 0, watermark: null } }), accepted: ["h2"] } as unknown as Status);
  assert.equal(last().accepted, 1);
  await sentOk(w);
  w.close();
});

test("a person's own uncheck survives the disabled state: unchecked, then every seen change decided elsewhere, then a look — the box comes on unchecked", async (t) => {
  const { w, ok } = await open(t, textWorld(), twoSeen());
  actIn(w.aside(), "fcsend")!.click();
  const cb = acceptBox(w);
  cb.checked = false; dispatch(cb, new Ev("change"));
  actIn(w.aside(), "fcsendcancel")!.click();
  await land(w, ok, status({ store: { v: 3, path: "docs/report.md", suggestions: sug(hunk2), comments: COMMENTS }, hunks: [hunk2], storeMtimeNs: "1757145600000000004" }));   // the two seen decided from the cards, the third landed
  actIn(w.aside(), "fcsend")!.click();
  assert.equal(acceptBox(w).disabled, true, "all unseen");
  assert.equal(acceptBox(w).checked, false);
  scrollBody(w, 340); gesture(w.body, "wheel");
  assert.equal(acceptBox(w).disabled, false);
  assert.equal(acceptBox(w).checked, false, "their choice, not the default");
  w.close();
});

test("at source: doSend's accept is the by-id accept over the seen split, after the send's own gesture, and no accept-all; the option and the in-place update share syncAcceptOption; the render's option is the seen split's", () => {
  const send = SRC.slice(SRC.indexOf("async doSend(): Promise<void> {"), SRC.indexOf("private async sendOnce("));
  assert.ok(send.includes('this.gesture();                                    // a send is a gesture'), "the send's gesture");
  assert.ok(send.indexOf("this.gesture();") < send.indexOf("const acceptIds = this.sendOpts.accept ? this.pendingSplit(s).seen.map((h) => String(h.id)) : [];"), "the split is read after the gesture");
  assert.ok(send.includes('const a = await this.mutate("accept", { ids: acceptIds }, "send");'), "by id, through mutate (the card's fcaccept path)");
  assert.ok(!send.includes('"accept-all"'), "no accept-all in the send");
  assert.ok(send.includes("accepted = decided.length;"), "the count is the reply's");
  assert.ok(send.includes("const counts = sendCounts(parts, acceptIds.length > 0, accepted);"));
  assert.ok(SRC.includes('fcaccept: (x, ev) => { ev.stopPropagation(); void this.mutate("accept", { ids: [x.dataset.id!] }, "change:" + x.dataset.id!); },'), "the same verb and args shape the card uses");
  assert.ok(SRC.includes("if (split.seen.length + split.unseen.length) opts.appendChild(this.acceptOption(s));"), "renderSend's option");
  assert.ok(SRC.includes("if (cb && this.status) this.syncAcceptOption(cb, this.status);"), "reflectSeen's in-place update");
  const sync = SRC.slice(SRC.indexOf("private syncAcceptOption("), SRC.indexOf("private todoOpts("));
  assert.ok(sync.includes("cb.disabled = split.seen.length === 0;"));
  assert.ok(sync.includes("cb.checked = split.seen.length > 0 && this.sendOpts.accept;"));
  assert.ok(!sync.includes("resolvedByAccept"), "an accept resolves no comment (decision 42): no resolve count on the option");
  assert.ok(!/setTimeout|setInterval|Date\.now/.test(SRC.slice(SRC.indexOf("private pendingSplit("), SRC.indexOf("private todoOpts("))), "no timer: seen is the gesture's");
});

test("vocabulary: this module's own prose says a change's old and new text, file comment and run of turns; the words CONTEXT.md sets aside appear nowhere in it, nor the banned sessions-pane word, nor a home path", () => {
  const own = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "file-comments-send-seen.test.ts"), "utf8")
    .replace(/\n\/\/ ── the seen-only accept[\s\S]*$/, (m) => m);
  const prose = own.split("\n").filter((l) => l.trim().startsWith("//") || /^test\(/.test(l)).join("\n");
  assert.doesNotMatch(prose, /\bfleet\b/i);
  assert.doesNotMatch(prose, /\b(suggestion|diff|annotation)\b/i);
  assert.doesNotMatch(own, /\/home\/[a-z]/, "no home path");
});

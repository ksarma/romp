// The recurring-passage tie-break, reviewed (2026-09-11; plans/file-review.md, decision 51 and the anchors follow-on note).
// Two findings on the panel's half. (1) The words for a guessed copy end by asking the person to reveal it and save again
// from the right copy, but the card offered Reveal only for a passage it could not paint, and a guessed copy IS painted
// (in the dashed cue), so the open card's actions were Reply and Resolve alone: the words named a button the card did not
// have. Now a guessed copy's card offers Reveal too, which switches to Raw and scrolls to the guessed copy, and its title
// says what the save does (a new comment on the copy chosen; this card keeps its tag until it is resolved, as
// docs/guide.md says). (2) A copy the host confirmed at a place the view's text has since moved past (the poll's reload
// paints before the fresh status lands; a refused refresh keeps the old status) is painted as a guess nearest THAT place,
// the paint's hint, while the tag, the open card and the mark said it was the copy nearest the stored position, which
// can be another copy. The words now name the confirmed place in that state (PanelCard.confirmedAt). Driven over the DOM
// stand-in file-comments-tiebreak.test.ts uses. Synthetic fixtures only: the notes-api world, placeholder ids.
import { test, type TestContext } from "node:test";
import * as assert from "node:assert/strict";
import { inspect } from "node:util";
import { assertHiddenEvent, hideEdges, staysEnumerable } from "../test-dom-shim";
import type { FileViewActionCtx, TrackedEdit } from "./file-view";
import type { Status, StoreComment } from "./file-comments-model";
import { locateComment, makeAnchor } from "./anchor-map";

// ── a DOM stand-in: ancestry, attributes, events with capture and bubbling, a small selector engine ──
class Ev {
  target: El | Txt | null = null;
  currentTarget: El | null = null;
  defaultPrevented = false;
  stopped = false;
  key: string;
  ctrlKey: boolean; metaKey: boolean;
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
/** Comma groups of descendant chains (`A B`), each link a compound `tag.class[attr="v"]`. */
function parseSel(sel: string): Compound[][] {
  return sel.split(",").map((g) => g.trim()).filter(Boolean).map((g) => g.split(/\s+/).map((s) => {
    const m = /^([a-zA-Z][\w-]*)?((?:\.[\w-]+)*)((?:\[[\w-]+(?:="[^"]*")?\])*)$/.exec(s);
    if (!m) throw new Error("stand-in: unsupported selector " + s);
    const classes = (m[2].match(/\.[\w-]+/g) || []).map((c) => c.slice(1));
    const attrs: Array<[string, string | null]> = [];
    for (const a of m[3].match(/\[[^\]]+\]/g) || []) { const am = /^\[([\w-]+)(?:="([^"]*)")?\]$/.exec(a)!; attrs.push([am[1], am[2] ?? null]); }
    return { tag: m[1] ? m[1].toUpperCase() : null, classes, attrs };
  }));
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
  style: Record<string, string> = {};
  rect = { left: 0, top: 0, right: 0, bottom: 0, width: 0, height: 0 };
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
  get tabIndex(): number { return this.attrs.has("tabindex") ? Number(this.attrs.get("tabindex")) : -1; }
  set tabIndex(v: number) { this.attrs.set("tabindex", String(v)); }
  dataset: Record<string, string> = new Proxy({} as Record<string, string>, {
    get: (_, k) => this.attrs.get("data-" + kebab(String(k))) as string,
    set: (_, k, v) => { this.attrs.set("data-" + kebab(String(k)), String(v)); return true; },
    has: (_, k) => this.attrs.has("data-" + kebab(String(k))),
    deleteProperty: (_, k) => { this.attrs.delete("data-" + kebab(String(k))); return true; },
  });
  get textContent(): string { return this.childNodes.map((c) => c.textContent).join(""); }
  set textContent(v: string) { for (const c of this.childNodes) c.parentNode = null; this.childNodes.length = 0; if (v !== "") this.appendChild(new Txt(v)); }
  private detach(n: El | Txt): void { const p = n.parentNode; if (p) { const i = p.childNodes.indexOf(n); if (i >= 0) p.childNodes.splice(i, 1); n.parentNode = null; } }
  appendChild<T extends El | Txt>(n: T): T { this.detach(n); this.childNodes.push(n); n.parentNode = this; return n; }
  insertBefore<T extends El | Txt>(n: T, ref: El | Txt | null): T {
    if (!ref) return this.appendChild(n);
    this.detach(n);
    const i = this.childNodes.indexOf(ref);
    this.childNodes.splice(i < 0 ? this.childNodes.length : i, 0, n); n.parentNode = this; return n;
  }
  removeChild<T extends El | Txt>(n: T): T { this.detach(n); return n; }
  replaceChildren(...c: Array<El | Txt>): void { for (const x of this.childNodes) x.parentNode = null; this.childNodes.length = 0; for (const x of c) this.appendChild(x); }
  remove(): void { this.detach(this); }
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
  focus(): void { doc.activeElement = this; }
  blur(): void { if (doc.activeElement === this) doc.activeElement = null; }
  scrollIntoView(): void { /* inert */ }
  getBoundingClientRect(): typeof this.rect { return this.rect; }
  get offsetWidth(): number { return 0; }
}
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
/** The DOM event path: document capture, ancestors' capture root→target, target and ancestors' bubble, document bubble. */
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
  for (const n of chain) if (run(n.listeners, false, n)) return !ev.defaultPrevented;
  run(doc.listeners, false, null);
  return !ev.defaultPrevented;
}
const win: any = new EventTarget();
win.parent = win; win.innerWidth = 1200; win.innerHeight = 800;
let selection: any = null;
win.getSelection = () => selection;
win.confirm = () => true;
(globalThis as any).window = win;
(globalThis as any).document = doc;
const store = new Map<string, string>();
(globalThis as any).localStorage = {
  getItem: (k: string) => (store.has(k) ? store.get(k)! : null),
  setItem: (k: string, v: string) => { store.set(k, String(v)); },
  removeItem: (k: string) => { store.delete(k); },
};



// ── fixtures: the notes-api world, a report whose paragraph recurs, and one whose sentence does ───
const SID = "11111111-2222-3333-4444-555555555555";
const ABS = "/repo/notes-api/docs/report.md";
const ROOT = "/repo/notes-api";
const STORE_PATH = ROOT + "/.trackchanges/docs%2Freport.md.json";
const T0 = 1757145600000;
// one paragraph, over a thousand characters, three times: a phrase in its middle has the same surroundings for more
// than the host's widening cap (480 characters) on both sides of every copy, so every anchor on it ties
const PARA = ("The quick brown fox jumps over the lazy dog. ".repeat(12)
  + "Here is the marker phrase to comment on. "
  + "Pack my box with five dozen liquor jugs. ".repeat(12)).trim();
const DOC = "# Report\n\n" + PARA + "\n\n" + PARA + "\n\n" + PARA + "\n";
const MARKER = "the marker phrase";
const FIRST = DOC.indexOf(MARKER);
const SECOND = DOC.indexOf(MARKER, FIRST + 1);
const THIRD = DOC.indexOf(MARKER, SECOND + 1);
assert.ok(FIRST > 0 && SECOND > FIRST && THIRD > SECOND, "the fixture has three copies");
const RANGE = { start: SECOND, end: SECOND + MARKER.length };
const GAP = SECOND - FIRST;
// the session's paragraph, inserted above the first copy, longer than half the gap between copies: the engine's nearest
// tied hit to the OLD position is the first copy
const INSERTED = "The session added this paragraph meanwhile. ".repeat(13).trim();
const ABOVE = "# Report\n\n" + INSERTED + "\n\n" + PARA + "\n\n" + PARA + "\n\n" + PARA + "\n";
const SHIFT = ABOVE.length - DOC.length;
assert.ok(SHIFT > GAP / 2, "the insertion is longer than half the gap: nearest-wins picks the other copy");
// an edit in the second paragraph, inside the anchor's context before the passage: that copy's anchor breaks, the others
// still match in whole, and the position names none of them
const NEAR = DOC.slice(0, SECOND - "Here is ".length) + "Here, then, is " + DOC.slice(SECOND);
// a report whose passage is unique, and the same with the paragraph inserted above it
const UNIQ = "# Report\n\nAlpha line.\n\nThe unique passage here.\n\nOmega line.\n";
const UPHRASE = "unique passage";
const URANGE = { start: UNIQ.indexOf(UPHRASE), end: UNIQ.indexOf(UPHRASE) + UPHRASE.length };
const UNIQ_ABOVE = "# Report\n\n" + INSERTED + "\n\n" + UNIQ.slice("# Report\n\n".length);
// the anchor the host stores at its cap for the second copy (engine.makeAnchor with 480 characters of context)
const CAP_ANCHOR = { quote: MARKER, prefix: DOC.slice(SECOND - 480, SECOND), suffix: DOC.slice(SECOND + MARKER.length, SECOND + MARKER.length + 480) };
const onSecond: StoreComment = {
  id: T0 + "-" + SECOND, author: "you", ts: T0, body: "Say it once.", anchor: CAP_ANCHOR, anchorAt: SECOND, replies: [], resolved: false,
};
// a report whose closing sentence recurs, once per day (the shape of tests/fixtures/file_comments/report.md)
const SHIP = "Ship it.";
const REPORT = "# Latency report\n\n## Findings\n\nThe api session cut p95 latency by 40% after enabling the response cache.\n"
  + "Cold starts remain slow on the first request of the day.\n\n## Recommendation\n\nWe recommend shipping the cache in v1.2.\n\n"
  + "## Checks\n\n- retry on timeout\n- retry on timeout\n- retry on timeout\n- retry on timeout\n\n"
  + "## Day 1\n\nThe tests pass on every supported platform. Ship it.\nNo regressions were seen in the nightly run.\n\n"
  + "## Day 2\n\nThe tests pass on every supported platform. Ship it.\nNo regressions were seen in the nightly run.\n";
const DAY1 = REPORT.indexOf(SHIP);
const DAY2 = REPORT.indexOf(SHIP, DAY1 + 1);
assert.ok(DAY1 > 0 && DAY2 > DAY1 && REPORT.indexOf(SHIP, DAY2 + 1) === -1, "the sentence recurs exactly twice");
const DAY2_ROW = 25;   // the rows: Day 1's sentence is row 20, Day 2's row 25
const SOON = REPORT.slice(0, DAY2) + "Ship it soon." + REPORT.slice(DAY2 + SHIP.length);   // the session's rewrite of Day 2's sentence
// the panel's words, copied here so a swap or a rewording fails a driven test
// the panel's words, copied here so a swap or a rewording fails a driven test: both end by saying how to confirm the copy
const CONFIRM = " Reveal it and save again from the right copy to confirm.";
const UNSURE_POSITION = "This passage occurs in the file more than once with the same surroundings, and the position stored with the comment names none of the copies as the file is now, so the copy nearest that position is highlighted, not a confirmed one." + CONFIRM;
const UNSURE_NONE = "This passage occurs in the file more than once with the same surroundings, and the comment stores no position to tell the copies apart, so the first copy is highlighted, not a confirmed one." + CONFIRM;
const storeWith = (comments: StoreComment[]): Status["store"] => ({ v: 3, path: "docs/report.md", suggestions: [], comments });
function status(over: Partial<Status> = {}): Status {
  return {
    verb: "status", root: ROOT, storePath: STORE_PATH, trackedBy: null, agentTooling: "present",
    fileMtimeNs: "1757145600000000001", storeMtimeNs: "1757145600000000002", configMtimeNs: null,
    store: storeWith([]),
    hunks: [], log: [],
    unsent: { comments: [], replies: [], accepted: 0, rejected: 0, watermark: null },
    ...over,
  };
}

// ── the viewer stand-in: the body row with Raw rows, the seam as closures, the poll's HEAD answers ──
type World = {
  ctx: FileViewActionCtx; posted: any[]; main: El; body: El; code: El; actions: El;
  hooks: { rendered: Array<() => void>; selection: Array<(s: Selection) => void>; saved: Array<(i: { mtimeNs: string; logged: boolean }) => void>; close: Array<() => void> };
  disk: string; reloads: number; scrolls: number[]; modes: string[];
  mtimes: Record<string, string>; heads: string[];
  editing: boolean; tracked: TrackedEdit | null;    // the viewer's edit mode, and the panel's half of editing over pending changes (Slice 5)
  setText(src: string): void; close(): void;
};
let cur: World | null = null;
(globalThis as any).fetch = async (url: string) => {
  if (url.includes("/sessions")) return { json: async () => [] };
  const p = decodeURIComponent((/[?&]path=([^&]*)/.exec(url) || [])[1] || "");
  const w = cur!;
  w.heads.push(p);
  const mt = w.mtimes[p];
  return { status: mt === undefined ? 404 : 200, headers: { get: (h: string) => (h === "X-Romp-Mtime-Ns" && mt !== undefined ? mt : null) } };
};
/** The Raw view's rows, as codeBlock builds them: one `.fv-cl > .fv-ct` per line, a trailing newline being no line. */
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
function world(over: { path?: string; sid?: string | null; todoId?: string | null; src?: string } = {}): World {
  const main = new El("div"); main.className = "fileview-main";
  const body = new El("div"); body.className = "fileview-body";
  const actions = new El("div"); actions.className = "fileview-actions"; actions.appendChild(new Txt("Rendered · Raw"));
  const wrap = new El("div"); wrap.className = "fileview-code";
  const pre = new El("pre"); pre.className = "fileview-pre fileview-wrap";
  const code = new El("code"); code.className = "hljs";
  pre.appendChild(code); wrap.appendChild(pre);
  body.appendChild(actions); body.appendChild(wrap);
  main.appendChild(body);
  let text = over.src ?? DOC;
  const w = {
    posted: [] as any[], main, body, code, actions,
    hooks: { rendered: [] as Array<() => void>, selection: [] as Array<(s: Selection) => void>, saved: [] as Array<(i: { mtimeNs: string; logged: boolean }) => void>, close: [] as Array<() => void> },
    disk: text, reloads: 0, scrolls: [] as number[], modes: [] as string[], mtimes: {} as Record<string, string>, heads: [] as string[],
    editing: false, tracked: null,
  } as World;
  rows(code, text);
  w.setText = (s) => { text = s; rows(code, s); for (const cb of w.hooks.rendered) cb(); };   // the viewer's renderBody + fireRendered
  w.ctx = {
    path: over.path ?? ABS, sid: over.sid === undefined ? SID : over.sid, todoId: over.todoId ?? null,
    body: () => body as unknown as HTMLElement, mode: () => "raw", text: () => text, mtimeNs: () => "1757145600000000001", media: () => null, mediaElement: () => null, renderedImages: () => [], pdfPages: () => [],
    identity: () => ({ name: "api", color: null }),
    onRendered: (cb) => { w.hooks.rendered.push(cb); }, onSelection: (cb) => { w.hooks.selection.push(cb); },
    onSaved: (cb) => { w.hooks.saved.push(cb); }, onClose: (cb) => { w.hooks.close.push(cb); },
    post: (m) => { w.posted.push(m); }, ensureEditingAllowed: async () => true, setEditBlocked: () => { /* inert */ }, editing: () => w.editing, setTrackedEdit: (t) => { w.tracked = t; }, guardClose: () => { /* inert */ },   // the viewer's close ask (main, 2026-09-07): the stand-in asks nothing
    aside: (node) => { main.querySelector(".fileview-aside")?.remove(); if (node) { const n = node as unknown as El; n.classList.add("fileview-aside"); main.appendChild(n); } },
    setMode: (m) => { w.modes.push(m); }, scrollToOffset: (n) => { w.scrolls.push(n); },
    reload: () => { w.reloads++; w.setText(w.disk); },   // fetchFile: the bytes now on disk, repainted, the seam's onRendered fired
  };
  w.close = () => { for (const cb of w.hooks.close) cb(); if (cur === w) cur = null; };
  cur = w;
  return w;
}
const flush = () => new Promise<void>((r) => setImmediate(r));
const lastOf = (w: World, type: string, verb?: string) => [...w.posted].reverse().find((m) => m.type === type && (verb === undefined || m.verb === verb));
const countOf = (w: World, type: string, verb?: string) => w.posted.filter((m) => m.type === type && (verb === undefined || m.verb === verb)).length;
function answer(w: World, s: Status, m = lastOf(w, "fileComments", "status")): void {
  assert.ok(m, "a status ask is outstanding");
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId: m.reqId, ...s } }));
  // the poll's baseline follows the reply: the HEADs answer these mtimes until a test moves one
  w.mtimes[w.ctx.path] = s.fileMtimeNs;
  if (s.storePath && s.storeMtimeNs !== null) w.mtimes[s.storePath] = s.storeMtimeNs;
  if (s.root && s.configMtimeNs !== null) w.mtimes[s.root + "/.trackchanges/config.json"] = s.configMtimeNs;
}
function refuse(w: World, m: any, code: string, error: string): void {
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsFailed", reqId: m.reqId, verb: m.verb, code, error } }));
}
async function mount(w: World): Promise<{ unit: El; button: El }> {
  const fc = await import("./file-comments");
  const unit = fc.fileCommentsAction.mount(w.ctx) as unknown as El;
  return { unit, button: unit.childNodes[0] as El };
}
/** Mount, answer the probe, open the panel, answer its refresh: the panel as a person first sees it. */
async function openPanel(w: World, s: Status = status()): Promise<{ unit: El; button: El; aside: El }> {
  const { unit, button } = await mount(w);
  answer(w, s); await flush();
  button.click();
  answer(w, s); await flush();
  const aside = w.main.querySelector(".fileview-aside")!;
  assert.ok(aside, "the panel is mounted beside the body");
  return { unit, button, aside };
}


// ── the review's two legs: the guessed copy's Reveal, and the words for a confirmed place the view moved past ──

/** The status the host answers after a raw insertion above (ABOVE): the store as it stands, the position stale, and the
 *  tie-break's verdict for the comment. */
const placedAs = (at: number, confirmed: boolean, by: "ordinal" | "section" | "nearest", over: Partial<Status> = {}): Status =>
  status({ store: storeWith([onSecond]), placed: { [onSecond.id]: { at, confirmed, by } }, ...over });
const SECOND_ROW = 6;   // ABOVE's rows: title, blank, the inserted paragraph, blank, the first copy, blank, the second copy
const FIRST_ROW = 4;
/** The row (0-based line) a mark sits in: the `.fv-cl` ancestor's index among the code's rows. */
function rowOf(w: World, mark: El): number { return w.code.childNodes.indexOf(mark.closest(".fv-cl")!); }
const headOf = (aside: El, id: string): El => aside.querySelector('.fc-card[data-id="' + id + '"] .fc-card-head')!;
const tagsOf = (head: El): El[] => head.querySelectorAll(".fc-tag");
const openCard = (aside: El, id: string): El | null => aside.querySelector('.fc-card.open[data-id="' + id + '"]');
const buttonsOf = (card: El): string[] => card.querySelectorAll(".fc-actions button").map((b) => b.textContent);
const revealOf = (card: El): El | null => card.querySelector('[data-act="fcreveal"]');
const noteOf = (card: El): El | null => card.querySelector(".fc-note");
/** Open the comment's card and hand it back, with its head. */
function open(aside: El, id: string): { head: El; card: El } {
  const head = headOf(aside, id);
  head.click();
  const card = openCard(aside, id);
  assert.ok(card, "the card opens");
  return { head, card: card! };
}
// the panel's words for the third state (the stand-in above copies the other two), so a swap or a rewording fails a driven test
const UNSURE_CONFIRMED_PLACE = "This passage occurs in the file more than once with the same surroundings, and the place where the comment's copy was last confirmed names none of the copies as the file is now, so the copy nearest that place is highlighted, not a confirmed one." + CONFIRM;
const MARK_POSITION = "Open the comment; this passage recurs, and this copy is the nearest to the comment's stored position, not a confirmed one";
const MARK_CONFIRMED_PLACE = "Open the comment; this passage recurs, and this copy is the nearest to where the comment's copy was last confirmed, not a confirmed one";
const REVEAL_TAIL = "; a comment saved from the copy you mean is placed on that copy, and this one keeps its tag until you resolve it";
const revealTitle = (row: number): string => "Show this copy in the Raw view (line " + (row + 1) + ")" + REVEAL_TAIL;

test("a guessed copy (the host's verdict fell back to the nearest): the open card offers the Reveal its words name, beside Reply and Resolve; it switches to Raw and scrolls to the guessed copy, and its title says what the save does", async (t: TestContext) => {
  const w = world({ src: ABOVE }); t.after(() => w.close());
  const { aside } = await openPanel(w, placedAs(FIRST + SHIFT, false, "nearest"));
  const marks = w.code.querySelectorAll(".fc-hl");
  assert.equal(marks.length, 1);
  assert.equal(rowOf(w, marks[0]), FIRST_ROW, "the guessed copy, painted");
  const { head, card } = open(aside, onSecond.id);
  assert.equal(tagsOf(head)[0].title, UNSURE_POSITION);
  assert.equal(noteOf(card)!.textContent, UNSURE_POSITION, "the open card asks the person to reveal the copy and save again");
  assert.deepEqual(buttonsOf(card), ["Reply", "Resolve", "Reveal"], "and offers the Reveal the words name");
  const rv = revealOf(card)!;
  assert.equal(rv.title, revealTitle(FIRST_ROW), "the title names the Raw line, and says the save adds a comment on the chosen copy while this one keeps its tag");
  const modes = w.modes.length, scrolls = w.scrolls.length;
  rv.click();
  assert.deepEqual(w.modes.slice(modes), ["raw"], "Reveal switches to Raw");
  assert.deepEqual(w.scrolls.slice(scrolls), [FIRST + SHIFT], "and scrolls to the guessed copy, the one highlighted, where the other copies are near it");
});

test("no verdict (an older host) and a comment with no position: guessed copies both, and both cards offer Reveal", async (t: TestContext) => {
  const w = world({ src: ABOVE }); t.after(() => w.close());
  const { aside } = await openPanel(w, status({ store: storeWith([onSecond]) }));
  const { card } = open(aside, onSecond.id);
  assert.equal(noteOf(card)!.textContent, UNSURE_POSITION);
  assert.deepEqual(buttonsOf(card), ["Reply", "Resolve", "Reveal"]);
  assert.equal(revealOf(card)!.title, revealTitle(FIRST_ROW));
  w.close();
  const w2 = world(); t.after(() => w2.close());
  const { anchorAt: _at, ...withoutAt } = onSecond;
  const { aside: aside2 } = await openPanel(w2, status({ store: storeWith([withoutAt as StoreComment]), placed: {} }));
  const { card: card2 } = open(aside2, onSecond.id);
  assert.equal(noteOf(card2)!.textContent, UNSURE_NONE);
  assert.deepEqual(buttonsOf(card2), ["Reply", "Resolve", "Reveal"]);
  assert.equal(revealOf(card2)!.title, revealTitle(2), "the engine's earliest tie is DOC's first copy, row 2");
});

test("a copy the host confirmed paints plainly and its card offers no Reveal (nothing to reveal: the copy is painted and vouched for); a resolved comment offers none either", async (t: TestContext) => {
  const w = world({ src: ABOVE }); t.after(() => w.close());
  const { aside } = await openPanel(w, placedAs(SECOND + SHIFT, true, "ordinal"));
  const { head, card } = open(aside, onSecond.id);
  assert.deepEqual(tagsOf(head), [], "no tag");
  assert.equal(noteOf(card), null, "no note");
  assert.deepEqual(buttonsOf(card), ["Reply", "Resolve"], "no Reveal: the words that name it are not on this card");
  w.close();
  const w2 = world({ src: ABOVE }); t.after(() => w2.close());
  const { aside: aside2 } = await openPanel(w2, status({ store: storeWith([{ ...onSecond, resolved: true }]), placed: { [onSecond.id]: { at: FIRST + SHIFT, confirmed: false, by: "nearest" } } }));
  assert.equal(w2.code.querySelectorAll(".fc-hl").length, 0, "a resolved comment paints nothing");
  const fold = aside2.querySelector('[data-act="fcresolved"]');
  if (fold) fold.click();
  const head2 = headOf(aside2, onSecond.id);
  assert.ok(head2, "the resolved card is listed");
  head2.click();
  const card2 = openCard(aside2, onSecond.id);
  assert.ok(card2, "the resolved card opens");
  assert.equal(revealOf(card2!), null, "no Reveal on a resolved comment: it is not painted, and not a guess either");
  assert.deepEqual(tagsOf(head2).map((x) => x.textContent), ["resolved"]);
});

test("a unique passage is painted plainly and its card offers no Reveal: the guessed copy's Reveal is for a guess alone", async (t: TestContext) => {
  const w = world({ src: UNIQ }); t.after(() => w.close());
  const unique: StoreComment = { id: T0 + "-" + URANGE.start, author: "you", ts: T0, body: "Once.", anchor: makeAnchor(UNIQ, URANGE), anchorAt: URANGE.start, replies: [], resolved: false };
  const { aside } = await openPanel(w, status({ store: storeWith([unique]) }));
  const marks = w.code.querySelectorAll(".fc-hl");
  assert.equal(marks.length, 1);
  assert.equal(marks[0].textContent, UPHRASE);
  assert.equal(marks[0].classList.contains("fc-hl-context"), false);
  const { head, card } = open(aside, unique.id);
  assert.deepEqual(tagsOf(head), []);
  assert.deepEqual(buttonsOf(card), ["Reply", "Resolve"]);
});

test("a confirmed place the view's text moved past: the copy nearest THAT place is painted as a guess, and the tag, the open card and the mark say so in those words, not as the copy nearest the stored position, which is another copy; the card offers Reveal", async (t: TestContext) => {
  const w = world({ src: ABOVE }); t.after(() => w.close());
  const { aside } = await openPanel(w, placedAs(SECOND + SHIFT + 5, true, "ordinal"));
  const marks = w.code.querySelectorAll(".fc-hl");
  assert.equal(marks.length, 1);
  assert.equal(rowOf(w, marks[0]), SECOND_ROW, "the copy nearest the host's confirmed place (the engine's nearest-wins from the hint)");
  assert.ok(marks[0].classList.contains("fc-hl-context"), "as a guess: the place names no copy of this text");
  assert.equal(marks[0].title, MARK_CONFIRMED_PLACE, "the mark says which place this copy is the nearest to");
  // the words the old branch would have used are false of this paint: the copy nearest the STORED position is the first
  assert.equal(locateComment(ABOVE, CAP_ANCHOR, SECOND).range!.start, FIRST + SHIFT, "nearest the stored position is the first copy, not the one painted");
  const { head, card } = open(aside, onSecond.id);
  assert.deepEqual(tagsOf(head).map((x) => x.textContent), ["passage recurs"]);
  assert.equal(tagsOf(head)[0].title, UNSURE_CONFIRMED_PLACE, "the tag's title names the confirmed place");
  assert.equal(noteOf(card)!.textContent, UNSURE_CONFIRMED_PLACE, "so does the open card");
  assert.deepEqual(buttonsOf(card), ["Reply", "Resolve", "Reveal"]);
  assert.equal(revealOf(card)!.title, revealTitle(SECOND_ROW));
  // the control: the same text and comment with no verdict paint the copy nearest the stored position, in the words for it
  w.close();
  const w2 = world({ src: ABOVE }); t.after(() => w2.close());
  const { aside: aside2 } = await openPanel(w2, status({ store: storeWith([onSecond]) }));
  const marks2 = w2.code.querySelectorAll(".fc-hl");
  assert.equal(rowOf(w2, marks2[0]), FIRST_ROW);
  assert.equal(marks2[0].title, MARK_POSITION);
  assert.equal(tagsOf(headOf(aside2, onSecond.id))[0].title, UNSURE_POSITION);
});

test("the poll's path to that state: a confirmed copy painted plainly, then a raw write above reloads the view before the fresh status lands, and the interim paint is a guess nearest the confirmed place, said as one; the fresh status paints it plainly again", async (t: TestContext) => {
  const w = world({ src: ABOVE }); t.after(() => w.close());
  const { aside } = await openPanel(w, placedAs(SECOND + SHIFT, true, "ordinal"));
  assert.equal(rowOf(w, w.code.querySelectorAll(".fc-hl")[0]), SECOND_ROW, "confirmed: painted plainly on the second copy");
  assert.deepEqual(tagsOf(headOf(aside, onSecond.id)), []);
  // a second raw insertion above, shorter than half the gap: the copies move down two rows, and the confirmed place
  // (SECOND + SHIFT) now sits in the inserted text nearest the second copy, while the stored position (SECOND) is
  // still nearest the first; the viewer reloads the bytes (the poll's askReload) and the panel paints over them with
  // the status it has
  const LINE = "One more line above.\n\n";
  const AGAIN = "# Report\n\n" + LINE + ABOVE.slice("# Report\n\n".length);
  const AGAIN_SECOND = AGAIN.indexOf(MARKER, AGAIN.indexOf(MARKER) + 1);
  assert.ok(LINE.length < GAP / 2, "the shift is short: nearest-wins from the confirmed place keeps the second copy");
  w.disk = AGAIN; w.ctx.reload();
  const marks = w.code.querySelectorAll(".fc-hl");
  assert.equal(marks.length, 1);
  assert.equal(rowOf(w, marks[0]), SECOND_ROW + 2, "the second copy still, two rows down");
  assert.equal(marks[0].textContent, MARKER);
  assert.ok(marks[0].classList.contains("fc-hl-context"), "but a guess now: the confirmed place names no copy of this text");
  assert.equal(marks[0].title, MARK_CONFIRMED_PLACE);
  assert.equal(locateComment(AGAIN, CAP_ANCHOR, SECOND + SHIFT).range!.start, AGAIN_SECOND, "the copy nearest the confirmed place is the one painted");
  assert.equal(locateComment(AGAIN, CAP_ANCHOR, SECOND).range!.start, AGAIN.indexOf(MARKER), "the copy nearest the stored position is the first: the old words would have been false of the paint");
  const head = headOf(aside, onSecond.id);
  assert.deepEqual(tagsOf(head).map((x) => x.textContent), ["passage recurs"]);
  assert.equal(tagsOf(head)[0].title, UNSURE_CONFIRMED_PLACE);
  head.click();
  const card = openCard(aside, onSecond.id)!;
  assert.equal(noteOf(card)!.textContent, UNSURE_CONFIRMED_PLACE);
  assert.deepEqual(buttonsOf(card), ["Reply", "Resolve", "Reveal"]);
  // the fresh status: the host, over the new bytes, confirms the copy at its new place, and the paint is plain again
  w.close();
  const w2 = world({ src: AGAIN }); t.after(() => w2.close());
  const { aside: aside2 } = await openPanel(w2, placedAs(AGAIN_SECOND, true, "ordinal"));
  const marks2 = w2.code.querySelectorAll(".fc-hl");
  assert.equal(rowOf(w2, marks2[0]), SECOND_ROW + 2);
  assert.equal(marks2[0].classList.contains("fc-hl-context"), false);
  assert.deepEqual(tagsOf(headOf(aside2, onSecond.id)), []);
});

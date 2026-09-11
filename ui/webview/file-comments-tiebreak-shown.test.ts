// The tie-break's words for what the render shows (the review, round 3, 2026-09-11; plans/file-review.md, decision 51 and
// the anchors follow-on note). Two findings on the panel's half. (1) With the editor up (Slice 5), a guessed passage card
// kept the read view's words, which end by asking the person to Reveal the copy and save again, while the card offered
// Reply and Resolve alone (Reveal and the card links go with the read view): the words named a button the card did not
// have, the round-1 defect back for the editor state. Now the editor's words say the state without a paint (the editor
// shows no highlight of ours) and name the way there first: leave edit mode, then reveal it and save again. (2) In Raw, a
// region on an embed line that recurs kept the words for the view that shows its picture (draw a new region on the figure
// you mean; what Re-place does), while Raw renders no picture and the card offers no Re-place: the words now name the view
// that shows the image, as the stale-region words already did there. Driven over the DOM stand-in the recourse module
// uses (copied, as every module here copies it), with a viewer that flips into edit mode the way enterEdit does: begin()
// at the click, then the flip, then one onRendered. Synthetic fixtures only: the notes-api world, placeholder ids.
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

// ── the words for what the render shows: the editor, and a region in a view with no picture ──────────

// the panel's words, copied here so a swap or a rewording fails a driven test
const UNSURE_IN_EDITOR = "This passage occurs in the file more than once with the same surroundings, and as the file is now the copy this comment is on can only be guessed. ";
const PASSAGE_AFTER_EDIT = UNSURE_IN_EDITOR + "To confirm the copy, leave edit mode, then reveal it and save again from the right copy.";
const SAVE_FROM_COPY_NOTE = "A comment saved from the copy you mean is placed on that copy, and this one keeps its tag until you resolve it.";
const STATE_POSITION = "This passage occurs in the file more than once with the same surroundings, and the position stored with the comment names none of the copies as the file is now, so the copy nearest that position is highlighted, not a confirmed one.";
const REGION_CONFIRM = "To confirm the copy, draw a new region on the figure you mean; this comment keeps its tag until you resolve it. Re-place redraws the rectangle on the figure shown and does not move the comment to another figure. Drawing a region needs a mouse.";
const REGION_TAIL = "; this comment keeps its tag until you resolve it. Re-placing it there redraws the rectangle on the figure it is on and does not move the comment to another figure. Drawing a region needs a mouse.";
const REGION_UNSEEN = "To confirm the copy, draw a new region on the figure you mean in the view that shows the image" + REGION_TAIL;
const UNSURE_REGION_UNSEEN = STATE_POSITION + " " + REGION_UNSEEN;
const REGION_AFTER_EDIT = UNSURE_IN_EDITOR + "To confirm the copy, leave edit mode, then draw a new region on the figure you mean in the view that shows the image" + REGION_TAIL;
assert.equal(UNSURE_POSITION, STATE_POSITION + CONFIRM, "the read view's passage words, as the recourse module holds them");
const notesOf = (card: El): string[] => card.querySelectorAll(".fc-note").map((n) => n.textContent);
const refOf = (card: El): El => card.querySelector(".fc-card-head .fc-ref")!;
/** The viewer's Edit (enterEdit): the seam's begin() at the click, then the flip into edit mode, then the one onRendered
 *  the editor's mount fires, which is the paint that gives the cards their edit-mode state. */
function enterEdit(w: World): void { w.tracked!.begin(); w.editing = true; for (const cb of w.hooks.rendered) cb(); }
/** Cancel: the read view is back with the bytes on disk, and its paint follows. */
function leaveEdit(w: World): void { w.editing = false; w.setText(w.disk); }

// a report embedding one figure twice with the same long paragraphs around each (the region module's world): an anchor on
// either embed line, widened to the host's cap, has the same context at both copies
const H1 = "1111111111111111111111111111111111111111111111111111111111111111";
const BEFORE = "The quick brown fox jumps over the lazy dog. ".repeat(12).trim();
const AFTER = "Pack my box with five dozen liquor jugs. ".repeat(12).trim();
const EMBED = "![Latency](figs/p95.png)";
const BLOCK = BEFORE + "\n\n" + EMBED + "\n\n" + AFTER;
const FIG_DOC = "# Report\n\n" + BLOCK + "\n\n" + BLOCK + "\n";
const FIRST_EMBED = FIG_DOC.indexOf(EMBED);
const SECOND_EMBED = FIG_DOC.indexOf(EMBED, FIRST_EMBED + 1);
assert.ok(FIRST_EMBED > 0 && SECOND_EMBED > FIRST_EMBED && FIG_DOC.indexOf(EMBED, SECOND_EMBED + 1) === -1, "two embeds");
const EMBED_ANCHOR = { quote: EMBED, prefix: FIG_DOC.slice(SECOND_EMBED - 480, SECOND_EMBED), suffix: FIG_DOC.slice(SECOND_EMBED + EMBED.length, SECOND_EMBED + EMBED.length + 480) };
// the title edited, and nothing recorded it: both copies moved by the edit's length, and the stored position names neither
const FIG_REVISED = FIG_DOC.replace("# Report", "# Report, revised");
const FIG_SHIFT = FIG_REVISED.length - FIG_DOC.length;
assert.ok(FIG_SHIFT > 0 && FIG_SHIFT < (SECOND_EMBED - FIRST_EMBED) / 2, "the shift is small: the nearest tied copy to the old position is still the second");
assert.equal(locateComment(FIG_REVISED, EMBED_ANCHOR, SECOND_EMBED).range!.start, SECOND_EMBED + FIG_SHIFT, "nearest-wins from the stale position picks the second copy, a guess");
/** A REGION comment drawn on the second figure, as the host saved it: the anchor and position on the embed line, and the
 *  rectangle with the figure's hash (regionState reads it against the status's embeddedHashes: current). */
const regionOnSecond: StoreComment = {
  id: T0 + "-region", author: "you", ts: T0, body: "Crop the y axis.", anchor: EMBED_ANCHOR, anchorAt: SECOND_EMBED, replies: [], resolved: false,
  target: { kind: "image", region: { x: 0.1667, y: 0.2, w: 0.3333, h: 0.3 }, hash: H1, src: "figs/p95.png" } as StoreComment["target"],
};
const figStatus = (): Status => status({ store: storeWith([regionOnSecond]), embeddedHashes: { "figs/p95.png": H1 } });

test("editor up over a guessed passage: the words say the state without a paint and name the way there (leave edit mode, then reveal it and save again), not the Reveal and save the card lacks; the save's line stands under them; the read view's words and Reveal return when the edit ends", async (t: TestContext) => {
  const w = world({ src: ABOVE }); t.after(() => w.close());
  const { aside } = await openPanel(w, placedAs(FIRST + SHIFT, false, "nearest"));
  const { card } = open(aside, onSecond.id);
  assert.deepEqual(notesOf(card), [UNSURE_POSITION, SAVE_FROM_COPY_NOTE], "the read view: the ask, then what the save does");
  assert.deepEqual(buttonsOf(card), ["Reply", "Resolve", "Reveal"]);
  assert.ok(refOf(card).classList.contains("fc-link"), "and the reference is a link into the read view");
  enterEdit(w);
  const head = headOf(aside, onSecond.id);
  assert.deepEqual(tagsOf(head).map((x) => x.textContent), ["passage recurs"], "the state stays on the card: the copy is still a guess");
  assert.equal(tagsOf(head)[0].title, PASSAGE_AFTER_EDIT, "the tag's title names the way there");
  const editing = openCard(aside, onSecond.id)!;
  assert.deepEqual(notesOf(editing), [PASSAGE_AFTER_EDIT, SAVE_FROM_COPY_NOTE], "so does the open card, with the line saying what the save does, which names no control");
  assert.deepEqual(buttonsOf(editing), ["Reply", "Resolve"], "Reveal goes with the read view (Slice 5)");
  assert.equal(revealOf(editing), null);
  assert.equal(refOf(editing).classList.contains("fc-link"), false, "no link into a read view that is gone");
  assert.ok(!/Reveal/.test(notesOf(editing).join(" ")), "no control the card lacks is named");
  assert.ok(!/highlight/.test(PASSAGE_AFTER_EDIT) && !/position|place where/.test(PASSAGE_AFTER_EDIT), "no paint is claimed and no hint is named: the editor shows no highlight of ours");
  assert.ok(PASSAGE_AFTER_EDIT.includes("leave edit mode"), "the way there, in the Cancel button's own words");
  assert.ok(PASSAGE_AFTER_EDIT.endsWith("save again from the right copy."), "and then the save the guide describes");
  assert.deepEqual(w.modes, []); assert.deepEqual(w.scrolls, []);
  leaveEdit(w);
  const back = openCard(aside, onSecond.id)!;
  assert.deepEqual(notesOf(back), [UNSURE_POSITION, SAVE_FROM_COPY_NOTE]);
  assert.deepEqual(buttonsOf(back), ["Reply", "Resolve", "Reveal"]);
  assert.equal(tagsOf(headOf(aside, onSecond.id))[0].title, UNSURE_POSITION);
});

test("the editor names no hint: a comment with no verdict, one whose confirmed place the view moved past and one with no position wear the same words while editing, and each its own once the edit ends", async (t: TestContext) => {
  for (const [s, readWords] of [[status({ store: storeWith([onSecond]) }), UNSURE_POSITION], [placedAs(SECOND + SHIFT + 5, true, "ordinal"), UNSURE_CONFIRMED_PLACE]] as Array<[Status, string]>) {
    const w = world({ src: ABOVE }); t.after(() => w.close());
    const { aside } = await openPanel(w, s);
    assert.equal(tagsOf(headOf(aside, onSecond.id))[0].title, readWords, "the read view's words for this state");
    enterEdit(w);
    assert.equal(tagsOf(headOf(aside, onSecond.id))[0].title, PASSAGE_AFTER_EDIT, "one set of words in the editor");
    const { card } = open(aside, onSecond.id);
    assert.deepEqual(notesOf(card), [PASSAGE_AFTER_EDIT, SAVE_FROM_COPY_NOTE]);
    assert.deepEqual(buttonsOf(card), ["Reply", "Resolve"]);
    leaveEdit(w);
    assert.equal(tagsOf(headOf(aside, onSecond.id))[0].title, readWords, "and the state's own words again");
    w.close();
  }
  const w = world(); t.after(() => w.close());
  const { anchorAt: _at, ...withoutAt } = onSecond;
  const { aside } = await openPanel(w, status({ store: storeWith([withoutAt as StoreComment]), placed: {} }));
  assert.equal(tagsOf(headOf(aside, onSecond.id))[0].title, UNSURE_NONE);
  enterEdit(w);
  assert.equal(tagsOf(headOf(aside, onSecond.id))[0].title, PASSAGE_AFTER_EDIT);
});

test("a copy the host confirmed, and a unique passage: no tag and no note in the editor either, so the editor's words are for a guess alone", async (t: TestContext) => {
  const w = world({ src: ABOVE }); t.after(() => w.close());
  const { aside } = await openPanel(w, placedAs(SECOND + SHIFT, true, "ordinal"));
  const { card } = open(aside, onSecond.id);
  assert.deepEqual(notesOf(card), []);
  enterEdit(w);
  assert.deepEqual(tagsOf(headOf(aside, onSecond.id)), []);
  const editing = openCard(aside, onSecond.id)!;
  assert.deepEqual(notesOf(editing), []);
  assert.deepEqual(buttonsOf(editing), ["Reply", "Resolve"]);
  w.close();
  const w2 = world({ src: UNIQ }); t.after(() => w2.close());
  const unique: StoreComment = { id: T0 + "-" + URANGE.start, author: "you", ts: T0, body: "Once.", anchor: makeAnchor(UNIQ, URANGE), anchorAt: URANGE.start, replies: [], resolved: false };
  const { aside: aside2 } = await openPanel(w2, status({ store: storeWith([unique]) }));
  enterEdit(w2);
  assert.deepEqual(tagsOf(headOf(aside2, unique.id)), []);
  assert.deepEqual(notesOf(open(aside2, unique.id).card), []);
});

test("Raw view, a region on the second of two embeds after an unrecorded title edit: the embed line is the guess, and the words name the view that shows the image, not a figure this view lacks or the Re-place it does not offer; the pictured view's words are not these", async (t: TestContext) => {
  const w = world({ src: FIG_REVISED }); t.after(() => w.close());
  const { aside } = await openPanel(w, figStatus());
  const marks = w.code.querySelectorAll(".fc-hl");
  assert.equal(marks.length, 1);
  assert.equal(marks[0].textContent, EMBED, "the embed line stands in for the picture Raw does not show");
  assert.ok(marks[0].classList.contains("fc-hl-context"), "a guess: the dashed cue");
  assert.equal(marks[0].title, MARK_POSITION, "the mark's title is the read view's: this copy is the nearest to the stored position");
  const { head, card } = open(aside, regionOnSecond.id);
  assert.deepEqual(tagsOf(head).map((x) => x.textContent), ["passage recurs"]);
  assert.equal(tagsOf(head)[0].title, UNSURE_REGION_UNSEEN, "the tag's title: the state, then the recourse worded for a view with no picture");
  assert.deepEqual(notesOf(card), [UNSURE_REGION_UNSEEN], "the open card says the same, in one line");
  assert.deepEqual(buttonsOf(card), ["Reply", "Resolve"], "no picture: no Re-place; a region: no Reveal");
  assert.equal(revealOf(card), null);
  assert.equal(refOf(card).title, "Scroll to the region", "the reference reaches the embed line's highlight");
  assert.ok(REGION_UNSEEN.includes("draw a new region on the figure you mean in the view that shows the image"), "the way there, as the stale-region words name it in this view");
  assert.ok(!/\bRe-place\b/.test(REGION_UNSEEN) && !REGION_UNSEEN.includes("figure shown"), "no control this card lacks, no figure this view shows");
  assert.ok(REGION_UNSEEN.includes("does not move the comment to another figure") && REGION_UNSEEN.endsWith("Drawing a region needs a mouse."), "and the rest of a region's recourse as the pictured view says it: what re-placing does instead, and the pointer drawing takes");
  assert.notEqual(REGION_UNSEEN, REGION_CONFIRM, "the pictured view's words (the region module drives them) are not these");
  assert.ok(REGION_CONFIRM.includes("Re-place redraws the rectangle on the figure shown"), "which name the Re-place that card offers, over the figure it shows");
});

test("the same region with the editor up: the state without a paint, then leave edit mode and draw in the view that shows the image; the Raw words return with the read view", async (t: TestContext) => {
  const w = world({ src: FIG_REVISED }); t.after(() => w.close());
  const { aside } = await openPanel(w, figStatus());
  open(aside, regionOnSecond.id);
  enterEdit(w);
  const head = headOf(aside, regionOnSecond.id);
  assert.deepEqual(tagsOf(head).map((x) => x.textContent), ["passage recurs"]);
  assert.equal(tagsOf(head)[0].title, REGION_AFTER_EDIT);
  const card = openCard(aside, regionOnSecond.id)!;
  assert.deepEqual(notesOf(card), [REGION_AFTER_EDIT], "one line: no save line for a region");
  assert.deepEqual(buttonsOf(card), ["Reply", "Resolve"]);
  assert.ok(REGION_AFTER_EDIT.startsWith(UNSURE_IN_EDITOR + "To confirm the copy, leave edit mode, then draw a new region"), "the passage's state sentence, then the region's way there");
  leaveEdit(w);
  assert.equal(tagsOf(headOf(aside, regionOnSecond.id))[0].title, UNSURE_REGION_UNSEEN);
  assert.deepEqual(notesOf(openCard(aside, regionOnSecond.id)!), [UNSURE_REGION_UNSEEN]);
});

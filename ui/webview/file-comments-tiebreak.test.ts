// The recurring-passage tie-break in the panel (2026-09-11; plans/file-review.md, Commenting from either view, the anchors
// follow-on note and decision 51). The user saw a comment on a passage that recurs painted as a guess after the file
// changed under the panel in a way the host never recorded: the anchor matched several copies, the stored position named
// none, and the copy nearest that position wore the dashed cue and the "passage recurs" tag. The host now stores the copy's
// ordinal, the count of copies and the heading path beside the position, and every reply carries `placed`: for each such
// comment, where the tie-break put it and whether it confirmed the copy (the ordinal's copy while the count is unchanged,
// else the one copy under the stored heading path) or fell back to the nearest, a guess. Here: a confirmed copy is painted
// plainly, with no dashed cue, no tag and no note, on the copy the host names; a guessed one, or a comment the reply has no
// verdict for (an older host), is painted as before, and the words now end by saying how to confirm it. A confirmed
// position that names no copy of the view's text (the view moved on since the status) is not trusted, and the paint falls
// back to the guess it would have made. Driven over the DOM stand-in file-comments-anchors-unsure.test.ts uses. Synthetic
// fixtures only: the notes-api world, placeholder ids.
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



// ── fixtures: the notes-api world — a report whose paragraph recurs, and one whose sentence does ───
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


// ── driving the composer: a selection in one row, the float, Enter ─────────────────────────────────
const RECT = { left: 100, top: 200, right: 300, bottom: 220, width: 200, height: 20 };
function textNodeIn(root: El, needle: string): { node: Txt; at: number } | null {
  for (const c of root.childNodes) {
    if (c instanceof Txt) { const i = c.data.indexOf(needle); if (i >= 0) return { node: c, at: i }; }
    else { const r = textNodeIn(c, needle); if (r) return r; }
  }
  return null;
}
/** A selection of `quote` in the Raw view's row `row` (0-based), the way the person drags over the second paragraph. */
function selectRow(w: World, row: number, quote: string): any {
  const hit = textNodeIn(w.code.childNodes[row] as El, quote);
  assert.ok(hit, "row " + row + " holds " + JSON.stringify(quote));
  return { rangeCount: 1, isCollapsed: false, anchorNode: hit.node, anchorOffset: hit.at, focusNode: hit.node, focusOffset: hit.at + quote.length,
    toString: () => quote, getRangeAt: () => ({ getBoundingClientRect: () => RECT }) };
}
const theFloat = (): El => { const all = doc.body.querySelectorAll(".fc-float"); return all[all.length - 1]; };
/** Select `quote` in row `row`, let the seam fire, and press the floating Comment button. */
function startCommentInRow(w: World, row: number, quote: string): void {
  const sel = selectRow(w, row, quote);
  for (const cb of w.hooks.selection) cb(sel);
  const float = theFloat();
  assert.equal(float.hidden, false, "the float appears beside a selection in the body");
  selection = sel;
  float.click();
}
const input = (aside: El): El => aside.querySelector(".fc-input")!;
/** The save chord (Ctrl+Enter; Cmd+Enter is the same key policy): a plain Enter is a newline in the box now. */
const chord = (el: El) => dispatch(el, new Ev("keydown", { key: "Enter", ctrlKey: true }));
const preselRows = (w: World): Array<[number, string]> => w.code.querySelectorAll(".fc-presel").map((m) => [w.code.childNodes.indexOf(m.closest(".fv-cl")!), m.textContent] as [number, string]);
const tag = (aside: El): El | null => aside.querySelector(".fc-composer-ref .fc-tag");
/** The row (0-based line) a mark sits in: the `.fv-cl` ancestor's index among the code's rows. */
function rowOf(w: World, mark: El): number { return w.code.childNodes.indexOf(mark.closest(".fv-cl")!); }
const headOf = (aside: El, id: string): El => aside.querySelector('.fc-card[data-id="' + id + '"] .fc-card-head')!;
const tagsOf = (head: El): El[] => head.querySelectorAll(".fc-tag");

// ── followPassage: a passage the edit reached, whose text survives only at a copy the edit never touched ──

// ── the host's verdict: a confirmed copy paints plainly, a guessed one as before ──────────────────

/** The status the host answers after a raw insertion above (ABOVE): the store as it stands, the position stale, and the
 *  tie-break's verdict for the comment. */
const placedAs = (at: number, confirmed: boolean, by: "ordinal" | "section" | "nearest", over: Partial<Status> = {}): Status =>
  status({ store: storeWith([onSecond]), placed: { [onSecond.id]: { at, confirmed, by } }, ...over });
const SECOND_ROW = 6;   // ABOVE's rows: title, blank, the inserted paragraph, blank, the first copy, blank, the second copy
const FIRST_ROW = 4;

test("the host confirmed the copy (by the ordinal): the highlight lands on the second copy, plainly, with the plain title, no tag on the card and no note on the open card", async (t: TestContext) => {
  const w = world({ src: ABOVE }); t.after(() => w.close());
  const { aside } = await openPanel(w, placedAs(SECOND + SHIFT, true, "ordinal"));
  const marks = w.code.querySelectorAll(".fc-hl");
  assert.equal(marks.length, 1, "one highlight");
  assert.equal(marks[0].textContent, MARKER);
  assert.equal(rowOf(w, marks[0]), SECOND_ROW, "the copy the host named, not the nearest to the stale position");
  assert.equal(marks[0].classList.contains("fc-hl-context"), false, "no dashed cue: a confirmed copy");
  assert.equal(marks[0].title, "Open the comment on this passage");
  const head = headOf(aside, onSecond.id);
  assert.deepEqual(tagsOf(head), [], "no tag");
  head.click();
  assert.equal(aside.querySelector('.fc-card.open[data-id="' + onSecond.id + '"] .fc-note'), null, "no note on the open card");
  // the control: the same file and comment with no verdict paint the nearest copy as a guess (below)
});

test("the host confirmed the copy by its heading path: painted the same way, plainly on the named copy", async (t: TestContext) => {
  const w = world({ src: ABOVE }); t.after(() => w.close());
  const { aside } = await openPanel(w, placedAs(SECOND + SHIFT, true, "section"));
  const marks = w.code.querySelectorAll(".fc-hl");
  assert.equal(marks.length, 1);
  assert.equal(rowOf(w, marks[0]), SECOND_ROW);
  assert.equal(marks[0].classList.contains("fc-hl-context"), false);
  assert.deepEqual(tagsOf(headOf(aside, onSecond.id)), []);
});

test("the host fell back to the nearest copy (a guess): the dashed cue, the tag and the words, which end by saying how to confirm it; the mark's title is the unsure one", async (t: TestContext) => {
  const w = world({ src: ABOVE }); t.after(() => w.close());
  const { aside } = await openPanel(w, placedAs(FIRST + SHIFT, false, "nearest"));
  const marks = w.code.querySelectorAll(".fc-hl");
  assert.equal(marks.length, 1);
  assert.equal(rowOf(w, marks[0]), FIRST_ROW, "the nearest copy to the stale position, as the host said");
  assert.ok(marks[0].classList.contains("fc-hl-context"), "the dashed cue");
  assert.match(marks[0].title, /not a confirmed one$/);
  const head = headOf(aside, onSecond.id);
  assert.deepEqual(tagsOf(head).map((x) => x.textContent), ["passage recurs"]);
  assert.equal(tagsOf(head)[0].title, UNSURE_POSITION);
  assert.ok(UNSURE_POSITION.endsWith(" Reveal it and save again from the right copy to confirm."), "the words end with the sentence that says how to confirm");
  head.click();
  const note = aside.querySelector('.fc-card.open[data-id="' + onSecond.id + '"] .fc-note');
  assert.ok(note, "the open card says it in words");
  assert.equal(note!.textContent, UNSURE_POSITION);
});

test("no verdict in the status (an older host): painted as before, the nearest copy as a guess with the words; a comment with no position likewise, with its own words", async (t: TestContext) => {
  const w = world({ src: ABOVE }); t.after(() => w.close());
  const { aside } = await openPanel(w, status({ store: storeWith([onSecond]) }));
  const marks = w.code.querySelectorAll(".fc-hl");
  assert.equal(marks.length, 1);
  assert.equal(rowOf(w, marks[0]), FIRST_ROW);
  assert.ok(marks[0].classList.contains("fc-hl-context"));
  assert.equal(tagsOf(headOf(aside, onSecond.id))[0].title, UNSURE_POSITION);
  w.close();
  const w2 = world(); t.after(() => w2.close());
  const { anchorAt: _at, ...withoutAt } = onSecond;
  const { aside: aside2 } = await openPanel(w2, status({ store: storeWith([withoutAt as StoreComment]), placed: {} }));
  const marks2 = w2.code.querySelectorAll(".fc-hl");
  assert.equal(marks2.length, 1);
  assert.equal(rowOf(w2, marks2[0]), 2, "the engine's earliest tie");
  assert.ok(marks2[0].classList.contains("fc-hl-context"));
  assert.equal(tagsOf(headOf(aside2, onSecond.id))[0].title, UNSURE_NONE);
});

test("a confirmed position that names no copy of the view's text is not trusted as confirmed: the view moved on since the status, and the copy nearest the host's offset is painted as a guess, with the cue and the tag", async (t: TestContext) => {
  const w = world({ src: ABOVE }); t.after(() => w.close());
  const { aside } = await openPanel(w, placedAs(SECOND + SHIFT + 5, true, "ordinal"));
  const marks = w.code.querySelectorAll(".fc-hl");
  assert.equal(marks.length, 1);
  assert.equal(rowOf(w, marks[0]), SECOND_ROW, "the copy nearest the host's offset (the engine's nearest-wins from the hint)");
  assert.ok(marks[0].classList.contains("fc-hl-context"), "but as a guess, said as one: the offset names no copy of this text");
  assert.match(marks[0].title, /not a confirmed one$/);
  assert.deepEqual(tagsOf(headOf(aside, onSecond.id)).map((x) => x.textContent), ["passage recurs"]);
});

test("a BOM-prefixed file: the host's confirmed position runs one past the view's text, as anchorAt does, and is mapped by the status's bom before the copy is painted", async (t: TestContext) => {
  const w = world({ src: ABOVE }); t.after(() => w.close());
  const { aside } = await openPanel(w, placedAs(SECOND + SHIFT + 1, true, "ordinal", { bom: true, store: storeWith([{ ...onSecond, anchorAt: SECOND + 1 }]) }));
  const marks = w.code.querySelectorAll(".fc-hl");
  assert.equal(marks.length, 1);
  assert.equal(rowOf(w, marks[0]), SECOND_ROW, "mapped past the BOM, the position names the second copy");
  assert.equal(marks[0].classList.contains("fc-hl-context"), false);
  assert.deepEqual(tagsOf(headOf(aside, onSecond.id)), []);
});

test("a verdict of the wrong shape claims nothing: a non-numeric position or a missing confirmed bit is read as no verdict", async (t: TestContext) => {
  const w = world({ src: ABOVE }); t.after(() => w.close());
  const { aside } = await openPanel(w, status({ store: storeWith([onSecond]), placed: { [onSecond.id]: { at: "x", confirmed: true, by: "ordinal" } as unknown as NonNullable<Status["placed"]>[string] } }));
  const marks = w.code.querySelectorAll(".fc-hl");
  assert.equal(marks.length, 1);
  assert.equal(rowOf(w, marks[0]), FIRST_ROW);
  assert.ok(marks[0].classList.contains("fc-hl-context"));
  assert.deepEqual(tagsOf(headOf(aside, onSecond.id)).map((x) => x.textContent), ["passage recurs"]);
});

// The stand-in's nodes inspect as their own projection, never as the tree (ui/test-dom-shim.ts says why).
test("stand-in: a node enumerates its primitives alone and inspects without its edges", () => {
  const root = doc.createElement("div");
  const kid = root.appendChild(doc.createElement("span"));
  kid.appendChild(doc.createTextNode("leaf"));
  for (const n of [root, kid, kid.firstChild!]) {
    const o = n as unknown as Record<string, unknown>;
    assert.ok(Object.keys(o).every((k) => staysEnumerable(o[k])), "only primitives enumerate on " + n.constructor.name);
    const dump = inspect(n, { compact: false, customInspect: false, depth: 1000, maxArrayLength: Infinity, showHidden: false, showProxy: false, sorted: true, getters: true });
    assert.ok(!dump.includes("parentNode") && !dump.includes("childNodes"), "no edge in the dump of " + n.constructor.name);
  }
  assertHiddenEvent(new Ev("click"), root, kid);
});

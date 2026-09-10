// The composer follows its passage into the text a reload shows, and never onto another copy of it (followPassage,
// retargetComposer; plans/file-review.md, Commenting from either view and the anchors follow-on). A pending passage
// used to be re-found through its 24-character anchor with the SELECTION-TIME offset as the engine's tie-break, so
// once the session inserted a paragraph above a recurring passage, longer than half the gap between its copies, the
// nearest tied hit was the OTHER copy: the presel moved a paragraph up, the chip said nothing, and Save sent that
// copy's offset as the hint the host now settles a tie by — the note was saved on a passage the person never
// selected. Pinned here: an edit that does not reach the passage moves its offsets exactly through the two texts'
// common prefix and suffix (whatever the anchor would have said); a passage the edit reaches is re-found only at one
// best hit, and a tie is marked `tied`, painted nowhere, and saved with NO offset, so the host refuses it
// (anchor-ambiguous) rather than guess, the note stays, and selecting the passage again pins the copy. The panel is
// driven over the DOM stand-in file-comments-behavior.test.ts uses. Synthetic fixtures only: the notes-api world,
// placeholder ids.
import { test, type TestContext } from "node:test";
import * as assert from "node:assert/strict";
import { inspect } from "node:util";
import * as fs from "node:fs";
import * as path from "node:path";
import type { FileViewActionCtx, TrackedEdit } from "./file-view";
import type { Status } from "./file-comments-model";
import { locateComment, makeAnchor } from "./anchor-map";
import { hideEdges, staysEnumerable } from "../test-dom-shim";

const web = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const SRC = web("file-comments.ts");

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
  // the edges are created hidden and hideEdges hides the rest: a node inspects as its own projection (ui/test-dom-shim.ts)
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

// The stand-in's nodes inspect as their own projection: hideEdges (ui/test-dom-shim.ts) makes every own property that
// holds an object, and every accessor, non-enumerable, so a failing assertion's dump of a node is a few lines and not
// the whole tree (a dump that walked parentNode up to the body grew to tens of GB before the box killed it, 2026-09-09).
test("stand-in: a node enumerates and inspects as its own projection, never the tree", () => {
  const root = doc.createElement("div");
  const kid = root.appendChild(doc.createElement("span"));
  kid.className = "fc-x"; kid.dataset.id = "k1"; kid.addEventListener("click", () => { /* inert */ });
  const leaf = kid.appendChild(doc.createTextNode("leaf"));
  for (const n of [root, kid, leaf]) {
    const own = n as unknown as Record<string, unknown>;
    assert.ok(Object.keys(own).every((k) => staysEnumerable(own[k])), "only primitives enumerate on " + n.constructor.name + ": " + Object.keys(own).join(", "));
    const dump = inspect(n, { compact: false, customInspect: false, depth: 1000, maxArrayLength: Infinity, showHidden: false, showProxy: false, sorted: true, getters: true });
    assert.ok(!dump.includes("parentNode") && !dump.includes("childNodes"), "the dump is the node's own projection:\n" + dump);
  }
});
const store = new Map<string, string>();
(globalThis as any).localStorage = {
  getItem: (k: string) => (store.has(k) ? store.get(k)! : null),
  setItem: (k: string, v: string) => { store.set(k, String(v)); },
  removeItem: (k: string) => { store.delete(k); },
};

// ── fixtures: the notes-api world, with a report whose paragraph recurs ────────────────────────────
const SID = "11111111-2222-3333-4444-555555555555";
const ABS = "/repo/notes-api/docs/report.md";
const ROOT = "/repo/notes-api";
const STORE_PATH = ROOT + "/.trackchanges/docs%2Freport.md.json";
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
// the session's paragraph, inserted above the first copy: longer than half the gap between copies, so the engine's
// nearest tied hit to the OLD offset is the first copy (the wrong one)
const INSERTED = "The session added this paragraph meanwhile. ".repeat(13).trim();
const ABOVE = "# Report\n\n" + INSERTED + "\n\n" + PARA + "\n\n" + PARA + "\n\n" + PARA + "\n";
const SHIFT = ABOVE.length - DOC.length;
assert.ok(SHIFT > GAP / 2, "the insertion is longer than half the gap: nearest-wins picks the other copy");
// an edit in the second paragraph, inside the anchor's 24 characters before the passage: that copy's anchor breaks
const NEAR = DOC.slice(0, SECOND - "Here is ".length) + "Here, then, is " + DOC.slice(SECOND);
// edits on both sides of the passage in one write: the title, and a line at the end
const BOTH = DOC.replace("# Report", "# Report, revised") + "\nDone.\n";
// a report whose passage is unique
const UNIQ = "# Report\n\nAlpha line.\n\nThe unique passage here.\n\nOmega line.\n";
const UPHRASE = "unique passage";
const URANGE = { start: UNIQ.indexOf(UPHRASE), end: UNIQ.indexOf(UPHRASE) + UPHRASE.length };
function status(over: Partial<Status> = {}): Status {
  return {
    verb: "status", root: ROOT, storePath: STORE_PATH, trackedBy: null, agentTooling: "present",
    fileMtimeNs: "1757145600000000001", storeMtimeNs: "1757145600000000002", configMtimeNs: null,
    store: { v: 3, path: "docs/report.md", suggestions: [], comments: [] },
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
const SECOND_ROW = 4;   // title, blank, first, blank, second
const PASSAGE_TIED = "The file changed and this passage now occurs in it more than once with the same surroundings, so the copy you selected cannot be told apart; Save asks the file's machine to place it, and refuses if the copies still tie. Select the passage again to pick the copy.";

// ── followPassage: exact through the edit, the anchor only where the edit reaches the passage ──────

test("followPassage: a paragraph inserted above a recurring passage moves the pair with ITS copy, exactly; the engine's nearest tied hit to the old offset was the other copy", async () => {
  const { followPassage } = await import("./file-comments");
  // what the re-find got wrong: the 24-character anchor ties on every copy, and nearest to the OLD offset is the first
  const wrong = locateComment(ABOVE, makeAnchor(DOC, RANGE), SECOND);
  assert.equal(wrong.state, "located");
  assert.equal(wrong.range!.start, FIRST + SHIFT, "the engine, hinted by an offset into other text, picks the other copy");
  assert.deepEqual(followPassage(DOC, RANGE, ABOVE), { state: "moved", range: { start: SECOND + SHIFT, end: SECOND + SHIFT + MARKER.length } });
  assert.equal(ABOVE.slice(SECOND + SHIFT, SECOND + SHIFT + MARKER.length), MARKER);
  // the same, over a text whose only change is below the passage: the offsets hold
  assert.deepEqual(followPassage(DOC, RANGE, DOC + "\nAppendix.\n"), { state: "moved", range: RANGE });
});

test("followPassage: an edit inside the anchor's context before the passage, in its own paragraph, still moves it exactly — that copy's anchor is the one now broken", async () => {
  const { followPassage } = await import("./file-comments");
  const d = NEAR.length - DOC.length;
  // the re-find's answer: the second copy's prefix no longer matches, the first and third tie, and nearest to the old offset is the first
  assert.equal(locateComment(NEAR, makeAnchor(DOC, RANGE), SECOND).range!.start, FIRST, "the anchor alone would have moved the note to the first copy");
  assert.deepEqual(followPassage(DOC, RANGE, NEAR), { state: "moved", range: { start: SECOND + d, end: SECOND + d + MARKER.length } });
  assert.equal(NEAR.slice(SECOND + d, SECOND + d + MARKER.length), MARKER);
});

test("followPassage: edits on both sides reach the passage; a recurring one is tied, a unique one is re-found at its hit, and one that is gone is gone", async () => {
  const { followPassage } = await import("./file-comments");
  assert.deepEqual(followPassage(DOC, RANGE, BOTH), { state: "tied" }, "three intact copies the anchor cannot tell apart, and the old offset must not choose one");
  const moved = UNIQ.replace("Alpha", "Alpha two").replace("Omega", "Omega two");
  assert.deepEqual(followPassage(UNIQ, URANGE, moved), { state: "moved", range: { start: moved.indexOf(UPHRASE), end: moved.indexOf(UPHRASE) + UPHRASE.length } });
  assert.deepEqual(followPassage(UNIQ, URANGE, UNIQ.replace("The unique passage here.\n\n", "")), { state: "gone" });
  assert.deepEqual(followPassage(UNIQ, URANGE, UNIQ.replace(UPHRASE, "unique sentence")), { state: "gone" }, "the quote changed between its context: a relocation, not the passage");
  assert.deepEqual(followPassage(UNIQ, URANGE, UNIQ), { state: "moved", range: URANGE }, "the same text: the same offsets");
});

// ── the panel, driven: the note lands on the copy that was selected ────────────────────────────────

test("a note on the second of three identical paragraphs, a long paragraph inserted above: the presel stays on the second copy and Save sends its offset", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  startCommentInRow(w, SECOND_ROW, MARKER);
  assert.deepEqual(preselRows(w), [[SECOND_ROW, MARKER]], "the presel marks the selected copy");
  input(aside).value = "Say it once.";
  // the session inserts its paragraph above the first copy; the poll saw the file move and the viewer reloaded the bytes
  w.disk = ABOVE; w.ctx.reload();
  assert.deepEqual(preselRows(w), [[SECOND_ROW + 2, MARKER]], "the presel moved two rows down with ITS copy, not to the first");
  assert.equal(tag(aside), null, "followed: no tag");
  assert.equal(input(aside).value, "Say it once.", "the note stands");
  chord(input(aside)); await flush();
  const post = lastOf(w, "fileComments", "comment");
  assert.ok(post, "Enter saves");
  assert.equal(post.args.hintOffset, SECOND + SHIFT, "the hint is the second copy's offset in the new text");
  assert.notEqual(post.args.hintOffset, FIRST + SHIFT);
  assert.equal(post.args.anchor.quote, MARKER);
  assert.equal(post.args.anchor.prefix, ABOVE.slice(SECOND + SHIFT - 24, SECOND + SHIFT), "the anchor is built over the new text at the followed range");
});

test("edits on both sides of the selected copy: the composer says the passage recurs, paints nothing, Save sends no offset, the host's refusal keeps the note, and selecting the copy again pins it", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  startCommentInRow(w, SECOND_ROW, MARKER);
  input(aside).value = "Say it once.";
  w.disk = BOTH; w.ctx.reload();
  const tg = tag(aside);
  assert.ok(tg, "the composer wears a tag");
  assert.equal(tg!.textContent, "passage recurs");
  assert.equal(tg!.title, PASSAGE_TIED);
  assert.equal(aside.querySelector(".fc-quote")!.textContent, MARKER, "the chip still names the passage");
  assert.deepEqual(preselRows(w), [], "no presel: which copy is not known");
  chord(input(aside)); await flush();
  const post = lastOf(w, "fileComments", "comment");
  assert.ok(post, "Save is offered and Enter saves: the host rules");
  assert.equal(post.args.anchor.quote, MARKER);
  assert.equal(post.args.anchor.prefix, DOC.slice(SECOND - 24, SECOND), "the selection-time anchor, over the text its offsets index");
  assert.equal("hintOffset" in post.args, false, "NO offset: the selection's start indexes other text and would settle the tie by coincidence");
  refuse(w, post, "anchor-ambiguous", "the selected passage occurs more than once in docs/report.md with the same surroundings, and the selection's position was not sent to tell the copies apart — reload and select it again"); await flush();
  assert.equal(input(aside).value, "Say it once.", "the refusal keeps the note where it was typed");
  assert.match(aside.querySelector(".fc-composer .fileview-err")!.textContent, /more than once/);
  // the person selects the second copy again, in the text as it is now: the pair is exact, and the note is still there
  startCommentInRow(w, SECOND_ROW, MARKER);
  assert.equal(tag(aside), null, "a fresh pair: no tag");
  assert.deepEqual(preselRows(w), [[SECOND_ROW, MARKER]]);
  assert.equal(input(aside).value, "Say it once.");
  chord(input(aside)); await flush();
  const again = lastOf(w, "fileComments", "comment");
  assert.notEqual(again, post);
  const secondNow = BOTH.indexOf(MARKER, BOTH.indexOf(MARKER) + 1);
  assert.equal(again.args.hintOffset, secondNow, "the second copy's offset in the current text");
  assert.equal(again.args.anchor.prefix, BOTH.slice(secondNow - 24, secondNow));
  assert.equal(again.args.note, "Say it once.");
});

test("a tie noted at one reload is dropped when the text is the pair's own again: the tag clears, the presel returns, and Save sends the offset", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  startCommentInRow(w, SECOND_ROW, MARKER);
  input(aside).value = "Say it once.";
  w.disk = BOTH; w.ctx.reload();
  assert.equal(tag(aside)!.textContent, "passage recurs");
  // the session's edit is reverted (or Reload brought the same bytes back)
  w.disk = DOC; w.ctx.reload();
  assert.equal(tag(aside), null, "the pair indexes the text shown: no tag");
  assert.deepEqual(preselRows(w), [[SECOND_ROW, MARKER]]);
  chord(input(aside)); await flush();
  const post = lastOf(w, "fileComments", "comment");
  assert.equal(post.args.hintOffset, SECOND, "the offset is sent again: it indexes the text the host will read");
});

test("a reload over the same text, and one whose only change is below the passage, leave the composer where it was", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  startCommentInRow(w, SECOND_ROW, MARKER);
  w.setText(DOC);
  assert.deepEqual(preselRows(w), [[SECOND_ROW, MARKER]]);
  assert.equal(tag(aside), null);
  w.disk = DOC + "\nAppendix.\n"; w.ctx.reload();
  assert.deepEqual(preselRows(w), [[SECOND_ROW, MARKER]], "the offsets hold: the change is after the passage");
  assert.equal(tag(aside), null);
  input(aside).value = "Say it once.";
  chord(input(aside)); await flush();
  assert.equal(lastOf(w, "fileComments", "comment").args.hintOffset, SECOND);
});

// ── pinned at source: both Save paths hold the offset back for a tied pair; the re-find goes through followPassage ──

test("source: retargetComposer follows through followPassage and marks a tie; a tied pair's Save carries no offset on either path", () => {
  assert.match(SRC, /const f = followPassage\(c\.text, c\.range, src\);\n\s*if \(f\.state === "moved"\) \{ c\.range = f\.range; c\.text = src; c\.tied = false; \}\n\s*else c\.tied = f\.state === "tied";/);
  assert.match(SRC, /if \(src === c\.text\) \{ c\.tied = false; return; \}/, "the pair's own text again: no tie");
  assert.doesNotMatch(SRC, /locateComment\(src, makeAnchor\(c\.text, c\.range\), c\.range\.start\)/, "the old offset is never the engine's tie-break against new text");
  // the passage path keeps the statement file-comments-behavior.test.ts pins, and the tied rule follows it
  assert.match(SRC, /args\.hintOffset = c\.range\.start; \}\n(\s*\/\/[^\n]*\n)*\s*if \(c\.tied\) delete args\.hintOffset;/);
  // the region path (a figure embedded twice with the same surroundings) gates the same way
  assert.match(SRC, /args\.anchor = makeAnchor\(c\.text, c\.range\); args\.hintOffset = c\.range\.start; \}\n\s*if \(c\.tied\) delete args\.hintOffset;/);
  assert.match(SRC, /private retargetComposer\(\): void \{\n\s*const c = this\.composer; const src = this\.indexedText\(\);/, "the line file-comments-editing-round3.test.ts pins");
  assert.match(SRC, /c\.tied \? "passage recurs" : "passage changed"/g);
  assert.equal((SRC.match(/c\.tied \? "passage recurs" : "passage changed"/g) || []).length, 2, "both composers: the passage and the embed line");
});

// Show changes inline (the inline-display follow-on to plans/file-review.md, 2026-09-07): the Comments panel's
// header control that turns the read view's change marks on and off, in both views, remembered across opens and
// pages through the shared settings store — and the Rendered view's struck deletions it governs. Driven AS A PANEL
// over the changes-review suite's DOM stand-in (its Rendered body is built by hand to marked's shape; its settings
// store is the stub localStorage every panel suite installs):
//   • the default: on, beside Track changes, offered only while the file has changes to show;
//   • Rendered: a deletion is a zero-width point at its place with the struck old text as its label, a substitution
//     its point right before its tint; the cards are as plain as an insertion's and keep the deletion's Reveal;
//   • off: one click, no status ask (posted[] unchanged), no change mark in the body while the comment highlights
//     stay, no "not shown" tag anywhere (nothing is shown by choice), Reveal on every change card still going to Raw;
//   • remembered: the store's changesInline, read when the next panel opens (Raw too) and written on every flip;
//   • a flip elsewhere — the settings signal another pane or the gear raises — repaints the live panel.
// What a stand-in cannot show is pinned at source: the delegate action, the header's order, the store's key and
// default, the listener's install. Synthetic fixtures only: the notes-api world, placeholder ids.
import { test, type TestContext } from "node:test";
import * as assert from "node:assert/strict";
import { inspect } from "node:util";
import * as fs from "node:fs";
import * as path from "node:path";
import type { FileViewActionCtx } from "./file-view";
import type { Status, Hunk, StoreComment } from "./file-comments-model";
import { hideEdges, sameNodes, staysEnumerable } from "../test-dom-shim";

const web = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const SRC = web("file-comments.ts");
const SETTINGS = web("settings.ts");
const GUIDE = fs.readFileSync(path.resolve(process.cwd(), "..", "docs", "guide.md"), "utf8");
const PLAN = fs.readFileSync(path.resolve(process.cwd(), "..", "plans", "file-review.md"), "utf8");

// ── fixtures: the notes-api world ──────────────────────────────────────────────────────────────────
const SID = "11111111-2222-3333-4444-555555555555";
const ABS = "/repo/notes-api/docs/report.md";
const ROOT = "/repo/notes-api";
const STORE_PATH = ROOT + "/.trackchanges/docs%2Freport.md.json";
const T0 = 1757145600000;
const DOC = "# Report\n\n## Findings\nThe api session cut p95 latency by 40% and the p99 by 10%.\n\n"
  + "We recommend shipping the cache in v1.2.\n\nRisks remain in the fallback path.\n\nNext steps: measure again.\n";
const at = (needle: string, src = DOC): number => { const i = src.indexOf(needle); assert.ok(i >= 0, needle); return i; };
const H = (id: string, kind: Hunk["kind"], from: number, to: number, oldText: string, newText: string, ts = T0 - 90000): Hunk =>
  ({ id, author: "api", ts, kind, curFrom: from, curTo: to, baseFrom: from, baseTo: from + oldText.length, oldText, newText, anchor: null });
const h1 = H("h1", "sub", at("cut"), at("cut") + 3, "reduced", "cut");
const h2 = H("h2", "ins", at(" and the p99"), at(" and the p99") + " and the p99 by 10%".length, "", " and the p99 by 10%", T0 - 80000);
const h3 = H("h3", "del", at("shipping"), at("shipping"), "quickly ", "", T0 - 70000);
const h5 = H("h5", "ins", at(" again"), at(" again") + 6, "", " again", T0 - 50000);
/** The same change with its offsets moved by `n` — hunks computed over another string. */
const shifted = (h: Hunk, n: number): Hunk => ({ ...h, curFrom: h.curFrom + n, curTo: h.curTo + n });
const passage: StoreComment = {
  id: T0 + "-118", author: "you", ts: T0, body: "Which cache? Say which.",
  anchor: { quote: "shipping the cache in v1.2", prefix: "We recommend ", suffix: "." }, replies: [], resolved: false,
};
// a passage comment the session answered with a revision: it keeps its anchor and gains the change's id
const hosted: StoreComment = {
  id: T0 + 5000 + "-7", author: "you", ts: T0 + 5000, body: "Cut is the right word.",
  anchor: { quote: "cut p95 latency", prefix: "The api session ", suffix: " by 40%" }, suggestionId: "h1", replies: [], resolved: false,
};
const SUGG = [{ id: "h1", author: "api", authorId: SID, ts: T0 - 90000, kind: "sub", from: h1.curFrom, oldText: "reduced", newText: "cut" },
  { id: "h3", author: "api", ts: T0 - 70000, kind: "del", from: h3.curFrom, oldText: "quickly " }];
function status(over: Partial<Status> = {}): Status {
  return {
    verb: "status", root: ROOT, storePath: STORE_PATH, trackedBy: { kind: "file", entry: "docs/report.md" }, agentTooling: "present",
    fileMtimeNs: "1757145600000000001", storeMtimeNs: "1757145600000000002", configMtimeNs: "1757145600000000003",
    store: { v: 3, path: "docs/report.md", suggestions: SUGG, comments: [passage] },
    hunks: [h1, h3], log: [],
    unsent: { comments: [passage.id], replies: [], accepted: 0, rejected: 0, watermark: null },
    ...over,
  };
}
const MOVED_FILE = "the file ~/notes-api/docs/report.md changed on disk since you opened the file — reload and retry";
const MOVED_STORE = "the comments for ~/notes-api/docs/report.md changed on disk since you opened the file — reload and retry";

// ── the DOM stand-in: ancestry, attributes, events, focus, a small selector engine ─────────────────
class Ev {
  target: El | Txt | null = null;
  currentTarget: El | null = null;
  defaultPrevented = false;
  stopped = false;
  key: string;
  constructor(public type: string, init: { key?: string } = {}) { this.key = init.key || ""; }
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
  getBoundingClientRect(): typeof this.rect { return this.rect; }
  get offsetWidth(): number { return 0; }
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
  for (const n of chain) if (run(n.listeners, false, n)) return !ev.defaultPrevented;
  run(doc.listeners, false, null);
  return !ev.defaultPrevented;
}
const win: any = new EventTarget();
win.parent = win; win.innerWidth = 1200; win.innerHeight = 800;
win.getSelection = () => null;
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

// ── the viewer stand-in: a Raw or Rendered body, the seam as closures, a file whose mtime the view tracks ──
type World = {
  ctx: FileViewActionCtx; posted: any[]; main: El; body: El;
  hooks: { rendered: Array<() => void>; close: Array<() => void> };
  disk: string; diskMtime: string; viewMtime: string; reloads: number; scrolls: number[]; modes: string[];
  mtimes: Record<string, string>;
  /** The held reload's landing (deferReload): the bytes and mtime now on disk, repainted, onRendered fired. */
  landReload: (() => void) | null;
  /** Releases the held colour fetch (holdSessions); the fetch stub awaits the gate. */
  releaseSessions: () => void;
  sessionsGate: Promise<void>;
  close(): void;
};
let cur: World | null = null;
(globalThis as any).fetch = async (url: string) => {
  if (url.includes("/sessions")) {
    await cur!.sessionsGate;
    return { json: async () => [{ id: SID, name: "api", bg: "#123456", fg: "#ffffff" }] };
  }
  const p = decodeURIComponent((/[?&]path=([^&]*)/.exec(url) || [])[1] || "");
  const mt = cur!.mtimes[p];
  return { status: mt === undefined ? 404 : 200, headers: { get: (h: string) => (h === "X-Romp-Mtime-Ns" && mt !== undefined ? mt : null) } };
};
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
const el = (tag: string, ...kids: Array<El | string>): El => { const e = new El(tag); for (const k of kids) e.appendChild(typeof k === "string" ? new Txt(k) : k); return e; };
/** A file-authored inline element the sanitizer keeps: `<span data-act=… data-id=…>text</span>`. */
const fileSpan = (act: string, id: string, text: string): El => { const s = el("span", text); s.dataset.act = act; s.dataset.id = id; return s; };
/** marked's rendering of DOC, built by hand: one element per block, in order, holding the block's text. */
function renderedDoc(box: El, intro?: El): void {
  const blocks: El[] = [el("h1", "Report")];
  if (intro) blocks.push(intro);
  blocks.push(el("h2", "Findings"), el("p", "The api session cut p95 latency by 40% and the p99 by 10%."),
    el("p", "We recommend shipping the cache in v1.2."), el("p", "Risks remain in the fallback path."), el("p", "Next steps: measure again."));
  box.replaceChildren(...blocks);
}
type WorldOpts = { src?: string; mode?: "raw" | "rendered"; intro?: () => El; deferReload?: boolean; holdSessions?: boolean };
function world(over: WorldOpts = {}): World {
  const mode = over.mode || "raw";
  const main = new El("div"); main.className = "fileview-main";
  const body = new El("div"); body.className = "fileview-body";
  main.appendChild(body);
  let text = over.src ?? DOC;
  let code: El | null = null, md: El | null = null;
  if (mode === "raw") {
    const wrap = new El("div"); wrap.className = "fileview-code";
    const pre = new El("pre"); pre.className = "fileview-pre fileview-wrap";
    code = new El("code"); code.className = "hljs";
    pre.appendChild(code); wrap.appendChild(pre); body.appendChild(wrap);
    rows(code, text);
  } else {
    md = new El("div"); md.className = "fileview-md"; body.appendChild(md);
    renderedDoc(md, over.intro ? over.intro() : undefined);
  }
  let release: () => void = () => { /* set below */ };
  const gate = new Promise<void>((r) => { release = r; });
  if (!over.holdSessions) release();
  const w = {
    posted: [] as any[], main, body,
    hooks: { rendered: [] as Array<() => void>, close: [] as Array<() => void> },
    disk: text, diskMtime: "1757145600000000001", viewMtime: "1757145600000000001", reloads: 0, scrolls: [] as number[], modes: [] as string[], mtimes: {} as Record<string, string>,
    landReload: null as (() => void) | null, releaseSessions: release, sessionsGate: gate,
  } as World;
  const setText = (s: string) => {
    text = s;
    if (code) rows(code, s); else if (md) renderedDoc(md, over.intro ? over.intro() : undefined);
    for (const cb of w.hooks.rendered) cb();
  };
  const land = () => { w.landReload = null; w.viewMtime = w.diskMtime; setText(w.disk); };
  w.ctx = {
    path: ABS, sid: SID, todoId: null,
    body: () => body as unknown as HTMLElement, mode: () => mode, text: () => text, mtimeNs: () => w.viewMtime, media: () => null, mediaElement: () => null, renderedImages: () => [], pdfPages: () => [],
    identity: () => ({ name: "api", color: null }),
    onRendered: (cb) => { w.hooks.rendered.push(cb); }, onSelection: () => { /* inert */ },
    onSaved: () => { /* inert */ }, onClose: (cb) => { w.hooks.close.push(cb); },
    post: (m) => { w.posted.push(m); }, ensureEditingAllowed: async () => true, setEditBlocked: () => { /* inert */ }, editing: () => false, setTrackedEdit: () => { /* inert */ }, guardClose: () => { /* inert */ },
    aside: (node) => { main.querySelector(".fileview-aside")?.remove(); if (node) { const n = node as unknown as El; n.classList.add("fileview-aside"); main.appendChild(n); } },
    setMode: (m) => { w.modes.push(m); }, scrollToOffset: (n) => { w.scrolls.push(n); },
    // fetchFile: an async GET in the real seam — held here until the test lands it (deferReload), else at once
    reload: () => { w.reloads++; if (over.deferReload) w.landReload = land; else land(); },
  };
  w.close = () => { for (const cb of w.hooks.close) cb(); if (cur === w) cur = null; };
  cur = w;
  return w;
}
const flush = () => new Promise<void>((r) => setImmediate(r));
const lastOf = (w: World, type: string, verb?: string) => [...w.posted].reverse().find((m) => m.type === type && (verb === undefined || m.verb === verb));
const countOf = (w: World, type: string, verb?: string) => w.posted.filter((m) => m.type === type && (verb === undefined || m.verb === verb)).length;
function answer(w: World, s: Status, m = lastOf(w, "fileComments", "status"), extra: Record<string, unknown> = {}): void {
  assert.ok(m, "an ask is outstanding");
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId: m.reqId, ...s, ...extra } }));
  w.mtimes[w.ctx.path] = s.fileMtimeNs;
  if (s.storePath && s.storeMtimeNs !== null) w.mtimes[s.storePath] = s.storeMtimeNs;
  if (s.root && s.configMtimeNs !== null) w.mtimes[s.root + "/.trackchanges/config.json"] = s.configMtimeNs;
}
function refuse(w: World, m: any, code: string, error: string): void {
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsFailed", reqId: m.reqId, verb: m.verb, code, error } }));
}
async function openPanel(w: World, s: Status = status()): Promise<{ unit: El; button: El; aside: El }> {
  const fc = await import("./file-comments");
  const unit = fc.fileCommentsAction.mount(w.ctx) as unknown as El;
  const button = unit.childNodes[0] as El;
  answer(w, s); await flush();
  button.click();
  answer(w, s); await flush(); await flush();
  const aside = w.main.querySelector(".fileview-aside")!;
  assert.ok(aside, "the panel is mounted beside the body");
  scrolledInto.length = 0;
  return { unit, button, aside };
}
const card = (aside: El, key: string): El | null => aside.querySelector('.fc-card[data-id="' + key + '"]');
const act = (root: El, a: string, id?: string): El | null => root.querySelector('[data-act="' + a + '"]' + (id ? '[data-id="' + id + '"]' : ""));
const texts = (els: El[]) => els.map((e) => e.textContent);
const marksOf = (w: World, id?: string): El[] => w.body.querySelectorAll('[data-act="fcchange"]' + (id ? '[data-id="' + id + '"]' : ""));
const tags = (c: El): string[] => texts(c.querySelectorAll(".fc-card-head .fc-tag"));
const isLink = (c: El): boolean => c.querySelector(".fc-ref")!.classes.includes("fc-link");

// ── helpers of this suite ──────────────────────────────────────────────────────────────────────────
const SETTINGS_KEY = "romp:settings";
const stored = (): Record<string, unknown> | null => { const raw = store.get(SETTINGS_KEY); return raw ? JSON.parse(raw) as Record<string, unknown> : null; };
const toggle = (aside: El): El | null => act(aside, "fcinline");
/** The text of `block` before `point` and after it, in document order (the point itself holds none). */
function around(block: El, point: El): [string, string] {
  let pre = "", post = "", seen = false;
  const visit = (n: El | Txt) => {
    if (n === point) { seen = true; return; }
    if (n instanceof Txt) { if (seen) post += n.data; else pre += n.data; return; }
    for (const c of n.childNodes) visit(c);
  };
  visit(block);
  return [pre, post];
}
const blockOf = (w: World, n: El): El => { let x: El = n; while (x.parentNode && !x.parentNode.classes.includes("fileview-md")) x = x.parentNode; return x; };
const changeCards = (aside: El): El[] => aside.querySelectorAll(".fc-card.fc-change");

// ── the default ────────────────────────────────────────────────────────────────────────────────────

test("the default: Show changes inline is ON, a two-state button beside Track changes and before Comment on this file, offered only while the file has changes; nothing is written to the store until a flip", async (t: TestContext) => {
  store.delete(SETTINGS_KEY);
  const w = world({ mode: "rendered" }); t.after(() => w.close());
  const { aside } = await openPanel(w, status({ hunks: [h2, h3] }));
  const row = aside.querySelector(".fc-head .fc-row")!;
  assert.deepEqual(row.childNodes.map((c) => (c as El).dataset.act), ["fctrack", "fcinline", "fcfile"], "Track changes · Show changes inline · Comment on this file");
  const b = toggle(aside)!;
  assert.equal(b.tagName, "BUTTON"); assert.equal(b.textContent, "Show changes inline");
  assert.ok(b.classes.includes("fileview-btn") && b.classes.includes("fc-toggle"), "the Track changes toggle's dress: the selected state is the accent fill");
  assert.equal(b.dataset.on, "1"); assert.equal(b.getAttribute("aria-pressed"), "true");
  assert.match(b.title, /marked in the text/); assert.match(b.title, /click to read the file without the marks/);
  assert.equal(stored(), null, "the default is the store's absence: nothing is written until the person flips it");
  assert.ok(marksOf(w).length > 0, "on: the marks are painted");
  w.close();
  // no changes: no control over marks that do not exist
  const w2 = world({ mode: "rendered" }); t.after(() => w2.close());
  const { aside: a2 } = await openPanel(w2, status({ hunks: [], store: { v: 3, path: "docs/report.md", suggestions: [], comments: [passage] } }));
  assert.equal(toggle(a2), null, "no changes: the header shows Track changes and Comment on this file alone");
  assert.deepEqual(a2.querySelector(".fc-head .fc-row")!.childNodes.map((c) => (c as El).dataset.act), ["fctrack", "fcfile"]);
});

// ── Rendered: the struck deletion ──────────────────────────────────────────────────────────────────

test("Rendered: a deletion is a zero-width point before the word it preceded, labelled with the struck old text; a substitution's point sits right before its tint; the cards are plain and link to their marks", async (t: TestContext) => {
  store.delete(SETTINGS_KEY);
  const w = world({ mode: "rendered" }); t.after(() => w.close());
  const { aside } = await openPanel(w, status({ hunks: [h1, h2, h3] }));
  const del = marksOf(w, "h3");
  assert.equal(del.length, 1);
  assert.equal(del[0].tagName, "SPAN"); assert.deepEqual(del[0].classes, ["fc-del"]);
  assert.equal(del[0].dataset.fcText, "quickly ", "the label is the old text, as Raw's is");
  assert.equal(del[0].childNodes.length, 0, "no text node: the label is the sheet's generated content");
  assert.equal(del[0].getAttribute("role"), "button"); assert.equal(del[0].tabIndex, 0); assert.equal(del[0].title, "Open this change");
  const p = blockOf(w, del[0]);
  assert.equal(p.tagName, "P");
  assert.deepEqual(around(p, del[0]), ["We recommend ", "shipping the cache in v1.2."], "struck 'quickly ' reads between 'We recommend' and 'shipping'");
  // the substitution: its point, then its tint, adjacent
  const sub = marksOf(w, "h1");
  assert.deepEqual(sub.map((m) => m.classes.join(" ")), ["fc-del", "fc-ins"], "a substitution paints the point and then its new text");
  assert.equal(sub[0].dataset.fcText, "reduced"); assert.equal(sub[1].textContent, "cut");
  assert.equal(sub[0].parentNode!.childNodes[sub[0].parentNode!.childNodes.indexOf(sub[0]) + 1], sub[1], "the point is the node right before the mark");
  // the cards: no tag, a link to the mark, and the deletion's constant Reveal
  for (const c of changeCards(aside)) {
    assert.equal(tags(c).includes("not shown"), false, c.dataset.id + " is shown");
    assert.ok(isLink(c), c.dataset.id + "'s reference links to its mark");
  }
  assert.ok(act(card(aside, "chg:h3")!, "fcreveal", "chg:h3"), "a deletion keeps its Reveal (a point is easy to miss)");
  assert.equal(act(card(aside, "chg:h1")!, "fcreveal", "chg:h1"), null, "a painted substitution needs none");
  const ref = card(aside, "chg:h3")!.querySelector(".fc-ref")!;
  ref.click();
  assert.ok(scrolledInto.includes(del[0]), "the reference scrolls to the point");
  // the panel owns the point: Enter on it opens its card
  del[0].focus();
  assert.equal(doc.activeElement, del[0]);
  dispatch(del[0], new Ev("keydown", { key: "Enter" }));
  assert.ok(card(aside, "chg:h3")!.classes.includes("open"), "Enter on the focused point opens the deletion's card");
});

// ── off ────────────────────────────────────────────────────────────────────────────────────────────

test("off: one click repaints at once with no status ask — no change mark in either view, the comment highlights stay, every change card is plain with Reveal to Raw; on again brings the marks back; each flip writes the store", async (t: TestContext) => {
  store.delete(SETTINGS_KEY);
  const w = world({ mode: "rendered" }); t.after(() => w.close());
  const { aside } = await openPanel(w, status({ hunks: [h1, h2, h3] }));
  assert.equal(marksOf(w).length, 4, "two for the substitution, one each for the insertion and the deletion");
  assert.equal(w.body.querySelectorAll(".fc-hl").length, 1, "the passage comment's highlight");
  const asks = w.posted.length;
  toggle(aside)!.click();
  await flush();
  assert.equal(w.posted.length, asks, "no message to the kernel: the hunks are already here");
  assert.equal(toggle(aside)!.dataset.on, "0"); assert.equal(toggle(aside)!.getAttribute("aria-pressed"), "false");
  assert.match(toggle(aside)!.title, /marks are off/);
  assert.equal(marksOf(w).length, 0, "no change mark in the body");
  assert.equal(w.body.querySelectorAll(".fc-hl").length, 1, "the comment highlight is not governed by the toggle");
  assert.equal(w.body.querySelector(".fc-hl")!.textContent, "shipping the cache in v1.2");
  assert.equal(w.body.textContent.includes("We recommend shipping the cache in v1.2."), true, "the text reads as it is");
  for (const c of changeCards(aside)) {
    assert.equal(tags(c).includes("not shown"), false, c.dataset.id + ": nothing is shown by choice, so no tag says the view failed to");
    assert.equal(isLink(c), false, c.dataset.id + ": no mark to link to");
    assert.ok(act(c, "fcreveal", c.dataset.id), c.dataset.id + " offers Reveal");
  }
  assert.equal(stored()!.changesInline, false, "the flip is written to the shared store");
  act(card(aside, "chg:h2")!, "fcreveal", "chg:h2")!.click();
  assert.deepEqual(w.modes, ["raw"]); assert.deepEqual(w.scrolls, [h2.curFrom], "Reveal still goes to the change's place");
  // on again
  toggle(aside)!.click();
  await flush();
  assert.equal(w.posted.length, asks);
  assert.equal(toggle(aside)!.dataset.on, "1");
  assert.equal(marksOf(w).length, 4, "the marks are back");
  assert.equal(marksOf(w, "h3")[0].dataset.fcText, "quickly ");
  assert.equal(stored()!.changesInline, true);
  assert.equal(w.body.querySelectorAll(".fc-hl").length, 1);
  // a poll's repaint keeps the person's choice (the field, not a per-paint read of the DOM)
  toggle(aside)!.click(); await flush();
  w.ctx.reload();   // the viewer re-rendered the body: onRendered → paintAll
  await flush();
  assert.equal(marksOf(w).length, 0, "a repaint paints no mark while the toggle is off");
  assert.equal(toggle(aside)!.dataset.on, "0");
  store.delete(SETTINGS_KEY);
});

// ── remembered ─────────────────────────────────────────────────────────────────────────────────────

test("remembered: a store that says off opens the next panel without marks, in Raw as in Rendered, its header saying so; a corrupt store reads as the default", async (t: TestContext) => {
  store.set(SETTINGS_KEY, JSON.stringify({ compact: true, changesInline: false }));
  const w = world(); t.after(() => w.close());   // Raw
  const { aside } = await openPanel(w, status({ hunks: [h1, h3] }));
  assert.equal(toggle(aside)!.dataset.on, "0", "the stored preference");
  assert.equal(marksOf(w).length, 0, "Raw paints no mark either");
  assert.ok(w.body.textContent.includes("cut p95 latency"), "the text reads as it is");
  for (const c of changeCards(aside)) { assert.equal(tags(c).includes("not shown"), false); assert.ok(act(c, "fcreveal", c.dataset.id)); }
  toggle(aside)!.click(); await flush();
  assert.ok(marksOf(w, "h1").some((m) => m.textContent === "cut"), "on: the Raw tint");
  assert.equal(marksOf(w, "h3")[0].dataset.fcText, "quickly ", "…and the Raw point");
  assert.equal(stored()!.changesInline, true);
  assert.equal(stored()!.compact, true, "the store's other keys are kept");
  w.close();
  store.set(SETTINGS_KEY, "{not json");
  const w2 = world({ mode: "rendered" }); t.after(() => w2.close());
  const { aside: a2 } = await openPanel(w2, status({ hunks: [h3] }));
  assert.equal(toggle(a2)!.dataset.on, "1", "a corrupt store costs nothing: the default, on");
  assert.equal(marksOf(w2, "h3").length, 1);
  store.delete(SETTINGS_KEY);
});

test("a flip elsewhere — the settings signal another pane or the gear raises, or another tab's storage event — repaints the live panel so its header and its body agree", async (t: TestContext) => {
  store.delete(SETTINGS_KEY);
  const w = world({ mode: "rendered" }); t.after(() => w.close());
  const { aside } = await openPanel(w, status({ hunks: [h2, h3] }));
  assert.equal(marksOf(w).length, 2);
  const asks = w.posted.length;
  store.set(SETTINGS_KEY, JSON.stringify({ changesInline: false }));
  win.dispatchEvent(new Event("romp:settings"));   // the gear's same-document signal (settings.ts onExternalSettingsChange)
  await flush();
  assert.equal(marksOf(w).length, 0, "the other pane's flip reaches this body");
  assert.equal(toggle(aside)!.dataset.on, "0", "…and this header");
  assert.equal(w.posted.length, asks, "no status ask for it");
  store.set(SETTINGS_KEY, JSON.stringify({ changesInline: true }));
  const ev = new Event("storage"); (ev as unknown as { key: string }).key = SETTINGS_KEY;
  win.dispatchEvent(ev);   // another same-origin tab's write
  await flush();
  assert.equal(marksOf(w).length, 2); assert.equal(toggle(aside)!.dataset.on, "1");
  // a signal that changes nothing repaints nothing (the marks stay the same nodes)
  const before = marksOf(w);
  win.dispatchEvent(new Event("romp:settings"));
  await flush();
  sameNodes(marksOf(w), before, "no new information, no repaint");   // by identity (ui/test-dom-shim.ts sameNodes)
  store.delete(SETTINGS_KEY);
});

// ── source pins ────────────────────────────────────────────────────────────────────────────────────

test("pins: the delegate action, the header's order, the store's key and default, the paint guard, the tag guard, the listener's install, the guide and the plan", () => {
  assert.match(SRC, /fcinline: \(\) => this\.toggleInline\(\),/, "the toggle is one of the panel's own delegated actions (click-safe through the one root)");
  assert.match(SRC, /private toggleInline\(\): void \{\n\s+this\.inline = !this\.inline;\n\s+saveSettings\(\{ changesInline: this\.inline \}\);\n\s+this\.paintAll\(\);\n\s+\}/, "flip, write the store, repaint — no request");
  const head = SRC.slice(SRC.indexOf("private renderHead("), SRC.indexOf("private renderComposer("));
  const pos = (s: string) => { const i = head.indexOf(s); assert.ok(i >= 0, s); return i; };
  assert.ok(pos('btn("Track changes", "fctrack", "fileview-btn fc-toggle")') < pos('btn("Show changes inline", "fcinline", "fileview-btn fc-toggle")'), "beside Track changes, after it");
  assert.ok(pos('btn("Show changes inline", "fcinline", "fileview-btn fc-toggle")') < pos('btn("Comment on this file", "fcfile")'), "…and before Comment on this file");
  assert.match(head, /if \(s && \(s\.hunks \|\| \[\]\)\.length && !this\.ctx\.editing\(\)\) \{\n\s+const i = btn\("Show changes inline"/, "offered while the file has changes and the read view is up");
  assert.match(head, /i\.dataset\.on = this\.inline \? "1" : "0";\n\s+i\.setAttribute\("aria-pressed", this\.inline \? "true" : "false"\);/, "the two-state button's state, as Track changes wears it");
  assert.match(SRC, /inline = loadSettings\(\)\.changesInline;/, "read from the shared store when the panel is made");
  assert.match(SRC, /private paintChanges\(root: Element, src: string, rendered: boolean, deferTrim = false\): void \{\n\s+const s = this\.status;\n\s+if \(!this\.inline\) return;/, "off: the change painters are not called, in either view");
  assert.match(SRC, /\} else if \(!painted && this\.inline && !editing && !inFlux && src !== null && this\.ctx\.mode\(\) !== "media"\) \{\n[^\n]*\n\s+const t = el\("span", "fc-tag", "not shown"\);/, "the tag is claimed only while the marks are on");
  assert.doesNotMatch(SRC, /The Rendered view cannot show a deletion/, "the Rendered view shows deletions now: the tag's del-specific title is gone");
  assert.match(SRC, /onExternalSettingsChange\(\(s\) => \{ if \(live && live\.inline !== s\.changesInline\) \{ live\.inline = s\.changesInline; live\.paintAll\(\); \} \}\);/, "one listener for the module, routed to the live panel");
  assert.ok(SRC.indexOf("onExternalSettingsChange((s) =>") > SRC.indexOf("function ensureListener(): void {") && SRC.indexOf("onExternalSettingsChange((s) =>") < SRC.indexOf("const KEY_ACTS"), "installed in ensureListener, once");
  assert.match(SETTINGS, /^\s+changesInline: boolean;/m, "a field of the shared settings (settings.ts), like subgoals: toggled from its surface, not the gear");
  // Pinned by value, not by the key's place in the literal: new settings are appended at its end (theme, then
  // changesInline itself), so a tail-anchored pin would go red at the next one with no change to the default.
  // statusline-branch.test.ts pins showBranch the same way.
  const DEFAULT_ON = /export const DEFAULT_SETTINGS: RompSettings = \{[^\n]*\bchangesInline: true[,\s}]/;
  assert.match(SETTINGS, DEFAULT_ON, "ON by default");
  const literal = SETTINGS.match(/export const DEFAULT_SETTINGS: RompSettings = \{[^\n]*\};/);
  assert.ok(literal, "the defaults literal is one line");
  assert.match(literal[0].replace("changesInline: true", "changesInline: true, later: false"), DEFAULT_ON, "…read by value: a setting appended after it keeps the pin green");
  assert.doesNotMatch(literal[0].replace("changesInline: true", "changesInline: false"), DEFAULT_ON, "…and a flipped default turns it red");
  assert.match(SETTINGS, /const KEY = "romp:settings";/, "the store this suite's stub localStorage holds");
  // the guide: both views, both marks, the toggle by its label
  const files = GUIDE.slice(GUIDE.indexOf("### Files"), GUIDE.indexOf("## Automatic nudges")).replace(/\s+/g, " ");
  for (const phrase of ["**Show changes inline**", "in both views", "deletion is struck", "insertion is tinted", "**Reveal**"]) assert.ok(files.includes(phrase), "guide: " + phrase);
  assert.doesNotMatch(files, /A deletion has nothing to mark in the Rendered view/, "the old sentence is gone");
  // the plan: the follow-on note beside the Slice 2 build note, the exclusion gone, the toggle in the UX paragraph
  assert.match(PLAN, /^The inline-display follow-on \(2026-09-07\)/m);
  const notV1 = PLAN.slice(PLAN.indexOf("## Deliberately not in v1"), PLAN.indexOf("## Dependencies"));
  assert.doesNotMatch(notV1, /inline\s+deletions in the Rendered view/);
  const ux = PLAN.slice(PLAN.indexOf("**Raw view is exact, Rendered view is best effort.**"), PLAN.indexOf("**Comment on a selection**")).replace(/\s+/g, " ");
  assert.ok(ux.includes("Show changes inline"), "the UX paragraph names the toggle");
  assert.ok(ux.includes("struck at its point in both views") || ux.includes("struck at their point in both views"), "…and says deletions read inline in Rendered too");
});

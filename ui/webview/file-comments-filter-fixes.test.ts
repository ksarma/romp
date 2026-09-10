// The Comments panel's filter (the filter follow-on to plans/file-review.md, 2026-09-07), after its second review: the
// cases the first round's fixes left untested or got wrong, driven AS A PANEL over the review suite's DOM stand-in (its
// harness, copied; the pointer events carry coordinates here, for a drag on a figure's overlay).
//   • the track slot's loader and refusal stand directly under the toggles' row, ABOVE the status refusal's row, on a file
//     with nothing to filter (no filter row: an append is where underToggles lands), as they did before the filter; with
//     cards, between the toggles' row and the filter's, the head's row below;
//   • Accept all under Changes, refused store-moved, and the re-read leaves no change pending: the Changes empty line and
//     the "Nothing decided" row under it — the clicked decision is not silent (CLAUDE.md, fail loudly);
//   • a region comment saved under Changes: the line names the card and the rectangle; a saved comment the session then
//     answers with a revision (bound by suggestionId) keeps its own card, hidden under Changes like every comment, so the
//     line stands and the change card counts the comment (the about follow-on, 2026-09-10; before it the comment was drawn
//     inside the change card and the line ended there);
//   • Show changes inline under Comments: the toggle stays (its setting governs All, Changes and other panels) and its title
//     says the filter hides the marks, never that the text carries marks it does not.
// Synthetic fixtures only: the notes-api world, placeholder ids.
import { test, type TestContext } from "node:test";
import * as assert from "node:assert/strict";
import { inspect } from "node:util";
import * as fs from "node:fs";
import * as path from "node:path";
import type { FileViewActionCtx, TrackedEdit } from "./file-view";
import { type Status, type Hunk, type StoreComment } from "./file-comments-model";
import { hideEdges, staysEnumerable } from "../test-dom-shim";

const web = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const SRC = web("file-comments.ts");

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
const passage: StoreComment = {
  id: T0 + "-118", author: "you", ts: T0, body: "Which cache? Say which.",
  anchor: { quote: "shipping the cache in v1.2", prefix: "We recommend ", suffix: "." }, replies: [], resolved: false,
};
// a passage comment the session answered with a revision: it keeps its anchor and gains the change's id; its own card,
// wearing an "answered by a change" tag (before the about follow-on, 2026-09-10, it was drawn inside h1's card)
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

// ── the DOM stand-in: ancestry, attributes, events, focus, a small selector engine ─────────────────
type Init = { key?: string; clientX?: number; clientY?: number; pointerId?: number; button?: number; buttons?: number };
class Ev {
  target: El | Txt | null = null;
  currentTarget: El | null = null;
  defaultPrevented = false;
  stopped = false;
  key: string; clientX: number; clientY: number; pointerId: number; button: number; buttons: number;
  constructor(public type: string, init: Init = {}) { this.key = init.key || ""; this.clientX = init.clientX ?? 0; this.clientY = init.clientY ?? 0; this.pointerId = init.pointerId ?? 1; this.button = init.button ?? 0; this.buttons = init.buttons ?? 1; }
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
let selection: any = null;                             // the selection the float's Comment reads (window.getSelection)
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

// ── the viewer stand-in: a Raw or Rendered body, the seam as closures, a file whose mtime the view tracks ──
type World = {
  ctx: FileViewActionCtx; posted: any[]; main: El; body: El;
  hooks: { rendered: Array<() => void>; selection: Array<(s: Selection) => void>; close: Array<() => void> };
  editing: boolean; tracked: TrackedEdit | null;    // the viewer's edit mode, and the panel's half of editing over pending changes (Slice 5)
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
    hooks: { rendered: [] as Array<() => void>, selection: [] as Array<(s: Selection) => void>, close: [] as Array<() => void> },
    editing: false, tracked: null,
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
    onRendered: (cb) => { w.hooks.rendered.push(cb); }, onSelection: (cb) => { w.hooks.selection.push(cb); },
    onSaved: () => { /* inert */ }, onClose: (cb) => { w.hooks.close.push(cb); }, guardClose: () => { /* inert */ },   // the viewer's close ask (main, 2026-09-07): the stand-in asks nothing
    post: (m) => { w.posted.push(m); }, ensureEditingAllowed: async () => true, setEditBlocked: () => { /* inert */ }, editing: () => w.editing, setTrackedEdit: (t) => { w.tracked = t; },
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
const tags = (c: El): string[] => texts(c.querySelectorAll(".fc-card-head .fc-tag"));

// ── helpers and fixtures of this suite ─────────────────────────────────────────────────────────────
const SETTINGS_KEY = "romp:settings";
const stored = (): Record<string, unknown> | null => { const raw = store.get(SETTINGS_KEY); return raw ? JSON.parse(raw) as Record<string, unknown> : null; };
const rowsOf = (aside: El): string[] => aside.querySelector(".fc-head")!.childNodes.filter((n) => n instanceof El && (n as El).classes.includes("fc-row")).map((r) => (r as El).classes.join(" "));
const headKids = (aside: El): El[] => aside.querySelector(".fc-head")!.childNodes.filter((n): n is El => n instanceof El);
const filterRow = (aside: El): El | null => aside.querySelector(".fc-head .fc-filter");
const option = (aside: El, key: string): El => { const b = aside.querySelector('[data-act="fcfilter"][data-key="' + key + '"]'); assert.ok(b, "the " + key + " option"); return b!; };
const chosen = (aside: El): string[] => aside.querySelectorAll('[data-act="fcfilter"]').filter((b) => b.dataset.on === "1").map((b) => b.dataset.key);
const changeCards = (aside: El): El[] => aside.querySelectorAll(".fc-card.fc-change");
const commentCards = (aside: El): El[] => aside.querySelectorAll(".fc-card").filter((c) => !c.classes.includes("fc-change"));
const highlights = (w: World): El[] => w.body.querySelectorAll(".fc-hl");
const pick = async (aside: El, key: string): Promise<void> => { option(aside, key).click(); await flush(); };
// a whole-file comment, a region comment on the picture (no anchor: kind "region"), and a resolved passage comment
const whole: StoreComment = { id: T0 + 1000 + "-3", author: "you", ts: T0 + 1000, body: "Tighten the summary throughout.", anchor: null, replies: [], resolved: false };
const region: StoreComment = { id: T0 + 2000 + "-4", author: "you", ts: T0 + 2000, body: "This axis needs a label.", target: { kind: "image", region: { x: 0.1, y: 0.2, w: 0.3, h: 0.4 }, hash: "sha256:0000" }, replies: [], resolved: false };
const done: StoreComment = { id: T0 + 3000 + "-5", author: "you", ts: T0 + 3000, body: "Resolved earlier.", anchor: { quote: "Risks remain", prefix: "", suffix: " in the fallback path." }, replies: [], resolved: true };
const h4 = H("h4", "ins", at("Risks"), at("Risks") + 5, "", "Risks", T0 - 60000);
const FIVE = [h1, h2, h3, h4, h5];                    // four paragraphs: "## Findings" (h1, h2), "We recommend" (h3), "Risks remain" (h4), "Next steps" (h5) — the fourth folds
const ALL_COMMENTS = [passage, hosted, whole, region, done];
/** The suite's world: four open comments (one on the pending change h1) and a resolved one, five pending changes. */
const full = (over: Partial<Status> = {}): Status => status({
  store: { v: 3, path: "docs/report.md", suggestions: SUGG, comments: ALL_COMMENTS }, hunks: FIVE,
  unsent: { comments: [passage.id, hosted.id, whole.id, region.id], replies: [], accepted: 0, rejected: 0, watermark: null }, ...over,
});

const savedLine = (aside: El): El | null => aside.querySelector(".fc-cards .fc-saved-hidden");
// the selection stand-in (the behavior suite's): a passage selected in the body, the seam fired, the float's Comment pressed
const RECT = { left: 100, top: 200, right: 300, bottom: 220, width: 200, height: 20 };
function textNodeWith(root: El, needle: string): { node: Txt; at: number } | null {
  for (const c of root.childNodes) {
    if (c instanceof Txt) { const i = c.data.indexOf(needle); if (i >= 0) return { node: c, at: i }; }
    else { const r = textNodeWith(c, needle); if (r) return r; }
  }
  return null;
}
function selectIn(root: El, quote: string): any {
  const hit = textNodeWith(root, quote);
  assert.ok(hit, "the passage " + JSON.stringify(quote) + " is in the DOM");
  return { rangeCount: 1, isCollapsed: false, anchorNode: hit.node, anchorOffset: hit.at, focusNode: hit.node, focusOffset: hit.at + quote.length,
    toString: () => quote, getRangeAt: () => ({ getBoundingClientRect: () => RECT }) };
}
function startPassageComment(w: World, quote: string): void {
  const sel = selectIn(w.body, quote);
  for (const cb of w.hooks.selection) cb(sel);
  const floats = doc.body.querySelectorAll(".fc-float"); const float = floats[floats.length - 1];
  assert.equal(float.hidden, false, "the float appears beside a selection in the body");
  selection = sel;
  float.click();
}
/** Type `note` in the open box and press Save; returns the posted `comment` ask. */
async function saveNote(aside: El, w: World, note: string): Promise<any> {
  const box = aside.querySelector(".fc-composer")!;
  assert.equal(box.hidden, false, "the box is open");
  (box.querySelector("textarea") as El).value = note;
  act(box, "fcsave")!.click(); await flush();
  const m = lastOf(w, "fileComments", "comment");
  assert.ok(m, "the comment went out");
  return m;
}

// ── this suite's own fixtures and helpers ──────────────────────────────────────────────────────────
const CORRUPT = "the comments for ~/notes-api/docs/report.md could not be read: the sidecar is not valid JSON";
const MOVED_STORE = "the comments for ~/notes-api/docs/report.md changed on disk since you opened the file — reload and retry";
const UNSENT_NONE = { comments: [], replies: [], accepted: 0, rejected: 0, watermark: null };
/** An untracked file with no comment, no change and no detached change: nothing to filter, so no filter row. */
const bare = (over: Partial<Status> = {}): Status => status({ trackedBy: null, hunks: [], store: { v: 3, path: "docs/report.md", suggestions: [], comments: [] }, unsent: UNSENT_NONE, ...over });
const withComments = (comments: StoreComment[], over: Partial<Status> = {}): Status =>
  full({ store: { v: 3, path: "docs/report.md", suggestions: SUGG, comments }, ...over });
/** The head's element children, each as its classes and, for a slot's row or loader, "@slot". */
const kids = (aside: El): string[] => headKids(aside).map((k) => k.classes.join(" ") + (k.dataset.slot ? "@" + k.dataset.slot : ""));
const countOf = (w: World, type: string, verb?: string) => w.posted.filter((m) => m.type === type && (verb === undefined || m.verb === verb)).length;
const marksOf = (w: World): El[] => w.body.querySelectorAll('[data-act="fcchange"]');
const errText = (row: El): string => (row.childNodes[0] as El).textContent;
const fire = (target: El, type: string, init: Init = {}): Ev => { const ev = new Ev(type, init); target.dispatchEvent(ev); return ev; };
async function mount(w: World): Promise<{ unit: El; button: El }> {
  const fc = await import("./file-comments");
  const unit = fc.fileCommentsAction.mount(w.ctx) as unknown as El;
  return { unit, button: unit.childNodes[0] as El };
}
// Rendered markdown with an embedded figure after the title (the filter suite's world): the source is DOC with the embed
// line in, the hunks moved past it, and a region comment on the figure. The picture is drawn 300×200 at (100, 200), so a
// drag's client coordinates read as fractions of it (regionFromPoints).
const shifted = (h: Hunk, n: number): Hunk => ({ ...h, curFrom: h.curFrom + n, curTo: h.curTo + n });
const EMBED = "![Figure](figure.png)\n\n";
const FIG_DOC = "# Report\n\n" + EMBED + DOC.slice("# Report\n\n".length);
const FIG_HASH = "3333333333333333333333333333333333333333333333333333333333333333";
const FIG_ANCHOR = { quote: "![Figure](figure.png)", prefix: "# Report\n\n", suffix: "\n\n## Findings" };
const figure: StoreComment = {
  id: T0 + 4000 + "-6", author: "you", ts: T0 + 4000, body: "Label the axis.",
  anchor: FIG_ANCHOR, target: { kind: "image", region: { x: 0.1, y: 0.2, w: 0.3, h: 0.4 }, hash: FIG_HASH, src: "figure.png" }, replies: [], resolved: false,
};
const IMG_RECT = { left: 100, top: 200, right: 400, bottom: 400, width: 300, height: 200 };
const figureIntro = (): El => { const img = new El("img"); img.setAttribute("src", "figure.png"); img.setAttribute("alt", "Figure"); img.rect = IMG_RECT; return el("p", img); };
const figured = (over: Partial<Status> = {}): Status => full({
  hunks: FIVE.map((h) => shifted(h, EMBED.length)),
  store: { v: 3, path: "docs/report.md", suggestions: SUGG, comments: [passage, hosted, whole, figure, done] },
  unsent: { comments: [passage.id, hosted.id, whole.id, figure.id], replies: [], accepted: 0, rejected: 0, watermark: null },
  embeddedHashes: { "figure.png": FIG_HASH }, ...over,
});
const rects = (w: World): El[] => w.body.querySelectorAll(".fc-region");

// ── the track slot's rows with no filter row ───────────────────────────────────────────────────────

test("Track changes on a file whose status is refused (no status, so no filter row): the toggle's loader, then its refusal, stand directly under the toggles' row and above the status refusal's row", async (t: TestContext) => {
  store.delete(SETTINGS_KEY);
  const w = world(); t.after(() => w.close());
  const { button } = await mount(w);
  refuse(w, lastOf(w, "fileComments", "status"), "corrupt", CORRUPT); await flush();
  button.click();
  refuse(w, lastOf(w, "fileComments", "status"), "corrupt", CORRUPT); await flush(); await flush();
  const aside = w.main.querySelector(".fileview-aside")!;
  assert.deepEqual(kids(aside), ["fc-row", "fileview-err fc-err@head"], "the status refusal's row; nothing to filter, so no filter row");
  assert.ok(act(aside, "fcreload"), "…with Reload");
  const asks = countOf(w, "fileComments", "status");
  act(aside, "fctrack")!.click(); await flush();
  assert.equal(countOf(w, "fileComments", "status"), asks + 1, "the click re-asks status under the toggle");
  assert.deepEqual(kids(aside), ["fc-row", "fileview-load fc-load@track", "fileview-err fc-err@head"], "the loader under the toggles, above the status refusal's row");
  refuse(w, lastOf(w, "fileComments", "status"), "corrupt", CORRUPT); await flush(); await flush();
  assert.deepEqual(kids(aside), ["fc-row", "fileview-err fc-err@track", "fileview-err fc-err@head"], "the refusal where the loader was: the answer to the click sits under the button that asked");
  assert.equal(errText(headKids(aside)[1]), "Nothing written: " + CORRUPT);
  assert.ok(act(headKids(aside)[2], "fcreload"), "the status refusal's row keeps its Reload below");
  store.delete(SETTINGS_KEY);
});

test("an untracked file with nothing to filter, its status held: the poll's re-read refused (the head's row), then Track changes → This file puts the scope row, the loader and the set-tracked refusal under the toggles, above the head's row; with cards the same rows stand above the filter's row and the head's row below it", async (t: TestContext) => {
  t.mock.timers.enable({ apis: ["setInterval"] });
  store.delete(SETTINGS_KEY);
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w, bare());
  assert.deepEqual(kids(aside), ["fc-row"], "the toggles' row alone: no filter row");
  w.mtimes[STORE_PATH] = "1757145600000000009";       // the sidecar moved: the poll re-asks status
  t.mock.timers.tick(2500); await flush(); await flush(); await flush();
  refuse(w, lastOf(w, "fileComments", "status"), "io", "the comments could not be read"); await flush(); await flush();
  assert.deepEqual(kids(aside), ["fc-row", "fileview-err fc-err@head"], "the re-read's refusal, over the status still showing");
  act(aside, "fctrack")!.click();
  assert.deepEqual(kids(aside), ["fc-row", "fc-row fc-choice", "fileview-err fc-err@head"], "the scope choice under the toggles");
  act(aside, "fctrackfile")!.click(); await flush();
  assert.deepEqual(kids(aside), ["fc-row", "fileview-load fc-load@track", "fileview-err fc-err@head"], "the loader while the set-tracked is out, in the choice's place");
  const m = lastOf(w, "fileComments", "set-tracked");
  assert.deepEqual(m.args, { on: true, scope: "file" });
  refuse(w, m, "io", "the tracking config could not be written"); await flush(); await flush();
  assert.deepEqual(kids(aside), ["fc-row", "fileview-err fc-err@track", "fileview-err fc-err@head"], "the refusal under the toggle that asked; the head's row keeps its place below");
  assert.equal(errText(headKids(aside)[1]), "the tracking config could not be written");
  w.close();
  // with cards: the filter's row between the track slot's rows and the head's
  const w2 = world(); t.after(() => w2.close());
  const { aside: a2 } = await openPanel(w2, full({ trackedBy: null }));
  act(a2, "fctrack")!.click(); act(a2, "fctrackfile")!.click(); await flush();
  assert.deepEqual(kids(a2), ["fc-row", "fileview-load fc-load@track", "fc-row fc-filter"], "the loader between the toggles' row and the filter's");
  refuse(w2, lastOf(w2, "fileComments", "set-tracked"), "io", "the tracking config could not be written"); await flush(); await flush();
  assert.deepEqual(kids(a2), ["fc-row", "fileview-err fc-err@track", "fc-row fc-filter"]);
  act(a2, "fcerrx")!.click();
  assert.deepEqual(kids(a2), ["fc-row", "fc-row fc-filter"]);
  w2.mtimes[STORE_PATH] = "1757145600000000009";
  t.mock.timers.tick(2500); await flush(); await flush(); await flush();
  refuse(w2, lastOf(w2, "fileComments", "status"), "io", "the comments could not be read"); await flush(); await flush();
  assert.deepEqual(kids(a2), ["fc-row", "fc-row fc-filter", "fileview-err fc-err@head"], "the head's row below the filter's");
  act(a2, "fctrack")!.click(); act(a2, "fctrackfile")!.click(); await flush();
  assert.deepEqual(kids(a2), ["fc-row", "fileview-load fc-load@track", "fc-row fc-filter", "fileview-err fc-err@head"]);
  refuse(w2, lastOf(w2, "fileComments", "set-tracked"), "io", "the tracking config could not be written"); await flush(); await flush();
  assert.deepEqual(kids(a2), ["fc-row", "fileview-err fc-err@track", "fc-row fc-filter", "fileview-err fc-err@head"], "the same order with every row present");
  store.delete(SETTINGS_KEY);
});

// ── the Changes empty state keeps a refused decision's row ─────────────────────────────────────────

test("Accept all under Changes, refused store-moved, and the re-read leaves no change pending: the Changes empty line shows and, under it, the 'Nothing decided' row with its ✕ — the clicked decision is not silent", async (t: TestContext) => {
  store.set(SETTINGS_KEY, JSON.stringify({ commentsFilter: "changes" }));
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w, status({ hunks: [h1], store: { v: 3, path: "docs/report.md", suggestions: [SUGG[0]], comments: [passage] } }));
  assert.deepEqual(chosen(aside), ["changes"]);
  assert.deepEqual(changeCards(aside).map((c) => c.dataset.id), ["chg:h1"]);
  assert.ok(aside.querySelector(".fc-foot"), "Accept all · Reject all");
  act(aside, "fcacceptall")!.click(); await flush();
  const acc = lastOf(w, "fileComments", "accept-all");
  assert.ok(acc, "the decision went out");
  refuse(w, acc, "store-moved", MOVED_STORE); await flush();
  // the fresh status a moved fence asks for: another client decided the change meanwhile
  answer(w, status({ storeMtimeNs: "1757145600000000009", hunks: [], store: { v: 3, path: "docs/report.md", suggestions: [], comments: [passage] } })); await flush(); await flush();
  assert.equal(countOf(w, "fileComments", "accept-all"), 1, "no retry of an id-less verb");
  assert.equal(aside.querySelector(".fc-foot"), null, "nothing pending: no foot");
  const list = aside.querySelector(".fc-cards")!;
  const empty = list.querySelector(".fc-empty")!;
  assert.equal(empty.textContent, "No changes are pending. All or Comments above shows the comments.");
  const row = list.querySelector('.fc-err[data-slot="changes"]')!;
  assert.ok(row, "the refusal's row, in the list where the foot was");
  assert.equal(errText(row), "Nothing decided: " + MOVED_STORE + ". The list of changes was re-read; look it over and try again.");
  assert.ok(list.childNodes.indexOf(row) > list.childNodes.indexOf(empty), "under the empty line");
  assert.deepEqual(chosen(aside), ["changes"], "the kept choice stands");
  act(row, "fcerrx")!.click();
  assert.equal(aside.querySelector('.fc-err[data-slot="changes"]'), null, "the ✕ clears it");
  await pick(aside, "all");
  assert.ok(card(aside, passage.id), "All: the comment the line pointed to");
  store.delete(SETTINGS_KEY);
});

// ── the saved line: a region comment's mark, and the comment a change comes to answer ──────────────

test("a region comment saved under Changes, drawn on a figure in rendered markdown: the line names the card and the rectangle, neither shown; All shows both and ends the line", async (t: TestContext) => {
  store.set(SETTINGS_KEY, JSON.stringify({ commentsFilter: "changes" }));
  const w = world({ mode: "rendered", src: FIG_DOC, intro: figureIntro }); t.after(() => w.close());
  const { aside } = await openPanel(w, figured());
  assert.deepEqual(chosen(aside), ["changes"]);
  const overlay = w.body.querySelector(".fileview-md .fc-imgwrap .fc-overlay")!;
  assert.ok(overlay, "the figure's overlay is up: the panel is open");
  assert.equal(overlay.classes.includes("fc-overlay-off"), false, "and armed: Changes withholds the marks, not the drag");
  assert.deepEqual(rects(w), [], "Changes: the earlier region comment's rectangle is withheld");
  fire(overlay, "pointerdown", { clientX: 150, clientY: 240, pointerId: 7, button: 0 });
  fire(overlay, "pointermove", { clientX: 250, clientY: 300, pointerId: 7 });
  assert.ok(overlay.querySelector(".fc-draw"), "the band while dragging");
  fire(overlay, "pointerup", { clientX: 250, clientY: 300, pointerId: 7 });
  const box = aside.querySelector(".fc-composer")!;
  assert.equal(box.hidden, false, "the composer opens on the region");
  const m = await saveNote(aside, w, "Name the axis.");
  assert.equal(m.args.note, "Name the axis.");
  assert.deepEqual(m.args.target, { kind: "image", region: { x: 0.1667, y: 0.2, w: 0.3333, h: 0.3 }, src: "figure.png" }, "the region as fractions of the drawn picture, on the figure's source");
  assert.equal(m.args.anchor.quote, "![Figure](figure.png)", "a figure in rendered markdown: the embed line's anchor rides along");
  assert.equal(m.args.anchor.prefix, "# Report\n\n");
  const fresh: StoreComment = { id: T0 + 9800 + "-13", author: "you", ts: T0 + 9800, body: "Name the axis.", anchor: m.args.anchor,
    target: { kind: "image", region: { x: 0.1667, y: 0.2, w: 0.3333, h: 0.3 }, hash: FIG_HASH, src: "figure.png" }, replies: [], resolved: false };
  answer(w, figured({ store: { v: 3, path: "docs/report.md", suggestions: SUGG, comments: [passage, hosted, whole, figure, done, fresh] }, storeMtimeNs: "1757145600000000010" }), m); await flush(); await flush();
  assert.equal(box.hidden, true, "saved: the box closed");
  assert.equal(card(aside, fresh.id), null, "the card is hidden: Changes is chosen");
  assert.deepEqual(rects(w), [], "…and its rectangle with it");
  assert.equal(overlay.querySelector(".fc-region-pending"), null, "the pending region left with the save");
  const line = savedLine(aside);
  assert.ok(line, "the line for the hidden card");
  assert.equal(line!.dataset.id, fresh.id);
  assert.equal(line!.textContent, "Your comment is saved; its card and rectangle are hidden while Changes is chosen above (All or Comments shows them).✕", "a region comment's mark is the rectangle, never a highlight");
  await pick(aside, "all");
  assert.ok(card(aside, fresh.id), "All shows the card");
  assert.deepEqual(rects(w).map((r) => r.dataset.id).sort(), [figure.id, fresh.id].sort(), "…and the rectangle, beside the earlier one");
  assert.equal(savedLine(aside), null, "the line is over");
  store.delete(SETTINGS_KEY);
});

test("the saved line stands when the session answers the comment with a revision: a passage comment saved under Changes, then bound to a change by the poll's status (suggestionId), keeps its own card, hidden like every comment under Changes, so the line stays as it was; the change card counts the comment, and the count's click (All, the card shown) ends the line, for good", async (t: TestContext) => {
  t.mock.timers.enable({ apis: ["setInterval"] });
  store.set(SETTINGS_KEY, JSON.stringify({ commentsFilter: "changes" }));
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w, full());
  startPassageComment(w, "fallback path");
  const m = await saveNote(aside, w, "Name the risks.");
  const fresh: StoreComment = { id: T0 + 9500 + "-10", author: "you", ts: T0 + 9500, body: "Name the risks.", anchor: { quote: "fallback path", prefix: "Risks remain in the ", suffix: "." }, replies: [], resolved: false };
  answer(w, withComments([...ALL_COMMENTS, fresh], { storeMtimeNs: "1757145600000000007" }), m); await flush(); await flush();
  const LINE = "Your comment is saved; its card and highlight are hidden while Changes is chosen above (All or Comments shows them).✕";
  assert.equal(savedLine(aside)?.textContent, LINE, "the line for the hidden card");
  assert.ok(!card(aside, fresh.id), "the card is hidden: Changes is chosen");
  assert.ok(!card(aside, "chg:h4")!.querySelector(".fc-about-count"), "h4's card counts no comment yet");
  // the session revises the passage in answer (track-edit --thread): the comment keeps its anchor and gains the change's id;
  // the sidecar moved, so the poll re-reads
  const asks = countOf(w, "fileComments", "status");
  w.mtimes[STORE_PATH] = "1757145600000000008";
  t.mock.timers.tick(2500); await flush(); await flush(); await flush();
  assert.equal(countOf(w, "fileComments", "status"), asks + 1, "the moved sidecar re-asks status");
  answer(w, withComments([...ALL_COMMENTS, { ...fresh, suggestionId: "h4" }], { storeMtimeNs: "1757145600000000008" })); await flush(); await flush();
  // every comment is its own card (the about follow-on, 2026-09-10): the answered comment is hidden under Changes like the
  // rest, so the line stands with its words unchanged. Before the follow-on the comment was drawn inside h4's card and the
  // line ended here; now the change card counts the comment instead, and the count is the way to it.
  assert.equal(savedLine(aside)?.textContent, LINE, "the line stands, its words unchanged: the comment's card is still hidden");
  assert.equal(savedLine(aside)!.dataset.id, fresh.id, "and still the saved comment's");
  assert.ok(!card(aside, fresh.id), "the comment's own card is hidden under Changes, answered or not");
  assert.equal(aside.querySelectorAll(".fc-hosted").length, 0, "no comment is drawn inside a change card");
  const h4card = card(aside, "chg:h4");
  assert.ok(h4card, "the change card, in the third group (shown)");
  const count = h4card!.querySelector(".fc-about-count");
  assert.ok(count, "the change card counts the comment the change answered");
  assert.equal(count!.textContent, "1 comment");
  assert.equal(count!.dataset.act, "fcaboutfirst"); assert.equal(count!.dataset.id, "h4");
  assert.equal(count!.title, "Show the comment about this change");
  // the count's click: All first (Changes hides the comment cards), then the comment's own card, open; the card seen, the
  // line is over and does not come back
  count!.click(); await flush();
  assert.deepEqual(chosen(aside), ["all"], "Changes hid the comment cards: All is chosen for the click");
  const own = card(aside, fresh.id);
  assert.ok(own, "the comment's own card");
  assert.ok(own!.classes.includes("open"), "open: the first (and only) comment about h4");
  const tag = own!.querySelector(".fc-card-head .fc-about");
  assert.ok(tag, "the tag naming the change that answered it");
  assert.equal(tag!.textContent, "answered by a change"); assert.equal(tag!.dataset.refs, "h4");
  assert.ok(tag!.title.startsWith("The session answered this comment with: "), tag!.title);
  assert.equal(own!.querySelector(".fc-kind")!.title, "A comment on a passage", "a passage comment the session answered keeps its kind");
  assert.ok(!savedLine(aside), "the card shown: the line is over");
  await pick(aside, "changes");
  assert.ok(!savedLine(aside), "and the line does not come back");
  assert.ok(!card(aside, fresh.id), "Changes hides the card again; the count on h4's card is the way to it");
  assert.equal(card(aside, "chg:h4")!.querySelector(".fc-about-count")!.textContent, "1 comment");
  store.delete(SETTINGS_KEY);
});

// ── Show changes inline under Comments ─────────────────────────────────────────────────────────────

test("Show changes inline under Comments: the toggle stays (its setting governs All, Changes and other panels) and its title says the filter hides the marks; a click flips the setting with no mark painted; the read view's own titles are back under All or Changes", async (t: TestContext) => {
  store.delete(SETTINGS_KEY);
  const ON = "The session's changes are marked in the text, insertions tinted and deletions struck; click to read the file without the marks";
  const OFF = "The marks are off and the file reads as it is; click to mark the session's changes in the text";
  const ON_WITHHELD = "Comments above hides the change marks with the change cards; under All or Changes the session's changes are marked in the text. Click to read the file without the marks there too";
  const OFF_WITHHELD = "The marks are off, and Comments above hides them with the change cards; click to mark the session's changes in the text under All or Changes";
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w, full());
  assert.equal(act(aside, "fcinline")!.title, ON); assert.equal(marksOf(w).length, 6);
  await pick(aside, "comments");
  assert.equal(marksOf(w).length, 0, "Comments: no change mark in the text");
  let b = act(aside, "fcinline")!;
  assert.ok(b, "the toggle is offered: the setting reaches All, Changes and other panels");
  assert.equal(b.dataset.on, "1"); assert.equal(b.getAttribute("aria-pressed"), "true");
  assert.equal(b.title, ON_WITHHELD, "the title does not claim marks in a text that carries none");
  b.click(); await flush();
  assert.equal(marksOf(w).length, 0, "off: still none");
  b = act(aside, "fcinline")!;
  assert.equal(b.dataset.on, "0"); assert.equal(b.getAttribute("aria-pressed"), "false");
  assert.equal(b.title, OFF_WITHHELD);
  assert.equal(stored()!.changesInline, false, "the setting flipped, for the views that show it");
  await pick(aside, "changes");
  assert.equal(marksOf(w).length, 0, "Changes with the marks off: the cards and no mark");
  assert.equal(act(aside, "fcinline")!.title, OFF, "the read view's own title where the setting shows");
  act(aside, "fcinline")!.click(); await flush();
  assert.equal(marksOf(w).length, 6, "on again: the marks under Changes");
  assert.equal(act(aside, "fcinline")!.title, ON);
  await pick(aside, "all");
  assert.equal(marksOf(w).length, 6); assert.equal(act(aside, "fcinline")!.title, ON);
  await pick(aside, "comments");
  assert.equal(marksOf(w).length, 0); assert.equal(act(aside, "fcinline")!.title, ON_WITHHELD);
  store.delete(SETTINGS_KEY);
});

// ── source pins ────────────────────────────────────────────────────────────────────────────────────

test("pins: with no filter row the move's anchor is the first of the head's other rows, set between the rows' build and the move (an insertBefore with no anchor appends); the inline title reads the filter", () => {
  const head = SRC.slice(SRC.indexOf("private renderHead("), SRC.indexOf("private renderComposer("));
  const a = head.indexOf('for (const n of [this.loader("track"), this.errRow("track"), this.errRow("head"), this.errRow("poll"), this.errRow("edit")]) if (n) head.appendChild(n);');
  const b = head.indexOf('if (!filterRow) filterRow = (Array.from(head.childNodes) as HTMLElement[]).find((n) => n.nodeType === 1 && ["head", "poll", "edit"].includes(n.dataset.slot || "")) || null;');
  const c = head.indexOf('if (n.nodeType === 1 && (n as HTMLElement).dataset.slot === "track") underToggles(n as HTMLElement);');
  assert.ok(a >= 0 && b > a && c > b, "the head's rows built, the anchor set, then the track rows moved");
  assert.match(head, /const withheld = this\.activeFilter\(\) === "comments";\n\s+i\.title = withheld\n/, "the toggle's title by the filter, the button offered all the same");
});

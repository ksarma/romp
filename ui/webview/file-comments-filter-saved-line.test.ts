// The Comments panel's saved line (noteHiddenSave / hiddenSavedRow; the filter follow-on to plans/file-review.md,
// 2026-09-07), after the slice's third review: the cases the two review suites left untested, driven AS A PANEL over the
// filter-fixes suite's DOM stand-in (its harness, copied).
//   • the status that answers a save can carry more than one comment the list did not hold before it — a session's,
//     written inside the poll window (track-comment, or track-edit --thread minting a comment on its change), lands in the
//     same sidecar re-read, and cardModel sorts by ts, so an older one is FIRST among the fresh. The line must track the
//     comment in the person's words, whatever landed beside it: a session's comment taken for the saved one puts the wrong
//     id, and the wrong mark word, on the line (before the about follow-on, 2026-09-10, a session's comment on a pending
//     change taken for the saved one ended the line before it started, the comment being drawn inside the change card;
//     now every comment is its own card, hidden under Changes alike, and the change card counts it). Both suites answered
//     every save with exactly one fresh comment, so the selection was untested;
//   • the row's shape: .fc-note (0.86em) on the words alone, the ✕ a .fileview-btn (0.82em) directly under the unsized
//     .fc-row — on the row, the class compounded the button to 0.705em, smaller than every other panel button and than the
//     ✕ of the err row the same list can show a line below (ui/CLAUDE.md, font sizes: nested em compounds). The confirm
//     rows put the class on their span the same way; file-comments-saved-line-sizes.test.ts resolves the sheets over it;
//   • the data-cue setters' comments name the tokens the sheets' rules read (--accent, --text-muted), as the plan and the
//     sheets' comment do since the reviews replaced the figure that named none.
// Synthetic fixtures only: the notes-api world, placeholder ids.
import { test, type TestContext } from "node:test";
import * as assert from "node:assert/strict";
import { inspect } from "node:util";
import * as fs from "node:fs";
import * as path from "node:path";
import type { FileViewActionCtx, TrackedEdit } from "./file-view";
import { type Status, type Hunk, type StoreComment } from "./file-comments-model";
import { assertHiddenEvent, hideEdges, staysEnumerable } from "../test-dom-shim";

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
  constructor(public type: string, init: Init = {}) { this.key = init.key || ""; this.clientX = init.clientX ?? 0; this.clientY = init.clientY ?? 0; this.pointerId = init.pointerId ?? 1; this.button = init.button ?? 0; this.buttons = init.buttons ?? 1; hideEdges(this); }
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
  // the file's own Ev hides target and currentTarget the same way (hideEdges(this) at the end of its constructor)
  assertHiddenEvent(new Ev("click"), root, kid);
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
const MOVED_STORE = "the comments for ~/notes-api/docs/report.md changed on disk since you opened the file — reload and retry";
const withComments = (comments: StoreComment[], over: Partial<Status> = {}): Status =>
  full({ store: { v: 3, path: "docs/report.md", suggestions: SUGG, comments }, ...over });
const errText = (row: El): string => (row.childNodes[0] as El).textContent;
/** Every ancestor of `n` up to the panel's root, classes joined — the chain a sheet's font-size rules resolve over. */
const ancestry = (n: El): string[] => { const out: string[] = []; for (let p = n.parentNode; p && !p.classes.includes("fc-panel"); p = p.parentNode) out.unshift(p.classes.join(".")); return out; };
// a session's comments, written inside the poll window before the person's save landed: an older ts than the saved one,
// so cardModel (ts ascending) puts them first among the comments the list did not hold before the save
const onH2: StoreComment = { id: T0 + 8500 + "-8", author: "api", authorId: SID, ts: T0 + 8500, body: "Which percentile do you mean?", suggestionId: "h2", replies: [], resolved: false };
const onFile: StoreComment = { id: T0 + 8600 + "-8", author: "api", authorId: SID, ts: T0 + 8600, body: "The summary repeats the findings.", anchor: null, replies: [], resolved: false };

// ── several comments landing with the save ─────────────────────────────────────────────────────────

test("a whole-file comment saved under Changes, the status answering the save carrying a session's comment on a pending change too, older and so first among the fresh: the line is the saved comment's; the session's is its own card, hidden by the choice as well, and counted on its change card", async (t: TestContext) => {
  store.set(SETTINGS_KEY, JSON.stringify({ commentsFilter: "changes" }));
  const w = world(); t.after(() => w.close());
  const { aside, button } = await openPanel(w, full());
  assert.deepEqual(chosen(aside), ["changes"]);
  act(aside, "fcfile")!.click();
  const m = await saveNote(aside, w, "Tighten the summary.");
  assert.deepEqual(m.args, { note: "Tighten the summary." });
  const mine: StoreComment = { id: T0 + 9000 + "-9", author: "you", ts: T0 + 9000, body: "Tighten the summary.", anchor: null, replies: [], resolved: false };
  // the host answers with the sidecar re-read after its write: the session's comment on h2 is in it, and older
  answer(w, withComments([...ALL_COMMENTS, onH2, mine], { storeMtimeNs: "1757145600000000006" }), m); await flush(); await flush();
  assert.equal(aside.querySelector(".fc-composer")!.hidden, true, "saved: the box closed");
  assert.ok(!card(aside, mine.id), "the saved comment's card is hidden: Changes is chosen");
  assert.ok(!card(aside, onH2.id), "the session's comment is its own card (the about follow-on, 2026-09-10), hidden by the choice too");
  assert.equal(button.textContent, "Comments · 6 · 5 changes", "both comments counted");
  const line = savedLine(aside);
  assert.ok(line, "the line for the hidden card: the session's comment, first among the fresh, is not the one saved");
  assert.equal(line!.dataset.id, mine.id, "the line tracks the comment in the person's words");
  assert.equal(line!.textContent, "Your comment is saved; its card is hidden while Changes is chosen above (All or Comments shows it).✕", "a whole-file comment: the card alone, no mark");
  assert.equal(aside.querySelectorAll(".fc-saved-hidden").length, 1, "one line: the save's, none for the session's comment");
  // the session's comment on h2 is counted on h2's card, collapsed or open, never drawn inside it (before the about
  // follow-on it was, as a comment on a change under Changes)
  assert.equal(aside.querySelectorAll(".fc-hosted").length, 0, "no comment is drawn inside a change card");
  const count = card(aside, "chg:h2")!.querySelector(".fc-about-count");
  assert.ok(count, "h2's card counts the session's comment");
  assert.equal(count!.textContent, "1 comment"); assert.equal(count!.dataset.act, "fcaboutfirst"); assert.equal(count!.dataset.id, "h2");
  card(aside, "chg:h2")!.querySelector(".fc-card-head")!.click();
  assert.equal(card(aside, "chg:h2")!.querySelector(".fc-about-count")!.textContent, "1 comment", "open, the count stands in the head");
  assert.equal(aside.querySelectorAll(".fc-hosted").length, 0);
  assert.ok(!card(aside, onH2.id), "the session's comment stays hidden under Changes with the card open");
  assert.deepEqual(chosen(aside), ["changes"], "the kept choice stands");
  await pick(aside, "all");
  assert.ok(card(aside, mine.id), "All shows the card");
  const own = card(aside, onH2.id);
  assert.ok(own, "and the session's own card");
  const tag = own!.querySelector(".fc-card-head .fc-about");
  assert.ok(tag, "wearing the tag that names the change it answered");
  assert.equal(tag!.textContent, "answered by a change"); assert.equal(tag!.dataset.refs, "h2");
  assert.equal(own!.querySelector(".fc-kind")!.title, "A comment the session answered with a change", "no passage, the session's own binding: the title says answered (the review, 2026-09-10)");
  assert.ok(!savedLine(aside), "and the line is over");
  store.delete(SETTINGS_KEY);
});

test("a passage comment saved under Changes, a session's whole-file comment having landed first: the line is the saved comment's and names its highlight; the session's comment is hidden by the choice as well, with no line — the line is about the save", async (t: TestContext) => {
  store.set(SETTINGS_KEY, JSON.stringify({ commentsFilter: "changes" }));
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w, full());
  assert.equal(highlights(w).length, 0, "Changes: no highlight painted");
  startPassageComment(w, "fallback path");
  const m = await saveNote(aside, w, "Name the risks.");
  assert.equal(m.args.anchor.quote, "fallback path");
  const mine: StoreComment = { id: T0 + 9500 + "-10", author: "you", ts: T0 + 9500, body: "Name the risks.", anchor: { quote: "fallback path", prefix: "Risks remain in the ", suffix: "." }, replies: [], resolved: false };
  answer(w, withComments([...ALL_COMMENTS, onFile, mine], { storeMtimeNs: "1757145600000000007" }), m); await flush(); await flush();
  const line = savedLine(aside);
  assert.ok(line, "the line for the hidden card");
  assert.equal(line!.dataset.id, mine.id, "the saved comment's id, not the session's (first among the fresh)");
  assert.equal(line!.textContent, "Your comment is saved; its card and highlight are hidden while Changes is chosen above (All or Comments shows them).✕", "the saved comment's mark, a highlight — the session's whole-file comment has none");
  assert.equal(card(aside, mine.id), null); assert.equal(card(aside, onFile.id), null, "the session's comment is hidden by the choice too");
  assert.equal(highlights(w).length, 0, "the highlight is hidden with the card");
  assert.equal(aside.querySelectorAll(".fc-saved-hidden").length, 1, "one line: the save's");
  await pick(aside, "all");
  assert.ok(card(aside, mine.id) && card(aside, onFile.id), "All shows both cards");
  assert.equal(w.body.querySelectorAll('.fc-hl[data-id="' + mine.id + '"]').length, 1, "and the saved comment's highlight, beside the others All paints");
  assert.equal(savedLine(aside), null, "the line is over");
  store.delete(SETTINGS_KEY);
});

// ── the row's shape ────────────────────────────────────────────────────────────────────────────────

test("the saved line: .fc-note on the words alone, the ✕ a .fileview-btn.fc-x directly under the unsized .fc-row — the shape of the confirm rows, and of the err row the same list shows under the Changes empty line after a refused Accept all", async (t: TestContext) => {
  store.set(SETTINGS_KEY, JSON.stringify({ commentsFilter: "changes" }));
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w, full({ trackedBy: { kind: "folder", entry: "docs" } }));
  act(aside, "fcfile")!.click();
  const m = await saveNote(aside, w, "Tighten the summary.");
  const mine: StoreComment = { id: T0 + 9000 + "-9", author: "you", ts: T0 + 9000, body: "Tighten the summary.", anchor: null, replies: [], resolved: false };
  answer(w, withComments([...ALL_COMMENTS, mine], { storeMtimeNs: "1757145600000000006", trackedBy: { kind: "folder", entry: "docs" } }), m); await flush(); await flush();
  const list = aside.querySelector(".fc-cards")!;
  const line = savedLine(aside)!;
  assert.ok(line, "the line for the hidden card");
  assert.deepEqual(line.classes, ["fc-row", "fc-saved-hidden"], "the row: .fc-row (unsized) and the line's own class, never .fc-note");
  assert.equal(line.childNodes.length, 2, "the words and the ✕");
  const [words, x] = line.childNodes as El[];
  assert.equal(words.tagName, "SPAN"); assert.deepEqual(words.classes, ["fc-note"], ".fc-note on the words' span");
  assert.equal(x.tagName, "BUTTON"); assert.deepEqual(x.classes, ["fileview-btn", "fc-x"]); assert.equal(x.dataset.act, "fchiddenx");
  assert.equal(x.parentNode, line, "the ✕ directly under the row");
  assert.equal(line.parentNode, list, "the row directly under the list");
  assert.deepEqual(ancestry(x), ["fc-sec-cards", "fc-cards", "fc-row.fc-saved-hidden"], "no sized ancestor between the panel and the ✕: .fileview-btn's own size is what it renders at");
  // the confirm rows, the precedent: the Stop confirm puts .fc-note on its span, its buttons beside it under the bare row
  act(aside, "fctrack")!.click();
  const stop = aside.querySelector(".fc-head .fc-choice")!;
  assert.deepEqual(stop.classes, ["fc-row", "fc-choice"]);
  assert.deepEqual((stop.childNodes[0] as El).classes, ["fc-note"], "the confirm's words wear the class");
  assert.equal(stop.querySelector('[data-act="fctrackstop"]')!.parentNode, stop, "…and its buttons are the row's own children");
  act(aside, "fctrackcancel")!.click();
  // Accept all refused store-moved, the re-read leaving no change pending: the err row lands in the same list under the
  // Changes empty line, its ✕ directly under a row directly under the list — the two ✕ share their ancestry down to the row
  act(aside, "fcacceptall")!.click(); await flush();
  const acc = lastOf(w, "fileComments", "accept-all");
  assert.ok(acc, "the decision went out");
  refuse(w, acc, "store-moved", MOVED_STORE); await flush();
  answer(w, status({ trackedBy: { kind: "folder", entry: "docs" }, storeMtimeNs: "1757145600000000009", hunks: [], store: { v: 3, path: "docs/report.md", suggestions: [], comments: [passage, whole, mine] } })); await flush(); await flush();
  const list2 = aside.querySelector(".fc-cards")!;
  const line2 = savedLine(aside)!;
  assert.ok(line2, "the saved line stands: the comment is still on no change, and Changes is still chosen");
  assert.equal(list2.childNodes[0], line2, "first in the list");
  assert.equal((list2.childNodes[1] as El).textContent, "No changes are pending. All or Comments above shows the comments.");
  const err = list2.querySelector('.fc-err[data-slot="changes"]')!;
  assert.ok(err, "the refusal's row, in the list where the foot was");
  assert.equal(errText(err), "Nothing decided: " + MOVED_STORE + ". The list of changes was re-read; look it over and try again.");
  const errX = act(err, "fcerrx")!;
  assert.equal(errX.parentNode, err); assert.equal(err.parentNode, list2);
  assert.deepEqual(ancestry(errX).slice(0, -1), ancestry(act(line2, "fchiddenx")!).slice(0, -1), "the two ✕: the same ancestry down to their rows");
  assert.deepEqual(ancestry(line2), ancestry(err), "…which are siblings in the list");
  store.delete(SETTINGS_KEY);
});

// ── source pins ────────────────────────────────────────────────────────────────────────────────────

test("pins: noteHiddenSave takes the fresh comment in the person's words (the host's author, the trimmed body), the newest fresh one failing that; the row's builders; the data-cue setters' comments name the tokens the sheets' rules read", () => {
  assert.match(SRC, /const fresh = this\.cards\(\)\.filter\(\(x\) => !before\.has\(x\.id\)\);\n\s+const mine = fresh\.find\(\(x\) => x\.author === "you" && x\.body === note\) \|\| fresh\[fresh\.length - 1\] \|\| null;/,
    "the comment in the person's words among the fresh, else the newest fresh — never the first, which cardModel's ts order gives to an older comment landing beside the save");
  // the host writes the person's comments as this author, and trims the body as saveComposer does (`note = this.input.value.trim()`)
  const host = fs.readFileSync(path.resolve(process.cwd(), "..", "tools", "file-comments-host.mjs"), "utf8");
  assert.match(host, /^export const AUTHOR = 'you';$/m, "the host's author for the person's comments is the one noteHiddenSave looks for");
  assert.match(SRC, /const note = this\.input\.value\.trim\(\);/, "the body the panel sends is the trimmed words, the body the host stores");
  // the row: the class on the words, the ✕ the row's own child
  assert.match(SRC, /const row = el\("div", "fc-row fc-saved-hidden"\);\n\s+row\.dataset\.id = card\.id;\n\s+row\.appendChild\(el\("span", "fc-note", "Your comment is saved; its card"/, ".fc-note on the span, the row unsized");
  assert.match(SRC, /const x = btn\("✕", "fchiddenx", "fileview-btn fc-x"\); x\.setAttribute\("aria-label", "Dismiss"\); row\.appendChild\(x\);\n\s+return row;/);
  // the setters' comments: the tokens, as the plan (tools/file-review-plan-kind-cue.test.mjs) and the sheets' comment
  // (feed-css-kind-cue.test.ts) name them; the figure the reviews replaced is gone from this file too
  assert.match(SRC, /card\.dataset\.cue = "comment";\s+\/\/ the left edge's colour: --accent for a comment \(a region is one\) — the sheets' \[data-cue\] rules/);
  assert.match(SRC, /card\.dataset\.cue = "change";\s+\/\/ the left edge's colour: --text-muted for a change — the sheets' \[data-cue\] rules/);
  assert.doesNotMatch(SRC, /muted tone/, "a tone in place of the token names nothing a reader can find in the sheet: say --text-muted");
  for (const f of ["styles.css", "feed.css"]) {
    const css = web(f);
    assert.ok(css.includes('\n.fc-card[data-cue="change"]:not(.fc-card-detached) { border-left: 3px solid var(--text-muted); }\n'), f + ": the change edge reads --text-muted, the token the setter's comment names");
    assert.ok(css.includes('\n.fc-card[data-cue="comment"]:not(.fc-card-detached) { border-left: 3px solid var(--accent); }\n'), f + ": the comment edge reads --accent");
  }
});

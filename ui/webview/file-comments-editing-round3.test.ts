// The Comments panel's third review round over editing (plans/file-review.md, Slice 5; the 2026-09-06 review of the
// slice, round 3). Four findings, each driven as a panel over the behavior suite's DOM stand-in, with the viewer's edit
// mode and the seam as closures:
//   • Edit before the first status has answered: the editor carries no marks, and the status that then shows the file's
//     pending changes must not let Save write the editor's empty list over them (the host would take it as the sidecar's
//     new contents and drop every change with no decision logged). The head says so at once, Save refuses in the same
//     words and asks the kernel nothing, and Cancel then Edit again carries the changes in. A file that moved as well is
//     left to the host's file fence, as the moved-file row promised.
//   • While the editor is up the cards group over the text the status's offsets index — the file as the editor loaded it,
//     or the last landed save's content — never the buffer, which typing moves under the offsets; the composer's
//     passage-changed tag reads the same text.
//   • On a coarse primary pointer the decide-in-editor words lead with the route a finger has (Save or Cancel, then the
//     buttons) and name the mouse gesture as one; the same words in the caption, the tooltips and the refusal row.
//   • The Reject-all confirm does not survive an Edit: opened, then Edit, it is not back re-counted when the editor closes.
// Synthetic fixtures only: the notes-api world, placeholder ids.
import { test, type TestContext } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import type { FileViewActionCtx, TrackedEdit } from "./file-view";
import type { Status, StoreComment, Hunk } from "./file-comments-model";
import { MOVED_UNDER_EDIT } from "./file-comments-model";

const web = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const SRC = web("file-comments.ts");

// ── a DOM stand-in: ancestry, attributes, events with capture and bubbling, a small selector engine ──
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
  parentNode: El | null = null;
  childNodes: Array<El | Txt> = [];
  attrs = new Map<string, string>();
  listeners: Reg[] = [];
  hidden = false; disabled = false; readOnly = false; title = ""; type = ""; value = ""; checked = false; placeholder = "";
  innerHTML = "";
  style: Record<string, string> = {};
  rect = { left: 0, top: 0, right: 0, bottom: 0, width: 0, height: 0 };
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
  get tabIndex(): number { return this.attrs.has("tabindex") ? Number(this.attrs.get("tabindex")) : -1; }
  set tabIndex(v: number) { this.attrs.set("tabindex", String(v)); }
  dataset: Record<string, string> = new Proxy({} as Record<string, string>, {
    get: (_, k) => this.attrs.get("data-" + kebab(String(k))) as string,
    set: (_, k, v) => { this.attrs.set("data-" + kebab(String(k)), String(v)); return true; },
    has: (_, k) => this.attrs.has("data-" + kebab(String(k))),
    deleteProperty: (_, k) => { this.attrs.delete("data-" + kebab(String(k))); return true; },
  });
  get textContent(): string { return this.childNodes.map((c) => c.textContent).join(""); }
  set textContent(v: string) { for (const c of this.childNodes) c.parentNode = null; this.childNodes = []; if (v !== "") this.appendChild(new Txt(v)); }
  private detach(n: El | Txt): void { const p = n.parentNode; if (p) { const i = p.childNodes.indexOf(n); if (i >= 0) p.childNodes.splice(i, 1); n.parentNode = null; } }
  appendChild<T extends El | Txt>(n: T): T { this.detach(n); this.childNodes.push(n); n.parentNode = this; return n; }
  insertBefore<T extends El | Txt>(n: T, ref: El | Txt | null): T {
    if (!ref) return this.appendChild(n);
    this.detach(n);
    const i = this.childNodes.indexOf(ref);
    this.childNodes.splice(i < 0 ? this.childNodes.length : i, 0, n); n.parentNode = this; return n;
  }
  removeChild<T extends El | Txt>(n: T): T { this.detach(n); return n; }
  replaceChildren(...c: Array<El | Txt>): void { for (const x of this.childNodes) x.parentNode = null; this.childNodes = []; for (const x of c) this.appendChild(x); }
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


// ── fixtures: the notes-api world, with two pending changes ────────────────────────────────────────
const SID = "11111111-2222-3333-4444-555555555555";
const ABS = "/repo/notes-api/docs/report.md";
const ROOT = "/repo/notes-api";
const STORE_PATH = ROOT + "/.trackchanges/docs%2Freport.md.json";
const T0 = 1757145600000;
const QUOTE = "shipping the cache in v1.2";
const DOC = "# Report\n\n## Findings\nThe api session cut p95 latency by 40% and the p99 by 10%.\n\nWe recommend " + QUOTE + ".\n\nMore text here.\n";
const passage: StoreComment = {
  id: T0 + "-118", author: "you", ts: T0, body: "Which cache? Say which.",
  anchor: { quote: QUOTE, prefix: "We recommend ", suffix: "." }, replies: [], resolved: false,
};
const at = (needle: string): number => { const i = DOC.indexOf(needle); assert.ok(i >= 0, needle); return i; };
// h1: the session's "reduced" became "cut" (a substitution, painted in Raw); h2: it removed " quickly" (a deletion: Reveal-only)
const h1: Hunk = { id: "h1", author: "api", ts: T0 - 90000, kind: "sub", curFrom: at("cut"), curTo: at("cut") + 3, baseFrom: at("cut"), baseTo: at("cut") + 7, oldText: "reduced", newText: "cut", anchor: null };
const h2: Hunk = { id: "h2", author: "api", ts: T0 - 80000, kind: "del", curFrom: at(" here."), curTo: at(" here."), baseFrom: at(" here."), baseTo: at(" here.") + 8, oldText: " quickly", newText: "", anchor: null };
const rec1 = { id: "h1", author: "api", authorId: SID, ts: T0 - 90000, kind: "sub", from: h1.curFrom, newText: "cut", oldText: "reduced" };
const rec2 = { id: "h2", author: "api", authorId: SID, ts: T0 - 80000, kind: "del", from: h2.curFrom, newText: "", oldText: " quickly" };
/** The same change and record, moved `by` characters — what the editor's remap hands the save after typing above them. */
const shifted = (h: Hunk, by: number): Hunk => ({ ...h, curFrom: h.curFrom + by, curTo: h.curTo + by, baseFrom: h.baseFrom + by, baseTo: h.baseTo + by });
const shiftedRec = (r: typeof rec1, by: number) => ({ ...r, from: r.from + by });
function status(over: Partial<Status> = {}): Status {
  return {
    verb: "status", root: ROOT, storePath: STORE_PATH, trackedBy: { kind: "file", entry: "docs/report.md" }, agentTooling: "present",
    fileMtimeNs: "1757145600000000001", storeMtimeNs: "1757145600000000002", configMtimeNs: "1757145600000000003",
    store: { v: 3, path: "docs/report.md", suggestions: [], comments: [passage] },
    hunks: [], log: [],
    unsent: { comments: [passage.id], replies: [], accepted: 0, rejected: 0, watermark: null },
    ...over,
  };
}
/** The status with changes pending: the hunks the host derived and the records the sidecar holds. */
function pending(over: Partial<Status> = {}, hunks: Hunk[] = [h1, h2], recs: Array<typeof rec1> = [rec1, rec2]): Status {
  return status({ hunks, store: { v: 3, path: "docs/report.md", suggestions: recs, comments: [passage] }, ...over });
}

// ── the viewer stand-in: the body row with Raw rows, the seam as closures, the poll's HEAD answers ──
// `buffer` is the editor's text while editing: the viewer's text() answers it then (plans/file-review.md Slice 5), and a
// test types by setting it; null means the editor holds the loaded text unchanged.
type World = {
  ctx: FileViewActionCtx; posted: any[]; main: El; body: El; code: El;
  hooks: { rendered: Array<() => void>; selection: Array<(s: Selection) => void>; close: Array<() => void> };
  disk: string; diskMtime: string; viewMtime: string; reloads: number; scrolls: number[]; modes: string[];
  mtimes: Record<string, string>;
  editing: boolean; buffer: string | null; tracked: TrackedEdit | null;
  setText(src: string): void; close(): void;
};
let cur: World | null = null;
(globalThis as any).fetch = async (url: string) => {
  if (url.includes("/sessions")) return { json: async () => [{ id: SID, name: "api", bg: "#123456", fg: "#ffffff" }] };
  const p = decodeURIComponent((/[?&]path=([^&]*)/.exec(url) || [])[1] || "");
  const mt = cur!.mtimes[p];
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
function world(): World {
  const main = new El("div"); main.className = "fileview-main";
  const body = new El("div"); body.className = "fileview-body";
  const wrap = new El("div"); wrap.className = "fileview-code";
  const pre = new El("pre"); pre.className = "fileview-pre fileview-wrap";
  const code = new El("code"); code.className = "hljs";
  pre.appendChild(code); wrap.appendChild(pre);
  body.appendChild(wrap);
  main.appendChild(body);
  let text = DOC;
  const w = {
    posted: [] as any[], main, body, code,
    hooks: { rendered: [] as Array<() => void>, selection: [] as Array<(s: Selection) => void>, close: [] as Array<() => void> },
    disk: text, diskMtime: "1757145600000000001", viewMtime: "1757145600000000001", reloads: 0, scrolls: [] as number[], modes: [] as string[], mtimes: {} as Record<string, string>,
    editing: false, buffer: null, tracked: null,
  } as World;
  rows(code, text);
  // the viewer's renderBody + fireRendered — in the real viewer the one hook in edit mode is enterEdit's
  w.setText = (s) => { text = s; rows(code, s); for (const cb of w.hooks.rendered) cb(); };
  w.ctx = {
    path: ABS, sid: SID, todoId: null,
    body: () => body as unknown as HTMLElement, mode: () => "raw",
    text: () => (w.editing && w.buffer !== null ? w.buffer : text),   // the viewer's seam: the buffer while editing (file-view.ts)
    mtimeNs: () => w.viewMtime, media: () => null, mediaElement: () => null, renderedImages: () => [], pdfPages: () => [],
    identity: () => ({ name: "api", color: null }),
    onRendered: (cb) => { w.hooks.rendered.push(cb); }, onSelection: (cb) => { w.hooks.selection.push(cb); },
    onSaved: () => { /* inert */ }, onClose: (cb) => { w.hooks.close.push(cb); },
    post: (m) => { w.posted.push(m); }, ensureEditingAllowed: async () => true, setEditBlocked: () => { /* inert */ }, editing: () => w.editing, setTrackedEdit: (t) => { w.tracked = t; },
    aside: (node) => { main.querySelector(".fileview-aside")?.remove(); if (node) { const n = node as unknown as El; n.classList.add("fileview-aside"); main.appendChild(n); } },
    setMode: (m) => { w.modes.push(m); }, scrollToOffset: (n) => { w.scrolls.push(n); },
    reload: () => { if (w.editing) return; w.reloads++; w.viewMtime = w.diskMtime; w.setText(w.disk); },
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
  w.mtimes[w.ctx.path] = s.fileMtimeNs;
  if (s.storePath && s.storeMtimeNs !== null) w.mtimes[s.storePath] = s.storeMtimeNs;
  if (s.root && s.configMtimeNs !== null) w.mtimes[s.root + "/.trackchanges/config.json"] = s.configMtimeNs;
}
function refuse(w: World, m: any, code: string, error: string): void {
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsFailed", reqId: m.reqId, verb: m.verb, code, error } }));
}
type Words = { DECIDE: string; TOUCH: string; UNREAD: string };
async function words(): Promise<Words> {
  const fc = await import("./file-comments");
  return { DECIDE: fc.DECIDE_IN_EDITOR, TOUCH: fc.DECIDE_IN_EDITOR_TOUCH, UNREAD: fc.CHANGES_UNREAD_UNDER_EDIT };
}
/** Mount without answering the probe: the file's bytes are up, the panel's first status is still out. */
async function mount(w: World): Promise<{ button: El; unit: El }> {
  const fc = await import("./file-comments");
  const unit = fc.fileCommentsAction.mount(w.ctx) as unknown as El;
  return { button: unit.childNodes[0] as El, unit };
}
/** Mount, answer the probe, open the panel, answer its refresh: the panel as a person first sees it. */
async function openPanel(w: World, s: Status): Promise<{ button: El; aside: El }> {
  const { button } = await mount(w);
  answer(w, s); await flush();
  button.click();
  answer(w, s); await flush(); await flush();
  const aside = w.main.querySelector(".fileview-aside")!;
  assert.ok(aside, "the panel is mounted beside the body");
  return { button, aside };
}
const card = (aside: El, key: string): El | null => aside.querySelector('.fc-card[data-id="' + key + '"]');
const act = (root: El, a: string, id?: string): El | null => root.querySelector('[data-act="' + a + '"]' + (id ? '[data-id="' + id + '"]' : ""));
const settle = (p: Promise<unknown>) => { const box: { ok?: unknown; err?: unknown } = {}; p.then((v) => { box.ok = v; }, (e) => { box.err = e; }); return box; };
const headRows = (aside: El): El[] => aside.querySelectorAll(".fc-sec-head .fc-err");
const groupTitles = (aside: El): string[] => aside.querySelectorAll(".fc-group").map((g) => g.textContent);
/** A render the person causes while the editor is up: a click on a card's head (fccard), which toggles it and re-renders. */
const rerender = (aside: El, key: string): void => { aside.querySelector('.fc-card[data-id="' + key + '"] .fc-card-head')!.click(); };
// the selection seam, as the behavior suite drives it: a passage selected in the body, the float pressed
function textNodeWith(root: El, needle: string): { node: Txt; at: number } | null {
  for (const c of root.childNodes) {
    if (c instanceof Txt) { const i = c.data.indexOf(needle); if (i >= 0) return { node: c, at: i }; }
    else { const r = textNodeWith(c, needle); if (r) return r; }
  }
  return null;
}
const RECT = { left: 100, top: 200, right: 300, bottom: 220, width: 200, height: 20 };
function startComment(w: World, quote: string): void {
  const hit = textNodeWith(w.body, quote);
  assert.ok(hit, "the passage is in the DOM");
  const sel: any = { rangeCount: 1, isCollapsed: false, anchorNode: hit.node, anchorOffset: hit.at, focusNode: hit.node, focusOffset: hit.at + quote.length,
    toString: () => quote, getRangeAt: () => ({ getBoundingClientRect: () => RECT }) };
  for (const cb of w.hooks.selection) cb(sel);
  const floats = doc.body.querySelectorAll(".fc-float"); const float = floats[floats.length - 1];
  assert.equal(float.hidden, false, "the float appears beside a selection in the body");
  selection = sel;
  float.click();
}

// ── Edit before the first status ───────────────────────────────────────────────────────────────────

test("Edit before the first status: the editor carries nothing; the status that then shows changes raises the head's row, Save refuses in its words and asks the kernel nothing; the edit's end retires the row and the next Edit carries the changes in", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { UNREAD } = await words();
  const { button } = await mount(w);
  assert.equal(countOf(w, "fileComments", "status"), 1, "the probe is out");
  // the bytes landed, the person clicks Edit; the sidecar (which holds two changes) has not been read yet
  w.editing = true;
  assert.equal(w.tracked!.begin(), null, "nothing to hand the editor: no status");
  assert.equal(w.tracked!.routesSave(), false, "no status: the viewer's own path, as before this slice");
  // the panel is opened meanwhile (a refresh ask joins the probe); the probe's answer lands: two pending changes
  button.click();
  const probe = w.posted.find((m) => m.type === "fileComments" && m.verb === "status");
  answer(w, pending(), probe); await flush(); await flush();
  const aside = w.main.querySelector(".fileview-aside")!;
  assert.equal(button.textContent, "Comments · 1 · 2 changes");
  const rowsNow = headRows(aside);
  assert.equal(rowsNow.length, 1, "one row in the head");
  assert.equal(rowsNow[0].childNodes[0].textContent, UNREAD);
  assert.equal(rowsNow[0].querySelector('[data-act="fcreload"]'), null, "nothing to reload: the disk is as the status read it");
  assert.match(UNREAD, /read only after you opened the editor/, "why the editor shows no marks");
  assert.match(UNREAD, /Save will refuse; copy anything you typed, then Cancel and Edit again\./, "what is left, as the moved-records row says it");
  // the refresh's answer too: the row is latched, not re-set
  answer(w, pending()); await flush();
  assert.equal(headRows(aside).length, 1, "one row per edit");
  // Save: the editor's list is empty (it carries no marks), and the sidecar holds two changes — refused, nothing sent
  assert.equal(w.tracked!.routesSave(), true, "a sidecar: Save comes to the panel");
  const out = settle(w.tracked!.save("the typed text", [], { accepted: [], rejected: [] }));
  await flush(); await flush();
  assert.equal(countOf(w, "fileComments", "save"), 0, "no save verb: the host would have written [] over the sidecar");
  assert.deepEqual(out.err, { code: "changes-unread", error: UNREAD }, "refused in the row's words, for the viewer's Save bar");
  // Cancel: the read view is back, the row and its latch are gone, and Edit again carries the changes
  w.editing = false; w.setText(w.disk);
  assert.equal(headRows(aside).length, 0, "the edit's end retires the row");
  w.editing = true;
  const begun = w.tracked!.begin();
  assert.deepEqual(begun && begun.records, [rec1, rec2], "the second Edit carries the records in");
  assert.equal(headRows(aside).length, 0, "…and raises nothing");
  const ok = settle(w.tracked!.save("the typed text", [rec1, rec2], { accepted: [], rejected: [] }));
  await flush();
  const save = lastOf(w, "fileComments", "save");
  assert.ok(save, "the save goes out");
  assert.deepEqual(save.args.suggestions, [rec1, rec2]);
  assert.equal(save.fence.storeMtimeNs, "1757145600000000002", "fenced on the sidecar the records came from");
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId: save.reqId, ...pending({ verb: "save", fileMtimeNs: "1757145600000000009", storeMtimeNs: "1757145600000000010" }), logged: true } }));
  await flush(); await flush();
  assert.deepEqual(ok.ok, { mtimeNs: "1757145600000000009", logged: true });
});

test("the refusal yields to the file's fence: changes recorded by a session under an edit that carried none moved the file too, so the moved-file row shows, the save goes to the host and its file fence refuses with Reload, as that row promised", async (t: TestContext) => {
  t.mock.timers.enable({ apis: ["setInterval"] });
  const w = world(); t.after(() => w.close());
  const { UNREAD } = await words();
  const { aside } = await openPanel(w, status());
  w.editing = true;
  assert.equal(w.tracked!.begin(), null, "nothing pending at Edit");
  // the session's track-edit lands under the edit: the file and the sidecar both move, and the poll sees it
  w.disk = DOC.replace("reduced", "cut"); w.diskMtime = "1757145600000000021"; w.mtimes[ABS] = w.diskMtime; w.mtimes[STORE_PATH] = "1757145600000000022";
  const asks = countOf(w, "fileComments", "status");
  t.mock.timers.tick(2500); await flush(); await flush(); await flush();
  assert.equal(countOf(w, "fileComments", "status"), asks + 1);
  answer(w, pending({ fileMtimeNs: w.diskMtime, storeMtimeNs: "1757145600000000022" }, [h1], [rec1])); await flush(); await flush();
  const rowsNow = headRows(aside);
  assert.equal(rowsNow.length, 1);
  assert.equal(rowsNow[0].childNodes[0].textContent, MOVED_UNDER_EDIT, "the file's row (the model's), not the unread one");
  assert.match(MOVED_UNDER_EDIT, /Save will refuse and offer Reload/, "the promise the refusal must keep");
  // Save: the host's file fence is the refusal here, with Reload — so the verb goes out, fenced on the file the editor loaded
  const out = settle(w.tracked!.save("the typed text", [], { accepted: [], rejected: [] }));
  await flush();
  const save = lastOf(w, "fileComments", "save");
  assert.ok(save, "the save reaches the host");
  assert.equal(save.fence.fileMtimeNs, "1757145600000000001", "the file as the editor loaded it: the host refuses file-moved");
  refuse(w, save, "file-moved", "the file changed on disk since you opened it — reload and retry"); await flush(); await flush();
  assert.deepEqual(out.err, { code: "file-moved", error: "the file changed on disk since you opened it — reload and retry" });
  assert.equal(countOf(w, "fileComments", "save"), 1, "a moved file is never retried");
  assert.equal(headRows(aside).map((r) => r.childNodes[0].textContent).includes(UNREAD), false);
});

// ── the cards group over the text the offsets index, not the buffer ────────────────────────────────

test("while the editor is up the cards group over the file as the editor loaded it, then over the last landed save's content — typing moves no group title; the composer's passage-changed tag reads the same text", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w, pending());
  assert.deepEqual(groupTitles(aside), ["## Findings", "More text here."], "read view: each change under its paragraph");
  // a passage composer opened before Edit: on the file's text, no tag
  startComment(w, QUOTE);
  assert.equal(aside.querySelector(".fc-quote")!.textContent, QUOTE);
  assert.equal(aside.querySelector(".fc-composer-ref .fc-tag"), null);
  // Edit, then thirty characters typed into the first line: every offset below moves in the buffer
  w.editing = true; w.tracked!.begin();
  const TYPED = " with thirty more chars typed!";
  assert.equal(TYPED.length, 30);
  w.buffer = DOC.replace("# Report", "# Report" + TYPED);
  rerender(aside, "chg:h1");
  assert.deepEqual(groupTitles(aside), ["## Findings", "More text here."], "the titles stand: the offsets index the loaded text, not the buffer");
  assert.equal(aside.querySelector(".fc-composer-ref .fc-tag"), null, "the file did not change: no passage-changed tag");
  // a save lands mid-edit with the records remapped by the editor: the reply's offsets index the saved content
  const content = w.buffer;
  const out = settle(w.tracked!.save(content, [shiftedRec(rec1, 30), shiftedRec(rec2, 30)], { accepted: [], rejected: [] }));
  await flush();
  const save = lastOf(w, "fileComments", "save");
  assert.ok(save);
  const reply = pending({ verb: "save", fileMtimeNs: "1757145600000000031", storeMtimeNs: "1757145600000000032" }, [shifted(h1, 30), shifted(h2, 30)], [shiftedRec(rec1, 30), shiftedRec(rec2, 30)]);
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId: save.reqId, ...reply, logged: true } }));
  await flush(); await flush();
  assert.deepEqual(out.ok, { mtimeNs: "1757145600000000031", logged: true });
  assert.deepEqual(groupTitles(aside), ["## Findings", "More text here."], "the saved content is what the new offsets index");
  assert.equal(aside.querySelector(".fc-composer-ref .fc-tag"), null, "the passage was re-found in the saved text");
  // the editor stays up and the person types above again: the titles still read the saved content
  w.buffer = "Another line first.\n" + content;
  rerender(aside, "chg:h1");
  assert.deepEqual(groupTitles(aside), ["## Findings", "More text here."]);
  assert.equal(aside.querySelector(".fc-composer-ref .fc-tag"), null);
  // the edit ends over the saved file: the read view's text is the one again
  w.editing = false; w.buffer = null; w.disk = content; w.diskMtime = "1757145600000000031"; w.viewMtime = w.diskMtime; w.setText(w.disk);
  assert.deepEqual(groupTitles(aside), ["## Findings", "More text here."]);
});

// ── the decide-in-editor words on a coarse pointer ─────────────────────────────────────────────────

test("on a coarse primary pointer the decide-in-editor words lead with the route a finger has and name the mouse gesture as one — in the caption, the tooltips and the refusal row; the rows are retired with the edit all the same", async (t: TestContext) => {
  win.matchMedia = (q: string) => ({ matches: q === "(pointer: coarse)" });
  t.after(() => { delete win.matchMedia; });
  const w = world(); t.after(() => w.close());
  const { DECIDE, TOUCH } = await words();
  const { aside } = await openPanel(w, pending());
  w.editing = true; w.tracked!.begin();
  assert.notEqual(TOUCH, DECIDE);
  assert.doesNotMatch(TOUCH, /^While you edit, decide in the editor: click/, "not the mouse instruction first");
  assert.match(TOUCH, /^While you edit, a tap on a change decides nothing/, "what a tap does, first");
  assert.match(TOUCH, /Save or Cancel first: Accept and Reject work again once the editor is closed\./, "the route a finger has");
  assert.match(TOUCH, /With a mouse, a click on a change accepts it and Alt-click \(Cmd-click on a Mac, Ctrl-click elsewhere\) rejects it/, "the mouse gesture, named as one: a tablet with a trackpad has both");
  assert.equal(aside.querySelector(".fc-foot .fc-decide-edit")!.textContent, TOUCH, "the caption");
  assert.equal(act(card(aside, "chg:h1")!, "fcaccept", "h1")!.title, TOUCH);
  assert.equal(act(card(aside, "chg:h1")!, "fcreject", "h1")!.title, TOUCH);
  assert.equal(act(aside, "fcacceptall")!.title, TOUCH);
  assert.equal(act(aside, "fcrejectall")!.title, TOUCH);
  // a tap on a card's Accept, and on the foot's Reject all: the row says the same words, the caption stands down for the foot's
  act(card(aside, "chg:h1")!, "fcaccept", "h1")!.click(); await flush();
  assert.equal(card(aside, "chg:h1")!.querySelector(".fc-err")!.childNodes[0].textContent, TOUCH);
  assert.equal(countOf(w, "fileComments", "accept"), 0);
  act(aside, "fcrejectall")!.click(); await flush();
  assert.equal(aside.querySelector(".fc-foot .fc-err")!.childNodes[0].textContent, TOUCH);
  assert.equal(aside.querySelector(".fc-foot .fc-decide-edit"), null, "the words once: the row, not the caption too");
  assert.equal(aside.querySelector(".fc-choice"), null);
  // the edit ends: both rows go with it, under either wording
  w.editing = false; w.setText(w.disk);
  assert.equal(card(aside, "chg:h1")!.querySelector(".fc-err"), null);
  assert.equal(aside.querySelector(".fc-foot .fc-err"), null);
  assert.equal(aside.querySelector(".fc-decide-edit"), null);
  assert.equal(act(card(aside, "chg:h1")!, "fcaccept", "h1")!.title, "Keep the text as it is and drop the change");
});

// ── the Reject-all confirm does not survive an Edit ────────────────────────────────────────────────

test("the Reject-all confirm opened before Edit is not back when the editor closes — after a Save that changed the count, or after Cancel; Reject all clicked again in the read view opens it as before", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w, pending());
  act(aside, "fcrejectall")!.click();
  assert.equal(aside.querySelector(".fc-choice .fc-note")!.textContent, "Put the old text back for all 2 changes?");
  assert.equal(act(aside, "fcrejectall")!.getAttribute("aria-expanded"), "true");
  // Edit: the confirm is a question the person walked away from
  w.editing = true; w.tracked!.begin();
  assert.equal(aside.querySelector(".fc-choice"), null, "hidden while the editor is up");
  // in the editor the person accepts h1 and saves; the reply shows one change left
  const out = settle(w.tracked!.save("the typed text", [rec2], { accepted: [{ id: "h1", oldText: "reduced", newText: "cut" }], rejected: [] }));
  await flush();
  const save = lastOf(w, "fileComments", "save");
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId: save.reqId, ...pending({ verb: "save", fileMtimeNs: "1757145600000000009", storeMtimeNs: "1757145600000000010" }, [h2], [rec2]), logged: true } }));
  await flush(); await flush();
  assert.deepEqual(out.ok, { mtimeNs: "1757145600000000009", logged: true });
  // the edit ends: no confirm re-counted for the one change left, no gesture asked for it
  w.editing = false; w.viewMtime = "1757145600000000009"; w.setText(w.disk);
  assert.equal(aside.querySelector(".fc-choice"), null, "not back after Save");
  assert.equal(act(aside, "fcrejectall")!.getAttribute("aria-expanded"), "false");
  assert.equal(countOf(w, "fileComments", "reject-all"), 0);
  // Cancel path: opened, Edit, the edit ends without a save
  act(aside, "fcrejectall")!.click();
  assert.equal(aside.querySelector(".fc-choice .fc-note")!.textContent, "Put the old text back for the change?", "a gesture opens it, as before");
  w.editing = true; w.tracked!.begin();
  assert.equal(aside.querySelector(".fc-choice"), null);
  w.editing = false; w.setText(w.disk);
  assert.equal(aside.querySelector(".fc-choice"), null, "not back after Cancel");
  assert.equal(act(aside, "fcrejectall")!.getAttribute("aria-expanded"), "false");
});

// ── source ──────────────────────────────────────────────────────────────────────────────────────────

test("source: the unread row is raised where every status lands and Save refuses on the same condition before asking; the cards and the composer read the indexed text, never the buffer; the decide words come from one device-aware function; begin retires the confirm", () => {
  const apply = SRC.split("applyStatus(s: Reply): boolean {")[1].split("\n  }\n")[0];
  assert.ok(apply.indexOf("this.noteChangesUnreadUnderEdit();") > apply.indexOf("this.noteChangesMovedUnderEdit();") && apply.indexOf("this.noteChangesUnreadUnderEdit();") < apply.indexOf("this.paintAll();"),
    "after the moved-records note, before the render the status gets");
  const note = SRC.split("private noteChangesUnreadUnderEdit(): void {")[1].split("\n  }\n")[0];
  assert.match(note, /if \(this\.editSeed \|\| !s \|\| !this\.ctx\.editing\(\) \|\| this\.changesUnreadUnderEdit\) return;/, "an editor carrying no records, and not said yet this edit");
  assert.match(note, /if \(!\(s\.hunks \|\| \[\]\)\.length \|\| laterNs\(s\.fileMtimeNs, this\.ctx\.mtimeNs\(\)\)\) return;/, "changes pending, and the file did not move (that row is the file's)");
  assert.match(note, /this\.errors\.set\("edit", \{ text: CHANGES_UNREAD_UNDER_EDIT, reload: false \}\);/, "the head's slot, no Reload");
  const save = SRC.split("async saveThroughComments(")[1].split("\n  }\n")[0];
  const guard = save.indexOf('throw { code: "changes-unread", error: CHANGES_UNREAD_UNDER_EDIT };');
  assert.ok(guard >= 0 && guard < save.indexOf('await this.request("save", args, fence)'), "refused before the verb is sent");
  assert.match(save, /if \(!seed && now && \(now\.hunks \|\| \[\]\)\.length && !laterNs\(now\.fileMtimeNs, this\.ctx\.mtimeNs\(\)\)\) throw/, "no records in the editor, changes on disk, the file where the editor loaded it");
  assert.match(save, /this\.editText = content;/, "a landed save's content is what its reply's offsets index");
  const paint = SRC.split("paintAll(): void {")[1].split("\n  }\n")[0];
  assert.match(paint, /if \(this\.changesUnreadUnderEdit\) \{ this\.changesUnreadUnderEdit = false; if \(this\.errors\.get\("edit"\)\?\.text === CHANGES_UNREAD_UNDER_EDIT\) this\.errors\.delete\("edit"\); \}/, "the edit's end retires the row and the latch");
  assert.match(paint, /this\.editText = null;/, "…and the indexed text");
  const view = SRC.split("changeView(): {")[1].split("\n  }\n")[0];
  assert.match(view, /changeGroups\(cards, this\.ctx\.mode\(\) === "media" \? null : this\.indexedText\(\)\)/, "the groups read the indexed text");
  assert.doesNotMatch(view, /this\.ctx\.text\(\)/);
  assert.equal(SRC.split("c.text !== this.indexedText()").length - 1, 2, "both passage-changed tags read it");
  assert.equal(SRC.split("c.text !== this.ctx.text()").length - 1, 0, "…and neither reads the buffer");
  assert.match(SRC, /private retargetComposer\(\): void \{\n\s*const c = this\.composer; const src = this\.indexedText\(\);/);
  assert.match(SRC, /function decideInEditor\(\): string \{ return isCoarsePointer\(\) \? DECIDE_IN_EDITOR_TOUCH : DECIDE_IN_EDITOR; \}/);
  assert.equal(SRC.split("? DECIDE_IN_EDITOR :").length - 1, 0, "no tooltip picks the mouse words directly");
  assert.equal(SRC.split("text: DECIDE_IN_EDITOR,").length - 1, 0, "no row does either");
  assert.match(SRC, /const DECIDE_TEXTS = new Set\(\[DECIDE_IN_EDITOR, DECIDE_IN_EDITOR_TOUCH\]\);/, "a row under either wording is the decide row");
  const begin = SRC.split("begin: () => {")[1].split("\n      },\n")[0];
  assert.match(begin, /this\.rejectAllConfirm = false;/, "Edit retires the confirm");
  assert.match(begin, /this\.editText = this\.ctx\.text\(\);/, "the text the offsets index, read before the editor holds the buffer");
  assert.ok(begin.indexOf("this.editText = this.ctx.text();") < begin.indexOf("if (!s || !hunks.length) { this.editSeed = null; this.render(); return null; }"), "…for an edit that carries nothing too");
});

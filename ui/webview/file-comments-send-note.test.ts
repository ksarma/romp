// The Send confirm's note box (the owner's ruling, 2026-09-09; plans/file-review.md, decision 40 and the arrivals follow-on
// under Slice 2), driven AS A PANEL over the third review round's stand-in (file-comments-review-fixes-3.test.ts, copied
// here): the confirm no longer shows the grey message preview or its toggle; in their place a multi-line box for the
// person's own words, empty by default, its placeholder naming the session, three rows growing to about eight. The text
// survives every re-render while the confirm is open (a status landing) and is cleared only by a successful send or by
// Cancel; a refused send keeps it. The note travels as `note` in the fileCommentsSend request, trimmed; over 4000
// characters the send is refused before any request, with a line naming the bound; a note with nothing else unsent still
// sends, so Send opens the confirm with nothing unsent and the confirm's own Send follows the box; the chord sends; the
// Log's send row and its detail show the note. Synthetic fixtures only: the notes-api world, placeholder ids.
import { test, type TestContext } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import type { FileViewActionCtx } from "./file-view";
import type { Status, StoreComment } from "./file-comments-model";
import { SEND_NOTE_MAX } from "./file-comments-model";

// ── a DOM stand-in: ancestry, attributes, events with capture and bubbling, a small selector engine ──
class Ev {
  target: El | Txt | null = null;
  currentTarget: El | null = null;
  defaultPrevented = false;
  stopped = false;
  key: string;
  ctrlKey: boolean; metaKey: boolean;
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
win.getSelection = () => null;
win.confirm = () => true;
(globalThis as any).window = win;
(globalThis as any).document = doc;
const store = new Map<string, string>();
(globalThis as any).localStorage = {
  getItem: (k: string) => (store.has(k) ? store.get(k)! : null),
  setItem: (k: string, v: string) => { store.set(k, String(v)); },
  removeItem: (k: string) => { store.delete(k); },
};

// ── fixtures: the notes-api world ──────────────────────────────────────────────────────────────────
const SID = "11111111-2222-3333-4444-555555555555";
const ABS = "/repo/notes-api/docs/report.md";
const ROOT = "/repo/notes-api";
const STORE_PATH = ROOT + "/.trackchanges/docs%2Freport.md.json";
const CONFIG_PATH = ROOT + "/.trackchanges/config.json";
const T0 = 1757145600000;
const F1 = "1757145600000000001", S2 = "1757145600000000002", C3 = "1757145600000000003";
const F55 = "1757145600000000055", S9 = "1757145600000000009", S12 = "1757145600000000012", S22 = "1757145600000000022";
const QUOTE = "shipping the cache in v1.2";
const DOC = "# Report\n\n## Findings\nThe api session cut p95 latency by 40% and the p99 by 10%.\n\nWe recommend " + QUOTE + ".\n\nMore text here.\n";
const first: StoreComment = {
  id: T0 + "-118", author: "you", ts: T0, body: "Which cache? Say which.",
  anchor: { quote: QUOTE, prefix: "We recommend ", suffix: "." }, replies: [], resolved: false,
};
const second: StoreComment = {
  id: (T0 - 60000) + "-40", author: "you", ts: T0 - 60000, body: "Cut this paragraph; it repeats the summary.",
  anchor: { quote: "The api session cut p95 latency by 40%", prefix: "## Findings\n", suffix: " and the" },
  replies: [{ author: "api", authorId: SID, ts: T0 - 30000, body: "Cut it." }], resolved: false,
};
const third: StoreComment = { id: T0 + 9000 + "-0", author: "you", ts: T0 + 9000, body: "Add a summary at the top.", replies: [], resolved: false };
const fourth: StoreComment = { id: T0 + 12000 + "-0", author: "you", ts: T0 + 12000, body: "And a date.", replies: [], resolved: false };
const fifth: StoreComment = { id: T0 + 15000 + "-3", author: "api", authorId: SID, ts: T0 + 15000, body: "Should the p99 line stay?", replies: [], resolved: false };
const NO_UNSENT = { comments: [], replies: [], accepted: 0, rejected: 0, watermark: null };
function status(over: Partial<Status> = {}): Status {
  return {
    verb: "status", root: ROOT, storePath: STORE_PATH, trackedBy: { kind: "file", entry: "docs/report.md" }, agentTooling: "present",
    fileMtimeNs: F1, storeMtimeNs: S2, configMtimeNs: C3,
    store: { v: 3, path: "docs/report.md", suggestions: [], comments: [first, second] },
    hunks: [],
    log: [{ ts: "2026-09-06T07:59:00Z", kind: "send", author: "you", sid: SID, comments: [{ id: second.id, desc: 'on "The api session cut p95 latency by 40%"', body: second.body }], accepted: 0, rejected: 0, queued: false }],
    unsent: { comments: [first.id], replies: [], accepted: 0, rejected: 0, watermark: T0 - 60000 },
    ...over,
  };
}
/** The status after a whole-file comment landed: the given comments, every `you` one past the send unsent. */
function withComments(storeMtimeNs: string, comments: StoreComment[], over: Partial<Status> = {}): Status {
  return status({ storeMtimeNs, store: { v: 3, path: "docs/report.md", suggestions: [], comments },
    unsent: { comments: comments.filter((c) => c.author === "you" && c.id !== second.id).map((c) => c.id), replies: [], accepted: 0, rejected: 0, watermark: T0 - 60000 }, ...over });
}

// ── the viewer stand-in: the body row with Raw rows, the seam as closures, the poll's HEAD answers ──
type World = {
  ctx: FileViewActionCtx; posted: any[]; main: El; body: El; code: El;
  hooks: { rendered: Array<() => void>; saved: Array<(i: { mtimeNs: string; logged: boolean }) => void>; close: Array<() => void> };
  disk: string; reloads: number;
  /** the view's mtime (ctx.mtimeNs): the file's at open, then the saved mtime on a save, then the disk's on a reload */
  viewMtime: string;
  mtimes: Record<string, string>; codes: Record<string, number>; heads: string[];
  setText(src: string): void; close(): void;
};
let cur: World | null = null;
(globalThis as any).fetch = async (url: string) => {
  if (url.includes("/sessions")) return { json: async () => [] };
  const p = decodeURIComponent((/[?&]path=([^&]*)/.exec(url) || [])[1] || "");
  const w = cur!;
  w.heads.push(p);
  if (w.codes[p]) return { status: w.codes[p], headers: { get: () => null } };   // a 413 or 415: the kernel refuses the HEAD
  const mt = w.mtimes[p];
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
function world(over: { path?: string; sid?: string | null; todoId?: string | null } = {}): World {
  const main = new El("div"); main.className = "fileview-main";
  const body = new El("div"); body.className = "fileview-body";
  const actions = new El("div"); actions.className = "fileview-actions"; actions.appendChild(new Txt("Rendered · Raw"));
  const wrap = new El("div"); wrap.className = "fileview-code";
  const pre = new El("pre"); pre.className = "fileview-pre fileview-wrap";
  const code = new El("code"); code.className = "hljs";
  pre.appendChild(code); wrap.appendChild(pre);
  body.appendChild(actions); body.appendChild(wrap);
  main.appendChild(body);
  let text = DOC;
  const w = {
    posted: [] as any[], main, body, code,
    hooks: { rendered: [] as Array<() => void>, saved: [] as Array<(i: { mtimeNs: string; logged: boolean }) => void>, close: [] as Array<() => void> },
    disk: text, reloads: 0, viewMtime: F1, mtimes: {} as Record<string, string>, codes: {} as Record<string, number>, heads: [] as string[],
  } as World;
  rows(code, text);
  w.setText = (s) => { text = s; rows(code, s); for (const cb of w.hooks.rendered) cb(); };
  w.ctx = {
    path: over.path ?? ABS, sid: over.sid === undefined ? SID : over.sid, todoId: over.todoId ?? null,
    body: () => body as unknown as HTMLElement, mode: () => "raw", text: () => text, mtimeNs: () => w.viewMtime, media: () => null, mediaElement: () => null, renderedImages: () => [], pdfPages: () => [],
    identity: () => ({ name: "api", color: null }),
    onRendered: (cb) => { w.hooks.rendered.push(cb); }, onSelection: () => { /* inert */ },
    onSaved: (cb) => { w.hooks.saved.push(cb); }, onClose: (cb) => { w.hooks.close.push(cb); },
    post: (m) => { w.posted.push(m); }, ensureEditingAllowed: async () => true, setEditBlocked: () => { /* inert */ }, editing: () => false, setTrackedEdit: () => { /* inert */ }, guardClose: () => { /* inert */ },
    aside: (node) => { main.querySelector(".fileview-aside")?.remove(); if (node) { const n = node as unknown as El; n.classList.add("fileview-aside"); main.appendChild(n); } },
    setMode: () => { /* inert */ }, scrollToOffset: () => { /* inert */ },
    // fetchFile: the bytes and the mtime now on disk (the HEAD table's, when the test set one)
    reload: () => { w.reloads++; if (w.mtimes[w.ctx.path] !== undefined) w.viewMtime = w.mtimes[w.ctx.path]; w.setText(w.disk); },
  };
  w.close = () => { for (const cb of w.hooks.close) cb(); if (cur === w) cur = null; };
  cur = w;
  return w;
}
const flush = () => new Promise<void>((r) => setImmediate(r));
/** A save acknowledged: the viewer sets its mtime to the saved one BEFORE it fires onSaved (file-view.ts doSave). */
function saved(w: World, mtimeNs: string): void { w.viewMtime = mtimeNs; for (const cb of w.hooks.saved) cb({ mtimeNs, logged: true }); }
const lastOf = (w: World, type: string, verb?: string) => [...w.posted].reverse().find((m) => m.type === type && (verb === undefined || m.verb === verb));
const countOf = (w: World, type: string, verb?: string) => w.posted.filter((m) => m.type === type && (verb === undefined || m.verb === verb)).length;
/** Answer the ask `m` with `s`. `disk` = the HEADs follow this reply's mtimes (the default); false for a reply that
 *  read the disk BEFORE what is now on it, which must not move the stand-in's disk backwards. */
function answer(w: World, s: Status, m = lastOf(w, "fileComments", "status"), disk = true): void {
  assert.ok(m, "an ask is outstanding");
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId: m.reqId, ...s } }));
  if (!disk) return;
  w.mtimes[w.ctx.path] = s.fileMtimeNs;
  if (s.storePath && s.storeMtimeNs !== null) w.mtimes[s.storePath] = s.storeMtimeNs;
  if (s.root && s.configMtimeNs !== null) w.mtimes[s.root + "/.trackchanges/config.json"] = s.configMtimeNs;
}
function refuse(w: World, m: any, code: string, error: string): void {
  assert.ok(m, "an ask is outstanding");
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsFailed", reqId: m.reqId, verb: m.verb, code, error } }));
}
function sent(w: World, m = lastOf(w, "fileCommentsSend")): void {
  assert.ok(m, "a send is outstanding");
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsSent", reqId: m.reqId, queued: false } }));
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
const input = (aside: El): El => aside.querySelector(".fc-input")!;
const press = (el: El, key: string) => dispatch(el, new Ev("keydown", { key }));
/** The save chord (Ctrl+Enter; Cmd+Enter is the same key policy): a plain Enter is a newline in the box now. */
const chord = (el: El) => dispatch(el, new Ev("keydown", { key: "Enter", ctrlKey: true }));
const cards = (aside: El): number => aside.querySelectorAll(".fc-card").length;
const sendLabel = (aside: El): string => aside.querySelector('[data-act="fcsend"]')!.textContent;
const errText = (row: El): string => row.childNodes[0].textContent;
/** Comment on this file, a note, Enter: the `comment` ask that goes out. */
async function enterComment(w: World, aside: El, note: string): Promise<any> {
  aside.querySelector('[data-act="fcfile"]')!.click();
  input(aside).value = note;
  chord(input(aside)); await flush();
  const post = lastOf(w, "fileComments", "comment");
  assert.ok(post, "Enter posted the comment");
  return post;
}
/** The file's own markup as the viewer places it: a `.fileview-md` box in the body holding what marked emitted
 *  and DOMPurify kept — here a paragraph of spans carrying the panel's own data-act names. */
function authorMarkup(w: World, acts: Array<[string, Record<string, string>]>): El[] {
  const md = new El("div"); md.className = "fileview-md";
  const p = new El("p"); md.appendChild(p);
  const out = acts.map(([act, data]) => {
    const s = new El("span"); s.dataset.act = act;
    for (const k of Object.keys(data)) s.dataset[k] = data[k];
    s.appendChild(new Txt("read more")); p.appendChild(s);
    return s;
  });
  w.body.appendChild(md);
  return out;
}
const CORRUPT = "the comments for ~/notes-api/docs/report.md could not be read: ~/notes-api/.trackchanges/docs%2Freport.md.json is not valid JSON in the expected shape; nothing was changed";
const MOVED = "the comments for ~/notes-api/docs/report.md changed under this request; nothing was written";
const GATE = "cannot write the comments for ~/notes-api/docs/report.md: dashboard file editing is off on this machine — the viewer's Edit button asks to turn it on";


// ── the note box ──────────────────────────────────────────────────────────────────────────────────
const SRC = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "file-comments.ts"), "utf8");
const noteBox = (aside: El): El => aside.querySelector(".fc-confirm .fc-send-note")!;
const typeNote = (aside: El, text: string): void => { const b = noteBox(aside); b.value = text; dispatch(b, new Ev("input")); };
const openConfirm = (aside: El): void => { aside.querySelector('[data-act="fcsend"]')!.click(); };
function refuseSend(w: World, error: string, m = lastOf(w, "fileCommentsSend")): void {
  assert.ok(m, "a send is outstanding");
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsSendFailed", reqId: m.reqId, error } }));
}

test("the confirm carries a note box in place of the preview: three rows, empty, its placeholder naming the session; no preview, no toggle", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  openConfirm(aside);
  const box = noteBox(aside);
  assert.ok(box, "the box stands in the confirm");
  assert.equal(box.tagName, "TEXTAREA");
  assert.equal((box as unknown as { rows: number }).rows, 3);
  assert.equal(box.value, "");
  assert.equal(box.placeholder, "Anything to add for api?");
  assert.ok(box.classList.contains("fc-input"), "the composer's dress");
  assert.equal(aside.querySelector('[data-act="fcpreview"]'), null, "no preview toggle");
  assert.equal(aside.querySelector(".fc-msg"), null, "no preview");
  assert.ok(aside.querySelector('[data-act="fcsendgo"]') && !aside.querySelector('[data-act="fcsendgo"]')!.disabled, "Send is on: a comment is unsent");
});

test("the words survive a status landing and a re-render while the confirm is open, and the chord sends them as `note`, trimmed; a successful send clears them", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  openConfirm(aside);
  typeNote(aside, "  Keep the tone of the first draft.\nIt reads well.  ");
  // a status lands (the viewer's save re-asks; a poll's landing is the same render)
  saved(w, "1757145600000000009"); await flush();
  answer(w, status({ fileMtimeNs: "1757145600000000009" })); await flush();
  const box = noteBox(aside);
  assert.ok(box, "the confirm is still open after the status");
  assert.equal(box.value, "  Keep the tone of the first draft.\nIt reads well.  ", "the words as typed");
  chord(box); await flush();
  const msg = lastOf(w, "fileCommentsSend");
  assert.ok(msg, "the chord sent");
  assert.equal(msg.note, "Keep the tone of the first draft.\nIt reads well.", "trimmed; the inner line break kept");
  assert.deepEqual(msg.comments.map((c: { id: string }) => c.id), [first.id], "with the unsent comment");
  sent(w); await flush(); answer(w, status({ unsent: NO_UNSENT })); await flush();
  assert.match(aside.querySelector(".fc-sent")!.textContent, /^Sent to api at /);
  assert.equal(aside.querySelector(".fc-confirm"), null, "the confirm closed");
  openConfirm(aside);
  assert.equal(noteBox(aside).value, "", "sent: the words went with the message");
});

test("a refused send keeps the words; Cancel clears them; a send without a note carries none", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  openConfirm(aside);
  typeNote(aside, "Say which cache in the abstract too.");
  aside.querySelector('[data-act="fcsendgo"]')!.click(); await flush();
  assert.equal(lastOf(w, "fileCommentsSend").note, "Say which cache in the abstract too.");
  refuseSend(w, "Couldn't deliver the message — the session didn't take it."); await flush();
  assert.equal(errText(aside.querySelector(".fc-send .fc-err")!), "Couldn't deliver the message — the session didn't take it.");
  assert.equal(noteBox(aside).value, "Say which cache in the abstract too.", "a refusal keeps the words");
  aside.querySelector('[data-act="fcsendcancel"]')!.click();
  assert.equal(aside.querySelector(".fc-confirm"), null);
  openConfirm(aside);
  assert.equal(noteBox(aside).value, "", "Cancel is a close on purpose: the words go");
  aside.querySelector('[data-act="fcsendgo"]')!.click(); await flush();
  const msg = lastOf(w, "fileCommentsSend");
  assert.ok(msg.reqId > 0);
  assert.equal("note" in msg, false, "no note, no field");
});

test("a note over the bound is refused before any request, with a line naming the bound; at the bound it goes", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  openConfirm(aside);
  typeNote(aside, "x".repeat(SEND_NOTE_MAX + 1));
  aside.querySelector('[data-act="fcsendgo"]')!.click(); await flush();
  assert.equal(lastOf(w, "fileCommentsSend"), undefined, "nothing posted");
  assert.equal(countOf(w, "fileComments", "set-tracked") + countOf(w, "fileComments", "accept-all"), 0, "no step of the send ran");
  assert.equal(errText(aside.querySelector(".fc-send .fc-err")!), "Nothing sent: the note is 4001 characters, and a send carries at most 4000. Shorten it.");
  assert.equal(noteBox(aside).value.length, SEND_NOTE_MAX + 1, "the words stay for the person to shorten");
  typeNote(aside, "y".repeat(SEND_NOTE_MAX));
  aside.querySelector('[data-act="fcsendgo"]')!.click(); await flush();
  assert.equal(lastOf(w, "fileCommentsSend").note.length, SEND_NOTE_MAX, "at the bound it goes");
});

test("nothing unsent: Send still opens the confirm, whose own Send is off until a note is typed; the note goes alone, with no comments and no decisions", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w, status({ unsent: NO_UNSENT }));
  const send = aside.querySelector('[data-act="fcsend"]')!;
  assert.equal(send.disabled, false, "Send is on with nothing unsent (before: off)");
  assert.equal(send.textContent, "Send to session", "no count");
  assert.equal(aside.querySelector(".fc-send .fc-note")!.textContent, "Nothing unsent: every comment, reply, and decision has gone.", "the caption still says so");
  openConfirm(aside);
  assert.ok(noteBox(aside), "the confirm is up, with the box");
  assert.equal(aside.querySelector(".fc-confirm .fc-note")!.textContent, "Nothing is unsent; a note goes to api:");
  const go = aside.querySelector('[data-act="fcsendgo"]')!;
  assert.equal(go.disabled, true, "nothing to send yet");
  go.click(); await flush();
  assert.equal(lastOf(w, "fileCommentsSend"), undefined, "a click on the disabled button in the stand-in: doSend sends nothing either");
  assert.ok(aside.querySelector(".fc-confirm .fc-send-note"), "the confirm stays up");
  typeNote(aside, "   ");
  assert.equal(aside.querySelector('[data-act="fcsendgo"]')!.disabled, true, "blank words are none");
  typeNote(aside, "Only this: the numbers in section 2 need a source.");
  assert.equal(aside.querySelector('[data-act="fcsendgo"]')!.disabled, false, "the box's input turned Send on, in place");
  aside.querySelector('[data-act="fcsendgo"]')!.click(); await flush();
  const msg = lastOf(w, "fileCommentsSend");
  assert.ok(msg, "the note went");
  assert.equal(msg.note, "Only this: the numbers in section 2 need a source.");
  assert.deepEqual(msg.comments, []); assert.equal(msg.accepted, 0); assert.equal(msg.rejected, 0);
  assert.equal(aside.querySelector(".fc-confirm"), null, "the confirm is down while the send is out (Sending…), as before");
  sent(w); await flush(); answer(w, status({ unsent: NO_UNSENT })); await flush();
  assert.match(aside.querySelector(".fc-sent")!.textContent, /^Sent to api at /, "the sent note as before");
});

test("the Log: a send's row names the note with the comments, or alone, and the row's detail shows the words first", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const log = [
    { ts: "2026-09-09T07:10:00Z", kind: "send", author: "you", sid: SID, comments: [{ id: second.id, desc: 'on "The api session cut p95 latency by 40%"', body: second.body }], accepted: 0, rejected: 0, queued: false, note: "Keep the tone of the first draft." },
    { ts: "2026-09-09T07:20:00Z", kind: "send", author: "you", sid: SID, comments: [], accepted: 0, rejected: 0, queued: false, note: "Only this: the numbers need a source." },
    { ts: "2026-09-09T07:30:00Z", kind: "send", author: "you", sid: SID, comments: [], accepted: 2, rejected: 0, queued: false },
  ];
  const { aside } = await openPanel(w, status({ log }));
  aside.querySelector('[data-act="fclog"]')!.click();
  const rows = aside.querySelectorAll(".fc-log-row").map((r) => r.childNodes[1].textContent);
  assert.deepEqual(rows, ["Sent 0 comments to api with 2 accepts and 0 rejects", "▸ Sent a note to api", "▸ Sent 1 comment and a note to api"]);
  const noteRow = aside.querySelectorAll(".fc-log-row")[1];
  noteRow.click();
  const detail = aside.querySelector(".fc-log-detail")!;
  assert.ok(detail, "the row opens");
  assert.equal(detail.querySelector(".fc-log-note")!.textContent, "Only this: the numbers need a source.");
  assert.equal(detail.querySelector(".fc-list"), null, "no comments, no list");
  const row2 = aside.querySelectorAll(".fc-log-row")[2];   // the rows were rebuilt by the click above: re-read
  row2.click();
  const kids = aside.querySelector(".fc-log")!.childNodes;
  const both = kids[kids.indexOf(aside.querySelectorAll(".fc-log-row")[2]) + 1] as El;   // a row's detail follows it
  assert.equal((both.childNodes[0] as El).className, "fc-body fc-log-note", "the words first");
  assert.equal(both.querySelectorAll(".fc-list li").length, 1, "then the comment");
});

test("at source: no preview, no toggle, no message built in the panel; the box is one persistent node whose focus and scroll the render restores; the chord is claimed for it at the window", () => {
  assert.doesNotMatch(SRC, /previewOpen|fcpreview|"The message"/);
  assert.doesNotMatch(SRC, /buildSendMessage\(/, "the panel builds no message: the kernel does, and the model's builder is its twin for the parity tests");
  assert.match(SRC, /noteBox = el\("textarea", "fc-input fc-send-note"\) as HTMLTextAreaElement;/);
  assert.match(SRC, /const noting = document\.activeElement === this\.noteBox;/);
  assert.match(SRC, /if \(noting && document\.activeElement !== this\.noteBox\) this\.noteBox\.focus\(\{ preventScroll: true \}\);/);
  assert.match(SRC, /else if \(ev\.target === p\.noteBox\) \{ ev\.stopImmediatePropagation\(\); p\.noteKey\(ev\); \}/);
  assert.match(SRC, /const long = noteTooLong\(note\);\n\s*if \(long\) \{ this\.errors\.set\("send", \{ text: long, reload: false \}\); this\.render\(\); return; \}/, "refused before any request");
  assert.match(SRC, /if \(note\) msg\.note = note;/);
  assert.match(SRC, /fcsendcancel: \(\) => \{ this\.sendConfirm = false; this\.sendNote = ""; this\.noteBox\.value = ""; this\.render\(\); \},/);
});

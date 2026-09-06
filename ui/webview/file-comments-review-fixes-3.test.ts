// The Comments panel's third round of review fixes (2026-09-06), driven AS A PANEL over a DOM stand-in: the real
// module mounted over a body row, its delegate root receiving clicks and keys, the kernel's replies arriving as
// window messages. Covered: markup the FILE's author wrote never reaches the panel's handlers (the sanitizer keeps
// data-* attributes, so a rendered markdown span can carry `data-act="fcsendgo"`); the send preview and the folder
// label name the path the kernel acts on, not the spelling the viewer was opened with; a status asked after a write
// but answered from a read before it is not applied over the write's reply; Send's turn-on-tracking step as
// behavior; the consent decline and the editing-off re-consent; the poll's stop row's wording; the Track changes
// toggle re-asking when no status stands behind it; Reload's loader. Synthetic fixtures only: the notes-api world,
// placeholder ids. The stand-in is the behavior suite's (raw rows, the seam as closures, the poll's HEAD answers);
// the author's markup is placed in the body the way the viewer places rendered markdown, and the guard under test
// is provenance, not view mode.
import { test, type TestContext } from "node:test";
import * as assert from "node:assert/strict";
import type { FileViewActionCtx } from "./file-view";
import type { Status, StoreComment } from "./file-comments-model";
import { buildSendMessage, sendParts } from "./file-comments-model";

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
    disk: text, reloads: 0, mtimes: {} as Record<string, string>, codes: {} as Record<string, number>, heads: [] as string[],
  } as World;
  rows(code, text);
  w.setText = (s) => { text = s; rows(code, s); for (const cb of w.hooks.rendered) cb(); };
  w.ctx = {
    path: over.path ?? ABS, sid: over.sid === undefined ? SID : over.sid, todoId: over.todoId ?? null,
    body: () => body as unknown as HTMLElement, mode: () => "raw", text: () => text, mtimeNs: () => F1, media: () => null, mediaElement: () => null, renderedImages: () => [], pdfPages: () => [],
    identity: () => ({ name: "api", color: null }),
    onRendered: (cb) => { w.hooks.rendered.push(cb); }, onSelection: () => { /* inert */ },
    onSaved: (cb) => { w.hooks.saved.push(cb); }, onClose: (cb) => { w.hooks.close.push(cb); },
    post: (m) => { w.posted.push(m); }, ensureEditingAllowed: async () => true, setEditBlocked: () => { /* inert */ }, editing: () => false, setTrackedEdit: () => { /* inert */ },
    aside: (node) => { main.querySelector(".fileview-aside")?.remove(); if (node) { const n = node as unknown as El; n.classList.add("fileview-aside"); main.appendChild(n); } },
    setMode: () => { /* inert */ }, scrollToOffset: () => { /* inert */ },
    reload: () => { w.reloads++; w.setText(w.disk); },
  };
  w.close = () => { for (const cb of w.hooks.close) cb(); if (cur === w) cur = null; };
  cur = w;
  return w;
}
const flush = () => new Promise<void>((r) => setImmediate(r));
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
const cards = (aside: El): number => aside.querySelectorAll(".fc-card").length;
const sendLabel = (aside: El): string => aside.querySelector('[data-act="fcsend"]')!.textContent;
const errText = (row: El): string => row.childNodes[0].textContent;
/** Comment on this file, a note, Enter: the `comment` ask that goes out. */
async function enterComment(w: World, aside: El, note: string): Promise<any> {
  aside.querySelector('[data-act="fcfile"]')!.click();
  input(aside).value = note;
  press(input(aside), "Enter"); await flush();
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

// ── the file's own markup never reaches the panel ─────────────────────────────────────────────────

test("data-act markup the file's author wrote sends nothing, stops no tracking, resolves nothing, reloads nothing, opens nothing — while the panel's own controls and its painted highlights still act", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { button } = await mount(w);
  answer(w, status({ trackedBy: { kind: "folder", entry: "docs/" } })); await flush();   // one unsent comment, the folder tracked
  const [send, stop, resolve, reload, open, file] = authorMarkup(w, [
    ["fcsendgo", {}], ["fctrackstop", {}], ["fcresolve", { id: first.id, on: "1" }], ["fcreload", { slot: "head" }], ["fcopen", { id: first.id }], ["fcfile", {}],
  ]);
  const before = w.posted.length;
  for (const s of [send, stop, resolve, reload, file]) s.click();
  await flush();
  assert.equal(w.posted.length, before, "nothing went out: no send, no set-tracked, no resolve, no status re-ask");
  assert.equal(w.reloads, 0, "the bytes were not re-fetched");
  assert.equal(w.main.querySelector(".fileview-aside"), null, "the panel did not open");
  open.click();
  assert.equal(w.main.querySelector(".fileview-aside"), null, "a data-act=fcopen in the prose opens nothing");
  assert.equal(press(open, "Enter"), true, "Enter on it is left to the browser (not prevented)…");
  assert.equal(w.main.querySelector(".fileview-aside"), null, "…and opens nothing");
  open.classList.add("fc-hl"); open.tabIndex = 0;
  open.click(); press(open, "Enter");
  assert.equal(w.main.querySelector(".fileview-aside"), null, "the highlight's own class name proves nothing");
  // the panel's own: a highlight it painted opens the panel with its card
  const mark = w.code.querySelector('.fc-hl[data-id="' + first.id + '"]')!;
  assert.ok(mark, "the passage comment is painted");
  mark.click();
  const aside = w.main.querySelector(".fileview-aside")!;
  assert.ok(aside, "the panel's own highlight opens it");
  assert.equal(aside.querySelector('.fc-card[data-id="' + first.id + '"]')!.classList.contains("open"), true, "…with its card open");
  answer(w, status({ trackedBy: { kind: "folder", entry: "docs/" } })); await flush();
  // …and the confirm's own Send sends, while the prose's span still does not
  aside.querySelector('[data-act="fcsend"]')!.click();
  send.click(); await flush();
  assert.equal(countOf(w, "fileCommentsSend"), 0, "the prose's fcsendgo: nothing, even with the confirm open");
  aside.querySelector('[data-act="fcsendgo"]')!.click(); await flush();
  assert.equal(countOf(w, "fileCommentsSend"), 1, "the panel's Send: one message");
  sent(w); await flush(); answer(w, status({ trackedBy: { kind: "folder", entry: "docs/" }, unsent: NO_UNSENT })); await flush();
  // the folder-off confirm's own Stop goes through; the prose's fctrackstop still does not
  aside.querySelector('[data-act="fctrack"]')!.click();
  assert.ok(aside.querySelector('.fc-choice [data-act="fctrackstop"]'), "the confirm row asks first");
  stop.click(); await flush();
  assert.equal(lastOf(w, "fileComments", "set-tracked"), undefined);
  aside.querySelector('.fc-choice [data-act="fctrackstop"]')!.click(); await flush();
  assert.deepEqual(lastOf(w, "fileComments", "set-tracked").args, { on: false, scope: "folder" }, "the panel's Stop turns the folder off");
});

test("a checkbox the file's markup carries flips no send option; the confirm's own does", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w, status({ trackedBy: null }));
  const md = new El("div"); md.className = "fileview-md";
  const rogue = new El("input"); rogue.type = "checkbox"; rogue.dataset.opt = "track"; rogue.checked = false;
  md.appendChild(rogue); w.body.appendChild(md);
  dispatch(rogue, new Ev("change"));
  aside.querySelector('[data-act="fcsend"]')!.click();
  const cb = aside.querySelector('input[data-opt="track"]')!;
  assert.equal(cb.checked, true, "the prose's unchecked box changed nothing: tracking is still to be turned on");
  cb.checked = false; dispatch(cb, new Ev("change"));
  aside.querySelector('[data-act="fcsendcancel"]')!.click(); aside.querySelector('[data-act="fcsend"]')!.click();
  assert.equal(aside.querySelector('input[data-opt="track"]')!.checked, false, "the confirm's own box is remembered");
});

// ── the preview and the folder label name the path the kernel acts on ─────────────────────────────

test("the send preview is the sent text whatever spelling the viewer was opened with: a relative token, a ~ path, a symlinked spelling all preview the store's file", async (t: TestContext) => {
  const want = buildSendMessage({ absPath: ABS, comments: sendParts(status()).comments, accepted: 0, rejected: 0, tracked: true });
  for (const spelling of ["docs/report.md", "~/notes-api/docs/report.md", "/vault/proj/report.md", ABS]) {
    const w = world({ path: spelling }); t.after(() => w.close());
    const { aside } = await openPanel(w, status({ trackedBy: null }));
    assert.equal(lastOf(w, "fileComments", "status").path, spelling, "the asks carry the viewer's spelling: the kernel resolves it");
    aside.querySelector('[data-act="fcsend"]')!.click();
    aside.querySelector('[data-act="fcpreview"]')!.click();
    const text = aside.querySelector(".fc-msg")!.textContent;
    assert.equal(text, want, "opened as " + spelling + ": the preview names the kernel's path, byte for byte");
    assert.match(text, /^\[obsidian-diff\] I left 1 comment on \/repo\/notes-api\/docs\/report\.md\.\n/);
    assert.match(text, /--file \/repo\/notes-api\/docs\/report\.md --thread/);
    // the Track choice names the same file's folder
    aside.querySelector('[data-act="fcsendcancel"]')!.click();
    aside.querySelector('[data-act="fctrack"]')!.click();
    assert.equal(aside.querySelector('.fc-choice [data-act="fctrackfolder"]')!.textContent, "Its folder /repo/notes-api/docs/", "opened as " + spelling);
    w.close();
  }
});

test("no sidecar yet: an absolute spelling is the kernel's path; a relative one names nothing, and the folder label says less rather than wrong", async (t: TestContext) => {
  const bare = status({ trackedBy: null, store: null, storePath: null, storeMtimeNs: null, unsent: NO_UNSENT });
  const w = world({ path: "/repo/notes-api/docs/new.md" }); t.after(() => w.close());
  const { aside } = await openPanel(w, bare);
  aside.querySelector('[data-act="fctrack"]')!.click();
  assert.equal(aside.querySelector('.fc-choice [data-act="fctrackfolder"]')!.textContent, "Its folder /repo/notes-api/docs/");
  w.close();
  const w2 = world({ path: "notes.md" }); t.after(() => w2.close());
  const p2 = await openPanel(w2, bare);
  p2.aside.querySelector('[data-act="fctrack"]')!.click();
  const f = p2.aside.querySelector('.fc-choice [data-act="fctrackfolder"]')!;
  assert.equal(f.textContent, "Its folder", "never 'Its folder /' for a bare file name");
  assert.equal(f.title, "Everything under the folder, files not written yet included");
  p2.aside.querySelector('.fc-choice [data-act="fctrackfolder"]')!.click(); await flush();
  assert.deepEqual(lastOf(w2, "fileComments", "set-tracked").args, { on: true, scope: "folder" }, "the host computes the entry from the real path");
});

// ── a status asked after a write, answered from a read before it ───────────────────────────────────

test("a status the poll asked AFTER a comment, answered from a sidecar read BEFORE the comment's write, does not take the new card away; one that read a later disk lands; a status asked after the write's reply settles a deletion", async (t: TestContext) => {
  t.mock.timers.enable({ apis: ["setInterval"] });
  const w = world(); t.after(() => w.close());
  const { aside, button } = await openPanel(w);
  assert.equal(cards(aside), 2); assert.equal(sendLabel(aside), "Send to session (1)");
  // Enter on a whole-file comment (B); while the host runs it, the session's track-edit moves the file and the
  // tick sees the move: it re-fetches the bytes and asks status (A) — issued AFTER B, so its reqId is the larger
  const B = await enterComment(w, aside, "Add a summary at the top.");
  w.mtimes[ABS] = F55;
  t.mock.timers.tick(2500); await flush(); await flush(); await flush();
  const A = lastOf(w, "fileComments", "status");
  assert.ok(A.reqId > B.reqId, "the poll's ask came after the comment's");
  assert.equal(w.reloads, 1, "the moved file was re-fetched");
  answer(w, withComments(S9, [first, second, third], { fileMtimeNs: F55 }), B); await flush();
  assert.equal(cards(aside), 3, "B's reply shows the new card");
  assert.equal(sendLabel(aside), "Send to session (2)"); assert.equal(button.textContent, "Comments · 3");
  // A's host run read the sidecar before B's write landed, and answers only now
  answer(w, status({ fileMtimeNs: F55 }), A, false); await flush();
  assert.equal(cards(aside), 3, "the pre-write reading is not applied over the write's reply: the card stays");
  assert.equal(sendLabel(aside), "Send to session (2)", "…Send's count holds");
  assert.equal(button.textContent, "Comments · 3");
  const asks = countOf(w, "fileComments", "status");
  t.mock.timers.tick(2500); await flush(); await flush(); await flush();
  assert.equal(countOf(w, "fileComments", "status"), asks, "the baseline is B's: nothing to re-read, the card never flaps");
  // an ask that overlapped the write but whose run started late — after the write and after the session's own
  // track-comment — read a LATER disk: new information, applied whatever its place in line
  const C = await enterComment(w, aside, "And a date.");
  w.hooks.saved[0]({ mtimeNs: F55, logged: true });   // a direct edit acknowledged meanwhile re-asks status (E > C)
  const E = lastOf(w, "fileComments", "status");
  assert.ok(E.reqId > C.reqId);
  answer(w, withComments(S12, [first, second, third, fourth], { fileMtimeNs: F55 }), C); await flush();
  assert.equal(cards(aside), 4);
  answer(w, withComments(S22, [first, second, third, fourth, fifth], { fileMtimeNs: F55 }), E); await flush();
  assert.equal(cards(aside), 5, "a later reading of the disk lands");
  // a status asked once no write is out is not suspect: a sidecar gone (the vendored CLIs delete a clean one) is applied
  w.hooks.saved[0]({ mtimeNs: F55, logged: true });
  answer(w, status({ fileMtimeNs: F55, store: null, storePath: STORE_PATH, storeMtimeNs: null, unsent: NO_UNSENT })); await flush();
  assert.equal(cards(aside), 0, "the poll settles a deletion");
});

// ── Send's turn-on-tracking step, as behavior ──────────────────────────────────────────────────────

test("Send with 'turn on tracking' checked: set-tracked goes first and the send waits for it, carrying the post-toggle verdict; a refused toggle sends nothing and says so", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w, status({ trackedBy: null }));
  aside.querySelector('[data-act="fcsend"]')!.click();
  const cb = aside.querySelector('input[data-opt="track"]')!;
  assert.ok(cb, "the file is untracked: the checkbox is offered"); assert.equal(cb.checked, true, "…checked by default");
  aside.querySelector('[data-act="fcpreview"]')!.click();
  assert.match(aside.querySelector(".fc-msg")!.textContent, /to revise the text: node ~\/\.claude\/hooks\/track-edit\.mjs --file/, "the preview shows the tracked bullet the send will carry");
  aside.querySelector('[data-act="fcsendgo"]')!.click(); await flush();
  const tog = lastOf(w, "fileComments", "set-tracked");
  assert.ok(tog, "the toggle goes first");
  assert.deepEqual(tog.args, { on: true, scope: "file" });
  assert.equal(lastOf(w, "fileCommentsSend"), undefined, "no send until the toggle is answered");
  assert.equal(sendLabel(aside), "Sending…");
  refuse(w, tog, "host-error", "the comments helper crashed"); await flush();
  assert.equal(lastOf(w, "fileCommentsSend"), undefined, "a refused toggle aborts before the send");
  assert.equal(errText(aside.querySelector(".fc-send .fc-err")!), "the comments helper crashed", "…and the refusal sits under Send");
  assert.equal(sendLabel(aside), "Send to session (1)");
  // again: the toggle lands, and the send carries what it answered
  aside.querySelector('[data-act="fcsendgo"]')!.click(); await flush();
  const tog2 = lastOf(w, "fileComments", "set-tracked");
  assert.ok(tog2.reqId > tog.reqId);
  answer(w, status({ trackedBy: { kind: "file", entry: "docs/report.md" } }), tog2); await flush();
  const msg = lastOf(w, "fileCommentsSend");
  assert.ok(msg, "the send follows the toggle's answer");
  assert.ok(msg.reqId > tog2.reqId);
  assert.equal(msg.tracked, true, "tracked: the post-toggle verdict, not the pre-toggle status");
  assert.equal(msg.path, ABS); assert.equal(msg.sid, SID);
  assert.deepEqual(msg.comments.map((c: { id: string }) => c.id), [first.id]);
  sent(w); await flush(); answer(w, status({ trackedBy: { kind: "file", entry: "docs/report.md" }, unsent: NO_UNSENT })); await flush();
  assert.match(aside.querySelector(".fc-sent")!.textContent, /^Sent to api at /);
  assert.equal(aside.querySelector('[data-act="fctrack"]')!.textContent, "Track changes · on");
});

test("Send with 'turn on tracking' unchecked: no toggle, the message goes with tracked:false and the edit-normally bullet", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w, status({ trackedBy: null }));
  aside.querySelector('[data-act="fcsend"]')!.click();
  const cb = aside.querySelector('input[data-opt="track"]')!;
  cb.checked = false; dispatch(cb, new Ev("change"));
  aside.querySelector('[data-act="fcpreview"]')!.click();
  assert.match(aside.querySelector(".fc-msg")!.textContent, /to revise the text: edit the file normally/);
  aside.querySelector('[data-act="fcsendgo"]')!.click(); await flush();
  assert.equal(lastOf(w, "fileComments", "set-tracked"), undefined, "nothing toggled");
  const msg = lastOf(w, "fileCommentsSend");
  assert.ok(msg); assert.equal(msg.tracked, false);
});

// ── the consent: a No is acknowledged; an editing-off refusal re-offers it once ────────────────────

test("a No on the consent popup: nothing is written, the composer says so under itself, and the note stays", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  let asked = 0;
  w.ctx.ensureEditingAllowed = async () => { asked++; return false; };
  aside.querySelector('[data-act="fcfile"]')!.click();
  input(aside).value = "Add a summary at the top.";
  press(input(aside), "Enter"); await flush();
  assert.equal(asked, 1, "the consent was asked");
  assert.equal(lastOf(w, "fileComments", "comment"), undefined, "no comment went out");
  const err = aside.querySelector(".fc-composer .fc-err")!;
  assert.ok(err, "the No is acknowledged with a row (never a Save that silently does nothing)");
  assert.equal(errText(err), "Nothing written: comments need file editing on.");
  assert.equal(err.querySelector('[data-act="fcreload"]'), null);
  assert.equal(input(aside).value, "Add a summary at the top.", "the note stays");
  assert.equal(aside.querySelector(".fc-composer")!.hidden, false);
  assert.equal(aside.querySelector('[data-act="fcsave"]')!.disabled, false, "Save is back for another try");
});

test("an editing-off refusal from the kernel re-offers the consent with the kernel's words and retries once; a No there shows the refusal and retries nothing", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  const asked: Array<string | undefined> = [];
  const answers = [true, true, true, false];   // first consent, re-consent (yes); first consent, re-consent (no)
  w.ctx.ensureEditingAllowed = async (refusal) => { asked.push(refusal); return answers.shift()!; };
  const post = await enterComment(w, aside, "Add a summary at the top.");
  assert.deepEqual(asked, [undefined], "the first consent, with no refusal text");
  refuse(w, post, "editing-off", GATE); await flush();
  assert.deepEqual(asked, [undefined, GATE], "the kernel's refusal is re-offered as the consent, in its words");
  const retry = lastOf(w, "fileComments", "comment");
  assert.ok(retry.reqId > post.reqId, "…and the comment is retried once");
  assert.deepEqual(retry.args, post.args);
  answer(w, withComments(S9, [first, second, third]), retry); await flush();
  assert.equal(aside.querySelector(".fc-composer")!.hidden, true, "saved: the composer closes");
  assert.equal(cards(aside), 3);
  // the same, declined at the re-offer
  const post2 = await enterComment(w, aside, "And a date.");
  refuse(w, post2, "editing-off", GATE); await flush();
  assert.deepEqual(asked.slice(2), [undefined, GATE]);
  assert.equal(lastOf(w, "fileComments", "comment"), post2, "no retry after a No");
  const err = aside.querySelector(".fc-composer .fc-err")!;
  assert.equal(errText(err), GATE, "the kernel's refusal, verbatim");
  assert.equal(err.querySelector('[data-act="fcreload"]'), null, "no Reload: nothing moved");
  assert.equal(input(aside).value, "And a date.", "the note stays");
});

// ── the poll's stop row ────────────────────────────────────────────────────────────────────────────

test("a 413 or 415 on a poll target stops the checking and says so in those words — never 'watching', under a toggle that still reads on", async (t: TestContext) => {
  t.mock.timers.enable({ apis: ["setInterval"] });
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  w.codes[STORE_PATH] = 413;
  t.mock.timers.tick(2500); await flush(); await flush(); await flush();
  const row = aside.querySelector('.fc-sec-head .fc-err[data-slot="poll"]')!;
  assert.ok(row, "the row sits in the head");
  assert.equal(errText(row), "Stopped checking " + STORE_PATH + " for changes: the kernel answered 413 (too large to serve). Reload to try again.");
  assert.ok(row.querySelector('[data-act="fcreload"]'), "Reload is offered");
  assert.doesNotMatch(aside.textContent, /watch/i, "'watched' is a word the vocabulary avoids for a tracked file (CONTEXT.md)");
  assert.equal(aside.querySelector('[data-act="fctrack"]')!.textContent, "Track changes · on", "the toggle above it is unchanged");
  assert.equal(aside.querySelector('[data-act="fctrack"]')!.dataset.on, "1");
  assert.equal(lastOf(w, "fileComments", "set-tracked"), undefined, "no tracking verb went out");
  w.codes[CONFIG_PATH] = 415;
  t.mock.timers.tick(2500); await flush(); await flush(); await flush();
  assert.equal(errText(aside.querySelector('.fc-sec-head .fc-err[data-slot="poll"]')!), "Stopped checking " + CONFIG_PATH + " for changes: the kernel answered 415 (not a type it serves). Reload to try again.");
});

// ── Track changes with no status behind it ─────────────────────────────────────────────────────────

test("Track changes clicked while the status is refused re-asks under the toggle: the loader while out, the refusal as its row, and on an answer the scope row", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { button } = await mount(w);
  refuse(w, lastOf(w, "fileComments", "status"), "corrupt", CORRUPT); await flush();
  button.click();
  refuse(w, lastOf(w, "fileComments", "status"), "corrupt", CORRUPT); await flush();
  const aside = w.main.querySelector(".fileview-aside")!;
  const toggle = () => aside.querySelector('[data-act="fctrack"]')!;
  assert.equal(toggle().disabled, false, "the toggle is a live control");
  const asks = countOf(w, "fileComments", "status");
  toggle().click(); await flush();
  assert.equal(countOf(w, "fileComments", "status"), asks + 1, "the click re-asks status: a result follows the acknowledgement");
  assert.ok(aside.querySelector(".fc-sec-head .fc-load"), "the toggle's slot wears the loader while the ask is out");
  toggle().click(); await flush();
  assert.equal(countOf(w, "fileComments", "status"), asks + 1, "a second click during the round trip asks nothing more");
  refuse(w, lastOf(w, "fileComments", "status"), "corrupt", CORRUPT); await flush();
  assert.equal(aside.querySelector(".fc-sec-head .fc-load"), null, "refused: no loader");
  const err = aside.querySelector('.fc-err[data-slot="track"]')!;
  assert.ok(err, "the refusal sits under the toggle");
  assert.equal(errText(err), "Nothing written: " + CORRUPT);
  assert.equal(err.querySelector('[data-act="fcreload"]'), null, "no Reload: re-reading cannot mend the sidecar");
  assert.equal(aside.querySelector(".fc-choice"), null, "no scope row on nothing");
  // the person mends the sidecar and clicks again: the answer lands, and the click's intent — turning tracking on — follows
  toggle().click(); await flush();
  answer(w, status({ trackedBy: null })); await flush();
  assert.equal(aside.querySelector('.fc-err[data-slot="track"]'), null, "the row is cleared by the answer");
  assert.ok(aside.querySelector('.fc-choice [data-act="fctrackfile"]'), "untracked: the scope row opens");
  assert.equal(cards(aside), 2, "the cards render from the status that came back");
});

test("Track changes clicked while the status is refused, on a file that turns out tracked: the toggle now reads so, and nothing is turned off", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { button } = await mount(w);
  refuse(w, lastOf(w, "fileComments", "status"), "host-error", "the comments helper crashed"); await flush();
  button.click();
  refuse(w, lastOf(w, "fileComments", "status"), "host-error", "the comments helper crashed"); await flush();
  const aside = w.main.querySelector(".fileview-aside")!;
  assert.equal(aside.querySelector('[data-act="fctrack"]')!.textContent, "Track changes", "off is what showed");
  aside.querySelector('[data-act="fctrack"]')!.click(); await flush();
  answer(w, status()); await flush();
  assert.equal(aside.querySelector('[data-act="fctrack"]')!.textContent, "Track changes · on", "the true state");
  assert.equal(lastOf(w, "fileComments", "set-tracked"), undefined, "a click meant as 'on' never turns a tracked file off");
  assert.equal(aside.querySelector(".fc-choice"), null);
});

// ── Reload wears the loader where its row was ──────────────────────────────────────────────────────

test("Reload from a row re-reads with the romp loader standing where the row was, until the answer; the cards stay up meanwhile", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  // a set-tracked refused store-moved twice leaves the track row with Reload
  aside.querySelector('[data-act="fctrack"]')!.click(); await flush();
  const off = lastOf(w, "fileComments", "set-tracked");
  assert.deepEqual(off.args, { on: false, scope: "file" });
  refuse(w, off, "store-moved", MOVED); await flush();
  answer(w, status()); await flush();
  const off2 = lastOf(w, "fileComments", "set-tracked");
  assert.ok(off2.reqId > off.reqId, "retried once on the fresh fence");
  refuse(w, off2, "store-moved", MOVED); await flush();
  const reload = aside.querySelector('.fc-err[data-slot="track"] [data-act="fcreload"]')!;
  assert.ok(reload, "the second refusal offers Reload");
  assert.equal(aside.querySelector(".fc-load"), null, "settled: no loader before the click");
  const asks = countOf(w, "fileComments", "status"), reloads = w.reloads;
  reload.click();
  assert.equal(countOf(w, "fileComments", "status"), asks + 1, "Reload asks status");
  assert.equal(w.reloads, reloads + 1, "…and re-fetches the bytes");
  assert.equal(aside.querySelector('.fc-err[data-slot="track"]'), null, "the row is gone");
  assert.ok(aside.querySelector(".fc-sec-head .fc-load"), "…and the loader stands where it was, for as long as the ask is out");
  assert.equal(cards(aside), 2, "the cards stay up meanwhile");
  answer(w, status()); await flush();
  assert.equal(aside.querySelector(".fc-load"), null, "the answer takes the loader down");
  assert.equal(aside.querySelector(".fc-err"), null);
  // a refused refresh over a showing status leaves the head's row with Reload: the same wait, in the head's slot
  w.hooks.saved[0]({ mtimeNs: F55, logged: true });
  refuse(w, lastOf(w, "fileComments", "status"), "host-error", "the comments helper crashed"); await flush();
  const r2 = aside.querySelector('.fc-err[data-slot="head"] [data-act="fcreload"]')!;
  assert.ok(r2);
  r2.click();
  assert.ok(aside.querySelector(".fc-sec-head .fc-load"), "the head's slot wears the loader");
  assert.equal(aside.querySelector(".fc-sec-cards .fc-load"), null, "one loader, not two: the cards are showing");
  answer(w, status({ fileMtimeNs: F55 })); await flush();
  assert.equal(aside.querySelector(".fc-load"), null);
});

test("the poll's own re-read wears no loader: nobody is waiting on it, and a swirl per change the session makes would only pull the eye", async (t: TestContext) => {
  t.mock.timers.enable({ apis: ["setInterval"] });
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  w.mtimes[STORE_PATH] = S22;
  t.mock.timers.tick(2500); await flush(); await flush(); await flush();
  assert.ok(lastOf(w, "fileComments", "status").reqId > 0);
  assert.equal(aside.querySelector(".fc-load"), null, "a re-read on the poll's own account shows no loader");
  assert.equal(cards(aside), 2);
  answer(w, status({ storeMtimeNs: S22 })); await flush();
});

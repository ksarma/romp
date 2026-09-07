// The Comments panel's moved-under-edit row is said ONCE PER EDIT (plans/file-review.md, Slice 5; the 2026-09-06
// review of the slice, round 4). The head's row for a file that changed on disk while the editor is up
// (MOVED_UNDER_EDIT) is raised from every status that reads a later file than the editor loaded: the poll's moved
// branch, every verb reply, the save's re-read. The editor's mtime is frozen while it is up, so every later status
// keeps reading later than it, and before this round each re-raised the row the person had dismissed with its ✕ —
// a comment on the file, a resolve, a poll that saw only the sidecar move — on nothing new about the file. The row
// now latches once per edit, as its sibling rows do (CHANGES_MOVED_UNDER_EDIT, CHANGES_UNREAD_UNDER_EDIT): dismissed,
// it stays dismissed; Cancel still re-reads the bytes (the latch, not the row, keys that); a new edit starts a new
// latch. Driven as a panel over the behavior suite's DOM stand-in, with the viewer's edit mode and the seam as
// closures. Synthetic fixtures only: the notes-api world, placeholder ids.
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
const GONE = "the comments for ~/notes-api/docs/report.md disappeared from disk since you opened the file — reload and retry";

// ── the viewer stand-in: the body row with Raw rows, the seam as closures, the poll's HEAD answers ──
type World = {
  ctx: FileViewActionCtx; posted: any[]; main: El; body: El; code: El;
  hooks: { rendered: Array<() => void>; close: Array<() => void> };
  disk: string; diskMtime: string; viewMtime: string; reloads: number; scrolls: number[]; modes: string[];
  mtimes: Record<string, string>;
  editing: boolean; tracked: TrackedEdit | null;    // the viewer's edit mode, and the panel's half of editing over pending changes
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
    hooks: { rendered: [] as Array<() => void>, close: [] as Array<() => void> },
    disk: text, diskMtime: "1757145600000000001", viewMtime: "1757145600000000001", reloads: 0, scrolls: [] as number[], modes: [] as string[], mtimes: {} as Record<string, string>,
    editing: false, tracked: null,
  } as World;
  rows(code, text);
  // the viewer's renderBody + fireRendered — in the real viewer the one hook in edit mode is enterEdit's; a test that paints in edit
  // mode is exercising the panel's own render, which the hook reaches through paintAll's editing branch
  w.setText = (s) => { text = s; rows(code, s); for (const cb of w.hooks.rendered) cb(); };
  w.ctx = {
    path: ABS, sid: SID, todoId: null,
    body: () => body as unknown as HTMLElement, mode: () => "raw", text: () => text, mtimeNs: () => w.viewMtime, media: () => null, mediaElement: () => null, renderedImages: () => [], pdfPages: () => [],
    identity: () => ({ name: "api", color: null }),
    onRendered: (cb) => { w.hooks.rendered.push(cb); }, onSelection: () => { /* inert */ },
    onSaved: () => { /* inert */ }, onClose: (cb) => { w.hooks.close.push(cb); },
    post: (m) => { w.posted.push(m); }, ensureEditingAllowed: async () => true, setEditBlocked: () => { /* inert */ }, editing: () => w.editing, setTrackedEdit: (t) => { w.tracked = t; },
    aside: (node) => { main.querySelector(".fileview-aside")?.remove(); if (node) { const n = node as unknown as El; n.classList.add("fileview-aside"); main.appendChild(n); } },
    setMode: (m) => { w.modes.push(m); }, scrollToOffset: (n) => { w.scrolls.push(n); },
    // fetchFile: the bytes and mtime now on disk, repainted, the seam's onRendered fired; a no-op in edit mode, as the viewer's is
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
  // the poll's baseline follows the reply: the HEADs answer these mtimes until a test moves one
  w.mtimes[w.ctx.path] = s.fileMtimeNs;
  if (s.storePath && s.storeMtimeNs !== null) w.mtimes[s.storePath] = s.storeMtimeNs;
  if (s.root && s.configMtimeNs !== null) w.mtimes[s.root + "/.trackchanges/config.json"] = s.configMtimeNs;
}
function refuse(w: World, m: any, code: string, error: string): void {
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsFailed", reqId: m.reqId, verb: m.verb, code, error } }));
}
/** Mount, answer the probe, open the panel, answer its refresh: the panel as a person first sees it. */
async function openPanel(w: World, s: Status): Promise<{ button: El; aside: El; DECIDE: string }> {
  const fc = await import("./file-comments");
  const unit = fc.fileCommentsAction.mount(w.ctx) as unknown as El;
  const button = unit.childNodes[0] as El;
  answer(w, s); await flush();
  button.click();
  answer(w, s); await flush(); await flush();
  const aside = w.main.querySelector(".fileview-aside")!;
  assert.ok(aside, "the panel is mounted beside the body");
  return { button, aside, DECIDE: fc.DECIDE_IN_EDITOR };
}
const card = (aside: El, key: string): El | null => aside.querySelector('.fc-card[data-id="' + key + '"]');
const act = (root: El, a: string, id?: string): El | null => root.querySelector('[data-act="' + a + '"]' + (id ? '[data-id="' + id + '"]' : ""));
const headRows = (aside: El): El[] => aside.querySelectorAll(".fc-sec-head .fc-err");
const NS = (n: number) => "17571456000000000" + String(n).padStart(2, "0");
const input = (aside: El): El => aside.querySelector(".fc-input")!;
const REPORT = "docs/report.md";

// ── the moved-under-edit row is said once per edit ─────────────────────────────────────────────────

test("the moved-under-edit row, dismissed with its ✕, does not return with a comment's reply, a resolve's reply, a poll that saw only the sidecar move, or a second rewrite; Cancel still re-reads the bytes; a new edit starts a new latch", async (t: TestContext) => {
  t.mock.timers.enable({ apis: ["setInterval"] });
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w, status());
  w.editing = true;
  assert.equal(w.tracked!.begin(), null, "no changes pending: the editor mounts as for any file, and the cards render in edit mode");
  // the session rewrote the file under the edit; the poll sees the move and the head says so
  w.disk = DOC.replace("More text here.", "More text here, rewritten by the session."); w.diskMtime = NS(33); w.mtimes[ABS] = w.diskMtime;
  let asks = countOf(w, "fileComments", "status");
  t.mock.timers.tick(2500); await flush(); await flush(); await flush();
  assert.equal(countOf(w, "fileComments", "status"), asks + 1);
  answer(w, status({ fileMtimeNs: NS(33) })); await flush();
  assert.equal(headRows(aside).length, 1, "the head says the bytes moved");
  assert.equal(headRows(aside)[0].childNodes[0].textContent, MOVED_UNDER_EDIT);
  assert.equal(w.reloads, 0, "never over the editor's buffer");
  // the person dismisses the row
  headRows(aside)[0].querySelector('[data-act="fcerrx"]')!.click();
  assert.equal(headRows(aside).length, 0, "dismissed");
  // Comment on this file — offered while editing (it is not a decision) — and its reply reads the file the poll already showed
  act(aside, "fcfile")!.click();
  assert.equal(aside.querySelector(".fc-composer-ref")!.textContent, "On this file");
  input(aside).value = "Add a summary at the top.";
  act(aside, "fcsave")!.click(); await flush();
  const cm = lastOf(w, "fileComments", "comment");
  assert.ok(cm, "the comment went out");
  const note: StoreComment = { id: T0 + "-200", author: "you", ts: T0 + 1000, body: "Add a summary at the top.", anchor: null, replies: [], resolved: false };
  answer(w, status({ verb: "comment", fileMtimeNs: NS(33), storeMtimeNs: NS(5), store: { v: 3, path: REPORT, suggestions: [], comments: [passage, note] } }), cm);
  await flush(); await flush();
  assert.equal(aside.querySelector(".fc-composer")!.hidden, true, "the comment landed: the reply closed the composer");
  assert.equal(headRows(aside).length, 0, "nothing new about the file: the dismissed row stays dismissed");
  // Resolve on the open card — offered while editing (it moves no change) — and its reply reads the same file
  card(aside, passage.id)!.click();
  act(card(aside, passage.id)!, "fcresolve")!.click(); await flush(); await flush();
  const rs = lastOf(w, "fileComments", "resolve");
  assert.ok(rs, "the resolve went out");
  const resolved = { ...passage, resolved: true };
  answer(w, status({ verb: "resolve", fileMtimeNs: NS(33), storeMtimeNs: NS(6), store: { v: 3, path: REPORT, suggestions: [], comments: [resolved, note] } }), rs);
  await flush(); await flush();
  assert.equal(headRows(aside).length, 0, "…nor with the resolve's reply");
  // a session's reply lands in the sidecar: the poll sees only the sidecar move, and the status reads the same file
  w.mtimes[STORE_PATH] = NS(7);
  asks = countOf(w, "fileComments", "status");
  t.mock.timers.tick(2500); await flush(); await flush(); await flush();
  assert.equal(countOf(w, "fileComments", "status"), asks + 1, "the sidecar is still watched while the editor is up");
  const replied = { ...resolved, replies: [{ author: "api", ts: T0 + 2000, body: "The write-through one." }] };
  answer(w, status({ fileMtimeNs: NS(33), storeMtimeNs: NS(7), store: { v: 3, path: REPORT, suggestions: [], comments: [replied, note] } })); await flush();
  assert.equal(headRows(aside).length, 0, "…nor with a poll that saw only the sidecar move");
  // the session rewrites the file a second time: the words would be the same (Save refuses, Cancel shows the file as it is now)
  w.disk = w.disk.replace("rewritten by the session", "rewritten twice by the session"); w.diskMtime = NS(34); w.mtimes[ABS] = w.diskMtime;
  t.mock.timers.tick(2500); await flush(); await flush(); await flush();
  answer(w, status({ fileMtimeNs: NS(34), storeMtimeNs: NS(7), store: { v: 3, path: REPORT, suggestions: [], comments: [replied, note] } })); await flush();
  assert.equal(headRows(aside).length, 0, "said once per edit, as the sibling rows are");
  assert.equal(w.reloads, 0, "…and still nothing re-read over the buffer");
  // Cancel: the viewer repaints the bytes it loaded (the pre-rewrite text) and fires onRendered; the latch, not the row, keys the re-read
  w.editing = false; w.setText(DOC);
  assert.equal(w.reloads, 1, "the first paint after the edit re-reads the file, dismissed row or not");
  assert.ok(w.code.textContent.includes("rewritten twice by the session"), "the read view shows the file as it is now");
  assert.equal(w.viewMtime, NS(34));
  assert.equal(headRows(aside).length, 0);
  // a new Edit; the session rewrites the file again: the row again
  w.editing = true;
  assert.equal(w.tracked!.begin(), null);
  w.disk = w.disk.replace("rewritten twice", "rewritten three times"); w.diskMtime = NS(35); w.mtimes[ABS] = w.diskMtime;
  t.mock.timers.tick(2500); await flush(); await flush(); await flush();
  answer(w, status({ fileMtimeNs: NS(35), storeMtimeNs: NS(7), store: { v: 3, path: REPORT, suggestions: [], comments: [replied, note] } })); await flush();
  assert.equal(headRows(aside).length, 1, "a new edit, a new latch");
  assert.equal(headRows(aside)[0].childNodes[0].textContent, MOVED_UNDER_EDIT);
  assert.equal(w.reloads, 1, "the row, not a re-read: the editor's buffer is untouched");
});

test("the row said first by a verb's reply latches the same way: a later poll on the sidecar does not bring it back", async (t: TestContext) => {
  t.mock.timers.enable({ apis: ["setInterval"] });
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w, status());
  w.editing = true;
  assert.equal(w.tracked!.begin(), null);
  // Resolve, answered after a session wrote the file: the reply's clocks say so, and the head says it
  card(aside, passage.id)!.click();
  act(card(aside, passage.id)!, "fcresolve")!.click(); await flush(); await flush();
  const rs = lastOf(w, "fileComments", "resolve");
  assert.ok(rs);
  w.disk = DOC.replace("More text here.", "More text here, rewritten by the session."); w.diskMtime = NS(33);
  const resolved = { ...passage, resolved: true };
  answer(w, status({ verb: "resolve", fileMtimeNs: NS(33), storeMtimeNs: NS(5), store: { v: 3, path: REPORT, suggestions: [], comments: [resolved] } }), rs);
  await flush(); await flush();
  assert.equal(headRows(aside)[0].childNodes[0].textContent, MOVED_UNDER_EDIT, "the head says the bytes moved, from the reply's clocks");
  headRows(aside)[0].querySelector('[data-act="fcerrx"]')!.click();
  assert.equal(headRows(aside).length, 0, "dismissed");
  // a session replies to the comment: the sidecar moves, the file does not
  w.mtimes[STORE_PATH] = NS(6);
  const asks = countOf(w, "fileComments", "status");
  t.mock.timers.tick(2500); await flush(); await flush(); await flush();
  assert.equal(countOf(w, "fileComments", "status"), asks + 1);
  answer(w, status({ fileMtimeNs: NS(33), storeMtimeNs: NS(6), store: { v: 3, path: REPORT, suggestions: [], comments: [{ ...resolved, replies: [{ author: "api", ts: T0 + 2000, body: "Done." }] }] } })); await flush();
  assert.equal(headRows(aside).length, 0, "the dismissed row stays dismissed");
  assert.equal(w.reloads, 0);
  w.editing = false; w.setText(DOC);
  assert.equal(w.reloads, 1, "Cancel still re-reads the bytes");
  assert.ok(w.code.textContent.includes("rewritten by the session"));
});

test("source: the moved-file row latches once per edit before the clocks are read, as its sibling rows do; one writer of the row, raised from the poll's moved branch, every verb reply and the save's re-read; the edit's end spends the latch", () => {
  const fn = SRC.split("private noteMovedUnderEdit(): void {")[1].split("\n  }\n")[0];
  assert.match(fn, /^\s*if \(this\.movedUnderEdit\) return;[^\n]*\n\s*const s = this\.status;\n\s*if \(!this\.ctx\.editing\(\) \|\| !s \|\| !laterNs\(s\.fileMtimeNs, this\.ctx\.mtimeNs\(\)\)\) return;/,
    "the latch is the first thing checked, before the clocks: a status read while the row is already latched re-sets nothing");
  assert.equal((SRC.match(/this\.errors\.set\("edit", \{ text: MOVED_UNDER_EDIT/g) || []).length, 1, "one writer of the row");
  assert.equal((SRC.match(/this\.noteMovedUnderEdit\(\);/g) || []).length, 3, "the poll's moved branch, every verb reply, the save's re-read");
  // the siblings check theirs the same way, so the three rows in the head's `edit` slot agree on once per edit
  assert.match(SRC, /if \(!seed \|\| !s \|\| !this\.ctx\.editing\(\) \|\| this\.changesMovedUnderEdit\) return;/);
  assert.match(SRC, /if \(this\.editSeed \|\| !s \|\| !this\.ctx\.editing\(\) \|\| this\.changesUnreadUnderEdit\) return;/);
  assert.match(SRC, /if \(this\.movedUnderEdit\) \{ this\.movedUnderEdit = false; this\.errors\.delete\("edit"\); this\.ctx\.reload\(\); \}/, "the edit's end spends the latch and re-reads");
});

// The Comments panel's filter (the filter follow-on to plans/file-review.md, 2026-09-07), after its review: the cases the
// first build got wrong, driven AS A PANEL over the filter suite's DOM stand-in (its harness, copied: a Raw or Rendered
// body built to the viewer's shape, the seam as closures, the stub localStorage every panel suite installs — here with
// the viewer's edit mode and its selection hook wired, which the filter suite leaves inert).
//   • a reply on a comment a change answered, under All or Comments: the comment stands on its own card (renderCards; since
//     the about follow-on, 2026-09-10, no comment is drawn inside a change card), so resolved it is under the Resolved fold,
//     whatever the changes fold does to the change's card. The slot's line names that fold and Cancel focuses its row,
//     whether the comment was resolved before the reply began (from the open fold under All, then Comments picked and
//     the fold closed; from the open fold under Comments, then closed) or meanwhile; never the "… N more changes" row,
//     which hides change cards alone and which Comments does not render;
//   • the "answered by a change" tag names the change that answered the comment (a legacy suggestionId, read as the
//     session's answer): a pending one, or a detached one whose text the file no longer holds (cardModel sets `refs` for
//     both); the change card counts the open comments about it; its kind cue says a detached change is nobody's to decide;
//   • the filter is offered while the editor is up (Slice 5), where the list half works and the editor keeps its own
//     marks: the option titles say so there, and say the read view's marks rule otherwise;
//   • a comment saved while Changes is chosen: its card and mark are hidden by that choice, so the list says so where the
//     card would be, with a ✕ — the kept choice stands; the line is over once the card shows or the comment is gone, and
//     does not come back on a later Changes; a comment about a change (the change card's Comment on this change) is its
//     own card, hidden under Changes like every comment's, so the line shows for it too;
//   • the Changes option carries the action-row label's own detached clause ("Changes 0 · 1 detached"), so a file holding
//     detached changes alone does not read as one with nothing to show, and its title names them;
//   • the Track scope choice, the Stop confirm and the track slot's refusal stand directly under the toggles' row, above the
//     filter's row: the answer to a click sits under the button that asked.
// Synthetic fixtures only: the notes-api world, placeholder ids.
import { test, type TestContext } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import type { FileViewActionCtx, TrackedEdit } from "./file-view";
import { type Status, type Hunk, type StoreComment, cardCounts, DETACHED_GROUP_TITLE } from "./file-comments-model";

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

// ── this suite's own fixtures and helpers ──────────────────────────────────────────────────────────
// a detached op as store-io keeps it: the engine's op record with `detached: true`, at its LAST place in a text that has
// moved on (300 is past the end of DOC), and a comment it answered (a legacy suggestionId: cardModel gives it a ref with
// source "answered" and state "detached", as a pending one's ref reads "pending")
const D1 = { id: "d1", author: "api", authorId: SID, ts: T0 - 40000, kind: "sub", from: 300, oldText: "cold starts were slow",
  newText: "cold starts stay slow", anchor: { quote: "cold starts stay slow", prefix: "and ", suffix: "." }, detached: true };
const D2 = { ...D1, id: "d2", ts: T0 - 39000, kind: "del", oldText: "the old footnote", newText: "" };
const onD1: StoreComment = { id: T0 + 6000 + "-30", author: "you", ts: T0 + 6000, body: "Keep the old wording.", suggestionId: "d1", replies: [], resolved: false };
/** A resolved comment h5 answered; h5's change card is in the fourth paragraph group, the one the changes fold hides under
 *  All. The comment's own card is never behind that fold (the about follow-on): resolved, it is under the Resolved fold. */
const onH5: StoreComment = { id: T0 + 7000 + "-31", author: "you", ts: T0 + 7000, body: "Measure twice.", suggestionId: "h5", replies: [], resolved: true };
const withComments = (comments: StoreComment[], over: Partial<Status> = {}): Status =>
  full({ store: { v: 3, path: "docs/report.md", suggestions: SUGG, comments }, ...over });
const slotNotes = (aside: El): string[] => texts(aside.querySelector(".fc-composer")!.querySelectorAll(".fc-composer-ref .fc-note"));
const composerIn = (aside: El): El => aside.querySelector(".fc-composer")!.parentNode!;
const titleOf = (c: El, sel: string): string => { const n = c.querySelector(sel); assert.ok(n, sel); return n!.title; };
const tagTitled = (c: El, text: string): El => { const t = c.querySelectorAll(".fc-card-head .fc-tag").find((x) => x.textContent === text); assert.ok(t, "the tag " + text); return t!; };
const savedLine = (aside: El): El | null => aside.querySelector(".fc-cards .fc-saved-hidden");
const RESOLVED_LINE = "The comment's card is under “Resolved” below; the reply still goes to it.";
const MEANWHILE_LINE = "The comment was resolved meanwhile, so its card is under “Resolved” below; the reply still goes to it.";
/** The keyboard in the slot's box, then Cancel: where the panel puts the focus (focusAway). The stand-in's focus() takes
 *  buttons and inputs only, so the textarea is set as the active element directly. */
function cancelFromBox(aside: El): El | null {
  const box = aside.querySelector(".fc-composer")!;
  doc.activeElement = box.querySelector("textarea") as El;
  act(box, "fccancel")!.click();
  return doc.activeElement;
}
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

// ── a reply on a resolved comment a change answered, under All and under Comments ─────────────────

test("a resolved comment a change answered, replied to from the open Resolved fold under All, then Comments picked and the fold closed: the slot's line names the Resolved fold, where its own card is under either filter, and Cancel focuses that fold; never a '… N more changes' row, which Comments does not render", async (t: TestContext) => {
  store.delete(SETTINGS_KEY);
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w, withComments([passage, { ...hosted, resolved: true }, whole, region, done]));
  // under All the comment is its own card, under the closed Resolved fold (the about follow-on, 2026-09-10; before it the
  // comment rode the change card, resolved or not); the change card counts open comments alone, so it wears no count tag
  assert.ok(!card(aside, hosted.id), "All: the resolved comment's card is under the closed Resolved fold");
  assert.equal(act(aside, "fcresolved")!.textContent, "▸ Resolved (2)");
  assert.equal(card(aside, "chg:h1")!.querySelectorAll(".fc-about-count").length, 0, "the change card counts no open comment about it");
  act(aside, "fcresolved")!.click();                  // open the fold
  card(aside, hosted.id)!.querySelector(".fc-card-head")!.click();
  act(aside, "fcreply", hosted.id)!.click();
  assert.ok(composerIn(aside).classes.includes("fc-card") && composerIn(aside).dataset.id === hosted.id, "All: the box in the comment's own card, under the open fold");
  await pick(aside, "comments");
  assert.ok(!act(aside, "fcmore"), "no change fold row under Comments");
  assert.equal(composerIn(aside).dataset.id, hosted.id, "Comments: the fold stays open across the pick, and the box in the card");
  act(aside, "fcresolved")!.click();                  // close the fold under the reply
  assert.ok(!card(aside, hosted.id), "Comments: the comment's own card is under the closed Resolved fold");
  assert.equal(act(aside, "fcresolved")!.textContent, "▸ Resolved (2)");
  assert.ok(composerIn(aside).classes.includes("fc-panel"), "the box is back in the panel's slot");
  assert.deepEqual(slotNotes(aside).slice(1), [RESOLVED_LINE], "the line says where the card is");
  const focused = cancelFromBox(aside);
  assert.equal(focused!.dataset.act, "fcresolved", "Cancel: the keyboard goes to the Resolved fold, the row that brings the card back");
  store.delete(SETTINGS_KEY);
});

test("under Comments, a resolved comment answered by a change the fold hides under All (h5, the fourth group): Reply from the open Resolved fold, then the fold closed; the line names Resolved, not '… 1 more change', and Cancel focuses the fold; under All the comment's own card is under Resolved too, whatever the changes fold does to h5's card", async (t: TestContext) => {
  store.set(SETTINGS_KEY, JSON.stringify({ commentsFilter: "comments" }));
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w, withComments([passage, hosted, whole, region, done, onH5]));
  assert.deepEqual(chosen(aside), ["comments"]);
  assert.ok(!act(aside, "fcmore"), "Comments renders no change fold row");
  act(aside, "fcresolved")!.click();                  // open the fold: done and onH5
  assert.deepEqual(commentCards(aside).map((c) => c.dataset.id), [passage.id, whole.id, region.id, hosted.id, done.id, onH5.id], "oldest first, the open cards then the fold's");
  card(aside, onH5.id)!.querySelector(".fc-card-head")!.click();
  act(aside, "fcreply", onH5.id)!.click();
  assert.equal(composerIn(aside).dataset.id, onH5.id, "the box in the comment's own card");
  act(aside, "fcresolved")!.click();                  // close the fold under the reply
  assert.ok(!card(aside, onH5.id), "the card is behind the closed fold");
  assert.ok(composerIn(aside).classes.includes("fc-panel"));
  assert.deepEqual(slotNotes(aside).slice(1), [RESOLVED_LINE]);
  assert.equal(cancelFromBox(aside)!.dataset.act, "fcresolved", "Cancel: the Resolved fold");
  // under All: h5's change card is behind the changes fold, and the comment's own card under the Resolved fold (the about
  // follow-on, 2026-09-10; before it the comment rode h5's card, and the changes fold row was the one named and focused)
  await pick(aside, "all");
  assert.ok(!card(aside, "chg:h5"), "h5's group is folded");
  assert.ok(!card(aside, onH5.id), "the comment's card is under the closed Resolved fold, not the changes fold");
  act(aside, "fcresolved")!.click();                  // open the Resolved fold: the comment's card, h5's still folded
  assert.ok(card(aside, onH5.id) && !card(aside, "chg:h5"), "the comment's card shows without h5's");
  assert.ok(card(aside, onH5.id)!.classes.includes("open"), "still open: the keyed expand state is untouched by the pick");
  act(aside, "fcreply", onH5.id)!.click();
  assert.equal(composerIn(aside).dataset.id, onH5.id, "the box in the comment's own card");
  act(aside, "fcmore")!.click();                      // unfold the changes: h5's card, with no count tag (the comment is resolved)
  assert.ok(card(aside, "chg:h5"), "h5's card shows");
  assert.equal(card(aside, "chg:h5")!.querySelectorAll(".fc-about-count").length, 0, "a resolved comment is not counted on the change card");
  assert.equal(composerIn(aside).dataset.id, onH5.id, "the box stays in the comment's card");
  act(aside, "fcmore")!.click();                      // fold the changes again under the reply: the comment's card stays
  assert.ok(!card(aside, "chg:h5") && !!card(aside, onH5.id), "the changes fold hides change cards alone");
  assert.equal(composerIn(aside).dataset.id, onH5.id);
  act(aside, "fcresolved")!.click();                  // close the Resolved fold under the reply
  assert.ok(composerIn(aside).classes.includes("fc-panel"));
  assert.deepEqual(slotNotes(aside).slice(1), [RESOLVED_LINE], "the line names Resolved under All too");
  assert.equal(cancelFromBox(aside)!.dataset.act, "fcresolved", "All: the Resolved fold row");
  store.delete(SETTINGS_KEY);
});

test("under Comments, a comment on a change resolved while its reply is written: the card moves into the closed fold, the line says so and names the fold, and Cancel focuses it", async (t: TestContext) => {
  store.set(SETTINGS_KEY, JSON.stringify({ commentsFilter: "comments" }));
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w, full());
  card(aside, hosted.id)!.querySelector(".fc-card-head")!.click();
  act(aside, "fcreply", hosted.id)!.click();
  assert.equal(composerIn(aside).dataset.id, hosted.id, "the box in the comment's own card");
  act(aside, "fcresolve", hosted.id)!.click(); await flush();
  const m = lastOf(w, "fileComments", "resolve");
  assert.deepEqual(m.args, { commentId: hosted.id, on: true });
  answer(w, withComments([passage, { ...hosted, resolved: true }, whole, region, done], { storeMtimeNs: "1757145600000000005" }), m); await flush(); await flush();
  assert.ok(!card(aside, hosted.id), "resolved: under the closed fold");
  assert.equal(act(aside, "fcresolved")!.textContent, "▸ Resolved (2)");
  assert.ok(composerIn(aside).classes.includes("fc-panel"));
  assert.deepEqual(slotNotes(aside).slice(1), [MEANWHILE_LINE]);
  assert.equal(cancelFromBox(aside)!.dataset.act, "fcresolved");
  store.delete(SETTINGS_KEY);
});

// ── the "answered by a change" tag and the change card's cue name a detached change ────────────────

test("under Comments a comment a DETACHED change answered wears the 'answered by a change' tag with a title that names the change and says detached; on a pending change the title says pending; under All the comment keeps its own card, both change cards count it, and the detached change card's cue says nobody decides it", async (t: TestContext) => {
  store.set(SETTINGS_KEY, JSON.stringify({ commentsFilter: "comments" }));
  const w = world(); t.after(() => w.close());
  const { aside, button } = await openPanel(w, full({ store: { v: 3, path: "docs/report.md", suggestions: SUGG, comments: [passage, hosted, onD1], detached: [D1] } }));
  assert.equal(button.textContent, "Comments · 3 · 5 changes · 1 detached change");
  const d = card(aside, onD1.id)!, p = card(aside, hosted.id)!;
  assert.ok(d && p, "both answered comments stand on their own cards under Comments");
  // the about tag with source "answered" (a legacy suggestionId; the about follow-on, 2026-09-10, replacing the "on a change"
  // tag): its data-refs the change's id, its title the change's words and its state
  assert.deepEqual(tags(d), ["answered by a change"]); assert.deepEqual(tags(p), ["answered by a change"]);
  const dt = tagTitled(d, "answered by a change"), pt = tagTitled(p, "answered by a change");
  assert.ok(dt.classes.includes("fc-about") && pt.classes.includes("fc-about"), "the about tag's class");
  assert.equal(dt.dataset.refs, "d1"); assert.equal(pt.dataset.refs, "h1");
  assert.equal(dt.title, "The session answered this comment with: cold starts were slow → cold starts stay slow (detached: the file no longer holds its text)");
  assert.equal(pt.title, "The session answered this comment with: reduced → cut (pending)");
  assert.equal(d.querySelector(".fc-ref")!.textContent, "cold starts were slow → cold starts stay slow", "no passage: the change's words as the reference, as for a pending one");
  assert.equal(titleOf(d, ".fc-kind"), "A comment the session answered with a change", "answered, never about: the person named no change (the review, 2026-09-10)");
  assert.equal(p.querySelector(".fc-ref")!.textContent, "“cut p95 latency”", "a legacy passage comment keeps its passage as the reference");
  assert.equal(titleOf(p, ".fc-kind"), "A comment on a passage");
  // All: the comment keeps its own card (before the about follow-on it rode the change card), the pending change's card
  // counts it, and the detached change's card is in its group behind the fold (five groups: four paragraphs and the
  // detached one) and counts it too
  await pick(aside, "all");
  assert.ok(card(aside, onD1.id), "the comment's own card under All too");
  assert.equal(card(aside, "chg:h1")!.querySelector(".fc-about-count")!.textContent, "1 comment", "the pending change counts the open comment it answered");
  act(aside, "fcmore")!.click();
  const dc = card(aside, "chg:d1")!;
  assert.ok(dc.classes.includes("fc-card-detached"));
  assert.deepEqual(tags(dc), ["detached", "1 comment"], "the detached change counts it too");
  assert.ok(texts(aside.querySelectorAll(".fc-group")).includes(DETACHED_GROUP_TITLE));
  assert.equal(titleOf(dc, ".fc-kind"), "A change the session made to the file, whose text the file no longer holds; nothing here accepts or rejects it");
  assert.equal(titleOf(card(aside, "chg:h1")!, ".fc-kind"), "A change the session made to the file, for you to accept or reject");
  assert.ok(!dc.querySelector('[data-act="fcaccept"]'), "…and indeed it offers no decision");
  assert.ok(!dc.querySelector('[data-act="fcchangecomment"]'), "nor Comment on this change: a detached card has no actions");
  store.delete(SETTINGS_KEY);
});

// ── the filter while the editor is up ──────────────────────────────────────────────────────────────

test("while the editor is up the filter row is offered (its list half is the point) and Show changes inline is not; the option titles say the editor keeps its change marks, and say the read view's marks rule again once the edit ends", async (t: TestContext) => {
  store.delete(SETTINGS_KEY);
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w, full());
  assert.equal(option(aside, "comments").title, "Show only the comments, including comments on changes; the change marks in the text are hidden with the change cards");
  assert.equal(option(aside, "changes").title, "Show only the changes, each with the comments made on it; the comment highlights in the text are hidden with the comment cards");
  // Edit: begin() runs at the click and renders; the viewer then holds the body and answers editing()
  w.editing = true;
  const begun = w.tracked!.begin()!;
  assert.equal(begun.records.length, SUGG.length, "the sidecar's records ride into the editor, whatever the filter (pendingRecords reads the store)");
  assert.ok(filterRow(aside), "the filter row stands in edit mode");
  assert.equal(act(aside, "fcinline"), null, "Show changes inline does not: the editor draws every change itself");
  assert.equal(option(aside, "comments").title, "Show only the comments, including comments on changes; the editor keeps every change marked in its text");
  assert.equal(option(aside, "changes").title, "Show only the changes, each with the comments made on it", "the editor paints no comment highlight: nothing to claim hidden");
  await pick(aside, "comments");
  assert.deepEqual(changeCards(aside), [], "the list half works in the editor");
  assert.deepEqual(commentCards(aside).map((c) => c.dataset.id), [passage.id, whole.id, region.id, hosted.id], "every comment card on its own, oldest first");
  assert.equal(stored()!.commentsFilter, "comments");
  assert.equal(option(aside, "comments").title, "Show only the comments, including comments on changes; the editor keeps every change marked in its text");
  // the edit ends: the read view's titles are back
  w.editing = false;
  await pick(aside, "all");
  assert.equal(option(aside, "comments").title, "Show only the comments, including comments on changes; the change marks in the text are hidden with the change cards");
  assert.equal(option(aside, "changes").title, "Show only the changes, each with the comments made on it; the comment highlights in the text are hidden with the comment cards");
  store.delete(SETTINGS_KEY);
});

// ── a comment saved while Changes is chosen ────────────────────────────────────────────────────────

test("a whole-file comment saved under Changes: the box closes, the card is hidden as the choice says, and a line at the top of the list says the comment is saved and where its card is; All shows the card and ends the line, and a return to Changes does not bring it back", async (t: TestContext) => {
  t.mock.timers.enable({ apis: ["setInterval"] });   // the poll's re-render below is driven, not simulated
  store.set(SETTINGS_KEY, JSON.stringify({ commentsFilter: "changes" }));
  const w = world(); t.after(() => w.close());
  const { aside, button } = await openPanel(w, full());
  assert.deepEqual(chosen(aside), ["changes"]);
  assert.equal(commentCards(aside).length, 0);
  act(aside, "fcfile")!.click();
  const m = await saveNote(aside, w, "Tighten the summary.");
  assert.deepEqual(m.args, { note: "Tighten the summary." });
  const fresh: StoreComment = { id: T0 + 9000 + "-9", author: "you", ts: T0 + 9000, body: "Tighten the summary.", anchor: null, replies: [], resolved: false };
  answer(w, withComments([...ALL_COMMENTS, fresh], { storeMtimeNs: "1757145600000000006" }), m); await flush(); await flush();
  assert.equal(aside.querySelector(".fc-composer")!.hidden, true, "saved: the box closed");
  assert.equal(card(aside, fresh.id), null, "the card is hidden: Changes is chosen");
  assert.equal(button.textContent, "Comments · 5 · 5 changes");
  const line = savedLine(aside);
  assert.ok(line, "the line for the hidden card");
  assert.equal(line!.dataset.id, fresh.id);
  assert.equal(line!.textContent, "Your comment is saved; its card is hidden while Changes is chosen above (All or Comments shows it).✕", "a whole-file comment has no mark in the file: the card alone");
  assert.equal(aside.querySelector(".fc-cards")!.childNodes[0], line, "first in the list, where the box was");
  // the row's shape (the third review, and file-comments-filter-saved-line.test.ts): .fc-note on the words alone, the row
  // unsized, so the ✕, a .fileview-btn, renders at the panel buttons' size and not compounded under a 0.86em row
  assert.deepEqual(line!.classes, ["fc-row", "fc-saved-hidden"], "the row unsized: .fc-row and the line's own class, never .fc-note");
  assert.deepEqual((line!.childNodes[0] as El).classes, ["fc-note"], ".fc-note on the words' span");
  assert.equal(act(line!, "fchiddenx")!.getAttribute("aria-label"), "Dismiss");
  assert.deepEqual(chosen(aside), ["changes"], "the kept choice stands");
  assert.equal(stored()!.commentsFilter, "changes");
  // the poll's re-render keeps it: the sidecar moved, the poll re-asks status, and the answer's render still holds the line
  // (a result posted with no ask outstanding is dropped by the panel, so it must be the poll's own ask that is answered)
  const asks = w.posted.filter((m) => m.type === "fileComments" && m.verb === "status").length;
  w.mtimes[STORE_PATH] = "1757145600000000007";
  t.mock.timers.tick(2500); await flush(); await flush(); await flush();
  assert.equal(w.posted.filter((m) => m.type === "fileComments" && m.verb === "status").length, asks + 1, "the moved sidecar re-asks status");
  answer(w, withComments([...ALL_COMMENTS, fresh], { storeMtimeNs: "1757145600000000007" })); await flush(); await flush();
  assert.ok(savedLine(aside), "still there after the poll's status");
  assert.equal(savedLine(aside)!.dataset.id, fresh.id, "the same comment's line");
  // All: the card, and the line is over
  await pick(aside, "all");
  assert.ok(card(aside, fresh.id), "All shows the card");
  assert.equal(savedLine(aside), null);
  await pick(aside, "changes");
  assert.equal(savedLine(aside), null, "seen once: Changes again does not bring the line back");
  assert.equal(card(aside, fresh.id), null);
  store.delete(SETTINGS_KEY);
});

test("a passage comment saved under Changes: the line names the card and the highlight, neither painted; the ✕ ends it; a comment about a change (the change card's Comment on this change) is its own card, hidden like every comment's, so the line is due for it too and the change card counts it; closing the panel ends a standing line", async (t: TestContext) => {
  store.set(SETTINGS_KEY, JSON.stringify({ commentsFilter: "changes" }));
  const w = world(); t.after(() => w.close());
  const { aside, button } = await openPanel(w, full());
  assert.equal(highlights(w).length, 0, "Changes: no highlight painted");
  startPassageComment(w, "fallback path");          // a passage no change mark splits (h4's tint holds "Risks")
  const m = await saveNote(aside, w, "Name the risks.");
  assert.equal(m.args.note, "Name the risks.");
  assert.equal(m.args.anchor.quote, "fallback path");
  const fresh: StoreComment = { id: T0 + 9500 + "-10", author: "you", ts: T0 + 9500, body: "Name the risks.", anchor: { quote: "fallback path", prefix: "Risks remain in the ", suffix: "." }, replies: [], resolved: false };
  answer(w, withComments([...ALL_COMMENTS, fresh], { storeMtimeNs: "1757145600000000007" }), m); await flush(); await flush();
  assert.ok(!card(aside, fresh.id));
  assert.equal(highlights(w).length, 0, "the highlight is hidden with the card");
  assert.equal(savedLine(aside)!.textContent, "Your comment is saved; its card and highlight are hidden while Changes is chosen above (All or Comments shows them).✕");
  act(aside, "fchiddenx")!.click();
  assert.ok(!savedLine(aside), "dismissed");
  assert.deepEqual(chosen(aside), ["changes"]);
  // a comment about a change (the about follow-on, 2026-09-10; before it the change card's Reply bound a comment that rode the
  // card, so nothing was hidden and no line was due): Comment on this change opens the passage composer in the panel's slot
  // over the change's new text with the about option checked, and the saved comment is its own card, hidden under Changes
  // like every comment's, so the line is due for it too; the change card counts it
  assert.ok(!card(aside, "chg:h2")!.classes.includes("open"), "h2's card is collapsed before the click");
  act(aside, "fcchangecomment", "h2")!.click(); await flush();
  assert.ok(card(aside, "chg:h2")!.classes.includes("open"), "Comment on this change opens the change card");
  assert.ok(composerIn(aside).classes.includes("fc-panel"), "the composer in the panel's slot, not in the card");
  const opt = aside.querySelector('.fc-composer .fc-about-opt input[data-opt="about"]');
  assert.ok(opt && opt.checked, "the about option, checked");
  assert.equal(opt!.parentNode!.textContent, "about this change");
  const m2 = await saveNote(aside, w, "Say which percentile.");
  assert.deepEqual(Object.keys(m2.args).sort(), ["anchor", "changeIds", "hintOffset", "note"], "a passage comment naming the change; never suggestionId");
  assert.equal(m2.args.note, "Say which percentile.");
  assert.equal(m2.args.anchor.quote, h2.newText, "the anchor over the change's new text");
  assert.equal(m2.args.hintOffset, h2.curFrom);
  assert.deepEqual(m2.args.changeIds, ["h2"]);
  const onH2: StoreComment = { id: T0 + 9600 + "-11", author: "you", ts: T0 + 9600, body: "Say which percentile.", anchor: m2.args.anchor, anchorAt: h2.curFrom, changeIds: ["h2"], replies: [], resolved: false };
  answer(w, withComments([...ALL_COMMENTS, fresh, onH2], { storeMtimeNs: "1757145600000000008" }), m2); await flush(); await flush();
  assert.ok(!card(aside, onH2.id), "Changes: the comment's own card is hidden like every comment's");
  assert.equal(highlights(w).length, 0, "and its highlight with it");
  assert.equal(card(aside, "chg:h2")!.querySelector(".fc-about-count")!.textContent, "1 comment", "the change card counts the comment about it");
  assert.equal(savedLine(aside)!.dataset.id, onH2.id, "the line is due for it too");
  assert.equal(savedLine(aside)!.textContent, "Your comment is saved; its card and highlight are hidden while Changes is chosen above (All or Comments shows them).✕");
  // a standing line ends with the panel: the person read it with the panel open
  act(aside, "fcfile")!.click();
  const m3 = await saveNote(aside, w, "One more.");
  const fresh3: StoreComment = { id: T0 + 9700 + "-12", author: "you", ts: T0 + 9700, body: "One more.", anchor: null, replies: [], resolved: false };
  answer(w, withComments([...ALL_COMMENTS, fresh, onH2, fresh3], { storeMtimeNs: "1757145600000000009" }), m3); await flush(); await flush();
  assert.equal(savedLine(aside)!.dataset.id, fresh3.id, "the latest save's line");
  button.click(); await flush();                     // close
  button.click(); answer(w, withComments([...ALL_COMMENTS, fresh, onH2, fresh3], { storeMtimeNs: "1757145600000000009" })); await flush(); await flush();
  const again = w.main.querySelector(".fileview-aside")!;
  assert.deepEqual(chosen(again), ["changes"]);
  assert.equal(savedLine(again), null, "reopened: no line about the earlier save");
  store.delete(SETTINGS_KEY);
});

// ── the Changes option carries the label's detached clause ─────────────────────────────────────────

test("a file with detached changes alone: the label says '1 detached change', the Changes option 'Changes 0 · 1 detached' with a title naming them, and picking it lists the detached card; with pending changes too the clause follows the count; two detached read as two", async (t: TestContext) => {
  store.delete(SETTINGS_KEY);
  const w = world(); t.after(() => w.close());
  const only = status({ hunks: [], store: { v: 3, path: "docs/report.md", suggestions: [], comments: [], detached: [D1] }, unsent: { comments: [], replies: [], accepted: 0, rejected: 0, watermark: null } });
  const { aside, button } = await openPanel(w, only);
  assert.equal(button.textContent, "Comments · 0 · 1 detached change");
  assert.deepEqual(cardCounts(only), { comments: 0, changes: 0 }, "the shared counts are unchanged: a detached change is not pending");
  assert.deepEqual(texts(filterRow(aside)!.childNodes as El[]), ["All", "Comments 0", "Changes 0 · 1 detached"]);
  assert.equal(option(aside, "changes").title, "Show only the changes, each with the comments made on it; the comment highlights in the text are hidden with the comment cards; the detached change is listed too, in a group of its own");
  await pick(aside, "changes");
  assert.deepEqual(changeCards(aside).map((c) => c.dataset.id), ["chg:d1"], "the option opens on the card it counted");
  assert.equal(aside.querySelector(".fc-empty"), null);
  w.close();
  const w2 = world(); t.after(() => w2.close());
  const { aside: a2, button: b2 } = await openPanel(w2, full({ store: { v: 3, path: "docs/report.md", suggestions: SUGG, comments: ALL_COMMENTS, detached: [D1, D2] } }));
  assert.equal(b2.textContent, "Comments · 4 · 5 changes · 2 detached changes");
  assert.deepEqual(texts(filterRow(a2)!.childNodes as El[]), ["All", "Comments 4", "Changes 5 · 2 detached"]);
  assert.ok(option(a2, "changes").title.endsWith("; the 2 detached changes are listed too, in a group of their own"));
  assert.equal(option(a2, "changes").dataset.key, "changes", "the same option, the same key");
  store.delete(SETTINGS_KEY);
});

// ── the toggles' confirm rows stand under the toggles, above the filter ────────────────────────────

test("Track changes on an untracked file with cards: the scope choice renders directly under the toggles' row, above the filter's; so does the folder Stop confirm and a refused set-tracked's row; the filter's row is under the toggles again once answered", async (t: TestContext) => {
  store.delete(SETTINGS_KEY);
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w, full({ trackedBy: null }));
  assert.deepEqual(rowsOf(aside), ["fc-row", "fc-row fc-filter"]);
  act(aside, "fctrack")!.click();
  assert.deepEqual(rowsOf(aside), ["fc-row", "fc-row fc-choice", "fc-row fc-filter"], "the answer to the click sits under the button that asked");
  assert.equal(aside.querySelector(".fc-choice .fc-note")!.textContent, "Track:");
  act(aside, "fctrackcancel")!.click();
  assert.deepEqual(rowsOf(aside), ["fc-row", "fc-row fc-filter"]);
  // a refused set-tracked: its row under the toggles' row too (the plan: an error row under the control that asked)
  act(aside, "fctrack")!.click();
  act(aside, "fctrackfile")!.click(); await flush();
  const m = lastOf(w, "fileComments", "set-tracked");
  assert.deepEqual(m.args, { on: true, scope: "file" });
  refuse(w, m, "io", "the tracking config could not be written"); await flush(); await flush();
  const kids = headKids(aside).map((k) => k.classes.join(" ") + (k.dataset.slot ? "@" + k.dataset.slot : ""));
  assert.deepEqual(kids, ["fc-row", "fileview-err fc-err@track", "fc-row fc-filter"], "the refusal's row between the toggles and the filter");
  act(aside, "fcerrx")!.click();
  assert.deepEqual(rowsOf(aside), ["fc-row", "fc-row fc-filter"]);
  w.close();
  const w2 = world(); t.after(() => w2.close());
  const { aside: a2 } = await openPanel(w2, full({ trackedBy: { kind: "folder", entry: "docs" } }));
  act(a2, "fctrack")!.click();
  assert.deepEqual(rowsOf(a2), ["fc-row", "fc-row fc-choice", "fc-row fc-filter"], "the Stop confirm, the same place");
  assert.ok(a2.querySelector(".fc-choice .fc-note")!.textContent.startsWith("Stop tracking everything under "));
  act(a2, "fctrackcancel")!.click();
  assert.deepEqual(rowsOf(a2), ["fc-row", "fc-row fc-filter"]);
  store.delete(SETTINGS_KEY);
});

// ── source pins ────────────────────────────────────────────────────────────────────────────────────

test("pins: replyAway takes the filter into account before the Resolved fold and has no change fold case (the about follow-on: no comment is behind the changes fold); the saved line's state, its action, and its place; the head's confirm rows go above the filter row in the DOM while the source order the filter suite pins stands", () => {
  const away = SRC.slice(SRC.indexOf("private replyAway("), SRC.indexOf("private hiddenSavedRow("));
  assert.match(away, /if \(!found\) return \{ text: "The comment is gone from the file's comments\.", gone: true, back: null \};/);
  assert.match(away, /if \(this\.activeFilter\(\) === "changes"\) return \{ gone: false, back: "fcfilter", text: "The comment's card is hidden while Changes is chosen above \(All or Comments shows it\); the reply still goes to it\." \};/, "under Changes every comment's card is hidden, a comment about a change too");
  assert.match(away, /if \(found\.resolved\) return \{ gone: false, back: "fcresolved", text: c\.resolved \? "The comment's card is under “Resolved” below; the reply still goes to it\." : "The comment was resolved meanwhile, so its card is under “Resolved” below; the reply still goes to it\." \};/);
  assert.ok(away.indexOf('this.activeFilter() === "changes"') < away.indexOf("found.resolved"), "the filter before the fold: under Changes no Resolved fold is rendered to name");
  assert.match(away, /return \{ gone: false, back: null, text: "The comment's card is not in the list; the reply still goes to it\." \};/, "the one case left: a status not yet in");
  assert.doesNotMatch(away, /fcmore|hunk|changeView/, "no change fold case: every comment is its own card, never behind the changes fold (the about follow-on, 2026-09-10; before it a comment bound to a change rode the change card, and the row named was the fold's)");
  assert.match(SRC, /hiddenSaved: string \| null = null;/);
  assert.match(SRC, /fchiddenx: \(\) => \{ this\.hiddenSaved = null; this\.render\(\); \},/, "the ✕ is one of the panel's own delegated actions");
  assert.match(SRC, /const before = new Set\(this\.cards\(\)\.map\(\(x\) => x\.id\)\);[^\n]*\n(?:\s+\/\/[^\n]*\n)*\s+this\.gesture\(\);\n\s+let r: Status \| null;/, "the comments before the save, so the fresh one is known (then the save's own gesture: the arrivals follow-on, 2026-09-09; the count it sampled went with the save's scroll, decision 43)");
  assert.match(SRC, /const hid = r !== null && c\.kind !== "reply" && this\.noteHiddenSave\(before, note\);\n\s+const lined = r !== null && this\.landSaved\(c, had, r, note\);[^\n]*\n\s+if \(r\) this\.closeComposer\(\);[^\n]*\n\s+if \(hid \|\| \(lined && c\.kind !== "reply"\)\) this\.render\(\);/, "noted after the save, before the landing (which finds no card the filter hides, so raises no line of its own) and the composer's close; the cards rendered once more with the line");
  assert.match(SRC, /if \(!mine \|\| this\.activeFilter\(\) !== "changes"\) return false;/, "every comment saved under Changes, a comment about a change too (the about follow-on; before it a comment on a change rode the change card and raised no line)");
  assert.match(SRC, /if \(!card \|\| filter !== "changes"\) \{ this\.hiddenSaved = null; return null; \}/, "the line ends, and the id with it, once the card shows or the comment is gone");
  assert.match(SRC, /for \(const n of \[this\.loader\("bytes"\), this\.errRow\("bytes"\)\]\) if \(n\) list\.appendChild\(n\);\n\s+const saved = this\.hiddenSavedRow\(filter\);/, "at the top of the list, before the empty states and the cards");
  assert.match(SRC, /closePanel\(\): void \{(?:(?!\n  \}\n)[\s\S])*?this\.hiddenSaved = null;[^\n]*\n\s+this\.stopPoll\(\);\n\s+\}\n/, "closePanel ends it");   // the method's own body (draftAsk stands between it and dispose)
  const head = SRC.slice(SRC.indexOf("private renderHead("), SRC.indexOf("private renderComposer("));
  assert.match(head, /let filterRow: HTMLElement \| null = null;/);
  assert.match(head, /head\.appendChild\(seg\);\n\s+filterRow = seg;/);
  assert.match(head, /const underToggles = \(n: HTMLElement\): void => \{ head\.insertBefore\(n, filterRow\); \};/, "a confirm row goes before the anchor: the filter's row when offered, else the first of the head's other rows (set below, the second round's fix), else at the end");

  assert.match(head, /underToggles\(pick\);/); assert.match(head, /underToggles\(stop\);/);
  assert.match(head, /for \(const n of Array\.from\(head\.childNodes\)\) if \(n\.nodeType === 1 && \(n as HTMLElement\)\.dataset\.slot === "track"\) underToggles\(n as HTMLElement\);/, "the track slot's rows, built with the head's others, are moved under the toggle — the head's own children, never a row's ✕");
  assert.ok(head.indexOf("head.appendChild(seg);") < head.indexOf("if (this.trackChoice && s) {"), "the source order the filter suite pins is unchanged");
  // the Changes option: the count as pinned, the detached clause on the button alone
  assert.match(head, /const b = btn\(key === "changes" && d \? label \+ " · " \+ d \+ " detached" : label, "fcfilter", "fileview-btn fc-toggle"\);/);
  assert.match(head, /const d = s && s\.store \? detachedChanges\(s\.store\)\.length : 0;/);
  // the titles: the read view's marks, or the editor's
  assert.match(head, /const editing = this\.ctx\.editing\(\);\n\s+const commentsTitle = /);
  // the about tag's title by the changes' words and states (the about follow-on, 2026-09-10, replacing the "on a change" tag,
  // whose title read the change's state off `hunk`), the cues' by the card's
  assert.match(SRC, /const t = el\("span", "fc-tag fc-about", aboutTagWords\(refs\.length, source\)\);\n\s+t\.dataset\.refs = refs\.map\(\(r\) => r\.id\)\.join\(" "\);\n\s+t\.title = \(source === "about" \? "This comment is about: " : "The session answered this comment with: "\)\n\s+\+ refs\.map\(\(r\) => \(r\.kind === null \? "a change the file no longer records" : changeRef\(\{ kind: r\.kind, oldText: r\.oldText, newText: r\.newText \}\)\) \+ " \(" \+ refStateWords\(r\.state\) \+ "\)"\)\.join\("; "\);/);
  assert.match(SRC, /kind\.title = c\.kind === "region" \? "A comment on a region of the picture"\n\s+: c\.kind === "file" && c\.refs\.some\(\(r\) => r\.source === "about"\) \? "A comment about a change"\n\s+: c\.kind === "file" && c\.refs\.length \? "A comment the session answered with a change"\n\s+: c\.kind === "file" \? "A comment on the file as a whole" : "A comment on a passage";/, "a comment with no passage that names changes is the file kind, cued as about a change when the person picked one (source about) and as answered when its only binding is the format's field (the review, 2026-09-10)");
  assert.match(SRC, /kind\.title = c\.detached \? "A change the session made to the file, whose text the file no longer holds; nothing here accepts or rejects it" : "A change the session made to the file, for you to accept or reject";/);
});

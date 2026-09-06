// The Comments panel while the editor is up, AROUND A SAVE THAT LANDS (plans/file-review.md, Slice 5; the 2026-09-06
// review of the slice, third pass). The viewer keeps the editor up past a landed save when keystrokes were typed during
// the round trip or a decision was clicked then (file-view.ts, hooks.saved), so a second Save from the same editor
// follows. Covered: that Save is fenced on the FIRST save's reply — the sidecar the editor's records were written back
// to — never the poll's latest, so a decision landed elsewhere between the two saves is refused rather than written
// back as pending, and the head says so from the status that shows it, before Save; the same when that decision pruned
// the sidecar; a landed save that leaves nothing pending seeds nothing, as Edit over no changes does; the host's
// `logWarning` on a save reply rides the resolved value and is said in the head; a sidecar-only verb's reply during an
// edit that read a later file puts the file's row in the head (the poll's baseline follows the reply, so nothing else
// could); and Accept all / Reject all while editing say where to decide ONCE, the click's row taking the caption's
// place, with words that name the route that needs no mouse. Driven as a panel over the behavior suite's DOM
// stand-in. Synthetic fixtures only: the notes-api world, placeholder ids.
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
  consent: () => Promise<boolean>;                  // the file-editing consent, deferrable: a decision waits on it while Edit goes ahead
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
    editing: false, tracked: null, consent: async () => true,
  } as World;
  rows(code, text);
  // the viewer's renderBody + fireRendered — in the real viewer no hook fires while editing; a test that paints in edit
  // mode is exercising the panel's own render, which the hook reaches through paintAll's editing branch
  w.setText = (s) => { text = s; rows(code, s); for (const cb of w.hooks.rendered) cb(); };
  w.ctx = {
    path: ABS, sid: SID, todoId: null,
    body: () => body as unknown as HTMLElement, mode: () => "raw", text: () => text, mtimeNs: () => w.viewMtime, media: () => null, mediaElement: () => null, renderedImages: () => [], pdfPages: () => [],
    identity: () => ({ name: "api", color: null }),
    onRendered: (cb) => { w.hooks.rendered.push(cb); }, onSelection: () => { /* inert */ },
    onSaved: () => { /* inert */ }, onClose: (cb) => { w.hooks.close.push(cb); },
    post: (m) => { w.posted.push(m); }, ensureEditingAllowed: () => w.consent(), setEditBlocked: () => { /* inert */ }, editing: () => w.editing, setTrackedEdit: (t) => { w.tracked = t; },
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
async function openPanel(w: World, s: Status): Promise<{ button: El; aside: El; DECIDE: string; CHANGES_MOVED: string }> {
  const fc = await import("./file-comments");
  const unit = fc.fileCommentsAction.mount(w.ctx) as unknown as El;
  const button = unit.childNodes[0] as El;
  answer(w, s); await flush();
  button.click();
  answer(w, s); await flush(); await flush();
  const aside = w.main.querySelector(".fileview-aside")!;
  assert.ok(aside, "the panel is mounted beside the body");
  return { button, aside, DECIDE: fc.DECIDE_IN_EDITOR, CHANGES_MOVED: fc.CHANGES_MOVED_UNDER_EDIT };
}
const card = (aside: El, key: string): El | null => aside.querySelector('.fc-card[data-id="' + key + '"]');
const act = (root: El, a: string, id?: string): El | null => root.querySelector('[data-act="' + a + '"]' + (id ? '[data-id="' + id + '"]' : ""));
const settle = (p: Promise<unknown>) => { const box: { ok?: unknown; err?: unknown } = {}; p.then((v) => { box.ok = v; }, (e) => { box.err = e; }); return box; };
const CHANGED = "the comments for ~/notes-api/docs/report.md changed on disk since you opened the file — reload and retry";
const FILE_CHANGED = "~/notes-api/docs/report.md changed on disk since you opened it — reload and retry";
const headRows = (aside: El): El[] => aside.querySelectorAll(".fc-sec-head .fc-err");
const CLOCK5 = "1757145600000000005";
const NS = (n: number) => "17571456000000000" + String(n).padStart(2, "0");
const WARN = "saved, but not written to the comments log for ~/notes-api/docs/report.md: EACCES: permission denied";
const H1_ACCEPT = { id: "h1", oldText: "reduced", newText: "cut" };
const NONE = { comments: [], replies: [], accepted: 0, rejected: 0, watermark: null };
/** An untracked file whose sidecar holds only changes: once every one is decided the host prunes it. */
const bare = (hunks: Hunk[], recs: Array<typeof rec1>, over: Partial<Status> = {}): Status =>
  pending({ trackedBy: null, unsent: NONE, store: { v: 3, path: "docs/report.md", suggestions: recs, comments: [] }, ...over }, hunks, recs);
const saved = (m: any, s: Status, extra: Record<string, unknown> = { logged: true }) =>
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId: m.reqId, ...s, verb: "save", ...extra } }));
/** The viewer after a landed save whose editor stayed up (hooks.saved's in-flight branch): its fence is the saved file. */
function stayedUp(w: World, text: string, fileNs: string): void {
  w.viewMtime = fileNs; w.disk = text; w.diskMtime = fileNs; w.mtimes[ABS] = fileNs;
}

// ── the fence after a landed save ───────────────────────────────────────────────────────────────────

test("a save that lands with the editor still up re-seeds the fence: a decision landed elsewhere before the next Save raises the head row from the status that shows it, and that Save is fenced on the first save's reply, not the poll's latest — refused, no retry", async (t: TestContext) => {
  t.mock.timers.enable({ apis: ["setInterval"] });
  const w = world(); t.after(() => w.close());
  const { aside, button, CHANGES_MOVED } = await openPanel(w, pending());
  w.editing = true;
  assert.deepEqual(w.tracked!.begin()!.records, [rec1, rec2]);
  // the person accepts h1 in the editor and saves; the reply is the sidecar with h2 alone, as the host wrote it back
  const first = settle(w.tracked!.save("the typed text", [rec2], { accepted: [H1_ACCEPT], rejected: [] }));
  await flush();
  const save1 = lastOf(w, "fileComments", "save");
  assert.equal(save1.fence.storeMtimeNs, NS(2), "fenced on the sidecar as it stood at Edit");
  saved(save1, pending({ fileMtimeNs: NS(9), storeMtimeNs: NS(10) }, [h2], [rec2]));
  await flush(); await flush();
  assert.deepEqual(first.ok, { mtimeNs: NS(9), logged: true });
  assert.equal(button.textContent, "Comments · 1 · 1 change", "the reply is the status");
  stayedUp(w, "the typed text", NS(9));                // keystrokes typed during the round trip: the editor stays
  assert.equal(headRows(aside).length, 0, "nothing moved: no head row");
  assert.equal(w.tracked!.routesSave(), true, "the editor still carries a record");
  // another browser accepts h2: the sidecar moves, the file does not, and the poll re-reads
  w.mtimes[STORE_PATH] = NS(20);
  const asks = countOf(w, "fileComments", "status");
  t.mock.timers.tick(2500); await flush(); await flush(); await flush();
  assert.equal(countOf(w, "fileComments", "status"), asks + 1, "the sidecar is still watched");
  answer(w, status({ fileMtimeNs: NS(9), storeMtimeNs: NS(20) })); await flush();
  assert.equal(headRows(aside).length, 1, "the head says the editor's change left the sidecar — before Save, which can only refuse");
  assert.equal(headRows(aside)[0].childNodes[0].textContent, CHANGES_MOVED);
  assert.equal(w.reloads, 0, "never over the editor's buffer");
  // Save again: fenced on the first save's reply, the sidecar the editor's record was written back to — the poll's latest
  // would pass the host's fence and write h2 back as pending, reverting the other decision
  const second = settle(w.tracked!.save("the typed text, more", [rec2], { accepted: [], rejected: [] }));
  await flush();
  const save2 = lastOf(w, "fileComments", "save");
  assert.deepEqual(save2.fence, { storeMtimeNs: NS(10), configMtimeNs: NS(3), fileMtimeNs: NS(9) }, "the first save's sidecar and the saved file");
  assert.deepEqual(save2.args.suggestions, [rec2]);
  refuse(w, save2, "store-moved", CHANGED); await flush();
  answer(w, status({ fileMtimeNs: NS(9), storeMtimeNs: NS(20) })); await flush(); await flush();
  assert.deepEqual(second.err, { code: "store-moved", error: CHANGED }, "the other decision stands, in the host's words");
  assert.equal(countOf(w, "fileComments", "save"), 2, "no retry: the records changed");
  assert.equal(headRows(aside).length, 1, "said once");
  // Cancel: the row goes with the editor; nothing to re-read, the bytes never moved
  w.editing = false; w.setText(w.disk);
  assert.equal(headRows(aside).length, 0);
  assert.equal(w.reloads, 0);
});

test("…and when that decision pruned the sidecar, Save still meets the first save's fence through the host — never an empty fence with the editor's record, which the host treats as a caller error, and never saveFile", async (t: TestContext) => {
  t.mock.timers.enable({ apis: ["setInterval"] });
  const w = world(); t.after(() => w.close());
  const { aside, CHANGES_MOVED } = await openPanel(w, bare([h1, h2], [rec1, rec2]));
  w.editing = true;
  assert.deepEqual(w.tracked!.begin()!.records, [rec1, rec2]);
  const first = settle(w.tracked!.save("the typed text", [rec2], { accepted: [H1_ACCEPT], rejected: [] }));
  await flush();
  const save1 = lastOf(w, "fileComments", "save");
  saved(save1, bare([h2], [rec2], { fileMtimeNs: NS(9), storeMtimeNs: NS(10) }));
  await flush(); await flush();
  assert.deepEqual(first.ok, { mtimeNs: NS(9), logged: true });
  stayedUp(w, "the typed text", NS(9));
  // elsewhere h2 is accepted: nothing left, no comment — the host pruned the sidecar; the poll sees it gone
  delete w.mtimes[STORE_PATH];
  t.mock.timers.tick(2500); await flush(); await flush(); await flush();
  const gone = status({ trackedBy: null, store: null, storeMtimeNs: null, unsent: NONE, fileMtimeNs: NS(9) });
  answer(w, gone); await flush();
  assert.equal(headRows(aside)[0].childNodes[0].textContent, CHANGES_MOVED);
  assert.equal(w.tracked!.routesSave(), true, "the record is still in the editor: its save meets the fence of the sidecar it came from");
  const frames = w.posted.length;
  const second = settle(w.tracked!.save("the typed text, more", [rec2], { accepted: [], rejected: [] }));
  await flush();
  const save2 = lastOf(w, "fileComments", "save");
  assert.equal(w.posted.length, frames + 1, "one frame, the save verb");
  assert.equal(save2.fence.storeMtimeNs, NS(10), "the first save's sidecar, not the poll's `` for a sidecar that is gone");
  refuse(w, save2, "store-moved", GONE); await flush();
  answer(w, gone); await flush(); await flush();
  assert.deepEqual(second.err, { code: "store-moved", error: GONE });
  assert.equal(countOf(w, "fileComments", "save"), 2, "no retry");
  assert.equal(countOf(w, "saveFile"), 0, "never re-routed to the viewer's own save");
});

test("a landed save that leaves nothing pending seeds nothing, as Edit over no changes does: Save follows the status again — the host for a tracked file or one with a sidecar, the viewer's own path once an untracked file's sidecar is gone", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  // tracked, one change: decided in the editor, the sidecar stays for its comment
  await openPanel(w, pending({}, [h1], [rec1]));
  w.editing = true;
  assert.deepEqual(w.tracked!.begin()!.records, [rec1]);
  const first = settle(w.tracked!.save("the typed text", [], { accepted: [H1_ACCEPT], rejected: [] }));
  await flush();
  saved(lastOf(w, "fileComments", "save"), status({ fileMtimeNs: NS(9), storeMtimeNs: NS(10) }));
  await flush(); await flush();
  assert.deepEqual(first.ok, { mtimeNs: NS(9), logged: true });
  stayedUp(w, "the typed text", NS(9));
  assert.equal(w.tracked!.routesSave(), true, "tracked, with a sidecar: the host, on the status's own fence");
  const second = settle(w.tracked!.save("the typed text, more", [], { accepted: [], rejected: [] }));
  await flush();
  const save2 = lastOf(w, "fileComments", "save");
  assert.deepEqual(save2.fence, { storeMtimeNs: NS(10), configMtimeNs: NS(3), fileMtimeNs: NS(9) }, "the status as it stands — which is the first save's reply");
  saved(save2, status({ fileMtimeNs: NS(11), storeMtimeNs: NS(12) }));
  await flush(); await flush();
  assert.deepEqual(second.ok, { mtimeNs: NS(11), logged: true });
  w.editing = false; w.setText(w.disk); w.close();
  // untracked, one change and no comment: decided in the editor, the host pruned the sidecar
  const w2 = world(); t.after(() => w2.close());
  await openPanel(w2, bare([h1], [rec1]));
  w2.editing = true;
  assert.deepEqual(w2.tracked!.begin()!.records, [rec1]);
  const only = settle(w2.tracked!.save("the typed text", [], { accepted: [H1_ACCEPT], rejected: [] }));
  await flush();
  saved(lastOf(w2, "fileComments", "save"), status({ trackedBy: null, store: null, storeMtimeNs: null, unsent: NONE, fileMtimeNs: NS(9) }));
  await flush(); await flush();
  assert.deepEqual(only.ok, { mtimeNs: NS(9), logged: true });
  stayedUp(w2, "the typed text", NS(9));
  assert.equal(w2.tracked!.routesSave(), false, "nothing in the editor, no sidecar, not tracked: the viewer's saveFile");
  assert.equal(w2.tracked!.begin(), null, "a new Edit has nothing to carry either");
});

// ── the host's logWarning on a save ─────────────────────────────────────────────────────────────────

test("a save reply carrying the host's logWarning: the resolved save carries it for the viewer, and the head says it in the host's words, where the Log lives; the row outlives the edit and a clean save retires it", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w, pending());
  w.editing = true; w.tracked!.begin();
  const out = settle(w.tracked!.save("the typed text", [rec2], { accepted: [H1_ACCEPT], rejected: [] }));
  await flush();
  saved(lastOf(w, "fileComments", "save"), pending({ fileMtimeNs: NS(9), storeMtimeNs: NS(10) }, [h2], [rec2]), { logged: false, logWarning: WARN });
  await flush(); await flush();
  assert.deepEqual(out.ok, { mtimeNs: NS(9), logged: false, logWarning: WARN }, "the viewer hears the warning with the save, as the fileSaved reply carries it");
  const row = aside.querySelector(".fc-sec-head .fc-err")!;
  assert.ok(row, "the head says so: the Log below lacks the entry this edit owed");
  assert.equal(row.childNodes[0].textContent, WARN);
  assert.ok(row.classes.includes("fc-err-warn"), "a warning, not a refusal: the save landed");
  assert.equal(row.querySelector('[data-act="fcreload"]'), null, "nothing a re-read would mend");
  // the edit ends: the row is about the Log, not the editor, and stays
  w.editing = false; w.viewMtime = NS(9); w.setText(w.disk);
  assert.equal(aside.querySelector(".fc-sec-head .fc-err")!.childNodes[0].textContent, WARN);
  // a later save whose append went through retires it
  w.editing = true; w.tracked!.begin();
  const again = settle(w.tracked!.save("the typed text, again", [rec2], { accepted: [], rejected: [] }));
  await flush();
  saved(lastOf(w, "fileComments", "save"), pending({ fileMtimeNs: NS(11), storeMtimeNs: NS(12) }, [h2], [rec2]));
  await flush(); await flush();
  assert.deepEqual(again.ok, { mtimeNs: NS(11), logged: true }, "no warning, no key: the seam's callers deep-equal the value");
  assert.equal(aside.querySelector(".fc-sec-head .fc-err"), null);
});

// ── a sidecar-only verb's reply that read a later file ──────────────────────────────────────────────

test("Resolve on a comment card while editing, answered after a session wrote the file: the head says the bytes moved from the reply's clocks, the poll (re-baselined by the reply) asks nothing more, and Cancel re-reads the bytes", async (t: TestContext) => {
  t.mock.timers.enable({ apis: ["setInterval"] });
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w, status());
  w.editing = true;
  assert.equal(w.tracked!.begin(), null, "no changes pending: the editor mounts as for any file, and the cards render in edit mode");
  // Resolve sits on the OPEN card; it moves no change, so it is offered while editing
  card(aside, passage.id)!.click();
  const res = act(card(aside, passage.id)!, "fcresolve")!;
  assert.ok(res, "Resolve is offered while editing");
  res.click(); await flush(); await flush();
  const m = lastOf(w, "fileComments", "resolve");
  assert.ok(m, "the request is out");
  assert.deepEqual(m.args, { commentId: passage.id, on: true });
  // the session rewrote the file during the round trip: the reply read the later file
  w.disk = DOC.replace("More text here.", "More text here, rewritten by the session."); w.diskMtime = NS(33);
  answer(w, status({ verb: "resolve", fileMtimeNs: NS(33), storeMtimeNs: NS(5), store: { v: 3, path: "docs/report.md", suggestions: [], comments: [{ ...passage, resolved: true }] } }), m);
  await flush(); await flush();
  const row = aside.querySelector(".fc-sec-head .fc-err")!;
  assert.ok(row, "the head says the bytes moved");
  assert.equal(row.childNodes[0].textContent, MOVED_UNDER_EDIT);
  assert.equal(w.reloads, 0, "never over the editor's buffer");
  // the reply re-baselined the poll: no later tick notices, so the row could have come from nowhere else
  const asks = countOf(w, "fileComments", "status");
  t.mock.timers.tick(2500); await flush(); await flush(); await flush();
  assert.equal(countOf(w, "fileComments", "status"), asks, "the poll asks nothing: its baseline is the reply's");
  // Cancel: the viewer repaints the bytes it loaded; the panel re-reads the file as it is now
  w.editing = false; w.setText(DOC);
  assert.equal(w.reloads, 1, "the first paint after the edit re-reads");
  assert.ok(w.code.textContent.includes("rewritten by the session"), "the read view shows the session's write");
  assert.equal(aside.querySelector(".fc-sec-head .fc-err"), null);
});

// ── the foot says it once ───────────────────────────────────────────────────────────────────────────

test("Accept all or Reject all while editing says where to decide once: the click's row takes the caption's place, its ✕ hands back to the caption, and the words name the route that needs no mouse", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside, DECIDE } = await openPanel(w, pending());
  w.editing = true; w.tracked!.begin();
  const foot = () => aside.querySelector(".fc-foot")!;
  const said = () => foot().querySelectorAll(".fc-decide-edit, .fc-err").filter((x) => x.childNodes[0]!.textContent === DECIDE).length;
  assert.equal(said(), 1, "before any click: the caption");
  assert.ok(foot().querySelector(".fc-decide-edit")); assert.equal(foot().querySelector(".fc-err"), null);
  act(aside, "fcacceptall")!.click(); await flush();
  assert.equal(said(), 1, "after Accept all: the row, and not the caption under it");
  assert.equal(foot().querySelector(".fc-decide-edit"), null, "the caption stands down while the row says the same");
  assert.equal(foot().querySelector(".fc-err")!.childNodes[0].textContent, DECIDE);
  assert.equal(countOf(w, "fileComments", "accept-all"), 0);
  foot().querySelector('[data-act="fcerrx"]')!.click();
  assert.equal(said(), 1, "dismissed: the caption is back, the row gone");
  assert.ok(foot().querySelector(".fc-decide-edit")); assert.equal(foot().querySelector(".fc-err"), null);
  act(aside, "fcrejectall")!.click(); await flush();
  assert.equal(said(), 1, "Reject all: the same");
  assert.equal(foot().querySelector(".fc-choice"), null, "no confirm to walk into");
  // the words: the mouse gestures for those who have one, and the route for those who do not (a tap or a keyboard
  // decides nothing in the editor, by design), which the plain sentence never said — Save or Cancel, then the cards
  assert.match(DECIDE, /^While you edit, decide in the editor: click a change to accept it, Alt-click \(Cmd-click on a Mac, Ctrl-click elsewhere\) to reject it\. /);
  assert.match(DECIDE, /To use Accept and Reject instead, Save or Cancel first: they work again once the editor is closed\.$/);
  for (const b of ["fcaccept", "fcreject", "fcacceptall", "fcrejectall"]) assert.equal(act(aside, b)!.title, DECIDE, b + " carries the same words");
  // the edit ends: neither row nor caption
  w.editing = false; w.setText(w.disk);
  assert.equal(said(), 0);
});

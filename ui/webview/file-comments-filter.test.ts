// The Comments panel's filter (the filter follow-on to plans/file-review.md, 2026-09-07): All · Comments · Changes in
// the panel header, under the Track changes and Show changes inline row — which cards the list shows and which marks the
// text wears, kept across opens and pages through the shared settings store — and the kind cue every card head wears.
// Driven AS A PANEL over the inline-toggle suite's DOM stand-in (a Raw body built to the viewer's shape; its settings store
// is the stub localStorage every panel suite installs):
//   • the default: All, the three buttons offered once the file has a comment or a change and never before, their counts
//     the action-row label's; nothing written to the store until a pick;
//   • Comments: every comment card on its own — passage, whole-file, region, and a comment on a pending change with the
//     change's words and an "on a change" tag — no change card, fold or foot; no change mark in the text, the highlights kept;
//   • Changes: the change cards alone, each with the comments made on it once open; no comment card or Resolved fold; the
//     change marks kept, no highlight; with Show changes inline off on top, the cards and no mark;
//   • All: today's list; the keyed expand state untouched by any pick; Send to session unfiltered;
//   • remembered: the store's commentsFilter, read when the next panel opens and written on each pick; a foreign value
//     reads as All; a pick elsewhere (the settings signal) re-renders the live panel;
//   • the arrow keys move along the group and choose, wrapping; Home and End;
//   • the kind cue: Comment / Change / Region before the chip, and the card's data-cue for the sheets' left edge.
// What a stand-in cannot show is pinned at source: the delegate action, the header's order, the paint guards, the store's
// key and default, the second listener, the sheets' rules (byte-equal in both). Synthetic fixtures only: the notes-api
// world, placeholder ids.
import { test, type TestContext } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import type { FileViewActionCtx } from "./file-view";
import { type Status, type Hunk, type StoreComment, cardCounts, filterOffered, actionLabel } from "./file-comments-model";

const web = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const SRC = web("file-comments.ts");
const SETTINGS = web("settings.ts");
const CHAT_CSS = web("styles.css");
const FEED_CSS = web("feed.css");

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
    post: (m) => { w.posted.push(m); }, ensureEditingAllowed: async () => true, setEditBlocked: () => { /* inert */ }, editing: () => false, setTrackedEdit: () => { /* inert */ },
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

// ── helpers and fixtures of this suite ─────────────────────────────────────────────────────────────
const SETTINGS_KEY = "romp:settings";
const stored = (): Record<string, unknown> | null => { const raw = store.get(SETTINGS_KEY); return raw ? JSON.parse(raw) as Record<string, unknown> : null; };
const filterRow = (aside: El): El | null => aside.querySelector(".fc-head .fc-filter");
const option = (aside: El, key: string): El => { const b = aside.querySelector('[data-act="fcfilter"][data-key="' + key + '"]'); assert.ok(b, "the " + key + " option"); return b!; };
const chosen = (aside: El): string[] => aside.querySelectorAll('[data-act="fcfilter"]').filter((b) => b.dataset.on === "1").map((b) => b.dataset.key);
const changeCards = (aside: El): El[] => aside.querySelectorAll(".fc-card.fc-change");
const commentCards = (aside: El): El[] => aside.querySelectorAll(".fc-card").filter((c) => !c.classes.includes("fc-change"));
const highlights = (w: World): El[] => w.body.querySelectorAll(".fc-hl");
const pick = async (aside: El, key: string): Promise<void> => { option(aside, key).click(); await flush(); };
const kindOf = (c: El): string => { const k = c.querySelector(".fc-card-head .fc-kind"); return k ? k.textContent : ""; };   // the head's own cue (a hosted comment wears none)
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

// ── the default ────────────────────────────────────────────────────────────────────────────────────

test("the default: All, the three buttons on their own row under the toggles, offered once the file has a comment or a change, their counts the action-row label's; nothing is written to the store until a pick; the list and the marks are today's", async (t: TestContext) => {
  store.delete(SETTINGS_KEY);
  const w = world(); t.after(() => w.close());
  const { aside, button } = await openPanel(w, full());
  const rows = aside.querySelector(".fc-head")!.childNodes.filter((n) => n instanceof El && (n as El).classes.includes("fc-row")) as El[];
  assert.deepEqual(rows.map((r) => r.classes.join(" ")), ["fc-row", "fc-row fc-filter"], "the toggles' row, then the filter's row");
  assert.deepEqual(rows[0].childNodes.map((c) => (c as El).dataset.act), ["fctrack", "fcinline", "fcfile"], "the first row is as it was");
  const seg = filterRow(aside)!;
  assert.equal(seg.getAttribute("role"), "group"); assert.equal(seg.getAttribute("aria-label"), "Show");
  const btns = seg.childNodes as El[];
  assert.deepEqual(btns.map((b) => [b.tagName, b.dataset.act, b.dataset.key, b.textContent]), [["BUTTON", "fcfilter", "all", "All"], ["BUTTON", "fcfilter", "comments", "Comments 4"], ["BUTTON", "fcfilter", "changes", "Changes 5"]]);
  for (const b of btns) assert.ok(b.classes.includes("fileview-btn") && b.classes.includes("fc-toggle"), "the toggles' dress: the chosen one is the accent fill");
  assert.deepEqual(btns.map((b) => [b.dataset.on, b.getAttribute("aria-pressed")]), [["1", "true"], ["0", "false"], ["0", "false"]], "All is chosen");
  assert.equal(button.textContent, "Comments · 4 · 5 changes", "the label…");
  assert.deepEqual(cardCounts(full()), { comments: 4, changes: 5 }, "…and the counts are one source");
  assert.equal(stored(), null, "the default is the store's absence");
  // today's list: the changes first (four groups, the fourth folded), the foot, then the comments and the Resolved fold
  assert.deepEqual(changeCards(aside).map((c) => c.dataset.id), ["chg:h1", "chg:h2", "chg:h3", "chg:h4"]);
  assert.ok(act(aside, "fcmore"), "the fold row"); assert.ok(aside.querySelector(".fc-foot"), "Accept all · Reject all");
  assert.deepEqual(commentCards(aside).map((c) => c.dataset.id), [passage.id, whole.id, region.id], "the comment on h1 rides its change card");
  assert.ok(act(aside, "fcresolved"), "the Resolved fold");
  assert.equal(marksOf(w).length, 6, "the change marks: a point and a tint for the substitution, one each for the rest");
  assert.equal(highlights(w).length, 2, "the passage comment's and the hosted comment's highlights");
  w.close();
  // nothing to filter: no control, whatever the store says
  store.set(SETTINGS_KEY, JSON.stringify({ commentsFilter: "changes" }));
  const w2 = world(); t.after(() => w2.close());
  const { aside: a2 } = await openPanel(w2, status({ hunks: [], store: { v: 3, path: "docs/report.md", suggestions: [], comments: [] } }));
  assert.equal(filterRow(a2), null, "no comment and no change: no control");
  assert.match(a2.querySelector(".fc-empty")!.textContent, /^No comments yet\./, "…and the kept choice governs nothing: the plain empty state");
  assert.equal(filterOffered(status({ hunks: [], store: { v: 3, path: "docs/report.md", suggestions: [], comments: [] } })), false);
  assert.equal(filterOffered(status({ hunks: [], store: { v: 3, path: "docs/report.md", suggestions: [], comments: [done] } })), true, "a resolved comment is a card to filter");
  assert.equal(filterOffered(status({ hunks: [], store: { v: 3, path: "docs/report.md", suggestions: [], comments: [], detached: [{ id: "d1", author: "api", ts: T0, kind: "del", from: 0, oldText: "x", newText: "" }] } })), true, "a detached change is one too");
  assert.equal(filterOffered(null), false); assert.equal(filterOffered(status({ store: null })), false);
  store.delete(SETTINGS_KEY);
});

test("the counts are the label's, case by case: open comments of every kind, pending changes; resolved and detached count for nothing here", () => {
  const s = (comments: StoreComment[], hunks: Hunk[], detached?: unknown[]) => status({ store: { v: 3, path: "docs/report.md", suggestions: SUGG, comments, ...(detached ? { detached } : {}) }, hunks });
  assert.deepEqual(cardCounts(null), { comments: 0, changes: 0 });
  assert.deepEqual(cardCounts(status({ store: null })), { comments: 0, changes: 0 });
  assert.deepEqual(cardCounts(s([], [])), { comments: 0, changes: 0 });
  assert.deepEqual(cardCounts(s([passage, hosted, whole, region, done], FIVE)), { comments: 4, changes: 5 }, "a comment on a change counts as a comment; the resolved one does not");
  assert.equal(actionLabel(s([passage, hosted, whole, region, done], FIVE)), "Comments · 4 · 5 changes");
  assert.deepEqual(cardCounts(s([done], [], [{ id: "d1", author: "api", ts: T0, kind: "del", from: 0, oldText: "x", newText: "" }])), { comments: 0, changes: 0 }, "detached changes are the label's own clause");
  assert.equal(actionLabel(s([done], [], [{ id: "d1", author: "api", ts: T0, kind: "del", from: 0, oldText: "x", newText: "" }])), "Comments · 0 · 1 detached change");
});

// ── the three states ───────────────────────────────────────────────────────────────────────────────

test("Comments: every comment card on its own — the comment on the pending change too, with the change's words and an 'on a change' tag — no change card, fold or foot; no change mark in the text while the highlights stay; the store written, no status ask", async (t: TestContext) => {
  store.delete(SETTINGS_KEY);
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w, full());
  const asks = w.posted.length;
  await pick(aside, "comments");
  assert.equal(w.posted.length, asks, "no message to the kernel: the cards and the hunks are already here");
  assert.deepEqual(chosen(aside), ["comments"]);
  assert.equal(stored()!.commentsFilter, "comments", "the pick is written to the shared store");
  assert.deepEqual(commentCards(aside).map((c) => c.dataset.id), [passage.id, whole.id, region.id, hosted.id], "the four open comments, oldest first (the bound one is the newest), the bound one among them");
  assert.deepEqual(changeCards(aside), [], "no change card");
  assert.equal(aside.querySelector(".fc-group"), null, "no paragraph group");
  assert.equal(act(aside, "fcmore"), null, "no fold row"); assert.equal(aside.querySelector(".fc-foot"), null, "no Accept all · Reject all");
  assert.equal(act(aside, "fcacceptall"), null); assert.equal(act(aside, "fcrejectall"), null);
  assert.ok(act(aside, "fcresolved"), "the Resolved fold stays: a resolved comment is a comment");
  const bound = card(aside, hosted.id)!;
  assert.equal(bound.querySelector(".fc-ref")!.textContent, "reduced → cut", "the change's words are the reference: the card keeps its change context");
  assert.ok(tags(bound).includes("on a change"), "…and says the change is behind All or Changes");
  assert.equal(kindOf(bound), "Comment");
  assert.equal(marksOf(w).length, 0, "no change mark in the body");
  assert.equal(highlights(w).length, 2, "the highlights are not governed by Comments");
  assert.equal(option(aside, "changes").textContent, "Changes 5", "the hidden kind keeps its count on the button");
  assert.equal(option(aside, "comments").textContent, "Comments 4");
  // a highlight click opens the comment's OWN card here: no change card hosts it
  const hl = highlights(w).find((m) => m.dataset.id === hosted.id)!;
  hl.click();
  assert.ok(card(aside, hosted.id)!.classes.includes("open"), "the bound comment's own card opens");
  assert.equal(card(aside, "chg:h1"), null);
  store.delete(SETTINGS_KEY);
});

test("Changes: the change cards alone, each with the comments made on it once open; no comment card and no Resolved fold; the change marks stay and the highlights go; with Show changes inline off on top, the cards and no mark at all", async (t: TestContext) => {
  store.delete(SETTINGS_KEY);
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w, full());
  const asks = w.posted.length;
  await pick(aside, "changes");
  assert.equal(w.posted.length, asks);
  assert.deepEqual(chosen(aside), ["changes"]);
  assert.equal(stored()!.commentsFilter, "changes");
  assert.deepEqual(changeCards(aside).map((c) => c.dataset.id), ["chg:h1", "chg:h2", "chg:h3", "chg:h4"], "the changes as under All");
  assert.ok(act(aside, "fcmore"), "the fold row"); assert.ok(aside.querySelector(".fc-foot"), "the foot");
  assert.deepEqual(commentCards(aside), [], "no comment card");
  assert.equal(act(aside, "fcresolved"), null, "no Resolved fold");
  assert.ok(tags(card(aside, "chg:h1")!).includes("1"), "the closed change card counts its comment");
  card(aside, "chg:h1")!.querySelector(".fc-card-head")!.click();
  const hostedBox = aside.querySelector('.fc-hosted[data-id="' + hosted.id + '"]');
  assert.ok(hostedBox, "the comment on the change is on the change's card");
  assert.equal(hostedBox!.querySelector(".fc-body")!.textContent, hosted.body);
  assert.ok(act(hostedBox!, "fcreply", hosted.id) && act(hostedBox!, "fcresolve", hosted.id), "with its Reply and Resolve");
  assert.equal(marksOf(w).length, 6, "the change marks stay");
  assert.equal(highlights(w).length, 0, "no comment highlight");
  assert.ok(w.body.textContent.includes("shipping the cache in v1.2"), "the text reads as before, unmarked");
  // the inline toggle applies on top
  act(aside, "fcinline")!.click(); await flush();
  assert.equal(marksOf(w).length, 0, "no mark of either kind");
  assert.equal(highlights(w).length, 0);
  assert.deepEqual(changeCards(aside).map((c) => c.dataset.id), ["chg:h1", "chg:h2", "chg:h3", "chg:h4"], "the change cards stay");
  for (const c of changeCards(aside)) assert.ok(act(c, "fcreveal", c.dataset.id), c.dataset.id + " offers Reveal, as with the marks off under All");
  assert.equal(stored()!.changesInline, false); assert.equal(stored()!.commentsFilter, "changes", "two settings, both kept");
  act(aside, "fcinline")!.click(); await flush();
  assert.equal(marksOf(w).length, 6); assert.equal(highlights(w).length, 0, "the marks are back; the filter still hides the highlights");
  store.delete(SETTINGS_KEY);
});

test("All brings today's list and both kinds of mark back; the keyed expand state is untouched by any pick; a change card opened under Changes and a comment card opened under All are still open when they show again", async (t: TestContext) => {
  store.delete(SETTINGS_KEY);
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w, full());
  card(aside, passage.id)!.querySelector(".fc-card-head")!.click();
  assert.ok(card(aside, passage.id)!.classes.includes("open"));
  await pick(aside, "changes");
  assert.equal(card(aside, passage.id), null, "hidden");
  card(aside, "chg:h2")!.querySelector(".fc-card-head")!.click();
  assert.ok(card(aside, "chg:h2")!.classes.includes("open"));
  await pick(aside, "comments");
  assert.equal(card(aside, "chg:h2"), null);
  assert.ok(card(aside, passage.id)!.classes.includes("open"), "the comment card is open again: the state survived the pick that hid it");
  await pick(aside, "all");
  assert.deepEqual(chosen(aside), ["all"]);
  assert.equal(stored()!.commentsFilter, "all");
  assert.ok(card(aside, passage.id)!.classes.includes("open")); assert.ok(card(aside, "chg:h2")!.classes.includes("open"), "both open, as they were left");
  assert.deepEqual(changeCards(aside).map((c) => c.dataset.id), ["chg:h1", "chg:h2", "chg:h3", "chg:h4"]);
  assert.deepEqual(commentCards(aside).map((c) => c.dataset.id), [passage.id, whole.id, region.id]);
  assert.ok(act(aside, "fcresolved") && act(aside, "fcmore") && aside.querySelector(".fc-foot"));
  assert.equal(marksOf(w).length, 6); assert.equal(highlights(w).length, 2);
  // the option already chosen changes nothing
  const before = marksOf(w);
  await pick(aside, "all");
  assert.deepEqual(marksOf(w), before, "no new information, no repaint");
  store.delete(SETTINGS_KEY);
});

test("Changes with no change pending, and comments to show: the line says where they are; Comments with no comment: the plain empty state", async (t: TestContext) => {
  store.set(SETTINGS_KEY, JSON.stringify({ commentsFilter: "changes" }));
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w, status({ hunks: [], store: { v: 3, path: "docs/report.md", suggestions: [], comments: [passage] } }));
  assert.ok(filterRow(aside), "a comment: the control is offered");
  assert.deepEqual(chosen(aside), ["changes"]);
  assert.equal(aside.querySelector(".fc-empty")!.textContent, "No changes are pending. All or Comments above shows the comments.");
  assert.deepEqual(commentCards(aside), []);
  await pick(aside, "comments");
  assert.deepEqual(commentCards(aside).map((c) => c.dataset.id), [passage.id]);
  w.close();
  store.set(SETTINGS_KEY, JSON.stringify({ commentsFilter: "comments" }));
  const w2 = world(); t.after(() => w2.close());
  const { aside: a2 } = await openPanel(w2, status({ hunks: [h1, h3], store: { v: 3, path: "docs/report.md", suggestions: SUGG, comments: [] } }));
  assert.match(a2.querySelector(".fc-empty")!.textContent, /^No comments yet\. Select a passage and press Comment, or comment on this file\.$/);
  assert.equal(option(a2, "changes").textContent, "Changes 2", "the changes are a click away, counted");
  store.delete(SETTINGS_KEY);
});

// ── remembered, and a pick elsewhere ───────────────────────────────────────────────────────────────

test("remembered: the store's commentsFilter opens the next panel filtered, header and list and marks agreeing; a foreign value reads as All; the store's other keys are kept", async (t: TestContext) => {
  store.set(SETTINGS_KEY, JSON.stringify({ compact: true, commentsFilter: "comments" }));
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w, full());
  assert.deepEqual(chosen(aside), ["comments"]);
  assert.deepEqual(changeCards(aside), []); assert.equal(commentCards(aside).length, 4);
  assert.equal(marksOf(w).length, 0); assert.equal(highlights(w).length, 2);
  await pick(aside, "all");
  assert.equal(stored()!.compact, true, "the store's other keys are kept"); assert.equal(stored()!.commentsFilter, "all");
  w.close();
  store.set(SETTINGS_KEY, JSON.stringify({ commentsFilter: "everything" }));
  const w2 = world(); t.after(() => w2.close());
  const { aside: a2 } = await openPanel(w2, full());
  assert.deepEqual(chosen(a2), ["all"], "a value the panel does not know costs the preference, never the list");
  assert.equal(changeCards(a2).length, 4);
  store.delete(SETTINGS_KEY);
});

test("a pick elsewhere — the settings signal another pane or the gear raises, or another tab's storage event — re-renders the live panel: header, list and marks; a signal that changes nothing repaints nothing", async (t: TestContext) => {
  store.delete(SETTINGS_KEY);
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w, full());
  const asks = w.posted.length;
  store.set(SETTINGS_KEY, JSON.stringify({ commentsFilter: "changes" }));
  win.dispatchEvent(new Event("romp:settings"));
  await flush();
  assert.deepEqual(chosen(aside), ["changes"], "this header");
  assert.deepEqual(commentCards(aside), []); assert.equal(changeCards(aside).length, 4);
  assert.equal(highlights(w).length, 0); assert.equal(marksOf(w).length, 6);
  assert.equal(w.posted.length, asks, "no status ask for it");
  store.set(SETTINGS_KEY, JSON.stringify({ commentsFilter: "comments" }));
  const ev = new Event("storage"); (ev as unknown as { key: string }).key = SETTINGS_KEY;
  win.dispatchEvent(ev);
  await flush();
  assert.deepEqual(chosen(aside), ["comments"]);
  assert.equal(marksOf(w).length, 0); assert.equal(highlights(w).length, 2); assert.equal(changeCards(aside).length, 0);
  const before = highlights(w);
  win.dispatchEvent(new Event("romp:settings"));
  await flush();
  assert.deepEqual(highlights(w), before, "no new information, no repaint");
  store.delete(SETTINGS_KEY);
});

// ── the keyboard ───────────────────────────────────────────────────────────────────────────────────

test("the arrow keys move along the group and choose: right or down to the next option, left or up to the previous, wrapping at the ends; Home and End; the keyboard lands on the chosen button after the re-render", async (t: TestContext) => {
  store.delete(SETTINGS_KEY);
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w, full());
  option(aside, "all").focus();
  assert.equal(doc.activeElement, option(aside, "all"));
  const press = (key: string): Ev => { const ev = new Ev("keydown", { key }); dispatch(doc.activeElement!, ev); return ev; };
  let ev = press("ArrowRight"); await flush();
  assert.ok(ev.defaultPrevented, "the arrow is the group's");
  assert.deepEqual(chosen(aside), ["comments"]); assert.equal(doc.activeElement, option(aside, "comments"), "chosen and focused");
  assert.equal(stored()!.commentsFilter, "comments"); assert.equal(changeCards(aside).length, 0);
  press("ArrowDown"); await flush();
  assert.deepEqual(chosen(aside), ["changes"]); assert.equal(doc.activeElement, option(aside, "changes"));
  press("ArrowRight"); await flush();
  assert.deepEqual(chosen(aside), ["all"], "wraps"); assert.equal(doc.activeElement, option(aside, "all"));
  press("ArrowLeft"); await flush();
  assert.deepEqual(chosen(aside), ["changes"], "wraps the other way"); assert.equal(doc.activeElement, option(aside, "changes"));
  press("ArrowUp"); await flush();
  assert.deepEqual(chosen(aside), ["comments"]);
  press("Home"); await flush();
  assert.deepEqual(chosen(aside), ["all"]); assert.equal(doc.activeElement, option(aside, "all"));
  press("End"); await flush();
  assert.deepEqual(chosen(aside), ["changes"]); assert.equal(doc.activeElement, option(aside, "changes"));
  ev = press("Enter");
  assert.equal(ev.defaultPrevented, false, "other keys are the button's own");
  // an arrow on any other control is not the group's
  const track = act(aside, "fctrack")!; track.focus();
  ev = press("ArrowRight"); await flush();
  assert.equal(ev.defaultPrevented, false); assert.deepEqual(chosen(aside), ["changes"]);
  store.delete(SETTINGS_KEY);
});

// ── Send to session ────────────────────────────────────────────────────────────────────────────────

test("Send to session is not filtered: under Comments and under Changes the button's count, the confirm's list and its accept checkbox are what they are under All", async (t: TestContext) => {
  store.delete(SETTINGS_KEY);
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w, full());
  const read = () => {
    act(aside, "fcsend")!.click();
    const out = { button: act(aside, "fcsend")!.textContent, items: texts(aside.querySelectorAll(".fc-confirm .fc-list li")), opts: texts(aside.querySelectorAll(".fc-confirm .fc-opt")) };
    act(aside, "fcsendcancel")!.click();
    return out;
  };
  const all = read();
  assert.equal(all.button, "Send to session (4)");
  assert.equal(all.items.length, 5, "the four comments and the decisions line");
  assert.equal(all.items[4], "5 accepted, 0 rejected", "the accept checkbox folds the pending changes in");
  assert.ok(all.opts.some((o) => o === "accept the 5 pending changes"));
  await pick(aside, "comments");
  assert.deepEqual(read(), all, "Comments: the same send");
  await pick(aside, "changes");
  assert.deepEqual(read(), all, "Changes: the same send");
  store.delete(SETTINGS_KEY);
});

// ── the kind cue ───────────────────────────────────────────────────────────────────────────────────

test("the kind cue: every card head names its kind before the author's chip — Comment, Change, Region — and the card carries data-cue for the sheets' left edge; a comment on a decided change is a Comment", async (t: TestContext) => {
  store.delete(SETTINGS_KEY);
  const w = world(); t.after(() => w.close());
  const decided: StoreComment = { ...hosted, id: T0 + 7000 + "-9", suggestionId: "h9" };   // bound to a change the log has accepted
  const log = [{ ts: "2026-09-07T10:00:00.000Z", kind: "accept", author: "you", changes: [{ id: "h9", oldText: "slow", newText: "fast" }] }];
  const { aside } = await openPanel(w, full({ store: { v: 3, path: "docs/report.md", suggestions: SUGG, comments: [...ALL_COMMENTS, decided] }, log }));
  const headOf = (c: El) => c.querySelector(".fc-card-head")!.childNodes.map((n) => (n as El).classes[0]);
  for (const c of changeCards(aside)) {
    assert.deepEqual(headOf(c).slice(0, 2), ["fc-kind", "fc-chip"], c.dataset.id + ": the cue, then the chip");
    assert.equal(kindOf(c), "Change"); assert.equal(c.dataset.cue, "change");
    assert.equal(c.querySelector(".fc-kind")!.title, "A change the session made to the file, for you to accept or reject");
  }
  const byId = (id: string) => card(aside, id)!;
  assert.deepEqual(headOf(byId(passage.id)).slice(0, 2), ["fc-kind", "fc-chip"]);
  assert.equal(kindOf(byId(passage.id)), "Comment"); assert.equal(byId(passage.id).dataset.cue, "comment"); assert.equal(byId(passage.id).querySelector(".fc-kind")!.title, "A comment on a passage");
  assert.equal(kindOf(byId(whole.id)), "Comment"); assert.equal(byId(whole.id).querySelector(".fc-kind")!.title, "A comment on the file as a whole");
  assert.equal(kindOf(byId(region.id)), "Region"); assert.equal(byId(region.id).dataset.cue, "comment", "a region is a comment: the comment's edge");
  assert.equal(byId(region.id).querySelector(".fc-kind")!.title, "A comment on a region of the picture");
  assert.equal(kindOf(byId(decided.id)), "Comment"); assert.equal(byId(decided.id).querySelector(".fc-kind")!.title, "A comment on a change");
  assert.ok(tags(byId(decided.id)).includes("accepted") && !tags(byId(decided.id)).includes("on a change"), "decided: the decision tag, not the pending one");
  act(aside, "fcresolved")!.click();
  assert.equal(kindOf(byId(done.id)), "Comment"); assert.equal(byId(done.id).dataset.cue, "comment");
  // the hosted comment on a change card wears no cue of its own: it is part of the change's card
  card(aside, "chg:h1")!.querySelector(".fc-card-head")!.click();
  assert.equal(aside.querySelector('.fc-hosted[data-id="' + hosted.id + '"] .fc-kind'), null);
  store.delete(SETTINGS_KEY);
});

// ── a reply's box when the filter hides its card ───────────────────────────────────────────────────

test("a reply being written on a comment card that Changes hides: the box returns to the slot with a line saying so, and Cancel hands the keyboard to All; a reply on a comment on a change follows the comment between its own card and the change's", async (t: TestContext) => {
  store.delete(SETTINGS_KEY);
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w, full());
  const fc = await import("./file-comments");
  void fc;
  card(aside, passage.id)!.querySelector(".fc-card-head")!.click();
  act(aside, "fcreply", passage.id)!.click();
  const box = aside.querySelector(".fc-composer")!;
  assert.equal(box.parentNode, card(aside, passage.id), "the box stands in the card");
  await pick(aside, "changes");
  const slotBox = aside.querySelector(".fc-composer")!;
  assert.equal(slotBox.parentNode!.classes.includes("fc-panel"), true, "the card is hidden: the box is back in the panel's slot");
  assert.ok(aside.textContent.includes("The comment's card is hidden while Changes is chosen above (All or Comments shows it); the reply still goes to it."));
  doc.activeElement = slotBox.querySelector("textarea") as El;   // the keyboard in the box (the stand-in's focus() takes buttons and inputs only)
  act(slotBox, "fccancel")!.click();
  assert.equal(doc.activeElement, option(aside, "all"), "Cancel: the keyboard goes to the row that brings the card back");
  // a reply on the comment bound to h1: on the change card under All and Changes, on its own card under Comments
  card(aside, "chg:h1")!.querySelector(".fc-card-head")!.click();
  act(aside, "fcreply", hosted.id)!.click();
  assert.equal(aside.querySelector(".fc-composer")!.parentNode!.dataset.id, hosted.id, "in the hosted comment's box on the change card");
  assert.ok(aside.querySelector(".fc-composer")!.parentNode!.classes.includes("fc-hosted"));
  await pick(aside, "comments");
  assert.equal(aside.querySelector(".fc-composer")!.parentNode, card(aside, hosted.id), "on the comment's own card");
  assert.ok(card(aside, hosted.id)!.classes.includes("open"));
  await pick(aside, "all");
  assert.ok(aside.querySelector(".fc-composer")!.parentNode!.classes.includes("fc-hosted"), "back on the change's card");
  assert.ok(card(aside, "chg:h1")!.classes.includes("open"), "which stays open for it");
  store.delete(SETTINGS_KEY);
});

// ── source pins ────────────────────────────────────────────────────────────────────────────────────

test("pins: the delegate action, the header's order, the paint guards, the store's key and default, the second listener, the keys", () => {
  assert.match(SRC, /fcfilter: \(x\) => this\.setFilter\(x\.dataset\.key as CommentsFilter\),/, "the filter is one of the panel's own delegated actions (click-safe through the one root)");
  assert.match(SRC, /private setFilter\(f: CommentsFilter\): void \{\n\s+if \(f === this\.filter \|\| !FILTERS\.includes\(f\)\) return;\n\s+this\.filter = f;\n\s+saveSettings\(\{ commentsFilter: f \}\);\n\s+this\.paintAll\(\);\n\s+\}/, "pick, write the store, repaint — no request; the chosen option changes nothing");
  assert.match(SRC, /activeFilter\(\): CommentsFilter \{\n\s+return filterOffered\(this\.status\) \? this\.filter : "all";/, "the kept choice governs only while there is a card to filter");
  const head = SRC.slice(SRC.indexOf("private renderHead("), SRC.indexOf("private renderComposer("));
  const pos = (s: string) => { const i = head.indexOf(s); assert.ok(i >= 0, s); return i; };
  assert.ok(pos('row.appendChild(btn("Comment on this file", "fcfile"));\n    head.appendChild(row);') < pos("if (filterOffered(s)) {"), "the filter's row comes after the toggles' row");
  assert.ok(pos('const seg = el("div", "fc-row fc-filter");') < pos("head.appendChild(seg);") && pos("head.appendChild(seg);") < pos("if (this.trackChoice && s) {"), "…and before the track-scope rows");
  assert.match(head, /\["all", "All", [^\]]+\],\n\s+\["comments", "Comments " \+ n\.comments, [^\]]+\],\n\s+\["changes", "Changes " \+ n\.changes, [^\]]+\],/, "All · Comments N · Changes M, in that order, counted from cardCounts");
  assert.match(head, /const n = cardCounts\(s\);/);
  assert.match(head, /b\.dataset\.on = this\.filter === key \? "1" : "0";\n\s+b\.setAttribute\("aria-pressed", this\.filter === key \? "true" : "false"\);/, "the toggles' state, per option");
  assert.match(SRC, /filter: CommentsFilter = loadSettings\(\)\.commentsFilter;/, "read from the shared store when the panel is made");
  assert.match(SRC, /if \(!this\.inline\) return;[^\n]*\n\s+if \(this\.activeFilter\(\) === "comments"\) return;/, "Comments: the change painters are not called, after the inline gate");
  assert.match(SRC, /for \(const card of this\.activeFilter\(\) === "changes" \? \[\] : this\.cards\(\)\) \{\n\s+if \(card\.resolved \|\| !card\.anchor\) continue;/, "Changes: no comment highlight is painted");
  assert.match(SRC, /const hideRegions = this\.activeFilter\(\) === "changes";[\s\S]*?if \(card\.resolved\) continue;\n\s+if \(hideRegions\) continue;/, "Changes: no region rectangle either, after the crop is kept");
  assert.match(SRC, /const cards = filter === "changes" \? \[\] : this\.cards\(\)\.filter\(\(c\) => filter === "comments" \|\| c\.hunk === null\);/, "the list: no comment card under Changes; every comment card, bound or not, under Comments");
  assert.match(SRC, /const view = filter === "comments" \? \{ cards: \[\], groups: \[\], shown: \[\], hidden: \[\], hiddenChanges: 0 \} : this\.changeView\(\);/, "no change card, group or fold under Comments (the foot hangs off view.cards)");
  assert.match(SRC, /return c && c\.hunk && this\.activeFilter\(\) !== "comments" \? "chg:" \+ c\.hunk\.id : commentId;/, "a bound comment's card is its own under Comments");
  assert.match(SRC, /onExternalSettingsChange\(\(s\) => \{ if \(live && live\.filter !== s\.commentsFilter\) \{ live\.filter = s\.commentsFilter; live\.paintAll\(\); \} \}\);/, "a pick elsewhere reaches the live panel");
  assert.match(SRC, /const FILTERS: CommentsFilter\[\] = \["all", "comments", "changes"\];\nconst FILTER_KEYS = new Set\(\["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "Home", "End"\]\);/);
  assert.match(SRC, /if \(!t \|\| !t\.dataset \|\| t\.dataset\.act !== "fcfilter" \|\| !this\.owns\(t\)\) return;/, "the arrows act for the panel's own buttons only");
  // the kind cue, in both builders
  assert.match(SRC, /const kind = el\("span", "fc-kind", c\.kind === "region" \? "Region" : "Comment"\);[\s\S]{0,400}head\.appendChild\(kind\);\n\s+head\.appendChild\(this\.chip\(c\.author, c\.authorId\)\);/, "a comment card: the cue before the chip");
  assert.match(SRC, /const kind = el\("span", "fc-kind", "Change"\);[^\n]*\n\s+kind\.title = [^\n]+\n\s+head\.appendChild\(kind\);\n\s+head\.appendChild\(this\.chip\(c\.author, c\.authorId\)\);/, "a change card: the same");
  assert.match(SRC, /card\.dataset\.cue = "comment";/); assert.match(SRC, /card\.dataset\.cue = "change";/);
  // the store
  assert.match(SETTINGS, /^\s+commentsFilter: CommentsFilter;/m, "a field of the shared settings, like changesInline");
  assert.match(SETTINGS, /export type CommentsFilter = "all" \| "comments" \| "changes";\nexport function commentsFilter\(v: unknown\): CommentsFilter \{\n\s+return v === "comments" \|\| v === "changes" \? v : "all";/, "the normalizer: two opt-ins, all else the default");
  assert.match(SETTINGS, /s\.commentsFilter = commentsFilter\(s\.commentsFilter\);/, "applied on load");
  const DEFAULT_ALL = /export const DEFAULT_SETTINGS: RompSettings = \{[^\n]*\bcommentsFilter: "all"[,\s}]/;
  assert.match(SETTINGS, DEFAULT_ALL, '"all" by default');
  const literal = SETTINGS.match(/export const DEFAULT_SETTINGS: RompSettings = \{[^\n]*\};/)!;
  assert.match(literal[0].replace('commentsFilter: "all"', 'commentsFilter: "all", later: false'), DEFAULT_ALL, "read by value, so a setting appended after it keeps the pin green");
  assert.doesNotMatch(literal[0].replace('commentsFilter: "all"', 'commentsFilter: "changes"'), DEFAULT_ALL);
});

test("pins: the sheets carry the cue's rules — the note's dress for the word, the accent edge for a comment, the muted edge for a change, the detached edge left alone — the same bytes in styles.css and feed.css, tokens only", () => {
  const rules = [
    "\n.fc-kind { flex: 0 0 auto; color: var(--dim); font-size: 0.86em; }\n",
    '\n.fc-card[data-cue="comment"]:not(.fc-card-detached) { border-left: 3px solid var(--accent); }\n',
    '\n.fc-card[data-cue="change"]:not(.fc-card-detached) { border-left: 3px solid var(--text-muted); }\n',
  ];
  for (const [name, css] of [["styles.css", CHAT_CSS], ["feed.css", FEED_CSS]] as const) {
    const a = css.indexOf("/* ── file comments panel (plans/file-review.md Slice 1; file-comments.ts)"), b = css.indexOf("/* ── end file comments panel ── */");
    const block = css.slice(a, b);
    for (const r of rules) assert.ok(block.includes(r), name + " carries " + r.trim());
    assert.ok(block.indexOf(rules[1]) < block.indexOf("\n.fc-card-detached {"), name + ": the cue rules stand before the detached rule");
    assert.ok(block.indexOf("\n.fc-card:hover {") < block.indexOf(rules[2]), name + ": the change edge comes after the hover rule, so it holds under it");
    assert.match(block, /^\s+--text-muted|var\(--text-muted\)/m);
    assert.ok(css.includes("--text-muted:"), name + " defines the token the change edge reads");
  }
});

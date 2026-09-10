// Reveal's title with Show changes inline off (the inline-display follow-on to plans/file-review.md, 2026-09-07; the
// review's finding): with the marks off every change card offers Reveal, as the plan requires, and paintChanges paints
// no mark in Raw either — so a title that promised "Show the change in the Raw view" named a mark the click would not
// show. Off, the title promises what Reveal does — opens the Raw view at the change, the guide's words — and says why
// nothing is marked there; on, the Slice 2 title stands. Driven AS A PANEL over the inline-toggle suite's DOM stand-in:
//   • Rendered, marks on → off → on: the title of every offered Reveal, its line number, the click (Raw, the change's start);
//   • Raw with a store that says off: the same title on every card, and the flip back;
//   • the bytes in flux with the marks off: no line number, as the on-state title has none either.
// Synthetic fixtures only: the notes-api world, placeholder ids.
import { test, type TestContext } from "node:test";
import * as assert from "node:assert/strict";
import { inspect } from "node:util";
import * as fs from "node:fs";
import * as path from "node:path";
import type { FileViewActionCtx } from "./file-view";
import type { Status, Hunk, StoreComment } from "./file-comments-model";
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
/** The same change with its offsets moved by `n` — hunks computed over another string. */
const shifted = (h: Hunk, n: number): Hunk => ({ ...h, curFrom: h.curFrom + n, curTo: h.curTo + n });
const passage: StoreComment = {
  id: T0 + "-118", author: "you", ts: T0, body: "Which cache? Say which.",
  anchor: { quote: "shipping the cache in v1.2", prefix: "We recommend ", suffix: "." }, replies: [], resolved: false,
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
  constructor(public type: string, init: { key?: string } = {}) { this.key = init.key || ""; hideEdges(this); }
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
function answer(w: World, s: Status, m = lastOf(w, "fileComments", "status"), extra: Record<string, unknown> = {}): void {
  assert.ok(m, "an ask is outstanding");
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId: m.reqId, ...s, ...extra } }));
  w.mtimes[w.ctx.path] = s.fileMtimeNs;
  if (s.storePath && s.storeMtimeNs !== null) w.mtimes[s.storePath] = s.storeMtimeNs;
  if (s.root && s.configMtimeNs !== null) w.mtimes[s.root + "/.trackchanges/config.json"] = s.configMtimeNs;
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


// ── helpers of this suite ──────────────────────────────────────────────────────────────────────────
const SETTINGS_KEY = "romp:settings";
const toggle = (aside: El): El | null => act(aside, "fcinline");
const changeCards = (aside: El): El[] => aside.querySelectorAll(".fc-card.fc-change");
const ON = "Show the change in the Raw view";
const OFF = "Open the Raw view at the change";
const OFF_TAIL = "; the marks are off, so the change is not marked there";
const revealOf = (aside: El, key: string): El => { const rv = act(card(aside, key)!, "fcreveal", key); assert.ok(rv, key + " offers Reveal"); return rv!; };
// DOC's lines: 1 "# Report", 3 "## Findings", 4 the p95 sentence (h1, h2), 6 the recommendation (h3), 10 the next steps (h5)
const LINE: Record<string, number> = { "chg:h1": 4, "chg:h2": 4, "chg:h3": 6 };

test("Rendered, marks on: a deletion's Reveal says it shows the change in Raw; off: every card's Reveal says it opens Raw at the change and that the marks are off, with the same line number, and the click still goes to Raw at the change's start; on again: the Slice 2 title is back", async (t: TestContext) => {
  store.delete(SETTINGS_KEY);
  const w = world({ mode: "rendered" }); t.after(() => w.close());
  const { aside } = await openPanel(w, status({ hunks: [h1, h2, h3] }));
  assert.equal(revealOf(aside, "chg:h3").title, ON + " (line 6)", "on: Raw paints the deletion's point, so the title promises it");
  assert.equal(act(card(aside, "chg:h1")!, "fcreveal", "chg:h1"), null, "a painted substitution needs no Reveal");
  assert.equal(act(card(aside, "chg:h2")!, "fcreveal", "chg:h2"), null, "nor a painted insertion");
  toggle(aside)!.click(); await flush();
  assert.equal(marksOf(w).length, 0, "off: nothing is marked in the body");
  assert.equal(changeCards(aside).length, 3);
  for (const c of changeCards(aside)) {
    const key = c.dataset.id;
    const title = revealOf(aside, key).title;
    assert.equal(title, OFF + " (line " + LINE[key] + ")" + OFF_TAIL, key + ": the place, the line, and why nothing is marked");
    assert.doesNotMatch(title, /Show the change/, key + ": no promise of a mark Raw will not paint");
  }
  revealOf(aside, "chg:h3").click();
  assert.deepEqual(w.modes, ["raw"]); assert.deepEqual(w.scrolls, [h3.curFrom], "the click does what the title says: Raw, at the change");
  toggle(aside)!.click(); await flush();
  assert.equal(marksOf(w).length, 4, "on again: the marks are back");
  assert.equal(revealOf(aside, "chg:h3").title, ON + " (line 6)", "…and so is the title that names them");
  assert.equal(act(card(aside, "chg:h1")!, "fcreveal", "chg:h1"), null);
  assert.equal(act(card(aside, "chg:h2")!, "fcreveal", "chg:h2"), null);
  store.delete(SETTINGS_KEY);
});

test("Raw with a store that says off: every card's Reveal wears the off title, in Raw as in Rendered; the flip to on restores the Slice 2 title on the deletion and drops Reveal from the painted substitution", async (t: TestContext) => {
  store.set(SETTINGS_KEY, JSON.stringify({ changesInline: false }));
  const w = world(); t.after(() => w.close());   // Raw
  const { aside } = await openPanel(w, status({ hunks: [h1, h3] }));
  assert.equal(toggle(aside)!.dataset.on, "0"); assert.equal(marksOf(w).length, 0, "Raw paints no mark: the title must not claim one");
  assert.equal(revealOf(aside, "chg:h1").title, OFF + " (line 4)" + OFF_TAIL);
  assert.equal(revealOf(aside, "chg:h3").title, OFF + " (line 6)" + OFF_TAIL);
  toggle(aside)!.click(); await flush();
  assert.equal(marksOf(w, "h3")[0].dataset.fcText, "quickly ", "on: the Raw point");
  assert.equal(revealOf(aside, "chg:h3").title, ON + " (line 6)");
  assert.equal(act(card(aside, "chg:h1")!, "fcreveal", "chg:h1"), null, "painted in Raw: no Reveal");
  store.delete(SETTINGS_KEY);
});

test("the bytes in flux with the marks off — a reject's reply landed, its reload not yet: the deletion's Reveal keeps the off title with no line number, since an offset into other bytes names no line; the line is back once the bytes land", async (t: TestContext) => {
  store.set(SETTINGS_KEY, JSON.stringify({ changesInline: false }));
  const w = world({ deferReload: true }); t.after(() => w.close());
  const { aside } = await openPanel(w, status({ hunks: [h1, h3, h5] }));
  assert.equal(revealOf(aside, "chg:h5").title, OFF + " (line 10)" + OFF_TAIL, "off: the unpainted insertion offers Reveal with its line");
  act(card(aside, "chg:h1")!, "fcreject", "h1")!.click(); await flush();
  const m = lastOf(w, "fileComments", "reject");
  // the reply: "cut" is "reduced" again, so every survivor sits four characters further on
  w.disk = DOC.replace("cut", "reduced"); w.diskMtime = "1757145600000000011";
  answer(w, status({ fileMtimeNs: "1757145600000000011", storeMtimeNs: "1757145600000000012", hunks: [shifted(h3, 4), shifted(h5, 4)],
    store: { v: 3, path: "docs/report.md", suggestions: [SUGG[1]], comments: [passage] },
    unsent: { comments: [passage.id], replies: [], accepted: 0, rejected: 1, watermark: null } }), m, { rejected: ["h1"] }); await flush(); await flush();
  assert.ok(w.landReload, "the reload is held: the view still shows the old bytes");
  assert.equal(revealOf(aside, "chg:h3").title, OFF + OFF_TAIL, "no line number from offsets into other bytes");
  assert.equal(act(card(aside, "chg:h5")!, "fcreveal", "chg:h5"), null, "an insertion's Reveal waits for the bytes, marks off or on");
  w.landReload!(); await flush();
  assert.equal(revealOf(aside, "chg:h3").title, OFF + " (line 6)" + OFF_TAIL, "the bytes landed: the line is known again");
  assert.equal(revealOf(aside, "chg:h5").title, OFF + " (line 10)" + OFF_TAIL);
  store.delete(SETTINGS_KEY);
});

test("pins: the title branches on the toggle's field, and both branches share the one line-number computation", () => {
  const i = SRC.indexOf('const rv = btn("Reveal", "fcreveal"); rv.dataset.id = c.key;');
  assert.ok(i >= 0);
  const block = SRC.slice(i, SRC.indexOf("acts.appendChild(rv)", i));
  assert.match(block, /const line = src !== null && !inFlux \? " \(line " \+ \(rawOffsetToLine\(src, c\.curFrom\) \+ 1\) \+ "\)" : "";/, "one line suffix");
  assert.match(block, /rv\.title = this\.inline \? "Show the change in the Raw view" \+ line\n\s+: "Open the Raw view at the change" \+ line \+ "; the marks are off, so the change is not marked there";/, "on: the mark; off: the place, and why");
});

test("the stand-in's nodes inspect as their projection: no enumerable edge, so a failing assertion's dump cannot walk the tree", () => {
  const root = doc.createElement("div");
  const kid = doc.createElement("span");
  root.appendChild(kid);
  kid.appendChild(doc.createTextNode("leaf"));
  root.setAttribute("data-x", "1"); root.classList.add("c");
  for (const n of [root, kid, kid.firstChild as Txt]) {
    assert.ok(Object.keys(n).every((k) => staysEnumerable((n as unknown as Record<string, unknown>)[k])), "only primitives stay enumerable on " + n.constructor.name);
    const dump = inspect(n, { compact: false, customInspect: false, depth: 1000, maxArrayLength: Infinity, showHidden: false, showProxy: false, sorted: true, getters: true });
    assert.ok(!dump.includes("parentNode") && !dump.includes("childNodes"), "no edge in the dump: " + dump);
  }
  // the file's own Ev hides target and currentTarget the same way (hideEdges(this) at the end of its constructor)
  assertHiddenEvent(new Ev("click"), root, kid);
});

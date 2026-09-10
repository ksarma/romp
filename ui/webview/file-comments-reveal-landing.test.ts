// The landing cue (the inline-display follow-on to plans/file-review.md, 2026-09-07; the review's finding): with Show
// changes inline off every change card offers Reveal, which switches to Raw and centres the change's row — and painted
// nothing there. The row the person landed on looked like its neighbours, and the line number and the "marks are off"
// clause lived in the button's title, which a finger never sees. Now a Reveal that lands where the Raw view shows no mark
// of ours for its subject cues the LANDING ROW: the `.fv-cl` the scroll centred wears `fc-landing` with the accent wash
// and bar inline (a row cue, not a change mark: the toggle's contract holds and no change mark appears). The cue is
// transient by event — the next paint pass, the next Reveal, the panel closing — never by clock. Driven AS A PANEL over
// the reveal-title suite's DOM stand-in, with a viewer seam that does what the real one does on setMode: re-renders the
// body synchronously and fires onRendered, and on scrollToOffset centres the row by the count of line ends:
//   • Rendered, marks off, a coarse pointer: Reveal on the deletion → Raw, the centred row cued, one row, no change mark;
//     Reveal on the insertion moves the cue (one landing at a time);
//   • marks on: the deletion's Reveal lands on its struck point in Raw, and no row is cued (the mark is the cue);
//   • the lifetime: a card opening (an aside re-render) leaves the cue; the toggle's flip, an accept's reply (a status
//     landing) and the panel closing each strip it, class and styles both;
//   • a file the viewer shows only Raw (setMode a no-op): the cue lands with no re-render;
//   • the source pins: paintAll clears before it paints, both Reveal branches cue after the scroll, the dress names the accent
//     tokens and no hex, and the row is chosen as the viewer's scrollToOffset chooses it.
// Synthetic fixtures only: the notes-api world, placeholder ids.
import { test, type TestContext } from "node:test";
import * as assert from "node:assert/strict";
import { inspect } from "node:util";
import * as fs from "node:fs";
import * as path from "node:path";
import type { FileViewActionCtx } from "./file-view";
import type { Status, Hunk, StoreComment } from "./file-comments-model";
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
  constructor(public type: string, init: { key?: string } = {}) { this.key = init.key || ""; }
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

const FV = web("file-view.ts");
// the pointer the finding's scenario names: a phone, where no title is ever shown (isCoarsePointer reads this query)
let coarse = false;
win.matchMedia = (q: string) => ({ matches: q === "(pointer: coarse)" && coarse });

// ── the viewer stand-in: a markdown file's Raw or Rendered body, with the seam doing what the real one does ────────
// setMode re-renders the body SYNCHRONOUSLY and fires onRendered (file-view.ts renderBody: the text is in memory), so
// the panel's paint pass has run by the time Reveal scrolls; scrollToOffset centres the `.fv-cl` row by the count of
// line ends before the offset, clamped to the last row (the viewer's own rule). A file the viewer never renders
// (md: false) keeps its Raw body on setMode, as the real seam returns early for a non-markdown file.
type World = {
  ctx: FileViewActionCtx; posted: any[]; main: El; body: El;
  hooks: { rendered: Array<() => void>; close: Array<() => void> };
  disk: string; diskMtime: string; viewMtime: string; reloads: number; scrolls: number[]; modes: string[];
  mtimes: Record<string, string>;
  mode: () => "raw" | "rendered";
  close(): void;
};
let cur: World | null = null;
(globalThis as any).fetch = async (url: string) => {
  if (url.includes("/sessions")) return { json: async () => [{ id: SID, name: "api", bg: "#123456", fg: "#ffffff" }] };
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
function renderedDoc(box: El): void {
  box.replaceChildren(el("h1", "Report"), el("h2", "Findings"), el("p", "The api session cut p95 latency by 40% and the p99 by 10%."),
    el("p", "We recommend shipping the cache in v1.2."), el("p", "Risks remain in the fallback path."), el("p", "Next steps: measure again."));
}
type WorldOpts = { mode?: "raw" | "rendered"; md?: boolean };
function world(over: WorldOpts = {}): World {
  let mode: "raw" | "rendered" = over.mode || "raw";
  const md = over.md !== false;
  const main = new El("div"); main.className = "fileview-main";
  const body = new El("div"); body.className = "fileview-body";
  main.appendChild(body);
  let text = DOC;
  const paintBody = () => {
    if (mode === "raw") {
      const wrap = new El("div"); wrap.className = "fileview-code";
      const pre = new El("pre"); pre.className = "fileview-pre fileview-wrap";
      const code = new El("code"); code.className = "hljs";
      pre.appendChild(code); wrap.appendChild(pre);
      rows(code, text);
      body.replaceChildren(wrap);
    } else {
      const box = new El("div"); box.className = "fileview-md";
      renderedDoc(box);
      body.replaceChildren(box);
    }
  };
  paintBody();
  const w = {
    posted: [] as any[], main, body,
    hooks: { rendered: [] as Array<() => void>, close: [] as Array<() => void> },
    disk: text, diskMtime: "1757145600000000001", viewMtime: "1757145600000000001", reloads: 0, scrolls: [] as number[], modes: [] as string[], mtimes: {} as Record<string, string>,
    mode: () => mode,
  } as World;
  const fireRendered = () => { for (const cb of w.hooks.rendered) cb(); };
  w.ctx = {
    path: ABS, sid: SID, todoId: null,
    body: () => body as unknown as HTMLElement, mode: () => mode, text: () => text, mtimeNs: () => w.viewMtime, media: () => null, mediaElement: () => null, renderedImages: () => [], pdfPages: () => [],
    identity: () => ({ name: "api", color: null }),
    onRendered: (cb) => { w.hooks.rendered.push(cb); }, onSelection: () => { /* inert */ },
    onSaved: () => { /* inert */ }, onClose: (cb) => { w.hooks.close.push(cb); },
    post: (m) => { w.posted.push(m); }, ensureEditingAllowed: async () => true, setEditBlocked: () => { /* inert */ }, editing: () => false, setTrackedEdit: () => { /* inert */ }, guardClose: () => { /* inert */ },
    aside: (node) => { main.querySelector(".fileview-aside")?.remove(); if (node) { const n = node as unknown as El; n.classList.add("fileview-aside"); main.appendChild(n); } },
    // the real seam: `if (!isMd || editing) return; fmt.md = mode; saveFmt(fmt); renderBody();` — renderBody swaps the body and fires onRendered
    setMode: (m) => { w.modes.push(m); if (!md) return; mode = m; paintBody(); fireRendered(); },
    // the real seam: the `.fv-cl` at the count of line ends before the offset, clamped to the last row, centred
    scrollToOffset: (n) => {
      w.scrolls.push(n);
      const code = body.querySelector("code.hljs");
      if (!code) return;
      const all = code.querySelectorAll(".fv-cl");
      if (!all.length) return;
      const line = (text.slice(0, Math.max(0, n)).match(/\n/g) || []).length;
      all[Math.min(line, all.length - 1)].scrollIntoView();
    },
    reload: () => { w.reloads++; w.viewMtime = w.diskMtime; text = w.disk; paintBody(); fireRendered(); },
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
const marksOf = (w: World, id?: string): El[] => w.body.querySelectorAll('[data-act="fcchange"]' + (id ? '[data-id="' + id + '"]' : ""));

// ── helpers of this suite ──────────────────────────────────────────────────────────────────────────
const SETTINGS_KEY = "romp:settings";
const toggle = (aside: El): El | null => act(aside, "fcinline");
const revealOf = (aside: El, key: string): El => { const rv = act(card(aside, key)!, "fcreveal", key); assert.ok(rv, key + " offers Reveal"); return rv!; };
const rawRows = (w: World): El[] => w.body.querySelectorAll("code.hljs .fv-cl");
/** The Raw row of a 1-based line, as the gutter numbers it. */
const rowAt = (w: World, line: number): El => { const r = rawRows(w)[line - 1]; assert.ok(r, "line " + line + " has a row"); return r; };
const cued = (w: World): El[] => rawRows(w).filter((r) => r.classes.includes("fc-landing"));
const BG = "var(--accent-wash)";
const BAR = "inset 2px 0 0 var(--accent)";
/** The cue in full: the class and both inline declarations, so a half-stripped row fails as loudly as a missing cue. */
function assertCued(row: El, why: string): void {
  assert.ok(row.classes.includes("fc-landing"), why + ": the row wears fc-landing");
  assert.equal(row.style.background, BG, why + ": the accent wash, inline");
  assert.equal(row.style.boxShadow, BAR, why + ": the accent bar at the row's left edge, inline");
}
function assertClean(row: El, why: string): void {
  assert.equal(row.classes.includes("fc-landing"), false, why + ": no fc-landing");
  assert.equal(row.style.background ?? "", "", why + ": no wash left behind");
  assert.equal(row.style.boxShadow ?? "", "", why + ": no bar left behind");
}
// DOC's lines: 1 "# Report", 3 "## Findings", 4 the p95 sentence (h1, h2), 6 the recommendation (h3), 10 the next steps (h5)

test("Rendered, marks off, on a phone: Reveal on the deletion switches to Raw and cues the row it centred — line 6, the class and the accent dress inline — one row, with no change mark anywhere; Reveal on the insertion moves the cue to line 4 and leaves line 6 clean", async (t: TestContext) => {
  store.set(SETTINGS_KEY, JSON.stringify({ changesInline: false }));
  coarse = true; t.after(() => { coarse = false; store.delete(SETTINGS_KEY); });
  const w = world({ mode: "rendered" }); t.after(() => w.close());
  const { aside } = await openPanel(w, status({ hunks: [h1, h2, h3] }));
  assert.equal(rawRows(w).length, 0, "Rendered: no rows yet");
  assert.equal(marksOf(w).length, 0, "off: nothing is marked");
  revealOf(aside, "chg:h3").click();
  assert.deepEqual(w.modes, ["raw"]); assert.deepEqual(w.scrolls, [h3.curFrom], "Raw, at the change's start");
  assert.equal(w.mode(), "raw"); assert.equal(rawRows(w).length, 10, "the Raw rows are up");
  const six = rowAt(w, 6);
  assert.equal(six.textContent, "We recommend shipping the cache in v1.2.", "the deletion's row");
  assert.equal(scrolledInto[scrolledInto.length - 1], six, "the viewer centred it");
  assertCued(six, "the centred row is the landing");
  assert.deepEqual(cued(w), [six], "one row cued, and only that one");
  assert.equal(marksOf(w).length, 0, "a row cue is not a change mark: the marks stay off");
  assert.equal(w.body.textContent.includes("quickly"), false, "the deletion's old text is not put into the view");
  assert.equal(w.body.querySelectorAll(".fc-hl").length, 1, "the passage comment's highlight is painted in Raw as ever");
  // the next Reveal: one landing at a time
  revealOf(aside, "chg:h2").click();
  assert.deepEqual(w.scrolls, [h3.curFrom, h2.curFrom]);
  const four = rowAt(w, 4);
  assert.equal(scrolledInto[scrolledInto.length - 1], four);
  assertCued(four, "the insertion's row is the landing now");
  assert.deepEqual(cued(w), [four], "the deletion's row gave the cue up");
  assert.equal(marksOf(w).length, 0);
});

test("marks on: the deletion's Reveal lands on its struck point in Raw, and the row wears no cue — the mark is the cue", async (t: TestContext) => {
  store.delete(SETTINGS_KEY);
  const w = world({ mode: "rendered" }); t.after(() => w.close());
  const { aside } = await openPanel(w, status({ hunks: [h1, h3] }));
  assert.equal(marksOf(w, "h3").length, 1, "on: the Rendered point");
  revealOf(aside, "chg:h3").click();
  assert.deepEqual(w.modes, ["raw"]);
  const pt = marksOf(w, "h3");
  assert.equal(pt.length, 1, "Raw paints the deletion's point");
  assert.equal(pt[0].dataset.fcText, "quickly ");
  assert.ok(rowAt(w, 6).contains(pt[0]), "…on the row the scroll centred");
  assert.equal(cued(w).length, 0, "no row cue beside a mark");
  assertClean(rowAt(w, 6), "the marked row");
});

test("the cue leaves on events, never on a clock: a card opening (an aside re-render) keeps it; the toggle's flip strips it from the row that stays; an accept's reply (a status landing) strips it; the panel closing strips it", async (t: TestContext) => {
  store.set(SETTINGS_KEY, JSON.stringify({ changesInline: false }));
  t.after(() => store.delete(SETTINGS_KEY));
  const w = world({ mode: "rendered" }); t.after(() => w.close());
  const { aside, button } = await openPanel(w, status({ hunks: [h1, h3] }));
  revealOf(aside, "chg:h3").click();
  let six = rowAt(w, 6);
  assertCued(six, "landed");
  // an aside re-render alone: the card opens, the body is untouched, the cue stands
  act(aside, "fccard", "chg:h1")!.click();
  assert.ok(card(aside, "chg:h1")!.classes.includes("open"), "the card opened (render ran)");
  assert.equal(rowAt(w, 6), six, "the same row");
  assertCued(six, "an aside re-render is not new information about the rows");
  // the toggle: a paint pass over the same rows — the marks come on, the cue comes off, class and styles both
  toggle(aside)!.click(); await flush();
  assert.equal(rowAt(w, 6), six, "the flip repaints the same body");
  assert.equal(marksOf(w, "h3").length, 1, "on: the point is there now");
  assertClean(six, "the marks answer where the change is; the landing cue is gone");
  assert.equal(cued(w).length, 0);
  toggle(aside)!.click(); await flush();
  assertClean(six, "off again: no cue comes back on its own");
  // a status landing: the person's own Accept, whose reply repaints
  revealOf(aside, "chg:h3").click();
  six = rowAt(w, 6);
  assertCued(six, "revealed again");
  act(card(aside, "chg:h1")!, "fcaccept", "h1")!.click(); await flush();
  const m1 = lastOf(w, "fileComments", "accept");
  answer(w, status({ hunks: [h3], store: { v: 3, path: "docs/report.md", suggestions: [SUGG[1]], comments: [passage] }, storeMtimeNs: "1757145600000000004",
    unsent: { comments: [passage.id], replies: [], accepted: 1, rejected: 0, watermark: null } }), m1, { accepted: ["h1"] }); await flush(); await flush();
  assert.equal(card(aside, "chg:h1"), null, "the accept landed");
  assert.equal(rowAt(w, 6), six, "the same rows (the file did not move)");
  assertClean(six, "a status landed: the cue is stale information");
  // the panel closing: the row is the viewer's, and the gesture that cued it was the panel's
  revealOf(aside, "chg:h3").click();
  six = rowAt(w, 6);
  assertCued(six, "revealed once more");
  button.click();
  assert.equal(w.main.querySelector(".fileview-aside"), null, "the panel closed");
  assert.equal(rowAt(w, 6), six);
  assertClean(six, "closing strips the cue");
  assert.equal(cued(w).length, 0);
});

test("a file the viewer shows only Raw (setMode returns early): with the marks off, Reveal cues the row with no re-render, and a second Reveal on the same row leaves one cue", async (t: TestContext) => {
  store.set(SETTINGS_KEY, JSON.stringify({ changesInline: false }));
  t.after(() => store.delete(SETTINGS_KEY));
  const w = world({ md: false }); t.after(() => w.close());   // Raw, and Raw it stays
  const { aside } = await openPanel(w, status({ hunks: [h1, h2, h3] }));
  const four = rowAt(w, 4);
  const hooks = w.hooks.rendered.length; const before = w.reloads;
  revealOf(aside, "chg:h1").click();
  assert.deepEqual(w.scrolls, [h1.curFrom]);
  assert.equal(rowAt(w, 4), four, "no re-render: the same row");
  assert.equal(w.reloads, before); assert.equal(w.hooks.rendered.length, hooks);
  assertCued(four, "the row the scroll centred");
  assert.deepEqual(cued(w), [four]);
  revealOf(aside, "chg:h2").click();   // the insertion sits on the same line
  assert.deepEqual(cued(w), [four], "the same row, cued once");
  assertCued(four, "still the landing");
  assert.equal(marksOf(w).length, 0, "off: no change mark in Raw");
});

test("pins: paintAll clears the landing before it paints; both Reveal branches cue right after the scroll; closePanel and dispose clear it; the dress names the accent tokens and no hex; the row is the one the viewer's scrollToOffset centres", () => {
  // the editor's stand-down keeps the first line (file-comments-behavior.test.ts pins it; the rows are the editor's then), the cue clears next
  assert.match(SRC, /paintAll\(\): void \{\n\s*if \(this\.ctx\.editing\(\)\) \{ this\.render\(\); return; \}[^\n]*\n\s+this\.clearLanding\(\);/, "the first statement of the read view's paint pass");
  assert.match(SRC, /this\.ctx\.scrollToOffset\(c\.curFrom\);\n\s+this\.landOn\(c\.curFrom, "fcchange", c\.id\);/, "a change: its start, its marks' action and id");
  assert.match(SRC, /this\.ctx\.scrollToOffset\(loc\.range\.start\);\n\s+this\.landOn\(loc\.range\.start, "fcopen", key\);/, "a comment: its range's start, its highlight's action and id");
  const close = SRC.slice(SRC.indexOf("  closePanel(): void {"), SRC.indexOf("  dispose(): void {"));
  assert.match(close, /this\.clearLanding\(\);/, "closePanel");
  const dispose = SRC.slice(SRC.indexOf("  dispose(): void {"), SRC.indexOf("  dispose(): void {") + 200);
  assert.match(dispose, /this\.clearLanding\(\);/, "dispose");
  assert.match(SRC, /const LANDING_BG = "var\(--accent-wash\)";/);
  assert.match(SRC, /const LANDING_BAR = "inset 2px 0 0 var\(--accent\)";/);
  const land = SRC.slice(SRC.indexOf("  private landOn("), SRC.indexOf("  private clearLanding("));
  assert.doesNotMatch(land, /#[0-9a-fA-F]{3,8}\b/, "no hardcoded colour in the cue (ui/CLAUDE.md)");
  assert.match(land, /if \(this\.ownMarks\(act, id\)\.length\) return;/, "a marked subject gets no row cue");
  assert.match(land, /const code = this\.ctx\.body\(\)\.querySelector\("code\.hljs"\);/, "the Raw root, as scrollToOffset finds it");
  assert.match(land, /rows\[Math\.min\(rawOffsetToLine\(src, offset\), rows\.length - 1\)\]/, "the row by line ends before the offset, clamped");
  // the viewer's rule the cue mirrors — should scrollToOffset choose its row another way, the cue must follow
  const sto = FV.slice(FV.indexOf("    scrollToOffset: (n) => {"), FV.indexOf("    reload: () =>"));
  assert.match(sto, /const rows = code\.querySelectorAll\("\.fv-cl"\);/);
  assert.match(sto, /const line = \(src\.slice\(0, Math\.max\(0, n\)\)\.match\(\/\\n\/g\) \|\| \[\]\)\.length;/);
  assert.match(sto, /rows\[Math\.min\(line, rows\.length - 1\)\]/);
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
});

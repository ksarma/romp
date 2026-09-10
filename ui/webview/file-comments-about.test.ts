// The about follow-on's panel (plans/file-review.md, "The about follow-on (2026-09-10)" under Slice 2; decisions 45 and
// the section-3 rule of decision 44's neighbour), driven over the Slice 2 stand-in (file-comments-changes.test.ts's,
// copied here as the sibling modules copy it, with the tree's edges hidden from a failing assertion). Pinned: no comment
// is drawn inside a change card, every comment its own card in the one list under All and Comments; the change card's
// Reply is Comment on this change, opening the composer in the panel's slot anchored over the change's span with the
// about option checked (a deletion: the comment about the change by id alone, the box saying so in one line), and Save
// posting changeIds beside the anchor, never suggestionId; a selection overlapping pending changes' marks offers the
// checked "about this change" (or "about N changes") option, unchecked a plain passage comment; a selection over a
// deletion's struck label alone offers the comment about that change by id; the tags on both cards ("about a change" on
// the comment, lighting the change's marks under the pointer; "N comments" on the change card, a control whose click
// shows the first, All chosen first when Changes hides it); a legacy suggestionId comment wearing "answered by a change";
// and the sources: no renderHosted, no .fc-hosted rule in either sheet, the ring rule in both. Synthetic fixtures only:
// the notes-api world, placeholder ids, the session "api".
import { test, type TestContext } from "node:test";
import * as assert from "node:assert/strict";
import { inspect } from "node:util";
import { assertHiddenEvent, hideEdges, staysEnumerable } from "../test-dom-shim";
import * as fs from "node:fs";
import * as path from "node:path";
import type { FileViewActionCtx } from "./file-view";
import { type Status, type Hunk, type StoreComment } from "./file-comments-model";

const web = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const SRC = web("file-comments.ts");
const CHAT_CSS = web("styles.css");
const FEED_CSS = web("feed.css");

// ── fixtures: the notes-api world (the Slice 2 suite's document and changes) ───────────────────────
const SID = "11111111-2222-3333-4444-555555555555";
const ABS = "/repo/notes-api/docs/report.md";
const ROOT = "/repo/notes-api";
const STORE_PATH = ROOT + "/.trackchanges/docs%2Freport.md.json";
const T0 = 1757145600000;
// the CURRENT text: the session's changes already applied (the file on disk always reads as if accepted)
const DOC = "# Report\n\n## Findings\nThe api session cut p95 latency by 40% and the p99 by 10%.\n\n"
  + "We recommend shipping the cache in v1.2.\n\nRisks remain in the fallback path.\n\nNext steps: measure again.\n";
const at = (needle: string, from = 0): number => { const i = DOC.indexOf(needle, from); assert.ok(i >= 0, needle); return i; };
const H = (id: string, kind: Hunk["kind"], from: number, to: number, oldText: string, newText: string, ts = T0 - 90000): Hunk =>
  ({ id, author: "api", ts, kind, curFrom: from, curTo: to, baseFrom: from, baseTo: from + oldText.length, oldText, newText, anchor: null });
const h1 = H("h1", "sub", at("cut"), at("cut") + 3, "reduced", "cut");                                        // ## Findings …
const h2 = H("h2", "ins", at(" and the p99"), at(" and the p99") + " and the p99 by 10%".length, "", " and the p99 by 10%", T0 - 80000);
const h3 = H("h3", "del", at("shipping"), at("shipping"), "quickly ", "", T0 - 70000);                           // a point: We recommend …
const passage: StoreComment = {
  id: T0 + "-118", author: "you", ts: T0, body: "Which cache? Say which.",
  anchor: { quote: "shipping the cache in v1.2", prefix: "We recommend ", suffix: "." }, replies: [], resolved: false,
};
/** A legacy comment the session's track-edit --thread bound to h1: the format's own field, read as the change that answered it. */
const legacy: StoreComment = { id: T0 + 1000 + "-5", author: "you", ts: T0 + 1000, body: "Say cut, not reduced.", suggestionId: "h1", replies: [
  { author: "api", authorId: SID, ts: T0 + 2000, kind: "edit", oldText: "cut", newText: "trimmed" },
], resolved: false };
const SUGG = [{ id: "h1", author: "api", authorId: SID, ts: T0 - 90000, kind: "sub", from: h1.curFrom, oldText: "reduced", newText: "cut" },
  { id: "h2", author: "api", authorId: SID, ts: T0 - 80000, kind: "ins", from: h2.curFrom, oldText: "", newText: h2.newText },
  { id: "h3", author: "api", ts: T0 - 70000, kind: "del", from: h3.curFrom, oldText: "quickly " }];
function status(over: Partial<Status> = {}): Status {
  return {
    verb: "status", root: ROOT, storePath: STORE_PATH, trackedBy: { kind: "file", entry: "docs/report.md" }, agentTooling: "present",
    fileMtimeNs: "1757145600000000001", storeMtimeNs: "1757145600000000002", configMtimeNs: "1757145600000000003",
    store: { v: 3, path: "docs/report.md", suggestions: SUGG, comments: [passage] },
    hunks: [h1, h2, h3], log: [],
    unsent: { comments: [passage.id], replies: [], accepted: 0, rejected: 0, watermark: null },
    ...over,
  };
}

// ── a DOM stand-in: ancestry, attributes, events with capture and bubbling, a small selector engine ──
class Ev {
  target: El | Txt | null = null;
  currentTarget: El | null = null;
  defaultPrevented = false;
  stopped = false;
  key: string;
  ctrlKey: boolean; metaKey: boolean;
  constructor(public type: string, init: { key?: string; ctrlKey?: boolean; metaKey?: boolean } = {}) { this.key = init.key || ""; this.ctrlKey = !!init.ctrlKey; this.metaKey = !!init.metaKey; hideEdges(this); }
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
  get previousSibling(): El | Txt | null { const p = this.parentNode; if (!p) return null; const i = p.childNodes.indexOf(this); return i > 0 ? p.childNodes[i - 1] : null; }
  get nextSibling(): El | Txt | null { const p = this.parentNode; if (!p) return null; const i = p.childNodes.indexOf(this); return i >= 0 && i + 1 < p.childNodes.length ? p.childNodes[i + 1] : null; }
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
    // the tree's edges are non-enumerable, so a node inspects as its own projection and a failing assertion's dump
    // stays small (ui/test-dom-shim.ts says why); assignments later keep them hidden
    Object.defineProperty(this, "parentNode", { value: null, writable: true, enumerable: false, configurable: true });
    Object.defineProperty(this, "childNodes", { value: [], writable: true, enumerable: false, configurable: true });
    hideEdges(this);
  }
  get ownerDocument(): typeof doc { return doc; }
  get parentElement(): El | null { return this.parentNode; }
  get firstChild(): El | Txt | null { return this.childNodes[0] || null; }
  get previousSibling(): El | Txt | null { const p = this.parentNode; if (!p) return null; const i = p.childNodes.indexOf(this); return i > 0 ? p.childNodes[i - 1] : null; }
  get nextSibling(): El | Txt | null { const p = this.parentNode; if (!p) return null; const i = p.childNodes.indexOf(this); return i >= 0 && i + 1 < p.childNodes.length ? p.childNodes[i + 1] : null; }
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
  set textContent(v: string) { for (const c of this.childNodes) c.parentNode = null; this.childNodes.length = 0; if (v !== "") this.appendChild(new Txt(v)); }
  private detach(n: El | Txt): void { const p = n.parentNode; if (p) { const i = p.childNodes.indexOf(n); if (i >= 0) p.childNodes.splice(i, 1); n.parentNode = null; } }
  appendChild<T extends El | Txt>(n: T): T { this.detach(n); this.childNodes.push(n); n.parentNode = this; return n; }
  insertBefore<T extends El | Txt>(n: T, ref: El | Txt | null): T {
    if (!ref) return this.appendChild(n);
    this.detach(n);
    const i = this.childNodes.indexOf(ref);
    this.childNodes.splice(i < 0 ? this.childNodes.length : i, 0, n); n.parentNode = this; return n;
  }
  removeChild<T extends El | Txt>(n: T): T { this.detach(n); return n; }
  replaceChildren(...c: Array<El | Txt>): void { for (const x of this.childNodes) x.parentNode = null; this.childNodes.length = 0; for (const x of c) this.appendChild(x); }
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

// ── the viewer stand-in: the body row with Raw rows, the seam as closures, a file whose mtime the view tracks ──
type World = {
  ctx: FileViewActionCtx; posted: any[]; main: El; body: El; code: El;
  hooks: { rendered: Array<() => void>; close: Array<() => void> };
  disk: string; diskMtime: string; viewMtime: string; reloads: number; scrolls: number[]; modes: string[];
  mtimes: Record<string, string>;
  setText(src: string): void; close(): void;
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
function world(over: { todoId?: string | null; src?: string } = {}): World {
  const main = new El("div"); main.className = "fileview-main";
  const body = new El("div"); body.className = "fileview-body";
  const wrap = new El("div"); wrap.className = "fileview-code";
  const pre = new El("pre"); pre.className = "fileview-pre fileview-wrap";
  const code = new El("code"); code.className = "hljs";
  pre.appendChild(code); wrap.appendChild(pre);
  body.appendChild(wrap);
  main.appendChild(body);
  let text = over.src ?? DOC;
  const w = {
    posted: [] as any[], main, body, code,
    hooks: { rendered: [] as Array<() => void>, close: [] as Array<() => void> },
    disk: text, diskMtime: "1757145600000000001", viewMtime: "1757145600000000001", reloads: 0, scrolls: [] as number[], modes: [] as string[], mtimes: {} as Record<string, string>,
  } as World;
  rows(code, text);
  w.setText = (s) => { text = s; rows(code, s); for (const cb of w.hooks.rendered) cb(); };
  w.ctx = {
    path: ABS, sid: SID, todoId: over.todoId ?? null,
    body: () => body as unknown as HTMLElement, mode: () => "raw", text: () => text, mtimeNs: () => w.viewMtime, media: () => null, mediaElement: () => null, renderedImages: () => [], pdfPages: () => [],
    identity: () => ({ name: "api", color: null }),
    onRendered: (cb) => { w.hooks.rendered.push(cb); }, onSelection: () => { /* inert */ },
    onSaved: () => { /* inert */ }, onClose: (cb) => { w.hooks.close.push(cb); },
    post: (m) => { w.posted.push(m); }, ensureEditingAllowed: async () => true, setEditBlocked: () => { /* inert */ }, editing: () => false, setTrackedEdit: () => { /* inert */ }, guardClose: () => { /* inert */ },
    aside: (node) => { main.querySelector(".fileview-aside")?.remove(); if (node) { const n = node as unknown as El; n.classList.add("fileview-aside"); main.appendChild(n); } },
    setMode: (m) => { w.modes.push(m); }, scrollToOffset: (n) => { w.scrolls.push(n); },
    // fetchFile: the bytes and mtime now on disk, repainted, the seam's onRendered fired
    reload: () => { w.reloads++; w.viewMtime = w.diskMtime; w.setText(w.disk); },
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
async function openPanel(w: World, s: Status = status()): Promise<{ unit: El; button: El; aside: El }> {
  const fc = await import("./file-comments");
  const unit = fc.fileCommentsAction.mount(w.ctx) as unknown as El;
  const button = unit.childNodes[0] as El;
  answer(w, s); await flush();
  button.click();
  answer(w, s); await flush(); await flush();
  const aside = w.main.querySelector(".fileview-aside")!;
  assert.ok(aside, "the panel is mounted beside the body");
  return { unit, button, aside };
}
const card = (aside: El, key: string): El | null => aside.querySelector('.fc-card[data-id="' + key + '"]');
const act = (root: El, a: string, id?: string): El | null => root.querySelector('[data-act="' + a + '"]' + (id ? '[data-id="' + id + '"]' : ""));
const texts = (els: El[]) => els.map((e) => e.textContent);

// ── the drive ─────────────────────────────────────────────────────────────────────────────────────
/** The panel's own instance is private; the float is its button in the document's body, and its click reads the live
 *  selection (window.getSelection) as the panel reads it, so a selection is faked there and the float clicked. */
type Sel = { isCollapsed: boolean; anchorNode: El | Txt | null; focusNode: El | Txt | null; anchorOffset: number; focusOffset: number; rangeCount: number; getRangeAt: (i: number) => { intersectsNode: (n: El | Txt) => boolean }; toString: () => string };
const rangeOver = (...nodes: Array<El | Txt>) => ({ intersectsNode: (n: El | Txt) => nodes.some((x) => x === n || (x instanceof El && x.contains(n))) });
function selectFrom(anchor: Txt, a: number, focus: Txt, f: number, over: Array<El | Txt> = []): Sel {
  return { isCollapsed: anchor === focus && a === f, anchorNode: anchor, focusNode: focus, anchorOffset: a, focusOffset: f, rangeCount: 1, getRangeAt: () => rangeOver(anchor, focus, ...over), toString: () => "" };
}
const floatOf = (): El => { const f = doc.body.querySelector(".fc-float"); assert.ok(f, "the Comment float is in the body"); return f!; };
const markOf = (w: World, id: string): El => { const m = w.body.querySelector('[data-act="fcchange"][data-id="' + id + '"]'); assert.ok(m, "the change " + id + " is marked"); return m!; };
const composerOf = (aside: El) => {
  const box = aside.querySelector(".fc-composer")!;
  const ref = aside.querySelector(".fc-composer-ref")!;
  const opt = aside.querySelector('input[data-opt="about"]');
  return { box, hidden: box.hidden, ref: ref.childNodes.map((n) => (n instanceof El ? n.className : "") + ":" + n.textContent), quote: aside.querySelector(".fc-quote")?.textContent ?? null,
    opt: opt ? { checked: opt.checked, label: opt.parentNode!.textContent, title: opt.parentNode!.title } : null, presel: cur ? cur.body.querySelectorAll(".fc-presel").map((m) => m.textContent).join("") : "" };
};
async function save(w: World, aside: El, note: string): Promise<any> {
  const input = aside.querySelector(".fc-input")!;
  input.value = note;
  dispatch(input, new Ev("keydown", { key: "Enter", ctrlKey: true })); await flush();
  const m = lastOf(w, "fileComments", "comment");
  assert.ok(m, "the comment verb went");
  return m;
}
/** The status after a save: the same store plus the new comment, as the host would write it. */
function saved(c: StoreComment, over: Partial<Status> = {}): Status {
  const base = status(over);
  return { ...base, store: { ...base.store!, comments: [...base.store!.comments, c] }, storeMtimeNs: "1757145600000000009", unsent: { ...base.unsent, comments: [...base.unsent.comments, c.id] } };
}
const tagsOf = (el: El): string[] => texts(el.querySelectorAll(".fc-card-head .fc-tag"));
const lit = (w: World, id: string): boolean => w.body.querySelectorAll('[data-act="fcchange"][data-id="' + id + '"]').every((m) => m.classList.contains("fc-lit"));

// ── the list: no comment inside a change card; the tags both ways ─────────────────────────────────

test("every comment is its own card in the one list: a comment about a change is under All and Comments with its about tag, the change card counts it and hosts nothing; a legacy suggestionId comment wears answered by a change", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const about: StoreComment = { id: T0 + 3000 + "-17", author: "you", ts: T0 + 3000, body: "Both numbers need a source.", anchor: { quote: "cut p95 latency by 40%", prefix: "The api session ", suffix: " and the p99 by 10%." }, anchorAt: at("cut"), changeIds: ["h1", "h2"], replies: [], resolved: false };
  const { aside, button } = await openPanel(w, status({ store: { v: 3, path: "docs/report.md", suggestions: SUGG, comments: [passage, legacy, about] } }));
  assert.equal(button.textContent, "Comments · 3 · 3 changes");
  assert.deepEqual(aside.querySelectorAll(".fc-card").map((c) => c.dataset.id), ["chg:h1", "chg:h2", "chg:h3", passage.id, legacy.id, about.id], "changes first, then every comment's own card, oldest first");
  assert.equal(aside.querySelector(".fc-hosted"), null, "no comment is drawn inside a change card");
  // the change cards: the count tag, a control, and Comment on this change in place of Reply
  const c1 = card(aside, "chg:h1")!, c2 = card(aside, "chg:h2")!, c3 = card(aside, "chg:h3")!;
  assert.deepEqual(tagsOf(c1), ["2 comments"], "h1: the legacy comment and the about one");
  assert.deepEqual(tagsOf(c2), ["1 comment"]);
  assert.deepEqual(tagsOf(c3), [], "no comment names h3: no tag");
  const count = c1.querySelector(".fc-about-count")!;
  assert.equal(count.dataset.act, "fcaboutfirst"); assert.equal(count.dataset.id, "h1"); assert.equal(count.tabIndex, 0); assert.equal(count.getAttribute("role"), "button");
  assert.deepEqual(texts(c1.querySelectorAll(".fc-actions button")), ["Accept", "Reject", "Comment on this change"], "the change card's Reply became Comment on this change");
  assert.equal(act(c1, "fcchangereply"), null, "the old act is gone");
  // the comment cards: the tags by source, their titles the changes' words and states
  const ca = card(aside, about.id)!;
  assert.deepEqual(tagsOf(ca), ["about 2 changes"]);
  const tag = ca.querySelector(".fc-tag.fc-about")!;
  assert.equal(tag.title, "This comment is about: reduced → cut (pending); added and the p99 by 10% (pending)");
  assert.equal(tag.dataset.refs, "h1 h2");
  assert.equal(ca.querySelector(".fc-kind")!.title, "A comment on a passage", "a passage comment about changes is still a comment on its passage");
  const cl = card(aside, legacy.id)!;
  assert.deepEqual(tagsOf(cl), ["answered by a change", "1"], "the legacy binding, and the turn count");
  assert.equal(cl.querySelector(".fc-tag.fc-about")!.title, "The session answered this comment with: reduced → cut (pending)");
  assert.equal(cl.querySelector(".fc-ref")!.textContent, "reduced → cut", "no passage: the change's words are its reference");
  assert.equal(cl.querySelector(".fc-kind")!.title, "A comment the session answered with a change", "the legacy binding: the session answered, the person named nothing (the review, 2026-09-10)");
  // hover lights the changes' marks, leave unlights them; a render while lit unlights (the tag under the pointer is rebuilt)
  assert.equal(lit(w, "h1"), false);
  dispatch(tag, new Ev("pointerenter"));
  assert.ok(lit(w, "h1") && lit(w, "h2"), "both changes' marks ring under the pointer");
  assert.equal(lit(w, "h3"), false, "h3 is not the comment's");
  dispatch(tag, new Ev("pointerleave"));
  assert.ok(!lit(w, "h1") && !lit(w, "h2"), "and unlight when the pointer leaves");
  dispatch(tag, new Ev("pointerenter"));
  assert.ok(lit(w, "h1"));
  act(aside, "fcfilter", undefined)!.click();          // a render: the All button (already chosen: setFilter changes nothing, but the delegate's render path is the head's)
  card(aside, legacy.id)!.querySelector(".fc-card-head")!.click();   // a render for sure: a card opens
  assert.ok(!lit(w, "h1") && !lit(w, "h2"), "a render unlights first: the leave never fires on a rebuilt tag");
  // Comments: every comment card, no change card; Changes: the change cards alone, the count tag standing
  aside.querySelectorAll('[data-act="fcfilter"]').find((b) => b.dataset.key === "comments")!.click();
  assert.deepEqual(aside.querySelectorAll(".fc-card").map((c) => c.dataset.id), [passage.id, legacy.id, about.id], "Comments: the comment cards, the about one among them (before: on the change card)");
  aside.querySelectorAll('[data-act="fcfilter"]').find((b) => b.dataset.key === "changes")!.click();
  assert.deepEqual(aside.querySelectorAll(".fc-card").map((c) => c.dataset.id), ["chg:h1", "chg:h2", "chg:h3"], "Changes: the change cards alone");
  assert.deepEqual(tagsOf(card(aside, "chg:h1")!), ["2 comments"], "the count stands under Changes: the way to the hidden comments");
  // the count tag's click: All first, then the first comment about the change as the focus, its card open
  act(card(aside, "chg:h1")!, "fcaboutfirst", "h1")!.click(); await flush();
  assert.equal(aside.querySelectorAll('[data-act="fcfilter"]').find((b) => b.dataset.on === "1")!.dataset.key, "all", "Changes hid the comment cards: All is chosen for the click");
  assert.ok(card(aside, legacy.id)!.classes.includes("open"), "the first comment about h1 (the legacy one, older) is open");
  assert.ok(scrolledInto.includes(card(aside, legacy.id)!) || scrolledInto.length > 0, "and brought into view");
  // the keyboard: Enter on the focused count tag is its click (KEY_ACTS)
  card(aside, about.id)!.querySelector(".fc-card-head")!.click();
  const tag2 = card(aside, "chg:h2")!.querySelector(".fc-about-count")!;
  tag2.focus(); dispatch(tag2, new Ev("keydown", { key: "Enter" })); await flush();
  assert.ok(card(aside, about.id)!.classes.includes("open"), "Enter on h2's count opens the comment about it");
});

// ── Comment on this change ───────────────────────────────────────────────────────────────────────

test("Comment on this change on a substitution: the composer opens in the slot anchored over the change's new text, the about option checked, the presel over the span; Save posts the anchor with changeIds; the saved comment is its own card, tagged, and counted on the change card", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  act(card(aside, "chg:h1")!, "fcchangecomment", "h1")!.click(); await flush();
  assert.ok(card(aside, "chg:h1")!.classes.includes("open"), "the change card opens for it");
  const c = composerOf(aside);
  assert.equal(c.hidden, false);
  assert.equal(c.quote, "cut", "anchored over the change's span: its new text");
  assert.equal(c.presel, "cut", "the presel is painted over the span");
  assert.deepEqual(c.opt, { checked: true, label: "about this change", title: "reduced → cut" }, "the option, checked, named for the one change");
  assert.ok(!card(aside, "chg:h1")!.contains(c.box), "the box stands in the panel's slot, not in the card");
  const m = await save(w, aside, "Keep reduced; the abstract uses it.");
  assert.deepEqual(m.args, { note: "Keep reduced; the abstract uses it.", anchor: { quote: "cut", prefix: DOC.slice(at("cut") - 24, at("cut")), suffix: DOC.slice(at("cut") + 3, at("cut") + 27) }, hintOffset: at("cut"), changeIds: ["h1"] }, "the passage anchor and the change's stored id (decision 45); never suggestionId");
  const c1: StoreComment = { id: T0 + 5000 + "-" + at("cut"), author: "you", ts: T0 + 5000, anchor: m.args.anchor, anchorAt: at("cut"), changeIds: ["h1"], body: m.args.note, replies: [], resolved: false };
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId: m.reqId, ...saved(c1) } })); await flush();
  assert.equal(aside.querySelector(".fc-composer")!.hidden, true, "saved: the composer closes");
  assert.ok(card(aside, c1.id), "the new comment is its own card");
  assert.deepEqual(tagsOf(card(aside, c1.id)!), ["about a change"]);
  assert.deepEqual(tagsOf(card(aside, "chg:h1")!), ["1 comment"]);
  assert.equal(card(aside, "chg:h1")!.querySelector(".fc-hosted"), null);
  assert.ok(act(card(aside, "chg:h1")!, "fcchangecomment", "h1"), "Comment on this change stands for the next comment about it");
});

test("the option unchecked makes a plain passage comment: Save posts the anchor and no changeIds; checked again, the ids go", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  act(card(aside, "chg:h2")!, "fcchangecomment", "h2")!.click(); await flush();
  const c = composerOf(aside);
  assert.equal(c.quote, " and the p99 by 10%".trim(), "an insertion: its text (the quote's ends trimmed for display)");
  const cb = aside.querySelector('input[data-opt="about"]')!;
  cb.checked = false; dispatch(cb, new Ev("change"));
  const m = await save(w, aside, "Is the p99 measured the same way?");
  assert.equal("changeIds" in m.args, false, "unchecked: a passage comment like any other");
  assert.equal(m.args.anchor.quote, " and the p99 by 10%");
  const w2 = world(); t.after(() => w2.close());
  const { aside: a2 } = await openPanel(w2);
  act(card(a2, "chg:h2")!, "fcchangecomment", "h2")!.click(); await flush();
  const cb2 = a2.querySelector('input[data-opt="about"]')!;
  cb2.checked = false; dispatch(cb2, new Ev("change"));
  cb2.checked = true; dispatch(cb2, new Ev("change"));
  const m2 = await save(w2, a2, "Is the p99 measured the same way?");
  assert.deepEqual(m2.args.changeIds, ["h2"], "checked again: the change's id goes");
});

test("Comment on this change on a deletion: no passage to carry it, so the composer offers the comment about the change alone and says so in one line; Save posts changeIds with no anchor; the saved card has no passage and the change's words as its reference", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  act(card(aside, "chg:h3")!, "fcchangecomment", "h3")!.click(); await flush();
  const c = composerOf(aside);
  assert.equal(c.hidden, false);
  assert.equal(c.opt, null, "no option: the comment can only be about the change");
  assert.deepEqual(c.ref, ["fc-note:About the change ", "fc-quote:removed quickly", "fc-note:The removed text is not in the file, so the comment names the change instead of a passage."], "the list layout's line (this stand-in lays no card at any point; the margin layout's words are pinned by layout in file-comments-about-review2.test.ts)");
  assert.equal(c.presel, "", "nothing to preselect");
  const m = await save(w, aside, "Why drop the word?");
  assert.deepEqual(m.args, { note: "Why drop the word?", changeIds: ["h3"] }, "the change alone, no anchor, never suggestionId");
  const c3: StoreComment = { id: T0 + 5000 + "-" + h3.curFrom, author: "you", ts: T0 + 5000, changeIds: ["h3"], body: "Why drop the word?", replies: [], resolved: false };
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId: m.reqId, ...saved(c3) } })); await flush();
  const cc = card(aside, c3.id)!;
  assert.ok(cc, "its own card");
  assert.equal(cc.querySelector(".fc-ref")!.textContent, "removed quickly", "the change's words as its reference");
  assert.equal(cc.querySelector(".fc-kind")!.title, "A comment about a change");
  assert.deepEqual(tagsOf(cc), ["about a change"]);
  assert.deepEqual(tagsOf(card(aside, "chg:h3")!), ["1 comment"]);
});

// ── a selection over the marks ────────────────────────────────────────────────────────────────────

test("a selection inside an insertion's new text is an ordinary passage comment with the about option checked; unchecked, no changeIds; a selection over two changes' marks offers about 2 changes, in text order", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  t.after(() => { win.getSelection = () => null; });
  const { aside } = await openPanel(w);
  const mark = markOf(w, "h2");
  const words = mark.childNodes[0] as Txt;
  assert.ok(words instanceof Txt && words.data === h2.newText, "the insertion's mark wraps its text");
  win.getSelection = () => selectFrom(words, 5, words, 12);   // "the p99" inside the new text
  floatOf().click(); await flush();
  let c = composerOf(aside);
  assert.equal(c.hidden, false);
  assert.equal(c.quote, "the p99", "an ordinary passage comment on the selected words");
  assert.deepEqual(c.opt, { checked: true, label: "about this change", title: "added and the p99 by 10%" }, "the option for the change the selection lies in, checked");
  assert.equal(card(aside, "chg:h2")!.classes.includes("open"), false, "no card opened: this is a comment, not a reply on the change");
  let m = await save(w, aside, "Measured how?");
  assert.equal(m.args.anchor.quote, "the p99"); assert.deepEqual(m.args.changeIds, ["h2"]);
  assert.equal("suggestionId" in m.args, false);
  // unchecked: a passage comment like any other (the reply repainted the body: the marks and their text nodes are fresh)
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId: m.reqId, ...status() } })); await flush();
  const words2 = markOf(w, "h2").childNodes[0] as Txt;
  win.getSelection = () => selectFrom(words2, 5, words2, 12);
  floatOf().click(); await flush();
  const cb = aside.querySelector('input[data-opt="about"]')!;
  cb.checked = false; dispatch(cb, new Ev("change"));
  m = await save(w, aside, "Measured how?");
  assert.equal("changeIds" in m.args, false);
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId: m.reqId, ...status() } })); await flush();
  // a selection from inside h1's new text across to inside h2's: both changes, in text order
  const insOf = (id: string): El => { const m = w.body.querySelector('.fc-ins[data-act="fcchange"][data-id="' + id + '"]'); assert.ok(m, "the tinted new text of " + id); return m!; };
  const w1 = insOf("h1").childNodes[0] as Txt, words3 = insOf("h2").childNodes[0] as Txt;   // a substitution paints its point and its new text; the text is the tinted mark's
  assert.equal(w1.data, "cut");
  win.getSelection = () => selectFrom(w1, 1, words3, 8);
  floatOf().click(); await flush();
  c = composerOf(aside);
  assert.ok(c.quote && c.quote.startsWith("ut p95 latency by 40% and"), "the passage spans the two marks: " + c.quote);
  assert.deepEqual(c.opt, { checked: true, label: "about 2 changes", title: "reduced → cut\nadded and the p99 by 10%" });
  m = await save(w, aside, "Both numbers need a source.");
  assert.deepEqual(m.args.changeIds, ["h1", "h2"]);
  // a selection touching no mark offers no option
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId: m.reqId, ...status() } })); await flush();
  const risks = w.body.querySelectorAll(".fv-ct").find((ct) => ct.textContent.startsWith("Risks remain"))!.childNodes[0] as Txt;
  win.getSelection = () => selectFrom(risks, 0, risks, 5);
  floatOf().click(); await flush();
  c = composerOf(aside);
  assert.equal(c.quote, "Risks"); assert.equal(c.opt, null, "no change under the selection: no option");
});

test("a selection reaching a deletion's point: across it, the passage comment offers the deletion among its changes; over the struck label alone, with no text of the file in it, the composer offers the comment about that change by id and says so", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  t.after(() => { win.getSelection = () => null; });
  const { aside } = await openPanel(w);
  const del = markOf(w, "h3");
  assert.ok(del.classes.includes("fc-del") && del.childNodes.length === 0, "a deletion's mark is a point with a struck label as generated text: no text of the file in it");
  // the point sits where the passage comment's highlight begins: the text before it is the row's, the text after it the
  // highlight's first node
  const before = del.previousSibling as Txt, hl = del.nextSibling as El;
  assert.ok(before instanceof Txt && hl instanceof El && hl.classes.includes("fc-hl"), "text before the point, the passage's highlight after it");
  const after = hl.childNodes[0] as Txt;
  assert.ok(after instanceof Txt && after.data.startsWith("shipping"));
  // across the point: "recommend " before and "shipping" after
  win.getSelection = () => selectFrom(before, before.data.length - "recommend ".length, after, "shipping".length, [del]);
  floatOf().click(); await flush();
  let c = composerOf(aside);
  assert.equal(c.quote, "recommend shipping", "the words either side of the removed text");
  assert.deepEqual(c.opt, { checked: true, label: "about this change", title: "removed quickly" }, "the deletion's point lies strictly inside the selection");
  let m = await save(w, aside, "Keep the word.");
  assert.deepEqual(m.args.changeIds, ["h3"]);
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId: m.reqId, ...status() } })); await flush();
  // the label alone: the selection's ends touch the point from either side and hold no text; the mapping refuses (the
  // reply repainted the body, so the nodes are re-found)
  const del2 = markOf(w, "h3"), before2 = del2.previousSibling as Txt, after2 = (del2.nextSibling as El).childNodes[0] as Txt;
  win.getSelection = () => selectFrom(before2, before2.data.length, after2, 0, [del2]);
  floatOf().click(); await flush();
  c = composerOf(aside);
  assert.equal(c.hidden, false, "the composer opens");
  assert.equal(c.opt, null);
  assert.deepEqual(c.ref, ["fc-note:About the change ", "fc-quote:removed quickly", "fc-note:The removed text is not in the file, so the comment names the change instead of a passage."], "the comment about the change by id, the line saying why (the list layout's words)");
  m = await save(w, aside, "Why drop the word?");
  assert.deepEqual(m.args, { note: "Why drop the word?", changeIds: ["h3"] });
  // a selection ending exactly at the point does not reach across the removed text: no option
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId: m.reqId, ...status() } })); await flush();
  const before3 = markOf(w, "h3").previousSibling as Txt;
  win.getSelection = () => selectFrom(before3, before3.data.length - "recommend ".length, before3, before3.data.length - 1, []);
  floatOf().click(); await flush();
  c = composerOf(aside);
  assert.equal(c.quote, "recommend"); assert.equal(c.opt, null, "the point is at the selection's edge, not inside it");
});

// ── what the stand-in cannot show, pinned at source ──────────────────────────────────────────────

test("sources: no hosted comment in the panel or the sheets; the new acts in the delegate table and KEY_ACTS; the option's listener; the ring and the tag rules in both sheets, byte-equal", () => {
  assert.doesNotMatch(SRC, /renderHosted|fc-hosted/, "the change card hosts no comment (the about follow-on)");
  assert.doesNotMatch(SRC, /kind: "change"/, "no composer of kind change: Comment on this change is a passage composer with the about option, or the ids alone");
  assert.doesNotMatch(SRC, /suggestionId: /, "the panel never writes suggestionId");
  assert.match(SRC, /fcchangecomment: \(x, ev\) => \{ ev\.stopPropagation\(\); this\.startChangeComment\(x\.dataset\.id!\); \}/);
  assert.match(SRC, /fcaboutfirst: \(x, ev\) => \{ ev\.stopPropagation\(\); this\.showAbout\(x\.dataset\.id!\); \}/);
  assert.match(SRC, /const KEY_ACTS = new Set\(\["fccard", "fcgoto", "fcopen", "fcchange", "fclogrow", "fcaboutfirst"\]\);/, "the count tag takes Enter and Space");
  assert.match(SRC, /else if \(k === "about"\) \{ const c = this\.composer; if \(c && c\.kind === "comment" && c\.about\) c\.about\.on = t\.checked; return; \}/);
  assert.match(SRC, /if \(c\.about && c\.about\.on\) args\.changeIds = c\.about\.ids;/, "the save carries the ids when the option is on");
  assert.match(SRC, /const del = !res\.ok \|\| res\.range\.end <= res\.range\.start \? this\.deletionUnder\(sel\) : null;/, "the deletion label case is read before the mapping's verdict is trusted");
  for (const [name, css] of [["styles.css", CHAT_CSS], ["feed.css", FEED_CSS]] as const) {
    assert.doesNotMatch(css, /\.fc-hosted/, name + ": the hosted rule is gone with its element");
    assert.match(css, /\.fc-tag\.fc-about \{ color: var\(--accent\); background: var\(--accent-wash\); \}/, name + ": the about tag in the accent");
    assert.match(css, /\.fc-ins\.fc-lit, \.fc-del\.fc-lit::before \{ outline: 2px solid var\(--accent\); outline-offset: 1px; border-radius: 3px; \}/, name + ": the ring on a lit mark, the deletion's on its label");
    assert.match(css, /\.fc-about-count \{ cursor: pointer; \}/, name + ": the count tag reads as a control");
  }
  const block = (css: string) => css.slice(css.indexOf("/* ── file comments panel"), css.indexOf("/* ── end file comments panel ── */"));
  assert.equal(block(CHAT_CSS), block(FEED_CSS), "the panel block is byte-equal in both sheets");
});

// The stand-in's nodes inspect as their own projection, never as the tree: every edge (parentNode, childNodes, the
// attribute map, the listener table, style, dataset, classList) is non-enumerable, so a failing assertion's dump of a
// node is a few lines, not the whole document (ui/test-dom-shim.ts says why; ui/test-dom-shim.test.ts keeps the ratchet).
test("stand-in: a node enumerates its primitives alone and inspects without its edges", () => {
  const root = doc.createElement("div");
  const kid = root.appendChild(doc.createElement("span"));
  kid.appendChild(doc.createTextNode("leaf"));
  kid.setAttribute("data-id", "k1");
  for (const n of [root, kid, kid.firstChild!]) {
    const o = n as unknown as Record<string, unknown>;
    assert.ok(Object.keys(o).every((k) => staysEnumerable(o[k])), "only primitives enumerate on " + n.constructor.name + ": " + Object.keys(o).join(","));
    const dump = inspect(n, { compact: false, customInspect: false, depth: 1000, maxArrayLength: Infinity, showHidden: false, showProxy: false, sorted: true, getters: true });
    assert.ok(!dump.includes("parentNode") && !dump.includes("childNodes"), "no edge in the dump of " + n.constructor.name);
  }
  assert.equal(kid.parentNode, root); assert.equal(root.childNodes.length, 1); assert.equal(kid.textContent, "leaf");
  // the file's own Ev hides target and currentTarget the same way (hideEdges(this) at the end of its constructor)
  assertHiddenEvent(new Ev("click"), root, kid);
});

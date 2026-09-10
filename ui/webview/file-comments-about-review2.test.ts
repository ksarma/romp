// The about follow-on's panel, the review of 2026-09-10 (plans/file-review.md, "The about follow-on (2026-09-10)" under
// Slice 2; decision 45; section 3's rule under decision 44's neighbour), driven over the stand-in file-comments-about.test.ts
// drives (copied here, as the sibling modules copy it), with the sheet's verdict on the fold switchable so the margin layout
// can be asked for. What the round found the first stand-in lacked, pinned here:
//   • The composer's about ids follow the status (pruneAbout): a change accepted from its own card while the note is being
//     written leaves the list, so Save never posts an id the host would refuse with "reload and retry" and a retry could
//     never land. The passage composer loses its option with its last id and saves a plain passage comment; an ids-only box
//     (Comment on this change on a deletion) says the change is gone, hides Save, refuses the chord and offers Comment on
//     this file, which keeps the words; two ids pruned to one relabel the option.
//   • A selection STARTING exactly at a deletion's point offers nothing about it (the plan: the point strictly inside), a
//     case the first stand-in's "ending at the point" selection stopped one character short of.
//   • The deletion marks the selection's own range crosses count: a drag across a struck label that took a letter either
//     side is trimmed by the mapping to a range starting at the point, and by the text alone never reached across; and a
//     whitespace-only selection ending against a deletion's mark (Chromium's reading of a drag from the text into the label)
//     is the comment about that change, not the whitespace refusal with a Switch to Raw that cannot help; away from a mark
//     the refusal stands.
//   • The kind cue's title tells a comment the person made about a change from one the session answered with a change (a
//     legacy suggestionId binding), as the tag and CONTEXT.md do; the first stand-ins pinned "about" for both.
//   • The ids-only composer's line says what the layout does: laid at the change's point in the margin layout, where
//     markTop's fallback lays it; in the list layout, where no card is laid at any point, that the comment names the change
//     in a passage's place.
// Synthetic fixtures only: the notes-api world, placeholder ids, the session "api".
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
  // the inline style as a record, with the two methods the margin layout's pass writes through (setProperty, removeProperty)
  style: Record<string, any> = { setProperty(k: string, v: string) { this[k] = v; }, removeProperty(k: string) { delete this[k]; } };
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

// the sheet's verdict on the fold (file-comments.ts marginMode): the list layout unless a test asks for the margin
let marginOn = false;
(globalThis as any).getComputedStyle = (el: El) => ({ flexDirection: el.classList.contains("fileview-main") && !marginOn ? "column" : "row" });
/** A range with its boundary points, as a browser's has them (touchesMark reads them); `over` the nodes it intersects. */
const rangeAt = (anchor: Txt, a: number, focus: Txt, f: number, over: Array<El | Txt> = []) =>
  ({ ...rangeOver(...over), startContainer: anchor, startOffset: a, endContainer: focus, endOffset: f });
function selectAt(anchor: Txt, a: number, focus: Txt, f: number, over: Array<El | Txt> = []): Sel {
  return { isCollapsed: anchor === focus && a === f, anchorNode: anchor, focusNode: focus, anchorOffset: a, focusOffset: f, rangeCount: 1, getRangeAt: () => rangeAt(anchor, a, focus, f, over), toString: () => "" };
}
const composerRow = (aside: El): string | null => { const r = aside.querySelector('.fc-composer .fc-err[data-slot="composer"]'); return r ? r.querySelector("span")!.textContent : null; };
const saveButton = (aside: El): El | null => act(aside, "fcsave");
/** The tinted new text of a substitution or an insertion (a substitution paints its point and its new text; the text is the tinted mark's). */
const insOf = (w: World, id: string): El => { const m = w.body.querySelector('.fc-ins[data-act="fcchange"][data-id="' + id + '"]'); assert.ok(m, "the tinted new text of " + id); return m!; };
/** The mutate reply that decides a change: the status without it (the host drops an accepted record). */
const without = (id: string, comments: StoreComment[] = [passage]): Status => status({
  verb: "accept", storeMtimeNs: "1757145600000000009",
  store: { v: 3, path: "docs/report.md", suggestions: SUGG.filter((x) => x.id !== id), comments },
  hunks: [h1, h2, h3].filter((h) => h.id !== id),
});
/** Accept from the change's own card, the reply `reply`: a status the composer's ids are read against (pruneAbout). */
async function accept(w: World, aside: El, id: string, reply: Status): Promise<void> {
  act(card(aside, "chg:" + id)!, "fcaccept", id)!.click(); await flush();
  const m = lastOf(w, "fileComments", "accept");
  assert.ok(m && Array.isArray(m.args.ids) && m.args.ids[0] === id, "the accept of " + id + " went");
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId: m.reqId, ...reply } })); await flush(); await flush();
}
const GONE = "The change this comment was about is no longer pending: it was accepted or rejected, or the session's next edit took it into a new one.";

// ── the composer's ids follow the status (pruneAbout) ─────────────────────────────────────────────

test("an ids-only composer whose change is accepted while the note is written: the box says the change is gone, hides Save, refuses the chord with the note kept, and Comment on this file saves the words as a whole-file comment with no changeIds", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  act(card(aside, "chg:h3")!, "fcchangecomment", "h3")!.click(); await flush();
  const input = aside.querySelector(".fc-input")!;
  input.value = "Why drop the word?";
  assert.deepEqual(composerOf(aside).ref.slice(0, 2), ["fc-note:About the change ", "fc-quote:removed quickly"]);
  await accept(w, aside, "h3", without("h3"));
  const c = composerOf(aside);
  assert.equal(c.hidden, false, "the box stays open with the words");
  assert.equal(input.value, "Why drop the word?", "the note is kept");
  assert.deepEqual(c.ref, ["fc-note fc-refused:" + GONE, "fileview-btn:Comment on this file"], "the line says the change is gone, and the way out that keeps the note is offered where a refused mapping offers Switch to Raw");
  assert.equal(c.opt, null);
  assert.equal(saveButton(aside), null, "no Save: nothing to save about");
  const before = countOf(w, "fileComments", "comment");
  dispatch(input, new Ev("keydown", { key: "Enter", ctrlKey: true })); await flush();
  assert.equal(countOf(w, "fileComments", "comment"), before, "the chord posts nothing: no request with a dead id, none with none");
  assert.equal(composerRow(aside), "Nothing saved: " + GONE.slice(0, -1) + ". Comment on this file keeps the note as a comment on the whole file; Cancel drops it.");
  assert.equal(input.value, "Why drop the word?", "the refusal keeps the note where it was typed");
  // the offered way out: the words become a comment on the whole file, with no changeIds and no anchor
  (aside.querySelector('.fc-composer-ref [data-act="fcfile"]') as El).click(); await flush();
  assert.deepEqual(composerOf(aside).ref, ["fc-note:On this file"], "Comment on this file replaces the box's subject");
  assert.equal(input.value, "Why drop the word?", "…and keeps the words");
  assert.equal(composerRow(aside), null, "the refusal row went with the subject");
  const m = await save(w, aside, "Why drop the word?");
  assert.deepEqual(m.args, { note: "Why drop the word?" }, "a whole-file comment: no changeIds, no anchor");
});

test("a passage composer with the option checked whose change is accepted meanwhile loses the option and saves the plain passage comment the unchecked box would have", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  act(card(aside, "chg:h1")!, "fcchangecomment", "h1")!.click(); await flush();
  assert.deepEqual(composerOf(aside).opt, { checked: true, label: "about this change", title: "reduced → cut" });
  await accept(w, aside, "h1", without("h1"));
  const c = composerOf(aside);
  assert.equal(c.hidden, false); assert.equal(c.quote, "cut", "the passage stands");
  assert.equal(c.opt, null, "the change is gone: no option to name it");
  assert.ok(saveButton(aside), "Save stands: the passage carries the comment");
  const m = await save(w, aside, "Say cut.");
  assert.equal("changeIds" in m.args, false, "a plain passage comment: no dead id");
  assert.equal(m.args.anchor.quote, "cut");
});

test("two ids under one selection, one accepted meanwhile: the option is relabelled for the one left and Save posts that id alone", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  const t1 = insOf(w, "h1").childNodes[0] as Txt, t2 = insOf(w, "h2").childNodes[0] as Txt;
  assert.ok(t1 instanceof Txt && t2 instanceof Txt && t1.data === "cut" && t2.data.startsWith(" and the p99"));
  win.getSelection = () => selectFrom(t1, 1, t2, 8);
  floatOf().click(); await flush();
  let c = composerOf(aside);
  assert.deepEqual(c.opt, { checked: true, label: "about 2 changes", title: "reduced → cut\nadded and the p99 by 10%" }, "both changes, in text order");
  await accept(w, aside, "h2", without("h2"));
  c = composerOf(aside);
  assert.deepEqual(c.opt, { checked: true, label: "about this change", title: "reduced → cut" }, "the one left, its label singular");
  const m = await save(w, aside, "Is the p99 measured the same way?");
  assert.deepEqual(m.args.changeIds, ["h1"], "the id the status still holds, and no other");
});

test("the option unchecked survives the prune of another id; a status that holds every id changes nothing; applyStatus is the one caller", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  win.getSelection = () => selectFrom(insOf(w, "h1").childNodes[0] as Txt, 1, insOf(w, "h2").childNodes[0] as Txt, 8);
  floatOf().click(); await flush();
  const cb = aside.querySelector('input[data-opt="about"]')!;
  assert.ok(cb, "the option for the two changes");
  cb.checked = false; dispatch(cb, new Ev("change"));
  await accept(w, aside, "h2", without("h2"));
  const c = composerOf(aside);
  assert.deepEqual(c.opt, { checked: false, label: "about this change", title: "reduced → cut" }, "unchecked stays unchecked; the list is the status's");
  const m = await save(w, aside, "Plain.");
  assert.equal("changeIds" in m.args, false);
  assert.match(SRC, /this\.pruneAbout\(\);\s+\/\/ the changes the composer's comment is about/, "applyStatus prunes: the status is the event");
  assert.equal(SRC.match(/this\.pruneAbout\(\)/g)!.length, 1, "…and nothing else does");
});

// ── a deletion's point at the selection's start ───────────────────────────────────────────────────

test("a selection starting exactly at a deletion's point does not reach across the removed text: no option (the plan: the point strictly inside the range)", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  const del = markOf(w, "h3");
  const hl = del.nextSibling as El;
  const after = hl.childNodes[0] as Txt;
  assert.ok(after instanceof Txt && after.data.startsWith("shipping"), "the text after the point is the highlight's first node");
  win.getSelection = () => selectFrom(after, 0, after, "shipping".length, []);
  floatOf().click(); await flush();
  const c = composerOf(aside);
  assert.equal(c.quote, "shipping");
  assert.equal(c.opt, null, "the point is at the selection's start, not inside it");
  const m = await save(w, aside, "Ship, or release?");
  assert.equal("changeIds" in m.args, false);
});

// ── the deletion marks the selection's own range crosses or ends against ───────────────────────────

test("a drag across a struck label that takes a letter either side: the mapping trims the range to start at the point, and the mark the selection's range crosses makes the change the option's, checked; the same letters with a range crossing nothing offer nothing", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  const del = markOf(w, "h3"), before = del.previousSibling as Txt, after = (del.nextSibling as El).childNodes[0] as Txt;
  assert.ok(before.data.endsWith("recommend ") && after.data.startsWith("shipping"));
  // the space before the point and the first letter after it: " s", trimmed by the mapping to "s" at the point
  win.getSelection = () => selectFrom(before, before.data.length - 1, after, 1, [del]);
  floatOf().click(); await flush();
  const c = composerOf(aside);
  assert.equal(c.quote, "s", "the letter the drag took after the point; the space before it is trimmed");
  assert.deepEqual(c.opt, { checked: true, label: "about this change", title: "removed quickly" }, "the pointer reached across the label: the change is offered, checked");
  const m = await save(w, aside, "Keep the word.");
  assert.deepEqual(m.args.changeIds, ["h3"]);
  assert.equal(m.args.anchor.quote, "s", "an ordinary passage comment on the selected letter");
  // the same letters with the range NOT crossing the mark (a stand-in's range with no such node): the text's verdict alone
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId: m.reqId, ...status() } })); await flush();
  const del2 = markOf(w, "h3"), before2 = del2.previousSibling as Txt, after2 = (del2.nextSibling as El).childNodes[0] as Txt;
  win.getSelection = () => selectFrom(before2, before2.data.length - 1, after2, 1, []);
  floatOf().click(); await flush();
  assert.equal(composerOf(aside).opt, null, "by the text alone the trimmed range starts at the point: nothing");
});

test("a whitespace-only selection ending against a deletion's mark is the comment about that change, the end spelled on the text node or on the parent; the same selection away from any mark is the whitespace refusal with Switch to Raw", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  const del = markOf(w, "h3"), before = del.previousSibling as Txt;
  // Chromium's reading of a drag from the text into the label: the one space before the mark, the range's end drawn back to
  // the text node's last offset — before the span, which the range therefore does not intersect
  win.getSelection = () => selectAt(before, before.data.length - 1, before, before.data.length, []);
  floatOf().click(); await flush();
  let c = composerOf(aside);
  assert.equal(c.hidden, false);
  assert.deepEqual(c.ref.slice(0, 2), ["fc-note:About the change ", "fc-quote:removed quickly"], "the label was the target: the comment about the change by id");
  assert.equal(c.opt, null);
  let m = await save(w, aside, "Why drop the word?");
  assert.deepEqual(m.args, { note: "Why drop the word?", changeIds: ["h3"] });
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId: m.reqId, ...status() } })); await flush();
  // the range's end as the parent's own child index, the other spelling of the same position
  const del2 = markOf(w, "h3"), before2 = del2.previousSibling as Txt, row = del2.parentNode!;
  const k = row.childNodes.indexOf(del2);
  win.getSelection = () => ({ ...selectAt(before2, before2.data.length - 1, before2, before2.data.length, []), getRangeAt: () => ({ ...rangeOver(), startContainer: before2, startOffset: before2.data.length - 1, endContainer: row, endOffset: k }) } as unknown as Sel);
  floatOf().click(); await flush();
  c = composerOf(aside);
  assert.deepEqual(c.ref.slice(0, 2), ["fc-note:About the change ", "fc-quote:removed quickly"], "the same position, spelled on the parent");
  m = await save(w, aside, "Why drop the word?");
  assert.deepEqual(m.args.changeIds, ["h3"]);
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId: m.reqId, ...status() } })); await flush();
  // a space with no mark against it: the mapping's refusal, as ever
  const risks = w.code.querySelectorAll(".fv-ct").find((ct) => ct.textContent.startsWith("Risks remain"))!;
  const rt = risks.childNodes[0] as Txt;
  assert.ok(rt instanceof Txt);
  win.getSelection = () => selectAt(rt, "Risks".length, rt, "Risks".length + 1, []);
  floatOf().click(); await flush();
  c = composerOf(aside);
  assert.deepEqual(c.ref, ["fc-note fc-refused:The selection is only whitespace.", "fileview-btn:Switch to Raw"], "no mark under it: the refusal stands");
});

test("a whitespace-only selection whose range starts right after a deletion's mark counts too (a drag out of the label into the text after it)", async (t: TestContext) => {
  const src2 = DOC.replace("Risks remain", "Risks  remain");   // two spaces: the point between them, a space either side
  const w = world({ src: src2 }); t.after(() => w.close());
  const at2 = src2.indexOf("  remain") + 1;
  const h4 = H("h4", "del", at2, at2, "still ", "", T0 - 60000);
  const { aside } = await openPanel(w, status({ hunks: [h1, h2, h3, h4], store: { v: 3, path: "docs/report.md", suggestions: [...SUGG, { id: "h4", author: "api", ts: T0 - 60000, kind: "del", from: at2, oldText: "still " }], comments: [passage] } }));
  const del4 = markOf(w, "h4"), after4 = del4.nextSibling as Txt;
  assert.ok(after4 instanceof Txt && after4.data.startsWith(" remain"), "the text after the point begins with the second space");
  win.getSelection = () => selectAt(after4, 0, after4, 1, []);
  floatOf().click(); await flush();
  assert.deepEqual(composerOf(aside).ref.slice(0, 2), ["fc-note:About the change ", "fc-quote:removed still"], "the range starts against the mark: the change is what was selected");
  const m = await save(w, aside, "Still?");
  assert.deepEqual(m.args, { note: "Still?", changeIds: ["h4"] });
});

// ── the kind cue's title ──────────────────────────────────────────────────────────────────────────

test("the kind cue's title: a comment with no passage the person made about a change reads about; one the session answered with a change (a legacy suggestionId binding) reads answered, as its tag does; both sources together read about", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const about: StoreComment = { id: T0 + 3000 + "-9", author: "you", ts: T0 + 3000, body: "Why this one?", changeIds: ["h2"], replies: [], resolved: false };
  const both: StoreComment = { id: T0 + 4000 + "-11", author: "you", ts: T0 + 4000, body: "Both.", changeIds: ["h2"], suggestionId: "h1", replies: [], resolved: false };
  const { aside } = await openPanel(w, status({ store: { v: 3, path: "docs/report.md", suggestions: SUGG, comments: [passage, legacy, about, both] } }));
  const title = (id: string): string => card(aside, id)!.querySelector(".fc-kind")!.title;
  assert.equal(title(legacy.id), "A comment the session answered with a change", "the session's binding: answered, never about");
  assert.deepEqual(tagsOf(card(aside, legacy.id)!), ["answered by a change", "1"], "…as the tag says");
  assert.equal(title(about.id), "A comment about a change", "the person's pick");
  assert.deepEqual(tagsOf(card(aside, about.id)!), ["about a change"]);
  assert.equal(title(both.id), "A comment about a change", "a pick of the person's makes it about, whatever else answered it");
  assert.deepEqual(tagsOf(card(aside, both.id)!), ["about a change", "answered by a change"]);
  assert.equal(title(passage.id), "A comment on a passage", "a passage comment keeps its kind whatever it names");
  assert.equal(card(aside, legacy.id)!.querySelector(".fc-kind")!.textContent, "Comment", "the cue's word is the same; the title tells them apart");
});

// ── the ids-only composer's line, by layout ───────────────────────────────────────────────────────

test("the ids-only composer's line in the list layout: the comment names the change in a passage's place (no card is laid at any point there)", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  assert.ok(!aside.classes.includes("fc-margin"), "the list layout");
  act(card(aside, "chg:h3")!, "fcchangecomment", "h3")!.click(); await flush();
  assert.deepEqual(composerOf(aside).ref, ["fc-note:About the change ", "fc-quote:removed quickly", "fc-note:The removed text is not in the file, so the comment names the change instead of a passage."]);
});

test("the ids-only composer's line in the margin layout: the comment is laid at the change's point (markTop's fallback); the margin's words are the ones the guide's pin and the browser leg read", async (t: TestContext) => {
  marginOn = true; t.after(() => { marginOn = false; });
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  assert.ok(aside.classes.includes("fc-margin"), "the margin layout");
  act(card(aside, "chg:h3")!, "fcchangecomment", "h3")!.click(); await flush();
  assert.deepEqual(composerOf(aside).ref, ["fc-note:About the change ", "fc-quote:removed quickly", "fc-note:The removed text is not in the file, so the comment is laid at the change's point."]);
  assert.match(SRC, /this\.margin \? "The removed text is not in the file, so the comment is laid at the change's point\."\s*: "The removed text is not in the file, so the comment names the change instead of a passage\."/);
});

test("a whitespace-only selection ending against a deletion's mark from inside an adjoining mark (an insertion whose tinted span ends where the deletion's point stands): the boundary at the span's edge is the mark's neighbour, and the comment is about the deletion", async (t: TestContext) => {
  const src2 = DOC.replace("Next steps: measure again.", "Next steps: measure soon again.");
  const w = world({ src: src2 }); t.after(() => w.close());
  const at6 = src2.indexOf("soon ");
  const h6 = H("h6", "ins", at6, at6 + "soon ".length, "", "soon ", T0 - 50000);
  const h7 = H("h7", "del", at6 + "soon ".length, at6 + "soon ".length, "now ", "", T0 - 40000);
  const { aside } = await openPanel(w, status({ hunks: [h1, h2, h3, h6, h7], store: { v: 3, path: "docs/report.md", suggestions: [...SUGG,
    { id: "h6", author: "api", ts: T0 - 50000, kind: "ins", from: at6, oldText: "", newText: "soon " }, { id: "h7", author: "api", ts: T0 - 40000, kind: "del", from: h7.curFrom, oldText: "now " }], comments: [passage] } }));
  const ins = insOf(w, "h6"), del7 = markOf(w, "h7");
  const insTxt = ins.childNodes[0] as Txt;
  assert.ok(insTxt instanceof Txt && insTxt.data === "soon ", "the insertion's text is the tinted span's");
  assert.equal(del7.previousSibling, ins, "the deletion's point stands right after the insertion's span");
  // Chromium's reading of a drag from the insertion's last letters into the label: the trailing space, the end at the span's
  // text's last offset, a node the deletion's parent does not hold directly
  win.getSelection = () => selectAt(insTxt, 4, insTxt, 5, []);
  floatOf().click(); await flush();
  const c = composerOf(aside);
  assert.deepEqual(c.ref.slice(0, 2), ["fc-note:About the change ", "fc-quote:removed now"], "the boundary climbs to the span, the mark's neighbour");
  const m = await save(w, aside, "Now, or soon?");
  assert.deepEqual(m.args, { note: "Now, or soon?", changeIds: ["h7"] });
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

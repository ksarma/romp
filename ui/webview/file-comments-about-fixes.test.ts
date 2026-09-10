// The about follow-on's panel, the review of 2026-09-10 (plans/file-review.md, "The about follow-on (2026-09-10)" under
// Slice 2; decision 45): what the first stand-in (file-comments-about.test.ts) left unpinned, driven over the same Slice 2
// stand-in with the viewer's edit mode added (the editing suites' seam: text() answers the buffer while editing). Pinned:
//   • Comment on this change while the editor is up cuts the span from the text the change's offsets index (the file as the
//     editor loaded it), never the buffer, which unsaved keystrokes move under the offsets — before, ten characters typed
//     above the change made the composer quote and Save anchor other words, tagged about the change.
//   • Comment on this change is withheld for a substitution or an insertion while the view's bytes are not the status's
//     (a reject's reply before its reload, the poll's reload before its status) and in media mode, and stands for a
//     deletion: before, the spanned change took the deletion's by-id composer, its line ("The removed text is not in the
//     file") false for it, and Save wrote a comment with no passage though the change has one.
//   • A refused selection that holds text of the file and happens to cross one deletion's mark shows the refusal (Switch to
//     Raw), not a comment about that deletion; a selection holding no text is the label-alone case as before.
//   • A BOM file: the host's offsets run one ahead of the view's, and both Comment on this change and the about option
//     follow the shift (the span is the change's text; a selection over the change's first character offers the option,
//     one beginning at the change's end does not).
//   • deletionUnder claims one mark alone: two adjacent deletion labels under a text-less selection are the mapping's
//     refusal, not a comment about the first.
//   • The open card names the changes the comment is about in words (the tag's title, which never reaches touch, and the
//     hover lighting, which the keyboard has no way to), a change the file no longer records among them; a legacy comment a
//     change answered has no such line, its answering revision standing among its turns.
//   • The decision tag's title says "about", one change or N, for the person's own pick; a legacy binding keeps its words.
// Synthetic fixtures only: the notes-api world, placeholder ids, the session "api".
import { test, type TestContext } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import type { FileViewActionCtx, TrackedEdit } from "./file-view";
import { type Status, type Hunk, type StoreComment, type LogEntry } from "./file-comments-model";

const web = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const SRC = web("file-comments.ts");

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
/** The tree's edges as non-enumerable properties: a failing assertion over a stand-in node would otherwise have node's
 *  assert walk the whole cyclic tree for its diff and allocate without bound (the box's finding of 2026-09-09; the shim
 *  migration's hideEdges). The tests here compare extracted fields, never two nodes, and this is the backstop. */
function hideEdges(n: { parentNode?: unknown; childNodes?: unknown }, withKids: boolean): void {
  Object.defineProperty(n, "parentNode", { value: null, writable: true, enumerable: false, configurable: true });
  if (withKids) Object.defineProperty(n, "childNodes", { value: [], writable: true, enumerable: false, configurable: true });
}
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
  parentNode!: El | null;
  constructor(public data: string) { hideEdges(this, false); }
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
  constructor(tag: string) { this.tagName = tag.toUpperCase(); hideEdges(this, true); }
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
  editing: boolean; buffer: string | null; tracked: TrackedEdit | null; mode: "raw" | "media";
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
    editing: false, buffer: null, tracked: null, mode: "raw",
  } as World;
  rows(code, text);
  w.setText = (s) => { text = s; rows(code, s); for (const cb of w.hooks.rendered) cb(); };
  w.ctx = {
    path: ABS, sid: SID, todoId: over.todoId ?? null,
    body: () => body as unknown as HTMLElement, mode: () => w.mode,
    text: () => (w.editing && w.buffer !== null ? w.buffer : text),   // the viewer's seam: the buffer while editing (file-view.ts)
    mtimeNs: () => w.viewMtime, media: () => null, mediaElement: () => null, renderedImages: () => [], pdfPages: () => [],
    identity: () => ({ name: "api", color: null }),
    onRendered: (cb) => { w.hooks.rendered.push(cb); }, onSelection: () => { /* inert */ },
    onSaved: () => { /* inert */ }, onClose: (cb) => { w.hooks.close.push(cb); },
    post: (m) => { w.posted.push(m); }, ensureEditingAllowed: async () => true, setEditBlocked: () => { /* inert */ }, editing: () => w.editing, setTrackedEdit: (t) => { w.tracked = t; }, guardClose: () => { /* inert */ },
    aside: (node) => { main.querySelector(".fileview-aside")?.remove(); if (node) { const n = node as unknown as El; n.classList.add("fileview-aside"); main.appendChild(n); } },
    setMode: (m) => { w.modes.push(m); }, scrollToOffset: (n) => { w.scrolls.push(n); },
    // fetchFile: the bytes and mtime now on disk, repainted, the seam's onRendered fired
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
/** `text`: what the selection's string holds — the file text under it, or nothing over a deletion's struck label alone (generated text never enters it). */
function selectFrom(anchor: Txt, a: number, focus: Txt, f: number, over: Array<El | Txt> = [], text = ""): Sel {
  return { isCollapsed: anchor === focus && a === f, anchorNode: anchor, focusNode: focus, anchorOffset: a, focusOffset: f, rangeCount: 1, getRangeAt: () => rangeOver(anchor, focus, ...over), toString: () => text };
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
// ── Comment on this change under the editor ───────────────────────────────────────────────────────

test("Comment on this change while the editor is up cuts the span from the text the offsets index, not the buffer: characters typed above the change, the composer still quotes the change's text, wears no passage-changed tag, and Save posts the anchor over it", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  assert.ok(w.tracked, "the seam's tracked-edit hook is set at mount");
  // Edit: begin() at the click (editing() still false), then the viewer flips into edit mode and repaints once as the editor
  // takes the body (enterEdit); then the person types above the change, unsaved
  w.tracked!.begin();
  w.editing = true; w.buffer = "Typed here, unsaved. " + DOC;
  for (const cb of w.hooks.rendered) cb();
  const c1 = card(aside, "chg:h1")!;
  assert.ok(act(c1, "fcchangecomment", "h1"), "the button is offered under the editor");
  assert.equal(act(c1, "fcreveal"), null, "Reveal is not (Slice 5)");
  act(c1, "fcchangecomment", "h1")!.click(); await flush();
  const c = composerOf(aside);
  assert.equal(c.hidden, false);
  assert.equal(c.quote, "cut", "the change's own text, cut from the file as the editor loaded it (before: the buffer's bytes at the file's offsets)");
  assert.equal(aside.querySelector(".fc-composer-ref .fc-tag"), null, "no passage-changed tag: the composer's text is the one the offsets index");
  assert.deepEqual(c.opt, { checked: true, label: "about this change", title: "reduced → cut" });
  const m = await save(w, aside, "Keep reduced; the abstract uses it.");
  assert.deepEqual(m.args, { note: "Keep reduced; the abstract uses it.", anchor: { quote: "cut", prefix: DOC.slice(at("cut") - 24, at("cut")), suffix: DOC.slice(at("cut") + 3, at("cut") + 27) }, hintOffset: at("cut"), changeIds: ["h1"] },
    "the anchor over the change's text in the file, with its id");
});

// ── the view's bytes are not the status's ─────────────────────────────────────────────────────────

test("Comment on this change is withheld for a substitution or an insertion while the view's bytes are not the status's, and in media mode, and stands for a deletion; it comes back with the bytes", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  const offered = (): boolean[] => ["h1", "h2", "h3"].map((id) => !!act(card(aside, "chg:" + id)!, "fcchangecomment", id));
  assert.deepEqual(offered(), [true, true, true], "the view current: every change");
  // the poll's reload landed before its status: the view repaints with the other bytes' mtime
  w.viewMtime = "1757145600000000099"; w.setText(w.disk);
  assert.deepEqual(offered(), [false, false, true], "in flux: the spanned changes offer none (over other bytes the span names the wrong words, and a comment by id alone loses the passage the change has); the deletion's is by id and stands");
  assert.deepEqual(texts(card(aside, "chg:h1")!.querySelectorAll(".fc-actions button")), ["Accept", "Reject"], "Accept and Reject stay");
  w.viewMtime = "1757145600000000001"; w.setText(w.disk);
  assert.deepEqual(offered(), [true, true, true], "the bytes landed: offered again");
  // the picture of a media file shows no text to anchor in
  w.mode = "media"; w.setText(w.disk);
  assert.deepEqual(offered(), [false, false, true], "media: no text to cut the span from; the deletion's by id");
});

// ── a refused selection holding text, with a deletion's mark under it ─────────────────────────────

test("a selection the mapping refuses that holds text of the file and crosses one deletion's mark shows the refusal with Switch to Raw, not a comment about the deletion, and Save posts nothing; the same drag holding no text is the label-alone case", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  t.after(() => { win.getSelection = () => null; });
  const { aside } = await openPanel(w);
  const del = markOf(w, "h3");
  const hl = del.nextSibling as El; const after = hl.childNodes[0] as Txt;
  assert.ok(after instanceof Txt && after.data.startsWith("shipping"));
  // the drag begins outside the file text (a node in the body row, outside code.hljs) and ends after "shipping", crossing the mark
  const outside = new El("div"); outside.className = "fileview-note"; const ot = new Txt("Outside the file text"); outside.appendChild(ot); w.body.appendChild(outside);
  win.getSelection = () => selectFrom(ot, 0, after, "shipping".length, [del], "Outside the file text\nWe recommend shipping");
  floatOf().click(); await flush();
  let c = composerOf(aside);
  assert.equal(c.hidden, false, "the composer opens");
  assert.ok(c.ref.some((x) => x.endsWith("fc-refused:The selection reaches outside the file text.")), "the mapping's refusal: " + JSON.stringify(c.ref));
  assert.ok(c.ref.some((x) => x.endsWith(":Switch to Raw")), "…with its way out");
  assert.ok(!c.ref.some((x) => x.includes("About the change")), "no comment about the deletion in the refusal's place: the person selected a passage");
  assert.equal(c.opt, null);
  const input = aside.querySelector(".fc-input")!;
  input.value = "Probe."; dispatch(input, new Ev("keydown", { key: "Enter", ctrlKey: true })); await flush();
  assert.equal(countOf(w, "fileComments", "comment"), 0, "a refused mapping saves nothing");
  // the same drag with no text of the file in it: the label alone is what was selected
  win.getSelection = () => selectFrom(ot, 0, after, 0, [del], "");
  floatOf().click(); await flush();
  c = composerOf(aside);
  assert.deepEqual(c.ref, ["fc-note:About the change ", "fc-quote:removed quickly", "fc-note:The removed text is not in the file, so the comment is laid at the change's point."], "no text held: the comment about the change by id");
});

// ── a BOM file ────────────────────────────────────────────────────────────────────────────────────

test("a BOM file: the host's offsets run one ahead of the view's, and Comment on this change and the about option follow them — the span is the change's text, a selection over the change's first character offers the option, one beginning at the change's end does not", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  t.after(() => { win.getSelection = () => null; });
  const shift = (h: Hunk): Hunk => ({ ...h, curFrom: h.curFrom + 1, curTo: h.curTo + 1, baseFrom: h.baseFrom + 1, baseTo: h.baseTo + 1 });
  const bom = status({ bom: true, hunks: [shift(h1), shift(h2), shift(h3)] });
  const { aside } = await openPanel(w, bom);
  act(card(aside, "chg:h1")!, "fcchangecomment", "h1")!.click(); await flush();
  const c0 = composerOf(aside);
  assert.equal(c0.quote, "cut", "the span one back from the host's offsets (unshifted it would read 'ut ')");
  assert.equal(c0.presel, "cut");
  const m = await save(w, aside, "Keep reduced.");
  assert.equal(m.args.anchor.quote, "cut"); assert.equal(m.args.hintOffset, at("cut")); assert.deepEqual(m.args.changeIds, ["h1"]);
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId: m.reqId, ...bom } })); await flush();
  // the row's own text: the painters verify each change's text at its offsets before painting, and over a BOM file's stripped
  // text the host's offsets do not verify, so no mark splits the row (the changes are card-only, each with Reveal)
  const ct = w.body.querySelectorAll(".fv-ct").find((x) => x.textContent.startsWith("The api session"))!;
  assert.equal(ct.querySelectorAll("[data-act=\"fcchange\"]").length, 0, "no change mark in the row");
  // the row's text node holding `needle`, and the needle's index in it (the composer's presel splits the row's text as it opens)
  const textAt = (needle: string): [Txt, number] => { const tn = ct.childNodes.find((n) => n instanceof Txt && n.data.includes(needle)) as Txt | undefined; assert.ok(tn, needle + " in the row's text"); return [tn!, tn!.data.indexOf(needle)]; };
  const [t1, i] = textAt("cut");
  win.getSelection = () => selectFrom(t1, i, t1, i + 1, [], "c");
  floatOf().click(); await flush();
  let c = composerOf(aside);
  assert.equal(c.quote, "c");
  assert.deepEqual(c.opt, { checked: true, label: "about this change", title: "reduced → cut" }, "the change's first character: inside it once the offsets are shifted (unshifted, the selection would end where the change begins and offer nothing)");
  const [t2, k] = textAt("10%.");                     // the "." right after the insertion's new text
  const j = k + 3;
  win.getSelection = () => selectFrom(t2, j, t2, j + 1, [], ".");
  floatOf().click(); await flush();
  c = composerOf(aside);
  assert.equal(c.quote, ".");
  assert.equal(c.opt, null, "a selection beginning at the insertion's end overlaps nothing (unshifted, it would be read as inside the insertion)");
});

// ── two deletion labels under one selection ──────────────────────────────────────────────────────

test("deletionUnder claims one mark alone: a selection over two adjacent deletion labels with no text of the file in it is the mapping's refusal, not a comment about the first; over one label it is the comment about that change", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  t.after(() => { win.getSelection = () => null; });
  const h4 = H("h4", "del", at("shipping"), at("shipping"), "very ", "", T0 - 60000);
  const base = status();
  const { aside } = await openPanel(w, status({ hunks: [h1, h2, h3, h4], store: { ...base.store!, suggestions: [...SUGG, { id: "h4", author: "api", ts: T0 - 60000, kind: "del", from: h3.curFrom, oldText: "very " }] } }));
  const d3 = markOf(w, "h3"), d4 = markOf(w, "h4");
  assert.ok(d3.parentNode && d3.parentNode === d4.parentNode, "two labels at one point: siblings");
  const kids = d3.parentNode!.childNodes;
  const first = Math.min(kids.indexOf(d3), kids.indexOf(d4)), last = Math.max(kids.indexOf(d3), kids.indexOf(d4));
  assert.equal(last - first, 1, "adjacent");
  const before = kids[first - 1] as Txt, hl = kids[last + 1] as El;
  assert.ok(before instanceof Txt && hl instanceof El && hl.classes.includes("fc-hl"), "text before the labels, the passage's highlight after them");
  const after = hl.childNodes[0] as Txt;
  win.getSelection = () => selectFrom(before, before.data.length, after, 0, [d3, d4], "");
  floatOf().click(); await flush();
  let c = composerOf(aside);
  assert.equal(c.hidden, false);
  assert.equal(c.opt, null);
  assert.ok(c.ref.some((x) => x.endsWith("fc-refused:Select some text to comment on.")), "two marks: nothing to claim, the mapping's refusal stands: " + JSON.stringify(c.ref));
  assert.ok(!c.ref.some((x) => x.includes("About the change")));
  const input = aside.querySelector(".fc-input")!;
  input.value = "Probe."; dispatch(input, new Ev("keydown", { key: "Enter", ctrlKey: true })); await flush();
  assert.equal(countOf(w, "fileComments", "comment"), 0, "nothing saved");
  win.getSelection = () => selectFrom(before, before.data.length, after, 0, [d4], "");
  floatOf().click(); await flush();
  c = composerOf(aside);
  assert.deepEqual(c.ref, ["fc-note:About the change ", "fc-quote:removed very", "fc-note:The removed text is not in the file, so the comment is laid at the change's point."], "one label: the comment about that change");
});

// ── the open card's words for the changes it names ────────────────────────────────────────────────

test("the open card names the changes the comment is about in words, the tag's title's own: the person's pick, a change the file no longer records among them; a legacy comment a change answered shows the revision as a turn instead; a comment naming none has no line, and the collapsed card has the tag alone", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const about: StoreComment = { id: T0 + 3000 + "-17", author: "you", ts: T0 + 3000, body: "Both numbers need a source.", anchor: { quote: "cut p95 latency by 40%", prefix: "The api session ", suffix: " and the p99 by 10%." }, anchorAt: at("cut"), changeIds: ["h1", "h2"], replies: [], resolved: false };
  const gone: StoreComment = { id: T0 + 4000 + "-90", author: "you", ts: T0 + 4000, body: "Cite the run.", anchor: { quote: "Risks remain", prefix: "", suffix: " in the fallback path." }, anchorAt: at("Risks"), changeIds: ["zz"], replies: [], resolved: false };
  const base = status();
  const { aside } = await openPanel(w, status({ store: { ...base.store!, comments: [passage, legacy, about, gone] } }));
  const open = (id: string): El => { card(aside, id)!.querySelector(".fc-card-head")!.click(); return card(aside, id)!; };
  const notes = (c: El): string[] => texts(c.querySelectorAll(".fc-about-note"));
  assert.deepEqual(notes(card(aside, about.id)!), [], "collapsed: the tag alone");
  assert.deepEqual(notes(open(about.id)), ["This comment is about: reduced → cut (pending); added and the p99 by 10% (pending)"], "open: which changes, their words and states");
  assert.equal(card(aside, about.id)!.querySelector(".fc-tag.fc-about")!.title, notes(card(aside, about.id)!)[0], "the tag's title's own words");
  assert.ok(card(aside, about.id)!.querySelector(".fc-about-note")!.classes.includes("fc-note"), "in the note's dress, like the region tags' open-card words");
  const l = open(legacy.id);
  assert.deepEqual(notes(l), [], "a legacy comment a change answered has no line: the answering revision is among its turns");
  assert.ok(l.querySelectorAll(".fc-reply").some((r) => r.textContent.includes("cut") && r.textContent.includes("trimmed")), "the revision's old and new text, in the open card");
  const g = open(gone.id);
  assert.deepEqual(tagsOf(g), ["about a change"]);
  assert.equal(g.querySelector(".fc-tag.fc-about")!.title, "This comment is about: a change the file no longer records (no longer recorded)", "a change in no hunk, no detached op and no log entry: its words, rendered");
  assert.deepEqual(notes(g), ["This comment is about: a change the file no longer records (no longer recorded)"]);
  assert.deepEqual(notes(open(passage.id)), [], "a comment naming no change has no line");
  card(aside, about.id)!.querySelector(".fc-card-head")!.click();
  assert.deepEqual(notes(card(aside, about.id)!), [], "folded again: the tag alone");
});

// ── the decision tag's title ──────────────────────────────────────────────────────────────────────

test("the decision tag on a comment whose named changes the person decided alike: the title says about, one change or N; a legacy binding keeps the words it had", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const both: StoreComment = { id: T0 + 3000 + "-17", author: "you", ts: T0 + 3000, body: "Both numbers need a source.", anchor: { quote: "cut p95 latency by 40%", prefix: "The api session ", suffix: " and the p99 by 10%." }, anchorAt: at("cut"), changeIds: ["h1", "h2"], replies: [], resolved: false };
  const one: StoreComment = { id: T0 + 3500 + "-60", author: "you", ts: T0 + 3500, body: "Measured how?", anchor: { quote: "the p99", prefix: "y by 40% and ", suffix: " by 10%." }, anchorAt: at("the p99"), changeIds: ["h2"], replies: [], resolved: false };
  const log: LogEntry = { ts: "2026-09-10T08:01:00Z", kind: "accept", author: "you", changes: [{ id: "h1", oldText: "reduced", newText: "cut" }, { id: "h2", oldText: "", newText: h2.newText }] };
  const { aside } = await openPanel(w, status({ hunks: [h3], store: { v: 3, path: "docs/report.md", suggestions: [SUGG[2]], comments: [legacy, both, one] }, log: [log] }));
  const title = (id: string): string => { const tag = card(aside, id)!.querySelectorAll(".fc-card-head .fc-tag").find((x) => x.textContent === "accepted"); assert.ok(tag, id + " wears the decision"); return tag!.title; };
  assert.equal(title(both.id), "You accepted the 2 changes this comment is about");
  assert.equal(title(one.id), "You accepted the change this comment is about");
  assert.equal(title(legacy.id), "You accepted the change this comment is on", "a legacy binding (the format's suggestionId): the words it had");
});

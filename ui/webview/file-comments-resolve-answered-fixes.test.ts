// Resolve answered, the review of 2026-09-10 (plans/file-review.md, "The about follow-on (2026-09-10)" under Slice 2;
// decision 46): what the first stand-in (file-comments-resolve-answered.test.ts) left unpinned, driven over the same Slice 2
// stand-in. Pinned:
//   • The confirm row is over once the status it was asked over leaves nothing for it: the answered comments resolved from
//     their own cards take the count to zero, and a status that answers two more shows the header action and NO confirm;
//     nor does the confirm survive the panel's close. Before, the flag was cleared by Resolve and Cancel alone, and a
//     question the person walked away from came back re-counted, one click from resolving with no gesture behind it.
//   • The file-editing consent is asked once for a Resolve answered and once for a Reopen all: declined, one row under the
//     header action and nothing written; granted, the writes go with no second ask. Before, every write asked, and a decline
//     was asked again for each comment and left one identical row per comment at the list's foot.
//   • The Reopen all line wears the acknowledgment's dress with the size on the words and the button alone (a .fc-note
//     inside a .fc-note compounded to 0.74 of the acknowledgment beside it), and borrows nothing from the saved line
//     (.fc-saved is that line's own, one class string in the panel: feed-css-saved-line-head-dress.test.ts); in the list
//     layout it stands under the header, and in the margin layout in the Send section, where it sticks to the section's
//     bottom edge, as the saved line does.
//   • A wheel while Reopen all holds the keyboard ends the offer and moves the focus to the nearest control, never to the
//     body (removeLine's rule for the saved line).
// Synthetic fixtures only: the notes-api world, placeholder ids, the sessions "api" and "web".
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

// ── fixtures: the notes-api world ──────────────────────────────────────────────────────────────────
const SID = "11111111-2222-3333-4444-555555555555";
const SID2 = "11111111-2222-3333-4444-666666666666";
const ABS = "/repo/notes-api/docs/report.md";
const ROOT = "/repo/notes-api";
const STORE_PATH = ROOT + "/.trackchanges/docs%2Freport.md.json";
const T0 = 1757145600000;
const DOC = "# Report\n\n## Findings\nThe api session cut p95 latency by 40% and the p99 by 10%.\n\n"
  + "We recommend shipping the cache in v1.2.\n\nRisks remain in the fallback path.\n\nNext steps: measure again.\n";
const at = (needle: string, from = 0): number => { const i = DOC.indexOf(needle, from); assert.ok(i >= 0, needle); return i; };
const H = (id: string, kind: Hunk["kind"], from: number, to: number, oldText: string, newText: string, ts = T0 - 90000): Hunk =>
  ({ id, author: "api", ts, kind, curFrom: from, curTo: to, baseFrom: from, baseTo: from + oldText.length, oldText, newText, anchor: null });
const h1 = H("h1", "sub", at("cut"), at("cut") + 3, "reduced", "cut");
const SUGG = [{ id: "h1", author: "api", authorId: SID, ts: T0 - 90000, kind: "sub", from: h1.curFrom, oldText: "reduced", newText: "cut" }];
const reply = (author: string, ts: number, body: string) => ({ author, authorId: author === "you" ? undefined : SID, ts, body });
const edit = (ts: number) => ({ author: "api", authorId: SID, ts, kind: "edit", oldText: "cut", newText: "trimmed" });
/** The person's comment the session answered in words. */
const answered: StoreComment = { id: T0 + "-118", author: "you", ts: T0, body: "Which cache? Say which.", anchor: { quote: "shipping the cache in v1.2", prefix: "We recommend ", suffix: "." },
  replies: [reply("api", T0 + 1000, "The response cache; the sentence names it now.")], resolved: false };
/** The person's comment the session answered with a revision (a turn of kind edit), no words. */
const revised: StoreComment = { id: T0 + 2000 + "-5", author: "you", ts: T0 + 2000, body: "Say cut, not reduced.", changeIds: ["h1"], replies: [edit(T0 + 3000)], resolved: false };
/** The person's comment with the person's own word last: the session's reply came before it. */
const mineLast: StoreComment = { id: T0 + 4000 + "-40", author: "you", ts: T0 + 4000, body: "Cite the run.", anchor: { quote: "Risks remain", prefix: "", suffix: " in the fallback path." },
  replies: [reply("api", T0 + 4100, "Done."), reply("you", T0 + 4200, "Which run, though?")], resolved: false };
/** The person's comment nobody answered. */
const open: StoreComment = { id: T0 + 5000 + "-0", author: "you", ts: T0 + 5000, body: "Add a summary at the top.", replies: [], resolved: false };
/** The session's own comment the person answered: not the person's to resolve in bulk. */
const theirs: StoreComment = { id: T0 + 6000 + "-60", author: "api", authorId: SID, ts: T0 + 6000, body: "Is the p99 number final?", anchor: { quote: "p99 by 10%", prefix: "by 40% and the ", suffix: "." },
  replies: [reply("you", T0 + 6100, "Yes.")], resolved: false };
/** The person's answered comment already resolved. */
const done: StoreComment = { ...answered, id: T0 + 7000 + "-7", ts: T0 + 7000, replies: [reply("web", T0 + 7100, "Fixed.")], resolved: true };
const ALL = [answered, revised, mineLast, open, theirs, done];
function status(over: Partial<Status> = {}): Status {
  return {
    verb: "status", root: ROOT, storePath: STORE_PATH, trackedBy: { kind: "file", entry: "docs/report.md" }, agentTooling: "present",
    fileMtimeNs: "1757145600000000001", storeMtimeNs: "1757145600000000002", configMtimeNs: "1757145600000000003",
    store: { v: 3, path: "docs/report.md", suggestions: SUGG, comments: ALL },
    hunks: [h1], log: [],
    unsent: { comments: [], replies: [], accepted: 0, rejected: 0, watermark: null },
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
// the sheet's verdict on the fold (file-comments.ts marginMode): the list layout unless a test asks for the margin
let marginOn = false;
(globalThis as any).getComputedStyle = (el: El) => ({ flexDirection: el.classList.contains("fileview-main") && !marginOn ? "column" : "row" });
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
const headBtn = (aside: El): El | null => act(aside, "fcresolveanswered");
const confirmRow = (aside: El): El | null => act(aside, "fcresolveanswereddo")?.parentNode || null;
const reopen = (aside: El): El | null => act(aside, "fcreopenall");
const resolves = (w: World) => w.posted.filter((m) => m.type === "fileComments" && m.verb === "resolve").map((m) => m.args);
const resolvedAll = (ids: string[]): Status => status({ verb: "resolve", storeMtimeNs: "1757145600000000009", store: { v: 3, path: "docs/report.md", suggestions: SUGG, comments: ALL.map((c) => (ids.includes(c.id) ? { ...c, resolved: true } : c)) } });
const gesture = (el: El, type: string): void => { el.dispatchEvent(new Ev(type)); };
/** Both answered comments resolved through the header action, the replies answered: the offer stands. */
async function resolveBoth(w: World, aside: El): Promise<void> {
  headBtn(aside)!.click();
  act(aside, "fcresolveanswereddo")!.click(); await flush();
  answer(w, resolvedAll([answered.id]), lastOf(w, "fileComments", "resolve")); await flush(); await flush();
  answer(w, resolvedAll([answered.id, revised.id]), lastOf(w, "fileComments", "resolve")); await flush(); await flush();
  assert.ok(aside.querySelector(".fc-reopen"), "the offer stands");
}

// ── the confirm's end ─────────────────────────────────────────────────────────────────────────────

test("the confirm is over once the count falls to zero: asked, then both answered comments resolved from their own cards, a status that answers two more shows the header action and no confirm row", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  headBtn(aside)!.click();
  assert.ok(confirmRow(aside), "the confirm is up");
  const resolveFromCard = async (id: string, after: Status): Promise<void> => {
    card(aside, id)!.querySelector(".fc-card-head")!.click();   // open: the card's own buttons are one click down
    act(card(aside, id)!, "fcresolve", id)!.click(); await flush();
    const m = lastOf(w, "fileComments", "resolve");
    assert.deepEqual(m.args, { commentId: id, on: true });
    answer(w, after, m); await flush(); await flush();
  };
  await resolveFromCard(answered.id, resolvedAll([answered.id]));
  assert.ok(confirmRow(aside), "one answered comment still open: the question stands, re-counted");
  assert.equal(confirmRow(aside)!.querySelector(".fc-note")!.textContent, "Resolve the 1 comment the session has answered?");
  await resolveFromCard(revised.id, resolvedAll([answered.id, revised.id]));
  assert.equal(headBtn(aside), null, "nothing answered: no action");
  assert.equal(confirmRow(aside), null, "…and no confirm");
  // the session answers two more (open, and done reopened): the reply to a card's Resolve carries the status
  const again: Status = status({ verb: "resolve", storeMtimeNs: "1757145600000000013", store: { v: 3, path: "docs/report.md", suggestions: SUGG, comments: [
    { ...answered, resolved: true }, { ...revised, resolved: true }, { ...mineLast, resolved: true },
    { ...open, replies: [reply("api", T0 + 5100, "Added a summary.")] }, theirs, { ...done, resolved: false }] } });
  await resolveFromCard(mineLast.id, again);
  assert.equal(headBtn(aside)!.textContent, "Resolve answered (2)", "two answered again: the action is back");
  assert.equal(confirmRow(aside), null, "the question the person walked away from is not: a click on the action asks it");
  assert.equal(resolves(w).length, 3, "three resolves, every one a card's own; the header action wrote nothing");
});

test("the confirm does not survive the panel's close: asked, closed, reopened, the action stands and the row does not", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside, button } = await openPanel(w);
  headBtn(aside)!.click();
  assert.ok(confirmRow(aside));
  button.click();
  assert.equal(w.main.querySelector(".fileview-aside"), null, "closed");
  button.click(); answer(w, status()); await flush(); await flush();
  const a2 = w.main.querySelector(".fileview-aside")!;
  assert.ok(a2, "reopened");
  assert.equal(headBtn(a2)!.textContent, "Resolve answered (2)");
  assert.equal(confirmRow(a2), null, "a question asked in the panel the person closed is not asked again by the reopen");
});

// ── the consent, once per run ─────────────────────────────────────────────────────────────────────

test("the file-editing consent is asked once for a Resolve answered and once for a Reopen all: declined, one row under the header action and nothing written; granted, the writes go with no second ask", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  let asks = 0, grant = false;
  w.ctx.ensureEditingAllowed = async () => { asks++; return grant; };
  const { aside } = await openPanel(w);
  headBtn(aside)!.click(); act(aside, "fcresolveanswereddo")!.click(); await flush(); await flush();
  assert.equal(asks, 1, "one ask for the run, not one per comment");
  assert.deepEqual(resolves(w), [], "declined: nothing written");
  const rows = aside.querySelectorAll(".fc-err");
  assert.equal(rows.length, 1, "one row, not one per comment");
  assert.equal(rows[0].dataset.slot, "answered");
  assert.equal(rows[0].querySelector("span")!.textContent, "Nothing written: comments need file editing on.", "mutate's words");
  assert.ok(aside.querySelector(".fc-head")!.contains(rows[0]), "under the header, where the action that asked is");
  assert.ok((rows[0].nextSibling as El).classes.includes("fc-filter"), "under the toggles' row and above the filter's, where the confirm stood");
  assert.equal(headBtn(aside)!.textContent, "Resolve answered (2)"); assert.equal(headBtn(aside)!.disabled, false, "the action is back, not stuck at Resolving…");
  assert.equal(aside.querySelector(".fc-reopen"), null, "nothing resolved: no offer");
  act(aside, "fcerrx")!.click();
  assert.equal(aside.querySelector(".fc-err"), null, "the row's ✕ dismisses it");
  // granted: the two writes go, and the consent is not asked again for the second
  grant = true;
  headBtn(aside)!.click(); act(aside, "fcresolveanswereddo")!.click(); await flush();
  assert.equal(asks, 2, "the run's one ask");
  answer(w, resolvedAll([answered.id]), lastOf(w, "fileComments", "resolve")); await flush(); await flush();
  answer(w, resolvedAll([answered.id, revised.id]), lastOf(w, "fileComments", "resolve")); await flush(); await flush();
  assert.equal(resolves(w).length, 2); assert.equal(asks, 2, "the second write asked nothing");
  // Reopen all: one ask for its run, declined the same row, granted the writes
  grant = false;
  reopen(aside)!.click(); await flush(); await flush();
  assert.equal(asks, 3); assert.equal(resolves(w).length, 2, "declined: nothing reopened");
  assert.equal(aside.querySelectorAll('.fc-err[data-slot="answered"]').length, 1, "the one row");
  assert.equal(aside.querySelector(".fc-reopen"), null, "the offer was taken by the click, as ever");
});

// ── the offer's dress ─────────────────────────────────────────────────────────────────────────────

test("the Reopen all line: the acknowledgment's dress with the size on the words and the button alone, nothing of the saved line's; the words then the button on one line", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  await resolveBoth(w, aside);
  const line = aside.querySelector(".fc-reopen")!;
  assert.deepEqual(line.classes, ["fc-note", "fc-sent", "fc-reopen"], ".fc-note and .fc-sent on the row as on the acknowledgment (the Send section's tiers count it as the acknowledgment, not as growth)");
  assert.equal(line.style.fontSize, "inherit", "the row's own size set back to the section's: its .fc-note is the tier's and the colour's, and a .fc-note inside it would compound (ui/CLAUDE.md)");
  const words = line.querySelector(".fc-note")!;
  assert.deepEqual(words.classes, ["fc-note", "fc-sent"], "the words at the note's size, in the acknowledgment's colour"); assert.equal(words.textContent, "Resolved 2 comments");
  const b = reopen(aside)!;
  assert.deepEqual(b.classes, ["fc-note", "fc-sent", "fc-link"], "the button: the note's size, the acknowledgment's colour, the panel's link hover; no .fc-saved, the saved line's own dress");
  assert.equal(b.style.background, "none"); assert.equal(b.style.border, "0"); assert.equal(b.style.padding, "0");
  assert.equal(b.style.display, undefined, "inline beside the words (.fc-saved's display: block stood it on a line of its own)");
  assert.equal(line.textContent, "Resolved 2 commentsReopen all", "the words, then the button (its gap is a margin, not a space)");
  assert.equal(b.style.marginLeft, "6px");
  assert.equal(line.style.position, undefined, "the list layout: not sticky (the margin layout's, below)");
  assert.ok(aside.querySelector(".fc-head")!.contains(line), "under the header: the list layout's place (the margin layout's is the Send section, the acknowledgment's position: the next test, and file-comments-resolve-answered-review2.test.ts)");
  // the source: one class string in the panel holds the fc-saved token, the saved line's own (feed-css-saved-line-head-dress.test.ts pins the same)
  assert.deepEqual(SRC.match(/"[^"\n]*\bfc-saved(?![\w-])[^"\n]*"/g), ['"fc-note fc-sent fc-saved"']);
});

test("in the margin layout the offer sticks to the Send section's bottom edge, as the saved line does: the section scrolls inside itself while its confirm is up, and a line after the confirm stood past its box", async (t: TestContext) => {
  marginOn = true; t.after(() => { marginOn = false; });
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  assert.ok(aside.classes.includes("fc-margin"), "the margin layout");
  await resolveBoth(w, aside);
  const line = aside.querySelector(".fc-reopen")!;
  assert.equal(line.style.position, "sticky"); assert.equal(line.style.bottom, "0"); assert.equal(line.style.background, "var(--bg)");
  assert.ok(aside.querySelector(".fc-send")!.contains(line));
});

// ── the keyboard on the offer ─────────────────────────────────────────────────────────────────────

test("a wheel while Reopen all holds the keyboard ends the offer and moves the focus to the nearest control of the panel, never to the body", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  await resolveBoth(w, aside);
  const b = reopen(aside)!;
  b.focus(); assert.equal(doc.activeElement, b, "Tab reached the offer");
  gesture(w.body, "wheel");
  assert.equal(aside.querySelector(".fc-reopen"), null, "the wheel ends the offer");
  assert.notEqual(doc.activeElement, b, "the removed button does not keep the focus (the browser would drop it to the body)");
  assert.ok(doc.activeElement && aside.contains(doc.activeElement), "the keyboard is on a control of the panel");
  assert.equal(doc.activeElement!.tagName, "BUTTON");
  assert.equal(resolves(w).length, 2, "and nothing was reopened");
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

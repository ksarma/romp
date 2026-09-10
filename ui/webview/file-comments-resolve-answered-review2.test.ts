// Resolve answered, the review of 2026-09-10, round 2 (plans/file-review.md, "The about follow-on (2026-09-10)" under Slice
// 2; decision 46), driven over the stand-in file-comments-resolve-answered-fixes.test.ts drives (copied here, as the sibling
// modules copy it; the sheet's verdict on the fold is switchable). Pinned, what the round found:
//   • In the LIST layout (the narrow pane, the panel under the text) the Reopen all offer stands under the header, where the
//     action that made it stood and the person is looking, and displaces nothing at the foot: the Send section is the
//     scroller's foot there, below every card, so the offer in it stood off screen after the click on a long list, and
//     every wheel toward it was the gesture that ends it (the saved line's own reason, savedLineHead). The margin layout's
//     offer keeps the sent acknowledgment's position in the Send section, displacing the acknowledgment until the offer
//     ends, as before. One line in the panel either way.
//   • The keyboard after the run: Enter on the confirm's Resolve removed the row under the focus, which fell to the body (a
//     head-row confirm has no place of its own for refocus to stand in for it), and when the run ended nothing handed it on;
//     the offer at the foot was reached only by tabbing through the head and every open card. Now the run's end puts the
//     keyboard on the Reopen all offer it made; Enter there reopens, and that run's end puts it on the header action the
//     reopen brought back. A run begun with the keyboard elsewhere (a pointer whose press focused nothing) moves it nowhere.
// Synthetic fixtures only: the notes-api world, placeholder ids, the sessions "api" and "web".
import { test, type TestContext } from "node:test";
import * as assert from "node:assert/strict";
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
  // the inline style as a record, with the two methods the margin layout's pass writes through (setProperty, removeProperty)
  style: Record<string, any> = { setProperty(k: string, v: string) { this[k] = v; }, removeProperty(k: string) { delete this[k]; } };
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


/** A send of the person's words alone (nothing is unsent in the fixture), so a sent acknowledgment stands at the foot (the
 *  first stand-in's drive): the confirm, its accept option unchecked, the words in the note box, its Send; the send answered,
 *  the refresh it asks answered with the status. */
async function sendWords(w: World, aside: El, words: string): Promise<void> {
  act(aside, "fcsend")!.click();
  const accept = aside.querySelector('input[data-opt="accept"]');
  if (accept) { accept.checked = false; dispatch(accept, new Ev("change")); }
  const box = aside.querySelector(".fc-confirm .fc-send-note")!;
  assert.ok(box, "the confirm is up, with its note box");
  box.value = words; dispatch(box, new Ev("input"));
  act(aside, "fcsendgo")!.click(); await flush();
  const m = lastOf(w, "fileCommentsSend");
  assert.ok(m, "the send went out");
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsSent", reqId: m.reqId, queued: false } })); await flush();
  answer(w, status()); await flush(); await flush();
}
/** The plain sent acknowledgment in the Send section: the div in the acknowledgment's dress that is not the Reopen all line. */
const sentAck = (aside: El): El[] => aside.querySelectorAll(".fc-send div.fc-sent").filter((d) => !d.classList.contains("fc-reopen"));
const offers = (aside: El): El[] => aside.querySelectorAll(".fc-reopen");
const inHead = (aside: El, n: El): boolean => aside.querySelector(".fc-head")!.contains(n);
const inSend = (aside: El, n: El): boolean => aside.querySelector(".fc-send")!.contains(n);

// ── the offer's place, by layout ──────────────────────────────────────────────────────────────────

test("the list layout: the Reopen all offer stands under the header, one in the panel, not sticky, and the sent acknowledgment at the foot is not displaced; a gesture ends the offer in place and doubles nothing; the next render shows the same", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  assert.ok(!aside.classes.includes("fc-margin"), "the list layout");
  await sendWords(w, aside, "The findings read well now.");
  assert.equal(sentAck(aside).length, 1, "the acknowledgment at the foot");
  await resolveBoth(w, aside);
  const line = offers(aside);
  assert.equal(line.length, 1, "one offer in the panel");
  assert.ok(inHead(aside, line[0]), "under the header, where the action stood and the person is looking");
  assert.ok(!inSend(aside, line[0]), "not at the scroller's foot");
  assert.equal(line[0].style.position, undefined, "not sticky: the header is on screen");
  assert.equal(line[0].textContent, "Resolved 2 commentsReopen all");
  assert.equal(reopen(aside)!.textContent, "Reopen all");
  const head = aside.querySelector(".fc-head")!;
  const kids = head.childNodes.filter((n) => n instanceof El) as El[];
  assert.ok(kids.indexOf(line[0]) > kids.findIndex((n) => n.classList.contains("fc-filter")), "below the filter row, with the header's other lines");
  assert.equal(sentAck(aside).length, 1, "the acknowledgment stays at the foot: the offer displaced nothing there");
  assert.match(sentAck(aside)[0].textContent, /^Sent to api at /);
  // a gesture ends the offer where it stands (reflectLines, no render), and brings nothing back: nothing was displaced
  gesture(w.body, "pointerdown");
  assert.equal(offers(aside).length, 0, "the offer is over");
  assert.equal(sentAck(aside).length, 1, "the acknowledgment once, not twice");
  assert.equal(resolves(w).length, 2, "nothing reopened");
  act(aside, "fcresolved")!.click();                   // a render (a fold toggled): the same
  assert.equal(offers(aside).length, 0);
  assert.equal(sentAck(aside).length, 1);
});

test("the list layout with no acknowledgment before: the offer under the header, a bare foot; the offer's click reopens both and the offer goes", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  await resolveBoth(w, aside);
  assert.ok(inHead(aside, offers(aside)[0]));
  assert.equal(sentAck(aside).length, 0, "nothing to show at the foot");
  reopen(aside)!.click(); await flush();
  assert.equal(offers(aside).length, 0, "the offer is taken");
  const m1 = lastOf(w, "fileComments", "resolve");
  assert.deepEqual(m1.args, { commentId: answered.id, on: false });
  answer(w, resolvedAll([revised.id]), m1); await flush(); await flush();
  const m2 = lastOf(w, "fileComments", "resolve");
  assert.deepEqual(m2.args, { commentId: revised.id, on: false });
  answer(w, resolvedAll([]), m2); await flush(); await flush();
  assert.equal(headBtn(aside)!.textContent, "Resolve answered (2)", "both open again: the action is back");
});

test("the margin layout: the offer stands in the Send section in the sent acknowledgment's place, displacing it until a gesture ends the offer and brings it back there", async (t: TestContext) => {
  marginOn = true; t.after(() => { marginOn = false; });
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  assert.ok(aside.classes.includes("fc-margin"), "the margin layout");
  await sendWords(w, aside, "Ship it.");
  assert.equal(sentAck(aside).length, 1);
  await resolveBoth(w, aside);
  const line = offers(aside);
  assert.equal(line.length, 1, "one offer in the panel");
  assert.ok(inSend(aside, line[0]), "the acknowledgment's position: the Send section pinned at the panel's foot");
  assert.ok(!inHead(aside, line[0]));
  assert.equal(line[0].style.position, "sticky", "…stuck to the section's bottom edge");
  assert.equal(sentAck(aside).length, 0, "the acknowledgment is displaced, not doubled");
  gesture(w.body, "wheel");
  assert.equal(offers(aside).length, 0, "a wheel ends it");
  assert.equal(sentAck(aside).length, 1, "the acknowledgment is back where the offer stood");
  assert.ok(inSend(aside, sentAck(aside)[0]));
  assert.match(sentAck(aside)[0].textContent, /^Sent to api at /);
  // the source: the two placements are one function, one layout each
  assert.match(SRC, /private reopenLineHead\(\): HTMLElement \| null \{\s+return this\.margin \|\| this\.reopenAll === null \? null : this\.reopenLine\(this\.reopenAll\.length\);/);
  assert.match(SRC, /if \(this\.reopenAll !== null && this\.margin\) box\.appendChild\(this\.reopenLine\(this\.reopenAll\.length\)\);/, "the Send section's offer is the margin layout's");
  assert.match(SRC, /if \(this\.sentNote && this\.sections\.send\.contains\(offer\)\) offer\.parentNode\?\.insertBefore/, "the acknowledgment comes back only where the offer displaced it");
});

// ── the keyboard after the run ────────────────────────────────────────────────────────────────────

test("Enter on the confirm's Resolve: when the run ends the keyboard is on the Reopen all offer it made, not on the body; Enter there reopens, and that run's end puts the keyboard on the header action the reopen brought back", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  headBtn(aside)!.click();
  const go = act(aside, "fcresolveanswereddo")!;
  go.focus(); assert.equal(doc.activeElement, go, "the keyboard is on the confirm's Resolve");
  go.click(); await flush();                           // the first render removed the row under the focus
  assert.ok(doc.activeElement === doc.body || doc.activeElement === null || !aside.contains(doc.activeElement), "mid-run the confirm is gone and nothing of the panel holds the keyboard (a head-row confirm has no stand-in)");
  answer(w, resolvedAll([answered.id]), lastOf(w, "fileComments", "resolve")); await flush(); await flush();
  answer(w, resolvedAll([answered.id, revised.id]), lastOf(w, "fileComments", "resolve")); await flush(); await flush();
  const b = reopen(aside)!;
  assert.ok(b, "the offer stands");
  assert.equal(doc.activeElement, b, "the run's end hands the keyboard to the one-click undo it made");
  assert.equal(offers(aside).length, 1, "the hand-off is no gesture: the offer stands");
  // Enter on the offer: the keyboard's click (the delegate's KEY_ACTS make Enter a click on a button natively; the stand-in clicks)
  b.click(); await flush();
  assert.equal(offers(aside).length, 0, "the offer is taken");
  answer(w, resolvedAll([revised.id]), lastOf(w, "fileComments", "resolve")); await flush(); await flush();
  answer(w, resolvedAll([]), lastOf(w, "fileComments", "resolve")); await flush(); await flush();
  const back = headBtn(aside)!;
  assert.equal(back.textContent, "Resolve answered (2)", "the reopen brought the action back");
  assert.equal(doc.activeElement, back, "…and the keyboard is on it");
});

test("a run begun with the keyboard outside the panel moves it nowhere: a pointer user's focus is left where it was", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  headBtn(aside)!.click();
  doc.activeElement = doc.body;
  act(aside, "fcresolveanswereddo")!.click(); await flush();
  answer(w, resolvedAll([answered.id]), lastOf(w, "fileComments", "resolve")); await flush(); await flush();
  answer(w, resolvedAll([answered.id, revised.id]), lastOf(w, "fileComments", "resolve")); await flush(); await flush();
  assert.ok(reopen(aside), "the offer stands");
  assert.equal(doc.activeElement, doc.body, "nothing of the panel took the keyboard");
});

test("a run every request of which is refused makes no offer, and the keyboard goes to the header action, which stands with its count", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  headBtn(aside)!.click();
  const go = act(aside, "fcresolveanswereddo")!;
  go.focus(); go.click(); await flush();
  refuse(w, lastOf(w, "fileComments", "resolve"), "no-comment", "the comment is gone"); await flush(); await flush();
  refuse(w, lastOf(w, "fileComments", "resolve"), "no-comment", "the comment is gone"); await flush(); await flush();
  assert.equal(reopen(aside), null, "nothing resolved: no offer");
  const b = headBtn(aside)!;
  assert.equal(b.textContent, "Resolve answered (2)");
  assert.equal(doc.activeElement, b, "the keyboard is on the action, where it began");
  assert.match(SRC, /for \(const act of \["fcreopenall", "fcresolveanswered", "fcfile"\]\)/, "the offer, else the action, else Comment on this file in the same row");
});

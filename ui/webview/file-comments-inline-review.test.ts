// The inline-display follow-on's review (plans/file-review.md, 2026-09-07): three behaviours the toggle suite's
// stand-in could show and did not, driven AS A PANEL over the same DOM stand-in (its Rendered body built by hand to
// marked's shape, its settings store the stub localStorage every panel suite installs):
//   • a change mark inside the author's link — the Rendered deletion point placed at the start of a link's label,
//     a substitution's point and tint over the label — opens its card AND cancels the click, so the <a> mdBlock gave
//     target=_blank opens no tab: by click, by Enter (KEY_ACTS), with the panel open or closed, and under the chat
//     pane's capture-phase link handler, which stands aside for a panel mark on the word that the delegate cancels;
//     the author's own span wearing data-act=fcchange inside a link is neither cancelled nor acted on;
//   • Show changes inline is withheld while the editor holds the body (the editor draws every change itself) and
//     offered again when the read view is back — the header's row, not a source pin, says so;
//   • a Rendered deletion the map cannot place (inside a code fence) is card-only, its "not shown" tag wearing the
//     generic title (this view does not show the change; Reveal opens it in Raw) — the same deletion IS struck in
//     Raw, so a title that said Rendered cannot show deletions would be false since the follow-on.
// The source pins that close the file hold fcchange's cancel beside fcopen's, and the module header's account of the
// marks: both views since the follow-on, where Slice 2's sentence (struck at their point in Raw) stood until the
// review's consolidation.
// Synthetic fixtures only: the notes-api world, placeholder ids, example.invalid URLs.
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
/** The session's URL on the recommendation, as the author wrote it: `[shipping the cache](…)`. */
const URL = "https://example.invalid/agent-chosen";
const DOC_LINK = DOC.replace("shipping the cache", "[shipping the cache](" + URL + ")");
/** A second link the author wrote around a span wearing the panel's own data-act (not the panel's to act on). */
const URL2 = "https://example.invalid/more";
/** A fenced code block after the title: a hole the Rendered mapping shows but does not place. */
const FENCE = "```\nrespond(request)\n```\n\n";
const DOC_FENCE = DOC.replace("# Report\n\n", "# Report\n\n" + FENCE);
const at = (needle: string, src = DOC): number => { const i = src.indexOf(needle); assert.ok(i >= 0, needle); return i; };
const H = (id: string, kind: Hunk["kind"], from: number, to: number, oldText: string, newText: string, ts = T0 - 90000): Hunk =>
  ({ id, author: "api", ts, kind, curFrom: from, curTo: to, baseFrom: from, baseTo: from + oldText.length, oldText, newText, anchor: null });
const h1 = H("h1", "sub", at("cut"), at("cut") + 3, "reduced", "cut");
const h3 = H("h3", "del", at("shipping"), at("shipping"), "quickly ", "", T0 - 70000);
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
    store: { v: 3, path: "docs/report.md", suggestions: SUGG, comments: [] },
    hunks: [h1, h3], log: [],
    unsent: { comments: [], replies: [], accepted: 0, rejected: 0, watermark: null },
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
  // the edges are created hidden and hideEdges hides the rest: a node inspects as its own projection (ui/test-dom-shim.ts)
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

// The stand-in's nodes inspect as their own projection: hideEdges (ui/test-dom-shim.ts) makes every own property that
// holds an object, and every accessor, non-enumerable, so a failing assertion's dump of a node is a few lines and not
// the whole tree (a dump that walked parentNode up to the body grew to tens of GB before the box killed it, 2026-09-09).
test("stand-in: a node enumerates and inspects as its own projection, never the tree", () => {
  const root = doc.createElement("div");
  const kid = root.appendChild(doc.createElement("span"));
  kid.className = "fc-x"; kid.dataset.id = "k1"; kid.addEventListener("click", () => { /* inert */ });
  const leaf = kid.appendChild(doc.createTextNode("leaf"));
  for (const n of [root, kid, leaf]) {
    const own = n as unknown as Record<string, unknown>;
    assert.ok(Object.keys(own).every((k) => staysEnumerable(own[k])), "only primitives enumerate on " + n.constructor.name + ": " + Object.keys(own).join(", "));
    const dump = inspect(n, { compact: false, customInspect: false, depth: 1000, maxArrayLength: Infinity, showHidden: false, showProxy: false, sorted: true, getters: true });
    assert.ok(!dump.includes("parentNode") && !dump.includes("childNodes"), "the dump is the node's own projection:\n" + dump);
  }
});
const store = new Map<string, string>();
(globalThis as any).localStorage = {
  getItem: (k: string) => (store.has(k) ? store.get(k)! : null),
  setItem: (k: string, v: string) => { store.set(k, String(v)); },
  removeItem: (k: string) => { store.delete(k); },
};


// ── the viewer stand-in: a Raw or Rendered body, the seam as closures, the viewer's edit mode as a switch ──
type World = {
  ctx: FileViewActionCtx; posted: any[]; main: El; body: El;
  hooks: { rendered: Array<() => void>; close: Array<() => void> };
  disk: string; diskMtime: string; viewMtime: string; reloads: number; scrolls: number[]; modes: string[];
  mtimes: Record<string, string>;
  /** The viewer's edit mode (ctx.editing reads it); the viewer fires onRendered once on entering and once on leaving. */
  editing: boolean;
  rerender: () => void;
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
/** A file-authored inline element the sanitizer keeps: `<span data-act=… data-id=…>text</span>`. */
const fileSpan = (act: string, id: string, text: string): El => { const s = el("span", text); s.dataset.act = act; s.dataset.id = id; return s; };
/** A link as mdBlock leaves it: marked's <a href>, given target=_blank rel=noopener by the viewer. */
const link = (href: string, ...kids: Array<El | string>): El => { const a = el("a", ...kids); a.setAttribute("href", href); a.setAttribute("target", "_blank"); a.setAttribute("rel", "noopener"); return a; };
/** marked's rendering of DOC (or DOC_LINK with `linked`), built by hand: one element per block, in order. */
function renderedDoc(box: El, over: WorldOpts): void {
  const blocks: El[] = [el("h1", "Report")];
  if (over.intro) blocks.push(over.intro());
  blocks.push(el("h2", "Findings"), el("p", "The api session cut p95 latency by 40% and the p99 by 10%."));
  blocks.push(over.linked ? el("p", "We recommend ", link(URL, "shipping the cache"), " in v1.2.") : el("p", "We recommend shipping the cache in v1.2."));
  // the author's own link around a span wearing the panel's data-act: the file's markup, whatever it carries
  blocks.push(over.linked ? el("p", "Risks remain in the ", link(URL2, fileSpan("fcchange", "zz", "fallback")), " path.") : el("p", "Risks remain in the fallback path."));
  blocks.push(el("p", "Next steps: measure again."));
  box.replaceChildren(...blocks);
}
type WorldOpts = { src?: string; mode?: "raw" | "rendered"; intro?: () => El; linked?: boolean; editing?: boolean };
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
    renderedDoc(md, over);
  }
  const w = {
    posted: [] as any[], main, body,
    hooks: { rendered: [] as Array<() => void>, close: [] as Array<() => void> },
    disk: text, diskMtime: "1757145600000000001", viewMtime: "1757145600000000001", reloads: 0, scrolls: [] as number[], modes: [] as string[], mtimes: {} as Record<string, string>,
    editing: !!over.editing,
  } as World;
  const setText = (s: string) => {
    text = s;
    if (code) rows(code, s); else if (md) renderedDoc(md, over);
    for (const cb of w.hooks.rendered) cb();
  };
  w.rerender = () => { for (const cb of w.hooks.rendered) cb(); };   // the viewer painted the body again (edit mode entered or left)
  w.ctx = {
    path: ABS, sid: SID, todoId: null,
    body: () => body as unknown as HTMLElement, mode: () => mode, text: () => text, mtimeNs: () => w.viewMtime, media: () => null, mediaElement: () => null, renderedImages: () => [], pdfPages: () => [],
    identity: () => ({ name: "api", color: null }),
    onRendered: (cb) => { w.hooks.rendered.push(cb); }, onSelection: () => { /* inert */ },
    onSaved: () => { /* inert */ }, onClose: (cb) => { w.hooks.close.push(cb); },
    post: (m) => { w.posted.push(m); }, ensureEditingAllowed: async () => true, setEditBlocked: () => { /* inert */ }, editing: () => w.editing, setTrackedEdit: () => { /* inert */ }, guardClose: () => { /* inert */ },
    aside: (node) => { main.querySelector(".fileview-aside")?.remove(); if (node) { const n = node as unknown as El; n.classList.add("fileview-aside"); main.appendChild(n); } },
    setMode: (m) => { w.modes.push(m); }, scrollToOffset: (n) => { w.scrolls.push(n); },
    reload: () => { w.reloads++; w.viewMtime = w.diskMtime; setText(w.disk); },
  };
  w.close = () => { for (const cb of w.hooks.close) cb(); if (cur === w) cur = null; };
  cur = w;
  return w;
}
const flush = () => new Promise<void>((r) => setImmediate(r));
const lastOf = (w: World, type: string, verb?: string) => [...w.posted].reverse().find((m) => m.type === type && (verb === undefined || m.verb === verb));
function answer(w: World, s: Status, m = lastOf(w, "fileComments", "status")): void {
  assert.ok(m, "an ask is outstanding");
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId: m.reqId, ...s } }));
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
const asideOf = (w: World): El => w.main.querySelector(".fileview-aside")!;
const card = (aside: El, key: string): El | null => aside.querySelector('.fc-card[data-id="' + key + '"]');
const act = (root: El, a: string, id?: string): El | null => root.querySelector('[data-act="' + a + '"]' + (id ? '[data-id="' + id + '"]' : ""));
const texts = (els: El[]) => els.map((e) => e.textContent);
const marksOf = (w: World, id?: string): El[] => w.body.querySelectorAll('[data-act="fcchange"]' + (id ? '[data-id="' + id + '"]' : ""));
const tags = (c: El): El[] => c.querySelectorAll(".fc-card-head .fc-tag");
const isLink = (c: El): boolean => c.querySelector(".fc-ref")!.classes.includes("fc-link");
const headRow = (aside: El): string[] => aside.querySelector(".fc-head .fc-row")!.childNodes.map((c) => (c as El).dataset.act);
const SETTINGS_KEY = "romp:settings";

// ── a change mark inside the author's link ─────────────────────────────────────────────────────────

test("a Rendered change mark inside the author's link — the deletion point at the start of the label, a substitution's point and tint over it — opens its card and cancels the click, so the link opens no tab: by click, by Enter, with the panel closed; the author's own span wearing data-act=fcchange inside a link is neither cancelled nor acted on", async (t: TestContext) => {
  store.delete(SETTINGS_KEY);
  const w = world({ mode: "rendered", src: DOC_LINK, linked: true }); t.after(() => w.close());
  const del = H("h3", "del", at("shipping", DOC_LINK), at("shipping", DOC_LINK), "quickly ", "", T0 - 70000);
  const sub = H("hL", "sub", at("cache", DOC_LINK), at("cache", DOC_LINK) + 5, "store", "cache", T0 - 60000);
  const { aside, button } = await openPanel(w, status({ hunks: [shifted(h1, 0), del, sub] }));
  // placement: the point is the anchor's first child; the substitution's point and tint stand inside the anchor too
  const point = marksOf(w, "h3");
  assert.equal(point.length, 1);
  const a = point[0].parentNode!;
  assert.equal(a.tagName, "A"); assert.equal(a.getAttribute("href"), URL); assert.equal(a.getAttribute("target"), "_blank");
  assert.equal(a.childNodes[0], point[0], "the deletion point is the first child of the author's <a>");
  const subMarks = marksOf(w, "hL");
  assert.deepEqual(subMarks.map((m) => m.classes.join(" ")), ["fc-del", "fc-ins"]);
  for (const m of subMarks) assert.equal(m.closest("a"), a, "the substitution's point and tint stand inside the same <a>");
  assert.equal(subMarks[1].textContent, "cache");
  const seen: boolean[] = [];
  const atDoc = (ev: Ev) => { seen.push(ev.defaultPrevented); };   // what the browser reads after dispatch: a cancelled click activates no anchor
  doc.addEventListener("click", atDoc);
  try {
    // 1. the panel open: a click on the struck label
    const ev1 = new Ev("click"); dispatch(point[0], ev1);
    assert.ok(card(aside, "chg:h3")!.classes.includes("open"), "the card opened");
    assert.equal(ev1.defaultPrevented, true, "the link's activation is cancelled: no tab to the session's URL");
    assert.deepEqual(seen, [true]);
    // 2. Enter on the focused point (KEY_ACTS: its click)
    point[0].focus();
    assert.equal(doc.activeElement, point[0]);
    dispatch(point[0], new Ev("keydown", { key: "Enter" }));
    assert.deepEqual(seen, [true, true], "the synthetic click is cancelled too");
    // 3. the substitution's tint and its point
    const ev3 = new Ev("click"); dispatch(subMarks[1], ev3);
    assert.ok(card(aside, "chg:hL")!.classes.includes("open"), "the tint opened its card");
    assert.equal(ev3.defaultPrevented, true);
    const ev3b = new Ev("click"); dispatch(subMarks[0], ev3b);
    assert.equal(ev3b.defaultPrevented, true);
    assert.deepEqual(seen, [true, true, true, true]);
    // 4. the panel closed: the marks stay painted, and the click opens the panel with the card, tab-free
    button.click();
    assert.equal(w.main.querySelector(".fileview-aside"), null, "the panel is closed");
    seen.length = 0;   // the panel button's own click reached the document too (uncancelled: no anchor around it)
    const again = marksOf(w, "h3");
    assert.equal(again.length, 1, "the point stays painted with the panel closed");
    const ev4 = new Ev("click"); dispatch(again[0], ev4);
    await flush();
    assert.ok(asideOf(w), "the panel opened");
    assert.equal(ev4.defaultPrevented, true, "…and the link's activation is cancelled");
    // 5. the file's own markup: a link the author wrote around a span wearing the panel's data-act
    const theirs = w.body.querySelector('span[data-act="fcchange"][data-id="zz"]')!;
    assert.equal(theirs.closest("a")!.getAttribute("href"), URL2);
    const ev5 = new Ev("click"); dispatch(theirs, ev5);
    assert.equal(ev5.defaultPrevented, false, "not the panel's control: the author's link follows as written");
    assert.equal(card(asideOf(w), "chg:zz"), null, "and nothing was acted on");
    assert.deepEqual(seen, [true, false]);
  } finally { doc.removeEventListener("click", atDoc); }
});

test("under the chat pane's capture-phase link handler, a change mark inside a link still opens its card and opens no tab — the handler asks panelMark and stands aside; the author's own link inside the file still opens through it", async (t: TestContext) => {
  store.delete(SETTINGS_KEY);
  const w = world({ mode: "rendered", src: DOC_LINK, linked: true }); t.after(() => w.close());
  const fc = await import("./file-comments");
  const del = H("h3", "del", at("shipping", DOC_LINK), at("shipping", DOC_LINK), "quickly ", "", T0 - 70000);
  const { aside } = await openPanel(w, status({ hunks: [del] }));
  const opened: string[] = [];
  // render.ts's handler, as coded: a link's click at the document's capture phase, the panel's marks excepted
  const shell = (ev: Ev) => {
    const t = ev.target as El | Txt | null;
    const a = t instanceof El ? t.closest("a[href]") : t ? t.parentNode!.closest("a[href]") : null;
    if (!a) return;
    if (fc.panelMark(ev.target as unknown as Element | null)) return;
    const href = a.getAttribute("href") || "";
    if (!/^[a-z][a-z0-9+.-]*:/i.test(href)) return;
    ev.preventDefault(); ev.stopPropagation();
    opened.push(href);
  };
  doc.addEventListener("click", shell, true);
  try {
    const point = marksOf(w, "h3")[0];
    assert.equal(point.parentNode!.tagName, "A");
    const ev1 = new Ev("click"); dispatch(point, ev1);
    assert.ok(card(aside, "chg:h3")!.classes.includes("open"), "the card opened: the shell stood aside");
    assert.equal(ev1.defaultPrevented, true, "the delegate cancelled the anchor");
    assert.deepEqual(opened, [], "the shell opened nothing");
    // the control: the author's own link, its text no panel mark, goes through the shell as before
    const label = point.parentNode!.childNodes[1] as Txt;
    assert.equal(label.data, "shipping the cache");
    const ev2 = new Ev("click"); dispatch(label, ev2);
    assert.deepEqual(opened, [URL], "the author's link opens through the shell's handler");
    assert.equal(ev2.defaultPrevented, true);
  } finally { doc.removeEventListener("click", shell, true); }
});

// ── Show changes inline while the editor is up ─────────────────────────────────────────────────────

test("Show changes inline is withheld while the editor holds the body — the header offers Track changes and Comment on this file alone, no mark is painted, the store is untouched — and offered again, on, when the read view is back", async (t: TestContext) => {
  store.delete(SETTINGS_KEY);
  const w = world({ editing: true }); t.after(() => w.close());
  const { aside } = await openPanel(w, status({ hunks: [h1, h3] }));
  assert.deepEqual(headRow(aside), ["fctrack", "fcfile"], "the editor draws every change itself: no control over marks the read view is not showing");
  assert.equal(act(aside, "fcinline"), null);
  assert.equal(marksOf(w).length, 0, "the read view's painters do not run under the editor");
  assert.equal(store.get(SETTINGS_KEY), undefined, "nothing written");
  assert.equal(aside.querySelectorAll(".fc-card.fc-change").length, 2, "the change cards still render");
  // the editor closes: the viewer paints the read view and fires onRendered
  w.editing = false; w.rerender(); await flush();
  assert.deepEqual(headRow(asideOf(w)), ["fctrack", "fcinline", "fcfile"], "the read view is back: the toggle beside Track changes");
  const b = act(asideOf(w), "fcinline")!;
  assert.equal(b.dataset.on, "1"); assert.equal(b.getAttribute("aria-pressed"), "true");
  assert.ok(marksOf(w).length > 0, "…and the marks are painted");
  // the editor opens again: the viewer fires onRendered once in edit mode
  w.editing = true; w.rerender(); await flush();
  assert.deepEqual(headRow(asideOf(w)), ["fctrack", "fcfile"], "withheld again");
  assert.equal(store.get(SETTINGS_KEY), undefined, "still nothing written: no flip happened");
});

// ── a Rendered deletion the map cannot place ───────────────────────────────────────────────────────

const NOT_SHOWN_TITLE = "This view does not show the change; Reveal opens it in Raw";

test("a Rendered deletion inside a code fence is card-only: its 'not shown' tag wears the generic title and the card keeps Reveal to Raw, while a deletion in prose is struck beside it; off, the tag goes; in Raw the same deletion is struck, so the title's 'this view' is the truth", async (t: TestContext) => {
  store.delete(SETTINGS_KEY);
  const w = world({ mode: "rendered", src: DOC_FENCE, intro: () => el("pre", el("code", "respond(request)\n")) }); t.after(() => w.close());
  const fenced = H("hc", "del", at("respond", DOC_FENCE), at("respond", DOC_FENCE), "await ", "", T0 - 65000);
  const prose = shifted(h3, FENCE.length);
  const { aside } = await openPanel(w, status({ hunks: [fenced, prose] }));
  assert.equal(marksOf(w, "hc").length, 0, "the fence is a hole the mapping does not place: no point beside the wrong words");
  assert.equal(marksOf(w, "h3").length, 1, "the control: the prose deletion is struck at its point");
  const c = card(aside, "chg:hc")!;
  assert.deepEqual(texts(tags(c)), ["not shown"]);
  assert.equal(tags(c)[0].title, NOT_SHOWN_TITLE, "the title speaks of this view, not of deletions: the Rendered view strikes them now");
  assert.equal(isLink(c), false, "no mark to link to");
  assert.ok(act(c, "fcreveal", "chg:hc"), "Reveal is the way to it");
  const p = card(aside, "chg:h3")!;
  assert.deepEqual(texts(tags(p)), [], "the struck one wears no tag");
  assert.ok(isLink(p));
  act(c, "fcreveal", "chg:hc")!.click();
  assert.deepEqual(w.modes, ["raw"]); assert.deepEqual(w.scrolls, [fenced.curFrom], "Reveal goes to the deletion's place in Raw");
  // off: nothing is shown by choice, so the tag would claim a failing that is none
  act(aside, "fcinline")!.click(); await flush();
  assert.deepEqual(texts(tags(card(asideOf(w), "chg:hc")!)), [], "off: no tag");
  store.delete(SETTINGS_KEY);
  w.close();
  // Raw is exact: the same deletion is struck inside the fence
  const w2 = world({ src: DOC_FENCE }); t.after(() => w2.close());
  const { aside: a2 } = await openPanel(w2, status({ hunks: [fenced] }));
  const raw = marksOf(w2, "hc");
  assert.equal(raw.length, 1); assert.equal(raw[0].dataset.fcText, "await ");
  assert.deepEqual(texts(tags(card(a2, "chg:hc")!)), [], "Raw shows it: no tag");
});

// ── source pins ────────────────────────────────────────────────────────────────────────────────────

test("pins: fcchange cancels the click as fcopen does, and both are Enter-activated controls (KEY_ACTS)", () => {
  assert.match(SRC, /fcchange: \(x, ev\) => \{ ev\.preventDefault\(\); if \(this\.dragClick\(ev\)\) return; this\.openPanel\(\); this\.showCard\("chg:" \+ x\.dataset\.id!\); \},/);
  assert.match(SRC, /fcopen: \(x, ev\) => \{ ev\.preventDefault\(\); if \(this\.dragClick\(ev\)\) return; this\.openPanel\(\);/);
  assert.match(SRC, /const KEY_ACTS = new Set\(\[[^\]]*"fcopen", "fcchange"[^\]]*\]\);/);
});

test("pins: the module header says the changes are marked in both views, a deletion the map cannot place card-only, and the toggle turns every mark off — not Slice 2's 'struck at their point in Raw', which read as current after the follow-on", () => {
  const header = SRC.slice(0, SRC.indexOf("\nimport "));
  assert.ok(header.startsWith("// File comments and tracked changes"), "the header is the module's opening comment, up to the first import");
  assert.match(header, /marked inline in both views/, "the header names both views");
  assert.match(header, /a deletion the map cannot place is card-only/, "…and the one case Rendered leaves to the card");
  assert.match(header, /Show changes inline in the panel's head turns every mark\s+(?:\/\/\s+)?off in both views/, "…and the toggle");
  assert.doesNotMatch(header, /struck at their point in Raw\b/, "Slice 2's Raw-only sentence is gone from the header");
});

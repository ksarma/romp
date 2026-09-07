// The viewer seam at the REAL openFileView (plans/file-review.md, "The viewer seam"; Slice 1's "the Edit
// refusal while changes are pending" and "Comment on a selection in either view"). The panel suites drive
// file-comments.ts over hand-written ctx objects, and file-comments.test.ts pins the seam's INTERFACE
// strings — so a closure that did nothing (setEditBlocked dropping its reason, mode() always answering
// "raw") passed typecheck and every suite (review round 2). Here the real module opens files over a DOM
// stand-in (the github-link test's idiom, widened to what openFileView touches), a probe action captures
// the ctx the viewer hands every action, and each closure is checked by what the viewer then DOES: the Edit
// button refusing in words off the kernel's hunks, mode() following the Rendered/Raw buttons and the
// kernel's Content-Type, and the fileSaved reply's `logWarning` reaching the note bar (review round 2: the
// kernel put the text on the reply and the viewer dropped it — a silent fallback CLAUDE.md forbids).
// Synthetic fixtures only: the notes-api world, placeholder ids.
import { test, type TestContext } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import type { FileViewActionCtx } from "./file-view";
import type { Status, Hunk } from "./file-comments-model";

const web = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const VIEW = web("file-view.ts");

// ── a DOM stand-in: ancestry, ids, attributes, events with capture and bubbling, a small selector engine ──
class Ev {
  target: El | Txt | null = null;
  currentTarget: El | null = null;
  defaultPrevented = false;
  stopped = false;
  key: string; ctrlKey: boolean; metaKey: boolean;
  constructor(public type: string, init: { key?: string; ctrlKey?: boolean; metaKey?: boolean } = {}) {
    this.key = init.key || ""; this.ctrlKey = !!init.ctrlKey; this.metaKey = !!init.metaKey;
  }
  preventDefault(): void { this.defaultPrevented = true; }
  stopPropagation(): void { this.stopped = true; }
}
type Listener = (ev: Ev) => void;
type Reg = { type: string; cb: Listener; capture: boolean; once: boolean };
const optsOf = (o?: boolean | { capture?: boolean; once?: boolean }) =>
  typeof o === "boolean" ? { capture: o, once: false } : { capture: !!(o && o.capture), once: !!(o && o.once) };
const kebab = (k: string) => k.replace(/[A-Z]/g, (c) => "-" + c.toLowerCase());
class Txt {
  nodeType = 3;
  parentNode: El | null = null;
  constructor(public data: string) {}
  get textContent(): string { return this.data; }
  get parentElement(): El | null { return this.parentNode; }
}
type Compound = { tag: string | null; id: string | null; classes: string[]; attrs: Array<[string, string | null]> };
/** Comma groups of descendant chains (`A B`), each link a compound `tag#id.class[attr="v"]`. */
function parseSel(sel: string): Compound[][] {
  return sel.split(",").map((g) => g.trim()).filter(Boolean).map((g) => g.split(/\s+/).map((s) => {
    const m = /^([a-zA-Z][\w-]*)?(#[\w-]+)?((?:\.[\w-]+)*)((?:\[[\w-]+(?:="[^"]*")?\])*)$/.exec(s);
    if (!m) throw new Error("stand-in: unsupported selector " + s);
    const classes = (m[3].match(/\.[\w-]+/g) || []).map((c) => c.slice(1));
    const attrs: Array<[string, string | null]> = [];
    for (const a of m[4].match(/\[[^\]]+\]/g) || []) { const am = /^\[([\w-]+)(?:="([^"]*)")?\]$/.exec(a)!; attrs.push([am[1], am[2] ?? null]); }
    return { tag: m[1] ? m[1].toUpperCase() : null, id: m[2] ? m[2].slice(1) : null, classes, attrs };
  }));
}
class El {
  nodeType = 1;
  tagName: string;
  parentNode: El | null = null;
  childNodes: Array<El | Txt> = [];
  attrs = new Map<string, string>();
  listeners: Reg[] = [];
  hidden = false; disabled = false; title = ""; type = ""; value = ""; placeholder = ""; spellcheck = true; wrap = "";
  src = ""; alt = ""; href = ""; download = ""; target = ""; rel = "";
  innerHTML = "";
  style: Record<string, string> = {};
  onclick: ((ev: Ev) => void) | null = null;
  scrolled = 0;                                  // scrollIntoView calls (scrollToOffset's visible effect)
  constructor(tag: string) { this.tagName = tag.toUpperCase(); }
  get id(): string { return this.attrs.get("id") || ""; }
  set id(v: string) { this.attrs.set("id", v); }
  get isConnected(): boolean { return doc.body.contains(this); }
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
  prepend(...ns: Array<El | Txt>): void { for (const n of ns.slice().reverse()) { this.detach(n); this.childNodes.unshift(n); n.parentNode = this; } }
  insertBefore<T extends El | Txt>(n: T, ref: El | Txt | null): T {
    if (!ref) return this.appendChild(n);
    this.detach(n);
    const i = this.childNodes.indexOf(ref);
    this.childNodes.splice(i < 0 ? this.childNodes.length : i, 0, n); n.parentNode = this; return n;
  }
  removeChild<T extends El | Txt>(n: T): T { this.detach(n); return n; }
  replaceChildren(...c: Array<El | Txt>): void { for (const x of this.childNodes) x.parentNode = null; this.childNodes = []; for (const x of c) this.appendChild(x); }
  remove(): void { this.detach(this); }
  normalize(): void { /* no adjacent text nodes are built here */ }
  setAttribute(k: string, v: string): void { this.attrs.set(k, v); }
  getAttribute(k: string): string | null { return this.attrs.has(k) ? (this.attrs.get(k) as string) : null; }
  hasAttribute(k: string): boolean { return this.attrs.has(k); }
  removeAttribute(k: string): void { this.attrs.delete(k); }
  contains(n: El | Txt | null): boolean { for (let x: El | Txt | null = n; x; x = x.parentNode) if (x === this) return true; return false; }
  private fits(c: Compound): boolean {
    return (!c.tag || c.tag === this.tagName) && (!c.id || c.id === this.id) && c.classes.every((k) => this.classes.includes(k))
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
  addEventListener(type: string, cb: Listener, o?: boolean | { capture?: boolean; once?: boolean }): void { this.listeners.push({ type, cb, ...optsOf(o) }); }
  removeEventListener(type: string, cb: Listener, o?: boolean | { capture?: boolean }): void {
    const cap = optsOf(o).capture;
    this.listeners = this.listeners.filter((l) => !(l.type === type && l.cb === cb && l.capture === cap));
  }
  dispatchEvent(ev: Ev): boolean { return dispatch(this, ev); }
  click(): void { this.dispatchEvent(new Ev("click")); }
  focus(): void { doc.activeElement = this; }
  blur(): void { if (doc.activeElement === this) doc.activeElement = null; }
  scrollIntoView(): void { this.scrolled++; }
  getBoundingClientRect(): { left: number; top: number; right: number; bottom: number; width: number; height: number } { return { left: 0, top: 0, right: 0, bottom: 0, width: 0, height: 0 }; }
  get offsetWidth(): number { return 0; }
}
const doc = {
  listeners: [] as Reg[],
  body: null as unknown as El,
  head: null as unknown as El,
  hidden: false,
  activeElement: null as El | null,
  createElement: (tag: string) => new El(tag),
  createTextNode: (s: string) => new Txt(s),
  getElementById: (id: string): El | null => doc.body.querySelector("#" + id),
  querySelectorAll: (sel: string): El[] => doc.body.querySelectorAll(sel),
  addEventListener(type: string, cb: Listener, o?: boolean | { capture?: boolean; once?: boolean }): void { doc.listeners.push({ type, cb, ...optsOf(o) }); },
  removeEventListener(type: string, cb: Listener, o?: boolean | { capture?: boolean }): void {
    const cap = optsOf(o).capture;
    doc.listeners = doc.listeners.filter((l) => !(l.type === type && l.cb === cb && l.capture === cap));
  },
  contains: (n: El | Txt | null) => doc.body.contains(n),
};
doc.body = new El("body"); doc.head = new El("head");
/** The DOM event path: document capture, ancestors' capture root→target, target and ancestors' bubble, document bubble. */
function dispatch(target: El | Txt, ev: Ev): boolean {
  ev.target = target;
  const chain: El[] = [];
  for (let n: El | null = target instanceof El ? target : target.parentNode; n; n = n.parentNode) chain.push(n);
  const run = (owner: { listeners: Reg[] }, capture: boolean, node: El | null): boolean => {
    for (const l of owner.listeners.slice()) {
      if (l.type !== ev.type || l.capture !== capture) continue;
      if (l.once) owner.listeners = owner.listeners.filter((x) => x !== l);
      ev.currentTarget = node; l.cb.call(node, ev);
      if (ev.stopped) return true;
    }
    if (node && !capture && ev.type === "click" && node.onclick) node.onclick(ev);
    return false;
  };
  if (run(doc, true, null)) return !ev.defaultPrevented;
  for (let i = chain.length - 1; i >= 0; i--) if (run(chain[i], true, chain[i])) return !ev.defaultPrevented;
  for (const n of chain) if (run(n, false, n)) return !ev.defaultPrevented;
  run(doc, false, null);
  return !ev.defaultPrevented;
}
const win: any = new EventTarget();
win.parent = win; win.innerWidth = 1200; win.innerHeight = 800;
let selection: any = null;
win.getSelection = () => selection;
win.confirm = () => true;
win.postMessage = () => { /* our own window: nothing listens here */ };
(globalThis as any).window = win;
(globalThis as any).document = doc;
const store = new Map<string, string>();
(globalThis as any).localStorage = {
  getItem: (k: string) => (store.has(k) ? store.get(k)! : null),
  setItem: (k: string, v: string) => { store.set(k, String(v)); },
  removeItem: (k: string) => { store.delete(k); },
};
// The editing substrate: the lazily-loaded CodeMirror chunk registers a window global the viewer's
// editorChunk() resolves from; this one is a buffer with the two callbacks the viewer wires.
const ed = { buf: "", onChange: null as (() => void) | null, mounted: 0, destroyed: 0 };
win.__rompEditor = {
  mount(host: El, opts: { text: string; onChange: () => void; onSave: () => void }) {
    ed.buf = opts.text; ed.onChange = opts.onChange; ed.mounted++;
    host.appendChild(new Txt(opts.text));
    return { value: () => ed.buf, focus() { /* inert */ }, destroy() { ed.destroyed++; } };
  },
};
const typeInto = (s: string) => { ed.buf = s; ed.onChange!(); };

// ── the kernel's /file, /version and /sessions, as the viewer fetches them ──────────────────────────
type Served = { bytes: string | Uint8Array; type: string; mtimeNs: string };
const disk: Record<string, Served> = {};
const fetches: string[] = [];
(globalThis as any).fetch = async (url: string, init?: { method?: string }) => {
  fetches.push((init && init.method || "GET") + " " + url.replace(/[?&]token=[^&]*/, ""));
  if (url.startsWith("/version")) return { json: async () => ({ fileEditing: true }) };   // consent already given
  if (url.startsWith("/sessions")) return { json: async () => [] };
  const p = decodeURIComponent((/[?&]path=([^&]*)/.exec(url) || [])[1] || "");
  const f = disk[p];
  const headers = { get: (h: string) => (f ? (h === "Content-Type" ? f.type : h === "X-Romp-Mtime-Ns" ? f.mtimeNs : h === "X-Romp-Text-Utf8" ? "1" : null) : null) };
  if (!f) return { ok: false, status: 404, headers, text: async () => "no such file: " + p };
  return {
    ok: true, status: 200, headers,
    text: async () => String(f.bytes),
    blob: async () => new Blob([f.bytes as unknown as BlobPart], { type: f.type }),
  };
};

// ── fixtures: the notes-api world ──────────────────────────────────────────────────────────────────
const SID = "11111111-2222-3333-4444-555555555555";
const ROOT = "/repo/notes-api";
const REPORT = ROOT + "/docs/report.md";
const APP = ROOT + "/src/app.py";
const PLOT = ROOT + "/docs/plot.png";
const DOC = "# Report\n\n## Findings\nThe api session cut p95 latency by 40%.\n\nWe recommend shipping the cache in v1.2.\n";
const PY = "def main():\n    return 0\n";
const MT = "1757145600000000001";
const T0 = 1757145600000;
const hunk = (id: string): Hunk => ({ id, author: "api", ts: T0, kind: "replace", curFrom: 28, curTo: 31, baseFrom: 28, baseTo: 31, oldText: "p95", newText: "p99", anchor: null });
function status(hunks: Hunk[]): Status {
  return {
    verb: "status", root: ROOT, storePath: ROOT + "/.trackchanges/docs%2Freport.md.json", trackedBy: { kind: "file", entry: "docs/report.md" },
    agentTooling: "present", fileMtimeNs: MT, storeMtimeNs: "1757145600000000002", configMtimeNs: "1757145600000000003",
    store: { v: 3, path: "docs/report.md", suggestions: [], comments: [] }, hunks,
    unsent: { comments: [], replies: [], accepted: 0, rejected: 0, watermark: null }, log: [],
  };
}
const WARN = "saved, but not written to the comments log for ~/notes-api/docs/report.md: the comments helper failed (exit 1): EACCES: permission denied";
const WARN_READBACK = "saved and written to the comments log, but the comments for ~/notes-api/docs/report.md could not be read back: the sidecar is not valid JSON";

// ── the probe: an action whose only job is to keep the ctx the viewer hands it ──────────────────────
let seam: FileViewActionCtx | null = null;
let paints = 0;
const savedInfos: Array<{ mtimeNs: string; logged: boolean }> = [];
const posted: any[] = [];
let fvMod: typeof import("./file-view") | null = null;
async function mod(): Promise<typeof import("./file-view")> {
  if (fvMod) return fvMod;
  fvMod = await import("./file-view");
  fvMod.initFileView((m) => posted.push(m));
  fvMod.registerFileViewAction({
    id: "seam-probe",
    mount(ctx) { seam = ctx; ctx.onRendered(() => { paints++; }); ctx.onSaved((info) => { savedInfos.push(info); }); return null; },
  });
  fvMod.setFileViewIdentity((sid) => (sid === SID ? { name: "api", color: { bg: "#123456", fg: "#ffffff" } } : null));
  return fvMod;
}
const settle = async () => { for (let i = 0; i < 8; i++) await new Promise<void>((r) => setImmediate(r)); };
type Btns = { rendered: El; raw: El; edit: El; save: El; cancel: El };
type Open = { fv: typeof import("./file-view"); ctx: FileViewActionCtx; wrap: El; body: El; b: Btns };
async function open(p: string, t: TestContext, sid: string | null = SID): Promise<Open> {
  const fv = await mod();
  disk[REPORT] = { bytes: DOC, type: "text/plain; charset=utf-8", mtimeNs: MT };
  disk[APP] = { bytes: PY, type: "text/plain; charset=utf-8", mtimeNs: MT };
  disk[PLOT] = { bytes: new Uint8Array([0x89, 0x50, 0x4e, 0x47]), type: "image/png", mtimeNs: MT };
  posted.length = 0; fetches.length = 0; savedInfos.length = 0; paints = 0; seam = null;
  store.delete("romp:fileviewFmt");                     // every open starts from the default: markdown Rendered
  ed.mounted = 0; ed.destroyed = 0;
  assert.equal(fv.openFileView(p, sid), true, "the open happened");
  t.after(() => { fv.closeFileView(); });
  await settle();
  const wrap = doc.getElementById("romp-fileview")!;
  assert.ok(wrap, "the viewer is up");
  const body = wrap.querySelector(".fileview-body")!;
  const acts = wrap.querySelector(".fileview-acts")!;
  // captured once, by the labels they wear at open: a click relabels Save to "Saving…" (the acknowledgement)
  const btn = (label: string) => { const b = acts.querySelectorAll("button").find((x) => x.textContent === label); assert.ok(b, "the " + label + " button"); return b!; };
  const isMd = p.endsWith(".md");
  const b: Btns = { rendered: isMd ? btn("Rendered") : new El("button"), raw: isMd ? btn("Raw") : new El("button"), edit: btn("Edit"), save: btn("Save"), cancel: btn("Cancel") };
  assert.ok(seam, "the probe action was mounted with the ctx");
  return { fv, ctx: seam!, wrap, body, b };
}
const lastOf = (type: string, verb?: string) => [...posted].reverse().find((m) => m.type === type && (verb === undefined || m.verb === verb));
/** The kernel's answer to the comments panel's status probe — the path a real Edit refusal takes. */
async function answerStatus(s: Status): Promise<void> {
  const m = lastOf("fileComments", "status");
  assert.ok(m, "the panel's status ask is outstanding");
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId: m.reqId, ...s } }));
  await settle();                                        // the panel applies the reply off a promise
}
/** Edit → the consent read → the editor chunk → the buffer: the viewer in edit mode over `text`. */
async function enterEdit(o: Open): Promise<void> {
  o.b.edit.click();
  await settle();
  assert.equal(o.b.save.hidden, false, "edit mode: Save is up");
  assert.ok(o.body.querySelector(".fileview-cm"), "the editor host holds the body");
}
/** Save the buffer as `content`; the saveFile frame goes out and its reqId comes back for the reply. */
function save(o: Open, content: string): number {
  typeInto(content);
  o.b.save.click();
  const m = lastOf("saveFile");
  assert.ok(m, "the save was posted");
  assert.equal(o.b.save.disabled, true); assert.equal(o.b.save.textContent, "Saving…", "acknowledged before the round-trip");
  return m.reqId;
}
const fileSaved = (reqId: number, extra: Record<string, unknown>) =>
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileSaved", reqId, path: REPORT, mtimeNs: "1757145600000000009", ...extra } }));
const errBar = (body: El) => body.querySelector(".fileview-err");

test("mode(), text(), mtimeNs(), media(), identity(), body(): answered from the open viewer's own state, following the Rendered/Raw buttons and setMode", async (t) => {
  const o = await open(REPORT, t);
  const { ctx, body } = o;
  assert.equal(ctx.path, REPORT); assert.equal(ctx.sid, SID);
  assert.equal(ctx.body(), body as unknown as HTMLElement, "the .fileview-body element itself");
  assert.equal(ctx.mode(), "rendered", "a markdown file opens Rendered");
  assert.ok(body.querySelector(".fileview-md"), "…and the body shows the rendered block");
  assert.equal(ctx.text(), DOC); assert.equal(ctx.mtimeNs(), MT); assert.equal(ctx.media(), null);
  assert.deepEqual(ctx.identity(), { name: "api", color: { bg: "#123456", fg: "#ffffff" } }, "resolved through the registered lookup");
  assert.equal(o.wrap.querySelector(".fileview-sess")!.textContent, "api", "the same identity is the title-bar chip");
  assert.equal(paints, 1, "onRendered fired for the open's paint");
  o.b.raw.click();
  assert.equal(ctx.mode(), "raw", "the Raw button is what mode() follows");
  assert.ok(body.querySelector("code.hljs") && !body.querySelector(".fileview-md"));
  assert.equal(paints, 2, "every text paint fires onRendered");
  ctx.setMode("rendered");
  assert.equal(ctx.mode(), "rendered", "setMode through the seam is the same switch");
  assert.equal(paints, 3);
  assert.equal(store.get("romp:fileviewFmt"), JSON.stringify({ md: "rendered" }), "the choice persists per browser");
});

test("a non-markdown text file is raw, and setMode cannot make it rendered", async (t) => {
  const { ctx } = await open(APP, t);
  assert.equal(ctx.mode(), "raw"); assert.equal(ctx.text(), PY); assert.equal(ctx.media(), null);
  ctx.setMode("rendered");
  assert.equal(ctx.mode(), "raw", "setMode is markdown-only");
  assert.equal(paints, 1, "…and repainted nothing");
});

test("an image body is media: mode() media, media() image, text() null, no Edit; close revokes the object URL", async (t) => {
  let revoked = 0;
  const realRevoke = URL.revokeObjectURL;
  URL.revokeObjectURL = ((u: string) => { revoked++; realRevoke.call(URL, u); }) as typeof URL.revokeObjectURL;
  t.after(() => { URL.revokeObjectURL = realRevoke; });
  const { fv, ctx, body, b } = await open(PLOT, t);
  assert.equal(ctx.mode(), "media"); assert.equal(ctx.media(), "image"); assert.equal(ctx.text(), null);
  assert.equal(ctx.mtimeNs(), MT, "the mtime still comes off the kernel's header");
  const img = body.querySelector("img.fileview-img");
  assert.ok(img && img.src.startsWith("blob:"), "one <img> at an object URL");
  assert.equal(b.edit.hidden, true, "image/* is not text/plain: no Edit");
  assert.equal(paints, 0, "a media paint is not a text paint");
  fv.closeFileView();
  assert.equal(revoked, 1, "the bytes leave with the viewer");
});

test("setEditBlocked, from the kernel's hunks through the panel: Edit refuses in words, in place, and opens no editor; null lifts it", async (t) => {
  const o = await open(REPORT, t);
  const { ctx, body, b } = o;
  assert.equal(b.edit.title, "Edit this file in place", "before the kernel has spoken: no reason");
  await answerStatus(status([hunk("h1"), hunk("h2")]));
  const reason = b.edit.title;
  assert.match(reason, /^2 changes are pending in this file, so Edit is off here/, "the panel's reason is the button's tooltip");
  assert.equal(b.edit.classList.contains("fileview-btn-blocked"), true);
  assert.equal(b.edit.hidden, false, "a real button, not a hidden or disabled one — the reason must reach touch and keyboard users");
  assert.equal(b.edit.disabled, false);
  const reads = fetches.length;
  b.edit.click();
  await settle();
  const bar = errBar(body);
  assert.ok(bar, "the refusal is a note bar in the body");
  assert.equal(bar!.textContent, reason);
  assert.equal(bar!.id, "fileview-save-err", "one notice at a time — the save-error slot");
  assert.equal(b.save.hidden, true, "no edit mode");
  assert.equal(ed.mounted, 0, "no editor was mounted");
  assert.equal(fetches.length, reads, "not even the consent read ran — the refusal is first");
  ctx.setEditBlocked(null);
  assert.equal(b.edit.title, "Edit this file in place");
  assert.equal(b.edit.classList.contains("fileview-btn-blocked"), false);
  await enterEdit(o);
  assert.equal(ed.mounted, 1);
  assert.equal(errBar(body), null, "the refusal left with the repaint");
});

test("fileSaved: onSaved hears mtimeNs and logged; a reply carrying logWarning puts the kernel's words in the note bar over the saved body; a clean reply leaves no bar", async (t) => {
  const o = await open(REPORT, t);
  const { ctx, body, b } = o;
  await enterEdit(o);
  assert.equal(ctx.mode(), "raw", "markdown edits from its Raw view");
  const v2 = DOC + "\nMore.\n";
  const reqId = save(o, v2);
  const frame = lastOf("saveFile");
  assert.deepEqual(frame, { type: "saveFile", path: REPORT, sid: SID, content: v2, baseMtimeNs: MT, reqId });
  fileSaved(reqId, { logged: false, logWarning: WARN });
  assert.deepEqual(savedInfos, [{ mtimeNs: "1757145600000000009", logged: false }], "the seam's onSaved: the panel refreshes its Log off this");
  assert.equal(ctx.mtimeNs(), "1757145600000000009", "the save fence moves to the kernel's new mtime");
  assert.equal(ctx.text(), v2, "text() is the saved bytes");
  assert.equal(b.save.hidden, true); assert.equal(b.edit.hidden, false, "edit mode left");
  assert.equal(b.save.disabled, false); assert.equal(b.save.textContent, "Save", "re-armed for the next edit");
  assert.equal(ed.destroyed, 1);
  const bar = errBar(body);
  assert.ok(bar, "the comments-log warning is shown — a silent Log without its entry is the failure mode this closes");
  assert.equal(bar!.textContent, WARN, "the kernel's own words, unreworded");
  assert.equal(body.childNodes[0], bar, "above the body, where a save failure would sit");
  assert.ok(body.querySelector("code.hljs"), "…and the saved bytes are painted under it: the save landed");
  // a read-back failure (logged: true, still a warning) is shown the same way
  await enterEdit(o);
  const v3 = v2 + "Again.\n";
  fileSaved(save(o, v3), { logged: true, logWarning: WARN_READBACK });
  assert.equal(savedInfos[1].logged, true);
  assert.equal(errBar(body)!.textContent, WARN_READBACK);
  // a clean reply: the previous bar goes with the repaint and no new one is raised
  await enterEdit(o);
  fileSaved(save(o, v3 + "Once more.\n"), { logged: true });
  assert.equal(errBar(body), null, "nothing to say, nothing shown");
  assert.equal(savedInfos.length, 3);
});

test("in-flight typing: a fileSaved with logWarning keeps edit mode and the newer keystrokes, re-arms Save, and still shows the warning above the editor", async (t) => {
  const o = await open(REPORT, t);
  const { ctx, body, b } = o;
  await enterEdit(o);
  const v2 = DOC + "\nMore.\n";
  const reqId = save(o, v2);
  typeInto(v2 + "typed while saving");                 // the buffer moved past the snapshot the save carried
  fileSaved(reqId, { logged: false, logWarning: WARN });
  assert.equal(b.save.hidden, false, "still editing");
  assert.equal(b.save.disabled, false); assert.equal(b.save.textContent, "Save", "re-armed");
  assert.equal(ed.destroyed, 0, "the editor and its newer keystrokes survive the ack");
  assert.equal(ctx.text(), v2, "the saved snapshot is the new baseline");
  assert.equal(body.childNodes.length, 2, "the note bar and the editor host, nothing else");
  assert.equal((body.childNodes[0] as El).className, "fileview-err");
  assert.equal(body.childNodes[0].textContent, WARN);
  assert.equal((body.childNodes[1] as El).className, "fileview-cm");
});

test("onSelection fires on mouseup inside the body ahead of the quote-chip gate; reload re-fetches; onClose drains on a replace-open and on close; post rides the pane's poster", async (t) => {
  const o = await open(REPORT, t);
  const { fv, ctx, body } = o;
  const seen: unknown[] = [];
  ctx.onSelection((sel) => { seen.push(sel); });
  selection = { isCollapsed: false, rangeCount: 1, anchorNode: body.querySelector(".fileview-md"), toString: () => "cache" };
  const reads = fetches.length;
  body.dispatchEvent(new Ev("mouseup"));
  assert.equal(seen.length, 1); assert.equal(seen[0], selection, "the live selection, as is");
  assert.equal(fetches.length, reads, "no composer anywhere: the chip's fresh read never ran, the hook still did");
  selection = null;
  ctx.post({ type: "fileComments", verb: "probe" });
  assert.deepEqual(posted[posted.length - 1], { type: "fileComments", verb: "probe" }, "the seam's post is the pane's poster");
  const v2 = DOC + "\nThe session appended this.\n";
  disk[REPORT] = { bytes: v2, type: "text/plain; charset=utf-8", mtimeNs: "1757145600000000007" };
  const before = paints;
  ctx.reload();
  await settle();
  assert.equal(ctx.text(), v2); assert.equal(ctx.mtimeNs(), "1757145600000000007");
  assert.equal(paints, before + 1, "the reload repaints and fires onRendered");
  let closed = 0;
  ctx.onClose(() => { closed++; });
  assert.equal(fv.openFileView(APP, SID), true);        // a replace-open: the old viewer's hooks drain
  assert.equal(closed, 1, "the replace path drains onClose");
  await settle();
  const ctx2 = seam!;
  assert.notEqual(ctx2, ctx, "a new open, a new ctx");
  assert.equal(ctx2.path, APP);
  let closed2 = 0;
  ctx2.onClose(() => { closed2++; });
  fv.closeFileView();
  assert.equal(closed2, 1, "closeFileView drains onClose");
  assert.equal(closed, 1, "…and never the previous open's hooks again");
  assert.equal(doc.getElementById("romp-fileview"), null);
  assert.equal(doc.body.classList.contains("fileview-open"), false);
});

test("scrollToOffset maps a source offset to its Raw row: one .fv-cl per logical line", async (t) => {
  const o = await open(REPORT, t);
  o.b.raw.click();
  const code = o.body.querySelector("code.hljs")!;
  // the stand-in does not parse innerHTML; lay the rows codeBlock's markup would produce
  const lines = DOC.split("\n"); lines.pop();
  code.replaceChildren(...lines.map((ln) => { const cl = new El("span"); cl.className = "fv-cl"; cl.appendChild(new Txt(ln)); return cl; }));
  const rows = code.querySelectorAll(".fv-cl");
  o.ctx.scrollToOffset(DOC.indexOf("The api session"));
  assert.equal(rows[3].scrolled, 1, "offset → the third newline → row 3");
  assert.equal(rows.map((r) => r.scrolled).reduce((a, b) => a + b, 0), 1, "one row scrolled");
  o.ctx.scrollToOffset(DOC.length + 50);
  assert.equal(rows[rows.length - 1].scrolled, 1, "past the end clamps to the last row");
});

// ── what the DOM run above would not catch on its own, pinned at source ────────────────────────────

test("source: the seam's closures are the viewer's own state, and the fileSaved branch reads the kernel's logWarning", () => {
  assert.match(VIEW, /setEditBlocked: \(reason\) => \{\n\s*editBlocked = reason;/, "the reason is stored, not dropped");
  assert.match(VIEW, /mode: \(\) => \(isImage \|\| isPdf\) && !\(svgSource && svgText !== null\) \? "media" : isMd && fmt\.md === "rendered" \? "rendered" : "raw",/);
  assert.match(VIEW, /let editHooks: \{ reqId: number; logWarning: string \| null; saved: \(mtimeNs: string, logged: boolean\) => void;/, "the save's hooks carry the warning");
  const reply = VIEW.split('m.type === "fileSaved" && editHooks')[1].split("} else if")[0];
  assert.match(reply, /h\.logWarning = typeof m\.logWarning === "string" && m\.logWarning \? m\.logWarning : null;\n\s*h\.saved\(String\(m\.mtimeNs \|\| ""\), m\.logged === true\);/,
    "read off the reply, the only place the text exists, before the ack runs");
  const saved = VIEW.split("saved: (mtNs, logged) => {")[1].split("\n      },")[0];
  assert.match(saved, /const noteLog = \(\) => \{ if \(hooks\.logWarning\) noteBar\(hooks\.logWarning\); \};/);
  assert.equal((saved.match(/\n\s*noteLog\(\);/g) || []).length, 2, "shown on both save outcomes: the in-flight-typing stay, and edit mode left");
  assert.ok(saved.indexOf("noteLog();") < saved.indexOf("if (bufValue() !== null"), "before the stay, which repaints nothing");
  assert.ok(saved.indexOf("exitEdit();") < saved.lastIndexOf("noteLog();"), "and after exitEdit's repaint, so the paint cannot wipe it");
});

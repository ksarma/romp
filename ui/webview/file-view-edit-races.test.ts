// Two races inside edit mode at the REAL openFileView (plans/file-review.md Slice 5; the review of that slice):
//
// 1. A save whose ack lands over in-flight typing keeps the editor, and with it the chunk's ledger of decisions,
//    which has no reset. The next Save used to read the same ledger and re-send the same accept/reject entries; the
//    host applied them again, logged them twice, and the Send confirm counted two accepted changes for one. The viewer
//    now keeps the decisions each landed save carried (`applied`) and sends only what the ledger holds beyond them.
// 2. A file fetch in flight when Edit is clicked (the poll saw the file move, then the person clicked) used to land
//    inside edit mode: the mtime moved to the newer file while the editor's buffer came from the older bytes, so both
//    save doors passed their fence and overwrote a session's write silently — the case the fence exists to refuse.
//    The viewer now applies headers and bytes in one step, paints nothing while the editor is up, and re-reads the
//    file when the edit ends.
//
// The DOM stand-in, the editor-chunk stub and the kernel stubs are the ones file-view-seam.test.ts carries. node:test
// runs each bundled file in its own process and that file exports nothing, so this one carries its own copy, trimmed
// of the PDF and media parts, with one addition: a gate that holds a file response's headers or its body until a test
// releases it. Synthetic fixtures only: the notes-api world, placeholder ids.
import { test, type TestContext } from "node:test";
import * as assert from "node:assert/strict";
import type { FileViewActionCtx } from "./file-view";
import type { Status, Hunk } from "./file-comments-model";

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
  splitText(off: number): Txt {
    const tail = new Txt(this.data.slice(off));
    this.data = this.data.slice(0, off);
    const p = this.parentNode;
    if (p) { const i = p.childNodes.indexOf(this); p.childNodes.splice(i + 1, 0, tail); tail.parentNode = p; }
    return tail;
  }
}
type Compound = { tag: string | null; id: string | null; classes: string[]; attrs: Array<[string, string | null]> };
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
  scrolled = 0;
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
win.getSelection = () => null;
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

// ── the editor chunk: a buffer, the two callbacks, and the track option's handle (records + a ledger with no reset) ──
type Entry = { id: string; oldText: string; newText: string };
type Decided = { accepted: Entry[]; rejected: Entry[] };
type TrackStub = { suggestions: unknown[]; authorColor: (a: string) => string | null; onLedger: (l: Decided) => void };
const ed = {
  buf: "", onChange: null as (() => void) | null, mounted: 0, destroyed: 0,
  trackOpts: null as TrackStub | null, records: [] as unknown[], ledger: { accepted: [], rejected: [] } as Decided,
};
win.__rompEditor = {
  mount(host: El, opts: { text: string; onChange: () => void; onSave: () => void; track?: TrackStub }) {
    ed.buf = opts.text; ed.onChange = opts.onChange; ed.mounted++; ed.trackOpts = opts.track || null;
    host.appendChild(new Txt(opts.text));
    const h: { value(): string; focus(): void; destroy(): void; track?: { suggestions(): unknown[]; ledger(): Decided } } =
      { value: () => ed.buf, focus() { /* inert */ }, destroy() { ed.destroyed++; } };
    if (opts.track) {
      ed.records = opts.track.suggestions.slice(); ed.ledger = { accepted: [], rejected: [] };
      h.track = { suggestions: () => ed.records, ledger: () => ed.ledger };
    }
    return h;
  },
};
const typeInto = (s: string) => { ed.buf = s; ed.onChange!(); };
/** An in-editor decision: the chunk drops the record from its field and reports the ledger (no text change on an accept). */
const decideInEditor = (side: "accepted" | "rejected", id: string) => {
  ed.records = ed.records.filter((r) => (r as { id: string }).id !== id);
  ed.ledger = { ...ed.ledger, [side]: [...ed.ledger[side], entry(id)] };
  ed.trackOpts!.onLedger(ed.ledger);
};
/** The chunk's ledger after an undo or a redo: what the field now holds, reported as the real chunk reports it. */
const reledger = (ledger: Decided, pending: string[]) => {
  ed.ledger = ledger; ed.records = pending.map(record);
  ed.trackOpts!.onLedger(ed.ledger);
};

// ── the kernel's /file, /version and /sessions, as the viewer fetches them — with a gate ──────────────
type Served = { bytes: string; type: string; mtimeNs: string };
const disk: Record<string, Served> = {};
const fetches: string[] = [];
/** Holds the NEXT file GET: `headers` keeps the whole response back, `body` lets the headers land and keeps the bytes back. */
let gate: { headers?: Promise<void>; body?: Promise<void> } | null = null;
const deferred = () => { let resolve!: () => void; const p = new Promise<void>((r) => { resolve = r; }); return { p, resolve }; };
(globalThis as any).fetch = async (url: string, init?: { method?: string }) => {
  const method = (init && init.method) || "GET";
  fetches.push(method + " " + url.replace(/[?&]token=[^&]*/, ""));
  if (url.startsWith("/version")) return { json: async () => ({ fileEditing: true }) };
  if (url.startsWith("/sessions")) return { json: async () => [{ id: SID, name: "api", bg: "#123456", fg: "#ffffff" }] };
  const p = decodeURIComponent((/[?&]path=([^&]*)/.exec(url) || [])[1] || "");
  const f = disk[p];                                   // the file as the kernel reads it NOW: headers and bytes agree
  const g = method === "GET" ? gate : null;
  if (g) gate = null;
  if (g && g.headers) await g.headers;
  const headers = { get: (h: string) => (f ? (h === "Content-Type" ? f.type : h === "X-Romp-Mtime-Ns" ? f.mtimeNs : h === "X-Romp-Text-Utf8" ? "1" : null) : null) };
  if (!f) return { ok: false, status: 404, headers, text: async () => { if (g && g.body) await g.body; return "no such file: " + p; } };
  return {
    ok: true, status: 200, headers,
    text: async () => { if (g && g.body) await g.body; return f.bytes; },
    blob: async () => new Blob([f.bytes], { type: f.type }),
  };
};

// ── fixtures: the notes-api world ──────────────────────────────────────────────────────────────────
const SID = "11111111-2222-3333-4444-555555555555";
const ROOT = "/repo/notes-api";
const REPORT = ROOT + "/docs/report.md";
const APP = ROOT + "/src/app.py";
const DOC = "# Report\n\n## Findings\nThe api session cut p95 latency by 40%.\n\nWe recommend shipping the cache in v1.2.\n";
const PY = "def main():\n    return 0\n";
const MT = "1757145600000000001";
const NS = (n: number) => "17571456000000000" + String(n).padStart(2, "0");   // a later mtime, in the fixture's own clock
const T0 = 1757145600000;
const hunk = (id: string): Hunk => ({ id, author: "api", ts: T0, kind: "sub", curFrom: 28, curTo: 31, baseFrom: 28, baseTo: 31, oldText: "p95", newText: "p99", anchor: null });
const record = (id: string) => ({ id, author: "api", authorId: SID, ts: T0, kind: "sub", from: DOC.indexOf("p95"), newText: "p99", oldText: "p95" });
const entry = (id: string): Entry => ({ id, oldText: "p95", newText: "p99" });
function status(hunks: Hunk[], over: Partial<Status> = {}): Status {
  return {
    verb: "status", root: ROOT, storePath: ROOT + "/.trackchanges/docs%2Freport.md.json", trackedBy: { kind: "file", entry: "docs/report.md" },
    agentTooling: "present", fileMtimeNs: MT, storeMtimeNs: NS(2), configMtimeNs: NS(3),
    store: { v: 3, path: "docs/report.md", suggestions: hunks.map((h) => record(h.id)), comments: [] }, hunks,
    unsent: { comments: [], replies: [], accepted: 0, rejected: 0, watermark: null }, log: [],
    ...over,
  };
}
const UNTRACKED: Status = { ...status([]), storePath: null, trackedBy: null, store: null, storeMtimeNs: null };
const FILE_MOVED = "the file ~/notes-api/docs/report.md changed on disk since you opened the file — reload and retry";

// ── the probe: an action whose only job is to keep the ctx the viewer hands it ──────────────────────
let seam: FileViewActionCtx | null = null;
const savedInfos: Array<{ mtimeNs: string; logged: boolean }> = [];
const posted: any[] = [];
let fvMod: typeof import("./file-view") | null = null;
async function mod(): Promise<typeof import("./file-view")> {
  if (fvMod) return fvMod;
  fvMod = await import("./file-view");
  fvMod.initFileView((m) => posted.push(m));
  fvMod.registerFileViewAction({
    id: "seam-probe",
    mount(ctx) { seam = ctx; ctx.onSaved((info) => { savedInfos.push(info); }); return null; },
  });
  fvMod.setFileViewIdentity((sid) => (sid === SID ? { name: "api", color: { bg: "#123456", fg: "#ffffff" } } : null));
  return fvMod;
}
const settle = async () => { for (let i = 0; i < 8; i++) await new Promise<void>((r) => setImmediate(r)); };
type Btns = { edit: El; save: El; cancel: El };
type Open = { fv: typeof import("./file-view"); ctx: FileViewActionCtx; wrap: El; body: El; b: Btns };
async function open(p: string, t: TestContext): Promise<Open> {
  const fv = await mod();
  disk[REPORT] = { bytes: DOC, type: "text/plain; charset=utf-8", mtimeNs: MT };
  disk[APP] = { bytes: PY, type: "text/plain; charset=utf-8", mtimeNs: MT };
  posted.length = 0; fetches.length = 0; savedInfos.length = 0; seam = null; gate = null;
  store.delete("romp:fileviewFmt");
  ed.mounted = 0; ed.destroyed = 0; ed.trackOpts = null; ed.records = []; ed.ledger = { accepted: [], rejected: [] };
  assert.equal(fv.openFileView(p, SID), true, "the open happened");
  t.after(() => { fv.closeFileView(); });
  await settle();
  const wrap = doc.getElementById("romp-fileview")!;
  assert.ok(wrap, "the viewer is up");
  const body = wrap.querySelector(".fileview-body")!;
  const acts = wrap.querySelector(".fileview-acts")!;
  const btn = (label: string) => { const b = acts.querySelectorAll("button").find((x) => x.textContent === label); assert.ok(b, "the " + label + " button"); return b!; };
  const b: Btns = { edit: btn("Edit"), save: btn("Save"), cancel: btn("Cancel") };
  assert.ok(seam, "the probe action was mounted with the ctx");
  return { fv, ctx: seam!, wrap, body, b };
}
const lastOf = (type: string, verb?: string) => [...posted].reverse().find((m) => m.type === type && (verb === undefined || m.verb === verb));
const countOf = (type: string, verb?: string) => posted.filter((m) => m.type === type && (verb === undefined || m.verb === verb)).length;
async function answerStatus(s: Status): Promise<void> {
  const m = lastOf("fileComments", "status");
  assert.ok(m, "the panel's status ask is outstanding");
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId: m.reqId, ...s } }));
  await settle();
}
async function enterEdit(o: Open): Promise<void> {
  o.b.edit.click();
  await settle();
  assert.equal(o.b.save.hidden, false, "edit mode: Save is up");
  assert.ok(o.body.querySelector(".fileview-cm"), "the editor host holds the body");
}
/** Save through the PANEL: the `save` verb goes out; the frame comes back for its args, fence and reqId. */
function saveTracked(o: Open, content: string): any {
  typeInto(content);
  const saves = countOf("saveFile");
  o.b.save.click();
  const m = lastOf("fileComments", "save");
  assert.ok(m, "the save went through the panel");
  assert.equal(countOf("saveFile"), saves, "…and not through saveFile");
  assert.equal(o.b.save.disabled, true); assert.equal(o.b.save.textContent, "Saving…", "acknowledged before the round-trip");
  return m;
}
const saveReply = async (reqId: number, s: Status) => {
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId, ...s, verb: "save", logged: true } }));
  await settle();
};
const saveRefused = async (reqId: number, code: string, error: string) => {
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsFailed", reqId, verb: "save", code, error } }));
  await settle();
};
const errBar = (body: El) => body.querySelector(".fileview-err");
const fileGets = () => fetches.filter((f) => f.startsWith("GET /file")).length;

// ── 1. the ledger across saves ──────────────────────────────────────────────────────────────────────

test("a save acked over in-flight typing keeps the editor and its ledger; the next Save sends only the decisions taken since, and a fresh Edit starts a fresh ledger", async (t) => {
  const o = await open(REPORT, t);
  const { ctx, b } = o;
  await answerStatus(status([hunk("h1"), hunk("h2")]));
  await enterEdit(o);
  decideInEditor("accepted", "h1");
  const m1 = saveTracked(o, DOC + "one\n");
  assert.deepEqual(m1.args, { content: DOC + "one\n", suggestions: [record("h2")], accepted: [entry("h1")], rejected: [] });
  typeInto(DOC + "one\ntwo");                          // typed during the round-trip
  await saveReply(m1.reqId, status([hunk("h2")], { fileMtimeNs: NS(9), storeMtimeNs: NS(10) }));
  assert.equal(ctx.editing(), true, "the in-flight keystrokes keep edit mode");
  assert.equal(ed.destroyed, 0); assert.equal(b.save.disabled, false); assert.equal(b.save.textContent, "Save", "re-armed");
  assert.equal(ctx.mtimeNs(), NS(9), "the fence moved to the saved file");
  assert.deepEqual(ed.ledger, { accepted: [entry("h1")], rejected: [] }, "the chunk's ledger still holds h1: it has no reset");
  const m2 = saveTracked(o, DOC + "one\ntwo\n");
  assert.deepEqual(m2.args, { content: DOC + "one\ntwo\n", suggestions: [record("h2")], accepted: [], rejected: [] },
    "the host applied and logged h1 with the first save: it is not sent again");
  assert.deepEqual(m2.fence, { storeMtimeNs: NS(10), configMtimeNs: NS(3), fileMtimeNs: NS(9) }, "fenced on the first save's reply");
  await saveReply(m2.reqId, status([hunk("h2")], { fileMtimeNs: NS(11), storeMtimeNs: NS(12) }));
  assert.equal(ctx.editing(), false, "nothing typed and nothing undecided during this round-trip: edit mode ends");
  assert.equal(ed.destroyed, 1);
  assert.deepEqual(savedInfos.map((i) => i.mtimeNs), [NS(9), NS(11)]);
  // a new editor is a new ledger (the mount's), and what it decides goes out once
  await enterEdit(o);
  decideInEditor("accepted", "h2");
  const m3 = saveTracked(o, DOC + "one\ntwo\n");
  assert.deepEqual(m3.args, { content: DOC + "one\ntwo\n", suggestions: [], accepted: [entry("h2")], rejected: [] });
});

test("after the in-flight ack, restoring the saved bytes leaves nothing to save: Save leaves edit mode and posts no second save", async (t) => {
  const o = await open(REPORT, t);
  const { ctx, b } = o;
  await answerStatus(status([hunk("h1")]));
  await enterEdit(o);
  decideInEditor("accepted", "h1");
  const m1 = saveTracked(o, DOC);
  assert.deepEqual(m1.args.accepted, [entry("h1")]);
  typeInto(DOC + "q");
  await saveReply(m1.reqId, status([], { fileMtimeNs: NS(9), storeMtimeNs: NS(10) }));
  assert.equal(ctx.editing(), true);
  typeInto(DOC);                                       // the keystroke undone by hand: the buffer is the saved bytes again
  const saves = countOf("fileComments", "save");
  b.save.click();
  await settle();
  assert.equal(countOf("fileComments", "save"), saves, "no save: the text is the file's and every decision has landed");
  assert.equal(ctx.editing(), false, "leaving is the honest ack");
  assert.equal(ed.destroyed, 1);
});

test("a decision clicked during the round-trip (no keystroke) is not lost with the editor: edit mode stays and the next Save carries it alone", async (t) => {
  const o = await open(REPORT, t);
  const { ctx, b } = o;
  await answerStatus(status([hunk("h1"), hunk("h2")]));
  await enterEdit(o);
  const m1 = saveTracked(o, DOC + "a");
  assert.deepEqual(m1.args.accepted, []);
  decideInEditor("accepted", "h1");                    // an accept moves no text: the buffer still equals the saved snapshot
  await saveReply(m1.reqId, status([hunk("h1"), hunk("h2")], { fileMtimeNs: NS(9), storeMtimeNs: NS(10) }));
  assert.equal(ctx.editing(), true, "the ledger holds a decision no save carried");
  assert.equal(ed.destroyed, 0); assert.equal(b.save.disabled, false);
  const m2 = saveTracked(o, DOC + "a");
  assert.deepEqual(m2.args, { content: DOC + "a", suggestions: [record("h2")], accepted: [entry("h1")], rejected: [] });
});

test("an id decided again after its save: undone and redone sends nothing; undone and reversed sends the reversal; reversed again, it is new again", async (t) => {
  const o = await open(REPORT, t);
  await answerStatus(status([hunk("h1")]));
  await enterEdit(o);
  decideInEditor("accepted", "h1");
  const m1 = saveTracked(o, DOC);
  typeInto(DOC + "x");
  await saveReply(m1.reqId, status([], { fileMtimeNs: NS(9), storeMtimeNs: NS(10) }));
  // undo the accept (the record is back in the field), redo it: the ledger reads as it did when the save landed
  reledger({ accepted: [], rejected: [] }, ["h1"]);
  reledger({ accepted: [entry("h1")], rejected: [] }, []);
  const m2 = saveTracked(o, DOC + "x\n");
  assert.deepEqual([m2.args.accepted, m2.args.rejected], [[], []], "the same decision is not a new one");
  typeInto(DOC + "x\ny");
  await saveReply(m2.reqId, status([], { fileMtimeNs: NS(11), storeMtimeNs: NS(12) }));
  // undo the accept and reject instead: the reject is new, and the log will read accept, reject — what happened
  reledger({ accepted: [], rejected: [entry("h1")] }, []);
  const m3 = saveTracked(o, DOC + "x\ny\n");
  assert.deepEqual([m3.args.accepted, m3.args.rejected], [[], [entry("h1")]]);
  typeInto(DOC + "x\ny\nz");
  await saveReply(m3.reqId, status([], { fileMtimeNs: NS(13), storeMtimeNs: NS(14) }));
  // back to accept: the landed save moved h1 to the rejected side, so an accept is a new decision again
  reledger({ accepted: [entry("h1")], rejected: [] }, []);
  const m4 = saveTracked(o, DOC + "x\ny\nz\n");
  assert.deepEqual([m4.args.accepted, m4.args.rejected], [[entry("h1")], []]);
  // a refused save applied nothing: the next Save carries the same decision again
  await saveRefused(m4.reqId, "desync", "change h1 does not fit the text being saved to ~/notes-api/docs/report.md: the text at 42..45 is not the change's text; nothing was changed — reload and retry");
  assert.equal(o.b.save.disabled, false, "the refusal reached the bar and Save is re-armed");
  assert.equal(lastOf("fileComments", "save").reqId, m4.reqId, "a desync is not retried");
  const again = saveTracked(o, DOC + "x\ny\nz\n\n");
  assert.deepEqual([again.args.accepted, again.args.rejected], [[entry("h1")], []]);
});

// ── 2. a fetch landing under the editor ─────────────────────────────────────────────────────────────

test("a fetch in flight at Edit (its headers landed, its bytes not): the editor keeps the bytes it loaded AND their mtime, the tracked save fences on that mtime so the host refuses, and Cancel reads the newer file", async (t) => {
  const o = await open(REPORT, t);
  const { ctx, body, b } = o;
  await answerStatus(status([]));                      // tracked, nothing pending: Save routes through the panel
  const NEW = DOC + "The api session appended this line.\n";
  disk[REPORT] = { bytes: NEW, type: "text/plain; charset=utf-8", mtimeNs: NS(7) };   // a session wrote the file
  const held = deferred();
  gate = { body: held.p };
  ctx.reload();                                        // the poll's reload, before Edit
  await settle();
  assert.equal(ctx.mtimeNs(), MT, "the headers alone move nothing: mtime and bytes are applied together");
  assert.equal(ctx.text(), DOC);
  await enterEdit(o);                                  // the person clicks Edit while the bytes are still in flight
  assert.equal(ed.buf, DOC, "the editor mounted the bytes the view held");
  held.resolve();
  await settle();
  assert.equal(ctx.editing(), true);
  assert.ok(body.querySelector(".fileview-cm"), "the editor host still holds the body: the landing painted nothing");
  assert.equal(ctx.mtimeNs(), MT, "the fence is the file the editor LOADED, not the one that landed under it");
  assert.equal(ctx.text(), DOC, "text() is the buffer");
  const m = saveTracked(o, DOC + "x");
  assert.equal(m.fence.fileMtimeNs, MT, "the host compares this to the newer file and refuses: the session's write is not overwritten");
  assert.equal(m.args.content, DOC + "x");
  await saveRefused(m.reqId, "file-moved", FILE_MOVED);
  const bar = errBar(body)!;
  assert.match(bar.childNodes[0].textContent, /^the file .* changed on disk/);
  assert.equal(bar.querySelector("button")!.textContent, "Reload file");
  assert.equal(ed.destroyed, 0, "the buffer stays");
  // the edit ends: the exit is the event the dropped bytes were waiting for
  const gets = fileGets();
  b.cancel.click();
  await settle();
  assert.equal(ctx.editing(), false);
  assert.equal(fileGets(), gets + 1, "one re-read, at the exit");
  assert.equal(ctx.text(), NEW, "the view shows the file as it is now");
  assert.equal(ctx.mtimeNs(), NS(7));
});

test("the same race with the whole response in flight, on an untracked file: saveFile's baseMtimeNs is the mtime the editor loaded", async (t) => {
  const u = await open(APP, t);
  await answerStatus(UNTRACKED);
  disk[APP] = { bytes: PY + "y = 2\n", type: "text/plain; charset=utf-8", mtimeNs: NS(7) };
  const held = deferred();
  gate = { headers: held.p };
  u.ctx.reload();
  await settle();
  await enterEdit(u);
  assert.equal(ed.buf, PY);
  held.resolve();
  await settle();
  assert.equal(u.ctx.editing(), true); assert.equal(u.ctx.mtimeNs(), MT); assert.equal(u.ctx.text(), PY);
  typeInto(PY + "x = 1\n");
  u.b.save.click();
  const m = lastOf("saveFile");
  assert.ok(m, "the untracked path posts saveFile");
  assert.equal(m.baseMtimeNs, MT, "the kernel's conflict floor is the loaded file: a moved file refuses");
  assert.equal(m.content, PY + "x = 1\n");
  assert.equal(lastOf("fileComments", "save"), undefined);
});

test("a fetch that FAILS under the editor paints no error pane over it; the exit re-reads and says why then", async (t) => {
  const o = await open(REPORT, t);
  const { ctx, body, b } = o;
  await answerStatus(status([]));
  delete disk[REPORT];                                 // the file is gone by the time the poll's reload runs
  const held = deferred();
  gate = { headers: held.p };
  ctx.reload();
  await settle();
  await enterEdit(o);
  held.resolve();
  await settle();
  assert.equal(ctx.editing(), true);
  assert.ok(body.querySelector(".fileview-cm"), "the editor's host survives the failed landing");
  assert.equal(errBar(body), null, "no error pane over the editor");
  b.cancel.click();
  await settle();
  assert.equal(ctx.editing(), false);
  assert.match(errBar(body)!.textContent, /^no such file: /, "the re-read's failure shows once the editor is gone");
});

test("a successful save while a dropped fetch is owed: the reply is the file as it stands, so the exit re-reads nothing", async (t) => {
  const o = await open(REPORT, t);
  const { ctx } = o;
  await answerStatus(status([]));
  const held = deferred();
  gate = { body: held.p };
  ctx.reload();                                        // the same bytes and mtime: a panel Reload control, not a moved file
  await settle();
  await enterEdit(o);
  held.resolve();
  await settle();
  assert.equal(ctx.editing(), true);
  const m = saveTracked(o, DOC + "s");
  await saveReply(m.reqId, status([], { fileMtimeNs: NS(9) }));
  const gets = fileGets();
  assert.equal(ctx.editing(), false);
  await settle();
  assert.equal(fileGets(), gets, "no re-read: the save's reply already said what the file is");
  assert.equal(ctx.text(), DOC + "s"); assert.equal(ctx.mtimeNs(), NS(9));
});

test("two reloads in flight land in either order: the newest fetch is the one that shows", async (t) => {
  const o = await open(REPORT, t);
  const { ctx } = o;
  const V1 = DOC + "first\n", V2 = DOC + "second\n";
  disk[REPORT] = { bytes: V1, type: "text/plain; charset=utf-8", mtimeNs: NS(5) };
  const held = deferred();
  gate = { body: held.p };
  ctx.reload();                                        // A: headers in, bytes held
  await settle();
  disk[REPORT] = { bytes: V2, type: "text/plain; charset=utf-8", mtimeNs: NS(6) };
  ctx.reload();                                        // B: lands whole
  await settle();
  assert.equal(ctx.text(), V2); assert.equal(ctx.mtimeNs(), NS(6));
  held.resolve();                                      // A lands last…
  await settle();
  assert.equal(ctx.text(), V2, "…and replaces nothing: its bytes are older");
  assert.equal(ctx.mtimeNs(), NS(6));
});

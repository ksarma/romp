// Two events the viewer raises for the comments panel and the person at the REAL openFileView (plans/file-review.md
// Slice 5; the review of that slice):
//
// 1. Edit with the aside open. The panel's change cards read the seam's editing() at render time: while the editor holds
//    the body they show the decide-in-editor caption, dim Accept and Reject with that caption as their title, and offer
//    neither Reveal nor the link into the read view (the viewer's setMode and scrollToOffset are no-ops then). The
//    viewer used to ask the panel's begin() (whose render is the only paint Edit triggered) BEFORE editing flipped, and
//    renderBody fires no onRendered in edit mode, so a panel open at Edit kept its read-mode cards: live-looking Reveal
//    and links that did nothing, undimmed buttons with read-mode tooltips, no caption, until some unrelated status
//    happened to land. The panel's own tests set editing before begin(), the reverse of the viewer's order, so only a
//    test through the real viewer sees it. The viewer now fires onRendered once edit mode is entered, as the editor takes
//    the body: that render is the cards' edit-mode one, and the exit's repaint hands the read-mode state back. A refused
//    mount still touches nothing (begin() keeps running before the flip).
// 2. A save acked after Cancel while a NEW editor is up. That editor mounted over the bytes from before the save; the
//    ack finds it and re-reads nothing (the editor holds the truth), but said nothing either, so the person learned that
//    their own save had moved the file under them only from the next Save's file-moved refusal. The viewer now says so
//    at the ack, above the editor, with the same Reload offer that refusal carries; the buffer stays and Cancel re-reads.
//
// The DOM stand-in, the editor-chunk stub and the kernel stubs are the ones file-view-edit-races.test.ts carries (node:test
// runs each bundled file in its own process and that file exports nothing), with the tracked-edit file's older-bundle
// switch and a Comments button. Synthetic fixtures only: the notes-api world, placeholder ids.
import { test, type TestContext } from "node:test";
import * as assert from "node:assert/strict";
import type { FileViewActionCtx } from "./file-view";
import type { Status, Hunk } from "./file-comments-model";
import { DECIDE_IN_EDITOR, DECIDE_IN_EDITOR_TOUCH } from "./file-comments";

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

// ── the editor chunk: a buffer, the two callbacks, and the track option's handle (records + decisions with no reset) ──
type Entry = { id: string; oldText: string; newText: string };
type Decided = { accepted: Entry[]; rejected: Entry[] };
type TrackStub = { suggestions: unknown[]; authorColor: (a: string) => string | null; onDecisions: (l: Decided) => void };
const ed = {
  buf: "", onChange: null as (() => void) | null, mounted: 0, destroyed: 0,
  tracks: true,                                        // false: the bundle predates the option and returns a handle without `track`
  trackOpts: null as TrackStub | null, records: [] as unknown[], decisions: { accepted: [], rejected: [] } as Decided,
};
win.__rompEditor = {
  mount(host: El, opts: { text: string; onChange: () => void; onSave: () => void; track?: TrackStub }) {
    ed.buf = opts.text; ed.onChange = opts.onChange; ed.mounted++; ed.trackOpts = opts.track || null;
    host.appendChild(new Txt(opts.text));
    const h: { value(): string; focus(): void; destroy(): void; track?: { suggestions(): unknown[]; decisions(): Decided } } =
      { value: () => ed.buf, focus() { /* inert */ }, destroy() { ed.destroyed++; } };
    if (opts.track && ed.tracks) {
      ed.records = opts.track.suggestions.slice(); ed.decisions = { accepted: [], rejected: [] };
      h.track = { suggestions: () => ed.records, decisions: () => ed.decisions };
    }
    return h;
  },
};
const typeInto = (s: string) => { ed.buf = s; ed.onChange!(); };
/** An in-editor decision: the chunk drops the record from its field and reports the decisions (no text change on an accept). */
const decideInEditor = (side: "accepted" | "rejected", id: string) => {
  ed.records = ed.records.filter((r) => (r as { id: string }).id !== id);
  ed.decisions = { ...ed.decisions, [side]: [...ed.decisions[side], entry(id)] };
  ed.trackOpts!.onDecisions(ed.decisions);
};
/** The chunk's decisions after an undo or a redo: what the field now holds, reported as the real chunk reports it. */
const redecide = (decisions: Decided, pending: string[]) => {
  ed.decisions = decisions; ed.records = pending.map(record);
  ed.trackOpts!.onDecisions(ed.decisions);
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
const recordOf = (h: Hunk) => ({ id: h.id, author: "api", authorId: SID, ts: T0, kind: h.kind, from: h.curFrom, newText: h.newText, oldText: h.oldText });
const record = (id: string) => recordOf(hunk(id));
// the session removed " now" after "shipping": a deletion is a point in the current text, so the card offers Reveal in the read view
const DEL_AT = DOC.indexOf(" the cache");
const del = (id: string): Hunk => ({ id, author: "api", ts: T0, kind: "del", curFrom: DEL_AT, curTo: DEL_AT, baseFrom: DEL_AT, baseTo: DEL_AT + 4, oldText: " now", newText: "", anchor: null });
const entry = (id: string): Entry => ({ id, oldText: "p95", newText: "p99" });
function status(hunks: Hunk[], over: Partial<Status> = {}): Status {
  return {
    verb: "status", root: ROOT, storePath: ROOT + "/.trackchanges/docs%2Freport.md.json", trackedBy: { kind: "file", entry: "docs/report.md" },
    agentTooling: "present", fileMtimeNs: MT, storeMtimeNs: NS(2), configMtimeNs: NS(3),
    store: { v: 3, path: "docs/report.md", suggestions: hunks.map(recordOf), comments: [] }, hunks,
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
type Btns = { edit: El; save: El; cancel: El; comments: El };
type Open = { fv: typeof import("./file-view"); ctx: FileViewActionCtx; wrap: El; body: El; b: Btns };
async function open(p: string, t: TestContext): Promise<Open> {
  const fv = await mod();
  disk[REPORT] = { bytes: DOC, type: "text/plain; charset=utf-8", mtimeNs: MT };
  disk[APP] = { bytes: PY, type: "text/plain; charset=utf-8", mtimeNs: MT };
  posted.length = 0; fetches.length = 0; savedInfos.length = 0; seam = null; gate = null;
  store.delete("romp:fileviewFmt");
  ed.mounted = 0; ed.destroyed = 0; ed.tracks = true; ed.trackOpts = null; ed.records = []; ed.decisions = { accepted: [], rejected: [] };
  assert.equal(fv.openFileView(p, SID), true, "the open happened");
  t.after(() => { fv.closeFileView(); });
  await settle();
  const wrap = doc.getElementById("romp-fileview")!;
  assert.ok(wrap, "the viewer is up");
  const body = wrap.querySelector(".fileview-body")!;
  const acts = wrap.querySelector(".fileview-acts")!;
  const btn = (label: string) => { const b = acts.querySelectorAll("button").find((x) => x.textContent === label); assert.ok(b, "the " + label + " button"); return b!; };
  const comments = acts.querySelector(".fileview-fc button")!;
  assert.ok(comments, "the Comments button");
  const b: Btns = { edit: btn("Edit"), save: btn("Save"), cancel: btn("Cancel"), comments };
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
/** Opens the aside through the real Comments button (its refresh asks status) and answers that ask with `s`. */
async function openAside(o: Open, s: Status): Promise<El> {
  o.b.comments.click(); await settle();
  await answerStatus(s);
  const aside = o.wrap.querySelector(".fc-panel");
  assert.ok(aside, "the aside is open");
  return aside!;
}
const acts = (aside: El, act: string) => aside.querySelectorAll('[data-act="' + act + '"]');
const DECIDE = new Set([DECIDE_IN_EDITOR, DECIDE_IN_EDITOR_TOUCH]);   // the caption's words, by pointer kind (the panel's DECIDE_TEXTS)
const READ_TITLES = { fcaccept: "Keep the text as it is and drop the change", fcreject: "Put the old text back in the file", fcacceptall: "Keep the text as it is and drop every change", fcrejectall: "Put the old text back for every change" };
/** The change cards as the read view offers them: the read-mode titles, no dimming, no caption. */
function expectReadMode(aside: El, where: string): void {
  assert.equal(aside.querySelector(".fc-decide-edit"), null, where + ": no decide-in-editor caption");
  for (const [act, title] of Object.entries(READ_TITLES)) {
    const btns = acts(aside, act);
    assert.ok(btns.length, where + ": " + act + " is offered");
    for (const b of btns) { assert.equal(b.title, title, where + ": " + act + " read-mode title"); assert.equal(b.classList.contains("fileview-btn-blocked"), false, where + ": " + act + " not dimmed"); }
  }
}
/** The change cards while the editor holds the body: decisions answer in place, no link or Reveal into a read view that is gone. */
function expectEditMode(aside: El, where: string): void {
  const cap = aside.querySelector(".fc-decide-edit");
  assert.ok(cap, where + ": the caption says to decide in the editor, without a click");
  assert.ok(DECIDE.has(cap!.textContent), where + ": in the panel's words");
  for (const act of Object.keys(READ_TITLES)) {
    const btns = acts(aside, act);
    assert.ok(btns.length, where + ": " + act + " stays a real button");
    for (const b of btns) { assert.ok(DECIDE.has(b.title), where + ": " + act + " says where to decide"); assert.equal(b.classList.contains("fileview-btn-blocked"), true, where + ": " + act + " dimmed"); }
  }
  assert.equal(acts(aside, "fcreveal").length, 0, where + ": no Reveal: setMode and scrollToOffset are no-ops while editing");
  assert.equal(acts(aside, "fcgoto").length, 0, where + ": no link into a read view that is gone");
  assert.deepEqual(aside.querySelectorAll(".fc-tag").map((x) => x.textContent).filter((x) => x === "not shown"), [], where + ": the editor shows the deletion");
}
const MOVED_AT_ACK = "Your earlier save landed after you reopened the editor, so this editor shows the file as it was before that save. Save from it will refuse; Cancel shows the saved file.";

// ── 1. the cards take their edit-mode state at Edit ─────────────────────────────────────────────────

test("Edit with the aside open: the change cards take their edit-mode state at Edit (caption, dimmed Accept/Reject, no Reveal or link), and the read-mode offers return at Cancel", async (t) => {
  const o = await open(REPORT, t);
  const { ctx, body, b } = o;
  const pending = [hunk("h1"), del("h2")];             // a painted substitution and a deletion (Reveal-only in the read view)
  await answerStatus(status(pending));                 // the panel's mount-time ask
  const aside = await openAside(o, status(pending));
  expectReadMode(aside, "before Edit");
  assert.ok(acts(aside, "fcreveal").length >= 1, "before Edit: the deletion offers Reveal");
  const gotos = acts(aside, "fcgoto").length;
  assert.ok(gotos >= 1, "before Edit: the painted substitution's ref is a link");
  await enterEdit(o);
  assert.equal(ctx.editing(), true);
  expectEditMode(aside, "after Edit");
  assert.ok(body.querySelector(".fileview-cm"), "the editor host holds the body");
  // the edit ends with nothing typed: the read view is back, and so are its offers
  b.cancel.click();
  await settle();
  assert.equal(ctx.editing(), false);
  expectReadMode(aside, "after Cancel");
  assert.ok(acts(aside, "fcreveal").length >= 1, "after Cancel: Reveal is back");
  // Edit moved the markdown to its Raw view; back in Rendered (the view the link was painted in) the link is back too.
  // (Raw is exact in a browser; this stand-in's code block has no text nodes to paint, so the link is asserted where the
  // stand-in can paint it.)
  ctx.setMode("rendered");
  await settle();
  assert.equal(acts(aside, "fcgoto").length, gotos, "after Cancel, in Rendered again: the link is back");
});

test("an Edit refused at the mount (an older editor bundle) leaves the cards in read mode: no caption over a read view that never left", async (t) => {
  const o = await open(REPORT, t);
  const { ctx, body, b } = o;
  const pending = [hunk("h1"), del("h2")];
  await answerStatus(status(pending));
  const aside = await openAside(o, status(pending));
  ed.tracks = false;                                   // the bundle predates the track option
  b.edit.click();
  await settle();
  assert.equal(ed.mounted, 1, "the tracked mount was tried…");
  assert.equal(ctx.editing(), false, "…and the handle without `track` ended it");
  assert.match(errBar(body)!.textContent, /pending in this file, so Edit is off here/);
  expectReadMode(aside, "after the refusal");
  assert.ok(acts(aside, "fcreveal").length >= 1, "the deletion still offers Reveal");
});

// ── 2. a save acked under a new editor ──────────────────────────────────────────────────────────────

test("Cancel during a tracked save, then Edit again before the ack: the ack says the file moved under this editor, above it, with Reload; the buffer and the fence stay, and Cancel re-reads", async (t) => {
  const o = await open(REPORT, t);
  const { ctx, body, b } = o;
  await answerStatus(status([hunk("h1")]));            // one pending change: Save routes through the panel
  await enterEdit(o);
  const m = saveTracked(o, DOC + "x");
  b.cancel.click();                                    // confirm says yes: edit mode ends while the host is writing
  await settle();
  assert.equal(ctx.editing(), false); assert.equal(ed.destroyed, 1);
  await enterEdit(o);                                  // a second editor, over the pre-save bytes and the pre-save records
  assert.equal(ed.mounted, 2); assert.equal(ed.buf, DOC); assert.equal(ctx.mtimeNs(), MT);
  assert.deepEqual(ed.trackOpts!.suggestions, [record("h1")]);
  typeInto(DOC + "y");                                 // typing in the second editor
  assert.equal(errBar(body), null, "nothing said yet: nothing has happened yet");
  const gets = fileGets();
  disk[REPORT] = { bytes: DOC + "x", type: "text/plain; charset=utf-8", mtimeNs: NS(9) };   // the host wrote the first save
  await saveReply(m.reqId, status([], { fileMtimeNs: NS(9), storeMtimeNs: NS(10) }));
  assert.equal(ctx.editing(), true, "the late ack touches no editor");
  assert.equal(ed.destroyed, 1, "the second editor stays");
  assert.equal(ed.buf, DOC + "y", "with its typing");
  assert.equal(ctx.mtimeNs(), MT, "the fence is the file this editor loaded, so a Save from it refuses rather than overwrite the landed save");
  assert.equal(fileGets(), gets, "no read while the editor holds the truth");
  const bar = errBar(body)!;
  assert.ok(bar, "the ack is the event: the viewer says the file moved under this editor");
  assert.equal(body.childNodes[0], bar, "above the editor host…");
  assert.ok(body.querySelector(".fileview-cm"), "…which still holds the body");
  assert.equal(bar.childNodes[0].textContent, MOVED_AT_ACK);
  assert.doesNotMatch(bar.textContent, /—/, "no dashes in the words");
  assert.equal(bar.querySelector("button")!.textContent, "Reload file", "the same offer the later refusal would carry");
  assert.deepEqual(savedInfos.map((i) => i.mtimeNs), [NS(9)], "the seam's onSaved still fires: the panel's bookkeeping completes");
  assert.equal(b.save.hidden, false); assert.equal(b.save.disabled, false); assert.equal(b.save.textContent, "Save", "Save is untouched: the refusal, if it comes, is the host's");
  // Cancel: the exit is the event the owed read waited for, and the bar leaves with the editor
  b.cancel.click();
  await settle();
  assert.equal(ctx.editing(), false);
  assert.equal(fileGets(), gets + 1, "one re-read, at the exit");
  assert.equal(ctx.text(), DOC + "x"); assert.equal(ctx.mtimeNs(), NS(9));
  assert.equal(errBar(body), null, "the bar went with the editor");
});

test("the same ack's Reload file reopens the viewer on the saved bytes (behind the discard confirm)", async (t) => {
  const o = await open(REPORT, t);
  const { body, b } = o;
  await answerStatus(status([hunk("h1")]));
  await enterEdit(o);
  const m = saveTracked(o, DOC + "x");
  b.cancel.click(); await settle();
  await enterEdit(o);
  typeInto(DOC + "y");
  disk[REPORT] = { bytes: DOC + "x", type: "text/plain; charset=utf-8", mtimeNs: NS(9) };
  await saveReply(m.reqId, status([], { fileMtimeNs: NS(9), storeMtimeNs: NS(10) }));
  let asked = 0;
  win.confirm = () => { asked++; return true; };
  t.after(() => { win.confirm = () => true; });
  const gets = fileGets();
  errBar(body)!.querySelector("button")!.click();
  await settle();
  assert.equal(asked, 1, "the dirty buffer is discarded only behind the confirm");
  assert.equal(fileGets(), gets + 1, "the reopen reads the disk");
  assert.equal(seam!.editing(), false, "a fresh viewer, in read mode");
  assert.equal(seam!.text(), DOC + "x", "on the saved bytes"); assert.equal(seam!.mtimeNs(), NS(9));
});

test("a save acked after Cancel with NO new editor up re-reads at once and says nothing: the view shows the saved file", async (t) => {
  const o = await open(REPORT, t);
  const { ctx, body, b } = o;
  await answerStatus(status([hunk("h1")]));
  await enterEdit(o);
  const m = saveTracked(o, DOC + "x");
  b.cancel.click(); await settle();
  const gets = fileGets();
  disk[REPORT] = { bytes: DOC + "x", type: "text/plain; charset=utf-8", mtimeNs: NS(9) };
  await saveReply(m.reqId, status([], { fileMtimeNs: NS(9), storeMtimeNs: NS(10) }));
  assert.equal(fileGets(), gets + 1, "one re-read, at the ack");
  assert.equal(ctx.text(), DOC + "x"); assert.equal(ctx.mtimeNs(), NS(9));
  assert.equal(errBar(body), null, "nothing moved under anything: no bar");
});

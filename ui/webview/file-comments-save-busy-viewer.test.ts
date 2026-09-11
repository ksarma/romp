// The viewer's half of a Save refused `busy` (plans/file-review.md, decision 49: the host's lock on the sidecar was
// still held by another writer after its wait), at the REAL openFileView. The panel's half (one status re-read, one
// retry with the fresh fence, the refusal handed on with its code and the host's words) is file-comments-save-busy.test.ts's,
// over a stand-in ctx; that suite stops at the TrackedEdit.save boundary and never runs the viewer's failed arm. The arm
// offers Reload file on `busy` as it does on a moved fence (file-view.ts, showSaveError's `moved`), and until this file that
// offer was held by two source pins alone (file-view.test.ts's ARM_CLOSE anchor, tools/file-review-plan-sidecar.test.mjs):
// with `|| code === "busy"` removed from the arm, every behavioral viewer suite stayed green, and a second `busy` on a save
// through the panel showed the host's words with no way to see what the other writer wrote (the slice review, 2026-09-11).
// The host's `busy` text names no disk change (`another editor is writing <path>; retry`), so showSaveError's fallback
// on the kernel's conflict wording (`changed on disk`) does not catch it: the offer rests on the code, and only a test
// that reads the bar after a real refusal pins it. Here the viewer runs over the seam suite's DOM stand-in
// (file-view-seam.test.ts, copied and trimmed as file-view-edit-races.test.ts copies it: node --test runs each bundled
// file in its own process and that file exports nothing), the panel is the real one, and each case is checked by what the
// viewer DOES: the bar's words, the button, the re-armed Save, the surviving buffer, and Reload's ask and re-open. A
// `busy` whose re-read shows the records changed carries the head's row into the bar in place of the host's words
// (file-comments.ts, underEditRefusal): both are read here, from the bar and from the opened panel's head.
// Synthetic fixtures only: the notes-api world, placeholder ids.
import { test, type TestContext } from "node:test";
import * as assert from "node:assert/strict";
import { inspect } from "node:util";
import { assertHiddenEvent, hideEdges, staysEnumerable } from "../test-dom-shim";
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
    hideEdges(this);
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
  parentNode!: El | null;
  constructor(public data: string) { Object.defineProperty(this, "parentNode", { value: null, writable: true, enumerable: false, configurable: true }); hideEdges(this); }
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
  parentNode!: El | null;
  childNodes!: Array<El | Txt>;
  attrs = new Map<string, string>();
  listeners: Reg[] = [];
  hidden = false; disabled = false; title = ""; type = ""; value = ""; placeholder = ""; spellcheck = true; wrap = "";
  src = ""; alt = ""; href = ""; download = ""; target = ""; rel = "";
  innerHTML = "";
  style: Record<string, string> = {};
  onclick: ((ev: Ev) => void) | null = null;
  scrolled = 0;
  constructor(tag: string) {
    this.tagName = tag.toUpperCase();
    Object.defineProperty(this, "parentNode", { value: null, writable: true, enumerable: false, configurable: true });
    Object.defineProperty(this, "childNodes", { value: [], writable: true, enumerable: false, configurable: true });
    hideEdges(this);
  }
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
  set textContent(v: string) { for (const c of this.childNodes) c.parentNode = null; this.childNodes.length = 0; if (v !== "") this.appendChild(new Txt(v)); }
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
win.getSelection = () => null;
win.confirm = () => true;
win.postMessage = () => { /* our own window: nothing listens here */ };
(globalThis as any).window = win;
(globalThis as any).location = { protocol: "http:" };   // the web dashboard: the viewer's discard ask is a confirm here (canPreview)
(globalThis as any).document = doc;
const store = new Map<string, string>();
(globalThis as any).localStorage = {
  getItem: (k: string) => (store.has(k) ? store.get(k)! : null),
  setItem: (k: string, v: string) => { store.set(k, String(v)); },
  removeItem: (k: string) => { store.delete(k); },
};

// ── the editor chunk: a buffer, the two callbacks, and the track option's handle (records + decisions) ──
type Entry = { id: string; oldText: string; newText: string };
type Decided = { accepted: Entry[]; rejected: Entry[] };
type TrackStub = { suggestions: unknown[]; authorColor: (a: string) => string | null; onDecisions: (l: Decided) => void };
const ed = {
  buf: "", onChange: null as (() => void) | null, mounted: 0, destroyed: 0,
  trackOpts: null as TrackStub | null, records: [] as unknown[], decisions: { accepted: [], rejected: [] } as Decided,
};
win.__rompEditor = {
  mount(host: El, opts: { text: string; onChange: () => void; onSave: () => void; track?: TrackStub }) {
    ed.buf = opts.text; ed.onChange = opts.onChange; ed.mounted++; ed.trackOpts = opts.track || null;
    host.appendChild(new Txt(opts.text));
    const h: { value(): string; focus(): void; destroy(): void; track?: { suggestions(): unknown[]; decisions(): Decided } } =
      { value: () => ed.buf, focus() { /* inert */ }, destroy() { ed.destroyed++; } };
    if (opts.track) {
      ed.records = opts.track.suggestions.slice(); ed.decisions = { accepted: [], rejected: [] };
      h.track = { suggestions: () => ed.records, decisions: () => ed.decisions };
    }
    return h;
  },
};
const typeInto = (s: string) => { ed.buf = s; ed.onChange!(); };

// ── the kernel's /file, /version and /sessions, as the viewer fetches them ──────────────────────────
type Served = { bytes: string; type: string; mtimeNs: string };
const disk: Record<string, Served> = {};
const fetches: string[] = [];
(globalThis as any).fetch = async (url: string, init?: { method?: string }) => {
  const method = (init && init.method) || "GET";
  fetches.push(method + " " + url.replace(/[?&]token=[^&]*/, ""));
  if (url.startsWith("/version")) return { json: async () => ({ fileEditing: true }) };   // consent already given
  if (url.startsWith("/sessions")) return { json: async () => [{ id: SID, name: "api", bg: "#123456", fg: "#ffffff" }] };
  const p = decodeURIComponent((/[?&]path=([^&]*)/.exec(url) || [])[1] || "");
  const f = disk[p];
  const headers = { get: (h: string) => (f ? (h === "Content-Type" ? f.type : h === "X-Romp-Mtime-Ns" ? f.mtimeNs : h === "X-Romp-Text-Utf8" ? "1" : null) : null) };
  if (!f) return { ok: false, status: 404, headers, text: async () => "no such file: " + p };
  return { ok: true, status: 200, headers, text: async () => f.bytes, blob: async () => new Blob([f.bytes], { type: f.type }) };
};

// ── fixtures: the notes-api world ──────────────────────────────────────────────────────────────────
const SID = "11111111-2222-3333-4444-555555555555";
const ROOT = "/repo/notes-api";
const REPORT = ROOT + "/docs/report.md";
const DOC = "# Report\n\n## Findings\nThe api session cut p95 latency by 40%.\n\nWe recommend shipping the cache in v1.2.\n";
const MT = "1757145600000000001";
const NS = (n: number) => "17571456000000000" + String(n).padStart(2, "0");   // a later mtime, in the fixture's own clock
const T0 = 1757145600000;
const hunk = (id: string): Hunk => ({ id, author: "api", ts: T0, kind: "sub", curFrom: 28, curTo: 31, baseFrom: 28, baseTo: 31, oldText: "p95", newText: "p99", anchor: null });
const record = (id: string) => ({ id, author: "api", authorId: SID, ts: T0, kind: "sub", from: DOC.indexOf("p95"), newText: "p99", oldText: "p95" });
function status(hunks: Hunk[], over: Partial<Status> = {}): Status {
  return {
    verb: "status", root: ROOT, storePath: ROOT + "/.trackchanges/docs%2Freport.md.json", trackedBy: { kind: "file", entry: "docs/report.md" },
    agentTooling: "present", fileMtimeNs: MT, storeMtimeNs: NS(2), configMtimeNs: NS(3),
    store: { v: 3, path: "docs/report.md", suggestions: hunks.map((h) => record(h.id)), comments: [] }, hunks,
    unsent: { comments: [], replies: [], accepted: 0, rejected: 0, watermark: null }, log: [],
    ...over,
  };
}
/** The host's refusal, verbatim (tools/file-comments-host.mjs, underStoreLock): the path as the host shows it. */
const BUSY = "another editor is writing ~/notes-api/docs/report.md; retry";
const S9 = NS(20);                                      // the sidecar's clock after the other writer's rename landed
const RELOAD_TITLE = "Fetch the file as it is now (asks before discarding your edits)";

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
  posted.length = 0; fetches.length = 0; savedInfos.length = 0; seam = null;
  store.delete("romp:fileviewFmt");
  ed.mounted = 0; ed.destroyed = 0; ed.trackOpts = null; ed.records = []; ed.decisions = { accepted: [], rejected: [] };
  win.confirm = () => true;
  assert.equal(fv.openFileView(p, SID), true, "the open happened");
  t.after(() => { fv.closeFileView(); });
  await settle();
  const wrap = doc.getElementById("romp-fileview")!;
  assert.ok(wrap, "the viewer is up");
  const body = wrap.querySelector(".fileview-body")!;
  const acts = wrap.querySelector(".fileview-acts")!;
  // captured once, by the labels they wear at open: a click relabels Save to "Saving…" (the acknowledgement)
  const btn = (label: string) => { const b = acts.querySelectorAll("button").find((x) => x.textContent === label); assert.ok(b, "the " + label + " button"); return b!; };
  const b: Btns = { edit: btn("Edit"), save: btn("Save"), cancel: btn("Cancel") };
  assert.ok(seam, "the probe action was mounted with the ctx");
  return { fv, ctx: seam!, wrap, body, b };
}
const lastOf = (type: string, verb?: string) => [...posted].reverse().find((m) => m.type === type && (verb === undefined || m.verb === verb));
const countOf = (type: string, verb?: string) => posted.filter((m) => m.type === type && (verb === undefined || m.verb === verb)).length;
/** The kernel's answer to the comments panel's status probe. */
async function answerStatus(s: Status): Promise<void> {
  const m = lastOf("fileComments", "status");
  assert.ok(m, "the panel's status ask is outstanding");
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId: m.reqId, ...s } }));
  await settle();                                        // the panel applies the reply off a promise
}
/** Edit → the consent read → the editor chunk → the buffer: the viewer in edit mode over the file. */
async function enterEdit(o: Open): Promise<void> {
  o.b.edit.click();
  await settle();
  assert.equal(o.b.save.hidden, false, "edit mode: Save is up");
  assert.ok(o.body.querySelector(".fileview-cm"), "the editor host holds the body");
}
/** Save the buffer as `content` through the PANEL (a tracked file): the `save` verb's frame, for its args, fence and reqId. */
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
// the viewer's notice bar (file-view.ts noteBar, #fileview-save-err) is a child of the card before .fileview-main, so it
// is read from the card: the card's first .fileview-err is the bar when one is up
const cardOf = (body: El) => body.parentNode!.parentNode as El;
const errBar = (body: El) => cardOf(body).querySelector(".fileview-err");
/** The bar stands right above the body row (the editor stands untouched under it). */
const aboveRow = (body: El) => { const main = body.parentNode!, box = cardOf(body), bar = errBar(body); return !!bar && box.childNodes.indexOf(bar) === box.childNodes.indexOf(main) - 1; };
/** Edit over one pending change, type `content`, Save, and take the first `busy`: the panel's one status re-read is out. */
async function saveIntoBusy(o: Open, content: string): Promise<{ first: any; asks: number }> {
  await answerStatus(status([hunk("h1")]));
  await enterEdit(o);
  const first = saveTracked(o, content);
  const asks = countOf("fileComments", "status");
  await saveRefused(first.reqId, "busy", BUSY);
  assert.equal(lastOf("fileComments").verb, "status", "one re-read before deciding: the other writer's write is on disk by now");
  assert.equal(countOf("fileComments", "status"), asks + 1);
  assert.equal(errBar(o.body), null, "nothing said to the person yet");
  assert.equal(o.b.save.disabled, true); assert.equal(o.b.save.textContent, "Saving…", "still saving through the retry");
  return { first, asks: asks + 1 };
}

test("a save refused busy, retried once and refused busy again: the bar holds the host's words verbatim with Reload file, Save is re-armed and the buffer survives; Save again goes out fenced on the re-read's sidecar, and its landing takes the bar down with the editor", async (t) => {
  const o = await open(REPORT, t);
  const { body, b } = o;
  const v2 = DOC.replace("40%", "45%");
  const { first, asks } = await saveIntoBusy(o, v2);
  // a reply a session wrote mid-edit moved the sidecar's clock; its records are the editor's: the panel retries once
  await answerStatus(status([hunk("h1")], { storeMtimeNs: S9 }));
  const again = lastOf("fileComments", "save");
  assert.notEqual(again.reqId, first.reqId, "the one retry");
  assert.deepEqual(again.fence, { storeMtimeNs: S9, configMtimeNs: NS(3), fileMtimeNs: MT }, "re-fenced on the sidecar as it stands after the other writer");
  assert.deepEqual(again.args, first.args, "the same text, records and decisions");
  assert.equal(errBar(body), null, "still nothing said: the retry is the panel's");
  // the lock is still held: the refusal reaches the viewer
  await saveRefused(again.reqId, "busy", BUSY);
  assert.equal(countOf("fileComments", "save"), 2, "one retry, never a third");
  assert.equal(countOf("fileComments", "status"), asks, "no re-read after the second refusal: the bar is the next move");
  const bar = errBar(body)!;
  assert.ok(bar, "the refusal is the note bar over the editor");
  assert.equal(bar.childNodes[0].textContent, BUSY, "the host's words, verbatim");
  assert.doesNotMatch(BUSY, /changed on disk/, "…which are not the kernel's conflict wording, so the offer below rests on the code");
  const reload = bar.querySelector("button");
  assert.ok(reload, "busy offers Reload file: the other writer's text is on disk, and a reload shows it");
  assert.equal(reload!.textContent, "Reload file");
  assert.equal(reload!.title, RELOAD_TITLE);
  assert.equal(bar.querySelectorAll("button").length, 1, "one offer");
  assert.equal(b.save.hidden, false); assert.equal(b.save.disabled, false); assert.equal(b.save.textContent, "Save", "re-armed");
  assert.equal(ed.destroyed, 0, "the buffer survives"); assert.equal(ed.buf, v2);
  assert.equal(o.ctx.editing(), true); assert.equal(o.ctx.text(), v2, "the seam still answers the buffer");
  assert.equal(body.childNodes[0], body.querySelector(".fileview-cm"), "the editor host is still the body, under the bar");
  assert.ok(aboveRow(body), "the bar stands above the row");
  // Save again from the re-armed button: straight out, fenced on the sidecar the re-read showed, no re-read before it
  const third = saveTracked(o, v2);
  assert.notEqual(third.reqId, again.reqId);
  assert.deepEqual(third.fence, { storeMtimeNs: S9, configMtimeNs: NS(3), fileMtimeNs: MT }, "the saving editor's fence followed the re-read");
  assert.equal(countOf("fileComments", "status"), asks, "no re-read before it");
  // the writer is gone and the save lands: the reply is the viewer's saved event, the editor leaves, the bar goes with it
  await saveReply(third.reqId, status([], { fileMtimeNs: NS(9), storeMtimeNs: NS(10) }));
  assert.deepEqual(savedInfos, [{ mtimeNs: NS(9), logged: true }]);
  assert.equal(o.ctx.mtimeNs(), NS(9), "the save fence moves to the host's new file mtime");
  assert.equal(o.ctx.editing(), false); assert.equal(b.save.hidden, true); assert.equal(b.edit.hidden, false, "edit mode left");
  assert.equal(ed.destroyed, 1);
  assert.equal(errBar(body), null, "the landed save takes the refusal's bar down with the editor");
  assert.equal(countOf("fileComments", "status"), asks, "no status re-ask after the save: the reply IS the panel's status");
});

// The re-read shows the records changed under the editor: the head's row (CHANGES_MOVED_UNDER_EDIT) is raised by that
// re-read, and the bar carries the SAME words under the `busy` code, not the host's "; retry" — the host's words were
// true while the lock was held and are stale once the re-read has shown other records, and a bar asking for a retry over
// a head saying Save will refuse sent the person into one refused round trip before the accurate words arrived (the slice
// review's stale-bar finding, 2026-09-11). The code keeps the Reload offer: the other writer's text is on disk.
test("a save refused busy whose re-read shows the sidecar's records changed: no retry, the bar carries the head's row (Save will refuse; copy, Cancel, Edit again) with Reload file, and the head says the same; Reload asks first, a no keeps the buffer and the viewer, a yes re-opens the file fresh, reading", async (t) => {
  const fc = await import("./file-comments");
  const o = await open(REPORT, t);
  const { body, b } = o;
  const v2 = DOC.replace("40%", "45%");
  const { first, asks } = await saveIntoBusy(o, v2);
  // the writer that held the lock recorded a second change: the records are no longer the editor's
  await answerStatus(status([hunk("h1"), hunk("h2")], { storeMtimeNs: S9 }));
  assert.equal(countOf("fileComments", "save"), 1, "no retry: the records changed under the editor");
  assert.equal(lastOf("fileComments", "save").reqId, first.reqId);
  assert.equal(countOf("fileComments", "status"), asks, "and no second re-read");
  const bar = errBar(body)!;
  assert.ok(bar, "the refusal is the note bar over the editor");
  assert.equal(bar.childNodes[0].textContent, fc.CHANGES_MOVED_UNDER_EDIT, "the head's row's words, not the host's");
  assert.notEqual(bar.childNodes[0].textContent, BUSY);
  assert.match(bar.childNodes[0].textContent, /Save will refuse; copy anything you typed, then Cancel and Edit again/, "what a Save would do, and what to do instead");
  // the head says the same: open the Comments aside and read its row
  const acts = o.wrap.querySelector(".fileview-acts")!;
  const comments = acts.querySelectorAll("button").find((x) => /^Comments/.test(x.textContent));
  assert.ok(comments, "the panel's button in the action row");
  comments!.click();
  await settle();
  const aside = o.wrap.querySelector(".fileview-aside")!;
  assert.ok(aside, "the panel is open beside the body");
  await answerStatus(status([hunk("h1"), hunk("h2")], { storeMtimeNs: S9 }));   // the open's own refresh
  const rows = aside.querySelectorAll(".fc-sec-head .fc-err");
  assert.equal(rows.length, 1, "one row in the head");
  assert.equal(rows[0].childNodes[0].textContent, bar.childNodes[0].textContent, "…and it is the bar's text: one instruction on screen, not two");
  comments!.click();                                   // closed again: the rest of the case is the viewer's
  await settle();
  assert.equal(o.wrap.querySelector(".fileview-aside"), null);
  assert.equal(errBar(body), bar, "the bar stands through the panel's open and close");
  assert.equal(countOf("fileComments", "status"), asks + 1, "the open's refresh was the one ask since the re-read");
  const asksNow = countOf("fileComments", "status");
  const reload = bar.querySelector("button")!;
  assert.ok(reload, "with Reload file");
  assert.equal(reload.textContent, "Reload file");
  assert.equal(reload.title, RELOAD_TITLE);
  assert.equal(b.save.hidden, false); assert.equal(b.save.disabled, false); assert.equal(b.save.textContent, "Save", "re-armed");
  assert.equal(ed.destroyed, 0, "the buffer survives"); assert.equal(ed.buf, v2);
  assert.ok(aboveRow(body), "the bar stands above the editor's row");
  // Reload: asks (the buffer is dirty), and a no keeps everything
  let asked = 0;
  win.confirm = () => { asked++; return false; };
  reload.click();
  await settle();
  assert.equal(asked, 1, "the discard question");
  assert.equal(ed.destroyed, 0, "declined: the buffer stays");
  assert.equal(doc.getElementById("romp-fileview"), o.wrap, "…and so does the viewer, editor and bar");
  assert.equal(errBar(body), bar);
  assert.equal(o.ctx.editing(), true);
  // a yes re-opens the same file fresh: reading, over the disk as it is now, with a fresh status probe
  win.confirm = () => { asked++; return true; };
  reload.click();
  await settle();
  assert.equal(asked, 2, "asked once per click, never twice for one");
  const fresh = doc.getElementById("romp-fileview")!;
  assert.ok(fresh && fresh !== o.wrap, "accepted: a fresh viewer replaced the old one, buffer and all");
  assert.equal(fresh.querySelector(".fileview-cm"), null, "…reading, not editing");
  assert.equal(fresh.querySelector(".fileview-err"), null, "…with no bar carried over");
  assert.equal(countOf("fileComments", "status"), asksNow + 1, "the fresh panel probes status");
  assert.equal(fetches.filter((f) => f.startsWith("GET /file")).length, 2, "the re-open read the file again");
});

// ── the stand-in's projection (ui/test-dom-shim.ts): a node inspects as its primitives, never as the tree ─────────────
test("a stand-in node enumerates its primitives alone, so a failing assertion's dump shows neither parentNode nor childNodes", () => {
  const root = new El("div"); root.className = "row";
  const child = root.appendChild(new El("span")); child.appendChild(new Txt("alpha")); root.appendChild(new Txt("beta"));
  for (const n of [root, child, root.childNodes[1]] as Array<El | Txt>) {
    for (const k of Object.keys(n)) assert.ok(staysEnumerable((n as any)[k]), k + " is enumerable and holds a " + typeof (n as any)[k]);
    const dump = inspect(n, { compact: false, customInspect: false, depth: 1000, maxArrayLength: Infinity, showHidden: false, showProxy: false, sorted: true, getters: true });
    assert.ok(!dump.includes("parentNode") && !dump.includes("childNodes"), "the dump holds no edge: " + dump);
  }
  assert.ok(child.parentNode === root && root.childNodes[0] === child && root.textContent === "alphabeta", "the tree is reachable as before");
  assertHiddenEvent(new Ev("click"), root, child);
});

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
import { inspect } from "node:util";
import { assertHiddenEvent, hideEdges, sameNodes, staysEnumerable } from "../test-dom-shim";
import { codeOnly, stripComments } from "../test-code-only";   // the comment stripper every source pin below reads through (the compiler's ranges)
import * as ts from "typescript";                              // the compiler enumerates the census's imports and bindings (the test build keeps typescript a runtime require)
import * as fs from "node:fs";
import * as path from "node:path";
import DOMPurify from "dompurify";   // the module-global instance md-sanitize.ts imports, for the record pin on the seam's constraint
import type { FileViewActionCtx, At } from "./file-view";
import type { Status, Hunk } from "./file-comments-model";
import { setMdSanitizer, sanitizeMd, MD_PURIFY } from "./md-sanitize";   // the sanitizer seam the node suites install a stand-in through (Slice 7 of plans/markdown-viewer.md); sanitizeMd and the profile for the inertness pins
import { marked } from "marked";                   // the singleton the viewer parses with: one case makes its lexer throw (the Slice 7 review's round 2)

const web = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const VIEW = web("file-view.ts");

// ── a DOM stand-in: ancestry, ids, attributes, events with capture and bubbling, a small selector engine ──
class Ev {
  target: El | Txt | null = null;
  currentTarget: El | null = null;
  defaultPrevented = false;
  stopped = false;
  key: string; ctrlKey: boolean; metaKey: boolean;
  deltaY: number; deltaMode: number;             // a wheel's (the text-size step over the body, textSizeControl bindWheel)
  detail: number;                                // a click's count: 0 for the click a key synthesizes on a button, as the browser sets it
  constructor(public type: string, init: { key?: string; ctrlKey?: boolean; metaKey?: boolean; deltaY?: number; deltaMode?: number; detail?: number } = {}) {
    this.key = init.key || ""; this.ctrlKey = !!init.ctrlKey; this.metaKey = !!init.metaKey;
    this.deltaY = init.deltaY || 0; this.deltaMode = init.deltaMode || 0; this.detail = init.detail ?? 0;
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
  // the change painters (Slice 2) split a row's text at a change's edges, as the comment painters do
  splitText(off: number): Txt {
    const tail = new Txt(this.data.slice(off));
    this.data = this.data.slice(0, off);
    const p = this.parentNode;
    if (p) { const i = p.childNodes.indexOf(this); p.childNodes.splice(i + 1, 0, tail); tail.parentNode = p; }
    return tail;
  }
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
  parentNode!: El | null;
  childNodes!: Array<El | Txt>;
  attrs = new Map<string, string>();
  listeners: Reg[] = [];
  hidden = false; disabled = false; title = ""; type = ""; value = ""; placeholder = ""; spellcheck = true; wrap = "";
  src = ""; alt = ""; href = ""; download = ""; target = ""; rel = "";
  innerHTML = "";
  style: Record<string, string> = {};
  onclick: ((ev: Ev) => void) | null = null;
  scrolled = 0;                                  // scrollIntoView calls (scrollToOffset's visible effect)
  scrolledWith: unknown = null;                  // the last scrollIntoView argument ({ block: "center" } for a row or an offset's block, "start" for a heading)
  focused = 0;                                   // focus() calls (takeKeyboard's visible effect; Slice 6 of plans/markdown-viewer.md, item 1)
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
  get children(): El[] { return this.childNodes.filter((c): c is El => c instanceof El); }   // the element children (file-view.ts watchBodyWidth stamps md.children)
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
  set textContent(v: string) { for (const c of this.childNodes) { this.dropFocusIn(c); c.parentNode = null; } this.childNodes.length = 0; if (v !== "") this.appendChild(new Txt(v)); }
  /** The browser's focus fixup: a removed subtree that held the active element leaves the keyboard on the document's body
   *  (so a paint that rebuilds a focused mark reads here as it does in Chromium; the keyboard cases below). */
  private dropFocusIn(n: El | Txt): void { if (n instanceof El && doc.activeElement && n.contains(doc.activeElement)) doc.activeElement = doc.body; }
  private detach(n: El | Txt): void { const p = n.parentNode; if (p) { const i = p.childNodes.indexOf(n); if (i >= 0) p.childNodes.splice(i, 1); n.parentNode = null; } }
  appendChild<T extends El | Txt>(n: T): T { this.detach(n); this.childNodes.push(n); n.parentNode = this; return n; }
  prepend(...ns: Array<El | Txt>): void { for (const n of ns.slice().reverse()) { this.detach(n); this.childNodes.unshift(n); n.parentNode = this; } }
  insertBefore<T extends El | Txt>(n: T, ref: El | Txt | null): T {
    if (!ref) return this.appendChild(n);
    this.detach(n);
    const i = this.childNodes.indexOf(ref);
    this.childNodes.splice(i < 0 ? this.childNodes.length : i, 0, n); n.parentNode = this; return n;
  }
  removeChild<T extends El | Txt>(n: T): T { this.dropFocusIn(n); this.detach(n); return n; }
  replaceChildren(...c: Array<El | Txt>): void { for (const x of this.childNodes) { this.dropFocusIn(x); x.parentNode = null; } this.childNodes.length = 0; for (const x of c) this.appendChild(x); }
  remove(): void { this.dropFocusIn(this); this.detach(this); }
  normalize(): void {   // unpainting a mark leaves adjacent text nodes; join them, as the browser does
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
  focus(): void { this.focused++; doc.activeElement = this; }
  get tabIndex(): number { const v = this.attrs.get("tabindex"); return v === undefined ? -1 : Number(v); }   // reflects the attribute, as the browser's does
  set tabIndex(v: number) { this.attrs.set("tabindex", String(v)); }
  blur(): void { if (doc.activeElement === this) doc.activeElement = null; }
  scrollIntoView(arg?: unknown): void { this.scrolled++; this.scrolledWith = arg ?? null; }
  getBoundingClientRect(): { left: number; top: number; right: number; bottom: number; width: number; height: number } { return { left: 0, top: 0, right: 0, bottom: 0, width: 0, height: 0 }; }
  get offsetWidth(): number { return 0; }
}
// ── the sanitizer's stand-in (md-sanitize.ts setMdSanitizer; Slice 7 of plans/markdown-viewer.md, item 1's first step) ──
// DOMPurify has no document under node, so before the seam every Rendered paint here went through mdBlock's catch, which
// wrote the note's text into the box (the record pin at the end of this file states the constraint). The stand-in hands
// mdBlock an empty body and the cases lay the blocks marked would paint by hand (layRendered), as they always did; the real
// mintHeadingIds and the registered passes run over the empty body and find nothing.
/** Every dirty string the stand-in was handed: one per Rendered paint (the record pin counts them). */
const sanitized: string[] = [];
/** Set for a case: the stand-in's sanitize throws this message instead of answering (item 1 of Slice 7: the render catch). */
let sanitizeFails: string | null = null;
/** Set for a case: what the stand-in's sanitize answers instead of an empty body (a throw from the adoption that follows it). */
let sanitizeAnswers: (() => El) | null = null;
const fakeSanitizer = { addHook: () => { /* the hooks are DOMPurify's; the stand-in has none */ }, sanitize: (dirty: string) => {
  if (sanitizeFails !== null) throw new Error(sanitizeFails);
  sanitized.push(dirty);
  return sanitizeAnswers ? sanitizeAnswers() : new El("body");
} };
setMdSanitizer(fakeSanitizer as unknown as Parameters<typeof setMdSanitizer>[0]);

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
// the page's address: the web dashboard by default (canPreview() reads the protocol; the viewer's discard ask is a
// confirm there and the notice bar in the VS Code webview, whose protocol a test sets for the length of a case)
(globalThis as any).location = { protocol: "http:" };
const store = new Map<string, string>();
(globalThis as any).localStorage = {
  getItem: (k: string) => (store.has(k) ? store.get(k)! : null),
  setItem: (k: string, v: string) => { store.set(k, String(v)); },
  removeItem: (k: string) => { store.delete(k); },
};
// The editing substrate: the lazily-loaded CodeMirror chunk registers a window global the viewer's
// editorChunk() resolves from; this one is a buffer with the two callbacks the viewer wires.
// Slice 5: the stub carries the mount's `track` option the way the real chunk does — the handle grows `track` with the
// records (as seeded; a test may remap them) and the decisions, and `onDecisions` is the callback the viewer wired.
// `tracks: false` plays an older bundle that ignores the option (no `track` on the handle).
type TrackStub = { suggestions: unknown[]; authorColor: (a: string) => string | null; onDecisions: (l: { accepted: unknown[]; rejected: unknown[] }) => void };
type Decided = { accepted: Array<{ id: string; oldText: string; newText: string }>; rejected: Array<{ id: string; oldText: string; newText: string }> };
const ed = {
  buf: "", onChange: null as (() => void) | null, mounted: 0, destroyed: 0,
  tracks: true, trackOpts: null as TrackStub | null, records: [] as unknown[], decisions: { accepted: [], rejected: [] } as Decided,
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
/** An in-editor decision: the chunk drops the record from its field and reports the decisions (no text changes on an accept). */
const decideInEditor = (side: "accepted" | "rejected", id: string, oldText: string, newText: string) => {
  ed.records = ed.records.filter((r) => (r as { id: string }).id !== id);
  ed.decisions = { ...ed.decisions, [side]: [...ed.decisions[side], { id, oldText, newText }] };
  ed.trackOpts!.onDecisions(ed.decisions);
};
// The PDF renderer chunk (Slice 4) the viewer's pdfChunkLoad resolves from: two page shells in the chunk's own DOM
// shape (div.fileview-pdf > div.fileview-pdf-page[data-page] > canvas.fileview-pdf-canvas), page 1 "drawn" before the
// promise resolves as the real chunk does, later pages drawn when a test calls onPage; a test may make it refuse.
const pdf = { renders: 0, disposed: 0, bytes: 0, opts: null as null | { maxBytes?: number; onPage?: (p: unknown) => void }, refuse: null as string | null, roots: [] as El[] };
win.__rompPdf = {
  DEFAULT_MAX_BYTES: 25 * 1024 * 1024,
  render(bytes: ArrayBuffer, container: El, opts: { maxBytes?: number; onPage?: (p: unknown) => void } = {}) {
    pdf.renders++; pdf.bytes = bytes.byteLength; pdf.opts = opts;
    if (pdf.refuse) return Promise.reject(new Error(pdf.refuse));
    const root = doc.createElement("div"); root.className = "fileview-pdf";
    for (let i = 1; i <= 2; i++) {
      const w = doc.createElement("div"); w.className = "fileview-pdf-page"; w.dataset.page = String(i); w.style.position = "relative";
      const c = doc.createElement("canvas"); c.className = "fileview-pdf-canvas"; c.dataset.page = String(i);
      w.appendChild(c); root.appendChild(w);
    }
    container.appendChild(root); pdf.roots.push(root);
    opts.onPage?.({ index: 1, canvas: root.childNodes[0], width: 800, height: 1035 });
    return Promise.resolve({ pages: 2, dispose() { pdf.disposed++; root.remove(); } });
  },
};

// ── the kernel's /file, /version and /sessions, as the viewer fetches them ──────────────────────────
type Served = { bytes: string | Uint8Array; type: string; mtimeNs: string; utf8?: "0" | "1" };   // utf8: the kernel's X-Romp-Text-Utf8 on a text answer ("1" unless a case says "0", the Latin-1 fallback; plans/markdown-viewer.md Slice 7, item 5)
const disk: Record<string, Served> = {};
const fetches: string[] = [];
(globalThis as any).fetch = async (url: string, init?: { method?: string }) => {
  fetches.push((init && init.method || "GET") + " " + url.replace(/[?&]token=[^&]*/, ""));
  if (url.startsWith("/version")) return { json: async () => ({ fileEditing: true }) };   // consent already given
  if (url.startsWith("/sessions")) return { json: async () => [{ id: SID, name: "api", bg: "#123456", fg: "#ffffff" }] };
  const p = decodeURIComponent((/[?&]path=([^&]*)/.exec(url) || [])[1] || "");
  const f = disk[p];
  // Content-Length: the body's byte count, as the kernel's _send writes it (tests/test_kernel_preview.py pins 0 for an empty file);
  // the viewer reads it for a file whose only bytes are a BOM (Slice 7, item 6: "" from more than zero bytes)
  const byteLength = (b: string | Uint8Array): number => (typeof b === "string" ? new TextEncoder().encode(b).length : b.length);
  const headers = { get: (h: string) => (f ? (h === "Content-Type" ? f.type : h === "X-Romp-Mtime-Ns" ? f.mtimeNs : h === "X-Romp-Text-Utf8" ? (f.utf8 ?? "1") : h === "Content-Length" ? String(byteLength(f.bytes)) : null) : null) };
  if (!f) return { ok: false, status: 404, headers, text: async () => "no such file: " + p };
  return {
    ok: true, status: 200, headers,
    text: async () => String(f.bytes).replace(/^\uFEFF/, ""),   // the browser's UTF-8 decode strips exactly one leading U+FEFF (Chromium 151, the Slice 7 review's round 4 record), so the stub does too
    blob: async () => new Blob([f.bytes as unknown as BlobPart], { type: f.type }),
  };
};

// ── fixtures: the notes-api world ──────────────────────────────────────────────────────────────────
const SID = "11111111-2222-3333-4444-555555555555";
const ROOT = "/repo/notes-api";
const REPORT = ROOT + "/docs/report.md";
const APP = ROOT + "/src/app.py";
const PLOT = ROOT + "/docs/plot.png";
const FIG = ROOT + "/docs/figure.svg";
const DECK = ROOT + "/docs/deck.pdf";
const SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><text x="1" y="8">p95</text></svg>\n';
const DOC = "# Report\n\n## Findings\nThe api session cut p95 latency by 40%.\n\nWe recommend shipping the cache in v1.2.\n";
const PY = "def main():\n    return 0\n";
const MT = "1757145600000000001";
const T0 = 1757145600000;
const hunk = (id: string): Hunk => ({ id, author: "api", ts: T0, kind: "sub", curFrom: 28, curTo: 31, baseFrom: 28, baseTo: 31, oldText: "p95", newText: "p99", anchor: null });
/** The sidecar's record behind a hunk (the storage format's shape), as `status` carries it in `store` (Slice 5). */
const record = (id: string) => ({ id, author: "api", authorId: SID, ts: T0, kind: "sub", from: DOC.indexOf("p95"), newText: "p99", oldText: "p95" });
function status(hunks: Hunk[], over: Partial<Status> = {}): Status {
  return {
    verb: "status", root: ROOT, storePath: ROOT + "/.trackchanges/docs%2Freport.md.json", trackedBy: { kind: "file", entry: "docs/report.md" },
    agentTooling: "present", fileMtimeNs: MT, storeMtimeNs: "1757145600000000002", configMtimeNs: "1757145600000000003",
    store: { v: 3, path: "docs/report.md", suggestions: hunks.map((h) => record(h.id)), comments: [] }, hunks,
    unsent: { comments: [], replies: [], accepted: 0, rejected: 0, watermark: null }, log: [],
    ...over,
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
/** `opts`: openFileView's third argument (`at`: where the open lands; Slice 6 of plans/markdown-viewer.md, item 4); `raw`: the
 *  stored preference says Raw for a markdown file (the default every open otherwise starts from is Rendered). */
async function open(p: string, t: TestContext, sid: string | null = SID, opts?: { todoId?: string | null; at?: At | null }, raw = false): Promise<Open> {
  const fv = await mod();
  disk[REPORT] = { bytes: DOC, type: "text/plain; charset=utf-8", mtimeNs: MT };
  disk[APP] = { bytes: PY, type: "text/plain; charset=utf-8", mtimeNs: MT };
  disk[PLOT] = { bytes: new Uint8Array([0x89, 0x50, 0x4e, 0x47]), type: "image/png", mtimeNs: MT };
  disk[FIG] = { bytes: SVG, type: "image/svg+xml", mtimeNs: MT };
  disk[DECK] = { bytes: "%PDF-1.4\n", type: "application/pdf", mtimeNs: MT };
  posted.length = 0; fetches.length = 0; savedInfos.length = 0; paints = 0; seam = null;
  store.delete("romp:fileviewFmt");                     // every open starts from the default: markdown Rendered
  if (raw) store.set("romp:fileviewFmt", JSON.stringify({ md: "raw" }));   // …unless the case wants the Raw preference
  ed.mounted = 0; ed.destroyed = 0; ed.tracks = true; ed.trackOpts = null; ed.records = []; ed.decisions = { accepted: [], rejected: [] };
  pdf.renders = 0; pdf.disposed = 0; pdf.bytes = 0; pdf.opts = null; pdf.refuse = null; pdf.roots.length = 0;
  assert.equal(fv.openFileView(p, sid, opts), true, "the open happened");
  t.after(() => { fv.closeFileView(); });
  await settle();
  const wrap = doc.getElementById("romp-fileview")!;
  assert.ok(wrap, "the viewer is up");
  const body = wrap.querySelector(".fileview-body")!;
  const acts = wrap.querySelector(".fileview-acts")!;
  // captured once, by the word they wear at open: a word button's text, a glyph's aria-label (T367 made Edit a glyph with its
  // word in the title and aria-label; Rendered, Raw, Save and Cancel keep their words); a click relabels Save to "Saving…" (the acknowledgement)
  const btn = (label: string) => { const b = acts.querySelectorAll("button").find((x) => x.textContent === label || x.getAttribute("aria-label") === label); assert.ok(b, "the " + label + " button"); return b!; };
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
/** Save through the PANEL (Slice 5: a tracked file, or one with a sidecar): the `save` verb goes out instead of saveFile. */
function saveTracked(o: Open, content: string): any {
  typeInto(content);
  const saves = posted.filter((m) => m.type === "saveFile").length;
  o.b.save.click();
  const m = lastOf("fileComments", "save");
  assert.ok(m, "the save went through the panel");
  assert.equal(posted.filter((x) => x.type === "saveFile").length, saves, "…and not through saveFile");
  assert.equal(o.b.save.disabled, true); assert.equal(o.b.save.textContent, "Saving…", "acknowledged before the round-trip");
  return m;
}
const saveReply = async (reqId: number, s: Status, extra: Record<string, unknown> = {}) => {
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId, ...s, verb: "save", logged: true, ...extra } }));
  await settle();
};
const saveRefused = async (reqId: number, code: string, error: string) => {
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsFailed", reqId, verb: "save", code, error } }));
  await settle();
};
const fileSaved = (reqId: number, extra: Record<string, unknown>) =>
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileSaved", reqId, path: REPORT, mtimeNs: "1757145600000000009", ...extra } }));
// the viewer's notice bar (file-view.ts noteBar, #fileview-save-err) is a child of the card before .fileview-main since
// Slice 2 of plans/markdown-viewer.md, so it is read from the card: the card's first .fileview-err is the bar when one is
// up, else a pane inside the body (a fetch failure's), the set the body-scoped read used to answer
const cardOf = (body: El) => body.parentNode!.parentNode as El;
const errBar = (body: El) => cardOf(body).querySelector(".fileview-err");
/** The bar stands right above the body row (the read view, or the editor, stands untouched under it). */
const aboveRow = (body: El) => { const main = body.parentNode!, box = cardOf(body), bar = errBar(body); return !!bar && box.childNodes.indexOf(bar) === box.childNodes.indexOf(main) - 1; };

test("the discard ask on both hosts: on the web a confirm asks about the editor's buffer, then about an action's draft registered through guardClose, and a no keeps everything; in the VS Code webview, where confirm shows nothing, nothing is asked, the thing is kept, the notice bar says so and what clears it, and every exit (Cancel, close, a replace-open) is vetoed the same way", async (t) => {
  const o = await open(REPORT, t);
  const { ctx, body, b } = o;
  // an action's draft ask, as the comments panel registers one: the question and the kept notice, named by the action
  let draft: { question: string; kept: string } | null = null;
  ctx.guardClose(() => draft);
  const confirms: string[] = [];
  const loc = (globalThis as any).location as { protocol: string };
  try {
    // the web: the editor's buffer is dirty; Cancel asks in the editor's words, and a no keeps the editor
    await enterEdit(o);
    typeInto(DOC + "x");
    win.confirm = (q: string) => { confirms.push(q); return false; };
    b.cancel.click(); await settle();
    assert.deepEqual(confirms, ["Discard unsaved changes to report.md?"]);
    assert.ok(body.querySelector(".fileview-cm"), "declined: the editor stays");
    assert.equal(errBar(body), null, "a dialog asked; no notice");
    // the web: a close meets the editor's ask and then the action's, through one guard; a no to the second vetoes the close
    draft = { question: "Discard the unsaved comment on report.md?", kept: "This file stays open: the comment typed on report.md is not saved. Save it, or clear the box, then try again." };
    win.confirm = (q: string) => { confirms.push(q); return q.startsWith("Discard unsaved changes"); };   // yes to the editor, no to the draft
    o.fv.closeFileView(); await settle();
    assert.deepEqual(confirms.slice(1), ["Discard unsaved changes to report.md?", "Discard the unsaved comment on report.md?"], "the editor's ask, then the action's");
    assert.ok(doc.getElementById("romp-fileview") === o.wrap, "the draft's no vetoed the close");
    assert.ok(body.querySelector(".fileview-cm"), "and the editor is still up (its yes discarded nothing on its own)");
    assert.equal(errBar(body), null);
    // the VS Code webview: no dialog. Cancel with a dirty buffer keeps the editor and says so in the notice bar
    loc.protocol = "vscode-webview:";
    const asked = confirms.length;
    b.cancel.click(); await settle();
    assert.equal(confirms.length, asked, "no confirm: it would show nothing there");
    assert.ok(body.querySelector(".fileview-cm"), "the editor stays");
    assert.equal(errBar(body)!.textContent, "The editor stays open: report.md has unsaved changes. Save or undo them, then try again.");
    // the buffer undone: the editor's ask has nothing to ask, and a close meets the action's draft the same way
    typeInto(DOC);
    o.fv.closeFileView(); await settle();
    assert.equal(confirms.length, asked);
    assert.ok(doc.getElementById("romp-fileview") === o.wrap, "kept: the viewer stays");
    assert.equal(errBar(body)!.textContent, draft.kept, "the action's notice replaced the editor's");
    // a replace-open (a link followed inside the file, a Files-pane row) meets the same wall
    assert.equal(o.fv.openFileView(APP, SID), false, "the replace-open is vetoed");
    assert.ok(doc.getElementById("romp-fileview") === o.wrap);
    assert.equal(errBar(body)!.textContent, draft.kept);
    assert.equal(confirms.length, asked);
    // with nothing at stake the close goes through, on either host
    draft = null;
    o.fv.closeFileView(); await settle();
    assert.equal(doc.getElementById("romp-fileview"), null, "closed");
  } finally {
    loc.protocol = "http:"; win.confirm = () => true; draft = null;   // the after-hook's close then meets a yes
  }
});

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
  assert.equal(paints, 0, "the picture has not loaded: onRendered waits for it (the media-paint test below)");
  fv.closeFileView();
  assert.equal(revoked, 1, "the bytes leave with the viewer");
});

// ── Slice 3: the media paint, the media element, the rendered figures (plans/file-review.md, Images and PDFs) ──

test("onRendered for an image fires on the img's load, once; mediaElement() is that img until the decode-failure pane replaces it, which is a paint of its own; a load on the replaced img fires nothing", async (t) => {
  const { ctx, body } = await open(PLOT, t);
  const img = body.querySelector("img.fileview-img")!;
  assert.equal(ctx.mediaElement(), img as unknown as HTMLElement, "the picture in the body");
  assert.deepEqual(ctx.renderedImages(), [], "a media body has no rendered figures");
  assert.equal(paints, 0, "no paint before the picture shows");
  img.dispatchEvent(new Ev("load"));
  assert.equal(paints, 1, "the load event is the media paint");
  img.dispatchEvent(new Ev("load"));
  assert.equal(paints, 1, "once: a second load (a browser re-decode) does not repaint");
  assert.equal(ctx.error(), null, "a media view shows: no pane (Slice 7 of plans/markdown-viewer.md, item 3)");
  // the bytes would not decode: imgFailed's pane takes the body, and the seam stops naming the picture
  img.dispatchEvent(new Ev("error"));
  assert.equal(img.isConnected, false, "the picture left with the pane swap");
  const pane = body.querySelector(".fileview-err")!;
  assert.ok(pane, "the failure pane is up");
  assert.equal(ctx.error(), pane.childNodes[0].textContent, "error() is the pane's own sentence, set before the hooks fire (Slice 7, item 3)");
  assert.ok(ctx.error()!.startsWith("this image failed to decode") && !ctx.error()!.includes(PLOT) && !ctx.error()!.includes("Download"),
    "the sentence alone: not the hint naming the path, not the button's label, which the pane's textContent carries: " + ctx.error());
  assert.equal(ctx.mode(), "media", "still a media body to the seam…");
  assert.equal(ctx.mediaElement(), null, "…but no media element: nothing to overlay");
  assert.equal(paints, 2, "the pane swap is a paint: the panel hears the picture is gone and takes its layer down (a reload whose bytes would not decode left the old picture's overlay standing before)");
  img.dispatchEvent(new Ev("load"));
  assert.equal(paints, 2, "a load on the replaced picture still fires nothing");
});

test("a load that lands after the viewer moved on fires nothing: the decode failed first, or a reload replaced the picture", async (t) => {
  const { ctx, body } = await open(PLOT, t);
  const img = body.querySelector("img.fileview-img")!;
  img.dispatchEvent(new Ev("error"));                      // the pane took the body before the picture ever showed
  assert.equal(paints, 1, "the failure pane is the paint (imgFailed fires the hooks itself)");
  assert.equal(ctx.error(), (await mod()).DECODE_FAILED, "error() names the pane with the exported sentence (Slice 7 of plans/markdown-viewer.md, item 3; DECODE_FAILED since the review's round 1)");
  img.dispatchEvent(new Ev("load"));
  assert.equal(paints, 1, "a load on the replaced picture is not a paint");
  disk[PLOT] = { bytes: new Uint8Array([0x89, 0x50, 0x4e, 0x47, 0x02]), type: "image/png", mtimeNs: "1757145600000000007" };
  ctx.reload();
  await settle();
  const img2 = body.querySelector("img.fileview-img")!;
  assert.notEqual(img2, img, "the reload built a new picture");
  assert.equal(ctx.error(), null, "a reload that decodes clears error() at the media arm's paint, before the picture's load: a media view is up, no pane");
  assert.equal(ctx.mediaElement(), img2 as unknown as HTMLElement);
  img.dispatchEvent(new Ev("load"));
  assert.equal(paints, 1, "the old picture's late load: nothing");
  img2.dispatchEvent(new Ev("load"));
  assert.equal(paints, 2, "the showing picture's load: the paint");
});

test("an img the browser already holds (complete) paints at once, without waiting for a load event", async (t) => {
  const realCreate = doc.createElement;
  doc.createElement = (tag: string) => { const e = realCreate(tag); if (tag === "img") (e as unknown as { complete: boolean }).complete = true; return e; };
  t.after(() => { doc.createElement = realCreate; });
  const { ctx, body } = await open(PLOT, t);
  assert.equal(paints, 1, "complete at paint time: onRendered ran with the replaceChildren");
  assert.equal(ctx.mediaElement(), body.querySelector("img.fileview-img") as unknown as HTMLElement);
  body.querySelector("img.fileview-img")!.dispatchEvent(new Ev("load"));
  assert.equal(paints, 1, "no listener was armed for a picture that had already loaded");
});

test("a PDF body: mediaElement() is the frame, onRendered fires at once (the frame gives no signal to wait for), text() null", async (t) => {
  const { ctx, body, b } = await open(DECK, t);
  assert.equal(ctx.mode(), "media"); assert.equal(ctx.media(), "pdf"); assert.equal(ctx.text(), null);
  const frame = body.querySelector("iframe.fileview-frame")!;
  assert.ok(frame && frame.src.startsWith("blob:"), "the browser's viewer at the object URL");
  assert.equal(ctx.mediaElement(), frame as unknown as HTMLElement);
  assert.equal(paints, 1, "shown the moment it is in the body");
  assert.deepEqual(ctx.renderedImages(), []);
  assert.equal(b.edit.hidden, true);
});

// ── Slice 4: the PDF's pages while the Comments panel is open (plans/file-review.md Slice 4; contract F3) ──

test("a PDF with the panel open: the loader over the kept frame, then the chunk's pages in its place — mediaElement() the pages root, pdfPages() the shells, onRendered after page 1 and per page; the panel closing brings the frame back and disposes", async (t) => {
  const { ctx, body } = await open(DECK, t);
  assert.equal(paints, 1, "the frame showed first: the panel is closed at open");
  assert.equal(pdf.renders, 0, "the chunk is not asked for a PDF nobody is commenting on");
  const shown = body.querySelector("iframe.fileview-frame")!;
  const aside = new El("div");
  ctx.aside(aside as unknown as HTMLElement);                                      // the panel opens: the seam's aside() IS the event
  assert.ok(body.querySelector(".fileview-load"), "the romp loader first (the loading-state rule)");
  const host = body.querySelector(".fileview-pdfhost")!;
  assert.ok(host && host.isConnected, "the chunk's host is in the body before render(): the pages fit its width");
  // The frame is NOT dropped for the loader: it stays through the attempt, in place, so the document is not
  // reloaded under the reader (a rebuilt or moved iframe reloads at page 1 — the review, 2026-09-06). The loader
  // heads the frame's own column, the host follows the column in the body, and nothing repaints for it.
  assert.equal(body.querySelector("iframe.fileview-frame"), shown, "the frame the open painted is still the frame, under the loader");
  const col = shown.parentElement!;
  assert.ok(col.classList.contains("fileview-pdffall") && col.parentNode === body, "…in its column, still the body's first child");
  assert.equal(col.childNodes[0], body.querySelector(".fileview-load"), "…the loader at the head of that column");
  assert.ok(host.parentNode === body && body.childNodes[0] === col && body.childNodes[1] === host, "…and the host after the column, never inside it: the frame does not move");
  assert.equal(paints, 1, "no paint for the loader: what shows is the frame that already painted");
  await settle();
  assert.equal(pdf.renders, 1);
  assert.equal(pdf.bytes, "%PDF-1.4\n".length, "the bytes the viewer already fetched — no second request");
  assert.equal(pdf.opts!.maxBytes, 25 * 1024 * 1024, "the cap rides into render() too, so the two cannot disagree");
  assert.equal(body.querySelector(".fileview-load"), null, "page 1 drawn: the loader gives way");
  assert.equal(body.querySelector("iframe.fileview-frame"), null, "…and only now is the frame gone: the pages are the body");
  assert.equal(body.querySelector(".fileview-pdffall"), null, "…its column with it");
  const root = body.querySelector(".fileview-pdf")!;
  assert.ok(root, "the chunk's root in the host");
  assert.equal(ctx.mediaElement(), root as unknown as HTMLElement, "the pages root is the media element while rendered");
  assert.equal(ctx.mode(), "media"); assert.equal(ctx.media(), "pdf");
  const pages = ctx.pdfPages();
  assert.equal(pages.length, 2, "one shell per page");
  assert.deepEqual(pages.map((pg) => (pg as unknown as El).dataset.page), ["1", "2"], "in page order, data-page 1-based");
  assert.equal(paints, 2, "onRendered once page 1 is drawn (the first onPage fired before the resolve, and counted nothing)");
  pdf.opts!.onPage!({ index: 2, canvas: pages[1], width: 800, height: 1035 });
  assert.equal(paints, 3, "…and again for every page the chunk draws after that");
  assert.equal(fetches.filter((f) => f.includes("deck.pdf")).length, 1, "one fetch of the file, ever");
  // the panel closes: the frame again, the pages released, and a late onPage from the old render is nothing
  ctx.aside(null);
  assert.equal(pdf.disposed, 1, "dispose(): the draws cancelled, the worker released, the root removed");
  const frame = body.querySelector("iframe.fileview-frame")!;
  assert.ok(frame && frame.src.startsWith("blob:"), "the browser's viewer at the object URL, as with the panel closed");
  assert.equal(ctx.mediaElement(), frame as unknown as HTMLElement);
  assert.deepEqual(ctx.pdfPages(), [], "no shells under the frame");
  assert.equal(paints, 4, "the frame's own paint");
  pdf.opts!.onPage!({ index: 2, canvas: pages[1], width: 800, height: 1035 });
  assert.equal(paints, 4, "a draw finishing after the pages left fires nothing");
  // open again: a fresh render from the same bytes
  ctx.aside(aside as unknown as HTMLElement); await settle();
  assert.equal(pdf.renders, 2);
  assert.equal(ctx.pdfPages().length, 2);
  assert.equal(body.querySelector("iframe.fileview-frame"), null);
});

test("a PDF over the cap with the panel open: the frame stays, with the notice naming the size and the cap above it; the chunk is never asked", async (t) => {
  const BIG = ROOT + "/docs/atlas.pdf";
  disk[BIG] = { bytes: new Uint8Array(26 * 1024 * 1024), type: "application/pdf", mtimeNs: MT };
  t.after(() => { delete disk[BIG]; });
  const { ctx, body } = await open(BIG, t);
  ctx.aside(new El("div") as unknown as HTMLElement); await settle();
  assert.equal(pdf.renders, 0, "refused before a megabyte of renderer is fetched for nothing");
  const fall = body.querySelector(".fileview-pdffall")!;
  assert.ok(fall, "the fallback column: the notice over the frame");
  const note = fall.querySelector(".fileview-err")!;
  assert.equal(note.textContent, "this PDF is 26.0 MB, over the 25.0 MB cap for rendering pages in the viewer — showing the browser's PDF viewer instead; comments on the whole file still work.");
  const frame = fall.querySelector("iframe.fileview-frame")!;
  assert.ok(frame && frame.src.startsWith("blob:"), "the browser's viewer under the notice, at the same object URL");
  assert.equal(ctx.mediaElement(), frame as unknown as HTMLElement, "the frame is the media element: whole-file comments work as before");
  assert.deepEqual(ctx.pdfPages(), []);
  assert.equal(paints, 2, "the fallback frame counts as shown, so the panel paints its whole-file cards");
  assert.equal(body.querySelector(".fileview-load"), null, "no loader left behind");
});

test("the chunk refusing the document, or failing to load at all, falls back the same way — the frame under the reason, never a blank pane", async (t) => {
  const { ctx, body } = await open(DECK, t);
  pdf.refuse = "Invalid PDF structure.";                 // pdf.js's own words for a file it will not open
  ctx.aside(new El("div") as unknown as HTMLElement); await settle();
  assert.equal(pdf.renders, 1, "the chunk was asked");
  let note = body.querySelector(".fileview-pdffall .fileview-err")!;
  assert.equal(note.textContent, "Invalid PDF structure. — showing the browser's PDF viewer instead; comments on the whole file still work.");
  assert.ok(body.querySelector(".fileview-pdffall iframe.fileview-frame"), "the frame");
  assert.equal(body.querySelector(".fileview-load"), null);
  assert.equal(body.querySelector(".fileview-pdfhost"), null, "the chunk's host went with the loader");
  // no chunk registered and no bundle script tag to derive it from (this stand-in has none): the loader's own refusal.
  // The chunk latch is per OPEN — a chunk that loaded once stays loaded for that viewer — so this is a fresh open.
  pdf.refuse = null;
  const saved = win.__rompPdf; win.__rompPdf = undefined;
  t.after(() => { win.__rompPdf = saved; });
  const again = await open(DECK, t);
  again.ctx.aside(new El("div") as unknown as HTMLElement); await settle();
  assert.equal(pdf.renders, 0, "the loader refused before any renderer was reached");
  note = again.body.querySelector(".fileview-pdffall .fileview-err")!;
  assert.ok(note, "the frame with a notice, again");
  assert.equal(note.textContent, "no bundle script tag to derive the PDF chunk URL from — showing the browser's PDF viewer instead; comments on the whole file still work.");
  assert.equal(again.ctx.mediaElement(), again.body.querySelector("iframe.fileview-frame") as unknown as HTMLElement);
});

test("an SVG: mediaElement() is the img while it shows as a picture, null under the Source view (a text view), the img again when toggled back", async (t) => {
  const { ctx, body, wrap } = await open(FIG, t);
  assert.equal(ctx.media(), "svg"); assert.equal(ctx.mode(), "media");
  const img = body.querySelector("img.fileview-img")!;
  assert.equal(ctx.mediaElement(), img as unknown as HTMLElement, "an SVG shown as an image is the media element");
  img.dispatchEvent(new Ev("load"));
  assert.equal(paints, 1);
  const srcBtn = wrap.querySelector(".fileview-acts")!.querySelectorAll("button").find((x) => x.textContent === "Source")!;
  srcBtn.click();
  await settle();
  assert.equal(ctx.mode(), "raw", "the Source view is a text view");
  assert.equal(ctx.mediaElement(), null, "…so it has no media element, whatever the kernel's media() verdict");
  assert.equal(ctx.media(), "svg", "the kernel's verdict is unchanged");
  assert.equal(paints, 2, "the Source paint is a text paint");
  srcBtn.click();
  assert.equal(ctx.mode(), "media");
  const again = body.querySelector("img.fileview-img")!;
  assert.equal(ctx.mediaElement(), again as unknown as HTMLElement, "back to the picture: a fresh img, read from the body");
});

test("mediaElement() is null for a text body even when the rendered markdown carries an <img class=\"fileview-img\">; renderedImages() lists the Rendered body's figures in document order and nothing in Raw", async (t) => {
  const o = await open(REPORT, t);
  const { ctx, body } = o;
  assert.equal(ctx.mediaElement(), null, "a text file has no media element");
  const md = body.querySelector(".fileview-md")!;
  assert.deepEqual(ctx.renderedImages(), [], "the stand-in parses no innerHTML: no figures yet");
  // the figures a README renders: one in a paragraph, one bare, one nested deeper — plus a README's own
  // <img class="fileview-img"> that the sanitizer would let through
  const p1 = new El("p"); const f1 = new El("img"); f1.setAttribute("src", "/file?path=%2Frepo%2Fnotes-api%2Fdocs%2Fplot.png"); p1.appendChild(f1);
  const f2 = new El("img"); f2.setAttribute("src", "https://example.test/x.png");
  const p3 = new El("p"); const span = new El("span"); const f3 = new El("img"); f3.className = "fileview-img"; f3.setAttribute("src", "data:image/png;base64,iVBORw0KGgo="); span.appendChild(f3); p3.appendChild(span);
  md.appendChild(p1); md.appendChild(f2); md.appendChild(p3);
  sameNodes(ctx.renderedImages(), [f1, f2, f3], "every figure, document order, whatever its src or class");   // by identity (ui/test-dom-shim.ts sameNodes)
  assert.equal(ctx.mediaElement(), null, "a rendered body's own <img class=fileview-img> never answers as the media element (the mode gate)");
  o.b.raw.click();
  assert.equal(ctx.mode(), "raw");
  assert.deepEqual(ctx.renderedImages(), [], "Raw shows no figures");
  ctx.setMode("rendered");
  assert.deepEqual(ctx.renderedImages(), [], "a repaint rebuilt the body: the hand-laid figures went with the old one, and innerHTML parses nothing here");
});

test("rewriteFigureSrcs, executed over a sanitized DOM stand-in: relative srcs go to the kernel's /file for <dir>/<src> and absolute paths to /file for themselves, the authored value kept in data-fv-src; protocol-relative, http(s), data:, blob: and empty srcs stay; a remote sid relays", async () => {
  const fv = await mod();
  const DIR = ROOT + "/docs/";
  const q = (p: string) => "/file?path=" + encodeURIComponent(p) + "&sid=" + SID;
  const mk = (src: string | null, extra: Record<string, string> = {}) => {
    const img = new El("img");
    if (src !== null) img.setAttribute("src", src);
    for (const k of Object.keys(extra)) img.setAttribute(k, extra[k]);
    return img;
  };
  const root = new El("div"); root.className = "fileview-md";
  const cases: Array<[El, string | null, string | null]> = [          // [img, expected src, expected data-fv-src]
    [mk("plot.png"), q(DIR + "plot.png"), "plot.png"],
    [mk("figs/plot.png"), q(DIR + "figs/plot.png"), "figs/plot.png"],
    [mk("../assets/logo.png"), q(DIR + "../assets/logo.png"), "../assets/logo.png"],    // dotdot as written: the kernel resolves and gates
    [mk("./plot.png"), q(DIR + "./plot.png"), "./plot.png"],
    [mk("six%20seven.png"), q(DIR + "six seven.png"), "six%20seven.png"],              // marked's percent-encoding decoded back to the path
    [mk("bad%E0%A4%A.png"), q(DIR + "bad%E0%A4%A.png"), "bad%E0%A4%A.png"],            // a malformed escape: taken as written
    [mk(ROOT + "/docs/plot.png"), q(ROOT + "/docs/plot.png"), ROOT + "/docs/plot.png"],  // absolute path: /file for the path itself, as the poll and the host read it (file-view-figures-absolute.test.ts)
    [mk("//cdn.example.test/x.png"), "//cdn.example.test/x.png", null],                 // protocol-relative: an absolute URL
    [mk("https://example.test/x.png"), "https://example.test/x.png", null],
    [mk("http://example.test/x.png"), "http://example.test/x.png", null],
    [mk("data:image/png;base64,iVBORw0KGgo="), "data:image/png;base64,iVBORw0KGgo=", null],
    [mk("blob:http://kernel.test/11111111-2222-3333-4444-555555555555"), "blob:http://kernel.test/11111111-2222-3333-4444-555555555555", null],
    [mk(""), "", null],
    [mk("https://example.test/y.png", { "data-fv-src": "authored.png" }), "https://example.test/y.png", null],   // an authored data-fv-src on an untouched figure is dropped
    [mk(null, { alt: "no src at all" }), null, null],
  ];
  const p = new El("p");
  for (const [img] of cases) p.appendChild(img);
  root.appendChild(p);
  fv.rewriteFigureSrcs(root as unknown as ParentNode, DIR, SID);
  for (const [img, src, authored] of cases) {
    assert.equal(img.getAttribute("src"), src, "src of " + JSON.stringify(authored ?? src));
    assert.equal(img.getAttribute("data-fv-src"), authored, "data-fv-src of " + JSON.stringify(authored ?? src));
  }
  // a remote session's figure relays through the owning host, as the file itself did (fileUrl)
  const remote = mk("plot.png"); root.appendChild(remote);
  fv.rewriteFigureSrcs(root as unknown as ParentNode, DIR, "gpu1:" + SID);
  assert.equal(remote.getAttribute("src"), "/remote/gpu1/file?path=" + encodeURIComponent(DIR + "plot.png") + "&sid=" + SID);
  // no sid, and a bare relative open path (dir ""): the src alone, for the kernel to resolve against the cwd it would use for the file
  const bare = mk("plot.png"); const root2 = new El("div"); root2.appendChild(bare);
  fv.rewriteFigureSrcs(root2 as unknown as ParentNode, "", null);
  assert.equal(bare.getAttribute("src"), "/file?path=plot.png");
});

test("setEditBlocked through the seam: Edit refuses in words, in place, and opens no editor; null lifts it (pending changes no longer set it — Slice 5)", async (t) => {
  const o = await open(REPORT, t);
  const { ctx, body, b } = o;
  assert.equal(b.edit.title, "Edit this file in place", "before the kernel has spoken: no reason");
  await answerStatus(status([hunk("h1"), hunk("h2")]));
  assert.equal(b.edit.title, "Edit this file in place", "two pending changes block nothing: they ride into the editor (Slice 5)");
  assert.equal(b.edit.classList.contains("fileview-btn-blocked"), false);
  const reason = "2 changes are pending in this file, so Edit is off here (a caller's own reason)";
  ctx.setEditBlocked(reason);
  assert.equal(b.edit.title, reason, "a caller's reason is the button's tooltip");
  assert.equal(b.edit.classList.contains("fileview-btn-blocked"), true);
  assert.equal(b.edit.hidden, false, "a real button, not a hidden or disabled one — the reason must reach touch and keyboard users");
  assert.equal(b.edit.disabled, false);
  const reads = fetches.length;
  b.edit.click();
  await settle();
  const bar = errBar(body);
  assert.ok(bar, "the refusal is the viewer's notice bar");
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
  assert.ok(aboveRow(body), "above the body row, where a save failure would sit");
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
  assert.equal(ctx.text(), v2 + "typed while saving", "text() is the BUFFER while the editor is up (Slice 5), newer keystrokes included");
  assert.equal(ctx.editing(), true);
  assert.equal(body.childNodes.length, 1, "the editor host, nothing else, in the body");
  assert.ok(aboveRow(body), "the note bar above the body row");
  assert.equal(errBar(body)!.textContent, WARN);
  assert.equal((body.childNodes[0] as El).className, "fileview-cm");
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

test("a failed reload is a paint the seam hears (Slice 7 of plans/markdown-viewer.md, item 3): the fetch chain's catch fires the hooks once after the pane's swap, error() answers the pane's words, and text(), mtimeNs() and mode() keep the last landing's; the file back, the next landing paints again and error() is null", async (t) => {
  const { ctx, body } = await open(REPORT, t);
  assert.equal(paints, 1); assert.equal(ctx.error(), null, "a text view: no pane");
  delete disk[REPORT];                                     // a session removed the file; the panel's poll asks a reload
  ctx.reload(); await settle();
  assert.equal(paints, 2, "the pane's paint fired the hooks once (before: no hook fired for a failed reload, and the Comments panel's loader stood until its 15 s deadline)");
  const words = "no such file: " + REPORT;                 // the stub's 404 body, as the kernel's names the resolved path
  assert.equal(ctx.error(), words, "error() is the pane's words");
  const pane = errBar(body)!;
  assert.ok(pane && pane.parentNode === body, "the pane is in the body");
  assert.equal(pane.textContent, words, "the same words the person reads (the message names the path, so no hint; a 404 offers no Download)");
  assert.equal(body.querySelector(".fileview-md"), null, "the note left with the swap");
  assert.equal(ctx.text(), DOC, "text() still answers the last landing's text…");
  assert.equal(ctx.mtimeNs(), MT, "…under its mtime: a failed landing lends none");
  assert.equal(ctx.mode(), "rendered", "mode() is unchanged: the view's word, not the pane's; error() is the pane's");
  assert.deepEqual(ctx.renderedImages(), [], "no figures over the pane"); assert.equal(ctx.mediaElement(), null);
  // the file is back: the landing's text paint clears the record and fires the hooks as any paint
  disk[REPORT] = { bytes: DOC, type: "text/plain; charset=utf-8", mtimeNs: "1757145600000000007" };
  ctx.reload(); await settle();
  assert.equal(paints, 3, "the landing's paint");
  assert.equal(ctx.error(), null, "a text view again: error() null");
  assert.ok(body.querySelector(".fileview-md") && !errBar(body), "the note is back and the pane gone");
  assert.equal(ctx.mtimeNs(), "1757145600000000007");
});

test("a first open whose fetch fails paints the pane and fires the hooks like a reload's failure (Slice 7, item 3, open question 5): paints 1, error() the pane's words, text() null and mtimeNs() empty, nothing to overlay", async (t) => {
  const MISSING = ROOT + "/docs/missing.md";
  const { ctx, body } = await open(MISSING, t);
  assert.equal(paints, 1, "the pane is the open's one paint (before: nothing fired, and a panel mounted later would have waited for a paint that never came)");
  assert.equal(ctx.error(), "no such file: " + MISSING, "the stub's 404 words");
  assert.equal(errBar(body)!.textContent, ctx.error(), "the pane in the body carries them");
  assert.equal(ctx.text(), null, "no landing: no text"); assert.equal(ctx.mtimeNs(), "", "and no mtime");
  assert.equal(ctx.mediaElement(), null); assert.deepEqual(ctx.renderedImages(), []);
});

test("scrollToOffset maps a source offset to its Raw row through the anchor map's verified row map: one .fv-cl per logical line, whichever ending the file has (Slice 7 of plans/markdown-viewer.md, item 7); past the end lands on the last row", async (t) => {
  const o = await open(REPORT, t);
  o.b.raw.click();
  // the stand-in does not parse innerHTML; lay the rows codeBlock's markup would produce
  let rows = layRows(o.body.querySelector("code.hljs")!, DOC);
  o.ctx.scrollToOffset(DOC.indexOf("The api session"));
  assert.deepEqual(scrolls(rows), [0, 0, 0, 1, 0, 0], "an LF file: the offset's line is the fourth, row 3, one row scrolled");
  assert.deepEqual(rows[3].scrolledWith, { block: "center" }, "centred");
  o.ctx.scrollToOffset(DOC.length + 50);
  assert.deepEqual(scrolls(rows), [0, 0, 0, 1, 0, 1], "past the end lands on the last row (the map's last row whose start is at or before the offset)");
  // a CR-only file (a classic Mac text, say): the same six lines with a CR after each; before item 7 the seam counted
  // LF alone, so every offset landed on row 0 (and the viewer painted ONE row for the whole file)
  const CR_DOC = DOC.replace(/\n/g, "\r");
  disk[REPORT] = { bytes: CR_DOC, type: "text/plain; charset=utf-8", mtimeNs: "1757145600000000002" };
  o.ctx.reload(); await settle();
  assert.equal(o.ctx.text(), CR_DOC, "the CR text landed"); assert.equal(o.ctx.mode(), "raw", "still the Raw view");
  rows = layRows(o.body.querySelector("code.hljs")!, CR_DOC);
  assert.equal(rows.length, 6, "six rows for six CR-ended lines");
  o.ctx.scrollToOffset(CR_DOC.indexOf("The api session"));
  assert.deepEqual(scrolls(rows), [0, 0, 0, 1, 0, 0], "a CR-only file: the offset's row, row 3 (before item 7: row 0, the LF count)");
  o.ctx.scrollToOffset(CR_DOC.indexOf("We recommend"));
  assert.deepEqual(scrolls(rows), [0, 0, 0, 1, 0, 1], "the sixth line's offset: row 5");
  o.ctx.scrollToOffset(CR_DOC.length + 50);
  assert.deepEqual(scrolls(rows), [0, 0, 0, 1, 0, 2], "past the end: the last row, as for LF");
  // a CRLF file: a CRLF is one ending, so the rows and the offsets are the file's
  const CRLF_DOC = DOC.replace(/\n/g, "\r\n");
  disk[REPORT] = { bytes: CRLF_DOC, type: "text/plain; charset=utf-8", mtimeNs: "1757145600000000003" };
  o.ctx.reload(); await settle();
  rows = layRows(o.body.querySelector("code.hljs")!, CRLF_DOC);
  assert.equal(rows.length, 6);
  o.ctx.scrollToOffset(CRLF_DOC.indexOf("We recommend"));
  assert.deepEqual(scrolls(rows), [0, 0, 0, 0, 0, 1], "a CRLF file: the sixth line's offset lands on row 5");
  // the map refuses (rows that do not match the source: a bug's shape, laid here by hand): the row is counted over the
  // source with the viewer's own split, exact by construction, never a silent last row and never the LF count
  disk[REPORT] = { bytes: CR_DOC, type: "text/plain; charset=utf-8", mtimeNs: "1757145600000000004" };
  o.ctx.reload(); await settle();
  const code = o.body.querySelector("code.hljs")!;
  const wrong = layRows(code, "w\nx\ny\nz\nq\nv\n");
  assert.equal(wrong.length, 6);
  o.ctx.scrollToOffset(CR_DOC.indexOf("The api session"));
  assert.deepEqual(scrolls(wrong), [0, 0, 0, 1, 0, 0], "the map refused (the rows' text is not the source's), the count over the source with the CR split gives row 3 (before item 7: row 0)");
  o.ctx.scrollToOffset(CR_DOC.length + 50);
  assert.deepEqual(scrolls(wrong), [0, 0, 0, 1, 0, 1], "past the end, clamped to the last row");
  const three = layRows(code, "w\nx\ny\n");
  o.ctx.scrollToOffset(CR_DOC.indexOf("We recommend"));
  assert.deepEqual(scrolls(three), [0, 0, 1], "the count beyond the rows laid: clamped to the last of them");
});

// ── what the DOM run above would not catch on its own, pinned at source ────────────────────────────

test("source: the seam's closures are the viewer's own state, and the fileSaved branch reads the kernel's logWarning", () => {
  assert.match(VIEW, /setEditBlocked: \(reason\) => \{\n\s*editBlocked = reason;/, "the reason is stored, not dropped");
  assert.match(VIEW, /mode: \(\) => \(isImage \|\| isPdf\) && !\(svgSource && svgText !== null\) \? "media" : isMd && fmt\.md === "rendered" && renderFell === null \? "rendered" : "raw",/,
    "the text arm reads renderFell (Slice 7 of plans/markdown-viewer.md, item 1; contract C7): over the Raw rows a failed render fell back to, mode() answers raw while the Rendered button stays pressed");
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

test("source: the Slice 3 seam members exist with their doc comments; the media arm fires onRendered through whenShown; the figure rewrite runs on the sanitized DOM, never on marked's string", () => {
  // the two members, as the contract spells them (slice34-contract E4; the regions module reads both)
  assert.ok(VIEW.includes("  mediaElement(): HTMLImageElement | HTMLElement | null;\n"), "FileViewActionCtx has mediaElement()");
  assert.ok(VIEW.includes("  renderedImages(): HTMLImageElement[];\n"), "FileViewActionCtx has renderedImages()");
  const iface = VIEW.split("export interface FileViewActionCtx {")[1].split("\n}")[0];
  const docOf = (member: string): string => { const at = iface.indexOf("\n  " + member); assert.ok(at > 0, member); const above = iface.slice(0, at); return above.slice(above.lastIndexOf("/**")); };
  assert.match(docOf("mediaElement():"), /the `<img>` for an image \(an SVG shown as an image included\), the frame\n\s*\*\s*for a PDF; null for every text view/, "documented in the seam's style, naming every answer");
  assert.match(docOf("renderedImages():"), /in document order/);
  assert.match(docOf("renderedImages():"), /data-fv-src/, "the doc names where the authored src went");
  assert.match(docOf("onRendered(cb"), /a media body once it shows/, "onRendered's doc no longer says TEXT bodies only");
  // Slice 7 of plans/markdown-viewer.md, item 3 (contract C1): error() is a REQUIRED member directly after mtimeNs(), with its doc
  assert.ok(VIEW.includes("  error(): string | null;\n"), "FileViewActionCtx has error()");
  assert.ok(iface.indexOf("\n  mtimeNs(): string;\n") >= 0 && iface.indexOf("\n  error(): string | null;") > iface.indexOf("\n  mtimeNs(): string;\n"), "placed after mtimeNs()");
  assert.equal(iface.slice(iface.indexOf("\n  mtimeNs(): string;\n") + "\n  mtimeNs(): string;\n".length).indexOf("  /** the words of the pane"), 0, "directly after it: the next line opens error()'s doc");
  const errDoc = docOf("error():");
  assert.match(errDoc, /the words of the pane the body shows IN PLACE of the file/, "what it answers");
  assert.match(errDoc, /null while a text or media view shows, the loader included, and null over the\s*\*?\s*Raw rows a failed render falls back to/, "and when it is null: item 1's fallback rows are content");
  assert.match(errDoc, /Closure state\s*\*?\s*\(`viewError`\) set at the two pane paints and cleared at every content paint/, "the mechanism, in the doc");
  assert.match(errDoc, /never read from the body; text\(\) and mtimeNs\(\) keep answering the\s*\*?\s*last landing's/);
  assert.match(docOf("text():"), /error\(\) tells the pane the body shows in its place/, "text()'s doc points at error() for a failed reload");
  assert.match(docOf("onRendered(cb"), /A failure pane is a paint too/, "onRendered's doc says a failure pane is a paint");
  assert.match(VIEW, /mtimeNs: \(\) => mtimeNs,\n\s*error: \(\) => viewError,/, "the closure answers the state, beside mtimeNs");
  assert.match(VIEW, /let viewError: string \| null = null;/, "per open");
  assert.equal((VIEW.match(/viewError = null;/g) || []).length, 3, "cleared at the text paint, the media arm (the SVG Source view, the pages, the frame or picture before whenShown) and the editor's entry");
  assert.match(VIEW, /renderFell = fell;[^\n]*\n\s*\}\n\s*if \(text === ""\) body\.prepend\(textBytes !== null && textBytes > 0 \? bomOnlyLine\(\) : emptyFileLine\(\)\);[^\n]*\n\s*viewError = null;[^\n]*\n\s*folds\.restore\(\);/, "the text paint: after the try's close and the empty file's line, so a swap stood (the Rendered box, or the fallback's line and rows) before the pane's record clears; a fallback swap that throws propagates past it and leaves a standing pane's words (the review's round 3)");
  assert.doesNotMatch(VIEW, /if \(text === null \|\| editing\) return;[^\n]*\n\s*viewError = null;/, "no longer before the pass (round 2's placement: a fallback throw over a standing pane left error() null while the pane stood)");
  assert.match(VIEW, /if \(objUrl === null\) return;[^\n]*\n\s*viewError = null;/, "the media arm: after the loader's return, before every media paint");
  assert.match(VIEW, /viewError = null;[^\n]*\n\s*fireRendered\(\);\n\s*\/\/ a notice over the read view/, "the editor's entry: before its edit-mode render");
  assert.equal((VIEW.match(/viewError = msg;/g) || []).length, 1, "set once at the fetch chain's catch"); assert.equal((VIEW.match(/viewError = words;/g) || []).length, 1, "and once at imgFailed");
  // both read the LIVE body under the mode gate — never a handle kept at paint time
  assert.match(VIEW, /mediaElement: \(\) => \(ctx\.mode\(\) === "media" \? body\.querySelector\("img\.fileview-img, iframe\.fileview-frame, \.fileview-pdf"\) as HTMLElement \| null : null\),/,
    "…the pages root joins the selector for a PDF the chunk renders (Slice 4)");
  assert.match(VIEW, /pdfPages: \(\) => \(ctx\.mode\(\) === "media" && isPdf \? Array\.from\(body\.querySelectorAll\("\.fileview-pdf \.fileview-pdf-page"\)\) as HTMLElement\[\] : \[\]\),/);
  assert.match(VIEW, /renderedImages: \(\) => \(ctx\.mode\(\) === "rendered" \? Array\.from\(body\.querySelectorAll\("\.fileview-md img"\)\) as HTMLImageElement\[\] : \[\]\),/);
  // the media arm: build, mount, THEN wait for the picture — so the element is in the DOM when the hook runs
  const mediaBranch = VIEW.split("if (isImage || isPdf) {")[1].split("if (text === null || editing) return;")[0];
  assert.match(mediaBranch, /const shown = isPdf \? pdfBlock\(objUrl, path\) : imgBlock\(objUrl, path, imgFailed\);\n\s*body\.replaceChildren\(shown\);\n\s*whenShown\(shown, fireRendered\);/);
  const when = VIEW.split("function whenShown(")[1].split("\n}\n")[0];
  assert.match(when, /const img = shown\.querySelector\("img\.fileview-img"\) as HTMLImageElement \| null;/);
  assert.match(when, /if \(!img \|\| img\.complete\) \{ cb\(\); return; \}/, "a frame, or an already-complete img: at once");
  assert.match(when, /img\.addEventListener\("load", \(\) => \{ if \(img\.isConnected\) cb\(\); \}, \{ once: true \}\);/, "else the load event, once, and only for a picture still in the document");
  assert.equal((VIEW.match(/fireRendered\(\);/g) || []).length, 8, "the SVG Source view, the text views, the decode-failure pane, the fetch chain's catch (Slice 7 of plans/markdown-viewer.md, item 3: a refused or failed fetch's pane is a paint, on a first open too), the PDF pages path three times (page 1 drawn; every later page; a later page pdf.js refuses, so the overlay armed on its canvas is redrawn) and enterEdit's edit-mode render (the one paint the panel's cards take their edit-mode state from) call fireRendered directly as a paint; the media arm hands it to whenShown (file-comments.test.ts pins the floor); the two reflows of a text view with its text unchanged (a text-size step, the body's width changing) go through fireRenderedKeepingSelection, which fires the hooks with why 'reflow' (below) so the panel re-places its cards and leaves its marks standing, and a standing selection outlives any hook that does re-wrap (file-view-text-size.test.ts, file-view-reflow-browser.test.ts)");
  assert.equal((VIEW.match(/fireRendered\("reflow"\);/g) || []).length, 1, "the reflows' one call, inside fireRenderedKeepingSelection");
  assert.equal((VIEW.match(/fireRenderedKeepingSelection\(\);/g) || []).length, 2, "the two reflow triggers, and nothing else, keep the selection");
  const failed = VIEW.split("const imgFailed = () => {")[1].split("\n  };\n")[0];
  assert.match(failed, /body\.replaceChildren\(why\);\n\s*viewError = words;[^\n]*\n[\s\S]*fireRendered\(\);$/, "the pane swap fires the hooks AFTER the swap, so a hook reading mediaElement() finds none; error() is set between them (Slice 7, item 3)");
  assert.match(failed, /why\.textContent = DECODE_FAILED;[^\n]*\n\s*const words = why\.textContent;/, "the exported sentence alone (DECODE_FAILED, hoisted for the guide's pin in the Slice 7 review's round 1), taken before the hint and the button join the pane");
  assert.match(VIEW, /\nexport const DECODE_FAILED = "this image failed to decode: it may be mid-write or truncated";\n/, "the constant's export line, the guide's pin");
  // the figure rewrite: called from mdBlock on the sanitized DOM, after DOMPurify; no fallback stands between them since Slice 7 of
  // plans/markdown-viewer.md (item 1): a throw propagates to renderBody's try, whose catch paints the failure line over Raw rows
  assert.match(VIEW, /body\.replaceChildren\(rendered \? mdBlock\(text, \{ kind: "file", path, sid: sid \|\| null \}\) : codeBlock\(text, path, true\)\);/,
    "mdBlock knows the open file's path and sid (as a MdDocLoc since the 2026-09-07 fold: the URL viewer shares the renderer)");
  // code only (codeOnly, below): the order is read off the statements, so a comment quoting the pinned lines above an adopt-first
  // body cannot satisfy it (the fork PR review's pre-answer record built that reversion and every raw-text pin passed on the comment)
  const mdFn = codeOnly(VIEW.split("function mdBlock(text: string, doc?: MdDocLoc): HTMLElement {")[1].split("\n}\n")[0]);
  const sanitizeAt = mdFn.indexOf("const clean = sanitizeMd(dirty, mintHeadingIds);");   // the shared sanitizer, md-sanitize.ts, with the heading ids as its caller pass (before the fill)
  const rewriteAt = mdFn.indexOf('rewriteFigureSrcs(clean, doc.path.slice(0, doc.path.lastIndexOf("/") + 1), doc.sid);');
  const gateAt = mdFn.indexOf("gateRemoteFigures(clean, document.baseURI);");
  const adoptAt = mdFn.indexOf("box.replaceChildren(...Array.from(clean.childNodes));");
  assert.equal(mdFn.indexOf("box.textContent = text;"), -1, "no fallback in mdBlock: the caller keeps the content (file-view.test.ts pins the try)");
  // the figure chain runs on the sanitizer's own body, DOMPurify's inert document, and the adoption into the live document's
  // box comes after it (2026-09-20): WebKit starts an img's fetch the moment its node document is one with a render tree, so
  // a chain after the adoption fetched a gated figure while its placeholder stood (file-view-figures-gate-adopt-browser.test.ts)
  assert.ok(sanitizeAt >= 0 && rewriteAt > sanitizeAt && gateAt > rewriteAt && adoptAt > gateAt, "sanitize, then rewrite, then gate, on `clean`, and only then the adoption into `box`");
  // the second layer, a name list: the three chain helpers named today must not be called over `box`. The REQUIRED guard for the
  // contract (no pass after the adoption sets, repoints, moves or creates a fetching element on an unlisted host) is the node
  // scene's end-state pin through figure-gate's own gateRefs and unlistedHosts (file-view-figures-gate-adopt.test.ts), keyed on
  // the outcome under the box and on no list of names: a new helper, or a pass that creates an element (the fence class), is red
  // there and not here (the round-1 ruling of the fork PR's review, defect A, 2026-09-20). That outcome is the gate's own model of
  // one, gateRefs over FIGURE_SEL's seven tags and the attributes the gate reads per tag, so the scene answers "did the gate's
  // model see a leak" and not "did anything fetch"; an element outside the gate's table is the gate's blind spot and the product's,
  // which no guard keyed on the product's model can see (the review's round 2, correctness-3, tests-2, extra6-2, disclosed there)
  assert.doesNotMatch(mdFn, /(resolveFigureRefs|rewriteFigureSrcs|gateRemoteFigures)\(box,/, "no figure pass runs on the live document's box (a name list, the second layer; the node scene's end-state pin is the guard)");
  assert.ok(mdFn.indexOf("resolveFigureRefs(clean, doc.href);") >= 0 && mdFn.indexOf("resolveFigureRefs(clean, doc.href);") < adoptAt, "the URL kind's resolution runs on `clean` too, before the adoption");
  assert.ok(mdFn.indexOf("return box;") > adoptAt);
  // the fence pass, the one pass that re-parses markup (code-block.ts wrapCodeLines through innerHTML), runs on `clean` between the
  // sanitize and the chain's first call, so the chain judges the elements its re-parse creates (an svg <image> split from its svg
  // comes back an HTML <img>; the fourth scene of file-view-figures-gate-adopt-browser.test.ts, 2026-09-20)
  const fenceAt = mdFn.indexOf('clean.querySelectorAll("pre code").forEach((node) => {');
  const firstChainAt = mdFn.indexOf("resolveFigureRefs(clean, doc.href);");
  assert.ok(fenceAt > sanitizeAt && firstChainAt > fenceAt, "the fence pass runs on `clean`, after the sanitize and before the chain's first call");
  assert.ok(mdFn.indexOf("wrapCodeLines(codeEl);") > fenceAt && mdFn.indexOf("wrapCodeLines(codeEl);") < firstChainAt, "and its re-parse (wrapCodeLines) is inside that pass");
  assert.equal(mdFn.indexOf('box.querySelectorAll("pre code")'), -1, "no fence pass over the live document's box");
  const rw = VIEW.split("export function rewriteFigureSrcs(root: ParentNode, dir: string, sid: string | null | undefined): void {")[1].split("\n}\n")[0];
  // Slice 4 of plans/markdown-viewer.md widened the walk from `img[src]` to every attribute a figure fetches through
  // (figure-gate.ts figureRefs: img src and srcset, source, video src and poster, audio, track, an svg image's href); the
  // path rule is one function applied to each, and only an img's src keeps data-fv-src
  assert.match(rw, /for \(const ref of figureRefs\(root\)\) \{/, "a DOM walk over the sanitized tree");
  assert.match(rw, /if \(!src \|\| src\.startsWith\("\/\/"\) \|\| \/\^\[a-z\]\[a-z0-9\+\.-\]\*:\/i\.test\(src\)\) return null;/, "untouched: empty, protocol-relative URL, any scheme; an absolute PATH is rewritten");
  assert.match(rw, /try \{ rel = decodeURI\(src\); \} catch \{/, "marked's percent-encoding undone; malformed taken as written");
  assert.match(rw, /return fileUrl\(rel\.startsWith\("\/"\) \? rel : dir \+ rel, sid\);/, "the kernel URL: the path itself when absolute, else <dir>/<src>");
  assert.match(rw, /if \(el\.tagName === "IMG" && ref\.attr === "src"\) \{\n\s*if \(p === null\) \{ el\.removeAttribute\("data-fv-src"\); continue; \}\n\s*el\.setAttribute\("data-fv-src", ref\.value\);\n\s*\}/, "the authored value kept on an img's src (the attribute the comments panel pairs an embed by), removed when the src is not a path");
  assert.doesNotMatch(rw, /innerHTML|outerHTML|\.replace\(|DOMParser/, "never a string rewrite of marked's HTML");
  assert.doesNotMatch(rw, /normalize|\.\.\//, "no client-side path normalization: the kernel resolves and gates `..`");
});

// ── the inertness premise, held where CI runs (the review of the gate-before-adoption fix, 2026-09-20) ──────────────
// The chain-before-adoption order pinned above rests on one fact: the body sanitizeMd hands mdBlock belongs to a document
// with no browsing context, so the chain's writes over it start no fetch. The browser legs execute that fact in each engine
// (file-view-figures-gate-adopt-browser.test.ts, the premise probe) and skip wherever Playwright's engines are absent, and
// in CI's job that runs npm test no browser install precedes that step (.github/workflows/ci.yml; the plan pin
// tools/markdown-viewer-plan-gate-adopt.test.mjs reads that property off the job's block), so under CI the fact stood on
// nothing: the pins above and their siblings in the other re-aimed modules match names and call order, and a change that kept both
// while handing back a live-document body left every CI-run test green. The review's refuters measured that in a scratch
// copy of the head (2026-09-20): one key, `ADD_ATTR: ["shadowrootmode"]`, on MD_PURIFY, the sanitize line and the chain as
// written, makes the installed DOMPurify (3.4.10) clone the sanitized body into the LIVE document (its RETURN_DOM branch,
// pinned below), every CI-run module stayed green, and in WebKit the figure server logged the gated figure while the
// placeholder stood; a `document.adoptNode(clean)` guarded by `typeof document` after the sanitize did the same. Under
// node DOMPurify.isSupported is false (the record pin below), so the fact cannot be executed in this suite; this test pins
// the doors to it instead, each one read off the code and derived where a written list would go stale: the profile literal
// whole and its runtime key set (a writer elsewhere would show in the keys), the config the sanitize is handed at run time,
// sanitizeMd's body whole, no live-document call and no config verb in md-sanitize.ts's code, no module of the dashboard but
// md-sanitize.ts naming the profile or DOMPurify's config verbs, the installed library's sites that pick the body's document
// (the factory's template document, _initDocument's two parsers, the RETURN_DOM branch's one road into the live document and
// the guard on it, and the whole dist's count of importNode and adoptNode), the two passes that run over the body INSIDE
// sanitizeMd before mdBlock's chain sees it (the caller's own pass, mintHeadingIds, and every registered post-pass, the
// registrant list derived from the code by its registerMdPostPass calls and held to the census REGISTERED_POST_PASSES,
// red on any new registrant: the round-1 ruling of the fork PR's review, 2026-09-20, found neither swept while this header
// claimed every door, and its ruling on its third round's finding guards-3 kept the census), each opening no door to the live
// document, and, in mdBlock, `clean` reaching the four chain calls and the fence pass's one read (`clean.querySelectorAll`)
// and nothing else before the adoption, and nothing after it. What this test does not do is execute the order: the node scene
// (below) asserts by execution that no node of the sanitizer's body enters the live document until the gate has run over it.
// Comments are stripped before any code is read
// (codeOnly), so a comment may name what the code may not. Red at the head with either of the two changes above (measured
// in a scratch copy, the same day). A red here means the premise moved: re-run the two gate-adopt browser legs in all three
// engines and read the servers' logs before re-aiming a pin. The ORDER itself (the chain's writes landing before the nodes
// enter the live document) is executed under node by file-view-figures-gate-adopt.test.ts, over a stand-in with an inert
// and a live document; the premise, that DOMPurify's body is inert, is what that scene assumes and this test pins.
// codeOnly (ui/test-code-only.ts): the compiler's comment ranges, so a string holding `//`, a template holding `/*` and a
// regex literal ending in backslash-slash are code and stay (the self-check below, and the module's header for the hand
// scanner it replaced and the line that scanner deleted).
test("codeOnly reads the compiler's comment ranges: an affected module keeps the line the hand scanner deleted (settings.ts, a regex literal ending in backslash-slash), md-sanitize.ts keeps a string holding // and loses the doc comments' word, and a synthetic module keeps every literal that holds a comment opener and loses every comment", () => {
  // the affected module the round-1 refuter named: the hand scanner took the regex literal's closing `\//` as a line comment
  const settings = web("settings.ts");
  assert.ok(settings.includes("hostname.toLowerCase()"), "the source holds the call (the pin below reads it back through the stripper)");
  assert.ok(codeOnly(settings).includes("hostname.toLowerCase()"), "settings.ts's hostname.toLowerCase() survives the strip (a regex literal ending in backslash-slash on the same line)");
  assert.ok(codeOnly(settings).includes('/^[a-z][a-z0-9+.-]*:\\/\\//i.test(s) ? s : "http://" + s'), "and the regex literal itself is intact");
  const SAN = web("md-sanitize.ts"), SAN_CODE = codeOnly(SAN);
  assert.ok(SAN_CODE.includes('const HTML_NS = "http://www.w3.org/1999/xhtml";'), "a string literal holding // is kept");
  assert.match(SAN, /allowedTags/); assert.doesNotMatch(SAN_CODE, /allowedTags|\/\*\*|^\s*\* /m, "the doc comments are gone (dropBodyTitle's names the hook's allowedTags lever; the code never does)");
  // a synthetic module: each construct a pattern-based stripper has mis-read, one per line, with a marker each that must survive or go
  const synthetic = [
    'const a = /x:\\/\\//i.test(s) ? s : "http://" + s; const keepA = 1;',       // the ruling's case: a regex literal ending in backslash-slash, then code
    'const b = "a // not a comment"; const keepB = 2;',                        // a string holding //
    'const c = `t /* not a comment */ ${d /* dropC */ + 1}`; const keepC = 3;',  // a template holding /*, with a real comment inside its substitution
    '/* dropD: a regex /a\\/b/ and a "quote" inside a block comment */ const keepD = 4;',
    'const e = "https://host.test/p?q=1#f"; const keepE = 5; // dropE',        // a URL in a string, a trailing line comment
    '/** dropF: see http://x.test/y */ const keepF = 6;',                      // a doc comment holding a URL, code after it on the line
    'const f = g / h; // dropG: a division, then a comment',
    'const i = j / /k/.test(l) ? 1 : 0; const keepH = 7;',                    // a division, then a regex literal: the parser's context tells the two slashes apart (ts.createSourceFile over this line: SlashToken, then RegularExpressionLiteral)
    'const d = a / b / c; // dropH: two divisions, then a comment',           // the division-first control: two slashes that are neither a regex nor a comment opener
  ].join("\n");
  const code = codeOnly(synthetic), whole = stripComments(synthetic);
  for (const keep of ["keepA", "keepB", "keepC", "keepD", "keepE", "keepF", "keepH", '"a // not a comment"', "`t /* not a comment */ ${d  + 1}`", '"https://host.test/p?q=1#f"', "/x:\\/\\//i", "const f = g / h;", "j / /k/.test(l)", "const d = a / b / c;"]) assert.ok(code.includes(keep), "kept: " + keep);
  for (const drop of ["dropC", "dropD", "dropE", "dropF", "dropG", "dropH"]) assert.ok(!code.includes(drop), "gone: " + drop);
  assert.deepEqual(code.split("\n").filter((l) => /\/\*|\/\//.test(l.replace(/"[^"]*"|`[^`]*`|\/x:[^;]*\/i/g, ""))), [], "outside the kept string, template and regex literals no comment opener is left");
  assert.equal(whole.split("\n").length, synthetic.split("\n").length, "stripComments keeps every newline, so line numbers survive");
  assert.equal(code.split("\n").length, 9, "codeOnly drops no line that holds code");
});
/** The profile's keys, in the literal's order: the whole of what sanitizeMd spreads RETURN_DOM onto. */
const PROFILE_KEYS = ["USE_PROFILES", "ADD_DATA_URI_TAGS", "ALLOW_DATA_ATTR", "FORBID_TAGS", "FORBID_ATTR", "SANITIZE_NAMED_PROPS"];

test("the inertness premise, held where CI runs: MD_PURIFY is its six-key literal at the source and at run time and reaches the sanitize with RETURN_DOM alone added; sanitizeMd's body is its five statements; md-sanitize.ts's code opens no door to the live document and no config verb, and no other dashboard module names the profile or those verbs; the installed DOMPurify parses into a template's document, returns that body itself, and clones into the live document only under a shadowroot attribute no profile here allows, and its whole dist holds importNode at four sites and adoptNode at none; the passes that run over the body inside sanitizeMd before the chain, mintHeadingIds and every registered post-pass (derived from the code), open no door to the live document; in mdBlock `clean` reaches the four chain calls and the fence pass's one read (`clean.querySelectorAll`) and nothing else before the adoption, and nothing after it", () => {
  const SAN = web("md-sanitize.ts");
  const SAN_CODE = codeOnly(SAN);
  // the reader's self-check, over an AFFECTED module too (the round-1 refuter's condition): settings.ts keeps the line the hand
  // scanner deleted; md-sanitize.ts keeps a string holding `//` and loses a word the doc comments use and the code does not
  assert.ok(codeOnly(web("settings.ts")).includes("hostname.toLowerCase()"), "codeOnly keeps settings.ts's hostname.toLowerCase() (a regex literal ending in backslash-slash sits before it on the line)");
  assert.ok(SAN_CODE.includes('const HTML_NS = "http://www.w3.org/1999/xhtml";'), "codeOnly keeps a string literal holding //");
  assert.match(SAN, /allowedTags/); assert.doesNotMatch(SAN_CODE, /allowedTags|\/\*\*|^\s*\* /m, "codeOnly drops the doc comments (dropBodyTitle's names the hook's allowedTags lever; the code never does)");
  // ── the profile: the literal whole, the object's keys, the config the sanitize is handed ──
  const literal = /^export const MD_PURIFY: Config = \{\n([\s\S]*?)\n\};$/m.exec(SAN_CODE);
  assert.ok(literal, "the profile is one exported literal");
  assert.deepEqual(literal![1].split("\n"), [
    "  USE_PROFILES: { html: true, svg: true },",
    '  ADD_DATA_URI_TAGS: ["img"],',
    "  ALLOW_DATA_ATTR: false,",
    "  FORBID_TAGS: [...MD_FORBID_TAGS],",
    "  FORBID_ATTR: [...MD_FORBID_ATTR],",
    "  SANITIZE_NAMED_PROPS: true,",
  ], "the six entries and no other: no ADD_ATTR, ADD_TAGS or ALLOWED_* (an allowed `shadowroot` or `shadowrootmode` makes DOMPurify clone the body into the live document, below), no RETURN_DOM_FRAGMENT, IN_PLACE or WHOLE_DOCUMENT");
  assert.deepEqual(Object.keys(MD_PURIFY), PROFILE_KEYS, "the object at run time has the literal's keys: no module added one after load");
  const seen: Array<Record<string, unknown>> = [];
  const recorder = { addHook: () => { /* the hooks are DOMPurify's; the recorder has none */ }, sanitize: (_dirty: string, cfg: Record<string, unknown>) => { seen.push(cfg); return new El("body"); } };
  setMdSanitizer(recorder as unknown as Parameters<typeof setMdSanitizer>[0]);
  try { sanitizeMd('<p><img src="http://remote.test/x.png"></p>'); }
  finally { setMdSanitizer(fakeSanitizer as unknown as Parameters<typeof setMdSanitizer>[0]); }   // the suite's stand-in back, for every paint after this test
  assert.equal(seen.length, 1, "one sanitize per sanitizeMd");
  assert.deepEqual(Object.keys(seen[0]), [...PROFILE_KEYS, "RETURN_DOM"], "the sanitize is handed the profile's keys and RETURN_DOM, nothing else");
  assert.equal(seen[0].RETURN_DOM, true);
  assert.deepEqual(seen[0].USE_PROFILES, { html: true, svg: true }, "DOMPurify's html and svg attribute lists, which quote no shadowroot attribute (below)");
  // ── sanitizeMd's body, whole ──
  const fnAt = SAN_CODE.indexOf("export function sanitizeMd(");
  assert.ok(fnAt > 0);
  assert.deepEqual(SAN_CODE.slice(fnAt, SAN_CODE.indexOf("\n}\n", fnAt) + 2).split("\n"), [
    "export function sanitizeMd(dirty: string, own?: (body: HTMLElement) => void): HTMLElement {",
    "  installMdSanitizeHooks();",
    "  const clean = purifier().sanitize(dirty, { ...MD_PURIFY, RETURN_DOM: true }) as HTMLElement;",
    "  keepOnlyInertCheckboxes(clean);",
    "  if (own) own(clean);",
    "  for (const pass of postPasses) pass(clean);",
    "  return clean;",
    "}",
  ], "the body DOMPurify returns is the body handed back: no statement between the sanitize and the return moves it or its nodes anywhere");
  assert.equal((SAN_CODE.match(/\bRETURN_DOM\b/g) || []).length, 1, "RETURN_DOM is spelled at the one sanitize");
  // ── no door to the live document, no config verb, in md-sanitize.ts's code ──
  for (const door of [/\bdocument\./, /\b(?:window|globalThis|self)\.document\b/, /adoptNode/, /importNode/, /RETURN_DOM_FRAGMENT/, /\bIN_PLACE\b/, /WHOLE_DOCUMENT/,
    /ADD_ATTR/, /ADD_TAGS/, /ALLOWED_ATTR/, /ALLOWED_TAGS/, /allowedAttributes/, /shadowroot/i, /setConfig/, /clearConfig/, /DOMParser/, /createHTMLDocument/,
    /createElement\(/, /innerHTML/, /outerHTML/, /insertAdjacentHTML/]) {
    assert.doesNotMatch(SAN_CODE, door, "md-sanitize.ts's code never spells " + String(door) + ": the live document (adoptNode, importNode, createElement, a fragment of it), a DOMPurify option or verb that changes which document the body belongs to (RETURN_DOM_FRAGMENT, IN_PLACE, an allowed shadowroot attribute through ADD_ATTR or ALLOWED_ATTR, setConfig), or a re-parse of the markup");
  }
  assert.deepEqual(SAN_CODE.match(/^.*ownerDocument.*$/gm), ["  (node.ownerDocument as Document).createDocumentFragment().appendChild(node);"],
    "the one call on a node's document is dropBodyTitle's fragment of the node's OWN document, DOMPurify's parse document during a sanitize");
  // ── no other module of the dashboard names the profile or DOMPurify's config verbs (a writer to MD_PURIFY, or a setConfig, which
  // makes DOMPurify ignore the per-call config, would change the body's document with the literal above intact) ──
  const UI_DIR = path.resolve(process.cwd(), "..", "ui", "webview");
  const others = fs.readdirSync(UI_DIR).filter((f) => f.endsWith(".ts") && !f.endsWith(".test.ts") && !f.endsWith(".d.ts") && f !== "md-sanitize.ts");
  assert.ok(others.includes("file-view.ts") && others.includes("render.ts"), "the sweep reads the dashboard's modules");
  const namers = others.filter((f) => { const code = codeOnly(web(f)); return /\b(?:MD_PURIFY|setConfig|clearConfig|addHook|RETURN_DOM|adoptNode|importNode)\b/.test(code) || /shadowroot/i.test(code); });
  assert.deepEqual(namers, [], "the profile, DOMPurify's config verbs, its hook registry and RETURN_DOM are md-sanitize.ts's alone (md-sanitize.test.ts sweeps the sanitize call and the seam the same way), and no dashboard module adopts or imports a node between documents (a guarded document.adoptNode inside the gate's own helper left every CI-run module green in the fork PR review's pre-answer mutation table, 2026-09-20)");
  // ── the passes that run over the body INSIDE sanitizeMd, before mdBlock's chain: the caller's own pass (mdBlock hands
  // mintHeadingIds; the sanitize-line pin above) and every registered post-pass (md-sanitize.ts postPasses, run in sanitizeMd's
  // fifth statement, above). Neither is in the chain block, so the mdBlock pins below never read them, and a live-document
  // adoption in either puts the body in the page before the chain with every pin below green (the round-1 ruling of the fork
  // PR's review, defect D, 2026-09-20). The registrant list is DERIVED here from the code and held to a written census: every
  // `registerMdPostPass(<name>)` in a dashboard module's comment-stripped code, the name resolved to its defining module
  // (the module itself, or a `./` module it imports the name from). A registration the resolver cannot follow (an inline
  // function, a member expression, a renamed or namespace import) is red here, so it is widened before it is trusted. ──
  assert.equal((SAN_CODE.match(/\bregisterMdPostPass\b/g) || []).length, 1, "md-sanitize.ts spells registerMdPostPass once, at its definition: the registry has no second writer there");
  assert.equal((SAN_CODE.match(/\bpostPasses\b/g) || []).length, 4, "and postPasses four times: the declaration, the includes and the push inside registerMdPostPass, the loop inside sanitizeMd (a fifth is a new door into the registry)");
  const REGISTER = /(?<!function )\bregisterMdPostPass\s*\(([^)]*)\)/g;
  const named = (clause: string): string[] => clause.split(",").map((raw) => raw.replace(/\btype\s+/, "").trim().split(/\s+as\s+/).pop() || "").filter(Boolean);
  const fnBody = (src: string, name: string, where: string): string => {
    const at = src.search(new RegExp("^(?:export )?function " + name + "\\(", "m"));
    assert.ok(at >= 0, where + " defines `function " + name + "(` at the top level (the sweep reads a top-level function's body; another form is widened here first)");
    const end = src.indexOf("\n}\n", at);   // the next top-level close; the module's last function closes at the end of the stripped text
    assert.ok(end >= 0 || src.endsWith("\n}"), where + ": " + name + "'s body closes at the top level");
    return src.slice(at, end < 0 ? src.length : end + 2);
  };
  const registrants: Array<{ site: string; name: string; module: string; body: string }> = [];
  for (const f of others) {
    const code = codeOnly(web(f));
    for (const m of code.matchAll(REGISTER)) {
      const arg = m[1].trim();
      assert.match(arg, /^[A-Za-z_]\w*$/, f + ": a registration the derivation cannot follow, `registerMdPostPass(" + arg + ")`: register a named function, and widen the resolver here first");
      let module = f;
      if (!new RegExp("^(?:export )?function " + arg + "\\(", "m").test(code)) {
        module = "";
        for (const im of code.matchAll(/import (?:type )?\{([^}]*)\} from "\.\/([^"]+)"/g)) if (named(im[1]).includes(arg)) module = im[2] + ".ts";
        assert.ok(module, f + ": registrant `" + arg + "` is neither a function of the module nor a name it imports from a `./` module under `import { ... }` (a namespace, default or renamed import: widen the resolver here first)");
      }
      registrants.push({ site: f, name: arg, module, body: fnBody(codeOnly(web(module)), arg, module) });
    }
  }
  assert.ok(registrants.length > 0, "the derivation found the registrations (an empty derivation is a broken reader, not a clean tree)");
  // ── the census: the derived list against REGISTERED_POST_PASSES, and red on ANY registrant not in it, a read-only one included
  // (the fork PR review's ruling on its third round's finding guards-3, 2026-09-20). The census cannot tell a read-only
  // registrant from one whose body it cannot follow: the sweep below reads a body's own text and not its callees, so a road to
  // the live document through a helper the body calls is invisible to it, and greening the first would green the second, which
  // reopens the premise this fix rests on, that nothing puts the body in the live document before the gate runs. A person adding
  // a read-only registrant pays one red and one line here; the red names both. ──
  const REGISTERED_POST_PASSES = ["md-config.ts: registerMdPostPass(renderMathPlaceholders) -> math.ts"];
  const CENSUS_REMEDY = "a registrant outside the census: judge the new registrant's body for live-document roads (the doors the sweep below reads, and any callee of its own that reaches the live document, which the sweep does not follow), then add its line to REGISTERED_POST_PASSES in ui/webview/file-view-seam.test.ts; the census refuses a read-only registrant too, since it cannot tell one from a registrant whose body it cannot follow";
  // The remedy's two names are read off the message and checked against this module's own source, never repeated here: the
  // constant it names must be declared in this file as an array literal (so a rename of the declaration that leaves the
  // message stale is red), and the file it names must be the one this module reads itself from (the one literal handed to
  // web). Found by the fork PR review's verification of the guards-3 change, 2026-09-20: the check before this one held
  // the message to a second copy of both names, and a rename of the declaration, its use and that copy stayed green.
  const SEAM_FILE = "file-view-seam.test.ts";
  const SELF = web(SEAM_FILE);
  const remedyNames = /add its line to (\w+) in ui\/webview\/([\w.-]+);/.exec(CENSUS_REMEDY);
  assert.ok(remedyNames !== null && new RegExp("^\\s*const " + remedyNames[1] + " = \\[", "m").test(SELF) && remedyNames[2] === SEAM_FILE,
    "the census's red names its remedy: the constant it says to add the line to is declared in this module as an array literal, and the file it names is the one this module reads itself from (the message names " + JSON.stringify(remedyNames && remedyNames.slice(1)) + ")");
  assert.deepEqual(registrants.map((r) => r.site + ": registerMdPostPass(" + r.name + ") -> " + r.module), REGISTERED_POST_PASSES,
    "the registered post-passes, derived from the code, are the census REGISTERED_POST_PASSES (one, the math fill, registered by md-config.ts and defined in math.ts); " + CENSUS_REMEDY);
  const preChain = [{ label: "mintHeadingIds (file-view.ts, the pass mdBlock hands sanitizeMd)", body: fnBody(codeOnly(VIEW), "mintHeadingIds", "file-view.ts") }, ...registrants.map((r) => ({ label: r.name + " (" + r.module + ", registered by " + r.site + ")", body: r.body }))];
  // no door to the live document in any of them: no `document`, `window`, `globalThis` or `self` (the live document and its
  // window), no cross-document verb, no element creation (a node created outside the body's document is a road out of it when
  // the body is appended into it), no re-parse; and every insertion verb's receiver is a binding of the pass's own (a parameter
  // or a local), never a module-level or imported element
  const PRE_CHAIN_DOORS = [/\bdocument\b/, /\b(?:window|globalThis|self)\b/, /adoptNode/, /importNode/, /createElement(?:NS)?\(/, /createTextNode\(/, /createDocumentFragment\(/, /createContextualFragment/, /innerHTML|outerHTML|insertAdjacentHTML|insertAdjacentElement|DOMParser|\bsetHTML\w*\s*\(|parseHTMLUnsafe/];
  const INSERT = /\b([A-Za-z_]\w*)\.(appendChild|append|prepend|insertBefore|replaceChildren|replaceWith|after|before)\(/g;
  for (const { label, body } of preChain) {
    assert.ok(body.split("\n").length > 2, label + ": the body was read");
    for (const door of PRE_CHAIN_DOORS) assert.doesNotMatch(body, door, label + " spells " + String(door) + " in a pass that runs over the sanitizer's body BEFORE the chain: a live-document road there puts the body in the page before the gate has run (the node scene's order leg executes this; this pin reads the code)");
    for (const m of body.matchAll(INSERT)) {
      const recv = m[1];
      const own = new RegExp("\\b(?:const|let|var)\\s+" + recv + "\\b|function \\w+\\([^)]*\\b" + recv + "\\b|\\(\\s*" + recv + "\\s*[,)]|[(,]\\s*" + recv + "\\s*[,)]|\\b" + recv + "\\s*=>");
      assert.ok(own.test(body), label + ": `" + m[0] + "` inserts into `" + recv + "`, which is not a parameter or a local of the pass (an element from outside the body is a road out of it)");
    }
  }
  // ── the installed library: the sites that pick the body's document, in every dist a bundler can take ──
  const DP = path.resolve(process.cwd(), "node_modules", "dompurify");
  const version = (JSON.parse(fs.readFileSync(path.join(DP, "package.json"), "utf8")) as { version: string }).version;
  for (const f of ["purify.es.mjs", "purify.cjs.js", "purify.js"]) {
    const lib = fs.readFileSync(path.join(DP, "dist", f), "utf8");
    const tag = "dompurify " + version + " " + f + ": ";
    // the factory: the live document is kept as originalDocument and importNode is its method; `document` becomes a <template>'s
    // content document, one with no browsing context, where the engine has templates
    assert.match(lib, /\n\s*let document = window\.document;\n\s*const originalDocument = document;\n/, tag + "the factory keeps the live document as originalDocument");
    assert.match(lib, /const template = document\.createElement\('template'\);\n\s*if \(template\.content && template\.content\.ownerDocument\) \{\n\s*document = template\.content\.ownerDocument;\n/, tag + "and works in a template's content document from then on");
    assert.match(lib, /\n\s*const importNode = originalDocument\.importNode;\n/, tag + "importNode is the live document's, the one method of it the sanitize keeps");
    // _initDocument: the parse document is DOMParser's, or one implementation (the template document's) creates; the only
    // `document.` call lends a text node, which insertBefore adopts into the body's document
    const initAt = lib.indexOf("_initDocument = function _initDocument(dirty) {");
    const initEnd = lib.indexOf("return WHOLE_DOCUMENT ? doc.documentElement : body;", initAt);
    assert.ok(initAt > 0 && initEnd > initAt, tag + "_initDocument is where the parse document is made");
    const init = codeOnly(lib.slice(initAt, initEnd), "js");
    assert.match(init, /doc = new DOMParser\(\)\.parseFromString\(dirtyPayload, PARSER_MEDIA_TYPE\);/, tag + "DOMParser first");
    assert.match(init, /doc = implementation\.createDocument\(NAMESPACE, 'template', null\);/, tag + "a created document when DOMParser gives none");
    assert.deepEqual(init.match(/\b(?:document|originalDocument|window)\.\w+/g), ["document.createTextNode"], tag + "the live document is not consulted for the parse document; the template document lends a text node");
    assert.doesNotMatch(init, /adoptNode|importNode/, tag + "nothing in the parse is moved between documents");
    // the RETURN_DOM branch: the parse document's body itself (or a fragment of the same document), cloned into the live document
    // by importNode ONLY when shadowroot or shadowrootmode is an allowed attribute
    const at = lib.indexOf("if (RETURN_DOM) {");
    const end = lib.indexOf("return returnNode;", at);
    assert.ok(at > 0 && end > at, tag + "the RETURN_DOM branch");
    const branch = codeOnly(lib.slice(at, end), "js");
    assert.match(branch, /if \(RETURN_DOM_FRAGMENT\) \{\n\s*returnNode = createDocumentFragment\.call\(body\.ownerDocument\);/, tag + "a fragment, were one asked for, is the body's own document's");
    assert.match(branch, /\} else \{\n\s*returnNode = body;\n\s*\}/, tag + "RETURN_DOM alone hands back the parse document's body itself");
    assert.match(branch, /if \(ALLOWED_ATTR\.shadowroot \|\| ALLOWED_ATTR\.shadowrootmode\) \{\n\s*returnNode = importNode\.call\(originalDocument, returnNode, true\);\n\s*\}\n?$/, tag + "the one road into the live document, a deep clone under importNode, taken only when shadowroot or shadowrootmode is allowed");
    assert.deepEqual(branch.match(/\b(?:originalDocument|document|adoptNode|importNode)\b/g), ["importNode", "originalDocument"], tag + "no other door in the branch");
    assert.doesNotMatch(lib, /['"]shadowroot(?:mode)?['"]/, tag + "no attribute list quotes shadowroot or shadowrootmode: neither the html nor the svg profile allows either, so the profile above cannot take that road by itself");
    // the whole dist, not the two regions above: every cross-document verb in the library's code, counted (comments stripped:
    // the raw text holds importNode seven times per dist, three of them in comments)
    const code = codeOnly(lib, "js");
    assert.equal((code.match(/\bimportNode\b/g) || []).length, 4, tag + "importNode at four sites in the whole dist's code: the factory's `const importNode = originalDocument.importNode` (the binding and the method), the RETURN_DOM branch's `importNode.call(originalDocument, returnNode, true)` (the one road into the live document, guarded above), and `body.ownerDocument.importNode(dirty, true)`, which clones a Node handed to sanitize into the PARSE document's body (sanitizeMd hands a string); a fifth site is a new cross-document road, judged here first");
    assert.equal((code.match(/\badoptNode\b/g) || []).length, 0, tag + "adoptNode nowhere in the dist's code");
  }
  // ── mdBlock: `clean` reaches the chain's four calls and the fence pass's one read before the adoption, and nothing after it ──
  const mdCode = codeOnly(VIEW.split("function mdBlock(text: string, doc?: MdDocLoc): HTMLElement {")[1].split("\n}\n")[0]);
  const bind = "const clean = sanitizeMd(dirty, mintHeadingIds);", adopt = "box.replaceChildren(...Array.from(clean.childNodes));";
  const bindAt = mdCode.indexOf(bind), adoptAt = mdCode.indexOf(adopt);
  assert.ok(bindAt > 0 && adoptAt > bindAt, "the body is bound to `clean` and adopted later");
  const between = mdCode.slice(bindAt + bind.length, adoptAt);
  assert.deepEqual(between.match(/\w+\(clean\b/g), ["resolveFigureRefs(clean", "gateRemoteFigures(clean", "rewriteFigureSrcs(clean", "gateRemoteFigures(clean"],
    "between the sanitize and the adoption `clean` is handed to the four chain calls (the URL kind's resolution and gate, the file kind's rewrite and gate) and to nothing else");
  assert.deepEqual(between.match(/\bclean\.\w+/g), ["clean.querySelectorAll"], "and the one property read of `clean` there is the fence pass's (a new use of the body before the adoption, a call or a read, is red here first)");
  assert.deepEqual(between.match(/\bdocument\.\w+/g), ["document.baseURI", "document.baseURI", "document.baseURI"], "the live document is read there for its base URI alone");
  assert.doesNotMatch(between, /\bbox\b|adoptNode|importNode|appendChild|\bappend\(|prepend\(|insertBefore|replaceChildren|replaceWith|\bafter\(|\bbefore\(/, "nothing moves a node into the live document before the chain is done");
  assert.doesNotMatch(mdCode.slice(adoptAt + adopt.length), /\bclean\b/, "after the adoption every pass reads `box`; the body is not touched again");
  assert.doesNotMatch(mdCode.slice(0, bindAt), /\bclean\b/, "and nothing is called `clean` before the sanitize binds it");
});

// ── no re-parse after the adoption: the population of re-parsing sites, derived from the code ──────────────────────────────
// The rule mdBlock's chain block states (file-view.ts): every pass that sets, repoints, moves or CREATES a fetching element runs
// before the adoption. A pass creates one by re-parsing or re-serializing markup in the live document: the fence pass's
// wrapCodeLines (code-block.ts) does that through innerHTML, and with the pass after the adoption an svg <image> split from its
// <svg> by the line splitter came back an HTML <img> the chain had never judged, which fetched from an unlisted host in all three
// engines (the fork PR review's pre-answer record, 2026-09-20; the fourth scene of file-view-figures-gate-adopt-browser.test.ts).
// The walk of attribute writes above cannot see that road (it writes no fetching attribute), so this test greps for the verbs that
// re-parse or re-serialize: RE_PARSE, over comment-stripped code, in the region of mdBlock after the adoption line and in every
// module a pass in that region reaches. The reach is walked in three steps, each derived from the code and pinned: the
// identifiers called in the region (every bare call there, no method call on an imported binding), each resolved through
// file-view.ts's named imports to its module or to a local function; the local functions reached from those, transitively over
// bare calls (REACHED_LOCALS), and every IMPORTED function a reached local calls, resolved the same way to its module
// (IMPORTED_CALLEES, each to its module, the one-line record the plan's paragraph is filled from; before the file review's
// landing round the walk followed a reached local's LOCAL calls alone, so the modules those functions live in sat outside the
// judged set while this header already promised the transitive reach, and a live re-parse write planted in any of them left
// this test green); then
// every module those modules name in an import the compiler parses (an import declaration under any clause: a named import, a
// type-only one, a namespace or default import, a side-effect import; an `export ... from`; an `import x = require()`; and a
// dynamic `import()` or `require()` of a string literal), under any quote and across any line break, a specifier that is not a
// string literal refused with its file and line (the file review's landing round, tests-1 with extra5-1, extra7-1 and extra7-2:
// the regex resolver before it read a double-quoted specifier at a line's start alone, so a single-quoted import in any reached
// module dropped that module and its whole closure from the judged set with nothing red, and its binding reader read
// `import ... from` lines alone, so file-view.ts's require-bound gclock was outside the method-call guard), transitively, and
// from every path relative to the importing module (`./x` and the vendored engine anchor-map.ts
// reads from `../../vendor/`, and gesture-clock.js), so the closure (REACHED_MODULES) is the whole set of modules a pass in the region can reach
// through the viewer's own code, on the safe side: a type-only import is followed too, since deciding which imports the
// compiler erases is a judgement this census need not make, and file-view.ts itself re-enters the set through file-comments.ts's
// type import of the viewer's action type, which brings every module file-view.ts imports along. What the walk does not read,
// stated so a green here is read for what it covers: the npm packages a reached module imports (PACKAGE_IMPORTS, derived and
// pinned: marked, DOMPurify, KaTeX, and highlight.js's core with its grammars), whose own code is not the viewer's; the sanitizer's and the highlighter's
// parses run before the adoption over `clean` (pinned above), and a write a package makes onto an element handed to it is that
// caller's site, judged where the caller is. The verbs are the HTML-parsing entry points an element or a document offers, the
// string-serializing reads a write can round-trip through, and a template element, whose content is parsed markup: innerHTML and
// outerHTML writes, insertAdjacentHTML, insertAdjacentElement, createContextualFragment, DOMParser, document.write, setHTMLUnsafe
// and parseHTMLUnsafe (which the installed lib.dom.d.ts carries), setHTML (the Sanitizer API's, not in those typings yet), and a
// template created by createElement or this module's `el` helper under any spelling of the argument (`[^)]*template`, the
// form the derivation command below and the plan's paragraph spell: a name under any quote, or one chosen or assembled inside
// the call; the fork PR review's verification found the first spelling of this list without setHTML, setHTMLUnsafe and
// parseHTMLUnsafe, and matching the double-quoted createElement alone, 2026-09-20, and the author's closing pass after the
// file review's landing round found RE_PARSE matching a name under a quote alone while the command spelled the wider form,
// and widened RE_PARSE to the command's form, the same lines matching at that head under both). The derivation itself is
// pinned (the callee list, the reached locals, the imported callees, the module
// set, the package list, and the import forms the resolver follows, by synthetic modules holding each form, the spellings the
// regex resolver once dropped among them, with a non-literal specifier asserted to refuse), so a new pass,
// call or import widens it here first, and a new such site after the adoption is red until it is judged in this list. The
// judged sites: mdBlock holds one write, the hljs highlight's, inside the fence pass BEFORE the adoption (escaped text: hljs
// creates spans alone); a reached local holds one, the figure control's glyph parsed onto a holder that enters no document;
// and every other module the walk reaches holds the sites JUDGED_SITES lists for it, each with its reason, or none: a write of
// the viewer's own constant markup onto a node outside the Rendered box (a tray or status icon, the panel's loader), a write
// onto a node that enters no document (anchor-map.ts's detached textarea, its character-reference decoder), a parse into a
// document of its own that is read and never adopted (reader-place.ts's DOMParser), a type annotation naming the property, and
// code-block.ts's wrapCodeLines, run before the adoption. None re-parses markup under `box` after the adoption. The whole
// file's count for file-view.ts is pinned as well, in the one assertion below that holds the number (the plan's re-parse
// paragraph and its tools pin read the count from that assertion, so the figure has one home), and file-view.ts is judged by
// that count rather than in the per-module loop; a new site anywhere in file-view.ts is red here until it is judged and the
// plan's count follows. The two property names are matched BARE (`\b(?:innerHTML|outerHTML)\b`, a read or a write under any
// spelling), not as `innerHTML =`: a write spelled `x["innerHTML"] = s`, `Object.assign(x, { innerHTML: s })` or
// `x.innerHTML ||= s` reaches the same setter and the assignment spelling did not match it (the fork PR review's round 2,
// its finding on the guards, 2026-09-20: such a write planted inside an existing post-adoption callee left this test green); a read of
// either in the region or a reached module is as suspect as a write, so the judged lines include a type annotation and the
// decoder's reads. The node scene records the write itself, by the property's setter, whatever the spelling
// (file-view-figures-gate-adopt.test.ts, Reparse). Derivation command, for a reader by hand (the test runs the same over
// codeOnly): grep -nE '\b(?:innerHTML|outerHTML)\b|insertAdjacentHTML|createContextualFragment|DOMParser|document\.write\b|
// insertAdjacentElement|\bsetHTML\w*\s*\(|parseHTMLUnsafe|createElement\(\s*[^)]*template|\bel\(\s*[^)]*template' over
// file-view.ts's mdBlock after the adoption line and over the modules REACHED_MODULES names.
const RE_PARSE = /\b(?:innerHTML|outerHTML)\b|insertAdjacentHTML|createContextualFragment|DOMParser|document\.write\b|insertAdjacentElement|\bsetHTML\w*\s*\(|parseHTMLUnsafe|createElement\(\s*[^)]*template|\bel\(\s*[^)]*template/;
/** The local functions of file-view.ts a post-adoption pass reaches, transitively over bare calls (derived below; a new one
 *  widens this list first and is judged against RE_PARSE with the rest). */
const REACHED_LOCALS = ["keepVideoShape", "addFigureControls", "pxDimension", "decideFigureControl", "figureAnchor", "figureControlAfter", "figureWantsControl", "removeFigureControl", "el", "figureControlGlyph", "oneImg", "linkAround", "figureState", "figureHasPicture", "figureTooSmall", "figureTarget", "linkAbove", "ringOf", "figureBox", "chosenSource", "absUrl"];
/** The imported functions a reached local calls, each to the module file-view.ts imports it from (derived below; a new one
 *  widens the module set first). One line with quoted keys: tools/markdown-viewer-plan-gate-adopt.test.mjs reads it as JSON
 *  and fills the plan's re-parse paragraph from it, so the names and their modules' count have this one home. */
const IMPORTED_CALLEES: Record<string, string> = { "figurePath": "file-comments-model.ts", "parseSrcset": "figure-gate.ts", "pictureDest": "file-comments.ts" };
/** The bare calls in a reached local that are neither a local function, an import nor a name the body binds itself: the
 *  language's globals (derived below; a new one is judged here first; neither parses markup, and DOMParser is RE_PARSE's). */
const GLOBAL_CALLS = ["Number", "URL"];
/** The modules a post-adoption pass reaches (derived below): the region's and the reached locals' imported callees' modules,
 *  then every module those name in an import the compiler parses, transitively, under any quote and any line break (a
 *  specifier that is not a string literal refuses); paths relative to
 *  ui/webview, a suffix kept as written (`.js` for the two JavaScript modules) and `.ts` supplied where the import has none.
 *  A new import widens this list first. */
const REACHED_MODULES = ["../../vendor/track-changents/engine.js", "actions.ts", "anchor-map.ts", "backend-names.ts", "capped-read.ts", "card-layout.ts", "code-block.ts", "commands.ts", "comments.ts", "ctx-color.ts", "docreview.ts", "fence-source.ts", "figure-gate.ts", "file-comments-model.ts", "file-comments-regions.ts", "file-comments.ts", "file-trail.ts", "file-view-links.ts", "file-view.ts", "gesture-clock.js", "host-prefix.ts", "icons.ts", "keybindings.ts", "link-opener.ts", "math.ts", "md-block-start.ts", "md-config.ts", "md-links.ts", "md-literal-tags.ts", "md-sanitize.ts", "media.ts", "path-links.ts", "pdf-cap.ts", "pick-held.ts", "pinch.ts", "preview.ts", "reader-place.ts", "region-geometry.ts", "session-badge.ts", "settings.ts", "status-widgets.ts", "tab-state.ts", "tab-widgets.ts", "url-links.ts", "viewer-grammars.ts", "widget-prefs.ts"];
/** The npm packages the reached modules import (derived below), which the walk does not read (the header says why). */
const PACKAGE_IMPORTS = ["dompurify", "highlight.js/lib/core", "highlight.js/lib/languages/bash", "highlight.js/lib/languages/c", "highlight.js/lib/languages/css", "highlight.js/lib/languages/diff", "highlight.js/lib/languages/go", "highlight.js/lib/languages/ini", "highlight.js/lib/languages/java", "highlight.js/lib/languages/javascript", "highlight.js/lib/languages/json", "highlight.js/lib/languages/markdown", "highlight.js/lib/languages/python", "highlight.js/lib/languages/rust", "highlight.js/lib/languages/sql", "highlight.js/lib/languages/typescript", "highlight.js/lib/languages/xml", "highlight.js/lib/languages/yaml", "katex", "marked"];
/** The re-parse sites RE_PARSE finds in the reached modules other than file-view.ts (judged by its whole-file count below):
 *  per module, each matching code line (comment-stripped, trimmed) with the judgement that lets it stand. A module absent here
 *  holds none; a new line, a moved one or a module gaining one is red until it is judged here. */
const JUDGED_SITES: Record<string, Array<[line: string, why: string]>> = {
  "anchor-map.ts": [
    ["let refDecoder: { innerHTML: string; textContent: string | null } | null | undefined;", "a type annotation naming the property: no read, no write"],
    ['if (d) { d.innerHTML = "&amp;&ltimes;"; if (d.textContent === "&\\u22c9") refDecoder = d; }', "domRefText's probe: a constant reference written onto a textarea created from the document and inserted nowhere, its text read back"],
    ['if (v === undefined) { refDecoder.innerHTML = ref; v = refDecoder.textContent || ""; refMemo.set(ref, v); }', "the decoder itself: a character reference written onto that detached textarea and read back as text; the textarea enters no document (pinned below)"],
  ],
  "code-block.ts": [["code.innerHTML = wrapLinesHtml(code.innerHTML);", "wrapCodeLines, the fence pass's re-parse, run over `clean` before the adoption (pinned above and below)"]],
  "file-comments.ts": [["w.innerHTML = '<img src=\"/media/romp-swirl-glyph.svg\" alt=\"\"><span>romp</span>'", "the Comments panel's loader row: the viewer's own constant markup with a same-origin /media path, on a row of the panel, never under the Rendered box"]],
  "preview.ts": [
    ["dl.innerHTML = ICON_DOWNLOAD;", "the lightbox tray's download control: icons.ts's constant drawing on the tray's own anchor"],
    ['btn.innerHTML = icon; btn.title = word; btn.setAttribute("aria-label", word);', "the tray's copy control swapping among icons.ts's constant drawings"],
  ],
  "reader-place.ts": [
    ['if (!isHtmlBlock(source, span) || typeof DOMParser !== "function") return false;', "a presence test of the parser, no parse"],
    ['const body = new DOMParser().parseFromString(source.slice(span.start, span.end) + "\\n<p " + PROBE + "></p>", "text/html").body;', "opensWrapper: the note's html block parsed into a document of its own, read for its shape and never adopted"],
    ['if (typeof DOMParser !== "function") return null;', "a presence test of the parser, no parse"],
    ['const parsed = elementsOf(new DOMParser().parseFromString(source.slice(span.start, span.end), "text/html").body);', "ownedElements: the same parse into its own document, its elements counted and compared, never adopted"],
  ],
  "status-widgets.ts": [["span.innerHTML = FOLDER_ICON_SVG;", "the statusline's folder icon, this module's constant markup, on the status line"]],
};
test("no re-parse after the adoption: mdBlock's post-adoption region and every module a pass there reaches, derived from the code through the reached locals' imported callees and every import form transitively, hold no use of innerHTML or outerHTML (a write under any spelling, or a read) and no insertAdjacentHTML, insertAdjacentElement, createContextualFragment, DOMParser, document.write, setHTML, setHTMLUnsafe, parseHTMLUnsafe or template element outside the judged sites; the two judged sites on the road before the adoption sit inside the fence pass and the third, a reached local's, writes onto a holder that enters no document; the whole file's count for file-view.ts is pinned in the one assertion the plan's paragraph reads", () => {
  const mdCode = codeOnly(VIEW.split("function mdBlock(text: string, doc?: MdDocLoc): HTMLElement {")[1].split("\n}\n")[0]);
  const adopt = "box.replaceChildren(...Array.from(clean.childNodes));";
  const adoptAt = mdCode.indexOf(adopt);
  assert.ok(adoptAt > 0, "the adoption line");
  const after = mdCode.slice(adoptAt + adopt.length), before = mdCode.slice(0, adoptAt);
  // the region: no verb after the adoption; the one site before it is the highlight's escaped text, inside the fence pass
  assert.deepEqual(after.split("\n").filter((l) => RE_PARSE.test(l)), [], "no re-parsing or re-serializing write after the adoption line in mdBlock");
  assert.deepEqual(before.split("\n").filter((l) => RE_PARSE.test(l)).map((l) => l.trim()), ["codeEl.innerHTML = hljs.highlight(raw, { language: lang }).value;"],
    "the one such write in mdBlock is the highlight's, before the adoption (hljs escapes the text: it creates spans and nothing that fetches)");
  assert.ok(before.indexOf('clean.querySelectorAll("pre code")') < before.indexOf("codeEl.innerHTML = hljs.highlight"), "inside the fence pass over `clean`");
  // the whole file: the count below is the figure's one home (the plan's re-parse paragraph and tools/markdown-viewer-plan-gate-adopt.test.mjs
  // read it from this assertion's literal); the highlight's is the one site inside mdBlock, the others the viewer's own constant
  // markup outside it (the tray's icon constants, the loading glyph, codeBlock's numbered rows, and two judged at the merge of
  // the trail and figure-control branch, 2026-09-20: the bar's Back and Forward arrows, written at the bar's build outside the box like
  // the other icon buttons, and the figure control's glyph, parsed once onto a holder that enters no document and cloned into
  // each control, since the control itself stands under the box during the render and a live write there is what the node
  // scene refuses; the control had written its glyph through innerHTML, two live re-parses under the box in that scene, red at
  // the merge)
  const whole = codeOnly(VIEW).split("\n").filter((l) => RE_PARSE.test(l));
  assert.equal(whole.length, 14, "the whole file's count of re-parse sites in comment-stripped file-view.ts (a new one is judged here and in the plan's paragraph before this number moves)");
  assert.equal(whole.filter((l) => l.trim() === "codeEl.innerHTML = hljs.highlight(raw, { language: lang }).value;").length, 1, "the highlight's write among them, the one inside mdBlock, so all but one sit outside it");
  assert.equal(whole.filter((l) => /holder\.innerHTML = ICON_EXPAND/.test(l)).length, 1, "the figure control's glyph is parsed onto its holder, never onto the control (the control is placed under the box)");
  // the callees of the post-adoption region: every identifier called there that is not a method, resolved through the imports
  const called = [...new Set([...after.matchAll(/(?<![.\w])([A-Za-z_]\w*)\(/g)].map((m) => m[1]))].filter((n) => !["if", "for", "while", "return", "switch", "catch"].includes(n));
  assert.deepEqual(called, ["keepVideoShape", "linkHref", "resolveDocRelative", "linkMarkdownAnchors", "addFigureControls", "linkifyFileText"], "the passes after the adoption call these and nothing else (a new call widens this list first)");
  // a pass written as a method call on an imported binding (`ns.pass(box)`, `hljs.highlight(...)`) is no bare call, so the list
  // above would not see it: every binding file-view.ts imports, under any form and from any source (the compiler's tree, so a
  // require-bound one, gclock, and a clause wrapped over lines are in the set; the file review's landing round, extra7-1), is
  // asserted absent as the object of a method call in the region and in every reached local (the fork PR review's round-2
  // verification named this blind spot, 2026-09-20)
  /** Every binding a module imports, by the compiler's tree: a default, a namespace, a named one (as renamed), an
   *  `import x = require()`, and a variable bound to require() or to await import() (destructured or not), under any quote and
   *  across any line break. */
  const bindingsOf = (src: string, file: string): Set<string> => {
    const sf = ts.createSourceFile(file, src, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);
    const names = new Set<string>();
    const isLoader = (e: ts.Expression): boolean => ts.isCallExpression(e) && ((ts.isIdentifier(e.expression) && e.expression.text === "require") || e.expression.kind === ts.SyntaxKind.ImportKeyword);
    const bindName = (nm: ts.BindingName): void => { if (ts.isIdentifier(nm)) names.add(nm.text); else for (const el of nm.elements) if (ts.isBindingElement(el)) bindName(el.name); };
    const walk = (n: ts.Node): void => {
      if (ts.isImportDeclaration(n) && n.importClause) { const c = n.importClause; if (c.name) names.add(c.name.text); if (c.namedBindings) { if (ts.isNamespaceImport(c.namedBindings)) names.add(c.namedBindings.name.text); else for (const el of c.namedBindings.elements) names.add(el.name.text); } }
      else if (ts.isImportEqualsDeclaration(n)) names.add(n.name.text);
      else if (ts.isVariableDeclaration(n) && n.initializer) { const init = ts.isAwaitExpression(n.initializer) ? n.initializer.expression : n.initializer; if (isLoader(init)) bindName(n.name); }
      ts.forEachChild(n, walk);
    };
    walk(sf);
    return names;
  };
  const bindings = bindingsOf(VIEW, "file-view.ts");
  assert.ok(bindings.has("hljs") && bindings.has("linkifyFileText") && bindings.has("marked") && bindings.has("gclock"), "the reader sees the default, the named, the singleton and the require-bound imports (gclock: `const gclock = require(\"./gesture-clock.js\")`)");
  // the binding reader, pinned by execution over a synthetic module holding each binding form: a default, a namespace, a named
  // and a renamed one, a default beside a namespace under single quotes, a clause wrapped over lines, a namespace wrapped over
  // lines, an import-equals, a require-bound name, a destructured require and an awaited import()
  const bindingForms = 'import a from "./a";\nimport * as b from "./b";\nimport { c, d as e } from "./c";\nimport f, * as g from \'./f\';\nimport {\n  h,\n} from "./h";\nimport * as\n  i from "./i";\nimport j = require("./j");\nconst k = require("./k");\nconst { l } = require("./l");\nconst m = await import("./m");\n';
  assert.deepEqual([...bindingsOf(bindingForms, "x.ts")].sort(), ["a", "b", "c", "e", "f", "g", "h", "i", "j", "k", "l", "m"], "the binding reader sees every binding form, under any quote and across a line break (a form it missed would leave a method call on that binding unguarded)");
  /** The imported bindings `text` calls a method on (`ns.pass(box)`): the shape the bare-call list above cannot see. */
  const methodCallsIn = (text: string): string[] => [...bindings].filter((b) => new RegExp("\\b" + b + "\\.\\w+\\(").test(text)).sort();
  assert.deepEqual(methodCallsIn("gclock.learnAll(box); hljs.highlight(raw, { language: lang }); linkifyFileText(box);"), ["gclock", "hljs"], "the guard, driven: a method call on the require-bound binding and on the default import is seen, a bare call is not (the file review's landing round, extra7-1: `gclock.learnAll(box)` planted after the adoption had left this test green, gclock being outside the binding set)");
  for (const b of bindings) assert.doesNotMatch(after, new RegExp("\\b" + b + "\\.\\w+\\("), "no method call on the imported binding `" + b + "` after the adoption: a pass in that form would hide from the callee list above");
  /** file-view.ts's named imports from `./`: the binding to the module, for resolving a bare call (the compiler's tree, so any
   *  quote and any line break; a type-only clause included, as the reader before it took `import type {`). */
  const importsOf = (src: string): Record<string, string> => {
    const map: Record<string, string> = {};
    const sf = ts.createSourceFile("file-view.ts", src, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);
    for (const st of sf.statements) {
      if (!ts.isImportDeclaration(st) || !st.importClause?.namedBindings || !ts.isNamedImports(st.importClause.namedBindings)) continue;
      if (!ts.isStringLiteral(st.moduleSpecifier) || !st.moduleSpecifier.text.startsWith("./")) continue;
      const rel = st.moduleSpecifier.text.slice(2);
      for (const el of st.importClause.namedBindings.elements) map[el.name.text] = /\.[cm]?[jt]s$/.test(rel) ? rel : rel + ".ts";
    }
    return map;
  };
  /** Every module `src` (at `from`, a path relative to ui/webview) names in an import the compiler parses: an import declaration
   *  under any clause (named, type-only, namespace, default, default beside a namespace or a clause, side-effect), an export
   *  with a module specifier, an `import x = require()`, and a require() or import() whose argument is a string literal, under
   *  any quote and across any line break; each as a path relative to ui/webview (`x` to `x.ts`, a suffix kept as written), the
   *  npm packages apart. A specifier that is not a string literal (a template, with or without a substitution, a variable, an
   *  expression) REFUSES with the file, the form and the line, on the safe side: a module the walk cannot name is a module it
   *  cannot judge (the file review's landing round, tests-1, extra5-1, extra7-1, extra7-2). */
  const importTargets = (src: string, from: string): { local: string[]; packages: string[] } => {
    const local = new Set<string>(), packages = new Set<string>();
    const sf = ts.createSourceFile(from, src, ts.ScriptTarget.Latest, true, from.endsWith(".js") ? ts.ScriptKind.JS : ts.ScriptKind.TS);
    const lineOf = (n: ts.Node): number => sf.getLineAndCharacterOfPosition(n.getStart(sf)).line + 1;
    const take = (spec: ts.Node | undefined, form: string, holder: ts.Node): void => {
      if (!spec || !ts.isStringLiteral(spec)) throw new Error(from + ":" + lineOf(holder) + ": " + form + " whose specifier is not a string literal (refused, on the safe side): " + holder.getText(sf).split("\n")[0].slice(0, 100));
      if (!spec.text.startsWith(".")) { packages.add(spec.text); return; }
      const rel = path.posix.normalize(path.posix.join(path.posix.dirname(from), spec.text));
      local.add(/\.[cm]?[jt]s$/.test(rel) ? rel : rel + ".ts");
    };
    const walk = (n: ts.Node): void => {
      if (ts.isImportDeclaration(n)) take(n.moduleSpecifier, "import", n);
      else if (ts.isExportDeclaration(n)) { if (n.moduleSpecifier) take(n.moduleSpecifier, "export from", n); }
      else if (ts.isImportEqualsDeclaration(n)) { if (ts.isExternalModuleReference(n.moduleReference)) take(n.moduleReference.expression, "import = require", n); }
      else if (ts.isCallExpression(n)) { const c = n.expression; const isReq = ts.isIdentifier(c) && c.text === "require"; if (isReq || c.kind === ts.SyntaxKind.ImportKeyword) take(n.arguments[0], isReq ? "require()" : "import()", n); }
      ts.forEachChild(n, walk);
    };
    walk(sf);
    return { local: [...local].sort(), packages: [...packages].sort() };
  };
  // the forms the resolver follows, pinned by execution over synthetic modules holding each one (the walk before the file
  // review's landing round followed the named form alone and asserted the namespace and default forms absent; preview.ts's
  // namespace import of pinch.ts is followed now); the spellings the regex resolver once dropped are followed here by
  // execution, each with a specifier of its own so the expected list grows with them (both refuters of tests-1: same-named
  // twins resolve to the same module and pass unpatched), and a non-literal specifier is asserted to refuse with its line
  const forms = 'import { a } from "./a";\nimport type { B } from "./b";\nimport * as c from "./c";\nimport d from "./d";\nimport e, { e2 } from "./e";\nexport { f } from "./f";\nexport * from "./g";\nimport "./h";\nconst i = await import("./i");\nconst j = require("./j");\nimport k from "../k/k.js";\nimport { l } from "pkg-l";\nimport m from "pkg-m/sub";\n';
  assert.deepEqual(importTargets(forms, "x.ts"), { local: ["../k/k.js", "a.ts", "b.ts", "c.ts", "d.ts", "e.ts", "f.ts", "g.ts", "h.ts", "i.ts", "j.ts"], packages: ["pkg-l", "pkg-m/sub"] }, "the resolver follows every import form and keeps the packages apart");
  // the spellings the regex resolver dropped silently (the file review's landing round): a single-quoted named import, a
  // single-quoted side-effect import, a single-quoted require, a single-quoted `export *`, a default beside a namespace, an
  // import after another statement on its line, a clause wrapped over lines, a namespace wrapped over lines, an import-equals,
  // a type-only re-export and a namespace re-export
  const more = "import { a } from './a';\nimport './b';\nconst c = require('./c');\nexport * from './d';\nimport e, * as f from \"./e\";\nexport {}; import { g } from \"./g\";\nimport {\n  h,\n} from \"./h\";\nimport * as\n  i from \"./i\";\nimport j = require(\"./j\");\nexport type { K } from './k';\nexport * as l from \"./l\";\n";
  assert.deepEqual(importTargets(more, "x.ts"), { local: ["a.ts", "b.ts", "c.ts", "d.ts", "e.ts", "g.ts", "h.ts", "i.ts", "j.ts", "k.ts", "l.ts"], packages: [] }, "the spellings the regex resolver once dropped are followed: single quotes, default beside a namespace, an import after another statement on its line, a clause or a namespace wrapped over lines, an import-equals, a type-only and a namespace re-export");
  // and a specifier that is not a string literal is refused with the file, the form and the line, never dropped: a template
  // with and without a substitution, a variable and an expression, under import() and under require()
  for (const [bad, form] of [["export function f() { return import(`./x`); }", "import()"], ["const s = './x'; export function f() { return import(s); }", "import()"], ["const q = import('./' + name);", "import()"], ["const p = require(`./x`);", "require()"], ["const p = require(`./${name}`);", "require()"], ["const p = require(spec);", "require()"]] as const) {
    assert.throws(() => importTargets(bad, "x.ts"), new RegExp("^Error: x\\.ts:1: " + form.replace(/[()]/g, "\\$&") + " whose specifier is not a string literal \\(refused, on the safe side\\): "), "a non-literal specifier is refused with its line, never dropped: " + bad);
  }
  const source = (m: string): string => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", m), "utf8");
  const viewImports = importsOf(VIEW);
  const localFns = new Set([...codeOnly(VIEW).matchAll(/^(?:export )?function (\w+)\(/gm)].map((m) => m[1]));
  const modules = new Set<string>(); const locals: string[] = [];
  for (const c of called) { if (viewImports[c]) modules.add(viewImports[c]); else if (localFns.has(c)) locals.push(c); else assert.fail("a callee neither imported nor local: " + c); }
  assert.deepEqual(locals, ["keepVideoShape", "addFigureControls"], "two local callees: the video's shape and the figure controls (the trail and figure-control branch's pass, judged at its merge, 2026-09-20)");
  // a local callee's own bare calls are followed too, transitively: to other local functions (so a write two levels down is read:
  // the figure control's decision sat one call below addFigureControls and wrote its glyph through innerHTML onto a button placed
  // under the box; the node scene caught it at the merge, and this walk reads it now), to imported functions (whose modules join
  // the set: the file review's landing round, fresh-1 with fresh-2) and to the language's globals (pinned, so a new one is judged)
  const localBody = (l: string): string => codeOnly(VIEW.split("function " + l + "(")[1].split("\n}\n")[0]);
  const reached = [...locals]; const importedCallees: Record<string, string> = {}; const globals = new Set<string>();
  for (let i = 0; i < reached.length; i++) {
    const body = localBody(reached[i]);
    // a name the body binds itself (an inner arrow, a nested function, a variable) is read with the body it stands in;
    // removeFigureControl's `take` is a handler read from the keyboardTakers register, which the viewer's open fills with its
    // own takeKeyboard (file-view.ts, judged by its whole-file count above)
    const inner = new Set([...body.matchAll(/\b(?:const|let|var|function)\s+(\w+)/g)].map((m) => m[1]));
    for (const m of body.matchAll(/(?<![.\w])([A-Za-z_]\w*)\(/g)) {
    const n = m[1];
    if (["if", "for", "while", "return", "switch", "catch"].includes(n) || inner.has(n)) continue;
    if (localFns.has(n)) { if (!reached.includes(n)) reached.push(n); }
    else if (viewImports[n]) importedCallees[n] = viewImports[n];
    else if (bindings.has(n)) assert.fail("a reached local calls the imported binding `" + n + "`, not from `./`: " + reached[i]);
    else globals.add(n);
    }
  }
  assert.deepEqual(reached, REACHED_LOCALS, "the local functions a post-adoption pass reaches, transitively over bare calls (a new one widens this list first)");
  assert.deepEqual(importedCallees, IMPORTED_CALLEES, "the imported functions a reached local calls, each to its module (a new one widens the module set first)");
  assert.deepEqual([...globals].sort(), [...GLOBAL_CALLS].sort(), "the globals a reached local calls (a new one is judged here first)");
  for (const l of reached) for (const b of bindings) assert.doesNotMatch(localBody(l), new RegExp("\\b" + b + "\\.\\w+\\("), "no method call on the imported binding `" + b + "` in the reached local " + l + ": a pass in that form would hide from the walk");
  const GLYPH_HOLDER = 'if (!figureGlyph) { const holder = el("span"); holder.innerHTML = ICON_EXPAND; figureGlyph = holder.firstElementChild ?? null; }';
  assert.deepEqual(reached.flatMap((l) => localBody(l).split("\n").filter((x) => RE_PARSE.test(x)).map((x) => l + ": " + x.trim())), ["figureControlGlyph: " + GLYPH_HOLDER], "the one re-parse a reached local holds is the glyph's holder (figureControlGlyph), judged: parsed once, cloned into each control");
  const glyphBody = localBody("figureControlGlyph");
  assert.equal(glyphBody.split("\n").filter((x) => /\bholder\b/.test(x)).length, 1, "the holder lives on that one line: it is inserted nowhere, so it enters no document");
  assert.match(glyphBody, /return figureGlyph \? figureGlyph\.cloneNode\(true\) : null;/, "and the control takes a clone");
  // the module closure: the region's imported callees' modules and the reached locals' imported callees' modules, then every
  // module those name, transitively, under every import form; the packages kept apart and pinned
  for (const m of Object.values(importedCallees)) modules.add(m);
  const packages = new Set<string>();
  const queue = [...modules];
  while (queue.length) { const m = queue.shift() as string; const t = importTargets(source(m), m); for (const p of t.packages) packages.add(p); for (const dep of t.local) if (!modules.has(dep)) { modules.add(dep); queue.push(dep); } }
  assert.deepEqual([...modules].sort(), REACHED_MODULES, "the modules a post-adoption pass reaches, transitively over every import form (a new import widens this list first)");
  assert.ok(modules.has("file-view.ts"), "file-view.ts itself re-enters the set (file-comments.ts's type import of the viewer's action type), and is judged by its whole-file count above, not in the loop below");
  assert.deepEqual([...packages].sort(), PACKAGE_IMPORTS, "the npm packages the reached modules import, which the walk does not read (the header says why; a new one is judged here first)");
  // every reached module other than file-view.ts holds exactly the sites judged for it, in order, or none
  for (const m of modules) {
    if (m === "file-view.ts") continue;
    const found = codeOnly(source(m), m.endsWith(".js") ? "js" : "ts").split("\n").filter((l) => RE_PARSE.test(l)).map((l) => l.trim());
    const judged = JUDGED_SITES[m] ?? [];
    assert.deepEqual(found, judged.map(([line]) => line), m + ": every re-parsing or re-serializing site in a module a post-adoption pass reaches is judged in JUDGED_SITES with its reason, and none is missing" + (judged.length ? " (judged: " + judged.map(([, why]) => why).join("; ") + ")" : ""));
  }
  for (const m of Object.keys(JUDGED_SITES)) assert.ok(modules.has(m), m + " is judged in JUDGED_SITES but the walk no longer reaches it: retire the entry");
  // the two sums the plan's re-parse paragraph states (its tools pin reads them from these two literals): the matching lines
  // across the reached set, file-view.ts's included, and the modules holding one
  assert.equal(whole.length + Object.values(JUDGED_SITES).flat().length, 26, "the matching lines across every module the walk reaches, file-view.ts's among them");
  assert.equal(Object.keys(JUDGED_SITES).length + 1, 7, "the modules holding a matching line, file-view.ts among them");
  // the judgements that rest on a claim about the code, pinned: anchor-map.ts's decoder is a textarea inserted nowhere (every line
  // naming it is the decoder's own), and code-block.ts's wrapCodeLines is called by the fence pass before the chain, never after
  const decoderLines = codeOnly(source("anchor-map.ts")).split("\n").filter((l) => /\brefDecoder\b/.test(l));
  assert.equal(decoderLines.length, 7, "anchor-map.ts names refDecoder on its declaration, the probe's four lines and the decoder's two, and nowhere else");
  assert.ok(decoderLines.every((l) => !/append|insertBefore|replaceChild|prepend|after\(|before\(/.test(l)), "and no line inserts it anywhere: the textarea enters no document");
  assert.equal(after.includes("wrapCodeLines("), false, "nothing after the adoption calls wrapCodeLines");
});

// ── editing over pending changes (plans/file-review.md Slice 5) ────────────────────────────────────
// The panel registers its half through setTrackedEdit; the viewer mounts the editor with the status's records and the
// colour map, answers text() from the buffer, counts an in-editor decision as a change worth saving, and sends Save
// through the panel's `save` verb — fenced on the sidecar the records came from AND the file the editor loaded — with
// the buffer surviving every refusal. An untracked file's save is saveFile, unchanged.

test("Edit over pending changes: the mount carries the status's records and the colour map; text() and editing() follow the buffer; an in-editor accept alone makes Save write, through the panel", async (t) => {
  const o = await open(REPORT, t);
  const { ctx, wrap, b } = o;
  await answerStatus(status([hunk("h1")]));
  // the panel open: its colour map loads (GET /sessions) so the marks can wear the author's session colour
  const comments = wrap.querySelector(".fileview-fc button")!;
  comments.click();
  await answerStatus(status([hunk("h1")]));
  const statusAsks = posted.filter((m) => m.type === "fileComments" && m.verb === "status").length;
  assert.equal(b.edit.title, "Edit this file in place", "a pending change no longer blocks Edit");
  await enterEdit(o);
  assert.ok(ed.trackOpts, "the mount got the track option");
  assert.deepEqual(ed.trackOpts!.suggestions, [record("h1")], "the sidecar's records as the status held them");
  assert.equal(ed.trackOpts!.authorColor("api"), "#123456", "the author label maps to the session's colour through the record's authorId");
  assert.equal(ed.trackOpts!.authorColor("web"), null, "an author no record carries: neutral");
  assert.equal(ctx.editing(), true);
  assert.equal(ctx.text(), DOC, "text() is the buffer, which starts as the file");
  typeInto(DOC + "x");
  assert.equal(ctx.text(), DOC + "x", "…and follows every keystroke");
  typeInto(DOC);
  // an accept changes no text: the text comparison alone would call the buffer clean and Save would just leave
  decideInEditor("accepted", "h1", "p95", "p99");
  const m = saveTracked(o, DOC);
  assert.deepEqual(m.args, { content: DOC, suggestions: [], accepted: [{ id: "h1", oldText: "p95", newText: "p99" }], rejected: [] },
    "the records as the editor holds them now (the accepted one gone) and the decisions taken in it");
  assert.deepEqual(m.fence, { storeMtimeNs: "1757145600000000002", configMtimeNs: "1757145600000000003", fileMtimeNs: MT },
    "fenced on the sidecar the records came from, the config, and the file the editor loaded");
  assert.equal(m.sid, SID); assert.equal(m.path, REPORT);
  const after = status([], { fileMtimeNs: "1757145600000000009", storeMtimeNs: "1757145600000000010" });
  await saveReply(m.reqId, after);
  assert.deepEqual(savedInfos, [{ mtimeNs: "1757145600000000009", logged: true }], "the reply is the viewer's saved event: onSaved fires as after saveFile");
  assert.equal(ctx.mtimeNs(), "1757145600000000009", "the save fence moves to the host's new file mtime");
  assert.equal(ctx.editing(), false); assert.equal(b.save.hidden, true); assert.equal(b.edit.hidden, false, "edit mode left");
  assert.equal(ctx.text(), DOC, "text() is the saved bytes again");
  assert.equal(ed.destroyed, 1);
  assert.equal(posted.filter((x) => x.type === "fileComments" && x.verb === "status").length, statusAsks,
    "no status re-ask after the save: the reply IS the panel's status");
  assert.equal(wrap.querySelector(".fileview-fc button")!.textContent, "Comments · 0", "…and the glance follows the reply (a sidecar, no changes left)");
});

test("a tracked file with nothing pending, or one with only a sidecar, still saves through the panel with no records; an untracked file saves through saveFile, byte for byte", async (t) => {
  const o = await open(REPORT, t);
  await answerStatus(status([]));                       // tracked, sidecar present, no changes
  await enterEdit(o);
  assert.equal(ed.trackOpts, null, "nothing pending: the editor mounts as for any file");
  const m = saveTracked(o, DOC + "\nMore.\n");
  assert.deepEqual(m.args, { content: DOC + "\nMore.\n", suggestions: [], accepted: [], rejected: [] });
  assert.deepEqual(m.fence, { storeMtimeNs: "1757145600000000002", configMtimeNs: "1757145600000000003", fileMtimeNs: MT }, "the latest status's fence when no records rode in");
  await saveReply(m.reqId, status([], { fileMtimeNs: "1757145600000000009" }));
  assert.equal(o.ctx.mtimeNs(), "1757145600000000009");
  // a sidecar with a comment and no tracking: still the panel's save (the host rewrites the fingerprint)
  const c = await open(REPORT, t);
  await answerStatus(status([], { trackedBy: null }));
  await enterEdit(c);
  const m2 = saveTracked(c, DOC + "\nMore.\nAgain.\n");
  assert.deepEqual(m2.fence, { storeMtimeNs: "1757145600000000002", configMtimeNs: "1757145600000000003", fileMtimeNs: MT });
  await saveReply(m2.reqId, status([], { trackedBy: null, fileMtimeNs: "1757145600000000011" }));
  assert.equal(c.ctx.mtimeNs(), "1757145600000000011");
  // no sidecar, not tracked: saveFile, the pinned frame
  const u = await open(APP, t);
  await answerStatus({ ...status([]), root: ROOT, storePath: null, trackedBy: null, store: null, storeMtimeNs: null });
  await enterEdit(u);
  const reqId = save(u, PY + "x = 1\n");
  assert.deepEqual(lastOf("saveFile"), { type: "saveFile", path: APP, sid: SID, content: PY + "x = 1\n", baseMtimeNs: MT, reqId });
  assert.equal(lastOf("fileComments", "save"), undefined, "no save verb for an untracked file");
});

test("a tracked file the session has not written yet (a folder entry covers it, no sidecar): Save goes through the panel fenced on an EMPTY store mtime — the host's must-not-exist — and the reply that creates no sidecar leaves the glance at tracked; a store-moved refusal re-fences on the sidecar that appeared when it holds no changes, and stands when it does", async (t) => {
  // routesSave() is true for trackedBy alone, so this is the one save whose store fence comes from a null storeMtimeNs.
  // The host's requireFence reads "" as "no sidecar may exist" and refuses store-moved ("disappeared from disk") for
  // any other string against an absent file — a stringified null would refuse every save of a tracked-but-unwritten
  // file, and the retry, re-fenced the same way, would refuse again. Mutating fenceOf to String(s.storeMtimeNs) passed
  // every suite before this test.
  const fresh: Partial<Status> = { trackedBy: { kind: "folder", entry: "docs/" }, store: null, storeMtimeNs: null };
  const o = await open(REPORT, t);
  await answerStatus(status([], fresh));
  assert.equal(o.wrap.querySelector(".fileview-fc button")!.textContent, "Comments · tracked", "the glance: tracked, nothing written yet");
  await enterEdit(o);
  assert.equal(ed.trackOpts, null, "no sidecar, nothing pending: a plain mount");
  const m = saveTracked(o, DOC + "\nMore.\n");
  assert.deepEqual(m.args, { content: DOC + "\nMore.\n", suggestions: [], accepted: [], rejected: [] }, "no records rode in, none come back");
  assert.deepEqual(m.fence, { storeMtimeNs: "", configMtimeNs: "1757145600000000003", fileMtimeNs: MT },
    "the absent sidecar is fenced as the empty string the host reads as must-not-exist — never \"null\"");
  // the host wrote the file and the log and created no sidecar: its reply is the status with store null again
  await saveReply(m.reqId, status([], { ...fresh, fileMtimeNs: "1757145600000000009" }));
  assert.deepEqual(savedInfos, [{ mtimeNs: "1757145600000000009", logged: true }], "saved and logged, as for any tracked file");
  assert.equal(o.ctx.mtimeNs(), "1757145600000000009");
  assert.equal(o.ctx.editing(), false); assert.equal(o.b.edit.hidden, false, "edit mode left");
  assert.equal(o.ctx.text(), DOC + "\nMore.\n", "text() is the saved bytes");
  assert.equal(o.wrap.querySelector(".fileview-fc button")!.textContent, "Comments · tracked", "still no sidecar: the glance did not move");
  // a sidecar appeared mid-edit (a session left a comment; no change): the refusal says so, the re-read holds no
  // records either, so the save goes again fenced on the sidecar as it stands now — no longer ""
  await enterEdit(o);
  const m2 = saveTracked(o, DOC + "\nMore.\nAgain.\n");
  assert.equal(m2.fence.storeMtimeNs, "", "the second edit fences from the latest status, which still has no sidecar");
  await saveRefused(m2.reqId, "store-moved", "the comments for ~/notes-api/docs/report.md appeared on disk since you opened the file — reload and retry");
  const commented = status([], { ...fresh, storeMtimeNs: "1757145600000000020", fileMtimeNs: "1757145600000000009",
    store: { v: 3, path: "docs/report.md", suggestions: [], comments: [{ id: "c-1", author: "api", authorId: SID, ts: T0, body: "Say which cache." }] } });
  await answerStatus(commented);
  const again = lastOf("fileComments", "save");
  assert.notEqual(again.reqId, m2.reqId, "a second save frame");
  assert.deepEqual(again.fence, { storeMtimeNs: "1757145600000000020", configMtimeNs: "1757145600000000003", fileMtimeNs: "1757145600000000009" },
    "re-fenced on the sidecar that appeared, and on the file as the editor loaded it");
  assert.deepEqual(again.args, m2.args, "the same text, still no records");
  assert.equal(o.b.save.disabled, true, "still saving");
  await saveReply(again.reqId, status([], { ...commented, fileMtimeNs: "1757145600000000021" }));
  assert.equal(o.ctx.mtimeNs(), "1757145600000000021");
  assert.equal(o.ctx.editing(), false);
  assert.equal(o.wrap.querySelector(".fileview-fc button")!.textContent, "Comments · 1", "the glance follows the reply: the sidecar with its one comment");
  // the sidecar that appeared carries a session's CHANGE: the editor never saw it, so no retry — the refusal stands, with Reload
  const c = await open(REPORT, t);
  await answerStatus(status([], fresh));
  await enterEdit(c);
  const m3 = saveTracked(c, DOC + "\nMore.\n");
  assert.equal(m3.fence.storeMtimeNs, "");
  await saveRefused(m3.reqId, "store-moved", "the comments for ~/notes-api/docs/report.md appeared on disk since you opened the file — reload and retry");
  await answerStatus(status([hunk("h1")], { trackedBy: { kind: "folder", entry: "docs/" }, storeMtimeNs: "1757145600000000030" }));
  assert.equal(lastOf("fileComments", "save").reqId, m3.reqId, "no retry: the sidecar holds a change the editor did not load");
  const bar = errBar(c.body)!;
  assert.ok(bar, "the refusal is the note bar over the editor");
  assert.match(bar.childNodes[0].textContent, /appeared on disk since you opened the file/);
  assert.equal(bar.querySelector("button")!.textContent, "Reload file", "a moved sidecar offers Reload");
  assert.equal(ed.destroyed, 0, "the buffer survives"); assert.equal(ed.buf, DOC + "\nMore.\n");
  assert.equal(c.b.save.disabled, false); assert.equal(c.b.save.textContent, "Save", "re-armed");
});

test("a store-moved refusal: the panel re-reads status and retries once when the sidecar's records are still the ones the editor carries; when they changed, the refusal reaches the bar with Reload, and the buffer survives; Reload asks, then re-opens", async (t) => {
  const o = await open(REPORT, t);
  const { body, b } = o;
  await answerStatus(status([hunk("h1")]));
  await enterEdit(o);
  const v2 = DOC.replace("40%", "45%");
  const m = saveTracked(o, v2);
  await saveRefused(m.reqId, "store-moved", "the comments for ~/notes-api/docs/report.md changed on disk since you opened the file — reload and retry");
  // a reply a session wrote moved the sidecar; its records are unchanged: the save goes again with the new fence
  await answerStatus(status([hunk("h1")], { storeMtimeNs: "1757145600000000020" }));
  const again = lastOf("fileComments", "save");
  assert.notEqual(again.reqId, m.reqId, "a second save frame");
  assert.deepEqual(again.fence, { storeMtimeNs: "1757145600000000020", configMtimeNs: "1757145600000000003", fileMtimeNs: MT }, "re-fenced on the sidecar as it stands now, the file as loaded");
  assert.deepEqual(again.args, m.args, "the same text and records");
  assert.equal(b.save.disabled, true, "still saving");
  // refused again, and this time a session's change is new in the sidecar: the refusal stands, in the host's words
  await saveRefused(again.reqId, "store-moved", "the comments for ~/notes-api/docs/report.md changed on disk since you opened the file — reload and retry");
  await answerStatus(status([hunk("h1"), hunk("h2")], { storeMtimeNs: "1757145600000000030" }));
  assert.equal(lastOf("fileComments", "save").reqId, again.reqId, "no third attempt: the records changed under the editor");
  const bar = errBar(body)!;
  assert.ok(bar, "the refusal is the note bar over the editor");
  assert.equal(bar.childNodes[0].textContent, "the comments for ~/notes-api/docs/report.md changed on disk since you opened the file — reload and retry");
  const reload = bar.querySelector("button")!;
  assert.equal(reload.textContent, "Reload file", "a moved fence offers Reload");
  assert.equal(b.save.hidden, false); assert.equal(b.save.disabled, false); assert.equal(b.save.textContent, "Save", "re-armed");
  assert.equal(ed.destroyed, 0, "the buffer survives");
  assert.equal(ed.buf, v2);
  assert.equal(body.childNodes[0], body.querySelector(".fileview-cm"), "the editor host is still the body, under the bar"); assert.ok(aboveRow(body), "the bar above the row");
  // Reload: asks (dirty), then re-opens the same file fresh — the buffer goes only on that click
  let asked = 0;
  win.confirm = () => { asked++; return false; };
  reload.click();
  await settle();
  assert.equal(asked, 1, "the discard question");
  assert.equal(ed.destroyed, 0, "declined: the buffer stays");
  const asks = posted.filter((x) => x.type === "fileComments" && x.verb === "status").length;
  win.confirm = () => { asked++; return true; };
  reload.click();
  await settle();
  assert.equal(asked, 2);
  const fresh = doc.getElementById("romp-fileview")!;
  assert.ok(fresh && fresh !== o.wrap, "accepted: a fresh viewer replaced the old one, buffer and all");
  assert.equal(fresh.querySelector(".fileview-cm"), null, "…reading, not editing");
  assert.ok(fresh.querySelector("code.hljs"), "the file as it is on disk");
  assert.equal(posted.filter((x) => x.type === "fileComments" && x.verb === "status").length, asks + 1, "the fresh panel probes status");
  win.confirm = () => true;
});

test("desync and file-moved: the reason shows, the buffer stays; file-moved offers Reload (the editor's text is from the old bytes), desync does not; editing-off re-offers the consent and retries", async (t) => {
  const o = await open(REPORT, t);
  const { body, b } = o;
  await answerStatus(status([hunk("h1")]));
  await enterEdit(o);
  const m = saveTracked(o, DOC + "z");
  await saveRefused(m.reqId, "desync", "change h1 does not fit the text being saved to ~/notes-api/docs/report.md: the text at 42..45 is not the change's text; nothing was changed — reload and retry");
  let bar = errBar(body)!;
  assert.match(bar.childNodes[0].textContent, /^change h1 does not fit/);
  assert.equal(bar.querySelector("button"), null, "no Reload on a desync: nothing on disk moved");
  assert.equal(ed.destroyed, 0); assert.equal(b.save.disabled, false);
  assert.equal(lastOf("fileComments", "status").reqId < m.reqId, true, "no status re-read for a desync");
  const m2 = saveTracked(o, DOC + "zz");
  await saveRefused(m2.reqId, "file-moved", "the file ~/notes-api/docs/report.md changed on disk since you opened the file — reload and retry");
  bar = errBar(body)!;
  assert.match(bar.childNodes[0].textContent, /^the file .* changed on disk/);
  assert.equal(bar.querySelector("button")!.textContent, "Reload file");
  assert.equal(ed.destroyed, 0, "the buffer stays");
  assert.equal(lastOf("fileComments", "save").reqId, m2.reqId, "a moved FILE is never retried");
  // editing-off: the consent is re-offered (the confirm), and a yes retries the save
  const m3 = saveTracked(o, DOC + "zzz");
  const confirms: string[] = [];
  win.confirm = (text: string) => { confirms.push(text); return true; };
  await saveRefused(m3.reqId, "editing-off", "cannot write the comments for ~/notes-api/docs/report.md: dashboard file editing is off on this machine — the viewer's Edit button asks to turn it on");
  assert.equal(confirms.length, 1); assert.match(confirms[0], /^Editing is off on/);
  assert.ok(lastOf("setFileEditing"), "the opt-in is re-posted");
  const m4 = lastOf("fileComments", "save");
  assert.notEqual(m4.reqId, m3.reqId, "…and the save retried");
  assert.equal(m4.args.content, DOC + "zzz");
  win.confirm = () => true;
});

test("an older editor bundle (a mount that ignores `track`): Edit refuses with the Slice 2 wording once the chunk answers, opens no editor, and refuses at the click from then on; with nothing pending the same bundle edits as before", async (t) => {
  const o = await open(REPORT, t);
  const { body, b } = o;
  await answerStatus(status([hunk("h1"), hunk("h2")]));
  ed.tracks = false;
  b.edit.click();
  await settle();
  const bar = errBar(body);
  assert.ok(bar, "the refusal is in the viewer's notice bar");
  assert.equal(bar!.textContent, "2 changes are pending in this file, so Edit is off here: a direct edit would move them. Accept or reject the 2 changes first; the session's own track-edit still works.");
  assert.equal(b.save.hidden, true, "no edit mode");
  assert.equal(ed.mounted, 1); assert.equal(ed.destroyed, 1, "the untracked editor the bundle built was torn down at once");
  assert.ok(body.querySelector("code.hljs"), "the read view is back");
  const reads = fetches.length;
  b.edit.click();
  await settle();
  assert.equal(ed.mounted, 1, "the next click refuses before the chunk: the bundle proved itself");
  assert.equal(fetches.length, reads, "not even the consent read");
  assert.equal(errBar(body)!.textContent, bar!.textContent);
  // the changes decided elsewhere: nothing pending, and the old bundle edits as it always did (the panel open re-asks status)
  o.wrap.querySelector(".fileview-fc button")!.click();
  await answerStatus(status([]));
  await enterEdit(o);
  assert.equal(ed.mounted, 2);
});

test("the chunk failing to load over pending changes: no fallback textarea (it cannot carry the changes) — the load error and the Slice 2 wording, read view kept; CRLF endings refuse at the click", async (t) => {
  const o = await open(REPORT, t);
  const { body, b } = o;
  await answerStatus(status([hunk("h1")]));
  const chunk = win.__rompEditor;
  delete win.__rompEditor;                               // no global and no bundle script tag: the load rejects
  try {
    b.edit.click();
    await settle();
    const bar = errBar(body)!;
    assert.match(bar.textContent, /^no bundle script tag to derive the editor chunk URL from — 1 change is pending in this file, so Edit is off here/);
    assert.equal(body.querySelector("textarea"), null, "no plain editor over pending changes");
    assert.equal(b.save.hidden, true);
    assert.ok(body.querySelector("code.hljs"));
  } finally { win.__rompEditor = chunk; }
  // CRLF: the editor normalizes line endings, which moves every offset the records hold — refused before the chunk loads
  disk[REPORT] = { bytes: DOC.replace(/\n/g, "\r\n"), type: "text/plain; charset=utf-8", mtimeNs: MT };
  o.ctx.reload();
  await settle();
  await answerStatus(status([hunk("h1")]));
  const mounted = ed.mounted;
  b.edit.click();
  await settle();
  assert.equal(ed.mounted, mounted, "no mount");
  assert.match(errBar(body)!.textContent, /^The editor rewrites this file's CR or CRLF line endings as it loads the text, and that would move the pending changes\. 1 change is pending/,
    "the consequence stated literally, as docs/guide.md states it: this is copy the person acts on (the sentence names CR and CRLF since Slice 7 of plans/markdown-viewer.md, item 7)");
  assert.ok(errBar(body)!.textContent.startsWith(o.fv.CR_REFUSAL + " 1 change is pending"), "the exported constant (contract C5), a space, then the panel's own refusal");
  assert.doesNotMatch(errBar(body)!.textContent, /\bride/, "no metaphor in the refusal");
  assert.equal(b.save.hidden, true);
});

test("source: the Slice 5 seam — text() answers the buffer in edit mode, the mount spreads the track option only when something is pending, Save routes by routesSave(), and the saveFile frame is byte for byte the pinned one", () => {
  assert.match(VIEW, /text: \(\) => \(editing && bufValue\(\) !== null \? bufValue\(\) : viewText\(\)\),/);
  assert.match(VIEW, /editing: \(\) => editing,\n\s*setTrackedEdit: \(t\) => \{ trackedEdit = t; \},/);
  assert.match(VIEW, /\.\.\.\(pending \? \{ track: \{ suggestions: pending\.records, authorColor: pending\.authorColor, onDecisions: \(\) => \{ dirty = cm!\.value\(\) !== norm\(text!\) \|\| decided\(\); \} \} \} : \{\}\),/,
    "the option's shape is the chunk's TrackOpts, data only");
  assert.match(VIEW, /onChange: \(\) => \{ dirty = cm!\.value\(\) !== norm\(text!\); if \(!dirty\) dirty = decided\(\); \},/, "a keystroke that restores the text leaves the decisions dirty");
  assert.match(VIEW, /if \(pending && !cm\.track\) \{/, "an older bundle is detected by the handle it returns, not by a flag");
  assert.match(VIEW, /if \(trackedEdit && trackedEdit\.routesSave\(\)\) \{[\s\S]*?trackedEdit\.save\(content, records, decisions\)\.then\(/);
  assert.match(VIEW, /\n    post\(\{ type: "saveFile", path, sid: sid \|\| undefined, content, baseMtimeNs: mtimeNs, reqId: saveSeq \}\);\n  \};/, "the untracked path ends in the pinned frame");
  assert.doesNotMatch(VIEW, /@codemirror|track-decorations|editor-chunk"/, "the viewer imports nothing from the chunk: the option is data through the mount call");
});

test("the paint pass runs as one fileview:paint frame of the page's performance collector, the panel's re-place of its cards after the body's width changed as one fileview:reflow frame (the bracket is fireRenderedKeepingSelection's, which both reflow triggers run through), and the pane's minute row carries both with the pass cost; no collector, the pass runs untimed", async (t) => {
  // The Files pane gets no frames pushed to it; its collector (perf-telemetry.ts, published as window.__rompPerf by
  // federation) times nothing unless the viewer brackets its own work (file-view.ts perfTimed), which is what made a
  // 20 s divider drag over a large reviewed note invisible to `romp perf client` (2026-09-09). The collector here is
  // the real one on a fake clock, the ResizeObserver a stand-in the test reports through (the viewer's reflow is keyed
  // on the body's width report; with no requestAnimationFrame the report itself is the frame).
  const { createPerfTelemetry } = await import("./perf-telemetry");
  const clock = { t: 1000, wall: 1_700_000_000_000 };
  const posted: any[] = [];
  const perf = createPerfTelemetry("files", {
    now: () => clock.t, wallNow: () => clock.wall, post: (m) => posted.push(m), raf: null, caf: null, setInterval: null,
    observer: null, supportedEntryTypes: [], heapBytes: () => null, domCount: () => 42, visible: () => true, hiddenPane: () => false,
    ua: "chrome-desktop", pageUrl: "http://h:1/files", windowEvents: null, documentEvents: null,
    switches: () => ({ share: false, mute: false }), entries: () => null, marks: () => null, env: () => null,
  });
  const observers: Array<{ cb: (entries: any[]) => void; targets: any[] }> = [];
  (globalThis as any).ResizeObserver = class {
    private rec: { cb: (entries: any[]) => void; targets: any[] };
    constructor(cb: (entries: any[]) => void) { this.rec = { cb, targets: [] }; observers.push(this.rec); }
    observe(el: any): void { this.rec.targets.push(el); }
    disconnect(): void {}
  };
  t.after(() => { delete win.__rompPerf; delete (globalThis as any).ResizeObserver; });
  // no collector on the page: the open paints as before, nothing is timed
  const o0 = await open(REPORT, t);
  const paintsBefore = paints;
  assert.ok(paintsBefore >= 1, "the open painted");
  o0.fv.closeFileView(); await settle();
  // the collector on the page: every paint of the open is a fileview:paint bracket, at the pass's cost
  win.__rompPerf = perf;
  const o = await open(REPORT, t);   // open() zeroes the paint count
  const painted = paints;
  assert.ok(painted >= 1, "the open painted");
  let snap: any = perf.snapshot();
  assert.deepEqual(Object.keys(snap.frames), ["fileview:paint"], "the open's paint passes, and nothing else, were timed");
  assert.equal(snap.frames["fileview:paint"].n, painted, "one bracket per paint pass (the onRendered hooks ran inside it)");
  // the body's width changes (the divider released): the panel re-places its cards once per changed width, as fileview:reflow
  const wo = observers.find((r) => r.targets.includes(o.body));
  assert.ok(wo, "the viewer observes the body's width");
  const reportsBefore = paints;
  wo!.cb([{ contentRect: { width: 600 } }]);           // the first report is the size at observe(), not a change
  assert.equal(paints, reportsBefore, "no reflow on the first report");
  wo!.cb([{ contentRect: { width: 400 } }]);           // narrower: the re-paint
  assert.equal(paints, reportsBefore + 1, "one reflow");
  wo!.cb([{ contentRect: { width: 400 } }]);           // the same width again: nothing
  assert.equal(paints, reportsBefore + 1);
  snap = perf.snapshot();
  assert.deepEqual(Object.keys(snap.frames).sort(), ["fileview:paint", "fileview:reflow"]);
  assert.equal(snap.frames["fileview:reflow"].n, 1);
  assert.equal(snap.frames["fileview:paint"].n, painted, "a reflow is not a paint");
  // the minute row: app files, both types
  clock.wall += 60_000;
  perf.tick();
  const rows = posted.filter((m) => m.what === "minute");
  assert.equal(rows.length, 1);
  assert.equal(rows[0].data.app, "files");
  assert.deepEqual(Object.keys(rows[0].data.frames).sort(), ["fileview:paint", "fileview:reflow"]);
  assert.equal(rows[0].data.dom, 42);
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
  // the file's own Ev hides target and currentTarget the same way (hideEdges(this) at the end of its constructor)
  assertHiddenEvent(new Ev("click"), root, child);
});

// ── the keyboard (plans/markdown-viewer.md Slice 6, item 1) ────────────────────────────────────────
// openFileView's takeKeyboard: the body is a Tab stop (tabindex 0) and takes the keyboard after the open's first landing and
// after a paint the reader asked for from the viewer's own chrome (the Rendered/Raw toggle, a text-size step, the SVG
// Source toggle), and only when nothing, the document's body or a control in the viewer's bar held it at that moment; a
// reload's landing and the panel's setMode never call it. The stand-in's focus() sets doc.activeElement and counts
// (El.focused); its tabIndex reflects the attribute; a removed subtree that held the active element drops the keyboard to
// doc.body (dropFocusIn), the browser's focus fixup, so a toggle's repaint over a focused mark reads as it does in Chromium.
// The press-time reading (a press inside the body lands on the body, the nearest focusable ancestor, where it fell to the
// document's body before; the variant of path-links-pointer-focus.test.ts's pin the brief asked for) needs a browser's
// own focus rules and the in-file link pass's TreeWalker, which this stand-in lacks: file-view-focus-body-browser.test.ts
// reads it over the real viewer. Before item 1: no tabindex on the body and no focus call anywhere in the open (red at the
// first assertion of each case over a git archive of the base).
test("the body is a Tab stop and takes the keyboard at the open's first landing when the document's body, or nothing, held it; a reload's landing never focuses; the Rendered/Raw toggle's paint refocuses the body when its button held the keyboard; the panel's setMode takes nothing", async (t) => {
  doc.activeElement = doc.body;
  t.after(() => { doc.activeElement = null; });
  const { ctx, body, b } = await open(REPORT, t);
  assert.equal(body.getAttribute("tabindex"), "0", "the body carries tabindex 0 after the open");
  assert.equal(body.tabIndex, 0);
  assert.equal(doc.activeElement, body, "the first landing focused the body (the document's body held the keyboard)");
  assert.equal(body.focused, 1, "one focus call");
  const painted = paints;
  ctx.reload(); await settle();
  assert.equal(paints, painted + 1, "the reload landed and painted");
  assert.equal(body.focused, 1, "a reload's landing calls focus on nothing (the reader may be tabbed onto a mark or typing)");
  // the toggle: the pressed button holds the keyboard (a browser focuses a clicked button), and the paint hands it on
  doc.activeElement = b.raw;
  b.raw.click();
  assert.equal(doc.activeElement, body, "the Raw paint moved the keyboard from the toggle button to the body");
  assert.equal(body.focused, 2);
  doc.activeElement = null;
  b.rendered.click();
  assert.equal(doc.activeElement, body, "with nothing focused the Rendered paint takes it too");
  assert.equal(body.focused, 3);
  // the panel's own switch is not the reader's gesture
  doc.activeElement = doc.body;
  ctx.setMode("raw");
  assert.equal(ctx.mode(), "raw");
  assert.equal(doc.activeElement, doc.body, "setMode paints without taking the keyboard");
  assert.equal(body.focused, 3);
  // and Escape from the focused body closes, through the document's handler, as from the document's body
  doc.activeElement = body;
  const esc = new Ev("keydown", { key: "Escape" });
  body.dispatchEvent(esc);
  assert.equal(doc.getElementById("romp-fileview"), null, "Escape with the body focused closed the viewer");
  assert.equal(esc.defaultPrevented, true);
});

test("the keyboard stays where it is when something else holds it: a control outside the card at the first landing and at a toggle, the aside's box at a toggle, a mark under a text-size step from the wheel, the editor's textarea; a mark a toggle's repaint removes drops the keyboard to the document's body, and the body takes it, as in a browser", async (t) => {
  const outside = doc.body.appendChild(new El("button"));
  doc.activeElement = outside;
  t.after(() => { outside.remove(); doc.activeElement = null; store.delete("romp:fileviewTextSize"); });
  const o = await open(REPORT, t);
  const { ctx, body, b } = o;
  assert.equal(doc.activeElement, outside, "a control outside the card kept the keyboard through the first landing");
  assert.equal(body.focused, 0);
  b.raw.click();
  assert.equal(doc.activeElement, outside, "…and through a toggle's paint");
  assert.equal(body.focused, 0);
  // a box inside the aside (the Comments panel's composer, retargeted across a paint, never rebuilt): a toggle's paint leaves it
  const aside = new El("div"); const box = aside.appendChild(new El("textarea"));
  ctx.aside(aside as unknown as HTMLElement); await settle();
  doc.activeElement = box;
  b.rendered.click();
  assert.equal(doc.activeElement, box, "the aside's box kept the keyboard through the Rendered paint");
  assert.equal(body.focused, 0);
  // a mark (a comment's highlight: role button, a Tab stop, inside the body) under a text-size step from the wheel: the
  // step rebuilds nothing, so the mark stands and keeps the keyboard
  const md = body.querySelector(".fileview-md")!;
  const mark = md.appendChild(new El("mark")); mark.setAttribute("role", "button"); mark.tabIndex = 0;
  doc.activeElement = mark;
  const wheel = new Ev("wheel", { ctrlKey: true, deltaY: -100, deltaMode: 0 });
  body.dispatchEvent(wheel);
  assert.equal(wheel.defaultPrevented, true, "the wheel step was taken");
  assert.notEqual(o.wrap.querySelector(".fileview")!.dataset.fvText, "100", "…and stepped the size off the default");
  assert.equal(doc.activeElement, mark, "the mark kept the keyboard through the text-size step");
  assert.equal(body.focused, 0);
  // the same mark under a toggle's repaint: the paint removes it, the focus falls to the document's body, and the body takes it
  b.raw.click();
  assert.equal(mark.isConnected, false, "the Raw paint rebuilt the body: the mark is gone");
  assert.equal(doc.activeElement, body, "…so the body took the keyboard the mark could no longer hold");
  assert.equal(body.focused, 1);
  // the editor owns the body while it is up: its textarea keeps the keyboard, and a toggle's click paints nothing and takes nothing
  await enterEdit(o);
  const host = body.querySelector(".fileview-cm")!;
  const ta = host.appendChild(new El("textarea"));
  doc.activeElement = ta;
  b.rendered.click();
  assert.equal(doc.activeElement, ta, "the editor's textarea kept the keyboard");
  assert.equal(body.focused, 1);
});

test("a picture's first landing and a code file's take the keyboard the same way; a control in the viewer's own bar yields it (the button whose click caused the paint)", async (t) => {
  t.after(() => { doc.activeElement = null; });
  doc.activeElement = doc.body;
  const pic = await open(PLOT, t);
  assert.equal(doc.activeElement, pic.body, "the picture's landing focused the body");
  assert.equal(pic.body.focused, 1);
  pic.fv.closeFileView();
  doc.activeElement = null;
  const code = await open(APP, t);
  assert.equal(doc.activeElement, code.body, "the code file's landing focused the body");
  assert.equal(code.body.focused, 1);
  // a bar control holds it at a step: the A+ button pressed with the pointer (a browser focuses it; the click's detail is its
  // count), then the paint hands the keyboard to the body; a key on the focused button (Enter, Space: a click of detail 0)
  // keeps it there, so a keyboard user's next press steps again (file-view-text-size.test.ts pins the three Enters)
  const up = code.wrap.querySelectorAll(".fileview-acts button").find((x) => x.textContent === "A+")!;
  doc.activeElement = up;
  up.dispatchEvent(new Ev("click", { detail: 1 }));
  assert.equal(doc.activeElement, code.body, "the A+ step from a pointer's click handed the keyboard from the button to the body");
  assert.equal(code.body.focused, 2);
  doc.activeElement = up;
  up.dispatchEvent(new Ev("click", { detail: 0 }));
  assert.equal(code.wrap.querySelector(".fileview")!.dataset.fvText !== "100" && doc.activeElement === up, true, "the A+ step from a key on the button stepped and kept the keyboard on the button");
  assert.equal(code.body.focused, 2);
  store.delete("romp:fileviewTextSize");
});

// ── where an open lands (plans/markdown-viewer.md Slice 6, item 4) ──────────────────────────────────
// openFileView's `at` (one of At: a line, a source offset or a heading) replaces the `line` and `frag` options: a line
// takes the Raw view for that open and its row (spent at the first text landing, as before); a heading lands after the
// first Rendered paint through scrollToFragment and says so in the notice bar when the note has no such section; an offset
// (new) is spent at the first text landing and scrolled one frame later, the heading landing's timing: the block holding
// it in the Rendered view (the anchor map's block table paired to the painted elements), the row in Raw, both centred.
// The relay's default branch reads its `at` through readAt (the message crossed a frame boundary) and the body's delegate
// hands a path link's data-line and data-frag on as `{ line }` and `{ heading }`. The stand-in parses no innerHTML, so a
// case lays the elements marked or codeBlock would paint (layRendered, layRows) between the paint and the frame it
// flushes (withFrames: requestAnimationFrame as a queue, installed for the case; the file's other cases run with none, the
// paint pass's own frame reads then running bare). Before item 4: `at` was ignored (an open landed at the top with no
// notice), readAt did not exist, and the delegate handed a line and a fragment as two arguments (red over a git archive of
// the base with readAt stubbed).
const frames: Array<() => void> = [];
const withFrames = (t: TestContext): void => {
  (globalThis as any).requestAnimationFrame = (cb: () => void) => { frames.push(cb); return frames.length; };
  t.after(() => { delete (globalThis as any).requestAnimationFrame; frames.length = 0; });
};
const flushFrames = (): void => { const run = frames.splice(0); for (const cb of run) cb(); };
const mk = (tag: string, text: string, id?: string): El => { const e = new El(tag); if (id) e.id = id; e.appendChild(new Txt(text)); return e; };
/** The Rendered DOM marked paints for DOC, laid by hand: one element per block of the table (h1, h2, p, p), the heading ids
 *  the viewer mints (md- plus the slug). Returned in block order. */
const layRendered = (md: El): El[] => {
  const els = [mk("h1", "Report", "md-report"), mk("h2", "Findings", "md-findings"), mk("p", "The api session cut p95 latency by 40%."), mk("p", "We recommend shipping the cache in v1.2.")];
  md.replaceChildren(...els);
  return els;
};
/** The Raw rows codeBlock paints for `src`: one .fv-cl per logical line, under the code.hljs element, split as the viewer
 *  splits since Slice 7 of plans/markdown-viewer.md (item 7): a CRLF, a lone CR or an LF each end a row. */
const layRows = (code: El, src: string): El[] => {
  const lines = src.split(/\r\n|\r|\n/); if (lines[lines.length - 1] === "") lines.pop();
  const rows = lines.map((ln) => { const cl = new El("span"); cl.className = "fv-cl"; cl.appendChild(new Txt(ln)); return cl; });
  code.replaceChildren(...rows);
  return rows;
};
const scrolls = (els: El[]) => els.map((e) => e.scrolled);

test("readAt: the relay's `at` is a line (a positive integer), an offset (a non-negative integer) or a heading (a non-empty string), in that order when a message carries more than one; anything else is no target", async () => {
  const { readAt } = await mod();
  assert.deepEqual(readAt({ line: 12 }), { line: 12 });
  assert.deepEqual(readAt({ offset: 0 }), { offset: 0 });
  assert.deepEqual(readAt({ offset: 4096 }), { offset: 4096 });
  assert.deepEqual(readAt({ heading: "results" }), { heading: "results" });
  assert.deepEqual(readAt({ heading: "Evidence%20Results" }), { heading: "Evidence%20Results" }, "as written: the landing decodes");
  assert.deepEqual(readAt({ line: 3, heading: "x" }), { line: 3 }, "a line first, then an offset, then a heading");
  assert.deepEqual(readAt({ offset: 7, heading: "x" }), { offset: 7 });
  for (const bad of [null, undefined, "results", 12, [], {}, { line: "12" }, { line: 0 }, { line: -4 }, { line: 1.5 }, { line: NaN }, { offset: -1 }, { offset: 2.5 }, { offset: "0" }, { heading: "" }, { heading: 7 }, { frag: "results" }, { at: { line: 1 } }])
    assert.equal(readAt(bad), null, "no target: " + inspect(bad));
});

test("an open at a line: the markdown file takes its Raw view for that open (the preference unsaved, the Rendered toggle one click away) and a heading rides through the relay's default branch and the body's delegate as `at`", async (t) => {
  withFrames(t);
  const o = await open(REPORT, t, SID, { at: { line: 2 } });
  assert.equal(o.ctx.mode(), "raw", "the line's open shows the Raw view");
  assert.ok(o.body.querySelector("code.hljs") && !o.body.querySelector(".fileview-md"));
  assert.equal(store.has("romp:fileviewFmt"), false, "…without writing the preference");
  assert.equal(frames.length, 0, "a line lands with the paint, no frame queued (as `line` did)");
  o.b.rendered.click();
  assert.equal(o.ctx.mode(), "rendered", "the toggle returns to the Rendered view");
  // the relay's default branch: the shell's message carries `at`, read through readAt
  const { fv } = o;
  win.dispatchEvent(new MessageEvent("message", { data: { romp: "viewFile", path: REPORT, sid: SID, at: { heading: "findings" } } }));
  await settle();
  const wrap2 = doc.getElementById("romp-fileview")!;
  assert.notEqual(wrap2, o.wrap, "the relay replaced the viewer");
  assert.equal(seam!.mode(), "rendered");
  assert.equal(frames.length, 1, "the heading's landing waits for the frame after the first Rendered paint");
  const els = layRendered(wrap2.querySelector(".fileview-md")!);
  flushFrames();
  assert.deepEqual(scrolls(els), [0, 1, 0, 0], "the Findings heading was scrolled to, nothing else");
  assert.deepEqual(els[1].scrolledWith, { block: "start" }, "…to the top of the body, as a section link lands");
  assert.equal(errBar(wrap2.querySelector(".fileview-body")!), null, "no notice: the section exists");
  // a malformed `at` off the relay is no target: the file opens at its top in its own view, with no notice and no frame
  win.dispatchEvent(new MessageEvent("message", { data: { romp: "viewFile", path: REPORT, sid: SID, at: { line: "2" } } }));
  await settle();
  const wrap3 = doc.getElementById("romp-fileview")!;
  assert.notEqual(wrap3, wrap2);
  assert.equal(seam!.mode(), "rendered", "a string line is no line: the Rendered view, not Raw");
  assert.equal(frames.length, 0, "nothing to land");
  assert.equal(errBar(wrap3.querySelector(".fileview-body")!), null);
  win.dispatchEvent(new MessageEvent("message", { data: { romp: "viewFile", path: REPORT, sid: SID, at: { line: 2 } } }));
  await settle();
  assert.equal(seam!.mode(), "raw", "a well-formed line off the relay takes the Raw view");
  // the body's delegate: a path link inside the shown file carries data-line or data-frag, handed on as `at`
  const body4 = doc.getElementById("romp-fileview")!.querySelector(".fileview-body")!;
  const link = new El("span"); link.dataset.act = "openpath"; link.dataset.path = REPORT; link.dataset.frag = "findings";
  body4.appendChild(link);
  link.dispatchEvent(new Ev("click"));
  await settle();
  const wrap5 = doc.getElementById("romp-fileview")!;
  assert.ok(wrap5 && !wrap5.contains(link), "the link's click replaced the viewer");
  assert.equal(seam!.mode(), "rendered", "a heading link opens the Rendered view");
  assert.equal(frames.length, 1);
  const els5 = layRendered(wrap5.querySelector(".fileview-md")!);
  flushFrames();
  assert.deepEqual(scrolls(els5), [0, 1, 0, 0], "…and lands on the heading");
  const link2 = new El("span"); link2.dataset.act = "openpath"; link2.dataset.path = REPORT; link2.dataset.line = "3";
  wrap5.querySelector(".fileview-body")!.appendChild(link2);
  link2.dispatchEvent(new Ev("click"));
  await settle();
  assert.equal(seam!.mode(), "raw", "a line link opens the Raw view for that open");
  assert.equal(store.get("romp:fileviewFmt"), JSON.stringify({ md: "rendered" }), "the preference the Rendered toggle saved above stands: the line's Raw view is not written");
  fv.closeFileView();
});

test("an open at a heading the note does not have lands nowhere and says so in the notice bar, above the body row, the name decoded; under the Raw preference the heading waits for the Rendered toggle, and the notice with it", async (t) => {
  withFrames(t);
  const o = await open(REPORT, t, SID, { at: { heading: "nowhere" } });
  assert.equal(frames.length, 1);
  assert.equal(errBar(o.body), null, "nothing said before the frame judges the painted DOM");
  flushFrames();   // no heading laid: the section is not in the note
  assert.equal(errBar(o.body)?.textContent, 'No section named "nowhere" in this file.', "the notice names the section");
  assert.ok(aboveRow(o.body), "as a card row above the body");
  assert.equal(o.body.scrolled, 0, "and nothing scrolled: never a silent landing at the top");
  // the frame ran once: a later paint (the toggle) lands nothing and raises nothing again
  o.b.raw.click(); o.b.rendered.click();
  assert.equal(frames.length, 0, "the heading was spent");
  // a percent-encoded name is shown decoded
  o.fv.openFileView(REPORT, SID, { at: { heading: "#Evidence%20Results" } });
  await settle();
  flushFrames();
  const body2 = doc.getElementById("romp-fileview")!.querySelector(".fileview-body")!;
  assert.equal(errBar(body2)?.textContent, 'No section named "Evidence Results" in this file.');
  // the Raw preference: no ids to land on, so the landing waits for the Rendered toggle rather than being spent
  const r = await open(REPORT, t, SID, { at: { heading: "findings" } }, true);
  assert.equal(r.ctx.mode(), "raw");
  assert.equal(frames.length, 0, "no landing queued from a Raw paint");
  assert.equal(errBar(r.body), null, "and no notice: the Raw view cannot judge");
  r.b.rendered.click();
  assert.equal(frames.length, 1, "the Rendered paint queues the landing");
  const els = layRendered(r.body.querySelector(".fileview-md")!);
  flushFrames();
  assert.deepEqual(scrolls(els), [0, 1, 0, 0], "the heading lands after the toggle");
  assert.equal(errBar(r.body), null);
});

test("an open at a heading on a file that is not markdown (a todo's `src/app.py#l12`, the section spelling of a line slip, or `src/app.py#main`): the file has no sections and no Rendered toggle to wait for, so its first text paint judges the target and the notice names the section, the name decoded (review round 2: before, the target was never spent and the file opened silently at its top, the very open the notice exists to name)", async (t) => {
  withFrames(t);
  const o = await open(APP, t, SID, { at: { heading: "#l12" } });
  assert.equal(o.ctx.mode(), "raw", "a code file's one text view");
  assert.equal(frames.length, 1, "the landing is judged one frame after the paint, as a note's is (before the fix: no frame queued, the target held for a Rendered toggle that never comes)");
  assert.equal(errBar(o.body), null, "nothing said before the frame");
  flushFrames();
  assert.equal(errBar(o.body)?.textContent, 'No section named "l12" in this file.', "the notice names the section");
  assert.ok(aboveRow(o.body), "as a card row above the body");
  assert.equal(o.body.scrolled, 0, "and nothing scrolled: never a silent landing at the top");
  assert.equal(frames.length, 0, "the heading was spent");
  // the name percent-decoded, as for a note
  o.fv.openFileView(APP, SID, { at: { heading: "main%20loop" } });
  await settle(); flushFrames();
  const body2 = doc.getElementById("romp-fileview")!.querySelector(".fileview-body")!;
  assert.equal(errBar(body2)?.textContent, 'No section named "main loop" in this file.');
  // a note's Raw view still waits for the Rendered toggle (the case above): only a file with no Rendered view is judged in Raw
  const r = await open(REPORT, t, SID, { at: { heading: "l12" } }, true);
  assert.equal(r.ctx.mode(), "raw");
  assert.equal(frames.length, 0, "a markdown file's Raw paint queues no landing");
  assert.equal(errBar(r.body), null);
});

test("an open at a source offset: the block holding it is scrolled to the centre in the Rendered view, the row in Raw (a .py file, or a markdown file under the Raw preference); an offset past the end lands on the last block or row and says so in the notice bar", async (t) => {
  withFrames(t);
  const o = await open(REPORT, t, SID, { at: { offset: DOC.indexOf("We recommend") } });
  assert.equal(o.ctx.mode(), "rendered", "an offset keeps the view the preference names");
  assert.equal(store.has("romp:fileviewFmt"), false);
  assert.equal(frames.length, 1, "the offset is spent at the landing and scrolled the next frame");
  const els = layRendered(o.body.querySelector(".fileview-md")!);
  flushFrames();
  assert.deepEqual(scrolls(els), [0, 0, 0, 1], "the fourth block, the paragraph holding the offset");
  assert.deepEqual(els[3].scrolledWith, { block: "center" }, "centred");
  assert.equal(errBar(o.body), null, "no notice: the offset is inside the text");
  // offset 0: the first block; an offset on a blank line between two blocks: the block after the gap (reader-place blockHolding)
  o.fv.openFileView(REPORT, SID, { at: { offset: 0 } }); await settle();
  let els2 = layRendered(doc.getElementById("romp-fileview")!.querySelector(".fileview-md")!); flushFrames();
  assert.deepEqual(scrolls(els2), [1, 0, 0, 0]);
  o.fv.openFileView(REPORT, SID, { at: { offset: DOC.indexOf("\n\n## Findings") + 1 } }); await settle();
  els2 = layRendered(doc.getElementById("romp-fileview")!.querySelector(".fileview-md")!); flushFrames();
  assert.deepEqual(scrolls(els2), [0, 1, 0, 0], "the blank line before Findings lands on Findings");
  // past the end: the last block, and the notice in the line rule's shape
  o.fv.openFileView(REPORT, SID, { at: { offset: DOC.length + 50 } }); await settle();
  const wrap3 = doc.getElementById("romp-fileview")!, body3 = wrap3.querySelector(".fileview-body")!;
  const els3 = layRendered(wrap3.querySelector(".fileview-md")!); flushFrames();
  assert.deepEqual(scrolls(els3), [0, 0, 0, 1], "the last block");
  assert.equal(errBar(body3)?.textContent, "Offset " + (DOC.length + 50) + " is past the end of this file, which has " + DOC.length + " characters; showing the last block.");
  assert.ok(aboveRow(body3));
  o.fv.closeFileView();
  // the Raw view: a code file's row at the offset (the second logical line of PY), centred
  const c = await open(APP, t, SID, { at: { offset: PY.indexOf("return") } });
  assert.equal(frames.length, 1);
  const rows = layRows(c.body.querySelector("code.hljs")!, PY); flushFrames();
  assert.deepEqual(scrolls(rows), [0, 1], "row 2 holds the offset");
  assert.deepEqual(rows[1].scrolledWith, { block: "center" });
  assert.equal(errBar(c.body), null);
  c.fv.openFileView(APP, SID, { at: { offset: PY.length + 9 } }); await settle();
  const body4 = doc.getElementById("romp-fileview")!.querySelector(".fileview-body")!;
  const rows4 = layRows(body4.querySelector("code.hljs")!, PY); flushFrames();
  assert.deepEqual(scrolls(rows4), [0, 1], "past the end: the last row");
  assert.equal(errBar(body4)?.textContent, "Offset " + (PY.length + 9) + " is past the end of this file, which has " + PY.length + " characters; showing the last line.");
  c.fv.closeFileView();
  // a markdown file under the Raw preference: the row, not a block
  const r = await open(REPORT, t, SID, { at: { offset: DOC.indexOf("We recommend") } }, true);
  assert.equal(r.ctx.mode(), "raw");
  const rrows = layRows(r.body.querySelector("code.hljs")!, DOC); flushFrames();
  assert.deepEqual(scrolls(rrows), [0, 0, 0, 0, 0, 1], "the sixth row (the offset's line, one .fv-cl per logical line)");
  assert.deepEqual(rrows[5].scrolledWith, { block: "center" });
  assert.equal(store.get("romp:fileviewFmt"), JSON.stringify({ md: "raw" }), "the preference stands as it was");
});

// ── a Latin-1 file's line (plans/markdown-viewer.md Slice 7, item 5) ─────────────────────────────────────────────────────
// The kernel serves a file its UTF-8 decode refused re-encoded from Latin-1, text/plain with X-Romp-Text-Utf8 "0", and the
// Edit gate hides its button on that verdict (file-edit.test.ts pins the gate); before item 5 nothing said why. The stub's
// `utf8` entry answers the header. The reading is the card's notice bar (errBar and aboveRow: the card's child directly above
// the body row, one notice at a time) and the Edit button's hidden bit. The file is one open() never resets, so a case sets
// its entry and removes it after. Synthetic text with one non-ASCII character, as the kernel would have re-encoded it.
const LEGACY = ROOT + "/docs/legacy.txt";
const LEGACY_TEXT = "café au lait\nthe notes-api readme an older editor wrote\n";
const focusWindow = () => { win.dispatchEvent(new Event("focus")); };   // the changed-on-disk probe's event (file-view-reload.test.ts's idiom)
const cardRows = (body: El): string[] => cardOf(body).childNodes.filter((x): x is El => x instanceof El).map((x) => x.className);
/** The bar's own words: its text nodes, without a button's label. */
const barWords = (body: El): string => { const bar = errBar(body); return bar ? bar.childNodes.filter((x): x is Txt => x instanceof Txt).map((x) => x.textContent).join("") : ""; };

test("a Latin-1 file says why Edit is off (Slice 7 of plans/markdown-viewer.md, item 5): a text/plain answer wearing X-Romp-Text-Utf8 \"0\" raises LATIN1_NOTICE in the notice bar, the card's child directly above the body row, with Edit hidden and the text shown (text() answers it, error() null: the file is readable); a reload's landing leaves the standing line as it is, the same element (one announcement; the review's round 1); the changed-on-disk bar takes the row and its Reload's landing brings the line back over the new text, a fresh element; a \"1\" file and an image raise nothing", async (t) => {
  disk[LEGACY] = { bytes: LEGACY_TEXT, type: "text/plain; charset=utf-8", mtimeNs: MT, utf8: "0" };
  t.after(() => { delete disk[LEGACY]; });
  const o = await open(LEGACY, t);
  const { fv, ctx, body, b } = o;
  const bar = errBar(body);
  assert.ok(bar, "the line is up (before item 5: no bar, and Edit hidden with no word)");
  assert.equal(bar!.textContent, fv.LATIN1_NOTICE, "the exported sentence, alone");
  assert.equal(fv.LATIN1_NOTICE, "This file is not UTF-8 on disk, so it can be read here but not edited: a save would rewrite its bytes as UTF-8.", "contract C5's text");
  assert.equal(bar!.id, "fileview-save-err", "the notice bar (noteBar), not a pane in the body");
  assert.ok(aboveRow(body), "a child of the card directly above the body row");
  assert.deepEqual(cardRows(body), ["fileview-bar", "fileview-err", "fileview-main"], "title bar, notice, body row: one notice at a time");
  assert.equal(bar!.querySelectorAll("button").length, 0, "no button: the way out is another encoding, not a click");
  assert.equal(b.edit.hidden, true, "Edit is off (the gate's own verdict, unchanged)");
  assert.equal(ctx.text(), LEGACY_TEXT, "text() answers the re-encoded text: the file is readable");
  assert.equal(ctx.error(), null, "error() null: the file shows; the line is a notice, not a pane in place of the file");
  assert.equal(ctx.mode(), "raw"); assert.ok(body.querySelector("code.hljs"), "the text is painted as rows");
  assert.equal(paints, 1);
  // a reload's landing (the Comments panel's poll asks one at every status whose mtime moved) finds the line standing with the same
  // words and leaves the element as it is: the bar is a role=status live region, so a fresh element with the same words was read
  // out again by assistive technology at every reload (the Slice 7 review's round 1; before, a fresh bar at every landing)
  ctx.reload(); await settle();
  const bar2 = errBar(body);
  assert.equal(bar2, bar, "the same element stands: nothing was re-raised and nothing is announced again"); assert.equal(bar2!.textContent, fv.LATIN1_NOTICE);
  assert.deepEqual(cardRows(body), ["fileview-bar", "fileview-err", "fileview-main"], "one notice");
  assert.equal(paints, 2); assert.equal(b.edit.hidden, true);
  // the changed-on-disk bar, raised later, takes the row (the one-bar rule); its Reload's landing drops that bar
  // (settleDiskBar, before the text paint) and the line returns over the new text
  const MT7 = "1757145600000000007";
  disk[LEGACY] = { bytes: LEGACY_TEXT + "one more line\n", type: "text/plain; charset=utf-8", mtimeNs: MT7, utf8: "0" };
  focusWindow(); await settle();
  assert.equal(barWords(body), "Changed on disk.", "the changed-on-disk bar took the row");
  const reload = errBar(body)!.querySelectorAll("button");
  assert.equal(reload.length, 1); assert.equal(reload[0].textContent, "Reload");
  reload[0].click(); await settle();
  assert.equal(paints, 3, "the Reload's landing painted");
  assert.equal(ctx.mtimeNs(), MT7); assert.equal(ctx.text(), LEGACY_TEXT + "one more line\n");
  assert.equal(errBar(body)?.textContent, fv.LATIN1_NOTICE, "the line is back over the dropped bar (before item 5: nothing said why Edit stayed off)");
  assert.notEqual(errBar(body), bar, "a fresh element here: the changed-on-disk bar had taken the row, so the line's return is new information and is announced");
  assert.equal(errBar(body)!.querySelectorAll("button").length, 0, "the bar's Reload went with it");
  assert.deepEqual(cardRows(body), ["fileview-bar", "fileview-err", "fileview-main"], "still one notice");
  assert.equal(b.edit.hidden, true);
  // a "1" file (the stub's default) raises nothing and arms Edit; an image, whose answer wears no text type, raises nothing either
  fv.closeFileView();
  const u = await open(APP, t);
  assert.equal(errBar(u.body), null, "a faithful UTF-8 file: no line"); assert.equal(u.b.edit.hidden, false, "and Edit is on");
  u.fv.closeFileView();
  const i = await open(PLOT, t);
  assert.equal(errBar(i.body), null, "an image: no line (the verdict reads the text type with the value, never !isText)");
  assert.equal(i.b.edit.hidden, true, "Edit off for the image's own reason");
});

test("a target's notice wins the row over the Latin-1 line (Slice 7, item 5, open question 13): an open at an offset past the end on a \"0\" file shows the line at the landing and the offset notice replaces it a frame later; a reload has no target and brings the line back (the past-the-end LINE notice, raised inside landTarget, wins by the raise's place before it: file-view.test.ts pins the order and the failures leg drives it, since this stand-in lays no rows at a landing)", async (t) => {
  withFrames(t);
  disk[LEGACY] = { bytes: LEGACY_TEXT, type: "text/plain; charset=utf-8", mtimeNs: MT, utf8: "0" };
  t.after(() => { delete disk[LEGACY]; });
  const o = await open(LEGACY, t, SID, { at: { offset: LEGACY_TEXT.length + 9 } });
  assert.equal(errBar(o.body)?.textContent, o.fv.LATIN1_NOTICE, "at the landing the line stands (the offset is spent a frame later)");
  assert.equal(frames.length, 1, "the offset's frame is queued");
  const rows = layRows(o.body.querySelector("code.hljs")!, LEGACY_TEXT); flushFrames();
  assert.deepEqual(scrolls(rows), [0, 1], "past the end: the last row");
  assert.equal(errBar(o.body)?.textContent, "Offset " + (LEGACY_TEXT.length + 9) + " is past the end of this file, which has " + LEGACY_TEXT.length + " characters; showing the last line.",
    "the target's notice took the row: the answer to the person's own click");
  assert.deepEqual(cardRows(o.body), ["fileview-bar", "fileview-err", "fileview-main"], "one notice");
  assert.equal(o.b.edit.hidden, true, "Edit still off");
  o.ctx.reload(); await settle();
  assert.equal(errBar(o.body)?.textContent, o.fv.LATIN1_NOTICE, "the reload's landing raised the line again");
  assert.equal(frames.length, 0, "a reload spends no target");
});

test("a landing whose header says UTF-8 drops a standing Latin-1 line (the Slice 7 review's round 1): the file re-saved as UTF-8 lands through the panel's door (ctx.reload) with Edit back and no line; a \"0\" landing after it raises the line again; a target's notice standing in the line's place is not touched by a UTF-8 landing", async (t) => {
  withFrames(t);
  disk[LEGACY] = { bytes: LEGACY_TEXT, type: "text/plain; charset=utf-8", mtimeNs: MT, utf8: "0" };
  t.after(() => { delete disk[LEGACY]; });
  const o = await open(LEGACY, t);
  const { fv, ctx, body, b } = o;
  assert.equal(errBar(body)?.textContent, fv.LATIN1_NOTICE, "the line is up"); assert.equal(b.edit.hidden, true);
  // re-saved as UTF-8 by a session: the Comments panel's poll lands the bytes through ctx.reload, the header saying "1" now
  const MT8 = "1757145600000000008";
  disk[LEGACY] = { bytes: LEGACY_TEXT + "utf-8 now\n", type: "text/plain; charset=utf-8", mtimeNs: MT8, utf8: "1" };
  ctx.reload(); await settle();
  assert.equal(ctx.mtimeNs(), MT8); assert.equal(ctx.text(), LEGACY_TEXT + "utf-8 now\n"); assert.equal(paints, 2, "the landing painted");
  assert.equal(b.edit.hidden, false, "Edit is back (the gate's own verdict, isText)");
  assert.equal(errBar(body), null, "the line went with the landing that made it false (before: it stood over the shown Edit button until the next notice, saying the file could not be edited)");
  assert.deepEqual(cardRows(body), ["fileview-bar", "fileview-main"], "title bar and body row: no notice");
  // Latin-1 again (an older editor wrote it back): the line returns with the "0"
  const MT9 = "1757145600000000009";
  disk[LEGACY] = { bytes: LEGACY_TEXT, type: "text/plain; charset=utf-8", mtimeNs: MT9, utf8: "0" };
  ctx.reload(); await settle();
  assert.equal(errBar(body)?.textContent, fv.LATIN1_NOTICE, "the line is back"); assert.equal(b.edit.hidden, true); assert.equal(paints, 3);
  // a target's notice standing in the row (an offset past the end on a "0" file, raised a frame after the open) is not the line: a
  // UTF-8 landing leaves it, since it is the answer to the person's own click and says nothing about Edit
  fv.closeFileView();
  disk[LEGACY] = { bytes: LEGACY_TEXT, type: "text/plain; charset=utf-8", mtimeNs: MT, utf8: "0" };
  const o2 = await open(LEGACY, t, SID, { at: { offset: LEGACY_TEXT.length + 9 } });
  layRows(o2.body.querySelector("code.hljs")!, LEGACY_TEXT); flushFrames();
  const words = "Offset " + (LEGACY_TEXT.length + 9) + " is past the end of this file, which has " + LEGACY_TEXT.length + " characters; showing the last line.";
  assert.equal(errBar(o2.body)?.textContent, words, "the target's notice took the row");
  disk[LEGACY] = { bytes: LEGACY_TEXT, type: "text/plain; charset=utf-8", mtimeNs: MT8, utf8: "1" };
  o2.ctx.reload(); await settle();
  assert.equal(errBar(o2.body)?.textContent, words, "a UTF-8 landing drops the Latin-1 line alone: the target's notice stands (the one-bar rule's next notice replaces it)");
  assert.equal(o2.b.edit.hidden, false, "Edit is back all the same");
});

// ── the sanitizer seam (md-sanitize.ts setMdSanitizer; Slice 7 of plans/markdown-viewer.md, item 1's first step) ─────
// A record pin: the stand-in installed at the top of this file is what every Rendered paint here sanitizes through, and the
// constraint it exists for is executed over the library itself. DOMPurify 3.4.10 built over a window with no `document`
// (createDOMPurify's isSupported branch, purify.es.mjs) returns the bare factory, its `sanitize` and `addHook` unassigned,
// so before the seam sanitizeMd threw at every call under node and every markdown paint in every node suite went through
// mdBlock's catch, which wrote the note's text into the box: no node suite ever ran the real sanitize, and none can (the
// browser legs do). Before the seam: the stand-in was never reached (red at the first assertion over a git archive of the
// base with setMdSanitizer stubbed).
test("record pin: a Rendered paint sanitizes through the seam's stand-in, once per paint and never on a Raw one, with marked's markup for the note; DOMPurify built over this stand-in's window (no document) is the bare factory, isSupported false with sanitize and addHook unassigned, and so is the module-global instance md-sanitize.ts imports: before the seam no node suite ran the real sanitize and every markdown paint here went through mdBlock's catch", async (t) => {
  const before = sanitized.length;
  const o = await open(REPORT, t);
  assert.equal(sanitized.length, before + 1, "the open's Rendered paint reached the stand-in's sanitize");
  assert.match(sanitized[before], /<h1>Report<\/h1>/, "handed marked's markup for the note (the heading ids are minted after, by sanitizeMd's own pass)");
  assert.ok(o.body.querySelector(".fileview-md"), "the box mdBlock adopted the stand-in's body into");
  assert.equal(o.ctx.mode(), "rendered");
  o.b.raw.click();
  assert.equal(sanitized.length, before + 1, "a Raw paint sanitizes nothing");
  o.b.rendered.click();
  assert.equal(sanitized.length, before + 2, "the Rendered toggle paints through the stand-in again");
  // the constraint, executed: an instance built for a window with no document, and the module-global one
  const bare = DOMPurify(win) as unknown as { isSupported: boolean; sanitize?: unknown; addHook?: unknown };
  assert.equal(bare.isSupported, false, "no window.document: DOMPurify reports itself unsupported");
  assert.equal(bare.sanitize, undefined); assert.equal(bare.addHook, undefined);
  assert.equal(DOMPurify.isSupported, false, "the module-global instance is that factory under node too");
});

test("a failed reload drops a standing Latin-1 line (the Slice 7 review's round 2): a \"0\" file whose next fetch answers 404 (a session deleted it; the Comments panel's poll reloads through ctx.reload) or 413 (it grew past the cap) shows the pane in the body with no notice bar over it (before: the line saying the file can be read here stood above a pane saying it could not be, until some other notice replaced it), error() the pane's words, Edit still off; a \"0\" landing after it raises the line again over the text", async (t) => {
  disk[LEGACY] = { bytes: LEGACY_TEXT, type: "text/plain; charset=utf-8", mtimeNs: MT, utf8: "0" };
  t.after(() => { delete disk[LEGACY]; });
  const o = await open(LEGACY, t);
  const { fv, ctx, body, b } = o;
  assert.equal(errBar(body)?.textContent, fv.LATIN1_NOTICE, "the line is up"); assert.equal(b.edit.hidden, true);
  /** The card's notice bar alone (noteBar's element), never a pane inside the body. */
  const noticeBar = (): El | null => cardOf(body).childNodes.find((x): x is El => x instanceof El && x.id === "fileview-save-err") ?? null;
  // deleted on disk: the panel's poll meets a 404
  delete disk[LEGACY];
  ctx.reload(); await settle();
  const pane = body.querySelector(".fileview-err");
  assert.ok(pane, "the pane is in the body"); assert.equal(pane!.textContent, "no such file: " + LEGACY, "the kernel's words");
  assert.equal(ctx.error(), "no such file: " + LEGACY, "error() answers the pane's words");
  assert.equal(noticeBar(), null, "no notice bar over the pane (before: the Latin-1 line stood there, contradicting it)");
  assert.deepEqual(cardRows(body), ["fileview-bar", "fileview-main"], "title bar and body row; the pane is inside the body");
  assert.equal(paints, 2, "the pane's paint fired the hooks"); assert.equal(b.edit.hidden, true, "Edit still off");
  // the file is back, still Latin-1: the landing raises the line again over the text
  disk[LEGACY] = { bytes: LEGACY_TEXT, type: "text/plain; charset=utf-8", mtimeNs: "1757145600000000031", utf8: "0" };
  ctx.reload(); await settle();
  assert.equal(noticeBar()?.textContent, fv.LATIN1_NOTICE, "the line is back with the \"0\"");
  assert.equal(body.querySelector(".fileview-err"), null, "the pane went with the text's paint");
  assert.deepEqual(cardRows(body), ["fileview-bar", "fileview-err", "fileview-main"]); assert.equal(paints, 3);
  // grown past the cap: the next fetch answers 413, the pane offers Download, and the line goes the same way
  const real = (globalThis as any).fetch;
  (globalThis as any).fetch = async (url: string, init?: { method?: string }) => {
    if ((!init || !init.method || init.method === "GET") && url.includes(encodeURIComponent(LEGACY))) return { ok: false, status: 413, headers: { get: () => null }, text: async () => "file too large to render: 20 MB over the 10 MB cap: " + LEGACY };
    return real(url, init);
  };
  t.after(() => { (globalThis as any).fetch = real; });
  ctx.reload(); await settle();
  const big = body.querySelector(".fileview-err");
  assert.ok(big && big.textContent.startsWith("file too large to render"), "the 413 pane");
  assert.equal(big!.querySelectorAll("button").length, 1, "Download offered: the file exists");
  assert.equal(noticeBar(), null, "no line over the 413 pane either");
  assert.equal(ctx.error(), "file too large to render: 20 MB over the 10 MB cap: " + LEGACY);
  assert.equal(paints, 4);
  (globalThis as any).fetch = real;
});

test("after the failure pane, a format pick brings the Latin-1 line back over the repainted text (the Slice 7 review's round 3): a \"0\" .md whose reload met a 404 shows the pane with no line (round 2's case); the Raw click repaints the last landing's text with Edit still off, and the line stands over it again, one bar (before: the text with Edit off and nothing saying why, until the next \"0\" landing); the Rendered click over content raises no second bar; the seam's setMode takes the same road; a changed-on-disk bar re-armed over the pane keeps the row, and its Reload's landing brings the line back as before; a UTF-8 file's repaint raises nothing", async (t) => {
  const LEGACY_MD = ROOT + "/docs/legacy.md";
  const LEGACY_MD_TEXT = "# Café\n\nau lait: the notes-api readme an older editor wrote\n";
  disk[LEGACY_MD] = { bytes: LEGACY_MD_TEXT, type: "text/plain; charset=utf-8", mtimeNs: MT, utf8: "0" };
  t.after(() => { delete disk[LEGACY_MD]; });
  const o = await open(LEGACY_MD, t);
  const { fv, ctx, body, b } = o;
  /** The card's notice bars (noteBar's element, id fileview-save-err), never a pane inside the body. */
  const noticeBarsOf = (bd: El): El[] => cardOf(bd).childNodes.filter((x): x is El => x instanceof El && x.id === "fileview-save-err");
  const noticeBar = (): El | null => noticeBarsOf(body)[0] ?? null;
  assert.equal(noticeBar()?.textContent, fv.LATIN1_NOTICE, "the line is up"); assert.equal(b.edit.hidden, true); assert.equal(paints, 1);
  // deleted on disk: the panel's poll meets a 404, the pane paints and the line goes (round 2)
  delete disk[LEGACY_MD];
  ctx.reload(); await settle();
  assert.ok(body.querySelector(".fileview-err"), "the pane is in the body"); assert.equal(noticeBar(), null, "no line over the pane");
  assert.equal(ctx.error(), "no such file: " + LEGACY_MD); assert.equal(paints, 2);
  // the Raw click: the last landing's text repaints over the pane, Edit still off, and the line says why again
  b.raw.click(); await settle();
  assert.equal(body.querySelector(".fileview-err"), null, "the pane went with the text's paint"); assert.ok(body.querySelector("code.hljs"), "the rows");
  assert.equal(ctx.error(), null, "error() null: content shows"); assert.equal(ctx.mode(), "raw"); assert.equal(ctx.text(), LEGACY_MD_TEXT, "the last landing's text");
  assert.equal(b.edit.hidden, true, "Edit still off (the gate reads the landing's verdict)");
  assert.equal(noticeBar()?.textContent, fv.LATIN1_NOTICE, "the line is back over the repainted text (before: no notice, Edit off, nothing saying why)");
  assert.equal(noticeBarsOf(body).length, 1, "one bar"); assert.deepEqual(cardRows(body), ["fileview-bar", "fileview-err", "fileview-main"]);
  assert.equal(paints, 3);
  // the Rendered click over content: the line stands, the same element, no second raise
  const standing = noticeBar()!;
  b.rendered.click(); await settle();
  assert.equal(ctx.mode(), "rendered"); assert.ok(body.querySelector(".fileview-md"), "the note renders");
  assert.equal(noticeBar(), standing, "the same bar: a pick over content raises nothing"); assert.equal(noticeBarsOf(body).length, 1); assert.equal(paints, 4);
  // the seam's setMode (the Comments panel's switch to Raw) over the pane takes the same road
  ctx.reload(); await settle();
  assert.ok(body.querySelector(".fileview-err"), "the pane again"); assert.equal(noticeBar(), null, "and the line dropped again"); assert.equal(paints, 5);
  ctx.setMode("raw"); await settle();
  assert.equal(ctx.mode(), "raw"); assert.equal(ctx.error(), null); assert.ok(body.querySelector("code.hljs"));
  assert.equal(noticeBar()?.textContent, fv.LATIN1_NOTICE, "setMode's repaint brings the line back too"); assert.equal(noticeBarsOf(body).length, 1); assert.equal(paints, 6);
  // a notice standing over the pane keeps the row (the one-bar rule): the changed-on-disk bar, whose own Reload met the 404 and
  // re-armed above the pane, answers the person's click and is not replaced by the line
  const MT7 = "1757145600000000007";
  disk[LEGACY_MD] = { bytes: LEGACY_MD_TEXT + "one more line\n", type: "text/plain; charset=utf-8", mtimeNs: MT7, utf8: "0" };
  focusWindow(); await settle();
  assert.equal(barWords(body), "Changed on disk.", "the changed-on-disk bar took the row");
  delete disk[LEGACY_MD];
  const reload = errBar(body)!.querySelectorAll("button");
  assert.equal(reload.length, 1); assert.equal(reload[0].textContent, "Reload");
  reload[0].click(); await settle();
  assert.ok(body.querySelector(".fileview-err"), "the bar's Reload met the 404: the pane"); assert.equal(paints, 7);
  assert.equal(barWords(body), "Changed on disk.", "the bar stands over the pane, re-armed"); assert.equal(reload[0].disabled, false); assert.equal(reload[0].textContent, "Reload");
  b.raw.click(); await settle();
  assert.equal(body.querySelector(".fileview-err"), null, "the text repainted"); assert.equal(paints, 8);
  assert.equal(barWords(body), "Changed on disk.", "the bar keeps the row: no line replaces a standing notice"); assert.equal(noticeBarsOf(body).length, 1);
  assert.equal(errBar(body)!.querySelectorAll("button").length, 1, "its Reload still there");
  // the bar's Reload with the file back, still Latin-1: the landing drops the bar and raises the line, as the round 1 case has it
  disk[LEGACY_MD] = { bytes: LEGACY_MD_TEXT + "one more line\n", type: "text/plain; charset=utf-8", mtimeNs: MT7, utf8: "0" };
  reload[0].click(); await settle();
  assert.equal(ctx.mtimeNs(), MT7); assert.equal(paints, 9);
  assert.equal(noticeBar()?.textContent, fv.LATIN1_NOTICE, "the landing's own raise"); assert.equal(noticeBarsOf(body).length, 1); assert.equal(errBar(body)!.querySelectorAll("button").length, 0);
  // a UTF-8 note: the same repaint over a 404 pane raises nothing (no header said Latin-1)
  fv.closeFileView();
  const u = await open(REPORT, t);
  delete disk[REPORT];
  t.after(() => { disk[REPORT] = { bytes: DOC, type: "text/plain; charset=utf-8", mtimeNs: MT }; });
  u.ctx.reload(); await settle();
  assert.ok(u.body.querySelector(".fileview-err"), "the pane"); assert.equal(u.ctx.error(), "no such file: " + REPORT);
  u.b.raw.click(); await settle();
  assert.equal(u.body.querySelector(".fileview-err"), null, "the note's text repainted"); assert.equal(u.ctx.error(), null);
  assert.equal(noticeBarsOf(u.body).length, 0, "no bar: nothing to explain"); assert.equal(u.b.edit.hidden, false, "Edit shows over a UTF-8 file's text");
});

// ── item 1 of Slice 7 of plans/markdown-viewer.md: a render that throws shows the text under a line that says so ─────────
// Every failure says what happened where the person is looking: mdBlock keeps no catch, and each viewer's renderBody wraps
// the block's build and the swap in one try whose catch records the message (renderFell), paints the RENDER_FELL line as the
// body's first child and the file's text as Raw rows under it (codeBlock), and lets the rest of the pass run, so the hooks
// fire once and read the rows through mode(), which answers "raw" while the record stands. The Rendered button stays pressed
// (the person's saved choice; the line says why rows show); the Raw click paints rows without the line; the Rendered click
// tries again. Before: mdBlock's own catch wrote the note's text into `.fileview-md` as one unannounced paragraph and mode()
// kept answering "rendered" (red at the first assertion over a git archive of the base with RENDER_FELL stubbed).
test("a Rendered paint whose sanitizer throws paints the RENDER_FELL line first, naming the message, and the text as Raw rows under it: no .fileview-md, mode() raw, renderedImages() empty, the Outline button hidden, the Rendered button pressed, one paint; the Raw click leaves rows and no line; a Rendered click that throws again brings the line back; the Rendered click with the sanitizer healed renders again", async (t) => {
  const { RENDER_FELL } = await mod();
  assert.equal(RENDER_FELL, "This file could not be shown as rendered Markdown, so its text is shown as written", "the exported words (contract C5: the guide carries them; no terminal period, the line adds the message and its own)");
  sanitizeFails = "synthetic sanitizer failure";
  t.after(() => { sanitizeFails = null; sanitizeAnswers = null; });
  const o = await open(REPORT, t);
  const { ctx, body } = o;
  const first = body.childNodes[0];
  assert.ok(first instanceof El && first.matches("div.fileview-err"), "the body's first child is the failure line, in the pane dress");
  assert.equal(first.textContent, RENDER_FELL + " (synthetic sanitizer failure).", "the sentence, then the error's message in parentheses");
  assert.equal(first.querySelectorAll("button").length, 0, "no Download: the text is showing");
  assert.equal(first.querySelectorAll(".fileview-err-hint").length, 0, "no hint row: the title bar names the path");
  const second = body.childNodes[1];
  assert.ok(second instanceof El && second.matches("div.fileview-code") && second.querySelector("code.hljs"), "the Raw rows' root under the line, its code element where the anchor map and the reader's place read rows");
  assert.equal(body.childNodes.length, 2, "the line and the rows, nothing else");
  assert.equal(body.querySelector(".fileview-md"), null, "no Rendered box: the failed block never reached the body");
  assert.equal(ctx.mode(), "raw", "mode() answers raw over the rows (the panel pairs over code.hljs, the place reads rows)");
  assert.equal(o.b.rendered.classList.contains("on"), true, "the Rendered button stays pressed: the person's saved choice, the line says why rows show");
  assert.equal(o.b.rendered.getAttribute("aria-pressed"), "true");
  assert.equal(o.b.raw.classList.contains("on"), false);
  assert.equal(store.get("romp:fileviewFmt"), undefined, "the saved preference is untouched (the default, Rendered, was never written)");
  assert.deepEqual(ctx.renderedImages(), [], "renderedImages() follows mode()");
  assert.equal(o.wrap.querySelector(".fileview-outline-btn")!.hidden, true, "the Outline button hides: no .fileview-md holds a heading");
  assert.equal(ctx.text(), DOC, "text() is the file's text: the rows are the content");
  assert.equal(paints, 1, "one paint, the fallback's, fired the hooks");
  assert.equal(errBar(body), first, "the card's first .fileview-err is the line in the body: no bar was raised");
  // the Raw click: rows alone, the record cleared
  o.b.raw.click();
  assert.equal(body.childNodes.length, 1);
  assert.ok((body.childNodes[0] as El).matches("div.fileview-code"), "rows alone");
  assert.equal(body.querySelector(".fileview-err"), null, "the line went with the Rendered attempt");
  assert.equal(ctx.mode(), "raw");
  assert.equal(paints, 2);
  // the Rendered click tries again: still throwing, the line comes back over rows
  o.b.rendered.click();
  assert.ok((body.childNodes[0] as El).matches("div.fileview-err") && (body.childNodes[1] as El).matches("div.fileview-code"), "the line over the rows again");
  assert.equal(ctx.mode(), "raw");
  assert.equal(paints, 3);
  // healed: the Rendered click renders
  sanitizeFails = null;
  o.b.rendered.click();
  assert.ok(body.querySelector(".fileview-md"), "the box mdBlock adopted the stand-in's body into");
  assert.equal(body.querySelector(".fileview-err"), null, "no line over a render that stands");
  assert.equal(ctx.mode(), "rendered");
  assert.equal(paints, 4);
  assert.equal(o.wrap.querySelector(".fileview-outline-btn")!.hidden, true, "no heading in the stand-in's empty body: the button stays hidden for that reason alone");
});

test("a throw from the DOM work after the sanitizer (adopting the body it answered) takes the same road as a sanitizer throw, and a thrown value that is not an Error is named by its string", async (t) => {
  const { RENDER_FELL } = await mod();
  // a body sanitizeMd's own passes can walk (querySelectorAll finds nothing) whose adoption, mdBlock's Array.from over its childNodes, throws
  sanitizeAnswers = () => { const b = new El("body"); b.querySelectorAll = () => []; Object.defineProperty(b, "childNodes", { get() { throw new Error("synthetic adoption failure"); } }); return b; };
  t.after(() => { sanitizeAnswers = null; sanitizeFails = null; });
  const o = await open(REPORT, t);
  assert.equal((o.body.childNodes[0] as El).textContent, RENDER_FELL + " (synthetic adoption failure).");
  assert.ok((o.body.childNodes[1] as El).matches("div.fileview-code"));
  assert.equal(o.ctx.mode(), "raw"); assert.equal(paints, 1);
  // a bare string thrown (a library that throws a value): String(err)
  sanitizeAnswers = () => { throw "bare string"; };   // eslint-disable-line no-throw-literal
  o.b.rendered.click();
  assert.equal((o.body.childNodes[0] as El).textContent, RENDER_FELL + " (bare string).");
  assert.equal(paints, 2);
  // an Error with an empty message: named by its String form, never an empty parenthesis
  sanitizeAnswers = () => { throw new Error(""); };
  o.b.rendered.click();
  assert.equal((o.body.childNodes[0] as El).textContent, RENDER_FELL + " (Error).");
  assert.equal(paints, 3);
});

test("an open at a heading whose Rendered paint throws (the Slice 7 review's round 1): the heading is not spent over the fallback rows, so no \"No section named\" notice stands under the failure line of a section the file has; the Raw click keeps it pending, a Rendered click that throws again too; the healed Rendered click lands it (as the Raw preference's toggle does)", async (t) => {
  withFrames(t);
  sanitizeFails = "synthetic sanitizer failure";
  t.after(() => { sanitizeFails = null; sanitizeAnswers = null; });
  const o = await open(REPORT, t, SID, { at: { heading: "findings" } });   // DOC holds "## Findings"
  assert.equal(o.ctx.mode(), "raw", "the paint fell to the rows");
  assert.ok((o.body.childNodes[0] as El).matches("div.fileview-err"), "the failure line first");
  assert.equal(frames.length, 0, "no landing frame queued from the fallback paint (before: one, whose run found no #md-findings among the rows and raised the notice)");
  assert.equal(cardOf(o.body).querySelectorAll("#fileview-save-err").length, 0, "no notice bar: the failure line is the one notice");
  o.b.raw.click();
  assert.equal(frames.length, 0, "the Raw paint spends nothing either (a note's Raw view cannot judge)");
  o.b.rendered.click();   // still throwing
  assert.ok((o.body.childNodes[0] as El).matches("div.fileview-err"), "the line over the rows again");
  assert.equal(frames.length, 0); assert.equal(cardOf(o.body).querySelectorAll("#fileview-save-err").length, 0, "still no bar");
  sanitizeFails = null;
  o.b.rendered.click();
  assert.equal(o.ctx.mode(), "rendered", "healed");
  assert.equal(frames.length, 1, "the Rendered paint that stands queues the landing");
  const els = layRendered(o.body.querySelector(".fileview-md")!);
  flushFrames();
  assert.deepEqual(scrolls(els), [0, 1, 0, 0], "the section lands (before: the heading was spent, the healed paint rendered from the top with the false notice standing)");
  assert.equal(cardOf(o.body).querySelectorAll("#fileview-save-err").length, 0, "and no notice");
});

test("an open at a source offset whose Rendered paint throws (the Slice 7 review's round 1): the offset lands on the row holding it through the seam's own scrollToOffset, the spender reading mode() and not the pressed button; an offset past the end lands on the last row and its notice says \"showing the last line.\"", async (t) => {
  withFrames(t);
  sanitizeFails = "synthetic sanitizer failure";
  t.after(() => { sanitizeFails = null; sanitizeAnswers = null; });
  const o = await open(REPORT, t, SID, { at: { offset: DOC.indexOf("We recommend") } });
  assert.equal(o.ctx.mode(), "raw"); assert.equal(o.b.rendered.classList.contains("on"), true, "the Rendered button pressed over the rows (item 1)");
  assert.equal(frames.length, 1, "the offset is spent at the landing and scrolled the next frame");
  const rows = layRows(o.body.querySelector("code.hljs")!, DOC); flushFrames();
  assert.deepEqual(scrolls(rows), [0, 0, 0, 0, 0, 1], "the sixth row, the offset's line (before: nothing scrolled, the spender read the button, took the Rendered branch and found no box)");
  assert.deepEqual(rows[5].scrolledWith, { block: "center" });
  assert.equal(cardOf(o.body).querySelectorAll("#fileview-save-err").length, 0, "no notice: the offset is inside the text");
  // past the end: the last row, and the notice names a line, what shows, not a block
  o.fv.openFileView(REPORT, SID, { at: { offset: DOC.length + 50 } }); await settle();
  const body2 = doc.getElementById("romp-fileview")!.querySelector(".fileview-body")!;
  assert.ok((body2.childNodes[0] as El).matches("div.fileview-err"), "the failure line again");
  const rows2 = layRows(body2.querySelector("code.hljs")!, DOC); flushFrames();
  assert.deepEqual(scrolls(rows2), [0, 0, 0, 0, 0, 1], "the last row");
  assert.equal(cardOf(body2).querySelector("#fileview-save-err")?.textContent, "Offset " + (DOC.length + 50) + " is past the end of this file, which has " + DOC.length + " characters; showing the last line.", "the notice names what shows (before: \"showing the last block.\" over rows, with nothing scrolled)");
});

test("a fallback that throws too (the Slice 7 review's round 2; a bug, not a file: the render swap and the fallback's swap both throwing from a click) propagates as designed and leaves the record matching the body: the previous Rendered paint stands, mode() still answers \"rendered\" and the Comments panel's contentRoot rule finds the box (before: renderFell was recorded before the fallback swap, so mode() answered \"raw\", renderedImages() [] and the rule looked for code.hljs over a standing .fileview-md); a healed click paints again; over a standing fallback the line, the rows and the record stand too", async (t) => {
  const o = await open(REPORT, t);
  const { ctx, body } = o;
  assert.equal(ctx.mode(), "rendered"); assert.ok(body.querySelector(".fileview-md"), "the Rendered box is up");
  // every swap into the body throws: the render swap, then the fallback's (an own property shadows the stand-in's method)
  const swaps: string[] = [];
  const failEverySwap = (why: string) => { (body as any).replaceChildren = (...nodes: Array<El | Txt>) => { swaps.push(nodes.map((n) => (n instanceof El ? n.className : "#text")).join("+")); throw new Error(why + " " + swaps.length); }; };
  const healSwap = () => { delete (body as any).replaceChildren; };
  t.after(healSwap);
  failEverySwap("synthetic swap failure");
  assert.throws(() => o.b.rendered.click(), /synthetic swap failure 2/, "the fallback's own throw propagates out of the click (a second failure is a bug, not a file)");
  assert.deepEqual(swaps, ["fileview-md", "fileview-err+fileview-code"], "the render swap threw first, then the fallback's line and rows");
  assert.ok(body.querySelector(".fileview-md"), "the previous Rendered paint stands"); assert.equal(body.querySelector(".fileview-err"), null, "no failure line reached the body");
  assert.equal(ctx.mode(), "rendered", "mode() answers what the body shows (before: \"raw\" over the standing box)");
  assert.ok(body.querySelector(ctx.mode() === "rendered" ? ".fileview-md" : "code.hljs"), "the panel's contentRoot rule (file-comments.ts) finds the root the body holds");
  assert.equal(ctx.error(), null, "no pane: error() null"); assert.equal(paints, 1, "no hook fired: the pass ended at the throw");
  assert.equal(o.b.rendered.classList.contains("on"), true, "the button took the click before the paint (fmt.md is the person's choice)");
  // healed: the Rendered click paints
  healSwap();
  o.b.rendered.click();
  assert.equal(ctx.mode(), "rendered"); assert.ok(body.querySelector(".fileview-md")); assert.equal(paints, 2);
  // over a standing fallback (the sanitizer throwing: the line over rows) a click whose fallback throws too leaves the line, the rows and the record
  sanitizeFails = "synthetic sanitizer failure";
  t.after(() => { sanitizeFails = null; });
  o.b.rendered.click();
  assert.ok((body.childNodes[0] as El).matches("div.fileview-err") && (body.childNodes[1] as El).matches("div.fileview-code"), "the line over the rows"); assert.equal(ctx.mode(), "raw"); assert.equal(paints, 3);
  swaps.length = 0; failEverySwap("synthetic swap failure again");
  assert.throws(() => o.b.rendered.click(), /synthetic swap failure again 1/, "mdBlock threw before any swap; the fallback's swap is the one that threw");
  assert.deepEqual(swaps, ["fileview-err+fileview-code"]);
  assert.ok((body.childNodes[0] as El).matches("div.fileview-err") && (body.childNodes[1] as El).matches("div.fileview-code"), "the earlier fallback stands");
  assert.equal(ctx.mode(), "raw", "and its record with it"); assert.equal(paints, 3);
});

test("over a standing failure pane, a format click whose render swap and fallback swap both throw (the Slice 7 review's round 3; a bug, not a file) leaves error() answering the pane the body still shows: a note deleted on disk, the reload's 404 pane up with error() its words, every body swap made to throw, the Rendered click's throw propagates, the pane stands, no hook fires, and error() still answers the words (before: null, cleared before the pass, so the Comments panel's next pass at the same mtime would have said the view still showed the earlier text over a pane saying the file could not be read); the Raw click the same; a healed click paints and clears it", async (t) => {
  const o = await open(REPORT, t);
  const { ctx, body } = o;
  t.after(() => { disk[REPORT] = { bytes: DOC, type: "text/plain; charset=utf-8", mtimeNs: MT }; });
  delete disk[REPORT];
  ctx.reload(); await settle();
  const words = "no such file: " + REPORT;
  const pane = errBar(body)!;
  assert.ok(pane && pane.parentNode === body, "the pane is in the body"); assert.equal(ctx.error(), words, "error() the pane's words"); assert.equal(paints, 2);
  const mt = ctx.mtimeNs();
  // every swap into the body throws: the render swap, then the fallback's (an own property shadows the stand-in's method)
  const swaps: string[] = [];
  (body as any).replaceChildren = (...nodes: Array<El | Txt>) => { swaps.push(nodes.map((n) => (n instanceof El ? n.className : "#text")).join("+")); throw new Error("synthetic everyswap failure " + swaps.length); };
  const healSwap = () => { delete (body as any).replaceChildren; };
  t.after(healSwap);
  assert.throws(() => o.b.rendered.click(), /synthetic everyswap failure 2/, "the fallback's own throw propagates out of the click");
  assert.deepEqual(swaps, ["fileview-md", "fileview-err+fileview-code"], "the render swap threw first, then the fallback's line and rows");
  assert.equal(errBar(body), pane, "the pane still stands"); assert.equal(pane.parentNode, body); assert.equal(pane.textContent, words);
  assert.equal(paints, 2, "no hook fired: the pass ended at the throw"); assert.equal(ctx.mtimeNs(), mt, "the mtime unchanged");
  assert.equal(ctx.error(), words, "error() still answers the pane's words (before: null over the standing pane)");
  assert.equal(ctx.mode(), "rendered", "mode() is the view's word, as over the pane's own paint (the contract's designed answer)");
  assert.throws(() => o.b.raw.click(), /synthetic everyswap failure 4/, "the Raw click: the rows' swap, then the fallback's");
  assert.equal(ctx.error(), words, "the Raw click the same"); assert.equal(errBar(body), pane); assert.equal(paints, 2);
  // healed: the Rendered click paints the note and the record clears with the paint
  healSwap();
  o.b.rendered.click(); await settle();
  assert.ok(body.querySelector(".fileview-md"), "the note repaints"); assert.equal(errBar(body), null, "the pane went");
  assert.equal(ctx.error(), null, "error() null once content stands"); assert.equal(ctx.mode(), "rendered"); assert.equal(paints, 3);
});

test("a throw inside marked's own stage is named by its message alone (the Slice 7 review's round 2): marked 12 appends a bug-report sentence with its tracker's URL to every message its lexer, walkTokens or parser rethrow, and the RENDER_FELL line cuts it (before: \"(synthetic lexer failure\\nPlease report this to https://github.com/markedjs/marked.).\", a foreign URL and a request to report a romp file's failure to marked inside romp's own line); a throw whose message is nothing but that sentence is named by the error's name, as an empty message is; a message with a newline of its own is kept whole", async (t) => {
  const { RENDER_FELL } = await mod();
  const lexer = marked.Lexer.prototype as any;
  const lex = lexer.lex;
  lexer.lex = function () { throw new Error("synthetic lexer failure"); };   // the singleton's parse runs _Lexer.lex, which builds a lexer and calls this
  t.after(() => { lexer.lex = lex; });
  assert.throws(() => marked.parse("hello"), (e: unknown) => e instanceof Error && e.message === "synthetic lexer failure\nPlease report this to https://github.com/markedjs/marked.", "marked's onError appends the sentence before rethrowing: the cut is keyed on this text");
  const o = await open(REPORT, t);
  const { ctx, body } = o;
  const first = body.childNodes[0] as El;
  assert.ok(first.matches("div.fileview-err") && (body.childNodes[1] as El).matches("div.fileview-code"), "the line over the rows");
  assert.equal(first.textContent, RENDER_FELL + " (synthetic lexer failure).", "the message alone: marked's sentence and URL cut (before: both printed, the newline collapsed to a space on screen)");
  assert.equal(ctx.mode(), "raw"); assert.equal(paints, 1);
  // an Error with no message of its own thrown inside marked: the sentence is all there is, and the line names the error's name
  lexer.lex = function () { throw new Error(""); };
  o.b.rendered.click();
  assert.equal((body.childNodes[0] as El).textContent, RENDER_FELL + " (Error).", "never marked's sentence alone, never an empty parenthesis");
  assert.equal(paints, 2);
  // a message with a newline of its own is kept whole: the cut is the one sentence, not the first line
  lexer.lex = function () { throw new Error("first line\nsecond line"); };
  o.b.rendered.click();
  assert.equal((body.childNodes[0] as El).textContent, RENDER_FELL + " (first line\nsecond line).");
  assert.equal(paints, 3);
  // healed: the Rendered click renders
  lexer.lex = lex;
  o.b.rendered.click();
  assert.ok(body.querySelector(".fileview-md")); assert.equal(ctx.mode(), "rendered"); assert.equal(paints, 4);
});

// ── item 6 of Slice 7 of plans/markdown-viewer.md: an empty file says so ─────────────────────────────────────────────────
// A zero-byte file painted zero Raw rows or an empty Rendered box and nothing else: a blank pane with Edit shown, so nothing
// told the reader an empty file from a paint that had not happened. Now the text paint puts the EMPTY_FILE line, in the
// .fileview-err dress, ABOVE the block the view would paint, a sibling of the root and never inside code.hljs or classed
// fv-cl (the anchor map's rawIndex sees zero rows over "" and accepts them; the Rendered pairing sees no block); text() is ""
// and never null, Edit stays shown, the Outline button hides, error() is null and mode() follows the buttons; a reload that
// lands bytes repaints without the line, and one that lands "" again brings it back. The stub serves "" as a text/plain
// answer wearing "1", the kernel's own answer for a zero-byte file (tests/test_kernel_preview.py pins it). Before item 6: the
// body held the empty root alone (red at the first assertion over a git archive of the base with EMPTY_FILE stubbed).
const EMPTY_MD = ROOT + "/docs/empty.md";
const EMPTY_TXT = ROOT + "/notes/todo.txt";
const MT_E2 = "1757145600000000021";
const MT_E3 = "1757145600000000022";
/** The body's first child as the empty-file line: the exported sentence alone, in the pane dress, the body's own child, outside
 *  code.hljs, not a row, no button and no hint. */
const emptyLine = (fv: typeof import("./file-view"), body: El): El => {
  const first = body.childNodes[0];
  assert.ok(first instanceof El && first.matches("div.fileview-err"), "the body's first child is the line, in the pane dress (before item 6: the empty root alone)");
  assert.equal(first.textContent, fv.EMPTY_FILE, "the exported sentence, alone");
  assert.equal(first.parentNode, body, "the body's own child: a sibling of the root");
  assert.equal(first.closest("code.hljs"), null, "never inside code.hljs (rawIndex reads rows from the code root)");
  assert.equal(first.classList.contains("fv-cl"), false, "never a row");
  assert.equal(first.querySelectorAll("button").length, 0, "no button"); assert.equal(first.querySelectorAll(".fileview-err-hint").length, 0, "no hint row");
  return first;
};

test("an empty markdown file says so (Slice 7 of plans/markdown-viewer.md, item 6): the body's first child is the EMPTY_FILE line above the empty Rendered box, text() \"\" and never null, error() null, mode() rendered, Edit shown, the Outline hidden, one paint, no bar; the Raw click paints the line above the empty rows' root with mode() raw; a reload that lands bytes repaints without the line, and one that lands \"\" again brings it back", async (t) => {
  disk[EMPTY_MD] = { bytes: "", type: "text/plain; charset=utf-8", mtimeNs: MT };
  t.after(() => { delete disk[EMPTY_MD]; });
  const o = await open(EMPTY_MD, t);
  const { fv, ctx, body, b } = o;
  assert.equal(fv.EMPTY_FILE, "This file is empty.", "contract C5's text, the one constant with its own period: the line shows it alone");
  const line = emptyLine(fv, body);
  assert.equal(body.childNodes.length, 2, "the line and the root, nothing else");
  const root = body.childNodes[1];
  assert.ok(root instanceof El && root.matches("div.fileview-md"), "the empty Rendered box under the line");
  assert.equal(root.childNodes.length, 0, "empty: nothing to render");
  assert.equal(ctx.text(), "", "text() is the empty string, never null (null means not landed, to the seam and the panel)");
  assert.equal(ctx.error(), null, "error() null: the content, all none of it, shows; the line is not a pane in place of the file");
  assert.equal(ctx.mode(), "rendered", "mode() follows the buttons");
  assert.equal(ctx.mtimeNs(), MT, "the landing took the mtime: a text landing like any other");
  assert.equal(b.edit.hidden, false, "Edit shown: an empty file is editable (the gate reads the text type and the mtime)");
  assert.equal(o.wrap.querySelector(".fileview-outline-btn")!.hidden, true, "the Outline button hides: no heading");
  assert.equal(paints, 1, "one paint");
  assert.equal(errBar(body), line, "the card's first .fileview-err is the line in the body: no bar was raised");
  assert.deepEqual(cardRows(body), ["fileview-bar", "fileview-main"], "no notice bar: the line is in the body, not the one-bar row");
  assert.deepEqual(ctx.renderedImages(), [], "no figure");
  // the Raw click: the line above the rows' root, which holds zero rows
  b.raw.click();
  emptyLine(fv, body);
  assert.equal(body.childNodes.length, 2, "the line and the rows' root");
  const code = body.childNodes[1];
  assert.ok(code instanceof El && code.matches("div.fileview-code") && code.querySelector("code.hljs"), "the rows' root under the line, its code element where the anchor map and the reader's place read rows");
  assert.equal(code.querySelectorAll(".fv-cl").length, 0, "zero rows");
  assert.equal(ctx.mode(), "raw", "mode() follows the buttons"); assert.equal(ctx.text(), ""); assert.equal(ctx.error(), null);
  assert.equal(paints, 2); assert.equal(b.edit.hidden, false, "Edit still shown");
  assert.equal(o.wrap.querySelector(".fileview-outline-btn")!.hidden, true);
  // Rendered again: the line over the box
  b.rendered.click();
  emptyLine(fv, body);
  assert.ok((body.childNodes[1] as El).matches("div.fileview-md")); assert.equal(ctx.mode(), "rendered"); assert.equal(paints, 3);
  // a reload that lands bytes repaints without the line
  disk[EMPTY_MD] = { bytes: DOC, type: "text/plain; charset=utf-8", mtimeNs: MT_E2 };
  ctx.reload(); await settle();
  assert.equal(paints, 4, "the landing's paint");
  assert.equal(body.querySelector(".fileview-err"), null, "the line went with the bytes");
  assert.equal(body.childNodes.length, 1); assert.ok((body.childNodes[0] as El).matches("div.fileview-md"), "the box alone");
  assert.equal(ctx.text(), DOC); assert.equal(ctx.mtimeNs(), MT_E2); assert.equal(ctx.error(), null); assert.equal(b.edit.hidden, false);
  // and a reload that lands "" again (a session emptied the file) brings the line back
  disk[EMPTY_MD] = { bytes: "", type: "text/plain; charset=utf-8", mtimeNs: MT_E3 };
  ctx.reload(); await settle();
  assert.equal(paints, 5);
  emptyLine(fv, body);
  assert.equal(ctx.text(), "", "text() \"\" again"); assert.equal(ctx.mtimeNs(), MT_E3); assert.equal(ctx.mode(), "rendered");
});

test("an empty text file says so (Slice 7, item 6): a file with no Rendered view paints the line above the empty rows' root, mode() raw, text() \"\", error() null, Edit shown, no Outline button, one paint, no bar; a reload that lands bytes repaints without the line", async (t) => {
  disk[EMPTY_TXT] = { bytes: "", type: "text/plain; charset=utf-8", mtimeNs: MT };
  t.after(() => { delete disk[EMPTY_TXT]; });
  const o = await open(EMPTY_TXT, t);
  const { fv, ctx, body, b } = o;
  emptyLine(fv, body);
  assert.equal(body.childNodes.length, 2, "the line and the rows' root, nothing else");
  const code = body.childNodes[1];
  assert.ok(code instanceof El && code.matches("div.fileview-code") && code.querySelector("code.hljs"), "the empty rows' root under the line");
  assert.equal(code.querySelectorAll(".fv-cl").length, 0, "zero rows");
  assert.equal(ctx.mode(), "raw"); assert.equal(ctx.text(), ""); assert.equal(ctx.error(), null); assert.equal(ctx.mtimeNs(), MT);
  assert.equal(b.edit.hidden, false, "Edit shown"); assert.equal(o.wrap.querySelector(".fileview-outline-btn"), null, "a text file has no Outline button");
  assert.equal(paints, 1); assert.deepEqual(cardRows(body), ["fileview-bar", "fileview-main"], "no bar");
  disk[EMPTY_TXT] = { bytes: PY, type: "text/plain; charset=utf-8", mtimeNs: MT_E2 };
  ctx.reload(); await settle();
  assert.equal(paints, 2); assert.equal(body.querySelector(".fileview-err"), null, "the line went with the bytes");
  assert.equal(body.childNodes.length, 1); assert.ok((body.childNodes[0] as El).matches("div.fileview-code"));
  assert.equal(ctx.text(), PY); assert.equal(ctx.mtimeNs(), MT_E2); assert.equal(b.edit.hidden, false);
});

test("a target over an empty file lands nothing and throws nothing, and the line stands (Slice 7, item 6, beside the Slice 6 PR body's open ruling): an offset open of an empty note raises the offset notice as worded today (past the end of a file with 0 characters, a record) a frame after the paint with the line still above the box; a line open of an empty text file raises the same one-line notice at the landing, with no last line to show (the Slice 7 review's round 1: before, scrollToLine returned over zero rows and said nothing)", async (t) => {
  withFrames(t);
  disk[EMPTY_MD] = { bytes: "", type: "text/plain; charset=utf-8", mtimeNs: MT };
  disk[EMPTY_TXT] = { bytes: "", type: "text/plain; charset=utf-8", mtimeNs: MT };
  t.after(() => { delete disk[EMPTY_MD]; delete disk[EMPTY_TXT]; });
  const o = await open(EMPTY_MD, t, SID, { at: { offset: 3 } });
  emptyLine(o.fv, o.body);
  assert.equal(frames.length, 1, "the offset's frame is queued at the landing");
  flushFrames();
  assert.equal(errBar(o.body)?.textContent, "Offset 3 is past the end of this file, which has 0 characters; showing the last block.", "the notice bar's words as worded today (a record: the line in the body says what the offset found)");
  assert.equal(errBar(o.body)!.id, "fileview-save-err", "the bar, not the line: the card's first .fileview-err is the bar above the body");
  emptyLine(o.fv, o.body);
  assert.ok((o.body.childNodes[1] as El).matches("div.fileview-md"), "the landing threw nothing: no pane replaced the body");
  assert.equal(o.ctx.error(), null); assert.equal(o.ctx.text(), ""); assert.equal(paints, 1);
  o.fv.closeFileView();
  const u = await open(EMPTY_TXT, t, SID, { at: { line: 2 } });
  emptyLine(u.fv, u.body);
  assert.equal(frames.length, 0, "a line lands at once, no frame");
  assert.equal(errBar(u.body)?.textContent, "Line 2 is past the end of this file, which has 0 lines.", "the line's one-line notice, the offset's shape, stopping short of \"showing the last line\" since there is none (before: no notice at all, the line above the rows' root being the only word)");
  assert.equal(errBar(u.body)!.id, "fileview-save-err", "the bar above the body, not the line in it");
  assert.deepEqual(cardRows(u.body), ["fileview-bar", "fileview-err", "fileview-main"], "one notice");
  assert.equal(errBar(u.body)!.querySelectorAll("button").length, 0, "no button");
  emptyLine(u.fv, u.body);
  assert.ok((u.body.childNodes[1] as El).matches("div.fileview-code"), "the landing threw nothing: the line and the empty rows' root stand");
  assert.equal(u.ctx.error(), null); assert.equal(u.ctx.text(), ""); assert.equal(paints, 1);
  // the control over rows (a line past the end of a file WITH rows keeps its "showing the last line" tail) is the failures leg's
  // line-9999 scene: this stand-in parses no innerHTML, so it lays no rows at a landing (the Latin-1 target case's note above)
});

// ── item 6 of Slice 7 of plans/markdown-viewer.md, the review's round 1: a file whose only bytes are a byte order mark ───────
// The kernel serves such a file as one U+FEFF under Content-Length 3, the browser's UTF-8 decode strips that one character, and
// the view's text is "" as an empty file's is, so the text paint said "This file is empty.", untrue of the bytes on disk. The
// paint tells the two apart by the answer's byte count (the verdict's `bytes`, the kernel's Content-Length): UTF-8 bytes that
// decode to nothing and number more than zero are exactly the three of a BOM, and the line says so (BOM_ONLY_FILE) in the empty
// file's shape and place. The stub answers Content-Length as the kernel does and strips one leading U+FEFF as the browser does.
// Red over a git archive of 98859d061 at the first line's words (EMPTY_FILE there) with BOM_ONLY_FILE undefined.
const BOM_MD = ROOT + "/docs/bom.md";
const BOM_TXT = ROOT + "/notes/bom.txt";

test("a file whose only bytes are a byte order mark says so (Slice 7, item 6; the review's round 1): served as one U+FEFF under Content-Length 3, the body's first child is the BOM_ONLY_FILE line in the empty file's place above the empty Rendered box, text() \"\", error() null, Edit shown, no bar; the Raw click keeps it above the empty rows' root; a reload landing an empty body (Content-Length 0) paints EMPTY_FILE, one landing text after the mark paints no line; a .txt of the same bytes says the same above its rows' root", async (t) => {
  disk[BOM_MD] = { bytes: "\uFEFF", type: "text/plain; charset=utf-8", mtimeNs: MT };
  disk[BOM_TXT] = { bytes: "\uFEFF", type: "text/plain; charset=utf-8", mtimeNs: MT };
  t.after(() => { delete disk[BOM_MD]; delete disk[BOM_TXT]; });
  const o = await open(BOM_MD, t);
  const { fv, ctx, body, b } = o;
  assert.equal(fv.BOM_ONLY_FILE, "This file holds only a byte order mark.", "the sentence, in the empty line's shape (its own period)");
  const first = body.childNodes[0];
  assert.ok(first instanceof El && first.matches("div.fileview-err"), "the body's first child is the line, in the pane dress");
  assert.equal(first.textContent, fv.BOM_ONLY_FILE, "the true sentence (before: EMPTY_FILE, untrue of the three bytes on disk)");
  assert.equal(first.querySelectorAll("button").length, 0, "no button"); assert.equal(first.closest("code.hljs"), null); assert.equal(first.classList.contains("fv-cl"), false);
  assert.equal(body.childNodes.length, 2, "the line and the root");
  assert.ok((body.childNodes[1] as El).matches("div.fileview-md") && (body.childNodes[1] as El).childNodes.length === 0, "the empty Rendered box under it");
  assert.equal(ctx.text(), "", "text() is the view's text, the mark stripped by the browser's decode, never null");
  assert.equal(ctx.error(), null, "error() null: the content shows"); assert.equal(ctx.mode(), "rendered"); assert.equal(ctx.mtimeNs(), MT);
  assert.equal(b.edit.hidden, false, "Edit shown: a save writes the three bytes back through the doors' BOM rule (item 4)");
  assert.equal(paints, 1); assert.deepEqual(cardRows(body), ["fileview-bar", "fileview-main"], "no bar: the line is in the body");
  b.raw.click();
  assert.equal((body.childNodes[0] as El).textContent, fv.BOM_ONLY_FILE, "the Raw click keeps the line"); assert.ok((body.childNodes[1] as El).matches("div.fileview-code"), "above the rows' root");
  assert.equal(body.querySelectorAll(".fv-cl").length, 0, "zero rows"); assert.equal(ctx.mode(), "raw");
  b.rendered.click();
  // a session emptied the file: zero bytes, and the empty file's words
  disk[BOM_MD] = { bytes: "", type: "text/plain; charset=utf-8", mtimeNs: MT_E2 };
  ctx.reload(); await settle();
  assert.equal(paints, 4); assert.equal((body.childNodes[0] as El).textContent, fv.EMPTY_FILE, "an empty body: the empty file's line (Content-Length 0)"); assert.equal(ctx.mtimeNs(), MT_E2);
  // a session wrote text after the mark: the decode strips the mark, the text paints, no line
  disk[BOM_MD] = { bytes: "\uFEFF" + DOC, type: "text/plain; charset=utf-8", mtimeNs: MT_E3 };
  ctx.reload(); await settle();
  assert.equal(paints, 5); assert.equal(body.querySelector(".fileview-err"), null, "no line over text"); assert.equal(ctx.text(), DOC, "the view's text without the mark, as the browser hands it");
  assert.ok((body.childNodes[0] as El).matches("div.fileview-md"), "the box alone"); assert.equal(body.childNodes.length, 1, "and nothing else");
  // a text file of the same bytes: the line above the empty rows' root
  fv.closeFileView();
  const u = await open(BOM_TXT, t);
  assert.equal((u.body.childNodes[0] as El).textContent, u.fv.BOM_ONLY_FILE, "the .txt says the same");
  assert.ok((u.body.childNodes[1] as El).matches("div.fileview-code") && u.body.querySelectorAll(".fv-cl").length === 0, "above the empty rows' root");
  assert.equal(u.ctx.mode(), "raw"); assert.equal(u.ctx.text(), ""); assert.equal(u.b.edit.hidden, false);
});

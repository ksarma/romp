// The reader's place across a paint of the file viewer's body (reader-place.ts), run FOR REAL over openFileView and
// openUrlView. A paint that replaces the body's children (the Rendered/Raw switch) left the numeric scrollTop standing
// over the other view's layout, and a text-size step (textSizeControl) reflowed the text under it, so the passage under
// the reader's eye changed with every switch and every step: the Raw view of a note is taller than its Rendered view,
// and a round trip that started on paragraph 40 came back on paragraph 50. Now every text paint reads the top-visible
// block before the swap and seats the same block at the same height after it (readPlace, seatPlace), and a size step
// reads before the size is applied and seats after.
//
// The viewer runs against a DOM stand-in (the text-size suite's: a tree, attributes, bubbling events, a small selector
// matcher, localStorage, a fetch answering the kernel's headers) given a few more things. An innerHTML that PARSES markup
// into the tree, since codeBlock's rows and mdBlock's fence pass write it, with tag names upper-cased as a DOM's are (the
// width stamp reads TABLE); a deterministic layout, read off a block's or a row's place and the body's scrollTop: the body
// is 600px tall with its top edge at 0; a top-level child of .fileview-md is `pct` px tall (100 at the default size, 115
// after one A+ press) stacked from 14px, a table three times that until the width stamp reaches it; a Raw row k is a
// fifth of `pct` (20px, then 23) stacked from 10px; nothing else has a box; scrollTop clamps to the content's height as
// a browser's does, and scrollIntoView scrolls the body so the element's top meets its edge. The browser's next frame is
// a queue the test flushes (the fragment landing rides one), and its ResizeObserver a stand-in whose report the test
// fires (the width stamp waits for one). The sanitizer (md-sanitize.ts) cannot run here: DOMPurify has no DOM under the
// stand-in (isSupported is false) and mdBlock would fall back to one text node, so its sanitize is stood in for by the
// same parse of marked's markup, which is what the sanitizer hands back for a note carrying nothing it removes. The
// sanitizer's own rules are its own suite's business; the pairing rule this suite exercises reads elements and text.
// Synthetic fixtures throughout: a notes-api world, a note of sixty three-line paragraphs (block k starts at line 4k),
// one with a heading at block 50, one with a table at block 30.
import { test, after, type TestContext } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import DOMPurify from "dompurify";

const web = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const VIEW = web("file-view.ts");
const OPEN_FN = VIEW.split("export function openFileView")[1].split("function offersDownload")[0];
const URL_FN = (VIEW.split("export function openUrlView")[1] || "").split("// Kick the browser's downloader")[0];

// ── the layout ─────────────────────────────────────────────────────────────────────────────────────
const VIEWPORT = 600;      // the body's height
const MD_PAD = 14;         // the rendered root's inset above its first block and below its last
const RAW_PAD = 10;        // the Raw view's inset above its first row and below its last
/** The text size in force over `el`, read off the viewer root's data-fv-text (textSizeControl writes it): 100 by default. */
const pctOf = (el: El): number => { const root = el.closest(".fileview"); return root ? parseInt(root.getAttribute("data-fv-text") || "100", 10) : 100; };
const blockH = (pct: number) => pct;
const rowH = (pct: number) => pct / 5;

// ── a DOM stand-in: the members the viewer touches, with a tree, bubbling events, parsed markup and boxes ──
class Ev {
  target: El | null = null;
  currentTarget: El | null = null;
  defaultPrevented = false;
  stopped = false;
  ctrlKey: boolean; metaKey: boolean; deltaY: number; deltaMode: number; key: string;
  constructor(public type: string, init: { ctrlKey?: boolean; metaKey?: boolean; deltaY?: number; deltaMode?: number; key?: string } = {}) {
    this.ctrlKey = !!init.ctrlKey; this.metaKey = !!init.metaKey;
    this.deltaY = init.deltaY ?? 0; this.deltaMode = init.deltaMode ?? 0; this.key = init.key ?? "";
  }
  preventDefault(): void { this.defaultPrevented = true; }
  stopPropagation(): void { this.stopped = true; }
}
type Listener = (ev: Ev) => void;
type Part = { tag: string; id: string; classes: string[]; attrs: Array<[string, string | null]>; known: boolean };
const kebab = (k: string) => k.replace(/[A-Z]/g, (c) => "-" + c.toLowerCase());
/** One compound selector (`tag#id.class[attr="v"]`); a shape the matcher does not know fits nothing. */
function part(s: string): Part {
  const m = /^([a-zA-Z][\w-]*|\*)?(#[\w-]+)?((?:\.[\w-]+)*)((?:\[[^\]]+\])*)$/.exec(s);
  if (!m) return { tag: "", id: "", classes: [], attrs: [], known: false };
  const attrs: Array<[string, string | null]> = [];
  let known = true;
  for (const a of m[4].match(/\[[^\]]+\]/g) || []) {
    const am = /^\[([\w-]+)(?:="([^"]*)")?\]$/.exec(a);
    if (am) attrs.push([am[1], am[2] ?? null]); else known = false;
  }
  return { tag: (m[1] || "").toLowerCase(), id: m[2] ? m[2].slice(1) : "", classes: (m[3].match(/\.[\w-]+/g) || []).map((c) => c.slice(1)), attrs, known };
}
/** A text node: nodeType 3 and its data, as the DOM has it (reader-place reads text nodes by nodeType). */
class Txt {
  readonly nodeType = 3;
  parentNode: El | null = null;
  constructor(public data: string) {}
  get textContent(): string { return this.data; }
}
const VOID = new Set(["br", "hr", "img", "input", "meta", "link", "area", "base", "col", "embed", "source", "track", "wbr"]);
const NAMED: Record<string, string> = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'", nbsp: " " };
const decodeEntities = (s: string) => s.replace(/&(#x[0-9a-fA-F]+|#\d+|[a-zA-Z]+);/g, (m, e: string) => {
  if (e[0] === "#") return String.fromCodePoint(parseInt(e[1] === "x" || e[1] === "X" ? e.slice(2) : e.slice(1), e[1] === "x" || e[1] === "X" ? 16 : 10));
  return e in NAMED ? NAMED[e] : m;
});
const esc = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
class El {
  readonly nodeType = 1;
  parentNode: El | null = null;
  childNodes: Array<El | Txt> = [];
  title = ""; hidden = false; type = ""; disabled = false; tabIndex = -1;
  href = ""; target = ""; rel = ""; spellcheck = true; value = ""; src = ""; alt = ""; download = "";
  style: { [k: string]: unknown; setProperty(k: string, v: string): void } = { setProperty: (k: string, v: string) => { this.style[k] = v; } };
  onclick: ((ev: Ev) => void) | null = null;
  private attrs = new Map<string, string>();
  private listeners: Array<{ type: string; fn: Listener; once: boolean; passive: boolean | undefined }> = [];
  private _scrollTop = 0;
  readonly tagName: string;
  constructor(tag: string) { this.tagName = tag.toUpperCase(); }   // as a DOM reports an HTML element's
  get id(): string { return this.attrs.get("id") ?? ""; }
  set id(v: string) { this.attrs.set("id", v); }
  get className(): string { return this.attrs.get("class") ?? ""; }
  set className(v: string) { this.attrs.set("class", v.trim()); }
  private get classes(): string[] { return this.className.split(/\s+/).filter(Boolean); }
  classList = {
    add: (...c: string[]) => { const s = new Set(this.classes); for (const x of c) s.add(x); this.className = [...s].join(" "); },
    remove: (...c: string[]) => { const s = new Set(this.classes); for (const x of c) s.delete(x); this.className = [...s].join(" "); },
    toggle: (c: string, on?: boolean): boolean => { const want = on ?? !this.classes.includes(c); if (want) this.classList.add(c); else this.classList.remove(c); return want; },
    contains: (c: string) => this.classes.includes(c),
  };
  /** data-* through dataset, the way the viewer writes its root attribute (camelCase to kebab-case, as the DOM does). */
  dataset: Record<string, string | undefined> = new Proxy({} as Record<string, string | undefined>, {
    get: (_, k) => this.attrs.get("data-" + kebab(String(k))),
    set: (_, k, v) => { this.attrs.set("data-" + kebab(String(k)), String(v)); return true; },
    has: (_, k) => this.attrs.has("data-" + kebab(String(k))),
    deleteProperty: (_, k) => { this.attrs.delete("data-" + kebab(String(k))); return true; },
  });
  get textContent(): string { return this.childNodes.map((c) => c.textContent).join(""); }
  set textContent(v: string) { this.replaceChildren(...(v === "" ? [] : [new Txt(v)])); }
  /** Element children only, in order. */
  get children(): El[] { return this.childNodes.filter((c): c is El => c instanceof El); }
  get childElementCount(): number { return this.children.length; }
  get isConnected(): boolean { let n: El = this; while (n.parentNode) n = n.parentNode; return n === docBody; }
  private adopt(c: El | Txt): void { if (c instanceof El) c.remove(); c.parentNode = this; }
  appendChild<T extends El | Txt>(c: T): T { this.adopt(c); this.childNodes.push(c); return c; }
  prepend(...cs: Array<El | Txt>): void { for (const c of cs) this.adopt(c); this.childNodes.unshift(...cs); }
  insertBefore<T extends El | Txt>(c: T, ref: El | Txt | null): T {
    if (ref && !this.childNodes.includes(ref)) throw new Error("insertBefore: the reference node is not a child of this node");
    this.adopt(c);
    const i = ref ? this.childNodes.indexOf(ref) : -1;
    if (i < 0) this.childNodes.push(c); else this.childNodes.splice(i, 0, c);
    return c;
  }
  replaceChildren(...cs: Array<El | Txt>): void {
    for (const c of this.childNodes) c.parentNode = null;
    this.childNodes = [];
    for (const c of cs) this.adopt(c);
    this.childNodes = [...cs];
  }
  remove(): void {
    const p = this.parentNode;
    if (!p) return;
    const i = p.childNodes.indexOf(this);
    if (i >= 0) p.childNodes.splice(i, 1);
    this.parentNode = null;
  }
  contains(n: El | null): boolean { for (let x: El | null = n; x; x = x.parentNode) if (x === this) return true; return false; }
  setAttribute(k: string, v: string): void { this.attrs.set(k, v); }
  removeAttribute(k: string): void { this.attrs.delete(k); }
  getAttribute(k: string): string | null { return this.attrs.get(k) ?? null; }
  hasAttribute(k: string): boolean { return this.attrs.has(k); }
  addEventListener(type: string, fn: Listener, opts?: boolean | { once?: boolean; passive?: boolean; capture?: boolean }): void {
    this.listeners.push({ type, fn, once: typeof opts === "object" && !!opts.once, passive: typeof opts === "object" ? opts.passive : undefined });
  }
  removeEventListener(type: string, fn: Listener): void { this.listeners = this.listeners.filter((l) => !(l.type === type && l.fn === fn)); }
  /** Bubble `ev` from this element to the root: each element's listeners in registration order, then its onclick for a click. */
  dispatchEvent(ev: Ev): boolean {
    ev.target = this;
    for (let n: El | null = this; n && !ev.stopped; n = n.parentNode) {
      ev.currentTarget = n;
      for (const l of n.listeners.slice()) {
        if (l.type !== ev.type) continue;
        if (l.once) n.listeners = n.listeners.filter((x) => x !== l);
        l.fn.call(n, ev);
      }
      if (ev.type === "click" && n.onclick) n.onclick(ev);
    }
    return !ev.defaultPrevented;
  }
  click(): void { this.dispatchEvent(new Ev("click")); }
  focus(): void { doc.activeElement = this; }
  /** `{ block: "start" }`, the landing's call (scrollToFragment): the body scrolls so this element's top meets its edge. */
  scrollIntoView(): void { const body = this.closest(".fileview-body"); const b = layoutOf(this); if (body && b) body.scrollTop += b.top; }
  private fits(p: Part): boolean {
    if (!p.known) return false;
    if (p.tag && p.tag !== "*" && p.tag !== this.tagName.toLowerCase()) return false;
    if (p.id && p.id !== this.id) return false;
    if (!p.classes.every((c) => this.classes.includes(c))) return false;
    return p.attrs.every(([a, v]) => this.attrs.has(a) && (v === null || this.attrs.get(a) === v));
  }
  /** Comma groups of descendant chains, each link a compound. */
  matches(sel: string): boolean {
    return sel.split(",").some((group) => {
      const chain = group.trim().split(/\s+/).filter(Boolean).map(part);
      if (!chain.length || !this.fits(chain[chain.length - 1])) return false;
      let k = chain.length - 2;
      for (let a = this.parentNode; a && k >= 0; a = a.parentNode) if (a.fits(chain[k])) k--;
      return k < 0;
    });
  }
  closest(sel: string): El | null { for (let n: El | null = this; n; n = n.parentNode) if (n.matches(sel)) return n; return null; }
  querySelectorAll(sel: string): El[] {
    const out: El[] = [];
    const walk = (n: El) => { for (const c of n.children) { if (c.matches(sel)) out.push(c); walk(c); } };
    walk(this);
    return out;
  }
  querySelector(sel: string): El | null { return this.querySelectorAll(sel)[0] ?? null; }
  // ── markup in and out: codeBlock and the fence pass write innerHTML, wrapCodeLines reads it back ──
  get innerHTML(): string { return this.childNodes.map(outerHTML).join(""); }
  set innerHTML(html: string) {
    this.replaceChildren();
    let cur: El = this;
    const re = /<!--[\s\S]*?-->|<\/?([a-zA-Z][\w-]*)([^>]*)>|([^<]+)/g;   // a comment is no node the pairing counts (nodeType 8 in a DOM)
    let m: RegExpExecArray | null;
    while ((m = re.exec(html))) {
      if (m[0].startsWith("<!--")) continue;
      if (m[3] !== undefined) { cur.appendChild(new Txt(decodeEntities(m[3]))); continue; }
      const tag = m[1].toUpperCase();
      if (m[0][1] === "/") { if (cur !== this && cur.tagName === tag && cur.parentNode) cur = cur.parentNode; continue; }
      const el = new El(tag);
      const attrRe = /([\w-]+)(?:="([^"]*)")?/g; let a: RegExpExecArray | null;
      while ((a = attrRe.exec(m[2]))) el.setAttribute(a[1], a[2] === undefined ? "" : decodeEntities(a[2]));
      cur.appendChild(el);
      if (!VOID.has(tag.toLowerCase()) && !m[2].endsWith("/")) cur = el;   // an unclosed tag nests what follows, as a browser's parser does
    }
  }
  attrList(): Array<[string, string]> { return [...this.attrs]; }
  // ── the layout ──
  get clientHeight(): number { return this.classList.contains("fileview-body") ? VIEWPORT : 0; }
  get scrollHeight(): number {
    if (!this.classList.contains("fileview-body")) return 0;
    const pct = pctOf(this);
    const md = this.querySelector(".fileview-md");
    if (md) return 2 * MD_PAD + md.children.reduce((sum, k) => sum + heightOf(k, pct), 0);
    const code = this.querySelector("code.hljs");
    if (code) return 2 * RAW_PAD + rowH(pct) * code.children.length;
    return 0;
  }
  get scrollTop(): number { return Math.max(0, Math.min(this._scrollTop, this.scrollHeight - this.clientHeight)); }
  set scrollTop(v: number) { this._scrollTop = Math.max(0, Math.min(v, this.scrollHeight - this.clientHeight)); }
  getBoundingClientRect(): { top: number; bottom: number; left: number; right: number; width: number; height: number } {
    const b = layoutOf(this);
    return b ? { top: b.top, bottom: b.top + b.height, left: 0, right: 0, width: 0, height: b.height } : { top: 0, bottom: 0, left: 0, right: 0, width: 0, height: 0 };
  }
}
function outerHTML(n: El | Txt): string {
  if (n instanceof Txt) return esc(n.data);
  const tag = n.tagName.toLowerCase();
  const open = "<" + tag + n.attrList().map(([k, v]) => " " + k + '="' + esc(v).replace(/"/g, "&quot;") + '"').join("") + ">";
  return VOID.has(tag) ? open : open + n.childNodes.map(outerHTML).join("") + "</" + tag + ">";
}
/** A top-level block's height: `pct` px, and three times that for a table the width stamp has not reached (watchBodyWidth
 *  sets --fv-body-w on a root's tables; until it does, a wide table lays out at its columns' width and wraps taller). */
const heightOf = (el: El, pct: number): number => (el.tagName === "TABLE" && el.style["--fv-body-w"] === undefined ? 3 * blockH(pct) : blockH(pct));
/** Where `el` stands: the body itself, a top-level block of the rendered root, or a Raw row; nothing else has a box. */
function layoutOf(el: El): { top: number; height: number } | null {
  if (el.classList.contains("fileview-body")) return { top: 0, height: VIEWPORT };
  const p = el.parentNode;
  const body = el.closest(".fileview-body");
  if (!p || !body) return null;
  const pct = pctOf(el);
  if (p.classList.contains("fileview-md") && p.parentNode === body) {
    let top = MD_PAD;
    for (const k of p.children) { if (k === el) break; top += heightOf(k, pct); }
    return { top: top - body.scrollTop, height: heightOf(el, pct) };
  }
  if (el.classList.contains("fv-cl") && p.tagName === "CODE" && p.classList.contains("hljs")) return { top: RAW_PAD + rowH(pct) * p.children.indexOf(el) - body.scrollTop, height: rowH(pct) };
  return null;
}
const docBody = new El("body");
const docKeys: Listener[] = [];                  // the viewer's document keydown handlers, one per open
const doc = {
  body: docBody,
  activeElement: null as El | null,
  createElement: (tag: string) => new El(tag),
  createTextNode: (s: string) => new Txt(s),
  getElementById: (id: string): El | null => docBody.querySelector("#" + id),
  querySelectorAll: (sel: string): El[] => docBody.querySelectorAll(sel),
  addEventListener: (type: string, fn: Listener) => { if (type === "keydown") docKeys.push(fn); },
  removeEventListener: (type: string, fn: Listener) => { const i = docKeys.indexOf(fn); if (i >= 0) docKeys.splice(i, 1); },
};
const win: any = new EventTarget();
win.parent = win;
win.confirm = () => true;
win.getSelection = () => null;
win.postMessage = () => { /* the quote seed: nothing selects here */ };
(globalThis as any).window = win;
(globalThis as any).document = doc;
const store = new Map<string, string>();
(globalThis as any).localStorage = {
  getItem: (k: string) => (store.has(k) ? store.get(k)! : null),
  setItem: (k: string, v: string) => { store.set(k, String(v)); },
  removeItem: (k: string) => { store.delete(k); },
};
// the browser's next frame, as a queue the test flushes: the fragment landing rides one (file-view.ts scrollToFragment)
const frames: Array<() => void> = [];
(globalThis as any).requestAnimationFrame = (fn: () => void): number => frames.push(fn);
const flushFrames = () => { for (const fn of frames.splice(0)) fn(); };
// the browser's ResizeObserver, as a stand-in whose report the test fires: the width stamp (watchBodyWidth) waits for one
type Report = Array<{ contentRect: { width: number } }>;
const observers: Array<{ cb: (entries: Report) => void }> = [];
class ObserverStandIn {
  constructor(public cb: (entries: Report) => void) { observers.push(this); }
  observe(_target: El): void { /* the report is the test's to fire */ }
  disconnect(): void { const i = observers.indexOf(this); if (i >= 0) observers.splice(i, 1); }
}
(globalThis as any).ResizeObserver = ObserverStandIn;
/** The body's content width, reported to the viewer's watch as the browser reports it once the body has a layout. */
const reportWidth = (w: number) => { const ro = observers[observers.length - 1]; assert.ok(ro, "the viewer watches its body"); ro!.cb([{ contentRect: { width: w } }]); };

// ── the sanitizer stood in for (the header says why): the same parse of marked's markup, into the tree ──
const purify = DOMPurify as unknown as { isSupported: boolean; sanitize?: (dirty: string) => unknown; addHook?: (...a: unknown[]) => void };
assert.equal(purify.isSupported, false, "no DOM for DOMPurify under the stand-in: mdBlock's sanitize is stood in for by a parse of marked's markup");
purify.sanitize = (dirty: string) => { const b = new El("body"); b.innerHTML = String(dirty); return b; };
purify.addHook = () => { /* the colour-only style hook rides the sanitizer that is not running */ };
after(() => { delete purify.sanitize; delete purify.addHook; });

// ── fixtures: a notes-api world, synthetic throughout ──────────────────────────────────────────────
const SID = "77777777-8888-9999-aaaa-bbbbbbbbbbbb";
const ROOT = "/tmp/notes-api";
const REPORT = ROOT + "/docs/report.md";
const NOTES = ROOT + "/docs/notes.md";
const FIG = ROOT + "/docs/fig.svg";
const SECTIONED = ROOT + "/docs/sections.md";
const HREF = "http://notes-api.test/reports/run-1/evidence.md";
const HREF_SECTIONS = "http://notes-api.test/reports/run-1/sections.md";
const HREF_TABLED = "http://notes-api.test/reports/run-1/tables.md";
const FMT_KEY = /const FMT_KEY = "([^"]+)";/.exec(VIEW)![1];   // the stored Rendered/Raw preference's key
const MT = "1700000000000000000";
const PARA = (k: number) => `Paragraph ${k}, line one of three.\nParagraph ${k}, line two.\nParagraph ${k}, line three.`;
const paras = (a: number, b: number) => Array.from({ length: b - a + 1 }, (_, i) => PARA(a + i)).join("\n\n");
/** Sixty three-line paragraphs: block k is lines 4k to 4k+2, with a blank line after it. 239 Raw rows. */
const NOTE = paras(0, 59) + "\n";
/** Thirty paragraphs, two html blocks with no text between them, thirty more: a pairing the place keeper declines. */
const TWO_HTML = paras(0, 29) + "\n\n<p>Html A, a raw paragraph.</p>\n\n<p>Html B, another.</p>\n\n" + paras(30, 59) + "\n";
/** Fifty paragraphs, a heading (block 50, line 200, id md-results), nine more: a deep link's landing place. 237 Raw rows. */
const SECTIONS = paras(0, 49) + "\n\n## Results\n\n" + paras(51, 59) + "\n";
/** Thirty paragraphs, a four-line table (block 30, lines 120 to 123), twenty-nine more: block k after it starts at line 4k + 1. */
const TABLED = paras(0, 29) + "\n\n| a | b |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |\n\n" + paras(31, 59) + "\n";
/** One hundred lines of XML, no blank line: one html block to the markdown lexer. */
const SVG_XML = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">\n' + Array.from({ length: 98 }, (_, k) => `  <rect x="${k}" y="${k}" width="1" height="1"/>`).join("\n") + "\n</svg>\n";
type Served = { bytes: string | Uint8Array; type: string };
const disk: Record<string, Served> = {
  [REPORT]: { bytes: NOTE, type: "text/plain; charset=utf-8" },
  [NOTES]: { bytes: TWO_HTML, type: "text/plain; charset=utf-8" },
  [FIG]: { bytes: SVG_XML, type: "image/svg+xml" },
  [SECTIONED]: { bytes: SECTIONS, type: "text/plain; charset=utf-8" },
};
// The fetches the viewer makes: the kernel's /file (Content-Type is its verdict), its /version, and a same-origin
// document for the URL viewer, answered as a real Response so the streamed, capped read runs as it does in a browser.
(globalThis as any).fetch = (url: string) => {
  if (url.startsWith("/version")) return Promise.resolve({ json: () => Promise.resolve({ fileEditing: true }) });
  if (/^https?:/.test(url)) return Promise.resolve(new Response(url.includes("sections.md") ? SECTIONS : url.includes("tables.md") ? TABLED : NOTE, { status: 200, headers: { "Content-Type": "text/markdown; charset=utf-8" } }));
  const p = decodeURIComponent((/[?&]path=([^&]*)/.exec(url) || [])[1] || "");
  const f = disk[p];
  const headers = { get: (h: string) => (f ? (h === "Content-Type" ? f.type : h === "X-Romp-Mtime-Ns" ? MT : h === "X-Romp-Text-Utf8" ? "1" : null) : null) };
  if (!f) return Promise.resolve({ ok: false, status: 404, headers, text: () => Promise.resolve("no such file: " + p) });
  return Promise.resolve({
    ok: true, status: 200, headers,
    text: () => Promise.resolve(String(f.bytes)),
    blob: () => Promise.resolve(new Blob([f.bytes as unknown as BlobPart], { type: f.type })),
  });
};
/** Let every pending promise chain run: the fetch settles, a blob decodes. */
const settle = async () => { for (let i = 0; i < 8; i++) await new Promise<void>((r) => setImmediate(r)); };

let bound: Promise<typeof import("./file-view")> | null = null;
function view(): Promise<typeof import("./file-view")> {
  if (!bound) bound = import("./file-view").then((fv) => { fv.initFileView(() => { /* the WS poster: nothing asks the kernel here */ }); return fv; });
  return bound;
}
type Card = { fv: typeof import("./file-view"); root: El; body: El; down: El; up: El; btn: (label: string) => El };
/** The card up now, with the size buttons held by reference (they are built once per open). */
function card(fv: typeof import("./file-view")): Card {
  const wrap = doc.getElementById("romp-fileview");
  assert.ok(wrap, "a viewer is up");
  const root = wrap!.children[0];
  assert.equal(root.className, "fileview");
  const body = root.children[root.children.length - 1];
  assert.equal(body.className, "fileview-body");
  const acts = root.children[0].children.find((c) => c.classList.contains("fileview-acts"))!;
  const btn = (label: string) => { const b = acts.children.find((c) => c.tagName === "BUTTON" && c.textContent === label); assert.ok(b, "the " + label + " button"); return b!; };
  return { fv, root, body, down: btn("A−"), up: btn("A+"), btn };
}
/** Open `p` for the fixture session and let the bytes land. The stored size and format are cleared with the card. */
async function openFile(t: TestContext, p: string): Promise<Card> {
  const fv = await view();
  fv.openFileView(p, SID);
  t.after(() => { fv.closeFileView(); store.clear(); });
  await settle();
  return card(fv);
}
async function openUrl(t: TestContext): Promise<Card> {
  const fv = await view();
  fv.openUrlView(HREF);
  t.after(() => { fv.closeFileView(); store.clear(); });
  await settle();
  return card(fv);
}
// what the reader sees, read off the boxes alone: the first block or row whose box ends below the body's top edge
const blocks = (o: Card): El[] => { const md = o.body.querySelector(".fileview-md"); assert.ok(md, "the Rendered view is up"); return md!.children; };
const rows = (o: Card): El[] => { const code = o.body.querySelector("code.hljs"); assert.ok(code, "a code view is up"); return code!.children; };
const topBlock = (o: Card): number => blocks(o).findIndex((c) => c.getBoundingClientRect().bottom > 0);
const topRow = (o: Card): number => rows(o).findIndex((r) => r.getBoundingClientRect().bottom > 0);
const blockTop = (o: Card, k: number): number => blocks(o)[k].getBoundingClientRect().top;
const rowTop = (o: Card, k: number): number => rows(o)[k].getBoundingClientRect().top;
const size = (o: Card): string | null => o.root.getAttribute("data-fv-text");

// ── the Rendered/Raw switch ────────────────────────────────────────────────────────────────────────

test("the Rendered/Raw switch keeps the block at the body's top edge: paragraph 40 to its first row and back, where the numeric scrollTop had put paragraph 50 on top; a body at its top stays at its top", async (t) => {
  const o = await openFile(t, REPORT);
  assert.equal(blocks(o).length, 60, "the sixty paragraphs rendered as sixty top-level blocks");
  assert.equal(o.body.scrollTop, 0);
  o.btn("Raw").click();
  assert.equal(rows(o).length, 239, "the Raw view: one row per line");
  assert.equal(o.body.scrollTop, 0, "at the top before, at the top after");
  o.btn("Rendered").click();
  assert.equal(o.body.scrollTop, 0);
  o.body.scrollTop = 4014;                                  // 14 + 100 * 40: paragraph 40's top edge at the body's
  assert.equal(topBlock(o), 40); assert.equal(blockTop(o, 40), 0);
  o.btn("Raw").click();
  assert.equal(o.body.children[0].className, "fileview-code", "the Raw view is up");
  assert.equal(o.body.scrollTop, 3210, "10 + 20 * 160: paragraph 40's first line (row 160) at the edge, not row 200 (paragraph 50) where 4014 stood");
  assert.equal(topRow(o), 160); assert.equal(rowTop(o, 160), 0);
  o.btn("Rendered").click();
  assert.equal(o.body.scrollTop, 4014, "and back to the pixel");
  assert.equal(topBlock(o), 40); assert.equal(blockTop(o, 40), 0);
});

test("partway into a block, the depth is kept as a fraction of the block's height in the other view (50 of 100px into paragraph 40 is 30 of its three rows' 60px), and the round trip returns exactly", async (t) => {
  const o = await openFile(t, REPORT);
  o.body.scrollTop = 4064;
  assert.equal(topBlock(o), 40); assert.equal(blockTop(o, 40), -50);
  o.btn("Raw").click();
  assert.equal(o.body.scrollTop, 3240, "10 + 20 * 160 + 30");
  assert.equal(rowTop(o, 160), -30, "the block's first row 30px above the edge: the second row is the one at the edge");
  assert.equal(topRow(o), 161);
  o.btn("Rendered").click();
  assert.equal(o.body.scrollTop, 4064);
  assert.equal(blockTop(o, 40), -50);
});

test("a document opened from a link keeps the place across its Rendered/Raw switch the same way", async (t) => {
  const o = await openUrl(t);
  assert.equal(blocks(o).length, 60);
  o.body.scrollTop = 4014;
  o.btn("Raw").click();
  assert.equal(o.body.scrollTop, 3210);
  assert.equal(topRow(o), 160);
  o.btn("Rendered").click();
  assert.equal(o.body.scrollTop, 4014);
  assert.equal(topBlock(o), 40);
});

// ── the text-size step ─────────────────────────────────────────────────────────────────────────────

test("a text-size step keeps the block under the reader's eye at the same fraction of its new height, in Rendered, in Raw and in the SVG Source view; the step back returns", async (t) => {
  const o = await openFile(t, REPORT);
  o.body.scrollTop = 4064;                                  // 50 of paragraph 40's 100px
  o.up.click();
  assert.equal(size(o), "115");
  assert.equal(blockTop(o, 40), -57.5, "half of the block's 115px above the edge, as half of its 100px was");
  assert.equal(o.body.scrollTop, 4671.5);
  assert.equal(topBlock(o), 40);
  o.down.click();
  assert.equal(o.body.scrollTop, 4064, "back at the default size, back to the pixel");
  o.btn("Raw").click();
  assert.equal(o.body.scrollTop, 3240);
  o.up.click();
  assert.equal(o.body.scrollTop, 3724.5, "10 + 23 * 160 + 34.5: the block's three rows are 69px now, and the reader is half way in as before");
  assert.equal(rowTop(o, 160), -34.5);
  assert.equal(topRow(o), 161);
  o.down.click();
  assert.equal(o.body.scrollTop, 3240);
  o.fv.closeFileView(); store.clear();
  const svg = await openFile(t, FIG);
  svg.btn("Source").click();
  await settle();
  assert.equal(rows(svg).length, 100, "the Source view: the XML's hundred lines as rows");
  svg.body.scrollTop = 1010;                                // 10 + 20 * 50: line 50 at the edge
  assert.equal(topRow(svg), 50);
  svg.up.click();
  assert.equal(svg.body.scrollTop, 1160, "10 + 23 * 50: line 50 still at the edge (the XML is one block, and the depth into it is the same fraction)");
  assert.equal(topRow(svg), 50); assert.equal(rowTop(svg, 50), 0);
});

// ── the pairing declines ───────────────────────────────────────────────────────────────────────────

test("a note whose blocks the pairing cannot follow (two html blocks with no text between them) is left where it stood, in both directions: no seat rather than a guessed one", async (t) => {
  const o = await openFile(t, NOTES);
  assert.equal(blocks(o).length, 62, "the two raw paragraphs rendered as two more blocks");
  o.body.scrollTop = 2014;                                  // paragraph 20 at the edge
  assert.equal(topBlock(o), 20);
  o.btn("Raw").click();
  assert.equal(o.body.scrollTop, 2014, "unmoved: the numeric scrollTop stands, as it did before the place was kept");
  o.btn("Rendered").click();
  assert.equal(o.body.scrollTop, 2014);
  assert.equal(topBlock(o), 20);
});

// ── a deep link lands last ─────────────────────────────────────────────────────────────────────────

test("a fragment waiting for the Rendered view lands after the seat and has the last word: the switch from Raw seats the reader's block at once, the next frame puts the linked heading at the edge, and with the fragment spent later switches seat the place; the same in a document opened from a link", async (t) => {
  store.set(FMT_KEY, JSON.stringify({ md: "raw" }));      // the stored preference is Raw, so the landing waits for the toggle
  const fv = await view();
  fv.openFileView(SECTIONED, SID, "results");
  t.after(() => { fv.closeFileView(); store.clear(); frames.length = 0; });
  await settle();
  const o = card(fv);
  assert.equal(rows(o).length, 237, "Raw first");
  assert.equal(frames.length, 0, "nothing to land on in Raw: the landing waits");
  o.body.scrollTop = 3210;                                  // paragraph 40's first row at the edge
  assert.equal(topRow(o), 160);
  o.btn("Rendered").click();
  assert.equal(o.body.scrollTop, 4014, "the seat, at once: paragraph 40 at the edge");
  assert.equal(frames.length, 1, "the landing is queued for the next frame");
  flushFrames();
  assert.equal(blocks(o)[50].id, "md-results");
  assert.equal(o.body.scrollTop, 5014, "14 + 100 * 50: the landing had the last word, the linked heading at the edge");
  assert.equal(topBlock(o), 50);
  o.btn("Raw").click();
  assert.equal(o.body.scrollTop, 4010, "10 + 20 * 200: the heading's row at the edge");
  o.btn("Rendered").click();
  assert.equal(o.body.scrollTop, 5014, "the fragment spent: the seat alone");
  assert.equal(frames.length, 0);
  fv.closeFileView(); store.set(FMT_KEY, JSON.stringify({ md: "raw" }));
  fv.openUrlView(HREF_SECTIONS + "#results");
  await settle();
  const u = card(fv);
  assert.equal(rows(u).length, 237); assert.equal(frames.length, 0);
  u.body.scrollTop = 3210;
  u.btn("Rendered").click();
  assert.equal(u.body.scrollTop, 4014, "the seat ran before the frame");
  assert.equal(frames.length, 1);
  flushFrames();
  assert.equal(u.body.scrollTop, 5014, "then the landing");
  assert.equal(topBlock(u), 50);
});

// ── the width stamp before the seat ───────────────────────────────────────────────────────────────

test("in a document opened from a link the seat measures a fresh root's tables at the stamped width: the switch back to Rendered puts the paragraph at the edge, where a stamp after the seat would have measured the table three blocks tall and left the paragraph 200px above the edge", async (t) => {
  const fv = await view();
  fv.openUrlView(HREF_TABLED);
  t.after(() => { fv.closeFileView(); store.clear(); frames.length = 0; });
  await settle();
  const o = card(fv);
  assert.equal(blocks(o).length, 60); assert.equal(blocks(o)[30].tagName, "TABLE");
  assert.equal(blockTop(o, 40), 4214, "the fixture: before any report the table lays out three blocks tall");
  reportWidth(800);                                         // the observer's first report, once the body has a layout
  assert.equal(blocks(o)[30].style["--fv-body-w"], "800px", "the stamp reached the root's table on the report");
  assert.equal(blockTop(o, 40), 4014);
  o.body.scrollTop = 4014;
  assert.equal(topBlock(o), 40);
  o.btn("Raw").click();
  assert.equal(o.body.scrollTop, 3230, "10 + 20 * 161: after the table's four lines, paragraph 40 starts a line later");
  assert.equal(topRow(o), 161);
  o.btn("Rendered").click();
  assert.equal(blocks(o)[30].style["--fv-body-w"], "800px", "the fresh root's table is stamped as the paint lands");
  assert.equal(o.body.scrollTop, 4014, "the seat measured the table at its width: paragraph 40 at the edge");
  assert.equal(blockTop(o, 40), 0);
  flushFrames();
  assert.equal(o.body.scrollTop, 4014, "no fragment to land");
});

// ── the order the viewer runs the keeper in (source pins) ─────────────────────────────────────────

test("both viewers read the place before the swap and seat it after the width stamp, before a fragment lands; the size step reads before the size is applied and seats after; a picture leaves nothing to read", () => {
  assert.match(VIEW, /import \{ readPlace, seatPlace, type Place \} from "\.\/reader-place";/);
  const paint = OPEN_FN.slice(OPEN_FN.indexOf("const renderBody = () => {"));
  assert.match(paint, /const kept = keptPlace\(\);[^\n]*\n\s*body\.replaceChildren\(rendered \? mdBlock\(text, \{ kind: "file", path, sid: sid \|\| null \}\) : codeBlock\(text, path, true\)\);\n\s*if \(rendered\) stampBodyWidth\(\);[^\n]*\n\s*shownText = text;[^\n]*\n\s*if \(kept\) seatPlace\(body, text, kept\);[^\n]*\n\s*if \(rendered && pendingFrag\) \{/,
    "the text arm: read, swap, stamp, record the text painted, seat, then the fragment landing");
  assert.match(paint, /body\.replaceChildren\(codeBlock\(svgText, path, true\)\);[^\n]*\n\s*shownText = svgText;/, "the Source arm records the XML as the text painted");
  assert.match(paint, /shownText = null;[^\n]*\n\s*body\.replaceChildren\(isPdf \? pdfBlock/, "a picture or a PDF frame: no text the body was painted from");
  assert.match(OPEN_FN, /const keptPlace = \(\): Place \| null => \(shownText === null \? null : readPlace\(body, shownText\)\);/);
  assert.match(OPEN_FN, /textSizeControl\(box, textShowing, \{ before: keptPlace, after: \(kept\) => \{ if \(kept && shownText !== null\) seatPlace\(body, shownText, kept\); \} \}\)/);
  assert.match(URL_FN, /const kept = keptPlace\(\);[^\n]*\n\s*body\.replaceChildren\(fmt\.md === "rendered"\n[^\n]*\n[^\n]*\n\s*if \(fmt\.md === "rendered"\) stampBodyWidth\(\);[^\n]*\n\s*shownText = text;[^\n]*\n\s*if \(kept\) seatPlace\(body, text, kept\);[^\n]*\n\s*landFragment\(\);/,
    "the URL viewer: the same order, the fragment landing last");
  assert.match(URL_FN, /textSizeControl\(box, \(\) => text !== null, \{ before: keptPlace, after: \(kept\) => \{ if \(kept && shownText !== null\) seatPlace\(body, shownText, kept\); \} \}\)/);
  const control = VIEW.slice(VIEW.indexOf("function textSizeControl("), VIEW.indexOf("function loaderEl("));
  assert.match(control, /const set = \(n: number\) => \{\s*\n?\s*if \(n === pct\) return;\s*\n?\s*pct = n; saveTextSize\(n\);\s*\n?\s*const kept = around \? around\.before\(\) : null;\s*\n?\s*apply\(\);\s*\n?\s*if \(around\) around\.after\(kept\);/,
    "one step: read the place, apply the size, seat");
});

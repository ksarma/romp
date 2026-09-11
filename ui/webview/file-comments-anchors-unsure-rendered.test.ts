// The guessed-copy cue on the two marks the raw suite never reaches (the anchors follow-on's review, round 3, 2026-09-08;
// plans/file-review.md, Commenting from either view and the follow-on note). (1) In Rendered view a comment on an embed
// line paints no text: its highlight is a frame on the picture (frameImage), and when the anchor ties and the stored
// position settles nothing, that frame wears the dashed cue like a Raw mark does — the ternary in paintAll's picture
// branch, which no test exercised: reverting it left the whole suite green while the card said "passage recurs" over a
// solid frame. (2) The mark's own title branches as the card's words do: a comment with no stored position (the shape
// `track-comment` writes) says so, instead of claiming a stored position the card on the same comment says it lacks.
// Driven over the DOM stand-in file-comments-region-tied.test.ts uses, with a Raw body added for the titles. Synthetic
// fixtures only: the notes-api world, placeholder ids.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inspect } from "node:util";
import { hideEdges, staysEnumerable } from "../test-dom-shim";
import type { FileViewActionCtx } from "./file-view";
import type { Status, StoreComment } from "./file-comments-model";
import { makeAnchor, locateComment } from "./anchor-map";

// ── the DOM stand-in ───────────────────────────────────────────────────────────────────────────────
type Rect = { left: number; top: number; right: number; bottom: number; width: number; height: number };
const rectOf = (left: number, top: number, width: number, height: number): Rect => ({ left, top, width, height, right: left + width, bottom: top + height });
const ZERO = rectOf(0, 0, 0, 0);
type Listener = { fn: (ev: Ev) => void; capture: boolean };
class Doc {
  body: E;
  hidden = false;
  activeElement: E;
  listeners = new Map<string, Listener[]>();
  constructor() { this.body = new E(this, "BODY"); this.activeElement = this.body; }
  createElement(tag: string): E { return new E(this, tag.toUpperCase()); }
  createTextNode(s: string): T { return new T(this, s); }
  getElementById(): null { return null; }
  addEventListener(type: string, fn: (ev: Ev) => void, opts?: boolean | { capture?: boolean }): void {
    const capture = typeof opts === "boolean" ? opts : !!(opts && opts.capture);
    (this.listeners.get(type) || this.listeners.set(type, []).get(type)!).push({ fn, capture });
  }
  removeEventListener(type: string, fn: (ev: Ev) => void): void { const l = this.listeners.get(type); if (l) { const i = l.findIndex((x) => x.fn === fn); if (i >= 0) l.splice(i, 1); } }
  left(n: N): void { if (n.contains(this.activeElement)) this.activeElement = this.body; }
}
class N {
  nodeType = 0;
  parentNode!: N | null;
  childNodes!: N[];
  constructor(public ownerDocument: Doc) {
    // the tree's edges are non-enumerable, so a node inspects as its own projection and a failing assertion's dump
    // stays small (ui/test-dom-shim.ts says why); assignments later keep them hidden
    Object.defineProperty(this, "parentNode", { value: null, writable: true, enumerable: false, configurable: true });
    Object.defineProperty(this, "childNodes", { value: [], writable: true, enumerable: false, configurable: true });
    hideEdges(this);
  }
  get parentElement(): E | null { return this.parentNode instanceof E ? this.parentNode : null; }
  get firstChild(): N | null { return this.childNodes[0] || null; }
  get textContent(): string { return this.nodeType === 3 ? (this as unknown as T).data : this.childNodes.map((c) => c.textContent).join(""); }
  set textContent(v: string) {
    for (const c of this.childNodes) c.parentNode = null;
    this.childNodes = v === "" ? [] : [this.ownerDocument.createTextNode(v)];
    for (const c of this.childNodes) c.parentNode = this;
  }
  contains(n: N | null): boolean { for (let x: N | null = n; x; x = x.parentNode) if (x === this) return true; return false; }
  remove(): void { if (this.parentNode) (this.parentNode as E).removeChild(this); }
}
class T extends N {
  nodeType = 3;
  constructor(doc: Doc, public data: string) { super(doc); hideEdges(this); }
  get length(): number { return this.data.length; }
  splitText(offset: number): T {
    const tail = new T(this.ownerDocument, this.data.slice(offset));
    this.data = this.data.slice(0, offset);
    const p = this.parentNode as E | null;
    if (p) { const i = p.childNodes.indexOf(this); p.childNodes.splice(i + 1, 0, tail); tail.parentNode = p; }
    return tail;
  }
}
type Init = { key?: string; clientX?: number; clientY?: number; pointerId?: number; button?: number };
type Ev = Init & { type: string; target: N; currentTarget: N | null; defaultPrevented: boolean; preventDefault(): void; stopPropagation(): void };
const kebab = (k: string | symbol): string => String(k).replace(/[A-Z]/g, (c) => "-" + c.toLowerCase());
type Compound = { tag: string | null; classes: string[]; attrs: Array<[string, string | null]> };
function parseSelector(sel: string): Compound[] {
  return sel.split(",").map((part) => {
    const s = part.trim();
    const out: Compound = { tag: null, classes: [], attrs: [] };
    const re = /^([a-zA-Z][\w-]*)|\.([\w-]+)|\[([\w-]+)(?:="([^"]*)")?\]/g;
    let m: RegExpExecArray | null;
    while ((m = re.exec(s))) {
      if (m[1]) out.tag = m[1].toUpperCase();
      else if (m[2]) out.classes.push(m[2]);
      else out.attrs.push([m[3], m[4] ?? null]);
      if (re.lastIndex === s.length) break;
    }
    return out;
  });
}
class E extends N {
  nodeType = 1;
  attrs = new Map<string, string>();
  listeners = new Map<string, Array<(ev: Ev) => void>>();
  hidden = false; title = ""; type = ""; disabled = false; placeholder = ""; value = ""; checked = false; offsetWidth = 0; tabIndex = -1; readOnly = false;
  width = 0; height = 0;
  naturalWidth = 0; naturalHeight = 0; complete: boolean | undefined = undefined;
  rect: Rect | null = null;
  scrolled = 0;
  style: Record<string, string> = {};
  dataset: Record<string, string>;
  classList = {
    add: (...c: string[]) => this.setClasses([...this.classes(), ...c]),
    remove: (...c: string[]) => this.setClasses(this.classes().filter((x) => !c.includes(x))),
    toggle: (c: string, on?: boolean) => { if (on === undefined ? !this.classes().includes(c) : on) this.classList.add(c); else this.classList.remove(c); },
    contains: (c: string) => this.classes().includes(c),
  };
  constructor(doc: Doc, public tagName: string) {
    super(doc);
    this.dataset = new Proxy({} as Record<string, string>, {
      get: (_t, k) => (typeof k === "string" ? this.attrs.get("data-" + kebab(k)) : undefined),
      set: (_t, k, v) => { this.attrs.set("data-" + kebab(k), String(v)); return true; },
      deleteProperty: (_t, k) => { this.attrs.delete("data-" + kebab(k)); return true; },
      has: (_t, k) => this.attrs.has("data-" + kebab(k)),
    });
    hideEdges(this);
  }
  private classes(): string[] { return (this.attrs.get("class") || "").split(/\s+/).filter(Boolean); }
  private setClasses(c: string[]): void { this.attrs.set("class", [...new Set(c)].join(" ")); }
  get className(): string { return this.attrs.get("class") || ""; }
  set className(v: string) { this.attrs.set("class", v); }
  set innerHTML(html: string) { this.replaceChildren(...parseHTML(this.ownerDocument, html)); }
  getAttribute(n: string): string | null { return this.attrs.has(n) ? (this.attrs.get(n) as string) : null; }
  setAttribute(n: string, v: string): void { this.attrs.set(n, v); }
  removeAttribute(n: string): void { this.attrs.delete(n); }
  hasAttribute(n: string): boolean { return this.attrs.has(n); }
  removeChild(n: N): N { const i = this.childNodes.indexOf(n); if (i >= 0) this.childNodes.splice(i, 1); n.parentNode = null; this.ownerDocument.left(n); return n; }
  appendChild<X extends N>(n: X): X { if (n.parentNode) (n.parentNode as E).removeChild(n); this.childNodes.push(n); n.parentNode = this; return n; }
  insertBefore(n: N, ref: N | null): N {
    if (!ref) return this.appendChild(n);
    if (n.parentNode) (n.parentNode as E).removeChild(n);
    const i = this.childNodes.indexOf(ref);
    this.childNodes.splice(i, 0, n); n.parentNode = this; return n;
  }
  replaceChildren(...c: N[]): void { for (const x of this.childNodes) { x.parentNode = null; this.ownerDocument.left(x); } this.childNodes.length = 0; for (const x of c) this.appendChild(x); }
  normalize(): void {
    const out: N[] = [];
    for (const c of this.childNodes) {
      const prev = out[out.length - 1];
      if (c instanceof T && prev instanceof T) { prev.data += c.data; c.parentNode = null; }
      else if (c instanceof T && c.data === "") c.parentNode = null;
      else out.push(c);
    }
    this.childNodes = out;
  }
  matches(sel: string): boolean {
    return parseSelector(sel).some((c) => (c.tag === null || c.tag === this.tagName)
      && c.classes.every((k) => this.classList.contains(k))
      && c.attrs.every(([a, v]) => this.attrs.has(a) && (v === null || this.attrs.get(a) === v)));
  }
  closest(sel: string): E | null { for (let x: N | null = this; x; x = x.parentNode) if (x instanceof E && x.matches(sel)) return x; return null; }
  querySelectorAll(sel: string): E[] {
    const out: E[] = [];
    const chains = sel.split(",").map((g) => g.trim().split(/\s+/));
    const fits = (el: E, chain: string[]): boolean => {
      if (!el.matches(chain[chain.length - 1])) return false;
      let k = chain.length - 2;
      for (let a: N | null = el.parentNode; a && k >= 0 && a !== this.parentNode; a = a.parentNode) if (a instanceof E && a.matches(chain[k])) k--;
      return k < 0;
    };
    const visit = (n: N) => { for (const c of n.childNodes) { if (c instanceof E) { if (chains.some((ch) => fits(c, ch))) out.push(c); visit(c); } } };
    visit(this);
    return out;
  }
  querySelector(sel: string): E | null { return this.querySelectorAll(sel)[0] || null; }
  addEventListener(type: string, fn: (ev: Ev) => void): void { (this.listeners.get(type) || this.listeners.set(type, []).get(type)!).push(fn); }
  removeEventListener(type: string, fn: (ev: Ev) => void): void { const l = this.listeners.get(type); if (l) l.splice(l.indexOf(fn), 1); }
  dispatch(type: string, init: Init = {}): Ev {
    let stopped = false;
    const ev: Ev = { ...init, type, target: this, currentTarget: null, defaultPrevented: false,
      preventDefault() { this.defaultPrevented = true; }, stopPropagation() { stopped = true; } };
    const doc = this.ownerDocument;
    const at = doc.listeners.get(type) || [];
    for (const l of [...at]) if (l.capture) l.fn(ev);
    for (let n: N | null = this; n && !stopped; n = n.parentNode) {
      if (!(n instanceof E)) continue;
      ev.currentTarget = n;
      for (const fn of [...(n.listeners.get(type) || [])]) fn(ev);
    }
    if (!stopped) for (const l of [...at]) if (!l.capture) l.fn(ev);
    return ev;
  }
  click(): void { this.dispatch("click"); }
  focus(): void { this.ownerDocument.activeElement = this; }
  blur(): void { if (this.ownerDocument.activeElement === this) this.ownerDocument.activeElement = this.ownerDocument.body; }
  getBoundingClientRect(): Rect {
    if (this.rect) return this.rect;
    if (this.classList.contains("fc-imgwrap")) { const img = this.childNodes.find((c) => c instanceof E && c.tagName === "IMG") as E | undefined; return img ? img.getBoundingClientRect() : ZERO; }
    return ZERO;
  }
  setPointerCapture(): void { /* inert */ }
  releasePointerCapture(): void { /* inert */ }
  getContext(): null { return null; }
  scrollIntoView(): void { this.scrolled++; }
}
const VOID = new Set(["br", "hr", "img", "input", "meta", "link", "area", "base", "col", "embed", "source", "track", "wbr"]);
const NAMED: Record<string, string> = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'", nbsp: " " };
function decodeEntities(s: string): string {
  return s.replace(/&(#x[0-9a-fA-F]+|#\d+|[a-zA-Z]+);/g, (m, e: string) => {
    if (e[0] === "#") return String.fromCodePoint(parseInt(e[1] === "x" || e[1] === "X" ? e.slice(2) : e.slice(1), e[1] === "x" || e[1] === "X" ? 16 : 10));
    return e in NAMED ? NAMED[e] : m;
  });
}
function parseHTML(doc: Doc, html: string): N[] {
  html = html.replace(/\r\n?/g, "\n");
  const root = doc.createElement("#fragment");
  const stack: E[] = [root];
  let i = 0;
  const top = () => stack[stack.length - 1];
  while (i < html.length) {
    if (html[i] === "<") {
      if (html.startsWith("<!--", i)) { const e = html.indexOf("-->", i); i = e < 0 ? html.length : e + 3; continue; }
      if (html[i + 1] === "/") {
        const e = html.indexOf(">", i);
        const name = html.slice(i + 2, e).trim().toUpperCase();
        for (let k = stack.length - 1; k > 0; k--) { if (stack[k].tagName === name) { stack.length = k; break; } }
        i = e + 1; continue;
      }
      const m = /^<([a-zA-Z][\w:-]*)((?:\s+[^\s"'>\/=]+(?:\s*=\s*(?:"[^"]*"|'[^']*'|[^\s"'=<>`]+))?)*)\s*(\/?)>/.exec(html.slice(i));
      if (!m) { top().appendChild(doc.createTextNode("<")); i++; continue; }
      const el = doc.createElement(m[1]);
      const attrRe = /([^\s"'>\/=]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+)))?/g;
      let a: RegExpExecArray | null;
      while ((a = attrRe.exec(m[2]))) el.setAttribute(a[1], decodeEntities(a[2] ?? a[3] ?? a[4] ?? ""));
      top().appendChild(el);
      i += m[0].length;
      if (!m[3] && !VOID.has(m[1].toLowerCase())) {
        stack.push(el);
        if (m[1].toLowerCase() === "pre" && html[i] === "\n") i++;
      }
      continue;
    }
    let e = html.indexOf("<", i);
    if (e < 0) e = html.length;
    top().appendChild(doc.createTextNode(decodeEntities(html.slice(i, e))));
    i = e;
  }
  return root.childNodes.slice();
}

// ── globals the modules reach for, installed before they are imported ──────────────────────────────
const doc = new Doc();
const win: any = new EventTarget();
win.parent = win;
win.innerWidth = 1200; win.innerHeight = 800;
win.devicePixelRatio = 1;
win.getSelection = () => ({ isCollapsed: true, rangeCount: 0, toString: () => "" });
win.matchMedia = () => { throw new TypeError("matchMedia is not a function"); };
(globalThis as any).window = win;
(globalThis as any).document = doc;
/** The kernel a test stands up: a 404 to every HEAD and no sessions. */
(globalThis as any).fetch = async () => ({ status: 404, headers: { get: () => null }, json: async () => [] });
const realSetInterval = globalThis.setInterval;
(globalThis as any).setInterval = (fn: () => void, ms: number) => { const t = realSetInterval(fn, ms); (t as any).unref?.(); return t; };
const tick = () => new Promise<void>((r) => setImmediate(r));

// ── fixtures: the notes-api world — a report embedding one figure twice, with the same long paragraphs around each ──
const SID = "11111111-2222-3333-4444-555555555555";
const MD = "/repo/notes-api/docs/report.md";
const STORE_MD = "/repo/notes-api/.trackchanges/docs%2Freport.md.json";
const T0 = 1757145600000;
// each paragraph is longer than the host's widening cap (480 characters), so an anchor on either embed line, widened to
// the cap by the host, has the same context at both copies: the copies tie, and only the stored position tells them apart
const BEFORE = "The quick brown fox jumps over the lazy dog. ".repeat(12).trim();
const AFTER = "Pack my box with five dozen liquor jugs. ".repeat(12).trim();
assert.ok(BEFORE.length > 480 && AFTER.length > 480, "the paragraphs outrun the cap");
const EMBED = "![Latency](figs/p95.png)";
const BLOCK = BEFORE + "\n\n" + EMBED + "\n\n" + AFTER;
const DOC = "# Report\n\n" + BLOCK + "\n\n" + BLOCK + "\n";
const FIRST_AT = DOC.indexOf(EMBED);
const SECOND_AT = DOC.indexOf(EMBED, FIRST_AT + 1);
assert.ok(FIRST_AT > 0 && SECOND_AT > FIRST_AT && DOC.indexOf(EMBED, SECOND_AT + 1) === -1, "two embeds");
// the anchor the host stores at its cap for the second embed (engine.makeAnchor with 480 characters of context)
const CAP_ANCHOR = { quote: EMBED, prefix: DOC.slice(SECOND_AT - 480, SECOND_AT), suffix: DOC.slice(SECOND_AT + EMBED.length, SECOND_AT + EMBED.length + 480) };
assert.equal(CAP_ANCHOR.prefix, DOC.slice(FIRST_AT - 480, FIRST_AT), "the same 480 characters before either embed");
assert.equal(CAP_ANCHOR.suffix, DOC.slice(FIRST_AT + EMBED.length, FIRST_AT + EMBED.length + 480), "and after");
// the title edited, and nothing recorded it: both copies moved by the edit's length, and the stored position names neither
const REVISED = DOC.replace("# Report", "# Report, revised");
const SHIFT = REVISED.length - DOC.length;
assert.ok(SHIFT > 0 && SHIFT < (SECOND_AT - FIRST_AT) / 2, "the shift is small: the nearest tied copy to the old position is still the second");
/** The Rendered body marked produces for the report, its title as given. */
const html = (title: string): string =>
  "<h1>" + title + "</h1>\n<p>" + BEFORE + "</p>\n<p><img src=\"figs/p95.png\" alt=\"Latency\"></p>\n<p>" + AFTER + "</p>\n"
  + "<p>" + BEFORE + "</p>\n<p><img src=\"figs/p95.png\" alt=\"Latency\"></p>\n<p>" + AFTER + "</p>\n";
/** The panel's comment on the second embed line, as the host saved it: the cap anchor and the located offset. */
const onSecond: StoreComment = {
  id: T0 + "-" + SECOND_AT, author: "you", ts: T0, body: "Use the p99 chart instead.", anchor: CAP_ANCHOR, anchorAt: SECOND_AT, replies: [], resolved: false,
};
/** A comment `track-comment` wrote on the first embed line: the engine's 24 characters of context (which tie here too)
 *  and no position — the CLI stores none. */
const byCli: StoreComment = {
  id: T0 + "-cli", author: "api", ts: T0, body: "Swap in the p99 chart.", anchor: makeAnchor(DOC, { start: FIRST_AT, end: FIRST_AT + EMBED.length }), replies: [], resolved: false,
};
assert.notEqual(locateComment(DOC, byCli.anchor!, 0).range!.start, locateComment(DOC, byCli.anchor!, DOC.length).range!.start, "the CLI's anchor ties");
// the panel's words, copied here so a swap or a rewording fails a driven test
const UNSURE_POSITION = "This passage occurs in the file more than once with the same surroundings, and the position stored with the comment names none of the copies as the file is now, so the copy nearest that position is highlighted, not a confirmed one. Reveal it and save again from the right copy to confirm.";
const UNSURE_NONE = "This passage occurs in the file more than once with the same surroundings, and the comment stores no position to tell the copies apart, so the first copy is highlighted, not a confirmed one. Reveal it and save again from the right copy to confirm.";
const MARK_UNSURE_POSITION = "Open the comment; this passage recurs, and this copy is the nearest to the comment's stored position, not a confirmed one";
const MARK_UNSURE_NONE = "Open the comment; this passage recurs, and the comment stores no position to tell the copies apart, so this is the first copy, not a confirmed one";
const MARK_PLAIN = "Open the comment on this passage";
function mdStatus(comments: StoreComment[]): Status {
  return {
    verb: "status", root: "/repo/notes-api", storePath: STORE_MD, trackedBy: null, agentTooling: "present",
    fileMtimeNs: "1757145600000000001", storeMtimeNs: "1757145600000000002", configMtimeNs: null,
    store: { v: 3, path: "docs/report.md", suggestions: [], comments },
    hunks: [], log: [], unsent: { comments: [], replies: [], accepted: 0, rejected: 0, watermark: null },
    embeddedHashes: {},
  };
}

// ── the harness: a Rendered body (`html`) or a Raw body (the code rows), the seam as closures ──────
const mk = (tag: string, cls: string): E => { const e = doc.createElement(tag); e.className = cls; return e; };
const IMG_RECT = rectOf(100, 200, 300, 200);
const picture = (img: E): void => { img.rect = IMG_RECT; img.naturalWidth = 600; img.naturalHeight = 400; img.complete = true; };
/** The Raw view's rows, as codeBlock builds them: one `.fv-cl > .fv-ct` per line, a trailing newline being no line. */
function rows(code: E, src: string): void {
  const lines = src.split("\n");
  if (lines.length && lines[lines.length - 1] === "") lines.pop();
  code.replaceChildren(...lines.map((ln) => {
    const cl = mk("span", "fv-cl");
    const ct = mk("span", "fv-ct");
    if (ln) ct.appendChild(doc.createTextNode(ln));
    cl.appendChild(ct);
    return cl;
  }));
}
async function harness(over: { mode: "rendered" | "raw"; src: string; html?: string }) {
  const fc = await import("./file-comments");
  const main = mk("div", "fileview-main");
  const body = mk("div", "fileview-body"); main.appendChild(body);
  if (over.mode === "rendered") {
    const md = mk("div", "fileview-md"); md.innerHTML = over.html!; body.appendChild(md);
    for (const img of md.querySelectorAll("img")) picture(img);
  } else {
    const wrap = mk("div", "fileview-code"); const pre = mk("pre", "fileview-pre fileview-wrap"); const code = mk("code", "hljs");
    rows(code, over.src); pre.appendChild(code); wrap.appendChild(pre); body.appendChild(wrap);
  }
  const posted: Array<Record<string, any>> = [];
  const closers: Array<() => void> = [];
  let aside: E | null = null;
  const noop = () => { /* inert */ };
  const ctx: FileViewActionCtx = {
    path: MD, sid: SID, todoId: null,
    body: () => body as unknown as HTMLElement,
    mode: () => over.mode,
    text: () => over.src,
    mtimeNs: () => "1757145600000000001",
    media: () => null, pdfPages: () => [], mediaElement: () => null, renderedImages: () => [],
    identity: () => ({ name: "api", color: null }),
    onRendered: noop, onSelection: noop, onSaved: noop, onClose: (cb) => { closers.push(cb); },
    post: (m) => { posted.push(m); }, ensureEditingAllowed: async () => true, setEditBlocked: noop, editing: () => false, setTrackedEdit: noop, guardClose: noop,
    aside: (el) => { if (el) { aside = el as unknown as E; main.appendChild(aside); } else if (aside) { aside.remove(); aside = null; } },
    setMode: noop, scrollToOffset: noop, reload: noop,
  };
  const unit = fc.fileCommentsAction.mount(ctx) as unknown as E;
  const button = unit.childNodes[0] as E;
  const last = () => posted[posted.length - 1];
  const reply = async (s: Status) => { win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId: last().reqId, ...s } })); await tick(); await tick(); };
  return {
    main,
    /** Answer the mount's probe, open the panel, answer its refresh: the panel as a person first sees it. */
    open: async (s: Status) => { await reply(s); button.dispatch("click"); await reply(s); },
    q: (sel: string) => main.querySelector(sel),
    qa: (sel: string) => main.querySelectorAll(sel),
    head: (id: string): E => main.querySelector('.fc-card[data-id="' + id + '"] .fc-card-head')!,
    tags: (id: string): E[] => main.querySelector('.fc-card[data-id="' + id + '"] .fc-card-head')!.querySelectorAll(".fc-tag"),
    dispose: () => { for (const cb of closers) cb(); },
  };
}
const framed = (img: E): boolean => img.classList.contains("fc-img") && img.classList.contains("fc-hl");

// ── the picture frame wears the cue ────────────────────────────────────────────────────────────────

test("Rendered view, the title edited unrecorded: the stored position names neither embed, so the nearest picture's frame is dashed and the card wears 'passage recurs' with the words for a position", async () => {
  const h = await harness({ mode: "rendered", src: REVISED, html: html("Report, revised") });
  await h.open(mdStatus([onSecond]));
  const [first, second] = h.qa(".fileview-md img");
  assert.ok(second && framed(second), "the second picture is framed: nearest to the old position among the tied copies");
  assert.equal(framed(first), false, "the first is not");
  assert.ok(second.classList.contains("fc-hl-context"), "the frame wears the dashed cue: a guess, not the copy that was chosen");
  assert.equal(second.style.outline, "2px dashed var(--warn)", "styleFrame draws the cue as a dashed outline");
  assert.equal(second.dataset.act, "fcopen"); assert.equal(second.dataset.id, onSecond.id);
  const tags = h.tags(onSecond.id);
  assert.deepEqual(tags.map((t) => t.textContent), ["passage recurs"]);
  assert.equal(tags[0].title, UNSURE_POSITION);
  h.head(onSecond.id).dispatch("click");
  assert.equal(h.q('.fc-card.open[data-id="' + onSecond.id + '"] .fc-note')!.textContent, UNSURE_POSITION, "the open card says it in words");
  h.dispose();
});

test("Rendered view, a comment with no stored position on an embed that recurs: the first picture's frame is dashed, with the words for no position", async () => {
  const h = await harness({ mode: "rendered", src: DOC, html: html("Report") });
  await h.open(mdStatus([byCli]));
  const [first, second] = h.qa(".fileview-md img");
  assert.ok(framed(first), "the engine's earliest tie: the first picture");
  assert.equal(framed(second), false);
  assert.ok(first.classList.contains("fc-hl-context"));
  assert.equal(first.style.outline, "2px dashed var(--warn)");
  const tags = h.tags(byCli.id);
  assert.deepEqual(tags.map((t) => t.textContent), ["passage recurs"]);
  assert.equal(tags[0].title, UNSURE_NONE);
  h.dispose();
});

test("Rendered view, the position naming the second embed in the text as saved: a solid frame on the second picture, no tag — the copy that was chosen", async () => {
  const h = await harness({ mode: "rendered", src: DOC, html: html("Report") });
  await h.open(mdStatus([onSecond]));
  const [first, second] = h.qa(".fileview-md img");
  assert.ok(framed(second), "the second picture is framed");
  assert.equal(framed(first), false);
  assert.equal(second.classList.contains("fc-hl-context"), false, "painted plainly: the position names this copy");
  assert.equal(second.style.outline, "2px solid var(--warn)");
  assert.deepEqual(h.tags(onSecond.id), [], "no tag");
  h.dispose();
});

// ── the mark's title says the same thing the card does ─────────────────────────────────────────────

test("Raw view: the guessed copy's highlight title branches as the card's words do — no stored position says so and names the first copy; a stale position says nearest; a position naming its copy is the plain title", async () => {
  // no position: the mark cannot claim one the card says is absent
  const none = await harness({ mode: "raw", src: DOC });
  await none.open(mdStatus([byCli]));
  let marks = none.qa("code.hljs .fc-hl");
  assert.equal(marks.length, 1, "one highlight (the embed line is one row)");
  assert.equal(marks[0].textContent, EMBED);
  assert.ok(marks[0].classList.contains("fc-hl-context"));
  assert.equal(marks[0].title, MARK_UNSURE_NONE);
  assert.match(marks[0].title, /not a confirmed one/);
  assert.equal(none.tags(byCli.id)[0].title, UNSURE_NONE, "the tag on the same comment: the same branch");
  none.dispose();
  // a stale position: nearest-wins, and the title says so
  const stale = await harness({ mode: "raw", src: REVISED });
  await stale.open(mdStatus([onSecond]));
  marks = stale.qa("code.hljs .fc-hl");
  assert.equal(marks.length, 1);
  assert.ok(marks[0].classList.contains("fc-hl-context"));
  assert.equal(marks[0].title, MARK_UNSURE_POSITION);
  assert.equal(stale.tags(onSecond.id)[0].title, UNSURE_POSITION);
  stale.dispose();
  // the position names its copy: no cue, the plain title
  const sure = await harness({ mode: "raw", src: DOC });
  await sure.open(mdStatus([onSecond]));
  marks = sure.qa("code.hljs .fc-hl");
  assert.equal(marks.length, 1);
  assert.equal(marks[0].classList.contains("fc-hl-context"), false);
  assert.equal(marks[0].title, MARK_PLAIN);
  assert.deepEqual(sure.tags(onSecond.id), []);
  sure.dispose();
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
});

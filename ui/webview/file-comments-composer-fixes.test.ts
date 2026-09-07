// The composer follow-on's review fixes in the box's own listeners (plans/file-review.md, "The composer follow-on
// (2026-09-07)"; the 2026-09-07 review), driven through the panel itself. An Escape pressed under a composing IME (macOS
// Chrome and Safari report key "Escape" with isComposing) is the IME's, and the box let it through to the viewer's
// document-level Escape (file-view.ts onKey reads no isComposing), which closed the whole viewer with the draft in it;
// every Escape stops at the box now, its default left to the IME. And autosizeComposer's `height: auto` measurement collapsed
// a grown box for one layout, in which a scrolled aside — short on the phone and in a short pane — was clamped toward its
// top on every keystroke; the scrolled ancestors are read before the collapse and written back after the new height. The
// drag-before-typing guard and the hint on a coarse pointer are file-comments-composer-review.test.ts's; the real layout
// and the real drag are file-comments-composer-fixes-browser.test.ts. The DOM stand-in is the one the panel tests share
// (copied, as each of them carries it; there is no jsdom in this tree). Synthetic fixtures only: the notes-api world,
// placeholder ids.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import type { FileViewActionCtx, TrackedEdit } from "./file-view";
import type { Status, StoreComment } from "./file-comments-model";

const web = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const SRC = web("file-comments.ts");

// ── the DOM stand-in ───────────────────────────────────────────────────────────────────────────────
class Doc {
  body: E;
  hidden = false;
  activeElement: E | null = null;
  listeners = new Map<string, Array<(ev: unknown) => void>>();
  constructor() { this.body = new E(this, "BODY"); this.activeElement = this.body; }
  createElement(tag: string): E { return new E(this, tag.toUpperCase()); }
  createTextNode(s: string): T { return new T(this, s); }
  getElementById(): null { return null; }
  addEventListener(type: string, fn: (ev: unknown) => void): void { (this.listeners.get(type) || this.listeners.set(type, []).get(type)!).push(fn); }
  removeEventListener(type: string, fn: (ev: unknown) => void): void { const l = this.listeners.get(type); if (l) l.splice(l.indexOf(fn), 1); }
  fire(type: string, target: N): void { for (const fn of this.listeners.get(type) || []) fn({ type, target }); }
}
class N {
  nodeType = 0;
  parentNode: N | null = null;
  childNodes: N[] = [];
  constructor(public ownerDocument: Doc) {}
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
  constructor(doc: Doc, public data: string) { super(doc); }
  get length(): number { return this.data.length; }
  splitText(offset: number): T {
    const tail = new T(this.ownerDocument, this.data.slice(offset));
    this.data = this.data.slice(0, offset);
    const p = this.parentNode as E | null;
    if (p) { const i = p.childNodes.indexOf(this); p.childNodes.splice(i + 1, 0, tail); tail.parentNode = p; }
    return tail;
  }
}
type Init = { key?: string; ctrlKey?: boolean; metaKey?: boolean; shiftKey?: boolean; isComposing?: boolean };
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
  hidden = false; title = ""; type = ""; disabled = false; placeholder = ""; value = ""; checked = false; offsetWidth = 0; readOnly = false;
  rows = 0;
  // the layout a test gives a box: what the browser would measure at height: auto (autosizeComposer reads these)
  scrollHeight = 0; offsetHeight = 0; clientHeight = 0;
  selectionStart = 0; selectionEnd = 0;
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
  }
  /** As the browser has it: a tabindex attribute, else 0 for a button, an input or a textarea, else -1. */
  get tabIndex(): number { return this.attrs.has("tabindex") ? Number(this.attrs.get("tabindex")) : (this.tagName === "BUTTON" || this.tagName === "INPUT" || this.tagName === "TEXTAREA" ? 0 : -1); }
  set tabIndex(v: number) { this.attrs.set("tabindex", String(v)); }
  private classes(): string[] { return (this.attrs.get("class") || "").split(/\s+/).filter(Boolean); }
  private setClasses(c: string[]): void { this.attrs.set("class", [...new Set(c)].join(" ")); }
  get className(): string { return this.attrs.get("class") || ""; }
  set className(v: string) { this.attrs.set("class", v); }
  set innerHTML(html: string) { this.replaceChildren(...parseHTML(this.ownerDocument, html)); }
  getAttribute(n: string): string | null { return this.attrs.has(n) ? (this.attrs.get(n) as string) : null; }
  setAttribute(n: string, v: string): void { this.attrs.set(n, v); }
  removeAttribute(n: string): void { this.attrs.delete(n); }
  /** A node leaves its parent; if it held the focus (itself or a descendant), the focus fixup rule moves it to the body. */
  detach(n: N): void {
    const i = this.childNodes.indexOf(n); if (i >= 0) this.childNodes.splice(i, 1); n.parentNode = null;
    const doc = this.ownerDocument;
    if (n instanceof E && doc.activeElement && n.contains(doc.activeElement)) doc.activeElement = doc.body;
  }
  removeChild(n: N): N { this.detach(n); return n; }
  appendChild<X extends N>(n: X): X { if (n.parentNode) (n.parentNode as E).detach(n); this.childNodes.push(n); n.parentNode = this; return n; }
  insertBefore(n: N, ref: N | null): N {
    if (!ref) return this.appendChild(n);
    if (n.parentNode) (n.parentNode as E).detach(n);
    const i = this.childNodes.indexOf(ref);
    this.childNodes.splice(i, 0, n); n.parentNode = this; return n;
  }
  replaceChildren(...c: N[]): void { for (const x of this.childNodes.slice()) this.detach(x); for (const x of c) this.appendChild(x); }
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
  /** Dispatch with bubbling: every ancestor's listeners run until one stops propagation. */
  dispatch(type: string, init: Init = {}): Ev {
    let stopped = false;
    const ev: Ev = { ...init, type, target: this, currentTarget: null, defaultPrevented: false,
      preventDefault() { this.defaultPrevented = true; }, stopPropagation() { stopped = true; } };
    for (let n: N | null = this; n && !stopped; n = n.parentNode) {
      if (!(n instanceof E)) continue;
      ev.currentTarget = n;
      for (const fn of [...(n.listeners.get(type) || [])]) fn(ev);
    }
    return ev;
  }
  getBoundingClientRect(): { left: number; top: number; right: number; bottom: number; width: number; height: number } {
    return this.tagName === "IMG" ? { left: 100, top: 200, right: 400, bottom: 400, width: 300, height: 200 } : { left: 0, top: 0, right: 0, bottom: 0, width: 0, height: 0 };
  }
  scrollIntoView(): void { /* inert */ }
  setSelectionRange(a: number, b: number): void { this.selectionStart = a; this.selectionEnd = b; }
  /** Focus lands only on a focusable, enabled element, as in the browser. */
  focus(): void { if (this.tabIndex >= 0 && !this.disabled) this.ownerDocument.activeElement = this; }
  blur(): void { if (this.ownerDocument.activeElement === this) this.ownerDocument.activeElement = this.ownerDocument.body; }
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

// ── globals the module reaches for, installed before it is imported ────────────────────────────────
const doc = new Doc();
const win: any = new EventTarget();
win.parent = win;
win.innerWidth = 1200; win.innerHeight = 800;
win.getSelection = () => ({ isCollapsed: true, rangeCount: 0, toString: () => "" });
(globalThis as any).window = win;
(globalThis as any).document = doc;
(globalThis as any).fetch = async () => ({ status: 404, headers: { get: () => null }, json: async () => [] });
const realSetInterval = globalThis.setInterval;
(globalThis as any).setInterval = (fn: () => void, ms: number) => { const t = realSetInterval(fn, ms); (t as any).unref?.(); return t; };
const tick = () => new Promise<void>((r) => setImmediate(r));
// the platform the module detected at import (its IS_MAC reads navigator.platform once, the editor's rule)
const MAC = typeof navigator !== "undefined" && /Mac|iP(?:hone|ad|od)/.test(navigator.platform || "");

// ── fixtures: the notes-api world ──────────────────────────────────────────────────────────────────
const SID = "11111111-2222-3333-4444-555555555555";
const ABS = "/repo/notes-api/docs/report.md";
const T0 = 1757145600000;
const passage: StoreComment = {
  id: T0 + "-118", author: "you", ts: T0, body: "Which cache? Say which.",
  anchor: { quote: "shipping the cache in v1.2", prefix: "We recommend ", suffix: "." }, replies: [], resolved: false,
};
function status(over: Partial<Status> = {}): Status {
  return {
    verb: "status", root: "/repo/notes-api", storePath: "/repo/notes-api/.trackchanges/docs%2Freport.md.json",
    trackedBy: { kind: "file", entry: "docs/report.md" }, agentTooling: "present",
    fileMtimeNs: "1757145600000000001", storeMtimeNs: "1757145600000000002", configMtimeNs: "1757145600000000003",
    store: { v: 3, path: "docs/report.md", suggestions: [], comments: [passage] },
    hunks: [], log: [],
    unsent: { comments: [passage.id], replies: [], accepted: 0, rejected: 0, watermark: null },
    ...over,
  };
}

// ── the harness: a mounted panel inside the viewer's body row ──────────────────────────────────────
type Posted = Record<string, any>;
async function harness(over: Partial<FileViewActionCtx> & { html?: string; src?: string } = {}) {
  const fc = await import("./file-comments");
  const { html, src, ...ctxOver } = over;
  const main = doc.createElement("div"); main.className = "fileview-main";
  const body = doc.createElement("div"); body.className = "fileview-body"; main.appendChild(body);
  if (html !== undefined) { const md = doc.createElement("div"); md.className = "fileview-md"; md.innerHTML = html; body.appendChild(md); }
  const posted: Posted[] = [];
  const tracked: Array<TrackedEdit | null> = [];
  const closers: Array<() => void> = [];
  const saved: Array<(info: { mtimeNs: string; logged: boolean }) => void> = [];
  const modes: string[] = [];
  let aside: E | null = null;
  const noop = () => { /* inert */ };
  const ctx: FileViewActionCtx = {
    path: ABS, sid: SID, todoId: null,
    body: () => body as unknown as HTMLElement, mode: () => "rendered", text: () => (src === undefined ? null : src),
    mtimeNs: () => "1757145600000000001", media: () => null, mediaElement: () => null, renderedImages: () => [], pdfPages: () => [], identity: () => ({ name: "api", color: null }),
    onRendered: noop, onSelection: noop, onSaved: (cb) => { saved.push(cb); }, onClose: (cb) => { closers.push(cb); },
    post: (m) => { posted.push(m); }, ensureEditingAllowed: async () => true, setEditBlocked: noop, editing: () => false, setTrackedEdit: (t) => { tracked.push(t); },
    aside: (el) => { if (el) { aside = el as unknown as E; main.appendChild(aside); } else if (aside) { aside.remove(); aside = null; } },
    setMode: (m) => { modes.push(m); }, scrollToOffset: noop, reload: noop,
    ...ctxOver,
  };
  const unit = fc.fileCommentsAction.mount(ctx) as unknown as E;
  const button = unit.childNodes[0] as E;
  const last = (): Posted => posted[posted.length - 1];
  const reply = async (data: Record<string, unknown>) => { win.dispatchEvent(new MessageEvent("message", { data })); await tick(); await tick(); };
  const h = {
    fc, main, body, unit, button, posted, modes, saved, last,
    ok: (over: Partial<Status> = {}) => reply({ type: "fileCommentsResult", reqId: last().reqId, ...status(over) }),
    refuse: (code: string, error: string) => reply({ type: "fileCommentsFailed", reqId: last().reqId, verb: last().verb, code, error }),
    q: (sel: string) => main.querySelector(sel),
    qa: (sel: string) => main.querySelectorAll(sel),
    click: (sel: string) => { const e = main.querySelector(sel); assert.ok(e, "a control " + sel); e!.dispatch("click"); },
    box: (): E => { const b = main.querySelector("textarea.fc-input"); assert.ok(b, "the comment box is a textarea"); return b!; },
    /** The keys as the browser sends them to the focused box. */
    key: (init: Init): Ev => h.box().dispatch("keydown", init),
    chord: (): Ev => h.key({ key: "Enter", ctrlKey: true }),
    /** Open the panel on a status and start a whole-file comment. */
    open: async (over: Partial<Status> = {}) => { await h.ok(over); button.dispatch("click"); await h.ok(over); },
    float: () => { const f = doc.body.querySelectorAll(".fc-float"); return f[f.length - 1]; },
    dispose: () => { for (const cb of closers) cb(); },
  };
  return h;
}

// ── an Escape the IME is composing under ───────────────────────────────────────────────────────────

test("an Escape under a composing IME is the IME's — no cancel, the draft stays — and it still never reaches the viewer's Escape", async () => {
  const h = await harness();
  await h.open();
  h.click('[data-act="fcfile"]');
  const box = h.box();
  box.value = "The response cache.\nNot the query cache.";
  let viewerSawEscape = 0;
  h.main.addEventListener("keydown", (ev) => { if (ev.key === "Escape") viewerSawEscape++; });
  const composing = h.key({ key: "Escape", isComposing: true });
  assert.equal(composing.defaultPrevented, false, "the IME's own default — cancelling the composition — is left to it");
  assert.equal(h.q(".fc-composer")!.hidden, false, "the composer stays open: this Escape was not a cancel");
  assert.equal(box.value, "The response cache.\nNot the query cache.", "the draft is untouched");
  assert.equal(viewerSawEscape, 0, "stopped at the box all the same: the viewer's document-level Escape, which closes the viewer with the draft in it, never fires");
  // the same key once the composition is over is the cancel it always was
  const plain = h.key({ key: "Escape" });
  assert.equal(plain.defaultPrevented, true);
  assert.equal(viewerSawEscape, 0);
  assert.equal(h.q(".fc-composer")!.hidden, true, "cancelled");
  assert.equal(box.value, "");
  // other composing keys are not the box's business and are not stopped either way (the IME's Enter commits, nothing saves)
  h.click('[data-act="fcfile"]');
  box.value = "Say which.";
  const before = h.posted.length;
  const commit = h.key({ key: "Enter", ctrlKey: true, isComposing: true });
  assert.equal(commit.defaultPrevented, false);
  await tick();
  assert.equal(h.posted.length, before, "no save from a composing Enter");
  h.dispose();
});

// ── the measurement leaves the scroll alone ────────────────────────────────────────────────────────

/** A box in a scrolled aside, as the browser lays them out: setting the box to `height: auto` collapses it, and the
 *  aside's scroll — near its bottom — is clamped in that shorter layout; putting the height back does not put it back. */
function scrolledBox(scrollHeight: number, asideTop: number) {
  const writes: number[] = [];
  const main = { scrollTop: 0, parentElement: null as unknown };
  const aside = { _top: asideTop, parentElement: main, get scrollTop() { return this._top; }, set scrollTop(v: number) { writes.push(v); this._top = v; } };
  const style = { _h: "" as string, get height() { return this._h; }, set height(v: string) { this._h = v; if (v === "auto") aside._top = Math.max(0, aside._top - 141); } };
  const ta = { style, parentElement: aside, scrollHeight, offsetHeight: scrollHeight ? scrollHeight + 2 : 0, clientHeight: scrollHeight };
  return { ta: ta as unknown as HTMLTextAreaElement, aside, main, writes };
}

test("autosizeComposer holds a scrolled ancestor's scroll across its height: auto measurement, on the measured path and the unmeasurable one", async () => {
  const { autosizeComposer } = await import("./file-comments");
  const grown = scrolledBox(168, 142);
  assert.equal(autosizeComposer(grown.ta), "170px", "sized as before");
  assert.equal(grown.aside.scrollTop, 142, "the aside is where the person scrolled it, not 1px from its top");
  assert.deepEqual(grown.writes, [142], "one write, after the new height is set");
  assert.equal(grown.main.scrollTop, 0, "an ancestor at its top has nothing to hold and is not written");
  // the box has no layout to measure: the height goes back, and so does the scroll
  const hidden = scrolledBox(0, 90);
  hidden.ta.style.height = "199.8px";
  assert.equal(autosizeComposer(hidden.ta), null);
  assert.equal(hidden.ta.style.height, "199.8px", "the inline height it had is put back");
  assert.equal(hidden.aside.scrollTop, 90, "…and the scroll with it");
  // nothing scrolled: nothing held, nothing written
  const top = scrolledBox(84, 0);
  assert.equal(autosizeComposer(top.ta), "86px");
  assert.deepEqual(top.writes, [], "an ancestor at scrollTop 0 cannot be clamped and is left alone");
});

// ── pinned at source ───────────────────────────────────────────────────────────────────────────────

test("source: every Escape stops at the box before the key policy runs; autosizeComposer holds the scrolled ancestors around the measurement", () => {
  assert.match(SRC, /if \(e\.key === "Escape"\) e\.stopPropagation\(\);\n\s*const act = composerKeyAction\(e\);/,
    "a composing Escape is null to composerKeyAction, so the stop comes before it, for every Escape");
  assert.match(SRC, /const held = scrolledAncestors\(ta\);\n\s*ta\.style\.height = "auto";/, "read before the collapse");
  assert.match(SRC, /if \(!\(sh > 0\)\) \{ ta\.style\.height = prev; restoreScroll\(held\); return null; \}/, "written back on the unmeasurable path");
  assert.match(SRC, /ta\.style\.height = h;\n\s*restoreScroll\(held\);\n\s*return h;/, "…and after the new height on the measured one");
  assert.match(SRC, /for \(let p = el\.parentElement; p; p = p\.parentElement\) if \(p\.scrollTop > 0\) out\.push\(\[p, p\.scrollTop\]\);/, "every scrolled ancestor, not one guessed scroller");
  assert.match(SRC, /for \(const \[p, top\] of held\) if \(p\.scrollTop !== top\) p\.scrollTop = top;/, "written back only where the layout moved it");
});

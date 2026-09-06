// Region comments on images, driven end to end through a DOM stand-in (plans/file-review.md, Slice 3;
// contract E5–E7): the panel is mounted over a media body or a rendered-markdown body, the overlay receives
// pointer events, the composer receives keys, and the kernel's replies arrive as window messages — the
// file-comments-panel.test.ts idiom, with the stand-in extended for what an overlay needs: a client rect per
// element, a picture's natural size, pointer events with coordinates, a canvas that records what it drew,
// and `matchMedia` for the coarse-pointer gate. What the stand-in cannot show (a real layout, the browser's
// synthesized click) is pinned at source. Synthetic fixtures only: the notes-api world, placeholder ids.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import type { FileViewActionCtx } from "./file-view";
import type { Status, StoreComment } from "./file-comments-model";

const web = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");

// ── the DOM stand-in ───────────────────────────────────────────────────────────────────────────────
type Rect = { left: number; top: number; right: number; bottom: number; width: number; height: number };
const rectOf = (left: number, top: number, width: number, height: number): Rect => ({ left, top, width, height, right: left + width, bottom: top + height });
const ZERO = rectOf(0, 0, 0, 0);
class Doc {
  body: E;
  hidden = false;
  listeners = new Map<string, Array<(ev: unknown) => void>>();
  constructor() { this.body = new E(this, "BODY"); }
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
/** What a canvas was asked to draw: drawImage's arguments, in order. */
const drawn: unknown[][] = [];
class E extends N {
  nodeType = 1;
  attrs = new Map<string, string>();
  listeners = new Map<string, Array<(ev: Ev) => void>>();
  hidden = false; title = ""; type = ""; disabled = false; placeholder = ""; value = ""; checked = false; offsetWidth = 0; tabIndex = -1;
  width = 0; height = 0;                              // a canvas
  naturalWidth = 0; naturalHeight = 0; complete: boolean | undefined = undefined;   // a picture
  rect: Rect | null = null;                          // the client rect a test gives the element
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
  }
  private classes(): string[] { return (this.attrs.get("class") || "").split(/\s+/).filter(Boolean); }
  private setClasses(c: string[]): void { this.attrs.set("class", [...new Set(c)].join(" ")); }
  get className(): string { return this.attrs.get("class") || ""; }
  set className(v: string) { this.attrs.set("class", v); }
  set innerHTML(html: string) { this.replaceChildren(...parseHTML(this.ownerDocument, html)); }
  getAttribute(n: string): string | null { return this.attrs.has(n) ? (this.attrs.get(n) as string) : null; }
  setAttribute(n: string, v: string): void { this.attrs.set(n, v); }
  removeAttribute(n: string): void { this.attrs.delete(n); }
  removeChild(n: N): N { const i = this.childNodes.indexOf(n); if (i >= 0) this.childNodes.splice(i, 1); n.parentNode = null; return n; }
  appendChild<X extends N>(n: X): X { if (n.parentNode) (n.parentNode as E).removeChild(n); this.childNodes.push(n); n.parentNode = this; return n; }
  insertBefore(n: N, ref: N | null): N {
    if (!ref) return this.appendChild(n);
    if (n.parentNode) (n.parentNode as E).removeChild(n);
    const i = this.childNodes.indexOf(ref);
    this.childNodes.splice(i, 0, n); n.parentNode = this; return n;
  }
  replaceChildren(...c: N[]): void { for (const x of this.childNodes) x.parentNode = null; this.childNodes = []; for (const x of c) this.appendChild(x); }
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
  /** The rect a test gave the element; a wrapper hugs its picture (the sheet's inline-block around a block img). */
  getBoundingClientRect(): Rect {
    if (this.rect) return this.rect;
    if (this.classList.contains("fc-imgwrap")) { const img = this.childNodes.find((c) => c instanceof E && c.tagName === "IMG") as E | undefined; return img ? img.getBoundingClientRect() : ZERO; }
    return ZERO;
  }
  setPointerCapture(): void { /* inert */ }
  releasePointerCapture(): void { /* inert */ }
  getContext(): { drawImage(...a: unknown[]): void } | null {
    return this.tagName === "CANVAS" ? { drawImage: (...a: unknown[]) => { drawn.push(a); } } : null;
  }
  scrollIntoView(): void { this.scrolled++; }
  focus(): void { /* inert */ }
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
/** The primary pointer a test claims: null leaves matchMedia absent (a desktop without it); true is a finger. */
let coarse: boolean | null = null;
win.matchMedia = (q: string) => { if (coarse === null) throw new TypeError("matchMedia is not a function"); return { matches: q === "(pointer: coarse)" && coarse }; };
(globalThis as any).window = win;
(globalThis as any).document = doc;
(globalThis as any).fetch = async () => ({ status: 404, headers: { get: () => null }, json: async () => [] });
const realSetInterval = globalThis.setInterval;
(globalThis as any).setInterval = (fn: () => void, ms: number) => { const t = realSetInterval(fn, ms); (t as any).unref?.(); return t; };
const tick = () => new Promise<void>((r) => setImmediate(r));

// ── fixtures: the notes-api world ──────────────────────────────────────────────────────────────────
const SID = "11111111-2222-3333-4444-555555555555";
const PNG = "/repo/notes-api/docs/figure.png";
const MD = "/repo/notes-api/docs/report.md";
const T0 = 1757145600000;
const H1 = "1111111111111111111111111111111111111111111111111111111111111111";
const H2 = "2222222222222222222222222222222222222222222222222222222222222222";
// the figure: a 600×400 picture drawn at half size, 100px in and 200px down
const IMG_RECT = rectOf(100, 200, 300, 200);
const REGION = { x: 0.1667, y: 0.2, w: 0.3333, h: 0.3 };   // the drag from (150,240) to (250,300) over IMG_RECT
const regionComment = (over: Partial<StoreComment> = {}, target: Record<string, unknown> = {}): StoreComment => ({
  id: T0 + "-0", author: "you", ts: T0, body: "The axis label is wrong.", replies: [], resolved: false,
  target: { kind: "image", region: REGION, hash: H1, ...target } as StoreComment["target"], ...over,
});
function pngStatus(over: Partial<Status> = {}): Status {
  return {
    verb: "status", root: "/repo/notes-api", storePath: "/repo/notes-api/.trackchanges/docs%2Ffigure.png.json",
    trackedBy: null, agentTooling: "present",
    fileMtimeNs: "1757145600000000001", storeMtimeNs: null, configMtimeNs: null,
    store: null, hunks: [], log: [], unsent: { comments: [], replies: [], accepted: 0, rejected: 0, watermark: null },
    fileHash: H1,
    ...over,
  };
}
const withStore = (comments: StoreComment[], path = "docs/figure.png"): Partial<Status> => ({
  storeMtimeNs: "1757145600000000002", store: { v: 3, path, suggestions: [], comments },
  unsent: { comments: comments.map((c) => c.id), replies: [], accepted: 0, rejected: 0, watermark: null },
});

// ── the harness ────────────────────────────────────────────────────────────────────────────────────
type Posted = Record<string, any>;
/** A mounted panel over a media body (`kind: "media"`: `.fileview-imgbox > img.fileview-img`) or a rendered-markdown
 *  body (`html` + `src`), inside the viewer's body row. */
async function harness(over: Partial<FileViewActionCtx> & { kind?: "media" | "rendered"; html?: string; src?: string; imgSrc?: string } = {}) {
  const fc = await import("./file-comments");
  const { kind = "media", html, src, imgSrc, ...ctxOver } = over;
  const main = doc.createElement("div"); main.className = "fileview-main";
  const body = doc.createElement("div"); body.className = "fileview-body"; main.appendChild(body);
  let media: E | null = null;
  if (kind === "media") {
    const box = doc.createElement("div"); box.className = "fileview-imgbox";
    media = doc.createElement("img"); media.className = "fileview-img"; media.setAttribute("src", imgSrc || "blob:romp/figure");
    media.rect = IMG_RECT; media.naturalWidth = 600; media.naturalHeight = 400; media.complete = true;
    box.appendChild(media); body.appendChild(box);
  } else if (html !== undefined) {
    const md = doc.createElement("div"); md.className = "fileview-md"; md.innerHTML = html; body.appendChild(md);
    for (const img of md.querySelectorAll("img")) { img.rect = IMG_RECT; img.naturalWidth = 600; img.naturalHeight = 400; img.complete = true; }
  }
  const posted: Posted[] = [];
  const closers: Array<() => void> = [];
  const saved: Array<(info: { mtimeNs: string; logged: boolean }) => void> = [];
  const rendered: Array<() => void> = [];
  const modes: string[] = [];
  let aside: E | null = null;
  const noop = () => { /* inert */ };
  const ctx: FileViewActionCtx = {
    path: kind === "media" ? PNG : MD, sid: SID, todoId: null,
    body: () => body as unknown as HTMLElement,
    mode: () => (kind === "media" ? "media" : "rendered"),
    text: () => (kind === "media" ? null : src === undefined ? null : src),
    mtimeNs: () => "1757145600000000001",
    media: () => (kind === "media" ? "image" : null),
    mediaElement: () => media as unknown as HTMLElement | null, renderedImages: () => [],
    identity: () => ({ name: "api", color: null }),
    onRendered: (cb) => { rendered.push(cb); }, onSelection: noop, onSaved: (cb) => { saved.push(cb); }, onClose: (cb) => { closers.push(cb); },
    post: (m) => { posted.push(m); }, ensureEditingAllowed: async () => true, setEditBlocked: noop,
    aside: (el) => { if (el) { aside = el as unknown as E; main.appendChild(aside); } else if (aside) { aside.remove(); aside = null; } },
    setMode: (m) => { modes.push(m); }, scrollToOffset: noop, reload: noop,
    ...ctxOver,
  };
  const unit = fc.fileCommentsAction.mount(ctx) as unknown as E;
  const button = unit.childNodes[0] as E;
  const last = (): Posted => posted[posted.length - 1];
  const reply = async (data: Record<string, unknown>) => { win.dispatchEvent(new MessageEvent("message", { data })); await tick(); await tick(); };
  const status = kind === "media" ? pngStatus : (o: Partial<Status> = {}) => pngStatus({ storePath: "/repo/notes-api/.trackchanges/docs%2Freport.md.json", fileHash: undefined, ...o });
  return {
    fc, main, body, unit, button, posted, modes, saved, rendered, last, media,
    ok: (o: Partial<Status> = {}) => reply({ type: "fileCommentsResult", reqId: last().reqId, ...status(o) }),
    refuse: (code: string, error: string) => reply({ type: "fileCommentsFailed", reqId: last().reqId, verb: last().verb, code, error }),
    q: (sel: string) => main.querySelector(sel),
    qa: (sel: string) => main.querySelectorAll(sel),
    click: (sel: string) => { const e = main.querySelector(sel); assert.ok(e, "a control " + sel); e!.dispatch("click"); },
    /** A drag on an overlay: press, move, release, then the click a browser synthesizes after it. */
    drag: (overlay: E, from: [number, number], to: [number, number]) => {
      overlay.dispatch("pointerdown", { clientX: from[0], clientY: from[1], pointerId: 7, button: 0 });
      overlay.dispatch("pointermove", { clientX: to[0], clientY: to[1], pointerId: 7 });
      overlay.dispatch("pointerup", { clientX: to[0], clientY: to[1], pointerId: 7 });
      return overlay.dispatch("click");
    },
    /** Open the panel: the button, then the status it re-asks. */
    open: async (o: Partial<Status> = {}) => { button.dispatch("click"); await reply({ type: "fileCommentsResult", reqId: last().reqId, ...status(o) }); },
    /** A fresh status the way the poll or a save brings one: the onSaved hook re-asks, the reply lands. */
    restatus: async (o: Partial<Status> = {}) => { saved[0]({ mtimeNs: "1757145600000000001", logged: true }); await tick(); await reply({ type: "fileCommentsResult", reqId: last().reqId, ...status(o) }); },
    float: () => { const f = doc.body.querySelectorAll(".fc-float"); return f[f.length - 1]; },
    input: () => main.querySelector("input.fc-input")!,
    dispose: () => { for (const cb of closers) cb(); },
  };
}
const styleOf = (e: E): string => e.getAttribute("style") || "";

// ── a standalone image ─────────────────────────────────────────────────────────────────────────────

test("a standalone image: the overlay wraps the picture after status, and the empty state names the drag", async () => {
  drawn.length = 0;
  const h = await harness();
  await h.ok();
  const wrap = h.q(".fileview-imgbox .fc-imgwrap")!;
  assert.ok(wrap, "the probe's status paints: a wrapper where the picture was, as the highlights would paint on a text file");
  assert.equal(wrap.childNodes[0], h.media, "the picture inside it");
  const overlay = wrap.querySelector(".fc-overlay")!;
  assert.ok(overlay, "the overlay beside it");
  assert.equal(overlay.classList.contains("fc-overlay-off"), true, "the panel is closed: no drag, the picture is the browser's");
  const idle = h.posted.length;
  h.drag(overlay, [150, 240], [250, 300]);
  assert.equal(h.q(".fc-composer"), null, "a drag on a closed panel draws nothing");
  assert.equal(h.posted.length, idle);
  await h.open();
  assert.equal(overlay.classList.contains("fc-overlay-off"), false, "open, with a fine pointer: the overlay draws");
  assert.equal(overlay.getAttribute("aria-label"), "Drag to comment on a region of the image");
  assert.equal(overlay.getAttribute("style"), null, "the wrapper hugs the picture: the sheet's inset: 0 places the overlay, no inline offsets");
  assert.equal(h.q(".fc-empty")!.textContent, "No comments yet. Drag a rectangle on the image, or comment on this file.");
  assert.equal(h.qa(".fc-imgwrap").length, 1, "one wrapper per picture, however many paints");
  await h.restatus();
  assert.equal(h.qa(".fc-imgwrap").length, 1, "a re-paint reuses the layer, never wraps twice");
  h.button.dispatch("click");                          // close the panel
  assert.equal(overlay.classList.contains("fc-overlay-off"), true, "closed again: disarmed, the rectangles would stay");
  h.dispose();
  assert.equal(h.q(".fc-imgwrap"), null, "closing the viewer takes the overlay down and puts the picture back");
  assert.equal(h.q(".fileview-imgbox img"), h.media);
});

test("a drag on a standalone image opens the composer on the region, Enter saves comment {target, note} with no anchor, and the card and rectangle follow", async () => {
  drawn.length = 0;
  const h = await harness();
  await h.ok();
  await h.open();
  const overlay = h.q(".fc-overlay")!;
  // press, move: a rubber band placed by percentages of the drawn image
  overlay.dispatch("pointerdown", { clientX: 150, clientY: 240, pointerId: 7, button: 0 });
  overlay.dispatch("pointermove", { clientX: 250, clientY: 300, pointerId: 7 });
  const band = overlay.querySelector(".fc-draw")!;
  assert.ok(band, "the band shows while dragging");
  assert.equal(styleOf(band), "left: 16.67%; top: 20.00%; width: 33.33%; height: 30.00%;");
  overlay.dispatch("pointerup", { clientX: 250, clientY: 300, pointerId: 7 });
  assert.equal(overlay.querySelector(".fc-draw"), null, "the band leaves with the release");
  const click = overlay.dispatch("click");
  assert.equal(click.defaultPrevented, true, "the click a browser synthesizes after the drag is swallowed before the delegate root sees it");
  const box = h.q(".fc-composer")!;
  assert.equal(box.hidden, false, "the composer opens");
  assert.equal(h.q(".fc-composer-ref .fc-note")!.textContent, "On the region at 0.17, 0.20, 0.33, 0.30", "two decimals shown");
  const crop = h.q(".fc-composer-ref canvas.fc-crop")!;
  assert.ok(crop, "the region cut from the picture, in the composer too");
  assert.deepEqual(drawn[drawn.length - 1].slice(1, 5), [100, 80, 200, 120], "the crop's source rectangle in natural pixels");
  const pending = overlay.querySelector(".fc-region-pending")!;
  assert.ok(pending, "the pending region shows on the picture");
  assert.equal(pending.getAttribute("data-act"), null, "and is not a control");
  // Enter: comment {note, target} — fractions of the natural size, no anchor, no hash (the host stamps it)
  h.input().value = "The axis label is wrong.";
  h.input().dispatch("keydown", { key: "Enter" });
  await tick();
  const c = h.last();
  assert.equal(c.verb, "comment");
  assert.deepEqual(c.args, { note: "The axis label is wrong.", target: { kind: "image", region: REGION } });
  assert.deepEqual(c.fence, { storeMtimeNs: "", configMtimeNs: "", figureHash: H1 }, "no sidecar yet: the fence says so — and names the picture's bytes as the status read them");
  await h.ok(withStore([regionComment()]));
  assert.equal(box.hidden, true, "saved: the composer closes");
  assert.equal(overlay.querySelector(".fc-region-pending"), null);
  const rect = overlay.querySelector('.fc-region[data-act="fcopen"][data-id="' + T0 + '-0"]')!;
  assert.ok(rect, "one rectangle per region comment, a control that opens the card");
  assert.equal(styleOf(rect), "left: 16.67%; top: 20.00%; width: 33.33%; height: 30.00%;", "placed by percentages: right at any width");
  assert.equal(rect.classList.contains("fc-stale"), false);
  assert.equal(rect.classList.contains("fc-unknown"), false);
  assert.equal(rect.tabIndex, 0, "a Tab stop (Enter opens it through KEY_ACTS)");
  const chip = rect.querySelector(".fc-region-chip")!;
  assert.equal(chip.getAttribute("data-label"), "you", "the author chip, drawn by the sheet from data-label");
  assert.equal(chip.childNodes.length, 0, "no text node under the picture");
  const card = h.q('.fc-card[data-id="' + T0 + '-0"]')!;
  assert.equal(card.querySelector(".fc-ref")!.textContent, "the region at 0.17, 0.20, 0.33, 0.30");
  assert.equal(card.querySelector(".fc-ref")!.getAttribute("data-act"), "fcgoto", "the reference scrolls to the rectangle");
  assert.equal(card.querySelector(".fc-tag"), null, "current: no stale or unknown tag");
  // the rectangle opens its card through the delegate root — it is the panel's own (owns)
  rect.dispatch("click");
  assert.ok(card.classList.contains("open") || h.q('.fc-card.open[data-id="' + T0 + '-0"]'), "the card opened");
  const open = h.q('.fc-card.open[data-id="' + T0 + '-0"]')!;
  assert.ok(open.querySelector("canvas.fc-crop"), "the open card shows the crop");
  assert.ok(open.querySelector('[data-act="fcreplace"]'), "and offers Re-place");
  assert.equal(open.querySelector('[data-act="fcreveal"]'), null, "the rectangle is in view: nothing to reveal");
  h.dispose();
});

test("the stale tag flips with the file's hash on the next status: stale (dashed) when it differs, unknown when the host has none", async () => {
  drawn.length = 0;
  const h = await harness();
  await h.ok(withStore([regionComment()]));
  await h.open(withStore([regionComment()]));
  const id = T0 + "-0";
  const rect = () => h.q('.fc-region[data-id="' + id + '"]')!;
  const tags = () => h.q('.fc-card[data-id="' + id + '"] .fc-card-head')!.querySelectorAll(".fc-tag").map((t) => t.textContent);
  assert.deepEqual(tags(), [], "hash h1 stored, h1 current");
  await h.restatus({ ...withStore([regionComment()]), fileHash: H2 });
  assert.equal(rect().classList.contains("fc-stale"), true, "the picture's bytes changed: dashed");
  assert.deepEqual(tags(), ["stale"]);
  h.click('.fc-card[data-id="' + id + '"] .fc-card-head');
  const rp = h.q('.fc-card.open [data-act="fcreplace"]')!;
  assert.match(rp.title, /The image changed/);
  await h.restatus({ ...withStore([regionComment()]), fileHash: null });
  assert.equal(rect().classList.contains("fc-stale"), false, "null is unknown, never stale (E2)");
  assert.equal(rect().classList.contains("fc-unknown"), true);
  assert.deepEqual(tags(), ["unknown"]);
  await h.restatus({ ...withStore([regionComment()]), fileHash: H1 });
  assert.deepEqual(tags(), [], "back to current");
  assert.equal(rect().classList.contains("fc-unknown"), false);
  // a resolved region paints no rectangle, like a resolved passage
  await h.restatus(withStore([regionComment({ resolved: true })]));
  assert.equal(h.q(".fc-region"), null);
  h.dispose();
});

test("Re-place: the next drag on the picture sends retarget {commentId, target}; the words stay, Cancel keeps the region", async () => {
  drawn.length = 0;
  const h = await harness();
  await h.ok(withStore([regionComment()]));
  await h.open(withStore([regionComment()]));
  const id = T0 + "-0";
  h.click('.fc-card[data-id="' + id + '"] .fc-card-head');
  h.click('.fc-card.open [data-act="fcreplace"]');
  const box = h.q(".fc-composer")!;
  assert.equal(box.hidden, false, "the composer box carries the instruction");
  assert.equal(h.input().hidden, true, "a re-place takes a drag, not words");
  assert.match(h.q(".fc-composer-ref .fc-note")!.textContent, /^Drag the comment's new place on the image \(now the region at 0\.17, 0\.20, 0\.33, 0\.30\)\./);
  assert.equal(h.q('.fc-composer [data-act="fcsave"]'), null, "nothing to save");
  const overlay = h.q(".fc-overlay")!;
  assert.equal(overlay.classList.contains("fc-replacing"), true, "the overlay wears the cue");
  // Cancel first: nothing sent, the cue leaves
  const before = h.posted.length;
  h.click('.fc-composer [data-act="fccancel"]');
  assert.equal(box.hidden, true);
  assert.equal(overlay.classList.contains("fc-replacing"), false);
  assert.equal(h.posted.length, before);
  // again, and draw: (110,210)→(190,260) over the 300×200 picture at (100,200)
  h.click('.fc-card.open [data-act="fcreplace"]');
  h.drag(overlay, [110, 210], [190, 260]);
  await tick();
  const r = h.last();
  assert.equal(r.verb, "retarget");
  assert.deepEqual(r.args, { commentId: id, target: { kind: "image", region: { x: 0.0333, y: 0.05, w: 0.2667, h: 0.25 } } });
  assert.deepEqual(r.fence, { storeMtimeNs: "1757145600000000002", configMtimeNs: "", figureHash: H1 }, "fenced on the sidecar (E3) and on the picture's bytes");
  assert.equal(box.hidden, true, "the composer box closes with the drag");
  assert.equal(h.input().hidden, false, "the input is back for the next note");
  const moved = regionComment({}, { region: { x: 0.0333, y: 0.05, w: 0.2667, h: 0.25 }, hash: H2 });
  await h.ok({ ...withStore([moved]), fileHash: H2 });
  const rect = h.q('.fc-region[data-id="' + id + '"]')!;
  assert.equal(styleOf(rect), "left: 3.33%; top: 5.00%; width: 26.67%; height: 25.00%;", "the rectangle moved");
  assert.equal(rect.classList.contains("fc-stale"), false, "re-placed on the current bytes: current again");
  assert.equal(h.q('.fc-card[data-id="' + id + '"] .fc-body')!.textContent, "The axis label is wrong.", "the words stayed");
  h.dispose();
});

test("a press that does not move is not a region: on a standalone image it does nothing, and a press on a rectangle leaves the click to the card", async () => {
  drawn.length = 0;
  const h = await harness();
  await h.ok(withStore([regionComment()]));
  await h.open(withStore([regionComment()]));
  const overlay = h.q(".fc-overlay")!;
  const before = h.posted.length;
  overlay.dispatch("pointerdown", { clientX: 150, clientY: 240, pointerId: 7, button: 0 });
  overlay.dispatch("pointermove", { clientX: 152, clientY: 241, pointerId: 7 });
  assert.equal(overlay.querySelector(".fc-draw"), null, "below the threshold: no band");
  overlay.dispatch("pointerup", { clientX: 152, clientY: 241, pointerId: 7 });
  const click = overlay.dispatch("click");
  assert.equal(click.defaultPrevented, false, "a click, left alone");
  assert.equal(h.q(".fc-composer")!.hidden, true, "no composer");
  assert.equal(h.float().hidden, true, "no Comment offer: a standalone image has no embed line");
  assert.equal(h.posted.length, before);
  // a press on the rectangle: the layer hands the click on (nothing of its own is drawn or swallowed), and the delegate's
  // click opens the card — the browser-driven pins are file-comments-regions-click.test.ts and -browser.test.ts
  const rect = h.q(".fc-region")!;
  rect.dispatch("pointerdown", { clientX: 160, clientY: 250, pointerId: 8, button: 0 });
  rect.dispatch("pointerup", { clientX: 160, clientY: 250, pointerId: 8 });
  rect.dispatch("click");
  assert.ok(h.q('.fc-card.open[data-id="' + T0 + '-0"]'), "the card opened through fcopen");
  assert.equal(h.q(".fc-composer")!.hidden, true);
  // a cancelled pointer draws nothing
  overlay.dispatch("pointerdown", { clientX: 150, clientY: 240, pointerId: 9, button: 0 });
  overlay.dispatch("pointermove", { clientX: 250, clientY: 300, pointerId: 9 });
  overlay.dispatch("pointercancel", { clientX: 250, clientY: 300, pointerId: 9 });
  assert.equal(overlay.querySelector(".fc-draw"), null);
  assert.equal(h.q(".fc-composer")!.hidden, true);
  h.dispose();
});

test("a coarse pointer: the overlay takes no drag (the whole-file comment stands in), the rectangles still open their cards", async () => {
  coarse = true;
  try {
    drawn.length = 0;
    const h = await harness();
    await h.ok(withStore([regionComment()]));
    await h.open(withStore([regionComment()]));
    const overlay = h.q(".fc-overlay")!;
    assert.equal(overlay.classList.contains("fc-overlay-off"), true, "pointer-events: none through the sheet");
    assert.equal(overlay.getAttribute("aria-label"), null, "no drawing affordance claimed");
    const before = h.posted.length;
    h.drag(overlay, [150, 240], [250, 300]);
    assert.equal(h.q(".fc-composer")!.hidden, true, "no composer: nothing listens");
    assert.equal(h.posted.length, before);
    assert.ok(h.q('.fc-region[data-act="fcopen"]'), "the rectangle is still painted");
    h.click(".fc-region");
    assert.ok(h.q('.fc-card.open[data-id="' + T0 + '-0"]'), "and still opens its card");
    assert.equal(h.q('.fc-card.open [data-act="fcreplace"]'), null, "no Re-place where nothing can be drawn");
    h.dispose();
    const h2 = await harness();
    await h2.ok();
    await h2.open();
    assert.equal(h2.q(".fc-empty")!.textContent, "No comments yet. Comment on this file to leave one.", "the empty state names no gesture the pointer cannot make");
    h2.dispose();
  } finally { coarse = null; }
});

test("a write about a figure is fenced on its bytes: figure-changed is never retried — the comments and the view are re-read, the row offers Reload, the note stays, and the next Enter carries the new hash; a status with no hash fences on the mtimes alone", async () => {
  drawn.length = 0;
  let reloads = 0;
  const h = await harness({ reload: () => { reloads++; } });
  await h.ok();
  await h.open();
  const overlay = h.q(".fc-overlay")!;
  const asks = () => h.posted.filter((m) => m.type === "fileComments" && m.verb === "status").length;
  const writes = () => h.posted.filter((m) => m.type === "fileComments" && m.verb === "comment").length;
  h.drag(overlay, [150, 240], [250, 300]);
  h.input().value = "The axis label is wrong.";
  h.input().dispatch("keydown", { key: "Enter" });
  await tick();
  assert.equal(h.last().verb, "comment");
  assert.equal(h.last().fence.figureHash, H1, "the hash the status holds for the picture");
  const n0 = asks();
  // the figure was regenerated between the drag and Enter: the host hashed other bytes than the fence names
  await h.refuse("figure-changed", "docs/figure.png changed on disk since it was shown — reload to see it as it is now, then draw the region again; nothing was changed");
  assert.equal(writes(), 1, "never retried: a retry would stamp the new bytes with a rectangle drawn on the old ones");
  assert.equal(asks(), n0 + 1, "the comments are re-read, as after a figure the poll saw move");
  assert.equal(reloads, 1, "and so is the view, so the new picture shows");
  await h.ok({ fileHash: H2 });
  const row = h.q('.fc-composer .fc-err[data-slot="composer"]')!;
  assert.ok(row, "the refusal shows under the composer");
  assert.match(row.textContent, /^docs\/figure\.png changed on disk since it was shown/);
  assert.ok(row.querySelector('[data-act="fcreload"]'), "with Reload, as every moved fence offers");
  assert.equal(h.q(".fc-composer")!.hidden, false, "the composer stays open");
  assert.equal(h.input().value, "The axis label is wrong.", "the note stays where it was typed");
  // drawn again on the new picture: the fence names the bytes the fresh status read
  h.drag(overlay, [150, 240], [250, 300]);
  h.input().value = "The axis label is wrong.";
  h.input().dispatch("keydown", { key: "Enter" });
  await tick();
  assert.equal(h.last().verb, "comment");
  assert.equal(h.last().fence.figureHash, H2);
  await h.ok(withStore([regionComment({}, { hash: H2 })]));
  assert.equal(h.q(".fc-composer")!.hidden, true, "saved");
  // a status with no hash for the picture (past the cap, unreadable, an older host): nothing to fence on, so nothing is sent
  await h.restatus({ ...withStore([regionComment({}, { hash: H2 })]), fileHash: null });
  h.drag(overlay, [110, 210], [190, 260]);
  h.input().value = "Second note.";
  h.input().dispatch("keydown", { key: "Enter" });
  await tick();
  assert.equal(h.last().verb, "comment");
  assert.deepEqual(h.last().fence, { storeMtimeNs: "1757145600000000002", configMtimeNs: "" }, "the mtime keys alone: a fence the panel cannot arm is left off, never guessed");
  h.dispose();
});

// ── a figure embedded in rendered markdown ─────────────────────────────────────────────────────────
const REPORT = "## Findings\n\n![Figure](figure.png)\n\nWe recommend shipping the cache in v1.2.\n";
const REPORT_HTML = '<h2>Findings</h2>\n<p><img src="figure.png" alt="Figure"></p>\n<p>We recommend shipping the cache in v1.2.</p>\n';
const passage: StoreComment = {
  id: T0 + "-118", author: "you", ts: T0 + 1000, body: "Which cache? Say which.",
  anchor: { quote: "shipping the cache in v1.2", prefix: "We recommend ", suffix: "." }, replies: [], resolved: false,
};
const embedded = (over: Partial<StoreComment> = {}, target: Record<string, unknown> = {}): StoreComment => regionComment({
  anchor: { quote: "![Figure](figure.png)", prefix: "## Findings\n\n", suffix: "\n\nWe recommend shipping" }, ...over,
}, { src: "figure.png", ...target });

test("a figure in rendered markdown: the drag's comment carries BOTH the embed line's anchor and target.src; staleness reads embeddedHashes", async () => {
  drawn.length = 0;
  const h = await harness({ kind: "rendered", html: REPORT_HTML, src: REPORT });
  await h.ok({ embeddedHashes: {} });
  await h.open({ embeddedHashes: {} });
  const img = h.q(".fileview-md img")!;
  const wrap = img.parentNode as E;
  assert.equal(wrap.className, "fc-imgwrap", "the figure is wrapped where it stood, inside its paragraph");
  assert.equal(wrap.parentNode, h.q(".fileview-md p"), "the paragraph still holds it");
  const overlay = wrap.querySelector(".fc-overlay")!;
  h.drag(overlay, [150, 240], [250, 300]);
  assert.equal(h.q(".fc-composer")!.hidden, false);
  assert.equal(h.q(".fc-composer-ref .fc-note")!.textContent, "On the region at 0.17, 0.20, 0.33, 0.30");
  h.input().value = "The axis label is wrong.";
  h.input().dispatch("keydown", { key: "Enter" });
  await tick();
  const c = h.last();
  assert.equal(c.verb, "comment");
  assert.deepEqual(c.args.target, { kind: "image", region: REGION, src: "figure.png" }, "src exactly as the embed writes it");
  assert.deepEqual(c.args.anchor, { quote: "![Figure](figure.png)", prefix: "## Findings\n\n", suffix: "\n\nWe recommend shipping " }, "the embed line's anchor, 24 characters of context");
  assert.equal(c.args.hintOffset, REPORT.indexOf("![Figure]"));
  assert.deepEqual(c.fence, { storeMtimeNs: "", configMtimeNs: "" }, "the first comment on a figure: the status hashes only the figures the sidecar names, so there is no hash to fence on yet");
  await h.ok({ ...withStore([embedded(), passage], "docs/report.md"), embeddedHashes: { "figure.png": H1 } });
  const rect = overlay.querySelector('.fc-region[data-id="' + T0 + '-0"]')!;
  assert.ok(rect, "the rectangle on the figure");
  assert.equal(rect.classList.contains("fc-stale"), false);
  assert.equal(img.classList.contains("fc-hl"), false, "the rectangle is the mark: the embed's picture is not framed as well");
  assert.equal(h.qa('.fc-hl[data-id="' + T0 + '-0"]').length, 0, "and no text highlight doubles it");
  assert.ok(h.q('.fc-hl[data-id="' + passage.id + '"]'), "the passage comment in the next paragraph still paints with the overlay in place");
  const card = h.q('.fc-card[data-id="' + T0 + '-0"]')!;
  assert.equal(card.querySelector(".fc-ref")!.getAttribute("data-act"), "fcgoto");
  assert.equal(card.querySelector(".fc-tag"), null);
  // the figure regenerated: its entry changes, the rectangle goes dashed
  await h.restatus({ ...withStore([embedded(), passage], "docs/report.md"), embeddedHashes: { "figure.png": H2 } });
  assert.equal(overlay.querySelector('.fc-region[data-id="' + T0 + '-0"]')!.classList.contains("fc-stale"), true);
  assert.deepEqual(h.q('.fc-card[data-id="' + T0 + '-0"] .fc-card-head')!.querySelectorAll(".fc-tag").map((t) => t.textContent), ["stale"]);
  // a plain click on the figure still offers Comment on its embed line; the next press hides the offer (the overlay
  // cancels the compat mousedown the float's own hide listens for, so the layer says so itself)
  overlay.dispatch("pointerdown", { clientX: 150, clientY: 240, pointerId: 7, button: 0 });
  overlay.dispatch("pointerup", { clientX: 151, clientY: 240, pointerId: 7 });
  assert.equal(h.float().hidden, false, "the float shows beside the figure");
  overlay.dispatch("pointerdown", { clientX: 150, clientY: 240, pointerId: 8, button: 0 });
  assert.equal(h.float().hidden, true, "a press hides it");
  overlay.dispatch("pointercancel", { clientX: 150, clientY: 240, pointerId: 8 });
  // Re-place on the stale figure: the retarget is fenced on the bytes the status holds for THIS figure (embeddedHashes[src])
  h.click('.fc-card[data-id="' + T0 + '-0"] .fc-card-head');
  h.click('.fc-card.open[data-id="' + T0 + '-0"] [data-act="fcreplace"]');
  h.drag(overlay, [110, 210], [190, 260]);
  await tick();
  assert.equal(h.last().verb, "retarget");
  assert.deepEqual(h.last().fence, { storeMtimeNs: "1757145600000000002", configMtimeNs: "", figureHash: H2 }, "the figure's current hash, by its src");
  h.dispose();
});

test("a figure whose src the viewer rewrote through /file still matches its embed (the seam's E4 rewrite), and a figure with no embed refuses with the note kept", async () => {
  drawn.length = 0;
  const rewritten = '<h2>Findings</h2>\n<p><img src="/file?path=%2Frepo%2Fnotes-api%2Fdocs%2Ffigure.png&amp;sid=' + SID + '" alt="Figure"></p>\n<p><img src="https://example.invalid/chart.png" alt="Chart"></p>\n';
  const h = await harness({ kind: "rendered", html: rewritten, src: REPORT });
  await h.ok({ embeddedHashes: {} });
  await h.open({ embeddedHashes: {} });
  const [fig, chart] = h.qa(".fileview-md img");
  h.drag((fig.parentNode as E).querySelector(".fc-overlay")!, [150, 240], [250, 300]);
  h.input().value = "Axis.";
  h.input().dispatch("keydown", { key: "Enter" });
  await tick();
  assert.equal(h.last().verb, "comment");
  assert.deepEqual(h.last().args.target, { kind: "image", region: REGION, src: "figure.png" }, "matched to its embed through the /file path");
  assert.deepEqual(h.last().args.anchor.quote, "![Figure](figure.png)");
  await h.ok({ ...withStore([embedded()], "docs/report.md"), embeddedHashes: { "figure.png": H1 } });
  assert.ok((fig.parentNode as E).querySelector('.fc-region[data-id="' + T0 + '-0"]'), "and painted back on that figure");
  // the second picture has no embed in the source: the region cannot be anchored, the reason is shown, Save is withheld
  h.drag((chart.parentNode as E).querySelector(".fc-overlay")!, [150, 240], [250, 300]);
  assert.equal(h.q(".fc-composer")!.hidden, false);
  assert.match(h.q(".fc-composer-ref .fc-refused")!.textContent, /^The line that embeds this image was not found in the source, so a region on it cannot be saved\./);
  assert.equal(h.q('.fc-composer [data-act="fcsave"]'), null, "Save withheld: it would have nothing to anchor to");
  assert.equal((chart.parentNode as E).querySelector(".fc-region-pending"), null, "a refused region is not shown as pending");
  const before = h.posted.length;
  h.input().value = "Wrong chart.";
  h.input().dispatch("keydown", { key: "Enter" });
  await tick();
  assert.equal(h.posted.length, before, "Enter saves nothing");
  assert.equal(h.q(".fc-composer .fc-err")!.textContent.startsWith("Nothing saved: the line that embeds this image was not found"), true);
  assert.equal(h.input().value, "Wrong chart.", "the note stays");
  h.dispose();
});

test("Re-place on an embedded figure refuses a drag on another figure: the anchor is on this figure's embed line", async () => {
  drawn.length = 0;
  const two = '<p><img src="figure.png" alt="Figure"></p>\n<p><img src="other.png" alt="Other"></p>\n';
  const src = "![Figure](figure.png)\n\n![Other](other.png)\n";
  const h = await harness({ kind: "rendered", html: two, src });
  const cm = embedded({ anchor: { quote: "![Figure](figure.png)", prefix: "", suffix: "\n\n![Other](other.png)\n" } });
  await h.ok({ ...withStore([cm], "docs/report.md"), embeddedHashes: { "figure.png": H1 } });
  await h.open({ ...withStore([cm], "docs/report.md"), embeddedHashes: { "figure.png": H1 } });
  const [fig, other] = h.qa(".fileview-md img");
  h.click('.fc-card[data-id="' + T0 + '-0"] .fc-card-head');
  h.click('.fc-card.open [data-act="fcreplace"]');
  assert.equal((fig.parentNode as E).querySelector(".fc-overlay")!.classList.contains("fc-replacing"), true, "the cue on the comment's own figure");
  assert.equal((other.parentNode as E).querySelector(".fc-overlay")!.classList.contains("fc-replacing"), false, "not on the other");
  const before = h.posted.length;
  h.drag((other.parentNode as E).querySelector(".fc-overlay")!, [150, 240], [250, 300]);
  assert.equal(h.posted.length, before, "nothing sent");
  assert.equal(h.q('.fc-card.open .fc-err')!.childNodes[0].textContent, "Draw the new place on the figure this comment is on, not on another one.");
  h.drag((fig.parentNode as E).querySelector(".fc-overlay")!, [150, 240], [250, 300]);
  await tick();
  assert.equal(h.last().verb, "retarget");
  assert.deepEqual(h.last().args, { commentId: T0 + "-0", target: { kind: "image", region: REGION, src: "figure.png" } }, "the src rides along, so the host hashes the same figure");
  h.dispose();
});

// ── the embed matcher, pure ────────────────────────────────────────────────────────────────────────

test("srcIsEmbed: the authored dest, its percent-encoded twin, or the /file rewrite against the file's directory", async () => {
  const { srcIsEmbed, embedPath, fileUrlPath, normPath } = await import("./file-comments");
  assert.equal(normPath("/repo/notes-api/docs/../docs/./figure.png"), "/repo/notes-api/docs/figure.png");
  assert.equal(normPath("a//b/../c"), "a/c");
  assert.equal(normPath("../x"), "../x", "a relative path may still climb");
  assert.equal(embedPath(MD, "figure.png"), "/repo/notes-api/docs/figure.png");
  assert.equal(embedPath(MD, "./img/fig%20a.png"), "/repo/notes-api/docs/img/fig a.png", "decoded for comparison");
  assert.equal(embedPath(MD, "../assets/fig.png"), "/repo/notes-api/assets/fig.png");
  assert.equal(embedPath(MD, "/abs/fig.png"), "/abs/fig.png");
  assert.equal(embedPath("report.md", "fig.png"), "fig.png", "a file with no directory");
  assert.equal(fileUrlPath("/file?path=%2Frepo%2Fnotes-api%2Fdocs%2Ffigure.png&sid=" + SID), "/repo/notes-api/docs/figure.png");
  assert.equal(fileUrlPath("/remote/TESTHOST/file?sid=x&path=%2Fa%2Fb.png"), "/a/b.png", "a federated relay URL too");
  assert.equal(fileUrlPath("figure.png"), null);
  assert.equal(fileUrlPath("https://example.invalid/file.png?path=x"), null, "only a /file route");
  assert.equal(srcIsEmbed("figure.png", "figure.png", MD), true);
  assert.equal(srcIsEmbed("fig%20a.png", "fig a.png", MD), true, "marked percent-encodes the destination");
  assert.equal(srcIsEmbed("/file?path=%2Frepo%2Fnotes-api%2Fdocs%2Ffigure.png&sid=" + SID, "figure.png", MD), true);
  assert.equal(srcIsEmbed("/file?path=%2Frepo%2Fnotes-api%2Fassets%2Ffig.png", "../assets/fig.png", MD), true);
  assert.equal(srcIsEmbed("/file?path=%2Frepo%2Fnotes-api%2Fdocs%2Fother.png", "figure.png", MD), false);
  assert.equal(srcIsEmbed("/file?path=%2Frepo%2Fnotes-api%2Fdocs%2Ffigure.png", "figure.png", null), false, "no file path to resolve against: no match claimed");
  assert.equal(srcIsEmbed("https://example.invalid/chart.png", "figure.png", MD), false);
});

// ── source pins: what the stand-in cannot show ─────────────────────────────────────────────────────

test("source pins: the overlay's wiring (data-act names, the coarse gate, the seam member, retarget on Re-place, the composer's target path)", () => {
  const SRC = web("file-comments.ts");
  const OVL = web("file-comments-regions.ts");
  // the seam member, by name (contract E4), read only in media mode; figures come from the rendered root
  assert.match(SRC, /const m = this\.ctx\.mediaElement\(\);/);
  assert.match(SRC, /if \(mode === "rendered"\) \{ const root = this\.contentRoot\(\); return root \? \(imgsIn\(root\) as HTMLImageElement\[\]\) : \[\]; \}/);
  // the coarse-pointer gate: matchMedia in the overlay module, consulted once per paint; the drag armed only while
  // the panel is open AND the pointer is fine; a press on a disarmed overlay does nothing
  assert.match(OVL, /return window\.matchMedia\("\(pointer: coarse\)"\)\.matches;/);
  assert.match(SRC, /const active = this\.open && !isCoarsePointer\(\);/);
  assert.match(SRC, /layer\.setActive\(active\);/);
  assert.match(OVL, /this\.overlay\.classList\.toggle\("fc-overlay-off", !on\);/);
  assert.match(OVL, /if \(!this\.active \|\| \(ev\.button \|\| 0\) !== 0\) return;/);
  assert.match(SRC, /this\.paintRegions\(\);\s*\/\/ arm the overlays' drag/, "openPanel arms");
  assert.match(SRC, /this\.paintRegions\(\);\s*\/\/ disarm/, "closePanel disarms");
  // the rectangles: data-act="fcopen" + data-id, a Tab stop, the chip from data-label with no text node
  assert.match(OVL, /r\.dataset\.act = "fcopen"; r\.dataset\.id = m\.id;/);
  assert.match(OVL, /r\.tabIndex = 0; r\.setAttribute\("role", "button"\);/);
  assert.match(OVL, /chip\.dataset\.label = m\.label;/);
  assert.doesNotMatch(OVL, /createTextNode|textContent =/, "no text node ever enters the picture's paragraph");
  // pointer events on the overlay, capture, the synthesized click swallowed after a drag
  for (const ev of ["pointerdown", "pointermove", "pointerup", "pointercancel"]) assert.ok(OVL.includes('o.addEventListener("' + ev + '"'), ev);
  assert.match(OVL, /o\.setPointerCapture\(ev\.pointerId\)/);
  assert.match(OVL, /this\.sizer = new ResizeObserver\(\(\) => this\.place\(\)\); this\.sizer\.observe\(img\);/, "the drawn size's own event re-measures the overlay");
  assert.match(SRC, /onPress: \(\) => \{ this\.float\.hidden = true; this\.imageTarget = null; \}/);
  assert.match(OVL, /o\.addEventListener\("click", \(ev: Event\) => \{ if \(this\.drew\) \{ this\.drew = false; ev\.stopPropagation\(\); ev\.preventDefault\(\); \} \}\);/);
  // the panel: the Re-place act, retarget with the comment's src, the composer's target path with the embed anchor
  assert.match(SRC, /fcreplace: \(x, ev\) => \{ ev\.stopPropagation\(\); this\.startReplace\(x\.dataset\.id!\); \}/);
  assert.match(SRC, /void this\.mutate\("retarget", \{ commentId: c\.commentId, target: regionTarget\(region, c\.src\) \}, "card:" \+ c\.commentId\);/);
  assert.match(SRC, /const args: Record<string, unknown> = \{ note, target: regionTarget\(c\.region, c\.src\) \};\n\s*if \(c\.range && c\.text !== undefined\) \{ args\.anchor = makeAnchor\(c\.text, c\.range\); args\.hintOffset = c\.range\.start; \}/);
  assert.match(SRC, /const e = root && t !== null \? embedFor\(img, root, t, this\.ctx\.path\) : null;/, "the embed found the way the picture click finds it");
  // every rectangle is registered as the panel's own, so the delegate routes its click
  assert.match(SRC, /for \(const r of layer\.paint\(per\.get\(img\) \|\| \[\], pending, replacing\)\) this\.mark\(r\);/, "every rectangle is the panel's own (owns), and registered for the document's listeners (panelMark)");
  assert.match(SRC, /this\.regionLayers\.set\(img, layer\);\n\s*this\.mark\(layer\.overlay\);/, "so is the overlay the browser's own click lands on after a handed-on press");
  // the overlay pass runs for a media body (where the text pass has nothing to paint) and after the text pass
  assert.match(SRC, /if \(src === null \|\| !root\) \{ this\.paintRegions\(\); this\.render\(\); return; \}/);
  assert.match(SRC, /this\.paintPresel\(root, src, rendered\);\n\s*this\.paintRegions\(\);\n\s*this\.render\(\);/);
  // the region card: a region's picture is not ALSO framed; the stale tag from regionState; Reveal scrolls to the picture
  assert.match(SRC, /if \(!painted && rendered && !card\.target\) \{/);
  assert.match(SRC, /const regionSt = c\.target \? regionState\(c\.target, this\.status\) : "current";/);
  assert.match(SRC, /if \(img\) \{ img\.scrollIntoView\(\{ block: "center" \}\); return; \}/);
  // layers leave with the viewer
  assert.match(SRC, /for \(const l of this\.regionLayers\.values\(\)\) l\.dispose\(\);/);
});

test("the sheets: the region rules sit inside the mirrored file-comments block, the chip is generated content, a coarse overlay takes no events", () => {
  for (const f of ["styles.css", "feed.css"]) {
    const css = web(f);
    const a = css.indexOf("/* ── file comments panel (plans/file-review.md Slice 1; file-comments.ts)");
    const b = css.indexOf("/* ── end file comments panel ── */");
    const block = css.slice(a, b);
    assert.match(block, /\n\.fc-imgwrap \{ position: relative; display: inline-block; max-width: 100%; \}\n\.fc-imgwrap > img \{ display: block; \}\n/, f + ": the wrapper hugs a block picture");
    assert.match(block, /\n\.fc-overlay \{ position: absolute; inset: 0; cursor: crosshair; touch-action: none; \}\n/, f);
    assert.match(block, /\n\.fc-overlay-off \{ pointer-events: none; cursor: default; \}\n\.fc-overlay-off \.fc-region \{ pointer-events: auto; \}\n/, f + ": a coarse pointer reads through the overlay, the rectangles still click");
    assert.match(block, /\n\.fc-region \{ position: absolute; box-sizing: border-box; border: 2px solid var\(--fc-author, var\(--warn\)\);/, f + ": the author's colour, the ring's colour as the fallback");
    assert.match(block, /\n\.fc-region\.fc-stale \{ border-style: dashed; \}\n\.fc-region\.fc-unknown \{ border-style: dotted; \}\n/, f);
    assert.match(block, /\n\.fc-region-chip::after \{ content: attr\(data-label\); \}\n/, f + ": the chip's label is generated, never a text node");
    assert.match(block, /\.fc-region-chip \{[^}]*font-size: 0\.72em;/, f + ": the chip size from the ladder");
  }
});

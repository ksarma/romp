// The SVG Source view keeps the reader's place as the Raw view does (plans/markdown-viewer.md Slice 2; file-view.ts
// renderBody; the Slice 2 review's third round): its paint reads the place, swaps, runs the seam's hooks, records the
// XML as the text the body was painted from and seats, in the order the Raw branch uses, and the media paint after it
// records no text, so a stale place is never read against a picture or a PDF frame. A source pin, so CI (which runs no
// browser legs) holds the order; file-view-place-svg-source-browser.test.ts measures the reload and the panel toggle in
// headless Chromium. Beside the pin, one EXECUTED node-only case over a DOM stand-in (the members an SVG open, the Source
// toggle and the group query touch, modelled on file-view-text-size.test.ts's; the stand-in hides its edges with the
// shared rule, ui/test-dom-shim.ts): the view group that holds the Source button is shown after an SVG's first paint and
// stays shown after Source on and after Source off. renderBody syncs the group before its media branch decides the Source
// button, so the group is re-read after that branch: the fork's fix (c260d885f, the 2026-09-15 upstream pull-in's fixer
// round 2), recorded in upstream/2026-09-16-svg-source-group-resync.md. Upstream's tip 14f1548a9 has the original order,
// the sync before the media branch and no re-read, so there the group stays hidden after an SVG's first paint and the
// Source button with it; the browser leg fails without the re-read, but CI runs npm test before any browser is installed,
// so this case is the pin where CI runs (the pull-in's review round 1). Synthetic fixtures only.
import { test, type TestContext } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { inspect } from "node:util";
import { assertHiddenEvent, hideEdges, staysEnumerable } from "../test-dom-shim";

const VIEW = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "file-view.ts"), "utf8");
const local = VIEW.split("export function openFileView(")[1].split("\nexport function ")[0];

test("file-view.ts: the SVG Source view's paint reads the place, swaps, runs the hooks, records the XML as shownText and seats; the media paint records no text; those are the only writers of shownText in the viewer, in that order", () => {
  assert.match(local,
    /if \(svgSource && svgText !== null\) \{\n(?:\s*\/\/[^\n]*\n)*\s*const kept = keptPlace\(\);\n\s*body\.replaceChildren\(codeBlock\(svgText, path, true\)\);[^\n]*\n\s*fireRendered\(\);[^\n]*\n\s*shownText = svgText;\n\s*seat\(kept\);\n\s*landRemembered\(\);[^\n]*\n\s*return;\n\s*\}\n\s*shownText = null;/,
    "the Source view: read, swap, hooks, record, seat; then, for a picture or a frame, no text");
  const writers = Array.from(local.matchAll(/\bshownText = ([^;]+);/g)).map((m) => m[0]);
  assert.deepEqual(writers, ["shownText = svgText;", "shownText = null;", "shownText = text;"], "the Source view's, the media paint's, the text views'");
});

// ── a DOM stand-in: the members the viewer touches in an SVG open, the Source toggle and the group query ────────────
class Ev {
  target: El | null = null;
  currentTarget: El | null = null;
  defaultPrevented = false;
  stopped = false;
  ctrlKey = false; metaKey = false; key = "";
  constructor(public type: string) { hideEdges(this); }   // target and currentTarget hide with the shared rule
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
class El {
  parentNode: El | null = null;
  childNodes: Array<El | string> = [];
  title = ""; hidden = false; type = ""; disabled = false; tabIndex = -1; innerHTML = "";
  href = ""; target = ""; rel = ""; spellcheck = true; value = ""; src = ""; alt = ""; download = "";
  style: Record<string, string> = {};
  onclick: ((ev: Ev) => void) | null = null;
  private attrs = new Map<string, string>();
  private listeners: Array<{ type: string; fn: Listener; once: boolean }> = [];
  constructor(public tagName: string) { hideEdges(this); }   // the edges (parentNode, childNodes, the listener table) hide with the shared rule
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
  get textContent(): string { return this.childNodes.map((c) => (typeof c === "string" ? c : c.textContent)).join(""); }
  set textContent(v: string) { this.replaceChildren(...(v === "" ? [] : [v])); }
  /** Element children only, in order. */
  get children(): El[] { return this.childNodes.filter((c): c is El => c instanceof El); }
  get isConnected(): boolean { let n: El = this; while (n.parentNode) n = n.parentNode; return n === docBody; }
  private adopt(c: El | string): void { if (c instanceof El) { c.remove(); c.parentNode = this; } }
  appendChild<T extends El>(c: T): T { this.adopt(c); this.childNodes.push(c); return c; }
  prepend(...cs: Array<El | string>): void { for (const c of cs) this.adopt(c); this.childNodes.unshift(...cs); }
  insertBefore<T extends El>(c: T, ref: El | null): T {
    if (ref && !this.childNodes.includes(ref)) throw new Error("insertBefore: the reference node is not a child of this node");
    this.adopt(c);
    const i = ref ? this.childNodes.indexOf(ref) : -1;
    if (i < 0) this.childNodes.push(c); else this.childNodes.splice(i, 0, c);
    return c;
  }
  replaceChildren(...cs: Array<El | string>): void {
    for (const c of this.childNodes) if (c instanceof El) c.parentNode = null;
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
    this.listeners.push({ type, fn, once: typeof opts === "object" && !!opts.once });
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
  scrollIntoView(): void { /* inert */ }
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
}
const docBody = new El("body");
const docKeys: Listener[] = [];                  // the viewer's document keydown handlers, one per open
const doc = {
  body: docBody,
  activeElement: null as El | null,
  createElement: (tag: string) => new El(tag),
  createTextNode: (s: string) => s,
  getElementById: (id: string): El | null => docBody.querySelector("#" + id),
  querySelectorAll: (sel: string): El[] => docBody.querySelectorAll(sel),   // no bundle <script src>: the editor chunk cannot load
  addEventListener: (type: string, fn: Listener) => { if (type === "keydown") docKeys.push(fn); },
  removeEventListener: (type: string, fn: Listener) => { const i = docKeys.indexOf(fn); if (i >= 0) docKeys.splice(i, 1); },
};
const win: any = new EventTarget();
win.parent = win;
win.confirm = () => true;                       // the discard ask, when a dirty buffer is about to go
win.getSelection = () => null;
win.postMessage = () => { /* the quote seed: nothing reads it here */ };
hideEdges(win);                                 // the stand-in's parent is itself: hidden with the rest
(globalThis as any).window = win;
(globalThis as any).document = doc;
const store = new Map<string, string>();
(globalThis as any).localStorage = {
  getItem: (k: string) => (store.has(k) ? store.get(k)! : null),
  setItem: (k: string, v: string) => { store.set(k, String(v)); },
  removeItem: (k: string) => { store.delete(k); },
};
// the body's width watcher (the reflow contract) and the frame the viewer folds its re-seats into: inert here, never run
(globalThis as any).ResizeObserver = class { observe(): void { /* inert */ } unobserve(): void { /* inert */ } disconnect(): void { /* inert */ } };
let frameSeq = 0;
const frames = new Map<number, () => void>();
(globalThis as any).requestAnimationFrame = (cb: () => void): number => { frames.set(++frameSeq, cb); return frameSeq; };
(globalThis as any).cancelAnimationFrame = (id: number): void => { frames.delete(id); };

// ── the fixture: one small diagram in the notes-api world, synthetic throughout ──────────────────────────────────────
const SID = "77777777-8888-9999-aaaa-bbbbbbbbbbbb";
const FIG = "/tmp/notes-api/docs/fig.svg";
const SVG_XML = '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10">\n  <rect width="10" height="10"/>\n</svg>\n';
const MT = "1700000000000000000";
// The fetches the viewer makes: the kernel's /file (Content-Type is its verdict: an SVG) and its /version (editing
// already allowed, so no consent popup).
(globalThis as any).fetch = (url: string) => {
  if (url.startsWith("/version")) return Promise.resolve({ json: () => Promise.resolve({ fileEditing: true }) });
  const p = decodeURIComponent((/[?&]path=([^&]*)/.exec(url) || [])[1] || "");
  const headers = { get: (h: string) => (p === FIG ? (h === "Content-Type" ? "image/svg+xml" : h === "X-Romp-Mtime-Ns" ? MT : h === "X-Romp-Text-Utf8" ? "1" : null) : null) };
  if (p !== FIG) return Promise.resolve({ ok: false, status: 404, headers, text: () => Promise.resolve("no such file: " + p) });
  return Promise.resolve({
    ok: true, status: 200, headers,
    text: () => Promise.resolve(SVG_XML),
    blob: () => Promise.resolve(new Blob([SVG_XML], { type: "image/svg+xml" })),
  });
};
/** Let every pending promise chain run: the fetch settles, the blob lands, a Source click's decode paints. */
const settle = async () => { for (let i = 0; i < 8; i++) await new Promise<void>((r) => setImmediate(r)); };

let bound: Promise<typeof import("./file-view")> | null = null;
function view(): Promise<typeof import("./file-view")> {
  if (!bound) bound = import("./file-view").then((fv) => { fv.initFileView(() => { /* the WS poster: nothing asks the kernel here */ }); return fv; });
  return bound;
}
type Card = { wrap: El; body: El; btn: (label: string) => El };
/** Open the diagram for the fixture session and let the bytes land: the card up now, its body and a finder for a bar button. */
async function openSvg(t: TestContext): Promise<Card> {
  const fv = await view();
  fv.openFileView(FIG, SID);
  t.after(() => { fv.closeFileView(); store.clear(); });
  await settle();
  const wrap = doc.getElementById("romp-fileview");
  assert.ok(wrap, "a viewer is up");
  const root = wrap!.children[0];
  assert.equal(root.className, "fileview");
  const bar = root.children[0];
  assert.equal(bar.className, "fileview-bar");
  const body = root.querySelector(".fileview-body");
  assert.ok(body, "the body");
  const acts = bar.children.find((c) => c.classList.contains("fileview-acts"));
  assert.ok(acts, "the actions row");
  const btn = (label: string) => { const walk = (n: El): El | undefined => { for (const c of n.children) { if (c.tagName === "button" && (c.textContent === label || c.getAttribute("aria-label") === label)) return c; const d = walk(c); if (d) return d; } return undefined; }; const b = walk(acts!); assert.ok(b, "the " + label + " button"); return b!; };   // T367: controls sit in groups, glyph buttons carry their word as aria-label
  return { wrap: wrap!, body: body!, btn };
}

test("executed, node-only: after an SVG's first paint the view group holding the Source button is shown, and it stays shown after Source on and after Source off (before the re-sync after renderBody's media branch, the first paint left the group hidden: its sync ran while the button was still hidden, and the button sat in a hidden group)", async (t) => {
  const o = await openSvg(t);
  assert.equal(o.body.children[0]?.className, "fileview-imgbox", "the first paint: the picture");
  const group = o.wrap.querySelector(".fileview-group-view");
  assert.ok(group, "the view group");
  assert.equal(group!.hidden, false, "after the first paint the group is shown: over a picture the Source button is its one control, decided by the media branch after the group's first sync, so the group is re-read after it");
  o.btn("Source").click();
  await settle();
  assert.equal(o.body.children[0]?.className, "fileview-code", "Source on: the XML rows");
  assert.equal(group!.hidden, false, "Source on: the group stays shown (a text view: the size glyph shows too)");
  o.btn("Source").click();
  await settle();
  assert.equal(o.body.children[0]?.className, "fileview-imgbox", "Source off: the picture again");
  assert.equal(group!.hidden, false, "Source off: the group stays shown (the Source button is still its one control)");
});

test("a stand-in node enumerates its primitives alone, so a failing assertion's dump shows neither parentNode nor childNodes", () => {
  const root = new El("div"); root.className = "row";
  const child = root.appendChild(new El("span")); child.textContent = "alpha"; const tail = root.appendChild(new El("span")); tail.textContent = "beta";
  for (const n of [root, child, tail]) {
    for (const k of Object.keys(n)) assert.ok(staysEnumerable((n as any)[k]), k + " is enumerable and holds a " + typeof (n as any)[k]);
    const dump = inspect(n, { compact: false, customInspect: false, depth: 1000, maxArrayLength: Infinity, showHidden: false, showProxy: false, sorted: true, getters: true });
    assert.ok(!dump.includes("parentNode") && !dump.includes("childNodes"), "the dump holds no edge: " + dump);
  }
  assert.ok(child.parentNode === root && root.childNodes[0] === child && root.textContent === "alphabeta", "the tree is reachable as before");
  // the file's own Ev hides target and currentTarget the same way (hideEdges(this) at the end of its constructor)
  assertHiddenEvent(new Ev("click"), root, child);
});

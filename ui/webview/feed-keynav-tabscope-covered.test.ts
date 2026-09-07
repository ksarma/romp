// The card keyboard scope yields while the board is covered (review 2026-09-07, round 3). Round 2 made the card
// cursor's handler stand down while the file viewer or the file browser is up (boardCovered), but its sibling — the
// Tab scope's window CAPTURE handler, which cycles a card's controls on Tab and falls back to the cursor's card
// (kbCardEl) — did not, and the cursor stays armed through the click that opens the viewer. So with the viewer up:
// a Tab from the composer's Save button (the box's own Tab lands there, and a button passes the scope's typing
// yield) was cancelled and focused a control of a card behind the viewer, with the accent ring on it; the next Enter
// clicked that control (the card's title: its timeline journey; one Tab on, its Clear button); and a scope armed
// before the viewer opened swallowed the Escape meant to close it — the handler runs ahead of the viewer's own
// Escape on `document`, so a cancel there never reached it. The same hole with #romp-filebrowse up. RUN, not pinned
// at the source: the real feed.ts boots under the DOM stand-in feed-keynav-covered.test.ts uses (copied here, with
// focus modelled and the window delivering a keydown capture-first, as a browser does), three synthetic cards
// render, the cursor is armed the way the shell arms it, and Tab, Shift+Tab, Enter and Escape are pressed with the
// viewer or the browser up. Synthetic only: the notes-api demo world, placeholder sids, hostname TESTHOST.
import { test, mock, after } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const FEED_SRC = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "feed.ts"), "utf8");

// ── a DOM stand-in ─────────────────────────────────────────────────────────────────────────────────
// feed-keynav-covered.test.ts's stand-in, with two things a browser does that these tests read: focus() and blur()
// move document.activeElement (the earlier copies leave them no-ops), and the window delivers a keydown the way a
// browser does — its CAPTURE listeners first, then, unless one of them stopped propagation, its bubble listeners
// (Node's EventTarget runs listeners in registration order, which puts the card cursor's bubble handler AHEAD of the
// Tab scope's capture handler and lets both act on one Escape; a browser runs the scope first and the cursor never
// sees a key the scope stopped).
class Style {
  [key: string]: any;
  private props = new Map<string, string>();
  setProperty(k: string, v: string): void { this.props.set(k, v); }
  removeProperty(k: string): void { this.props.delete(k); }
  getPropertyValue(k: string): string { return this.props.get(k) ?? ""; }
}
class Txt {
  nodeType = 3;
  parentNode: El | null = null;
  constructor(public textContent: string) {}
  get nextSibling(): El | Txt | null { return sib(this, 1); }
  remove(): void { this.parentNode?.removeChild(this); }
}
function sib(n: El | Txt, d: number): El | Txt | null {
  const p = n.parentNode; if (!p) return null;
  const i = p.childNodes.indexOf(n); return p.childNodes[i + d] ?? null;
}
const camel = (s: string) => s.replace(/-([a-z])/g, (_, c) => c.toUpperCase());
type Compound = { tag: string | null; id: string | null; classes: string[]; attrs: { name: string; value: string | null }[]; nots: Compound[]; pseudo: boolean };
function parseCompound(s: string): Compound {
  const c: Compound = { tag: null, id: null, classes: [], attrs: [], nots: [], pseudo: false };
  const m = /^([a-zA-Z][\w-]*)?(.*)$/.exec(s)!;
  c.tag = m[1] ? m[1].toUpperCase() : null;
  // :not(<compound>) is the one pseudo-class that resolves (kbCardEls reads ".fitem:not(.dismissing)"); every other
  // pseudo-class, :hover included, matches nothing
  const re = /\.([\w-]+)|#([\w-]+)|\[([\w-]+)(?:="([^"]*)")?\]|:not\(([^)]*)\)|:[\w-]+(?:\([^)]*\))?/g;
  let t: RegExpExecArray | null;
  while ((t = re.exec(m[2]))) {
    if (t[1]) c.classes.push(t[1]);
    else if (t[2]) c.id = t[2];
    else if (t[3]) c.attrs.push({ name: t[3], value: t[4] ?? null });
    else if (t[5] !== undefined) c.nots.push(parseCompound(t[5].trim()));
    else c.pseudo = true;
  }
  return c;
}
const clickEv = { stopPropagation() {}, preventDefault() {} };
class El extends EventTarget {
  nodeType = 1;
  id = ""; title = ""; hidden = false; value = ""; type = ""; checked = false; disabled = false;
  offsetWidth = 0; offsetHeight = 0; clientWidth = 800; clientHeight = 600; isContentEditable = false;
  scrollTop = 0;
  clicks = 0;                               // activations through click() — what the card cursor's Enter fires
  onclick: ((ev: any) => void) | null = null;
  parentNode: El | null = null;
  childNodes: Array<El | Txt> = [];
  dataset: Record<string, string | undefined> = {};
  style = new Style();
  private attrs = new Map<string, string>();
  private classes = new Set<string>();
  private _html = "";
  classList = {
    add: (...c: string[]) => { for (const x of c) this.classes.add(x); },
    remove: (...c: string[]) => { for (const x of c) this.classes.delete(x); },
    toggle: (c: string, force?: boolean) => {
      const on = force === undefined ? !this.classes.has(c) : force;
      if (on) this.classes.add(c); else this.classes.delete(c);
      return on;
    },
    contains: (c: string) => this.classes.has(c),
  };
  constructor(public tagName: string) { super(); this.tagName = tagName.toUpperCase(); }
  get className(): string { return [...this.classes].join(" "); }
  set className(v: string) { this.classes = new Set(v.split(/\s+/).filter(Boolean)); }
  get textContent(): string { return this.childNodes.map((c) => c.textContent).join(""); }
  set textContent(v: string | null) { this.detachAll(); if (v !== null && v !== "") this.appendChild(new Txt(String(v))); }
  get innerHTML(): string { return this._html; }
  set innerHTML(v: string) { this.detachAll(); this._html = v; }
  get children(): El[] { return this.childNodes.filter((c): c is El => c instanceof El); }
  get firstChild(): El | Txt | null { return this.childNodes[0] ?? null; }
  get nextSibling(): El | Txt | null { return sib(this, 1); }
  get parentElement(): El | null { return this.parentNode; }
  get previousElementSibling(): El | null { for (let n = sib(this, -1); n; n = sib(n, -1)) if (n instanceof El) return n; return null; }
  get nextElementSibling(): El | null { for (let n = sib(this, 1); n; n = sib(n, 1)) if (n instanceof El) return n; return null; }
  get isConnected(): boolean { return this === body || body.contains(this); }
  private detachAll(): void { for (const c of this.childNodes) c.parentNode = null; this.childNodes = []; }
  private adopt(c: El | Txt | string): El | Txt { const n = typeof c === "string" ? new Txt(c) : c; n.parentNode?.removeChild(n); n.parentNode = this; return n; }
  appendChild<T extends El | Txt>(c: T): T { this.childNodes.push(this.adopt(c) as T); return c; }
  append(...cs: Array<El | Txt | string>): void { for (const c of cs) this.childNodes.push(this.adopt(c)); }
  prepend(...cs: Array<El | Txt | string>): void { this.childNodes.unshift(...cs.map((c) => this.adopt(c))); }
  replaceChildren(...cs: Array<El | Txt | string>): void { this.detachAll(); this.append(...cs); }
  insertBefore<T extends El | Txt>(node: T, ref: El | Txt | null): T {
    const n = this.adopt(node);
    const i = ref ? this.childNodes.indexOf(ref) : -1;
    if (i < 0) this.childNodes.push(n); else this.childNodes.splice(i, 0, n);
    return node;
  }
  removeChild(c: El | Txt): void { const i = this.childNodes.indexOf(c); if (i >= 0) { this.childNodes.splice(i, 1); c.parentNode = null; } }
  remove(): void { this.parentNode?.removeChild(this); }
  after(...cs: Array<El | Txt | string>): void { const p = this.parentNode; if (!p) return; const ref = sib(this, 1); for (const c of cs) p.insertBefore(typeof c === "string" ? new Txt(c) : c, ref); }
  before(...cs: Array<El | Txt | string>): void { const p = this.parentNode; if (!p) return; for (const c of cs) p.insertBefore(typeof c === "string" ? new Txt(c) : c, this); }
  replaceWith(c: El | Txt): void { const p = this.parentNode; if (!p) return; p.insertBefore(c, this); this.remove(); }
  get firstElementChild(): El | null { return this.children[0] ?? null; }
  get lastElementChild(): El | null { const c = this.children; return c[c.length - 1] ?? null; }
  get lastChild(): El | Txt | null { return this.childNodes[this.childNodes.length - 1] ?? null; }
  get childElementCount(): number { return this.children.length; }
  contains(x: El | Txt | null): boolean { for (let n: El | Txt | null = x; n; n = n.parentNode) if (n === this) return true; return false; }
  setAttribute(k: string, v: string): void { this.attrs.set(k, String(v)); if (k.startsWith("data-")) this.dataset[camel(k.slice(5))] = String(v); if (k === "id") this.id = v; }
  getAttribute(k: string): string | null { return this.attrs.get(k) ?? (k.startsWith("data-") ? this.dataset[camel(k.slice(5))] ?? null : k === "title" && this.title ? this.title : null); }
  hasAttribute(k: string): boolean { return this.getAttribute(k) !== null; }
  removeAttribute(k: string): void { this.attrs.delete(k); if (k === "title") this.title = ""; }
  getBoundingClientRect() {
    for (let n: El | null = this; n; n = n.parentNode) if (n.style.display === "none") return { left: 0, top: 0, right: 0, bottom: 0, width: 0, height: 0 };
    if (!this.isConnected) return { left: 0, top: 0, right: 0, bottom: 0, width: 0, height: 0 };
    const p = this.parentNode!;
    const top = p.children.indexOf(this) * 100, left = p.id.length * 10;
    return { left, top, right: left + 300, bottom: top + 90, width: 300, height: 90 };
  }
  scrollIntoView(): void {}
  focus(): void { doc.activeElement = this; }                                   // what a browser does: focus moves here
  blur(): void { if (doc.activeElement === this) doc.activeElement = body; }   // …and falls to the body on blur
  click(): void { this.clicks++; this.onclick?.(clickEv); this.dispatchEvent(new MouseEvent("click")); }   // HTMLElement.click(): the handler runs
  matchesCompound(c: Compound): boolean {
    if (c.pseudo) return false;
    if (c.tag && c.tag !== this.tagName) return false;
    if (c.id && c.id !== this.id) return false;
    for (const k of c.classes) if (!this.classes.has(k)) return false;
    for (const a of c.attrs) { const v = this.getAttribute(a.name); if (v === null) return false; if (a.value !== null && v !== a.value) return false; }
    for (const n of c.nots) if (this.matchesCompound(n)) return false;
    return true;
  }
  matches(sel: string): boolean {
    return sel.split(",").some((one) => {
      const parts = one.trim().split(/\s+/).map(parseCompound);
      if (!this.matchesCompound(parts[parts.length - 1])) return false;
      let anc: El | null = this.parentNode;
      for (let i = parts.length - 2; i >= 0; i--) {
        while (anc && !anc.matchesCompound(parts[i])) anc = anc.parentNode;
        if (!anc) return false;
        anc = anc.parentNode;
      }
      return true;
    });
  }
  closest(sel: string): El | null { for (let n: El | null = this; n; n = n.parentNode) if (n.matches(sel)) return n; return null; }
  querySelectorAll(sel: string): El[] { return [...this.walk()].filter((e) => e.matches(sel)); }
  querySelector(sel: string): El | null { for (const e of this.walk()) if (e.matches(sel)) return e; return null; }
  *walk(): Generator<El> { for (const c of this.childNodes) if (c instanceof El) { yield c; yield* c.walk(); } }
  byId(id: string): El | null { for (const e of this.walk()) if (e.id === id) return e; return null; }
}
/** The window, delivering a keydown in a browser's order: capture listeners, then bubble listeners unless propagation
 *  was stopped in between (the same-target rule lets every capture listener run even after one stops it). */
class Win extends EventTarget {
  private keyL: { fn: (e: Event) => void; cap: boolean }[] = [];
  addEventListener(type: string, fn: any, opts?: any): void {
    if (type === "keydown") { this.keyL.push({ fn, cap: opts === true || !!(opts && opts.capture) }); return; }
    super.addEventListener(type, fn, opts);
  }
  removeEventListener(type: string, fn: any, opts?: any): void {
    if (type === "keydown") { const cap = opts === true || !!(opts && opts.capture); this.keyL = this.keyL.filter((l) => !(l.fn === fn && l.cap === cap)); return; }
    super.removeEventListener(type, fn, opts);
  }
  dispatchEvent(e: Event): boolean {
    if (e.type !== "keydown") return super.dispatchEvent(e);
    for (const l of this.keyL) if (l.cap) l.fn(e);
    if (!e.cancelBubble) for (const l of this.keyL) if (!l.cap) l.fn(e);   // cancelBubble: the stop-propagation flag
    return !e.defaultPrevented;
  }
}
const posted: any[] = [];
const body = new El("body");
const head = new El("div"); head.id = "feed-head";
const list = new El("div"); list.id = "feed-list";
const foot = new El("div"); foot.id = "feed-foot";
const gearGuard = new El("div"); gearGuard.id = "rsettings";   // initGear's idempotence check: present → the modal never mounts
body.append(head, list, foot, gearGuard);
const stores = { local: new Map<string, string>(), session: new Map<string, string>() };
const storage = (m: Map<string, string>) => ({
  getItem: (k: string) => (m.has(k) ? m.get(k)! : null),
  setItem: (k: string, v: string) => { m.set(k, String(v)); },
  removeItem: (k: string) => { m.delete(k); },
});
const win: any = new Win();
win.parent = win; win.top = win;
win.location = { hash: "", search: "", protocol: "http:" };
win.innerWidth = 1200; win.innerHeight = 800;
win.setTimeout = (...a: Parameters<typeof setTimeout>) => setTimeout(...a);
win.clearTimeout = (t: ReturnType<typeof setTimeout>) => clearTimeout(t);
win.setInterval = (...a: Parameters<typeof setInterval>) => setInterval(...a);
win.requestAnimationFrame = (cb: () => void) => setTimeout(cb, 0);
win.matchMedia = () => ({ matches: false, addEventListener() {}, addListener() {} });
win.getComputedStyle = () => ({ flexDirection: "row", order: "0" });
win.postMessage = () => {};
win.acquireVsCodeApi = () => ({ postMessage: (m: any) => posted.push(m) });
(globalThis as any).window = win;
(globalThis as any).requestAnimationFrame = win.requestAnimationFrame;
(globalThis as any).getComputedStyle = win.getComputedStyle;
(globalThis as any).MouseEvent = class MouseEvent extends Event { clientX = 0; clientY = 0; };
const doc: any = new EventTarget();
Object.assign(doc, {
  body, head: new El("head"), documentElement: new El("html"), hidden: false, activeElement: body,
  createElement: (tag: string) => new El(tag),
  createTextNode: (s: string) => new Txt(s),
  getElementById: (id: string) => body.byId(id),
  querySelectorAll: (sel: string) => body.querySelectorAll(sel),
  querySelector: (sel: string) => body.querySelector(sel),
  contains: (x: El) => body.contains(x),
});
(globalThis as any).document = doc;
(globalThis as any).localStorage = storage(stores.local);
(globalThis as any).sessionStorage = storage(stores.session);

// ── the world: three sessions of a notes-api project, three cards ─────────────────────────────────
const T0 = 1781100000;
const K0 = T0 - 300;
const WEB = "11111111-2222-3333-4444-555555555555", API = "11111111-2222-3333-4444-666666666666", TESTS = "11111111-2222-3333-4444-777777777777";
const node = (id: string, text: string, who: string, whoSid: string) =>
  ({ id, kind: "ask", text, who, whoSid, whoColor: null, status: "open", t: K0 - 240, last: K0 - 240, children: [] as string[] });
const cardOf = (itemId: string, sid: string, name: string, bg: string, text: string) => ({
  itemId, sid, name, color: { bg, fg: "#ffffff" }, text, t: K0 - 240, live: true, turnId: "turn-" + itemId, column: "working",
  summary: null, blockSummary: null, tree: [node(itemId, text, name, sid)],
});
const g1 = cardOf("g1", WEB, "web", "#3366cc", "Wire the notes-api health route");
const g2 = cardOf("g2", API, "api", "#cc6633", "Write the notes-api README");
const g3 = cardOf("g3", TESTS, "tests", "#33cc66", "Run the notes-api test suite");
const frame = (asks: any[]) => ({
  type: "feed", now: K0, nowAt: T0 * 1000, buildId: 1, asks,
  working: [], awaiting: [], stateUnknown: [], order: [WEB, API, TESTS], selfHost: "TESTHOST",
  sessions: [{ sid: WEB, name: "web", color: g1.color }, { sid: API, name: "api", color: g2.color }, { sid: TESTS, name: "tests", color: g3.color }],
  userTodos: {}, bgServices: {},
});
const listenerErrors: Error[] = [];
process.on("uncaughtException", (e) => { listenerErrors.push(e); });
const settle = async () => {
  await new Promise<void>((r) => setImmediate(r));   // let a deferred listener exception land before the assertions
  if (listenerErrors.length) { const es = listenerErrors.splice(0); throw new Error("a listener threw: " + es.map((e) => e.stack || e.message).join("\n---\n")); }
};
const dispatch = async (f: any) => { win.dispatchEvent(new MessageEvent("message", { data: f })); await settle(); };
/** One key at the window, the way a browser delivers a keydown that bubbled up from the focused element. */
const press = async (key: string, shift = false): Promise<Event> => {
  const e = Object.assign(new Event("keydown", { cancelable: true }), { key, altKey: false, ctrlKey: false, metaKey: false, shiftKey: shift });
  win.dispatchEvent(e);
  await settle();
  return e;
};
after(() => { assert.deepEqual(listenerErrors.map((e) => e.stack || e.message), [], "no listener threw outside a dispatch"); });
const card = (id: string): El => { const c = body.querySelector(`[data-key="a:${id}"]`); assert.ok(c, "card " + id); return c!; };
const title = (id: string): El => { const t = card(id).querySelector(".fcard-title.nav"); assert.ok(t, "title of " + id); return t!; };
const rings = () => body.querySelectorAll(".kbd-focus").length;
const ringed = (): El | null => body.querySelector(".kbd-focus");
const onTimeline = () => posted.filter((m) => m.type === "showOnTimeline").length;
const active = (): El => doc.activeElement as El;
/** A short name for an element in a failure message — never the element itself: the runner inspects a failed equal's
 *  operands, and a stand-in node reaches the whole document through parentNode, so an El-to-El equal that failed read
 *  as a hang (minutes of serialisation) instead of a red test. Identity is asserted as a boolean, the names carry
 *  the detail. */
const desc = (el: El | null): string => el
  ? (el.closest("[data-key]")?.dataset.key ?? "-") + "/" + el.tagName + (el.className ? "." + el.className.split(" ").join(".") : "") + (el.id ? "#" + el.id : "") + (el.dataset.act ? "[" + el.dataset.act + "]" : "")
  : "null";
const same = (got: El | null, want: El | null, msg: string): void => { assert.ok(got === want, msg + " (got " + desc(got) + ", want " + desc(want) + ")"); };
/** The viewer's composer row, the way file-comments.ts builds it: a real <button> per action under #romp-fileview. */
function mountViewer(): { view: El; box: El; save: El; cancel: El } {
  const view = new El("div"); view.id = "romp-fileview";
  const box = new El("textarea"); box.className = "fc-input";
  const save = new El("button"); save.className = "fileview-btn"; save.setAttribute("data-act", "fcsave");
  const cancel = new El("button"); cancel.className = "fileview-btn"; cancel.setAttribute("data-act", "fccancel");
  view.append(box, save, cancel); body.appendChild(view);
  return { view, box, save, cancel };
}

test("boot: three cards render, and the shell's paneFocus arms the card cursor on the first", async () => {
  mock.timers.enable({ apis: ["Date", "setTimeout", "setInterval"], now: T0 * 1000 });
  await import("./feed");
  await dispatch(frame([g1, g2, g3]));
  assert.equal(body.querySelectorAll(".feed-cols .fitem:not(.dismissing)").length, 3, "the stand-in resolves kbCardEls' selector");
  await dispatch({ romp: "paneFocus" });                          // what the shell posts on Alt+Arrow into the feed
  assert.ok(card("g1").classList.contains("focused"), "the cursor's ring is on the first card");
  assert.equal(rings(), 0, "…and no element inside it is ringed yet");
  same(active(), body, "nothing is focused: the cursor's ring is not focus");
});

test("board uncovered: Tab is the scope's — it rings and focuses the cursor's card's first control, and Escape releases it with the cursor still armed", async () => {
  const tab = await press("Tab");
  assert.equal(tab.defaultPrevented, true, "the scope took the key");
  same(ringed(), title("g1"), "the first control of the cursor's card is ringed");
  same(active(), title("g1"), "…and focused");
  const esc = await press("Escape");
  assert.equal(esc.defaultPrevented, true, "the scope's release");
  assert.equal(rings(), 0);
  same(active(), body, "the release blurred the control");
  assert.ok(card("g1").classList.contains("focused"), "the scope's Escape is not the cursor's: it stays armed (capture-first, the scope stopped the key)");
});

test("viewer up, focus on the composer's Save button: Tab and Shift+Tab are the page's own — not cancelled, focus untouched, no ring in a card — and Enter is the button's native click", async () => {
  const { view, save, cancel } = mountViewer();
  for (const b of [save, cancel]) {
    doc.activeElement = b;                                          // the box's own Tab landed here
    for (const shift of [false, true]) {
      const tab = await press("Tab", shift);
      assert.equal(tab.defaultPrevented, false, (shift ? "Shift+Tab" : "Tab") + " from " + b.dataset.act + " is not the scope's");
      assert.equal(rings(), 0, "no control behind the viewer was ringed");
      same(active(), b, "focus stays where the browser has it: the page's own order moves it, not the scope");
    }
    const enter = await press("Enter");
    assert.equal(enter.defaultPrevented, false, "Enter is " + b.dataset.act + "'s native click");
    assert.equal(title("g1").clicks, 0, "nothing behind the viewer was clicked");
  }
  assert.equal(onTimeline(), 0, "…and nothing was posted for a card the person cannot see");
  doc.activeElement = body;
  view.remove();
});

test("viewer up, focus on the body (what Save leaves): Tab is not the scope's, and Enter clicks nothing behind the viewer", async () => {
  const { view } = mountViewer();
  doc.activeElement = body;
  const tab = await press("Tab");
  assert.equal(tab.defaultPrevented, false);
  assert.equal(rings(), 0, "no card control was ringed");
  same(active(), body, "…or focused");
  const enter = await press("Enter");
  assert.equal(enter.defaultPrevented, false);
  assert.equal(title("g1").clicks, 0);
  assert.equal(card("g1").querySelector(".fdismiss")!.clicks, 0, "the card's Clear was not reached either");
  assert.equal(onTimeline(), 0);
  view.remove();
});

test("a scope armed before the viewer opened: Enter and Escape are not its while the viewer is up (Escape reaches the viewer's own handler), and the next Escape once the viewer is gone releases it", async () => {
  const tab = await press("Tab");                                   // uncovered: the scope arms on the cursor's card
  assert.equal(tab.defaultPrevented, true);
  same(active(), title("g1"), "focus");
  const { view } = mountViewer();                                   // the card menu's Browse files → a file, with the scope's control still focused
  const enter = await press("Enter");
  assert.equal(enter.defaultPrevented, false, "the scope did not click its control behind the viewer");
  assert.equal(title("g1").clicks, 0);
  const esc = await press("Escape");
  assert.equal(esc.defaultPrevented, false, "not the scope's release: the viewer's Escape handler on `document` gets the key");
  same(ringed(), title("g1"), "the scope is still armed, untouched");
  view.remove();                                                    // file-view.ts's onKey closed the viewer on that Escape
  const esc2 = await press("Escape");
  assert.equal(esc2.defaultPrevented, true, "with the board back, Escape is the scope's release");
  assert.equal(rings(), 0);
  same(active(), body, "focus");
  assert.ok(card("g1").classList.contains("focused"), "the cursor is still armed on the board");
});

test("the file browser up (the sibling overlay): the same yield", async () => {
  const fb = new El("div"); fb.id = "romp-filebrowse"; body.appendChild(fb);
  doc.activeElement = body;
  const tab = await press("Tab");
  assert.equal(tab.defaultPrevented, false, "Tab is not the scope's under the browser");
  assert.equal(rings(), 0);
  same(active(), body, "focus");
  fb.remove();
  const again = await press("Tab");
  assert.equal(again.defaultPrevented, true, "…and is again once the browser is gone");
  same(ringed(), title("g1"), "ring");
  await press("Escape");
  assert.equal(rings(), 0);
  mock.timers.reset();
});

test("source: the scope's handler yields on the same boardCovered() the cursor's does, ahead of its Escape, Tab and Enter branches", () => {
  const kd = FEED_SRC.slice(FEED_SRC.indexOf("// ── CARD KEYBOARD SCOPE"), FEED_SRC.indexOf("// The feed payload's full application"));
  const modal = kd.indexOf('if (document.getElementById("feed-modal")) return;');
  const covered = kd.indexOf("if (boardCovered()) return;");
  const esc = kd.indexOf('if (e.key === "Escape" && tabScopeKey) {');
  const tab = kd.indexOf('if (e.key === "Tab") {');
  assert.ok(modal >= 0 && covered > modal && esc > covered && tab > esc, "modal yield, then the covered yield, then the key branches");
  assert.equal((kd.match(/if \(boardCovered\(\)\) return;/g) || []).length, 1, "one yield covers every branch");
  assert.match(FEED_SRC, /function boardCovered\(\): boolean \{\n\s*return !!\(document\.getElementById\("romp-fileview"\) \|\| document\.getElementById\("romp-filebrowse"\)\);\n\}/, "the two full-pane ids the cursor's yield reads");
});

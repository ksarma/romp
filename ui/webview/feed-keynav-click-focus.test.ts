// A click's leftover focus never takes the card cursor's Enter (review 2026-09-07, round 3). Round 2 made the cursor
// yield Enter to a focused button or link, so a Tab from the comment box to Save and Enter saves. A mouse click also
// leaves the clicked control focused, and the focus policy keeps focus in the feed while the cursor is armed, so with
// the board uncovered the yield handed Enter to whatever the mouse last pressed: Summary clicked on card A, an arrow
// to card B, Enter — A's Summary toggled off (with no ring to show why: .fask-secbtn has no focus rule, and a browser
// rings keyboard focus only) and the cursor descended nowhere. The keyboard has ONE path to a focused control while
// the cursor is armed — the Tab scope, which takes every Tab — so any other focused button or link is a click's
// leftover: Enter drops one inside a card before the yield reads the focus, an arrow that moves the cursor drops one
// anywhere, and the scope's own control keeps its focus (kbDropClickFocus). RUN, not pinned at the source: the real
// feed.ts boots under the DOM stand-in feed-keynav-covered.test.ts uses (copied here, with focus modelled and the
// window delivering a keydown capture-first, as a browser does), three synthetic cards render, the cursor is armed
// the way the shell arms it, and a control is clicked and focused the way a mouse press leaves it. Synthetic only:
// the notes-api demo world, placeholder sids, hostname TESTHOST.
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

/** A mouse press on a control: the click runs, and the control is left focused (what a browser does on mousedown). */
const mouseClick = (el: El): void => { el.click(); doc.activeElement = el; };
const pill = (id: string): El => { const p = card(id).querySelector("button.fask-secbtn"); assert.ok(p, "a section pill on " + id); return p!; };

test("a pill the mouse pressed on the cursor's card: Enter is the cursor's — the leftover focus drops, the cursor descends, the pill does not re-toggle", async () => {
  const p = pill("g1");
  mouseClick(p);
  assert.equal(p.clicks, 1);
  same(active(), p, "the press left the pill focused");
  const enter = await press("Enter");
  assert.equal(enter.defaultPrevented, true, "the cursor took the key (a cancelled Enter fires no native click)");
  same(active(), body, "the leftover focus was dropped");
  same(ringed(), title("g1"), "the cursor descended into its card");
  assert.equal(p.clicks, 1, "the pill did not re-toggle");
  await press("Escape");                                            // card → cards
  assert.equal(rings(), 0);
});

test("…and after an arrow to another card: the arrow drops the leftover, Enter descends into the cursor's card", async () => {
  const p = pill("g1");
  mouseClick(p);
  const down = await press("ArrowDown");
  assert.equal(down.defaultPrevented, true, "the arrow is the cursor's");
  assert.ok(card("g2").classList.contains("focused") && !card("g1").classList.contains("focused"), "the cursor moved to the second card");
  same(active(), body, "the move dropped the leftover focus");
  const enter = await press("Enter");
  assert.equal(enter.defaultPrevented, true);
  same(ringed(), title("g2"), "Enter descended into the cursor's card, not the pill's");
  assert.equal(p.clicks, 2, "the pill was clicked once by the mouse and never again");
  await press("Escape");                                            // card → cards
  await press("ArrowUp");
  assert.ok(card("g1").classList.contains("focused"));
});

test("a header button the mouse pressed: Enter stays its native click (the round-2 call), an arrow drops the leftover, and Enter is then the cursor's", async () => {
  const headBtn = new El("button"); headBtn.className = "fhead-btn"; body.byId("feed-head")!.appendChild(headBtn);
  mouseClick(headBtn);
  const enter = await press("Enter");
  assert.equal(enter.defaultPrevented, false, "outside a card, Enter is the focused button's native click");
  same(active(), headBtn, "…and its focus stands");
  assert.equal(rings(), 0);
  const down = await press("ArrowDown");
  assert.equal(down.defaultPrevented, true);
  assert.ok(card("g2").classList.contains("focused"));
  same(active(), body, "the move dropped the leftover focus");
  const again = await press("Enter");
  assert.equal(again.defaultPrevented, true, "now the cursor's");
  same(ringed(), title("g2"), "ring");
  assert.equal(headBtn.clicks, 1, "the header button fired once, by the mouse");
  await press("Escape");
  await press("ArrowUp");
  headBtn.remove();
});

test("the Tab scope's control keeps its focus: an arrow moves the cursor, and Enter stays the control's native activation", async () => {
  // Tab until the scope's stop is a control Enter activates natively (a pill, Clear, the session link — the card's own
  // order decides which comes first); the scope cycles g1's controls, never leaving the card
  let link: El = active();
  for (let n = 0; n < 12 && !(link.matches("button, a") && card("g1").contains(link)); n++) {
    const tab = await press("Tab");
    assert.equal(tab.defaultPrevented, true, "uncovered, Tab is the scope's");
    link = active();
  }
  assert.ok(link.matches("button, a") && card("g1").contains(link), "the scope holds a button or link of the cursor's card");
  same(ringed(), link, "ring");
  const down = await press("ArrowDown");
  assert.equal(down.defaultPrevented, true, "the arrow is still the cursor's");
  assert.ok(card("g2").classList.contains("focused"));
  same(active(), link, "the scope's control was not dropped: the scope is a keyboard state with its own release");
  const enter = await press("Enter");
  assert.equal(enter.defaultPrevented, false, "Enter is the link's native activation, as the scope's own yield says");
  assert.equal(rings(), 1, "the scope's ring stands; the cursor descended nowhere");
  same(ringed(), link, "ring");
  const esc = await press("Escape");
  assert.equal(esc.defaultPrevented, true, "the scope's release");
  assert.equal(rings(), 0);
  same(active(), body, "focus");
  assert.ok(card("g2").classList.contains("focused"), "the cursor is still armed");
  await press("ArrowUp");
  assert.ok(card("g1").classList.contains("focused"));
});

test("the viewer up: a focused Save is a viewer button, and the cursor's yields stand down before any focus is read", async () => {
  const { view, save } = mountViewer();
  doc.activeElement = save;
  const enter = await press("Enter");
  assert.equal(enter.defaultPrevented, false);
  same(active(), save, "the covered-board yield comes first: Save keeps its focus for its native click");
  assert.equal(rings(), 0);
  doc.activeElement = body;
  view.remove();
  mock.timers.reset();
});

test("source: kbDropClickFocus spares the scope's control, drops in-card leftovers before the Enter yield reads the focus, and drops any leftover on a cursor move", () => {
  const helper = FEED_SRC.slice(FEED_SRC.indexOf("function kbDropClickFocus(inCardOnly: boolean): void {"), FEED_SRC.indexOf("function kbExit(): void"));
  assert.ok(helper.length > 0, "the helper stands ahead of kbExit — outside the cursor handler's pinned slice");
  assert.match(helper, /if \(!ae \|\| !activatesOnEnter\(ae\)\) return;/, "only a button or link is a leftover");
  assert.match(helper, /if \(tabScopeKey && cardElByKey\(tabScopeKey\)\?\.contains\(ae\)\) return;/, "the scope's control is spared");
  assert.match(helper, /if \(inCardOnly && !ae\.closest\("\.fitem"\)\) return;/, "Enter's drop is in-card only");
  assert.match(helper, /ae\.blur\(\);/);
  const kb = FEED_SRC.slice(FEED_SRC.indexOf("function kbExit(): void"), FEED_SRC.indexOf('window.addEventListener("blur", () => { if (kbMode) kbExit(); });'));
  const drop = kb.indexOf('if (e.key === "Enter") kbDropClickFocus(true);');
  const yieldAt = kb.indexOf('if (e.key === "Enter" && activatesOnEnter(document.activeElement)) return;');
  const move = kb.indexOf("if (fwd || back) kbDropClickFocus(false);");
  const keyRead = kb.indexOf("const k = e.key");
  assert.ok(drop >= 0 && yieldAt > drop, "the in-card drop runs right before the yield reads the focus");
  assert.ok(keyRead > yieldAt && move > keyRead, "the move's drop runs once the key is known to be an arrow, before either mode acts on it");
});

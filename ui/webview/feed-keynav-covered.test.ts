// The card cursor yields while the board is covered, and to a focused button (review 2026-09-07, round 2). Round 1
// made the shell-armed cursor (paneFocus; nothing but Escape or a window blur disarms it) yield to a focused text
// field — the comment box under the file viewer, which mounts in the feed document. Three holes remained, all on
// the same handler: (1) the viewer up with focus on the BODY — what Save leaves, since hiding the box drops the
// browser's focus to the body — let Enter descend into a card the person could not see and the next Enter click a
// control behind the viewer; (2) a Tab from the box to the Save (or Cancel) button and Enter: the cursor cancelled
// the keydown, and a cancelled Enter never fires a button's native click, so nothing saved and the cursor descended
// instead — the plan's "or the Save button saves", broken for the keyboard; (3) a key a nearer handler had already
// taken — the viewer's Escape, the browser's arrows — was acted on a second time by the cursor. RUN, not pinned at
// the source: the real feed.ts boots under the DOM stand-in feed-keynav-typing.test.ts uses (copied here, as that
// file copied it from feed-render-incremental.test.ts), three synthetic cards render, the cursor is armed the way the
// shell arms it, and the keys are pressed with the viewer or the browser up, with focus on a button, and with a key
// already taken. Synthetic only: the notes-api demo world, placeholder sids, hostname TESTHOST.
import { test, mock, after } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const FEED_SRC = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "feed.ts"), "utf8");

// ── a DOM stand-in ─────────────────────────────────────────────────────────────────────────────────
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
  focus(): void {}
  blur(): void {}
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
const win: any = new EventTarget();
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
const press = async (key: string): Promise<Event> => {
  const e = Object.assign(new Event("keydown", { cancelable: true }), { key, altKey: false, ctrlKey: false, metaKey: false, shiftKey: false });
  win.dispatchEvent(e);
  await settle();
  return e;
};
after(() => { assert.deepEqual(listenerErrors.map((e) => e.stack || e.message), [], "no listener threw outside a dispatch"); });
const card = (id: string): El => { const c = body.querySelector(`[data-key="a:${id}"]`); assert.ok(c, "card " + id); return c!; };
const title = (id: string): El => { const t = card(id).querySelector(".fcard-title.nav"); assert.ok(t, "title of " + id); return t!; };
const rings = () => body.querySelectorAll(".kbd-focus").length;
/** One key that a handler nearer the target already took (the viewer's Escape, the browser's arrows: both cancel the
 *  keydown on `document`, and the cursor's window handler sees it cancelled). */
const pressTaken = async (key: string): Promise<Event> => {
  const e = Object.assign(new Event("keydown", { cancelable: true }), { key, altKey: false, ctrlKey: false, metaKey: false, shiftKey: false });
  e.preventDefault();
  win.dispatchEvent(e);
  await settle();
  return e;
};
const askPaths = () => posted.filter((m) => m.type === "showAskPath").length;
const onTimeline = () => posted.filter((m) => m.type === "showOnTimeline").length;
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
});

test("viewer up, focus on the body (what Save leaves): Enter and the arrows are nobody's — no descent, no click behind the viewer, no cursor move", async () => {
  const { view, box } = mountViewer();
  doc.activeElement = box;                                          // typing…
  box.hidden = true; doc.activeElement = body;                      // …then Save hid the box: the browser drops focus to the body
  const paths = askPaths();
  const enter = await press("Enter");
  assert.equal(enter.defaultPrevented, false, "not the cursor's: nothing cancelled");
  assert.equal(rings(), 0, "the cursor did not descend into the card behind the viewer");
  assert.ok(card("g1").classList.contains("focused"), "the card cursor stays where it was, still armed");
  const again = await press("Enter");
  assert.equal(again.defaultPrevented, false);
  assert.equal(title("g1").clicks, 0, "no control behind the viewer was clicked");
  assert.equal(onTimeline(), 0, "…so nothing was posted for it either");
  const down = await press("ArrowDown");
  assert.equal(down.defaultPrevented, false, "an arrow is not the cursor's either");
  assert.ok(card("g1").classList.contains("focused") && !card("g2").classList.contains("focused"), "the card cursor did not move");
  assert.equal(askPaths(), paths, "…and lit no journey for a card the person cannot see");
  view.remove();
});

test("viewer up, focus on the composer's Save or Cancel button (Tab from the box): Enter is the button's native click, never cancelled, and the cursor does not descend", async () => {
  const { view, save, cancel } = mountViewer();
  for (const b of [save, cancel]) {
    doc.activeElement = b;
    const enter = await press("Enter");
    assert.equal(enter.defaultPrevented, false, "not cancelled: the browser fires " + b.dataset.act + "'s click");
    assert.equal(rings(), 0, "the cursor did not descend");
    assert.ok(card("g1").classList.contains("focused"), "the card cursor stays armed where it was");
    assert.equal(title("g1").clicks, 0, "nothing behind the viewer was clicked");
  }
  doc.activeElement = body;
  view.remove();
});

test("the file browser up (its sibling overlay in this document): a key the browser does not take itself is still not the cards' behind it", async () => {
  const fb = new El("div"); fb.id = "romp-filebrowse"; body.appendChild(fb);
  const paths = askPaths();
  const right = await press("ArrowRight");                         // the browser reads Up/Down/Left/Backspace/Enter/Escape, not Right
  assert.equal(right.defaultPrevented, false);
  assert.ok(card("g1").classList.contains("focused") && !card("g2").classList.contains("focused"), "the card cursor did not move");
  assert.equal(askPaths(), paths);
  const enter = await press("Enter");
  assert.equal(enter.defaultPrevented, false);
  assert.equal(rings(), 0, "no descent into a card behind the browser");
  fb.remove();
});

test("a key a nearer handler already took is not acted on again: the viewer's Escape closes the viewer and leaves the cursor armed on the board; a taken Enter does not descend", async () => {
  const { view } = mountViewer();
  view.remove();                                                    // file-view.ts's onKey: cancels Escape and removes #romp-fileview before the window sees the key
  await pressTaken("Escape");
  assert.ok(card("g1").classList.contains("focused"), "the cursor is still armed, where the person left it");
  await pressTaken("Enter");
  assert.equal(rings(), 0, "a taken Enter descends nowhere");
  assert.equal(title("g1").clicks, 0);
});

test("board uncovered, focus on a button elsewhere in the feed: Enter is the button's, the arrows stay the cursor's", async () => {
  const headBtn = new El("button"); headBtn.className = "fhead-btn"; body.byId("feed-head")!.appendChild(headBtn);
  doc.activeElement = headBtn;
  const enter = await press("Enter");
  assert.equal(enter.defaultPrevented, false, "not cancelled: the button's native click fires");
  assert.equal(rings(), 0, "the cursor did not descend");
  const paths = askPaths();
  const down = await press("ArrowDown");
  assert.equal(down.defaultPrevented, true, "an arrow with focus on a button is still the cursor's");
  assert.ok(card("g2").classList.contains("focused") && !card("g1").classList.contains("focused"), "the cursor moved to the second card");
  assert.equal(askPaths(), paths + 1, "…and lit its journey, as the hover would");
  const up = await press("ArrowUp");
  assert.equal(up.defaultPrevented, true);
  assert.ok(card("g1").classList.contains("focused"));
  doc.activeElement = body;
  headBtn.remove();
});

test("with the board uncovered and focus back on the page, the cursor works as before: Enter descends and rings the title, Enter again clicks it, Escape steps out", async () => {
  doc.activeElement = body;
  const enter = await press("Enter");
  assert.equal(enter.defaultPrevented, true, "the cursor took the key");
  assert.ok(title("g1").classList.contains("kbd-focus"), "the first control is ringed");
  const again = await press("Enter");
  assert.equal(again.defaultPrevented, true);
  assert.equal(title("g1").clicks, 1, "Enter on the ringed control is exactly one click on it");
  assert.equal(onTimeline(), 1);
  await press("Escape");                                            // card → cards
  assert.equal(rings(), 0);
  assert.ok(card("g1").classList.contains("focused"));
  await press("Escape");                                            // cards → off
  assert.ok(!card("g1").classList.contains("focused"), "the cursor is gone");
  const off = await press("Enter");
  assert.equal(off.defaultPrevented, false, "with the cursor off, Enter is nobody's");
  mock.timers.reset();
});

test("source: the yields read the two full-pane ids the chat pane's typing handler reads, the Tab scope's button set, and the key's own cancelled state", () => {
  assert.match(FEED_SRC, /function boardCovered\(\): boolean \{\n\s*return !!\(document\.getElementById\("romp-fileview"\) \|\| document\.getElementById\("romp-filebrowse"\)\);\n\}/);
  assert.match(FEED_SRC, /function activatesOnEnter\(t: EventTarget \| null\): boolean \{\n\s*const el = t as HTMLElement \| null;\n\s*return !!el && typeof el\.matches === "function" && el\.matches\("button, a"\);\n\}/);
  assert.match(FEED_SRC, /if \(ae\.matches\("button, a, input"\)\) return;/, "the Tab scope's own yield, which the cursor's mirrors");
  const kb = FEED_SRC.slice(FEED_SRC.indexOf("function kbExit(): void"), FEED_SRC.indexOf('window.addEventListener("blur", () => { if (kbMode) kbExit(); });'));
  const yields = kb.match(/^\s*if \((.*?)\) return;/gm)!.map((l) => l.trim());
  assert.deepEqual(yields, [
    "if (!kbMode) return;",
    "if (e.altKey || e.ctrlKey || e.metaKey) return;",
    'if (document.getElementById("feed-modal")) return;',
    "if (typingIn(document.activeElement)) return;",
    "if (e.defaultPrevented) return;",
    "if (boardCovered()) return;",
    'if (e.key === "Enter" && activatesOnEnter(document.activeElement)) return;',
  ], "every yield stands before any key is read, in this order");
  assert.ok(kb.indexOf("if (boardCovered()) return;") < kb.indexOf("const k = e.key"), "…before the key is read");
});

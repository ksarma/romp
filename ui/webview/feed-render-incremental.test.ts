// The feed pane's per-card update gate, RUN (2026-09-06): feed.ts booted under a DOM stand-in, fed synthetic
// frames through the window message it listens on, and watched for what each render REBUILT. Before the
// gate every render re-ran updateAskCard on every card — the name nodes minted anew, the delegation lines
// rebuilt, the whole tree's style invalidated — and the scroll restore then forced a layout of all of it, so
// a delta carrying 58 changed cards cost as much as a full frame (feed-card-gate.ts has the numbers). The
// invariant these frames pin: a card repaints when the kernel sent it (a new object), when a board-level
// input it reads changed (the key), when a gesture touched it, or when it aged (the 15 s live pass); its
// column and order are re-applied on every render regardless; nothing else touches it.
//
// The stand-in is the fleet-live-clock.test.ts tree of plain objects, grown to what feed.ts's boot and
// render paths touch: a small selector engine (descendant chains, classes, ids, attribute presence and
// equality; every pseudo-class, :hover included, matches nothing), insertBefore/sibling walks, dataset-backed data-* attributes, a
// style object with custom properties, EventTarget elements, and counters for the writes the gate is about
// (replaceChildren on a card's name node, textContent sets, getBoundingClientRect reads, scrollTop writes).
// gear.js's initGear returns at once when #rsettings already exists, so the settings modal never mounts.
// Synthetic only: the notes-api demo world, placeholder sids, hostname TESTHOST.
import { test, mock, after } from "node:test";
import * as assert from "node:assert/strict";

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
type Compound = { tag: string | null; id: string | null; classes: string[]; attrs: { name: string; value: string | null }[]; pseudo: boolean };
function parseCompound(s: string): Compound {
  const c: Compound = { tag: null, id: null, classes: [], attrs: [], pseudo: false };
  const m = /^([a-zA-Z][\w-]*)?(.*)$/.exec(s)!;
  c.tag = m[1] ? m[1].toUpperCase() : null;
  const re = /\.([\w-]+)|#([\w-]+)|\[([\w-]+)(?:="([^"]*)")?\]|:[\w-]+(?:\([^)]*\))?/g;
  let t: RegExpExecArray | null;
  while ((t = re.exec(m[2]))) {
    if (t[1]) c.classes.push(t[1]);
    else if (t[2]) c.id = t[2];
    else if (t[3]) c.attrs.push({ name: t[3], value: t[4] ?? null });
    else c.pseudo = true;
  }
  return c;
}
class El extends EventTarget {
  nodeType = 1;
  id = ""; title = ""; hidden = false; value = ""; type = ""; checked = false; disabled = false;
  offsetWidth = 0; offsetHeight = 0; clientWidth = 800; clientHeight = 600; isContentEditable = false;
  onclick: ((ev: any) => void) | null = null;
  parentNode: El | null = null;
  childNodes: Array<El | Txt> = [];
  dataset: Record<string, string | undefined> = {};
  style = new Style();
  rc = 0;                                   // replaceChildren calls (the name nodes' rebuild)
  tc = 0;                                   // textContent sets
  private attrs = new Map<string, string>();
  private classes = new Set<string>();
  private _html = "";
  private _scrollTop = 0;
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
  set textContent(v: string | null) { this.tc++; this.detachAll(); if (v !== null && v !== "") this.appendChild(new Txt(String(v))); }
  get innerHTML(): string { return this._html; }
  set innerHTML(v: string) { this.detachAll(); this._html = v; }
  get scrollTop(): number { return this._scrollTop; }
  set scrollTop(v: number) { scrollWrites.push(v); this._scrollTop = v; }
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
  replaceChildren(...cs: Array<El | Txt | string>): void { this.rc++; this.detachAll(); this.append(...cs); }
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
    // a rendered element gets a rect from its place: a column's cards stack 100 px apart and each column sits
    // at its own left, so a card that changed column or slot has a different rect and one that did not has
    // the same; anything hidden (display:none on it or an ancestor) or detached is a zero rect, as in a browser
    rectReads++;
    for (let n: El | null = this; n; n = n.parentNode) if (n.style.display === "none") return { left: 0, top: 0, right: 0, bottom: 0, width: 0, height: 0 };
    if (!this.isConnected) return { left: 0, top: 0, right: 0, bottom: 0, width: 0, height: 0 };
    const p = this.parentNode!;
    const top = p.children.indexOf(this) * 100, left = p.id.length * 10;
    return { left, top, right: left + 300, bottom: top + 90, width: 300, height: 90 };
  }
  scrollIntoView(): void {}
  focus(): void {}
  blur(): void {}
  matchesCompound(c: Compound): boolean {
    if (c.pseudo) return false;
    if (c.tag && c.tag !== this.tagName) return false;
    if (c.id && c.id !== this.id) return false;
    for (const k of c.classes) if (!this.classes.has(k)) return false;
    for (const a of c.attrs) { const v = this.getAttribute(a.name); if (v === null) return false; if (a.value !== null && v !== a.value) return false; }
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
let rectReads = 0;
const scrollWrites: number[] = [];
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
const T0 = 1781100000;                      // the browser clock at boot
const K0 = T0 - 300;                        // the kernel clock, five minutes behind — every age follows it
const WEB = "11111111-2222-3333-4444-555555555555", API = "11111111-2222-3333-4444-666666666666", TESTS = "11111111-2222-3333-4444-777777777777";
const node = (id: string, text: string, who: string, whoSid: string, children: string[] = []) =>
  ({ id, kind: "ask", text, who, whoSid, whoColor: null, status: "open", t: K0 - 240, last: K0 - 240, children });
const cardOf = (itemId: string, sid: string, name: string, bg: string, text: string, column: string, extra: Record<string, unknown> = {}) => ({
  itemId, sid, name, color: { bg, fg: "#ffffff" }, text, t: K0 - 240, live: true, turnId: "turn-" + itemId, column,
  summary: null, blockSummary: null, tree: [node(itemId, text, name, sid)], ...extra,
});
const g1 = cardOf("g1", WEB, "web", "#3366cc", "Wire the notes-api health route", "working",
  { tree: [node("g1", "Wire the notes-api health route", "web", WEB, ["g1a"]), node("g1a", "Add the /health handler", "web", WEB)] });
const g2 = cardOf("g2", API, "api", "#cc6633", "Write the notes-api README", "working");
const g3 = cardOf("g3", TESTS, "tests", "#33cc66", "Run the notes-api test suite", "working",
  { awaiting: { why: "", kind: "agents", count: 2, since: K0 - 600 } });   // a wait ten minutes old: its duration must move without a frame
const frame = (asks: any[], over: Record<string, unknown> = {}) => ({
  type: "feed", now: K0, nowAt: T0 * 1000, buildId: 1, asks,
  working: [], awaiting: [], stateUnknown: [], order: [WEB, API, TESTS], selfHost: "TESTHOST",
  sessions: [{ sid: WEB, name: "web", color: g1.color }, { sid: API, name: "api", color: g2.color }, { sid: TESTS, name: "tests", color: g3.color }],
  userTodos: {}, bgServices: {}, ...over,
});
const listenerErrors: Error[] = [];
process.on("uncaughtException", (e) => { listenerErrors.push(e); });
const settle = () => new Promise<void>((r) => setImmediate(r));   // let a deferred listener exception land before the assertions
const dispatch = async (f: any) => {
  win.dispatchEvent(new MessageEvent("message", { data: f }));
  await settle();
  if (listenerErrors.length) { const es = listenerErrors.splice(0); throw new Error("a listener threw: " + es.map((e) => e.stack || e.message).join("\n---\n")); }
};
after(() => { assert.deepEqual(listenerErrors.map((e) => e.stack || e.message), [], "no listener threw outside a dispatch (a gesture handler, a timer)"); });
const card = (id: string): any => body.querySelector(`[data-key="a:${id}"]`);
const colOf = (id: string) => card(id)?.parentNode?.id;
const nameRebuilds = () => ({ g1: card("g1")._name.rc, g2: card("g2")._name.rc, g3: card("g3")._name.rc });
const ev = { stopPropagation() {}, preventDefault() {} };

test("frame A: three cards are built once each, in the Working column", async () => {
  mock.timers.enable({ apis: ["Date", "setTimeout", "setInterval"], now: T0 * 1000 });
  await import("./feed");                   // module load: gear (a no-op here), listeners, the 15 s live pass
  assert.equal(posted.filter((m) => m.type === "ready").length, 1, "the ready handshake");
  await dispatch(frame([g1, g2, g3]));
  assert.deepEqual(nameRebuilds(), { g1: 1, g2: 1, g3: 1 }, "each name node was built exactly once");
  assert.deepEqual({ g1: colOf("g1"), g2: colOf("g2"), g3: colOf("g3") }, { g1: "col-asks-list", g2: "col-asks-list", g3: "col-asks-list" });
  assert.equal(card("g1")._time.textContent, "4m ago", "on the kernel's clock (the browser clock is five minutes ahead)");
  assert.equal(card("g3")._awaitWhy.textContent, "Awaiting agents · 10m", "the awaiting box, with the wait's duration");
  assert.equal(card("g3")._awaitWhy.querySelector(".fask-dur")?.dataset.ageFmt, "dur", "…as a stamped element the live pass can reach");
  // open card 1's Sub-goals section (a gesture): the section state must survive the renders below untouched
  card("g1")._subBtn.onclick(ev);
  assert.equal(card("g1")._subBtn.getAttribute("aria-pressed"), "true");
  assert.equal(card("g1")._checklist.children.length, 1, "one sub-goal row");
});

test("frame B: only the card whose object changed repaints; it moves column; the other cards keep their DOM and their open section", async () => {
  const row = card("g1")._checklist.children[0];
  const readsBefore = rectReads;
  list.scrollTop = 120; scrollWrites.length = 0;
  const g2done = { ...g2, column: "completed" };
  await dispatch(frame([g1, g2done, g3]));
  assert.deepEqual(nameRebuilds(), { g1: 1, g2: 2, g3: 1 }, "exactly one name rebuild: the re-sent card");
  assert.equal(colOf("g2"), "col-completed-list", "the changed card moved to Completed");
  assert.equal(colOf("g1"), "col-asks-list"); assert.equal(colOf("g3"), "col-asks-list");
  assert.equal(body.byId("col-asks-count")!.textContent, "2"); assert.equal(body.byId("col-completed-count")!.textContent, "1");
  assert.equal(card("g1")._subBtn.getAttribute("aria-pressed"), "true", "the open section stayed open");
  assert.equal(card("g1")._checklist.children[0], row, "…and its rows are the same nodes, not a rebuild");
  assert.equal(scrollWrites[scrollWrites.length - 1], 120, "the scroll position is restored");
  assert.ok(rectReads > readsBefore, "a column changed, so the FLIP passes read rects");
  assert.ok(card("g2").classList.contains("fitem-flying"), "the card that crossed columns flies in the back layer");
  assert.match(card("g2").style.transform, /^translate\(/, "…inverted to its old spot first");
});

test("frame C: the same frame re-dispatched (a federation re-emit) rebuilds nothing and reads no rects", async () => {
  // frame B emptied api's run in Working, so its session header left as a ghost (re-keyed x:N until its exit
  // animation ends, or the 600 ms backstop) and g2 flew to Completed; 700 ms later both backstops have fired:
  // no transition ends under the stand-in, so the fly's own backstop is what takes the card out of the back
  // layer (before it, a card whose transitionend never came kept pointer-events:none until its next repaint)
  // (two ticks: a timer created inside a mock tick is stamped with the tick's END time, so one 700 ms tick
  // would run the nested animation frame AFTER the 650 ms backstop — the reverse of a browser's order)
  mock.timers.tick(20);
  assert.equal(card("g2").style.transform, "translate(0, 0)", "the frame after the invert releases the offset");
  mock.timers.tick(680);
  assert.equal(body.querySelectorAll(".sess-exit").length, 0, "the exited header is gone");
  assert.ok(!card("g2").classList.contains("fitem-flying"), "the fly ended by its backstop");
  assert.equal(card("g2").style.transform, "", "…and the card is back in normal flow");
  await dispatch(frame([g1, { ...g2, column: "completed" }, g3]));   // a fresh copy of g2 IS a new object: it repaints — that is the contract
  assert.deepEqual(nameRebuilds(), { g1: 1, g2: 3, g3: 1 });
  const readsBefore = rectReads;
  const tcBefore = { g1: card("g1")._title.tc, g2: card("g2")._title.tc, g3: card("g3")._title.tc };
  const same = frame([g1, card("g2")._it, g3]);              // now the very objects the cards were painted from
  await dispatch(same);
  await dispatch(same);
  assert.deepEqual(nameRebuilds(), { g1: 1, g2: 3, g3: 1 }, "zero rebuilds on identical objects under identical inputs");
  assert.deepEqual({ g1: card("g1")._title.tc, g2: card("g2")._title.tc, g3: card("g3")._title.tc }, tcBefore,
    "no title text was rewritten either");
  assert.equal(rectReads, readsBefore, "no column's key sequence changed: the FLIP passes read nothing");
});

test("frame D: `working` naming card 1's session repaints card 1 (its dot) and leaves the other sessions' cards alone", async () => {
  const g2now = card("g2")._it;
  await dispatch(frame([g1, g2now, g3], { working: ["web"] }));
  assert.deepEqual(nameRebuilds(), { g1: 2, g2: 3, g3: 1 }, "the key changed for web's card only");
  assert.ok(card("g1")._name.previousElementSibling?.classList.contains("fwork-dot"), "the working dot sits before the name");
  await dispatch(frame([g1, g2now, g3], { working: ["web"] }));
  assert.deepEqual(nameRebuilds(), { g1: 2, g2: 3, g3: 1 }, "…and the same inputs again change nothing");
});

test("a colour echo (an in-place write into the shared objects) repaints that session's cards through the key, once", async () => {
  const before = nameRebuilds();
  win.dispatchEvent(Object.assign(new Event("storage"), { key: "romp:color-echo", newValue: JSON.stringify({ sid: API, bg: "#cc3366" }) }));
  assert.deepEqual(nameRebuilds(), { g1: before.g1, g2: before.g2 + 1, g3: before.g3 }, "api's card repainted, the others did not");
  assert.equal(card("g2")._name.style.color, "#cc3366");
  await dispatch(frame([g1, card("g2")._it, g3], { working: ["web"] }));   // the same objects again, colour still echoed
  assert.deepEqual(nameRebuilds(), { g1: before.g1, g2: before.g2 + 1, g3: before.g3 }, "the echoed colour is in the key: no flap, no second rebuild");
});

test("the 15 s live pass moves ages and durations on cards no frame touched, writing only the labels whose text changed", () => {
  const before = nameRebuilds();
  const time1 = card("g1")._time, dur3 = card("g3")._awaitWhy.querySelector(".fask-dur")!;
  const t1 = time1.tc, d3 = dur3.tc;
  mock.timers.tick(15_000);                 // 4m15s: "4m ago" still; the wait is 10m15s: "10m" still
  assert.equal(time1.tc, t1, "an unchanged label is not written");
  assert.equal(dur3.tc, d3);
  mock.timers.tick(45_000);                 // 5m00s and 11m00s
  assert.equal(time1.textContent, "5m ago"); assert.equal(dur3.textContent, "11m");
  assert.equal(time1.tc, t1 + 1, "one write, at the minute it crossed");
  assert.equal(dur3.tc, d3 + 1);
  assert.deepEqual(nameRebuilds(), before, "the pass repaints labels, never cards");
});

test("Undo inside a card's 180 ms collapse keeps the restored card: the gesture strips .dismissing, which the class rewrite used to do", () => {
  const c3 = card("g3");
  c3._clr.onclick(ev);                      // Clear: .dismissing + a 180 ms removal timer, the id held back from pushes
  assert.ok(c3.classList.contains("dismissing"));
  assert.equal(posted.filter((m) => m.type === "askClear").length, 1);
  body.byId("feed-undoclear")!.onclick!(ev);   // Undo before the collapse ends: the same object, the same key
  assert.ok(!c3.classList.contains("dismissing"), "Undo took the class off");
  mock.timers.tick(200);                    // the collapse timer fires and finds nothing to remove
  assert.equal(card("g3"), c3, "the restored card is still on the board, the same element");
  assert.equal(colOf("g3"), "col-asks-list");
});

test("a card moving into a FOLDED column (display:none, a zero rect) gets no fly: nothing to glide to, and the class it would wear turns the pointer off", async () => {
  body.byId("col-completed-list")!.style.display = "none";   // the Completed section folded to its header
  const g3done = { ...card("g3")._it, column: "completed" };
  await dispatch(frame([g1, card("g2")._it, g3done], { working: ["web"] }));
  assert.equal(colOf("g3"), "col-completed-list", "the card moved");
  assert.ok(!card("g3").classList.contains("fitem-flying"), "no fly into a column nobody can see");
  assert.equal(card("g3").style.transform ?? "", "", "no inverted transform left on it");
  body.byId("col-completed-list")!.style.display = "";
});

test("…and a card LEAVING a folded column (a zero First rect) gets no fly either: nothing to glide from", async () => {
  body.byId("col-completed-list")!.style.display = "none";   // g3 sits in the folded Completed section
  await dispatch(frame([g1, card("g2")._it, { ...card("g3")._it, column: "working" }], { working: ["web"] }));
  assert.equal(colOf("g3"), "col-asks-list", "the card moved back to Working");
  assert.ok(!card("g3").classList.contains("fitem-flying"), "no fly from a spot nobody could see");
  assert.equal(card("g3").style.transform ?? "", "", "no inverted transform from the pane's corner");
  body.byId("col-completed-list")!.style.display = "";
});

test("a second fly of the same card while the first still runs keeps its own Invert through the first fly's cancel, and the first fly's backstop leaves it alone", async () => {
  const c2 = card("g2");
  await dispatch(frame([g1, { ...c2._it, column: "working" }, card("g3")._it], { working: ["web"] }));   // fly 1: Completed → Working
  assert.ok(c2.classList.contains("fitem-flying"));
  mock.timers.tick(20);                                        // fly 1 plays: its transition is running
  assert.equal(c2.style.transform, "translate(0, 0)");
  await dispatch(frame([g1, { ...c2._it, column: "completed" }, card("g3")._it], { working: ["web"] }));   // fly 2, mid-flight: back to Completed
  const inverted = c2.style.transform;
  assert.match(inverted, /^translate\(-?\d/, "fly 2 inverted the card to its old spot");
  assert.notEqual(inverted, "translate(0, 0)");
  // the browser cancels fly 1's transition on that write and tells EVERY listener before fly 2's Play frame
  c2.dispatchEvent(Object.assign(new Event("transitioncancel"), { propertyName: "transform" }));
  assert.equal(c2.style.transform, inverted, "fly 1's cancel handler is superseded; fly 2's ignores an event before its own Play — the Invert survives");
  assert.ok(c2.classList.contains("fitem-flying"), "…and the back layer stays on for the crossing");
  mock.timers.tick(20);                                        // fly 2 plays
  assert.equal(c2.style.transform, "translate(0, 0)");
  assert.match(c2.style.transition, /transform \.42s/);
  mock.timers.tick(610);                                       // fly 1's 650 ms backstop falls due: superseded, a no-op
  assert.match(c2.style.transition, /transform \.42s/, "fly 2 is still in flight");
  assert.ok(c2.classList.contains("fitem-flying"));
  mock.timers.tick(20);                                        // fly 2's own backstop ends it
  assert.equal(c2.style.transform, "");
  assert.equal(c2.style.transition, "");
  assert.ok(!c2.classList.contains("fitem-flying"));
});

test("Retry latches on the click and re-arms only on a deciding event: the kernel's reply frame, or a repaint of the card", async () => {
  const blockedG1 = { ...g1, blocked: { state: "apiError", what: "the API returned 529", status: 529 } };
  await dispatch(frame([blockedG1, card("g2")._it, card("g3")._it]));   // web is NOT working: the API-error unit shows
  const retry = card("g1")._apiRetry;
  assert.equal(retry.style.display, ""); assert.equal(retry.disabled, false); assert.equal(retry.textContent, "Retry");
  const sent = posted.length;
  retry.onclick(ev);
  assert.deepEqual(posted.slice(sent), [{ type: "apiRetry", id: WEB, manual: true }], "a MANUAL retry: the kernel fires it past every auto gate");
  assert.equal(retry.disabled, true); assert.equal(retry.textContent, "Retrying…");
  await dispatch(frame([blockedG1, card("g2")._it, card("g3")._it]));   // the same objects again: nothing decided
  assert.equal(retry.disabled, true, "a re-emit is not a deciding event");
  await dispatch({ type: "err", sid: API, text: "another session's business" });
  assert.equal(retry.disabled, true, "another session's reply is not this card's event");
  await dispatch({ type: "err", sid: WEB, text: "the retry was not delivered" });
  assert.equal(retry.disabled, false, "the kernel's reply for this session re-arms it");
  assert.equal(retry.textContent, "Retry");
  retry.onclick(ev);
  assert.equal(retry.disabled, true);
  await dispatch(frame([{ ...blockedG1 }, card("g2")._it, card("g3")._it]));   // a new object for the card: it repaints
  assert.equal(retry.disabled, false, "a repaint re-arms it too");
  await dispatch(frame([g1, card("g2")._it, card("g3")._it]));   // the block is gone: the unit hides
  assert.equal(card("g1")._apiRetry.style.display, "none");
});

test("a second reveal pulse inside the first's window is not cut short by the first's backstop", async () => {
  const c1 = card("g1");
  await dispatch({ type: "revealCards", keys: ["g1"] });
  assert.ok(c1.classList.contains("card-pulse"));
  mock.timers.tick(600);
  await dispatch({ type: "revealCards", keys: ["g1"] });        // pulse again, 600 ms in
  mock.timers.tick(1000);                                       // the FIRST backstop's moment (1500 ms after it armed)
  assert.ok(c1.classList.contains("card-pulse"), "the second pulse still shows: one handle per element");
  mock.timers.tick(600);                                        // the second backstop
  assert.ok(!c1.classList.contains("card-pulse"), "…and it comes off at its own end");
  mock.timers.reset();
});

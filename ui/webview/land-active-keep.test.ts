// landActive's take and its roads, EXECUTED (PR E, the maintainer's round 2 ruling A; the outcome rule of the maintainer's round 3 ruling
// B). A land takes the figures the unit observer parked since the last paint (applyMeasure: the head spacer and the gap units re-sized) on
// every road but the nothing-armed re-show, BEFORE its landing attempt, because the roads that land read the target's live rect
// (scrollToAnchor, landOn) and a resident target rebuilds nothing, so a take after the attempt would re-size the spacer under a row just
// placed. The take is decided on what is ARMED; the OUTCOME decides what stands. A land whose anchor MISSES with no fetch armed (nowhere in
// the transcript, the wrong kind) puts the row the SAVED place held back at its offset over the take (captured at that place before the
// take: the scroller does not hold the saved place yet on a switch, the leaving tab's position is still under the viewport); where that
// restore has no row to put back (no row was capturable, the saved place inside a spacer; the captured row gone, because the attempt's
// window build around the anchor's unit replaced the rows before its re-query missed) the take is UNDONE (untakeMeasure: the figures
// parked again, the spacers back) and the raw land-saved write of the saved scrollTop lands in the layout it was saved in, as on the
// nothing-armed road, where nothing was taken. A miss with a FETCH ARMED puts nothing back, because the reply is still coming: a pre-jump's
// placement stands over the take it was measured in, and with no pre-jump the saved scrollTop is written raw with the take undone (the road on
// the second behaviour PR 861 changed here, below). Until the author's pass 3 the missed land took and wrote raw (the reader moved by the
// spacer's delta: the maintainer's round 1 ruling's HIGH 2 shape one road over, while the comment in the source said the road could not
// happen); until this pass the two no-row roads took and wrote raw, disclosed (the third road named by the author's own verifiers after
// pass 3, where the comment, the pin and the body had named two). The reload restore with no anchor row is the one raw write after a take
// that KEEPS the take: its scrollTop was measured on the page before the reload, whose figures the take re-derives. That exception is the
// VALUE's, not the site's: a write of a figure measured in the state it lands in needs no take-back only while nothing is taken between the
// read of that figure and the write, so the world traces every take-class event (the take, the untake, the spacer redraws, every write of
// the parked flag and of the view's take state, `measured`, `avgTurnH` and `pxPerTurn`) and every geometry event in order with the record's
// binding, the site's own read of `rs.top` and the writes, and the ordering is pinned on both raw reload shapes from the binding to the
// write. That window is WIDER than the one ruled, which runs from the site's own read of `rs.top` to the write (one expression today), so
// it is strictly stronger, and that is why the anchor at the binding stands (the maintainer's round 4 ruling, ordering-3); the persisted
// top's first read is earlier still, in landActive's `saved` computation, where takeReloadScroll admits the record to decide the take (the
// reviewer's answer to the author's tail-2 question, 2026-09-21; spacer-measure.test.ts checks the same window on the tree, where a take
// through a helper the site calls is named). landActive,
// captureScrollAnchor and restoreScrollAnchor are lifted from render.ts and run over a layout model (the toggle harness's: a head spacer,
// rows of known heights, a scroller with a viewport); the stubs record the take, the untake, the landing attempt and every write, and
// scrollToAnchor answers what the world says. keepPlaceAcrossWindow, the other taker pinned by source text alone until the author's pass
// 3, is lifted the same way over both its roads (the direct restore, the deep-link re-land with the kept offset) and the road where both
// miss: it takes before the restores (restoreScrollAnchor needs the row's y in the re-sized layout), so on a double miss it took and
// wrote nothing, and the content under the viewport moved by the take's delta; the row under the viewport top, captured before the take,
// goes back at its offset there, and when the attempt's rebuild dropped that row too the take is undone. Synthetic uuids.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { takeReloadScroll, type ReloadScroll } from "./reload-restore";
import { hideEdges } from "../test-dom-shim";

const requireCjs = createRequire(__filename);
const RENDER = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "render.ts"), "utf8");

function liftBetween(startAnchor: string, endAnchor: string): string {
  const a = RENDER.indexOf(startAnchor), b = RENDER.indexOf(endAnchor, a);
  assert.ok(a > 0 && b > a, `anchors not found: ${startAnchor.slice(0, 40)} or ${endAnchor.slice(0, 40)} moved; re-anchor`);
  return requireCjs("esbuild").transformSync(RENDER.slice(a, b), { loader: "ts" }).code;
}

/** The layout model: the scroller holds one view whose children stack from offset 0, each of a known height; a row's client rect is its
 *  offset less the scroller's scrollTop (the scroller's own rect top is 0). Geometry is OBSERVABLE here and the model FAILS CLOSED on what it
 *  cannot represent (the maintainer's round 4 ruling, closure-6: until this pass a row had no `style`, the view element's `style` was an
 *  untracked bag and a production-shaped `style.height` write was a silent no-op, while a spacer query planted in the window reddened on
 *  selector text rather than on the geometry it wrote). A row's `style.height` is routed into its `h` and recorded on the world's trace; the
 *  view element's `style.height`, which the model has no figure for (its height is its children's sum), throws; any other style key throws
 *  on a read, a write, a delete or a define, and a define of `height` on the style object throws too; and the style OBJECT itself is
 *  non-writable on a row and on the view element, so replacing it throws too (the
 *  maintainer's round 5 ruling, extra8-3: a replaced style would have routed every later height write into a plain object in silence). A child inserted or removed through the DOM's methods (appendChild, insertBefore, removeChild, replaceChildren, a
 *  node's remove) is recorded; the children collection is read-only like the DOM's. A selector is resolved for what the lifted code and
 *  production's spacer code are entitled to query among the children (every uuid-carrying row, one uuid, one class with or without
 *  `:scope > `), and any other selector throws, so an unmodelled query fails closed instead of matching nothing. Every property the model
 *  LACKS fails closed too (the author's fixer pass over the pass after the maintainer's round 4 ruling: until then a write of `hidden`,
 *  `innerHTML` or `textContent` on a node created the property in silence under strict mode, and a read of `lastElementChild`, `firstChild`
 *  or `classList` gave undefined, which an optional chain swallowed, so a production-shaped change or removal in the window passed both
 *  halves green): each of the scroller, the view element and a row is a Proxy (failClosed) whose read, write or delete of a key that is neither
 *  an own property nor on the prototype throws with the model's message. The geometry events on the trace: `style <class> height=<px> (was
 *  <px>)`, `child +<class>:<px>`, `child -<class>:<px>`, beside the take-class events the stubs and the accessors push (the world below). */
type Write = { writer: string; top: number; stick: boolean; from: number | undefined };
const px = (v: unknown, what: string): number => { const m = /^(-?\d+(?:\.\d+)?)px$/.exec(String(v)); assert.ok(m, what + ": the model reads a height in px, not " + JSON.stringify(v)); return Number(m![1]); };
/** A `style` whose `height` reads `read()` and writes through `write`; every other key throws on a read, a write, a delete or a define (a write
 *  there would change nothing the model measures, so it fails closed rather than passing silently), and a DEFINE of `height` throws too: with
 *  no defineProperty trap a define landed an own property on the proxy's target, which the traps never read, so the model kept routing where a
 *  DOM element's style takes the own property over its accessor and every later height write is a silent no-op (the closing lens over the
 *  author's fixer pass over the pass after the maintainer's round 5, CL-4). `name` names the element in the errors. */
function styleOf(name: string, read: () => number, write: (h: number) => void): Record<string, string> {
  const refuse = (k: string | symbol, what: string): never => { throw new Error(name + ".style." + String(k) + " " + what + ": the model carries a height and nothing else, so this fails closed rather than passing as a silent no-op"); };
  return new Proxy({} as Record<string, string>, {
    get: (_t, k) => k === "height" ? read() + "px" : typeof k === "symbol" || k === "toJSON" || k === "then" ? undefined : refuse(k, "read"),
    set: (_t, k, v) => { if (k === "height") { write(px(v, name + ".style.height")); return true; } return refuse(k, "written as " + JSON.stringify(v)); },
    deleteProperty: (_t, k) => refuse(k, "deleted"),
    defineProperty: (_t, k) => refuse(k, "defined"),
  });
}
/** A model object that FAILS CLOSED on any property it lacks: a read or a write of a key that is neither an own property nor on the
 *  prototype throws, naming the object and the key, and a delete or a DEFINE of any key throws (the DOM's nodes have no deletable geometry,
 *  and a define, Object.defineProperty's, Object.defineProperties' or Reflect.defineProperty's, reaches the defineProperty trap and not the
 *  set trap, so a define of `style` replaced the instrumented style in silence until the author's fixer pass over the pass after the
 *  maintainer's round 5, the door its verifier (a) found still open beside the refused write of the object), so a
 *  production-shaped change the model has no figure for reds with the model's message instead of passing as a silent no-op. The JS internals
 *  a dump or an await reads (symbols, `then`, `toJSON`) read undefined. `hideEdges` runs on the raw object before it is wrapped, so the
 *  projection is the raw object's and the ratchet in test-dom-shim.test.ts reads the call. */
function failClosed<T extends object>(o: T, name: string): T {
  const known = (k: string | symbol): boolean => typeof k === "symbol" || k in o || k === "then" || k === "toJSON";
  return new Proxy(o, {
    get: (t, k, r) => { if (known(k)) return Reflect.get(t, k, r); throw new Error(name + "." + String(k) + " read: the model has no such property, so this fails closed rather than reading undefined"); },
    set: (t, k, v, r) => {
      if (!known(k)) throw new Error(name + "." + String(k) + " written as " + JSON.stringify(v) + ": the model has no such property, so this fails closed rather than passing as a silent no-op");
      // the TARGET as the receiver, as the view record's set trap below has it: with the proxy as the receiver an ordinary write of an existing
      // data property ends in the proxy's defineProperty trap, which refuses every define; the model's classes have no setter that reads
      // `this`, so the receiver changes nothing else
      if (Reflect.set(t, k, v)) return true;
      throw new Error(name + "." + String(k) + " written as " + JSON.stringify(v) + ": read-only in the model as in the DOM (a getter with no setter, or the instrumented style object, which the DOM's element.style also refuses to replace), so this fails closed rather than passing as a silent no-op");
    },
    deleteProperty: (_t, k) => { throw new Error(name + "." + String(k) + " deleted: the model has nothing to delete, so this fails closed rather than passing as a silent no-op"); },
    defineProperty: (_t, k) => { throw new Error(name + "." + String(k) + " defined: the model has nothing to define (a define of `style` would replace the instrumented style, where the DOM's element takes an own property over its accessor), so this fails closed rather than passing as a silent no-op"); },
  });
}
class Content {
  scrollTop = 0; host: Host | null = null;
  constructor(private readonly viewportH: number, public trace: string[]) { hideEdges(this); return failClosed(this, "content"); }
  /** The viewport's height, read-only as in the DOM: a write here is refused by the proxy with the model's message (until the author's fixer
   *  pass over the pass after the maintainer's round 4 ruling, VE-6, a public field a write in the window could move in silence). */
  get clientHeight(): number { return this.viewportH; }
  get scrollHeight(): number { return this.host ? this.host.height() : 0; }
  getBoundingClientRect() { return { top: 0, bottom: this.clientHeight }; }
}
class Node {
  dataset: Record<string, string> = {}; host: Host | null = null; declare readonly style: Record<string, string>;
  constructor(public h: number, public className: string, uuid?: string) {
    if (uuid) this.dataset.uuid = uuid;
    // a height written on a row moves the model's geometry and is recorded on the trace of the view the row is in (a detached row's write
    // reaches the trace when the row is inserted, with its height). The style object is installed NON-WRITABLE (configurable, so hideEdges
    // can still hide it), so a write of the object itself, `row.style = {...}`, fails Reflect.set and the proxy's set trap throws: until the
    // pass after the maintainer's round 5 ruling (extra8-3) it was a writable field and a replaced style routed every later height write
    // into a plain object, a silent no-op the model refused for its keys but not for the object
    Object.defineProperty(this, "style", { value: styleOf("<" + className + ">", () => this.h, (h) => { this.host?.content.trace.push("style " + this.className + " height=" + h + " (was " + this.h + ")"); this.h = h; }), writable: false, enumerable: false, configurable: true });
    hideEdges(this); return failClosed(this, "<" + className + ">");
  }
  getBoundingClientRect() { const top = this.host!.offsetOf(this) - this.host!.content.scrollTop; return { top, bottom: top + this.h }; }
  remove(): void { this.host?.removeChild(this); }
}
class Host {
  private kids: Node[] = []; declare readonly style: Record<string, string>;
  constructor(public content: Content) {
    const noHeight = (): never => { throw new Error("v.el.style.height: the view element's height is its children's sum and the model has no figure of its own for it, so a read or a write here fails closed rather than passing as a silent no-op"); };
    Object.defineProperty(this, "style", { value: styleOf("v.el", noHeight, noHeight), writable: false, enumerable: false, configurable: true });   // non-writable, as on Node: the object itself cannot be replaced
    hideEdges(this); const p = failClosed(this, "v.el"); content.host = p; return p;
  }
  /** The children, read-only like the DOM's collection: insertion and removal go through the methods below, which record them. */
  get children(): readonly Node[] { return Object.freeze([...this.kids]); }
  height(): number { return this.kids.reduce((a, c) => a + c.h, 0); }
  add(n: Node): Node { return this.appendChild(n); }
  appendChild(n: Node): Node { return this.insertBefore(n, null); }
  insertBefore(n: Node, ref: Node | null): Node {
    if (n.host === this) this.removeChild(n);   // the DOM moves a node already in the tree
    const i = ref ? this.kids.indexOf(ref) : this.kids.length; assert.ok(i >= 0, "insertBefore: the reference node is a child");
    n.host = this; this.kids.splice(i, 0, n); this.content.trace.push("child +" + n.className + ":" + n.h); return n;
  }
  removeChild(n: Node): Node { const i = this.kids.indexOf(n); assert.ok(i >= 0, "removeChild: the node is a child"); this.kids.splice(i, 1); n.host = null; this.content.trace.push("child -" + n.className + ":" + n.h); return n; }
  replaceChildren(...ns: Node[]): void { for (const c of [...this.kids]) this.removeChild(c); for (const n of ns) this.appendChild(n); }
  offsetOf(n: Node): number { let y = 0; for (const c of this.kids) { if (c === n) return y; y += c.h; } throw new Error("not a child"); }
  /** What a caller is entitled to query among the children: every uuid-carrying row (`[data-uuid]`, captureScrollAnchor's), one uuid
   *  (restoreScrollAnchor's), or one class with or without `:scope > ` (production's spacer and gap redraws: `.tx-spacer-top`,
   *  `:scope > .tx-gap`); any other selector throws. Until this pass the two methods asserted their one caller's selector text, so a spacer
   *  query planted in the window reddened on the text, an accidental guard standing in for the geometry check (closure-6). */
  querySelectorAll(sel: string): Node[] {
    if (sel === "[data-uuid]") return this.kids.filter((c) => c.dataset.uuid != null);
    const byUuid = /^\[data-uuid="([^"]*)"\]$/.exec(sel); if (byUuid) return this.kids.filter((c) => c.dataset.uuid === byUuid[1]);
    const byClass = /^(?::scope > )?\.([A-Za-z0-9_-]+)$/.exec(sel); if (byClass) return this.kids.filter((c) => c.className.split(/\s+/).includes(byClass[1]));
    throw new Error("the model resolves [data-uuid], [data-uuid=\"…\"] and one class among the view's children; not " + JSON.stringify(sel) + " (an unmodelled query fails closed rather than matching nothing)");
  }
  querySelector(sel: string): Node | null { return this.querySelectorAll(sel)[0] ?? null; }
}

type Arm = { anchor?: string; t?: number; keepY?: number; seek?: { sid: string; uuid: string; kind: string }; reload?: unknown; land?: boolean; landT?: boolean; rebuild?: (host: Host) => void; preJump?: number; fetch?: boolean; landAt?: number; stale?: boolean };
type Opts = { spacerH?: number; n?: number; rowH?: number; clientHeight?: number; saved: number; scrollTop?: number; shown?: boolean; stick?: boolean; parked?: boolean; bottomSpacerH?: number; gap?: boolean };
type World = { content: Content; host: Host; v: any; spacer: Node; rows: Node[]; writes: Write[]; calls: any[]; rows_: any[]; toasts: string[]; trace: string[]; geometryAt: Record<string, string[]>; land: (content: Content | null, v: any, scrollerHolds?: boolean) => void; parked: () => boolean };
const D = 300;   // the take's delta: the head spacer re-sized by the re-measured figure over the head gap's turns

/** A view of `n` rows of `rowH` under a head spacer of `spacerH` (uuids r0..), in a scroller of `clientHeight`; `saved` is the view's
 *  saved place (v.scrollTop, recorded when the tab was left) and `scrollTop` the scroller's position when the land runs (the saved place
 *  on a re-show; the LEAVING tab's on a switch, the default here being the saved place). `parked`: a figure waits for a taker, and the
 *  take grows the head spacer by D (the stubbed applyMeasure models what sizeSpacers draws from the taken figure). `arm` is what the
 *  land finds armed and how the stubbed landings answer (`land`: scrollToAnchor's answer, `landT`: landNearestMoment's; `rebuild` runs
 *  over the host before scrollToAnchor answers: the window rebuilt around the anchor's unit, rows leaving; `preJump`, the place the attempt's
 *  pre-jump writes (land-guess) before scrollToAnchor answers, the record synced to the scroller after it and follow mode ended, as
 *  preJumpIntoGap does for a deep link with a time whose window is asked for, which marks the pre-jump for the attempt, anchorPreJumped;
 *  production reaches the pre-jump only through the window ask, which arms the fetch, so the world refuses a `preJump` without `fetch`;
 *  `fetch`, the attempt's miss leaves a fetch armed for the anchor, anchorPendingOlder, as scrollToAnchor's four fetch roads do, both marks
 *  cleared on entry as scrollToAnchor clears them; `landAt`, the place a landing that hits writes, land-on, as landOn does; `stale`, both
 *  marks left set by an earlier attempt whose fetch is still on the wire). `gap`: a 40 px gap row
 *  (`tx-gap`, with the unit range production's redraw reads) between r4 and r5, and `bottomSpacerH` a bottom spacer, so a view holds every
 *  kind of child production's spacer code draws on: a gap redraw or a bottom-spacer resize planted in the ordering window matched nothing in a
 *  view without them and moved no geometry (the author's fixer pass over the pass after the maintainer's round 4 ruling, VE-3). */
function world(o: Opts, arm: Arm = {}): World {
  const spacerH = o.spacerH ?? 2000, n = o.n ?? 10, rowH = o.rowH ?? 100, clientHeight = o.clientHeight ?? 600;
  const trace: string[] = [];   // the land's events in order; the world's own construction below is cut from it
  const content = new Content(clientHeight, trace); const host = new Host(content);
  const spacer = host.add(new Node(spacerH, "tx-spacer tx-spacer-top"));
  const rows: Node[] = []; for (let i = 0; i < n; i++) rows.push(host.add(new Node(rowH, "turn", "r" + i)));
  if (o.gap) { const g = new Node(40, "tx-gap"); g.dataset.lo = "5"; g.dataset.hi = "7"; host.insertBefore(g, rows[5] ?? null); }
  if (o.bottomSpacerH) host.add(new Node(o.bottomSpacerH, "tx-spacer tx-spacer-bot"));
  trace.length = 0;
  content.scrollTop = o.scrollTop ?? o.saved;
  const takeState: Record<string, unknown> = { measured: undefined, avgTurnH: undefined, pxPerTurn: undefined };
  const vRaw: any = { el: host, scrollTop: o.saved, shown: o.shown ?? true, stick: o.stick ?? false };
  // the view the lifted code holds: a Proxy over the record whose deleteProperty trap throws for every key, so a delete of the take state in
  // ANY form fails closed (the `delete` operator; `Reflect.deleteProperty`, which returns false and throws nothing on a non-configurable
  // property, under strict mode too; either with a computed key): until the author's fixer pass over the pass after the maintainer's round 4
  // ruling (VT21) the accessors below were the whole refusal and a Reflect.deleteProperty of a take-state field passed in silence. Its
  // defineProperty trap throws for every key the same way (Object.defineProperty, Object.defineProperties, Reflect.defineProperty, a computed
  // key): until the closing fixer over the author's fixer pass over pass 5 (CL-2) a define of a take-state field reddened by the engine's own
  // TypeError on the non-configurable accessor, and Reflect.defineProperty, which returns false instead of throwing, passed in silence. The
  // set trap forwards a write to the record itself (a write through a Proxy with no set trap ends in its defineProperty trap, the receiver
  // being the Proxy), so the lifted code's own writes of `stick` and `shown` land and a write of a take-state field reaches its accessor.
  const isTakeState = (k: string | symbol): boolean => Object.prototype.hasOwnProperty.call(takeState, k);
  const v: any = new Proxy(vRaw, {
    set: (t, k, val) => Reflect.set(t, k, val),
    deleteProperty: (_t, k) => { throw new Error("v." + String(k) + " deleted" + (isTakeState(k) ? ": a delete of the view's take state is a take at the site, refused in every form (the delete operator, Reflect.deleteProperty, a computed key)" : ": the model's view has no deletable field, so this fails closed rather than passing as a silent no-op")); },
    defineProperty: (_t, k) => { throw new Error("v." + String(k) + " defined" + (isTakeState(k) ? ": a define of the view's take state is a take at the site, refused in every form (Object.defineProperty, Object.defineProperties, Reflect.defineProperty, a computed key)" : ": the model's view has no definable field, so this fails closed rather than passing as a silent no-op")); },
  });
  const H: any = { content, v, spacer, writes: [] as Write[], calls: [] as any[], rows: [] as any[], toasts: [] as string[], deferred: [] as any[], trace, geometryAt: {} as Record<string, string[]>,
                   delta: D, arm,
                   land: (uuid: string) => {
                     if (arm.rebuild) arm.rebuild(host);
                     if (arm.preJump != null) { assert.ok(arm.fetch, "a pre-jump runs only inside the window ask (requestAround), which arms the fetch: the world models no pre-jump without one"); v.stick = false; H.writeScroll(content, arm.preJump, "land-guess"); v.scrollTop = content.scrollTop; }
                     if (arm.land && arm.landAt != null) H.writeScroll(content, arm.landAt, "land-on");
                     return !!arm.land;
                   }, landT: (t: number) => !!arm.landT };
  // the take state, the persisted top and the geometry, traced in order with the writes (the ordering test below). The take state: the parked
  // flag, which the stubs hold in place of production's parked figures, and the view's own three fields (`measured`, `avgTurnH`, `pxPerTurn`:
  // the fields the take writes, the untake restores and the parked figures are read from, derived from render.ts's tree and stated once in
  // spacer-measure.test.ts), each an accessor that traces its write as `<field>=<value>`, whatever the form of the write (an assignment of any
  // operator, a destructuring pattern, Object.assign, Reflect.set, an accessor or a method member of an Object.assign source, whose value the
  // assign reads and sets), and refuses a delete and a define in every form (the view's Proxy above throws on a deleteProperty and on a
  // defineProperty, whether the operator's, Object's or Reflect's, with a literal or a computed key, so a define reds by the model's message
  // and not by the engine's on the non-configurable accessor); nothing lifted here writes them, so a write of any is a take at the
  // site (the maintainer's round 4 ruling, ordering-1: the world traced `measured` alone). The record: takeReloadScroll returns the persisted object ITSELF, the same object to the `saved`
  // decision's call and to the binding's, so the object's identity cannot tell the two records apart; the wrapper below gives each admitting
  // call a serial k, pushes `record#k`, and returns a per-call VIEW of the record whose `top` pushes `read rs.top#k` when read, so the read
  // that precedes the write names the binding whose value is written (the maintainer's round 4 ruling, ordering-2: a window anchored at the
  // last `record` label slid past a planted take whenever a later call admitted the record again). The geometry, every child by class and
  // height, is snapshotted at each record and at each write (`geometryAt`), so the ordering test compares the layout the write lands in
  // with the layout at the binding, over and above the events the model records between them.
  let parkedFlag = o.parked ?? true, recordCalls = 0;
  const geometry = (): string[] => host.children.map((c) => c.className + ":" + c.h);
  H.geometry = geometry;
  // the document stand-in: getElementById alone (the one call the lifted span makes); every other member fails closed with the model's
  // message, so production's `document.createElement` or `document.querySelectorAll` planted in the window reds by the model's refusal
  // rather than a bare TypeError (the author's fixer pass over the pass after the maintainer's round 4 ruling, VE-4)
  H.writeScroll = (c: Content, top: number, writer: string, stick = false, from?: number): void => { H.writes.push({ writer, top, stick, from }); H.trace.push("write " + writer); H.geometryAt["write " + writer] = H.geometry(); c.scrollTop = Math.max(0, Math.min(top, c.scrollHeight - c.clientHeight)); };
  H.document = failClosed({ getElementById: (id: string) => (id === "content" ? content : null) }, "document");
  Object.defineProperty(H, "parked", { get: () => parkedFlag, set: (x: boolean) => { H.trace.push("parked=" + x); parkedFlag = x; } });
  for (const f of Object.keys(takeState)) Object.defineProperty(vRaw, f, { configurable: false, enumerable: true, get: () => takeState[f], set: (x: unknown) => { H.trace.push(f + "=" + JSON.stringify(x)); takeState[f] = x; } });
  H.takeReloadScroll = (saved: unknown, id: string | null): ReloadScroll | null => {
    const r = takeReloadScroll(saved, id);
    if (!r) return null;
    const k = ++recordCalls;
    H.trace.push("record#" + k); H.geometryAt["record#" + k] = geometry();
    return { id: r.id, stick: r.stick, anchor: r.anchor, get top(): number { H.trace.push("read rs.top#" + k); return r.top; } };
  };
  const js = liftBetween("function landActive(content: HTMLElement | null, v: View", "// Scroll ANCHORING for scrolled-up re-renders")
           + liftBetween("function captureScrollAnchor(", "// Live tail-append to the ACTIVE view");
  const prelude = `"use strict";
    const H = HOOKS;
    let pendingAnchor = H.arm.anchor ?? null, pendingAnchorT = H.arm.t ?? null, pendingAnchorIntent = null, pendingAnchorKind = null;
    let pendingAnchorKeepY = H.arm.keepY ?? null, pendingAnchorClick = false, pendingReloadScroll = H.arm.reload ?? null;
    let seek = H.arm.seek ?? null, landTrail = [], landSettling = null, anchorPendingOlder = !!H.arm.stale, anchorPreJumped = !!H.arm.stale;
    const activeId = "A"; const views = new Map([["A", H.v]]); const sessions = new Map([["A", { name: "web" }]]);
    const document = H.document;
    const vscodeApi = { postMessage: (row) => { H.rows.push(row); } };
    const whenChatVisible = (cb) => { H.deferred.push(cb); };
    const takeReloadScroll = H.takeReloadScroll;
    const applyMeasure = (v) => { H.calls.push("applyMeasure"); H.trace.push("take"); if (!H.parked) return false; H.parked = false; H.spacer.h += H.delta; return true; };
    const figuresBefore = (v) => ({ parked: H.parked });   // production's: what is parked before the take (spacer-measure.test.ts executes the real pair)
    const untakeMeasure = (v, fig) => { H.calls.push("untakeMeasure"); H.trace.push("untake"); if (!fig.parked || H.parked) return false; H.parked = true; H.spacer.h -= H.delta; return true; };   // the take undone: the figures parked again, the spacer back
    const redrawGapUnits = () => { H.calls.push("redrawGapUnits"); H.trace.push("redrawGapUnits"); };
    const sizeSpacers = () => { H.calls.push("sizeSpacers"); H.trace.push("sizeSpacers"); };
    const scrollToAnchor = (uuid) => { H.calls.push(["scrollToAnchor", uuid]); anchorPendingOlder = false; anchorPreJumped = false; const hit = H.land(uuid); if (H.arm.preJump != null) anchorPreJumped = true; if (!hit && H.arm.fetch) anchorPendingOlder = true; return hit; };
    const landNearestMoment = (t) => { H.calls.push(["landNearestMoment", t]); return H.landT(t); };
    const revealProgressTick = () => {}; const clearSeek = () => { H.calls.push("clearSeek"); }; const showSeekNote = () => { H.calls.push("showSeekNote"); };
    const settleSample = () => {}; const landToast = (m) => { H.toasts.push(m); }; const notifyShell = () => {};
    const writeScroll = H.writeScroll;
    const scheduleRailSticky = () => {}; const updateJumpBtn = () => {}; const cssEscape = (s) => s;
  `;
  const land = new Function("HOOKS", prelude + js + "\nreturn landActive;")(H) as (content: Content | null, v: any, scrollerHolds?: boolean) => void;
  return { content, host, v, spacer, rows, writes: H.writes, calls: H.calls, rows_: H.rows, toasts: H.toasts, trace: H.trace, geometryAt: H.geometryAt, land, parked: () => H.parked };
}
const takes = (w: World) => w.calls.filter((c) => c === "applyMeasure").length;
const attemptAfterTake = (w: World) => { const t = w.calls.indexOf("applyMeasure"), a = w.calls.findIndex((c) => Array.isArray(c)); return t >= 0 && a >= 0 && t < a; };
// the reader's saved place in these worlds: 2350 in a 3000 px view under a 2000 px spacer, a 600 px viewport: the row under the
// viewport top is r3 (2300..2400), 50 px above it
const R3_OFFSET = -50;

test("the nothing-armed re-show of a scrolled-up view (land-saved): no take, the spacers sized as they were, the raw write at the saved place", () => {
  const w = world({ saved: 2350 });
  w.land(w.content, w.v);
  assert.equal(takes(w), 0, "nothing armed: the land takes nothing (a spacer written here would move the saved place)");
  assert.deepEqual(w.calls.filter((c) => typeof c === "string"), ["sizeSpacers", "untakeMeasure"], "the spacers take the figures the view holds; the fallback's untake finds nothing taken; nothing else runs");
  assert.equal(w.spacer.h, 2000, "the parked figure stays parked for the next anchoring paint"); assert.equal(w.parked(), true);
  assert.deepEqual(w.writes, [{ writer: "land-saved", top: 2350, stick: false, from: undefined }], "the saved scrollTop is exact in a layout nothing re-sized: the raw write");
  assert.equal(w.rows[3].getBoundingClientRect().top, R3_OFFSET, "the row the saved place held is where it was");
  assert.equal(w.v.shown, true);
});

test("an armed anchor that MISSES on a re-show: the take before the attempt, then the row the saved place held is put back at its offset over the re-sized spacer (anchor-restore), never the raw pre-resize scrollTop", () => {
  // a card's anchor nowhere in the transcript (scrollToAnchor false: pointer-not-rendered), a figure parked, the scroller at the saved place
  const w = world({ saved: 2350 }, { anchor: "11111111-2222-4333-8444-000000000001", land: false });
  w.land(w.content, w.v);
  assert.equal(takes(w), 1, "an armed land takes, whatever its outcome (the take is decided before the attempt)");
  assert.ok(attemptAfterTake(w), "…and before the landing attempt, which reads live rects");
  assert.deepEqual(w.calls.filter((c) => Array.isArray(c)), [["scrollToAnchor", "11111111-2222-4333-8444-000000000001"]], "one attempt");
  assert.equal(w.spacer.h, 2000 + D, "the head spacer grew by the taken figure's delta");
  assert.deepEqual(w.writes, [{ writer: "anchor-restore", top: 2350 + D, stick: false, from: undefined }],
    "the fallback restores the row the saved place held (r3) at its offset, 300 px further down the document; the raw land-saved write at 2350 would leave the reader 300 px above their place");
  assert.equal(w.rows[3].getBoundingClientRect().top, R3_OFFSET, "r3 is where the saved place had it (with the raw write it would sit at +250, moved by the spacer's delta)");
  assert.equal(w.rows_.length, 1, "the miss files its locate row"); assert.equal(w.rows_[0].ok, false);
  assert.deepEqual(w.toasts, ["couldn't locate this in the transcript"], "…and says so: the road stays the error road it was");
});

test("the same miss on a tab SWITCH: the scroller still holds the leaving tab's position, so the row is captured at the SAVED place, not under the viewport as it stands, and put back there", () => {
  // the leaving tab was at its top (scrollTop 0); the entering view's saved place is 2350. A capture at the scroller's own position would
  // hold r0 (the first row, 2000 px below a viewport at 0) and put the reader at r0, a place they never were
  const w = world({ saved: 2350, scrollTop: 0 }, { anchor: "11111111-2222-4333-8444-000000000001", land: false });
  w.land(w.content, w.v);
  assert.equal(takes(w), 1);
  assert.equal(w.spacer.h, 2000 + D);
  assert.deepEqual(w.writes, [{ writer: "anchor-restore", top: 2350 + D, stick: false, from: undefined }], "r3, the row at the saved place, back at its offset");
  assert.equal(w.rows[3].getBoundingClientRect().top, R3_OFFSET);
});

// The saved place on a view ALREADY ON SCREEN (the landing lab's road 10, red in CI on two PRs once PR 861 landed). The view's record
// `v.scrollTop` follows the reader through the #content scroll listener (followReader), so it lags the scroller by one frame after any page
// write that does not sync it: the re-window's (virtualizeToViewport), whose scroll event runs a frame later. A deep link on the displayed tab
// inside that frame captured the saved place's row at the stale record, and when its land missed (a fetch armed) put that row back: the
// anchor restore wrote the reader to where they stood a frame earlier (the lab's record: the scroller 8, the record 0, the restore 8 -> 0).
// When the view was already on screen and no deferred build came between (showActive's `scrollerHolds`), the scroller holds the reader
// and landActive reads the saved place from it; a switch keeps the record, because the scroller still holds the leaving tab (the switch
// road above, and the contrast at the end of the second road below). A miss with a fetch armed now puts nothing back (the roads after these:
// the pre-jump stands, and with no pre-jump the saved place is written raw), so the scroller's read reaches the fetch-armed miss through the
// raw write's value and a miss with no fetch armed through the row the restore puts back; the second road runs both. The worlds: a 2000 px
// head spacer standing for the head gap (no child there carries a uuid, so the row captured is the first below it, as in the lab), the
// scroller at 8 where the re-window wrote it, the record still at 0, nothing parked (the lab's missed land took nothing: its restore wrote
// the row's own y back)
const STALE: Opts = { saved: 0, scrollTop: 8, parked: false };
const LINK = "11111111-2222-4333-8444-000000000021";
const LINK_SEEK = { sid: "A", uuid: LINK, kind: "user" };   // setActive arms the durable seek for the link it lands (armSeek): a miss keeps searching, no toast

test("a deep link WITH a time on the view already on screen, run inside the frame between a page write and its scroll event: the pre-jump writes where the scroller already stands and syncs the record, the land misses with its window's fetch armed, and the reader stays where the scroller held them; no anchor restore writes them back to the record's stale place", () => {
  const w = world(STALE, { anchor: LINK, t: 1700000000, seek: LINK_SEEK, land: false, preJump: 8, fetch: true });
  const r0Before = w.rows[0].getBoundingClientRect().top;   // 1992: the first row under the head gap, as the reader sees it
  w.land(w.content, w.v, true);
  assert.equal(w.content.scrollTop, 8, "the reader is where the scroller held them (at the base the anchor restore put them at the record's 0, the row captured there written back to its y there): " + JSON.stringify(w.writes));
  assert.deepEqual(w.writes.filter((x) => x.top !== 8), [], "no write moves the reader off the scroller's place: the pre-jump writes 8, and what follows it writes 8 too: " + JSON.stringify(w.writes));
  assert.equal(w.rows[0].getBoundingClientRect().top, r0Before, "the row under the head gap sits where the reader saw it");
  assert.deepEqual(w.toasts, [], "the seek keeps searching; the miss raises no toast"); assert.ok(w.calls.includes("showSeekNote"));
});

test("a deep link WITHOUT a time on the view already on screen, inside the same frame: no pre-jump; its land misses with no fetch armed (the row captured at the saved place is put back) or with one (the saved place is written raw), and either way the reader stays where the scroller held them; nothing writes them back to the record's stale place", () => {
  for (const fetch of [false, true]) {
    const road = fetch ? "a fetch armed" : "no fetch armed";
    const w = world(STALE, { anchor: LINK, seek: LINK_SEEK, land: false, fetch });
    const r0Before = w.rows[0].getBoundingClientRect().top;
    w.land(w.content, w.v, true);
    assert.equal(w.content.scrollTop, 8, road + ": the reader is where the scroller held them (at the base the anchor restore wrote 0): " + JSON.stringify(w.writes));
    assert.deepEqual(w.writes.filter((x) => x.top !== 8), [], road + ": no write moves the reader off the scroller's place: " + JSON.stringify(w.writes));
    assert.equal(w.rows[0].getBoundingClientRect().top, r0Before, road + ": the row under the head gap sits where the reader saw it");
    // the contrast: the same world on a SWITCH (the scroller does not hold this view's reader, so the flag is false) reads the record, the
    // saved place: the row it held is put back at its offset, or, with a fetch armed, the saved place is written raw
    const sw = world(STALE, { anchor: LINK, seek: LINK_SEEK, land: false, fetch });
    sw.land(sw.content, sw.v, false);
    assert.deepEqual(sw.writes.map((x) => [x.writer, x.top]), [[fetch ? "land-saved" : "anchor-restore", 0]], road + ": on a switch the record is the saved place");
  }
});

test("the raw land-saved write on a missed land with no row at the saved place, on the view already on screen inside the same frame: the saved scrollTop written is the scroller's, not the lagging record's (this read predates PR 861); a pre-jump in the same pass still stands, because the write reads the record after the attempt synced it", () => {
  // rows 0..1000 then a 5000 px bottom spacer; the scroller at 3008 and the record a frame behind at 3000: no row at or below the viewport top
  const o: Opts = { spacerH: 0, saved: 3000, scrollTop: 3008, bottomSpacerH: 5000, parked: false };
  const w = world(o, { anchor: LINK, seek: LINK_SEEK, land: false });
  w.land(w.content, w.v, true);
  assert.equal(w.content.scrollTop, 3008, "the reader is where the scroller held them (at the base the raw write put them at the record's 3000): " + JSON.stringify(w.writes));
  assert.deepEqual(w.writes, [{ writer: "land-saved", top: 3008, stick: false, from: undefined }], "no row to put back: the raw write, of the scroller's place");
  // a pre-jump in the same pass (a link with a time) placed the reader, and the record was synced to it: the raw write keeps it (a write
  // of the place read before the attempt would reverse the pre-jump on this road, where it stands today and stood before PR 861)
  const j = world(o, { anchor: LINK, t: 1700000000, seek: LINK_SEEK, land: false, preJump: 4000, fetch: true });
  j.land(j.content, j.v, true);
  assert.deepEqual(j.writes.map((x) => [x.writer, x.top]), [["land-guess", 4000], ["land-saved", 4000]], "the pre-jump stands on the raw road");
  assert.equal(j.content.scrollTop, 4000);
});

// A DEEP PRE-JUMP STANDS THROUGH ITS ARMED FETCH (the second behaviour PR 861 changed on these lines). A deep link with a time into history the
// page does not hold asks for a window, and the pre-jump (preJumpIntoGap) moves the reader into the gap where the target will be, the loading
// glyph in the empty space; the land then misses, because the target comes with the reply. Before PR 861 the fallback wrote the saved place the
// pre-jump had just synced, which moved nothing. PR 861's fallback put back the row captured before the attempt, which returned the reader to
// where they started in the same pass, and the reply's landing then moved them forward again. With a fetch armed the miss is not final (the
// reply lands the anchor, or its dead end puts back the origin the pre-jump recorded, chatWindow), so nothing is put back; the pre-jump read
// the gap after the take, so the take stands under it. The restore still serves a miss with no fetch armed (the roads above). The worlds: a
// reader scrolled up at 2350 (r3 50 px above the viewport top), not following the tail, a figure parked (the take grows the head spacer,
// which stands for the head gap, by D), on the view already on screen
const DEEP = "11111111-2222-4333-8444-000000000031";
const DEEP_SEEK = { sid: "A", uuid: DEEP, kind: "user" };

test("a deep link with a time whose pre-jump moves a reader who is not following the tail deep into the gap: the land misses with its fetch armed and the pre-jump stands, with no anchor restore writing the reader back to the row captured before the attempt and the take kept under the placement measured over it; when the fetch lands the land completes at the target, and the reader never went back in between", () => {
  const arm: Arm = { anchor: DEEP, t: 1700000000, seek: DEEP_SEEK, land: false, fetch: true, preJump: 1000 };
  const w = world({ saved: 2350 }, arm);
  w.land(w.content, w.v, true);
  assert.equal(w.content.scrollTop, 1000, "the reader is where the pre-jump put them, in the gap (at the base the anchor restore wrote them back to r3 at its offset, 2650 over the take): " + JSON.stringify(w.writes));
  assert.deepEqual(w.writes.filter((x) => x.writer === "anchor-restore"), [], "with the fetch armed nothing is put back: " + JSON.stringify(w.writes));
  assert.deepEqual(w.writes.slice(1).filter((x) => x.top !== 1000), [], "nothing after the pre-jump writes anywhere else: " + JSON.stringify(w.writes));
  assert.equal(takes(w), 1, "the armed land took before its attempt");
  assert.equal(w.spacer.h, 2000 + D, "the take stands under the placement: the pre-jump read the gap after it, and giving it back would re-size the gap under the reader just placed");
  assert.equal(w.parked(), false);
  assert.deepEqual(w.toasts, [], "the seek keeps searching; the miss raises no toast");
  // the reply: the window arrives and the landing re-arms on its anchor (chatWindow, then showActive; here the durable seek re-arms it) and lands
  arm.land = true; arm.landAt = 1200; delete arm.preJump; arm.fetch = false;
  w.land(w.content, w.v, true);
  assert.equal(w.content.scrollTop, 1200, "the land completes at the target: " + JSON.stringify(w.writes));
  const visited = w.writes.map((x) => x.top).filter((top, i, a) => i === 0 || top !== a[i - 1]);
  assert.deepEqual(visited, [1000, 1200], "the reader went from the pre-jump's place to the target, never back to where they started and forward again: " + JSON.stringify(w.writes));
  // the same link with NO time: no pre-jump placed the reader, and the restore applies only to a miss with no fetch armed, so the saved place
  // is written raw, in the layout it was saved in (the take given back), and the reader stays where they were
  const n = world({ saved: 2350 }, { anchor: DEEP, seek: DEEP_SEEK, land: false, fetch: true });
  n.land(n.content, n.v, true);
  assert.equal(n.rows[3].getBoundingClientRect().top, R3_OFFSET, "no pre-jump: the reader stays where they were, r3 50 px above the viewport top");
  assert.deepEqual(n.writes, [{ writer: "land-saved", top: 2350, stick: false, from: undefined }], "no anchor restore with a fetch armed: the raw write of the saved place");
  assert.equal(n.spacer.h, 2000, "…in the layout it was measured in, the take given back (with the take standing, the raw write would leave the reader 300 px above their place)");
  assert.equal(n.parked(), true);
  // a pass that makes no attempt by id (a moment that misses) finds the two flags as an earlier attempt left them, its fetch still on the wire:
  // they are not this pass's, so its miss is the ordinary one, the row the saved place held put back over the take
  const m = world({ saved: 2350 }, { t: 1700000000, landT: false, stale: true });
  m.land(m.content, m.v, true);
  assert.equal(m.rows[3].getBoundingClientRect().top, R3_OFFSET, "the moment's miss keeps the reader where they were (read as this pass's, the earlier pre-jump's mark would skip the take's give-back under the raw write, 300 px off): " + JSON.stringify(m.writes));
  assert.deepEqual(m.writes, [{ writer: "anchor-restore", top: 2350 + D, stick: false, from: undefined }], "the ordinary miss: the row put back over the take");
});

test("render.ts: the two marks the fallback reads describe this attempt: scrollToAnchor clears both before anything else, the pre-jump (reached only through scrollToAnchor's window ask) marks the jump right after its write and the record's sync, and landActive reads them straight after its attempt by id, never on a pass that made none. A source pin on where the marks are set and read, which the harness above stubs; the road above executes what landActive does with them, and the landing lab's roads 10 and 16 run the pre-jump in the browser", () => {
  assert.match(RENDER, /function scrollToAnchor\(uuid: string\): boolean \{\n\s*anchorPendingOlder = false;[^\n]*\n\s*anchorPreJumped = false;/, "scrollToAnchor clears both marks on entry, so what they say is this attempt's");
  assert.equal((RENDER.match(/\brequestAround\(/g) || []).length, 2, "requestAround is declared once and called once, inside scrollToAnchor");
  assert.equal((RENDER.match(/\bpreJumpIntoGap\(/g) || []).length, 2, "preJumpIntoGap is declared once and called once, inside requestAround: the pre-jump runs only inside an attempt, after its marks were cleared");
  const pj = RENDER.match(/^function preJumpIntoGap\([\s\S]*?\n\}/m);
  assert.ok(pj, "preJumpIntoGap");
  assert.match(pj![0], /writeScroll\(content, y, "land-guess"\);\n\s*v\.scrollTop = content\.scrollTop;\n\s*anchorPreJumped = true;/, "the pre-jump marks the jump right after it writes the reader's place and syncs the record, on the one road that places the reader");
  assert.equal((RENDER.match(/anchorPreJumped = true;/g) || []).length, 1, "nothing else marks a pre-jump");
  const land = RENDER.slice(RENDER.indexOf("function landActive("), RENDER.indexOf("\n}\n", RENDER.indexOf("function landActive(")));
  assert.match(land, /let scrolled = pendingAnchor \? scrollToAnchor\(pendingAnchor\) : false;\n(?:\s*\/\/[^\n]*\n)*\s*const fetchArmed = !!att\.anchor && anchorPendingOlder, preJumped = fetchArmed && anchorPreJumped;/, "landActive reads both marks straight after its attempt, and only when the attempt was by id (a moment's pass finds them as an earlier attempt left them)");
});

test("render.ts: showActive decides whether the scroller holds the view's reader BEFORE the display flip (a switch's entering view is still display:none then) and hands the decision to the synchronous land alone; the deferred build's land and the hidden pane's retry pass nothing. A source pin, keyed on where the decision is read and what each land is handed. Executed: the landing lab's road 16 (tests/test_landing_notice_browser.py) runs the hand-off, a deep link on the displayed tab reaching landActive through showActive with every conjunct true, and the roads above run what the flag changes inside landActive. No executed road reaches five parts, which this pin alone guards: the display conjunct (a switch; the decision read after the flip drops it), the pane-height conjunct, the pending-build conjunct, the deferred land passing nothing and the hidden pane's retry passing nothing", () => {
  const m = RENDER.match(/^function showActive\(keep\?: \{ uuid: string; y: number \} \| null\) \{([\s\S]*?)\n\}/m);
  assert.ok(m, "showActive");
  const body = m![1];
  const decl = body.indexOf('const scrollerHolds = v.el.style.display !== "none" && content.clientHeight > 0 && pendingBuildRaf == null;');
  const flip = body.indexOf('for (const [vid, vv] of views) vv.el.style.display = vid === activeId ? "" : "none";');
  assert.ok(decl >= 0 && flip > decl, "the decision reads the view's display, the pane's height and the pending build before the loop that shows the entering view");
  assert.equal((body.match(/landActive\(/g) || []).length, 2, "showActive lands on two paths");
  assert.match(body, /syncView\(activeId!\); landActive\(content, v, scrollerHolds\);/, "the synchronous land is handed the decision");
  assert.match(body, /syncView\(target\);[^\n]*\n\s*landActive\(cc, vv\);/, "the deferred land passes nothing: while a build is pending the scroller can hold the reveal's clamp, which the record never took");
  assert.match(RENDER, /if \(c && vv\) landActive\(c, vv\); \}\);/, "the hidden pane's retry passes nothing");
});

test("an armed miss with no row at the saved place (the saved place inside a spacer): the take, then, with no row to put back, the take undone and the raw land-saved write exact in the layout the saved place was measured in (the maintainer's round 3 ruling B: until then the take stood and the raw write moved the reader by its delta, disclosed)", () => {
  // rows 0..1000 then a 5000 px bottom spacer; the saved place at 3000 has no row at or below the viewport top
  const w = world({ spacerH: 0, saved: 3000, bottomSpacerH: 5000 }, { anchor: "11111111-2222-4333-8444-000000000002", land: false });
  w.land(w.content, w.v);
  assert.equal(takes(w), 1, "the take is on the arm, not the row");
  assert.equal(w.spacer.h, 0, "the head spacer is back where the saved scrollTop was measured (at the head the maintainer's round 3 ruled on it stood 300 px taller under the raw write: the property, asserted before the mechanism so the red-before is on it)");
  assert.deepEqual(w.calls.filter((c) => typeof c === "string"), ["applyMeasure", "redrawGapUnits", "sizeSpacers", "untakeMeasure"], "the take before the attempt, then, with no row to put back, the untake before the raw write");
  assert.equal(w.parked(), true, "the figures are parked again for the next paint that anchors");
  assert.deepEqual(w.writes, [{ writer: "land-saved", top: 3000, stick: false, from: undefined }], "nothing to put back: the raw write, exact in the layout it was saved in");
});

test("the reload restore with no anchor row (the reader's place inside a spacer when the page went down): the take stands and the persisted scrollTop is written raw over it, the one raw write after a take that keeps the take, because that scrollTop was measured on the page before the reload, whose figures the take re-derives (both refuters' probes on the round-3 filing: a capture-then-restore here would displace the reader by the take's delta)", () => {
  const r = world({ saved: 2350, scrollTop: 0 }, { reload: { id: "A", top: 2350, stick: false, anchor: null } });
  r.land(r.content, r.v);
  assert.equal(takes(r), 1, "a record is armed: the land takes before the restore");
  assert.ok(!r.calls.includes("untakeMeasure"), "…and gives nothing back: the persisted figure was measured against the figures the take re-derives");
  assert.equal(r.spacer.h, 2000 + D, "the take stands");
  assert.deepEqual(r.writes, [{ writer: "reload-restore", top: 2350, stick: false, from: undefined }], "the persisted top, raw, over the re-derived figures (the first guess; a record with an anchor row arms the deep-link land after it)");
  assert.equal(r.v.stick, false); assert.equal(r.parked(), false);
});

test("the reload restore's raw write, the ordering its exception rests on: the take, then the record bound for the restore (the window's start, wider than the window ruled, which runs from the site's own read of rs.top to the write, so strictly stronger; the persisted top's first read is earlier, in landActive's saved computation, where takeReloadScroll admits the record to decide the take), then the site's read of that record's top, then the write, with nothing between the binding and the write but that read, on both raw shapes (no anchor row; an anchor row the fresh window lacks), in a view that holds a gap row and a bottom spacer beside the head spacer and the rows, so production's gap redraw and either spacer's resize have geometry to move. The window is anchored on the IDENTITY of the binding whose value is written: the read that precedes the write names its call and the window runs from that call's record (the maintainer's round 4 ruling, ordering-2), and the road's admissions of the record are COUNTED, exactly two (the saved computation's, which decides the take, and the binding's), the write reading the second, so a later call that admits the record again reds on the count, whether it is bound to a second variable or rebinds the site's own record (the closing lens over the author's fixer pass over pass 5: until then the window followed the record whose top the write read, so a site that re-admitted the record into its own binding after a take or a geometry change moved the window's start past the change, both halves green). The site needs no take-back because its value was measured in the state it lands in, the pre-reload page's layout that the take before it re-derives, not because the site is special: a change in that window would land the value in a layout it was not measured in, so this pin reds the moment the window opens, on a take-class event, on a geometry event (a height written on a row or the view element, a child inserted or removed: the model records them and fails closed on what it cannot represent, closure-6 of the same ruling), on another record, and on the geometry at the write differing from the geometry at the binding (the reviewer's answer to the author's tail-2 question, 2026-09-21; spacer-measure.test.ts checks the window on the tree)", () => {
  for (const reload of [{ id: "A", top: 2350, stick: false, anchor: null }, { id: "A", top: 2350, stick: false, anchor: { uuid: "11111111-2222-4333-8444-000000000007", y: -50 } }]) {
    const shape = reload.anchor ? "an anchor row the fresh window lacks" : "no anchor row";
    // a view with every kind of child production's spacer code draws on (a head spacer, rows, a gap row, a bottom spacer), so a redraw of
    // any of them planted in the window moves geometry the model records
    const r = world({ saved: 2350, scrollTop: 0, gap: true, bottomSpacerH: 500 }, { reload, land: false });
    r.land(r.content, r.v);
    const write = r.trace.indexOf("write reload-restore");
    assert.ok(write >= 0, shape + ": the raw write ran: " + JSON.stringify(r.trace));
    // the record is admitted twice: once to decide the take (before it: nothing armed but the record) and once for the restore, and both
    // calls return the same persisted object, so the binding whose value is written is named by its CALL: the last read of a record's top
    // before the write is the site's, and its serial is the binding's. The window follows that call's record, so the road's admissions are
    // COUNTED first, exactly two with the write reading the second: a site that admits the record again after a take or a geometry change
    // and rebinds its value to the later record (the executed verifier's E4 after the maintainer's round 4 ruling, with a second variable; the
    // closing lens over the author's fixer pass over pass 5, with `rs` itself rebound, `const` made `let`) would move the window's start past
    // the change, and the count reds it instead of the window emptying; spacer-measure.test.ts pins the same shape on the tree (`rs` a const
    // bound once, assigned nowhere in landActive, takeReloadScroll called twice there)
    const readEv = r.trace.slice(0, write).reverse().find((e) => e.startsWith("read rs.top#"));
    assert.ok(readEv, shape + ": the write's value was read from a record's top: " + JSON.stringify(r.trace));
    assert.deepEqual(r.trace.filter((e) => e.startsWith("record#")), ["record#1", "record#2"], shape + ": the record is admitted exactly twice on this road, once to decide the take and once for the binding whose top the write reads; a third admission is a site that admits the record again after the binding, and a window that followed its record would start past whatever ran before it: " + JSON.stringify(r.trace));
    assert.equal(readEv, "read rs.top#2", shape + ": the write reads the second admission's record, the binding's, not the saved computation's: " + JSON.stringify(r.trace));
    const recordEv = "record#" + readEv!.slice("read rs.top#".length);
    const take = r.trace.indexOf("take"), record = r.trace.indexOf(recordEv), read = r.trace.indexOf(readEv!);
    assert.ok(take >= 0 && record > take, shape + ": the take runs before the record is bound for the restore (the take stands, by measurement): " + JSON.stringify(r.trace));
    assert.ok(read > record && write > read, shape + ": the site reads its record's top after the binding, and writes after the read: " + JSON.stringify(r.trace));
    assert.deepEqual(r.trace.slice(record + 1, write).filter((e) => e !== readEv), [], shape + ": from the record's binding to its write the trace holds the site's read of that record's top and nothing else: no take-class event (a take, an untake, a spacer redraw, a write of the parked flag or of the view's take state), no geometry event (a height written on a row or the view element, a child inserted or removed), no other record; a change here would land the persisted top in a layout it was not measured in, and the site would owe a take-back like every other (the window follows the record whose top the write reads, and the admissions are counted above, so a site rebound to a later record reds on the count instead of moving the window's start): " + JSON.stringify(r.trace));
    assert.deepEqual(r.geometryAt["write reload-restore"], r.geometryAt[recordEv], shape + ": the geometry the write lands in is the geometry at the binding, every child by class and height");
    assert.deepEqual(r.writes.map((x) => x.writer), ["reload-restore"], shape + ": the raw write is the land's one write");
    assert.ok(!r.trace.some((e) => /^(measured|avgTurnH|pxPerTurn)=/.test(e)), shape + ": the view's own take state (any of its three fields) is written by nothing on this road: " + JSON.stringify(r.trace));
  }
});

test("the model refuses a write of the `style` OBJECT itself on a row, on the head spacer and on the view element, not only of its keys: the instrumented style is installed non-writable, so the set trap's throw fires, and a replaced style cannot disable the height routing in silence for every later write; a DEFINE of the object (Object.defineProperty, Object.defineProperties, Reflect.defineProperty), which reaches the defineProperty trap and not the set trap, is refused the same way; a define of a KEY on the style object itself (`height` or another) is refused by the style proxy's own defineProperty trap; the members still route (the maintainer's round 5 ruling, extra8-3: closure-6's second named witness was still green; the define door is the author's fixer pass over the pass after that round, its verifier (a); the style's own define door is the closing lens over that fixer pass, CL-4)", () => {
  // until this pass `style` was an own writable data property on Node and Host, so `row.style = {...}` and `v.el.style = {...}` passed the set
  // trap through Reflect.set and the model's height routing went to a plain object: a silent no-op inside the ordering window, the shape the
  // model exists to refuse (the members were refused, the object was not)
  const w = world({ saved: 2350, scrollTop: 0, gap: true, bottomSpacerH: 500 });
  const before = w.trace.length;
  assert.throws(() => { (w.rows[0] as any).style = { height: "1px" }; }, /<turn>\.style written as .*read-only in the model as in the DOM/, "a row's style object cannot be replaced");
  assert.throws(() => { (w.spacer as any).style = { height: "3px" }; }, /<tx-spacer tx-spacer-top>\.style written as .*read-only in the model/, "the head spacer's neither");
  assert.throws(() => { (w.host as any).style = {}; }, /v\.el\.style written as .*read-only in the model/, "nor the view element's");
  assert.throws(() => { Reflect.set(w.rows[1] as any, "style", {}); }, /read-only in the model/, "…through Reflect.set too (the trap throws where the DOM would ignore the write)");
  // the DEFINE door (the author's fixer pass over the pass after the maintainer's round 5, its verifier (a)): Object.defineProperty and
  // Reflect.defineProperty reach a proxy's defineProperty trap, never its set trap, and the style is configurable (hideEdges redefines it
  // before the wrap), so with no such trap a redefinition replaced the instrumented style in silence, Reflect's returned true, and every
  // later height write was the silent no-op this cell exists to refuse; the DOM's element takes an own property there too. The trap throws
  // for every key, as the view record's does (Object.defineProperty, Object.defineProperties, Reflect.defineProperty)
  assert.throws(() => { Object.defineProperty(w.rows[0], "style", { value: {}, writable: true, configurable: true }); }, /<turn>\.style defined: the model has nothing to define/, "a row's style object cannot be redefined");
  assert.throws(() => { Reflect.defineProperty(w.host, "style", { value: {}, configurable: true }); }, /v\.el\.style defined: the model has nothing to define/, "nor the view element's, through Reflect.defineProperty, which returns true where the DOM's element takes an own property");
  assert.throws(() => { Object.defineProperties(w.spacer, { style: { value: {} } }); }, /<tx-spacer tx-spacer-top>\.style defined/, "nor the head spacer's, through Object.defineProperties");
  assert.throws(() => { Object.defineProperty(w.rows[1], "h", { value: 1 }); }, /<turn>\.h defined: the model has nothing to define/, "…and no other key either: a define is not a write the model represents, whatever the key");
  // the style object's OWN keys (the closing lens over the author's fixer pass over the pass after the maintainer's round 5, CL-4): the
  // style proxy refused a read, a write and a delete of every key but `height` and had no defineProperty trap, so a define of `height` on
  // the style itself threw nothing, returned the proxy and landed an own property on the proxy's target, which the traps never read (the
  // model's read and a later write still routed), where a DOM element's style takes the own property over its accessor and every later
  // height write is a silent no-op; the trap refuses every key, `height` included, as failClosed's does
  assert.throws(() => { Object.defineProperty(w.rows[0].style, "height", { value: "1px", writable: true, configurable: true }); }, /<turn>\.style\.height defined: the model carries a height and nothing else/, "a define of `height` on a row's style object is refused");
  assert.throws(() => { Reflect.defineProperty(w.host.style, "height", { value: "1px", configurable: true }); }, /v\.el\.style\.height defined/, "…and on the view element's, through Reflect.defineProperty, which returned true where the DOM's style takes an own property");
  assert.throws(() => { Object.defineProperties(w.spacer.style, { color: { value: "red" } }); }, /<tx-spacer tx-spacer-top>\.style\.color defined/, "…and of any other key, through Object.defineProperties");
  assert.equal(Object.getOwnPropertyDescriptor(w.rows[0].style, "height"), undefined, "no own property landed on the style: its target is untouched");
  assert.equal(w.rows[0].h, 100, "the row's height is untouched"); assert.equal(w.rows[1].h, 100, "the other row's too"); assert.equal(w.trace.length, before, "nothing traced: no write landed");
  w.rows[0].style.height = "120px";
  assert.equal(w.rows[0].h, 120, "a height written through the instrumented style still routes into the model");
  assert.deepEqual(w.trace.slice(before), ["style turn height=120 (was 100)"], "…and is traced");
  assert.throws(() => { (w.rows[0].style as any).color = "red"; }, /the model carries a height and nothing else/, "…and every other key is refused as before");
});

test("an armed miss whose attempt REBUILT the window around the anchor's unit (scrollToAnchor's pointer-not-rendered and pointer-wrong-kind roads): the captured row left with the old rows, so the restore misses, the take is undone and the raw land-saved write of the saved scrollTop lands in the layout it was saved in, the third of the raw write's roads; a rebuild that renders the saved place's row again under its uuid is restored over the take", () => {
  // the build removes every child and renders the units around the anchor's: rows 20..29 stand where 0..9 stood, and r3 is gone
  const gone = (host: Host) => { host.replaceChildren(host.children[0]); for (let i = 20; i < 30; i++) host.add(new Node(100, "turn", "r" + i)); };
  const w = world({ saved: 2350 }, { anchor: "11111111-2222-4333-8444-000000000006", land: false, rebuild: gone });
  w.land(w.content, w.v);
  assert.equal(takes(w), 1, "the take is on the arm");
  assert.ok(attemptAfterTake(w));
  assert.equal(w.spacer.h, 2000, "the take undone: the head spacer back where the saved scrollTop was measured (at the head it stood 300 px taller under the raw write, the reader 300 px off in the rebuilt window)");
  assert.equal(w.parked(), true, "the figures wait for a paint that anchors");
  assert.deepEqual(w.writes, [{ writer: "land-saved", top: 2350, stick: false, from: undefined }],
    "no row of the captured DOM is left to put back: the raw write at the saved place, in the layout it was saved in; the reader is in the window built around the anchor (the residual the body names, narrowed to that)");
  assert.deepEqual(w.toasts, ["couldn't locate this in the transcript"], "the error road it was");
  // the same rebuild rendering the saved place's row again (a fresh node, the same uuid): the restore finds it, so the rule is the
  // restore's answer, not whether a rebuild ran
  const again = (host: Host) => { host.replaceChildren(host.children[0]); for (let i = 0; i < 10; i++) host.add(new Node(100, "turn", "r" + i)); };
  const w2 = world({ saved: 2350 }, { anchor: "11111111-2222-4333-8444-000000000006", land: false, rebuild: again });
  w2.land(w2.content, w2.v);
  assert.equal(takes(w2), 1);
  assert.deepEqual(w2.writes, [{ writer: "anchor-restore", top: 2350 + D, stick: false, from: undefined }], "the rebuilt r3 is put back at its offset over the re-sized spacer");
  assert.equal(w2.host.children[4].getBoundingClientRect().top, R3_OFFSET, "the new r3 sits where the saved place had the old one");
  assert.equal(w2.spacer.h, 2000 + D, "the take stands: the row was put back over it"); assert.equal(w2.parked(), false);
});

test("the anchoring roads each take once, before the attempt, and landActive writes nothing of its own when the landing placed the reader: an anchor that hits, a moment, a seek; the reload restore and the bottom land take and write their own", () => {
  const anchor = "11111111-2222-4333-8444-000000000003";
  // an anchor that hits: scrollToAnchor placed the reader (landOn's write, inside the stub); a keep-offset re-land (pendingAnchorKeepY) the same
  for (const arm of [{ anchor, land: true }, { anchor, keepY: -50, land: true }] as Arm[]) {
    const w = world({ saved: 2350 }, arm);
    w.land(w.content, w.v);
    assert.equal(takes(w), 1, "one take: " + JSON.stringify(arm)); assert.ok(attemptAfterTake(w), "before the attempt: " + JSON.stringify(arm));
    assert.deepEqual(w.writes, [], "the landing's own write placed the reader; no fallback: " + JSON.stringify(arm));
    assert.equal(w.toasts.length, 0); assert.equal(w.rows_[0].ok, true);
  }
  // a moment (time-only navigation): no anchor, landNearestMoment lands
  const m = world({ saved: 2350 }, { t: 1700000000, landT: true });
  m.land(m.content, m.v);
  assert.equal(takes(m), 1); assert.ok(attemptAfterTake(m));
  assert.deepEqual(m.calls.filter((c) => Array.isArray(c)), [["landNearestMoment", 1700000000]], "the moment's land, no anchor attempt");
  assert.deepEqual(m.writes, []);
  // a durable seek for this tab re-arms the attempt from its uuid; a hit clears the seek
  const s = world({ saved: 2350 }, { seek: { sid: "A", uuid: "11111111-2222-4333-8444-000000000004", kind: "user" }, land: true });
  s.land(s.content, s.v);
  assert.equal(takes(s), 1); assert.ok(attemptAfterTake(s));
  assert.deepEqual(s.calls.filter((c) => Array.isArray(c)), [["scrollToAnchor", "11111111-2222-4333-8444-000000000004"]], "the seek's uuid is the attempt");
  assert.ok(s.calls.includes("clearSeek"), "the landing event ends the seek"); assert.deepEqual(s.writes, []);
  // …and a seek that misses this pass keeps searching (no toast) and puts the saved place's row back over the take
  const s2 = world({ saved: 2350 }, { seek: { sid: "A", uuid: "11111111-2222-4333-8444-000000000004", kind: "user" }, land: false });
  s2.land(s2.content, s2.v);
  assert.equal(takes(s2), 1); assert.ok(s2.calls.includes("showSeekNote")); assert.deepEqual(s2.toasts, []);
  assert.deepEqual(s2.writes, [{ writer: "anchor-restore", top: 2350 + D, stick: false, from: undefined }]);
  // the reload restore, a follow-mode reader: the bottom, after the take
  const r = world({ saved: 2350 }, { reload: { id: "A", top: 2350, stick: true, anchor: null } });
  r.land(r.content, r.v);
  assert.equal(takes(r), 1);
  assert.deepEqual(r.writes.map((x) => [x.writer, x.stick]), [["reload-restore", true]], "the follow-mode reader lands at the bottom"); assert.equal(r.v.stick, true);
  // the reload restore with an anchor row the rebuilt DOM holds: the reload's own anchor restore, after the take
  const r2 = world({ saved: 2350, scrollTop: 0 }, { reload: { id: "A", top: 2350, stick: false, anchor: { uuid: "r3", y: -50 } } });
  r2.land(r2.content, r2.v);
  assert.equal(takes(r2), 1);
  assert.deepEqual(r2.writes, [{ writer: "anchor-restore", top: 2350 + D, stick: false, from: undefined }], "the reload's anchor row at its offset over the re-sized spacer");
  // the bottom land: a view not yet shown, and a follow-mode view
  for (const o of [{ saved: 2350, shown: false }, { saved: 2350, stick: true }] as Opts[]) {
    const b = world(o);
    b.land(b.content, b.v);
    assert.equal(takes(b), 1, "the bottom land takes: " + JSON.stringify(o));
    assert.deepEqual(b.writes.map((x) => [x.writer, x.stick]), [["land-bottom", true]], "…and writes the bottom: " + JSON.stringify(o));
    assert.equal(b.v.shown, true);
  }
});

test("a hidden pane with a jump armed defers the whole land (nothing taken, nothing written) until the pane shows", () => {
  const w = world({ saved: 2350, clientHeight: 0 }, { anchor: "11111111-2222-4333-8444-000000000005", land: true });
  w.land(w.content, w.v);
  assert.equal(takes(w), 0, "no take in a zero-height view"); assert.deepEqual(w.writes, []); assert.deepEqual(w.calls, []);
});

// ── keepPlaceAcrossWindow: the take over its restores, and the double miss (the maintainer's round 2 ruling, tests-4 and correctness-3) ──────────────

type KeepArm = { land?: boolean; older?: boolean; rebuild?: (host: Host) => void };
type KeepWorld = { content: Content; host: Host; spacer: Node; rows: Node[]; writes: Write[]; calls: any[]; keep: (k: { uuid: string; y: number }) => boolean; state: () => { pendingAnchor: string | null; pendingAnchorKeepY: number | null; relandAsk: boolean }; parked: () => boolean };
/** The reader at `scrollTop` over the same view; `parked` a figure waiting; the stubbed scrollToAnchor answers `land`, marks an older fetch
 *  when `older`, and runs `rebuild` over the host first (the window rebuilt around the anchor's unit: rows leave). */
function keepWorld(scrollTop: number, arm: KeepArm = {}, parked = true): KeepWorld {
  const content = new Content(600, []); const host = new Host(content);
  const spacer = host.add(new Node(2000, "tx-spacer tx-spacer-top"));
  const rows: Node[] = []; for (let i = 0; i < 10; i++) rows.push(host.add(new Node(100, "turn", "r" + i)));
  content.scrollTop = scrollTop;
  const v: any = { el: host, scrollTop, shown: true, stick: false };
  const H: any = { content, v, spacer, writes: [] as Write[], calls: [] as any[], parked, delta: D, arm };
  const js = liftBetween("function keepPlaceAcrossWindow(", "// Scroll/anchor landing + deep-link diagnostics + restamp")
           + liftBetween("function captureScrollAnchor(", "// Live tail-append to the ACTIVE view");
  const prelude = `"use strict";
    const H = HOOKS;
    let pendingAnchor = null, pendingAnchorKeepY = null, relandAsk = false, anchorPendingOlder = false;
    const applyMeasure = (v) => { H.calls.push("applyMeasure"); if (!H.parked) return false; H.parked = false; H.spacer.h += H.delta; return true; };
    const figuresBefore = (v) => ({ parked: H.parked });
    const untakeMeasure = (v, fig) => { H.calls.push("untakeMeasure"); if (!fig.parked || H.parked) return false; H.parked = true; H.spacer.h -= H.delta; return true; };
    const redrawGapUnits = () => { H.calls.push("redrawGapUnits"); };
    const sizeSpacers = () => { H.calls.push("sizeSpacers"); };
    const scrollToAnchor = (uuid) => { H.calls.push(["scrollToAnchor", uuid, relandAsk, pendingAnchor, pendingAnchorKeepY]); if (H.arm.rebuild) H.arm.rebuild(H.content.host); if (H.arm.older) anchorPendingOlder = true; return !!H.arm.land; };
    const writeScroll = (c, top, writer, stick = false, from) => { H.writes.push({ writer, top, stick, from }); c.scrollTop = Math.max(0, Math.min(top, c.scrollHeight - c.clientHeight)); };
    const cssEscape = (s) => s;
  `;
  const api = new Function("HOOKS", prelude + js + "\nreturn { keep: (k) => keepPlaceAcrossWindow(H.content, H.v, k), state: () => ({ pendingAnchor, pendingAnchorKeepY, relandAsk }) };")(H);
  return { content, host, spacer, rows, writes: H.writes, calls: H.calls, keep: api.keep, state: api.state, parked: () => H.parked };
}
const keepTakes = (w: KeepWorld) => w.calls.filter((c) => c === "applyMeasure").length;

test("keepPlaceAcrossWindow, the direct restore: the take first (spacers and gap units re-sized), then the reader's row back at its offset over them; true, one write", () => {
  const w = keepWorld(2350);   // r3 under the viewport top, 50 px above it
  assert.equal(w.keep({ uuid: "r3", y: R3_OFFSET }), true);
  assert.equal(keepTakes(w), 1, "the land of the reader's own row takes");
  assert.deepEqual(w.calls.filter((c) => typeof c === "string"), ["applyMeasure", "redrawGapUnits", "sizeSpacers"], "the take, the gap units, the spacers, before any restore");
  assert.equal(w.spacer.h, 2000 + D);
  assert.deepEqual(w.writes, [{ writer: "anchor-restore", top: 2350 + D, stick: false, from: undefined }], "r3 at its offset, 300 px further down the document");
  assert.equal(w.rows[3].getBoundingClientRect().top, R3_OFFSET, "the row did not move on screen");
  assert.deepEqual(w.calls.filter((c) => Array.isArray(c)), [], "no deep-link attempt: the row was there");
  assert.equal(w.state().pendingAnchor, null);
  // nothing parked: no re-size, the row back where it is
  const w2 = keepWorld(2350, {}, false);
  assert.equal(w2.keep({ uuid: "r3", y: R3_OFFSET }), true);
  assert.equal(keepTakes(w2), 1, "asked"); assert.equal(w2.spacer.h, 2000, "…and nothing to take");
  assert.deepEqual(w2.writes, [{ writer: "anchor-restore", top: 2350, stick: false, from: undefined }]);
});

test("keepPlaceAcrossWindow, the restore missing (the reader's row gone from the rebuilt window): the deep-link re-land with the kept offset, armed and flagged as the re-land of the reader's own row while it runs, disarmed after unless an older fetch is on the wire", () => {
  const w = keepWorld(2350, { land: true });
  assert.equal(w.keep({ uuid: "11111111-2222-4333-8444-000000000011", y: R3_OFFSET }), true);
  assert.equal(keepTakes(w), 1);
  assert.deepEqual(w.calls.filter((c) => Array.isArray(c)), [["scrollToAnchor", "11111111-2222-4333-8444-000000000011", true, "11111111-2222-4333-8444-000000000011", R3_OFFSET]],
    "the attempt runs with relandAsk raised and the anchor armed with the kept offset (the keep-offset write is scrollToAnchor's own)");
  assert.deepEqual(w.state(), { pendingAnchor: null, pendingAnchorKeepY: null, relandAsk: false }, "disarmed after the land, the flag lowered");
  assert.deepEqual(w.writes, [], "the landing wrote; nothing else does");
  // an older fetch pointed at the anchor keeps the arm for chatHead's arrival
  const w2 = keepWorld(2350, { land: false, older: true });
  assert.equal(w2.keep({ uuid: "11111111-2222-4333-8444-000000000011", y: R3_OFFSET }), false);
  assert.deepEqual(w2.state(), { pendingAnchor: "11111111-2222-4333-8444-000000000011", pendingAnchorKeepY: R3_OFFSET, relandAsk: false }, "armed for the arrival");
});

test("keepPlaceAcrossWindow, BOTH restores missing (the reader's row gone and the attempt landing nothing): the take was made, so the row that was under the viewport top goes back at its offset (measured on its own rect), never a take with no write; when the attempt's rebuild dropped that row too, nothing is written and the take is undone (the maintainer's round 3 ruling B: until then the take stood under a reader nothing had placed, disclosed)", () => {
  // the reader's row is nowhere (a fetch is armed for it); before the fix the take grew the head spacer 300 px and nothing was written,
  // so the content under the viewport moved down by 300 px
  const w = keepWorld(2350, { land: false, older: true });
  assert.equal(w.keep({ uuid: "11111111-2222-4333-8444-000000000012", y: R3_OFFSET }), false);
  assert.equal(keepTakes(w), 1, "the take is made before the restores, whatever they find");
  assert.equal(w.spacer.h, 2000 + D);
  assert.deepEqual(w.writes, [{ writer: "anchor-restore", top: 2350 + D, stick: false, from: undefined }], "the row under the viewport top before the take (r3) is put back at its offset");
  assert.equal(w.rows[3].getBoundingClientRect().top, R3_OFFSET, "what the reader saw under the viewport top is still there (it sat 300 px lower with no write)");
  assert.equal(w.parked(), false, "the take stands: the row was put back over it");
  // the same with no fetch armed (an anchor nowhere in the transcript): the arm is dropped, the row still goes back
  const w2 = keepWorld(2350, { land: false });
  assert.equal(w2.keep({ uuid: "11111111-2222-4333-8444-000000000012", y: R3_OFFSET }), false);
  assert.deepEqual(w2.writes, [{ writer: "anchor-restore", top: 2350 + D, stick: false, from: undefined }]);
  assert.deepEqual(w2.state(), { pendingAnchor: null, pendingAnchorKeepY: null, relandAsk: false });
  // the attempt rebuilt the window around the anchor's unit (every row replaced) and its re-query missed: the captured row is gone too,
  // nothing is written, the take is undone, and the reader is where the rebuild left them in the layout it was built in
  const w3 = keepWorld(2350, { land: false, rebuild: (host) => { host.replaceChildren(host.children[0]); for (let i = 20; i < 30; i++) host.add(new Node(100, "turn", "r" + i)); } });
  assert.equal(w3.keep({ uuid: "11111111-2222-4333-8444-000000000012", y: R3_OFFSET }), false);
  assert.equal(keepTakes(w3), 1); assert.deepEqual(w3.writes, [], "no row of the captured DOM is left to put back: nothing written");
  assert.equal(w3.spacer.h, 2000, "…and the take is undone: the head spacer back (at the head it stood 300 px taller under a reader nothing had placed)");
  assert.equal(w3.parked(), true, "the figures wait for a paint that anchors");
  assert.ok(w3.calls.includes("untakeMeasure"), "through untakeMeasure, after both restores missed");
});

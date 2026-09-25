// Compact mode's tail seam, EXECUTED (PR E, the author's pass 0): syncViewInner lifted from render.ts over stubs that record what the seam
// hands its collaborators, the way chat-exact-tail-exec.test.ts lifts chatTail. chat-compact-tail.test.ts drives the plan and the trim
// and pins the seam's text; this file drives the seam's two arguments the text pins could not execute: the rail reference the first
// re-rendered unit is seeded with (railChainBefore over the view's window start, never a scan of s.events: rail-chain.test.ts) and the
// footer patch's `from` (the first CHANGED event when no unit reaches it, a hidden thinking block, else the first re-rendered event,
// whichever is earlier). The author's pass 1b, applying the maintainer's round 1 addendum, added the measured figure's rule over takers, executed: a figure is taken ONLY by a paint that
// anchors the reader (the `anchored` flag: atBottom passed, or true) and EVERY anchoring paint takes one; the stubs record the take and the
// flag the build is handed, and renderWindowItems is lifted alone for its own gate. Synthetic events.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import * as ts from "typescript";
import { createRequire } from "node:module";
import { compactTailPlan } from "./chat-compact-tail";
import type { DisplayItem } from "./compact";
import { DayWalk } from "./time-marker";
import { hideEdges } from "../test-dom-shim";

const requireCjs = createRequire(__filename);
const RENDER = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "render.ts"), "utf8");

function liftBetween(startAnchor: string, endAnchor: string): string {
  const a = RENDER.indexOf(startAnchor), b = RENDER.indexOf(endAnchor, a);
  assert.ok(a > 0 && b > a, `anchors not found: ${startAnchor.slice(0, 40)} or ${endAnchor.slice(0, 40)} moved; re-anchor`);
  return requireCjs("esbuild").transformSync(RENDER.slice(a, b), { loader: "ts" }).code;
}

/** The view's host as the seam reads it: children with data-unit, no bottom spacer, the trim stubbed. */
class FakeEl {
  children!: FakeEl[]; dataset: Record<string, string> = {}; style: Record<string, string> = {};
  constructor(public tag: string, public className = "") { Object.defineProperty(this, "children", { value: [], writable: true, enumerable: false, configurable: true }); hideEdges(this); }
  get childNodes(): FakeEl[] { return this.children; }
  get firstChild(): FakeEl | null { return this.children[0] ?? null; }
  get lastChild(): FakeEl | null { return this.children[this.children.length - 1] ?? null; }
  appendChild(c: FakeEl): FakeEl { this.children.push(c); return c; }
  removeChild(c: FakeEl): void { this.children = this.children.filter((x) => x !== c); }
  querySelector(_sel: string): FakeEl | null { return null; }
}
type Call = any[];
const SENTINEL = 424242;   // the reference railChainBefore hands back, so the seed appendItem receives is traceable to it

/** The seam's prelude: every collaborator syncViewInner reaches, stubbed to record what it is handed. Module-level so the names it stubs
 *  are pinned against render.ts's module-level declarations by a cell below (a stub of a name the renderer no longer has is a red here,
 *  not a dead line: the maintainer's round 6 ruling, regression-2, found dayWalkBeforeEvent stubbed after the author's pass after
 *  the maintainer's round 5 ruling removed it, and nothing stubbed for gapElement, which normal mode's block calls). */
const SEAM_PRELUDE = `
    const H = HOOKS;
    let renderingSid = null, renderingOwnerSid = null;
    const subParts = () => null;
    const sessions = H.sessions, views = H.views;
    const ensureView = (id) => views.get(id);
    const settings = { compact: H.compact !== false };   // compact mode unless the world says normal (the desktop's exact tail, the maintainer's round 2 ruling)
    const displayItems = (s) => H.itemsOf(s);
    const WINDOW_TAIL = 80;
    const lastCompactUnit = () => 0;
    const renderWindowItems = (v, s, items, ws, we, working, anchored) => { H.calls.push(["renderWindowItems", ws, we, anchored]); };
    const applyMeasure = (v) => { H.calls.push(["applyMeasure"]); return false; }; const redrawGapUnits = () => {};
    const sizeSpacers = () => { H.calls.push(["sizeSpacers"]); };
    const patchWorkedFooters = (v, s, from, working, items) => { H.calls.push(["patchWorkedFooters", from, working, items ? items.length : null]); };
    const compactTailPlan = H.compactTailPlan;
    const trimUnitsFrom = (host, u0) => { H.calls.push(["trim", u0]); return 0; };
    const clearRailRings = (host) => { H.calls.push(["clearRailRings", host === H.views.get("A").el]); };   // the band module's ring remover, host-scoped for the tail paint (the maintainer's round 2 ruling took the rings and the glow here; the maintainer's round 3 ruling D left the glow to applyGlow); records that it is the view's own host
    const railChainBefore = (s, items, winStart, u0) => { H.calls.push(["railChainBefore", winStart, u0]); return H.SENTINEL; };
    const dayWalkBefore = () => new H.DayWalk();
    const turnOfEvents = () => null;
    const appendItem = (v, s, items, u, prevEpoch) => { H.calls.push(["appendItem", u, prevEpoch]); return prevEpoch; };
    const evictCompactTop = (v, ws) => { H.calls.push(["evict", ws]); if (ws <= (v.winStart ?? 0)) return false; v.winStart = ws; return true; };   // the real one's answer: whether it evicted
    const reseedWindowHead = (v, s, items) => { H.calls.push(["reseed", v.winStart, items.length]); };
    // normal mode's names: reached in a normal-mode world alone (the renderer records the event it drew; gapElement records the gap it drew, which
    // the block reaches for a gap item at or past the first changed event's unit on the exact-tail path: the maintainer's round 6 ruling, regression-2)
    const prevTimedEpoch = () => null; const eventEpoch = () => null; const dayDividerFor = () => null;
    const gapElement = (s, it, v) => { H.calls.push(["gapElement", it.lo, it.hi]); return new H.FakeEl("div", "tx-gap"); };
    const renderEvent = (ev) => { H.calls.push(["renderEvent", ev.uuid]); return new H.FakeEl("div", "turn"); }; const turnWorkedSecs = () => null; const stampWalkDay = () => {};
    const HTMLElement = H.FakeEl; const el = (t, c) => new H.FakeEl(t, c || "");
  `;

function liftSeam(sessions: Map<string, any>, views: Map<string, any>, itemsOf: (s: any) => DisplayItem[], calls: Call[], compact = true) {
  const js = liftBetween("function syncViewInner(", "function patchWorkedFooters(");
  // itemFirstEvent is LIFTED with the seam, never hand-copied (the author's verifier pass over pass 1b): a copy re-creates the drift the
  // next time production's first-event rule moves, and the seam's footer `from` (the first re-rendered unit's first event) would then be
  // modelled against a stale map while the harness stayed green. No itemFirstEvent call in the lifted range can see a gap: compact mode's
  // footer patch reads it at u0, where the plan has rebuilt for a gap at or past u0, and normal mode's lookup and its loop skip a gap item by
  // its kind; so the lift is proven by a production mutation of the run case, which a hand copy would have hidden.
  const first = liftBetween("function itemFirstEvent(", "// The display-unit index");
  return new Function("HOOKS", SEAM_PRELUDE + first + js + "\nreturn syncViewInner;")({ sessions, views, itemsOf, calls, compactTailPlan, DayWalk, FakeEl, SENTINEL, compact }) as (id: string, atBottom?: boolean, anchored?: boolean) => any;
}
/** renderWindowItems lifted alone (its own gate on the flag) over a recording applyMeasure and stubs for what it appends. */
function liftBuild(calls: Call[]) {
  const js = liftBetween("function renderWindowItems(", "/** The spacer map's gap entries");
  const prelude = `
    const H = HOOKS;
    const applyMeasure = (v) => { H.calls.push(["applyMeasure"]); return false; };
    const el = (t, c) => new H.FakeEl(t, c || "");
    const railSeed = () => null; const dayWalkBefore = () => new H.DayWalk(); const turnOfEvents = () => null;
    const appendItem = (v, s, items, u, prevEpoch) => { H.calls.push(["appendItem", u]); return prevEpoch; };
    const gapUnitsOf = () => undefined; const sizeSpacers = () => { H.calls.push(["sizeSpacers"]); };
  `;
  return new Function("HOOKS", prelude + js + "\nreturn renderWindowItems;")({ calls, FakeEl, DayWalk }) as (...a: any[]) => void;
}
const ev = (index: number): DisplayItem => ({ kind: "event", index });
const tg = (...indices: number[]): DisplayItem => ({ kind: "toolgroup", indices });
/** A world: a session over `kinds`, its view built from `prevItems` over the whole list (winStart given), the first changed event `from`;
 *  `compact` false is the desktop's normal mode (a unit is an event). */
function world(kinds: string[], prevItems: DisplayItem[], itemsNow: DisplayItem[], from: number, winStart = 0, working = true, compact = true) {
  const calls: Call[] = [];
  const s = { id: "A", events: kinds.map((kind, i) => ({ kind, uuid: "e" + i, ts: "2026-09-19T10:00:0" + (i % 10) + "Z" })), status: { state: working ? "working" : "ready" } };
  const host = new FakeEl("div");
  for (let u = winStart; u < prevItems.length; u++) { const n = new FakeEl("div", "turn"); n.dataset.unit = String(u); host.appendChild(n); }
  const v: any = { el: host, rendered: from, stale: false, winStart, winEnd: prevItems.length, unitTotal: prevItems.length, units: prevItems, working: !working, shown: true, stick: true };
  const sync = liftSeam(new Map([["A", s]]), new Map([["A", v]]), () => itemsNow, calls, compact);
  return { calls, s, v, sync };
}

test("the seam seeds the first re-rendered unit with railChainBefore over the view's window start, and appendItem receives that reference", () => {
  // the reply at unit 2 streams behind a collapsed run; the window opened at unit 1 (a top spacer stands for the prompt)
  const w = world(["user", "tool", "tool", "assistant"], [ev(0), tg(1, 2), ev(3)], [ev(0), tg(1, 2), ev(3)], 3, 1);
  w.sync("A", true);
  assert.deepEqual(w.calls.filter((c) => c[0] === "railChainBefore"), [["railChainBefore", 1, 2]], "the chain from the window's start to u0");
  assert.deepEqual(w.calls.filter((c) => c[0] === "appendItem"), [["appendItem", 2, SENTINEL]], "the reply's unit re-rendered from that reference");
  assert.deepEqual(w.calls.filter((c) => c[0] === "trim"), [["trim", 2]]);
  assert.deepEqual(w.calls.filter((c) => c[0] === "clearRailRings"), [["clearRailRings", true]], "the band's rings come off the view's own host, through the band module's remover (the maintainer's round 2 ruling, narrowed by the maintainer's round 3 ruling D to the rings)");
  assert.ok(w.calls.findIndex((c) => c[0] === "clearRailRings") < w.calls.findIndex((c) => c[0] === "trim"), "…where the trim drops the band, before it");
  assert.equal(w.v.rendered, 4); assert.deepEqual(w.v.units, [ev(0), tg(1, 2), ev(3)]);
  // a run forming (a tool joins the lone tool at unit 1): the seam re-renders from unit 1, seeded with the chain before it
  const w2 = world(["user", "tool", "tool"], [ev(0), ev(1)], [ev(0), tg(1, 2)], 2, 0);
  w2.sync("A", true);
  assert.deepEqual(w2.calls.filter((c) => c[0] === "railChainBefore"), [["railChainBefore", 0, 1]]);
  assert.deepEqual(w2.calls.filter((c) => c[0] === "appendItem"), [["appendItem", 1, SENTINEL]]);
});

test("the footer patch's from: the first CHANGED event when no unit reaches it (a hidden thinking block landing, working flipping in the same frame), else the first re-rendered event, whichever is earlier; the flip's fast path is not taken", () => {
  // the idle session's reply carries its footer; the session resumes the same turn: a thinking atom lands (event 2, hidden) with the status
  // flip to working in the same frame. No unit reaches event 2 (u0 = total): nothing re-rendered, and the patch must be told 2, not len (3)
  const w = world(["user", "assistant", "thinking"], [ev(0), ev(1)], [ev(0), ev(1)], 2, 0, true);
  w.v.working = false;   // the view's last sync saw the session idle
  w.sync("A", true);
  assert.deepEqual(w.calls.filter((c) => c[0] === "renderWindowItems"), [], "no rebuild: the plan's append with u0 = total");
  assert.deepEqual(w.calls.filter((c) => c[0] === "appendItem"), [], "nothing re-rendered");
  assert.deepEqual(w.calls.filter((c) => c[0] === "patchWorkedFooters"), [["patchWorkedFooters", 2, true, 2]], "the patch is told the first changed event (v.rendered before the bookkeeping), with the unit list");
  assert.equal(w.v.rendered, 3, "…and the bookkeeping then moves v.rendered to len");
  // a reply appended at the tail: the first re-rendered event is the changed one
  const w2 = world(["user", "assistant", "user"], [ev(0), ev(1)], [ev(0), ev(1), ev(2)], 2, 0);
  w2.sync("A", true);
  assert.deepEqual(w2.calls.filter((c) => c[0] === "patchWorkedFooters"), [["patchWorkedFooters", 2, true, 3]]);
  // a run forming behind the change: the first re-rendered event (the run's first member, 1) is earlier than the changed event (2)
  const w3 = world(["user", "tool", "tool"], [ev(0), ev(1)], [ev(0), tg(1, 2)], 2, 0);
  w3.sync("A", true);
  assert.deepEqual(w3.calls.filter((c) => c[0] === "patchWorkedFooters"), [["patchWorkedFooters", 1, true, 2]]);
});

test("an append at the bottom that evicts the top re-seeds the promoted head unit: the eviction reports it and the seam hands the re-seed the session and the units; an append that evicts nothing re-seeds nothing", () => {
  // 81 units built over the whole list (the span is max(WINDOW_TAIL, 81)); a prompt lands: 82 units, the top evicted to unit 1
  const kinds = Array.from({ length: 82 }, () => "user");
  const prev = Array.from({ length: 81 }, (_, i) => ev(i)), now = prev.concat([ev(81)]);
  const w = world(kinds, prev, now, 81, 0);
  w.sync("A", true);
  assert.deepEqual(w.calls.filter((c) => c[0] === "evict" || c[0] === "reseed"), [["evict", 1], ["reseed", 1, 82]], "the eviction, then the re-seed at the new start over the units now");
  assert.ok(w.calls.findIndex((c) => c[0] === "reseed") > w.calls.findIndex((c) => c[0] === "appendItem"), "…after the append, so the window it re-seeds is the one a build would render");
  // a shorter window: the appended unit fits the span, nothing is evicted, nothing re-seeded
  const w2 = world(["user", "assistant", "user"], [ev(0), ev(1)], [ev(0), ev(1), ev(2)], 2, 0);
  w2.sync("A", true);
  assert.deepEqual(w2.calls.filter((c) => c[0] === "evict" || c[0] === "reseed"), [["evict", 0]], "the eviction asked and declined: no re-seed");
});

test("a scrolled-up reader's append (atBottom false) keeps the window's top (keepTop): no eviction is asked, no re-seed, and v.winStart holds", () => {
  // the same world as the evicting append above, the reader scrolled up: the content above the viewport must stay where it is
  const kinds = Array.from({ length: 82 }, () => "user");
  const prev = Array.from({ length: 81 }, (_, i) => ev(i)), now = prev.concat([ev(81)]);
  const w = world(kinds, prev, now, 81, 0);
  w.sync("A", false);
  assert.deepEqual(w.calls.filter((c) => c[0] === "evict" || c[0] === "reseed"), [], "no eviction asked, no re-seed");
  assert.equal(w.v.winStart, 0, "the window's start held");
  assert.deepEqual(w.calls.filter((c) => c[0] === "appendItem"), [["appendItem", 81, SENTINEL]], "the unit was appended all the same");
  assert.equal(w.v.winEnd, 82);
});

test("a change below a browsed window patches the worked footers from the first changed event and grows the bottom spacer: no trim, no appendItem, no rebuild (the maintainer's round 1 addendum: the footer is the one render inside the window that reads later events)", () => {
  // six units built, a reply landed as the seventh; the window browsed away from the tail (winEnd lowered to 4 by hand, as a landing leaves it).
  // The footer patch is told the first changed event (6, v.rendered before the bookkeeping moves it to len) with the unit list, as the append
  // branch's is; the rebuild this branch replaced re-rendered the window's footers whenever events landed below it, and the branch alone left
  // them as they were (a turn completed by a prompt below the window kept its live spinner instead of its "worked …" footer)
  const kinds = ["user", "assistant", "user", "assistant", "user", "assistant", "assistant"];
  const prev = Array.from({ length: 6 }, (_, i) => ev(i)), now = prev.concat([ev(6)]);
  const w = world(kinds, prev, now, 6, 0);
  w.v.winEnd = 4;
  w.sync("A");
  assert.deepEqual(w.calls, [["patchWorkedFooters", 6, true, 7], ["sizeSpacers"]], "the footer patch from the pre-append v.rendered, then the spacer re-size, and nothing else");
  assert.deepEqual(w.calls.filter((c) => c[0] === "appendItem" || c[0] === "renderWindowItems" || c[0] === "trim"), [], "no unit re-rendered, no rebuild");
  assert.equal(w.calls.filter((c) => c[0] === "sizeSpacers").length, 1, "one spacer re-size");
  assert.equal(w.v.spacerCountBot, 3, "total less winEnd: the units the bottom spacer stands for");
  assert.equal(w.v.rendered, 7, "the bookkeeping moves v.rendered to len after the patch"); assert.equal(w.v.unitTotal, 7); assert.deepEqual(w.v.units, now);
  assert.equal(w.v.el.children.length, 6, "no unit node added or removed");
});

test("normal mode (the compact switch off), a change below a browsed window: the browse branch patches the worked footers from the first changed event with the unit list, then grows the bottom spacer: no trim, no re-render, no rebuild (the maintainer's round 3 ruling B: compact mode's spacer branch was fixed for this in the author's pass 1b and this branch, the same outcome on the other side of the switch, was not, so a prompt completing the turn below the window put no footer on the window's last reply)", () => {
  // the compact test above, on the other side of the switch: six units built, a reply landed as the seventh, the window browsed away from the
  // tail (winEnd lowered to 4 by hand, as a landing leaves it); the patch is told the unit list, seven items here, one per event, as every
  // site is (the maintainer's round 5 ruling, regression-1: this mode's list carries the regions' gaps, so a unit is the list's index)
  const kinds = ["user", "assistant", "user", "assistant", "user", "assistant", "assistant"];
  const prev = Array.from({ length: 6 }, (_, i) => ev(i)), now = prev.concat([ev(6)]);
  const w = world(kinds, prev, now, 6, 0, true, false);
  w.v.winEnd = 4;
  w.sync("A");
  assert.deepEqual(w.calls, [["patchWorkedFooters", 6, true, 7], ["sizeSpacers"]], "the footer patch from the pre-append v.rendered with the unit list (seven items), then the spacer re-size, and nothing else (at the head the maintainer's round 3 ruled on: the spacer re-size alone; at the head the maintainer's round 5 ruled on: no unit list)");
  assert.deepEqual(w.calls.filter((c) => c[0] === "trim" || c[0] === "renderEvent" || c[0] === "renderWindowItems" || c[0] === "appendItem"), [], "no unit re-rendered, no rebuild");
  assert.equal(w.v.spacerCountBot, 3, "total less winEnd: the units the bottom spacer stands for");
  assert.equal(w.v.rendered, 7, "the bookkeeping moves v.rendered to len after the patch"); assert.equal(w.v.unitTotal, 7);
  assert.equal(w.v.el.children.length, 6, "no unit node added or removed");
});

test("normal mode's exact tail trims through the shared walk (trimUnitsFrom from the first changed event's unit), then re-renders from there and patches the footers with the unit list: no plan, no compact helper (the maintainer's round 2 ruling: its own copy of the walk stopped at a hover's band and re-appended the tail on top of a stale copy)", () => {
  // the desktop (compact off): the reply at event 1 edited (from = 1) in a two-event view; the walk is asked from event 1, the events from
  // it re-rendered in order, the footers patched from it with the unit list (two items, one per event; the maintainer's round 5 ruling, regression-1)
  const w = world(["user", "assistant"], [ev(0), ev(1)], [ev(0), ev(1)], 1, 0, true, false);
  w.sync("A", true);
  assert.deepEqual(w.calls.filter((c) => c[0] === "trim"), [["trim", 1]], "one trim, from the first changed event's unit (the shared walk drops a foreign child on its way: chat-compact-tail.test.ts)");
  assert.deepEqual(w.calls.filter((c) => c[0] === "clearRailRings"), [["clearRailRings", true]], "the band's rings come off the view's own host here too, through the band module's remover");
  assert.ok(w.calls.findIndex((c) => c[0] === "clearRailRings") < w.calls.findIndex((c) => c[0] === "trim"), "…before the trim drops the band");
  assert.deepEqual(w.calls.filter((c) => c[0] === "renderEvent"), [["renderEvent", "e1"]], "the events from the change re-rendered");
  assert.deepEqual(w.calls.filter((c) => c[0] === "patchWorkedFooters"), [["patchWorkedFooters", 1, true, 2]], "the footers patched from the change, with the unit list (two items)");
  assert.deepEqual(w.calls.filter((c) => c[0] === "appendItem" || c[0] === "renderWindowItems" || c[0] === "evict" || c[0] === "reseed"), [], "no compact helper, no rebuild");
  assert.ok(w.calls.findIndex((c) => c[0] === "trim") < w.calls.findIndex((c) => c[0] === "renderEvent"), "the trim before the re-render");
  assert.equal(w.v.rendered, 2); assert.equal(w.v.winEnd, 2); assert.equal(w.v.spacerCountBot, 0);
  assert.equal(w.v.el.children[w.v.el.children.length - 1].dataset.unit, "1", "the re-rendered node carries its event index as its unit");
  // an append at the tail (from = len before the append): the walk is asked from the new event, where nothing stands yet
  const w2 = world(["user", "assistant", "user"], [ev(0), ev(1)], [ev(0), ev(1), ev(2)], 2, 0, true, false);
  w2.sync("A", true);
  assert.deepEqual(w2.calls.filter((c) => c[0] === "trim" || c[0] === "renderEvent"), [["trim", 2], ["renderEvent", "e2"]]);
});

test("render.ts: one owner per hover class. The tail paint (both paths and the trim) removes no class itself; the rings' one remover is the band module's clearRailRings, host-scoped when the tail paint calls it; the glow's one remover is applyGlow (the maintainer's round 3 ruling D: a second remover of a class outside its owner is the defect). The census reads the compiler's syntax tree of render.ts and of every module it reaches, and keys on the class a mutation RESOLVES to, never on a spelling (the author's fixer pass over pass 4)", () => {
  // the population: the classes the tail paint took off until pass 4 (.rail-ring, the band's; .ext-glow, applyGlow's), each with its adder and
  // its remover named, so the ownership is a fact of the tree and not of a comment. The census parses render.ts and every module it reaches
  // through relative imports (the webview's bundle from this entry) and keys on the PROPERTY: a class mutation (classList.add/remove/toggle/
  // replace, a className write, setAttribute("class")) whose class argument RESOLVES to an owned class sits inside its owner, whatever the
  // spelling and whatever the file. Resolution: a string literal, a substitution-free template, a regular-expression literal (its source read
  // as the class tokens it names, escapes stripped), the RegExp constructor, called or constructed, over a source that resolves (the second
  // closing lens over the closing pass: `new RegExp("\\bext-glow\\b")` was no literal to `resolve`, which read a `new` expression as
  // nothing), a template or `+` concatenation of resolvable parts, a conditional's two arms, an identifier bound to a string, a
  // regular-expression or a RegExp-constructor constant in an enclosing block or at module level; a className write is read whole and, when
  // its right side is built by `.replace` or `.replaceAll`, through that call's pattern and replacement, so a rewrite that strips the class
  // by a regular expression is a remover naming it (the closing pass over the author's fixer pass: `className =
  // className.replace(/\bext-glow\b/, "")` planted in sizeSpacers and in evictCompactTop passed both axes, the right side resolving to nothing
  // and the regular expression being no literal to the second axis). The pass-4 census counted the literal `classList.remove("ext-glow")`
  // over render.ts alone, so a `classList.toggle("ext-glow", false)`, a remover through an alias of the class name and a remover in another
  // module all passed it (the mutations note, R4-M32 and its variants). Second axis: every string, template or regular-expression literal
  // naming an owned class as a token, every literal read through a regular expression's escape rules first (so a RegExp source in a string,
  // `"\\bext-glow\\b"`, names ext-glow, where its text tokenized to `bext-glow` before the second closing lens), by (module, owner), a
  // closed multiset, so a literal handed to a helper that mutates by parameter, or a new selector on the class, is enumerated here or reds. Outside the two axes: a mutator whose class comes from a parameter or a computed
  // value with no literal at its site, enumerated below as a closed multiset by (module, owner, method), so a mutator added with no
  // constant class is named or reds (the second closing lens over the closing pass: the count stood in a comment alone); none is handed an
  // owned class by any literal the second axis sees, and a caller passing the class through a variable shows up as its module's literal.
  // Outside the census: a className write that names no class at all (a wipe to "", a list rebuilt from a computed value), which takes
  // every class off a node it does not own.
  const dir = path.resolve(process.cwd(), "..", "ui", "webview");
  const files = new Map<string, ts.SourceFile>();
  const load = (rel: string): void => {
    const base = path.resolve(dir, rel);
    const p = [base + ".ts", base + ".js", base].find((c) => fs.existsSync(c) && fs.statSync(c).isFile());   // a specifier may carry its extension (a vendored .js module)
    assert.ok(p, "an import in render.ts's bundle resolves to a module file: " + rel);
    if (files.has(p!)) return;
    const sf = ts.createSourceFile(p!, fs.readFileSync(p!, "utf8"), ts.ScriptTarget.Latest, true, p!.endsWith(".js") ? ts.ScriptKind.JS : ts.ScriptKind.TS);
    files.set(p!, sf);
    for (const st of sf.statements) {
      const spec = (ts.isImportDeclaration(st) || ts.isExportDeclaration(st)) && st.moduleSpecifier && ts.isStringLiteral(st.moduleSpecifier) ? st.moduleSpecifier.text : null;
      if (spec && spec.startsWith(".")) load(path.join(path.dirname(path.relative(dir, p!)), spec));
    }
  };
  load("render");
  assert.ok(files.size > 100, "the bundle's modules are reached from render.ts (" + files.size + ")");
  const OWNED = new Set(["ext-glow", "rail-ring"]);
  // a regular expression's source as the class tokens it names: the slashes and flags off, escaped punctuation kept (`\-` is a hyphen in a
  // class name), the class escapes (`\b`, `\s`, `\S` and the rest) read as separators, so `/\bext-glow\b/` names ext-glow; every literal
  // the second axis tokenizes goes through the same rules, so a source string for the RegExp constructor names its class too
  const regexClasses = (src: string): string => src.replace(/^\/([\s\S]*)\/[a-z]*$/, "$1").replace(/\\([^A-Za-z0-9])/g, "$1").replace(/\\[A-Za-z]/g, " ");
  const namesOwned = (text: string): boolean => regexClasses(text).split(/[^A-Za-z0-9_-]+/).some((t) => OWNED.has(t));
  const REMOVERS = new Set(["classList.remove", "classList.toggle", "classList.replace", "className=", "setAttribute(class)"]);
  const mutations: string[] = [], literals: string[] = [], tailPaint: string[] = [], ringCalls: string[] = [], unresolved: string[] = [];
  let clearHoverMarks = 0;
  for (const [p, sf] of files) {
    const rel = path.relative(dir, p);
    const nameOf = (fn: ts.SignatureDeclaration): string | null => {
      if ((ts.isFunctionDeclaration(fn) || ts.isMethodDeclaration(fn) || ts.isFunctionExpression(fn)) && fn.name) return fn.name.getText(sf);
      const q = fn.parent;
      if (q && ts.isVariableDeclaration(q) && ts.isIdentifier(q.name)) return q.name.text;
      if (q && (ts.isPropertyAssignment(q) || ts.isPropertyDeclaration(q))) return q.name.getText(sf);
      return null;
    };
    const ownerOf = (n: ts.Node): string => { for (let q: ts.Node | undefined = n.parent; q; q = q.parent) { if (ts.isFunctionLike(q)) { const nm = nameOf(q); if (nm) return nm; } } return "<module>"; };
    // the RegExp constructor, called or constructed, over a source it resolves: `new RegExp("\\bext-glow\\b")` names ext-glow as its literal does
    const isRegExpCtor = (e: ts.Node): e is ts.NewExpression | ts.CallExpression => (ts.isNewExpression(e) || ts.isCallExpression(e)) && ts.isIdentifier(e.expression) && e.expression.text === "RegExp";
    const constOf = (id: ts.Identifier): string | null => {   // `const <id> = "<literal>"`, `= /<pattern>/` or `= new RegExp("<source>")` in the nearest enclosing block that declares it, else the module's
      for (let q: ts.Node | undefined = id.parent; q; q = q.parent) {
        if (!ts.isBlock(q) && !ts.isSourceFile(q)) continue;
        for (const st of q.statements) if (ts.isVariableStatement(st)) for (const d of st.declarationList.declarations) if (ts.isIdentifier(d.name) && d.name.text === id.text && d.initializer) {
          if (ts.isStringLiteral(d.initializer) || ts.isNoSubstitutionTemplateLiteral(d.initializer)) return d.initializer.text;
          if (ts.isRegularExpressionLiteral(d.initializer)) return regexClasses(d.initializer.text);
          if (isRegExpCtor(d.initializer)) return resolve(d.initializer);
        }
      }
      return null;
    };
    const resolve = (e: ts.Expression | undefined): string | null => {   // null: the class is not a constant of the source
      if (!e) return "";
      if (ts.isStringLiteral(e) || ts.isNoSubstitutionTemplateLiteral(e)) return e.text;
      if (ts.isRegularExpressionLiteral(e)) return regexClasses(e.text);
      if (isRegExpCtor(e)) { const r = resolve(e.arguments?.[0]); return r == null ? null : regexClasses(r); }
      if (ts.isIdentifier(e)) return constOf(e);
      if (ts.isTemplateExpression(e)) { let t = e.head.text; for (const sp of e.templateSpans) { const r = resolve(sp.expression); if (r == null) return null; t += r + sp.literal.text; } return t; }
      if (ts.isBinaryExpression(e) && e.operatorToken.kind === ts.SyntaxKind.PlusToken) { const a = resolve(e.left), b = resolve(e.right); return a == null || b == null ? null : a + b; }
      if (ts.isParenthesizedExpression(e)) return resolve(e.expression);
      if (ts.isConditionalExpression(e)) { const a = resolve(e.whenTrue), b = resolve(e.whenFalse); return a == null || b == null ? null : a + " " + b; }
      return null;
    };
    const record = (n: ts.Node, method: string, args: readonly ts.Expression[]): void => {
      const owner = ownerOf(n);
      if ((owner === "syncViewInner" || owner === "trimUnitsFrom") && REMOVERS.has(method)) tailPaint.push(rel + ":" + owner + ":" + method);
      for (const a of args) { const r = resolve(a); if (r == null) unresolved.push(rel + ":" + owner + ":" + method); else if (namesOwned(r)) mutations.push(rel + ":" + owner + ":" + method + ":" + r.trim()); }
    };
    // a className write's class arguments: the right side whole and, when it is built by a `.replace` or `.replaceAll` chain (a rewrite that
    // strips or swaps a class), each call's pattern and replacement
    const classWriteArgs = (e: ts.Expression): ts.Expression[] => { const out: ts.Expression[] = [e]; for (let x: ts.Expression = e; ts.isCallExpression(x) && ts.isPropertyAccessExpression(x.expression); x = x.expression.expression) if (x.expression.name.text === "replace" || x.expression.name.text === "replaceAll") out.push(...x.arguments); return out; };
    const visit = (n: ts.Node): void => {
      if (ts.isCallExpression(n) && ts.isPropertyAccessExpression(n.expression)) {
        const m = n.expression.name.text, obj = n.expression.expression;
        if (["add", "remove", "toggle", "replace"].includes(m) && ts.isPropertyAccessExpression(obj) && obj.name.text === "classList") record(n, "classList." + m, m === "toggle" ? n.arguments.slice(0, 1) : n.arguments);
        if (m === "setAttribute" && n.arguments[0] && ts.isStringLiteral(n.arguments[0]) && n.arguments[0].text === "class") record(n, "setAttribute(class)", n.arguments.slice(1));
      }
      if (ts.isCallExpression(n) && ts.isIdentifier(n.expression) && n.expression.text === "clearRailRings") ringCalls.push(rel + ":" + ownerOf(n) + "(" + n.arguments.map((a) => a.getText(sf)).join(", ") + ")");
      if (ts.isBinaryExpression(n) && n.operatorToken.kind >= ts.SyntaxKind.FirstAssignment && n.operatorToken.kind <= ts.SyntaxKind.LastAssignment && ts.isPropertyAccessExpression(n.left) && n.left.name.text === "className") record(n, "className=", classWriteArgs(n.right));
      if ((ts.isStringLiteral(n) || ts.isNoSubstitutionTemplateLiteral(n) || ts.isTemplateHead(n) || ts.isTemplateMiddle(n) || ts.isTemplateTail(n)) && namesOwned(n.text)) literals.push(rel + ":" + ownerOf(n) + ":" + JSON.stringify(n.text));
      if (ts.isRegularExpressionLiteral(n) && namesOwned(regexClasses(n.text))) literals.push(rel + ":" + ownerOf(n) + ":" + n.text);
      if (ts.isIdentifier(n) && n.text === "clearHoverMarks") clearHoverMarks++;
      ts.forEachChild(n, visit);
    };
    visit(sf);
  }
  assert.deepEqual(mutations.sort(), [
    "render.ts:applyGlow:classList.add:ext-glow", "render.ts:applyGlow:classList.add:ext-glow",   // by mid, by uuid
    "render.ts:applyGlow:classList.remove:ext-glow",                                            // the one remover of the glow: document-wide, at the start of every application
    "render.ts:clearRailRings:classList.remove:rail-ring",                                      // the one remover of the rings: on the host it is given, the document by default
    "render.ts:drawRailBand:classList.add:rail-ring",                                           // the one adder of the rings
  ].sort(), "every class mutation in the bundle that resolves to a hover class, by module, owner and method: one adder and one remover per class, each inside its owner; a second remover in any spelling, through an alias of the class name, in another module, or as a className rewrite through a regular expression, a literal or the RegExp constructor over a string, reds");
  assert.deepEqual(literals.sort(), [
    'render.ts:applyGlow:".ext-glow"', 'render.ts:applyGlow:"ext-glow"', 'render.ts:applyGlow:"ext-glow"', 'render.ts:applyGlow:"ext-glow"',   // the remover's selector and the three mutations
    'render.ts:clearRailRings:".dot.rail-ring"', 'render.ts:clearRailRings:"rail-ring"',                                                    // the remover's selector and the mutation
    'render.ts:drawRailBand:"rail-ring"',                                                                                                 // the adder
    'render.ts:paintGlowRuler:".turn.ext-glow"', 'render.ts:paintRailBand:".turn.ext-glow"',                                                // the two READERS of the glow: the ruler mirrors it, the band reads it
  ].sort(), "every string, template or regular-expression literal in the bundle naming a hover class as a token, by module and owner: the owners, the two readers, nothing else (a literal handed to a helper that mutates by parameter, a new selector on the class, or a pattern that strips it, a regular-expression literal or a RegExp source string, is enumerated here or reds)");
  // the mutators the two axes cannot read (a parameter, a computed value), by module, owner and method, a closed multiset; the message names
  // what was added and what is gone, so a 45th is enumerated here (and its class, when a literal reaches it, on the literal axis) or reds
  const EXPECTED_UNRESOLVED = [
    "anchor-map.ts:makeMark:setAttribute(class)", "anchor-map.ts:makePoint:setAttribute(class)", "anchor-map.ts:stampBlock:setAttribute(class)",
    "code-block.ts:el:className=", "ctx-menu.ts:addMenuItem:className=", "ctx-menu.ts:menuCard:className=", "file-browse.ts:el:className=",
    "file-comments-regions.ts:mk:className=", "file-comments.ts:el:className=", "file-comments.ts:frameImage:classList.add", "file-comments.ts:graft:className=",
    "file-comments.ts:stripBlockPaint:classList.remove", "file-comments.ts:unframeImage:classList.remove", "file-view-links.ts:withClass:setAttribute(class)",
    "file-view.ts:copySay:classList.add",
    // the figure's Open the picture control, neither class a hover class: decideFigureControl adds fv-figopen-left or fv-figopen-right,
    // FIGOPEN_CLASS joined to the figure's own align attribute (the sanitizer keeps it), so the control floats with a floated figure, the side
    // read at run time; dressFigureControl toggles FIGOPEN_WEB_CLASS, fv-figopen-web, on a control whose target is a picture from the web, a
    // constant declared as FIGOPEN_CLASS + "-web", a concatenation constOf above (a literal initializer alone) does not fold
    "file-view.ts:decideFigureControl:classList.add", "file-view.ts:dressFigureControl:classList.toggle",
    // the drop of the classes the sheets dim from an author's markup around a figure (the file review's round 16, extra5-2), no hover class
    // among them: dropDimmingClasses removes the classes of SHEET_DIM_CLASSES an element of the sanitizer's body carries, read at run time off
    // the author's class attribute, before any pass of the viewer's own; and beside it the drop of what lets a press pass through an author
    // element (the file review's round 16, extra5-1, the covered sign), no hover class among them either: dropPressThrough removes the classes
    // of SHEET_PRESS_THROUGH_CLASSES any element of the sanitizer's body carries, read the same way
    "file-view.ts:dropDimmingClasses:classList.remove", "file-view.ts:dropPressThrough:classList.remove",
    "file-view.ts:el:className=", "path-links.ts:el:className=", "path-links.ts:markPathLink:setAttribute(class)",
    "pinned-notes.ts:make:className=", "preview.ts:say:classList.add",
    "render.ts:applyFold:classList.add", "render.ts:applyTabStatus:classList.add", "render.ts:dress:className=", "render.ts:el:className=",
    "render.ts:notice:classList.add", "render.ts:notice:classList.add", "render.ts:onMoveDirCompletions:className=", "render.ts:rememberFold:classList.toggle",
    "render.ts:renderDirMenu:className=", "render.ts:renderFilePreview:className=", "render.ts:renderPendingGroup:className=", "render.ts:updateCommentRail:className=",
    "render.ts:updateStatusline:classList.add",
    "status-chip.ts:statusChip:className=", "status-controls.ts:el:className=", "status-widgets.ts:el:className=",
    "tab-widgets.ts:composeTabRing:classList.add", "tab-widgets.ts:composeTabRing:classList.remove", "tab-widgets.ts:el:className=",
    "url-links.ts:linkifyUrls:className=", "url-links.ts:urlChip:className=",
  ];
  const multisetLess = (a: string[], b: string[]): string[] => { const left = new Map<string, number>(); for (const x of b) left.set(x, (left.get(x) ?? 0) + 1); return a.filter((x) => { const n = left.get(x) ?? 0; if (n > 0) { left.set(x, n - 1); return false; } return true; }); };
  assert.deepEqual(unresolved.sort(), [...EXPECTED_UNRESOLVED].sort(), "every class mutator in the bundle whose class is no constant of the source (a parameter, a computed value), by module, owner and method, a closed multiset: added " + JSON.stringify(multisetLess(unresolved, EXPECTED_UNRESOLVED)) + ", gone " + JSON.stringify(multisetLess(EXPECTED_UNRESOLVED, unresolved)) + "; a mutator added with no constant class is enumerated here or reds");
  assert.deepEqual(tailPaint, [], "the tail paint (syncViewInner, both paths, and the trim) removes or replaces no class of any kind itself, by owner from the tree");
  assert.deepEqual(ringCalls.filter((c) => c.startsWith("render.ts:syncViewInner")), ["render.ts:syncViewInner(v.el)", "render.ts:syncViewInner(v.el)"], "both tail paths hand the view's own host to the band module's remover (the compact seam's append branch, normal mode's exact tail; compact-tail-differential.test.ts lifts the remover and executes both paths)");
  assert.equal(clearHoverMarks, 0, "the second remover is gone: no identifier in the bundle names it");
  assert.match(RENDER, /function clearRailRings\(host: ParentNode = document\): void \{\s*\n\s*host\.querySelectorAll\("\.dot\.rail-ring"\)\.forEach\(\(n\) => n\.classList\.remove\("rail-ring"\)\);\s*\n\}/, "the remover reads the host it is given, the document by default (executed by the differential's lift)");
});

test("a paint of the view ends a re-window's follow of its rebuilt rows: the mark armed by the stick re-window is cleared before any branch runs (the maintainer's round 1 addendum; the reader's own scroll is the other ending event, tail-shrink.test.ts)", () => {
  const w = world(["user", "assistant"], [ev(0), ev(1)], [ev(0), ev(1)], 2, 0);
  w.v.followRebuilt = true;
  w.sync("A", true);
  assert.equal(w.v.followRebuilt, false, "appendActive's paint has a follow of its own (append-stick); the re-window's is over");
  const w2 = world(["user", "assistant"], [ev(0), ev(1)], [ev(0), ev(1)], 2, 0);
  w2.v.followRebuilt = true;
  w2.sync("A");
  assert.equal(w2.v.followRebuilt, false, "…and a switch's or a landing's paint ends it too");
});

// ── the measured figure: taken only by a paint that anchors the reader, and by every one of them (the maintainer's round 1 addendum) ──────────────────

test("a sync with no flag (a switch's, a landing's, a hidden prebuild's) takes no measured figure and tells its build so: applyMeasure is never called and renderWindowItems is handed anchored false", () => {
  // a stale view, so the paint takes the rebuild road: the flag reaches the build
  const w = world(["user", "assistant"], [ev(0), ev(1)], [ev(0), ev(1)], 2, 0);
  w.v.stale = true;
  w.sync("A");
  assert.deepEqual(w.calls.filter((c) => c[0] === "applyMeasure"), [], "no take in a paint that does not anchor the reader");
  assert.deepEqual(w.calls.filter((c) => c[0] === "renderWindowItems"), [["renderWindowItems", 0, 2, false]], "…and the build is told it may not take either");
});

test("every anchoring paint takes: atBottom passed with no flag (the default: atBottom was passed) and the flag passed true (the toggle's keep holding a row, appendActive's follow or anchor) each call applyMeasure once and hand the build anchored true", () => {
  for (const args of [["A", true], ["A", false], ["A", undefined, true]] as Array<[string, boolean | undefined, boolean?]>) {
    const w = world(["user", "assistant"], [ev(0), ev(1)], [ev(0), ev(1)], 2, 0);
    w.v.stale = true;
    w.sync(...args);
    assert.deepEqual(w.calls.filter((c) => c[0] === "applyMeasure"), [["applyMeasure"]], "one take for " + JSON.stringify(args));
    assert.deepEqual(w.calls.filter((c) => c[0] === "renderWindowItems"), [["renderWindowItems", 0, 2, true]], "…and the build is told it anchors: " + JSON.stringify(args));
    assert.ok(w.calls.findIndex((c) => c[0] === "applyMeasure") < w.calls.findIndex((c) => c[0] === "renderWindowItems"), "the take comes first, so the build's spacers read it");
  }
});

test("renderWindowItems takes a parked figure only when its caller says it anchors: the flag absent or false calls applyMeasure never, true calls it once before the build", () => {
  const s = { events: [{ kind: "user" }, { kind: "assistant" }], status: { state: "ready" } };
  for (const [flag, expect] of [[undefined, []], [false, []], [true, [["applyMeasure"]]]] as Array<[boolean | undefined, Call[]]>) {
    const calls: Call[] = []; const build = liftBuild(calls);
    const v: any = { el: new FakeEl("div") };
    if (flag === undefined) build(v, s, [ev(0), ev(1)], 0, 2, false); else build(v, s, [ev(0), ev(1)], 0, 2, false, flag);
    assert.deepEqual(calls.filter((c) => c[0] === "applyMeasure"), expect, "the take under flag " + flag);
    if (flag) assert.equal(calls[0][0], "applyMeasure", "…before the build, so the spacers below read what was taken");
    assert.deepEqual(calls.filter((c) => c[0] === "appendItem"), [["appendItem", 0], ["appendItem", 1]], "the build ran whatever the flag");
    assert.equal(v.winStart, 0); assert.equal(v.winEnd, 2); assert.equal(v.rendered, 2);
    assert.deepEqual(calls[calls.length - 1], ["sizeSpacers"], "…and sized its spacers last");
  }
});

test("normal mode's exact tail with a GAP at or past the first changed event's unit: the block draws the gap through gapElement (recorded), tagged by its unit, between the events around it, and patches the footers from the change with the list (the maintainer's round 6 ruling, regression-2: the harness stubbed a removed name and nothing for gapElement, so this world threw a ReferenceError at the head that round ruled on)", () => {
  // the reply at event 1 edited (from = 1), a gap standing before event 2 in a three-event view: units e0, e1, gap, e2. v.rendered 1, not 0 (a
  // first build takes the rebuild path and never reaches this block); a gap below `from` is untouched, so the trigger is a gap at or past it
  const gap: DisplayItem = { kind: "gap", lo: 10, hi: 12, before: 2 };
  const w = world(["user", "assistant", "user"], [ev(0), ev(1), gap, ev(2)], [ev(0), ev(1), gap, ev(2)], 1, 0, true, false);
  w.sync("A", true);
  assert.deepEqual(w.calls.filter((c) => c[0] === "trim"), [["trim", 1]], "one trim, from the changed event's unit");
  assert.deepEqual(w.calls.filter((c) => c[0] === "renderEvent" || c[0] === "gapElement"), [["renderEvent", "e1"], ["gapElement", 10, 12], ["renderEvent", "e2"]], "the gap drawn between the events around it, through gapElement, as appendItem draws it (no divider, no epoch)");
  const g = w.v.el.children.find((c: FakeEl) => c.className === "tx-gap");
  assert.ok(g, "the gap node stands in the view"); assert.equal(g!.dataset.unit, "2", "…tagged by its unit, the list's index");
  assert.deepEqual(w.calls.filter((c) => c[0] === "patchWorkedFooters"), [["patchWorkedFooters", 1, true, 4]], "the footers patched from the change (v.rendered), with the unit list (four items, the gap among them)");
  assert.deepEqual(w.calls.filter((c) => c[0] === "appendItem" || c[0] === "renderWindowItems" || c[0] === "evict" || c[0] === "reseed"), [], "no compact helper, no rebuild");
  assert.equal(w.v.rendered, 3); assert.equal(w.v.winEnd, 4);
});

test("every name the seam's prelude stubs is one render.ts declares at module level (a function, a class, a variable or an import binding), read off both trees, so a stub of a name the renderer no longer has reds here instead of standing as a dead line; two names are the harness's own and exempt by name, H (the hooks object) and HTMLElement (a DOM global the renderer never declares) (the maintainer's round 6 ruling, regression-2)", () => {
  const bind = (n: ts.BindingName, into: string[]): void => { if (ts.isIdentifier(n)) into.push(n.text); else for (const e of n.elements) if (!ts.isOmittedExpression(e)) bind(e.name, into); };
  const prelude = ts.createSourceFile("prelude.js", SEAM_PRELUDE, ts.ScriptTarget.Latest, true, ts.ScriptKind.JS);
  const stubbed: string[] = [];
  for (const st of prelude.statements) { if (ts.isVariableStatement(st)) for (const d of st.declarationList.declarations) bind(d.name, stubbed); else if (ts.isFunctionDeclaration(st) && st.name) stubbed.push(st.name.text); }
  const kindOf = (st: ts.Statement): string => ts.isVariableStatement(st) ? "a variable statement" : ts.isFunctionDeclaration(st) ? "a function declaration" : ts.isClassDeclaration(st) ? "a class declaration" : ts.SyntaxKind[st.kind];
  const unread = prelude.statements.filter((st) => !ts.isVariableStatement(st) && !(ts.isFunctionDeclaration(st) && st.name)).map(kindOf);
  assert.deepEqual(unread, [], "every statement of the prelude is a variable statement or a named function declaration, the two forms this pin reads its names from: a stub in another form (a class, an expression statement) would be a name the pin never checks against render.ts, so it reds here by kind (the author's fixer pass over the pass after the maintainer's round 6, its verifier (b), which found a floor on the count standing where this belongs)");
  assert.ok(stubbed.includes("gapElement") && stubbed.includes("appendItem"), "the prelude's stubbed names, read off its own tree, every statement read (" + stubbed.length + "): " + stubbed.join(", "));
  const sf = ts.createSourceFile("render.ts", RENDER, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);
  const declared: string[] = [];
  for (const st of sf.statements) {
    if ((ts.isFunctionDeclaration(st) || ts.isClassDeclaration(st)) && st.name) declared.push(st.name.text);
    else if (ts.isVariableStatement(st)) for (const d of st.declarationList.declarations) bind(d.name, declared);
    else if (ts.isImportDeclaration(st) && st.importClause) {
      const c = st.importClause; if (c.name) declared.push(c.name.text);
      const nb = c.namedBindings; if (nb) { if (ts.isNamespaceImport(nb)) declared.push(nb.name.text); else for (const e of nb.elements) declared.push(e.name.text); }
    }
  }
  const has = new Set(declared);
  const EXEMPT: Record<string, string> = { H: "the harness's hooks object", HTMLElement: "a DOM global the renderer never declares" };
  const missing = stubbed.filter((n) => !(n in EXEMPT) && !has.has(n));
  assert.deepEqual(missing, [], "a name the prelude stubs that render.ts declares nowhere at module level: a stub of a removed function is dead, and the harness no longer models the renderer it lifts");
  for (const n of Object.keys(EXEMPT)) assert.ok(stubbed.includes(n) && !has.has(n), n + " is exempt because it is " + EXEMPT[n] + ", and render.ts indeed declares it nowhere");
  assert.ok(has.has("gapElement") && has.has("appendItem") && has.has("dayWalkBefore"), "the renderer declares the block's collaborators the prelude stubs");
});

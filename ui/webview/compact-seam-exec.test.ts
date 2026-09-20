// Compact mode's tail seam, EXECUTED (PR E review round 0): syncViewInner lifted from render.ts over stubs that record what the seam
// hands its collaborators, the way chat-exact-tail-exec.test.ts lifts chatTail. chat-compact-tail.test.ts drives the plan and the trim
// and pins the seam's text; this file drives the seam's two arguments the text pins could not execute: the rail reference the first
// re-rendered unit is seeded with (railChainBefore over the view's window start, never a scan of s.events: rail-chain.test.ts) and the
// footer patch's `from` (the first CHANGED event when no unit reaches it, a hidden thinking block, else the first re-rendered event,
// whichever is earlier). Review round 1b added the measured figure's rule over takers, executed: a figure is taken ONLY by a paint that
// anchors the reader (the `anchored` flag: atBottom passed, or true) and EVERY anchoring paint takes one; the stubs record the take and the
// flag the build is handed, and renderWindowItems is lifted alone for its own gate. Synthetic events.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
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

function liftSeam(sessions: Map<string, any>, views: Map<string, any>, itemsOf: (s: any) => DisplayItem[], calls: Call[]) {
  const js = liftBetween("function syncViewInner(", "function patchWorkedFooters(");
  const prelude = `
    const H = HOOKS;
    let renderingSid = null, renderingOwnerSid = null;
    const subParts = () => null;
    const sessions = H.sessions, views = H.views;
    const ensureView = (id) => views.get(id);
    const settings = { compact: true };
    const displayItems = (s) => H.itemsOf(s);
    const WINDOW_TAIL = 80;
    const lastCompactUnit = () => 0;
    const renderWindowItems = (v, s, items, ws, we, working, anchored) => { H.calls.push(["renderWindowItems", ws, we, anchored]); };
    const applyMeasure = (v) => { H.calls.push(["applyMeasure"]); return false; }; const redrawGapUnits = () => {};
    const sizeSpacers = () => { H.calls.push(["sizeSpacers"]); };
    const patchWorkedFooters = (v, s, from, working, items) => { H.calls.push(["patchWorkedFooters", from, working, items ? items.length : null]); };
    const compactTailPlan = H.compactTailPlan;
    const trimUnitsFrom = (host, u0) => { H.calls.push(["trim", u0]); return 0; };
    const railChainBefore = (s, items, winStart, u0) => { H.calls.push(["railChainBefore", winStart, u0]); return H.SENTINEL; };
    const dayWalkBefore = () => new H.DayWalk();
    const turnOfEvents = () => null;
    const appendItem = (v, s, items, u, prevEpoch) => { H.calls.push(["appendItem", u, prevEpoch]); return prevEpoch; };
    const evictCompactTop = (v, ws) => { H.calls.push(["evict", ws]); if (ws <= (v.winStart ?? 0)) return false; v.winStart = ws; return true; };   // the real one's answer: whether it evicted
    const reseedWindowHead = (v, s, items) => { H.calls.push(["reseed", v.winStart, items.length]); };
    const itemFirstEvent = (it) => (it.kind === "toolgroup" || it.kind === "noticegroup" ? it.indices[0] : it.kind === "gap" ? it.before : it.index);
    // normal mode's names: never reached in a compact world
    const dayWalkBeforeEvent = () => new H.DayWalk(); const prevTimedEpoch = () => null; const eventEpoch = () => null; const dayDividerFor = () => null;
    const renderEvent = () => new H.FakeEl("div"); const turnWorkedSecs = () => null; const stampWalkDay = () => {};
    const HTMLElement = H.FakeEl; const el = (t, c) => new H.FakeEl(t, c || "");
  `;
  return new Function("HOOKS", prelude + js + "\nreturn syncViewInner;")({ sessions, views, itemsOf, calls, compactTailPlan, DayWalk, FakeEl, SENTINEL }) as (id: string, atBottom?: boolean, anchored?: boolean) => any;
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
/** A world: a session over `kinds`, its view built from `prevItems` over the whole list (winStart given), the first changed event `from`. */
function world(kinds: string[], prevItems: DisplayItem[], itemsNow: DisplayItem[], from: number, winStart = 0, working = true) {
  const calls: Call[] = [];
  const s = { id: "A", events: kinds.map((kind, i) => ({ kind, uuid: "e" + i, ts: "2026-09-19T10:00:0" + (i % 10) + "Z" })), status: { state: working ? "working" : "ready" } };
  const host = new FakeEl("div");
  for (let u = winStart; u < prevItems.length; u++) { const n = new FakeEl("div", "turn"); n.dataset.unit = String(u); host.appendChild(n); }
  const v: any = { el: host, rendered: from, stale: false, winStart, winEnd: prevItems.length, unitTotal: prevItems.length, units: prevItems, working: !working, shown: true, stick: true };
  const sync = liftSeam(new Map([["A", s]]), new Map([["A", v]]), () => itemsNow, calls);
  return { calls, s, v, sync };
}

test("the seam seeds the first re-rendered unit with railChainBefore over the view's window start, and appendItem receives that reference", () => {
  // the reply at unit 2 streams behind a collapsed run; the window opened at unit 1 (a top spacer stands for the prompt)
  const w = world(["user", "tool", "tool", "assistant"], [ev(0), tg(1, 2), ev(3)], [ev(0), tg(1, 2), ev(3)], 3, 1);
  w.sync("A", true);
  assert.deepEqual(w.calls.filter((c) => c[0] === "railChainBefore"), [["railChainBefore", 1, 2]], "the chain from the window's start to u0");
  assert.deepEqual(w.calls.filter((c) => c[0] === "appendItem"), [["appendItem", 2, SENTINEL]], "the reply's unit re-rendered from that reference");
  assert.deepEqual(w.calls.filter((c) => c[0] === "trim"), [["trim", 2]]);
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

test("a change below a browsed window grows the bottom spacer and touches no node: exactly sizeSpacers, no trim, no appendItem, no rebuild", () => {
  // six units built, a reply landed as the seventh; the window browsed away from the tail (winEnd lowered to 4 by hand, as a landing leaves it)
  const kinds = ["user", "assistant", "user", "assistant", "user", "assistant", "assistant"];
  const prev = Array.from({ length: 6 }, (_, i) => ev(i)), now = prev.concat([ev(6)]);
  const w = world(kinds, prev, now, 6, 0);
  w.v.winEnd = 4;
  w.sync("A");
  assert.deepEqual(w.calls, [["sizeSpacers"]], "the spacer re-size alone");
  assert.equal(w.v.spacerCountBot, 3, "total less winEnd: the units the bottom spacer stands for");
  assert.equal(w.v.rendered, 7); assert.equal(w.v.unitTotal, 7); assert.deepEqual(w.v.units, now);
  assert.equal(w.v.el.children.length, 6, "no node touched");
});

// ── the measured figure: taken only by a paint that anchors the reader, and by every one of them (review round 1b) ──────────────────

test("a sync with no flag (a switch's, a landing's, a hidden prebuild's) takes no measured figure and tells its build so: applyMeasure is never called and renderWindowItems is handed anchored false", () => {
  // a stale view, so the paint takes the rebuild road: the flag reaches the build
  const w = world(["user", "assistant"], [ev(0), ev(1)], [ev(0), ev(1)], 2, 0);
  w.v.stale = true;
  w.sync("A");
  assert.deepEqual(w.calls.filter((c) => c[0] === "applyMeasure"), [], "no take in a paint that does not anchor the reader");
  assert.deepEqual(w.calls.filter((c) => c[0] === "renderWindowItems"), [["renderWindowItems", 0, 2, false]], "…and the build is told it may not take either");
});

test("every anchoring paint takes: atBottom passed (appendActive's follow or anchor restore, either value) and the flag passed true (the toggle's keep) each call applyMeasure once and hand the build anchored true", () => {
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

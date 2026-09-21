// Compact mode's tail path by unit (PR E, 2026-09-19). Before it, every paint that changed or appended an event in compact
// mode (the default) rebuilt the whole rendered window: renderWindowItems removed every child and re-rendered every unit of
// the current window (at least 80) once per animation frame while a turn streamed. Now syncViewInner asks the plan
// (chat-compact-tail.ts, pure) for the first unit to re-render and trims from there by data-unit, as normal mode's tail has
// done since the exact-tail change. Three layers here: the plan EXECUTED over every rule; the trim and the eviction LIFTED
// from render.ts and run over a fake DOM (the models-rev.test.ts / chat-exact-tail-exec.test.ts pattern); a replica of N
// streamed frames over an 80-unit window that counts the nodes each frame replaces (the rebuild replaced them all); and
// source pins on the seam's wiring, which no harness lifts. Synthetic events; the browser leg
// (tests/test_history_regions_browser.py, ServedCompactStream) counts the same replacement end to end on the served page.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { compactTailPlan, firstDifferingUnit, firstUnitReaching, itemLastEvent, sameItem, type TailPlan } from "./chat-compact-tail";
import { compactDisplay, type DisplayItem } from "./compact";
import { hideEdges } from "../test-dom-shim";

const requireCjs = createRequire(__filename);
const RENDER = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "render.ts"), "utf8");

const ev = (index: number): DisplayItem => ({ kind: "event", index });
const tg = (...indices: number[]): DisplayItem => ({ kind: "toolgroup", indices });
const ng = (...indices: number[]): DisplayItem => ({ kind: "noticegroup", indices });
const gap = (lo: number, hi: number, before: number): DisplayItem => ({ kind: "gap", lo, hi, before });
/** A world at the tail: the window covers every unit, no bottom spacer, not stale, the DOM built from `prev`. */
function atTail(prev: DisplayItem[], items: DisplayItem[], from: number, winStart = 0): Parameters<typeof compactTailPlan>[0] {
  return { prev, items, from, winStart, winEnd: prev.length, unitTotal: prev.length, stale: false, bottomSpacer: false };
}
const append = (u0: number): TailPlan => ({ kind: "append", u0 });

// ── the plan ─────────────────────────────────────────────────────────────────────────────────────

test("a growing reply is its own unit: the same item list, the first changed event names the unit to re-render from", () => {
  const items = [ev(0), tg(1, 2), ev(3)];   // a prompt, a folded run of two tools, the reply
  assert.deepEqual(compactTailPlan(atTail(items.slice(), items, 3)), append(2), "the reply's unit, nothing above it");
  assert.equal(firstDifferingUnit(items, items.slice()), -1, "the lists are the same list");
});

test("a new event appends one unit; a tool joining a lone tool, or extending a run, re-renders from the run's unit, never a rebuild", () => {
  assert.deepEqual(compactTailPlan(atTail([ev(0), ev(1)], [ev(0), ev(1), ev(2)], 2)), append(2), "an appended reply");
  // event{1} (a lone tool) becomes toolgroup{[1, 2]}: the lists part at unit 1, and that is where the trim starts
  assert.deepEqual(compactTailPlan(atTail([ev(0), ev(1)], [ev(0), tg(1, 2)], 2)), append(1), "a run forming");
  assert.deepEqual(compactTailPlan(atTail([ev(0), tg(1, 2)], [ev(0), tg(1, 2, 3)], 3)), append(1), "a run extending: the same unit, its item changed");
  assert.deepEqual(compactTailPlan(atTail([ev(0), ev(1)], [ev(0), ng(1, 2)], 2)), append(1), "the notice twin");
  // the real fold: compactDisplay over kinds, a tool landing after a lone tool
  const before = compactDisplay(["user", "assistant", "tool"]);
  const after = compactDisplay(["user", "assistant", "tool", "tool"]);
  assert.deepEqual(after, [ev(0), ev(1), tg(2, 3)]);
  assert.deepEqual(compactTailPlan(atTail(before, after, 3)), append(2), "from the unit that held the lone tool");
});

test("a change inside a run, or at a hidden event, re-renders from the unit that reaches it; a change past every visible event renders nothing", () => {
  const items = [ev(0), tg(1, 3)];   // events 1 and 3 are tools, 2 a thinking block compact mode never shows
  assert.equal(itemLastEvent(tg(1, 3)), 3); assert.equal(itemLastEvent(ev(7)), 7); assert.equal(itemLastEvent(gap(0, 9, 4)), -1, "a gap holds no event");
  assert.equal(firstUnitReaching(items, 2), 1, "the run reaches past the hidden event");
  assert.deepEqual(compactTailPlan(atTail(items.slice(), items, 2)), append(1));
  const trailing = [ev(0), ev(1)];   // events: a prompt, a reply, then a thinking block at 2 that has no unit
  assert.equal(firstUnitReaching(trailing, 2), 2, "no unit reaches it: the list's length");
  assert.deepEqual(compactTailPlan(atTail(trailing.slice(), trailing, 2)), append(2), "trim nothing, render nothing, take the bookkeeping");
});

test("the rebuild stays for a stale view, a view with no unit record, and a record that does not describe the DOM", () => {
  const items = [ev(0), ev(1)];
  assert.deepEqual(compactTailPlan({ ...atTail(items, items, 1), stale: true }), { kind: "rebuild", why: "stale" });
  assert.deepEqual(compactTailPlan({ ...atTail(items, items, 1), prev: undefined }), { kind: "rebuild", why: "no-record" });
  assert.deepEqual(compactTailPlan({ ...atTail(items, items, 1), unitTotal: 5 }), { kind: "rebuild", why: "no-record" }, "a record of another build's length");
  assert.deepEqual(compactTailPlan({ ...atTail(items, items, 1), unitTotal: undefined }), { kind: "rebuild", why: "no-record" });
});

test("a change among the hidden units above the window rebuilds; a bottom spacer under the window rebuilds; a gap at or past the start rebuilds", () => {
  const prev = [ev(0), ev(1), ev(2), ev(3)];
  const changedAbove = [ev(0), ng(1, 2), ev(3)];   // units 1 and 2 folded: the lists part at unit 1, above a window starting at 2
  assert.equal(firstDifferingUnit(prev, changedAbove), 1);
  assert.deepEqual(compactTailPlan(atTail(prev, changedAbove, 3, 2)), { kind: "rebuild", why: "below-window" });
  assert.deepEqual(compactTailPlan({ ...atTail(prev, prev, 3), bottomSpacer: true }), { kind: "rebuild", why: "bottom-spacer" });
  const withGap = [ev(0), gap(0, 16, 1), ev(1), ev(2)];
  assert.deepEqual(compactTailPlan(atTail(withGap.slice(), withGap, 0)), { kind: "rebuild", why: "gap" }, "a gap past the start: keyed by unit, not re-appended");
  assert.deepEqual(compactTailPlan(atTail(withGap.slice(), withGap, 2)), append(3), "a gap above the start is left where it is");
});

test("a window browsed away from the tail grows its bottom spacer when the change lies below it and rebuilds when it lies inside", () => {
  const items = Array.from({ length: 10 }, (_, i) => ev(i));
  const browsed = { prev: items, items, from: 8, winStart: 0, winEnd: 6, unitTotal: 10, stale: false, bottomSpacer: true };
  assert.deepEqual(compactTailPlan(browsed), { kind: "spacer" }, "below the window: no node touched");
  assert.deepEqual(compactTailPlan({ ...browsed, from: 4 }), { kind: "rebuild", why: "inside-browsed" });
  const grown = items.concat([ev(10)]);
  assert.deepEqual(compactTailPlan({ ...browsed, items: grown, from: 10 }), { kind: "spacer" }, "a new event below a browsed window");
});

test("sameItem compares the unit's shape: kind, the event, the members in order, a gap's turns and its place", () => {
  assert.ok(sameItem(ev(3), ev(3))); assert.ok(!sameItem(ev(3), ev(4))); assert.ok(!sameItem(ev(3), tg(3)));
  assert.ok(sameItem(tg(1, 2), tg(1, 2))); assert.ok(!sameItem(tg(1, 2), tg(1, 2, 3))); assert.ok(!sameItem(tg(1, 2), tg(2, 1)));
  assert.ok(!sameItem(tg(1, 2), ng(1, 2)), "a tool run and a notice run are different units over the same events");
  assert.ok(sameItem(gap(0, 16, 3), gap(0, 16, 3))); assert.ok(!sameItem(gap(0, 16, 3), gap(0, 32, 3))); assert.ok(!sameItem(gap(0, 16, 3), gap(0, 16, 4)));
  assert.equal(firstDifferingUnit([ev(0), ev(1)], [ev(0), ev(1), ev(2)]), 2, "a longer list differs at the first extra unit");
  assert.equal(firstDifferingUnit([ev(0), ev(1), ev(2)], [ev(0), ev(1)]), 2, "…and a shorter one at its end");
});

// ── the trim and the eviction, lifted from render.ts ─────────────────────────────────────────────

/** A render.ts span, transpiled with esbuild at run time, required dynamically so the test bundle does not bundle esbuild. */
function liftBetween(startAnchor: string, endAnchor: string): string {
  const a = RENDER.indexOf(startAnchor), b = RENDER.indexOf(endAnchor, a);
  assert.ok(a > 0 && b > a, `anchors not found: ${startAnchor.slice(0, 40)} or ${endAnchor.slice(0, 40)} moved; re-anchor`);
  return requireCjs("esbuild").transformSync(RENDER.slice(a, b), { loader: "ts" }).code;
}

/** Enough of an element for the trim and the eviction: a class list, data-unit, a parent's child list and the sibling walk. */
class FakeEl {
  children!: FakeEl[]; parent: FakeEl | null = null; dataset: Record<string, string> = {}; style: Record<string, string> = {};
  constructor(public tag: string, public className = "") {
    Object.defineProperty(this, "children", { value: [], writable: true, enumerable: false, configurable: true });
    hideEdges(this);
  }
  get classList() { const cls = this.className.split(/\s+/); return { contains: (c: string) => cls.includes(c) }; }
  get parentElement(): FakeEl | null { return this.parent; }
  get firstChild(): FakeEl | null { return this.children[0] ?? null; }
  get lastChild(): FakeEl | null { return this.children[this.children.length - 1] ?? null; }
  get nextSibling(): FakeEl | null { const p = this.parent; if (!p) return null; const i = p.children.indexOf(this); return i >= 0 ? p.children[i + 1] ?? null : null; }
  get previousSibling(): FakeEl | null { const p = this.parent; if (!p) return null; const i = p.children.indexOf(this); return i > 0 ? p.children[i - 1] : null; }
  appendChild(c: FakeEl): FakeEl { c.parent?.removeChild(c); c.parent = this; this.children.push(c); return c; }
  insertBefore(c: FakeEl, ref: FakeEl | null): FakeEl { c.parent?.removeChild(c); c.parent = this; const i = ref ? this.children.indexOf(ref) : -1; if (i < 0) this.children.push(c); else this.children.splice(i, 0, c); return c; }
  removeChild(c: FakeEl): void { this.children = this.children.filter((x) => x !== c); c.parent = null; }
  querySelector(sel: string): FakeEl | null {
    const m = /^(?::scope > )?\.([\w-]+)$/.exec(sel);
    if (m) return this.children.find((c) => c.classList.contains(m[1])) ?? null;
    const u = /^:scope > \[data-unit(?:="(\d+)")?\] > \.([\w-]+)$/.exec(sel);   // the re-seed's: the window's first marker-bearing node (any unit, or one named)
    if (!u) throw new Error("unsupported selector " + sel);
    for (const c of this.children) { if (c.dataset.unit == null || (u[1] != null && c.dataset.unit !== u[1])) continue; const hit = c.children.find((x) => x.classList.contains(u[2])); if (hit) return hit; }
    return null;
  }
}
type Lifted = { unitOfNode: (n: FakeEl) => number; trimUnitsFrom: (host: FakeEl, u0: number) => number; evictCompactTop: (v: any, newWinStart: number) => boolean; reseedWindowHead: (v: any, s: any, items: any[]) => void };
/** The trim, the eviction and its re-seed lifted; `seed` is what the stubbed railChainBefore answers, `seeds` records the (window start,
 *  marker's unit) pairs it is asked for, `painted` records paintMarker's calls. */
function liftTrim(hooks: { sized: number[]; seed?: number | null; seeds?: Array<[number, number]>; painted?: Array<[number, number | null]> }): Lifted {
  const js = liftBetween("function unitOfNode(", "/** The estimated height of the units [from, to)");
  const prelude = `
    const H = HOOKS;
    const HTMLElement = H.FakeEl;
    const el = (tag, cls) => new H.FakeEl(tag, cls || "");
    const sizeSpacers = (v) => { H.sized.push(v.winStart); };
    const railChainBefore = (s, items, ws, um) => { H.seeds.push([ws, um]); return H.seed === undefined ? null : H.seed; };
    const paintMarker = (m, epoch, prev, now) => { (H.painted || []).push([epoch, prev]); };
    const Date = { now: () => 0 };
  `;
  return new Function("HOOKS", prelude + js + "\nreturn { unitOfNode, trimUnitsFrom, evictCompactTop, reseedWindowHead };")({ ...hooks, FakeEl, seeds: hooks.seeds ?? [] }) as Lifted;
}
/** A view host holding units [winStart, winEnd) with a top spacer when winStart > 0; a unit owns one node, or two when `dividerAt` names it. */
function window(winStart: number, winEnd: number, dividerAt: number[] = []): FakeEl {
  const host = new FakeEl("div");
  if (winStart > 0) host.appendChild(new FakeEl("div", "tx-spacer tx-spacer-top"));
  for (let u = winStart; u < winEnd; u++) {
    if (dividerAt.includes(u)) { const d = new FakeEl("div", "day-divider"); d.dataset.unit = String(u); host.appendChild(d); }
    const n = new FakeEl("div", "turn"); n.dataset.unit = String(u); host.appendChild(n);
  }
  return host;
}
const unitsIn = (host: FakeEl): number[] => host.children.filter((c) => c.dataset.unit != null).map((c) => Number(c.dataset.unit));

test("the trim drops every node from the unit onward off the end, dividers included, and a spacer ends the walk on its own", () => {
  const { unitOfNode, trimUnitsFrom } = liftTrim({ sized: [] });
  const host = window(100, 180, [150, 179]);   // 80 units; two of them open a day
  assert.equal(unitOfNode(host.children[0]), -1, "the spacer carries no unit");
  assert.equal(trimUnitsFrom(host, 179), 2, "the streaming unit: its divider and its row");
  assert.deepEqual(unitsIn(host).slice(-2), [177, 178], "the units before it stand");
  assert.equal(trimUnitsFrom(host, 150), 30, "units 150..178 (29 rows), plus 150's divider");
  assert.equal(host.children.length, 1 + 50);
  assert.equal(trimUnitsFrom(host, 0), 50, "…down to the spacer, which stops the walk");
  assert.equal(host.children.length, 1); assert.ok(host.children[0].classList.contains("tx-spacer-top"));
  assert.equal(trimUnitsFrom(host, 0), 0, "nothing left to trim");
});

test("a foreign child (a hover's rail band, appended as the thread's last child) neither ends the trim nor counts: the walk reaches the units behind it and drops the band; a spacer still ends it", () => {
  // drawRailBand appends the band to the thread (host.appendChild) on every rail, dot or feed hover, with a class and no data-unit; the
  // walk stopped at it, trimmed nothing and re-appended the tail units on top of stale copies of themselves (the maintainer's round 1 ruling, high)
  const { trimUnitsFrom } = liftTrim({ sized: [] });
  const host = window(100, 180);
  host.appendChild(new FakeEl("div", "rail-band rail-band-local"));
  assert.equal(trimUnitsFrom(host, 179), 1, "the streaming unit's one row, the band not counted");
  assert.deepEqual(unitsIn(host).slice(-1), [178], "the units before it stand");
  assert.equal(host.children.filter((c) => c.classList.contains("rail-band")).length, 0, "the band is dropped (a hover redraws it on the next mouseenter), so nothing foreign stands among the units");
  assert.equal(host.children.length, 1 + 79, "the spacer and 79 units");
  // a band behind a unit below u0: the walk still ends at that unit, and the band, met first, is dropped
  host.appendChild(new FakeEl("div", "rail-band"));
  assert.equal(trimUnitsFrom(host, 179), 0, "nothing at or past 179 is left");
  assert.equal(host.children.filter((c) => c.classList.contains("rail-band")).length, 0);
  assert.equal(unitsIn(host).length, 79);
  // a band over a spacer: the spacer ends the walk as before
  host.appendChild(new FakeEl("div", "rail-band rail-band-local"));
  assert.equal(trimUnitsFrom(host, 0), 79, "every unit, down to the spacer");
  assert.equal(host.children.length, 1); assert.ok(host.children[0].classList.contains("tx-spacer-top"));
});

test("the eviction keeps the window's span after an append at the bottom: the leading units leave, the top spacer stands for them and is re-sized", () => {
  const sized: number[] = [];
  const { evictCompactTop } = liftTrim({ sized });
  const host = window(100, 181);   // 81 units after one appended at the tail of an 80-unit window
  const v: any = { el: host, winStart: 100, winEnd: 181, spacerCount: 100 };
  assert.equal(evictCompactTop(v, 101), true, "it evicted (the caller re-seeds the promoted head)");
  assert.deepEqual(unitsIn(host)[0], 101, "unit 100 left");
  assert.equal(host.children.length, 1 + 80, "the spacer and 80 units");
  assert.equal(v.winStart, 101); assert.equal(v.spacerCount, 101);
  assert.deepEqual(sized, [101], "the spacers were re-sized once, after the bookkeeping");
  assert.equal(evictCompactTop(v, 101), false, "nothing to evict");
  assert.deepEqual(sized, [101], "nothing to evict: no re-size");
  assert.equal(evictCompactTop(v, 90), false);
  assert.equal(v.winStart, 101, "a smaller start is not an eviction");
  // a window that had no spacer (winStart 0) gets one when its first units leave
  const whole = window(0, 81);
  const v2: any = { el: whole, winStart: 0, winEnd: 81, spacerCount: 0 };
  evictCompactTop(v2, 1);
  assert.ok(whole.children[0].classList.contains("tx-spacer-top"), "a top spacer was put in front");
  assert.deepEqual(unitsIn(whole)[0], 1);
});

test("the eviction's re-seed: the window's first marker is repainted against the reference a build hands its unit (railChainBefore from the new start), data-prev with it; the head unit's own marker when it has one, the first marker after a marker-less head (a gap) otherwise; nothing when it already carries it, or when no marker stands in the window", () => {
  // the promoted unit was drawn mid-window with the chain's reference (8000); a build of the window seeds it with the seed at the new start (4242)
  const painted: Array<[number, number | null]> = [], seeds: Array<[number, number]> = [];
  const { evictCompactTop, reseedWindowHead } = liftTrim({ sized: [], seed: 4242, seeds, painted });
  const host = window(100, 181, [101]);   // unit 101 opens a day: its divider precedes its row (the divider carries no marker)
  const row = host.children.find((c) => c.dataset.unit === "101" && !c.classList.contains("day-divider"))!;
  const m = new FakeEl("div", "time-marker"); m.dataset.epoch = "9000"; m.dataset.prev = "8000"; row.appendChild(m);
  const later = new FakeEl("div", "time-marker"); later.dataset.epoch = "9500"; later.dataset.prev = "9000"; host.children.find((c) => c.dataset.unit === "102")!.appendChild(later);
  const v: any = { el: host, winStart: 100, winEnd: 181, spacerCount: 100 };
  assert.ok(evictCompactTop(v, 101));
  reseedWindowHead(v, {}, []);
  assert.equal(m.dataset.prev, "4242", "the reference is the build's");
  assert.deepEqual(seeds, [[101, 101]], "the chain asked from the new start to the marker's own unit: the seed itself");
  assert.deepEqual(painted, [[9000, 4242]], "the marker repainted against it (its epoch, the reference)");
  assert.equal(later.dataset.prev, "9000", "the marker of the unit after the head is not touched: it chains from the head on both paths");
  reseedWindowHead(v, {}, []);
  assert.deepEqual(painted, [[9000, 4242]], "already the build's: nothing painted");
  // a seed of null (the transcript's start): the reference is empty, as timeMarker stamps it
  const { reseedWindowHead: reseedNull } = liftTrim({ sized: [], seed: null, painted });
  reseedNull(v, {}, []);
  assert.equal(m.dataset.prev, ""); assert.deepEqual(painted.slice(-1), [[9000, null]]);
  // the head unit carries no marker (a gap element: no epoch, no row of its own): the first marker after it is the one re-seeded, against
  // the chain from the new start to ITS unit (the seed carried through the gap, railExit's identity there); re-seeding the head's own
  // marker found none and left this one on the chain's reference (the author's second pass over round 1)
  const gapped = window(100, 181); const seeds2: Array<[number, number]> = [], painted2: Array<[number, number | null]> = [];
  const { evictCompactTop: evict2, reseedWindowHead: reseed2 } = liftTrim({ sized: [], seed: 5151, seeds: seeds2, painted: painted2 });
  const gapEl = gapped.children.find((c) => c.dataset.unit === "101")!; gapEl.className = "tx-gap";
  const m2 = new FakeEl("div", "time-marker"); m2.dataset.epoch = "9100"; m2.dataset.prev = "8100"; gapped.children.find((c) => c.dataset.unit === "102")!.appendChild(m2);
  const v2: any = { el: gapped, winStart: 100, winEnd: 181, spacerCount: 100 };
  assert.ok(evict2(v2, 101));
  reseed2(v2, {}, []);
  assert.deepEqual(seeds2, [[101, 102]], "the chain asked from the gap (the new start) to the first marker's unit");
  assert.equal(m2.dataset.prev, "5151", "the first marker after the gap carries the build's reference");
  assert.deepEqual(painted2, [[9100, 5151]]);
  // no marker anywhere in the window (every row untimed): nothing to re-seed, nothing painted
  const bare = window(100, 181); const v3: any = { el: bare, winStart: 100, winEnd: 181, spacerCount: 100 };
  const before = painted.length;
  evictCompactTop(v3, 101); reseedWindowHead(v3, {}, []);
  assert.equal(painted.length, before);
});

// ── the replica: N streamed frames over an 80-unit window ────────────────────────────────────────

test("replica: frames of a growing reply over an 80-unit window replace the reply's nodes alone; a new unit replaces itself and the evicted one; the rebuild replaced every unit", () => {
  const { trimUnitsFrom, evictCompactTop } = liftTrim({ sized: [] });
  const WINDOW_TAIL = 80;
  const items: DisplayItem[] = Array.from({ length: 180 }, (_, i) => ev(i));
  const host = window(100, 180);
  const v: any = { el: host, winStart: 100, winEnd: 180, unitTotal: 180, spacerCount: 100, rendered: 180, stale: false, units: items.slice() };
  const replaced: number[] = [];
  const paint = (now: DisplayItem[], from: number) => {   // syncViewInner's compact branch, with appendItem standing in as one node per unit
    const total = now.length;
    const plan = compactTailPlan({ prev: v.units, items: now, from, winStart: v.winStart, winEnd: v.winEnd, unitTotal: v.unitTotal, stale: v.stale, bottomSpacer: false });
    assert.equal(plan.kind, "append", "every streamed frame at the tail takes the incremental path: " + JSON.stringify(plan));
    const span = Math.max(WINDOW_TAIL, v.winEnd - v.winStart);
    const u0 = (plan as { u0: number }).u0;
    let n = trimUnitsFrom(host, u0);
    for (let u = u0; u < total; u++) { const node = new FakeEl("div", "turn"); node.dataset.unit = String(u); host.appendChild(node); n++; }
    v.winEnd = total; v.spacerCount = v.winStart; v.unitTotal = total; v.rendered = total; v.units = now;
    const before = host.children.length;
    evictCompactTop(v, Math.max(0, total - span));
    replaced.push(n + (before - host.children.length));
  };
  assert.equal(host.children.length - 1, WINDOW_TAIL, "the window holds 80 units: a rebuild would replace 80 nodes a frame");
  for (let f = 0; f < 6; f++) paint(items, 179);              // the reply at unit 179 grows, six frames
  assert.deepEqual(replaced, [2, 2, 2, 2, 2, 2], "one node out, one node in, per frame");
  const grown = items.concat([ev(180)]);
  paint(grown, 180);                                           // a new unit lands at the tail
  assert.deepEqual(replaced.slice(-1), [2], "the new unit in, the evicted first unit out");
  assert.deepEqual([v.winStart, v.winEnd, host.children.length - 1], [101, 181, WINDOW_TAIL], "the span held");
  for (let f = 0; f < 3; f++) paint(grown, 180);
  assert.ok(replaced.every((n) => n <= 2), "no frame replaced more than two nodes: " + replaced.join(","));
});

// ── source pins on the seam ──────────────────────────────────────────────────────────────────────

test("syncViewInner asks the plan in compact mode between the fast path and the rebuild, and executes an append by trim, appendItem, footer patch, bookkeeping and eviction", () => {
  const sync = RENDER.slice(RENDER.indexOf("function syncViewInner("), RENDER.indexOf("function patchWorkedFooters("));
  const fast = sync.indexOf("if (v.rendered === len && !v.stale && v.el.childNodes.length > 0) return v;");
  const seam = sync.indexOf("if (settings.compact) {\n    const plan = compactTailPlan({ prev: v.units, items, from: v.rendered, winStart: v.winStart ?? 0, winEnd: v.winEnd ?? total, unitTotal: v.unitTotal,");
  const rebuild = sync.indexOf("if (settings.compact || v.stale) {");
  const normal = sync.indexOf("// Normal mode, pure append.");
  assert.ok(fast > 0 && seam > fast && rebuild > seam && normal > rebuild, "fast path, then the plan, then the rebuild, then normal mode");
  assert.match(sync, /stale: v\.stale, bottomSpacer: !!v\.el\.querySelector\(":scope > \.tx-spacer-bot"\) \}\);/, "the plan reads the stale mark and the bottom spacer off the view");
  assert.match(sync, /if \(plan\.kind === "spacer"\) \{\s*\n(?:\s*\/\/[^\n]*\n)*\s*patchWorkedFooters\(v, s, v\.rendered, working, items\);\s*\n\s*v\.spacerCountBot = total - \(v\.winEnd \?\? total\); v\.unitTotal = total; v\.rendered = len; v\.units = items; sizeSpacers\(v\); return v;/, "below a browsed window: the worked footers are patched from the first changed event (the pre-append v.rendered, the one render that reads later events; compact-seam-exec.test.ts runs it), then the bottom spacer grows, as normal mode's does");
  const app = sync.slice(sync.indexOf('if (plan.kind === "append") {'), rebuild);
  assert.match(app, /const span = Math\.max\(WINDOW_TAIL, \(v\.winEnd \?\? total\) - \(v\.winStart \?\? 0\)\);/, "the span is read before the append");
  // the first re-rendered unit is seeded with the rail chain a window build reaches there (railChainBefore: the seed at winStart advanced
  // over the units before u0 by appendItem's rule; rail-chain.test.ts executes it) and the day walk's mark (dayWalkBefore), never a scan of
  // s.events from the unit's first event, which sees hidden thinking rows and a collapsed run's last member (the author's pass 0)
  assert.match(app, /trimUnitsFrom\(v\.el, u0\);\s*\n(?:\s*\/\/[^\n]*\n)*\s*let prevEpoch = railChainBefore\(s, items, v\.winStart \?\? 0, u0\);\s*\n\s*const walk = dayWalkBefore\(s, items, u0\);/, "the trim, then the build's own chain and walk for the first re-rendered unit");
  assert.doesNotMatch(app, /prevTimedEpoch\(/, "the seam scans no events for its seed");
  assert.match(app, /const turns = s\.regions \? turnOfEvents\(s\) : null;\s*\n\s*for \(let u = u0; u < total; u\+\+\) prevEpoch = appendItem\(v, s, items, u, prevEpoch, walk, working, turns\);/, "the same appendItem loop as a window build");
  // the footer patch names the reply before the FIRST CHANGED EVENT (v.rendered, still pre-append here), as normal mode's `from` does: when no
  // unit reaches the change (u0 = total: a hidden thinking block) the first re-rendered event would be `len`, and the plan would name the
  // thinking row, which has no node, and never re-evaluate the reply before it (the author's pass 0, low; chat-exact-tail-exec.test.ts runs the shape)
  assert.match(app, /patchWorkedFooters\(v, s, Math\.min\(v\.rendered, u0 < total \? itemFirstEvent\(items\[u0\]\) : len\), working, items\);/, "the footer patch by unit, from the first changed event or the first re-rendered one, whichever is earlier");
  assert.ok(app.indexOf("patchWorkedFooters(v, s, Math.min(v.rendered,") < app.indexOf("v.rendered = len;"), "…read before the bookkeeping moves v.rendered to len");
  assert.match(app, /v\.winEnd = total; v\.spacerCount = v\.winStart \?\? 0; v\.spacerCountBot = 0; v\.unitTotal = total; v\.rendered = len; v\.units = items; v\.measureDue = true;/, "the bookkeeping records the units and asks for a measure");
  assert.match(app, /if \(!\(wasAtTail && atBottom === false\) && evictCompactTop\(v, Math\.max\(0, total - span\)\)\) reseedWindowHead\(v, s, items\);\s*\n\s*return v;/, "the top is evicted to the span unless the reader is scrolled up (keepTop), and an eviction re-seeds the promoted head unit (compact-tail-differential.test.ts executes the equivalence)");
  assert.match(RENDER, /v\.units = items;\s*\/\/[^\n]*\n\s*v\.measureDue = true;/, "renderWindowItems records the units its DOM holds");
  assert.match(RENDER, /import \{ compactTailPlan \} from "\.\/chat-compact-tail";/);
});

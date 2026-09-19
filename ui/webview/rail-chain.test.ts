// The rail's raw previous-epoch chain, the same-minute rule's reference, at the compact tail's seam (PR E review round 0, medium).
// A window build chains the reference unit by unit through appendItem (`adv`: a row's epoch when it has one; a collapsed tool run
// leaves the chain on its FIRST member, an expanded one on its members in order; a notice run on its anchor; a hidden thinking block is
// never seen). The seam re-renders from a unit in the middle of the window and seeded it with prevTimedEpoch(s.events, the unit's first
// event): a scan of s.events that sees the hidden thinking rows and a collapsed run's LAST member, so the streaming reply's stamp was
// decided against a time no rendered row shows, and a rebuild of the same rows drew it differently. railExit is appendItem's rule as a
// pure function, railChainBefore the chain a build reaches at a unit; both are lifted here with appendItem itself (its renderers stubbed
// to record the reference they were handed) and executed: the rule per kind, the equivalence of appendItem's return with railExit over
// every kind and fold state, the composition (the chain a build hands unit u0 equals railChainBefore(…, u0)), and the phone's shape with
// the real markerLabel: a collapsed run across a minute boundary, then the reply in the last member's minute. Synthetic events.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { itemAnchor, type DisplayItem } from "./compact";
import { DayWalk, markerLabel } from "./time-marker";
import { hideEdges } from "../test-dom-shim";

const requireCjs = createRequire(__filename);
const RENDER = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "render.ts"), "utf8");

function liftBetween(startAnchor: string, endAnchor: string): string {
  const a = RENDER.indexOf(startAnchor), b = RENDER.indexOf(endAnchor, a);
  assert.ok(a > 0 && b > a, `anchors not found: ${startAnchor.slice(0, 40)} or ${endAnchor.slice(0, 40)} moved; re-anchor`);
  return requireCjs("esbuild").transformSync(RENDER.slice(a, b), { loader: "ts" }).code;
}

/** Enough of an element for appendItem: data-*, a class list, children. */
class FakeEl {
  children!: FakeEl[]; dataset: Record<string, string> = {}; cls: string[] = [];
  constructor(public tag: string, className = "") { this.cls = className ? className.split(/\s+/) : []; Object.defineProperty(this, "children", { value: [], writable: true, enumerable: false, configurable: true }); hideEdges(this); }
  get classList() { const c = this.cls; return { add: (x: string) => { c.push(x); }, contains: (x: string) => c.includes(x) }; }
  get firstChild(): FakeEl | null { return this.children[0] ?? null; }
  appendChild(c: FakeEl): FakeEl { this.children.push(c); return c; }
}

type Ev = { kind: string; uuid: string; t?: number };
type Rendered = { what: string; index: number; prev: number | null };
type Lifted = {
  prevTimedEpoch: (events: Ev[], i: number) => number | null;
  railSeed: (s: any, items: DisplayItem[], u: number) => number | null;
  railExit: (s: any, it: DisplayItem, prev: number | null) => number | null;
  railChainBefore: (s: any, items: DisplayItem[], winStart: number, u0: number) => number | null;
  appendItem: (v: any, s: any, items: DisplayItem[], u: number, prev: number | null, walk: DayWalk, working: boolean, turns?: number[] | null) => number | null;
  unitExit: (s: any, it: DisplayItem) => number | null;
};
/** The rail helpers and appendItem, lifted; `open` is the set of fold keys that stand open ("tg:<uuid>" / "ng:<uuid>", the real keys' shape). */
function lift(open: Set<string>, rendered: Rendered[]): Lifted {
  const rail = liftBetween("function prevTimedEpoch(", "// The day the WALK is in at a row");
  const append = liftBetween("function appendItem(", "// Full (re)build of the window");
  const prelude = `
    const H = HOOKS;
    const HTMLElement = H.FakeEl;
    const el = (tag, cls) => new H.FakeEl(tag, cls || "");
    const eventEpoch = (ev) => (ev.t == null ? null : ev.t);
    const openFolds = H.open;
    const toolGroupKey = (first) => "tg:" + first.uuid;
    const noticeGroupKey = (first) => "ng:" + first.uuid;
    const itemAnchor = H.itemAnchor;
    const itemFirstEvent = (it) => (it.kind === "toolgroup" || it.kind === "noticegroup" ? it.indices[0] : it.kind === "gap" ? it.before : it.index);
    const dayDividerFor = () => null;
    const stampWalkDay = () => {};
    const gapElement = () => new H.FakeEl("div", "tx-gap");
    const turnWorkedSecs = () => null;
    const renderEvent = (ev, prev) => { H.rendered.push({ what: "event:" + ev.kind, index: H.indexOf(ev), prev: prev === undefined ? null : prev }); return new H.FakeEl("div", "turn turn-" + ev.kind); };
    const renderToolGroup = (tools, prev) => { H.rendered.push({ what: "toolgroup", index: H.indexOf(tools[0]), prev }); return new H.FakeEl("div", "turn turn-toolgroup"); };
    const renderNoticeGroup = (evs, anchor, prev) => { H.rendered.push({ what: "noticegroup", index: H.indexOf(anchor), prev }); return new H.FakeEl("div", "turn turn-noticegroup"); };
  `;
  const hooks: any = { FakeEl, open, itemAnchor, rendered, indexOf: (ev: Ev) => hooks.events.indexOf(ev), events: [] as Ev[] };
  const api = new Function("HOOKS", prelude + rail + append + "\nreturn { prevTimedEpoch, railSeed, railExit, railChainBefore, appendItem, unitExit };")(hooks) as Lifted;
  return { ...api, appendItem: (v, s, items, u, prev, walk, working, turns = null) => { hooks.events = s.events; return api.appendItem(v, s, items, u, prev, walk, working, turns); },
           railChainBefore: (s, items, ws, u0) => { hooks.events = s.events; return api.railChainBefore(s, items, ws, u0); }, railExit: (s, it, p) => { hooks.events = s.events; return api.railExit(s, it, p); } };
}

const ev = (index: number): DisplayItem => ({ kind: "event", index });
const tg = (...indices: number[]): DisplayItem => ({ kind: "toolgroup", indices });
const ng = (...indices: number[]): DisplayItem => ({ kind: "noticegroup", indices });
const gap = (lo: number, hi: number, before: number): DisplayItem => ({ kind: "gap", lo, hi, before });
const E = (kind: string, uuid: string, t?: number): Ev => (t == null ? { kind, uuid } : { kind, uuid, t });
/** A local clock: seconds since the epoch for a fixed day, so the same-minute rule reads local hours and minutes the way the rail does. */
const at = (h: number, m: number, s: number) => Math.floor(new Date(2026, 8, 19, h, m, s).getTime() / 1000);

test("railExit is appendItem's rule per kind: an event's own epoch; a gap leaves the chain; a collapsed tool run its FIRST member, an open one its members in order; a notice run its anchor, then its members and the anchor again when open", () => {
  const L = lift(new Set(), []);
  const events: Ev[] = [E("user", "u0", 100), E("tool", "t1", 110), E("thinking", "th2", 120), E("tool", "t3", 130), E("assistant", "a4", 140), E("retried", "n5", 150), E("retried", "n6", 160), E("system", "s7")];
  const s = { events };
  assert.equal(L.railExit(s, ev(4), 99), 140, "an event: its epoch");
  assert.equal(L.railExit(s, ev(7), 99), 99, "…unchanged when it has none");
  assert.equal(L.railExit(s, gap(0, 16, 0), 99), 99, "a gap leaves the chain");
  assert.equal(L.railExit(s, tg(1, 3), 99), 110, "a collapsed tool run: the first member (appendItem's adv(it.indices[0]) alone)");
  const open = lift(new Set(["tg:t1", "ng:n5"]), []);
  assert.equal(open.railExit(s, tg(1, 3), 99), 130, "an open tool run: the members in order, the last one's epoch");
  assert.equal(L.railExit(s, ng(5, 6), 99), 160, "a collapsed notice run: its anchor (the latest member)");
  assert.equal(open.railExit(s, ng(5, 6), 99), 160, "…open: the members, then the anchor again");
  const skewed = { events: [E("retried", "n0", 500), E("retried", "n1", 400)] };   // a member stamped earlier than the one before it
  assert.equal(itemAnchor(ng(0, 1), (i) => skewed.events[i].t ?? null), 0, "the anchor is the latest member");
  assert.equal(lift(new Set(["ng:n0"]), []).railExit(skewed, ng(0, 1), null), 500, "open: the walk leaves the run on its anchor, whatever order the members came in");
  assert.equal(L.railExit(skewed, ng(0, 1), null), 500, "collapsed: the anchor");
});

test("appendItem returns railExit for every kind and fold state: the two cannot part", () => {
  const events: Ev[] = [E("user", "u0", 100), E("tool", "t1", 110), E("thinking", "th2", 120), E("tool", "t3", 130), E("assistant", "a4", 140), E("retried", "n5", 150), E("retried", "n6", 160), E("system", "s7"), E("tool", "t8"), E("tool", "t9", 190)];
  const s = { events, regions: undefined };
  for (const open of [new Set<string>(), new Set(["tg:t1", "ng:n5", "tg:t8"])]) {
    const L = lift(open, []);
    for (const it of [ev(0), ev(4), ev(7), gap(0, 16, 0), tg(1, 3), ng(5, 6), tg(8, 9)]) {
      for (const prev of [null, 99]) {
        const v = { el: new FakeEl("div") };
        const items = [it];
        const got = L.appendItem(v, s, items, 0, prev, new DayWalk(), false);
        assert.equal(got, L.railExit(s, it, prev), `${JSON.stringify(it)} from ${prev} with ${[...open].join(",") || "no"} folds open`);
      }
    }
  }
});

test("the composition: the chain a window build hands to unit u0 equals railChainBefore(s, items, winStart, u0), whatever the units before it", () => {
  const events: Ev[] = [E("user", "u0", 100), E("tool", "t1", 110), E("thinking", "th2", 120), E("tool", "t3", 130), E("assistant", "a4", 140), E("retried", "n5", 150), E("retried", "n6", 160), E("system", "s7"), E("user", "u8", 180), E("assistant", "a9", 190)];
  const items = [ev(0), tg(1, 3), ev(4), ng(5, 6), ev(7), ev(8), ev(9)];
  for (const open of [new Set<string>(), new Set(["tg:t1"]), new Set(["ng:n5", "tg:t1"])]) {
    const rendered: Rendered[] = [];
    const L = lift(open, rendered);
    const s = { events, regions: undefined };
    for (const winStart of [0, 1, 2]) {
      const v = { el: new FakeEl("div") };
      let prev = L.railSeed(s, items, winStart);
      for (let u = winStart; u < items.length; u++) {
        assert.equal(prev, L.railChainBefore(s, items, winStart, u), `unit ${u} from winStart ${winStart}, folds open: ${[...open].join(",") || "none"}`);
        prev = L.appendItem(v, s, items, u, prev, new DayWalk(), false);
      }
    }
  }
  assert.equal(lift(new Set(), []).railSeed({ events }, items, 2), 130, "the seed at a window's start is the most recent timed event before its first (the back-scan over s.events)");
  assert.equal(lift(new Set(), []).railSeed({ events }, items, 0), null);
});

test("the phone's shape: a collapsed run across a minute boundary, then the reply in the last member's minute: the build's chain stamps the reply, the old seed suppressed it, and the seam now seeds as the build does", () => {
  const events: Ev[] = [E("user", "u0", at(10, 0, 0)), E("tool", "t1", at(10, 0, 10)), E("tool", "t2", at(10, 3, 0)), E("tool", "t3", at(10, 5, 30)), E("assistant", "a4", at(10, 5, 40))];
  const items = [ev(0), tg(1, 3), ev(2 + 2)];   // the prompt, the collapsed run of three tools, the reply
  const rendered: Rendered[] = [];
  const L = lift(new Set(), rendered);
  const s = { events, regions: undefined };
  const now = new Date(2026, 8, 19, 10, 5, 50).getTime();
  // the rebuild: chained from the window's start through appendItem, the reply's reference is the run's FIRST member
  const v = { el: new FakeEl("div") };
  let prev: number | null = null;
  for (let u = 0; u < items.length; u++) prev = L.appendItem(v, s, items, u, prev, new DayWalk(), false);
  const reply = rendered.find((r) => r.what === "event:assistant")!;
  assert.equal(reply.prev, at(10, 0, 10), "the reply's reference under a rebuild: the collapsed run's first member");
  assert.equal(markerLabel(at(10, 5, 40), reply.prev, now).text, "10:05", "…so its stamp shows");
  // the seam's old seed: the most recent timed event before the reply, the run's LAST member, in the reply's minute
  const old = L.prevTimedEpoch(events, 4);
  assert.equal(old, at(10, 5, 30));
  assert.equal(markerLabel(at(10, 5, 40), old, now).text, "", "…which suppressed the streaming reply's stamp, against a time the reader cannot see");
  // the seam's seed now
  assert.equal(L.railChainBefore(s, items, 0, 2), reply.prev, "railChainBefore hands the seam the build's own reference");
  // a hidden thinking block in the reply's minute is not seen by either the build or the seam
  const withThinking = { events: [...events.slice(0, 4), E("thinking", "th", at(10, 5, 35)), events[4]], regions: undefined };
  const items2 = [ev(0), tg(1, 3), ev(5)];
  assert.equal(L.prevTimedEpoch(withThinking.events, 5), at(10, 5, 35), "the scan lands on the thinking block");
  assert.equal(L.railChainBefore(withThinking, items2, 0, 2), at(10, 0, 10), "the chain never sees it");
  // …and from a window that opens at the run (a spacer above): the seed is the prompt's epoch, the chain the run's first member
  assert.equal(L.railChainBefore(s, items, 1, 2), at(10, 0, 10));
  assert.equal(L.railSeed(s, items, 1), at(10, 0, 0));
});

test("render.ts: the compact tail's seam seeds from railChainBefore over the view's window start, and the window build from railSeed", () => {
  assert.match(RENDER, /let prevEpoch = railChainBefore\(s, items, v\.winStart \?\? 0, u0\);/, "the seam");
  assert.match(RENDER, /function renderWindowItems\([\s\S]*?let prevEpoch = railSeed\(s, items, unitStart\);/, "the build");
  assert.match(RENDER, /function railChainBefore\(s: Session, items: DisplayItem\[\], winStart: number, u0: number\): number \| null \{\s*\n\s*let prev = railSeed\(s, items, winStart\);\s*\n\s*for \(let u = winStart; u < u0 && u < items\.length; u\+\+\) prev = railExit\(s, items\[u\], prev\);/, "the chain: the seed advanced by the exit rule");
  const seam = RENDER.slice(RENDER.indexOf('if (plan.kind === "append") {'), RENDER.indexOf("if (settings.compact || v.stale) {"));
  assert.doesNotMatch(seam, /prevTimedEpoch\(/, "no scan of s.events in the seam");
});

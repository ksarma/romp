// Compact mode's incremental tail against a full rebuild of the same state: the DIFFERENTIAL (PR E review round 1, lens one). The seam
// (render.ts syncViewInner) re-renders the tail by unit where the rebuild (renderWindowItems) re-rendered the whole window, and the PR
// rested that equivalence on a byte-for-byte source pin, which detects an edit and cannot detect a divergence. Here the real code is
// lifted from render.ts, syncViewInner and patchWorkedFooters, appendItem and renderWindowItems, the rail chain (railSeed, railExit,
// railChainBefore), the day walk (dayWalkBefore, dayDividerFor, stampWalkDay), the trim, the eviction and its re-seed, over a stand-in
// DOM whose rows record what a reader can see: the unit, the class list, the row's text, the rail marker's reference (data-prev) and the
// stamp it yields (markerLabel), the walk's day (data-day) and the worked footer. Every kind of change the stream delivers is driven
// through the incremental path frame by frame, and after each frame the same session and window are rebuilt from scratch and the two
// DOMs compared unit by unit: an append (a prompt, a reply, a tool), an edit of the last block, a tool joining a run and a run extending
// (a fold boundary, closed and open), a status-only tail (the footer flip), a shrink (the tail truncated), a hover's rail band present as
// the thread's last child, and an eviction (the window's span kept, the promoted head unit's stamp). The plan's kind is asserted per
// frame, so a seam that silently fell back to the rebuild could not make the comparison vacuously green. The renderers are stubs that
// record their inputs; the rail and day rules, the trim and the footer patch are the real functions.
// Silent on scroll-only properties: the spacers' heights, the measured figures, the keepTop guard and every scroll write are outside
// what a DOM projection can see (spacer-measure.test.ts, chat-compact-tail.test.ts and the served labs carry those). Synthetic events.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { compactDisplay, itemAnchor, type DisplayItem } from "./compact";
import { DayWalk, markerLabel } from "./time-marker";
import { gapHeight } from "./chat-regions";
import { turnWorkedSecs as workedSecsOf, workedFooterPlan } from "./worked-footer";
import { compactTailPlan, type TailPlan } from "./chat-compact-tail";
import { hideEdges } from "../test-dom-shim";

const requireCjs = createRequire(__filename);
const RENDER = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "render.ts"), "utf8");

function liftBetween(startAnchor: string, endAnchor: string): string {
  const a = RENDER.indexOf(startAnchor), b = RENDER.indexOf(endAnchor, a);
  assert.ok(a > 0 && b > a, `anchors not found: ${startAnchor.slice(0, 40)} or ${endAnchor.slice(0, 40)} moved; re-anchor`);
  return requireCjs("esbuild").transformSync(RENDER.slice(a, b), { loader: "ts" }).code;
}

/** Enough of an element for the seam, the build, the footer patch and the eviction: a class list, data-*, children with the sibling walk,
 *  and the selectors those functions use (`:scope > [data-unit="N"]:not(.day-divider)`, `:scope > .cls`, `:scope > [data-unit="N"] > .cls`). */
class FakeEl {
  children!: FakeEl[]; parent: FakeEl | null = null; dataset: Record<string, string> = {}; style: Record<string, string> = { display: "" };
  nodeType = 1; textContent = "";
  private cls: string[];
  constructor(public tag: string, className = "") {
    this.cls = className ? className.split(/\s+/).filter(Boolean) : [];
    Object.defineProperty(this, "children", { value: [], writable: true, enumerable: false, configurable: true });
    hideEdges(this);
  }
  get className(): string { return this.cls.join(" "); }
  get classList() {
    const c = this.cls;
    return { add: (...xs: string[]) => { for (const x of xs) if (!c.includes(x)) c.push(x); }, contains: (x: string) => c.includes(x),
             remove: (...xs: string[]) => { for (const x of xs) { const i = c.indexOf(x); if (i >= 0) c.splice(i, 1); } },
             toggle: (x: string, force?: boolean) => { const on = force ?? !c.includes(x); if (on && !c.includes(x)) c.push(x); if (!on) { const i = c.indexOf(x); if (i >= 0) c.splice(i, 1); } return on; } };
  }
  get childNodes(): FakeEl[] { return this.children; }
  get firstChild(): FakeEl | null { return this.children[0] ?? null; }
  get lastChild(): FakeEl | null { return this.children[this.children.length - 1] ?? null; }
  get previousSibling(): FakeEl | null { const p = this.parent; if (!p) return null; const i = p.children.indexOf(this); return i > 0 ? p.children[i - 1] : null; }
  get nextSibling(): FakeEl | null { const p = this.parent; if (!p) return null; const i = p.children.indexOf(this); return i >= 0 ? p.children[i + 1] ?? null : null; }
  appendChild(c: FakeEl): FakeEl { c.parent?.removeChild(c); c.parent = this; this.children.push(c); return c; }
  append(...cs: FakeEl[]): void { for (const c of cs) this.appendChild(c); }
  insertBefore(c: FakeEl, ref: FakeEl | null): FakeEl { c.parent?.removeChild(c); c.parent = this; const i = ref ? this.children.indexOf(ref) : -1; if (i < 0) this.children.push(c); else this.children.splice(i, 0, c); return c; }
  removeChild(c: FakeEl): void { this.children = this.children.filter((x) => x !== c); c.parent = null; }
  remove(): void { this.parent?.removeChild(this); }
  private matches(step: string): boolean {
    const re = /\.([\w-]+)|\[data-([\w-]+)(?:="([^"]*)")?\]|:not\(\.([\w-]+)\)/g;
    let m: RegExpExecArray | null, seen = 0;
    while ((m = re.exec(step))) {
      seen += m[0].length;
      if (m[1] != null) { if (!this.cls.includes(m[1])) return false; }
      else if (m[2] != null) { const v = this.dataset[m[2]]; if (v == null || (m[3] != null && v !== m[3])) return false; }
      else if (m[4] != null) { if (this.cls.includes(m[4])) return false; }
    }
    if (seen !== step.length) throw new Error("unsupported selector step " + step);
    return true;
  }
  private select(sel: string): FakeEl[] {
    if (sel.startsWith(":scope > ")) {
      let nodes: FakeEl[] = [this];
      for (const step of sel.slice(9).split(" > ")) nodes = nodes.flatMap((n) => n.children.filter((c) => c.matches(step)));
      return nodes;
    }
    const out: FakeEl[] = [];
    const walk = (n: FakeEl) => { for (const c of n.children) { if (c.matches(sel)) out.push(c); walk(c); } };
    walk(this);
    return out;
  }
  querySelector(sel: string): FakeEl | null { return this.select(sel)[0] ?? null; }
  querySelectorAll(sel: string): FakeEl[] { return this.select(sel); }
}

type Ev = { kind: string; uuid: string; t?: number; md?: string; name?: string; human?: boolean };
type Lifted = {
  syncViewInner: (id: string, atBottom?: boolean) => any;
  renderWindowItems: (v: any, s: any, items: DisplayItem[], ws: number, we: number, working: boolean) => void;
};
const WINDOW_TAIL = 8;   // the harness's window: small, so an append evicts the top within a few frames (the real one is 80; the plan and the trim do not read it)

/** The display units for a session: compactDisplay over the events' kinds, tool names and foldable notices (render.ts displayItems, no regions). */
const itemsOf = (s: { events: Ev[] }): DisplayItem[] => compactDisplay(s.events.map((e) => e.kind), s.events.map((e) => (e.kind === "tool" ? e.name : undefined)), s.events.map((e) => e.kind === "retried"));

/** render.ts lifted over the stand-in DOM. `open` is the set of fold keys that stand open ("tg:<uuid>" / "ng:<uuid>"); `plans` records
 *  every plan the seam asks for. The renderers record the inputs a reader can see: the row's text as data-text, the rail reference on a
 *  time-marker first child (data-epoch / data-prev, as timeMarker stamps them), the worked footer as a .turn-elapsed child. */
function lift(sessions: Map<string, any>, views: Map<string, any>, open: Set<string>, plans: TailPlan[]): Lifted {
  const seam = liftBetween("function syncViewInner(", "// prevEpoch for event i");
  const rail = liftBetween("function prevTimedEpoch(", "// ── Unified bidirectional virtualization");
  const first = liftBetween("function itemFirstEvent(", "// The display-unit index");
  const build = liftBetween("function appendItem(", "/** The estimated height of the units [from, to)");
  const divider = liftBetween("function dayDividerFor(", "// STICKY rail stamp");
  const prelude = `
    const H = HOOKS;
    let renderingSid = null, renderingOwnerSid = null;
    const subParts = () => null;
    const sessions = H.sessions, views = H.views;
    const ensureView = (id) => views.get(id);
    const settings = { compact: true };
    const displayItems = (s) => H.itemsOf(s);
    const WINDOW_TAIL = H.WINDOW_TAIL;
    const lastCompactUnit = () => 0;
    const applyMeasure = () => false; const redrawGapUnits = () => {}; const sizeSpacers = () => {};
    const compactTailPlan = (w) => { const p = H.compactTailPlan(w); H.plans.push(p); return p; };
    const turnOfEvents = () => null;
    const DayWalk = H.DayWalk;
    const HTMLElement = H.FakeEl; const el = (t, c) => new H.FakeEl(t, c || "");
    const eventEpoch = (ev) => (ev.t == null ? null : ev.t);
    const openFolds = H.open;
    const toolGroupKey = (first) => "tg:" + first.uuid;
    const noticeGroupKey = (first) => "ng:" + first.uuid;
    const itemAnchor = H.itemAnchor;
    const gapHeight = H.gapHeight;
    const gapElement = (s, it, v) => { const g = el("div", "tx-gap"); g.dataset.lo = String(it.lo); g.dataset.hi = String(it.hi); return g; };
    const turnWorkedSecs = (events, i, working) => H.workedSecsOf(events, i, working, eventEpoch);
    const workedFooterPlan = H.workedFooterPlan;
    const elapsedFooter = (secs) => { const f = el("div", "turn-elapsed"); f.textContent = String(secs); return f; };
    const timeMarker = (epoch, prev) => { const m = el("div", "time-marker"); m.dataset.epoch = String(epoch); m.dataset.prev = prev == null ? "" : String(prev); return m; };
    const paintMarker = (m, epoch, prev, now) => { H.painted.push([m.dataset.unit, epoch, prev]); };
    const renderEvent = (ev, prev, worked) => {
      const t = el("div", "turn turn-" + ev.kind); t.dataset.uuid = ev.uuid; t.dataset.text = ev.md || "";
      if (ev.t != null) t.insertBefore(timeMarker(ev.t, prev == null ? null : prev), t.firstChild);
      if (worked != null) t.appendChild(elapsedFooter(worked));
      return t;
    };
    const renderToolGroup = (tools, prev, key, open) => {
      const t = el("div", "turn turn-toolgroup" + (open ? " expanded" : "")); t.dataset.uuid = tools[0].uuid; t.dataset.text = tools.map((x) => x.name).join(",");
      const ep = eventEpoch(tools[0]); if (ep != null) t.insertBefore(timeMarker(ep, prev == null ? null : prev), t.firstChild);
      return t;
    };
    const renderNoticeGroup = (evs, anchor, prev, key, open) => {
      const t = el("div", "turn turn-toolgroup turn-noticegroup" + (open ? " expanded" : "")); t.dataset.uuid = anchor.uuid; t.dataset.text = evs.length + " notices";
      const ep = eventEpoch(anchor); if (ep != null) t.insertBefore(timeMarker(ep, prev == null ? null : prev), t.firstChild);
      return t;
    };
    const Date = { now: () => H.NOW };
  `;
  const hooks = { FakeEl, sessions, views, itemsOf, WINDOW_TAIL, compactTailPlan, plans, open, itemAnchor, gapHeight, workedSecsOf, workedFooterPlan, DayWalk, NOW, painted: [] as any[] };
  return new Function("HOOKS", prelude + rail + first + divider + build + seam + "\nreturn { syncViewInner, renderWindowItems };")(hooks) as Lifted;
}

/** A local clock on a fixed day, so the same-minute rule reads local hours and minutes the way the rail does; NOW is a later day, so
 *  every stamp is a clock time (a row of today would read how long ago). */
const at = (h: number, m: number, s: number) => Math.floor(new Date(2026, 0, 15, h, m, s).getTime() / 1000);
const NOW = new Date(2026, 0, 20, 12, 0, 0).getTime();
const user = (uuid: string, t: number, md: string): Ev => ({ kind: "user", uuid, t, md, human: true });
const reply = (uuid: string, t: number, md: string): Ev => ({ kind: "assistant", uuid, t, md });
const tool = (uuid: string, t: number, name: string): Ev => ({ kind: "tool", uuid, t, name });
const thinking = (uuid: string, t: number): Ev => ({ kind: "thinking", uuid, t });

/** What a reader can see of a view's DOM, unit by unit: the unit, the class list, the row's text, the rail marker (its reference and the
 *  stamp that reference yields, the walk's day) and the worked footer; a spacer as itself; a child that is neither as "foreign". */
type Row = { unit: number; cls: string; uuid: string | null; text: string; marker: { epoch: number; prev: string; day: string | null; stamp: string } | null; footer: string | null };
type Projected = { spacer: string } | { foreign: string } | Row;
function project(host: FakeEl): Projected[] {
  return host.children.map((c): Projected => {
    if (c.classList.contains("tx-spacer")) return { spacer: c.className };
    if (c.dataset.unit == null) return { foreign: c.className };
    const m = c.children.find((x) => x.classList.contains("time-marker")) ?? null;
    const f = c.children.find((x) => x.classList.contains("turn-elapsed")) ?? null;
    const prev = m ? (m.dataset.prev === "" ? null : Number(m.dataset.prev)) : null;
    return { unit: Number(c.dataset.unit), cls: c.className, uuid: c.dataset.uuid ?? null, text: c.dataset.text ?? c.textContent ?? "",
             marker: m ? { epoch: Number(m.dataset.epoch), prev: m.dataset.prev, day: m.dataset.day ?? null, stamp: markerLabel(Number(m.dataset.epoch), prev, NOW).text } : null,
             footer: f ? f.textContent : null };
  });
}
const units = (p: Projected[]): Row[] => p.filter((x): x is Row => "unit" in x);

type World = { s: any; v: any; L: Lifted; plans: TailPlan[]; open: Set<string>; frames: string[] };
/** A session over `events` in a view built by the real first build (renderWindowItems over the tail window), the seam lifted over it. */
function world(events: Ev[], open: Set<string>, working = true): World {
  const s = { id: "A", events, status: { state: working ? "working" : "ready" }, regions: undefined };
  const v: any = { el: new FakeEl("div"), rendered: 0, scrollTop: 0, stick: true, shown: true, stale: false, winStart: 0 };
  const plans: TailPlan[] = [];
  const L = lift(new Map([["A", s]]), new Map([["A", v]]), open, plans);
  L.syncViewInner("A", true);
  assert.equal(plans.length, 0, "the first build asks no plan");
  assert.ok(v.el.children.length > 0, "the first build rendered the window");
  return { s, v, L, plans, open, frames: [] };
}
/** The rebuild of the same state over the incremental view's own window, in a fresh view. */
function rebuild(w: World): FakeEl {
  const v2: any = { el: new FakeEl("div"), rendered: 0, scrollTop: 0, stick: true, shown: true, stale: false, winStart: 0 };
  w.L.renderWindowItems(v2, w.s, itemsOf(w.s), w.v.winStart ?? 0, w.v.winEnd ?? itemsOf(w.s).length, w.s.status.state === "working");
  return v2.el;
}
/** The two DOMs agree, unit by unit, and nothing foreign stands among the incremental view's units. */
function compare(w: World, label: string): void {
  const inc = project(w.v.el), full = project(rebuild(w));
  assert.ok(units(full).length > 0, label + ": the rebuild rendered units (a derived expectation over an empty window would prove nothing)");
  assert.deepEqual(inc, full, label + ": the incremental DOM against the rebuild of the same state over [" + w.v.winStart + ", " + w.v.winEnd + ")\nframes: " + w.frames.join(" | "));
  assert.deepEqual(inc.filter((x) => "foreign" in x), [], label + ": no foreign child among the units after the paint");
}
/** One streamed frame: the events after `mutate`, the first changed index (identity first, as the kernel's diff: an edited event is a new
 *  object) lowering v.rendered, a shrink marking the view stale (the chatTail handler's `shrank`), then appendActive's sync with the reader
 *  at the bottom. `expect` is the plan the frame must take ("fast": the status-only fast path asks no plan). */
function frame(w: World, label: string, mutate: (events: Ev[]) => Ev[], expect: "append" | "rebuild" | "fast", opts: { working?: boolean; band?: boolean } = {}): void {
  const was: Ev[] = w.s.events;
  const now = mutate(was.slice());
  let from = 0;
  while (from < was.length && from < now.length && was[from] === now[from]) from++;
  w.s.events = now;
  if (opts.working != null) w.s.status.state = opts.working ? "working" : "ready";
  w.v.rendered = Math.min(w.v.rendered, from);
  if (now.length < was.length) w.v.stale = true;
  if (opts.band) w.v.el.appendChild(new FakeEl("div", "rail-band rail-band-local"));   // a hover's band: drawRailBand appends it to the thread as its last child
  const n = w.plans.length;
  w.L.syncViewInner("A", true);
  w.frames.push(label);
  const asked = w.plans.slice(n);
  if (expect === "fast") assert.equal(asked.length, 0, label + ": a status-only tail takes the fast path, no plan asked: " + JSON.stringify(asked));
  else { assert.equal(asked.length, 1, label + ": one plan asked: " + JSON.stringify(asked)); assert.equal(asked[0].kind, expect, label + ": the plan " + JSON.stringify(asked[0])); }
  compare(w, label);
}

// The transcript: a prompt, a reply, then the agentic turn (a prompt, a collapsed run of two tools across a minute boundary, a hidden
// thinking block in a later minute, the reply in that minute). The run's key is "tg:t1"; the fold state is the sequence's parameter.
const base = (): Ev[] => [
  user("u0", at(9, 58, 0), "first question"), reply("a1", at(9, 58, 30), "first answer"),
  user("u2", at(10, 0, 0), "second question"), tool("t1", at(10, 0, 10), "Read"), tool("t2", at(10, 3, 0), "Grep"),
  thinking("th3", at(10, 4, 10)), reply("a4", at(10, 4, 20), "second answer"),
];
const FOLDS = [["closed", new Set<string>()], ["open", new Set(["tg:t1", "ng:n5"])]] as const;

for (const [fold, open] of FOLDS) {
  test(`the stream, run ${fold}: a growing reply, a tool landing and joining a run, the run extending, a prompt completing the turn, a status-only tail, a shrink: every frame's DOM equals a rebuild of the same state`, () => {
    const w = world(base(), new Set(open));
    compare(w, "the first build");
    // the reply grows, three frames (an edit of the last block: the same uuid, a new object)
    for (let i = 1; i <= 3; i++) frame(w, "reply grows " + i, (ev) => { ev[ev.length - 1] = reply("a4", at(10, 4, 20), "second answer, more words " + i); return ev; }, "append");
    // a lone tool lands after the reply, then a second joins it (the fold forms), then a third extends the run
    frame(w, "a tool lands", (ev) => ev.concat([tool("t5", at(10, 5, 0), "Bash")]), "append");
    frame(w, "a tool joins: the run forms", (ev) => ev.concat([tool("t6", at(10, 5, 30), "Read")]), "append");
    frame(w, "the run extends", (ev) => ev.concat([tool("t7", at(10, 6, 5), "Edit")]), "append");
    // the reply after the run streams, then a prompt lands: the previous turn completes and its reply gains the worked footer
    frame(w, "a reply after the run", (ev) => ev.concat([reply("a8", at(10, 6, 40), "third answer")]), "append");
    frame(w, "a prompt completes the turn", (ev) => ev.concat([user("u9", at(10, 8, 0), "third question")]), "append");
    // a status-only tail: the session goes idle (the footer on the last reply comes on), then back to work (it comes off)
    frame(w, "idle", (ev) => ev, "fast", { working: false });
    frame(w, "working again", (ev) => ev, "fast", { working: true });
    // the tail shrinks: the kernel retires the last prompt (the handler's shrank flag marks the view stale: the rebuild)
    frame(w, "the tail shrinks", (ev) => ev.slice(0, -1), "rebuild");
    frame(w, "a prompt lands again", (ev) => ev.concat([user("u10", at(10, 9, 0), "third question, again")]), "append");
  });

  test(`a hover's rail band as the thread's last child, run ${fold}: the next streamed frame still renders what a rebuild renders (the trim reaches the units behind it), and nothing foreign is left among the units`, () => {
    const w = world(base(), new Set(open));
    frame(w, "a frame with the band present", (ev) => { ev[ev.length - 1] = reply("a4", at(10, 4, 20), "second answer, hovered"); return ev; }, "append", { band: true });
    frame(w, "a tool lands with the band present", (ev) => ev.concat([tool("t5", at(10, 5, 0), "Bash")]), "append", { band: true });
    frame(w, "a frame with no band", (ev) => ev.concat([reply("a8", at(10, 5, 40), "third answer")]), "append");
    assert.equal((w.v.el as FakeEl).children.filter((c) => c.classList.contains("rail-band")).length, 0, "the band is gone after the paint (a hover redraws it on the next mouseenter)");
  });

  test(`an eviction, run ${fold}: appends past the window's span evict the top, and the unit that becomes the window's first carries the rail reference a build of that window gives it (its stamp does not depend on which path last painted it)`, () => {
    const w = world(base(), new Set(open));
    assert.equal(w.v.winStart, 0, "the first build holds every unit: no eviction yet");
    // appends until the window evicts: the promoted head unit is the reply after the collapsed run and the hidden thinking block, the shape
    // where the build's seed (the back-scan over s.events: the run's last member, the thinking row) and the chain (appendItem's own rule:
    // a collapsed run's first member, no hidden row) part
    const pushes: Array<[string, Ev]> = [["a tool lands", tool("t5", at(10, 5, 0), "Bash")], ["a prompt", user("u6", at(10, 7, 0), "third question")],
                                        ["a reply", reply("a7", at(10, 7, 30), "third answer")], ["a prompt", user("u8", at(10, 9, 0), "fourth question")],
                                        ["a reply", reply("a9", at(10, 9, 20), "fourth answer")], ["a prompt", user("u10", at(10, 11, 0), "fifth question")],
                                        ["a reply", reply("a11", at(10, 11, 30), "fifth answer")]];
    let evicted = 0;
    for (const [label, ev] of pushes) {
      const before = w.v.winStart;
      frame(w, label, (evs) => evs.concat([ev]), "append");
      if (w.v.winStart > before) evicted++;
    }
    assert.ok(evicted >= 2, "the window evicted its top at least twice over the stream (winStart " + w.v.winStart + ")");
    assert.equal(w.v.winEnd - w.v.winStart, WINDOW_TAIL, "the span held");
    const head = units(project(w.v.el))[0];
    assert.equal(head.unit, w.v.winStart, "the first unit under the spacer is the window's start");
    assert.ok(head.marker, "the head unit carries a time marker");
  });
}

test("the stand-in DOM's selectors read what render.ts asks for: a unit's nodes by data-unit less the divider, a run's rows by position, the marker under a unit", () => {
  const host = new FakeEl("div");
  const sp = new FakeEl("div", "tx-spacer tx-spacer-top"); host.appendChild(sp);
  const dv = new FakeEl("div", "day-divider"); dv.dataset.unit = "3"; host.appendChild(dv);
  const head = new FakeEl("div", "turn turn-toolgroup"); head.dataset.unit = "3"; const m = new FakeEl("div", "time-marker"); head.appendChild(m); host.appendChild(head);
  const row = new FakeEl("div", "turn turn-tool tg-child"); row.dataset.unit = "3"; host.appendChild(row);
  const rows = host.querySelectorAll(':scope > [data-unit="3"]:not(.day-divider)');
  assert.ok(rows.length === 2 && rows[0] === head && rows[1] === row, "the unit's nodes less the divider, in order");
  assert.equal(host.querySelector(':scope > [data-unit="3"] > .time-marker'), m);
  assert.equal(host.querySelector(":scope > .tx-spacer-top"), sp);
  assert.equal(host.querySelector(':scope > [data-unit="4"]'), null);
  assert.equal(row.previousSibling, head); assert.equal(head.nextSibling, row); assert.equal(dv.previousSibling, sp); assert.equal(sp.previousSibling, null);
});

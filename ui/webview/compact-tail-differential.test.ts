// Compact mode's incremental tail against a full rebuild of the same state: the DIFFERENTIAL (PR E, the maintainer's round 1 ruling, lens one). The seam
// (render.ts syncViewInner) re-renders the tail by unit where the rebuild (renderWindowItems) re-rendered the whole window, and the PR
// rested that equivalence on a byte-for-byte source pin, which detects an edit and cannot detect a divergence. Here the real code is
// lifted from render.ts, syncViewInner and patchWorkedFooters, appendItem and renderWindowItems, the rail chain (railSeed, railExit,
// railChainBefore), the day walk (dayWalkBefore, dayDividerFor, stampWalkDay), the trim, the eviction and its re-seed, over a stand-in
// DOM whose rows record what a reader can see: the unit, the class list, the row's text, the rail marker's reference (data-prev) and the
// stamp it yields (markerLabel), the walk's day (data-day) and the worked footer. Frames are driven through the incremental path one
// at a time, and after each the same session and window are rebuilt from scratch and the two DOMs compared unit by unit. WHAT IS
// DRIVEN is derived from two lists rather than claimed whole (the maintainer's round 2 ruling): the seam's OUTCOMES (chat-compact-tail.ts TailPlan:
// append, spacer, rebuild, and syncViewInner's status-only fast path) over the UNIT KINDS compactDisplay mints (compact.ts DisplayItem:
// a lone event, a tool run, a notice run, a gap) and the states the stream delivers (working, compacting, ready).
// - append, per unit kind and fold state: a prompt, a reply, a tool, a notice landing; an edit of the last block and of a tool inside
//   a run (a result landing); a hidden thinking block landing at the tail (no unit reaches it: nothing re-rendered); a tool joining a
//   run and a run extending (a fold boundary, closed and open); a notice run forming on an anchor out of order, and a run with one
//   member from each branch of isFoldableNoticeShape (a notice kind, a user-shaped and an assistant-shaped member; the predicate admits
//   four kinds and three user shapes, so the run stands for its branches, not for every shape it admits, and the list is minted
//   through the predicate itself); a reply landing while idle (the footer moves off the reply before it); a day crossing (the divider
//   the seam appends); a hover's rail
//   band present as the thread's last child, and the rings and glow it lit (dropped with it, as the rebuild's wipe dropped them); an
//   eviction (the window's span kept, the promoted head unit's stamp; a gap promoted to the head, the stamp of the first marker after
//   it).
// - spacer, in both directions below a browsed window: the footer landing on the window's last reply when the completing prompt lands
//   below it, and coming off when a later reply joins the turn below it (the one branch the maintainer's round 1 addendum changed).
// - the fast path: a status-only tail while the turn is OPEN, over every state (idle puts the footer on the turn's last reply and on
//   the last row of an open notice run by its position; work and compacting take it off).
// - rebuild: the shrink (the tail truncated: the handler's stale mark). Its other whys (no-record, below-window, inside-browsed,
//   bottom-spacer, gap) share one executor that never reads plan.why and calls the same renderWindowItems the rebuild leg calls, so no
//   mutation there can make the legs diverge, and they have no frame here; a scrolled-up reader's keepTop is a window bound the
//   projection cannot see (compact-seam-exec.test.ts drives it).
// The plan's kind is asserted per frame, and after an append the units below the plan's u0 are the SAME nodes and the units from u0
// are new, so a seam that silently fell back to the rebuild, with the plan asked or not, could not make the comparison vacuously green
// (the plan assertion alone guarded the planner, not the executor: the author's second pass over round 1); a spacer frame replaces no node. The rebuild
// leg and the browse helper's window build read the working state the seam stored on the view (v.working), never a restatement of the
// state test, and every read asserts the value present first (workingOf). The renderers are
// stubs that record their inputs; the rail and day rules, the trim, the hover clear and the footer patch are the real functions.
// Silent on scroll-only properties: the spacers' heights, the measured figures, the keepTop guard and every scroll write are outside
// what a DOM projection can see (spacer-measure.test.ts, chat-compact-tail.test.ts and the served labs carry those). Synthetic events.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { compactDisplay, isFoldableNoticeShape, itemAnchor, type DisplayItem } from "./compact";
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
  set className(s: string) { this.cls = s ? String(s).split(/\s+/).filter(Boolean) : []; }   // a className write lands on the list classList and the selectors read (the closing pass over the author's fixer pass: with a getter alone a remover spelled as a className rewrite was inert here, so the hover pins saw classList mutations only)
  get classList() {
    const c = this.cls;
    return { add: (...xs: string[]) => { for (const x of xs) if (!c.includes(x)) c.push(x); }, contains: (x: string) => c.includes(x),
             remove: (...xs: string[]) => { for (const x of xs) { const i = c.indexOf(x); if (i >= 0) c.splice(i, 1); } },
             toggle: (x: string, force?: boolean) => { const on = force ?? !c.includes(x); if (on && !c.includes(x)) c.push(x); if (!on) { const i = c.indexOf(x); if (i >= 0) c.splice(i, 1); } return on; } };
  }
  get childNodes(): FakeEl[] { return this.children; }
  get parentElement(): FakeEl | null { return this.parent; }
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

type Ev = { kind: string; uuid: string; t?: number; md?: string; name?: string; human?: boolean;
            rompSystem?: boolean; interruptMarker?: boolean; interruptSettle?: boolean; source?: string; undelivered?: boolean };   // the notice shapes isFoldableNoticeShape reads
type Lifted = {
  syncViewInner: (id: string, atBottom?: boolean) => any;
  renderWindowItems: (v: any, s: any, items: DisplayItem[], ws: number, we: number, working: boolean) => void;
  rulerState: () => [number[], number[]];   // the lift's own bindings of glowHistory and glowUnits, read after a frame (the ruler instrument's marks half)
  setRulerState: (history: number[], units: number[]) => void;   // …and set through the lift, the way applyGlow leaves them for the code the seam runs
};
const WINDOW_TAIL = 8;   // the harness's window: small, so an append evicts the top within a few frames (the real one is 80; the plan and the trim do not read it)

/** The display units for a session: compactDisplay over the events' kinds, tool names and foldable notices (render.ts displayItems,
 *  whose notice predicate is compact.ts isFoldableNoticeShape: passed here as production passes it, never a hand copy of one of its six
 *  shapes, which could mint no run of the other five; the maintainer's round 2 ruling); a session with `gapBefore` set holds a hidden-history gap (T386:
 *  turns the page does not hold) as the unit before the one opening at that event, where the regions' itemization puts it. */
const firstEventOf = (it: DisplayItem): number => (it.kind === "event" ? it.index : it.kind === "gap" ? it.before : it.indices[0]);
const itemsFor = (s: { events: Ev[]; gapBefore?: number }, compact: boolean): DisplayItem[] => {
  const base: DisplayItem[] = compact
    ? compactDisplay(s.events.map((e) => e.kind), s.events.map((e) => (e.kind === "tool" ? e.name : undefined)), s.events.map(isFoldableNoticeShape))
    : s.events.map((_, i) => ({ kind: "event", index: i }));   // normal mode: one unit per event, thinking rows included (render.ts displayItems' other branch)
  if (s.gapBefore == null) return base;
  const out: DisplayItem[] = [];
  for (const it of base) { if (firstEventOf(it) === s.gapBefore) out.push({ kind: "gap", lo: 10, hi: 12, before: s.gapBefore }); out.push(it); }
  assert.equal(out.length, base.length + 1, "the gap stands before the unit that opens at event " + s.gapBefore);
  return out;
};
const itemsOf = (s: { events: Ev[]; gapBefore?: number }): DisplayItem[] => itemsFor(s, true);   // compact mode's list, the fold-state tests'
/** The UNIT of the first event at or past event `i` in a list: its index in the list, which carries the regions' gaps (a head gap makes every
 *  event's unit its index plus one); the list's length when no event is at or past `i`. The rule normal mode's exact tail derives its trim
 *  from since the maintainer's round 5 ruling (regression-1); the compare below checks the DOM, so this copy cannot make a mis-tagged tail
 *  green on its own. */
const unitOfEvent = (items: DisplayItem[], i: number): number => { const u = items.findIndex((it) => it.kind !== "gap" && firstEventOf(it) >= i); return u < 0 ? items.length : u; };

/** render.ts lifted over the stand-in DOM. `open` is the set of fold keys that stand open ("tg:<uuid>" / "ng:<uuid>"); `plans` records
 *  every plan the seam asks for. The renderers record the inputs a reader can see: the row's text as data-text, the rail reference on a
 *  time-marker first child (data-epoch / data-prev, as timeMarker stamps them), the worked footer as a .turn-elapsed child. */
function lift(sessions: Map<string, any>, views: Map<string, any>, open: Set<string>, plans: TailPlan[], compact = true): Lifted {
  const seam = liftBetween("function syncViewInner(", "// prevEpoch for event i");
  const rail = liftBetween("function prevTimedEpoch(", "// ── Unified bidirectional virtualization");
  const first = liftBetween("function itemFirstEvent(", "// The display-unit index");
  const build = liftBetween("function appendItem(", "/** The estimated height of the units [from, to)");
  const divider = liftBetween("function dayDividerFor(", "// STICKY rail stamp");
  const rings = liftBetween("function clearRailRings(", "// ONE continuous rail band per hovered segment");   // the band module's remover, real: the tail paint hands it the view's host
  const prelude = `
    const H = HOOKS;
    let renderingSid = null, renderingOwnerSid = null;
    // no document in the lift: the tail paint's ring clear is host-scoped (a document query here is a red), and the overview ruler is an
    // instrument: paintGlowRuler records its calls, glowHistory and glowUnits stand as applyGlow left them (the maintainer's round 3 ruling D),
    // read back through the lift's OWN bindings (rulerState below): a reset inside the seam (glowHistory = []) rebinds these locals and
    // leaves the hook object's arrays untouched, so the hook read alone was blind to it (the author's fixer pass over pass 4)
    const document = { querySelectorAll: () => { throw new Error("the tail paint queried the document: the ring clear is host-scoped"); } };
    let glowHistory = H.ruler.history, glowUnits = H.ruler.units;
    const paintGlowRuler = () => { H.ruler.paints++; };
    const subParts = () => null;
    const sessions = H.sessions, views = H.views;
    const ensureView = (id) => views.get(id);
    const settings = { compact: H.compact };   // the compact switch, the world's side: compact mode's seam or normal mode's exact tail (the maintainer's round 3 ruling B: every property driven on both sides where the road has the switch)
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
  const hooks = { FakeEl, sessions, views, itemsOf: (s: any) => itemsFor(s, compact), WINDOW_TAIL, compactTailPlan, plans, open, itemAnchor, gapHeight, workedSecsOf, workedFooterPlan, DayWalk, NOW, painted: [] as any[], compact, ruler };
  return new Function("HOOKS", prelude + rings + rail + first + divider + build + seam + "\nreturn { syncViewInner, renderWindowItems, rulerState: () => [glowHistory, glowUnits], setRulerState: (h, u) => { glowHistory = h; glowUnits = u; } };")(hooks) as Lifted;
}
/** The overview ruler as an instrument: what applyGlow last left on it (the history marks and the resident units with no row, as fractions and
 *  units) and how many times the tail paint repainted it. A hover through the lift leaves these as applyGlow would; the tail paint must not touch them. */
type Ruler = { history: number[]; units: number[]; paints: number };
const ruler: Ruler = { history: [], units: [], paints: 0 };

/** A local clock on a fixed day, so the same-minute rule reads local hours and minutes the way the rail does; NOW is a later day, so
 *  every stamp is a clock time (a row of today would read how long ago). */
const at = (h: number, m: number, s: number) => Math.floor(new Date(2026, 0, 15, h, m, s).getTime() / 1000);
const NOW = new Date(2026, 0, 20, 12, 0, 0).getTime();
const user = (uuid: string, t: number, md: string): Ev => ({ kind: "user", uuid, t, md, human: true });
const reply = (uuid: string, t: number, md: string): Ev => ({ kind: "assistant", uuid, t, md });
const tool = (uuid: string, t: number, name: string): Ev => ({ kind: "tool", uuid, t, name });
const thinking = (uuid: string, t: number): Ev => ({ kind: "thinking", uuid, t });
const notice = (uuid: string, t: number): Ev => ({ kind: "retried", uuid, t });   // a foldable notice: two in a row fold into a notice run (itemsOf)
const sysNotice = (uuid: string, t: number): Ev => ({ kind: "user", uuid, t, md: "a note from the tracker", rompSystem: true });   // a user-shaped foldable notice (an injected romp line)
const settleNotice = (uuid: string, t: number): Ev => ({ kind: "assistant", uuid, t, interruptSettle: true });                 // an assistant-shaped one (an interrupt's settle)
const nextDay = (h: number, m: number, s: number) => Math.floor(new Date(2026, 0, 16, h, m, s).getTime() / 1000);   // the day after `at`'s

/** What a reader can see of a view's DOM, unit by unit: the unit, the class list, the row's text, the rail marker (its reference and the
 *  stamp that reference yields, the walk's day) and the worked footer; a spacer as itself; a child that is neither as "foreign". The
 *  glow on a turn (.ext-glow) is left out of the class list: it is applyGlow's cross-surface hover state, which neither leg paints and
 *  which the incremental leg KEEPS on the units it does not re-render (the maintainer's round 3 ruling D); the hover tests read it apart. */
const HOVER_CLASSES = new Set(["ext-glow"]);
type Row = { unit: number; cls: string; uuid: string | null; text: string; marker: { epoch: number; prev: string; day: string | null; stamp: string } | null; footer: string | null };
type Projected = { spacer: string } | { foreign: string } | Row;
function project(host: FakeEl): Projected[] {
  return host.children.map((c): Projected => {
    if (c.classList.contains("tx-spacer")) return { spacer: c.className };
    if (c.dataset.unit == null) return { foreign: c.className };
    const m = c.children.find((x) => x.classList.contains("time-marker")) ?? null;
    const f = c.children.find((x) => x.classList.contains("turn-elapsed")) ?? null;
    const prev = m ? (m.dataset.prev === "" ? null : Number(m.dataset.prev)) : null;
    return { unit: Number(c.dataset.unit), cls: c.className.split(" ").filter((x) => !HOVER_CLASSES.has(x)).join(" "), uuid: c.dataset.uuid ?? null, text: c.dataset.text ?? c.textContent ?? "",
             marker: m ? { epoch: Number(m.dataset.epoch), prev: m.dataset.prev, day: m.dataset.day ?? null, stamp: markerLabel(Number(m.dataset.epoch), prev, NOW).text } : null,
             footer: f ? f.textContent : null };
  });
}
const units = (p: Projected[]): Row[] => p.filter((x): x is Row => "unit" in x);
/** The hover's marks a view holds: the dots a rail band grew (.dot.rail-ring, drawRailBand) and the turns a glow lit (.turn.ext-glow, applyGlow),
 *  and which units carry the glow. */
const hoverMarks = (host: FakeEl) => ({ rings: host.querySelectorAll(".dot.rail-ring").length, glow: host.querySelectorAll(".turn.ext-glow").length });
const glowedUnits = (host: FakeEl) => host.querySelectorAll(".turn.ext-glow").map((t) => Number(t.dataset.unit));

type World = { s: any; v: any; L: Lifted; plans: TailPlan[]; open: Set<string>; frames: string[]; compact: boolean; items: () => DisplayItem[] };
/** A session over `events` in a view built by the real first build (renderWindowItems over the tail window), the seam lifted over it;
 *  `compact` is the side of the switch the world runs on (the maintainer's round 3 ruling B: the same instrument on both sides where the
 *  road has the switch; normal mode's units are its events, so its worlds have no fold state). */
function world(events: Ev[], open: Set<string>, working = true, gapBefore?: number, compact = true): World {
  const s = { id: "A", events, status: { state: working ? "working" : "ready" }, regions: undefined, gapBefore };
  const v: any = { el: new FakeEl("div"), rendered: 0, scrollTop: 0, stick: true, shown: true, stale: false, winStart: 0 };
  const plans: TailPlan[] = [];
  const L = lift(new Map([["A", s]]), new Map([["A", v]]), open, plans, compact);
  L.syncViewInner("A", true);
  assert.equal(plans.length, 0, "the first build asks no plan");
  assert.ok(v.el.children.length > 0, "the first build rendered the window");
  return { s, v, L, plans, open, frames: [], compact, items: () => itemsFor(s, compact) };
}
/** The rebuild of the same state over the incremental view's own window, in a fresh view. The rebuild leg reads the working state
 *  production's own syncViewInner computed and stored on the view (render.ts `v.working = working`), never a restatement of the state
 *  test: a copy here dropped `compacting` and rendered the two legs from different inputs, so the instrument went red against correct
 *  production code (the maintainer's round 2 ruling). The value is asserted present so a production change that stops storing it is a loud red here,
 *  not a rebuild over `undefined` that happens to match. */
function rebuild(w: World): FakeEl {
  const v2: any = { el: new FakeEl("div"), rendered: 0, scrollTop: 0, stick: true, shown: true, stale: false, winStart: 0 };
  const items = w.items();
  w.L.renderWindowItems(v2, w.s, items, w.v.winStart ?? 0, w.v.winEnd ?? items.length, workingOf(w, "the rebuild leg"));
  return v2.el;
}
/** The working state the seam's last paint computed and stored on the view (render.ts `v.working = working`), asserted present BEFORE
 *  any use: the one reader for the rebuild leg and the browse helper, so a production change that stops storing it reds at the read
 *  that would have rendered over `undefined` (as idle), naming the leg, rather than one step later (the author's fixer pass over pass 3: the browse helper
 *  handed the value on unasserted, so under that change the browsed window rendered idle first and the red came from the rebuild). */
function workingOf(w: World, leg: string): boolean {
  assert.notEqual(w.v.working, undefined, leg + " reads the working state the seam's last paint stored on the view (syncViewInner stores v.working), and the view holds none");
  return w.v.working as boolean;
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
 *  at the bottom. `expect` is the plan the frame must take ("fast": the status-only fast path asks no plan). After an append the EXECUTOR
 *  is checked, not the planner alone: every unit node below the plan's u0 is the node that was there before the paint (the eviction takes
 *  some away and the re-seed repaints the promoted head's marker in place; a spacer carries no unit), every unit node from u0 is new, and
 *  when u0 is the unit count (`u0: "total"`: a hidden thinking block landed, no unit reaches it) nothing is new. A seam that asked the
 *  plan and rebuilt the window anyway passes the plan assertion with every node new. */
function frame(w: World, label: string, mutate: (events: Ev[]) => Ev[], expect: "append" | "rebuild" | "fast", opts: { working?: boolean; state?: "working" | "ready" | "compacting"; band?: boolean; u0?: "total" } = {}): void {
  const was: Ev[] = w.s.events;
  const now = mutate(was.slice());
  let from = 0;
  while (from < was.length && from < now.length && was[from] === now[from]) from++;
  w.s.events = now;
  if (opts.state != null) w.s.status.state = opts.state;   // the stream's own state words (compacting is work to the footer: syncViewInner's `working`)
  else if (opts.working != null) w.s.status.state = opts.working ? "working" : "ready";
  w.v.rendered = Math.min(w.v.rendered, from);
  if (now.length < was.length) w.v.stale = true;
  if (opts.band) w.v.el.appendChild(new FakeEl("div", "rail-band rail-band-local"));   // a hover's band: drawRailBand appends it to the thread as its last child
  const before = new Set<FakeEl>((w.v.el as FakeEl).children);
  const n = w.plans.length;
  w.L.syncViewInner("A", true);
  w.frames.push(label);
  const asked = w.plans.slice(n);
  /** The EXECUTOR's check: every unit node below `u0` is the node that was there before the paint, every one from `u0` is new. */
  const executed = (u0: number, total: number, why: string) => {
    let kept = 0, fresh = 0;
    for (const c of (w.v.el as FakeEl).children) {
      const u = c.dataset.unit == null ? -1 : Number(c.dataset.unit);
      if (u < 0) continue;
      if (u < u0) { assert.ok(before.has(c), `${label}: unit ${u} below u0=${u0} is the node that was there before the paint (${why})`); kept++; }
      else { assert.ok(!before.has(c), `${label}: unit ${u} at or past u0=${u0} is a new node (${why})`); fresh++; }
    }
    if (u0 > (w.v.winStart ?? 0)) assert.ok(kept > 0, label + ": the units below u0 inside the window stood (an append never renders the whole window)");
    if (u0 < total) assert.ok(fresh > 0, label + ": the units from u0 were re-rendered"); else assert.equal(fresh, 0, label + ": u0 is the unit count: nothing re-rendered");
  };
  if (!w.compact) {
    // normal mode: no plan on its road (the seam is compact mode's); the exact tail trims from the first changed event's UNIT, its index in the
    // list past any gap (unitOfEvent: under a head gap every event's unit is its index plus one), bounded below by the window's start; the
    // fast path replaces no node, and a stale view takes the rebuild (the maintainer's round 5 ruling, regression-1)
    assert.equal(asked.length, 0, label + ": normal mode asks no plan: " + JSON.stringify(asked));
    const total = w.items().length;
    if (expect === "append") executed(Math.max(unitOfEvent(w.items(), from), w.v.winStart ?? 0), total, "normal mode's trim from the first changed event's unit (its index in the list, past any gap)");
    else if (expect === "fast") for (const c of (w.v.el as FakeEl).children) assert.ok(before.has(c), label + ": a status-only tail replaces no node");
    else executed(w.v.winStart ?? 0, total, "the rebuild renders every unit anew");
  }
  else if (expect === "fast") assert.equal(asked.length, 0, label + ": a status-only tail takes the fast path, no plan asked: " + JSON.stringify(asked));
  else {
    assert.equal(asked.length, 1, label + ": one plan asked: " + JSON.stringify(asked));
    const plan = asked[0];
    assert.equal(plan.kind, expect, label + ": the plan " + JSON.stringify(plan));
    if (plan.kind === "append") {
      const total = w.items().length;
      if (opts.u0 === "total") assert.equal(plan.u0, total, label + ": no unit reaches the change, so u0 is the unit count");
      executed(plan.u0, total, "the plan's u0");
    }
  }
  compare(w, label);
}
/** The reader browses away from the tail: the window re-rendered over [ws, we) with `we` below the unit count, through the real
 *  renderWindowItems (a landing or a scroll-back leaves the view this way), so a bottom spacer stands under the window and the next
 *  change below it takes the seam's spacer branch. */
function browse(w: World, ws: number, we: number): void {
  const items = w.items();
  assert.ok(we < items.length, "a browsed window ends below the unit count (" + we + " of " + items.length + ")");
  w.L.renderWindowItems(w.v, w.s, items, ws, we, workingOf(w, "the browse"));
  assert.equal(w.v.winEnd, we, "the window ends where the browse put it");
  assert.ok((w.v.el as FakeEl).querySelector(":scope > .tx-spacer-bot"), "a bottom spacer stands for the units below the window");
  w.frames.push("browse [" + ws + ", " + we + ")");
  compare(w, "the browsed window");
}
/** One streamed frame whose change lies BELOW a browsed window: the seam's SPACER outcome (the maintainer's round 2 ruling: the one branch the delta
 *  changed, the footer patch, and the outcome the frame() driver could not reach). The events after `mutate` (an append below the
 *  window), the first changed index lowering v.rendered, then the sync with the reader scrolled up. Exactly one plan is asked and it is
 *  `spacer`; no unit node is replaced (every unit node is the node that was there: the footer patch edits a row in place); the bottom
 *  spacer stands; and the window's DOM equals a rebuild of the same state over the same window, which is where a footer that should
 *  have landed or come off shows (the composition: the seam's `from` and its unit list reaching the real patchWorkedFooters). */
function spacerFrame(w: World, label: string, mutate: (events: Ev[]) => Ev[], opts: { working?: boolean } = {}): void {
  const was: Ev[] = w.s.events;
  const now = mutate(was.slice());
  let from = 0;
  while (from < was.length && from < now.length && was[from] === now[from]) from++;
  assert.ok(now.length > was.length && from === was.length, label + ": a spacer frame appends below the window");
  w.s.events = now;
  if (opts.working != null) w.s.status.state = opts.working ? "working" : "ready";
  w.v.rendered = Math.min(w.v.rendered, from);
  const before = new Set<FakeEl>((w.v.el as FakeEl).children);
  const n = w.plans.length;
  w.L.syncViewInner("A", false);
  w.frames.push(label);
  const asked = w.plans.slice(n);
  if (w.compact) {
    assert.equal(asked.length, 1, label + ": one plan asked: " + JSON.stringify(asked));
    assert.equal(asked[0].kind, "spacer", label + ": the change below the browsed window is the spacer outcome: " + JSON.stringify(asked[0]));
  } else assert.equal(asked.length, 0, label + ": normal mode asks no plan; its browse branch is the same outcome on the other side of the switch");
  for (const c of (w.v.el as FakeEl).children) assert.ok(before.has(c), label + ": no node replaced (the branch re-renders no unit; the footer is patched in place)");
  assert.ok((w.v.el as FakeEl).querySelector(":scope > .tx-spacer-bot"), label + ": the bottom spacer stands");
  assert.equal(w.v.spacerCountBot, w.items().length - w.v.winEnd, label + ": the bottom spacer stands for the units below the window");
  compare(w, label);
}
/** The footer text on the incremental view's node(s) for `uuid`: an event's row, or a run's head and the rows of its members (a run's head
 *  carries its anchor's uuid). Null when the node stands with no footer; undefined when no node carries the uuid (a collapsed run's member). */
function footerOn(w: World, uuid: string): string | null | undefined {
  const rows = units(project(w.v.el)).filter((r) => r.uuid === uuid);
  if (!rows.length) return undefined;
  return rows.map((r) => r.footer).find((f) => f != null) ?? null;
}

/** A hover held through a streamed frame, on either side of the compact switch: a hover as drawRailBand and applyGlow leave it (a dot on
 *  every turn, the hovered segment's dots ringed and its turns glowed: the first three units, below the unit the frame re-renders, so they
 *  are KEPT nodes; the band as the thread's last child; the ruler's history marks and spacer units as applyGlow set them), then the frame.
 *  After it: the band is gone (the trim), the rings are gone (clearRailRings on the view's host, the band module's own remover), the glow
 *  stands on every kept unit that had it and on no fresh node, the ruler was not repainted and its marks stand, and the incremental DOM
 *  equals the rebuild's with the glow read apart (project leaves the hover class out). */
function hoverThroughFrame(w: World): void {
  const turns = (w.v.el as FakeEl).children.filter((c) => c.dataset.unit != null && !c.classList.contains("day-divider"));
  for (const t of turns) t.appendChild(new FakeEl("span", "dot green"));
  for (const t of turns.slice(0, 3)) { t.classList.add("ext-glow"); t.children.find((x) => x.classList.contains("dot"))!.classList.add("rail-ring"); }
  const lit = glowedUnits(w.v.el);
  assert.deepEqual(hoverMarks(w.v.el), { rings: 3, glow: 3 }, "the hover lit three units");
  ruler.history = [0.25]; ruler.units = [0]; ruler.paints = 0;   // the hover's marks on the ruler, as applyGlow left them (a history mark, a resident unit with no row)
  w.L.setRulerState(ruler.history, ruler.units);   // …bound in the lift's own scope too, where the seam's code reads them (the lift bound the hook's arrays at lift time; these are the frame's)
  frame(w, "the reply grows under a hover", (ev) => { ev[ev.length - 1] = reply("a4", at(10, 4, 20), "second answer, hovered"); return ev; }, "append", { band: true });
  assert.equal(hoverMarks(w.v.el).rings, 0, "the band's rings left with the band: the band module's remover ran on the view's host");
  assert.deepEqual(glowedUnits(w.v.el), lit, "the glow stands on every kept unit that had it: the tail paint does not touch applyGlow's class (at the head the round ruled on: none, the kept units unlit while the ruler still banded them)");
  assert.equal(hoverMarks(rebuild(w)).glow, 0, "the rebuild leg's rows are fresh nodes with no glow: the two legs are compared with the hover class read apart");
  assert.equal(ruler.paints, 0, "the ruler was not repainted by the tail paint"); assert.deepEqual([ruler.history, ruler.units], [[0.25], [0]], "…and its marks stand as applyGlow left them: the ruler and the kept turns' glow agree");
  assert.deepEqual(w.L.rulerState(), [[0.25], [0]], "…read through the lift's own bindings too: a reset of glowHistory or glowUnits inside the seam rebinds the lift's locals and leaves the hook object's arrays as they were, so the read above alone was green under a planted reset (the author's fixer pass over pass 4)");
  assert.equal((w.v.el as FakeEl).children.filter((c) => c.classList.contains("rail-band")).length, 0, "the band itself is gone (a hover redraws it on the next mouseenter)");
}

// The transcript: a prompt, a reply, then the agentic turn (a prompt, a collapsed run of two tools across a minute boundary, a hidden
// thinking block in a later minute, the reply in that minute). The run's key is "tg:t1"; the fold state is the sequence's parameter, and
// the open fold also opens the run that forms during the stream ("tg:t6") and the notice run ("ng:n5").
const base = (): Ev[] => [
  user("u0", at(9, 58, 0), "first question"), reply("a1", at(9, 58, 30), "first answer"),
  user("u2", at(10, 0, 0), "second question"), tool("t1", at(10, 0, 10), "Read"), tool("t2", at(10, 3, 0), "Grep"),
  thinking("th3", at(10, 4, 10)), reply("a4", at(10, 4, 20), "second answer"),
];
const FOLDS = [["closed", new Set<string>()], ["open", new Set(["tg:t1", "tg:t6", "ng:n5"])]] as const;

for (const [fold, open] of FOLDS) {
  test(`the stream, run ${fold}: a growing reply, a thinking block at the tail, a tool result inside the run, a tool landing and joining a run, the run extending, the footer on and off the open turn's last reply, a reply landing while idle, a prompt completing the turn, a notice run forming on an anchor out of order and going idle, a shrink, a day crossing: every frame's DOM equals a rebuild of the same state`, () => {
    const w = world(base(), new Set(open));
    compare(w, "the first build");
    // the reply grows, three frames (an edit of the last block: the same uuid, a new object)
    for (let i = 1; i <= 3; i++) frame(w, "reply grows " + i, (ev) => { ev[ev.length - 1] = reply("a4", at(10, 4, 20), "second answer, more words " + i); return ev; }, "append");
    // a hidden thinking block lands at the tail: compact mode shows no unit for it, so the plan's u0 is the unit count and nothing is re-rendered
    frame(w, "a thinking block lands", (ev) => ev.concat([thinking("th5", at(10, 4, 50))]), "append", { u0: "total" });
    // a tool's result lands inside the base run (an edit of t1: the same uuid, a new object): the run's unit re-renders whole
    frame(w, "a tool result lands inside the run", (ev) => { ev[3] = { ...ev[3], md: "12 lines" }; return ev; }, "append");
    // a lone tool lands after the reply, then a second joins it (the fold forms: "tg:t6", expanded in the open fold, so the run gains a row
    // per member), then a third extends the run
    frame(w, "a tool lands", (ev) => ev.concat([tool("t6", at(10, 5, 0), "Bash")]), "append");
    frame(w, "a tool joins: the run forms", (ev) => ev.concat([tool("t7", at(10, 5, 30), "Read")]), "append");
    frame(w, "the run extends", (ev) => ev.concat([tool("t8", at(10, 6, 5), "Edit")]), "append");
    // the reply after the run streams; the turn is OPEN, so a status-only tail flips its footer: idle puts it on (the fast path's patch,
    // from = len), work takes it off again
    frame(w, "a reply after the run", (ev) => ev.concat([reply("a9", at(10, 6, 40), "third answer")]), "append");
    assert.equal(footerOn(w, "a9"), null, "the streaming reply carries no footer while the session works");
    frame(w, "idle", (ev) => ev, "fast", { working: false });
    assert.equal(footerOn(w, "a9"), String(at(10, 6, 40) - at(10, 0, 0)), "idle: the footer is on the turn's last reply, the prompt to the reply");
    frame(w, "working again", (ev) => ev, "fast", { working: true });
    assert.equal(footerOn(w, "a9"), null, "back at work: the footer comes off");
    // compacting is a state the stream delivers and the footer reads as work (syncViewInner: working || compacting): a status-only tail
    // into it changes nothing, on both legs (the maintainer's round 2 ruling: the rebuild leg restated the state test and dropped compacting)
    frame(w, "compacting", (ev) => ev, "fast", { state: "compacting" });
    assert.equal(footerOn(w, "a9"), null, "compacting is work: no footer on the open turn's reply");
    // idle again, then a reply lands in the same turn: the footer comes off the reply before it (the seam's patch, its off branch) and the
    // new reply is rendered with its own
    frame(w, "idle again", (ev) => ev, "fast", { working: false });
    frame(w, "a reply lands while idle", (ev) => ev.concat([reply("a10", at(10, 7, 10), "third answer, continued")]), "append");
    assert.equal(footerOn(w, "a9"), null, "no longer the turn's last reply");
    assert.equal(footerOn(w, "a10"), String(at(10, 7, 10) - at(10, 0, 0)), "the new reply carries the footer");
    // a prompt lands and the session works on it: the previous turn is complete and its footer stays
    frame(w, "a prompt completes the turn", (ev) => ev.concat([user("u11", at(10, 8, 0), "third question")]), "append", { working: true });
    assert.equal(footerOn(w, "a10"), String(at(10, 7, 10) - at(10, 0, 0)), "complete: the footer stays");
    // two notices land in the new turn; the second is stamped EARLIER (a notice that kept the moment it was queued), so the run it forms
    // anchors on its first member ("ng:n5": in the open fold the head, then a row per member)
    frame(w, "a notice lands", (ev) => ev.concat([notice("n5", at(10, 9, 0))]), "append");
    frame(w, "a second notice joins, stamped earlier: the run forms on the first", (ev) => ev.concat([notice("n6", at(10, 8, 40))]), "append");
    // idle with the open notice run last: the footer goes on the last member's ROW, read by its position under the run's unit (the fast
    // path's patch); a collapsed run has no row for it, so nothing is on screen and nothing patched; work takes it off again
    frame(w, "idle with the notice run last", (ev) => ev, "fast", { working: false });
    if (fold === "open") assert.equal(footerOn(w, "n6"), String(at(10, 8, 40) - at(10, 8, 0)), "the run's last row carries the footer");
    else assert.equal(footerOn(w, "n6"), undefined, "a collapsed run shows no row for its member");
    frame(w, "working with the notice run last", (ev) => ev, "fast", { working: true });
    assert.notEqual(footerOn(w, "n6"), String(at(10, 8, 40) - at(10, 8, 0)), "back at work: no footer on the row");
    // the tail shrinks: the kernel retires the last notice (the handler's shrank flag marks the view stale: the rebuild), then a prompt lands
    frame(w, "the tail shrinks", (ev) => ev.slice(0, -1), "rebuild");
    frame(w, "a prompt lands again", (ev) => ev.concat([user("u12", at(10, 9, 30), "third question, again")]), "append");
    // the next day: the prompt opens a day, so the seam appends the divider a rebuild draws above it (the walk's mark from dayWalkBefore);
    // the reply after it opens none
    frame(w, "a prompt the next day", (ev) => ev.concat([user("u13", nextDay(0, 1, 0), "next morning")]), "append");
    assert.ok(units(project(w.v.el)).some((r) => r.uuid == null && r.cls.includes("day-divider")), "a day divider stands among the units");
    frame(w, "a reply the next day", (ev) => ev.concat([reply("a14", nextDay(0, 1, 30), "next morning's answer")]), "append");
    frame(w, "idle the next day", (ev) => ev, "fast", { working: false });
  });

  test(`a change below a browsed window, run ${fold}: the spacer outcome patches the window's worked footers in both directions (the footer lands on the window's last reply when the completing prompt lands below it; comes off when a later reply joins the turn below it), replaces no node, and the window equals a rebuild of the same state`, () => {
    // the base transcript and an injected user-kind line after the agentic turn's reply (a line the footer's turn scan skips: a tool or
    // a reply there would make the reply not its turn's last); the reader browses the window to end at that reply (unit 4: the injected
    // line is the one unit below it, under the bottom spacer). The turn is OPEN and the session works, so the reply carries no footer
    const w = world(base().concat([sysNotice("x5", at(10, 5, 0))]), new Set(open));
    browse(w, 0, 5);
    assert.equal(footerOn(w, "a4"), null, "the open turn's reply carries no footer while the session works");
    // a human prompt lands below the window: the turn is complete, so its last reply, INSIDE the window, gets its footer (the seam's spacer
    // branch patches from the first changed event; the rebuild this branch replaced re-rendered the window's footers; the maintainer's round 1 addendum)
    spacerFrame(w, "a prompt completes the turn below the window", (ev) => ev.concat([user("u6", at(10, 6, 0), "third question")]), { working: true });
    assert.equal(footerOn(w, "a4"), String(at(10, 4, 20) - at(10, 0, 0)), "the completing prompt below the window put the footer on the window's last reply");
    // the other direction, its own world: the session is idle, so the open turn's last reply carries the footer; a later reply lands below
    // the browsed window and the footer comes off the reply inside it (the new reply, unrendered, is the turn's last)
    const w2 = world(base().concat([sysNotice("x5", at(10, 5, 0))]), new Set(open), false);
    browse(w2, 0, 5);
    assert.equal(footerOn(w2, "a4"), String(at(10, 4, 20) - at(10, 0, 0)), "idle: the footer is on the turn's last reply");
    spacerFrame(w2, "a reply joins the turn below the window", (ev) => ev.concat([reply("a6", at(10, 5, 30), "second answer, continued")]));
    assert.equal(footerOn(w2, "a4"), null, "no longer the turn's last reply: the footer came off, below a browsed window");
  });

  test(`a notice run with one member from each branch of isFoldableNoticeShape, run ${fold}: a retried (a notice kind), then a user-shaped and an assistant-shaped foldable notice, each appended and compared against a rebuild`, () => {
    // the unit list is minted through production's own predicate, so the run forms here as it does in render.ts displayItems; a hand
    // copy of one shape (`kind === "retried"`) could mint none of these (the maintainer's round 2 ruling: hardening, no failing-before of its own). The
    // predicate has three branches (four notice kinds; a user row by interrupt marker, rompSystem note or peer source; an assistant
    // row by interruptSettle): one member per branch, not one per shape (the author's fixer pass over pass 3: the name said "the three shapes production
    // folds", a count the predicate does not have)
    const w = world(base(), new Set(open));
    frame(w, "a retried notice lands", (ev) => ev.concat([notice("n5", at(10, 5, 0))]), "append");
    frame(w, "a user-shaped notice joins: the run forms", (ev) => ev.concat([sysNotice("n6", at(10, 5, 20))]), "append");
    frame(w, "an assistant-shaped notice extends the run", (ev) => ev.concat([settleNotice("n7", at(10, 5, 40))]), "append");
    const last = itemsOf(w.s)[itemsOf(w.s).length - 1];
    assert.deepEqual(last, { kind: "noticegroup", indices: [7, 8, 9] }, "the three fold into one notice run (production's predicate admits a member from each of its branches)");
    const rows = units(project(w.v.el)).filter((r) => r.unit === itemsOf(w.s).length - 1);
    assert.equal(rows.length, fold === "open" ? 4 : 1, "the run's head, and a row per member when the fold is open");
  });

  test(`a hover held through a streamed frame, run ${fold}: the band and its rings come off with the paint (the band module's remover, on the view's host), the glow stays on the kept units and the ruler stands as applyGlow left it, so the transcript and the ruler agree on every kept turn; the re-rendered unit, a fresh node, carries no glow until the next glowTurns tick, as after any rebuild (the maintainer's round 3 ruling D: taking the glow off left the transcript dark and the ruler banding the turns it had unlit)`, () => {
    hoverThroughFrame(world(base(), new Set(open)));
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

  test(`an eviction that promotes a GAP to the window's first, run ${fold}: the first marker after the gap carries the reference a build of that window gives it (the seed at the gap, carried through the marker-less head)`, () => {
    // a hidden-history gap (T386: a landing loaded a mid-transcript run, then the jump to the live tail) stands before the tail run's
    // first prompt, under a collapsed run across a minute boundary, and the window spans it; the appends evict the units above the gap
    // one by one, then the gap itself. The build's seed at the gap is the back-scan from the event below it (the run's LAST member),
    // where the chain the prompt below was drawn with left the collapsed run on its FIRST: re-seeding the head unit's own marker alone
    // found none on the gap and left the prompt's stamp on the chain's reference until the next eviction repaired it (the author's second pass over round 1).
    const events: Ev[] = [
      user("u0", at(9, 50, 0), "first question"), reply("a1", at(9, 50, 30), "first answer"),
      user("u2", at(9, 52, 0), "second question"), tool("t1", at(9, 52, 10), "Read"), tool("t2", at(9, 55, 0), "Grep"),
      user("u5", at(9, 55, 30), "third question"), reply("a6", at(9, 56, 0), "third answer"), user("u7", at(9, 57, 0), "fourth question"), reply("a8", at(9, 57, 30), "fourth answer"),
    ];
    const w = world(events, new Set(open), true, 5);
    const items0 = itemsOf(w.s);
    assert.equal(items0.length, 9, "eight items and the gap");
    assert.equal(items0[4].kind, "gap", "the gap is the unit before the tail run's prompt");
    assert.equal(w.v.winStart, 1, "the first build opens one unit down: the window spans the gap");
    compare(w, "the first build");
    const pushes: Array<[string, Ev]> = [["a prompt", user("u9", at(9, 58, 0), "fifth question")], ["a reply", reply("a10", at(9, 58, 30), "fifth answer")],
                                        ["a prompt", user("u11", at(9, 59, 0), "sixth question")], ["a reply", reply("a12", at(9, 59, 30), "sixth answer")]];
    let gapHeaded = 0;
    for (const [label, ev] of pushes) {
      frame(w, label, (evs) => evs.concat([ev]), "append");
      if (w.v.winStart === 4) {
        gapHeaded++;
        const rows = units(project(w.v.el));
        assert.equal(rows[0].unit, 4, "the gap is the window's first unit"); assert.equal(rows[0].marker, null, "and carries no marker");
        assert.equal(rows[1].unit, 5); assert.equal(rows[1].marker!.prev, String(at(9, 55, 0)), "the prompt below it is stamped against the run's last member, the seed's back-scan, not the chain's first member");
      }
    }
    assert.equal(gapHeaded, 1, "one frame's eviction made the gap the window's first unit");
    assert.equal(w.v.winStart, 5, "the next eviction promoted the prompt");
  });
}

// ── normal mode: the same instrument on the other side of the compact switch (the maintainer's round 3 ruling B) ─────────────────────────
// The desktop's exact tail (render.ts syncViewInner's normal-mode block, pinned byte for byte in chat-exact-tail.test.ts) trims from the
// first changed event and re-renders to the end, patches the footers with no unit list, patches them and grows the bottom spacer under a
// browsed window, and takes the rebuild for a stale view; a unit is an event, so there are no runs and no fold state, and a thinking block
// is a row of its own. WHAT IS DRIVEN is derived the same way as above: the block's outcomes (the append from the first changed event, the
// browse branch, the fast path, the rebuild) over the event kinds normal mode renders and the states the stream delivers.

test("normal mode, the stream: a growing reply, a thinking block (a row of its own), a tool result landing, tools landing (no run), the footer on and off the open turn's last reply over working, idle and compacting, a reply landing while idle, a prompt completing the turn, notices (no run), a shrink, a day crossing: every frame's DOM equals a rebuild of the same state", () => {
  const w = world(base(), new Set(), true, undefined, false);
  compare(w, "the first build");
  for (let i = 1; i <= 3; i++) frame(w, "reply grows " + i, (ev) => { ev[ev.length - 1] = reply("a4", at(10, 4, 20), "second answer, more words " + i); return ev; }, "append");
  frame(w, "a thinking block lands", (ev) => ev.concat([thinking("th5", at(10, 4, 50))]), "append");
  frame(w, "a tool result lands", (ev) => { ev[3] = { ...ev[3], md: "12 lines" }; return ev; }, "append");
  frame(w, "a tool lands", (ev) => ev.concat([tool("t6", at(10, 5, 0), "Bash")]), "append");
  frame(w, "a second tool lands", (ev) => ev.concat([tool("t7", at(10, 5, 30), "Read")]), "append");
  frame(w, "a reply after the tools", (ev) => ev.concat([reply("a9", at(10, 6, 40), "third answer")]), "append");
  assert.equal(footerOn(w, "a9"), null, "the streaming reply carries no footer while the session works");
  frame(w, "idle", (ev) => ev, "fast", { working: false });
  assert.equal(footerOn(w, "a9"), String(at(10, 6, 40) - at(10, 0, 0)), "idle: the footer is on the turn's last reply (the fast path's patch, told no unit list)");
  frame(w, "working again", (ev) => ev, "fast", { working: true });
  assert.equal(footerOn(w, "a9"), null, "back at work: the footer comes off");
  frame(w, "compacting", (ev) => ev, "fast", { state: "compacting" });
  assert.equal(footerOn(w, "a9"), null, "compacting is work: no footer on the open turn's reply");
  frame(w, "idle again", (ev) => ev, "fast", { working: false });
  frame(w, "a reply lands while idle", (ev) => ev.concat([reply("a10", at(10, 7, 10), "third answer, continued")]), "append");
  assert.equal(footerOn(w, "a9"), null, "no longer the turn's last reply"); assert.equal(footerOn(w, "a10"), String(at(10, 7, 10) - at(10, 0, 0)), "the new reply carries the footer");
  frame(w, "a prompt completes the turn", (ev) => ev.concat([user("u11", at(10, 8, 0), "third question")]), "append", { working: true });
  assert.equal(footerOn(w, "a10"), String(at(10, 7, 10) - at(10, 0, 0)), "complete: the footer stays");
  frame(w, "a notice lands", (ev) => ev.concat([notice("n5", at(10, 9, 0))]), "append");
  frame(w, "a second notice lands, stamped earlier (a row of its own: no run in normal mode)", (ev) => ev.concat([notice("n6", at(10, 8, 40))]), "append");
  frame(w, "idle with the notices last", (ev) => ev, "fast", { working: false });
  frame(w, "the tail shrinks", (ev) => ev.slice(0, -1), "rebuild");
  frame(w, "a prompt lands again", (ev) => ev.concat([user("u12", at(10, 9, 30), "third question, again")]), "append");
  frame(w, "a prompt the next day", (ev) => ev.concat([user("u13", nextDay(0, 1, 0), "next morning")]), "append");
  assert.ok(units(project(w.v.el)).some((r) => r.uuid == null && r.cls.includes("day-divider")), "a day divider stands among the units (the block appends it)");
  frame(w, "a reply the next day", (ev) => ev.concat([reply("a14", nextDay(0, 1, 30), "next morning's answer")]), "append");
  frame(w, "idle the next day", (ev) => ev, "fast", { working: false });
});

test("normal mode, a change below a browsed window: the browse branch patches the window's worked footers in both directions (the footer lands on the window's last reply when the completing prompt lands below it; comes off when a later reply joins the turn below it), replaces no node, and the window equals a rebuild of the same state (the maintainer's round 3 ruling B: compact mode's spacer branch was fixed for this in the author's pass 1b and this branch was not; red here at the head the round ruled on, the footer missing against the rebuild's)", () => {
  // the compact test above on the other side of the switch: in normal mode every event is a unit, so a4 is unit 6 and the injected line unit 7
  const w = world(base().concat([sysNotice("x5", at(10, 5, 0))]), new Set(), true, undefined, false);
  browse(w, 0, 7);
  assert.equal(footerOn(w, "a4"), null, "the open turn's reply carries no footer while the session works");
  spacerFrame(w, "a prompt completes the turn below the window", (ev) => ev.concat([user("u6", at(10, 6, 0), "third question")]), { working: true });
  assert.equal(footerOn(w, "a4"), String(at(10, 4, 20) - at(10, 0, 0)), "the completing prompt below the window put the footer on the window's last reply (at the head: none, the branch grew the spacer and returned)");
  const w2 = world(base().concat([sysNotice("x5", at(10, 5, 0))]), new Set(), false, undefined, false);
  browse(w2, 0, 7);
  assert.equal(footerOn(w2, "a4"), String(at(10, 4, 20) - at(10, 0, 0)), "idle: the footer is on the turn's last reply");
  spacerFrame(w2, "a reply joins the turn below the window", (ev) => ev.concat([reply("a6", at(10, 5, 30), "second answer, continued")]));
  assert.equal(footerOn(w2, "a4"), null, "no longer the turn's last reply: the footer came off, below a browsed window");
});

// ── normal mode under a HEAD GAP (the maintainer's round 5 ruling, regression-1) ──────────────────────────────────────────────────────
// The list carries the regions' gaps in normal mode too (displayItems runs withGapItems in both modes), so with a head gap the list's
// unit 0 is the gap and every event's unit is its index plus one. At the head that round ruled on, normal mode's sites handed the footer
// patch NO unit list and its no-list arm mapped the event index onto data-unit, so the footer landed on the row above the reply (the fast
// path and the browse branch) or on none, and the exact tail tagged its rows by event index and trimmed from one, so the window's rows
// (appendItem's, by unit) and the tail's disagreed and the trim dropped a row. The three cells below drive both: the footer's row is
// asserted by the UNIT it names, and every frame's DOM is compared with a rebuild of the same state.

test("normal mode under a head gap, the footer lands on the row whose unit names the turn's last reply: the fast path's patch after a window build, then the exact tail's appends, a reply landing while idle, a prompt completing the turn, a shrink and the next append; every frame equals a rebuild (the maintainer's round 5 ruling, regression-1)", () => {
  const w = world(base(), new Set(), true, 0, false);
  const items = w.items();
  assert.equal(items[0].kind, "gap", "the head gap is the list's unit 0");
  // the window as production first builds it (renderWindowItems, rows tagged by unit through appendItem), so the fast path's patch below
  // runs over correctly tagged rows and the footer's landing is the one thing under test
  w.L.renderWindowItems(w.v, w.s, items, 0, items.length, workingOf(w, "the window build"));
  w.frames.push("window build [0, " + items.length + ")");
  compare(w, "the window build");
  const unitOfUuid = (uuid: string): number => w.items().findIndex((it) => it.kind === "event" && w.s.events[it.index].uuid === uuid);
  /** The row carrying `uuid`, its unit checked against the list's, and the footer on it (null: none); the row above it has none, since the
   *  footer that used to land there (the event index onto data-unit, one unit above under a head gap) is the ruled defect's shape. */
  const footerByUnit = (uuid: string): string | null => {
    const rows = units(project(w.v.el)), r = rows.find((x) => x.uuid === uuid);
    assert.ok(r, uuid + " has a row"); assert.equal(r!.unit, unitOfUuid(uuid), uuid + "'s row carries the unit the list gives it (its event index plus the head gap)");
    const above = rows.find((x) => x.unit === r!.unit - 1 && !x.cls.includes("day-divider"));
    if (above && above.uuid !== uuid) assert.equal(above.footer, null, "the row above " + uuid + "'s (unit " + above.unit + ", " + above.cls + ") carries no footer: at the head the maintainer's round 5 ruled on, the event index onto data-unit put it there");
    return r!.footer;
  };
  frame(w, "idle", (ev) => ev, "fast", { working: false });
  assert.equal(footerByUnit("a4"), String(at(10, 4, 20) - at(10, 0, 0)), "idle: the footer is on the row whose unit names the turn's last reply, a4's, with the turn's seconds");
  frame(w, "working again", (ev) => ev, "fast", { working: true });
  assert.equal(footerByUnit("a4"), null, "back at work: no footer on a4's row");
  for (let i = 1; i <= 2; i++) frame(w, "reply grows " + i, (ev) => { ev[ev.length - 1] = reply("a4", at(10, 4, 20), "second answer, more words " + i); return ev; }, "append");
  frame(w, "a reply after a tool", (ev) => ev.concat([tool("t6", at(10, 5, 0), "Bash"), reply("a9", at(10, 6, 40), "third answer")]), "append");
  frame(w, "idle again", (ev) => ev, "fast", { working: false });
  assert.equal(footerByUnit("a9"), String(at(10, 6, 40) - at(10, 0, 0)), "the footer on the tail-appended reply's row, by the unit the list gives it");
  frame(w, "a reply lands while idle", (ev) => ev.concat([reply("a10", at(10, 7, 10), "third answer, continued")]), "append");
  assert.equal(footerByUnit("a10"), String(at(10, 7, 10) - at(10, 0, 0)), "the footer moved to the new last reply's row, by unit");
  assert.equal(footerByUnit("a9"), null, "…and came off the reply before it");
  frame(w, "a prompt completes the turn", (ev) => ev.concat([user("u11", at(10, 8, 0), "third question")]), "append", { working: true });
  assert.equal(footerByUnit("a10"), String(at(10, 7, 10) - at(10, 0, 0)), "complete: the footer stays on a10's row");
  frame(w, "the tail shrinks", (ev) => ev.slice(0, -1), "rebuild");
  frame(w, "a prompt lands again", (ev) => ev.concat([user("u12", at(10, 9, 30), "third question, again")]), "append");
  // the next day under the head gap (the maintainer's round 6 ruling, extra6-1: the executed witness of render.ts's divider tag): the prompt
  // opens a day, so the block appends the divider a rebuild draws above it, tagged by the list's UNIT; the executor reads every child's
  // data-unit, the divider's too, so a divider tagged by the event index (one below its unit under the head gap) is a new node below u0 and
  // reds there; then the prompt is edited in place (the trim from its unit must take the divider with it, or the re-append draws a second
  // and the rebuild disagrees), and a reply follows it. The window build drew the first day's divider above the first event (its unit is
  // 1 under the head gap), so the dividers are read by UNIT: the first event's and the next day's prompt's, both derived from the list.
  frame(w, "a prompt the next day", (ev) => ev.concat([user("u13", nextDay(0, 1, 0), "next morning")]), "append");
  const dividerUnits = (): number[] => units(project(w.v.el)).filter((r) => r.uuid == null && r.cls.includes("day-divider")).map((r) => r.unit);
  assert.deepEqual(dividerUnits(), [unitOfUuid("u0"), unitOfUuid("u13")], "two day dividers stand among the units, by unit: the window build's above the first event (its unit under the head gap) and the block's above the next day's prompt, tagged by the list's unit (the event index plus the head gap), never the event index");
  frame(w, "the next day's prompt is edited", (ev) => { ev[ev.length - 1] = user("u13", nextDay(0, 1, 0), "next morning, edited"); return ev; }, "append");
  assert.deepEqual(dividerUnits(), [unitOfUuid("u0"), unitOfUuid("u13")], "the edit's trim took the divider with the prompt's unit and the re-append drew it once: no duplicate divider");
  frame(w, "a reply the next day", (ev) => ev.concat([reply("a14", nextDay(0, 1, 30), "next morning's answer")]), "append");
  assert.deepEqual(dividerUnits(), [unitOfUuid("u0"), unitOfUuid("u13")], "the reply opens no day: the same two dividers");
});

test("normal mode under a head gap, a change below a browsed window: the browse branch's patch lands the footer on the row whose unit names the window's last reply, in both directions, and the window equals a rebuild (the maintainer's round 5 ruling, regression-1)", () => {
  // the normal-mode browse test above under a head gap: a4 is event 6 and unit 7, the injected line event 7 and unit 8
  const w = world(base().concat([sysNotice("x5", at(10, 5, 0))]), new Set(), true, 0, false);
  browse(w, 0, 8);
  assert.equal(footerOn(w, "a4"), null, "the open turn's reply carries no footer while the session works");
  spacerFrame(w, "a prompt completes the turn below the window", (ev) => ev.concat([user("u6", at(10, 6, 0), "third question")]), { working: true });
  const rows = units(project(w.v.el)), row = rows.find((x) => x.uuid === "a4");
  assert.ok(row && row.unit === 7 && row.footer != null, "the footer on a4's row, unit 7 (event 6 plus the head gap): " + JSON.stringify(row));
  assert.equal(rows.find((x) => x.unit === 6 && !x.cls.includes("day-divider"))?.footer, null, "the row above it (unit 6, the thinking row) carries none: at the head the maintainer's round 5 ruled on, the event index onto data-unit put it there");
  assert.equal(footerOn(w, "a4"), String(at(10, 4, 20) - at(10, 0, 0)), "the completing prompt below the window put the footer on the window's last reply");
  const w2 = world(base().concat([sysNotice("x5", at(10, 5, 0))]), new Set(), false, 0, false);
  browse(w2, 0, 8);
  assert.equal(footerOn(w2, "a4"), String(at(10, 4, 20) - at(10, 0, 0)), "idle: the footer is on the turn's last reply");
  spacerFrame(w2, "a reply joins the turn below the window", (ev) => ev.concat([reply("a6", at(10, 5, 30), "second answer, continued")]));
  assert.equal(footerOn(w2, "a4"), null, "no longer the turn's last reply: the footer came off, below a browsed window");
});

test("normal mode under a MID gap (turns the page does not hold between two runs it does), a change above the gap: the exact tail's trim drops the gap's element with the rows below it and the re-render draws the gap again as its unit, tagging the rows after it by unit, so every frame equals a rebuild (at the head the maintainer's round 5 ruled on, the loop walked the events and drew no gap, so the gap vanished from the DOM until the next window build)", () => {
  // the gap stands before event 3 (the first tool), unit 3 of eight; an edit of a1 (event 1) puts the first changed event's unit, 1, above it
  const w = world(base(), new Set(), true, 3, false);
  const items = w.items();
  assert.equal(items[3].kind, "gap", "the gap is unit 3");
  compare(w, "the first build");
  frame(w, "the first answer is edited above the gap", (ev) => { ev[1] = reply("a1", at(9, 58, 30), "first answer, edited"); return ev; }, "append");
  assert.equal(units(project(w.v.el)).filter((r) => r.cls.includes("tx-gap")).map((r) => r.unit).join(","), "3", "the gap stands again at unit 3 after the re-render from unit 1");
  assert.deepEqual(units(project(w.v.el)).filter((r) => !r.cls.includes("day-divider")).map((r) => r.unit), items.map((_, u) => u), "every unit 0 to the list's end, the gap among them (a divider shares its turn's unit and is left out here)");
  frame(w, "a reply lands below the gap", (ev) => ev.concat([reply("a7", at(10, 5, 0), "third answer")]), "append");
  frame(w, "idle", (ev) => ev, "fast", { working: false });
  assert.equal(footerOn(w, "a7"), String(at(10, 5, 0) - at(10, 0, 0)), "the footer on the reply below the gap, found by its unit");
});

test("normal mode, a hover held through a streamed frame: the band and its rings come off with the paint, the glow stays on the kept units and the ruler stands as applyGlow left it (the maintainer's round 3 ruling D on the other side of the switch: normal mode's tail took the rings and the glow off unconditionally since the author's pass 3)", () => {
  hoverThroughFrame(world(base(), new Set(), true, undefined, false));
});

test("normal mode, a hover's rail band as the thread's last child: the next streamed frame still renders what a rebuild renders (the shared trim reaches the units behind it), and nothing foreign is left among the units", () => {
  const w = world(base(), new Set(), true, undefined, false);
  frame(w, "a frame with the band present", (ev) => { ev[ev.length - 1] = reply("a4", at(10, 4, 20), "second answer, hovered"); return ev; }, "append", { band: true });
  frame(w, "a tool lands with the band present", (ev) => ev.concat([tool("t5", at(10, 5, 0), "Bash")]), "append", { band: true });
  frame(w, "a frame with no band", (ev) => ev.concat([reply("a8", at(10, 5, 40), "third answer")]), "append");
  assert.equal((w.v.el as FakeEl).children.filter((c) => c.classList.contains("rail-band")).length, 0, "the band is gone after the paint (a hover redraws it on the next mouseenter)");
});

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

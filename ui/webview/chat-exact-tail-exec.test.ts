// The chat's exact tail path, EXECUTED: chatTail and patchWorkedFooters lifted from render.ts and driven over
// stubs and a minimal fake DOM, the way tab-strip-skip-exec.test.ts lifts renderTabs. chat-exact-tail.test.ts
// pins the SHAPE of what no harness lifts (syncViewInner, reconcileRewind, the frame paths); this file drives
// the BEHAVIOUR of the two functions it can: the kernel's `from` is where the tail re-renders from, a shrunken
// tail or a change inside a window the reader scrolled away from still rebuilds the window, chatTail hands its
// `from` to the rewind pass as the bound, a gap asks for the full session; and the footer patch adds, removes
// and re-homes the fork spot by unit, skips a day divider sharing its turn's unit number, maps compact-mode
// units, and reaches a reply folded into a run by its row's position when the run is open (PR E; it marked the
// view stale before). Synthetic events; epochs are seconds.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inspect } from "node:util";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { workedFooterPlan } from "./worked-footer";
import { hideEdges, staysEnumerable } from "../test-dom-shim";

const requireCjs = createRequire(__filename);
const RENDER = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "render.ts"), "utf8");

/** A render.ts function, transpiled (TS → JS) with esbuild at run time, required dynamically so the test bundle
 *  does not try to bundle esbuild itself (the models-rev.test.ts pattern). */
function liftBetween(startAnchor: string, endAnchor: string): string {
  const a = RENDER.indexOf(startAnchor), b = RENDER.indexOf(endAnchor, a);
  assert.ok(a > 0 && b > a, `anchors not found: ${startAnchor.slice(0, 40)} or ${endAnchor.slice(0, 40)} moved; re-anchor`);
  return requireCjs("esbuild").transformSync(RENDER.slice(a, b), { loader: "ts" }).code;
}

// ── chatTail ──────────────────────────────────────────────────────────────────────────────────────

type TailHooks = { fulls: string[]; strips: number; rewinds: [string, number | undefined][]; optRecs: number;
                   tabRenders: number; appends: number; bgRenders: number; prebuilds: number };
type TailApi = { chatTail: (msg: any) => void; set: (p: { sessions?: Map<string, any>; views?: Map<string, any>; activeId?: string | null }) => void };

function liftChatTail(): (hooks: TailHooks) => TailApi {
  const js = liftBetween("function chatTail(msg: any) {", "// Older history streaming in from a loadOlder request");
  const prelude = `
    let sessions = new Map(), views = new Map(), activeId = null;
    const ledgers = new Map();
    const H = HOOKS;
    const requestFullSession = (id) => { H.fulls.push(id); };
    const skeletonTabs = { ids: new Set(HOOKS.skeleton || []) };   // a skeleton tab's tail asks for the full instead of splicing (the reconnect regime); the default world holds none
    const isOptimistic = (e) => !!e.opt;
    const stripOptimistic = (s) => { s.events = s.events.filter((e) => !e.opt); H.strips++; };
    const reconcileRewind = (s, bound) => { H.rewinds.push([s.id, bound]); };
    const isHeldGroup = (e) => !!e.held;                 // a group the client made for held kernel copies (T262i): not kernel coordinates
    const reconcileHeldCopies = () => {};                // the held-copy pass runs between the rewind and the pending sends (T262i)
    const reconcileOptimistic = () => { H.optRecs++; };
    const awaitKey = (st) => JSON.stringify((st && st.awaitingWhy) || "");
    const scheduleRenderTabs = () => { H.tabRenders++; };
    const pendingFlags = new Map(); const applyFrameFlags = () => [];   // the view flags' pending guard (flag-pending.ts, 2026-09-14): no click in these worlds
    const scheduleAppendActive = () => { H.appends++; };
    const renderBgTasks = () => { H.bgRenders++; };
    const awaitChanged = (_sid) => { H.bgRenders++; };   // 2026-09-10: the tail calls this (box + a viewer's header); it counts as the box render
    const schedulePrebuild = () => { H.prebuilds++; };
    const renderPinnedNotes = () => {};                  // the pinned-notes strip rides the active tab's tail frame (a fork seam, 2026-09-08): inert here
    const regionsAbsorbTail = () => {};                  // the tail run's regions follow the events (T386 stage 2); this slice holds no regions
  `;
  const epilogue = `
    return { chatTail, set: (p) => { if (p.sessions) sessions = p.sessions; if (p.views) views = p.views; if ("activeId" in p) activeId = p.activeId; } };
  `;
  return new Function("HOOKS", prelude + js + epilogue) as (hooks: TailHooks) => TailApi;
}

const kernelEvents = (n: number) => Array.from({ length: n }, (_, i) => ({ kind: i % 2 ? "assistant" : "user", uuid: "e" + i }));
function tailWorld(opts: { rendered: number; winEnd: number; unitTotal: number; active: boolean; headFrom?: number; opt?: boolean }) {
  const H: TailHooks = { fulls: [], strips: 0, rewinds: [], optRecs: 0, tabRenders: 0, appends: 0, bgRenders: 0, prebuilds: 0 };
  const api = liftChatTail()(H);
  const events: any[] = kernelEvents(10);
  if (opts.opt) events.splice(6, 0, { kind: "user", uuid: "opt-1", opt: true });   // a bubble at its send slot, mid-array
  const s: any = { id: "A", events, status: { state: "working" }, headFrom: opts.headFrom };
  const v: any = { rendered: opts.rendered, stale: false, winStart: 0, winEnd: opts.winEnd, unitTotal: opts.unitTotal, el: {} };
  api.set({ sessions: new Map([["A", s]]), views: new Map([["A", v]]), activeId: opts.active ? "A" : "B" });
  return { H, api, s, v };
}

test("a tail for a skeleton tab asks for the full session and touches nothing: the page holds no current copy to splice onto", () => {
  const { H, api, s, v } = tailWorld({ rendered: 10, winEnd: 10, unitTotal: 10, active: true });
  const skel = liftChatTail()({ ...H, skeleton: ["A"] } as any);
  skel.set({ sessions: new Map([["A", s]]), views: new Map([["A", v]]), activeId: "A" });
  skel.chatTail({ id: "A", from: 7, events: [{ kind: "assistant", uuid: "e7b" }] });
  assert.deepEqual(H.fulls, ["A"], "the full is asked for once");
  assert.equal(s.events.length, 10, "the held events are not spliced");
  assert.equal(v.rendered, 10, "nothing repaints");
  assert.equal(H.rewinds.length, 0);
  assert.equal(H.appends, 0);
});

test("the active view re-renders from the kernel's exact first changed event; the rewind pass is bounded there", () => {
  const { H, api, s, v } = tailWorld({ rendered: 10, winEnd: 10, unitTotal: 10, active: true });
  api.chatTail({ id: "A", from: 7, events: [{ kind: "assistant", uuid: "e7b" }, { kind: "user", uuid: "e8b" }, { kind: "assistant", uuid: "e9b" }] });
  assert.equal(v.rendered, 7, "repaint from the exact changed point, not a trailing window");
  assert.equal(v.stale, false, "nothing earlier changed: no window rebuild");
  assert.deepEqual(s.events.slice(7).map((e: any) => e.uuid), ["e7b", "e8b", "e9b"], "the suffix is replaced from `from`");
  assert.deepEqual(H.rewinds, [["A", 7]], "chatTail passes its from as the bound: the editable set is judged below the tail's start");
  assert.equal(H.appends, 1, "one paint scheduled"); assert.equal(H.tabRenders, 1); assert.deepEqual(H.fulls, []);
  api.chatTail({ id: "A", from: 9, events: [{ kind: "assistant", uuid: "e9c" }] });
  assert.equal(v.rendered, 7, "an earlier re-render start stands: min(rendered, from)");
});

test("a tail that shrinks the transcript rebuilds the window: rendered would equal the length and the fast path would skip the repaint", () => {
  const { api, s, v } = tailWorld({ rendered: 10, winEnd: 10, unitTotal: 10, active: true });
  api.chatTail({ id: "A", from: 9, events: [] });   // the last queued message retired with nothing in its place
  assert.equal(s.events.length, 9);
  assert.equal(v.rendered, 9);
  assert.equal(v.stale, true, "a pure truncation marks the view stale");
});

/** A suffix replacing events [from, 10) one for one: the transcript keeps its length, so the shrink rule (its own
 *  test above) stays out of these cases and what they show is the window rule alone. */
const sameLengthFrom = (from: number) => Array.from({ length: 10 - from }, (_, i) => ({ kind: (from + i) % 2 ? "assistant" : "user", uuid: "r" + (from + i) }));

test("a background view: a change inside a window the reader scrolled away from rebuilds it; one below the window, or at the tail, repaints from `from`", () => {
  const away = tailWorld({ rendered: 10, winEnd: 6, unitTotal: 10, active: false });   // window [0,6) of 10 units: not at the tail
  away.api.chatTail({ id: "A", from: 8, events: sameLengthFrom(8) });
  assert.equal(away.v.stale, false, "the change lies below the window: the incremental path's assumption holds");
  assert.equal(away.v.rendered, 8);
  away.api.chatTail({ id: "A", from: 4, events: sameLengthFrom(4) });
  assert.equal(away.v.stale, true, "the change landed inside the scrolled-away window (nothing shrank): rebuild");
  assert.equal(away.H.prebuilds, 2, "the off-screen view is rebuilt in idle either way");
  assert.equal(away.H.appends, 0, "no active paint for a background tab");
  const atTail = tailWorld({ rendered: 10, winEnd: 10, unitTotal: 10, active: false });
  atTail.api.chatTail({ id: "A", from: 4, events: sameLengthFrom(4) });
  assert.equal(atTail.v.stale, false, "at the tail, an exact repaint from `from` is enough");
  assert.equal(atTail.v.rendered, 4);
});

test("a delta starting past what the client holds is a desync: ask for the full session, touch nothing; below the loaded head, nothing", () => {
  const { H, api, s, v } = tailWorld({ rendered: 10, winEnd: 10, unitTotal: 10, active: true });
  api.chatTail({ id: "A", from: 11, events: [{ kind: "user", uuid: "q" }] });
  assert.deepEqual(H.fulls, ["A"]);
  assert.equal(s.events.length, 10); assert.equal(v.rendered, 10); assert.deepEqual(H.rewinds, []);
  api.chatTail({ id: "Z", from: 0, events: [] });
  assert.deepEqual(H.fulls, ["A", "Z"], "a session the client holds no base for asks too");
  const headed = tailWorld({ rendered: 10, winEnd: 10, unitTotal: 10, active: true, headFrom: 5 });
  headed.api.chatTail({ id: "A", from: 3, events: [] });   // global index 3 < headFrom 5: our resident tail is still valid
  assert.equal(headed.s.events.length, 10); assert.deepEqual(headed.H.rewinds, []);
  headed.api.chatTail({ id: "A", from: 12, events: [{ kind: "user", uuid: "n" }] });   // global 12 → local 7
  assert.equal(headed.v.rendered, 7, "msg.from is a global index: mapped through headFrom");
});

test("an optimistic bubble is not in the kernel's coordinate space: the gap check counts kernel events, and the bubble is stripped before the delta applies", () => {
  const { H, api, s, v } = tailWorld({ rendered: 11, winEnd: 11, unitTotal: 11, active: true, opt: true });
  assert.equal(s.events.length, 11);
  api.chatTail({ id: "A", from: 10, events: [{ kind: "user", uuid: "e10" }] });   // one past the kernel's ten: an append, not a gap
  assert.deepEqual(H.fulls, [], "ten kernel events held: from = 10 is the next one");
  assert.equal(H.strips, 1);
  assert.deepEqual(s.events.map((e: any) => e.uuid).slice(9), ["e9", "e10"], "the bubble is gone and the delta appended in kernel coordinates");
  assert.equal(H.optRecs, 1, "…and the in-flight send is re-asserted or retired after");
  assert.equal(v.rendered, 10);
});

test("a status-only tail (empty suffix) replaces the status and re-renders the awaiting box only when the awaited fields changed", () => {
  const { H, api, s, v } = tailWorld({ rendered: 10, winEnd: 10, unitTotal: 10, active: true });
  api.chatTail({ id: "A", from: 10, events: [], status: { state: "ready" } });
  assert.equal(s.status.state, "ready"); assert.equal(v.rendered, 10); assert.equal(v.stale, false);
  assert.equal(H.bgRenders, 0, "no awaited field changed");
  api.chatTail({ id: "A", from: 10, events: [], status: { state: "working", awaitingWhy: "agents" } });
  assert.equal(H.bgRenders, 1, "the awaiting box renders from the same frame that flips the chip");
});

// ── patchWorkedFooters ────────────────────────────────────────────────────────────────────────────

/** Enough of Element for the footer patch: children, a class list, data-unit, and the two selector shapes it uses. */
class FakeEl {
  children!: FakeEl[]; parent: FakeEl | null = null; dataset: Record<string, string> = {}; textContent = ""; title = "";
  constructor(public tag: string, public className = "") {
    // the edges are non-enumerable, and so is every other object the node holds (hideEdges, ui/test-dom-shim.ts): a
    // failing assertion's dump of a node is its own primitives, never the tree it hangs in
    Object.defineProperty(this, "children", { value: [], writable: true, enumerable: false, configurable: true });
    hideEdges(this);
  }
  has(c: string): boolean { return this.className.split(/\s+/).includes(c); }
  appendChild(c: FakeEl): FakeEl { c.parent?.removeChild(c); c.parent = this; this.children.push(c); return c; }
  removeChild(c: FakeEl): void { this.children = this.children.filter((x) => x !== c); c.parent = null; }
  remove(): void { this.parent?.removeChild(this); }
  private select(sel: string): FakeEl[] {
    // ':scope > [data-unit="N"]:not(.day-divider)' and ':scope > .cls', the patch's two shapes
    const m = /^:scope > (.+)$/.exec(sel);
    if (!m) throw new Error("unsupported selector " + sel);
    const attr = /\[data-unit="([^"]*)"\]/.exec(m[1]), cls = /^\.([\w-]+)/.exec(m[1]), not = /:not\(\.([\w-]+)\)/.exec(m[1]);
    return this.children.filter((c) => (!attr || c.dataset.unit === attr[1]) && (!cls || c.has(cls[1])) && (!not || !c.has(not[1])));
  }
  querySelector(sel: string): FakeEl | null { return this.select(sel)[0] ?? null; }
  querySelectorAll(sel: string): FakeEl[] { return this.select(sel); }   // the patch reads a run's nodes by position (PR E)
}
type FootHooks = { FakeEl: typeof FakeEl; workedFooterPlan: typeof workedFooterPlan };
type Patch = (v: any, s: any, from: number, working: boolean, items?: any[] | null) => void;

function liftPatch(): (hooks: FootHooks) => Patch {
  const js = liftBetween("function patchWorkedFooters(", "// prevEpoch for event i");
  // itemFirstEvent is LIFTED with the patch, never hand-copied: a copy without the gap case (a gap's first event is its `before`, not an
  // `index`) mis-modelled the one unit kind whose first event is not `index`, and a window opening on a gap read NaN (the maintainer's round 1 addendum)
  const first = liftBetween("function itemFirstEvent(", "// The display-unit index");
  const prelude = `
    const H = HOOKS;
    const workedFooterPlan = H.workedFooterPlan;
    const eventEpoch = (ev) => (ev.t == null ? null : ev.t);
    const elapsedFooter = (secs) => { const f = new H.FakeEl("div", "turn-elapsed"); f.textContent = String(secs); return f; };
  `;
  return new Function("HOOKS", prelude + first + js + "\nreturn patchWorkedFooters;") as (hooks: FootHooks) => Patch;
}

const user = (t: number) => ({ kind: "user", human: true, t });
const reply = (t: number) => ({ kind: "assistant", t });
const tool = (t: number) => ({ kind: "tool", t });
/** A rendered window: one node per unit tagged data-unit, unit `spotOn` carrying a fork spot. */
function footWorld(events: any[], units: number, spotOn: number) {
  const patch = liftPatch()({ FakeEl, workedFooterPlan });
  const el = new FakeEl("div");
  const nodes: FakeEl[] = [];
  for (let u = 0; u < units; u++) { const n = new FakeEl("div", "turn"); n.dataset.unit = String(u); el.appendChild(n); nodes.push(n); }
  const spot = new FakeEl("span", "fork-spot"); nodes[spotOn].appendChild(spot);
  const v: any = { el, winStart: 0, stale: false };
  return { patch, v, s: { events }, nodes, spot };
}

test("the footer patch adds the elapsed row to the turn's last reply once its turn completes, moving the fork spot into it; a repeat adds nothing", () => {
  const events = [user(100), tool(110), reply(160), user(200)];
  const { patch, v, s, nodes, spot } = footWorld(events, 4, 2);
  patch(v, s, 3, true);                                          // the prompt at 3 just landed: the tail re-rendered [3, 4)
  const f = nodes[2].querySelector(":scope > .turn-elapsed");
  assert.ok(f, "the reply before `from` gained its footer"); assert.equal(f!.textContent, "60");
  assert.equal(spot.parent, f, "the fork spot moved into the new elapsed row, where applyForkSpots places it");
  assert.equal(nodes[3].querySelector(":scope > .turn-elapsed"), null, "the prompt carries none");
  patch(v, s, 3, true);
  assert.equal(nodes[2].children.filter((c) => c.has("turn-elapsed")).length, 1, "already there: not added twice");
  assert.equal(v.stale, false);
});

test("…and takes it off when a reply lands in the same turn (the footer moved to the new last reply), the spot back onto the turn", () => {
  const { patch, v, s, nodes, spot } = footWorld([user(100), tool(110), reply(160), user(200)], 4, 2);
  patch(v, s, 3, true);
  s.events = [user(100), tool(110), reply(160), reply(170)];   // the kernel replaced the suffix: another reply, same turn
  patch(v, s, 3, true);
  assert.equal(nodes[2].querySelector(":scope > .turn-elapsed"), null, "demoted: no longer the turn's last reply");
  assert.equal(spot.parent, nodes[2], "the fork spot is back on the turn itself");
});

test("the session going idle with an empty suffix (from = len) completes the final turn; going back to work takes the footer off again", () => {
  const events = [user(100), tool(110), reply(160)];
  const { patch, v, s, nodes } = footWorld(events, 3, 2);
  patch(v, s, 3, true);
  assert.equal(nodes[2].querySelector(":scope > .turn-elapsed"), null, "still working: the live spinner owns the final turn");
  patch(v, s, 3, false);
  assert.equal(nodes[2].querySelector(":scope > .turn-elapsed")?.textContent, "60", "idle: the footer");
  patch(v, s, 3, true);
  assert.equal(nodes[2].querySelector(":scope > .turn-elapsed"), null, "a nudge put it back to work on the same turn");
});

test("a day divider shares its turn's unit number and is never the footer's home", () => {
  const { patch, v, s, nodes } = footWorld([user(100), tool(110), reply(160), user(200)], 4, 2);
  const divider = new FakeEl("div", "day-divider"); divider.dataset.unit = "2";
  v.el.children.splice(2, 0, divider); divider.parent = v.el;   // the divider precedes its turn in the DOM
  patch(v, s, 3, true);
  assert.equal(divider.children.length, 0, "the divider got nothing");
  assert.ok(nodes[2].querySelector(":scope > .turn-elapsed"), "the turn did");
});

test("a window that opens ON a gap: the patch reads the window's first event through production's itemFirstEvent (a gap's `before`), so the footer lands and comes off; the harness's hand copy read the gap's index as undefined, the plan was empty, and neither direction ran (the maintainer's round 1 addendum)", () => {
  const events = [user(100), tool(110), reply(160)];
  const items = [{ kind: "gap", lo: 0, hi: 5, before: 0 }, { kind: "event", index: 0 }, { kind: "event", index: 1 }, { kind: "event", index: 2 }];
  const { patch, v, s, nodes } = footWorld(events, 4, 3);   // unit 0 is the gap element, units 1..3 the three events
  v.winStart = 0;
  patch(v, s, 3, false, items);   // idle with the suffix empty: the turn is complete, the reply (event 2, unit 3) gains its footer
  assert.equal(nodes[3].querySelector(":scope > .turn-elapsed")?.textContent, "60", "the add direction: the footer on the reply behind the gap-headed window");
  assert.equal(nodes[0].querySelector(":scope > .turn-elapsed"), null, "the gap element got nothing");
  s.events = [user(100), tool(110), reply(160), reply(170)];   // another reply in the same turn: the footer moves off
  patch(v, s, 3, true, items);
  assert.equal(nodes[3].querySelector(":scope > .turn-elapsed"), null, "the remove direction: the stale footer comes off");
});

test("compact mode: the window start is a unit and the plan wants an event index; the reply's event maps back to its unit; a reply folded into a run is patched by position when the run is open, and left alone (never stale) when it is collapsed", () => {
  const events = [user(100), tool(110), tool(120), reply(160), user(200)];
  // units: the prompt, one folded tool run, the reply, the prompt
  const items = [{ kind: "event", index: 0 }, { kind: "toolgroup", indices: [1, 2] }, { kind: "event", index: 3 }, { kind: "event", index: 4 }];
  const { patch, v, s, nodes } = footWorld(events, 4, 2);
  patch(v, s, 4, true, items);
  assert.ok(nodes[2].querySelector(":scope > .turn-elapsed"), "event 3 is unit 2: the footer lands on the reply's unit");
  assert.equal(v.stale, false);
  // the reply itself folded into a notice run that is COLLAPSED: its row is not on screen, nothing is patched and the view is not
  // marked stale (until PR E it was, and in compact mode's incremental tail that made the next paint a full rebuild whenever the
  // event before the streaming reply sat inside a run: the everyday agentic shape)
  const folded = [{ kind: "event", index: 0 }, { kind: "noticegroup", indices: [1, 2, 3] }, { kind: "event", index: 4 }];
  const w2 = footWorld(events, 3, 1);
  w2.patch(w2.v, w2.s, 4, true, folded);
  assert.equal(w2.v.stale, false, "a collapsed run shows no row for the reply: nothing to patch, no rebuild asked");
  assert.ok(w2.nodes.every((n) => !n.querySelector(":scope > .turn-elapsed")), "…and nothing was patched by hand, the head least of all");
  // the same run OPEN: the head, then a row per member, all carrying the run's unit; member 2 (event 3) is the third row of unit 1
  const w4 = footWorld(events, 3, 1);
  const rows = [1, 2, 3].map((i) => { const r = new FakeEl("div", "turn tg-child"); r.dataset.unit = "1"; return r; });
  const headIdx = w4.v.el.children.indexOf(w4.nodes[1]);
  w4.v.el.children.splice(headIdx + 1, 0, ...rows); for (const r of rows) r.parent = w4.v.el;
  w4.patch(w4.v, w4.s, 4, true, folded);
  assert.ok(rows[2].querySelector(":scope > .turn-elapsed"), "the reply's own row got the footer");
  assert.ok(!rows[0].querySelector(":scope > .turn-elapsed") && !rows[1].querySelector(":scope > .turn-elapsed") && !w4.nodes[1].querySelector(":scope > .turn-elapsed"), "not the head, not the other members");
  assert.equal(w4.v.stale, false);
  // a tool inside a run before the streaming reply (the agentic shape): the plan names it, the collapsed run has no row for it, nothing happens
  const agentic = [user(100), tool(110), tool(120), reply(160)];
  const runItems = [{ kind: "event", index: 0 }, { kind: "toolgroup", indices: [1, 2] }, { kind: "event", index: 3 }];
  const w5 = footWorld(agentic, 3, 1);
  w5.patch(w5.v, w5.s, 3, true, runItems);   // the reply at 3 streams: the tail re-rendered [3, 4); the plan names the tool at 2
  assert.equal(w5.v.stale, false, "no rebuild asked for the everyday agentic shape");
  // a window whose start unit is past the items: winEv falls to the event count, so the plan sees no reply before it
  const w3 = footWorld(events, 4, 2); w3.v.winStart = 9;
  w3.patch(w3.v, w3.s, 4, true, items);
  assert.ok(w3.nodes.every((n) => !n.querySelector(":scope > .turn-elapsed")));
});

test("compact mode: a continuation with no user line (the first changed event is a hidden thinking block, working flips in the same frame) takes the footer off the reply before it when the patch is told the first CHANGED event; told `len`, it names the thinking row and leaves the footer", () => {
  // the seam's from (the author's pass 0, low): syncViewInner passes Math.min(v.rendered, first re-rendered event); with no unit reaching the
  // change the second term is `len`, and the plan then scans down from len - 1 to the thinking event, which has no node in compact mode
  const thinking = (t: number) => ({ kind: "thinking", t });
  const idle = [user(100), tool(110), reply(160)];
  const items = [{ kind: "event", index: 0 }, { kind: "event", index: 1 }, { kind: "event", index: 2 }];
  const w = footWorld(idle, 3, 2);
  w.patch(w.v, w.s, 3, false, items);
  assert.equal(w.nodes[2].querySelector(":scope > .turn-elapsed")?.textContent, "60", "the idle session's reply carries its footer");
  w.s.events = [user(100), tool(110), reply(160), thinking(200)];   // the session resumes the same turn: a thinking atom lands, status working
  w.patch(w.v, w.s, 3, true, items);                                 // from = the first changed event (v.rendered = 3): the plan names the reply
  assert.equal(w.nodes[2].querySelector(":scope > .turn-elapsed"), null, "the reply is no longer the turn's last event and the session works: the footer comes off");
  // the same shape with from = len (the first re-rendered event when no unit reaches the change): the plan names the thinking row, no node
  const w2 = footWorld(idle, 3, 2);
  w2.patch(w2.v, w2.s, 3, false, items);
  w2.s.events = [user(100), tool(110), reply(160), thinking(200)];
  w2.patch(w2.v, w2.s, 4, true, items);
  assert.equal(w2.nodes[2].querySelector(":scope > .turn-elapsed")?.textContent, "60", "told `len`, the patch leaves the stale footer: the argument the seam must not pass");
  assert.deepEqual(workedFooterPlan(w2.s.events, 4, 0, true, (ev: any) => ev.t ?? null), [{ unit: 3, secs: null }], "…because the plan names the hidden event");
  assert.deepEqual(workedFooterPlan(w2.s.events, 3, 0, true, (ev: any) => ev.t ?? null), [{ unit: 2, secs: null }], "from the first changed event it names the reply");
});

// ── the stand-in's nodes inspect as their own projection (ui/test-dom-shim.ts) ────────────────────
test("a stand-in node enumerates its primitives alone, and a dump of one names neither its children nor its parent", () => {
  const root = new FakeEl("div"), turn = new FakeEl("div", "turn"); root.appendChild(turn); turn.dataset.unit = "3"; turn.textContent = "alpha";
  for (const n of [root, turn]) {
    for (const k of Object.keys(n)) assert.ok(staysEnumerable((n as any)[k]), k + " is enumerable and holds a " + typeof (n as any)[k]);
    const dump = inspect(n, { compact: false, customInspect: false, depth: 1000, maxArrayLength: Infinity, showHidden: false, showProxy: false, sorted: true, getters: true });
    assert.ok(!dump.includes("children") && !dump.includes("parent"), "a dump stays on the node: " + dump);
  }
  assert.ok(turn.parent === root && root.children[0] === turn, "the edges still hold the tree");
  assert.ok(root.querySelector(':scope > [data-unit="3"]') === turn); turn.remove(); assert.equal(root.children.length, 0);
});

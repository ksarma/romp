// scrollToAnchor's roads behind its flagged window build, EXECUTED (PR E review round 2, G: a census keyed on the road, not the spelling).
// A deep-link land whose target is not resident renders a window around the anchor's unit through renderWindowItems with `anchored`
// true, the build's take of the parked figures (spacer-measure.test.ts pins the flag's spelling), and then re-queries the target: the
// spelling census stayed green with a `return false` planted right after that build, a take followed by no write. Here the function is
// lifted from render.ts over a stand-in view and driven road by road, so the pin reads what follows the take: a resident target lands
// with no build; a target rendered by the build lands on it (landOn) in the same pass; a keep-offset re-land restores the offset; a
// target the build's re-query does not find, or of the wrong kind, returns with no write and the build's take already made (the
// take-then-no-write roads the PR body discloses, reached from the three direct callers, markjump, replyjump and cmtjump: landActive's
// and keepPlaceAcrossWindow's calls run after a take of their own, so the build there finds nothing parked, and landNearestMoment's
// take is dead for the same reason); an anchor older than the resident tail asks for the chunk and builds nothing. Synthetic uuids.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import type { DisplayItem } from "./compact";
import { hideEdges } from "../test-dom-shim";

const requireCjs = createRequire(__filename);
const RENDER = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "render.ts"), "utf8");

function liftBetween(startAnchor: string, endAnchor: string): string {
  const a = RENDER.indexOf(startAnchor), b = RENDER.indexOf(endAnchor, a);
  assert.ok(a > 0 && b > a, `anchors not found: ${startAnchor.slice(0, 40)} or ${endAnchor.slice(0, 40)} moved; re-anchor`);
  return requireCjs("esbuild").transformSync(RENDER.slice(a, b), { loader: "ts" }).code;
}

/** A turn row: a class list (the kind guard reads it) and the data-* the five selectors read (uuid, orphan-of, mid, mids, uuids). */
class Row {
  dataset: Record<string, string> = {};
  constructor(public className: string, uuid: string) { this.dataset.uuid = uuid; hideEdges(this); }
  get classList() { const c = this.className.split(/\s+/); return { contains: (x: string) => c.includes(x) }; }
  getBoundingClientRect() { return { top: 100, bottom: 140 }; }
}
/** The view's host: `.turn[data-KEY="V"]` and `.turn[data-KEY~="V"]` (the whitespace-separated token), the selectors scrollToAnchor uses. */
class Host {
  children: Row[] = [];   // the DOM edge name, the shape the edge-initialiser detector reads
  constructor() { hideEdges(this); }
  querySelector(sel: string): Row | null {
    const m = /^\.turn\[data-([\w-]+)(~?)="([^"]*)"\]$/.exec(sel);
    assert.ok(m, "scrollToAnchor's selector shape: " + sel);
    const key = m![1].replace(/-([a-z])/g, (_, c: string) => c.toUpperCase());
    return this.children.find((r) => { const v = r.dataset[key]; return v != null && (m![2] ? v.split(/\s+/).includes(m![3]) : v === m![3]); }) ?? null;
  }
}

type Ev = { kind: string; uuid: string };
type Opts = { resident?: string[]; events: Ev[]; rendersOnBuild?: boolean; intent?: string | null; keepY?: number | null; headFrom?: number; proto?: number; older?: boolean };
type World = { host: Host; calls: any[]; writes: any[]; rows: any[]; toasts: string[]; state: () => { pendingAnchor: string | null; pendingAnchorIntent: string | null; pendingAnchorKeepY: number | null; anchorPendingOlder: boolean; landTrail: string[] }; jump: (uuid: string) => boolean };

/** A view holding `resident` uuids as rows, over a session of `events` (a unit per event); the stubbed renderWindowItems records the
 *  flag it is handed and, when `rendersOnBuild`, gives the anchor its row (the re-query then finds it); `intent` is the kind guard's,
 *  `keepY` a re-land's kept offset; `headFrom` and `older` shape the older-than-the-tail branch. */
function world(o: Opts): World {
  const host = new Host();
  for (const u of o.resident ?? []) host.children.push(new Row("turn " + (o.events.find((e) => e.uuid === u)?.kind === "user" ? "turn-user" : "turn-assistant"), u));
  const s: any = { id: "A", events: o.events, status: { state: "working" }, proto: o.proto ?? 1, headFrom: o.headFrom ?? 0, regions: undefined };
  const v: any = { el: host };
  const H: any = { host, s, v, calls: [] as any[], writes: [] as any[], rows: [] as any[], toasts: [] as string[], intent: o.intent ?? null, keepY: o.keepY ?? null, older: !!o.older,
                   build: (uuid: string) => { if (o.rendersOnBuild) { const ev = o.events.find((e) => e.uuid === uuid); host.children.push(new Row("turn " + (ev?.kind === "user" ? "turn-user" : "turn-assistant"), uuid)); } } };
  const js = liftBetween("function scrollToAnchor(uuid: string): boolean {", "/** The atoms of the transcript turn");
  const prelude = `
    const H = HOOKS;
    let anchorPendingOlder = false, pendingAnchor = null, pendingAnchorIntent = H.intent, pendingAnchorKeepY = H.keepY, pendingAnchorClick = false, pendingAnchorQuote = null, landTrail = [];
    const activeId = "A"; const views = new Map([["A", H.v]]);
    const liveSession = () => H.s;
    const displayItems = (s) => s.events.map((e, i) => ({ kind: "event", index: i }));
    const itemFirstEvent = (it) => it.index;
    const openFolds = new Set(); const toolGroupKey = (e) => "tg:" + e.uuid; const noticeGroupKey = (e) => "ng:" + e.uuid;
    const WINDOW_RADIUS = 70;
    let building = null;
    const renderWindowItems = (v, s, items, ws, we, working, anchored) => { H.calls.push(["renderWindowItems", ws, we, anchored]); H.build(building); };
    const cssEscape = (x) => x;
    const olderOnServer = () => H.older; const liveWindowAsk = () => null; const loadingOlder = new Set(); const pendingOlderAnchor = new Map(); const pendingOlderKeepY = new Map();
    const requestAround = () => false;
    const fetchOlderForAnchor = (sid, uuid) => { H.calls.push(["fetchOlderForAnchor", uuid]); return H.older; };
    const landToast = (m) => { H.toasts.push(m); }; const pulseLandingNotice = () => {};
    const scrollDiagRow = (kind, row) => { H.rows.push([kind, row]); };
    const document = { getElementById: (id) => (id === "content" ? { scrollTop: 500, getBoundingClientRect: () => ({ top: 0 }) } : null) };
    const writeScroll = (c, top, writer) => { H.writes.push([writer, top]); };
    const highlightCiteSpan = () => null; const firstTextAtomBelow = () => null;
    const landOn = (target, uuid) => { H.calls.push(["landOn", target.dataset.uuid, uuid]); };
  `;
  const epilogue = `
    return { jump: (uuid) => { building = uuid; return scrollToAnchor(uuid); },
             state: () => ({ pendingAnchor, pendingAnchorIntent, pendingAnchorKeepY, anchorPendingOlder, landTrail: landTrail.slice() }) };
  `;
  const api = new Function("HOOKS", prelude + js + epilogue)(H) as { jump: (uuid: string) => boolean; state: World["state"] };
  return { host, calls: H.calls, writes: H.writes, rows: H.rows, toasts: H.toasts, state: api.state, jump: api.jump };
}
const U = (n: number) => "11111111-2222-4333-8444-0000000000" + String(n).padStart(2, "0");
const events: Ev[] = [{ kind: "user", uuid: U(1) }, { kind: "assistant", uuid: U(2) }, { kind: "user", uuid: U(3) }, { kind: "assistant", uuid: U(4) }];
const builds = (w: World) => w.calls.filter((c) => c[0] === "renderWindowItems");
const lands = (w: World) => w.calls.filter((c) => c[0] === "landOn");

test("a resident target: no build (no take), the landing on the row, true", () => {
  const w = world({ resident: [U(1), U(2)], events });
  assert.equal(w.jump(U(2)), true);
  assert.deepEqual(builds(w), [], "the row is there: nothing rebuilt, nothing taken");
  assert.deepEqual(lands(w), [["landOn", U(2), U(2)]], "the reader is put on the row");
  assert.deepEqual(w.writes, []); assert.deepEqual(w.state().landTrail, ["pointer-exact"]);
  assert.equal(w.state().pendingAnchor, null, "the arm is consumed");
});

test("a target the window does not hold, in the events: the flagged build (the take), then the re-query finds the row the build rendered and the landing follows in the same pass (a `return false` after the build leaves the take with no write: this is the pin that reds under it)", () => {
  const w = world({ resident: [U(1), U(2)], events, rendersOnBuild: true });
  assert.equal(w.jump(U(4)), true);
  assert.deepEqual(builds(w), [["renderWindowItems", 0, 4, true]], "one window build around the anchor's unit, flagged: its take is the land's");
  assert.deepEqual(lands(w), [["landOn", U(4), U(4)]], "the take is followed by the placing write");
  assert.ok(w.calls.findIndex((c) => c[0] === "renderWindowItems") < w.calls.findIndex((c) => c[0] === "landOn"), "the build (and its take) before the land, which reads the row's live rect");
  assert.deepEqual(w.state().landTrail, ["pointer-exact"]); assert.equal(w.state().pendingAnchor, null);
});

test("a keep-offset re-land (keepPlaceAcrossWindow's, or the reload restore's): the row back at its kept offset, no landOn, no flash", () => {
  const w = world({ resident: [U(1), U(2)], events, rendersOnBuild: true, keepY: -50 });
  assert.equal(w.jump(U(4)), true);
  assert.deepEqual(builds(w), [["renderWindowItems", 0, 4, true]]);
  assert.deepEqual(lands(w), [], "a restore, not a jump");
  assert.deepEqual(w.writes, [["keep-offset", 100 + 500 + 50]], "the row's top in scroll space less the kept offset");
  assert.deepEqual(w.state().landTrail, ["pointer-keep-offset"]); assert.equal(w.state().pendingAnchorKeepY, null, "the offset is consumed");
});

test("the take-then-no-write roads the body discloses, reached from markjump, replyjump and cmtjump: the build's re-query finds no row (pointer-not-rendered: the arm stays for the next pass, a landmiss row is filed), or the row is the wrong kind for a prompt-intent link (pointer-wrong-kind: the arm is dropped); neither writes", () => {
  // the build renders the window around the unit but no row answers to the uuid (a member the fold hides, a row minted under another key)
  const miss = world({ resident: [U(1), U(2)], events, rendersOnBuild: false });
  assert.equal(miss.jump(U(4)), false);
  assert.deepEqual(builds(miss), [["renderWindowItems", 0, 4, true]], "the build took");
  assert.deepEqual(lands(miss), []); assert.deepEqual(miss.writes, [], "…and nothing placed the reader (the window rebuilt around the unit is where they are now)");
  assert.deepEqual(miss.state().landTrail, ["pointer-not-rendered"]); assert.equal(miss.state().pendingAnchor, U(4), "armed for the next pass");
  assert.deepEqual(miss.rows.map((r) => r[0]), ["landmiss"], "the miss files the state it saw");
  // a prompt-intent link whose anchor resolves to an assistant row
  const kind = world({ resident: [U(1), U(2)], events, rendersOnBuild: true, intent: "user" });
  assert.equal(kind.jump(U(4)), false);
  assert.deepEqual(builds(kind), [["renderWindowItems", 0, 4, true]], "the build took");
  assert.deepEqual(lands(kind), []); assert.deepEqual(kind.writes, []);
  assert.deepEqual(kind.state().landTrail, ["pointer-wrong-kind"]); assert.equal(kind.state().pendingAnchor, null, "the arm is dropped"); assert.equal(kind.state().pendingAnchorIntent, null);
  // …and a prompt-intent link onto a user row lands
  const ok = world({ resident: [U(1), U(2)], events, rendersOnBuild: true, intent: "user" });
  assert.equal(ok.jump(U(3)), true);
  assert.deepEqual(lands(ok), [["landOn", U(3), U(3)]]);
});

test("an anchor older than the resident tail: the older chunk is asked for around it, nothing is built (no take) and the arm waits for chatHead's arrival", () => {
  const w = world({ resident: [U(1), U(2)], events, headFrom: 40, older: true });
  assert.equal(w.jump("11111111-2222-4333-8444-000000000099"), false);
  assert.deepEqual(builds(w), [], "no window to build: the anchor is not in the resident events");
  assert.deepEqual(w.calls.filter((c) => c[0] === "fetchOlderForAnchor"), [["fetchOlderForAnchor", "11111111-2222-4333-8444-000000000099"]]);
  assert.equal(w.state().anchorPendingOlder, true); assert.equal(w.state().pendingAnchor, "11111111-2222-4333-8444-000000000099");
  assert.deepEqual(w.state().landTrail, ["pointer-fetch-older"]); assert.deepEqual(w.writes, []);
});

test("an empty anchor is refused before anything runs", () => {
  const w = world({ resident: [U(1)], events });
  assert.equal(w.jump(""), false);
  assert.deepEqual(w.calls, []); assert.deepEqual(w.writes, []);
});

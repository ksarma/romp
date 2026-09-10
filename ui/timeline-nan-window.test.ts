// NaN-window poisoning regression (the Chrome "stub lane lines, no bars" bug, 2026-07-15).
// On a federated page, a remote host winning the connect race made the manager emit merged
// timeline payloads with now:undefined (`now` is taken from the LOCAL host, which hadn't
// arrived yet). fitWindow() then computed _winSec = NaN and latched `fitted`, winSec()'s
// min/max clamp passed the NaN through, and every x() coordinate went NaN for the page's
// lifetime — lane lines rendered as stubs (x2="NaN" → 0 in SVG2) and every bar vanished,
// even after healthy local payloads arrived. These tests drive the exact poisoned sequence
// through update()/applyBars() and pin that the panel heals the moment a clock sample lands.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as path from "node:path";
import { createRequire } from "node:module";
import { nodeFactory } from "./test-dom-shim";

// ---- the fake DOM: ui/test-dom-shim.ts, the host measuring 1400x420 ----
const makeNode = nodeFactory({ rect: { width: 1400, height: 420, left: 0, top: 0, right: 1400, bottom: 420 } });
const g: any = global;
g.document = {
  createElement(t: string) { return t === "canvas" ? { getContext() { return { font: "", measureText(s: string) { return { width: (s ? s.length : 0) * 6 }; } }; } } : makeNode(t); },
  createElementNS(_n: any, t: string) { return makeNode(t); },
  body: makeNode("body"), documentElement: makeNode("html"), head: makeNode("head"),
  getElementById() { return null; },
  addEventListener() {}, removeEventListener() {},
};
g.localStorage = { getItem() { return null; }, setItem() {}, removeItem() {} };
g.getComputedStyle = () => ({ backgroundColor: "rgb(30,30,30)" });
g.requestAnimationFrame = () => 0;
g.addEventListener = () => {}; g.removeEventListener = () => {};
g.matchMedia = () => ({ matches: false, addEventListener() {}, addListener() {} });
g.window = g;
g.innerWidth = 1400; g.innerHeight = 800;

const viewPath = path.resolve(process.cwd(), "..", "ui", "romp-timeline-view.js");
const { TimelinePanel, isFreshNowSample } = createRequire(__filename)(viewPath);

const NOW = 1_781_000_000;

// walk the rendered SVG for the lane baseline lines (stroke #ffffff14, width 2)
function laneLines(node: any, out: any[] = []): any[] {
  if (node.tag === "line" && node.getAttribute("stroke") === "#ffffff14" && node.getAttribute("stroke-width") === 2) out.push(node);
  for (const c of node.children || []) laneLines(c, out);
  return out;
}

function remoteLanes(): any {
  // what mergeHostTimelines emitted when only the remote host had arrived: lanes/turns
  // present, but `now` (local clock authority) undefined
  return {
    sessions: [{ id: "r1:aaa", name: "rem", color: "#f66", state: "working", live: true, host: "r1",
                 awaiting: [], compacting: [], compactions: [] }],
    turns: {}, messages: [], judging: [], activeChat: null, focus: null, hover: null, usage: null,
  };
}

test("a remote-first merge (no data.now) must not latch a NaN window; the first clock sample heals it", () => {
  const panel: any = new TimelinePanel(makeNode("div"));
  panel._activeOnly = false;   // this test is about the NaN heal, and `loc` below has no turns — keep the
  //                              always-show-live rule so both lanes render (active-only has its own tests)
  panel.update(remoteLanes());
  panel.applyBars({ type: "bars", turns: { "r1:aaa": [{ id: "x", start: NOW - 3000, end: NOW - 2000 }] },
                    messages: [], judging: [] });
  assert.equal(panel.fitted, false, "no clock sample yet → fitWindow must refuse to latch");
  assert.ok(Number.isFinite(panel.winSec()), "winSec() stays finite through the poisoned frames");

  // the local snapshot lands: same lanes plus the local group, and a real `now`
  const healthy: any = remoteLanes();
  healthy.now = NOW;
  healthy.sessions.unshift({ id: "bbb", name: "loc", color: "#6f6", state: "working", live: true, host: "",
                             awaiting: [], compacting: [], compactions: [] });
  healthy.turns = { "r1:aaa": [{ id: "x", start: NOW - 3000, end: NOW - 2000 }] };
  panel.update(healthy);
  assert.equal(panel.fitted, true, "the first payload WITH a clock sample fits and latches");
  assert.ok(Number.isFinite(panel.winSec()), "the fitted window is a real number");
  const lanes = laneLines(panel.svg);
  assert.ok(lanes.length >= 2, "lane baselines render");
  for (const l of lanes) {
    assert.ok(Number.isFinite(+l.getAttribute("x2")), `lane line x2 must be finite, got ${l.getAttribute("x2")}`);
    assert.ok(+l.getAttribute("x2") > +l.getAttribute("x1"), "the lane line spans the plot, not a backwards stub");
  }
});

test("winSec(): a non-finite _winSec falls back to the default instead of riding through the clamp", () => {
  const panel: any = new TimelinePanel(makeNode("div"));
  panel._winSec = NaN;   // the min/max clamp passes NaN through — the fallback must catch it
  assert.ok(Number.isFinite(panel.winSec()) && panel.winSec() > 0);
});

test("isFreshNowSample: NaN is never adopted as the newest clock sample", () => {
  // an adopted NaN would compare false against every later real sample, freezing data.now forever
  assert.equal(isFreshNowSample(null, NaN), false);
  assert.equal(isFreshNowSample(null, undefined), false);
  assert.equal(isFreshNowSample(null, 100), true);
  assert.equal(isFreshNowSample(100, 101), true);
});

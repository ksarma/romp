// An awaiting or compacting interval the session is STILL in arrives with its end at the payload's own
// clock (kernel _state_intervals ends an open span at `now`): the renderer reads an end within 2 s of
// data.now — or a null end — as OPEN and draws it to the live edge, the way barEndT draws an open work
// bar, so the stripe glides with the edge instead of sitting at the kernel's build clock until the next
// rebuild (2026-09-06; the lanes frame is deduped per rebuild, so the build clock can trail the edge by up
// to a bucket). The end stays numeric on the wire: a null end was a wire break for every already-loaded
// renderer (Math.min(null, t1) = 0 dropped the stripe). Headless draw() over a minimal DOM shim (the
// timeline-render.test.ts pattern), with the live edge pushed 30 s past data.now so "to the live edge"
// and "to the payload's end" land on different pixels.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";

function makeNode(tag: string): any {
  const n: any = {
    tag, _attrs: {}, children: [] as any[], style: {}, dataset: {}, textContent: "", parentNode: null,
    classList: { _s: new Set<string>(), add(...a: string[]) { a.forEach((c) => this._s.add(c)); },
      remove(...a: string[]) { a.forEach((c) => this._s.delete(c)); },
      toggle(c: string, f?: boolean) { f ? this._s.add(c) : this._s.delete(c); }, contains(c: string) { return this._s.has(c); } },
    setAttribute(k: string, v: any) { this._attrs[k] = v; }, getAttribute(k: string) { return this._attrs[k]; },
    setAttributeNS(_n: any, k: string, v: any) { this._attrs[k] = v; }, removeAttribute(k: string) { delete this._attrs[k]; },
    appendChild(c: any) { c.parentNode = n; this.children.push(c); return c; },
    insertBefore(c: any, ref: any) { c.parentNode = n; const i = this.children.indexOf(ref); i < 0 ? this.children.push(c) : this.children.splice(i, 0, c); return c; },
    removeChild(c: any) { const i = this.children.indexOf(c); if (i >= 0) this.children.splice(i, 1); return c; },
    get firstChild() { return this.children[0] || null; },
    addEventListener() {}, removeEventListener() {}, querySelector() { return null; }, querySelectorAll() { return []; },
    getBoundingClientRect() { return { width: 1400, height: 420, left: 0, top: 0, right: 1400, bottom: 420 }; },
    closest() { return null; }, focus() {},
    createEl(t: string, o: any) { const e = makeNode(t); if (o && o.cls) e.classList.add(o.cls); if (o && o.text) e.textContent = o.text; this.appendChild(e); return e; },
    createDiv(o: any) { return this.createEl("div", o); }, createSpan(o: any) { return this.createEl("span", o); },
  };
  return n;
}
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
const { TimelinePanel } = createRequire(__filename)(viewPath);
const SRC = fs.readFileSync(viewPath, "utf8");

const NOW = 1_781_000_000;
const AHEAD = 30;   // the view's MAX_INTERP_AHEAD: how far the live edge is pushed past data.now below
function lane(id: string, name: string, extra: any) {
  return {
    id, name, color: "#7aa2f7", state: "working", live: true, model: "m", effort: "high",
    context: 40, since: NOW - 60, awaiting: [], compacting: [], compactions: [], pendingMail: 0, faded: false, stale: false, ...extra,
  };
}
function turn(id: string) {
  return { id, promptId: id + "#p", workId: id + "#w", start: NOW - 400, end: NOW - 200, prompt: "do the thing", src: "typed",
    mids: [], pending: false, summary: "did the thing", tid: "fork-" + id, uuid: "u-" + id, workUuid: "w-" + id, replyUuid: "r-" + id };
}
function collect(node: any, pred: (n: any) => boolean, out: any[] = []): any[] {
  if (pred(node)) out.push(node);
  for (const c of node.children || []) collect(c, pred, out);
  return out;
}
const hatch = (fill: string) => (n: any) => n.tag === "rect" && n.getAttribute("fill") === fill;
const right = (r: any) => Number(r.getAttribute("x")) + Number(r.getAttribute("width"));
const width = (r: any) => Number(r.getAttribute("width"));

// A panel live-following with its edge 30 s past data.now (the glide the view does between kernel
// frames), gaps uncollapsed so x is linear in time.
function livePanel(data: any) {
  const panel: any = new TimelinePanel(makeNode("div"));
  panel.data = data;
  panel._collapseGaps = false;
  panel._pinned = true; panel._frozeFromPin = false;
  panel._nowBaseSec = NOW; panel._nowBaseMs = performance.now() - 5 * AHEAD * 1000;   // clamps to AHEAD
  return panel;
}

test("an open interval (end at the payload clock) draws to the live edge; a closed one stops at its end; a null end draws the same", () => {
  const ids = ["S1", "S2", "S3", "S4", "S5"];
  const panel = livePanel({
    now: NOW,
    sessions: [
      lane("S1", "web", { state: "needsInput", awaiting: [[NOW - 100, NOW]] }),        // OPEN: the kernel's shape, end == now
      lane("S2", "api", { awaiting: [[NOW - 100, NOW - 30]] }),                        // closed 30 s ago
      lane("S3", "tests", { awaiting: [[NOW - 100, NOW - 60]] }),                      // closed 60 s ago (with S2: px per second)
      lane("S4", "docs", { state: "needsInput", awaiting: [[NOW - 100, null]] }),      // a null end still reads as open
      lane("S5", "build", { compactions: [{ t: NOW }] }),                              // a marker ending at x(now): the reference pixel
    ],
    turns: Object.fromEntries(ids.map((id) => [id, [turn(id + ":1")]])),
    messages: [], activeChat: null, focus: null, hover: null, usage: null,
  });
  assert.doesNotThrow(() => panel.draw(), "draw() accepts numeric and null interval ends");
  const stripes = collect(panel.svg, hatch("url(#vault-await-hatch)"));
  assert.equal(stripes.length, 4, "every awaiting span draws (a null end used to draw nothing)");
  const [open, closed30, closed60, openNull] = stripes;
  const marker = collect(panel.svg, hatch("url(#vault-compact-hatch)"));
  assert.equal(marker.length, 1, "one compaction marker");
  const xNow = right(marker[0]);
  const pps = (width(closed30) - width(closed60)) / 30;
  assert.ok(pps > 0.05, "the window resolves seconds to pixels: " + pps);
  assert.ok(Math.abs(right(closed30) - (xNow - 30 * pps)) < 1, "a closed span stops at its own end");
  assert.ok(Math.abs(right(open) - (xNow + AHEAD * pps)) < 1,
    "the open span reaches the live edge, 30 s past the payload's now (it used to stop at x(now), the build clock)");
  assert.ok(Math.abs(right(openNull) - right(open)) < 0.01, "a null end lands on the same live edge");
  assert.equal(open.getAttribute("x"), openNull.getAttribute("x"), "…starting where the payload says");
});

test("an open compacting interval draws its cross-hatch to the live edge", () => {
  const panel = livePanel({
    now: NOW,
    sessions: [
      lane("S1", "web", { state: "compacting", compacting: [[NOW - 50, NOW]] }),   // open: end at the payload clock
      lane("S2", "api", { compactions: [{ t: NOW }] }),                            // the x(now) reference marker
    ],
    turns: { S1: [turn("S1:1")], S2: [turn("S2:1")] },
    messages: [], activeChat: null, focus: null, hover: null, usage: null,
  });
  assert.doesNotThrow(() => panel.draw());
  const hx = collect(panel.svg, hatch("url(#vault-compact-hatch)"));
  assert.equal(hx.length, 2, "the live compacting stripe and the marker");
  const [stripe, marker] = hx;
  assert.ok(right(stripe) > right(marker) + 2, "the open compacting stripe runs past x(now) to the live edge");
});

test("open detection and the tooltips read an end at the payload clock (or null) as open, and the open end follows the live edge", () => {
  // No DOM events in the shim, so pin the tooltip and label wiring at the source.
  assert.equal((SRC.match(/const open = span\[1\] == null \|\| span\[1\] >= data\.now - 2;/g) || []).length, 2,
    "both stripe loops detect an open span the same way");
  assert.equal((SRC.match(/const a0 = span\[0\], b0 = open \? Math\.max\(nowS, a0\) : span\[1\];/g) || []).length, 2,
    "an open end is the live edge (nowS), never before the span's start");
  assert.match(SRC, /const end = open \? 'now' : clock\(b0\);/, "the awaiting tooltip says 'now'");
  assert.match(SRC, /const live = open;\n\s+const cw2 = live \? 'compacting' : 'compacted';/, "the compacting label reads 'compacting'");
});

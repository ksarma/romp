// perf-telemetry.ts on a fake clock: the frame classifier, the per-type ring and its p90, the minute flush
// (one row, its shape; an idle minute sends nothing), the free-main-thread sample two animation frames after
// a handler, the slowframe threshold and its long-frame attribution, the long-animation-frame aggregation
// from synthetic entries (with and without `scripts`, and the longtask fallback), and the feature guards
// when performance.memory, PerformanceObserver, requestAnimationFrame or performance.now itself are absent.
// The collector takes every browser dependency through PerfDeps, so nothing here touches a real window
// except the install tests, which stand one in the way fleet-live-clock.test.ts does.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import {
  Ring, percentile, classifyFrame, scriptKey, sanitizeInvoker, uaClass, attributeScripts,
  createPerfTelemetry, installPerfTelemetry, perfFrameHandler,
  RING_CAPACITY, MAX_FRAME_TYPES, SLOW_FRAME_MS, type PerfDeps,
} from "./perf-telemetry";

function harness(over: Partial<PerfDeps> = {}) {
  const clock = { t: 1000, wall: 1_700_000_000_000 };
  const posted: any[] = [];
  const rafQueue: Array<(t: number) => void> = [];
  const cancelled: number[] = [];
  const deps: PerfDeps = {
    now: () => clock.t,
    wallNow: () => clock.wall,
    post: (m) => posted.push(m),
    raf: (cb) => { rafQueue.push(cb); return rafQueue.length; },
    caf: (id) => cancelled.push(id),
    setInterval: null,
    observer: null,
    supportedEntryTypes: [],
    heapBytes: () => 200 * 1048576,
    domCount: () => 1234,
    visible: () => true,
    hiddenPane: () => false,
    ua: "chrome-desktop",
    windowEvents: null,
    documentEvents: null,
    ...over,
  };
  /** run the animation-frame callbacks queued so far (one frame); a callback that queues another leaves it for the next call */
  const runRafs = () => { for (const cb of rafQueue.splice(0)) cb(clock.t); };
  /** a frame whose handler takes `ms` on the fake clock */
  const frame = (p: ReturnType<typeof createPerfTelemetry>, msg: unknown, ms: number) =>
    p.frame(msg, () => { clock.t += ms; });
  return { deps, clock, posted, rafQueue, cancelled, runRafs, frame };
}

const minuteRows = (posted: any[]) => posted.filter((m) => m.what === "minute");
const slowRows = (posted: any[]) => posted.filter((m) => m.what === "slowframe");

// ── pure pieces ──

test("classifyFrame: the type, a raw delta by slot, shell messages, and everything else as other", () => {
  assert.equal(classifyFrame({ type: "feed", asks: [] }), "feed");
  assert.equal(classifyFrame({ type: "chatTail", from: 3 }), "chatTail");
  assert.equal(classifyFrame({ type: "delta", slot: "bars", rev: 4 }), "delta:bars");
  assert.equal(classifyFrame({ type: "delta" }), "delta:other");
  assert.equal(classifyFrame({ romp: "paneFocus" }), "shell");
  assert.equal(classifyFrame({ type: "not an identifier!" }), "other");
  assert.equal(classifyFrame({ type: "x".repeat(40) }), "other");
  assert.equal(classifyFrame({}), "other");
  assert.equal(classifyFrame(null), "other");
  assert.equal(classifyFrame("feed"), "other");
});

test("Ring keeps the newest 64 samples; percentile is nearest-rank", () => {
  const r = new Ring(RING_CAPACITY);
  for (let i = 1; i <= 100; i++) r.push(i);
  assert.equal(r.n, 100);
  const v = r.values();
  assert.equal(v.length, 64);
  assert.equal(Math.min(...v), 37);
  assert.equal(Math.max(...v), 100);
  assert.equal(percentile([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 0.9), 9);
  assert.equal(percentile([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 0.5), 5);
  assert.equal(percentile([7], 0.9), 7);
  assert.equal(percentile([], 0.9), 0);
  assert.equal(percentile([5, 1, 3], 1), 5);
});

test("scriptKey, sanitizeInvoker, uaClass carry identifiers only", () => {
  assert.equal(scriptKey({ sourceURL: "http://h:1/dist/feed.js?v=1757100000", sourceFunctionName: "render" }), "feed.js:render");
  assert.equal(scriptKey({ sourceURL: "", sourceFunctionName: "" }), "inline:(anonymous)");
  assert.equal(scriptKey({ sourceURL: "http://h/dist/render.js#x", sourceFunctionName: "chatTail" }), "render.js:chatTail");
  assert.equal(sanitizeInvoker("DIV#tab-web.onclick"), "DIV.onclick");
  assert.equal(sanitizeInvoker("WebSocket.onmessage"), "WebSocket.onmessage");
  assert.equal(sanitizeInvoker(undefined), "");
  assert.equal(uaClass("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"), "chrome-desktop");
  assert.equal(uaClass("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"), "safari-ios");
  assert.equal(uaClass("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15", 5), "safari-ios");
  assert.equal(uaClass("Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Mobile Safari/537.36"), "other");
  assert.equal(uaClass("Mozilla/5.0 (X11; Linux x86_64; rv:130.0) Gecko/20100101 Firefox/130.0"), "other");
});

test("attributeScripts sums per file:function, largest first, and keeps the latest sanitized invoker", () => {
  const rows = attributeScripts([
    { sourceURL: "http://h/dist/feed.js?v=1", sourceFunctionName: "render", invoker: "DIV#c1.onclick", duration: 30 },
    { sourceURL: "http://h/dist/feed.js?v=1", sourceFunctionName: "render", invoker: "WebSocket.onmessage", duration: 50 },
    { sourceURL: "http://h/dist/federation.js?v=1", sourceFunctionName: "inbound", invoker: "WebSocket.onmessage", duration: 10 },
    { sourceURL: "x", duration: "nope" },
  ]);
  assert.deepEqual(rows, [
    { k: "feed.js:render", ms: 80, inv: "WebSocket.onmessage" },
    { k: "federation.js:inbound", ms: 10, inv: "WebSocket.onmessage" },
  ]);
});

// ── frames and the minute flush ──

test("a minute with frames sends ONE row in the documented shape; an idle minute sends nothing", () => {
  const h = harness();
  const p = createPerfTelemetry("feed", h.deps);
  h.frame(p, { type: "feed" }, 10);
  h.frame(p, { type: "feed" }, 20);
  h.frame(p, { type: "chatTail" }, 2);
  h.frame(p, { romp: "paneFocus" }, 0.5);
  h.frame(p, { type: "delta", slot: "bars" }, 1);
  h.frame(p, null, 0);                       // a frame the handler ignores still counts
  // the main thread frees 45 ms after the first frame's handler returned: two animation frames later
  h.clock.t += 45;
  h.runRafs(); h.runRafs();
  h.clock.wall += 60_000;
  p.tick();
  const rows = minuteRows(h.posted);
  assert.equal(rows.length, 1);
  const row = rows[0];
  assert.equal(row.type, "clientDiag");
  assert.equal(row.surface, "perf");
  assert.equal(row.what, "minute");
  const d = row.data;
  assert.equal(d.app, "feed");
  assert.equal(d.since, 1_700_000_000_000);
  assert.equal(d.span_ms, 60_000);
  assert.deepEqual(d.frames.feed, { n: 2, ms_sum: 30, ms_max: 20, p90: 20 });
  assert.deepEqual(d.frames.chatTail, { n: 1, ms_sum: 2, ms_max: 2, p90: 2 });
  assert.deepEqual(d.frames.shell, { n: 1, ms_sum: 0.5, ms_max: 0.5, p90: 0.5 });
  assert.deepEqual(d.frames["delta:bars"], { n: 1, ms_sum: 1, ms_max: 1, p90: 1 });
  assert.deepEqual(d.frames.other, { n: 1, ms_sum: 0, ms_max: 0, p90: 0 });
  // one free sample: scheduled after the first frame (t=1010), resolved at 1010+20+2+0.5+1+0+45
  assert.deepEqual(d.free, { n: 1, p50: 68.5, p90: 68.5, max: 68.5 });
  assert.deepEqual(d.loaf, { n: 0, blocking_ms: 0, worst_ms: 0, top: [], src: "none" });
  assert.equal(d.heap_mb, 200);
  assert.equal(d.dom, 1234);
  assert.equal(d.visible, true);
  assert.equal(d.hidden_pane, false);
  assert.equal(d.ua, "chrome-desktop");
  assert.deepEqual(Object.keys(d).sort(),
    ["app", "dom", "frames", "free", "heap_mb", "hidden_pane", "loaf", "since", "span_ms", "ua", "visible"]);
  // a row's values are numbers, strings of identifiers, booleans or null: never nested text
  const walk = (v: any): void => {
    if (v === null || typeof v === "number" || typeof v === "boolean") return;
    if (typeof v === "string") { assert.match(v, /^[A-Za-z0-9_.:()-]*$/); return; }
    for (const x of Object.values(v)) walk(x);
  };
  walk(d);
  // the next minute: nothing happened, nothing sent, and the bucket restarted at the new wall time
  assert.equal(slowRows(h.posted).length, 0);
  h.clock.wall += 60_000;
  p.tick();
  assert.equal(h.posted.length, 1);
  assert.equal(p.snapshot().since, 1_700_000_120_000);
});

test("per-type ring: p90 over the newest 64 of a busy type; the minute's counts are all of them", () => {
  const h = harness();
  const p = createPerfTelemetry("chat", h.deps);
  for (let i = 1; i <= 100; i++) h.frame(p, { type: "chatTail" }, i);   // 1..100 ms; the ring holds 37..100
  h.clock.wall += 60_000;
  p.tick();
  const f = minuteRows(h.posted)[0].data.frames.chatTail;
  assert.equal(f.n, 100);
  assert.equal(f.ms_sum, 5050);
  assert.equal(f.ms_max, 100);
  assert.equal(f.p90, 94);                    // nearest rank 58 of 64 sorted values 37..100
});

test("distinct frame types are capped per minute; the overflow folds into other", () => {
  const h = harness();
  const p = createPerfTelemetry("chat", h.deps);
  for (let i = 0; i < MAX_FRAME_TYPES + 3; i++) h.frame(p, { type: "t" + i }, 1);
  h.clock.wall += 60_000;
  p.tick();
  const frames = minuteRows(h.posted)[0].data.frames;
  assert.equal(Object.keys(frames).length, MAX_FRAME_TYPES + 1);
  assert.equal(frames.other.n, 3);
});

test("the pane's own exception propagates and the frame is still recorded; nested timing counts once", () => {
  const h = harness();
  const p = createPerfTelemetry("feed", h.deps);
  assert.throws(() => p.frame({ type: "feed" }, () => { h.clock.t += 5; throw new Error("pane bug"); }), /pane bug/);
  p.frame({ type: "bars" }, () => { h.clock.t += 3; p.frame({ type: "feed" }, () => { h.clock.t += 4; }); });
  const s: any = p.snapshot();
  assert.deepEqual(s.frames.feed, { n: 1, ms_sum: 5, ms_max: 5, p90: 5 });
  assert.deepEqual(s.frames.bars, { n: 1, ms_sum: 7, ms_max: 7, p90: 7 });
});

test("wrapFrameHandler hands the event through and times by its data", () => {
  const h = harness();
  const p = createPerfTelemetry("waiting", h.deps);
  const seen: any[] = [];
  const wrapped = p.wrapFrameHandler((e) => { seen.push(e.data); h.clock.t += 2; });
  wrapped({ data: { type: "feed" } } as MessageEvent);
  wrapped({ data: { type: "warn", text: "x" } } as MessageEvent);
  assert.deepEqual(seen.map((m) => m.type), ["feed", "warn"]);
  const s: any = p.snapshot();
  assert.equal(s.frames.feed.n, 1);
  assert.equal(s.frames.warn.n, 1);
});

// ── the free-main-thread sample ──

test("free: one sample in flight; frames landing before it resolves share it; hidden panes take none", () => {
  const h = harness();
  const p = createPerfTelemetry("feed", h.deps);
  h.frame(p, { type: "feed" }, 10);          // ends at 1010, sample armed
  h.frame(p, { type: "feed" }, 10);          // ends at 1020: the thread is still busy, no second sample
  assert.equal(h.rafQueue.length, 1);
  h.clock.t += 30;                           // 1050
  h.runRafs();                               // first rAF queues the second
  assert.equal(h.rafQueue.length, 1);
  h.clock.t += 10;                           // 1060
  h.runRafs();
  const s: any = p.snapshot();
  assert.deepEqual(s.free, { n: 1, p50: 50, p90: 50, max: 50 });   // 1060 - 1010
  assert.equal(s.free_pending, false);
  // a pane with no viewport (the shell's display:none) arms nothing: rAF does not run there
  const hidden = harness({ hiddenPane: () => true });
  const q = createPerfTelemetry("feed", hidden.deps);
  hidden.frame(q, { type: "feed" }, 10);
  assert.equal(hidden.rafQueue.length, 0);
  // a sample that resolves after the pane went hidden is dropped, not recorded as a huge gap
  let vis = true;
  const flip = harness({ visible: () => vis });
  const r = createPerfTelemetry("feed", flip.deps);
  flip.frame(r, { type: "feed" }, 10);
  vis = false;
  flip.clock.t += 5000;
  flip.runRafs(); flip.runRafs();
  assert.equal((r.snapshot() as any).free, null);
});

test("visibilitychange to hidden cancels the armed sample; pagehide flushes the minute", () => {
  const win = new EventTarget();
  const doc = new EventTarget();
  let vis = true;
  const h = harness({ windowEvents: win, documentEvents: doc, visible: () => vis });
  const p = createPerfTelemetry("feed", h.deps);
  h.frame(p, { type: "feed" }, 10);
  assert.equal((p.snapshot() as any).free_pending, true);
  vis = false;
  doc.dispatchEvent(new Event("visibilitychange"));
  assert.equal((p.snapshot() as any).free_pending, false);
  assert.deepEqual(h.cancelled, [1]);
  win.dispatchEvent(new Event("pagehide"));
  assert.equal(minuteRows(h.posted).length, 1);
  assert.equal(minuteRows(h.posted)[0].data.frames.feed.n, 1);
});

// ── slow frames ──

test("slowframe: a handler at the threshold sends a row at once when no long-frame observer exists", () => {
  const h = harness();
  const p = createPerfTelemetry("feed", h.deps);
  h.frame(p, { type: "feed" }, SLOW_FRAME_MS - 0.1);
  assert.equal(slowRows(h.posted).length, 0);
  h.frame(p, { type: "feed" }, SLOW_FRAME_MS);
  const rows = slowRows(h.posted);
  assert.equal(rows.length, 1);
  assert.equal(rows[0].surface, "perf");
  assert.deepEqual(rows[0].data, { app: "feed", type: "feed", ms: 100, dom: 1234 });
});

class FakeObserver {
  static cb: ((list: { getEntries(): any[] }) => void) | null = null;
  static opts: any = null;
  static constructed = 0;
  constructor(cb: (list: { getEntries(): any[] }) => void) { FakeObserver.cb = cb; FakeObserver.constructed++; }
  observe(o: any): void { FakeObserver.opts = o; }
  disconnect(): void {}
  static deliver(entries: any[]): void { FakeObserver.cb!({ getEntries: () => entries }); }
}

test("slowframe with a long-frame observer: held for the report covering it, then sent with its attribution", () => {
  const h = harness({ observer: FakeObserver as any, supportedEntryTypes: ["long-animation-frame", "longtask"] });
  const p = createPerfTelemetry("feed", h.deps);
  assert.equal(p.observerKind, "loaf");
  assert.deepEqual(FakeObserver.opts, { type: "long-animation-frame", buffered: false });
  h.frame(p, { type: "feed" }, 130);         // 1000..1130
  assert.equal(slowRows(h.posted).length, 0, "held for the browser's report");
  assert.equal((p.snapshot() as any).pending_slow, 1);
  FakeObserver.deliver([{
    startTime: 995, duration: 140, blockingDuration: 90,
    scripts: [
      { sourceURL: "http://h/dist/feed.js?v=1", sourceFunctionName: "render", invoker: "DIV#card-1.onclick", duration: 110 },
      { sourceURL: "http://h/dist/federation.js?v=1", sourceFunctionName: "inbound", invoker: "WebSocket.onmessage", duration: 20 },
    ],
  }]);
  const rows = slowRows(h.posted);
  assert.equal(rows.length, 1);
  assert.deepEqual(rows[0].data, {
    app: "feed", type: "feed", ms: 130, dom: 1234,
    loaf: { ms: 140, blocking_ms: 90, top: [{ k: "feed.js:render", ms: 110, inv: "DIV.onclick" }, { k: "federation.js:inbound", ms: 20, inv: "WebSocket.onmessage" }] },
  });
  assert.equal((p.snapshot() as any).pending_slow, 0);
});

test("slowframe backstops: a later report that starts after it, or the minute tick, sends it without attribution", () => {
  const h = harness({ observer: FakeObserver as any, supportedEntryTypes: ["long-animation-frame"] });
  const p = createPerfTelemetry("chat", h.deps);
  h.frame(p, { type: "chatTail" }, 120);     // 1000..1120
  FakeObserver.deliver([{ startTime: 1500, duration: 60, blockingDuration: 10, scripts: [] }]);
  let rows = slowRows(h.posted);
  assert.equal(rows.length, 1);
  assert.deepEqual(rows[0].data, { app: "chat", type: "chatTail", ms: 120, dom: 1234 });
  h.frame(p, { type: "chatTail" }, 150);
  assert.equal(slowRows(h.posted).length, 1);
  h.clock.wall += 60_000;
  p.tick();
  rows = slowRows(h.posted);
  assert.equal(rows.length, 2);
  assert.equal(rows[1].data.ms, 150);
  assert.equal("loaf" in rows[1].data, false);
});

// ── long-frame aggregation ──

test("long frames: entries over 50 ms aggregate into count, blocking, worst and the top attributed keys", () => {
  const h = harness({ observer: FakeObserver as any, supportedEntryTypes: ["long-animation-frame"] });
  const p = createPerfTelemetry("feed", h.deps);
  FakeObserver.deliver([
    { startTime: 10, duration: 40, blockingDuration: 0, scripts: [{ sourceURL: "a.js", sourceFunctionName: "x", duration: 40 }] },   // under 50: ignored
    { startTime: 100, duration: 120, blockingDuration: 70, scripts: [
      { sourceURL: "http://h/dist/feed.js?v=2", sourceFunctionName: "render", invoker: "WebSocket.onmessage", duration: 100 },
      { sourceURL: "http://h/dist/feed.js?v=2", sourceFunctionName: "paintFreezeBadges", invoker: "WebSocket.onmessage", duration: 15 },
    ] },
    { startTime: 400, duration: 80, blockingDuration: 30 },                                                                            // no scripts field
    { startTime: 700, duration: 300, blockingDuration: 250, scripts: [
      { sourceURL: "http://h/dist/feed.js?v=2", sourceFunctionName: "render", invoker: "Window.requestAnimationFrame", duration: 280 },
    ] },
  ]);
  h.clock.wall += 60_000;
  p.tick();
  const rows = minuteRows(h.posted);
  assert.equal(rows.length, 1, "a long frame alone makes the minute worth a row");
  assert.deepEqual(rows[0].data.frames, {});
  assert.deepEqual(rows[0].data.loaf, {
    n: 3, blocking_ms: 350, worst_ms: 300, src: "loaf",
    top: [
      { k: "feed.js:render", ms: 380, n: 2, inv: "Window.requestAnimationFrame" },
      { k: "feed.js:paintFreezeBadges", ms: 15, n: 1, inv: "WebSocket.onmessage" },
    ],
  });
});

test("longtask fallback: no long-animation-frame support observes longtask, blocking is time over 50 ms, no attribution", () => {
  const h = harness({ observer: FakeObserver as any, supportedEntryTypes: ["longtask", "mark"] });
  const p = createPerfTelemetry("feed", h.deps);
  assert.equal(p.observerKind, "longtask");
  assert.deepEqual(FakeObserver.opts, { type: "longtask", buffered: false });
  FakeObserver.deliver([{ startTime: 0, duration: 130, attribution: [{ containerType: "iframe" }] }]);
  // a slow handler sends at once under this observer: longtask entries carry no scripts to wait for
  h.frame(p, { type: "feed" }, 110);
  assert.equal(slowRows(h.posted).length, 1);
  assert.equal("loaf" in slowRows(h.posted)[0].data, false);
  const s: any = p.snapshot();
  assert.deepEqual(s.loaf, { n: 1, blocking_ms: 80, worst_ms: 130, top: [], src: "longtask" });
});

// ── feature guards ──

test("guards: no observer, no heap, a throwing DOM count, no rAF: the row still goes out, minus those fields", () => {
  const h = harness({ observer: null, heapBytes: () => null, domCount: () => { throw new Error("no document"); }, raf: null });
  const p = createPerfTelemetry("feed", h.deps);
  assert.equal(p.observerKind, "none");
  h.frame(p, { type: "feed" }, 3);
  assert.equal(h.rafQueue.length, 0);
  h.clock.wall += 60_000;
  p.tick();
  const d = minuteRows(h.posted)[0].data;
  assert.equal("heap_mb" in d, false);
  assert.equal(d.dom, null);
  assert.equal(d.free, null);
  assert.equal(d.loaf.src, "none");
  // an observer whose support list is empty is not constructed at all
  FakeObserver.constructed = 0;
  const q = createPerfTelemetry("feed", harness({ observer: FakeObserver as any, supportedEntryTypes: [] }).deps);
  assert.equal(q.observerKind, "none");
  assert.equal(FakeObserver.constructed, 0);
  // an observer whose constructor throws leaves the collector working without it
  class Broken { constructor() { throw new Error("no observer here"); } observe() {} disconnect() {} }
  const r = createPerfTelemetry("feed", harness({ observer: Broken as any, supportedEntryTypes: ["long-animation-frame"] }).deps);
  assert.equal(r.observerKind, "none");
});

test("a post that throws never reaches the pane; a null post keeps measuring", () => {
  const h = harness({ post: () => { throw new Error("socket gone"); } });
  const p = createPerfTelemetry("feed", h.deps);
  h.frame(p, { type: "feed" }, 200);
  h.clock.wall += 60_000;
  assert.doesNotThrow(() => p.tick());
  p.setPost(null);
  h.frame(p, { type: "feed" }, 200);
  assert.equal((p.snapshot() as any).frames.feed.n, 1);
});

test("the timer, when given, is unref'd for a node host and drives tick()", () => {
  let cb: (() => void) | null = null;
  let unrefd = false;
  const h = harness({ setInterval: (fn, ms) => { assert.equal(ms, 60_000); cb = fn; return { unref: () => { unrefd = true; } }; } });
  const p = createPerfTelemetry("feed", h.deps);
  assert.equal(unrefd, true);
  h.frame(p, { type: "feed" }, 1);
  cb!();
  assert.equal(minuteRows(h.posted).length, 1);
});

// ── the browser install ──

test("installPerfTelemetry: null without a window or without performance.now; the handler is handed back unwrapped", () => {
  const g: any = globalThis;
  assert.equal(typeof g.window, "undefined");
  assert.equal(installPerfTelemetry("feed"), null);
  const handler = () => {};
  assert.equal(perfFrameHandler("feed", undefined, handler), handler);
  // a stand-in page with no performance object (the node DOM stand-ins): nothing installed
  g.window = new EventTarget();
  g.document = new EventTarget();
  try {
    assert.equal(installPerfTelemetry("feed"), null);
    assert.equal(g.window.__rompPerf, undefined);
    assert.equal(perfFrameHandler("feed", undefined, handler), handler);
  } finally {
    delete g.window;
    delete g.document;
  }
});

test("installPerfTelemetry: one collector per page on window.__rompPerf; a later caller's post replaces the transport", () => {
  const g: any = globalThis;
  const win: any = new EventTarget();
  let t = 0;
  win.performance = { now: () => t };
  win.navigator = { userAgent: "Mozilla/5.0 (Macintosh) Chrome/128.0.0.0 Safari/537.36", maxTouchPoints: 0 };
  win.parent = win;
  win.innerWidth = 800; win.innerHeight = 600;
  const sent: any[] = [];
  win.__rompLocalSend = (m: any) => sent.push({ via: "shim", m });
  const doc: any = new EventTarget();
  doc.visibilityState = "visible";
  doc.getElementsByTagName = () => ({ length: 42 });
  g.window = win;
  g.document = doc;
  try {
    const a = installPerfTelemetry("timeline");
    assert.ok(a);
    assert.equal(win.__rompPerf, a);
    const posted: any[] = [];
    const wrapped = perfFrameHandler("timeline", (m) => posted.push(m), () => { t += 150; });
    wrapped({ data: { type: "bars" } } as MessageEvent);
    // the pane's transport took over from the shim default, and the frame was timed on the page's clock
    assert.equal(sent.length, 0);
    assert.equal(posted.length, 1);
    assert.deepEqual(posted[0].data, { app: "timeline", type: "bars", ms: 150, dom: 42 });
    assert.equal(installPerfTelemetry("timeline"), a);
    const s: any = a!.snapshot();
    assert.equal(s.ua, "chrome-desktop");
    assert.equal(s.observer, "none");
    assert.equal(s.frames.bars.n, 1);
  } finally {
    delete g.window;
    delete g.document;
  }
});

// shell-perf.ts: the dashboard shell's performance collector. The shell (the top-level window) receives no frames,
// but Chromium reports an iframe's long animation frames to it and to no pane, so it runs the panes' collector
// (perf-telemetry.ts) under app "shell" and posts its minute row through its own kernel socket
// (window.__rompShellSend). Stood in the way the perf-telemetry install tests stand a window in: a fake window
// with performance.now and a PerformanceObserver whose callback the test drives, the module imported once the
// fakes are in place (its boot line installs on import). Synthetic URLs and ids only: host h, the placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";

const SID = "11111111-2222-3333-4444-555555555555";
const g: any = globalThis;
const sent: any[] = [];
let socketOpen = true;
let observerCb: ((list: { getEntries(): any[] }) => void) | null = null;
let observed: any = null;
const win: any = new EventTarget();
let now = 5000;
win.performance = { now: () => now, memory: { usedJSHeapSize: 96 * 1048576 } };
win.navigator = { userAgent: "Mozilla/5.0 (Macintosh) Chrome/128.0.0.0 Safari/537.36", maxTouchPoints: 0 };
win.location = { href: "http://h:1/?token=abc" };     // the shell page: an inline shell script's sourceURL, query and all
win.parent = win;
win.PerformanceObserver = class {
  static supportedEntryTypes = ["long-animation-frame", "longtask"];
  constructor(cb: (list: { getEntries(): any[] }) => void) { observerCb = cb; }
  observe(opts: any): void { observed = opts; }
  disconnect(): void {}
};
// the socket script (kernel.py shellWS) runs AFTER the bundles: the send is read at call time, so it is set here
// only once the module has booted (the first test), which is also the order on the page
g.window = win;
g.document = new EventTarget();

const emit = (entry: any) => { assert.ok(observerCb, "the observer is installed"); observerCb!({ getEntries: () => [entry] }); };
const loaf = (ms: number, scripts: any[]) => ({ startTime: now, duration: ms, blockingDuration: Math.max(0, ms - 50), scripts });

test("the shell installs the panes' collector under app \"shell\", observing long-animation-frame entries, and posts through window.__rompShellSend", async () => {
  const mod = await import("./shell-perf");
  assert.equal(mod.SHELL_APP, "shell");
  const p = win.__rompPerf;
  assert.ok(p && typeof p.tick === "function", "published as window.__rompPerf like every pane's");
  assert.equal(p.snapshot().app, "shell");
  assert.equal(p.snapshot().observer, "loaf", "long-animation-frame, with attribution");
  assert.deepEqual(observed, { type: "long-animation-frame", buffered: false });
  win.__rompShellSend = (m: any) => { if (!socketOpen) return false; sent.push(m); return true; };
  // an idle minute: nothing posted (the shell has no frames; a row is a minute with a long frame in it)
  p.tick();
  assert.equal(sent.length, 0);
});

test("a long frame the browser attributes to a pane's script becomes one scrubbed minute row: script basenames without query, page: for an inline script, invokers without element ids or URLs; nothing in it carries a slash, a query or a session id", () => {
  const p = win.__rompPerf;
  emit(loaf(20_000, [
    // the Files pane's bundle, as Chromium names it: the full URL with its dist token, run from the pane's animation frame
    { sourceURL: "http://h:1/dist/files.js?v=1757100000", sourceFunctionName: "paintAll", sourceCharPosition: 9000, invoker: "Window.requestAnimationFrame", duration: 19_500 },
    // the pane's inline shim, whose sourceURL is the pane page with its token and the session it shows
    { sourceURL: "http://h:1/files?token=abc&sid=" + SID, sourceFunctionName: "", sourceCharPosition: 4000, invoker: "WebSocket.onmessage", duration: 300 },
    // the shell's own inline script (the divider drag): its sourceURL is the shell page itself
    { sourceURL: "http://h:1/?token=abc", sourceFunctionName: "onMove", sourceCharPosition: 120, invoker: "DIV#pane-divider-" + SID + ".onpointermove", duration: 150 },
    // an image the chat pane loaded, its source a file path with the session
    { sourceURL: "http://h:1/dist/render.js?v=1757100000", sourceFunctionName: "", sourceCharPosition: 77, invoker: "IMG[src=/file?path=/repo/notes-api/docs/plot.png&sid=" + SID + "].onload", duration: 50 },
  ]));
  emit({ startTime: now + 100, duration: 30, scripts: [{ sourceURL: "http://h:1/dist/feed.js", sourceFunctionName: "x", duration: 30 }] });   // under 50 ms: not a long frame
  p.tick();
  assert.equal(sent.length, 1, "one row for the minute");
  const row = sent[0];
  assert.equal(row.type, "clientDiag"); assert.equal(row.surface, "perf"); assert.equal(row.what, "minute");
  const d = row.data;
  assert.equal(d.app, "shell");
  assert.deepEqual(Object.keys(d.frames), [], "the shell brackets nothing");
  assert.equal(d.free, null, "no frame, no free sample");
  assert.equal(d.loaf.n, 1);
  assert.equal(d.loaf.worst_ms, 20_000);
  assert.equal(d.loaf.blocking_ms, 19_950);
  assert.equal(d.loaf.src, "loaf");
  assert.deepEqual(d.loaf.top, [
    { k: "files.js:paintAll@9000", ms: 19_500, n: 1, inv: "Window.requestAnimationFrame" },
    { k: "files:(anonymous)@4000", ms: 300, n: 1, inv: "WebSocket.onmessage" },
    { k: "page:onMove@120", ms: 150, n: 1, inv: "DIV.onpointermove" },
    { k: "render.js:(anonymous)@77", ms: 50, n: 1, inv: "IMG[src].onload" },
  ]);
  assert.equal(d.heap_mb, 96);
  assert.equal(d.ua, "chrome-desktop");
  // the privacy contract over every string in the row, keys included
  const strings: string[] = [];
  (function walk(v: unknown, at: string) {
    if (typeof v === "string") strings.push(at + "=" + v);
    else if (Array.isArray(v)) v.forEach((x, i) => walk(x, at + "[" + i + "]"));
    else if (v && typeof v === "object") for (const k of Object.keys(v as object)) { strings.push(at + "." + k); walk((v as any)[k], at + "." + k); }
  })(row, "row");
  assert.ok(strings.length > 10);
  for (const s of strings) {
    assert.ok(!s.includes("/"), "no slash: " + s);
    assert.ok(!s.includes("?") && !s.includes("&") && !s.includes("token"), "no query: " + s);
    assert.ok(!s.includes(SID) && !s.includes("11111111"), "no session id: " + s);
    assert.ok(!s.includes("notes-api") && !s.includes("plot.png") && !s.includes("h:1"), "no path or host: " + s);
  }
});

test("a row the socket refuses is held and goes ahead of the next one that finds it open, in order; nothing is sent while it stays closed", () => {
  const p = win.__rompPerf;
  sent.length = 0;
  socketOpen = false;
  emit(loaf(120, [{ sourceURL: "http://h:1/dist/feed.js?v=1", sourceFunctionName: "render", sourceCharPosition: 1, duration: 120 }]));
  p.tick();
  assert.equal(sent.length, 0, "closed: held");
  emit(loaf(130, [{ sourceURL: "http://h:1/dist/feed.js?v=1", sourceFunctionName: "render", sourceCharPosition: 1, duration: 130 }]));
  p.tick();
  assert.equal(sent.length, 0, "still closed: both held");
  socketOpen = true;
  emit(loaf(140, [{ sourceURL: "http://h:1/dist/feed.js?v=1", sourceFunctionName: "render", sourceCharPosition: 1, duration: 140 }]));
  p.tick();
  assert.deepEqual(sent.map((m) => m.data.loaf.worst_ms), [120, 130, 140], "the held rows first, then the new one");
});

test("shellPost: no send yet (the socket script has not run) holds too; past HELD_MAX the oldest held row goes; a send that fails mid-drain keeps the rest in order", async () => {
  const { shellPost, HELD_MAX } = await import("./shell-perf");
  let send: ((m: any) => boolean) | undefined;
  const out: any[] = [];
  const post = shellPost(() => send);
  for (let i = 0; i < HELD_MAX + 3; i++) post({ i });
  send = (m) => { out.push(m); return true; };
  post({ i: "last" });
  assert.equal(out.length, HELD_MAX + 1);
  assert.deepEqual(out.map((m) => m.i), [...Array.from({ length: HELD_MAX }, (_, k) => k + 3), "last"], "the three oldest went; the rest in arrival order");
  // the socket closes again mid-drain: what went stays sent, the rest stay held in order, the new row behind them
  out.length = 0;
  send = () => false;
  post({ i: "a" }); post({ i: "b" }); post({ i: "c" });
  let calls = 0;
  send = (m) => { calls++; if (calls === 2) return false; out.push(m); return true; };
  post({ i: "d" });
  assert.deepEqual(out.map((m) => m.i), ["a"], "a went; b failed and stopped the drain");
  send = (m) => { out.push(m); return true; };
  post({ i: "e" });
  assert.deepEqual(out.map((m) => m.i), ["a", "b", "c", "d", "e"], "the rest followed in order once the socket answered");
});

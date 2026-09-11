// tests/ui-bench.test.mjs: tools/ui-bench.mjs, the headless-Chrome bench for the dashboard panes.
//
// Three layers. Browser-free: the frame classifier (the report's rows), the percentile and compare
// arithmetic, the report fold, the /tmp path guard that keeps a recording of real session data out
// of any git checkout (with a simulated macOS layout, where /tmp is a symlink), the private file
// modes a recording is written with, the synthesizer's wire shapes (the compact bars slot the pane's
// shim keys itself, contiguous delta revisions, a byte-stable stream), the --record client against a local
// WebSocket server (the query, the cookie and Origin credential form, the ready handshake and nothing
// else, the JSONL shape, the early-close and refusal errors), and the CPU-profile fold over a
// synthetic .cpuprofile, and the per-user run directory with its dead-owner sweep. With python3 and a
// built dist: the Handler subprocess's environment (seen through a stub interpreter that echoes it)
// and its exit when the node process that started it is SIGKILLed. With a browser as well: a synthetic feed stream and a synthetic timeline stream replayed
// back-to-back into the REAL pages, served by the kernel's own page route and the built bundles, must
// produce a report with every frame type measured and settled and no console error, uncaught
// exception or failed resource load; the feed run also writes a CPU profile. Those tests skip, naming
// the reason, when a prerequisite is missing, unless ROMP_UI_BENCH_REQUIRE is set (CI sets it), when
// the skip becomes a failure so a runner image that lost its browser cannot pass silently.
//
// Everything here is synthetic: the notes-api demo domain, placeholder uuids, a fixed clock.
// Run: node --test tests/ui-bench.test.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import http from "node:http";
import os from "node:os";
import path from "node:path";
import { createRequire } from "node:module";
import { spawn, spawnSync } from "node:child_process";
import { fileURLToPath, pathToFileURL } from "node:url";
import {
  APPS, DELTA_SEP, REPO, STRIPPED_ENV, WHOLE_STATE_TYPES, aggregateProfile, assertTmpPath, barsKeys, benchRoot, browserAvailability, buildReport, classifyFrame,
  compareReports, dispatchExpectation, dispatchType, frameKey, frameSettle, launchBrowser, loadFrames, matchDispatches, mergeAggregates, mergeWindows, percentile, rankProfile,
  parseArgs, recordFrames, refineAlignment, renderCompare, renderProfile, renderReport, replay, sourceLocator, startPageServer, streamSummary, stripProfileQueries, summarize,
  sweepDeadRuns, synthesizeFrames, writeFrames,
} from "../tools/ui-bench.mjs";

const TOOL = path.join(REPO, "tools", "ui-bench.mjs");
const THIS_FILE = fileURLToPath(import.meta.url);
const requireExt = createRequire(path.join(REPO, "vscode-extension", "package.json"));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const mode = (p) => fs.statSync(p).mode & 0o777;
const UID = os.userInfo().uid;

/** A stand-in interpreter: announces a port and blocks on stdin the way the Handler's watcher does. */
function writeStub(dir, name = "python-stub", prelude = "") {
  const stub = path.join(dir, name);
  fs.writeFileSync(stub, `#!/bin/sh\n${prelude}echo "PORT 1"\ncat > /dev/null\n`, { mode: 0o755 });
  return stub;
}
/** A directory that passes startPageServer's dist check. */
function fakeDist(dir) {
  const dist = path.join(dir, "dist");
  fs.mkdirSync(dist, { recursive: true });
  fs.writeFileSync(path.join(dist, "feed.js"), "");
  return dist;
}

/** Set environment variables for the duration of `fn`, restoring the previous values after. */
async function withEnv(vars, fn) {
  const saved = {};
  for (const [k, v] of Object.entries(vars)) { saved[k] = process.env[k]; if (v === undefined) delete process.env[k]; else process.env[k] = v; }
  try { return await fn(); }
  finally { for (const [k, v] of Object.entries(saved)) { if (v === undefined) delete process.env[k]; else process.env[k] = v; } }
}

// ── the classifier ───────────────────────────────────────────────────────────────────────────────

test("classifyFrame files kernel frames by type, and a view delta by its slot", () => {
  assert.equal(classifyFrame('{"type": "delta", "slot": "bars", "base": 3, "rev": 4, "coll": {"turns": {"set": {"x": {"type": "not-me"}}}}}'), "delta:bars");
  assert.equal(classifyFrame('{"type": "delta", "slot": "feed", "base": 0, "rev": 1, "coll": {}}'), "delta:feed");
  assert.equal(classifyFrame('{"type":"feedDelta","now":1760000000,"buildId":4,"asks":[]}'), "feedDelta");
  assert.equal(classifyFrame('{"now": 1760000000, "type": "feed", "asks": []}'), "feed", "the feed frame carries now before type");
  assert.equal(classifyFrame('{"type": "ka", "dv": 1760000000}'), "ka");
  assert.equal(classifyFrame('{"type": "chatTail", "id": "11111111-2222-3333-4444-555555555555", "from": 3, "events": []}'), "chatTail");
  assert.equal(classifyFrame('{"type": "bars", "turns": {}, "judging": [], "messages": [], "now": 1, "warming": false}'), "bars");
  assert.equal(classifyFrame('{"type": "data", "data": {"type": "timeline", "sessions": []}}'), "data", "the outer frame's type, not the nested one");
});

test("classifyFrame falls back to a parse when the type is not in the head, and says other for the rest", () => {
  const late = '{"pad": "' + "x".repeat(5000) + '", "type": "session", "id": "s"}';
  assert.equal(classifyFrame(late), "session");
  assert.equal(classifyFrame('{"type": "delta", "pad": "' + "y".repeat(5000) + '", "slot": "bars"}'), "delta:?", "a delta whose slot is out of reach is still a delta");
  assert.equal(classifyFrame("not json at all"), "other");
  assert.equal(classifyFrame('{"x": 1}'), "other");
  assert.equal(classifyFrame('{"type": 7}'), "other");
  assert.equal(classifyFrame(null), "other");
  assert.equal(classifyFrame(Buffer.from("{}")), "other");
});

// ── arithmetic ───────────────────────────────────────────────────────────────────────────────────

test("percentile is nearest-rank and summarize folds a sample", () => {
  const xs = [10, 1, 5, 3, 8, 2, 9, 4, 7, 6];
  assert.equal(percentile(xs, 50), 5);
  assert.equal(percentile(xs, 90), 9);
  assert.equal(percentile(xs, 100), 10);
  assert.equal(percentile(xs, 0), 1);
  assert.equal(percentile([], 50), null);
  assert.equal(percentile([NaN, 4, undefined, 2], 50), 2, "non-numbers are dropped");
  assert.deepEqual(summarize([]), { n: 0, p50: null, p90: null, max: null, mean: null });
  assert.deepEqual(summarize([4, 2]), { n: 2, p50: 2, p90: 4, max: 4, mean: 3 });
});

function fakeRun({ perFrame, loaf = [], heapUsed = 1000, domElements = 10, consoleErrors = [], addListenerMessages = 0, banner = null,
  dispatch = { hook: true, unmatched: 0, flushTasks: 0, flushMs: 0 } }) {
  return {
    readyMs: 100, replayMs: 50, sent: perFrame, perFrame, misaligned: 0, reconnects: 0, clientMessages: { ready: 1 }, clientDiag: {},
    loaf, loafKind: "long-animation-frame", domElements, heap: { used: heapUsed, total: heapUsed * 2 }, addListenerMessages, banner, dispatch,
    cdp: { nodes: domElements * 3, documents: 1, jsEventListeners: 5, layoutCount: 3, recalcStyleCount: 4, layoutMs: 1.5, recalcStyleMs: 0.5, scriptMs: 20, taskMs: 30, heapUsed, heapTotal: heapUsed * 2 },
    consoleErrors, pageErrors: [], warnings: 0, failedResources: [],
  };
}
// A frame row as replayOnce builds it: pf without a handoff (a keepalive, or a frame the bench did not see handed
// over), pfd with one, inside the handler (the inline shim) or from a flush task 20 ms after it (the deferred shim).
const pf = (i, type, bytes, handlerMs, settleMs) => ({ i, type, bytes, at: i, handlerMs, settleMs, t0: 1000 + i * 100, lenMatch: true, dispatchT0: null, dispatchMs: null, coalesced: false, dispatchInline: null });
const pfd = (i, type, bytes, handlerMs, settleMs, dispatchMs, where = "inline") => {
  const f = pf(i, type, bytes, handlerMs, settleMs);
  return { ...f, dispatchT0: where === "inline" ? f.t0 + 0.2 : f.t0 + handlerMs + 20, dispatchMs, dispatchInline: where === "inline" };
};

test("parseArgs: --fast, --hidden and --help take no value; every other option takes the next word", () => {
  const o = parseArgs(["--replay", "timeline", "--frames", "f.jsonl", "--hidden", "--fast", "--iters", "3"]);
  assert.equal(o.replay, "timeline"); assert.equal(o.frames, "f.jsonl"); assert.equal(o.hidden, true); assert.equal(o.fast, true); assert.equal(o.iters, "3");
  assert.equal(parseArgs(["--replay", "timeline"]).hidden, undefined, "absent → not set");
  assert.throws(() => parseArgs(["--frames"]), /--frames needs a value/);
});

test("buildReport carries the hidden regime: the expansion counts, and the return's cost and what it expanded", () => {
  const plain = fakeRun({ perFrame: [pf(0, "bars", 5000, 40, 90)] });
  const r0 = buildReport({ app: "timeline", framesFile: "f", cpuThrottle: 1, fast: true, iters: 1, browser: "t", runs: [plain] });
  assert.equal(r0.hidden, false); assert.equal(r0.expand, null); assert.equal(r0.hiddenReturn, null, "a run without the fields reports none");
  assert.doesNotMatch(renderReport(r0), /page hidden|return of the hidden page|timeline expansion/);
  const a = { ...fakeRun({ perFrame: [pf(0, "bars", 5000, 4, 90)] }), hidden: true, expand: { bars: 0, judging: 0 }, hiddenReturn: { ms: 30, before: { bars: 0, judging: 0 }, after: { bars: 120, judging: 40 } } };
  const b = { ...a, hiddenReturn: { ms: 50, before: { bars: 0, judging: 0 }, after: { bars: 120, judging: 40 } } };
  const r = buildReport({ app: "timeline", framesFile: "f", cpuThrottle: 1, fast: true, iters: 2, browser: "t", runs: [a, b] });
  assert.equal(r.hidden, true);
  assert.deepEqual(r.expand, { bars: 0, judging: 0 }, "the replay's own expansion, averaged over runs");
  assert.deepEqual(r.hiddenReturn, { ms: 40, maxMs: 50, expandBars: 120, expandJudging: 40 }, "the return: mean and max ms, what the catch-up paint expanded");
  const text = renderReport(r);
  assert.match(text, /page hidden/);
  assert.match(text, /timeline expansion during the replay .*: 0 bars, 0 judging entries per run/);
  assert.match(text, /return of the hidden page .*: 40(\.0)? ms mean, 50(\.0)? ms max; it expanded 120 bars, 40 judging entries/);
  const c = { ...a, expand: null, hiddenReturn: { ms: 10, before: null, after: null } };
  const rc = buildReport({ app: "feed", framesFile: "f", cpuThrottle: 1, fast: true, iters: 1, browser: "t", runs: [c] });
  assert.equal(rc.expand, null, "a page without the counter reports no expansion");
  assert.deepEqual(rc.hiddenReturn, { ms: 10, maxMs: 10, expandBars: null, expandJudging: null });
  assert.doesNotMatch(renderReport(rc), /it expanded/);
});

test("buildReport folds runs per frame type with percentiles, attribution and end state", () => {
  const run = fakeRun({
    perFrame: [pf(0, "ka", 30, 0.1, 5), pf(1, "feed", 5000, 40, 90), pf(2, "feedDelta", 300, 4, 20), pf(3, "feedDelta", 500, 6, 30), pf(4, "feedDelta", 100, 2, 10)],
    // The keys long-animation-frame entries produce on this harness: the bench's onmessage wrapper (the
    // entry point of every pushed frame) and a script's own evaluation, invoked by its URL.
    loaf: [{ start: 0, duration: 120, blocking: 70, scripts: [{ url: "ui-bench-instrument.js", fn: "rompBenchOnMessage", invoker: "DOMWebSocket.onmessage", duration: 100 },
      { url: "", fn: "", invoker: "http://127.0.0.1:1/feed?token=secret-looking", duration: 15 }] }],
    heapUsed: 4096, domElements: 250,
  });
  const r = buildReport({ app: "feed", framesFile: "/tmp/x.jsonl", cpuThrottle: 1, fast: true, iters: 1, browser: "test", runs: [run] });
  assert.equal(r.tool, "ui-bench");
  assert.equal(r.frames.total, 5);
  assert.equal(r.frames.bytes, 5930);
  assert.deepEqual(r.first, { index: 1, type: "feed", bytes: 5000, handlerMs: 40, dispatchMs: null, settleMs: 90 }, "the first content frame skips the keepalive");
  assert.deepEqual(Object.keys(r.types), ["feed", "feedDelta", "ka"], "rows ordered by bytes");
  assert.equal(r.types.feedDelta.count, 3);
  assert.equal(r.types.feedDelta.measured, 3);
  assert.equal(r.types.feedDelta.bytes, 900);
  assert.equal(r.types.feedDelta.bytesMax, 500);
  assert.deepEqual(r.types.feedDelta.handlerMs, { n: 3, p50: 4, p90: 6, max: 6, mean: 4 });
  assert.deepEqual(r.types.feedDelta.settleMs, { n: 3, p50: 20, p90: 30, max: 30, mean: 20 });
  assert.equal(r.loaf.count, 1);
  assert.equal(r.loaf.blockingMs, 70);
  assert.equal(r.loaf.topScripts[0].key, "message handler (shim + bundle) <DOMWebSocket.onmessage>", "the wrapper's row is labelled for what runs inside it, not the instrument's file");
  assert.equal(r.loaf.topScripts[1].key, "(inline):(anonymous) <script feed>", "a URL-shaped invoker keeps its basename and loses its query");
  assert.equal(r.end.heapUsed, 4096);
  assert.equal(r.end.afterGc, true, "the heap figure is read after a forced GC");
  assert.equal(r.end.domElements, 250);
  assert.equal(r.end.cdpNodes, 750);
  assert.equal(r.frames.settleMissing, 0);
  assert.equal(r.frames.addListenerMessages, 0);
  assert.equal(r.frames.buildBannerRaised, 0);
  assert.equal(r.cpuProfile, undefined, "no profile unless one was taken");
  assert.equal(r.perFrame.length, 5, "a single run keeps the per-frame rows");
  const text = renderReport(r);
  assert.match(text, /first content frame: feed, 4\.9 KB/);
  assert.match(text, /feedDelta\s+3\s+900 B\s+500 B\s+4\.0 \/ 6\.0 \/ 6\.0/);
  assert.match(text, /console: 0 errors/);
  assert.match(text, /after a forced GC/);
  assert.match(text, /cumulative since navigation .*3 layouts/, "the counters are labelled for what they are");
  assert.match(text, /entry point .*not the bundle function/);
  assert.doesNotMatch(text, /warning:/);
  assert.doesNotMatch(text, /secret-looking/, "no query string from a page URL reaches the report");
});

test("buildReport counts frames whose settle never stamped, extra message listeners and a raised banner, and renderReport warns", () => {
  const run = fakeRun({ perFrame: [pf(0, "feed", 5000, 40, 90), pf(1, "feedDelta", 300, 4, -1), pf(2, "feedDelta", 300, 5, 20), pf(3, "ka", 30, 0.1, -1)], addListenerMessages: 2, banner: "build" });
  const r = buildReport({ app: "feed", framesFile: "f", cpuThrottle: 1, fast: true, iters: 1, browser: "t", runs: [run] });
  assert.equal(r.types.feedDelta.settleMissing, 1);
  assert.equal(r.types.feedDelta.measured, 2, "the handler was still timed");
  assert.deepEqual(r.types.feedDelta.settleMs, { n: 1, p50: 20, p90: 20, max: 20, mean: 20 }, "settle percentiles cover the stamped frames only");
  assert.equal(r.types.ka.settleMissing, 1);
  assert.equal(r.frames.settleMissing, 2);
  assert.equal(r.frames.addListenerMessages, 2);
  assert.equal(r.frames.buildBannerRaised, 1);
  assert.equal(r.frames.connBannerRaised, 0);
  const text = renderReport(r);
  assert.match(text, /feedDelta .*\(1 settle missing\)/);
  assert.match(text, /warning: 2 frames never received a settle stamp/);
  assert.match(text, /warning: 2 message listeners were added with addEventListener/);
  assert.match(text, /warning: the page raised its "newer build" banner in 1 run/);
});

test("buildReport pools iterations: counts per run, percentiles over every sample", () => {
  const a = fakeRun({ perFrame: [pf(0, "feed", 100, 10, 20), pf(1, "ka", 10, 1, 2)] });
  const b = fakeRun({ perFrame: [pf(0, "feed", 100, 30, 40), pf(1, "ka", 10, 3, 4)] });
  const r = buildReport({ app: "feed", framesFile: "f", cpuThrottle: 2, fast: false, iters: 2, browser: "t", runs: [a, b] });
  assert.equal(r.iters, 2);
  assert.equal(r.types.feed.count, 1);
  assert.deepEqual(r.types.feed.handlerMs, { n: 2, p50: 10, p90: 30, max: 30, mean: 20 });
  assert.equal(r.first.handlerMs, 20, "the first frame's time is the mean over iterations");
  assert.equal(r.perFrame, undefined, "pooled runs carry no single per-frame list");
  assert.equal(r.cpuThrottle, 2);
});

test("compareReports subtracts B from A per type and for the totals", () => {
  const mk = (settle, loafBlocking, heap, errors, replayMs = 1000) => ({
    app: "feed", cpuThrottle: 1, fast: true, frames: { replayMs },
    first: { type: "feed", bytes: 5000, handlerMs: settle / 2, settleMs: settle },
    types: { feed: { count: 1, bytes: 5000, handlerMs: { p50: settle / 2, p90: settle / 2, max: settle / 2 }, settleMs: { p50: settle, p90: settle, max: settle } },
      ka: { count: 3, bytes: 90, handlerMs: { p50: 0.1, p90: 0.2, max: 0.2 }, settleMs: { p50: 1, p90: 2, max: 2 } } },
    loaf: { count: 2, durationMs: 300, blockingMs: loafBlocking, maxMs: 200 },
    end: { heapUsed: heap, domElements: 100, layoutCount: 5, scriptMs: 50, taskMs: 80 },
    console: { errors },
  });
  const A = mk(200, 100, 4000, []);
  const B = mk(150, 60, 5000, ["boom"]);
  B.types.feedDelta = { count: 4, bytes: 400, handlerMs: { p50: 1, p90: 2, max: 3 }, settleMs: { p50: 5, p90: 6, max: 7 } };
  const c = compareReports(A, B);
  assert.deepEqual(c.types.feed.settleP50, { a: 200, b: 150, diff: -50, pct: -25 });
  assert.deepEqual(c.types.feed.handlerP50, { a: 100, b: 75, diff: -25, pct: -25 });
  assert.deepEqual(c.first.settleMs, { a: 200, b: 150, diff: -50, pct: -25 });
  assert.deepEqual(c.loaf.blockingMs, { a: 100, b: 60, diff: -40, pct: -40 });
  assert.deepEqual(c.end.heapUsed, { a: 4000, b: 5000, diff: 1000, pct: 25 });
  assert.deepEqual(c.types.feedDelta.count, { a: null, b: 4, diff: null, pct: null }, "a type present on one side only compares to nothing");
  assert.deepEqual(c.console.errors, [0, 1]);
  assert.deepEqual(c.replayMs, [1000, 1000]);
  assert.equal(c.endComparable, true);
  const text = renderCompare(c);
  assert.match(text, /feed\s+count 1 → 1 \(unchanged\); settle p50 200 → 150 ms \(-50, -25%\)/);
  assert.match(text, /first content frame: bytes 5000 → 5000 \(unchanged\); handler 100 → 75 ms \(-25, -25%\)/);
  assert.match(text, /feedDelta\s+count - → 4;/);
  assert.match(text, /heap 4000 → 5000 B \(\+1000, \+25%\)/);
  assert.match(text, /console errors: 0 → 1/);
  A.end.layoutCount = 100; B.end.layoutCount = 50;
  assert.match(renderCompare(compareReports(A, B)), /layouts 100 → 50 \(-50, -50%\)/, "runs of the same pacing and length compare with percentages");
  assert.doesNotMatch(renderCompare(compareReports(A, B)), /carry no percentage/);
  // A paced run against a fast one, or runs of different length: the cumulative counters lose their percentages.
  const longer = mk(150, 60, 5000, [], 5000); longer.end.layoutCount = 50;
  const cl = compareReports(A, longer);
  assert.equal(cl.endComparable, false);
  const tl = renderCompare(cl);
  assert.match(tl, /layouts 100 → 50 \(-50\); script/);
  assert.match(tl, /cumulative since navigation and the runs differ in pacing or length \(replay 1000 → 5000 ms\)/);
  assert.match(tl, /heap 4000 → 5000 B \(\+1000, \+25%\)/, "the heap is a state, not a cumulative counter, so it keeps its percentage");
  const paced = mk(150, 60, 5000, [], 1000); paced.fast = false;
  assert.equal(compareReports(A, paced).endComparable, false);
  assert.equal(compareReports(A, mk(150, 60, 5000, [], 1200)).endComparable, true, "a fifth is within tolerance");
  assert.equal(compareReports({ ...A, frames: undefined }, B).endComparable, false, "an older report without replayMs is not assumed comparable");
  // The dispatch columns: reports written before they existed carry none, so both sides are null and the text says n/a, never NaN.
  assert.deepEqual(c.types.feed.dispatchP50, { a: null, b: null, diff: null, pct: null });
  assert.deepEqual(c.first.dispatchMs, { a: null, b: null, diff: null, pct: null });
  assert.match(text, /first content frame: .*; handler 100 → 75 ms \(-25, -25%\); dispatch n\/a; settled 200 → 150 ms/);
  assert.match(text, /^feed\s+count .*; handler p50 100 → 75 ms \(-25, -25%\); dispatch p50 n\/a$/m);
  assert.doesNotMatch(text, /NaN|undefined/);
  const A2 = mk(200, 100, 4000, []); A2.first.dispatchMs = 90; A2.types.feed.dispatchMs = { p50: 90, p90: 90, max: 90 };
  const B2 = mk(150, 60, 5000, []); B2.first.dispatchMs = 60; B2.types.feed.dispatchMs = { p50: 60, p90: 70, max: 80 };
  const cd = compareReports(A2, B2);
  assert.deepEqual(cd.types.feed.dispatchP50, { a: 90, b: 60, diff: -30, pct: -33.3 });
  assert.deepEqual(cd.types.feed.dispatchMax, { a: 90, b: 80, diff: -10, pct: -11.1 });
  assert.deepEqual(cd.first.dispatchMs, { a: 90, b: 60, diff: -30, pct: -33.3 });
  const td = renderCompare(cd);
  assert.match(td, /first content frame: .*; dispatch 90 → 60 ms \(-30, -33\.3%\); settled/);
  assert.match(td, /^feed\s+count .*; dispatch p50 90 → 60 ms \(-30, -33\.3%\)$/m);
  assert.match(renderCompare(compareReports(A, B2)), /dispatch p50 - → 60 ms/, "one side only: the missing side prints as -, as every other one-sided field does");
});

// ── the dispatch hook's records: matching frames to the bundle's inbound calls ───────────────────

test("dispatchType: keepalives and the restart notice never reach the bundle, a view delta reaches it as its slot, everything else as itself", () => {
  assert.equal(dispatchType("ka"), null);
  assert.equal(dispatchType("restarting"), null);
  assert.equal(dispatchType("delta:bars"), "bars");
  assert.equal(dispatchType("delta:feed"), "feed");
  assert.equal(dispatchType("feedDelta"), "feedDelta");
  assert.equal(dispatchType("data"), "data");
  assert.equal(dispatchType("session"), "session");
  assert.deepEqual([...WHOLE_STATE_TYPES].sort(), ["bars", "data", "feed", "globalRetryPaused", "tabOrder", "working"], "the shim's WHOLE set");
});

// The three tests below feed dispatch records WITHOUT n (the handler ordinal the page records), so they
// exercise the clock fallback; the order rule has its own test after them.
test("matchDispatches: the inline shim (each handoff inside its own frame's handler) matches every non-keepalive frame to itself", () => {
  const sent = [{ type: "ka" }, { type: "feed" }, { type: "feedDelta" }, { type: "ka" }, { type: "feedDelta" }, { type: "working" }];
  const recs = sent.map((_s, i) => ({ t0: 100 + i * 10 }));
  // the last handoff's start reads the same clock value as its handler's start (the page clock is coarsened to 0.1 ms)
  const dispatches = [{ t0: 110.2, dur: 5, type: "feed", inHandler: true }, { t0: 120.1, dur: 1, type: "feedDelta", inHandler: true }, { t0: 140.1, dur: 1, type: "feedDelta", inHandler: true },
    { t0: 150, dur: 0.1, type: "working", inHandler: true }];
  const m = matchDispatches(sent, recs, dispatches);
  assert.deepEqual(m.counts, { dispatched: 4, coalesced: 0, unmatched: 0 });
  assert.deepEqual(m.perFrame[5], { dispatchT0: 150, dispatchMs: 0.1, coalesced: false, dispatchInline: true, dispatchSettleAt: null }, "a handler start equal to the handoff's start is a candidate (<=, not <)");
  assert.deepEqual(m.perFrame[0], { dispatchT0: null, dispatchMs: null, coalesced: false, dispatchInline: null, dispatchSettleAt: null }, "a keepalive is never handed over");
  assert.deepEqual(m.perFrame[1], { dispatchT0: 110.2, dispatchMs: 5, coalesced: false, dispatchInline: true, dispatchSettleAt: null });
  assert.deepEqual(m.perFrame[2], { dispatchT0: 120.1, dispatchMs: 1, coalesced: false, dispatchInline: true, dispatchSettleAt: null });
  assert.equal(m.perFrame[3].dispatchMs, null);
  assert.deepEqual(m.perFrame[4], { dispatchT0: 140.1, dispatchMs: 1, coalesced: false, dispatchInline: true, dispatchSettleAt: null });
  const noFlag = matchDispatches(sent, recs, dispatches.map(({ inHandler, ...d }) => d));
  assert.equal(noFlag.perFrame[1].dispatchInline, null, "without the page's handler-depth record the flag is unknown, not guessed");
});

test("matchDispatches: the deferred shim (every handoff after the burst, in queue order) matches chained frames first-in first-out and a whole-state type to its newest frame, the older ones coalesced", () => {
  const sent = [{ type: "feed" }, { type: "feedDelta" }, { type: "feed" }, { type: "feedDelta" }, { type: "ka" }];
  const recs = sent.map((_s, i) => ({ t0: 100 + i * 10 }));
  // the flush ran after all five handlers; the queue held [feedDelta, feed, feedDelta]: the newer feed took the
  // older one's place and moved to the end
  const dispatches = [{ t0: 200, dur: 2, type: "feedDelta", inHandler: false }, { t0: 203, dur: 30, type: "feed", inHandler: false }, { t0: 234, dur: 1, type: "feedDelta", inHandler: false }];
  const m = matchDispatches(sent, recs, dispatches);
  assert.deepEqual(m.counts, { dispatched: 3, coalesced: 1, unmatched: 0 });
  assert.deepEqual(m.perFrame[0], { dispatchT0: null, dispatchMs: null, coalesced: true, dispatchInline: null, dispatchSettleAt: null }, "the older feed never reached the bundle");
  assert.deepEqual(m.perFrame[1], { dispatchT0: 200, dispatchMs: 2, coalesced: false, dispatchInline: false, dispatchSettleAt: null });
  assert.deepEqual(m.perFrame[2], { dispatchT0: 203, dispatchMs: 30, coalesced: false, dispatchInline: false, dispatchSettleAt: null });
  assert.deepEqual(m.perFrame[3], { dispatchT0: 234, dispatchMs: 1, coalesced: false, dispatchInline: false, dispatchSettleAt: null });
  assert.equal(m.perFrame[4].dispatchMs, null);
});

test("matchDispatches: a view delta matches the dispatch of its slot, a frame received after a handoff started waits for the next, and a dispatch with no candidate is unmatched", () => {
  const sent = [{ type: "data" }, { type: "bars" }, { type: "delta:bars" }, { type: "delta:bars" }];
  const recs = [{ t0: 100 }, { t0: 110 }, { t0: 120 }, { t0: 130 }];
  const dispatches = [{ t0: 100.5, dur: 1, type: "data", inHandler: true }, { t0: 125, dur: 4, type: "bars", inHandler: false }, { t0: 131, dur: 3, type: "bars", inHandler: false }, { t0: 140, dur: 1, type: "session", inHandler: false }];
  const m = matchDispatches(sent, recs, dispatches);
  assert.deepEqual(m.counts, { dispatched: 3, coalesced: 1, unmatched: 1 });
  assert.deepEqual(m.perFrame[0], { dispatchT0: 100.5, dispatchMs: 1, coalesced: false, dispatchInline: true, dispatchSettleAt: null });
  assert.equal(m.perFrame[1].coalesced, true, "the full bars frame was replaced by the first delta's reassembled message before the flush");
  assert.deepEqual(m.perFrame[2], { dispatchT0: 125, dispatchMs: 4, coalesced: false, dispatchInline: false, dispatchSettleAt: null }, "the delta received before that flush is the one handed over");
  assert.deepEqual(m.perFrame[3], { dispatchT0: 131, dispatchMs: 3, coalesced: false, dispatchInline: false, dispatchSettleAt: null }, "the delta received after it started waits for the next flush");
  assert.deepEqual(matchDispatches(sent, [], dispatches).counts, { dispatched: 0, coalesced: 0, unmatched: 4 }, "without page records nothing can match");
  assert.deepEqual(matchDispatches(sent, recs, []).counts, { dispatched: 0, coalesced: 0, unmatched: 0 });
});

test("dispatchExpectation: chained types by their frame count, whole-state types by their last frame", () => {
  assert.deepEqual(dispatchExpectation([{ type: "ka" }, { type: "feed" }, { type: "feedDelta" }, { type: "feed" }, { type: "feedDelta" }, { type: "delta:bars" }, { type: "bars" }, { type: "restarting" }]),
    { chained: { feedDelta: 2 }, wholeLast: { feed: 3, bars: 6 } });
  assert.deepEqual(dispatchExpectation([{ type: "ka" }]), { chained: {}, wholeLast: {} });
});

test("matchDispatches keys candidacy on the handler order the page recorded (n), so same-type frames whose clock reads coincide are each matched to their own handoff; the clock is the fallback for records without n", () => {
  // The page clock (performance.now(), not cross-origin isolated) is coarsened to 0.1 ms, so a handler that starts
  // within a tick of a same-type handoff reads the same value; the order rule does not read the clock at all.
  // The inline shim: two `working` frames handled back to back, each handed over inside its own handler, every read 100.0.
  const inline = matchDispatches([{ type: "working" }, { type: "working" }], [{ t0: 100 }, { t0: 100 }],
    [{ t0: 100, dur: 0, type: "working", inHandler: true, n: 1, settleAt: null }, { t0: 100, dur: 0, type: "working", inHandler: true, n: 2, settleAt: null }]);
  assert.deepEqual(inline.counts, { dispatched: 2, coalesced: 0, unmatched: 0 }, "nothing coalesces on the inline shim, which has no queue");
  assert.deepEqual(inline.perFrame[0], { dispatchT0: 100, dispatchMs: 0, coalesced: false, dispatchInline: true, dispatchSettleAt: null });
  assert.deepEqual(inline.perFrame[1], { dispatchT0: 100, dispatchMs: 0, coalesced: false, dispatchInline: true, dispatchSettleAt: null });
  // The deferred shim: frame 0's flush task hands it over at 100.1 and frame 1's handler starts in the same tick.
  const deferred = matchDispatches([{ type: "tabOrder" }, { type: "tabOrder" }], [{ t0: 100 }, { t0: 100.1 }],
    [{ t0: 100.1, dur: 0, type: "tabOrder", inHandler: false, n: 1, settleAt: 130 }, { t0: 100.2, dur: 0, type: "tabOrder", inHandler: false, n: 2, settleAt: 131 }]);
  assert.deepEqual(deferred.counts, { dispatched: 2, coalesced: 0, unmatched: 0 });
  assert.deepEqual(deferred.perFrame[0], { dispatchT0: 100.1, dispatchMs: 0, coalesced: false, dispatchInline: false, dispatchSettleAt: 130 }, "the handoff's settle stamp rides along");
  assert.deepEqual(deferred.perFrame[1], { dispatchT0: 100.2, dispatchMs: 0, coalesced: false, dispatchInline: false, dispatchSettleAt: 131 });
  // The same records without n fall back to the clock, which cannot tell the two frames apart: the later frame takes
  // the first handoff, the earlier one is called coalesced and the second handoff finds no candidate.
  const byClock = matchDispatches([{ type: "working" }, { type: "working" }], [{ t0: 100 }, { t0: 100 }],
    [{ t0: 100, dur: 0, type: "working", inHandler: true }, { t0: 100, dur: 0, type: "working", inHandler: true }]);
  assert.deepEqual(byClock.counts, { dispatched: 1, coalesced: 1, unmatched: 1 });
  // With n the order decides even when the clock says otherwise: a frame whose handler started after the flush began
  // (index >= n) is not a candidate for that flush's handoff, whatever its t0 reads.
  const later = matchDispatches([{ type: "feed" }, { type: "feed" }], [{ t0: 100 }, { t0: 100 }],
    [{ t0: 100, dur: 30, type: "feed", inHandler: false, n: 1 }, { t0: 140, dur: 30, type: "feed", inHandler: false, n: 2 }]);
  assert.deepEqual(later.counts, { dispatched: 2, coalesced: 0, unmatched: 0 });
  assert.equal(later.perFrame[0].dispatchT0, 100);
  assert.equal(later.perFrame[1].dispatchT0, 140);
  // The deferred FIFO and whole-state coalescing under the order rule: one flush after all five handlers (n 5).
  const sent = [{ type: "feed" }, { type: "feedDelta" }, { type: "feed" }, { type: "feedDelta" }, { type: "ka" }];
  const m = matchDispatches(sent, sent.map((_s, i) => ({ t0: 100 + i })),
    [{ t0: 200, dur: 2, type: "feedDelta", inHandler: false, n: 5 }, { t0: 203, dur: 30, type: "feed", inHandler: false, n: 5 }, { t0: 234, dur: 1, type: "feedDelta", inHandler: false, n: 5 }]);
  assert.deepEqual(m.counts, { dispatched: 3, coalesced: 1, unmatched: 0 });
  assert.equal(m.perFrame[0].coalesced, true, "the older feed was replaced in the queue");
  assert.deepEqual([m.perFrame[1].dispatchT0, m.perFrame[2].dispatchT0, m.perFrame[3].dispatchT0], [200, 203, 234]);
  // A whole-state handoff from a flush that began after three handlers (n 3): frames 0 and 1 are its candidates, the
  // newer one is handed over; frame 3 arrived later and waits for the next flush (n 4). Every clock value equal.
  const bars = matchDispatches([{ type: "bars" }, { type: "delta:bars" }, { type: "ka" }, { type: "delta:bars" }], [{ t0: 100 }, { t0: 100 }, { t0: 100 }, { t0: 100 }],
    [{ t0: 100, dur: 4, type: "bars", inHandler: false, n: 3 }, { t0: 100, dur: 3, type: "bars", inHandler: false, n: 4 }]);
  assert.deepEqual(bars.counts, { dispatched: 2, coalesced: 1, unmatched: 0 });
  assert.equal(bars.perFrame[0].coalesced, true);
  assert.equal(bars.perFrame[1].dispatchMs, 4);
  assert.equal(bars.perFrame[3].dispatchMs, 3);
  // A dispatch recorded before any handler started (n 0) has no candidate.
  assert.deepEqual(matchDispatches([{ type: "feed" }], [{ t0: 100 }], [{ t0: 50, dur: 1, type: "feed", inHandler: false, n: 0 }]).counts, { dispatched: 0, coalesced: 0, unmatched: 1 });
});

test("frameSettle: a frame's settle is the later of the handler's stamp and its handoff's stamp, both from the handler's start; a handler stamp that never landed stays missing", () => {
  assert.equal(frameSettle({ t0: 100, settle: 20 }, { dispatchSettleAt: null }), 20, "the inline shim stamps no handoff settle: the handler's stamp alone");
  assert.equal(frameSettle({ t0: 100, settle: 20 }, { dispatchSettleAt: 150 }), 50, "the deferred shim in a burst: the handler's stamp landed before the frame's own handoff, the handoff's stamp is the settle");
  assert.equal(frameSettle({ t0: 100, settle: 60 }, { dispatchSettleAt: 150 }), 60, "a paced replay: the handler's stamp landed after the handoff's");
  assert.equal(frameSettle({ t0: 100, settle: -1 }, { dispatchSettleAt: 150 }), -1, "a handler stamp that never landed is reported missing, not replaced");
  assert.equal(frameSettle({ t0: 100, settle: 20 }, undefined), 20, "a frame that was not matched (a keepalive, a coalesced frame)");
  assert.equal(frameSettle({ t0: 100, settle: 20 }, { dispatchSettleAt: -1 }), 20, "a handoff stamp that has not landed changes nothing");
});

test("profileWindows picks, per type, the largest frame that was handed to the bundle over a larger one the shim replaced in its queue, and a coalesced pick says so in its row", () => {
  const cf = (functionName, url) => ({ functionName, url, lineNumber: 1, columnNumber: 0 });
  const nodes = [{ id: 1, callFrame: cf("(root)", ""), children: [2, 5] }, { id: 2, callFrame: cf("rompBenchOnPort", "ui-bench-instrument.js"), children: [3] },
    { id: 3, callFrame: cf("rompBenchDispatch", "ui-bench-instrument.js"), children: [4] }, { id: 4, callFrame: cf("render", "http://127.0.0.1:1/dist/timeline.js") }, { id: 5, callFrame: cf("(program)", "") }];
  // The deferred shim under a back-to-back timeline replay: the first skeleton (data) and the single full bars frame
  // were replaced in the queue before the first flush; a later skeleton and one reassembled delta were handed over.
  const row = (i, type, bytes, extra) => ({ ...pf(i, type, bytes, 0.4, 5), t0: 100 + i, ...extra });
  const frames = [
    row(0, "data", 8200, { coalesced: true }),
    row(1, "bars", 9000, { coalesced: true }),
    row(2, "data", 8100, { dispatchT0: 130, dispatchMs: 15, dispatchInline: false }),
    row(3, "delta:bars", 400, { dispatchT0: 146, dispatchMs: 40, dispatchInline: false }),
    row(4, "delta:bars", 500, { coalesced: true }),
    { ...pf(5, "ka", 30, 0.1, 5), t0: 200 },
  ];
  const truth = 20;
  const times = [];
  for (let x = 146.2; x < 186; x += 0.5) times.push({ x, n: 4 });   // 80 render samples inside the delta's dispatch span
  for (let x = 186.2; x < 190; x += 0.5) times.push({ x, n: 5 });
  const us = times.map((s) => Math.round((s.x - truth) * 1000));
  const profile = { nodes, startTime: 0, endTime: us[us.length - 1] + 500, samples: times.map((s) => s.n), timeDeltas: us.map((u, i) => u - (i ? us[i - 1] : 0)) };
  const run = { ...fakeRun({ perFrame: frames, dispatch: { hook: true, unmatched: 0, flushTasks: 2, flushMs: 55 } }), profiling: { p0: truth + 0.8, alignMs: 1, profile } };
  const r = buildReport({ app: "timeline", framesFile: "f", cpuThrottle: 1, fast: true, iters: 1, browser: "t", runs: [run] });
  const cp = r.cpuProfile;
  const byLabel = Object.fromEntries(cp.windows.map((w) => [w.label, w]));
  assert.deepEqual(Object.keys(byLabel), ["first content frame", "largest data", "largest bars", "largest delta:bars"]);
  assert.equal(byLabel["first content frame"].index, 0, "the first content frame is the first frame whatever became of it");
  assert.equal(byLabel["first content frame"].coalesced, true);
  assert.equal(byLabel["first content frame"].dispatchMs, null);
  assert.equal(byLabel["largest data"].index, 2, "the handed-over skeleton, though the replaced one was larger");
  assert.equal(byLabel["largest data"].coalesced, false);
  assert.equal(byLabel["largest data"].dispatchMs, 15);
  assert.equal(byLabel["largest bars"].index, 1, "no bars frame reached the bundle, so the largest of the type stands");
  assert.equal(byLabel["largest bars"].coalesced, true);
  assert.equal(byLabel["largest delta:bars"].index, 3, "the handed-over delta over the larger replaced one");
  assert.equal(byLabel["largest delta:bars"].samples, 80);
  assert.equal(byLabel["largest delta:bars"].coalesced, false);
  const text = renderProfile(cp);
  assert.match(text, /window: first content frame \(coalesced: replaced in the shim's queue before the handoff, so the window holds the shim's parse only\) \(data, 8\.0 KB, frame 0\): handler 0\.4 ms, dispatch -, 0\.4 ms of window, 0 samples/);
  assert.match(text, /window: largest bars \(coalesced: replaced in the shim's queue before the handoff, so the window holds the shim's parse only\) \(bars, 8\.8 KB, frame 1\)/);
  assert.match(text, /window: largest data \(data, 7\.9 KB, frame 2\): handler 0\.4 ms, dispatch 15\.0 ms/);
  assert.match(text, /window: largest delta:bars \(delta:bars, 400 B, frame 3\): handler 0\.4 ms, dispatch 40\.0 ms, 40\.4 ms of window, 80 samples/);
  assert.doesNotMatch(text, /largest data \(coalesced/);
});

test("buildReport carries the dispatch times beside the handler times, says which shim shape ran, and renderReport prints them", () => {
  const args = { app: "feed", framesFile: "f", cpuThrottle: 1, fast: true, iters: 1, browser: "t" };
  // the inline shim: every handoff inside its frame's handler
  const inline = fakeRun({ perFrame: [pf(0, "ka", 30, 0.1, 5), pfd(1, "feed", 5000, 40, 90, 38), pfd(2, "feedDelta", 300, 4, 20, 3), pfd(3, "feedDelta", 500, 6, 30, 5)] });
  const r = buildReport({ ...args, runs: [inline] });
  assert.deepEqual(r.first, { index: 1, type: "feed", bytes: 5000, handlerMs: 40, dispatchMs: 38, settleMs: 90 });
  assert.deepEqual(r.types.feedDelta.dispatchMs, { n: 2, p50: 3, p90: 5, max: 5, mean: 4 });
  assert.equal(r.types.feedDelta.dispatched, 2);
  assert.equal(r.types.feedDelta.coalesced, 0);
  assert.deepEqual(r.types.ka.dispatchMs, { n: 0, p50: null, p90: null, max: null, mean: null });
  assert.equal(r.types.ka.dispatched, 0);
  assert.deepEqual(r.dispatch, { hook: true, inline: 3, deferred: 0, unmatched: 0, coalesced: 0, flushTasks: 0, flushMs: 0, hookError: null });
  assert.equal(r.perFrame[1].dispatchMs, 38);
  assert.equal(r.perFrame[1].dispatchT0, 1100.2);
  assert.equal(r.perFrame[1].t0, 1100);
  assert.equal(r.perFrame[0].dispatchMs, null);
  const text = renderReport(r);
  assert.match(text, /first content frame: feed, 4\.9 KB, handler 40\.0 ms, dispatch 38\.0 ms, settled 90\.0 ms/);
  assert.match(text, /handler p50\/p90\/max ms\s+dispatch p50\/p90\/max ms\s+settle p50\/p90\/max ms/);
  assert.match(text, /feedDelta\s+2\s+800 B\s+500 B\s+4\.0 \/ 6\.0 \/ 6\.0\s+3\.0 \/ 5\.0 \/ 5\.0\s+20\.0 \/ 30\.0 \/ 30\.0/);
  assert.match(text, /^ka\s+1 .*0\.1 \/ 0\.1 \/ 0\.1\s+- \/ - \/ -\s+5\.0/m, "a keepalive is never handed over and is not flagged for it");
  assert.match(text, /^dispatch \(the shim's handoff .*\): 3 inside the socket handler, 0 from a queued flush task; 0 coalesced .*, 0 unmatched; 0 flush tasks$/m);
  assert.doesNotMatch(text, /warning:|not dispatched|coalesced\)/);
  // the deferred shim: the same frames handed over from two flush tasks; a newer feed replaced the older one in the queue
  const deferred = fakeRun({ perFrame: [pf(0, "ka", 30, 0.1, 5), { ...pf(1, "feed", 5000, 0.5, 90), coalesced: true }, pfd(2, "feed", 5200, 0.6, 95, 38, "deferred"), pfd(3, "feedDelta", 300, 0.1, 20, 3, "deferred")],
    dispatch: { hook: true, unmatched: 0, flushTasks: 2, flushMs: 41.5 } });
  const rd = buildReport({ ...args, runs: [deferred] });
  assert.equal(rd.types.feed.count, 2);
  assert.equal(rd.types.feed.dispatched, 1);
  assert.equal(rd.types.feed.coalesced, 1);
  assert.deepEqual(rd.types.feed.dispatchMs, { n: 1, p50: 38, p90: 38, max: 38, mean: 38 });
  assert.equal(rd.first.dispatchMs, null, "the first content frame was replaced before it reached the bundle");
  assert.deepEqual(rd.dispatch, { hook: true, inline: 0, deferred: 2, unmatched: 0, coalesced: 1, flushTasks: 2, flushMs: 41.5, hookError: null });
  assert.equal(rd.perFrame[1].coalesced, true);
  const td = renderReport(rd);
  assert.match(td, /first content frame: feed, 4\.9 KB, handler 0\.5 ms, dispatch -, settled 90\.0 ms/);
  assert.match(td, /^dispatch .*: 0 inside the socket handler, 2 from a queued flush task; 1 coalesced .*, 0 unmatched; 2 flush tasks, 41\.5 ms$/m);
  assert.match(td, /^feed\s+2 .*  \(1 coalesced\)$/m);
  assert.doesNotMatch(td, /not dispatched/);
  // a frame of a dispatching type that was neither handed over nor replaced is flagged on its row
  const missing = fakeRun({ perFrame: [pfd(0, "feed", 5000, 40, 90, 38), pf(1, "feedDelta", 300, 4, 20)] });
  assert.match(renderReport(buildReport({ ...args, runs: [missing] })), /^feedDelta\s+1 .*  \(1 not dispatched\)$/m);
  // without the page's handler-depth flag the shim shape comes from the spans: a dispatch span inside the handler span is inline
  const unflagged = fakeRun({ perFrame: [{ ...pfd(0, "feed", 5000, 40, 90, 38), dispatchInline: null }, { ...pfd(1, "feedDelta", 300, 4, 20, 3, "deferred"), dispatchInline: null }] });
  const ru = buildReport({ ...args, runs: [unflagged] });
  assert.equal(ru.dispatch.inline, 1);
  assert.equal(ru.dispatch.deferred, 1);
  // two iterations pool: counts per run, percentiles over every handoff
  const r2 = buildReport({ ...args, iters: 2, runs: [inline, inline] });
  assert.equal(r2.types.feedDelta.dispatched, 2);
  assert.equal(r2.types.feedDelta.dispatchMs.n, 4);
  assert.equal(r2.dispatch.inline, 6);
  assert.equal(r2.first.dispatchMs, 38);
  // no hook: the page never assigned window.__rompFed; the report says so loudly
  const unhooked = fakeRun({ perFrame: [pf(0, "feed", 5000, 40, 90)], dispatch: { hook: false, hookError: null, unmatched: 0, flushTasks: 0, flushMs: 0 } });
  const rh = buildReport({ ...args, runs: [unhooked] });
  assert.equal(rh.dispatch.hook, false);
  assert.match(renderReport(rh), /^warning: the dispatch hook never engaged \(the page did not assign window\.__rompFed\); the dispatch columns are empty$/m);
  const failed = fakeRun({ perFrame: [pf(0, "feed", 5000, 40, 90)], dispatch: { hook: false, hookError: "Cannot assign to read only property 'inbound'", unmatched: 0, flushTasks: 0, flushMs: 0 } });
  assert.match(renderReport(buildReport({ ...args, runs: [failed] })), /warning: the dispatch hook never engaged \(the page did not assign window\.__rompFed: Cannot assign to read only property 'inbound'\)/);
  assert.equal(buildReport({ ...args, iters: 2, runs: [inline, unhooked] }).dispatch.hook, false, "the hook must have engaged in every run");
  // long-animation-frame attribution on the deferred shim: the flush task enters through the bench's port wrapper,
  // whether the entry names the wrapper's function or only the port's onmessage as the invoker
  const loaf = [{ start: 0, duration: 70, blocking: 20, scripts: [{ url: "ui-bench-instrument.js", fn: "rompBenchOnPort", invoker: "MessagePort.onmessage", duration: 60 }] },
    { start: 100, duration: 60, blocking: 10, scripts: [{ url: "ui-bench-instrument.js", fn: "", invoker: "MessagePort.onmessage", duration: 55 }] },
    { start: 200, duration: 55, blocking: 5, scripts: [{ url: "ui-bench-instrument.js", fn: "rompBenchOnMessage", invoker: "DOMWebSocket.onmessage", duration: 50 }] }];
  const rl = buildReport({ ...args, runs: [fakeRun({ perFrame: deferred.perFrame, loaf })] });
  assert.deepEqual(rl.loaf.topScripts.map((t) => [t.key, t.count]), [["flush task (shim queue + bundle) <MessagePort.onmessage>", 2], ["message handler (shim + bundle) <DOMWebSocket.onmessage>", 1]]);
});

// ── the path guard ───────────────────────────────────────────────────────────────────────────────

test("assertTmpPath allows /tmp, refuses the repo, other roots, and a checkout under /tmp", () => {
  const ok = fs.mkdtempSync(path.join(os.tmpdir(), "romp-ui-bench-guard-"));
  try {
    assert.equal(assertTmpPath(path.join(ok, "frames.jsonl")), path.join(ok, "frames.jsonl"));
    assert.equal(assertTmpPath(path.join(ok, "deeper", "frames.jsonl")), path.join(ok, "deeper", "frames.jsonl"), "a not-yet-created leaf directory is fine");
    assert.equal(assertTmpPath(path.join(ok, "a", "b", "c", "frames.jsonl")), path.join(ok, "a", "b", "c", "frames.jsonl"), "several missing directories are fine");
    assert.throws(() => assertTmpPath(path.join(REPO, "frames.jsonl")), /outside \/tmp/);
    assert.throws(() => assertTmpPath("/var/tmp/frames.jsonl"), /outside \/tmp/);
    assert.throws(() => assertTmpPath("frames.jsonl"), /outside \/tmp/, "a relative path resolves against the cwd, which is not /tmp here");
    fs.mkdirSync(path.join(ok, "clone", ".git"), { recursive: true });
    assert.throws(() => assertTmpPath(path.join(ok, "clone", "sub", "frames.jsonl")), /inside a git checkout/);
  } finally {
    fs.rmSync(ok, { recursive: true, force: true });
  }
});

test("assertTmpPath resolves symlinks on both sides: a root that is a link (macOS's /tmp) and an ancestor that is one", () => {
  // The macOS layout in miniature: <base>/tmp -> <base>/private/tmp, and $TMPDIR under <base>/private/var.
  const base = fs.mkdtempSync(path.join(os.tmpdir(), "romp-ui-bench-mac-"));
  try {
    fs.mkdirSync(path.join(base, "private", "tmp"), { recursive: true });
    fs.mkdirSync(path.join(base, "private", "var", "folders", "T"), { recursive: true });
    fs.symlinkSync(path.join(base, "private", "tmp"), path.join(base, "tmp"));
    fs.symlinkSync(path.join(base, "private", "var"), path.join(base, "var"));
    const roots = [path.join(base, "tmp"), path.join(base, "var", "folders", "T")];
    const fresh = path.join(base, "tmp", "romp-perf", "frames.jsonl");
    assert.equal(assertTmpPath(fresh, { roots }), fresh, "first run: the directory does not exist yet");
    fs.mkdirSync(path.join(base, "tmp", "romp-perf"));
    assert.equal(assertTmpPath(fresh, { roots }), fresh, "second run: the directory exists and resolves through the link");
    assert.equal(assertTmpPath(path.join(base, "private", "tmp", "romp-perf", "x.jsonl"), { roots }), path.join(base, "private", "tmp", "romp-perf", "x.jsonl"), "the resolved form of the root is accepted too");
    assert.equal(assertTmpPath(path.join(base, "var", "folders", "T", "x.jsonl"), { roots }), path.join(base, "var", "folders", "T", "x.jsonl"), "a $TMPDIR path");
    assert.throws(() => assertTmpPath(path.join(base, "private", "var", "elsewhere", "x.jsonl"), { roots }), /outside \/tmp/, "a sibling of the roots is still refused");
    assert.throws(() => assertTmpPath(path.join(base, "x.jsonl"), { roots }), /outside \/tmp/);
    // An ancestor link that points OUT of /tmp: the resolved parent decides.
    fs.mkdirSync(path.join(base, "private", "home", "sub"), { recursive: true });
    fs.symlinkSync(path.join(base, "private", "home"), path.join(base, "tmp", "away"));
    assert.throws(() => assertTmpPath(path.join(base, "tmp", "away", "sub", "x.jsonl"), { roots }), /outside \/tmp/, "a link under /tmp that leaves it is refused");
  } finally {
    fs.rmSync(base, { recursive: true, force: true });
  }
});

test("assertTmpPath refuses a symlink at the leaf, and writeFrames will not write through one", () => {
  const base = fs.mkdtempSync(path.join(os.tmpdir(), "romp-ui-bench-leaf-"));
  try {
    fs.mkdirSync(path.join(base, "fakeco", ".git"), { recursive: true });
    fs.mkdirSync(path.join(base, "fakeco", "sub"));
    const leaf = path.join(base, "leaf.jsonl");
    fs.symlinkSync(path.join(base, "fakeco", "sub", "target.jsonl"), leaf);
    assert.throws(() => assertTmpPath(leaf), /through a symlink/);
    assert.throws(() => writeFrames(leaf, { synthetic: true }, synthesizeFrames("feed", 2)), /ELOOP|EMLINK|symlink/i, "O_NOFOLLOW refuses the open");
    assert.ok(!fs.existsSync(path.join(base, "fakeco", "sub", "target.jsonl")), "nothing landed in the checkout");
    const dangling = path.join(base, "dangling.jsonl");
    fs.symlinkSync(path.join(base, "nowhere", "x.jsonl"), dangling);
    assert.throws(() => assertTmpPath(dangling), /through a symlink/, "a dangling link is a link");
  } finally {
    fs.rmSync(base, { recursive: true, force: true });
  }
});

// ── the synthesizer ──────────────────────────────────────────────────────────────────────────────

test("synthesizeFrames: the feed stream is one full frame, then deltas and keepalives, byte-stable", () => {
  const frames = synthesizeFrames("feed", 30);
  const types = frames.map((f) => classifyFrame(f.data));
  assert.equal(types[0], "feed");
  const full = JSON.parse(frames[0].data);
  assert.equal(full.asks.length, 30);
  assert.ok(full.asks.every((a) => a.itemId && a.sid && a.name && a.column && Array.isArray(a.tree) && a.tree.length), "every card has an id, a session and a tree");
  assert.ok(full.asks.every((a) => /^11111111-2222-3333-4444-5555555555\d\d$/.test(a.sid)), "placeholder uuids only");
  assert.ok(types.includes("feedDelta") && types.includes("ka"));
  assert.equal(types.filter((t) => t === "feed").length, 1);
  let prevBuild = full.buildId;
  for (const f of frames) {
    const m = JSON.parse(f.data);
    if (m.type !== "feedDelta") continue;
    assert.ok(m.buildId > prevBuild, "buildId advances on every delta"); prevBuild = m.buildId;
    assert.equal(typeof m.now, "number");
    assert.ok(Array.isArray(m.asks) && m.asks.length >= 1, "every delta upserts at least one card");
    if (m.top) assert.ok(!("asks" in m.top) && !("now" in m.top), "top carries the non-keyed remainder only");
  }
  assert.ok(frames.some((f) => JSON.parse(f.data).removeAsks), "some deltas retire a card");
  assert.ok(frames.some((f) => JSON.parse(f.data).top), "some deltas carry the remainder");
  assert.ok(frames.every((f, i) => i === 0 || f.t >= frames[i - 1].t), "timestamps are monotonic");
  assert.deepEqual(synthesizeFrames("feed", 30), frames, "the same seed gives the same bytes");
  assert.notDeepEqual(synthesizeFrames("feed", 30, { seed: 8 }), frames, "another seed gives another stream");
  assert.deepEqual(Object.keys(streamSummary(frames).byType).sort(), ["feed", "feedDelta", "ka"]);
});

test("synthesizeFrames: the Outline stream carries ledgers, the waiting stream carries todo rows", () => {
  const outlineFull = JSON.parse(synthesizeFrames("fleet", 12)[0].data);
  assert.equal(outlineFull.ledgers.length, 3);
  assert.ok(outlineFull.ledgers.every((l) => l.sid && l.name && l.ledger && Array.isArray(l.ledger.tree)));
  assert.ok(synthesizeFrames("fleet", 12).some((f) => Array.isArray(JSON.parse(f.data).ledgers) && JSON.parse(f.data).type === "feedDelta"), "some deltas upsert a ledger");
  const waitingFull = JSON.parse(synthesizeFrames("waiting", 12)[0].data);
  assert.ok(Array.isArray(waitingFull.userTodoRows) && waitingFull.userTodoRows.length >= 1);
  assert.equal(waitingFull.userTodosOn, true);
});

// The wire tables, read from the view's export (ui/romp-timeline-view.js BAR_WIRE and JUDGING_WIRE; the module loads
// under bare node) rather than copied by hand: tests/test_timeline_bars_wire.py holds that table byte for byte to
// kernel.py's _BAR_WIRE and _JUDGING_WIRE, so the kernel literal, the view and this synthesizer are one chain, and a
// key the kernel renames, retires or adds (the view following) reddens the subset checks below instead of leaving the
// bench emitting a wire the kernel no longer sends. The long names a bar keeps (id, start, end; kernel.py _BAR_LONG)
// and a judging entry's k, t and t1 are hand-listed: the view exports no list of them. A subset check catches a key
// the synth emits that the wire lacks, not a wire key the synth never emits.
const { BAR_WIRE, JUDGING_WIRE } = createRequire(import.meta.url)(path.join(REPO, "ui", "romp-timeline-view.js"));
const BAR_KEYS = new Set(["id", "start", "end", ...Object.keys(BAR_WIRE)]);
const JUDGING_KEYS = new Set(["k", "t", "t1", ...Object.keys(JUDGING_WIRE)]);
/** A compact bar omits every default (kernel.py's bar literal; wire_bar in tests/test_timeline_bars_wire.py is its
 *  twin, and the view's expandBar fills them back), so a short key that is present must carry something other than
 *  its BAR_WIRE default: no src at "typed", no empty mids, no open, cont, nudgeAuto or romp at false. */
function assertNoBarDefaults(b, what) {
  for (const [short, [name, dflt]] of Object.entries(BAR_WIRE)) {
    if (short in b) assert.notDeepEqual(b[short], dflt, `${what}: ${name} (${short}) rides only off its default`);
  }
}

test("synthesizeFrames: the timeline stream is the skeleton, the compact bars slot, then bar-level deltas", () => {
  const frames = synthesizeFrames("timeline", 30);
  const types = frames.map((f) => classifyFrame(f.data));
  assert.equal(types[0], "data");
  assert.equal(types[1], "bars");
  const skel = JSON.parse(frames[0].data);
  assert.equal(skel.data.type, "timeline");
  assert.equal(skel.data.sessions.length, 3);
  assert.ok(skel.data.sessions.every((s) => s.id && s.name && typeof s.live === "boolean" && s.color), "lanes carry id, name, live and color");
  assert.deepEqual(skel.data.turns, {}, "the skeleton carries no bars");
  const bars = JSON.parse(frames[1].data);
  assert.equal(Object.keys(bars.turns).length, 3);
  assert.equal(Object.values(bars.turns).reduce((a, lane) => a + lane.length, 0), 30);
  // the wire since T278c: compact bars, per-lane compact judging, and no key list (the pane's shim derives the keys)
  assert.equal(bars._keys, undefined, "the full carries no key list");
  const every = Object.values(bars.turns).flat();
  assert.ok(every.every((b) => Object.keys(b).every((k) => BAR_KEYS.has(k))), "a bar is {id, start, end} plus _BAR_WIRE's short keys");
  for (const b of every) assertNoBarDefaults(b, "a full's bar");
  assert.ok(every.every((b) => b.p && b.w && b.r && b.q && b.c && b.m), "the ids and captions ride under their short keys");
  assert.ok(every.some((b) => b.u === true) && every.every((b) => !("u" in b) || b.u === true), "open is u: true, and only on an open bar");
  assert.ok(!Array.isArray(bars.judging) && Object.keys(bars.judging).length >= 1, "judging is a per-lane object");
  const entries = Object.values(bars.judging).flat();
  assert.ok(entries.length >= 1);
  assert.ok(entries.every((e) => typeof e.k === "string" && e.k.split(DELTA_SEP).length === 2 && e.j && typeof e.t === "number" && typeof e.t1 === "number"
    && !("judge" in e) && !("sid" in e) && !("kd" in e) && !("x" in e)), "a judging entry is compact: k, t, j, t1 and the counts; no long names, the run kind and empty text omitted");
  assert.ok(entries.every((e) => Object.keys(e).every((k) => JUDGING_KEYS.has(k))), "a judging entry is {k, t, t1} plus _JUDGING_WIRE's short keys");
  const keys = barsKeys(bars);
  assert.equal(keys.turns.length, 30);
  assert.ok(keys.turns.every((k) => k.includes(DELTA_SEP)), "a bar's key is lane + separator + id");
  assert.ok(keys.judging.length === entries.length && keys.judging.every((k) => k.split(DELTA_SEP).length === 3), "a judging key is lane + separator + k");
  let rev = 0;
  for (const f of frames) {
    const m = JSON.parse(f.data);
    if (m.type !== "delta") continue;
    assert.equal(m.slot, "bars");
    assert.equal(m.base, rev, "each delta's base is the revision the pane holds");
    assert.equal(m.rev, rev + 1); rev = m.rev;
    assert.ok(m.coll.turns.set && Object.keys(m.coll.turns.set).every((k) => k.includes(DELTA_SEP)));
    for (const [k, b] of Object.entries(m.coll.turns.set)) {
      assert.equal(k, k.split(DELTA_SEP)[0] + DELTA_SEP + b.id, "a set key is what the shim would derive for its bar");
      assert.ok(Object.keys(b).every((x) => BAR_KEYS.has(x)) && !("open" in b), "a delta's bar is compact too");
      assertNoBarDefaults(b, "a delta's bar");
    }
    assert.equal(typeof m.rest.now, "number", "the clock rides every delta");
  }
  assert.ok(rev >= 20);
  assert.ok(types.filter((t) => t === "data").length >= 2, "the skeleton is re-pushed during the stream");
  assert.deepEqual(Object.keys(streamSummary(frames).byType).sort(), ["bars", "data", "delta:bars", "ka"]);
});

test("barsKeys derives the shim's keys: an empty lane is its bare prefix, judging keys by lane + k, messages key by id", () => {
  const keys = barsKeys({ turns: { a: [], b: [{ id: "x" }, { id: 7 }] }, judging: { s: [{ k: "1" + DELTA_SEP + "closer", t: 1, j: "closer", t1: 2 }], e: [] }, messages: [{ id: "m1" }] });
  assert.deepEqual(keys, { turns: ["a" + DELTA_SEP, "b" + DELTA_SEP + "x", "b" + DELTA_SEP + "7"], judging: ["s" + DELTA_SEP + "1" + DELTA_SEP + "closer", "e" + DELTA_SEP], messages: ["m1"] });
});

test("synthesizeFrames refuses the apps it cannot fake, each for its own reason, and unknown apps", () => {
  assert.throws(() => synthesizeFrames("chat", 5), /not synthesized .*build_session/);
  assert.throws(() => synthesizeFrames("files", 5), /not synthesized .*parses no frames/);
  assert.doesNotThrow(() => { try { synthesizeFrames("files", 5); } catch (e) { if (/build_session/.test(e.message)) throw e; } }, "the files reason is not the chat's");
  assert.throws(() => synthesizeFrames("board", 5), /unknown app/);
  assert.deepEqual(APPS, ["feed", "fleet", "waiting", "chat", "timeline", "files"]);
});

test("writeFrames and loadFrames round-trip a stream with its meta row", () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "romp-ui-bench-rt-"));
  try {
    const frames = synthesizeFrames("feed", 4);
    const file = path.join(tmp, "nested", "s.jsonl");
    writeFrames(file, { synthetic: true, app: "feed" }, frames);
    const back = loadFrames(file);
    assert.deepEqual(back.meta, { synthetic: true, app: "feed" });
    assert.deepEqual(back.frames, frames.map((f) => ({ t: f.t, data: f.data })));
    const rows = fs.readFileSync(file, "utf8").trim().split("\n").map((l) => JSON.parse(l));
    assert.equal(rows[1].bytes, Buffer.byteLength(frames[0].data, "utf8"), "each row records its byte length");
    if (process.platform !== "win32") {
      assert.equal(mode(file), 0o600, "a recording is private to the user");
      assert.equal(mode(path.join(tmp, "nested")), 0o700, "and so is a directory it creates");
      const shared = path.join(tmp, "shared.jsonl");
      fs.writeFileSync(shared, "old\n", { mode: 0o644 });
      writeFrames(shared, { synthetic: true }, frames);
      assert.equal(mode(shared), 0o600, "an overwritten file is made private too");
      assert.deepEqual(loadFrames(shared).frames.length, frames.length, "and truncated first");
    }
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
});

// ── the --record client, against a local WebSocket server ────────────────────────────────────────

/** A loopback WebSocket server standing in for the kernel: records the upgrade request and every client
 *  message, and runs `onReady(ws)` when the client's handshake arrives. */
async function fakeKernel(onReady) {
  const { WebSocketServer } = requireExt("ws");
  const server = http.createServer((_req, res) => { res.writeHead(404); res.end(); });
  const wss = new WebSocketServer({ server });
  const seen = { requests: [], messages: [] };
  wss.on("connection", (ws, req) => {
    seen.requests.push({ url: req.url, headers: req.headers });
    ws.on("message", (d) => { seen.messages.push(d.toString()); if (JSON.parse(d.toString()).type === "ready") onReady(ws); });
  });
  await new Promise((r) => server.listen(0, "127.0.0.1", r));
  return { port: server.address().port, seen, close: () => { for (const c of wss.clients) c.terminate(); server.close(); } };
}

test("recordFrames connects as the page does, sends only the ready handshake, and writes the frames as JSONL", async () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "romp-ui-bench-rec-"));
  const token = "synthetic-serve-token-for-the-test";
  const pushed = [JSON.stringify({ type: "feed", asks: [], now: 1_760_000_000, buildId: 1 }), JSON.stringify({ type: "ka", dv: 1_760_000_000 })];
  const k = await fakeKernel((ws) => { for (const f of pushed) ws.send(f); });
  try {
    fs.mkdirSync(path.join(tmp, "state"));
    fs.writeFileSync(path.join(tmp, "state", "serve-token"), token + "\n");
    const out = path.join(tmp, "rec", "frames.jsonl");
    const res = await withEnv({ ROMP_STATE_DIR: path.join(tmp, "state") }, () => recordFrames({ app: "feed", seconds: 0.5, out, port: k.port, log: () => {} }));
    assert.equal(res.frames, 2);
    assert.equal(k.seen.requests.length, 1, "one connection");
    const u = new URL(k.seen.requests[0].url, "http://127.0.0.1");
    assert.equal(u.pathname, "/ws");
    assert.equal(u.searchParams.get("app"), "feed");
    assert.equal(u.searchParams.get("delta"), "1");
    assert.equal(u.searchParams.get("caps"), "feedDelta,readyGate", "the feed page's capabilities");
    assert.match(u.searchParams.get("iid"), /^[0-9a-f-]{36}$/);
    assert.equal(u.searchParams.get("token"), null, "no token in the query");
    const h = k.seen.requests[0].headers;
    assert.equal(h.cookie, `romp_token=${token}`, "the browser's credential: the cookie");
    assert.equal(h.origin, `http://127.0.0.1:${k.port}`, "with a same-origin Origin");
    assert.equal(h["x-romp-token"], undefined, "and no header token");
    assert.deepEqual(k.seen.messages.map((m) => JSON.parse(m)), [{ type: "ready" }], "the ready handshake and nothing else");
    const back = loadFrames(out);
    assert.equal(back.meta.mode, "record");
    assert.equal(back.meta.app, "feed");
    assert.equal(back.meta.frames, 2);
    assert.equal(back.meta.port, k.port);
    assert.ok(back.meta.events.some((e) => e.event === "open"));
    assert.deepEqual(back.frames.map((f) => f.data), pushed, "the frames round-trip byte for byte");
    assert.ok(back.frames.every((f) => f.t >= Date.parse(back.meta.startedAt)), "receive timestamps");
    if (process.platform !== "win32") assert.equal(mode(out), 0o600);
  } finally {
    k.close();
    fs.rmSync(tmp, { recursive: true, force: true });
  }
});

test("recordFrames is loud when the kernel closes early or refuses the upgrade, and still writes what it got", async () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "romp-ui-bench-rec2-"));
  const k = await fakeKernel((ws) => { ws.send(JSON.stringify({ type: "ka", dv: 1 })); setTimeout(() => ws.close(1012, "restarting"), 50); });
  const refusing = http.createServer((_req, res) => { res.writeHead(404); res.end(); });
  refusing.on("upgrade", (_req, socket) => { socket.end("HTTP/1.1 403 Forbidden\r\nContent-Type: text/plain\r\nContent-Length: 9\r\nConnection: close\r\n\r\nforbidden"); });
  await new Promise((r) => refusing.listen(0, "127.0.0.1", r));
  try {
    fs.mkdirSync(path.join(tmp, "state"));
    fs.writeFileSync(path.join(tmp, "state", "serve-token"), "t\n");
    await withEnv({ ROMP_STATE_DIR: path.join(tmp, "state") }, async () => {
      const early = path.join(tmp, "early.jsonl");
      await assert.rejects(recordFrames({ app: "timeline", seconds: 5, out: early, port: k.port, log: () => {} }), /closed the socket early \(code 1012\) after 1 frames/);
      const back = loadFrames(early);
      assert.equal(back.frames.length, 1, "the frame received before the close was written");
      assert.ok(back.meta.events.some((e) => e.event === "close" && e.code === 1012));
      await assert.rejects(recordFrames({ app: "feed", seconds: 5, out: path.join(tmp, "refused.jsonl"), port: refusing.address().port, log: () => {} }), /refused the WebSocket: HTTP 403 forbidden/);
      await assert.rejects(recordFrames({ app: "board", seconds: 1, out: path.join(tmp, "x.jsonl"), port: 1, log: () => {} }), /unknown app/);
      await assert.rejects(recordFrames({ app: "feed", seconds: 1, out: path.join(REPO, "x.jsonl"), port: 1, log: () => {} }), /outside \/tmp/, "the path guard runs before any network use");
    });
    assert.equal(process.listenerCount("SIGINT"), 0, "no interrupt listener outlives a recording");
  } finally {
    k.close();
    refusing.close();
    fs.rmSync(tmp, { recursive: true, force: true });
  }
});

// ── the CPU-profile fold ─────────────────────────────────────────────────────────────────────────

/** A tiny .cpuprofile: main -> render -> fmt, with one recursive render call, beside (program) and GC. */
const SYNTH_PROFILE = (() => {
  const cf = (functionName, lineNumber, url = "http://127.0.0.1:1/dist/feed.js?v=3") => ({ functionName, url, lineNumber, columnNumber: 0, scriptId: "7" });
  return {
    nodes: [
      { id: 1, callFrame: cf("(root)", -1, ""), children: [2, 3, 6] },
      { id: 2, callFrame: cf("(program)", -1, "") },
      { id: 3, callFrame: cf("main", 9), children: [4], hitCount: 1 },
      // V8's per-line ticks: the first render node's two samples fell on bundle lines 20 and 25, the recursive one's on 25.
      { id: 4, callFrame: cf("render", 19), children: [5, 7], hitCount: 2, positionTicks: [{ line: 20, ticks: 1 }, { line: 25, ticks: 1 }] },
      { id: 5, callFrame: cf("fmt", 29), hitCount: 2 },
      { id: 6, callFrame: cf("(garbage collector)", -1, "") },
      { id: 7, callFrame: cf("render", 19), hitCount: 1, positionTicks: [{ line: 25, ticks: 1 }] },
    ],
    startTime: 1000, endTime: 1900,
    samples: [3, 4, 5, 5, 7, 2, 6, 4],
    timeDeltas: [100, 100, 100, 100, 100, 100, 100, 100],
  };
})();

test("frameKey labels a call frame url-basename:function:line, 1-based, and keeps V8's bookkeeping names", () => {
  assert.equal(frameKey({ functionName: "render", url: "http://127.0.0.1:1/dist/feed.js?v=3", lineNumber: 19 }), "feed.js:render:20");
  assert.equal(frameKey({ functionName: "", url: "http://127.0.0.1:1/dist/feed.js", lineNumber: 0 }), "feed.js:(anonymous):1");
  assert.equal(frameKey({ functionName: "tick", url: "", lineNumber: 4 }), "(inline):tick:5", "code without a url but with a line: an eval");
  assert.equal(frameKey({ functionName: "getBoundingClientRect", url: "", lineNumber: -1 }), "(native):getBoundingClientRect", "a builtin has neither");
  assert.equal(frameKey({ functionName: "ws.onmessage", url: "http://127.0.0.1:1/feed?token=secret-looking", lineNumber: 135 }), "feed:ws.onmessage:136", "the page's inline shim, query dropped");
  assert.equal(frameKey({ functionName: "(program)", url: "", lineNumber: -1 }), "(program)");
  assert.equal(frameKey({ functionName: "(garbage collector)", url: "", lineNumber: -1 }), "(garbage collector)");
  assert.equal(frameKey(null), "(unknown)");
});

test("aggregateProfile attributes each sample's interval as self time to its node and once as total time to every function on its stack", () => {
  const a = aggregateProfile(SYNTH_PROFILE);
  assert.equal(a.durationMs, 0.9);
  assert.equal(a.sampledMs, 0.8, "eight samples of 100 us, the last owning the interval to endTime");
  assert.equal(a.samples, 8);
  assert.deepEqual(a.meta, { "(program)": 0.1, "(garbage collector)": 0.1 }, "bookkeeping nodes are totalled, not ranked");
  const by = Object.fromEntries(a.functions.map((f) => [f.key, { key: f.key, selfMs: f.selfMs, totalMs: f.totalMs, samples: f.samples }]));
  assert.deepEqual(Object.keys(by).sort(), ["feed.js:fmt:30", "feed.js:main:10", "feed.js:render:20"]);
  assert.equal(a.functions.find((f) => f.key === "feed.js:render:20").cf.lineNumber, 19, "each function keeps a call frame for the source locator");
  assert.deepEqual(a.functions.find((f) => f.key === "feed.js:render:20").lines, [{ line: 25, ms: 0.2 }, { line: 20, ms: 0.1 }], "self time split over the function's lines by V8's ticks, both render nodes pooled");
  assert.equal(a.functions.find((f) => f.key === "feed.js:fmt:30").lines, undefined, "no ticks, no lines");
  assert.deepEqual(by["feed.js:render:20"], { key: "feed.js:render:20", selfMs: 0.3, totalMs: 0.5, samples: 3 }, "the recursive call's sample counts once in total");
  assert.deepEqual(by["feed.js:fmt:30"], { key: "feed.js:fmt:30", selfMs: 0.2, totalMs: 0.2, samples: 2 });
  assert.deepEqual(by["feed.js:main:10"], { key: "feed.js:main:10", selfMs: 0.1, totalMs: 0.6, samples: 1 });
  const ranked = rankProfile(a, 2);
  assert.deepEqual(ranked.topSelf.map((f) => f.key), ["feed.js:render:20", "feed.js:fmt:30"]);
  assert.deepEqual(ranked.topSelf[0].lines, [{ line: 25, ms: 0.2, share: 0.67 }, { line: 20, ms: 0.1, share: 0.33 }], "the hottest functions carry their lines");
  assert.equal(ranked.topTotal[1].lines, undefined, "the total ranking does not");
  assert.deepEqual(ranked.topTotal.map((f) => f.key), ["feed.js:main:10", "feed.js:render:20"]);
  assert.equal(ranked.functions, 3);
  // A window on the profile's clock: samples at 1300 and 1400 (both fmt under render under main).
  const w = aggregateProfile(SYNTH_PROFILE, [1250, 1450]);
  assert.ok(w.functions.every((f) => f.lines === undefined), "ticks cover the whole profile, so a window gets no lines");
  assert.equal(w.durationMs, 0.2, "a window's duration is its own width, not the profile's");
  assert.equal(w.samples, 2);
  assert.equal(w.sampledMs, 0.2);
  assert.deepEqual(w.meta, {});
  assert.deepEqual(Object.fromEntries(w.functions.map((f) => [f.key, [f.selfMs, f.totalMs]])), { "feed.js:fmt:30": [0.2, 0.2], "feed.js:render:20": [0, 0.2], "feed.js:main:10": [0, 0.2] });
  const merged = rankProfile(mergeAggregates([a, a]), 3);
  assert.equal(merged.sampledMs, 1.6);
  assert.equal(merged.topSelf[0].selfMs, 0.6, "iterations pool by summing");
  assert.deepEqual(merged.topSelf[0].lines, [{ line: 25, ms: 0.4, share: 0.67 }, { line: 20, ms: 0.2, share: 0.33 }], "and so do the lines");
  assert.deepEqual(merged.meta, { "(program)": 0.2, "(garbage collector)": 0.2 });
  const text = renderProfile({ files: ["/tmp/x.cpuprofile"], samplingIntervalUs: 500, alignMs: 0.4, ...ranked, windows: [{ label: "first content frame", index: 0, type: "feed", bytes: 5000, handlerMs: 0.3, ...rankProfile(w, 2) }] });
  assert.match(text, /cpu profile: 8 samples over 0\.9 ms at 500 us, 3 functions; bookkeeping: \(program\) 0\.1 ms, \(garbage collector\) 0\.1 ms/);
  assert.match(text, /written: \/tmp\/x\.cpuprofile/);
  assert.match(text, /top 2 by self time \(under a function, the lines[^\n]*\n\s+self ms\s+total ms\s+samples\s+url:function:line\n\s+0\.3\s+0\.5\s+3\s+feed\.js:render:20\n\s+67%\s+0\.2 ms  line 25\n\s+33%\s+0\.1 ms  line 20\n/);
  assert.match(text, /top 2 by total time\n[^\n]*\n\s+0\.1\s+0\.6\s+1\s+feed\.js:main:10/);
  assert.match(text, /window: first content frame \(feed, 4\.9 KB, frame 0\): handler 0\.3 ms, dispatch -, 0\.2 ms of window, 2 samples/);
  assert.doesNotMatch(text, /source:line/, "no source column without maps");
});

test("sourceLocator maps a bundle position to its source through the dist's .map file, and rankProfile carries it", () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "romp-ui-bench-map-"));
  try {
    // A two-line bundle whose map says: generated line 1 <- src/a.ts line 1, generated line 2 <- src/a.ts line 2 ("AAAA;AACA").
    fs.writeFileSync(path.join(tmp, "feed.js.map"), JSON.stringify({ version: 3, sources: ["../src/a.ts"], names: [], mappings: "AAAA;AACA" }));
    const locate = sourceLocator(tmp);
    assert.equal(locate({ functionName: "f", url: "http://127.0.0.1:1/dist/feed.js?v=9", lineNumber: 1, columnNumber: 4 }), "src/a.ts:2", "the leading ../ segments go when the source lies outside the repo");
    assert.equal(locate({ functionName: "f", url: "http://127.0.0.1:1/dist/feed.js", lineNumber: 0, columnNumber: 0 }), "src/a.ts:1");
    assert.equal(locate({ functionName: "g", url: "http://127.0.0.1:1/dist/other.js", lineNumber: 0, columnNumber: 0 }), null, "no map, no position");
    assert.equal(locate({ functionName: "native", url: "", lineNumber: -1 }), null);
    assert.equal(locate(null), null);
    assert.equal(locate.probe("feed.js"), true);
    assert.equal(locate.probe("other.js"), false);
    assert.deepEqual([...locate.loaded], ["feed.js"], "the locator says which maps it loaded");
    assert.deepEqual([...locate.missing], ["other.js"], "and which it could not");
    // A bundle whose second line first maps at column 4 (bundled node_modules code does this): a column-0
    // probe lands on line 1's mapping and the same-line guard refuses it; the per-line probe steps to it.
    fs.writeFileSync(path.join(tmp, "indent.js.map"), JSON.stringify({ version: 3, sources: ["../src/b.ts"], names: [], mappings: "AAAA;IACA" }));
    const cfi = { functionName: "f", url: "http://127.0.0.1:1/dist/indent.js?v=1", lineNumber: 1, columnNumber: 0 };
    assert.equal(locate(cfi), null, "the function-level lookup at column 0 refuses the previous line's mapping");
    assert.equal(locate.line(cfi, 1), "src/b.ts:2", "the per-line lookup finds the line's first mapping at column 4");
    assert.equal(locate.line(cfi, 0), "src/b.ts:1");
    assert.equal(locate.line(cfi, 7), null, "an unmapped line stays unresolved");
    assert.equal(locate.line({ functionName: "n", url: "", lineNumber: -1 }, 3), null);
    assert.equal(locate.line({ ...cfi, url: "http://127.0.0.1:1/dist/other.js" }, 1), null);
    const ranked = rankProfile(aggregateProfile(SYNTH_PROFILE), 1, locate);
    assert.equal(ranked.topSelf[0].src, undefined, "a line the map does not cover gets no position");
    const one = rankProfile({ durationMs: 1, sampledMs: 1, samples: 1, meta: {}, functions: [{ key: "feed.js:f:2", selfMs: 1, totalMs: 1, samples: 1, cf: { url: "http://x/dist/feed.js", lineNumber: 1, columnNumber: 0 }, lines: [{ line: 2, ms: 0.9 }, { line: 1, ms: 0.1 }, { line: 7, ms: 0.01 }] }] }, 1, locate);
    assert.deepEqual(one.topSelf, [{ key: "feed.js:f:2", selfMs: 1, totalMs: 1, samples: 1, src: "src/a.ts:2", lines: [{ line: 2, ms: 0.9, share: 0.9, src: "src/a.ts:2" }, { line: 1, ms: 0.1, share: 0.1, src: "src/a.ts:1" }] }], "lines resolve to their own source position; a line under a twentieth of the function's time is left out");
    const native = rankProfile({ durationMs: 1, sampledMs: 1, samples: 1, meta: {}, functions: [{ key: "(native):append", selfMs: 1, totalMs: 1, samples: 1, cf: { functionName: "append", url: "", lineNumber: -1 }, lines: [{ line: 5, ms: 1 }] }] }, 1, locate);
    assert.deepEqual(native.topSelf, [{ key: "(native):append", selfMs: 1, totalMs: 1, samples: 1 }], "a builtin's ticks name call sites in a file it does not have, so no lines");
    assert.match(renderProfile({ files: [], samplingIntervalUs: 500, alignMs: 0.1, sourceMaps: true, ...one, windows: [] }), /url:function:line  source:line\n\s+1\.0\s+1\.0\s+1\s+feed\.js:f:2  src\/a\.ts:2/);
    // The real dist, when built: the feed bundle's positions resolve into ui/webview.
    const dist = path.join(REPO, "vscode-extension", "dist");
    if (fs.existsSync(path.join(dist, "feed.js.map"))) {
      const real = sourceLocator(dist)({ functionName: "x", url: "http://127.0.0.1:1/dist/feed.js?v=1", lineNumber: 200, columnNumber: 0 });
      assert.match(real, /^(?!\.\.)(?!\/)\S+\.(ts|js):\d+$/, `a repo-relative source position: ${real}`);
    }
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
});

test("the report claims source positions only for bundles whose maps loaded, and warns about the ones without", () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "romp-ui-bench-maps-"));
  try {
    const mkRun = () => { const run = fakeRun({ perFrame: [pf(0, "feed", 5000, 40, 90), pf(1, "feedDelta", 300, 4, 20)] }); run.profiling = { profile: SYNTH_PROFILE, p0: 0, alignMs: 1 }; return run; };
    const build = (sourceMapDir) => buildReport({ app: "feed", framesFile: "f", cpuThrottle: 1, fast: true, iters: 1, browser: "t", runs: [mkRun()], cpuProfileFiles: ["/tmp/x.cpuprofile"], sourceMapDir });
    const noMaps = path.join(tmp, "nomaps");
    fs.mkdirSync(noMaps);
    const r1 = build(noMaps).cpuProfile;
    assert.equal(r1.sourceMaps, false, "a configured directory is not a loaded map");
    assert.deepEqual(r1.sourceMapsMissing, ["feed.js"]);
    assert.deepEqual(r1.sourceMapsLoaded, []);
    const t1 = renderProfile(r1);
    assert.match(t1, /warning: no feed\.js\.map beside the served bundle; names and lines are the bundle's own, and a --production build is minified/);
    assert.doesNotMatch(t1, /source positions from/);
    assert.doesNotMatch(t1, /source:line/);
    const withMaps = path.join(tmp, "maps");
    fs.mkdirSync(withMaps);
    fs.writeFileSync(path.join(withMaps, "feed.js.map"), JSON.stringify({ version: 3, sources: ["../src/a.ts"], names: [], mappings: "AAAA;AACA" }));
    const r2 = build(withMaps).cpuProfile;
    assert.equal(r2.sourceMaps, true);
    assert.deepEqual(r2.sourceMapsLoaded, ["feed.js"]);
    assert.deepEqual(r2.sourceMapsMissing, []);
    const t2 = renderProfile(r2);
    assert.match(t2, /source positions from feed\.js\.map/);
    assert.doesNotMatch(t2, /warning:/);
    assert.equal(r2.alignRefined, false, "this profile has no wrapper samples, so the bracketing estimate stands");
    assert.equal(r2.alignMs, 1);
    assert.equal(r2.alignBoundMs, 1);
    assert.match(t2, /±1\.0 ms \(the bracketing estimate; the refinement did not apply: no handler or dispatch windows to check against\)/);
    const first = r2.windows.find((w) => w.label === "first content frame");
    assert.equal(first.durationMs, 40, "a window's duration is the handler window's width");
    assert.equal(first.samples, 0, "and this profile has no samples in it");
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
});

test("refineAlignment recovers the page-to-profile offset from the wrapper's samples", () => {
  // Ten wrapper samples 100 us apart from t=100 us, then ten (program) samples. The true page time of the
  // profile's start is 50 ms, so the handler window is [50.1, 51.05) ms; the bracketing estimate is 3 ms off.
  const cf = (functionName, url) => ({ functionName, url, lineNumber: 1, columnNumber: 0 });
  const profile = {
    nodes: [{ id: 1, callFrame: cf("(root)", ""), children: [2, 4] }, { id: 2, callFrame: cf("rompBenchOnMessage", "ui-bench-instrument.js"), children: [3] },
      { id: 3, callFrame: cf("render", "http://x/dist/feed.js") }, { id: 4, callFrame: cf("(program)", "") }],
    startTime: 0, endTime: 2100, samples: [...Array(10).fill(3), ...Array(10).fill(4)], timeDeltas: Array(20).fill(100),
  };
  const al = refineAlignment(profile, 53, 5, [[50.1, 51.05]]);
  assert.ok(Math.abs(al.p0 - 50) <= 0.13, `refined to ${al.p0}`);
  assert.equal(al.alignMs, 0.125, "a single grid point fits: the uncertainty is a quarter of the sampling interval");
  assert.equal(al.inside, 1, "every wrapper sample lands inside a handler window");
  assert.equal(al.refined, true);
  const none = refineAlignment(profile, 53, 5, []);
  assert.deepEqual(none, { p0: 53, alignMs: 5, inside: null, refined: false }, "without windows the estimate stands");
  const noWrapper = refineAlignment({ ...profile, samples: Array(20).fill(4) }, 53, 5, [[50.1, 51.05]]);
  assert.deepEqual(noWrapper, { p0: 53, alignMs: 5, inside: null, refined: false }, "without wrapper samples too");
  const far = refineAlignment(profile, 53, 5, [[80, 81]]);
  assert.deepEqual(far, { p0: 53, alignMs: 5, inside: 0, refined: false }, "when no offset within the bound fits, the estimate and its bound stand and the result says so");
  // Two long handler windows with slack at both edges (the shape of a real run: samples every 0.5 ms
  // from 0.4 ms after each window opens): every offset within the slack scores the same, so the answer
  // is the plateau's midpoint and half its width is the uncertainty, not the grid step. The true offset
  // lies within that uncertainty; the data cannot place it more precisely.
  const wins = [[100, 800], [900, 1760]];
  const truth = 50;   // the page time of the profile's start
  const pageTimes = [];
  for (const [a, b] of wins) for (let x = a + 0.4; x <= b - 0.4 + 1e-9; x += 0.5) pageTimes.push(x);
  const us = pageTimes.map((x) => Math.round((x - truth) * 1000));
  const long = { nodes: profile.nodes, startTime: 0, endTime: us[us.length - 1] + 500, samples: us.map(() => 3), timeDeltas: us.map((u, i) => u - (i ? us[i - 1] : 0)) };
  const pl = refineAlignment(long, truth + 0.7, 2, wins);
  assert.equal(pl.refined, true);
  assert.equal(pl.inside, 1);
  assert.ok(pl.alignMs >= 0.3 && pl.alignMs <= 0.5, `half the plateau's width (about a millisecond of slack), not the grid step: ${pl.alignMs}`);
  assert.ok(Math.abs(pl.p0 - truth) <= pl.alignMs, `the true offset lies within the reported uncertainty: ${pl.p0} ± ${pl.alignMs}`);
  assert.ok(Math.abs(pl.p0 - truth) < 0.7, `and the 0.7 ms estimate error was corrected: ${pl.p0}`);
});

test("mergeWindows joins overlapping and touching windows and drops empty ones; refineAlignment counts a sample after a nested dispatch window's end as inside the handler window around it", () => {
  assert.deepEqual(mergeWindows([[10, 20], [12, 15], [20, 25], [30, 30], [40, 35], [27, 29]]), [[10, 25], [27, 29]]);
  assert.deepEqual(mergeWindows([[5, 6], [1, 2]]), [[1, 2], [5, 6]]);
  assert.deepEqual(mergeWindows([]), []);
  // The inline shim's shape: the handler window [50.1, 51.05) holds the dispatch window [50.2, 50.6); the wrapper's
  // samples run 0.1 ms apart across the whole handler window (true offset 50). Before the merge the search picked
  // the nested window for every sample after 50.2 and called the four after 50.6 outside.
  const cf = (functionName, url) => ({ functionName, url, lineNumber: 1, columnNumber: 0 });
  const profile = {
    nodes: [{ id: 1, callFrame: cf("(root)", ""), children: [2, 4] }, { id: 2, callFrame: cf("rompBenchOnMessage", "ui-bench-instrument.js"), children: [3] },
      { id: 3, callFrame: cf("rompBenchDispatch", "ui-bench-instrument.js") }, { id: 4, callFrame: cf("(program)", "") }],
    startTime: 0, endTime: 2100, samples: [...Array(10).fill(3), ...Array(10).fill(4)], timeDeltas: Array(20).fill(100),
  };
  const al = refineAlignment(profile, 53, 5, [[50.1, 51.05], [50.2, 50.6]]);
  assert.equal(al.inside, 1, "every sample lies inside the outer window");
  assert.ok(Math.abs(al.p0 - 50) <= 0.13, `refined to ${al.p0}`);
  assert.equal(al.refined, true);
  const same = refineAlignment(profile, 53, 5, [[50.1, 51.05]]);
  assert.deepEqual(al, same, "the nested window changes nothing about the fit");
  // the deferred shim's shape: a short handler window and a separate dispatch window later hold the samples between them (none falls in the gap)
  const split = refineAlignment(profile, 53, 5, [[50.05, 50.52], [50.58, 51.05]]);
  assert.equal(split.inside, 1);
  assert.ok(Math.abs(split.p0 - 50) <= 0.13, `refined to ${split.p0}`);
});

test("profileReport: a frame whose samples lie in its dispatch span only (the deferred shim) still fills its window, sized to the union of its spans; a nested dispatch span (the inline shim) is folded once", () => {
  const cf = (functionName, url) => ({ functionName, url, lineNumber: 1, columnNumber: 0 });
  const nodes = [{ id: 1, callFrame: cf("(root)", ""), children: [2, 5] }, { id: 2, callFrame: cf("rompBenchOnPort", "ui-bench-instrument.js"), children: [3] },
    { id: 3, callFrame: cf("rompBenchDispatch", "ui-bench-instrument.js"), children: [4] }, { id: 4, callFrame: cf("render", "http://127.0.0.1:1/dist/feed.js") }, { id: 5, callFrame: cf("(program)", "") }];
  // page clock: the feed frame's handler ran [100, 100.5); the flush handed it over at [130, 170); the profile started at page time 20
  const truth = 20;
  const times = [];
  for (let x = 130.2; x < 170; x += 0.5) times.push({ x, n: 4 });   // 80 render samples inside the dispatch span, each owning 0.5 ms
  for (let x = 170.2; x < 175; x += 0.5) times.push({ x, n: 5 });   // then (program) samples outside every window
  const us = times.map((s) => Math.round((s.x - truth) * 1000));
  const profile = { nodes, startTime: 0, endTime: us[us.length - 1] + 500, samples: times.map((s) => s.n), timeDeltas: us.map((u, i) => u - (i ? us[i - 1] : 0)) };
  const feed = { ...pf(0, "feed", 5000, 0.5, 90), t0: 100, dispatchT0: 130, dispatchMs: 40, dispatchInline: false };
  const ka = { ...pf(1, "ka", 30, 0.1, 5), t0: 200 };
  const args = { app: "feed", framesFile: "f", cpuThrottle: 1, fast: true, iters: 1, browser: "t" };
  const run = { ...fakeRun({ perFrame: [feed, ka], dispatch: { hook: true, unmatched: 0, flushTasks: 1, flushMs: 40.2 } }), profiling: { p0: truth + 0.8, alignMs: 1, profile } };
  const r = buildReport({ ...args, runs: [run] });
  const cp = r.cpuProfile;
  assert.ok(cp, "a profile was folded");
  assert.equal(cp.alignRefined, true, "the dispatch span's samples refined the alignment");
  assert.equal(cp.wrapperSamplesInHandlers, 1);
  const first = cp.windows.find((w) => w.label === "first content frame");
  assert.ok(first, cp.windows.map((w) => w.label).join(", "));
  assert.equal(first.handlerMs, 0.5);
  assert.equal(first.dispatchMs, 40);
  assert.equal(first.durationMs, 40.5, "the window is the handler span plus the dispatch span");
  assert.equal(first.samples, 80, "the samples in the dispatch span fill the window");
  assert.ok(Math.abs(first.sampledMs - 40) <= 1, `sampled ${first.sampledMs}`);
  assert.equal(first.topSelf[0].key, "feed.js:render:2");
  assert.deepEqual(cp.windows.map((w) => w.label), ["first content frame"], "a keepalive gets no window");
  assert.match(renderProfile(cp), /window: first content frame \(feed, 4\.9 KB, frame 0\): handler 0\.5 ms, dispatch 40\.0 ms, 40\.5 ms of window, 80 samples, 40\.0 ms sampled/);
  // the inline shim: the handler span [130, 170) holds the dispatch span [130.3, 169.8); the window is the handler span alone
  const inline = { ...feed, t0: 130, handlerMs: 40, dispatchT0: 130.3, dispatchMs: 39.5, dispatchInline: true };
  const ri = buildReport({ ...args, runs: [{ ...run, perFrame: [inline, ka] }] });
  const fi = ri.cpuProfile.windows[0];
  assert.equal(fi.durationMs, 40, "the union's width, not the sum of the spans");
  assert.equal(fi.samples, 80, "no sample counted twice");
  assert.equal(ri.cpuProfile.wrapperSamplesInHandlers, 1);
  assert.equal(ri.dispatch.inline, 1);
  // a frame the bench saw handled but never handed over (no dispatch span) keeps its handler-only window
  const alone = { ...feed, t0: 130, handlerMs: 40, dispatchT0: null, dispatchMs: null };
  const ra = buildReport({ ...args, runs: [{ ...run, perFrame: [alone, ka] }] });
  assert.equal(ra.cpuProfile.windows[0].durationMs, 40);
  assert.equal(ra.cpuProfile.windows[0].dispatchMs, null);
  assert.equal(ra.cpuProfile.windows[0].samples, 80);
});

test("aggregateProfile spreads self time over lines by V8's ticks per hit, not per sample, and gives no lines when no hit was recorded", () => {
  // The real profile has nodes whose hitCount is below their sample count (V8 records ticks with
  // update_stats off) and nodes with hitCount 0 that were still sampled.
  const cf = (functionName, lineNumber) => ({ functionName, url: "http://127.0.0.1:1/dist/feed.js", lineNumber, columnNumber: 0 });
  const prof = {
    nodes: [
      { id: 1, callFrame: { functionName: "(root)", url: "", lineNumber: -1 }, children: [2, 3] },
      { id: 2, callFrame: cf("render", 19), hitCount: 1, positionTicks: [{ line: 20, ticks: 1 }] },   // one tick recorded, two samples landed
      { id: 3, callFrame: cf("rk", 39), hitCount: 0 },
    ],
    startTime: 0, endTime: 400, samples: [2, 2, 3], timeDeltas: [100, 100, 100],
  };
  const a = aggregateProfile(prof);
  const render = a.functions.find((f) => f.key === "feed.js:render:20");
  assert.equal(render.selfMs, 0.2);
  assert.deepEqual(render.lines, [{ line: 20, ms: 0.2 }], "the lines sum to the node's self time (a per-sample split would say 0.1)");
  const rk = a.functions.find((f) => f.key === "feed.js:rk:40");
  assert.equal(rk.selfMs, 0.1);
  assert.equal(rk.lines, undefined, "self time but no lines when V8 recorded no hit");
  const ranked = rankProfile(a, 5);
  assert.deepEqual(ranked.topSelf[0].lines, [{ line: 20, ms: 0.2, share: 1 }]);
  assert.equal(ranked.topSelf[1].lines, undefined);
});

test("stripProfileQueries drops every call frame's URL query before the profile is written", () => {
  const prof = { nodes: [
    { id: 1, callFrame: { functionName: "ws.onmessage", url: "http://127.0.0.1:1/feed?token=secret-looking", lineNumber: 135 } },
    { id: 2, callFrame: { functionName: "render", url: "http://127.0.0.1:1/dist/feed.js?v=3", lineNumber: 19 } },
    { id: 3, callFrame: { functionName: "(program)", url: "", lineNumber: -1 } },
  ], startTime: 0, endTime: 1, samples: [1], timeDeltas: [1] };
  const out = stripProfileQueries(prof);
  assert.deepEqual(out.nodes.map((n) => n.callFrame.url), ["http://127.0.0.1:1/feed", "http://127.0.0.1:1/dist/feed.js", ""]);
  assert.doesNotMatch(JSON.stringify(out), /secret-looking|token=/);
  assert.ok(prof.nodes[0].callFrame.url.includes("token="), "the in-memory profile is untouched");
  assert.equal(out.samples, prof.samples);
});

test("aggregateProfile on an empty or window-less profile yields nothing rather than NaN", () => {
  const e = aggregateProfile({ nodes: [{ id: 1, callFrame: { functionName: "(root)", url: "", lineNumber: -1 } }], startTime: 5, endTime: 5, samples: [], timeDeltas: [] });
  assert.deepEqual(e, { durationMs: 0, sampledMs: 0, samples: 0, meta: {}, functions: [] });
  assert.deepEqual(rankProfile(e, 5).topSelf, []);
  assert.equal(aggregateProfile(SYNTH_PROFILE, [5000, 6000]).samples, 0);
});

// ── a real replay, when a browser is at hand ─────────────────────────────────────────────────────

const avail = browserAvailability();
const distBuilt = fs.existsSync(path.join(REPO, "vscode-extension", "dist", "feed.js"));
const pythonOk = (() => { try { return spawnSync("python3", ["--version"]).status === 0; } catch { return false; } })();
const skipServer = !distBuilt ? "no built bundles at vscode-extension/dist (run: cd vscode-extension && npm run build)"
  : !pythonOk ? "python3 is not on PATH (the replay serves the page through the kernel's own Handler)"
  : false;
const skipReplay = !avail.ok ? `no browser: ${avail.why}` : skipServer;
// ROMP_UI_BENCH_REQUIRE (CI sets it) turns a skip into a failure that names the missing prerequisite:
// a runner image that lost its Chrome must not turn the only CI run of the real pages into a green skip.
const required = !!process.env.ROMP_UI_BENCH_REQUIRE;
const gate = (why) => ({ skip: required ? false : why });
const requireOrSkip = (why) => { if (why) assert.fail(`ROMP_UI_BENCH_REQUIRE is set and this test cannot run: ${why}`); };

test("ROMP_UI_BENCH_REQUIRE turns the browser skip into a failure that names the reason", { timeout: 60_000 }, () => {
  const empty = fs.mkdtempSync(path.join(os.tmpdir(), "romp-ui-bench-nobrowser-"));
  try {
    const env = { ROMP_UI_BENCH_REQUIRE: "1", PATH: "", PLAYWRIGHT_BROWSERS_PATH: empty, HOME: os.homedir() };
    const r = spawnSync(process.execPath, ["--test", "--test-name-pattern", "^replay:", THIS_FILE], { env, encoding: "utf8", timeout: 50_000 });
    assert.notEqual(r.status, 0, `the nested run must fail\n${r.stdout}\n${r.stderr}`);
    assert.match(r.stdout, /ROMP_UI_BENCH_REQUIRE is set and this test cannot run: no browser/);
    assert.match(r.stdout, /# fail 2/, "both replay tests, not a skip");
    assert.doesNotMatch(r.stdout, /# skipped [1-9]/);
    delete env.ROMP_UI_BENCH_REQUIRE;
    const s = spawnSync(process.execPath, ["--test", "--test-name-pattern", "^replay:", THIS_FILE], { env, encoding: "utf8", timeout: 50_000 });
    assert.equal(s.status, 0, `without the variable the same run skips\n${s.stdout}\n${s.stderr}`);
    assert.match(s.stdout, /# skipped 2/);
  } finally {
    fs.rmSync(empty, { recursive: true, force: true });
  }
});

// ── the Handler subprocess ───────────────────────────────────────────────────────────────────────

test("startPageServer hands the Handler an isolated environment: a minted token, no manager, no API keys, no postal peers", { timeout: 30_000 }, async () => {
  // A stub interpreter stands in for python3: it echoes its environment, announces a port, and blocks on
  // stdin the way the Handler's watcher thread does. So this needs neither python nor the kernel.
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "romp-ui-bench-env-"));
  try {
    const stub = writeStub(tmp, "python-stub", `env > "$UI_BENCH_STUB_ENV_OUT"\nprintf 'ARGS %s\\n' "$#" >> "$UI_BENCH_STUB_ENV_OUT"\nprintf 'TMPARG %s\\n' "$4" >> "$UI_BENCH_STUB_ENV_OUT"\n`);
    const dist = fakeDist(tmp);
    const envOut = path.join(tmp, "env.txt");
    const planted = { UI_BENCH_STUB_ENV_OUT: envOut, ANTHROPIC_PROBE_FOR_THE_TEST: "must-not-cross", ROMP_CLAUDE_BIN: "/nonexistent/claude", ROMP_MANAGER_PORT: "1", ROMP_MANAGER_PID: "1", ROMP_SUPERVISED: "1", ROMP_POSTAL_PEERS: "1",
      ROMP_SERVICE_ENV_FILE: path.join(tmp, "planted-service.env"), ROMP_MODEL_CATALOG: "on" };
    const srv = await withEnv(planted, () => startPageServer({ dist, python: stub }));
    try {
      assert.equal(srv.port, 1);
      assert.match(srv.token, /^[A-Za-z0-9_-]{24}$/, "a per-run token, 18 random bytes as base64url");
      assert.ok(srv.pid > 0);
      assert.ok(fs.existsSync(srv.tmp));
      const env = Object.fromEntries(fs.readFileSync(envOut, "utf8").trim().split("\n").map((l) => { const i = l.indexOf("="); return i < 0 ? [l, ""] : [l.slice(0, i), l.slice(i + 1)]; }));
      assert.equal(env.ROMP_SERVE_TOKEN, srv.token);
      assert.equal(env.ROMP_POSTAL_PEERS, "0", "the Handler never asks the live postal bus for its peers");
      assert.equal(env.ROMP_KERNEL_NO_OPEN, "1");
      assert.equal(env.ROMP_SERVICE_ENV_FILE, path.join(srv.tmp, "no-service.env"), "the manager's key file is pointed at a path that never exists (the kernel would otherwise read ~/.config/romp/service.env)");
      assert.equal(env.ROMP_SERVICE_ENV, env.ROMP_SERVICE_ENV_FILE);
      assert.ok(!fs.existsSync(env.ROMP_SERVICE_ENV_FILE));
      assert.equal(env.ROMP_MODEL_CATALOG, "off", "no boot fetch of the Models API");
      assert.equal(env.ROMP_CLAUDE_BIN, "/bin/false", "a binary that runs nothing; removing the variable would resolve the real CLI");
      assert.equal(path.dirname(srv.tmp), srv.root, "the run directory sits under the per-user parent");
      assert.equal(path.basename(srv.root), `romp-ui-bench-${UID}`);
      assert.equal(fs.readFileSync(path.join(srv.tmp, "owner.pid"), "utf8").trim(), String(process.pid), "the run records its owner for the dead-owner sweep");
      if (process.platform !== "win32") { assert.equal(mode(srv.root), 0o700); assert.equal(mode(srv.tmp), 0o700); }
      assert.equal(env.ROMP_DIST_DIR, dist);
      assert.ok(env.XDG_STATE_HOME.startsWith(srv.tmp + path.sep), "a private state root");
      assert.ok(env.TMUX_TMPDIR.startsWith(srv.tmp + path.sep));
      assert.ok(fs.readFileSync(envOut, "utf8").includes(`\nTMPARG ${srv.tmp}\n`), "the subprocess is told its directory so it can remove it");
      for (const k of Object.keys(env)) assert.ok(!k.startsWith("ANTHROPIC_"), `${k} must not reach the Handler`);
      for (const k of STRIPPED_ENV) assert.equal(env[k], undefined, `${k} must not reach the Handler`);
      assert.equal(env.UI_BENCH_STUB_ENV_OUT, envOut, "unrelated variables pass through");
    } finally {
      srv.stop();
    }
    await sleep(100);
    assert.ok(!fs.existsSync(srv.tmp), "stop removes the directory");
    assert.throws(() => process.kill(srv.pid, 0), /ESRCH/, "and ends the subprocess");
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
});

test("startPageServer cleans up when the interpreter exits before announcing a port, and refuses without a dist before creating anything", { timeout: 30_000 }, async () => {
  // os.tmpdir() follows TMPDIR, so the server's directories land in a private one this test can list
  // (the machine's shared temp root is never enumerated).
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "romp-ui-bench-fail-"));
  const scratch = path.join(tmp, "scratch");
  fs.mkdirSync(scratch);
  try {
    await withEnv({ TMPDIR: scratch }, async () => {
      assert.equal(os.tmpdir(), scratch);
      await assert.rejects(startPageServer({ dist: path.join(tmp, "nodist") }), /no built bundles/);
      assert.deepEqual(fs.readdirSync(scratch), [], "the dist check runs before any directory is created");
      const dist = fakeDist(tmp);
      const dying = path.join(tmp, "python-dying");
      fs.writeFileSync(dying, "#!/bin/sh\necho 'ImportError: fake' >&2\nexit 3\n", { mode: 0o755 });
      await assert.rejects(startPageServer({ dist, python: dying }), /exited with 3[\s\S]*ImportError: fake/);
      const root = path.join(scratch, `romp-ui-bench-${UID}`);
      assert.deepEqual(fs.readdirSync(scratch), [path.basename(root)], "only the per-user parent is created");
      assert.deepEqual(fs.readdirSync(root), [], "an interpreter that dies before its port leaves no run directory behind");
      await assert.rejects(startPageServer({ dist, python: path.join(tmp, "no-such-interpreter") }), /could not start \S*no-such-interpreter: spawn \S*no-such-interpreter ENOENT/);
      assert.deepEqual(fs.readdirSync(root), [], "nor does one that cannot be spawned (an unhandled 'error' event used to crash the process and leak it)");
    });
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
});

test("benchRoot is a private per-user directory, and sweepDeadRuns reclaims the runs whose owner is gone", { timeout: 30_000 }, async () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "romp-ui-bench-root-"));
  const scratch = path.join(tmp, "scratch");
  fs.mkdirSync(scratch);
  try {
    await withEnv({ TMPDIR: scratch }, async () => {
      const root = benchRoot();
      assert.equal(root, path.join(scratch, `romp-ui-bench-${UID}`));
      if (process.platform !== "win32") {
        assert.equal(mode(root), 0o700);
        fs.chmodSync(root, 0o755);
        assert.equal(benchRoot(), root);
        assert.equal(mode(root), 0o700, "a loosened mode is restored");
      }
      const dead = spawnSync(process.execPath, ["-e", "0"]).pid;   // a process that has already exited
      const mk = (name, pid) => { fs.mkdirSync(path.join(root, name)); if (pid !== undefined) fs.writeFileSync(path.join(root, name, "owner.pid"), `${pid}\n`); };
      mk("run-dead", dead); mk("run-live", process.pid); mk("run-nopid"); mk("run-garbage", "abc");
      assert.deepEqual(sweepDeadRuns(root), ["run-dead"]);
      assert.deepEqual(fs.readdirSync(root).sort(), ["run-garbage", "run-live", "run-nopid"], "a live owner, a missing pid file and an unreadable one are left alone");
      mk("run-dead2", dead);
      const logged = [];
      const srv = await startPageServer({ dist: fakeDist(tmp), python: writeStub(tmp), log: (l) => logged.push(l) });
      try {
        assert.ok(!fs.existsSync(path.join(root, "run-dead2")), "a start sweeps the dead runs first");
        assert.ok(fs.existsSync(path.join(root, "run-live")), "and leaves the live ones");
        assert.ok(logged.some((l) => /removed 1 run directory left behind by dead runs/.test(l)), logged.join("\n"));
        assert.equal(path.dirname(srv.tmp), root);
      } finally {
        srv.stop();
      }
      assert.deepEqual(fs.readdirSync(root).sort(), ["run-garbage", "run-live", "run-nopid"], "stop removed its own run directory");
      assert.deepEqual(sweepDeadRuns(path.join(tmp, "absent")), [], "a missing root is nothing to sweep");
      // Something else holding the parent's name is refused, never adopted.
      const linkBase = path.join(tmp, "linkbase");
      fs.mkdirSync(path.join(tmp, "elsewhere"));
      fs.mkdirSync(linkBase);
      fs.symlinkSync(path.join(tmp, "elsewhere"), path.join(linkBase, `romp-ui-bench-${UID}`));
      assert.throws(() => benchRoot(linkBase), /not a directory; refusing/);
    });
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
});

test("launchBrowser puts Playwright's profile and artifacts directories under the run directory", { ...gate(skipReplay), timeout: 60_000 }, async () => {
  requireOrSkip(skipReplay);
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "romp-ui-bench-browser-"));
  const srv = await startPageServer({ dist: fakeDist(tmp), python: writeStub(tmp) });
  const before = process.env.TMPDIR;
  let browser;
  try {
    browser = await launchBrowser({ tmpRoot: srv.tmp });
    assert.equal(process.env.TMPDIR, before, "TMPDIR is restored once the browser is up");
    const names = fs.readdirSync(srv.tmp);
    assert.ok(names.some((n) => n.startsWith("playwright")), `the browser's directories live in the run directory, where stop() and the sweep reach them: ${names.join(", ")}`);
  } finally {
    if (browser) await browser.close().catch(() => {});
    srv.stop();
    fs.rmSync(tmp, { recursive: true, force: true });
  }
  assert.ok(!fs.existsSync(srv.tmp), "stop takes the browser's directories with the run's");
});

test("the Handler subprocess ends and removes its directory when the node process that started it is SIGKILLed", { ...gate(skipServer), timeout: 90_000 }, async () => {
  requireOrSkip(skipServer);
  const script = `
    import { startPageServer } from ${JSON.stringify(pathToFileURL(TOOL).href)};
    const s = await startPageServer({ log: () => {} });
    process.stdout.write(JSON.stringify({ pid: s.pid, tmp: s.tmp, port: s.port }) + "\\n");
    setInterval(() => {}, 1000);
  `;
  const child = spawn(process.execPath, ["--input-type=module", "-e", script], { stdio: ["ignore", "pipe", "pipe"] });
  let info = null;
  try {
    let buf = "", err = "";
    child.stderr.on("data", (c) => { err += c; });
    info = await new Promise((resolve, reject) => {
      child.stdout.on("data", (c) => { buf += c; const nl = buf.indexOf("\n"); if (nl >= 0) resolve(JSON.parse(buf.slice(0, nl))); });
      child.on("exit", (code) => reject(new Error(`the child exited early with ${code}: ${err}`)));
    });
    assert.ok(fs.existsSync(info.tmp), "the Handler's directory exists while it runs");
    assert.doesNotThrow(() => process.kill(info.pid, 0), "the Handler is alive");
    const page = await new Promise((resolve, reject) => http.get({ host: "127.0.0.1", port: info.port, path: "/feed" }, (res) => { res.resume(); resolve(res.statusCode); }).on("error", reject));
    assert.equal(page, 403, "and without the minted token the page route refuses");
  } finally {
    child.kill("SIGKILL");
  }
  const t0 = Date.now();
  let alive = true, dirThere = true;
  while (Date.now() - t0 < 20_000) {
    try { process.kill(info.pid, 0); alive = true; } catch (e) { alive = e.code !== "ESRCH"; }
    dirThere = fs.existsSync(info.tmp);
    if (!alive && !dirThere) break;
    await sleep(50);
  }
  assert.equal(alive, false, "the Handler ended once its stdin pipe closed");
  assert.equal(dirThere, false, "and removed its directory");
});

// ── a real replay, when a browser is at hand ─────────────────────────────────────────────────────

for (const app of ["feed", "timeline"]) {
  test(`replay: a synthetic ${app} stream renders in headless Chromium, every frame type measured, no console errors`,
    { ...gate(skipReplay), timeout: 180_000 }, async () => {
      requireOrSkip(skipReplay);
      const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "romp-ui-bench-replay-"));
      try {
        const frames = synthesizeFrames(app, 40);
        const file = path.join(tmp, `${app}.jsonl`);
        writeFrames(file, { synthetic: true, app }, frames);
        const jsonOut = path.join(tmp, "report.json");
        const cpuProfile = app === "feed" ? path.join(tmp, "prof", "feed.cpuprofile") : undefined;
        const timersBefore = process.getActiveResourcesInfo().filter((x) => x === "Timeout").length;
        const report = await replay({ app, framesFile: file, fast: true, jsonOut, cpuProfile, log: () => {} });
        const timersAfter = process.getActiveResourcesInfo().filter((x) => x === "Timeout").length;
        assert.ok(timersAfter <= timersBefore, `replay left ${timersAfter - timersBefore} timer(s) armed (the handshake timeout must be cleared)`);
        assert.equal(process.listenerCount("SIGINT"), 0, "the signal handlers are removed on the way out");
        assert.equal(report.tool, "ui-bench");
        assert.equal(report.app, app);
        assert.equal(report.fast, true);
        assert.equal(report.cpuThrottle, 1);
        assert.equal(report.frames.total, frames.length);
        assert.equal(report.frames.misaligned, 0, "every page record matched its frame by length");
        assert.equal(report.frames.reconnects, 0);
        for (const k of ["first", "types", "loaf", "end", "console", "clientMessages", "perFrame"]) assert.ok(k in report, `report.${k}`);
        assert.ok(report.frames.readyMs > 0, "the page reached its ready handshake");
        const expected = new Set(frames.map((f) => classifyFrame(f.data)));
        assert.ok(expected.size >= 3);
        for (const type of expected) {
          const s = report.types[type];
          assert.ok(s, `a row for ${type}`);
          assert.ok(s.measured >= 1, `${type}: at least one measured frame`);
          assert.equal(s.measured, s.count, `${type}: every frame measured`);
          assert.equal(s.handlerMs.n, s.count, `${type}: every frame's handler timed`);
          assert.equal(s.settleMs.n, s.count, `${type}: every frame's settle stamped (null percentiles compare as 0, so the sample size is what proves it)`);
          assert.equal(s.settleMissing, 0, `${type}: no settle stamp missing`);
          assert.equal(typeof s.settleMs.p50, "number");
          assert.ok(s.handlerMs.p50 >= 0 && s.handlerMs.max >= s.handlerMs.p50, `${type}: handler percentiles`);
          assert.ok(s.settleMs.p50 >= 0 && s.settleMs.max >= s.settleMs.p50, `${type}: settle percentiles`);
          assert.ok(s.settleMs.p50 >= s.handlerMs.p50, `${type}: the main thread is free no sooner than the handler returns`);
        }
        assert.equal(report.frames.settleMissing, 0);
        // The bundle's work per frame: the shim's handoff, window.__rompFed.inbound, timed by the dispatch hook on both
        // shims (inside the socket handler on the inline shim, from a queued flush task on the deferred one).
        assert.equal(report.dispatch.hook, true, `federation.js assigned window.__rompFed and the bench wrapped its inbound${report.dispatch.hookError ? `: ${report.dispatch.hookError}` : ""}`);
        assert.equal(report.dispatch.unmatched, 0, "every inbound call matched a frame the replay sent");
        assert.equal(report.dispatch.inline + report.dispatch.deferred, Object.values(report.types).reduce((a, s) => a + s.dispatched, 0), "every handoff is counted as inline or deferred");
        assert.ok(report.dispatch.inline + report.dispatch.deferred > 0);
        // The inline/deferred split and the flush counter come from the page-side instrument (R.depth and the MessagePort
        // wrapper), which only this test runs; the two relations below hold on both shims and fail when either breaks.
        assert.ok(report.dispatch.inline === 0 || report.dispatch.deferred === 0, `one shim shape ran: every handoff inside the socket handler or every one from a flush task (${report.dispatch.inline} inline, ${report.dispatch.deferred} deferred)`);
        assert.equal(report.dispatch.deferred > 0, report.dispatch.flushTasks > 0, `deferred handoffs come from flush tasks, and flush tasks exist only when handoffs were deferred (${report.dispatch.deferred} deferred, ${report.dispatch.flushTasks} flush tasks)`);
        // A frame's settle is stamped two animation frames after the later of its handler and its handoff, so it lands after
        // the frame's own handoff on both shims (the rows are rounded to 0.1 ms; 0.2 covers the rounding of three values).
        for (const f of report.perFrame) {
          if (f.dispatchT0 == null) continue;
          assert.ok(f.t0 + f.settleMs + 0.2 >= f.dispatchT0 + f.dispatchMs, `frame ${f.i} (${f.type}): the settle stamp lands after the frame's own handoff (handler at ${f.t0}, settle ${f.settleMs} ms, handoff ${f.dispatchT0} to ${Math.round((f.dispatchT0 + f.dispatchMs) * 10) / 10})`);
        }
        for (const type of expected) {
          const s = report.types[type];
          if (dispatchType(type) == null) { assert.equal(s.dispatched, 0, `${type}: never handed to the bundle`); assert.equal(s.coalesced, 0); continue; }
          assert.equal(s.dispatched + s.coalesced, s.count, `${type}: every frame handed to the bundle or replaced by a newer frame of its type before the handoff (${s.dispatched} + ${s.coalesced} of ${s.count})`);
          assert.equal(s.dispatchMs.n, s.dispatched, `${type}: every handoff timed`);
          assert.ok(s.dispatched === 0 || s.dispatchMs.p50 >= 0, `${type}: dispatch percentiles`);
        }
        // The first content frame's handoff. The feed stream holds one feed frame, so nothing can replace it and its
        // render is milliseconds on any machine. The timeline's first frame is the skeleton (data), a whole-state type
        // the stream repeats: on the deferred shim a back-to-back replay can queue a later skeleton before the first
        // flush, and the shim then hands over only the newer one, so the first frame is coalesced and not timed.
        const firstRow = report.perFrame[report.first.index];
        if (firstRow.coalesced) {
          assert.ok(WHOLE_STATE_TYPES.has(dispatchType(report.first.type)), `only a whole-state frame can be replaced before its handoff (${report.first.type})`);
          assert.ok(report.types[report.first.type].dispatched >= 1, "a newer frame of its type was handed over instead");
          assert.equal(report.first.dispatchMs, null);
        } else {
          assert.ok(report.first.dispatchMs > 0, `the first content frame's handoff took time (${report.first.dispatchMs} ms)`);
          assert.ok(firstRow.dispatchT0 >= firstRow.t0, "the handoff starts no earlier than the frame's handler");
        }
        if (app === "feed") assert.ok(report.first.dispatchMs > 0, `the one feed frame is always handed over, and forty cards render in milliseconds (${report.first.dispatchMs} ms)`);
        assert.equal(report.frames.addListenerMessages, 0, "the pane's socket handler is the onmessage the bench times");
        assert.equal(report.frames.buildBannerRaised, 0, "a synthetic stream's keepalive dv never outruns the dist");
        assert.equal(report.frames.connBannerRaised, 0);
        assert.equal(report.end.afterGc, true);
        assert.equal(report.first.type, app === "feed" ? "feed" : "data");
        assert.ok(report.first.bytes > 1000);
        assert.deepEqual(report.console.errors, [], "console errors");
        assert.deepEqual(report.console.pageErrors, [], "uncaught exceptions");
        assert.deepEqual(report.console.failedResources, [], "every page resource served");
        assert.equal(report.clientMessages.ready, 1, "the bundle's handshake, once");
        assert.ok(!report.clientMessages.needSlot && !report.clientMessages.needFullFeed, "the pane applied every frame without asking for a resync");
        assert.ok(report.end.heapUsed > 0);
        assert.ok(report.end.domElements > 20);
        assert.ok(report.end.cdpNodes >= report.end.domElements);
        assert.equal(typeof report.loaf.count, "number");
        assert.ok(["long-animation-frame", "longtask"].includes(report.loaf.kind), "an observer kind was chosen");
        if (app === "feed") assert.ok(report.end.domElements > 40 * 5, "forty cards render as more than a handful of elements each");
        const disk = JSON.parse(fs.readFileSync(jsonOut, "utf8"));
        assert.equal(disk.frames.total, frames.length, "--json wrote the same report");
        const text = renderReport(report);
        assert.match(text, new RegExp(`^ui-bench ${app}: ${frames.length} frames`));
        assert.match(text, /console: 0 errors, 0 uncaught exceptions/);
        assert.doesNotMatch(text, /warning:/);
        if (cpuProfile) {
          const cp = report.cpuProfile;
          assert.ok(cp, "a CPU profile was taken");
          assert.deepEqual(cp.files, [cpuProfile]);
          const raw = JSON.parse(fs.readFileSync(cpuProfile, "utf8"));
          for (const k of ["nodes", "startTime", "endTime", "samples", "timeDeltas"]) assert.ok(k in raw, `.cpuprofile has ${k}`);
          assert.ok(raw.samples.length > 100, `enough samples (${raw.samples.length})`);
          assert.equal(cp.samplingIntervalUs, 500);
          assert.equal(cp.alignRefined, true, "the wrapper's samples refined the clock alignment");
          assert.ok(cp.alignMs > 0 && cp.alignMs <= cp.alignBoundMs, `the refined uncertainty (${cp.alignMs} ms) is within the bracketing bound (${cp.alignBoundMs} ms)`);
          assert.ok(cp.wrapperSamplesInHandlers >= 0.9, `the instrument's samples fall inside the frames' handler and dispatch windows (${cp.wrapperSamplesInHandlers})`);
          assert.equal(cp.sourceMaps, true);
          assert.deepEqual(cp.sourceMapsMissing, [], "every profiled bundle had its map beside it");
          assert.ok(cp.sourceMapsLoaded.includes("feed.js"), cp.sourceMapsLoaded.join(", "));
          assert.ok(!fs.readFileSync(cpuProfile, "utf8").includes("token="), "the written profile carries no serve token (the page URL's query is dropped from every frame)");
          assert.ok(cp.topSelf.some((f) => /^ui\/webview\/\S+\.ts:\d+$/.test(f.src || "")), `source positions resolved: ${cp.topSelf.slice(0, 5).map((f) => f.src).join(", ")}`);
          assert.ok(cp.topSelf.slice(0, 5).some((f) => f.lines && f.lines.length && f.lines[0].src), `the hottest functions name their lines: ${JSON.stringify(cp.topSelf[0].lines)}`);
          assert.ok(cp.windows.every((w) => w.topSelf.every((f) => !f.lines)), "windows carry no line split");
          assert.ok(cp.topSelf.length > 5 && cp.topTotal.length > 5);
          assert.ok(cp.topSelf.some((f) => /^feed\.js:[^:]+:\d+$/.test(f.key)), `functions of the feed bundle are named: ${cp.topSelf.slice(0, 5).map((f) => f.key).join(", ")}`);
          assert.ok(cp.topSelf.every((f) => !/^\((program|idle|garbage collector|root)\)$/.test(f.key)), "bookkeeping nodes are not ranked");
          assert.ok(cp.topTotal[0].totalMs >= cp.topSelf[0].selfMs);
          const labels = cp.windows.map((w) => w.label);
          assert.ok(labels.includes("first content frame"), labels.join(", "));
          assert.ok(labels.includes("largest feedDelta"), labels.join(", "));
          const first = cp.windows.find((w) => w.label === "first content frame");
          assert.equal(first.type, "feed");
          assert.ok(first.samples > 0 && first.topSelf.length > 0, "the first frame's window (its handler and dispatch spans) has samples");
          assert.ok(first.dispatchMs > 0, `the first window row carries the frame's dispatch time (${first.dispatchMs})`);
          assert.ok(first.durationMs >= Math.max(first.handlerMs, first.dispatchMs), `the window spans both (${first.durationMs} ms of window for handler ${first.handlerMs}, dispatch ${first.dispatchMs})`);
          assert.ok(Math.abs(first.sampledMs - first.durationMs) <= Math.max(5, first.durationMs * 0.25), `the window's sampled time (${first.sampledMs}) tracks the union of its handler and dispatch spans (${first.durationMs})`);
          assert.ok(first.topSelf.some((f) => /^feed\.js:/.test(f.key)), `the first frame's window holds the feed bundle's work: ${first.topSelf.slice(0, 5).map((f) => f.key).join(", ")}`);
          assert.match(text, /cpu profile: \d+ samples over/);
          assert.match(text, /window: first content frame \(feed,.*handler [\d.]+ ms, dispatch [\d.]+ ms, [\d.]+ ms of window/);
        } else {
          assert.equal(report.cpuProfile, undefined);
        }
      } finally {
        fs.rmSync(tmp, { recursive: true, force: true });
      }
    });
}

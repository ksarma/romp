// tests/ui-bench.test.mjs: tools/ui-bench.mjs, the headless-Chrome bench for the dashboard panes.
//
// Two layers. Browser-free: the frame classifier (the report's rows), the percentile and compare
// arithmetic, the report fold, the /tmp path guard that keeps a recording of real session data out
// of any git checkout, and the synthesizer's wire shapes (the kernel's _keys list for the bars slot,
// contiguous delta revisions, a byte-stable stream). With a browser: a synthetic feed stream and a
// synthetic timeline stream replayed back-to-back into the REAL pages, served by the kernel's own
// page route and the built bundles, must produce a report with every frame type measured and no
// console error, uncaught exception or failed resource load. Those two tests skip, naming the
// reason, when no Chromium, no python3 or no built dist is available.
//
// Everything here is synthetic: the notes-api demo domain, placeholder uuids, a fixed clock.
// Run: node --test tests/ui-bench.test.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";
import {
  APPS, DELTA_SEP, REPO, assertTmpPath, barsKeys, browserAvailability, buildReport, classifyFrame, compareReports,
  loadFrames, percentile, renderCompare, renderReport, replay, streamSummary, summarize, synthesizeFrames, writeFrames,
} from "../tools/ui-bench.mjs";

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

function fakeRun({ perFrame, loaf = [], heapUsed = 1000, domElements = 10, consoleErrors = [] }) {
  return {
    readyMs: 100, replayMs: 50, sent: perFrame, perFrame, misaligned: 0, reconnects: 0, clientMessages: { ready: 1 }, clientDiag: {},
    loaf, loafKind: "long-animation-frame", domElements, heap: { used: heapUsed, total: heapUsed * 2 }, addListenerMessages: 0,
    cdp: { nodes: domElements * 3, documents: 1, jsEventListeners: 5, layoutCount: 3, recalcStyleCount: 4, layoutMs: 1.5, recalcStyleMs: 0.5, scriptMs: 20, taskMs: 30, heapUsed, heapTotal: heapUsed * 2 },
    consoleErrors, pageErrors: [], warnings: 0, failedResources: [],
  };
}
const pf = (i, type, bytes, handlerMs, settleMs) => ({ i, type, bytes, at: i, handlerMs, settleMs, lenMatch: true });

test("buildReport folds runs per frame type with percentiles, attribution and end state", () => {
  const run = fakeRun({
    perFrame: [pf(0, "ka", 30, 0.1, 5), pf(1, "feed", 5000, 40, 90), pf(2, "feedDelta", 300, 4, 20), pf(3, "feedDelta", 500, 6, 30), pf(4, "feedDelta", 100, 2, 10)],
    loaf: [{ start: 0, duration: 120, blocking: 70, scripts: [{ url: "http://127.0.0.1:1/dist/feed.js?v=1", fn: "render", invoker: "DOMWebSocket.onmessage", duration: 100 },
      { url: "", fn: "", invoker: "http://127.0.0.1:1/feed?token=secret-looking", duration: 15 }] }],
    heapUsed: 4096, domElements: 250,
  });
  const r = buildReport({ app: "feed", framesFile: "/tmp/x.jsonl", cpuThrottle: 1, fast: true, iters: 1, browser: "test", runs: [run] });
  assert.equal(r.tool, "ui-bench");
  assert.equal(r.frames.total, 5);
  assert.equal(r.frames.bytes, 5930);
  assert.deepEqual(r.first, { index: 1, type: "feed", bytes: 5000, handlerMs: 40, settleMs: 90 }, "the first content frame skips the keepalive");
  assert.deepEqual(Object.keys(r.types), ["feed", "feedDelta", "ka"], "rows ordered by bytes");
  assert.equal(r.types.feedDelta.count, 3);
  assert.equal(r.types.feedDelta.measured, 3);
  assert.equal(r.types.feedDelta.bytes, 900);
  assert.equal(r.types.feedDelta.bytesMax, 500);
  assert.deepEqual(r.types.feedDelta.handlerMs, { n: 3, p50: 4, p90: 6, max: 6, mean: 4 });
  assert.deepEqual(r.types.feedDelta.settleMs, { n: 3, p50: 20, p90: 30, max: 30, mean: 20 });
  assert.equal(r.loaf.count, 1);
  assert.equal(r.loaf.blockingMs, 70);
  assert.equal(r.loaf.topScripts[0].key, "feed.js:render <DOMWebSocket.onmessage>");
  assert.equal(r.loaf.topScripts[1].key, "(inline):(anonymous) <script feed>", "a URL-shaped invoker keeps its basename and loses its query");
  assert.equal(r.end.heapUsed, 4096);
  assert.equal(r.end.domElements, 250);
  assert.equal(r.end.cdpNodes, 750);
  assert.equal(r.perFrame.length, 5, "a single run keeps the per-frame rows");
  const text = renderReport(r);
  assert.match(text, /first content frame: feed, 4\.9 KB/);
  assert.match(text, /feedDelta\s+3\s+900 B\s+500 B\s+4\.0 \/ 6\.0 \/ 6\.0/);
  assert.match(text, /console: 0 errors/);
  assert.doesNotMatch(text, /secret-looking/, "no query string from a page URL reaches the report");
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
  const mk = (settle, loafBlocking, heap, errors) => ({
    app: "feed", cpuThrottle: 1, fast: true,
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
  const text = renderCompare(c);
  assert.match(text, /feed\s+count 1 → 1 \(unchanged\); settle p50 200 → 150 ms \(-50, -25%\)/);
  assert.match(text, /first content frame: bytes 5000 → 5000 \(unchanged\); handler 100 → 75 ms \(-25, -25%\)/);
  assert.match(text, /feedDelta\s+count - → 4;/);
  assert.match(text, /heap 4000 → 5000 B \(\+1000, \+25%\)/);
  assert.match(text, /console errors: 0 → 1/);
});

// ── the path guard ───────────────────────────────────────────────────────────────────────────────

test("assertTmpPath allows /tmp, refuses the repo, other roots, and a checkout under /tmp", () => {
  const ok = fs.mkdtempSync(path.join("/tmp", "romp-ui-bench-guard-"));
  try {
    assert.equal(assertTmpPath(path.join(ok, "frames.jsonl")), path.join(ok, "frames.jsonl"));
    assert.equal(assertTmpPath(path.join(ok, "deeper", "frames.jsonl")), path.join(ok, "deeper", "frames.jsonl"), "a not-yet-created leaf directory is fine");
    assert.throws(() => assertTmpPath(path.join(REPO, "frames.jsonl")), /outside \/tmp/);
    assert.throws(() => assertTmpPath("/var/tmp/frames.jsonl"), /outside \/tmp/);
    assert.throws(() => assertTmpPath("frames.jsonl"), /outside \/tmp/, "a relative path resolves against the cwd, which is not /tmp here");
    fs.mkdirSync(path.join(ok, "clone", ".git"), { recursive: true });
    assert.throws(() => assertTmpPath(path.join(ok, "clone", "sub", "frames.jsonl")), /inside a git checkout/);
  } finally {
    fs.rmSync(ok, { recursive: true, force: true });
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
  const fleetFull = JSON.parse(synthesizeFrames("fleet", 12)[0].data);
  assert.equal(fleetFull.ledgers.length, 3);
  assert.ok(fleetFull.ledgers.every((l) => l.sid && l.name && l.ledger && Array.isArray(l.ledger.tree)));
  assert.ok(synthesizeFrames("fleet", 12).some((f) => Array.isArray(JSON.parse(f.data).ledgers) && JSON.parse(f.data).type === "feedDelta"), "some deltas upsert a ledger");
  const waitingFull = JSON.parse(synthesizeFrames("waiting", 12)[0].data);
  assert.ok(Array.isArray(waitingFull.userTodoRows) && waitingFull.userTodoRows.length >= 1);
  assert.equal(waitingFull.userTodosOn, true);
});

test("synthesizeFrames: the timeline stream is the skeleton, the keyed bars slot, then bar-level deltas", () => {
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
  assert.ok(bars._keys, "a keyed full frame carries the kernel's key list");
  assert.deepEqual(bars._keys, barsKeys(bars));
  assert.ok(bars._keys.turns.every((k) => k.includes(DELTA_SEP)), "a bar's key is lane + separator + id");
  assert.equal(bars._keys.turns.length, 30);
  assert.ok(bars._keys.judging.every((k) => k.split(DELTA_SEP).length === 4), "a judging key is sid, t, judge, t1");
  let rev = 0;
  for (const f of frames) {
    const m = JSON.parse(f.data);
    if (m.type !== "delta") continue;
    assert.equal(m.slot, "bars");
    assert.equal(m.base, rev, "each delta's base is the revision the pane holds");
    assert.equal(m.rev, rev + 1); rev = m.rev;
    assert.ok(m.coll.turns.set && Object.keys(m.coll.turns.set).every((k) => k.includes(DELTA_SEP)));
    assert.equal(typeof m.rest.now, "number", "the clock rides every delta");
  }
  assert.ok(rev >= 20);
  assert.ok(types.filter((t) => t === "data").length >= 2, "the skeleton is re-pushed during the stream");
  assert.deepEqual(Object.keys(streamSummary(frames).byType).sort(), ["bars", "data", "delta:bars", "ka"]);
});

test("barsKeys mints the kernel's keys: an empty lane is its bare prefix, messages key by id", () => {
  const keys = barsKeys({ turns: { a: [], b: [{ id: "x" }, { id: 7 }] }, judging: [{ sid: "s", t: 1, judge: "closer", t1: 2 }], messages: [{ id: "m1" }] });
  assert.deepEqual(keys, { turns: ["a" + DELTA_SEP, "b" + DELTA_SEP + "x", "b" + DELTA_SEP + "7"], judging: ["s" + DELTA_SEP + "1" + DELTA_SEP + "closer" + DELTA_SEP + "2"], messages: ["m1"] });
});

test("synthesizeFrames refuses the apps it cannot fake, and unknown apps", () => {
  assert.throws(() => synthesizeFrames("chat", 5), /not synthesized/);
  assert.throws(() => synthesizeFrames("files", 5), /not synthesized/);
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
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
});

// ── a real replay, when a browser is at hand ─────────────────────────────────────────────────────

const avail = browserAvailability();
const distBuilt = fs.existsSync(path.join(REPO, "vscode-extension", "dist", "feed.js"));
const pythonOk = (() => { try { return spawnSync("python3", ["--version"]).status === 0; } catch { return false; } })();
const skipReplay = !avail.ok ? `no browser: ${avail.why}`
  : !distBuilt ? "no built bundles at vscode-extension/dist (run: cd vscode-extension && npm run build)"
  : !pythonOk ? "python3 is not on PATH (the replay serves the page through the kernel's own Handler)"
  : false;

for (const app of ["feed", "timeline"]) {
  test(`replay: a synthetic ${app} stream renders in headless Chromium, every frame type measured, no console errors`,
    { skip: skipReplay, timeout: 180_000 }, async () => {
      const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "romp-ui-bench-replay-"));
      try {
        const frames = synthesizeFrames(app, 40);
        const file = path.join(tmp, `${app}.jsonl`);
        writeFrames(file, { synthetic: true, app }, frames);
        const jsonOut = path.join(tmp, "report.json");
        const report = await replay({ app, framesFile: file, fast: true, jsonOut, log: () => {} });
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
          assert.ok(s.handlerMs.p50 >= 0 && s.handlerMs.max >= s.handlerMs.p50, `${type}: handler percentiles`);
          assert.ok(s.settleMs.p50 >= 0 && s.settleMs.max >= s.settleMs.p50, `${type}: settle percentiles`);
          assert.ok(s.settleMs.p50 >= s.handlerMs.p50, `${type}: the main thread is free no sooner than the handler returns`);
        }
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
      } finally {
        fs.rmSync(tmp, { recursive: true, force: true });
      }
    });
}

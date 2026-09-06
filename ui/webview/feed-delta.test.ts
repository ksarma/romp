// The feed's delta path, client side (2026-09-02): the kernel streams {type:"feedDelta"} frames to the
// local socket once it holds a full frame; federation.ts applies them onto its per-host last full frame
// and re-emits a merged full `feed`, so every downstream consumer keeps seeing whole frames. Pure-function
// tests on applyFeedDelta plus source pins on the wiring (the harness imports no DOM; see feed-dead.test.ts).
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { applyFeedDelta, upsertById } from "./feed-delta";
import { mergeHostFeeds, FederationManager } from "./federation";
import { ageRgb } from "./age-color";
import { liveNow } from "./feed-age";

const UI = path.resolve(process.cwd(), "..", "ui", "webview");
const FEED = fs.readFileSync(path.join(UI, "feed.ts"), "utf8");
const FED = fs.readFileSync(path.join(UI, "federation.ts"), "utf8");
const KERNEL = fs.readFileSync(path.resolve(process.cwd(), "..", "kernel", "kernel.py"), "utf8");

const card = (i: number, over: Record<string, unknown> = {}) => ({
  itemId: "TESTSID:g" + i, sid: "TESTSID", name: "web", text: "goal " + i, t: 1000 - i, column: "working", ...over,
});
const base = () => ({
  type: "feed", asks: [card(0), card(1), card(2)], now: 1000, buildId: 1,
  order: ["TESTSID"], working: ["web"], sessions: [{ sid: "TESTSID", name: "web", color: null }],
  ledgers: [{ sid: "TESTSID", name: "web", ledger: { tops: [] }, status: { state: "working" } }],
});

test("upserts replace in place by id, removals drop, new cards append; the base is untouched", () => {
  const b = base();
  const out = applyFeedDelta(b, { type: "feedDelta", now: 1010, buildId: 2,
    asks: [card(1, { text: "changed" }), card(9)], removeAsks: ["TESTSID:g2"] });
  assert.equal(out.type, "feed");
  assert.deepEqual(out.asks.map((a: any) => a.itemId), ["TESTSID:g0", "TESTSID:g1", "TESTSID:g9"]);
  assert.equal(out.asks[1].text, "changed");
  assert.equal(out.now, 1010); assert.equal(out.buildId, 2);
  assert.deepEqual(out.order, ["TESTSID"], "non-keyed fields carry over when the delta has no `top`");
  assert.deepEqual(out.ledgers, b.ledgers, "ledgers carry over when the delta has none");
  assert.deepEqual(b.asks.map((a: any) => a.text), ["goal 0", "goal 1", "goal 2"], "the base frame is not mutated");
  assert.notEqual(out, b);
});

test("`top` present ⇒ it is the COMPLETE set of non-keyed fields — a field that left the frame leaves here too", () => {
  const b = { ...base(), stale: "gone-in-the-next-build" };
  const out = applyFeedDelta(b, { type: "feedDelta", now: 1010, buildId: 2, top: { order: ["TESTSID"], working: [] } });
  assert.deepEqual(out.working, []);
  assert.equal("stale" in out, false);
  assert.equal("sessions" in out, false, "not in top → not in the frame");
  assert.deepEqual(out.asks, b.asks, "keyed fields are never in `top`; they carry over");
  assert.deepEqual(out.ledgers, b.ledgers);
});

test("ledgers upsert by sid; a `ledgers` key in the delta means the client holds a list afterwards", () => {
  const b = { ...base(), ledgers: undefined as any };
  delete (b as any).ledgers;
  const out = applyFeedDelta(b, { type: "feedDelta", ledgers: [], removeLedgers: [] });
  assert.deepEqual(out.ledgers, [], "the Outline pane's 'the build ran' gate reads the key's presence");
  const out2 = applyFeedDelta(base(), { type: "feedDelta",
    ledgers: [{ sid: "TESTSID", name: "web", ledger: { tops: ["x"] }, status: { state: "waiting" } }] });
  assert.equal(out2.ledgers.length, 1); assert.deepEqual(out2.ledgers[0].status, { state: "waiting" });
  const out3 = applyFeedDelta(base(), { type: "feedDelta", ledgers: [], removeLedgers: ["TESTSID"] });
  assert.deepEqual(out3.ledgers, []);
});

test("upsertById keeps order, drops the removed, appends the new", () => {
  assert.deepEqual(upsertById([{ k: "a", v: 1 }, { k: "b", v: 1 }], [{ k: "b", v: 2 }, { k: "c", v: 1 }], ["a"], "k"),
    [{ k: "b", v: 2 }, { k: "c", v: 1 }]);
});

test("a delta-applied frame merges exactly like a pushed full frame", () => {
  const applied = applyFeedDelta(base(), { type: "feedDelta", asks: [card(0, { text: "changed" })] });
  const merged = mergeHostFeeds({ "": applied }, [""]);
  assert.equal(merged.type, "feed");
  assert.equal(merged.asks[0].text, "changed");
  assert.equal(merged.asks.length, 3);
});

test("federation applies deltas onto the LOCAL host's held frame and re-emits; no base → needFullFeed", () => {
  assert.match(FED, /import \{ applyFeedDelta \} from "\.\/feed-delta";/);
  const i = FED.indexOf('if (m && m.type === "feedDelta") {');
  assert.ok(i > 0, "inbound has a feedDelta branch");
  const branch = FED.slice(i, i + 1800);
  assert.match(branch, /const base = host === LOCAL \? this\.perHostFeed\[host\] : null;/, "only the local socket announces, so only it may carry deltas");
  assert.match(branch, /this\.diag\("feedDelta-nobase"/);
  assert.match(branch, /s\(\{ type: "needFullFeed" \}\)/);
  assert.match(branch, /this\.perHostFeed\[host\] = applyFeedDelta\(base, m\);\s*\n\s*this\.perHostFeedAt\[host\] = Date\.now\(\);[^\n]*\n\s*this\.emitMergedFeed\(\);/,
    "applied, its arrival stamped beside it (the pane's clock anchor), re-emitted");
  assert.ok(FED.indexOf('if (m && m.type === "feed") {') < i, "the full-frame branch stays first and unchanged");
});

test("a feedDelta that reaches the pane unapplied is loud and asks for a full frame", () => {
  const i = FEED.indexOf('if (m.type === "feedDelta") {');
  assert.ok(i > 0);
  const branch = FEED.slice(i, i + 900);
  assert.match(branch, /console\.error\(/);
  assert.match(branch, /what: "feedDelta-unapplied"/);
  assert.match(branch, /postMessage\(\{ type: "needFullFeed" \}\)/);
  assert.ok(i < FEED.indexOf('if (m.type === "feed") {'), "checked before the full-frame branch");
});

test("the kernel announces the delta capability on every feed-consumer page's socket, the hold on every pane's, and the wire vocabulary matches", () => {
  assert.match(KERNEL, /FEED_DELTA_CAP = "feedDelta"/);
  assert.match(KERNEL, /READY_GATE_CAP = "readyGate"/);
  // the feed page, the Waiting on you page and (2026-09-05) the Outline page: each loads federation.js ahead of
  // its bundle, and federation applies the deltas — the bundles keep reading whole `feed` frames
  for (const app of ["feed", "waiting", "fleet"]) assert.match(KERNEL, new RegExp(`_shim\\("${app}", v, caps=FEED_DELTA_CAP \\+ "," \\+ READY_GATE_CAP\\)`), app);
  for (const app of ["chat", "timeline"]) assert.match(KERNEL, new RegExp(`_shim\\("${app}", v, caps=READY_GATE_CAP\\)`), app);
  // the delta's keys, as the kernel writes them — the client reads exactly these
  for (const k of ['"asks":[', '"removeAsks":', '"ledgers":[', '"removeLedgers":', '"top":']) assert.ok(KERNEL.includes(k), k);
  assert.match(KERNEL, /_FEED_KEYED = \(\("asks", "itemId"\), \("ledgers", "sid"\)\)/);
  assert.match(KERNEL, /msg\.get\("type"\) == "needFullFeed"/);
});

test("the recency tint is computed client-side from `t` on a live clock; deltas never carry trgb, full frames still do for older bundles", () => {
  assert.equal(/\.trgb\b|trgb[?]?:/.test(FEED), false, "no reader or type of a per-card colour remains — present or absent on the wire, it is ignored");
  assert.ok(KERNEL.includes('"trgb": list(cm.age_rgb('), "full frames keep the tint: an older bundle destructures it unguarded");
  assert.match(KERNEL, /def _strip_trgb\(card\):/);
  assert.match(KERNEL, /cards = \{a\["itemId"\]: json\.dumps\(_strip_trgb\(a\), default=str\)/, "deltas are built from tint-less cards");
  assert.match(KERNEL, /stable\["asks"\] = \[_strip_trgb\(a\) for a in stable\["asks"\]\]/, "…and the dedup signature ignores the tint");
  assert.match(FEED, /applyTint\(card, nowSec\(\) - it\.t\);/);
  assert.match(FEED, /applyTint\(card, nowSec\(\) - g\.t\);/);
  assert.match(FEED, /stampAge\(meta, node\.last, "paren", true, nowSec\(\), relAge, ageTint\);/);
  // the 15s tick moves the wash too — the host no longer reposts for the fade (feed-age.test.ts pins the rest)
  assert.match(FEED, /applyTint\(card, now - it\.t\);/);
  // a colourless card's border falls back to the age ramp — it used to read the removed trgb destructure
  assert.match(FEED, /setCardChannels\(card, \(it\.color && hexToRgb\(it\.color\.bg\)\) \|\| ageRgb\(nowSec\(\) - it\.t\)\);/);
  assert.match(FEED, /setCardChannels\(card, \(g\.color && hexToRgb\(g\.color\.bg\)\) \|\| ageRgb\(nowSec\(\) - g\.t\)\);/);
  // the ramp is the kernel's age_rgb: same stops, log scale, 2 min bright … 96 h dark
  assert.deepEqual(ageRgb(0), ageRgb(120), "clamped below 2 min");
  assert.deepEqual(ageRgb(345600), ageRgb(10 * 345600), "clamped above 96 h");
  assert.notDeepEqual(ageRgb(120), ageRgb(345600));
  assert.deepEqual(ageRgb(345600), [84, 178, 4], "aurora's dark end (v=0 → stops[0]) — the kernel's ramp(0)");
});

// ── the clock anchor travels with the frame ──────────────────────────────────────────────────────────
// The real manager, a stub window (emissions) and a stub clock. federation re-emits the merged feed on a
// view-order write (`storage` / VIEW_ORDER_EVENT → reorder → emitMergedFeed; view-order-wiring.test.ts pins
// the wiring), on every remote host's frame and on a detach — and feed.ts anchors its live clock on the
// frame it is handed. The 2026-09-03 review: anchored on the EMIT, a re-emit after a quiet hour took every
// age and tint back by that hour ("1m ago" → "<1m ago" on a tab drag in another pane; an attached kernel's
// 60 s reposts pinned the clock there). The anchor is now the (now, nowAt) PAIR of the local frame's wire
// arrival, so a re-emit anchors exactly as the arrival did.
function withFeedManager(fn: (fm: FederationManager, emitted: any[], clock: { ms: number }) => void): void {
  const emitted: any[] = [];
  const clock = { ms: 5_000_000 };
  const g: any = globalThis;
  const hadWindow = "window" in g, prevWindow = g.window;
  const hadLS = "localStorage" in g, prevLS = g.localStorage;
  const realNow = Date.now;
  g.window = { dispatchEvent: (ev: any) => { if (ev && ev.data) emitted.push(ev.data); } };
  g.localStorage = { getItem: () => null, setItem: () => {} };
  Date.now = () => clock.ms;
  try {
    fn(new FederationManager(), emitted, clock);
  } finally {
    Date.now = realNow;
    if (hadWindow) g.window = prevWindow; else delete g.window;
    if (hadLS) g.localStorage = prevLS; else delete g.localStorage;
  }
}
const pair = (m: any) => [m.now, m.nowAt];

test("the merged frame's clock anchor is the local frame's (now, nowAt) wire arrival: a re-emit after a quiet hour carries the same pair", () => {
  withFeedManager((fm, emitted, clock) => {
    const T = 1_000_000;
    fm.inbound("", { type: "feed", asks: [card(0)], now: T, buildId: 1 });
    assert.equal(emitted.length, 1);
    assert.deepEqual(pair(emitted[0]), [T, 5_000_000], "stamped with the moment the frame arrived");
    clock.ms += 3_600_000;                       // a quiet hour: the delta path sends the pane nothing
    (fm as any).emitMergedFeed();                // what a view-order write runs (reorder), with no new frame
    assert.equal(emitted.length, 2);
    assert.deepEqual(pair(emitted[1]), [T, 5_000_000], "the re-emit anchors exactly as the arrival did");
    assert.equal(liveNow(emitted[1].now, emitted[1].nowAt, clock.ms), T + 3600, "so the pane's live clock keeps the hour");
    assert.equal(liveNow(emitted[1].now, clock.ms, clock.ms), T, "anchored on the emit it would lose it — the bug");
    assert.deepEqual(emitted[1].asks.map((a: any) => a.itemId), ["TESTSID:g0"], "the same board, unchanged");
  });
});

test("a remote host's frame never moves the local anchor; a local delta re-anchors on its own arrival", () => {
  withFeedManager((fm, emitted, clock) => {
    const T = 1_000_000;
    fm.inbound("", { type: "feed", asks: [card(0)], now: T, buildId: 1 });
    clock.ms += 3_600_000;
    fm.inbound("TESTHOST", { type: "feed", asks: [], now: T + 7200, buildId: 9 });   // an attached kernel's 60 s repost, its clock 2 h ahead
    assert.equal(emitted.length, 2);
    assert.deepEqual(pair(emitted[1]), [T, 5_000_000], "the local pair, untouched by the remote's clock or arrival");
    assert.equal(liveNow(emitted[1].now, emitted[1].nowAt, clock.ms), T + 3600);
    clock.ms += 60_000;
    fm.inbound("", { type: "feedDelta", now: T + 3660, buildId: 2, asks: [card(0, { text: "changed" })] });
    assert.equal(emitted.length, 3);
    assert.deepEqual(pair(emitted[2]), [T + 3660, clock.ms], "new local information: the delta's clock, and when it arrived");
    assert.equal(emitted[2].asks[0].text, "changed");
    clock.ms += 30_000;
    fm.inbound("TESTHOST", { type: "feed", asks: [], now: T + 7300, buildId: 10 });
    assert.deepEqual(pair(emitted[3]), [T + 3660, clock.ms - 30_000], "…and the remote's next repost leaves it there");
  });
});

test("with no local frame yet the pair comes from the newest REMOTE arrival — both halves from one host; no arrivals known → no nowAt", () => {
  withFeedManager((fm, emitted, clock) => {
    fm.inbound("HOSTA", { type: "feed", asks: [], now: 500 });
    clock.ms += 10_000;
    fm.inbound("HOSTB", { type: "feed", asks: [], now: 900 });
    assert.deepEqual(pair(emitted[emitted.length - 1]), [900, 5_010_000], "HOSTB arrived last: its clock with its arrival");
  });
  const perHost = { HOSTA: { type: "feed", now: 500 }, HOSTB: { type: "feed", now: 900 } };
  const older = mergeHostFeeds(perHost, ["", "HOSTA", "HOSTB"], [], [], { HOSTA: 9, HOSTB: 5 });
  assert.deepEqual(pair(older), [500, 9], "the newest ARRIVAL wins, not the largest clock");
  const local = mergeHostFeeds({ "": { type: "feed", now: 7 }, HOSTA: { type: "feed", now: 500 } }, ["", "HOSTA"], [], [], { "": 3, HOSTA: 9 });
  assert.deepEqual(pair(local), [7, 3], "a local frame is the anchor whenever it exists, however old its arrival");
  const bare = mergeHostFeeds({ "": { type: "feed", now: 7 } }, [""]);
  assert.equal(bare.now, 7);
  assert.equal("nowAt" in bare, false, "a caller with no wire (no arrivals) sets none: the pane anchors on its own arrival");
  const none = mergeHostFeeds({ HOSTA: { type: "feed", asks: [] } }, ["", "HOSTA"], [], [], { HOSTA: 9 });
  assert.equal("now" in none, false, "a frame with no clock (an older kernel) anchors nothing");
});

test("federation stamps the arrival beside the frame on both wire paths, drops it with the host, and the merge is handed it", () => {
  assert.match(FED, /private perHostFeedAt: Record<string, number> = \{\};/);
  assert.match(FED, /this\.perHostFeed\[host\] = m;\n\s*this\.perHostFeedAt\[host\] = Date\.now\(\);/, "a full frame's arrival");
  assert.match(FED, /this\.perHostFeed\[host\] = applyFeedDelta\(base, m\);\n\s*this\.perHostFeedAt\[host\] = Date\.now\(\);[^\n]*\n\s*this\.emitMergedFeed\(\);/, "a delta's arrival");
  assert.match(FED, /delete this\.perHostFeed\[host\];\n\s*delete this\.perHostFeedAt\[host\];/, "a detach forgets both");
  assert.match(FED, /mergeHostFeeds\(this\.perHostFeed, this\.hostSeq, this\.view\(\), dead, this\.perHostFeedAt\)/, "every emit carries the arrivals");
  assert.equal((FED.match(/perHostFeedAt\[host\] = Date\.now\(\)/g) || []).length, 2, "stamped on the two wire paths and nowhere else — never on an emit");
});


// ── the Outline pane's path (2026-09-05) ─────────────────────────────────────────────────────────────
// The kernel-served Outline page announces the delta capability too (on full frames alone, one browser's
// Outline client fell 12.7 MB behind and was dropped seven times in a morning). Its bundle (fleet.ts) reads
// `ledgers`, `asks` and `views` off whole `feed` frames and has no delta reader (fleet.test.ts): federation
// applies each delta onto the full frame it holds for the local host and re-emits the merge. So what the
// pane sees is pinned here, through the real manager.
test("a delta's ledger upserts and removals reach the Outline pane as a whole `feed` frame, and `views` carries over from the base", () => {
  withFeedManager((fm, emitted) => {
    fm.inbound("", { type: "feed", asks: [card(0)], now: 1000, buildId: 1, views: { v1: { name: "mine" } },
                     ledgers: [{ sid: "TESTSID", name: "web", ledger: { tops: [] } }, { sid: "TESTSID2", name: "api", ledger: { tops: [] } }] });
    fm.inbound("", { type: "feedDelta", now: 1010, buildId: 2,
                     ledgers: [{ sid: "TESTSID", name: "web", ledger: { tops: ["t1"] } }], removeLedgers: ["TESTSID2"] });
    assert.equal(emitted.length, 2);
    const m = emitted[1];
    assert.equal(m.type, "feed", "the merge re-emits whole frames: the only shape fleet.ts reads");
    assert.deepEqual(m.ledgers.map((l: any) => [l.sid, l.ledger.tops]), [["TESTSID", ["t1"]]], "upserted by sid, the removed one gone");
    assert.deepEqual(m.views, { v1: { name: "mine" } }, "no `top` in the delta ⇒ the base's non-keyed fields carry forward");
    assert.deepEqual(m.asks.map((a: any) => a.itemId), ["TESTSID:g0"], "cards untouched by the delta stay");
    assert.equal(m.buildId, 2);
  });
});

test("a delta with no full frame held asks the local kernel for one (needFullFeed) and emits nothing", () => {
  withFeedManager((fm, emitted) => {
    const sent: any[] = [];
    (globalThis as any).window.__rompLocalSend = (m: any) => sent.push(m);
    fm.inbound("", { type: "feedDelta", now: 1010, buildId: 2, ledgers: [{ sid: "TESTSID", name: "web" }] });
    assert.equal(emitted.length, 0, "nothing to apply onto, nothing emitted — the pane keeps its loader");
    assert.deepEqual(sent.filter((m) => m.type === "needFullFeed"), [{ type: "needFullFeed" }]);
    assert.ok(sent.some((m) => m.type === "clientDiag" && m.what === "feedDelta-nobase"), "…and it says so");
  });
});

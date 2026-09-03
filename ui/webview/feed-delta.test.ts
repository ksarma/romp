// The feed's delta path, client side (2026-09-02): the kernel streams {type:"feedDelta"} frames to the
// local socket once it holds a full frame; federation.ts applies them onto its per-host last full frame
// and re-emits a merged full `feed`, so every downstream consumer keeps seeing whole frames. Pure-function
// tests on applyFeedDelta plus source pins on the wiring (the harness imports no DOM; see feed-dead.test.ts).
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { applyFeedDelta, upsertById } from "./feed-delta";
import { mergeHostFeeds } from "./federation";
import { ageRgb } from "./age-color";

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
  assert.match(branch, /this\.perHostFeed\[host\] = applyFeedDelta\(base, m\);\s*\n\s*this\.emitMergedFeed\(\);/);
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

test("the kernel announces the capability on the feed page's socket only, and the wire vocabulary matches", () => {
  assert.match(KERNEL, /FEED_DELTA_CAP = "feedDelta"/);
  assert.match(KERNEL, /_shim\("feed", v, caps=FEED_DELTA_CAP\)/);
  assert.match(KERNEL, /_shim\("fleet", v\)/); assert.match(KERNEL, /_shim\("chat", v\)/); assert.match(KERNEL, /_shim\("timeline", v\)/);
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
  assert.match(FEED, /card\.style\.background = cardTint\(nowSec\(\) - it\.t\);/);
  assert.match(FEED, /card\.style\.background = cardTint\(nowSec\(\) - g\.t\);/);
  assert.match(FEED, /stampAge\(meta, node\.last, "paren", true, nowSec\(\), relAge, ageTint\);/);
  // the 15s tick moves the wash too — the host no longer reposts for the fade (feed-age.test.ts pins the rest)
  assert.match(FEED, /if \(it\) card\.style\.background = cardTint\(now - it\.t\);/);
  // a colourless card's border falls back to the age ramp — it used to read the removed trgb destructure
  assert.match(FEED, /setCardChannels\(card, \(it\.color && hexToRgb\(it\.color\.bg\)\) \|\| ageRgb\(nowSec\(\) - it\.t\)\);/);
  assert.match(FEED, /setCardChannels\(card, \(g\.color && hexToRgb\(g\.color\.bg\)\) \|\| ageRgb\(nowSec\(\) - g\.t\)\);/);
  // the ramp is the kernel's age_rgb: same stops, log scale, 2 min bright … 96 h dark
  assert.deepEqual(ageRgb(0), ageRgb(120), "clamped below 2 min");
  assert.deepEqual(ageRgb(345600), ageRgb(10 * 345600), "clamped above 96 h");
  assert.notDeepEqual(ageRgb(120), ageRgb(345600));
  assert.deepEqual(ageRgb(345600), [84, 178, 4], "aurora's dark end (v=0 → stops[0]) — the kernel's ramp(0)");
});

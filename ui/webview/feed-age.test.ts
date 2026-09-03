// The feed's live clock and its age refresh (feed-age.ts), RUN: a delta client hears nothing from a quiet
// board (the kernel used to repost the frame every 60 s, so its clock was never more than a minute stale),
// so the pane keeps the clock moving itself and one 15 s pass repaints every stamped age — ask cards, group
// cards, sub-goal rows, an open modal. The 2026-09-03 review found group cards and the modal frozen at the
// age of the last change for hours. Pure functions here, plus source pins on feed.ts's wiring (the feed has
// no DOM harness; see feed-dead.test.ts). Synthetic only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { liveNow, paintAge, refreshAges, stampAge, type AgeEl } from "./feed-age";
import { ageRgb } from "./age-color";

const FEED = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "feed.ts"), "utf8");
// feed.ts's relAge, in shape (feed-relage.test.ts pins the real one); the refresh takes it as a parameter
const rel = (s: number) => s < 60 ? "<1m ago" : s < 3600 ? Math.round(s / 60) + "m ago" : s < 86400 ? Math.round(s / 3600) + "h ago" : Math.round(s / 86400) + "d ago";
const tint = (s: number) => "rgb(" + ageRgb(s).join(",") + ")";
const mk = (): AgeEl => ({ textContent: null, style: { color: "" }, dataset: {} });

test("liveNow is the kernel's clock plus the local time since the payload landed — never the browser's own clock", () => {
  assert.equal(liveNow(1_000_000, 50_000, 50_000), 1_000_000, "at the payload: the payload's now");
  assert.equal(liveNow(1_000_000, 50_000, 65_500), 1_000_015, "15.5 s later: +15 (whole seconds)");
  assert.equal(liveNow(1_000_000, 50_000, 40_000), 1_000_000, "a local clock that went backwards never rewinds it");
  // skew between the kernel's clock and the browser's never enters: only the local clock's DELTAS do
  assert.equal(liveNow(1_000_000, 1_900_000_000_000, 1_900_000_060_000), 1_000_060);
});

test("a quiet board's ages advance: every stamped element repaints from the live clock, tinted ones re-tint", () => {
  const T = 1_000_000, t = T - 240;                         // everything 4 minutes old at the payload
  const cardTime = mk(), groupTime = mk(), treeMeta = mk(), modalAge = mk();
  stampAge(cardTime, t, "plain", false, T, rel, tint);      // an ask card's stamp
  stampAge(groupTime, t, "plain", false, T, rel, tint);     // a group card's stamp
  stampAge(treeMeta, t, "paren", true, T, rel, tint);       // a sub-goal row: "(4m ago)", recency-tinted
  stampAge(modalAge, t, "plain", true, T, rel, tint);       // the modal's age: tinted
  assert.equal(cardTime.textContent, "4m ago"); assert.equal(groupTime.textContent, "4m ago");
  assert.equal(treeMeta.textContent, "(4m ago)"); assert.equal(modalAge.textContent, "4m ago");
  assert.equal(cardTime.style.color, "", "card stamps keep their own colour");
  assert.equal(treeMeta.style.color, tint(240));
  // an hour passes with no payload: the 15 s tick's pass, from the live clock
  const n = refreshAges([cardTime, groupTime, treeMeta, modalAge], T + 3600, rel, tint);
  assert.equal(n, 4, "every stamped element is repainted — group cards and the modal included");
  assert.equal(cardTime.textContent, "1h ago"); assert.equal(groupTime.textContent, "1h ago");
  assert.equal(treeMeta.textContent, "(1h ago)"); assert.equal(modalAge.textContent, "1h ago");
  assert.equal(treeMeta.style.color, tint(3840)); assert.notEqual(treeMeta.style.color, tint(240), "the tint aged");
  assert.equal(modalAge.style.color, tint(3840));
  assert.equal(cardTime.style.color, "", "…and an untinted stamp stays untinted");
});

test("the anchor is the served frame's clock: a frame stamped at the serve gives true ages, a frame carrying its build's clock does not", () => {
  // The kernel serves a connecting pane its CACHED frame, built while some client was last connected — hours
  // earlier after a client-less night — and a quiet board sends a delta client nothing afterwards, so the
  // pane's clock is only as good as the `now` on that one frame. The kernel therefore stamps the served
  // frame with the time of the SERVE (_send_feed_now); this is the arithmetic that stamp keeps honest.
  const built = 1_000_000, serve = built + 10 * 3600, landedMs = 5_000_000;   // a card touched 1 h before the build
  const cardT = built - 3600;
  const freshNow = liveNow(serve, landedMs, landedMs + 300_000);              // stamped at the serve, 5 min later
  assert.equal(rel(freshNow - cardT), "11h ago", "the card is 11 h old and reads so");
  const staleNow = liveNow(built, landedMs, landedMs + 300_000);              // the build's clock, as the pane once got it
  assert.equal(rel(staleNow - cardT), "1h ago", "anchored on the build it would read 1 h old — for the rest of the morning");
});

test("an unstamped element is left alone", () => {
  const plain = mk(); plain.textContent = "Blocked";       // a question node's meta carries no age
  assert.equal(paintAge(plain, 5, rel, tint), false);
  assert.equal(plain.textContent, "Blocked");
  const junk = mk(); junk.dataset.ageT = "not-a-number";
  assert.equal(refreshAges([plain, junk], 5, rel, tint), 0);
});

test("feed.ts reads the clock only through nowSec(), stamps every age-bearing element, and the tick repaints them all", () => {
  assert.match(FEED, /import \{ liveNow, refreshAges, stampAge \} from "\.\/feed-age";/);
  assert.match(FEED, /function nowSec\(\): number \{ return liveNow\(hostNow, hostNowAt, Date\.now\(\)\); \}/);
  assert.match(FEED, /hostNow = typeof m\.now === "number" \? m\.now : Math\.floor\(Date\.now\(\) \/ 1000\);\n\s*hostNowAt = Date\.now\(\);/,
    "the payload's clock is recorded with WHEN it landed");
  assert.equal((FEED.match(/\bhostNow\b/g) || []).length, 3,
    "hostNow is declared, recorded and read by nowSec() — nothing else reads it raw (a raw read is a frozen age)");
  // the stamps: ask card, group card, sub-goal row (parenthesized, tinted), the modal (tinted), the log rows
  assert.match(FEED, /stampAge\(a\._time, it\.t, "plain", false, nowSec\(\), relAge, ageTint\);/);
  assert.match(FEED, /stampAge\(a\._time, g\.t, "plain", false, nowSec\(\), relAge, ageTint\);/);
  assert.match(FEED, /else stampAge\(meta, node\.last, "paren", true, nowSec\(\), relAge, ageTint\);/);
  assert.match(FEED, /stampAge\(ageEl, it\.t, "plain", true, nowSec\(\), relAge, ageTint\);/);
  assert.match(FEED, /stampAge\(ageEl, grp\.t, "plain", true, nowSec\(\), relAge, ageTint\);/);
  assert.match(FEED, /stampAge\(when, rt, "plain", false, nowSec\(\), relAge, ageTint\);/);
  // the wash is recomputed from the live clock at render…
  assert.match(FEED, /card\.style\.background = cardTint\(nowSec\(\) - it\.t\);/);
  assert.match(FEED, /card\.style\.background = cardTint\(nowSec\(\) - g\.t\);/);
  // …and the 15 s tick re-applies it to ask AND group cards, then repaints every stamped age
  const tick = FEED.slice(FEED.indexOf("setInterval(() => {\n  const now = nowSec();"), FEED.indexOf("}, 15000);"));
  assert.ok(tick.length > 0, "the tick reads the live clock");
  assert.match(tick, /for \(const card of askEls\.values\(\)\) \{\s*\n\s*const it = \(card as any\)\._it as AskItem \| undefined;\s*\n\s*if \(it\) card\.style\.background = cardTint\(now - it\.t\);/);
  assert.match(tick, /for \(const card of groupEls\.values\(\)\) \{\s*\n\s*const g = \(card as any\)\._g as AskGroup \| undefined;\s*\n\s*if \(g\) card\.style\.background = cardTint\(now - g\.t\);/);
  assert.match(tick, /refreshAges\(document\.querySelectorAll<HTMLElement>\("\[data-age-t\]"\), now, relAge, ageTint\);/);
});

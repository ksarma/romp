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
import { liveNow, liveRefresher, paintAge, refreshAges, stampAge, type AgeEl } from "./feed-age";
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
  assert.equal(n, 4, "every stamped element is repainted — group cards and the modal included (every label changed)");
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

test("the anchor is a (now, nowAt) pair that travels with the frame: a re-emit after a quiet hour reads the same live clock as the arrival", () => {
  // federation re-emits the merged frame on a view-order write, on every remote host's frame and on a detach,
  // and the pane sets its clock from whatever frame it is handed. The pair pins the anchor to the WIRE arrival:
  // the same stored frame, re-emitted an hour later, anchors identically. Anchored on the emit instead, every
  // age and tint went back by the quiet period (the 2026-09-03 review: "1m ago" → "<1m ago" on a tab drag).
  const T = 1_000_000, arrivedMs = 5_000_000, hourLater = arrivedMs + 3_600_000;
  const anchor = (m: { now: number; nowAt?: number }, handledMs: number) =>
    liveNow(m.now, typeof m.nowAt === "number" ? m.nowAt : handledMs, handledMs);   // feed.ts's rule, pinned below
  assert.equal(anchor({ now: T, nowAt: arrivedMs }, arrivedMs), T, "at the arrival");
  assert.equal(anchor({ now: T, nowAt: arrivedMs }, hourLater), T + 3600, "the re-emit keeps the hour");
  assert.equal(anchor({ now: T }, hourLater), T, "a frame with no pair anchors on the handling — the old rule, and the bug on a re-emit");
});

test("an unstamped element is left alone", () => {
  const plain = mk(); plain.textContent = "Blocked";       // a question node's meta carries no age
  assert.equal(paintAge(plain, 5, rel, tint), false);
  assert.equal(plain.textContent, "Blocked");
  const junk = mk(); junk.dataset.ageT = "not-a-number";
  assert.equal(refreshAges([plain, junk], 5, rel, tint), 0);
});

test("a second pass at the same `now` writes NOTHING, and a pass across a minute boundary writes exactly the labels that crossed it", () => {
  // Blink treats an identical textContent write as a real Text-node replacement once the document has created
  // a MutationObserver (gear.js does at boot), so the compare is what keeps a quiet 15 s pass off the layout.
  const T = 1_000_000;
  const writes = (init: number) => {
    let n = 0;
    const e = { _text: "" as string | null, style: { color: "" }, dataset: {} as AgeEl["dataset"],
      get textContent() { return this._text; }, set textContent(v: string | null) { this._text = v; n++; } };
    stampAge(e, T - init, "plain", true, T, rel, tint);
    return { e, count: () => n };
  };
  const a = writes(100), b = writes(150), c = writes(4 * 60);   // "2m ago", "3m ago" (rounded), "4m ago"
  const c0 = a.count() + b.count() + c.count();
  assert.equal(c0, 3, "the stamp paints once each");
  assert.equal(refreshAges([a.e, b.e, c.e], T, rel, tint), 0, "same now: nothing rewritten");
  assert.equal(a.count() + b.count() + c.count(), c0, "…and no textContent setter ran");
  assert.equal(a.e.style.color, tint(100));
  // 20 s later: a (120 s → "2m ago") and c (260 s → "4m ago") read the same; b (170 s) rounds to "3m ago" still — but
  // every tinted colour moves on the log ramp, so the tinted labels rewrite their colour, not their text
  const nText = { a: a.count(), b: b.count(), c: c.count() };
  refreshAges([a.e, b.e, c.e], T + 20, rel, tint);
  assert.deepEqual({ a: a.count(), b: b.count(), c: c.count() }, nText, "no text changed: no textContent write");
  // untinted stamps (card time stamps) have only their text: a pass that moves no label writes nothing at all
  let wrote = 0;
  const plain = { _text: "" as string | null, style: { color: "" }, dataset: {} as AgeEl["dataset"],
    get textContent() { return this._text; }, set textContent(v: string | null) { this._text = v; wrote++; } };
  stampAge(plain, T - 100, "plain", false, T, rel, tint);          // "2m ago"
  assert.equal(refreshAges([plain], T + 20, rel, tint), 0);          // 120 s: still "2m ago"
  assert.equal(refreshAges([plain], T + 40, rel, tint), 0);          // 140 s: "2m ago"
  assert.equal(refreshAges([plain], T + 50, rel, tint), 1, "150 s rounds to 3m: the one label that crossed is rewritten");
  assert.equal(plain.textContent, "3m ago");
  assert.equal(wrote, 2, "one write at the stamp, one at the crossing");
});

test("a running DURATION is a stamp too (fmt 'dur'): workingFor's minutes-then-hours vocabulary, moving with the clock", () => {
  const T = 1_000_000;
  const d = mk();
  stampAge(d, T - 42 * 60, "dur", false, T, rel, tint);
  assert.equal(d.textContent, "42m", "the awaiting box's / narration's duration, bare — the caller places the separator");
  refreshAges([d], T + 18 * 60, rel, tint);
  assert.equal(d.textContent, "1h 0m", "past sixty minutes it splits out the hours, as workingFor always did");
  assert.equal(refreshAges([d], T + 18 * 60 + 30, rel, tint), 0, "within the same minute nothing is written");
  assert.equal(d.style.color, "", "untinted");
});

test("liveRefresher: a hidden pane skips the pass and catches up exactly once when shown; an ordinary resize runs nothing", () => {
  let hidden = false, passes = 0;
  const live = liveRefresher({ hidden: () => hidden, pass: () => { passes++; } });
  live.tick(); assert.equal(passes, 1, "visible: the tick runs the pass");
  live.catchUp(); assert.equal(passes, 1, "nothing owed: a resize or visibility flip runs nothing");
  hidden = true;
  live.tick(); live.tick(); assert.equal(passes, 1, "hidden: two ticks, no pass");
  live.catchUp(); assert.equal(passes, 1, "still hidden: the catch-up waits");
  hidden = false;
  live.catchUp(); assert.equal(passes, 2, "shown: ONE catch-up pass for the two skipped ticks");
  live.catchUp(); assert.equal(passes, 2, "…and only one");
  live.tick(); assert.equal(passes, 3, "the cadence resumes");
});

test("feed.ts reads the clock only through nowSec(), stamps every age-bearing element, and the live pass repaints them all", () => {
  assert.match(FEED, /import \{ liveNow, liveRefresher, refreshAges, stampAge \} from "\.\/feed-age";/);
  assert.match(FEED, /function nowSec\(\): number \{ return liveNow\(hostNow, hostNowAt, Date\.now\(\)\); \}/);
  assert.match(FEED, /if \(typeof m\.now === "number"\) \{\n\s*hostNow = m\.now;\n\s*hostNowAt = typeof m\.nowAt === "number" \? m\.nowAt : Date\.now\(\);/,
    "the payload's clock is recorded with when THAT FRAME ARRIVED (federation's `nowAt`) — never with when this handler ran");
  assert.equal((FEED.match(/hostNowAt = Date\.now\(\)/g) || []).length, 2,
    "the bare arrival time anchors only a frame with no `nowAt` (no federation layer) or no `now` at all (an older kernel)");
  assert.equal((FEED.match(/\bhostNow\b/g) || []).length, 4,
    "hostNow is declared, recorded (with and without a kernel clock) and read by nowSec() — nothing else reads it raw (a raw read is a frozen age)");
  // the stamps: ask card, group card, sub-goal row (parenthesized, tinted), the modal (tinted), the log rows
  assert.match(FEED, /stampAge\(a\._time, it\.t, "plain", false, nowSec\(\), relAge, ageTint\);/);
  assert.match(FEED, /stampAge\(a\._time, g\.t, "plain", false, nowSec\(\), relAge, ageTint\);/);
  assert.match(FEED, /else stampAge\(meta, node\.last, "paren", true, nowSec\(\), relAge, ageTint\);/);
  assert.match(FEED, /stampAge\(ageEl, it\.t, "plain", true, nowSec\(\), relAge, ageTint\);/);
  assert.match(FEED, /stampAge\(ageEl, grp\.t, "plain", true, nowSec\(\), relAge, ageTint\);/);
  assert.match(FEED, /stampAge\(when, rt, "plain", false, nowSec\(\), relAge, ageTint\);/);
  // …and the collapsed history gist's "· Xm ago": one text with the age baked in froze at render time while
  // the sub-goal row above it kept counting (the 2026-09-03 review)
  assert.match(FEED, /gist\.textContent = \(opened \? "▾ " : "▸ "\) \+ logPhrase\(last\) \+ " · ";\n/);
  assert.match(FEED, /stampAge\(gistAge, logRowT\(last\), "plain", false, nowSec\(\), relAge, ageTint\);/);
  assert.doesNotMatch(FEED, /logPhrase\(last\) \+ " · " \+ relAge\(/, "the gist's age is no longer built into a text the tick cannot reach");
  // the running DURATIONS (2026-09-06): the awaiting box, the Awaiting-task pill, the waiting-on chip, the
  // working narration and the per-paragraph ages are stamped too — the per-card update gate repaints a card
  // only when its inputs change, so a duration baked into a caption would freeze on a card never re-sent
  assert.match(FEED, /function durSpan\(since: number\): HTMLElement \{\n\s*const d = el\("span", "fask-dur"\);\n\s*stampAge\(d, since, "dur", false, nowSec\(\), relAge, ageTint\);/);
  assert.doesNotMatch(FEED, /, Date\.now\(\) \/ 1000\)/, "no elapsed label reads the browser clock any more (the clock anchors themselves still do, feed-age.ts liveNow)");
  assert.match(FEED, /if \(bp!\[i\]\.since\) stampAge\(age, bp!\[i\]\.since, "plain", false, nowS, relAge, ageTint\);/);
  // the wash is recomputed from the live clock at render, through the one compare-then-write tint helper…
  assert.match(FEED, /function applyTint\(card: HTMLElement, ageSecs: number\): void \{\n\s*const s = cardTint\(ageSecs\);\n\s*if \(\(card as any\)\._tint === s\) return;/);
  assert.match(FEED, /applyTint\(card, nowSec\(\) - it\.t\);/);
  assert.match(FEED, /applyTint\(card, nowSec\(\) - g\.t\);/);
  // …and the 15 s live pass re-applies it to ask AND group cards, then repaints every stamped age, writing
  // only what changed, through the shared visibility gate
  const pass = FEED.slice(FEED.indexOf("function livePass(): void {"), FEED.indexOf("const paneHidden = () =>"));
  assert.ok(pass.length > 0, "the live pass exists");
  assert.match(pass, /const now = nowSec\(\);/);
  assert.match(pass, /for \(const card of askEls\.values\(\)\) \{\s*\n\s*const it = \(card as any\)\._it as AskItem \| undefined;\s*\n\s*if \(!it\) continue;\s*\n\s*applyTint\(card, now - it\.t\);/);
  assert.match(pass, /for \(const card of groupEls\.values\(\)\) \{\s*\n\s*const g = \(card as any\)\._g as AskGroup \| undefined;\s*\n\s*if \(g\) applyTint\(card, now - g\.t\);/);
  assert.match(pass, /refreshAges\(document\.querySelectorAll<HTMLElement>\("\[data-age-t\]"\), now, relAge, ageTint\);/);
  assert.match(FEED, /const paneHidden = \(\) => document\.hidden \|\| window\.innerWidth === 0 \|\| window\.innerHeight === 0;\n/);
  assert.match(FEED, /const live = liveRefresher\(\{ hidden: paneHidden, pass: livePass \}\);\nsetInterval\(live\.tick, 15000\);\ndocument\.addEventListener\("visibilitychange", live\.catchUp\);\nwindow\.addEventListener\("resize", live\.catchUp\);/);
});

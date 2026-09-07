// Feed cards FLY to their new column when status changes (the user 2026-06-27), instead of teleporting. Cards
// are reused nodes reconcileCol MOVES between columns, so FLIP works: record rect+column before the move, then
// invert+play after. A column-CROSSER rides the BACK layer (z-index:-1 in the #feed-cols stacking context) so it
// never passes over other cards; a card that STAYED in a column but shifted (because a sibling left) glides IN
// PLACE so the column reflows smoothly instead of snapping (the user 2026-06-29). Source pins (no jsdom).
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const FEED = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "feed.ts"), "utf8");
const CSS = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "feed.css"), "utf8");

test("render() captures rects BEFORE the reconcile and flies changed cards AFTER", () => {
  // capture must precede the column reconciles…
  // …over the columns whose planned key sequence differs from the DOM's (feed-card-gate.ts sameKeySeq): a
  // column where nothing enters, leaves or changes place has nothing that can glide, so its rects go unread
  assert.match(FEED, /const differing = FLY_COLS\.filter\(\(k\) => !sameKeySeq\(childKeys\(cols\[k\]\), buckets\[k\]\.map\(\(e\) => entryKey\(e, cols\[k\]\)\)\)\);\n\s*const flipCols = differing\.length && \(stackForced \|\| gprefs\.stacked\) \? FLY_COLS : differing;\n\s*const flipFirst = captureCardRects\(cols, flipCols\);[\s\S]*?reconcileCol\(cols\.asks/,
    "…and in the stacked layout a move anywhere reads every column: the sections below the move all shift");
  // …and the fly runs after the DOM (and scroll) settle (the identity-alias step sits just before it)
  assert.match(FEED, /list\.scrollTop = prevScroll;[\s\S]*?\/\/ FLIP step 2[\s\S]*?flyColumnChanges\(flipFirst, cols, flipCols\);/);
});

test("FLIP-across-identity: a new-key card aliases to its predecessor's rect so it slides, not pops", () => {
  // each render maps goal itemId → covering card key; a card whose key is NEW borrows its predecessor's First rect
  assert.match(FEED, /const curItemKey = new Map<string, string>\(\);/);
  assert.match(FEED, /coverInto\("a:" \+ e\.ask\.itemId, \[e\.ask\.itemId, \.\.\.\(e\.ask\.tree \|\| \[\]\)\.map\(\(n\) => n\.id\)\]\)/);
  assert.match(FEED, /const prevKey = prevItemKey\.get\(itemId\);/);
  assert.match(FEED, /if \(prevKey && prevKey !== curKey && flipFirst\.has\(prevKey\)\) flipFirst\.set\(curKey, flipFirst\.get\(prevKey\)!\);/);
  assert.match(FEED, /prevItemKey = curItemKey;/);   // remembered for next render
});

test("captureCardRects records each card's rect + column", () => {
  assert.match(FEED, /function captureCardRects\(/);
  assert.match(FEED, /m\.set\(c\.dataset\.key, \{ rect: c\.getBoundingClientRect\(\), col: colEl\.id \}\)/);
});

test("flyColumnChanges FLIPs any moved card (not new cards / non-movers); only crossers ride the back layer", () => {
  assert.match(FEED, /function flyColumnChanges\(/);
  assert.match(FEED, /if \(!prev\) continue;/);                               // brand-new card → no FLIP
  assert.match(FEED, /if \(!dx && !dy\) continue;/);                          // no real move → skip
  // staying in the same column NO LONGER aborts — an in-column shifter must glide too (the user 2026-06-29)
  assert.doesNotMatch(FEED, /prev\.col === colEl\.id\) continue/);
  // a column-crosser gets the back layer; an in-column shifter glides in normal flow
  assert.match(FEED, /moves\.push\(\{ c, dx, dy, crossed: prev\.col !== colEl\.id \}\);/);
  assert.match(FEED, /if \(crossed\) c\.classList\.add\("fitem-flying"\);/);
  // every Last rect is READ before any transform is WRITTEN: a transform write dirties layout, so the old
  // per-card read/write interleave forced a layout per shifted card (about 60 per delta, measured)
  const fly = FEED.slice(FEED.indexOf("function flyColumnChanges("), FEED.indexOf("// ── Absorb:"));
  const at = (s: string) => { const i = fly.indexOf(s); assert.ok(i >= 0, "present: " + s); return i; };
  assert.ok(at("moves.push(") < at("// WRITE phase") && at("// WRITE phase") < at("c.style.transform ="), "every read (into `moves`) precedes the first write");
  assert.equal((fly.match(/getBoundingClientRect/g) || []).length, 1, "one read per card, all in the read phase");
  // a target with a zero rect (its column folded to the header) gets no fly: nothing runs a transition on a
  // display:none element, so the fly would never end and the card would keep pointer-events:none (2026-09-06)
  assert.match(fly, /if \(!now\.width && !now\.height\) continue;/);
  // …and a fly that does start ends on end OR cancel, with a backstop, never leaving the class behind
  assert.match(fly, /c\.addEventListener\("transitionend", done\);\n\s*c\.addEventListener\("transitioncancel", done\);\n\s*window\.setTimeout\(done, 650\);/);
});

test("FLIP: invert to the old spot instantly, then release with a transition (two rAFs)", () => {
  assert.match(FEED, /c\.style\.transition = "none";\s*\n\s*c\.style\.transform = `translate\(\$\{dx\}px, \$\{dy\}px\)`;/);
  assert.match(FEED, /requestAnimationFrame\(\(\) => requestAnimationFrame\(\(\) => \{[\s\S]*?c\.style\.transform = "translate\(0, 0\)";/);
  // cleans up on transitionend so the card returns to normal flow + stacking; the back-layer class comes off
  // whichever fly added it (a superseded crossing fly leaves it to the fly that replaced it — 2026-09-06)
  assert.match(FEED, /ev\.propertyName !== "transform"/);
  assert.match(FEED, /c\.classList\.remove\("fitem-flying"\);\s*\/\/ whichever fly added it/);
  // ONE fly owns an element at a time: a per-element token makes a superseded fly's end/cancel/backstop a
  // no-op, and `played` makes a fly ignore the cancel of the transition its own Invert interrupted
  assert.match(FEED, /const mine = \+\+flySeq;\n\s*\(c as any\)\._flySeq = mine;/);
  assert.match(FEED, /if \(ev && \(ev\.propertyName !== "transform" \|\| !played\)\) return;/);
  assert.match(FEED, /if \(\(c as any\)\._flySeq !== mine\) return;/);
  assert.match(FEED, /if \(flown \|\| \(c as any\)\._flySeq !== mine\) return;\n\s*played = true;/);
});

test("respects prefers-reduced-motion", () => {
  assert.match(FEED, /matchMedia\("\(prefers-reduced-motion: reduce\)"\)\.matches\) return;/);
});

test("the flying card sits in the BACK layer, and #feed-cols is the stacking context that makes that work", () => {
  assert.match(CSS, /\.feed-cols \{[^}]*position: relative; z-index: 0;/);
  assert.match(CSS, /\.fitem-flying \{ position: relative; z-index: -1; pointer-events: none; will-change: transform; \}/);
});

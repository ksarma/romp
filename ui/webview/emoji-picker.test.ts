// The tab menu's emoji picker (2026-09-07): the pure half runs for real here: the search filter, the
// Recent row's storage, the section list the grid draws, and the keyboard model. Synthetic categories
// keep the assertions independent of the curated list's exact contents (emoji-data.test.ts checks that
// list's shape); the last test touches the real data only for the seam the dialog relies on.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { EMOJI_GRID_COLS, EMOJI_RECENT_KEY, EMOJI_RECENT_MAX, emojiName, filterEmoji, gridSections,
         moveInGrid, parseRecentEmoji, rememberEmoji } from "./emoji-picker";
import type { EmojiCategory } from "./emoji-data";
import { EMOJI_CATEGORIES } from "./emoji-data";

const MOON = "\u{1F319}", SUN = "\u{2600}\u{FE0F}", ROCKET = "\u{1F680}", CAT = "\u{1F431}", DOG = "\u{1F436}";
const CATS: EmojiCategory[] = [
  { id: "animals", label: "Animals & nature", icon: CAT, items: [
    [CAT, "cat face", "pet kitten"],
    [DOG, "dog face", "pet puppy"],
    [MOON, "crescent moon", "night sky"],
    [SUN, "sun", "sunny weather"],
  ] },
  { id: "travel", label: "Travel & places", icon: ROCKET, items: [
    [ROCKET, "rocket", "launch space"],
    ["\u{1F697}", "automobile", "car red"],
    ["\u{1F30C}", "milky way", "night galaxy space"],
  ] },
];

// ── the filter ──

test("the filter matches word prefixes of the name, is case-insensitive, and an empty query matches nothing", () => {
  assert.deepEqual(filterEmoji("moo", CATS).map((e) => e[0]), [MOON]);
  assert.deepEqual(filterEmoji("MOON", CATS).map((e) => e[0]), [MOON], "case does not matter");
  assert.deepEqual(filterEmoji("  Cat  ", CATS).map((e) => e[0]), [CAT], "surrounding whitespace is trimmed");
  assert.deepEqual(filterEmoji("", CATS), [], "an empty query is the categories, not a match list");
  assert.deepEqual(filterEmoji("   ", CATS), []);
  assert.deepEqual(filterEmoji("zebra", CATS), [], "no match is an empty list, never a throw");
});

test("keywords match too, ranked after name hits; every typed word must match somewhere", () => {
  // "night" is a keyword on the moon and on the milky way: both come back, in category order
  assert.deepEqual(filterEmoji("night", CATS).map((e) => e[0]), [MOON, "\u{1F30C}"]);
  // a name hit outranks a keyword hit: "sun" is the sun's name and only a keyword-prefix ("sunny") on nothing else
  assert.deepEqual(filterEmoji("space", CATS).map((e) => e[0]), [ROCKET, "\u{1F30C}"]);
  // the name whose FIRST word starts with the query leads one whose later word does
  assert.deepEqual(filterEmoji("face", CATS).map((e) => e[1]), ["cat face", "dog face"]);
  assert.deepEqual(filterEmoji("dog fa", CATS).map((e) => e[0]), [DOG], "two words: both must match");
  assert.deepEqual(filterEmoji("dog rocket", CATS), [], "a word that matches nothing on the entry excludes it");
  // a word in the middle of a name is found by its own prefix, not by a substring of another word
  assert.deepEqual(filterEmoji("oon", CATS), [], "prefixes, not substrings");
});

test("pasting an emoji into the search finds its own entry", () => {
  assert.deepEqual(filterEmoji(MOON, CATS).map((e) => e[1]), ["crescent moon"]);
});

// ── the Recent row ──

test("recents: most recent first, a re-pick moves to the front, capped at 16, under a namespaced key", () => {
  assert.equal(EMOJI_RECENT_KEY, "romp:emoji-recent");
  assert.equal(EMOJI_RECENT_MAX, 16);
  let list: string[] = [];
  list = rememberEmoji(list, MOON);
  list = rememberEmoji(list, ROCKET);
  assert.deepEqual(list, [ROCKET, MOON], "the latest pick leads");
  list = rememberEmoji(list, MOON);
  assert.deepEqual(list, [MOON, ROCKET], "picking again moves it up, no duplicate");
  for (let i = 0; i < 40; i++) list = rememberEmoji(list, String.fromCodePoint(0x1F400 + i));
  assert.equal(list.length, 16, "capped");
  assert.equal(list[0], String.fromCodePoint(0x1F400 + 39), "the newest survives the cap");
  assert.ok(!list.includes(MOON), "the oldest fall off the end");
  assert.deepEqual(rememberEmoji([MOON], ""), [MOON], "an empty value (a clear) is not a recent");
});

test("the stored list is parsed tolerantly: junk costs the row, never the dialog", () => {
  assert.deepEqual(parseRecentEmoji(null), []);
  assert.deepEqual(parseRecentEmoji(""), []);
  assert.deepEqual(parseRecentEmoji("not json"), []);
  assert.deepEqual(parseRecentEmoji('{"a":1}'), [], "not an array");
  assert.deepEqual(parseRecentEmoji(JSON.stringify([MOON, 7, "", null, ROCKET, MOON])), [MOON, ROCKET],
                   "non-strings, empties and duplicates are dropped");
  const many = Array.from({ length: 30 }, (_, i) => String.fromCodePoint(0x1F400 + i));
  assert.equal(parseRecentEmoji(JSON.stringify(many)).length, 16, "an over-long stored list is capped on read");
  // round trip: what rememberEmoji builds, parseRecentEmoji reads back unchanged
  const built = rememberEmoji(rememberEmoji([], MOON), ROCKET);
  assert.deepEqual(parseRecentEmoji(JSON.stringify(built)), built);
});

// ── the sections the grid draws ──

test("no query: the Recent row (when there is one) leads the categories; a query: one Results section", () => {
  const plain = gridSections("", [], CATS);
  assert.deepEqual(plain.map((s) => s.id), ["animals", "travel"], "no recents, no Recent row");
  const withRecent = gridSections("", [ROCKET, "\u{1F984}"], CATS);
  assert.deepEqual(withRecent.map((s) => s.id), ["recent", "animals", "travel"]);
  assert.equal(withRecent[0].label, "Recent");
  assert.deepEqual(withRecent[0].cells.map((c) => c[0]), [ROCKET, "\u{1F984}"], "in stored order");
  assert.equal(withRecent[0].cells[0][1], "rocket", "a known recent carries its curated name");
  assert.equal(withRecent[0].cells[1][1], "\u{1F984}", "an unknown one (typed or pasted, accepted) is its own name");
  const searched = gridSections("night", [ROCKET], CATS);
  assert.deepEqual(searched.map((s) => s.id), ["results"], "searching hides the Recent row and the categories");
  assert.deepEqual(searched[0].cells.map((c) => c[0]), [MOON, "\u{1F30C}"]);
  const none = gridSections("zebra", [ROCKET], CATS);
  assert.equal(none.length, 1);
  assert.equal(none[0].cells.length, 0, "a fruitless search is an EMPTY Results section, which the dialog labels");
  assert.equal(emojiName(MOON, CATS), "crescent moon");
  assert.equal(emojiName("\u{1F984}", CATS), undefined);
});

// ── the keyboard model ──

test("arrows move within a row and across row ends; the grid's edges hold", () => {
  const L = [10];   // one section, 8 per row: rows of 8 and 2
  assert.deepEqual(moveInGrid(L, { section: 0, index: 0 }, "ArrowRight"), { section: 0, index: 1 });
  assert.deepEqual(moveInGrid(L, { section: 0, index: 7 }, "ArrowRight"), { section: 0, index: 8 }, "the row's end flows onto the next row");
  assert.deepEqual(moveInGrid(L, { section: 0, index: 8 }, "ArrowLeft"), { section: 0, index: 7 });
  assert.deepEqual(moveInGrid(L, { section: 0, index: 0 }, "ArrowLeft"), { section: 0, index: 0 }, "the first cell holds");
  assert.deepEqual(moveInGrid(L, { section: 0, index: 9 }, "ArrowRight"), { section: 0, index: 9 }, "the last cell holds");
  assert.deepEqual(moveInGrid(L, { section: 0, index: 1 }, "ArrowDown"), { section: 0, index: 9 });
  assert.deepEqual(moveInGrid(L, { section: 0, index: 5 }, "ArrowDown"), { section: 0, index: 9 }, "down onto a short row lands on its last cell");
  assert.deepEqual(moveInGrid(L, { section: 0, index: 9 }, "ArrowUp"), { section: 0, index: 1 });
  assert.deepEqual(moveInGrid(L, { section: 0, index: 3 }, "ArrowUp"), { section: 0, index: 3 }, "the top row holds");
  assert.deepEqual(moveInGrid(L, { section: 0, index: 9 }, "ArrowDown"), { section: 0, index: 9 }, "the bottom holds");
  assert.deepEqual(moveInGrid(L, { section: 0, index: 4 }, "Home"), { section: 0, index: 0 });
  assert.deepEqual(moveInGrid(L, { section: 0, index: 4 }, "End"), { section: 0, index: 9 });
  assert.equal(EMOJI_GRID_COLS, 8);
});

test("arrows cross category boundaries: right off a section's last cell, down and up between sections, keeping the column", () => {
  const L = [3, 20, 0, 5];   // Recent (3), a category of 20 (rows 8, 8, 4), an EMPTY section, a category of 5
  assert.deepEqual(moveInGrid(L, { section: 0, index: 2 }, "ArrowRight"), { section: 1, index: 0 });
  assert.deepEqual(moveInGrid(L, { section: 1, index: 0 }, "ArrowLeft"), { section: 0, index: 2 });
  assert.deepEqual(moveInGrid(L, { section: 0, index: 1 }, "ArrowDown"), { section: 1, index: 1 }, "down from the Recent row keeps the column");
  assert.deepEqual(moveInGrid(L, { section: 1, index: 1 }, "ArrowUp"), { section: 0, index: 1 }, "and back up");
  assert.deepEqual(moveInGrid(L, { section: 1, index: 6 }, "ArrowUp"), { section: 0, index: 2 }, "up onto a shorter row clamps to its last cell");
  assert.deepEqual(moveInGrid(L, { section: 1, index: 12 }, "ArrowDown"), { section: 1, index: 19 }, "down from a row above the last, onto a slot the short last row lacks, reaches the section's last cell first");
  assert.deepEqual(moveInGrid(L, { section: 1, index: 19 }, "ArrowDown"), { section: 3, index: 3 }, "then crosses, skipping the empty section, keeping the column");
  assert.deepEqual(moveInGrid(L, { section: 1, index: 17 }, "ArrowDown"), { section: 3, index: 1 }, "down from the last row crosses at once, keeping the column");
  assert.deepEqual(moveInGrid(L, { section: 1, index: 19 }, "ArrowRight"), { section: 3, index: 0 });
  assert.deepEqual(moveInGrid(L, { section: 3, index: 0 }, "ArrowLeft"), { section: 1, index: 19 });
  assert.deepEqual(moveInGrid(L, { section: 3, index: 4 }, "ArrowUp"), { section: 1, index: 19 }, "up from column 4 onto a last row of 4 clamps to its last cell (index 19, column 3)");
  assert.deepEqual(moveInGrid(L, { section: 3, index: 2 }, "ArrowUp"), { section: 1, index: 18 }, "up keeps the column when the row above has it");
  assert.deepEqual(moveInGrid(L, { section: 3, index: 4 }, "ArrowDown"), { section: 3, index: 4 }, "the grid's bottom holds");
  assert.deepEqual(moveInGrid(L, { section: 3, index: 2 }, "Home"), { section: 0, index: 0 });
  assert.deepEqual(moveInGrid(L, { section: 0, index: 0 }, "End"), { section: 3, index: 4 });
  // a grid whose first section is empty (nothing recent, or a fruitless search) still has a Home
  assert.deepEqual(moveInGrid([0, 4], { section: 1, index: 3 }, "Home"), { section: 1, index: 0 });
  assert.deepEqual(moveInGrid([0], { section: 0, index: 0 }, "ArrowDown"), { section: 0, index: 0 }, "an empty grid holds");
});

test("Enter, Space and Escape are not grid moves: the model returns null so the button's own activation and the dialog's closer handle them", () => {
  for (const k of ["Enter", " ", "Escape", "Tab", "a"]) assert.equal(moveInGrid([10], { section: 0, index: 2 }, k), null, k);
});

// ── the real list, at the seam the dialog uses ──

test("the curated list answers a plain search and the category ids the strip jumps to are the section ids", () => {
  const hits = filterEmoji("moon");
  assert.ok(hits.length > 0, "some moon");
  assert.ok(hits.every((e) => /moon/.test(e[1] + " " + e[2])), "every hit says moon somewhere");
  const secs = gridSections("", []);
  assert.deepEqual(secs.map((s) => s.id), EMOJI_CATEGORIES.map((c) => c.id), "one section per category, same ids, same order");
  assert.ok(secs.every((s) => s.cells.length > 0), "no category draws empty");
});

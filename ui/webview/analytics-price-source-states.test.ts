// The Token usage modal's price-source line, the states review round 1 (2026-09-20) found unsaid or missaid, run
// for real through the pure formatter gear.js exports (raPriceNote), beside analytics-price-source.test.ts (the
// wording's base cases, the node and the wiring). The kernel's block (_price_feed_status) carries more than a
// source and a reason: `fetchedAt` and `lastError` outlive the fetch that set them, `rows` counts the built-in ids
// the feed matched and `known` how many the table holds, and `off` is the switch as read now. Each pin here is a
// state the recorded blocks can hold, worded so it is true when shown:
// - a fetch in flight is said as one, never as "nothing fetched yet": after a landed-empty or failed fetch the
//   kernel's re-attempt reads inflight with fetchedAt or lastError set, and "nothing fetched" would be false;
// - the feed's rows keep serving under the switch or after a failed refresh (traffic stops, data does not), and the
//   line says which, where it used to say "live feed, fetched N hours ago" alone;
// - a feed that matched some of the table's ids prices those and no more, and the line says so instead of calling
//   the whole table live; a block without `known` (an older kernel) is the plain line;
// - a ROMP_PRICE_FEED value that is neither off nor unset leaves the feed on (only off turns it off), and the line
//   says so on either source from the kernel's boolean `unrecognised`, naming the variable and never the value (the
//   review of PR 878: such a value read the same as an unset variable on every surface, and the fetch went out);
// - rows of model-prices.json the kernel could not read are skipped alone and the rest of the file applies (that
//   review's re-ruling, 2026-09-21: the round's shape voided every row after a bad one, a reach that depended on the
//   row's position), and the line says how many from the kernel's count `overrideRowsRejected`, last, after the
//   override count, and never a key (the block rides the auth-exempt /version; the kernel's log names each row once);
// - a model-prices.json the kernel could not read as a JSON object is ignored whole, and the line says so from the
//   kernel's class `overrideFault` ('file'), in the skipped rows' slot and as fixed text (the second round of that
//   review: the line worded the skipped rows and never the whole-file fault, so a file discarded whole read as a clean
//   one); 'row' keeps the count clause, and any other value words nothing;
// - the fetch age is the shell's one age helper's words (api-health-merge.ts agoWords: now under 45 s, then rounded
//   minutes, rounded hours under 24 h, rounded days), so the line says 30 days ago where the API-health popup does
//   (that round: a copy of the helper here counted hours without end and said just now where the popup says now).
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { agoWords } from "./api-health-merge";

const gear = require("./gear.js");
const note = (pf: unknown): string => {
  assert.equal(typeof gear.raPriceNote, "function", "gear.js exports raPriceNote beside initGear");
  return gear.raPriceNote(pf);
};

test("a fetch in flight is worded as one, apart from nothing fetched yet, so a re-attempt never says nothing was fetched", () => {
  assert.equal(note({ off: false, source: "defaults", reason: "inflight", fetchedAt: null, ageS: null, lastError: null, rows: 0 }),
    "prices: built-in defaults; fetching the feed now", "the first open: the payload is built before the fetch it started lands");
  assert.equal(note({ source: "defaults", reason: "unfetched" }), "prices: built-in defaults; nothing fetched from the feed yet",
    "no attempt this kernel life (reachable on /version before the first open)");
  // the kernel's re-attempt after a fetch that landed and matched nothing: fetchedAt set, cache empty, a worker parked
  const afterEmpty = note({ off: false, source: "defaults", reason: "inflight", fetchedAt: 1_781_100_000, ageS: 21_600, lastError: null, rows: 0 });
  assert.equal(afterEmpty, "prices: built-in defaults; fetching the feed now");
  assert.ok(!afterEmpty.includes("nothing fetched"), "a fetch landed six hours ago: 'nothing fetched' would be false");
  // the kernel's re-attempt after a failed fetch: lastError set, a worker parked
  const afterFailed = note({ off: false, source: "defaults", reason: "inflight", fetchedAt: null, ageS: null, lastError: "HTTPError: HTTP 500", rows: 0 });
  assert.equal(afterFailed, "prices: built-in defaults; fetching the feed now");
  assert.ok(!afterFailed.includes("nothing fetched"));
});

test("the feed's rows under the switch: the line names the feed with its age and says no refresh will come", () => {
  assert.equal(note({ off: true, source: "feed", reason: null, fetchedAt: 1_700_000_000, ageS: 600, lastError: null, rows: 6 }),
    "prices: live feed, fetched 10 minutes ago; refresh off (ROMP_PRICE_FEED=off)",
    "the user stopped the traffic, not the data: the rows serve, and the line says the switch is what keeps them from refreshing");
  assert.equal(note({ off: false, source: "feed", ageS: 600 }), "prices: live feed, fetched 10 minutes ago", "the switch unset: the plain line");
  assert.equal(note({ source: "feed", ageS: 600 }), "prices: live feed, fetched 10 minutes ago", "no `off` in the block: nothing claimed about the switch");
  assert.equal(note({ off: "off", source: "feed", ageS: 600 }), "prices: live feed, fetched 10 minutes ago", "`off` is the kernel's boolean; a string is not read as the switch");
});

test("the feed's rows after a failed refresh: the age says when they landed and the line says the refresh since failed", () => {
  assert.equal(note({ off: false, source: "feed", reason: null, fetchedAt: 1_700_000_000, ageS: 21_600, lastError: "HTTPError: HTTP 500", rows: 6 }),
    "prices: live feed, fetched 6 hours ago; the last refresh failed (HTTPError: HTTP 500)",
    "the kernel keeps the rows when a refresh fails and records the failure; both are said");
  assert.equal(note({ source: "feed", ageS: 612_000, lastError: "URLError: ConnectionRefusedError: errno 111 (Connection refused)" }),
    "prices: live feed, fetched 7 days ago; the last refresh failed (URLError: ConnectionRefusedError: errno 111 (Connection refused))",
    "a week of failed refreshes on a dead host: the failure is on the line, not only in the kernel's log, and the age is said in days as the API-health popup would say it");
  assert.equal(note({ source: "feed", lastError: "HTTPError: HTTP 500" }), "prices: live feed; the last refresh failed (HTTPError: HTTP 500)",
    "no age in the block: the failure is still said");
  assert.equal(note({ off: true, source: "feed", ageS: 7_200, lastError: "HTTPError: HTTP 500" }),
    "prices: live feed, fetched 2 hours ago; refresh off (ROMP_PRICE_FEED=off)",
    "the switch outranks a failure it predates: with it on no refresh will come, so that is what is said");
  assert.equal(note({ source: "feed", ageS: 7_200, lastError: null }), "prices: live feed, fetched 2 hours ago", "a landed refresh clears the blame, and the line");
});

test("a feed that matched some of the table's ids prices those and no more, and the line says which share", () => {
  assert.equal(note({ off: false, source: "feed", reason: null, fetchedAt: 1_781_100_000, ageS: 0, lastError: null, rows: 1, known: 6 }),
    "prices: live feed for 1 of 6 models, fetched now; built-in defaults for the rest",
    "one built-in id matched: the other five are priced from the defaults, and the line does not call the table live");
  assert.equal(note({ source: "feed", ageS: 240, rows: 5, known: 6 }),
    "prices: live feed for 5 of 6 models, fetched 4 minutes ago; built-in defaults for the rest");
  assert.equal(note({ source: "feed", ageS: 240, rows: 6, known: 6 }), "prices: live feed, fetched 4 minutes ago",
    "every id matched: the plain line, no share to report");
  assert.equal(note({ source: "feed", ageS: 240, rows: 1 }), "prices: live feed, fetched 4 minutes ago",
    "no `known` in the block (an older kernel): nothing to compare against, so nothing claimed");
  assert.equal(note({ source: "feed", ageS: 240, known: 6 }), "prices: live feed, fetched 4 minutes ago", "no `rows` either");
  assert.equal(note({ source: "feed", ageS: 21_600, rows: 5, known: 6, lastError: "HTTPError: HTTP 500" }),
    "prices: live feed for 5 of 6 models, fetched 6 hours ago; built-in defaults for the rest; the last refresh failed (HTTPError: HTTP 500)",
    "the share and the refresh's state are separate clauses, in that order");
});

test("review round 2's copy pass: the served table is the built-in defaults, and a failed fetch says what could not be done, the reason class after it", () => {
  // built-in is the literal term for the table that ships with romp (the model catalog's copy already says "built-in");
  // "the feed could not be fetched" states the failure without a "last" that, with nothing cached, has no earlier success to stand against
  assert.equal(note({ off: false, source: "defaults", reason: "failed", fetchedAt: null, ageS: null, lastError: "HTTPError: HTTP 500", rows: 0 }),
    "prices: built-in defaults; the feed could not be fetched (HTTPError: HTTP 500)");
  assert.equal(note({ source: "defaults", reason: "failed" }), "prices: built-in defaults; the feed could not be fetched", "no recorded reason: the fact alone");
  assert.equal(note({ source: "defaults", reason: "failed", lastError: "HTTPError: HTTP 500", overrides: 2 }),
    "prices: built-in defaults; the feed could not be fetched (HTTPError: HTTP 500); 2 rows overridden by model-prices.json", "the tails keep their order after it");
  assert.equal(note({ off: true, source: "defaults", reason: "off" }), "prices: built-in defaults; live feed off (ROMP_PRICE_FEED=off)");
  for (const s of [note({ source: "defaults", reason: "off" }), note({ source: "defaults", reason: "unfetched" }), note({ source: "feed", ageS: 240, rows: 5, known: 6 })])
    assert.ok(!s.includes("baked-in"), "the word the copy pass retired is on no line: " + s);
});

test("review round 2: rows the feed had for known models that could not be read are said on the feed line too, apart from models it never named", () => {
  // the kernel's block after a landing that parsed one of the two rows the feed had for known models (its stderr line says
  // so once, at the fetch); the modal says it while those rows serve, so a schema move at the feed for one model is not
  // read as a feed that never priced it
  assert.equal(note({ off: false, source: "feed", reason: null, fetchedAt: 1_781_100_000, ageS: 1, lastError: null, rows: 1, matched: 2, known: 6 }),
    "prices: live feed for 1 of 6 models, fetched now; built-in defaults for the rest; the feed's rows for 1 known model could not be read");
  assert.equal(note({ source: "feed", ageS: 240, rows: 3, matched: 5, known: 6 }),
    "prices: live feed for 3 of 6 models, fetched 4 minutes ago; built-in defaults for the rest; the feed's rows for 2 known models could not be read", "plural");
  assert.equal(note({ source: "feed", ageS: 240, rows: 1, matched: 1, known: 6 }),
    "prices: live feed for 1 of 6 models, fetched 4 minutes ago; built-in defaults for the rest", "every row the feed had for a known model parsed: nothing unread to say");
  assert.equal(note({ source: "feed", ageS: 240, rows: 1, known: 6 }),
    "prices: live feed for 1 of 6 models, fetched 4 minutes ago; built-in defaults for the rest", "no `matched` in the block (an older kernel): nothing claimed");
  assert.equal(note({ off: true, source: "feed", ageS: 600, rows: 1, matched: 2, known: 6, overrides: 1 }),
    "prices: live feed for 1 of 6 models, fetched 10 minutes ago; built-in defaults for the rest; the feed's rows for 1 known model could not be read; refresh off (ROMP_PRICE_FEED=off); 1 row overridden by model-prices.json",
    "the tails keep their order: the share, the unread rows, the refresh's state, the override count");
});

// The switch's value read as neither off nor unset (the review of PR 878, 2026-09-20): the kernel compares
// ROMP_PRICE_FEED against off alone, so `of`, `false` or `0` leaves the feed on and, until the kernel's `unrecognised`,
// read on every surface exactly as an unset variable. The clause names the variable and the rule and never the
// value: the block rides the auth-exempt /version, and an environment value is the user's own text.
const UNREC = "ROMP_PRICE_FEED is set to a value that is not off, so the feed stays on (only off turns it off)";

test("a ROMP_PRICE_FEED value that is not off: the feed stays on, and the line says so on either source, last before the override count", () => {
  assert.equal(note({ off: false, unrecognised: true, source: "feed", reason: null, fetchedAt: 1_700_000_000, ageS: 240, lastError: null, rows: 6, matched: 6, known: 6, overrides: 0 }),
    "prices: live feed, fetched 4 minutes ago; " + UNREC, "the feed line: the rows and their age, then that the switch did not take");
  assert.equal(note({ off: false, unrecognised: true, source: "defaults", reason: "inflight", fetchedAt: null, ageS: null, lastError: null, rows: 0 }),
    "prices: built-in defaults; fetching the feed now; " + UNREC,
    "the first open under a misspelt switch: the fetch is under way, and the line says why the switch did not stop it");
  assert.equal(note({ unrecognised: true, source: "defaults", reason: "unfetched" }), "prices: built-in defaults; nothing fetched from the feed yet; " + UNREC,
    "before the first attempt (reachable on /version): the value is already read, and said");
  assert.equal(note({ unrecognised: true, source: "defaults", reason: "failed", lastError: "HTTPError: HTTP 500", overrides: 2 }),
    "prices: built-in defaults; the feed could not be fetched (HTTPError: HTTP 500); " + UNREC + "; 2 rows overridden by model-prices.json",
    "after the reason, before the override count");
  assert.equal(note({ unrecognised: true, source: "feed", ageS: 7_200, lastError: "HTTPError: HTTP 500", overrides: 1 }),
    "prices: live feed, fetched 2 hours ago; the last refresh failed (HTTPError: HTTP 500); " + UNREC + "; 1 row overridden by model-prices.json",
    "after the refresh's state, before the override count");
  assert.equal(note({ unrecognised: true, source: "feed", ageS: 240, rows: 1, matched: 2, known: 6 }),
    "prices: live feed for 1 of 6 models, fetched 4 minutes ago; built-in defaults for the rest; the feed's rows for 1 known model could not be read; " + UNREC,
    "after every clause about the rows: the share, the unread rows, then the switch");
});

test("the switch's other readings word nothing new: `unrecognised` false or absent is the older line byte for byte, and no value a block might carry is echoed", () => {
  assert.equal(note({ off: false, unrecognised: false, source: "feed", ageS: 240 }), "prices: live feed, fetched 4 minutes ago", "the variable unset or empty: the plain line");
  assert.equal(note({ off: false, unrecognised: false, source: "defaults", reason: "inflight" }), "prices: built-in defaults; fetching the feed now");
  assert.equal(note({ off: true, unrecognised: false, source: "defaults", reason: "off" }), "prices: built-in defaults; live feed off (ROMP_PRICE_FEED=off)", "off took: that is what is said");
  assert.equal(note({ off: true, unrecognised: false, source: "feed", ageS: 600 }), "prices: live feed, fetched 10 minutes ago; refresh off (ROMP_PRICE_FEED=off)");
  for (const pf of [{ source: "feed", ageS: 240 }, { source: "defaults", reason: "inflight" }, { source: "defaults", reason: "unfetched", overrides: 1 }])
    assert.equal(note(pf), note({ ...pf, unrecognised: false }), "an older kernel's block, with no such key, and a current kernel's false read the same: " + JSON.stringify(pf));
  assert.equal(note({ unrecognised: "disabled", source: "feed", ageS: 240 }), "prices: live feed, fetched 4 minutes ago", "the kernel's flag is a boolean; a string is not read as it");
  assert.equal(note({ unrecognised: 1, source: "defaults", reason: "unfetched" }), "prices: built-in defaults; nothing fetched from the feed yet", "nor is a number");
  // no kernel puts the value in the block (it rides the auth-exempt /version and carries no environment text), and a
  // block that did would not be echoed: the clause is fixed text keyed on the boolean, and reads no other key for it
  const withValue = note({ unrecognised: true, value: "disabled", ROMP_PRICE_FEED: "disabled", source: "feed", ageS: 240 });
  assert.equal(withValue, "prices: live feed, fetched 4 minutes ago; " + UNREC);
  assert.ok(!withValue.includes("disabled"), "the value is on no line");
  assert.equal(UNREC.indexOf(";"), -1, "the clause holds no semicolon of its own: the line's tails are semicolon-joined, and one clause reads as one");
});

// Rows the kernel could not read (the re-ruling of the review of PR 878, 2026-09-21): the kernel skips the bad row alone,
// counts it in the block as `overrideRowsRejected`, and names it in its own log; the line carries the count as one
// clause, last, after the override count that says what the file changed, so the reader sees that the rest of the file
// applies and how much of it did not read. A count only: the keys are the user's own text and the block rides /version.
const SKIPPED_1 = "1 row of model-prices.json could not be read and was skipped (the rest of the file applies)";
const SKIPPED_2 = "2 rows of model-prices.json could not be read and were skipped (the rest of the file applies)";

test("rows of model-prices.json the kernel could not read: the count is said last on either source, singular and plural", () => {
  assert.equal(note({ off: true, source: "defaults", reason: "off", overrides: 2, overrideRowsRejected: 1 }),
    "prices: built-in defaults; live feed off (ROMP_PRICE_FEED=off); 2 rows overridden by model-prices.json; " + SKIPPED_1,
    "the feed-off box the reference sends to the file: the rows in effect, then the row that was not read");
  assert.equal(note({ off: true, source: "defaults", reason: "off", overrides: 0, overrideRowsRejected: 2 }),
    "prices: built-in defaults; live feed off (ROMP_PRICE_FEED=off); " + SKIPPED_2,
    "no row in effect and two skipped: nothing about a count of rows in effect, the skipped clause alone, plural");
  assert.equal(note({ source: "feed", ageS: 240, overrides: 1, overrideRowsRejected: 1 }),
    "prices: live feed, fetched 4 minutes ago; 1 row overridden by model-prices.json; " + SKIPPED_1, "the feed line: the same order");
  assert.equal(note({ off: true, unrecognised: false, source: "feed", ageS: 600, rows: 1, matched: 2, known: 6, overrides: 1, overrideRowsRejected: 1 }),
    "prices: live feed for 1 of 6 models, fetched 10 minutes ago; built-in defaults for the rest; the feed's rows for 1 known model could not be read; refresh off (ROMP_PRICE_FEED=off); 1 row overridden by model-prices.json; " + SKIPPED_1,
    "every tail keeps its order: the share, the unread feed rows, the refresh's state, the override count, then the skipped rows");
  assert.equal(note({ unrecognised: true, source: "defaults", reason: "failed", lastError: "HTTPError: HTTP 500", overrides: 2, overrideRowsRejected: 1 }),
    "prices: built-in defaults; the feed could not be fetched (HTTPError: HTTP 500); " + UNREC + "; 2 rows overridden by model-prices.json; " + SKIPPED_1,
    "after the switch clause and the override count");
  assert.equal(SKIPPED_1.indexOf(";"), -1, "the clause holds no semicolon of its own: the line's tails are semicolon-joined, and one clause reads as one");
});

test("a count of zero, no count, or a count that is not a number says nothing about skipped rows, and no key of the file is echoed", () => {
  assert.equal(note({ off: true, source: "defaults", reason: "off", overrides: 1, overrideRowsRejected: 0 }),
    "prices: built-in defaults; live feed off (ROMP_PRICE_FEED=off); 1 row overridden by model-prices.json", "every row read: nothing to say");
  for (const pf of [{ source: "feed", ageS: 240 }, { source: "defaults", reason: "off", overrides: 1 }, { source: "defaults", reason: "unfetched" }])
    assert.equal(note(pf), note({ ...pf, overrideRowsRejected: 0 }), "an older kernel's block, with no such key, and a current kernel's zero read the same: " + JSON.stringify(pf));
  assert.equal(note({ source: "defaults", reason: "off", overrideRowsRejected: "1" }), "prices: built-in defaults; live feed off (ROMP_PRICE_FEED=off)",
    "the kernel's count is a number; a string is not read as one");
  assert.equal(note({ source: "defaults", reason: "off", overrideRowsRejected: true }), "prices: built-in defaults; live feed off (ROMP_PRICE_FEED=off)", "nor is a boolean");
  // no kernel puts a row's key in the block; a block that did would not be echoed, since the clause is fixed text keyed on the count
  const withKey = note({ source: "defaults", reason: "off", overrideRowsRejected: 1, rejectedKeys: ["claude-opus-4-8"] });
  assert.equal(withKey, "prices: built-in defaults; live feed off (ROMP_PRICE_FEED=off); " + SKIPPED_1);
  assert.ok(!withKey.includes("opus"), "no key of the file is on the line");
});

// A model-prices.json the kernel could not read as a JSON object (a syntax error, a top-level list) is ignored whole, the
// kernel's class `overrideFault` 'file' (the second round of that review, 2026-09-21: the line worded the skipped rows
// and never this, so a file discarded whole rendered the clean line byte for byte, the worse fault the silent one).
// Fixed text in the skipped rows' slot, distinct from the row clause, which says the rest applies; never the path or the
// file's text. The kernel emits one class or the other (a file that did not parse has no rows to skip), so the two
// clauses never share a line.
const FILE_IGNORED = "model-prices.json could not be read as a JSON object and was ignored (none of it applies)";

test("a model-prices.json ignored whole: the line says so on either source, last, in the skipped rows' slot, and echoes nothing of the file", () => {
  assert.equal(note({ off: true, source: "defaults", reason: "off", overrides: 0, overrideFault: "file", overrideRowsRejected: 0 }),
    "prices: built-in defaults; live feed off (ROMP_PRICE_FEED=off); " + FILE_IGNORED,
    "the feed-off box the reference sends to the file, and the file did not parse: the reader is told none of it took");
  assert.equal(note({ source: "feed", ageS: 240, overrides: 0, overrideFault: "file", overrideRowsRejected: 0 }),
    "prices: live feed, fetched 4 minutes ago; " + FILE_IGNORED, "the feed line: the same slot");
  assert.equal(note({ unrecognised: true, source: "defaults", reason: "failed", lastError: "HTTPError: HTTP 500", overrideFault: "file" }),
    "prices: built-in defaults; the feed could not be fetched (HTTPError: HTTP 500); " + UNREC + "; " + FILE_IGNORED,
    "after the reason and the switch clause; no count of rows in effect, since none is");
  assert.equal(note({ off: true, source: "feed", ageS: 600, rows: 1, matched: 2, known: 6, overrideFault: "file" }),
    "prices: live feed for 1 of 6 models, fetched 10 minutes ago; built-in defaults for the rest; the feed's rows for 1 known model could not be read; refresh off (ROMP_PRICE_FEED=off); " + FILE_IGNORED,
    "every tail keeps its order: the share, the unread feed rows, the refresh's state, then the file");
  // NOT a shape the kernel emits (a file ignored whole puts no row in effect): the slot alone is pinned, after the count
  assert.equal(note({ source: "defaults", reason: "off", overrides: 2, overrideFault: "file" }),
    "prices: built-in defaults; live feed off (ROMP_PRICE_FEED=off); 2 rows overridden by model-prices.json; " + FILE_IGNORED,
    "a deliberately foreign block: the clause sits where the skipped rows would, after the override count");
  // no kernel puts the file's text or its path in the block; a block that did would not be echoed: the clause is fixed
  // text keyed on the class, and reads no other key for it
  const withText = note({ source: "defaults", reason: "off", overrideFault: "file", overrideText: "[1, 2", overridePath: "/somewhere/model-prices.json" });
  assert.equal(withText, "prices: built-in defaults; live feed off (ROMP_PRICE_FEED=off); " + FILE_IGNORED);
  assert.ok(!withText.includes("[1") && !withText.includes("/somewhere"), "nothing of the file, and no path, is on the line");
  assert.equal(FILE_IGNORED.indexOf(";"), -1, "the clause holds no semicolon of its own: the line's tails are semicolon-joined, and one clause reads as one");
  assert.ok(!FILE_IGNORED.includes("/") && !FILE_IGNORED.includes("~"), "the file is named by its name alone, as the row clause names it");
});

test("the row class keeps the count clause and no file clause; an absent, null or foreign class words nothing new", () => {
  // a guard, green before the clause landed and after: it pins what the clause must not change
  const row = note({ off: true, source: "defaults", reason: "off", overrides: 2, overrideFault: "row", overrideRowsRejected: 1 });
  assert.equal(row, "prices: built-in defaults; live feed off (ROMP_PRICE_FEED=off); 2 rows overridden by model-prices.json; " + SKIPPED_1,
    "'row': the count says what was skipped, and the rest of the file applies");
  assert.ok(!row.includes("ignored"), "no file clause under the row class");
  for (const pf of [{ source: "feed", ageS: 240 }, { source: "defaults", reason: "off", overrides: 1 }, { source: "defaults", reason: "unfetched" },
    { source: "defaults", reason: "off", overrides: 2, overrideRowsRejected: 1 }])
    assert.equal(note({ ...pf, overrideFault: null }), note(pf), "an older kernel's block, with no such key, and a current kernel's null read the same: " + JSON.stringify(pf));
  for (const v of ["FILE", "whole", "rows", 1, true, ["file"], { file: true }])
    assert.equal(note({ source: "defaults", reason: "off", overrideFault: v }), "prices: built-in defaults; live feed off (ROMP_PRICE_FEED=off)",
      "a class this view does not know says nothing rather than something false: " + JSON.stringify(v));
});

// The fetch age (the second round of that review): the line's words are the shell's one age helper's, api-health-merge.ts
// agoWords, the words the API-health popup's as-of uses, so a stamp reads the same on both surfaces: now under 45 s, then
// the rounded minute, the rounded hour under 24 h, then the rounded day. A copy of the helper here floored instead of
// rounding, said just now under a minute, and counted hours without end (720 hours ago for the popup's 30 days ago).
test("the fetch age is the shell's age words: now under 45 s, rounded minutes, rounded hours under a day, then days", () => {
  assert.equal(note({ source: "feed", ageS: 0 }), "prices: live feed, fetched now", "the second the fetch landed");
  assert.equal(note({ source: "feed", ageS: 44 }), "prices: live feed, fetched now", "under 45 s");
  assert.equal(note({ source: "feed", ageS: 45 }), "prices: live feed, fetched 1 minute ago", "45 s rounds to the minute");
  assert.equal(note({ source: "feed", ageS: 89 }), "prices: live feed, fetched 1 minute ago");
  assert.equal(note({ source: "feed", ageS: 90 }), "prices: live feed, fetched 2 minutes ago", "rounded, not floored");
  assert.equal(note({ source: "feed", ageS: 3_570 }), "prices: live feed, fetched 1 hour ago", "59.5 minutes rounds to 60, which is the hour");
  assert.equal(note({ source: "feed", ageS: 3_600 }), "prices: live feed, fetched 1 hour ago");
  assert.equal(note({ source: "feed", ageS: 82_800 }), "prices: live feed, fetched 23 hours ago");
  assert.equal(note({ source: "feed", ageS: 86_400 }), "prices: live feed, fetched 1 day ago",
    "the day arm: the feed's TTL is six hours, and a cache kept under the switch or through failed refreshes can be days old");
  assert.equal(note({ source: "feed", ageS: 90_000 }), "prices: live feed, fetched 1 day ago", "25 hours is a day, not 25 hours");
  assert.equal(note({ source: "feed", ageS: 2_592_000 }), "prices: live feed, fetched 30 days ago", "what the API-health popup says of the same stamp");
  // the same helper, by execution: the line's words are agoWords' for every age, the boundaries included
  const ages = [0, 1, 44, 45, 59, 60, 89, 90, 599, 600, 3_570, 3_599, 3_600, 5_400, 21_600, 82_800, 84_600, 86_400, 90_000, 129_600, 612_000, 2_592_000];
  assert.ok(ages.length > 20, "the boundary set is populated");
  for (const s of ages)
    assert.equal(note({ source: "feed", ageS: s }), "prices: live feed, fetched " + agoWords(s), "one helper, at " + s + " s");
});

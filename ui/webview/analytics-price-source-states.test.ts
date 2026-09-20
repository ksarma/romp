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
//   the whole table live; a block without `known` (an older kernel) is the plain line.
import { test } from "node:test";
import * as assert from "node:assert/strict";

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
    "prices: live feed, fetched 170 hours ago; the last refresh failed (URLError: ConnectionRefusedError: errno 111 (Connection refused))",
    "a week of failed refreshes on a dead host: the failure is on the line, not only in the kernel's log");
  assert.equal(note({ source: "feed", lastError: "HTTPError: HTTP 500" }), "prices: live feed; the last refresh failed (HTTPError: HTTP 500)",
    "no age in the block: the failure is still said");
  assert.equal(note({ off: true, source: "feed", ageS: 7_200, lastError: "HTTPError: HTTP 500" }),
    "prices: live feed, fetched 2 hours ago; refresh off (ROMP_PRICE_FEED=off)",
    "the switch outranks a failure it predates: with it on no refresh will come, so that is what is said");
  assert.equal(note({ source: "feed", ageS: 7_200, lastError: null }), "prices: live feed, fetched 2 hours ago", "a landed refresh clears the blame, and the line");
});

test("a feed that matched some of the table's ids prices those and no more, and the line says which share", () => {
  assert.equal(note({ off: false, source: "feed", reason: null, fetchedAt: 1_781_100_000, ageS: 0, lastError: null, rows: 1, known: 6 }),
    "prices: live feed for 1 of 6 models, fetched just now; built-in defaults for the rest",
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
    "prices: live feed for 1 of 6 models, fetched just now; built-in defaults for the rest; the feed's rows for 1 known model could not be read");
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

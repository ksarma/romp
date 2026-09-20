// The Token usage modal's price-source line, the states review round 1 (2026-09-20) found unsaid or missaid, run
// for real through the pure formatter gear.js exports (raPriceNote), beside analytics-price-source.test.ts (the
// wording's base cases, the node and the wiring). The kernel's block (_price_feed_status) carries more than a
// source and a reason: `fetchedAt` and `lastError` outlive the fetch that set them, `rows` counts the baked-in ids
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
    "prices: baked-in defaults; fetching the feed now", "the first open: the payload is built before the fetch it started lands");
  assert.equal(note({ source: "defaults", reason: "unfetched" }), "prices: baked-in defaults; nothing fetched from the feed yet",
    "no attempt this kernel life (reachable on /version before the first open)");
  // the kernel's re-attempt after a fetch that landed and matched nothing: fetchedAt set, cache empty, a worker parked
  const afterEmpty = note({ off: false, source: "defaults", reason: "inflight", fetchedAt: 1_781_100_000, ageS: 21_600, lastError: null, rows: 0 });
  assert.equal(afterEmpty, "prices: baked-in defaults; fetching the feed now");
  assert.ok(!afterEmpty.includes("nothing fetched"), "a fetch landed six hours ago: 'nothing fetched' would be false");
  // the kernel's re-attempt after a failed fetch: lastError set, a worker parked
  const afterFailed = note({ off: false, source: "defaults", reason: "inflight", fetchedAt: null, ageS: null, lastError: "HTTPError: HTTP 500", rows: 0 });
  assert.equal(afterFailed, "prices: baked-in defaults; fetching the feed now");
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
    "prices: live feed for 1 of 6 models, fetched just now; baked-in defaults for the rest",
    "one baked-in id matched: the other five are priced from the defaults, and the line does not call the table live");
  assert.equal(note({ source: "feed", ageS: 240, rows: 5, known: 6 }),
    "prices: live feed for 5 of 6 models, fetched 4 minutes ago; baked-in defaults for the rest");
  assert.equal(note({ source: "feed", ageS: 240, rows: 6, known: 6 }), "prices: live feed, fetched 4 minutes ago",
    "every id matched: the plain line, no share to report");
  assert.equal(note({ source: "feed", ageS: 240, rows: 1 }), "prices: live feed, fetched 4 minutes ago",
    "no `known` in the block (an older kernel): nothing to compare against, so nothing claimed");
  assert.equal(note({ source: "feed", ageS: 240, known: 6 }), "prices: live feed, fetched 4 minutes ago", "no `rows` either");
  assert.equal(note({ source: "feed", ageS: 21_600, rows: 5, known: 6, lastError: "HTTPError: HTTP 500" }),
    "prices: live feed for 5 of 6 models, fetched 6 hours ago; baked-in defaults for the rest; the last refresh failed (HTTPError: HTTP 500)",
    "the share and the refresh's state are separate clauses, in that order");
});

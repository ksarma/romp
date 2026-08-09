// A KNOWN session state must never render as NOTHING (the user 2026-08-09). The dashboard drew no pip
// for sessions whose kernel-recorded state was `waiting`, while a same-state session that happened to be
// awaiting background work drew a straw one — so a blank pip was indistinguishable from a rendering hole
// (and from a genuinely unknown state). The kernel now emits a TOTAL per-session status partition
// (working / awaiting / ready / stateUnknown) on the feed payload; the feed and the fleet render every
// quarter explicitly (gold dot / straw dot / hollow steel ready ring / gray unknown ring, each with a
// tooltip). A bare name is reserved for payloads that PREDATE the lists — an old kernel, including an
// old REMOTE kernel in a federated merge, whose sessions land in no list and keep the legacy look
// instead of reading falsely as "unknown". Source pins + executable federation checks (no jsdom).
import { test } from "node:test";
import assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { prefixInbound, mergeHostFeeds } from "./federation";

const W = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const FEED = W("feed.ts");
const FEEDCSS = W("feed.css");
const FLEET = W("fleet.ts");
const FLEETCSS = W("fleet-pane.css");
const KERNEL = fs.readFileSync(path.resolve(process.cwd(), "..", "bin", "romp-kernel"), "utf8");

test("kernel: the feed payload carries the ready/stateUnknown halves of the partition", () => {
  // the helper mirrors build_feed's own filters (hideFromFeed in no list) and splits the rest by
  // whether the merged live map could actually be read for that session
  assert.match(KERNEL, /def _feed_status_names\(alive, tmux, working, awaiting\):/);
  assert.match(KERNEL, /\(ready if tmux\.get\(s\["sid"\]\) is not None else unknown\)\.append\(nm\)/);
  assert.match(KERNEL, /"ready": ready, "stateUnknown": state_unknown,/);
});

test("feed: dotFor is total over the partition — ready and unknown render explicitly, blank = legacy only", () => {
  assert.match(FEED, /readySet = new Set\(Array\.isArray\(m\.ready\) \? m\.ready : \[\]\);/);
  assert.match(FEED, /unknownSet = new Set\(Array\.isArray\(m\.stateUnknown\) \? m\.stateUnknown : \[\]\);/);
  // the gap this fixes: a name absent from work/await used to fall straight to "" (render nothing);
  // now it must pass through the ready and unknown quarters before the legacy-blank fallback
  assert.match(FEED, /: readySet\.has\(name\) \? "ready" : unknownSet\.has\(name\) \? "unknown" : "";/);
  // every pip explains itself on hover (the user 2026-07-22) — including the two new quarters
  assert.match(FEED, /ready: "idle — nothing running; finished its last turn",/);
  assert.match(FEED, /unknown: "state unknown — romp couldn't read this session's live state",/);
  // one kind class at a time; a dot retints in place when the state flips
  assert.match(FEED, /for \(const k of \["await", "ready", "unknown"\]\) d\.classList\.toggle\(k, st === k\);/);
});

test("feed css: hollow ring = at rest / unknown, filled = active — status colors keep their meaning", () => {
  // ready ring wears the chat chip's Ready steel (--st-ready-bg #2b7fb8); unknown the detached-host gray
  assert.match(FEEDCSS, /\.fwork-dot\.ready \{ background: transparent; box-shadow: inset 0 0 0 1\.5px #2b7fb8; \}/);
  assert.match(FEEDCSS, /\.fwork-dot\.unknown \{ background: transparent; box-shadow: inset 0 0 0 1\.5px #8a8a8a; \}/);
});

test("fleet: the session rows speak the same four-class pip language off their own status.state", () => {
  assert.match(FLEET, /function statusDot\(s: FleetSession\): HTMLElement \| null \{/);
  // working → gold, awaitingBg → straw, ready/idle → ring, MISSING status → explicit unknown ring
  assert.match(FLEET, /st === "working" \? "" : st === "awaitingBg" \? "await"/);
  assert.match(FLEET, /: st === "ready" \|\| st === "idle" \? "ready" : st \? null : "unknown";/);
  // both name sites route through it (grouped header + flat-view session label)
  assert.equal((FLEET.match(/statusDot\(s\)/g) || []).length, 2);
  assert.match(FLEETCSS, /\.fl-workdot\.await\{background:#54B204\}/);
  assert.match(FLEETCSS, /\.fl-workdot\.ready\{background:transparent;box-shadow:inset 0 0 0 1\.5px #2b7fb8\}/);
  assert.match(FLEETCSS, /\.fl-workdot\.unknown\{background:transparent;box-shadow:inset 0 0 0 1\.5px #8a8a8a\}/);
});

// ── federation: the new lists ride like working/awaiting, per-host honestly ─────────────────────────

const U = "11111111-2222-3333-4444-555555555555";

test("federation: prefixInbound prefixes ready/stateUnknown names like the other session-id arrays", () => {
  const m = prefixInbound("TESTHOST", { type: "feed", working: ["web"], awaiting: [],
                                        ready: ["api"], stateUnknown: ["tests"], asks: [] });
  assert.deepEqual(m.ready, ["TESTHOST:api"]);
  assert.deepEqual(m.stateUnknown, ["TESTHOST:tests"]);
});

test("federation: mergeHostFeeds concatenates the lists; an OLD host contributes to none of them", () => {
  const local = { type: "feed", items: [], asks: [], working: ["web"], awaiting: [],
                  ready: ["api"], stateUnknown: ["docs"], order: [] };
  // a remote kernel too old to send the new lists — its sessions must NOT read as "unknown"
  const oldRemote = { type: "feed", items: [], asks: [{ sid: "TESTHOST:" + U, name: "TESTHOST:tests" }],
                      working: [], awaiting: [], order: [] };
  const m = mergeHostFeeds({ "": local, TESTHOST: oldRemote }, ["", "TESTHOST"]);
  assert.deepEqual(m.ready, ["api"]);
  assert.deepEqual(m.stateUnknown, ["docs"]);
  // the old host's session lands in NO status list → the renderer keeps the legacy bare-name look
  for (const k of ["working", "awaiting", "ready", "stateUnknown"] as const)
    assert.ok(!m[k].includes("TESTHOST:tests"), k + " must not claim the old host's session");
});

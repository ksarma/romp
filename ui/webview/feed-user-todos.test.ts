// The quiet feed-card marker + the escalated card (plans/user-todos.md, slice 2). Todos are
// session-scoped, so EVERY card of the owning session wears the marker (no feed strip in v1);
// the idle-escalation floor's card carries the story on the standard blocked badge instead, so
// one card never says it twice. Data rides build_feed's top-level sid-keyed open-count map, the
// way working[]/bgServices ride the payload. Source pins for the render (feed.ts has no jsdom
// harness) + EXECUTED federation merges (mergeHostFeeds/prefixInbound are importable).
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { mergeHostFeeds, prefixInbound } from "./federation";

const FEED = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "feed.ts"), "utf8");
const FEED_CSS = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "feed.css"), "utf8");

test("the feed payload's sid-keyed map lands in module state", () => {
  assert.match(FEED, /let userTodosMap: Record<string, number> = \{\};/);
  assert.match(FEED, /userTodosMap = m\.userTodos && typeof m\.userTodos === "object" && !Array\.isArray\(m\.userTodos\)/);
});

test("every card of the owning session wears the quiet marker", () => {
  assert.match(FEED, /el\("a", "fask-usertodo"\)/);
  assert.match(FEED, /const utn = userTodosMap\[it\.sid\] \|\| 0;/);
  assert.match(FEED, /waiting on you/, "the split card's own heading vocabulary — one term everywhere");
});

test("the marker yields on the escalated card (the blocked badge carries the story there)", () => {
  assert.match(FEED, /utn > 0 && it\.blocked\?\.state !== "userTodos"/,
    "one card never says it twice");
});

test("the marker is quiet, and click-safe via updateAskCard's per-push rewire", () => {
  assert.match(FEED_CSS, /\.fask-usertodo \{/);
  assert.match(FEED_CSS, /\.fask-usertodo[^}]*var\(--dim\)/, "dim by default — quiet, never an alarm");
  // the marker opens the owning session's chat (where the split card with Reply/Dismiss lives)
  const marker = FEED.slice(FEED.indexOf("const utn = userTodosMap"));
  assert.match(marker.slice(0, 900), /openSession/, "click lands on the session, live");
});

test("the escalated card and the goal-less placeholder wear the userTodos badge", () => {
  assert.match(FEED, /it\.blocked\.state === "userTodos" \? "⚑ waiting on you"/,
    "its own badge text — never the ⏸ picker fallthrough");
  const badge = FEED.slice(FEED.indexOf('=== "userTodos" ? "⚑ waiting on you"') - 400,
    FEED.indexOf('=== "userTodos" ? "⚑ waiting on you"') + 1200);
  assert.match(badge, /live: true/, "the badge click opens the chat at its live bottom (the split card)");
});

test("federation: the map's keys are host-prefixed inbound and merged across hosts", () => {
  const pre: any = prefixInbound("TESTHOST", { type: "feed", userTodos: { "11111111-2222": 2 } });
  assert.deepEqual(pre.userTodos, { "TESTHOST:11111111-2222": 2 });
  const merged: any = mergeHostFeeds({
    "": { type: "feed", asks: [], userTodos: { "11111111-2222": 1 } },
    "TESTHOST": { type: "feed", asks: [], userTodos: { "TESTHOST:33333333-4444": 2 } },
  }, ["", "TESTHOST"]);
  assert.deepEqual(merged.userTodos, { "11111111-2222": 1, "TESTHOST:33333333-4444": 2 });
});

test("a host too old to send the map contributes nothing and breaks nothing", () => {
  const merged: any = mergeHostFeeds({
    "": { type: "feed", asks: [] },
    "TESTHOST": { type: "feed", asks: [] },
  }, ["", "TESTHOST"]);
  assert.deepEqual(merged.userTodos, {});
});

// ── the "Waiting on you" pane's rows (userTodoRows, waiting.ts) ride the same frame ──────────────
// One {sid, name, color, todos} per session with open todos. sid+name are host-prefixed inbound
// (OBJ_SID), so the pane's ops route back to the owning kernel by the sid's prefix; the todo ids
// inside stay bare (every op names them beside the routed sid). Merged by concatenation, and —
// like ledgers — present only once some host actually sent the key: the pane gates its loader on
// the key being an array, so a frame from a kernel that predates the pane must never read as
// "nothing waiting".
test("federation: userTodoRows get sid+name prefixed inbound, todo ids untouched", () => {
  const pre: any = prefixInbound("TESTHOST", { type: "feed", userTodoRows: [
    { sid: "11111111-2222", name: "web", color: null, todos: [{ id: "ut-0a0a0a0a", text: "Need the port", createdT: 1 }] },
  ] });
  assert.deepEqual(pre.userTodoRows, [
    { sid: "TESTHOST:11111111-2222", name: "TESTHOST:web", color: null, todos: [{ id: "ut-0a0a0a0a", text: "Need the port", createdT: 1 }] },
  ]);
});

test("federation: userTodoRows concatenate across hosts; userTodosOn is the LOCAL kernel's alone", () => {
  const merged: any = mergeHostFeeds({
    "": { type: "feed", asks: [], userTodosOn: false, userTodoRows: [] },
    "TESTHOST": { type: "feed", asks: [], userTodosOn: true,
                  userTodoRows: [{ sid: "TESTHOST:33333333-4444", name: "TESTHOST:api", color: null, todos: [{ id: "ut-0b0b0b0b", text: "Need the auth decision", createdT: 2 }] }] },
  }, ["", "TESTHOST"]);
  assert.deepEqual(merged.userTodoRows.map((r: any) => r.sid), ["TESTHOST:33333333-4444"]);
  assert.equal(merged.userTodosOn, false, "the switch is per install: the pane says 'off here' for the local kernel only");
});

test("federation: no host has sent userTodoRows → the key is ABSENT, so the pane's loader holds", () => {
  const merged: any = mergeHostFeeds({
    "": { type: "feed", asks: [] },
    "TESTHOST": { type: "feed", asks: [] },
  }, ["", "TESTHOST"]);
  assert.ok(!("userTodoRows" in merged), "an older kernel's frame must read 'not built', never 'nothing waiting'");
  const some: any = mergeHostFeeds({ "": { type: "feed", asks: [], userTodoRows: [] } }, [""]);
  assert.deepEqual(some.userTodoRows, [], "…while an honest empty [] from a current kernel comes through as []");
});

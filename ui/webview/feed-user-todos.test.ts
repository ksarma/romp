// The quiet request marker on the feed's cards (plans/user-todos.md, the ambient surfaces): the feed frame carries a
// sid-keyed map of OPEN request counts (kernel build_feed `userTodos`, store values only, sid-sorted), and every card of
// the owning session wears a small dim marker, a BUTTON that opens the session's chat at its live bottom, with the count
// when there is more than one. The count is a board-level input, so it rides the per-card update gate's key: a request
// registered or closed reaches an unchanged card, and an unrelated push repaints nothing (feed-render-incremental.test.ts
// runs that). Federation prefixes the map's keys inbound and merges it across hosts. Source pins over feed.ts and
// feed.css (the render has no DOM harness beyond the incremental test), the federation transforms EXECUTED.
// No card moves here: the marker is furniture on cards that exist. Synthetic notes-api world, hostname TESTHOST.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { prefixInbound, mergeHostFeeds } from "./federation";

const FEED = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "feed.ts"), "utf8");
const CSS = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "feed.css"), "utf8");
const WEB = "11111111-2222-3333-4444-555555555555";
const API = "11111111-2222-3333-4444-666666666666";
const PAINT = FEED.slice(FEED.indexOf("const utn = userTodosMap[it.sid] || 0;"), FEED.indexOf("// The DISTILLER's line", FEED.indexOf("const utn = userTodosMap[it.sid] || 0;")));

test("the frame's map lands in module state through a guard: an object keyed by sid, else empty (the off frame's and an older kernel's)", () => {
  assert.match(FEED, /^let userTodosMap: Record<string, number> = \{\};/m);
  assert.match(FEED, /userTodosMap = m\.userTodos && typeof m\.userTodos === "object" && !Array\.isArray\(m\.userTodos\) \? m\.userTodos : \{\};/,
    "a missing map reads as no requests, never a throw");
});

test("the marker is a hidden BUTTON minted with the card, kept on it, and painted per update from the map", () => {
  assert.match(FEED, /const utMark = el\("button", "fask-usertodo"\) as HTMLButtonElement; utMark\.type = "button"; utMark\.style\.display = "none";/,
    "a button like its row-mates (Retry, Revive, the cap switch): focusable, Enter and Space from the element");
  assert.match(FEED, /row2\.append\(utMark\);/, "a direct row2 child in its own append");
  assert.match(FEED, /a\._utMark = utMark;/);
  assert.ok(PAINT.length > 0, "the paint block sits in updateAskCard");
  assert.match(PAINT, /if \(utn > 0\) \{/, "shown while the session has an open request");
  assert.match(PAINT, /utMark\.textContent = utn > 1 \? "⚑ " \+ utn \+ " requests" : "⚑ request";/, "the count only past one");
  assert.match(PAINT, /setTip\(utMark, /, "a styled tip, like the row's other badges");
  assert.match(PAINT, /utMark\.onclick = \(ev: Event\) => \{ ev\.stopPropagation\(\); vscodeApi\?\.postMessage\(\{ type: "openSession", id: it\.sid, live: true \}\); \};/,
    "the click opens the session's chat at its live bottom, where the card with Reply is, and never bubbles to the card's own click");
  assert.match(PAINT, /\} else \{\s*\n\s*utMark\.style\.display = "none";/, "no open request: hidden, no empty pill");
});

test("every marker string says request; none says todo or waiting on you (the yellow ring's phrase), and none carries an em dash", () => {
  const strings = [...PAINT.matchAll(/"([^"\n]*)"/g)].map((m) => m[1]).filter((s) => /[a-z]{3}/.test(s) && !/^(openSession|button|none)$/.test(s));
  assert.ok(strings.some((s) => /request/.test(s)), "the words are there to check: " + JSON.stringify(strings));
  for (const s of strings) {
    assert.doesNotMatch(s, /todo/i, s);
    assert.doesNotMatch(s, /waiting on you/i, s);
    assert.doesNotMatch(s, /\u2014/, s);
  }
  assert.match(PAINT, /"this session has a request for you: click to open its chat and answer it"/);
  assert.match(PAINT, /"this session has " \+ utn \+ " requests for you: click to open its chat and answer them"/);
});

test("the count is a paint input of the card gate: the env member reads the map, so a register or a close reaches an unchanged card", () => {
  assert.match(FEED, /userTodos: \(sid\) => userTodosMap\[sid\] \|\| 0,/);
  const GATE = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "feed-card-gate.ts"), "utf8");
  assert.match(GATE, /userTodos: \(sid: string\) => number;/);
  assert.match(GATE, /String\(env\.userTodos\(it\.sid\) \|\| ""\),/, "in the key, empty for none so a request-less card's key is unchanged");
});

test("GUARD: the floor's state does not exist yet: no badge text and no marker yield for blocked.state === \"userTodos\"; the blocked tip's suffix stands", () => {
  assert.ok(!FEED.includes('blocked.state === "userTodos"'), "the escalation is a later change's, in one place with its state");
  assert.ok(!FEED.includes('"⚑ waiting on you"'));
  assert.match(FEED, /setTip\(a\._blocked as HTMLElement, it\.blocked\.what \+ "[^"]*click to jump to the prompt in the chat"\);/);
});

test("the marker's rule: dim by default (a marker, never an alarm), theme tokens for its border and hover, the button resets, a focus-visible arm, no hardcoded white", () => {
  const rule = /^\.fask-usertodo \{([^}]*)\}/m.exec(CSS);
  assert.ok(rule, "one .fask-usertodo rule");
  assert.match(rule![1], /color: var\(--dim\)/);
  assert.match(rule![1], /border: 1px solid var\(--box-border\)/, "the token defined in both theme blocks; a white alpha vanished on the light theme");
  assert.match(rule![1], /background: none/);
  assert.match(rule![1], /font: inherit/, "the button resets, so it wears the row's font like its span row-mates");
  assert.match(rule![1], /cursor: pointer/);
  assert.match(CSS, /^\.fask-usertodo:hover, \.fask-usertodo:focus-visible \{[^}]*color: var\(--fg\);[^}]*border-color: var\(--dim\);/m, "hover and keyboard focus say it is clickable");
  const block = CSS.slice(CSS.indexOf(".fask-usertodo {"), CSS.indexOf("}", CSS.indexOf(".fask-usertodo:hover")));
  assert.doesNotMatch(block, /rgba\(255, 255, 255/);
  assert.doesNotMatch(block, /#fff\b|#ffffff/);
});

// ── federation, executed ─────────────────────────────────────────────────────────────────────────────────────────────
test("prefixInbound prefixes the feed frame's map keys with the host (a map is not an id-bearing array: the generic passes cannot reach its keys)", () => {
  const out = prefixInbound("TESTHOST", { type: "feed", asks: [], userTodos: { [WEB]: 2, [API]: 1 } });
  assert.deepEqual(out.userTodos, { ["TESTHOST:" + WEB]: 2, ["TESTHOST:" + API]: 1 });
  assert.deepEqual(prefixInbound("", { type: "feed", userTodos: { [WEB]: 2 } }).userTodos, { [WEB]: 2 }, "the local host is the identity");
  assert.deepEqual(prefixInbound("TESTHOST", { type: "session", userTodos: { [WEB]: 2 } }).userTodos, { [WEB]: 2 }, "a non-feed frame's field is left alone");
  assert.equal(prefixInbound("TESTHOST", { type: "feed", asks: [] }).userTodos, undefined, "a frame without the map gains none");
});

test("mergeHostFeeds merges the hosts' maps, keys pre-prefixed; a host without the map contributes nothing; an array or scalar contributes nothing rather than throwing", () => {
  const local = { type: "feed", now: 1, asks: [], userTodos: { [WEB]: 1 } };
  const remote = prefixInbound("TESTHOST", { type: "feed", now: 2, asks: [], userTodos: { [API]: 3 } });
  const merged = mergeHostFeeds({ "": local, TESTHOST: remote }, ["", "TESTHOST"]);
  assert.deepEqual(merged.userTodos, { [WEB]: 1, ["TESTHOST:" + API]: 3 });
  const older = mergeHostFeeds({ "": { type: "feed", now: 1, asks: [] }, TESTHOST: remote }, ["", "TESTHOST"]);
  assert.deepEqual(older.userTodos, { ["TESTHOST:" + API]: 3 }, "a local frame without the map (the off frame's, an older kernel's) hands the remote's through");
  assert.deepEqual(mergeHostFeeds({ "": { type: "feed", now: 1, asks: [] } }, [""]).userTodos, {}, "no host sends it: an honest empty map, never undefined");
  const junk = mergeHostFeeds({ "": { type: "feed", now: 1, asks: [], userTodos: [WEB] }, TESTHOST: { type: "feed", now: 2, asks: [], userTodos: 7 } }, ["", "TESTHOST"]);
  assert.deepEqual(junk.userTodos, {}, "a map of another shape is nobody's count");
});

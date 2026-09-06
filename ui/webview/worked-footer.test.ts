// The "worked …" footer's rule and the tail path's footer plan (worked-footer.ts, 2026-09-06). The chat's tail
// path re-renders exactly the events the kernel names as changed, so the one render that depends on later
// events — the footer on a turn's last reply — is patched from this plan. Synthetic events; epochs are seconds.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { turnWorkedSecs, workedFooterPlan } from "./worked-footer";

type Ev = { kind: string; human?: boolean; t?: number };
const epoch = (e: Ev) => (e.t == null ? null : e.t);
const user = (t: number, human = true): Ev => ({ kind: "user", human, t });
const reply = (t: number): Ev => ({ kind: "assistant", t });
const tool = (t: number): Ev => ({ kind: "tool", t });

test("turnWorkedSecs: the turn's last reply carries the footer once a genuine prompt follows or the session is idle", () => {
  const evs = [user(100), tool(110), reply(160), user(200), reply(230)];
  assert.equal(turnWorkedSecs(evs, 2, true, epoch), 60, "a completed turn's last reply: prompt to reply");
  assert.equal(turnWorkedSecs(evs, 1, true, epoch), null, "not the turn's last reply");
  assert.equal(turnWorkedSecs(evs, 4, true, epoch), null, "the final turn while working: the spinner owns it");
  assert.equal(turnWorkedSecs(evs, 4, false, epoch), 30, "…and idle: the footer");
  assert.equal(turnWorkedSecs(evs, 0, false, epoch), null, "a prompt carries none");
});

test("turnWorkedSecs: the elapsed runs from the immediate trigger, and an injected user line does not end a turn", () => {
  const evs = [user(100), reply(140), user(1000, false), reply(1030), user(2000)];
  assert.equal(turnWorkedSecs(evs, 1, false, epoch), null, "a nudge followed the reply: the same turn continues, so this reply is not its last");
  assert.equal(turnWorkedSecs(evs, 3, false, epoch), 30, "measured from the nudge that prompted the work, not the older prompt");
});

test("plan: a status-only tail (from = len) names the current turn's last reply; idle puts the footer on, working takes it off", () => {
  const evs = [user(100), tool(110), reply(160), user(200), tool(205), reply(230)];
  assert.deepEqual(workedFooterPlan(evs, evs.length, 0, false, epoch), [{ unit: 5, secs: 30 }, { unit: 2, secs: 60 }]);
  assert.deepEqual(workedFooterPlan(evs, evs.length, 0, true, epoch), [{ unit: 5, secs: null }, { unit: 2, secs: 60 }],
    "back at work on the same turn: the current reply's footer comes off (null); the completed one stands");
});

test("plan: a prompt landing at the tail completes the previous turn, whose reply sits before `from`", () => {
  const evs = [user(100), reply(160), user(200)];
  assert.deepEqual(workedFooterPlan(evs, 2, 0, true, epoch), [{ unit: 1, secs: 60 }]);
});

test("plan: replies at or past `from` were just rendered with their footer, so only earlier ones are named", () => {
  const evs = [user(100), reply(160), user(200), tool(205), reply(230)];
  assert.deepEqual(workedFooterPlan(evs, 3, 0, false, epoch), [{ unit: 1, secs: 60 }], "a tool fill at 3 re-rendered 3..4: the turn's reply at 4 is fresh; only the previous turn's reply is patched");
  assert.deepEqual(workedFooterPlan(evs, 1, 0, false, epoch), [], "everything from 1 was rendered: nothing to patch");
});

test("plan: stops at the rendered window's start and after two turns; a lone tool never carries a footer", () => {
  const evs = [user(0), reply(10), user(20), reply(30), user(40), reply(50), user(60), tool(65), reply(70)];
  assert.deepEqual(workedFooterPlan(evs, evs.length, 0, false, epoch), [{ unit: 8, secs: 10 }, { unit: 5, secs: 10 }], "two turns, one reply each; the tool at 7 is not its turn's last reply");
  assert.deepEqual(workedFooterPlan(evs, evs.length, 6, false, epoch), [{ unit: 8, secs: 10 }], "the previous turn's reply is outside the rendered window");
});

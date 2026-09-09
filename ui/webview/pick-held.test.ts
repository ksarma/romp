// A settings pick HELD for live work: the words every surface uses, EXECUTED against ./pick-held (the chat
// line, its hover and the badge tips take them from it; render.ts's call sites are source-pinned in
// effort-switch-pending.test.ts). One case per held kind (effort, permission mode, fast mode, billing) and
// per state (work still running; none left, the pick waiting for the turn to finish), since the round-1
// copy said "Applying max effort when the background work finishes" for every kind, effort or not, and
// "waiting on 0 subagents and 0 background tasks" once the work was done (review round 2, 2026-09-09).
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { pickHeldLine, pickHeldTitle, pickHeldSubject, badgeHeldTip, workPhrase, pickKindName } from "./pick-held";

test("work still running: the line names the pick and the counts, per kind", () => {
  assert.equal(pickHeldLine({ surfaces: ["effort"], subagents: 2, tasks: 1 }),
    "The effort pick is waiting on 2 subagents and 1 background task");
  assert.equal(pickHeldLine({ surfaces: ["mode"], subagents: 1, tasks: 0 }),
    "The permission mode pick is waiting on 1 subagent and 0 background tasks");
  assert.equal(pickHeldLine({ surfaces: ["fast"], subagents: 0, tasks: 3 }),
    "The fast mode pick is waiting on 0 subagents and 3 background tasks");
  assert.equal(pickHeldLine({ surfaces: ["auth"], subagents: 1, tasks: 1 }),
    "The billing pick is waiting on 1 subagent and 1 background task");
  assert.equal(pickHeldTitle({ surfaces: ["effort"], subagents: 2, tasks: 1 }),
    "the session reloads to apply the change when they finish; reloading now would cut them off");
});

test("work done, the settle pending: the line says the pick applies when this turn finishes, per kind", () => {
  for (const [kind, name] of [["effort", "effort"], ["mode", "permission mode"], ["fast", "fast mode"], ["auth", "billing"]]) {
    const h = { surfaces: [kind], subagents: 0, tasks: 0 };
    assert.equal(pickHeldLine(h), `The ${name} pick applies when this turn finishes`, kind);
    assert.doesNotMatch(pickHeldLine(h), /waiting on 0/, "never 'waiting on 0 subagents'");
    assert.match(pickHeldTitle(h), /^the background work has finished; the session reloads .* when the turn that delivers the last result ends$/);
  }
});

test("two or more held picks are named together and the verbs agree", () => {
  assert.deepEqual(pickHeldSubject({ surfaces: ["effort", "auth"], subagents: 1, tasks: 0 }),
    { text: "The effort and billing picks", plural: true });
  assert.equal(pickHeldLine({ surfaces: ["effort", "mode", "fast"], subagents: 1, tasks: 0 }),
    "The effort, permission mode and fast mode picks are waiting on 1 subagent and 0 background tasks");
  assert.equal(pickHeldLine({ surfaces: ["effort", "auth"], subagents: 0, tasks: 0 }),
    "The effort and billing picks apply when this turn finishes");
  // a hold naming no surface (a request that recorded none) still reads as a sentence
  assert.equal(pickHeldLine({ surfaces: [], subagents: 0, tasks: 0 }), "The pending change applies when this turn finishes");
  // a surface this build does not know is named as the kernel sent it, never dropped
  assert.equal(pickKindName("env"), "environment");
  assert.equal(pickKindName("someNewKind"), "someNewKind");
});

test("the badge tip names the pick and the wait, and says the label is what runs now", () => {
  assert.equal(badgeHeldTip("effort", { surfaces: ["effort"], subagents: 1, tasks: 2 }),
    "an effort pick is waiting on 1 subagent and 2 background tasks; the badge shows what the session runs now");
  assert.equal(badgeHeldTip("mode", { surfaces: ["mode"], subagents: 0, tasks: 0 }),
    "a permission mode pick applies when this turn finishes; the badge shows what the session runs now");
  assert.equal(badgeHeldTip("fast", { surfaces: ["fast", "effort"], subagents: 0, tasks: 1 }),
    "a fast mode pick is waiting on 0 subagents and 1 background task; the badge shows what the session runs now");
  assert.equal(workPhrase(1, 1), "1 subagent and 1 background task");
  assert.equal(workPhrase(0, 2), "0 subagents and 2 background tasks");
});

test("no turn open once the work is done: the copy names the session's NEXT turn, per kind and per surface", () => {
  // at zero counts the copy always said "this turn" while the kernel log said the pick waits for the next
  // turn's settle (the stuck-queue regime, where the CLI starts no delivery turn). The kernel sends whether a
  // turn is open (`inflight`); false names the next turn, true keeps this turn, and a payload without the bit
  // (an older kernel) keeps this turn too (review round 3, 2026-09-09)
  for (const [kind, name] of [["effort", "effort"], ["mode", "permission mode"], ["fast", "fast mode"], ["auth", "billing"]]) {
    const idle = { surfaces: [kind], subagents: 0, tasks: 0, inflight: false };
    const open = { surfaces: [kind], subagents: 0, tasks: 0, inflight: true };
    assert.equal(pickHeldLine(idle), `The ${name} pick applies when the next turn finishes`, kind);
    assert.equal(pickHeldLine(open), `The ${name} pick applies when this turn finishes`, kind);
    assert.equal(pickHeldTitle(idle),
      "the background work has finished and no turn is open; the session reloads to apply the change when the session's next turn ends", kind);
    assert.match(pickHeldTitle(open), /when the turn that delivers the last result ends$/, kind);
    assert.equal(badgeHeldTip(kind, idle), `${/^[aeiou]/i.test(name) ? "an" : "a"} ${name} pick applies when the next turn finishes; the badge shows what the session runs now`, kind);
    assert.equal(badgeHeldTip(kind, open), `${/^[aeiou]/i.test(name) ? "an" : "a"} ${name} pick applies when this turn finishes; the badge shows what the session runs now`, kind);
  }
  assert.equal(pickHeldLine({ surfaces: ["effort", "auth"], subagents: 0, tasks: 0, inflight: false }),
    "The effort and billing picks apply when the next turn finishes");
  // work still running: the counts, whichever the phase (the turn bit matters only once the work is done)
  assert.equal(pickHeldLine({ surfaces: ["effort"], subagents: 1, tasks: 0, inflight: false }),
    "The effort pick is waiting on 1 subagent and 0 background tasks");
  assert.equal(badgeHeldTip("effort", { surfaces: ["effort"], subagents: 0, tasks: 2, inflight: false }),
    "an effort pick is waiting on 0 subagents and 2 background tasks; the badge shows what the session runs now");
  // a payload without the bit keeps today's copy
  assert.equal(pickHeldLine({ surfaces: ["effort"], subagents: 0, tasks: 0 }), "The effort pick applies when this turn finishes");
});

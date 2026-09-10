// A settings pick HELD for live work: the words every surface uses, EXECUTED against ./pick-held (the chat
// line, its hover and the badge tips take them from it; render.ts's call sites are source-pinned in
// effort-switch-pending.test.ts). One case per held kind (effort, permission mode, fast mode, billing) and
// per state (work still running; none left, the pick waiting for the turn to finish), since the round-1
// copy said "Applying max effort when the background work finishes" for every kind, effort or not, and
// "waiting on 0 subagents and 0 background tasks" once the work was done (review round 2, 2026-09-09).
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { pickHeldLine, pickHeldTitle, pickHeldSubject, badgeHeldTip, workPhrase, pickKindName, heldUntil, heldRowValue, heldMenuMarks, RUNNING_TAG } from "./pick-held";

const WEBVIEW = path.resolve(process.cwd(), "..", "ui", "webview");

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

test("the refused opt-in's flagless relaunch is a restore, not a pick: the line says the fast mode control is restored", () => {
  // the kernel records the "fast-reset" surface for the relaunch _adopt_fast_state requests when the CLI
  // refuses an armed fast opt-in. Recorded as "fast" until review round 3b (2026-09-09), a held relaunch
  // read "The fast mode pick is waiting on ..." right after the toast had said the pick is back off. The
  // copy never says a pick waits and never mentions a badge: the kernel blanks the fast badge while the
  // refusal's reason stands, so no held mark or tip renders during this hold
  const running = { surfaces: ["fast-reset"], subagents: 1, tasks: 0 };
  const open = { surfaces: ["fast-reset"], subagents: 0, tasks: 0, inflight: true };
  const idle = { surfaces: ["fast-reset"], subagents: 0, tasks: 0, inflight: false };
  const older = { surfaces: ["fast-reset"], subagents: 0, tasks: 0 };
  assert.equal(pickHeldLine(running), "The fast mode control is restored when 1 subagent and 0 background tasks finish");
  assert.equal(pickHeldLine({ surfaces: ["fast-reset"], subagents: 0, tasks: 2 }),
    "The fast mode control is restored when 0 subagents and 2 background tasks finish");
  assert.equal(pickHeldLine(open), "The fast mode control is restored when this turn finishes");
  assert.equal(pickHeldLine(idle), "The fast mode control is restored when the next turn finishes");
  assert.equal(pickHeldLine(older), "The fast mode control is restored when this turn finishes");
  for (const h of [running, open, idle, older]) {
    assert.doesNotMatch(pickHeldLine(h), /pick|badge|waiting/, "never a waiting pick, never a badge");
  }
  // the hover keeps its words: it names the change, not the pick
  assert.equal(pickHeldTitle(running), "the session reloads to apply the change when they finish; reloading now would cut them off");
  // beside a held pick the restore is its own clause after the pick's line, and the verbs agree
  assert.equal(pickHeldLine({ surfaces: ["effort", "fast-reset"], subagents: 2, tasks: 0 }),
    "The effort pick is waiting on 2 subagents and 0 background tasks; the fast mode control is restored with it");
  assert.equal(pickHeldLine({ surfaces: ["effort", "fast-reset", "auth"], subagents: 0, tasks: 0, inflight: false }),
    "The effort and billing picks apply when the next turn finishes; the fast mode control is restored with them");
  assert.deepEqual(pickHeldSubject({ surfaces: ["fast-reset", "mode"], subagents: 1, tasks: 0 }),
    { text: "The permission mode pick", plural: false }, "the subject counts picks only");
  assert.equal(pickKindName("fast-reset"), "fast mode restore");
});

test("one 'until' clause for every surface that says when a held pick applies, and the tooltip rows take the Billing row's shape", () => {
  // the Billing row and the tab menu's Billing sub-line read only the surfaces, so at zero counts they still said
  // "the background work" while the chat line beside them named the turn; the tab tooltip's Mode and Effort rows
  // showed the running value flat, with no sign of the hold the Billing row in the same popover explained
  // (review round 4, 2026-09-10). heldUntil is the one phrase; heldRowValue is the tooltip rows' shape. The
  // callers are pinned here and executed in billing-label.test.ts; render.ts's rows are pinned in
  // effort-switch-pending.test.ts
  assert.equal(heldUntil({ surfaces: ["auth"], subagents: 1, tasks: 0 }), "the background work finishes");
  assert.equal(heldUntil({ surfaces: ["auth"], subagents: 0, tasks: 2, inflight: false }), "the background work finishes",
    "work still running: the counts decide, whatever the turn bit");
  assert.equal(heldUntil({ surfaces: ["auth"], subagents: 0, tasks: 0, inflight: true }), "this turn finishes");
  assert.equal(heldUntil({ surfaces: ["auth"], subagents: 0, tasks: 0, inflight: false }), "the next turn finishes");
  assert.equal(heldUntil({ surfaces: ["auth"], subagents: 0, tasks: 0 }), "this turn finishes", "a payload without the bit keeps this turn");
  // the same clause the chat line ends on once the work is done
  for (const h of [{ surfaces: ["effort"], subagents: 0, tasks: 0, inflight: true }, { surfaces: ["effort"], subagents: 0, tasks: 0, inflight: false }]) {
    assert.ok(pickHeldLine(h).endsWith(`when ${heldUntil(h)}`), pickHeldLine(h));
    assert.ok(badgeHeldTip("effort", h).includes(`applies when ${heldUntil(h)};`), badgeHeldTip("effort", h));
  }
  // the tooltip rows, per kind: the running value, then when the pick takes over
  assert.equal(heldRowValue("high", "effort", { surfaces: ["effort"], subagents: 2, tasks: 0 }),
    "high until the background work finishes, then the picked effort");
  assert.equal(heldRowValue("high", "effort", { surfaces: ["effort"], subagents: 0, tasks: 0, inflight: true }),
    "high until this turn finishes, then the picked effort");
  assert.equal(heldRowValue("Accept edits", "mode", { surfaces: ["mode", "effort"], subagents: 0, tasks: 0, inflight: false }),
    "Accept edits until the next turn finishes, then the picked permission mode");
  assert.equal(heldRowValue("Default", "mode", { surfaces: ["mode"], subagents: 0, tasks: 1 }),
    "Default until the background work finishes, then the picked permission mode");
  // the callers take the clause from here: no second wording anywhere
  const BILLING = fs.readFileSync(path.join(WEBVIEW, "billing-label.ts"), "utf8");
  const RENDER = fs.readFileSync(path.join(WEBVIEW, "render.ts"), "utf8");
  assert.match(BILLING, /import \{ heldUntil, type PickHeld \} from "\.\/pick-held";/);
  assert.match(BILLING, /const until = heldUntil\(f\.pickHeld!\);\s*\n\s*if \(now && f\.authLive === f\.auth\) return `\$\{then\} \(the reload waits until \$\{until\}\)`;\s*\n\s*return now \? `\$\{now\} until \$\{until\}, then \$\{then\}` : `\$\{then\} applies when \$\{until\}`;/);
  assert.match(BILLING, /if \(billingHeld\(f\)\) return `waiting until \$\{heldUntil\(f\.pickHeld!\)\}`;/);
  assert.doesNotMatch(BILLING, /until the background work finishes|waiting for background work/, "the old fixed wording is gone");
  assert.match(RENDER, /heldRowValue\(now, kind, held, pickedOf\(kind\)\)/);
});

test("the tooltip rows name the PICKED value when the status carries it, and fall back to the kind when it does not", () => {
  // the status reports what the session RUNS beside the hold, so until review round 5 no payload carried the picked
  // strings and the rows said "then the picked effort"; pickHeld.picked names it now ("high until ..., then max"), and
  // a payload from an older kernel keeps the kind
  const h = { surfaces: ["effort"], subagents: 2, tasks: 0, picked: { effort: "max" } };
  assert.equal(heldRowValue("high", "effort", h, h.picked.effort), "high until the background work finishes, then max");
  assert.equal(heldRowValue("Normal", "mode", { surfaces: ["mode"], subagents: 0, tasks: 0, inflight: true, picked: { mode: "bypassPermissions" } }, "Bypass"),
    "Normal until this turn finishes, then Bypass", "the caller prettifies the mode, as it does the running one");
  assert.equal(heldRowValue("high", "effort", { surfaces: ["effort"], subagents: 2, tasks: 0 }), "high until the background work finishes, then the picked effort");
  assert.equal(heldRowValue("high", "effort", h, undefined), "high until the background work finishes, then the picked effort");
  assert.equal(heldRowValue("high", "effort", h, ""), "high until the background work finishes, then the picked effort");
});

test("one menu convention while a pick is held: the check on the picked value, a running tag on the value the session runs", () => {
  // the statusline's effort and mode menus check-marked the RUNNING value during a hold (they never read the hold) while
  // the tab menu's Billing flyout check-marked the PICKED side (review round 5, ui-2): one hold, two readings on one
  // screen. heldMenuMarks is the one rule for every menu: not held, null (the menu marks its current value as before)
  const held = { surfaces: ["effort", "mode", "auth"], subagents: 1, tasks: 0, picked: { effort: "max", mode: "bypassPermissions", auth: "key" } };
  assert.deepEqual(heldMenuMarks("effort", held, "high"), { current: "max", running: "high" });
  assert.deepEqual(heldMenuMarks("mode", held, "default"), { current: "bypassPermissions", running: "default" });
  assert.deepEqual(heldMenuMarks("auth", held, "login"), { current: "key", running: "login" });
  assert.equal(heldMenuMarks("fast", held, "off"), null, "a kind not held: the menu's own current rule");
  assert.equal(heldMenuMarks("effort", null, "high"), null);
  assert.equal(heldMenuMarks("effort", undefined, "high"), null);
  assert.equal(heldMenuMarks("effort", { surfaces: [], subagents: 0, tasks: 0 }, "high"), null);
  // the picked side can equal the running side (a billing pick the CLI already bills): the same row wears both marks
  assert.deepEqual(heldMenuMarks("auth", { surfaces: ["auth"], subagents: 1, tasks: 0, picked: { auth: "key" } }, "key"), { current: "key", running: "key" });
  // an older kernel's payload carries no picked value: no row is checked, the running one is still tagged
  assert.deepEqual(heldMenuMarks("effort", { surfaces: ["effort"], subagents: 1, tasks: 0 }, "high"), { current: "", running: "high" });
  assert.deepEqual(heldMenuMarks("auth", { surfaces: ["auth"], subagents: 1, tasks: 0, picked: {} }, ""), { current: "", running: "" }, "no report yet: nothing runs to tag");
  assert.equal(RUNNING_TAG, "running");
});

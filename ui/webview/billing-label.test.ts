// The Billing label's cases, EXECUTED against ./billing-label (the hover row and the tab menu's Billing
// item both take their words from it); the two call sites are source-pinned in auth-selector.test.ts.
//
// The bug these pin (the user 2026-09-09): on a box whose sessions authenticate through Claude Code's
// apiKeyHelper, romp holds no key, so the seeded intent read "login" for every unpicked session, and the
// row showed plain "Login" (the kernel's live merge never put the CLI's report on the wire); had the report
// reached it, the old wording would have shown "Login picked, but the CLI reports the API key" for a default
// nobody picked. The CLI's report leads now, and only an EXPLICIT pick it contradicts is worded as a
// contradiction. The new-session picker's Billing row takes its decision from the same module.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { billingRowText, billingSubText, billingSide, billingContradicted, pickerBillingRow, pickerBillingTitle, billingPickUnavailable, billingFellTo } from "./billing-label";

const ROOT = path.resolve(process.cwd(), "..");
const KERNEL = fs.readFileSync(path.join(ROOT, "kernel", "kernel.py"), "utf8");
const BILLING = fs.readFileSync(path.join(ROOT, "ui", "webview", "billing-label.ts"), "utf8");

test("an unpicked session whose CLI reports the key reads 'API key', whatever the seeded intent", () => {
  // the apiKeyHelper box: the intent was seeded "login" (no key of romp's), the CLI found the key
  const f = { auth: "login", authLive: "key", authPicked: false, authAcct: "user@example.com" };
  assert.equal(billingRowText(f), "API key");
  assert.equal(billingSubText(f), "API key");
  assert.equal(billingContradicted(f), false, "a default that guessed wrong is not a contradiction");
});

test("an unpicked session with no report yet shows the seeded intent", () => {
  assert.equal(billingRowText({ auth: "key", authLive: "", authPicked: false }), "API key",
    "the box declaration seeded the key: the row says so before any init");
  assert.equal(billingRowText({ auth: "login", authPicked: false, authAcct: "user@example.com" }),
    "Login (user@example.com)", "a login intent names the account");
  assert.equal(billingSubText({ auth: "login", authPicked: false }), "Login");
});

test("an unpicked session whose CLI reports the login names the account", () => {
  const f = { auth: "key", authLive: "login", authPicked: false, authAcct: "user@example.com" };
  assert.equal(billingRowText(f), "Login (user@example.com)");
  assert.equal(billingSubText(f), "Login (user@example.com)");
});

test("a login PICK the CLI landed on the key is the warning, on both surfaces", () => {
  const f = { auth: "login", authLive: "key", authPicked: true, authAcct: "user@example.com" };
  assert.equal(billingRowText(f), "⚠ Login picked, but the CLI reports the API key; this session bills that");
  assert.equal(billingSubText(f), "⚠ CLI reports API key");
  assert.equal(billingContradicted(f), true);
  // and the other way round
  const g = { auth: "key", authLive: "login", authPicked: true };
  assert.equal(billingRowText(g), "⚠ API key picked, but the CLI reports the login; this session bills that");
  assert.equal(billingSubText(g), "⚠ CLI reports login");
});

test("a pick the CLI confirmed reads plainly", () => {
  assert.equal(billingRowText({ auth: "key", authLive: "key", authPicked: true }), "API key");
  assert.equal(billingSubText({ auth: "key", authLive: "key", authPicked: true }), "API key");
  assert.equal(billingRowText({ auth: "login", authLive: "login", authPicked: true, authAcct: "user@example.com" }),
    "Login (user@example.com)");
});

test("a billing pick HELD for the session's live work says so, and names what bills meanwhile", () => {
  // the switch reconnects, and the reconnect waits for the session's subagents and background tasks
  // (2026-09-09); the status's one held marker (pickHeld) carries it. Until review round 2 the row read
  // "Login (applying, not confirmed yet)" and the sub-line "applying…" for the whole hold, though nothing
  // was applying; the CLI's last report still describes the running process, so it leads
  const f = { auth: "login", authLive: "key", authPicked: true, authPending: true,
              pickHeld: { surfaces: ["auth"], subagents: 1, tasks: 0 } };
  assert.equal(billingRowText(f), "API key until the background work finishes, then Login");
  assert.equal(billingSubText(f), "waiting until the background work finishes");
  // no report to name: the pick is named as what waits, never as the fact
  const g = { auth: "key", authLive: "", authPicked: true, authPending: true, pickHeld: { surfaces: ["auth"], subagents: 0, tasks: 2 } };
  assert.equal(billingRowText(g), "API key applies when the background work finishes");
  assert.equal(billingSubText(g), "waiting until the background work finishes");
  // the work is done and the pick waits for a turn to finish (review round 4, 2026-09-10): the row and the
  // sub-line name the turn, the way the chat line does, through pick-held.ts's one clause (heldUntil); until
  // round 4 both read only the surfaces and said "the background work" for a wait that can last indefinitely
  // (authPending stands from the pick to the landing). Both forms of the row: with a report and without
  const open = { ...f, pickHeld: { surfaces: ["auth"], subagents: 0, tasks: 0, inflight: true } };
  assert.equal(billingRowText(open), "API key until this turn finishes, then Login");
  assert.equal(billingSubText(open), "waiting until this turn finishes");
  const idle = { ...f, pickHeld: { surfaces: ["auth"], subagents: 0, tasks: 0, inflight: false } };
  assert.equal(billingRowText(idle), "API key until the next turn finishes, then Login");
  assert.equal(billingSubText(idle), "waiting until the next turn finishes");
  const older = { ...f, pickHeld: { surfaces: ["auth"], subagents: 0, tasks: 0 } };
  assert.equal(billingRowText(older), "API key until this turn finishes, then Login", "a payload without the bit keeps this turn");
  assert.equal(billingSubText(older), "waiting until this turn finishes");
  assert.equal(billingRowText({ ...g, pickHeld: { surfaces: ["auth"], subagents: 0, tasks: 0, inflight: false } }),
    "API key applies when the next turn finishes");
  assert.equal(billingRowText({ ...g, pickHeld: { surfaces: ["auth"], subagents: 0, tasks: 0, inflight: true } }),
    "API key applies when this turn finishes");
  assert.equal(billingSubText({ ...g, pickHeld: { surfaces: ["auth"], subagents: 0, tasks: 0, inflight: false } }),
    "waiting until the next turn finishes");
  // and the clause is pick-held.ts's, never a second wording here
  assert.match(BILLING, /import \{ heldUntil, type PickHeld \} from "\.\/pick-held";/);
  assert.doesNotMatch(BILLING, /until the background work finishes|waiting for background work/);
  // the picked side EQUALS the side the CLI reports (review round 5, ui-1): the kernel compares a billing pick against
  // the side that launched, never against the report, so a key pick on a process that launched plain and found the
  // helper's key is held with authLive "key" already. The row said "API key until the background work finishes, then
  // API key"; it names the side once now and says the reload waits. The sub-line names no side and is unchanged
  const sameKey = { auth: "key", authLive: "key", authPicked: true, authPending: true,
                    pickHeld: { surfaces: ["auth"], subagents: 1, tasks: 0 } };
  assert.equal(billingRowText(sameKey), "API key (the reload waits until the background work finishes)");
  assert.equal(billingSubText(sameKey), "waiting until the background work finishes");
  const sameLogin = { auth: "login", authLive: "login", authPicked: true, authPending: true, authAcct: "user@example.com",
                      pickHeld: { surfaces: ["auth"], subagents: 0, tasks: 0, inflight: true } };
  assert.equal(billingRowText(sameLogin), "Login (user@example.com) (the reload waits until this turn finishes)");
  assert.equal(billingSubText(sameLogin), "waiting until this turn finishes");
  assert.doesNotMatch(billingRowText(sameKey), /applying/, "nothing is applying during a hold (round 2 retired that wording for holds)");
  // a hold on some OTHER pick leaves the billing words alone, and so does the armed reconnect (no hold)
  const h = { auth: "login", authLive: "", authPicked: true, authPending: true, pickHeld: { surfaces: ["effort"], subagents: 1, tasks: 0 } };
  assert.equal(billingRowText(h), "Login (applying, not confirmed yet)");
  assert.equal(billingSubText(h), "applying…");
  assert.equal(billingSubText({ auth: "login", authPending: true, pickHeld: null }), "applying…");
});

test("a pick before its init lands shows the pick as the intent, never as a contradiction", () => {
  // a real, open-ended window: spawn writes the reg's auth from a remembered pick and authLive stays ""
  // until the first init's report (a dormant session holds this state indefinitely). Dropping the
  // report guard in billingContradicted would word every such session as "Login picked, but the CLI
  // reports the login" until its init; the shipped cases never exercised it (review round 1, 2026-09-09).
  const f = { auth: "login", authPicked: true, authLive: "", authAcct: "user@example.com" };
  assert.equal(billingRowText(f), "Login (user@example.com)");
  assert.equal(billingSubText(f), "Login (user@example.com)");
  assert.equal(billingContradicted(f), false, "no report yet: nothing to contradict");
  const g = { auth: "key", authPicked: true };   // the dormant row before any init: authLive absent
  assert.equal(billingRowText(g), "API key");
  assert.equal(billingSubText(g), "API key");
  assert.equal(billingContradicted(g), false);
  // and a pick whose applying reconnect is in flight still says so
  assert.equal(billingRowText({ auth: "login", authPicked: true, authLive: "", authPending: true }),
    "Login (applying, not confirmed yet)");
  assert.equal(billingSubText({ auth: "login", authPicked: true, authLive: "", authPending: true }), "applying…");
});

test("the picker's Billing row shows whenever the host can name what a new session bills, buttons only for two real choices", () => {
  // both real: buttons, nothing written out
  assert.deepEqual(pickerBillingRow({ login: true, key: true, acct: "user@example.com", default: "key" }),
    { show: true, both: true, fixed: "" });
  // a login alone: written out, naming the account when known
  // a keyed box under a remembered login pick with no login signed in: the spawn seeds the login, so the row says so
  assert.deepEqual(pickerBillingRow({ login: false, key: true, acct: "", default: "login" }),
    { show: true, both: false, fixed: "Login" }, "the written-out choice follows default, not the helper's key");
  assert.deepEqual(pickerBillingRow({ login: true, key: false, acct: "user@example.com", default: "login" }),
    { show: true, both: false, fixed: "Login (user@example.com)" });
  assert.equal(pickerBillingRow({ login: true, default: "login" }).fixed, "Login");
  // a key of romp's alone
  assert.deepEqual(pickerBillingRow({ login: false, key: true, acct: "", default: "key" }),
    { show: true, both: false, fixed: "API key" });
  // the apiKeyHelper box (W2, review round 1): neither credential of romp's, the host declares the key;
  // the gate used to require a login or a key of romp's, so this box, the one the fix is for, had no row
  assert.deepEqual(pickerBillingRow({ login: false, key: false, acct: "", default: "key" }),
    { show: true, both: false, fixed: "API key" });
  // a login beside a declared key: no buttons (romp cannot pick the helper's key), the declared side written out
  assert.deepEqual(pickerBillingRow({ login: true, key: false, acct: "user@example.com", default: "key" }),
    { show: true, both: false, fixed: "API key" });
  // nothing the host can vouch for: hidden, never a fabricated Login
  assert.deepEqual(pickerBillingRow({ login: false, key: false, acct: "", default: "login" }),
    { show: false, both: false, fixed: "" });
  assert.equal(pickerBillingRow(null).show, false, "no availability reply yet (an older kernel never sends one)");
});

test("the written-out row's hover names why the other side is off, in the kernel's reason, keyed on the helper as upstream keys it", () => {
  // upstream #1147 (the user 2026-09-08): the picker never disappears, and the side it cannot offer says why
  assert.equal(pickerBillingTitle({ login: false, key: true, default: "key" }), "Login unavailable: no Claude login signed in on this machine");
  assert.equal(pickerBillingTitle({ login: false, key: true, default: "key", loginWhy: "X" }), "Login unavailable: X");
  assert.equal(pickerBillingTitle({ login: true, key: false, default: "login", keyWhy: "Y" }), "API key unavailable: Y");
  assert.equal(pickerBillingTitle({ login: true, key: false, default: "login" }), "API key unavailable: no apiKeyHelper configured");
  // a login beside a declared key (ROMP_EXPECTED_AUTH=key, no helper): the row writes out the declared side, and the
  // hover is what upstream renders for this reply, that no helper is configured. The 2026-09-09 fold's resolve had
  // returned "" here; no fork test had pinned that, so upstream's rendering stands (slice 3)
  assert.equal(pickerBillingTitle({ login: true, key: false, default: "key" }), "API key unavailable: no apiKeyHelper configured");
  // the same declaration with no login either: the fork shows the row where upstream hides it; the hover is the same
  assert.equal(pickerBillingTitle({ login: false, key: false, default: "key" }), "API key unavailable: no apiKeyHelper configured");
  assert.equal(pickerBillingTitle({ login: true, key: true }), "", "buttons, no hover");
  assert.equal(pickerBillingTitle({ login: false, key: false, default: "login" }), "", "a hidden row has no hover");
  assert.equal(pickerBillingTitle(null), "");
});

test("a pick this box cannot bill is the kernel's word, never inferred, and the row says where the launch went", () => {
  // authPickUnavailable names an EXPLICIT pick (the kernel's pick_unavailable); a seeded default never carries it
  assert.equal(billingPickUnavailable({ auth: "login", authPickUnavailable: "login" }), true);
  assert.equal(billingPickUnavailable({ auth: "login", authPickUnavailable: "" }), false);
  assert.equal(billingPickUnavailable({ auth: "login", authAvail: { login: false, key: true } }), false, "availability alone is no verdict on the pick");
  assert.equal(billingPickUnavailable({ auth: "", authPickUnavailable: "" }), false);
  // the fall is authPickFell when the kernel sent it (the launch's own decision; "" = went out as picked)
  assert.equal(billingFellTo({ auth: "login", authPickUnavailable: "login", authPickFell: "key" }), "key");
  assert.equal(billingFellTo({ auth: "key", authPickUnavailable: "key", authPickFell: "login" }), "login");
  assert.equal(billingFellTo({ auth: "login", authPickUnavailable: "login", authPickFell: "", authAvail: { login: false, key: true } }), "");
  // an older kernel without the field: inferred from the other side existing, as the sub-line always did
  assert.equal(billingFellTo({ auth: "login", authPickUnavailable: "login", authAvail: { login: false, key: true } }), "key");
  assert.equal(billingFellTo({ auth: "key", authPickUnavailable: "key", authAvail: { login: true, key: false } }), "login");
  assert.equal(billingFellTo({ auth: "login", authPickUnavailable: "login", authAvail: { login: false, key: false } }), "");
  assert.equal(billingFellTo({ auth: "login", authPickUnavailable: "login" }), "key", "no availability at all reads as both sides existing");
  assert.equal(billingFellTo({ auth: "login", authPickUnavailable: "" }), "", "a pick the box can bill (or none) never fell");
  // the row and the sub-line, in upstream's words: the kernel's reason for the picked side, then the fall
  const fell = { auth: "login", authPickUnavailable: "login", authPickFell: "key", authAvail: { login: false, key: true, loginWhy: "no Claude login signed in on this machine" } };
  assert.equal(billingRowText(fell), "⚠ Login picked, but no Claude login signed in on this machine — this session bills the API key");
  assert.equal(billingSubText(fell), "⚠ login unavailable, billing API key");
  const fellKey = { auth: "key", authPickUnavailable: "key", authPickFell: "login", authAvail: { login: true, key: false, keyWhy: "no apiKeyHelper configured" } };
  assert.equal(billingRowText(fellKey), "⚠ API key picked, but no apiKeyHelper configured — this session bills the login");
  assert.equal(billingSubText(fellKey), "⚠ API key unavailable, billing login");
  const stood = { auth: "login", authPickUnavailable: "login", authPickFell: "", authAvail: { login: false, key: false } };
  assert.equal(billingRowText(stood), "⚠ Login picked, but this machine cannot bill it — nothing to fall to, so the launch went out as picked");
  assert.equal(billingSubText(stood), "⚠ login unavailable");
  // precedence: pending > unavailable > contradicted > plain
  assert.equal(billingRowText({ ...fell, authPending: true }), "Login (applying, not confirmed yet)", "a pending switch still wins");
  assert.equal(billingSubText({ ...fell, authPending: true }), "applying…");
  const both = { auth: "login", authPickUnavailable: "login", authPickFell: "key", authLive: "key", authPicked: true };
  assert.equal(billingRowText(both), "⚠ Login picked, but this machine cannot bill it — this session bills the API key",
    "the kernel's own account of the fall outranks the contradiction reading of the same landing");
  assert.equal(billingSubText(both), "⚠ login unavailable, billing API key");
  assert.equal(billingRowText({ auth: "login", authPickUnavailable: "", authPickFell: "", authLive: "login", authPicked: true, authAcct: "user@example.com" }),
    "Login (user@example.com)", "a pick the box bills reads plainly");
});

test("a pending switch reads as pending, never as applied fact, and outranks a stale report (T124)", () => {
  const f = { auth: "key", authLive: "login", authPicked: true, authPending: true };
  assert.equal(billingRowText(f), "API key (applying, not confirmed yet)");
  assert.equal(billingSubText(f), "applying…");
});

test("no side at all is no label (the caller gates the row on auth)", () => {
  assert.equal(billingSide(""), "");
  assert.equal(billingRowText({}), "");
  assert.equal(billingContradicted({ authLive: "key", authPicked: true }), false, "no intent, nothing to contradict");
});

test("the kernel's session payload carries authPicked beside auth and authLive", () => {
  assert.ok(KERNEL.includes('"authPicked": bool(tm.get("authPicked")),'), "build_session's Billing fields");
  assert.ok(KERNEL.includes('"authLive": st.get("authLive", ""),'), "the live merge forwards the CLI's report");
  assert.ok(KERNEL.includes('"authPicked": bool(st.get("authPicked")),'), "and the pick flag");
});

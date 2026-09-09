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
import { billingRowText, billingSubText, billingSide, billingContradicted, pickerBillingRow } from "./billing-label";

const ROOT = path.resolve(process.cwd(), "..");
const KERNEL = fs.readFileSync(path.join(ROOT, "kernel", "kernel.py"), "utf8");

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

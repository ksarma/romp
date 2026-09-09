// The Billing label's cases, EXECUTED against ./billing-label (the hover row and the tab menu's Billing
// item both take their words from it); the two call sites are source-pinned in auth-selector.test.ts.
//
// The bug these pin (the user 2026-09-09): on a box whose sessions authenticate through Claude Code's
// apiKeyHelper, romp holds no key, so the seeded intent read "login" for every unpicked session, and the
// row either showed plain "Login" (no report on the wire) or "Login picked, but the CLI reports the API
// key" when nobody had picked anything. The CLI's report leads now, and only an EXPLICIT pick it
// contradicts is worded as a contradiction.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { billingRowText, billingSubText, billingSide, billingContradicted } from "./billing-label";

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

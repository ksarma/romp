// The Billing flyout on a one-auth box (the user 2026-09-08): both choices are ALWAYS listed, the one this
// box cannot bill is greyed with its reason in the hover and inert, and a pick that fell to the other side
// says so in the sub-line. render.ts has no jsdom harness, so these are source pins, the same idiom as
// auth-selector.test.ts; the kernel/backend halves are pinned in tests/test_session_auth.py.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { billingRowText, billingSubText, billingFellTo } from "./billing-label";

const ROOT = path.resolve(process.cwd(), "..");
const RENDER = fs.readFileSync(path.join(ROOT, "ui", "webview", "render.ts"), "utf8");
const STYLES = fs.readFileSync(path.join(ROOT, "ui", "webview", "styles.css"), "utf8");
const KERNEL = fs.readFileSync(path.join(ROOT, "kernel", "kernel.py"), "utf8");
const BACKEND = fs.readFileSync(path.join(ROOT, "kernel", "sdk_backend.py"), "utf8");

test("the Billing submenu renders on availability, not only when both sides exist", () => {
  assert.match(RENDER, /if \(st && st\.auth && \(st\.authAvail \|\| st\.authBoth\)\) \{/);
  assert.match(RENDER, /const avail: AuthAvail = st\.authAvail \|\| \{ login: true, key: true \};/);
});

test("both options are listed; the unavailable one is greyed, titled with its reason, and inert", () => {
  assert.match(RENDER, /value: "login", why: avail\.login \? "" : \(avail\.loginWhy \|\| "no Claude login signed in on this machine"\)/);
  assert.match(RENDER, /value: "key", why: avail\.key \? "" : \(avail\.keyWhy \|\| "no apiKeyHelper configured"\)/);
  // (the check reads `current`, the held-pick mark's resolution of st.auth, and a running tag rides beside it; the
  // disabled class is appended whatever the hold says: auth-selector.test.ts pins the held half)
  assert.match(RENDER, /\(current \? " current" : ""\) \+ \(running \? " running" : ""\) \+ \(c\.why \? " disabled" : ""\)/);
  assert.match(RENDER, /opt\.title = c\.why;\s*\n\s*opt\.setAttribute\("aria-disabled", "true"\);/);
  assert.match(RENDER, /if \(c\.why\) return;\s*\/\/ a disabled option posts nothing/);
  // the click handler posts setAuth only past that guard
  const i = RENDER.indexOf('if (c.why) return;');
  const j = RENDER.indexOf('vscodeApi.postMessage({ type: "setAuth", id, value: c.value })', i);
  assert.ok(i > 0 && j > i, "setAuth is posted only after the disabled guard");
  assert.match(STYLES, /\.ctx-sub \.ctx-item\.disabled \{ opacity: 0\.45; cursor: default; \}/);
});

test("a pick that fell to the other side is said in the sub-line, from the kernel's word on the fall", () => {
  // The fork renders the sub-line and the hover row through billing-label.ts (one module decides the copy, so the two
  // surfaces cannot drift; the 2026-09-09 fold, ruling C), so upstream's inline pins run here as executed cases of
  // that module, in upstream's words. render.ts calls billingSubText/billingRowText (auth-selector.test.ts pins the calls).
  assert.equal(billingSubText({ auth: "login", authPickUnavailable: "login", authPickFell: "key" }), "⚠ login unavailable, billing API key");
  assert.equal(billingSubText({ auth: "key", authPickUnavailable: "key", authPickFell: "" }), "⚠ API key unavailable");
  // the fall itself is the kernel's authPickFell (the launch's own decision), read by BOTH surfaces; an older
  // kernel without the field is inferred the way the sub-line always did (the other side exists)
  assert.match(RENDER, /authPickUnavailable\?: string; authPickFell\?: string;/);
  assert.equal(billingFellTo({ auth: "login", authPickUnavailable: "login", authPickFell: "key" }), "key", "the kernel's word wins");
  assert.equal(billingFellTo({ auth: "login", authPickUnavailable: "login", authPickFell: "", authAvail: { login: false, key: true } }), "",
    "an empty authPickFell is the kernel saying the launch went out as picked, whatever the availability");
  assert.equal(billingFellTo({ auth: "login", authPickUnavailable: "login", authAvail: { login: false, key: true } }), "key", "an older kernel: inferred from the other side existing");
  assert.equal(billingFellTo({ auth: "login", authPickUnavailable: "login", authAvail: { login: false, key: false } }), "", "…and nothing to fall to");
  assert.equal(billingFellTo({ auth: "login", authPickUnavailable: "", authAvail: { login: false, key: true } }), "", "a pick this box can bill (or no pick) never fell");
  assert.equal(billingRowText({ auth: "login", authPickUnavailable: "login", authPickFell: "key", authAvail: { login: false, key: true, loginWhy: "no Claude login signed in on this machine" } }),
    "⚠ Login picked, but no Claude login signed in on this machine — this session bills the API key");
  assert.equal(billingRowText({ auth: "key", authPickUnavailable: "key", authPickFell: "login", authAvail: { login: true, key: false, keyWhy: "no apiKeyHelper configured" } }),
    "⚠ API key picked, but no apiKeyHelper configured — this session bills the login");
  assert.equal(billingRowText({ auth: "login", authPickUnavailable: "login", authPickFell: "", authAvail: { login: false, key: false } }),
    "⚠ Login picked, but this machine cannot bill it — nothing to fall to, so the launch went out as picked");
});

test("the kernel's status carries authAvail with reasons, and authBoth only for older clients", () => {
  assert.match(KERNEL, /"authAvail": _auth_avail_status\(\),/);
  assert.match(KERNEL, /def _auth_avail_status\(\):/);
  assert.match(KERNEL, /out\["loginWhy"\] = jd\._cred\.WHY_MANAGED_HELPER if managed else jd\._cred\.WHY_NO_LOGIN/);
  assert.match(KERNEL, /out\["keyWhy"\] = jd\._cred\.WHY_NO_HELPER/);
  // the default falls to the side that exists, in BOTH directions: the backend's one rule (SdkBackend.new_session_auth ->
  // seeded_auth with pick_unavailable, symmetric), which the kernel's picker default reads and never re-decides
  // (the 2026-09-09 fold, ruling C over slice-2 ruling 10)
  assert.match(KERNEL, /default = _unpicked_default\(\)\s*\n\s*out = \{"login": login_ok, "key": key,/);
  assert.match(BACKEND, /return new_session_auth\(self\.state_dir, self\.key_available, self\.pick_unavailable\)/);
  assert.match(BACKEND, /if unavailable is not None:\s*\n\s*return "" if unavailable\(a\) else a/);
});

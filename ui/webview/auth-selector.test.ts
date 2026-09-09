// Per-session BILLING (the user 2026-08-08, reshaped 2026-08-09): pick, per session, whether it bills
// the Claude login or the API key the manager's environment carries — and SEE the fact everywhere even
// when there is nothing to pick.
//   * the new-session picker's Billing row is ALWAYS there for an SDK session: segmented buttons when
//     the selected host's own sessionList reply (authAvail) says both choices are real, and the same
//     spot writes the single choice out as plain text when only one is (a fact, not a control);
//   * the SWITCHING control is a Billing submenu in the chat tab's right-click menu (moved from a
//     statusline badge, the user 2026-08-09): it exists only when the machine offers both
//     (st.authBoth), posting the same setAuth; the sub-line says "applying…" while the reconnect
//     is pending;
//   * the chat tab's hover carries the fact as a Billing row whenever the backend reports it
//     (st.auth rides ungated now), naming WHICH login account (st.authAcct) beside 'Login'.
// The key is labelled plainly 'API key' — NO key material anywhere: not the key, not even a last-4
// tail (the user 2026-08-08, evening: a tail is still key material; hosts are told apart by name).
// No jsdom harness → source pins (the repo convention).
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const ROOT = path.resolve(process.cwd(), "..");
const RENDER = fs.readFileSync(path.join(ROOT, "ui", "webview", "render.ts"), "utf8");
const INTENT = fs.readFileSync(path.join(ROOT, "vscode-extension", "src", "pipe-intent.ts"), "utf8");
const BILLING = fs.readFileSync(path.join(ROOT, "ui", "webview", "billing-label.ts"), "utf8");

test("the picker's Billing row shows for SDK whenever availability is known", () => {
  // one thing the host can name is enough to SHOW the row (the user 2026-08-09): a login, a key of romp's,
  // or a declared key (review round 1, 2026-09-09: the apiKeyHelper box has neither credential of romp's).
  // The decision is billing-label.ts's pickerBillingRow, executed in billing-label.test.ts; the both-test
  // only decides buttons vs written-out text; the backend toggle still re-decides the row (tmux CLIs live
  // in the tmux server's env, which the kernel doesn't control)
  // (pickerBackendChoice reads the Backend row's chip alone since tab groups, 2026-09-04 — the Tags
  // row wears the same chip grammar, and a selected tag must never read as the backend)
  assert.match(RENDER, /const row = pickerBillingRow\(a\);\s*\n\s*const show = !pickMode && row\.show && pickerBackendChoice\(\) === "sdk";/);
  assert.match(BILLING, /const show = !!\(a && \(a\.login \|\| a\.key \|\| a\.default === "key"\)\);/);
  assert.match(RENDER, /function pickerBackendChoice\(\): string \{\s*\n\s*const beSel = document\.querySelector\("#picker \.picker-backend:not\(\.picker-host\):not\(\.picker-auth\):not\(\.picker-tags\) \.picker-be-opt\.sel"\) as HTMLElement \| null;\s*\n\s*return beSel\?\.dataset\.be \|\| loadSettings\(\)\.backend;/);
  assert.match(RENDER, /const both = row\.both;/);
  assert.match(BILLING, /const both = !!\(a && a\.login && a\.key\);/);
  assert.match(RENDER, /auWrap\.style\.display = "none";\s*\/\/ hidden until a sessionList reply carries authAvail/);
  assert.match(RENDER, /beWrap\.addEventListener\("click", \(\) => \{ syncPickerAuth\(\); syncPickerTags\(\); \}\);/);   // the Tags row follows the backend pick too (tab groups)
  // a host switch clears the availability — the choices on screen belong to the OLD host
  assert.match(RENDER, /pickerAuthAvail = null;\s*\n\s*syncPickerAuth\(\);/);
  // …and the reply that re-arms it is dropped-if-stale by the same host check the list itself uses
  assert.match(RENDER, /pickerAuthAvail = \(m\.authAvail && typeof m\.authAvail === "object"\) \? m\.authAvail : null;/);
});

test("one real choice renders WRITTEN OUT in the buttons' place, naming the login account", () => {
  // the buttons hide, the fixed span shows the single applying choice as plain text (the user
  // 2026-08-09: informative, never a one-option selector) — Login named by its account when known
  assert.match(RENDER, /wrap\.querySelectorAll\("\.picker-be-opt"\)\.forEach\(\(x\) => \(\(x as HTMLElement\)\.style\.display = both \? "" : "none"\)\);/);
  assert.match(RENDER, /fixed\.style\.display = both \? "none" : "";/);
  // the written-out choice is the key when romp holds one OR when the host declares its sessions bill one
  // (a.default reads "key" under ROMP_EXPECTED_AUTH=key on an apiKeyHelper box, which holds no key of romp's),
  // else the login named by its account: pickerBillingRow's `fixed`, executed in billing-label.test.ts
  assert.match(RENDER, /fixed\.textContent = row\.fixed;/);
  assert.match(BILLING, /const fixed = !show \|\| both \? "" : \(\(a!\.key \|\| a!\.default === "key"\) \? "API key" : billingSide\("login", a!\.acct\)\);/);
  assert.match(RENDER, /import \{ billingRowText, billingSubText, pickerBillingRow \} from "\.\/billing-label";/);
  assert.match(RENDER, /const auFixed = el\("span", "picker-auth-fixed"\);/);
  // in button mode, the Login button's hover names WHICH account
  assert.match(RENDER, /if \(loginBtn && a!\.acct\) loginBtn\.title = `Bill this session to the machine's Claude login \(\$\{a!\.acct\}\)\.`;/);
});

test("the pick rides createSession, omitted when the row is hidden or written-out", () => {
  assert.match(RENDER, /function pickerAuthChoice\(\): string/);
  // (the picker's Tags row rides the same create since tab groups, 2026-09-04 — omitted the same way when nothing is picked)
  assert.match(RENDER, /host: hostSel, \.\.\.\(auth \? \{ auth \} : \{\}\), \.\.\.\(tags\.length \? \{ tags \} : \{\}\) \}\);/);
  assert.match(RENDER, /interface CreateReq \{ name: string; backend: string; dir: string; host: string; auth\?: string; tags\?: string\[\] \}/);
  // text mode sends nothing — the kernel default IS the single choice, and a stale .sel from a
  // previously-selected both-offering host must not ride along
  assert.match(RENDER, /if \(!sel \|\| sel\.style\.display === "none"\) return "";/);
  // fresh open forgets last time's pick + availability; the local reply re-arms it
  assert.match(RENDER, /auWrapEl\.querySelectorAll\("\.picker-be-opt"\)\.forEach\(\(x\) => x\.classList\.remove\("sel"\)\);/);
  // the default selection comes from the host's own answer, once, not on every re-sync
  assert.match(RENDER, /const def = a!\.default === "key" \? "key" : "login";/);
});

test("the switching CONTROL is the tab menu's Billing submenu, gated on both", () => {
  // moved OUT of the statusline (the user 2026-08-09): no auth badge kind survives there
  assert.match(RENDER, /type MetaKind = "mode" \| "model" \| "effort" \| "fast";/);
  assert.doesNotMatch(RENDER, /metaButton\("auth"/);
  assert.doesNotMatch(RENDER, /AUTH_CHOICES/);
  // …and INTO showTabMenu: only when the machine offers both choices does the item exist at all
  // (a one-auth machine keeps the fact on the tab hover, never a dead selector)
  assert.match(RENDER, /if \(st && st\.auth && st\.authBoth\) \{/);
  // the flyout offers the two plain labels — Login named by its account, the key by NO material —
  // with the session's current choice check-marked
  assert.match(RENDER, /\{ label: st\.authAcct \? `Login \(\$\{st\.authAcct\}\)` : "Login", value: "login" \},/);
  assert.match(RENDER, /\{ label: "API key", value: "key" \}\]/);
  assert.match(RENDER, /el\("div", "ctx-item" \+ \(st\.auth === c\.value \? " current" : ""\)\)/);
  // a pick posts the same setAuth the badge used, and only a CHANGE posts (current = dismiss)
  assert.match(RENDER, /if \(st\.auth !== c\.value && vscodeApi\) vscodeApi\.postMessage\(\{ type: "setAuth", id, value: c\.value \}\);/);
  // the item's sub-line names the current billing, or the applying reconnect (billing-label.ts's words)
  assert.match(BILLING, /if \(f\.authPending\) return "applying…";/);
  assert.match(RENDER, /auth\?: string; authLive\?: string; authPending\?: boolean; authBoth\?: boolean; authAcct\?: string;/);
});

test("no key material reaches the webview — no tail plumbing survives anywhere", () => {
  // the user 2026-08-08 (evening): even a last-4 tail is more key than any label needs. The kernel
  // stopped shipping authTail/apiTail/tail, and the client has no code left that could render one.
  assert.doesNotMatch(RENDER, /authTail/);
  assert.doesNotMatch(RENDER, /apiTail/);
  assert.doesNotMatch(RENDER, /a!\.tail/);
});

test("the chat tab hover says Billing whenever the backend reports it, through billing-label's words", () => {
  // ungated on machine shape (the user 2026-08-09: one-auth machines included; only a tmux session,
  // whose CLI env romp does not control, reports nothing). Anchored at the gate + label: a no-auth
  // session (tmux, the exclusion above) must never grow a fabricated Billing row, so the
  // `if (s.status.auth)` guard is part of the pinned behavior. The WORDS are billing-label.ts's and
  // run as executed cases in billing-label.test.ts (the CLI's report leads, a pending pick reads as
  // pending, an explicit pick the CLI contradicted leads with the warning, a seeded default never does).
  assert.match(RENDER, /if \(s\.status\.auth\) rows\.push\(\["Billing", billingRowText\(s\.status\)\]\);/,
    "the hover row's text is the shared decision");
  // the SWITCH CONTROL (the Billing submenu) carries the same decision where the pick lives (T124)
  assert.match(RENDER, /sb\.textContent = billingSubText\(st\);/,
    "the submenu sub-line is the same decision, shorter");
  assert.match(RENDER, /import \{ billingRowText, billingSubText, pickerBillingRow \} from "\.\/billing-label";/);
  // the field that tells a pick from a seeded default rides the status type
  assert.match(RENDER, /authBoth\?: boolean; authAcct\?: string; authPicked\?: boolean;/);
});

test("set_auth refuses a login pick on a box with no login — the same bar the key side always had (T124)", () => {
  const BACKEND = fs.readFileSync(path.resolve(process.cwd(), "..", "kernel", "sdk_backend.py"), "utf8");
  assert.ok(BACKEND.includes('if value == "login" and not self.login_ok():'),
    "refuse loudly at pick time when the box demonstrably lacks the credential");
  const KERNEL = fs.readFileSync(path.resolve(process.cwd(), "..", "kernel", "kernel.py"), "utf8");
  assert.ok(KERNEL.includes("_sdk_backend.login_ok = lambda: bool(_claude_account())"),
    "the probe is the credential store — the authority the usage bars trust");
  assert.ok(KERNEL.includes("or this machine has no Claude login to switch to."),
    "the warn toast names the login case");
});

test("setAuth is an intent op — held through a kernel-restart window, never dropped", () => {
  assert.match(INTENT, /"setModel", "setEffort", "setMode", "setFast", "setAuth",/);
});

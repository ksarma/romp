// Quarantine card in the feed (per-host trust model): mail from a DIRECTED federated peer is HELD, and
// surfaces as a COMPACT needs_input card under the RECIPIENT session's name — "New message" + one dim
// sender/gist line (the user 2026-07-26: the full-body card made the feed scroll; the delivery to that
// session is what's being approved). Clicking the line opens the decision dialog with the whole body,
// read-only (editing was cut from the flow); Approve delivers, Deny flips the dialog to an optional
// note back to the sender (the bus mails it to the origin host). Approve/Deny post a
// quarantineDecision op that carries the card's sid, so the federation manager routes the verdict to
// the kernel that actually HOLDS the file (a remote hold's Approve used to land on the local kernel
// and silently no-op — the user 2026-07-26). The dialog lives on document.body, outside the
// re-rendered feed root, so a kernel push mid-decision can't eat the note. Source-pin (no jsdom for
// the feed renderer), like the other feed-*.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const FEED = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "feed.ts"), "utf8");

test("the quarantine card is compact: Approve/Deny buttons + a one-line sender/gist, no Edit", () => {
  assert.match(FEED, /const qApprove = el\("button", "fdismiss fq fq-ok"\)[\s\S]*?qApprove\.textContent = "Approve"/);
  assert.match(FEED, /const qDeny = el\("button", "fdismiss fq fq-no"\)[\s\S]*?qDeny\.textContent = "Deny"/);
  assert.doesNotMatch(FEED, /qEdit/, "editing was cut from the flow (the user 2026-07-26)");
  // the body is the ROUTE then the gist (the user 2026-07-29): host:session -> host:session, hosts as
  // quiet metadata, session names in their identity colours, click-through to the decision dialog
  assert.match(FEED, /const qbody = el\("div", "fask-qbody"\)/);
  assert.match(FEED, /qBody\.replaceChildren\(\s*\n\s*quarWho\(it\.blocked\.origin \|\| "", it\.blocked\.frm \|\| "\?"\),/);
  assert.match(FEED, /Object\.assign\(el\("span", "fq-arrow"\), \{ textContent: "\\u2192" \}\)/);
  assert.match(FEED, /quarWho\(toHost, it\.blocked\.to \|\| it\.name \|\| "\?", it\.color\?\.bg\)/);
  assert.match(FEED, /Object\.assign\(el\("div", "fq-gist"\), \{ textContent: it\.blocked\.gist \|\| it\.blocked\.body \|\| "" \}\)/);
  // the recipient's host: this card's own kernel — a remote card's sid prefix, else this machine's name
  assert.match(FEED, /const toHost = \(it\.sid && it\.sid\.indexOf\(":"\) > 0\) \? it\.sid\.slice\(0, it\.sid\.indexOf\(":"\)\) : feedSelfHost;/);
  assert.match(FEED, /qBody\.onclick = [\s\S]*?showQuarantineDialog\(\.\.\.ends\(\), it\.blocked!\.body \|\| "", decide, false\)/);
  assert.match(FEED, /a\._qApprove = qApprove; a\._qDeny = qDeny; a\._qBody = qbody;/);
});

test("the blocked type carries the quarantine fields (incl. the gist)", () => {
  assert.match(FEED, /mid\?: string; frm\?: string; to\?: string; origin\?: string; body\?: string; gist\?: string \};\s*\/\/ quarantine/);
});

test("the decision carries the card's sid so a remote hold's verdict reaches the holding kernel", () => {
  assert.match(FEED, /const isQuar = it\.blocked\?\.state === "quarantine"/);
  // the block chip is suppressed for a quarantine card — its own buttons carry the decision
  assert.match(FEED, /it\.blocked\.state !== "quarantine"/);
  // sid rides the op — federation's routeOutbound keys on it (same shape as the askClear fix, 2026-07-02)
  assert.match(FEED, /vscodeApi\?\.postMessage\(\{ type: "quarantineDecision", mid, action, text, sid: it\.sid, feedback \}\)/);
  assert.match(FEED, /a\._qApprove\.onclick = [\s\S]*?decide\("approve", "Delivering…", it\.blocked!\.body \|\| ""\)/);
  // the card's Deny goes through the dialog's feedback step, never a blind drop
  assert.match(FEED, /a\._qDeny\.onclick = [\s\S]*?showQuarantineDialog\(\.\.\.ends\(\), it\.blocked!\.body \|\| "", decide, true\)/);
});

test("the decision dialog: read-only body, Approve/Deny, deny step offers a note to the sender", () => {
  assert.match(FEED, /function showQuarantineDialog\(/);
  const a = FEED.indexOf("function showQuarantineDialog"), b = FEED.indexOf("function showDenyNoteDialog(", a);
  assert.ok(a > 0 && b > a, "the fork's decision dialog sits above upstream's deny-note prompt");
  const dlg = FEED.slice(a, b);
  assert.match(dlg, /document\.body\.appendChild\(overlay\)/);
  // the body is a read-only view, not a textarea (editing was cut)
  assert.match(dlg, /el\("div", "qdlg-view"\)/);
  assert.match(dlg, /view\.textContent = body/);
  assert.match(dlg, /decide\("approve", "Delivering…", body\)/);
  // deny step: optional note back to the sender, or a bare deny; Cancel keeps the message held
  assert.match(dlg, /el\("textarea", "qdlg-text qdlg-feedback"\)/);
  assert.match(dlg, /decide\("deny", "Denying…", body, ta\.value\.trim\(\) \|\| undefined\)/);
  assert.match(dlg, /decide\("deny", "Denying…", body\)/);
  // no Cancel button (the user 2026-07-26: approve or deny, nothing else) — the backdrop click is the
  // only no-decision exit, and the message stays held
  assert.doesNotMatch(dlg, /"Cancel"/);
  assert.match(dlg, /if \(e\.target === overlay\) overlay\.remove\(\)/);
});

// Kept from upstream PR 1885's rewrite of this file: the notice action's KIND on the noticeAction wire and the quarantine
// kind's deny-note prompt, both taken in fold 4 beside the quarantine card above, which this fork keeps (upstream's pins of
// the card's removal are not taken).
test("a notice action posts its KIND on the wire, with the stored body; an older frame's route reads as send; only a held-mail Deny takes a click-time input", () => {
  assert.match(FEED, /actions: \{ label: string; kind\?: string; route\?: string; body: Record<string, unknown> \}\[\];/, "the record: kind, with route for an older frame");
  assert.match(FEED, /const kind = act\.kind \|\| \(act\.route === "\/send" \? "send" : ""\);/);
  assert.match(FEED, /vscodeApi\?\.postMessage\(\{ type: "noticeAction", itemId: it\.itemId, sid: it\.sid, kind, body: act\.body, \.\.\.\(input \? \{ input \} : \{\}\) \}\);/,
    "kind and body, the input member only when the click made one; the sid rides for federation");
  assert.match(FEED, /if \(kind === "quarantine" && act\.body && \(act\.body as any\)\.verdict === "deny"\) showDenyNoteDialog\(\(note\) => go\(note \? \{ note \} : undefined\)\);\s*\n\s*else go\(\);/);
  assert.doesNotMatch(FEED, /type: "noticeAction"[^\n]*route:/, "no route on the wire");
});

test("the deny-note prompt: on document.body, two choices and no Cancel, the backdrop closes without deciding", () => {
  const dlg = FEED.slice(FEED.indexOf("function showDenyNoteDialog("), FEED.indexOf("function showPickerDialog"));
  assert.ok(dlg.length > 0 && dlg.length < 3000, "one small function");
  assert.match(dlg, /document\.body\.appendChild\(overlay\)/);
  assert.match(dlg, /el\("textarea", "qdlg-text qdlg-feedback"\)/);
  assert.match(dlg, /withNote\.textContent = "Deny & send note"/); assert.match(dlg, /bare\.textContent = "Deny without note"/);
  assert.match(dlg, /onDeny\(note \|\| undefined\)/); assert.match(dlg, /bare\.onclick = \(\) => \{ overlay\.remove\(\); onDeny\(undefined\); \};/);
  assert.doesNotMatch(dlg, /"Cancel"/, "no Cancel button (the user 2026-07-26: approve or deny, nothing else)");
  assert.match(dlg, /if \(e\.target === overlay\) overlay\.remove\(\)/, "the backdrop is the only no-decision exit");
  assert.doesNotMatch(dlg, /qdlg-view/, "no read-only body view: the message text is the card's body and the modal's");
});

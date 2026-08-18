// A chatTail delta that starts PAST what the tab holds is a gap: the events in between never arrived.
// Applying it would fabricate a transcript that silently skips them, so the client used to just drop it
// and "wait for the next full" — which never came, because the kernel's per-client bookkeeping advances
// when it SENDS, not when the client APPLIES. The tab froze there: a stale "working" chip, no new
// messages, and every deep-link into the missing range honest-failing "couldn't locate this in the
// transcript", until the socket happened to drop (the user 2026-07-28 — locate-audit.jsonl recorded six
// pointer-not-rendered misses on one session, then pointer-exact on the SAME anchor the moment a kernel
// restart forced a reconnect). The fix: ask for the full session, and file the miss in the error center.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const ROOT = path.resolve(process.cwd(), "..");
const RENDER = fs.readFileSync(path.join(ROOT, "ui", "webview", "render.ts"), "utf8");
const FEED = fs.readFileSync(path.join(ROOT, "ui", "webview", "feed.ts"), "utf8");
const KERNEL = fs.readFileSync(path.join(ROOT, "bin", "romp-kernel"), "utf8");

test("a delta gap asks the kernel for a full session instead of freezing", () => {
  // measured against the KERNEL-owned length: the injected optimistic tail is not in the kernel's
  // coordinate space, and counting it masked a genuine 1-event gap (the user 2026-08-09)
  assert.match(RENDER, /if \(from > kernelLen\) \{/,
    "chatTail must treat a too-far-ahead delta as its own case, not fold it into the silent return");
  assert.match(RENDER, /while \(kernelLen > 0 && isOptimistic\(s\.events\[kernelLen - 1\]\)\) kernelLen--;/,
    "…in kernel coordinates, with the injected tail excluded");
  assert.match(RENDER, /requestFullSession\(msg\.id\);/, "…and request a re-base");
  assert.match(RENDER, /vscodeApi\?\.postMessage\(\{ type: "needFull", id \}\)/,
    "the resync request must actually reach the kernel");
});

test("the resync is asked ONCE per desync, and re-arms when the full session lands", () => {
  // the pusher runs every 0.5-3s; without the guard every rejected delta would re-ask
  assert.match(RENDER, /awaitingFull\.has\(id\)\) return;/, "one ask per desync");
  assert.match(RENDER, /awaitingFull\.add\(id\);/);
  assert.match(RENDER, /awaitingFull\.delete\(msg\.id\)/,
    "upsert() must clear the flag so a LATER gap can ask again");
});

test("a below-the-head delta is still ignored quietly (not a desync)", () => {
  // from < 0 means the change is in history this tab doesn't hold; its resident tail is still valid,
  // so it must NOT trigger a resync storm.
  assert.match(RENDER, /if \(from < 0\) return;/,
    "the below-the-loaded-head case keeps its quiet return");
});

test("the kernel talking about a session this client doesn't hold triggers the SAME re-ask (2026-08-18)", () => {
  // chatTail's !s used to be a silent drop — the exact hole that made a torn-down tab's swirl permanent:
  // echat advances on SEND, so the kernel kept sending deltas the client kept dropping, and the one
  // repair channel's only call site sat BELOW this return, unreachable. The missing base is the same
  // authoritative signal as the delta gap ("the kernel is talking about a session I don't have").
  assert.match(RENDER,
    /function chatTail\(msg: any\) \{\s*\n\s*const s = sessions\.get\(msg\.id\);\s*\n\s*if \(!s\) \{[\s\S]{0,800}?requestFullSession\(msg\.id\);\s*\n\s*return;\s*\n\s*\}/,
    "chatTail with no base asks for the full session instead of dropping the evidence");
  assert.match(RENDER,
    /function statusOnly\(msg: any\) \{\s*\n\s*const s = sessions\.get\(msg\.id\);\s*\n\s*if \(!s\) \{ requestFullSession\(msg\.id\); return; \}/,
    "statusOnly too — the same desync signal, third key (the tabOrder re-list is pinned in tab-ghost-heal)");
});

test("the re-ask stands down for closing tabs, provisional ids, and unreachable remote hosts", () => {
  // A tab the user just closed must not be resurrected by its own goodbye traffic (the kernel keeps
  // listing + talking about it for a push or two after the ✕); the kernel never knew a client-minted
  // provisional id; and a DETACHED host's teardown (closeRemote's synthesized closed fan-out) or a down
  // host must not turn into an ask-forever loop — the reattach's fresh connect re-sends everything anyway.
  assert.match(RENDER, /if \(isProvisionalId\(id\) \|\| closingTabs\.has\(id\)\) return;/,
    "provisional + mid-close suppression, inside requestFullSession so every ask key inherits it");
  assert.match(RENDER, /fed\.hosts\(\)\.indexOf\(h\) < 0 \|\| hostIsDown\(id\)\) return;/,
    "detached (not attached) and down hosts are suppressed the same way closingTabs is");
});

test("awaitingFull cannot wedge across a reconnect — the socket edge clears it", () => {
  // A needFull whose REPLY is lost with the socket would otherwise latch its slot forever: only upsert
  // clears it, so every later re-ask for that sid would be suppressed and the swirl would be back to
  // permanent. The socket edge is the deciding event (the kernel treats a reconnect as a fresh client
  // and re-sends full sessions, so clearing here never costs an extra ask — it only re-arms the repair).
  assert.match(RENDER, /window\.addEventListener\("romp:wsdown", \(\) => awaitingFull\.clear\(\)\);/);
  assert.match(RENDER, /window\.addEventListener\("romp:wsup", \(\) => awaitingFull\.clear\(\)\);/);
  assert.match(RENDER, /if \(m\.type === "pipeState"\) \{ if \(!m\.up\) awaitingFull\.clear\(\);/,
    "the VS Code pipe's down edge too — its shim never fires the romp:ws* events");
  // …and the shim genuinely fires those events on the local socket's close/reopen, so the clear has a source
  assert.ok(KERNEL.includes('new Event("romp:wsdown")'), "the shim dispatches romp:wsdown on close");
  assert.ok(KERNEL.includes('new Event("romp:wsup")'), "…and romp:wsup on reconnect");
});

test("the kernel handles needFull by forgetting what that client holds", () => {
  assert.ok(KERNEL.includes('msg.get("type") == "needFull"'), "the kernel must handle the frame");
  const i = KERNEL.indexOf('msg.get("type") == "needFull"');
  const body = KERNEL.slice(i, i + 1200);
  assert.ok(body.includes('"echat"'), "drop the client's tail base → next push sends a full session");
  assert.ok(body.includes('("chat", sid)'), "drop the dedup slot → the full send isn't swallowed");
  assert.ok(body.includes("_push_one(client)"), "repair immediately, not on the next tick");
});

test("a failed jump is filed in the error center, not just toasted", () => {
  // the toast is transient and locate-audit.jsonl is invisible from the UI, so a failed click left
  // nothing the user could point at afterwards (the user 2026-07-28)
  assert.match(RENDER, /notifyShell\("locate",/, "the chat files a locate entry on an honest failure");
  assert.match(RENDER, /romp: "notify", kind, text, sid/, "…over the shell's notify bridge");
  assert.match(FEED, /kind: "locate"/, "the feed's no-anchor summary click files one too");
  // and the kind must be registered in the shell, or the entry renders chip-less and unfilterable
  assert.ok(KERNEL.includes("'locate'"), "the error center must know the locate kind");
  assert.ok(KERNEL.includes("locate:'jump failed'"), "…with a label");
  assert.ok(/locate:"[^"]+"/.test(KERNEL), "…and a description for its filter tooltip");
});

test("the anchor re-query uses the same selectors as the first lookup", () => {
  // the recovery re-render found the event, then re-queried with only 2 of the 3 selectors — so an
  // unhydrated postal turn (ids only in data-mids) still honest-failed pointer-not-rendered
  const both = RENDER.split("data-mids~=").length - 1;
  assert.ok(both >= 2, "data-mids must be in BOTH the initial query and the post-re-render re-query");
});

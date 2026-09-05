// THE CHAT PANE'S VIEWS WRITES ARE ACKNOWLEDGED (the user 2026-09-05, who lost a batch of tag
// renames and assignments). The tab menu's Tags flyout had the timeline dialog's shape: every
// gesture posted the WHOLE blob from the pane's own un-echoed optimistic copy, so a New tag… then a
// Move to carried the pre-burst `at` stamp and the kernel's stale-writer guard refused the second
// against the first; the copy cleared on an exact echo or after THREE frames, whichever came first.
// Now: tag gestures post TARGETED tagEdit ops; lens and order edits keep the whole-blob write; both
// carry a writeId the kernel's ack names, and the optimistic copy clears on the ACK — never on a
// frame count. Executed tests on the pure module (views-writes.ts) plus source pins on render.ts
// (the tab-order.ts pattern; no jsdom for render.ts). Synthetic ids only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { ackOutcome, mintWriteId } from "./views-writes";

const RENDER = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "render.ts"), "utf8");
const S1 = { active: "all", at: 113, tags: [{ id: "g1", name: "qa", color: "#DD42FF", members: ["tests"], mtime: 113 }] };

test("executed: an ok ack settles ITS write; the copy clears only when nothing else is in flight", () => {
  // the burst: a create (w1) and the rename typed before its echo (w2), both in flight
  const a = ackOutcome(["w1", "w2"], { type: "tagEditAck", writeId: "w1", ok: true, views: S1 });
  assert.deepEqual(a, { inflight: ["w2"], clearPending: false, refusal: null },
    "the create's ack leaves the rename's optimistic copy showing — the user's typed name never blinks to 'tag N'");
  const b = ackOutcome(a.inflight, { type: "tagEditAck", writeId: "w2", ok: true, views: S1 });
  assert.deepEqual(b, { inflight: [], clearPending: true, refusal: null }, "the last ack settles the copy");
});

test("executed: a refusal drops everything at once and names the tag and the reason", () => {
  const why = 'a tag named "web" already exists';
  const r = ackOutcome(["w1", "w2"], { type: "tagEditAck", writeId: "w1", ok: false, error: why, views: S1 });
  assert.deepEqual(r, { inflight: [], clearPending: true, refusal: why }, "revert now: the store's blob (in the ack) is what stands");
  // the whole-blob path's refusal lists the tags the guard kept, each with its reason
  const reason = 'your copy of "web" predates a newer edit to it; the newer state was kept';
  const w = ackOutcome(["w3"], { type: "viewsAck", writeId: "w3", ok: false, refused: [{ name: "web", reason }], error: reason, views: S1 });
  assert.equal(w.refusal, "web: " + reason);
  assert.equal(w.clearPending, true);
  // no error text at all → still a plain word, never an empty toast
  assert.equal(ackOutcome(["w4"], { writeId: "w4", ok: false }).refusal, "refused");
  assert.equal(ackOutcome(["w5"], { writeId: "w5", ok: false, refused: [{ name: "qa", reason: "kept" }] }).refusal, "qa: kept",
    "reasons compose when the ack carries only the refused rows");
});

test("executed: an ack for a write this page never made counts as information — nothing stays pinned", () => {
  assert.deepEqual(ackOutcome([], { type: "viewsAck", writeId: "w-from-a-previous-load", ok: true, views: S1 }),
    { inflight: [], clearPending: true, refusal: null });
  assert.deepEqual(ackOutcome(["w9"], { type: "viewsAck", writeId: "w-other", ok: true, views: S1 }),
    { inflight: ["w9"], clearPending: false, refusal: null }, "…but our own in-flight write still holds its copy");
});

test("executed: write ids are unique per page across same-ms gestures", () => {
  const a = mintWriteId(1), b = mintWriteId(2);
  assert.notEqual(a, b);
  assert.match(a, /^w[0-9a-z]+-1$/);
});

test("pins: render.ts posts a writeId on every views write and routes both acks to onViewsAck", () => {
  assert.match(RENDER, /function postViews\(v: SessionViews\) \{\s*\n\s*const writeId = holdViews\(v\);\s*\n\s*if \(vscodeApi\) vscodeApi\.postMessage\(\{ type: "setTimelineViews", views: v, writeId \}\);/,
    "a lens/order edit is still the whole blob (the kernel owns no lens op), now with its writeId");
  assert.match(RENDER, /function postTagEdit\(nv: SessionViews, edit: TagEditOp\) \{\s*\n\s*const writeId = holdViews\(nv\);\s*\n\s*if \(vscodeApi\) vscodeApi\.postMessage\(\{ type: "tagEdit", writeId, \.\.\.edit \}\);/,
    "a tag gesture is a targeted op — the op's fields ARE the message");
  assert.match(RENDER, /else if \(m\.type === "viewsAck" \|\| m\.type === "tagEditAck"\) onViewsAck\(m\);/);
  const ack = RENDER.slice(RENDER.indexOf("function onViewsAck("), RENDER.indexOf("\n}\n", RENDER.indexOf("function onViewsAck(")));
  assert.match(ack, /const out = ackOutcome\(viewsWrites, m\);/, "the pure module decides; render.ts applies");
  assert.match(ack, /if \(m\.views\) sessionViews = m\.views;/, "the ack's blob is the new base, verdict regardless");
  assert.match(ack, /if \(out\.refusal\) warnToast\(/, "a refusal is LOUD — the flyout has no error surface of its own");
});

test("pins: the three-frame yield is gone from the tab strip — captureViews clears only on the write's exact echo", () => {
  assert.doesNotMatch(RENDER, /pendingViewsAge/, "no frame counter anywhere in render.ts");
  const cap = RENDER.slice(RENDER.indexOf("function captureViews("), RENDER.indexOf("\n}\n", RENDER.indexOf("function captureViews(")));
  assert.doesNotMatch(cap, />= 3/);
  assert.match(cap, /if \(pendingSessionViews && v && viewsKey\(v\) === viewsKey\(pendingSessionViews\)\) \{\s*\n\s*pendingSessionViews = null; viewsWrites = \[\];/);
});

test("pins: the Tags flyout's local edits are targeted ops on ONE optimistic blob; a MOVE is two ops, one blob", () => {
  const at = RENDER.indexOf("const editUnion = (g: TagUnion");
  const body = RENDER.slice(at, at + 3200);
  assert.ok(body.includes('ops.push({ op: "addMember", name: g.name, sids: edit.add.slice() });'), "a local add is an addMember by name");
  assert.ok(body.includes('ops.push({ op: "removeMember", name: g.name, sids: edit.remove.slice() });'), "a local remove is a removeMember by name");
  assert.match(body, /const postUnionEdits = \(nv: SessionViews, \.\.\.edits: UnionEdit\[\]\) =>/);
  assert.match(body, /for \(const op of ops\) postTagEdit\(nv, op\);/, "N ops, the one copy shown for all of them");
  assert.match(RENDER, /const a = applyUnionEdit\(nv, to, \{ add: \[id\] \}\);\s*\n\s*const r = applyUnionEdit\(nv, from, \{ remove: \[id\] \}\);\s*\n\s*postUnionEdits\(nv, a, r\);/,
    "the move: two ops on one blob — the strip never shows the half-moved state");
  assert.match(RENDER, /postTagEdit\(nv, \{ op: "create", name, color, id: tg\.id, sids: \[id\] \}\);/,
    "New tag… is ONE create carrying the session — the tag and its first member land together");
  const fly = RENDER.slice(at, RENDER.indexOf("// HOVER-INTENT open", at));
  assert.doesNotMatch(fly, /postViews\(/, "no whole-blob write anywhere in the flyout's tag edits");
});

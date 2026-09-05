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
import { ackOutcome, adoptViews, mintWriteId, seqOf } from "./views-writes";

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
  // the whole-blob path's refusal lists the tags the guard kept, each with a NAME-FREE reason; the
  // kernel's one-line `error` names each tag once — and the page never prefixes the name a second time
  const reason = "your copy predates a newer edit to it, so your change was not applied and the newer state was kept";
  const w = ackOutcome(["w3"], { type: "viewsAck", writeId: "w3", ok: false, refused: [{ tid: "gA", name: "web", reason }], error: '"web": ' + reason, views: S1 });
  assert.equal(w.refusal, '"web": ' + reason, "the kernel's line as-is: the name once, then what was refused and what was kept");
  assert.equal(w.clearPending, true);
  // no error text at all → still a plain word, never an empty toast
  assert.equal(ackOutcome(["w4"], { writeId: "w4", ok: false }).refusal, "refused");
  assert.equal(ackOutcome(["w5"], { writeId: "w5", ok: false, refused: [{ name: "qa", reason: "kept" }] }).refusal, '"qa": kept',
    "with only the rows, the same shape is composed here");
  // ok WITH refusals listed (the guard kept the store's copy of tags this write did not edit — a lens
  // write from a stale copy): the write is settled, nothing is toasted, the ack's blob is the base
  assert.deepEqual(ackOutcome(["w6"], { type: "viewsAck", writeId: "w6", ok: true, refused: [{ tid: "gA", name: "web", reason }], views: S1 }),
    { inflight: [], clearPending: true, refusal: null }, "nothing the user did was refused");
});

test("executed: an ack for a write this page never made counts as information — nothing stays pinned", () => {
  assert.deepEqual(ackOutcome([], { type: "viewsAck", writeId: "w-from-a-previous-load", ok: true, views: S1 }),
    { inflight: [], clearPending: true, refusal: null });
  assert.deepEqual(ackOutcome(["w9"], { type: "viewsAck", writeId: "w-other", ok: true, views: S1 }),
    { inflight: ["w9"], clearPending: false, refusal: null }, "…but our own in-flight write still holds its copy");
});

test("executed: a blob is adopted by write SEQUENCE, never by arrival order — older is ignored, equal or newer lands, no seq adopts", () => {
  const held = { active: "all", tags: [], seq: 12 };
  assert.equal(adoptViews(held, { active: "all", tags: [], seq: 11 }), false, "the pusher's warmed cache, delivered after the ack: ignored");
  assert.equal(adoptViews(held, { active: "all", tags: [], seq: 12 }), true, "the same write, seen again (the ack's blob then its frame): fine");
  assert.equal(adoptViews(held, { active: "all", tags: [], seq: 13 }), true);
  assert.equal(adoptViews(held, { active: "all", tags: [] }), true, "a kernel from before the stamp sends no seq — nothing is gated on a field it never sends");
  assert.equal(adoptViews(null, { active: "all", tags: [], seq: 3 }), true, "nothing held yet");
  assert.equal(adoptViews({ active: "all", tags: [] }, { active: "all", tags: [], seq: 3 }), true, "a seq-less base yields to the first stamped blob");
  assert.equal(adoptViews(held, null), false);
  assert.equal(seqOf({ seq: 7 } as any), 7);
  assert.equal(seqOf({ seq: "7" } as any), null, "a non-number is no seq");
  assert.equal(seqOf(null), null);
});

test("executed: write ids are unique per page across same-ms gestures", () => {
  const a = mintWriteId(1), b = mintWriteId(2);
  assert.notEqual(a, b);
  assert.match(a, /^w[0-9a-z]+-1$/);
});

test("pins: render.ts posts a writeId on every views write and routes both acks to onViewsAck", () => {
  const pv = RENDER.slice(RENDER.indexOf("function postViews(v: SessionViews, edited: string[] = [])"), RENDER.indexOf("\n}\n", RENDER.indexOf("function postViews(")));
  assert.match(pv, /const writeId = holdViews\(v\);/);
  assert.match(pv, /vscodeApi\.postMessage\(\{ type: "setTimelineViews", views: v, writeId, edited \}\);/,
    "a lens/order edit is still the whole blob (the kernel owns no lens op), with its writeId and the tag ids it changed (none) — a refusal on an untouched tag is acked ok, no toast");
  assert.match(RENDER, /warnToast\("Tag edit not applied — " \+ out\.refusal\);/, "the toast adds no second name: the reason names the tag once and says what was kept");
  const pte = RENDER.slice(RENDER.indexOf("function postTagEdit("), RENDER.indexOf("\n}\n", RENDER.indexOf("function postTagEdit(")));
  assert.match(pte, /if \(!kernelCaps\.has\("tagEdit"\)\) \{ postViews\(nv, \[edit\.tid, edit\.tid_from, edit\.tid_to\]\.filter\(\(t\): t is string => !!t\)\); return; \}/,
    "no `tagEdit` capability announced (an older kernel) → the pre-cap whole-blob write naming the tags it changed, reconciled by the legacy path");
  assert.match(pte, /const writeId = holdViews\(nv\);\s*\n\s*if \(vscodeApi\) vscodeApi\.postMessage\(\{ type: "tagEdit", writeId, edit \}\);/,
    "a tag gesture is a targeted op, NESTED under `edit` so no tag name sits at the top level where the federation router reads session addresses");
  assert.match(RENDER, /else if \(m\.type === "viewsAck" \|\| m\.type === "tagEditAck"\) onViewsAck\(m\);/);
  assert.match(RENDER, /else if \(m\.type === "caps"\) onKernelCaps\(m\);\s*\n\s*else if \(m\.type === "unknownOp"\) onUnknownOp\(m\);/,
    "the kernel's caps (every `ready`) and its answer to an op it does not know both have a door");
  const caps = RENDER.slice(RENDER.indexOf("function onKernelCaps("), RENDER.indexOf("\n}\n", RENDER.indexOf("function onKernelCaps(")));
  assert.match(caps, /kernelCaps = new Set\(/);
  assert.match(caps, /if \(!viewsWrites\.length\) return;\s*\n\s*viewsWrites = \[\]; pendingSessionViews = null;\s*\n\s*warnToast\(/,
    "a caps frame with writes in flight is a re-established socket: their acks may never come, so they are dropped and the user is told");
  const unk = RENDER.slice(RENDER.indexOf("function onUnknownOp("), RENDER.indexOf("\n}\n", RENDER.indexOf("function onUnknownOp(")));
  assert.match(unk, /if \(typeof m\.op === "string"\) kernelCaps\.delete\(m\.op\);/, "the capability is withdrawn");
  assert.match(unk, /viewsWrites\.includes\(m\.writeId\)\)\s*\n\s*onViewsAck\(\{ type: "unknownOp", writeId: m\.writeId, ok: false,/, "…and the write is refused, through the one ack door");
  const ack = RENDER.slice(RENDER.indexOf("function onViewsAck("), RENDER.indexOf("\n}\n", RENDER.indexOf("function onViewsAck(")));
  assert.match(ack, /const out = ackOutcome\(viewsWrites, m\);/, "the pure module decides; render.ts applies");
  assert.match(ack, /takeViews\(m\.views\);/, "the ack's blob is the new base unless a newer frame already overtook it (the seq decides), verdict regardless");
  assert.match(ack, /if \(out\.refusal\) warnToast\(/, "a refusal is LOUD — the flyout has no error surface of its own");
});

test("pins: every views arrival in render.ts goes through the ONE seq-gated adopter, and the exact-echo clear is legacy-only", () => {
  const take = RENDER.slice(RENDER.indexOf("function takeViews("), RENDER.indexOf("\n}\n", RENDER.indexOf("function takeViews(")));
  assert.match(take, /if \(adoptViews\(sessionViews, v\)\) \{ sessionViews = v; return true; \}/, "adopt by write sequence, never by arrival order");
  assert.match(take, /what: "views-stale-blob"/, "an ignored blob leaves one breadcrumb per page load — a visible fact, not a flicker");
  assert.doesNotMatch(RENDER, /pendingViewsAge/, "no frame counter anywhere in render.ts");
  const cap = RENDER.slice(RENDER.indexOf("function captureViews("), RENDER.indexOf("\n}\n", RENDER.indexOf("function captureViews(")));
  assert.match(cap, /^\s*takeViews\(v\);/m, "a pushed frame is adopted through the gate");
  assert.match(cap, /if \(pendingSessionViews && v && seqOf\(v\) === null\s*\n\s*&& \(viewsKey\(v\) === viewsKey\(pendingSessionViews\) \|\| \+\+legacyViewsAge >= 3\)\) \{\s*\n\s*pendingSessionViews = null; viewsWrites = \[\]; legacyViewsAge = 0;/,
    "the exact-echo clear and the three-frame yield survive ONLY for a blob without a seq (a kernel that acks nothing); a stamped kernel's frames never clear a write they cannot name");
  assert.equal((cap.match(/>= 3/g) || []).length, 1, "one legacy yield, under the seq-less condition, nowhere else");
  assert.equal((RENDER.match(/(?<!pending)(?<!\w)sessionViews = /g) || []).length, 1,
    "the base is assigned in exactly one place — inside the gate");
});

test("pins: the Tags flyout's local edits are targeted ops on ONE optimistic blob; a MOVE is two ops, one blob", () => {
  const at = RENDER.indexOf("const editUnion = (g: TagUnion");
  const body = RENDER.slice(at, at + 3200);
  assert.ok(body.includes('ops.push({ op: "addMember", tid: g.localId, sids: edit.add.slice() });'), "a local add is an addMember by the tag's stored id");
  assert.ok(body.includes('ops.push({ op: "removeMember", tid: g.localId, sids: edit.remove.slice() });'), "a local remove is a removeMember by id");
  assert.doesNotMatch(body, /op: "(?:addMember|removeMember|rename|recolor|delete)", name:/, "no op but create carries a tag name");
  assert.match(body, /const postUnionEdits = \(nv: SessionViews, \.\.\.edits: UnionEdit\[\]\) =>/);
  assert.match(body, /for \(const op of ops\) postTagEdit\(nv, op\);/, "N ops, the one copy shown for all of them");
  assert.match(RENDER, /const a = applyUnionEdit\(nv, to, \{ add: \[id\] \}\);\s*\n\s*const r = applyUnionEdit\(nv, from, \{ remove: \[id\] \}\);/,
    "the move: two edits on one blob — the strip never shows the half-moved state");
  assert.match(RENDER, /\{ op: "move", tid_from: rem\.tid, tid_to: add\.tid, sid: id \}/,
    "…posted as ONE atomic op when both tags are local (both halves land or neither)");
  assert.match(RENDER, /postTagEdit\(nv, \{ op: "create", name, color, sids: \[id\] \}\);/,
    "New tag… is ONE create carrying the session — the tag and its first member land together; the kernel mints the id");
  const fly = RENDER.slice(at, RENDER.indexOf("// HOVER-INTENT open", at));
  assert.doesNotMatch(fly, /postViews\(/, "no whole-blob write anywhere in the flyout's tag edits");
});

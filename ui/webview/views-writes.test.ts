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
import { ackOutcome, adoptViews, applyTagEdit, createInFlight, mintWriteId, rederivePending, seqOf, type InflightWrite } from "./views-writes";

const RENDER = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "render.ts"), "utf8");
const S1 = { active: "all", at: 113, tags: [{ id: "g1", name: "qa", color: "#DD42FF", members: ["tests"], mtime: 113 }] };

const W1: InflightWrite = { id: "w1", edit: { op: "create", name: "qa", color: "#DD42FF", sids: ["tests"] }, newId: "pending-1" };
const W2: InflightWrite = { id: "w2", edit: { op: "rename", tid: "g1", newName: "quality" } };

test("executed: an ok ack settles ITS write; the copy clears only when nothing else is in flight", () => {
  // the burst: a create (w1) and the rename typed before its echo (w2), both in flight
  const a = ackOutcome([W1, W2], { type: "tagEditAck", writeId: "w1", ok: true, views: S1 });
  assert.deepEqual(a, { inflight: [W2], clearPending: false, rederive: false, refusal: null },
    "the create's ack leaves the rename's optimistic copy showing — the user's typed name never blinks to 'tag N'");
  const b = ackOutcome(a.inflight, { type: "tagEditAck", writeId: "w2", ok: true, views: S1 });
  assert.deepEqual(b, { inflight: [], clearPending: true, rederive: false, refusal: null }, "the last ack settles the copy");
});

test("executed: a refusal drops ITS write only and names the tag and the reason; a later in-flight write keeps its copy", () => {
  const why = 'a tag named "web" already exists';
  const r = ackOutcome([W1, W2], { type: "tagEditAck", writeId: "w1", ok: false, error: why, views: S1 });
  assert.deepEqual(r, { inflight: [W2], clearPending: false, rederive: true, refusal: why },
    "the refused write is dropped; the rename still in flight is not — the copy is re-derived without the refused change (round 3 of the 2026-09-05 review: a refusal cleared the whole list, and a later write flapped off and back on)");
  assert.deepEqual(ackOutcome([W1], { type: "tagEditAck", writeId: "w1", ok: false, error: why, views: S1 }),
    { inflight: [], clearPending: true, rederive: false, refusal: why }, "with nothing else in flight the store's blob (in the ack) is what stands");
  // the whole-blob path's refusal lists the tags the guard kept, each with a NAME-FREE reason; the
  // kernel's one-line `error` names each tag once — and the page never prefixes the name a second time
  const reason = "your copy predates a newer edit to it, so your change was not applied and the newer state was kept";
  const w = ackOutcome([{ id: "w3", blob: S1 }], { type: "viewsAck", writeId: "w3", ok: false, refused: [{ tid: "gA", name: "web", reason }], error: '"web": ' + reason, views: S1 });
  assert.equal(w.refusal, '"web": ' + reason, "the kernel's line as-is: the name once, then what was refused and what was kept");
  assert.equal(w.clearPending, true);
  // no error text at all → still a plain word, never an empty toast
  assert.equal(ackOutcome([{ id: "w4" }], { writeId: "w4", ok: false }).refusal, "refused");
  assert.equal(ackOutcome([{ id: "w5" }], { writeId: "w5", ok: false, refused: [{ name: "qa", reason: "kept" }] }).refusal, '"qa": kept',
    "with only the rows, the same shape is composed here");
  // ok WITH refusals listed (the guard kept the store's copy of tags this write did not edit — a lens
  // write from a stale copy): the write is settled, nothing is toasted, the ack's blob is the base
  assert.deepEqual(ackOutcome([{ id: "w6", blob: S1 }], { type: "viewsAck", writeId: "w6", ok: true, refused: [{ tid: "gA", name: "web", reason }], views: S1 }),
    { inflight: [], clearPending: true, rederive: false, refusal: null }, "nothing the user did was refused");
});

test("executed: the pending copy re-derives from the store's blob plus the writes still in flight — only the refused change reverts", () => {
  const base = { active: "all", seq: 5, tags: [{ id: "gA", name: "web", color: "#3b82f6", members: ["s1"] }] };
  // A (recolor) refused, B (addMember, posted after A from the copy that showed the recolor) still in flight
  const B: InflightWrite = { id: "wB", edit: { op: "addMember", tid: "gA", sids: ["s2"] } };
  const p = rederivePending(base, [B])!;
  assert.deepEqual(p.tags, [{ id: "gA", name: "web", color: "#3b82f6", members: ["s1", "s2"] }], "the add shows, the refused recolor does not");
  assert.deepEqual(base.tags[0].members, ["s1"], "the base is never mutated");
  assert.equal(rederivePending(base, []), null, "nothing in flight → the base itself shows");
  // a whole-blob write in flight IS the state it posted; a targeted op after it applies on top
  const blob = { active: "all", tags: [{ id: "gA", name: "web", color: "#000000", members: [] }], actives: { chat: { tags: ["web"] } } };
  const q = rederivePending(base, [{ id: "wL", blob }, { id: "wC", edit: { op: "create", name: "qa", color: "#DD42FF", sids: ["s3"] }, newId: "pending-x" }])!;
  assert.deepEqual(q.actives, { chat: { tags: ["web"] } });
  assert.deepEqual(q.tags, [{ id: "gA", name: "web", color: "#000000", members: [] }, { id: "pending-x", name: "qa", color: "#DD42FF", members: ["s3"] }],
    "the create's row wears the placeholder id its gesture drew");
  // every op, applied the way the gesture applied it; an unknown tid is a no-op
  const t2 = { active: "gA", tags: [{ id: "gA", name: "web", members: ["s1", "s2"] }, { id: "gB", name: "api", members: ["s3"] }] };
  assert.equal(applyTagEdit(t2, { op: "rename", tid: "gA", newName: "site" }).tags![0].name, "site");
  assert.equal(applyTagEdit(t2, { op: "recolor", tid: "gB", color: "#54B204" }).tags![1].color, "#54B204");
  const del = applyTagEdit(t2, { op: "delete", tid: "gA" });
  assert.deepEqual([del.tags!.map((t) => t.id), del.active], [["gB"], "all"], "a deleted active tag falls back to All, as the gesture did");
  assert.deepEqual(applyTagEdit(t2, { op: "removeMember", tid: "gA", sids: ["s1"] }).tags![0].members, ["s2"]);
  const mv = applyTagEdit(t2, { op: "move", tid_from: "gA", tid_to: "gB", sid: "s2" });
  assert.deepEqual([mv.tags![0].members, mv.tags![1].members], [["s1"], ["s3", "s2"]]);
  assert.deepEqual(applyTagEdit(t2, { op: "rename", tid: "gZ", newName: "x" }).tags, t2.tags, "an unknown tid changes nothing — the kernel refuses it");
  assert.equal(createInFlight([B]), false);
  assert.equal(createInFlight([B, W1]), true, "a create in flight gates the next New tag…");
});

test("executed: an ack for a write this page never made counts as information — nothing stays pinned", () => {
  assert.deepEqual(ackOutcome([], { type: "viewsAck", writeId: "w-from-a-previous-load", ok: true, views: S1 }),
    { inflight: [], clearPending: true, rederive: false, refusal: null });
  assert.deepEqual(ackOutcome([{ id: "w9" }], { type: "viewsAck", writeId: "w-other", ok: true, views: S1 }),
    { inflight: [{ id: "w9" }], clearPending: false, rederive: false, refusal: null }, "…but our own in-flight write still holds its copy");
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
  assert.match(pv, /const writeId = holdViews\(v, \{ blob: v \}\);/, "the record keeps the blob it posted: a refusal elsewhere re-derives from it");
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
  assert.match(unk, /viewsWrites\.some\(\(w\) => w\.id === m\.writeId\)\)\s*\n\s*onViewsAck\(\{ type: "unknownOp", writeId: m\.writeId, ok: false,/, "…and the write is refused, through the one ack door");
  const ack = RENDER.slice(RENDER.indexOf("function onViewsAck("), RENDER.indexOf("\n}\n", RENDER.indexOf("function onViewsAck(")));
  assert.match(ack, /const out = ackOutcome\(viewsWrites, m\);/, "the pure module decides; render.ts applies");
  assert.match(ack, /takeViews\(m\.views\);/, "the ack's blob is the new base unless a newer frame already overtook it (the seq decides), verdict regardless");
  assert.match(ack, /if \(out\.clearPending\) pendingSessionViews = null;\s*\n\s*else if \(out\.rederive\) pendingSessionViews = rederivePending\(sessionViews, viewsWrites\);/,
    "a refusal with other writes in flight re-derives the copy from the base plus them — only the refused change reverts");
  assert.match(ack, /if \(out\.refusal\) warnToast\(/, "a refusal is LOUD — the flyout has no error surface of its own");
  assert.match(ack, /syncNewTagInput\(\);/, "…and the flyout's New tag… input is re-armed in place — never by rebuilding the flyout, which would drop typed text");
  const sync = RENDER.slice(RENDER.indexOf("function syncNewTagInput("), RENDER.indexOf("\n}\n", RENDER.indexOf("function syncNewTagInput(")));
  assert.match(sync, /const busy = createInFlight\(viewsWrites\);\s*\n\s*tagsFlyNewInput\.disabled = busy;\s*\n\s*tagsFlyNewInput\.placeholder = busy \? "creating…" : "New tag…";/,
    "disabled and saying so while a create is in flight (a second Enter before the ack made a second tag)");
  assert.match(RENDER, /function dismissTabMenu\(\) \{\s*\n\s*ctxMenuEl\?\.remove\(\);\s*\n\s*ctxMenuEl = null;\s*\n\s*tagsFlyNewInput = null;/, "a closed menu forgets its input");
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
  const fly = RENDER.slice(at, RENDER.indexOf("// BROWSE FILES", at));
  assert.ok(body.includes('ops.push({ op: "addMember", tid: g.localId, sids: edit.add.slice() });'), "a local add is an addMember by the tag's stored id");
  assert.ok(body.includes('ops.push({ op: "removeMember", tid: g.localId, sids: edit.remove.slice() });'), "a local remove is a removeMember by id");
  assert.doesNotMatch(body, /op: "(?:addMember|removeMember|rename|recolor|delete)", name:/, "no op but create carries a tag name");
  assert.match(body, /const postUnionEdits = \(nv: SessionViews, \.\.\.edits: UnionEdit\[\]\) =>/);
  assert.match(body, /for \(const op of ops\) postTagEdit\(nv, op\);/, "N ops, the one copy shown for all of them");
  assert.match(RENDER, /const a = applyUnionEdit\(nv, to, \{ add: \[id\] \}\);\s*\n\s*const r = applyUnionEdit\(nv, from, \{ remove: \[id\] \}\);/,
    "the move: two edits on one blob — the strip never shows the half-moved state");
  assert.match(RENDER, /\{ op: "move", tid_from: rem\.tid, tid_to: add\.tid, sid: id \}/,
    "…posted as ONE atomic op when both tags are local (both halves land or neither)");
  assert.match(RENDER, /postTagEdit\(nv, \{ op: "create", name, color, sids: \[id\] \}, tg\.id\);/,
    "New tag… is ONE create carrying the session — the tag and its first member land together; the kernel mints the id (the placeholder rides along for the legacy path's re-id)");
  assert.match(fly, /if \(e2\.key !== "Enter"\) return;\s*\n\s*if \(createInFlight\(viewsWrites\)\) return;/, "one create at a time: Enter is ignored while one is in flight");
  assert.match(fly, /nrow\.appendChild\(inp\);\s*\n\s*tagsFlyNewInput = inp; syncNewTagInput\(\);/, "the input renders disabled when a create is already in flight");
  assert.doesNotMatch(fly, /postViews\(/, "no whole-blob write anywhere in the flyout's tag edits");
});

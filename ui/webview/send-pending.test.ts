// Send durability on the client (the 2026-09-05/06 audits). Two things went wrong at once: a send fed
// into a running turn is taken by the CLI at a later tool boundary and placed at its SEND time, so the
// pending bubble at the bottom vanished and the message reappeared higher up with no cue; and the
// client's bubble had a 20 s lifetime, so when the kernel's own echo was pruned early the send simply
// looked delivered. Now: (1) a pending send has NO lifetime — it ends on a landing, the kernel's
// never-delivered verdict, or the user's ✕; (2) the pending bubble is drawn AT ITS SEND POSITION from the
// start — right after its anchor, the last stable kernel event at the press — so the steps that stream
// in afterwards land below it and the absorbed atom, which the kernel places at the send time, replaces
// it in the same spot (T252, the user 2026-09-07: a header plus a button that jumps somewhere and later
// disappears is weird; the first cut's "joined mid-turn" header and the jump/✕ cue are gone);
// (3) every composer send posts a clientDiag breadcrumb (never the text).
// The 2026-09-06 adversarial review then fixed the decision's frame: (4) every verdict is read from the
// events AFTER the send's anchor, never from a 30-event tail count; (5) [retired with the cue];
// (6) the lost verdict shares the anchor; (7) exact text, one landing per send; (8) a connection
// drop repaints once; (9) the bare label is per bubble; (10) the kernel's own copy clears "not confirmed".
// Round 3 of that review: (11) receipt is attributed per send, like landings; (12) the ✕ removes the
// bubble's own entry; (13) a stamp taken late reads the events' own times. Round 4: (14) a late stamp
// presumes the frame's newest queued copy of its text is its own (the queued bubble carries no stamp).
// The decisions are executed through send-pending.ts; the DOM half is pinned in render.ts/styles.css.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { newPending, pendingBody, reconcilePending, dropPending, scanFrom, queuedCopyToHide, landedIn, provisionalIn, bareGroupLabel, sentAtLabel, type TailEvent, type PendingSend } from "./send-pending";

const read = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const RENDER = read("render.ts");
const CSS = read("styles.css");
const T0 = 1_700_000_000_000;
const TEXT = "rename this to fetch_notes";

// The press: registerOptimistic reconciles the fresh entry against the tail as it stands BEFORE any
// kernel round-trip, which stamps the anchor. Every scenario below starts there.
const press = (tail: TailEvent[], ...texts: string[]): PendingSend[] => {
  const list = texts.map((t, i) => newPending(t, undefined, T0 + i));
  reconcilePending(tail, list);
  return list;
};
const filler = (n: number, prefix = "f"): TailEvent[] =>
  Array.from({ length: n }, (_, i) => (i % 3 === 0 ? { kind: "thinking", uuid: `${prefix}${i}` } : i % 3 === 1 ? { kind: "tool", uuid: `${prefix}${i}` } : { kind: "assistant", md: "…", uuid: `${prefix}${i}` }));

// ── (1) no lifetime ──────────────────────────────────────────────────────────────────────────────

test("a pending send survives past 20 s — and past any time — without confirmation", () => {
  const list = press([{ kind: "assistant", md: "still working on the earlier step", uuid: "a0" }], TEXT);
  // nothing happens for a minute, then an hour: the wall clock moves on and the kernel's stamps move on
  // with it, and the decision reads neither
  const realNow = Date.now;
  try {
    for (const later of [T0 + 21_000, T0 + 60_000, T0 + 3_600_000]) {
      Date.now = () => later;
      const r = reconcilePending([
        { kind: "assistant", md: "still working on the earlier step", uuid: "a0" },
        { kind: "assistant", md: "…", uuid: "a-" + later, ts: new Date(later).toISOString() },
      ], list);
      assert.equal(r.keep.length, 1, `still pending at +${(later - T0) / 1000}s`);
      assert.equal(r.inject.length, 1, "…and still shown: nothing in the payload accounts for it");
    }
  } finally {
    Date.now = realNow;
  }
  assert.doesNotMatch(RENDER, /OPT_TTL_MS/, "the 20 s backstop is gone from render.ts");
});

test("it clears on the kernel's echo (suppressed) and ends on the landing (retired, with the index)", () => {
  const list = press([{ kind: "assistant", md: "…", uuid: "a1" }], TEXT);
  let r = reconcilePending([{ kind: "assistant", md: "…", uuid: "a1" }, { kind: "user", md: TEXT, uuid: "echo:1" }], list);
  assert.equal(r.keep.length, 1, "the kernel's provisional never retires the entry");
  assert.equal(r.inject.length, 1, "…and ours stays drawn: the echo is hidden for it, one bubble at the tail (T262h)");
  assert.deepEqual(r.echoHide, [1], "the caller hides the kernel's echo");
  r = reconcilePending([
    { kind: "assistant", md: "…", uuid: "a1" },
    { kind: "user", md: TEXT, uuid: "att1", absorbed: true },
    { kind: "tool", uuid: "t9" },
  ], list);
  assert.equal(r.keep.length, 0, "a landed user atom ends it");
  assert.deepEqual(r.landed.map((l) => l.idx), [1], "…naming the landed event: the slot the bubble held");
});

test("an image send lands even though the paths are gone from the text", () => {
  // the composer appends the dragged paths to the typed text; the CLI rewrites them to "[Image #N]" and the
  // kernel strips the placeholders and renders the pictures — so the sent text can never match verbatim
  const text = 'compare with the old one\n/tmp/notes-api/docs/before.png "/tmp/notes-api/docs/after one.png"';
  const imgs = ["/tmp/notes-api/docs/before.png", "/tmp/notes-api/docs/after one.png"];
  assert.equal(pendingBody(text, imgs), "compare with the old one");
  const p = newPending(text, imgs, T0);
  const landed: TailEvent = { kind: "user", uuid: "u7", md: "compare with the old one", images: [{}, {}] };
  assert.equal(landedIn(landed, p), true);
  assert.equal(landedIn({ kind: "user", uuid: "u8", md: "compare with the old one" }, p), false,
    "the body alone is not enough — the landing must carry the pictures");
  assert.equal(landedIn({ kind: "user", uuid: "u9", md: 'compare with the old one\n""', images: [{}, {}] }, p), true,
    "a quoted path's leftover quotes do not break the match");
  assert.equal(landedIn({ kind: "user", uuid: "u10", md: "compare with the old one, then the new", images: [{}] }, p), false,
    "exact body, not a substring");
  assert.equal(landedIn({ kind: "user", uuid: "u11", md: text }, p), true, "paths landing verbatim (an SDK session) match the text itself");
  reconcilePending([{ kind: "assistant", md: "…", uuid: "a1" }], [p]);   // the press: anchored on a tail without it
  const r = reconcilePending([{ kind: "assistant", md: "…", uuid: "a1" }, landed], [p]);
  assert.equal(r.keep.length, 0, "the pictures-bearing atom after the anchor is the landing");
});

test("the kernel's never-delivered verdict ends the entry — its bubble carries the text and the resend", () => {
  const list = press([{ kind: "assistant", md: "…", uuid: "a1" }], TEXT);
  const r = reconcilePending([{ kind: "assistant", md: "…", uuid: "a1" }, { kind: "user", md: TEXT, uuid: "echo:1", undelivered: true }], list);
  assert.equal(r.keep.length, 0);
  assert.equal(r.lost.length, 1);
  assert.equal(r.inject.length, 0, "never a 'sending…' bubble beside a 'never delivered' one");
  // the kernel's undelivered bubble is the resend path: copy to composer / dismiss (undelivered-echo.test.ts)
  assert.match(RENDER, /re\.dataset\.act = "echorestore";/);
});

test("a connection drop marks unconfirmed sends 'not confirmed' — an event, and reversible by a confirmation", () => {
  assert.match(RENDER, /window\.addEventListener\("romp:wsdown", \(\) => markPendingLost\("connection"\)\);/);
  assert.match(RENDER, /if \(m\.type === "pipeState"\) \{ if \(!m\.up\) awaitingFull\.clear\(\); if \(!m\.up\) markPendingLost\("connection"\);/,
    "the VS Code pipe's down edge too — it never fires romp:wsdown");
  assert.match(RENDER, /function markPendingLost\(why: string\): void \{[\s\S]{0,600}?for \(const p of list\) if \(!p\.lost && !p\.received\) \{ p\.lost = why; changed = true; \}/);
  // the bubble says so, in the bare group's own label and on the bubble; ✕ stays the way back
  assert.match(RENDER, /if \(t\.optimistic && t\.lost\) bubble\.title = "not confirmed — the connection dropped after this was sent; ✕ moves it back to the composer to send again";/);
  assert.match(CSS, /\.queued-head \.queued-count \.lost \{ color: var\(--warn\); \}/);
  // a confirmation after the reconnect retires it like any other: the flag is display-only
  const list = press([{ kind: "assistant", md: "…", uuid: "a1" }], "go ahead");
  list[0].lost = "connection";
  const r = reconcilePending([{ kind: "assistant", md: "…", uuid: "a1" }, { kind: "user", md: "go ahead", uuid: "u1" }], list);
  assert.equal(r.keep.length, 0);
});

// ── (4) the anchor: verdicts are read after the send, never from a tail count ─────────────────────

test("a landing 100 events above the tail still ends the bubble — the scan is bounded by the send's anchor, not a count", () => {
  const before: TailEvent[] = [{ kind: "user", md: "first ask", uuid: "u0" }, ...filler(12, "b"), { kind: "tool", uuid: "t-last" }];
  const list = press(before, TEXT);
  assert.equal(list[0].at?.after, "t-last", "anchored on the last stable kernel event at the press");
  list[0].lost = "connection";                   // the socket dropped while the turn ran on
  // the reconnect's full frame: the absorbed atom sits at its SEND time, a hundred events above the tail
  const after: TailEvent[] = [...before, { kind: "user", md: TEXT, uuid: "att1", absorbed: true }, ...filler(100, "g")];
  const r = reconcilePending(after, list);
  assert.equal(r.keep.length, 0, "the landing is after the anchor, wherever the tail has grown to");
  assert.deepEqual(r.landed.map((l) => l.idx), [before.length]);
  // the same depth for the kernel's never-delivered verdict
  const list2 = press(before, TEXT);
  const r2 = reconcilePending([...before, { kind: "user", md: TEXT, uuid: "echo:9", undelivered: true }, ...filler(100, "g")], list2);
  assert.equal(r2.lost.length, 1);
});

test("an anchor that left the resident window (the transcript grew past the wire tail) means everything resident is later", () => {
  const list = press([{ kind: "assistant", md: "…", uuid: "old-anchor" }], TEXT);
  // the next full frame is a re-windowed tail that no longer holds the anchor event
  const r = reconcilePending([...filler(40, "w"), { kind: "user", md: TEXT, uuid: "u-new" }, ...filler(5, "z")], list);
  assert.equal(r.keep.length, 0);
  assert.equal(r.landed[0].idx, 40);
  assert.equal(scanFrom([{ kind: "tool", uuid: "zz" }], { after: "gone", seen: [], queued: 0 }), 0, "the scan starts at the head when the anchor has left the window");
  // and a send into an empty transcript has nothing to anchor on: the head is the start
  const list2 = press([], TEXT);
  assert.equal(list2[0].at?.after, null);
  assert.equal(reconcilePending([{ kind: "user", md: TEXT, uuid: "u1" }], list2).landed.length, 1);
});

test("what was already there at the press is background: an older identical message, a kernel echo, a queued copy", () => {
  const tail: TailEvent[] = [
    { kind: "user", md: TEXT, uuid: "u-old" },
    { kind: "assistant", md: "done", uuid: "a1" },
    { kind: "user", md: TEXT, uuid: "echo:prev" },
    { kind: "queued", texts: [{ md: TEXT }] },
  ];
  const list = press(tail, TEXT);
  assert.equal(list[0].at?.after, "a1", "the anchor skips the kernel's echo: it is replaced when its text lands");
  assert.deepEqual(list[0].at?.seen, ["u-old", "echo:prev"]);
  assert.equal(list[0].at?.queued, 1);
  const r = reconcilePending(tail, list);
  assert.equal(r.keep.length, 1, "not retired by the older copy");
  assert.equal(list[0].received, undefined, "the old echo and the old queued copy prove nothing about THIS send");
  assert.equal(r.inject.length, 1, "…and cover nothing: our bubble shows beside the older copies (two sends, two bubbles)");
});

// ── (5) the bubble sits at the TAIL (T252d): render.ts appends one bare group after every kernel event ──

// ── (T252c) identity from the kernel, on this module's wire: the send id on the queued copies and on the landed atom ──
// Upstream's T252c latches a kernel-minted `qid` from the first copy attributed by text and position. Here the id
// is minted at the press (section 16) and every kernel copy of the send names it (`texts[].sendId` on a queued
// copy, `sendIds` on a user event), so nothing is latched; the scenarios are upstream's, read on this wire.

test("our own send's identity rules landing, cover and hiding: a same-text copy of another send is never ours (T252c)", () => {
  const tail: TailEvent[] = [{ kind: "assistant", md: "…", uuid: "a1" }];
  const p = newPending("continue", undefined, T0);
  reconcilePending(tail, [p]);
  // the kernel lists our copy with its id: the copy covers us (ours drawn at the tail, that copy hidden)
  let r = reconcilePending([...tail, { kind: "queued", texts: [{ md: "continue", sendId: p.sendId }] }], [p]);
  assert.deepEqual(r.unqueue, [p]);
  assert.equal(queuedCopyToHide([{ md: "continue", sendId: "c8" }, { md: "continue", sendId: p.sendId }], "continue", p.sendId), 1, "the copy to hide is OURS by id, not the newest by text");
  // another client's same-text copy landing does NOT retire us: only the record carrying our id does
  r = reconcilePending([...tail, { kind: "user", md: "continue", uuid: "uX", sendIds: ["c8"] }, { kind: "queued", texts: [{ md: "continue", sendId: p.sendId }] }], [p]);
  assert.deepEqual(r.keep, [p], "a same-text landing with another id is not ours");
  r = reconcilePending([...tail, { kind: "user", md: "continue", uuid: "uX", sendIds: ["c8"] }, { kind: "user", md: "continue", uuid: "uMine", sendIds: [p.sendId] }], [p]);
  assert.deepEqual(r.landed.map((l) => [l.p, l.idx]), [[p, 2]], "our landing, by id, even behind a same-text one");
  // the echo path, the same: the echo names the send, and so does the record that lands it
  const q = newPending("go", undefined, T0 + 1);
  reconcilePending(tail, [q]);
  r = reconcilePending([...tail, { kind: "user", md: "go", uuid: "echo:g1", sendIds: [q.sendId] }], [q]);
  assert.deepEqual([r.inject, r.keep, r.echoHide], [[q], [q], [1]], "the echo naming the send proves receipt and is hidden for it; ours stays drawn (T262h)");
  r = reconcilePending([...tail, { kind: "user", md: "go", uuid: "uG", sendIds: [q.sendId] }], [q]);
  assert.deepEqual(r.landed.map((l) => l.idx), [1]);
});

test("identity edges: an id-less copy beside an echo, a landing carrying several ids, and an identified copy whose landing lost its id (T252c review)", () => {
  const tail: TailEvent[] = [{ kind: "assistant", md: "…", uuid: "a1" }];
  // the tmux route: the queued copy carries no id, the echo a random uuid and no ids, the landing nothing: text
  // decides throughout, and our bubble never doubles beside the kernel's copies
  const p = newPending("go on", undefined, T0);
  reconcilePending(tail, [p]);
  let r = reconcilePending([...tail, { kind: "queued", texts: [{ md: "go on" }] }], [p]);
  assert.deepEqual(r.unqueue, [p]);
  r = reconcilePending([...tail, { kind: "user", md: "go on", uuid: "echo:random" }], [p]);
  assert.deepEqual([r.inject.length, r.echoHide], [1, [1]], "the echo is attributed by text: hidden, ours stays (T262h)");
  r = reconcilePending([...tail, { kind: "user", md: "go on", uuid: "uL" }], [p]);
  assert.deepEqual(r.landed.map((l) => l.idx), [1]);
  // a record the CLI wrote from two sends lands stamped with both ids: each retires on its own
  const [x, y] = press(tail, "one", "two");
  reconcilePending([...tail, { kind: "queued", texts: [{ md: "one", sendId: x.sendId }, { md: "two", sendId: y.sendId }] }], [x, y]);
  r = reconcilePending([...tail, { kind: "user", md: "one two", uuid: "uXY", blocks: ["one", "two"], sendIds: [x.sendId, y.sendId] }], [x, y]);
  assert.deepEqual(r.landed.map((l) => [l.p.text, l.idx]), [["one", 1], ["two", 1]]);
});

test("queuedCopyToHide: the newest not-yet-hidden copy of the text, never a copy the kernel marked non-cancelable", () => {
  // the kernel marks a queued copy cancelable:false when no recall exists (a tmux queue): that copy stays the
  // one bubble shown, with its honest "can't be recalled" tooltip, and ours is suppressed as before — hiding it
  // behind our bubble's ✕ offered a cancel the kernel would refuse (review of the first cut)
  const texts = [{ md: "a" }, { md: "b", cancelable: false }, { md: "a", hiddenByPending: true }, { md: "a" }];
  assert.equal(queuedCopyToHide(texts, "a"), 3, "the newest visible copy");
  assert.equal(queuedCopyToHide(texts.slice(0, 3), "a"), 0, "…skipping one already hidden");
  assert.equal(queuedCopyToHide(texts, "b"), -1, "a non-cancelable copy is never hidden");
  assert.equal(queuedCopyToHide(texts, "zzz"), -1);
  assert.equal(queuedCopyToHide([{ md: " a " }], "a"), 0, "trimmed match, like every other text test");
  // render.ts: a copy the helper refuses keeps covering our bubble (the send leaves `inject`); the bubble's id
  // goes along, so the copy hidden is the one naming the send (section 18 below)
  assert.match(RENDER, /const k = queuedCopyToHide\(q\.texts, p\.text, p\.sendId\);/);
  assert.match(RENDER, /if \(k < 0\) return null;\s*\/\/ no copy to hide/);
  assert.match(RENDER, /const hid = hideQueuedCopy\(s, p\);\s*\n\s*if \(hid === null\) covered\.add\(p\); else if \(hid\.held\) heldBy\.set\(p, hid\.held\);/);
  assert.match(RENDER, /const inject = r\.inject\.filter\(\(p\) => !covered\.has\(p\)\);/);
});

test("the kernel's queued copy at the tail is hidden for a send drawn as our own bubble — one bubble per message (T252)", () => {
  const tail: TailEvent[] = [{ kind: "assistant", md: "…", uuid: "a1" }];
  const list = press(tail, TEXT);
  const r = reconcilePending([...tail, { kind: "tool", uuid: "t1" }, { kind: "queued", texts: [{ md: TEXT }] }], list);
  assert.equal(list[0].received, true, "the kernel's copy proves receipt");
  assert.deepEqual(r.inject, [list[0]], "…but ours stays drawn, at the tail");
  assert.deepEqual(r.unqueue, [list[0]], "and the caller drops the kernel's tail copy for it");
  // an ECHO atom proves receipt and is hidden in turn (T262h): ours is the one bubble, at the tail, until the landing
  const r2 = reconcilePending([...tail, { kind: "user", md: TEXT, uuid: "echo:1" }], press(tail, TEXT));
  assert.equal(r2.inject.length, 1);
  assert.equal(r2.unqueue.length, 0);
  assert.deepEqual(r2.echoHide, [1]);
});

test("render.ts appends the pending sends as ONE bare group at the tail, in send order; strips its own injections before applying kernel indices; carries no header or cue (T252d)", () => {
  assert.match(RENDER, /s\.events\.push\(\{ kind: "queued", bare: true, texts: inject\.map\(mk\), uuid: OPT_PREFIX \+ inject\[0\]\.ts/,
    "one bare group pushed at the tail, the sends in list (send) order");
  assert.doesNotMatch(RENDER, /injectionGroups|placementIndex/, "the send-slot placement machinery is gone from render.ts");
  const fn = RENDER.split("function reconcileOptimisticInner(")[1].split("\nfunction ")[0];   // the guarded body (T262h)
  assert.match(fn, /settle\(inject\.map\(\(p\) => p\.text\)\);/, "the repaint signature is the texts alone: the tail slot moves with every push by design");
  assert.match(RENDER, /function stripOptimistic\(s: Session, keepHeld = false\): void \{/, "one strip, used by every ingest path (keepHeld: the pending reconcile leaves the held kernel copies in, T262i)");
  const tail = RENDER.slice(RENDER.indexOf("function chatTail(msg: any) {"), RENDER.indexOf("s.events.length = from;"));
  assert.match(tail, /stripOptimistic\(s\);/, "the delta's kernel index is applied to KERNEL events only — a mid-array bubble would shift it");
  // …but only once the delta is going to be applied: stripping before the gap/head early returns left s.events
  // without the bubble while the DOM still showed it (review of the first cut)
  const afterReturns = tail.slice(tail.indexOf("if (from < 0) return;"));
  assert.match(afterReturns, /stripOptimistic\(s\);/, "the strip sits after both early returns");
  assert.doesNotMatch(tail.slice(0, tail.indexOf("if (from > kernelLen) {")), /stripOptimistic\(s\);/, "…and not before the gap check");
  assert.match(tail, /const kernelLen = s\.events\.reduce\(\(n, e\) => n \+ \(isOptimistic\(e\) \|\| isHeldGroup\(e\) \? 0 : 1\), 0\);/, "the gap check counts kernel events without mutating");
  for (const gone of ["absorbedHeader", "absorbedCues", "noteAbsorbedLanding", "renderAbsorbedCue", "appendAbsorbedCues", "dismissAbsorbedCue", "cueRendered", "abjump", "abdismiss", "absorbed-tag", "turn-absorbed-cue"])
    assert.ok(!RENDER.includes(gone), gone + " is gone from render.ts");
  for (const gone of [".absorbed-tag", ".turn-absorbed-cue", ".absorbed-cue-line", ".absorbed-cue-act"])
    assert.ok(!CSS.includes(gone), gone + " is gone from styles.css");
  // the "not confirmed" state and the ✕ on the pending bubble itself stay
  assert.match(RENDER, /if \(t\.optimistic && t\.lost\) bubble\.dataset\.lost = "1";/);
  assert.match(RENDER, /if \(t\.optimistic\) x\.dataset\.qopt = "1";/);
});

test("a resend of a never-delivered message is not retired by the old verdict — only a verdict after the send counts", () => {
  // the flow the never-delivered bubble offers: copy to composer, Enter — the old bubble is still in the tail
  const tail: TailEvent[] = [{ kind: "assistant", md: "…", uuid: "a1" }, { kind: "user", md: TEXT, uuid: "echo:old", undelivered: true }];
  const list = press(tail, TEXT);
  let r = reconcilePending(tail, list);
  assert.equal(r.lost.length, 0, "the old verdict is about the old send");
  assert.equal(r.keep.length, 1);
  assert.equal(r.inject.length, 1, "…and the old verdict is not a provisional either: our bubble shows");
  assert.equal(provisionalIn(tail[1], list[0]), false, "a never-delivered echo never suppresses");
  // the kernel's echo for the resend, then ITS verdict — that one ends the entry
  r = reconcilePending([...tail, { kind: "user", md: TEXT, uuid: "echo:new" }], list);
  assert.deepEqual([r.inject.length, r.echoHide], [1, [tail.length]], "ours stays, the echo is hidden (T262h)");
  r = reconcilePending([...tail, { kind: "user", md: TEXT, uuid: "echo:new", undelivered: true }], list);
  assert.equal(r.lost.length, 1);
  // a shorter send that the old never-delivered text merely contains is not its resend at all
  const list2 = press([{ kind: "user", md: "ok, go ahead and rename it", uuid: "echo:old", undelivered: true }], "go ahead");
  assert.equal(reconcilePending([{ kind: "user", md: "ok, go ahead and rename it", uuid: "echo:old", undelivered: true }], list2).keep.length, 1);
});

// ── (7) exact text, one landing per send ─────────────────────────────────────────────────────────

test("two identical sends in flight: the first landing retires the first, the second the second — across pushes", () => {
  const tail: TailEvent[] = [{ kind: "assistant", md: "…", uuid: "a1" }];
  const list = press(tail, "continue", "continue");
  let r = reconcilePending([...tail, { kind: "user", md: "continue", uuid: "u1", absorbed: true }, { kind: "tool", uuid: "t1" }], list);
  assert.equal(r.landed.length, 1, "one landing, one entry");
  assert.equal(r.landed[0].p, list[0], "…the earlier send");
  assert.equal(r.keep.length, 1);
  assert.equal(r.inject.length, 1, "the second still shows: its message has not landed");
  // the next push (the first entry is gone from the list): the claimed landing stays claimed
  r = reconcilePending([...tail, { kind: "user", md: "continue", uuid: "u1", absorbed: true }, { kind: "tool", uuid: "t1" }], r.keep);
  assert.equal(r.keep.length, 1, "the first send's landing does not retire the second");
  r = reconcilePending([...tail, { kind: "user", md: "continue", uuid: "u1", absorbed: true }, { kind: "tool", uuid: "t1" }, { kind: "user", md: "continue", uuid: "u2" }], r.keep);
  assert.equal(r.landed.length, 1);
  assert.equal(r.landed[0].idx, 3, "the second landing is the second send's");
  // both landing in one push: attributed in order
  const list2 = press(tail, "continue", "continue");
  r = reconcilePending([...tail, { kind: "user", md: "continue", uuid: "u1" }, { kind: "user", md: "continue", uuid: "u2" }], list2);
  assert.deepEqual(r.landed.map((l) => [l.p, l.idx]), [[list2[0], 1], [list2[1], 2]]);
});

test("exact text: a pending 'test' is not retired when 'test the continue button' lands, nor the reverse", () => {
  const tail: TailEvent[] = [{ kind: "assistant", md: "…", uuid: "a1" }];
  const list = press(tail, "test", "test the continue button");
  let r = reconcilePending([...tail, { kind: "user", md: "test the continue button", uuid: "u1" }], list);
  assert.deepEqual(r.landed.map((l) => l.p.text), ["test the continue button"]);
  assert.deepEqual(r.keep.map((p) => p.text), ["test"]);
  r = reconcilePending([...tail, { kind: "user", md: "test the continue button", uuid: "u1" }, { kind: "user", md: "test", uuid: "u2" }], r.keep);
  assert.deepEqual(r.landed.map((l) => [l.p.text, l.idx]), [["test", 2]]);
  // edge whitespace is the one tolerance: the composer trims, the kernel strips
  assert.equal(landedIn({ kind: "user", md: "  test\n", uuid: "u3" }, newPending("test")), true);
  // the kernel's echo and queued bubble are matched the same way
  const p = newPending("test");
  assert.equal(provisionalIn({ kind: "user", md: "test the continue button", uuid: "echo:1" }, p), false);
  assert.equal(provisionalIn({ kind: "queued", texts: [{ md: "test the continue button" }] }, p), false);
  assert.equal(provisionalIn({ kind: "queued", texts: [{ md: "test" }] }, p), true);
});

// ── (8) a connection drop repaints once ──────────────────────────────────────────────────────────

test("markPendingLost repaints only when an entry actually changed — the shim fires the down edge on every redial", () => {
  const fn = RENDER.slice(RENDER.indexOf("function markPendingLost("), RENDER.indexOf("\n}\n", RENDER.indexOf("function markPendingLost(")));
  assert.match(fn, /let changed = false;/);
  assert.match(fn, /if \(!changed\) continue;/, "an unchanged session is neither reconciled nor marked stale");
  assert.match(fn, /if \(sid === activeId\) activeChanged = true;/);
  assert.match(fn, /if \(activeChanged\) appendActive\(\);/, "the active chat rebuilds only for its own change");
  assert.doesNotMatch(fn, /if \(activeId && pendingSent\.has\(activeId\)\) appendActive\(\);/);
});

// ── (9) the bare label is per bubble ─────────────────────────────────────────────────────────────

test("the bare group's label counts lost and sending bubbles separately", () => {
  const texts = (n: number, m: number) => bareGroupLabel(n, m).parts.map((p) => (p.lost ? "!" : "") + p.text);
  assert.deepEqual(texts(0, 1), ["sending…"]);
  assert.deepEqual(texts(0, 3), ["sending 3…"]);
  assert.deepEqual(texts(1, 0), ["!not confirmed"]);
  assert.deepEqual(texts(2, 0), ["!2 not confirmed"]);
  assert.deepEqual(texts(1, 1), ["!not confirmed", "sending…"], "a mixed group names both states, the lost one first");
  assert.deepEqual(texts(1, 2), ["!not confirmed", "sending 2…"]);
  assert.match(bareGroupLabel(1, 0).title, /^The connection dropped after this was sent/);
  assert.match(bareGroupLabel(0, 1).title, /^on its way to the session/);
  assert.match(bareGroupLabel(1, 1).title, /^The connection dropped after this was sent[\s\S]*The rest: on its way/);
  // render.ts builds the label from the bubbles' own states, and the ✕'s recount reads them back off the
  // surviving bubbles (data-lost) — never off the label's previous class
  assert.match(RENDER, /const nLost = texts\.filter\(\(t\) => t\.lost\)\.length;\s*\n\s*fillBareLabel\(label, nLost, texts\.length - nLost\);/);
  assert.match(RENDER, /if \(t\.optimistic && t\.lost\) bubble\.dataset\.lost = "1";/);
  assert.match(RENDER, /const nLost = bubbles\.filter\(\(b\) => \(b as HTMLElement\)\.dataset\.lost === "1"\)\.length;\s*\n\s*fillBareLabel\(label, nLost, bubbles\.length - nLost\);/);
  assert.doesNotMatch(RENDER, /label\.classList\.contains\("lost"\)/);
  assert.match(RENDER, /const span = el\("span", part\.lost \? "lost" : ""\);/, "only the lost part wears the warn color");
});

// ── (10) the kernel's own copy clears "not confirmed" ────────────────────────────────────────────

test("the kernel's echo or queued copy seen after the press proves receipt: 'not confirmed' clears and never returns", () => {
  const tail: TailEvent[] = [{ kind: "assistant", md: "…", uuid: "a1" }];
  const list = press(tail, TEXT);
  list[0].lost = "connection";                                   // the drop, as markPendingLost writes it
  let r = reconcilePending([...tail, { kind: "user", md: TEXT, uuid: "echo:1" }], list);
  assert.equal(list[0].lost, undefined, "the kernel minted this echo on receipt of the send: the drop did not lose it");
  assert.equal(list[0].received, true);
  r = reconcilePending(tail, list);                              // the echo blinks in its echo→landed handoff
  assert.equal(r.inject.length, 1);
  assert.equal(r.inject[0].lost, undefined, "…and our bubble steps back in as 'sending…', not as a false loss");
  // a queued copy that was not listed at the press is the same proof
  const list2 = press([{ kind: "queued", texts: [{ md: TEXT }] }], TEXT);
  list2[0].lost = "connection";
  reconcilePending([{ kind: "queued", texts: [{ md: TEXT }] }], list2);
  assert.equal(list2[0].lost, "connection", "one copy at the press, one copy now: nothing new");
  reconcilePending([{ kind: "queued", texts: [{ md: TEXT }, { md: TEXT }] }], list2);
  assert.equal(list2[0].lost, undefined, "a second copy is this send's");
  // a later drop leaves a received send alone (render.ts markPendingLost's guard)
  assert.match(RENDER, /if \(!p\.lost && !p\.received\) \{ p\.lost = why; changed = true; \}/);
});

// ── (11) receipt is attributed per send, like landings ───────────────────────────────────────────

test("two identical sends, one kernel echo: the first is received and covered; the second still shows, still unconfirmed", () => {
  const tail: TailEvent[] = [{ kind: "assistant", md: "…", uuid: "a1" }];
  const list = press(tail, "continue", "continue");
  let r = reconcilePending([...tail, { kind: "user", md: "continue", uuid: "echo:1" }], list);
  assert.deepEqual(list.map((p) => p.received), [true, undefined], "one echo is one send's receipt");
  assert.deepEqual(r.inject, [list[0], list[1]], "both bubbles stay ours; the echo that proved the first's receipt is hidden (T262h)");
  assert.deepEqual(r.echoHide, [1]);
  assert.deepEqual(list[1].at?.seen, ["echo:1"], "the claimed echo is background for the later send");
  // the drop (as render.ts markPendingLost writes it): only the unconfirmed send is marked
  for (const p of list) if (!p.lost && !p.received) p.lost = "connection";
  assert.deepEqual(list.map((p) => p.lost), [undefined, "connection"]);
  // the same echo on later pushes proves nothing new — even once the first entry is gone (its ✕)
  r = reconcilePending([...tail, { kind: "user", md: "continue", uuid: "echo:1" }], [list[1]]);
  assert.equal(list[1].received, undefined);
  assert.equal(list[1].lost, "connection", "the bubble the kernel never received keeps saying so");
  assert.equal(r.inject.length, 1);
  // a second echo is the second send's
  reconcilePending([...tail, { kind: "user", md: "continue", uuid: "echo:1" }, { kind: "user", md: "continue", uuid: "echo:2" }], list);
  assert.deepEqual(list.map((p) => p.received), [true, true]);
  assert.equal(list[1].lost, undefined);
  // the claimed echo's verdict is the claimant's too: its never-delivered flag ends the first send only
  const list2 = press(tail, "continue", "continue");
  reconcilePending([...tail, { kind: "user", md: "continue", uuid: "echo:1" }], list2);
  r = reconcilePending([...tail, { kind: "user", md: "continue", uuid: "echo:1", undelivered: true }], list2);
  assert.deepEqual(r.lost, [list2[0]]);
  assert.deepEqual(r.keep, [list2[1]]);
});

test("both 'not confirmed', one echo arrives: one label clears, the other stays — and the landing retires the received one", () => {
  const tail: TailEvent[] = [{ kind: "assistant", md: "…", uuid: "a1" }];
  const list = press(tail, "continue", "continue");
  list[0].lost = list[1].lost = "connection";
  reconcilePending([...tail, { kind: "user", md: "continue", uuid: "echo:1" }], list);
  assert.deepEqual(list.map((p) => p.lost), [undefined, "connection"]);
  const r = reconcilePending([...tail, { kind: "user", md: "continue", uuid: "u1" }], list);   // the echo→landed handoff
  assert.deepEqual(r.landed.map((l) => l.p), [list[0]]);
  assert.deepEqual(r.keep, [list[1]]);
  assert.equal(list[1].lost, "connection", "still unconfirmed: the kernel has shown one copy, and it landed");
});

test("queued copies are handed out by position: one new copy confirms one send; the copies a press listed are its background", () => {
  const tail: TailEvent[] = [{ kind: "assistant", md: "…", uuid: "a1" }];
  const list = press(tail, "continue", "continue");
  let r = reconcilePending([...tail, { kind: "queued", texts: [{ md: "continue" }] }], list);
  assert.deepEqual(list.map((p) => p.received), [true, undefined]);
  assert.deepEqual(r.inject, [list[0], list[1]], "both drawn in place (T252); the kernel's one copy is hidden for the first");
  assert.deepEqual(r.unqueue, [list[0]]);
  r = reconcilePending([...tail, { kind: "queued", texts: [{ md: "continue" }, { md: "continue" }] }], list);
  assert.deepEqual(list.map((p) => p.received), [true, true]);
  assert.deepEqual(r.unqueue, [list[0], list[1]], "two kernel copies, both hidden: two bubbles for two sends, in place");
  // a second press that already saw the first send's copy counts it as background, not as its own
  const a = press(tail, "continue");
  reconcilePending([...tail, { kind: "queued", texts: [{ md: "continue" }] }], a);
  const b = newPending("continue", undefined, T0 + 1);
  const both = [a[0], b];
  reconcilePending([...tail, { kind: "queued", texts: [{ md: "continue" }] }], both);   // b's press: one copy listed already
  assert.equal(b.at?.queued, 1);
  assert.equal(b.received, undefined, "the copy b's press listed is a's");
  reconcilePending([...tail, { kind: "queued", texts: [{ md: "continue" }, { md: "continue" }] }], both);
  assert.deepEqual(both.map((p) => p.received), [true, true]);
});

// ── (12) the ✕ removes the bubble's OWN entry ────────────────────────────────────────────────────

test("✕ on one of two identical bubbles removes that bubble's entry, never the first with the text", () => {
  const tail: TailEvent[] = [{ kind: "assistant", md: "…", uuid: "a1" }];
  const A = newPending("continue", undefined, T0), B = newPending("continue", undefined, T0 + 5000);
  const list = [A, B];
  reconcilePending(tail, list);
  A.lost = "connection";                                   // A dropped; B was sent after the reconnect
  let r = reconcilePending(tail, list);
  assert.deepEqual(r.inject.map((p) => p.lost), ["connection", undefined], "the group reads 'not confirmed · sending…'");
  // the ✕ on B's bubble names B (data-qts) — the first-with-the-text lookup took A
  assert.equal(dropPending(list, "continue", B.ts), B);
  assert.deepEqual(list, [A]);
  r = reconcilePending(tail, list);
  assert.deepEqual(r.inject.map((p) => p.lost), ["connection"], "the dismissed bubble stays gone; the lost one stays put");
  // the ✕ on the LOST bubble of the pair
  const C = newPending("continue", undefined, T0), D = newPending("continue", undefined, T0 + 5000);
  const list2 = [C, D];
  reconcilePending(tail, list2);
  C.lost = "connection";
  assert.equal(dropPending(list2, "continue", C.ts), C);
  assert.deepEqual(list2, [D]);
  // a bubble whose entry a push already retired removes nothing — never a neighbour with the same text
  assert.equal(dropPending(list2, "continue", T0 + 999), undefined);
  assert.deepEqual(list2, [D]);
  // a ✕ on the KERNEL's own queued copy names no entry of ours: the first pending send with the text goes
  assert.equal(dropPending(list2, "continue"), D);
  assert.deepEqual(list2, []);
  // render.ts: the identity rides the bubble's ✕, and the handler removes by it
  assert.match(RENDER, /const mk = \(p: PendingSend\) => \(\{ md: p\.text, optimistic: true, cancelable: true, imgPaths: p\.imgPaths, lost: p\.lost, qts: p\.ts, sendId: p\.sendId \}\);/);
  assert.match(RENDER, /if \(t\.optimistic && t\.qts !== undefined\) x\.dataset\.qts = String\(t\.qts\);/);   // a kernel copy's own qts (its enqueue stamp, T252c) is not an entry of ours
  assert.match(RENDER, /const qts = el\.dataset\.qts !== undefined \? Number\(el\.dataset\.qts\) : undefined;\s*\n\s*if \(dropPending\(list, qmd, qts, el\.dataset\.qsid\)\) \{ if \(list\.length\) pendingSent\.set\(sidQ, list\); else pendingSent\.delete\(sidQ\); \}/);
  assert.doesNotMatch(RENDER, /list\.findIndex\(\(p\) => p\.text === qmd\)/);
});

// ── (13) a late stamp reads the events' own times ────────────────────────────────────────────────

test("a send pressed against no frame (a placeholder tab): the first frame's copy of it is this send's, not background", () => {
  const isoAt = (s: number) => new Date(s * 1000).toISOString();   // kernel.py iso(t): ISO-8601 UTC, whole seconds
  const pressMs = T0 + 250;                                          // the press, on the client's clock
  const S = Math.floor(pressMs / 1000);
  const late = (): PendingSend => ({ ...newPending(TEXT, undefined, pressMs), late: true });   // registerOptimistic, no resident session
  // the first frame holds an older identical message, the last step before the send, this send's own
  // echo, and a step after it
  const frame: TailEvent[] = [
    { kind: "user", md: TEXT, uuid: "u-old", ts: isoAt(S - 3600) },
    { kind: "assistant", md: "…", uuid: "a1", ts: isoAt(S - 2) },
    { kind: "user", md: TEXT, uuid: "echo:1", ts: isoAt(S) },     // the kernel stamps the echo at its receipt: the press's second, or later
    { kind: "assistant", md: "…", uuid: "a2", ts: isoAt(S + 1) },
  ];
  let list = [late()];
  let r = reconcilePending(frame, list);
  assert.equal(list[0].at?.after, "a1", "the anchor is the last stable event stamped BEFORE the press — not a2");
  assert.deepEqual(list[0].at?.seen, ["u-old"], "the old message is background; this send's echo is not");
  assert.equal(list[0].received, true);
  assert.deepEqual([r.inject.length, r.echoHide], [1, [2]], "the kernel's echo is hidden for our bubble: no double bubble (T262h)");
  const landed: TailEvent[] = [frame[0], frame[1], { kind: "user", md: TEXT, uuid: "u1", ts: isoAt(S) }, frame[3]];
  r = reconcilePending(landed, list);
  assert.equal(r.keep.length, 0, "the echo→landed handoff retires it");
  // the CLI was idle: the first frame already holds the LANDED atom
  list = [late()];
  r = reconcilePending(landed, list);
  assert.equal(list[0].at?.after, "a1", "…and the landed atom is not the anchor either");
  assert.deepEqual(r.landed.map((l) => l.idx), [2], "it is the landing: the bubble ends, instead of never ending");
  // a first frame that predates the send entirely stamps exactly as a press-time stamp would
  list = [late()];
  reconcilePending([frame[0], frame[1]], list);
  assert.deepEqual(list[0].at, { after: "a1", seen: ["u-old"], queued: 0 });
  // a press-time stamp reads no stamp: its frame predates the press by construction, so an identical
  // message that landed within the press's own second is still background
  const prompt = press([frame[1], { kind: "user", md: TEXT, uuid: "u-same-second", ts: isoAt(Math.floor(T0 / 1000)) }], TEXT);
  assert.deepEqual(prompt[0].at?.seen, ["u-same-second"]);
  assert.equal(prompt[0].at?.after, "u-same-second");
  // render.ts marks the entry when the press finds no resident session, and stamps it nowhere else
  assert.match(RENDER, /const p = newPending\(text, imgPaths\);\s*\n\s*arr\.push\(p\);/);
  assert.match(RENDER, /if \(!s\) \{ p\.late = true; return p; \}/);
  // the clock the bound compares against: the kernel stamps the echo atom at its receipt of the send, in
  // whole seconds (sdk_backend.py send). That the chat builder ships every event's stamp as iso(t) is
  // proven behaviourally, not pinned here: tests/test_kernel_fed_echo_absorbed.py (ChatEventSaysAbsorbed)
  // reads a built user event's ts back as iso(t) of its atom.
  const SDK = fs.readFileSync(path.resolve(process.cwd(), "..", "kernel", "sdk_backend.py"), "utf8");
  assert.match(SDK, /sent_t = int\(time\.time\(\)\)/);
  assert.match(SDK, /"t": sent_t\b/);
});

test("a late stamp presumes the first frame's newest queued copy of the text is this send's own (busy and held queues)", () => {
  const isoAt = (s: number) => new Date(s * 1000).toISOString();
  const pressMs = T0 + 250;
  const S = Math.floor(pressMs / 1000);
  const late = (): PendingSend => ({ ...newPending(TEXT, undefined, pressMs), late: true });
  const step: TailEvent = { kind: "assistant", md: "…", uuid: "a1", ts: isoAt(S - 2) };
  // the queued bubble carries no stamp: a busy session's queue (the CLI holds the text) and a held one
  // (an account limit; the kernel holds it, for hours) look the same to the stamp
  for (const q of [{ kind: "queued", texts: [{ md: TEXT }] }, { kind: "queued", texts: [{ md: TEXT }], held: { reason: "limit" } }] as TailEvent[]) {
    const list = [late()];
    let r = reconcilePending([step, q], list);
    assert.equal(list[0].at?.queued, 0, "the frame's one copy is presumed this press's, not background");
    assert.equal(r.inject.length, 1, "ours stays drawn at its send slot (T252)…");
    assert.equal(r.unqueue.length, 1, "…and the kernel's copy is the one hidden: no double bubble");
    assert.equal(list[0].received, true);
    // every later push, the same copy keeps proving receipt — the entry never sat unconfirmed until the CLI took it
    r = reconcilePending([step, q], list);
    assert.equal(r.inject.length, 1);
    assert.equal(r.unqueue.length, 1);
    // …and when the CLI takes the text, the landing ends the bubble (a tmux route: no echo in between)
    r = reconcilePending([step, { kind: "user", md: TEXT, uuid: "u1", ts: isoAt(S + 40) }], list);
    assert.deepEqual(r.landed.map((l) => l.idx), [1]);
  }
  // an older identical copy queued BEFORE the press sits at the head: the newest copy is ours, the older
  // one is background, so a second frame with a third copy would prove nothing about this send
  const list = [late()];
  reconcilePending([step, { kind: "queued", texts: [{ md: TEXT }, { md: TEXT }] }], list);
  assert.equal(list[0].at?.queued, 1);
  // the frame was built before the kernel received the send: no copy yet, none presumed; the copy that
  // follows covers it, exactly as at a press-time stamp
  const early = [late()];
  let r = reconcilePending([step], early);
  assert.deepEqual(early[0].at, { after: "a1", seen: [], queued: 0 });
  assert.equal(r.inject.length, 1);
  r = reconcilePending([step, { kind: "queued", texts: [{ md: TEXT }] }], early);
  assert.equal(r.inject.length, 1);
  assert.equal(r.unqueue.length, 1, "the copy that follows is this send's: hidden, ours drawn, receipt proven");
  assert.equal(early[0].received, true);
  // two identical sends pressed against the same placeholder frame own one copy EACH — and when the frame
  // lists only one of them (the kernel had not received the second), the second waits for its own
  const pair = [late(), late()];
  r = reconcilePending([step, { kind: "queued", texts: [{ md: TEXT }, { md: TEXT }] }], pair);
  assert.deepEqual(pair.map((p) => p.at?.queued), [0, 0]);
  assert.equal(r.inject.length, 2, "both copies are the pair's: both hidden, both of ours drawn");
  assert.equal(r.unqueue.length, 2);
  const pair2 = [late(), late()];
  r = reconcilePending([step, { kind: "queued", texts: [{ md: TEXT }] }], pair2);
  assert.deepEqual(pair2.map((p) => p.at?.queued), [0, 0], "fewer copies than presses: the count floors at zero");
  assert.equal(r.inject.length, 2, "both drawn; one copy proves one send, the other waits for its own");
  assert.equal(r.unqueue.length, 1);
  r = reconcilePending([step, { kind: "queued", texts: [{ md: TEXT }, { md: TEXT }] }], pair2);
  assert.equal(r.unqueue.length, 2);
  // a press-time stamp presumes nothing: its frame predates the press, so every listed copy is background
  const prompt = press([step, { kind: "queued", texts: [{ md: TEXT }] }], TEXT);
  assert.equal(prompt[0].at?.queued, 1);
  // the ✕ on the kernel's copy (which names no entry) drops the one it covers — ours — so cancelling the
  // queued send leaves no orphan bubble behind
  const covered = [late()];
  reconcilePending([step, { kind: "queued", texts: [{ md: TEXT }] }], covered);
  const mine = covered[0];
  assert.equal(dropPending(covered, TEXT), mine);
  assert.equal(covered.length, 0);
});

test("every composer send posts a clientDiag breadcrumb — sid, time, length, route; never the text", () => {
  const m = RENDER.match(/vscodeApi\.postMessage\(\{ type: "clientDiag", surface: "chat", what: "send",\s*\n\s*data: \{ ([^}]*) \} \}\);/);
  assert.ok(m, "the breadcrumb is posted from routeUserMessage");
  const fields = m![1];
  assert.match(fields, /\bsid\b/); assert.match(fields, /ts: Date\.now\(\)/); assert.match(fields, /len: text\.length/); assert.match(fields, /route:/);
  assert.doesNotMatch(fields, /\btext\b(?!\.length)/, "the text itself never leaves the client");
  assert.doesNotMatch(fields, /\bbody\b|\bmd\b/);
  // one owner: the breadcrumb sits in routeUserMessage, which every send path (plain, quote, follow-up, staged flush) goes through
  const fn = RENDER.slice(RENDER.indexOf("function routeUserMessage("), RENDER.indexOf("\n}\n", RENDER.indexOf("function routeUserMessage(")));
  assert.ok(fn.includes('what: "send"'));
});

// ── (15) one record, several sends ───────────────────────────────────────────────────────────────

test("two back-to-back sends the CLI took as ONE record retire both bubbles; a third with other text stays", () => {
  const tail: TailEvent[] = [{ kind: "assistant", md: "…", uuid: "a1" }];
  const list = press(tail, "continue", "continue", "and the docstring");
  // the kernel's user event for the batched record: md is the blocks joined; `blocks` lists each send
  const rec: TailEvent = { kind: "user", md: "continue continue", uuid: "u1", blocks: ["continue", "continue"] };
  const r = reconcilePending([...tail, rec], list);
  assert.deepEqual(r.landed.map((l) => [l.p, l.idx]), [[list[0], 1], [list[1], 1]], "one copy per block, in send order");
  assert.deepEqual(r.keep, [list[2]], "the third send's text is in no block");
  assert.equal(landedIn(rec, list[2]), false);
  assert.equal(landedIn(rec, list[0]), true);
  // two sends of DIFFERENT texts batched the same way: each block is its own send's landing
  const list2 = press(tail, "continue", "and the docstring");
  const rec2: TailEvent = { kind: "user", md: "continue and the docstring", uuid: "u2", blocks: ["continue", "and the docstring"] };
  const r2 = reconcilePending([...tail, rec2], list2);
  assert.deepEqual(r2.landed.map((l) => [l.p.text, l.idx]), [["continue", 1], ["and the docstring", 1]]);
  // a record of two copies that was already there at the press is background twice over
  const list3 = press([...tail, rec], "continue");
  assert.deepEqual(list3[0].at?.seen, ["u1", "u1"], "seen counts copies, not events");
  assert.equal(reconcilePending([...tail, rec], list3).keep.length, 1, "neither copy is this send's");
  // across pushes: the first of three identical sends retired on its own record earlier; the two-block
  // record then retires exactly the two that remain — the claims on one record are counted
  const list4 = press(tail, "continue", "continue", "continue");
  let r4 = reconcilePending([...tail, { kind: "user", md: "continue", uuid: "u0" }], list4);
  assert.deepEqual(r4.landed.map((l) => l.p), [list4[0]]);
  r4 = reconcilePending([...tail, { kind: "user", md: "continue", uuid: "u0" }, rec], r4.keep);
  assert.deepEqual(r4.landed.map((l) => l.p), [list4[1], list4[2]]);
  assert.equal(r4.keep.length, 0);
  // a fourth identical send pressed later finds every copy already there: the record of two is two
  const list5 = press([...tail, { kind: "user", md: "continue", uuid: "u0" }, rec], "continue");
  assert.deepEqual(list5[0].at?.seen, ["u0", "u1", "u1"], "the press lists the two-block record twice");
  assert.equal(reconcilePending([...tail, { kind: "user", md: "continue", uuid: "u0" }, rec], list5).keep.length, 1);
  // the same counting for the kernel's copies: a record of several sends is never an echo (one text each)
  assert.equal(provisionalIn({ kind: "user", md: "continue continue", uuid: "echo:1", blocks: ["continue", "continue"] }, list[0]), true,
    "…but were one ever shipped with blocks, its copies would be read the same way");
});

// ── (16) identity: the send id (2026-09-08) ──────────────────────────────────────────────────────
// The incident: a composer send and a todo reply queued during one open turn were fused by the CLI into
// ONE record whose text matched neither bubble, so the first stayed "sending…" until a ✕. The kernel now
// feeds one text at a time (tests/test_queued_sends_not_fused.py); on this side every send carries an id
// the kernel echoes back on its copies, and the decisions match on it wherever a copy carries one.
// Folded onto T252 (2026-09-08): the id decides WHICH kernel copy is this send's; T252 and its follow-ups
// decide WHERE the bubble sits (the tail since T252d). A queued copy naming the send is therefore a queued cover like an
// id-less text match: ours stays drawn at the tail (`inject`) and that copy is hidden (`unqueue`). An
// echo atom naming the send covers ours outright, as an id-less echo does: the kernel draws that atom.

test("a landing names the send by id: the id decides, the words do not", () => {
  const list = press([{ kind: "assistant", md: "…", uuid: "a1" }], "first words", "Re: the ask — the reply");
  const [A, B] = list;
  assert.notEqual(A.sendId, B.sendId, "each press mints its own id");
  // a record that carries B's id but wears A's words is B's landing, not A's
  let r = reconcilePending([{ kind: "assistant", md: "…", uuid: "a1" },
                            { kind: "user", md: "first words", uuid: "u1", sendIds: [B.sendId] }], list);
  assert.deepEqual(r.landed.map((l) => l.p), [B], "the id retires B");
  assert.deepEqual(r.keep, [A], "…and A, whose words the record wears, stays pending");
  // a record that carries no id (an older kernel, a path that mints none) is matched by its words
  r = reconcilePending([{ kind: "assistant", md: "…", uuid: "a1" },
                        { kind: "user", md: "first words", uuid: "u2" }], [A]);
  assert.deepEqual(r.landed.map((l) => l.p), [A], "no id on the record → the text match still lands it");
});

test("one fused record stamped with both ids clears both bubbles", () => {
  const list = press([{ kind: "assistant", md: "…", uuid: "a1" }], "first words", "Re: the ask — the reply");
  const [A, B] = list;
  const fused: TailEvent = { kind: "user", md: "first words Re: the ask — the reply", uuid: "u9", sendIds: [A.sendId, B.sendId] };
  const r = reconcilePending([{ kind: "assistant", md: "…", uuid: "a1" }, fused], list);
  assert.deepEqual(r.landed.map((l) => l.p), [A, B], "the record the kernel stamped with both ids retires both");
  assert.equal(r.keep.length, 0, "nothing left saying sending…");
});

test("a kernel copy that names ANOTHER send never covers this one, however similar the words", () => {
  const list = press([{ kind: "assistant", md: "…", uuid: "a1" }], TEXT);
  const [p] = list;
  // the kernel's queued copy of a different send with the same words: not ours
  let r = reconcilePending([{ kind: "assistant", md: "…", uuid: "a1" },
                            { kind: "queued", texts: [{ md: TEXT, sendId: "s-someone-else" }] }], list);
  assert.equal(r.inject.length, 1, "our bubble stays: the copy is another send's");
  assert.equal(r.unqueue.length, 0, "…and no copy is hidden for it");
  assert.equal(p.received, undefined, "…and proves nothing about our receipt");
  // the copy carrying OUR id is this send's: a queued cover (T252), so ours is drawn at the tail and the
  // kernel's copy of it is the one hidden
  r = reconcilePending([{ kind: "assistant", md: "…", uuid: "a1" },
                        { kind: "queued", texts: [{ md: TEXT, sendId: p.sendId }] }], list);
  assert.deepEqual(r.inject, [p], "ours stays drawn, at the tail (T252d)");
  assert.deepEqual(r.unqueue, [p], "…and the kernel's copy of THIS send is the one hidden for it");
  assert.equal(p.received, true, "…and proves the kernel has it");
  // an id-less copy (an older kernel) covers by text, as before: in place
  const q = press([{ kind: "assistant", md: "…", uuid: "a1" }], TEXT);
  r = reconcilePending([{ kind: "assistant", md: "…", uuid: "a1" }, { kind: "queued", texts: [{ md: TEXT }] }], q);
  assert.deepEqual(r.unqueue, [q[0]], "no id on the copy → the text match still covers, in place");
  // the kernel's echo atom, likewise: its ids decide when it carries any
  const e = press([{ kind: "assistant", md: "…", uuid: "a1" }], TEXT);
  r = reconcilePending([{ kind: "assistant", md: "…", uuid: "a1" },
                        { kind: "user", md: TEXT, uuid: "echo:9", sendIds: ["s-someone-else"] }], e);
  assert.equal(r.inject.length, 1, "another send's echo does not hide ours");
  assert.ok(provisionalIn({ kind: "user", md: TEXT, uuid: "echo:9", sendIds: [e[0].sendId] }, e[0]), "ours does");
  r = reconcilePending([{ kind: "assistant", md: "…", uuid: "a1" },
                        { kind: "user", md: TEXT, uuid: "echo:9", sendIds: [e[0].sendId] }], e);
  assert.deepEqual([r.inject.length, r.echoHide], [1, [1]], "…and the kernel's echo atom, naming the send, is this send's: hidden for it, ours stays the one bubble (T262h)");
});

test("the ✕ removes exactly its own entry of two wearing the same words — by id", () => {
  const list = press([{ kind: "assistant", md: "…", uuid: "a1" }], "go ahead", "go ahead");
  const [A, B] = list;
  assert.equal(dropPending(list, "go ahead", undefined, B.sendId), B, "the id names B");
  assert.deepEqual(list, [A], "A stays, whatever the click's index or words");
  assert.equal(dropPending(list, "go ahead", undefined, "s-not-here"), undefined, "an unknown id removes nothing");
  assert.deepEqual(list, [A]);
});

test("the DOM half posts the id with the send and carries it on the ✕ (render.ts)", () => {
  assert.match(RENDER, /type: "sendMessage", id: sid, text, sendId: p\.sendId/, "a plain send posts its bubble's id");
  assert.match(RENDER, /type: "sendMessage", id: sid, text: body, sendId: p\.sendId/, "…and so does a quote send");
  assert.match(RENDER, /if \(t\.sendId\) x\.dataset\.qsid = t\.sendId/, "the bubble's ✕ names the send");
  assert.match(RENDER, /dropPending\(list, qmd, qts, el\.dataset\.qsid\)/, "…and the ✕ drops that entry");
  assert.match(RENDER, /if \(el\.dataset\.qsid\) msg\.sendId = el\.dataset\.qsid/, "…and tells the kernel which entry to remove");
  assert.match(RENDER, /sendId: p\.sendId \}\);\n/, "the injected bubble carries its id, so its own kernel copy is matched by it");
});

// ── (17) the id is exact where the words are not (the 2026-09-08 review of the id change) ────────
// Three places still let the words or a clock outvote an id the kernel had echoed back: a queued copy
// carrying this send's id was handed out by POSITION (two identical sends, two id-carrying copies: the
// second found position 0 taken and showed a phantom "sending…" beside the kernel's own copy of it); a
// late stamp filed an echo or landing that NAMED the send as background when the client's clock ran
// ahead of the kernel's; and a provisional tab's adoption re-sent its held texts with no id at all.

test("two identical sends whose queued copies both carry ids each clear on their own copy: no phantom bubble", () => {
  const tail: TailEvent[] = [{ kind: "assistant", md: "…", uuid: "a1" }];
  const chip = (...ps: PendingSend[]): TailEvent => ({ kind: "queued", texts: ps.map((p) => ({ md: "continue", sendId: p.sendId })) });
  const list = press(tail, "continue", "continue");
  let r = reconcilePending([...tail, chip(...list)], list);
  assert.deepEqual(r.inject, list, "two sends, both drawn at the tail (T252d)");
  assert.deepEqual(r.unqueue, list, "two kernel copies naming them, both hidden: two bubbles for two sends, no third");
  assert.deepEqual(list.map((p) => p.received), [true, true], "each copy proves its own send's receipt");
  // three identical sends, the same
  const trio = press(tail, "continue", "continue", "continue");
  r = reconcilePending([...tail, chip(...trio)], trio);
  assert.deepEqual(r.unqueue, trio);
  assert.deepEqual(trio.map((p) => p.received), [true, true, true]);
  // the kernel's queue order is its own: the chip listing B before A changes nothing
  const pair = press(tail, "continue", "continue");
  r = reconcilePending([...tail, chip(pair[1], pair[0])], pair);
  assert.deepEqual(r.unqueue, pair, "the chip listing B before A changes nothing");
  // only B's copy has arrived: B's is the copy hidden; A's bubble waits for its own
  const two = press(tail, "continue", "continue");
  r = reconcilePending([...tail, chip(two[1])], two);
  assert.deepEqual(r.inject, two, "both drawn: A uncovered, B drawn over its hidden copy");
  assert.deepEqual(r.unqueue, [two[1]], "the copy names B, so B's is the copy hidden; A's bubble waits for its own");
  assert.deepEqual(two.map((p) => p.received), [undefined, true]);
  // a drop before the chip marked both 'not confirmed': the chip naming both clears both
  const dropped = press(tail, "continue", "continue");
  dropped[0].lost = dropped[1].lost = "connection";
  reconcilePending([...tail, chip(...dropped)], dropped);
  assert.deepEqual(dropped.map((p) => p.lost), [undefined, undefined]);
  // mixed: an id-less copy (a path that mints none) beside one carrying B's id. B takes its own by id; the
  // id-less one is handed out by position, and A is the one entry left to take it
  const mixed = press(tail, "continue", "continue");
  r = reconcilePending([...tail, { kind: "queued", texts: [{ md: "continue" }, { md: "continue", sendId: mixed[1].sendId }] }], mixed);
  assert.deepEqual(r.unqueue, mixed, "B takes its own by id; the id-less one is handed out by position, and A is the one entry left to take it");
  assert.deepEqual(mixed.map((p) => p.received), [true, true]);
  // copies naming OTHER sends are neither ours nor positions: they cover nothing and count for nothing
  const strangers = press(tail, "continue", "continue");
  r = reconcilePending([...tail, { kind: "queued", texts: [{ md: "continue", sendId: "s-someone-else" }, { md: "continue", sendId: "s-another" }] }], strangers);
  assert.equal(r.inject.length, 2, "two copies of other sends cover neither of ours");
  assert.equal(r.unqueue.length, 0, "…and neither is hidden");
  assert.deepEqual(strangers.map((p) => p.received), [undefined, undefined]);
  // the group's next push without B's copy (the CLI took it): B's bubble waits for its landing, and A's
  // copy still covers A. No position bookkeeping crosses the two.
  const later = press(tail, "continue", "continue");
  reconcilePending([...tail, chip(...later)], later);
  r = reconcilePending([...tail, chip(later[0])], later);
  assert.deepEqual(r.inject, later, "B's copy gone (the CLI took it): both drawn, B's bubble waiting for its landing");
  assert.deepEqual(r.unqueue, [later[0]], "A's copy still covers A; no position bookkeeping crosses the two");
  r = reconcilePending([...tail, chip(later[0]), { kind: "user", md: "continue", uuid: "u1", sendIds: [later[1].sendId] }], later);
  assert.deepEqual(r.landed.map((l) => l.p), [later[1]]);
  assert.deepEqual(r.inject, [later[0]]);
  assert.deepEqual(r.unqueue, [later[0]]);
});

test("a late stamp against a queued copy that NAMES the send presumes nothing: the id is the identity", () => {
  const isoAt = (s: number) => new Date(s * 1000).toISOString();
  const pressMs = T0 + 250;
  const S = Math.floor(pressMs / 1000);
  const late = (): PendingSend => ({ ...newPending(TEXT, undefined, pressMs), late: true });
  const step: TailEvent = { kind: "assistant", md: "…", uuid: "a1", ts: isoAt(S - 2) };
  // the frame's copy carries this send's id: covered by it, exactly, on every push it is listed (ours drawn
  // at the tail, that copy hidden: T252d)
  let p = late();
  let r = reconcilePending([step, { kind: "queued", texts: [{ md: TEXT, sendId: p.sendId }] }], [p]);
  assert.deepEqual(r.unqueue, [p], "covered by its own copy, exactly, on every push it is listed");
  assert.equal(p.received, true);
  assert.equal(p.at?.queued, 0, "an id-carrying copy is never an id-less position");
  // an older id-less copy sits beside it: that one is background, not presumed ours (we know which is ours)
  p = late();
  r = reconcilePending([step, { kind: "queued", texts: [{ md: TEXT }, { md: TEXT, sendId: p.sendId }] }], [p]);
  assert.equal(p.at?.queued, 1, "the id-less copy is background; the presumption is off once the frame names the send");
  assert.deepEqual(r.unqueue, [p], "covered by its own copy");
  r = reconcilePending([step, { kind: "queued", texts: [{ md: TEXT }] }], [p]);
  assert.equal(r.inject.length, 1, "once its own copy is gone (the CLI took it), the older copy covers nothing: ours shows until it lands");
  assert.equal(r.unqueue.length, 0, "…and the older copy is not hidden for it");
  // two identical late presses, the frame naming only the first: the second waits for its own copy, and the
  // first's copy is not lent to it by position
  const pair = [late(), late()];
  r = reconcilePending([step, { kind: "queued", texts: [{ md: TEXT, sendId: pair[0].sendId }] }], pair);
  assert.deepEqual(r.inject, pair, "both drawn, at the tail");
  assert.deepEqual(r.unqueue, [pair[0]], "the first's copy is hidden for the first, and not lent to the second by position");
  assert.deepEqual(pair.map((q) => q.received), [true, undefined]);
  r = reconcilePending([step, { kind: "queued", texts: [{ md: TEXT, sendId: pair[0].sendId }, { md: TEXT, sendId: pair[1].sendId }] }], pair);
  assert.deepEqual(r.unqueue, pair);
  assert.deepEqual(pair.map((q) => q.received), [true, true]);
  // id-less copies keep the presumption (an older kernel names nothing), as the round-4 test above pins
  const old = late();
  reconcilePending([step, { kind: "queued", texts: [{ md: TEXT }] }], [old]);
  assert.equal(old.at?.queued, 0);
});

test("a late stamp reads an event that NAMES the send as this send's, whatever its stamp: a client clock ahead of the kernel", () => {
  const isoAt = (s: number) => new Date(s * 1000).toISOString();
  const pressMs = T0 + 200;                 // the press, 200 ms into its second on the client's clock
  const S = Math.floor(pressMs / 1000);
  const late = (): PendingSend => ({ ...newPending(TEXT, undefined, pressMs), late: true });
  const step: TailEvent = { kind: "assistant", md: "…", uuid: "a1", ts: isoAt(S - 10) };
  // the echo form: the kernel (its clock 300 ms behind ours) stamped this send's echo in the second before
  // the press's second. The echo carries the send's id: it is this send's, not background.
  let p = late();
  let r = reconcilePending([step, { kind: "user", md: TEXT, uuid: "echo:1", ts: isoAt(S - 1), sendIds: [p.sendId] }], [p]);
  assert.deepEqual(p.at?.seen, [], "an event that names the send is never background");
  assert.deepEqual([r.inject.length, r.echoHide], [1, [1]], "…so the kernel's echo is this send's: hidden for it, ours stays drawn (T262h)");
  assert.equal(p.received, true);
  // the landing form: the CLI took the text at once, and the first frame already holds the landed record,
  // stamped a second early. It is neither the anchor nor background: it is the landing.
  p = late();
  r = reconcilePending([step, { kind: "user", md: TEXT, uuid: "u-landed", ts: isoAt(S - 1), sendIds: [p.sendId] }], [p]);
  assert.equal(p.at?.after, "a1", "nothing this send produced anchors it");
  assert.deepEqual(r.landed.map((l) => l.idx), [1], "the bubble ends on the first frame, instead of never");
  // …even when the session has already replied inside the skew: the reply sits after the record, so it is
  // after the send as well, and cannot be the anchor either
  p = late();
  r = reconcilePending([step, { kind: "user", md: TEXT, uuid: "u-landed", ts: isoAt(S - 1), sendIds: [p.sendId] },
                        { kind: "assistant", md: "done", uuid: "a2", ts: isoAt(S - 1) }], [p]);
  assert.equal(p.at?.after, "a1");
  assert.deepEqual(r.landed.map((l) => l.idx), [1]);
  // the send's record as the FIRST event of the frame: no anchor, the scan starts at the head
  p = late();
  r = reconcilePending([{ kind: "user", md: TEXT, uuid: "u-landed", ts: isoAt(S - 1), sendIds: [p.sendId] }], [p]);
  assert.equal(p.at?.after, null);
  assert.deepEqual(r.landed.map((l) => l.idx), [0]);
  // the kernel's never-delivered verdict on this send, stamped early: a verdict, not background
  p = late();
  r = reconcilePending([step, { kind: "user", md: TEXT, uuid: "echo:1", ts: isoAt(S - 1), sendIds: [p.sendId], undelivered: true }], [p]);
  assert.deepEqual(r.lost, [p]);
  // a record naming ANOTHER send, stamped early, is what it always was: not this send's
  p = late();
  r = reconcilePending([step, { kind: "user", md: TEXT, uuid: "u-other", ts: isoAt(S - 1), sendIds: ["s-someone-else"] }], [p]);
  assert.equal(r.keep.length, 1);
  assert.equal(r.inject.length, 1);
  // an id-less record stamped early keeps the stamp reading (an older kernel names nothing): the clock
  // bound now applies to id-less records only
  p = late();
  reconcilePending([step, { kind: "user", md: TEXT, uuid: "u-old", ts: isoAt(S - 1) }], [p]);
  assert.deepEqual(p.at?.seen, ["u-old"]);
});

test("a provisional tab's held sends post their bubble's id at adoption, like every other composer send (render.ts)", () => {
  const adopt = RENDER.slice(RENDER.indexOf("function adoptProvisional("), RENDER.indexOf("\n}\n", RENDER.indexOf("function adoptProvisional(")));
  assert.match(adopt, /for \(const text of queued\) \{\s*\n\s*const p = registerOptimistic\(realId, text\);\s*\n\s*vscodeApi\?\.postMessage\(\{ type: "sendMessage", id: realId, text, sendId: p\.sendId \}\);/,
    "registered FIRST, so the id exists to post; then posted with the send");
  assert.doesNotMatch(adopt, /type: "sendMessage", id: realId, text \}/, "the id-less send is gone from this path");
  // no composer arm posts a sendMessage without an id: the kernel's copies of every send name its bubble
  const posts = RENDER.match(/type: "sendMessage"[^}]*\}/g) || [];
  assert.ok(posts.length >= 3, "the plain, quote and adoption sends");
  for (const s of posts) assert.match(s, /sendId: p\.sendId/, "an id-less send: " + s);
  // the loop, executed as written: the id the kernel receives is the id the bubble wears
  const loop = adopt.slice(adopt.indexOf("for (const text of queued) {"));
  const body = loop.slice(0, loop.indexOf("\n  }\n") + 4);
  const posted: { type: string; id: string; text: string; sendId?: string }[] = [];
  const registered: PendingSend[] = [];
  const run = new Function("queued", "realId", "registerOptimistic", "vscodeApi", body);
  run(["run the tests", "run the tests"], "11111111-2222-3333-4444-555555555555",
    (id: string, text: string) => { const p = newPending(text, undefined, T0 + registered.length); registered.push(p); return p; },
    { postMessage: (m: any) => posted.push(m) });
  assert.equal(posted.length, 2);
  assert.deepEqual(posted.map((m) => m.sendId), registered.map((p) => p.sendId), "each post carries the id of the bubble registered for it");
  assert.notEqual(posted[0].sendId, posted[1].sendId, "two identical texts, two ids: the kernel can tell them apart");
  for (const m of posted) { assert.equal(m.type, "sendMessage"); assert.equal(m.id, "11111111-2222-3333-4444-555555555555"); assert.ok(m.sendId); }
});

// ── (18) the id decides which kernel copy is hidden (the 2026-09-08 fold of T252 onto the send id) ─────
// The kernel copy hidden for a bubble drawn as our own is the one naming the send, wherever it sits in the
// queue; the newest id-less copy of its text stands in when none does. The floor this section also covered
// (followed by id across the echo → landed swap, the text ordinal standing in) went with the send-slot
// placement at T252d: the bubble sits at the tail.

test("queuedCopyToHide hides the copy NAMING the send first, else the newest id-less copy of its text; a copy naming another send is never a position", () => {
  const texts = [{ md: "a", sendId: "s1" }, { md: "a" }, { md: "a", sendId: "s2" }];
  assert.equal(queuedCopyToHide(texts, "a", "s1"), 0, "the copy naming the send, wherever it sits in the queue");
  assert.equal(queuedCopyToHide(texts, "a", "s9"), 1, "no copy names it: the newest ID-LESS copy of the text");
  assert.equal(queuedCopyToHide(texts, "a"), 1, "…and the same with no id at all");
  assert.equal(queuedCopyToHide([{ md: "a", sendId: "s1", cancelable: false }, { md: "a" }], "a", "s1"), -1, "its own copy, non-cancelable: nothing hidden, the kernel's bubble stays");
  assert.equal(queuedCopyToHide([{ md: "a", sendId: "s2" }], "a", "s1"), -1, "only another send's copy: nothing to hide");
  // render.ts hands the helper the bubble's id (hideQueuedCopy)
  assert.match(RENDER, /const k = queuedCopyToHide\(q\.texts, p\.text, p\.sendId\);/);
});

// ── (19) the id and the queued presumption together (the 2026-09-08 remerge of the fold onto T252b) ──────
// #385 stamps every client copy with its send id; the late stamp's presumption (14) reads copies by text.
// Merged: the id decides which copy is whose, the text rule applies among the copies no id claims. T252b's
// placement legs (the foreign queue, the floors) went with the send-slot placement at T252d (the fold of
// 2026-09-08): the bubble sits at the tail, so nothing here decides WHERE.

test("a late stamp the queue names: a copy naming another send is background by id, never by position; the presumption skips id-less copies only (merged seam)", () => {
  const isoAt = (s: number) => new Date(s * 1000).toISOString();
  const pressMs = T0 + 250;
  const S = Math.floor(pressMs / 1000);
  const step: TailEvent = { kind: "assistant", md: "…", uuid: "a1", ts: isoAt(S - 2) };
  const late = (text = "mine"): PendingSend => ({ ...newPending(text, undefined, pressMs), late: true });
  // before ours: another client's F; after ours: a later press G (its id): every copy is matched on its id
  let p = late();
  let frame: TailEvent[] = [step, { kind: "queued", texts: [{ md: "F", sendId: "sF" }, { md: "mine", sendId: p.sendId }, { md: "G", sendId: "sG" }] }];
  let r = reconcilePending(frame, [p]);
  assert.equal(p.at?.queued, 0, "no id-less copy of the text: nothing is background by position");
  assert.deepEqual(r.unqueue, [p], "covered by its own copy");
  assert.equal(p.received, true);
  // the presumption is id-less only: with two same-text copies, one naming another send, one id-less, the newest
  // id-less copy is presumed ours (the frame does not name the send) and the id copy stays another send's
  p = late();
  frame = [step, { kind: "queued", texts: [{ md: "mine", sendId: "sOther" }, { md: "mine" }] }];
  r = reconcilePending(frame, [p]);
  assert.equal(p.at?.queued, 0, "the id-less copy is not background either: it is presumed ours");
  assert.deepEqual(r.unqueue, [p], "…and covers ours by position");
});

// ── (T252c, second and third reviews) identity decides where the frame SHOWS it; text decides where it does not ──
// Upstream's scenarios on this module's wire (the id is the press's, never latched: section 16). Two of upstream's
// cases have no counterpart here and are left out, each named where it would have gone.

test("two identical identified sends the CLI took as one record both retire on that landing (T252c second review)", () => {
  const tail: TailEvent[] = [{ kind: "assistant", md: "…", uuid: "a1" }];
  const [p1, p2] = press(tail, "ok", "ok");
  reconcilePending([...tail, { kind: "queued", texts: [{ md: "ok", sendId: p1.sendId }, { md: "ok", sendId: p2.sendId }] }], [p1, p2]);
  const landing: TailEvent[] = [...tail, { kind: "user", md: "ok ok", uuid: "uXY", blocks: ["ok", "ok"], sendIds: [p1.sendId, p2.sendId] }];
  const r = reconcilePending(landing, [p1, p2]);
  assert.deepEqual(r.landed.map((l) => [l.p, l.idx]), [[p1, 1], [p2, 1]], "each retires on its own id, whatever the other claimed of the text");
  assert.deepEqual(r.keep, []);
  // and the frames after: nothing lingers
  assert.deepEqual(reconcilePending(landing, [p1, p2].filter((p) => !r.landed.some((l) => l.p === p))).keep, []);
});

test("an id the frame no longer carries leaves the decision to text: a restart that re-minted the mirrors, or an older kernel (T252c second review)", () => {
  const tail: TailEvent[] = [{ kind: "assistant", md: "…", uuid: "a1" }];
  const named = (text: string, ts: number): PendingSend => {
    const p = newPending(text, undefined, ts);
    reconcilePending(tail, [p]);
    const r = reconcilePending([...tail, { kind: "queued", texts: [{ md: text, sendId: p.sendId }] }], [p]);
    assert.deepEqual(r.unqueue, [p], "the kernel's copy named the send");
    return p;
  };
  // (1) the restored copy carries no id: it still covers ours, by text: ours drawn at the tail, that copy hidden
  const p = named("rename it", T0);
  let r = reconcilePending([...tail, { kind: "queued", texts: [{ md: "rename it" }] }], [p]);
  assert.deepEqual([r.unqueue, r.inject], [[p], [p]], "one bubble, never ours beside the kernel's copy");
  // (2) an echo under a new uuid and no ids covers by text
  r = reconcilePending([...tail, { kind: "user", md: "rename it", uuid: "echo:new" }], [p]);
  assert.deepEqual([r.inject, r.keep, r.echoHide], [[p], [p], [1]], "the echo is attributed by text and hidden; ours stays (T262h)");
  // (3) that echo flagged never-delivered is the verdict, by text
  r = reconcilePending([...tail, { kind: "user", md: "rename it", uuid: "echo:new", undelivered: true }], [p]);
  assert.deepEqual(r.lost, [p]);
  // Upstream's fourth case (a record whose OTHER block carries an id while ours carries none lands ours by text) is
  // not this module's reading: a record carrying any ids is read by them alone (idVerdict), and a partially mapped
  // record is the kernel's to map per block. Left out at the 2026-09-08 fold, with the module's known edge named.
});

test("an id the frame still shows queued or echoed refuses a same-text landing that lacks it (T252c second review)", () => {
  const tail: TailEvent[] = [{ kind: "assistant", md: "…", uuid: "a1" }];
  const [a, b] = press(tail, "ok", "ok");
  reconcilePending([...tail, { kind: "queued", texts: [{ md: "ok", sendId: a.sendId }, { md: "ok", sendId: b.sendId }] }], [a, b]);
  // the first copy lands unpaired (no id on the record) while the second is still queued under its id
  let r = reconcilePending([...tail, { kind: "user", md: "ok", uuid: "u1" }, { kind: "queued", texts: [{ md: "ok", sendId: b.sendId }] }], [a, b]);
  assert.deepEqual(r.landed.map((l) => l.p), [a], "the id-less landing is the first send's, by text");
  assert.deepEqual([r.keep, r.unqueue, r.inject], [[b], [b], [b]], "the second is still in the queue under its id: not that landing's");
  // the same with the second copy fed: its echo names the send, and the first send, landed, does not go on to claim
  // that echo as its own cover on the way out
  r = reconcilePending([...tail, { kind: "user", md: "ok", uuid: "u1" }, { kind: "user", md: "ok", uuid: "echo:q2" }], [a, b]);
  assert.deepEqual([r.landed.map((l) => l.p), r.keep, r.inject, r.echoHide], [[a], [b], [b], [2]], "the id-less echo is the second send's by text: hidden for it, ours drawn (T262h)");
  // …and the same when the echo NAMES the second send (the kernel ships sendIds on its echoes): the one it names is
  // covered by id (that echo hidden, ours drawn), and the landed first send never claims it
  r = reconcilePending([...tail, { kind: "user", md: "ok", uuid: "u1" }, { kind: "user", md: "ok", uuid: "echo:q2", sendIds: [b.sendId] }], [a, b]);
  assert.deepEqual([r.landed.map((l) => l.p), r.keep, r.inject, r.echoHide], [[a], [b], [b], [2]]);
  // a send read by text (its id is nowhere in the frame) never takes an echo another send owns by id
  const [c, d] = press(tail, "go", "go");
  reconcilePending([...tail, { kind: "queued", texts: [{ md: "go", sendId: c.sendId }, { md: "go", sendId: d.sendId }] }], [c, d]);
  r = reconcilePending([...tail, { kind: "user", md: "go", uuid: "echo:d1", sendIds: [d.sendId] }], [c, d]);
  assert.deepEqual([r.keep, r.inject, r.echoHide], [[c, d], [c, d], [1]], "the echo is the second send's, by id: hidden for it; both bubbles are ours, and the first never claimed it");
  assert.deepEqual([c.received, d.received], [true, true], "both were received by their queued copies earlier; the echo added nothing to the first");
});

test("a send that landed claims nothing after its landing: a later same-text echo stays the next send's cover (T252c second review, adopted at the 2026-09-08 fold)", () => {
  const tail: TailEvent[] = [{ kind: "assistant", md: "…", uuid: "a1" }];
  // two identical sends on an id-less route (an older kernel: no ids anywhere); A's record lands, then B's echo follows
  const [a, b] = press(tail, "ok", "ok");
  const frame: TailEvent[] = [...tail, { kind: "user", md: "ok", uuid: "u1" }, { kind: "tool", uuid: "t1" }, { kind: "user", md: "ok", uuid: "echo:2" }];
  const r = reconcilePending(frame, [a, b]);
  assert.deepEqual(r.landed.map((l) => [l.p, l.idx]), [[a, 1]], "A lands on the record");
  assert.deepEqual([r.keep, r.inject, r.echoHide], [[b], [b], [3]], "the echo after it is B's cover: hidden for B, whose bubble stays ours (T262h)");
  assert.equal(b.received, true);
  assert.deepEqual(b.at?.seen, ["u1"], "A's landing is spoken for; the echo was never A's");
});

test("a send covered by its identified copy holds it: a later same-text send never takes that copy, nor a landing wearing its id (T252c third review)", () => {
  const tail: TailEvent[] = [{ kind: "assistant", md: "…", uuid: "a1" }];
  const [p1, p2] = press(tail, "ok", "ok");
  // the kernel shows the first copy alone: p1's, by id; p2 has nothing yet
  let r = reconcilePending([...tail, { kind: "queued", texts: [{ md: "ok", sendId: p1.sendId }] }], [p1, p2]);
  assert.deepEqual([r.unqueue, r.inject], [[p1], [p1, p2]]);
  // both copies show: each covered by its own
  r = reconcilePending([...tail, { kind: "queued", texts: [{ md: "ok", sendId: p1.sendId }, { md: "ok", sendId: p2.sendId }] }], [p1, p2]);
  assert.deepEqual(r.unqueue, [p1, p2]);
  // the first copy's landing retires p1 alone; p2 is still the queued second copy
  r = reconcilePending([...tail, { kind: "user", md: "ok", uuid: "u1", sendIds: [p1.sendId] }, { kind: "queued", texts: [{ md: "ok", sendId: p2.sendId }] }], [p1, p2]);
  assert.deepEqual([r.landed.map((l) => l.p), r.keep, r.unqueue], [[p1], [p2], [p2]]);
  // a copy naming the LATER send is never the earlier one's, whatever the list order; nor is a landing wearing its id
  const [c, d] = press(tail, "go", "go");
  r = reconcilePending([...tail, { kind: "queued", texts: [{ md: "go", sendId: d.sendId }] }], [c, d]);
  assert.deepEqual([r.unqueue, r.inject], [[d], [c, d]], "the one copy is d's: c is drawn uncovered");
  r = reconcilePending([...tail, { kind: "user", md: "go", uuid: "uD", sendIds: [d.sendId] }], [c, d]);
  assert.deepEqual([r.landed.map((l) => l.p), r.keep], [[d], [c]], "the landing wearing d's id is d's, whatever the list order");
});

test("the ✕ on the kernel's copy of an identified send drops THAT send's entry, by id (T252c third review)", () => {
  const tail: TailEvent[] = [{ kind: "assistant", md: "…", uuid: "a1" }];
  const [p1, p2, p3] = press(tail, "ok", "ok", "ok");
  reconcilePending([...tail, { kind: "queued", texts: [{ md: "ok", sendId: p1.sendId }, { md: "ok", sendId: p2.sendId }] }], [p1, p2, p3]);
  const list = [p1, p2, p3];
  assert.equal(dropPending(list, "ok", undefined, p2.sendId), p2, "the second copy's ✕ removes the second send, not the first with the text");
  // upstream's fall-through to "the first entry still without an id" has no counterpart here: every entry owns its
  // id from the press, so an id no entry wears removes nothing (section 16), never a neighbour wearing the text
  assert.equal(dropPending(list, "ok", undefined, "s-not-here"), undefined);
  assert.deepEqual(list, [p1, p3]);
});

// ── (T252d) the landed bubble's hover names the send time ─────────────────────────────────────────

test("the landed bubble's hover says when the message was SENT, once the landing is more than a minute later (T252d)", () => {
  const ts = "2026-09-08T10:05:30.000Z";
  const at = Math.floor(Date.parse(ts) / 1000);
  assert.equal(sentAtLabel(ts, at - 30), null, "half a minute apart: no hover");
  assert.equal(sentAtLabel(ts, at - 60), null, "exactly a minute: no hover");
  const label = sentAtLabel(ts, at - 61);
  assert.ok(label && label.startsWith("sent at ") && /\d\d:\d\d$/.test(label), "more than a minute: 'sent at HH:MM' — " + label);
  assert.equal(sentAtLabel(undefined, at), null);
  assert.equal(sentAtLabel(ts, undefined), null);
  // render.ts applies it to the landed user bubble's title, from the kernel's two stamps (never the client's clock)
  assert.match(RENDER, /const sentTip = sentAtLabel\(ev\.ts, ev\.sentAt\);\s*\n\s*if \(sentTip\) bubble\.title = sentTip;/);
});

test("our own send in the fed gap: the kernel's echo visible AND its held copy in the group — ours is the one bubble, both kernel copies hidden (T262h review)", () => {
  // upstream #1124, re-aimed to the fork's wire at the 2026-09-09 fold (slice 2; the T262 steer, R4): the copy's identity is
  // the sendId minted at the press, carried by the queued entry (sendId) and the echo (sendIds); nothing latches a kernel
  // id onto the send (upstream's p.qid), so the queued push proves receipt instead. `landing` is taken as upstream wrote it
  const tail: TailEvent[] = [{ kind: "assistant", md: "…", uuid: "a1" }];
  const p = newPending("hi there", undefined, T0);
  reconcilePending(tail, [p]);
  reconcilePending([...tail, { kind: "queued", texts: [{ md: "hi there", sendId: p.sendId }] }], [p]);
  assert.equal(p.received, true, "the queued copy wearing our id proves the kernel holds the send");
  // the copy left the queue (fed) and is held by the caller, marked landing; the kernel's echo shows too
  const frame: TailEvent[] = [...tail, { kind: "user", md: "hi there", uuid: "echo:q1", sendIds: [p.sendId] },
                              { kind: "queued", texts: [{ md: "hi there", sendId: p.sendId, landing: true }], uuid: "held:s" }];
  const r = reconcilePending(frame, [p]);
  assert.deepEqual([r.inject, r.unqueue, r.echoHide], [[p], [p], [1]], "ours drawn; the held copy hidden; the echo hidden");
  // an id-less send (an older kernel): the same by text
  const q = newPending("go on", undefined, T0 + 1);
  reconcilePending(tail, [q]);
  const frame2: TailEvent[] = [...tail, { kind: "user", md: "go on", uuid: "echo:zz" }, { kind: "queued", texts: [{ md: "go on", landing: true }], uuid: "held:s" }];
  const r2 = reconcilePending(frame2, [q]);
  assert.deepEqual([r2.inject, r2.unqueue, r2.echoHide], [[q], [q], [1]]);
});

test("two identical presses, then one push with the first's echo AND the second's queued copy: each send takes its own kernel copy (fed-gap fix review)", () => {
  // upstream #1124 on the fork's sendId wire (the 2026-09-09 fold, slice 2; R4): the echo names the first press, the
  // queued copy the second, each by the id minted at its press; upstream's latched-id assertion has no counterpart
  const tail: TailEvent[] = [{ kind: "assistant", md: "…", uuid: "a1" }];
  const [p1, p2] = press(tail, "x", "x");
  const frame: TailEvent[] = [...tail, { kind: "user", md: "x", uuid: "echo:x1", sendIds: [p1.sendId] }, { kind: "queued", texts: [{ md: "x", sendId: p2.sendId }] }];
  let r = reconcilePending(frame, [p1, p2]);
  assert.deepEqual([p1.received, p2.received], [true, true], "the echo is the first's, the queued copy the second's — never the first's by text");
  assert.deepEqual([r.inject, r.unqueue, r.echoHide], [[p1, p2], [p2], [1]], "both drawn by us; the copy hidden for the second, the echo for the first");
  r = reconcilePending(frame, [p1, p2]);
  assert.deepEqual([r.inject, r.unqueue, r.echoHide], [[p1, p2], [p2], [1]], "…and the same on the next push: no third bubble");
  // the first's landing retires the first, and only the first
  const landed: TailEvent[] = [...tail, { kind: "user", md: "x", uuid: "ux1", sendIds: [p1.sendId] }, { kind: "queued", texts: [{ md: "x", sendId: p2.sendId }] }];
  r = reconcilePending(landed, [p1, p2]);
  assert.deepEqual([r.landed.map((l) => l.p), r.keep, r.unqueue], [[p1], [p2], [p2]]);
});

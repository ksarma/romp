// Skeleton tabs — the client's copy of the set the kernel withholds after a redial (2026-09-07). The pure state
// machine in skeleton-tabs.ts is run here directly (the prebuild.ts / tab-meta.ts pattern); how render.ts wires
// it is pinned at the source in skeleton-tabs-wiring.test.ts. Synthetic ids only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { newSkeletonState, applyTabOrderSkeleton, onStatus, holdStatus, onFull, onDismiss, onSocketUp, nextPrefetch,
         renderKind, gateOnFrame, gateOnStrip, gateOnShow, type SkeletonState } from "./skeleton-tabs";

const A = "11111111-2222-3333-4444-aaaaaaaaaaaa";
const B = "11111111-2222-3333-4444-bbbbbbbbbbbb";
const C = "11111111-2222-3333-4444-cccccccccccc";
const D = "11111111-2222-3333-4444-dddddddddddd";
const all = () => true;
const none = new Set<string>();

const held = (st: SkeletonState) => [...st.ids].sort();

test("the spec's story: a reconnect strip lists [B, C]; a stale session never makes a skeleton read as loaded", () => {
  const st = newSkeletonState();
  assert.equal(applyTabOrderSkeleton(st, [B, C], [A, B, C]), true, "a set landed → changed");
  assert.deepEqual(st.order, [B, C], "the kernel's order is kept verbatim — it is the prefetch order");
  gateOnFrame(st, A, [A]);   // the active tab's full applied: the idle chain may start (the start gate, stage 0)
  // the page HELD B before the outage (hasSession = true) — that stale entry must not paint it as loaded
  assert.equal(renderKind(st, B, true), "skeleton");
  assert.equal(renderKind(st, A, true), "loaded", "the active tab, sent in full, is a plain loaded tab");
  assert.equal(renderKind(st, D, false), "placeholder", "an unknown, session-less id is still the building placeholder");
  // status frames: stored for a skeleton (the chip reads ONLY these), passed through for anyone else
  assert.equal(onStatus(st, B, { state: "working", sinceEpoch: 1 }), "skeleton");
  assert.deepEqual(st.status.get(B), { state: "working", sinceEpoch: 1 });
  assert.equal(onStatus(st, A, { state: "idle" }), "not-skeleton");
  assert.equal(st.status.has(A), false, "a non-skeleton status is the caller's business");
  // the user clicks B → render.ts asks (pinned in the wiring test) and B sits in awaitingFull: the prefetch
  // holds while ANY skeleton is in flight, even one the user asked for (one at a time)
  assert.equal(nextPrefetch(st, B, new Set([B]), false, all), null, "one in flight → nothing else is fetched");
  // B's full lands
  assert.equal(onFull(st, B), true, "it WAS held → the caller re-shows the view instead of appending");
  assert.deepEqual(held(st), [C]);
  assert.equal(st.status.has(B), false, "its stored status goes with it");
  assert.deepEqual(st.order, [C]);
  assert.equal(onFull(st, A), false, "a full for a loaded tab is not a skeleton release");
  // a later strip WITHOUT the key (an older kernel; the set emptied so the key was dropped): keep, pruned
  assert.equal(applyTabOrderSkeleton(st, undefined, [A, C]), false, "C kept, nothing changed");
  assert.deepEqual(held(st), [C]);
  assert.equal(applyTabOrderSkeleton(st, undefined, [A]), true, "C left the strip → pruned");
  assert.deepEqual(held(st), []);
});

test("absent key = keep (pruned to the strip); an array = replace — the kernel's list is authoritative", () => {
  const st = newSkeletonState();
  applyTabOrderSkeleton(st, [B, C, D], [A, B, C, D]);
  assert.equal(applyTabOrderSkeleton(st, undefined, [A, C]), true);
  assert.deepEqual(held(st), [C], "B and D are no longer on the strip → pruned; C kept (absent = keep)");
  assert.deepEqual(st.order, [C]);
  // a second reconnect while C is outstanding: the new socket's strip names [A] — A had loaded, but it is
  // stale after the second outage, and C (not listed) is what the kernel now sends in full
  onSocketUp(st);
  assert.equal(applyTabOrderSkeleton(st, [A], [A, C]), true);
  assert.deepEqual(held(st), [A], "replaced, not merged");
  assert.deepEqual(st.order, [A]);
});

test("an array is cleaned: strings only, deduped; status entries for ids that left are dropped", () => {
  const st = newSkeletonState();
  applyTabOrderSkeleton(st, [B, C], [A, B, C]);
  onStatus(st, B, { state: "idle" });
  onStatus(st, C, { state: "idle" });
  assert.equal(applyTabOrderSkeleton(st, [C, 7, null, C, ""], [A, B, C]), true);
  assert.deepEqual(held(st), [C]);
  assert.deepEqual(st.order, [C]);
  assert.equal(st.status.has(B), false, "B left the set → its status is gone");
  assert.equal(st.status.has(C), true);
  assert.equal(applyTabOrderSkeleton(st, [C], [A, B, C]), false, "the same list again → unchanged (no repaint)");
  assert.equal(applyTabOrderSkeleton(st, [], [A, B, C]), true, "an empty array empties the set");
  assert.deepEqual(held(st), []);
});

test("a list that names a tab whose full already arrived on THIS socket is a stale relay, never re-adopted", () => {
  // The kernel releases a sid as it sends its full and enqueues both under one lock, so a strip naming X can only
  // be ahead of X's full — never behind it. The federation merge re-attaches its per-host copy of the list to
  // every merged strip and is never told the last id loaded (the kernel's key just disappears): without this
  // rule the last skeleton re-skeletoned on every push, asked, loaded, and re-skeletoned again — a flap.
  const st = newSkeletonState();
  applyTabOrderSkeleton(st, [C], [A, C]);
  assert.equal(onFull(st, C), true);
  assert.equal(applyTabOrderSkeleton(st, [C], [A, C]), false, "the stale relay of [C] is ignored");
  assert.deepEqual(held(st), []);
  // a NEW socket is new information about every tab: the same list is adopted after the socket reopens
  onSocketUp(st);
  assert.equal(applyTabOrderSkeleton(st, [C], [A, C]), true);
  assert.deepEqual(held(st), [C]);
});

test("nextPrefetch: null when hidden, null while one is in flight, else the first held id in order that is in view and not active", () => {
  const st = newSkeletonState();
  applyTabOrderSkeleton(st, [C, B, D], [A, B, C, D]);   // the kernel's order: ascending transcript size
  gateOnFrame(st, A, [A]);   // the active tab's full applied: the start gate is open for the rest of this case (stage 0)
  assert.equal(nextPrefetch(st, A, none, true, all), null, "hidden → nothing (bytes nobody sees)");
  assert.equal(nextPrefetch(st, A, new Set([D]), false, all), null, "a skeleton in flight → wait for its upsert");
  assert.equal(nextPrefetch(st, A, new Set([A]), false, all), C, "a non-skeleton in flight does not hold the chain");
  assert.equal(nextPrefetch(st, A, none, false, all), C, "the first of the kernel's order");
  assert.equal(nextPrefetch(st, C, none, false, all), B, "…skipping the active tab (its own click path asks)");
  assert.equal(nextPrefetch(st, A, none, false, (id) => id !== C), B, "…and a view-hidden tab (it loads on click)");
  onFull(st, C); onFull(st, B);
  assert.equal(nextPrefetch(st, A, none, false, all), D, "the chain walks the list one upsert at a time");
  onFull(st, D);
  assert.equal(nextPrefetch(st, A, none, false, all), null, "nothing left");
  assert.equal(nextPrefetch(newSkeletonState(), A, none, false, all), null, "a fresh page has no set");
});

test("holdStatus: a status ahead of its strip is kept for the array that lists the id and dropped by one that does not", () => {
  // The pane shim's FIFO delivers a newer tabOrder at the END of a burst, so a skeleton's status frames can land before
  // the strip that names the set (a later chat column's open sends two strips, 2026-09-11). The status waits for the
  // strip; an ask in its place loaded the whole board behind a column opened as a view of one session.
  const st = newSkeletonState();
  gateOnStrip(st, [A, C, D], null);   // no active tab to wait for: the gate is open (stage 0), so a null below means nothing is held
  assert.equal(onStatus(st, C, { state: "working" }), "not-skeleton", "no set yet: the caller's fallthrough, which holds");
  holdStatus(st, C, { state: "working" }); holdStatus(st, D, { state: "idle" });
  assert.deepEqual(held(st), [], "a held status makes no skeleton");
  assert.equal(renderKind(st, C, false), "placeholder", "…and draws nothing as one");
  assert.equal(nextPrefetch(st, A, none, false, all), null, "…and the idle walk has nothing to fetch");
  applyTabOrderSkeleton(st, [C], [A, C, D]);
  assert.deepEqual(held(st), [C]);
  assert.deepEqual(st.status.get(C), { state: "working" }, "the held status is the chip's the moment the strip lists the id");
  assert.equal(st.status.has(D), false, "a status for an id the array does not list is dropped with the strip");
  onFull(st, C);
  assert.equal(st.status.has(C), false, "the full clears it as any skeleton's");
});

test("onDismiss: a tab that left the strip has nothing left to load", () => {
  const st = newSkeletonState();
  applyTabOrderSkeleton(st, [C], [A, C]);
  gateOnFrame(st, A, [A]);   // the gate open (stage 0): the null at the end is the empty set's, not the gate's
  onStatus(st, C, { state: "working" });
  onDismiss(st, C);
  assert.deepEqual(held(st), []);
  assert.deepEqual(st.order, []);
  assert.equal(st.status.size, 0);
  onDismiss(st, C);   // idempotent
  assert.deepEqual(held(st), []);
  assert.equal(nextPrefetch(st, A, none, false, all), null);
});

test("renderKind with a stale session present: skeleton wins; without the set the old two states are unchanged", () => {
  const st = newSkeletonState();
  assert.equal(renderKind(st, B, true), "loaded");
  assert.equal(renderKind(st, B, false), "placeholder");
  applyTabOrderSkeleton(st, [B], [A, B]);
  assert.equal(renderKind(st, B, true), "skeleton", "the stale pre-outage entry is kept for the append, never painted");
  assert.equal(renderKind(st, B, false), "skeleton", "a page that opened a socket and received nothing: still a skeleton, loads on click/idle");
});

test("an array never adopts an id the strip does not list: a session that ended before it loaded is gone", () => {
  const st = newSkeletonState();
  applyTabOrderSkeleton(st, ["B", "Z"], ["A", "B"]);
  assert.deepEqual(st.order, ["B"], "Z is not on the strip → not a skeleton either (the prefetch must never ask for it)");
  assert.equal(st.ids.has("Z"), false);
});

test("a dismissed tab leaves the loaded set, so its re-listing is a skeleton again and the pane asks for its frame (T357)", () => {
  const st = newSkeletonState();
  applyTabOrderSkeleton(st, ["A"], ["A", "B"]);
  onFull(st, "A");                                    // its frame landed on this socket
  assert.ok(st.loaded.has("A")); assert.ok(!st.ids.has("A"));
  applyTabOrderSkeleton(st, ["A"], ["A", "B"]);       // re-listed as a skeleton while loaded: refused, the page has it
  assert.ok(!st.ids.has("A"), "a loaded id is never re-skeletoned on the same socket");
  onDismiss(st, "A");                                 // its tab left the strip (a host drop, an omission): the view went with it
  assert.ok(!st.loaded.has("A"), "no longer loaded here");
  applyTabOrderSkeleton(st, ["A"], ["A", "B"]);       // the host re-attached: the strip names it a skeleton again
  assert.ok(st.ids.has("A"), "…and now it is one, so the pane asks for its frame");
});

// ── the idle prefetch's START GATE (stage 0 of the reconnect design, 2026-09-18) ──
// The kernel sends the strip before it builds anything and the active tab is never in the skeleton set, so a chain armed
// from the strip's first paint sent its first background ask ahead of the visible tab's full; on a phone link the visible
// session then waited behind a tab nobody was looking at. The gate keys the chain on the visible tab's first frame applied,
// or on a strip that lists no such tab. The click road is never gated (render.ts showActive asks at once; the wiring test
// pins it). Executed here over the pure state; the wiring is pinned in skeleton-tabs-wiring.test.ts.

test("T2: no background ask leaves before the visible tab's full has applied; that frame opens the chain, a click's frame does not", () => {
  const st = newSkeletonState();
  applyTabOrderSkeleton(st, [B, C], [A, B, C]);   // the diet's strip: A (the visible tab) is the one full coming; B and C rest
  assert.equal(st.gate, false, "a fresh socket's gate is closed");
  assert.equal(nextPrefetch(st, A, none, false, all), null, "nothing in flight, the page visible, two tabs resting: still no ask before A's full");
  assert.equal(gateOnStrip(st, [A, B, C], A), false, "the strip lists the visible tab: the gate waits for its frame");
  assert.equal(st.gate, false);
  assert.equal(gateOnFrame(st, C, [A]), false, "a frame for another tab (a click's, a relay's) is not the event");
  assert.equal(nextPrefetch(st, A, none, false, all), null);
  assert.equal(gateOnFrame(st, A, [A]), true, "the visible tab's full applied: the gate opens NOW (the caller arms once)");
  assert.equal(gateOnFrame(st, A, [A]), false, "…and an open gate reports no second opening");
  assert.equal(nextPrefetch(st, A, none, false, all), B, "the chain starts, in the kernel's order");
  assert.equal(gateOnFrame(st, B, [null, undefined]), false, "no want at all: a frame opens nothing (and an open gate stays open)");
  assert.equal(st.gate, true);
});

test("T2, the awaited tab: after a reload the pane awaits its stored tab with no active yet; that tab's frame is the visible tab's", () => {
  const st = newSkeletonState();
  applyTabOrderSkeleton(st, [B, C], [A, B, C]);
  assert.equal(gateOnStrip(st, [A, B, C], A), false, "wantActive A is listed: wait for its frame");
  assert.equal(gateOnFrame(st, B, [A, null]), false, "render.ts passes [the awaited tab, the active tab (null before adoption)]");
  assert.equal(gateOnFrame(st, A, [A, null]), true);
  assert.equal(nextPrefetch(st, null, none, false, all), B);
});

test("T3: a tab tapped before the chain reaches it is asked at once by the click road (ungated), and its ask holds the chain (one at a time)", () => {
  const st = newSkeletonState();
  applyTabOrderSkeleton(st, [B, C, D], [A, B, C, D]);
  // the user taps C before A's full has landed: render.ts's showActive asks for C with why=skeleton-click whatever the gate says
  // (pinned at source in skeleton-tabs-wiring.test.ts); its ask sits in awaitingFull
  const inFlight = new Set([C]);
  assert.equal(nextPrefetch(st, C, inFlight, false, all), null, "closed gate, and the click's ask in flight: no background ask");
  gateOnFrame(st, C, [A, C]);   // C's full lands: C is the active tab now (the tap moved activeId), so ITS frame is the visible tab's
  assert.equal(onFull(st, C), true);
  inFlight.delete(C);
  assert.equal(nextPrefetch(st, C, inFlight, false, all), B, "then the chain runs for the rest, skipping the active tab");
  const st2 = newSkeletonState();
  applyTabOrderSkeleton(st2, [B, C, D], [A, B, C, D]);
  gateOnFrame(st2, A, [A]);
  assert.equal(nextPrefetch(st2, A, new Set([D]), false, all), null, "the click's ask ahead of the chain's: while D (tapped) is in flight the chain waits, as before this change");
});

test("T5, ended-active: the strip lists no tab as active, so the gate opens on the strip and the tabs load in the kernel's order", () => {
  const st = newSkeletonState();
  applyTabOrderSkeleton(st, [B, C], [B, C]);   // the stored tab A ended while the page was away: every listed tab is a skeleton, no full is coming
  assert.equal(nextPrefetch(st, null, none, false, all), null, "closed until the strip says so");
  assert.equal(gateOnStrip(st, [B, C], A), true, "the strip does not list A: the event that says no full is coming, the gate opens NOW");
  assert.equal(nextPrefetch(st, null, none, false, all), B, "the chain loads the tabs, cheapest first");
  const st2 = newSkeletonState();
  applyTabOrderSkeleton(st2, [B, C], [B, C]);
  assert.equal(gateOnStrip(st2, [B, C], null), true, "no stored tab at all (a fresh profile): the strip opens it too");
  assert.equal(gateOnStrip(st2, [B, C], null), false, "an open gate reports no second opening");
  const st3 = newSkeletonState();
  assert.equal(gateOnStrip(st3, [], A), true, "an empty local strip (a kernel with no sessions): nothing is coming");
});

test("T6: a return on the phone (the owner's decision, 2026-09-19): the redial reloads the visible tab alone; the other tabs reload only when tapped, for the socket's life; the desktop keeps its chain", () => {
  const st = newSkeletonState();
  applyTabOrderSkeleton(st, [B, C], [A, B, C]);
  gateOnFrame(st, A, [A]);
  onFull(st, B); onFull(st, C);   // the first chain finished: every tab loaded on this socket
  assert.equal(nextPrefetch(st, A, none, false, all), null, "nothing left");
  onSocketUp(st, true);   // the return's redial (reconnect=1) on the phone layout: the kernel re-skeletons every non-active tab on the new socket
  assert.equal(st.gate, false, "a new socket closes the gate: the visible tab's full comes first again");
  assert.equal(st.returnHold, true, "…and on the phone the chain is held for this socket's life");
  assert.equal(applyTabOrderSkeleton(st, [B, C], [A, B, C]), true, "the redial's strip re-lists B and C (the loaded record was cleared with the socket)");
  assert.equal(gateOnStrip(st, [A, B, C], A), false, "the strip opens nothing");
  assert.equal(gateOnStrip(st, [B, C], A), false, "…not even a strip that lists no local want (an ended stored tab): the hold outranks the strip's opening");
  assert.equal(nextPrefetch(st, A, none, false, all), null, "no background ask on the redial before A's full");
  assert.equal(gateOnFrame(st, A, [A]), false, "A's full applied on the new socket: the visible tab alone reloads, the gate stays closed");
  assert.equal(nextPrefetch(st, A, none, false, all), null, "the chain does not re-download B and C (17 to 22 MB on the owner's board, for tabs nobody asked for)");
  // the user taps B: the click road asks for its full at once (render.ts showActive's skeleton-click, never gated), B loads
  onFull(st, B);
  assert.equal(gateOnShow(st, B), false, "the tap onto the now-whole B opens nothing either");
  assert.equal(nextPrefetch(st, B, none, false, all), null, "C stays a skeleton until its own tap: reloaded only when tapped");
  assert.deepEqual([...st.ids], [C]);
  // the desktop keeps today's chain: the redial's active full reopens the gate and the other tabs re-download in order
  const st2 = newSkeletonState();
  applyTabOrderSkeleton(st2, [B, C], [A, B, C]);
  gateOnFrame(st2, A, [A]); onFull(st2, B); onFull(st2, C);
  onSocketUp(st2, false);
  assert.equal(st2.returnHold, false, "the desktop passes false: no hold");
  applyTabOrderSkeleton(st2, [B, C], [A, B, C]);
  assert.equal(gateOnStrip(st2, [A, B, C], A), false, "the strip lists A: the gate waits for A's frame");
  assert.equal(nextPrefetch(st2, A, none, false, all), null, "no background ask on the redial before A's full");
  assert.equal(gateOnFrame(st2, A, [A]), true, "A's full applied on the new socket");
  assert.equal(nextPrefetch(st2, A, none, false, all), B, "and the chain re-downloads the other tabs, as before");
  // a call without the layout (an older caller, a standalone page's stand-in) is the desktop's
  const st3 = newSkeletonState();
  onSocketUp(st3);
  assert.equal(st3.returnHold, false);
  assert.equal(newSkeletonState().returnHold, false, "a fresh state holds nothing: the boot dial sends no wsup, so a cold open's chain is untouched");
});

test("F4 and F7 (review round 1, 2026-09-19): a want on another host is not this chain's to wait for; the local strip opens the gate, on the boot dial and after a local-only redial", () => {
  const R = "TESTHOST:11111111-2222-3333-4444-eeeeeeeeeeee";   // the stored tab lives on another kernel: its full comes over that host's relay socket
  const st = newSkeletonState();
  applyTabOrderSkeleton(st, [B, C], [B, C]);   // the local kernel's own dial: every local transcript tab is a skeleton (the hint names no local sid)
  assert.equal(gateOnStrip(st, [B, C], R), true, "a stored remote tab: the local strip says no full is coming from this kernel, so the chain starts (as before this change; the remote's full rides its relay)");
  assert.equal(nextPrefetch(st, null, none, false, all), B);
  // the merged strip under federation lists the remote tab too (emitMergedOrder folds every host's slice into the local emission): the want's HOST decides, not the listing
  const st2 = newSkeletonState();
  applyTabOrderSkeleton(st2, [B, C], [R, B, C]);
  assert.equal(gateOnStrip(st2, [R, B, C], R), true, "listed or not, a remote want opens the gate on the local strip");
  // a local-only redial while the shown tab is remote (the watchdog's redial of the pane socket with the relays alive): the socket flip closes the gate, the redial's strip reopens it
  const st3 = newSkeletonState();
  applyTabOrderSkeleton(st3, [B, C], [R, B, C]);
  gateOnStrip(st3, [R, B, C], R);
  onFull(st3, B); onFull(st3, C);
  onSocketUp(st3);
  assert.equal(st3.gate, false, "the local socket's flip closes the gate whatever the shown tab's host");
  assert.equal(applyTabOrderSkeleton(st3, [B, C], [R, B, C]), true, "the redial re-skeletons every local tab");
  assert.equal(nextPrefetch(st3, R, none, false, all), null, "closed until the strip");
  assert.equal(gateOnStrip(st3, [R, B, C], R), true, "the redial's local strip reopens it: no local full is coming for a remote shown tab (before this fix the gate stayed closed for the socket's life)");
  assert.equal(nextPrefetch(st3, R, none, false, all), B, "the chain reloads the local tabs");
  // a LOCAL want listed by the strip still waits for its frame (T2 unchanged)
  const st4 = newSkeletonState();
  applyTabOrderSkeleton(st4, [B, C], [A, B, C]);
  assert.equal(gateOnStrip(st4, [A, B, C], A), false);
});

test("F8 (review round 1, 2026-09-19): a tap onto a tab already whole on this socket opens the gate (gateOnShow); a tab not yet loaded on this socket does not", () => {
  const Y = "11111111-2222-3333-4444-ffffffffffff";   // a transcript-less session, never a skeleton, served whole ahead of the stored tab's full
  const st = newSkeletonState();
  applyTabOrderSkeleton(st, [B, C], [A, B, C, Y]);
  assert.equal(gateOnStrip(st, [A, B, C, Y], A), false, "the strip lists the stored tab A: wait for its frame");
  onFull(st, Y);
  assert.equal(gateOnFrame(st, Y, [A, null]), false, "Y's full is not the shown tab's");
  assert.equal(nextPrefetch(st, null, none, false, all), null);
  assert.equal(gateOnShow(st, Y), true, "the user taps Y, whole on this socket: the visible tab has its frame, the chain may start (before this fix it waited for A's full, or Y's re-post about 60 s later)");
  assert.equal(nextPrefetch(st, Y, none, false, all), B);
  assert.equal(gateOnShow(st, Y), false, "an open gate reports no second opening");
  const st2 = newSkeletonState();
  applyTabOrderSkeleton(st2, [B, C], [A, B, C]);
  assert.equal(gateOnShow(st2, C), false, "a tap onto a skeleton (not loaded on this socket) opens nothing here: the click road asks for it and its full opens the gate");
  assert.equal(st2.gate, false);
  onSocketUp(st2);
  assert.equal(gateOnShow(st2, A), false, "after a redial nothing is loaded on the new socket yet: the stale session map is never the key");
});

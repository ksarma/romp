// An ENDED session must leave the tab strip even when the kernel's one-shot `closed` frame never arrived
// (the 2026-08-11 ghost: a session the kernel had ended stayed on the dashboard looking alive — last status
// still "working", transcript cached, fully clickable — and only a manual reload cleared it).
//
// The chain that minted it, each link by design: pane JS state survives WS reconnects (the shim reconnects,
// never reloads); a client that stops draining is force-dropped at the send-queue byte cap (a frozen webview
// popout, a sleeping laptop), so it is exactly the client that is DISCONNECTED at the kill moment and misses
// the one-shot `closed`; and applyTabOrder's keep re-adopted any locally-known tab the kernel's order didn't
// carry — forever. The fix makes the CONTINUOUS tabOrder push the authority: an id any push has carried is
// kernel-owned (`kernelListed`), and a later push omitting it dismisses the tab with the same teardown the
// `closed` event runs. `closed` stays as the fast path.
//
// The executed model below runs the real reconcileTabOrder through the whole miss-and-heal cycle with
// applyTabOrder's bookkeeping; the source pins hold that wiring in render.ts.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { reconcileTabOrder } from "./tab-order";

const RENDER = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "render.ts"), "utf8");

// A stand-in for the client around a session death: the sessions map, the render order, and applyTabOrder's
// kernelListed bookkeeping. dismiss() mirrors dismissSession's teardown surface (session + view + draft go).
// The re-ask half (2026-08-18) mirrors requestFullSession/awaitingFull: a push that lists an id an EARLIER
// push already listed, with no session behind it, asks the kernel for the full session — once per desync.
function model() {
  let order: string[] = [];
  const sessions = new Map<string, { state: string }>();
  const drafts = new Map<string, string>();
  const kernelListed = new Set<string>();
  const dismissed: string[] = [];
  const awaitingFull = new Set<string>();
  const asked: string[] = [];
  const dismiss = (id: string) => {
    dismissed.push(id);
    sessions.delete(id); drafts.delete(id);
    order = order.filter((x) => x !== id);
  };
  const upsert = (id: string, state: string) => {
    sessions.set(id, { state });
    awaitingFull.delete(id);                      // a full session landed → a later gap may ask again
    if (!order.includes(id)) order.push(id);
  };
  return {
    dismissed, asked,
    session(id: string, state = "working") { upsert(id, state); },
    draft(id: string, text: string) { drafts.set(id, text); },
    closedEvent(id: string) { dismiss(id); },     // the kernel's one-shot frame, when it DOES arrive
    // federation's detach teardown (closeRemote's TAGGED closed frame, 2026-08-18): same dismiss,
    // plus the kernelListed prune — after a detach the host's past listings are no longer live
    // evidence, so its reattach must read as the silent tabs-first boot, not a re-listing.
    hostDetachEvent(id: string) { kernelListed.delete(id); dismiss(id); },
    // the kernel's answer to a needFull ask — and ONLY to an ask: the field case has no spontaneous
    // session frames (the kernel's echat believes this client is caught up), so the reply must be
    // CAUSED by the re-ask or the heal never happens.
    needFullReply(id: string, state = "working") {
      if (!asked.includes(id)) throw new Error("no needFull was asked for " + id);
      upsert(id, state);
    },
    // a kernel tabOrder push, with applyTabOrder's bookkeeping: kernel-owned omissions dismiss first,
    // then the reconcile (whose keep no longer applies to kernel-owned ids), then the RE-ASK for any
    // repeat-listed id whose session this client lost, then the add-only record.
    push(kernel: string[]) {
      for (const id of order.slice()) if (kernelListed.has(id) && !kernel.includes(id)) dismiss(id);
      order = reconcileTabOrder(kernel, order, (id) => sessions.has(id), (id) => kernelListed.has(id));
      for (const id of kernel) {
        if (kernelListed.has(id) && !sessions.has(id) && !awaitingFull.has(id)) { awaitingFull.add(id); asked.push(id); }
      }
      for (const id of kernel) kernelListed.add(id);
    },
    tabs() { return order.slice(); },
    placeholders() { return order.filter((id) => !sessions.has(id)); },   // strip ids with no session = the swirl
    state(id: string) { return sessions.get(id)?.state ?? null; },
    hasDraft(id: string) { return drafts.has(id); },
  };
}

test("a session ended while the socket was down leaves the strip on the reconnect's first push", () => {
  const m = model();
  m.session("web"); m.session("api");
  m.push(["web", "api"]);                 // both kernel-owned
  // api is ended while this client's socket is down (frozen popout force-dropped at the queue cap): the
  // one-shot `closed` frame is LOST, api's session survives in the maps with its last live status…
  assert.equal(m.state("api"), "working", "the cached state still claims a live session");
  // …and the reconnect's resync push no longer carries it. Before the fix this push KEPT the tab (its
  // session was locally known), so the ended session sat on the strip looking alive until a manual reload.
  m.push(["web"]);
  assert.deepEqual(m.tabs(), ["web"], "the omission is the removal event — the ghost heals");
  assert.deepEqual(m.dismissed, ["api"], "…with the same teardown the closed event runs");
  assert.equal(m.state("api"), null, "no live-looking cached session left behind");
  m.push(["web"]);                        // and it STAYS healed on every later push
  assert.deepEqual(m.tabs(), ["web"]);
});

test("the teardown clears the dead session's composer leftovers too", () => {
  const m = model();
  m.session("web"); m.session("api");
  m.push(["web", "api"]);
  m.draft("api", "half-typed message");
  m.push(["web"]);
  assert.equal(m.hasDraft("api"), false, "kernel-driven drop runs the full dismissSession surface");
});

test("the closed event remains the fast path; the push after it has nothing left to do", () => {
  const m = model();
  m.session("web"); m.session("api");
  m.push(["web", "api"]);
  m.closedEvent("api");                   // delivered normally this time
  assert.deepEqual(m.tabs(), ["web"]);
  m.push(["web"]);                        // the confirming push neither re-adds nor double-dismisses
  assert.deepEqual(m.tabs(), ["web"]);
  assert.deepEqual(m.dismissed, ["api"]);
});

test("a revival re-adopts the same sid after a ghost heal (dead sessions revive with their history)", () => {
  const m = model();
  m.session("web"); m.session("api");
  m.push(["web", "api"]);
  m.push(["web"]);                        // api ended + healed
  m.session("api", "opening");            // revived: the kernel lists the SAME sid again
  m.push(["web", "api"]);
  assert.deepEqual(m.tabs(), ["web", "api"]);
  assert.equal(m.state("api"), "opening");
});

test("a teardown-then-relist heals through the needFull re-ask — NO spontaneous session frame (the field case)", () => {
  // The revival test above assumes a session frame arrives with the re-listing (the create/revive flow,
  // where the kernel genuinely pushes one). The FIELD case has no such frame: one flaky liveness read made
  // a push omit every tmux session (the collapse seam) → torn down as designed; the next push re-lists
  // them, but the kernel's per-client delta bookkeeping (echat, advanced on SEND) still believes this
  // client is caught up — so it sends only chatTail deltas the client drops, and the tab sat as the dead
  // unclickable swirl until a browser reload (seen on a remote host's tabs, 2026-08-18).
  const m = model();
  m.session("web"); m.session("api");
  m.push(["web", "api"]);
  m.push(["web"]);                        // the collapsed cycle's push: api torn down (the authority spoke)
  assert.deepEqual(m.dismissed, ["api"]);
  m.push(["web", "api"]);                 // …and the very next push lists it again
  assert.deepEqual(m.placeholders(), ["api"], "honest transient: the swirl while the re-ask is in flight");
  assert.deepEqual(m.asked, ["api"], "the re-list IS the desync signal — ask for the full session");
  m.needFullReply("api");                 // the kernel pops echat + pushes the full session NOW
  assert.deepEqual(m.placeholders(), [], "the reply fills the placeholder in — no reload needed");
  assert.equal(m.state("api"), "working");
  assert.deepEqual(m.tabs(), ["web", "api"]);
});

test("the re-ask fires once per desync and re-arms when the full session lands", () => {
  const m = model();
  m.session("web"); m.session("api");
  m.push(["web", "api"]);
  m.push(["web"]);
  m.push(["web", "api"]);
  m.push(["web", "api"]);                 // the pusher re-lists every 0.5-3s — no ask storm
  assert.deepEqual(m.asked, ["api"], "one ask while the reply is in flight");
  m.needFullReply("api");
  m.push(["web"]);                        // lost again later…
  m.push(["web", "api"]);
  assert.deepEqual(m.asked, ["api", "api"], "…a LATER desync may ask again (the reply re-armed the slot)");
});

test("the tabs-first boot never re-asks — a first-ever listing's frames are already on their way", () => {
  const m = model();
  m.push(["web", "api"]);                 // fresh page: the order lands before any session frame (by design)
  assert.deepEqual(m.placeholders(), ["web", "api"], "the designed transient placeholder strip");
  assert.deepEqual(m.asked, [], "no ask: the kernelListed gate keys the re-ask to REPEAT listings only");
  m.session("web"); m.session("api");     // the same cycle's builds land
  assert.deepEqual(m.placeholders(), []);
});

test("a host detach + reattach boots silently — no needFull burst for sessions whose frames are already in flight", () => {
  // The reattach's connect push sends tabOrder FIRST (tabs-first, by design), and the fed layer
  // re-emits the merged order before any of that push's session frames splice through — so with
  // kernelListed still holding the host's ids from before the detach, applyTabOrder re-asked for
  // every one of them on every window: N duplicate multi-MB full sends per window, queued ahead of
  // fresh deltas on the tunnel. The detach's tagged closed frames prune the ids, so the re-listing
  // is a first listing again (the exempt boot pass) and the burst never fires.
  const m = model();
  m.session("gpu1:web"); m.session("gpu1:api");
  m.push(["gpu1:web", "gpu1:api"]);                       // the host's sids, kernel-owned
  m.hostDetachEvent("gpu1:web"); m.hostDetachEvent("gpu1:api");   // detach: closeRemote's tagged frames
  assert.deepEqual(m.tabs(), [], "the detach teardown still clears the strip");
  m.push(["gpu1:web", "gpu1:api"]);                       // reattach: the remote's tabs-first connect push
  assert.deepEqual(m.asked, [], "no re-ask: the connect push IS the heal those asks would request");
  assert.deepEqual(m.placeholders(), ["gpu1:web", "gpu1:api"], "the designed transient boot strip");
  m.session("gpu1:web"); m.session("gpu1:api");           // the same push's full frames land right after
  assert.deepEqual(m.placeholders(), []);
  // …and the reattach listing re-armed the add-only record: a LATER real teardown-then-relist on
  // the same host still heals through the re-ask, exactly like a local session.
  m.push(["gpu1:web"]);
  m.push(["gpu1:web", "gpu1:api"]);
  assert.deepEqual(m.asked, ["gpu1:api"], "a genuine desync after the reattach still asks");
});

test("a create placeholder the kernel has never listed still survives unrelated pushes", () => {
  const m = model();
  m.session("web");
  m.push(["web"]);
  m.session("provisional:new");           // client-minted optimistic tab — the kernel knows nothing yet
  m.push(["web"]);                        // an unrelated push must not eat it (the just-arrived grace)
  assert.deepEqual(m.tabs(), ["web", "provisional:new"]);
  assert.deepEqual(m.dismissed, []);
});

// ---- the wiring in render.ts -------------------------------------------------------------------------

test("applyTabOrder dismisses kernel-owned omissions BEFORE reconciling, then records add-only", () => {
  // the drop loop sits between ackClosingTabs and the reconcile, and dismissSession is the shared teardown
  assert.match(RENDER,
    /ackClosingTabs\(kernelOrder\);[\s\S]{0,700}?for \(const id of order\.slice\(\)\) \{\s*\n\s*if \(kernelListed\.has\(id\) && !inKernel\.has\(id\)\) dismissSession\(id\);\s*\n\s*\}/,
    "kernel-owned tabs the push stopped carrying get the closed-event teardown");
  // the reconcile passes the kernelListed predicate, so the pure model enforces the same rule
  assert.match(RENDER,
    /reconcileTabOrder\(kernelOrder, order, \(id\) => sessions\.has\(id\) \|\| tabMeta\.has\(id\),\s*\n\s*\(id\) => kernelListed\.has\(id\)\)/);
  // add-only, recorded AFTER the reconcile: dropping entries would hand a late stale `session` frame the
  // never-listed keep and re-mint the ghost
  assert.match(RENDER, /for \(const id of next\) order\.push\(id\);[\s\S]{0,1300}?for \(const id of kernelOrder\) kernelListed\.add\(id\);/);
  const body = RENDER.match(/function dismissSession\(id: string\): void \{[\s\S]*?\n\}/);
  assert.ok(body, "dismissSession not found");
  assert.doesNotMatch(body![0], /kernelListed/, "the record outlives the dismiss (add-only set)");
});

test("applyTabOrder re-asks for a re-listed id whose session this client lost — BEFORE the add-only record", () => {
  // The re-ask keys on the kernel's own repeated claim (kernelListed = an EARLIER push listed it), so the
  // tabs-first boot — where the order deliberately lands before any session frame — never asks. It must
  // run before this push's ids are recorded, or every first listing would read as a repeat.
  assert.match(RENDER,
    /for \(const id of kernelOrder\) \{\s*\n\s*if \(kernelListed\.has\(id\) && !sessions\.has\(id\)\) requestFullSession\(id\);\s*\n\s*\}\s*\n\s*for \(const id of kernelOrder\) kernelListed\.add\(id\);/,
    "the re-ask sits between the order rebuild and the add-only kernelListed record");
});

test("the detach prune is wired: closeRemote tags its frames, the closed HANDLER prunes, dismissSession stays clean", () => {
  const FED = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "federation.ts"), "utf8");
  assert.match(FED, /\{ type: "closed", id: sid, hostDetach: true \}/,
    "the detach teardown is tagged at its one source — no kernel frame ever carries the tag");
  assert.match(RENDER, /if \(m\.hostDetach\) kernelListed\.delete\(m\.id\);\s*\n\s*dismissSession\(m\.id\);/,
    "the prune lives in the closed handler, BEFORE the dismiss");
  // the add-only property stays load-bearing for kernel-omission teardowns: dismissSession itself
  // still never touches kernelListed (also pinned structurally above)
  const body = RENDER.match(/function dismissSession\(id: string\): void \{[\s\S]*?\n\}/);
  assert.ok(body);
  assert.doesNotMatch(body![0], /kernelListed/);
});

test("reconcileTabOrder's keep is gated on the kernel never having listed the id", () => {
  const TAB_ORDER = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "tab-order.ts"), "utf8");
  assert.match(TAB_ORDER, /kernelSeen: \(id: string\) => boolean = \(\) => false/,
    "the predicate defaults off so single-shot callers keep the plain adopt-verbatim semantics");
  assert.match(TAB_ORDER, /!inKernel\.has\(id\) && known\(id\) && !kernelSeen\(id\)/,
    "extras keep = locally known AND never kernel-listed");
});

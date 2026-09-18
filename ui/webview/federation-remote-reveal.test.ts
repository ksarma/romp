// A jump to a REMOTE host's session posts the shell's chat reveal from the sending pane (review round 2 of the
// parked-pane change, 2026-09-18), and only when a remote socket took the jump (round 3). The kernel that answers a jump
// with a chat focus also tells its OWN shell clients to reveal the chat; a remote kernel has none here (the shell socket
// is local-only), so on the phone a tap on a remote session made while the chat pane was parked found no chat client at
// that kernel, parked there, and the Chat tab never came forward. FederationManager.outbound posts {romp:'reveal',
// pane:'chat'} to the shell for a jump a remote route delivered, the message waiting.ts openSession and render.ts
// revealSelfPane post: the shell shows the pane, the parked pane dials, and the remote's parked copy lands on its relay's
// first strip. A jump sendRemote DROPS (the host's socket not open: still connecting, closed under the page, or never
// dialed) posts none: the drop's toast says the action was not delivered, and a reveal for it moved the phone's tab and
// un-collapsed a desktop chat pane on a session the user never tapped (round 3; the local road posts nothing in that
// case). The op set is the kernel's, derived by AST and pinned equal to REMOTE_CHAT_REVEAL_OPS in
// tests/test_remote_chat_reveal_ops.py; here every member of the constant is driven through the real manager, with a
// fake WebSocket and a fake shell that records what the pane posts and the toasts it raises. Synthetic only (host
// TESTHOST, placeholder uuids).
import { test } from "node:test";
import assert from "node:assert/strict";
import { FederationManager, REMOTE_CHAT_REVEAL_OPS } from "./federation";

const U = "11111111-2222-3333-4444-555555555555";        // a session TESTHOST owns
const LOCAL_U = "99999999-8888-7777-6666-555555555555";  // a bare (local) session id

class FakeWS {
  static made: FakeWS[] = [];
  readyState = 0;
  sent: any[] = [];
  onopen: (() => void) | null = null;
  onmessage: ((ev: any) => void) | null = null;
  onclose: ((ev: any) => void) | null = null;
  onerror: (() => void) | null = null;
  constructor(public url: string) { FakeWS.made.push(this); }
  send(d: string): void { try { this.sent.push(JSON.parse(d)); } catch (e) { this.sent.push(d); } }
  open(): void { this.readyState = 1; this.onopen && this.onopen(); }
  close(): void { this.readyState = 3; }
}

let clock = 1_000_000_000;
// the fake pane window: `local` records what goes to the page's own socket (its clientDiag rows filtered out),
// `posted` what the pane posts to its shell, `events` the window events the manager raises (dropWarn's toast is a
// `warn` message event). `localUp` false is the parked pane's own shape (the shim's netState).
async function withManager(fn: (fm: any, local: any[], posted: any[], events: any[]) => void | Promise<void>,
                           opts: { localUp?: boolean } = {}): Promise<void> {
  const local: any[] = [], posted: any[] = [], events: any[] = [];
  const g: any = globalThis;
  const saved: Record<string, any> = {};
  const set = (k: string, v: any) => { saved[k] = { had: k in g, v: g[k] }; g[k] = v; };
  FakeWS.made = [];
  const realNow = Date.now;
  Date.now = () => clock;
  set("WebSocket", FakeWS);
  set("location", { protocol: "http:", host: "TESTHOST.local:1", search: "" });
  set("localStorage", { getItem: () => null, setItem: () => {} });
  const win: any = {
    dispatchEvent: (ev: any) => { if (ev && ev.data) events.push(ev.data); return true; },
    __rompLocalSend: (m: any) => { if (!m || m.type !== "clientDiag") local.push(m); },
    sessionStorage: { getItem: () => "" },
    parent: { postMessage: (m: any) => { posted.push(m); } },
  };
  if (opts.localUp === false) win.__rompLocalUp = false;
  set("window", win);
  try {
    await fn(new FederationManager(), local, posted, events);
  } finally {
    Date.now = realNow;
    for (const [k, r] of Object.entries(saved)) { if (r.had) g[k] = r.v; else delete g[k]; }
  }
}
const reveals = (posted: any[]) => posted.filter((p) => p && p.romp === "reveal");
const warns = (events: any[]) => events.filter((m) => m && m.type === "warn").map((m) => String(m.text || ""));
const ops = (ws: FakeWS) => ws.sent.filter((m) => m && m.type !== "ready");

/** How each op the kernel answers with a chat focus names its session, so routeOutbound carries it to TESTHOST: by `id`
 *  or `sid` (SCALAR_ID), by `session` or `name` (name-addressed, to a KNOWN host), or by an explicit `host` (the + modal's
 *  createSession). The kernel's set is derived by AST and pinned equal to REMOTE_CHAT_REVEAL_OPS in
 *  tests/test_remote_chat_reveal_ops.py; this map is pinned equal to the constant, so an op the kernel gains is driven
 *  here or fails loudly, never covered by a name alone. */
const JUMP: Record<string, { sent: any; landed: any }> = {
  openSession:    { sent: { type: "openSession", id: "TESTHOST:" + U, live: true },          landed: { type: "openSession", id: U, live: true } },
  showOnTimeline: { sent: { type: "showOnTimeline", sid: "TESTHOST:" + U, anchor: "u1" },    landed: { type: "showOnTimeline", sid: U, anchor: "u1" } },
  deepLink:       { sent: { type: "deepLink", session: "TESTHOST:" + U, anchor: "u1" },      landed: { type: "deepLink", session: U, anchor: "u1" } },
  viewReadOnly:   { sent: { type: "viewReadOnly", id: "TESTHOST:" + U },                     landed: { type: "viewReadOnly", id: U } },
  reviveSession:  { sent: { type: "reviveSession", id: "TESTHOST:" + U },                    landed: { type: "reviveSession", id: U } },
  createSession:  { sent: { type: "createSession", host: "TESTHOST", name: "web", dir: "" }, landed: { type: "createSession", name: "web", dir: "" } },
  pickResult:     { sent: { type: "pickResult", id: "TESTHOST:" + U },                       landed: { type: "pickResult", id: U } },
  openByName:     { sent: { type: "openByName", name: "TESTHOST:web" },                      landed: { type: "openByName", name: "web" } },
  forkSession:    { sent: { type: "forkSession", id: "TESTHOST:" + U, name: "web-fork" },    landed: { type: "forkSession", id: U, name: "web-fork" } },
  commentPromote: { sent: { type: "commentPromote", id: "TESTHOST:" + U, tid: "t1", name: "web-thread" }, landed: { type: "commentPromote", id: U, tid: "t1", name: "web-thread" } },
};

test("the ops this file drives are exactly REMOTE_CHAT_REVEAL_OPS, which the kernel pin derives; round 2's five are among them", () => {
  assert.deepEqual(Object.keys(JUMP).sort(), [...REMOTE_CHAT_REVEAL_OPS].sort(),
    "an op in the constant without a JUMP row here is posted for by name alone: give it a row");
  for (const op of ["openSession", "showOnTimeline", "deepLink", "viewReadOnly", "reviveSession"]) assert.ok(REMOTE_CHAT_REVEAL_OPS.has(op), op);
});

test("a remote-bound openSession rides the relay and posts exactly one chat reveal to the shell", async () => {
  await withManager((fm, local, posted, events) => {
    fm.app = "feed";                                   // the feed's card tap, the phone's usual jump
    fm.openRemote("TESTHOST", true);
    const ws = FakeWS.made[0];
    ws.open();
    fm.outbound({ type: "openSession", id: "TESTHOST:" + U, live: true });
    assert.deepEqual(ops(ws), [{ type: "openSession", id: U, live: true }], "the op goes to the owning kernel, prefix stripped");
    assert.deepEqual(local, [], "nothing to the local kernel: its shell line never runs for this jump");
    assert.deepEqual(reveals(posted), [{ romp: "reveal", pane: "chat" }], "the pane asks the shell for the chat, as waiting.ts does for a local jump");
    assert.deepEqual(warns(events), [], "a delivered jump raises no toast");
    fm.conns.get("TESTHOST").closed = true;
  });
});

test("a local-bound openSession posts no reveal: the local kernel's shell line does that", async () => {
  await withManager((fm, local, posted) => {
    fm.app = "feed";
    fm.openRemote("TESTHOST", true);
    FakeWS.made[0].open();
    fm.outbound({ type: "openSession", id: LOCAL_U, live: true });
    assert.deepEqual(local, [{ type: "openSession", id: LOCAL_U, live: true }]);
    assert.deepEqual(ops(FakeWS.made[0]), [], "a bare id routes local alone");
    assert.deepEqual(reveals(posted), []);
    fm.conns.get("TESTHOST").closed = true;
  });
});

test("a remote op the kernel answers with no chat focus posts none: activeTab, tagEdit, timelineHover", async () => {
  await withManager((fm, _local, posted) => {
    fm.app = "feed";
    fm.openRemote("TESTHOST", true);
    FakeWS.made[0].open();
    fm.outbound({ type: "activeTab", id: "TESTHOST:" + U, nonce: 1 });
    fm.outbound({ type: "tagEdit", id: "TESTHOST:" + U, name: "x" });
    fm.outbound({ type: "timelineHover", id: "TESTHOST:" + U });
    assert.deepEqual(reveals(posted), [], "only a jump brings the chat forward");
    fm.conns.get("TESTHOST").closed = true;
  });
});

test("every op in the set reaches the owning kernel with the prefix stripped and posts the reveal once, by whichever field carries its host", async () => {
  await withManager((fm, local, posted) => {
    fm.app = "timeline";
    fm.openRemote("TESTHOST", true);
    const ws = FakeWS.made[0];
    ws.open();
    const order = [...REMOTE_CHAT_REVEAL_OPS];
    for (const op of order) fm.outbound({ ...JUMP[op].sent });
    assert.deepEqual(ops(ws), order.map((op) => JUMP[op].landed), "each op reached the owning kernel, host-blind");
    assert.deepEqual(local, [], "none of them touched the local kernel");
    assert.equal(reveals(posted).length, order.length, "one reveal per jump, never per route");
    fm.conns.get("TESTHOST").closed = true;
  });
});

test("with the pane's own local socket down the relay dial is deferred, the jump is dropped with its toast, and no reveal goes out", async () => {
  // re-meant in review round 3 (2026-09-18): round 2 asserted the reveal still went out here, as what un-parks the chat
  // pane. But the jump reached no kernel (sendRemote dropped it: no socket to carry it, the toast says so), and a reveal
  // for it moves the view to a session nobody tapped. The un-park of a parked chat pane for a REMOTE tap rides the taps
  // that do go out: the feed's, whose relays are up because the feed never parks.
  await withManager((fm, _local, posted, events) => {
    fm.app = "chat";
    fm.openRemote("TESTHOST", true);
    assert.equal(FakeWS.made.length, 0, "the relay dial waits for romp:wsup (the local-down rule)");
    fm.outbound({ type: "openSession", id: "TESTHOST:" + U, live: true });
    assert.equal(FakeWS.made.length, 0, "still no socket: nothing carried the op");
    assert.deepEqual(warns(events).map((t) => /was not delivered/.test(t) && /openSession/.test(t)), [true], "the drop's toast, unchanged");
    assert.deepEqual(reveals(posted), [], "no reveal for an op that reached no kernel");
  }, { localUp: false });
});

test("a jump to a host whose relay is still CONNECTING is dropped with its toast and posts no reveal; the same jump after the open posts one", async () => {
  await withManager((fm, local, posted, events) => {
    fm.app = "feed";
    fm.openRemote("TESTHOST", true);
    const ws = FakeWS.made[0];
    assert.equal(ws.readyState, 0, "dialed, not open");
    fm.outbound({ type: "openSession", id: "TESTHOST:" + U, live: true });
    assert.deepEqual(ops(ws), [], "nothing went out on a CONNECTING socket");
    assert.deepEqual(local, []);
    assert.deepEqual(warns(events).map((t) => /was not delivered/.test(t) && /openSession/.test(t)), [true], "the drop's toast, as before");
    assert.deepEqual(reveals(posted), [], "the tab does not move for an op no kernel got");
    ws.open();
    fm.outbound({ type: "openSession", id: "TESTHOST:" + U, live: true });
    assert.deepEqual(ops(ws), [{ type: "openSession", id: U, live: true }]);
    assert.deepEqual(reveals(posted), [{ romp: "reveal", pane: "chat" }], "delivered now: one reveal");
    assert.equal(warns(events).length, 1, "no new toast");
    fm.conns.get("TESTHOST").closed = true;
  });
});

test("a host never dialed (no conn) and a relay closed under the page both drop the jump with its toast and post no reveal", async () => {
  await withManager((fm, local, posted, events) => {
    fm.app = "feed";
    fm.outbound({ type: "showOnTimeline", sid: "TESTHOST:" + U, anchor: "u1" });   // known from a frame, never dialed here
    assert.equal(FakeWS.made.length, 0);
    assert.deepEqual(local, []);
    assert.equal(warns(events).length, 1, "the drop toast");
    assert.deepEqual(reveals(posted), []);
    fm.openRemote("TESTHOST", true);
    const ws = FakeWS.made[0];
    ws.open();
    ws.close();                                          // the tunnel went down under the page (readyState 3)
    fm.outbound({ type: "reviveSession", id: "TESTHOST:" + U });
    assert.deepEqual(ops(ws), [], "nothing sent on a closed socket");
    assert.equal(warns(events).length, 2, "a second drop toast");
    assert.deepEqual(reveals(posted), [], "still no reveal");
    fm.conns.get("TESTHOST").closed = true;
  });
});

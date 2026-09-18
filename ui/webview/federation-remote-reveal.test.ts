// A jump to a REMOTE host's session posts the shell's chat reveal from the sending pane (review round 2 of the
// parked-pane change, 2026-09-18). The kernel that answers openSession, showOnTimeline, deepLink, viewReadOnly or
// reviveSession with a chat focus also tells its OWN shell clients to reveal the chat; a remote kernel has none here
// (the shell socket is local-only), so on the phone a tap on a remote session made while the chat pane was parked
// found no chat client at that kernel, parked there, and the Chat tab never came forward. FederationManager.outbound
// now posts {romp:'reveal', pane:'chat'} to the shell for a jump routed to a remote host, the message waiting.ts
// openSession and render.ts revealSelfPane post: the shell shows the pane, the parked pane dials, and the remote's
// parked copy lands on its relay's first strip. Executed against the real manager with a fake WebSocket and a fake
// shell that records what the pane posts. Synthetic only (host TESTHOST, placeholder uuids).
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
// `posted` what the pane posts to its shell. `localUp` false is the parked pane's own shape (the shim's netState).
async function withManager(fn: (fm: any, local: any[], posted: any[]) => void | Promise<void>, opts: { localUp?: boolean } = {}): Promise<void> {
  const local: any[] = [], posted: any[] = [];
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
    dispatchEvent: () => {},
    __rompLocalSend: (m: any) => { if (!m || m.type !== "clientDiag") local.push(m); },
    sessionStorage: { getItem: () => "" },
    parent: { postMessage: (m: any) => { posted.push(m); } },
  };
  if (opts.localUp === false) win.__rompLocalUp = false;
  set("window", win);
  try {
    await fn(new FederationManager(), local, posted);
  } finally {
    Date.now = realNow;
    for (const [k, r] of Object.entries(saved)) { if (r.had) g[k] = r.v; else delete g[k]; }
  }
}
const reveals = (posted: any[]) => posted.filter((p) => p && p.romp === "reveal");
const ops = (ws: FakeWS) => ws.sent.filter((m) => m && m.type !== "ready");

test("the op set is the kernel's chat-focus answers, by name", () => {
  assert.deepEqual([...REMOTE_CHAT_REVEAL_OPS].sort(), ["deepLink", "openSession", "reviveSession", "showOnTimeline", "viewReadOnly"]);
});

test("a remote-bound openSession rides the relay and posts exactly one chat reveal to the shell", async () => {
  await withManager((fm, local, posted) => {
    fm.app = "feed";                                   // the feed's card tap, the phone's usual jump
    fm.openRemote("TESTHOST", true);
    const ws = FakeWS.made[0];
    ws.open();
    fm.outbound({ type: "openSession", id: "TESTHOST:" + U, live: true });
    assert.deepEqual(ops(ws), [{ type: "openSession", id: U, live: true }], "the op goes to the owning kernel, prefix stripped");
    assert.deepEqual(local, [], "nothing to the local kernel: its shell line never runs for this jump");
    assert.deepEqual(reveals(posted), [{ romp: "reveal", pane: "chat" }], "the pane asks the shell for the chat, as waiting.ts does for a local jump");
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

test("every jump op posts the reveal once, by whichever field carries its session: id, sid or session", async () => {
  await withManager((fm, _local, posted) => {
    fm.app = "timeline";
    fm.openRemote("TESTHOST", true);
    const ws = FakeWS.made[0];
    ws.open();
    fm.outbound({ type: "showOnTimeline", sid: "TESTHOST:" + U, anchor: "u1" });
    fm.outbound({ type: "deepLink", session: "TESTHOST:" + U, anchor: "u1" });
    fm.outbound({ type: "viewReadOnly", id: "TESTHOST:" + U });
    fm.outbound({ type: "reviveSession", id: "TESTHOST:" + U });
    assert.deepEqual(ops(ws).map((m) => m.type), ["showOnTimeline", "deepLink", "viewReadOnly", "reviveSession"], "each op reached the owning kernel");
    assert.equal(reveals(posted).length, 4, "one reveal per jump, never per route");
    fm.conns.get("TESTHOST").closed = true;
  });
});

test("with the pane's own local socket down the relay dial is deferred and the reveal still goes out: it is what un-parks the chat pane", async () => {
  await withManager((fm, _local, posted) => {
    fm.app = "chat";
    fm.openRemote("TESTHOST", true);
    assert.equal(FakeWS.made.length, 0, "the relay dial waits for romp:wsup (the local-down rule)");
    fm.outbound({ type: "openSession", id: "TESTHOST:" + U, live: true });
    assert.deepEqual(reveals(posted), [{ romp: "reveal", pane: "chat" }], "the shell's show is the event the parked pane's dial waits on");
  }, { localUp: false });
});

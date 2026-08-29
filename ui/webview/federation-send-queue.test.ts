// Outbound kernel settings must survive socket churn (the user 2026-08-28, whose file-viewer Edit
// consent vanished into a restarting kernel): during a kernel restart every federated socket churns
// for a few seconds, and outbound() used to DROP any message routed to a host whose socket wasn't
// OPEN — a warn toast, nothing in the client-diag journal, and no second chance. For the gear's
// KERNEL_SETTING broadcasts that is a real loss: the Edit consent was OK'd mid-churn, the
// setFileEditing broadcast rode a closed socket into the void, and the save was later refused by a
// kernel that never heard the yes — with refusal copy pointing back at a popup already answered.
//
// The fix, two-sided:
// - KERNEL_SETTING messages queue per connection while the socket is down — LATEST per type only
//   (settings are latest-wins by nature; a reconnect must never replay a stale older value over the
//   one chosen last) — and flush on the socket's OPEN event, before any post-reconnect traffic.
//   That extends the "the flag lands first" ordering the file viewer's re-offer relies on
//   (file-view.ts) across a down-socket window.
// - Non-setting messages keep their delivery behavior (replaying an arbitrary action minutes later
//   can be worse than dropping it — a deliberate non-goal) but the drop leaves a client-diag
//   breadcrumb naming the message type and target host, next to the warn toast: never silent.
//
// End-to-end through the real FederationManager (the withManager precedent in
// multi-kernel-merge.test.ts): stub window/location/WebSocket, dial real conns, drive the sockets.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { FederationManager } from "./federation";

const U = "11111111-2222-3333-4444-555555555555";

class FakeSocket {
  static instances: FakeSocket[] = [];
  readyState = 0; // CONNECTING, like a real just-dialed WebSocket
  sent: string[] = [];
  onopen: (() => void) | null = null;
  onmessage: ((ev: unknown) => void) | null = null;
  onclose: ((ev: unknown) => void) | null = null;
  onerror: (() => void) | null = null;
  constructor(public url: string) {
    FakeSocket.instances.push(this);
  }
  send(s: string): void {
    // the real browser refuses a send on a non-open socket — a fake that accepted one would hide
    // exactly the misdelivery this suite exists to catch
    if (this.readyState !== 1) throw new Error("send() on a socket that is not OPEN");
    this.sent.push(s);
  }
  close(): void { this.readyState = 3; }
  open(): void { this.readyState = 1; if (this.onopen) this.onopen(); }
  types(): string[] { return this.sent.map((s) => JSON.parse(s).type); }
}

function withFed(fn: (fm: any, winEvents: any[], localSends: any[]) => void): void {
  const g: any = globalThis;
  const keys = ["window", "location", "WebSocket"] as const;
  const had: Record<string, boolean> = {}, prev: Record<string, any> = {};
  for (const k of keys) { had[k] = k in g; prev[k] = g[k]; }
  const winEvents: any[] = [];
  const localSends: any[] = [];
  FakeSocket.instances = [];
  g.window = {
    dispatchEvent: (ev: any) => { if (ev && ev.data) winEvents.push(ev.data); return true; },
    __rompLocalSend: (m: any) => localSends.push(m),
  };
  g.location = { protocol: "http:", host: "127.0.0.1:0", search: "" };
  g.WebSocket = FakeSocket;
  try {
    fn(new FederationManager() as any, winEvents, localSends);
  } finally {
    for (const k of keys) { if (had[k]) g[k] = prev[k]; else delete g[k]; }
  }
}

/** Dial a remote host through the real openRemote/connect path; returns its (CONNECTING) socket. */
function attach(fm: any, host: string): FakeSocket {
  fm.openRemote(host, "token-" + host, true);
  return fm.conns.get(host).ws as FakeSocket;
}

/** The poll's re-dial (federation.ts's `if (c.live && …) this.connect(c)`), minus the fetch. */
function redial(fm: any, host: string): FakeSocket {
  fm.connect(fm.conns.get(host));
  return fm.conns.get(host).ws as FakeSocket;
}

const diags = (localSends: any[], what: string) =>
  localSends.filter((m) => m && m.type === "clientDiag" && m.surface === "federation" && m.what === what);

test("a kernel setting sent while the socket is still CONNECTING is delivered on the open event", () => {
  withFed((fm, _win, localSends) => {
    const sock = attach(fm, "TESTHOSTA");
    assert.equal(sock.readyState, 0, "just dialed — not open yet");
    fm.outbound({ type: "setFileEditing", enabled: true });
    // the LOCAL kernel's copy goes out at once (the pane shim's own queue covers the local socket)
    assert.deepEqual(localSends.filter((m) => m.type === "setFileEditing"),
      [{ type: "setFileEditing", enabled: true }]);
    assert.deepEqual(sock.types(), [], "nothing can ride a CONNECTING socket");
    sock.open();
    assert.deepEqual(sock.types(), ["setFileEditing"], "the open event itself delivers the queued setting");
    assert.deepEqual(JSON.parse(sock.sent[0]), { type: "setFileEditing", enabled: true });
  });
});

test("a kernel setting sent while the socket is CLOSED rides the next reconnect (the re-dial path)", () => {
  withFed((fm) => {
    const s1 = attach(fm, "TESTHOSTA");
    s1.open();
    s1.readyState = 3; // the relay dropped (kernel restart) — the state the /tunnels poll re-dials on
    fm.outbound({ type: "setAutoNudge", enabled: false });
    assert.deepEqual(s1.sent.length, 0, "the dead socket carried nothing");
    const s2 = redial(fm, "TESTHOSTA");
    assert.notEqual(s2, s1, "the re-dial made a fresh socket");
    s2.open();
    assert.deepEqual(s2.types(), ["setAutoNudge"], "the queued setting flushes on the fresh socket's open");
  });
});

test("latest-wins: two sends of one setting type while down deliver only the newest value", () => {
  withFed((fm) => {
    const sock = attach(fm, "TESTHOSTA");
    fm.outbound({ type: "setFileEditing", enabled: true });
    fm.outbound({ type: "setJudgeModel", model: "m1" });
    fm.outbound({ type: "setFileEditing", enabled: false }); // the user changed their mind while down
    sock.open();
    const msgs = sock.sent.map((s) => JSON.parse(s));
    assert.deepEqual(msgs.map((m: any) => m.type).sort(), ["setFileEditing", "setJudgeModel"],
      "one message per setting type, distinct types both flush");
    const fe = msgs.filter((m: any) => m.type === "setFileEditing");
    assert.equal(fe.length, 1, "the stale older value is never replayed");
    assert.equal(fe[0].enabled, false, "the newest value wins");
  });
});

test("a setting queued for one host never leaks to another, and a host that heard it live hears it once", () => {
  withFed((fm) => {
    const a = attach(fm, "TESTHOSTA"); // still CONNECTING — down at send time
    const b = attach(fm, "TESTHOSTB");
    b.open();
    fm.outbound({ type: "setDistillModel", model: "m2" });
    assert.deepEqual(b.types(), ["setDistillModel"], "the reachable host hears the broadcast live");
    assert.deepEqual(a.types(), [], "the down host holds it queued");
    a.open();
    assert.deepEqual(a.types(), ["setDistillModel"], "the queued copy reaches its own host on open");
    assert.deepEqual(b.types(), ["setDistillModel"], "…and the other host is not re-sent what it already heard");
  });
});

test("a NON-setting drop stays a drop — but leaves a client-diag breadcrumb and the warn toast", () => {
  withFed((fm, winEvents, localSends) => {
    const s1 = attach(fm, "TESTHOSTA");
    s1.open();
    s1.readyState = 3;
    fm.outbound({ type: "openSession", id: "TESTHOSTA:" + U });
    const dg = diags(localSends, "senddrop");
    assert.equal(dg.length, 1, "the drop is journaled, never silent");
    assert.equal(dg[0].data.host, "TESTHOSTA");
    assert.equal(dg[0].data.msgType, "openSession");
    assert.ok(winEvents.some((m) => m.type === "warn" && /TESTHOSTA/.test(m.text || "")),
      "the user-visible warn toast stays");
    const s2 = redial(fm, "TESTHOSTA");
    s2.open();
    assert.deepEqual(s2.types(), [],
      "a dropped action is never replayed later — a stale action can be worse than a dropped one");
  });
});

test("the undoClear send site drops loudly too: diag + warn on a down socket", () => {
  withFed((fm, winEvents, localSends) => {
    attach(fm, "TESTHOSTA"); // still CONNECTING
    fm.lastClearHost = "TESTHOSTA";
    fm.outbound({ type: "undoClear" });
    const dg = diags(localSends, "senddrop");
    assert.equal(dg.length, 1);
    assert.equal(dg[0].data.msgType, "undoClear");
    assert.ok(winEvents.some((m) => m.type === "warn"), "the toast fires for this site as well");
  });
});

test("flush ordering: a queued setting lands before any message sent after the reconnect", () => {
  withFed((fm) => {
    const s1 = attach(fm, "TESTHOSTA");
    s1.open();
    s1.readyState = 3;
    fm.outbound({ type: "setFileEditing", enabled: true }); // the consent click, mid-churn
    const s2 = redial(fm, "TESTHOSTA");
    s2.open();
    assert.deepEqual(s2.types(), ["setFileEditing"],
      "the flush is synchronous with the open event — no timer, no later tick");
    // the very next post-reconnect send (e.g. the file viewer retrying its save) must find the
    // flag already landed — the same-ordered-socket guarantee, now across the down window
    fm.outbound({ type: "fileSave", sid: "TESTHOSTA:" + U, text: "x" });
    assert.deepEqual(s2.types(), ["setFileEditing", "fileSave"]);
  });
});

// Source pins, in the federation-remote-gate.test.ts style: the properties above hold only while
// every remote send routes through the ONE queue-aware helper, and the flush hangs on the open
// event itself — a raw `ws.send` site or a timer-based flush would reopen the hole quietly.
const FED = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "federation.ts"), "utf8");

test("both outbound remote send sites route through sendRemote — no raw inline drop path remains", () => {
  const outb = FED.slice(FED.indexOf("outbound(m: any): void {"), FED.indexOf("private dropWarn"));
  assert.match(outb, /this\.sendRemote\(this\.lastClearHost, m\);/);
  assert.match(outb, /this\.sendRemote\(r\.host, r\.msg\);/);
  assert.doesNotMatch(outb, /readyState === 1\) c\.ws\.send/,
    "the old drop-if-not-open inline sends must not come back");
});

test("the pending-settings flush rides the socket's open event, never a timer", () => {
  const connectFn = FED.slice(FED.indexOf("private connect(conn: Conn)"));
  const onopen = connectFn.slice(connectFn.indexOf("ws.onopen"), connectFn.indexOf("ws.onmessage"));
  assert.match(onopen, /flushPending/, "onopen is the flush hook");
  const flushFn = FED.slice(FED.indexOf("private flushPending"), FED.indexOf("private connect(conn: Conn)"));
  assert.ok(flushFn.length > 0, "flushPending exists");
  assert.doesNotMatch(flushFn, /setTimeout|setInterval/, "no timer anywhere in the flush");
});

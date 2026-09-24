// The relay sockets' liveness watchdog + the timeline's pending-host signal (the user 2026-09-02).
//
// The audited two-minute gap: after a phone re-foreground the dashboard's relay sockets to two attached,
// healthy hosts OPENED and then delivered nothing — dead on arrival — and, unlike the pane shim's LOCAL
// socket (30s keepalive watchdog), federation.ts's remote sockets had no liveness check at all, so the
// hosts rendered as simply absent until TCP gave up ~104s later. Executed against the real manager with
// a fake WebSocket: the verdict table, the close+redial on silence, the foreground fast-path, the
// breadcrumb, and the pending set the panes and the shell read while a host is still coming. Synthetic
// only (host TESTHOST, placeholder uuids).
import { test } from "node:test";
import assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { FederationManager, PANE_CHANNELS, mergeHostTimelines, socketVerdict,
         REMOTE_STALE_MS, REMOTE_CONNECT_MS, REMOTE_REDIAL_MS, REMOTE_PROVISIONAL_MS } from "./federation";

const U = "11111111-2222-3333-4444-555555555555";

// ── the pure verdict ─────────────────────────────────────────────────────────────────────────────
test("socketVerdict: an OPEN socket silent past the keepalive bound is closed; a fresh one is left alone", () => {
  const t = 1_000_000;
  assert.equal(socketVerdict(1, t, t - 5000, t + REMOTE_STALE_MS + 1), "close", "31s of silence since open");
  assert.equal(socketVerdict(1, t, t - 5000, t + REMOTE_STALE_MS), "", "at the bound, not past it");
  assert.equal(socketVerdict(1, t + 20000, t, t + 25000), "", "a frame 5s ago keeps it");
  // silence is measured from THIS socket's own open (lastRecv stamped at onopen), never an earlier socket's traffic
  assert.equal(socketVerdict(1, 0, t, t + REMOTE_STALE_MS + 1), "close", "no frame at all → the connect stamp is the reference");
});

test("socketVerdict: a hung handshake is aborted; a CLOSED socket with no fresh attempt is redialed", () => {
  const t = 1_000_000;
  assert.equal(socketVerdict(0, 0, t, t + REMOTE_CONNECT_MS + 1), "close", "CONNECTING past 15s");
  assert.equal(socketVerdict(0, 0, t, t + 3000), "", "a young handshake is left to finish");
  assert.equal(socketVerdict(3, 0, t, t + REMOTE_REDIAL_MS + 1), "redial", "CLOSED 8s+ with no new connect = a lost retry timer");
  assert.equal(socketVerdict(3, 0, t, t + 1000), "", "the 2s onclose redial is still coming");
  assert.equal(socketVerdict(2, 0, t, t + 99999), "", "CLOSING is in flight — onclose will follow");
});

test("the bounds are the pane shim's, byte for byte (kernel keepalive 10s → stale at 30s)", () => {
  assert.equal(REMOTE_STALE_MS, 30000);
  assert.equal(REMOTE_CONNECT_MS, 15000);
  assert.equal(REMOTE_REDIAL_MS, 8000);
  assert.equal(REMOTE_PROVISIONAL_MS, 15000, "a resumed keep no frame has confirmed: 1.5 keepalive periods");
});

// ── the manager, end to end, with a fake WebSocket ──────────────────────────────────────────────
class FakeWS {
  static made: FakeWS[] = [];
  readyState = 0;
  closed = 0;
  onopen: (() => void) | null = null;
  onmessage: ((ev: any) => void) | null = null;
  onclose: ((ev: any) => void) | null = null;
  onerror: (() => void) | null = null;
  constructor(public url: string) { FakeWS.made.push(this); }
  open(): void { this.readyState = 1; this.onopen && this.onopen(); }
  frame(data: any): void { this.onmessage && this.onmessage({ data: JSON.stringify(data) }); }
  close(): void { this.closed++; this.readyState = 3; }
  die(code = 1006): void { this.readyState = 3; this.onclose && this.onclose({ code, wasClean: false }); }
}

// the test owns the clock: the manager stamps connT/lastRecv with Date.now(), and the watchdog is
// ticked with an explicit `now`, so silence is advanced by hand rather than waited out
let clock = 1_000_000_000;
async function withManager(fn: (fm: any, emitted: any[], diag: any[], posted: any[]) => void | Promise<void>): Promise<void> {
  const emitted: any[] = [], diag: any[] = [], posted: any[] = [];
  const g: any = globalThis;
  const saved: Record<string, any> = {};
  const set = (k: string, v: any) => { saved[k] = { had: k in g, v: g[k] }; g[k] = v; };
  FakeWS.made = [];
  const realNow = Date.now;
  Date.now = () => clock;
  set("WebSocket", FakeWS);
  set("location", { protocol: "http:", host: "TESTHOST.local:1" });
  set("localStorage", { getItem: () => null, setItem: () => {} });
  const parent = { postMessage: (m: any) => { posted.push(m); } };
  set("window", {
    dispatchEvent: (ev: any) => { if (ev && ev.data) emitted.push(ev.data); },
    __rompLocalSend: (m: any) => { if (m && m.type === "clientDiag") diag.push(m); },
    sessionStorage: { getItem: () => "" },
    parent,
  });
  try {
    await fn(new FederationManager(), emitted, diag, posted);   // awaited: the globals must outlive an async poll
  } finally {
    Date.now = realNow;
    for (const [k, r] of Object.entries(saved)) { if (r.had) g[k] = r.v; else delete g[k]; }
  }
}
const localFeed = { type: "feed", asks: [], items: [], working: [], ledgers: [], order: [], sessions: [], now: 1000, buildId: 1 };

test("a relay socket that opens and then goes silent past the bound is abandoned with a breadcrumb, and a fresh one dialed at once", async () => {
  await withManager((fm, _emitted, diag) => {
    fm.openRemote("TESTHOST", true);
    assert.equal(FakeWS.made.length, 1, "an up host is dialed at once");
    const ws = FakeWS.made[0];
    assert.match(ws.url, /\/remote\/TESTHOST\/ws\?app=chat/, "the dial goes through the local kernel's relay");
    assert.doesNotMatch(ws.url, /token=/, "…which adds the remote's credential itself; the page never carries one (2026-09-08)");
    ws.open();
    clock += 10_000;
    fm.watchdog(clock);
    assert.equal(ws.closed, 0, "10s after open: still inside the keepalive bound");
    clock += 15_000;
    ws.frame({ type: "ka", dv: 1 });                       // a keepalive counts as life — that IS the heartbeat
    clock += 20_000;                                        // 45s since open, but only 20s since the last frame
    fm.watchdog(clock);
    assert.equal(ws.closed, 0, "the keepalive 20s ago reset the clock");
    clock += REMOTE_STALE_MS;                               // 50s of silence since that frame
    fm.watchdog(clock);
    assert.equal(ws.closed, 1, "silent past the bound → the watchdog puts the dead-on-arrival socket down");
    const crumb = diag.find((d) => d.what === "hostconn" && d.data && d.data.ev === "watchdog-close");
    assert.ok(crumb, "the close lands in the hostconn breadcrumb family, so client-diag says WHO closed it");
    assert.equal(crumb.data.host, "TESTHOST");
    assert.equal(crumb.data.why, "quiet");
    assert.ok(crumb.data.quietMs > REMOTE_STALE_MS, "…and how long it had been silent");
    // NOT waited for: a dead socket's closing handshake never completes (the browser holds CLOSING
    // ~60s before onclose) — the fresh dial happens in the same pass, and the corpse is disowned
    assert.equal(FakeWS.made.length, 2, "a fresh socket is dialed at once");
    const conn = fm.conns.get("TESTHOST");
    assert.equal(conn.ws, FakeWS.made[1], "the conn now owns the new socket");
    assert.equal(ws.onclose, null, "the abandoned socket's handlers are detached — its late onclose redials nothing");
    assert.equal(ws.onmessage, null);
    FakeWS.made[1].open();
    FakeWS.made[1].frame({ type: "feed", asks: [] });
    assert.equal(diag.filter((d) => d.data && d.data.ev === "watchdog-close").length, 1, "one crumb per abandonment");
    conn.closed = true;
  });
});

test("the foreground fast-path kills a socket still CONNECTING, whatever its age — the sleeping tab's unfinished handshake", async () => {
  await withManager((fm, _e, diag) => {
    fm.openRemote("TESTHOST", true);
    const ws = FakeWS.made[0];              // never opens (readyState 0)
    clock += 1000;
    fm.watchdog(clock);
    assert.equal(ws.closed, 0, "a 1s-old handshake is left to finish on a plain tick");
    fm.watchdog(clock, true);
    assert.equal(ws.closed, 1, "…but a foreground pass closes it now rather than waiting the handshake bound out");
    assert.equal(diag.filter((d) => d.data && d.data.ev === "watchdog-close" && d.data.why === "connecting" && d.data.foreground).length, 1);
    assert.equal(FakeWS.made.length, 2, "…and dials a fresh one in the same pass");
    fm.conns.get("TESTHOST").closed = true;
  });
});

test("a CLOSED socket whose retry timer was lost is redialed directly (the throttled-tab case)", async () => {
  await withManager((fm) => {
    fm.openRemote("TESTHOST", true);
    const conn = fm.conns.get("TESTHOST");
    conn.ws.readyState = 3;                 // closed under us with no onclose → no 2s timer armed
    clock += REMOTE_REDIAL_MS + 1000;
    fm.watchdog(clock);
    assert.equal(FakeWS.made.length, 2, "the watchdog dialed a fresh socket");
    conn.closed = true;
  });
});

test("a detached host is never touched by the watchdog, and a DOWN tunnel is never dialed by it", async () => {
  await withManager((fm) => {
    fm.openRemote("TESTHOST", false);   // /tunnels says not up → no socket
    assert.equal(FakeWS.made.length, 0);
    clock += 999_999;
    fm.watchdog(clock);
    assert.equal(FakeWS.made.length, 0, "no dial against a tunnel the kernel calls down");
    fm.openRemote("HOSTB", true);
    fm.closeRemote("HOSTB");                  // detach → closed:true
    const n = FakeWS.made.length;
    clock += 999_999;
    fm.watchdog(clock);
    assert.equal(FakeWS.made.length, n, "a detached conn is skipped, never redialed");
  });
});

// ── the Page Lifecycle `resume` stamp (the user 2026-09-07, whose dashboard froze on return) ─────
// A Chromium tab left in the background is FROZEN: no JS runs, so no frame can stamp lastRecv even
// while the socket underneath stays open and the kernel keeps heartbeating. lastRecv then measures
// "JS did not run", not "the socket went silent" — and the foreground fast-path above read that as
// 30s+ of silence and abandoned+redialed EVERY attached host on every thaw, each redial a full resend.
// The thaw fires `resume` before `visibilitychange`; stamping every OPEN socket there makes the
// foreground pass see fresh sockets and keep them. socketVerdict itself is unchanged.
test("`resume` stamps every OPEN relay socket's lastRecv — and only the open ones", async () => {
  await withManager((fm) => {
    fm.openRemote("TESTHOST", true);
    fm.openRemote("HOSTB", true);
    fm.openRemote("HOSTC", true);
    const [a, b, c] = FakeWS.made;
    a.open(); b.open();                                   // c never finishes its handshake (CONNECTING)
    clock += 45_000;                                      // frozen: no JS ran, so no frame was stamped
    fm.resumed(clock);
    assert.equal(fm.conns.get("TESTHOST").lastRecv, clock, "an open socket is stamped at the thaw");
    assert.equal(fm.conns.get("HOSTB").lastRecv, clock, "…every open socket, not just the first");
    assert.equal(fm.conns.get("HOSTC").lastRecv, 0, "a CONNECTING socket is NOT stamped — the foreground pass must still kill it");
    assert.equal(c.readyState, 0);
    for (const h of ["TESTHOST", "HOSTB", "HOSTC"]) fm.conns.get(h).closed = true;
  });
});

test("thaw: `resume` then the foreground watchdog pass closes NOTHING — and silence AFTER the resume still counts", async () => {
  await withManager((fm, _e, diag) => {
    fm.openRemote("TESTHOST", true);
    fm.openRemote("HOSTB", true);
    const [a, b] = FakeWS.made;
    a.open(); b.open();
    clock += 45_000;                                      // well past REMOTE_STALE_MS with no frame
    fm.resumed(clock);
    fm.watchdog(clock, true);                             // the visibilitychange fast-path, as on every thaw
    assert.equal(a.closed, 0, "the open socket is kept: the resume re-based its silence to now");
    assert.equal(b.closed, 0, "…for every attached host");
    assert.equal(FakeWS.made.length, 2, "no redial → no full resend from either kernel");
    assert.equal(diag.filter((d) => d.data && d.data.ev === "watchdog-close").length, 0, "nothing was put down, so no crumb");
    clock += 5000;
    fm.watchdog(clock);
    assert.equal(a.closed, 0, "the next plain tick keeps it too");
    // the stamp re-BASES the watchdog, it does not disarm it: a socket that stays silent after the
    // thaw (dead on arrival, FIN never delivered) is still abandoned (at the provisional bound since
    // 2026-09-08, see below; this tick is past either)
    clock += REMOTE_STALE_MS;
    fm.watchdog(clock);
    assert.equal(a.closed, 1, "30s+ of real silence after the resume → abandoned as before");
    assert.equal(b.closed, 1);
    assert.equal(FakeWS.made.length, 4, "…and redialed");
    for (const h of ["TESTHOST", "HOSTB"]) fm.conns.get(h).closed = true;
  });
});

test("no `resume` (a browser without Page Lifecycle, or a tab that was hidden but running): the stale verdict still closes on foreground", async () => {
  await withManager((fm, _e, diag) => {
    fm.openRemote("TESTHOST", true);
    const ws = FakeWS.made[0];
    ws.open();
    clock += 45_000;                                      // 45s with no frame and no resume = real silence
    fm.watchdog(clock, true);
    assert.equal(ws.closed, 1, "abandoned exactly as before the resume stamp existed");
    assert.equal(FakeWS.made.length, 2, "…and a fresh socket dialed in the same pass");
    const crumb = diag.find((d) => d.data && d.data.ev === "watchdog-close");
    assert.equal(crumb.data.why, "quiet");
    assert.equal(crumb.data.foreground, true);
    fm.conns.get("TESTHOST").closed = true;
  });
});

test("a CONNECTING socket is still killed on foreground after a `resume` — the stamp never reaches an unfinished handshake", async () => {
  await withManager((fm, _e, diag) => {
    fm.openRemote("TESTHOST", true);
    const ws = FakeWS.made[0];                            // never opens
    clock += 1000;
    fm.resumed(clock);
    assert.equal(fm.conns.get("TESTHOST").lastRecv, 0, "not stamped");
    fm.watchdog(clock, true);
    assert.equal(ws.closed, 1, "the foreground pass closes it now, resume or not");
    assert.equal(FakeWS.made.length, 2, "…and dials a fresh one");
    assert.equal(diag.filter((d) => d.data && d.data.ev === "watchdog-close" && d.data.why === "connecting" && d.data.foreground).length, 1);
    fm.conns.get("TESTHOST").closed = true;
  });
});

// ── the relay dial waits for the pane's LOCAL socket (2026-09-18) ────────────────────────────────
// The relay is the same kernel's /remote/<host>/ws on location.host, so it cannot open while the pane's local
// socket is down; the shim publishes that socket's state as window.__rompLocalUp (kernel.py netState) and fires
// romp:wsup when it reopens. On the user's phone every return from the background had every manager dial the
// relay into a dead path, the tick cut the hung handshake at 15 s and dialed again: 55 `watchdog-close
// connecting` rows in 23 minutes. Now the kill stays and the DIAL waits: one dial-deferred row per conn per
// down spell, the redial on romp:wsup (localUp) with the 4 s poll as the backstop, and no /tunnels GET meanwhile.
const DEFERRED = { host: "TESTHOST", ev: "dial-deferred", why: "local-down" };

test("local socket down: the foreground pass still abandons a quiet relay socket, but the dial is deferred with one row per spell; the pane's can't-reach line names the host while it is still coming", async () => {
  const g: any = globalThis;
  const hadFetch = "fetch" in g, prevFetch = g.fetch;
  g.fetch = async () => ({ ok: true, json: async () => ({ tunnels: [{ host: "TESTHOST", hasToken: true, localPort: 5, status: "up" }] }) });
  try {
    await withManager(async (fm, emitted, diag) => {
      fm.app = "feed";
      fm.openRemote("TESTHOST", true);
      const ws = FakeWS.made[0];
      ws.open();
      g.window.__rompLocalUp = false;                      // the shim put its socket down (netState("down"))
      clock += 45_000;
      fm.watchdog(clock, true);
      assert.equal(ws.closed, 1, "the quiet socket is put down exactly as before");
      const kills = () => diag.filter((d) => d.data && d.data.ev === "watchdog-close");   // re-filtered at each check: a snapshot bound here could not fail below (round 1)
      assert.equal(kills().length, 1);
      assert.equal(kills()[0].data.why, "quiet");
      const conn = fm.conns.get("TESTHOST");
      assert.equal(conn.ws, null, "the corpse is disowned and nulled");
      assert.equal(FakeWS.made.length, 1, "…and NO fresh socket is dialed while the local socket is down");
      let rows = diag.filter((d) => d.what === "hostconn" && d.data && d.data.ev === "dial-deferred");
      assert.equal(rows.length, 1, "the deferral is said once");
      assert.deepEqual(rows[0].data, DEFERRED, "fixed identifiers only: the row carries no free text");
      assert.equal(conn.deferred, true);
      // The one visible change: the deferred conn's null socket is a dead link to deadHosts(), so the merged feed's
      // pendingDead names the host and the pane shows its can't-reach line for a host it is still WAITING on, where a
      // hung handshake read as dialing. The line is the pending host's: a host whose payload already landed shows its
      // cards and no line, deferred or not.
      assert.deepEqual(fm.deadHosts(), ["TESTHOST"], "no socket while deferred = a dead link right now");
      fm.inbound("", localFeed);
      const feed = () => emitted.filter((m) => m.type === "feed").pop();
      assert.deepEqual(feed().pendingHosts, ["TESTHOST"], "no feed payload from it yet: the pane waits on it");
      assert.deepEqual(feed().pendingDead, ["TESTHOST"], "…on a dead link, so the pane says it cannot reach the host instead of an open-ended wait");
      fm.inbound("TESTHOST", { type: "feed", asks: [], items: [], working: [], ledgers: [], order: [], sessions: [], now: 1000 });   // a payload that landed before the outage
      assert.deepEqual(feed().pendingHosts, [], "its payload retires the wait");
      assert.deepEqual(feed().pendingDead, [], "…and with it the line: the mark is the pending host's, not every remote session's");
      assert.deepEqual(fm.deadHosts(), ["TESTHOST"], "the link itself still reads dead");
      clock += 5_000;
      fm.watchdog(clock);                                  // a plain tick: a null socket is nobody's to verdict
      fm.watchdog(clock, true);                            // a second foreground pass (the phone's next return in the same outage)
      fm.connect(conn);                                    // a lost retry timer firing, or the poll's dial
      assert.equal(FakeWS.made.length, 1, "still no dial");
      rows = diag.filter((d) => d.data && d.data.ev === "dial-deferred");
      assert.equal(rows.length, 1, "a second deferral in the same spell files no second row");
      assert.equal(kills().length, 1, "and nothing else was killed");
      // the local socket's return: the deferred dial runs, and a socket dialing is not a dead link
      g.window.__rompLocalUp = true;
      fm.localUp();
      assert.equal(FakeWS.made.length, 2, "the dial that waited runs on the return");
      assert.equal(conn.ws, FakeWS.made[1]);
      assert.equal(conn.deferred, false);
      assert.deepEqual(fm.deadHosts(), [], "CONNECTING is not dead: the line would go with the next merged frame");
      await new Promise((r) => setTimeout(r, 0));          // let localUp's poll finish while the fakes stand
      conn.closed = true;
    });
  } finally {
    if (hadFetch) g.fetch = prevFetch; else delete g.fetch;
  }
});

test("local socket down: a CONNECTING relay socket is still killed on foreground, and its redial waits", async () => {
  await withManager((fm, _e, diag) => {
    const g: any = globalThis;
    fm.openRemote("TESTHOST", true);
    const ws = FakeWS.made[0];                           // never opens: the handshake into the dead path
    g.window.__rompLocalUp = false;
    clock += 1000;
    fm.watchdog(clock, true);
    assert.equal(ws.closed, 1, "the foreground kill of a CONNECTING socket is unchanged");
    assert.equal(diag.filter((d) => d.data && d.data.ev === "watchdog-close" && d.data.why === "connecting").length, 1);
    assert.equal(FakeWS.made.length, 1, "no second handshake into the same dead path");
    assert.equal(diag.filter((d) => d.data && d.data.ev === "dial-deferred").length, 1);
    fm.conns.get("TESTHOST").closed = true;
  });
});

test("the local socket's return (romp:wsup → localUp) dials every live conn whose socket is null or CLOSED, once, and runs one poll", async () => {
  const g: any = globalThis;
  const hadFetch = "fetch" in g, prevFetch = g.fetch;
  let fetches = 0;
  g.fetch = async () => { fetches++; return { ok: true, json: async () => ({ tunnels: [
    { host: "TESTHOST", hasToken: true, localPort: 5, status: "up" },
    { host: "HOSTB", hasToken: true, localPort: 6, status: "up" },
    { host: "HOSTC", hasToken: true, localPort: 7, status: "up" },
  ] }) }; };
  try {
    await withManager(async (fm, _e, diag) => {
      fm.openRemote("TESTHOST", true);                   // will be the deferred one (ws null)
      fm.openRemote("HOSTB", true);                      // will be CLOSED under us (readyState 3, no timer)
      fm.openRemote("HOSTC", true);                      // stays CONNECTING: not touched
      assert.equal(FakeWS.made.length, 3);
      FakeWS.made[0].open();
      g.window.__rompLocalUp = false;
      clock += 45_000;
      fm.watchdog(clock, true);                          // TESTHOST abandoned, dial deferred; HOSTB/HOSTC CONNECTING → killed too, deferred
      assert.equal(FakeWS.made.length, 3, "nothing dialed while down");
      assert.equal(diag.filter((d) => d.data && d.data.ev === "dial-deferred").length, 3, "one row per conn");
      const b = fm.conns.get("HOSTB");
      b.ws = FakeWS.made[1]; b.ws.readyState = 3;        // a CLOSED socket whose retry timer was lost (the throttled-tab case)
      const c = fm.conns.get("HOSTC");
      c.ws = FakeWS.made[2]; c.ws.readyState = 0;        // a handshake in flight again (the kill above had set the fake CLOSED)
      // the shim's onopen flips the flag BEFORE it dispatches romp:wsup
      g.window.__rompLocalUp = true;
      const listeners: Record<string, Array<() => void>> = {};
      fm.watchLocalLink({ addEventListener(t: string, fn: () => void) { (listeners[t] ||= []).push(fn); } });
      assert.equal((listeners["romp:wsup"] || []).length, 1, "one romp:wsup listener");
      for (const fn of listeners["romp:wsup"]) fn();
      assert.equal(FakeWS.made.length, 5, "TESTHOST (null) and HOSTB (CLOSED) dialed; HOSTC (CONNECTING) left alone");
      assert.equal(fm.conns.get("TESTHOST").ws, FakeWS.made[3]);
      assert.equal(fm.conns.get("TESTHOST").deferred, false, "the dial that ran clears the spell");
      assert.equal(b.ws, FakeWS.made[4]);
      assert.equal(c.ws, FakeWS.made[2]);
      assert.equal(fetches, 1, "one /tunnels read rides the return");
      await new Promise((r) => setTimeout(r, 0));        // let that poll finish while the fakes stand
      assert.equal(FakeWS.made.length, 5, "the poll found every host dialed or dialing: no second dial");
      for (const fn of listeners["romp:wsup"]) fn();     // a second wsup with everything up
      assert.equal(FakeWS.made.length, 5, "nothing to dial");
      assert.equal(fetches, 2);
      await new Promise((r) => setTimeout(r, 0));
      for (const x of fm.conns.values()) x.closed = true;
    });
  } finally {
    if (hadFetch) g.fetch = prevFetch; else delete g.fetch;
  }
});

test("localUp dials nothing for a detached conn or a host /tunnels says is down", async () => {
  const g: any = globalThis;
  const hadFetch = "fetch" in g, prevFetch = g.fetch;
  g.fetch = async () => ({ ok: true, json: async () => ({ tunnels: [] }) });
  try {
    await withManager(async (fm) => {
      fm.openRemote("TESTHOST", false);                  // not up: never dialed
      const c = fm.conns.get("TESTHOST");
      g.window.__rompLocalUp = true;
      fm.localUp();
      assert.equal(FakeWS.made.length, 0, "a down tunnel is not dialed by the return either");
      c.live = true; c.closed = true;
      fm.localUp();
      assert.equal(FakeWS.made.length, 0, "nor a detached conn");
      await new Promise((r) => setTimeout(r, 0));
    });
  } finally {
    if (hadFetch) g.fetch = prevFetch; else delete g.fetch;
  }
});

test("local socket up, or no flag at all (a page without the shim, VS Code): the foreground pass dials in the same pass, as before", async () => {
  await withManager((fm, _e, diag) => {
    const g: any = globalThis;
    assert.ok(!("__rompLocalUp" in g.window), "the harness window carries no flag: today's every other test runs this path");
    fm.openRemote("TESTHOST", true);
    FakeWS.made[0].open();
    clock += 45_000;
    fm.watchdog(clock, true);
    assert.equal(FakeWS.made.length, 2, "undefined: abandon and dial in one pass");
    FakeWS.made[1].open();
    g.window.__rompLocalUp = true;
    clock += 45_000;
    fm.watchdog(clock, true);
    assert.equal(FakeWS.made.length, 3, "true: the same");
    assert.equal(diag.filter((d) => d.data && d.data.ev === "dial-deferred").length, 0, "no deferral row on either path");
    assert.ok(!fm.conns.get("TESTHOST").deferred, "no spell open (this case passes before the change too: it pins the path that must not move)");
    fm.conns.get("TESTHOST").closed = true;
  });
});

test("poll(): no /tunnels GET while the local socket is down; the first poll after the flip reads it (the backstop for a missed romp:wsup)", async () => {
  const g: any = globalThis;
  const hadFetch = "fetch" in g, prevFetch = g.fetch;
  let fetches = 0;
  g.fetch = async () => { fetches++; return { ok: true, json: async () => ({ tunnels: [{ host: "TESTHOST", hasToken: true, localPort: 5, status: "up" }] }) }; };
  try {
    await withManager(async (fm, _e, diag) => {
      g.window.__rompLocalUp = false;
      await fm.poll();
      assert.equal(fetches, 0, "no GET into the origin the socket cannot reach");
      assert.equal(fm.hostsRead, false, "a list that was not read is not a list in hand");
      assert.equal(fm.pollFailing, false, "…and not a failure either: nothing was tried");
      assert.equal(diag.length, 0, "no row: the poll is simply held");
      g.window.__rompLocalUp = true;
      await fm.poll();
      assert.equal(fetches, 1, "the next 4 s poll reads the flag the shim flipped at its onopen");
      assert.equal(fm.hostsRead, true);
      assert.equal(FakeWS.made.length, 1, "and dials the host it lists");
      delete g.window.__rompLocalUp;
      await fm.poll();
      assert.equal(fetches, 2, "no flag: polls as before");
      fm.conns.get("TESTHOST").closed = true;
    });
  } finally {
    if (hadFetch) g.fetch = prevFetch; else delete g.fetch;
  }
});

test("the 4 s poll is the backstop: a deferred conn (null socket) is redialed by the first poll that reads the flag true, with no romp:wsup; a second down spell files a second row", async () => {
  const g: any = globalThis;
  const hadFetch = "fetch" in g, prevFetch = g.fetch;
  g.fetch = async () => ({ ok: true, json: async () => ({ tunnels: [{ host: "TESTHOST", hasToken: true, localPort: 5, status: "up" }] }) });
  try {
    await withManager(async (fm, _e, diag) => {
      fm.openRemote("TESTHOST", true);
      const ws = FakeWS.made[0];                           // the handshake into the dead path: never opens
      g.window.__rompLocalUp = false;
      clock += 1000;
      fm.watchdog(clock, true);                            // the foreground kill; its redial is deferred
      const conn = fm.conns.get("TESTHOST");
      assert.equal(ws.closed, 1);
      assert.equal(conn.ws, null);
      assert.equal(conn.deferred, true);
      assert.equal(FakeWS.made.length, 1, "nothing dialed while down");
      const rows = () => diag.filter((d) => d.data && d.data.ev === "dial-deferred");
      assert.equal(rows().length, 1);
      // a FIRST open dispatches no romp:wsup (the loader waits for content), so nothing calls localUp: the shim flipped
      // the flag at its onopen and the next poll reads it, taking the null socket as a lost dial
      g.window.__rompLocalUp = true;
      await fm.poll();
      assert.equal(FakeWS.made.length, 2, "the poll's dial loop redials the deferred conn");
      assert.equal(conn.ws, FakeWS.made[1]);
      assert.equal(conn.deferred, false, "the dial that ran ends the spell");
      assert.equal(rows().length, 1, "no new row: a spell ended, none began");
      // a second down spell while that handshake is in flight: the kill is the same, and the redial waits again
      g.window.__rompLocalUp = false;
      clock += 1000;
      fm.watchdog(clock, true);
      assert.equal(FakeWS.made[1].closed, 1, "the foreground kill of the CONNECTING socket, as before");
      assert.equal(conn.ws, null);
      assert.equal(conn.deferred, true);
      assert.equal(FakeWS.made.length, 2, "no dial while down");
      assert.equal(rows().length, 2, "one row per conn per spell: the second spell files its own");
      conn.closed = true;
    });
  } finally {
    if (hadFetch) g.fetch = prevFetch; else delete g.fetch;
  }
});

test("the document wiring: `resume` then `visibilitychange`→visible keeps an open socket; `visibilitychange` alone abandons a quiet one; hidden fires nothing", async () => {
  await withManager((fm) => {
    // a fake document that records the listeners and lets the test fire them in the browser's order
    const listeners: Record<string, Array<() => void>> = {};
    const doc = {
      visibilityState: "visible",
      addEventListener(t: string, fn: () => void) { (listeners[t] ||= []).push(fn); },
      fire(t: string) { for (const fn of listeners[t] || []) fn(); },
    };
    fm.watchLifecycle(doc);
    assert.equal((listeners.resume || []).length, 1, "one resume listener");
    assert.equal((listeners.visibilitychange || []).length, 1, "one visibilitychange listener");
    fm.openRemote("TESTHOST", true);
    const ws = FakeWS.made[0];
    ws.open();
    clock += 45_000;
    doc.fire("resume");                                   // Chromium's thaw order: resume, then visibilitychange
    doc.fire("visibilitychange");
    assert.equal(ws.closed, 0, "kept: the resume stamped it before the foreground pass ran");
    assert.equal(FakeWS.made.length, 1);
    clock += 45_000;
    doc.visibilityState = "hidden";
    doc.fire("visibilitychange");
    assert.equal(ws.closed, 0, "going HIDDEN is not a foreground pass");
    doc.visibilityState = "visible";
    doc.fire("visibilitychange");                         // no resume this time: real silence
    assert.equal(ws.closed, 1, "abandoned on foreground, exactly today's behaviour");
    assert.equal(FakeWS.made.length, 2);
    fm.conns.get("TESTHOST").closed = true;
  });
});

// A resumed keep is PROVISIONAL (review find, 2026-09-08): the stamp re-bases the watchdog, it does not vouch
// for the far end. A peer that died without a FIN reaching the browser (a laptop sleep across a network change,
// a tunnel whose local end stays open) leaves the relay socket OPEN at the thaw, so the stamp kept it and the
// host sat absent until the tick crossed REMOTE_STALE_MS, 30 s later. Now the kernel's next frame confirms the
// keep, and until one lands the watchdog runs at REMOTE_PROVISIONAL_MS; a socket already overdue BEFORE the
// freeze is not stamped at all, its gap is real and the foreground pass redials it as it did before the stamp.
test("a resumed keep is provisional: silence after the thaw is put down at REMOTE_PROVISIONAL_MS, a frame confirms it to the full bound", async () => {
  await withManager((fm, _e, diag) => {
    const listeners: Record<string, Array<() => void>> = {};
    const doc = {
      visibilityState: "visible",
      addEventListener(t: string, fn: () => void) { (listeners[t] ||= []).push(fn); },
      fire(t: string) { for (const fn of listeners[t] || []) fn(); },
    };
    fm.watchLifecycle(doc);
    fm.openRemote("TESTHOST", true);
    fm.openRemote("HOSTB", true);
    const [a, b] = FakeWS.made;
    a.open(); b.open();
    clock += 1000;
    doc.fire("freeze");
    clock += 45_000;
    doc.fire("resume");                                   // Chromium's thaw order: resume, then visibilitychange
    doc.fire("visibilitychange");
    const stamp = clock;
    assert.equal(a.closed, 0, "the thaw itself keeps both sockets: the healthy case pays nothing");
    assert.equal(b.closed, 0);
    assert.equal(fm.conns.get("TESTHOST").resumeProvisional, stamp, "the keep records the stamp it rests on");
    clock += 2000;
    b.frame({ type: "ka", dv: 1 });                       // HOSTB's kernel speaks: its keep is confirmed, a keepalive is enough
    assert.equal(fm.conns.get("HOSTB").resumeProvisional, 0);
    assert.equal(fm.conns.get("TESTHOST").resumeProvisional, stamp, "TESTHOST's is still waiting on a frame");
    clock += 10_000;                                      // 12 s since the stamp
    fm.watchdog(clock);
    assert.equal(a.closed, 0, "inside the provisional bound the socket stands");
    clock += 3001;                                        // 15.001 s since the stamp, no beat from that kernel
    fm.watchdog(clock);
    assert.equal(a.closed, 1, "put down at the provisional bound, not at 30 s: the kept socket was dead all along");
    assert.equal(b.closed, 0, "the confirmed socket stands");
    assert.equal(FakeWS.made.length, 3, "…and TESTHOST is redialed at once");
    const crumb = diag.find((d) => d.what === "hostconn" && d.data && d.data.ev === "watchdog-close");
    assert.equal(crumb.data.host, "TESTHOST");
    assert.equal(crumb.data.why, "quiet");
    assert.equal(crumb.data.quietMs, 15_001, "silence measured from the stamp");
    assert.equal(fm.conns.get("TESTHOST").resumeProvisional, 0, "the fresh socket starts unmarked: the rule was the resumed socket's");
    clock += 15_999;                                      // 29 s since HOSTB's confirming frame
    fm.watchdog(clock);
    assert.equal(b.closed, 0, "confirmed: the shorter bound no longer applies");
    clock += 1001;                                        // 30.001 s since that frame
    fm.watchdog(clock);
    assert.equal(b.closed, 1, "real silence after the confirmation is still put down at REMOTE_STALE_MS");
    for (const h of ["TESTHOST", "HOSTB"]) fm.conns.get(h).closed = true;
  });
});

test("a socket already overdue before the freeze is not stamped by `resume`: the foreground pass redials it at once", async () => {
  await withManager((fm, _e, diag) => {
    const listeners: Record<string, Array<() => void>> = {};
    const doc = {
      visibilityState: "visible",
      addEventListener(t: string, fn: () => void) { (listeners[t] ||= []).push(fn); },
      fire(t: string) { for (const fn of listeners[t] || []) fn(); },
    };
    fm.watchLifecycle(doc);
    fm.openRemote("TESTHOST", true);
    const ws = FakeWS.made[0];
    ws.open();
    const opened = clock;
    clock += 31_000;                                      // silent past REMOTE_STALE_MS while JS still ran: that gap is real
    doc.fire("freeze");
    clock += 45_000;
    doc.fire("resume");
    assert.equal(fm.conns.get("TESTHOST").lastRecv, opened, "not stamped: the resume vouches for nothing here");
    assert.equal(fm.conns.get("TESTHOST").resumeProvisional, 0);
    doc.fire("visibilitychange");
    assert.equal(ws.closed, 1, "abandoned on foreground, exactly as before the stamp existed");
    assert.equal(FakeWS.made.length, 2, "…and a fresh socket dialed in the same pass");
    const crumb = diag.find((d) => d.data && d.data.ev === "watchdog-close");
    assert.equal(crumb.data.quietMs, 76_000);
    fm.conns.get("TESTHOST").closed = true;
  });
});

test("source pin: start() installs the lifecycle listeners through watchLifecycle(document), guarded for a document-less host", () => {
  const src = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "federation.ts"), "utf8");
  const start = src.slice(src.indexOf("  start(): void {"), src.indexOf("  watchLifecycle("));
  assert.ok(start.length > 0, "start() precedes watchLifecycle()");
  assert.match(start, /try \{\s*this\.watchLifecycle\(document\);\s*\} catch/, "installed once, inside the no-document guard");
  assert.ok(!/document\.addEventListener/.test(start), "no second, un-testable listener install in start()");
  assert.match(start, /this\.watchLocalLink\(w\);/, "the romp:wsup listener is installed the same way (2026-09-18), so the fake-window test above covers the real wiring");
  assert.ok(!/addEventListener\("romp:wsup"/.test(start), "…and not a second time inline");
});

// ── the pending-host signal: what the panes and the shell read while a host is still coming ────
test("mergeHostTimelines names attached hosts that have no lanes payload yet, and which of those sit on a dead link", () => {
  const local = { sessions: [{ id: U, name: "web" }], turns: {}, messages: [], judging: [], now: 1000 };
  const before = mergeHostTimelines({ "": local }, ["", "TESTHOST"], [], []);
  assert.deepEqual(before.pendingHosts, ["TESTHOST"], "listed by /tunnels, no lanes yet — the placeholder window");
  assert.deepEqual(before.pendingDead, []);
  const dead = mergeHostTimelines({ "": local }, ["", "TESTHOST"], [], ["TESTHOST"]);
  assert.deepEqual(dead.pendingDead, ["TESTHOST"], "pending on a closed socket = named as reconnecting");
  const after = mergeHostTimelines({ "": local, TESTHOST: { sessions: [], turns: {}, now: 1000 } }, ["", "TESTHOST"], [], []);
  assert.deepEqual(after.pendingHosts, [], "the first lanes payload — even an EMPTY one — is the retire event");
  assert.deepEqual(mergeHostTimelines({ "": local }, [""]).pendingHosts, [], "the local kernel never pends");
});

test("the merged lanes emission carries the pending set, so the timeline can draw its placeholder rows", async () => {
  await withManager((fm, emitted) => {
    fm.app = "timeline";
    fm.openRemote("TESTHOST", true);
    fm.inbound("", { type: "data", data: { sessions: [{ id: U, name: "web" }], turns: {}, messages: [], judging: [], now: 1000 } });
    const lanes = emitted.filter((m) => m.type === "data").pop();
    assert.deepEqual(lanes.data.pendingHosts, ["TESTHOST"]);
    assert.deepEqual(lanes.data.pendingDead, [], "the socket is dialed (CONNECTING), not dead");
    fm.inbound("TESTHOST", { type: "data", data: { sessions: [], turns: {}, messages: [], judging: [], now: 1000 } });
    const after = emitted.filter((m) => m.type === "data").pop();
    assert.deepEqual(after.data.pendingHosts, [], "retired by that host's own first lanes payload");
    fm.conns.get("TESTHOST").closed = true;
  });
});

test("each pane tells the shell which hosts IT still waits on — by its own channel, on change only", async () => {
  await withManager((fm, _e, _d, posted) => {
    fm.app = "feed";
    fm.openRemote("TESTHOST", true);
    fm.inbound("", localFeed);
    assert.deepEqual(posted.pop(), { romp: "hostsPending", app: "feed", hosts: ["TESTHOST"] },
      "the feed pane pends TESTHOST until its feed payload lands");
    fm.inbound("", { ...localFeed, buildId: 2 });
    assert.equal(posted.length, 0, "unchanged set → nothing re-posted");
    fm.inbound("TESTHOST", { type: "feed", asks: [], items: [], working: [], order: [], sessions: [], now: 1000 });
    assert.deepEqual(posted.pop(), { romp: "hostsPending", app: "feed", hosts: [] }, "the payload retires it");
    fm.closeRemote("TESTHOST");
  });
  await withManager((fm, _e, _d, posted) => {
    fm.app = "timeline";
    fm.openRemote("TESTHOST", true);
    fm.inbound("", { type: "data", data: { sessions: [], turns: {}, messages: [], judging: [], now: 1000 } });
    assert.deepEqual(posted.pop(), { romp: "hostsPending", app: "timeline", hosts: ["TESTHOST"] },
      "the timeline pends on the LANES channel, not the feed");
    fm.inbound("TESTHOST", localFeed);   // a feed payload from that host means nothing to the timeline pane
    assert.equal(posted.length, 0, "still pending: no lanes from it yet");
    fm.conns.get("TESTHOST").closed = true;
  });
});

test("a host that ATTACHES is pending from that moment: the poll re-emits the merged payloads it can complete", async () => {
  const g: any = globalThis;
  const hadFetch = "fetch" in g, prevFetch = g.fetch;
  g.fetch = async () => ({ ok: true, json: async () => ({ tunnels: [{ host: "TESTHOST", hasToken: true, localPort: 5, status: "up" }] }) });
  try {
    await withManager(async (fm, emitted) => {
      fm.app = "feed";
      fm.inbound("", localFeed);
      const n = emitted.length;
      await fm.poll();
      const feed = emitted.slice(n).filter((m) => m.type === "feed").pop();
      assert.ok(feed, "the attach itself re-emitted the merged feed");
      assert.deepEqual(feed.pendingHosts, ["TESTHOST"], "…already naming the host as coming");
      fm.conns.get("TESTHOST").closed = true;
    });
  } finally {
    if (hadFetch) g.fetch = prevFetch; else delete g.fetch;
  }
});

test("the kernel's recovery counter bumping while a row reads up is a hostUp: one per bump, none on a first observation or a steady poll (T291b)", async () => {
  const g: any = globalThis;
  const hadFetch = "fetch" in g, prevFetch = g.fetch;
  let seq = 4;
  g.fetch = async () => ({ ok: true, json: async () => ({ tunnels: [{ host: "TESTHOST", hasToken: true, localPort: 5, status: "up", upSeq: seq }] }) });
  try {
    await withManager(async (fm, emitted) => {
      fm.app = "feed";
      const hostUps = () => emitted.filter((m) => m && m.type === "hostUp");
      await fm.poll();                                  // first observation: the counter is recorded, never fired
      assert.equal(hostUps().length, 0, "a first observation is not a recovery");
      await fm.poll();                                  // steady: same counter, same status
      assert.equal(hostUps().length, 0, "a steady answered row fires nothing");
      seq = 5;                                          // the kernel noted a miss-then-answer while the row stayed up
      await fm.poll();
      assert.deepEqual(hostUps().map((m) => m.hosts), [["TESTHOST"]], "one hostUp for the bump, the status never having left up");
      await fm.poll();
      assert.equal(hostUps().length, 1, "…and none for the same counter again");
      fm.conns.get("TESTHOST").closed = true;
    });
  } finally {
    if (hadFetch) g.fetch = prevFetch; else delete g.fetch;
  }
});

test("…but never drops an EMPTY merged feed onto a page still waiting for its local kernel", async () => {
  const g: any = globalThis;
  const hadFetch = "fetch" in g, prevFetch = g.fetch;
  g.fetch = async () => ({ ok: true, json: async () => ({ tunnels: [{ host: "TESTHOST", hasToken: true, localPort: 5, status: "up" }] }) });
  try {
    await withManager(async (fm, emitted) => {
      fm.app = "feed";
      await fm.poll();
      assert.equal(emitted.filter((m) => m.type === "feed").length, 0, "no local feed yet → the feed hold stands (the loader stays up)");
      fm.conns.get("TESTHOST").closed = true;
    });
  } finally {
    if (hadFetch) g.fetch = prevFetch; else delete g.fetch;
  }
});

test("a page that renders no pushed channel pends nothing and tells the shell nothing: settings and files (2026-09-18)", async () => {
  // the /settings page and the file browser load this module (the gear's fan-out, the host routing) but receive no pushed
  // view, so no frame of theirs could retire a host: the settings frame's manager posted every attached host as pending
  // for good and the network panel read every connected remote as "loading sessions…" from the first gear open
  for (const app of ["settings", "files"]) {
    await withManager((fm, _e, _d, posted) => {
      fm.app = app;
      fm.openRemote("TESTHOST", true);
      assert.deepEqual(fm.pendingFor(), [], app + ": no channel to be heard on, nothing pending");
      fm.inbound("", localFeed);
      fm.inbound("", { type: "data", data: { sessions: [], turns: {}, messages: [], judging: [], now: 1000 } });
      assert.equal(posted.filter((m) => m && m.romp === "hostsPending").length, 0, app + ": never posts hostsPending");
      fm.conns.get("TESTHOST").closed = true;
    });
  }
});

test("the WAITING pane renders the feed payload too, so it pends its attached host, tells the shell, and is retired by that host's feed payload (fork pin, review round 1, 2026-09-21)", async () => {
  // the fork's fifth pushed-channel pane: the kernel pushes the feed payload to the feed pane, the Outline AND the
  // Waiting-on-you pane (kernel.py _push's feed branch; waiting.ts reads feed.userTodoRows). The project's
  // PANE_CHANNELS named its own four panes, and this pane dropped out of the shell's pending signal: its merged feed still
  // carried pendingHosts (the pane's own loading line) while the network panel heard nothing from it.
  await withManager((fm, _e, _d, posted) => {
    const hp = () => posted.filter((m) => m && m.romp === "hostsPending");
    fm.app = "waiting";
    fm.openRemote("TESTHOST", true);
    assert.deepEqual(fm.pendingFor(), ["TESTHOST"], "attached and dialed, no feed payload from it yet");
    fm.inbound("", localFeed);
    assert.deepEqual(hp().pop(), { romp: "hostsPending", app: "waiting", hosts: ["TESTHOST"] },
      "the waiting pane pends TESTHOST until its feed payload lands, and says so to the shell");
    fm.inbound("", { ...localFeed, buildId: 2 });
    assert.equal(hp().length, 1, "unchanged set: nothing re-posted");
    fm.inbound("TESTHOST", { type: "feed", asks: [], items: [], working: [], order: [], sessions: [], now: 1000 });
    assert.deepEqual(fm.pendingFor(), [], "its first feed payload retires it");
    assert.deepEqual(hp().pop(), { romp: "hostsPending", app: "waiting", hosts: [] }, "and the follow-up post clears the host in the shell");
    assert.equal(hp().length, 2, "exactly the pend and the retire");
    fm.closeRemote("TESTHOST");
  });
});

// ── the pushed-channel roster, derived from the kernel's send loop (review rounds 1 to 3, 2026-09-21) ────────────────
// Enough of Python's surface to read _push's body as statements: comments dropped, a backslash continuation joined, a
// newline inside brackets folded to one space (a wrapped tuple reads as one line), every other newline kept. Per output
// character: whether it sits inside a string literal (an f-string field, a docstring's prose), the output index of its
// innermost open bracket (a % format's operand tuple), and its source line for the failure messages.
function pyNormalise(src: string, firstLine: number): { text: string; inStr: boolean[]; encl: number[]; line: number[] } {
  const out: string[] = [], inStr: boolean[] = [], encl: number[] = [], line: number[] = [];
  const stack: number[] = [];
  let ln = firstLine;
  const emit = (ch: string, s: boolean) => { out.push(ch); inStr.push(s); encl.push(stack.length ? stack[stack.length - 1] : -1); line.push(ln); };
  const n = src.length;
  let i = 0;
  while (i < n) {
    const ch = src[i];
    const pm = /^([rRbBuUfF]{0,2})("""|'''|"|')/.exec(src.slice(i, i + 5));   // a string literal, with any prefix letters
    if (pm && (pm[1] === "" || i === 0 || !/[A-Za-z0-9_]/.test(src[i - 1]))) {
      for (const p of pm[1]) emit(p, false);
      i += pm[1].length;
      const q = pm[2];
      for (const qc of q) emit(qc, true);
      i += q.length;
      while (i < n) {
        if (src[i] === "\\" && i + 1 < n) {                 // an escape: the next character is the string's, whatever it is
          if (src[i + 1] === "\n") ln++;
          emit(src[i], true); emit(src[i + 1], true); i += 2; continue;
        }
        if (src.startsWith(q, i)) { for (const qc of q) emit(qc, true); i += q.length; break; }
        if (src[i] === "\n") ln++;
        emit(src[i], true); i++;
      }
      continue;
    }
    if (ch === "#") { while (i < n && src[i] !== "\n") i++; continue; }                        // a comment, to its line's end
    if (ch === "\\" && src[i + 1] === "\n") {                                                // a continuation: one line
      i += 2; ln++;
      while (i < n && (src[i] === " " || src[i] === "\t")) i++;
      emit(" ", false); continue;
    }
    if (ch === "\n") {
      ln++; i++;
      if (stack.length) { while (i < n && (src[i] === " " || src[i] === "\t")) i++; emit(" ", false); continue; }   // wrapped
      emit("\n", false); continue;
    }
    if (ch === "(" || ch === "[" || ch === "{") { emit(ch, false); stack.push(out.length - 1); i++; continue; }
    if (ch === ")" || ch === "]" || ch === "}") { stack.pop(); emit(ch, false); i++; continue; }
    emit(ch, false); i++;
  }
  return { text: out.join(""), inStr, encl, line };
}

// The forms a read of the "app" key in _push's body can take. Two the census READS as an audience; one it can rule out as
// no audience at all (the value becomes text: the send log line's `%` operand); every other form it cannot see through, so
// each is NAMED, counted over the body and asserted absent, the way tests/test_card_boards.py's _other_card_forms
// enumerates what its card census cannot read (review round 3, 2026-09-21: both refuters defeated a wider regex with a
// named constant, `c["app"] in NOTE_APPS`, which no pattern over literals can read; the enumeration turns it red instead of
// invisible). Keyed on the KEY written as a string literal, however spaced or wrapped (a subscript or a .get with any
// whitespace around the literal and around the call's dot, name and paren; a subscript wrapped over a line, which
// pyNormalise folds to the spaced form), so a renamed loop variable is still read. A key that is NOT a literal is keyed
// on the shape of its read, never on its spelling (review round 6, 2026-09-21): a subscript or a .get whose key is a
// bare name (`c[APP_KEY]`, `c.get(key)`) is the ninth named form, NAME_KEY_FORM, listed with its statement and asserted
// absent whatever the name (every key _push reads at the head is written as a literal, so the form has nothing to fire
// on until a key is held in a name; the bracket arm needs a receiver before the bracket, whatever can end a primary
// in Python's grammar, so a one-element list display is not listed and a generic annotation such as `list[str]` is,
// review rounds 7 and 8, the bound stated at the arm); and every "app" literal in the body
// that no detector read (bound to a name in any shape, a default, a keyword argument, a passed value) is listed under
// UNREAD_LITERAL and asserted absent, so the road from inside the body to a key held in a name is red at both ends, the
// literal and the read. What stays disclosed, not detected: a key held in a dict or a list, reached through an attribute
// or returned by a call (`c[KEYS[0]]`, `c[self.key]`, `c[pick()]`), whose value the body never spells as a literal.
const READ_TUPLE = "a tuple of string literals (the audience, read)";
const READ_SINGLE = "a singleton, == a string literal (the audience, read)";
const READ_TEXT = "a value formatted into text (a % format's operand, a .format argument, a field inside a string literal): no audience";
const OTHER_FORMS = [
  "a membership test against a name, an attribute or a call (a named constant, a variable)",
  "a membership test against a list or a set literal",
  "a tuple with a member that is not a string literal",
  "a negated test (!= or not in)",
  "an equality test against something other than a string literal",
  "a .get(\"app\", ...) with a default",
  "the read bound to a name (an assignment or a walrus)",
  "a read in any other position (a call's argument, a returned value, a comparison's right operand, a yield): not followed",
] as const;
// The ninth named form, keyed on the SHAPE of the read rather than on the key: a subscript or a .get whose key is a bare
// name. Listed whatever the name (the census cannot tell it from a read of the app key) and asserted absent.
const NAME_KEY_FORM = "a subscript or a .get whose key is a bare name (a constant, a variable, a parameter; a generic annotation such as list[str] shares the bracket): which key it reads is not known here";
// Python's keywords (3.12's keyword.kwlist) and the two soft keywords that precede a bracket in their keyword role
// (keyword.softkwlist's match and case: `match [c]:` a subject, `case [c]:` a sequence pattern): a bracket directly behind
// one of these as a STANDALONE token is a list display or a pattern and is not listed; after a dot, spaced or tight,
// match and case alone are identifiers (`self.match[k]`), read by the arm below, since of this set only those two can
// follow an attribute's dot (a hard keyword after a dot, as in `1. in [k]`, is still the keyword; review round 9,
// 2026-09-24). The other two soft keywords, _ and type, are
// not here: neither ever precedes a bracket in its keyword role (a type alias is `type Name = ...`, a wildcard pattern
// `_` stands alone), so `type[int]` and `_[k]` are subscripts and are listed. The residual, disclosed here, in
// federation.ts's PANE_CHANNELS comment and in the ledger entry: a bare variable named match or case, subscripted
// (`match[k]`), reads as the keyword and is not listed (review round 7, 2026-09-23; round 8, the set derived from where a
// keyword-role bracket can stand, not from the soft-keyword list).
const PY_KEYWORDS = new Set([
  "False", "None", "True", "and", "as", "assert", "async", "await", "break", "class", "continue", "def", "del", "elif",
  "else", "except", "finally", "for", "from", "global", "if", "import", "in", "is", "lambda", "nonlocal", "not", "or",
  "pass", "raise", "return", "try", "while", "with", "yield",
  "case", "match",
]);
// The one label for every "app" literal in the body that none of the detectors read, whatever holds it.
const UNREAD_LITERAL = "the app literal in a position the census does not read (bound to a name in any shape, a default, a keyword argument, a passed value)";
type Audiences = { tuples: string[][]; singles: string[]; text: string[]; other: Map<string, string[]>; reads: number; unread: string[]; byName: string[] };
function pushAudiences(kernel: string): Audiences {
  const at = kernel.indexOf("\ndef _push(targets");
  assert.ok(at >= 0, "kernel.py's _push(targets, ...) is the pusher's send loop");
  const body = kernel.slice(at + 1, kernel.indexOf("\ndef ", at + 1));   // _push's own body, up to the next top-level def
  const { text, inStr, encl, line } = pyNormalise(body, kernel.slice(0, at + 1).split("\n").length);
  const a: Audiences = { tuples: [], singles: [], text: [], other: new Map(OTHER_FORMS.map((f) => [f, []])), reads: 0, unread: [], byName: [] };
  const lit = /(["'])([^"'\\]*)\1/g;
  const whereAt = (p: number) => {   // kernel.py:line and the statement, for the failure messages
    const ls = text.lastIndexOf("\n", p) + 1;
    const le = text.indexOf("\n", p);
    return "kernel.py:" + line[p] + " " + text.slice(ls, le < 0 ? text.length : le).trim().slice(0, 120);
  };
  const consumed = new Set<number>();   // the positions of the "app" literals the detectors below read: the key, a tuple's members, a singleton's operand
  for (const m of text.matchAll(/\[\s*(["'])app\1\s*\]|\.\s*get\s*\(\s*(["'])app\2/g)) {   // the KEY as a literal, however spaced (a wrapped subscript is one space here; any whitespace around a .get's dot, name and paren)
    const p = m.index!;
    let e = p + m[0].length;
    a.reads++;
    consumed.add(p + m[0].indexOf(m[1] ?? m[2]));
    const ls = text.lastIndexOf("\n", p) + 1;
    const where = whereAt(p);
    const other = (form: string) => a.other.get(form)!.push(where);
    if (inStr[p]) { a.text.push(where); continue; }
    if (m[2]) {                                            // `.get("app"`: closed at once, or a default follows
      const tail = /^\s*\)/.exec(text.slice(e));
      if (!tail) { other(OTHER_FORMS[5]); continue; }
      e += tail[0].length;
    }
    const after = text.slice(e);
    let mm: RegExpExecArray | null;
    if ((mm = /^\s*==\s*(["'])([^"'\\]+)\1/.exec(after))) { consumed.add(e + mm[0].indexOf(mm[1])); a.singles.push(mm[2]); continue; }   // the compared value is read
    if (/^\s*==/.test(after)) { other(OTHER_FORMS[4]); continue; }
    if (/^\s*!=/.test(after) || /^\s+not\s+in\b/.test(after)) { other(OTHER_FORMS[3]); continue; }
    if ((mm = /^\s+in\s*\(/.exec(after))) {                  // zero or more spaces after the keyword (review round 6)
      const q = e + mm[0].length - 1;                      // the tuple's "(": its members run to the matching ")"
      let d = 0, r = q;
      for (; r < text.length; r++) {
        if (inStr[r]) continue;
        if (text[r] === "(") d++;
        else if (text[r] === ")" && --d === 0) break;
      }
      const inner = text.slice(q + 1, r);
      const lits = [...inner.matchAll(lit)];
      for (const l of lits) consumed.add(q + 1 + l.index!);   // the members are read, into the roster or to refuse the tuple
      const members = lits.map((l) => l[2]);
      if (members.length >= 1 && inner.replace(lit, "").replace(/[\s,]/g, "") === "") { a.tuples.push(members); continue; }
      other(OTHER_FORMS[2]); continue;
    }
    if (/^\s+in\s*[\[{]/.test(after)) { other(OTHER_FORMS[1]); continue; }   // zero or more spaces after the keyword (review round 6)
    if (/^\s+in\b/.test(after)) { other(OTHER_FORMS[0]); continue; }
    if (/(?:^|[\s,(])[A-Za-z_]\w*\s*(?::\s*[\w\[\], ]+)?\s*:?=\s*[A-Za-z_][\w.]*(?:\[[^\]]*\])*\s*$/.test(text.slice(ls, p))) { other(OTHER_FORMS[6]); continue; }   // `name = <receiver>` before the key (any whitespace before a .get's dot)
    const enc = encl[p];
    if (enc >= 0 && text[enc] === "(" && /(?:(["'])\s*%|\.format)\s*$/.test(text.slice(0, enc))) { a.text.push(where); continue; }
    other(OTHER_FORMS[7]);
  }
  // Every "app" literal in the body that none of the detectors above read (the key, a tuple's members, a singleton's
  // compared value), listed under one label whatever holds it: a binding of any shape (an assignment, a tuple unpacking,
  // an annotated one however the annotation is spelled, a walrus, a for target, a parameter default), a keyword argument,
  // a passed value, a parenthesised or a call-wrapped literal. Keyed on the PROPERTY (a literal the census did not read),
  // not on a binding's spelling (review round 6, 2026-09-21: a scan keyed on four binding spellings missed a tuple
  // unpacking, a parenthesised literal, an unspaced union annotation and a string annotation, and listed a keyword
  // argument as a bound name), so the road from inside the body to a key held in a name starts red at the literal,
  // whatever binds it. A literal inside a string (a docstring's prose) is skipped: its opening quote follows a character
  // inside the string, where a literal of its own follows code (or a prefix letter, which pyNormalise emits as code).
  for (const m of text.matchAll(/(["'])app\1/g)) {
    const p = m.index!;
    if (consumed.has(p) || (p > 0 && inStr[p - 1])) continue;
    a.unread.push(whereAt(p));
  }
  // The ninth named form, keyed on the SHAPE of the read: a subscript or a .get whose key is a bare name, outside a
  // string, whatever the name (a constant, a variable, a parameter). Which key it reads is not known here, so it is
  // listed and asserted absent (every key _push reads at the head is written as a literal, so the form has nothing to
  // fire on until a key is held in a name) rather than disclosed. Tolerates the whitespace the literal read tolerates.
  // The bracket arm is a subscript only behind a receiver primary directly before the bracket, joined by spaces or tabs
  // only: whatever can end a subscriptable primary in Python's grammar, a name, a closing parenthesis, a closing bracket,
  // a closing brace (a dict or set display, a comprehension) or a closing quote, double or single (a string literal); the
  // statement's text before the bracket is read from its line start, and pyNormalise folds a newline inside brackets to
  // one space, so a newline never lets one statement's tail become the next bare bracket's receiver. The derived set,
  // in the same words here, in federation.ts's PANE_CHANNELS comment and in the ledger entry: a name is a whole
  // identifier token, ASCII or not; a number of any spelling, an Ellipsis or a keyword constant (None, True, False)
  // before a bracket is unlisted; a name after a dot is an identifier only where Python allows one there (match and
  // case). So the name alternative's characters are an identifier's, \w or any code unit past ASCII (outside a string or
  // a comment, valid Python holds one only in an identifier), and it starts only where a name can start: never behind an
  // identifier character, so `1j[k]`, `0x1f[k]`, `0xff[k]` and `1e5[k]` are not listed through their tails and a
  // name with a character past ASCII is listed whole, and never directly behind a number's trailing dot (a digit run
  // that starts a token, then the dot), so `1.e5[k]` and `1_0.j[k]`, one number token each, are not listed either, while
  // `v5.e5[k]` and `1.5.e5[k]`, attributes, are. Both lookbehinds sit inside the name alternative alone, so a closing
  // parenthesis still ends `f(x)[k]`'s receiver. A name in PY_KEYWORDS is no receiver as a STANDALONE token only
  // (`case [k]:`, `in [k]`, `return [c]`), and of that set only match and case can follow an attribute's dot: for those
  // two alone the text before the name is read for a dot followed by spaces or tabs, so after a dot, tight or spaced
  // (`self.match[k]`, `c . case[k]`), the spelling is an identifier and its bracket a subscript, listed, while a hard
  // keyword after a dot (`1. in [k]` behind a float's trailing dot, `... in [k]` behind an Ellipsis) is the keyword and
  // its bracket a list display. So a one-element list display (`xs = [c]`, `return [c]`, `f([c], 1)`) and a sequence
  // pattern are not listed, and a generic annotation such as `list[str]`, `pick(c)[k]`, `targets[0][k]`, `{**c}[k]`,
  // `"abc"[k]` and `'abc'[k]` are: subscripts with a bare-name key, whose remedy is not the literal (review round 7,
  // 2026-09-23: the arm listed every one-name bracket, so a list display in the body turned the census red with a cause
  // and a remedy that did not apply; round 8: the receiver class derived from the grammar after a name-paren-bracket
  // class fitted to the examples left a dict display and a string literal unlisted; round 9, 2026-09-24: the name
  // alternative matched a run of ASCII characters, so a number was listed through its letter tail and a name with a
  // character past ASCII was not, and the dot test read any dot before a keyword as an attribute's). Deliberately
  // unlisted, and disclosed in the same three homes: a number, an Ellipsis or a keyword constant before a bracket, a
  // subscript in the grammar that no client record can stand behind, and a bare variable named match or case,
  // subscripted, which reads as the keyword (PY_KEYWORDS).
  for (const m of text.matchAll(/\[\s*[A-Za-z_]\w*\s*\]|\.\s*get\s*\(\s*[A-Za-z_]\w*\s*[,)]/g)) {
    const p = m.index!;
    if (inStr[p]) continue;
    if (m[0].endsWith("]")) {   // the bracket arm: the receiver, if any, ends the statement's text before the bracket
      const before = text.slice(text.lastIndexOf("\n", p) + 1, p);
      const rcv = /((?<![\w\u0080-\uFFFF])(?<!(?<![\w\u0080-\uFFFF.])\d[\d_]*\.)[A-Za-z_\u0080-\uFFFF][\w\u0080-\uFFFF]*|[)\]}"'])[ \t]*$/.exec(before);
      if (!rcv || (PY_KEYWORDS.has(rcv[1]) && !((rcv[1] === "match" || rcv[1] === "case") && /\.[ \t]*$/.test(before.slice(0, rcv.index))))) continue;   // no receiver (a list display, a number), or a standalone keyword before the bracket (after a dot, match and case alone are identifiers)
    }
    a.byName.push(whereAt(p));
  }
  return a;
}

test("every app the kernel's _push addresses is a pushed-channel pane here, on the channel its audience names: the roster is derived from every read of the app key written as a string literal in _push's body, however spaced or wrapped (a tuple of string literals however wrapped or spaced, a singleton of any name, or a value formatted into text), every other form is named and asserted absent, a subscript or a .get whose key is a bare name is named and asserted absent, and every app literal the census did not read is listed and asserted absent, so a pane added to any of _push's audiences in any spelling of the key as a literal reads red here, in the roster or as a named form, a key held in a name reads red at the name or at the literal a name would be bound to, a key held in a dict or reached through an attribute is disclosed as outside, and a member _push never addresses reads red (review rounds 1 to 6, 2026-09-21)", async () => {
  // Keyed on the PRODUCER, not on the compliant sites: a set that names the panes it knows cannot see the one it misses,
  // and the project's four-name set missed this fork's fifth. Round 1 read the first `if c["app"] in (...):` alone, the
  // feed branch, so a pane added to the timeline's or the chat's audience (a `==` widened to a tuple) took no verdict.
  // Round 2 matched every one-line tuple and singleton of lowercase names, so a pane added in a wrapped tuple, under a
  // name with a hyphen or a digit, or through a named constant took no verdict either. The belt (pushAudiences above):
  // every read of the "app" key in _push's body is accounted for, as a tuple of string literals (the body normalised
  // first: comments dropped, continuations joined, a newline inside brackets folded, the separator a comma plus any
  // whitespace), a singleton of any name, or a value formatted into text (the send log line, no audience), and every
  // other form is NAMED and counted (OTHER_FORMS): the premise is asserted here as an empty set, and each detector is
  // shown to fire in the case below. A tuple's channel is the one of feed, chat, timeline it names, a singleton's its own
  // name, and each member is driven through the manager on that channel with the other two channels' frames refused, so
  // a non-feed member cannot fall silently to perHostFeed in pendingFor's selector (federation.ts), where every app that
  // is not the timeline or the chat reads the feed.
  // The harm of a missed pane, as the round 3 refuters measured it: NOT every attached host pending forever. pendingFor
  // returns [] for an app outside PANE_CHANNELS, so the pane posts no hostsPending at all: the shell loses its
  // "connected, loading sessions" caveat for that pane while the pane's own loading line still shows (the 2026-09-18
  // waiting-pane dropout). The forever-pending direction is the other miss, a set member _push never addresses, which the
  // second roster assertion below catches.
  // SCOPE: this census reads _push's body, the pusher's send loop. Senders outside it test the app key on their own
  // (_feed_first's cold first feed frame, _send_feed_now's ready-time frame, the tab strips of _push_session_now and
  // _confirm_close_now), each addressing a pane _push also addresses; none is read here, so a pane pushed ONLY by a route
  // outside _push's body is outside this case's claim. And the key is read as a STRING LITERAL, however spaced or wrapped;
  // a key held in a name is caught by the shape of its read, at both ends (review round 6, 2026-09-21): a subscript or a
  // .get whose key is a bare name (c[APP_KEY], c.get(key)) is listed whatever the name, and so is every "app" literal in
  // the body the census did not read (the literal a name would be bound to, in any binding's spelling); both are asserted
  // absent here. What stays disclosed, not detected: a key held in a dict or a list, reached through an attribute or
  // returned by a call (c[KEYS[0]], c[self.key]), whose value the body never spells as a literal.
  const kernel = fs.readFileSync(path.resolve(process.cwd(), "..", "kernel", "kernel.py"), "utf8");
  const { tuples, singles, other, unread, byName } = pushAudiences(kernel);
  assert.deepEqual([...other].filter(([, hits]) => hits.length), [],
    "a read of the app key in _push's body the census cannot read, as [form, [kernel.py:line statement]]: write the audience as a tuple of string literals or a singleton, or teach pushAudiences the form and say what it reads");
  assert.deepEqual(byName, [],
    NAME_KEY_FORM + ", in _push's body, as kernel.py:line statement: the census cannot tell it from a read of the app key, so write the key as a string literal, or teach pushAudiences what the name holds");
  assert.deepEqual(unread, [],
    UNREAD_LITERAL + ", in _push's body, as kernel.py:line statement: a name bound to it carries the key past every detector here, so read the key as a literal where it is used, or say in the SCOPE note what the literal is for");
  assert.ok(tuples.length >= 1, "the send loop's `c[\"app\"] in (...)` feed branch is an audience");
  const union = new Set<string>([...tuples.flat(), ...singles]);
  assert.ok(union.has("feed") && union.has("waiting"), "the feed audience carries the feed pane and this fork's Waiting-on-you pane (" + [...union].sort().join(", ") + ")");
  assert.deepEqual([...union].filter((a) => !PANE_CHANNELS.has(a)), [],
    "an app _push addresses that PANE_CHANNELS misses: add it there, or, if it renders no pushed view, name it here as excluded with the reason");
  assert.deepEqual([...PANE_CHANNELS].filter((a) => !union.has(a)), [],
    "a PANE_CHANNELS member _push never addresses would pend every attached host forever: drop it, or push to it");
  // each member's channel, from the audience that names it
  const CH = ["feed", "chat", "timeline"];
  const channelOf = new Map<string, string>();
  for (const t of tuples) {
    const named = CH.filter((c) => t.includes(c));
    if (named.length !== 1) continue;   // a tuple naming none or two of the channel apps places nothing: its members are placed by another
    for (const a of t) {
      assert.ok(!channelOf.has(a) || channelOf.get(a) === named[0], a + ": named in the audiences of two channels (" + channelOf.get(a) + ", " + named[0] + ")");
      channelOf.set(a, named[0]);
    }
  }
  for (const a of singles) if (!channelOf.has(a) && CH.includes(a)) channelOf.set(a, a);
  for (const a of union) assert.ok(channelOf.has(a), a + ": no audience names its channel (feed, chat or timeline); place it");
  const frames: Record<string, any> = {
    feed: { type: "feed", asks: [], items: [], working: [], order: [], sessions: [], now: 1000 },
    chat: { type: "tabOrder", order: [], tabs: [] },
    timeline: { type: "data", data: { sessions: [], turns: {}, messages: [], judging: [], now: 1000 } },
  };
  for (const app of [...union].sort()) {
    const ch = channelOf.get(app)!;
    await withManager((fm, _e, _d, posted) => {
      const hp = () => posted.filter((m) => m && m.romp === "hostsPending");
      fm.app = app;
      fm.openRemote("TESTHOST", true);
      assert.deepEqual(fm.pendingFor(), ["TESTHOST"], app + ": pends its attached host");
      if (ch === "feed") {
        fm.inbound("", localFeed);
        assert.deepEqual(hp().pop(), { romp: "hostsPending", app, hosts: ["TESTHOST"] }, app + ": pends its attached host on the feed channel, and says so to the shell");
      }
      for (const other of CH) {
        if (other === ch) continue;
        fm.inbound("TESTHOST", frames[other]);
        assert.deepEqual(fm.pendingFor(), ["TESTHOST"], app + ": the host's " + other + " frame is not its channel and retires nothing");
      }
      fm.inbound("TESTHOST", frames[ch]);
      assert.deepEqual(fm.pendingFor(), [], app + ": retired by the host's " + ch + " frame, its channel");
      if (ch === "feed") assert.deepEqual(hp().pop(), { romp: "hostsPending", app, hosts: [] }, app + ": retired by that host's feed payload, in the shell too");
      fm.closeRemote("TESTHOST");
    });
  }
});

test("the census's premise, shown to hold for a reason: on a planted _push every named form the census cannot read fires exactly where planted, the roster reads the wrapped, unspaced, hyphenated, digit-carrying and continued spellings, a tuple with no space after its in, and the key spaced inside its subscript or its .get call, around the call's dot, name and paren, or wrapped over a line, a formatted value and a docstring's prose read as text, a subscript by a bare name behind each receiver the grammar allows (a name, ASCII or not, a call, a subscript, a dict display, a string literal, double- or single-quoted, an attribute named by a soft keyword with the dot tight or spaced, an attribute after a name ending in a digit or after a float, the builtin type and the variable _) and a generic annotation are listed where planted, and a one-element list display, a sequence pattern behind the soft keyword case, a number of each spelling before a bracket and a list display behind a hard keyword after a float's trailing dot or an Ellipsis are not, no app literal is listed as unread, and every read of the key lands in exactly one form (review rounds 3, 5 and 6, 2026-09-21; rounds 7 and 8, 2026-09-23; round 9, 2026-09-24)", () => {
  // the synthetic body, one read per tagged line: T a tuple the roster reads, S a singleton, X text, a number the
  // OTHER_FORMS index that must fire there, null a line with no read of its own (a wrapped tuple's continuation lines, a
  // one-element list display, a match statement and its sequence pattern, a number before a bracket, a list display
  // behind a hard keyword)
  const T = READ_TUPLE, S = READ_SINGLE, X = READ_TEXT, N = NAME_KEY_FORM;
  const plant: [string, string | number | null][] = [
    ["def _push(targets, connect=False, live_map=None):", null],
    ['    """prose naming c["app"] in NOTE_APPS or c[KEY] is text, not a test or a read by a name"""', X],   // a bare-name subscript inside a string is no ninth form (review round 6)
    ['    if c["app"] in ("feed",   # a wrapped tuple, a comment inside it, a hyphen, a digit, a trailing comma', T],
    ['                    "outline",', null],
    ['                    "waiting-2", "x9",):', null],
    ["        pass", null],
    ['    if c["app"] in ("timeline","notes"):', T],
    ["        pass", null],
    ['    if c["app"] in("chat", "tight"):', T],                    // no space after the keyword (review round 6)
    ["        pass", null],
    ['    ok = any(c["app"] \\', S],
    ['             == "chat" for c in targets)', null],
    ["    tl = [t for t in targets if t.get('app') == 'timeline']", S],
    ["    if c[ 'app' ] in (\"chat\", \"spaced\"):", T],           // the key spaced inside its subscript (review round 5)
    ["        pass", null],
    ['    sp = [t for t in targets if t.get( "app" ) == "feed"]', S],   // the key spaced inside its .get call
    ['    sq = [t for t in targets if t.get ("app") == "chat"]', S],    // the .get call spaced between its name and its paren (review round 6)
    ["    if c[", T],                                              // the key wrapped over a line inside its subscript:
    ['        "app"] in ("timeline", "wrapped"):', null],           // pyNormalise folds the newline to one space
    ["        pass", null],
    ['    sys.stderr.write("push send %s (%s)\\n" % ("feed", c.get("app")))', X],
    ["    log(f\"push {c['app']}\")", X],
    ['    if c["app"] in NOTE_APPS:', 0],
    ["        pass", null],
    ['    if c["app"] in ["feed", "outline"]:', 1],
    ["        pass", null],
    ['    if c["app"] in["feed", "tight"]:', 1],                   // no space after the keyword (review round 6)
    ["        pass", null],
    ['    if c["app"] in ("feed", OUTLINE_APP):', 2],
    ["        pass", null],
    ['    if c["app"] != "chat":', 3],
    ["        pass", null],
    ['    if c["app"] not in ("a", "b"):', 3],
    ["        pass", null],
    ['    if c["app"] == APP:', 4],
    ["        pass", null],
    ['    if c.get("app", "") == "chat":', 5],
    ["        pass", null],
    ['    app = c["app"]', 6],
    ['    if (a := c.get("app")) == "x":', 6],
    ["        pass", null],
    ['    b = c . get("app")', 6],                                 // the read bound to a name, through a .get spaced around its dot (review round 6)
    ['    if c[APP_KEY] in ("feed", "outline"):', N],              // the key held in a name: the ninth form, keyed on the shape (review round 6)
    ["        pass", null],
    ["    seen: list[str] = []", N],                               // a generic annotation shares the bracket: a subscript with a bare-name key, listed (review round 7)
    ["    xs = [c]", null],                                        // a one-element list display: no receiver before its bracket, not listed (review round 7)
    ["    dd = {**c}[APP_KEY]", N],                                // a dict display subscripted: a closing brace is a receiver (review round 8, 2026-09-23)
    ['    ss = "feedchat"[i]', N],                                 // a string literal subscripted: a closing double quote is a receiver (review round 8)
    ["    qs = 'feedchat'[i]", N],                                 // the same single-quoted: a closing single quote is a receiver (red where the class drops the single quote; review round 9, 2026-09-24)
    ["    vv = self.type[APP_KEY]", N],                            // an attribute named by a soft keyword outside PY_KEYWORDS: listed as a name (review round 8)
    ["    ww = self . type[APP_KEY]", N],                          // the same with the dot spaced (review round 8)
    ["    mm = self.match[APP_KEY]", N],                           // an attribute named by a soft keyword IN PY_KEYWORDS: match after a dot is an identifier, the dot read, listed (review round 8)
    ["    cc = c . case[APP_KEY]", N],                             // the same with the dot spaced, the tolerance the .get read has (review round 8)
    ["    tt = type[int]", N],                                     // the builtin type subscripted: type is not in PY_KEYWORDS, it never precedes a keyword-role bracket (review round 8)
    ["    uu = _[k]", N],                                          // the variable _ subscripted: _ is not in PY_KEYWORDS either (review round 8)
    ["    nn = targets[0][APP_KEY]", N],                           // a subscript subscripted: a closing bracket is a receiver, and [0] holds no bare name (review round 8)
    ["    pp = pick(c)[APP_KEY]", N],                              // a call subscripted: a closing parenthesis is a receiver (review round 8)
    ["    n7 = 7[APP_KEY]", null],                                 // a letter-free number before a bracket: no name ends the text, not listed (the control, unlisted before round 9 and after)
    ["    cj = 1j[APP_KEY]", null],                                // an imaginary number: its j is the number's tail, not a name, not listed (red where the name arm matched a run of letters inside a token and listed j; review round 9)
    ["    hx = 0x1f[APP_KEY]", null],                              // a hex number ending in a digit: not listed (red where the name arm listed x1f)
    ["    hf = 0xff[APP_KEY]", null],                              // a hex number ending in a letter: not listed (red where the name arm listed xff)
    ["    ex = 1e5[APP_KEY]", null],                               // an exponent: not listed (red where the name arm listed e5)
    ["    fe = 1.e5[APP_KEY]", null],                              // a float with a bare trailing dot before its exponent, one number token: not listed (red where a name directly after a number's trailing dot was a name, e5 listed)
    ["    fj = 1_0.j[APP_KEY]", null],                             // the same with an underscore-grouped digit run before an imaginary j: not listed (red where j was listed, or where the run before the dot was read as one digit)
    ["    q1 = v5.e5[APP_KEY]", N],                                // an attribute after a name ending in a digit: the digit run is the name's, so no number ends at the dot, listed (red where any digit run before the dot counted as a number)
    ["    r5 = 1.5.e5[APP_KEY]", N],                               // an attribute of a float: the digit run before the dot follows the fraction's dot, so no number ends at this dot, listed (red where a digit run after a dot counted as a number)
    ["    e1 = \u00e95.e5[APP_KEY]", N],                           // the same after a name whose first character is past ASCII and whose last is a digit: listed (red where a digit run after such a character counted as a number)
    ["    cf = caf\u00e9[APP_KEY]", N],                            // a name whose last character is past ASCII (the e accented): a whole identifier token, listed (red where the name arm was a run of ASCII characters and left it unlisted)
    ["    ea = \u00e9a[APP_KEY]", N],                              // a name whose first character is past ASCII: listed (red where the name arm's first character was ASCII only, which leaves the a behind that character no start)
    ["    if 1. in [k]:", null],                                   // a list display behind the hard keyword in after a float's trailing dot: only match and case follow an attribute's dot, so in is the keyword, not listed (red where the dot test read any dot before a keyword as an attribute's; review round 9)
    ["        pass", null],
    ["    el = ... in [k]", null],                                 // the same after an Ellipsis: not listed (red where the Ellipsis's last dot was read as an attribute's)
    ["    match c:", null],                                        // a match statement: no bracket of its own
    ["        case [k]:", null],                                   // a sequence pattern behind the standalone soft keyword case: not listed (review round 8)
    ["            pass", null],
    ['    _serve(c["app"])', 7],
    ['    return c["app"]', 7],
    ["    return [c]", null],                                      // a one-element list display behind a keyword: not listed (review round 7)
  ];
  const src = "\n" + plant.map(([l]) => l).join("\n") + "\n\ndef _next():\n    pass\n";
  const a = pushAudiences(src);
  const lineOf = (w: string) => parseInt(w.slice("kernel.py:".length), 10);
  const linesTagged = (tag: string | number) => plant.flatMap(([, t], i) => (t === tag ? [i + 2] : []));   // the leading newline: plant[0] is line 2
  assert.deepEqual(a.tuples, [["feed", "outline", "waiting-2", "x9"], ["timeline", "notes"], ["chat", "tight"], ["chat", "spaced"], ["timeline", "wrapped"]], T);
  assert.deepEqual(a.singles, ["chat", "timeline", "feed", "chat"], S);
  assert.deepEqual(a.unread, [], "the plant leaves no app literal unread: OTHER_FORMS[6]'s `app = c[\"app\"]` binds a name to the READ, not to the key, and every tuple member and every compared value is a read");
  const listDisplays = plant.flatMap(([l, t], i) => (t === null && /\[c\]/.test(l) ? [i + 2] : []));
  assert.equal(listDisplays.length, 2, "the two one-element list displays are planted (xs = [c], return [c])");
  assert.deepEqual(a.byName.map(lineOf).filter((l) => listDisplays.includes(l)), [], "a one-element list display has no receiver before its bracket and is no subscript: not listed as the ninth form (review round 7)");
  const patterns = plant.flatMap(([l, t], i) => (t === null && /^\s*case \[/.test(l) ? [i + 2] : []));
  assert.equal(patterns.length, 1, "the sequence pattern behind the soft keyword case is planted (case [k]:)");
  assert.deepEqual(a.byName.map(lineOf).filter((l) => patterns.includes(l)), [], "a sequence pattern behind the standalone soft keyword case is no subscript: not listed as the ninth form (review round 8)");
  assert.deepEqual(a.byName.map(lineOf), linesTagged(N), N);
  assert.deepEqual(a.text.map(lineOf), linesTagged(X), X);
  OTHER_FORMS.forEach((form, k) => {
    assert.ok(linesTagged(k).length >= 1, form + ": planted at least once, so the detector is known to fire");
    assert.deepEqual(a.other.get(form)!.map(lineOf), linesTagged(k), form);
  });
  assert.equal(a.reads, a.tuples.length + a.singles.length + a.text.length + [...a.other.values()].flat().length,
    "every read of the app key landed in exactly one form");
  assert.equal(a.reads, plant.filter(([, t]) => t !== null && t !== N).length, "and the plant's reads were all seen (the ninth form's read is of a key the census does not know)");
  // the message a red carries names the form, the line and the statement
  assert.match(a.other.get(OTHER_FORMS[0])![0], /^kernel\.py:\d+ if c\["app"\] in NOTE_APPS:$/);
});

test("an app literal in _push's body in a position the census does not read is listed with its statement, whatever holds it (an assignment, a tuple unpacking, an annotated one with a spaced, an unspaced union or a string annotation, a walrus, a parameter default, a for target, a parenthesised target, a parenthesised or a call-wrapped literal, a keyword argument, a passed value) and never from a docstring's prose, another literal, a read key, a compared value or a tuple's member, and a read through a bare name is listed as a subscript or a .get by a name: the road to a key held in a name is red at both ends (review rounds 5 and 6, 2026-09-21)", () => {
  const src = [
    "",
    "def _push(targets, connect=False, live_map=None):",
    '    """prose saying KEY = "app" is text, not a binding"""',
    '    KEY = "app"',
    '    if c[KEY] in ("feed", "outline"):',
    "        pass",
    "    key2: str = 'app'",
    '    if (k3 := "app") and c.get(k3) == "chat":',
    "        pass",
    '    def inner(k4="app"):',
    "        return c.get(k4)",
    '    tag = "app-2"',
    '    if c["app"] == "app":',
    "        pass",
    '    k5, k6 = "x", "app"',                 // a tuple unpacking (review round 6: the shapes a scan keyed on a binding's spelling missed)
    '    k7 = ("app")',                        // a parenthesised literal
    '    k8: str|None = "app"',                // an unspaced union annotation
    '    k9: "str" = "app"',                   // a string annotation
    '    for k10 in ("app",):',                // a for target
    "        pass",
    '    k11 = str("app")',                    // a call-wrapped literal
    '    (k12) = "app"',                       // a parenthesised target
    '    opts = dict(kind="app")',             // a keyword argument (round 5 listed it too, as a bound local name: the wrong cause)
    '    _serve("app")',                       // a passed value
    '    if c["app"] in ("app", "feed"):',     // a tuple's member is read into the roster, not listed
    "        pass",
    "",
    "def _next():",
    "    pass",
    "",
  ].join("\n");
  const a = pushAudiences(src);
  const lineOf = (w: string) => parseInt(w.slice("kernel.py:".length), 10);
  assert.deepEqual(a.unread.map(lineOf), [4, 7, 8, 10, 15, 16, 17, 18, 19, 21, 22, 23, 24],
    "the thirteen literals the census does not read, and neither the docstring's prose, the other literal, the read key, the compared value nor the tuple's member");
  assert.match(a.unread[0], /^kernel\.py:4 KEY = "app"$/);
  assert.deepEqual(a.byName.map(lineOf), [5, 8, 11], "c[KEY], c.get(k3) and c.get(k4): each read through a bare name is listed as the ninth form");
  assert.match(a.byName[0], /^kernel\.py:5 if c\[KEY\] in \("feed", "outline"\):$/);
  assert.equal(a.reads, 2, "the three reads through a name are no reads of the app key the census knows; the literal reads are the two");
  assert.deepEqual(a.singles, ["app"]);
  assert.deepEqual(a.tuples, [["app", "feed"]]);
});

test("a pane's FIRST publish posts even an empty list, so a reloaded pane replaces the list its predecessor left (2026-09-18)", async () => {
  await withManager((fm, _e, _d, posted) => {
    fm.app = "feed";
    fm.inbound("", localFeed);   // no remote attached: the fresh instance still declares its (empty) list once
    assert.deepEqual(posted.filter((m) => m && m.romp === "hostsPending").pop(), { romp: "hostsPending", app: "feed", hosts: [] },
      "the first publish is never gated by the empty signature");
    fm.inbound("", { ...localFeed, buildId: 2 });
    assert.equal(posted.filter((m) => m && m.romp === "hostsPending").length, 1, "…and posts again only on a change");
  });
});

test("the CHAT pane pends on the TAB LIST channel — the set its pin prune reads as __rompFed.pending (render.ts reachableHosts): an attached host pends from openRemote until its own tabOrder lands here, whatever else arrives; a detach retires it", async () => {
  await withManager((fm) => {
    fm.app = "chat";
    fm.openRemote("TESTHOST", true);
    assert.deepEqual(fm.pendingFor(), ["TESTHOST"], "attached and dialed, no tab list from it yet");
    fm.inbound("", { type: "tabOrder", order: [U], tabs: [{ id: U, name: "web" }] });
    assert.deepEqual(fm.pendingFor(), ["TESTHOST"], "the LOCAL list is not the remote's");
    fm.inbound("TESTHOST", localFeed);
    assert.deepEqual(fm.pendingFor(), ["TESTHOST"], "a feed payload from the host means nothing to the chat pane");
    fm.inbound("TESTHOST", { type: "tabOrder", order: [], tabs: [] });
    assert.deepEqual(fm.pendingFor(), [], "its first tab list — even an EMPTY one — retires it");
    fm.closeRemote("TESTHOST");
    assert.deepEqual(fm.pendingFor(), [], "detached: in no list at all");
  });
});

// ── the page never holds, nor sends, a remote's credential (2026-09-08) ──────────────────────────────
// /tunnels used to ship each remote's serve token to the page, and the dial URL carried it back — even
// though the relay (_remote_ws) injects that token itself. The row now says only whether one exists.
test("the poll dials the hosts that HAVE a token, and no dial URL carries a token — not even one a row still ships", async () => {
  const g: any = globalThis;
  const hadFetch = "fetch" in g, prevFetch = g.fetch;
  const LEAKED = "remote-secret-DO-NOT-USE";
  g.fetch = async () => ({ ok: true, json: async () => ({ tunnels: [
    { host: "TESTHOST", hasToken: true, localPort: 5, status: "up" },
    { host: "HOSTB", hasToken: false, localPort: 6, status: "up" },          // no admin path to it: not dialed
    { host: "HOSTC", hasToken: true, token: LEAKED, localPort: 7, status: "up" },   // an older kernel's row shape
  ] }) });
  try {
    await withManager(async (fm) => {
      fm.app = "feed";
      await fm.poll();
      assert.deepEqual([...fm.conns.keys()].sort(), ["HOSTC", "TESTHOST"], "hasToken gates the dial; HOSTB is left alone");
      assert.equal(FakeWS.made.length, 2, "one socket per dialed host");
      for (const ws of FakeWS.made) {
        assert.match(ws.url, /\/remote\/(TESTHOST|HOSTC)\/ws\?app=feed/, "through the local kernel's relay");
        assert.doesNotMatch(ws.url, /token=/, "the relay adds the remote's credential; the page sends none");
        assert.ok(!ws.url.includes(LEAKED), "a token a row still carries never leaves the page");
      }
      for (const c of fm.conns.values()) c.closed = true;
    });
  } finally {
    if (hadFetch) g.fetch = prevFetch; else delete g.fetch;
  }
});

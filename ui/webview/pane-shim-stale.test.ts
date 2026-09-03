// The pane shim's stale-banner rule, RUN rather than grepped (2026-09-02). The shim is the JS the kernel
// inlines into every pane page (kernel.py _shim); its template is lifted from the kernel source here,
// rendered as the feed page renders it, and executed in a sandbox with a fake WebSocket, a fake clock and
// a fake shell. The rule under test: after a reconnect, the "what you see may be stale" prompt is raised
// by the SECOND KEEPALIVE arriving before the resync frame (one full heartbeat period, bracketed by two
// kernel heartbeats on this socket with no resync between them — a single keepalive can be a beat that
// was already queued when the socket was accepted), or by the reconnected socket CLOSING before it, and
// by nothing else — no timer (every scenario runs the pending timers afterwards and asserts nothing
// fired, and asserts no timer is armed on open); the first non-keepalive frame retires it; a keepalive
// never reaches the bundle. Also run here: the close breadcrumbs (one `wsclose` per socket that OPENED;
// the redials an outage refused coalesced into one `wsconnfail` row on the next open), the cap on
// queued breadcrumbs, and the reconnect's `ready` re-send — only once the BUNDLE has sent its own (the
// 2026-09-03 review: a redial that completed before feed.js had loaded said `ready` for it, the kernel
// served the frame to a page with no listener, and the bundle's own `ready` was then deduped against it).
// Synthetic only (TESTHOST, no session data).
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import * as vm from "node:vm";

const KERNEL = fs.readFileSync(path.resolve(process.cwd(), "..", "kernel", "kernel.py"), "utf8");

function shimJs(app: string, caps: string): string {
  const def = KERNEL.indexOf("def _shim(app, v=0, caps=\"\"):");
  assert.ok(def > 0, "the shim renderer exists with its caps parameter");
  const start = KERNEL.indexOf('return """', def) + 'return """'.length;
  const end = KERNEL.indexOf('""" % (app, int(v), caps, app, app)', start);
  assert.ok(end > start, "the template's format tuple is the one the test substitutes");
  const args = [app, "5", caps, app, app];
  let i = 0;
  return KERNEL.slice(start, end).replace(/%[sd]/g, () => args[i++]).replace(/%%/g, "%");
}

class Harness {
  posted: any[] = [];          // what the pane told the shell (wsStale / wsFresh / wsState)
  sent: any[] = [];            // what went up the socket (ready, clientDiag rows)
  toBundle: any[] = [];        // frames the shim handed to the bundle
  sockets: any[] = [];
  timers: Array<() => void> = [];
  visibility: Array<() => void> = [];
  now = 1_000_000;
  win: any;                    // the sandbox window (the shim hangs __rompLocalSend on it)
  constructor(js: string) {
    const h = this;
    class FakeWS {
      url: string; readyState = 0; onopen: any; onmessage: any; onclose: any; onerror: any;
      constructor(url: string) { this.url = url; h.sockets.push(this); }
      send(s: string) { h.sent.push(JSON.parse(s)); }
      close() { if (this.readyState === 3) return; this.readyState = 3; this.onclose?.({ code: 1006, reason: "", wasClean: false }); }
      open() { this.readyState = 1; this.onopen?.(); }
      msg(o: any) { this.onmessage?.({ data: JSON.stringify(o) }); }
    }
    class FakeDate extends Date { static now() { return h.now; } }
    const sandbox: any = {
      window: {
        parent: { postMessage: (m: any) => h.posted.push(m) },   // embedded: the shell owns the banner
        sessionStorage: { getItem: () => "" },
        dispatchEvent: (e: any) => { if (e && e.data !== undefined) h.toBundle.push(e.data); return true; },
        addEventListener: () => {}, innerWidth: 800, innerHeight: 600,
      },
      document: {
        addEventListener: (t: string, f: () => void) => { if (t === "visibilitychange") h.visibility.push(f); },
        visibilityState: "visible", getElementById: () => null,
      },
      localStorage: { getItem: () => null, setItem: () => {} },
      location: { protocol: "http:", host: "TESTHOST:29855", search: "" },
      URLSearchParams: class { get() { return ""; } },
      WebSocket: FakeWS, Date: FakeDate, JSON, console,
      encodeURIComponent,
      Event: class { type: string; constructor(t: string) { this.type = t; } },
      MessageEvent: class { type: string; data: any; constructor(t: string, o: any) { this.type = t; this.data = o.data; } },
      setTimeout: (f: () => void) => { h.timers.push(f); return h.timers.length; },
      clearTimeout: () => {}, setInterval: () => 0,
    };
    sandbox.window.window = sandbox.window;
    this.win = sandbox.window;
    vm.runInNewContext(js, sandbox);
  }
  get ws() { return this.sockets[this.sockets.length - 1]; }
  runTimers() { const t = this.timers.splice(0); for (const f of t) f(); }
  stale() { return this.posted.filter((m) => m.romp === "wsStale" && !m.build).length; }
  fresh() { return this.posted.filter((m) => m.romp === "wsFresh").length; }
  diags(what: string) { return this.sent.filter((m) => m.type === "clientDiag" && m.what === what); }
  kaReachedBundle() { return this.toBundle.some((m) => m && m.type === "ka"); }
  readys() { return this.sent.filter((m) => m.type === "ready").length; }
  /** the bundle has loaded and installed its listener: its own connect handshake goes through the shim's send() */
  bundleReady() { this.win.__rompLocalSend({ type: "ready" }); }
  /** connect, the bundle loads, deliver the first frame, then drop the socket and let the redial run: a RECONNECTED socket */
  reconnected(): any {
    this.ws.open(); this.bundleReady(); this.ws.msg({ type: "feed", asks: [] });
    this.ws.close(); this.runTimers();
    assert.equal(this.sockets.length, 2, "the close redialed");
    this.ws.open();
    assert.equal(this.timers.length, 0, "no timer is armed on open");
    return this.ws;
  }
  /** the end of every scenario: whatever timers are pending fire, and the prompt count must not move */
  settles(expectStale: number) {
    this.runTimers();
    assert.equal(this.stale(), expectStale, "nothing raises the prompt later — no timer does");
  }
}

const FEED = () => new Harness(shimJs("feed", "feedDelta"));

test("the socket announces the page's capability and a reconnect re-sends the connect handshake", () => {
  const h = FEED();
  assert.match(h.ws.url, /\/ws\?app=feed.*&caps=feedDelta/);
  h.reconnected();
  assert.equal(h.readys(), 2, "the bundle's own at load, and one re-sent on the reconnect");
  assert.deepEqual(h.sent.slice(-1), [{ type: "ready" }], "the re-send is the reconnect's last word");
  assert.equal(new Harness(shimJs("chat", "")).ws.url.includes("caps="), false, "a page with no caps announces nothing");
  h.settles(0);
});

test("a reconnect BEFORE the bundle's ready sends none — the bundle's own lifts the hold — and a reconnect after it re-sends", () => {
  const h = FEED();
  h.ws.open();                                     // the socket opens before feed.js has run…
  h.ws.close(); h.runTimers(); h.ws.open();        // …drops mid-load, and the redial opens, still before feed.js
  assert.equal(h.readys(), 0, "nothing says `ready` for a bundle that has not loaded: the kernel keeps holding");
  assert.equal(h.sockets.length, 2);
  h.bundleReady();                                 // feed.js installs its listener and sends its handshake
  assert.equal(h.readys(), 1, "the bundle's own handshake, once");
  h.ws.msg({ type: "feed", asks: [] });            // served on it
  h.ws.close(); h.runTimers(); h.ws.open();        // a later drop
  assert.equal(h.readys(), 2, "…and from then on a reconnect re-sends it");
  assert.deepEqual(h.sent.slice(-1), [{ type: "ready" }]);
  h.settles(0);
});

test("a bundle `ready` queued while the socket was down rides the flush alone — the reconnect adds no second", () => {
  const h = FEED();
  h.ws.open(); h.ws.close();                       // opened, then dropped before the bundle had loaded
  h.bundleReady();                                 // the bundle finishes loading during the outage: its handshake queues
  assert.equal(h.readys(), 0, "queued: the socket is down");
  h.runTimers(); h.ws.open();
  assert.equal(h.readys(), 1, "the queued handshake goes up, and the reconnect does not add another");
  h.ws.msg({ type: "feed", asks: [] });            // served on it: the resync this reconnect's arm was waiting for
  h.ws.close(); h.runTimers(); h.ws.open();
  assert.equal(h.readys(), 2, "a reconnect with nothing queued re-sends as usual");
  h.settles(0);
});

test("resync first: a normal reconnect shows nothing, later keepalives are silent, and no timer is armed", () => {
  const h = FEED();
  const ws = h.reconnected();
  assert.equal(h.stale(), 0, "arming shows nothing");
  ws.msg({ type: "feed", asks: [] });
  assert.equal(h.stale(), 0);
  assert.equal(h.fresh(), 1, "the resync retires the (never shown) prompt");
  ws.msg({ type: "ka", dv: 0 }); ws.msg({ type: "ka", dv: 0 });
  assert.equal(h.stale(), 0, "keepalives after the resync are just keepalives");
  assert.equal(h.toBundle.filter((m) => m.type === "feed").length, 2, "both frames reached the bundle");
  assert.equal(h.kaReachedBundle(), false, "a keepalive never reaches the bundle");
  h.settles(0);
});

test("one keepalive, then the resync: nothing shows — a single beat can be one already queued when the socket was accepted", () => {
  const h = FEED();
  const ws = h.reconnected();
  ws.msg({ type: "ka", dv: 0 });
  assert.equal(h.stale(), 0, "a single keepalive is not the event");
  assert.equal(h.fresh(), 0, "…and it does not retire the arm either: it is not a resync");
  ws.msg({ type: "feed", asks: [] });
  assert.equal(h.stale(), 0);
  assert.equal(h.fresh(), 1, "the resync retires it");
  ws.msg({ type: "ka", dv: 0 });
  assert.equal(h.stale(), 0, "the count died with the arm");
  assert.equal(h.kaReachedBundle(), false);
  h.settles(0);
});

test("two keepalives with no resync between them: the kernel is alive, talking to this socket and has not resynced it — raised", () => {
  const h = FEED();
  const ws = h.reconnected();
  ws.msg({ type: "ka", dv: 0 });
  assert.equal(h.stale(), 0);
  ws.msg({ type: "ka", dv: 0 });
  assert.equal(h.stale(), 1, "the second heartbeat is the event");
  assert.equal(h.diags("stale-raise")[0].data.why, "reconnect");
  ws.msg({ type: "ka", dv: 0 });
  assert.equal(h.stale(), 1, "raised once, not per keepalive");
  ws.msg({ type: "feed", asks: [] });
  assert.equal(h.fresh(), 1, "the late resync still retires it");
  assert.equal(h.kaReachedBundle(), false);
  h.settles(1);
});

test("the reconnected socket closing before its resync raises; the foreground path's own close does not", () => {
  const h = FEED();
  const ws = h.reconnected();
  ws.close();
  assert.equal(h.stale(), 1);
  h.runTimers(); h.ws.open();   // the breadcrumb was queued on the dead socket; it flushes on the redial
  assert.equal(h.timers.length, 0, "no timer is armed on open");
  assert.equal(h.diags("stale-raise")[0].data.why, "reconnect-closed");
  h.settles(1);
  // foreground fast-path: a quiet socket is closed by the pane itself — no raise for that close; the
  // reconnect it forces arms with why=foreground, and two keepalives before the resync raise as usual
  const g = FEED();
  g.ws.open(); g.ws.msg({ type: "feed", asks: [] });
  g.now += 31_000;
  for (const f of g.visibility) f();
  assert.equal(g.stale(), 0, "closing a quiet socket is not a raise");
  g.runTimers(); g.ws.open();
  assert.equal(g.timers.length, 0, "no timer is armed on open");
  g.ws.msg({ type: "ka", dv: 0 });
  assert.equal(g.stale(), 0);
  g.ws.msg({ type: "ka", dv: 0 });
  assert.equal(g.stale(), 1);
  assert.equal(g.diags("stale-raise")[0].data.why, "foreground");
  g.settles(1);
});

test("an announced restart's reconnect skips the arm once (T217); a second reconnect arms as always", () => {
  const h = FEED();
  h.ws.open(); h.ws.msg({ type: "feed", asks: [] });
  h.ws.msg({ type: "restarting" });
  h.ws.close(); h.runTimers(); h.ws.open();
  h.ws.msg({ type: "ka", dv: 0 }); h.ws.msg({ type: "ka", dv: 0 });
  assert.equal(h.stale(), 0, "the announced restart explained this reconnect");
  h.ws.msg({ type: "feed", asks: [] });
  h.ws.close(); h.runTimers(); h.ws.open();
  h.ws.msg({ type: "ka", dv: 0 }); h.ws.msg({ type: "ka", dv: 0 });
  assert.equal(h.stale(), 1, "the latch was one-shot");
  h.settles(1);
});

test("every close of a socket that OPENED leaves a wsclose breadcrumb with the code, the socket's age and the quiet gap", () => {
  const h = FEED();
  h.ws.open(); h.now += 4_000; h.ws.msg({ type: "feed", asks: [] }); h.now += 2_500;
  h.ws.close();
  assert.equal(h.diags("wsclose").length, 0, "queued while the socket is down…");
  h.runTimers(); h.ws.open();
  const rows = h.diags("wsclose");
  assert.equal(rows.length, 1, "…and delivered on the reconnect");
  assert.equal(rows[0].surface, "pane-shim");
  assert.deepEqual(rows[0].data, { app: "feed", code: 1006, reason: "", wasClean: false, sinceOpenMs: 6_500, quietMs: 2_500, everConnected: true });
  assert.equal(h.diags("wsconnfail").length, 0, "no handshake failed");
});

test("the redials an outage refuses leave ONE coalesced row on the next open, never a wsclose each", () => {
  const h = FEED();
  h.ws.open(); h.bundleReady(); h.ws.msg({ type: "feed", asks: [] });
  h.now += 1_000;
  h.ws.close();                                    // the real drop: this socket had opened
  const t0 = h.now;
  for (let i = 0; i < 2400; i++) {                 // an hour of 1.5 s redials, every handshake refused
    h.runTimers();                                 // the redial dials a new socket…
    h.now += 1_500;
    h.ws.close();                                  // …which the browser closes (1006) without it ever opening
  }
  h.runTimers(); h.ws.open();                      // the kernel is back
  const closes = h.diags("wsclose");
  assert.equal(closes.length, 1, "one wsclose: the socket that opened");
  assert.equal(closes[0].data.sinceOpenMs, 1_000, "with ITS timings, not the outage's");
  const fails = h.diags("wsconnfail");
  assert.equal(fails.length, 1, "the refused handshakes are one row");
  assert.deepEqual(fails[0].data, { app: "feed", attempts: 2400, firstFailMs: h.now - (t0 + 1_500) });
  assert.deepEqual(h.sent.slice(-1), [{ type: "ready" }], "…delivered ahead of the handshake");
  assert.equal(h.sent.filter((m) => m.type === "clientDiag").length, 2, "nothing else piled up");
});

test("queued breadcrumbs are capped while the socket is down; other queued messages are untouched", () => {
  const h = FEED();                                // never opened yet: everything queues
  for (let i = 0; i < 30; i++) h.win.__rompLocalSend({ type: "clientDiag", surface: "pane-shim", what: "probe", data: { i } });
  h.win.__rompLocalSend({ type: "activeTab", id: "TESTSID" });
  h.win.__rompLocalSend({ type: "clientDiag", surface: "pane-shim", what: "probe", data: { i: 30 } });
  assert.equal(h.sent.length, 0, "nothing goes up before the open");
  h.ws.open();
  const diag = h.sent.filter((m) => m.type === "clientDiag");
  assert.equal(diag.length, 20, "at most DIAG_QUEUE_MAX breadcrumbs ride the reconnect");
  assert.deepEqual(diag.map((m) => m.data.i), [...Array(20).keys()], "the oldest are kept: the rows about the drop that started it");
  assert.equal(h.sent.filter((m) => m.type === "activeTab").length, 1, "a non-diagnostic message is never dropped");
  assert.equal(h.sent.length, 21);
});

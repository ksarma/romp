// The pane shim's stale-banner rule, RUN rather than grepped (2026-09-02). The shim is the JS the kernel
// inlines into every pane page (kernel.py _shim); its template is lifted from the kernel source here, rendered
// as the feed page renders it, and executed in a sandbox with a fake WebSocket, a fake clock and a fake shell.
// The rule under test: after a reconnect, the "what you see may be stale" prompt is raised by the SECOND
// KEEPALIVE arriving before the resync frame (one full heartbeat period, bracketed by two kernel heartbeats
// on this socket with no resync between them — a single keepalive can be a beat that was already queued
// when the socket was accepted), by the reconnected socket CLOSING before it, or by the shim ABANDONING it
// as quiet before it (the watchdog's tick or the foreground path: a socket the kernel accepted and never
// spoke on — abandon() disowns its onclose, so it runs the close rule itself; the why names the path that
// ARMED, reconnect-quiet or foreground-quiet), and by nothing else — no
// timer (every scenario runs the pending timers afterwards and asserts nothing fired, and asserts no timer
// is armed on open; the watchdog's interval is captured and ticked by hand); the first non-keepalive frame
// retires it; a keepalive never reaches the bundle. Also run here: the close breadcrumbs (one `wsclose` per
// socket that OPENED and was closed by the browser — an abandoned socket leaves none: the watchdog's own
// `watchdog-close` row went down the quiet socket before the abandon, and an armed socket's `-quiet` raise
// rides the redial; the redials an outage refused coalesced into one `wsconnfail` row on the next open),
// the cap on queued breadcrumbs, the reconnect's `ready` re-send — only once the BUNDLE has sent its own (the
// 2026-09-03 review: a redial that completed before feed.js had loaded said `ready` for it, the kernel
// served the frame to a page with no listener, and the bundle's own `ready` was then deduped against it) —
// and the Files pane's opt-out of the arm (NO_STALE_CAP, at the end). The caps (readyGate, feedDelta,
// noStale) are the fork's shim; upstream's shim dials without them, and this file pins both the dial
// upstream expects and the caps the fork adds to it.
// Synthetic only (TESTHOST, no session data).
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import * as vm from "node:vm";

const KERNEL = fs.readFileSync(path.resolve(process.cwd(), "..", "kernel", "kernel.py"), "utf8");

// the cap a page with no kernel-pushed view announces (the Files pane): the template bakes the constant's
// value into the shim's CAPS check, so the test reads it from the kernel source rather than restating it
const NO_STALE_CAP = (KERNEL.match(/^NO_STALE_CAP = "(\w+)"$/m) || [])[1] || "";

function shimJs(app: string, caps: string): string {
  const def = KERNEL.indexOf("def _shim(app, v=0, caps=\"\"):");
  assert.ok(def > 0, "the shim renderer exists with its caps parameter");
  const start = KERNEL.indexOf('return """', def) + 'return """'.length;
  // the tuple's first slot is the reload core (T265, its own executed test in tests/test_dashboard_auto_reload.py);
  // an empty core here leaves window.__rompReload undefined, so the shim's raise takes its fallback path; the
  // caps and the no-stale cap constant are the fork's slots (the Files pane's opt-out, at the end)
  const end = KERNEL.indexOf('""" % (_reload_core(v), app, int(v), caps, NO_STALE_CAP, app, app)', start);
  assert.ok(end > start, "the template's format tuple is the one the test substitutes");
  assert.ok(NO_STALE_CAP, "the no-stale cap constant exists");
  const args = ["", app, "5", caps, NO_STALE_CAP, app, app];
  let i = 0;
  return KERNEL.slice(start, end).replace(/%[sd]/g, () => args[i++]).replace(/%%/g, "%");
}

class Harness {
  posted: any[] = [];          // what the pane told the shell (wsStale / wsFresh / wsState)
  sent: any[] = [];            // what went up the socket (ready, clientDiag rows)
  toBundle: any[] = [];        // frames the shim handed to the bundle
  reloads: any[] = [];         // what the shim asked the reload core for (T265: the build raise goes there)
  sockets: any[] = [];
  timers: Array<() => void> = [];
  interval: (() => void) | null = null;   // the progress watchdog's 5 s tick, run by hand (tick)
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
        // T265 (upstream 2026-09-08): the build raise asks the reload core embedded above the shim, not the shell
        // directly. The core's own tests are tests/test_dashboard_auto_reload.py; here a fake records the requests,
        // and says the page sits in a shell so the reconnect's checkBoot stays the shell's
        __rompReload: { requests: [] as any[], request(reason: string, detail: string) { h.reloads.push({ reason, detail }); },
                        inShell: () => true, checkBoot: () => {}, refused: null as any },
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
      clearTimeout: () => {}, setInterval: (f: () => void) => { h.interval = f; return 1; },
      // 2026-09-07: the shim hands frames to the bundle through a MessageChannel-flushed queue. Delivered
      // synchronously here, so `toBundle` reads in wire order exactly as before; the slicing has its own tests
      // (tests/test_pane_shim_return.py). `performance` backs the page-load breadcrumb's navigation type.
      MessageChannel: class { port1: any = { onmessage: null }; port2: any; constructor() { const p1 = this.port1; this.port2 = { postMessage: (d: any) => { p1.onmessage?.({ data: d }); } }; } },
      performance: { getEntriesByType: () => [] },
    };
    sandbox.window.window = sandbox.window;
    this.win = sandbox.window;
    vm.runInNewContext(js, sandbox);
  }
  get ws() { return this.sockets[this.sockets.length - 1]; }
  runTimers() { const t = this.timers.splice(0); for (const f of t) f(); }
  /** one tick of the progress watchdog (the shim's setInterval body) */
  tick() { assert.ok(this.interval, "the watchdog is armed"); this.interval!(); }
  stale() { return this.posted.filter((m) => m.romp === "wsStale" && !m.build).length; }
  fresh() { return this.posted.filter((m) => m.romp === "wsFresh").length; }
  builds() { return this.reloads.filter((r) => r.reason === "build"); }
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
  assert.match(h.ws.url, /^ws:\/\/TESTHOST:29855\/ws\?app=feed&delta=1&iid=/, "dialed as the kernel's connect handler expects it");
  assert.match(h.ws.url, /\/ws\?app=feed.*&caps=feedDelta/, "…with the page's caps on the end");
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

test("a delta frame the shim reassembles is the resync too: it retires the arm like a full frame", () => {
  // the connect push to a pane that already holds the slot arrives as {type:"delta"} (the kernel's view
  // deltas); the shim rebuilds the full message and hands THAT to the bundle — the resync, whatever its wire shape
  const h = FEED();
  const ws = h.reconnected();
  ws.msg({ type: "ka", dv: 0 });
  ws.msg({ type: "feed", asks: [{ itemId: "TESTSID:g1", text: "a" }], _keys: { asks: ["TESTSID:g1"] } });
  assert.equal(h.fresh(), 1);
  ws.close(); h.runTimers(); h.ws.open();
  h.ws.msg({ type: "ka", dv: 0 });
  h.ws.msg({ type: "delta", slot: "feed", base: 0, rev: 1, coll: { asks: { set: { "TESTSID:g1": { itemId: "TESTSID:g1", text: "b" } } } } });
  assert.equal(h.stale(), 0);
  assert.equal(h.fresh(), 2, "the reassembled delta retired the second arm");
  assert.equal(h.toBundle[h.toBundle.length - 1].asks[0].text, "b", "…and the bundle got the full message");
  h.ws.msg({ type: "ka", dv: 0 }); h.ws.msg({ type: "ka", dv: 0 });
  assert.equal(h.stale(), 0);
  h.settles(0);
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

test("a reconnected socket that stays SILENT — no keepalive, no resync — raises when the watchdog abandons it; the redial resyncs as usual", () => {
  // the kernel accepted the reconnect and never spoke on it (a wedged kernel; a proxy that accepted and
  // forwards nothing): no keepalive arrives to count, and abandon() disowns the socket's onclose, so the
  // close rule never sees it either. Until abandon() ran that rule itself, every silent cycle re-armed from
  // zero — the loader flapped every 30 s and the prompt never came, where the old timer raised on the first.
  const h = FEED();
  const ws = h.reconnected();
  h.now += 31_000;
  h.tick();
  assert.equal(h.stale(), 1, "abandoning an armed socket is the event: nothing is coming on it");
  assert.equal(h.sockets.length, 3, "…and the same tick redialed");
  assert.equal(ws.onclose, null, "the abandoned socket is disowned: its eventual close is nobody's event");
  assert.equal(h.sent.filter((m) => m.type === "clientDiag" && m.what === "stale-raise").length, 0,
    "the breadcrumb queued rather than going down the quiet socket, which would have swallowed it");
  h.ws.open();
  assert.equal(h.timers.length, 0, "no timer is armed on open");
  const raised = h.diags("stale-raise");
  assert.equal(raised.length, 1, "…and it rode the reconnect");
  assert.equal(raised[0].data.why, "reconnect-quiet");
  assert.equal(h.diags("wsclose").length, 1, "the abandoned socket leaves no wsclose row: only the browser-reported drop did");
  assert.equal(h.diags("watchdog-close").length, 1, "the watchdog's own row, sent down the quiet socket before the abandon");
  h.ws.msg({ type: "feed", asks: [] });
  assert.equal(h.fresh(), 1, "the redial's resync retires the prompt as always");
  h.ws.msg({ type: "ka", dv: 0 }); h.ws.msg({ type: "ka", dv: 0 });
  assert.equal(h.stale(), 1, "…after which its keepalives are just keepalives");
  h.settles(1);
});

test("three silent cycles: one raise per cycle, one watchdog row each, and no wsclose for any abandoned socket", () => {
  const h = FEED();
  h.reconnected();
  for (let i = 1; i <= 3; i++) {
    h.now += 31_000;
    h.tick();
    assert.equal(h.stale(), i, "cycle " + i + " raised: the watchdog never eats an armed cycle");
    h.ws.open();
    assert.equal(h.timers.length, 0, "no timer is armed on open");
  }
  assert.equal(h.sockets.length, 5);
  assert.deepEqual(h.diags("stale-raise").map((m) => m.data.why), ["reconnect-quiet", "reconnect-quiet", "reconnect-quiet"]);
  assert.equal(h.diags("watchdog-close").length, 3);
  assert.equal(h.diags("wsclose").length, 1, "the first, browser-reported drop — and nothing for the three abandonments");
  h.settles(3);
});

test("the foreground path abandoning an ARMED quiet socket raises too; its redial arms as foreground", () => {
  const h = FEED();
  h.reconnected();                          // armed on the reconnect; the tab then slept on a socket that said nothing
  h.now += 31_000;
  for (const f of h.visibility) f();
  assert.equal(h.stale(), 1, "the tab came back to a socket that armed and then heard nothing");
  assert.equal(h.sockets.length, 3, "abandoned and redialed at once");
  h.ws.open();
  assert.equal(h.diags("stale-raise")[0].data.why, "reconnect-quiet", "named for the path that armed, not the one that abandoned");
  h.ws.msg({ type: "ka", dv: 0 }); h.ws.msg({ type: "ka", dv: 0 });
  assert.equal(h.stale(), 2, "the foreground redial armed on its own account, and its two beats raise as usual");
  assert.equal(h.diags("stale-raise")[1].data.why, "foreground");
  h.settles(2);
});

test("a redial armed as FOREGROUND that then stays silent raises when the watchdog abandons it: the why is foreground-quiet", () => {
  // the arm names the path that forced the reconnect, and a silent socket's raise keeps that name with the
  // -quiet suffix — the shim comment and docs/read-side.md name both spellings; only reconnect-quiet was
  // pinned before this
  const h = FEED();
  h.ws.open(); h.ws.msg({ type: "feed", asks: [] });   // connected, then the socket goes quiet while the tab sleeps
  h.now += 31_000;
  for (const f of h.visibility) f();                    // foregrounded: the quiet socket is abandoned (it never armed: no raise) and redialed now
  assert.equal(h.stale(), 0, "abandoning a socket that never armed is not a raise");
  assert.equal(h.sockets.length, 2, "abandoned and redialed at once");
  h.ws.open();                                          // the forced reconnect opens and arms as foreground
  assert.equal(h.timers.length, 0, "no timer is armed on open");
  h.now += 31_000;
  h.tick();                                             // the foreground redial said nothing either: the watchdog abandons it
  assert.equal(h.stale(), 1, "abandoning the armed foreground redial is the event");
  assert.equal(h.sockets.length, 3, "…and the same tick redialed");
  h.ws.open();
  assert.deepEqual(h.diags("stale-raise").map((m) => m.data.why), ["foreground-quiet"], "named for the path that armed, with the quiet suffix");
  assert.equal(h.diags("watchdog-close").length, 1);
  h.ws.msg({ type: "feed", asks: [] });
  assert.equal(h.fresh(), 1, "the redial's resync retires it");
  h.settles(1);
});

test("every close the browser reports for a socket that OPENED leaves a wsclose breadcrumb with the code, the socket's age and the quiet gap", () => {
  const h = FEED();
  h.ws.open(); h.now += 4_000; h.ws.msg({ type: "feed", asks: [] }); h.now += 2_500;
  h.ws.close();
  assert.equal(h.diags("wsclose").length, 0, "queued while the socket is down…");
  h.runTimers(); h.ws.open();
  const rows = h.diags("wsclose");
  assert.equal(rows.length, 1, "…and delivered on the reconnect");
  assert.equal(rows[0].surface, "pane-shim");
  // bundleReady false: the bundle never said ready on this page, so the redial dialed as a fresh page (below)
  assert.deepEqual(rows[0].data, { app: "feed", code: 1006, reason: "", wasClean: false, sinceOpenMs: 6_500, quietMs: 2_500, everConnected: true, bundleReady: false });
  assert.equal(h.diags("wsconnfail").length, 0, "no handshake failed");
});

// The wsclose row's bundleReady is the shim's state at the CLOSE; the kernel stamps every row with whether the
// socket that carried it declared the redial (?reconnect=1). The queued row rides the redial, so the pair tells
// the three shapes apart in client-diag.jsonl (2026-09-10; the kernel half is tests/test_client_diag_reconnect_stamp.py).
test("the wsclose row says whether the bundle had said ready at the close, beside the redial's own term", () => {
  // declared: the bundle said ready on the socket that died, and the redial carries the term
  let h = FEED();
  h.ws.open(); h.bundleReady(); h.ws.msg({ type: "feed", asks: [] });
  h.ws.close(); h.runTimers();
  assert.match(h.ws.url, /&reconnect=1$/, "the redial declares itself");
  h.ws.open();
  assert.equal(h.diags("wsclose")[0].data.bundleReady, true, "the bundle had said ready when the socket closed");
  // gated off: the socket died before the bundle said ready, and the redial dials as a fresh page
  h = FEED();
  h.ws.open(); h.ws.close(); h.runTimers();
  assert.doesNotMatch(h.ws.url, /reconnect=1/, "no term: the page held nothing");
  h.ws.open();
  assert.equal(h.diags("wsclose")[0].data.bundleReady, false, "the bundle had not said ready at the close");
  // the ready reached the shim while the socket was CLOSING (the browser holds a closing handshake open): it
  // queued, the row says the bundle was ready, and the redial still carries no term (the queued ready is the
  // bundle's own, flushed onto the redial); the kernel reads the pair as reconnect false, bundleReady true
  h = FEED();
  h.ws.open(); h.ws.readyState = 2; h.bundleReady();
  h.ws.close(); h.runTimers();
  assert.doesNotMatch(h.ws.url, /reconnect=1/, "the ready is still queued for this open, so no term");
  h.ws.open();
  const kinds = h.sent.map((m) => (m.type === "clientDiag" ? m.what : m.type));
  assert.deepEqual(kinds, ["ready", "wsclose"], "the ready queued first, during the close; this socket declared no term, so the order does not touch the stamp");
  assert.equal(h.diags("wsclose")[0].data.bundleReady, true);
  assert.equal(h.readys(), 1, "the queued ready went out once; nothing re-sent it");
  // on the declared shape the order is the other way round: the shim flushes the queued row ahead of the re-sent
  // ready (a shim fact; the kernel's stamp reads the socket's dial record, set at accept and never consumed, so it
  // does not depend on this order)
  h = FEED();
  h.ws.open(); h.bundleReady(); h.ws.msg({ type: "feed", asks: [] }); h.ws.close(); h.runTimers(); h.ws.open();
  assert.deepEqual(h.sent.slice(-2).map((m) => (m.type === "clientDiag" ? m.what : m.type)), ["wsclose", "ready"]);
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
  assert.deepEqual(h.sent.slice(-2, -1), fails, "…sent on the open, after the flushed wsclose");
  assert.deepEqual(h.sent.slice(-1), [{ type: "ready" }], "…and ahead of the handshake the reconnect re-sends (the bundle had sent its own)");
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

// ── the Files pane: a page with NO live kernel-pushed view opts out of the arm ──────────────────────
// app=files (2026-09-03) is a viewer, not a feed consumer: its file comes over HTTP on demand and its socket
// carries keepalives and request/response replies only, so the kernel sends it NOTHING on a connect. The
// "first non-keepalive frame" that retires every other pane's arm never comes, and the arm's second
// keepalive raised the shell's shared "connection lost — what you see may be stale" banner dashboard-wide
// after every unannounced reconnect (the 2026-09-03 review), for a file a dropped socket cannot make stale.
// The page announces NO_STALE_CAP; the shim reads it from CAPS and neither arms nor retires. Run, not
// grepped, against the same harness — and the contrast (the same page shape WITHOUT the cap) still raises.
const FILES = (caps: string) => new Harness(shimJs("files", caps));

test("the cap is the kernel's NO_STALE_CAP, announced by the Files page alone, read off CAPS by the shim", () => {
  assert.equal(NO_STALE_CAP, "noStale");
  assert.match(KERNEL, /_shim\("files", v, caps=READY_GATE_CAP \+ "," \+ NO_STALE_CAP\)/);
  assert.equal(KERNEL.match(/_shim\("\w+", v, caps=[^)]*NO_STALE_CAP/g)!.length, 1, "no other pane page passes it");
  assert.ok(shimJs("files", "readyGate,noStale").includes('var NOSTALE=CAPS.split(",").indexOf("noStale")>=0;'));
});

test("a page announcing the no-stale cap never arms: no keepalive count, no close, no foreground path raises, nothing is retired", () => {
  const h = FILES("readyGate," + NO_STALE_CAP);
  assert.match(h.ws.url, /\/ws\?app=files.*&caps=readyGate%2CnoStale/, "the cap rides the ws URL like the others");
  h.ws.open(); h.bundleReady();                    // no connect-time frame: the kernel builds nothing for this page
  h.ws.close(); h.runTimers(); h.ws.open();        // an UNANNOUNCED reconnect
  assert.equal(h.sockets.length, 2);
  assert.equal(h.readys(), 2, "the ready re-send is untouched: the hold still lifts on a reconnect");
  h.ws.msg({ type: "ka", dv: 0 }); h.ws.msg({ type: "ka", dv: 0 }); h.ws.msg({ type: "ka", dv: 0 });
  assert.equal(h.stale(), 0, "keepalives with no resync between them are not the event here: no resync was ever coming");
  assert.equal(h.diags("stale-raise").length, 0);
  h.ws.msg({ type: "fileSaved", reqId: 1, mtimeNs: "1" });   // an op reply: request/response, not a resync
  assert.equal(h.toBundle.filter((m) => m.type === "fileSaved").length, 1, "replies still reach the bundle");
  assert.equal(h.fresh(), 0, "…and retire nothing: the page never armed, and a peer pane's prompt is not its to retract");
  h.ws.close();                                    // the reconnected socket dying before any frame
  assert.equal(h.stale(), 0, "the close rule needs an arm too");
  h.runTimers(); h.ws.open();
  // the foreground fast-path: a quiet socket is closed by the pane and the reconnect it forces would arm with
  // why=foreground on any other page
  h.ws.msg({ type: "fileSaved", reqId: 2, mtimeNs: "2" });
  h.now += 31_000;
  for (const f of h.visibility) f();
  h.runTimers(); h.ws.open();
  h.ws.msg({ type: "ka", dv: 0 }); h.ws.msg({ type: "ka", dv: 0 });
  assert.equal(h.stale(), 0);
  assert.equal(h.fresh(), 0);
  // BUILD drift is a separate raise and still stands: new code is not delivered by any frame, only a reload.
  // Since T265 (upstream 2026-09-08, taken as written) the raise is a request to the reload core, which forwards
  // to the shell or reloads the page itself, not a wsStale post; the cap leaves it alone either way
  h.ws.msg({ type: "ka", dv: 9 });
  assert.equal(h.builds().length, 1, "the newer-build request is untouched");
  assert.equal(h.posted.filter((m) => m.romp === "wsStale").length, 0, "…and it is the reload core's raise, not the connection prompt");
  h.settles(0);
  // the contrast: the same page shape WITHOUT the cap, the same sequence — raised on the second keepalive.
  // The opt-out is the cap the page announces, not its app name.
  const g = FILES("readyGate");
  g.ws.open(); g.bundleReady(); g.ws.close(); g.runTimers(); g.ws.open();
  g.ws.msg({ type: "ka", dv: 0 });
  assert.equal(g.stale(), 0);
  g.ws.msg({ type: "ka", dv: 0 });
  assert.equal(g.stale(), 1, "without the cap the arm and its second-keepalive raise are exactly the feed's");
  assert.equal(g.diags("stale-raise")[0].data.why, "reconnect");
  g.settles(1);
});

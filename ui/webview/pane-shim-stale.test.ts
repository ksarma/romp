// The pane shim's stale-banner rule, RUN rather than grepped (2026-09-02). The shim is the JS the kernel
// inlines into every pane page (kernel.py _shim); its template is lifted from the kernel source here,
// rendered as the feed page renders it, and executed in a sandbox with a fake WebSocket, a fake clock and
// a fake shell. The rule under test: after a reconnect, the "what you see may be stale" prompt is raised
// by a KEEPALIVE arriving before the resync frame, or by the reconnected socket CLOSING before it, and by
// nothing else; the first non-keepalive frame retires it. Synthetic only (TESTHOST, no session data).
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
    vm.runInNewContext(js, sandbox);
  }
  get ws() { return this.sockets[this.sockets.length - 1]; }
  runTimers() { const t = this.timers.splice(0); for (const f of t) f(); }
  stale() { return this.posted.filter((m) => m.romp === "wsStale" && !m.build).length; }
  fresh() { return this.posted.filter((m) => m.romp === "wsFresh").length; }
  diags(what: string) { return this.sent.filter((m) => m.type === "clientDiag" && m.what === what); }
  /** connect, deliver the first frame, then drop the socket and let the redial run: a RECONNECTED socket */
  reconnected(): any {
    this.ws.open(); this.ws.msg({ type: "feed", asks: [] });
    this.ws.close(); this.runTimers();
    assert.equal(this.sockets.length, 2, "the close redialed");
    this.ws.open();
    return this.ws;
  }
}

const FEED = () => new Harness(shimJs("feed", "feedDelta"));

test("the socket announces the page's capability and a reconnect re-sends the connect handshake", () => {
  const h = FEED();
  assert.match(h.ws.url, /\/ws\?app=feed.*&caps=feedDelta/);
  h.reconnected();
  assert.deepEqual(h.sent.filter((m) => m.type === "ready"), [{ type: "ready" }], "ready rides the reconnect, once");
  assert.equal(new Harness(shimJs("chat", "")).ws.url.includes("caps="), false, "a page with no caps announces nothing");
});

test("resync first: a normal reconnect shows nothing, and the next keepalive is silent too", () => {
  const h = FEED();
  const ws = h.reconnected();
  assert.equal(h.stale(), 0, "arming shows nothing");
  ws.msg({ type: "feed", asks: [] });
  assert.equal(h.stale(), 0);
  assert.equal(h.fresh(), 1, "the resync retires the (never shown) prompt");
  ws.msg({ type: "ka", dv: 0 });
  assert.equal(h.stale(), 0, "a keepalive after the resync is just a keepalive");
  assert.equal(h.toBundle.filter((m) => m.type === "feed").length, 2, "both frames reached the bundle");
});

test("keepalive first: the kernel is alive and has not resynced this socket, so the prompt is raised", () => {
  const h = FEED();
  const ws = h.reconnected();
  ws.msg({ type: "ka", dv: 0 });
  assert.equal(h.stale(), 1);
  assert.equal(h.diags("stale-raise")[0].data.why, "reconnect");
  ws.msg({ type: "ka", dv: 0 });
  assert.equal(h.stale(), 1, "raised once, not per keepalive");
  ws.msg({ type: "feed", asks: [] });
  assert.equal(h.fresh(), 1, "the late resync still retires it");
});

test("the reconnected socket closing before its resync raises; the foreground path's own close does not", () => {
  const h = FEED();
  const ws = h.reconnected();
  ws.close();
  assert.equal(h.stale(), 1);
  h.runTimers(); h.ws.open();   // the breadcrumb was queued on the dead socket; it flushes on the redial
  assert.equal(h.diags("stale-raise")[0].data.why, "reconnect-closed");
  // foreground fast-path: a quiet socket is closed by the pane itself — no raise for that close; the
  // reconnect it forces arms with why=foreground, and a keepalive before the resync raises as usual
  const g = FEED();
  g.ws.open(); g.ws.msg({ type: "feed", asks: [] });
  g.now += 31_000;
  for (const f of g.visibility) f();
  assert.equal(g.stale(), 0, "closing a quiet socket is not a raise");
  g.runTimers(); g.ws.open();
  g.ws.msg({ type: "ka", dv: 0 });
  assert.equal(g.stale(), 1);
  assert.equal(g.diags("stale-raise")[0].data.why, "foreground");
});

test("an announced restart's reconnect skips the arm once (T217); a second reconnect arms as always", () => {
  const h = FEED();
  h.ws.open(); h.ws.msg({ type: "feed", asks: [] });
  h.ws.msg({ type: "restarting" });
  h.ws.close(); h.runTimers(); h.ws.open();
  h.ws.msg({ type: "ka", dv: 0 });
  assert.equal(h.stale(), 0, "the announced restart explained this reconnect");
  h.ws.msg({ type: "feed", asks: [] });
  h.ws.close(); h.runTimers(); h.ws.open();
  h.ws.msg({ type: "ka", dv: 0 });
  assert.equal(h.stale(), 1, "the latch was one-shot");
});

test("every close leaves a wsclose breadcrumb with the code, the socket's age and the quiet gap", () => {
  const h = FEED();
  h.ws.open(); h.now += 4_000; h.ws.msg({ type: "feed", asks: [] }); h.now += 2_500;
  h.ws.close();
  assert.equal(h.diags("wsclose").length, 0, "queued while the socket is down…");
  h.runTimers(); h.ws.open();
  const rows = h.diags("wsclose");
  assert.equal(rows.length, 1, "…and delivered on the reconnect");
  assert.equal(rows[0].surface, "pane-shim");
  assert.deepEqual(rows[0].data, { app: "feed", code: 1006, reason: "", wasClean: false, sinceOpenMs: 6_500, quietMs: 2_500, everConnected: true });
});

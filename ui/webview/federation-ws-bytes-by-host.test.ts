// wsBytesByHost (2026-09-19): the text-frame characters each REMOTE host's sockets deliver to a federated page, counted by
// the FederationManager in the conn's ws.onmessage before the parse (a keepalive and an undecodable frame both count, as the
// shim's own wsBytes counter counts them on the LOCAL socket: the same unit, String.length, and disjoint from it), kept per
// host POSITION for the page's life (h1 the first remote host the page saw, assigned in the order hosts first appear, the
// kernel's /tunnels row order for a first answer that lists several) and published as window.__rompFed.wsBytesByHost for
// the collector (perf-telemetry.ts) to difference per minute. The two maps are never pruned: a detached host keeps its
// position and its total, a re-attached host counts on under its old position, and hostSeq (pruned on detach, re-pushed
// on re-attach) is shown NOT to be the source. Executed against the real FederationManager with a fake WebSocket, a
// stubbed /tunnels fetch and a stub window. The user approved the field as one number per host and no content: these
// assert numbers under positional keys and no host name on the published map. Synthetic only (hosts TESTHOSTA,
// TESTHOSTB, TESTHOSTC; placeholder uuids; the notes-api demo's session name `api`).
import { test } from "node:test";
import assert from "node:assert/strict";
import { FederationManager, LOCAL } from "./federation";

const HOST_A = "TESTHOSTA";
const HOST_B = "TESTHOSTB";
const HOST_C = "TESTHOSTC";
const SID = "11111111-2222-4333-8444-000000000901";
const PAGE_IID = "PAGEIID-0001";

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
  /** hand the socket one text frame; returns the characters it carried (String.length, the unit under test) */
  frame(data: any): number { const s = JSON.stringify(data); this.onmessage && this.onmessage({ data: s }); return s.length; }
  /** hand the socket raw text (an undecodable frame); returns its length */
  raw(s: string): number { this.onmessage && this.onmessage({ data: s }); return s.length; }
  close(): void { this.readyState = 3; }
  host(): string { return decodeURIComponent(/\/remote\/([^/]+)\/ws/.exec(this.url)![1]); }
}

let clock = 1_000_000_000;

function terms(): any {
  return { app: "feed", iid: PAGE_IID, active: "", col: "", skeleton: 0, provrows: 0, proto: 2, delta: 1, caps: "feedDelta,readyGate" };
}

interface Rig { fm: any; sent: any[]; rows: any[] }

/** The manager on a stub window, with a /tunnels stub whose rows the test rewrites between polls (rig.rows). */
async function withManager(fn: (rig: Rig) => void | Promise<void>): Promise<void> {
  const g: any = globalThis;
  const saved: Record<string, any> = {};
  const set = (k: string, v: any) => { saved[k] = { had: k in g, v: g[k] }; g[k] = v; };
  FakeWS.made = [];
  const sent: any[] = [];
  const rows: any[] = [];
  const realNow = Date.now;
  Date.now = () => clock;
  set("WebSocket", FakeWS);
  set("location", { protocol: "http:", host: "hub.local:1", search: "?wid=hublab" });
  set("localStorage", { getItem: () => null, setItem: () => {} });
  set("fetch", async () => ({ ok: true, status: 200, json: async () => ({ tunnels: rows.slice() }) }));
  set("window", {
    dispatchEvent: () => {},
    __rompLocalSend: (m: any) => sent.push(m),
    __rompDialTerms: () => terms(),
    sessionStorage: { getItem: () => "" },
    parent: { postMessage: () => {} },
  });
  try {
    const fm: any = new FederationManager();
    fm.app = "feed";
    await fn({ fm, sent, rows });
  } finally {
    Date.now = realNow;
    for (const [k, r] of Object.entries(saved)) { if (r.had) g[k] = r.v; else delete g[k]; }
  }
}

const row = (host: string) => ({ host, hasToken: true, localPort: 5, status: "up" });
const last = (xs: any[]) => xs[xs.length - 1];
const socketFor = (host: string) => [...FakeWS.made].reverse().find((w) => w.host() === host)!;
const full = (n: number) => ({ type: "feed", now: 500, buildId: n, asks: [{ itemId: SID + ":g" + n, sid: SID, name: "api", text: "goal " + n, t: 1000 - n, column: "working" }], ledgers: [] });
// the 2 s retry timers connect() and ws.onclose arm (real setTimeout calls under node), held for the test to fire when it
// chooses (federation-remote-feed-delta.test.ts heldTimers)
function heldTimers(fn: () => void): Array<() => void> {
  const timers: Array<() => void> = [];
  const real = globalThis.setTimeout;
  (globalThis as any).setTimeout = (cb: () => void) => { timers.push(cb); return 0; };
  try { fn(); } finally { (globalThis as any).setTimeout = real; }
  return timers;
}

test("two hosts from one /tunnels answer take positions in the row's order; frames of known length count under h1 and h2 in String.length units, a keepalive and an undecodable frame included; a host with no frame yet reads 0; the local socket's frames count nowhere here", async () => {
  await withManager(async ({ fm, rows }) => {
    assert.deepEqual(fm.wsBytesByHost(), {}, "no remote host ever attached: an empty map (the collector then leaves the key off the row)");
    rows.push(row(HOST_B), row(HOST_A));   // the kernel's row order: B first
    await fm.poll();
    assert.deepEqual([...fm.conns.keys()], [HOST_B, HOST_A]);
    assert.deepEqual(fm.wsBytesByHost(), { h1: 0, h2: 0 }, "both positions exist from the attach, nothing received yet");
    const wsB = socketFor(HOST_B), wsA = socketFor(HOST_A);
    wsB.open(); wsA.open();
    const b1 = wsB.frame(full(1));
    const a1 = wsA.frame(full(2));
    assert.deepEqual(fm.wsBytesByHost(), { h1: b1, h2: a1 }, "the first row's host is h1 whatever its name; the count is the frame text's length");
    assert.ok(b1 > 100 && a1 > 100, "the frames were real text, not empty");
    const ka = wsB.frame({ type: "ka" });
    assert.equal(fm.wsBytesByHost().h1, b1 + ka, "a keepalive counts: the heartbeat is bytes the host sent");
    const bad = wsA.raw("{not json at all");
    assert.equal(fm.wsBytesByHost().h2, a1 + bad, "an undecodable frame counts: the count happens before the parse");
    // the LOCAL kernel's frames come through inbound(), not a relay socket: no position, no key
    fm.inbound(LOCAL, { type: "feed", now: 400, buildId: 7, asks: [], ledgers: [] });
    assert.deepEqual(Object.keys(fm.wsBytesByHost()), ["h1", "h2"], "no local key: wsBytes stays the shim's, and the two are disjoint");
    // a third host attached later, no frame yet: its position exists at 0
    fm.openRemote(HOST_C, true);
    assert.deepEqual(fm.wsBytesByHost(), { h1: b1 + ka, h2: a1 + bad, h3: 0 });
    for (const c of fm.conns.values()) c.closed = true;
    // positions and numbers only on the published map: no host name anywhere in it
    const text = JSON.stringify(fm.wsBytesByHost());
    for (const h of [HOST_A, HOST_B, HOST_C]) assert.ok(!text.includes(h), "no host name on the map: " + text);
  });
});

test("positions are stable for the page's life: a host detached by a /tunnels answer that omits it keeps its position and its total, the other host stays where it was, a host first seen WHILE one is detached takes the next position (never the detached host's), a re-attached host counts on under its old position while hostSeq now lists it LAST", async () => {
  await withManager(async ({ fm, rows }) => {
    rows.push(row(HOST_A), row(HOST_B));
    await fm.poll();
    const wsA = socketFor(HOST_A), wsB = socketFor(HOST_B);
    wsA.open(); wsB.open();
    const a1 = wsA.frame(full(1)), b1 = wsB.frame(full(2));
    assert.deepEqual(fm.wsBytesByHost(), { h1: a1, h2: b1 });
    assert.deepEqual(fm.hostSeq, [LOCAL, HOST_A, HOST_B]);
    assert.deepEqual(fm.attachedHostOrdinals(), ["h1", "h2"], "both attached: the collector's second reader names both positions");
    // /tunnels stops listing A: closeRemote(A) runs from poll()
    rows.splice(0, rows.length, row(HOST_B));
    await fm.poll();
    assert.equal(fm.conns.has(HOST_A), false, "A is detached");
    assert.deepEqual(fm.hostSeq, [LOCAL, HOST_B], "hostSeq pruned A (why it cannot be the position's source)");
    assert.deepEqual(fm.wsBytesByHost(), { h1: a1, h2: b1 }, "neither map was pruned: A's position and total stand, B stays h2");
    assert.deepEqual(fm.attachedHostOrdinals(), ["h2"], "the detach ends A's attachment and nothing else: the collector reads this to leave A off the rows after its detach minute");
    const b2 = wsB.frame(full(3));
    assert.deepEqual(fm.wsBytesByHost(), { h1: a1, h2: b1 + b2 }, "B counts on under h2 after A's detach");
    // a host never seen before arrives WHILE A is detached: the third position, never A's first (a count of the hosts
    // attached now would hand it B's position and merge two hosts' bytes under h2)
    rows.push(row(HOST_C));
    await fm.poll();
    assert.deepEqual(fm.hostSeq, [LOCAL, HOST_B, HOST_C], "two hosts attached, three positions given out");
    socketFor(HOST_C).open();
    const c1 = socketFor(HOST_C).frame(full(5));
    assert.deepEqual(fm.wsBytesByHost(), { h1: a1, h2: b1 + b2, h3: c1 }, "C is h3: positions are never reused, and no two hosts share one");
    assert.deepEqual(fm.attachedHostOrdinals(), ["h2", "h3"]);
    // A comes back: a NEW conn and socket, the same position, while hostSeq lists it last
    rows.splice(0, rows.length, row(HOST_B), row(HOST_C), row(HOST_A));
    await fm.poll();
    assert.deepEqual(fm.hostSeq, [LOCAL, HOST_B, HOST_C, HOST_A], "hostSeq re-pushed A last");
    const wsA2 = socketFor(HOST_A);
    assert.notEqual(wsA2, wsA, "a new socket for the re-attached host");
    wsA2.open();
    const a2 = wsA2.frame(full(4));
    assert.deepEqual(fm.wsBytesByHost(), { h1: a1 + a2, h2: b1 + b2, h3: c1 }, "A is h1 again and its bytes add to h1, not to a fourth position");
    assert.deepEqual(fm.attachedHostOrdinals(), ["h1", "h2", "h3"], "the re-attached host is attached under its old position, in ordinal order whatever hostSeq's");
    for (const c of fm.conns.values()) c.closed = true;
  });
});

test("a detached conn's late retry timer dials nothing and writes nothing: the re-attached conn's socket alone counts under the host's position, and the total is exactly the frames it carried", async () => {
  await withManager(({ fm }) => {
    fm.openRemote(HOST_A, true);
    const ws = last(FakeWS.made);
    ws.open();
    const n = ws.frame(full(1));
    assert.deepEqual(fm.wsBytesByHost(), { h1: n });
    const timers = heldTimers(() => ws.onclose!({ code: 1006, wasClean: false }));   // the socket dropped: its 2 s redial, held
    assert.equal(timers.length, 1);
    fm.closeRemote(HOST_A);   // /tunnels stopped listing the host: the conn is detached, its timer still armed
    assert.deepEqual(fm.wsBytesByHost(), { h1: n }, "the detach prunes neither the position nor the total");
    fm.openRemote(HOST_A, true);   // the next poll lists the host again: a NEW conn
    const ws2 = last(FakeWS.made);
    assert.notEqual(ws2, ws);
    ws2.open();
    const dials = FakeWS.made.length;
    for (const t of timers) t();   // the dead conn's redial fires now: connect() returns at the closed guard
    assert.equal(FakeWS.made.length, dials, "nothing dialed for the dead conn");
    assert.deepEqual(fm.wsBytesByHost(), { h1: n }, "and nothing written by it");
    const m = ws2.frame(full(2));
    assert.deepEqual(fm.wsBytesByHost(), { h1: n + m }, "the live socket's frame adds to the same position");
    fm.conns.get(HOST_A).closed = true;
  });
});

test("start() publishes the getter as window.__rompFed.wsBytesByHost beside hosts(), with attachedHostOrdinals beside it, and both read live state", () => {
  const g: any = globalThis;
  const saved: Record<string, [boolean, unknown]> = {};
  for (const k of ["window", "document", "localStorage", "setInterval", "fetch", "WebSocket", "location"]) saved[k] = [k in g, g[k]];
  const win: any = new EventTarget();
  win.__rompApp = "feed";
  win.__rompDialTerms = () => terms();
  win.sessionStorage = { getItem: () => "" };
  win.parent = { postMessage: () => {} };
  FakeWS.made = [];
  g.window = win;
  g.document = Object.assign(new EventTarget(), { visibilityState: "visible" });
  g.localStorage = { getItem: () => null, setItem: () => {} };
  g.setInterval = () => 0;                 // start()'s poll and watchdog timers: never armed here
  g.fetch = () => new Promise(() => {});   // start()'s first /tunnels poll never answers here
  g.WebSocket = FakeWS;
  g.location = { protocol: "http:", host: "hub.local:1", search: "?wid=hublab" };
  try {
    const fm: any = new FederationManager();
    fm.start();
    assert.equal(typeof win.__rompFed.wsBytesByHost, "function", "published on the window slot for the collector");
    assert.equal(typeof win.__rompFed.attachedHostOrdinals, "function", "…with the attachment reader beside it");
    assert.deepEqual(win.__rompFed.wsBytesByHost(), {}, "nothing attached: an empty map");
    assert.deepEqual(win.__rompFed.attachedHostOrdinals(), []);
    fm.openRemote(HOST_A, true);
    const ws = last(FakeWS.made);
    ws.open();
    const n = ws.frame(full(1));
    assert.deepEqual(win.__rompFed.wsBytesByHost(), { h1: n }, "the getter reads the live map");
    assert.deepEqual(win.__rompFed.attachedHostOrdinals(), ["h1"], "the attachment reader reads the live conns");
    assert.deepEqual(win.__rompFed.hosts(), [HOST_A], "beside the hosts getter the pickers read");
    fm.conns.get(HOST_A).closed = true;
  } finally {
    for (const [k, [had, v]] of Object.entries(saved)) { if (had) g[k] = v; else delete g[k]; }
  }
});

// The grain, by execution (round 3, 2026-09-20; the probe's cases): a position is minted per FederationManager instance, one
// per pane DOCUMENT, so two managers on one page can hold one host under different positions, two panes of the same app
// included, and nothing on either published map names the document. The disclosure copies state the grain and its
// consequence: a page with several panes mints several positions for one machine.
test("two managers on one page assign different positions to one host when their first /tunnels answers differ in order, a same-app pair included; a detach and re-attach reordering does the same across a fresh document; two managers reading one unchanged roster agree; no published map names the document", async () => {
  await withManager(async ({ fm, rows }) => {
    const fm2: any = new FederationManager();
    fm2.app = fm.app;   // the same app: two columns of one kind
    const ord = (m: any) => Object.fromEntries([...m.hostOrdinal].map(([h, o]: [string, number]) => [h, "h" + o]));
    // differing timing: fm polls [A, B]; the roster reorders (a detach and re-attach on the hub) before fm2's first poll
    rows.push(row(HOST_A), row(HOST_B));
    await fm.poll();
    rows.splice(0, rows.length, row(HOST_B), row(HOST_A));
    await fm2.poll();
    assert.deepEqual(ord(fm), { [HOST_A]: "h1", [HOST_B]: "h2" });
    assert.deepEqual(ord(fm2), { [HOST_B]: "h1", [HOST_A]: "h2" }, "one host, two positions, one app: the grain is the manager instance, not the page or (wid, app)");
    const wsA1 = fm.conns.get(HOST_A).ws, wsA2 = fm2.conns.get(HOST_A).ws;
    wsA1.open(); wsA2.open();
    const n1 = wsA1.frame(full(1)), n2 = wsA2.frame(full(2));
    assert.equal(fm.wsBytesByHost().h1, n1);
    assert.equal(fm2.wsBytesByHost().h2, n2, "host A's characters land under h1 in one document and under h2 in the other");
    // a detach and re-attach reordering: fm3 polls [A, B], then [B], then [B, C], so C is h3 there; fm4, a fresh document, polls [B, C]: C is h2
    const fm3: any = new FederationManager(), fm4: any = new FederationManager();
    fm3.app = "timeline"; fm4.app = "timeline";
    rows.splice(0, rows.length, row(HOST_A), row(HOST_B));
    await fm3.poll();
    rows.splice(0, rows.length, row(HOST_B));
    await fm3.poll();
    rows.push(row(HOST_C));
    await fm3.poll();
    await fm4.poll();
    assert.deepEqual(ord(fm3), { [HOST_A]: "h1", [HOST_B]: "h2", [HOST_C]: "h3" });
    assert.deepEqual(ord(fm4), { [HOST_B]: "h1", [HOST_C]: "h2" }, "the same host under h3 in one document and h2 in another");
    // the control: one unchanged roster, two managers, every position agrees
    const fm5: any = new FederationManager(), fm6: any = new FederationManager();
    fm5.app = "feed"; fm6.app = "feed";
    rows.splice(0, rows.length, row(HOST_B), row(HOST_A), row(HOST_C));
    await fm5.poll(); await fm6.poll();
    assert.deepEqual(ord(fm5), { [HOST_B]: "h1", [HOST_A]: "h2", [HOST_C]: "h3" });
    assert.deepEqual(ord(fm6), ord(fm5), "an unchanged roster gives the same positions in every document");
    // nothing on any published map names the document, the pane or a host
    for (const m of [fm, fm2, fm3, fm4, fm5, fm6]) {
      const text = JSON.stringify(m.wsBytesByHost()) + JSON.stringify(m.attachedHostOrdinals());
      for (const h of [HOST_A, HOST_B, HOST_C, "app", "wid", "hublab", "timeline", "feed"]) assert.ok(!text.includes(h), text);
      for (const c of m.conns.values()) c.closed = true;
    }
  });
});

// A federated feed-riding pane's REMOTE sockets take the feed as feedDelta frames (2026-09-18). Before this
// the relay dial announced no caps, so a remote kernel served its feed on the view-delta slot path
// ({type:"delta", slot:"feed"}), which nothing on this side decoded then: the shim reassembled view deltas on its
// LOCAL socket alone (each remote conn carries a receiver since the fold, federation-remote-view-delta.test.ts),
// and federation.ts applied a feedDelta for the local host only. The merged board froze
// on the remote's first full frame; fleet.ts filed a `delta-unapplied` row per dropped frame and posted a
// needSlot the LOCAL kernel could not answer (86 rows in 2.4 minutes on the user's phone). Now remoteDialUrl
// announces REMOTE_DIAL_CAPS on every remote dial, and a remote host's feedDelta applies onto the raw frame
// held for that host and is prefixed whole, as a full frame from it is; with no base held, the kernel that
// sent the delta is asked for a full frame on its own socket. Executed against the real FederationManager
// with a fake WebSocket that records its sends and a stub window that records what the merge emits.
// Synthetic only (host TESTHOST, placeholder uuids, the notes-api demo: sessions `api` and `worker`).
import { test } from "node:test";
import assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { FederationManager, REMOTE_REDIAL_MS, REMOTE_STALE_MS } from "./federation";
import * as fed from "./federation";
import { GEN_MAX } from "./view-deltas";
// the manager's announced capability, read off the module namespace so this file still bundles (and runs red) against a
// federation.ts that predates the export: the wire word is asserted literally below, the export beside it
const REMOTE_DIAL_CAPS: string | undefined = (fed as any).REMOTE_DIAL_CAPS;

const HOST = "TESTHOST";
const SID_A = "11111111-2222-4333-8444-000000000701";   // "api" on TESTHOST
const SID_B = "11111111-2222-4333-8444-000000000702";   // "worker" on TESTHOST
const SID_L = "99999999-8888-7777-6666-000000000001";   // "web", a local session
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
  frame(data: any): void { this.onmessage && this.onmessage({ data: JSON.stringify(data) }); }
  close(): void { this.readyState = 3; }
}

let clock = 1_000_000_000;

// the Outline page's live dial terms, as the shim's __rompDialTerms returns them
function terms(): any {
  return { app: "fleet", iid: PAGE_IID, active: "", col: "", skeleton: 0, provrows: 1, proto: null, delta: 1 };
}

interface Rig { fm: any; emitted: any[]; sent: any[]; notified: any[] }

/** `terms` replaces the page's __rompDialTerms (a function, or null for a page without the shim's seam). */
async function withManager(fn: (rig: Rig) => void | Promise<void>, opts: { terms?: (() => any) | null } = {}): Promise<void> {
  const g: any = globalThis;
  const saved: Record<string, any> = {};
  const set = (k: string, v: any) => { saved[k] = { had: k in g, v: g[k] }; g[k] = v; };
  FakeWS.made = [];
  const emitted: any[] = [];   // what the merge hands the pane (no direct-delivery handler registered: emit dispatches on window)
  const sent: any[] = [];      // what goes to the LOCAL kernel (__rompLocalSend): diag rows, and a needFullFeed if the local path asks
  const notified: any[] = [];  // what the manager posts to the shell (window.parent.postMessage): the apply-throw refusal's visible message (tellShell), hostsPending, reveal
  const realNow = Date.now;
  Date.now = () => clock;
  set("WebSocket", FakeWS);
  set("location", { protocol: "http:", host: "hub.local:1", search: "?wid=hublab" });
  set("localStorage", { getItem: () => null, setItem: () => {} });
  const win: any = {
    dispatchEvent: (ev: any) => { if (ev && ev.data) emitted.push(ev.data); },
    __rompLocalSend: (m: any) => sent.push(m),
    sessionStorage: { getItem: () => "" },
    parent: { postMessage: (m: any) => notified.push(m) },
  };
  win.parent.postMessage = (m: any) => notified.push(m);
  if (opts.terms !== null) win.__rompDialTerms = opts.terms || (() => terms());
  set("window", win);
  try {
    const fm: any = new FederationManager();
    fm.app = "fleet";
    await fn({ fm, emitted, sent, notified });
  } finally {
    Date.now = realNow;
    for (const [k, r] of Object.entries(saved)) { if (r.had) g[k] = r.v; else delete g[k]; }
  }
}

const qOf = (url: string) => new URLSearchParams(url.split("?")[1] || "");
const feeds = (emitted: any[]) => emitted.filter((m) => m && m.type === "feed");
const last = (xs: any[]) => xs[xs.length - 1];
const diagRows = (sent: any[], what: string) => sent.filter((x) => x && x.type === "clientDiag" && x.what === what).map((x) => x.data);
// the 2 s retry timers connect() and ws.onclose arm (real setTimeout calls under node), held for the test to fire when it
// chooses, through a setTimeout stub scoped to the call
function heldTimers(fn: () => void): Array<() => void> {
  const timers: Array<() => void> = [];
  const real = globalThis.setTimeout;
  (globalThis as any).setTimeout = (cb: () => void) => { timers.push(cb); return 0; };
  try { fn(); } finally { (globalThis as any).setTimeout = real; }
  return timers;
}

const card = (sid: string, n: number, over: Record<string, unknown> = {}) =>
  ({ itemId: sid + ":g" + n, sid, name: sid === SID_L ? "web" : sid === SID_A ? "api" : "worker", text: "goal " + n, t: 1000 - n, column: "working", ...over });
const ledger = (sid: string, name: string, tops: string[] = []) => ({ sid, name, ledger: { tops }, status: { state: "working" } });

// the remote kernel's full feed frame, as it sends it: bare ids throughout
function remoteFull(): any {
  return { type: "feed", now: 500, buildId: 1, asks: [card(SID_A, 1)], working: [SID_A],
           ledgers: [ledger(SID_A, "api"), ledger(SID_B, "worker")] };
}

// dial, open, and hand the socket the remote's first full frame; returns the socket
function attached(fm: any): FakeWS {
  fm.openRemote(HOST, true);
  const ws = last(FakeWS.made);
  ws.open();
  ws.frame(remoteFull());
  return ws;
}

test("every remote dial announces caps=feedDelta beside the page's terms, the redial included", async () => {
  await withManager(({ fm }) => {
    fm.outbound({ type: "ready", proto: 2 });
    fm.openRemote(HOST, true);
    const q = qOf(FakeWS.made[0].url);
    assert.equal(q.get("caps"), "feedDelta", "the manager's own capability rides the dial: the kernel's FEED_DELTA_CAP, spelled as the shim spells it");
    assert.equal(REMOTE_DIAL_CAPS, "feedDelta", "…exported as REMOTE_DIAL_CAPS");
    assert.equal(q.get("app"), "fleet");
    assert.equal(q.get("delta"), "1", "the page's own terms still ride unchanged");
    assert.equal(q.get("provrows"), "1");
    const first = FakeWS.made[0];
    first.open();
    first.frame({ type: "caps" });   // the remote acked the page's ready: a later dial is a redial
    first.readyState = 3;
    clock += REMOTE_REDIAL_MS + 1000;
    fm.watchdog(clock);
    assert.equal(FakeWS.made.length, 2, "the watchdog dialed again");
    const rq = qOf(FakeWS.made[1].url);
    assert.equal(rq.get("caps"), "feedDelta", "the redial announces it too: a new client dict on the remote reads its caps at accept");
    assert.equal(rq.get("reconnect"), "1");
    fm.conns.get(HOST).closed = true;
  });
});

// The caps term is REMOTE_DIAL_CAPS and nothing of the page's (2026-09-19): the page's caps string is never a source for a
// remote dial. Its two hold words are the shim's on its OWN socket (readyGate: the kernel sends a client that announces it
// nothing until its bundle's ready, and this manager posts its own ready on a first dial's open and dials a redial as
// ready from accept) and the chat page's (chatResume, a hold this manager never answers), and a held member the page
// states is the pair the PAGE holds for its LOCAL kernel, which the remote kernel would count a miss. These pin the
// negative: terms carrying each of those yield exactly feedDelta on the first dial and the redial, and the three
// no-caps corners (a page without __rompDialTerms, terms carrying no caps field, an empty caps string) yield the same.
const capsOf = (ws: FakeWS) => qOf(ws.url).get("caps");
/** dial, ack the ready, drop the socket and let the watchdog redial: [the first dial's caps, the redial's] */
function firstAndRedial(fm: any): [string | null, string | null] {
  fm.outbound({ type: "ready", proto: 2 });
  fm.openRemote(HOST, true);
  const first = last(FakeWS.made);
  first.open();
  first.frame({ type: "caps" });
  first.readyState = 3;
  clock += REMOTE_REDIAL_MS + 1000;
  fm.watchdog(clock);
  const redial = last(FakeWS.made);
  assert.notEqual(redial, first, "the watchdog dialed again");
  assert.equal(qOf(redial.url).get("reconnect"), "1");
  fm.conns.get(HOST).closed = true;
  return [capsOf(first), capsOf(redial)];
}

test("the page's caps never travel: terms carrying feedDelta,readyGate (the Outline), readyGate alone (the chat) and feedDelta,readyGate,chatResume,held:feed:x.1 each yield exactly feedDelta on the first dial and the redial", async () => {
  await withManager(({ fm }) => {
    assert.deepEqual(firstAndRedial(fm), ["feedDelta", "feedDelta"], "the Outline's caps: its readyGate stays home, its feedDelta is not read (the word is this manager's own)");
  }, { terms: () => ({ ...terms(), caps: "feedDelta,readyGate" }) });
  await withManager(({ fm }) => {
    fm.app = "chat";
    assert.deepEqual(firstAndRedial(fm), ["feedDelta", "feedDelta"], "the chat's caps: readyGate alone yields the decoder word alone");
  }, { terms: () => ({ app: "chat", iid: PAGE_IID, active: "", col: "", skeleton: 1, provrows: 0, proto: 2, delta: 1, caps: "readyGate" }) });
  await withManager(({ fm }) => {
    fm.app = "chat";
    const [first, redial] = firstAndRedial(fm);
    assert.deepEqual([first, redial], ["feedDelta", "feedDelta"], "the chat's two holds and the page's LOCAL held pair: none of it rides a remote dial, on either dial");
    for (const ws of FakeWS.made) assert.equal(qOf(ws.url).get("caps"), "feedDelta", "no dial carried readyGate, chatResume or held:feed:x.1: " + ws.url);
  }, { terms: () => ({ app: "chat", iid: PAGE_IID, active: "", col: "", skeleton: 1, provrows: 0, proto: 2, delta: 1, caps: "feedDelta,readyGate,chatResume,held:feed:x.1" }) });
});

test("the three no-caps corners each yield exactly feedDelta: a page without __rompDialTerms, terms carrying no caps field, an empty caps string", async () => {
  await withManager(({ fm }) => {
    fm.openRemote(HOST, true);
    assert.equal(capsOf(last(FakeWS.made)), "feedDelta", "no seam (a page before 2026-09-15): the decoder word alone");
    assert.equal(qOf(last(FakeWS.made).url).get("delta"), null, "and none of the page's terms, as before");
    fm.conns.get(HOST).closed = true;
  }, { terms: null });
  await withManager(({ fm }) => {
    fm.openRemote(HOST, true);
    assert.equal(capsOf(last(FakeWS.made)), "feedDelta", "terms carrying no caps field (the shim's __rompDialTerms states none)");
    assert.equal(qOf(last(FakeWS.made).url).get("delta"), "1", "the page's other terms ride");
    fm.conns.get(HOST).closed = true;
  });
  await withManager(({ fm }) => {
    fm.openRemote(HOST, true);
    assert.equal(capsOf(last(FakeWS.made)), "feedDelta", "an empty field (a page whose shim announces no cap)");
    fm.conns.get(HOST).closed = true;
  }, { terms: () => ({ ...terms(), caps: "" }) });
});

test("a remote host's feedDelta applies onto the raw frame held for it: removals by the kernel's bare ids land, and the merge reads the result prefixed whole", async () => {
  await withManager(({ fm, emitted, sent }) => {
    fm.inbound("", { type: "feed", now: 400, buildId: 7, asks: [card(SID_L, 1)], ledgers: [ledger(SID_L, "web")] });
    const ws = attached(fm);
    let m = last(feeds(emitted));
    assert.deepEqual(m.ledgers.map((l: any) => [l.sid, l.name]),
      [[SID_L, "web"], [HOST + ":" + SID_A, HOST + ":api"], [HOST + ":" + SID_B, HOST + ":worker"]],
      "the full frame merges prefixed, as before");
    const before = feeds(emitted).length;
    ws.frame({ type: "feedDelta", now: 510, buildId: 2,
               asks: [card(SID_A, 2)], removeAsks: [SID_A + ":g1"],
               ledgers: [ledger(SID_A, "api", ["t1"])], removeLedgers: [SID_B] });
    assert.equal(feeds(emitted).length, before + 1, "the delta re-emits the merge once");
    m = last(feeds(emitted));
    assert.deepEqual(m.asks.map((a: any) => [a.itemId, a.sid, a.name]),
      [[SID_L + ":g1", SID_L, "web"], [SID_A + ":g2", HOST + ":" + SID_A, HOST + ":api"]],
      "the removed card left by its bare itemId, the new one arrived with its sid and name prefixed, the local card stands");
    assert.deepEqual(m.ledgers.map((l: any) => [l.sid, l.name, l.ledger.tops]),
      [[SID_L, "web", []], [HOST + ":" + SID_A, HOST + ":api", ["t1"]]],
      "the ledger removed by its bare sid is gone and the upserted one replaced its prefixed twin, not appended beside it");
    assert.deepEqual(m.working, [HOST + ":" + SID_A], "a non-keyed field carries over from the raw base, prefixed");
    assert.deepEqual(ws.sent, [], "nothing asked of the remote: the delta applied");
    assert.equal(sent.filter((x) => x && x.type === "needFullFeed").length, 0, "nothing asked of the local kernel either");
    assert.equal(sent.filter((x) => x && x.type === "clientDiag" && x.what === "feedDelta-nobase").length, 0);
    ws.frame({ type: "feedDelta", now: 520, buildId: 3, removeAsks: [SID_A + ":g2"], top: { working: [] } });
    m = last(feeds(emitted));
    assert.deepEqual(m.asks.map((a: any) => a.itemId), [SID_L + ":g1"], "a second delta applies onto the FIRST delta's result, not the stale full");
    assert.deepEqual(m.working, [], "`top` replaced the non-keyed fields");
    assert.deepEqual(m.ledgers.map((l: any) => l.sid), [SID_L, HOST + ":" + SID_A], "ledgers carry over when the delta names none");
    fm.conns.get(HOST).closed = true;
  });
});

test("a remote feedDelta with no full frame held asks THAT kernel for one on its own socket; the local kernel is not asked and nothing is emitted", async () => {
  await withManager(({ fm, emitted, sent }) => {
    fm.openRemote(HOST, true);
    const ws = FakeWS.made[0];
    ws.open();
    ws.frame({ type: "feedDelta", now: 510, buildId: 2, asks: [card(SID_A, 2)] });
    assert.deepEqual(ws.sent, [{ type: "needFullFeed" }], "the ask goes to the kernel that sent the delta: it forgets this socket's base and serves a full frame");
    assert.equal(sent.filter((x) => x && x.type === "needFullFeed").length, 0, "the local kernel holds no base for this host: not asked");
    const diag = sent.filter((x) => x && x.type === "clientDiag" && x.what === "feedDelta-nobase");
    assert.equal(diag.length, 1, "…and it says so, once");
    assert.equal(diag[0].data.host, HOST);
    assert.equal(feeds(emitted).length, 0, "nothing to apply onto, nothing emitted");
    ws.frame(remoteFull());   // the full frame the ask earns
    assert.equal(feeds(emitted).length, 1);
    assert.deepEqual(last(feeds(emitted)).ledgers.map((l: any) => l.sid), [HOST + ":" + SID_A, HOST + ":" + SID_B]);
    ws.frame({ type: "feedDelta", now: 520, buildId: 3, removeLedgers: [SID_B], ledgers: [] });
    assert.deepEqual(last(feeds(emitted)).ledgers.map((l: any) => l.sid), [HOST + ":" + SID_A], "the stream applies from the full frame on");
    assert.deepEqual(ws.sent, [{ type: "needFullFeed" }], "no second ask");
    fm.conns.get(HOST).closed = true;
  });
});

test("a detach forgets the host's raw base: the re-attached host's first delta finds none and asks its kernel", async () => {
  await withManager(({ fm, emitted }) => {
    attached(fm);
    assert.equal(feeds(emitted).length, 1);
    fm.closeRemote(HOST);
    assert.deepEqual(last(feeds(emitted)).asks, [], "the detach dropped the host's cards");
    fm.openRemote(HOST, true);
    const ws2 = last(FakeWS.made);
    assert.notEqual(ws2, FakeWS.made[0], "a fresh conn and socket");
    ws2.open();
    ws2.frame({ type: "feedDelta", now: 600, buildId: 9, asks: [card(SID_A, 3)] });
    assert.deepEqual(ws2.sent, [{ type: "needFullFeed" }], "the stale base did not survive the detach; the remote is asked for a full frame");
    fm.conns.get(HOST).closed = true;
  });
});

// A redial on the SAME conn (the onclose retry; the watchdog's abandon-and-dial takes the same connect() road) forgets the
// raw base with the dead socket, as connect() re-mints the slot receiver: the base is the socket's, and a new socket's
// first feed frame from every kernel in this repo is whole (a fresh client dict holds no last build), so this is pinned
// for the contract (federation-remote-view-delta.test.ts, the redial legs). FakeWS.close() fires no onclose, so the
// handler is called as a browser would and the redial it arms (a real 2 s timer under node) is run at once.
test("a redial on the same conn forgets the host's raw base with the dead socket: the replacement socket's first delta finds none and asks its kernel", async () => {
  await withManager(({ fm, emitted, sent }) => {
    const ws = attached(fm);
    ws.frame({ type: "feedDelta", now: 510, buildId: 2, asks: [card(SID_A, 2)], removeAsks: [SID_A + ":g1"] });
    assert.deepEqual(last(feeds(emitted)).asks.map((a: any) => a.itemId), [SID_A + ":g2"]);
    const before = feeds(emitted).length, conn = fm.conns.get(HOST);
    ws.readyState = 3;
    const timers = heldTimers(() => ws.onclose!({ code: 1006, wasClean: false }));
    assert.equal(timers.length, 1, "the close armed one redial");
    timers[0]();
    const ws2 = last(FakeWS.made);
    assert.notEqual(ws2, ws, "a fresh socket");
    assert.equal(fm.conns.get(HOST), conn, "…on the same conn");
    ws2.open();
    ws2.frame({ type: "feedDelta", now: 520, buildId: 3, asks: [card(SID_A, 3)] });   // continues the dead socket's stream
    assert.deepEqual(ws2.sent, [{ type: "needFullFeed" }], "no base on the new socket: that kernel is asked for a full frame on it");
    assert.deepEqual(sent.filter((x) => x && x.type === "clientDiag" && x.what === "feedDelta-nobase").map((x) => x.data), [{ host: HOST, buildId: 3 }], "one no-base row");
    assert.equal(feeds(emitted).length, before, "nothing emitted");
    assert.deepEqual(last(feeds(emitted)).asks.map((a: any) => a.itemId), [SID_A + ":g2"], "the merge stands where the dead socket left it");
    assert.deepEqual(ws.sent, [], "nothing on the dead socket");
    assert.equal(conn.feedRaw, undefined, "the mechanism: the raw base went with the dead socket, and the ask's full frame will seed a new one");
    fm.conns.get(HOST).closed = true;
  });
});

test("the local host's path is unchanged: a local delta applies onto the merge's frame, and a local no-base asks the local kernel, never a remote socket", async () => {
  await withManager(({ fm, emitted, sent }) => {
    const ws = attached(fm);
    fm.inbound("", { type: "feedDelta", now: 410, buildId: 8, asks: [card(SID_L, 1)] });
    assert.deepEqual(sent.filter((x) => x && x.type === "needFullFeed"), [{ type: "needFullFeed" }], "no local base yet: the local kernel is asked");
    assert.deepEqual(ws.sent, [], "…and the remote socket carries nothing for it");
    fm.inbound("", { type: "feed", now: 420, buildId: 9, asks: [card(SID_L, 1)], ledgers: [ledger(SID_L, "web")] });
    fm.inbound("", { type: "feedDelta", now: 430, buildId: 10, asks: [card(SID_L, 1, { text: "changed" })] });
    const m = last(feeds(emitted));
    assert.equal(m.asks.find((a: any) => a.sid === SID_L).text, "changed", "the local delta applied");
    assert.deepEqual(m.asks.map((a: any) => a.sid), [SID_L, HOST + ":" + SID_A], "beside the remote's frame");
    fm.conns.get(HOST).closed = true;
  });
});

// ── the ask's class (2026-09-19) ──────────────────────────────────────────────────────────────────────────────────────
// needFullFeed to a remote socket is the pane's own bookkeeping, held on the conn like needFull and needSlot and never
// toasted (BOOKKEEPING). This pins the CLASSIFICATION, not a road a browser reaches today: FakeWS.frame dispatches
// whatever the socket's readyState, where a spec-faithful socket never dispatches a message on a socket that is not
// OPEN, so a real page raises the ask only on the socket the delta just arrived on, which is open. Before the
// registration the same frame took the gesture arm: a warn toast naming the wire word, and a senddrop row.
test("a needFullFeed the remote socket cannot carry is held like its twins: no toast, one hostconn hold row, flushed on the open behind the ready; a host with no conn drops it with the breadcrumb alone", async () => {
  await withManager(({ fm, emitted, sent }) => {
    fm.outbound({ type: "ready", proto: 2 });   // the page's proto: the open posts a ready first, so the flush's place behind it is visible
    fm.openRemote(HOST, true);
    const ws = FakeWS.made[0];                  // left CONNECTING: no open()
    ws.frame({ type: "feedDelta", now: 510, buildId: 2, asks: [card(SID_A, 2)] });
    const warns = () => emitted.filter((m) => m && m.type === "warn");
    const rows = (what: string) => sent.filter((x) => x && x.type === "clientDiag" && x.what === what).map((x) => x.data);
    assert.deepEqual(warns(), [], "no toast: the user sent nothing for a toast to be about");
    assert.deepEqual(rows("senddrop"), [], "not a drop: held");
    assert.deepEqual(rows("hostconn").filter((d) => d.ev === "hold"), [{ host: HOST, ev: "hold", msgType: "needFullFeed", rs: 0 }],
      "held once, journaled in the hostconn family at the not-held to held transition");
    assert.equal(fm.conns.get(HOST).pending.size, 1);
    assert.deepEqual(rows("feedDelta-nobase"), [{ host: HOST, buildId: 2 }], "the no-base row still says why the ask was raised");
    assert.deepEqual(ws.sent, [], "nothing goes on a socket that is not open");
    ws.open();
    assert.deepEqual(ws.sent, [{ type: "ready", proto: 2 }, { type: "needFullFeed" }],
      "flushed on the open event itself, behind the ready (the ready is this socket's first word, federation.ts onopen 2026-09-18; the held ask rides right behind it, so the kernel serves a full frame at once, one extra full per reconnect at most, as a held needSlot does)");
    assert.deepEqual(last(rows("hostconn")), { host: HOST, ev: "open", flushed: ["needFullFeed"] }, "the open row names what flushed");
    assert.equal(fm.conns.get(HOST).pending.size, 0);
    assert.deepEqual(warns(), []);
    // a host this page holds no conn for (detached since the frame): nothing to hold it on, dropped with the breadcrumb alone
    fm.closeRemote(HOST);
    fm.applyRemoteFeedDelta(HOST, { type: "feedDelta", now: 520, buildId: 3, asks: [card(SID_A, 3)] });
    assert.deepEqual(rows("senddrop"), [{ host: HOST, msgType: "needFullFeed", why: "no-conn" }], "the no-conn drop names its why");
    assert.deepEqual(warns(), [], "and still no toast");
  });
});

// ── two hosts, overlapping names (2026-09-19) ─────────────────────────────────────────────────────────────────────────
// Session names and sids are not unique across hosts: a hub federating two boxes that both run a session called `api`
// (here even the same bare sid, the hardest case) must apply each host's delta onto THAT host's raw frame and nothing
// else. These pin that the raw base is each conn's own (Conn.feedRaw), not the feature: they are green at this head and
// red under the mutation that reads and writes the base through one slot shared by every conn (the store site and
// applyRemoteFeedDelta's read and write), which the single-host tests above cannot see (a review round found that a "host B untouched after host
// A's delta" case stays green under it: only DIFFERENT content per host, and a no-base leg with one host holding a base
// and the other none, make the collapse visible). Asserted by prefixed sid, never by position: mergeHostFeeds
// concatenates per host in hostSeq order.
const HOST_A = "TESTHOSTA";
const HOST_B = "TESTHOSTB";
const SID_S = "11111111-2222-4333-8444-000000000901";   // "api" on BOTH hosts
const cardOn = (n: number, text: string) => ({ itemId: SID_S + ":g" + n, sid: SID_S, name: "api", text, t: 1000 - n, column: "working" });
const fullA = () => ({ type: "feed", now: 500, buildId: 1, asks: [cardOn(1, "goal 1 on A")], working: [SID_S], ledgers: [ledger(SID_S, "api", ["tA"])] });
const fullB = () => ({ type: "feed", now: 500, buildId: 1, asks: [cardOn(3, "goal 3 on B")], working: [], ledgers: [ledger(SID_S, "api", ["tB"])] });
const asksOf = (m: any, host: string) => m.asks.filter((a: any) => a.sid === host + ":" + SID_S).map((a: any) => a.itemId);
const topsOf = (m: any, host: string) => m.ledgers.filter((l: any) => l.sid === host + ":" + SID_S).map((l: any) => l.ledger.tops);

// dial, open, and hand the socket that host's first full frame; returns the socket
function attachedAs(fm: any, host: string, full: any): FakeWS {
  fm.openRemote(host, true);
  const ws = last(FakeWS.made);
  ws.open();
  ws.frame(full);
  return ws;
}

test("two hosts with the same session name and sid: each host's rows move only on its own deltas, applied onto its own raw frame", async () => {
  await withManager(({ fm, emitted, sent }) => {
    const wsA = attachedAs(fm, HOST_A, fullA());
    const wsB = attachedAs(fm, HOST_B, fullB());
    let m = last(feeds(emitted));
    assert.deepEqual([asksOf(m, HOST_A), asksOf(m, HOST_B)], [[SID_S + ":g1"], [SID_S + ":g3"]], "both hosts' cards merged, each under its own prefix");
    wsA.frame({ type: "feedDelta", now: 510, buildId: 2, asks: [cardOn(2, "goal 2 on A")], removeAsks: [SID_S + ":g1"], ledgers: [ledger(SID_S, "api", ["tA2"])] });
    m = last(feeds(emitted));
    assert.deepEqual(asksOf(m, HOST_A), [SID_S + ":g2"], "A's delta replaced A's card");
    assert.deepEqual(asksOf(m, HOST_B), [SID_S + ":g3"], "…and left B's, the same bare sid, alone");
    assert.deepEqual([topsOf(m, HOST_A), topsOf(m, HOST_B)], [[["tA2"]], [["tB"]]], "A's ledger moved, B's stands");
    assert.deepEqual(m.working, [HOST_A + ":" + SID_S], "the non-keyed fields came from A's own raw base");
    assert.deepEqual([wsA.sent, wsB.sent], [[], []], "nothing asked of either kernel");
    assert.deepEqual(fm.conns.get(HOST_A).feedRaw.asks.map((a: any) => a.itemId), [SID_S + ":g2"], "A's conn's raw base advanced (bare ids: the base is the conn's, so the host's)");
    assert.deepEqual(fm.conns.get(HOST_B).feedRaw.asks.map((a: any) => a.itemId), [SID_S + ":g3"], "B's is untouched");
    // B's turn: ledgers: [] beside removeLedgers, since applyFeedDelta applies ledger removals only when `ledgers` is an array
    wsB.frame({ type: "feedDelta", now: 520, buildId: 2, removeAsks: [SID_S + ":g3"], ledgers: [], removeLedgers: [SID_S] });
    m = last(feeds(emitted));
    assert.deepEqual([asksOf(m, HOST_B), topsOf(m, HOST_B)], [[], []], "B's rows are gone");
    assert.deepEqual([asksOf(m, HOST_A), topsOf(m, HOST_A)], [[SID_S + ":g2"], [["tA2"]]], "A's are as A's delta left them");
    assert.deepEqual([wsA.sent, wsB.sent], [[], []]);
    assert.equal(sent.filter((x) => x && x.type === "clientDiag" && x.what === "feedDelta-nobase").length, 0);
    fm.conns.get(HOST_A).closed = true; fm.conns.get(HOST_B).closed = true;
  });
});

test("two hosts, one base: a delta from the host with no full frame held asks THAT host alone, and the other host's base is not applied onto", async () => {
  await withManager(({ fm, emitted, sent }) => {
    const wsA = attachedAs(fm, HOST_A, fullA());
    fm.openRemote(HOST_B, true);
    const wsB = last(FakeWS.made);
    wsB.open();                                  // no full frame from B
    const before = feeds(emitted).length;
    wsB.frame({ type: "feedDelta", now: 510, buildId: 2, asks: [cardOn(4, "goal 4 on B")] });
    assert.deepEqual(wsB.sent, [{ type: "needFullFeed" }], "B's kernel is asked for a full frame on B's socket");
    assert.deepEqual(wsA.sent, [], "A's is not");
    assert.equal(sent.filter((x) => x && x.type === "needFullFeed").length, 0, "nor the local kernel");
    const nobase = sent.filter((x) => x && x.type === "clientDiag" && x.what === "feedDelta-nobase");
    assert.deepEqual(nobase.map((x) => x.data.host), [HOST_B], "one no-base row, naming B");
    assert.equal(feeds(emitted).length, before, "nothing emitted: B's delta was not applied onto A's base");
    const m = last(feeds(emitted));
    assert.deepEqual([asksOf(m, HOST_A), asksOf(m, HOST_B)], [[SID_S + ":g1"], []], "the merge carries A's rows only");
    assert.deepEqual(fm.conns.get(HOST_A).feedRaw.asks.map((a: any) => a.itemId), [SID_S + ":g1"], "A's raw base is as A's full left it");
    fm.conns.get(HOST_A).closed = true; fm.conns.get(HOST_B).closed = true;
  });
});

test("two hosts: detaching one drops its raw base and leaves the other's; the re-attached host's first delta asks on its NEW socket only", async () => {
  await withManager(({ fm, emitted }) => {
    const wsA = attachedAs(fm, HOST_A, fullA());
    const wsB = attachedAs(fm, HOST_B, fullB());
    const connB = fm.conns.get(HOST_B);
    fm.closeRemote(HOST_B);
    assert.equal(fm.conns.has(HOST_B), false, "B's conn went with B");
    assert.equal(connB.feedRaw, undefined, "…and its raw base with it");
    assert.deepEqual(fm.conns.get(HOST_A).feedRaw.asks.map((a: any) => a.itemId), [SID_S + ":g1"], "A's raw base survived B's detach");
    wsA.frame({ type: "feedDelta", now: 530, buildId: 3, asks: [cardOn(1, "goal 1 on A, edited")] });
    assert.deepEqual(wsA.sent, [], "A's next delta applied onto A's base: nothing asked");
    let m = last(feeds(emitted));
    assert.deepEqual(m.asks.map((a: any) => [a.sid, a.text]), [[HOST_A + ":" + SID_S, "goal 1 on A, edited"]], "A's card moved and no B row remains");
    fm.openRemote(HOST_B, true);
    const wsB2 = last(FakeWS.made);
    assert.notEqual(wsB2, wsB, "a fresh conn and socket for B");
    wsB2.open();
    wsB2.frame({ type: "feedDelta", now: 540, buildId: 2, asks: [cardOn(5, "goal 5 on B")] });
    assert.deepEqual(wsB2.sent, [{ type: "needFullFeed" }], "B's first delta on the new socket finds no base and asks B's kernel");
    assert.deepEqual([wsA.sent, wsB.sent], [[], []], "…on that socket alone");
    m = last(feeds(emitted));
    assert.deepEqual(asksOf(m, HOST_A), [SID_S + ":g1"], "A's rows stand throughout");
    fm.conns.get(HOST_A).closed = true; fm.conns.get(HOST_B).closed = true;
  });
});

// ── the late retry timers against the feed base (2026-09-19, review round 5) ────────────────────────────────────────
// A 2 s retry timer (the onclose redial a dead socket armed, or the constructor-throw retry) calls connect() without
// looking first, so it can land on a conn that is detached, marked down by the poll, or already holding a live
// replacement socket: connect() returns at its guards, and the per-dial reset sits below them. The raw feed base is the
// CONN's (Conn.feedRaw), so such a call can only ever reach the conn it was called for. These legs pin both for the feed
// half, as federation-remote-view-delta.test.ts's two late-timer legs (19 and 20 at this head: the onclose retry landing
// after the watchdog redialed, and the constructor-throw retry) pin the bars half at the connecting/open guard. The one road
// that crosses conns: closeRemote cancels no timer, so a DETACHED conn's redial fires after the host was re-attached on a
// NEW Conn whose socket has seeded a base by then. While the base was keyed by host (before round 5), a reset above the
// guards would have deleted the live conn's base through the dead conn's call, and no per-conn assertion could see it:
// the first two legs are red under a mutant that keys the base by host again and moves the reset to the top of connect(),
// and green under the top placement alone, which states the design (a dead conn's call reaches a dead conn's field). The
// last two are red under the top placement alone: there the call is the live conn's own.
test("a detached conn's late onclose redial cannot touch the re-attached conn's raw feed base: nothing dialed for the dead conn, and the new conn's next delta applies with nothing asked", async () => {
  await withManager(({ fm, emitted, sent }) => {
    const ws = attached(fm);
    const connA = fm.conns.get(HOST);
    ws.readyState = 3;
    const timers = heldTimers(() => ws.onclose!({ code: 1006, wasClean: false }));   // the socket dropped: its 2 s redial, held
    assert.equal(timers.length, 1, "the drop armed one redial on conn A");
    fm.closeRemote(HOST);   // /tunnels stopped listing the host: the conn is detached, its timer still armed
    assert.equal(connA.closed, true);
    assert.equal(fm.conns.has(HOST), false, "the detach dropped the conn");
    assert.equal(connA.feedRaw, undefined, "…and its raw base with it");
    fm.openRemote(HOST, true);   // the next poll lists the host again: a NEW conn
    const ws2 = last(FakeWS.made), connB = fm.conns.get(HOST);
    assert.notEqual(connB, connA, "a fresh conn");
    assert.notEqual(ws2, ws, "and a fresh socket");
    ws2.open();
    ws2.frame(remoteFull());
    assert.ok(connB.feedRaw, "the new socket's full frame seeded the new conn's base (the value the leg turns on)");
    const vdB = connB.viewDeltas, made = FakeWS.made.length, before = feeds(emitted).length;
    timers[0]();   // the dead conn's redial lands: connect() on a conn that is closed
    assert.equal(FakeWS.made.length, made, "nothing dialed for the dead conn");
    assert.equal(connB.ws, ws2, "the live conn's socket stands");
    assert.ok(connB.feedRaw, "the live conn's base stands");
    ws2.frame({ type: "feedDelta", now: 620, buildId: 5, asks: [card(SID_A, 4)] });
    assert.deepEqual(ws2.sent, [], "nothing asked: the delta applied onto the live conn's base");
    assert.deepEqual(diagRows(sent, "feedDelta-nobase"), [], "no no-base row");
    assert.equal(feeds(emitted).length, before + 1, "the merge moved once");
    assert.deepEqual(last(feeds(emitted)).asks.map((a: any) => a.itemId).sort(), [SID_A + ":g1", SID_A + ":g4"].sort());
    assert.equal(connB.viewDeltas, vdB, "the mechanism: the dead conn's call minted nothing on the live conn");
    assert.deepEqual(ws.sent, [], "nothing on the dead socket");
    fm.conns.get(HOST).closed = true;
  });
});

test("the constructor-throw retry of a detached conn: the same, on the other timer", async () => {
  await withManager(({ fm, emitted, sent }) => {
    // the first dial's constructor throws once (a browser refusing the URL), so connect() arms its 2 s retry on conn A,
    // which holds no socket at all
    const g: any = globalThis;
    const Fake = g.WebSocket;
    g.WebSocket = function () { g.WebSocket = Fake; throw new Error("refused"); };
    const retries = heldTimers(() => fm.openRemote(HOST, true));
    const connA = fm.conns.get(HOST);
    assert.equal(retries.length, 1, "the constructor-throw retry, held");
    assert.equal(connA.ws, null, "no socket on conn A");
    fm.closeRemote(HOST);
    assert.equal(fm.conns.has(HOST), false);
    fm.openRemote(HOST, true);   // re-attached: the constructor answers now
    const ws2 = last(FakeWS.made), connB = fm.conns.get(HOST);
    assert.notEqual(connB, connA, "a fresh conn");
    ws2.open();
    ws2.frame(remoteFull());
    assert.ok(connB.feedRaw, "seeded");
    const vdB = connB.viewDeltas, made = FakeWS.made.length, before = feeds(emitted).length;
    retries[0]();   // the dead conn's retry lands
    assert.equal(FakeWS.made.length, made, "nothing dialed for the dead conn");
    assert.equal(connB.ws, ws2);
    ws2.frame({ type: "feedDelta", now: 620, buildId: 5, asks: [card(SID_A, 4)] });
    assert.deepEqual(ws2.sent, [], "nothing asked: the live conn's base stood");
    assert.deepEqual(diagRows(sent, "feedDelta-nobase"), []);
    assert.equal(feeds(emitted).length, before + 1);
    assert.equal(connB.viewDeltas, vdB);
    fm.conns.get(HOST).closed = true;
  });
});

test("a late redial on a conn whose /tunnels row went down keeps the open socket's base: poll() marks the conn down without closing its socket, frames still arrive, and the call returns at the first guard", async () => {
  await withManager(({ fm, emitted, sent }) => {
    const ws = attached(fm);
    const conn = fm.conns.get(HOST);
    ws.readyState = 3;
    const timers = heldTimers(() => ws.onclose!({ code: 1006, wasClean: false }));
    clock += REMOTE_REDIAL_MS + 1000;
    fm.watchdog(clock);   // the redial verdict on the CLOSED socket dials the conn a fresh socket before the timer lands
    const ws2 = last(FakeWS.made);
    assert.notEqual(ws2, ws, "the watchdog redialed");
    ws2.open();
    ws2.frame(remoteFull());
    ws2.frame({ type: "feedDelta", now: 610, buildId: 2, asks: [card(SID_A, 2)] });
    assert.deepEqual(ws2.sent, [], "the new socket's base took a delta");
    conn.live = false;   // what poll() does on a row that reads down: the socket is left as it is
    const before = feeds(emitted).length, vd = conn.viewDeltas;
    timers[0]();   // the late timer: connect() on a conn that is not live, its socket OPEN
    assert.equal(conn.ws, ws2, "no new socket: the guard returned");
    ws2.frame({ type: "feedDelta", now: 620, buildId: 3, asks: [card(SID_A, 3)] });
    assert.deepEqual(ws2.sent, [], "nothing asked: the open socket's base stood through the late call");
    assert.deepEqual(diagRows(sent, "feedDelta-nobase"), []);
    assert.equal(feeds(emitted).length, before + 1, "the delta re-emitted the merge");
    assert.equal(conn.viewDeltas, vd, "the mechanism: a call that dialed nothing minted nothing");
    conn.closed = true;
  });
});

test("late timers on a conn whose own replacement socket is CONNECTING, then OPEN: the call returns at the connecting/open guard, and the open socket's base stands", async () => {
  await withManager(({ fm, emitted, sent }) => {
    const ws = attached(fm);
    const conn = fm.conns.get(HOST);
    ws.readyState = 3;
    const t1 = heldTimers(() => ws.onclose!({ code: 1006, wasClean: false }));   // the onclose redial, held
    clock += REMOTE_REDIAL_MS + 1000;
    const g: any = globalThis;
    const Fake = g.WebSocket;
    g.WebSocket = function () { g.WebSocket = Fake; throw new Error("refused"); };
    const t2 = heldTimers(() => fm.watchdog(clock));   // the redial verdict dials and the constructor throws once: the retry, held
    assert.equal(t2.length, 1, "the constructor-throw retry, held");
    assert.equal(conn.ws, ws, "the dead socket still on the conn");
    clock += REMOTE_REDIAL_MS + 1000;
    fm.watchdog(clock);   // the next verdict: the constructor answers
    const ws2 = last(FakeWS.made);
    assert.notEqual(ws2, ws, "a fresh socket");
    assert.equal(ws2.readyState, 0, "CONNECTING");
    const made = FakeWS.made.length;
    t1[0]();   // the onclose redial lands while the replacement is CONNECTING: nothing to wipe yet, and no second dial
    assert.equal(FakeWS.made.length, made, "no second dial");
    assert.equal(conn.ws, ws2);
    ws2.open();
    ws2.frame(remoteFull());
    ws2.frame({ type: "feedDelta", now: 610, buildId: 2, asks: [card(SID_A, 2)] });
    assert.deepEqual(ws2.sent, [], "the new socket's base took a delta");
    const before = feeds(emitted).length, vd = conn.viewDeltas;
    t2[0]();   // the constructor-throw retry lands with the socket OPEN
    assert.equal(conn.ws, ws2, "no new socket");
    ws2.frame({ type: "feedDelta", now: 620, buildId: 3, asks: [card(SID_A, 3)] });
    assert.deepEqual(ws2.sent, [], "nothing asked: the live socket's base stood through the late call");
    assert.deepEqual(diagRows(sent, "feedDelta-nobase"), []);
    assert.equal(feeds(emitted).length, before + 1);
    assert.equal(conn.viewDeltas, vd);
    conn.closed = true;
  });
});

// ── the held pair across a redial (2026-09-19) ───────────────────────────────────────────────────────────────────────
// A kernel that stamps its frames (gen on the full and on each feedDelta) leaves the conn's raw base a pair (Conn.feedHeld):
// (gen, 0) at the full, advanced by each delta that applies. connect()'s per-dial reset is gated per base, so a base holding
// a pair survives the redial and remoteDialUrl writes it as held:feed:<gen>.<rev> beside REMOTE_DIAL_CAPS, on both redial
// roads, with reconnect=1 and without, and the remote composes the feed from the declared rev instead of serving it whole.
// A base holding no gen (every kernel in this repo today) is reset as before and declares nothing (tests 5 and 8 above
// stand unchanged). The pair is read from the base alone: the page's own terms may carry a held:feed member (the pair the
// page holds for its LOCAL kernel) and it never reaches a remote dial. The composed frame that answers a declaration (base
// r, rev R, through R, gen g, newGen g2) applies onto the surviving base; a stamped delta whose gen differs, or whose base
// is above the held rev, posts needFullFeed carrying the held pair on the arriving conn and applies nothing. The gens
// are in the kernel's form (view-deltas.ts genOf): the boot's 16-hex token, '-', a decimal counter; strings, never numbers.
const GEN_STAMP = "0123456789abcdef";
const G = GEN_STAMP + "-7", G2 = GEN_STAMP + "-9", G3 = GEN_STAMP + "-11";
const stamped = (over: Record<string, unknown> = {}) => ({ ...remoteFull(), gen: G, ...over });
/** a per-cycle stamped delta from rev `base` to `base + 1`: card n set, in the stamping kernel's per-cycle shape, through
 *  equal to rev (every stamped delta carries through; one carrying none is refused: the no-through case below) */
const cycle = (gen: string, base: number, n: number) => ({ type: "feedDelta", gen, base, rev: base + 1, through: base + 1, now: 510 + n, buildId: 10 + n, asks: [card(SID_A, n)] });
/** the page's terms carrying its LOCAL kernel's held pair and its hold words: none of it is a remote dial's */
const pageTerms = () => ({ ...terms(), proto: 2, caps: "feedDelta,readyGate,held:feed:1.1" });
const heldOf = (fm: any) => fm.conns.get(HOST).feedHeld;

test("a conn whose raw base holds a pair redials declaring it on the onclose road: caps=feedDelta,held:feed:g.r beside reconnect=1, g.r the conn's applied pair and not the page's, no held:bars; the composed feedDelta that answers applies onto the surviving base and moves the pair to (newGen, through)", async () => {
  await withManager(({ fm, emitted, sent }) => {
    fm.outbound({ type: "ready", proto: 2 });
    fm.openRemote(HOST, true);
    const ws = last(FakeWS.made), conn = fm.conns.get(HOST);
    assert.equal(qOf(ws.url).get("caps"), "feedDelta", "the first dial: no base yet, nothing declared");
    ws.open();
    ws.frame({ type: "caps" });   // the remote acked the page's ready: a later dial is a redial
    ws.frame(stamped());
    assert.deepEqual(heldOf(fm), { gen: G, rev: 0 }, "the stamped full leaves the pair (gen, 0)");
    ws.frame(cycle(G, 0, 2));
    assert.deepEqual(heldOf(fm), { gen: G, rev: 1 }, "a per-cycle stamped delta advances it to (gen, rev)");
    assert.deepEqual(last(feeds(emitted)).asks.map((a: any) => a.itemId).sort(), [SID_A + ":g1", SID_A + ":g2"].sort());
    const before = feeds(emitted).length;
    ws.readyState = 3;
    const timers = heldTimers(() => ws.onclose!({ code: 1006, wasClean: false }));
    assert.equal(timers.length, 1);
    timers[0]();
    const ws2 = last(FakeWS.made);
    assert.notEqual(ws2, ws, "a fresh socket");
    assert.equal(fm.conns.get(HOST), conn, "…on the same conn");
    const q = qOf(ws2.url);
    assert.equal(q.get("caps"), "feedDelta,held:feed:" + G + ".1", "the redial declares the conn's pair beside the decoder word: not the page's held:feed:1.1, and no held:bars (a feed conn holds no bars base)");
    assert.equal(q.get("reconnect"), "1");
    assert.equal(q.get("delta"), "1", "the page's terms ride as before");
    assert.ok(conn.feedRaw, "the mechanism: the gen-holding base survived the redial");
    assert.deepEqual(heldOf(fm), { gen: G, rev: 1 });
    ws2.open();
    assert.deepEqual(ws2.sent, [], "a redial posts no ready");
    // the composed frame the declaration earns: everything from rev 1 through 4 in one delta, stamped with the new generation
    ws2.frame({ type: "feedDelta", gen: G, newGen: G2, base: 1, rev: 4, through: 4, now: 600, buildId: 20, asks: [card(SID_A, 5)], removeAsks: [SID_A + ":g2"] });
    assert.equal(feeds(emitted).length, before + 1, "the composed frame applied onto the surviving base and the merge moved once");
    assert.deepEqual(last(feeds(emitted)).asks.map((a: any) => [a.itemId, a.sid]).sort(), [[SID_A + ":g1", HOST + ":" + SID_A], [SID_A + ":g5", HOST + ":" + SID_A]].sort(), "the merge reads the result prefixed");
    assert.deepEqual(ws2.sent, [], "nothing asked: no needFullFeed");
    assert.deepEqual(diagRows(sent, "feedDelta-nobase"), []);
    assert.deepEqual(diagRows(sent, "feedDelta-stale"), []);
    assert.deepEqual(heldOf(fm), { gen: G2, rev: 4 }, "the pair is (newGen, through)");
    ws2.frame(cycle(G2, 4, 6));
    assert.deepEqual(heldOf(fm), { gen: G2, rev: 5 }, "and the stream continues under the new generation");
    fm.conns.get(HOST).closed = true;
  }, { terms: pageTerms });
});

test("the watchdog's abandon-and-dial declares the same pair, without reconnect when the remote never acked the ready: the member rides a first dial's shape too", async () => {
  await withManager(({ fm }) => {
    fm.openRemote(HOST, true);   // no ready posted, no caps frame: the redial gate stays shut
    const ws = last(FakeWS.made), conn = fm.conns.get(HOST);
    ws.open();
    ws.frame(stamped());
    ws.frame(cycle(G, 0, 2));
    ws.frame(cycle(G, 1, 3));
    assert.deepEqual(heldOf(fm), { gen: G, rev: 2 });
    clock += REMOTE_STALE_MS + 1000;   // an OPEN socket quiet past the stale bound: the watchdog abandons it and dials
    fm.watchdog(clock);
    assert.equal(ws.onclose, null, "the watchdog abandoned the quiet socket");
    const ws2 = last(FakeWS.made);
    assert.notEqual(ws2, ws);
    assert.equal(fm.conns.get(HOST), conn);
    const q = qOf(ws2.url);
    assert.equal(q.get("caps"), "feedDelta,held:feed:" + G + ".2", "declared without reconnect: a kernel that stamps its frames reads the member at the compose on either dial; no kernel in this repo stamps a gen yet, so nothing declares one today");
    assert.equal(q.get("reconnect"), null);
    assert.ok(conn.feedRaw, "the base survived");
    fm.conns.get(HOST).closed = true;
  }, { terms: pageTerms });
});

test("a stamped delta whose gen differs, or whose base is above the held rev, or whose through is below it or carrying no through, posts needFullFeed carrying the held pair on the arriving conn and applies nothing; the feedDelta-stale row names the cause (gen, ahead, behind, through: a word per field failure and a word per relation); the full the ask earns re-seeds the pair", async () => {
  await withManager(({ fm, emitted, sent }) => {
    const ws = attached(fm);   // a gen-less full first: the pair is absent
    assert.equal(heldOf(fm), undefined);
    ws.frame(stamped({ buildId: 2 }));
    ws.frame(cycle(G, 0, 2));
    assert.deepEqual(heldOf(fm), { gen: G, rev: 1 });
    const before = feeds(emitted).length, raw = fm.conns.get(HOST).feedRaw;
    ws.frame({ type: "feedDelta", gen: GEN_STAMP + "-8", base: 1, rev: 2, now: 520, buildId: 30, asks: [card(SID_A, 9)] });
    assert.deepEqual(ws.sent, [{ type: "needFullFeed", gen: G, rev: 1 }], "another generation: the ask carries the held pair, for the kernel to compose from");
    ws.frame({ type: "feedDelta", gen: G, base: 3, rev: 4, now: 521, buildId: 31, asks: [card(SID_A, 9)] });
    assert.equal(ws.sent.length, 2, "a base above the held rev: asked again");
    assert.deepEqual(last(ws.sent), { type: "needFullFeed", gen: G, rev: 1 });
    ws.frame({ type: "feedDelta", gen: G, base: 0, rev: 1, through: 0, now: 522, buildId: 32, asks: [card(SID_A, 9)] });
    assert.equal(ws.sent.length, 3, "a composed frame reaching below the held rev: asked again");
    ws.frame({ type: "feedDelta", gen: G, base: 1, rev: 2, now: 523, buildId: 33, asks: [card(SID_A, 9)] });   // no through: every stamped delta carries it
    assert.equal(ws.sent.length, 4, "a stamped delta carrying no through: asked again");
    ws.frame({ type: "feedDelta", gen: G, base: 0, rev: 1.5, through: 0, now: 524, buildId: 34, asks: [card(SID_A, 9)] });   // below the held rev AND a rev that is no safe integer
    assert.equal(ws.sent.length, 5, "a frame below the held rev with a bad rev: asked again");
    // the base field's own failure, a base that is no safe integer, on a frame whose base is NOT above the held rev and whose
    // other fields pass (round 4, tests-2): a non-integer base above the held rev would read "base" on the relation's arm
    // too under a ladder that lost the integer test (JS coercion makes 1.5 > 1 true), so that frame cannot pin the test;
    // this one can, since without it the frame falls through to "disagree"
    ws.frame({ type: "feedDelta", gen: G, base: 0.5, rev: 1, through: 1, now: 525, buildId: 35, asks: [card(SID_A, 9)] });
    assert.equal(ws.sent.length, 6, "a base that is no safe integer: asked again");
    assert.deepEqual(diagRows(sent, "feedDelta-stale"), [{ host: HOST, buildId: 30, why: "gen" }, { host: HOST, buildId: 31, why: "ahead" }, { host: HOST, buildId: 32, why: "behind" }, { host: HOST, buildId: 33, why: "through" }, { host: HOST, buildId: 35, why: "base" }],
                     "a field's word for a field's own failure (gen; through not carried; a base that is no safe integer) and a relation's word for a relation's (ahead: the base above the held rev; behind: the through below it), the gate's tests in order: a frame below the held rev reads behind whatever its rev (round 4: base and through each carried a relation under their field's word); the row is latched on its word, so the second behind (buildId 34) files no row while its ask was sent");
    assert.equal(feeds(emitted).length, before, "nothing applied, nothing emitted");
    assert.equal(fm.conns.get(HOST).feedRaw, raw, "the base stands");
    assert.deepEqual(heldOf(fm), { gen: G, rev: 1 }, "…and the pair with it");
    assert.deepEqual(diagRows(sent, "feedDelta-nobase"), [], "not a no-base: a base is held");
    assert.equal(sent.filter((x) => x && x.type === "needFullFeed").length, 0, "the local kernel is not asked");
    // the full the ask earns, stamped with the kernel's new generation: the pair re-seeds and the stream applies from it
    ws.frame(stamped({ gen: G3, buildId: 40 }));
    assert.deepEqual(heldOf(fm), { gen: G3, rev: 0 });
    ws.frame(cycle(G3, 0, 4));
    assert.deepEqual(heldOf(fm), { gen: G3, rev: 1 });
    assert.equal(ws.sent.length, 6, "no further ask");
    fm.conns.get(HOST).closed = true;
  });
});

test("the vintage guard: a delta carrying no gen applies onto a base holding none and moves no pair, and that conn's redial declares nothing; a full carrying no gen after a gen-holding pair clears the pair and the next dial carries no held:feed; a stamped delta onto that pair-less base is refused with why unpaired and a bare needFullFeed carrying no gen and no rev", async () => {
  await withManager(({ fm, emitted, sent }) => {
    const ws = attached(fm);
    assert.equal(heldOf(fm), undefined, "a full carrying no gen (every kernel in this repo today) leaves no pair");
    ws.frame({ type: "feedDelta", now: 510, buildId: 2, asks: [card(SID_A, 2)] });
    assert.deepEqual(last(feeds(emitted)).asks.map((a: any) => a.itemId).sort(), [SID_A + ":g1", SID_A + ":g2"].sort(), "the gen-less delta applied on the base's presence alone");
    assert.deepEqual(ws.sent, []);
    assert.equal(heldOf(fm), undefined, "…and moved no pair");
    ws.readyState = 3;
    const timers = heldTimers(() => ws.onclose!({ code: 1006, wasClean: false }));
    timers[0]();
    const ws2 = last(FakeWS.made);
    assert.equal(qOf(ws2.url).get("caps"), "feedDelta", "a gen-less base declares nothing: the redial is undeclared, as every remote redial is until the kernel stamps its frames");
    assert.equal(fm.conns.get(HOST).feedRaw, undefined, "and the gen-less base was reset with the dead socket, as before");
    ws2.open();
    ws2.frame(stamped());
    ws2.frame(cycle(G, 0, 3));
    assert.deepEqual(heldOf(fm), { gen: G, rev: 1 });
    ws2.frame(remoteFull());   // a full carrying no gen after a gen-holding pair: a kernel rolled back to one before the stamp
    assert.equal(heldOf(fm), undefined, "the pair is cleared by the gen-less full");
    assert.ok(fm.conns.get(HOST).feedRaw, "the base is the new full");
    // the ladder's first arm and the pair-less ask (round 4, tests-1): a stamped delta onto a base holding no pair is refused
    // with the pair's word, and the ask carries no gen and no rev, since none is held to declare
    const before2 = feeds(emitted).length, raw2 = fm.conns.get(HOST).feedRaw, asked = ws2.sent.length;
    ws2.frame(cycle(G, 0, 4));
    assert.deepEqual(ws2.sent.slice(asked), [{ type: "needFullFeed" }], "the bare ask: no gen, no rev");
    assert.deepEqual(diagRows(sent, "feedDelta-stale"), [{ host: HOST, buildId: 14, why: "unpaired" }], "the pair's word: no pair is held for a stamped stream");
    assert.equal(feeds(emitted).length, before2, "nothing applied");
    assert.equal(fm.conns.get(HOST).feedRaw, raw2, "the base stands");
    assert.equal(heldOf(fm), undefined, "and still no pair");
    ws2.readyState = 3;
    const timers2 = heldTimers(() => ws2.onclose!({ code: 1006, wasClean: false }));
    timers2[0]();
    assert.equal(qOf(last(FakeWS.made).url).get("caps"), "feedDelta", "the next dial carries no held:feed");
    fm.conns.get(HOST).closed = true;
  }, { terms: pageTerms });
});

// The feed road's reading of the same shape the bars test pins (round 3, the fixer's pass, 2026-09-20): a delta carrying
// newGen and through but no gen is a gen-less delta, applied on the base's presence alone, and moves no pair, so the two
// roads agree that a newGen rides only a frame whose gen the gate matched.
test("a feedDelta carrying newGen and through but no gen applies as a gen-less delta and moves no pair: the held pair stands and the redial declares it, never the newGen", async () => {
  await withManager(({ fm, emitted }) => {
    const ws = attached(fm);
    ws.frame(stamped());
    ws.frame(cycle(G, 0, 2));
    assert.deepEqual(heldOf(fm), { gen: G, rev: 1 });
    const before = feeds(emitted).length;
    ws.frame({ type: "feedDelta", newGen: G2, base: 1, rev: 4, through: 4, now: 530, buildId: 60, asks: [card(SID_A, 9)] });
    assert.deepEqual(ws.sent, [], "applied: nothing asked");
    assert.equal(feeds(emitted).length, before + 1, "emitted once");
    assert.deepEqual(heldOf(fm), { gen: G, rev: 1 }, "no gen on the frame, so the pair does not move: the newGen is not adopted");
    ws.readyState = 3;
    const timers = heldTimers(() => ws.onclose!({ code: 1006, wasClean: false }));
    timers[0]();
    assert.equal(qOf(last(FakeWS.made).url).get("caps"), "feedDelta,held:feed:" + G + ".1", "the redial declares the held pair, never the newGen");
    fm.conns.get(HOST).closed = true;
  });
});

// One base is the real shape: the kernel serves the feed payload to a feed-riding app's socket and the bars to a timeline's,
// and each conn dials with one app, so a feed conn holds feedRaw and never a bars base and a timeline conn the reverse. The
// two-base state is a harness construction (inbound stores a feed frame on any manager, and the receiver seeds a bars base
// on any conn), checked for the shape of the members alone: each written from its own base, in this order.
const SEP = String.fromCharCode(31);
const remoteBarsStamped = (gen: string) => ({ type: "bars", gen, turns: { [SID_A]: [{ id: "seg-1", start: 1000, end: 1005, q: "first" }] }, judging: {}, messages: [], now: 500, warming: false });
const barsCycle = (gen: string, base: number, id: string) => ({ type: "delta", slot: "bars", gen, base, rev: base + 1, coll: { turns: { set: { [SID_A + SEP + id]: { id, start: 1010, end: 1015, q: "next" } } } }, rest: { now: 505 } });

test("the both-gen shape check: a conn whose raw feed base and receiver bars base each hold a pair redials with held:feed:g.r and held:bars:g.r both, each from its own base; the composed frames that answer apply onto each surviving base with nothing asked", async () => {
  await withManager(({ fm, emitted }) => {
    fm.openRemote(HOST, true);
    const ws = last(FakeWS.made), conn = fm.conns.get(HOST);
    ws.open();
    ws.frame(stamped());
    ws.frame(cycle(G, 0, 2));
    ws.frame(remoteBarsStamped(G));
    ws.frame(barsCycle(G, 0, "seg-2"));
    ws.frame(barsCycle(G, 1, "seg-3"));
    assert.deepEqual(heldOf(fm), { gen: G, rev: 1 });
    assert.deepEqual(conn.viewDeltas.held("bars"), { gen: G, rev: 2 }, "the receiver's one read: the bars base's pair");
    assert.deepEqual(conn.viewDeltas.held("feed"), { gen: G, rev: 0 }, "the receiver's feed slot is seeded by every remote full and never patched on a feedDelta conn (it goes with the receiver); the dial's held:feed is the RAW base's pair at rev 1, not this rev 0");
    const vd = conn.viewDeltas, before = feeds(emitted).length;
    ws.readyState = 3;
    const timers = heldTimers(() => ws.onclose!({ code: 1006, wasClean: false }));
    timers[0]();
    const ws2 = last(FakeWS.made);
    assert.equal(qOf(ws2.url).get("caps"), "feedDelta,held:feed:" + G + ".1,held:bars:" + G + ".2", "both members, each its own base's pair, in this order");
    assert.equal(conn.viewDeltas, vd, "the receiver survived: its bars base holds a gen");
    assert.ok(conn.feedRaw, "the raw base survived: it holds a gen");
    ws2.open();
    ws2.frame({ type: "feedDelta", gen: G, newGen: G2, base: 1, rev: 3, through: 3, now: 600, buildId: 20, asks: [card(SID_A, 5)] });
    assert.equal(feeds(emitted).length, before + 1, "the composed feedDelta applied onto the surviving raw base");
    assert.deepEqual(heldOf(fm), { gen: G2, rev: 3 });
    ws2.frame({ type: "delta", slot: "bars", gen: G, newGen: G2, base: 2, rev: 5, through: 5, coll: { turns: { set: { [SID_A + SEP + "seg-9"]: { id: "seg-9", start: 1020, end: 1025, q: "ninth" } } } }, rest: { now: 600 } });
    assert.deepEqual(conn.viewDeltas.held("bars"), { gen: G2, rev: 5 }, "the composed bars patch applied onto the surviving receiver base");
    assert.deepEqual(ws2.sent, [], "nothing asked of the remote on either slot");
    fm.conns.get(HOST).closed = true;
  });
});

// Every delta a stamping kernel sends carries `through` (equal to its rev on a per-cycle delta, R on a composed frame), so
// through's presence does not tell a per-cycle delta from a composed one and the gate never keys on it: a per-cycle
// delta stamped base r, rev r+1, through r+1 and no newGen passes the gate (through at or above the held rev) and leaves
// (gen, r+1), the pair (gen, through). The redial then declares what the whole stream left.
test("a per-cycle stamped delta carrying through equal to its rev applies under the gate and leaves (gen, rev), through's presence making it no composed frame; a composed frame after it leaves (newGen, through) and the redial declares that pair in the kernel's string form", async () => {
  await withManager(({ fm, emitted }) => {
    fm.outbound({ type: "ready", proto: 2 });
    fm.openRemote(HOST, true);
    const ws = last(FakeWS.made);
    ws.open();
    ws.frame({ type: "caps" });
    ws.frame(stamped());
    const before = feeds(emitted).length;
    ws.frame({ ...cycle(G, 0, 2), through: 1 });   // the stamping kernel's per-cycle shape: gen, base, rev and through, through equal to rev, no newGen
    assert.equal(feeds(emitted).length, before + 1, "applied: through at or above the held rev, the gate passed");
    assert.deepEqual(heldOf(fm), { gen: G, rev: 1 }, "(gen, rev): the pair (gen, through), through equal to rev");
    ws.frame({ ...cycle(G, 1, 3), through: 2 });
    assert.deepEqual(heldOf(fm), { gen: G, rev: 2 });
    assert.deepEqual(ws.sent.filter((x: any) => x.type !== "ready"), [], "nothing asked (the first dial's own ready aside)");
    ws.frame({ type: "feedDelta", gen: G, newGen: G2, base: 2, rev: 5, through: 5, now: 600, buildId: 20, asks: [card(SID_A, 5)] });
    assert.deepEqual(heldOf(fm), { gen: G2, rev: 5 }, "a composed frame: (newGen, through), the newGen telling it from the per-cycle shape");
    ws.readyState = 3;
    const timers = heldTimers(() => ws.onclose!({ code: 1006, wasClean: false }));
    timers[0]();
    assert.equal(qOf(last(FakeWS.made).url).get("caps"), "feedDelta,held:feed:" + G2 + ".5", "the redial declares the pair the whole stream left, the gen as the kernel's string");
    fm.conns.get(HOST).closed = true;
  });
});

// The pair advances to the frame's rev, and a stamped delta's rev IS its through (the design: through equal to rev on a
// per-cycle delta, R on a composed frame); a frame whose two disagree is refused into needFullFeed carrying the held pair,
// in either direction, because advancing to either number would declare a reach the stream never reached: (gen, 7) from a
// delta that applied rev 2 (the round-3 find: the gate read through against the held rev alone), or (gen, 2) from one whose
// stated reach was 7. The row's why is "disagree", the relation word (round 3's fifth word): both revs are good safe
// integers and no field failed, and the row carries the word alone, so a field's word ("rev") would hide the cause from
// its reader; "rev" is a rev that is no safe integer, and it is read before the relation, so a non-integer rev that also
// disagrees reads "rev".
test("a stamped delta whose rev and through disagree is refused with why disagree and the held pair on the ask, in either direction and for a composed frame; a non-integer rev reads rev, disagreeing or not; the row is latched on its word and the remote's build while every refused frame asks; nothing applied, the pair stands, and the redial declares only what applied", async () => {
  await withManager(({ fm, emitted, sent }) => {
    fm.outbound({ type: "ready", proto: 2 });
    fm.openRemote(HOST, true);
    const ws = last(FakeWS.made);
    ws.open();
    ws.frame({ type: "caps" });
    ws.frame(stamped());
    ws.frame(cycle(G, 0, 2));
    assert.deepEqual(heldOf(fm), { gen: G, rev: 1 });
    const before = feeds(emitted).length, raw = fm.conns.get(HOST).feedRaw;
    ws.frame({ type: "feedDelta", gen: G, base: 1, rev: 2, through: 7, now: 520, buildId: 50, asks: [card(SID_A, 9)] });   // through past rev
    assert.deepEqual(ws.sent.filter((x: any) => x.type !== "ready"), [{ type: "needFullFeed", gen: G, rev: 1 }], "refused: the ask carries the pair that applied, not (gen, 7)");
    ws.frame({ type: "feedDelta", gen: G, base: 1, rev: 7, through: 2, now: 521, buildId: 51, asks: [card(SID_A, 9)] });   // rev past through
    ws.frame({ type: "feedDelta", gen: G, newGen: G2, base: 1, rev: 4, through: 5, now: 522, buildId: 52, asks: [card(SID_A, 9)] });   // a composed frame whose two disagree
    ws.frame({ type: "feedDelta", gen: G, base: 1, rev: 2.5, through: 2, now: 523, buildId: 53, asks: [card(SID_A, 9)] });   // gen, base and through pass; the rev is no safe integer: the rev field's own failure
    ws.frame({ type: "feedDelta", gen: G, base: 1, rev: 2.5, through: 7, now: 524, buildId: 54, asks: [card(SID_A, 9)] });   // a non-integer rev that also disagrees with its through: the field word, read before the relation
    assert.equal(ws.sent.filter((x: any) => x.type === "needFullFeed").length, 5, "each refused frame asks once: the ask is not latched (the bars road's needSlot is not either)");
    assert.ok(ws.sent.filter((x: any) => x.type === "needFullFeed").every((x: any) => x.gen === G && x.rev === 1), "every ask carries the pair that applied");
    assert.deepEqual(diagRows(sent, "feedDelta-stale"),
                     [{ host: HOST, buildId: 50, why: "disagree" }, { host: HOST, buildId: 53, why: "rev" }],
                     "the relation word for two good revs that disagree (not one rev to advance to), the field word for a rev that is no safe integer, whatever its through; the row is latched on its word and the remote's build (round 4, sayDeltaOnce), so the same word again on this conn files no second row");
    // the latch's key carries the remote's build: the same word from the remote on another build is news and files again
    fm.conns.get(HOST).peerSha = "a1b2c3d4e";
    ws.frame({ type: "feedDelta", gen: G, base: 1, rev: 2, through: 7, now: 525, buildId: 55, asks: [card(SID_A, 9)] });
    assert.equal(ws.sent.filter((x: any) => x.type === "needFullFeed").length, 6, "asked again");
    assert.deepEqual(last(diagRows(sent, "feedDelta-stale")), { host: HOST, buildId: 55, why: "disagree" }, "the word again under another build files its own row");
    assert.equal(diagRows(sent, "feedDelta-stale").length, 3);
    assert.equal(feeds(emitted).length, before, "nothing applied, nothing emitted");
    assert.equal(fm.conns.get(HOST).feedRaw, raw, "the base stands");
    assert.deepEqual(heldOf(fm), { gen: G, rev: 1 }, "the pair is what applied");
    ws.frame(cycle(G, 1, 3));   // a well-formed per-cycle delta after them (rev 2, through 2) applies as ever
    assert.deepEqual(heldOf(fm), { gen: G, rev: 2 });
    assert.equal(feeds(emitted).length, before + 1);
    ws.readyState = 3;
    const timers = heldTimers(() => ws.onclose!({ code: 1006, wasClean: false }));
    timers[0]();
    assert.equal(qOf(last(FakeWS.made).url).get("caps"), "feedDelta,held:feed:" + G + ".2", "the redial declares the applied rev, never a stated reach");
    fm.conns.get(HOST).closed = true;
  });
});

test("the gen's form: a non-empty string holding neither '.' nor ',' (the kernel's token and counter joined by '-'), at most GEN_MAX characters; a full carrying a value of any other form (a number, an empty string, a string carrying either separator or one over the cap) leaves no pair, and onto that gen-less base a delta carrying the same value applies as a gen-less one and the redial declares nothing (onto a base holding a pair it is refused: the round-4 test below)", async () => {
  const overCap = GEN_STAMP + "-" + "9".repeat(GEN_MAX - GEN_STAMP.length);   // GEN_MAX + 1 characters, all in the kernel's alphabet
  assert.equal(overCap.length, GEN_MAX + 1);
  for (const bad of [7, 0, "", GEN_STAMP + ".7", GEN_STAMP + ",7", null, true, overCap]) {
    await withManager(({ fm, emitted }) => {
      fm.outbound({ type: "ready", proto: 2 });
      fm.openRemote(HOST, true);
      const ws = last(FakeWS.made);
      ws.open();
      ws.frame({ type: "caps" });
      ws.frame(stamped({ gen: bad }));
      assert.equal(heldOf(fm), undefined, "no pair for a gen of this form: " + JSON.stringify(bad));
      const before = feeds(emitted).length;
      ws.frame({ ...cycle(G, 0, 2), gen: bad });
      assert.equal(feeds(emitted).length, before + 1, "the delta applied on the base's presence, as a gen-less one does: " + JSON.stringify(bad));
      assert.deepEqual(ws.sent.filter((x: any) => x.type !== "ready"), [], "nothing asked");
      ws.readyState = 3;
      const timers = heldTimers(() => ws.onclose!({ code: 1006, wasClean: false }));
      timers[0]();
      assert.equal(qOf(last(FakeWS.made).url).get("caps"), "feedDelta", "nothing declared for a base holding no gen: " + JSON.stringify(bad));
      fm.conns.get(HOST).closed = true;
    });
  }
});

// Unparseable is not absent (round 4, 2026-09-20). GEN_MAX made a 65-character gen read as no stamp, so a foreign-generation
// delta carrying one bypassed the gate and applied onto a base holding a gen (the length door); the same held for every
// other form genOf cannot read (a number, an empty string, a separator) at both heads. Now a frame carrying a gen of ANY
// form onto a base holding a pair enters the gate, and a value genOf cannot read is no match for the held gen: refused
// with the field word, the ask carrying the held pair, nothing applied, the pair standing. The scope is the base holding a
// pair (the minimal of the two options the round offered, applied to the feed and bars roads alike): onto a base holding no
// gen such a frame applies as a gen-less one, as the form test above pins, since no pair is held there for a refusal to
// protect.
test("a delta carrying a gen genOf cannot read (one over GEN_MAX, a separator, a number, an empty string, null) onto a base holding a pair is refused with why gen and the held pair on the ask, never applied as a gen-less one: nothing emitted, the base and the pair stand", async () => {
  const overCap = GEN_STAMP + "-" + "9".repeat(GEN_MAX - GEN_STAMP.length);
  assert.equal(overCap.length, GEN_MAX + 1);
  for (const bad of [overCap, GEN_STAMP + ".7", GEN_STAMP + ",7", 7, "", null, true]) {
    await withManager(({ fm, emitted, sent }) => {
      fm.outbound({ type: "ready", proto: 2 });
      fm.openRemote(HOST, true);
      const ws = last(FakeWS.made);
      ws.open();
      ws.frame({ type: "caps" });
      ws.frame(stamped());
      ws.frame(cycle(G, 0, 2));
      assert.deepEqual(heldOf(fm), { gen: G, rev: 1 });
      const before = feeds(emitted).length, raw = fm.conns.get(HOST).feedRaw;
      ws.frame({ type: "feedDelta", gen: bad, base: 1, rev: 2, through: 2, now: 540, buildId: 70, asks: [card(SID_A, 9)] });
      assert.deepEqual(ws.sent.filter((x: any) => x.type !== "ready"), [{ type: "needFullFeed", gen: G, rev: 1 }], "refused, the ask carrying the held pair: " + JSON.stringify(bad));
      assert.deepEqual(diagRows(sent, "feedDelta-stale"), [{ host: HOST, buildId: 70, why: "gen" }], "the gen field's word: a value genOf cannot read is no match for the held gen: " + JSON.stringify(bad));
      assert.equal(feeds(emitted).length, before, "nothing applied, nothing emitted: " + JSON.stringify(bad));
      assert.equal(fm.conns.get(HOST).feedRaw, raw, "the base stands: " + JSON.stringify(bad));
      assert.deepEqual(heldOf(fm), { gen: G, rev: 1 }, "the pair stands: " + JSON.stringify(bad));
      ws.readyState = 3;
      heldTimers(() => ws.onclose!({ code: 1006, wasClean: false }))[0]();
      assert.equal(qOf(last(FakeWS.made).url).get("caps"), "feedDelta,held:feed:" + G + ".1", "the redial declares the pair that applied: " + JSON.stringify(bad));
      fm.conns.get(HOST).closed = true;
    });
  }
});

// The same rule one field over (round 4): a composed frame whose gen the gate matched but whose newGen genOf cannot read
// used to fall back to the OLD gen and advance the pair to the frame's rev under it, so the redial declared a pair that
// generation's stream never held. The gate now reads newGen where it reads gen: a present value genOf cannot read is a
// refusal (why newGen, the field's own word), inside the gate and before the apply, so nothing applies and the pair stands.
test("a composed frame whose gen matched but whose newGen genOf cannot read is refused with why newGen and the held pair on the ask: nothing applied, the pair does not advance under the old gen, and the redial declares what applied", async () => {
  const overCap = GEN_STAMP + "-" + "9".repeat(GEN_MAX - GEN_STAMP.length);
  for (const bad of [overCap, GEN_STAMP + ".9", GEN_STAMP + ",9", 9, "", null]) {
    await withManager(({ fm, emitted, sent }) => {
      fm.outbound({ type: "ready", proto: 2 });
      fm.openRemote(HOST, true);
      const ws = last(FakeWS.made);
      ws.open();
      ws.frame({ type: "caps" });
      ws.frame(stamped());
      ws.frame(cycle(G, 0, 2));
      assert.deepEqual(heldOf(fm), { gen: G, rev: 1 });
      const before = feeds(emitted).length, raw = fm.conns.get(HOST).feedRaw;
      ws.frame({ type: "feedDelta", gen: G, newGen: bad, base: 1, rev: 4, through: 4, now: 541, buildId: 71, asks: [card(SID_A, 9)] });
      assert.deepEqual(ws.sent.filter((x: any) => x.type !== "ready"), [{ type: "needFullFeed", gen: G, rev: 1 }], "refused, the ask carrying the held pair: " + JSON.stringify(bad));
      assert.deepEqual(diagRows(sent, "feedDelta-stale"), [{ host: HOST, buildId: 71, why: "newGen" }], "the newGen field's own word: " + JSON.stringify(bad));
      assert.equal(feeds(emitted).length, before, "nothing applied: " + JSON.stringify(bad));
      assert.equal(fm.conns.get(HOST).feedRaw, raw, "the base stands: " + JSON.stringify(bad));
      assert.deepEqual(heldOf(fm), { gen: G, rev: 1 }, "the pair does not advance to rev 4 under the old gen: " + JSON.stringify(bad));
      ws.readyState = 3;
      heldTimers(() => ws.onclose!({ code: 1006, wasClean: false }))[0]();
      assert.equal(qOf(last(FakeWS.made).url).get("caps"), "feedDelta,held:feed:" + G + ".1", "the redial declares (G, 1), never (G, 4): " + JSON.stringify(bad));
      fm.conns.get(HOST).closed = true;
    });
  }
});

// The one statement of what the declared pair does today (round 3, 2026-09-20): federation.ts says it once, at
// Conn.feedHeld, in the words the other sites point at, and no comment on either road claims in the present tense that
// kernel.py reads the pair at the compose (no kernel in this repo reads a held member or an ask's pair). A source pin, the
// way perf-beacon-settings.test.ts pins the gear copy.
test("federation.ts states once what the pair does today (no kernel in this repo stamps a gen yet, so nothing declares one today) and no comment on either road says kernel.py reads the pair at the compose", () => {
  const UI = path.resolve(process.cwd(), "..", "ui", "webview");
  // the comments' wrapping is not part of the claim: a line break and its comment marker read as one space
  const flat = (f: string) => fs.readFileSync(path.join(UI, f), "utf8").replace(/\n\s*(\/\/|\*)\s?/g, " ").replace(/\s+/g, " ");
  const fedSrc = flat("federation.ts"), vdSrc = flat("view-deltas.ts");
  const home = "no kernel in this repo stamps a gen yet, so nothing declares one today";
  assert.equal(fedSrc.split("What the pair does today, stated here once").length, 2, "the home statement, once, at Conn.feedHeld");
  assert.ok(fedSrc.includes(home) && vdSrc.includes(home), "both files carry the statement's words");
  // the forbidden CLASS, not the wordings the round removed (the fixer's pass: a comment of the class in other words passed
  // the two exact regexes): kernel.py, or "the kernel" unqualified, said in the present tense to read a pair, member, gen,
  // rev or "it" at the compose. "A kernel that stamps its frames reads the member at the compose" is the qualified
  // statement the sites make and passes; "reads no pair" is the negation and passes.
  const claim = /\b(kernel\.py|the kernel)\b(?![^.;]{0,30}?\bthat stamps\b)[^.;]{0,30}?\breads\b(?! no\b)[^.;]{0,40}?\b(pair|member|gen|rev|it)\b[^.;]{0,40}?\bat the compose\b/;
  for (const shape of ["(kernel.py reads it at the compose)", "the kernel reads the member at the compose on either", "; kernel.py reads the held pair at the compose",
                       "kernel.py, which reads the pair at the compose", "the kernel's handler reads the ask's gen and rev at the compose"]) {
    assert.match(shape, claim, "the pin's own reach: " + shape);
  }
  for (const shape of ["a kernel that stamps its frames reads the member at the compose on either", "the kernel that stamps its frames reads the member at the compose",
                       "kernel.py's handler above serves a full frame at once whatever the ask carries and reads no pair", "that kernel would read the declared member at the compose"]) {
    assert.doesNotMatch(shape, claim, "the pin's own reach, the allowed side: " + shape);
  }
  for (const [name, src] of [["federation.ts", fedSrc], ["view-deltas.ts", vdSrc]]) {
    assert.doesNotMatch(src, claim, name + ": kernel.py is not said to read the pair at the compose, in any words");
  }
});

// The length bound (round 3, 2026-09-20): the form bounds the alphabet and not the digits, so genOf caps a stamp at GEN_MAX
// characters (the form test's list holds the one-over case); a gen at the cap is a stamp, the pair holds and the redial
// declares it, so the cap is exactly where it is stated.
test("a gen of exactly GEN_MAX characters is a stamp: the pair holds and the redial declares it", async () => {
  const atCap = GEN_STAMP + "-" + "9".repeat(GEN_MAX - GEN_STAMP.length - 1);
  assert.equal(atCap.length, GEN_MAX);
  await withManager(({ fm }) => {
    fm.outbound({ type: "ready", proto: 2 });
    fm.openRemote(HOST, true);
    const ws = last(FakeWS.made);
    ws.open();
    ws.frame({ type: "caps" });
    ws.frame(stamped({ gen: atCap }));
    assert.deepEqual(heldOf(fm), { gen: atCap, rev: 0 }, "at the cap: a stamp");
    ws.readyState = 3;
    heldTimers(() => ws.onclose!({ code: 1006, wasClean: false }))[0]();
    assert.equal(qOf(last(FakeWS.made).url).get("caps"), "feedDelta,held:feed:" + atCap + ".0", "declared at the cap");
    fm.conns.get(HOST).closed = true;
  });
});

// ── the apply-throw refusal, BOTH roads (the maintainer's round 5, refusals-2, and the 19:31Z ruling: the local road guarded
// too, with its own recovery, road word and bound) ──────────────────────────────────────────────────────────────────────────
// applyFeedDelta guards nothing but the two list shapes it upserts into, so a malformed delta throws out of upsertById; until this
// pass the throw escaped ws.onmessage (a TypeError out of the handler, no ask, no row, the pane on its last frame) and, on the
// local road, inbound into the shim's FIFO drain. Now feed-delta.ts's tryApplyFeedDelta catches it for both callers and each road
// refuses it: nothing written (the base and the pair stand), one BARE needFullFeed per stall (the base's own content is a
// suspect: a full carrying a null ask lands, and every well-formed delta after it throws in upsertById's walk of the base), a
// feedDelta-apply row with its own word (asked, stopped) and its road (wire, local), latched per word; and the BOUND, keyed on
// progress: a second throw while the ask is out asks nothing; a throw after the answering full landed (the feed arm) stops the
// asking and tells the shell once, through the {romp: "notify"} post the shell's error center reads; a delta that applies clears
// the latch; the remote latch resets with the socket (connect()), the local one lives for the page. The shell message is what
// the person sees: their cards frozen at the last update, and the way out named.
const notifies = (notified: any[]) => notified.filter((m) => m && m.romp === "notify");
const badDelta = (buildId: number) => ({ type: "feedDelta", now: 510, buildId, asks: { not: "a list" } });   // ups.map is not a function
const poisonedFull = (buildId: number) => ({ ...remoteFull(), buildId, asks: [null] });   // lands whole; the next delta's walk of the base throws
const applyRows = (sent: any[]) => diagRows(sent, "feedDelta-apply");

test("a remote feedDelta whose apply throws is REFUSED: one bare needFullFeed on the arriving conn, a feedDelta-apply row with why asked and road wire, nothing emitted, the base and the pair standing, no TypeError out of the handler; a second throw while the ask is out asks nothing and files nothing; the latch clears when a delta applies, and a later throw asks once more with the row latched", async () => {
  for (const withPair of [false, true]) {
    await withManager(({ fm, emitted, sent, notified }) => {
      const ws = attached(fm);
      if (withPair) { ws.frame(stamped({ buildId: 2 })); ws.frame(cycle(G, 0, 2)); assert.deepEqual(heldOf(fm), { gen: G, rev: 1 }); }
      const before = feeds(emitted).length, raw = fm.conns.get(HOST).feedRaw, held = heldOf(fm);
      ws.frame(withPair ? { ...cycle(G, 1, 3), asks: { not: "a list" } } : badDelta(2));   // no throw escapes: the rig would fail here
      assert.deepEqual(ws.sent, [{ type: "needFullFeed" }], "one BARE ask, never the held pair (the base's content is a suspect): pair=" + withPair);
      assert.deepEqual(applyRows(sent), [{ host: HOST, buildId: withPair ? 13 : 2, why: "asked", road: "wire" }], "its own row: the word asked, the road wire");
      assert.deepEqual(diagRows(sent, "feedDelta-stale"), []); assert.deepEqual(diagRows(sent, "feedDelta-nobase"), []);
      assert.equal(feeds(emitted).length, before, "nothing emitted");
      assert.equal(fm.conns.get(HOST).feedRaw, raw, "the base stands (nothing was written)");
      assert.deepEqual(heldOf(fm), held, "and the pair stands");
      assert.equal(fm.conns.get(HOST).feedApply, "asked");
      assert.deepEqual(notifies(notified), [], "nothing told to the shell yet: the ask may repair it");
      ws.frame(withPair ? { ...cycle(G, 1, 4), asks: [null] } : { type: "feedDelta", now: 511, buildId: 3, asks: [null] });   // a second throw while the ask is out
      assert.equal(ws.sent.length, 1, "a second throw while the ask is out asks nothing (a second ask is a second full, the flood the bound stops)");
      assert.equal(applyRows(sent).length, 1, "and files nothing");
      ws.frame(withPair ? stamped({ buildId: 4 }) : { ...remoteFull(), buildId: 4 });   // the full the ask earned
      assert.equal(fm.conns.get(HOST).feedApply, "answered", "the full landed: answered (the feed arm)");
      ws.frame(withPair ? cycle(G, 0, 5) : { type: "feedDelta", now: 520, buildId: 5, asks: [card(SID_A, 5)] });   // a good delta applies
      assert.equal(fm.conns.get(HOST).feedApply, undefined, "a delta that applies clears the latch: the stream is healthy again");
      assert.equal(feeds(emitted).length, before + 2, "the full and the delta each emitted");
      ws.frame(withPair ? { ...cycle(G, 1, 6), asks: { not: "a list" } } : badDelta(6));   // a later stall
      assert.equal(ws.sent.length, 2, "a later throw asks once more (the bound is per stall)");
      assert.deepEqual(last(ws.sent), { type: "needFullFeed" });
      assert.equal(applyRows(sent).length, 1, "the row is latched per word and build (sayDeltaOnce): no second asked row");
      assert.deepEqual(notifies(notified), [], "still nothing told: every stall so far was repaired or is being asked about");
      fm.conns.get(HOST).closed = true;
    });
  }
});

test("the BOUND on the remote road: after the answering full lands a second throw stops the asking and tells the shell once (a feedDelta-apply row with why stopped, one notify naming the host); further throws ask nothing, file nothing and tell nothing; a clean full and an applying delta clear it", async () => {
  await withManager(({ fm, emitted, sent, notified }) => {
    const ws = attached(fm);
    ws.frame(badDelta(2));
    assert.equal(ws.sent.length, 1, "the rig: asked");
    ws.frame(poisonedFull(3));   // the full the kernel sent back, itself poisoned: lands (prefixInbound and the merge take a null ask)
    const before = feeds(emitted).length;
    assert.equal(fm.conns.get(HOST).feedApply, "answered");
    ws.frame({ type: "feedDelta", now: 520, buildId: 4, asks: [card(SID_A, 2)] });   // well-formed, and it throws in upsertById's walk of the poisoned base
    assert.equal(ws.sent.length, 1, "the asking STOPPED: the full the kernel sent back did not repair the stream, and a second ask would earn the same full");
    assert.deepEqual(applyRows(sent).map((r: any) => r.why), ["asked", "stopped"], "the rows: asked, then stopped, each once");
    assert.deepEqual(applyRows(sent)[1], { host: HOST, buildId: 4, why: "stopped", road: "wire" });
    assert.equal(fm.conns.get(HOST).feedApply, "stopped");
    const told = notifies(notified);
    assert.equal(told.length, 1, "the shell told once");
    assert.equal(told[0].kind, "error");
    assert.match(told[0].text, /^TESTHOST: its cards are frozen at their last update\./, "the message names the host and what the person sees");
    assert.match(told[0].text, /reconnects\.$/, "and the way out");
    assert.equal(feeds(emitted).length, before, "nothing emitted for the refused delta");
    ws.frame({ type: "feedDelta", now: 521, buildId: 5, asks: [card(SID_A, 3)] });
    ws.frame(badDelta(6));
    assert.equal(ws.sent.length, 1, "two more throws: no ask");
    assert.equal(applyRows(sent).length, 2, "no row");
    assert.equal(notifies(notified).length, 1, "no second notify (the shell's center folds a repeat anyway; this side sends none)");
    ws.frame({ ...remoteFull(), buildId: 7 });   // a clean full (a kernel restart, or the stream recovering)
    assert.equal(fm.conns.get(HOST).feedApply, "stopped", "a full alone does not clear a stop (the last full did not repair it either)");
    ws.frame({ type: "feedDelta", now: 530, buildId: 8, asks: [card(SID_A, 4)] });   // and a delta that applies
    assert.equal(fm.conns.get(HOST).feedApply, undefined, "an applying delta clears the latch: progress is the reset");
    assert.equal(feeds(emitted).length, before + 2);
    fm.conns.get(HOST).closed = true;
  });
});

test("the remote latch resets with the socket: from stopped, the redial's replacement socket serves a full and a throwing delta asks exactly once again (one ask per socket life for a stall the fulls never repair)", async () => {
  await withManager(({ fm, sent, notified }) => {
    fm.outbound({ type: "ready", proto: 2 });
    fm.openRemote(HOST, true);
    const ws = last(FakeWS.made);
    ws.open();
    ws.frame({ type: "caps" });
    ws.frame(remoteFull());
    ws.frame(badDelta(2)); ws.frame(poisonedFull(3)); ws.frame({ type: "feedDelta", now: 520, buildId: 4, asks: [card(SID_A, 2)] });
    assert.equal(fm.conns.get(HOST).feedApply, "stopped", "the rig: stopped");
    assert.equal(notifies(notified).length, 1);
    ws.readyState = 3;
    heldTimers(() => ws.onclose!({ code: 1006, wasClean: false }))[0]();
    const ws2 = last(FakeWS.made);
    assert.notEqual(ws2, ws, "the rig: a fresh socket on the same conn");
    assert.equal(fm.conns.get(HOST).feedApply, undefined, "connect() reset the latch with the socket: a new stream for the bound to judge");
    ws2.open();
    ws2.frame(remoteFull());
    ws2.frame(badDelta(9));
    assert.deepEqual(ws2.sent.filter((x: any) => x.type !== "ready"), [{ type: "needFullFeed" }], "asked once again on the new socket");
    assert.equal(applyRows(sent).length, 2, "the rows stay latched per word and build (the same build: no third row)");
    ws2.frame(badDelta(10));
    assert.equal(ws2.sent.filter((x: any) => x.type !== "ready").length, 1, "and not twice");
    fm.conns.get(HOST).closed = true;
  });
});

test("the LOCAL road's twin: a local feedDelta whose apply throws is refused with one bare needFullFeed to the LOCAL kernel (its recovery, the same handler the no-base arm asks), a feedDelta-apply row with host local and road local, nothing emitted, the merge's frame standing; a second throw asks nothing; an applying delta clears the latch", async () => {
  await withManager(({ fm, emitted, sent, notified }) => {
    attached(fm);
    fm.inbound("", { type: "feed", now: 420, buildId: 9, asks: [card(SID_L, 1)], ledgers: [ledger(SID_L, "web")] });
    const before = feeds(emitted).length, local = fm.perHostFeed[""];
    fm.inbound("", { type: "feedDelta", now: 430, buildId: 10, asks: { not: "a list" } });   // no throw escapes inbound
    assert.deepEqual(sent.filter((x) => x && x.type === "needFullFeed"), [{ type: "needFullFeed" }], "one bare ask to the local kernel");
    assert.deepEqual(applyRows(sent), [{ host: "local", buildId: 10, why: "asked", road: "local" }], "its own row: the word local under host, the road local");
    assert.equal(feeds(emitted).length, before, "nothing emitted");
    assert.equal(fm.perHostFeed[""], local, "the merge's frame stands");
    assert.equal(fm.localFeedApply, "asked");
    fm.inbound("", { type: "feedDelta", now: 431, buildId: 11, asks: [null] });
    assert.equal(sent.filter((x) => x && x.type === "needFullFeed").length, 1, "a second throw while the ask is out asks nothing");
    assert.equal(applyRows(sent).length, 1);
    fm.inbound("", { type: "feed", now: 440, buildId: 12, asks: [card(SID_L, 1)], ledgers: [ledger(SID_L, "web")] });   // the full the ask earned
    assert.equal(fm.localFeedApply, "answered");
    fm.inbound("", { type: "feedDelta", now: 450, buildId: 13, asks: [card(SID_L, 1, { text: "changed" })] });
    assert.equal(fm.localFeedApply, undefined, "an applying delta clears the local latch");
    assert.equal(last(feeds(emitted)).asks.find((a: any) => a.sid === SID_L).text, "changed", "and applied");
    assert.deepEqual(notifies(notified), [], "nothing told");
    fm.conns.get(HOST).closed = true;
  });
});

test("the LOCAL bound: after the local full landed a second throw stops the asking and tells the shell once, naming both ways out (the connection's reconnect, a page reload); further throws are silent; a later local full still shows (the cards refresh) and leaves the stop standing, since the shim's in-page redial is a dial this manager never sees; the local road implicates no peer (host local, road local) and touches no remote socket", async () => {
  await withManager(({ fm, emitted, sent, notified }) => {
    const ws = attached(fm);
    fm.inbound("", { type: "feed", now: 420, buildId: 9, asks: [card(SID_L, 1)], ledgers: [ledger(SID_L, "web")] });
    fm.inbound("", { type: "feedDelta", now: 430, buildId: 10, asks: { not: "a list" } });
    fm.inbound("", { type: "feed", now: 440, buildId: 11, asks: [null] });   // the answering full, poisoned
    assert.equal(fm.localFeedApply, "answered", "the rig: answered");
    const before = feeds(emitted).length;
    fm.inbound("", { type: "feedDelta", now: 450, buildId: 12, asks: [card(SID_L, 2)] });   // throws in the walk of the poisoned base
    assert.equal(sent.filter((x) => x && x.type === "needFullFeed").length, 1, "the asking stopped");
    assert.deepEqual(applyRows(sent).map((r: any) => [r.host, r.why, r.road]), [["local", "asked", "local"], ["local", "stopped", "local"]]);
    assert.equal(fm.localFeedApply, "stopped");
    const told = notifies(notified);
    assert.equal(told.length, 1, "the shell told once");
    assert.equal(told[0].kind, "error");
    assert.match(told[0].text, /^The cards are frozen at their last update\./);
    assert.match(told[0].text, /They refresh when the connection reconnects, or when you reload the page\.$/, "the local road's two ways out: the shim redials the local socket in-page after a drop and the feed arm shows the full it earns whatever the latch, or the page is reloaded (the author's fixer pass after round 5, refusal-3: the message had named the reload alone, on the premise that the local socket's life is the page's, which the shim's reconnect=1 redial refutes)");
    assert.equal(feeds(emitted).length, before);
    fm.inbound("", { type: "feedDelta", now: 451, buildId: 13, asks: { not: "a list" } });
    assert.equal(sent.filter((x) => x && x.type === "needFullFeed").length, 1); assert.equal(applyRows(sent).length, 2); assert.equal(notifies(notified).length, 1);
    // a later LOCAL full (the redialed socket's, or a kernel restart's): it lands and shows, the cards refreshing as the message
    // says, and the stop stands (a full is not progress; the manager sees no dial event for the local socket, so the page's life
    // is the local bound's), so the next throw asks nothing and files nothing
    fm.inbound("", { type: "feed", now: 460, buildId: 14, asks: [card(SID_L, 3)], ledgers: [ledger(SID_L, "web")] });
    assert.equal(feeds(emitted).length, before + 1, "the later local full shows: the feed arm stores and emits every full whatever the latch");
    assert.equal(last(feeds(emitted)).asks.find((a: any) => a.sid === SID_L).text, card(SID_L, 3).text, "and it is the full's content the cards now show");
    assert.equal(fm.localFeedApply, "stopped", "the stop stands past the full (only an applying delta clears it; no dial resets the local bound)");
    fm.inbound("", { type: "feedDelta", now: 461, buildId: 15, asks: { not: "a list" } });
    assert.equal(sent.filter((x) => x && x.type === "needFullFeed").length, 1, "a throw after the later full asks nothing"); assert.equal(applyRows(sent).length, 2, "and files nothing"); assert.equal(notifies(notified).length, 1, "and tells nothing further");
    assert.deepEqual(ws.sent, [], "the remote socket carried nothing for any of it");
    assert.equal(fm.conns.get(HOST).feedApply, undefined, "and the remote conn's latch is untouched");
    fm.conns.get(HOST).closed = true;
  });
});

test("the two roads' latches are independent: a remote stall does not move the local latch and a local stall does not move the remote's, and each files under its own host and road", async () => {
  await withManager(({ fm, sent }) => {
    const ws = attached(fm);
    fm.inbound("", { type: "feed", now: 420, buildId: 9, asks: [card(SID_L, 1)], ledgers: [ledger(SID_L, "web")] });
    ws.frame(badDelta(2));
    assert.equal(fm.conns.get(HOST).feedApply, "asked"); assert.equal(fm.localFeedApply, undefined);
    fm.inbound("", { type: "feedDelta", now: 430, buildId: 10, asks: { not: "a list" } });
    assert.equal(fm.localFeedApply, "asked"); assert.equal(fm.conns.get(HOST).feedApply, "asked");
    assert.deepEqual(applyRows(sent).map((r: any) => [r.host, r.road]), [[HOST, "wire"], ["local", "local"]]);
    assert.deepEqual(ws.sent, [{ type: "needFullFeed" }], "the remote ask on the remote socket");
    assert.deepEqual(sent.filter((x) => x && x.type === "needFullFeed"), [{ type: "needFullFeed" }], "the local ask to the local kernel");
    fm.conns.get(HOST).closed = true;
  });
});

// ── the fourth shape the served mirror does not read, an ACCEPTANCE (the maintainer's round 5, extra7-1) ───────────────────
// Every remote frame passes the conn's receiver before the arms, and the receiver decodes the feed slot (a kernel too old to read
// the caps term serves the feed as {type: "delta", slot: "feed"} patches), so such a patch reassembles into a {type: "feed"} frame
// that enters the feed arm and RE-SEEDS Conn.feedHeld from the reassembled frame's gen: the patch's rest.gen (content no frame
// recorder keeps), the receiver's feed base's gen with the rev reset, or nothing under restAll. The served mirror (held_pair,
// tests/test_federated_dial_terms_served.py) reads no delta frame on the feed slot and holds the pair the deltas before it left,
// so this is a divergence and not a refusal; the RECEIVER_BLIND rows feed-slotpatch-* hold these three readings, measured here. No
// kernel in this repo sends the patch to a socket that announced caps=feedDelta, and none stamps a gen on that road.
test("a delta slot:feed patch re-seeds the feed pair from the frame the receiver reassembles: rest.gen gives (rest.gen, 0), an empty rest the base's gen at rev 0, restAll with a rest carrying no gen clears it; the served mirror reads (G, 1) for all three", async () => {
  const drive = async (patch: any) => {
    let held: any = "unread";
    await withManager(({ fm }) => {
      fm.openRemote(HOST, true);
      const ws = last(FakeWS.made);
      ws.open();
      ws.frame(stamped({ buildId: 2 }));
      ws.frame(cycle(G, 0, 2));
      assert.deepEqual(heldOf(fm), { gen: G, rev: 1 }, "the rig: the pair the deltas left, the mirror's reading for every case below");
      ws.frame({ type: "delta", slot: "feed", base: 0, rev: 1, coll: {}, ...patch });
      held = heldOf(fm);
      fm.conns.get(HOST).closed = true;
    });
    return held;
  };
  assert.deepEqual(await drive({ rest: { gen: G2, now: 600, buildId: 9 } }), { gen: G2, rev: 0 }, "rest.gen: re-seeded under the patch's own gen, content no recorder keeps");
  assert.deepEqual(await drive({ rest: { now: 600, buildId: 9 } }), { gen: G, rev: 0 }, "an empty rest: the receiver's feed base's gen, the rev reset");
  assert.equal(await drive({ rest: { type: "feed", now: 600 }, restAll: true }), undefined, "restAll with a rest carrying no gen: the reassembled frame carries none, the pair cleared");
});

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
import { FederationManager, REMOTE_REDIAL_MS } from "./federation";
import * as fed from "./federation";
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

interface Rig { fm: any; emitted: any[]; sent: any[] }

async function withManager(fn: (rig: Rig) => void | Promise<void>): Promise<void> {
  const g: any = globalThis;
  const saved: Record<string, any> = {};
  const set = (k: string, v: any) => { saved[k] = { had: k in g, v: g[k] }; g[k] = v; };
  FakeWS.made = [];
  const emitted: any[] = [];   // what the merge hands the pane (no direct-delivery handler registered: emit dispatches on window)
  const sent: any[] = [];      // what goes to the LOCAL kernel (__rompLocalSend): diag rows, and a needFullFeed if the local path asks
  const realNow = Date.now;
  Date.now = () => clock;
  set("WebSocket", FakeWS);
  set("location", { protocol: "http:", host: "hub.local:1", search: "?wid=hublab" });
  set("localStorage", { getItem: () => null, setItem: () => {} });
  set("window", {
    dispatchEvent: (ev: any) => { if (ev && ev.data) emitted.push(ev.data); },
    __rompLocalSend: (m: any) => sent.push(m),
    __rompDialTerms: () => terms(),
    sessionStorage: { getItem: () => "" },
    parent: { postMessage: () => {} },
  });
  try {
    const fm: any = new FederationManager();
    fm.app = "fleet";
    await fn({ fm, emitted, sent });
  } finally {
    Date.now = realNow;
    for (const [k, r] of Object.entries(saved)) { if (r.had) g[k] = r.v; else delete g[k]; }
  }
}

const qOf = (url: string) => new URLSearchParams(url.split("?")[1] || "");
const feeds = (emitted: any[]) => emitted.filter((m) => m && m.type === "feed");
const last = (xs: any[]) => xs[xs.length - 1];

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
test("a needFullFeed the remote socket cannot carry is held like its twins: no toast, one hostconn hold row, flushed first on the open; a host with no conn drops it with the breadcrumb alone", async () => {
  await withManager(({ fm, emitted, sent }) => {
    fm.outbound({ type: "ready", proto: 2 });   // the page's proto: the open posts a ready, so the flush's place before it is visible
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
    assert.deepEqual(ws.sent, [{ type: "needFullFeed" }, { type: "ready", proto: 2 }],
      "flushed on the open event itself, ahead of the ready post (flushPending runs first): the kernel serves a full frame at once, one extra full per reconnect at most, as for needFull and needSlot");
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
// else. These pin the per-host keying of perHostFeedRaw, not the feature: they are green at this head and red under
// the mutation that keys the raw base by a constant at its four sites (the store, the two reads in applyRemoteFeedDelta,
// the detach), which the single-host tests above cannot see (a review round found that a "host B untouched after host
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
    assert.deepEqual(fm.perHostFeedRaw[HOST_A].asks.map((a: any) => a.itemId), [SID_S + ":g2"], "A's raw base advanced (bare ids: the key is the host alone)");
    assert.deepEqual(fm.perHostFeedRaw[HOST_B].asks.map((a: any) => a.itemId), [SID_S + ":g3"], "B's raw base is untouched");
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
    assert.deepEqual(fm.perHostFeedRaw[HOST_A].asks.map((a: any) => a.itemId), [SID_S + ":g1"], "A's raw base is as A's full left it");
    fm.conns.get(HOST_A).closed = true; fm.conns.get(HOST_B).closed = true;
  });
});

test("two hosts: detaching one drops its raw base and leaves the other's; the re-attached host's first delta asks on its NEW socket only", async () => {
  await withManager(({ fm, emitted }) => {
    const wsA = attachedAs(fm, HOST_A, fullA());
    const wsB = attachedAs(fm, HOST_B, fullB());
    fm.closeRemote(HOST_B);
    assert.equal(fm.perHostFeedRaw[HOST_B], undefined, "B's raw base went with B");
    assert.deepEqual(fm.perHostFeedRaw[HOST_A].asks.map((a: any) => a.itemId), [SID_S + ":g1"], "A's raw base survived B's detach");
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

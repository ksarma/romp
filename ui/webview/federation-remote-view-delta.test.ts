// A federated pane's REMOTE sockets reassemble the kernel's view deltas (2026-09-18). The relay dial has carried the
// page's own terms since 8fe70da07 (2026-09-15), delta=1 among them, so after the first full frame a remote kernel
// serves its bars slot as {type:"delta", slot:"bars"} patches (kernel.py _send_slot_delta; the feed takes the same
// path on a remote too old to read the caps term). Nothing on this side reassembled one: the kernel's inline shim
// decodes only its own LOCAL socket's frames, and federation.ts had no arm for the type, so the raw patch fell
// through to the pane, where timeline-boot.ts's dispatchFrame drops an unknown type without a row. On the phone a
// remote host's lanes froze where its first full frame put them. Now every remote Conn carries a ViewDeltas receiver
// (ui/webview/view-deltas.ts, the class VS Code's pipe uses) that runs on the raw frame before prefixing: a patch
// continues as the reassembled whole frame down the bars/feed arms, and one it cannot apply asks THAT kernel for the
// whole slot on its own socket, never the local kernel. Executed against the real FederationManager with a fake
// WebSocket that records its sends and a stub window that records what the merge emits (the rig of
// federation-remote-feed-delta.test.ts). Synthetic only (host TESTHOST, placeholder uuids, the notes-api demo:
// sessions `api` on the remote and `web` locally).
import { test } from "node:test";
import assert from "node:assert/strict";
import { FederationManager, REMOTE_STALE_MS, REMOTE_REDIAL_MS } from "./federation";

const HOST = "TESTHOST";
const SID_A = "11111111-2222-4333-8444-000000000701";   // "api" on TESTHOST
const SID_L = "99999999-8888-7777-6666-000000000001";   // "web", a local session
const PAGE_IID = "PAGEIID-0001";
const SEP = String.fromCharCode(31);   // the unit separator: the kernel keys a dictlist entry as lane + SEP + id (_delta_split)

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

interface Rig { fm: any; emitted: any[]; sent: any[] }

// the page's live dial terms, as the shim's __rompDialTerms returns them: delta: 1 for every app (kernel.py)
async function withManager(app: string, fn: (rig: Rig) => void | Promise<void>): Promise<void> {
  const g: any = globalThis;
  const saved: Record<string, any> = {};
  const set = (k: string, v: any) => { saved[k] = { had: k in g, v: g[k] }; g[k] = v; };
  FakeWS.made = [];
  const emitted: any[] = [];   // what the merge hands the pane (no direct-delivery handler registered: emit dispatches on window)
  const sent: any[] = [];      // what goes to the LOCAL kernel (__rompLocalSend): diag rows, and a needSlot if anything asks it there
  const realNow = Date.now;
  Date.now = () => clock;
  set("WebSocket", FakeWS);
  set("location", { protocol: "http:", host: "hub.local:1", search: "?wid=hublab" });
  set("localStorage", { getItem: () => null, setItem: () => {} });
  set("window", {
    dispatchEvent: (ev: any) => { if (ev && ev.data) emitted.push(ev.data); },
    __rompLocalSend: (m: any) => sent.push(m),
    __rompDialTerms: () => ({ app, iid: PAGE_IID, active: "", col: "", skeleton: 0, provrows: app === "fleet" ? 1 : 0, proto: null, delta: 1 }),
    sessionStorage: { getItem: () => "" },
    parent: { postMessage: () => {} },
  });
  try {
    const fm: any = new FederationManager();
    fm.app = app;
    await fn({ fm, emitted, sent });
  } finally {
    Date.now = realNow;
    for (const [k, r] of Object.entries(saved)) { if (r.had) g[k] = r.v; else delete g[k]; }
  }
}

const qOf = (url: string) => new URLSearchParams(url.split("?")[1] || "");
const barsOf = (emitted: any[]) => emitted.filter((m) => m && m.type === "bars");
const feedsOf = (emitted: any[]) => emitted.filter((m) => m && m.type === "feed");
const last = (xs: any[]) => xs[xs.length - 1];
const ids = (bars: any[]) => bars.map((b: any) => b.id);
const localAsks = (sent: any[]) => sent.filter((x) => x && x.type === "needSlot");

const bar = (id: string, start: number, end: number, q: string) => ({ id, start, end, q });

// the LOCAL kernel's lanes and bars: the merge holds a bars emit until both exist (emitMergedTimeline)
function seedLocalTimeline(fm: any): void {
  fm.inbound("", { type: "data", data: { sessions: [{ id: SID_L, name: "web" }], turns: { [SID_L]: [] }, judging: {}, messages: [], now: 500 } });
  fm.inbound("", { type: "bars", turns: { [SID_L]: [bar("loc-1", 1000, 1005, "local first")] }, judging: {}, messages: [], now: 500, warming: false });
}

// the remote kernel's FULL bars frame, as it sends it: bare sids, its own clock
function remoteBars(): any {
  return { type: "bars", turns: { [SID_A]: [bar("seg-1", 1000, 1005, "first")] }, judging: {}, messages: [], now: 500, warming: false };
}

// a bars patch as the kernel sends it to a delta=1 client (kernel.py _send_slot_delta): one bar set under its
// lane-and-id key, the clock riding in the remainder
function barsPatch(base: number, b: any, now: number): any {
  return { type: "delta", slot: "bars", base, rev: base + 1, coll: { turns: { set: { [SID_A + SEP + b.id]: b } } }, rest: { now } };
}

// dial, open, and hand the socket the remote's first full bars frame; returns the socket
function attached(fm: any): FakeWS {
  fm.openRemote(HOST, true);
  const ws = last(FakeWS.made);
  ws.open();
  ws.frame(remoteBars());
  return ws;
}

test("a remote host's bars patch reassembles onto the full frame held for its socket and the merged timeline moves; nothing is asked of either kernel", async () => {
  await withManager("timeline", ({ fm, emitted, sent }) => {
    seedLocalTimeline(fm);
    const ws = attached(fm);
    assert.equal(qOf(ws.url).get("delta"), "1", "the remote dial still carries the page's delta term: the remote serves patches");
    let m = last(barsOf(emitted));
    assert.deepEqual(Object.keys(m.turns).sort(), [SID_L, HOST + ":" + SID_A].sort(), "the full frame merges prefixed, as before");
    assert.deepEqual(ids(m.turns[HOST + ":" + SID_A]), ["seg-1"]);
    const before = barsOf(emitted).length;
    ws.frame(barsPatch(0, bar("seg-2", 1010, 1015, "second"), 505));
    assert.equal(barsOf(emitted).length, before + 1, "the patch re-emits the merge once");
    m = last(barsOf(emitted));
    assert.deepEqual(ids(m.turns[HOST + ":" + SID_A]), ["seg-1", "seg-2"], "the appended bar landed beside the held one, on the prefixed lane");
    assert.deepEqual(ids(m.turns[SID_L]), ["loc-1"], "the local lane stands");
    // the host's held frame is the reassembled whole, prefixed as a full frame is; the merged emit's times are rebased
    // onto the local clock (mergeHostBars), so the reassembly's content is read here
    const held = fm.perHostTlBars[HOST];
    assert.deepEqual(held.turns[HOST + ":" + SID_A], [bar("seg-1", 1000, 1005, "first"), bar("seg-2", 1010, 1015, "second")]);
    assert.equal(held.now, 505, "the remainder's clock advanced");
    assert.deepEqual(ws.sent, [], "nothing asked of the remote: the patch applied");
    assert.deepEqual(localAsks(sent), [], "nothing asked of the local kernel either: it holds nothing for this host");
    // a second patch applies onto the FIRST patch's result (rev 1 to 2), not the stale full frame
    ws.frame(barsPatch(1, bar("seg-2", 1010, 1020, "second"), 510));
    m = last(barsOf(emitted));
    assert.deepEqual(ids(m.turns[HOST + ":" + SID_A]), ["seg-1", "seg-2"]);
    assert.deepEqual(fm.perHostTlBars[HOST].turns[HOST + ":" + SID_A].map((b: any) => [b.id, b.end]), [["seg-1", 1005], ["seg-2", 1020]], "the open bar's end advanced in place");
    assert.deepEqual(ws.sent, []);
    fm.conns.get(HOST).closed = true;
  });
});

test("a remote bars patch with no full frame held asks THAT kernel for the whole slot on its own socket; the local kernel is not asked and nothing is emitted", async () => {
  await withManager("timeline", ({ fm, emitted, sent }) => {
    seedLocalTimeline(fm);
    fm.openRemote(HOST, true);
    const ws = last(FakeWS.made);
    ws.open();
    const before = barsOf(emitted).length;
    ws.frame(barsPatch(0, bar("seg-2", 1010, 1015, "second"), 505));
    assert.deepEqual(ws.sent, [{ type: "needSlot", slot: "bars" }],
      "the ask goes to the kernel that sent the patch: it forgets what it believes this socket holds and serves the whole slot (kernel.py needSlot)");
    assert.deepEqual(localAsks(sent), [], "the local kernel holds no base for this host: not asked (routeOutbound's local fall-through is not the route)");
    assert.equal(barsOf(emitted).length, before, "nothing to apply onto, nothing emitted");
    ws.frame(remoteBars());   // the whole slot the ask earns
    assert.equal(barsOf(emitted).length, before + 1);
    ws.frame(barsPatch(0, bar("seg-2", 1010, 1015, "second"), 505));
    assert.deepEqual(ids(last(barsOf(emitted)).turns[HOST + ":" + SID_A]), ["seg-1", "seg-2"], "the stream applies from the full frame on");
    assert.deepEqual(ws.sent, [{ type: "needSlot", slot: "bars" }], "no second ask");
    // a patch from past what this socket holds (a base the receiver never saw) asks again and emits nothing
    const applied = barsOf(emitted).length;
    ws.frame(barsPatch(7, bar("seg-9", 1030, 1035, "ninth"), 520));
    assert.deepEqual(ws.sent, [{ type: "needSlot", slot: "bars" }, { type: "needSlot", slot: "bars" }], "a base mismatch asks the sender for the whole slot");
    assert.equal(barsOf(emitted).length, applied, "…and the merge stands as the last applied frame left it");
    assert.deepEqual(localAsks(sent), []);
    fm.conns.get(HOST).closed = true;
  });
});

test("a detach drops the host's receiver with its conn: the re-attached host's first patch finds no base and asks its kernel", async () => {
  await withManager("timeline", ({ fm, emitted }) => {
    seedLocalTimeline(fm);
    const ws = attached(fm);
    ws.frame(barsPatch(0, bar("seg-2", 1010, 1015, "second"), 505));
    assert.deepEqual(ws.sent, []);
    assert.deepEqual(ids(last(barsOf(emitted)).turns[HOST + ":" + SID_A]), ["seg-1", "seg-2"]);
    fm.closeRemote(HOST);
    assert.ok(!(HOST + ":" + SID_A in last(barsOf(emitted)).turns), "the detach dropped the host's lanes");
    fm.openRemote(HOST, true);
    const ws2 = last(FakeWS.made);
    assert.notEqual(ws2, ws, "a fresh conn and socket");
    ws2.open();
    ws2.frame(barsPatch(1, bar("seg-3", 1020, 1025, "third"), 515));   // continues the OLD socket's stream: no base here
    assert.deepEqual(ws2.sent, [{ type: "needSlot", slot: "bars" }], "the stale base did not survive the detach; the remote is asked for the whole slot");
    assert.deepEqual(ws.sent, [], "…on the new socket, not the dead one");
    fm.conns.get(HOST).closed = true;
  });
});

// ── a redial on the same conn (2026-09-19) ──────────────────────────────────────────────────────────────────────────
// The receiver belongs to one SOCKET (view-deltas.ts; the extension's pipe mints one per dial), and the conn outlives the
// socket: the onclose retry and the watchdog's abandon-and-dial both keep the Conn and make a new socket on it. connect()
// re-mints the receiver per dial, beside the socket's other per-dial resets, so a replacement socket's first patch finds no
// base and asks its kernel for the whole slot instead of applying onto the dead socket's half-assembled slot. LATENT
// against every kernel in this repo (dstate is per connection and a redial opens a fresh upstream socket, so a new
// socket's first frame is whole); pinned for the module's contract. FakeWS.close() fires no onclose, so road A calls the
// handler as a browser would and runs the redial it arms (a real 2 s timer under node) at once, through a setTimeout
// stub scoped to the call.
function armedRedials(fn: () => void): Array<() => void> {
  const timers: Array<() => void> = [];
  const real = globalThis.setTimeout;
  (globalThis as any).setTimeout = (cb: () => void) => { timers.push(cb); return 0; };
  try { fn(); } finally { (globalThis as any).setTimeout = real; }
  return timers;
}

test("an onclose redial mints a fresh receiver: the replacement socket's first patch cannot apply onto the dead socket's slot and asks its kernel", async () => {
  await withManager("timeline", ({ fm, emitted, sent }) => {
    seedLocalTimeline(fm);
    const ws = attached(fm);
    ws.frame(barsPatch(0, bar("seg-2", 1010, 1015, "second"), 505));
    assert.deepEqual(ids(last(barsOf(emitted)).turns[HOST + ":" + SID_A]), ["seg-1", "seg-2"]);
    const conn = fm.conns.get(HOST), vd = conn.viewDeltas, before = barsOf(emitted).length;
    ws.readyState = 3;
    const redials = armedRedials(() => ws.onclose!({ code: 1006, wasClean: false }));   // the socket dropped: the handler arms the redial
    assert.equal(redials.length, 1, "one redial armed");
    redials[0]();   // it fires: connect() on the same conn
    const ws2 = last(FakeWS.made);
    assert.notEqual(ws2, ws, "a fresh socket");
    assert.equal(fm.conns.get(HOST), conn, "…on the same conn (the page's identity for the host)");
    ws2.open();
    ws2.frame(barsPatch(1, bar("seg-3", 1020, 1025, "third"), 515));   // continues the DEAD socket's stream (base 1): no base here
    assert.deepEqual(ws2.sent, [{ type: "needSlot", slot: "bars" }], "the new socket's first patch finds no base: that kernel is asked for the whole slot on the new socket");
    assert.equal(barsOf(emitted).length, before, "nothing emitted: the patch did not apply onto the dead socket's slot");
    assert.deepEqual(ids(last(barsOf(emitted)).turns[HOST + ":" + SID_A]), ["seg-1", "seg-2"], "the merge stands where the dead socket left it");
    assert.deepEqual(ws.sent, [], "nothing on the dead socket");
    assert.deepEqual(localAsks(sent), []);
    assert.notEqual(conn.viewDeltas, vd, "the mechanism: a fresh receiver per dial, the dead socket's slot bases gone with it");
    fm.conns.get(HOST).closed = true;
  });
});

test("the watchdog's abandon-and-dial mints a fresh receiver too: it nulls the dead socket's handlers before dialing, so no onclose runs on that road", async () => {
  await withManager("timeline", ({ fm, emitted, sent }) => {
    seedLocalTimeline(fm);
    const ws = attached(fm);
    ws.frame(barsPatch(0, bar("seg-2", 1010, 1015, "second"), 505));
    const conn = fm.conns.get(HOST), vd = conn.viewDeltas, before = barsOf(emitted).length;
    clock += REMOTE_STALE_MS + 1000;   // an OPEN socket quiet past the stale bound
    fm.watchdog(clock);
    assert.equal(ws.onclose, null, "the watchdog abandoned the quiet socket: its handlers are detached");
    const ws2 = last(FakeWS.made);
    assert.notEqual(ws2, ws, "…and dialed a fresh one");
    assert.equal(fm.conns.get(HOST), conn, "on the same conn");
    ws2.open();
    ws2.frame(barsPatch(1, bar("seg-3", 1020, 1025, "third"), 515));
    assert.deepEqual(ws2.sent, [{ type: "needSlot", slot: "bars" }], "the dead socket's base is not the new socket's: asked for whole");
    assert.equal(barsOf(emitted).length, before, "nothing emitted");
    assert.deepEqual(ids(last(barsOf(emitted)).turns[HOST + ":" + SID_A]), ["seg-1", "seg-2"]);
    assert.deepEqual(ws.sent, []);
    assert.deepEqual(localAsks(sent), []);
    assert.notEqual(conn.viewDeltas, vd, "the mechanism: a fresh receiver per dial");
    fm.conns.get(HOST).closed = true;
  });
});

const card = (sid: string, n: number) =>
  ({ itemId: sid + ":g" + n, sid, name: sid === SID_L ? "web" : "api", text: "goal " + n, t: 1000 - n, column: "working" });
const ledger = (sid: string, name: string) => ({ sid, name, ledger: { tops: [] }, status: { state: "working" } });

test("the feed slot takes the same path: a remote host serving {type:\"delta\", slot:\"feed\"} (a kernel too old to read the caps term) is reassembled and merged prefixed, as its full frame is", async () => {
  await withManager("fleet", ({ fm, emitted, sent }) => {
    fm.inbound("", { type: "feed", now: 500, buildId: 7, asks: [card(SID_L, 1)], ledgers: [ledger(SID_L, "web")] });
    fm.openRemote(HOST, true);
    const ws = last(FakeWS.made);
    ws.open();
    ws.frame({ type: "feed", now: 500, buildId: 1, asks: [card(SID_A, 1)], working: [SID_A], ledgers: [ledger(SID_A, "api")] });
    let m = last(feedsOf(emitted));
    assert.deepEqual(m.asks.map((a: any) => [a.itemId, a.sid]), [[SID_L + ":g1", SID_L], [SID_A + ":g1", HOST + ":" + SID_A]], "the full frame merges prefixed");
    const before = feedsOf(emitted).length;
    // the kernel's feed patch: asks keyed by itemId (byid:itemId), the rest of the frame in the remainder
    ws.frame({ type: "delta", slot: "feed", base: 0, rev: 1, coll: { asks: { set: { [SID_A + ":g2"]: card(SID_A, 2) }, del: [SID_A + ":g1"] } }, rest: { now: 505, buildId: 2 } });
    assert.equal(feedsOf(emitted).length, before + 1, "the patch re-emits the merge once");
    m = last(feedsOf(emitted));
    assert.deepEqual(m.asks.map((a: any) => [a.itemId, a.sid, a.name]),
      [[SID_L + ":g1", SID_L, "web"], [SID_A + ":g2", HOST + ":" + SID_A, HOST + ":api"]],
      "the removed card left by its bare itemId, the new one arrived with its sid and name prefixed, the local card stands");
    assert.deepEqual(m.working, [HOST + ":" + SID_A], "a field the patch did not carry came over from the held base, prefixed");
    assert.deepEqual(fm.conns.get(HOST).feedRaw.asks.map((a: any) => a.itemId), [SID_A + ":g2"], "the reassembled frame is the conn's raw feed base too (a later feedDelta applies onto it)");
    assert.deepEqual(ws.sent, [], "nothing asked of the remote");
    assert.deepEqual(localAsks(sent), []);
    assert.equal(sent.filter((x) => x && x.type === "clientDiag" && x.what === "feedDelta-nobase").length, 0);
    fm.conns.get(HOST).closed = true;
  });
});

test("the LOCAL socket's frames pass untouched: the shim reassembles its own deltas, and a raw one is the pane's loud path, not this manager's", async () => {
  await withManager("fleet", ({ fm, emitted, sent }) => {
    const raw = { type: "delta", slot: "feed", base: 3, rev: 4, coll: { asks: { set: {} } }, rest: { now: 600 } };
    fm.inbound("", raw);
    assert.deepEqual(last(emitted), raw, "handed on as it came (fleet.ts files delta-unapplied and asks its own kernel)");
    assert.deepEqual(localAsks(sent), [], "this manager asks nothing for the local socket");
  });
});

// ── the one frame neither path decodes (2026-09-19) ──────────────────────────────────────────────────────────────────
// A patch for a slot this receiver has no table for (a kernel newer than this bundle) is asked for whole by the receiver
// (needSlot on this conn, view-deltas.ts recover) and said first by the manager: one hostconn row under keys the family
// already has (ev delta-unknown-slot, why = the slot), and a console line. A patch with no slot at all is the same event
// (a frame this bundle does not decode, from the same remote: said no more once a row stands, the next test) and is asked
// for nothing (there is no slot to name). Neither reaches the pane, and the known slot's base stands.
test("a remote patch for a slot this side does not decode is said (a hostconn row naming the slot) and asked for whole on the sending socket; a slotless one is dropped and asks for nothing; the known slot's base survives", async () => {
  await withManager("timeline", ({ fm, emitted, sent }) => {
    seedLocalTimeline(fm);
    const ws = attached(fm);
    const before = barsOf(emitted).length;
    const rows = () => sent.filter((x) => x && x.type === "clientDiag" && x.what === "hostconn" && x.data && x.data.ev === "delta-unknown-slot").map((x) => x.data);
    ws.frame({ type: "delta", slot: "lanes", base: 0, rev: 1, coll: {}, rest: { now: 505 } });
    assert.deepEqual(rows(), [{ host: HOST, ev: "delta-unknown-slot", why: "lanes" }], "said once, naming the host and the slot, under the family's existing keys");
    assert.deepEqual(ws.sent, [{ type: "needSlot", slot: "lanes" }], "…and that kernel is asked for the whole slot on this conn (its full frame renders through the raw dispatch below)");
    assert.equal(barsOf(emitted).length, before, "nothing emitted for it");
    assert.equal(emitted.filter((m) => m && m.type === "delta").length, 0, "the raw patch never reached the pane");
    ws.frame({ type: "delta" });
    assert.deepEqual(rows().map((r) => r.why), ["lanes"], "a slotless patch is the same event (a frame this bundle does not decode, from the same remote): the standing row says it");
    assert.deepEqual(ws.sent, [{ type: "needSlot", slot: "lanes" }], "…and it asks for nothing: there is no slot to name");
    ws.frame(barsPatch(0, bar("seg-2", 1010, 1015, "second"), 506));
    assert.deepEqual(ids(last(barsOf(emitted)).turns[HOST + ":" + SID_A]), ["seg-1", "seg-2"], "the bars base held through both: a known slot's patch still applies");
    assert.deepEqual(localAsks(sent), []);
    fm.conns.get(HOST).closed = true;
  });
});

// The row and the console line are said once per EVENT (Conn.saidDelta, sayDeltaOnce), and the event is this bundle's,
// not the slot name's: a patch for ANY slot this bundle does not decode, the slotless patch included, from the same
// remote on the same build (the hub's /tunnels row; this rig has none, so no build) is one event, one row naming the first
// slot seen and one console line, however many names the remote uses (the bound is this side's, further down), the rule
// the refused-base row shares below; the needSlot stays per patch, since it is the resync itself and the kernel coalesces
// asks. A detach ends the conn and its latch; a redial keeps the conn, and the same remote on the redialed socket is the
// same event, said no more (the build case is further down).
test("the unknown-slot breadcrumb is said once per event, and the event is this bundle's: a second patch for the slot, a second unknown slot and a slotless patch are said no more (and asked for where a slot is named); a re-attached host is said again; a redialed socket (the same remote) is not", async () => {
  await withManager("timeline", ({ fm, sent }) => countingConsoleErrors((errors) => {
    seedLocalTimeline(fm);
    const ws = attached(fm);
    const rows = () => sent.filter((x) => x && x.type === "clientDiag" && x.what === "hostconn" && x.data && x.data.ev === "delta-unknown-slot").map((x) => x.data);
    ws.frame({ type: "delta", slot: "lanes", base: 0, rev: 1, coll: {}, rest: { now: 505 } });
    ws.frame({ type: "delta", slot: "lanes", base: 1, rev: 2, coll: {}, rest: { now: 506 } });
    assert.deepEqual(rows(), [{ host: HOST, ev: "delta-unknown-slot", why: "lanes" }], "two lanes patches, said once");
    assert.equal(errors.length, 1, "and one console line: " + errors.join(" | "));
    assert.deepEqual(ws.sent, [{ type: "needSlot", slot: "lanes" }, { type: "needSlot", slot: "lanes" }], "asked per patch all the same: the ask is the resync");
    ws.frame({ type: "delta", slot: "marks", base: 0, rev: 1, coll: {} });
    assert.deepEqual(rows().map((r) => r.why), ["lanes"], "a second unknown slot is the same event: this bundle decodes neither, and the standing row (the first name seen) says so");
    assert.deepEqual(last(ws.sent), { type: "needSlot", slot: "marks" }, "…asked for whole all the same");
    ws.frame({ type: "delta" }); ws.frame({ type: "delta" });
    assert.deepEqual(rows().map((r) => r.why), ["lanes"], "the slotless patch too: nothing new to say");
    assert.equal(errors.length, 1, "one console line for the lot");
    // a redial on the conn (the watchdog's abandon-and-dial) keeps the latch: it is the conn's, not the socket's
    const conn = fm.conns.get(HOST);
    clock += REMOTE_STALE_MS + 1000;
    fm.watchdog(clock);
    const ws2 = last(FakeWS.made);
    assert.notEqual(ws2, ws, "redialed");
    assert.equal(fm.conns.get(HOST), conn);
    ws2.open();
    ws2.frame({ type: "delta", slot: "lanes", base: 0, rev: 1, coll: {} });
    assert.deepEqual(rows().map((r) => r.why), ["lanes"], "not said again on the redialed socket");
    assert.deepEqual(ws2.sent, [{ type: "needSlot", slot: "lanes" }], "…but asked, on the new socket");
    // a detach ends the conn and its latch: the re-attached host's first unknown patch is said again, naming the slot it came with
    fm.closeRemote(HOST);
    fm.openRemote(HOST, true);
    const ws3 = last(FakeWS.made);
    ws3.open();
    ws3.frame({ type: "delta", slot: "marks", base: 0, rev: 1, coll: {} });
    assert.deepEqual(rows().map((r) => r.why), ["lanes", "marks"], "said again on the new conn, with the first name that conn saw");
    assert.equal(errors.length, 2);
    fm.conns.get(HOST).closed = true;
  }));
});

// ── two hosts, the same bare lane (2026-09-19) ──────────────────────────────────────────────────────────────────────
// A receiver per conn, not one shared: two hosts whose bars frames carry the same bare lane (a session sid is not
// unique across hosts) each reassemble onto their own base. Different bar ids per host make a shared base visible
// (A's patch onto B's full would put B's bar on A's lane).
test("two hosts with the same bare lane: a patch from one host reassembles onto that host's own base and moves only its lane", async () => {
  await withManager("timeline", ({ fm, emitted }) => {
    seedLocalTimeline(fm);
    const HOST_B = "TESTHOSTB";
    const wsA = attached(fm);   // TESTHOST: lane SID_A holds seg-1
    fm.openRemote(HOST_B, true);
    const wsB = last(FakeWS.made);
    wsB.open();
    wsB.frame({ type: "bars", turns: { [SID_A]: [bar("b-1", 2000, 2005, "B's first")] }, judging: {}, messages: [], now: 600, warming: false });
    let m = last(barsOf(emitted));
    assert.deepEqual([ids(m.turns[HOST + ":" + SID_A]), ids(m.turns[HOST_B + ":" + SID_A])], [["seg-1"], ["b-1"]], "both hosts' lanes merged under their own prefixes");
    wsA.frame(barsPatch(0, bar("seg-2", 1010, 1015, "second"), 505));
    m = last(barsOf(emitted));
    assert.deepEqual(ids(m.turns[HOST + ":" + SID_A]), ["seg-1", "seg-2"], "A's patch appended to A's lane, onto A's own base");
    assert.deepEqual(ids(m.turns[HOST_B + ":" + SID_A]), ["b-1"], "B's lane, the same bare key, stands");
    assert.deepEqual([wsA.sent, wsB.sent], [[], []], "nothing asked of either kernel");
    wsB.frame(barsPatch(0, bar("b-2", 2010, 2015, "B's second"), 610));
    m = last(barsOf(emitted));
    assert.deepEqual([ids(m.turns[HOST + ":" + SID_A]), ids(m.turns[HOST_B + ":" + SID_A])], [["seg-1", "seg-2"], ["b-1", "b-2"]], "and B's onto B's");
    assert.deepEqual([wsA.sent, wsB.sent], [[], []]);
    fm.conns.get(HOST).closed = true; fm.conns.get(HOST_B).closed = true;
  });
});

// ── a kernel before T278c (2026-09-19) ──────────────────────────────────────────────────────────────────────────────
// A remote kernel from a750f860d (2026-09-03, the slot protocol) to 328e46c26 (T278c, 2026-09-09; upstream kernels in
// that window, and fork main from its 2026-09-05 fold until it folded T278c) keys the bars frame's judging as a FLAT
// list (bykeys:sid,t,judge,t1) and ships its own key list (_keys). This receiver's table says dictlist:k and cannot key
// that list, and the kernel's rule for a collection its kind cannot key is the whole frame, never zero entries
// (_delta_split); the receiver follows it and seeds no base. Seeded instead, the first judging patch assembled to the
// patched entries alone, per lane and in the old entry shape, and the lane's marks collapsed between full frames. The
// whole frame renders through judgingToWire, which converts the flat list; every patch from that kernel recovers, so its
// bars cross whole per change, the pre-delta cost. A future collection keyed by another table takes the same road. The
// refused seed is the one silent shape whose repair never repairs (a bad base or a malformed patch files nothing either,
// but the whole frame they earn seeds). The seed itself is not the event: a remote before the slot protocol sends the
// same flat list in whole frames and never a patch, and at the seed the two are one frame, so a row there would name a
// remote behaving as designed (its whole frames render as they always did). The event is the first PATCH that finds no
// base because the seed was refused: the receiver reports each such patch, and federation says it once per distinct
// row (ev delta-unkeyed-base; why the slot, the collection and shape the table could not key, and the remote's build
// when the /tunnels row names one), never per patch, per re-sent whole frame (an idle slot reposts one about every
// 60 s) or per redial that reproduces it.
const oldJudging = (t: number, judge: string, t1: number | null) => ({ sid: SID_A, t, judge, t1, kind: "run", text: "judged" });
const oldKey = (e: any) => SID_A + SEP + e.t + SEP + e.judge + SEP + e.t1;   // bykeys:sid,t,judge,t1, joined by the unit separator
const oldFull = (sid: string, judging: any[]) =>
  ({ type: "bars", turns: { [sid]: [bar("seg-1", 1000, 1005, "first")] }, judging, messages: [], now: 500, warming: false,
     _keys: { turns: [sid + SEP + "seg-1"], judging: judging.map(oldKey), messages: [] } });
const REFUSED_JUDGING = "bars judging dictlist:k is a list";   // the row's why: the slot, the collection, its kind in the table and the container the table could not key
const unkeyedRows = (sent: any[]) =>
  sent.filter((x) => x && x.type === "clientDiag" && x.what === "hostconn" && x.data && x.data.ev === "delta-unkeyed-base").map((x) => x.data);
// console.error, counted for the test's span (the sibling unknown-slot arm prints its line; this one is counted too)
async function countingConsoleErrors(fn: (errors: string[]) => void | Promise<void>): Promise<void> {
  const errors: string[] = [];
  const real = console.error;
  console.error = (...args: any[]) => { errors.push(args.map(String).join(" ")); };
  try { await fn(errors); } finally { console.error = real; }
}

test("a bars full frame from a kernel before T278c (judging a flat list, its own _keys) seeds no base and is said by nothing: the frame renders whole through judgingToWire; its first patch asks that kernel for the whole slot and is the event said, once, naming the collection and shape", async () => {
  await withManager("timeline", ({ fm, emitted, sent }) => countingConsoleErrors((errors) => {
    seedLocalTimeline(fm);
    fm.openRemote(HOST, true);
    const ws = last(FakeWS.made);
    ws.open();
    const e1 = oldJudging(1001, "unblocker", 1002);
    const full = oldFull(SID_A, [e1]);
    ws.frame(full);
    let m = last(barsOf(emitted));
    assert.deepEqual(ids(m.turns[HOST + ":" + SID_A]), ["seg-1"], "the full frame merges as any other");
    assert.deepEqual(m.judging[HOST + ":" + SID_A].map((c: any) => c.j), ["unblocker"], "the flat list rendered compact through judgingToWire, under the prefixed lane");
    ws.frame(full);   // the idle slot's repost: refused again
    assert.deepEqual(unkeyedRows(sent), [], "the refused seed alone files nothing: at the seed a remote that never patches and one that will send the same frame, and the frame rendered");
    assert.equal(errors.length, 0, "and nothing on the console: " + errors.join(" | "));
    const before = barsOf(emitted).length;
    const e2 = oldJudging(1011, "planner", null);
    ws.frame({ type: "delta", slot: "bars", base: 0, rev: 1, coll: { judging: { set: { [oldKey(e2)]: e2 } } }, rest: { now: 515 } });
    assert.deepEqual(ws.sent, [{ type: "needSlot", slot: "bars" }], "the patch is not applied onto a frame this receiver could not key: that kernel is asked for the whole slot on this conn");
    assert.equal(barsOf(emitted).length, before, "nothing emitted for the patch");
    assert.deepEqual(localAsks(sent), [], "the local kernel is not asked");
    assert.deepEqual(unkeyedRows(sent), [{ host: HOST, ev: "delta-unkeyed-base", why: REFUSED_JUDGING }],
      "the patch is the event: one hostconn row under the family's keys, naming the host, the slot, the collection and the shape this side's table could not key (no build: this rig has no /tunnels row)");
    assert.equal(errors.length, 1, "and once on the console: " + errors.join(" | "));
    assert.match(errors[0], /a bars patch from TESTHOST arrived/);
    assert.match(errors[0], /judging dictlist:k is a list/);
    // the whole slot the ask earns, as that kernel sends it: the flat list grown by the entry, keys and all
    ws.frame({ ...full, judging: [e1, e2], now: 515, _keys: { ...full._keys, judging: [oldKey(e1), oldKey(e2)] } });
    m = last(barsOf(emitted));
    assert.deepEqual(m.judging[HOST + ":" + SID_A].map((c: any) => c.j), ["unblocker", "planner"],
      "both marks, compact, from the whole frame (a seeded base would have assembled the patched entry alone, in the old shape, under the lane)");
    assert.deepEqual(ids(m.turns[HOST + ":" + SID_A]), ["seg-1"]);
    assert.equal(unkeyedRows(sent).length, 1, "the re-sent whole frame is refused again and says nothing");
    ws.frame({ type: "delta", slot: "bars", base: 0, rev: 1, coll: { judging: { set: {} } }, rest: { now: 520 } });
    assert.deepEqual(ws.sent, [{ type: "needSlot", slot: "bars" }, { type: "needSlot", slot: "bars" }], "every patch from that kernel recovers: the slot crosses whole per change");
    assert.deepEqual(localAsks(sent), []);
    assert.equal(unkeyedRows(sent).length, 1, "the second patch is the same event (the same reason, the same remote): said no more");
    assert.equal(errors.length, 1, "one console line for the whole exchange");
    fm.conns.get(HOST).closed = true;
  }));
});

test("two hosts before T278c: the row is per host (per conn), and a redial on a conn that reproduces the same event (the same reason, the same remote) is said no more", async () => {
  await withManager("timeline", ({ fm, emitted, sent }) => countingConsoleErrors((errors) => {
    seedLocalTimeline(fm);
    const HOST_B = "TESTHOSTB";
    const full = oldFull(SID_A, [oldJudging(1001, "unblocker", 1002)]);
    const patch = (now: number) => ({ type: "delta", slot: "bars", base: 0, rev: 1, coll: { judging: { set: {} } }, rest: { now } });
    fm.openRemote(HOST, true);
    const wsA = last(FakeWS.made);
    wsA.open();
    wsA.frame(full);
    fm.openRemote(HOST_B, true);
    const wsB = last(FakeWS.made);
    wsB.open();
    wsB.frame(full);
    assert.deepEqual(unkeyedRows(sent), [], "two refused seeds and no patch yet: nothing said");
    wsA.frame(patch(505)); wsB.frame(patch(605));
    assert.deepEqual(unkeyedRows(sent), [{ host: HOST, ev: "delta-unkeyed-base", why: REFUSED_JUDGING }, { host: HOST_B, ev: "delta-unkeyed-base", why: REFUSED_JUDGING }], "one row per host: each conn's own latch");
    wsA.frame(full); wsB.frame(full);   // the resyncs' whole frames: refused again
    wsA.frame(patch(510)); wsB.frame(patch(610));   // the next change's patches: the same event on each conn
    assert.equal(unkeyedRows(sent).length, 2, "said no more");
    // a redial on A's conn (the watchdog's abandon-and-dial) mints a fresh receiver, which refuses the same seed and reports
    // its first patch; the latch is the CONN's and keyed on the event, and the event is the same (the same reason, and no
    // /tunnels row names a build in this rig), so the redialed socket's report is said no more
    const conn = fm.conns.get(HOST);
    clock += REMOTE_STALE_MS + 1000;
    fm.watchdog(clock);
    const wsA2 = last(FakeWS.made);
    assert.notEqual(wsA2, wsA, "A redialed");
    assert.equal(fm.conns.get(HOST), conn, "on the same conn");
    wsA2.open();
    wsA2.frame(full);
    wsA2.frame(patch(700));
    assert.deepEqual(wsA2.sent, [{ type: "needSlot", slot: "bars" }], "asked all the same, on the new socket: the ask is the resync");
    assert.equal(unkeyedRows(sent).length, 2, "the redialed socket's report is not said again: the same reason from the same remote is the event already said");
    assert.equal(errors.length, 2, "two console lines, one per host");
    assert.deepEqual(ids(last(barsOf(emitted)).turns[HOST_B + ":" + SID_A]), ["seg-1"], "both hosts' frames rendered whole throughout");
    fm.conns.get(HOST).closed = true; fm.conns.get(HOST_B).closed = true;
  }));
});

test("the same vintage's feed full frame keys asks as this table does and seeds as any other: its patch applies and nothing is asked", async () => {
  await withManager("fleet", ({ fm, emitted, sent }) => {
    fm.inbound("", { type: "feed", now: 500, buildId: 7, asks: [card(SID_L, 1)], ledgers: [ledger(SID_L, "web")] });
    fm.openRemote(HOST, true);
    const ws = last(FakeWS.made);
    ws.open();
    ws.frame({ type: "feed", now: 500, buildId: 1, asks: [card(SID_A, 1)], ledgers: [ledger(SID_A, "api")], _keys: { asks: [SID_A + ":g1"] } });
    const before = feedsOf(emitted).length;
    ws.frame({ type: "delta", slot: "feed", base: 0, rev: 1, coll: { asks: { set: { [SID_A + ":g2"]: card(SID_A, 2) } } }, rest: { now: 505, buildId: 2 } });
    assert.equal(feedsOf(emitted).length, before + 1, "the patch applied: the key list rides beside a collection this receiver keys the same way");
    assert.deepEqual(last(feedsOf(emitted)).asks.map((a: any) => a.itemId).sort(), [SID_L + ":g1", SID_A + ":g1", SID_A + ":g2"].sort());
    assert.deepEqual(ws.sent, [], "nothing asked of the remote");
    assert.deepEqual(localAsks(sent), []);
    assert.deepEqual(unkeyedRows(sent), [], "its feed frame seeded: nothing to say");
    fm.conns.get(HOST).closed = true;
  });
});

// ── a kernel before the slot protocol (2026-09-19) ──────────────────────────────────────────────────────────────────
// A remote before a750f860d (8a4d48f10 among them) sends the same flat judging in whole frames and never a patch. The
// receiver refuses its seed too, and that costs nothing: its whole frames render as they always did, and no patch ever
// asks for one. No row names it (corner 2d of tests/test_federated_capability_corners_served.py, the served twin of this
// pin): the row is the first patch's, and a row at the seed would have named a remote behaving as designed, since the
// seed cannot tell this remote from one that will patch.
test("a remote before the slot protocol (the same flat judging, no _keys, whole frames only) is refused as a base and never named: its whole frames render, and no row is filed without a patch", async () => {
  await withManager("timeline", ({ fm, emitted, sent }) => countingConsoleErrors((errors) => {
    seedLocalTimeline(fm);
    fm.openRemote(HOST, true);
    const ws = last(FakeWS.made);
    ws.open();
    const preDelta = (judging: any[], now: number) =>
      ({ type: "bars", turns: { [SID_A]: [bar("seg-1", 1000, 1005, "first")] }, judging, messages: [], now, warming: false });
    const e1 = oldJudging(1001, "unblocker", 1002), e2 = oldJudging(1011, "planner", null);
    ws.frame(preDelta([e1], 500));
    assert.deepEqual(last(barsOf(emitted)).judging[HOST + ":" + SID_A].map((c: any) => c.j), ["unblocker"], "rendered whole, compact, through judgingToWire");
    const before = barsOf(emitted).length;
    assert.ok(before > 0);
    ws.frame(preDelta([e1, e2], 515));   // the change, whole, as that vintage sends every change
    ws.frame(preDelta([e1, e2], 575));   // the idle repost a minute on
    assert.equal(barsOf(emitted).length, before + 2, "each whole frame re-emits the merge");
    assert.deepEqual(last(barsOf(emitted)).judging[HOST + ":" + SID_A].map((c: any) => c.j), ["unblocker", "planner"], "the change shows");
    assert.deepEqual(ws.sent, [], "nothing asked: no patch, so no resync");
    assert.deepEqual(unkeyedRows(sent), [], "no row: nothing names a remote behaving as designed (the row is the first patch's, and none comes)");
    assert.equal(errors.length, 0, "and nothing on the console: " + errors.join(" | "));
    fm.conns.get(HOST).closed = true;
  }));
});

// ── the latch is keyed on the event, not the conn's life (2026-09-19) ───────────────────────────────────────────────
// Conn.saidDelta holds the ROWS a conn has filed (ev and why; the why carries the slot, the reason and the remote's build
// as the hub's /tunnels row names it, Conn.peerSha), so the same event files once however many patches, reposts or
// redials produce it, while a row that would say something different files: another collection or shape refused, or the
// same refusal from a remote that came back on another build. A latch on the conn's life would have missed the case an
// admin looks at: a redial that crosses the remote's deploy, the new build refusing the seed too, said by nothing because
// the old row outlived what it described. No time window (the repo's rule: the event, not a period that approximates
// it). Both breadcrumbs share the rule (sayDeltaOnce).
const barsPatchEmpty = (now: number) => ({ type: "delta", slot: "bars", base: 0, rev: 1, coll: { judging: { set: {} } }, rest: { now } });

test("the refused-base row is keyed on the event: a second collection refused on the same conn is its own row, and a redial that reproduces the first refusal (the same reason, the same remote) is not", async () => {
  await withManager("timeline", ({ fm, sent }) => countingConsoleErrors((errors) => {
    seedLocalTimeline(fm);
    fm.openRemote(HOST, true);
    const ws = last(FakeWS.made);
    ws.open();
    const full = oldFull(SID_A, [oldJudging(1001, "unblocker", 1002)]);
    ws.frame(full); ws.frame(barsPatchEmpty(505));
    assert.deepEqual(unkeyedRows(sent).map((r) => r.why), [REFUSED_JUDGING]);
    // the same kernel's frame keyed by yet another table: turns as a LIST where this table says dictlist:id (judging keyed
    // as this table does, so the refusal is turns' alone): a different reason, its own row
    const turnsAsList = { type: "bars", turns: [bar("seg-1", 1000, 1005, "first")], judging: {}, messages: [], now: 600, warming: false };
    ws.frame(turnsAsList); ws.frame(barsPatchEmpty(605));
    assert.deepEqual(unkeyedRows(sent).map((r) => r.why), [REFUSED_JUDGING, "bars turns dictlist:id is a list"], "a refusal for another collection is its own row, naming it");
    assert.equal(errors.length, 2);
    ws.frame(turnsAsList); ws.frame(barsPatchEmpty(610));
    assert.equal(unkeyedRows(sent).length, 2, "the same again: nothing");
    // a redial (the watchdog's abandon-and-dial): the fresh receiver refuses the FIRST shape again and reports its patch;
    // the row would read as the first did, so it is not filed
    const conn = fm.conns.get(HOST);
    clock += REMOTE_STALE_MS + 1000;
    fm.watchdog(clock);
    const ws2 = last(FakeWS.made);
    assert.notEqual(ws2, ws, "redialed");
    assert.equal(fm.conns.get(HOST), conn, "on the same conn");
    ws2.open(); ws2.frame(full); ws2.frame(barsPatchEmpty(700));
    assert.deepEqual(ws2.sent, [{ type: "needSlot", slot: "bars" }], "asked on the new socket: the resync is per patch");
    assert.equal(unkeyedRows(sent).length, 2, "the redial reproduced an event already said (the same reason, the same remote): no row");
    assert.equal(errors.length, 2);
    fm.conns.get(HOST).closed = true;
  }));
});

// the hub's /tunnels answer, as poll() reads it: one row for TESTHOST, `kernelSha` the remote kernel's build (the sha it
// booted from, as the hub's supervisor read it off the peer's /version), which poll() carries onto the conn (Conn.peerSha)
function tunnelsStub(row: Record<string, any>): () => void {
  const g: any = globalThis;
  const had = "fetch" in g, prev = g.fetch;
  g.fetch = async () => ({ ok: true, json: async () => ({ tunnels: [{ host: HOST, hasToken: true, localPort: 5, status: "up", ...row }] }) });
  return () => { if (had) g.fetch = prev; else delete g.fetch; };
}

test("…and on the remote's build: the same refusal from the same build across a redial files nothing; a redial that finds the /tunnels row naming a new build (the remote redeployed) files the row again, naming the build", async () => {
  const row: Record<string, any> = { kernelSha: "aaaaaaaaa" };
  const restore = tunnelsStub(row);
  try {
    await withManager("timeline", ({ fm, sent }) => countingConsoleErrors(async (errors) => {
      seedLocalTimeline(fm);
      fm.openRemote(HOST, true);
      const ws = last(FakeWS.made);
      await fm.poll();   // the row in hand
      const conn = fm.conns.get(HOST);
      assert.equal(conn.peerSha, "aaaaaaaaa", "poll() read the row's kernelSha onto the conn");
      ws.open();
      const full = oldFull(SID_A, [oldJudging(1001, "unblocker", 1002)]);
      ws.frame(full); ws.frame(barsPatchEmpty(505));
      assert.deepEqual(unkeyedRows(sent), [{ host: HOST, ev: "delta-unkeyed-base", why: REFUSED_JUDGING + " @aaaaaaaaa" }], "the row names the remote's build");
      assert.equal(errors.length, 1);
      assert.match(errors[0], /aaaaaaaaa/, "so does the console line");
      // a redial to the SAME build (a blip; the watchdog's abandon-and-dial): the same event, nothing
      clock += REMOTE_STALE_MS + 1000;
      fm.watchdog(clock);
      const ws2 = last(FakeWS.made);
      assert.notEqual(ws2, ws, "redialed");
      ws2.open(); ws2.frame(full); ws2.frame(barsPatchEmpty(600));
      assert.deepEqual(ws2.sent, [{ type: "needSlot", slot: "bars" }], "asked: the resync is per patch");
      assert.equal(unkeyedRows(sent).length, 1, "the same refusal from the same build: not said again, however many redials");
      // the remote restarts on a new build: the hub's supervisor re-reads its /version, the row's kernelSha changes, the
      // next poll carries it onto the conn, and the redialed socket's first patch after the refused seed is news
      row.kernelSha = "bbbbbbbbb";
      await fm.poll();
      assert.equal(conn.peerSha, "bbbbbbbbb");
      clock += REMOTE_STALE_MS + 1000;
      fm.watchdog(clock);
      const ws3 = last(FakeWS.made);
      assert.notEqual(ws3, ws2, "redialed again");
      assert.equal(fm.conns.get(HOST), conn, "the same conn throughout: the latch is the conn's, and the event moved");
      ws3.open(); ws3.frame(full); ws3.frame(barsPatchEmpty(700));
      assert.deepEqual(unkeyedRows(sent).map((r) => r.why), [REFUSED_JUDGING + " @aaaaaaaaa", REFUSED_JUDGING + " @bbbbbbbbb"], "the redial across the deploy files the row again, naming the new build");
      assert.equal(errors.length, 2);
      assert.match(errors[1], /bbbbbbbbb/);
      ws3.frame(full); ws3.frame(barsPatchEmpty(705));
      assert.equal(unkeyedRows(sent).length, 2, "and the new build's row is latched like the old one's");
      fm.conns.get(HOST).closed = true;
    }));
  } finally { restore(); }
});

test("the unknown-slot breadcrumb shares the rule: the same slot from the same build across a redial is said no more, and a redial that finds a new build says it again, naming the build", async () => {
  const row: Record<string, any> = { kernelSha: "aaaaaaaaa" };
  const restore = tunnelsStub(row);
  try {
    await withManager("timeline", ({ fm, sent }) => countingConsoleErrors(async (errors) => {
      seedLocalTimeline(fm);
      const ws = attached(fm);
      await fm.poll();
      const rows = () => sent.filter((x) => x && x.type === "clientDiag" && x.what === "hostconn" && x.data && x.data.ev === "delta-unknown-slot").map((x) => x.data);
      const lanes = (base: number) => ({ type: "delta", slot: "lanes", base, rev: base + 1, coll: {}, rest: { now: 505 } });
      ws.frame(lanes(0)); ws.frame(lanes(1));
      assert.deepEqual(rows(), [{ host: HOST, ev: "delta-unknown-slot", why: "lanes @aaaaaaaaa" }], "said once, naming the slot and the remote's build");
      assert.equal(errors.length, 1);
      assert.match(errors[0], /aaaaaaaaa/);
      clock += REMOTE_STALE_MS + 1000;
      fm.watchdog(clock);
      const ws2 = last(FakeWS.made);
      assert.notEqual(ws2, ws, "redialed");
      ws2.open(); ws2.frame(lanes(0));
      assert.equal(rows().length, 1, "the same slot from the same build on the redialed socket: not again");
      assert.deepEqual(ws2.sent, [{ type: "needSlot", slot: "lanes" }], "…but asked, on the new socket");
      row.kernelSha = "bbbbbbbbb";
      await fm.poll();
      clock += REMOTE_STALE_MS + 1000;
      fm.watchdog(clock);
      const ws3 = last(FakeWS.made);
      assert.notEqual(ws3, ws2);
      ws3.open(); ws3.frame(lanes(0));
      assert.deepEqual(rows().map((r) => r.why), ["lanes @aaaaaaaaa", "lanes @bbbbbbbbb"], "the redial across the remote's deploy says it again, naming the new build");
      assert.equal(errors.length, 2);
      assert.match(errors[1], /bbbbbbbbb/);
      fm.conns.get(HOST).closed = true;
    }));
  } finally { restore(); }
});

// The latch's key is this side's to bound (review round 4: keyed on the wire slot name, 200 invented slot names from one
// remote were 200 rows, 200 console lines and 200 Set entries, held across a redial, and the bound was the peer's). Now
// every slot this bundle does not decode is one key per build (federation.ts UNKNOWN_SLOT_KEY); the first name rides in the
// row, cut to 32 characters so the kernel's 64-character cut of `why` (CLIENT_DIAG_STR_MAX) keeps the build tag behind it;
// and Conn.saidDelta holds at most seven keys per build the /tunnels row has named on the conn (the six refusals this
// side's table can produce, and the one unknown-slot marker).
test("a remote that names a new unknown slot in every patch spends one row, one console line and one latch key per build: 200 names are one row naming the first, a redial adds none, a new build adds one, and a long name is cut so the build tag survives the kernel's cut", async () => {
  const row: Record<string, any> = { kernelSha: "aaaaaaaaa" };
  const restore = tunnelsStub(row);
  try {
    await withManager("timeline", ({ fm, sent }) => countingConsoleErrors(async (errors) => {
      seedLocalTimeline(fm);
      const ws = attached(fm);
      await fm.poll();
      const conn = fm.conns.get(HOST);
      const rows = () => sent.filter((x) => x && x.type === "clientDiag" && x.what === "hostconn" && x.data && x.data.ev === "delta-unknown-slot").map((x) => x.data);
      const lane = (i: number) => ({ type: "delta", slot: "lane" + i, base: 0, rev: 1, coll: {}, rest: { now: 505 } });
      for (let i = 0; i < 200; i++) ws.frame(lane(i));
      assert.deepEqual(rows(), [{ host: HOST, ev: "delta-unknown-slot", why: "lane0 @aaaaaaaaa" }], "200 slot names from one remote: one row, naming the first seen and the build");
      assert.equal(errors.length, 1, "one console line");
      assert.equal(conn.saidDelta.size, 1, "one latch key: the set's size is this side's, not the remote's");
      assert.equal(ws.sent.length, 200);
      assert.ok(ws.sent.every((m: any, i: number) => m.type === "needSlot" && m.slot === "lane" + i), "asked per patch all the same, each by its wire name: the ask is the resync, and the kernel coalesces asks");
      clock += REMOTE_STALE_MS + 1000;
      fm.watchdog(clock);
      const ws2 = last(FakeWS.made);
      assert.notEqual(ws2, ws, "redialed");
      ws2.open();
      for (let i = 200; i < 400; i++) ws2.frame(lane(i));
      assert.equal(rows().length, 1, "200 more names on the redialed socket: the same event, no row");
      assert.equal(conn.saidDelta.size, 1);
      // the remote redeploys: the row's kernelSha changes, a poll lands it, a redial; the first patch this bundle does not
      // decode from the new build is one more row and one more key, its (long) name cut so the build tag stands
      row.kernelSha = "bbbbbbbbb";
      await fm.poll();
      clock += REMOTE_STALE_MS + 1000;
      fm.watchdog(clock);
      const ws3 = last(FakeWS.made);
      assert.notEqual(ws3, ws2);
      ws3.open();
      const long = "l".repeat(80);
      ws3.frame({ type: "delta", slot: long, base: 0, rev: 1, coll: {}, rest: {} });
      assert.deepEqual(rows().map((r) => r.why), ["lane0 @aaaaaaaaa", "l".repeat(32) + " @bbbbbbbbb"], "the new build is a new key: one row, the peer's name cut to 32 so the build tag stands inside the kernel's 64-character cut of why");
      assert.ok(last(rows()).why.length <= 64, "under the kernel's cut");
      assert.deepEqual(ws3.sent, [{ type: "needSlot", slot: long }], "asked with the whole name: the ask is the wire's");
      ws3.frame({ type: "delta" }); ws3.frame(lane(1));
      assert.equal(rows().length, 2, "a slotless patch and another name under the same build: nothing");
      assert.equal(conn.saidDelta.size, 2, "two keys for two builds");
      assert.equal(errors.length, 2);
      fm.conns.get(HOST).closed = true;
    }));
  } finally { restore(); }
});

// ── connect() reached with a live socket (2026-09-19) ───────────────────────────────────────────────────────────────
// The poll, localUp and the watchdog dial only a conn whose socket is null or CLOSED, but a 2 s retry timer does not look
// first: the onclose redial a dead socket armed lands after the watchdog's "redial" verdict (or a poll) already dialed the
// conn a fresh socket, and the constructor-throw retry lands after the same. connect() returns at its already-connecting/
// open guard, and the per-dial receiver reset sits BELOW that guard: at the top it would wipe the LIVE socket's base under
// the patches applying onto it, and the next patch would ask that kernel for the whole slot for nothing (the placement
// probe of round 4). The behavioural assertion comes first (the base kept: the patch applies, nothing asked); the
// receiver's identity is the mechanism, checked after. The feed half, the first guard (a detached conn's timer, a conn
// whose row went down) and the CONNECTING state are in federation-remote-feed-delta.test.ts (review round 5).
test("the onclose retry timer landing after the watchdog already redialed the conn: connect() returns at its open guard and the live socket's base stands (the next patch applies, nothing asked)", async () => {
  await withManager("timeline", ({ fm, emitted }) => {
    seedLocalTimeline(fm);
    const ws = attached(fm);
    const conn = fm.conns.get(HOST);
    ws.readyState = 3;
    const redials = armedRedials(() => ws.onclose!({ code: 1006, wasClean: false }));   // the socket dropped: its 2 s redial, held
    assert.equal(redials.length, 1, "one redial armed");
    clock += REMOTE_REDIAL_MS + 1000;   // the watchdog's redial verdict on the CLOSED socket lands before the timer
    fm.watchdog(clock);
    const ws2 = last(FakeWS.made);
    assert.notEqual(ws2, ws, "the watchdog redialed");
    ws2.open();
    ws2.frame(remoteBars());
    ws2.frame(barsPatch(0, bar("seg-2", 1010, 1015, "second"), 505));
    assert.deepEqual(ids(last(barsOf(emitted)).turns[HOST + ":" + SID_A]), ["seg-1", "seg-2"], "the new socket's base took a patch");
    const before = barsOf(emitted).length, vd = conn.viewDeltas;
    assert.ok(before > 0);
    redials[0]();   // the late timer: connect() on a conn whose socket is OPEN
    assert.equal(conn.ws, ws2, "no new socket: the guard returned");
    ws2.frame(barsPatch(1, bar("seg-3", 1020, 1025, "third"), 515));
    assert.deepEqual(ws2.sent, [], "nothing asked: the live socket's base stood through the late call and the patch applied onto it");
    assert.equal(barsOf(emitted).length, before + 1, "the patch re-emitted the merge");
    assert.deepEqual(ids(last(barsOf(emitted)).turns[HOST + ":" + SID_A]), ["seg-1", "seg-2", "seg-3"]);
    assert.equal(conn.viewDeltas, vd, "the mechanism: a call that dialed nothing minted nothing");
    fm.conns.get(HOST).closed = true;
  });
});

test("the constructor-throw retry timer landing after the watchdog dialed: the same guard, the same base kept", async () => {
  await withManager("timeline", ({ fm, emitted }) => {
    seedLocalTimeline(fm);
    const ws = attached(fm);
    const conn = fm.conns.get(HOST);
    ws.readyState = 3;
    clock += REMOTE_REDIAL_MS + 1000;
    // the watchdog's redial verdict dials, and the constructor throws once (a browser refusing the URL): connect() arms its
    // 2 s retry and the dead socket stays on the conn
    const g: any = globalThis;
    const Fake = g.WebSocket;
    g.WebSocket = function () { g.WebSocket = Fake; throw new Error("refused"); };
    const retries = armedRedials(() => fm.watchdog(clock));
    assert.equal(retries.length, 1, "the constructor-throw retry, held");
    assert.equal(conn.ws, ws, "the dead socket still on the conn");
    clock += REMOTE_REDIAL_MS + 1000;
    fm.watchdog(clock);   // the next tick's redial verdict: the constructor answers now
    const ws2 = last(FakeWS.made);
    assert.notEqual(ws2, ws, "a fresh socket");
    ws2.open();
    ws2.frame(remoteBars());
    ws2.frame(barsPatch(0, bar("seg-2", 1010, 1015, "second"), 505));
    assert.deepEqual(ids(last(barsOf(emitted)).turns[HOST + ":" + SID_A]), ["seg-1", "seg-2"]);
    const before = barsOf(emitted).length, vd = conn.viewDeltas;
    assert.ok(before > 0);
    retries[0]();   // the late retry: connect() with the fresh socket OPEN
    assert.equal(conn.ws, ws2, "no new socket");
    ws2.frame(barsPatch(1, bar("seg-3", 1020, 1025, "third"), 515));
    assert.deepEqual(ws2.sent, [], "nothing asked: the base stood");
    assert.equal(barsOf(emitted).length, before + 1);
    assert.deepEqual(ids(last(barsOf(emitted)).turns[HOST + ":" + SID_A]), ["seg-1", "seg-2", "seg-3"]);
    assert.equal(conn.viewDeltas, vd);
    fm.conns.get(HOST).closed = true;
  });
});

// The build in the key is the /tunnels row's as poll() last read it, so it lags the remote's real build by one supervisor
// pass and one poll: a reason that first fires on a redialed socket inside that lag files under the OLD build and again
// under the new one when the poll lands it. That over-report is bounded: one extra row per (conn, slot, reason) per change
// of the row's sha (a remote deploy the hub's row records), never per poll window (a poll that re-reads the same sha adds
// no key) and never a third through "" (the row keeps the last successful probe's sha while the peer is down: kernel.py
// _remote_public). A fix followed by a rollback is the design: the key names a state (this conn, this slot, this reason,
// this build), and a rollback to a build with the same reason returns to a state already said, so no row.
test("the stale-sha over-report is bounded to one extra row per conn, slot and reason per deploy: a reason first said on a redialed socket under the old build is said again when the poll lands the new one, and no third (the same reason, a poll re-reading the same sha, a rollback to the old build); another reason is its own row", async () => {
  const row: Record<string, any> = { kernelSha: "aaaaaaaaa" };
  const restore = tunnelsStub(row);
  try {
    await withManager("timeline", ({ fm, sent }) => countingConsoleErrors(async (errors) => {
      seedLocalTimeline(fm);
      const ws = attached(fm);   // the remote on build a serves a keyable frame: the refusal has never fired on this conn
      await fm.poll();
      const conn = fm.conns.get(HOST);
      assert.equal(conn.peerSha, "aaaaaaaaa");
      assert.deepEqual(unkeyedRows(sent), [], "nothing refused on the old build");
      // the remote redeploys onto build b and restarts; the socket dies and the watchdog redials BEFORE the hub's
      // supervisor has re-read the peer's /version (the row still says a): the new build's frame is refused and its
      // first patch files under the stale build
      clock += REMOTE_STALE_MS + 1000;
      fm.watchdog(clock);
      const ws2 = last(FakeWS.made);
      assert.notEqual(ws2, ws, "redialed");
      assert.equal(fm.conns.get(HOST), conn, "on the same conn");
      const full = oldFull(SID_A, [oldJudging(1001, "unblocker", 1002)]);
      ws2.open(); ws2.frame(full); ws2.frame(barsPatchEmpty(600));
      assert.deepEqual(unkeyedRows(sent).map((r) => r.why), [REFUSED_JUDGING + " @aaaaaaaaa"], "the first row names the build the hub's row last had: the over-report's extra row");
      // the supervisor's pass and the poll land the new sha; the same reason (the resync's whole frame refused again, its
      // next patch) is news under the new build: the second row, the one naming the build that refused
      row.kernelSha = "bbbbbbbbb";
      await fm.poll();
      assert.equal(conn.peerSha, "bbbbbbbbb");
      ws2.frame(full); ws2.frame(barsPatchEmpty(605));
      assert.deepEqual(unkeyedRows(sent).map((r) => r.why), [REFUSED_JUDGING + " @aaaaaaaaa", REFUSED_JUDGING + " @bbbbbbbbb"], "exactly two rows: one under the old build, one under the new");
      assert.equal(errors.length, 2);
      // no third: the same reason again, a poll that re-reads the same sha (a new poll window is not a new key), and the
      // same reason after it
      ws2.frame(full); ws2.frame(barsPatchEmpty(610));
      await fm.poll();
      ws2.frame(full); ws2.frame(barsPatchEmpty(615));
      assert.equal(unkeyedRows(sent).length, 2, "no third row: the same reason under the same build, across a poll that re-read the same sha (the bound is per sha change, not per poll window)");
      // a rollback to build a with the same reason: a state this conn already said, so no row (designed, not a limitation)
      row.kernelSha = "aaaaaaaaa";
      await fm.poll();
      assert.equal(conn.peerSha, "aaaaaaaaa");
      clock += REMOTE_STALE_MS + 1000;
      fm.watchdog(clock);
      const ws3 = last(FakeWS.made);
      assert.notEqual(ws3, ws2, "redialed across the rollback");
      ws3.open(); ws3.frame(full); ws3.frame(barsPatchEmpty(700));
      assert.deepEqual(ws3.sent, [{ type: "needSlot", slot: "bars" }], "asked all the same: the resync is per patch");
      assert.equal(unkeyedRows(sent).length, 2, "the rollback returns to a state already said (this reason, this build): no row");
      assert.equal(errors.length, 2);
      // a reason that changes inside the lag is a different event, its own row by design, under the same bound
      const turnsAsList = { type: "bars", turns: [bar("seg-1", 1000, 1005, "first")], judging: {}, messages: [], now: 800, warming: false };
      ws3.frame(turnsAsList); ws3.frame(barsPatchEmpty(805));
      assert.deepEqual(unkeyedRows(sent).map((r) => r.why), [REFUSED_JUDGING + " @aaaaaaaaa", REFUSED_JUDGING + " @bbbbbbbbb", "bars turns dictlist:id is a list @aaaaaaaaa"], "another collection refused under a build already in the set is its own row: the key carries the reason");
      assert.equal(errors.length, 3);
      fm.conns.get(HOST).closed = true;
    }));
  } finally { restore(); }
});

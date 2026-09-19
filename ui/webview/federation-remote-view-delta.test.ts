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
import { FederationManager, REMOTE_STALE_MS } from "./federation";

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
    assert.deepEqual(fm.perHostFeedRaw[HOST].asks.map((a: any) => a.itemId), [SID_A + ":g2"], "the reassembled frame is the host's raw base too (a later feedDelta applies onto it)");
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
// already has (ev delta-unknown-slot, why = the slot), and a console line. A patch with no slot at all is said the same
// way and asked for nothing (there is no slot to name). Neither reaches the pane, and the known slot's base stands.
test("a remote patch for a slot this side does not decode is said (a hostconn row naming the slot) and asked for whole on the sending socket; a slotless one is said and dropped; the known slot's base survives", async () => {
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
    assert.deepEqual(rows().map((r) => r.why), ["lanes", ""], "a slotless patch is said too (an empty why)");
    assert.deepEqual(ws.sent, [{ type: "needSlot", slot: "lanes" }], "…and asks for nothing: there is no slot to name");
    ws.frame(barsPatch(0, bar("seg-2", 1010, 1015, "second"), 506));
    assert.deepEqual(ids(last(barsOf(emitted)).turns[HOST + ":" + SID_A]), ["seg-1", "seg-2"], "the bars base held through both: a known slot's patch still applies");
    assert.deepEqual(localAsks(sent), []);
    fm.conns.get(HOST).closed = true;
  });
});

// The condition lasts the conn's life (the slot stays unknown to this bundle), so the row and the console line are said
// once per conn per slot, like the sibling dial-deferred row and the refused-seed row below (Conn.saidDelta); the
// needSlot stays per patch, since it is the resync itself and the kernel coalesces asks. The slot name is the key, the
// empty string for a slotless patch its own; a detach ends the conn and its latch, a redial keeps both.
test("the unknown-slot breadcrumb is latched per conn per slot: a second patch for the slot is asked for whole again but said no more, a second slot has its own row, a re-attached host is said again, a redialed socket is not", async () => {
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
    assert.deepEqual(rows().map((r) => r.why), ["lanes", "marks"], "a second unknown slot has its own row");
    ws.frame({ type: "delta" }); ws.frame({ type: "delta" });
    assert.deepEqual(rows().map((r) => r.why), ["lanes", "marks", ""], "the slotless patch is its own key, said once");
    assert.equal(errors.length, 3);
    // a redial on the conn (the watchdog's abandon-and-dial) keeps the latch: it is the conn's, not the socket's
    const conn = fm.conns.get(HOST);
    clock += REMOTE_STALE_MS + 1000;
    fm.watchdog(clock);
    const ws2 = last(FakeWS.made);
    assert.notEqual(ws2, ws, "redialed");
    assert.equal(fm.conns.get(HOST), conn);
    ws2.open();
    ws2.frame({ type: "delta", slot: "lanes", base: 0, rev: 1, coll: {} });
    assert.deepEqual(rows().map((r) => r.why), ["lanes", "marks", ""], "not said again on the redialed socket");
    assert.deepEqual(ws2.sent, [{ type: "needSlot", slot: "lanes" }], "…but asked, on the new socket");
    // a detach ends the conn and its latch: the re-attached host's first unknown patch is said again
    fm.closeRemote(HOST);
    fm.openRemote(HOST, true);
    const ws3 = last(FakeWS.made);
    ws3.open();
    ws3.frame({ type: "delta", slot: "lanes", base: 0, rev: 1, coll: {} });
    assert.deepEqual(rows().map((r) => r.why), ["lanes", "marks", "", "lanes"], "said again on the new conn");
    assert.equal(errors.length, 4);
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
// but the whole frame they earn seeds), so it is said ONCE per conn per slot: a hostconn row under the family's keys
// (ev delta-unkeyable-seed, why the slot) and a console line, at the refusal, never per patch and never per re-sent
// whole frame (an idle slot reposts one about every 60 s).
const oldJudging = (t: number, judge: string, t1: number | null) => ({ sid: SID_A, t, judge, t1, kind: "run", text: "judged" });
const oldKey = (e: any) => SID_A + SEP + e.t + SEP + e.judge + SEP + e.t1;   // bykeys:sid,t,judge,t1, joined by the unit separator
const oldFull = (sid: string, judging: any[]) =>
  ({ type: "bars", turns: { [sid]: [bar("seg-1", 1000, 1005, "first")] }, judging, messages: [], now: 500, warming: false,
     _keys: { turns: [sid + SEP + "seg-1"], judging: judging.map(oldKey), messages: [] } });
const unkeyableRows = (sent: any[]) =>
  sent.filter((x) => x && x.type === "clientDiag" && x.what === "hostconn" && x.data && x.data.ev === "delta-unkeyable-seed").map((x) => x.data);
// console.error, counted for the test's span (the sibling unknown-slot arm prints its line; this one is counted too)
async function countingConsoleErrors(fn: (errors: string[]) => void | Promise<void>): Promise<void> {
  const errors: string[] = [];
  const real = console.error;
  console.error = (...args: any[]) => { errors.push(args.map(String).join(" ")); };
  try { await fn(errors); } finally { console.error = real; }
}

test("a bars full frame from a kernel before T278c (judging a flat list, its own _keys) seeds no base: the frame renders whole through judgingToWire, its patch asks that kernel for the whole slot, and the refused seed is said once", async () => {
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
    assert.deepEqual(unkeyableRows(sent), [{ host: HOST, ev: "delta-unkeyable-seed", why: "bars" }],
      "the refused seed is said at the refusal: one hostconn row under the family's keys, naming the host and the slot (the one row that attributes the standing cost: every patch from this kernel crosses whole)");
    assert.equal(errors.length, 1, "and once on the console: " + errors.join(" | "));
    assert.match(errors[0], /TESTHOST/);
    assert.match(errors[0], /bars/);
    const before = barsOf(emitted).length;
    const e2 = oldJudging(1011, "planner", null);
    ws.frame({ type: "delta", slot: "bars", base: 0, rev: 1, coll: { judging: { set: { [oldKey(e2)]: e2 } } }, rest: { now: 515 } });
    assert.deepEqual(ws.sent, [{ type: "needSlot", slot: "bars" }], "the patch is not applied onto a frame this receiver could not key: that kernel is asked for the whole slot on this conn");
    assert.equal(barsOf(emitted).length, before, "nothing emitted for the patch");
    assert.deepEqual(localAsks(sent), [], "the local kernel is not asked");
    assert.equal(unkeyableRows(sent).length, 1, "the patch's resync files nothing: the row is the seed's");
    // the whole slot the ask earns, as that kernel sends it: the flat list grown by the entry, keys and all
    ws.frame({ ...full, judging: [e1, e2], now: 515, _keys: { ...full._keys, judging: [oldKey(e1), oldKey(e2)] } });
    m = last(barsOf(emitted));
    assert.deepEqual(m.judging[HOST + ":" + SID_A].map((c: any) => c.j), ["unblocker", "planner"],
      "both marks, compact, from the whole frame (a seeded base would have assembled the patched entry alone, in the old shape, under the lane)");
    assert.deepEqual(ids(m.turns[HOST + ":" + SID_A]), ["seg-1"]);
    assert.equal(unkeyableRows(sent).length, 1, "the re-sent whole frame is refused again and said no more: latched per conn per slot");
    ws.frame({ type: "delta", slot: "bars", base: 0, rev: 1, coll: { judging: { set: {} } }, rest: { now: 520 } });
    assert.deepEqual(ws.sent, [{ type: "needSlot", slot: "bars" }, { type: "needSlot", slot: "bars" }], "every patch from that kernel recovers: the slot crosses whole per change");
    assert.deepEqual(localAsks(sent), []);
    assert.equal(unkeyableRows(sent).length, 1);
    assert.equal(errors.length, 1, "one console line for the whole exchange");
    fm.conns.get(HOST).closed = true;
  }));
});

test("two hosts before T278c: the refused seed is said once per host (per conn, per slot), and a redial on a conn keeps its latch", async () => {
  await withManager("timeline", ({ fm, emitted, sent }) => countingConsoleErrors((errors) => {
    seedLocalTimeline(fm);
    const HOST_B = "TESTHOSTB";
    const full = oldFull(SID_A, [oldJudging(1001, "unblocker", 1002)]);
    fm.openRemote(HOST, true);
    const wsA = last(FakeWS.made);
    wsA.open();
    wsA.frame(full);
    fm.openRemote(HOST_B, true);
    const wsB = last(FakeWS.made);
    wsB.open();
    wsB.frame(full);
    assert.deepEqual(unkeyableRows(sent), [{ host: HOST, ev: "delta-unkeyable-seed", why: "bars" }, { host: HOST_B, ev: "delta-unkeyable-seed", why: "bars" }], "one row per host");
    wsA.frame(full); wsB.frame(full);   // the idle slot's reposts: refused again, said no more
    assert.equal(unkeyableRows(sent).length, 2);
    // a redial on A's conn (the watchdog's abandon-and-dial) mints a fresh receiver, and the fresh receiver refuses the
    // same seed; the latch is the CONN's, not the receiver's, so the redialed socket's refusal is not said again
    const conn = fm.conns.get(HOST);
    clock += REMOTE_STALE_MS + 1000;
    fm.watchdog(clock);
    const wsA2 = last(FakeWS.made);
    assert.notEqual(wsA2, wsA, "A redialed");
    assert.equal(fm.conns.get(HOST), conn, "on the same conn");
    wsA2.open();
    wsA2.frame(full);
    assert.equal(unkeyableRows(sent).length, 2, "the redialed socket's refusal is not said again: the vintage did not change with the socket");
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
    assert.deepEqual(unkeyableRows(sent), [], "its feed frame seeded: nothing to say");
    fm.conns.get(HOST).closed = true;
  });
});

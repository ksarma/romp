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
import { FederationManager } from "./federation";

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

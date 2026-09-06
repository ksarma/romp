// The federation manager REPLAYS the local kernel's views blob — on every merged tabOrder re-emit
// (localViews) and inside the merged lanes payload (perHostTl[LOCAL].views). Both stores adopt a
// blob only when its write sequence is at least the stored one (the 2026-09-05 review): the kernel's
// pusher builds frames from a warmed cache that can predate a write whose ack the pane already
// adopted, and a replay of that older blob would roll the pane back behind the ack. Executed against
// the real manager. Synthetic only (placeholder ids).
import { test } from "node:test";
import assert from "node:assert/strict";
import { FederationManager } from "./federation";

const U = "11111111-2222-3333-4444-555555555555";
const V = "99999999-8888-7777-6666-555555555555";

function withManager(fn: (fm: any, emitted: any[]) => void): void {
  const emitted: any[] = [];
  const store = new Map<string, string>();
  const g: any = globalThis;
  const hadWindow = "window" in g, prevWindow = g.window;
  const hadLS = "localStorage" in g, prevLS = g.localStorage;
  g.window = { dispatchEvent: (ev: any) => { if (ev && ev.data) emitted.push(ev.data); } };
  g.localStorage = { getItem: (k: string) => store.get(k) ?? null, setItem: (k: string, v: string) => { store.set(k, v); } };
  try { fn(new FederationManager(), emitted); } finally {
    if (hadWindow) g.window = prevWindow; else delete g.window;
    if (hadLS) g.localStorage = prevLS; else delete g.localStorage;
  }
}
const lastOf = (emitted: any[], type: string) => emitted.filter((m) => m && m.type === type).pop()!;
const views = (seq: number | undefined, active = "all") => ({ active, tags: [], ...(seq === undefined ? {} : { seq }) });

test("the replayed LOCAL views blob keeps the newest write sequence across tabOrder frames", () => {
  withManager((fm, emitted) => {
    fm.inbound("", { type: "tabOrder", order: [U], tabs: [{ id: U, name: "web" }], views: views(5) });
    assert.equal(lastOf(emitted, "tabOrder").views.seq, 5);
    fm.inbound("", { type: "tabOrder", order: [U], tabs: [{ id: U, name: "web" }], views: views(4) });
    assert.equal(lastOf(emitted, "tabOrder").views.seq, 5, "an older blob (the pusher's cache, delivered after a newer one) does not replace the stored one");
    fm.emitMergedOrder();
    assert.equal(lastOf(emitted, "tabOrder").views.seq, 5, "a synthetic re-emit replays the newest");
    fm.inbound("", { type: "tabOrder", order: [U], tabs: [{ id: U, name: "web" }], views: views(6) });
    assert.equal(lastOf(emitted, "tabOrder").views.seq, 6, "a newer blob lands as before");
    fm.inbound("", { type: "tabOrder", order: [U], tabs: [{ id: U, name: "web" }], views: views(undefined, "untagged") });
    assert.equal(lastOf(emitted, "tabOrder").views.active, "untagged", "a blob without a seq (a kernel from before the stamp) still adopts");
  });
});

test("a kernel's `caps` frame describes THAT kernel: the local one reaches the panes, a remote's is dropped", () => {
  withManager((fm, emitted) => {
    fm.inbound("TESTHOST", { type: "caps", caps: ["tagEdit"] });
    assert.equal(emitted.filter((m) => m.type === "caps").length, 0, "a remote kernel's capabilities would read as the local kernel's — the panes write only the local views store");
    fm.inbound("", { type: "caps", caps: ["tagEdit"] });
    assert.deepEqual(emitted.filter((m) => m.type === "caps"), [{ type: "caps", caps: ["tagEdit"] }], "the local kernel's frame is handed to the panes as-is");
  });
});

// ROUND 6 of the 2026-09-05 review, the refuters' F6/F7: the local caps frame adopts the blob each store's
// gate last turned away and RE-EMITS before the caps frame is handed on — the panes see the local blob only
// through these re-emits, so the restored blob must meet their own gate before their caps door adopts it.
const typesOf = (emitted: any[]) => emitted.map((m) => m && m.type);
test("the local kernel's `caps` frame adopts the blob each replayed store turned away — the restarted kernel's connect push under an older seq — and re-emits it BEFORE the caps frame reaches the panes", () => {
  withManager((fm, emitted) => {
    const lanes = (v: any) => ({ type: "data", data: { sessions: [{ id: U, name: "web" }], turns: {}, messages: [], judging: [], now: 1000, views: v } });
    fm.inbound("", { type: "tabOrder", order: [U], tabs: [{ id: U, name: "web" }], views: views(1000) });
    fm.inbound("", lanes(views(1000)));
    fm.inbound("", { type: "caps", caps: ["tagEdit"] });   // the load's caps frame: nothing was turned away, nothing is re-emitted
    assert.deepEqual(typesOf(emitted), ["tabOrder", "data", "caps"]);
    // the kernel restarted over a store restored from an older copy: its connect push carries seq 900
    fm.inbound("", { type: "tabOrder", order: [U], tabs: [{ id: U, name: "web" }], views: views(900, "untagged") });
    fm.inbound("", lanes(views(900, "untagged")));
    assert.equal(lastOf(emitted, "tabOrder").views.seq, 1000, "the gate turns the push away, as it must before the reconnect event…");
    assert.equal(lastOf(emitted, "data").data.views.seq, 1000, "…so the panes saw it wearing the stored blob");
    const n = emitted.length;
    fm.inbound("", { type: "caps", caps: ["tagEdit"] });
    assert.deepEqual(typesOf(emitted.slice(n)), ["tabOrder", "data", "caps"], "one re-emit per store that adopted, then the caps frame — in that order");
    const order = emitted[n], data = emitted[n + 1];
    assert.equal(order.views.seq, 900, "the merged order now carries the restored store's blob…");
    assert.equal(order.views.active, "untagged");
    assert.equal(order.reemit, true, "…as a synthetic re-emit (no host reported anything)");
    assert.equal(data.data.views.seq, 900, "…and so does the lanes payload");
    assert.deepEqual(data.data.sessions.map((s: any) => s.id), [U], "with its lanes intact");
    fm.inbound("", { type: "tabOrder", order: [U], tabs: [{ id: U, name: "web" }], views: views(899) });
    fm.inbound("", lanes(views(899)));
    assert.equal(lastOf(emitted, "tabOrder").views.seq, 900, "the store's own order gates again from the adopted seq");
    assert.equal(lastOf(emitted, "data").data.views.seq, 900);
    // a REMOTE kernel's caps frame is inert: it neither adopts the blobs just turned away nor re-emits
    const k = emitted.length;
    fm.inbound("TESTHOST", { type: "caps", caps: ["tagEdit"] });
    assert.equal(emitted.length, k, "a remote's caps frame emits nothing here");
    fm.emitMergedOrder();
    assert.equal(lastOf(emitted, "tabOrder").views.seq, 900, "…and the replayed stores stand");
    fm.emitMergedTimeline(false);
    assert.equal(lastOf(emitted, "data").data.views.seq, 900);
    // the LOCAL caps frame does adopt them — the same blobs a remote's frame left alone
    fm.inbound("", { type: "caps", caps: ["tagEdit"] });
    assert.equal(lastOf(emitted, "tabOrder").views.seq, 899);
    assert.equal(lastOf(emitted, "data").data.views.seq, 899);
  });
});

test("a healthy reconnect keeps both stores' gates: the connect push is adopted, the caps frame retains nothing and re-emits nothing, and a pusher frame built before a concurrent write is still turned away", () => {
  withManager((fm, emitted) => {
    const lanes = (v: any) => ({ type: "data", data: { sessions: [{ id: U, name: "web" }], turns: {}, messages: [], judging: [], now: 1000, views: v } });
    fm.inbound("", { type: "tabOrder", order: [U], tabs: [{ id: U, name: "web" }], views: views(1000) });
    fm.inbound("", lanes(views(1000)));
    // the socket came back on the same kernel; another dashboard's write landed meanwhile (seq 1001): the connect push is current
    fm.inbound("", { type: "tabOrder", order: [U], tabs: [{ id: U, name: "web" }], views: views(1001, "untagged") });
    fm.inbound("", lanes(views(1001, "untagged")));
    const n = emitted.length;
    fm.inbound("", { type: "caps", caps: ["tagEdit"] });
    assert.deepEqual(typesOf(emitted.slice(n)), ["caps"], "nothing was turned away: no re-emit, just the caps frame handed on");
    // the pusher thread's frame, built from its cache before that write and enqueued after the caps frame
    fm.inbound("", { type: "tabOrder", order: [U], tabs: [{ id: U, name: "web" }], views: views(1000) });
    fm.inbound("", lanes(views(1000)));
    assert.equal(lastOf(emitted, "tabOrder").views.seq, 1001, "turned away: the gate never opened, so the panes never see the older blob");
    assert.equal(lastOf(emitted, "data").data.views.seq, 1001);
    fm.inbound("", { type: "tabOrder", order: [U], tabs: [{ id: U, name: "web" }], views: views(1001, "untagged") });
    fm.inbound("", lanes(views(1001, "untagged")));
    // that adoption let the kept blobs go: a later caps frame (another reconnect, same store) has nothing to adopt
    const k = emitted.length;
    fm.inbound("", { type: "caps", caps: ["tagEdit"] });
    assert.deepEqual(typesOf(emitted.slice(k)), ["caps"]);
    fm.emitMergedOrder();
    assert.equal(lastOf(emitted, "tabOrder").views.seq, 1001);
  });
});

test("…and across lanes payloads: an older LOCAL data frame keeps the stored views while its lanes still land", () => {
  withManager((fm, emitted) => {
    const lanes = (ids: string[], now: number, v: any) => ({ type: "data", data: { sessions: ids.map((id) => ({ id, name: id.slice(0, 4) })), turns: {}, messages: [], judging: [], now, views: v } });
    fm.inbound("", lanes([U], 1000, views(5)));
    fm.inbound("", lanes([U, V], 1001, views(4)));
    const d = lastOf(emitted, "data").data;
    assert.equal(d.views.seq, 5, "the stored blob stands");
    assert.deepEqual(d.sessions.map((s: any) => s.id), [U, V], "…and the frame's lanes still land — the blob is the only field the seq governs");
    assert.equal(d.now, 1001);
    fm.inbound("", lanes([U, V], 1002, views(7)));
    assert.equal(lastOf(emitted, "data").data.views.seq, 7);
    // a REMOTE host's lanes payload is not the local blob's store at all
    fm.inbound("TESTHOST", lanes([V], 900, views(1)));
    assert.equal(lastOf(emitted, "data").data.views.seq, 7, "a remote kernel's views are its own dashboards' prefs; the merge carries the local blob");
  });
});

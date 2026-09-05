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

// The federated timeline's merge holds and prefix coverage (the user 2026-08-17, whose dashboard —
// freshly reloaded with snape newly attached — showed most local sessions bar-less, connectors from
// a session that wasn't running, and idle remote lanes). Three exact defects, pinned here:
// 1. BOOT BARS RACE: the merged BARS emission was gated only on the local LANES snapshot, so a
//    remote's bars landing first emitted a merged-without-local payload — and the panel's applyBars
//    REPLACES turns wholesale, blanking every local lane until the next local push.
// 2. A lane's fork parent (sessions[].branch.fromId) was never host-prefixed, so remote branch
//    connectors silently missed their vidx lookup and never drew.
// 3. The kernel stripped bar `mids` from the wire (a 2026-07-07 payload audit) that the 2026-08-06
//    merged-view dmid join READS — the join's key set was always empty on live payloads. Source pins.
// 4. BARS AHEAD OF THE LANES (2026-09-11): the pane shim's dispatch queue keeps one frame per whole-state
//    type and a newer skeleton takes the queue's end, so a page behind a burst (a slow machine, a throttled
//    tab) receives [bars, data]. The bars emission held for the missing LOCAL lanes and nothing re-emitted
//    it when they landed, so the pane kept its loader until the kernel's next bars push; the bench's hidden
//    timeline replay under CPU throttling lost every bar this way. The lanes' arrival now emits the held
//    bars, once. Executed against the real manager over the bare stand-in window the direct-delivery test
//    uses. Synthetic only (placeholder ids, the notes-api demo domain).
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { FederationManager } from "./federation";

const FED = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "federation.ts"), "utf8");
const KERNEL = fs.readFileSync(path.resolve(process.cwd(), "..", "kernel", "kernel.py"), "utf8");

test("the merged bars emission waits for the LOCAL bars snapshot, like the lanes hold", () => {
  assert.match(FED, /if \(!\(LOCAL in this\.perHostTl\)\) return;/);
  assert.match(FED, /if \(bars && !\(LOCAL in this\.perHostTlBars\)\) return;/,
    "a remote winning the connect race can no longer blank every local lane");
});

test("a remote lane's fork parent is prefixed so its branch connector draws", () => {
  assert.match(FED, /if \(out\.branch && typeof out\.branch === "object" && typeof out\.branch\.fromId === "string"\)/);
  assert.match(FED, /out\.branch = \{ \.\.\.out\.branch, fromId: prefixId\(host, out\.branch\.fromId\) \};/);
});

test("bar mids ride the wire — the merged-view dmid join reads them", () => {
  assert.doesNotMatch(KERNEL, /_b\.pop\("mids", None\)/, "the payload-audit pop predated the dmid join and starved it");
  assert.match(KERNEL, /mids STAY on the wire \(2026-08-17\)/);
  assert.match(KERNEL, /_m\.pop\("fromOrig", None\)/, "fromOrig stays binder-only — nothing client-side reads it");
});

// ── 4. a bars detail ahead of the LOCAL lanes ──

const U = "11111111-2222-3333-4444-555555555555";
/** The bare manager over a stand-in window, with `got` every merged frame it hands its subscriber. */
function withManager(fn: (fm: any, got: any[]) => void): void {
  const store = new Map<string, string>();
  const g: any = globalThis;
  const hadWindow = "window" in g, prevWindow = g.window;
  const hadLS = "localStorage" in g, prevLS = g.localStorage;
  g.window = { dispatchEvent: () => {} };
  g.localStorage = { getItem: (k: string) => store.get(k) ?? null, setItem: (k: string, v: string) => { store.set(k, v); } };
  try {
    const fm: any = new FederationManager();
    const got: any[] = [];
    fm.onFrame((e: MessageEvent) => got.push(e.data));
    fn(fm, got);
  } finally {
    if (hadWindow) g.window = prevWindow; else delete g.window;
    if (hadLS) g.localStorage = prevLS; else delete g.localStorage;
  }
}
const lanes = (now: number) => ({ type: "data", data: { now, sessions: [{ id: U, name: "web" }], lanes: [] } });
const bars = (now: number) => ({ type: "bars", now, turns: { [U]: [{ id: "b1", start: now - 60, end: now - 30 }] }, messages: [], judging: {}, warming: false });
const types = (frames: any[]) => frames.map((m) => m && m.type);

test("a bars detail that arrived ahead of the LOCAL lanes lands with them, once", () => {
  withManager((fm, got) => {
    fm.inbound("", bars(1_700_000_000));
    assert.deepEqual(types(got), [], "held: the merge needs the local lanes (the clock authority and the connector stitch)");
    fm.inbound("", lanes(1_700_000_000));
    assert.deepEqual(types(got), ["data", "bars"], "the lanes' arrival emits the lanes and then the held bars");
    assert.deepEqual(Object.keys(got[1].turns), [U]);
    assert.equal(got[1].turns[U][0].id, "b1");
    assert.equal(got[1].now, 1_700_000_000, "the bars keep their own clock sample");
    fm.inbound("", lanes(1_700_000_060));
    assert.deepEqual(types(got), ["data", "bars", "data"], "spent: a later skeleton alone re-emits no bars");
  });
});

test("lanes first: the bars emit on their own arrival, and no skeleton re-emits them", () => {
  withManager((fm, got) => {
    fm.inbound("", lanes(1_700_000_000));
    fm.inbound("", bars(1_700_000_000));
    fm.inbound("", lanes(1_700_000_060));
    fm.inbound("", lanes(1_700_000_120));
    assert.deepEqual(types(got), ["data", "bars", "data", "data"]);
  });
});

test("the lanes' arrival emits the held bars only when it is the LOCAL lanes that were missing", () => {
  withManager((fm, got) => {
    fm.inbound("", bars(1_700_000_000));
    fm.inbound("TESTHOST", lanes(1_700_000_000));
    assert.deepEqual(types(got), [], "a remote's lanes lift neither hold: the merge still needs the local lanes");
    fm.inbound("", lanes(1_700_000_000));
    assert.deepEqual(types(got), ["data", "bars"]);
  });
});

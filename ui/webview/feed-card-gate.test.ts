// The per-card update gate (feed-card-gate.ts), EXECUTED: every board-level input updateAskCard reads
// outside the ask object must flip the key, equal inputs must give equal keys, a quarantine card must
// never skip, and cardNeedsUpdate must fire on a new object OR a new key. A missed input here is a stale
// badge on an unchanged card, so the test walks the inputs one at a time. Synthetic notes-api world.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { cardInputsKey, cardNeedsUpdate, sameKeySeq, type GateEnv, type GateItem } from "./feed-card-gate";

const WEB = "11111111-2222-3333-4444-555555555555";
const API = "11111111-2222-3333-4444-666666666666";
const card = (over: Partial<GateItem> = {}): GateItem => ({
  itemId: "g1", sid: WEB, name: "web", color: { bg: "#3366cc" },
  tree: [
    { kind: "ask", who: "web", whoSid: WEB },
    { kind: "handoff", who: "api", whoSid: API },
  ],
  delegTracked: [{ name: "tests" }],
  ...over,
});
const env = (over: Partial<GateEnv> = {}): GateEnv => ({
  dot: () => "",
  working: () => false,
  userTodos: {},
  focusId: null,
  pinnedId: null,
  notifyOn: () => false,
  prefs: { grouped: true, collapsed: false, colormap: "aurora" },
  hostDown: () => false,
  selfHost: "TESTHOST",
  seq: 1,
  ...over,
});

test("identical inputs give an identical key, across renders and across a fresh env object", () => {
  const it = card();
  assert.equal(cardInputsKey(it, env()), cardInputsKey(it, env()));
  assert.equal(cardInputsKey(it, env({ seq: 7 })), cardInputsKey(it, env({ seq: 9 })),
    "the per-render counter reaches only quarantine cards");
});

test("each board-level input flips the key on its own", () => {
  const it = card();
  const base = cardInputsKey(it, env());
  const flips: Record<string, Partial<GateEnv>> = {
    "the card's own working dot":      { dot: (n) => (n === "web" ? "work" : "") },
    "the card's own awaiting dot":     { dot: (n) => (n === "web" ? "await" : "") },
    "the card's own unknown ring":     { dot: (n) => (n === "web" ? "unknown" : "") },
    "a tracked delegation peer's dot": { dot: (n) => (n === "tests" ? "work" : "") },
    "a handoff recipient working":     { working: (n) => n === "api" },
    "the session's open user todos":   { userTodos: { [WEB]: 2 } },
    "hover focus on this card":        { focusId: "g1" },
    "a pin on this card":              { pinnedId: "g1" },
    "the bell":                        { notifyOn: () => true },
    "grouped mode":                    { prefs: { grouped: false, collapsed: false, colormap: "aurora" } },
    "the collapsed default":           { prefs: { grouped: true, collapsed: true, colormap: "aurora" } },
    "the colormap":                    { prefs: { grouped: true, collapsed: false, colormap: "viridis" } },
    "the session's host going down":   { hostDown: (sid) => sid === WEB },
    "this machine's own name":         { selfHost: "OTHERHOST" },
  };
  const seen = new Set<string>([base]);
  for (const [what, over] of Object.entries(flips)) {
    const k = cardInputsKey(it, env(over));
    assert.notEqual(k, base, what + " must flip the key");
    assert.ok(!seen.has(k), what + " must not collide with another input's key");
    seen.add(k);
  }
});

test("inputs that belong to OTHER sessions leave this card's key alone", () => {
  const it = card();
  const base = cardInputsKey(it, env());
  assert.equal(cardInputsKey(it, env({ dot: (n) => (n === "api" ? "work" : "") })), base,
    "api working: not this card's session, not a tracked peer — the handoff line reads workingSet, tested separately");
  assert.equal(cardInputsKey(it, env({ userTodos: { [API]: 3 } })), base, "another session's todos");
  assert.equal(cardInputsKey(it, env({ focusId: "g2", pinnedId: "g2" })), base, "focus and pin on another card");
  assert.equal(cardInputsKey(it, env({ hostDown: (sid) => sid === API })), base, "another host down");
});

test("the colour echo's in-place write reaches the gate through the key (the object identity cannot carry it)", () => {
  const it = card();
  const before = cardInputsKey(it, env());
  it.color = { bg: "#cc3366" };   // feed.ts applyColorEcho writes the shared ask object in place, by design
  assert.notEqual(cardInputsKey(it, env()), before);
  assert.equal(cardNeedsUpdate({ _it: it, _ik: before }, it, cardInputsKey(it, env())), true,
    "same object, echoed colour: the card repaints");
});

test("a quarantine card never yields an equal key across renders", () => {
  const q = card({ blocked: { state: "quarantine" } });
  assert.notEqual(cardInputsKey(q, env({ seq: 1 })), cardInputsKey(q, env({ seq: 2 })));
  assert.equal(cardInputsKey(q, env({ seq: 3 })), cardInputsKey(q, env({ seq: 3 })),
    "…within one render it is stable (the counter is per render, not per call)");
  const plain = card({ blocked: { state: "permission" } });
  assert.equal(cardInputsKey(plain, env({ seq: 1 })), cardInputsKey(plain, env({ seq: 2 })),
    "an ordinary block reads no per-name colour map: it skips like any card");
});

test("cardNeedsUpdate: false for the same object under the same key; true for a copy, or for a new key", () => {
  const it = card();
  const k = cardInputsKey(it, env());
  assert.equal(cardNeedsUpdate({ _it: it, _ik: k }, it, k), false, "nothing changed: skip");
  assert.equal(cardNeedsUpdate({ _it: it, _ik: k }, { ...it }, k), true, "a new object (the kernel re-sent it): update");
  assert.equal(cardNeedsUpdate({ _it: it, _ik: k }, it, k + "|x"), true, "a board-level input changed: update");
  assert.equal(cardNeedsUpdate({}, it, k), true, "a freshly minted card has neither: update");
});

test("sameKeySeq: the FLIP gate is order-sensitive and length-sensitive", () => {
  assert.equal(sameKeySeq(["a:1", "a:2"], ["a:1", "a:2"]), true);
  assert.equal(sameKeySeq(["a:1", "a:2"], ["a:2", "a:1"]), false, "a sort change is a move");
  assert.equal(sameKeySeq(["a:1", "a:2"], ["a:1"]), false, "a card left");
  assert.equal(sameKeySeq(["a:1"], ["a:1", "a:2"]), false, "a card arrived");
  assert.equal(sameKeySeq([], []), true, "an empty column stays empty");
});

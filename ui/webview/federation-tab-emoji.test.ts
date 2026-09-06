// A federated viewer's tabs come from each remote kernel's own tabOrder frame; the tab emoji (the user
// 2026-09-06) is a plain field beside name and color there, so the id-prefixing pass carries it untouched,
// and the tab menu's setSessionEmoji routes to the owning host by the tab's prefixed id with the emoji
// intact (only the field that decided the route is stripped — the renameSession rule). Executable: both
// functions are pure. Synthetic host and ids.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { prefixInbound, routeOutbound } from "./federation";

const MOON = "\u{1F319}";

test("a remote kernel's tab meta and its emojiSet confirm keep the emoji through the id-prefixing pass", () => {
  const out = prefixInbound("gpu1", { type: "tabOrder", order: ["S1"],
                                     tabs: [{ id: "S1", name: "web", color: { bg: "#336699", fg: "#ffffff" }, emoji: MOON },
                                            { id: "S2", name: "api", color: null, emoji: "" }] });
  assert.equal(out.tabs[0].id, "gpu1:S1");
  assert.equal(out.tabs[0].emoji, MOON);
  assert.deepEqual(out.tabs[0].color, { bg: "#336699", fg: "#ffffff" });
  assert.equal(out.tabs[1].emoji, "", "a cleared emoji stays an explicit empty string");
  const confirm = prefixInbound("gpu1", { type: "emojiSet", id: "S1", emoji: MOON });
  assert.equal(confirm.id, "gpu1:S1");
  assert.equal(confirm.emoji, MOON);
});

test("setSessionEmoji for a remote tab routes to its host with the bare id and the emoji untouched", () => {
  const routes = routeOutbound({ type: "setSessionEmoji", id: "gpu1:S1", emoji: MOON }, new Set(["gpu1"]));
  assert.equal(routes.length, 1);
  assert.equal(routes[0].host, "gpu1");
  assert.deepEqual(routes[0].msg, { type: "setSessionEmoji", id: "S1", emoji: MOON });
});

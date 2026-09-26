// GUARD, passes today (2026-09-22): the tabOrder roster row's userTodos count (the kernel's _tab_meta; tab-meta.ts) reaches
// a federated viewer through the id-prefixing pass untouched, so a remote tab held as a skeleton wears its flag like a
// local one. No federation change was needed for that: `tabs` is an OBJ_ID list (federation.ts), each row spread by
// _prefixIdBearing with only its id and name rewritten, and emitMergedOrder concatenates the per-host rows. This pins
// the shape it relies on: a pass that started copying rows field by field would drop the count, and every unwatched
// remote tab's flag with it. federation-tab-emoji.test.ts's shape. Executable: prefixInbound is pure. Synthetic host and ids.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { prefixInbound } from "./federation";

test("GUARD (passes today): a remote kernel's tabOrder rows keep userTodos through the id-prefixing pass, 0 and an absent key included", () => {
  const out = prefixInbound("gpu1", { type: "tabOrder", order: ["S1", "S2", "S3"],
                                     tabs: [{ id: "S1", name: "web", color: { bg: "#336699", fg: "#ffffff" }, emoji: "", userTodos: 2 },
                                            { id: "S2", name: "api", color: null, userTodos: 0 },
                                            { id: "S3", name: "tests", color: null }] });
  assert.equal(out.tabs[0].id, "gpu1:S1");
  assert.equal(out.tabs[0].name, "gpu1:web", "the id and the display name are the rewritten fields");
  assert.equal(out.tabs[0].userTodos, 2, "the count rides beside name, colour and emoji");
  assert.deepEqual(out.tabs[0].color, { bg: "#336699", fg: "#ffffff" });
  assert.equal(out.tabs[1].userTodos, 0, "an empty count is a real value and stays one");
  assert.equal("userTodos" in out.tabs[2], false, "an older kernel's row has no key and gains none");
});

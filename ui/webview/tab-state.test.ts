// tab-state.ts: the tab strip's ONE state → class rule, worn by the tab (render.ts renderTabs). The
// folded section header once summarized its members with a pip by this rule; the header reads as a
// label now (the user 2026-09-06) and carries none — tab-groups.test.ts pins that. Executed on the pure
// module. Synthetic statuses only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { tabStateClass } from "./tab-state";

test("executed: tabStateClass — the strip's rule, on-you blocks red, transient API errors amber", () => {
  assert.equal(tabStateClass({ state: "working" }), "tab-working");
  assert.equal(tabStateClass({ state: "blocked" }), "tab-retrying", "a transient API error auto-retries: amber, not red");
  assert.equal(tabStateClass({ state: "blocked", apiTooLong: true }), "tab-blocked");
  assert.equal(tabStateClass({ state: "blocked", apiSpendLimit: true }), "tab-blocked");
  assert.equal(tabStateClass({ state: "blocked", apiModelLimit: true }), "tab-blocked");
  assert.equal(tabStateClass({ state: "blocked", apiAuthErr: true }), "tab-blocked");
  assert.equal(tabStateClass({ state: "blocked", apiRefusal: true }), "tab-blocked");
  assert.equal(tabStateClass({ state: "needsInput" }), "tab-awaiting");
  assert.equal(tabStateClass({ state: "awaiting" }), "tab-awaiting", "the legacy name an older remote kernel sends");
  assert.equal(tabStateClass({ state: "retrying" }), "tab-retrying");
  assert.equal(tabStateClass({ state: "compacting" }), "tab-compacting");
  assert.equal(tabStateClass({ state: "clearing" }), "tab-compacting");
  assert.equal(tabStateClass({ state: "closed" }), "tab-closed");
  assert.equal(tabStateClass({ state: "ready" }), "", "no tab treatment → no class");
  assert.equal(tabStateClass(undefined), "");
});

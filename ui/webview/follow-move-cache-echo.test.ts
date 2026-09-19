// The optimistic follow-up move must never WRITE into the payload it renders (the user 2026-08-02, who
// replied to a blocked card and watched it bounce working → blocked → working). On the federated page the
// ask objects in a `feed` payload ARE the FederationManager's cached per-host frames: mergeHostFeeds
// concatenates the cached arrays element-by-reference, and the merged frame reaches the pane by direct call
// from federation's emit (a same-realm window dispatch only when no handler is registered), so no structured
// clone severs the references. So applyFollowMove's old in-place
// `a.column = "working"` edited the manager's cache; the next merged re-emit — fired by ANY host's frame,
// seconds later — served the pane its own edit back as kernel truth, reconcileFollowMove read it as the
// kernel confirming the move ("confirmed") and dropped the prediction, and the next local build already in
// flight when the reply landed (honestly pre-reply) bounced the card back to Blocked with nothing left to
// hold it. Recorded end to end in client-diag.jsonl: predict:followup → payload flip back with
// predicted:false three seconds later → payload flip forward nine seconds after that.
//
// feed.ts has import-time DOM side effects, so per the established precedent this is source pins plus the
// decision EXECUTED: since the lazy-panes change (review round 3, 2026-09-19) the prediction is a pure transform,
// predictFollowMoves, which applyFollowMove applies to the list in place (paintedKeyOf plans over the same
// transform), and the executed case below runs those two functions lifted from feed.ts's own text under esbuild
// (the feed-hidden-paint.test.ts liftedPlan precedent) rather than the hand-written replica the test carried
// before: a copy of the code under test is not a witness of it.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";

const requireCjs = createRequire(__filename);
const F = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "feed.ts"), "utf8");
const FED = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "federation.ts"), "utf8");

// the whole body of each, so the pins below can't be satisfied by unrelated code
const fnBody = (name: string) => {
  const m = F.match(new RegExp("function " + name + "\\([^)]*\\)[^{]*\\{[\\s\\S]*?\\n\\}"));
  assert.ok(m, name + " not found in feed.ts");
  return m![0];
};
const predictBody = fnBody("predictFollowMoves");
const applyBody = fnBody("applyFollowMove");

test("predictFollowMoves copies a predicted card and applyFollowMove puts the copy in the slot: neither mutates the payload object", () => {
  // the copy idiom, in the transform: spread into a fresh AskItem, column set on the copy, the copy returned for the slot
  assert.match(predictBody, /const c: AskItem = \{ \.\.\.a, column: "working" \};/);
  assert.match(predictBody, /return c;/);
  // the application replaces the slot with the transform's element
  assert.match(applyBody, /list\[i\] = out\[i\];/);
  // and no write lands on the shared object itself in either (assignment, not the `===` comparison in the guards)
  assert.doesNotMatch(predictBody, /\ba\.(column|recheck|followupPending|t)\s*=[^=]/);
  assert.doesNotMatch(applyBody, /\.(column|recheck|followupPending|t)\s*=[^=]/);
});

test("the shared-reference premise holds: the merge reuses cached frame elements, delivered same-realm", () => {
  // mergeHostFeeds concatenates the cached asks arrays by reference (no per-element copy)…
  assert.match(FED, /if \(Array\.isArray\(f\.asks\)\) merged\.asks\.push\(\.\.\.f\.asks\);/);
  // …and the merged frame is handed to the pane by direct call (emit: the registered handler, else a same-realm
  // window dispatch), so no structured clone severs the references
  assert.match(FED, /this\.emit\(mergeHostFeeds\(/);
});

// Executed on feed.ts's OWN lines: predictFollowMoves and applyFollowMove, lifted from the source above and run under
// esbuild with the module's three Maps stood in (pendingFollowMove, pendingMoveKind, predictedFrom). The exact scenario
// off the diagnosed trail: a cached host frame holds the blocked card; the merge serves its elements by reference; the
// pane predicts and renders. The cache must still read needs_input afterwards; else the next re-emit "confirms" the
// prediction the pane itself painted.
function lifted() {
  const js = requireCjs("esbuild").transformSync(predictBody + "\n" + applyBody, { loader: "ts" }).code;
  const prelude = "const pendingFollowMove = new Map(), pendingMoveKind = new Map(), predictedFrom = new Map();\n";
  return new Function(prelude + js + "\nreturn { apply: (list) => applyFollowMove(list), pending: (id, kind) => { pendingFollowMove.set(id, true); pendingMoveKind.set(id, kind); }, predictedFrom };")() as
    { apply(list: any[]): void; pending(id: string, kind: "followup" | "answer"): void; predictedFrom: Map<string, any> };
}
test("rendering a predicted card leaves the cached frame untouched, so a re-emit cannot false-confirm", () => {
  const L = lifted();
  L.pending("s1:g1", "followup");                          // the user replied to the card: optimisticFollowMove's registration
  const apply = (list: any[]) => L.apply(list);           // render()'s applyFollowMove(asks), feed.ts's own lines
  const nowSec = Math.floor(Date.now() / 1000);           // the transform's clock: the copy's sort key is bumped to now
  const cached: any[] = [{ itemId: "s1:g1", column: "needs_input", t: 900 }];   // the manager's stored local frame
  const merged: any[] = [...cached];                      // mergeHostFeeds: fresh array, shared elements
  apply(merged);
  // the render shows the prediction…
  assert.equal(merged[0].column, "working");
  assert.equal(merged[0].recheck, true);
  assert.ok(merged[0].t >= nowSec, "the copy's sort key is bumped to now: " + merged[0].t);
  assert.equal(L.predictedFrom.get("s1:g1"), cached[0], "what a refusal puts back is the cached object itself, unwritten");
  // …while the cache still holds exactly what the kernel sent, so the next merged re-emit still shows the
  // card blocked and reconcileFollowMove keeps waiting for the kernel's real answer
  assert.equal(cached[0].column, "needs_input");
  assert.equal(cached[0].t, 900);
  assert.equal("recheck" in cached[0], false);
  // and a second render pass over a re-merge of the same cache predicts again without double-copying
  const remerged = [...cached];
  apply(remerged);
  assert.equal(remerged[0].column, "working");
  assert.equal(cached[0].column, "needs_input");
});

// The margin block's rationale comment in styles.css records whose design the layout is. The repo's
// `(the user <date>: ...)` convention marks a paraphrased user ruling — the WHY a maintainer reads before changing a
// rule — and the block's comment as first written put the build's design inside it: the user, after walking the loop,
// wanting each card level with its passage. The plan's margin-layout note (plans/file-review.md, Slice 2) records the
// ask differently — comments moving with the window when possible, each trying to stay centered near its place in the
// text — and files "level with its passage rather than centered on it" under the build's reading, awaiting the user's
// word (tools/file-review-plan-attribution.test.mjs holds the plan to that). The first round's correction reached the
// plan only; the sheets still said the user had asked for what was built (the 2026-09-07 review, round 2). This module
// holds the comment to the same record: the layout is the build's reading, the ask carries its hedges and none of the
// design, and the plan's note is where the two are set out. feed.css carries the block byte-equal
// (tests/test_guide_files_margin_layout.py, the sheets agree), so this pin reaches it too. Synthetic: only the repo's own
// text; the user is paraphrased, never quoted.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const UI = path.resolve(process.cwd(), "..", "ui", "webview");     // npm test runs in vscode-extension
const STYLES = fs.readFileSync(path.join(UI, "styles.css"), "utf8");

/** The comment that introduces the margin layout: the one ending right before the `.fc-panel.fc-margin` rule, wraps collapsed. */
function marginComment(): string {
  const at = STYLES.indexOf("\n.fc-panel.fc-margin {");
  assert.ok(at > 0, "the margin layout's root rule");
  const before = STYLES.slice(0, at);
  const open = before.lastIndexOf("/*");
  assert.ok(open > 0 && before.slice(open).includes("*/"), "a comment closes right before the rule");
  return before.slice(open).replace(/\s+/g, " ");
}
const comment = marginComment();
// the attribution clause: the parenthetical that opens the comment
const clause = /^\/\* the margin layout \(([^)]*)\)/.exec(comment);

test("the margin layout's comment opens by naming the layout as the build's reading of the ask, not the user's ruling", () => {
  assert.ok(clause, "the comment opens with the attribution clause: " + comment.slice(0, 120));
  assert.match(clause![1], /^the build's reading, not a ruling, of the user's 2026-09-07 ask/);
});

test("the ask in the clause carries its hedges and the centering the build did not do", () => {
  const ask = clause![1];
  assert.match(ask, /move with the window when possible/, "a wish with its hedge, not a requirement");
  assert.match(ask, /trying to stay centered near its place in the text/, "centering near the passage, which the build did not do");
});

test("the clause says where the build departed from the ask, and where the plan records both", () => {
  const c = clause![1];
  assert.match(c, /the build put each card level with its passage instead/);
  assert.match(c, /plan's margin-layout note under Slice 2 records both/);
});

test("the comment nowhere attributes level-with placement to the user", () => {
  // the first wording: a dated user attribution whose content was the build's layout
  assert.doesNotMatch(comment, /\(the user 2026-09-07/, "no dated user ruling opens the comment");
  assert.doesNotMatch(comment, /the user[^.;)]*should sit level with/, "the user is not said to have required level-with placement");
  assert.doesNotMatch(comment, /after walking the loop: a/, "the old clause's shape is gone");
});

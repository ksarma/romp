// The panel's margin-layout section comment records whose design the layout is. The repo's `(the user <date>: ...)`
// convention marks a paraphrased user ruling — the WHY a maintainer reads before changing placeCards — and the section's
// comment as first written put the build's design inside it: the user, after walking the loop, wanting each card level
// with its passage. The plan's margin-layout note (plans/file-review.md, Slice 2) records the ask differently — comments
// moving with the window when possible, each trying to stay centered near its place in the text — and files "level with
// its passage rather than centered on it" under the build's reading, awaiting the user's word
// (tools/file-review-plan-attribution.test.mjs holds the plan to that; styles-fc-margin-attribution.test.ts the sheets).
// The first two rounds' corrections reached the plan and the sheets; the panel source, the file the plan names as the
// layout's home, still said the user had asked for what was built (the 2026-09-07 review, round 3). This module holds the
// comment to the same record: the layout is the build's reading, the ask carries its hedges and none of the design, and
// the plan's note is where the two are set out. Synthetic: only the repo's own text; the user is paraphrased, never quoted.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const UI = path.resolve(process.cwd(), "..", "ui", "webview");     // npm test runs in vscode-extension
const PANEL = fs.readFileSync(path.join(UI, "file-comments.ts"), "utf8");

/** The Panel's margin-layout section comment: the `// ── the margin layout (` lines down to the `margin = false;` field
 *  they introduce, the comment markers and wraps collapsed to one line. */
function marginComment(): string {
  const at = PANEL.indexOf("\n  // ── the margin layout (");
  assert.ok(at > 0, "the section comment that introduces the margin layout's fields");
  const end = PANEL.indexOf("\n  margin = false;", at);
  assert.ok(end > at, "the `margin` field the comment introduces");
  const lines = PANEL.slice(at + 1, end).split("\n");
  assert.ok(lines.every((l) => l.startsWith("  // ")), "one comment, every line of it: " + lines.find((l) => !l.startsWith("  // ")));
  return lines.map((l) => l.slice(5)).join(" ").replace(/\s+/g, " ");
}
const comment = marginComment();
// the attribution clause: the parenthetical that opens the comment
const clause = /^── the margin layout \(([^)]*)\)/.exec(comment);

test("the panel's margin-layout comment opens by naming the layout as the build's reading of the ask, not the user's ruling", () => {
  assert.ok(clause, "the comment opens with the attribution clause: " + comment.slice(0, 120));
  assert.match(clause![1], /^the build's reading, not a ruling, of the user's 2026-09-07 ask/);
});

test("the ask in the clause carries its hedges and the centering the build did not do", () => {
  const ask = clause![1];
  assert.match(ask, /move with the window when possible/, "a wish with its hedge, not a requirement");
  assert.match(ask, /trying to stay centered near its place in the text/, "centering near the passage, which the build did not do");
});

test("the clause says where the build departed from the ask, where the plan records both, and that the user's word is still to come", () => {
  const c = clause![1];
  assert.match(c, /the build put each card level with its passage instead/);
  assert.match(c, /plan's margin-layout note under Slice 2 records both/);
  assert.match(c, /the user's word still to come/);
});

test("the comment nowhere attributes level-with placement to the user", () => {
  // the first wording: a dated user attribution whose content was the build's layout
  assert.doesNotMatch(comment, /\(the user 2026-09-07/, "no dated user ruling opens the comment");
  assert.doesNotMatch(comment, /the user[^.;)]*should sit level with/, "the user is not said to have required level-with placement");
  assert.doesNotMatch(comment, /after walking the loop: a/, "the old clause's shape is gone");
});

test("the panel source carries the old clause nowhere else", () => {
  assert.doesNotMatch(PANEL, /\(the user 2026-09-07/, "no dated user ruling for the layout anywhere in the panel");
  assert.doesNotMatch(PANEL, /after walking the loop: a/);
});

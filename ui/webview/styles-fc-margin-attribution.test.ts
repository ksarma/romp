// The margin block's rationale comment records whose design the layout is, and it does so in BOTH sheets. The repo's
// `(the user <date>: ...)` convention marks a paraphrased user ruling — the WHY a maintainer reads before changing a
// rule — and the block's comment as first written put the build's design inside it: the user, after walking the loop,
// wanting each card level with its passage. The plan's margin-layout note (plans/file-review.md, Slice 2) records the
// ask differently — comments moving with the window when possible, each trying to stay centered near its place in the
// text — and files "level with its passage rather than centered on it" under the build's reading, awaiting the user's
// word (tools/file-review-plan-attribution.test.mjs holds the plan to that). The first round's correction reached the
// plan only; the sheets still said the user had asked for what was built (the 2026-09-07 review, round 2). Round 2
// corrected styles.css and pinned it here, reading styles.css alone on the strength of the sheets' byte-equal pin
// (tests/test_guide_files_margin_layout.py, the sheets agree) — but that pin was red, round 2 had not touched feed.css,
// and feed.css still opened the block with the dated user ruling while every attribution test passed (round 3).
// feed.css is the only sheet the feed page loads, and the viewer with its panel mounts there, so a pin on one sheet
// leaves the feed page's copy unread. This module reads each sheet itself and holds each comment to the same record:
// the layout is the build's reading, the ask carries its hedges and none of the design, and the plan's note is where
// the two are set out. The last test holds the two comments equal, so a correction to one sheet cannot again miss the
// other without a red here. Synthetic: only the repo's own text; the user is paraphrased, never quoted.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const UI = path.resolve(process.cwd(), "..", "ui", "webview");     // npm test runs in vscode-extension
/** Both sheets that carry the file-comments block: the chat page loads styles.css, the feed page feed.css alone. */
const SHEETS = ["styles.css", "feed.css"].map((name) => [name, fs.readFileSync(path.join(UI, name), "utf8")] as const);

/** The comment that introduces the margin layout in `css`: the one ending right before the `.fc-panel.fc-margin` rule, wraps collapsed. */
function marginComment(css: string, where: string): string {
  const at = css.indexOf("\n.fc-panel.fc-margin {");
  assert.ok(at > 0, where + ": the margin layout's root rule");
  const before = css.slice(0, at);
  const open = before.lastIndexOf("/*");
  assert.ok(open > 0 && before.slice(open).includes("*/"), where + ": a comment closes right before the rule");
  return before.slice(open).replace(/\s+/g, " ");
}
/** The attribution clause: the parenthetical that opens the comment. */
function attribution(css: string, where: string): string {
  const comment = marginComment(css, where);
  const clause = /^\/\* the margin layout \(([^)]*)\)/.exec(comment);
  assert.ok(clause, where + ": the comment opens with the attribution clause: " + comment.slice(0, 120));
  return clause![1];
}

for (const [name, css] of SHEETS) {
  test(name + ": the margin layout's comment opens by naming the layout as the build's reading of the ask, not the user's ruling", () => {
    assert.match(attribution(css, name), /^the build's reading, not a ruling, of the user's 2026-09-07 ask/);
  });

  test(name + ": the ask in the clause carries its hedges and the centering the build did not do", () => {
    const ask = attribution(css, name);
    assert.match(ask, /move with the window when possible/, "a wish with its hedge, not a requirement");
    assert.match(ask, /trying to stay centered near its place in the text/, "centering near the passage, which the build did not do");
  });

  test(name + ": the clause says where the build departed from the ask, and where the plan records both", () => {
    const c = attribution(css, name);
    assert.match(c, /the build put each card level with its passage instead/);
    assert.match(c, /plan's margin-layout note under Slice 2 records both/);
  });

  test(name + ": the comment nowhere attributes level-with placement to the user", () => {
    const comment = marginComment(css, name);
    // the first wording: a dated user attribution whose content was the build's layout
    assert.doesNotMatch(comment, /\(the user 2026-09-07/, "no dated user ruling opens the comment");
    assert.doesNotMatch(comment, /the user[^.;)]*should sit level with/, "the user is not said to have required level-with placement");
    assert.doesNotMatch(comment, /after walking the loop: a/, "the old clause's shape is gone");
  });
}

test("the two sheets carry the same margin comment, so a correction to one cannot again miss the other", () => {
  const [chat, feed] = SHEETS.map(([name, css]) => marginComment(css, name));
  assert.equal(feed, chat, "feed.css's margin comment is styles.css's");
});

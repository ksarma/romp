// The filter suites' titles and assertion messages name what broke in the plan's literal terms. The slice first titled
// its sheet pin "the note's dress for the word" and the review suite described the saved line as "the note's dress on a
// row"; the plan's review replaced that figure (tools/file-review-plan-kind-cue.test.mjs holds the plan to the change,
// feed-css-kind-cue.test.ts the sheets' comment) because it names no rule, and "note" is a word CONTEXT.md lists under
// Avoid for a file comment — the panel's `note` (file-comments.ts, the mutate args) IS the saved body — so a reporter line
// reading "the note's dress" says the comment's own text, not the .fc-note rule. node --test prints a failing test as
// `not ok N - <title>` and a failing assertion by its message, so the two are exactly what a reader of a red run sees, and
// the suites' own text had kept the figure after the plan and the sheets dropped it. This module holds the three filter
// suites to the plan's terms: the rule by its selector (.fc-note), the token by name (--text-muted), no possessive "note"
// and no "muted tone". Synthetic: only the repo's own text.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const SUITES = ["file-comments-filter.test.ts", "file-comments-filter-review.test.ts", "file-comments-filter-fixes.test.ts"];
const read = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");

for (const f of SUITES) {
  test(f + ": no \"the note's …\" and no \"muted tone\" in its titles, messages or comments — the figures the plan's review replaced", () => {
    const src = read(f);
    assert.doesNotMatch(src, /\bnote's\b/, f + ": \"the note's …\" reads as the file comment's own text; name the rule (.fc-note) or the thing");
    assert.doesNotMatch(src, /muted tone/, f + ": \"the muted tone\" names no token; say --text-muted");
  });
}

test("the sheet pin's title names the rule the word copies and the edge's token, as the sheets' comment does", () => {
  const src = read("file-comments-filter.test.ts");
  assert.match(src, /^test\("pins: the sheets carry the cue's rules — \.fc-kind styled like \.fc-note \(--dim, 0\.86em\), a 3px left border in the accent for a comment and in --text-muted for a change,/m,
    "the title says .fc-kind is styled like .fc-note (--dim, 0.86em) and the change edge is --text-muted");
});

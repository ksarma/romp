// The filter suites' titles, assertion messages and comments name what broke in the plan's literal terms. The slice first
// titled its sheet pin "the note's dress for the word" and the review suite described the saved line as "the note's dress
// on a row"; the plan's review replaced that figure (tools/file-review-plan-kind-cue.test.mjs holds the plan to the change,
// feed-css-kind-cue.test.ts the sheets' comment) because it names no rule, and "note" is a word CONTEXT.md lists under
// Avoid for a file comment — the panel's `note` (file-comments.ts, the mutate args) IS the saved body — so a reporter line
// reading "the note's dress" says the comment's own text, not the .fc-note rule. node --test prints a failing test as
// `not ok N - <title>` and a failing assertion by its message, so the two are exactly what a reader of a red run sees, and
// the suites' own text had kept the figure after the plan and the sheets dropped it. This module holds the follow-on's
// suites to the plan's terms: the rule by its selector (.fc-note), the token by name (--text-muted), the focus move by
// where the focus goes (the plan's pin bans "hands the keyboard" in the note; the suites follow it) — no possessive "note",
// no "muted tone", no handed keyboard. The scan covers the four driven suites and the two size probes the follow-on
// touched (styles-fc-computed-sizes.test.ts gained the .fc-kind probe, file-comments-saved-line-sizes.test.ts the saved
// row's); it skips a line that BANS one of the figures (assert.doesNotMatch), since that line must name what it bans.
// feed-css-kind-cue.test.ts and this module quote the figures on purpose, to ban them, and are not scanned. Synthetic:
// only the repo's own text.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const SUITES = [
  "file-comments-filter.test.ts", "file-comments-filter-review.test.ts", "file-comments-filter-fixes.test.ts",
  "file-comments-filter-saved-line.test.ts",                                    // the third round's driven suite
  "file-comments-saved-line-sizes.test.ts", "styles-fc-computed-sizes.test.ts",  // the two size probes the follow-on touched
];
const read = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
// the text the scan reads: every line but one that bans a figure by naming it
const scanned = (f: string): string => read(f).split("\n").filter((l) => !/assert\.doesNotMatch\(/.test(l)).join("\n");

for (const f of SUITES) {
  test(f + ": no \"the note's …\", no \"muted tone\" and no \"hands the keyboard\" in its titles, messages or comments — the figures the plan's review replaced", () => {
    const src = scanned(f);
    assert.doesNotMatch(src, /(?<!fc-)\bnote's\b/, f + ": \"the note's …\" reads as the file comment's own text; name the rule (.fc-note's size, .fc-note's color) or the thing");

    assert.doesNotMatch(src, /muted tone/, f + ": \"the muted tone\" names no token; say --text-muted");
    assert.doesNotMatch(src, /hands the keyboard/, f + ": \"hands the keyboard\" names no element; say where the focus moves (the plan's note does)");
  });
}

test("every suite named file-comments-filter… under ui/webview is scanned, so the next round's suite is held to the terms too", () => {
  const dir = path.resolve(process.cwd(), "..", "ui", "webview");
  const inTree = fs.readdirSync(dir).filter((f) => /^file-comments-filter.*\.test\.ts$/.test(f) && f !== "file-comments-filter-wording.test.ts").sort();
  assert.deepEqual(inTree.filter((f) => !SUITES.includes(f)), [], "a filter suite in the tree is missing from SUITES above");
});

test("the sheet pin's title names the rule the word copies and the edge's token, as the sheets' comment does", () => {
  const src = read("file-comments-filter.test.ts");
  assert.match(src, /^test\("pins: the sheets carry the cue's rules — \.fc-kind styled like \.fc-note \(--dim, 0\.86em\), a 3px left border in the accent for a comment and in --text-muted for a change,/m,
    "the title says .fc-kind is styled like .fc-note (--dim, 0.86em) and the change edge is --text-muted");
});

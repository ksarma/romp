// The shared path matcher names the user todo's text field with the plan's word (plans/file-review.md,
// Slice 0; the round-3 review, 2026-09-06). The plan calls that field `detail` at every mention and uses
// `note` for the text a person types into a file comment (`comment {anchor?, note}`; the CLI's --note),
// and CONTEXT.md lists "note" under File comment's Avoid — so a module that marks paths in both a todo's
// detail and, later, a comment's text cannot call the detail "a todo's note" without splitting the
// vocabulary the two slices share. The idiom was inherited from render.ts and the old test header, and
// the slice moved one such comment and wrote two more before the sweep to "detail"; this pins the
// module's comments to the pinned word so the split cannot reopen here.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const SRC = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "path-links.ts"), "utf8");

test("path-links.ts calls the user todo's text field its detail", () => {
  assert.match(SRC, /\btodo's detail\b/, "the field the pane links is named as the plan names it");
});

test("path-links.ts never calls a todo's detail a note", () => {
  // The two shapes the module used before the sweep: "a todo's note", "one session's note".
  assert.doesNotMatch(SRC, /\b(?:todo|todos|todo's|todos')\s+note\b/i, "plans/file-review.md: the todo field is `detail`");
  assert.doesNotMatch(SRC, /\bsession's\s+note\b/i, "a session writes a todo's detail, not a note");
});

test("in path-links.ts a note is only ever a file comment's text", () => {
  // The plan's `note` is what a person types into a file comment. A line here that says "note" must say
  // whose it is, so a reader of the shared module cannot take it for the todo's detail.
  const strays = SRC.split("\n").filter((l) => /\bnotes?\b/i.test(l) && !/\bcomment/i.test(l));
  assert.deepEqual(strays, [], "every line naming a note names the comment it belongs to");
});

// The Files pane's one definition of `todoId` — the openHere doc in files.ts — names the user todo a file
// was opened from with CONTEXT.md's word (plans/file-review.md Slice 0; the round-3 review, 2026-09-06).
// CONTEXT.md's "User todo" entry lists "ask" under Avoid because the feed payload's `asks` field already
// means the card list. The relay's two ends each document the same parameter: file-view.ts's
// FileViewActionCtx doc (pinned by file-view-vocab.test.ts) and this one, and the round-2 fix that
// corrected the viewer's end left this end saying "a re-open is no longer that ask". This pins the pane's
// end too, so the two cannot describe one parameter with different nouns.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const SRC = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "files.ts"), "utf8");

/** The JSDoc block directly above `function openHere(`: from its `/**` opener to the line the function starts on. */
function openHereDoc(): string {
  const lines = SRC.split("\n");
  const at = lines.findIndex((l) => l.startsWith("function openHere("));
  assert.ok(at > 0, "openHere is declared");
  assert.ok(lines[at - 1].trimEnd().endsWith("*/"), "a doc comment closes directly above openHere");
  let start = at - 1;
  while (start > 0 && !lines[start].trimStart().startsWith("/**")) start--;
  assert.ok(lines[start].trimStart().startsWith("/**"), "the doc comment above openHere has an opener");
  return lines.slice(start, at).join("\n");
}

test("openHere's doc defines todoId as a user todo and never calls it an ask", () => {
  const doc = openHereDoc();
  assert.match(doc, /`todoId`/, "the doc above openHere defines `todoId`");
  assert.match(doc, /\buser todo\b/, "todoId is defined as the user todo the file was opened from");
  assert.doesNotMatch(doc, /\bask\b/i, "CONTEXT.md (User todo, Avoid): `asks` already means the feed's card list");
});

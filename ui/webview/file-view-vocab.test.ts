// The viewer's action-registry doc names the user todo a file was opened from with CONTEXT.md's word
// (plans/file-review.md Slice 0; the round-1 review, 2026-09-06). CONTEXT.md's "User todo" entry lists
// "ask" under Avoid because the feed payload's `asks` field already means the card list — and file-view.ts
// uses "ask" for a request to the kernel two lines above this very comment (the GitHub link's kernel
// ask), so "tie its work back to the ask" gave `todoId` a referent a reader could take for a card or a
// kernel round-trip. The slice's fix commit corrected the kernel's relay comment and left this one;
// this pins the definition of `todoId` to the pinned vocabulary so the two cannot drift apart again.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const VIEW = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "file-view.ts"), "utf8");

/** The `todoId` doc comment: the contiguous `// \`todoId\`:` lines directly above FileViewActionCtx. */
function todoIdDoc(): string {
  const lines = VIEW.split("\n");
  const at = lines.findIndex((l) => l.startsWith("export interface FileViewActionCtx"));
  assert.ok(at > 0, "FileViewActionCtx is declared");
  let start = at;
  while (start > 0 && lines[start - 1].startsWith("//")) start--;
  const doc = lines.slice(start, at);
  const from = doc.findIndex((l) => l.startsWith("// `todoId`:"));
  assert.ok(from >= 0, "the doc comment above FileViewActionCtx defines `todoId`");
  return doc.slice(from).join("\n");
}

test("FileViewActionCtx's todoId doc calls its referent a user todo, never an ask", () => {
  const doc = todoIdDoc();
  assert.match(doc, /\buser todo\b/, "todoId is defined as the user todo the file was opened from");
  assert.doesNotMatch(doc, /\bask\b/i, "CONTEXT.md (User todo, Avoid): `asks` already means the feed's card list");
});

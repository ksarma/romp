// user-todo-links.test.ts's assertion messages name the user todo a file was opened from with CONTEXT.md's
// word (plans/file-review.md Slice 0; the round-2 review, 2026-09-06). A failing assertion prints its
// message as the run's only prose, and that file's messages describe the same referent files.ts's
// `todoId` does — so they hold to the same vocabulary file-view-vocab.test.ts pins for file-view.ts.
// CONTEXT.md's "User todo" entry lists "ask" under Avoid because the feed payload's `asks` field already
// means the card list, and ui/webview uses "the ask" for a feed card throughout: a message saying the
// recent list "does not remember the ask" told the reader a card was involved when the subject was the
// todo. That message was the one leftover after the slice's own sweep; this pins the whole file so a
// new message cannot reintroduce the word. The pin is a sibling file rather than a test inside
// user-todo-links.test.ts because a self-scan would have to name the banned word in its own prose.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const LINKS_TEST = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "user-todo-links.test.ts"), "utf8");

test("user-todo-links.test.ts calls the user todo a todo, never an ask", () => {
  assert.match(LINKS_TEST, /\btodo\b/, "the file speaks of the user todo at all");
  assert.doesNotMatch(LINKS_TEST, /\bask\b/i, "CONTEXT.md (User todo, Avoid): `asks` already means the feed's card list");
});

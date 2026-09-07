// The Undo click's failure path (2026-09-07): the kernel stands down, with nothing written, when a restored
// session's goal store or archive cannot be read, and answers undoClearResult; the pane puts its optimistic
// restore back the way it was, ends the working cue and says why (fail loudly). Success stays silent: the
// next feed payload carries the restored cards. Source pin, like feed-warn-chip.test.ts.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const FEED = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "feed.ts"), "utf8");

test("the Undo click keeps the batch it restored optimistically, so a refusal can put it back", () => {
  assert.match(FEED, /let lastUndoBatch: AskItem\[\] \| null = null;/);
  assert.match(FEED, /lastUndoBatch = batch && batch\.length \? batch : null;/);
});

test("a refused Undo is reverted, its cue ended, and the reason said out loud", () => {
  const i = FEED.indexOf('m.type === "undoClearResult"');
  assert.ok(i > 0, "the feed handles undoClearResult");
  const block = FEED.slice(i, i + 1400);
  assert.match(block, /if \(!m\.ok\) \{/);
  assert.match(block, /clearUndoBusy\(\);/);
  assert.match(block, /pendingRestored\.delete\(it\.itemId\);/);
  assert.match(block, /pendingCleared\.add\(it\.itemId\);/);
  assert.match(block, /asks\.splice\(i, 1\);/);
  assert.match(block, /clearedStack\.push\(lastUndoBatch\);/);
  assert.match(block, /feedToast\("couldn't undo the clear: " \+ \(String\(m\.error \|\| ""\) \|\| "the kernel refused it"\)\);/);
});

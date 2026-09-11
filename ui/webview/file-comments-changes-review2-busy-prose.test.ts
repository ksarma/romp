// The changes suite's own explanation of the `busy` case (file-comments-changes-review2.test.ts, "Accept refused busy")
// held to the premise the source states at MOVED: the host refuses `busy` while the other writer STILL holds the lock,
// `status` takes no lock, so the one re-read shows that writer's write only when it landed in the gap before the re-read,
// and only then does the retry carry a fence that lands. file-comments-busy-retry-fence.test.ts pins that premise in
// the panel's source and bans the retracted sentence there (the holder's write "on disk by the time" `busy` arrives, the
// same re-read showing it and the retry landing after it); its scan reads file-comments.ts alone, and the slice review
// (2026-09-11) found the retracted sentence standing in the suite's comment. This file scans the suite the same way, so
// the explanation beside the test cannot drift back to a guarantee the lock does not give. It reads the test's SOURCE
// (the bundled copy strips comments), and it is a separate file because a suite scanning itself would match its own
// ban's literal. Synthetic fixtures only: the suite's notes-api world.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const repoFile = (...parts: string[]) => fs.readFileSync(path.resolve(process.cwd(), "..", ...parts), "utf8");
/** Comment prose as one line (the fence test's helper): continuation markers and line breaks folded to single spaces. */
const flat = (s: string): string => s.replace(/\n\s*(?:\/\/|\* ?)/g, " ").replace(/\s+/g, " ");
/** The suite's `busy` test: from its `test("Accept refused busy` line to the next top-level `test(` or section rule. */
function busyCase(src: string): string {
  const start = src.indexOf('\ntest("Accept refused busy');
  assert.ok(start >= 0, "the suite has the Accept refused busy case (plans/file-review.md names it)");
  const rest = src.slice(start + 1);
  const end = rest.search(/\n(?:test\(|\/\/ ── )/);
  return end < 0 ? rest : rest.slice(0, end);
}

test("the changes suite's busy case explains itself as the fence test pins the source: busy arrives while the lock is still held, the re-read shows the holder's write only when it landed in the gap, and the retry is the moved-fence path", () => {
  const prose = flat(busyCase(repoFile("ui", "webview", "file-comments-changes-review2.test.ts")));
  assert.ok(prose.includes("the retry is the moved-fence path reused, not a wait for the holder"), "the retry is not a wait for the holder");
  assert.ok(prose.includes("the host refuses `busy` while the other writer STILL holds the lock (it releases after its last rename; `status` takes no lock)"), "the premise: the lock is still held at the refusal, and the re-read cannot wait for it");
  assert.ok(prose.includes("the one re-read shows that writer's write only when it landed in the gap before the re-read, and only then does the retry carry a fence that lands"), "the one case the retry lands");
  assert.ok(prose.includes("The harness answers the re-read with S9: that case."), "and the comment says the fixture models that case, not that every busy does");
  assert.ok(prose.includes("`busy` again from a lock still held or `store-moved` from a holder that finished under the retry, shows verbatim with Reload, and there is no third try"), "the two second refusals, as the fence test has them");
});

test("nowhere does the changes suite claim the holder's write is on disk when busy arrives (the fence test's ban, over the suite it does not read)", () => {
  const prose = flat(repoFile("ui", "webview", "file-comments-changes-review2.test.ts"));
  assert.doesNotMatch(prose, /on disk by (?:the time|now)|re-read shows what it wrote|the retry lands after it\b|one retry lands after it\b/,
    "the retracted premise (the slice review, 2026-09-11) stays out of the suite's comments and assertion messages");
  assert.doesNotMatch(prose, /re-read shows (?:it|what (?:that|the other) writer wrote)\b/, "…in its other wordings too");
});

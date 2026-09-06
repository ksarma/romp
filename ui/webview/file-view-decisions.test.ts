// The viewer's word for what the person accepted or rejected inside the editor is `decisions` — the plan's word for
// the save verb's two lists, the chunk's canonical name (editor-chunk.ts, TrackDecisions) and the viewer's own
// EditDecisions. The slice's first word, a ledger, is one CONTEXT.md lists under Avoid for the comments log, which is
// where the host writes these very decisions; the chunk moved to `decisions` in the round-2 review and kept the old
// spelling on marked alias lines for callers that had not moved — and the viewer was that caller, still saying
// "ledger" in the prose beside "log" where the save is built (the round-3 review). This file pins the viewer's half:
// the prose says decisions, and the old word survives only on the lines that read or pass the chunk's aliases, each
// marked "old spelling" — kept because the viewer's test harnesses stub the handle by those names and
// file-view-seam.test.ts pins the mount line's text; the identifiers go with those tests, and the aliases with them.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const VIEW = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "file-view.ts"), "utf8");
const LINES = VIEW.split("\n");

test("the old word appears in file-view.ts only on lines marked as the old spelling", () => {
  const unmarked = LINES.map((l, i) => [i + 1, l] as const).filter(([, l]) => /ledger/i.test(l) && !/old spelling/.test(l));
  assert.deepEqual(unmarked, [], "every use of the old word is an alias read, an alias passed, or the note explaining them");
});

test("the alias lines are exactly the chunk's two aliases in use: the handle's ledger() reader and the mount's onLedger callback", () => {
  const code = LINES.filter((l) => /ledger/i.test(l) && !l.trim().startsWith("//"));
  assert.equal(code.length, 3, "the handle's type, its one reader, and the mount's callback");
  for (const l of code) assert.match(l, /ledger\(\): EditDecisions \}|cm\.track\.ledger\(\)|onLedger: \(\) =>/, l);
  assert.doesNotMatch(VIEW, /(?:let|const|function) [a-z]*[Ll]edger|type [A-Za-z]*Ledger|interface [A-Za-z]*Ledger/, "no identifier of the old spelling is the viewer's own");
});

test("the prose says decisions: EditDecision's doc, the applied/unsent block, the exit and the ack", () => {
  const docLine = LINES.find((l) => l.startsWith("/** One decision taken inside the editor"));
  assert.ok(docLine, "EditDecision's doc comment");
  assert.match(docLine!, /as the chunk's decisions report/);
  const block = VIEW.split("let trackedEdit: TrackedEdit | null = null;")[1].split("let applied: EditDecisions")[0];
  assert.match(block, /The chunk's decisions are a fold over every accept and reject since the MOUNT/);
  assert.match(block, /the decisions beyond it/);
  assert.match(block, /a fresh mount starts its decisions afresh/);
  assert.doesNotMatch(block, /ledger/i, "the block that sits beside 'logged' and 'the log' names the other record by its own word");
  assert.match(VIEW, /the decisions went with the editor; the next mount starts its own afresh/);
  assert.match(VIEW, /it is in the decisions beyond what this save carried/);
});

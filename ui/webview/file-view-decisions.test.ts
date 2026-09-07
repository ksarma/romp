// The viewer's word for what the person accepted or rejected inside the editor is `decisions` — the plan's word for
// the save verb's two lists, the chunk's canonical name (editor-chunk.ts, TrackDecisions) and the viewer's own
// EditDecisions. The slice's first word was one CONTEXT.md lists under Avoid for the comments log, which is where the
// host writes these very decisions; the chunk moved to `decisions` in the round-2 review and kept the old spelling on
// alias lines for the viewer, which still read and passed the aliases (the round-3 review) because its test harnesses
// stubbed the handle by those names. The consolidation pass moved the viewer, the harnesses and the chunk together and
// dropped the aliases. This file pins the viewer's half: the prose says decisions, the handle is read as decisions()
// and the mount passes onDecisions, and the old word appears nowhere in file-view.ts — editor-chunk-decisions.test.ts
// pins the same of the chunk and of every other webview module.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const VIEW = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "file-view.ts"), "utf8");
const LINES = VIEW.split("\n");
const OLD = "led" + "ger";   // assembled so this file's own text is not a hit for a scan of the test tree

test("the old word appears nowhere in file-view.ts: not as an identifier, not in prose", () => {
  const hits = LINES.map((l, i) => [i + 1, l] as const).filter(([, l]) => new RegExp(OLD, "i").test(l));
  assert.deepEqual(hits, [], "the viewer says decisions (its EditDecisions) where it once said the avoided word");
});

test("the viewer reads the chunk's decisions() and passes onDecisions: the canonical names, no alias", () => {
  assert.match(VIEW, /track\?: \{ suggestions\(\): unknown\[\]; decisions\(\): EditDecisions \}/, "the handle's type");
  assert.match(VIEW, /const l = cm && cm\.track \? cm\.track\.decisions\(\) : null;/, "its one reader, for unsent()");
  assert.match(VIEW, /\btrack: \{ suggestions: pending\.records, authorColor: pending\.authorColor, onDecisions: \(\) => \{/, "the mount's callback");
  assert.doesNotMatch(VIEW, /\bonLed|\.led[a-z]*\(\)/i, "no alias shape of the old spelling");
});

test("the prose says decisions: EditDecision's doc, the applied/unsent block, the exit and the ack", () => {
  const docLine = LINES.find((l) => l.startsWith("/** One decision taken inside the editor"));
  assert.ok(docLine, "EditDecision's doc comment");
  assert.match(docLine!, /as the chunk's decisions report/);
  const block = VIEW.split("let trackedEdit: TrackedEdit | null = null;")[1].split("let applied: EditDecisions")[0];
  assert.match(block, /The chunk's decisions are a fold over every accept and reject since the MOUNT/);
  assert.match(block, /the decisions beyond it/);
  assert.match(block, /a fresh mount starts its decisions afresh/);
  assert.match(VIEW, /the decisions went with the editor; the next mount starts its own afresh/);
  assert.match(VIEW, /it is in the decisions beyond what this save carried/);
});

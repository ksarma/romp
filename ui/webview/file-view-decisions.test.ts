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
// One value is let through, by value and inside one literal alone: the quoted page class of the other pages' tree nodes (the old
// word, a hyphen and tnode; styles.css), which a sheet dims, so SHEET_DIM_CLASSES, the classes the viewer takes off an author's
// markup around a figure, holds it as the sheets spell it (file-figure-open.test.ts holds that list to the sheets both ways). It
// is another page's class name, not the viewer's word for decisions. The quoted token is taken off the lines of that literal
// before the read, and nothing else is, so the word anywhere else in file-view.ts, on those lines included, stays a hit; and
// the literal is found by its declaration, so a file without it lets nothing through.
const PAGE_CLASS = '"' + OLD + '-tnode"';
const LIST_FROM = LINES.findIndex((l) => l.startsWith("const SHEET_DIM_CLASSES"));
const LIST_TO = LIST_FROM < 0 ? -1 : LINES.findIndex((l, i) => i > LIST_FROM && l.startsWith("]);"));
const readLine = (l: string, i: number): string => (LIST_FROM >= 0 && i >= LIST_FROM && i <= LIST_TO ? l.split(PAGE_CLASS).join("") : l);

test("the old word appears nowhere in file-view.ts: not as an identifier, not in prose (one quoted page class let through inside the drop list's literal, by value)", () => {
  const hits = LINES.map((l, i) => [i + 1, l, readLine(l, i)] as const).filter(([, , r]) => new RegExp(OLD, "i").test(r)).map(([n, l]) => [n, l] as const);
  assert.deepEqual(hits, [], "the viewer says decisions (its EditDecisions) where it once said the avoided word; the one quoted page class inside SHEET_DIM_CLASSES's literal is let through by value and nothing else is (a property pin over every line of file-view.ts)");
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

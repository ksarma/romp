// The plan's account of which panel elements have a rule of their own (plans/file-review.md, the Slice 2 build note
// and the composer follow-on) is held to the sheets. The Slice 2 note said the new elements (.fc-change, .fc-group,
// .fc-hosted, .fc-foot, .fc-diff) wear the Slice 1 classes and need no rule of their own; the review of the reply-place
// follow-on (2026-09-07) gave .fc-hosted one (a flex column at the turns' gap, both sheets; feed-fc-hosted-gap.test.ts
// pins the rule itself), and for a round the plan still listed .fc-hosted among the elements that need none, while the
// follow-on paragraph never named the rule. A reader of that sentence would take the rule for a stray and remove it,
// or not mirror it when the block is next edited, and the 0px seam would be back. This file holds the two sides
// together, the way file-review-docs.test.ts holds the Tests and Docs sections to the tree: the Slice 2 sentence
// names .fc-hosted as its one exception; every other element it lists has no rule of its own in either sheet (so the
// sentence stays true of them); .fc-hosted has one in both sheets (so the exception stays true); and the follow-on
// note names the rule and the test that pins it, which exists. Whichever side moves first, the plan or a sheet, a
// test here names the other. Prose is matched across line wraps. Synthetic throughout — nothing here renders.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const ROOT = path.resolve(process.cwd(), "..");
const read = (...p: string[]) => fs.readFileSync(path.join(ROOT, ...p), "utf8");
const PLAN = read("plans", "file-review.md");
const FEED = read("ui", "webview", "feed.css");
const CHAT = read("ui", "webview", "styles.css");

const escapeRe = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
/** A phrase as the plan wraps it: any run of whitespace between words. */
const prose = (words: string) => new RegExp(words.trim().split(/\s+/).map(escapeRe).join("\\s+"));
/** The plan's text from one marker up to (not including) the next. */
function between(doc: string, from: string, to: string): string {
  const start = doc.indexOf(from);
  assert.notEqual(start, -1, JSON.stringify(from) + " is in the plan");
  const end = doc.indexOf(to, start);
  assert.notEqual(end, -1, JSON.stringify(to) + " follows it in the plan");
  return doc.slice(start, end);
}
/** Whether a sheet has a rule whose selector list names the bare class on its own (`.x {`, `.x,` or `, .x {`). */
const hasOwnRule = (css: string, cls: string) => new RegExp("(?:^|\\n|,[ \\t]*)" + escapeRe(cls) + "[ \\t]*[{,]").test(css);

const SLICE2 = between(PLAN, "The Slice 2 build (2026-09-06), panel side", "The composer follow-on (2026-09-07)");
const FOLLOW_ON = between(PLAN, "The composer follow-on (2026-09-07)", "### Slice 3: region comments on images");
/** The elements the Slice 2 note lists as wearing the Slice 1 classes, read from the note itself. */
const listed = Array.from(SLICE2.match(/The new\s+elements \(([^)]+)\)/)![1].matchAll(/`(\.fc-[a-z-]+)`/g), (m) => m[1]);

test("the Slice 2 note lists the new elements and names .fc-hosted as the one that has a rule of its own", () => {
  assert.deepEqual(listed, [".fc-change", ".fc-group", ".fc-hosted", ".fc-foot", ".fc-diff"], "the list the note gives");
  assert.match(SLICE2, prose("need no rule of their own to be usable, all but `.fc-hosted`"), "the exception, in the same sentence as the claim");
  assert.match(SLICE2, prose("gave a flex-column rule at the turns' gap"), "what the exception's rule is");
});

test("the sheets agree: no rule of its own for the elements the note says need none, one in both sheets for .fc-hosted", () => {
  for (const [name, css] of [["feed.css", FEED], ["styles.css", CHAT]] as const) {
    for (const cls of listed.filter((c) => c !== ".fc-hosted")) {
      assert.ok(!hasOwnRule(css, cls), `${name} has a rule of its own for ${cls}; the plan's Slice 2 note says it needs none — change the note or the sheet`);
    }
    assert.ok(hasOwnRule(css, ".fc-hosted"), `${name} has no .fc-hosted rule; the plan says both sheets carry one (feed-fc-hosted-gap.test.ts pins its shape)`);
  }
});

test("the follow-on note names the .fc-hosted rule, the seam it closed, and the test that pins it", () => {
  assert.match(FOLLOW_ON, prose("A comment on a change card (`.fc-hosted`) had no rule of its own until then"));
  assert.match(FOLLOW_ON, prose("it is a flex column at the turns' own gap now, in both sheets"));
  assert.match(FOLLOW_ON, prose("(`feed-fc-hosted-gap.test.ts`)"), "the test the note credits");
  assert.ok(fs.existsSync(path.join(ROOT, "ui", "webview", "feed-fc-hosted-gap.test.ts")), "and that file exists");
});

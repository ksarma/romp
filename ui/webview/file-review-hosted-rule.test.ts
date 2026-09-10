// The plan's account of which panel elements have a rule of their own (plans/file-review.md, the Slice 2 build note
// and the composer follow-on) is held to the sheets. The Slice 2 note lists the elements the build added as wearing the
// Slice 1 classes and needing no rule of their own. For a while one of them, `.fc-hosted` (the comment drawn inside a
// change card), had a rule after all (a flex column at the turns' gap, in both sheets, from the reply-place follow-on's
// review, 2026-09-07), and this file held the plan's exception to the sheets. The about follow-on (2026-09-10) draws no
// comment inside a change card: the element, its rule in both sheets and the test that pinned the rule
// (feed-fc-hosted-gap.test.ts) are gone. This file now holds the other direction: every element the note lists has no
// rule of its own in either sheet (so the sentence stays true of them), and `.fc-hosted` is in neither sheet nor the
// panel (so nothing brings the element or its rule back unnoticed). The plan's wording of the element's departure is the
// user's and is matched loosely here: a mention of `.fc-hosted` in either note must sit with the about follow-on that
// removed it, so a rewording does not fail this file. Prose is matched across line wraps. Synthetic throughout: nothing
// here renders.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const ROOT = path.resolve(process.cwd(), "..");
const read = (...p: string[]) => fs.readFileSync(path.join(ROOT, ...p), "utf8");
const PLAN = read("plans", "file-review.md");
const FEED = read("ui", "webview", "feed.css");
const CHAT = read("ui", "webview", "styles.css");
const PANEL = read("ui", "webview", "file-comments.ts");

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
function listedElements(): string[] {
  const m = SLICE2.match(/The new\s+elements \(([^)]+)\)/);
  assert.ok(m, "the Slice 2 note lists the new elements in parentheses");
  return Array.from(m![1].matchAll(/`(\.fc-[a-z-]+)`/g), (x) => x[1]);
}

test("the Slice 2 note lists the new elements, none of them .fc-hosted, and says they need no rule of their own", () => {
  const listed = listedElements();
  assert.ok(listed.length > 0, "the list the note gives: " + listed.join(", "));
  assert.ok(!listed.includes(".fc-hosted"), ".fc-hosted is not among the elements the panel has");
  assert.match(SLICE2, prose("need no rule of their own to be usable"), "the claim");
  for (const [name, note] of [["the Slice 2 note", SLICE2], ["the composer follow-on note", FOLLOW_ON]] as const) {
    if (note.includes(".fc-hosted")) assert.match(note, /about follow-on/, name + " mentions .fc-hosted only beside the about follow-on that removed it");
  }
});

test("the sheets agree: no rule of its own for any element the note lists, and no .fc-hosted rule or class in either sheet or the panel", () => {
  const listed = listedElements();
  for (const [name, css] of [["feed.css", FEED], ["styles.css", CHAT]] as const) {
    for (const cls of listed) assert.ok(!hasOwnRule(css, cls), `${name} has a rule of its own for ${cls}; the plan's Slice 2 note says it needs none; change the note or the sheet`);
    assert.ok(!css.includes(".fc-hosted"), `${name} still names .fc-hosted; the element went with the about follow-on (2026-09-10)`);
  }
  assert.ok(!PANEL.includes("fc-hosted") && !PANEL.includes("renderHosted"), "the panel draws no comment inside a change card");
});

test("the test that pinned the .fc-hosted rule is gone with the rule", () => {
  assert.ok(!fs.existsSync(path.join(ROOT, "ui", "webview", "feed-fc-hosted-gap.test.ts")), "feed-fc-hosted-gap.test.ts would pin a rule neither sheet has");
});

// The kind-cue comment in feed.css's panel block (the filter follow-on, plans/file-review.md "The filter follow-on
// (2026-09-07)") says what the .fc-kind rule does in the plan's own literal terms. The plan first said the kind word is
// rendered "in the note's dress" and the change edge is "the muted tone"; its review found that neither named the thing
// it meant — the first is the .fc-kind rule copying .fc-note's color and size, and "note" is a word CONTEXT.md lists under
// Avoid for a file comment, so a reader could take it for the comment's own text — and rewrote the plan to name the rule,
// the tokens and the border (tools/file-review-plan-kind-cue.test.mjs holds that wording). The same two figures had been
// written into both sheets' comments above the rule and stood there after the plan changed (the second review): a reader
// at the rule learns its dress from the comment, not the plan. This module holds feed.css's comment to the plan's terms —
// the selector it copies, the tokens, the width, and no figure where a literal phrase exists — and holds the statement to
// the declarations it describes. styles.css carries the same bytes: file-comments.test.ts pins the whole panel block
// byte-equal across the two sheets (the feed page loads feed.css alone), and the last test here names the twin comment so
// a drift in one sheet's comment reads as that, not as an unexplained block mismatch. Synthetic: only the repo's own text.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const read = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const FEED = read("feed.css");
const CHAT = read("styles.css");

// The panel block, and the comment that stands directly above the .fc-kind rule in it.
function panelBlock(css: string): string {
  const a = css.indexOf("/* ── file comments panel (plans/file-review.md Slice 1; file-comments.ts)");
  const b = css.indexOf("/* ── end file comments panel ── */");
  assert.ok(a >= 0 && b > a, "the panel block and its end marker");
  return css.slice(a, b);
}
function kindCueComment(css: string): string {
  const block = panelBlock(css);
  const rule = block.indexOf("\n.fc-kind {");
  assert.ok(rule >= 0, "the .fc-kind rule is in the panel block");
  const open = block.lastIndexOf("/*", rule);
  assert.ok(open >= 0, "a comment opens above the .fc-kind rule");
  const c = block.slice(open, rule);
  assert.ok(c.endsWith("*/") && c.split("*/").length === 2, "one comment, closing directly above the .fc-kind rule");
  return c;
}
// A one-line rule's declarations, by selector.
function decls(css: string, selector: string): string[] {
  const m = new RegExp("^" + selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + " \\{ ([^}]*) \\}$", "m").exec(css);
  assert.ok(m, selector + " is a one-line rule in the sheet");
  return m![1].split(";").map((d) => d.trim()).filter(Boolean);
}

test("feed.css: the kind-cue comment names the rule the word copies by its selector and tokens, and the edge's width and token", () => {
  const c = kindCueComment(FEED);
  assert.match(c, /^\/\* the kind cue \(the filter follow-on, 2026-09-07\):/, "the comment is the kind cue's");
  assert.match(c, /styled\s+like \.fc-note \(--dim, 0\.86em\)/, "the word is styled like .fc-note, named by selector, with the color and size it copies");
  assert.match(c, /3px border in the accent for a comment \(a\s+region is one\) and in --text-muted for a change/, "the edge: its width, the accent for a comment, --text-muted for a change");
  assert.match(c, /renderCard \/ renderChangeCard set data-cue/, "the setters of the attribute the edge rules read");
});

test("feed.css: the comment states the styling, it does not figure it — no dress, no muted tone, and \"note\" only as the .fc-note selector", () => {
  const c = kindCueComment(FEED);
  // the two figures the plan's review replaced (tools/file-review-plan-kind-cue.test.mjs holds the plan to the same)
  assert.doesNotMatch(c, /\bdress\b/, "'in the note's dress' named no rule: say which rule the word is styled like");
  assert.doesNotMatch(c, /muted tone/, "'the muted tone' named no token: say --text-muted");
  // CONTEXT.md lists "note" under Avoid for a file comment, and the comment body IS the nearest thing called a note in this
  // panel (file-comments.ts: `note` is the saved body), so the word appears here only inside the selector .fc-note
  assert.doesNotMatch(c, /\bnote's\b/, "no \"the note's …\": that reads as the file comment's own text");
  assert.doesNotMatch(c.replace(/\.fc-note\b/g, ""), /\bnotes?\b/, "\"note\" only as the .fc-note selector");
});

test("feed.css: the comment's statement holds — .fc-kind carries .fc-note's color and size, the change edge reads --text-muted", () => {
  const kind = decls(FEED, ".fc-kind"), ref = decls(FEED, ".fc-note");
  for (const d of ["color: var(--dim)", "font-size: 0.86em"]) {
    assert.ok(ref.includes(d), ".fc-note has " + d);
    assert.ok(kind.includes(d), ".fc-kind has " + d + " (the comment says it is styled like .fc-note)");
  }
  assert.ok(FEED.includes('\n.fc-card[data-cue="change"]:not(.fc-card-detached) { border-left: 3px solid var(--text-muted); }\n'), "the change edge: 3px, --text-muted");
  assert.ok(FEED.includes('\n.fc-card[data-cue="comment"]:not(.fc-card-detached) { border-left: 3px solid var(--accent); }\n'), "the comment edge: 3px, the accent");
});

test("styles.css carries the same kind-cue comment: the panel block is byte-equal across the sheets (file-comments.test.ts), comments included", () => {
  assert.equal(kindCueComment(CHAT), kindCueComment(FEED), "the chat sheet's comment above .fc-kind is feed.css's, byte for byte");
});

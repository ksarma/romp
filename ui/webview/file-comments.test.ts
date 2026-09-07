// The viewer's Comments panel (plans/file-review.md, Slice 1): the pure half runs for real (the view
// model, the unsent count, the Send-to-session message against the kernel's literal, the Log rows, the
// poll's verdicts); the seam's shared consent helper and the action's mount run against the small DOM
// stand-in the GitHub link's test uses; what neither can show (the wire shapes, the one delegate root,
// the string mtime comparison, the sheets) stays pinned at source. Synthetic fixtures only: the notes-api
// world, placeholder ids, TESTHOST.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import { spawnSync } from "node:child_process";
import type { FileViewActionCtx } from "./file-view";
import {
  type Status, type Hunk, type StoreComment, type MessageOpts, unsentCount, actionLabel, describeComment, sendParts, buildSendMessage, neutralizeRompMarkers,
  cardModel, logRowText, pollBaseline, headVerdict, pollTargets, mtimeMoved, editBlockedReason, lineStartOffset, folderOf, ABSENT,
} from "./file-comments-model";

const web = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const SRC = web("file-comments.ts");
const MODEL = web("file-comments-model.ts");
const VIEW = web("file-view.ts");
const GEAR = web("gear.js");
const CHAT_CSS = web("styles.css");
const FEED_CSS = web("feed.css");
const GUIDE = fs.readFileSync(path.resolve(process.cwd(), "..", "docs", "guide.md"), "utf8");
const ADR = fs.readFileSync(path.resolve(process.cwd(), "..", "docs", "adr", "0002-file-comments-in-the-track-changents-sidecar.md"), "utf8");

// ── fixtures: the notes-api world ──────────────────────────────────────────────────────────────────
const SID = "11111111-2222-3333-4444-555555555555";   // the api session's stable id (its ROMP_SID, the CLIs' authorId)
const ABS = "/repo/notes-api/docs/report.md";
const T0 = 1757145600000;                              // 2026-09-06T08:00:00Z, as the CLIs stamp `ts`

const passage: StoreComment = {
  id: T0 + "-118", author: "you", ts: T0, body: "Which cache? Say which.",
  anchor: { quote: "shipping the cache in v1.2", prefix: "We recommend ", suffix: "." }, replies: [], resolved: false,
};
const replied: StoreComment = {
  id: (T0 - 60000) + "-40", author: "you", ts: T0 - 60000, body: "Cut this paragraph; it repeats the summary.",
  anchor: { quote: "The api session cut p95 latency by 40%", prefix: "## Findings\n", suffix: " and the" },
  replies: [{ author: "api", authorId: SID, ts: T0 - 30000, body: "Cut it." }, { author: "you", ts: T0 + 5000, body: "Thanks, and drop the chart too." }],
  resolved: false,
};
const whole: StoreComment = { id: T0 + 9000 + "-0", author: "you", ts: T0 + 9000, body: "Add a summary at the top.", replies: [], resolved: false };
const hunk: Hunk = { id: "h1", author: "api", ts: T0 - 90000, kind: "sub", curFrom: 30, curTo: 33, baseFrom: 30, baseTo: 37, oldText: "reduced", newText: "cut", anchor: null };
const bound: StoreComment = { id: T0 + 1000 + "-5", author: "you", ts: T0 + 1000, body: "Say cut, not reduced.", suggestionId: "h1", replies: [], resolved: false };

function status(over: Partial<Status> = {}): Status {
  return {
    verb: "status", root: "/repo/notes-api", storePath: "/repo/notes-api/.trackchanges/docs%2Freport.md.json",
    trackedBy: { kind: "file", entry: "docs/report.md" }, agentTooling: "present",
    fileMtimeNs: "1757145600000000001", storeMtimeNs: "1757145600000000002", configMtimeNs: "1757145600000000003",
    store: { v: 3, path: "docs/report.md", suggestions: [], comments: [passage, replied, whole] },
    hunks: [], log: [],
    unsent: { comments: [passage.id, whole.id], replies: [{ commentId: replied.id, ts: T0 + 5000 }], accepted: 0, rejected: 0, watermark: T0 - 60000 },
    ...over,
  };
}

// ── the pure half ──────────────────────────────────────────────────────────────────────────────────

test("the unsent count is the comments log's derivation as the status reply carries it — never browser state", () => {
  assert.equal(unsentCount(status().unsent), 3, "two openings + one reply");
  assert.equal(unsentCount({ comments: [], replies: [], accepted: 2, rejected: 1, watermark: null }), 3, "decisions count too (Slice 2)");
  assert.equal(unsentCount(null), 0);
  assert.equal(unsentCount(undefined), 0);
});

test("the action-row label is the glance: plain until a sidecar exists, then the counts", () => {
  assert.equal(actionLabel(null), "Comments");
  assert.equal(actionLabel(status({ store: null, trackedBy: null })), "Comments");
  assert.equal(actionLabel(status({ store: null })), "Comments · tracked", "a tracked file with no sidecar says so");
  assert.equal(actionLabel(status()), "Comments · 3");
  assert.equal(actionLabel(status({ hunks: [hunk] })), "Comments · 3 · 1 change");
  assert.equal(actionLabel(status({ hunks: [hunk, { ...hunk, id: "h2" }] })), "Comments · 3 · 2 changes");
  const resolved = status({ store: { v: 3, path: "docs/report.md", suggestions: [], comments: [{ ...passage, resolved: true }, whole] } });
  assert.equal(actionLabel(resolved), "Comments · 1", "resolved comments leave the count");
});

test("desc is the complete parenthetical without parentheses (contract C2)", () => {
  assert.equal(describeComment(passage, []), 'on "shipping the cache in v1.2"');
  const long: StoreComment = { ...passage, anchor: { quote: "a".repeat(41) + "z", prefix: "", suffix: "" } };
  assert.equal(describeComment(long, []), 'on "' + "a".repeat(40) + '"', "the first 40 characters of the passage");
  assert.equal(describeComment(bound, [hunk]), 'on your change "reduced" to "cut"');
  assert.equal(describeComment(bound, []), "on this file", "a bound comment whose change coalesced away falls back honestly");
  assert.equal(describeComment(whole, []), "on this file");
  const region: StoreComment = { ...whole, target: { kind: "image", region: { x: 0.12, y: 0.4, w: 0.35, h: 0.2 }, hash: "abc" } };
  assert.equal(describeComment(region, []), "on the region at 0.12, 0.40, 0.35, 0.20");
  const page: StoreComment = { ...whole, target: { kind: "pdf", region: { x: 0.12, y: 0.4, w: 0.35, h: 0.2 }, page: 2, hash: "abc" } };
  assert.equal(describeComment(page, []), "on the region at 0.12, 0.40, 0.35, 0.20 of page 2");
});

test("sendParts: what one send hands over — openings the log never saw, else only the new replies, oldest first", () => {
  const p = sendParts(status());
  assert.deepEqual(p.comments.map((c) => c.id), [replied.id, passage.id, whole.id], "oldest first, by the comment's ts");
  assert.deepEqual(p.comments[0], { id: replied.id, desc: 'on "The api session cut p95 latency by 40%"', body: "Thanks, and drop the chart too." },
    "an already-sent opening lists only its new reply — the session's own reply never goes back to it");
  assert.equal(p.comments[1].body, "Which cache? Say which.");
  assert.equal(p.comments[2].desc, "on this file");
  assert.equal(p.watermark, T0 + 9000, "the largest ts among what goes");
  assert.equal(p.accepted, 0); assert.equal(p.rejected, 0);
  // an opening AND a later reply on the same comment go together, blank-line joined
  const both = status({ unsent: { comments: [replied.id], replies: [{ commentId: replied.id, ts: T0 + 5000 }], accepted: 0, rejected: 0, watermark: null } });
  assert.equal(sendParts(both).comments[0].body, "Cut this paragraph; it repeats the summary.\n\nThanks, and drop the chart too.");
  // an edit step recorded as a reply has no words and never goes
  const withEdit = status({
    store: { v: 3, path: "docs/report.md", suggestions: [], comments: [{ ...replied, replies: [{ author: "api", authorId: SID, ts: T0 + 5000, kind: "edit", oldText: "a", newText: "b" }] }] },
    unsent: { comments: [], replies: [{ commentId: replied.id, ts: T0 + 5000 }], accepted: 0, rejected: 0, watermark: null },
  });
  assert.deepEqual(sendParts(withEdit).comments, []);
  assert.deepEqual(sendParts(status({ store: null })).comments, [], "no sidecar: nothing to send");
});

// ── the message: the kernel's builder is tested against THESE literals (contract C3) ──────────────
// The literals here and in tests/test_file_comments.py (TheMessage) are the spec each builder is pinned to on
// its own side; the cross-run further down feeds BOTH builders the same inputs and compares their output, so
// a change to one builder that re-pins only its own suite still fails here.
const TAIL_TRACKED =
  "To respond:\n" +
  "  • reply in words:     node ~/.claude/hooks/track-reply.mjs --file " + ABS + " --thread <id> --note \"<your reply>\"\n" +
  "  • to revise the text: node ~/.claude/hooks/track-edit.mjs --file " + ABS + " --thread <id> --old \"<exact text>\" --new \"<replacement>\"\n" +
  "\n" +
  "When you have addressed these, ask me for another look the same way you asked for this one,\n" +
  "naming the file.\n";

test("the message for ONE comment, tracked, text file — byte for byte", () => {
  const msg = buildSendMessage({ absPath: ABS, comments: [{ id: "1757145600000-118", desc: 'on "shipping the cache in v1.2"', body: "Which cache? Say which." }],
    accepted: 0, rejected: 0, tracked: true, media: false });
  assert.equal(msg,
    "[obsidian-diff] I left 1 comment on " + ABS + ".\n" +
    "\n" +
    "Comment 1757145600000-118 (on \"shipping the cache in v1.2\"):\n" +
    "Which cache? Say which.\n" +
    "\n" + TAIL_TRACKED);
});

test("the message for SEVERAL comments: one blank line between, the plural, no decisions line in Slice 1", () => {
  const msg = buildSendMessage({ absPath: ABS, comments: [
    { id: "1757145540000-40", desc: 'on "The api session cut p95 latency by 40%"', body: "Thanks, and drop the chart too." },
    { id: "1757145600000-118", desc: 'on "shipping the cache in v1.2"', body: "Which cache? Say which." },
    { id: "1757145609000-0", desc: "on this file", body: "Add a summary at the top.\n\nAnd a date." },
  ], accepted: 0, rejected: 0, tracked: true, media: false });
  assert.equal(msg,
    "[obsidian-diff] I left 3 comments on " + ABS + ".\n" +
    "\n" +
    "Comment 1757145540000-40 (on \"The api session cut p95 latency by 40%\"):\n" +
    "Thanks, and drop the chart too.\n" +
    "\n" +
    "Comment 1757145600000-118 (on \"shipping the cache in v1.2\"):\n" +
    "Which cache? Say which.\n" +
    "\n" +
    "Comment 1757145609000-0 (on this file):\n" +
    "Add a summary at the top.\n\nAnd a date.\n" +
    "\n" + TAIL_TRACKED);
});

test("tracked OFF: the second bullet is the edit-normally wording; decisions appear only when any were made", () => {
  const off = buildSendMessage({ absPath: ABS, comments: [{ id: "1757145600000-118", desc: 'on "shipping the cache in v1.2"', body: "Which cache? Say which." }],
    accepted: 0, rejected: 0, tracked: false, media: false });
  assert.equal(off,
    "[obsidian-diff] I left 1 comment on " + ABS + ".\n" +
    "\n" +
    "Comment 1757145600000-118 (on \"shipping the cache in v1.2\"):\n" +
    "Which cache? Say which.\n" +
    "\n" +
    "To respond:\n" +
    "  • reply in words:     node ~/.claude/hooks/track-reply.mjs --file " + ABS + " --thread <id> --note \"<your reply>\"\n" +
    "  • to revise the text: edit the file normally, then say what you changed with the reply command above\n" +
    "\n" +
    "When you have addressed these, ask me for another look the same way you asked for this one,\n" +
    "naming the file.\n");
  const decided = buildSendMessage({ absPath: ABS, comments: [{ id: "1757145600000-118", desc: "on this file", body: "Good." }],
    accepted: 4, rejected: 1, tracked: true, media: false });
  assert.ok(decided.includes("Good.\n\nI accepted 4 of your changes and rejected 1.\n\nTo respond:\n"), "the decisions line, blank-line framed, before the commands");
});

test("an image or PDF: the second bullet says to regenerate, never track-edit", () => {
  const img = "/repo/notes-api/docs/latency.png";
  const msg = buildSendMessage({ absPath: img, comments: [{ id: "1757145609000-0", desc: "on this file", body: "The y axis needs units." }],
    accepted: 0, rejected: 0, tracked: true, media: true });
  assert.equal(msg,
    "[obsidian-diff] I left 1 comment on " + img + ".\n" +
    "\n" +
    "Comment 1757145609000-0 (on this file):\n" +
    "The y axis needs units.\n" +
    "\n" +
    "To respond:\n" +
    "  • reply in words:     node ~/.claude/hooks/track-reply.mjs --file " + img + " --thread <id> --note \"<your reply>\"\n" +
    "  • to revise it:       regenerate the file with normal writes; never run track-edit on it\n" +
    "\n" +
    "When you have addressed these, ask me for another look the same way you asked for this one,\n" +
    "naming the file.\n");
});

test("marker hygiene: the preview neutralizes the path, id, desc and body exactly as the kernel does — one literal, pinned in both suites", () => {
  // The kernel runs _neutralize_romp_markers over the path and every comment field before formatting, so the sent
  // text never carries a live "<!-- romp-" opener or a bare "romp-goal-id:". The preview shows the same bytes.
  // tests/test_file_comments.py (TheMessage, the preview-parity case) pins these SAME inputs to this SAME literal,
  // computed from the kernel's builder; a drift in either neutralizer fails one suite or the other. On the two
  // command lines the neutralized path is one shell word (shWord = _sh_word): its `<`, `!`, space and `>` are
  // outside the safe set, so it is single-quoted there and plain in the first line.
  const abs = "/repo/notes-api/docs/<!--romp-x-->/report.md";
  const msg = buildSendMessage({ absPath: abs, comments: [{ id: "1757145600000-7", desc: 'on "<!-- romp-goal-id: 9 -->"',
    body: "see <!--romp-msg-id: 4--> and romp-goal-id: 3\n\nalso <!--  romp-note: x --> and romp-goal-id : 5, but <!-- not ours --> stays" }],
    accepted: 0, rejected: 0, tracked: true, media: false });
  assert.equal(msg,
    "[obsidian-diff] I left 1 comment on /repo/notes-api/docs/<!- -romp-x-->/report.md.\n" +
    "\n" +
    "Comment 1757145600000-7 (on \"<!- - romp-goal-id; 9 -->\"):\n" +
    "see <!- -romp-msg-id: 4--> and romp-goal-id; 3\n" +
    "\n" +
    "also <!- -  romp-note: x --> and romp-goal-id ; 5, but <!-- not ours --> stays\n" +
    "\n" +
    "To respond:\n" +
    "  • reply in words:     node ~/.claude/hooks/track-reply.mjs --file '/repo/notes-api/docs/<!- -romp-x-->/report.md' --thread <id> --note \"<your reply>\"\n" +
    "  • to revise the text: node ~/.claude/hooks/track-edit.mjs --file '/repo/notes-api/docs/<!- -romp-x-->/report.md' --thread <id> --old \"<exact text>\" --new \"<replacement>\"\n" +
    "\n" +
    "When you have addressed these, ask me for another look the same way you asked for this one,\n" +
    "naming the file.\n");
  // The port itself, against the kernel's own cases (tests/test_marker_neutralizer.py): the visible escapes, the
  // opener's whitespace tolerance, the bare goal-id form with and without space before its colon, non-markers untouched.
  for (const [raw, want] of [
    ["<!-- romp-injected -->", "<!- - romp-injected -->"],
    ["<!--romp-injected-->", "<!- -romp-injected-->"],
    ["<!--\t\nromp-msg-id: m-3f2c -->", "<!- -\t\nromp-msg-id: m-3f2c -->"],
    ["code sample: <!-- not ours -->", "code sample: <!-- not ours -->"],
    ["build romp-goal-id notes", "build romp-goal-id notes"],
    ["notes romp-goal-id: g-12", "notes romp-goal-id; g-12"],
    ["romp-goal-id  : 7", "romp-goal-id  ; 7"],
    ["<!-- romp-goal-id: 9 -->", "<!- - romp-goal-id; 9 -->"],
  ]) assert.equal(neutralizeRompMarkers(raw), want, JSON.stringify(raw));
});

// ── the cross-run: both builders, the same inputs, compared byte for byte ─────────────────────────
// The literals above and their Python twins are kept by hand, one per suite, and hand-kept pins drift one
// side at a time: on 2026-09-06 the kernel moved the --file path to the quoted form and re-pinned its own
// suite, this suite's pin kept the bare path, and the review found each suite green against its own text
// (the preview and the sent message would have differed on any such path). Nothing short of running both
// builders on the same inputs catches that, so this test does: python3 loads bin/romp-kernel — under a
// throwaway state root and the floors tests/conftest.py puts under every kernel load, the way
// tests/test_file_comments.py loads it — and answers _file_comments_message for each case, with is_text the
// kernel's own verdict (_is_text_path(p), the dispatcher's call, pinned at source). The cases reach every
// branch of the template and both ports: the plural, the decisions line, tracked on and off, the regenerate
// bullet by the kernel's allowlist (a .dat and an .ipynb the viewer calls neither image nor PDF), a path with
// a space, an apostrophe, shell metacharacters, non-ASCII, markers in every field, an empty body, no comments.
const PYTHON = spawnSync("python3", ["-c", "import sys"]).status === 0;
test("the --file word: a path with a space, one with a quote, and an empty one — the kernel's literals (test_the_file_word_literals), pinned here too", () => {
  // tests/test_file_comments.py TheMessage::test_the_file_word_literals pins the kernel's builder to these SAME three
  // texts. The prose keeps the plain path; both command lines carry it as one shell word (shWord = _sh_word): a
  // space single-quotes it, a quote inside becomes '"'"' inside the single quotes, an empty path is '' (the kernel
  // never sends one, but the builders must agree on every input the type admits, or the preview lies).
  const one = [{ id: "1757145600000-118", desc: "on this file", body: "Good." }];
  assert.equal(buildSendMessage({ absPath: "/repo/notes-api/vault/Meeting notes.md", comments: one, accepted: 0, rejected: 0, tracked: true, media: false }),
    "[obsidian-diff] I left 1 comment on /repo/notes-api/vault/Meeting notes.md.\n" +
    "\n" +
    "Comment 1757145600000-118 (on this file):\n" +
    "Good.\n" +
    "\n" +
    "To respond:\n" +
    "  • reply in words:     node ~/.claude/hooks/track-reply.mjs --file '/repo/notes-api/vault/Meeting notes.md' --thread <id> --note \"<your reply>\"\n" +
    "  • to revise the text: node ~/.claude/hooks/track-edit.mjs --file '/repo/notes-api/vault/Meeting notes.md' --thread <id> --old \"<exact text>\" --new \"<replacement>\"\n" +
    "\n" +
    "When you have addressed these, ask me for another look the same way you asked for this one,\n" +
    "naming the file.\n");
  assert.equal(buildSendMessage({ absPath: "/repo/notes-api/vault/it's here.md", comments: one, accepted: 0, rejected: 0, tracked: false, media: false }),
    "[obsidian-diff] I left 1 comment on /repo/notes-api/vault/it's here.md.\n" +
    "\n" +
    "Comment 1757145600000-118 (on this file):\n" +
    "Good.\n" +
    "\n" +
    "To respond:\n" +
    "  • reply in words:     node ~/.claude/hooks/track-reply.mjs --file '/repo/notes-api/vault/it'\"'\"'s here.md' --thread <id> --note \"<your reply>\"\n" +
    "  • to revise the text: edit the file normally, then say what you changed with the reply command above\n" +
    "\n" +
    "When you have addressed these, ask me for another look the same way you asked for this one,\n" +
    "naming the file.\n");
  // an empty path has no extension, so both builders call it non-text (the kernel's _is_text_path, isTextPath here)
  assert.equal(buildSendMessage({ absPath: "", comments: one, accepted: 0, rejected: 0, tracked: true, media: false }),
    "[obsidian-diff] I left 1 comment on .\n" +
    "\n" +
    "Comment 1757145600000-118 (on this file):\n" +
    "Good.\n" +
    "\n" +
    "To respond:\n" +
    "  • reply in words:     node ~/.claude/hooks/track-reply.mjs --file '' --thread <id> --note \"<your reply>\"\n" +
    "  • to revise it:       regenerate the file with normal writes; never run track-edit on it\n" +
    "\n" +
    "When you have addressed these, ask me for another look the same way you asked for this one,\n" +
    "naming the file.\n");
});

test("cross-run: buildSendMessage and the kernel's _file_comments_message agree on every branch, from the same inputs",
  { skip: PYTHON ? false : "python3 not installed on this machine" }, () => {
  const REPO = path.resolve(process.cwd(), "..");
  const KERNEL = fs.readFileSync(path.join(REPO, "kernel", "kernel.py"), "utf8");
  assert.match(KERNEL, /_file_comments_message\(p, comments, accepted, rejected, bool\(msg\.get\("tracked"\)\), _is_text_path\(p\)\)/,
    "the send op's call — is_text is the kernel's verdict on the path, which is what this cross-run mirrors");

  const one = [{ id: "1757145600000-118", desc: 'on "shipping the cache in v1.2"', body: "Which cache? Say which." }];
  const three = [
    { id: "1757145540000-40", desc: 'on "The api session cut p95 latency by 40%"', body: "Thanks, and drop the chart too." },
    { id: "1757145600000-118", desc: 'on your change "reduced" to "cut"', body: "Keep \"reduced\".\n\nIt is the word the abstract uses." },
    { id: "1757145609000-0", desc: "on this file", body: "Add a summary at the top.\n\nAnd a date." },
  ];
  const markers = [{ id: "1757145600000-7", desc: 'on "<!-- romp-goal-id: 9 -->"',
    body: "see <!--romp-msg-id: 4--> and romp-goal-id: 3\n\nalso <!--  romp-note: x --> and romp-goal-id : 5, but <!-- not ours --> stays" }];
  const odd = [
    { id: "", desc: "", body: "" },
    { id: "1757145600000-1", desc: "on the region at 0.12, 0.40, 0.35, 0.20 of page 2", body: "  leading and trailing blanks  \n" },
    { id: "1757145600000-2", desc: 'on "naïve — «quoted»"', body: "Ünïcödé, an em dash — and a tab\tinside\r\nand a CRLF." },
  ];
  const cases: MessageOpts[] = [
    { absPath: ABS, comments: one, accepted: 0, rejected: 0, tracked: true },
    { absPath: ABS, comments: three, accepted: 0, rejected: 0, tracked: true },
    { absPath: ABS, comments: one, accepted: 0, rejected: 0, tracked: false },
    { absPath: ABS, comments: one, accepted: 4, rejected: 1, tracked: true },
    { absPath: ABS, comments: one, accepted: 0, rejected: 2, tracked: false },
    { absPath: ABS, comments: [], accepted: 0, rejected: 0, tracked: true },
    { absPath: ABS, comments: odd, accepted: 0, rejected: 0, tracked: true },
    { absPath: "/repo/notes-api/docs/latency.png", comments: one, accepted: 0, rejected: 0, tracked: true },
    { absPath: "/repo/notes-api/docs/paper.pdf", comments: one, accepted: 1, rejected: 0, tracked: false },
    { absPath: "/repo/notes-api/data/latency.dat", comments: one, accepted: 0, rejected: 0, tracked: true },
    { absPath: "/repo/notes-api/data/report.ipynb", comments: one, accepted: 0, rejected: 0, tracked: true },
    { absPath: "/repo/notes-api/docs/flow.svg", comments: one, accepted: 0, rejected: 0, tracked: true },
    { absPath: "/repo/notes-api/Makefile", comments: one, accepted: 0, rejected: 0, tracked: true },
    { absPath: "/repo/notes-api/.env.local", comments: one, accepted: 0, rejected: 0, tracked: true },
    { absPath: "/repo/notes-api/docs/Report.MD", comments: one, accepted: 0, rejected: 0, tracked: true },
    { absPath: "/repo/notes-api/vault/Meeting notes.md", comments: one, accepted: 0, rejected: 0, tracked: true },
    { absPath: "/repo/notes-api/vault/Meeting notes.md", comments: one, accepted: 0, rejected: 0, tracked: false },
    { absPath: "/repo/notes-api/vault/it's here.md", comments: one, accepted: 0, rejected: 0, tracked: true },
    { absPath: "/repo/notes-api/vault/notes; touch PWNED #.md", comments: one, accepted: 0, rejected: 0, tracked: true },
    { absPath: "/repo/notes-api/vault/a$(touch PWNED2).md", comments: one, accepted: 0, rejected: 0, tracked: true },
    { absPath: "/repo/notes-api/vault/résumé.md", comments: one, accepted: 0, rejected: 0, tracked: true },
    { absPath: "/repo/notes-api/docs/<!--romp-x-->/report.md", comments: markers, accepted: 0, rejected: 0, tracked: true },
    { absPath: "/repo/notes-api/<!-- romp-x -->/latency.png", comments: markers, accepted: 2, rejected: 3, tracked: true },
  ];
  // One python3, all cases on stdin, one JSON array back: the kernel's text for each, in order.
  const script = [
    "import json, os, sys",
    "from importlib.machinery import SourceFileLoader",
    "os.environ.pop('ROMP_STATE_DIR', None)",
    "km = SourceFileLoader('romp_kernel_parity', os.path.join(sys.argv[1], 'bin', 'romp-kernel')).load_module()",
    "out = []",
    "for c in json.load(sys.stdin):",
    "    p = c['absPath']",
    "    out.append(km._file_comments_message(p, c['comments'], c['accepted'], c['rejected'], bool(c['tracked']), km._is_text_path(p)))",
    "json.dump(out, sys.stdout)",
  ].join("\n");
  const scratch = fs.mkdtempSync(path.join(os.tmpdir(), "romp-fc-parity-"));
  try {
    // the floors tests/conftest.py and tests/test_file_comments.py put under a kernel load: a hermetic state
    // root, a dead manager port, no browser open, no real CLI, no catalog fetch, no systemd scope
    const env: NodeJS.ProcessEnv = { ...process.env, XDG_STATE_HOME: scratch, ROMP_MANAGER_PORT: "1", ROMP_KERNEL_NO_OPEN: "1",
      ROMP_SERVE_TOKEN: "testtok", ROMP_CLAUDE_BIN: "/bin/false", ROMP_MODEL_CATALOG: "off", ROMP_CLI_SCOPE: "0" };
    delete env.ROMP_STATE_DIR;
    const r = spawnSync("python3", ["-c", script, REPO], { input: JSON.stringify(cases), encoding: "utf8", env, timeout: 60000, maxBuffer: 8 << 20 });
    assert.equal(r.status, 0, "the kernel loaded and built every message: " + (r.stderr || r.error));
    const kernelText: string[] = JSON.parse(r.stdout);
    assert.equal(kernelText.length, cases.length);
    cases.forEach((c, i) => assert.equal(buildSendMessage(c), kernelText[i], "case " + i + " (" + c.absPath + ", tracked " + c.tracked + ")"));
    // the cases still reach every branch — a guard on the list, not on the builders
    const all = kernelText.join("");
    for (const frag of ["I left 1 comment on", "I left 3 comments on", "I left 0 comments on", "I accepted 4 of your changes and rejected 1.",
      "I accepted 0 of your changes and rejected 2.", "track-edit.mjs --file " + ABS + " --thread", "edit the file normally",
      "regenerate the file with normal writes", "--file '/repo/notes-api/vault/Meeting notes.md' --thread", "--file '/repo/notes-api/vault/it'\"'\"'s here.md' --thread",
      "--file '/repo/notes-api/docs/<!- -romp-x-->/report.md' --thread", "<!- - romp-goal-id; 9 -->", "Comment  ():"]) {
      assert.ok(all.includes(frag), "the case list reaches: " + frag);
    }
  } finally {
    fs.rmSync(scratch, { recursive: true, force: true });
  }
});

test("the card model: one card per comment from store + hunks, oldest first, kinds and refs; no card model crosses the wire", () => {
  const cards = cardModel(status({ store: { v: 3, path: "docs/report.md", suggestions: [], comments: [passage, bound, replied, whole] }, hunks: [hunk] }).store, [hunk]);
  assert.deepEqual(cards.map((c) => c.kind), ["passage", "passage", "change", "file"]);
  assert.deepEqual(cards.map((c) => c.id), [replied.id, passage.id, bound.id, whole.id]);
  assert.equal(cards[0].replies.length, 2); assert.equal(cards[0].replies[0].authorId, SID);
  assert.equal(cards[1].ref, "shipping the cache in v1.2");
  assert.equal(cards[2].ref, "reduced → cut"); assert.equal(cards[2].hunk?.id, "h1");
  assert.equal(cards[3].ref, "this file"); assert.equal(cards[3].anchor, null);
  assert.deepEqual(cardModel(null, []), []);
  assert.doesNotMatch(SRC, /\.cards\b\s*[:=]/, "the panel derives cards from store + hunks in the reply, never a `cards` field");
  assert.match(SRC, /cardModel\(this\.status\.store, this\.status\.hunks \|\| \[\], this\.status\.log \|\| \[\]\)/, "…and the log, which remembers a decided change's texts");
});

test("Log rows: one line per comments-log entry, in the person's terms", () => {
  const name = (sid: string) => (sid === SID ? "api" : null);
  assert.equal(logRowText({ ts: "2026-09-06T08:00:00Z", kind: "send", author: "you", sid: SID, comments: [{ id: "a" }, { id: "b" }], accepted: 0, rejected: 0, queued: false }, name), "Sent 2 comments to api");
  assert.equal(logRowText({ ts: "2026-09-06T08:00:00Z", kind: "send", author: "you", sid: SID, comments: [{ id: "a" }], accepted: 0, rejected: 0, queued: true }, name), "Sent 1 comment to api (queued until the session wakes)");
  assert.equal(logRowText({ ts: "", kind: "send", author: "you", sid: SID, comments: [], accepted: 4, rejected: 1, queued: false }, name), "Sent 0 comments to api with 4 accepts and 1 reject");
  assert.equal(logRowText({ ts: "", kind: "send", author: "you", sid: "22222222-3333-4444-5555-666666666666", comments: [] }), "Sent 0 comments to 22222222", "an unknown sid: its first 8 characters");
  assert.equal(logRowText({ ts: "", kind: "accept", author: "you", ids: ["h1", "h2"] }), "Accepted 2 changes");
  assert.equal(logRowText({ ts: "", kind: "reject", author: "you", ids: ["h1"] }), "Rejected 1 change");
  assert.equal(logRowText({ ts: "", kind: "set-tracked", author: "you", on: true, entry: "docs/" }), "Track changes on for docs/");
  assert.equal(logRowText({ ts: "", kind: "set-tracked", author: "you", on: false, entry: "docs/report.md" }), "Track changes off for docs/report.md");
  assert.equal(logRowText({ ts: "", kind: "edit", author: "you", summary: { bytesBefore: 1200, bytesAfter: 1180 } }), "Edited the file directly (1200 → 1180 bytes)");
  assert.equal(logRowText({ ts: "", kind: "edit", author: "you" }), "Edited the file directly");
  assert.equal(logRowText({ ts: "", kind: "something-new", author: "you" }), "something-new", "an unknown kind still shows, never drops");
});

test("the poll's state machine: baseline from the reply, 404 = absent, 413/415 stop, and STRING mtime comparison", () => {
  const b = pollBaseline(status({ storeMtimeNs: null, configMtimeNs: null }));
  assert.deepEqual(b, { file: "1757145600000000001", store: ABSENT, config: ABSENT }, "a missing sidecar/config is the value 'absent'");
  assert.deepEqual(headVerdict(200, "1757145600000000009"), { kind: "value", value: "1757145600000000009" });
  assert.deepEqual(headVerdict(404, null), { kind: "value", value: ABSENT }, "absent → present is a transition like any other");
  assert.deepEqual(headVerdict(413, null), { kind: "stop", status: 413 });
  assert.deepEqual(headVerdict(415, null), { kind: "stop", status: 415 });
  assert.deepEqual(headVerdict(500, null), { kind: "unknown", status: 500 });
  assert.deepEqual(headVerdict(200, null), { kind: "unknown", status: 200 }, "an old kernel mirroring no mtime is unknown, not a change");
  // ~1.7e18 exceeds JS's safe integers: as numbers these two writes would compare EQUAL
  assert.equal(Number("1757145600000000001") === Number("1757145600000000002"), true, "the trap the string rule avoids");
  assert.equal(mtimeMoved("1757145600000000001", "1757145600000000002"), true);
  assert.equal(mtimeMoved("1757145600000000001", "1757145600000000001"), false);
  assert.equal(mtimeMoved(ABSENT, "1757145600000000001"), true);
  assert.match(MODEL, /return baseline !== seen;/, "the comparison is string inequality");
  assert.doesNotMatch(SRC + MODEL, /Number\([^)]*[mM]time|parseInt\([^)]*[mM]time|BigInt\(/, "no numeric coercion of an mtime anywhere");
});

test("the poll's HEAD targets: the file, the sidecar the kernel named, config.json beside the root — never a client-computed sidecar path", () => {
  const t = pollTargets(status(), ABS);
  assert.deepEqual(t, { file: ABS, store: "/repo/notes-api/.trackchanges/docs%2Freport.md.json", config: "/repo/notes-api/.trackchanges/config.json" });
  assert.deepEqual(pollTargets(status({ root: null, storePath: null }), ABS), { file: ABS, store: null, config: null }, "no project root: the file alone");
  assert.deepEqual(pollTargets(status({ root: "/repo/notes-api/" }), ABS).config, "/repo/notes-api/.trackchanges/config.json");
  assert.doesNotMatch(SRC + MODEL, /encodeURIComponent\([^)]*\)\s*\+\s*["'`]\.json/, "the sidecar's name is the kernel's to compute");
  assert.match(MODEL, /store: s\.storePath \|\| null/);
  assert.match(SRC, /fetch\(fileUrl\(target, this\.ctx\.sid\), \{ method: "HEAD", cache: "no-store" \}\)/, "HEAD over the same host-routed /file route the bytes use");
  assert.match(SRC, /headVerdict\(r\.status, r\.headers\.get\("X-Romp-Mtime-Ns"\)\)/);
  assert.match(SRC, /const POLL_MS = 2500;/);
  assert.match(SRC, /const paneHidden = \(\): boolean => document\.hidden \|\| window\.innerWidth === 0 \|\| window\.innerHeight === 0;/,
    "a shell-hidden pane has a zero viewport — the sessions pane's gate");
  assert.match(SRC, /if \(paneHidden\(\)\) \{ this\.tickSkipped = true; return; \}/);
  assert.match(SRC, /document\.addEventListener\("visibilitychange", this\.catchUp\);\n\s*window\.addEventListener\("resize", this\.catchUp\);/);
  assert.match(SRC, /this\.base = pollBaseline\(s\);/, "every fileCommentsResult re-baselines the poll — the person's own writes never fire it");
  assert.match(SRC, /if \(fileMoved\) this\.ctx\.reload\(\);/);
  assert.match(SRC, /this\.stopped\.add\(target\);/);
});

test("the Edit refusal while changes are pending (Slice 2 wording: accept or reject them first), and the small helpers", () => {
  assert.equal(editBlockedReason([]), null);
  assert.equal(editBlockedReason([hunk]), "1 change is pending in this file, so Edit is off here: a direct edit would move it. Accept or reject the change first; the session's own track-edit still works.");
  assert.equal(editBlockedReason([hunk, { ...hunk, id: "h2" }, { ...hunk, id: "h3" }]), "3 changes are pending in this file, so Edit is off here: a direct edit would move them. Accept or reject the 3 changes first; the session's own track-edit still works.");
  assert.doesNotMatch(editBlockedReason([hunk])!, /next update|next slice/, "the Slice 1 wording is gone");
  assert.match(SRC, /this\.ctx\.setEditBlocked\(editBlockedReason\(s\.hunks \|\| \[\]\)\);/, "set from every status reply");
  assert.equal(lineStartOffset("ab\ncd\nef", 0), 0);
  assert.equal(lineStartOffset("ab\ncd\nef", 1), 3);
  assert.equal(lineStartOffset("ab\ncd\nef", 2), 6);
  assert.equal(lineStartOffset("ab\ncd\nef", 9), 8, "past the last line: the end");
  assert.equal(folderOf(ABS), "/repo/notes-api/docs/");
  assert.equal(folderOf("report.md"), "/");
});

// ── the DOM stand-in (the GitHub link test's idiom): the seam's consent helper, and the action's mount ──
class El {
  id = ""; title = ""; hidden = false; type = ""; disabled = false; placeholder = ""; value = ""; checked = false;
  href = ""; target = ""; rel = "";
  dataset: Record<string, string> = {};
  style: Record<string, string> = {};
  childNodes: Array<El | string> = [];
  parentElement: El | null = null;
  private attrs = new Map<string, string>();
  private classes = new Set<string>();
  classList = {
    add: (...c: string[]) => { for (const x of c) this.classes.add(x); },
    remove: (...c: string[]) => { for (const x of c) this.classes.delete(x); },
    toggle: (c: string, on?: boolean) => { if (on === undefined ? !this.classes.has(c) : on) this.classes.add(c); else this.classes.delete(c); },
    contains: (c: string) => this.classes.has(c),
  };
  constructor(public tagName: string) {}
  get className(): string { return [...this.classes].join(" "); }
  set className(v: string) { this.classes = new Set(v.split(/\s+/).filter(Boolean)); }
  get textContent(): string { return this.childNodes.map((c) => (typeof c === "string" ? c : c.textContent)).join(""); }
  set textContent(v: string) { this.childNodes = v === "" ? [] : [v]; }
  appendChild<T extends El>(c: T): T { this.childNodes.push(c); c.parentElement = this; return c; }
  replaceChildren(...c: Array<El | string>): void { this.childNodes = c; for (const x of c) if (x instanceof El) x.parentElement = this; }
  remove(): void { /* inert */ }
  querySelector(): null { return null; }
  querySelectorAll(): El[] { return []; }
  setAttribute(k: string, v: string): void { this.attrs.set(k, v); }
  getAttribute(k: string): string | null { return this.attrs.get(k) ?? null; }
  addEventListener(): void {}
  removeEventListener(): void {}
  focus(): void {}
  contains(): boolean { return false; }
}
const win: any = new EventTarget();
win.parent = win;
win.innerWidth = 1200; win.innerHeight = 800;
(globalThis as any).window = win;
(globalThis as any).document = {
  createElement: (tag: string) => new El(tag),
  createTextNode: (s: string) => s,
  getElementById: () => null,
  addEventListener: () => {},
  removeEventListener: () => {},
  body: new El("body"),
  hidden: false,
};
const store = new Map<string, string>();
(globalThis as any).localStorage = {
  getItem: (k: string) => (store.has(k) ? store.get(k)! : null),
  setItem: (k: string, v: string) => { store.set(k, String(v)); },
  removeItem: (k: string) => { store.delete(k); },
};
const tick = () => new Promise<void>((r) => setImmediate(r));

test("ensureEditingAllowed — first consent: the kernel's live flag, else the one popup; only a yes posts the opt-in", async () => {
  const fv = await import("./file-view");
  const posted: any[] = [];
  fv.initFileView((m) => posted.push(m));
  let flag = true;
  (globalThis as any).fetch = async () => ({ json: async () => ({ fileEditing: flag }) });
  const confirms: string[] = [];
  let answer = false;
  win.confirm = (t: string) => { confirms.push(t); return answer; };
  assert.equal(await fv.ensureEditingAllowed(null), true, "the flag is on: no popup");
  assert.equal(confirms.length, 0); assert.equal(posted.length, 0);
  flag = false; answer = false;
  assert.equal(await fv.ensureEditingAllowed(null), false, "a no changes nothing");
  assert.equal(confirms.length, 1);
  assert.match(confirms[0], /^Allow editing files from the dashboard\?\n\n/);
  assert.match(confirms[0], /Saves and comments write straight to disk on the file's machine/, "the copy stays true for comments (decision 5)");
  assert.match(confirms[0], /your comments reach it when you send them/, "comments are not traced at once, the send is the notification");
  assert.equal(posted.length, 0);
  answer = true;
  assert.equal(await fv.ensureEditingAllowed(null), true);
  assert.equal(posted.length, 1);
  assert.equal(posted[0].type, "setFileEditing"); assert.equal(posted[0].enabled, true);
  assert.equal(typeof posted[0].gt, "number", "gesture-stamped: federation orders applies by it");
  // /version unreachable: the popup still asks (the kernel-side gate refuses regardless)
  (globalThis as any).fetch = async () => { throw new Error("down"); };
  confirms.length = 0;
  assert.equal(await fv.ensureEditingAllowed(null), true);
  assert.equal(confirms.length, 1);
});

test("ensureEditingAllowed — re-consent on the owning kernel's gate refusal, naming the machine; other refusals re-offer nothing", async () => {
  const fv = await import("./file-view");
  const posted: any[] = [];
  fv.initFileView((m) => posted.push(m));
  (globalThis as any).fetch = async () => { throw new Error("must not be read on the refusal path"); };
  const confirms: string[] = [];
  let answer = true;
  win.confirm = (t: string) => { confirms.push(t); return answer; };
  const gate = "cannot write the comments for ~/notes-api/docs/report.md: dashboard file editing is off on this machine";
  assert.equal(await fv.ensureEditingAllowed("TESTHOST:" + SID, gate), true);
  assert.match(confirms[0], /^Editing is off on “TESTHOST” — it may have connected after you allowed editing here\.\n\nAllow editing files from the dashboard\?/);
  assert.equal(posted.length, 1); assert.equal(posted[0].type, "setFileEditing");
  assert.equal(await fv.ensureEditingAllowed(null, gate), true);
  assert.match(confirms[1], /^Editing is off on this machine\.\n\n/);
  answer = false;
  assert.equal(await fv.ensureEditingAllowed(SID, gate), false, "a no: the caller shows the refusal, nothing is posted");
  assert.equal(posted.length, 2);
  assert.equal(await fv.ensureEditingAllowed(SID, "~/notes-api/docs/report.md changed on disk since you opened it"), false, "a conflict is not the gate");
  assert.equal(confirms.length, 3, "…and asks nothing");
});

function stubCtx(posted: any[], over: Partial<FileViewActionCtx> = {}): FileViewActionCtx {
  const noop = () => { /* inert */ };
  const body = new El("div") as unknown as HTMLElement;
  return {
    path: ABS, sid: SID, todoId: null,
    body: () => body, mode: () => "rendered", text: () => null, mtimeNs: () => "1757145600000000001", media: () => null, mediaElement: () => null, renderedImages: () => [], pdfPages: () => [],
    identity: () => ({ name: "api", color: null }),
    onRendered: noop, onSelection: noop, onSaved: noop, onClose: noop,
    post: (m) => posted.push(m), ensureEditingAllowed: async () => true, setEditBlocked: noop, aside: noop, setMode: noop,
    scrollToOffset: noop, reload: noop, ...over,
  };
}

test("the Comments action mounts hidden, asks `status` with sid, and is revealed by the answer with the glance label", async () => {
  const fc = await import("./file-comments");
  const posted: any[] = [];
  const blocked: Array<string | null> = [];
  const unit = fc.fileCommentsAction.mount(stubCtx(posted, { setEditBlocked: (r) => { blocked.push(r); } })) as unknown as El;
  assert.equal(unit.className, "fileview-fc");
  assert.equal(unit.hidden, true, "hidden until the kernel answers");
  const b = unit.childNodes[0] as El;
  assert.equal(b.tagName, "button"); assert.equal(b.textContent, "Comments"); assert.equal(b.type, "button");
  assert.equal(posted.length, 1);
  const ask = posted[0];
  assert.deepEqual(ask, { type: "fileComments", reqId: ask.reqId, sid: SID, path: ABS, verb: "status" }, "the disk op carries sid (federation routes by it)");
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId: ask.reqId, ...status({ hunks: [hunk] }) } }));
  await tick();
  assert.equal(unit.hidden, false, "the answer reveals the action");
  assert.equal(b.textContent, "Comments · 3 · 1 change");
  assert.deepEqual(blocked, [editBlockedReason([hunk])], "pending changes block Edit through the seam");
});

test("a `no-node` refusal keeps the action away for good; a stale reqId lands nowhere", async () => {
  const fc = await import("./file-comments");
  const posted: any[] = [];
  const unit = fc.fileCommentsAction.mount(stubCtx(posted)) as unknown as El;
  const ask = posted[posted.length - 1];
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId: ask.reqId - 1, ...status() } }));
  await tick();
  assert.equal(unit.hidden, true, "another open's reply is not this one's answer");
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsFailed", reqId: ask.reqId, verb: "status", code: "no-node", error: "node was not found on this kernel's PATH" } }));
  await tick();
  assert.equal(unit.hidden, true, "no node on the owning kernel: the action never appears (the gear's row says why)");
});

test("rawTarget's fallbacks: a rawRange the source no longer holds gives way to the selection, an empty selection targets nothing, a passage gone from the block is still found earlier, and an absent one leaves the mapper's slice", async () => {
  const { rawTarget } = await import("./file-comments");
  const src = "Latency: p95 in prose.\n\n| Route | p95 |\n|---|---|\n| /a | 1 |\n";
  const table = src.indexOf("| Route");
  const inTable = { start: src.indexOf("p95", table), end: src.indexOf("p95", table) + 3 };
  const base = { ok: false as const, reason: "This selection touches a table; comment on it from the Raw view.", blockStartLine: 2, blockStartOffset: table, rawHasQuote: true };
  // a rawRange found over a longer text (the file shrank under a reload): out of bounds, so the trimmed selection is
  // searched instead — from the block, so the table's cell wins over the prose above it
  assert.deepEqual(rawTarget(src, { ...base, rawRange: { start: 9, end: src.length + 40 }, selText: " p95 " }), inTable);
  assert.deepEqual(rawTarget(src, { ...base, rawRange: { start: 12, end: 9 }, selText: "p95" }), inTable, "an inverted range is no range");
  assert.deepEqual(rawTarget(src, { ...base, rawRange: { start: -1, end: 3 }, selText: "p95" }), inTable, "nor is one before the start");
  // the selection was whitespace and the mapper kept no slice: nothing to search for — null, the button only scrolls
  assert.equal(rawTarget(src, { ...base, selText: "  \n" }), null);
  // the words are not in the refused block after all (the block came out of sync) but do occur earlier: that
  // occurrence is targeted rather than none — the person still lands on the text they selected
  const prose = { start: src.indexOf("p95"), end: src.indexOf("p95") + 3 };
  assert.deepEqual(rawTarget(src, { ...base, blockStartOffset: src.indexOf("|---|"), selText: "p95 in prose" }), { start: 9, end: 9 + "p95 in prose".length });
  assert.deepEqual(rawTarget(src, { ...base, blockStartOffset: undefined, selText: "p95" }), prose, "no block offset: searched from the top");
  assert.deepEqual(rawTarget(src, { ...base, blockStartOffset: -5, selText: "p95" }), prose, "a negative one clamps to the top");
  // the DOM spelling is nowhere in the source and the mapper kept no slice: null; with a slice, the slice stands
  assert.equal(rawTarget(src, { ...base, selText: "p99" }), null);
  const rr = { start: inTable.start, end: inTable.end };
  const got = rawTarget(src, { ...base, rawRange: rr, selText: "p99" });
  assert.deepEqual(got, inTable, "the mapper's slice, searched by its own source spelling");
  assert.equal(src.slice(got!.start, got!.end), "p95", "…and the range's quote is the source's text");
});

// ── what the stand-in cannot show, pinned at source ────────────────────────────────────────────────

test("the registry entry: exported by file-comments.ts, registered in file-view.ts, with no runtime import cycle", () => {
  assert.match(SRC, /export const fileCommentsAction: FileViewAction = \{\n  id: "file-comments",/);
  assert.match(VIEW, /import \{ fileCommentsAction \} from "\.\/file-comments";/);
  assert.match(VIEW, /registerFileViewAction\(githubLinkAction\);\n(?:\/\/[^\n]*\n)*registerFileViewAction\(fileCommentsAction\);/, "second entry, after the GitHub link");
  assert.doesNotMatch(SRC.replace(/^\s*\/\/.*$/gm, ""), /registerFileViewAction/, "registered by the viewer, not at this module's top level");
  const fromView = SRC.match(/^import .* from "\.\/file-view";$/gm) || [];
  assert.deepEqual(fromView, ['import type { FileViewAction, FileViewActionCtx, FileViewIdentity } from "./file-view";'], "types only");
  // contract C4: the anchor-map API, imported by name
  assert.match(SRC, /import \{ mapRawSelection, mapRenderedSelection, makeAnchor, locateComment, paintRaw, paintRendered, rawOffsetToLine \} from "\.\/anchor-map";/);
  assert.doesNotMatch(SRC, /vendor\/track-changents/, "the engine is reached through anchor-map, never twice");
});

test("both ops carry sid and a client-minted reqId; replies match by reqId; a warn or a socket drop fails what is outstanding", () => {
  assert.match(SRC, /const msg: Record<string, unknown> = \{ type: "fileComments", reqId, sid: ctx\.sid \|\| undefined, path: ctx\.path, verb \};/);
  assert.match(SRC, /this\.ctx\.post\(\{ \.\.\.msg, type: "fileCommentsSend", reqId \}\);/);
  assert.match(SRC, /sid: this\.ctx\.sid, path: this\.ctx\.path, tracked, comments: parts\.comments,\n\s*accepted: counts\.accepted, rejected: counts\.rejected, watermark: parts\.watermark,/,
    "the counts are sendCounts' — the log's unsent decisions plus the pending changes the confirm's checkbox accepts (Slice 2)");
  assert.match(SRC, /if \(answerTodo\) msg\.todoId = this\.ctx\.todoId;/);
  assert.match(SRC, /const answerTodo = !!this\.ctx\.todoId && this\.sendOpts\.todo && !this\.todoAnswered;/, "one send answers the todo; later sends carry none");
  for (const t of ["fileCommentsResult", "fileCommentsFailed", "fileCommentsSent", "fileCommentsSendFailed"]) assert.ok(SRC.includes('m.type === "' + t + '"'), t);
  assert.match(SRC, /const p = this\.pending\.get\(Number\(m\.reqId\)\);\n\s*if \(!p\) return;/);
  assert.match(SRC, /else if \(m\.type === "warn"\) live\.failAll\(/, "a federation warn during an outstanding request is its failure");
  assert.match(SRC, /window\.addEventListener\("romp:wsdown", \(\) => \{ if \(live\) live\.failAll\(/);
  assert.doesNotMatch(SRC, /m\.sid === /, "never matched by sid: a remote reply's sid comes back host-prefixed");
});

test("the send sequence: build from the current status, set-tracked when asked, then send with the post-toggle verdict; a refusal aborts before the send", () => {
  const send = SRC.split("async doSend(): Promise<void> {")[1].split("\n  }\n")[0];
  const at = (s: string) => { const i = send.indexOf(s); assert.ok(i >= 0, s); return i; };
  assert.ok(at("const parts: SendParts = sendParts(s);") < at('await this.mutate("set-tracked", { on: true, scope: "file" }, "send")'), "the message is built first");
  assert.ok(at("if (!r) return;") < at("await this.sendOnce(msg, false)"), "a refused toggle aborts before the send");
  assert.ok(at("tracked = !!r.trackedBy;") < at("await this.sendOnce(msg, false)"), "tracked is the post-toggle verdict");
  assert.match(send, /this\.sentNote = reply\.queued \? "Queued for " \+ who : "Sent to " \+ who \+ " at " \+ clock\(Date\.now\(\)\);/);
  assert.match(send, /if \(reply\.warning\) this\.errors\.set\("send", \{ text: reply\.warning, reload: false, warn: true \}\);/, "sent but nothing stamped: the kernel's own reason shows");
  assert.match(SRC, /warning: \[str\(m\.warning\), str\(m\.logWarning\)\]\.filter\(Boolean\)\.join\(" "\) \|\| undefined/,
    "a send whose comments-log append failed is loud too: the kernel's logWarning rides the same warn row");
  assert.match(SRC, /btn\(this\.sending \? "Sending…" : "Send to session" \+ \(n \? " \(" \+ n \+ "\)" : ""\), "fcsend"\)/, "count = unsent; relabeled while sending");
  assert.match(SRC, /const stale = !!this\.statusRefusal;\n\s*b\.disabled = !s \|\| !n \|\| this\.sending \|\| !this\.ctx\.sid \|\| stale;/,
    "Send stands down while a status refusal stands: the unsent list was derived from a disk the kernel can no longer read");
  assert.match(send, /if \(!s \|\| this\.statusRefusal \|\| this\.sending \|\| !this\.ctx\.sid\) return;/, "and doSend refuses the same way, a click never sends over a stale status");
  assert.match(SRC, /if \(this\.ctx\.todoId && !this\.todoAnswered\) opts\.appendChild\(this\.opt\("todo", "answer the todo this file was opened from"\)\);/);
  assert.match(SRC, /if \(!s\.trackedBy\) opts\.appendChild\(this\.opt\("track", "turn on tracking so the session's edits come back as changes"\)\);/);
  assert.match(SRC, /sendOpts = \{ todo: true, track: true, accept: true \};/, "all three checked by default (decision 8; the third is Slice 2's accept-pending box)");
  assert.match(SRC, /const abs = this\.filePath\(\);\n\s*if \(abs === null\)[^\n]*\n\s*else cf\.appendChild\(el\("pre", "fc-msg", buildSendMessage\(\{ absPath: abs, comments: parts\.comments, accepted: counts\.accepted, rejected: counts\.rejected, tracked, media \}\)\)\);/,
    "the preview is the same builder the tests pin against the kernel's literal, fed the path the kernel will name (filePath), never a relative or ~ spelling, and the send's own A and R");
  // the send's editing-off refusal takes the branch every mutating verb takes (mutateOnce): the kernel refuses
  // a send while file editing is off because the send's log entry is a disk write, and the refusal text carries
  // the phrase the consent helper matches — so the panel re-offers the consent and sends once more on yes
  assert.match(send, /const reply = await this\.sendOnce\(msg, false\);/, "doSend sends through the retrying helper");
  const once = SRC.split("private async sendOnce(")[1].split("\n  }\n")[0];
  assert.match(once, /try \{ return await this\.requestSend\(msg\); \}/);
  assert.match(once, /if \(!retried && e\.code === "editing-off" && await this\.ctx\.ensureEditingAllowed\(e\.error\)\) return this\.sendOnce\(msg, true\);/, "consent (naming the machine), then ONE retry");
  assert.match(once, /throw err;/, "a no, or a second refusal, reaches doSend's error row verbatim");
});

test("every mutating verb: consent first, a fence from the current status, one retry on editing-off (re-consent) or a moved fence (fresh status), then the refusal verbatim with Reload", () => {
  const mut = SRC.split("async mutate(verb: string, args: Record<string, unknown>, slot: string): Promise<Status | null> {")[1].split("\n  }\n")[0];
  assert.match(mut, /if \(!\(await this\.ctx\.ensureEditingAllowed\(\)\)\)/, "the first-consent path, per click (never cached)");
  const once = SRC.split("private async mutateOnce(")[1].split("\n  }\n")[0];
  assert.match(once, /const fence: Record<string, string> = \{ storeMtimeNs: s && s\.storeMtimeNs !== null \? s\.storeMtimeNs : "", configMtimeNs: s && s\.configMtimeNs !== null \? s\.configMtimeNs : "" \};/,
    '"" means the file must not exist yet — two browsers cannot both create it');
  assert.match(once, /if \(FILE_VERBS\.has\(verb\)\) fence\.fileMtimeNs = s \? s\.fileMtimeNs : "";/, "the file-writing verbs (reject, reject-all) also fence on the file's mtime (Slice 2)");
  assert.match(once, /if \(!retried && e\.code === "editing-off"\) \{\n\s*if \(await this\.ctx\.ensureEditingAllowed\(e\.error\)\) return this\.mutateOnce\(verb, args, slot, true\);/);
  assert.match(once, /\} else if \(!retried && MOVED\.has\(e\.code\)\) \{\n\s*await this\.refresh\(\);\n\s*if \(e\.code === "file-moved"\) this\.ctx\.reload\(\);[^\n]*\n\s*return this\.mutateOnce\(verb, args, slot, true\);/,
    "a moved fence: fresh status (and the file's bytes when the file moved), then one retry");
  assert.match(once, /this\.errors\.set\(slot, \{ text: e\.error, reload: MOVED\.has\(e\.code\) \|\| e\.code === FIGURE_CHANGED \}\);/, "a second refusal shows verbatim; moved fences offer Reload, and so does a figure whose bytes changed (Slice 3: never retried)");
  assert.match(once, /const fh = FIGURE_VERBS\.has\(verb\) && args\.target \? figureFenceHash\(s, args\.target as Target\) : null;\n\s*if \(fh\) fence\.figureHash = fh;/, "a write about a figure also fences on its bytes, when the status holds a hash for it (Slice 3)");
  assert.match(SRC, /const MOVED = new Set\(\["store-moved", "file-moved", "config-moved"\]\);/);
  for (const verb of ['"set-tracked", { on: true, scope: "file" }', '"set-tracked", { on: true, scope: "folder" }', '"set-tracked", { on: false, scope: "folder" }',
    '"set-tracked", { on: false, scope: "file" }', '"reply", { commentId: c.commentId, note }', '"comment", args', '"resolve", { commentId: x.dataset.id!, on: x.dataset.on === "1" }']) {
    assert.ok(SRC.includes("this.mutate(" + verb), verb + " goes through mutate()");
  }
  assert.match(SRC, /args\.anchor = makeAnchor\(src, c\.range\); args\.hintOffset = c\.range\.start;/, "a passage comment carries the engine's anchor and the start offset");
  assert.match(SRC, /if \(r\) this\.closeComposer\(\);\s*\/\/ a refusal keeps the note where it was typed/);
});

test("click-safety: ONE delegate() root for every control (the body row, which also holds the highlights), keyed expand state, flash on the direct buttons", () => {
  assert.equal((SRC.match(/\bdelegate\(/g) || []).length, 1, "one delegate root");
  assert.match(SRC, /const row = ctx\.body\(\)\.parentElement \|\| ctx\.body\(\);\n\s*delegate\(row, \{/);
  assert.doesNotMatch(SRC.replace(/^\s*\/\/.*$/gm, ""), /\.onclick\s*=/, "no per-node handlers on rebuilt nodes");
  assert.match(SRC, /openCards = new Set<string>\(\);/);
  assert.match(SRC, /const isOpen = this\.openCards\.has\(c\.id\);/);
  assert.match(SRC, /fccard: \(x\) => \{ const id = x\.dataset\.id!; if \(this\.openCards\.has\(id\)\) this\.openCards\.delete\(id\); else this\.openCards\.add\(id\); this\.render\(\); \}/);
  assert.match(SRC, /flash\(this\.float\);/); assert.match(SRC, /flash\(this\.button\);/);
  // the composer's input is never rebuilt, and the aside's own children are placed once per open, so a
  // poll re-render swaps section CHILDREN only and cannot drop the input's focus mid-word
  assert.match(SRC, /if \(!box\.contains\(this\.input\)\) box\.replaceChildren\(ref, this\.input, acts, err\);/);
  assert.match(SRC, /if \(!this\.root\.contains\(head\)\) this\.root\.replaceChildren\(head, this\.composerBox, cards, send, log\);/);
  assert.equal((SRC.match(/this\.root\.replaceChildren\(/g) || []).length, 1, "the aside's children are never rebuilt elsewhere");
  // the highlights carry the delegate's action and the comment id; painted through anchor-map, states located / context / detached
  assert.match(SRC, /paintRendered\(root, src, loc\.range, cls, \{ act: "fcopen", id: card\.id \}\)/);
  assert.match(SRC, /paintRaw\(root, src, loc\.range, cls, \{ act: "fcopen", id: card\.id \}\)/);
  assert.match(SRC, /const cls = "fc-hl" \+ \(loc\.state === "context" \? " fc-hl-context" : ""\);/);
  assert.match(SRC, /if \(c\.anchor && loc && loc\.range && !loc\.painted\) \{\n\s*const rv = btn\("Reveal", "fcreveal"\);/, "an unpainted comment's card never dead-ends");
  assert.match(SRC, /the wire: ONE window listener for the module/);
  // waits show the romp loader
  assert.match(SRC, /const w = el\("div", "fileview-load fc-load"\);\n\s*w\.innerHTML = '<img src="\/media\/romp-swirl-glyph\.svg" alt=""><span>romp<\/span>'/);
});

test("the floating Comment button rides the seam's selection hook — before the composer gate — and the mapping refusal keeps the note and offers Raw", () => {
  assert.match(SRC, /ctx\.onSelection\(\(sel\) => this\.onSelection\(sel\)\);/);
  assert.match(SRC, /if \(!this\.open \|\| this\.ctx\.mode\(\) === "media" \|\| !sel\.rangeCount\) return;/, "with the panel open, on a text view");
  assert.match(SRC, /for \(const ev of \["mousedown", "touchstart"\]\) this\.float\.addEventListener\(ev, \(e\) => e\.preventDefault\(\)\);/, "the click must not collapse the selection it is about");
  assert.match(SRC, /const res = this\.ctx\.mode\(\) === "rendered" \? mapRenderedSelection\(sel, root, src\) : mapRawSelection\(sel, root, src\);/);
  assert.match(SRC, /else this\.composer = \{ kind: "comment", range: null, quote: null, refusal: \{ \.\.\.res, selText \} \};/, "a refusal opens the composer anyway, note intact");
  const raw = SRC.split("switchToRaw(): void {")[1].split("\n  }\n")[0];
  assert.match(raw, /this\.ctx\.setMode\("raw"\);/);
  // the passage is re-targeted through rawTarget — the refused block's own occurrence, not the file's first — and
  // the composer then holds a placed range: refusal gone, the view scrolled to it, the presel mark on it
  assert.match(raw, /const range = rawTarget\(src, r\);\n\s*if \(range\) \{\n\s*c\.range = range; c\.quote = src\.slice\(range\.start, range\.end\); c\.text = src; c\.refusal = null;/);
  assert.match(raw, /this\.ctx\.scrollToOffset\(range\.start\);\n\s*this\.repaintPresel\(\);/);
  assert.doesNotMatch(raw, /\.indexOf\(/, "the switch does no lookup of its own — the search and its fallbacks live in rawTarget");
  assert.match(raw, /if \(typeof r\.blockStartLine === "number"\) this\.ctx\.scrollToOffset\(lineStartOffset\(src, r\.blockStartLine\)\);/, "else scrolled to the block's first line");
  assert.match(SRC, /else if \(e\.key === "Escape"\) \{ e\.preventDefault\(\); e\.stopPropagation\(\); this\.closeComposer\(\); \}/, "Escape in the composer never closes the viewer");
});

test("the seam in file-view.ts: every member exists, hooks fire where they should, and both exits drain the close hooks", () => {
  for (const m of ["body(): HTMLElement;", 'mode(): "raw" | "rendered" | "media";', "text(): string | null;", "mtimeNs(): string;",
    'media(): "image" | "pdf" | "svg" | null;', "mediaElement(): HTMLImageElement | HTMLElement | null;", "renderedImages(): HTMLImageElement[];",
    "pdfPages(): HTMLElement[];", "identity(): FileViewIdentity | null;", "onRendered(cb: () => void): void;",
    "onSelection(cb: (sel: Selection) => void): void;", "onSaved(cb: (info: { mtimeNs: string; logged: boolean }) => void): void;",
    "onClose(cb: () => void): void;", "post(m: Record<string, unknown>): void;", "ensureEditingAllowed(refusal?: string): Promise<boolean>;",
    "setEditBlocked(reason: string | null): void;", "aside(el: HTMLElement | null): void;", 'setMode(mode: "raw" | "rendered"): void;',
    "scrollToOffset(n: number): void;", "reload(): void;"]) {
    assert.ok(VIEW.includes(m), "FileViewActionCtx has " + m);
  }
  assert.match(VIEW, /export async function ensureEditingAllowed\(sid: string \| null \| undefined, refusal\?: string\): Promise<boolean> \{/);
  assert.match(VIEW, /ensureEditingAllowed: \(refusal\) => ensureEditingAllowed\(sid, refusal\),/);
  // the aside: mounted beside the body in the body row; the viewer owns the two-column CSS
  assert.match(VIEW, /const main = el\("div", "fileview-main"\);\n\s*const body = el\("div", "fileview-body"\);/);
  assert.match(VIEW, /main\.appendChild\(body\);/);
  assert.match(VIEW, /box\.appendChild\(bar\); box\.appendChild\(main\);/);
  assert.match(VIEW, /if \(node\) \{ node\.classList\.add\("fileview-aside"\); main\.appendChild\(node\); \}/);
  // hooks: every text paint, the selection before the composer gate, the save ack with `logged`, both exits
  // the SVG Source view and every text paint fire onRendered; the media body's own call (contract E4, so the region
  // overlays paint after the picture loads) is a third, so the count is a floor and the two text sites are pinned by shape
  assert.ok((VIEW.match(/fireRendered\(\);/g) || []).length >= 2, "the SVG Source view and the text views both fire onRendered");
  assert.match(VIEW, /body\.replaceChildren\(codeBlock\(svgText, path, true\)\);[^\n]*\n\s*fireRendered\(\);/, "the SVG Source view fires it");
  assert.match(VIEW, /body\.replaceChildren\(rendered \? mdBlock\(text, path, sid\) : codeBlock\(text, path, true\)\);[^\n]*\n\s*fireRendered\(\);/, "every text paint fires it");
  assert.match(VIEW, /for \(const cb of savedHooks\) \{ try \{ cb\(\{ mtimeNs: mtNs, logged \}\); \}/);
  assert.equal((VIEW.match(/runCloseHooks\(\);/g) || []).length, 2, "closeFileView AND the replace path");
  const closeFn = VIEW.split("export function closeFileView")[1].split("/** Show `path`")[0];
  assert.match(closeFn, /dropMediaUrl\(\);[^\n]*\n\s*runCloseHooks\(\);[^\n]*\n\s*wrap\.remove\(\);/, "hooks drain before the element goes");
  // Edit refuses in words while blocked — the button stays a button so the reason reaches touch users
  assert.match(VIEW, /if \(editBlocked\) \{ noteBar\(editBlocked\); return; \}/);
  assert.match(VIEW, /editBtn\.title = reason \|\| "Edit this file in place";/);
  // reload re-runs the fetch pipeline, never in edit mode; setMode is markdown-only
  assert.match(VIEW, /reload: \(\) => \{ if \(!editing\) fetchFile\(\); \},/);
  assert.match(VIEW, /setMode: \(mode\) => \{ if \(!isMd \|\| editing\) return; fmt\.md = mode; saveFmt\(fmt\); renderBody\(\); \},/);
  assert.match(VIEW, /const line = \(src\.slice\(0, Math\.max\(0, n\)\)\.match\(\/\\n\/g\) \|\| \[\]\)\.length;/, "one .fv-cl per logical line");
});

test("the sheets: the panel block is byte-equal in styles.css and feed.css, tokens only, sizes from the ladder", () => {
  const block = (css: string) => {
    const a = css.indexOf("/* ── file comments panel (plans/file-review.md Slice 1; file-comments.ts)");
    const b = css.indexOf("/* ── end file comments panel ── */");
    assert.ok(a >= 0 && b > a, "the block and its end marker");
    return css.slice(a, b);
  };
  const chat = block(CHAT_CSS);
  assert.equal(chat, block(FEED_CSS), "the feed page loads only feed.css — the viewer's aside dresses the same there");
  const body = chat.replace(/\/\*[\s\S]*?\*\//g, "");
  assert.doesNotMatch(body, /#[0-9a-fA-F]{3,8}\b/, "no bare hex: colours through tokens");
  assert.doesNotMatch(body, /rgba?\(/, "no bare rgba either — --accent-wash, --overlay-05/10 and color-mix over tokens");
  assert.doesNotMatch(body, /border-radius: 999px/, "pills through --radius-pill");
  for (const m of body.match(/font-size: (0\.\d+em)/g) || []) assert.ok(["0.66em", "0.72em", "0.82em", "0.86em"].includes(m.slice(11)), m + " is on the ladder");
  // the Log row carries no size of its own: its time is the SAME .fc-time a card head wears, and a 0.72em time inside a
  // 0.86em row would compound to 0.62em (ui/CLAUDE.md, font sizes) — the body size sits on the text span beside it.
  // The byte-equal check above holds the feed page to this too.
  assert.match(body, /\n\.fc-log-row \{ display: flex; gap: 8px; align-items: baseline; \}\n\.fc-log-row > :not\(\.fc-time\) \{ font-size: 0\.86em; \}\n/);
  assert.match(body, /\.fc-time \{[^}]*font-size: 0\.72em;/, "the one time size, card heads and Log rows alike");
  assert.match(body, /\.fileview-main \{ flex: 1 1 auto; min-height: 0; display: flex; container-type: inline-size; \}/);
  assert.match(body, /@container \(max-width: 680px\) \{\n\s*\.fileview-main \{ flex-direction: column; \}/, "the narrow fold: the aside drops below the body");
  assert.match(body, /\.fc-hl \{ background: color-mix\(in srgb, var\(--warn\) 14%, transparent\); box-shadow: inset 0 0 0 1\.5px/, "a ring, not a fill a diff colour would occlude");
  assert.match(body, /\.fc-toggle\[data-on="1"\] \{ background: var\(--accent\); color: var\(--accent-fg\); border-color: var\(--accent\); \}/);
  // the body stays the plain overflow block the editor's height: 100% relies on
  assert.match(CHAT_CSS, /\.fileview-body \{ flex: 1 1 auto; min-height: 0; overflow: auto; \}/);
});

test("the gear's File comments row reads /defaults.fileComments: the reason for no-node, the install.sh sentence for absent tooling, no invented op", () => {
  assert.match(GEAR, /<b>File comments<\/b>/);
  assert.match(GEAR, /<span class=rs-sub id=rs-filecomments>/);
  assert.match(GEAR, /FILECOMMENTS_SUB\[typeof d\.fileComments === 'string' \? d\.fileComments : 'unknown'\]/);
  const sub = GEAR.split("var FILECOMMENTS_SUB = {")[1].split("\n};")[0];
  assert.match(sub, /'no-node': '[^']*node was not found on the kernel\\u2019s PATH[^']*Comments action does not appear[^']*'/, "names the machine's reason");
  assert.match(sub, /'agent-tooling-absent': '[^']*sessions cannot reply[^']*Run install\.sh on this machine[^']*there is no button for it[^']*'/);
  assert.match(sub, /this machine/, "the local kernel is the machine /defaults answers for");
  assert.doesNotMatch(GEAR, /linkTooling|installTooling|fileCommentsLink|runInstall/, "no WS op to run the link step exists — none is invented");
  // the row sits beside "File links open in"
  assert.ok(GEAR.indexOf("<b>File links open in</b>") < GEAR.indexOf("<b>File comments</b>") && GEAR.indexOf("<b>File comments</b>") < GEAR.indexOf("<b>Text scheme</b>"));
});

test("vocabulary and privacy: the person's words, never the format's; no personal identifiers", () => {
  // CONTEXT.md: file comment / change / tracked file / direct edit / comments log / Send to session — never thread,
  // suggestion, annotation in UI or docs. The CLI flag `--thread` in the message is the format's own and stays.
  assert.doesNotMatch(SRC, /\b(thread|suggestion|annotation)s?\b/i);
  const modelWords = (MODEL.match(/\b(thread|suggestion|annotation)s?\b/gi) || []).filter((w) => !new RegExp("--" + w).test(MODEL));
  assert.deepEqual([...new Set(MODEL.match(/[^-]\b(thread|annotation)s?\b/gi) || [])], [], "the model's only 'thread' is the --thread flag");
  void modelWords;
  const newGuide = GUIDE.slice(GUIDE.indexOf("### Files"), GUIDE.indexOf("## Automatic nudges"));
  assert.doesNotMatch(newGuide, /\b(suggestion|annotation)s?\b/i);
  assert.doesNotMatch(newGuide.replace(/`[^`]*`/g, ""), /\bthreads?\b/i);
  // This file is new prose too, and its assertion messages print to the person on failure — so it scans itself,
  // with the guard's own regex lines set aside (an assertion message here once named the sessions pane by its old word).
  const SELF = web("file-comments.test.ts").split("\n").filter((l) => !l.includes("/fleet/i")).join("\n");
  for (const [name, text] of [["file-comments.ts", SRC], ["file-comments-model.ts", MODEL], ["guide.md Files", newGuide], ["file-comments.test.ts", SELF]] as const) {
    assert.doesNotMatch(text, /fleet/i, name + ": no new fleet identifiers or prose");
    assert.doesNotMatch(text, /\/home\/[a-z]/, name + ": no absolute home paths");
  }
});

test("docs: the guide covers the panel, the poll, the consent, either view and media, the log and its opt-out, and where to look when the action is missing; the ADR is accepted", () => {
  const flat = (t: string) => t.replace(/\s+/g, " ");   // the guide wraps at 80 columns
  const files = flat(GUIDE.slice(GUIDE.indexOf("### Files"), GUIDE.indexOf("## Automatic nudges")));
  for (const phrase of ["**Comments**", "**Track changes**", "**Send to session**", "Rendered or Raw", "**Comment on this file**", "image or a PDF",
    ".trackchanges/", "comments log", ".gitignore", "**File comments**", "**File editing**", "every few seconds", "**Re-place**"]) {
    assert.ok(files.includes(phrase), "Files section: " + phrase);
  }
  const chat = flat(GUIDE.slice(GUIDE.indexOf("### The chat"), GUIDE.indexOf("### The feed")));
  assert.ok(chat.includes("quote chip"), "chips remain for one-off notes");
  assert.ok(chat.includes("**Comments**"), "…and point at the panel for anything worth keeping");
  assert.ok(files.includes("folder a session will write into"), "track the folder before the session writes");
  assert.match(ADR, /^Status: accepted \(2026-09-06\), with Slice 1 of `plans\/file-review\.md`$/m);
});

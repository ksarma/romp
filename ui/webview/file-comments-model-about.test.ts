// The about follow-on (plans/file-review.md, "The about follow-on (2026-09-10)" under Slice 2; decision 45) in the pure
// model: a comment names the changes it is ABOUT with `changeIds`, the person's own pick, and the model reads them as
// `refs` on its card, each with a source and a state; a legacy `suggestionId` (a sidecar from before the follow-on, or
// one `track-edit --thread` wrote) reads as a ref of source "answered". Pinned here: refIds and commentRefs (both fields,
// once each, the about list first, defensively); CardKind without "change" and every comment its own card (no `hunk`);
// the card's reference and decision from its refs; describeComment naming the passage THEN the changes ("about your
// change …", the same words the card wears) so the message to the session says which changes a comment is about, with
// the truncated-tail and unknown-change edges; changeCards counting the open comments about a change instead of
// hosting them (commentsAbout); and the sent text for an about desc, byte for byte the kernel's shape (C3), which
// tests/test_file_comments.py pins on its side to the same literal. Synthetic fixtures only: the notes-api world,
// placeholder ids, the session "api".
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import {
  type Status, type Hunk, type StoreComment, type LogEntry, type Card,
  refIds, commentRefs, aboutClause, changeWords, describeComment, cardModel, changeCards, commentsAbout, sendParts, buildSendMessage, statusEntries,
} from "./file-comments-model";

const REPO = path.resolve(process.cwd(), "..");
const read = (...p: string[]) => fs.readFileSync(path.join(REPO, ...p), "utf8");
const MODEL = read("ui", "webview", "file-comments-model.ts");

// ── fixtures: the notes-api world ──────────────────────────────────────────────────────────────────
const SID = "11111111-2222-3333-4444-555555555555";
const ABS = "/TESTDIR/notes-api/docs/report.md";
const ROOT = "/repo/notes-api";
const T0 = 1757145600000;
const DOC = "# Report\n\n## Findings\nThe api session cut p95 latency by 40% and the p99 by 10%.\n\n"
  + "We recommend shipping the cache in v1.3.\n\nCold starts stay slow.\n";
const at = (needle: string): number => { const i = DOC.indexOf(needle); assert.ok(i >= 0, needle); return i; };
const H = (id: string, kind: Hunk["kind"], from: number, to: number, oldText: string, newText: string, ts = T0 - 90000): Hunk =>
  ({ id, author: "api", ts, kind, curFrom: from, curTo: to, baseFrom: from, baseTo: from + oldText.length, oldText, newText, anchor: null });
const h1 = H("h1", "sub", at("cut"), at("cut") + 3, "reduced", "cut");
const h2 = H("h2", "ins", at("Cold starts"), at("Cold starts") + "Cold starts stay slow.".length, "", "Cold starts stay slow.", T0 - 80000);
const h3 = H("h3", "del", at("shipping"), at("shipping"), "quickly ", "", T0 - 70000);
const h4 = H("h4", "sub", at("v1.3"), at("v1.3") + 4, "v1.2", "v1.3", T0 - 60000);
const SUGG = [h1, h2, h3, h4].map((h) => ({ id: h.id, authorId: SID }));
const QUOTE = "shipping the cache in v1.3";
const ANCHOR = { quote: QUOTE, prefix: "We recommend ", suffix: "." };
/** A passage comment about the change inside its passage: the composer's checked "about 1 change" option. */
const aboutOne: StoreComment = { id: T0 + "-" + at(QUOTE), author: "you", ts: T0, body: "Which version ships it?", anchor: ANCHOR, anchorAt: at(QUOTE), changeIds: ["h4"], replies: [], resolved: false };
/** A comment about two changes with no passage: Comment on this change on a deletion, then a second id. */
const aboutTwo: StoreComment = { id: T0 + 1000 + "-" + at("shipping"), author: "you", ts: T0 + 1000, body: "Why drop the word, and why the version bump?", changeIds: ["h3", "h4"], replies: [], resolved: false };
/** A legacy comment the session answered with track-edit --thread: a passage, and the format's own field. */
const legacyPassage: StoreComment = { id: T0 + 2000 + "-" + at("cut"), author: "you", ts: T0 + 2000, body: "Say cut, not reduced.", anchor: { quote: "cut p95 latency by 40%", prefix: "The api session ", suffix: " and the p99 by 10%." }, suggestionId: "h1", replies: [{ author: "api", authorId: SID, ts: T0 + 2500, kind: "edit", oldText: "reduced", newText: "cut" }], resolved: false };
/** A legacy Reply on a change card: no passage, the format's own field. */
const legacyReply: StoreComment = { id: T0 + 3000 + "-" + at("Cold starts"), author: "you", ts: T0 + 3000, body: "Keep this.", suggestionId: "h2", replies: [], resolved: false };
const whole: StoreComment = { id: T0 + 4000 + "-0", author: "you", ts: T0 + 4000, body: "Add a summary.", replies: [], resolved: false };
const ACCEPT_H4: LogEntry = { ts: "2026-09-10T08:01:00Z", kind: "accept", author: "you", changes: [{ id: "h4", oldText: "v1.2", newText: "v1.3" }] };
const REJECT_H3: LogEntry = { ts: "2026-09-10T08:02:00Z", kind: "reject", author: "you", changes: [{ id: "h3", oldText: "quickly ", newText: "" }] };
const EDIT: LogEntry = { ts: "2026-09-10T08:03:00Z", kind: "edit", author: "you", summary: { bytesBefore: 120, bytesAfter: 124 } };
const store = (comments: StoreComment[], detached: unknown[] = []) => ({ v: 3, path: "docs/report.md", suggestions: SUGG, comments, detached });
function status(over: Partial<Status> = {}): Status {
  return {
    verb: "status", root: ROOT, storePath: ROOT + "/.trackchanges/docs%2Freport.md.json", trackedBy: { kind: "file", entry: "docs/report.md" },
    agentTooling: "present", fileMtimeNs: "1757145600000000001", storeMtimeNs: "1757145600000000002", configMtimeNs: "1757145600000000003",
    store: store([]), hunks: [h1, h2, h3, h4], log: [], unsent: { comments: [], replies: [], accepted: 0, rejected: 0, watermark: null },
    ...over,
  };
}
const unsentAll = (...cs: StoreComment[]) => ({ comments: cs.map((c) => c.id), replies: [], accepted: 0, rejected: 0, watermark: null });
const ROMP_NOUNS = /\b(romp|card|board|goal|column|cleared|dismissal|nudge|status check)s?\b/i;

// ── the refs ───────────────────────────────────────────────────────────────────────────────────────

test("refIds: the about list first, in its order, then the answering change; each id once, an id in both lists is the person's own; read defensively", () => {
  assert.deepEqual(refIds(aboutTwo), [{ id: "h3", source: "about" }, { id: "h4", source: "about" }]);
  assert.deepEqual(refIds(legacyReply), [{ id: "h2", source: "answered" }]);
  assert.deepEqual(refIds({ changeIds: ["h1", "h1", 7, "", null, "h2"] as unknown as string[], suggestionId: "h1" }), [{ id: "h1", source: "about" }, { id: "7", source: "about" }, { id: "h2", source: "about" }], "once each, numbers as strings, garbage skipped, the answering id already named as about stays about");
  assert.deepEqual(refIds({ changeIds: "h1" as unknown as string[] }), [], "a field of the wrong shape claims nothing");
  assert.deepEqual(refIds({ suggestionId: "" }), []);
  assert.deepEqual(refIds({}), []);
});

test("commentRefs: every named change with its source, its state and its texts through boundChange, the sidecar first; a change nothing describes is unknown", () => {
  assert.deepEqual(commentRefs(aboutTwo, [h1, h2, h3, h4], [], []), [
    { id: "h3", source: "about", state: "pending", kind: "del", oldText: "quickly ", newText: "" },
    { id: "h4", source: "about", state: "pending", kind: "sub", oldText: "v1.2", newText: "v1.3" },
  ]);
  assert.deepEqual(commentRefs(aboutTwo, [h1, h2], [], [ACCEPT_H4, REJECT_H3]), [
    { id: "h3", source: "about", state: "rejected", kind: "del", oldText: "quickly ", newText: "" },
    { id: "h4", source: "about", state: "accepted", kind: "sub", oldText: "v1.2", newText: "v1.3" },
  ], "decided: the log's entries, the kind derived from the texts");
  const D4 = { id: "h4", author: "api", ts: T0, kind: "sub", from: 90, oldText: "v1.2", newText: "v1.3", anchor: null, detached: true };
  assert.deepEqual(commentRefs(aboutOne, [h1], [D4], [ACCEPT_H4])[0], { id: "h4", source: "about", state: "detached", kind: "sub", oldText: "v1.2", newText: "v1.3" }, "the sidecar's detached op before an older log entry");
  assert.deepEqual(commentRefs(aboutOne, [h1], [], [EDIT], { h4: { decision: "accepted", oldText: "v1.2", newText: "v1.3" } })[0].state, "accepted", "the host's decided when the tail lacks the entry");
  assert.deepEqual(commentRefs(aboutOne, [h1], [], [EDIT]), [{ id: "h4", source: "about", state: "unknown", kind: null, oldText: "", newText: "" }], "gone from the sidecar with no decision known: the reference stands, unknown");
  assert.deepEqual(commentRefs(legacyPassage, [h1], [], []), [{ id: "h1", source: "answered", state: "pending", kind: "sub", oldText: "reduced", newText: "cut" }]);
});

// ── the card ───────────────────────────────────────────────────────────────────────────────────────

test("cardModel: every comment its own card, its refs on it, no hunk and no kind change; the reference is the passage, else the changes' words; the decision when every named change was decided alike", () => {
  const cards = cardModel(store([aboutOne, aboutTwo, legacyPassage, legacyReply, whole]), [h1, h2, h3, h4], []);
  assert.deepEqual(cards.map((c) => c.kind), ["passage", "file", "passage", "file", "file"], "kind says what the comment is ON; CardKind has no \"change\"");
  assert.ok(cards.every((c) => !("hunk" in c)), "no card rides a change card any more");
  assert.deepEqual(cards[0].refs.map((r) => [r.id, r.source, r.state]), [["h4", "about", "pending"]]);
  assert.equal(cards[0].ref, QUOTE, "a passage comment's reference stays its quote");
  assert.deepEqual(cards[1].refs.map((r) => [r.id, r.source]), [["h3", "about"], ["h4", "about"]]);
  assert.equal(cards[1].ref, "removed quickly; v1.2 → v1.3", "no passage: the changes' words, the change card's own (changeRef), one line");
  assert.deepEqual(cards[2].refs.map((r) => [r.id, r.source]), [["h1", "answered"]]);
  assert.equal(cards[2].ref, "cut p95 latency by 40%", "a legacy passage comment keeps its passage as the reference (before: the change's words)");
  assert.deepEqual(cards[2].replies.map((r) => r.kind), ["rev"], "the edit turn is a revision row still");
  assert.deepEqual(cards[3].refs.map((r) => [r.id, r.source]), [["h2", "answered"]]);
  assert.equal(cards[3].ref, "added Cold starts stay slow.", "the old Reply-on-a-change shape: the change's words");
  assert.deepEqual(cards[4].refs, []); assert.equal(cards[4].ref, "this file");
  assert.deepEqual(cards.map((c) => c.decision), [null, null, null, null, null], "pending: no decision");
  const decided = cardModel(store([aboutOne, aboutTwo]), [h1, h2], [ACCEPT_H4, REJECT_H3]);
  assert.equal(decided[0].decision, "accepted", "the one change it names was accepted");
  assert.equal(decided[1].decision, null, "two changes decided differently: no one tag says it; the refs carry each state");
  assert.deepEqual(decided[1].refs.map((r) => r.state), ["rejected", "accepted"]);
  const both = cardModel(store([{ ...aboutTwo, changeIds: ["h4", "h3"] }]), [h1, h2], [ACCEPT_H4, { ...REJECT_H3, kind: "accept" }]);
  assert.equal(both[0].decision, "accepted", "both accepted: the tag says so once");
  const unknown = cardModel(store([aboutOne]), [], [EDIT]);
  assert.equal(unknown[0].ref, QUOTE); assert.equal(unknown[0].refs[0].state, "unknown"); assert.equal(unknown[0].decision, null);
  const unknownOnly = cardModel(store([aboutTwo]), [], [EDIT]);
  assert.equal(unknownOnly[0].ref, "this file", "no passage and nothing known of the changes: the file, the honest fallback");
  assert.doesNotMatch(MODEL, /export type CardKind = [^;]*"change"/, "CardKind lost \"change\"");
  assert.doesNotMatch(MODEL, /\n\s*hunk: Hunk \| null;\n[^}]*replies: CardTurn\[\];/, "Card has no hunk");
});

test("changeCards: the count of open comments naming each change, both sources, resolved ones not counted; commentsAbout lists them oldest first", () => {
  const resolvedAbout: StoreComment = { ...aboutOne, id: T0 + 9000 + "-1", ts: T0 + 9000, resolved: true };
  const st = store([aboutOne, aboutTwo, legacyPassage, legacyReply, resolvedAbout]);
  const cards = changeCards(st, [h1, h2, h3, h4]);
  assert.deepEqual(cards.map((c) => [c.id, c.comments]), [["h1", 1], ["h3", 1], ["h4", 2], ["h2", 1]], "in text order; h4: the passage comment and the two-change one; the resolved one not counted; a legacy answering ref counts too");
  assert.ok(cards.every((c) => typeof c.comments === "number"), "a count, not the cards: no comment is drawn inside a change card");
  const all = cardModel(st, [h1, h2, h3, h4]);
  assert.deepEqual(commentsAbout(all, "h4").map((c) => c.id), [aboutOne.id, aboutTwo.id]);
  assert.deepEqual(commentsAbout(all, "h1").map((c) => c.id), [legacyPassage.id]);
  assert.deepEqual(commentsAbout(all, "nope"), []);
  const D = { id: "d1", author: "api", ts: T0, kind: "ins", from: 5, oldText: "", newText: "Added.", anchor: null, detached: true };
  const onD: StoreComment = { ...whole, id: T0 + 7000 + "-5", ts: T0 + 7000, changeIds: ["d1"] };
  const withD = changeCards(store([onD], [D]), [h1]);
  assert.deepEqual(withD.map((c) => [c.id, c.comments, c.detached]), [["h1", 0, false], ["d1", 1, true]], "a detached change's card counts the comments naming it");
  // the entries the seen set keys on: a comment's subject is its own card whatever it names
  const es = statusEntries({ store: st, hunks: [h1, h2, h3, h4] });
  assert.equal(es.find((e) => e.key === aboutOne.id)!.subject, aboutOne.id);
  assert.equal(es.find((e) => e.key === legacyReply.id)!.subject, legacyReply.id, "a legacy bound comment is its own card too (before: mapped onto the change card by the panel)");
});

// ── the description: the passage, then the changes ────────────────────────────────────────────────

test("describeComment: the passage first, then the changes the comment is about, in the change card's words; no passage: the about clause alone", () => {
  const hunks = [h1, h2, h3, h4];
  assert.equal(describeComment(aboutOne, hunks), 'on "shipping the cache in v1.3", about your change "v1.2" to "v1.3"');
  assert.equal(describeComment(aboutTwo, hunks), 'about the text you removed "quickly " and your change "v1.2" to "v1.3"', "two changes joined as a list; a deletion by its old text, a substitution by both");
  const three: StoreComment = { ...aboutTwo, changeIds: ["h2", "h3", "h4"] };
  assert.equal(describeComment(three, hunks), 'about the text you added "Cold starts stay slow.", the text you removed "quickly " and your change "v1.2" to "v1.3"', "three: commas, then and");
  assert.equal(changeWords(h1), 'your change "reduced" to "cut"'); assert.equal(changeWords(h2), 'the text you added "Cold starts stay slow."'); assert.equal(changeWords(h3), 'the text you removed "quickly "');
  assert.equal(aboutClause(commentRefs(aboutTwo, hunks, [], [])), 'about the text you removed "quickly " and your change "v1.2" to "v1.3"');
  assert.equal(aboutClause([]), null);
  // a region comment about a change: the region first, as the passage would be
  const region: StoreComment = { ...aboutOne, anchor: undefined, target: { kind: "image", region: { x: 0.1, y: 0.2, w: 0.3, h: 0.4 } } };
  assert.equal(describeComment(region, hunks), 'on the region at 0.10, 0.20, 0.30, 0.40, about your change "v1.2" to "v1.3"');
  for (const d of [describeComment(aboutOne, hunks), describeComment(aboutTwo, hunks), describeComment(three, hunks)]) {
    assert.doesNotMatch(d, ROMP_NOUNS, "the person's voice");
    assert.doesNotMatch(d, /""/, "no empty quoted text");
  }
});

test("describeComment after a decision: the change's texts from the log or the host's decided; a truncated tail names an unknown change by id, a full log leaves it out; a legacy answered ref keeps the passage or, with none, describes the change", () => {
  assert.equal(describeComment(aboutOne, [h1], [ACCEPT_H4]), 'on "shipping the cache in v1.3", about your change "v1.2" to "v1.3"', "accepted: the entry's texts");
  assert.equal(describeComment(aboutTwo, [h1], [ACCEPT_H4, REJECT_H3]), 'about the text you removed "quickly " and your change "v1.2" to "v1.3"');
  assert.equal(describeComment(aboutOne, [h1], [EDIT], { decided: { h4: { decision: "accepted", oldText: "v1.2", newText: "v1.3" } } }), 'on "shipping the cache in v1.3", about your change "v1.2" to "v1.3"', "the host's decided");
  assert.equal(describeComment(aboutOne, [h1], [EDIT], { logTruncated: true }), 'on "shipping the cache in v1.3", about your change h4', "a truncated tail: the change by id, since the decision may sit in the part not sent");
  assert.equal(describeComment(aboutTwo, [h1], [EDIT], { logTruncated: true }), "about your change h3 and your change h4");
  assert.equal(describeComment(aboutTwo, [h1], [REJECT_H3], { logTruncated: true }), 'about the text you removed "quickly " and your change h4', "one known, one not");
  assert.equal(describeComment(aboutOne, [h1], [EDIT]), 'on "shipping the cache in v1.3"', "a full log with no decision: the change left with none the log knows, and the passage alone describes the comment");
  assert.equal(describeComment(aboutTwo, [h1], [EDIT]), "on this file", "…and with no passage either, the file");
  // legacy: a passage comment the session answered is described by its passage (before: by the change, the passage dropped)
  assert.equal(describeComment(legacyPassage, [h1, h2, h3, h4]), 'on "cut p95 latency by 40%"');
  assert.equal(describeComment(legacyReply, [h1, h2, h3, h4]), 'on the text you added "Cold starts stay slow."', "the old Reply-on-a-change shape keeps its old words");
  assert.equal(describeComment(legacyReply, [], [EDIT], { logTruncated: true }), "on your change h2");
  assert.equal(describeComment(legacyReply, [], [EDIT]), "on this file");
  assert.equal(describeComment({ ...legacyReply, changeIds: ["h4"] }, [h1, h2, h3, h4]), 'about your change "v1.2" to "v1.3"', "an about ref beside a legacy one: the about clause describes it; the answering change is not what the comment is about");
});

test("the sent text with an about desc is the kernel's shape byte for byte: tests/test_file_comments.py pins the same literal (C3)", () => {
  const parts = sendParts(status({ store: store([aboutOne, aboutTwo]), unsent: unsentAll(aboutOne, aboutTwo) }));
  assert.deepEqual(parts.comments.map((c) => c.desc), ['on "shipping the cache in v1.3", about your change "v1.2" to "v1.3"', 'about the text you removed "quickly " and your change "v1.2" to "v1.3"']);
  const one = [{ id: "1781100000000-40", desc: 'on "shipping the cache in v1.3", about your change "v1.2" to "v1.3"', body: "Which version ships it?" }];
  const want = "[obsidian-diff] I left 1 comment on " + ABS + ".\n"
    + "\n"
    + "Comment 1781100000000-40 (on \"shipping the cache in v1.3\", about your change \"v1.2\" to \"v1.3\"):\n"
    + "Which version ships it?\n"
    + "\n"
    + "To respond:\n"
    + "  • reply in words:     node ~/.claude/hooks/track-reply.mjs --file " + ABS + " --thread <id> --note \"<your reply>\"\n"
    + "  • to revise the text: node ~/.claude/hooks/track-edit.mjs --file " + ABS + " --old \"<exact text>\" --new \"<replacement>\"\n"
    + "\n"
    + "When you have addressed these, ask me for another look the same way you asked for this one,\n"
    + "naming the file.\n";
  assert.equal(buildSendMessage({ absPath: ABS, comments: one, accepted: 0, rejected: 0, tracked: true }), want);
  assert.doesNotMatch(want, ROMP_NOUNS);
  const KERNEL = read("kernel", "kernel.py");
  assert.ok(KERNEL.includes("about your change"), "the kernel's docstring names the about form of the desc it prints verbatim");
});

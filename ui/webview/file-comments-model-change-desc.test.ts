// The message's parenthetical for a comment bound to a change (plans/file-review.md, the message to the session;
// C2's desc), by the change's kind, and where the change's texts come from once the sidecar no longer holds it.
// Pinned here: an insertion and a deletion are named by their one text — never 'your change "" to "…"', an empty
// quoted string in the person's voice — and the card says the same thing (changeRef); kindOf is the engine's rule,
// so the log's accept and reject entries (texts, no kind) read the same way; a truncated log tail
// (Status.logTruncated, the host's LOG_TAIL) never turns a bound comment into "on this file"; and the
// decisions-only message shape (a send with no comments) is the kernel's, byte for byte (C3). Synthetic fixtures
// only: the notes-api world, placeholder ids.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import {
  type Status, type Hunk, type StoreComment, type LogEntry,
  kindOf, changeDesc, changeRef, describeComment, decidedChange, cardModel, sendParts, buildSendMessage,
} from "./file-comments-model";

const REPO = path.resolve(process.cwd(), "..");
const read = (...p: string[]) => fs.readFileSync(path.join(REPO, ...p), "utf8");

// ── fixtures: the notes-api world ──────────────────────────────────────────────────────────────────
const SID = "11111111-2222-3333-4444-555555555555";
const ABS = "/repo/notes-api/docs/report.md";
const ROOT = "/repo/notes-api";
const T0 = 1757145600000;
const DOC = "# Report\n\n## Findings\nThe api session cut p95 latency by 40% and the p99 by 10%.\n\n"
  + "We recommend shipping the cache in v1.2.\n\nCold starts stay slow.\n";
const at = (needle: string): number => { const i = DOC.indexOf(needle); assert.ok(i >= 0, needle); return i; };
const H = (id: string, kind: Hunk["kind"], from: number, to: number, oldText: string, newText: string, ts = T0 - 90000): Hunk =>
  ({ id, author: "api", ts, kind, curFrom: from, curTo: to, baseFrom: from, baseTo: from + oldText.length, oldText, newText, anchor: null });
const h1 = H("h1", "sub", at("cut"), at("cut") + 3, "reduced", "cut");
const h2 = H("h2", "ins", at("Cold starts"), at("Cold starts") + "Cold starts stay slow.".length, "", "Cold starts stay slow.", T0 - 80000);
const h3 = H("h3", "del", at("shipping"), at("shipping"), "quickly ", "", T0 - 70000);
const bound = (id: string, suggestionId: string, body: string, ts: number): StoreComment =>
  ({ id, author: "you", ts, body, suggestionId, replies: [], resolved: false });
const onH1 = bound(T0 + 1000 + "-5", "h1", "Say cut, not reduced.", T0 + 1000);
const onH2 = bound(T0 + 2000 + "-12", "h2", "Keep this.", T0 + 2000);
const onH3 = bound(T0 + 3000 + "-40", "h3", "Why drop it?", T0 + 3000);
const ACCEPT_SUB: LogEntry = { ts: "2026-09-06T08:01:00Z", kind: "accept", author: "you", changes: [{ id: "h1", oldText: "reduced", newText: "cut" }] };
const ACCEPT_INS: LogEntry = { ts: "2026-09-06T08:02:00Z", kind: "accept", author: "you", changes: [{ id: "h2", oldText: "", newText: "Cold starts stay slow." }] };
const REJECT_DEL: LogEntry = { ts: "2026-09-06T08:03:00Z", kind: "reject", author: "you", changes: [{ id: "h3", oldText: "quickly ", newText: "" }] };
const EDIT: LogEntry = { ts: "2026-09-06T08:04:00Z", kind: "edit", author: "you", summary: { bytesBefore: 120, bytesAfter: 124 } };
function status(over: Partial<Status> = {}): Status {
  return {
    verb: "status", root: ROOT, storePath: ROOT + "/.trackchanges/docs%2Freport.md.json", trackedBy: { kind: "file", entry: "docs/report.md" },
    agentTooling: "present", fileMtimeNs: "1757145600000000001", storeMtimeNs: "1757145600000000002", configMtimeNs: "1757145600000000003",
    store: { v: 3, path: "docs/report.md", suggestions: [], comments: [] }, hunks: [], log: [],
    unsent: { comments: [], replies: [], accepted: 0, rejected: 0, watermark: null },
    ...over,
  };
}
const unsentAll = (...cs: StoreComment[]) => ({ comments: cs.map((c) => c.id), replies: [], accepted: 0, rejected: 0, watermark: null });
const ROMP_NOUNS = /\b(romp|card|board|goal|column|cleared|dismissal|nudge|status check)s?\b/i;

test("describeComment by kind, from a pending hunk: a substitution names both texts, an insertion its new text, a deletion its old text — never an empty quoted string", () => {
  assert.equal(describeComment(onH1, [h1, h2, h3]), 'on your change "reduced" to "cut"', "the plan's own template for a substitution, unchanged (the C3 fixture across the suites)");
  assert.equal(describeComment(onH2, [h1, h2, h3]), 'on the text you added "Cold starts stay slow."');
  assert.equal(describeComment(onH3, [h1, h2, h3]), 'on the text you removed "quickly "');
  for (const h of [h1, h2, h3]) {
    const d = changeDesc(h);
    assert.doesNotMatch(d, /""/, h.kind + ": no empty quoted text");
    assert.doesNotMatch(d, /your change "" to|" to ""/, h.kind);
    assert.doesNotMatch(d, ROMP_NOUNS, h.kind + ": the person's voice");
    assert.ok(d.includes(h.kind === "del" ? h.oldText : h.newText), h.kind + ": carries the text the session can find");
  }
});

test("…and from the log's accept or reject entry, whose texts carry no kind: kindOf is the engine's own rule, pinned against engine.js", () => {
  assert.equal(describeComment(onH1, [], [ACCEPT_SUB]), 'on your change "reduced" to "cut"');
  assert.equal(describeComment(onH2, [], [ACCEPT_INS]), 'on the text you added "Cold starts stay slow."', "an accepted insertion");
  assert.equal(describeComment(onH3, [], [REJECT_DEL]), 'on the text you removed "quickly "', "a rejected deletion");
  assert.deepEqual(decidedChange([ACCEPT_INS], "h2"), { decision: "accepted", oldText: "", newText: "Cold starts stay slow." }, "the entry as the log has it: the kind is derived where it is read");
  assert.equal(kindOf("reduced", "cut"), "sub"); assert.equal(kindOf("", "cut"), "ins"); assert.equal(kindOf("reduced", ""), "del");
  assert.equal(kindOf("", ""), "del", "the engine's own edge: no text either way reads as a deletion");
  const ENGINE = read("vendor", "track-changents", "engine.js");
  assert.match(ENGINE, /function kindOf\(oldText, newText\) \{\n  return oldText && newText \? 'sub' : \(newText \? 'ins' : 'del'\);\n\}/, "the rule this ports, word for word");
  assert.match(ENGINE, /kind: kindOf\(oldText, newText\),/, "…and the one toHunks applies, so a hunk's kind and a log entry's derived kind agree");
});

test("the card and the message agree: changeRef's added/removed is changeDesc's added/removed for every kind; the sent message carries the one-text forms", () => {
  assert.equal(changeRef(h2), "added Cold starts stay slow.");
  assert.equal(changeRef(h3), "removed quickly");
  assert.match(changeDesc(h2), /^on the text you added "/); assert.match(changeDesc(h3), /^on the text you removed "/);
  assert.equal(changeRef(h1), "reduced → cut"); assert.match(changeDesc(h1), /^on your change "reduced" to "cut"$/);
  const parts = sendParts(status({ store: { v: 3, path: "docs/report.md", suggestions: [], comments: [onH2, onH3] }, hunks: [h1, h2, h3], unsent: unsentAll(onH2, onH3) }));
  assert.deepEqual(parts.comments.map((c) => c.desc), ['on the text you added "Cold starts stay slow."', 'on the text you removed "quickly "']);
  const msg = buildSendMessage({ absPath: ABS, comments: parts.comments, accepted: parts.accepted, rejected: parts.rejected, tracked: true });
  assert.ok(msg.includes("Comment " + onH2.id + ' (on the text you added "Cold starts stay slow."):\nKeep this.\n'), msg);
  assert.ok(msg.includes("Comment " + onH3.id + ' (on the text you removed "quickly "):\nWhy drop it?\n'), msg);
  assert.doesNotMatch(msg, /\(on your change "" to|" to ""\)/, "the old form is gone from the sent text");
});

test("cardModel: a decided insertion's card reads 'added …' and a decided deletion's 'removed …' — the change card's own words — with the decision from the log", () => {
  const cards = cardModel({ v: 3, path: "docs/report.md", suggestions: [], comments: [onH1, onH2, onH3] }, [], [ACCEPT_SUB, ACCEPT_INS, REJECT_DEL]);
  assert.deepEqual(cards.map((c) => [c.kind, c.ref, c.decision, c.hunk]), [
    ["change", "reduced → cut", "accepted", null],
    ["change", "added Cold starts stay slow.", "accepted", null],
    ["change", "removed quickly", "rejected", null],
  ]);
  const pending = cardModel({ v: 3, path: "docs/report.md", suggestions: [], comments: [onH2] }, [h2], []);
  assert.equal(pending[0].ref, "added Cold starts stay slow."); assert.equal(pending[0].hunk?.id, "h2"); assert.equal(pending[0].decision, null);
});

test("a truncated log: when the host's tail lacks the decision, a bound comment names the change rather than claiming the file; a full log without it keeps the file fallback; an anchor still wins", () => {
  // the host caps the status's log at its newest LOG_TAIL entries (tools/file-comments-host.mjs) and says so with
  // logTruncated; the accept entry of an older decision is then not in the reply, though it is on disk
  const HOST = read("tools", "file-comments-host.mjs");
  assert.match(HOST, /logTruncated = entries\.length > LOG_TAIL;\n\s*log = logTruncated \? entries\.slice\(entries\.length - LOG_TAIL\) : entries;/, "the tail this guards against");
  const st = { v: 3, path: "docs/report.md", suggestions: [], comments: [{ ...onH1, resolved: true }] };
  const truncated = sendParts(status({ store: st, hunks: [], log: [EDIT, EDIT], logTruncated: true, unsent: unsentAll(onH1) }));
  assert.equal(truncated.comments[0].desc, "on your change h1", "the comment is on a change; the tail just does not carry its texts");
  const full = sendParts(status({ store: st, hunks: [], log: [EDIT, EDIT], logTruncated: false, unsent: unsentAll(onH1) }));
  assert.equal(full.comments[0].desc, "on this file", "a complete log with no decision: the change left the sidecar with none the log knows — the standing fallback");
  const present = sendParts(status({ store: st, hunks: [], log: [ACCEPT_SUB, EDIT], logTruncated: true, unsent: unsentAll(onH1) }));
  assert.equal(present.comments[0].desc, 'on your change "reduced" to "cut"', "the entry in the tail: its texts");
  assert.equal(describeComment(onH1, [], [], { logTruncated: true }), "on your change h1");
  assert.equal(describeComment(onH1, [], []), "on this file");
  assert.equal(describeComment(onH1, [], undefined, { logTruncated: false }), "on this file");
  const anchored: StoreComment = { ...onH1, anchor: { quote: "cut p95 latency by 40%", prefix: "The api session ", suffix: " and" } };
  assert.equal(describeComment(anchored, [], [], { logTruncated: true }), 'on "cut p95 latency by 40%"', "a passage comment track-edit --thread bound: its passage describes it");
  const region: StoreComment = { ...onH1, target: { kind: "image", region: { x: 0.1, y: 0.2, w: 0.3, h: 0.4 } } };
  assert.equal(describeComment(region, [], [], { logTruncated: true }), "on the region at 0.10, 0.20, 0.30, 0.40");
  const msg = buildSendMessage({ absPath: ABS, comments: truncated.comments, accepted: 0, rejected: 0, tracked: true });
  assert.ok(msg.includes("Comment " + onH1.id + " (on your change h1):\nSay cut, not reduced.\n"), msg);
  assert.doesNotMatch("on your change h1", ROMP_NOUNS);
  // the host's `decided` (tools/file-comments-host.mjs decidedFor): the decision read off the WHOLE log for a change a
  // comment is bound to that the sidecar no longer holds — so the card and the message have the texts however old the
  // decision is, and the by-id fallback above is left for a host from before the field
  const decided = { h1: { decision: "accepted" as const, oldText: "reduced", newText: "cut" } };
  const viaDecided = sendParts(status({ store: st, hunks: [], log: [EDIT, EDIT], logTruncated: true, decided, unsent: unsentAll(onH1) }));
  assert.equal(viaDecided.comments[0].desc, 'on your change "reduced" to "cut"', "the message names the texts, not the id");
  assert.equal(describeComment(onH1, [], [EDIT], { logTruncated: true, decided }), 'on your change "reduced" to "cut"');
  const cards = cardModel(st, [], [EDIT, EDIT], decided);
  assert.deepEqual(cards.map((c) => [c.kind, c.ref, c.decision, c.hunk]), [["change", "reduced → cut", "accepted", null]], "the card reads as a decided change, not as a comment on the file");
  assert.deepEqual(cardModel(st, [], [EDIT, EDIT]).map((c) => [c.kind, c.ref]), [["file", "this file"]], "without it, the standing fallback — the truncation the field exists for");
  // the lookup order is the sidecar's own, then the tail's entry, then decided: a pending hunk wins, and the tail's own
  // entry is read before the host's (same texts by construction; the order says whose word it is)
  const grown = { h1: { decision: "rejected" as const, oldText: "reduced", newText: "cut, later" } };
  assert.equal(describeComment(onH1, [h1], [], { decided: grown }), 'on your change "reduced" to "cut"', "pending: the hunk");
  assert.equal(describeComment(onH1, [], [ACCEPT_SUB], { decided: grown }), 'on your change "reduced" to "cut"', "the tail's entry before the host's field");
  assert.equal(cardModel(st, [], [], grown)[0].decision, "rejected", "decided alone: its verdict");
});

// The kernel's decisions-only shape (kernel.py _file_comments_message, `if not comments:`), which
// tests/test_kernel_file_comments_decisions_send.py pins on its side; file-comments.test.ts's cross-run feeds both
// builders the same inputs. A send with no comments is reachable since Slice 2: a manual Accept or Reject is
// unsent until a send carries it.
const ASK_AGAIN = "When you have made more changes, ask me for another look the same way you asked for this one,\nnaming the file.\n";

test("the decisions-only message (no comments): the kernel's second shape byte for byte — the file, the decisions line, nothing needs a reply, the closing ask", () => {
  assert.equal(buildSendMessage({ absPath: ABS, comments: [], accepted: 3, rejected: 0, tracked: true }),
    "[obsidian-diff] I went over " + ABS + ".\n" +
    "\n" +
    "I accepted 3 of your changes and rejected 0.\n" +
    "\n" +
    "No comments this time, so nothing needs a reply.\n" + ASK_AGAIN);
  assert.ok(buildSendMessage({ absPath: ABS, comments: [], accepted: 0, rejected: 3, tracked: true }).includes("\n\nI accepted 0 of your changes and rejected 3.\n\nNo comments this time"));
  assert.ok(buildSendMessage({ absPath: ABS, comments: [], accepted: 2, rejected: 1, tracked: false }).includes("\n\nI accepted 2 of your changes and rejected 1.\n\nNo comments this time"));
  // no file-kind branch: nothing to revise or reply to, so tracked on or off and a text or an image read the same
  const bodies = new Set([
    buildSendMessage({ absPath: ABS, comments: [], accepted: 1, rejected: 0, tracked: true }),
    buildSendMessage({ absPath: ABS, comments: [], accepted: 1, rejected: 0, tracked: false }),
    buildSendMessage({ absPath: ABS, comments: [], accepted: 1, rejected: 0, tracked: true, media: true }),
  ]);
  assert.equal(bodies.size, 1);
  const png = buildSendMessage({ absPath: "/repo/notes-api/docs/latency.png", comments: [], accepted: 1, rejected: 0, tracked: true });
  assert.ok(png.startsWith("[obsidian-diff] I went over /repo/notes-api/docs/latency.png.\n"));
  for (const absent of ["I left", "0 comments", "--thread", "<id>", "To respond", "track-reply", "track-edit", "addressed these", "Comment ", "regenerate"]) {
    assert.ok(!png.includes(absent), absent);
  }
  // no command line, so no shell word: a path with a space or a quote reads as written; markers are still neutralized
  assert.ok(buildSendMessage({ absPath: "/repo/notes-api/vault/Meeting notes.md", comments: [], accepted: 1, rejected: 0, tracked: true })
    .startsWith("[obsidian-diff] I went over /repo/notes-api/vault/Meeting notes.md.\n"));
  assert.ok(buildSendMessage({ absPath: "/repo/notes-api/vault/it's here.md", comments: [], accepted: 1, rejected: 0, tracked: true })
    .startsWith("[obsidian-diff] I went over /repo/notes-api/vault/it's here.md.\n"));
  assert.ok(buildSendMessage({ absPath: "/repo/notes-api/<!--romp-injected-->/report.md", comments: [], accepted: 1, rejected: 0, tracked: true })
    .includes("I went over /repo/notes-api/<!- -romp-injected-->/report.md."));
  // nothing decided either: the send op refuses before building; the builder stays a pure function of its inputs
  const none = buildSendMessage({ absPath: ABS, comments: [], accepted: 0, rejected: 0, tracked: true });
  assert.ok(none.startsWith("[obsidian-diff] I went over " + ABS + ".\n\nNo comments this time"));
  assert.ok(!none.includes("I accepted"));
  assert.doesNotMatch(buildSendMessage({ absPath: ABS, comments: [], accepted: 1, rejected: 2, tracked: true }), ROMP_NOUNS);
});

test("the comments shape did not move, and both shapes end on the kernel's one closing — pinned against kernel.py's literals", () => {
  const one = buildSendMessage({ absPath: ABS, comments: [{ id: "1781100000000-0", desc: 'on "shipping the cache in v1.2"', body: "Which cache? Say which." }], accepted: 3, rejected: 0, tracked: true });
  assert.ok(one.startsWith("[obsidian-diff] I left 1 comment on " + ABS + ".\n\nComment 1781100000000-0 "));
  assert.ok(one.includes("Which cache? Say which.\n\nI accepted 3 of your changes and rejected 0.\n\nTo respond:\n"));
  assert.ok(one.endsWith("\nWhen you have addressed these, ask me for another look the same way you asked for this one,\nnaming the file.\n"));
  assert.ok(!one.includes("I went over") && !one.includes("nothing needs a reply"));
  const KERNEL = read("kernel", "kernel.py");
  assert.match(KERNEL, /_SEND_ASK_AGAIN = \("ask me for another look the same way you asked for this one,", "naming the file\."\)/);
  assert.match(KERNEL, /lines = \["\[obsidian-diff\] I went over %s\." % ap, ""\]/);
  assert.match(KERNEL, /"No comments this time, so nothing needs a reply\.",\n\s*"When you have made more changes, " \+ _SEND_ASK_AGAIN\[0\], _SEND_ASK_AGAIN\[1\]\]/);
  assert.match(KERNEL, /lines\.append\("When you have addressed these, " \+ _SEND_ASK_AGAIN\[0\]\)/);
  const MODEL = read("ui", "webview", "file-comments-model.ts");
  assert.match(MODEL, /const SEND_ASK_AGAIN = \["ask me for another look the same way you asked for this one,", "naming the file\."\] as const;/, "the same constant on this side");
});

// The Comments panel's CHANGE cards (plans/file-review.md, Slice 2; the contract's D1 and D5): the pure model
// runs for real (one card per change, paragraph groups named by their first line, the fold past three groups,
// the send's counts, the message with the decisions line against the kernel's literal shape, the Edit refusal's
// wording, a decided change remembered from the log); what a stand-in cannot show is pinned at source (the
// data-act names, the fence carrying fileMtimeNs for the file-writing verbs only, the send sequence's order,
// the third checkbox's default); and the panel is driven AS A PANEL over the behavior suite's DOM stand-in for
// Accept, Reject with the retry after a file-moved refusal, Accept all through the send confirm, Reveal, the
// fold, a click on an inline mark, Reply bound to a change, a comment shown on its change's card, and the
// repaints over ONE body (the open's, a poll tick's, an accept's) leaving one mark per change. Synthetic
// fixtures only: the notes-api world, placeholder ids.
//
// The inline marks are painted by anchor-map's change painters (contract D4, built beside this): the driven
// tests assert only what any conforming painter yields — an element carrying data-act="fcchange" and the
// change's id for an insertion or substitution — never a painter's own classes, and of a deletion's mark only
// that a repaint never doubles it.
import { test, type TestContext } from "node:test";
import * as assert from "node:assert/strict";
import { inspect } from "node:util";
import { hideEdges, staysEnumerable } from "../test-dom-shim";
import * as fs from "node:fs";
import * as path from "node:path";
import type { FileViewActionCtx } from "./file-view";
import {
  type Status, type Hunk, type StoreComment, type LogEntry, changeCards, changeGroups, foldGroups, paragraphAt, moreChangesLabel, GROUP_LIMIT,
  changeRef, authorIdOf, sendCounts, sendParts, buildSendMessage, editBlockedReason, describeComment, decidedChange, cardModel, actionLabel,
} from "./file-comments-model";

const web = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const SRC = web("file-comments.ts");
const MODEL = web("file-comments-model.ts");
const GUIDE = fs.readFileSync(path.resolve(process.cwd(), "..", "docs", "guide.md"), "utf8");

// ── fixtures: the notes-api world ──────────────────────────────────────────────────────────────────
const SID = "11111111-2222-3333-4444-555555555555";
const ABS = "/repo/notes-api/docs/report.md";
const ROOT = "/repo/notes-api";
const STORE_PATH = ROOT + "/.trackchanges/docs%2Freport.md.json";
const T0 = 1757145600000;
// the CURRENT text: the session's changes already applied (the file on disk always reads as if accepted)
const DOC = "# Report\n\n## Findings\nThe api session cut p95 latency by 40% and the p99 by 10%.\n\n"
  + "We recommend shipping the cache in v1.2.\n\nRisks remain in the fallback path.\n\nNext steps: measure again.\n";
const at = (needle: string, from = 0): number => { const i = DOC.indexOf(needle, from); assert.ok(i >= 0, needle); return i; };
const H = (id: string, kind: Hunk["kind"], from: number, to: number, oldText: string, newText: string, ts = T0 - 90000): Hunk =>
  ({ id, author: "api", ts, kind, curFrom: from, curTo: to, baseFrom: from, baseTo: from + oldText.length, oldText, newText, anchor: null });
const h1 = H("h1", "sub", at("cut"), at("cut") + 3, "reduced", "cut");                                        // paragraph: ## Findings …
const h2 = H("h2", "ins", at(" and the p99"), at(" and the p99") + " and the p99 by 10%".length, "", " and the p99 by 10%", T0 - 80000);
const h3 = H("h3", "del", at("shipping"), at("shipping"), "quickly ", "", T0 - 70000);                           // a point: We recommend …
const h4 = H("h4", "sub", at("remain"), at("remain") + 6, "persist", "remain", T0 - 60000);                       // Risks …
const h5 = H("h5", "ins", at(" again"), at(" again") + 6, "", " again", T0 - 50000);                             // Next steps …
const FIVE = [h1, h2, h3, h4, h5];
const passage: StoreComment = {
  id: T0 + "-118", author: "you", ts: T0, body: "Which cache? Say which.",
  anchor: { quote: "shipping the cache in v1.2", prefix: "We recommend ", suffix: "." }, replies: [], resolved: false,
};
const bound: StoreComment = { id: T0 + 1000 + "-5", author: "you", ts: T0 + 1000, body: "Say cut, not reduced.", suggestionId: "h1", replies: [
  { author: "api", authorId: SID, ts: T0 + 2000, kind: "edit", oldText: "cut", newText: "trimmed" },
  { author: "api", authorId: SID, ts: T0 + 3000, body: "Done." },
], resolved: false };
const SUGG = [{ id: "h1", author: "api", authorId: SID, ts: T0 - 90000, kind: "sub", from: h1.curFrom, oldText: "reduced", newText: "cut" },
  { id: "h3", author: "api", ts: T0 - 70000, kind: "del", from: h3.curFrom, oldText: "quickly " }];
function status(over: Partial<Status> = {}): Status {
  return {
    verb: "status", root: ROOT, storePath: STORE_PATH, trackedBy: { kind: "file", entry: "docs/report.md" }, agentTooling: "present",
    fileMtimeNs: "1757145600000000001", storeMtimeNs: "1757145600000000002", configMtimeNs: "1757145600000000003",
    store: { v: 3, path: "docs/report.md", suggestions: SUGG, comments: [passage] },
    hunks: [h1, h3], log: [],
    unsent: { comments: [passage.id], replies: [], accepted: 0, rejected: 0, watermark: null },
    ...over,
  };
}
const ACCEPT_LOG: LogEntry = { ts: "2026-09-06T08:01:00Z", kind: "accept", author: "you", changes: [{ id: "h1", oldText: "reduced", newText: "cut" }] };

// ── the pure half ──────────────────────────────────────────────────────────────────────────────────

test("hunk kinds are the engine's three strings everywhere (D1): the type, the fixtures, and the reference per kind", () => {
  assert.match(MODEL, /export type HunkKind = "ins" \| "del" \| "sub";/);
  assert.match(MODEL, /kind: HunkKind; curFrom: number; curTo: number;/);
  for (const f of ["file-comments.test.ts", "file-view-seam.test.ts", "file-comments-changes.test.ts"]) assert.doesNotMatch(web(f), /kind: "(replace|insert|delete)"/, f + " uses no plan-era kind");
  assert.equal(changeRef(h1), "reduced → cut");
  assert.equal(changeRef(h2), "added and the p99 by 10%");
  assert.equal(changeRef(h3), "removed quickly");
  assert.equal(changeRef({ kind: "sub", oldText: "a".repeat(40), newText: "b" }), "a".repeat(29) + "… → b", "each side one-lined at 30");
  assert.equal(h3.curFrom, h3.curTo, "a deletion is a point in the current text");
});

test("changeCards: one card per hunk in text order, keyed apart from comment ids, with the sidecar's authorId and the count of comments naming it", () => {
  const st = status({ store: { v: 3, path: "docs/report.md", suggestions: SUGG, comments: [passage, bound] }, hunks: [h3, h1] });
  const cards = changeCards(st.store, [h3, h1]);
  assert.deepEqual(cards.map((c) => c.id), ["h1", "h3"], "ordered by curFrom, whatever order the reply gave");
  assert.deepEqual(cards.map((c) => c.key), ["chg:h1", "chg:h3"], "the expand key is prefixed: a change id and a comment id can never collide");
  assert.equal(cards[0].authorId, SID, "toHunks drops authorId; the sidecar record has it");
  assert.equal(cards[1].authorId, null, "a record without one: neutral");
  assert.equal(cards[0].comments, 1, "the count of open comments naming the change (the about follow-on: the comment is its own card, not the change card's)");
  assert.equal(cards[1].comments, 0);
  const own = cardModel(st.store, [h3, h1]).find((c) => c.id === bound.id)!;
  assert.deepEqual(own.replies.map((r) => r.kind), ["rev", "msg"], "an edit turn is a revision row, in ts order among the words");
  const rev = own.replies[0];
  assert.ok(rev.kind === "rev" && rev.oldText === "cut" && rev.newText === "trimmed");
  assert.deepEqual(changeCards(null, [h1]).map((c) => c.authorId), [null], "no sidecar in the reply: still a card per hunk");
  assert.equal(authorIdOf(status().store, "h1"), SID); assert.equal(authorIdOf(status().store, "nope"), null); assert.equal(authorIdOf(null, "h1"), null);
});

test("paragraphs: the source split on blank lines; a group is named by its first line, trimmed to 60 characters", () => {
  assert.deepEqual(paragraphAt(DOC, at("cut")), { start: at("## Findings"), end: at("10%.") + 4 }, "the heading and the line under it are one paragraph (no blank between)");
  assert.deepEqual(paragraphAt(DOC, 0), { start: 0, end: 8 });
  assert.deepEqual(paragraphAt(DOC, 9), { start: 9, end: 9 }, "a blank line is its own empty paragraph");
  assert.deepEqual(paragraphAt(DOC, DOC.length), { start: DOC.length, end: DOC.length }, "past the end: empty, never throws");
  const groups = changeGroups(changeCards(null, FIVE), DOC);
  assert.deepEqual(groups.map((g) => g.title), ["## Findings", "We recommend shipping the cache in v1.2.", "Risks remain in the fallback path.", "Next steps: measure again."]);
  assert.deepEqual(groups.map((g) => g.changes.map((c) => c.id)), [["h1", "h2"], ["h3"], ["h4"], ["h5"]], "consecutive changes in one paragraph share a group");
  const long = "x".repeat(70) + "\n\nshort\n";
  const g2 = changeGroups(changeCards(null, [H("a", "ins", 0, 1, "", "x"), H("b", "ins", 72, 73, "", "s")]), long);
  assert.equal(g2[0].title, "x".repeat(59) + "…", "60 characters with the ellipsis");
  assert.equal(g2[1].title, "short");
  const blankAt = changeGroups(changeCards(null, [H("d", "del", 9, 9, "gone\n", "")]), DOC);
  assert.equal(blankAt[0].title, "line 2", "a deletion at a blank line: the paragraph has no first line, so the line number names it");
  assert.deepEqual(changeGroups(changeCards(null, [h1]), null).map((g) => [g.title, g.changes.length]), [["", 1]], "no text to read (media, or not loaded yet): one unnamed group");
  assert.deepEqual(changeGroups([], DOC), []);
});

test("the fold: more than three groups collapse behind one '… N more changes' row counting CHANGES; expanded shows all", () => {
  assert.equal(GROUP_LIMIT, 3);
  const groups = changeGroups(changeCards(null, FIVE), DOC);
  const folded = foldGroups(groups, false);
  assert.deepEqual(folded.shown.map((g) => g.title), ["## Findings", "We recommend shipping the cache in v1.2.", "Risks remain in the fallback path."]);
  assert.deepEqual(folded.hidden.map((g) => g.changes.map((c) => c.id)), [["h5"]]);
  assert.equal(folded.hiddenChanges, 1);
  assert.equal(moreChangesLabel(1), "… 1 more change"); assert.equal(moreChangesLabel(4), "… 4 more changes");
  const open = foldGroups(groups, true);
  assert.equal(open.shown.length, 4); assert.equal(open.hiddenChanges, 0);
  const three = foldGroups(groups.slice(0, 3), false);
  assert.equal(three.hidden.length, 0, "exactly three groups: nothing folds");
  // two groups hidden, three changes between them: the row counts the changes the person has yet to see
  const many = changeGroups(changeCards(null, [...FIVE, H("h6", "ins", at("measure"), at("measure") + 7, "", "measure", T0), H("h7", "sub", at("Report"), at("Report") + 6, "Draft", "Report", T0)]), DOC);
  assert.equal(many.length, 5);
  assert.equal(foldGroups(many, false).hiddenChanges, 3);
});

test("the glance and the counts: 'Comments · N · M changes'; the send's A and R fold in the pending changes only when the box is checked", () => {
  assert.equal(actionLabel(status({ hunks: FIVE, store: { v: 3, path: "docs/report.md", suggestions: [], comments: [passage, bound] } })), "Comments · 2 · 5 changes");
  const parts = sendParts(status({ unsent: { comments: [passage.id], replies: [], accepted: 1, rejected: 2, watermark: null } }));
  assert.deepEqual(sendCounts(parts, true, 3), { accepted: 4, rejected: 2 }, "the log's unsent decisions plus the N the send accepts");
  assert.deepEqual(sendCounts(parts, false, 3), { accepted: 1, rejected: 2 }, "unchecked: the log's alone");
  assert.deepEqual(sendCounts(parts, true, 0), { accepted: 1, rejected: 2 }, "nothing pending: the box is not even offered");
});

// The kernel builds the sent text from the same A and R (contract C3); tests/test_file_comments.py pins the same
// literal shape on its side, and file-comments.test.ts's cross-run feeds both builders the decisions case. A send
// with NO comments (a manual Accept or Reject carried alone) wears the kernel's decisions-only shape instead —
// no "0 comments" header, no `--thread <id>` command lines with no id to put in them (the round-1 review,
// 2026-09-06); file-comments-model-change-desc.test.ts pins that shape in full, and tests/test_kernel_file_comments_decisions_send.py
// on the kernel's side.
const TAIL = "To respond:\n" +
  "  • reply in words:     node ~/.claude/hooks/track-reply.mjs --file " + ABS + " --thread <id> --note \"<your reply>\"\n" +
  "  • to revise the text: node ~/.claude/hooks/track-edit.mjs --file " + ABS + " --old \"<exact text>\" --new \"<replacement>\"\n" +
  "\n" +
  "When you have addressed these, ask me for another look the same way you asked for this one,\n" +
  "naming the file.\n";

test("the preview with decisions, ONE comment: the 'I accepted A of your changes and rejected R.' line, blank-line framed, before the commands", () => {
  const msg = buildSendMessage({ absPath: ABS, comments: [{ id: "1757145601000-5", desc: 'on your change "reduced" to "cut"', body: "Say cut, not reduced." }],
    accepted: 4, rejected: 1, tracked: true });
  assert.equal(msg,
    "[obsidian-diff] I left 1 comment on " + ABS + ".\n" +
    "\n" +
    "Comment 1757145601000-5 (on your change \"reduced\" to \"cut\"):\n" +
    "Say cut, not reduced.\n" +
    "\n" +
    "I accepted 4 of your changes and rejected 1.\n" +
    "\n" + TAIL);
});

test("the preview with decisions, SEVERAL comments; no comments at all wears the decisions-only shape (R alone); the line absent when A + R is zero", () => {
  const several = buildSendMessage({ absPath: ABS, comments: [
    { id: "1757145540000-40", desc: 'on "The api session cut p95 latency by 40%"', body: "Thanks, and drop the chart too." },
    { id: "1757145600000-118", desc: 'on "shipping the cache in v1.2"', body: "Which cache? Say which." },
  ], accepted: 2, rejected: 0, tracked: true });
  assert.equal(several,
    "[obsidian-diff] I left 2 comments on " + ABS + ".\n" +
    "\n" +
    "Comment 1757145540000-40 (on \"The api session cut p95 latency by 40%\"):\n" +
    "Thanks, and drop the chart too.\n" +
    "\n" +
    "Comment 1757145600000-118 (on \"shipping the cache in v1.2\"):\n" +
    "Which cache? Say which.\n" +
    "\n" +
    "I accepted 2 of your changes and rejected 0.\n" +
    "\n" + TAIL);
  const alone = buildSendMessage({ absPath: ABS, comments: [], accepted: 0, rejected: 3, tracked: true });
  assert.equal(alone,
    "[obsidian-diff] I went over " + ABS + ".\n" +
    "\n" +
    "I accepted 0 of your changes and rejected 3.\n" +
    "\n" +
    "No comments this time, so nothing needs a reply.\n" +
    "When you have made more changes, ask me for another look the same way you asked for this one,\n" +
    "naming the file.\n", "decisions alone still make a message, in the decisions-only shape");
  assert.doesNotMatch(alone, /I left 0 comments/, "the retired shape's header is gone");
  assert.doesNotMatch(alone, /--thread <id>|track-reply|track-edit|To respond:/, "…and its command lines, which had no id to point at");
  assert.doesNotMatch(buildSendMessage({ absPath: ABS, comments: [{ id: "1", desc: "on this file", body: "Good." }], accepted: 0, rejected: 0, tracked: true }), /I accepted/);
});

test("the Edit refusal (Slice 2 wording): one line naming the count, saying to accept or reject first, the session's own track-edit still working", () => {
  assert.equal(editBlockedReason([h1]), "1 change is pending in this file, so Edit is off here: a direct edit would move it. Accept or reject the change first; the session's own track-edit still works.");
  assert.equal(editBlockedReason(FIVE), "5 changes are pending in this file, so Edit is off here: a direct edit would move them. Accept or reject the 5 changes first; the session's own track-edit still works.");
  assert.equal(editBlockedReason([]), null);
  assert.doesNotMatch(editBlockedReason([h1])!, /\n/, "one line");
  assert.doesNotMatch(editBlockedReason([h1])!, /next update|next slice|card|board|goal|nudge/i);
  // Slice 5: no status reply blocks Edit; the wording is the refusal trackedEdit.begin() hands the viewer. The one call left
  // is holdEdit's, for a decision this panel sent and not yet answered (file-comments-editing-races.test.ts drives it).
  const apply = SRC.split("applyStatus(s: Reply): boolean {")[1].split("\n  }\n")[0];
  assert.doesNotMatch(apply, /setEditBlocked/, "a status reply blocks nothing");
  assert.equal((SRC.match(/this\.ctx\.setEditBlocked\(/g) || []).length, 1, "the panel's one call: holdEdit's");
  assert.match(SRC, /private holdEdit\(delta: 1 \| -1\): void \{[^]*?this\.ctx\.setEditBlocked\(this\.decisionsOut \? DECISION_IN_FLIGHT : null\);/);
  assert.match(SRC, /refusal: editBlockedReason\(hunks\) \|\| "",/);
});

test("a decided change is remembered from the log: describeComment and the card keep the change's texts after Accept dropped it from the sidecar", () => {
  assert.equal(describeComment(bound, [h1]), 'on your change "reduced" to "cut"', "pending: from the hunk");
  assert.equal(describeComment(bound, [], [ACCEPT_LOG]), 'on your change "reduced" to "cut"', "decided: from the accept entry");
  assert.equal(describeComment(bound, []), "on this file", "no log, no hunk: the honest fallback");
  assert.deepEqual(decidedChange([ACCEPT_LOG], "h1"), { decision: "accepted", oldText: "reduced", newText: "cut" });
  assert.equal(decidedChange([ACCEPT_LOG], "h2"), null);
  const later: LogEntry = { ts: "2026-09-06T08:02:00Z", kind: "reject", author: "you", changes: [{ id: "h1", oldText: "reduced", newText: "cut" }] };
  assert.equal(decidedChange([ACCEPT_LOG, later], "h1")!.decision, "rejected", "the newest entry wins");
  assert.equal(decidedChange([{ ts: "", kind: "accept", author: "you", ids: ["h1"] }], "h1"), null, "an entry without the texts remembers nothing");
  const cards = cardModel({ v: 3, path: "docs/report.md", suggestions: [], comments: [bound] }, [], [ACCEPT_LOG]);
  assert.equal(cards[0].kind, "file"); assert.equal(cards[0].refs[0].state, "accepted"); assert.equal(cards[0].decision, "accepted"); assert.equal(cards[0].ref, "reduced → cut");
  const pending = cardModel({ v: 3, path: "docs/report.md", suggestions: [], comments: [bound] }, [h1], []);
  assert.equal(pending[0].decision, null); assert.deepEqual(pending[0].refs.map((r) => [r.id, r.source, r.state]), [["h1", "answered", "pending"]], "a legacy suggestionId reads as the change that answered the comment");
  // sendParts describes from the status's log too, so a manual Accept before the send keeps the change in the message
  const p = sendParts(status({ store: { v: 3, path: "docs/report.md", suggestions: [], comments: [bound] }, hunks: [], log: [ACCEPT_LOG],
    unsent: { comments: [bound.id], replies: [], accepted: 1, rejected: 0, watermark: null } }));
  assert.equal(p.comments[0].desc, 'on your change "reduced" to "cut"');
});

// ── what the stand-in cannot show, pinned at source ────────────────────────────────────────────────

test("the data-act names, all in the one delegate map; the file-writing verbs' fence; the send sequence; the third checkbox", () => {
  const map = SRC.split("delegate(row, {")[1].split("\n    });")[0];
  for (const act of ["fcaccept", "fcreject", "fcacceptall", "fcrejectall", "fcrejectallgo", "fcrejectallcancel", "fcchangecomment", "fcaboutfirst", "fcmore", "fcchange", "fcreveal"]) {
    assert.match(map, new RegExp("^\\s*" + act + ": ", "m"), act + " is a key of the one delegate map");
  }
  assert.equal((SRC.match(/\bdelegate\(/g) || []).length, 1, "still one delegate root");
  assert.match(map, /fcaccept: \(x, ev\) => \{ ev\.stopPropagation\(\); void this\.mutate\("accept", \{ ids: \[x\.dataset\.id!\] \}, "change:" \+ x\.dataset\.id!\); \}/);
  assert.match(map, /fcreject: \(x, ev\) => \{ ev\.stopPropagation\(\); void this\.mutate\("reject", \{ ids: \[x\.dataset\.id!\] \}, "change:" \+ x\.dataset\.id!\); \}/);
  assert.match(map, /void this\.mutate\("accept-all", \{\}, "changes"\)/);
  assert.match(map, /fcrejectallgo: \(\) => \{ this\.rejectAllConfirm = false; void this\.mutate\("reject-all", \{\}, "changes"\); \}/, "Reject all goes after its pane-local confirm");
  assert.match(map, /fcchange: \(x, ev\) => \{ ev\.preventDefault\(\); if \(this\.dragClick\(ev\)\) return; this\.openPanel\(\); this\.showCard\("chg:" \+ x\.dataset\.id!\); \}/,
    "an inline mark opens its card, and cancels the click: a mark inside an author's target=_blank link must not also open the tab, and one inside a URL the viewer linked (file-view-links.ts) must not open it either; the click that ends a drag-selection inside the mark opens nothing (dragClick; file-comments-markclick.test.ts)");
  assert.match(SRC, /const KEY_ACTS = new Set\(\["fccard", "fcgoto", "fcopen", "fcchange", "fclogrow", "fcaboutfirst"\]\);/, "…by keyboard too (the change card's count tag among the keyed controls since the about follow-on)");
  // the fence: fileMtimeNs for reject and reject-all ONLY, from the last status/result reply
  assert.match(SRC, /const FILE_VERBS = new Set\(\["reject", "reject-all"\]\);/);
  const once = SRC.split("private async mutateOnce(")[1].split("\n  }\n")[0];
  assert.match(once, /if \(FILE_VERBS\.has\(verb\)\) fence\.fileMtimeNs = s \? s\.fileMtimeNs : "";/);
  assert.equal((once.match(/fileMtimeNs/g) || []).length, 2, "fileMtimeNs enters the fence in that one place; mutateOnce reads nothing else off it — the re-fetch is applyStatus's");
  // the re-fetch after a reject (and after any status whose file mtime is not the view's) is ONE rule, in applyStatus:
  // the poll never will — every reply re-baselines it
  const apply = SRC.split("applyStatus(s: Reply): boolean {")[1].split("\n  }\n")[0];
  assert.match(apply, /this\.base = pollBaseline\(s\);[\s\S]*this\.syncBytes\(s\);[\s\S]*this\.paintAll\(\);/, "every applied status brings the bytes to its text, then paints");
  const sync = SRC.split("private syncBytes(s: Status): void {")[1].split("\n  }\n")[0];
  assert.match(sync, /if \(!vm \|\| !s\.fileMtimeNs \|\| vm === s\.fileMtimeNs\) return;\n\s*this\.askReload\(s\.fileMtimeNs\);\n\s*this\.awaitBytes\(s\);/,
    "the view's mtime against the status's: a re-fetch keyed on the mtime, and the loader until the paint shows it");
  assert.doesNotMatch(once, /this\.ctx\.reload\(\)/, "mutateOnce asks no fetch of its own: a moved fence's fresh status carries the file's mtime");
  assert.match(once, /await this\.refreshAfterMoved\(e\.code\);/, "a moved fence: the fresh status (and the bytes, when the file is what moved and no status lands)");
  // the send: parts first, set-tracked, the accept of the SEEN pending changes by id (decision 41: the card's own verb with
  // the ids, never an accept-all, so an unseen change stays pending), then the send with A = unsent.accepted + N and R = unsent.rejected
  const send = SRC.split("async doSend(): Promise<void> {")[1].split("\n  }\n")[0];
  const pos = (s: string) => { const i = send.indexOf(s); assert.ok(i >= 0, s); return i; };
  assert.ok(pos("const parts: SendParts = sendParts(s);") < pos('await this.mutate("set-tracked", { on: true, scope: "file" }, "send")'), "the message parts come first: a bound comment's desc needs the change the accept removes");
  assert.ok(pos('await this.mutate("set-tracked", { on: true, scope: "file" }, "send")') < pos('await this.mutate("accept", { ids: acceptIds }, "send")'), "set-tracked before the accept");
  assert.ok(pos('await this.mutate("accept", { ids: acceptIds }, "send")') < pos("await this.sendOnce(msg, false)"), "the accept before the send");
  assert.match(send, /if \(acceptIds\.length\) \{\n\s*const a = await this\.mutate\("accept", \{ ids: acceptIds \}, "send"\);\n\s*if \(!a\) return;/, "a refused accept aborts before the send; with no id to accept, no accept goes");
  assert.match(send, /const acceptIds = this\.sendOpts\.accept \? this\.pendingSplit\(s\)\.seen\.map\(\(h\) => String\(h\.id\)\) : \[\];/, "the ids: the seen pending changes' (pendingSplit), in the hunks' order; none with the box unchecked");
  assert.doesNotMatch(send, /mutate\("accept-all"/, "the send runs no accept-all: the unseen changes are not its to decide");
  assert.match(send, /accepted = decided\.length;/, "N is what the accept's reply lists");
  assert.match(send, /const counts = sendCounts\(parts, acceptIds\.length > 0, accepted\);/);
  assert.match(send, /accepted: counts\.accepted, rejected: counts\.rejected, watermark: parts\.watermark,/);
  assert.match(MODEL, /return \{ accepted: parts\.accepted \+ \(acceptPending && pending > 0 \? pending : 0\), rejected: parts\.rejected \};/);
  // the third checkbox: checked by default, offered when any change is pending (seen or not), wired through the same change listener
  assert.match(SRC, /sendOpts = \{ todo: true, track: true, accept: true \};/);
  assert.match(SRC, /if \(split\.seen\.length \+ split\.unseen\.length\) opts\.appendChild\(this\.acceptOption\(s\)\);/, "the option stands whenever a change is pending; its words and state are syncAcceptOption's");
  const syncOpt = SRC.split("private syncAcceptOption(cb: HTMLInputElement, s: Status): void {")[1].split("\n  }\n")[0];
  assert.match(syncOpt, /acceptOptionLabel\(split\.seen\.length, split\.unseen\.length\)/, "the words are the model's (acceptOptionLabel) over the seen split; an accept resolves no comment (decision 42), so no resolve count");
  assert.match(syncOpt, /cb\.disabled = split\.seen\.length === 0;/, "nothing seen: the box is off, there is nothing it may accept");
  assert.match(SRC, /else if \(k === "todo" \|\| k === "track" \|\| k === "accept"\) this\.sendOpts\[k\] = t\.checked;/, "the three checkboxes land in sendOpts…");
  assert.match(SRC, /if \(k === "todopick"\) this\.todoPick = t\.value;/, "…and the todo radio group (the todo-file follow-on) in todoPick; anything else flips nothing");
  assert.match(SRC, /const counts = sendCounts\(parts, this\.sendOpts\.accept, split\.seen\.length\);/, "the list uses the send's own counts: the seen pending changes are what the send accepts");
  // the confirm shows no message since the note box replaced the preview (2026-09-09): the panel builds none, the kernel does
  assert.doesNotMatch(SRC, /buildSendMessage\(/);
  assert.match(SRC, /cf\.appendChild\(this\.noteBox\);/, "the note box stands in the confirm");
});

test("the paint pass: unpaintChanges before each repaint, the change painters after the comment highlights, stylesFor from the colour map, the marks owned", () => {
  assert.match(SRC, /import \{ paintChangesRaw, paintChangesRendered, unpaintChanges \} from "\.\/anchor-map";/, "the D4 API by name");
  assert.match(SRC, /import type \{ MapRefusal, SourceRange, Located, ChangePaint \} from "\.\/anchor-map";/);
  const paint = SRC.split("  paintAll(): void {")[1].split("\n  }\n")[0];
  // each line is asserted PRESENT before its place is compared: a bare indexOf gives -1 for a missing line, and
  // -1 sorts before everything, so an ordering pin alone would pass with the unpaint deleted
  const pos = (s: string) => { const i = paint.indexOf(s); assert.ok(i >= 0, "paintAll has: " + s); return i; };
  assert.ok(pos("unpaintChanges(this.ctx.body());") < pos('this.unpaint(".fc-hl, .fc-presel");'), "unpaint the changes before anything is repainted");
  assert.ok(pos("this.located.set(card.id, { ...loc, painted });") < pos("this.paintChanges(root, src, rendered, true);"), "changes after the comment highlights");
  assert.ok(pos("this.paintChanges(root, src, rendered, true);") < pos("this.paintPresel(root, src, rendered);"), "…and before the composer's target");
  // every painter of the pass defers its trim of collapsed blanks (paintChanges's `true`; paintPresel always does, since its other
  // caller, repaintPresel, trims after it too since round 14), and the pass trims ONCE after the last of them: one layout for the
  // pass, not one per comment (anchor-map.ts trimCollapsedMarks; the Slice 4 review, round 12)
  assert.ok(pos("this.paintPresel(root, src, rendered);") < pos("this.trimBlanks();"), "…and the pass trims its blanks once, after every painter");
  const pc = SRC.split("private paintChanges(")[1].split("\n  }\n")[0];
  assert.match(pc, /return col && col\.color \? \{ "--fc-author": col\.color\.bg \} : \{\};/, "the author's session colour as --fc-author; nothing when unknown (the sheet's neutral)");
  assert.match(pc, /const aid = authorIdOf\(store, c\.id\);/, "the sidecar record's authorId, since toHunks drops it");
  assert.match(pc, /paintChangesRendered\(root, src, changes, stylesFor, \{ trim: !deferTrim \}\)/, "the Rendered painter trims its own marks unless the pass defers the trim"); assert.match(pc, /paintChangesRaw\(root, src, changes, stylesFor\)/);
  assert.match(pc, /if \(!s \|\| !\(s\.hunks \|\| \[\]\)\.length \|\| !this\.textCurrent\(s\)\) return;/, "offsets index the text the host read: no marks over other bytes");
  assert.match(pc, /this\.mark\(m\);/, "a change mark is the panel's own (mark: owns, and the registry the chat pane's link handler reads), like a comment highlight");
  assert.match(SRC, /const rv = btn\("Reveal", "fcreveal"\); rv\.dataset\.id = c\.key;/, "Reveal on a change card carries the card's key");
  assert.match(SRC, /if \(c\.kind === "del" \|\| !painted\) \{/, "Reveal on a deletion and on any change the view does not show");
  // the switch goes through revealInRaw since the focus follow-on's merge audit (2026-09-09): in the margin layout it
  // makes the card the focus BEFORE setMode, so the switch's own pass lays the card level with its Raw mark; the shape
  // of that method is file-comments-focus-audit.test.ts's pin, this one holds Reveal's order: Raw, then the change's start
  assert.match(SRC, /this\.revealInRaw\(key\);\n\s*this\.ctx\.scrollToOffset\(c\.curFrom\);/, "Reveal: Raw (revealInRaw), then the change's start");
  const rir = SRC.split("private revealInRaw(key: string): void {")[1].split("\n  }\n")[0];
  assert.match(rir, /this\.ctx\.setMode\("raw"\);/, "revealInRaw is the switch to Raw");
});

test("vocabulary: the person's words in the panel and the guide; CONTEXT.md's terms, never the format's", () => {
  assert.doesNotMatch(SRC, /\b(thread|suggestion|annotation)s?\b/i);
  assert.doesNotMatch(web("file-comments-changes.test.ts").split("\n").filter((l) => !l.includes("/i);")).join("\n"), /fleet/i);
  const files = GUIDE.slice(GUIDE.indexOf("### Files"), GUIDE.indexOf("## Automatic nudges")).replace(/\s+/g, " ");
  for (const phrase of ["**Accept**", "**Reject**", "**Accept all**", "**Reject all**", "**Reveal**", "accept the", "pending changes", "keeps the text", "puts the old text back"]) {
    assert.ok(files.includes(phrase), "guide Files section: " + phrase);
  }
  assert.doesNotMatch(files, /arrive with the next update/, "the Slice 1 sentence is gone");
  assert.doesNotMatch(files, /\b(suggestion|annotation)s?\b/i);
});

// ── the DOM stand-in (the behavior suite's): ancestry, attributes, events, a small selector engine ──
class Ev {
  target: El | Txt | null = null;
  currentTarget: El | null = null;
  defaultPrevented = false;
  stopped = false;
  key: string;
  ctrlKey: boolean; metaKey: boolean;
  constructor(public type: string, init: { key?: string; ctrlKey?: boolean; metaKey?: boolean } = {}) { this.key = init.key || ""; this.ctrlKey = !!init.ctrlKey; this.metaKey = !!init.metaKey; hideEdges(this); }
  preventDefault(): void { this.defaultPrevented = true; }
  stopPropagation(): void { this.stopped = true; }
}
type Listener = (ev: Ev) => void;
type Reg = { type: string; cb: Listener; capture: boolean };
const kebab = (k: string) => k.replace(/[A-Z]/g, (c) => "-" + c.toLowerCase());
class Txt {
  nodeType = 3;
  parentNode!: El | null;
  constructor(public data: string) {
    Object.defineProperty(this, "parentNode", { value: null, writable: true, enumerable: false, configurable: true });
    hideEdges(this);
  }
  get textContent(): string { return this.data; }
  get length(): number { return this.data.length; }
  get parentElement(): El | null { return this.parentNode; }
  splitText(off: number): Txt {
    const tail = new Txt(this.data.slice(off));
    this.data = this.data.slice(0, off);
    const p = this.parentNode;
    if (p) { const i = p.childNodes.indexOf(this); p.childNodes.splice(i + 1, 0, tail); tail.parentNode = p; }
    return tail;
  }
}
type Compound = { tag: string | null; classes: string[]; attrs: Array<[string, string | null]> };
function parseSel(sel: string): Compound[][] {
  return sel.split(",").map((g) => g.trim()).filter(Boolean).map((g) => g.split(/\s+/).map((s) => {
    const m = /^([a-zA-Z][\w-]*)?((?:\.[\w-]+)*)((?:\[[\w-]+(?:="[^"]*")?\])*)$/.exec(s);
    if (!m) throw new Error("stand-in: unsupported selector " + s);
    const classes = (m[2].match(/\.[\w-]+/g) || []).map((c) => c.slice(1));
    const attrs: Array<[string, string | null]> = [];
    for (const a of m[3].match(/\[[^\]]+\]/g) || []) { const am = /^\[([\w-]+)(?:="([^"]*)")?\]$/.exec(a)!; attrs.push([am[1], am[2] ?? null]); }
    return { tag: m[1] ? m[1].toUpperCase() : null, classes, attrs };
  }));
}
class El {
  nodeType = 1;
  tagName: string;
  parentNode!: El | null;
  childNodes!: Array<El | Txt>;
  attrs = new Map<string, string>();
  listeners: Reg[] = [];
  hidden = false; disabled = false; readOnly = false; title = ""; type = ""; value = ""; checked = false; placeholder = "";
  innerHTML = "";
  style: Record<string, string> = {};
  rect = { left: 0, top: 0, right: 0, bottom: 0, width: 0, height: 0 };
  constructor(tag: string) {
    this.tagName = tag.toUpperCase();
    // the tree's edges are non-enumerable, so a node inspects as its own projection and a failing assertion's dump
    // stays small (ui/test-dom-shim.ts says why); assignments later keep them hidden
    Object.defineProperty(this, "parentNode", { value: null, writable: true, enumerable: false, configurable: true });
    Object.defineProperty(this, "childNodes", { value: [], writable: true, enumerable: false, configurable: true });
    hideEdges(this);
  }
  get ownerDocument(): typeof doc { return doc; }
  get parentElement(): El | null { return this.parentNode; }
  get firstChild(): El | Txt | null { return this.childNodes[0] || null; }
  get className(): string { return this.attrs.get("class") || ""; }
  set className(v: string) { this.attrs.set("class", v); }
  get classes(): string[] { return this.className.split(/\s+/).filter(Boolean); }
  classList = {
    add: (...c: string[]) => { const s = new Set(this.classes); for (const x of c) s.add(x); this.className = [...s].join(" "); },
    remove: (...c: string[]) => { const s = new Set(this.classes); for (const x of c) s.delete(x); this.className = [...s].join(" "); },
    toggle: (c: string, on?: boolean) => { const want = on === undefined ? !this.classes.includes(c) : on; if (want) this.classList.add(c); else this.classList.remove(c); },
    contains: (c: string) => this.classes.includes(c),
  };
  get tabIndex(): number { return this.attrs.has("tabindex") ? Number(this.attrs.get("tabindex")) : -1; }
  set tabIndex(v: number) { this.attrs.set("tabindex", String(v)); }
  dataset: Record<string, string> = new Proxy({} as Record<string, string>, {
    get: (_, k) => this.attrs.get("data-" + kebab(String(k))) as string,
    set: (_, k, v) => { this.attrs.set("data-" + kebab(String(k)), String(v)); return true; },
    has: (_, k) => this.attrs.has("data-" + kebab(String(k))),
    deleteProperty: (_, k) => { this.attrs.delete("data-" + kebab(String(k))); return true; },
  });
  get textContent(): string { return this.childNodes.map((c) => c.textContent).join(""); }
  set textContent(v: string) { for (const c of this.childNodes) c.parentNode = null; this.childNodes.length = 0; if (v !== "") this.appendChild(new Txt(v)); }
  private detach(n: El | Txt): void { const p = n.parentNode; if (p) { const i = p.childNodes.indexOf(n); if (i >= 0) p.childNodes.splice(i, 1); n.parentNode = null; } }
  appendChild<T extends El | Txt>(n: T): T { this.detach(n); this.childNodes.push(n); n.parentNode = this; return n; }
  insertBefore<T extends El | Txt>(n: T, ref: El | Txt | null): T {
    if (!ref) return this.appendChild(n);
    this.detach(n);
    const i = this.childNodes.indexOf(ref);
    this.childNodes.splice(i < 0 ? this.childNodes.length : i, 0, n); n.parentNode = this; return n;
  }
  removeChild<T extends El | Txt>(n: T): T { this.detach(n); return n; }
  replaceChildren(...c: Array<El | Txt>): void { for (const x of this.childNodes) x.parentNode = null; this.childNodes.length = 0; for (const x of c) this.appendChild(x); }
  remove(): void { this.detach(this); }
  normalize(): void {
    const out: Array<El | Txt> = [];
    for (const c of this.childNodes) {
      if (c instanceof Txt) { if (!c.data) { c.parentNode = null; continue; } const last = out[out.length - 1]; if (last instanceof Txt) { last.data += c.data; c.parentNode = null; continue; } }
      else c.normalize();
      out.push(c);
    }
    this.childNodes = out;
  }
  setAttribute(k: string, v: string): void { this.attrs.set(k, v); }
  getAttribute(k: string): string | null { return this.attrs.has(k) ? (this.attrs.get(k) as string) : null; }
  hasAttribute(k: string): boolean { return this.attrs.has(k); }
  removeAttribute(k: string): void { this.attrs.delete(k); }
  contains(n: El | Txt | null): boolean { for (let x: El | Txt | null = n; x; x = x.parentNode) if (x === this) return true; return false; }
  private fits(c: Compound): boolean {
    return (!c.tag || c.tag === this.tagName) && c.classes.every((k) => this.classes.includes(k))
      && c.attrs.every(([a, v]) => this.attrs.has(a) && (v === null || this.attrs.get(a) === v));
  }
  matches(sel: string): boolean {
    return parseSel(sel).some((chain) => {
      if (!this.fits(chain[chain.length - 1])) return false;
      let k = chain.length - 2;
      for (let a: El | null = this.parentNode; a && k >= 0; a = a.parentNode) if (a.fits(chain[k])) k--;
      return k < 0;
    });
  }
  closest(sel: string): El | null { for (let x: El | null = this; x; x = x.parentNode) if (x.matches(sel)) return x; return null; }
  querySelectorAll(sel: string): El[] {
    const out: El[] = [];
    const visit = (n: El) => { for (const c of n.childNodes) if (c instanceof El) { if (c.matches(sel)) out.push(c); visit(c); } };
    visit(this);
    return out;
  }
  querySelector(sel: string): El | null { return this.querySelectorAll(sel)[0] || null; }
  addEventListener(type: string, cb: Listener, opts?: boolean | { capture?: boolean }): void {
    this.listeners.push({ type, cb, capture: typeof opts === "boolean" ? opts : !!(opts && opts.capture) });
  }
  removeEventListener(type: string, cb: Listener, opts?: boolean | { capture?: boolean }): void {
    const cap = typeof opts === "boolean" ? opts : !!(opts && opts.capture);
    this.listeners = this.listeners.filter((l) => !(l.type === type && l.cb === cb && l.capture === cap));
  }
  dispatchEvent(ev: Ev): boolean { return dispatch(this, ev); }
  click(): void { this.dispatchEvent(new Ev("click")); }
  focus(): void { doc.activeElement = this; }
  blur(): void { if (doc.activeElement === this) doc.activeElement = null; }
  scrollIntoView(): void { scrolledInto.push(this); }
  getBoundingClientRect(): typeof this.rect { return this.rect; }
  get offsetWidth(): number { return 0; }
}
const scrolledInto: El[] = [];
const doc = {
  listeners: [] as Reg[],
  body: null as unknown as El,
  hidden: false,
  activeElement: null as El | null,
  createElement: (tag: string) => new El(tag),
  createTextNode: (s: string) => new Txt(s),
  getElementById: () => null,
  addEventListener(type: string, cb: Listener, opts?: boolean | { capture?: boolean }): void {
    doc.listeners.push({ type, cb, capture: typeof opts === "boolean" ? opts : !!(opts && opts.capture) });
  },
  removeEventListener(type: string, cb: Listener, opts?: boolean | { capture?: boolean }): void {
    const cap = typeof opts === "boolean" ? opts : !!(opts && opts.capture);
    doc.listeners = doc.listeners.filter((l) => !(l.type === type && l.cb === cb && l.capture === cap));
  },
  contains: (n: El | Txt | null) => doc.body.contains(n),
};
doc.body = new El("body");
function dispatch(target: El | Txt, ev: Ev): boolean {
  ev.target = target;
  const chain: El[] = [];
  for (let n: El | null = target instanceof El ? target : target.parentNode; n; n = n.parentNode) chain.push(n);
  const run = (ls: Reg[], capture: boolean, node: El | null): boolean => {
    for (const l of ls.slice()) {
      if (l.type !== ev.type || l.capture !== capture) continue;
      ev.currentTarget = node; l.cb.call(node, ev);
      if (ev.stopped) return true;
    }
    return false;
  };
  if (run(doc.listeners, true, null)) return !ev.defaultPrevented;
  for (let i = chain.length - 1; i >= 0; i--) if (run(chain[i].listeners, true, chain[i])) return !ev.defaultPrevented;
  for (const n of chain) if (run(n.listeners, false, n)) return !ev.defaultPrevented;
  run(doc.listeners, false, null);
  return !ev.defaultPrevented;
}
const win: any = new EventTarget();
win.parent = win; win.innerWidth = 1200; win.innerHeight = 800;
win.getSelection = () => null;
win.confirm = () => true;
(globalThis as any).window = win;
(globalThis as any).document = doc;
const store = new Map<string, string>();
(globalThis as any).localStorage = {
  getItem: (k: string) => (store.has(k) ? store.get(k)! : null),
  setItem: (k: string, v: string) => { store.set(k, String(v)); },
  removeItem: (k: string) => { store.delete(k); },
};

// ── the viewer stand-in: the body row with Raw rows, the seam as closures, a file whose mtime the view tracks ──
type World = {
  ctx: FileViewActionCtx; posted: any[]; main: El; body: El; code: El;
  hooks: { rendered: Array<() => void>; close: Array<() => void> };
  disk: string; diskMtime: string; viewMtime: string; reloads: number; scrolls: number[]; modes: string[];
  mtimes: Record<string, string>;
  setText(src: string): void; close(): void;
};
let cur: World | null = null;
(globalThis as any).fetch = async (url: string) => {
  if (url.includes("/sessions")) return { json: async () => [{ id: SID, name: "api", bg: "#123456", fg: "#ffffff" }] };
  const p = decodeURIComponent((/[?&]path=([^&]*)/.exec(url) || [])[1] || "");
  const mt = cur!.mtimes[p];
  return { status: mt === undefined ? 404 : 200, headers: { get: (h: string) => (h === "X-Romp-Mtime-Ns" && mt !== undefined ? mt : null) } };
};
function rows(code: El, src: string): void {
  const lines = src.split("\n");
  if (lines.length && lines[lines.length - 1] === "") lines.pop();
  code.replaceChildren(...lines.map((ln) => {
    const cl = new El("span"); cl.className = "fv-cl";
    const ct = new El("span"); ct.className = "fv-ct";
    if (ln) ct.appendChild(new Txt(ln));
    cl.appendChild(ct);
    return cl;
  }));
}
function world(over: { todoId?: string | null; src?: string } = {}): World {
  const main = new El("div"); main.className = "fileview-main";
  const body = new El("div"); body.className = "fileview-body";
  const wrap = new El("div"); wrap.className = "fileview-code";
  const pre = new El("pre"); pre.className = "fileview-pre fileview-wrap";
  const code = new El("code"); code.className = "hljs";
  pre.appendChild(code); wrap.appendChild(pre);
  body.appendChild(wrap);
  main.appendChild(body);
  let text = over.src ?? DOC;
  const w = {
    posted: [] as any[], main, body, code,
    hooks: { rendered: [] as Array<() => void>, close: [] as Array<() => void> },
    disk: text, diskMtime: "1757145600000000001", viewMtime: "1757145600000000001", reloads: 0, scrolls: [] as number[], modes: [] as string[], mtimes: {} as Record<string, string>,
  } as World;
  rows(code, text);
  w.setText = (s) => { text = s; rows(code, s); for (const cb of w.hooks.rendered) cb(); };
  w.ctx = {
    path: ABS, sid: SID, todoId: over.todoId ?? null,
    body: () => body as unknown as HTMLElement, mode: () => "raw", text: () => text, mtimeNs: () => w.viewMtime, media: () => null, mediaElement: () => null, renderedImages: () => [], pdfPages: () => [],
    identity: () => ({ name: "api", color: null }),
    onRendered: (cb) => { w.hooks.rendered.push(cb); }, onSelection: () => { /* inert */ },
    onSaved: () => { /* inert */ }, onClose: (cb) => { w.hooks.close.push(cb); },
    post: (m) => { w.posted.push(m); }, ensureEditingAllowed: async () => true, setEditBlocked: () => { /* inert */ }, editing: () => false, setTrackedEdit: () => { /* inert */ }, guardClose: () => { /* inert */ },
    aside: (node) => { main.querySelector(".fileview-aside")?.remove(); if (node) { const n = node as unknown as El; n.classList.add("fileview-aside"); main.appendChild(n); } },
    setMode: (m) => { w.modes.push(m); }, scrollToOffset: (n) => { w.scrolls.push(n); },
    // fetchFile: the bytes and mtime now on disk, repainted, the seam's onRendered fired
    reload: () => { w.reloads++; w.viewMtime = w.diskMtime; w.setText(w.disk); },
  };
  w.close = () => { for (const cb of w.hooks.close) cb(); if (cur === w) cur = null; };
  cur = w;
  return w;
}
const flush = () => new Promise<void>((r) => setImmediate(r));
const lastOf = (w: World, type: string, verb?: string) => [...w.posted].reverse().find((m) => m.type === type && (verb === undefined || m.verb === verb));
const countOf = (w: World, type: string, verb?: string) => w.posted.filter((m) => m.type === type && (verb === undefined || m.verb === verb)).length;
function answer(w: World, s: Status, m = lastOf(w, "fileComments", "status")): void {
  assert.ok(m, "a status ask is outstanding");
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId: m.reqId, ...s } }));
  w.mtimes[w.ctx.path] = s.fileMtimeNs;
  if (s.storePath && s.storeMtimeNs !== null) w.mtimes[s.storePath] = s.storeMtimeNs;
  if (s.root && s.configMtimeNs !== null) w.mtimes[s.root + "/.trackchanges/config.json"] = s.configMtimeNs;
}
function refuse(w: World, m: any, code: string, error: string): void {
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsFailed", reqId: m.reqId, verb: m.verb, code, error } }));
}
async function openPanel(w: World, s: Status = status()): Promise<{ unit: El; button: El; aside: El }> {
  const fc = await import("./file-comments");
  const unit = fc.fileCommentsAction.mount(w.ctx) as unknown as El;
  const button = unit.childNodes[0] as El;
  answer(w, s); await flush();
  button.click();
  answer(w, s); await flush(); await flush();
  const aside = w.main.querySelector(".fileview-aside")!;
  assert.ok(aside, "the panel is mounted beside the body");
  return { unit, button, aside };
}
const card = (aside: El, key: string): El | null => aside.querySelector('.fc-card[data-id="' + key + '"]');
const act = (root: El, a: string, id?: string): El | null => root.querySelector('[data-act="' + a + '"]' + (id ? '[data-id="' + id + '"]' : ""));
const texts = (els: El[]) => els.map((e) => e.textContent);

// ── the panel, driven ──────────────────────────────────────────────────────────────────────────────

test("the change cards render first, grouped by paragraph, in text order, the buttons visible on a collapsed card; a comment naming a change is its own card, counted on the change's", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside, button } = await openPanel(w, status({ store: { v: 3, path: "docs/report.md", suggestions: SUGG, comments: [passage, bound] } }));
  assert.equal(button.textContent, "Comments · 2 · 2 changes", "the glance");
  const cards = aside.querySelectorAll(".fc-card");
  assert.deepEqual(cards.map((c) => c.dataset.id), ["chg:h1", "chg:h3", passage.id, bound.id], "changes first, then every comment's own card (the about follow-on, 2026-09-10: no comment is drawn inside a change card)");
  assert.ok(card(aside, bound.id), "the comment naming a change has a card of its own");
  assert.equal(aside.querySelector(".fc-hosted"), null, "…and no box on the change card");
  const groups = aside.querySelectorAll(".fc-group");
  assert.deepEqual(texts(groups), ["## Findings", "We recommend shipping the cache in v1.2."], "each group named by its paragraph's first line");
  const c1 = card(aside, "chg:h1")!;
  assert.equal(c1.dataset.act, "fccard", "collapsed: the whole card expands");
  assert.equal(c1.querySelector(".fc-ref")!.textContent, "reduced → cut");
  assert.equal(c1.querySelector(".fc-chip")!.textContent, "api", "the author's chip through the colour map");
  assert.deepEqual(texts(c1.querySelectorAll(".fc-actions button")), ["Accept", "Reject", "Comment on this change"], "Accept and Reject never hide; Comment on this change stands whether or not a comment names the change");
  assert.equal(c1.querySelector(".fc-count")!.textContent, "1 comment", "one comment names it, counted on the head");
  const c3 = card(aside, "chg:h3")!;
  assert.deepEqual(texts(c3.querySelectorAll(".fc-actions button")), ["Accept", "Reject", "Comment on this change", "Reveal"], "a deletion: Comment on this change and Reveal");
  assert.equal(c3.querySelector(".fc-ref")!.textContent, "removed quickly");
  assert.equal(c3.querySelector(".fc-count"), null, "no comment names it: no count");
  // expand h1: the old and new text, nothing else
  c1.querySelector(".fc-card-head")!.click();
  const open = card(aside, "chg:h1")!;
  assert.ok(open.classes.includes("open"));
  assert.equal(open.querySelector("del")!.textContent, "reduced"); assert.equal(open.querySelector("ins")!.textContent, "cut");
  assert.ok(!open.textContent.includes("Say cut, not reduced."), "the comment's words are on its own card");
  // the comment's own card: collapsed, its head says it names a change the sidecar holds; open, its turns and its own Reply/Resolve
  const own = card(aside, bound.id)!;
  assert.deepEqual(texts(own.querySelectorAll(".fc-card-head .fc-tag")), ["answered by a change", "2"], "the tag on the head (a legacy binding: the change answered it), and the turn count while collapsed");
  own.querySelector(".fc-card-head")!.click();
  const hosted = card(aside, bound.id)!;
  assert.ok(hosted.classes.includes("open"));
  assert.ok(hosted.textContent.includes("Say cut, not reduced."));
  assert.deepEqual(texts(hosted.querySelectorAll(".fc-replies .fc-tag")), ["revised"], "the session's edit turn shows as a revision row");
  assert.equal(hosted.querySelectorAll(".fc-reply del")[0].textContent, "cut"); assert.equal(hosted.querySelectorAll(".fc-reply ins")[0].textContent, "trimmed");
  assert.ok(hosted.textContent.includes("Done."), "…in ts order with the words");
  assert.ok(act(hosted, "fcreply", bound.id) && act(hosted, "fcresolve", bound.id), "the comment's own Reply and Resolve, by its id");
  // Reply on the comment is the reply verb into that comment
  act(hosted, "fcreply", bound.id)!.click();
  const input = aside.querySelector(".fc-input")!;
  assert.ok(aside.querySelector('.fc-card[data-id="' + bound.id + '"] .fc-composer'), "the box opens inside the comment's card (the reply follow-on)");
  input.value = "Trimmed is fine.";
  dispatch(input, new Ev("keydown", { key: "Enter", ctrlKey: true })); await flush();
  const m = lastOf(w, "fileComments", "reply");
  assert.deepEqual(m.args, { commentId: bound.id, note: "Trimmed is fine." });
});

test("Accept: the verb with the change's id and a sidecar fence (no fileMtimeNs); the button relabels and disables meanwhile; the reply's status renders", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside, button } = await openPanel(w);
  act(card(aside, "chg:h1")!, "fcaccept", "h1")!.click(); await flush();
  const m = lastOf(w, "fileComments", "accept");
  assert.ok(m, "the accept verb went");
  assert.deepEqual(m.args, { ids: ["h1"] });
  assert.deepEqual(m.fence, { storeMtimeNs: "1757145600000000002", configMtimeNs: "1757145600000000003" }, "accept changes the sidecar only: no file fence");
  const busy = card(aside, "chg:h1")!;
  const ok = act(busy, "fcaccept", "h1")!;
  assert.equal(ok.textContent, "Accepting…"); assert.equal(ok.disabled, true);
  assert.equal(act(busy, "fcreject", "h1")!.disabled, true, "one write in flight per card");
  assert.ok(busy.querySelector(".fc-load"), "the romp loader on the card while the verb is out");
  const after = status({ hunks: [h3], store: { v: 3, path: "docs/report.md", suggestions: [SUGG[1]], comments: [passage] },
    storeMtimeNs: "1757145600000000004", log: [ACCEPT_LOG], unsent: { comments: [passage.id], replies: [], accepted: 1, rejected: 0, watermark: null } });
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId: m.reqId, ...after } })); await flush();
  assert.equal(card(aside, "chg:h1"), null, "the accepted change is gone");
  assert.ok(card(aside, "chg:h3"));
  assert.equal(button.textContent, "Comments · 1 · 1 change");
  assert.equal(w.reloads, 0, "accept changes no bytes: no reload");
  assert.ok(aside.querySelector('[data-act="fcsend"]')!.textContent.includes("(2)"), "the decision counts toward the send");
});

test("Reject: the fence carries fileMtimeNs; a file-moved refusal re-reads status, repaints the bytes, and retries once with the fresh fence; success reloads the view", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  act(card(aside, "chg:h1")!, "fcreject", "h1")!.click(); await flush();
  const first = lastOf(w, "fileComments", "reject");
  assert.deepEqual(first.args, { ids: ["h1"] });
  assert.deepEqual(first.fence, { storeMtimeNs: "1757145600000000002", configMtimeNs: "1757145600000000003", fileMtimeNs: "1757145600000000001" }, "reject rewrites the file: the file's mtime as last seen");
  assert.equal(act(card(aside, "chg:h1")!, "fcreject", "h1")!.textContent, "Rejecting…");
  // the session's track-edit landed meanwhile: the host refuses file-moved; the panel re-asks status
  const asks = countOf(w, "fileComments", "status");
  w.disk = DOC.replace("40%", "41%"); w.diskMtime = "1757145600000000009";
  refuse(w, first, "file-moved", "~/notes-api/docs/report.md changed since the panel read it"); await flush();
  assert.equal(countOf(w, "fileComments", "status"), asks + 1, "a moved fence re-issues status");
  answer(w, status({ fileMtimeNs: "1757145600000000009", storeMtimeNs: "1757145600000000010" })); await flush(); await flush();
  assert.equal(w.reloads, 1, "the file moved under the view: its bytes are re-fetched");
  assert.equal(w.viewMtime, "1757145600000000009");
  const retry = lastOf(w, "fileComments", "reject");
  assert.notEqual(retry.reqId, first.reqId, "one retry, by the same stable id");
  assert.deepEqual(retry.args, { ids: ["h1"] });
  assert.equal(retry.fence.fileMtimeNs, "1757145600000000009", "…with the fresh file mtime");
  assert.equal(retry.fence.storeMtimeNs, "1757145600000000010");
  // the retry lands: the file is rewritten (a new mtime), the change is gone, and the view reloads once more
  w.disk = w.disk.replace("cut", "reduced"); w.diskMtime = "1757145600000000011";
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId: retry.reqId,
    ...status({ fileMtimeNs: "1757145600000000011", storeMtimeNs: "1757145600000000012", hunks: [h3], store: { v: 3, path: "docs/report.md", suggestions: [SUGG[1]], comments: [passage] },
      unsent: { comments: [passage.id], replies: [], accepted: 0, rejected: 1, watermark: null } }), verb: "reject", rejected: ["h1"] } })); await flush(); await flush();
  assert.equal(w.reloads, 2, "the reply's fileMtimeNs differs from the view's: reload (the poll never will, the reply re-baselined it)");
  assert.equal(w.viewMtime, "1757145600000000011");
  assert.equal(card(aside, "chg:h1"), null);
  assert.equal(aside.querySelectorAll(".fc-err").length, 0);
});

test("Reject refused twice: the second refusal shows verbatim under the card, with Reload; Reject all asks once, pane-locally, then goes with the file fence", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  act(card(aside, "chg:h3")!, "fcreject", "h3")!.click(); await flush();
  const first = lastOf(w, "fileComments", "reject");
  refuse(w, first, "file-moved", "~/notes-api/docs/report.md changed since the panel read it"); await flush();
  answer(w, status({ fileMtimeNs: "1757145600000000009" })); await flush(); await flush();
  const retry = lastOf(w, "fileComments", "reject");
  assert.notEqual(retry.reqId, first.reqId);
  refuse(w, retry, "file-moved", "~/notes-api/docs/report.md changed again"); await flush();
  assert.equal(countOf(w, "fileComments", "reject"), 2, "no third try");
  const err = card(aside, "chg:h3")!.querySelector(".fc-err")!;
  assert.ok(err, "the refusal is the card's own row");
  assert.ok(err.textContent.includes("~/notes-api/docs/report.md changed again"), "verbatim");
  assert.ok(act(err, "fcreload"), "a moved fence offers Reload");
  // Reject all: the confirm row names the count; Cancel closes it; the go button sends reject-all with the file fence
  act(aside, "fcrejectall")!.click();
  const ask = aside.querySelector(".fc-foot .fc-choice")!;
  assert.ok(ask, "a pane-local confirm, not a modal");
  assert.ok(ask.textContent.includes("all 2 changes"));
  assert.equal(countOf(w, "fileComments", "reject-all"), 0, "nothing sent yet");
  act(ask, "fcrejectallcancel")!.click();
  assert.equal(aside.querySelector(".fc-foot .fc-choice"), null);
  act(aside, "fcrejectall")!.click();
  act(aside, "fcrejectallgo")!.click(); await flush();
  const all = lastOf(w, "fileComments", "reject-all");
  assert.ok(all); assert.deepEqual(all.args, {});
  assert.equal(all.fence.fileMtimeNs, "1757145600000000009", "the file fence, from the LAST status");
  assert.equal(act(aside, "fcrejectall")!.textContent, "Rejecting…");
  assert.equal(act(aside, "fcacceptall")!.disabled, true);
  // Accept all carries no file fence
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId: all.reqId, ...status({ fileMtimeNs: "1757145600000000009" }) } })); await flush();
  act(aside, "fcacceptall")!.click(); await flush();
  const acc = lastOf(w, "fileComments", "accept-all");
  assert.deepEqual(acc.fence, { storeMtimeNs: "1757145600000000002", configMtimeNs: "1757145600000000003" });
});

test("Accept through the send confirm: the third checkbox, checked, names the N seen; the list carries A = unsent + N; Send runs the accept by id over the seen changes, then the send with those counts", async (t: TestContext) => {
  // the panel's first status holds both changes, so both are seen (the arrivals follow-on's rule): the accept names them by id
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w, status({ unsent: { comments: [passage.id], replies: [], accepted: 1, rejected: 0, watermark: null } }));
  act(aside, "fcsend")!.click();
  const cb = aside.querySelector('input[data-opt="accept"]')!;
  assert.ok(cb, "the third checkbox appears when changes are pending");
  assert.equal(cb.checked, true, "checked by default");
  assert.equal(cb.parentNode!.textContent, "accept the 2 pending changes you have seen");
  assert.equal(aside.querySelector('input[data-opt="track"]'), null, "the file is tracked: no tracking box");
  assert.ok(texts(aside.querySelectorAll(".fc-list li")).includes("3 accepted, 0 rejected"), "the log's 1 plus the 2 the send accepts");
  assert.equal(act(aside, "fcpreview"), null, "no message preview in the confirm (the note box took its place, 2026-09-09)");
  assert.ok(aside.querySelector(".fc-confirm .fc-send-note"), "the note box stands in the confirm");
  act(aside, "fcsendgo")!.click(); await flush();
  const acc = lastOf(w, "fileComments", "accept");
  assert.ok(acc, "the accept goes before the send");
  assert.deepEqual(acc.args, { ids: ["h1", "h3"] }, "by id, the seen pending changes in the hunks' order: the card's own verb, never an accept-all");
  assert.equal(countOf(w, "fileComments", "accept-all"), 0);
  assert.deepEqual(acc.fence, { storeMtimeNs: "1757145600000000002", configMtimeNs: "1757145600000000003" }, "the sidecar fence, as the card's accept carries it");
  assert.equal(countOf(w, "fileCommentsSend"), 0, "…and the send waits for it");
  assert.equal(countOf(w, "fileComments", "set-tracked"), 0, "already tracked: no toggle");
  const after = status({ hunks: [], store: { v: 3, path: "docs/report.md", suggestions: [], comments: [passage] }, storeMtimeNs: "1757145600000000005",
    unsent: { comments: [passage.id], replies: [], accepted: 3, rejected: 0, watermark: null } });
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId: acc.reqId, ...after, accepted: ["h1", "h3"] } })); await flush(); await flush();
  const send = lastOf(w, "fileCommentsSend");
  assert.ok(send, "then the send");
  assert.equal(send.accepted, 3); assert.equal(send.rejected, 0); assert.equal(send.tracked, true);
  assert.deepEqual(send.comments.map((c: any) => c.id), [passage.id]);
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsSent", reqId: send.reqId, queued: false } })); await flush();
  answer(w, after); await flush();
  assert.ok(aside.querySelector(".fc-sent")!.textContent.startsWith("Sent to api at "));
});

test("the accept box unchecked: no accept, the send carries the log's counts alone; a refused accept aborts before the send and shows the refusal", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  act(aside, "fcsend")!.click();
  const cb = aside.querySelector('input[data-opt="accept"]')!;
  cb.checked = false; dispatch(cb, new Ev("change"));
  assert.equal(texts(aside.querySelectorAll(".fc-list li")).some((t) => /accepted/.test(t)), false, "no decisions line with nothing to state");
  act(aside, "fcsendgo")!.click(); await flush();
  assert.equal(countOf(w, "fileComments", "accept"), 0, "unchecked: no accept goes");
  const send = lastOf(w, "fileCommentsSend");
  assert.ok(send); assert.equal(send.accepted, 0); assert.equal(send.rejected, 0);
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsSent", reqId: send.reqId, queued: false } })); await flush();
  answer(w, status()); await flush();
  // checked again, but the host refuses the accept: nothing is sent, the refusal is the send's row
  act(aside, "fcsend")!.click();
  const cb2 = aside.querySelector('input[data-opt="accept"]')!;
  assert.equal(cb2.checked, false, "the choice is remembered for the viewer");
  cb2.checked = true; dispatch(cb2, new Ev("change"));
  act(aside, "fcsendgo")!.click(); await flush();
  const acc = lastOf(w, "fileComments", "accept");
  assert.deepEqual(acc.args, { ids: ["h1", "h3"] });
  refuse(w, acc, "corrupt", "the comments for ~/notes-api/docs/report.md are not valid JSON"); await flush(); await flush();
  assert.equal(countOf(w, "fileComments", "accept"), 1, "a corrupt sidecar is no moved fence: no retry");
  assert.equal(countOf(w, "fileCommentsSend"), 1, "no second send");
  assert.ok(aside.querySelector(".fc-send .fc-err")!.textContent.includes("not valid JSON"), "the refusal, under Send");
});

/** The poll's next tick sees a moved sidecar and re-asks status; `s` answers it — a re-render from new information. */
async function repoll(w: World, t: TestContext, s: Status): Promise<void> {
  const asks = countOf(w, "fileComments", "status");
  w.mtimes[STORE_PATH] = s.storeMtimeNs!;
  t.mock.timers.tick(2500); await flush(); await flush(); await flush();
  assert.equal(countOf(w, "fileComments", "status"), asks + 1, "the poll re-read status");
  answer(w, s); await flush();
}

test("Reveal on a deletion: Raw, then the change's start; the fold past three groups, its keyed state surviving a re-render; a mark click opens a folded card", async (t: TestContext) => {
  t.mock.timers.enable({ apis: ["setInterval"] });
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w, status({ hunks: FIVE, store: { v: 3, path: "docs/report.md", suggestions: [], comments: [passage] } }));
  act(card(aside, "chg:h3")!, "fcreveal", "chg:h3")!.click();
  assert.deepEqual(w.modes, ["raw"]); assert.deepEqual(w.scrolls, [h3.curFrom]);
  assert.match(act(card(aside, "chg:h3")!, "fcreveal", "chg:h3")!.title, /line 6\)$/, "the title names the Raw line");
  // the fold: four paragraphs, three shown, the fourth's change behind one row
  assert.deepEqual(aside.querySelectorAll(".fc-card.fc-change").map((c) => c.dataset.id), ["chg:h1", "chg:h2", "chg:h3", "chg:h4"]);
  const more = act(aside, "fcmore")!;
  assert.equal(more.textContent, "… 1 more change");
  more.click();
  assert.deepEqual(aside.querySelectorAll(".fc-card.fc-change").map((c) => c.dataset.id), ["chg:h1", "chg:h2", "chg:h3", "chg:h4", "chg:h5"]);
  assert.equal(act(aside, "fcmore")!.textContent, "▾ Fewer changes");
  await repoll(w, t, status({ hunks: FIVE, store: { v: 3, path: "docs/report.md", suggestions: [], comments: [passage] }, storeMtimeNs: "1757145600000000007" }));
  assert.equal(aside.querySelectorAll(".fc-card.fc-change").length, 5, "a re-render keeps the fold open");
  act(aside, "fcmore")!.click();
  assert.equal(aside.querySelectorAll(".fc-card.fc-change").length, 4, "…and it folds back on request");
  // a click on an inline mark (whatever painter made it, it carries data-act fcchange and the id) opens the card,
  // unfolding when the card is behind the row
  const mark = w.body.querySelector('[data-act="fcchange"][data-id="h5"]');
  assert.ok(mark, "the insertion in the last paragraph is marked in the Raw view");
  assert.equal(mark!.tabIndex, 0, "a mark is a keyboard control");
  mark!.click();
  const c5 = card(aside, "chg:h5")!;
  assert.ok(c5 && c5.classes.includes("open"), "the folded card is shown and expanded");
  assert.ok(scrolledInto.includes(c5), "…and scrolled to");
  assert.ok(card(aside, "chg:h1")!.querySelector(".fc-ref")!.classes.includes("fc-link"), "a painted change's reference scrolls to its mark");
});

test("repaints over the SAME body leave one mark per change: the open (status twice, then the colours), a store-only poll tick, and an accept's reply stack nothing", async (t: TestContext) => {
  // applyStatus repaints without rebuilding the rows — only a status whose file mtime is not the view's reloads them — so
  // every status reply paints over marks already there (D5: unwrapped before each repaint, never stacked). Counted by what
  // any conforming painter yields, an element carrying data-act="fcchange" and the change's id: exactly one for an
  // insertion inside a row, at most one for a deletion's point, and for every change the same number after each repaint.
  t.mock.timers.enable({ apis: ["setInterval"] });
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w, status({ hunks: FIVE }));
  const marks = (id: string) => w.body.querySelectorAll('[data-act="fcchange"][data-id="' + id + '"]').length;
  const counts = () => Object.fromEntries(FIVE.map((h) => [h.id, marks(h.id)]));
  assert.equal(w.reloads, 0, "the rows were never rebuilt: the open's paints all went over the same body");
  assert.equal(marks("h2"), 1, "an insertion is marked once after the open's repaints");
  assert.equal(marks("h5"), 1);
  assert.ok(marks("h3") <= 1, "a deletion's point, when the painter draws one, is one element");
  for (const h of FIVE) assert.ok(marks(h.id) >= 1, h.id + " is painted");
  const first = counts();
  // the poll: the sidecar moved and the file did not — the status lands and the same rows are repainted
  await repoll(w, t, status({ hunks: FIVE, storeMtimeNs: "1757145600000000007" }));
  assert.equal(w.reloads, 0, "a store-only move rebuilds nothing");
  assert.deepEqual(counts(), first, "the poll's repaint stacks no mark");
  assert.equal(marks("h5"), 1);
  // an accept: the reply's status repaints; the accepted change's marks are gone, the rest are as before
  act(card(aside, "chg:h1")!, "fcaccept", "h1")!.click(); await flush();
  const m = lastOf(w, "fileComments", "accept");
  assert.ok(m, "the accept verb went");
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId: m.reqId, ...status({ hunks: [h2, h3, h4, h5],
    store: { v: 3, path: "docs/report.md", suggestions: [SUGG[1]], comments: [passage] }, storeMtimeNs: "1757145600000000008", log: [ACCEPT_LOG],
    unsent: { comments: [passage.id], replies: [], accepted: 1, rejected: 0, watermark: null } }) } })); await flush();
  assert.equal(w.reloads, 0, "an accept changes no bytes: the same rows again");
  assert.equal(card(aside, "chg:h1"), null, "the accepted change's card is gone");
  assert.deepEqual(counts(), { ...first, h1: 0 }, "…its marks with it, and every other change is painted as before");
});

test("Comment on this change writes a comment about the change: comment {anchor over the change's span, changeIds: [id], note}, no suggestionId; the saved comment is its own card and the change card counts it", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  act(card(aside, "chg:h1")!, "fcchangecomment", "h1")!.click();
  assert.ok(card(aside, "chg:h1")!.classes.includes("open"), "the card opens for it");
  assert.equal(aside.querySelector(".fc-composer-ref .fc-quote")!.textContent, "cut", "the composer is anchored over the change's new text");
  assert.equal(aside.querySelector('input[data-opt="about"]')!.checked, true, "the about option, checked");
  const input = aside.querySelector(".fc-input")!;
  input.value = "Keep reduced; the abstract uses it.";
  dispatch(input, new Ev("keydown", { key: "Enter", ctrlKey: true })); await flush();
  const m = lastOf(w, "fileComments", "comment");
  assert.ok(m, "the comment verb went");
  assert.deepEqual(m.args, { note: "Keep reduced; the abstract uses it.", anchor: { quote: "cut", prefix: DOC.slice(at("cut") - 24, at("cut")), suffix: DOC.slice(at("cut") + 3, at("cut") + 27) }, hintOffset: at("cut"), changeIds: ["h1"] }, "about the change by its stored id (decision 45), the passage anchor beside it, never suggestionId");
  assert.deepEqual(m.fence, { storeMtimeNs: "1757145600000000002", configMtimeNs: "1757145600000000003" });
  const withComment: StoreComment = { id: T0 + 5000 + "-" + at("cut"), author: "you", ts: T0 + 5000, anchor: m.args.anchor, anchorAt: at("cut"), changeIds: ["h1"], body: "Keep reduced; the abstract uses it.", replies: [], resolved: false };
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId: m.reqId, ...status({ store: { v: 3, path: "docs/report.md", suggestions: SUGG, comments: [passage, withComment] },
    storeMtimeNs: "1757145600000000006", unsent: { comments: [passage.id, withComment.id], replies: [], accepted: 0, rejected: 0, watermark: null } }) } })); await flush();
  assert.equal(card(aside, "chg:h1")!.querySelector(".fc-hosted"), null, "the new comment is not drawn inside the change card");
  assert.ok(card(aside, withComment.id), "…it is its own card");
  assert.deepEqual(texts(card(aside, withComment.id)!.querySelectorAll(".fc-card-head .fc-tag")), ["about a change"]);
  assert.equal(card(aside, "chg:h1")!.querySelector(".fc-count")!.textContent, "1 comment");
  assert.ok(act(card(aside, "chg:h1")!, "fcchangecomment", "h1"), "Comment on this change stands for the next comment about it");
  assert.equal(aside.querySelector(".fc-composer")!.hidden, true, "saved: the composer closes");
});

test("a Log accept row opens to the changes it decided (old → new), one click down, keyed so a re-render keeps it", async (t: TestContext) => {
  t.mock.timers.enable({ apis: ["setInterval"] });
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w, status({ hunks: [h3], log: [ACCEPT_LOG] }));
  act(aside, "fclog")!.click();
  const row = aside.querySelector(".fc-log-row")!;
  assert.equal(row.dataset.act, "fclogrow");
  assert.equal(row.title, "Show the changes");
  assert.ok(row.textContent.includes("Accepted 1 change"));
  row.click();
  const detail = aside.querySelector(".fc-log-detail")!;
  assert.ok(detail);
  assert.equal(detail.querySelector("del")!.textContent, "reduced"); assert.equal(detail.querySelector("ins")!.textContent, "cut");
  await repoll(w, t, status({ hunks: [h3], log: [ACCEPT_LOG], storeMtimeNs: "1757145600000000008" }));
  assert.ok(aside.querySelector(".fc-log-detail"), "still open after the re-render");
});

// The stand-in's nodes inspect as their own projection, never as the tree: every edge (parentNode, childNodes, the
// attribute map, the listener table, style, dataset, classList) is non-enumerable, so a failing assertion's dump of a
// node is a few lines, not the whole document (ui/test-dom-shim.ts says why; ui/test-dom-shim.test.ts keeps the ratchet).
test("stand-in: a node enumerates its primitives alone and inspects without its edges", () => {
  const root = doc.createElement("div");
  const kid = root.appendChild(doc.createElement("span"));
  kid.appendChild(doc.createTextNode("leaf"));
  kid.setAttribute("data-id", "k1");
  for (const n of [root, kid, kid.firstChild!]) {
    const o = n as unknown as Record<string, unknown>;
    assert.ok(Object.keys(o).every((k) => staysEnumerable(o[k])), "only primitives enumerate on " + n.constructor.name + ": " + Object.keys(o).join(","));
    const dump = inspect(n, { compact: false, customInspect: false, depth: 1000, maxArrayLength: Infinity, showHidden: false, showProxy: false, sorted: true, getters: true });
    assert.ok(!dump.includes("parentNode") && !dump.includes("childNodes"), "no edge in the dump of " + n.constructor.name);
  }
  assert.equal(kid.parentNode, root); assert.equal(root.childNodes.length, 1); assert.equal(kid.textContent, "leaf");
});

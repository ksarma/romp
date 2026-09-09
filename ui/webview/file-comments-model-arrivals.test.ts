// The arrivals' pure half (plans/file-review.md, "The arrivals follow-on (2026-09-09)" under Slice 2; file-comments-model.ts
// statusEntries, arrivalsAmong, arrivalWords, acceptOptionLabel). The panel keeps the set of entries the person has seen; the
// model says what a status's entries are, which of them are arrivals against that set — another author's, not seen; never the
// person's own writes (YOU, decision 6's label) — and the words of the line under the header and of the Send confirm's
// accept option. The panel's use of them, over the stand-in, is file-comments-arrivals.test.ts. Synthetic fixtures only:
// the notes-api world, placeholder ids, the session names "api" and "web".
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { statusEntries, arrivalsAmong, arrivalWords, acceptOptionLabel, resolvedByAccept, sentNoteWords, YOU, type Entry, type Status, type StoreComment, type Hunk } from "./file-comments-model";

const SID = "11111111-2222-3333-4444-555555555555";
const SID2 = "22222222-3333-4444-5555-666666666666";
const T0 = 1757145600000;
const mine: StoreComment = { id: T0 + "-1", author: "you", ts: T0, body: "Which cache?", anchor: { quote: "the cache", prefix: "shipping ", suffix: " in" }, replies: [
  { author: "api", authorId: SID, ts: T0 + 1000, body: "The query cache." },
  { author: "you", ts: T0 + 2000, body: "Say so in the text." },
], resolved: false };
const theirs: StoreComment = { id: (T0 + 3000) + "-2", author: "api", authorId: SID, ts: T0 + 3000, body: "Is this line current?", replies: [], resolved: false };
const h1: Hunk = { id: "h1", author: "api", ts: T0 + 4000, kind: "ins", curFrom: 10, curTo: 20, baseFrom: 10, baseTo: 10, oldText: "", newText: "ten chars.", anchor: null };
const h2: Hunk = { id: "h2", author: "web", ts: T0 + 5000, kind: "del", curFrom: 40, curTo: 40, baseFrom: 40, baseTo: 45, oldText: "gone.", newText: "", anchor: null };
const detached = { id: "h9", author: "api", authorId: SID, ts: T0 + 100, kind: "sub", from: 5, oldText: "old", newText: "new" };
const status = (over: Partial<Status> = {}): Pick<Status, "store" | "hunks"> => ({
  store: { v: 3, path: "docs/report.md", suggestions: [{ id: "h1", authorId: SID }, { id: "h2", authorId: SID2 }], comments: [mine, theirs], detached: [detached] },
  hunks: [h1, h2], ...over,
});
const keys = (es: Entry[]): string[] => es.map((e) => e.key);
const byLabel = (author: string): string => author;

test("statusEntries: the pending changes, the detached changes, the comments and their replies, each keyed and with its author, its subject and whether it is pending", () => {
  const es = statusEntries(status());
  assert.deepEqual(keys(es), ["chg:h1", "chg:h2", "chg:h9", mine.id, mine.id + "|" + (T0 + 1000), mine.id + "|" + (T0 + 2000), theirs.id]);
  const by = new Map(es.map((e) => [e.key, e]));
  assert.deepEqual(by.get("chg:h1"), { key: "chg:h1", kind: "change", author: "api", authorId: SID, subject: "chg:h1", pending: true });
  assert.deepEqual(by.get("chg:h2"), { key: "chg:h2", kind: "change", author: "web", authorId: SID2, subject: "chg:h2", pending: true }, "the change's authorId is the sidecar record's (authorIdOf)");
  assert.deepEqual(by.get("chg:h9"), { key: "chg:h9", kind: "change", author: "api", authorId: SID, subject: "chg:h9", pending: false }, "a detached change is an entry and not pending");
  assert.deepEqual(by.get(mine.id), { key: mine.id, kind: "comment", author: "you", authorId: null, subject: mine.id, pending: false });
  assert.deepEqual(by.get(mine.id + "|" + (T0 + 1000)), { key: mine.id + "|" + (T0 + 1000), kind: "reply", author: "api", authorId: SID, subject: mine.id, pending: false }, "a reply's subject is its comment");
  assert.deepEqual(by.get(theirs.id), { key: theirs.id, kind: "comment", author: "api", authorId: SID, subject: theirs.id, pending: false });
  assert.deepEqual(statusEntries(null), []);
  assert.deepEqual(statusEntries({ store: null, hunks: [] }), []);
});

test("arrivalsAmong: another author's entries not in the seen set; the person's own never, whatever the set holds; an empty set against the first status is the panel's to avoid (it seeds the set with all of it)", () => {
  const es = statusEntries(status());
  assert.equal(YOU, "you", "decision 6's label");
  const none = arrivalsAmong(es, new Set(keys(es)));
  assert.deepEqual(none, [], "everything seen: nothing arrives");
  const all = arrivalsAmong(es, new Set());
  assert.deepEqual(keys(all), ["chg:h1", "chg:h2", "chg:h9", mine.id + "|" + (T0 + 1000), theirs.id], "against an empty set every entry of another author's, in the status's order; the person's comment and reply never");
  const some = arrivalsAmong(es, new Set(["chg:h1", "chg:h9", theirs.id]));
  assert.deepEqual(keys(some), ["chg:h2", mine.id + "|" + (T0 + 1000)]);
});

test("arrivalWords: the counts by kind — changes, comments, replies — singular when one, joined as a list, after the authors' names as the chips show them, distinct and joined with and", () => {
  const e = (kind: Entry["kind"], author: string, authorId: string | null = SID, n = 0): Entry => ({ key: kind + n + author, kind, author, authorId, subject: "s", pending: kind === "change" });
  const many = (kind: Entry["kind"], author: string, n: number): Entry[] => Array.from({ length: n }, (_, i) => e(kind, author, SID, i));
  assert.equal(arrivalWords([...many("change", "api", 11), ...many("reply", "api", 7)], byLabel), "api made 11 changes and 7 replies since you last looked", "the report's own numbers");
  assert.equal(arrivalWords([e("change", "api"), e("comment", "api"), e("reply", "api")], byLabel), "api made 1 change, 1 comment and 1 reply since you last looked");
  assert.equal(arrivalWords([...many("comment", "api", 2)], byLabel), "api made 2 comments since you last looked");
  assert.equal(arrivalWords([e("reply", "api")], byLabel), "api made 1 reply since you last looked");
  assert.equal(arrivalWords([e("change", "api", SID, 1), e("reply", "web", SID2, 2)], byLabel), "api and web made 1 change and 1 reply since you last looked", "two authors");
  assert.equal(arrivalWords([e("change", "api", SID, 1), e("reply", "web", SID2, 2), e("comment", "tests", null, 3), e("reply", "api", SID, 4)], byLabel), "api, web and tests made 1 change, 1 comment and 2 replies since you last looked", "three, each once, in first-appearance order");
  // the name comes from the caller: the session's current name by its id when the panel knows it, the label otherwise
  const nameOf = (author: string, authorId: string | null): string => (authorId === SID ? "notes-api" : author);
  assert.equal(arrivalWords([e("change", "api", SID, 1), e("reply", "web", SID2, 2)], nameOf), "notes-api and web made 1 change and 1 reply since you last looked");
  assert.equal(arrivalWords([], byLabel), "", "nothing to say");
});

test("acceptOptionLabel: the Send confirm's accept option as before, and with the pending changes that arrived named after it", () => {
  assert.equal(acceptOptionLabel(2, 0), "accept the 2 pending changes");
  assert.equal(acceptOptionLabel(1, 0), "accept the 1 pending change");
  assert.equal(acceptOptionLabel(2, 1), "accept the 2 pending changes (1 arrived since you last looked)");
  assert.equal(acceptOptionLabel(11, 11), "accept the 11 pending changes (11 arrived since you last looked)");
  assert.equal(acceptOptionLabel(1, 1), "accept the 1 pending change (1 arrived since you last looked)");
});

test("acceptOptionLabel with the comments the accept resolves (the lost-update probe, 2026-09-09): one parenthesis, the resolve first, joined with a semicolon", () => {
  assert.equal(acceptOptionLabel(2, 0, 1), "accept the 2 pending changes (resolves 1 comment)");
  assert.equal(acceptOptionLabel(11, 0, 7), "accept the 11 pending changes (resolves 7 comments)");
  assert.equal(acceptOptionLabel(11, 3, 7), "accept the 11 pending changes (resolves 7 comments; 3 arrived since you last looked)");
  assert.equal(acceptOptionLabel(2, 0, 0), "accept the 2 pending changes");
});

test("resolvedByAccept: the unresolved comments bound to a pending change; a resolved one, one bound to a detached or decided change, and an unbound one count for nothing", () => {
  const bound = (id: string, sug: string, resolved = false): StoreComment => ({ id, author: "you", ts: T0, body: "b", suggestionId: sug, resolved, replies: [] });
  const store = { v: 3, path: "docs/report.md", suggestions: [], comments: [bound("c1", "h1"), bound("c2", "h1"), bound("c3", "h2", true), bound("c4", "h9"), mine] };
  assert.equal(resolvedByAccept(store, [h1, h2]), 2, "two open comments on h1; the one on h2 is resolved already; h9 is not pending; the plain comment is unbound");
  assert.equal(resolvedByAccept(store, []), 0);
  assert.equal(resolvedByAccept(null, [h1]), 0);
});

test("sentNoteWords: the base alone when nothing moved; with what the accept moved to Resolved otherwise", () => {
  assert.equal(sentNoteWords("Sent to api at 10:32", 2, 0), "Sent to api at 10:32");
  assert.equal(sentNoteWords("Sent to api at 10:32", 2, 1), "Sent to api at 10:32 · accepted 2 changes; 1 comment with the session's replies moved to Resolved");
  assert.equal(sentNoteWords("Queued for api", 11, 7), "Queued for api · accepted 11 changes; 7 comments with the session's replies moved to Resolved");
  assert.equal(sentNoteWords("Sent to api at 10:32", 1, 1), "Sent to api at 10:32 · accepted 1 change; 1 comment with the session's replies moved to Resolved");
});

test("vocabulary: no romp nouns in the words a person reads here, and none of the words CONTEXT.md sets aside", () => {
  const texts = [arrivalWords([{ key: "k", kind: "change", author: "api", authorId: SID, subject: "s", pending: true }], byLabel), acceptOptionLabel(3, 2, 1), sentNoteWords("Sent to api at 10:32", 3, 1)];
  for (const t of texts) {
    assert.doesNotMatch(t, /\b(card|board|goal|column|nudge|fleet)\b/i, t);
    assert.doesNotMatch(t, /\b(suggestion|diff|thread|annotation)\b/i, t);
  }
});

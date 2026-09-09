// An edit turn is not a reply (the arrivals follow-on, plans/file-review.md under Slice 2). When a session answers a comment
// with `track-edit --thread <id>`, the sidecar records the op (a hunk in the status, the change) and pushes a `kind: "edit"`
// record with no `body` into the comment's replies (vendor/track-changents/store-io.mjs addThreadEditTurn); cardModel renders
// that record as a "rev" turn ("revised"), never as words. statusEntries used to file it as a reply too, so one edit answering
// a comment read "1 change and 1 reply" under the header and the incident's eleven edits answering comments plus seven word
// replies read "11 changes and 18 replies". Now a reply entry is a record with words; the edit turn's change is the entry.
// Synthetic fixtures only: the notes-api world, placeholder ids, the session name "api".
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { statusEntries, arrivalsAmong, arrivalWords, type Entry, type Status, type StoreComment, type StoreReply, type Hunk } from "./file-comments-model";

const SID = "11111111-2222-3333-4444-555555555555";
const T0 = 1757145600000;
const keys = (es: Entry[]): string[] => es.map((e) => e.key);
const byLabel = (author: string): string => author;
const editTurn = (ts: number): StoreReply => ({ author: "api", authorId: SID, ts, kind: "edit", oldText: "the cache", newText: "the query cache" });
const wordReply = (ts: number): StoreReply => ({ author: "api", authorId: SID, ts, body: "Made it the query cache." });
const hunk = (id: string, ts: number): Hunk => ({ id, author: "api", ts, kind: "sub", curFrom: 10, curTo: 25, baseFrom: 10, baseTo: 19, oldText: "the cache", newText: "the query cache", anchor: null });
const status = (comments: StoreComment[], hunks: Hunk[]): Pick<Status, "store" | "hunks"> => ({
  store: { v: 3, path: "docs/report.md", suggestions: hunks.map((h) => ({ id: h.id, authorId: SID })), comments, detached: [] },
  hunks,
});

test("one edit answering the person's comment: the hunk is the entry, the comment's edit turn is not a reply, and the line reads 1 change", () => {
  const mine: StoreComment = { id: T0 + "-1", author: "you", ts: T0, body: "Which cache?", suggestionId: "h2", replies: [editTurn(T0 + 1000)], resolved: false };
  const before = statusEntries(status([{ ...mine, suggestionId: undefined, replies: [] }], []));
  const seen = new Set(keys(before));
  assert.deepEqual(Array.from(seen), [mine.id], "the panel's first status: the comment alone, seen");
  const es = statusEntries(status([mine], [hunk("h2", T0 + 1000)]));
  assert.deepEqual(keys(es), ["chg:h2", mine.id], "no reply entry for the edit turn");
  const arrivals = arrivalsAmong(es, seen);
  assert.deepEqual(keys(arrivals), ["chg:h2"]);
  assert.equal(arrivalWords(arrivals, byLabel), "api made 1 change since you last looked", "not '1 change and 1 reply': no reply was written");
});

test("the incident's shape: eleven edits answering comments and seven replies in words read 11 changes and 7 replies, not 18 replies", () => {
  const comments: StoreComment[] = [];
  const hunks: Hunk[] = [];
  for (let i = 0; i < 11; i++) {
    const id = "h" + (i + 1);
    hunks.push(hunk(id, T0 + 1000 * (i + 1)));
    comments.push({ id: T0 + "-" + (i + 1), author: "you", ts: T0 + i, body: "Comment " + i, suggestionId: id, replies: [editTurn(T0 + 1000 * (i + 1))], resolved: false });
  }
  for (let i = 0; i < 7; i++) {
    comments.push({ id: T0 + "-" + (20 + i), author: "you", ts: T0 + 20 + i, body: "Question " + i, replies: [wordReply(T0 + 50000 + i)], resolved: false });
  }
  const seen = new Set(comments.map((c) => c.id));                         // the person's comments, seen when written
  const arrivals = arrivalsAmong(statusEntries(status(comments, hunks)), seen);
  assert.equal(arrivals.filter((e) => e.kind === "change").length, 11);
  assert.equal(arrivals.filter((e) => e.kind === "reply").length, 7);
  assert.equal(arrivalWords(arrivals, byLabel), "api made 11 changes and 7 replies since you last looked");
});

test("a comment's replies in words are entries, an edit turn between them is not, and a record with neither words nor an edit (nothing shown) is not either", () => {
  const c: StoreComment = { id: T0 + "-1", author: "you", ts: T0, body: "Which cache?", suggestionId: "h2", resolved: false, replies: [
    wordReply(T0 + 1000),
    editTurn(T0 + 2000),
    { author: "api", authorId: SID, ts: T0 + 3000 } as StoreReply,
    { author: "you", ts: T0 + 4000, body: "Good." },
  ] };
  const es = statusEntries(status([c], [hunk("h2", T0 + 2000)]));
  assert.deepEqual(keys(es), ["chg:h2", c.id, c.id + "|" + (T0 + 1000), c.id + "|" + (T0 + 4000)]);
  assert.deepEqual(es.filter((e) => e.kind === "reply").map((e) => e.author), ["api", "you"]);
  // the edit turn's change is where the arrival shows: the hunk's card, which the bound comment's card is
  const arrivals = arrivalsAmong(es, new Set([c.id, c.id + "|" + (T0 + 4000)]));
  assert.deepEqual(keys(arrivals), ["chg:h2", c.id + "|" + (T0 + 1000)]);
  assert.deepEqual(arrivals.map((e) => e.subject), ["chg:h2", c.id]);
});

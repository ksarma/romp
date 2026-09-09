// The seen-only accept's pure half (plans/file-review.md, decision 41 and "The seen follow-on (2026-09-09)" under Slice 2;
// file-comments-model.ts partitionPending, acceptOptionLabel). The Send confirm's accept option used to accept every pending
// change; it now accepts the ones the person has SEEN — a change whose card or mark was on screen at one of their gestures,
// the arrivals follow-on's rule — and leaves the unseen ones pending. The model splits a status's pending changes against the
// panel's seen set and gives the option its words; the panel's use of both, over the stand-in, is
// file-comments-send-seen.test.ts. Synthetic fixtures only: placeholder ids, the session names "api" and "web".
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { partitionPending, acceptOptionLabel, statusEntries, type Hunk } from "./file-comments-model";

const SID = "11111111-2222-3333-4444-555555555555";
const T0 = 1757145600000;
const h1: Hunk = { id: "h1", author: "api", ts: T0 + 4000, kind: "ins", curFrom: 10, curTo: 20, baseFrom: 10, baseTo: 10, oldText: "", newText: "ten chars.", anchor: null };
const h2: Hunk = { id: "h2", author: "web", ts: T0 + 5000, kind: "del", curFrom: 40, curTo: 40, baseFrom: 40, baseTo: 45, oldText: "gone.", newText: "", anchor: null };
const h3: Hunk = { id: "h3", author: "api", ts: T0 + 6000, kind: "sub", curFrom: 50, curTo: 53, baseFrom: 50, baseTo: 53, oldText: "old", newText: "new", anchor: null };
const ids = (hs: Hunk[]): string[] => hs.map((h) => h.id);

test("partitionPending: a pending change is seen when the set holds its entry key, unseen otherwise; each side keeps the hunks' order", () => {
  const seen = new Set(["chg:h1", "chg:h3", (T0 + 1) + "-0"]);
  const split = partitionPending([h1, h2, h3], seen);
  assert.deepEqual(ids(split.seen), ["h1", "h3"]);
  assert.deepEqual(ids(split.unseen), ["h2"]);
  assert.deepEqual(partitionPending([h2, h1], seen), { seen: [h1], unseen: [h2] });
  assert.deepEqual(partitionPending([], seen), { seen: [], unseen: [] }, "nothing pending: both sides empty");
  assert.deepEqual(partitionPending([h1, h2], new Set()), { seen: [], unseen: [h1, h2] }, "an empty set: all unseen");
});

test("partitionPending reads the key statusEntries writes for a change, so the panel's set and the split agree", () => {
  const es = statusEntries({ store: { v: 3, path: "docs/report.md", suggestions: [{ id: "h1", authorId: SID }], comments: [] }, hunks: [h1] });
  assert.equal(es.length, 1);
  assert.deepEqual(partitionPending([h1], new Set([es[0].key])), { seen: [h1], unseen: [] });
});

test("partitionPending with no set yet (the panel before its first render with a status): nothing counts as seen", () => {
  assert.deepEqual(partitionPending([h1, h2], null), { seen: [], unseen: [h1, h2] });
});

test("acceptOptionLabel: the seen count and 'you have seen'; the unseen count after it, staying pending; singulars", () => {
  assert.equal(acceptOptionLabel(2, 0), "accept the 2 pending changes you have seen");
  assert.equal(acceptOptionLabel(1, 0), "accept the 1 pending change you have seen");
  assert.equal(acceptOptionLabel(2, 1), "accept the 2 pending changes you have seen (1 unseen stays pending)");
  assert.equal(acceptOptionLabel(1, 3), "accept the 1 pending change you have seen (3 unseen stay pending)");
  assert.equal(acceptOptionLabel(11, 11), "accept the 11 pending changes you have seen (11 unseen stay pending)");
});

test("acceptOptionLabel with nothing seen: no count to accept; the words say every pending change is unseen and that nothing is accepted until the person looks", () => {
  assert.equal(acceptOptionLabel(0, 3), "accept the pending changes you have seen (all 3 pending changes are unseen; nothing is accepted until you look)");
  assert.equal(acceptOptionLabel(0, 1), "accept the pending changes you have seen (the 1 pending change is unseen; nothing is accepted until you look)");
});

test("acceptOptionLabel takes two counts: an accept resolves no comment (decision 42), so the option has no resolve clause", () => {
  assert.equal(acceptOptionLabel.length, 2);
  for (const [seen, unseen] of [[2, 0], [2, 1], [0, 3]] as Array<[number, number]>) assert.ok(!acceptOptionLabel(seen, unseen).includes("resolves"));
});

test("the option never says 'arrived since you last looked': the unseen pending changes are the arrivals line's count, said once there", () => {
  for (const [s, u] of [[2, 1], [0, 2], [1, 1], [3, 0]] as Array<[number, number]>) assert.ok(!acceptOptionLabel(s, u).includes("arrived"), acceptOptionLabel(s, u));
});

test("vocabulary: no romp nouns in the words a person reads here, and none of the words CONTEXT.md sets aside", () => {
  for (const t of [acceptOptionLabel(3, 2), acceptOptionLabel(0, 2), acceptOptionLabel(1, 0)]) {
    assert.doesNotMatch(t, /\b(card|board|goal|column|nudge|fleet)\b/i, t);
    assert.doesNotMatch(t, /\b(suggestion|diff|thread|annotation)\b/i, t);
  }
});

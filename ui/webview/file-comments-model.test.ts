// sendParts()'s reply key. The status reply's `unsent.replies` names each unsent reply by
// (commentId, ts), and sendParts() joins the pair into one Set key to look each stored reply up. The
// key has a separator ("\0", the two-character escape, never the raw byte — a raw NUL in a small module
// sits inside git's binary sniff window and turns the source into a `Bin` blob that the privacy scans skip;
// file-comments-model-text-source.test.ts pins the source form) because comment ids are `<ts>-<n>` and a
// reply's ts is a number: two different pairs concatenate to the same string once the digits run
// together, so a bare `commentId + ts` key would send a reply the log never listed. file-comments.test.ts
// covers what one Send hands over; this pins the collision the separator is there for.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { type Status, type StoreComment, type Unsent, sendParts } from "./file-comments-model";

const T0 = 1757145600000;                              // 2026-09-06T08:00:00Z, as the CLIs stamp `ts`

// Two comments on the notes-api report whose id + reply-ts concatenations coincide: "<id>-1" + "18" and
// "<id>-11" + "8" both read "<id>-118". The reply timestamps are chosen for that, not for realism.
const first: StoreComment = {
  id: T0 + "-1", author: "you", ts: T0, body: "Name the cache.", anchor: null, resolved: false,
  replies: [{ author: "you", ts: 18, body: "The read cache, the one v1.2 ships." }],
};
const second: StoreComment = {
  id: T0 + "-11", author: "you", ts: T0 + 1000, body: "Cut the chart.", anchor: null, resolved: false,
  replies: [{ author: "you", ts: 8, body: "And the table under it." }],
};
assert.equal(first.id + first.replies![0].ts, second.id + second.replies![0].ts, "the fixture's premise: the bare concatenations collide");

function status(unsent: Partial<Unsent>): Status {
  return {
    verb: "status", root: "/repo/notes-api", storePath: "/repo/notes-api/.trackchanges/docs/report.md.json",
    trackedBy: { kind: "file", entry: "docs/report.md" }, agentTooling: "present",
    fileMtimeNs: "1757145600000000000", storeMtimeNs: "1757145600000000000", configMtimeNs: null,
    store: { v: 3, path: "docs/report.md", suggestions: [], comments: [first, second] }, hunks: [], log: [],
    unsent: { comments: [], replies: [], accepted: 0, rejected: 0, watermark: null, ...unsent },
  };
}

test("sendParts: the reply key tells (commentId, ts) pairs apart whose concatenations coincide", () => {
  const onlyFirst = sendParts(status({ replies: [{ commentId: first.id, ts: 18 }] }));
  assert.deepEqual(onlyFirst.comments, [{ id: first.id, desc: "on this file", body: "The read cache, the one v1.2 ships." }],
    "the second comment's reply, unlisted by the log, stays home");
  assert.equal(onlyFirst.watermark, 18, "the watermark covers what goes, not the look-alike");

  const onlySecond = sendParts(status({ replies: [{ commentId: second.id, ts: 8 }] }));
  assert.deepEqual(onlySecond.comments, [{ id: second.id, desc: "on this file", body: "And the table under it." }]);
  assert.equal(onlySecond.watermark, 8);

  const both = sendParts(status({ replies: [{ commentId: first.id, ts: 18 }, { commentId: second.id, ts: 8 }] }));
  assert.deepEqual(both.comments.map((c) => c.id), [first.id, second.id], "listed together, both go, oldest comment first");
});

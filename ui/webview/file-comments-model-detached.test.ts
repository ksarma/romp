// The Comments panel's DETACHED changes (plans/file-review.md, the contract: a host "preserves and shows rather
// than drops" the ops the load-time rebase could not re-place; Risks: a rebase, a checkout, or an outside editor
// detaches). The pure model runs for real: the sidecar's `detached[]` read defensively, one card per detached
// change after the pending ones with `detached: true`, their own titled group after the paragraphs, the glance
// counting them, and a comment bound to a detached change riding its card and described by the change's texts in
// the message. What the model cannot show is pinned at source: the panel renders every card changeCards returns
// and its empty line yields to them, and the vendored store-io keeps detached ops on load and keeps the sidecar for
// them. Before this, a change the rebase detached vanished from the panel and the count while its record stayed
// on disk — and came back, unasked, if its text returned. Synthetic fixtures only: the notes-api world,
// placeholder ids.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import {
  type Status, type Store, type Hunk, type StoreComment, type LogEntry,
  changeCards, changeGroups, foldGroups, moreChangesLabel, GROUP_LIMIT, DETACHED_GROUP_KEY, DETACHED_GROUP_TITLE,
  detachedChanges, boundChange, cardModel, describeComment, sendParts, actionLabel, changeRef,
} from "./file-comments-model";

const REPO = path.resolve(process.cwd(), "..");
const read = (...p: string[]) => fs.readFileSync(path.join(REPO, ...p), "utf8");
const SRC = read("ui", "webview", "file-comments.ts");
const MODEL = read("ui", "webview", "file-comments-model.ts");

// ── fixtures: the notes-api world ──────────────────────────────────────────────────────────────────
const SID = "11111111-2222-3333-4444-555555555555";
const ROOT = "/repo/notes-api";
const T0 = 1757145600000;
const DOC = "# Report\n\n## Findings\nThe api session cut p95 latency by 40%.\n\n"
  + "We recommend shipping the cache in v1.2.\n\nRisks remain in the fallback path.\n\nNext steps: measure again.\n";
const at = (needle: string): number => { const i = DOC.indexOf(needle); assert.ok(i >= 0, needle); return i; };
const H = (id: string, kind: Hunk["kind"], from: number, to: number, oldText: string, newText: string, ts = T0 - 90000): Hunk =>
  ({ id, author: "api", ts, kind, curFrom: from, curTo: to, baseFrom: from, baseTo: from + oldText.length, oldText, newText, anchor: null });
const h1 = H("h1", "sub", at("cut"), at("cut") + 3, "reduced", "cut");
const h3 = H("h3", "del", at("shipping"), at("shipping"), "quickly ", "", T0 - 70000);
const h4 = H("h4", "sub", at("remain"), at("remain") + 6, "persist", "remain", T0 - 60000);
const h5 = H("h5", "ins", at(" again"), at(" again") + 6, "", " again", T0 - 50000);
// the detached ops as store-io keeps them: the engine's op record (from, oldText, newText, anchor, sometimes kind)
// with `detached: true`, at the op's LAST place in a text that has since moved on
const D1 = { id: "d1", author: "api", authorId: SID, ts: T0 - 40000, kind: "sub", from: 300, oldText: "cold starts were slow",
  newText: "cold starts stay slow", anchor: { quote: "cold starts stay slow", prefix: "and ", suffix: "." }, detached: true };
const D2 = { id: "d2", author: "api", ts: T0 - 30000, from: 20, oldText: "", newText: "Cold starts stay slow.", anchor: null, detached: true };
const GARBAGE: unknown[] = [null, "x", 7, {}, { id: "" }, { id: 3, newText: "numeric id" }];
const passage: StoreComment = {
  id: T0 + "-118", author: "you", ts: T0, body: "Which cache? Say which.",
  anchor: { quote: "shipping the cache in v1.2", prefix: "We recommend ", suffix: "." }, replies: [], resolved: false,
};
const onD1: StoreComment = { id: T0 + 5000 + "-300", author: "you", ts: T0 + 5000, body: "Keep the old wording.", suggestionId: "d1", replies: [], resolved: false };
const onD2: StoreComment = { id: T0 + 6000 + "-20", author: "you", ts: T0 + 6000, body: "Say why.", suggestionId: "d2", replies: [], resolved: false };
const store = (over: Partial<Store> = {}): Store => ({ v: 3, path: "docs/report.md", suggestions: [], comments: [], detached: [], ...over });
function status(over: Partial<Status> = {}): Status {
  return {
    verb: "status", root: ROOT, storePath: ROOT + "/.trackchanges/docs%2Freport.md.json", trackedBy: { kind: "file", entry: "docs/report.md" },
    agentTooling: "present", fileMtimeNs: "1757145600000000001", storeMtimeNs: "1757145600000000002", configMtimeNs: "1757145600000000003",
    store: store(), hunks: [], log: [], unsent: { comments: [], replies: [], accepted: 0, rejected: 0, watermark: null },
    ...over,
  };
}

test("detachedChanges reads the sidecar's detached[] defensively: the engine's fields, the kind derived when the record has none, garbage skipped, oldest first", () => {
  const ds = detachedChanges(store({ detached: [D2, ...GARBAGE, D1] }));
  assert.deepEqual(ds.map((d) => d.id), ["d1", "d2"], "by ts, whatever order the sidecar kept them in");
  assert.equal(ds[0].kind, "sub");
  assert.equal(ds[1].kind, "ins", "no kind on the record: the engine's rule from the texts");
  assert.equal(ds[0].authorId, SID, "the record's own authorId (toHunks never saw a detached op)");
  assert.equal(ds[1].authorId, null);
  assert.equal(ds[0].from, 300, "the op's last place, kept as the sidecar has it");
  assert.deepEqual(ds[0].anchor, D1.anchor);
  assert.equal(ds[1].anchor, null);
  assert.deepEqual(detachedChanges(store()), []);
  assert.deepEqual(detachedChanges(store({ detached: undefined })), [], "a sidecar without the field: none");
  assert.deepEqual(detachedChanges(null), []);
});

test("changeCards: the pending changes in text order, then one card per detached change with detached: true — key prefixed, the record's authorId, the same reference the pending cards wear", () => {
  const cards = changeCards(store({ detached: [D2, D1] }), [h4, h1]);
  assert.deepEqual(cards.map((c) => [c.id, c.detached]), [["h1", false], ["h4", false], ["d1", true], ["d2", true]]);
  assert.deepEqual(cards.slice(2).map((c) => c.key), ["chg:d1", "chg:d2"]);
  assert.equal(cards[2].authorId, SID);
  assert.equal(cards[3].authorId, null);
  assert.equal(cards[2].ref, "cold starts were slow → cold starts stay slow");
  assert.equal(cards[3].ref, "added Cold starts stay slow.");
  assert.equal(cards[2].kind, "sub"); assert.equal(cards[3].kind, "ins");
  assert.equal(cards[2].curFrom, 300); assert.equal(cards[2].curTo, 300 + D1.newText.length, "the op's last place; a detached change has no live position");
  assert.deepEqual(changeCards(store({ detached: [D1] }), []).map((c) => c.id), ["d1"], "no pending change at all: the detached one still has its card");
  assert.deepEqual(changeCards(null, [h1]).map((c) => c.detached), [false], "no sidecar in the reply: pending cards only, none detached");
});

test("a comment bound to a detached change rides its card: hunk set (the op in hunk shape) so it leaves the comment list, kind change, no decision; the message names the change's texts", () => {
  const st = store({ detached: [D1, D2], comments: [onD1, onD2] });
  const cm = cardModel(st, [h1], []);
  assert.equal(cm[0].kind, "change"); assert.equal(cm[0].hunk?.id, "d1"); assert.equal(cm[0].hunk?.kind, "sub");
  assert.equal(cm[0].decision, null, "detached is not decided");
  assert.equal(cm[0].ref, "cold starts were slow → cold starts stay slow");
  assert.equal(cm[1].hunk?.id, "d2"); assert.equal(cm[1].ref, "added Cold starts stay slow.");
  const cards = changeCards(st, [h1]);
  assert.deepEqual(cards.find((c) => c.id === "d1")!.comments.map((c) => c.id), [onD1.id], "on the detached change's card");
  assert.deepEqual(cards.find((c) => c.id === "d2")!.comments.map((c) => c.id), [onD2.id]);
  assert.equal(cards.find((c) => c.id === "h1")!.comments.length, 0);
  assert.equal(describeComment(onD1, [h1], [], { detached: st.detached }), 'on your change "cold starts were slow" to "cold starts stay slow"');
  assert.equal(describeComment(onD2, [h1], [], { detached: st.detached }), 'on the text you added "Cold starts stay slow."');
  assert.equal(describeComment(onD1, [h1]), "on this file", "without the sidecar's detached ops the model cannot know the change — which is why sendParts passes them");
  const parts = sendParts(status({ store: st, hunks: [h1], unsent: { comments: [onD1.id, onD2.id], replies: [], accepted: 0, rejected: 0, watermark: null } }));
  assert.deepEqual(parts.comments.map((c) => c.desc), ['on your change "cold starts were slow" to "cold starts stay slow"', 'on the text you added "Cold starts stay slow."']);
  assert.match(MODEL, /describeComment\(c, s\.hunks \|\| \[\], s\.log \|\| \[\], \{ detached: store\.detached, logTruncated: s\.logTruncated === true, decided: s\.decided \}\)/,
    "sendParts reads the status alone: its hunks, the sidecar's detached ops, its log, whether that log is a tail, and the decisions the whole log holds");
  // the lookup order is the sidecar's own: a change still in it (pending, then detached) is never read from an older log entry
  const old: LogEntry = { ts: "2026-09-06T08:00:00Z", kind: "accept", author: "you", changes: [{ id: "d1", oldText: "older", newText: "entry" }, { id: "h1", oldText: "older", newText: "entry" }] };
  assert.equal(boundChange("h1", [h1], st.detached, [old])!.state, "pending");
  assert.equal(boundChange("d1", [h1], st.detached, [old])!.state, "detached");
  assert.equal(boundChange("d1", [h1], st.detached, [old])!.oldText, "cold starts were slow", "the sidecar's texts, not the entry's");
  assert.equal(boundChange("d1", [h1], [], [old])!.state, "accepted", "gone from the sidecar: the log's decision");
  assert.equal(boundChange("zz", [h1], st.detached, [old]), null);
});

test("changeGroups: the paragraphs first, then the detached changes as one titled group — with the text, without it, and alone", () => {
  const st = store({ detached: [D1, D2] });
  const withText = changeGroups(changeCards(st, [h1, h4]), DOC);
  assert.deepEqual(withText.map((g) => [g.key === DETACHED_GROUP_KEY ? g.key : g.title, g.changes.map((c) => c.id)]),
    [["## Findings", ["h1"]], ["Risks remain in the fallback path.", ["h4"]], [DETACHED_GROUP_KEY, ["d1", "d2"]]]);
  const last = withText[2];
  assert.equal(last.title, DETACHED_GROUP_TITLE);
  assert.equal(last.start, -1, "no paragraph of the current text is theirs");
  assert.ok(DETACHED_GROUP_TITLE.length <= 60, "a group title's length: the paragraph titles are cut at 60");
  assert.doesNotMatch(DETACHED_GROUP_TITLE, /\b(suggestion|card|board|goal|nudge|column)s?\b/i, "the person's words, and no romp nouns");
  assert.doesNotMatch(DETACHED_GROUP_KEY, /^\d+-\d+$/, "a paragraph's key is start-end; the detached key can never collide with one");
  const noText = changeGroups(changeCards(st, [h1]), null);
  assert.deepEqual(noText.map((g) => [g.key, g.changes.map((c) => c.id)]), [["all", ["h1"]], [DETACHED_GROUP_KEY, ["d1", "d2"]]], "media or not loaded: one unnamed group of pending changes, then the detached");
  assert.deepEqual(changeGroups(changeCards(st, []), null).map((g) => g.key), [DETACHED_GROUP_KEY], "detached alone, no text: no empty unnamed group");
  assert.deepEqual(changeGroups(changeCards(st, []), DOC).map((g) => g.key), [DETACHED_GROUP_KEY]);
  assert.deepEqual(changeGroups([], DOC), []);
});

test("the fold: the detached group is a group like the others — past three groups it folds behind the row, whose N counts the detached changes too", () => {
  const groups = changeGroups(changeCards(store({ detached: [D1] }), [h1, h3, h4, h5]), DOC);
  assert.equal(groups.length, 5, "four paragraphs and the detached group");
  const f = foldGroups(groups, false);
  assert.equal(f.shown.length, GROUP_LIMIT);
  assert.deepEqual(f.hidden.map((g) => g.key).slice(-1), [DETACHED_GROUP_KEY], "last, so it folds first");
  assert.equal(f.hiddenChanges, 2, "h5 and d1: the count the glance also carries");
  assert.equal(moreChangesLabel(f.hiddenChanges), "… 2 more changes");
  assert.equal(foldGroups(groups, true).shown.length, 5);
});

test("the glance counts them: 'Comments · N · M changes · K detached changes', the detached part only when there are any", () => {
  assert.equal(actionLabel(status({ store: store({ detached: [D1, D2] }) })), "Comments · 0 · 2 detached changes");
  assert.equal(actionLabel(status({ store: store({ detached: [D1], comments: [passage] }), hunks: [h1] })), "Comments · 1 · 1 change · 1 detached change");
  assert.equal(actionLabel(status({ store: store({ detached: [D1, D2], comments: [passage] }), hunks: [h1, h4] })), "Comments · 1 · 2 changes · 2 detached changes");
  assert.equal(actionLabel(status({ store: store(), hunks: [h1] })), "Comments · 0 · 1 change", "none: the label as before");
  assert.equal(actionLabel(status({ store: store({ detached: undefined }), hunks: [h1, h4] })), "Comments · 0 · 2 changes");
  assert.equal(actionLabel(status({ store: store({ detached: GARBAGE }) })), "Comments · 0", "garbage in detached[] counts for nothing");
});

test("pinned at source: the panel renders the model's cards and groups (so a detached card renders) and its empty line yields to them; store-io keeps detached ops and the sidecar for them", () => {
  assert.match(SRC, /const cards = s \? changeCards\(s\.store, s\.hunks \|\| \[\], s\.log \|\| \[\], s\.decided\) : \[\];/, "the panel's change cards are the model's");
  assert.match(SRC, /const groups = changeGroups\(cards, /, "…grouped by the model");
  assert.match(SRC, /if \(!cards\.length && !view\.cards\.length\) \{/, "the 'No comments yet' line only when there is no card at all");
  // the engine side of the contract this leans on
  const STORE_IO = read("vendor", "track-changents", "store-io.mjs");
  assert.match(STORE_IO, /for \(const d of rb\.detached\) if \(!have\.has\(d\.id\)\) store\.detached\.push\(d\);/, "a load-time rebase's detached ops are kept on the store");
  assert.match(STORE_IO, /\|\| \(store\.detached \|\| \[\]\)\.length > 0\) return false;/, "pruneIfClean keeps a sidecar that holds one");
  const ENGINE = read("vendor", "track-changents", "engine.js");
  assert.match(ENGINE, /detached\.push\(\{ \.\.\.s, detached: true \}\);/, "the record is the op with detached: true — the fields detachedChanges reads");
  assert.equal(changeRef({ kind: "del", oldText: "quickly ", newText: "" }), "removed quickly", "the reference a detached deletion's card wears");
});

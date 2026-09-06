// Region comments on figures embedded in a text file — the model's two Slice 3 pieces the review found missing
// (plans/file-review.md, Slice 3; the review of 2026-09-06). Both come from the same fact: a figure in a markdown
// page is a file of its own. (1) The sent message's parenthetical named the region and not the figure, so on a
// page with two charts the session read "on the region at 0.12, 0.40, 0.35, 0.20" twice and could not tell which
// picture either comment was about without opening the sidecar; describeComment now names the figure by its `src`
// as the embed writes it. (2) The poll HEADed the text file, the sidecar and config.json, none of which moves when
// a session regenerates the figure, so a region comment never flipped to stale while the panel was open;
// figureTargets and figuresMoved are the poll's figure half: which paths to HEAD and, since the status reply
// carries hashes and no figure mtimes, a HEAD-to-HEAD baseline of the poll's own. Synthetic fixtures only: the
// notes-api world's docs/figures.md with two charts.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import {
  describeComment, sendParts, buildSendMessage, cardModel, figurePath, figureTargets, figuresMoved, pollTargets, ABSENT,
  decodeSrc, regionState, regionTarget,
  type Status, type StoreComment, type Target,
} from "./file-comments-model";

const web = (f: string): string => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const MODEL = web("file-comments-model.ts");
const VIEW = web("file-view.ts");
const HOST = fs.readFileSync(path.resolve(process.cwd(), "..", "tools", "file-comments-host.mjs"), "utf8");

// ── fixtures: docs/figures.md embeds two charts ────────────────────────────────────────────────────
const ABS = "/repo/notes-api/docs/figures.md";
const T0 = 1757145600000;                              // 2026-09-06T08:00:00Z, as the CLIs stamp `ts`
const REGION_A = { x: 0.12, y: 0.4, w: 0.35, h: 0.2 };
const REGION_B = { x: 0.5, y: 0.5, w: 0.25, h: 0.1 };
const H = (c: string): string => c.repeat(64);

const onLatency: StoreComment = {
  id: T0 + "-11", author: "you", ts: T0, body: "The y axis is mislabeled.", replies: [], resolved: false,
  anchor: { quote: "![p95 latency](figs/latency.png)", prefix: "# Figures\n\n", suffix: "\n\n![error rate](figs/e" },
  target: { kind: "image", region: REGION_A, hash: H("a"), src: "figs/latency.png" },
};
const onErrors: StoreComment = {
  id: (T0 + 1000) + "-46", author: "you", ts: T0 + 1000, body: "Start this one at zero.", replies: [], resolved: false,
  anchor: { quote: "![error rate](figs/errors.png)", prefix: "s/latency.png)\n\n", suffix: "\n" },
  target: { kind: "image", region: REGION_B, hash: H("b"), src: "figs/errors.png" },
};
const passage: StoreComment = {
  id: (T0 + 2000) + "-2", author: "you", ts: T0 + 2000, body: "Say which week.", replies: [], resolved: false,
  anchor: { quote: "Figures", prefix: "# ", suffix: "\n\n![p95" },
};

function status(over: Partial<Status> = {}): Status {
  return {
    verb: "status", root: "/repo/notes-api", storePath: "/repo/notes-api/.trackchanges/docs%2Ffigures.md.json",
    trackedBy: null, agentTooling: "present",
    fileMtimeNs: "1757145600000000001", storeMtimeNs: "1757145600000000002", configMtimeNs: null,
    store: { v: 3, path: "docs/figures.md", suggestions: [], comments: [onLatency, onErrors, passage] },
    hunks: [], log: [],
    unsent: { comments: [onLatency.id, onErrors.id], replies: [], accepted: 0, rejected: 0, watermark: null },
    embeddedHashes: { "figs/latency.png": H("a"), "figs/errors.png": H("b") },
    ...over,
  };
}

// ── (1) the message names the figure ───────────────────────────────────────────────────────────────
test("desc on an embedded figure names the region AND the figure, by its src decoded to the file's name on disk", () => {
  assert.equal(describeComment(onLatency, []), "on the region at 0.12, 0.40, 0.35, 0.20 of figs/latency.png");
  assert.equal(describeComment(onErrors, []), "on the region at 0.50, 0.50, 0.25, 0.10 of figs/errors.png");
  assert.ok(!describeComment(onLatency, []).includes("![p95 latency]"), "the region wins over the embed line's anchor; the figure is named by src, not by quoting the embed");
  const encoded: StoreComment = { ...onLatency, target: { ...onLatency.target!, src: "figs/p95%20latency.png" } };
  assert.equal(describeComment(encoded, []), "on the region at 0.12, 0.40, 0.35, 0.20 of figs/p95 latency.png",
    "the file's name on disk, not the embed's percent-encoded spelling (the review of 2026-09-06: `ls figs/p95%20latency.png` got ENOENT while the host hashed the decoded file)");
});

// The review of 2026-09-06 (round 2): marked percent-encodes a destination with a space, so `![](figs/p95%20latency.png)`
// is the only inline embed spelling for such a file — the normal case, not an edge — and the message named that
// spelling while the host (decodeSrc) hashed `figs/p95 latency.png`. The figure's name in the message and on the card
// now goes through the same decode the viewer and the host apply; the src AS WRITTEN stays what the target stores
// and what keys embeddedHashes, so the decode is display-only and staleness still finds its hash.
test("the figure's name is the src decoded as the viewer loads it and the host hashes it; the stored src and the hash key stay as written", () => {
  assert.equal(decodeSrc("figs/p95%20latency.png"), "figs/p95 latency.png");
  assert.equal(decodeSrc("figs/latency.png"), "figs/latency.png", "a plain src is itself");
  assert.equal(decodeSrc("figs/100%.png"), "figs/100%.png", "a malformed escape is taken as written, as the host reads it");
  assert.equal(decodeSrc("figs/%E0%A4%A.png"), "figs/%E0%A4%A.png");
  assert.equal(decodeSrc("figs/caf%C3%A9.png"), "figs/café.png", "a UTF-8 escape decodes to the character the file name has");
  const encoded: StoreComment = { ...onLatency, target: { ...onLatency.target!, src: "figs/p95%20latency.png" } };
  const malformed: StoreComment = { ...onErrors, target: { ...onErrors.target!, src: "figs/100%.png" } };
  assert.equal(describeComment(malformed, []), "on the region at 0.50, 0.50, 0.25, 0.10 of figs/100%.png", "unreadable as an escape: named as written, which IS the file's name");
  // the name the message gives and the file the poll HEADs are one file: the desc's tail is figurePath's tail
  for (const c of [onLatency, onErrors, encoded, malformed]) {
    const named = describeComment(c, []).split(" of ")[1];
    assert.ok(figurePath(ABS, c.target!.src!)!.endsWith("/" + named), named + " is the file the poll watches: " + figurePath(ABS, c.target!.src!));
  }
  // the sent message and the collapsed card carry the decoded name
  const s = status({
    store: { v: 3, path: "docs/figures.md", suggestions: [], comments: [encoded, malformed] },
    unsent: { comments: [encoded.id, malformed.id], replies: [], accepted: 0, rejected: 0, watermark: null },
    embeddedHashes: { "figs/p95%20latency.png": H("a"), "figs/100%.png": H("b") },
  });
  const parts = sendParts(s);
  const body = buildSendMessage({ absPath: ABS, comments: parts.comments, accepted: 0, rejected: 0, tracked: false });
  assert.ok(body.includes("Comment " + encoded.id + " (on the region at 0.12, 0.40, 0.35, 0.20 of figs/p95 latency.png):\nThe y axis is mislabeled.\n"), body);
  assert.ok(!body.includes("%20"), "no percent-encoded spelling reaches the session");
  assert.deepEqual(cardModel(s.store, [], []).map((c) => c.ref),
    ["the region at 0.12, 0.40, 0.35, 0.20 of figs/p95 latency.png", "the region at 0.50, 0.50, 0.25, 0.10 of figs/100%.png"]);
  // display-only: the target still stores the src as written, and embeddedHashes is still read by that key
  assert.equal(regionTarget(REGION_A, "figs/p95%20latency.png").src, "figs/p95%20latency.png", "the target the comment sends keeps the embed's spelling");
  assert.equal(regionState(encoded.target, s), "current", "staleness looks the hash up under the spelling the host keyed it by");
  assert.equal(regionState({ ...encoded.target!, hash: H("z") }, s), "stale");
  assert.equal(regionState(encoded.target, { embeddedHashes: { "figs/p95 latency.png": H("a") } }), "unknown", "the decoded spelling is not the key");
  assert.match(MODEL, /at \+ " of " \+ decodeSrc\(c\.target\.src\)/, "the figure's name goes through the shared decode");
  assert.doesNotMatch(MODEL, /at \+ " of " \+ c\.target\.src\b/, "never the src as written");
  assert.ok(HOST.includes("function decodeSrc(src) {\n  try { return decodeURI(src); } catch { return src; }"), "the host's decode is the same two lines");
});

test("the standalone forms are unchanged: an image names the region alone, a PDF page its page (the plan's own two)", () => {
  const whole: StoreComment = { id: T0 + "-0", author: "you", ts: T0, body: "Crop.", replies: [], resolved: false };
  const image: Target = { kind: "image", region: REGION_A, hash: H("c") };
  assert.equal(describeComment({ ...whole, target: image }, []), "on the region at 0.12, 0.40, 0.35, 0.20");
  const page: Target = { kind: "pdf", region: REGION_A, page: 2, hash: H("c") };
  assert.equal(describeComment({ ...whole, target: page }, []), "on the region at 0.12, 0.40, 0.35, 0.20 of page 2");
  assert.equal(describeComment({ ...whole, target: { ...image, src: "" } }, []), "on the region at 0.12, 0.40, 0.35, 0.20", "an empty src names nothing");
});

test("the message for two figures on one page tells them apart (the scenario the review reproduced), and stays the kernel's shape", () => {
  const parts = sendParts(status());
  assert.deepEqual(parts.comments.map((c) => c.desc), [
    "on the region at 0.12, 0.40, 0.35, 0.20 of figs/latency.png",
    "on the region at 0.50, 0.50, 0.25, 0.10 of figs/errors.png",
  ]);
  assert.notEqual(parts.comments[0].desc.replace(/ of figs\/latency\.png$/, ""), parts.comments[0].desc, "the figure is part of what goes");
  const body = buildSendMessage({ absPath: ABS, comments: parts.comments, accepted: 0, rejected: 0, tracked: false });
  assert.ok(body.includes("Comment " + onLatency.id + " (on the region at 0.12, 0.40, 0.35, 0.20 of figs/latency.png):\nThe y axis is mislabeled.\n"), body);
  assert.ok(body.includes("Comment " + onErrors.id + " (on the region at 0.50, 0.50, 0.25, 0.10 of figs/errors.png):\nStart this one at zero.\n"), body);
  assert.ok(body.startsWith("[obsidian-diff] I left 2 comments on " + ABS + ".\n"), "the header and the rest are untouched: the kernel prints the client's desc verbatim, so the parenthetical is the one place this lands");
  assert.match(MODEL, /at \+ " of " \+ decodeSrc\(c\.target\.src\)/, "the figure follows the region phrase the way a PDF's page does");
});

test("the card's one-line reference names the figure too — on a page with several, the collapsed card says which", () => {
  const cards = cardModel(status().store, [], []);
  assert.deepEqual(cards.filter((c) => c.kind === "region").map((c) => c.ref), [
    "the region at 0.12, 0.40, 0.35, 0.20 of figs/latency.png",
    "the region at 0.50, 0.50, 0.25, 0.10 of figs/errors.png",
  ]);
  assert.equal(cards[2].kind, "passage", "a passage comment on the same page is unaffected");
});

// ── (2) the poll's figure half ─────────────────────────────────────────────────────────────────────
test("figurePath resolves a src the way the viewer loads it and the host hashes it: decodeURI, absolute as itself, relative against the file's directory, a URL is no file", () => {
  assert.equal(figurePath(ABS, "figs/latency.png"), "/repo/notes-api/docs/figs/latency.png");
  assert.equal(figurePath(ABS, "figs/p95%20latency.png"), "/repo/notes-api/docs/figs/p95 latency.png", "marked percent-encodes; the file has the space");
  assert.equal(figurePath(ABS, "figs/%E0%A4%A.png"), "/repo/notes-api/docs/figs/%E0%A4%A.png", "a malformed escape is taken as written");
  assert.equal(figurePath(ABS, "/repo/notes-api/assets/banner.png"), "/repo/notes-api/assets/banner.png", "an absolute src is itself");
  assert.equal(figurePath(ABS, "../assets/banner.png"), "/repo/notes-api/docs/../assets/banner.png", "`..` stays as written: the kernel resolves and gates the path");
  assert.equal(figurePath(ABS, "./figs/latency.png"), "/repo/notes-api/docs/./figs/latency.png");
  assert.equal(figurePath("figures.md", "figs/latency.png"), "figs/latency.png", "a bare file name has no directory: the src resolves as the file did");
  for (const url of ["https://example.invalid/chart.png", "http://example.invalid/c.png", "data:image/png;base64,AAAA", "blob:https://example.invalid/x", "file:///etc/hosts"]) {
    assert.equal(figurePath(ABS, url), null, url);
  }
  assert.equal(figurePath(ABS, ""), null, "an empty src names nothing");
  assert.equal(figurePath(ABS, "c:figs/x.png"), null, "one letter and a colon is a scheme to the viewer too — the same rule, so the two never disagree on what is a file");
  // the same three decisions in the same three places
  const SCHEME = "/^[a-z][a-z0-9+.-]*:/i";
  for (const [name, src] of [["the model", MODEL], ["the viewer", VIEW], ["the host", HOST]] as const) {
    assert.ok(src.includes(SCHEME), name + " tests a URL scheme with the shared literal");
    assert.ok(src.includes("decodeURI(src)"), name + " decodes the src with decodeURI");
  }
});

test("figureTargets: one HEAD target per distinct figure the sidecar's region comments name, first appearance first, resolved comments included", () => {
  assert.deepEqual(figureTargets(status(), ABS), ["/repo/notes-api/docs/figs/latency.png", "/repo/notes-api/docs/figs/errors.png"]);
  const twice: StoreComment = { ...onLatency, id: T0 + "-99", ts: T0 + 5000, target: { ...onLatency.target!, region: REGION_B } };
  const resolved: StoreComment = { ...onErrors, resolved: true };
  const store = { v: 3, path: "docs/figures.md", suggestions: [], comments: [twice, resolved, passage, onLatency] };
  assert.deepEqual(figureTargets({ store }, ABS), ["/repo/notes-api/docs/figs/latency.png", "/repo/notes-api/docs/figs/errors.png"],
    "two comments on one figure are one HEAD; a resolved comment's card still wears the stale tag, so its figure is watched");
  const spellings: StoreComment[] = [
    { ...onLatency, target: { ...onLatency.target!, src: "figs/p95%20latency.png" } },
    { ...onErrors, target: { ...onErrors.target!, src: "figs/p95 latency.png" } },
  ];
  assert.deepEqual(figureTargets({ store: { ...store, comments: spellings } }, ABS), ["/repo/notes-api/docs/figs/p95 latency.png"], "two spellings of one path are one target");
  const skipped: StoreComment[] = [
    passage,                                                                                            // no target
    { ...onLatency, target: { kind: "image", region: REGION_A, hash: H("d") } },                        // standalone: no src (the poll's `file`)
    { ...onErrors, target: { ...onErrors.target!, src: "https://example.invalid/chart.png" } },         // a URL: no file the kernel serves
  ];
  assert.deepEqual(figureTargets({ store: { ...store, comments: skipped } }, ABS), []);
  assert.deepEqual(figureTargets({ store: null }, ABS), [], "no sidecar: nothing to watch");
  assert.deepEqual(figureTargets(null, ABS), []);
  assert.deepEqual(figureTargets(undefined, ABS), []);
  // the figures ride beside the three targets, not among them: the panel's tick walks {file, store, config} by key
  assert.deepEqual(pollTargets(status(), ABS), { file: ABS, store: "/repo/notes-api/.trackchanges/docs%2Ffigures.md.json", config: "/repo/notes-api/.trackchanges/config.json" });
});

test("figuresMoved: a first reading is a baseline, a differing later one is a move; a silent tick keeps the last reading; a figure no longer named is dropped", () => {
  const A = "/repo/notes-api/docs/figs/latency.png", B = "/repo/notes-api/docs/figs/errors.png";
  const first = figuresMoved({}, [A, B], { [A]: "1757145600000000010", [B]: "1757145600000000020" });
  assert.deepEqual(first, { moved: [], next: { [A]: "1757145600000000010", [B]: "1757145600000000020" } }, "nothing to compare a first reading with");
  const same = figuresMoved(first.next, [A, B], { [A]: "1757145600000000010", [B]: "1757145600000000020" });
  assert.deepEqual(same.moved, []);
  const regen = figuresMoved(same.next, [A, B], { [A]: "1757145600000000010", [B]: "1757145600000000021" });
  assert.deepEqual(regen, { moved: [B], next: { [A]: "1757145600000000010", [B]: "1757145600000000021" } }, "the session regenerated errors.png: that figure moved, and the new reading is the baseline");
  const blip = figuresMoved(regen.next, [A, B], { [A]: "1757145600000000010" });
  assert.deepEqual(blip, { moved: [], next: regen.next }, "a HEAD that did not answer this tick leaves its figure's baseline standing");
  const gone = figuresMoved(blip.next, [A], { [A]: "1757145600000000010", [B]: "1757145600000000022" });
  assert.deepEqual(gone, { moved: [], next: { [A]: "1757145600000000010" } }, "a figure no longer named by any comment is dropped, and a stray reading of it is ignored");
  const appears = figuresMoved({ [A]: ABSENT }, [A], { [A]: "1757145600000000030" });
  assert.deepEqual(appears.moved, [A], "absent → present is a move like any other (the figure was written after the comment)");
  assert.deepEqual(figuresMoved({ [A]: "1757145600000000001" }, [A], { [A]: "1757145600000000002" }).moved, [A],
    "~1.7e18 exceeds JS's safe integers: compared as strings, two adjacent writes differ");
  assert.doesNotMatch(MODEL, /Number\([^)]*[mM]time|parseInt\([^)]*[mM]time|BigInt\(/, "no numeric coercion of an mtime in the model");
});

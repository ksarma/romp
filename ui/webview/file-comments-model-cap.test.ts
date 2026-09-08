// The message's parenthetical for a passage whose widened surroundings are too wide to quote (the anchors follow-on
// review, round 2, 2026-09-07). The round-1 form names a recurring passage by its whole widened prefix and suffix,
// JSON-quoted, so the session can build a unique `track-edit --old` from them; at the host's cap (480 characters a
// side) that put a kilobyte of escaped text on the one `Comment <id> (…):` line, and named a span that still sits on
// every copy — the anchor at the cap may still tie, and the sidecar stores no `unique` flag to say. Pinned here: the
// bound the sides are printed whole up to (DESC_CTX_MAX, five of the host's steps, below its cap); past it on either
// side the desc keeps the plan's `on "<first 40 characters>"` and says only that the text recurs with the same
// surroundings (RECURS_CLAUSE), whatever the width; the real host's anchor at the cap for the tests' REPEAT fixture
// gets that form, short, one line, the same for every copy (the message cannot tell them apart, and says nothing
// that claims to); the vendored CLI refuses the dropped span as not unique, which is why it is not printed; and the
// Send path carries the short line. Synthetic fixtures only: invented text, placeholder ids, the notes-api paths.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { spawnSync } from "node:child_process";
import {
  type Status, type StoreComment, type Anchor,
  ANCHOR_CTX, DESC_CTX_MAX, RECURS_CLAUSE, anchorWidened, passageDesc, describeComment, sendParts, buildSendMessage,
} from "./file-comments-model";

const REPO = path.resolve(process.cwd(), "..");
const read = (...p: string[]) => fs.readFileSync(path.join(REPO, ...p), "utf8");
const HOST = read("tools", "file-comments-host.mjs");
const hostConst = (name: string): number => {
  const m = HOST.match(new RegExp("^export const " + name + " = (\\d+);$", "m"));
  assert.ok(m, "the host exports " + name);
  return Number(m![1]);
};

// ── the REPEAT fixture the host, e2e and painter tests share: one paragraph over a thousand characters, three times,
// a phrase in its middle with the same surroundings for more than the cap on both sides of every copy ─────────────
const PARA = ("The quick brown fox jumps over the lazy dog. ".repeat(12)
  + "Here is the marker phrase to comment on. "
  + "Pack my box with five dozen liquor jugs. ".repeat(12)).trim();
const REPEAT = "# Repeats\n\n" + PARA + "\n\n" + PARA + "\n\n" + PARA + "\n";
const MARKER = "the marker phrase";
const FIRST = REPEAT.indexOf(MARKER);
const SECOND = REPEAT.indexOf(MARKER, FIRST + 1);
const THIRD = REPEAT.indexOf(MARKER, SECOND + 1);
assert.ok(FIRST > 0 && SECOND > FIRST && THIRD > SECOND && REPEAT.indexOf(MARKER, THIRD + 1) === -1, "three copies");

const ABS = "/repo/notes-api/docs/repeat.md";
const ROOT = "/repo/notes-api";
const T0 = 1781100000000;
const ROMP_NOUNS = /\b(romp|card|board|goal|column|cleared|dismissal|nudge|status check)s?\b/i;
const count = (hay: string, needle: string): number => { let n = 0, i = -1; while ((i = hay.indexOf(needle, i + 1)) !== -1) n++; return n; };
/** The engine's makeAnchor by hand: the quote with `ctx` characters either side, clipped at the file's bounds. */
const anchorOf = (text: string, from: number, to: number, ctx: number): Anchor =>
  ({ quote: text.slice(from, to), prefix: text.slice(Math.max(0, from - ctx), from), suffix: text.slice(to, to + ctx) });
const passage = (id: string, ts: number, body: string, anchor: Anchor, at: number): StoreComment =>
  ({ id, author: "you", ts, body, anchor, anchorAt: at, replies: [], resolved: false });
function status(over: Partial<Status> = {}): Status {
  return {
    verb: "status", root: ROOT, storePath: ROOT + "/.trackchanges/docs%2Frepeat.md.json", trackedBy: { kind: "file", entry: "docs/repeat.md" },
    agentTooling: "present", fileMtimeNs: "1781100000000000001", storeMtimeNs: "1781100000000000002", configMtimeNs: "1781100000000000003",
    store: { v: 3, path: "docs/repeat.md", suggestions: [], comments: [] }, hunks: [], log: [],
    unsent: { comments: [], replies: [], accepted: 0, rejected: 0, watermark: null },
    ...over,
  };
}

/** The real host's uniqueAnchor on the REPEAT fixture's three copies, and the vendored CLI's verdict on `--old` as the
 *  stored prefix + quote + suffix of the second — run in a node of their own (both modules guard their main on
 *  argv[1], so the text and the paths travel in the environment and argv stays empty). */
type HostSays = {
  cap: number;
  a1: { anchor: Anchor; unique: boolean }; a2: { anchor: Anchor; unique: boolean }; a3: { anchor: Anchor; unique: boolean };
  bySpan: { error?: string; from?: number; to?: number };
};
function askHost(): HostSays {
  const driver = [
    'import { pathToFileURL } from "node:url";',
    "const host = await import(pathToFileURL(process.env.CAP_HOST).href);",
    "const edit = await import(pathToFileURL(process.env.CAP_EDIT).href);",
    "const text = process.env.CAP_TEXT; const q = process.env.CAP_MARKER;",
    "const at = [0, 1, 2].map((i) => { let p = -1; for (let k = 0; k <= i; k++) p = text.indexOf(q, p + 1); return p; });",
    "const [a1, a2, a3] = at.map((p) => host.uniqueAnchor(text, p, p + q.length));",
    "const span = a2.anchor.prefix + q + a2.anchor.suffix;",
    "const r = edit.applyTrackedEdit(text, span, a2.anchor.prefix + \"the other phrase\" + a2.anchor.suffix);",
    "process.stdout.write(JSON.stringify({ cap: host.ANCHOR_CTX_CAP, a1, a2, a3, bySpan: { error: r.error, from: r.from, to: r.to } }));",
  ].join("\n");
  const r = spawnSync(process.execPath, ["--input-type=module", "-e", driver], {
    encoding: "utf8", timeout: 60000,
    env: { ...process.env, CAP_HOST: path.join(REPO, "tools", "file-comments-host.mjs"),
      CAP_EDIT: path.join(REPO, "vendor", "track-changents", "cli", "track-edit.mjs"), CAP_TEXT: REPEAT, CAP_MARKER: MARKER },
  });
  assert.equal(r.status, 0, "the host and the CLI import cleanly: " + r.stderr);
  return JSON.parse(r.stdout) as HostSays;
}

test("DESC_CTX_MAX: five of the host's steps, a multiple of its step, below its cap", () => {
  assert.equal(DESC_CTX_MAX, 120);
  assert.equal(DESC_CTX_MAX, ANCHOR_CTX * 5);
  assert.equal(hostConst("ANCHOR_CTX"), ANCHOR_CTX);
  assert.equal(DESC_CTX_MAX % hostConst("ANCHOR_CTX_STEP"), 0, "no stored width falls between the bound and the next step");
  assert.ok(DESC_CTX_MAX < hostConst("ANCHOR_CTX_CAP"), "an anchor at the host's cap is past the bound, so the cap never prints its sides");
  assert.ok(DESC_CTX_MAX >= ANCHOR_CTX * 2, "the one-step widening the recurring test pins (48) still prints whole");
});

test("RECURS_CLAUSE joins the plan's form on one line, in the person's voice", () => {
  assert.equal(RECURS_CLAUSE, ", which appears more than once with the same text around each copy");
  assert.ok(RECURS_CLAUSE.startsWith(", ") && !RECURS_CLAUSE.includes("\n") && !RECURS_CLAUSE.includes('"'));
  assert.doesNotMatch(RECURS_CLAUSE, ROMP_NOUNS);
  assert.doesNotMatch(RECURS_CLAUSE, /anchor|offset|position|unique|sidecar/i, "nothing the session has no tool for, and no engine words");
});

test("the sides print whole up to the bound and not at all past it, on either side", () => {
  const q = "Ship it.";
  const p = "p".repeat(DESC_CTX_MAX), s = "s".repeat(DESC_CTX_MAX);
  const atBound: Anchor = { quote: q, prefix: p, suffix: s };
  assert.ok(anchorWidened(atBound));
  assert.equal(passageDesc(atBound), 'on "Ship it.", the one after "' + p + '" and before "' + s + '"', "exactly the bound: whole");
  assert.equal(passageDesc({ quote: q, prefix: p + "p", suffix: s }), 'on "Ship it."' + RECURS_CLAUSE, "one over on the prefix");
  assert.equal(passageDesc({ quote: q, prefix: p, suffix: s + "s" }), 'on "Ship it."' + RECURS_CLAUSE, "one over on the suffix");
  assert.equal(passageDesc({ quote: q, prefix: "", suffix: "s".repeat(480) }), 'on "Ship it."' + RECURS_CLAUSE, "at the cap with the other side at the file's start");
  assert.equal(passageDesc({ quote: q, prefix: "x".repeat(480) } as unknown as Anchor), 'on "Ship it."' + RECURS_CLAUSE, "a sidecar missing a side is read as empty");
  // the clause never cuts a side short: a truncated span would not be the unique text the round-1 form promises
  const wide = passageDesc({ quote: q, prefix: "a".repeat(DESC_CTX_MAX + 24), suffix: "b".repeat(24) });
  assert.ok(!wide.includes("the one after") && !wide.includes("aaaa"), "no partial context, no ellipsis form");
  // the 40-character cut of the quote is untouched in both forms
  const long = "q".repeat(50);
  assert.equal(passageDesc({ quote: long, prefix: p + "p", suffix: "" }), 'on "' + "q".repeat(40) + '"' + RECURS_CLAUSE);
  assert.equal(passageDesc({ quote: long, prefix: "b".repeat(48), suffix: "" }), 'on "' + "q".repeat(40) + '", the one after "' + "b".repeat(48) + '"');
});

test("the host's anchor at the cap for a passage that ties past it reads short, the same on every copy, naming nothing the span cannot", () => {
  const h = askHost();
  assert.equal(h.cap, 480);
  for (const a of [h.a1, h.a2, h.a3]) {
    assert.equal(a.unique, false, "the tie the cap exists for");
    assert.deepEqual([a.anchor.prefix.length, a.anchor.suffix.length], [h.cap, h.cap], "saved at the cap");
    assert.ok(anchorWidened(a.anchor));
  }
  assert.deepEqual(h.a2.anchor, anchorOf(REPEAT, SECOND, SECOND + MARKER.length, 480));
  const d = passageDesc(h.a2.anchor);
  assert.equal(d, 'on "the marker phrase"' + RECURS_CLAUSE);
  assert.equal(passageDesc(h.a1.anchor), d);
  assert.equal(passageDesc(h.a3.anchor), d, "three copies the message cannot tell apart read alike — no false 'the one after'");
  assert.ok(d.length < 100, "short: " + d.length);
  assert.ok(!d.includes("\n") && !d.includes("\\n"), "one line, with nothing escaped onto it");
  assert.ok(!d.includes("quick brown fox") && !d.includes("liquor jugs"), "none of the surroundings");
  assert.doesNotMatch(d, ROMP_NOUNS);
  assert.equal(describeComment(passage(T0 + "-" + SECOND, T0, "Say it once.", h.a2.anchor, SECOND), []), d, "anchorAt adds nothing: the position is the painter's");
  // what the round-1 form would have named: a span that sits on every copy, and one the CLI refuses
  assert.equal(count(REPEAT, h.a2.anchor.prefix + MARKER + h.a2.anchor.suffix), 3);
  assert.match(h.bySpan.error || "", /not unique/, "the whole cap-width span is an --old the CLI refuses, so printing it would claim a copy it does not name");
});

test("Send to session carries the short line for a comment at the cap, and the body follows it", () => {
  const h = askHost();
  const two = passage(T0 + 2000 + "-" + SECOND, T0 + 2000, "Say it once.", h.a2.anchor, SECOND);
  const three = passage(T0 + 3000 + "-" + THIRD, T0 + 3000, "And here.", h.a3.anchor, THIRD);
  const s = status({
    store: { v: 3, path: "docs/repeat.md", suggestions: [], comments: [two, three] },
    unsent: { comments: [two.id, three.id], replies: [], accepted: 0, rejected: 0, watermark: null },
  });
  const parts = sendParts(s);
  assert.deepEqual(parts.comments.map((c) => c.desc), ['on "the marker phrase"' + RECURS_CLAUSE, 'on "the marker phrase"' + RECURS_CLAUSE]);
  const msg = buildSendMessage({ absPath: ABS, comments: parts.comments, accepted: 0, rejected: 0, tracked: true });
  const lines = msg.split("\n");
  assert.equal(lines[0], "[obsidian-diff] I left 2 comments on " + ABS + ".");
  const commentLines = lines.filter((l) => l.startsWith("Comment "));
  assert.deepEqual(commentLines, [
    "Comment " + two.id + ' (on "the marker phrase"' + RECURS_CLAUSE + "):",
    "Comment " + three.id + ' (on "the marker phrase"' + RECURS_CLAUSE + "):",
  ]);
  for (const l of commentLines) assert.ok(l.length < 160, "the kernel prints the desc verbatim on this line, and it stays a line: " + l.length);
  assert.equal(lines.indexOf("Say it once."), lines.indexOf(commentLines[0]) + 1);
  assert.equal(lines.indexOf("And here."), lines.indexOf(commentLines[1]) + 1);
  assert.equal(msg.length < 900, true, "two comments at the cap: well under the ~1.5 KB one comment cost before, " + msg.length);
  assert.ok(!msg.includes("quick brown fox"), "the message carries none of the widened context");
  assert.doesNotMatch(msg.split("To respond:")[0], ROMP_NOUNS);
});

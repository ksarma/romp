// The message's parenthetical for a passage that recurs (the anchors follow-on review, 2026-09-07). The host widens a
// passage comment's anchor until it locates uniquely and stores the offset beside it, and the panel paints the copy the
// person chose — but the Send to session message named the passage by its quote alone, so two comments on two copies of
// the same text read identically to the session, and the one revision tool it has for a tracked file, `track-edit --old`,
// refuses text that is not unique. Pinned here: a passage unique at the engine's default context keeps the plan's form,
// `on "<first 40 characters>"`, whether or not it carries anchorAt; a passage whose anchor the host widened is named by
// its surroundings, the widened prefix and suffix whole and JSON-quoted, so the desc stays one line and the session can
// build a unique --old from it; the two copies' descs differ; the real host's uniqueAnchor and the vendored CLI's own
// uniqueness rule agree with what the message says; the card's one-line reference does not change (the painter, not
// the words, tells the copies apart on the panel); and the clause speaks in the person's voice. Fixtures are the
// repo's synthetic notes-api report and invented text; placeholder ids.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { spawnSync } from "node:child_process";
import {
  type Status, type StoreComment, type Anchor,
  ANCHOR_CTX, anchorWidened, passageDesc, describeComment, sendParts, buildSendMessage, cardModel,
} from "./file-comments-model";

const REPO = path.resolve(process.cwd(), "..");
const read = (...p: string[]) => fs.readFileSync(path.join(REPO, ...p), "utf8");
const MODEL = read("ui", "webview", "file-comments-model.ts");
const HOST = read("tools", "file-comments-host.mjs");
const ENGINE = read("vendor", "track-changents", "engine.js");
const FIXTURE = path.join(REPO, "tests", "fixtures", "file_comments", "report.md");
const TEXT = fs.readFileSync(FIXTURE, "utf8");

// ── the notes-api world: the fixture's two "Ship it." lines, one under Day 1 and one under Day 2 ───
const ABS = "/repo/notes-api/docs/report.md";
const ROOT = "/repo/notes-api";
const T0 = 1781100000000;
const QUOTE = "Ship it.";
const FIRST = TEXT.indexOf(QUOTE);
const SECOND = TEXT.indexOf(QUOTE, FIRST + 1);
assert.ok(FIRST > 0 && SECOND > FIRST && TEXT.indexOf(QUOTE, SECOND + 1) === -1, "the fixture has exactly two copies");
/** The engine's makeAnchor by hand: the quote with `ctx` characters either side, clipped at the file's bounds. */
const anchorAt = (text: string, from: number, to: number, ctx: number): Anchor =>
  ({ quote: text.slice(from, to), prefix: text.slice(Math.max(0, from - ctx), from), suffix: text.slice(to, to + ctx) });
const passage = (id: string, ts: number, body: string, anchor: Anchor, at: number): StoreComment =>
  ({ id, author: "you", ts, body, anchor, anchorAt: at, replies: [], resolved: false });
function status(over: Partial<Status> = {}): Status {
  return {
    verb: "status", root: ROOT, storePath: ROOT + "/.trackchanges/docs%2Freport.md.json", trackedBy: { kind: "file", entry: "docs/report.md" },
    agentTooling: "present", fileMtimeNs: "1781100000000000001", storeMtimeNs: "1781100000000000002", configMtimeNs: "1781100000000000003",
    store: { v: 3, path: "docs/report.md", suggestions: [], comments: [] }, hunks: [], log: [],
    unsent: { comments: [], replies: [], accepted: 0, rejected: 0, watermark: null },
    ...over,
  };
}
const ROMP_NOUNS = /\b(romp|card|board|goal|column|cleared|dismissal|nudge|status check)s?\b/i;
const count = (hay: string, needle: string): number => { let n = 0, i = -1; while ((i = hay.indexOf(needle, i + 1)) !== -1) n++; return n; };

/** The real host's uniqueAnchor and the vendored CLI's applyTrackedEdit, run in a node of their own (both modules guard
 *  their main on argv[1], so the paths travel in the environment and argv stays empty). Returns what each says about the
 *  fixture's two copies: the anchors the host would store, and the CLI's verdict on `--old` as the quote, as the engine's
 *  24-character span, and as the stored prefix + quote + suffix. */
type HostSays = {
  ctx: number; first: number; second: number;
  a1: { anchor: Anchor; unique: boolean }; a2: { anchor: Anchor; unique: boolean };
  byQuote: { error?: string }; bySpan24: { error?: string }; bySpan: { error?: string; from?: number; to?: number };
};
function askHost(): HostSays {
  const driver = [
    'import { readFileSync } from "node:fs";',
    'import { pathToFileURL } from "node:url";',
    "const host = await import(pathToFileURL(process.env.RECUR_HOST).href);",
    "const edit = await import(pathToFileURL(process.env.RECUR_EDIT).href);",
    'const text = readFileSync(process.env.RECUR_FIXTURE, "utf8");',
    'const q = "Ship it."; const first = text.indexOf(q), second = text.indexOf(q, first + 1);',
    "const a1 = host.uniqueAnchor(text, first, first + q.length), a2 = host.uniqueAnchor(text, second, second + q.length);",
    "const strip = (r) => ({ error: r.error, from: r.from, to: r.to });",
    "const s24 = text.slice(second - 24, second) + q + text.slice(second + q.length, second + q.length + 24);",
    "const span = a2.anchor.prefix + q + a2.anchor.suffix;",
    "process.stdout.write(JSON.stringify({ ctx: host.ANCHOR_CTX, first, second, a1, a2,",
    '  byQuote: strip(edit.applyTrackedEdit(text, q, "Not yet.")), bySpan24: strip(edit.applyTrackedEdit(text, s24, "x")),',
    '  bySpan: strip(edit.applyTrackedEdit(text, span, a2.anchor.prefix + "Not yet." + a2.anchor.suffix)) }));',
  ].join("\n");
  const r = spawnSync(process.execPath, ["--input-type=module", "-e", driver], {
    encoding: "utf8", timeout: 60000,
    env: { ...process.env, RECUR_HOST: path.join(REPO, "tools", "file-comments-host.mjs"),
      RECUR_EDIT: path.join(REPO, "vendor", "track-changents", "cli", "track-edit.mjs"), RECUR_FIXTURE: FIXTURE },
  });
  assert.equal(r.status, 0, "the host and the CLI import cleanly: " + r.stderr);
  return JSON.parse(r.stdout) as HostSays;
}

test("ANCHOR_CTX is the engine's default context and the host's: 24, pinned at both sources", () => {
  assert.equal(ANCHOR_CTX, 24);
  assert.match(HOST, /^export const ANCHOR_CTX = 24;$/m, "the host's constant — uniqueAnchor starts here and widens from here");
  assert.match(ENGINE, /const c = ctx == null \? 24 : ctx;/, "engine.js makeAnchor's default, what track-comment and the other editors write");
  assert.match(MODEL, /else if \(c\.anchor && typeof c\.anchor\.quote === "string" && c\.anchor\.quote\) head = passageDesc\(c\.anchor\);/, "describeComment routes every anchored comment through passageDesc, so the injected-voice scan reaches its phrases");
});

test("a passage unique at the default context keeps the plan's form, with or without anchorAt", () => {
  const q = "shipping the cache in v1.2";
  const at = TEXT.indexOf(q);
  assert.ok(at > 0 && count(TEXT, q) === 1);
  const a = anchorAt(TEXT, at, at + q.length, 24);
  assert.equal(anchorWidened(a), false);
  assert.equal(passageDesc(a), 'on "shipping the cache in v1.2"');
  assert.equal(describeComment(passage(T0 + "-" + at, T0, "Which cache?", a, at), []), 'on "shipping the cache in v1.2"', "anchorAt alone adds nothing: the position is the painter's, not the message's");
  const withoutAt: StoreComment = { ...passage(T0 + "-" + at, T0, "Which cache?", a, at), anchorAt: undefined };
  assert.equal(describeComment(withoutAt, []), 'on "shipping the cache in v1.2"', "a comment from before the follow-on reads as it did");
  const long: Anchor = { quote: "a".repeat(50), prefix: "b".repeat(24), suffix: "c".repeat(24) };
  assert.equal(passageDesc(long), 'on "' + "a".repeat(40) + '"', "the 40-character cut, unchanged");
  const bare: Anchor = { quote: "Ship it.", prefix: "", suffix: "" };
  assert.equal(passageDesc(bare), 'on "Ship it."', "no context at all is not a widened anchor");
});

test("the anchor the host stores for the second of two identical passages names the copy by its surroundings, and the CLI accepts exactly that text", () => {
  const h = askHost();
  assert.equal(h.ctx, ANCHOR_CTX);
  assert.deepEqual([h.first, h.second], [FIRST, SECOND]);
  // the browser's anchors for the two copies are byte-identical at 24; the host widened both to 48 and no further
  assert.deepEqual(anchorAt(TEXT, FIRST, FIRST + QUOTE.length, 24), anchorAt(TEXT, SECOND, SECOND + QUOTE.length, 24), "the tie the follow-on exists for");
  assert.deepEqual(h.a2, { anchor: anchorAt(TEXT, SECOND, SECOND + QUOTE.length, 48), unique: true });
  assert.deepEqual(h.a1, { anchor: anchorAt(TEXT, FIRST, FIRST + QUOTE.length, 48), unique: true });
  assert.ok(anchorWidened(h.a1.anchor) && anchorWidened(h.a2.anchor), "the model reads the host's widening off the stored fields");
  // the desc: the quote, then the copy by its whole surroundings, JSON-quoted so the line breaks stay escapes
  const d2 = passageDesc(h.a2.anchor);
  assert.equal(d2, 'on "Ship it.", the one after " 2\\n\\nThe tests pass on every supported platform. " and before "\\nNo regressions were seen in the nightly run.\\n"');
  const d1 = passageDesc(h.a1.anchor);
  assert.equal(d1, 'on "Ship it.", the one after " 1\\n\\nThe tests pass on every supported platform. " and before "\\nNo regressions were seen in the nightly run.\\n\\n#"');
  assert.notEqual(d1, d2, "the two copies read differently to the session");
  assert.ok(!d1.includes("\n") && !d2.includes("\n"), "one line each: the message's `Comment <id> (…):` line survives");
  assert.doesNotMatch(d1 + d2, ROMP_NOUNS, "the person's voice");
  // what the session does with it: --old as the quote is refused, as the engine's 24 characters is refused, and as the
  // surroundings the message names it lands — on the second copy
  assert.match(h.byQuote.error || "", /not unique/, "the message's quote alone is an --old the CLI refuses");
  assert.match(h.bySpan24.error || "", /not unique/, "and so is the browser's 24-character span — the surroundings the desc names go further");
  assert.equal(h.bySpan.error, undefined);
  assert.equal(h.bySpan.from, SECOND - h.a2.anchor.prefix.length, "the widened span lands once, at the chosen copy");
  assert.equal(count(TEXT, h.a2.anchor.prefix + QUOTE + h.a2.anchor.suffix), 1);
  assert.equal(count(TEXT, QUOTE), 2);
});

test("the clause names only the sides the file has, and escapes what a context can hold", () => {
  // a recurring passage at the very start of a file: no prefix to name, the suffix widened past 24
  const start: Anchor = { quote: "Ship it.", prefix: "", suffix: "\n\nThe tests pass on every supported platform." };
  assert.ok(anchorWidened(start));
  assert.equal(passageDesc(start), 'on "Ship it.", the one before "\\n\\nThe tests pass on every supported platform."');
  // …and at the very end, only a prefix
  const end: Anchor = { quote: "Ship it.", prefix: "The tests pass on every supported platform. ", suffix: "" };
  assert.equal(passageDesc(end), 'on "Ship it.", the one after "The tests pass on every supported platform. "');
  // quotation marks and a tab inside the context are JSON escapes, never a second unescaped quote on the line
  const quoted: Anchor = { quote: "Ship it.", prefix: 'He said "ready", then\ttyped: ', suffix: "\nNo regressions were seen in the nightly run." };
  assert.equal(passageDesc(quoted), 'on "Ship it.", the one after "He said \\"ready\\", then\\ttyped: " and before "\\nNo regressions were seen in the nightly run."');
  // one side over the default is enough: the other side may sit at the file's bound
  const oneSide: Anchor = { quote: "Ship it.", prefix: "x".repeat(25), suffix: "" };
  assert.equal(anchorWidened(oneSide), true);
  assert.equal(anchorWidened({ quote: "Ship it.", prefix: "x".repeat(24), suffix: "y".repeat(24) }), false);
  // a sidecar anyone can edit: a missing side is not a widened one
  assert.equal(anchorWidened({ quote: "Ship it." } as unknown as Anchor), false);
  assert.equal(passageDesc({ quote: "Ship it.", prefix: "x".repeat(30) } as unknown as Anchor), 'on "Ship it.", the one after "' + "x".repeat(30) + '"');
});

test("Send to session carries the clause on the message's Comment line, and the card's reference stays the quote", () => {
  const h = askHost();
  const one = passage(T0 + 1000 + "-" + FIRST, T0 + 1000, "Say it once.", h.a1.anchor, FIRST);
  const two = passage(T0 + 2000 + "-" + SECOND, T0 + 2000, "Not yet.", h.a2.anchor, SECOND);
  const s = status({
    store: { v: 3, path: "docs/report.md", suggestions: [], comments: [one, two] },
    unsent: { comments: [one.id, two.id], replies: [], accepted: 0, rejected: 0, watermark: null },
  });
  const parts = sendParts(s);
  assert.deepEqual(parts.comments.map((c) => c.desc), [passageDesc(h.a1.anchor), passageDesc(h.a2.anchor)]);
  const msg = buildSendMessage({ absPath: ABS, comments: parts.comments, accepted: 0, rejected: 0, tracked: true });
  const lines = msg.split("\n");
  assert.equal(lines[0], "[obsidian-diff] I left 2 comments on " + ABS + ".");
  assert.ok(lines.includes("Comment " + two.id + " (" + passageDesc(h.a2.anchor) + "):"), "the kernel prints the desc verbatim on this line, so this is what the session reads");
  assert.ok(lines.includes("Comment " + one.id + " (" + passageDesc(h.a1.anchor) + "):"));
  assert.equal(lines.filter((l) => l.startsWith("Comment ")).length, 2, "no desc broke its line");
  assert.equal(lines.indexOf("Not yet."), lines.indexOf("Comment " + two.id + " (" + passageDesc(h.a2.anchor) + "):") + 1, "the body follows its own line");
  assert.doesNotMatch(msg.split("To respond:")[0], ROMP_NOUNS);
  // the panel: the collapsed card names the passage as before — the highlight, placed by anchorAt, says which copy
  const cards = cardModel(s.store, []);
  assert.deepEqual(cards.map((c) => [c.kind, c.ref, c.anchorAt]), [["passage", "Ship it.", FIRST], ["passage", "Ship it.", SECOND]]);
});

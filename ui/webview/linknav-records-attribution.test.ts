// The rounds the link-navigation follow-on's records name, held to the section's own convention (plans/markdown-viewer.md,
// "Follow-on: Link navigation (2026-09-19)", the opening paragraph). The convention: the branch's adversarial review before
// the PR ran two rounds, "the review's round 1 and round 2"; the maintainer's review of the PR is "the file review", with the
// rounds it has ruled enumerated there; the author's own verification after each round's fixes is "the author's closing pass
// after that round", never a round, and its findings carry the ids behaviour-N, records-N and coverage-N, which no fixlist of
// the file review holds. The file review's round 3 (tests-2) asked for a pin over the population of these attributions, and
// its round 4 (rules-1) re-ruled the pin onto the STRUCTURAL rule: the pin built after the file review's round 3 matched one
// string, the branch's review named with a round over 2, and the commits that built it credited the author's closing pass to
// a fourth round of the file review, which no maintainer had run at that head, in twelve lines of the tree, the ledger's
// where: line, a comment wrapped over two lines and the PR body; a string the pin did not hold could not fail it. The rule
// here, every part of it read off the convention paragraph: every "round N" a record names belongs to the review named
// nearest before it in the same unit of text, and N is a round the convention enumerates for that review; a pass of the
// author's has no rounds, so "round N" after a pass anchor fails; an id of the author's family stands only in a unit that has
// named a pass before it, so crediting the pass's finding to a round of the file review fails whatever the round; and a
// "round N" with no review named before it in its unit fails, since nothing can be checked about it. A review outside the
// section's convention (a "Slice 7 review") is not the section's to enumerate and is left alone.
// Read as the language reads it (source-units.ts, the one reader the refused-state pin in file-view-figure-shapes.test.ts
// shares): a TS or JS module's comments as text with wrapped lines joined and its string literals by value, so a phrase
// naming a round is one phrase whether its apostrophe is bare, escaped inside a JS string or typographic (the file review's
// round 4, tests-2: the earlier pin was keyed on one spelling of the apostrophe and passed the escaped form its two scanned
// modules used); a Markdown or Python file as paragraphs, Python with backslash escapes folded (the compiler does not read
// Python), which the message says. Two roads, as the author's closing pass after the file review's round 3 (behaviour-6) set
// them: (1) in every checkout the files the branch created (a roster), the plan's section, the guide's Links paragraph, the
// browser plan's pointer paragraph and the units of file-view.ts that name the file review (file-view.ts also carries the
// viewer project's own review, whose rounds this section does not enumerate, so its units naming only "the review" are road
// 2's); (2) where origin/main is known and the merge-base with it is neither origin/main nor HEAD, every "round N" and every id on a line the branch
// added since the merge-base, in every file it changed, judged in the unit that carries it (a modified file's untouched
// lines are context, never the charge: a stylesheet's block carries other projects' rounds around the lines this branch
// added), and the roster checked against the diff's added files. The gate
// on the merge-base (the file review's round 4, extra8-1): with the merge-base at origin/main the diff would be the whole
// history over main's tip, which is what a later local branch, a batch head, main itself, or this branch right after merging
// origin/main all look like, and on each the roster equality would fail for a reason that is not a defect; road 2 runs on the
// open PR branch once main has moved past the branch's last merge, and the diagnostic says which road ran. Synthetic values
// only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { execFileSync } from "node:child_process";
import { comments, lineAt, literals, proseUnits, unitsOf, type Unit } from "./source-units";

const REPO = path.resolve(process.cwd(), "..");
const read = (rel: string): string => fs.readFileSync(path.join(REPO, rel), "utf8");
const exists = (rel: string): boolean => fs.existsSync(path.join(REPO, rel));

/** The files the branch created (road 2 checks this roster against the diff's added files where it runs). */
export const CREATED = [
  "tests/test_guide_trail_chords_and_figure_button.py",
  "tools/markdown-viewer-plan-linknav-review.test.mjs",
  "tools/markdown-viewer-plan-linknav.test.mjs",
  "ui/webview/file-figure-open-browser.test.ts",
  "ui/webview/file-figure-open.test.ts",
  "ui/webview/file-trail-browser.test.ts",
  "ui/webview/file-trail.test.ts",
  "ui/webview/file-trail.ts",
  "ui/webview/file-view-figure-chosen-browser.test.ts",
  "ui/webview/file-view-figure-chosen.test.ts",
  "ui/webview/file-view-figure-floor-browser.test.ts",
  "ui/webview/file-view-figure-recent-browser.test.ts",
  "ui/webview/file-view-figure-shapes-browser.test.ts",
  "ui/webview/file-view-figure-shapes.test.ts",
  "ui/webview/file-view-figure-state-browser.test.ts",
  "ui/webview/linknav-records-attribution.test.ts",
  "ui/webview/source-units.ts",
  "upstream/2026-09-19-linknav-trail-back-forward.md",
];

// ── the convention, read from the section ──────────────────────────────────────────────────────────
const plan = read("plans/markdown-viewer.md");
const HEAD = "## Follow-on: Link navigation (2026-09-19)";
const headAt = plan.indexOf("\n" + HEAD + "\n");
assert.ok(headAt >= 0, "the follow-on section is in the plan");
const nextAt = plan.indexOf("\n## ", headAt + 1);
const sectionStart = headAt + 1;
const sectionText = plan.slice(sectionStart, nextAt < 0 ? plan.length : nextAt);
const sectionLine = plan.slice(0, sectionStart).split("\n").length;
/** The section's paragraphs, their lines numbered in the plan. */
const sectionUnits = (): Unit[] => proseUnits(sectionText).map((u) => ({ ...u, line: u.line + sectionLine - 1, endLine: u.endLine + sectionLine - 1 }));

export type Reviews = { branch: Set<number>; file: Set<number>; ids: string[] };
/** What the convention paragraph gives each review: the branch's review "round 1 and round 2", the file review "round 1 to
 *  round N", and the id family of the author's passes. Asserts the paragraph states all three and names the pass as never a
 *  round. */
export function conventionOf(paragraph: string): Reviews {
  const branch = /named below as the review's round 1 and round 2;/.exec(paragraph);
  assert.ok(branch, "the convention names the branch's review's two rounds");
  const file = /are named the file review's round 1 to round (\d+), the rounds it has ruled/.exec(paragraph);
  assert.ok(file, "the convention enumerates the file review's rounds (round 1 to round N)");
  const ids = /is named the author's closing pass after that round, never a round of either review, and its findings carry the ids ((?:[a-z]+-N(?:, | and ))+)/.exec(paragraph);
  assert.ok(ids, "the convention names the author's passes as passes, never rounds, with their id family");
  const n = Number(file![1]);
  assert.ok(n >= 1 && n < 100, "a plausible count of file-review rounds: " + n);
  const family = Array.from(ids![1].matchAll(/([a-z]+)-N/g), (m) => m[1]);
  assert.ok(family.length >= 1, "the id family: " + JSON.stringify(family));
  return { branch: new Set([1, 2]), file: new Set(Array.from({ length: n }, (_, i) => i + 1)), ids: family };
}

type Who = "file" | "branch" | "other" | "pass";
const ANCHORS: [RegExp, Who][] = [
  [/\bfile review\b/g, "file"],
  [/\bSlice \d+ review\b/g, "other"],
  [/\breview\b/g, "branch"],
  [/\b(?:closing|verification|verifier's|author's|own) pass(?:es)?\b|\bverifier\b/g, "pass"],
];
/** Every "round N" and every id of the author's family in a unit, judged against the reviews named before it: the faults,
 *  each a sentence with the offset in `text` of the phrase it is about. */
export type Fault = { at: number; fault: string };
export function roundFaults(text: string, reviews: Reviews): Fault[] {
  const anchors: { at: number; end: number; who: Who }[] = [];
  for (const [re, who] of ANCHORS) for (const m of text.matchAll(re)) anchors.push({ at: m.index!, end: m.index! + m[0].length, who });
  // "review" inside "file review" or "Slice 7 review" is that anchor, not the branch's
  const kept = anchors.filter((a) => a.who !== "branch" || !anchors.some((b) => b.who !== "branch" && b.at <= a.at && a.end <= b.end));
  kept.sort((a, b) => a.at - b.at);
  const faults: Fault[] = [];
  const quoteAt = (m: RegExpMatchArray): string => {
    const at = Math.max(0, m.index! - 60);
    return JSON.stringify((at > 0 ? "..." : "") + text.slice(at, m.index! + m[0].length + 30));
  };
  const fileMax = Math.max(...reviews.file);
  for (const m of text.matchAll(/\bround[- ](\d+)\b/gi)) {
    const n = Number(m[1]);
    const before = kept.filter((a) => a.end <= m.index!);
    const near = before.length ? before[before.length - 1] : null;
    if (!near) faults.push({ at: m.index!, fault: quoteAt(m) + ": names round " + n + " of no review (nothing is named before it in this unit); write the file review's round " + n + ", the review's round " + n + ", or the author's closing pass after the file review's round M" });
    else if (near.who === "pass") faults.push({ at: m.index!, fault: quoteAt(m) + ": a pass of the author's has no rounds; it is the author's closing pass after the file review's round M, with the finding's id kept" });
    else if (near.who === "file" && !reviews.file.has(n)) faults.push({ at: m.index!, fault: quoteAt(m) + ": the file review's round " + n + " is not one the convention enumerates (rounds 1 to " + fileMax + "); a round the maintainer has ruled is named in the convention first" });
    else if (near.who === "branch" && !reviews.branch.has(n)) faults.push({ at: m.index!, fault: quoteAt(m) + ": the branch's review ran rounds 1 and 2 alone; a later round is the file review's (write the file review's round " + n + ") or the author's closing pass" });
  }
  const idRe = new RegExp("\\b(?:" + reviews.ids.join("|") + ")-\\d+\\b", "g");
  for (const m of text.matchAll(idRe)) {
    if (!kept.some((a) => a.who === "pass" && a.end <= m.index!)) faults.push({ at: m.index!, fault: quoteAt(m) + ": an id of the author's family (" + reviews.ids.map((p) => p + "-N").join(", ") + ") with no pass named before it in this unit; the finding is the author's closing pass's, never a round's of the file review" });
  }
  return faults;
}

/** The faults of a set of units, each prefixed with its label and the line of the phrase; `keep` narrows them to the lines a
 *  road is about (road 2: the lines the branch added), the unit still the context every phrase is judged in. */
const faultsOf = (label: string, units: Unit[], reviews: Reviews, keep: (line: number) => boolean = () => true): string[] =>
  units.flatMap((u) => roundFaults(u.text, reviews).map((f) => ({ line: lineAt(u, f.at), fault: f.fault })).filter((f) => keep(f.line)).map((f) => label + ":" + f.line + " " + f.fault));

const convention = (): Reviews => {
  const para = sectionUnits().find((u) => u.text.includes("named below as the review's round 1 and round 2"));
  assert.ok(para, "the section's opening paragraph carries the naming convention");
  return conventionOf(para!.text);
};

test("the reader (source-units.ts): a literal's value is the program's whatever the quoting or the escape, a run of line comments and a block comment are one unit each with wrapped lines joined, an offset maps back to the source line that carries it, and a Python paragraph has its escapes folded", () => {
  const src = "const a = 'x\\'y';\nconst b = \"x'y\";\nconst c = `x'y`;\nconst d = `${a}x'y`;\nconst e = 'fai\\x6ced';\nconst f = /x'y/g;\n// one\n// two 'q'\nlet g;\n/** three\n *  four\n */\n// five\n\n// six\n";
  const lits = literals(src, "probe.ts");
  assert.deepEqual(lits.map((l) => [l.kind, l.text, l.line]), [["string", "x'y", 1], ["string", "x'y", 2], ["template", "x'y", 3], ["template", "", 4], ["template", "x'y", 4], ["string", "failed", 5], ["regex", "/x'y/g", 6]], "values, not spellings");
  const cs = comments(src, "probe.ts");
  assert.deepEqual(cs.map((c) => [c.text, c.line, c.endLine]), [["one two 'q'", 7, 8], ["three four", 10, 12], ["five", 13, 13], ["six", 15, 15]], "a run and a block, each one unit; a blank line ends a run; a quote inside a literal opened no comment");
  assert.equal(lineAt(cs[0], cs[0].text.indexOf("two")), 8, "the second line's words map to line 8");
  assert.equal(lineAt(cs[1], cs[1].text.indexOf("four")), 11);
  const py = proseUnits("a = 'it\\'s round'\nb = 2\n\nc = 3\n", true);
  assert.deepEqual(py.map((u) => [u.text, u.line, u.endLine]), [["a = 'it's round' b = 2", 1, 2], ["c = 3", 4, 4]], "paragraphs, the escape folded");
  assert.equal(lineAt(py[0], py[0].text.indexOf("b = 2")), 2, "the fold moves the offsets and the starts follow");
});

test("the convention: the branch's review has rounds 1 and 2, the file review's rounds are enumerated, the author's passes are never rounds and own an id family; the rule reads a unit's nearest review and refuses a round the convention does not give it, a pass with a round, an id of the pass's family with no pass named, and a round with no review named", () => {
  const r = convention();
  assert.deepEqual([...r.branch], [1, 2]);
  assert.ok(r.file.size >= 4 && r.file.has(1) && r.file.has(r.file.size), "the file review's rounds 1 to " + r.file.size);
  assert.deepEqual(r.ids, ["behaviour", "records", "coverage"]);
  const two: Reviews = { branch: new Set([1, 2]), file: new Set([1, 2, 3, 4]), ids: ["behaviour", "records", "coverage"] };
  // the probes are assembled, so this module's own literals name no round and no id at rest
  const F = "the file review's round ", B = "the review's round ", P = "the author's closing pass ";
  assert.deepEqual(roundFaults(F + 2 + " re-decided this on the rule the record of its round " + 1 + " had said did not exist", two), []);
  assert.deepEqual(roundFaults(B + 1 + " found it; " + F + 3 + " (tests-2) pinned it", two), []);
  assert.deepEqual(roundFaults(P + "after " + F + 3 + " (records-" + 3 + ") said so", two), []);
  assert.deepEqual(roundFaults("measured in the Slice 7 review's round " + 9, two), [], "another review's rounds are not this section's");
  assert.equal(roundFaults(F + 5 + " found it", two).length, 1, "a file-review round past the enumeration");
  assert.equal(roundFaults("the file review\\'s round " + 9 + " found it", two).length, 1, "the escaped apostrophe is the same phrase");
  assert.equal(roundFaults(B + 3 + " found it", two).length, 1, "a branch-review round it never had");
  assert.equal(roundFaults(P + "(round " + 4 + ", behaviour-" + 2 + ") found it", two).length, 1, "a pass named as a round (the id after the pass is fine)");
  assert.equal(roundFaults("the verifier's round-" + 6 + " probe", two).length, 1, "a verifier's pass named as a round");
  assert.equal(roundFaults("since round " + 2 + " a failed figure opens nothing", two).length, 1, "a round with no review named");
  assert.equal(roundFaults("(" + F + 4 + ", records-" + 3 + ")", two).length, 1, "the pass's finding credited to a round of the file review: the id has no pass before it");
  assert.equal(roundFaults("recorded by " + F + 4 + " (rules-" + 1 + ")", two).length, 0, "the maintainer's own ids are not the family's");
  assert.deepEqual(roundFaults("the review ran two rounds; the pin holds a round-trip", two), [], "no round number, no claim");
});

test("road 1, every checkout: the files the branch created, the plan's section, the guide's Links paragraph, the browser plan's pointer and file-view.ts's units naming the file review name no round outside the convention and no finding of the author's outside a pass; road 2, where the merge-base tells the branch's delta from main's tip: every unit the branch added or touched, and the roster is the diff's added files", (t) => {
  const reviews = convention();
  const faults: string[] = [];
  for (const f of CREATED) {
    assert.ok(exists(f), f + " exists (a created file of the branch; a rename moves it here too)");
    faults.push(...faultsOf(f, unitsOf(f, read(f)), reviews));
  }
  faults.push(...faultsOf("plans/markdown-viewer.md (the follow-on section)", sectionUnits(), reviews));
  const guide = read("docs/guide.md");
  const linksAt = guide.indexOf("**Links in a file.**");
  assert.ok(linksAt >= 0, "the guide's Links in a file paragraph");
  faults.push(...faultsOf("docs/guide.md (Links in a file)", proseUnits(guide.slice(linksAt, guide.indexOf("\n\n", linksAt))), reviews));
  const browserPlan = read("plans/file-browser.md");
  const pointerAt = browserPlan.indexOf("Since 2026-09-19 the viewer keeps a trail of its own");
  assert.ok(pointerAt >= 0, "the browser plan's pointer paragraph");
  faults.push(...faultsOf("plans/file-browser.md (the pointer)", proseUnits(browserPlan.slice(pointerAt, browserPlan.indexOf("\n\n", pointerAt))), reviews));
  const viewer = read("ui/webview/file-view.ts");
  const viewerUnits = unitsOf("ui/webview/file-view.ts", viewer).filter((u) => /\bfile review\b/.test(u.text));
  assert.ok(viewerUnits.length >= 10, "file-view.ts names the file review in its figure and trail comments: " + viewerUnits.length);
  faults.push(...faultsOf("ui/webview/file-view.ts (units naming the file review)", viewerUnits, reviews));
  assert.deepEqual(faults, [], "every round a record names is a round the convention gives the review it names, and every finding of the author's family follows a pass (TS and JS read by the compiler, comments joined and literals by value; Markdown as paragraphs; Python as paragraphs with backslash escapes folded)");
  // road 2
  const git = (...args: string[]): string => execFileSync("git", args, { cwd: REPO, encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] }).trim();
  let base: string | null = null;
  let main: string | null = null;
  try { base = git("merge-base", "origin/main", "HEAD"); main = git("rev-parse", "origin/main"); } catch { base = null; }
  if (!base) { t.diagnostic("road 2 did not run: origin/main is not known in this checkout (CI's default-depth checkout); road 1 read the created files, the section, the guide, the pointer and file-view.ts's file-review units"); return; }
  const head = git("rev-parse", "HEAD");
  if (base === main || base === head) {
    t.diagnostic("road 2 did not run: the merge-base with origin/main is " + (base === head ? "HEAD (main, or a branch merged into it)" : "origin/main itself (a branch cut from main's tip, a batch head, or this branch just after merging origin/main)") + ", so the diff since it is not this follow-on's delta alone; road 2 runs on the open PR branch once main has moved past the branch's last merge. Road 1 ran.");
    return;
  }
  const status = git("diff", "--name-status", base, "HEAD").split("\n").filter(Boolean).map((l) => l.split("\t"));
  const created = status.filter((s) => s[0] === "A").map((s) => s[1]).sort();
  assert.deepEqual(created, [...CREATED].sort(), "the roster is the diff's added files since " + base + " (a file created later joins the roster)");
  const touched = status.filter((s) => s[0] !== "A" && s[0] !== "D").map((s) => s[s.length - 1]);
  const faults2: string[] = [];
  for (const f of touched) {
    const ranges: [number, number][] = [];
    for (const m of git("diff", "-U0", base, "HEAD", "--", f).matchAll(/^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@/gm)) {
      const n = m[2] === undefined ? 1 : Number(m[2]);
      if (n > 0) ranges.push([Number(m[1]), Number(m[1]) + n - 1]);
    }
    if (!ranges.length) continue;
    const units = unitsOf(f, read(f)).filter((u) => ranges.some(([a, b]) => u.line <= b && u.endLine >= a));
    faults2.push(...faultsOf(f, units, reviews, (line) => ranges.some(([a, b]) => line >= a && line <= b)));
  }
  assert.ok(touched.length > 0, "the branch touched files since " + base);
  assert.deepEqual(faults2, [], "every round and every id on a line the branch added since " + base + " is judged in its unit and passes (road 2)");
  t.diagnostic("road 2 ran: " + touched.length + " touched files read since " + base + ", the added lines judged in their units");
});

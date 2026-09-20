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
// author's has no rounds, so "round N" after a pass anchor fails; an id of the author's family stands only where the review
// named nearest before it is the author's pass (a pass named by the round it followed, "the author's closing pass after the
// file review's round 4", is one name through its digits), so crediting the pass's finding to a round of the file review
// fails whatever the round, in a unit that names the pass elsewhere too (the file review's round 5, correctness-3 with
// regression-1: the id had stood after ANY pass named earlier in the unit, and the round-4 HIGH's exact misattribution passed
// beside a pass); and a "round N" with no review named before it in its unit fails, since nothing can be checked about it. A
// review outside the section's convention (a "Slice 7 review") is not the section's to enumerate and is left alone.
// What the reader takes as a round, stated so a green here is read for what it covers (the author's closing pass after the
// file review's round 4, guards-2 with attribution-and-gates-3: the plural form passed silently while the message claimed
// every round): the word round or rounds, a hyphen or whitespace (a line break inside a literal or a wrapped comment
// included), and digits, bare or wrapped in Markdown emphasis or code markers ("round **N**", "round `N`"; the file review's
// round 5, extra6-2: one space or hyphen alone was read, so an escaped newline in a literal and a plan's marked-up digits
// went unread), and after rounds a comma list or a to-range ("rounds N, M and K", "rounds N to M", the range expanded) as
// the set of those rounds, each judged against the same nearest review; an ordinal ("the fourth round"), a spelled-out
// number ("round four") and an abbreviation ("R4") are not read. An id is the family word, a hyphen and digits
// ("behaviour-N"); the spaced form ("behaviour N") is not read.
// Read as the language reads it (source-units.ts, the one reader the refused-state pin in file-view-figure-shapes.test.ts
// shares): a TS or JS module's comments as text with wrapped lines joined and each string the program sees as one value as
// one unit with that value (either quote, every escape resolved, a + chain of literals as the value it computes, a template's
// spans joined with each hole kept as its source text), so a phrase naming a round is one phrase whether its apostrophe is
// bare, escaped inside a JS string or typographic (the file review's round 4, tests-2: the earlier pin was keyed on one
// spelling of the apostrophe and passed the escaped form its two scanned modules used) and whether it is one literal or
// several joined by + or split by a hole (the file review's round 5, correctness-2 with extra6-1: a phrase split across
// tokens had sat in no unit); what stays outside the read, a value assembled at run time (a join, a concat, a hole's value,
// the part of a chain after a non-literal operand), the reader's header lists and the messages say; a Markdown file as
// paragraphs, a Python file as paragraphs with its literals cooked as Python cooks them and adjacent literals glued (the
// compiler does not read Python), which the message says. Two roads. Road 1, in every checkout, is a RULE over the tree
// (the file review's round 5, extra5-1 with tests-1, extra5-2 and correctness-5, in the refuters' corrected form: the road had
// read a hand-written roster of eighteen files, and the road that checked the roster against the diff ran in no checkout
// that CI makes, so the roster was the guard). The population is every path git lists at the repo root, tracked or
// untracked and not ignored (`git ls-files --cached --others --exclude-standard`), read from the WORKING TREE, so a new
// uncommitted file is judged like a committed one (road 2's diff lists tracked paths alone, so a phrase planted in a new
// file was a false green there; the file review's round 5, correctness-5 with tests-6); a path that is not a regular file
// or a symlink to one is skipped and counted (a dangling symlink; a symlink to a directory, which crashed the prototype's
// read), and a file with a NUL byte in its first 8 KiB is binary and skipped. The candidates are the files whose text
// names the file review or carries an id of the author's family (roadOneViewerUnit over the whole text, the narrow
// predicate: a loose one, every "round N" in the tree, faulted about 871 records of other projects' rounds by the round's
// count) and the files the branch created (CREATED, kept as an existence roster: each must be in the population, and each
// is judged in FULL, every unit of it, since the predicate alone drops the units naming only "the review"); the plan's
// follow-on section, the guide's Links paragraph and the browser plan's pointer are this follow-on's records by their place
// and are judged in full too. Every other candidate's units that carry the vocabulary are judged KEYED on the review named
// (the file review's round 5, regression-2: file-view.ts is shared, and a unit there naming another review's round, or a
// unit in a file another PR brought in, had been judged against this follow-on's enumeration, a red for everyone on a
// record that was not ours): a round or an id is this follow-on's only where the review named nearest before it is the
// file review or the author's pass as the convention names it (the author's closing pass, a verifier's pass; not any word
// "pass", since a caller's own pass is code); a phrase whose nearest review is another (a Slice N review, a fork PR review,
// the bare "review" outside the roster) or none is that review's or no one's, left alone and counted in the diagnostic
// (the gate-before-adoption fix the merge of the fork's main brought in names its rounds the fork PR review's and its
// findings guards-N, the same family word). Floors that fail on an empty derivation: the population at least a
// thousand files, the candidates at least ten, the units judged at least two hundred; and the count of this follow-on's
// units in file-view.ts is asserted equal to the derived count at the swept head, the lines printed beside it, so a deleted
// or an added attribution there moves it and the fix is to re-derive, never to fit (the file review's round 5,
// correctness-6 with tests-5 and extra8-4: a floor of ten stood against fourteen). The diagnostic prints the candidate list
// for a human to compare with the PR's added files, which the roster equality of road 2 did where it ran. Road 2 is kept and
// disclosed: it runs in no CI job and in none after the merge (the plan's Tests paragraph states this once, with the
// checkouts). Where the merge-base with origin/main tells this branch's delta from main's tip, it judges every "round N"
// and every id on a line the branch added since the merge-base, in every tracked file it changed, in the unit that carries
// it under the full rule (a modified file's untouched lines are context, never the charge: a stylesheet's block carries
// other projects' rounds around the lines this branch added). The gate on road 2 has two parts, both read off git (the
// file review's round 4, extra8-1, taking its refuter's correction): the merge-base is not origin/main itself, and the
// diff since the merge-base adds this module. One part alone is not the gate. With the merge-base at origin/main the diff
// is the whole history over main's tip, which is what main itself, a branch or a batch head cut from main's tip and this
// branch right after merging origin/main all look like; and once the follow-on has landed, a later branch whose fork point
// main has moved past has a merge-base off origin/main too, while its diff adds that branch's files and not this module
// (the roster equality before this gate failed on every such branch in the repo, in both refuters' scratch repos). So road
// 2 runs on this follow-on's open PR branch in a clone where origin/main has moved past the branch's last merge of it, and
// the diagnostic says which road ran and, when road 2 stood down, which part of the gate held it. The gate's residual,
// disclosed and not closed: a batch head that main has moved under (a commit landed on main after the batch was cut from
// its tip) has its merge-base off origin/main and a diff that adds this module, so road 2 runs over the batch's whole
// delta. A third part would close it, every first-parent merge since the merge-base merging main alone, and is named for
// the maintainer in the PR body rather than built unruled (the author's closing pass after the file review's round 4,
// attribution-and-gates-2 with records-2). Road 2 diffs the WORKING TREE against the merge-base, not HEAD, so the line
// ranges and the units it reads come from the same bytes and an uncommitted EDIT in a scratch copy is charged like a
// committed one (the same pass, guards-3: a diff against HEAD read no added line for an uncommitted planted phrase, a false
// green for a verifier who edits a copy without committing); an uncommitted NEW file is road 1's, through the population's
// untracked paths, since no diff lists it. Synthetic values only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import { execFileSync } from "node:child_process";
import { comments, lineAt, literals, proseUnits, scriptUnits, unitsOf, type Unit } from "./source-units";

const REPO = path.resolve(process.cwd(), "..");
const read = (rel: string): string => fs.readFileSync(path.join(REPO, rel), "utf8");

/** This module's own path: road 2 runs only where the diff since the merge-base adds it (the second part of its gate). */
const THIS_MODULE = "ui/webview/linknav-records-attribution.test.ts";

/** The files the branch created: an existence roster (each must be in road 1's population) whose files are judged in full,
 *  every unit of them, where the tree rule's predicate selects units by their vocabulary. Road 2 prints the diff's added
 *  files beside it where it runs, for a human to compare. */
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
/** The section's paragraphs, their lines numbered in the plan: the unit's lines and every start it maps offsets through
 *  (the author's closing pass after the file review's round 4, attribution-and-gates-4: with the starts left section-relative,
 *  a fault in the section was charged to a line about seven thousand short of the plan's). */
const sectionUnits = (): Unit[] => proseUnits(sectionText).map((u) => ({ ...u, line: u.line + sectionLine - 1, endLine: u.endLine + sectionLine - 1, starts: u.starts.map((s) => ({ line: s.line + sectionLine - 1, at: s.at })) }));

export type Reviews = { branch: Set<number>; file: Set<number>; ids: string[] };
/** What the convention paragraph gives each review: the branch's review "round 1 and round 2", the file review "round 1 to
 *  round N", and the id family of the author's passes. Asserts the paragraph states all three and names the pass as never a
 *  round. */
export function conventionOf(paragraph: string): Reviews {
  const branch = /named below as the review's round 1 and round 2;/.exec(paragraph);
  assert.ok(branch, "the convention names the branch's review's two rounds");
  const file = /are named the file review's round 1 to round (\d+), the rounds it has ruled/.exec(paragraph);
  assert.ok(file, "the convention enumerates the file review's rounds (round 1 to round N)");
  const ids = /is named the author's closing pass after that round, never a round of either review, and its findings carry the ids ((?:[a-z]+(?:-[a-z]+)*-N(?:, | and ))+)/.exec(paragraph);
  assert.ok(ids, "the convention names the author's passes as passes, never rounds, with their id family");
  const n = Number(file![1]);
  assert.ok(n >= 1 && n < 100, "a plausible count of file-review rounds: " + n);
  const family = Array.from(ids![1].matchAll(/([a-z]+(?:-[a-z]+)*)-N/g), (m) => m[1]);
  assert.ok(family.length >= 1, "the id family: " + JSON.stringify(family));
  return { branch: new Set([1, 2]), file: new Set(Array.from({ length: n }, (_, i) => i + 1)), ids: family };
}

type Who = "file" | "branch" | "other" | "pass";
/** The reviews a unit can name, each by its own words: the file review; another project's review by a qualifier (a Slice N
 *  review); the bare "review" (the branch's, inside this follow-on's records); and the author's pass as the convention names
 *  it, the author's closing pass or a verifier's pass, never any word "pass" (the file review's round 5, regression-2: "the
 *  caller's own pass" in a shared test is code, and had anchored a round after it as a pass's). */
const ANCHORS: [RegExp, Who][] = [
  [/\bfile review\b/g, "file"],
  [/\bSlice \d+ review\b/g, "other"],
  [/\breview\b/g, "branch"],
  [/\b(?:closing|verification|verifier's|author's) pass(?:es)?\b|\bverifier's\b/g, "pass"],
];
/** A pass named by the round it followed ("the author's closing pass after the file review's round 4") is one name, its span
 *  through the round's digits, and an id after the whole name has the pass as the review named nearest before it. The name is
 *  an anchor for the id road alone: the round inside the name, and a round named after it (a record's "the round-N
 *  condition" after the pass's name), are judged against the review the name says, whose anchor stands inside the name. */
const PASS_NAME_RE = /\b(?:closing|verification|verifier's|author's) pass(?:es)?\b after (?:the |its |that )?(?:file review's |review's )?rounds?[- ]\d+(?:(?:,\s*|\s+(?:and|or|to)\s+)\d+)*/g;
/** A round phrase as the set of rounds it names: `round N` or `round-N`, the digits after a hyphen or any whitespace (a
 *  line break inside a literal too) and bare or wrapped in Markdown emphasis or code markers; after the plural, a comma list
 *  or a `to` range (`rounds N, M and K`, `rounds N to M`, the range expanded). Digits only: an ordinal, a spelled-out number
 *  and an abbreviation are outside the reader, which the messages say. */
const MARK = "(?:\\*\\*|__|[*_`])?";   // Markdown emphasis or code markers around the digits
const ROUND_RE = new RegExp("\\bround(?:-|\\s+)" + MARK + "(\\d+)" + MARK + "(?!\\w)|\\brounds(?:-|\\s+)" + MARK + "(\\d+)" + MARK + "((?:(?:,\\s*|\\s+(?:and|or|to)\\s+)" + MARK + "\\d+" + MARK + ")*)(?!\\w)", "gi");
const roundsOf = (m: RegExpMatchArray): number[] => {
  if (m[1] !== undefined) return [Number(m[1])];
  const out = [Number(m[2])];
  for (const p of m[3].matchAll(/(?:,\s*|\s+(and|or|to)\s+)(?:\*\*|__|[*_`])?(\d+)/g)) {
    const n = Number(p[2]);
    if (p[1] === "to") { for (let k = out[out.length - 1] + 1; k <= n; k++) out.push(k); } else out.push(n);
  }
  return out;
};
/** An id of the author's family: the family word, a hyphen and digits (the spaced form is not read). */
const idPattern = (reviews: Reviews, flags = ""): RegExp => new RegExp("\\b(?:" + reviews.ids.join("|") + ")-\\d+\\b", flags);
/** Road 1's selection of file-view.ts units: those naming the file review, and those carrying an id of the author's family
 *  (a pass misnamed as a round beside its id, in a figure comment that names no review, is judged in every checkout; the
 *  author's closing pass after the file review's round 4, records-1); a unit naming only "the review" is the viewer project's
 *  and road 2's. */
export const roadOneViewerUnit = (text: string, reviews: Reviews): boolean => /\bfile review\b/.test(text) || idPattern(reviews).test(text);
/** Every round phrase and every id of the author's family in a unit, judged against the review named NEAREST before it (the
 *  anchor whose span ends last before the phrase): the faults, each a sentence with the offset in `text` of the phrase it is
 *  about. The id road reads the same nearest anchor as the round road (the file review's round 5, correctness-3 with
 *  regression-1: it had accepted an id when ANY pass was named earlier in the unit, so the pass's finding credited to a round
 *  of the file review passed in every unit that also named the pass, the round-4 HIGH restated as a green). With `keyed`
 *  (the tree rule outside this follow-on's own files) a phrase is judged only where the review named nearest before it is
 *  the file review or the author's pass; a phrase whose nearest review is another, or none, is counted as `foreign` or
 *  `unanchored` and left alone (the file review's round 5, regression-2). */
export type Fault = { at: number; fault: string };
export type Judgement = { faults: Fault[]; judged: number; foreign: number; unanchored: number };
export function roundFaults(text: string, reviews: Reviews, keyed = false): Fault[] {
  return judgeUnit(text, reviews, keyed).faults;
}
export function judgeUnit(text: string, reviews: Reviews, keyed = false): Judgement {
  type Anchor = { at: number; end: number; who: Who };
  const anchors: Anchor[] = [];
  for (const [re, who] of ANCHORS) for (const m of text.matchAll(re)) anchors.push({ at: m.index!, end: m.index! + m[0].length, who });
  // "review" inside "file review" or "Slice 7 review" is that anchor, not the branch's
  const kept = anchors.filter((a) => a.who !== "branch" || !anchors.some((b) => b.who !== "branch" && b.at <= a.at && a.end <= b.end));
  const passNames: Anchor[] = Array.from(text.matchAll(PASS_NAME_RE), (m) => ({ at: m.index!, end: m.index! + m[0].length, who: "pass" as Who }));
  /** The review named nearest before `pos` among `among`: the anchor ending last at or before it. */
  const nearest = (pos: number, among: Anchor[]): Anchor | null => {
    let near: Anchor | null = null;
    for (const a of among) if (a.end <= pos && (!near || a.end > near.end)) near = a;
    return near;
  };
  const forIds = [...kept, ...passNames];
  const faults: Fault[] = [];
  let judged = 0, foreign = 0, unanchored = 0;
  /** Under the keyed rule, whether the phrase is this follow-on's to judge: the review named nearest before it is the file
   *  review or the author's pass. Another review's phrase, or one naming no review, is counted and left alone. */
  const ours = (near: Anchor | null): boolean => {
    if (!keyed || (near && (near.who === "file" || near.who === "pass"))) { judged++; return true; }
    if (near) foreign++; else unanchored++;
    return false;
  };
  const quoteAt = (m: RegExpMatchArray): string => {
    const at = Math.max(0, m.index! - 60);
    return JSON.stringify((at > 0 ? "..." : "") + text.slice(at, m.index! + m[0].length + 30));
  };
  const fileMax = Math.max(...reviews.file);
  for (const m of text.matchAll(ROUND_RE)) {
    const ns = roundsOf(m);
    const list = ns.join(", ");
    const near = nearest(m.index!, kept);
    if (!ours(near)) continue;
    if (!near) faults.push({ at: m.index!, fault: quoteAt(m) + ": names round " + list + " of no review (nothing is named before it in this unit); write the file review's round " + list + ", the review's round " + list + ", or the author's closing pass after the file review's round M" });
    else if (near.who === "pass") faults.push({ at: m.index!, fault: quoteAt(m) + ": a pass of the author's has no rounds; it is the author's closing pass after the file review's round M, with the finding's id kept" });
    else if (near.who === "file") {
      const bad = ns.filter((n) => !reviews.file.has(n));
      if (bad.length) faults.push({ at: m.index!, fault: quoteAt(m) + ": the file review's round " + bad.join(" and ") + " is not one the convention enumerates (its last is round " + fileMax + "); a round the maintainer has ruled is named in the convention first" });
    } else if (near.who === "branch") {
      const bad = ns.filter((n) => !reviews.branch.has(n));
      if (bad.length) faults.push({ at: m.index!, fault: quoteAt(m) + ": the branch's review ran rounds 1 and 2 alone; a later round is the file review's (write the file review's round " + bad.join(" and ") + ") or the author's closing pass" });
    }
  }
  const idRe = idPattern(reviews, "g");
  const named: Record<Who, string> = { file: "the file review", branch: "the branch's review", other: "another review", pass: "the author's pass" };
  for (const m of text.matchAll(idRe)) {
    const near = nearest(m.index!, forIds);
    if (!ours(near)) continue;
    if (!near || near.who !== "pass") faults.push({ at: m.index!, fault: quoteAt(m) + ": an id of the author's family (" + reviews.ids.map((p) => p + "-N").join(", ") + ") where the review named nearest before it is " + (near ? named[near.who] : "no review") + "; the finding is the author's closing pass's, never a round's of the file review, and the pass is named nearest before its id (the author's closing pass after the file review's round M, the id)" });
  }
  return { faults, judged, foreign, unanchored };
}

/** The judgement of a set of units under one label: the faults, each prefixed with the label and the line of the phrase, and
 *  the counts summed; `keep` narrows the faults to the lines a road is about (road 2: the lines the branch added), the unit
 *  still the context every phrase is judged in; `keyed` is the tree rule's scope outside this follow-on's own files. */
type Tally = { faults: string[]; units: number; judged: number; foreign: number; unanchored: number };
function judgeUnits(label: string, units: Unit[], reviews: Reviews, keyed = false, keep: (line: number) => boolean = () => true): Tally {
  const t: Tally = { faults: [], units: units.length, judged: 0, foreign: 0, unanchored: 0 };
  for (const u of units) {
    const j = judgeUnit(u.text, reviews, keyed);
    t.judged += j.judged; t.foreign += j.foreign; t.unanchored += j.unanchored;
    t.faults.push(...j.faults.map((f) => ({ line: lineAt(u, f.at), fault: f.fault })).filter((f) => keep(f.line)).map((f) => label + ":" + f.line + " " + f.fault));
  }
  return t;
}
const faultsOf = (label: string, units: Unit[], reviews: Reviews, keep: (line: number) => boolean = () => true): string[] => judgeUnits(label, units, reviews, false, keep).faults;

/** Road 1's population: every path git lists at `repo`'s root, tracked or untracked and not ignored (`git ls-files --cached
 *  --others --exclude-standard`), that is a regular file or a symlink to one, relative to `repo` and sorted; a path that is
 *  not (a dangling symlink, a symlink to a directory, a tracked path missing from the working tree) is returned in `skipped`
 *  (the file review's round 5, correctness-5 with tests-6: a new uncommitted file is in the population, which no diff lists;
 *  the prototype's read of a directory symlink crashed the run). */
export function populationOf(repo: string): { files: string[]; skipped: string[] } {
  const listed = execFileSync("git", ["-C", repo, "ls-files", "--cached", "--others", "--exclude-standard", "-z"], { encoding: "utf8", maxBuffer: 64 * 1024 * 1024 });
  const files: string[] = [];
  const skipped: string[] = [];
  for (const rel of new Set(listed.split("\0").filter(Boolean))) {
    let st: fs.Stats;
    try { st = fs.statSync(path.join(repo, rel)); } catch { skipped.push(rel); continue; }   // stat follows a symlink; a dangling one throws
    (st.isFile() ? files : skipped).push(rel);
  }
  return { files: files.sort(), skipped: skipped.sort() };
}
/** Binary by git's own rule of thumb: a NUL byte in the first 8 KiB. */
const isBinary = (buf: Buffer): boolean => { const i = buf.indexOf(0); return i >= 0 && i < 8192; };
/** The 1-based line of an offset in a text. */
const lineOfOffset = (text: string, at: number): number => text.slice(0, at).split("\n").length;
/** The paragraph of a prose file that starts at `marker`, its units numbered in the file's lines, with the span it covers. */
function paragraphAt(text: string, marker: string, what: string): { units: Unit[]; span: [number, number] } {
  const at = text.indexOf(marker);
  assert.ok(at >= 0, what);
  const end = text.indexOf("\n\n", at);
  const first = lineOfOffset(text, at);
  const units = proseUnits(text.slice(at, end < 0 ? text.length : end)).map((u) => ({ ...u, line: u.line + first - 1, endLine: u.endLine + first - 1, starts: u.starts.map((s) => ({ line: s.line + first - 1, at: s.at })) }));
  return { units, span: [first, units.length ? units[units.length - 1].endLine : first] };
}

const convention = (): Reviews => {
  const para = sectionUnits().find((u) => u.text.includes("named below as the review's round 1 and round 2"));
  assert.ok(para, "the section's opening paragraph carries the naming convention");
  return conventionOf(para!.text);
};

test("the reader (source-units.ts): a string the program sees as one value is one unit with that value whatever the quoting, the escape, a + between literals or a hole in a template; a run of line comments and a block comment are one unit each with wrapped lines joined; an offset maps back to the source line that carries it through a starts map built from source positions; a Python paragraph has its literals cooked as Python cooks them", () => {
  const src = "const a = 'x\\'y';\nconst b = \"x'y\";\nconst c = `x'y`;\nconst d = `${a}x'y`;\nconst e = 'fai\\x6ced';\nconst f = /x'y/g;\n// one\n// two 'q'\nlet g;\n/** three\n *  four\n */\n// five\n\n// six\n";
  const lits = literals(src, "probe.ts");
  assert.deepEqual(lits.map((l) => [l.kind, l.text, l.line]), [["string", "x'y", 1], ["string", "x'y", 2], ["template", "x'y", 3], ["template", "${a}x'y", 4], ["string", "failed", 5], ["regex", "/x'y/g", 6]], "values, not spellings; a substitution template is one unit with its hole kept as the source text between ${ and }");
  const cs = comments(src, "probe.ts");
  assert.deepEqual(cs.map((c) => [c.text, c.line, c.endLine]), [["one two 'q'", 7, 8], ["three four", 10, 12], ["five", 13, 13], ["six", 15, 15]], "a run and a block, each one unit; a blank line ends a run; a quote inside a literal opened no comment");
  assert.equal(lineAt(cs[0], cs[0].text.indexOf("two")), 8, "the second line's words map to line 8");
  assert.equal(lineAt(cs[1], cs[1].text.indexOf("four")), 11);
  // a + chain of literals alone is one unit with the value the program computes, folded across lines and parentheses, each
  // operand's characters charged to the operand's line (the file review's round 5, correctness-2 with tests-2 and extra6-1:
  // each token had been a unit, so a phrase split across a + sat in no unit); the probes say "step N", never round, so this
  // module's own literals name no round at rest. The fold is the maximal all-literal subtree: an identifier LAST leaves the
  // literal prefix before it one unit (+ is left-associative), an identifier SECOND leaves every operand its own unit
  const chain = literals("const s = 'the file ' +\n  (\"review's \" + `step ` + 9) +\n  ' found it';\nconst t = 'the file ' + who + ' step ' + 9;\nconst u = 'step ' + n(9);\nconst v = 'the file ' + 'step ' + 9 + who;\nconst w = 1 + 2 + 'a' + (1 + ('b' + 2));\n", "probe.ts");
  assert.deepEqual(chain.map((l) => [l.kind, l.text, l.line, l.endLine]), [["string", "the file review's step 9 found it", 1, 3], ["string", "the file ", 4, 4], ["string", " step ", 4, 4], ["string", "step ", 5, 5], ["string", "the file step 9", 6, 6], ["string", "3a1b2", 7, 7]], "the all-literal chain folded across its lines and its parentheses, a number by the text JS gives it (numbers add until a string joins); an identifier second leaves the operands apart, an identifier last folds the prefix before it");
  assert.deepEqual(chain[0].starts, [{ line: 1, at: 0 }, { line: 2, at: 9 }, { line: 3, at: 24 }], "a start where each operand's line begins");
  assert.equal(lineAt(chain[0], chain[0].text.indexOf("step 9")), 2, "the step is charged to the operand's line");
  assert.equal(lineAt(chain[0], chain[0].text.indexOf("found")), 3);
  // a substitution template is one unit, its spans joined with each hole kept as the source between ${ and } (so a phrase
  // split by a hole is judged whole with the hole named, and a hole in place of the digits is visibly no number); a literal
  // inside a hole is a unit of its own; a tagged template is read as its cooked spans whatever the tag returns
  const tmpl = literals("const a = `the file review's ${x} step 9`;\nconst b = `step ${n}`;\nconst c = `q${'inner step 3'}r`;\nconst d = tag`raw\\n${z}`;\n", "probe.ts");
  assert.deepEqual(tmpl.map((l) => [l.kind, l.text, l.line]), [["template", "the file review's ${x} step 9", 1], ["template", "step ${n}", 2], ["template", "q${'inner step 3'}r", 3], ["string", "inner step 3", 3], ["template", "raw\n${z}", 4]], "the template whole with its holes named, the hole's own literal a unit too, the tagged template cooked");
  // a comment between two operands is blanked with neither token and stands as its own unit
  assert.deepEqual(scriptUnits("const a = 'a' + // between\n 'b';\n", "probe.ts").map((u) => [u.kind, u.text, u.line, u.endLine]), [["string", "ab", 1, 2], ["comment", "between", 1, 1]], "the chain folded around the comment, the comment kept");
  // the starts map is built from SOURCE positions (the file review's round 5, correctness-1 with tests-3: it had counted the
  // newlines of the cooked text, so a one-line literal with escaped newlines was charged to lines past it, past the end of the
  // file in one probe): an escaped newline is a character of the value and no line; a template's real newline, a CRLF and a
  // backslash continuation are source lines, charged where they begin; an escape of any width charges its own line; a raw
  // line separator (U+2028) in a template is a line break to the compiler and gets a start
  const nl = literals("const a = 'x\\nstep 9';\nconst b = `x\nstep 9`;\nconst c = `x\r\nstep 9`;\nconst d = 'x\\\n step 9';\nconst e = '\\u{1F600}\\x41\\101 step 9';\nconst f = `x step 9`;\n", "probe.ts");
  assert.deepEqual(nl.map((l) => [l.text, l.line, l.endLine, lineAt(l, l.text.indexOf("step")), l.starts]), [
    ["x\nstep 9", 1, 1, 1, [{ line: 1, at: 0 }]],
    ["x\nstep 9", 2, 3, 3, [{ line: 2, at: 0 }, { line: 3, at: 2 }]],
    ["x\nstep 9", 4, 5, 5, [{ line: 4, at: 0 }, { line: 5, at: 2 }]],
    ["x step 9", 6, 7, 7, [{ line: 6, at: 0 }, { line: 7, at: 1 }]],
    ["\u{1F600}AA step 9", 8, 8, 8, [{ line: 8, at: 0 }]],
    ["x step 9", 9, 10, 10, [{ line: 9, at: 0 }, { line: 10, at: 2 }]],
  ], "the one-line literal's step is on line 1 and it has one start; the template's, the CRLF's and the continuation's on the line they stand on");
  // an erroneous literal (unterminated, an invalid escape) makes the walk and the compiler disagree, and the read throws
  // naming the file rather than charge lines it cannot vouch for
  assert.throws(() => literals("const a = \"step 9\nconst b = 1;\n", "some/module.ts"), /source-units: some\/module\.ts:1 string literal .* cooks to .* where the compiler read/, "an unterminated literal aborts the read with the file named");
  assert.throws(() => literals("const a = \"\\x4g step 9\";\n", "some/module.ts"), /some\/module\.ts:1 string literal/, "an invalid escape aborts the read with the file named");
  // Python: the literals cooked as Python cooks them (the file review's round 5, extra6-3: every backslash had been dropped,
  // so \n read as the letter n, glued the words the escape separated and could manufacture a phrase the source does not
  // carry); adjacent literals glued with nothing between them, an f-string's field kept as written, a raw literal and a
  // comment as written
  const py = proseUnits("a = 'it\\'s round'\nb = 2\n\nc = 3\n", true);
  assert.deepEqual(py.map((u) => [u.text, u.line, u.endLine]), [["a = 'it's round' b = 2", 1, 2], ["c = 3", 4, 4]], "paragraphs, the escape folded");
  assert.equal(lineAt(py[0], py[0].text.indexOf("b = 2")), 2, "the fold moves the offsets and the starts follow");
  const pyText = (s: string): string => proseUnits(s, true).map((u) => u.text).join(" | ");
  assert.equal(pyText("x = 'the file review\\x27s step 9'\n"), "x = 'the file review's step 9'", "\\x27 is the apostrophe (it had read x27, which broke the phrase: a miss)");
  assert.equal(pyText("x = 'a\\nstep 9'\n"), "x = 'a step 9'", "\\n is a space for matching (it had read the letter n, gluing the words: a miss)");
  assert.equal(pyText("x = 'step \\9 of it'\n"), "x = 'step \\9 of it'", "an unknown escape keeps its backslash as Python keeps it (dropping it had manufactured the digits the source does not carry)");
  assert.equal(pyText("x = ('the file review\\'s ' 'step 9')\n"), "x = ('the file review's step 9')", "adjacent literals are one value");
  assert.equal(pyText("x = ('the file review\\'s '\n     'step 9')\n"), "x = ('the file review's step 9')", "adjacent literals across a wrapped line");
  assert.equal(pyText("x = 'the file review\\'s' \\\n    'step 9'\n"), "x = 'the file review'sstep 9'", "adjacent literals across a continuation glue with nothing between them, as the program glues them: no word step here (it had read a space in, a phrase the source does not carry)");
  assert.equal(pyText("x = 'abc \\\n def'\ny = 'abc\\\ndef'\n"), "x = 'abc def' y = 'abcdef'", "a continuation inside a literal is no character");
  assert.equal(pyText("x = f'the file review\\'s step {n}'\n"), "x = f'the file review's step {n}'", "an f-string's field is kept as written, the hole named");
  assert.equal(pyText("x = r'the file review\\'s step 9'\n"), "x = r'the file review\\'s step 9'", "a raw literal as written");
  assert.equal(pyText("# it's step 4 here\ny = 1  # don't 'quote'\n"), "# it's step 4 here y = 1 # don't 'quote'", "a comment as written: its apostrophes open no literal");
  assert.equal(pyText("x = 'a'\ny = 2\n"), "x = 'a' y = 2", "a literal closing a line and a statement on the next are not glued");
  const doc = proseUnits("def f():\n    \"\"\"The file review's\n    step 9 ruled it.\n\n    Second para 'a' 'b'.\n    \"\"\"\n    return 1\n", true);
  assert.deepEqual(doc.map((u) => [u.text, u.line, u.endLine]), [["def f(): \"\"\"The file review's step 9 ruled it.", 1, 3], ["Second para 'a' 'b'. \"\"\" return 1", 5, 7]], "a docstring's lines join with a space and its blank line ends a paragraph; quotes inside it are its text");
  assert.equal(lineAt(doc[0], doc[0].text.indexOf("step 9")), 3, "charged to the docstring line that carries it");
});

test("the convention: the branch's review has rounds 1 and 2, the file review's rounds are enumerated, the author's passes are never rounds and own an id family; the rule reads a unit's nearest review and refuses a round the convention does not give it, a pass with a round, an id of the pass's family with no pass named, and a round with no review named", () => {
  const r = convention();
  assert.deepEqual([...r.branch], [1, 2]);
  assert.ok(r.file.size >= 4 && r.file.has(1) && r.file.has(r.file.size), "the file review's rounds 1 to " + r.file.size);
  assert.deepEqual(r.ids, ["behaviour", "records", "coverage", "guards", "attribution-and-gates"]);
  const two: Reviews = { branch: new Set([1, 2]), file: new Set([1, 2, 3, 4]), ids: ["behaviour", "records", "coverage"] };
  // a phrase in the section is charged to the plan line that carries it: the section's last paragraph's last word stands at
  // the end of the plan line lineAt names (the starts follow the section's offset; the author's closing pass after the file
  // review's round 4, attribution-and-gates-4, found them section-relative)
  const units = sectionUnits();
  const last = units[units.length - 1];
  const w = last.text.slice(last.text.lastIndexOf(" ") + 1);
  assert.ok(plan.split("\n")[lineAt(last, last.text.length - 1) - 1].trimEnd().endsWith(w), "the section's last word " + JSON.stringify(w) + " is charged to the plan line that ends with it");
  // the probes are assembled, so this module's own literals name no round and no id at rest: an identifier first leaves the
  // chain unfolded, and a probe that would otherwise be all literals routes its digits through a call (n), since the reader
  // folds a chain of literals alone into the value the program computes and this module reads itself on road 1
  const n = (k: number): number => k;
  const F = "the file review's round ", B = "the review's round ", P = "the author's closing pass ";
  assert.deepEqual(roundFaults(F + 2 + " re-decided this on the rule the record of its round " + 1 + " had said did not exist", two), []);
  assert.deepEqual(roundFaults(B + 1 + " found it; " + F + 3 + " (tests-2) pinned it", two), []);
  assert.deepEqual(roundFaults(P + "after " + F + 3 + " (records-" + 3 + ") said so", two), []);
  assert.deepEqual(roundFaults("measured in the Slice 7 review's round " + n(9), two), [], "another review's rounds are not this section's");
  assert.equal(roundFaults(F + 5 + " found it", two).length, 1, "a file-review round past the enumeration");
  assert.equal(roundFaults("the file review\\'s round " + n(9) + " found it", two).length, 1, "the escaped apostrophe is the same phrase");
  assert.equal(roundFaults(B + 3 + " found it", two).length, 1, "a branch-review round it never had");
  assert.equal(roundFaults(P + "(round " + 4 + ", behaviour-" + 2 + ") found it", two).length, 1, "a pass named as a round (the id after the pass is fine)");
  assert.equal(roundFaults("the verifier's round-" + n(6) + " probe", two).length, 1, "a verifier's pass named as a round");
  assert.equal(roundFaults("since round " + n(2) + " a failed figure opens nothing", two).length, 1, "a round with no review named");
  assert.equal(roundFaults("(" + F + 4 + ", records-" + 3 + ")", two).length, 1, "the pass's finding credited to a round of the file review: the id has no pass before it");
  // the review named NEAREST before the id decides, not any pass named earlier in the unit (the file review's round 5,
  // correctness-3 with regression-1: the shape below passed with 0 faults, the round-4 HIGH's misattribution beside a pass)
  const credited = roundFaults(P + "after " + F + 3 + " measured it; " + F + 4 + " (records-" + 2 + ") ruled it", two);
  assert.ok(credited.length === 1 && /nearest before it is the file review/.test(credited[0].fault) && credited[0].at === (P + "after " + F + 3 + " measured it; " + F + 4 + " (").length, "a pass named, then the pass's finding credited to a round of the file review: one fault, the id's, at the id");
  assert.equal(roundFaults(P + "(records-" + 1 + ") found it; " + F + 4 + " (records-" + 2 + ") ruled it", two).length, 1, "the id after the pass stands; the id after the file review's round, later in the same unit, faults");
  assert.deepEqual(roundFaults(F + 3 + " found it; " + P + "after " + F + 3 + " (records-" + 3 + ") fixed it", two), [], "a file-review round, then the pass named by the round it followed with its id: the pass is the review named nearest before the id, its own name through the digits");
  assert.deepEqual(roundFaults(P + "after the review's round " + 2 + " (behaviour-" + 1 + ") measured it", two), [], "the pass named by the branch review's round it followed: the round is the branch's, the id the pass's");
  assert.equal(roundFaults(P + "after " + F + 7 + " (records-" + 1 + ") measured it", two).length, 1, "the round inside the pass's name is judged against the file review's enumeration");
  assert.equal(roundFaults("recorded by " + F + 4 + " (rules-" + 1 + ")", two).length, 0, "the maintainer's own ids are not the family's");
  assert.deepEqual(roundFaults("the review ran two rounds; the pin holds a round-trip", two), [], "no round number, no claim");
  // the digits after any whitespace (a literal's escaped newline, now a character of its value) or Markdown markers (the file
  // review's round 5, extra6-2: one space or hyphen alone was read)
  assert.equal(roundFaults(F.trimEnd() + "\n" + n(9) + " found it", two).length, 1, "a line break between the word and its digits");
  assert.equal(roundFaults(F + "**" + n(9) + "** found it", two).length, 1, "the digits in Markdown emphasis");
  assert.equal(roundFaults(F + "`" + n(9) + "` found it", two).length, 1, "the digits in Markdown code markers");
  assert.equal(roundFaults(F + "_" + n(9) + "_ found it", two).length, 1, "the digits in Markdown underscores");
  assert.deepEqual(roundFaults(F + "**" + n(4) + "** and " + B + "`" + n(2) + "` found it", two), [], "marked-up digits of rounds the reviews had");
  // a fault is charged to the source line of the phrase, so a line filter (road 2's added lines) keeps it (the file review's
  // round 5, extra7-1: with the starts map counting the cooked text's newlines, a one-line literal's fault was charged past
  // the literal and the filter dropped it, a real violation on an added line passing as a green)
  const kept = faultsOf("probe", unitsOf("probe.ts", "const a = \"a\\nb\\nc\\nthe review's round " + n(9) + "\";\nconst b = 1;\n"), two, (l) => l === 1);
  assert.ok(kept.length === 1 && /^probe:1 /.test(kept[0]), "the escaped-newline literal's fault is charged to line 1 and survives a filter keeping line 1: " + JSON.stringify(kept));
  // the plural and the range (the author's closing pass after the file review's round 4, guards-2: the plural form passed the
  // singular reader), and the forms the reader leaves outside, held there so the message's own words stay true
  const FS = "the file review's rounds ", BS = "the review's rounds ";
  assert.equal(roundFaults(FS + 5 + " and " + 6 + " found it", two).length, 1, "the plural naming rounds past the enumeration: one fault for the phrase");
  assert.deepEqual(roundFaults(FS + 1 + " to " + 4 + " ruled it; " + BS + 1 + " and " + 2 + " found it", two), [], "a range and a list of rounds the reviews had");
  assert.equal(roundFaults(FS + 3 + " to " + 5 + " found it", two).length, 1, "a to-range is expanded, and the round past the enumeration reds");
  assert.equal(roundFaults(P + "(rounds " + 5 + " and " + 6 + ", records-" + 2 + ")", two).length, 1, "a pass with rounds in the plural");
  assert.deepEqual(roundFaults("the file review's fourth round found it, in its round four (R4)", two), [], "an ordinal, a spelled-out number and an abbreviation are outside the reader, which the message says");
  assert.deepEqual(roundFaults("(" + F + 4 + ", behaviour " + 3 + ")", two), [], "a spaced id is outside the reader, which the message says");
  // road 1's selection of file-view.ts units (the author's closing pass after the file review's round 4, records-1): a unit
  // carrying an id of the family is read even
  // where it names no review, and a pass named as a round there reds; a unit naming only the review is road 2's
  const misnamed = "decided in the author's closing pass (round " + n(5) + ", behaviour-" + n(2) + ") over the measured box";
  assert.ok(roadOneViewerUnit(misnamed, two) && roundFaults(misnamed, two).length === 1, "a pass named as a round beside its id, in a unit naming no review, is selected and reds");
  const pronoun = "its round " + n(4) + " (behaviour-" + n(2) + ", records-" + n(1) + ") measured this";
  const pf = roundFaults(pronoun, two);
  assert.ok(roadOneViewerUnit(pronoun, two) && pf.length === 3 && /of no review/.test(pf[0].fault), "the pronoun form: a round of no review and two ids with no pass");
  assert.ok(!roadOneViewerUnit("the review's round " + n(3) + " found it", two), "a unit naming only the review is not selected by the vocabulary (inside a created file it is judged with the file, in full)");
  // the keyed rule (the file review's round 5, regression-2): outside this follow-on's own files a phrase is judged only where
  // the review named nearest before it is the file review or the author's pass; another review's phrase, or one naming no
  // review, is counted and left alone, so a later review's round in the shared file-view.ts, or a record another PR brought
  // in, cannot red this module; the same texts under the full rule show what the key withholds
  const other = "the fork PR review's round " + n(9) + " (its records-" + n(7) + ") found it";
  assert.deepEqual(judgeUnit(other, two, true), { faults: [], judged: 0, foreign: 2, unanchored: 0 }, "another review's round and its finding, named by that review: left alone and counted");
  assert.equal(roundFaults(other, two).length, 2, "the same text under the full rule: the branch's review had no ninth round, and the id has no pass");
  assert.equal(roundFaults(F + n(9) + " found it", two, true).length, 1, "the file review's round past the enumeration is ours wherever it stands");
  assert.equal(roundFaults(misnamed, two, true).length, 1, "the pass named as a round beside its id is ours wherever it stands (the pass is the review named nearest before the round)");
  assert.deepEqual(judgeUnit("measured in the Slice 7 review's round " + n(9), two, true), { faults: [], judged: 0, foreign: 1, unanchored: 0 });
  assert.deepEqual(judgeUnit("since round " + n(2) + " a failed figure opens nothing", two, true), { faults: [], judged: 0, foreign: 0, unanchored: 1 }, "a round naming no review is no one's outside our files (the full rule faults it)");
  assert.deepEqual(judgeUnit("the caller's own pass ran first; the round-" + n(1) + " ruling of the fork PR's review kept its finding records-" + n(3), two, true), { faults: [], judged: 0, foreign: 1, unanchored: 1 }, "a caller's own pass is code and no anchor; the round before the review is named by nothing, the id after it is that review's");
  assert.equal(roundFaults(P + "after " + F + 3 + " measured it; " + F + 4 + " (records-" + 2 + ") ruled it", two, true).length, 1, "the fourth round's HIGH, the misattribution beside a pass, is ours under the key too: the file review is the review named nearest before the id");
  assert.deepEqual(judgeUnit(F + 3 + " ruled it; the fork PR review's round " + n(9) + " (records-" + n(7) + ") did too", two, true), { faults: [], judged: 1, foreign: 2, unanchored: 0 }, "one unit, two reviews: the file review's round is judged, the other review's round and id are left alone");
});

/** The count of this follow-on's units in the shared ui/webview/file-view.ts at the swept head: the units selected by the
 *  vocabulary that name the file review or carry a phrase the keyed rule judges as ours. Derived, never fitted: a deleted or an added
 *  attribution comment there moves it, and the fix is to re-derive this number at the new head (the file review's round 5,
 *  correctness-6 with tests-5 and extra8-4: a floor of ten had stood against fourteen, so four could go with the guard green). */
const VIEWER_UNITS = 14;

test("road 1, every checkout, a rule over the tree: every file git lists at the repo root, tracked or untracked and not ignored, whose text names the file review or carries an id of the author's family, plus the files the branch created, the plan's section, the guide's Links paragraph and the browser plan's pointer; the created files and the three records in full, the rest keyed on the review named, so another review's rounds are left alone; no round outside the convention and no finding of the author's outside a pass; road 2, on the open PR branch where main has moved past its last merge (the merge-base off origin/main and the diff adding this module): every unit the branch added or touched, the working tree against the merge-base", (t) => {
  const reviews = convention();
  const vocabulary = (text: string): boolean => roadOneViewerUnit(text, reviews);
  const pop = populationOf(REPO);
  assert.ok(pop.files.length >= 1000, "the population is the tree: " + pop.files.length + " files (a derivation that reads nothing is red)");
  for (const f of CREATED) assert.ok(pop.files.includes(f), f + " is in the population (a created file of the branch; a rename moves it here too)");
  // this follow-on's records by their place, judged in full and numbered in their files' lines; their spans are left out of
  // the keyed walk over the same files so no phrase is judged twice
  const full = new Map<string, { label: string; units: Unit[]; span: [number, number] }>();
  const sec = sectionUnits();
  full.set("plans/markdown-viewer.md", { label: "plans/markdown-viewer.md (the follow-on section)", units: sec, span: [sectionLine, sec[sec.length - 1].endLine] });
  const links = paragraphAt(read("docs/guide.md"), "**Links in a file.**", "the guide's Links in a file paragraph");
  full.set("docs/guide.md", { label: "docs/guide.md (Links in a file)", units: links.units, span: links.span });
  const pointer = paragraphAt(read("plans/file-browser.md"), "Since 2026-09-19 the viewer keeps a trail of its own", "the browser plan's pointer paragraph");
  full.set("plans/file-browser.md", { label: "plans/file-browser.md (the pointer)", units: pointer.units, span: pointer.span });
  const faults: string[] = [];
  const tally = { units: 0, judged: 0, foreign: 0, unanchored: 0 };
  const add = (x: Tally): void => { faults.push(...x.faults); tally.units += x.units; tally.judged += x.judged; tally.foreign += x.foreign; tally.unanchored += x.unanchored; };
  for (const r of full.values()) add(judgeUnits(r.label, r.units, reviews));
  const candidates: string[] = [];
  const another: string[] = [];   // files with a phrase left alone as another review's or no review's
  let binary = 0;
  let viewerOwn: number[] = [];
  for (const f of pop.files) {
    const buf = fs.readFileSync(path.join(REPO, f));
    if (isBinary(buf)) { binary++; continue; }
    const text = buf.toString("utf8");
    const whole = CREATED.includes(f);
    if (!whole && !vocabulary(text)) continue;
    candidates.push(f);
    const place = full.get(f);
    const units = unitsOf(f, text).filter((u) => !(place && u.line >= place.span[0] && u.endLine <= place.span[1]) && (whole || vocabulary(u.text)));
    const x = judgeUnits(f, units, reviews, !whole);
    add(x);
    if (x.foreign + x.unanchored > 0) another.push(f + " (" + x.foreign + " another review's, " + x.unanchored + " naming none)");
    if (f === "ui/webview/file-view.ts") viewerOwn = units.filter((u) => /\bfile review\b/.test(u.text) || judgeUnit(u.text, reviews, true).judged > 0).map((u) => u.line);
  }
  assert.ok(candidates.length >= 10, "the candidates, the files naming the file review or carrying an id of the family, and the created files: " + candidates.length);
  assert.ok(tally.units >= 200, "the units judged: " + tally.units);
  assert.deepEqual(faults, [], "every round a record names is a round the convention gives the review it names, and every finding of the author's family follows a pass (TS and JS read by the compiler, comments joined and each string the program sees as one value one unit, a + chain of literals and a template's spans folded, a join, a concat and a hole's run-time value outside the read; Markdown as paragraphs; Python as paragraphs with its literals cooked as Python cooks them; a round is read as the word round or rounds, a hyphen or whitespace and digits, bare or in Markdown emphasis or code markers, with a comma list or a to-range after rounds as the set, and not as an ordinal, a spelled-out number or an abbreviation; an id as the family word, a hyphen and digits, never spaced; outside the created files and the three records a phrase is judged only where the review named nearest before it is the file review or the author's pass)");
  assert.equal(viewerOwn.length, VIEWER_UNITS, "ui/webview/file-view.ts carries " + VIEWER_UNITS + " units of this follow-on's (naming the file review, or the author's pass before a round or an id); derived: " + viewerOwn.length + " at lines " + viewerOwn.join(", ") + ". A deleted or an added attribution there moves this count; re-derive VIEWER_UNITS at the new head, never fit the records to it");
  t.diagnostic("road 1 ran over the tree: " + pop.files.length + " files in the population (" + pop.skipped.length + " paths skipped as no regular file, " + binary + " binary), " + candidates.length + " candidates, " + tally.units + " units judged, " + tally.judged + " phrases ours, " + tally.foreign + " another review's and " + tally.unanchored + " naming no review left alone" + (another.length ? " in " + another.join("; ") : "") + ". Candidates (compare with the PR's added files): " + candidates.join(", "));
  // road 2 (kept and disclosed: it runs in no CI job and in none after the merge; the plan's Tests paragraph says why)
  const git = (...args: string[]): string => execFileSync("git", args, { cwd: REPO, encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] }).trim();
  let base: string | null = null;
  let main: string | null = null;
  try { base = git("merge-base", "origin/main", "HEAD"); main = git("rev-parse", "origin/main"); } catch { base = null; }
  if (!base) { t.diagnostic("road 2 did not run: origin/main is not known in this checkout (CI's default-depth checkout: road 2 runs in no CI job and in none after the merge, the plan's Tests paragraph); road 1 ran over the tree"); return; }
  if (base === main) {
    t.diagnostic("road 2 did not run: the merge-base with origin/main is origin/main itself (main itself, a branch or a batch head cut from main's tip, or this branch just after merging origin/main), so the diff since it is the whole history over main's tip and not this follow-on's delta; road 2 runs on the open PR branch once main has moved past the branch's last merge of it, and in no CI job and in none after the merge (the plan's Tests paragraph). Road 1 ran over the tree.");
    return;
  }
  // the working tree against the merge-base (no HEAD argument): the ranges and the units read come from the same bytes; the
  // diff lists tracked paths alone, so a new uncommitted file is road 1's
  const status = git("diff", "--name-status", base).split("\n").filter(Boolean).map((l) => l.split("\t"));
  const created = status.filter((s) => s[0] === "A").map((s) => s[1]).sort();
  if (!created.includes(THIS_MODULE)) {
    t.diagnostic("road 2 did not run: the diff since the merge-base " + base + " does not add " + THIS_MODULE + " (a later branch after this follow-on landed, whose fork point main has moved past; or HEAD is main), so the diff is that branch's delta and not this follow-on's; road 2 runs on the open PR branch once main has moved past the branch's last merge of it, and in no CI job and in none after the merge (the plan's Tests paragraph). Road 1 ran over the tree.");
    return;
  }
  const notInRoster = created.filter((f) => !CREATED.includes(f));
  const notAdded = CREATED.filter((f) => !created.includes(f));
  const touched = status.filter((s) => s[0] !== "A" && s[0] !== "D").map((s) => s[s.length - 1]);
  const faults2: string[] = [];
  for (const f of touched) {
    const ranges: [number, number][] = [];
    for (const m of git("diff", "-U0", base, "--", f).matchAll(/^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@/gm)) {
      const n = m[2] === undefined ? 1 : Number(m[2]);
      if (n > 0) ranges.push([Number(m[1]), Number(m[1]) + n - 1]);
    }
    if (!ranges.length) continue;
    const units = unitsOf(f, read(f)).filter((u) => ranges.some(([a, b]) => u.line <= b && u.endLine >= a));
    faults2.push(...faultsOf(f, units, reviews, (line) => ranges.some(([a, b]) => line >= a && line <= b)));
  }
  assert.ok(touched.length > 0, "the branch touched files since " + base);
  assert.deepEqual(faults2, [], "every round and every id on a line the branch added since " + base + " (the working tree against the merge-base, so an uncommitted edit is charged like a committed one) is judged in its unit and passes (road 2; a round is read as the word round or rounds followed by digits, a comma list or a to-range after rounds as the set, never an ordinal, a spelled-out number or an abbreviation; an id as the family word, a hyphen and digits)");
  t.diagnostic("road 2 ran: " + touched.length + " touched files read since " + base + ", the working tree's added lines (committed or not) judged in their units; the diff adds " + created.length + " files" + (notInRoster.length ? ", not in CREATED: " + notInRoster.join(", ") : "") + (notAdded.length ? "; in CREATED and not added by the diff: " + notAdded.join(", ") : "") + " (for a human to compare; nothing here gates landing)");
});

test("the population helper (road 1): a temp repo with a tracked file, an untracked file, an ignored file, a symlink to a file, a dangling symlink and a symlink to a directory lists the tracked, the untracked and the file symlink, and skips the two other symlinks", () => {
  const repo = fs.mkdtempSync(path.join(os.tmpdir(), "linknav-pop-"));
  try {
    const git = (...args: string[]): void => { execFileSync("git", ["-C", repo, "-c", "user.email=t@example.test", "-c", "user.name=t", ...args], { stdio: "ignore" }); };
    git("init", "-q", ".");
    fs.mkdirSync(path.join(repo, "sub"));
    fs.writeFileSync(path.join(repo, "tracked.md"), "a\n");
    fs.writeFileSync(path.join(repo, "sub", "untracked.ts"), "b\n");
    fs.writeFileSync(path.join(repo, ".gitignore"), "ignored.md\n");
    fs.writeFileSync(path.join(repo, "ignored.md"), "c\n");
    fs.symlinkSync("tracked.md", path.join(repo, "link-to-file.md"));
    fs.symlinkSync("nowhere.md", path.join(repo, "dangling.md"));
    fs.symlinkSync("sub", path.join(repo, "link-to-dir"));
    git("add", "tracked.md");
    git("commit", "-q", "-m", "x");
    const pop = populationOf(repo);
    assert.deepEqual(pop.files, [".gitignore", "link-to-file.md", "sub/untracked.ts", "tracked.md"], "the tracked file, the untracked ones (the .gitignore itself among them) and the symlink to a file; the ignored file is not listed");
    assert.deepEqual(pop.skipped, ["dangling.md", "link-to-dir"], "the dangling symlink and the symlink to a directory are skipped, not read");
  } finally {
    fs.rmSync(repo, { recursive: true, force: true });
  }
});

// The browser-legs census, held to the tree and to the planted forms. The gating vscode-extension job runs the legs named in
// vscode-extension/ci-browser-legs.txt after its Chromium install (the step "Browser legs (node --test over
// ci-browser-legs.txt)", scripts/ci-browser-legs.sh); every other browser leg of the extension's test build is in
// ci-browser-legs-excluded.txt with a reason, and the census's directory list is held equal to that build here, by execution.
// The census that decides what a browser leg IS lives in vscode-extension/scripts/browser-legs-census.mjs, which reads each
// test module's tree with the TypeScript compiler (its header states the rule), and the compiler is installed only under
// vscode-extension/node_modules, so this test, in the extension's own suite (npm test, this job), is where the completeness
// property is executed: the roster PLUS the exclusions whose source is present EQUALS the census's legs, no refusal, every roster
// line passes the roster gate and reaches Chromium alone, an exclusions reason names Firefox or WebKit when and only when the
// source reaches it, and carries the embedded-driver sentence when and only when the leg is one. An exclusions reason "pending
// #<PR>: <why>" names a leg an open PR brings and stands while its source is absent; once the source is present the line is red
// here with the promotion remedy derived from the census's record of that source (a roster line for a shared Chromium leg that
// passes the gate, the engine form or the embedded-driver sentence for a leg the gating job cannot run, the gate's own remedy
// for a Chromium-only leg that misses it, no line for a module that is no leg; a leg in neither file is red with the same
// derived remedy). The grandfather reason is bound, in one header line,
// to the roster's creation commit: this test reads the commit from the header, fetches it at depth 1 when the checkout lacks it
// (a fetch that fails is a red hold-off, never a pass) and refuses a row carrying the sentence whose source is not in the tree at
// that commit. tools/ci-browser-legs.test.mjs, in CI's Shell job with
// no node_modules, holds the parse-free half (file shape, duplicates, both files, reasons, the ci.yml pins) and runs the script
// over synthetic trees with a stub node that answers the census call from a table; the script's reading of the REAL census is
// executed here, over the tree and over a synthetic root. The planted forms under tests/fixtures/browser-legs-plants are the
// spellings the round-1 review of the convention found escaping a textual census (an aliased import of the launcher, a
// single-quoted require, a launch spelled launchPersistentContext, destructured or bracketed, a shared call inside try/catch, a
// .skip( held in a comment, Firefox reached by a named or destructured import, a block-comment mention) and the forms the parse
// refuses: each is classified or refused as recorded here, none is silent. Of the 51 round-3 rows (p38 to p88), 45 red under the
// census before round 3 (the round-2 base; 44 at round 3, and p74 since round 5, whose safety net refuses a text that census passed),
// 6 hold something else and say what in the table's holds field (a stated residual
// boundary, the no-refusal half of a pair whose partner reds, a guard of round 3's own scoping), and 3 of the 45 red on a property
// other than their section's and name the plant that carries it (carried); the plant-table test holds the table to that statement,
// a count of this file's rows and not a figure from the run. Of the 67 round-4 rows (p89 to p155: the forms the round-3 review's
// class ruling named, a load, an engine or a launch the walker could not fold and classed none instead of refusing, the round-3
// lows, a type-only import read as a load, a called launcher binding misnamed, a destructuring of an untracked load that stopped the
// census, a rebound name folded to its initializer, and the two residuals the round's own verifiers found, a launcher binding as the
// left operand of a logical or other binary expression exempted as an assignment's target, and a var redeclared by a for-of or
// for-in head folded to its first initializer), 62 are red under the census before round 4 (the module at the round-3 head)
// and 5 say in their holds field what else they hold, and the same test holds the table to that statement. Of the round-5 rows (p156
// onward: the eleven silent forms the round-4 review named and the tagged-template loader its verifiers found, each planted with THE
// SAFETY NET's refusal as its outcome until a fold reads the form, the fold's sentence or class once one does, with one net-only row
// per kind of mention the net names so every arm of the net keeps a plant, and the controls and pin rows the folds bring; then the
// string-typed parameter passed back to its own function, under which the census before round 5 died whole with a bare RangeError, so
// those rows red as census(PLANTS) throwing rather than as a row mismatch, beside its non-cyclic control), every one
// is red under the census before round 5 (the module at
// the round-4 head) unless the table names it held with its reason, and the same test holds the table to that statement. A module
// whose classification throws for any other reason is refused by name and the census goes on, executed over a synthetic root by a
// test of its own (a directory named like a test module, a nesting generated to overflow whatever stack is in effect). Population figures are derived from the run and printed as
// diagnostics, never asserted as constants. Synthetic: the fixtures' invented modules and a stub launcher.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import { spawnSync } from "node:child_process";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";

const EXT = process.cwd();                                                  // npm test runs in vscode-extension
const REPO = path.resolve(EXT, "..");
const MODULE = path.join(EXT, "scripts", "browser-legs-census.mjs");
const SCRIPT = path.join(EXT, "scripts", "ci-browser-legs.sh");
const ROSTER = "ci-browser-legs.txt";
const EXCLUDED = "ci-browser-legs-excluded.txt";
const PLANTS = path.join(REPO, "tests", "fixtures", "browser-legs-plants");
const STUB_LAUNCHER = path.join(PLANTS, "ui", "webview", "real-viewer-leg.ts");

type Launch = { line: number; how: string };
type Rec = {
  rel: string; refusals: string[]; launcherImported?: boolean; sharedCalls?: number; embedded?: { line: number; what: string }[];
  playwright?: string[]; engines?: string[]; launches?: Launch[]; skipTodo?: { line: number; what: string }[]; swallow?: number[]; reaches?: boolean;
};
type Census = {
  census(root?: string, opts?: { strictComputed?: boolean }): { legs: string[]; byBundle: Map<string, Rec>; refusals: string[]; localModules: number };
  rosterGap(r: Rec): string | null;
  engineNames(r: Rec): string[];
  classOf(r: Rec): string;
  resolveLocal(fromFile: string, spec: string, root: string): { abs: string } | { ambiguous: string[] } | null;
  EMBEDDED_PHRASE: string;
  ENGINE_PHRASE: string;
  LEG_DIRS: string[];
};
const load = (): Promise<Census> => import(pathToFileURL(MODULE).href) as Promise<Census>;
const read = (p: string): string => fs.readFileSync(p, "utf8");
const sourceOf = (bundle: string): string => path.join(REPO, bundle.replace(/^out-tests\//, "").replace(/\.test\.js$/, ".test.ts"));
/** Roster lines: [{ n, bundle }], comments and blanks dropped. */
const parseRoster = (text: string) => text.split("\n").map((line, i) => ({ n: i + 1, line })).filter(({ line }) => !/^\s*(#|$)/.test(line)).map(({ n, line }) => ({ n, bundle: line }));
/** Exclusions lines: [{ n, bundle, reason, pending }] (reason null when the line has no tab; `pending` is undefined for an
 *  ordinary reason, { pr } for a reason of the class "pending #<PR>: <why>", with pr null when it names no PR). */
type Excluded = { n: number; bundle: string; reason: string | null; pending?: { pr: string | null } };
const parseExcluded = (text: string): Excluded[] => text.split("\n").map((line, i) => ({ n: i + 1, line })).filter(({ line }) => !/^\s*(#|$)/.test(line)).map(({ n, line }) => {
  const tab = line.indexOf("\t");
  const e: Excluded = tab < 0 ? { n, bundle: line, reason: null } : { n, bundle: line.slice(0, tab), reason: line.slice(tab + 1) };
  if (e.reason !== null && /^\s*pending/.test(e.reason)) { const m = /^\s*pending #(\d+): \S/.exec(e.reason); e.pending = { pr: m ? m[1] : null }; }
  return e;
});
const where = (file: string, e: { n: number; bundle: string }) => file + " line " + e.n + " (" + e.bundle + ")";
/** The exclusions header's two quoted sentences, read from the file the rows live in: the grandfather sentence with the commit
 *  it is bound to (the one bound line), and the embedded-driver sentence (quoted after "carries the sentence"; the census
 *  module exports the same as EMBEDDED_PHRASE, and the first test holds the two equal rather than trusting either). */
const headerOf = (text: string) => {
  const lines = text.split("\n").filter((l) => l.startsWith("#"));
  const hits = lines.map((l) => /^# Every grandfather reason, "([^"]+)", is bound to commit ([0-9a-f]{40}):/.exec(l)).filter((m): m is RegExpExecArray => m !== null);
  assert.equal(hits.length, 1, EXCLUDED + "'s header holds exactly one line binding the grandfather reason to a commit (the bound's one home); found " + hits.length);
  const joined = lines.map((l) => l.replace(/^# ?/, "")).join(" ");
  const em = /carries the sentence "([^"]+)"/.exec(joined);
  assert.ok(em, EXCLUDED + "'s header quotes the embedded-driver sentence after 'carries the sentence'");
  return { sentence: hits[0][1], sha: hits[0][2], embedded: (em as RegExpExecArray)[1] };
};
/** An exclusions reason is exactly one of four closed forms, or refused by name: grandfather (the header's bound sentence, whole
 *  and exact); engine ("launches <Firefox|WebKit|Firefox and WebKit>; " then ENGINE_PHRASE, a tail after the phrase allowed,
 *  since two rows carry a locator there); embedded (the embedded-driver sentence, whole and exact); pending ("pending #<PR>:
 *  <why>"). A reason matching none is refused (there is no reason of its own, so a misspelt exemption cannot pass as one), and
 *  one that reads as a form while its text carries another form's phrase, or an engine reason whose tail names a second
 *  engine, is refused as AMBIGUOUS, so a tail cannot carry a second claim. The age claim behind the grandfather form is settled
 *  by git, in the bound test below; this reads the form.
 *  tools/ci-browser-legs.test.mjs holds the same rule for CI's Shell job. */
type Kind = "grandfather" | "engine" | "embedded" | "pending";
type Verdict = { kind: Kind; engines: string[] } | { kind: null; refusal: string };
const ENGINE_FORM = /^launches (Firefox|WebKit|Firefox and WebKit); /;
function reasonKind(reason: string, sentence: string, enginePhrase: string, embeddedSentence: string): Verdict {
  const head = ENGINE_FORM.exec(reason);
  const forms: [Kind, boolean][] = [["grandfather", reason === sentence], ["engine", head !== null && reason.slice(head[0].length).startsWith(enginePhrase)], ["embedded", reason === embeddedSentence], ["pending", /^pending #\d+: \S/.test(reason)]];
  const phrases: [Kind, boolean][] = [["grandfather", reason.includes(sentence)], ["engine", reason.includes(enginePhrase) || /\blaunches (Firefox|WebKit)\b/.test(reason)], ["embedded", reason.includes(embeddedSentence)], ["pending", /\bpending #\d+: /.test(reason)]];
  const matched = forms.filter(([, ok]) => ok).map(([k]) => k);
  const carried = phrases.filter(([, ok]) => ok).map(([k]) => k !== matched[0] ? k : null).filter((k): k is Kind => k !== null);
  const FORMS = "the four forms the header of " + EXCLUDED + " defines (the grandfather sentence as quoted there, whole and exact; 'launches <Firefox|WebKit|Firefox and WebKit>; " + enginePhrase + "', a tail after the phrase allowed; the embedded-driver sentence, whole and exact; 'pending #<PR>: <why>')";
  if (matched.length === 0) return { kind: null, refusal: "the reason is none of " + FORMS + "; a reason of its own is not admitted, so a misspelt exemption cannot pass as one" };
  if (matched.length > 1 || carried.length) return { kind: null, refusal: "the reason is AMBIGUOUS: it reads as the " + matched.join(" and the ") + " form and its text also carries the " + [...matched.slice(1), ...carried].join(" and the ") + " form's phrase; a reason is exactly one of " + FORMS };
  if (matched[0] === "engine") {
    // the engines a reason claims have one home, the form's head (reasonVerdict reads them there): a tail naming another engine is a second claim
    const second = /\b(Firefox|WebKit)\b/.exec(reason.slice((head as RegExpExecArray)[0].length + enginePhrase.length));
    if (second) return { kind: null, refusal: "the reason is AMBIGUOUS: it reads as the engine form and its tail, after the phrase, names an engine (" + second[1] + "); the engines a reason claims have one home, the form's head, so a tail cannot carry a second engine; a reason is exactly one of " + FORMS };
  }
  return { kind: matched[0], engines: matched[0] === "engine" ? (head as RegExpExecArray)[1].split(" and ") : [] };
}
/** The verdict on one exclusions row that is not pending, against the census's record of its source (`r` is undefined when the
 *  source is not in the tree) and the reason's form: null, or the sentence the red carries. The exclusions rows' reason verdicts
 *  are the half no script harness reaches (the script reads a reason only for the pending class), so this function is driven
 *  over a synthetic table in its own test and called from the loop over the real file, one writer for both. */
function reasonVerdict(e: Excluded, r: Rec | undefined, v: Verdict, mod: Census, embeddedSentence: string): string | null {
  const at = where(EXCLUDED, e);
  if (e.reason === null) return at + " has no tab, so it has no reason to read here (refused by name above and by tools/ci-browser-legs.test.mjs)";
  if (r === undefined) return at + " names " + path.relative(REPO, sourceOf(e.bundle)) + ", which is not in the tree (the source moved or was deleted): fix the line";
  if (!r.reaches) return at + " names no browser leg" + (r.launcherImported ? ": " + mod.rosterGap(r) : " (the source reaches no browser by the census rule): remove the line");
  if (v.kind === null) return at + ": " + v.refusal + "; the reason reads: " + e.reason;
  const engines = mod.engineNames(r);
  for (const eng of ["Firefox", "WebKit"]) {
    const inReason = v.kind === "engine" && v.engines.includes(eng), inSource = engines.includes(eng);
    if (inReason !== inSource) return at + ": the reason " + (inReason ? "names " : "does not name ") + eng + " and the source " + (inSource ? "reaches it" : "does not reach it") + " (engines from playwright-derived expressions and from the engine passed to the shared launcher; comments and strings excluded); " + (inReason ? "drop the engine from the reason, or, if the source reaches it in a form the census does not read, write the read so the census sees it" : "write \"launches " + eng + "; " + mod.ENGINE_PHRASE + "\" in the reason") + "; the reason reads: " + e.reason;
  }
  const isEmbedded = mod.classOf(r) === "embedded";
  if ((v.kind === "embedded") !== isEmbedded) return at + ": the reason " + (v.kind === "embedded" ? "carries" : "does not carry") + " the embedded-driver sentence and the leg " + (isEmbedded ? "is one (its only playwright is in a driver string it runs as a child process)" : "is not one (class " + mod.classOf(r) + ")") + "; the sentence is " + JSON.stringify(embeddedSentence) + "; the reason reads: " + e.reason;
  return null;
}
/** The class of remedy the census's record of a source derives, one rule for the pending line's promotion (promotionOf) and
 *  for a leg in neither file (neitherRemedy); the script's remedy_kind states the same rule over its --tsv row. Every remedy
 *  names a row one of the exclusions' four forms admits, or the roster: none (no leg), embedded (the embedded-driver sentence),
 *  engine (the engine form; the engine alone is why the gating job cannot run it), roster (passes the gate and reaches Chromium
 *  alone), gate (reaches Chromium alone and misses the gate: no form admits such a leg, so it passes the gate and is rostered). */
type Remedy = "none" | "embedded" | "engine" | "roster" | "gate";
function remedyKind(c: Census, r: Rec | undefined): Remedy {
  if (!r || !r.reaches) return "none";
  if (c.classOf(r) === "embedded") return "embedded";
  if (c.engineNames(r).length) return "engine";
  return c.rosterGap(r) === null ? "roster" : "gate";
}
const engineForm = (c: Census, r: Rec): string => "launches " + c.engineNames(r).join(" and ") + "; " + c.ENGINE_PHRASE;
const gateRemedy = (c: Census, r: Rec): string => "pass the roster gate (the source " + c.rosterGap(r) + ": launch through inBrowser alone, with no playwright, launch, skip or todo of the leg's own)";
const NO_OWN_REASON = "the exclusions admit no reason of its own, so a leg that reaches Chromium alone is rostered once it passes the gate";
/** The remedy for a browser leg in neither file, derived from the census's record (the ruling's benign mode: an undeclared leg
 *  takes the pending-row remedy, never a bare add-or-exclude). */
function neitherRemedy(c: Census, r: Rec | undefined, bundle: string): string {
  switch (remedyKind(c, r)) {
    case "roster": return "add '" + bundle + "' to " + ROSTER + " (the source launches through inBrowser alone and reaches no engine but Chromium), with the step's measured seconds in the PR body";
    case "engine": return "add it to " + EXCLUDED + " with a tab and the engine form its header admits, \"" + engineForm(c, r as Rec) + "\"";
    case "embedded": return "add it to " + EXCLUDED + " with a tab and the embedded-driver sentence its header states (the leg's only playwright is in a driver string it runs as a child process, which the switch never reaches)";
    case "gate": return gateRemedy(c, r as Rec) + " and add '" + bundle + "' to " + ROSTER + " with the step's measured seconds in the PR body: " + NO_OWN_REASON;
    default: return "not a browser leg by the census rule (the census pass lists legs only)";
  }
}
/** The promotion remedy for a pending line whose source has arrived, derived from the census's record of the source (the
 *  script's promotion_of states the same rule over the same record). */
function promotionOf(c: Census, r: Rec | undefined, bundle: string): string {
  switch (remedyKind(c, r)) {
    case "roster": return "delete this line and add '" + bundle + "' to " + ROSTER + " (the source launches through inBrowser alone and reaches no engine but Chromium), with the step's measured seconds in the PR body";
    case "engine": return "keep the line and replace the reason with the engine form the header of " + EXCLUDED + " admits, \"" + engineForm(c, r as Rec) + "\"";
    case "embedded": return "keep the line and replace the reason with the embedded-driver sentence the header of " + EXCLUDED + " states (the leg's only playwright is in a driver string it runs as a child process, which the switch never reaches)";
    case "gate": return gateRemedy(c, r as Rec) + ", then delete this line and add '" + bundle + "' to " + ROSTER + " with the step's measured seconds in the PR body: " + NO_OWN_REASON;
    default: return "remove the line (the source reaches no browser by the census rule" + (r && r.launcherImported ? "; " + c.rosterGap(r) : "") + ")";
  }
}

test("the roster plus the exclusions whose source is present equals the census's legs, with no refusal; every roster line passes the roster gate and reaches Chromium alone; an exclusions reason names Firefox or WebKit, or carries the embedded-driver sentence, when and only when the source does; a pending line names a PR and stands while its source is absent, and is red with the promotion remedy once it is present", async (t) => {
  const mod = await load();
  const { census, rosterGap, engineNames, classOf, EMBEDDED_PHRASE, ENGINE_PHRASE } = mod;
  const c = census(REPO);
  assert.deepEqual(c.refusals, [], "the census refused a form it cannot classify (file:line above each): rewrite the form, or teach scripts/browser-legs-census.mjs to read it");
  assert.ok(c.legs.length > 100, "the tree holds browser legs (the census found " + c.legs.length + "; a count near zero means the rule stopped matching, not that the legs left)");
  const roster = parseRoster(read(path.join(EXT, ROSTER)));
  const excludedText = read(path.join(EXT, EXCLUDED));
  const excluded = parseExcluded(excludedText);
  const header = headerOf(excludedText);
  // two keys to one sentence, the header's quotation and the module's export: held equal, never one trusted over the other
  assert.equal(header.embedded, EMBEDDED_PHRASE, EXCLUDED + "'s header quotes the embedded-driver sentence as " + JSON.stringify(header.embedded) + " and scripts/browser-legs-census.mjs exports EMBEDDED_PHRASE as " + JSON.stringify(EMBEDDED_PHRASE) + ": the two disagree; make them one sentence");
  const kindOf = (e: Excluded) => reasonKind(e.reason as string, header.sentence, ENGINE_PHRASE, EMBEDDED_PHRASE);
  // a malformed line, or an exclusions line without a reason, is refused by name before any lookup: the LINE is shown with its
  // whitespace visible (JSON spells a tab \t and a carriage return \r) and the leg it names, its first word after leading
  // whitespace, is attributed to it, so the census never reports that leg as missing from both files. A bundle path holds no
  // whitespace, so the first word is the path or nothing well formed (the script's names_of and tools/ci-browser-legs.test.mjs
  // read the same shape).
  const WELL_FORMED = /^out-tests\/\S+\.test\.js$/;
  const namesOf = (line: string) => line.replace(/^\s+/, "").split(/\s/)[0];
  for (const e of roster) assert.match(e.bundle, WELL_FORMED, ROSTER + " line " + e.n + ": " + JSON.stringify(e.bundle) + " is not a bundle path (out-tests/<dir>/<name>.test.js; a trailing space, tab or carriage return counts): fix the line" + (WELL_FORMED.test(namesOf(e.bundle)) ? "; it names " + namesOf(e.bundle) + ", which is judged by that line and not called missing from both files" : ""));
  for (const e of excluded) {
    const line = e.reason === null ? e.bundle : e.bundle + "\t" + e.reason;
    assert.ok(e.reason !== null && e.reason.trim() !== "", EXCLUDED + " line " + e.n + ": " + JSON.stringify(line) + " has no reason: write the bundle path, a tab, and why the gating job does not run it" + (WELL_FORMED.test(namesOf(line)) ? "; it names " + namesOf(line) + ", which is judged by that line and not called missing from both files" : ""));
    assert.match(e.bundle, WELL_FORMED, EXCLUDED + " line " + e.n + ": " + JSON.stringify(line) + " is not a bundle path, a tab and a reason (a leading or trailing space, tab or carriage return counts): fix the line" + (WELL_FORMED.test(namesOf(line)) ? "; it names " + namesOf(line) + ", which is judged by that line and not called missing from both files" : ""));
  }
  // a source that is not in the tree is named as such (the census has no record of it) and never called "no browser leg"
  const gone = (file: string, e: { n: number; bundle: string }) => { const src = sourceOf(e.bundle); assert.ok(fs.existsSync(src), where(file, e) + " names " + path.relative(REPO, src) + ", which is not in the tree (the source moved or was deleted): fix the line"); };
  for (const e of roster) {
    gone(ROSTER, e);
    const r = c.byBundle.get(e.bundle);
    assert.ok(r && r.reaches, where(ROSTER, e) + " names no browser leg" + (r && r.launcherImported ? ": " + rosterGap(r) : " (the source reaches no browser by the census rule): remove the line"));
    assert.equal(rosterGap(r), null, where(ROSTER, e) + " does not launch through the one shared launcher (" + rosterGap(r) + "): only inBrowser reads ROMP_BROWSER_LEGS_REQUIRE, so a launch or a skip of the leg's own stands outside the switch; launch through inBrowser (ui/webview/real-viewer-leg.ts), with no launch, skip or playwright of the leg's own, before rostering it");
    assert.deepEqual(engineNames(r), [], where(ROSTER, e) + " reaches " + engineNames(r).join(" and ") + "; the gating job installs Chromium only, so under the switch that launch is red: keep the leg in " + EXCLUDED + " with that reason");
  }
  const pending = excluded.filter((e) => e.pending);
  for (const e of pending) {
    assert.ok(e.pending && e.pending.pr !== null, where(EXCLUDED, e) + " has a pending reason that names no PR (" + JSON.stringify(e.reason) + "): a pending line reads 'pending #<PR>: <why>', the PR whose merge of main brings the leg and promotes the line");
    const pr = (e.pending as { pr: string }).pr, src = sourceOf(e.bundle);
    assert.ok(!fs.existsSync(src), where(EXCLUDED, e) + " is pending #" + pr + " and its source " + path.relative(REPO, src) + " is in the tree, so the leg has arrived (#" + pr + " merged main, or this is #" + pr + "'s branch) and the line's condition has passed: promote it: " + (fs.existsSync(src) ? promotionOf(mod, c.byBundle.get(e.bundle), e.bundle) : ""));
    const v = kindOf(e);
    assert.equal(v.kind, "pending", where(EXCLUDED, e) + ": " + (v.kind === null ? v.refusal : "the reason reads as the " + v.kind + " form") + "; the reason reads: " + e.reason);
  }
  // every other row: exactly one closed form, and the form's engine and driver words true of the source (reasonVerdict, one
  // writer, driven over a synthetic table in its own test below)
  for (const e of excluded) {
    if (e.pending) continue;   // its source is absent (asserted above), so the census has no record of it and the reason's engine and driver words are not about a source in the tree
    const s = reasonVerdict(e, c.byBundle.get(e.bundle), e.reason === null ? { kind: null, refusal: "no reason" } : kindOf(e), mod, EMBEDDED_PHRASE);
    if (s !== null) assert.fail(s);
  }
  // the equality is over the roster plus the exclusions whose source is present: a pending line names an absent source (asserted
  // above), so it is a member of neither the listed set nor the census, and the two stay equal
  const listed = new Set([...roster.map((e) => e.bundle), ...excluded.filter((e) => !e.pending).map((e) => e.bundle)]);
  const neither = c.legs.filter((b) => !listed.has(b));
  assert.deepEqual(neither, [], "browser legs in neither " + ROSTER + " nor " + EXCLUDED + ", each with the remedy the census derives from its source: " + neither.map((b) => b + ": " + neitherRemedy(mod, c.byBundle.get(b), b)).join("; "));
  assert.deepEqual([...listed].sort(), c.legs, "the roster plus the present-source exclusions is exactly the census's legs");
  // the population, derived from this run (figures for a PR body come from here, never from a constant kept elsewhere)
  const recs = c.legs.map((b) => c.byBundle.get(b) as Rec);
  const count = (f: (r: Rec) => boolean) => recs.filter(f).length;
  const classes: Record<string, number> = {};
  for (const r of recs) classes[classOf(r)] = (classes[classOf(r)] || 0) + 1;
  const engineSets: Record<string, number> = {};
  for (const r of recs) { const k = (r.engines || []).join("+") || "none"; engineSets[k] = (engineSets[k] || 0) + 1; }
  t.diagnostic("census: " + c.byBundle.size + " test modules read (and " + c.localModules + " modules of the tree they load), " + c.legs.length + " legs, " + roster.length + " rostered, " + (excluded.length - pending.length) + " excluded, " + pending.length + " pending (absent sources, PRs " + JSON.stringify([...new Set(pending.map((e) => "#" + (e.pending as { pr: string }).pr))]) + ")");
  t.diagnostic("classes: " + JSON.stringify(classes) + "; engines: " + JSON.stringify(engineSets));
  t.diagnostic("rosterable by the gate: " + count((r) => rosterGap(r) === null) + "; legs importing the launcher and never calling it: " + count((r) => !!r.launcherImported && r.sharedCalls === 0) + "; shared calls inside try/catch (admitted, reported): " + count((r) => (r.swallow || []).length > 0) + "; legs with a skip or todo: " + count((r) => (r.skipTodo || []).length > 0) + "; own launches: " + recs.reduce((n, r) => n + (r.launches || []).length, 0) + " sites in " + count((r) => (r.launches || []).length > 0) + " modules");
});

/** What each planted form is: the fixture's file under tests/fixtures/browser-legs-plants/<dir>, and the verdict the census
 *  gives it. `gap` is a substring of rosterGap's sentence (null: the gate passes); `refused` a substring of the refusal, with the
 *  line; `strictRefused`: refused under --strict-computed, where computed names are not folded. The round-1 findings each plant
 *  answers are named beside it. A round-3 row (p38 to p88) also says whether it discriminates against the census before round 3
 *  (the round-2 base): `holds` on a row that stays green under that census, one of the five Held forms and the row's detail;
 *  `carried` on a row that reds under it, but not on the property its section names, naming the plant that carries that property.
 *  A round-4 row (p89 to p155) carries the same two fields against the census before round 4 (the module at the round-3 head), and
 *  a round-5 row (p156 onward) against the census before round 5 (the module at the round-4 head), where the fifth Held form, a
 *  pin of an arm no plant carried, names a row refused there already by an arm no earlier row exercised.
 *  The plant-table test holds the table to these fields; the discrimination itself was established by running that census over
 *  the plants (the PR's notes) and is not re-run here. */
type Held = `${"a stated residual boundary" | "the no-refusal half of a pair whose partner reds" | "a guard of round 3's own scoping" | "a shape another plant carries" | "a pin of an arm no plant carried"}: ${string}`;
type Plant = {
  dir: string; file: string; leg: boolean; cls: string; gap: string | null; engines?: string[]; playwright?: string[];
  launches?: string[]; skipTodo?: string[]; swallow?: number[]; refused?: string; strictRefused?: boolean; launcherImported?: boolean;
  holds?: Held; carried?: `a shape another plant carries: ${string}`;
};
const W = "ui/webview";
/** The shadow refusal's WHOLE sentence after "<file>:<line>: ", as the census emits it (read from a run of the CLI over the plants,
 *  not guessed): the p17 and p47 rows hold the whole sentence, not the prefix "a local declaration shadows an import binding",
 *  because the sentence (why the shadow is refused, and the remedy) is what the round-3 item landed and the prefix predates it;
 *  a reword of the why or the remedy in the module is red at those rows. The two rows hold the SENTENCE: a reword of the module's
 *  refusal moves this constant too (and the rows through it). */
const SHADOW_REFUSAL = "a local declaration shadows an import binding of the launcher or of playwright (a use inside the local's scope reaches the local, not the import; the shadow is refused so an import it leaves uncalled, or whose launches it hides, is not read as an ordinary non-leg without notice: rename the local)";
/** The round-4 refusals' sentences after "<file>:<line>: " (and, for a hand-on, handedHow's parenthetical inside the module-binding
 *  sentence), as the census emits them (read from a run of the CLI over the plants, not guessed): the p89 to p120 rows that refuse
 *  hold the SENTENCE through these constants, since the sentence (the form named, why it is unread, the remedy) is what round 4
 *  landed (the p129 and p142 to p154 rows, the author's closing pass after round 4's verification, the same way); a reword of the
 *  module's refusal moves the constant and the rows through it. The four existing computed-member rows
 *  (p15a, p31, p64, p65) hold the prefix that predates the reword and stay where they are. No row spells the refused line's code
 *  after the sentence: this module is itself a module of the tree the census reads, and a string literal here that loads a
 *  playwright package by its text (`require("playwright")` spelled out) would make this test an embedded-driver leg. */
const REQUIRECJS_ALIAS_REFUSAL = "the launcher's requireCjs loader handed on as a value, not called (a load made through the alias is unread by the walker: call requireCjs where the load is made)";
const REQUIRECJS_MEMBER_HANDOFF = "read for requireCjs without a call, so a load made through it elsewhere is unread: call requireCjs where the load is made";
const REQUIRECJS_LOAD_HANDOFF = "the launcher loaded where it stands and read for requireCjs without a call, so a load made through it elsewhere is unread: call requireCjs on the load where it is made";
const COND_PLAYWRIGHT_REFUSAL = "a playwright load or binding read through a conditional or logical expression the walker does not follow (the engines and launches read through it are unread): bind the load in a statement of its own";
const COND_LAUNCHER_REFUSAL = "the shared launcher loaded inside a conditional or logical expression the walker does not follow, so where inBrowser is called from is unread: bind the load in a statement of its own";
const COND_BINDING_HANDOFF = "read through a conditional or logical expression the walker does not follow: bind the module in a statement of its own";
const COMPUTED_REFUSAL = "a computed member with a name the walker cannot fold on a playwright or launcher binding or load";
const SPREAD_TAIL = "a spread element at or before the engine position, an argument list the walker cannot read (an engine may be passed in it): spell each argument out";
const CALLED_HANDOFF = "called as a function, which the launcher's module is not: call its inBrowser";
const CONSTRUCTED_HANDOFF = "constructed with new, which the launcher's module is not: call its inBrowser";
const OPERAND_HANDOFF = "read as an operand of !==, a value use the walker does not follow: use the binding only to call inBrowser";
const INBROWSER_VALUE_REFUSAL = "the launcher's inBrowser binding used as a value, not called (the walker cannot follow where it is called from)";
/** THE SAFETY NET's sentences (round 5), as the census emits them (read from a run of the CLI over the plants, not guessed): after
 *  "<file>:<line>: ", the head names the first unaccounted mention by kind and token and the count of the rest, and the tail says
 *  which clause refused (the fold produced no reach and no refusal, or its reach does not account for the mention); the read-through
 *  clause has a sentence of its own naming the package; a companion's own net refusal reaches its importer through localRefusals'
 *  cannot-classify arm (VIA_COMPANION). The round-5 rows hold the SENTENCE through these constants: a reword of the module's net
 *  moves the constants and the rows through them. No constant spells a package name as a call's argument: this module is itself a
 *  module of the tree the census reads, and the net refuses exactly that position (the p74 form), which is why the pieces below are
 *  concatenated and the driver rows append their token to NET_DRIVER themselves. */
const NET_HEAD = "mentions a browser load the walker did not fold (";
const NET_NO_REACH = "), and the fold produced no reach and no refusal, so the census refuses the module rather than pass it silently: spell the load through a form the walker reads, or teach scripts/browser-legs-census.mjs the form";
const NET_REACH = "), and the fold's reach does not account for it, so the census refuses the module rather than pass the mention silently: spell the load through a form the walker reads, or teach scripts/browser-legs-census.mjs the form";
const NET_RCJS = "the identifier requireCjs, the launcher's loader, resolved to no launcher binding: \"requireCjs\"";
const NET_PW = "a playwright package specifier: \"playwright\"";
const NET_LAUNCHER = "the launcher module's name: \"./real-viewer-leg\"";
const NET_CR = (spelled: string) => "createRequire in a position the walker does not fold (not a declaration's own name or an import's, the callee of a call bound as a loader or applied as one, or the object of a member other than call, apply or bind): \"" + spelled + "\"";
const NET_MODREQ = "module.require, a loader, in a position the walker does not read (not called): \"module.require\"";
const NET_DRIVER = "a playwright package specifier inside a string's text read as code: ";
const NET_NMPW = "a relative path into node_modules naming a playwright package: \"../../vscode-extension/node_modules/playwright\"";
const NET_READ_THROUGH = "the census read no engine and no launch through the playwright package it loads (playwright), so the load or its binding is handed on where the walker does not read and the engines and launches reached through it are unread: bind the load to a name in a statement of its own and launch on that name";
const MORE = (n: number) => "; and " + n + " more mention" + (n > 1 ? "s" : "");
const VIA_COMPANION = (chain: string, companion: string, mention: string) => "loads " + chain + ", which the census cannot classify (" + companion + ":2: " + NET_HEAD + mention + NET_NO_REACH + ")";
/** The round-5 FOLDS' sentences (the forms the net planted, read by the walker since the folds landed: each row that moved from the
 *  net's sentence to a fold's holds the fold's SENTENCE through these, and reds under the net-only module, whose sentence differs).
 *  The positions are valueHandedHow's, the parenthetical the loader and playwright hand-on refusals share. */
const LOADER_REEXPORT = (chain: string) => "loads " + chain + ", which hands on the shared launcher's requireCjs loader (a re-export of it, or of the launcher whole), so a playwright load or a launch this module makes through it is unread";
const LOADER_HANDOFF = (name: string, how: string) => "a loader (" + name + ") handed on as a value, not called (a load made through the alias is unread by the walker: call the loader where the load is made): " + how;
const CREATEREQUIRE_HANDOFF = (how: string) => "a createRequire(...) loader made where it stands and handed on (" + how + "), so every load made through it is unread by the walker: bind it to a name in a declaration of its own, or apply it where the load is made";
const HOW_ALIASED = "aliased by a declaration";
const HOW_ASSIGNED = "aliased by an assignment";
const HOW_ARGUMENT = "passed as an argument";
const HOW_LITERAL = "held in an array or an object literal";
const HOW_MEMBER = (name: string) => "read for ." + name + ", through which a load is made or a loader bound where the walker does not follow";
const HOW_RETURNED = "returned from a function";
const PW_HANDOFF = (name: string, how: string) => "a playwright binding (" + name + ") handed on as a value (" + how + "), so the engines and launches reached through it are unread by the walker: launch on the binding where it is bound, or bind the load in the module that launches";
const COMPOUND_PLAYWRIGHT = "a playwright load or binding bound by a compound assignment the walker does not follow (which value the name takes is unread): bind it with = in a statement of its own";
const COMPOUND_LAUNCHER = "the shared launcher loaded by a compound assignment the walker does not follow, so where inBrowser is called from is unread: bind the load with = in a statement of its own";
const WRITE_REFUSAL = (module: string, name: string, what: string) => "a " + module + " binding (" + name + ") written with " + what + ", which the walker does not follow: a call through the rebound name would count as a call through the binding while what the name holds is unread: bind the load once, or give the other value a name of its own";
const WHAT_NO_LOAD = "a value that is no load the walker reads";
const WHAT_PW_LOAD = "a load of a playwright package";
const PLANT_TABLE: Plant[] = [
  { dir: W, file: "p01-alias.test.ts", leg: true, cls: "shared", gap: null },                                                     // tests-1, extra7-2, extra7-3: an aliased import, called
  { dir: W, file: "p02-single-quote-require.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: ["chromium"], playwright: ["playwright"], launches: [".launch("] }, // extra5-1
  { dir: W, file: "p03-namespace.test.ts", leg: true, cls: "shared", gap: null },
  { dir: W, file: "p04-launch-persistent.test.ts", leg: true, cls: "both", gap: "loads playwright itself", engines: ["chromium"], launches: [".launchPersistentContext("] }, // extra7-4, extra6-1
  { dir: W, file: "p05-destructured-launch.test.ts", leg: true, cls: "both", gap: "loads playwright itself", engines: ["chromium"], launches: ["destructured launch", "call of destructured launch"] }, // extra7-4
  { dir: W, file: "p06-bracket-launch.test.ts", leg: true, cls: "both", gap: "loads playwright itself", engines: ["chromium"], launches: [".launch("] }, // extra7-4
  { dir: W, file: "p07-swallow.test.ts", leg: true, cls: "shared", gap: null, swallow: [3] },                                     // extra8-2: admitted, reported with its line
  { dir: W, file: "p08-comment-skip.test.ts", leg: true, cls: "shared", gap: null, skipTodo: [] },                                // extra8-3: a comment holds no skip
  { dir: W, file: "p09a-named-firefox.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: ["firefox"] }, // extra6-1
  { dir: W, file: "p09b-destructured-firefox-bare-webkit.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: ["firefox", "webkit"] }, // extra6-1
  { dir: W, file: "p10-block-comment-mention.test.ts", leg: false, cls: "none", gap: "never calls its inBrowser through that import: call it, or remove the line", launcherImported: true }, // extra7-1, extra7-2's non-launching importer
  { dir: W, file: "p11-source-pin-string.test.ts", leg: false, cls: "none", gap: null, launcherImported: false },                // extra7-1: a source pin is a string
  { dir: W, file: "p12-dynamic-import.test.ts", leg: true, cls: "shared", gap: null },
  { dir: W, file: "p13-value-indirect.test.ts", leg: false, cls: "none", gap: "never calls its inBrowser through that import", launcherImported: true, refused: "p13-value-indirect.test.ts:3: the launcher's inBrowser binding used as a value" }, // extra7-2's indirect form: refused, and the import stands uncalled
  { dir: W, file: "p14-nonliteral-spec.test.ts", leg: false, cls: "none", gap: null, refused: "p14-nonliteral-spec.test.ts:3: a loader whose specifier is not a string literal" },
  { dir: W, file: "p15a-computed-env.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: [], refused: "p15a-computed-env.test.ts:3: a computed member with a name the walker cannot fold" },
  { dir: W, file: "p15b-computed-loop.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: ["chromium", "firefox"], strictRefused: true }, // the tree's live for-of shape
  { dir: W, file: "p16-type-only.test.ts", leg: false, cls: "none", gap: null, launcherImported: false },
  { dir: W, file: "p17-shadow.test.ts", leg: false, cls: "none", gap: "never calls its inBrowser through that import", launcherImported: true, refused: "p17-shadow.test.ts:3: " + SHADOW_REFUSAL }, // fresh-1: the call reaches the local arrow, so the import stands uncalled and the identifier-named shadow is refused; the row holds the whole refusal sentence (SHADOW_REFUSAL) because the sentence is what round 3 landed and the prefix predates it. This row read leg true, class shared, before names were resolved by scope: a WRONG EXPECTATION the module-flat lookup let pass (the call is the local's, never the import's)
  { dir: W, file: "p18-launch-call.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", launches: [".launch( via .call/.apply"] },
  { dir: W, file: "p19-default-core.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: ["webkit"], playwright: ["playwright-core"] },
  { dir: W, file: "p20-todo.test.ts", leg: true, cls: "shared", gap: "holds a skip or todo of its own (line 3: .todo()", skipTodo: [".todo(", "{ todo: } option"] }, // correctness-1's todo, read from the tree
  { dir: W, file: "p21-import-equals.test.ts", leg: true, cls: "shared", gap: null },
  { dir: "vscode-extension/src", file: "p22-from-src.test.ts", leg: true, cls: "shared", gap: null },                             // the launcher by a resolved relative path
  { dir: W, file: "p23-js-suffix.test.ts", leg: true, cls: "shared", gap: null },
  { dir: W, file: "p24-connect-cdp.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", launches: [".connectOverCDP("] }, // extra6-1's connect forms
  { dir: W, file: "p25-launcher-loader.test.ts", leg: true, cls: "both", gap: "loads playwright itself" },                     // playwright through the launcher's own requireCjs
  { dir: W, file: "p26-embedded-driver.test.ts", leg: true, cls: "embedded", gap: "drives playwright from a child process whose source is held in a string (line 2)" },
  { dir: W, file: "p27-parse-error.test.ts", leg: false, cls: "refused", gap: null, refused: "p27-parse-error.test.ts:4: the parser reports a diagnostic" },
  { dir: W, file: "p28-string-param-callsites.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: ["chromium", "webkit"], strictRefused: true },
  // the round-2 verifiers' forms: a value use in an initializer, a reassigned let, and the modules of the tree a test loads
  { dir: W, file: "p29-value-alias.test.ts", leg: false, cls: "none", gap: "never calls its inBrowser through that import", launcherImported: true, refused: "p29-value-alias.test.ts:3: the launcher's inBrowser binding used as a value" }, // const f = inBrowser; f(t, ...)
  { dir: W, file: "p30-default-value.test.ts", leg: false, cls: "none", gap: "never calls its inBrowser through that import", launcherImported: true, refused: "p30-default-value.test.ts:4: the launcher's inBrowser binding used as a value" }, // const { x = inBrowser } = o
  { dir: W, file: "p31-let-reassigned.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: [], refused: "p31-let-reassigned.test.ts:5: a computed member with a name the walker cannot fold" }, // let name = "chromium"; name = "firefox"; pw[name]
  { dir: W, file: "p32-barrel.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p32-barrel.test.ts:2: loads ui/webview/leg-barrel.ts, which binds or calls the shared launcher's inBrowser" }, // export { inBrowser } from the launcher
  { dir: W, file: "p33-wrapper.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p33-wrapper.test.ts:2: loads ui/webview/leg-wrap.ts, which binds or calls the shared launcher's inBrowser" }, // a wrapper calling inBrowser
  { dir: W, file: "p34-helper-playwright.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p34-helper-playwright.test.ts:2: loads ui/webview/pw-helper.ts, which names a playwright package (playwright)" },
  { dir: W, file: "p35-chain.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p35-chain.test.ts:2: loads ui/webview/leg-chain.ts, which loads ui/webview/leg-wrap.ts, which binds or calls the shared launcher's inBrowser" }, // two modules away
  { dir: W, file: "p36-wrapper-beside-call.test.ts", leg: true, cls: "shared", gap: null },                                       // the wrapper beside a call of inBrowser itself: a shared leg, no refusal
  { dir: W, file: "p37-missing-module.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p37-missing-module.test.ts:2: loads ./no-such-module, which names no file in the tree" },
  // the round-2 verifiers' forms, fresh-2: a bind target the walker does not follow is refused by the kind the line holds
  { dir: W, file: "p38-prop-assign-launcher.test.ts", leg: false, cls: "none", gap: "never calls its inBrowser through that import", launcherImported: true, refused: "p38-prop-assign-launcher.test.ts:3: a property assignment of a loaded module the walker does not follow: h.leg" }, // h.leg = require(the launcher); h.leg.inBrowser(t, ...)
  { dir: W, file: "p39-prop-assign-playwright.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: [], launches: [], refused: "p39-prop-assign-playwright.test.ts:4: a property assignment of a playwright expression the walker does not follow: o.pw" }, // o.pw = pw; o.pw.chromium.launch(): the launch sits behind the refused target
  { dir: W, file: "p40-elem-assign-playwright.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: ["chromium"], launches: [], refused: "p40-elem-assign-playwright.test.ts:4: an element assignment of a playwright expression the walker does not follow: o[0]" }, // o[0] = pw.chromium: the engine is read from the value, the launch through o[0] is not
  { dir: W, file: "p41-array-destructure-playwright.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: [], launches: [], refused: "p41-array-destructure-playwright.test.ts:3: an array destructuring of a playwright expression the walker does not follow: [eng]", carried: "a shape another plant carries: fresh-2's kind-naming targetKind is carried by p38, p39, p40 and p43 (red under one constant for every kind), since this row's kind is the constant's own text; it reds under the census before round 3 on the sentence's tail alone (the walker does not follow)" },
  { dir: W, file: "p42-array-destructure-loaded.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: [], launches: [], refused: "p42-array-destructure-loaded.test.ts:2: an array destructuring of a loaded module the walker does not follow: [x]", carried: "a shape another plant carries: fresh-2's kind-naming targetKind is carried by p38, p39, p40 and p43 (red under one constant for every kind), since this row's kind is the constant's own text; it reds under the census before round 3 on one word of the sentence alone (a loaded module)" },
  { dir: W, file: "p43-object-assign-destructure.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: [], launches: [], refused: "p43-object-assign-destructure.test.ts:4: an object destructuring by assignment of a playwright expression the walker does not follow: { chromium }" },
  // fresh-1: a name is read at its use site by lexical scope, so an inner scope's same-named binding is not the tracked one
  { dir: W, file: "p44-pattern-param-reuses-name.test.ts", leg: true, cls: "both", gap: "loads playwright itself", engines: ["firefox"], launches: [".launch("] }, // a parameter's array pattern reuses pw inside an arrow (the shape PR 853's module holds): the inner pw is the parameter, the module's pw is playwright, and nothing is refused
  { dir: W, file: "p45-catch-and-for-shadow.test.ts", leg: true, cls: "shared", gap: null },                                       // a catch variable and a for-of const named inBrowser, the import called after them: the call reaches the import
  { dir: W, file: "p46-inner-destructured-shadow.test.ts", leg: false, cls: "none", gap: "never calls its inBrowser through that import", launcherImported: true }, // an inner block's destructured inBrowser is what the call reaches, so the import stands uncalled; a destructured shadow has no identifier-named declaration, so no shadow refusal
  { dir: W, file: "p47-shadow-delegates.test.ts", leg: true, cls: "shared", gap: null, refused: "p47-shadow-delegates.test.ts:3: " + SHADOW_REFUSAL, carried: "a shape another plant carries: fresh-1's scoping is carried by p17 and p46 (leg false by scope where the flat lookup read a call of the import) and p45 (no refusal by scope where the flat lookup refused its catch variable and for-of const as value uses); this row's leg, class and gap are what the census before round 3 also gave and its refusal prefix predates round 3, so it reds under that census on the shadow refusal's whole sentence alone (SHADOW_REFUSAL, r3v-census-3)" }, // fresh-1's twin: the local shadow delegates to a module-level helper that calls the import, so the module IS a shared leg (the call resolves to the import by scope) and the identifier-named shadow is still refused; the row holds the whole refusal sentence (SHADOW_REFUSAL) because the sentence is what round 3 landed and the prefix predates it
  // the round-2 review's roads, section A of its rulings: a loader result used where it stands, in any position
  { dir: W, file: "p48-require-pw-chain.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: ["chromium"], playwright: ["playwright"], launches: [".launch("] }, // correctness-1, extra7-1: require("playwright").chromium.launch(), never bound
  { dir: W, file: "p49-require-launcher-chain.test.ts", leg: true, cls: "shared", gap: null, launcherImported: true },              // correctness-1: require(the launcher).inBrowser(t, ...), the load followed as the object of the member the call arm read
  { dir: W, file: "p50-class-field-loader.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: [], launches: [], playwright: ["playwright"], refused: "p50-class-field-loader.test.ts:2: " + NET_READ_THROUGH }, // correctness-1: a class field holding the loader result; the package is recorded where it is resolved, the launch through the field is not derived, and since round 5 THE SAFETY NET's read-through clause refuses the record (a load with no engine and no launch read through it) where round 2 accepted it as recorded-unread
  { dir: W, file: "p51-object-property-loader.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: [], launches: [], playwright: ["playwright"], refused: "p51-object-property-loader.test.ts:2: " + NET_READ_THROUGH }, // correctness-1: an object property holding it (round 5: refused by the read-through clause, as p50)
  { dir: W, file: "p52-wrapper-return.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p52-wrapper-return.test.ts:2: THE INVARIANT: the census resolved the shared launcher (./real-viewer-leg) here and its record carries nothing of the load" }, // correctness-1's wrapper return: the load stands in a position the walker does not read, refused by the invariant (before it: class none, no refusal, a false gap sentence)
  { dir: W, file: "p53-createrequire-direct-pw.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: ["chromium"], playwright: ["playwright"], launches: [".launch("] }, // extra6-1: createRequire(__filename)("playwright"), the loader applied directly
  { dir: W, file: "p54-createrequire-direct-launcher.test.ts", leg: true, cls: "shared", gap: null, launcherImported: true },       // extra6-1: the same for the launcher, destructured
  { dir: W, file: "p55-requirecjs-unbound.test.ts", leg: true, cls: "own", gap: "never calls its inBrowser through that import", engines: ["chromium"], playwright: ["playwright"], launches: [".launch("], launcherImported: true }, // extra7-1: requireCjs("playwright").chromium.launch() on the launcher's own loader, unbound
  { dir: W, file: "p56-await-import-unbound.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: ["chromium"], playwright: ["playwright"], launches: [".launch("] }, // extra7-1: (await import("playwright")).chromium.launch()
  { dir: W, file: "p57-import-then.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: [], launches: [], playwright: ["playwright"], refused: "p57-import-then.test.ts:2: " + NET_READ_THROUGH }, // extra7-1: import("playwright").then(pw => ...): the package is recorded, the launch on the callback's parameter is not derived (round 5: refused by the read-through clause, as p50)
  { dir: W, file: "p58-member-to-value.test.ts", leg: false, cls: "none", gap: "never calls its inBrowser through that import", launcherImported: true, refused: "p58-member-to-value.test.ts:3: the launcher's module binding handed on as a value (read for inBrowser without a call)" }, // extra7-2: const run = leg.inBrowser
  { dir: W, file: "p59-namespace-alias.test.ts", leg: false, cls: "none", gap: "never calls its inBrowser through that import", launcherImported: true, refused: "p59-namespace-alias.test.ts:3: the launcher's module binding handed on as a value (aliased by a declaration)" }, // extra7-2: const alias = leg
  { dir: W, file: "p60-destructure-namespace.test.ts", leg: false, cls: "none", gap: "never calls its inBrowser through that import", launcherImported: true, refused: "p60-destructure-namespace.test.ts:3: the launcher's module binding handed on as a value (destructured)" }, // extra7-2: const { inBrowser } = leg
  { dir: W, file: "p61-namespace-as-argument.test.ts", leg: false, cls: "none", gap: "never calls its inBrowser through that import", launcherImported: true, refused: "p61-namespace-as-argument.test.ts:4: the launcher's module binding handed on as a value (passed as an argument)" }, // extra7-2: go(leg, t)
  { dir: W, file: "p62-await-import-member-call.test.ts", leg: true, cls: "shared", gap: null, launcherImported: true },            // extra7-2: (await import(the launcher)).inBrowser(t, ...)
  { dir: W, file: "p63-default-import-member.test.ts", leg: true, cls: "shared", gap: null, launcherImported: true },               // extra7-2: a default import's inBrowser member, called
  { dir: W, file: "p64-cast-pw-computed.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: [], launches: [], refused: "p64-cast-pw-computed.test.ts:4: a computed member with a name the walker cannot fold" }, // extra7-3: (pw as any)[which()].launch(), the cast on the object unwrapped at every step of rootOf
  { dir: W, file: "p65-cast-launcher-computed.test.ts", leg: false, cls: "none", gap: "never calls its inBrowser through that import", launcherImported: true, refused: "p65-cast-launcher-computed.test.ts:4: a computed member with a name the walker cannot fold" }, // extra7-3: (leg as any)[which()](t, ...): one refusal, the computed member's (extra7-4: the reference is read as refused, not refused twice)
  { dir: W, file: "p66-driver-substitution.test.ts", leg: true, cls: "embedded", gap: "drives playwright from a child process whose source is held in a string (line 3)" }, // extra7-5: a driver template assembled with a substitution bound to a const literal, folded before the text is read
  { dir: W, file: "p67-driver-concatenation.test.ts", leg: true, cls: "embedded", gap: "drives playwright from a child process whose source is held in a string (line 2)" }, // extra7-5: a + concatenation, folded
  // the third residual, stated in the census header: a browser reached without spelling a playwright package or the launcher is unread, class none, no refusal
  { dir: W, file: "p68-driver-env-piece.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, holds: "a stated residual boundary: the third residual's run-time package name (the fold leaves a placeholder), class none, no refusal, which the census before round 3 also gives" },                   // extra7-5's unfoldable piece: the package name arrives from the environment, the fold leaves a placeholder that spells nothing
  { dir: W, file: "p69-other-driver-package.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, holds: "a stated residual boundary: the third residual's other driver package, class none, no refusal, which the census before round 3 also gives" },               // extra6-4: another driver package (puppeteer)
  { dir: W, file: "p70-playwright-chromium-package.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, holds: "a stated residual boundary: a package name containing a tracked spelling is no playwright package, class none, no refusal, which the census before round 3 also gives" },        // extra6-4: a package whose name contains a tracked spelling (playwright-chromium) is not a playwright package to the census
  { dir: W, file: "p71-spawn-binary.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, holds: "a stated residual boundary: the third residual's spawned browser binary, class none, no refusal, which the census before round 3 also gives" },                       // extra6-4: a browser binary spawned by name
  // extra7-4: the call arm and the value-use arm read one record of the identifier the call resolved through
  { dir: W, file: "p72-namespace-member-call.test.ts", leg: true, cls: "shared", gap: null, launcherImported: true, holds: "the no-refusal half of a pair whose partner reds: p73 (.bind, refused as a value use) reds under the census before round 3, which read the .bind as a call; this row's counted call is what that census also gave" },               // leg.inBrowser.call(null, t, ...): a counted shared call, never also a value use
  { dir: W, file: "p73-namespace-member-bind.test.ts", leg: false, cls: "none", gap: "never calls its inBrowser through that import", launcherImported: true, refused: "p73-namespace-member-bind.test.ts:3: the launcher's module binding handed on as a value (read for inBrowser without a call (.bind makes no call))" }, // leg.inBrowser.bind(null): .bind makes no call, so the bound reference is a value use
  // THE INVARIANT's boundary: text that names playwright or the launcher without a resolution (a title, an array literal, a regex, a message string) trips nothing of the invariant; since round 5 THE SAFETY NET reads such text on its own terms and refuses a package name standing in a specifier-capable position (here deps.includes's argument at line 5, the array at line 3 and the regex being no such position), the net's stated false refusal, whose remedy is a respelling (as this file's own assembled literal was respelled for it)
  { dir: W, file: "p74-text-names-playwright.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p74-text-names-playwright.test.ts:5: " + NET_HEAD + NET_PW + NET_NO_REACH }, // held before round 5 as a stated residual boundary (class none, no refusal, which the census before round 3 also gave); the row now reds under that census on the net's refusal, so it holds nothing and the round-3 statement counts it red
  // regression-1's engine parameter (PR 853's launcher takes an engine as inBrowser's third argument): read into the engines the leg reaches, through the closed forms and the two the stub launcher's exports supply; anything else refused
  { dir: W, file: "p75-engine-for-of-import.test.ts", leg: true, cls: "shared", gap: null, engines: ["chromium", "firefox", "webkit"] }, // for (const engine of ENGINES), ENGINES the launcher's exported const array (853's shape)
  { dir: W, file: "p76-engine-typed-param.test.ts", leg: true, cls: "shared", gap: null, engines: ["chromium", "firefox", "webkit"] }, // a parameter typed by the launcher's exported alias Engine: the whole union, on the safe side
  { dir: W, file: "p77-engine-literal.test.ts", leg: true, cls: "shared", gap: null, engines: ["firefox"] },
  { dir: W, file: "p78-engine-unfoldable.test.ts", leg: true, cls: "shared", gap: null, engines: [], refused: "p78-engine-unfoldable.test.ts:3: an engine argument to the shared launcher the walker cannot fold" }, // process.env.ENGINE: refused, never read as no engine
  { dir: W, file: "p79-engine-via-call.test.ts", leg: true, cls: "shared", gap: null, engines: ["webkit"] },                          // inBrowser.call(null, t, body, "webkit"): the engine is the fourth argument
  { dir: W, file: "p80-engine-unknown-name.test.ts", leg: true, cls: "shared", gap: null, engines: [], refused: "p80-engine-unknown-name.test.ts:3: an engine argument to the shared launcher that names no engine (chrome" }, // a literal that is no engine
  // the round-3 verifiers' forms: the launcher handed to a promise callback or read for a default member (the tree's own idiom for sibling modules, `import(x).then(...)`), a helper that calls inBrowser on a load it never binds, a hoisted var, an awaited promise binding
  { dir: W, file: "p81-import-then-launcher.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p81-import-then-launcher.test.ts:2: the launcher loaded where it stands and handed on through a member the walker does not follow (a promise callback through .then, .catch or .finally, or a default member)" }, // import(the launcher).then((m) => m.inBrowser(...)): refused by name, the load read by that refusal (before: class none, no refusal, a false gap sentence)
  { dir: W, file: "p82-bound-promise-then.test.ts", leg: false, cls: "none", gap: "never calls its inBrowser through that import", launcherImported: true, refused: "p82-bound-promise-then.test.ts:3: the launcher's module binding handed on as a value (handed to a promise callback through .then" }, // const p = import(the launcher); p.then(({ inBrowser }) => ...): the binding handed on, the position named
  { dir: W, file: "p83-require-default-member.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p83-require-default-member.test.ts:2: THE INVARIANT: the census resolved the shared launcher (./real-viewer-leg) here and its record carries nothing of the load" }, // require(the launcher).default.inBrowser(...): a default member is no export of the launcher, so the load is not followed and the invariant refuses it
  { dir: W, file: "p84-helper-unbound-call.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p84-helper-unbound-call.test.ts:2: loads ui/webview/call-helper.ts, which binds or calls the shared launcher's inBrowser" }, // the helper calls require(the launcher).inBrowser(...) and binds nothing: a call hands the browser on to the importer as a binding does (before: class none, no refusal)
  { dir: W, file: "p85-helper-await-import-call.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p85-helper-await-import-call.test.ts:2: loads ui/webview/await-helper.ts, which binds or calls the shared launcher's inBrowser" }, // the same through (await import(the launcher)).inBrowser(...)
  { dir: W, file: "p86-helper-then.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p86-helper-then.test.ts:2: loads ui/webview/then-helper.ts, which the census cannot classify (ui/webview/then-helper.ts:2: the launcher loaded where it stands and handed on through a member the walker does not follow" }, // a helper doing the .then hand-on: the helper's own refusal reaches the importer
  { dir: W, file: "p87-hoisted-var.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: ["firefox"], playwright: ["playwright"], launches: [".launch("], holds: "a guard of round 3's own scoping: a var hoisted out of its block is bound at its function (r3v-census-4), which a census that never scoped cannot red against (it read the var flat); red under a var held at the block" }, // { var pw = require("playwright"); } then pw.firefox.launch() outside the block: the var is the module's, so the engine and the launch are read (before: engines [], launches [])
  { dir: W, file: "p88-bound-promise-await-later.test.ts", leg: false, cls: "none", gap: "never calls its inBrowser through that import", launcherImported: true, refused: "p88-bound-promise-await-later.test.ts:3: the launcher's module binding handed on as a value (awaited into a name the walker does not bind" }, // const p = import(the launcher); const m = await p; m.inBrowser(...): refused, the position named (before: the same refusal listing four forms the line does not hold)
  // the round-3 review's class ruling (round 4, extra6-1): the launcher's own requireCjs is a loader wherever it is reached, and a form that hands it on is refused by name
  { dir: W, file: "p89-requirecjs-namespace-member.test.ts", leg: true, cls: "own", gap: "never calls its inBrowser through that import", engines: ["firefox"], playwright: ["playwright"], launches: [".launch("], launcherImported: true }, // leg.requireCjs("playwright").firefox.launch() on a namespace import: the member callee is a loader (before round 4: class none, no refusal, the package, the engine and the launch all unread)
  { dir: W, file: "p90-requirecjs-default-member.test.ts", leg: true, cls: "own", gap: "never calls its inBrowser through that import", engines: ["firefox"], playwright: ["playwright"], launches: [".launch("], launcherImported: true }, // the same on a default import (before: class none, no refusal)
  { dir: W, file: "p91-requirecjs-destructured-require.test.ts", leg: true, cls: "own", gap: "never calls its inBrowser through that import", engines: ["firefox"], playwright: ["playwright"], launches: [".launch("], launcherImported: true }, // const { requireCjs } = require(the launcher): the binding pass 2 makes joins the loaders inside the fixpoint (before: class none, no refusal)
  { dir: W, file: "p92-requirecjs-destructured-await-import.test.ts", leg: true, cls: "own", gap: "never calls its inBrowser through that import", engines: ["webkit"], playwright: ["playwright"], launches: [".launch("], launcherImported: true }, // the same destructured from await import(the launcher), WebKit (before: class none, no refusal)
  { dir: W, file: "p93-requirecjs-member-bound-result.test.ts", leg: true, cls: "own", gap: "never calls its inBrowser through that import", engines: ["firefox"], playwright: ["playwright"], launches: [".launch("], launcherImported: true }, // const pw = leg.requireCjs("playwright"), the result bound and launched through (before: class none, no refusal)
  { dir: W, file: "p94-requirecjs-member-off-require.test.ts", leg: true, cls: "own", gap: "never calls its inBrowser through that import", engines: ["firefox"], playwright: ["playwright"], launches: [".launch("], launcherImported: true }, // require(the launcher).requireCjs("playwright"): the member callee off the load where it stands, the load followed (before: class none, no refusal)
  { dir: W, file: "p95-requirecjs-member-off-await-import.test.ts", leg: true, cls: "own", gap: "never calls its inBrowser through that import", engines: ["webkit"], playwright: ["playwright"], launches: [".launch("], launcherImported: true }, // the same off (await import(the launcher)), WebKit (before: class none, no refusal)
  { dir: W, file: "p96-requirecjs-member-alias.test.ts", leg: false, cls: "none", gap: "never calls its inBrowser through that import", launcherImported: true, refused: "p96-requirecjs-member-alias.test.ts:3: the launcher's module binding handed on as a value (" + REQUIRECJS_MEMBER_HANDOFF + ")" }, // const r = leg.requireCjs, then r("playwright"): the loader handed on through the module binding, the load through the alias unread, refused by name (before: class none, no refusal)
  { dir: W, file: "p97-requirecjs-named-alias.test.ts", leg: false, cls: "none", gap: "never calls its inBrowser through that import", launcherImported: true, refused: "p97-requirecjs-named-alias.test.ts:3: " + REQUIRECJS_ALIAS_REFUSAL }, // const r = requireCjs (the named import), then r("playwright"): the loader binding handed on as a value, refused by name (before: class none, no refusal)
  { dir: W, file: "p98-helper-requirecjs-member.test.ts", leg: true, cls: "shared", gap: null, refused: "p98-helper-requirecjs-member.test.ts:3: loads ui/webview/requirecjs-helper.ts, which names a playwright package (playwright)" }, // a shared caller whose helper launches through leg.requireCjs("playwright").firefox: the helper's package is read, so the import is refused with the chain (before: class shared, gap null, no refusal, the helper's Firefox launch unread)
  // fresh-1: a playwright load or binding, or a load of the launcher, read through a conditional or logical expression is refused by name at the chain's root, one site for every shape (the walker does not follow which branch the value takes)
  { dir: W, file: "p99-cond-ternary-require.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: [], launches: [], playwright: ["playwright"], refused: "p99-cond-ternary-require.test.ts:2: " + COND_PLAYWRIGHT_REFUSAL }, // const pw = cond ? require("playwright") : null, then pw.firefox.launch() (before round 4: class own, no refusal, engines [] with the Firefox launch unread)
  { dir: W, file: "p100-cond-nullish-require.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: [], launches: [], playwright: ["playwright"], refused: "p100-cond-nullish-require.test.ts:2: " + COND_PLAYWRIGHT_REFUSAL }, // require("playwright") ?? null, WebKit (before: as p99)
  { dir: W, file: "p101-cond-or-require.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: [], launches: [], playwright: ["playwright"], refused: "p101-cond-or-require.test.ts:2: " + COND_PLAYWRIGHT_REFUSAL }, // require("playwright") || null (before: as p99)
  { dir: W, file: "p102-cond-and-require.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: [], launches: [], playwright: ["playwright"], refused: "p102-cond-and-require.test.ts:3: " + COND_PLAYWRIGHT_REFUSAL }, // ok && require("playwright") (before: as p99)
  { dir: W, file: "p103-cond-ternary-destructured.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: [], launches: [], playwright: ["playwright"], refused: "p103-cond-ternary-destructured.test.ts:2: " + COND_PLAYWRIGHT_REFUSAL }, // const { firefox } = cond ? require("playwright") : { firefox: null } (before: as p99)
  { dir: W, file: "p104-cond-chain-root-bound.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: [], launches: [], playwright: ["playwright"], refused: "p104-cond-chain-root-bound.test.ts:2: " + COND_PLAYWRIGHT_REFUSAL }, // const ff = (cond ? require("playwright") : null).firefox: the conditional as a bound chain's root (before: as p99)
  { dir: W, file: "p105-cond-chain-root-unbound.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: [], launches: [], playwright: ["playwright"], refused: "p105-cond-chain-root-unbound.test.ts:2: " + COND_PLAYWRIGHT_REFUSAL }, // (cond ? require("playwright") : null).webkit.launch() where it stands: the unbound chain root (before: as p99)
  { dir: W, file: "p106-cond-playwright-binding.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: [], launches: [], playwright: ["playwright"], refused: "p106-cond-playwright-binding.test.ts:3: " + COND_PLAYWRIGHT_REFUSAL }, // import * as real from "playwright", then const pw = cond ? real : null: a tracked binding through a ternary, no loader call (before: as p99)
  { dir: W, file: "p107-cond-assignment-ternary.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: [], launches: [], playwright: ["playwright"], refused: "p107-cond-assignment-ternary.test.ts:3: " + COND_PLAYWRIGHT_REFUSAL }, // pw = cond ? require("playwright") : null, the assignment arm (before: as p99)
  { dir: W, file: "p108-cond-nested-ternary.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: [], launches: [], playwright: ["playwright"], refused: "p108-cond-nested-ternary.test.ts:2: " + COND_PLAYWRIGHT_REFUSAL }, // a ? (b ? require("playwright") : null) : null, the branches flattened through the nested conditional (before: as p99)
  { dir: W, file: "p109-cond-launcher-ternary-load.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p109-cond-launcher-ternary-load.test.ts:2: " + COND_LAUNCHER_REFUSAL }, // const leg = cond ? require(the launcher) : null, then leg.inBrowser(t, ...): the load refused by name and marked followed, so THE INVARIANT does not refuse it a second time (before: THE INVARIANT's refusal, whose position list the line does not hold)
  { dir: W, file: "p110-cond-launcher-nullish-load.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p110-cond-launcher-nullish-load.test.ts:2: " + COND_LAUNCHER_REFUSAL }, // require(the launcher) ?? null (before: as p109)
  { dir: W, file: "p111-cond-launcher-binding-ternary.test.ts", leg: false, cls: "none", gap: "never calls its inBrowser through that import", launcherImported: true, refused: "p111-cond-launcher-binding-ternary.test.ts:3: the launcher's module binding handed on as a value (" + COND_BINDING_HANDOFF + ")" }, // const leg = cond ? realLeg : null: the launcher binding through a ternary, handedHow naming the form (before: the same hand-on sentence with the fallback parenthetical naming the node kind)
  // correctness-2: a computed member with a name the walker cannot fold on an UNBOUND playwright load is refused as the bound twin (p15a) is, through loadRoot
  { dir: W, file: "p112-computed-unbound-require.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: [], launches: [], playwright: ["playwright"], refused: "p112-computed-unbound-require.test.ts:2: " + COMPUTED_REFUSAL }, // require("playwright")[process.env.ENGINE as string].launch(), never bound (before round 4: class own, no refusal, the engine from the environment and the launch both dropped)
  { dir: W, file: "p113-computed-unbound-await-import.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: [], launches: [], playwright: ["playwright"], refused: "p113-computed-unbound-await-import.test.ts:2: " + COMPUTED_REFUSAL }, // the await import twin (before: as p112)
  { dir: W, file: "p114-computed-unbound-bound-name.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: [], launches: [], playwright: ["playwright"], refused: "p114-computed-unbound-bound-name.test.ts:2: " + COMPUTED_REFUSAL }, // const eng = require("playwright")[process.env.ENGINE as string], the result bound with no launch: bindLoaded's own computed-member arm is unreachable (the peel stops at the access node) and the value falls through to pwChain's arm, which refuses it (before: class own, no refusal)
  // extra6-2: a spread element at or before the engine position of a shared call is refused (the fixed-index read would pass it as no engine), one sentence per call form; a spread after the engine is read as before (p119, the control)
  { dir: W, file: "p115-spread-all.test.ts", leg: true, cls: "shared", gap: null, engines: [], refused: "p115-spread-all.test.ts:3: the shared launcher called with " + SPREAD_TAIL }, // (inBrowser as any)(...run) with run = [t, body, "firefox"] as const (before round 4: class shared, gap null, engines [], no refusal, admitted to the roster as Chromium-only while the spread carries firefox)
  { dir: W, file: "p116-spread-tail-before-engine.test.ts", leg: true, cls: "shared", gap: null, engines: [], refused: "p116-spread-tail-before-engine.test.ts:3: the shared launcher called with " + SPREAD_TAIL }, // (inBrowser as any)(t, ...tail) with tail = [body, "webkit"] as const (before: as p115)
  { dir: W, file: "p117-spread-via-call.test.ts", leg: true, cls: "shared", gap: null, engines: [], refused: "p117-spread-via-call.test.ts:3: the shared launcher called through .call with " + SPREAD_TAIL }, // (inBrowser as any).call(null, t, ...rest) (before: as p115)
  { dir: W, file: "p118-spread-via-apply.test.ts", leg: true, cls: "shared", gap: null, engines: [], refused: "p118-spread-via-apply.test.ts:3: the shared launcher applied to " + SPREAD_TAIL }, // (inBrowser as any).apply(null, [t, ...rest]) (before: as p115)
  { dir: W, file: "p119-spread-after-engine.test.ts", leg: true, cls: "shared", gap: null, engines: ["firefox"], holds: "the no-refusal half of a pair whose partner reds: p115, p116, p117 and p118 (a spread at or before the engine position, refused) red under the census before round 4, which read a spread after the engine as this row does, engines [firefox] with no refusal" }, // (inBrowser as any)(t, body, "firefox", ...extra): the engine is read at its index and the spread after it is no engine argument, green before and after
  // extra6-1's fourth hand-on spelling: requireCjs read off the launcher loaded where it stands, not called
  { dir: W, file: "p120-requirecjs-member-off-load-handed.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p120-requirecjs-member-off-load-handed.test.ts:3: " + REQUIRECJS_LOAD_HANDOFF }, // go(require(the launcher).requireCjs): the member read without a call hands the loader on, refused by name with the load followed (before: read as an import of another export, class none, no refusal, launcherImported true)
  // correctness-1 (round 3): a type-only import or export of a playwright package (`import type`, `export type ... from`, or named
  // bindings every one inline type-only) is erased at build time, binds nothing and is carried by typeOnly, not a load: the module
  // is no leg for it. Rows p121 to p124 red before on leg and class (read as a load of playwright); p125 the control (a default
  // binding beside an inline type stays a load); p126 the same predicate on launcherImported (the inline type-only launcher import
  // read as p16's clause-level form does)
  { dir: W, file: "p121-type-only-shared-leg.test.ts", leg: true, cls: "shared", gap: null, playwright: [], launcherImported: true }, // import type { Browser } from playwright beside a call of inBrowser: a shared leg that passes the gate (before round 4: class both, gap "loads playwright itself")
  { dir: W, file: "p122-type-only-playwright-alone.test.ts", leg: false, cls: "none", gap: null, playwright: [], launcherImported: false }, // import type { chromium } from playwright alone: no leg (before: leg 1, class own)
  { dir: W, file: "p123-type-only-inline.test.ts", leg: false, cls: "none", gap: null, playwright: [], launcherImported: false }, // import { type Page } from playwright, the all-inline form: no leg (before: leg 1, class own, the inline form recorded nowhere but the playwright set)
  { dir: W, file: "p124-type-only-export-from.test.ts", leg: false, cls: "none", gap: null, playwright: [], launcherImported: false }, // export type { Browser } from playwright: no leg (before: leg 1, class own)
  { dir: W, file: "p125-default-and-inline-type.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: ["chromium"], launches: [".launch("], playwright: ["playwright"], holds: "the no-refusal half of a pair whose partner reds: p122, p123 and p124 (a type-only import or export of playwright, no longer a load) red under the census before round 4, which read this row's default binding beside an inline type as a load, as the census does now: class own, engines [chromium], the launch read, no refusal" }, // import pw, { type Page } from playwright, then pw.chromium.launch(): the default binding is a value binding, so the import stays a load, green before and after
  { dir: W, file: "p126-type-only-inline-launcher.test.ts", leg: false, cls: "none", gap: null, launcherImported: false }, // import { type Opened } from the launcher: binds nothing, recorded as type-only, as p16's clause-level form is (before: launcherImported true with the never-calls gap, the asymmetry between the two spellings)
  // correctness-3 (round 3): a launcher module binding CALLED as a function (or constructed) is refused naming that position, not
  // "passed as an argument" (p61 holds the true argument position)
  { dir: W, file: "p127-default-called.test.ts", leg: false, cls: "none", gap: "never calls its inBrowser through that import", launcherImported: true, refused: "p127-default-called.test.ts:3: the launcher's module binding handed on as a value (" + CALLED_HANDOFF + ")" }, // import leg from the launcher, then leg(t, ...) (before: the parenthetical read "passed as an argument")
  { dir: W, file: "p128-namespace-called-cast.test.ts", leg: false, cls: "none", gap: "never calls its inBrowser through that import", launcherImported: true, refused: "p128-namespace-called-cast.test.ts:3: the launcher's module binding handed on as a value (" + CALLED_HANDOFF + ")" }, // import * as leg, then (leg as any)(t, ...): the callee through a cast (before: as p127)
  { dir: W, file: "p129-default-constructed.test.ts", leg: false, cls: "none", gap: "never calls its inBrowser through that import", launcherImported: true, refused: "p129-default-constructed.test.ts:3: the launcher's module binding handed on as a value (" + CONSTRUCTED_HANDOFF + ")" }, // new (leg as any)(t): the constructed form named as constructed, the header's word (before round 4: as p127; before the closing pass: named as called)
  // correctness-4 (round 3): only a playwright or launcher load reaches bindName, so a destructuring of an UNTRACKED loaded module
  // (a package, a local helper) is read by no arm and refuses nothing; a local helper is still read transitively for what it names
  { dir: W, file: "p130-array-destructure-package.test.ts", leg: false, cls: "none", gap: null, launcherImported: false }, // const [a, b] = require of node:os: no leg, no refusal (before round 4: refused as an array destructuring of a loaded module, the whole census stopped)
  { dir: W, file: "p131-nested-destructure-package.test.ts", leg: false, cls: "none", gap: null, launcherImported: false }, // const { constants: { signals } } = require of node:os: an object pattern, which the one-line gate the fixlist proposed would still have handed to bindName (before: refused as a nested destructuring the walker does not follow)
  { dir: W, file: "p132-array-destructure-pw-helper.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p132-array-destructure-pw-helper.test.ts:2: loads ui/webview/pw-helper.ts, which names a playwright package (playwright)" }, // const [h] = require of the helper that loads playwright: the helper's refusal alone, the gate opens no road (before: a second refusal beside it, the array destructuring, so the module carried two refusals and the one-refusal-per-refused-plant count below was red)
  // fresh-2 (round 3): a let or var WRITTEN anywhere in the module is not bound to its initializer, whatever the write's form: a
  // for-of or for-in head over the name, a destructuring assignment holding it at any depth, a second var declaration with an
  // initializer, beside the plain reassignment (p31) and ++ or --; a read of the name inside a literal or as a computed key
  // (p140, p141) is no write
  { dir: W, file: "p133-for-of-rebind.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: [], launches: [], playwright: ["playwright"], refused: "p133-for-of-rebind.test.ts:5: " + COMPUTED_REFUSAL }, // let name = "chromium", for (name of ["firefox"]) {}, then pw[name].launch() (before round 4: folded to the initializer, engines [chromium], no refusal, the Firefox launch read as Chromium)
  { dir: W, file: "p134-for-in-rebind.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: [], launches: [], playwright: ["playwright"], refused: "p134-for-in-rebind.test.ts:5: " + COMPUTED_REFUSAL }, // for (name in { firefox: 1 }) {} (before: as p133)
  { dir: W, file: "p135-array-destructure-assign.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: [], launches: [], playwright: ["playwright"], refused: "p135-array-destructure-assign.test.ts:5: " + COMPUTED_REFUSAL }, // [name] = ["webkit"] (before: as p133)
  { dir: W, file: "p136-nested-array-destructure-assign.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: [], launches: [], playwright: ["playwright"], refused: "p136-nested-array-destructure-assign.test.ts:5: " + COMPUTED_REFUSAL }, // [[name]] = [["webkit"]]: the name one level down, which a predicate over the literal's own elements alone would miss (before: as p133)
  { dir: W, file: "p137-object-destructure-assign.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: [], launches: [], playwright: ["playwright"], refused: "p137-object-destructure-assign.test.ts:5: " + COMPUTED_REFUSAL }, // ({ name } = { name: "webkit" }), the shorthand property as a target (before: as p133)
  { dir: W, file: "p138-var-redeclared.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: [], launches: [], playwright: ["playwright"], refused: "p138-var-redeclared.test.ts:5: " + COMPUTED_REFUSAL }, // var name = "chromium", then var name = "firefox": a second declaration of the same var with an initializer, no assignment expression at all (before: as p133)
  { dir: W, file: "p139-for-of-rebind-engine-shared.test.ts", leg: true, cls: "shared", gap: null, engines: [], refused: "p139-for-of-rebind-engine-shared.test.ts:5: an engine argument to the shared launcher the walker cannot fold" }, // let engine = "chromium", for (engine of ["firefox"]) {}, inBrowser(t, body, engine): the same fold feeds the engine read, so the roster gate saw a Chromium leg (before: engines [chromium], gap null, no refusal, rosterable while it reaches Firefox at run time)
  { dir: W, file: "p140-read-in-literal-control.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: ["chromium"], launches: [".launch("], playwright: ["playwright"], strictRefused: true, holds: "the no-refusal half of a pair whose partner reds: p133 to p138 (a write to the name in a for-of or for-in head, a destructuring assignment or a second var declaration) red under the census before round 4, which folded this row's read of the name inside an object literal as the census does now: engines [chromium], no refusal" }, // const seen = { name }: a shorthand property in a literal that is no assignment target is a read, green before and after
  { dir: W, file: "p141-computed-key-write-control.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: ["chromium"], launches: [".launch("], playwright: ["playwright"], strictRefused: true, holds: "the no-refusal half of a pair whose partner reds: p133 to p138 (a write to the name) red under the census before round 4, which read this row's o[name] = 1 as a write to o, not to the name, as the census does now: engines [chromium], no refusal (a predicate over every reference inside the target would refuse it)" }, // o[name] = 1: the name as a computed key of the target is a read of it, green before and after
  // the author's closing pass after round 4's verification: two residuals its verifiers found by probe, each red under the census
  // before round 4 and under the round-4 module before the pass (the class rule's left operand, the write predicate's var head)
  { dir: W, file: "p142-logical-left-nullish-namespace.test.ts", leg: false, cls: "none", gap: "never calls its inBrowser through that import", launcherImported: true, refused: "p142-logical-left-nullish-namespace.test.ts:3: the launcher's module binding handed on as a value (" + COND_BINDING_HANDOFF + ")" }, // (leg ?? null).inBrowser(t, ...): the namespace binding as the LEFT operand of ??, which the value-use arm exempted as an assignment's target (before: class none, launcherImported, no refusal, the gap saying the module never calls inBrowser)
  { dir: W, file: "p143-logical-left-or-default-cast.test.ts", leg: false, cls: "none", gap: "never calls its inBrowser through that import", launcherImported: true, refused: "p143-logical-left-or-default-cast.test.ts:3: the launcher's module binding handed on as a value (" + COND_BINDING_HANDOFF + ")" }, // ((leg || null) as any).inBrowser(t, ...): the default binding as the left operand of || (before: as p142)
  { dir: W, file: "p144-logical-left-and-bound.test.ts", leg: false, cls: "none", gap: "never calls its inBrowser through that import", launcherImported: true, refused: "p144-logical-left-and-bound.test.ts:3: the launcher's module binding handed on as a value (" + COND_BINDING_HANDOFF + ")" }, // const l = leg && other, then l.inBrowser(t, ...): the left operand of && at a binding's initializer (before: as p142)
  { dir: W, file: "p145-logical-left-nullish-bound.test.ts", leg: false, cls: "none", gap: "never calls its inBrowser through that import", launcherImported: true, refused: "p145-logical-left-nullish-bound.test.ts:3: the launcher's module binding handed on as a value (" + COND_BINDING_HANDOFF + ")" }, // const l = leg ?? null, then l.inBrowser(t, ...) (before: as p142)
  { dir: W, file: "p146-logical-left-inbrowser-binding.test.ts", leg: false, cls: "none", gap: "never calls its inBrowser through that import", launcherImported: true, refused: "p146-logical-left-inbrowser-binding.test.ts:3: " + INBROWSER_VALUE_REFUSAL }, // (inBrowser ?? null)(t, ...): the named binding as the left operand, a value use (before: class none, no refusal)
  { dir: W, file: "p147-logical-left-nullish-engine.test.ts", leg: false, cls: "none", gap: "never calls its inBrowser through that import", launcherImported: true, engines: [], refused: "p147-logical-left-nullish-engine.test.ts:3: the launcher's module binding handed on as a value (" + COND_BINDING_HANDOFF + ")" }, // (leg ?? null).inBrowser(t, body, "firefox"): the class rule's stated consequence, a Firefox shared leg with every gate green (before: class none, engines [], no refusal)
  { dir: W, file: "p148-logical-left-requirecjs.test.ts", leg: false, cls: "none", gap: "never calls its inBrowser through that import", launcherImported: true, refused: "p148-logical-left-requirecjs.test.ts:3: " + REQUIRECJS_ALIAS_REFUSAL }, // const r = requireCjs ?? null, then r("playwright").firefox.launch(): the loader binding as the left operand, the same exemption in the requireCjs arm (before: class none, no refusal, the Firefox launch unread)
  { dir: W, file: "p149-comparison-left-operand.test.ts", leg: true, cls: "shared", gap: null, refused: "p149-comparison-left-operand.test.ts:3: the launcher's module binding handed on as a value (" + OPERAND_HANDOFF + ")" }, // const ok = leg !== null, beside a counted call: the left operand of a comparison, a value use no exempt position names, refused with the operator (before: no refusal, the comparison exempt as an assignment's target)
  { dir: W, file: "p150-comparison-right-operand.test.ts", leg: true, cls: "shared", gap: null, refused: "p150-comparison-right-operand.test.ts:3: the launcher's module binding handed on as a value (" + OPERAND_HANDOFF + ")" }, // const ok = null !== leg: the right operand of a comparison, named with its operator (before: refused, the parenthetical misnaming it "aliased by an assignment")
  { dir: W, file: "p151-for-of-var-rebind.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: [], launches: [], playwright: ["playwright"], refused: "p151-for-of-var-rebind.test.ts:5: " + COMPUTED_REFUSAL }, // var name = "chromium", for (var name of ["firefox"]) {}, then pw[name].launch(): the head redeclares the var, a write the predicate's for-head clause skipped (before: folded to the initializer, engines [chromium], no refusal, the Firefox launch read as Chromium)
  { dir: W, file: "p152-for-in-var-rebind.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: [], launches: [], playwright: ["playwright"], refused: "p152-for-in-var-rebind.test.ts:5: " + COMPUTED_REFUSAL }, // for (var name in { firefox: 1 }) {} (before: as p151)
  { dir: W, file: "p153-for-of-var-pattern-rebind.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: [], launches: [], playwright: ["playwright"], refused: "p153-for-of-var-pattern-rebind.test.ts:5: " + COMPUTED_REFUSAL }, // for (var [name] of [["firefox"]]) {}: the name inside the head's binding pattern (before: as p151)
  { dir: W, file: "p154-for-of-var-rebind-engine-shared.test.ts", leg: true, cls: "shared", gap: null, engines: [], refused: "p154-for-of-var-rebind-engine-shared.test.ts:5: an engine argument to the shared launcher the walker cannot fold" }, // var engine = "chromium", for (var engine of ["firefox"]) {}, inBrowser(t, body, engine): the same fold feeds the engine read (before: engines [chromium], gap null, no refusal, rosterable while it reaches Firefox at run time)
  { dir: W, file: "p155-for-of-let-head-control.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: ["chromium"], launches: [".launch("], playwright: ["playwright"], strictRefused: true, holds: "the no-refusal half of a pair whose partner reds: p151 to p154 (a var redeclared by a for-of or for-in head, a write) red under the census before round 4, which read this row's let head as a declaration of its own scope and no write to the module's var, as the census does now: engines [chromium], no refusal" }, // var name = "chromium", for (let name of ["firefox"]) {}: the let is the for head's own declaration, the module's name folds to its initializer, green before and after
  // THE SAFETY NET (round 5): the eleven silent forms the round-4 review named (a re-exported requireCjs loader, a known loader handed
  // on as a value or module.require, a createRequire result bound anywhere but a declaration initializer or reached through an alias,
  // an aliased or a parameter loader, a playwright binding handed on, a compound-assignment binding, a launcher binding rebound to a
  // playwright load, a driver string the regex reader cannot match) and the tagged-template loader the round's verifiers found, each
  // planted with the net's refusal as its outcome: the first clause (no reach, no refusal) for a class-none form, the second for a
  // reaching module whose mention the reach does not account for, the read-through clause for a recorded load with no engine and no
  // launch. Every row was class none, or shared with gap null, or own with engines [] and launches [], with no refusal, under the
  // census before round 5. A fold that reads a form re-aims its rows to the fold's sentence or class and accounts for the mention by
  // construction (each row's comment says what the net alone gave, the fact the round's records hold under the net-only module); a
  // companion barrel's own refusal reaches the importer through localRefusals' arms, once. The relative node_modules form (n09) is
  // planted under tests/fixtures/browser-legs-plants/relative-node-modules and run over a synthetic root by its own test below, since
  // its path resolves only beside a node_modules the fixtures cannot carry.
  { dir: W, file: "p156-n01a-reexport-named.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p156-n01a-reexport-named.test.ts:2: " + LOADER_REEXPORT("ui/webview/rcjs-barrel.ts") }, // n01a (extra5-1): import { requireCjs } from a barrel that re-exports it from the launcher, then requireCjs("playwright").firefox.launch(): the barrel carries loaderReexport and localRefusals refuses the importer on that flag alone (before round 5: class none, no refusal, the Firefox launch unread; under the net alone: the barrel's own clause-1 refusal on its export specifier, carried)
  { dir: W, file: "p157-n01b-reexport-renamed.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p157-n01b-reexport-renamed.test.ts:2: " + LOADER_REEXPORT("ui/webview/rcjs-barrel-renamed.ts") }, // n01b: export { requireCjs as load } from the launcher, then load("playwright").webkit.launch(): the renamed re-export sets the flag through the specifier's propertyName (before: class none, no refusal; net alone: the barrel's refusal, carried)
  { dir: W, file: "p158-n01c-reexport-star-chain.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p158-n01c-reexport-star-chain.test.ts:2: " + LOADER_REEXPORT("ui/webview/rcjs-barrel-star.ts, which loads ui/webview/rcjs-barrel.ts") }, // n01c: export * over the requireCjs barrel, the chain two modules long, the flag on the launcher-facing barrel the queue reaches (before: class none, no refusal; net alone: the inner barrel's refusal, carried)
  { dir: W, file: "p159-n01d-reexport-star-as.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p159-n01d-reexport-star-as.test.ts:2: " + LOADER_REEXPORT("ui/webview/rcjs-barrel-star-as.ts, which loads ui/webview/rcjs-barrel.ts") }, // n01d: export * as ns over the barrel, then ns.requireCjs("playwright") (before: class none, no refusal; net alone: the inner barrel's refusal, carried)
  { dir: W, file: "p160-n01e-reexport-both-calls.test.ts", leg: true, cls: "shared", gap: null, launcherImported: true, refused: "p160-n01e-reexport-both-calls.test.ts:3: " + LOADER_REEXPORT("ui/webview/rcjs-barrel.ts") }, // n01e: inBrowser from the launcher AND requireCjs from the barrel, the Firefox launch inside inBrowser: the flag is read with NO gate on the importer's shared calls, which is why it is a flag of its own and not launcherBinds (before round 5: class shared, gap null, rosterable with the Firefox launch unread; net alone: the barrel's refusal, carried)
  { dir: W, file: "p161-n01f-launcher-star-both-calls.test.ts", leg: true, cls: "shared", gap: null, launcherImported: true, refused: "p161-n01f-launcher-star-both-calls.test.ts:3: " + LOADER_REEXPORT("ui/webview/launcher-star-barrel.ts") }, // n01f: inBrowser direct AND b.requireCjs("playwright") through a barrel that is export * from the launcher: export * sets the flag too (before: class shared, gap null, the WebKit launch unread; net alone: the second clause on this module's own line 4, the shared call not accounting for the requireCjs member off a local binding nor the package name)
  { dir: W, file: "p162-n02a-require-alias.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p162-n02a-require-alias.test.ts:2: " + LOADER_HANDOFF("require", HOW_ALIASED) }, // n02a (extra5-2, extra7-1): const r = require, then r("playwright").webkit.launch(): the global loader handed on by a declaration, the twin of the requireCjs value-use arm keyed on the loaders set (before round 5: class none, no refusal; net alone: the package name as the argument of a call the walker knows no loader for, at line 3)
  { dir: W, file: "p163-n02b-require-call.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p163-n02b-require-call.test.ts:2: " + LOADER_HANDOFF("require", HOW_MEMBER("call")) }, // n02b: (require as any).call(null, "playwright").firefox.launch(): the object of .call is not an exempt member position, since .call makes the load where the walker does not follow (before: class none, no refusal; net alone: the package name in .call's argument)
  { dir: W, file: "p164-n02c-module-require.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: ["firefox"], launches: [".launch("], playwright: ["playwright"] }, // n02c: module.require("playwright").firefox.launch(): CommonJS's loader off the module object joins loaderCall's callees, so the load, the engine and the launch are read, no refusal (before round 5: class none, no refusal; net alone: module.require, a callee the walker did not know, then the package name)
  { dir: W, file: "p165-n02d-require-alias-launcher.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p165-n02d-require-alias-launcher.test.ts:2: " + LOADER_HANDOFF("require", HOW_ALIASED) }, // n02d: const r = require, const leg = r(the launcher), leg.inBrowser(t, ...): the hand-on is refused at the alias, and the launcher load through it stays unread (launcherImported false) (before: class none, launcherImported false, no refusal; net alone: the launcher's name as the argument of a call the walker knows no loader for, at line 3)
  { dir: W, file: "p166-n02e-require-bind.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p166-n02e-require-bind.test.ts:2: " + LOADER_HANDOFF("require", HOW_MEMBER("bind")) }, // n02e: const r = require.bind(null), then r("playwright"): .bind binds a loader where the walker does not follow, not an exempt member read (before: class none, no refusal; net alone: the package name at line 3)
  { dir: W, file: "p167-n03a-createrequire-argument.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p167-n03a-createrequire-argument.test.ts:4: " + CREATEREQUIRE_HANDOFF(HOW_ARGUMENT) }, // n03a (extra7-1): loadPw(createRequire(__filename)) where loadPw returns r("playwright"): the loader made where it stands and passed on, refused at the call (before: class none, no refusal; net alone: the package name inside loadPw at line 3, the createRequire value at line 4)
  { dir: W, file: "p168-n03b-createrequire-assigned.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p168-n03b-createrequire-assigned.test.ts:4: " + CREATEREQUIRE_HANDOFF(HOW_ASSIGNED) }, // n03b (extra5-2): let req, then req = createRequire(__filename): an assignment's right side is not the declaration initializer walk1 binds a loader from, so the call is refused where it stands (before: class none, no refusal; net alone: createRequire in an unfolded position at line 4)
  { dir: W, file: "p169-n03c-createrequire-in-object.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p169-n03c-createrequire-in-object.test.ts:3: " + CREATEREQUIRE_HANDOFF(HOW_LITERAL) }, // n03c: { req: createRequire(__filename) }.req("playwright"): the loader held in an object literal (before: class none, no refusal; net alone: createRequire at line 3)
  { dir: W, file: "p170-n03d-createrequire-import-alias.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: ["firefox"], launches: [".launch("], playwright: ["playwright"] }, // n03d: import { createRequire as cr }, const req = cr(__filename), req("playwright").firefox.launch(): the alias resolved through its import binding (isCreateRequireId), so req joins the loaders and the load, the engine and the launch are read, no refusal (before round 5: class none, no refusal; net alone: the alias cr in an unfolded position at line 3, then the package name)
  { dir: W, file: "p171-n03e-createrequire-alias-launcher.test.ts", leg: true, cls: "shared", gap: null, launcherImported: true }, // n03e: cr(__filename)(the launcher).inBrowser(t, ...): the alias applied directly is a loader callee through isCreateRequireCall, so the launcher load is bound and the call counted, a rosterable shared leg (before: class none, launcherImported false, no refusal; net alone: cr at line 3, then the launcher's name)
  { dir: W, file: "p172-n04-loader-aliased.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p172-n04-loader-aliased.test.ts:4: " + LOADER_HANDOFF("req", HOW_ALIASED) }, // n04 (extra7-1): const req = createRequire(__filename), const load = req, load("playwright"): the createRequire-bound loader handed on by a declaration, refused at the alias (before: class none, no refusal; net alone: the package name at line 5)
  { dir: W, file: "p173-n05-loader-parameter.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p173-n05-loader-parameter.test.ts:5: " + LOADER_HANDOFF("req", HOW_ARGUMENT) }, // n05: loadPw(req) where loadPw returns r("playwright"): the loader passed as an argument, refused at the call site (the parameter r inside loadPw is its own binding, not the loader) (before: class none, no refusal; net alone: the package name at line 4)
  { dir: W, file: "p174-n06a-pw-argument.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: [], launches: [], playwright: ["playwright"], refused: "p174-n06a-pw-argument.test.ts:4: " + PW_HANDOFF("pw", HOW_ARGUMENT) }, // n06a (correctness-2): const pw = require("playwright"), then go(pw) where go launches p.firefox: the binding passed as an argument, refused at the call with the position named (before round 5: class own, engines [], launches [], no refusal, the exclusions engine form unavailable; net alone: the read-through clause at the load's line 2)
  { dir: W, file: "p175-n06b-pw-object-literal.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: [], launches: [], playwright: ["playwright"], refused: "p175-n06b-pw-object-literal.test.ts:3: " + PW_HANDOFF("pw", HOW_LITERAL) }, // n06b: const bag = { pw }, then bag.pw.webkit.launch(): the shorthand property is a value position, not a name (before: as p174; net alone: the read-through clause)
  { dir: W, file: "p176-n06c-pw-returned.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: [], launches: [], playwright: ["playwright"], refused: "p176-n06c-pw-returned.test.ts:3: " + PW_HANDOFF("pw", HOW_RETURNED) }, // n06c: function get() { return pw }, then get().firefox.launch() (before: as p174; net alone: the read-through clause)
  { dir: W, file: "p177-n06d-derived-handed.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: ["firefox"], launches: [], playwright: ["playwright"], refused: "p177-n06d-derived-handed.test.ts:5: " + PW_HANDOFF("firefox", HOW_ARGUMENT) }, // n06d (tests-2, correctness-2): const { firefox } = pw, then go(firefox): bindLoaded's derived arm notes each destructured element's own chain, so the engine is read at the destructuring (engines [firefox], where the base chain alone read none), and the derived name passed as an argument is refused as a playwright binding handed on (before: class own, engines [], launches [], no refusal; net alone: the read-through clause)
  { dir: W, file: "p178-n06e-pw-helper-argument.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: [], launches: [], playwright: ["playwright"], refused: "p178-n06e-pw-helper-argument.test.ts:4: " + PW_HANDOFF("pw", HOW_ARGUMENT) }, // n06e: launchWith(pw) into a companion (pw-launch-helper.ts) that launches p.webkit and names no package: refused at the argument in this module (the helper is class none and carries no refusal) (before: as p174; net alone: the read-through clause at line 3)
  { dir: W, file: "p179-n07a-nullish-assign-require.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: [], launches: [], playwright: ["playwright"], refused: "p179-n07a-nullish-assign-require.test.ts:3: " + COMPOUND_PLAYWRIGHT }, // n07a (extra8-1, extra5-4): let pw, then pw ??= require("playwright") at module level, pw.firefox.launch(): walk2 reads every assignment operator, binds under = alone and refuses a compound operator with a playwright load on its right by name (before round 5: class own, engines [], launches [], no refusal; net alone: the read-through clause at line 3)
  { dir: W, file: "p180-n07b-or-assign-require.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: [], launches: [], playwright: ["playwright"], refused: "p180-n07b-or-assign-require.test.ts:3: " + COMPOUND_PLAYWRIGHT }, // n07b: pw ||= require("playwright") inside the test body, WebKit: walk2 walks every node, so the position inside a function changes nothing (before: as p179; net alone: the read-through clause)
  { dir: W, file: "p181-n07c-and-assign-await-import.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: [], launches: [], playwright: ["playwright"], refused: "p181-n07c-and-assign-await-import.test.ts:3: " + COMPOUND_PLAYWRIGHT }, // n07c: pw &&= await import("playwright") inside the test, Firefox: the await unwrapped, the dynamic import a loader call (before: as p179; net alone: the read-through clause)
  { dir: W, file: "p182-n08c-launcher-rebound-to-playwright.test.ts", leg: true, cls: "own", gap: "never calls its inBrowser through that import", launcherImported: true, engines: [], launches: [], playwright: ["playwright"], refused: "p182-n08c-launcher-rebound-to-playwright.test.ts:3: " + WRITE_REFUSAL("launcher", "leg", WHAT_PW_LOAD) }, // n08c (tests-1): let leg = require(the launcher), then leg = require("playwright"), leg.firefox.launch(): the write-time refusal, the binding kept as the launcher's and written with a load of the OTHER kind, so the Firefox launch through the name is unread (before round 5: class own, engines [], launches [], launcherImported true, no refusal; net alone: the read-through clause at line 3)
  { dir: W, file: "p183-n10a-driver-createrequire-applied.test.ts", leg: true, cls: "embedded", gap: "drives playwright from a child process whose source is held in a string (line 2)" }, // n10a (correctness-3): a driver string applying createRequire(...)("playwright"), which the regex reader (require( or import( or from before the name) cannot match: the walker now reads the text as code with its own loader walk, so the string is embedded (before round 5: class none, embedded [], no refusal; net alone: the specifier inside the string's text read as code, at line 2)
  { dir: W, file: "p184-n10b-driver-subpath.test.ts", leg: true, cls: "embedded", gap: "drives playwright from a child process whose source is held in a string (line 2)" }, // n10b: require("playwright/test") in the text, a subpath the regex's closing quote excludes and isPwPackage reads (before: class none, no refusal; net alone: the subpath inside the text)
  { dir: W, file: "p185-n10c-driver-bound-loader.test.ts", leg: true, cls: "embedded", gap: "drives playwright from a child process whose source is held in a string (line 2)" }, // n10c: const req = createRequire(import.meta.url), req("playwright") in the text: the bound loader read by the same walk1 rule the module's own code is (before: class none, no refusal; net alone: the specifier inside the text)
  { dir: W, file: "p186-n12-tagged-template-loader.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p186-n12-tagged-template-loader.test.ts:2: " + NET_HEAD + NET_PW + NET_NO_REACH }, // n12 (the round-5 verifiers' twelfth form): require`playwright`.firefox.launch(), a tagged template the walker reads as no call: the template's text is a specifier-capable position to the net, no fold reads the form, and the net's refusal is its outcome (before round 5: class none, no refusal)
  // net-only rows (round 5's folds): one row per KIND of mention the net names whose planted forms the folds now read, so every arm of
  // the net keeps a plant that reds when it is silenced; each is a form no fold reads, and each is a stated false refusal of the p74
  // class (the walker reaches no browser through it) or a silent form the round's rulings fold nowhere
  { dir: W, file: "p187-n02f-module-require-handed.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p187-n02f-module-require-handed.test.ts:2: " + NET_HEAD + NET_MODREQ + MORE(1) + NET_NO_REACH }, // n02f: const r = module.require, then r("playwright"): module.require is a loader callee when called (p164) and handed on here, which no fold reads (the loaders twin keys on identifiers); the net names it first, the package second (before round 5: class none, no refusal)
  { dir: W, file: "p188-n03f-createrequire-identifier-aliased.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p188-n03f-createrequire-identifier-aliased.test.ts:3: " + NET_HEAD + NET_CR("createRequire") + MORE(1) + NET_NO_REACH }, // n03f: const make = createRequire, const req = make(__filename), req("playwright"): the createRequire IDENTIFIER handed on uncalled (the fold refuses the CALL in an unfolded position, p167 to p169), which the net alone reads (before: class none, no refusal)
  { dir: W, file: "p189-n02g-launcher-name-unknown-callee.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p189-n02g-launcher-name-unknown-callee.test.ts:3: " + NET_HEAD + NET_LAUNCHER + NET_NO_REACH }, // n02g: import { load } from a companion (plain-loader-helper.ts) whose load returns its argument, then load(the launcher).inBrowser(t, ...): the launcher's name as the argument of a call the walker knows no loader for, the p74 class with the launcher's name (before: class none, launcherImported false, no refusal)
  { dir: W, file: "p190-n01g-requirecjs-lookalike.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p190-n01g-requirecjs-lookalike.test.ts:2: " + VIA_COMPANION("ui/webview/rcjs-lookalike.ts", "ui/webview/rcjs-lookalike.ts", NET_RCJS) }, // n01g: import { requireCjs } from a companion (rcjs-lookalike.ts) that exports a function of that name and never touches the launcher, then requireCjs("playwright"): the companion's own function name is a mention of the loader resolved to no launcher binding (the net exempts no name position for requireCjs), so its clause-1 refusal reaches the importer through the cannot-classify arm, first (before: class none, no refusal)
  { dir: W, file: "p191-n13-shared-call-beside-package-argument.test.ts", leg: true, cls: "shared", gap: null, launcherImported: true, refused: "p191-n13-shared-call-beside-package-argument.test.ts:4: " + NET_HEAD + NET_PW + NET_REACH }, // n13: inBrowser(t, ...) counted, beside pick("playwright") where pick returns its argument: THE SAFETY NET's second clause, a reach (the shared call) that does not account for the package name in a call's argument, the p74 class on a reaching module (before round 5: class shared, gap null, no refusal)
  // tests-1 with extra8-1 (round 5): a tracked launcher or playwright binding WRITTEN with a value the walker does not follow is
  // refused at the write, in one home (walk2's assignment arm over isAssignmentOp), whatever the operator; null, undefined, a loader
  // call of the same kind and a chain the walker read are exempt, so the tree's let-null-try idiom (p197, p198) stays green
  { dir: W, file: "p192-n07d-launcher-nullish-assign.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p192-n07d-launcher-nullish-assign.test.ts:3: " + COMPOUND_LAUNCHER }, // n07d (extra8-1, extra5-4): let leg, then leg ??= require(the launcher), leg.inBrowser(t, ...): the launcher twin of p179, refused by name at the compound assignment and marked followed, so THE INVARIANT does not refuse it a second time (before round 5: refused by THE INVARIANT's clause 2 with its position list, a sentence the line does not hold; the row moves to the by-name sentence, so it reds under that census on the sentence)
  { dir: W, file: "p193-n08a-let-launcher-rebound.test.ts", leg: true, cls: "shared", gap: null, launcherImported: true, refused: "p193-n08a-let-launcher-rebound.test.ts:3: " + WRITE_REFUSAL("launcher", "leg", WHAT_NO_LOAD) }, // n08a (tests-1): let leg = require(the launcher), then leg = { inBrowser: stub }, leg.inBrowser(t, ...): the binding stays the launcher's, so the call through the stub counts as a shared call and the roster gate would pass the leg while the switch is never read; refused at the write (before round 5: class shared, gap null, rosterable, no refusal, red under no net arm: the write shape the null-try control shares, so this row is fold-only)
  { dir: W, file: "p194-n08b-destructured-let-rebound.test.ts", leg: true, cls: "shared", gap: null, launcherImported: true, refused: "p194-n08b-destructured-let-rebound.test.ts:3: " + WRITE_REFUSAL("launcher", "inBrowser", WHAT_NO_LOAD) }, // n08b: let { inBrowser } = require(the launcher), then inBrowser = stub: the destructured element's name resolves by scope to its binding element, the write refused there (before: as p193, fold-only)
  { dir: W, file: "p195-n08d-and-assign-launcher-stub.test.ts", leg: true, cls: "shared", gap: null, launcherImported: true, refused: "p195-n08d-and-assign-launcher-stub.test.ts:3: " + WRITE_REFUSAL("launcher", "leg", WHAT_NO_LOAD) }, // n08d: leg &&= { inBrowser: stub }: a compound operator whose right side is no load reaches the write-time arm, not the compound-load one (before: as p193, fold-only)
  { dir: W, file: "p196-n08e-write-in-function-before-bind.test.ts", leg: true, cls: "shared", gap: null, launcherImported: true, refused: "p196-n08e-write-in-function-before-bind.test.ts:2: " + WRITE_REFUSAL("launcher", "leg", WHAT_NO_LOAD) }, // n08e: function reset() { leg = { inBrowser: stub } } declared ABOVE let leg = require(the launcher): the write is visited before the declaration binds the name and refused on the fixpoint's next pass, which is why the arm sits inside the loop (before: as p193, fold-only)
  { dir: W, file: "p197-n08z-null-try-launcher-control.test.ts", leg: true, cls: "shared", gap: null, launcherImported: true, holds: "the no-refusal half of a pair whose partner reds: p193 to p196 (a launcher binding written with a value the walker does not follow) red under the census before round 5, which read this row's null writes and same-kind load as the census does now: class shared, gap null, no refusal" }, // n08z: let leg = null, try { leg = require(the launcher) } catch { leg = null }: the tree's own idiom, null and the same-kind load exempt, green before and after
  { dir: W, file: "p198-n06z-pw-guard-control.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: ["firefox"], launches: [".launch("], playwright: ["playwright"], holds: "the no-refusal half of a pair whose partner reds: p174 to p178 (a playwright binding handed on as a value) red under the census before round 5, which read this row's guards (!pw, pw !== null, typeof pw) as value tests, as the census does now: class own, engines [firefox], the launch read, no refusal" }, // n06z: let pw = null, try { pw = require("playwright") } catch { pw = null }, then if (!pw || (pw !== null && typeof pw !== "object")) return, pw.firefox.launch(): the tree's guard idiom (116 !pw guards and one pw !== null at the round-4 head), every test position exempt for playwright, green before and after
  // correctness-3 (round 5): a driver text the walker's own read loads nothing from, while the net's wider read of the same text sees
  // the package name in a call's argument: the net's refusal, the string boundary stated in the census header's embedded clause
  { dir: W, file: "p199-n10d-driver-wrapped-loader.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p199-n10d-driver-wrapped-loader.test.ts:2: " + NET_HEAD + NET_DRIVER + "\"playwright\"" + NET_NO_REACH }, // n10d: a driver text whose loader is a wrapper, function load(s) { return require(s) }, then load("playwright"): the walker's read of the text folds no load (require's specifier is a parameter, refused inside the text's own record, which is not read), so the string is no driver to it, and the net refuses the module on the specifier in the text (before round 5: class none, no refusal, the regex matching nothing)
  // extra7-3 (round 5): a computed member on a playwright load or binding in CALLEE position is refused through pwChain, the one home
  // of the computed-member refusal; these rows are pins of an arm no plant carried (refused at the round-4 head already, by the call
  // arm's own copy of the refusal, which the reroute removed), so they hold rather than red: with pwChain's refusal deleted, p15a,
  // p31, p64, p65, p112 to p114, p133 to p138, p151 to p153 and these three red together (the round's records), where under the
  // two-homes module these three and p65 kept the callee copy's refusal
  { dir: W, file: "p200-n11a-callee-computed-require.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: [], launches: [], playwright: ["playwright"], refused: "p200-n11a-callee-computed-require.test.ts:2: " + COMPUTED_REFUSAL, holds: "a pin of an arm no plant carried: the computed member on a playwright load in callee position (the load of the package where it stands, indexed by a name from the environment and called), refused at the round-4 head by the call arm's own copy of the computed-member refusal and since round 5 through pwChain alone; no earlier row held the callee position of a playwright load, so this row is green under the census before round 5 and pins the one home" }, // n11a: the playwright-callee twin of p65
  { dir: W, file: "p201-n11b-callee-computed-binding.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: [], launches: [], playwright: ["playwright"], refused: "p201-n11b-callee-computed-binding.test.ts:4: " + COMPUTED_REFUSAL, holds: "a pin of an arm no plant carried: the computed member on a playwright BINDING in callee position, pw[k]() with k bound to a value from the environment, refused at the round-4 head by the call arm's copy and since round 5 through pwChain alone; green under the census before round 5, a pin of the one home" }, // n11b: import pw from playwright, const k = process.env.K, pw[k]()
  { dir: W, file: "p202-n11c-callee-computed-await-import.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: [], launches: [], playwright: ["playwright"], refused: "p202-n11c-callee-computed-await-import.test.ts:2: " + COMPUTED_REFUSAL, holds: "a pin of an arm no plant carried: the computed member on an awaited dynamic import of playwright in callee position (the awaited import indexed by a name from the environment and called), refused at the round-4 head by the call arm's copy and since round 5 through pwChain alone; green under the census before round 5, a pin of the one home" }, // n11c: the await import twin
  // correctness-1 (round 5): a string-typed parameter passed back to its own function's call, directly or through another function,
  // re-entered foldIdentifier's parameter arm without bound, and the census over ANY tree holding such a module died with a bare
  // RangeError (exit 1, zero rows, no file, no line: a silent pass for every module of the tree). The fold now keeps the parameter
  // declarations whose call-site fold is in progress and returns null on re-entry, so the caller's refusal names the line. The red
  // before round 5 for p203 to p206 is NOT a row mismatch: with any one of them in the fixtures, census(PLANTS) under the census
  // before round 5 throws before judging a single row (the round's records: exit 1, stdout empty, stderr the bare message), so every
  // plant test of this file is red under it, not these rows alone. p207 is the non-cyclic control, whose fold is keyed on the
  // declaration and still reads the literal through two calls. The other half of correctness-1, a module whose classification throws
  // for any other reason (a read error, an overflow the guard does not cover), is refused by name at census()'s and own()'s catches
  // and is executed over a synthetic root by its own test below (a directory named like a test module, a generated nesting), since a
  // directory cannot sensibly live under the fixtures and an overflow's threshold is the stack's
  { dir: W, file: "p203-qc1a-self-call-computed.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: [], launches: [], playwright: ["playwright"], refused: "p203-qc1a-self-call-computed.test.ts:3: " + COMPUTED_REFUSAL }, // qc1a: async function go(engine: string, again: boolean) { if (again) return go(engine, false); pw[engine].launch() }, go("chromium", true): the self call passes engine back, the re-entered fold returns null, the computed member is refused (before round 5: the census whole threw, unnamed)
  { dir: W, file: "p204-qc1b-self-call-inbrowser.test.ts", leg: true, cls: "shared", gap: null, engines: [], refused: "p204-qc1b-self-call-inbrowser.test.ts:3: an engine argument to the shared launcher the walker cannot fold" }, // qc1b: the inBrowser twin, go(t, engine, false) inside go and inBrowser(t, body, engine as any): the engine argument's fold returns null on re-entry and the engine refusal names the line, as p78's does (before: the census whole threw)
  { dir: W, file: "p205-qc1c-mutual-recursion.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: [], launches: [], playwright: ["playwright"], refused: "p205-qc1c-mutual-recursion.test.ts:4: " + COMPUTED_REFUSAL }, // qc1c: a(e) calls b(e), b(e) calls a(e) and reads pw[e]: the fold of b's e reaches a's e, which reaches b's e again, the re-entry keyed on b's declaration, refused at the computed member (before: the census whole threw)
  { dir: W, file: "p206-qc1d-p28-plus-self-call.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: [], launches: [], playwright: ["playwright"], refused: "p206-qc1d-p28-plus-self-call.test.ts:3: " + COMPUTED_REFUSAL }, // qc1d: p28's inEngine(t, name, retry = 1) with a retry call inEngine(t, name, retry - 1) inside it: the two literal call sites no longer fold, since the third passes name back (before: the census whole threw; p28 itself, with no self call, still folds to chromium and webkit)
  { dir: W, file: "p207-qc1e-two-level-chain-control.test.ts", leg: true, cls: "shared", gap: null, engines: ["firefox"], holds: "the no-refusal half of a pair whose partner reds: p203 to p206 (a string-typed parameter passed back to its own function, which ended the census before round 5 whole and unnamed, so those rows red as census(PLANTS) throwing, not as a row mismatch) beside this non-cyclic chain, outer(t, e) to go(t, e) to inBrowser(t, body, e), which the census before round 5 folded to firefox in a root of its own as the census does now: class shared, gap null, engines [firefox], no refusal (the guard is keyed on the parameter's declaration, not a flag, so a fold through another function's parameter is no re-entry)" }, // qc1e: the control
];
const bundleOf = (p: Plant): string => "out-tests/" + p.dir + "/" + p.file.replace(/\.test\.ts$/, ".test.js");

/** The census's population against esbuild's test build: `built` is bundle -> entry point from a metafile build of the
 *  config's own entry points (the mapping is esbuild's, by its outbase, never restated here), `read` the bundles census() read.
 *  Each direction is a sentence naming the modules and the directories they fall in (derived from the bundle paths), or null. */
function scopeDiff(built: Map<string, string>, read: Set<string>): { builtNotRead: string | null; readNotBuilt: string | null } {
  const dirs = (bs: string[]) => [...new Set(bs.map((b) => path.dirname(b.replace(/^out-tests\//, ""))))].sort();
  const bnr = [...built.keys()].filter((b) => !read.has(b)).sort();
  const rnb = [...read].filter((b) => !built.has(b)).sort();
  return {
    builtNotRead: bnr.length ? "esbuild.js testBuild compiles these modules and the census never reads them, so a browser leg among them is in neither file with every check green: add their directories (" + dirs(bnr).join(", ") + ", relative to the repo root) to LEG_DIRS in scripts/browser-legs-census.mjs: " + bnr.map((b) => built.get(b) + " -> " + b).join(", ") : null,
    readNotBuilt: rnb.length ? "the census reads these modules and esbuild.js testBuild does not compile them, so npm test never runs them and a roster line naming one has no bundle: remove their directories (" + dirs(rnb).join(", ") + ") from LEG_DIRS in scripts/browser-legs-census.mjs, or add each to testBuild's entry list: " + rnb.join(", ") : null,
  };
}
/** esbuild's own mapping of a test-build config to bundles: a metafile build of `entryPoints` with the config's outdir, outbase,
 *  format, platform and target and no bundling (the mapping depends on the entry points and the outbase alone; bundling 1065
 *  entries in memory costs gigabytes), nothing written. esbuild.js and the esbuild package are required at run time
 *  (createRequire, as src/esbuild-build.test.ts does) because this test module is itself bundled. */
async function builtBundles(cwd: string, cfg: { entryPoints: string[]; outdir: string; outbase?: string; format: string; platform: string; target: string }): Promise<Map<string, string>> {
  const esbuild = createRequire(path.join(EXT, "package.json"))("esbuild");
  const res = await esbuild.build({ entryPoints: cfg.entryPoints, outdir: cfg.outdir, outbase: cfg.outbase, format: cfg.format, platform: cfg.platform, target: cfg.target, bundle: false, write: false, metafile: true, logLevel: "silent", absWorkingDir: cwd });
  const built = new Map<string, string>();
  for (const [out, o] of Object.entries(res.metafile.outputs as Record<string, { entryPoint?: string }>)) if (o.entryPoint) built.set(out, o.entryPoint);
  return built;
}

test("scope equals walk, by execution: the entry points esbuild.js testBuild compiles, mapped to bundles by esbuild's own metafile, are exactly the modules the census reads, in both directions; every LEG_DIRS entry is a directory under the repo root; this test's source mapping is esbuild's entry point for every bundle; census() reads no esbuild.js; and each direction's sentence is exercised over a synthetic config, a fourth directory the build compiles and a directory the build does not", async (t) => {
  const { census, LEG_DIRS } = await load();
  const { testBuild } = createRequire(path.join(EXT, "package.json"))(path.join(EXT, "esbuild.js"));
  const cfg = testBuild();
  const built = await builtBundles(EXT, cfg);
  assert.equal(built.size, cfg.entryPoints.length, "esbuild reports one output with an entry point per entry point of the test build (" + cfg.entryPoints.length + ")");
  const c = census(REPO);
  const d = scopeDiff(built, new Set(c.byBundle.keys()));
  assert.equal(d.builtNotRead, null, d.builtNotRead as string);
  assert.equal(d.readNotBuilt, null, d.readNotBuilt as string);
  // an absent LEG_DIRS entry contributes no bundle, so the equality above cannot see it (census() skips a directory that is not there)
  for (const dir of LEG_DIRS) assert.ok(fs.existsSync(path.join(REPO, dir)) && fs.statSync(path.join(REPO, dir)).isDirectory(), "LEG_DIRS in scripts/browser-legs-census.mjs names " + dir + ", which is not a directory under the repo root: the census walks nothing there, and the set equality above cannot see it because census() skips an absent directory");
  for (const [b, entry] of built) assert.equal(sourceOf(b), path.resolve(EXT, entry), "this test's source mapping for " + b + " is esbuild's entry point (" + entry + ")");
  assert.ok(!read(MODULE).split("\n").some((l) => !/^\s*\/\//.test(l) && /esbuild/.test(l)), "scripts/browser-legs-census.mjs names esbuild on no code line: the population is held equal to the test build here, by execution, never derived at run time (census() runs over synthetic roots that carry no esbuild.js, so a run-time derivation would need a fallback and the fallback is the silent skip this pin closes)");
  t.diagnostic("scope: " + built.size + " entry points built, " + c.byBundle.size + " modules read, directories " + JSON.stringify([...new Set([...built.keys()].map((b) => path.dirname(b)))].sort()));
  // both sentences, over a synthetic root and a synthetic config of testBuild's shape: four directories, the fourth (ui/panes)
  // holding a test module the census never reads; then a config of one directory while the census reads two
  const { root } = syntheticRoot(t, ["p01-alias.test.ts", "p22-from-src.test.ts"]);
  fs.mkdirSync(path.join(root, "ui", "panes"), { recursive: true });
  fs.writeFileSync(path.join(root, "ui", "panes", "probe-panes.test.ts"), 'import { test } from "node:test";\ntest("a leg in a fourth directory", () => {});\n');
  const ext = path.join(root, "vscode-extension");
  const entriesOf = (dirs: string[]) => dirs.flatMap((dir) => fs.readdirSync(path.join(ext, dir)).filter((f) => f.endsWith(".test.ts")).map((f) => dir + "/" + f));
  const four = await builtBundles(ext, { ...cfg, entryPoints: entriesOf(["src", "../ui", "../ui/webview", "../ui/panes"]) });
  const readSyn = new Set(census(root).byBundle.keys());
  const s1 = scopeDiff(four, readSyn);
  assert.ok(s1.builtNotRead !== null && s1.builtNotRead.includes("add their directories (ui/panes, relative to the repo root) to LEG_DIRS") && s1.builtNotRead.includes("../ui/panes/probe-panes.test.ts -> out-tests/ui/panes/probe-panes.test.js"), "a fourth directory in the config is red naming the directory and the module: " + s1.builtNotRead);
  assert.equal(s1.readNotBuilt, null, "and nothing the census read is unbuilt: " + s1.readNotBuilt);
  // esbuild's outbase is the entry points' common ancestor (a config of one directory alone would map its bundles directly under
  // out-tests/), so the second synthetic config keeps two directories under the root, one the census reads and one it does not
  const two = await builtBundles(ext, { ...cfg, entryPoints: entriesOf(["src", "../ui/panes"]) });
  const s2 = scopeDiff(two, readSyn);
  assert.ok(s2.readNotBuilt !== null && s2.readNotBuilt.includes("remove their directories (ui/webview) from LEG_DIRS") && s2.readNotBuilt.includes("out-tests/ui/webview/p01-alias.test.js"), "a directory the census reads and the config does not compile is red naming it: " + s2.readNotBuilt);
  assert.ok(s2.builtNotRead !== null && s2.builtNotRead.includes("(ui/panes, relative to the repo root)"), "and the fourth directory is still named in the other direction: " + s2.builtNotRead);
  assert.deepEqual(scopeDiff(four, new Set(four.keys())), { builtNotRead: null, readNotBuilt: null }, "equal sets: neither sentence");
});

/** The verdict on one grandfather row's history read, git's `cat-file -e <sha>:<rel>` result: null when the source is in the tree at
 *  the bound (exit 0); the remedy sentence naming the row when git says the path is not in that commit (exit 128 with either of
 *  git's two wordings, "does not exist in" for a path not on disk and "exists on disk, but not in" for a source added later); the
 *  hold-off sentence, a red never a pass, for any other result (the commit unreadable, another status). The one writer of that
 *  verdict: the loop over the real rows calls it, and the same test drives it over synthetic results and over two real git reads at
 *  the bound, since every real row passes and a verdict asserted over real rows alone could be gutted with the test green. */
function boundVerdict(where: string, sha: string, rel: string, r: { status: number | null; stderr: string }): string | null {
  if (r.status === 0) return null;
  if (r.status === 128 && /does not exist in|exists on disk, but not in/.test(r.stderr)) return where + ": the grandfather reason is bound to commit " + sha + " and " + rel + " is not in the tree at that commit, so the reason does not apply to this leg: run it in the step and add its bundle to " + ROSTER + " with the step's measured seconds, or, when the source reaches Firefox or WebKit or drives playwright from a string, write the engine form or the embedded-driver sentence";
  return where + ": the grandfather check could not read " + sha + ":" + rel + " (git cat-file -e exit " + r.status + ": " + r.stderr.trim() + "); a red hold-off, not a pass";
}

test("every grandfather row's source existed at the commit the exclusions header binds the reason to: the header holds one bound line; the commit is fetched at depth 1 when the checkout lacks it, and a fetch or object read that fails is a red hold-off naming the reason, never a pass; a source absent at that commit is refused with the remedy; the bound line says it reads the file's age, not what the file did there; the per-row verdict is one function, boundVerdict, driven here over synthetic git results (exit 0, 128 with each of git's two wordings, 128 with another message, another status) and over two reads through git itself at the bound (a path never in the tree, a source added after the bound)", async (t) => {
  const { ENGINE_PHRASE, EMBEDDED_PHRASE } = await load();
  const text = read(path.join(EXT, EXCLUDED));
  const { sentence, sha, embedded } = headerOf(text);
  const boundLine = text.split("\n").find((l) => l.startsWith("# Every grandfather reason, ")) as string;
  assert.ok(boundLine.includes("reads the file's age, not what it did there"), "the bound line names its residual: a source present at the commit without a browser launch may carry the reason (the bound reads the file's age); one that gained its launch later is rostered once it passes the gate, or carries the engine or embedded-driver form when one is true of it");
  const git = (args: string[]) => spawnSync("git", ["-C", REPO, ...args], { encoding: "utf8", timeout: 120000 });
  let have = git(["cat-file", "-e", sha]);
  if (have.status !== 0) {
    const shallow = git(["rev-parse", "--is-shallow-repository"]).stdout.trim();
    const fetch = git(["fetch", "--depth=1", "origin", sha]);
    assert.equal(fetch.status, 0, "the grandfather check could not run: commit " + sha + " is not in this clone (shallow: " + shallow + ") and `git fetch --depth=1 origin " + sha + "` failed (exit " + fetch.status + "): " + fetch.stderr.trim() + "; the bound cannot be read here, so this is a red hold-off, not a pass");
    have = git(["cat-file", "-e", sha]);
    assert.equal(have.status, 0, "the grandfather check could not run: after `git fetch --depth=1 origin " + sha + "` the commit is still not readable (git cat-file -e exit " + have.status + "): " + have.stderr.trim() + "; a red hold-off, not a pass");
    t.diagnostic("fetched commit " + sha + " at depth 1 (the clone lacked it; shallow: " + shallow + ")");
  }
  const kinds = parseExcluded(text).filter((e) => e.reason !== null).map((e) => ({ e, v: reasonKind(e.reason as string, sentence, ENGINE_PHRASE, embedded) }));
  assert.deepEqual(kinds.filter(({ v }) => v.kind === null).map(({ e, v }) => EXCLUDED + " line " + e.n + " (" + e.bundle + "): " + (v as { refusal: string }).refusal + "; the reason reads: " + e.reason), [], "every reason is one of the four closed forms before history is read for the grandfather rows (a misspelt exemption is refused here by name, never read as a reason of its own)");
  const rows = kinds.filter(({ v }) => v.kind === "grandfather").map(({ e }) => e);
  assert.ok(rows.length > 0, "the exclusions hold grandfather rows (" + rows.length + "); zero means the sentence stopped matching, not that the rows left");
  for (const e of rows) {
    const rel = path.relative(REPO, sourceOf(e.bundle));
    const v = boundVerdict(EXCLUDED + " line " + e.n + " (" + e.bundle + ")", sha, rel, git(["cat-file", "-e", sha + ":" + rel]));
    if (v !== null) assert.fail(v);
  }
  t.diagnostic(rows.length + " grandfather rows bound to " + sha + ", every source in the tree at that commit");
  // boundVerdict driven over synthetic results (every real row above passes, so without these the verdict could be gutted with the
  // test green and the diagnostic false): exit 0 passes; 128 with either of git's wordings for a path the commit lacks is the remedy
  // naming the row, the bound and the source; 128 with another message, or another status, is the hold-off, never a pass
  const AT = EXCLUDED + " line 999 (out-tests/ui/webview/zz-synthetic.test.js)";
  const REL = "ui/webview/zz-synthetic.test.ts";
  assert.equal(boundVerdict(AT, sha, REL, { status: 0, stderr: "" }), null, "a source in the tree at the bound (git exit 0): no verdict");
  const remedy = boundVerdict(AT, sha, REL, { status: 128, stderr: "fatal: path '" + REL + "' does not exist in '" + sha + "'" });
  assert.ok(remedy !== null && remedy.startsWith(AT + ": the grandfather reason is bound to commit " + sha + " and " + REL + " is not in the tree at that commit") && remedy.includes("add its bundle to " + ROSTER), "git's 'does not exist in' wording: the remedy sentence naming the row, the bound and the source, with the roster remedy (holds the sentence's opening and the remedy's words): " + remedy);
  assert.equal(boundVerdict(AT, sha, REL, { status: 128, stderr: "fatal: path '" + REL + "' exists on disk, but not in '" + sha + "'" }), remedy, "git's 'exists on disk, but not in' wording (a source added after the bound): the same remedy sentence");
  const unreadable = boundVerdict(AT, sha, REL, { status: 128, stderr: "fatal: Not a valid object name " + sha });
  assert.ok(unreadable !== null && unreadable.startsWith(AT + ": the grandfather check could not read " + sha + ":" + REL) && unreadable.endsWith("a red hold-off, not a pass"), "128 with another message (the commit unreadable): the hold-off naming the read, never a pass: " + unreadable);
  const other = boundVerdict(AT, sha, REL, { status: 1, stderr: "" });
  assert.ok(other !== null && other.includes("git cat-file -e exit 1") && other.endsWith("a red hold-off, not a pass"), "another status: the hold-off naming the status, never a pass: " + other);
  // and through git itself, so the wording the remedy keys on is held to git's, not to the strings above: a path not on disk and
  // absent at the bound ("does not exist in"), and a source on disk that was added after the bound ("exists on disk, but not in")
  const never = git(["cat-file", "-e", sha + ":ui/webview/zz-never.test.ts"]);
  assert.ok(never.status === 128 && /does not exist in/.test(never.stderr), "git at the bound over a path not on disk: exit 128 with 'does not exist in', the wording the remedy keys on (a git whose wording moved reds here, by name, not in the loop above): exit " + never.status + ": " + never.stderr.trim());
  const neverVerdict = boundVerdict(AT, sha, "ui/webview/zz-never.test.ts", never);
  assert.ok(neverVerdict !== null && neverVerdict.includes("ui/webview/zz-never.test.ts is not in the tree at that commit"), "a path absent at the bound, through git itself: the remedy: " + neverVerdict);
  const later = git(["cat-file", "-e", sha + ":ui/webview/real-viewer-leg-switch.test.ts"]);
  assert.ok(later.status === 128 && /exists on disk, but not in/.test(later.stderr), "git at the bound over ui/webview/real-viewer-leg-switch.test.ts, a source on disk that was added after the bound (a witness of a newer source: the bound the header names, " + sha.slice(0, 9) + ", predates that test, so a bound moved past its addition reds this assertion for a fixture reason, not a defect; pick a source newer than the bound then): exit 128 with 'exists on disk, but not in': exit " + later.status + ": " + later.stderr.trim());
  const laterVerdict = boundVerdict(AT, sha, "ui/webview/real-viewer-leg-switch.test.ts", later);
  assert.ok(laterVerdict !== null && laterVerdict.includes("ui/webview/real-viewer-leg-switch.test.ts is not in the tree at that commit"), "a source added after the bound, through git itself: the remedy naming that source: " + laterVerdict);
});

test("an exclusions reason is exactly one of four closed forms: the grandfather sentence as quoted, an engine reason with the phrase (a tail allowed), the embedded-driver sentence, a pending line; every variant of the exemption (a letter, a punctuation mark, a space, the word grandfather, an inflection, a paraphrase) is refused by name, and a reason that reads as one form while carrying another's phrase, or an engine reason whose tail names a second engine, is refused as ambiguous", async () => {
  const { ENGINE_PHRASE, EMBEDDED_PHRASE } = await load();
  const sentence = "existing before the roster, unmeasured in the gating job; its owner moves it to the roster with measured numbers";
  const k = (reason: string) => reasonKind(reason, sentence, ENGINE_PHRASE, EMBEDDED_PHRASE);
  assert.deepEqual(k(sentence), { kind: "grandfather", engines: [] }, "the sentence as quoted, whole and exact");
  assert.deepEqual(k("launches Firefox; " + ENGINE_PHRASE), { kind: "engine", engines: ["Firefox"] });
  assert.deepEqual(k("launches Firefox and WebKit; " + ENGINE_PHRASE + "; plans/x.md's Tests paragraph records the node scene, pinned by tools/x.test.mjs"), { kind: "engine", engines: ["Firefox", "WebKit"] }, "an engine reason admits a tail after the phrase (a locator, not a claim)");
  assert.deepEqual(k(EMBEDDED_PHRASE), { kind: "embedded", engines: [] });
  assert.deepEqual(k("pending #862: launches through inBrowser; at its merge of main the owner moves it to the roster"), { kind: "pending", engines: [] });
  const variants: [string, string][] = [["a capital letter", "Existing before the roster, unmeasured in the gating job; its owner moves it to the roster with measured numbers"], ["a comma for a semicolon", "existing before the roster; unmeasured in the gating job, its owner moves it to the roster with measured numbers"], ["doubled and tabbed spacing", "existing  before the\troster, unmeasured in the gating job; its owner moves it to the roster with measured numbers"], ["the word grandfather", "the grandfather clause: measured later"], ["one letter changed (befora)", sentence.replace("before", "befora")], ["one letter changed (rostar)", sentence.replace("the roster,", "the rostar,")], ["a letter added (rosters)", sentence.replace("the roster,", "the rosters,")], ["a letter dropped (befor)", sentence.replace("before", "befor")], ["an inflection (grandfathered)", "grandfathered: measured later"], ["a paraphrase", "predates the roster; measured later"], ["an engine named without the phrase", "launches Firefox"], ["the engine phrase alone", ENGINE_PHRASE], ["a pending line naming no PR", "pending: a leg with no PR named"], ["a reason of its own", "launches on its own"]];
  for (const [what, reason] of variants) { const v = k(reason); assert.equal(v.kind, null, what + " is refused, not read as a form: " + JSON.stringify(reason)); assert.ok((v as { refusal: string }).refusal.startsWith("the reason is none of the four forms"), what + ": the refusal names the four forms: " + (v as { refusal: string }).refusal); }
  const ambiguous: [string, string][] = [["an engine reason whose tail carries the grandfather sentence", "launches Firefox; " + ENGINE_PHRASE + "; " + sentence], ["an engine reason whose tail carries the embedded-driver sentence", "launches WebKit; " + ENGINE_PHRASE + "; " + EMBEDDED_PHRASE], ["a pending line that names an engine", "pending #859: launches Firefox at its merge"], ["a pending line carrying the engine phrase", "pending #859: " + ENGINE_PHRASE], ["a pending line carrying the embedded-driver sentence", "pending #864: " + EMBEDDED_PHRASE], ["an engine reason whose tail names a second engine", "launches Firefox; " + ENGINE_PHRASE + "; also WebKit"], ["an engine reason whose tail names the same engine again", "launches WebKit; " + ENGINE_PHRASE + "; WebKit in the pane's own scene"]];
  for (const [what, reason] of ambiguous) { const v = k(reason); assert.equal(v.kind, null, what + " is refused: " + JSON.stringify(reason)); assert.ok((v as { refusal: string }).refusal.startsWith("the reason is AMBIGUOUS"), what + ": refused as ambiguous, naming both forms: " + (v as { refusal: string }).refusal); }
});

test("reasonVerdict, the one writer of the exclusions rows' reason verdicts, driven over a synthetic table (the script's harness never reaches these rows): an engine named and not reached, reached and not named, the embedded-driver sentence on a leg that is not one and its reverse, an absent source, a source that is no leg, a reason of no form, an ambiguous reason, a row without a tab, and the matching pairs that pass", async () => {
  const mod = await load();
  const { ENGINE_PHRASE, EMBEDDED_PHRASE } = mod;
  const sentence = "existing before the roster, unmeasured in the gating job; its owner moves it to the roster with measured numbers";
  const rec = (over: Partial<Rec>): Rec => ({ rel: "ui/webview/zz.test.ts", refusals: [], launcherImported: false, sharedCalls: 1, embedded: [], playwright: [], engines: [], launches: [], skipTodo: [], swallow: [], reaches: true, ...over });
  const shared = rec({}), firefox = rec({ engines: ["chromium", "firefox"] }), embeddedLeg = rec({ sharedCalls: 0, embedded: [{ line: 2, what: "driver" }] }), noLeg = rec({ sharedCalls: 0, reaches: false, launcherImported: true });
  const row = (reason: string | null, n = 7): Excluded => ({ n, bundle: "out-tests/ui/webview/zz.test.js", reason });
  const verdict = (reason: string | null, r: Rec | undefined) => reasonVerdict(row(reason), r, reason === null ? { kind: null, refusal: "no reason" } : reasonKind(reason, sentence, ENGINE_PHRASE, EMBEDDED_PHRASE), mod, EMBEDDED_PHRASE);
  const has = (s: string | null, ...needles: string[]) => { assert.ok(s !== null, "a sentence, not null; needles " + JSON.stringify(needles)); for (const x of needles) assert.ok((s as string).includes(x), "the sentence carries " + JSON.stringify(x) + ": " + s); };
  has(verdict("launches Firefox; " + ENGINE_PHRASE, shared), "line 7", "the reason names Firefox and the source does not reach it", "drop the engine from the reason");
  has(verdict(sentence, firefox), "the reason does not name Firefox and the source reaches it", 'write "launches Firefox; ' + ENGINE_PHRASE + '" in the reason');
  has(verdict(EMBEDDED_PHRASE, shared), "the reason carries the embedded-driver sentence and the leg is not one (class shared)");
  has(verdict(sentence, embeddedLeg), "the reason does not carry the embedded-driver sentence and the leg is one");
  has(verdict(sentence, undefined), "names ui/webview/zz.test.ts, which is not in the tree (the source moved or was deleted): fix the line");
  has(verdict(sentence, noLeg), "names no browser leg: ", "never calls its inBrowser through that import");
  has(verdict("existing befora the roster, unmeasured in the gating job; its owner moves it to the roster with measured numbers", shared), "the reason is none of the four forms", "a misspelt exemption cannot pass as one", "the reason reads: existing befora");
  has(verdict("launches Firefox; " + ENGINE_PHRASE + "; " + sentence, firefox), "the reason is AMBIGUOUS", "reads as the engine form", "carries the grandfather form's phrase");
  has(verdict(null, shared), "has no tab, so it has no reason to read here");
  assert.equal(verdict("launches Firefox; " + ENGINE_PHRASE, firefox), null, "an engine reason over a source reaching that engine passes");
  assert.equal(verdict("launches Firefox; " + ENGINE_PHRASE + "; a locator after the phrase", firefox), null, "with a tail too");
  assert.equal(verdict(sentence, shared), null, "the grandfather sentence over a shared leg passes here (its age claim is the bound test's)");
  assert.equal(verdict(EMBEDDED_PHRASE, embeddedLeg), null, "the embedded-driver sentence over an embedded leg passes");
});

test("every planted form under tests/fixtures/browser-legs-plants is classified or refused as recorded, none is silent; a form the census cannot classify refuses with file and line; the plants in neither file are exactly the plants that are legs", async () => {
  const { census, rosterGap, engineNames, classOf } = await load();
  // the table and the fixture tree name the same files
  const onDisk = [W, "vscode-extension/src"].flatMap((d) => fs.readdirSync(path.join(PLANTS, d)).filter((f) => f.endsWith(".test.ts")).map((f) => d + "/" + f)).sort();
  assert.deepEqual(onDisk, PLANT_TABLE.map((p) => p.dir + "/" + p.file).sort(), "the plant table names every fixture and no other (a fixture added without a row is a plant with no expected outcome)");
  assert.ok(fs.existsSync(STUB_LAUNCHER), "the fixture tree carries a stub ui/webview/real-viewer-leg.ts for the plants to import");
  const c = census(PLANTS);
  const strict = census(PLANTS, { strictComputed: true });
  for (const p of PLANT_TABLE) {
    const bundle = bundleOf(p), r = c.byBundle.get(bundle);
    const at = p.dir + "/" + p.file + ": ";
    assert.ok(r, at + "the census read the module");
    if (p.refused) {
      assert.ok(r.refusals.some((x) => x.includes(p.refused as string)), at + "refused with file and line; expected a refusal containing " + JSON.stringify(p.refused) + ", got " + JSON.stringify(r.refusals) + ((p.refused as string).includes(SHADOW_REFUSAL) ? " (this row holds the SENTENCE through SHADOW_REFUSAL: a reword of the module's shadow refusal moves that constant and this row too)" : ""));
      assert.ok(c.refusals.some((x) => x.includes(p.refused as string)), at + "the refusal reaches the census's own list (the CLI exits 2 on it)");
      assert.equal(r.refusals.length, 1, at + "one refusal, the one the row holds (a second refusal on the same module is a form the census still refuses beside it, as the array destructuring of an untracked load was beside p132's helper refusal before round 4): " + JSON.stringify(r.refusals));
    } else {
      assert.deepEqual(r.refusals, [], at + "no refusal");
    }
    if (p.cls === "refused") { assert.equal(r.sharedCalls, undefined, at + "a parse diagnostic judges nothing else"); assert.ok(!c.legs.includes(bundle), at + "and is not a leg"); continue; }
    assert.equal(!!r.reaches, p.leg, at + (p.leg ? "is a browser leg" : "is not a browser leg"));
    assert.equal(c.legs.includes(bundle), p.leg, at + "the legs list agrees");
    assert.equal(classOf(r), p.cls, at + "class");
    const gap = r.reaches || r.launcherImported ? rosterGap(r) : null;   // the gate is asked of a leg, or of a module that imports the launcher
    if (p.gap === null) assert.equal(gap, null, at + "passes the roster gate; got " + JSON.stringify(gap));
    else assert.ok(gap !== null && gap.includes(p.gap), at + "the roster gap names the reason; expected a sentence containing " + JSON.stringify(p.gap) + ", got " + JSON.stringify(gap));
    if (p.engines) assert.deepEqual(r.engines, p.engines, at + "engines");
    if (p.playwright) assert.deepEqual(r.playwright, p.playwright, at + "playwright packages");
    if (p.launches) assert.deepEqual((r.launches || []).map((l) => l.how), p.launches, at + "own launches, by form");
    if (p.skipTodo) assert.deepEqual((r.skipTodo || []).map((s) => s.what), p.skipTodo, at + "skips and todos read from the tree");
    if (p.swallow) assert.deepEqual(r.swallow, p.swallow, at + "shared calls inside try/catch, by line");
    if (p.launcherImported !== undefined) assert.equal(r.launcherImported, p.launcherImported, at + "the launcher import is recorded");
    if (p.strictRefused) {
      const sr = strict.byBundle.get(bundle) as Rec;
      assert.ok(sr.refusals.some((x) => x.includes(p.file + ":")), at + "refused under --strict-computed (the fold is what reads it): " + JSON.stringify(sr.refusals));
    } else if (!p.refused) {
      assert.deepEqual((strict.byBundle.get(bundle) as Rec).refusals, [], at + "no refusal under --strict-computed either");
    }
    // the engine names as the exclusions reasons spell them
    const names = engineNames(r);
    assert.deepEqual(names, (p.engines || r.engines || []).filter((e) => e !== "chromium").map((e) => (e === "firefox" ? "Firefox" : "WebKit")), at + "engine names");
  }
  // with every plant in neither file, the census names exactly the plants that are legs
  const expectedLegs = PLANT_TABLE.filter((p) => p.leg).map(bundleOf).sort();
  assert.deepEqual(c.legs, expectedLegs, "the plants the census calls legs");
  assert.equal(c.refusals.length, PLANT_TABLE.filter((p) => p.refused).length, "one refusal per refused plant: " + JSON.stringify(c.refusals));
  // the census header states the third residual beside the other two: a browser reached without spelling a playwright package or
  // the launcher is unread by the walker, class none, no refusal. A text pin on the header's prose (its // lines joined, since the
  // sentence wraps): it holds that the header names the three forms and the outcome, not that the walker behaves so; the CLASS is
  // executed above by the p68 to p71 rows (a package name from the environment, another driver package, a package whose name
  // contains a tracked spelling, a spawned binary), each class none with no refusal. The read is the module's LEADING comment
  // block, the // lines before its first line of code, so a sentence moved into a body comment does not satisfy it. Each of the
  // three assertions holds the SENTENCE: a reword of the header's prose moves the pin too.
  const moduleLines = read(MODULE).split("\n");
  const codeAt = moduleLines.findIndex((l) => !l.startsWith("//") && l.trim() !== "");
  const header = moduleLines.slice(0, codeAt < 0 ? moduleLines.length : codeAt).filter((l) => l.startsWith("//")).map((l) => l.replace(/^\/\/ ?/, "")).join(" ");
  assert.ok(header.includes("Three residuals, stated"), "the census header's leading comment block states three residuals (the string-typed parameter's fold, the non-loader call, and a browser reached without spelling a playwright package or the launcher); a header counting two has dropped the third, whose plants are the p68 to p71 rows above. A sentence moved into a body comment is not the header's. Holds the sentence: a reword moves this pin too");
  for (const form of ["another driver package such as puppeteer", "a browser binary it spawns", "a driver source whose package name arrives at run time"]) assert.ok(header.includes(form), "the census header's leading comment block names the third residual's form " + JSON.stringify(form) + " (a text pin on the header's prose: the class that form takes is executed by the p68 to p71 rows above; holds the sentence: a reword of the form moves this pin too)");
  assert.ok(header.includes("is unread by the walker: class none, no refusal"), "the census header's leading comment block states the third residual's outcome, unread by the walker: class none, no refusal (the outcome the p68 to p71 rows record; holds the sentence: a reword moves this pin too)");
});

test("resolveLocal's two fallback bases (the repo root and vscode-extension/) resolve under the root alone: a folded specifier that lands outside the root against a base (../ui/<f> from the root is beside the checkout) is never looked up, so a sibling directory beside the checkout is neither read as a module of the tree nor an ambiguity, and the population is derived from the tree alone; executed over a root minted one level inside a temp parent with a sibling ui/ holding a file that loads playwright: with the tree's own copy absent the load names no file in the tree, with it present the tree's copy is the one file; the beside resolution is the module's own relative path and may name a file outside the checkout, stated in the function's comment, not clamped", async (t) => {
  const { census, resolveLocal } = await load();
  // the root one level inside the parent, so the sibling ui/ is the parent's and not a shared temp directory's (a root minted
  // directly under os.tmpdir() would put the sibling beside every other test's temp files)
  const parent = fs.mkdtempSync(path.join(os.tmpdir(), "cbl-nested-"));
  t.after(() => fs.rmSync(parent, { recursive: true, force: true }));
  const root = path.join(parent, "root");
  fs.mkdirSync(path.join(root, "ui", "webview"), { recursive: true });
  fs.mkdirSync(path.join(parent, "ui"), { recursive: true });
  // the sibling's text is assembled from pieces: this module is itself read by the census, and a string literal here that loads
  // playwright by its text would make this test an embedded-driver leg; the package name is assembled too, since THE SAFETY NET
  // refuses a package name standing as a call's argument (JSON.stringify's, as this line spelled it before round 5) and this module
  // is a module of the tree, so that spelling turned the tree census red on this file alone
  const loadsPlaywright = ["export const pw = requ", "ire(", JSON.stringify(["play", "wright"].join("")), ");\n"].join("");
  fs.writeFileSync(path.join(parent, "ui", "outside-helper.ts"), loadsPlaywright);
  const plant = path.join(root, "ui", "webview", "p-outside-fallback.test.ts");
  fs.writeFileSync(plant, 'import { test } from "node:test";\nconst h = require("../ui/outside-helper");\ntest("outside", () => { void h; });\n');
  const bundle = "out-tests/ui/webview/p-outside-fallback.test.js";
  const sibling = path.join(parent, "ui", "outside-helper.ts"), own = path.join(root, "ui", "outside-helper.ts");
  // case A: the tree's copy absent. Beside the module ../ui/outside-helper names root/ui/ui/outside-helper (no file); against the
  // root it names the SIBLING, outside the root, which the clamp drops; against vscode-extension/ it names root/ui/outside-helper,
  // absent. So the load names no file in the tree, and the census says so at the import line rather than reading the sibling
  assert.equal(resolveLocal(plant, "../ui/outside-helper", root), null, "case A (the tree's copy absent): resolveLocal names no file for ../ui/outside-helper (the candidate against the root, " + sibling + ", is outside the root and is dropped before it is looked up); a result naming the sibling means the base resolution read past the root");
  const a = census(root);
  const recA = a.byBundle.get(bundle) as Rec;
  assert.ok(recA.refusals.some((x) => x.startsWith("ui/webview/p-outside-fallback.test.ts:2: loads ../ui/outside-helper, which names no file in the tree (tried beside ui/webview/p-outside-fallback.test.ts, under the repo root and under vscode-extension/)")), "case A: the census refuses the plant at its import line with the no-file sentence naming the three places it tried, none of them beside the checkout; a refusal naming ../ui/outside-helper.ts as a module that names playwright means the sibling was read as a module of the tree: " + JSON.stringify(recA.refusals));
  assert.ok(!recA.refusals.some((x) => x.includes("names a playwright package")), "case A: the sibling beside the checkout is not read as a module of the tree: " + JSON.stringify(recA.refusals));
  // case B: the tree's own copy present too (a clean module). Against vscode-extension/ the specifier names it; against the root
  // it would name the sibling, dropped by the clamp: one file, no ambiguity
  fs.writeFileSync(own, "export const pw = null;\n");
  assert.deepEqual(resolveLocal(plant, "../ui/outside-helper", root), { abs: own }, "case B (both present): resolveLocal names the tree's own copy alone; an ambiguity naming the sibling means the base resolution read past the root");
  const b = census(root);
  assert.deepEqual((b.byBundle.get(bundle) as Rec).refusals, [], "case B: no refusal, the tree's copy is the one file the load names (an ambiguity refusal naming two files means the sibling beside the checkout was counted as one of them)");
  // the boundary the comment states: the beside resolution is the module's own relative path and is not clamped, so a specifier
  // that genuinely climbs out of the checkout names the outside file by its spelling (here through the sibling, read as itself)
  assert.deepEqual(resolveLocal(plant, "../../../ui/outside-helper", root), { abs: sibling }, "the beside resolution (the module's own relative path) may name a file outside the checkout and is stated, not clamped: ../../../ui/outside-helper from root/ui/webview names the sibling");
});

test("the plant table says which of its 51 round-3 rows (p38 to p88) discriminate against the census before round 3 and what the others hold: 45 red under that census (44 at round 3, and p74 since round 5's safety net refused a text that census passed), 6 hold one of four stated reasons instead (holds), and 3 of the 45 red on a property other than their section's and name the plant that carries it (carried); which of its 67 round-4 rows (p89 to p155) discriminate against the census before round 4: 62 red under that census and 5 hold a stated reason instead; and which of its round-5 rows (p156 to R5_LAST) discriminate against the census before round 5, the module at the round-4 head: every one red under it unless R5_HELD names it with its reason; the discrimination itself was established by running each earlier census over the plants, recorded in the PR's notes, and is not re-run here, since none of those censuses is in the tree at test time, so this test holds the TABLE's statement, not the fact", () => {
  const idOf = (p: Plant) => (/^p\d+/.exec(p.file) || [""])[0];
  const num = (p: Plant) => Number(idOf(p).slice(1));
  const inRound3 = (p: Plant) => num(p) >= 38 && num(p) <= 88;
  // the round-4 rows: p89 to R4_LAST, one row each; a round-4 builder that adds a row moves R4_LAST and, when the row stays green
  // under the census before round 4, adds it to R4_HELD with holds set (the round-3 population above is closed and does not move)
  const R4_LAST = 155;
  const R4_HELD = ["p119", "p125", "p140", "p141", "p155"];
  const R4_CARRIED: string[] = [];
  const inRound4 = (p: Plant) => num(p) >= 89 && num(p) <= R4_LAST;
  const byNum = (a: string, b: string) => Number(a.slice(1)) - Number(b.slice(1));
  const NOT_RERUN = " (the discrimination was established by running the census before round 3 over the plants, recorded in the PR's notes, and is not re-run here, since that census is not in the tree at test time: this assertion holds the table's statement, not the fact)";
  const r3 = PLANT_TABLE.filter(inRound3);
  assert.deepEqual(r3.map(idOf).sort(byNum), Array.from({ length: 51 }, (_, i) => "p" + (38 + i)), "the round-3 rows are p38 to p88, 51 of them, one row each, so every one takes a verdict below: red under the census before round 3 (no holds field) or green with holds set" + NOT_RERUN);
  // the five forms a holds field opens with: the four the round-3 and round-4 rows use, and round 5's pin of an arm no plant carried (a
  // row refused at the head before its round by an arm no earlier row exercised, which the round rerouted or kept: green before and after)
  const FORMS = ["a stated residual boundary", "the no-refusal half of a pair whose partner reds", "a guard of round 3's own scoping", "a shape another plant carries", "a pin of an arm no plant carried"];
  const held = r3.filter((p) => p.holds !== undefined);
  assert.deepEqual(held.map(idOf).sort(byNum), ["p68", "p69", "p70", "p71", "p72", "p87"], "the round-3 rows that stay green under the census before round 3 are exactly these 6, each with holds set (p74 held until round 5, whose safety net refuses it, so its row now reds under that census and is counted red): a row marked as holding something else that reds under that census, or a green row left unmarked, is red here" + NOT_RERUN);
  for (const p of held) assert.ok(FORMS.some((f) => (p.holds as string).startsWith(f + ": ") && (p.holds as string).length > f.length + 2), idOf(p) + ": holds begins with one of the five forms, a colon and the row's detail: " + JSON.stringify(p.holds));
  const carried = r3.filter((p) => p.carried !== undefined);
  assert.deepEqual(carried.map(idOf).sort(byNum), ["p41", "p42", "p47"], "the round-3 rows that red under the census before round 3 on a property other than their section's are exactly these 3, each with carried set" + NOT_RERUN);
  const rows = new Map(PLANT_TABLE.map((p) => [idOf(p), p] as [string, Plant]));
  for (const p of carried) {
    assert.equal(p.holds, undefined, idOf(p) + ": a carried row reds under the census before round 3, so it holds no reason of its own");
    const detail = (p.carried as string).slice("a shape another plant carries: ".length);
    assert.ok((p.carried as string).startsWith("a shape another plant carries: ") && detail.length > 0, idOf(p) + ": carried begins with that form, a colon and the row's detail: " + JSON.stringify(p.carried));
    const carriers = [...new Set([...detail.matchAll(/\bp\d+\b/g)].map((m) => m[0]))].filter((x) => x !== idOf(p));
    assert.ok(carriers.length > 0, idOf(p) + ": carried names the plant that carries the property");
    for (const c of carriers) {
      const q = rows.get(c);
      assert.ok(q !== undefined, idOf(p) + ": the carrier " + c + " is a table row" + NOT_RERUN);
      assert.equal((q as Plant).holds, undefined, idOf(p) + ": the carrier " + c + (inRound3(q as Plant) ? " is a round-3 row without holds, so the table says it reds under the census before round 3" : " is a row before p38, outside the round-3 population, where holds is never set (the last assertion below), so this check holds only that the row exists; that it reds under the census before round 3 is the table's statement alone") + NOT_RERUN);
    }
  }
  assert.equal(r3.length - held.length, 45, "45 round-3 rows red under the census before round 3 (51 rows, 6 with holds: 44 red at round 3, and p74 since round 5)" + NOT_RERUN);
  // the round-4 rows, the same statement against the census before round 4 (the module at the round-3 head): every row without
  // holds reds under it, a row with holds says what else it holds, and a carried row names its carrier
  const NOT_RERUN4 = " (the discrimination was established by running the census before round 4, the module at the round-3 head, over the plants, recorded in the PR's notes, and is not re-run here, since that census is not in the tree at test time: this assertion holds the table's statement, not the fact)";
  const r4 = PLANT_TABLE.filter(inRound4);
  assert.deepEqual(r4.map(idOf).sort(byNum), Array.from({ length: R4_LAST - 88 }, (_, i) => "p" + (89 + i)), "the round-4 rows are p89 to p" + R4_LAST + ", " + (R4_LAST - 88) + " of them, one row each, so every one takes a verdict below: red under the census before round 4 (no holds field) or green with holds set" + NOT_RERUN4);
  const held4 = r4.filter((p) => p.holds !== undefined);
  assert.deepEqual(held4.map(idOf).sort(byNum), R4_HELD, "the round-4 rows that stay green under the census before round 4 are exactly " + JSON.stringify(R4_HELD) + ", each with holds set: a row marked as holding something else that reds under that census, or a green row left unmarked, is red here" + NOT_RERUN4);
  for (const p of held4) assert.ok(FORMS.some((f) => (p.holds as string).startsWith(f + ": ") && (p.holds as string).length > f.length + 2), idOf(p) + ": holds begins with one of the five forms, a colon and the row's detail: " + JSON.stringify(p.holds));
  const carried4 = r4.filter((p) => p.carried !== undefined);
  assert.deepEqual(carried4.map(idOf).sort(byNum), R4_CARRIED, "the round-4 rows that red under the census before round 4 on a property other than their section's are exactly " + JSON.stringify(R4_CARRIED) + ", each with carried set" + NOT_RERUN4);
  for (const p of carried4) {
    assert.equal(p.holds, undefined, idOf(p) + ": a carried row reds under the census before round 4, so it holds no reason of its own");
    const carriers = [...new Set([...(p.carried as string).slice("a shape another plant carries: ".length).matchAll(/\bp\d+\b/g)].map((m) => m[0]))].filter((x) => x !== idOf(p));
    assert.ok(carriers.length > 0 && carriers.every((c) => rows.has(c)), idOf(p) + ": carried names a table row that carries the property" + NOT_RERUN4);
  }
  assert.equal(r4.length - held4.length, R4_LAST - 88 - R4_HELD.length, (R4_LAST - 88 - R4_HELD.length) + " round-4 rows red under the census before round 4 (" + (R4_LAST - 88) + " rows, " + R4_HELD.length + " with holds)" + NOT_RERUN4);
  // the round-5 rows, the same statement against the census before round 5 (the module at the round-4 head): THE SAFETY NET's plants
  // and the rows the round's folds add after them, p156 to R5_LAST, one row each, every one red under that census (class none with no
  // refusal, or a reach with engines [] and launches [] and no refusal, where the row expects a refusal; for p203 to p206, the census
  // over the plants throwing whole before it judges a row, the shape correctness-1 named) unless R5_HELD names it with
  // holds set (a control, a pin of an arm no plant carried, a stated boundary); a round-5 builder who adds a row moves R5_LAST to it
  // and, when the row stays green under that census, adds it to R5_HELD with holds set (the round-4 population above is closed)
  const NOT_RERUN5 = " (the discrimination was established by running the census before round 5, the module at the round-4 head, over the plants, recorded in the PR's notes, and is not re-run here, since that census is not in the tree at test time: this assertion holds the table's statement, not the fact)";
  const R5_FIRST = R4_LAST + 1, R5_LAST = 207;
  const R5_HELD = ["p197", "p198", "p200", "p201", "p202", "p207"];
  const R5_CARRIED: string[] = [];
  const inRound5 = (p: Plant) => num(p) >= R5_FIRST && num(p) <= R5_LAST;
  const r5 = PLANT_TABLE.filter(inRound5);
  assert.deepEqual(PLANT_TABLE.filter((p) => num(p) > R5_LAST).map(idOf), [], "every row past p" + R4_LAST + " is a round-5 row and takes a verdict below: a row numbered past R5_LAST (p" + R5_LAST + ") is outside the statement, so a builder who adds a row moves R5_LAST to it" + NOT_RERUN5);
  assert.deepEqual(r5.map(idOf).sort(byNum), Array.from({ length: R5_LAST - R5_FIRST + 1 }, (_, i) => "p" + (R5_FIRST + i)), "the round-5 rows are p" + R5_FIRST + " to p" + R5_LAST + ", " + (R5_LAST - R5_FIRST + 1) + " of them, one row each, so every one takes a verdict below: red under the census before round 5 (no holds field) or green with holds set" + NOT_RERUN5);
  const held5 = r5.filter((p) => p.holds !== undefined);
  assert.deepEqual(held5.map(idOf).sort(byNum), R5_HELD, "the round-5 rows that stay green under the census before round 5 are exactly " + JSON.stringify(R5_HELD) + ", each with holds set: a row marked as holding something else that reds under that census, or a green row left unmarked, is red here" + NOT_RERUN5);
  for (const p of held5) assert.ok(FORMS.some((f) => (p.holds as string).startsWith(f + ": ") && (p.holds as string).length > f.length + 2), idOf(p) + ": holds begins with one of the five forms, a colon and the row's detail: " + JSON.stringify(p.holds));
  const carried5 = r5.filter((p) => p.carried !== undefined);
  assert.deepEqual(carried5.map(idOf).sort(byNum), R5_CARRIED, "the round-5 rows that red under the census before round 5 on a property other than their section's are exactly " + JSON.stringify(R5_CARRIED) + ", each with carried set" + NOT_RERUN5);
  for (const p of carried5) {
    assert.equal(p.holds, undefined, idOf(p) + ": a carried row reds under the census before round 5, so it holds no reason of its own");
    const carriers = [...new Set([...(p.carried as string).slice("a shape another plant carries: ".length).matchAll(/\bp\d+\b/g)].map((m) => m[0]))].filter((x) => x !== idOf(p));
    assert.ok(carriers.length > 0 && carriers.every((c) => rows.has(c)), idOf(p) + ": carried names a table row that carries the property" + NOT_RERUN5);
  }
  assert.equal(r5.length - held5.length, R5_LAST - R5_FIRST + 1 - R5_HELD.length, (R5_LAST - R5_FIRST + 1 - R5_HELD.length) + " round-5 rows red under the census before round 5 (" + (R5_LAST - R5_FIRST + 1) + " rows, " + R5_HELD.length + " with holds)" + NOT_RERUN5);
  assert.deepEqual(PLANT_TABLE.filter((p) => (p.holds !== undefined || p.carried !== undefined) && !inRound3(p) && !inRound4(p) && !inRound5(p)).map(idOf), [], "holds and carried are fields of the round-3 rows (p38 to p88), the round-4 rows (p89 to p" + R4_LAST + ") and the round-5 rows (p" + R5_FIRST + " to p" + R5_LAST + "), the populations the statements are about; an earlier row carries neither");
});

test("the relative node_modules road (n09, extra5-3), over a synthetic root whose vscode-extension/node_modules is the extension's own: a test module that imports playwright by a relative path into node_modules is class own with the engine and the launch read, one that requires it so the same, one that loads a helper doing so is refused by name as loading a module that names a playwright package, and one that spells the path as the argument of a call the walker knows no loader for is refused by THE SAFETY NET's relative-path kind (keyed on resolveSpec, the fold's own reader); the plants live under tests/fixtures/browser-legs-plants/relative-node-modules, outside the tree the table enumerates, since their path resolves only beside a node_modules the fixtures cannot carry (before round 5 each was class none with no refusal: the walker read the path as a local module and the census skipped a file under node_modules, a silent Firefox or WebKit leg; under the net alone the first three were refused by the relative-path kind, n09c through its helper)", async (t) => {
  const { census, classOf } = await load();
  const RELPW = path.join(PLANTS, "relative-node-modules", "ui", "webview");
  const { root } = syntheticRoot(t, []);
  const files = fs.readdirSync(RELPW).sort();
  assert.deepEqual(files, ["n09a-relative-node-modules-import.test.ts", "n09b-relative-node-modules-require.test.ts", "n09c-relative-node-modules-helper.test.ts", "n09d-relative-node-modules-unknown-callee.test.ts", "relpw-helper.ts"], "the fixture directory holds the four plants and the helper, and nothing else (a plant added without a row below is a plant with no expected outcome)");
  for (const f of files) fs.copyFileSync(path.join(RELPW, f), path.join(root, "ui", "webview", f));
  // the precondition, derived from the fixture rather than restated (a package name spelled as a call's argument here would be the
  // p74 form in a module of the tree, and the net refused this file on that spelling when the precondition was first written so):
  // the path the helper spells resolves, beside the synthetic root's linked node_modules, to the extension's own copy of the package
  const spelled = (/ from "([^"]+)";/.exec(read(path.join(RELPW, "relpw-helper.ts"))) as RegExpExecArray)[1];
  assert.ok(fs.existsSync(path.join(root, "ui", "webview", spelled, "package.json")), "the extension's node_modules carries the package the plants spell by relative path (" + spelled + "; npm ci installs it): without it the load names no file and the refusal would be the missing-module one, not the census's reading of the package, so the precondition is asserted rather than left to the rows");
  const c = census(root);
  const bundle = (file: string) => "out-tests/ui/webview/" + file.replace(/\.test\.ts$/, ".test.js");
  assert.equal(c.byBundle.size, 4, "the census read the four plants and nothing else");
  // the two direct loads: class own, the package recorded under the spelled path, the engine read through the binding, the launch read
  const own: [string, string][] = [["n09a-relative-node-modules-import.test.ts", "firefox"], ["n09b-relative-node-modules-require.test.ts", "webkit"]];
  for (const [file, engine] of own) {
    const r = c.byBundle.get(bundle(file)) as Rec;
    assert.ok(r, file + ": the census read the module");
    assert.deepEqual(r.refusals, [], file + ": no refusal (the fold reads the load; a refusal here is the net's relative-path kind, which means resolveSpec stopped reading the path as the package)");
    assert.equal(classOf(r), "own", file + ": class own, the package loaded by the module itself");
    assert.deepEqual(r.playwright, [spelled], file + ": the playwright set carries the specifier as spelled (the relative path), read by resolveSpec as the package");
    assert.deepEqual(r.engines, [engine], file + ": the engine read through the binding");
    assert.equal((r.launches || []).length, 1, file + ": the launch read: " + JSON.stringify(r.launches));
    assert.ok(c.legs.includes(bundle(file)), file + ": a leg");
  }
  // the helper: read transitively, its package named at the importer with the spelled path, the importer class none
  const helperRow = c.byBundle.get(bundle("n09c-relative-node-modules-helper.test.ts")) as Rec;
  const helperWant = "n09c-relative-node-modules-helper.test.ts:2: loads ui/webview/relpw-helper.ts, which names a playwright package (" + spelled + "), so this module reaches a browser through it";
  assert.equal(helperRow.refusals.length, 1, "n09c: one refusal, the importer's: " + JSON.stringify(helperRow.refusals));
  assert.ok(helperRow.refusals[0].includes(helperWant), "n09c: refused as loading a module that names a playwright package, the spelled path named (holds the SENTENCE of localRefusals' arm); expected a refusal containing " + JSON.stringify(helperWant) + ", got " + JSON.stringify(helperRow.refusals));
  assert.equal(classOf(helperRow), "none", "n09c: class none (the walker follows nothing through the helper)");
  // the unknown callee: no fold reads load(<path>), so the mention stands and the net refuses by its relative-path kind, at line 3
  const netRow = c.byBundle.get(bundle("n09d-relative-node-modules-unknown-callee.test.ts")) as Rec;
  const netWant = "n09d-relative-node-modules-unknown-callee.test.ts:3: " + NET_HEAD + NET_NMPW + NET_NO_REACH;
  assert.equal(netRow.refusals.length, 1, "n09d: one refusal, the net's: " + JSON.stringify(netRow.refusals));
  assert.ok(netRow.refusals[0].includes(netWant), "n09d: refused by name with the path and the line (holds the SENTENCE through the NET_ constants); expected a refusal containing " + JSON.stringify(netWant) + ", got " + JSON.stringify(netRow.refusals));
  assert.equal(classOf(netRow), "none", "n09d: class none, no reach");
  for (const r of [helperRow, netRow]) assert.ok(c.refusals.includes(r.refusals[0]), r.rel + ": the refusal reaches the census's own list (the CLI exits 2 on it)");
  assert.equal(c.refusals.length, 2, "two refusals on the census's list, n09c's and n09d's");
  assert.deepEqual(c.legs, own.map(([f]) => bundle(f)).sort(), "the legs are the two direct loads");
});

test("the census never dies unnamed (correctness-1, round 5): a module whose classification throws is refused by name with the exception's name and message, as the thrown record (refusals alone, class refused, no TSV row), and every other module is judged, at both homes of the catch, executed over a synthetic root: a DIRECTORY named like a test module beside a plain shared leg (a read error, EISDIR, deterministic with no fixture bytes) is refused at census()'s catch and the neighbour is judged; a test module that loads a helper whose expression nesting overflows the walker (a binary chain generated here, sized from this thread's own recursion limit so it overflows whatever stack is in effect, which is why it is no fixture) is refused at its import line through localRefusals' own() catch with the helper's thrown record in the chain, and a test module holding such a chain itself is refused at census()'s catch; the CLI over the root exits 2 with the thrown refusal on stderr, the neighbour's row on stdout and a summary line saying each refusal names its file, since a thrown record has no line; before round 5 the census over such a root threw unnamed, exit 1 and zero rows, a silent pass for every module of the tree", async (t) => {
  const { census, classOf } = await load();
  const { root } = syntheticRoot(t, []);
  const web = path.join(root, "ui", "webview");
  const DIR = "qc1h-directory-named-as-a-module.test.ts", NEIGHBOUR = "qc1i-neighbour.test.ts", DEEP = "qc1f-deep-binary-chain.test.ts", IMPORTER = "qc1g-imports-deep-helper.test.ts", HELPER = "deep-helper.ts";
  const bundle = (f: string) => "out-tests/ui/webview/" + f.replace(/\.test\.ts$/, ".test.js");
  const THREW = ": the census threw while classifying this module, so it is refused rather than left unjudged";
  fs.mkdirSync(path.join(web, DIR));
  fs.writeFileSync(path.join(web, NEIGHBOUR), 'import { test } from "node:test";\nimport { inBrowser } from "./real-viewer-leg";\ntest("qc1i", (t) => inBrowser(t, async () => {}));\n');
  // the recursion limit of THIS thread (census() below runs in it), measured by a trivial recursion; the chain holds four times that
  // many terms, and the walker spends more than one frame per term of a left-deep chain (the round's records: the overflow at well under
  // half the trivial limit on the default stack), so it overflows here under any --stack-size, and a larger stack grows the chain with it
  const limit = (() => { let d = 0; const f = (): void => { d++; f(); }; try { f(); } catch { /* the RangeError is the measurement */ } return d; })();
  const chain = "export const depth = (" + Array.from({ length: 4 * limit }, () => "1").join(" + ") + ");\n";
  fs.writeFileSync(path.join(web, HELPER), '// a helper whose expression nesting overflows the walker (generated by the census test)\nimport { inBrowser } from "./real-viewer-leg";\n' + chain + 'export function go(t: any, body: (b: any) => Promise<void>): Promise<void> { return inBrowser(t, body); }\n');
  fs.writeFileSync(path.join(web, IMPORTER), 'import { test } from "node:test";\nimport { inBrowser } from "./real-viewer-leg";\nimport { go } from "./deep-helper";\ntest("qc1g-own", (t) => inBrowser(t, async () => {}));\ntest("qc1g-helper", (t) => go(t, async () => {}));\n');
  fs.writeFileSync(path.join(web, DEEP), 'import { test } from "node:test";\nimport { inBrowser } from "./real-viewer-leg";\n' + chain + 'test("qc1f", (t) => inBrowser(t, async () => {}));\n');
  const c = census(root);
  assert.equal(c.byBundle.size, 4, "the census read the four entries (a directory named like a test module is an entry the read finds) and judged or refused each; before round 5 it threw at the first of them and judged none: " + JSON.stringify([...c.byBundle.keys()]));
  // census()'s catch, the read error: refused by name with the exception, the record the parse-diagnostic shape, the neighbour judged
  const dirRow = c.byBundle.get(bundle(DIR)) as Rec;
  assert.equal(dirRow.refusals.length, 1, DIR + ": one refusal, the thrown record's: " + JSON.stringify(dirRow.refusals));
  assert.ok(dirRow.refusals[0].startsWith("ui/webview/" + DIR + THREW), DIR + ": refused by name at census()'s catch, the refusal opening with the file (no line: the module was never read) and the thrown sentence (holds the SENTENCE: a reword of thrown() moves this pin); got " + JSON.stringify(dirRow.refusals[0]));
  assert.ok(dirRow.refusals[0].includes("EISDIR"), DIR + ": the exception's text is in the refusal (the read error's code), so the reader knows what the census could not read: " + dirRow.refusals[0]);
  assert.equal(dirRow.sharedCalls, undefined, DIR + ": the thrown record judges nothing else (the parse-diagnostic record's shape, refusals alone)");
  assert.equal(classOf(dirRow), "refused", DIR + ": class refused");
  assert.ok(!c.legs.includes(bundle(DIR)), DIR + ": not a leg");
  const nb = c.byBundle.get(bundle(NEIGHBOUR)) as Rec;
  assert.deepEqual(nb.refusals, [], NEIGHBOUR + ": the neighbour is judged, no refusal (the census went on past the directory)");
  assert.equal(classOf(nb), "shared", NEIGHBOUR + ": the neighbour is judged, class shared");
  assert.ok(c.legs.includes(bundle(NEIGHBOUR)), NEIGHBOUR + ": the neighbour is a leg");
  // own()'s catch: the helper's thrown record reaches the importer through the cannot-classify arm, the exception in the chain, and the
  // importer's own call is still read
  const imp = c.byBundle.get(bundle(IMPORTER)) as Rec;
  const want = "ui/webview/" + IMPORTER + ":3: loads ui/webview/" + HELPER + ", which the census cannot classify (ui/webview/" + HELPER + THREW;
  assert.equal(imp.refusals.length, 1, IMPORTER + ": one refusal, the importer's through the helper's thrown record: " + JSON.stringify(imp.refusals));
  assert.ok(imp.refusals[0].startsWith(want), IMPORTER + ": refused at the import line with the helper's thrown record in the chain (own()'s catch); expected a refusal opening with " + JSON.stringify(want) + ", got " + JSON.stringify(imp.refusals[0]));
  assert.ok(imp.refusals[0].includes("RangeError"), IMPORTER + ": the exception's name is in the chain (the walker's or the compiler's recursion overflowing): " + imp.refusals[0]);
  assert.equal(classOf(imp), "shared", IMPORTER + ": the importer's own inBrowser call is read beside the refusal, class shared");
  // census()'s catch, the walker's own overflow on a test module
  const deep = c.byBundle.get(bundle(DEEP)) as Rec;
  assert.equal(deep.refusals.length, 1, DEEP + ": one refusal, the thrown record's: " + JSON.stringify(deep.refusals));
  assert.ok(deep.refusals[0].startsWith("ui/webview/" + DEEP + THREW) && deep.refusals[0].includes("RangeError"), DEEP + ": refused by name at census()'s catch with the RangeError (before round 5 the census died here, unnamed); got " + JSON.stringify(deep.refusals[0]));
  assert.equal(classOf(deep), "refused", DEEP + ": class refused, nothing else judged of it");
  assert.equal(c.refusals.length, 3, "three refusals on the census's list (the directory's, the importer's, the deep module's), each reaching the CLI: " + JSON.stringify(c.refusals));
  assert.deepEqual(c.legs, [bundle(IMPORTER), bundle(NEIGHBOUR)].sort(), "the legs are the neighbour and the importer, judged on either side of the modules that threw");
  // the CLI over the same root, the chain files removed first (the child process's stack is not this thread's, and the directory's read
  // error is the deterministic witness there): exit 2, the thrown refusal on stderr, the neighbour's row on stdout, the summary reworded
  for (const f of [DEEP, IMPORTER, HELPER]) fs.rmSync(path.join(web, f));
  const r = spawnSync(process.execPath, [path.join(root, "vscode-extension", "scripts", "browser-legs-census.mjs"), "--tsv", root], { cwd: path.join(root, "vscode-extension"), encoding: "utf8" });
  assert.equal(r.status, 2, "the CLI exits 2 on the thrown refusal (before round 5: exit 1 with the bare message and no row); stderr:\n" + r.stderr);
  assert.ok(r.stderr.includes("browser-legs-census: REFUSED ui/webview/" + DIR + THREW), "the CLI prints the thrown refusal by name; stderr:\n" + r.stderr);
  assert.ok(r.stderr.includes(" refusal(s) above, each naming its file"), "the CLI's summary line says each refusal names its file, since a thrown record has no line and the earlier wording (each with file and line) would be false for it; stderr:\n" + r.stderr);
  assert.ok(r.stdout.includes(bundle(NEIGHBOUR) + "\t1\t-\t-\tshared"), "the neighbour's row is on stdout: the census went on past the directory; stdout:\n" + r.stdout);
  assert.ok(!r.stdout.includes(bundle(DIR)), "the thrown record has no TSV row (it carries no class fields); stdout:\n" + r.stdout);
});

test("THE INVARIANT is armed: one mutation of the walker per clause, over the plants, is refused by the invariant naming what the mutation silenced (a playwright package resolved and not recorded; a launcher load the walker stopped reading; a launcher binding handed on that the value-use arm stopped refusing; a computed member on the binding that rootOf stopped seeing), and each mutation's anchor is found once, so a rewrite of the walker re-anchors this test rather than passing it empty", async (t) => {
  // the census module copied into a synthetic root beside the compiler, mutated by one exact replacement, and run over the plants
  // named; every mutation below silences one road the round-2 review found (its plants under tests/fixtures/browser-legs-plants)
  // and the invariant, unchanged, refuses that road with its own sentence. A mutation that leaves the invariant blind is not here:
  // the createRequire-applied loader (extra6-1) and the invariant's own removal are held by the plant rows alone.
  const plants = ["p48-require-pw-chain.test.ts", "p49-require-launcher-chain.test.ts", "p62-await-import-member-call.test.ts", "p58-member-to-value.test.ts", "p59-namespace-alias.test.ts", "p60-destructure-namespace.test.ts", "p61-namespace-as-argument.test.ts", "p73-namespace-member-bind.test.ts", "p65-cast-launcher-computed.test.ts", "p01-alias.test.ts"];
  const { root } = syntheticRoot(t, plants);
  const source = read(MODULE);
  const mutations: { clause: string; anchor: string; to: string; refused: string[] }[] = [
    { clause: "1: a playwright package resolved by a loader call is recorded where it is resolved", anchor: 'if (r.kind === "playwright") playwright.add(r.spec);\n    noteResolved(e, r.kind, r.spec, "load");', to: 'noteResolved(e, r.kind, r.spec, "load");', refused: ["p48-require-pw-chain.test.ts:2: THE INVARIANT: the census resolved the playwright package playwright"] },
    { clause: "2: a launcher load that is the object of a member the walker read is followed", anchor: 'const l = loaderCall(obj); if (l && l.kind === "launcher") { followed.add(unwrap(obj));', to: 'const l = null; if (l && l.kind === "launcher") { followed.add(unwrap(obj));', refused: ["p49-require-launcher-chain.test.ts:2: THE INVARIANT: the census resolved the shared launcher (./real-viewer-leg) here and its record carries nothing of the load", "p62-await-import-member-call.test.ts:2: THE INVARIANT: the census resolved the shared launcher (./real-viewer-leg) here and its record carries nothing of the load"] },
    { clause: "3: a launcher binding handed on as a value is refused by the value-use arm", anchor: "else if (handed) { refuse(n,", to: "else if (false) { refuse(n,", refused: ["p58-member-to-value.test.ts:3: THE INVARIANT: the census resolved the name leg here to the shared launcher's binding", "p59-namespace-alias.test.ts:3: THE INVARIANT: the census resolved the name leg", "p60-destructure-namespace.test.ts:3: THE INVARIANT: the census resolved the name leg", "p61-namespace-as-argument.test.ts:4: THE INVARIANT: the census resolved the name leg", "p73-namespace-member-bind.test.ts:3: THE INVARIANT: the census resolved the name leg"] },
    { clause: "3: a computed member on the binding under a cast is refused by name (rootOf unwraps at every step)", anchor: "e = unwrap(e.expression); return e; };", to: "e = e.expression; return e; };", refused: ["p65-cast-launcher-computed.test.ts:4: THE INVARIANT: the census resolved the name leg here to the shared launcher's binding"] },
  ];
  for (const [i, m] of mutations.entries()) {
    assert.equal(source.split(m.anchor).length - 1, 1, "mutation " + i + " (clause " + m.clause + "): its anchor occurs once in scripts/browser-legs-census.mjs; a rewrite of the walker re-anchors this test: " + JSON.stringify(m.anchor));
    // the mutant runs as the CLI (--json over the synthetic root), the way the script runs the census: its refusals and exit 2
    const mutant = path.join(root, "vscode-extension", "scripts", "browser-legs-census-mutant-" + i + ".mjs");
    fs.writeFileSync(mutant, source.replace(m.anchor, m.to));
    const r = spawnSync(process.execPath, [mutant, "--json", root], { cwd: path.join(root, "vscode-extension"), encoding: "utf8" });
    assert.equal(r.status, 2, "mutation " + i + " (clause " + m.clause + "): the mutant census exits 2 (a refusal) over the plants; stderr: " + r.stderr);
    const out = JSON.parse(r.stdout) as { refusals: string[]; modules: Record<string, Rec> };
    for (const want of m.refused) assert.ok(out.refusals.some((x) => x.startsWith("ui/webview/" + want)), "mutation " + i + " (clause " + m.clause + "): the invariant refuses the road the mutation silenced, a refusal starting " + JSON.stringify(want) + "; the mutant's refusals: " + JSON.stringify(out.refusals));
    assert.deepEqual(out.modules[B("p01-alias.test.ts")].refusals, [], "mutation " + i + ": the plain aliased caller stays clean under the mutant (the invariant refuses the silenced road, not every module)");
  }
});

test("the script's --list-legs is the census's legs and its --check is green over the tree; the CLI's --tsv carries one line per module with the leg flag, the gap, the engines and the class", async () => {
  const { census, rosterGap, engineNames, classOf } = await load();
  const c = census(REPO);
  const list = spawnSync("bash", [SCRIPT, "--list-legs"], { cwd: EXT, encoding: "utf8" });
  assert.equal(list.status, 0, list.stderr);
  assert.deepEqual(list.stdout.split("\n").filter(Boolean).sort(), c.legs, "the script lists the census's legs (it runs the same module; the script prints them in the census's walk order over LEG_DIRS and census() returns them sorted, so the two are compared sorted)");
  const check = spawnSync("bash", [SCRIPT, "--check"], { cwd: EXT, encoding: "utf8" });
  assert.equal(check.status, 0, check.stderr);
  assert.match(check.stdout, /^ci-browser-legs: the roster and the tree agree: \d+ rostered, \d+ browser legs in the census/m, check.stdout);
  assert.equal(check.stderr, "", "nothing on stderr when the files and the tree agree");
  const tsv = spawnSync(process.execPath, [MODULE, "--tsv"], { cwd: EXT, encoding: "utf8" });
  assert.equal(tsv.status, 0, tsv.stderr);
  const rows = tsv.stdout.split("\n").filter(Boolean).map((l) => l.split("\t"));
  assert.equal(rows.length, c.byBundle.size, "one row per module read");
  for (const [bundle, flag, gap, engines, cls] of rows) {
    const r = c.byBundle.get(bundle) as Rec;
    assert.ok(r, bundle + " is a module the census read");
    assert.equal(flag, r.reaches ? "1" : "0", bundle + ": the leg flag");
    assert.equal(gap, (r.reaches || r.launcherImported ? rosterGap(r) : null) || "-", bundle + ": the gap");
    assert.equal(engines, engineNames(r).join(" and ") || "-", bundle + ": the engines");
    assert.equal(cls, classOf(r), bundle + ": the class");
  }
});

/** A synthetic root with the script and the census module in place, the extension's node_modules linked in (the compiler),
 *  a stub launcher, and the named plants copied from the fixtures; `run` writes the two files and runs the script's --check. */
function syntheticRoot(t: { after(fn: () => void): void }, plants: string[]) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "cbl-census-"));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const ext = path.join(root, "vscode-extension");
  for (const d of ["vscode-extension/scripts", "vscode-extension/src", "ui/webview"]) fs.mkdirSync(path.join(root, d), { recursive: true });
  fs.copyFileSync(SCRIPT, path.join(ext, "scripts", "ci-browser-legs.sh"));
  fs.copyFileSync(MODULE, path.join(ext, "scripts", "browser-legs-census.mjs"));
  fs.writeFileSync(path.join(ext, "package.json"), '{ "name": "synthetic" }\n');
  fs.symlinkSync(path.join(EXT, "node_modules"), path.join(ext, "node_modules"), "dir");
  fs.copyFileSync(STUB_LAUNCHER, path.join(root, "ui", "webview", "real-viewer-leg.ts"));
  for (const p of plants) { const row = PLANT_TABLE.find((x) => x.file === p) as Plant; fs.copyFileSync(path.join(PLANTS, row.dir, row.file), path.join(root, row.dir, row.file)); }
  const run = (roster: string, excluded: string) => {
    fs.writeFileSync(path.join(ext, ROSTER), roster);
    fs.writeFileSync(path.join(ext, EXCLUDED), excluded);
    return spawnSync("bash", [path.join(ext, "scripts", "ci-browser-legs.sh"), "--check"], { cwd: ext, encoding: "utf8" });
  };
  return { run, root };
}
const B = (file: string) => bundleOf(PLANT_TABLE.find((x) => x.file === file) as Plant);

test("the script's reading of the real census over a synthetic root: an aliased caller is rosterable; a rostered importer that never calls inBrowser is red with the keep-it remedy; a rostered leg that loads playwright itself, or skips or todos, or reaches WebKit, is refused with the census's sentence; a leg in neither file is named; a form the census refuses stops the script with file and line", (t) => {
  const { run } = syntheticRoot(t, ["p01-alias.test.ts", "p02-single-quote-require.test.ts", "p10-block-comment-mention.test.ts", "p25-launcher-loader.test.ts", "p20-todo.test.ts", "p19-default-core.test.ts"]);
  const P01 = B("p01-alias.test.ts"), P02 = B("p02-single-quote-require.test.ts"), P10 = B("p10-block-comment-mention.test.ts"), P25 = B("p25-launcher-loader.test.ts"), P20 = B("p20-todo.test.ts"), P19 = B("p19-default-core.test.ts");
  const rest = P02 + "\tlaunches on its own\n" + P25 + "\tlaunches on its own\n" + P20 + "\tskips on its own\n" + P19 + "\tlaunches WebKit; the gating job installs Chromium only\n";
  const ok = run(P01 + "\n", rest);
  assert.equal(ok.status, 0, "an aliased caller of the shared launcher is rosterable under the parsed gate; stderr: " + ok.stderr);
  assert.match(ok.stdout, /the roster and the tree agree: 1 rostered, 5 browser legs in the census/, ok.stdout);
  const refused = (r: ReturnType<typeof run>, ...needles: string[]) => {
    assert.equal(r.status, 1, "exit 1; stderr: " + r.stderr);
    for (const n of needles) assert.ok(r.stderr.includes(n), "stderr names " + JSON.stringify(n) + ":\n" + r.stderr);
    assert.ok(r.stderr.includes("no leg ran"), r.stderr);
  };
  refused(run(P01 + "\n" + P10 + "\n", rest), ROSTER + " line 2: '" + P10 + "' names no browser leg: ui/webview/p10-block-comment-mention.test.ts imports ui/webview/real-viewer-leg.ts and never calls its inBrowser through that import: call it, or remove the line");
  refused(run(P01 + "\n" + P25 + "\n", P02 + "\tlaunches on its own\n" + P20 + "\tskips on its own\n" + P19 + "\tlaunches WebKit; the gating job installs Chromium only\n"), ROSTER + " line 2: '" + P25 + "' does not launch through the one shared launcher (loads playwright itself (playwright): inBrowser owns the one playwright read a rostered leg needs): only inBrowser reads ROMP_BROWSER_LEGS_REQUIRE");
  refused(run(P01 + "\n" + P20 + "\n", P02 + "\tlaunches on its own\n" + P25 + "\tlaunches on its own\n" + P19 + "\tlaunches WebKit; the gating job installs Chromium only\n"), ROSTER + " line 2: '" + P20 + "' does not launch through the one shared launcher (holds a skip or todo of its own (line 3: .todo())");
  refused(run(P01 + "\n" + P19 + "\n", P02 + "\tlaunches on its own\n" + P25 + "\tlaunches on its own\n" + P20 + "\tskips on its own\n"), ROSTER + " line 2: '" + P19 + "' does not launch through the one shared launcher (never imports the shared launcher, ui/webview/real-viewer-leg.ts)");
  const neither = run(P01 + "\n", P02 + "\tlaunches on its own\n" + P25 + "\tlaunches on its own\n" + P20 + "\tskips on its own\n");
  refused(neither, "browser leg '" + P19 + "' is in neither " + ROSTER + " nor " + EXCLUDED + ": add it to " + EXCLUDED + " with a tab and the engine form its header admits, \"launches WebKit; the gating job installs Chromium only\"");
  const excludedImporter = run(P01 + "\n", rest + P10 + "\ta reason\n");
  refused(excludedImporter, EXCLUDED + " line 5: '" + P10 + "' names no browser leg: ui/webview/p10-block-comment-mention.test.ts imports ui/webview/real-viewer-leg.ts and never calls its inBrowser through that import: call it, or remove the line");
});

test("a rostered leg reaching an engine the gating job does not install is red naming the engine, from the census's engine read", (t) => {
  // p09b reaches Firefox and WebKit by a destructured binding and a bare property read, which no string spells
  const { run } = syntheticRoot(t, ["p01-alias.test.ts", "p09b-destructured-firefox-bare-webkit.test.ts"]);
  const P01 = B("p01-alias.test.ts"), P09B = B("p09b-destructured-firefox-bare-webkit.test.ts");
  const r = run(P01 + "\n" + P09B + "\n", "");
  assert.equal(r.status, 1, r.stderr);
  // the gate is read first (the leg never imports the launcher); the engine verdict is what the exclusions reason must carry
  assert.ok(r.stderr.includes(ROSTER + " line 2: '" + P09B + "' does not launch through the one shared launcher"), r.stderr);
  const excluded = run(P01 + "\n", P09B + "\tlaunches Firefox and WebKit; the gating job installs Chromium only\n");
  assert.equal(excluded.status, 0, excluded.stderr);
});

test("the script's reading of the real census over a pending line: allowed while the source is absent (counted on the agreement line); red naming no PR; once the source is present, red with the remedy derived from the source (a shared Chromium leg to the roster; an engine leg keeps the line with the engine form; a non-leg importer removes the line; an embedded driver keeps the line with the header's sentence; the fifth class, a Chromium-only leg that misses the gate, is the next test's) and never as in neither; and promotionOf, this file's copy of that rule, prints the script's sentence for each class", async (t) => {
  const mod = await load();
  const { run, root } = syntheticRoot(t, ["p01-alias.test.ts", "p19-default-core.test.ts", "p10-block-comment-mention.test.ts", "p26-embedded-driver.test.ts"]);
  const cs = mod.census(root);
  // promotionOf is otherwise evaluated only inside a failing assertion's message (guarded there by existsSync, since node:assert
  // builds the message eagerly): executed here over each present pending source against the sentence the script printed
  const agrees = (r: ReturnType<typeof run>, bundle: string) => assert.ok(r.stderr.includes("promote it: " + promotionOf(mod, cs.byBundle.get(bundle), bundle)), "promotionOf prints the script's remedy for " + bundle + " (" + promotionOf(mod, cs.byBundle.get(bundle), bundle) + "):\n" + r.stderr);
  const P01 = B("p01-alias.test.ts"), P19 = B("p19-default-core.test.ts"), P10 = B("p10-block-comment-mention.test.ts"), P26 = B("p26-embedded-driver.test.ts");
  const ABSENT = "out-tests/ui/webview/zz-absent-browser.test.js";
  const rest = P19 + "\tlaunches WebKit; the gating job installs Chromium only\n" + P26 + "\tloads playwright in a child process it drives from a string; the switch never reaches it\n";
  const absent = run(P01 + "\n", rest + ABSENT + "\tpending #999: a leg an open PR brings\n");
  assert.equal(absent.status, 0, "a pending line naming an absent source is allowed; stderr: " + absent.stderr);
  assert.match(absent.stdout, /the roster and the tree agree: 1 rostered, 3 browser legs in the census, 1 pending lines naming absent sources/, absent.stdout);
  const refused = (r: ReturnType<typeof run>, ...needles: string[]) => {
    assert.equal(r.status, 1, "exit 1; stderr: " + r.stderr);
    for (const n of needles) assert.ok(r.stderr.includes(n), "stderr names " + JSON.stringify(n) + ":\n" + r.stderr);
    assert.ok(!r.stderr.includes("is in neither"), "the arrived leg is not also called missing from both files:\n" + r.stderr);
  };
  refused(run(P01 + "\n", rest + ABSENT + "\tpending: a leg with no PR named\n"), EXCLUDED + " line 3: '" + ABSENT + "' has a pending reason that names no PR ('pending: a leg with no PR named'): a pending line reads 'pending #<PR>: <why>'");
  const shared = run("", rest + P01 + "\tpending #862: launches through inBrowser\n");
  refused(shared, EXCLUDED + " line 3: '" + P01 + "' is pending #862 and its source ui/webview/p01-alias.test.ts is in the tree, so the leg has arrived (#862 merged main, or this is #862's branch) and the line's condition has passed: promote it: delete this line and add '" + P01 + "' to " + ROSTER + " (the source launches through inBrowser alone and reaches no engine but Chromium), with the step's measured seconds in the PR body");
  agrees(shared, P01);
  // the engine remedy is held by includes() up to the form's closing quote, here and at the neither red in the fifth-remedy test
  // below: a tail appended AFTER the closing quote is not refused by these pins, since the quoted form is what a copy into the
  // exclusions carries and a tail outside it grants nothing, while a tail inside the form that carries a second claim (another
  // form's phrase, a second engine) is refused as ambiguous by the closed-set tests
  const engine = run(P01 + "\n", P26 + "\tloads playwright in a child process it drives from a string; the switch never reaches it\n" + P19 + "\tpending #859: launches on its own\n");
  refused(engine, "'" + P19 + "' is pending #859", "promote it: keep the line and replace the reason with the engine form the header of " + EXCLUDED + " admits, \"launches WebKit; the gating job installs Chromium only\"");
  agrees(engine, P19);
  const nonLeg = run(P01 + "\n", rest + P10 + "\tpending #861: a module\n");
  refused(nonLeg, "'" + P10 + "' is pending #861", "promote it: remove the line (the source reaches no browser by the census rule; imports ui/webview/real-viewer-leg.ts and never calls its inBrowser through that import: call it, or remove the line)");
  agrees(nonLeg, P10);
  const embedded = run(P01 + "\n", P19 + "\tlaunches WebKit; the gating job installs Chromium only\n" + P26 + "\tpending #863: a driver\n");
  refused(embedded, "'" + P26 + "' is pending #863", "promote it: keep the line and replace the reason with the embedded-driver sentence the header of " + EXCLUDED + " states");
  agrees(embedded, P26);
});

test("the fifth remedy class, executed in the script and in promotionOf: a pending line whose arrived source calls inBrowser beside a playwright load of its own (class both, Chromium alone) is red with the gate's own remedy, since no form of the exclusions admits such a leg; and a leg in neither file is red with the remedy derived from its source (the gate's for that leg, the engine form for a WebKit leg), never the bare add-or-exclude", async (t) => {
  const mod = await load();
  const { run, root } = syntheticRoot(t, ["p01-alias.test.ts", "p04-launch-persistent.test.ts", "p19-default-core.test.ts"]);
  const cs = mod.census(root);
  const P01 = B("p01-alias.test.ts"), P04 = B("p04-launch-persistent.test.ts"), P19 = B("p19-default-core.test.ts");
  const ENGINE_ROW = P19 + "\tlaunches WebKit; the gating job installs Chromium only\n";
  const gate = run(P01 + "\n", ENGINE_ROW + P04 + "\tpending #853: calls inBrowser beside a playwright load of its own\n");
  assert.equal(gate.status, 1, "exit 1; stderr: " + gate.stderr);
  const want = "promote it: pass the roster gate (the source loads playwright itself (playwright): inBrowser owns the one playwright read a rostered leg needs: launch through inBrowser alone, with no playwright, launch, skip or todo of the leg's own), then delete this line and add '" + P04 + "' to " + ROSTER + " with the step's measured seconds in the PR body: the exclusions admit no reason of its own, so a leg that reaches Chromium alone is rostered once it passes the gate";
  assert.ok(gate.stderr.includes("'" + P04 + "' is pending #853") && gate.stderr.includes(want), "the gate's remedy, not a reason no form admits:\n" + gate.stderr);
  assert.ok(!gate.stderr.includes("why the gating job does not run it"), "the old remedy, a bare gap sentence both checkers refuse as none of the four forms, is gone:\n" + gate.stderr);
  assert.ok(gate.stderr.includes("promote it: " + promotionOf(mod, cs.byBundle.get(P04), P04)), "promotionOf prints the script's sentence for the gate class:\n" + gate.stderr);
  assert.ok(!gate.stderr.includes("is in neither"), "the arrived leg is not also called missing from both files:\n" + gate.stderr);
  // the same two legs in neither file: each red carries the remedy its source derives
  const neither = run(P01 + "\n", "");
  assert.equal(neither.status, 1, neither.stderr);
  assert.ok(neither.stderr.includes("browser leg '" + P04 + "' is in neither " + ROSTER + " nor " + EXCLUDED + ": pass the roster gate (the source loads playwright itself (playwright)"), "the gate's remedy for the both-class leg:\n" + neither.stderr);
  assert.ok(neither.stderr.includes("browser leg '" + P19 + "' is in neither " + ROSTER + " nor " + EXCLUDED + ": add it to " + EXCLUDED + " with a tab and the engine form its header admits, \"launches WebKit; the gating job installs Chromium only\""), "the engine form for the WebKit leg:\n" + neither.stderr);
  assert.ok(!neither.stderr.includes("or to the exclusions with a tab and a reason"), "no bare add-or-exclude:\n" + neither.stderr);
  for (const b of [P04, P19]) assert.ok(neither.stderr.includes(": " + neitherRemedy(mod, cs.byBundle.get(b), b)), "neitherRemedy, this file's copy of the script's rule, prints the script's sentence for " + b + ":\n" + neither.stderr);
});

test("a form the census cannot classify stops the script with the file and line, judging nothing; without the compiler the census exits 1 naming CI's Shell job and the script stops the same way", (t) => {
  const { run } = syntheticRoot(t, ["p01-alias.test.ts", "p27-parse-error.test.ts"]);
  const P01 = B("p01-alias.test.ts");
  const r = run(P01 + "\n", "");
  assert.equal(r.status, 1, r.stderr);
  assert.ok(r.stderr.includes("browser-legs-census: REFUSED ui/webview/p27-parse-error.test.ts:4: the parser reports a diagnostic"), r.stderr);
  assert.ok(r.stderr.includes("the census refused a form it cannot classify (above, with file and line)") && r.stderr.includes("nothing else was judged and no leg ran"), r.stderr);
  assert.ok(!r.stderr.includes("is in neither"), "nothing else is judged over a refusal:\n" + r.stderr);
  // no compiler: a copy of the module under a vscode-extension with no node_modules
  const bare = fs.mkdtempSync(path.join(os.tmpdir(), "cbl-bare-"));
  t.after(() => fs.rmSync(bare, { recursive: true, force: true }));
  fs.mkdirSync(path.join(bare, "vscode-extension", "scripts"), { recursive: true });
  fs.mkdirSync(path.join(bare, "ui", "webview"), { recursive: true });
  fs.copyFileSync(MODULE, path.join(bare, "vscode-extension", "scripts", "browser-legs-census.mjs"));
  fs.copyFileSync(SCRIPT, path.join(bare, "vscode-extension", "scripts", "ci-browser-legs.sh"));
  fs.writeFileSync(path.join(bare, "vscode-extension", "package.json"), '{ "name": "bare" }\n');
  fs.copyFileSync(STUB_LAUNCHER, path.join(bare, "ui", "webview", "real-viewer-leg.ts"));
  fs.copyFileSync(path.join(PLANTS, W, "p01-alias.test.ts"), path.join(bare, "ui", "webview", "p01-alias.test.ts"));
  const cli = spawnSync(process.execPath, [path.join(bare, "vscode-extension", "scripts", "browser-legs-census.mjs"), "--tsv"], { cwd: path.join(bare, "vscode-extension"), encoding: "utf8" });
  assert.equal(cli.status, 1, "exit 1, not a refusal (2) and not a census: " + cli.stderr);
  assert.equal(cli.stdout, "", "nothing judged: no module line, not even the leg that is there");
  assert.ok(cli.stderr.includes("the typescript compiler is not installed under vscode-extension/node_modules") && cli.stderr.includes("npm ci") && cli.stderr.includes("Shell job") && cli.stderr.includes("tools/ci-browser-legs.test.mjs"), cli.stderr);
  fs.writeFileSync(path.join(bare, "vscode-extension", ROSTER), B("p01-alias.test.ts") + "\n");
  fs.writeFileSync(path.join(bare, "vscode-extension", EXCLUDED), "");
  const sh = spawnSync("bash", [path.join(bare, "vscode-extension", "scripts", "ci-browser-legs.sh"), "--check"], { cwd: path.join(bare, "vscode-extension"), encoding: "utf8" });
  assert.equal(sh.status, 1, sh.stderr);
  assert.ok(sh.stderr.includes("the typescript compiler is not installed") && sh.stderr.includes("the census did not run (exit 1, above), so nothing was judged and no leg ran"), sh.stderr);
  assert.equal(sh.stdout, "", "no agreement line and no legs listed");
});

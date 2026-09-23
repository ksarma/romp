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
// to the roster's creation commit: this test reads the commit from the header, fetches it at depth 1 only when the checkout is
// itself shallow (CI's depth-1 checkout) and lacks it (a fetch that fails is a red hold-off, never a pass; a full clone that lacks
// it takes a red naming the bound line, with no fetch, since a depth fetch would make the whole store shallow, and a scratch-clone
// test drives both arms) and refuses a row carrying the sentence whose source is not in the tree at
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
// to R5_LAST: the eleven silent forms the round-4 review named and the tagged-template loader its verifiers found, each planted with THE
// SAFETY NET's refusal as its outcome until a fold reads the form, the fold's sentence or class once one does, with one net-only row
// per kind of mention the net names and, since round 6, one per position specHolder reads and per spelling of the createRequire hit
// that had none (p246 to p248: the package's name in an array literal that is a call's argument, as a new expression's argument, and
// the member createRequire with a const specifier, each refused by the net before round 6 and silenced by the deletion of its arm
// alone, which no fixture row caught), so every arm of the net keeps a plant, and the controls and pin rows the folds bring; then the
// string-typed parameter passed back to its own function, under which the census before round 5 died whole with a bare RangeError, so
// those rows red as census(PLANTS) throwing rather than as a row mismatch, beside its non-cyclic control; then a helper's own engine,
// skip or swallow, dropped before round 5 from the record of a test that calls inBrowser itself and folded into it since, beside the
// direct, helper-only and non-launcher controls; then the name positions (a class, interface or enum member, an accessor, a type
// parameter, a label) and the satisfies or angle-bracket assertion peels under which the value-use arm refused a launcher binding
// falsely before round 5, beside the computed-name and initializer controls that stay refused and the two whose sentence improved;
// then the spawned-driver file, the third residual's stated boundary, beside its fork twin and the control that imports the driver
// and is refused; then, from the closing pass after the round's verification, the loader specifier bound by a let or var the module
// writes to after its declaration, folded to the declaration's text before and loading the package or the launcher silently, refused
// now as folding through no closed form, beside its never-written control), every one
// is red under the census before round 5 (the module at
// the round-4 head) unless the table names it held with its reason, and the same test holds the table to that statement. Of the
// round-6 rows (R6_FIRST to R6_LAST, p249 onward, past the round-5 range: a function parameter or an inner declaration sharing a
// module const's name, which the specifier fold read as that const before round 6, so a playwright package or the launcher passed in
// through the parameter loaded with class none and no refusal under the census and under the net alike, beside the literal control,
// whose refusal moves from the net's sentence at the call to the walker's at the function line, and the renamed-parameter control,
// and, from the closing pass after the round's verification, a parameter shadowing an unwritten let and a destructured parameter
// sharing a const's name, silent the same way before round 6, beside the catch variable sharing a const's name, a pin of the fold's
// catch-variable arm, refused through no closed form before round 6 by the by-name read's two declarations and, at the round-6 head
// before the closing pass, as loading a placeholder that names no file, the wrong reason; a
// loader or a playwright binding handed on as a parameter's default value, which both isName tests exempted as a name position
// before round 6, the loader silent and the binding's WebKit launch unread beside a read Firefox engine, beside the name-position and
// argument-position controls; and a playwright load in a position the walker does not read, a class field, an object property, a
// promise callback, an argument or a return, unread beside a read engine before round 6 since the read-through clause is per module
// and refused by name now through a position predicate over every unread position, beside the read-position controls, with the
// three round-3 rows for the field, the property and .then re-aimed in place to its sentence; a test calling inBrowser directly and
// through a barrel that re-exports it with an engine, class shared with the barrel's engine lost before round 6 and refused at the
// barrel's import since, whatever the test's own calls, beside the barrel-only control p32, which keeps the launcherBinds sentence;
// and a specifier assembled from literals, joined with a slash before round 6 as if a path, so the package or the launcher so spelled
// was refused for the wrong reason and a relative chain resolved to a decoy at the slash-joined path silently, folded since by
// concatenation when the chain crossed no path call, beside the literal control and the path-call control, and the chain nested
// inside a path call's argument, joined piece by piece before and after, the boundary the closing pass stated; and a shared inBrowser
// call whose rejection is swallowed by a spelling other than a try statement of the same function, the call's promise handed to
// .catch, to .then's second argument or to Promise.allSettled, directly, through a chain of .then and .finally, or as a parenthesized
// element of the array literal, the call inside a callback lexically inside a try, or a helper's such call folded at the import line,
// each read as no swallow before round 6, when the read was the same-function try alone, beside the .finally and bare .then controls,
// the Promise.all control, the wrapper-in-try residual the census header states and the never-awaited try, which reads as a swallow
// before and after, and the two spellings the closing pass stated as residuals beside the wrapper's, a .catch on a name the promise
// was bound to and on a Promise.all over the call, swallow [] before and after; and, from the review's round 7, in the same range, a
// const or var declared in a switch's case block, a namespace body or a class static block that shares a module const's name, read
// as the module const at the round-6 head (a silent Firefox leg, the package or the launcher loaded through it class none with no
// refusal), beside the two var stop controls, a var in a namespace body or a static block hoisted to the module and refused
// falsely there, and a declaration with no initializer (a for-of or for-in head's const, a for-of let, an ambient declare const, a
// let never written) refused as loading a placeholder that names no file, the wrong reason, beside the catch variable, the
// class's control; and a module named like the launcher loaded through a path call or a placeholder chain, bound as the launcher by
// its spelling before round 7 (class shared, gap null, no refusal) and resolved since, beside the real launcher through the same
// path call, with the placeholder splitting the launcher's name and the launcher's .cjs twin, read as the launcher before round 7
// and by its own content since; and a playwright package's or the launcher's name bound to a name, returned from a function, held
// in an object literal that is a call's argument or standing in a conditional's branch or a logical's operand as one, handed to a
// callee the walker knows no loader for, class none with no refusal before round 7 and refused by THE SAFETY NET since, beside the
// literal control, the controls of the clause's own reading and the boundaries the census header states; and Promise.allSettled
// over a name an array holding a shared inBrowser call was bound to, or over a spread of that name, swallow [] before and after,
// the two witnesses the review's round 7 added to the rule the census header's swallow clause states; and a specifier spelled with
// a script suffix, read since round 7 by the bundler's mapping: a .cjs or .mjs spelling that names no file, read as the .ts beside it
// before (the launcher bound, class shared, gap null, no refusal) where the bundler loads the .cts or the .mts twin, which launches
// Firefox, the .cjs row in a plants root of its own since the main tree's .cjs twin stands at that spelling; a .js spelling whose
// .tsx the bundler loads and a .jsx spelling of the launcher, each refused as naming no file before; a .jsx module loaded as spelled,
// skipped as no script before, class none with no refusal; a .js spelling beside a declaration file alone, read as the
// declaration before, which the bundler never loads; and a .js spelling with a .js beside the launcher, bound as the launcher
// before round 7 when the .ts came first), every one is red under
// the census before round 6 (the module at the round-5 head) unless the table names it held with its reason, and the same test holds
// the table to that statement. A module
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
  loadTypescript(): any;   // the census's own compiler load (vscode-extension/node_modules/typescript), read by the identifier census over the net block
  isLexicalScope(ts: any, n: any): boolean;   // classify's isScope, the lexical read's scope set (round 7), pinned against the binder below
  holdsVarScope(ts: any, n: any): boolean;    // classify's holdsVarsOf, the scopes that hold a var (round 7)
};
const load = (): Promise<Census> => import(pathToFileURL(MODULE).href) as Promise<Census>;
const read = (p: string): string => fs.readFileSync(p, "utf8");
/** The census module's LEADING comment block, its // lines before the first line of code joined with spaces (a sentence moved into a
 *  body comment does not satisfy a pin over it; a wrapped clause reads as one line). The header pins of the plants test and the
 *  identifier census read the header through this. */
const moduleHeader = (): string => {
  const lines = read(MODULE).split("\n");
  const codeAt = lines.findIndex((l) => !l.startsWith("//") && l.trim() !== "");
  return lines.slice(0, codeAt < 0 ? lines.length : codeAt).filter((l) => l.startsWith("//")).map((l) => l.replace(/^\/\/ ?/, "")).join(" ");
};
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
  t.diagnostic("rosterable by the gate: " + count((r) => rosterGap(r) === null) + "; legs importing the launcher and never calling it: " + count((r) => !!r.launcherImported && r.sharedCalls === 0) + "; shared calls whose rejection is swallowed (a try with a catch, .catch, .then's second argument or Promise.allSettled; admitted, reported): " + count((r) => (r.swallow || []).length > 0) + "; legs with a skip or todo: " + count((r) => (r.skipTodo || []).length > 0) + "; own launches: " + recs.reduce((n, r) => n + (r.launches || []).length, 0) + " sites in " + count((r) => (r.launches || []).length > 0) + " modules");
});

/** What each planted form is: the fixture's file under tests/fixtures/browser-legs-plants/<dir> (under <root>/<dir> when the row
 *  names a root: a plants root of its own, a directory of the fixture tree beside ui/ and vscode-extension/ with its own stub
 *  launcher, read by census() over that root, for a shape the main tree cannot carry; p370's .cjs spelling reaches a .cts only where
 *  no .cjs stands, and the main tree's .cjs twin, p348 and p349, stands there), and the verdict the census
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
  dir: string; root?: string; file: string; leg: boolean; cls: string; gap: string | null; engines?: string[]; playwright?: string[];
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
/** THE BOUND-NAME clause's sentences (the review's round 6, extra6-1, built in round 7), as the census emits them (read from a run of
 *  the CLI over the plants, not guessed): after NET_HEAD, what the text names, the name it is bound to (or the target it is written
 *  to, or the return it leaves by) and the line of the first reference no fold of the walker read. The round-7 rows hold the SENTENCE
 *  through these constants: a reword of the module's clause moves them and the rows through them. No piece is a package's name
 *  standing alone, for the reason the constants above give: this module is itself a module of the tree the census reads, and a name
 *  bound to such a text is what the clause refuses. NET_PW_CORE is NET_PW's sentence for the other package the p344 and p356 rows
 *  name first. */
const NET_BOUND_PW = (name: string, line: number) => "a playwright package's name bound to " + name + " and read at line " + line + " where no fold of the walker accounts for it: \"playwright\"";
const NET_BOUND_PW_CORE = (name: string, line: number) => "a playwright package's name bound to " + name + " and read at line " + line + " where no fold of the walker accounts for it: \"playwright-core\"";
const NET_BOUND_LAUNCHER = (name: string, line: number) => "the launcher module's name bound to " + name + " and read at line " + line + " where no fold of the walker accounts for it: \"./real-viewer-leg\"";
const NET_BOUND_EXPORTED = (name: string) => "a playwright package's name bound to " + name + " and exported: \"playwright\"";
const NET_BOUND_TARGET = (target: string) => "a playwright package's name bound to " + target + ", whose references the walker does not read: \"playwright\"";
const NET_RETURNED = "a playwright package's name returned from a function, whose callers the walker does not follow: \"playwright\"";
const NET_PW_CORE = "a playwright package specifier: \"playwright-core\"";
const NET_CR = (spelled: string) => "createRequire in a position the walker does not fold (not a declaration's own name or an import's, the callee of a call bound as a loader or applied as one, or the object of a member other than call, apply or bind): \"" + spelled + "\"";
const NET_MODREQ = "module.require, a loader, in a position the walker does not read (not called): \"module.require\"";
const NET_DRIVER = "a playwright package specifier inside a string's text read as code: ";
const NET_NMPW = "a relative path into node_modules naming a playwright package: \"../../vscode-extension/node_modules/playwright\"";
const NET_READ_THROUGH = "the census read no engine and no launch through the playwright package it loads (playwright), so the load or its binding is handed on where the walker does not read and the engines and launches reached through it are unread: bind the load to a name in a statement of its own and launch on that name";
const MORE = (n: number) => "; and " + n + " more mention" + (n > 1 ? "s" : "");
/** The launcher value-use arm's sentence with the position handedHow names (the extra5-5 rows hold the position's text). */
const HAND = (position: string) => "the launcher's module binding handed on as a value (" + position + ")";
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
const HOW_DEFAULT = "as a parameter's default value";   // round 6 (extra5-1, extra5-2): valueHandedHow's name for a Parameter's initializer, one home for the loader arm, the createRequire arm and the playwright-binding arm
const PW_HANDOFF = (name: string, how: string) => "a playwright binding (" + name + ") handed on as a value (" + how + "), so the engines and launches reached through it are unread by the walker: launch on the binding where it is bound, or bind the load in the module that launches";
const COMPOUND_PLAYWRIGHT = "a playwright load or binding bound by a compound assignment the walker does not follow (which value the name takes is unread): bind it with = in a statement of its own";
const COMPOUND_LAUNCHER = "the shared launcher loaded by a compound assignment the walker does not follow, so where inBrowser is called from is unread: bind the load with = in a statement of its own";
const WRITE_REFUSAL = (module: string, name: string, what: string) => "a " + module + " binding (" + name + ") written with " + what + ", which the walker does not follow: a call through the rebound name would count as a call through the binding while what the name holds is unread: bind the load once, or give the other value a name of its own";
/** The loader-specifier refusal's WHOLE sentence after "<file>:<line>: " and before ": <code>", as the census emits it (read from a
 *  run of the CLI over the plants, not guessed): the closing pass after round 5's rows p237 to p244 hold the SENTENCE through this
 *  constant (p14 holds its prefix and stays where it is); a reword of the module's refusal moves the constant and the rows through it. */
const SPEC_NO_CLOSED_FORM = "a loader whose specifier is not a string literal and folds through no closed form (refused, on the safe side)";
/** The load-position arm's sentences (round 6, extra5-3), as the census emits them (read from a run of the CLI over the plants, not
 *  guessed): a playwright package loaded where it stands in a position the walker does not read is refused by name with the position
 *  (valueHandedHow's parenthetical, HOW_CLASS_FIELD its round-6 branch) or, for a promise member, the callback sentence. The p268 to
 *  p274 rows and the re-aimed p50, p51 and p57 hold the SENTENCE through these constants: a reword of the module's arm moves the
 *  constants and the rows through them. */
const HOW_CLASS_FIELD = "held in a class field";
const PW_LOAD_HANDED = ", so the engines and launches reached through the load are unread by the walker: bind the load to a name in a statement of its own and launch on that name";
const PW_LOAD_HANDOFF = (how: string) => "a playwright package loaded where it stands and handed on (" + how + ")" + PW_LOAD_HANDED;
const PW_LOAD_THEN = "a playwright package loaded where it stands and handed to a promise callback through .then" + PW_LOAD_HANDED;
/** The barrel arm's sentence after "<file>:<line>: " (round 6, D, correctness-2), as the census emits it (read from a run of the CLI
 *  over the plants, not guessed): a loaded module that re-exports the launcher's inBrowser (named, renamed or export * from the
 *  launcher: launcherReexport, carried in its record since round 6) refuses the importer at the import line WHATEVER the importer's
 *  own calls, since a call made through the re-export, and the engine it passes, resolves to no launcher binding the walker counts.
 *  Before round 6 the only arm for such a module was launcherBinds, gated on the importer's shared calls being zero, so a test calling
 *  inBrowser directly AND through the barrel was class shared, gap null, engines [], the barrel's engine lost. p280 to p284 hold the
 *  SENTENCE through this constant; p32, the barrel-only control, keeps the launcherBinds arm's sentence, which fires first. */
const BARREL_REEXPORT = (chain: string) => "loads " + chain + ", which re-exports the shared launcher's inBrowser, so a call this module makes through that export, and the engine it passes, is unread";
/** The launcherBinds arm's WHOLE sentence after "<file>:<line>: ", as the census emits it (read from a run of the CLI over the plants):
 *  a loaded module that binds or calls the launcher's inBrowser, imported by a test that never calls inBrowser itself. p288 to p290
 *  (round 6, F) hold the SENTENCE through this constant at the module their folded chain names; p32's row holds the sentence's head as
 *  a literal of its own. */
const LAUNCHER_BINDS = (chain: string) => "loads " + chain + ", which binds or calls the shared launcher's inBrowser, so this module may launch through it without the census seeing a call";
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
  { dir: W, file: "p50-class-field-loader.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: [], launches: [], playwright: ["playwright"], refused: "p50-class-field-loader.test.ts:2: " + PW_LOAD_HANDOFF(HOW_CLASS_FIELD) }, // correctness-1: a class field holding the loader result; the package is recorded where it is resolved, the launch through the field is not derived; round 2 accepted the record as recorded-unread, round 5's safety net refused it by the read-through clause (a load with no engine and no launch read through it), and since round 6 the load-position arm refuses the LOAD by name at the same line, the position named (extra5-3), the net standing down
  { dir: W, file: "p51-object-property-loader.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: [], launches: [], playwright: ["playwright"], refused: "p51-object-property-loader.test.ts:2: " + PW_LOAD_HANDOFF(HOW_LITERAL) }, // correctness-1: an object property holding it (round 5: refused by the read-through clause, as p50; round 6: the load-position arm's sentence, as p50)
  { dir: W, file: "p52-wrapper-return.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p52-wrapper-return.test.ts:2: THE INVARIANT: the census resolved the shared launcher (./real-viewer-leg) here and its record carries nothing of the load" }, // correctness-1's wrapper return: the load stands in a position the walker does not read, refused by the invariant (before it: class none, no refusal, a false gap sentence)
  { dir: W, file: "p53-createrequire-direct-pw.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: ["chromium"], playwright: ["playwright"], launches: [".launch("] }, // extra6-1: createRequire(__filename)("playwright"), the loader applied directly
  { dir: W, file: "p54-createrequire-direct-launcher.test.ts", leg: true, cls: "shared", gap: null, launcherImported: true },       // extra6-1: the same for the launcher, destructured
  { dir: W, file: "p55-requirecjs-unbound.test.ts", leg: true, cls: "own", gap: "never calls its inBrowser through that import", engines: ["chromium"], playwright: ["playwright"], launches: [".launch("], launcherImported: true }, // extra7-1: requireCjs("playwright").chromium.launch() on the launcher's own loader, unbound
  { dir: W, file: "p56-await-import-unbound.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: ["chromium"], playwright: ["playwright"], launches: [".launch("] }, // extra7-1: (await import("playwright")).chromium.launch()
  { dir: W, file: "p57-import-then.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: [], launches: [], playwright: ["playwright"], refused: "p57-import-then.test.ts:2: " + PW_LOAD_THEN }, // extra7-1: import("playwright").then(pw => ...): the package is recorded, the launch on the callback's parameter is not derived (round 5: refused by the read-through clause, as p50; round 6: the load-position arm's promise-callback sentence)
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
  // net-only rows (round 5's folds): one row per kind of mention the net names whose planted forms the folds now read, and, since round
  // 6, one per position specHolder reads and per spelling of the createRequire hit (p246 to p248, at the round-5 range's end), so every
  // arm of the net keeps a plant that reds when it is silenced; each is a form no fold reads, and each is a stated false refusal of the
  // p74 class (the walker reaches no browser through it) or a silent form the round's rulings fold nowhere
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
  // fresh-1 (round 5): a test that calls inBrowser itself AND loads a helper that binds or calls the launcher was class shared, gap null,
  // with the helper's own record dropped (engines [], swallow [], skipTodo []), rosterable as Chromium-only while the helper reached
  // Firefox, skipped or swallowed; the helper-only twin of the same import was refused. census() now folds each record the walk over
  // an import passed without a refusal into the test's (foldLoaded), gated per record on the module binding or calling the launcher:
  // the engines as the sorted union, a swallow at the test's import line, a skip or todo at the import line naming the helper and its
  // line. The rows below red under the census before round 5 on the folded field (the round's records: the same fixtures over a root
  // of their own under that census, engines [], skipTodo [], swallow [], no refusal), the three controls hold: the engine passed by the
  // module itself, the helper-only twin still refused, and a UI helper whose { todo: } object literal the gate keeps out of the test's
  // record (ungated, the fold put a production module's todo property on two importers of the tree, a record change the --tsv hides)
  { dir: W, file: "p208-qf1a-helper-engine.test.ts", leg: true, cls: "shared", gap: null, engines: ["firefox"] }, // qf1a: inBrowser(t, body) beside inFirefox(t, body) from ff-helper.ts, whose inBrowser call passes "firefox": the helper's engine folded into the test's record (before round 5: class shared, gap null, engines [], no refusal)
  { dir: W, file: "p209-qf1b-helper-skip.test.ts", leg: true, cls: "shared", gap: "holds a skip or todo of its own (line 3: .skip( in ui/webview/skip-helper.ts:3, which this module loads)", skipTodo: [".skip( in ui/webview/skip-helper.ts:3, which this module loads"] }, // qf1b: the helper calls t.skip("...") before its shared call: the skip folded at the test's import line, naming the helper and its line, so the roster gate's sentence points at it (before: gap null, skipTodo [])
  { dir: W, file: "p210-qf1c-helper-swallow.test.ts", leg: true, cls: "shared", gap: null, swallow: [3] }, // qf1c: the helper's shared call sits inside try/catch: a swallow at the test's import line, reported as the module's own would be (before: swallow [])
  { dir: W, file: "p211-qf1f-chain-helper-engine.test.ts", leg: true, cls: "shared", gap: null, engines: ["firefox"] }, // qf1f: inFirefox reached through chain-helper.ts, a barrel that re-exports it and binds nothing of the launcher itself: the gate is per visited record, so the chain folds through the carrier and ff-helper's engine lands (before: engines [])
  { dir: W, file: "p212-qf1d-direct-engine-control.test.ts", leg: true, cls: "shared", gap: null, engines: ["firefox"], holds: "a shape another plant carries: p77 (an engine literal passed to inBrowser by the module itself), the direct half of p208's pair, green before and after round 5 with engines [firefox] read from the module's own call, which the fold does not touch" }, // qf1d: the direct-engine control
  { dir: W, file: "p213-qf1e-helper-only-control.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p213-qf1e-helper-only-control.test.ts:2: loads ui/webview/ff-helper.ts, which binds or calls the shared launcher's inBrowser", holds: "a shape another plant carries: p33 (a helper that calls the launcher, loaded by a test that never calls inBrowser itself), the helper-only twin of p208's import, refused before and after round 5: the fold is asked only of a walk that refused nothing, so this row pins that the refusal stands beside p208's fold of the same helper" }, // qf1e: the helper-only control
  { dir: W, file: "p214-qf1h-non-launcher-todo-prop-control.test.ts", leg: true, cls: "shared", gap: null, engines: [], skipTodo: [], holds: "a stated residual boundary: the fold's gate, a loaded module that neither binds nor calls the launcher carries nothing into the test's record; this row loads a UI helper whose { todo: t } object literal the walker's skip/todo read takes as a todo in the helper's own record, and stays class shared, gap null, skipTodo [] before and after round 5 (green before because nothing was folded, green after because the gate keeps the helper out; ungated, the fold put such a property on two importers of the tree, a record change the --tsv hides and the roster gate reds for a shared leg)" }, // qf1h: inBrowser(t, body) beside rows() from todo-prop-helper.ts, a UI helper that never touches the launcher and pushes { todo: t }: the walker's skip/todo read takes that property as a todo in the helper's own record, and the gate keeps it out of the test's (before: the same, nothing folded)
  // extra5-5 (round 5): the launcher value-use arm refused a NAME position and a peeled satisfies or angle-bracket assertion as a
  // hand-on, naming the node kind (a false refusal, never silent). p215 to p229 each hold a launcher namespace binding in such a
  // position beside a counted leg.inBrowser call: refused at :3 under the census before round 5 with the kind in the sentence
  // (MethodDeclaration, PropertyDeclaration, GetAccessor, SetAccessor, PropertySignature, MethodSignature, EnumMember,
  // LabeledStatement with BreakStatement or ContinueStatement, FirstNode for the two dotted names, TypeParameter, SatisfiesExpression,
  // TypeAssertionExpression, and the requireCjs loader's own sentence for p229), class shared with no refusal now: the rows red on
  // a refusal they do not expect. The controls: p230 (a computed name) and p231 (a member's initializer) stay refused with the kind
  // named, before and after (held: pins of handedHow's position-naming arm, which no earlier row carried); p232 (inBrowser read
  // under satisfies without a call) and p233 (the import = alias, a dotted name outside a type) stay refused with a sentence that
  // improved, so they red on the sentence; the type-node gate on the dotted name is load-bearing: under a blanket QualifiedName
  // exemption p233 is class none with the never-calls gap and NO refusal while ib(t, ...) runs the launcher (measured, round 5).
  { dir: W, file: "p215-e01-class-method.test.ts", leg: true, cls: "shared", gap: null, launcherImported: true },            // class H { leg() {} }: a method's name spelled like the binding (before: refused, MethodDeclaration)
  { dir: W, file: "p216-e02-class-property.test.ts", leg: true, cls: "shared", gap: null, launcherImported: true },          // class H { leg = 1 }: a property's name (before: refused, PropertyDeclaration)
  { dir: W, file: "p217-e03-get-accessor.test.ts", leg: true, cls: "shared", gap: null, launcherImported: true },            // get leg() (before: refused, GetAccessor)
  { dir: W, file: "p218-e04-set-accessor.test.ts", leg: true, cls: "shared", gap: null, launcherImported: true },            // set leg(v) (before: refused, SetAccessor)
  { dir: W, file: "p219-e05-property-signature.test.ts", leg: true, cls: "shared", gap: null, launcherImported: true },      // interface Cfg { leg: string } (before: refused, PropertySignature)
  { dir: W, file: "p220-e06-method-signature.test.ts", leg: true, cls: "shared", gap: null, launcherImported: true },        // interface Cfg { leg(): void } (before: refused, MethodSignature)
  { dir: W, file: "p221-e07-enum-member.test.ts", leg: true, cls: "shared", gap: null, launcherImported: true },             // enum E { leg } (before: refused, EnumMember)
  { dir: W, file: "p222-e08-label-break.test.ts", leg: true, cls: "shared", gap: null, launcherImported: true },             // leg: for (;;) { break leg } (before: refused twice, LabeledStatement and BreakStatement)
  { dir: W, file: "p223-e09-label-continue.test.ts", leg: true, cls: "shared", gap: null, launcherImported: true },          // leg: for (...) { continue leg } (before: refused twice, LabeledStatement and ContinueStatement)
  { dir: W, file: "p224-e10-type-qualifier.test.ts", leg: true, cls: "shared", gap: null, launcherImported: true },          // const o: leg.Opened | null: a dotted name rooted in a type reference (before: refused, FirstNode)
  { dir: W, file: "p225-e11-typeof-qualifier.test.ts", leg: true, cls: "shared", gap: null, launcherImported: true },        // let f: typeof leg.pageHtml: a dotted name rooted in a type query (before: refused, FirstNode)
  { dir: W, file: "p226-e12-type-parameter.test.ts", leg: true, cls: "shared", gap: null, launcherImported: true },          // function g<leg>(x: leg): leg: a type parameter's name (before: refused, TypeParameter)
  { dir: W, file: "p227-e13-satisfies-peel.test.ts", leg: true, cls: "shared", gap: null, launcherImported: true },          // (leg satisfies object).pageHtml(): a member read through satisfies (before: refused, SatisfiesExpression)
  { dir: W, file: "p228-e14-angle-assertion-peel.test.ts", leg: true, cls: "shared", gap: null, launcherImported: true },    // (<any>leg).pageHtml(): a member read through an angle-bracket assertion (before: refused, TypeAssertionExpression)
  { dir: W, file: "p229-e15-requirecjs-satisfies-peel.test.ts", leg: true, cls: "shared", gap: null, launcherImported: true }, // (requireCjs satisfies Function)("node:path"): the loader called through satisfies (before: refused as handed on, not called)
  { dir: W, file: "p230-c01-computed-name.test.ts", leg: true, cls: "shared", gap: null, launcherImported: true, refused: "p230-c01-computed-name.test.ts:3: " + HAND("in a position the walker does not read (ComputedPropertyName)"), holds: "a pin of an arm no plant carried: handedHow's position-naming arm, which names the node kind of a position no other clause reads, refused this row's computed class-member name [leg]() at the round-4 head and refuses it now: a computed name is not a name position (the identifier is read as a value for the key), so the round-5 exemption does not reach it; no earlier row held that arm, so this row is green under the census before round 5 and pins the exemption's edge" }, // class H { [leg]() {} }: the control for the name-position exemption, refused before and after
  { dir: W, file: "p231-c02-initializer.test.ts", leg: true, cls: "shared", gap: null, launcherImported: true, refused: "p231-c02-initializer.test.ts:3: " + HAND("in a position the walker does not read (PropertyDeclaration)"), holds: "a pin of an arm no plant carried: handedHow's position-naming arm refused this row's class-member initializer x = leg at the round-4 head and refuses it now: the exemption is keyed on the member's NAME being the identifier (p.name === n), and an initializer hands the binding on; green under the census before round 5, a pin of the exemption's edge (a row spelling leg = leg would not discriminate, since refuse() dedupes two refusals of one line's text)" }, // class H { x = leg }: the control for the initializer, refused before and after
  { dir: W, file: "p232-c03-satisfies-inbrowser-read.test.ts", leg: true, cls: "shared", gap: null, launcherImported: true, refused: "p232-c03-satisfies-inbrowser-read.test.ts:3: " + HAND("read for inBrowser without a call") }, // const x = (leg satisfies object).inBrowser: the peel reaches the member read, and the refusal names what the line holds (before: refused as a SatisfiesExpression position, the sentence the row does not hold)
  { dir: W, file: "p233-c04-import-equals-alias.test.ts", leg: false, cls: "none", gap: "never calls its inBrowser through that import", launcherImported: true, refused: "p233-c04-import-equals-alias.test.ts:3: " + HAND("aliased by a dotted name outside a type (an import = declaration or another non-type position), which the walker does not follow: import the launcher and call its inBrowser") }, // import ib = leg.inBrowser; ib(t, ...): a dotted name rooted in no type node stays refused, readably (before: refused as FirstNode, the enum alias ts.SyntaxKind prints for QualifiedName); under a blanket QualifiedName exemption this row is silent
  // correctness-4 (round 5): the third residual's stated boundary, a driver held in a separate file of the tree that the test spawns
  // by path. A spawn is no load, so the file is unread: class none, no refusal, under the census before round 5 and now, and the
  // header names the form beside the other three (the residual pin below holds the sentence). The companions spawn-driver.mjs
  // (createRequire, require of playwright, a Chromium launch) and fork-driver.ts (a Firefox import and launch) are outside
  // census() and this table's enumeration (not .test.ts). p236 imports the same driver the spawn test spawns and is refused as
  // loading a module that names a playwright package: the boundary is exactly load against spawn.
  { dir: W, file: "p234-c4a-spawn-driver-file.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, holds: "a stated residual boundary: the third residual's driver held in a separate file of the tree that the test spawns by path (spawnSync(process.execPath, [path.join(__dirname, the driver)]); a spawn is no load, so the file is unread), class none, no refusal, which the census before round 5 also gives; the spawn-reading capability was not taken in a landing round" }, // the spawned-driver file, a stated boundary
  { dir: W, file: "p235-c4b-fork-url-driver.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, holds: "a stated residual boundary: the third residual's driver in a separate file, reached by fork(new URL(the driver, import.meta.url)), the second witness of the same rule (a fork is no load), class none, no refusal, which the census before round 5 also gives" }, // the fork-by-URL twin
  { dir: W, file: "p236-c4z-imports-driver-control.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p236-c4z-imports-driver-control.test.ts:2: loads ui/webview/spawn-driver.mjs, which names a playwright package (playwright)", holds: "a shape another plant carries: p34 (a loaded module that names a playwright package, refused at the importer), the load half of p234's boundary: importing the driver the spawn test only spawns is refused before and after round 5, so the boundary is exactly load against spawn" }, // import "./spawn-driver.mjs": the control, refused before and after
  // the closing pass after round 5 (the round's verifiers' finding): a loader's specifier bound by a let or var the module WRITES to
  // after its declaration was folded to the declaration's text, so `let spec = "./decoy-helper"; spec = "playwright"; require(spec)`
  // loaded the decoy to the walker and the package at run time: class none, no refusal, under the census before round 5 and under the
  // net alone alike (the net reads no assignment's right side, and a load through a name is the walker's fold), the one silent form
  // of the round's press that the head passed. constInitializer now treats a written let or var as the engine fold does
  // (assignedSomewhere): no closed form, so the loader call is refused where it stands. The rows below are red under the census
  // before round 5 as class none with no refusal; p245 is the never-written control, folded to its initializer before and after.
  { dir: W, file: "p237-w01-let-specifier-rewritten-require.test.ts", leg: false, cls: "none", gap: null, refused: "p237-w01-let-specifier-rewritten-require.test.ts:4: " + SPEC_NO_CLOSED_FORM }, // let spec = "./decoy-helper"; spec = "playwright"; require(spec).firefox.launch(): the write after the declaration (before: class none, the decoy loaded, no refusal)
  { dir: W, file: "p238-w02-var-specifier-rewritten-require.test.ts", leg: false, cls: "none", gap: null, refused: "p238-w02-var-specifier-rewritten-require.test.ts:4: " + SPEC_NO_CLOSED_FORM }, // the var twin, webkit (before: class none, no refusal)
  { dir: W, file: "p239-w03-let-specifier-rewritten-in-function.test.ts", leg: false, cls: "none", gap: null, refused: "p239-w03-let-specifier-rewritten-in-function.test.ts:5: " + SPEC_NO_CLOSED_FORM }, // the write inside a function called before the load (before: class none, no refusal)
  { dir: W, file: "p240-w04-let-specifier-rewritten-await-import.test.ts", leg: false, cls: "none", gap: null, refused: "p240-w04-let-specifier-rewritten-await-import.test.ts:4: " + SPEC_NO_CLOSED_FORM }, // await import(spec) inside the test body (before: class none, no refusal)
  { dir: W, file: "p241-w05-let-specifier-rewritten-createrequire.test.ts", leg: false, cls: "none", gap: null, refused: "p241-w05-let-specifier-rewritten-createrequire.test.ts:6: " + SPEC_NO_CLOSED_FORM }, // a createRequire loader called through the rebound name (before: class none, no refusal)
  { dir: W, file: "p242-w06-let-specifier-rewritten-requirecjs.test.ts", leg: false, cls: "none", gap: "never calls its inBrowser through that import", launcherImported: true, refused: "p242-w06-let-specifier-rewritten-requirecjs.test.ts:5: " + SPEC_NO_CLOSED_FORM }, // the launcher's requireCjs called through the rebound name, the launcher imported and never called (before: class none, launcherImported true, no refusal)
  { dir: W, file: "p243-w07-let-specifier-rewritten-to-launcher.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p243-w07-let-specifier-rewritten-to-launcher.test.ts:4: " + SPEC_NO_CLOSED_FORM }, // spec = "./real-viewer-leg"; require(spec).inBrowser(t, ...): the launcher loaded and called through the rebound name, unread (before: class none, launcherImported false, no refusal)
  { dir: W, file: "p244-w08-let-specifier-rewritten-to-relative-node-modules.test.ts", leg: false, cls: "none", gap: null, refused: "p244-w08-let-specifier-rewritten-to-relative-node-modules.test.ts:4: " + SPEC_NO_CLOSED_FORM }, // spec = a relative path into node_modules naming the package (before: class none, no refusal)
  { dir: W, file: "p245-w09-let-specifier-never-written-control.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: ["firefox"], launches: [".launch("], playwright: ["playwright"], holds: "the no-refusal half of a pair whose partner reds: p237 to p244 (a loader's specifier bound by a let or var written after its declaration, folded to the declaration's text before the closing pass after round 5 and loading the package or the launcher silently) beside this let no statement writes to, which folds to its initializer before and after: class own, engines [firefox], the launch read, no refusal" }, // let spec = "playwright"; require(spec).firefox.launch(): the control
  // the net's arms no plant carried (tests-1, round 5, planted in round 6 into the round-5 range): deleting any one of the three left
  // every fixture row green while a module in its form went silent, so no row pinned the arm; each row holds the net's SENTENCE at its
  // line, refused by the census before round 6 and red under the census before round 5 (class none, no refusal) and under the
  // deletion of its arm alone (executed at round 6, recorded in the PR's notes)
  { dir: W, file: "p246-r6e-e1-array-literal-in-call-argument.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p246-r6e-e1-array-literal-in-call-argument.test.ts:3: " + NET_HEAD + NET_PW + NET_NO_REACH }, // e1: load(["playwright"]).firefox.launch() through function load(a: string[]) { return a[0] }: the package's name in an array literal that is a call's argument, specHolder's array-in-call position (before round 5: class none, no refusal; the position deleted: silent)
  { dir: W, file: "p247-r6e-e2-new-expression-argument.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p247-r6e-e2-new-expression-argument.test.ts:3: " + NET_HEAD + NET_PW + NET_NO_REACH }, // e2: new Loader("playwright").get().firefox.launch(): the package's name as a new expression's argument, specHolder's new-argument position (before round 5: class none, no refusal; the position deleted: silent)
  { dir: W, file: "p248-r6e-e3-member-createrequire-const-specifier.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p248-r6e-e3-member-createrequire-const-specifier.test.ts:3: " + NET_HEAD + NET_CR("mod.createRequire") + MORE(1) + NET_NO_REACH }, // since round 7 the const specifier, read through req (a loader the walker did not bind), is THE BOUND-NAME clause's mention at line 5, so the line-3 refusal counts one more mention; with the member arm deleted the module is refused at line 5 by that clause, not silent, and the row still reds on its line and sentence. e3: import * as mod from "node:module"; const make = mod.createRequire; const req = make(__filename); const spec = "playwright"; req(spec).firefox.launch(): the MEMBER createRequire handed on uncalled, the net's member arm (p188 is the identifier's), with a const specifier so the line carries one mention (a literal specifier is a second hit on its own line that survives the arm's deletion and pins nothing) (before round 5: class none, no refusal; the arm deleted: silent)
  // round 6, A (correctness-1): a name is not a binding. constInitializer read a loader's or a driver template's identifier by NAME over
  // the whole module before round 6 (the one variable declaration so named, wherever it stood), so a function parameter sharing a
  // module const's name was read as that const: `const spec = "./decoy-helper"; function load(spec: string) { return require(spec); }
  // load(PW)` folded to the decoy, and the package or the launcher passed in through the parameter loaded with class none and no
  // refusal, under the census and under THE SAFETY NET alike (the package's name stands in a declaration's initializer, a position
  // the net does not read). The read is by lexical scope now (declOfUse), so the parameter reaches no variable declaration and the
  // loader call is refused as folding through no closed form, at the require line. The rows below are red under the census before
  // round 6 as class none with no refusal; p251 is the literal control, whose refusal moves from the net's sentence at the call line
  // to the walker's at the function line (the walker refuses first and the net stands down), and p252 the renamed-parameter control,
  // refused the same way before and after, held.
  { dir: W, file: "p249-r6a-q1-param-collision-function.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p249-r6a-q1-param-collision-function.test.ts:4: " + SPEC_NO_CLOSED_FORM }, // const spec = "./decoy-helper"; const PW = "playwright"; function load(spec: string) { return require(spec); } load(PW).firefox.launch(): the parameter collision as a function declaration (before: class none, no refusal, the net silent)
  { dir: W, file: "p250-r6a-q2-param-collision-launcher-twin.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p250-r6a-q2-param-collision-launcher-twin.test.ts:4: " + SPEC_NO_CLOSED_FORM }, // the launcher twin: const LEG = "./real-viewer-leg"; load(LEG).inBrowser(t, body, "firefox") through the colliding parameter (before: class none, launcherImported false, no refusal)
  { dir: W, file: "p251-r6a-q3-literal-control.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p251-r6a-q3-literal-control.test.ts:3: " + SPEC_NO_CLOSED_FORM }, // the literal control, load("playwright") through the colliding parameter: before round 6 the net's sentence at line 4 (a package name as a call's argument, the fold read the decoy and produced no reach and no refusal), now the walker's at line 3, the function line, the net standing down: a sentence and line move, red before
  { dir: W, file: "p252-r6a-q4-renamed-param-control.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p252-r6a-q4-renamed-param-control.test.ts:4: " + SPEC_NO_CLOSED_FORM, holds: "a shape another plant carries: p14 (a loader whose specifier is a name the fold reads no closed form for), the renamed-parameter control beside p249's collision: function load(s: string) { return require(s); } reaches a parameter and no variable declaration, so the specifier folds through no closed form before and after round 6 and the require line carries the same refusal" }, // the control that pins the fix against over-reaching: refused by name before and after
  { dir: W, file: "p253-r6a-q5-param-collision-arrow.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p253-r6a-q5-param-collision-arrow.test.ts:4: " + SPEC_NO_CLOSED_FORM }, // the arrow twin: const load = (spec: string): any => require(spec) (before: class none, no refusal)
  { dir: W, file: "p254-r6a-q6-decoy-const-in-other-function.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p254-r6a-q6-decoy-const-in-other-function.test.ts:4: " + SPEC_NO_CLOSED_FORM }, // the decoy const declared inside ANOTHER function: function other() { const spec = "./decoy-helper"; return spec; }, the by-name read found it there (before: class none, no refusal)
  // round 6, B (extra5-1, extra5-2): a parameter's default value is a value position. Both isName tests took ts.isParameter(p) without
  // p.name === n before round 6, so an identifier standing as a Parameter's INITIALIZER (its parent the Parameter) was exempt as a
  // name position: `function load(r = require)` handed the global or a createRequire-bound loader on with no refusal (r(s) is no
  // loader callee, and the net reads no bare require and no declaration's initializer), a silent Firefox leg in neither roster nor
  // exclusions; and `async function go(p = pw)` handed a playwright binding on the same way, so beside a direct Firefox launch the
  // WebKit launch through the default was unread and an exclusions reason naming Firefox alone passed reasonVerdict. Both arms exempt
  // the parameter's NAME only now, and valueHandedHow names the default value (HOW_DEFAULT). The loader rows are red under the census
  // before round 6 as class none with no refusal (p255, the literal-in-call control, moves from the net's sentence to the arm's at the
  // same line); the binding rows as class own with engines [firefox] and no refusal (p263 and p267, the default alone, move from the
  // net's read-through sentence at the load line to the arm's at the function line); p260 and p261 are the name-position controls
  // (a parameter NAMED require, a parameter named req shadowing the module's loader), class none with no refusal before and after,
  // and p266 the argument-position control, refused by the binding arm before and after, all three held.
  { dir: W, file: "p255-r6b-a06-literal-in-call-control.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p255-r6b-a06-literal-in-call-control.test.ts:2: " + LOADER_HANDOFF("require", HOW_DEFAULT) }, // function load(r = require): any { return r("playwright"); } then load().firefox.launch(): before round 6 the net's sentence at line 2 (the package's name as a call's argument to a callee the walker knows no loader for), now the loader arm's at the same line, the net standing down: a sentence move, red before
  { dir: W, file: "p256-r6b-a06b-default-require-const-specifier.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p256-r6b-a06b-default-require-const-specifier.test.ts:2: " + LOADER_HANDOFF("require", HOW_DEFAULT) }, // the same with const s = "playwright"; return r(s): silent before round 6 (class none, no refusal, the net reading no declaration's initializer)
  { dir: W, file: "p257-r6b-a06c-default-createrequire-loader.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p257-r6b-a06c-default-createrequire-loader.test.ts:4: " + LOADER_HANDOFF("req", HOW_DEFAULT) }, // const req = createRequire(__filename); function load(r = req) at line 4: the createRequire-bound loader as the default (before: silent)
  { dir: W, file: "p258-r6b-a06d-default-require-launcher.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p258-r6b-a06d-default-require-launcher.test.ts:2: " + LOADER_HANDOFF("require", HOW_DEFAULT) }, // the default require loading the LAUNCHER: const s = "./real-viewer-leg"; return r(s), then load().inBrowser(t, body, "firefox") (before: class none, launcherImported false, no refusal)
  { dir: W, file: "p259-r6b-a40-default-require-arrow.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p259-r6b-a40-default-require-arrow.test.ts:2: " + LOADER_HANDOFF("require", HOW_DEFAULT) }, // the arrow twin: const load = (r = require): any => { const s = "playwright"; return r(s); } (before: silent)
  { dir: W, file: "p260-r6b-e1-param-named-require-control.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, holds: "the no-refusal half of a pair whose partner reds: p255 to p259 (a loader handed on as a parameter's default value) beside this parameter NAMED require, function f(require: (s: string) => unknown), the name position the arm keeps exempt (p.name === n): class none, no refusal before and after round 6, the pin against over-refusing" }, // the parameter's name is a name position
  { dir: W, file: "p261-r6b-e3-param-named-req-shadow-control.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, holds: "the no-refusal half of a pair whose partner reds: p257 (a createRequire-bound loader handed on as a default value) beside this parameter named req that shadows the module's createRequire-bound req, a name position and its own binding: class none, no refusal before and after round 6" }, // the shadowing parameter's name
  { dir: W, file: "p262-r6b-a07-pw-default-beside-firefox.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: ["firefox"], launches: [".launch("], playwright: ["playwright"], launcherImported: false, refused: "p262-r6b-a07-pw-default-beside-firefox.test.ts:3: " + PW_HANDOFF("pw", HOW_DEFAULT) }, // const pw = require("playwright"); async function go(p: any = pw) { await p.webkit.launch() } beside pw.firefox.launch() in the test: before round 6 class own, engines [firefox], no refusal, the WebKit launch through the default unread, so an exclusions reason naming Firefox alone passed reasonVerdict
  { dir: W, file: "p263-r6b-a07b-pw-default-alone-control.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: [], launches: [], playwright: ["playwright"], launcherImported: false, refused: "p263-r6b-a07b-pw-default-alone-control.test.ts:3: " + PW_HANDOFF("pw", HOW_DEFAULT) }, // the same without the Firefox launch: before round 6 the net's read-through sentence at line 2 (no engine and no launch read through the package), now the binding arm's at line 3, the function line, the net standing down: a sentence and line move, red before, not a held row (under the arm no default-value hand-on reaches the read-through clause)
  { dir: W, file: "p264-r6b-a33-pw-default-computed-engine.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: ["firefox"], launches: [".launch("], playwright: ["playwright"], launcherImported: false, refused: "p264-r6b-a33-pw-default-computed-engine.test.ts:3: " + PW_HANDOFF("pw", HOW_DEFAULT) }, // const e = "webkit"; await p[e].launch() inside go(p = pw), beside firefox: the computed engine through the default (before: own, engines [firefox], no refusal)
  { dir: W, file: "p265-r6b-a34-derived-default-beside-firefox.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: ["firefox", "webkit"], launches: [".launch("], playwright: ["playwright"], launcherImported: false, refused: "p265-r6b-a34-derived-default-beside-firefox.test.ts:4: " + PW_HANDOFF("webkit", HOW_DEFAULT) }, // const { webkit } = pw; async function go(e: any = webkit) { await e.launch() } beside firefox: the DERIVED name as a default, refused at the function line (before: own, engines [firefox, webkit] from the destructuring, the e.launch() at line 4 unread, no refusal)
  { dir: W, file: "p266-r6b-a35-pw-argument-control.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: ["firefox"], launches: [".launch("], playwright: ["playwright"], launcherImported: false, refused: "p266-r6b-a35-pw-argument-control.test.ts:4: " + PW_HANDOFF("pw", HOW_ARGUMENT), holds: "a shape another plant carries: p174 (a playwright binding passed as an argument) beside p262's default value: go(pw) is refused by the binding arm at the call before and after round 6, the argument position the round-6 tokens do not touch" }, // the argument-position control
  { dir: W, file: "p267-r6b-a41-namespace-default-alone.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: [], launches: [], playwright: ["playwright"], launcherImported: false, refused: "p267-r6b-a41-namespace-default-alone.test.ts:3: " + PW_HANDOFF("pw", HOW_DEFAULT) }, // import * as pw from "playwright"; async function go(b: any = pw) { await b.firefox.launch() }, alone: the import binding as a default (before: the net's read-through sentence at line 2, now the arm's at line 3: a sentence and line move, red before)
  // round 6, C (extra5-3): a playwright LOAD in a position the walker does not read. The header's bound of the read-through clause was
  // false for a load (as opposed to a binding): a load held in a class field, an object property, handed to .then, passed as an
  // argument or returned from a wrapper was refused by no arm, and the read-through clause is per module (it needs no engine and no
  // launch read), so beside a direct Firefox launch the WebKit launch through the load was unread with both checkers green, an
  // exclusions reason able to under-name an engine. refusePwLoadPosition, the twin of THE INVARIANT's clause 2 for the launcher, is a
  // position predicate: from the load up through the wrappers, a conditional's branches and a logical's operands and along the member
  // chain the walker reads, ending read at a call on the chain, a statement of its own, a declaration's initializer or an assignment's
  // right side under any operator, and refusing every other position by name (valueHandedHow; a promise member with the callback
  // sentence). The rows below are red under the census before round 6 as class own with engines [firefox] and no refusal; p271, the
  // class field alone, moves from the net's read-through sentence to the arm's at the same line; p50, p51 and p57 above are re-aimed
  // in place the same way; p275 to p279 are the controls, held: the binding in an object literal (the binding arm's, p175), the
  // launch's result passed as an argument (a call on the chain ends the walk read), the live tree's assignment through a chain inside
  // try/catch (an assignment's right side, the exemption that keeps the tree's --tsv byte-identical), the awaited import's member
  // launch, and the computed member on the load (pwChain's refusal, p112).
  { dir: W, file: "p268-r6c-a36-class-field-beside-firefox.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: ["firefox"], launches: [".launch("], playwright: ["playwright"], launcherImported: false, refused: "p268-r6c-a36-class-field-beside-firefox.test.ts:2: " + PW_LOAD_HANDOFF(HOW_CLASS_FIELD) }, // class T { pw = require("playwright"); async run() { await this.pw.webkit.launch() } } beside a direct require("playwright").firefox.launch(): before round 6 class own, engines [firefox], no refusal, the WebKit launch through the field unread beside a read engine
  { dir: W, file: "p269-r6c-a36b-object-property-beside-firefox.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: ["firefox"], launches: [".launch("], playwright: ["playwright"], launcherImported: false, refused: "p269-r6c-a36b-object-property-beside-firefox.test.ts:2: " + PW_LOAD_HANDOFF(HOW_LITERAL) }, // const bag = { pw: require("playwright") } beside firefox, then bag.pw.webkit.launch() (before: own, engines [firefox], no refusal)
  { dir: W, file: "p270-r6c-a36c-import-then-beside-firefox.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: ["firefox"], launches: [".launch("], playwright: ["playwright"], launcherImported: false, refused: "p270-r6c-a36c-import-then-beside-firefox.test.ts:2: " + PW_LOAD_THEN }, // import("playwright").then((m) => m.webkit.launch()) beside firefox: the load handed to a promise callback (before: own, engines [firefox], no refusal)
  { dir: W, file: "p271-r6c-a36d-class-field-alone-control.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: [], launches: [], playwright: ["playwright"], launcherImported: false, refused: "p271-r6c-a36d-class-field-alone-control.test.ts:2: " + PW_LOAD_HANDOFF(HOW_CLASS_FIELD) }, // the class field alone, no Firefox: before round 6 the net's read-through sentence at line 2, now the arm's at the same line, the net standing down: a sentence move, red before, not a held row (under the arm no load in an unread position reaches the read-through clause)
  { dir: W, file: "p272-r6c-a36e-load-as-argument-beside-firefox.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: ["firefox"], launches: [".launch("], playwright: ["playwright"], launcherImported: false, refused: "p272-r6c-a36e-load-as-argument-beside-firefox.test.ts:3: " + PW_LOAD_HANDOFF(HOW_ARGUMENT) }, // use(require("playwright")) beside firefox, where use launches WebKit on its parameter: the load itself passed as an argument (before: own, engines [firefox], no refusal)
  { dir: W, file: "p273-r6c-a36f-conditional-load-as-argument.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: ["firefox"], launches: [".launch("], playwright: ["playwright"], launcherImported: false, refused: "p273-r6c-a36f-conditional-load-as-argument.test.ts:3: " + PW_LOAD_HANDOFF(HOW_ARGUMENT) }, // use(process.env.X ? require("playwright") : null) beside firefox: the conditional peeled to the position the value reaches, one refusal (before: own, engines [firefox], no refusal)
  { dir: W, file: "p274-r6c-a36g-wrapper-return-beside-firefox.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: ["firefox"], launches: [".launch("], playwright: ["playwright"], launcherImported: false, refused: "p274-r6c-a36g-wrapper-return-beside-firefox.test.ts:2: " + PW_LOAD_HANDOFF(HOW_RETURNED) }, // function load(): any { return require("playwright"); } beside firefox, then load().webkit.launch() (before: own, engines [firefox], no refusal: derivation stops at the wrapper's call, the second residual, and the load's return position was refused by no arm)
  { dir: W, file: "p275-r6c-a36h-binding-in-object-control.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: ["firefox"], launches: [".launch("], playwright: ["playwright"], launcherImported: false, refused: "p275-r6c-a36h-binding-in-object-control.test.ts:3: " + PW_HANDOFF("pw", HOW_LITERAL), holds: "a shape another plant carries: p175 (a playwright binding held in an object literal) beside p269's load in the same position: const bag = { pw } is the binding arm's before and after round 6, the load-position arm being asked of a load where it stands only" }, // the binding twin of p269
  { dir: W, file: "p276-r6c-a36i-launch-result-as-argument-control.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: ["firefox"], launches: [".launch("], playwright: ["playwright"], launcherImported: false, holds: "the no-refusal half of a pair whose partner reds: p272 (the load itself passed as an argument) beside this launch's RESULT passed as an argument, close(require(the package).firefox.launch()): the walk from the load ends read at the call on the chain (the call arm counted the launch), class own, engines [firefox], no refusal before and after round 6" }, // a call on the chain is a read position
  { dir: W, file: "p277-r6c-a36j-assignment-through-chain-in-try-control.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: ["chromium"], launches: [".launch("], playwright: ["playwright"], launcherImported: false, holds: "the no-refusal half of a pair whose partner reds: p268 to p274 (a load in a position the walker does not read) beside the live tree's own form, try { chromium = require(the package).chromium; } catch { chromium = null; }: an assignment's right side reached through a member chain is a read position (bindLoaded binds the target), class own, engines [chromium], no refusal before and after round 6, the exemption that keeps the tree's --tsv byte-identical" }, // the tree's form, an assignment's right side through a chain
  { dir: W, file: "p278-r6c-a36k-await-import-member-launch-control.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: ["firefox"], launches: [".launch("], playwright: ["playwright"], launcherImported: false, holds: "the no-refusal half of a pair whose partner reds: p270 (the load handed to a promise callback through .then) beside (await import(the package)).firefox.launch(): the await and the parentheses are wrappers the walk reads through and the member chain ends at the call, class own, engines [firefox], the launch read, no refusal before and after round 6" }, // an awaited import's member launch is read
  { dir: W, file: "p279-r6c-a36l-computed-member-on-load-control.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: [], launches: [], playwright: ["playwright"], launcherImported: false, refused: "p279-r6c-a36l-computed-member-on-load-control.test.ts:3: " + COMPUTED_REFUSAL, holds: "a shape another plant carries: p112 (a computed member with a name the walker cannot fold on a load) beside p272's argument position: use(require(the package)[k]) ends the walk at the computed member, which pwChain refuses by name, and the load-position arm stands down, so the line carries one refusal before and after round 6" }, // the computed member on the load: pwChain's refusal, one per line
  // round 6, D (correctness-2): the barrel that re-exports the launcher's inBrowser. localRefusals refused a loaded module that binds or
  // calls inBrowser (launcherBinds) only while the test's own shared calls were zero, so a test calling inBrowser directly AND through
  // the barrel's export with an engine was class shared, gap null, engines [], the barrel call and its engine unread (a call through
  // the re-export resolves to no launcher binding the walker counts, and the fold of the barrel's record carries no engine): the
  // both-calls twin of the round-4 requireCjs re-export finding, for the launcher's own re-export. Since round 6 classify's record
  // carries launcherReexport and localRefusals refuses the importer on it whatever its own calls, after the launcherBinds arm (so p32,
  // the barrel-only control, keeps that arm's sentence); the arm over-approximates a barrel imported for another export beside a
  // direct call (p284), on the safe side, with the same remedy. The five rows hold the arm's SENTENCE through BARREL_REEXPORT at the
  // barrel's import line; engines [] states the unread engine as a property.
  { dir: W, file: "p280-r6d-d1-both-calls-named-reexport.test.ts", leg: true, cls: "shared", gap: null, launcherImported: true, engines: [], refused: "p280-r6d-d1-both-calls-named-reexport.test.ts:3: " + BARREL_REEXPORT("ui/webview/leg-barrel.ts") }, // d1: import { inBrowser } from the launcher and { inBrowser as ib2 } from leg-barrel (export { inBrowser } from the launcher), inBrowser(t, body) then ib2(t, body, "firefox") (before round 6: class shared, gap null, engines [], no refusal, rosterable with the Firefox engine lost)
  { dir: W, file: "p281-r6d-d2-both-calls-renamed-reexport.test.ts", leg: true, cls: "shared", gap: null, launcherImported: true, engines: [], refused: "p281-r6d-d2-both-calls-renamed-reexport.test.ts:3: " + BARREL_REEXPORT("ui/webview/leg-barrel-renamed.ts") }, // d2: the renamed twin, export { inBrowser as open } from the launcher, open(t, body, "firefox") beside the direct call (before: as p280)
  { dir: W, file: "p282-r6d-d3-both-calls-namespace-import.test.ts", leg: true, cls: "shared", gap: null, launcherImported: true, engines: [], refused: "p282-r6d-d3-both-calls-namespace-import.test.ts:3: " + BARREL_REEXPORT("ui/webview/leg-barrel.ts") }, // d3: the namespace twin, import * as B from leg-barrel, B.inBrowser(t, body, "webkit") beside the direct call (before: as p280, the WebKit engine lost)
  { dir: W, file: "p283-r6d-d4-both-calls-barrel-chain.test.ts", leg: true, cls: "shared", gap: null, launcherImported: true, engines: [], refused: "p283-r6d-d4-both-calls-barrel-chain.test.ts:3: " + BARREL_REEXPORT("ui/webview/leg-barrel2.ts, which loads ui/webview/leg-barrel.ts") }, // d4: a barrel of the barrel (leg-barrel2 re-exports leg-barrel's inBrowser), the two-link chain in the sentence, the walk's BFS reaching the re-export one link down (before: as p280)
  { dir: W, file: "p284-r6d-d7-other-export-beside-direct-call.test.ts", leg: true, cls: "shared", gap: null, launcherImported: true, engines: [], refused: "p284-r6d-d7-other-export-beside-direct-call.test.ts:3: " + BARREL_REEXPORT("ui/webview/leg-barrel-plus.ts") }, // d7: the over-approximation's witness, import { helper } from a barrel that re-exports inBrowser beside its own export, helper() and a direct inBrowser call, nothing launched through the barrel (before round 6: class shared, gap null, engines [], no refusal; refused now on the safe side, since the walker reads no import list against the barrel's exports, the remedy the same import of the launcher directly)
  // round 6, F (tests-2, extra5-4): a specifier assembled from literals. foldSpecifier joined a `+` chain's or a template's literal pieces
  // with "/" whatever the chain, a path-join reading, so `require("play" + "wright")` loaded play/wright: refused as naming no file (the
  // wrong reason, on the safe side) when no file stood there, refused by the net's clause 1 when the fixture's decoy play/wright.ts stood
  // there (the flat text names the package), and for a RELATIVE chain, "./play" + "wright", resolved to the decoy with NO refusal, the
  // module ./playwright it loads unread: the silent shape. Since round 6 a chain that crossed no path call is a string concatenation and
  // its pieces are joined as written before resolveSpec, the literal's own road (the package for p285 and p286, the launcher for p287,
  // the module ./playwright for p288 and p289, refused at the importer as p290, the literal control, is), and a chain that did cross a
  // path call keeps the "/" join (p291, the path-call control, still resolves to the decoy: class none, no refusal). The fix line's own
  // shape, substring tests over both joins with the "/" join kept as the specifier, was executed and refuted at round 6: it read p291's
  // ./play/wright as a package and refused it falsely. p288 to p290 hold the launcherBinds arm's SENTENCE through LAUNCHER_BINDS; p285
  // to p287 hold the class, the package or the launcher import, and the engine as PROPERTIES.
  { dir: W, file: "p285-r6f-a01-package-from-plus-literals.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: ["webkit"], launches: [".launch("], playwright: ["playwright"], launcherImported: false }, // a01: const pw = require("play" + "wright"), pw.webkit.launch() (before round 6, the decoy in the fixture: class none, refused by the net's clause 1 at line 2; with no file at play/wright: refused as loading play/wright, which names no file)
  { dir: W, file: "p286-r6f-a04-package-from-template-const-tail.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: ["firefox"], launches: [".launch("], playwright: ["playwright"], launcherImported: false }, // a04: const tail = "wright", await import(`play${tail}`), .firefox.launch(): the template's const read through its closed form (before: as p285, at line 3)
  { dir: W, file: "p287-r6f-a26-launcher-from-plus-literals.test.ts", leg: true, cls: "shared", gap: null, launcherImported: true, engines: [] }, // a26: const leg = require("./real-" + "viewer-leg"), leg.inBrowser(t, body): the launcher's name from two literals, a shared call on the load (before round 6: class none, launcherImported false, refused as loading ./real-/viewer-leg, which names no file)
  { dir: W, file: "p288-r6f-a34-relative-plus-literals-decoy.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p288-r6f-a34-relative-plus-literals-decoy.test.ts:2: " + LAUNCHER_BINDS("ui/webview/playwright.ts") }, // a34: const m = require("./play" + "wright"), m.run(t), the decoy play/wright.ts beside the module ./playwright that binds and calls inBrowser (before round 6: class none, no refusal, the load resolved to the decoy: the silent shape)
  { dir: W, file: "p289-r6f-a35-relative-template-decoy.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p289-r6f-a35-relative-template-decoy.test.ts:3: " + LAUNCHER_BINDS("ui/webview/playwright.ts") }, // a35: the template twin, const tail = "wright", require(`./play${tail}`), m.run(t) (before: silent, as p288)
  { dir: W, file: "p290-r6f-a36-literal-relative-control.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p290-r6f-a36-literal-relative-control.test.ts:2: " + LAUNCHER_BINDS("ui/webview/playwright.ts"), holds: "a shape another plant carries: p32 (a literal relative specifier naming a module that binds or calls the launcher's inBrowser, refused at the importer by the launcherBinds arm); the literal control for p288 and p289, whose chains fold to this literal's road since round 6, refused with this row's sentence before and after" }, // a36: const m = require("./playwright"), m.run(t)
  { dir: W, file: "p291-r6f-a32-path-join-control.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, holds: "the no-refusal half of a pair whose partner reds: p288 and p289 (the same pieces with no path call, folded by concatenation to ./playwright since round 6 and refused there); a chain that crossed path.join is a path and keeps the slash join, so it resolves to the clean decoy play/wright.ts, class none with no refusal before and after round 6; the row that refutes the fix line's own shape, under which ./play/wright was read as a package and refused falsely" }, // a32: import path from "node:path", const m = require(path.join("./play", "wright")), void m.nothing
  // round 6, G (fresh-3): a shared call whose rejection is swallowed. The swallow read was a try statement of the SAME function with a
  // catch clause, so a shared call whose rejection was handled another way, its promise handed to .catch, to .then's second argument or
  // to Promise.allSettled, or the call inside a callback lexically inside a try, was class shared, gap null, swallow [] and rosterable
  // with the swallow unreported, while every spelling swallows the switch's failure at run time the same. Since round 6 swallowed(n)
  // reads the underlying predicate: an enclosing try with a catch up to the module through callbacks, or the promise, through any
  // chain of .then and .finally, reaching .catch or a .then with two arguments, or standing as Promise.allSettled's argument or an
  // element of its array literal; .finally and a bare .then hand the rejection on and are not swallows, Promise.all rejects through.
  // Every row here holds the swallow field as a PROPERTY (the lines, as p07 and p210 do), none a refusal: p292 to p296 and p299 to
  // p302 red under the census before round 6 (swallow [] where the row expects the call's line, or the helper's import line), the
  // rest held. The census header's swallow clause is held by a sentence pin at the top of the plants test (the header-pin line first).
  { dir: W, file: "p292-r6g-s2-catch.test.ts", leg: true, cls: "shared", gap: null, swallow: [3] },                                  // s2: await inBrowser(t, body).catch(() => {}) (before round 6: swallow [], the .catch unread)
  { dir: W, file: "p293-r6g-s6-then-second-argument.test.ts", leg: true, cls: "shared", gap: null, swallow: [3] },                    // s6: .then(() => {}, () => {}), the second argument the rejection handler (before: swallow [])
  { dir: W, file: "p294-r6g-s4-allsettled.test.ts", leg: true, cls: "shared", gap: null, swallow: [3] },                              // s4: await Promise.allSettled([inBrowser(t, body)]), the rejection settled, never thrown (before: swallow [])
  { dir: W, file: "p295-r6g-s3-callback-in-try.test.ts", leg: true, cls: "shared", gap: null, swallow: [4] },                         // s3: the call inside an async callback the try awaits through a wrapper, run(async () => { await inBrowser(...) }), the same-function read stopped at the callback (before: swallow [])
  { dir: W, file: "p296-r6g-s10-helper-catch.test.ts", leg: true, cls: "shared", gap: null, swallow: [2] },                           // s10: the test calls inBrowser itself and a helper whose shared call carries .catch (catch-helper.ts): the helper's swallow folds into the record at the import line, as p210's try/catch helper does (before: swallow [], the helper's .catch unread)
  { dir: W, file: "p297-r6g-s5-finally-control.test.ts", leg: true, cls: "shared", gap: null, swallow: [], holds: "the no-refusal half of a pair whose partner reds: p292 (.catch on the same call); .finally hands the rejection on and is not a swallow, so the field stays [] before and after round 6, the control the widened read must leave alone" }, // s5: await inBrowser(t, body).finally(() => {})
  { dir: W, file: "p298-r6g-s7-bare-then-control.test.ts", leg: true, cls: "shared", gap: null, swallow: [], holds: "the no-refusal half of a pair whose partner reds: p293 (.then with a second argument on the same call); a bare .then hands the rejection on and is not a swallow, so the field stays [] before and after round 6" }, // s7: await inBrowser(t, body).then(() => {})
  { dir: W, file: "p299-r6g-s13-then-catch-chain.test.ts", leg: true, cls: "shared", gap: null, swallow: [3] },                       // s13: .then(() => {}).catch(() => {}), the .catch reached through the chain (before: swallow [])
  { dir: W, file: "p300-r6g-s14-finally-catch-chain.test.ts", leg: true, cls: "shared", gap: null, swallow: [3] },                    // s14: .finally(() => {}).catch(() => {}), the .catch reached through .finally (before: swallow [])
  { dir: W, file: "p301-r6g-s15-allsettled-parenthesized-second.test.ts", leg: true, cls: "shared", gap: null, swallow: [3] },        // s15: Promise.allSettled([Promise.resolve(), (inBrowser(t, body))]), the call a parenthesized second element (before: swallow [])
  { dir: W, file: "p302-r6g-s16-then-undefined-second.test.ts", leg: true, cls: "shared", gap: null, swallow: [3] },                  // s16: .then(undefined, () => {}), read by arity: two arguments, the first undefined (before: swallow [])
  { dir: W, file: "p303-r6g-s11-promise-all-control.test.ts", leg: true, cls: "shared", gap: null, swallow: [], holds: "the no-refusal half of a pair whose partner reds: p294 (Promise.allSettled over the same call); Promise.all rejects through, so the field stays [] before and after round 6, the control that keeps the allSettled read from widening to every Promise member" }, // s11: await Promise.all([inBrowser(t, body)])
  { dir: W, file: "p304-r6g-s12-wrapper-returns-call-in-try.test.ts", leg: true, cls: "shared", gap: null, swallow: [], holds: "a stated residual boundary: a shared call returned by a wrapper, const p = (t) => inBrowser(t, body), and awaited inside a try is the wrapper's to the read (the call is lexically the wrapper's, outside the try) and swallows at run time all the same, stated in the census header's swallow clause; swallow [] before and after round 6" }, // s12: try { await p(t); } catch {}
  { dir: W, file: "p305-r6g-s9-try-no-await.test.ts", leg: true, cls: "shared", gap: null, swallow: [3], holds: "a stated residual boundary: a try with a catch around a call never awaited, try { void inBrowser(t, body) } catch {}, reads as a swallow before and after round 6 (the same-function read already saw it) and leaves an unhandled rejection at run time, the over-approximation on the safe side the census header's swallow clause states" }, // s9: the try swallows nothing at run time, the read says [3]
  // the closing pass after round 6 (the round's verifiers' findings), three groups. A: two more shapes of the name read as a binding,
  // a parameter shadowing an unwritten let (the let's initializer is a closed form, so the by-name read folded the parameter to the
  // decoy) and an object-destructured parameter sharing a module const's name (a binding element, no variable declaration), both
  // class none with no refusal under the census before round 6 and refused since as folding through no closed form, at the require
  // line (the rows hold the SENTENCE through SPEC_NO_CLOSED_FORM); and the catch variable sharing a const's name, a pin of
  // constInitializer's catch-variable arm: a catch clause's variable is a VariableDeclaration under the CatchClause, which the
  // lexical read reached and, finding no initializer, took the null road, so the round-6 module before the closing pass refused the
  // loader as loading the placeholder <spec>, which names no file, the wrong reason, where the census before round 6 refused it
  // through no closed form by its by-name read's two declarations, the row held. G: the two swallow spellings the read does not
  // reach, a .catch on a name the call's promise was bound to and on a Promise.all over the call, stated as residuals in the census
  // header's swallow clause beside the wrapper's, swallow [] before and after round 6, held. F: a `+` chain nested inside a path
  // call's argument, joined piece by piece with the call's other arguments before and after round 6 (pathCall is per chain), the
  // boundary foldSpecifier's docstring states, refused as naming no file at both, held.
  { dir: W, file: "p306-r6a-q7-param-shadows-unwritten-let.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p306-r6a-q7-param-shadows-unwritten-let.test.ts:4: " + SPEC_NO_CLOSED_FORM }, // let spec = "./decoy-helper" never written; function load(spec: string) { return require(spec); } load(PW): the parameter shadows a let (before: class none, no refusal, folded to the decoy)
  { dir: W, file: "p307-r6a-q8-destructured-param-shares-const-name.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p307-r6a-q8-destructured-param-shares-const-name.test.ts:4: " + SPEC_NO_CLOSED_FORM }, // function load({ spec }: { spec: string }) { return require(spec); } load({ spec: PW }): the binding element shares the const's name (before: class none, no refusal, folded to the decoy)
  { dir: W, file: "p308-r6a-q9-catch-variable-shares-const-name.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p308-r6a-q9-catch-variable-shares-const-name.test.ts:4: " + SPEC_NO_CLOSED_FORM, holds: "a pin of an arm no plant carried: constInitializer's no-initializer close, whose first member, the catch variable, the closing pass after round 6's verification repaired alone through a catch-clause arm, which the review's round 7 folds into the class rule (every declaration with no initializer is bound to no text, p318 to p322 the rest of the class). A catch clause's variable is a VariableDeclaration whose parent is the CatchClause, not a VariableDeclarationList, so the round-6 module's lexical read reached it, found no initializer and took the null road: the fold pushed the placeholder <spec> and the loader was refused as loading <spec>, which names no file in the tree, the wrong reason, where the census before round 6 refused this row through no closed form by another road, its by-name read finding two declarations so named. Green under the census before round 6 on the same sentence, red under the round-6 module before the closing pass and under the round-7 module with the null road restored, executed and recorded in the PR's notes" }, // try { throw PW; } catch (spec) { return require(spec as string); } beside const spec = "./decoy-helper"
  { dir: W, file: "p309-r6g-s17-bound-promise-catch-residual.test.ts", leg: true, cls: "shared", gap: null, swallow: [], holds: "a stated residual boundary: the swallow read follows the chain on the call itself, so a .catch on a name the call's promise was bound to, const p = inBrowser(t, body); await p.catch(() => {}), is not read, swallow [] before and after round 6 while the rejection is swallowed at run time, the first of the two residuals the closing pass after round 6's verification stated in the census header's swallow clause beside the wrapper's" }, // s17: the promise bound, then caught on the name
  { dir: W, file: "p310-r6g-s18-promise-all-catch-residual.test.ts", leg: true, cls: "shared", gap: null, swallow: [], holds: "a stated residual boundary: a .catch on the result of Promise.all over an array holding the call, await Promise.all([inBrowser(t, body)]).catch(() => {}), is not read either (the chain is followed on the call, not on a combinator's result; p303 holds Promise.all alone rejecting through), swallow [] before and after round 6 while the rejection is swallowed at run time, the second residual the closing pass stated in the census header's swallow clause" }, // s18: the combinator's result caught
  { dir: W, file: "p311-r6f-a37-plus-inside-path-join-boundary.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p311-r6f-a37-plus-inside-path-join-boundary.test.ts:3: loads ./play/wr/ight, which names no file in the tree", holds: "a stated residual boundary: pathCall is per chain, not per argument, so a + chain standing as one argument of a path call is joined with the call's other arguments piece by piece, require(path.join(\"./play\", \"wr\" + \"ight\")) folding to ./play/wr/ight, not ./play/wright, refused as naming no file before and after round 6 (the safe side, and silent only were a module to stand at the misjoined path), the boundary foldSpecifier's docstring states since the closing pass after round 6's verification" }, // a37: the chain inside path.join's second argument
  // the review's round 7, in the round-6 range (the round-6 rulings place them there, R6_LAST moved), every row red under the census
  // before round 6 and under the round-6 head, executed and recorded in the PR's notes. A (extra5-1): the lexical read's scopes are
  // the compiler's grammar, not the shapes a round found. A const declared in a switch's case block or a namespace body, or a var
  // declared in a class static block (a const there was read at the static block's body, a block), that shares a module const's
  // name read as the module const at the round-6 head, so the package or the launcher loaded through it was class none with no refusal under the census and
  // the net alike, a silent Firefox leg (p312 to p315; the census before round 6 refused each through no closed form by its by-name
  // read's two declarations). p312 and p315 read own Firefox now, p313 the launcher twin shared Firefox with gap null, and p314,
  // whose namespace exports the load for a launch through N.pw that the walker does not read, the net's read-through clause at the
  // load. p316 and p317, a var in a namespace body or a static block beside a module const of the same name, are the stop controls:
  // the walk hoisted that var to the module, so the round-6 head refused the module const's load through no closed form, falsely,
  // and they read own Firefox with no refusal now that the walk stops at a namespace body and a static block as at a function. The
  // census test's scope-set case pins the predicates against the binder; these rows pin the readers and the stop, which it cannot
  // see. E (extra5-2): the no-initializer class, a for-of const, a for-in const, a for-of let, an ambient declare const and a let
  // never written, each refused at the round-6 head (and before round 6, with no module const of the same name) as loading the
  // placeholder <spec> (<SPEC>), which names no file in the tree, the wrong reason, and through no closed form now, the rows holding
  // the SENTENCE through SPEC_NO_CLOSED_FORM; p308 above, the catch variable, is the class's control.
  { dir: W, file: "p312-r7a-a01-case-clause-package.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: ["firefox"], playwright: ["playwright"], launches: [".launch("], launcherImported: false }, // a01: const spec = "./decoy-helper"; switch (k) { default: const spec = "playwright"; pw = require(spec); } then pw.firefox.launch() (before round 7: class none, no refusal, folded to the decoy)
  { dir: W, file: "p313-r7a-a02-case-clause-launcher-twin.test.ts", leg: true, cls: "shared", gap: null, engines: ["firefox"], launcherImported: true }, // a02: the launcher twin, const spec = "./real-viewer-leg" in the case clause, leg.inBrowser(t, body, "firefox") (before round 7: class none, launcherImported false, no refusal)
  { dir: W, file: "p314-r7a-a03-namespace-package-export.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: [], playwright: ["playwright"], launcherImported: false, refused: "p314-r7a-a03-namespace-package-export.test.ts:3: " + NET_READ_THROUGH }, // a03: namespace N { const spec = "playwright"; export const pw = require(spec); } then N.pw.firefox.launch() (before round 7: class none, no refusal, folded to the decoy)
  { dir: W, file: "p315-r7a-a05-static-block-var-package.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: ["firefox"], playwright: ["playwright"], launches: [".launch("], launcherImported: false }, // a05: class C { static { var spec = "playwright"; pw = require(spec); } } beside const spec = "./decoy-helper" (before round 7: class none, no refusal, folded to the decoy)
  { dir: W, file: "p316-r7a-a07-namespace-var-stop-control.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: ["firefox"], playwright: ["playwright"], launches: [".launch("], launcherImported: false }, // a07: namespace N { var spec = "./decoy-helper"; } beside const spec = "playwright"; require(spec) (before round 7: refused through no closed form at line 4, the namespace's var hoisted to the module)
  { dir: W, file: "p317-r7a-a12-static-block-var-stop-control.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: ["firefox"], playwright: ["playwright"], launches: [".launch("], launcherImported: false }, // a12: class C { static { var spec = "./decoy-helper"; } } beside const spec = "playwright"; require(spec) (before round 7: refused through no closed form at line 5, the static block's var hoisted to the module)
  { dir: W, file: "p318-r7e-e10-for-of-const-head.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p318-r7e-e10-for-of-const-head.test.ts:3: " + SPEC_NO_CLOSED_FORM }, // e10: for (const spec of PW) { return require(spec); } (before round 7: loads <spec>, which names no file in the tree)
  { dir: W, file: "p319-r7e-e11-for-in-const-head.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p319-r7e-e11-for-in-const-head.test.ts:3: " + SPEC_NO_CLOSED_FORM }, // e11: for (const spec in PW) { return require(spec); } (before round 7: loads <spec>, which names no file in the tree)
  { dir: W, file: "p320-r7e-e12-for-of-let-head.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p320-r7e-e12-for-of-let-head.test.ts:3: " + SPEC_NO_CLOSED_FORM }, // e12: for (let spec of PW) { return require(spec); } (before round 7: loads <spec>, which names no file in the tree)
  { dir: W, file: "p321-r7e-e04-ambient-declare-const.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p321-r7e-e04-ambient-declare-const.test.ts:3: " + SPEC_NO_CLOSED_FORM }, // e04: declare const SPEC: string; require(SPEC) (before round 7: loads <SPEC>, which names no file in the tree)
  { dir: W, file: "p322-r7e-e05-never-written-let.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p322-r7e-e05-never-written-let.test.ts:3: " + SPEC_NO_CLOSED_FORM }, // e05: let spec: any; require(spec), the let never written (before round 7: loads <spec>, which names no file in the tree)
  // B (correctness-1): the launcher is matched by RESOLVED path. foldSpecifier's fallback bound any folded text CONTAINING the
  // launcher's name as the launcher, so a module named like it and loaded through a path call or a placeholder chain was class
  // shared with gap null and no refusal under the census and the net alike (p323 to p325, p327 to p330; the census before round 6
  // gave the same). Since round 7 a placeholder chain naming the launcher is refused before it is resolved (p324, p327), a text is
  // resolved and binds the launcher only on the launcher's file (p326, the real launcher through the same path-call spelling, the
  // control, bound before and after), a text landing on another file takes the local road and is read by its content (p323 and
  // p325 launch nothing and are class none, p330 wraps the launcher with Firefox and is refused at its import), and a text landing
  // nowhere or on two files is refused with that reason (p328, p329). Companions: real-viewer-leg-stub.ts,
  // real-viewer-leg-cjsonly.cjs and real-viewer-leg-wrap.ts under ui/webview, real-viewer-leg-amb.ts at the plants' root and under
  // their vscode-extension/.
  { dir: W, file: "p323-r7b-b1-path-call-launcher-named-stub.test.ts", leg: false, cls: "none", gap: null, launcherImported: false }, // b1: require(path.resolve(process.cwd(), "..", "ui", "webview", "real-viewer-leg-stub")), a stub that launches nothing (before round 7: class shared, gap null, no refusal)
  { dir: W, file: "p324-r7b-b2-placeholder-chain-launcher-named-stub.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p324-r7b-b2-placeholder-chain-launcher-named-stub.test.ts:2: " + SPEC_NO_CLOSED_FORM }, // b2: require(process.env.LEG_DIR + "/real-viewer-leg-stub") (before round 7: class shared, gap null, no refusal)
  { dir: W, file: "p325-r7b-b3b-path-call-launcher-named-cjs-only.test.ts", leg: false, cls: "none", gap: null, launcherImported: false }, // b3b: the .cjs spelling with no .ts beside it, real-viewer-leg-cjsonly.cjs through path.resolve, read by its content (before round 7: class shared, gap null, no refusal)
  { dir: W, file: "p326-r7b-b4-path-call-real-launcher-control.test.ts", leg: true, cls: "shared", gap: null, launcherImported: true, holds: "the no-refusal half of a pair whose partner reds: p323 (a module named like the launcher, loaded through the same path-call spelling, class shared before round 7 and class none since): the real launcher through path.resolve(process.cwd(), \"..\", \"ui\", \"webview\", \"real-viewer-leg\") lands on the launcher's file and binds it, class shared with gap null before and after round 7, so the fold binds the launcher by where its text lands, not by refusing a path call" }, // b4: the control
  { dir: W, file: "p327-r7b-b5-placeholder-prefix-spelling-launcher-path.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p327-r7b-b5-placeholder-prefix-spelling-launcher-path.test.ts:2: " + SPEC_NO_CLOSED_FORM }, // b5: require(process.env.LEG_ROOT + "/ui/webview/real-viewer-leg"), a placeholder prefix spelling the launcher's own path, the refuter's stricter clause (before round 7: class shared, gap null, no refusal)
  { dir: W, file: "p328-r7b-b8-path-call-launcher-named-nowhere.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p328-r7b-b8-path-call-launcher-named-nowhere.test.ts:3: loads ../ui/webview/real-viewer-leg-missing, which names no file in the tree" }, // b8: a launcher-named path that resolves nowhere, the true reason (before round 7: class shared, gap null, no refusal)
  { dir: W, file: "p329-r7b-b11-path-call-launcher-named-ambiguous.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p329-r7b-b11-path-call-launcher-named-ambiguous.test.ts:3: loads real-viewer-leg-amb, which names two files (real-viewer-leg-amb.ts and vscode-extension/real-viewer-leg-amb.ts), so the walker cannot tell which one it reads" }, // b11: a launcher-named path the two bases resolve to two files, the true reason (before round 7: class shared, gap null, no refusal)
  { dir: W, file: "p330-r7b-b16-path-call-launcher-named-wrapper-firefox.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p330-r7b-b16-path-call-launcher-named-wrapper-firefox.test.ts:3: " + LAUNCHER_BINDS("ui/webview/real-viewer-leg-wrap.ts") }, // b16: a launcher-named wrapper passing Firefox to the launcher, read by its content (before round 7: class shared, gap null, engines [], a Firefox leg hidden behind the name)
  // C (extra6-1): THE BOUND-NAME clause. A playwright package's or the launcher's name bound to a const, a let or a var, written or
  // not, and handed to a callee the walker knows no loader for was class none with no refusal under the census and the net alike, a
  // one-hop bypass of the net's unknown-callee road (p332, p333, p335 to p340; p340's require.main.require reaches Firefox with node
  // builtins alone in the CJS test bundle); the net refuses each since round 7 with a sentence naming the bound name, and an object
  // literal as a call's argument is read beside the array literal (p331). p334, the literal handed to the same callee, is the
  // control the net refused before and after. p341 and p342, a text held in an object or an array literal bound to a name, are the
  // clause's stated boundary; p343, a text returned from a function, is refused by the return arm; p344, a text in a conditional's
  // branches standing as the call's argument, by the climb through a conditional and a logical.
  { dir: W, file: "p331-r7c-q02-object-literal-argument.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p331-r7c-q02-object-literal-argument.test.ts:3: " + NET_HEAD + NET_PW + NET_NO_REACH }, // q02: load({ spec: PW }) to a foreign callee, specHolder's object-literal position (before round 7: class none, no refusal)
  { dir: W, file: "p332-r7c-q05-const-foreign-callee.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p332-r7c-q05-const-foreign-callee.test.ts:3: " + NET_HEAD + NET_BOUND_PW("name", 4) + NET_NO_REACH }, // q05: const name = PW; load(name) to a foreign callee (before round 7: class none, no refusal)
  { dir: W, file: "p333-r7c-q07-const-same-module-nonloader.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p333-r7c-q07-const-same-module-nonloader.test.ts:3: " + NET_HEAD + NET_BOUND_PW("name", 4) + NET_NO_REACH }, // q07: the same through a function of the module that is no loader (before round 7: class none, no refusal)
  { dir: W, file: "p334-r7c-q08-literal-foreign-callee-control.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p334-r7c-q08-literal-foreign-callee-control.test.ts:3: " + NET_HEAD + NET_PW + NET_NO_REACH, holds: "a shape another plant carries: p74 (a package name as a call's argument, the net's literal arm): the literal handed to a callee the walker knows no loader for, load(\"playwright\"), refused by the net's literal sentence before and after round 7, the control beside the bound-name rows, whose name the net read in no position before" }, // q08: the control
  { dir: W, file: "p335-r7c-q09a-jiti-const.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p335-r7c-q09a-jiti-const.test.ts:3: " + NET_HEAD + NET_BOUND_PW("pkg", 4) + NET_NO_REACH }, // q09a: jiti(__filename)(pkg), a loader package the walker does not know (before round 7: class none, no refusal)
  { dir: W, file: "p336-r7c-q09b-companion-launcher-const.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p336-r7c-q09b-companion-launcher-const.test.ts:3: " + NET_HEAD + NET_BOUND_LAUNCHER("LEG", 4) + NET_NO_REACH }, // q09b: const LEG = "./real-viewer-leg" handed to a companion helper's load, then leg.inBrowser(t, body, "firefox") (before round 7: class none, no refusal)
  { dir: W, file: "p337-r7c-q10a-unwritten-let-foreign-callee.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p337-r7c-q10a-unwritten-let-foreign-callee.test.ts:3: " + NET_HEAD + NET_BOUND_PW("name", 4) + NET_NO_REACH }, // q10a: let name = PW, never written, to a foreign callee (before round 7: class none, no refusal)
  { dir: W, file: "p338-r7c-q10b-written-let-foreign-callee.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p338-r7c-q10b-written-let-foreign-callee.test.ts:4: " + NET_HEAD + NET_BOUND_PW("name", 5) + NET_NO_REACH }, // q10b: let name = "./decoy-helper"; name = PW, an assignment's right side (before round 7: class none, no refusal)
  { dir: W, file: "p339-r7c-q12-companion-package-const.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p339-r7c-q12-companion-package-const.test.ts:3: " + NET_HEAD + NET_BOUND_PW("PKG", 4) + NET_NO_REACH }, // q12: const PKG = PW handed to a companion helper's load (before round 7: class none, no refusal)
  { dir: W, file: "p340-r7c-q21-require-main-require.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p340-r7c-q21-require-main-require.test.ts:2: " + NET_HEAD + NET_BOUND_PW("name", 3) + NET_NO_REACH }, // q21: require.main!.require(name), node builtins alone (before round 7: class none, no refusal)
  { dir: W, file: "p341-r7c-q14-object-bound-to-a-name-boundary.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, holds: "a stated residual boundary: the bound-name clause's boundary, a package name held in an object literal bound to a name, const cfg = { pkg: \"playwright\" }, read through cfg.pkg into a callee the walker knows no loader for, class none with no refusal before and after round 7: reading a literal's elements refuses the census module's own PW_PACKAGES through the census test's import, a false refusal on the tree, as the census header states" }, // q14
  { dir: W, file: "p342-r7c-q38-array-bound-to-a-name-boundary.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, holds: "a stated residual boundary: the bound-name clause's boundary, a package name held in an array literal bound to a name, const specs = [\"playwright\"], read through specs[0] into a callee the walker knows no loader for, class none with no refusal before and after round 7, for the reason p341 gives, as the census header states" }, // q38
  { dir: W, file: "p343-r7c-q36-returned-from-a-function.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p343-r7c-q36-returned-from-a-function.test.ts:3: " + NET_HEAD + NET_RETURNED + NET_NO_REACH }, // q36: function pkg() { return PW; } then load(pkg()), the return arm's return statement (before round 7: class none, no refusal)
  { dir: W, file: "p344-r7c-q44-conditional-call-argument.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p344-r7c-q44-conditional-call-argument.test.ts:3: " + NET_HEAD + NET_PW_CORE + MORE(1) + NET_NO_REACH }, // q44: load(cond ? "playwright-core" : PW), the climb through a conditional's two branches, each a mention, so the refusal names the first and counts the second (before round 7: class none, no refusal)
  // D (extra5-3, with correctness-2, extra6-2 and extra7-1): the swallow read's under-reads stated as a rule. The read takes its
  // spellings on the call itself, so Promise.allSettled over a name an array holding the call was bound to (p345), or over a spread
  // of that name (p346), is not read: swallow [] under the census before round 6, at the round-6 head and since, while the
  // rejection is swallowed at run time. Both are held, the rule's witnesses beside p309 and p310, and the census header's swallow
  // clause and swallowed()'s docstring name them, which the third header pin in the plants-row test holds.
  { dir: W, file: "p345-r7d-s19-allsettled-bound-array-residual.test.ts", leg: true, cls: "shared", gap: null, swallow: [], holds: "a stated residual boundary: the swallow read follows the chain on the call itself and takes Promise.allSettled's own array literal only, so Promise.allSettled over a name an array holding the call was bound to, const ps = [inBrowser(t, body)]; await Promise.allSettled(ps), is not read, swallow [] under the census before round 6, at the round-6 head and since, while the rejection is swallowed at run time, a witness of the rule the census header's swallow clause states (the review's round 7)" }, // s19: the array bound, then settled
  { dir: W, file: "p346-r7d-s20-allsettled-spread-bound-array-residual.test.ts", leg: true, cls: "shared", gap: null, swallow: [], holds: "a stated residual boundary: Promise.allSettled over a spread of a name an array holding the call was bound to, await Promise.allSettled([...ps]), is not read either (the spread stands between the array literal the read takes and the call), swallow [] under the census before round 6, at the round-6 head and since, while the rejection is swallowed at run time, a witness of the rule the census header's swallow clause states (the review's round 7)" }, // s20: the bound array spread into the literal
  // Appended past D's rows (p345, p346), in the order the round's plan fixed. B, as ruled by the maintainer's answers: p347, the
  // round-6 regression, a placeholder splitting the launcher's name in a chain crossing no path call, which round 6's concatenation
  // landed on the launcher's file as a local module, class none with no refusal over the stub launcher (the census before round 6
  // refused it as naming no file, the wrong reason), refused through no closed form since every folded text is resolved; p348 and
  // p349, the launcher's .cjs twin, a real-viewer-leg.cjs beside the stub launcher that launches Firefox itself, loaded by a literal
  // and by a path call, read as the launcher before round 7 (class shared, gap null, no refusal, a Firefox leg rostered as a Chromium
  // one) and read by its own content since, resolveSpec and candidatesOf taking the file that stands at the spelled path first, the
  // bundler's order. C, the climb and the return arm as ruled, one row per operator and per road: p350 to p352, a text as either
  // operand of &&, || and ?? standing as a foreign callee's argument; p353, a generator's yield, the next road out of a function
  // past the return arm's reach, held; then one row per arm of the clause beyond the ruled rows (a parameter's default, a binding
  // element's default, a conditional initializer, a nullish initializer, a property target, a class-field target, an exported
  // declaration, an object literal at depth and as a new expression's argument), each class none with no refusal before round 7;
  // p363, a chained const a require loads, the recursion's control, own Firefox before and after; p364, the return arm's arrow
  // body; and p365, a text read through a member of its own, past the climb's reach, held.
  { dir: W, file: "p347-r7b-b9-placeholder-split-launcher-name.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p347-r7b-b9-placeholder-split-launcher-name.test.ts:2: " + SPEC_NO_CLOSED_FORM }, // b9: require("ui/webview/real-viewer-" + process.env.PLANT_X + "leg") (before round 7: class none, no refusal; before round 6: loads ui/webview/real-viewer-/<process.env.PLANT_X>/leg, which names no file)
  { dir: W, file: "p348-r7b-t1-cjs-twin-literal.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p348-r7b-t1-cjs-twin-literal.test.ts:2: loads ui/webview/real-viewer-leg.cjs, which names a playwright package (playwright)" }, // t1: require("./real-viewer-leg.cjs") beside the stub launcher, resolveSpec's road (before round 7: class shared, gap null, no refusal, bound as the launcher)
  { dir: W, file: "p349-r7b-t2-cjs-twin-path-call.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p349-r7b-t2-cjs-twin-path-call.test.ts:3: loads ui/webview/real-viewer-leg.cjs, which names a playwright package (playwright)" }, // t2: the same through path.resolve, resolveLocal's candidatesOf road (before round 7: class shared, gap null, no refusal)
  { dir: W, file: "p350-r7c-h1-logical-and-call-argument.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p350-r7c-h1-logical-and-call-argument.test.ts:3: " + NET_HEAD + NET_PW + NET_NO_REACH }, // h1: load(process.env.PLANT_ON && PW) (before round 7: class none, no refusal)
  { dir: W, file: "p351-r7c-h2-logical-or-call-argument.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p351-r7c-h2-logical-or-call-argument.test.ts:3: " + NET_HEAD + NET_PW + NET_NO_REACH }, // h2: load(process.env.PLANT_PKG || PW) (before round 7: class none, no refusal)
  { dir: W, file: "p352-r7c-h3-nullish-call-argument.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p352-r7c-h3-nullish-call-argument.test.ts:3: " + NET_HEAD + NET_PW + NET_NO_REACH }, // h3: load(process.env.PLANT_PKG ?? PW) (before round 7: class none, no refusal)
  { dir: W, file: "p353-r7c-r2-generator-yield-boundary.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, holds: "a stated residual boundary: the bound-name clause's boundary past the return arm, which reads a return statement's expression and an arrow's expression body and no other road out of a function: a text a generator yields, function* names() { yield \"playwright\"; }, handed through names().next().value to a callee the walker knows no loader for, is class none with no refusal before and after round 7, the witness the census header names for the arm's reach" }, // r2
  { dir: W, file: "p354-r7c-q33-parameter-default.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p354-r7c-q33-parameter-default.test.ts:3: " + NET_HEAD + NET_BOUND_PW("spec", 3) + NET_NO_REACH }, // q33: function open(spec = PW) { return load(spec); } (before round 7: class none, no refusal)
  { dir: W, file: "p355-r7c-q34-binding-element-default.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p355-r7c-q34-binding-element-default.test.ts:3: " + NET_HEAD + NET_BOUND_PW("spec", 4) + NET_NO_REACH }, // q34: const { spec = PW } = {} (before round 7: class none, no refusal)
  { dir: W, file: "p356-r7c-q42-conditional-initializer.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p356-r7c-q42-conditional-initializer.test.ts:3: " + NET_HEAD + NET_BOUND_PW_CORE("name", 4) + MORE(1) + NET_NO_REACH }, // q42: const name = cond ? "playwright-core" : PW, each branch a mention through the climb (before round 7: class none, no refusal)
  { dir: W, file: "p357-r7c-q43-nullish-initializer.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p357-r7c-q43-nullish-initializer.test.ts:3: " + NET_HEAD + NET_BOUND_PW("name", 4) + NET_NO_REACH }, // q43: const name = process.env.PW_PKG ?? PW (before round 7: class none, no refusal)
  { dir: W, file: "p358-r7c-q25-member-assignment-target.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p358-r7c-q25-member-assignment-target.test.ts:4: " + NET_HEAD + NET_BOUND_TARGET("cfg.pkg") + NET_NO_REACH }, // q25: cfg.pkg = PW, a property target (before round 7: class none, no refusal)
  { dir: W, file: "p359-r7c-q35-class-field-target.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p359-r7c-q35-class-field-target.test.ts:3: " + NET_HEAD + NET_BOUND_TARGET("the class field spec") + NET_NO_REACH }, // q35: class Cfg { spec = PW } (before round 7: class none, no refusal)
  { dir: W, file: "p360-r7c-c13-exported-const.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p360-r7c-c13-exported-const.test.ts:2: " + NET_HEAD + NET_BOUND_EXPORTED("PKG") + NET_NO_REACH }, // c13: export const PKG = PW, an exported declaration an importer may hand anywhere (before round 7: class none, no refusal)
  { dir: W, file: "p361-r7c-q29-object-literal-at-depth.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p361-r7c-q29-object-literal-at-depth.test.ts:3: " + NET_HEAD + NET_PW + NET_NO_REACH }, // q29: load({ opts: { spec: PW } }), the object literal at depth (before round 7: class none, no refusal)
  { dir: W, file: "p362-r7c-q31-object-literal-new-argument.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p362-r7c-q31-object-literal-new-argument.test.ts:3: " + NET_HEAD + NET_PW + NET_NO_REACH }, // q31: new Loader({ spec: PW }), the object literal as a new expression's argument (before round 7: class none, no refusal)
  { dir: W, file: "p363-r7c-c03-chained-const-require-control.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: ["firefox"], playwright: ["playwright"], launches: [".launch("], launcherImported: false, holds: "the no-refusal half of a pair whose partner reds: p332 (a const bound to the package's name and handed to a callee the walker knows no loader for, refused by the bound-name clause): a const bound to the package's name and bound in turn to a second const that a require loads is own Firefox with no refusal before and after round 7, the clause accounting the reference through the chained name (without that recursion the clause refuses this row falsely)" }, // c03: const PKG = PW; const SPEC = PKG; require(SPEC)
  { dir: W, file: "p364-r7c-r1-arrow-body-return.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p364-r7c-r1-arrow-body-return.test.ts:3: " + NET_HEAD + NET_RETURNED + NET_NO_REACH }, // r1: const pkg = () => PW, the return arm's arrow body (before round 7: class none, no refusal)
  { dir: W, file: "p365-r7c-h4-member-of-the-text-boundary.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, holds: "a stated residual boundary: the climb's boundary, a text read through a member of its own, load(\"playwright\".trim()), stands in no position the net reads, since the climb passes the wrappers, a conditional's branches and a logical's operands and no other expression, class none with no refusal before and after round 7, the witness the census header names for the climb's reach" }, // h4
  // three controls of the clause's own reading, each green before and after round 7 and red under the mutation that drops what it
  // holds (executed and recorded in the PR's notes): p366, a bound name read only where isValueRef reads no reference (a plain
  // assignment's target, a property name, a destructuring's property name, a type query, a label); p367, a bound name read through a `+` chain that a require loads,
  // chainRoot's climb through a `+` operand; p368, two names bound to each other in a cycle, the recursion's guard. And p369, the
  // clause's refusal of a declaration whose name is a binding pattern, const [head] = PW, a target whose references it does not read
  // (the text's characters, never the package's name, reach the pattern, so the refusal is on the safe side and the row pins the arm).
  { dir: W, file: "p366-r7c-c19-bound-name-read-in-no-value-position-control.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, holds: "the no-refusal half of a pair whose partner reds: p337 (a let bound to the package's name and read as a foreign callee's argument, refused by the bound-name clause): a let bound to the package's name and read only as a plain assignment's target, a property name, a destructuring's property name, a type query and a label, no value reference among them, is class none with no refusal before and after round 7 (the clause's isValueRef reads none of them as a reference, and with any of those exclusions dropped the clause refuses this row falsely)" }, // c19
  { dir: W, file: "p367-r7c-c10-chained-plus-const-require-control.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: ["firefox"], launches: [".launch("], launcherImported: false, holds: "the no-refusal half of a pair whose partner reds: p332 (a const bound to the package's name and handed to a callee the walker knows no loader for, refused by the bound-name clause): a const bound to the package's name, read inside a + chain that initializes a second const a require loads, is own Firefox with no refusal before and after round 7, the clause climbing the + operand to the chain's root and accounting the reference through the second name (the row holds no playwright field: the census before round 6 joined the chain with a slash, the spelling p285 and its kin carry)" }, // c10: const PKG = PW; const SPEC = PKG + "-core"; require(SPEC)
  { dir: W, file: "p368-r7c-c20-bound-names-in-a-cycle-control.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, holds: "the no-refusal half of a pair whose partner reds: p338 (a let bound to the package's name by an assignment and read as a foreign callee's argument, refused by the bound-name clause): two lets bound to each other in a cycle, let a = \"playwright\"; let b = a; a = b, with no other reference, are class none with no refusal before and after round 7, the clause's recursion ending at the name it has already read (without that guard the census throws on this row)" }, // c20
  { dir: W, file: "p369-r7c-d1-destructured-declaration-target.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p369-r7c-d1-destructured-declaration-target.test.ts:3: " + NET_HEAD + NET_BOUND_TARGET("[head]") + NET_NO_REACH }, // d1: const [head] = PW handed to a foreign callee (before round 7: class none, no refusal)
  // B, the bundler's mapping (correctness-1, the maintainer's answer after the round's first build): resolveSpec and candidatesOf read
  // a script spelling as the bundler does, the file at the spelled path first, then its rewrite, a .js or .jsx as the .ts then the
  // .tsx, a .cjs as the .cts, a .mjs as the .mts, where the round's first build read a .cjs or .mjs that names no file as the .ts
  // beside it. p370, a .cjs spelling in the plants root no-cjs-twin (in the main tree the .cjs twin, p348 and p349, is the file the
  // bundler loads for that spelling), whose launcher has a real-viewer-leg.cts beside it that launches Firefox, and p371, the .mjs
  // spelling beside the main tree's launcher and its real-viewer-leg.mts: class shared, gap null, no refusal before round 7 (a
  // Firefox leg rostered as a Chromium one), refused by the twin's content since. p372, a .js spelling whose .tsx the bundler loads
  // (no .ts beside it; the .tsx carries JSX and parses as TSX alone), and p373, a .jsx spelling of the launcher: each refused as
  // naming no file before, read as the .tsx and bound as the launcher since. p374, a .jsx module loaded as spelled: skipped as no
  // script before (class none, no refusal), read since. p375, a .js spelling beside a declaration file alone: read as the declaration
  // before, which the bundler never loads, and refused as naming no file since. Each red under the census before round 6 and under
  // the round's first build alike. And p376, in no-cjs-twin, a .js spelling with a real-viewer-leg.js beside that root's launcher,
  // which launches Firefox: the spelled path first, so the .js is read and not the launcher (bound as the launcher before round 7,
  // when the .ts came first, and read as the .js since the round's first build); with the .cts beside the main tree's .cjs twin it
  // holds the spelled path first at both roads under the bundler's mapping, where a .cjs never reaches the launcher's .ts. The
  // parity test after resolveLocal's bases test holds each planted specifier's file equal to the bundler's.
  { dir: W, root: "no-cjs-twin", file: "p370-r7b-m1-cts-beside-the-launcher.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p370-r7b-m1-cts-beside-the-launcher.test.ts:2: loads ui/webview/real-viewer-leg.cts, which names a playwright package (playwright)" }, // m1: require("./real-viewer-leg.cjs"), no .cjs beside the launcher, a .cts there (before round 7: class shared, gap null, no refusal, bound as the launcher)
  { dir: W, file: "p371-r7b-m2-mts-beside-the-launcher.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p371-r7b-m2-mts-beside-the-launcher.test.ts:2: loads ui/webview/real-viewer-leg.mts, which names a playwright package (playwright)" }, // m2: import { inBrowser } from "./real-viewer-leg.mjs", no .mjs beside the launcher, a .mts there (before round 7: class shared, gap null, no refusal)
  { dir: W, file: "p372-r7b-m3-js-spelling-reaches-a-tsx.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p372-r7b-m3-js-spelling-reaches-a-tsx.test.ts:2: loads ui/webview/bundler-tsx-helper.tsx, which names a playwright package (playwright)" }, // m3: require("./bundler-tsx-helper.js") with the .tsx alone (before round 7: loads ./bundler-tsx-helper.js, which names no file)
  { dir: W, file: "p373-r7b-m4-jsx-spelling-of-the-launcher.test.ts", leg: true, cls: "shared", gap: null, launcherImported: true }, // m4: import { inBrowser } from "./real-viewer-leg.jsx" (before round 7: loads ./real-viewer-leg.jsx, which names no file)
  { dir: W, file: "p374-r7b-m5-jsx-module-loaded-as-spelled.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p374-r7b-m5-jsx-module-loaded-as-spelled.test.ts:2: loads ui/webview/bundler-jsx-helper.jsx, which names a playwright package (playwright)" }, // m5: require("./bundler-jsx-helper.jsx") (before round 7: class none, no refusal, the .jsx skipped as no script)
  { dir: W, file: "p375-r7b-m6-js-spelling-with-a-declaration-file-alone.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p375-r7b-m6-js-spelling-with-a-declaration-file-alone.test.ts:2: loads ./bundler-dts-only.js, which names no file in the tree" }, // m6: require("./bundler-dts-only.js") beside bundler-dts-only.d.ts alone (before round 7: class none, no refusal, the declaration read)
  { dir: W, root: "no-cjs-twin", file: "p376-r7b-m7-js-file-beside-the-launcher.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p376-r7b-m7-js-file-beside-the-launcher.test.ts:2: loads ui/webview/real-viewer-leg.js, which names a playwright package (playwright)" }, // m7: require("./real-viewer-leg.js") with a real-viewer-leg.js beside the launcher (before round 7: class shared, gap null, no refusal, bound as the launcher, the .ts first)
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

/** git over one store: the real-rows test below reads the checkout's store (REPO); the scratch-clone test after it reads stores it made. */
function gitIn(repo: string): (args: string[]) => { status: number | null; stdout: string; stderr: string } {
  return (args: string[]) => spawnSync("git", ["-C", repo, ...args], { encoding: "utf8", timeout: 120000 });
}

/** The exclusions header's bound line named by its 1-based line number, for a verdict: derived from the text (the line that opens
 *  "# Every grandfather reason, "), never a constant, so a header that gains a line above it moves the name with it. */
function boundLineAt(text: string): string {
  return EXCLUDED + " line " + (text.split("\n").findIndex((l) => l.startsWith("# Every grandfather reason, ")) + 1);
}

/** Whether the bound commit can be read in the store: verdict null when it is present, or when it was fetched at depth 1 into a
 *  SHALLOW store (CI's depth-1 checkout, the one place this test fetches); otherwise the hold-off sentence, a red never a pass.
 *  The fetch is gated on `git rev-parse --is-shallow-repository` printing true. A full store is never fetched into: every commit
 *  that carries this test descends from the bound (main at the roster's creation is the branch point), so a full store that lacks
 *  the bound holds a checkout the bound is not an ancestor of, which means the header's bound line names the wrong commit; and a
 *  --depth fetch into a full store writes .git/shallow and makes the WHOLE store shallow, for every worktree that shares it (measured
 *  in a scratch store: a full clone lacking the commit, fetched at depth 1, reads --is-shallow-repository true after, the fetched
 *  commit parentless). A store whose shape read prints anything but "true" (an older git, an error) is treated as full: no fetch,
 *  the hold-off, the restricted side. `fetched` is true only when the depth-1 fetch ran and brought the commit; a fetch that failed,
 *  or that left the commit unreadable, reports false beside its hold-off, as does a store that needed no fetch (the scratch-clone
 *  test pins both values). */
function boundReadable(git: (args: string[]) => { status: number | null; stdout: string; stderr: string }, sha: string, boundAt: string): { verdict: string | null; fetched: boolean } {
  if (git(["cat-file", "-e", sha]).status === 0) return { verdict: null, fetched: false };
  const shallow = git(["rev-parse", "--is-shallow-repository"]).stdout.trim();
  if (shallow !== "true") return { verdict: boundAt + ": the bound commit " + sha + " is not in this clone and the clone is not shallow (git rev-parse --is-shallow-repository printed " + JSON.stringify(shallow) + "), so the commit is not an ancestor of this checkout and the bound line names a commit that is not main at the roster's creation: fix the line (no fetch is made into a full store, since a depth-1 fetch would make the whole store shallow); a red hold-off, not a pass", fetched: false };
  const fetch = git(["fetch", "--depth=1", "origin", sha]);
  if (fetch.status !== 0) return { verdict: boundAt + ": the grandfather check could not run: commit " + sha + " is not in this shallow clone and `git fetch --depth=1 origin " + sha + "` failed (exit " + fetch.status + "): " + fetch.stderr.trim() + "; the bound cannot be read here, so this is a red hold-off, not a pass", fetched: false };
  const have = git(["cat-file", "-e", sha]);
  if (have.status !== 0) return { verdict: boundAt + ": the grandfather check could not run: after `git fetch --depth=1 origin " + sha + "` into this shallow clone the commit is still not readable (git cat-file -e exit " + have.status + "): " + have.stderr.trim() + "; a red hold-off, not a pass", fetched: false };
  return { verdict: null, fetched: true };
}

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

test("every grandfather row's source existed at the commit the exclusions header binds the reason to: the header holds one bound line; the commit is fetched at depth 1 only when the checkout is itself shallow and lacks it, a fetch or object read that fails is a red hold-off naming the reason, never a pass, and a full clone that lacks it is a red hold-off naming the bound line with no fetch (boundReadable, driven over scratch clones by the next test); a source absent at that commit is refused with the remedy; the bound line says it reads the file's age, not what the file did there; the per-row verdict is one function, boundVerdict, driven here over synthetic git results (exit 0, 128 with each of git's two wordings, 128 with another message, another status) and over two reads through git itself at the bound (a path never in the tree, a source added after the bound)", async (t) => {
  const { ENGINE_PHRASE, EMBEDDED_PHRASE } = await load();
  const text = read(path.join(EXT, EXCLUDED));
  const { sentence, sha, embedded } = headerOf(text);
  const boundLine = text.split("\n").find((l) => l.startsWith("# Every grandfather reason, ")) as string;
  assert.ok(boundLine.includes("reads the file's age, not what it did there"), "the bound line names its residual: a source present at the commit without a browser launch may carry the reason (the bound reads the file's age); one that gained its launch later is rostered once it passes the gate, or carries the engine or embedded-driver form when one is true of it");
  const git = gitIn(REPO);
  // the bound's readability, gated on the store's shape (boundReadable: a shallow checkout that lacks it is fetched at depth 1, a
  // full one is never fetched into and takes the hold-off naming the bound line by its number, derived from the text)
  const bound = boundReadable(git, sha, boundLineAt(text));
  if (bound.verdict !== null) assert.fail(bound.verdict);
  if (bound.fetched) t.diagnostic("fetched commit " + sha + " at depth 1 into the shallow checkout (the clone lacked it)");
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

test("the bound fetch is gated on the store's shape (regression-3, round 5): boundReadable driven over scratch clones with their own .git under the temp dir, made and removed here: a shallow clone that lacks the bound fetches it at depth 1, reads it and stays shallow; a full clone that lacks it is NOT fetched into (no .git/shallow written, no FETCH_HEAD, the store non-shallow, the commit still absent) and takes the hold-off naming the bound line and saying the line is wrong; a full clone that holds it reads it with no fetch; and in the shallow clone a fetch of a commit the remote lacks is the fetch-failed hold-off, never a pass", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "cbl-bound-gate-"));
  try {
    const sh = (cwd: string, args: string[]) => { const r = spawnSync("git", ["-C", cwd, ...args], { encoding: "utf8", timeout: 120000 }); assert.equal(r.status, 0, "git " + args.join(" ") + " in " + cwd + ": " + r.stderr); return r.stdout.trim(); };
    const remote = path.join(root, "remote.git"), work = path.join(root, "work"), full = path.join(root, "full"), shallow = path.join(root, "shallow");
    // three fixture facts found by execution (git 2.43): the bare remote takes --initial-branch=main since the pushes go to main
    // (else the remote HEAD names another branch and every clone comes up empty and non-shallow); the clones go over file:// URLs
    // since git ignores --depth for a clone by local path (its local-transport shortcut would give a full clone named shallow);
    // and the remote holds two commits before the shallow clone is taken, since a depth-1 clone whose tip is the root commit cuts
    // nothing and reports --is-shallow-repository false
    sh(root, ["init", "--bare", "-q", "--initial-branch=main", remote]);
    sh(root, ["clone", "-q", remote, work]);
    for (const [k, v] of [["user.name", "t"], ["user.email", "t@example.invalid"]]) sh(work, ["config", k, v]);
    const commit = (body: string) => { fs.writeFileSync(path.join(work, "a.txt"), body + "\n"); sh(work, ["add", "a.txt"]); sh(work, ["commit", "-q", "-m", body]); sh(work, ["push", "-q", "origin", "HEAD:refs/heads/main"]); return sh(work, ["rev-parse", "HEAD"]); };
    const one = commit("one"); commit("two");
    sh(root, ["clone", "-q", "file://" + remote, full]);
    sh(root, ["clone", "-q", "--depth=1", "file://" + remote, shallow]);
    assert.equal(sh(shallow, ["rev-parse", "--is-shallow-repository"]), "true", "the fixture's shallow clone is shallow (a path remote, or a one-commit remote, would have given a full clone)");
    assert.equal(sh(full, ["rev-parse", "--is-shallow-repository"]), "false", "the fixture's full clone is full");
    const bound = commit("three");   // the bound: pushed after both clones were taken, so neither holds it
    const AT = boundLineAt(read(path.join(EXT, EXCLUDED)));   // the label the real-rows test passes, derived the same way
    // the shallow clone lacking the bound: fetched at depth 1 and readable, the store shallow as it was
    const s = boundReadable(gitIn(shallow), bound, AT);
    assert.deepEqual(s, { verdict: null, fetched: true }, "a shallow clone lacking the bound fetches it at depth 1 and reads it: " + s.verdict);
    assert.equal(gitIn(shallow)(["cat-file", "-e", bound]).status, 0, "the bound is readable in the shallow clone after the fetch");
    assert.equal(sh(shallow, ["rev-parse", "--is-shallow-repository"]), "true", "the shallow clone stays shallow");
    // the full clone lacking the bound: no fetch, the hold-off naming the bound line and saying the line is wrong, the store untouched
    const f = boundReadable(gitIn(full), bound, AT);
    assert.ok(f.verdict !== null && f.verdict.startsWith(AT + ": the bound commit " + bound + " is not in this clone and the clone is not shallow (git rev-parse --is-shallow-repository printed \"false\")") && f.verdict.includes("the bound line names a commit that is not main at the roster's creation: fix the line") && f.verdict.includes("no fetch is made into a full store") && f.verdict.endsWith("a red hold-off, not a pass"), "a full clone lacking the bound: the hold-off names the bound line, says the line is wrong and that no fetch is made, never a pass: " + f.verdict);
    assert.equal(f.fetched, false, "and reports no fetch");
    assert.ok(!fs.existsSync(path.join(full, ".git", "shallow")), "no .git/shallow was written into the full clone");
    assert.ok(!fs.existsSync(path.join(full, ".git", "FETCH_HEAD")), "no fetch ran in the full clone (a clone writes no FETCH_HEAD; a fetch, failed or not, does)");
    assert.equal(sh(full, ["rev-parse", "--is-shallow-repository"]), "false", "the full clone stays non-shallow");
    assert.notEqual(gitIn(full)(["cat-file", "-e", bound]).status, 0, "the bound stays absent from the full clone (nothing was fetched)");
    // the full clone holding the commit: read with no fetch
    const p = boundReadable(gitIn(full), one, AT);
    assert.deepEqual(p, { verdict: null, fetched: false }, "a full clone holding the bound reads it with no fetch");
    assert.ok(!fs.existsSync(path.join(full, ".git", "FETCH_HEAD")), "still no fetch in the full clone");
    // the shallow clone asked for a commit the remote lacks: the fetch fails and the verdict is the fetch-failed hold-off
    const absent = "0123456789abcdef0123456789abcdef01234567";
    const a = boundReadable(gitIn(shallow), absent, AT);
    assert.ok(a.verdict !== null && a.verdict.startsWith(AT + ": the grandfather check could not run: commit " + absent + " is not in this shallow clone and `git fetch --depth=1 origin " + absent + "` failed (exit ") && a.verdict.endsWith("a red hold-off, not a pass") && a.fetched === false, "a shallow clone whose depth-1 fetch fails: the hold-off naming the fetch and its exit, never a pass: " + a.verdict);
  } finally { fs.rmSync(root, { recursive: true, force: true }); }
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
  // the header-pin line FIRST (fresh-3, round 6): the census header's swallow clause states the widened read, a shared call whose
  // rejection is swallowed where it stands by a try with a catch through callbacks, or by .catch, .then's second argument or
  // Promise.allSettled, with .finally and a bare .then stated as not swallows. Two sentence pins over the module's leading comment
  // block (its // lines joined, since the clause wraps), before the rows: the round-6 swallow rows below (p292 to p305, p309 and p310, the closing pass's stated residuals, and p345 and p346, the review's round 7's) hold the
  // read's OUTCOME as a property, and this holds that the header SAYS what it reads, so a clause reworded back to the same-function
  // try reds here first. Holds the sentence: a reword of either phrase moves this pin too.
  const swallowHeader = moduleHeader();
  assert.ok(swallowHeader.includes("whose rejection is swallowed where it stands"), "the census header's swallow clause reads the rejection's fate, not a try statement's position: the leading comment block says a shared inBrowser call whose rejection is swallowed where it stands (before round 6 it said inside a try statement that has a catch clause, the same-function read the round-5 review found under-reads .catch, .then's second argument, Promise.allSettled and a callback inside a try). Holds the sentence: a reword moves this pin too");
  assert.ok(swallowHeader.includes(".finally and a bare .then hand the rejection on and are not swallows"), "the census header's swallow clause states the read's boundary on the promise chain, .finally and a bare .then hand the rejection on and are not swallows (the p297 and p298 controls hold the outcome). Holds the sentence: a reword moves this pin too");
  // the third header pin (the review's round 7, extra7-1, the owner's call 3 held mechanically): the clause NAMES its witnesses. The
  // expected set is DERIVED from the table, every row with a swallow field of [] and holds beginning "a stated residual boundary: "
  // (the swallow under-reads the table holds), and each of the two homes the call named, the census header's swallow clause (the
  // leading block's text from its one swallow: field to its embedded: field) and swallowed()'s docstring (the doc block directly
  // above its declaration), names exactly that set as (pN). A witness dropped from either home, an under-read row added without
  // its name there, or a home naming a row that is no under-read reds here, the message naming the id and the home. The derivation
  // cannot pass empty: it must be non-empty and hold the three witnesses the call named. Holds the PROPERTY (a reword that keeps
  // every (pN) stays green; the two pins above hold the sentences).
  const pidOf = (p: Plant): string => (/^p\d+/.exec(p.file) || [""])[0];
  const pidNum = (a: string, b: string): number => Number(a.slice(1)) - Number(b.slice(1));
  const namedIn = (text: string): string[] => [...new Set([...text.matchAll(/\(p(\d+)\)/g)].map((m) => "p" + m[1]))].sort(pidNum);
  const underReads = PLANT_TABLE.filter((p) => Array.isArray(p.swallow) && p.swallow.length === 0 && typeof p.holds === "string" && p.holds.startsWith("a stated residual boundary: ")).map(pidOf).sort(pidNum);
  assert.ok(underReads.length > 0, "the plant table's swallow under-reads (rows with swallow [] and holds beginning \"a stated residual boundary: \") are not empty: an empty derivation would hold both homes to naming nothing and pass, so it reds here. Holds the property");
  for (const w of ["p304", "p309", "p310"]) assert.ok(underReads.includes(w), "the plant table's swallow under-reads include " + w + ", a witness the owner's call 3 named, so the derivation reads the rows it is about; got " + JSON.stringify(underReads) + ". Holds the property");
  const clauseAt = swallowHeader.indexOf("swallow:"), clauseEnd = swallowHeader.indexOf("embedded:");
  assert.ok(clauseAt >= 0 && clauseEnd > clauseAt && swallowHeader.indexOf("swallow:", clauseAt + 1) < 0, "the census header carries one swallow: field, before its embedded: field: the witness read slices the clause between them");
  const moduleSrc = read(MODULE), declAt = moduleSrc.indexOf("const swallowed = "), docAt = moduleSrc.lastIndexOf("/**", declAt), docEnd = moduleSrc.indexOf("*/", docAt);
  assert.ok(declAt > 0 && docAt > 0 && docEnd < declAt && moduleSrc.slice(docEnd + 2, declAt).trim() === "", "swallowed()'s docstring stands directly above its declaration: the witness read takes the doc block there");
  for (const [home, text] of [["the census header's swallow clause", swallowHeader.slice(clauseAt, clauseEnd)], ["swallowed()'s docstring", moduleSrc.slice(docAt, docEnd)]]) {
    const named = namedIn(text);
    for (const w of underReads) assert.ok(named.includes(w), w + " is missing from " + home + ": every swallow under-read the plant table holds (" + JSON.stringify(underReads) + ") is named there as (" + w + "), so a disclosed residual keeps its named witness in both homes the owner's call 3 named. Holds the property");
    for (const w of named) assert.ok(underReads.includes(w), home + " names (" + w + "), which is no swallow under-read of the plant table (" + JSON.stringify(underReads) + "): a witness named in prose is a row with swallow [] and holds a stated residual boundary. Holds the property");
  }
  // the table and the fixture tree name the same files. A plants root of its own is every directory of the fixture tree beside ui/
  // and vscode-extension/ (the relative-node-modules subtree aside, which a test of its own reads over a synthetic root), derived
  // from the tree, so a root added without rows, or rows naming a root that is not there, is red here and no plant goes unread
  const ownRoots = fs.readdirSync(PLANTS, { withFileTypes: true }).filter((e) => e.isDirectory() && !["ui", "vscode-extension", "relative-node-modules"].includes(e.name)).map((e) => e.name).sort();
  assert.deepEqual(ownRoots, [...new Set(PLANT_TABLE.flatMap((p) => (p.root ? [p.root] : [])))].sort(), "every directory of the fixture tree beside ui/ and vscode-extension/ (relative-node-modules aside) is a plants root of its own that rows name, and every root a row names is such a directory");
  for (const o of ownRoots) assert.ok(fs.existsSync(path.join(PLANTS, o, "ui", "webview", "real-viewer-leg.ts")), "the plants root " + o + " carries its own stub ui/webview/real-viewer-leg.ts for its plants to import");
  const onDisk = [W, "vscode-extension/src"].flatMap((d) => fs.readdirSync(path.join(PLANTS, d)).filter((f) => f.endsWith(".test.ts")).map((f) => d + "/" + f))
    .concat(ownRoots.flatMap((o) => [W, "vscode-extension/src"].filter((d) => fs.existsSync(path.join(PLANTS, o, d))).flatMap((d) => fs.readdirSync(path.join(PLANTS, o, d)).filter((f) => f.endsWith(".test.ts")).map((f) => o + "/" + d + "/" + f)))).sort();
  assert.deepEqual(onDisk, PLANT_TABLE.map((p) => (p.root ? p.root + "/" : "") + p.dir + "/" + p.file).sort(), "the plant table names every fixture and no other (a fixture added without a row is a plant with no expected outcome)");
  assert.ok(fs.existsSync(STUB_LAUNCHER), "the fixture tree carries a stub ui/webview/real-viewer-leg.ts for the plants to import");
  // one census per root, the main tree's first; a row is judged by its own root's
  const runs = new Map(["", ...ownRoots].map((o) => [o, { c: census(path.join(PLANTS, o)), strict: census(path.join(PLANTS, o), { strictComputed: true }) }] as [string, { c: ReturnType<Census["census"]>; strict: ReturnType<Census["census"]> }]));
  for (const p of PLANT_TABLE) {
    const { c, strict } = runs.get(p.root || "") as { c: ReturnType<Census["census"]>; strict: ReturnType<Census["census"]> };
    const bundle = bundleOf(p), r = c.byBundle.get(bundle);
    const at = (p.root ? p.root + "/" : "") + p.dir + "/" + p.file + ": ";
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
    if (p.swallow) assert.deepEqual(r.swallow, p.swallow, at + "shared calls whose rejection is swallowed (a try with a catch, .catch, .then's second argument or Promise.allSettled), by line");
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
  // with every plant in neither file, the census names exactly the plants that are legs, per root
  for (const [o, { c }] of runs) {
    const rows = PLANT_TABLE.filter((p) => (p.root || "") === o), where = o ? " (the plants root " + o + ")" : "";
    const expectedLegs = rows.filter((p) => p.leg).map(bundleOf).sort();
    assert.deepEqual(c.legs, expectedLegs, "the plants the census calls legs" + where);
    assert.equal(c.refusals.length, rows.filter((p) => p.refused).length, "one refusal per refused plant" + where + ": " + JSON.stringify(c.refusals));
  }
  // the census header states the third residual beside the other two: a browser reached without spelling a playwright package or
  // the launcher is unread by the walker, class none, no refusal. A text pin on the header's prose (its // lines joined, since the
  // sentence wraps): it holds that the header names the three forms and the outcome, not that the walker behaves so; the CLASS is
  // executed above by the p68 to p71 rows (a package name from the environment, another driver package, a package whose name
  // contains a tracked spelling, a spawned binary) and by p234 and p235 (a driver file the test spawns by path or forks by URL,
  // the form correctness-4 named in round 5), each class none with no refusal. The read is the module's LEADING comment
  // block, the // lines before its first line of code, so a sentence moved into a body comment does not satisfy it. Each of the
  // three assertions holds the SENTENCE: a reword of the header's prose moves the pin too.
  const moduleLines = read(MODULE).split("\n");
  const codeAt = moduleLines.findIndex((l) => !l.startsWith("//") && l.trim() !== "");
  const header = moduleLines.slice(0, codeAt < 0 ? moduleLines.length : codeAt).filter((l) => l.startsWith("//")).map((l) => l.replace(/^\/\/ ?/, "")).join(" ");
  assert.ok(header.includes("Three residuals, stated"), "the census header's leading comment block states three residuals (the string-typed parameter's fold, the non-loader call, and a browser reached without spelling a playwright package or the launcher); a header counting two has dropped the third, whose plants are the p68 to p71 rows above. A sentence moved into a body comment is not the header's. Holds the sentence: a reword moves this pin too");
  for (const form of ["another driver package such as puppeteer", "a browser binary it spawns", "a driver source whose package name arrives at run time", "a driver held in a separate file of the tree that the test spawns by path"]) assert.ok(header.includes(form), "the census header's leading comment block names the third residual's form " + JSON.stringify(form) + " (a text pin on the header's prose: the class that form takes is executed by the p68 to p71 rows above and, for the spawned-driver file, by p234 and p235 beside their import control p236; holds the sentence: a reword of the form moves this pin too)");
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

test("the census resolves each planted specifier to the file the bundler loads (correctness-1, the review's round 7, the maintainer's condition on the bundler's mapping): for every relative string specifier a plant loads by a form the bundler resolves when it bundles (an import or export declaration that is not type-only, an import = require, a require or import() call on a literal), a metafile build of a one-line entry beside the plant, with esbuild.js testBuild's platform, format, resolveExtensions and nodePaths and every file it resolves loaded empty, names the file the bundler loads, and resolveLocal, the census's local road over the one table resolveSpec reads too, names the same file, or both name none; the rows the mapping's arms name are in the population, so it cannot pass empty; before the mapping a .cjs or .mjs spelling that named no file was read as the .ts beside it, which this reds naming p370 and p371", async (t) => {
  // Holds the PROPERTY that the census and the bundler resolve alike, derived from the bundler's own resolution and never from a
  // table kept here: a rewrite the census reads otherwise (the round's first build read a .cjs or .mjs as the .ts beside it, where
  // the bundler reads the .cts or the .mts and never the .ts) reds naming the plant, the census's file and the bundler's. The census
  // side is resolveLocal, the local road's resolver over candidatesOf; resolveSpec, the launcher's road, reads the same table
  // (rewritesOf) and its reading is executed by the rows p370, p371, p373 and p376, which red when it binds or misses the launcher
  // otherwise. A specifier a plant builds at run time (a path call, a createRequire-bound loader) is resolved by node when the
  // test runs, not by the bundler, and is outside this population.
  const census = await load();
  const ts = census.loadTypescript();
  const req = createRequire(path.join(EXT, "package.json"));
  const esbuild = req("esbuild");
  const cfg = req(path.join(EXT, "esbuild.js")).testBuild();
  const ENTRY = "bundler-parity-entry.js";
  const lit = (e: any): string | null => (e && (ts.isStringLiteral(e) || ts.isNoSubstitutionTemplateLiteral(e)) ? e.text : null);
  const specsOf = (file: string): { spec: string; line: number }[] => {
    const sf = ts.createSourceFile(file, read(file), ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);
    const out: { spec: string; line: number }[] = [];
    const visit = (n: any): void => {
      let s: string | null = null;
      if (ts.isImportDeclaration(n) && !(n.importClause && n.importClause.isTypeOnly)) s = lit(n.moduleSpecifier);
      else if (ts.isExportDeclaration(n) && n.moduleSpecifier && !n.isTypeOnly) s = lit(n.moduleSpecifier);
      else if (ts.isImportEqualsDeclaration(n) && ts.isExternalModuleReference(n.moduleReference)) s = lit(n.moduleReference.expression);
      else if (ts.isCallExpression(n) && n.arguments.length > 0 && ((ts.isIdentifier(n.expression) && n.expression.text === "require") || n.expression.kind === ts.SyntaxKind.ImportKeyword)) s = lit(n.arguments[0]);
      if (s !== null && s.startsWith(".")) out.push({ spec: s, line: sf.getLineAndCharacterOfPosition(n.getStart(sf)).line + 1 });
      ts.forEachChild(n, visit);
    };
    visit(sf);
    return out;
  };
  const checked = new Set<string>(), mismatches: string[] = [];
  let specifiers = 0;
  for (const p of PLANT_TABLE) {
    const id = (/^p\d+/.exec(p.file) || [""])[0], root = path.join(PLANTS, p.root || ""), dir = path.join(root, p.dir), file = path.join(dir, p.file);
    for (const { spec, line } of specsOf(file)) {
      const cr = census.resolveLocal(file, spec, root);
      const censusFile = cr === null ? null : "ambiguous" in cr ? "two files (" + cr.ambiguous.map((a) => path.relative(root, a)).join(" and ") + ")" : path.relative(root, cr.abs);
      let bundlerFile: string | null = null;
      try {
        const res = await esbuild.build({ stdin: { contents: "require(" + JSON.stringify(spec) + ");\n", resolveDir: dir, sourcefile: ENTRY, loader: "js" }, bundle: true, write: false, metafile: true, platform: cfg.platform, format: cfg.format, resolveExtensions: cfg.resolveExtensions, nodePaths: cfg.nodePaths, logLevel: "silent", absWorkingDir: root, outdir: path.join(root, "out-parity"),
          plugins: [{ name: "resolve-only", setup(b: any) { b.onLoad({ filter: /.*/ }, () => ({ contents: "", loader: "js" })); } }] });
        const inputs = Object.keys(res.metafile.inputs).filter((k) => path.resolve(root, k) !== path.join(dir, ENTRY));
        assert.equal(inputs.length, 1, id + " loads " + spec + ": the bundler's metafile holds the entry and the one file the specifier names, got " + JSON.stringify(Object.keys(res.metafile.inputs)));
        bundlerFile = path.relative(root, path.resolve(root, inputs[0]));
      } catch (e) {
        // the bundler's own "cannot resolve" is its reading that no file answers the spelling; any other failure is no reading, red
        if (!/Could not resolve/.test(String((e as Error).message))) throw e;
      }
      checked.add(id);
      specifiers++;
      if (censusFile !== bundlerFile) mismatches.push(id + " (" + (p.root ? p.root + "/" : "") + p.dir + "/" + p.file + ":" + line + ") loads " + spec + ": the census resolves " + (censusFile === null ? "no file" : censusFile) + ", the bundler loads " + (bundlerFile === null ? "no file (it cannot resolve the specifier)" : bundlerFile));
    }
  }
  // the population, derived from the plants and required to hold the rows the mapping's arms name: the .js spelling of the launcher
  // (p23), the .cjs twin at its own spelling (p348) and the .mjs driver at its own (p236), the .cjs and .mjs spellings that name no
  // file (p370, p371), the .js spelling of a .tsx (p372), the .jsx spelling of the launcher (p373), the .jsx module as spelled (p374)
  // and the .js spelling beside a declaration file alone (p375), the .js spelling with a .js beside the launcher (p376), and the
  // extensionless spelling every launcher plant carries (p01)
  for (const id of ["p01", "p23", "p236", "p348", "p370", "p371", "p372", "p373", "p374", "p375", "p376"]) assert.ok(checked.has(id), "the parity population holds " + id + ", a row the bundler's mapping names, so the comparison reads the specifiers it is about (" + checked.size + " rows checked). Holds the property");
  t.diagnostic("bundler parity: " + specifiers + " specifiers over " + checked.size + " plant rows, " + mismatches.length + " resolved otherwise by the census");
  assert.deepEqual(mismatches, [], "each planted specifier the bundler resolves names the file the census resolves, and a specifier the bundler cannot resolve names no file to the census: a census that reads another file than the bundler loads judges a module no test runs. Holds the property: " + mismatches.join(" | "));
});

test("the plant table says which of its 51 round-3 rows (p38 to p88) discriminate against the census before round 3 and what the others hold: 45 red under that census (44 at round 3, and p74 since round 5's safety net refused a text that census passed), 6 hold one of four stated reasons instead (holds), and 3 of the 45 red on a property other than their section's and name the plant that carries it (carried); which of its 67 round-4 rows (p89 to p155) discriminate against the census before round 4: 62 red under that census and 5 hold a stated reason instead; and which of its round-5 rows (p156 to R5_LAST) discriminate against the census before round 5, the module at the round-4 head: every one red under it unless R5_HELD names it with its reason; and which of its round-6 rows (R6_FIRST to R6_LAST, p249 onward) discriminate against the census before round 6, the module at the round-5 head: every one red under it unless R6_HELD names it with its reason; the discrimination itself was established by running each earlier census over the plants, recorded in the PR's notes, and is not re-run here, since none of those censuses is in the tree at test time, so this test holds the TABLE's statement, not the fact", () => {
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
  // over the plants throwing whole before it judges a row, the shape correctness-1 named; for p208 to p211, a loaded helper's engine,
  // skip or swallow missing from the test's record, the field fresh-1's fold reads; for p215 to p229, a refusal the row does not
  // expect, the value-use arm's false refusal of a name position or a peeled satisfies or type assertion, the shape extra5-5 named;
  // for p232 and p233, the sentence of a refusal the row holds, which that census spelled by the node kind; for p237 to p244, class none with no refusal where the row expects
  // the specifier refusal, the closing pass's written let or var; for p246 to p248, class none with no refusal where the row expects
  // the net's sentence, the three arms of THE SAFETY NET no plant carried, planted at round 6) unless R5_HELD names it with
  // holds set (a control, a pin of an arm no plant carried, a stated boundary); a round-5 builder who adds a row moves R5_LAST to it
  // and, when the row stays green under that census, adds it to R5_HELD with holds set (the round-4 population above is closed)
  const NOT_RERUN5 = " (the discrimination was established by running the census before round 5, the module at the round-4 head, over the plants, recorded in the PR's notes, and is not re-run here, since that census is not in the tree at test time: this assertion holds the table's statement, not the fact)";
  const R5_FIRST = R4_LAST + 1, R5_LAST = 248;
  const R5_HELD = ["p197", "p198", "p200", "p201", "p202", "p207", "p212", "p213", "p214", "p230", "p231", "p234", "p235", "p236", "p245"];
  const R5_CARRIED: string[] = [];
  const inRound5 = (p: Plant) => num(p) >= R5_FIRST && num(p) <= R5_LAST;
  // the round-6 rows: R6_FIRST to R6_LAST, one row each, the statement below. R6_FIRST is a literal, not R5_LAST + 1, and the two
  // ranges are held to abut: p246 to p248, the three plants of THE SAFETY NET's arms that had none, are the round-5 range's (refused
  // by the census before round 6, red under the census before round 5), so a moved R5_LAST alone cannot slide them into the round-6
  // population, whose statement (red under the census before round 6) would be false for them and which this test cannot re-run
  const R6_FIRST = 249, R6_LAST = 376;
  const R6_HELD = ["p252", "p260", "p261", "p266", "p275", "p276", "p277", "p278", "p279", "p290", "p291", "p297", "p298", "p303", "p304", "p305", "p308", "p309", "p310", "p311", "p326", "p334", "p341", "p342", "p345", "p346", "p353", "p363", "p365", "p366", "p367", "p368"];
  const R6_CARRIED: string[] = [];
  const inRound6 = (p: Plant) => num(p) >= R6_FIRST && num(p) <= R6_LAST;
  const r5 = PLANT_TABLE.filter(inRound5);
  assert.deepEqual(PLANT_TABLE.filter((p) => num(p) > R5_LAST && !inRound6(p)).map(idOf), [], "every row past p" + R4_LAST + " is a round-5 row (to p" + R5_LAST + ") or a round-6 row (p" + R6_FIRST + " to p" + R6_LAST + ") and takes a verdict below: a row numbered between R5_LAST and R6_FIRST, or past R6_LAST, is outside every statement, so a builder who adds a row moves R5_LAST or R6_LAST to it" + NOT_RERUN5);
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
  // the round-6 rows, the same statement against the census before round 6 (the module at the round-5 head): the name read as a
  // binding (a function parameter or an inner declaration sharing a module const's name, which constInitializer read as that const
  // before round 6, so the package or the launcher passed in through the parameter loaded with class none and no refusal, under the
  // census and under the net alike, where the row expects the specifier refusal; p251, the literal control, red on the sentence and
  // the line, the net's at the call giving way to the walker's at the function; and, from the closing pass after the round's
  // verification, a parameter shadowing an unwritten let and a destructured parameter sharing a const's name, silent the same way,
  // p306 and p307), a loader or a playwright binding handed on as a
  // parameter's DEFAULT value (a value position both isName tests exempted as a name before round 6: class none with no refusal for
  // the loader rows, and for the binding rows class own with engines [firefox] and no refusal, the WebKit launch through the default
  // unread beside a read engine, where the row expects the arm's refusal; p255, p263 and p267 red on the sentence, the net's giving
  // way to the arm's), and a playwright load in a position the walker does not read (a class field, an object property, a promise
  // callback, an argument, a return: class own with engines [firefox] and no refusal before round 6, the read-through clause being
  // per module, where the row expects the load-position arm's refusal; p271 red on the sentence, the net's read-through giving way
  // to the arm's, as the round-3 rows p50, p51 and p57 re-aimed in place do, outside this population), a test calling inBrowser
  // directly and through a barrel that re-exports it (class shared, gap null, engines [] and no refusal before round 6, the barrel
  // call's engine unread, where the row expects the barrel arm's refusal at the import line), and a specifier assembled from literals
  // with no path call (the package or the launcher so spelled refused as naming no file, or by the net's clause 1 with a file at the
  // slash-joined path, where the row expects class own or shared; the relative chain resolved to the decoy with no refusal, where the
  // row expects the launcherBinds sentence at the module ./playwright), and a shared call whose rejection is swallowed by a spelling
  // the same-function try read missed, its promise handed to .catch, to .then's second argument or to Promise.allSettled, directly or
  // through a chain, the call inside a callback lexically inside a try, or a helper's such call (swallow [] before round 6 where the
  // row expects the call's line, or the helper's import line, the field a PROPERTY), and, from the review's round 7, a const or var
  // declared in a case block, a namespace body or a static block that shares a module const's name (refused through no closed form
  // by the census before round 6's by-name read, where the row expects the leg read, or the read-through clause for p314; at the
  // round-6 head class none with no refusal, and for the two var stop controls, p316 and p317, a false refusal through no closed
  // form) and a declaration with no initializer, p318 to p322 (refused before round 6 and at the round-6 head as loading a
  // placeholder that names no file, where the row expects the no-closed-form SENTENCE), and a module named like the launcher loaded
  // through a path call or a placeholder chain, p323 to p325 and p327 to p330, with the placeholder splitting the launcher's name,
  // p347, and the launcher's .cjs twin, p348 and p349 (class shared, gap null, no refusal before round 6 and at the round-6 head,
  // where the row expects the local road's verdict, class none or the true reason; p347 refused before round 6 as naming no file and
  // class none at the round-6 head, where the row expects the no-closed-form SENTENCE), and a playwright package's or the launcher's
  // name bound to a name, returned from a function, held in an object literal that is a call's or new's argument, or standing in a
  // conditional's branch or a logical's operand as a callee's argument, handed to a callee the walker knows no loader for, p331 to
  // p333, p335 to p340, p343, p344, p350 to p352, p354 to p362, p364 and p369 (class none with no refusal before round 6 and at the round-6
  // head, where the row expects THE SAFETY NET's sentence), and a specifier the bundler's mapping names, p370 to p376 (a .cjs or .mjs
  // spelling, or a .js spelling with a .js beside the launcher, bound as the launcher, class shared, gap null, no refusal, a .js
  // spelling of a .tsx and a .jsx spelling of the launcher refused as naming no file, a .jsx module skipped as no script and a
  // declaration file read, before round 6 and at the round-6 head, where the row expects the twin's or the helper's content read,
  // the launcher bound or the no-file sentence), unless R6_HELD names it with
  // holds set (the renamed-parameter control, the two name-position controls, the argument-position control, the five read-position
  // controls, the literal control and the path-call control of the literal chain, and, of the swallow read, the .finally and bare
  // .then controls, the Promise.all control, the wrapper-in-try residual and the never-awaited try boundary, and, from the closing
  // pass after the round's verification, the catch-variable pin of the specifier fold, p308, green under that census by its by-name
  // read's other road and red under the round-6 module before the pass (the no-initializer class's control since round 7), the two
  // swallow spellings stated as residuals, p309 and
  // p310, and the chain nested inside a path call's argument stated as a boundary, p311; and, from the review's round 7, the real
  // launcher through a path call, p326, the literal handed to a foreign callee, p334, the bound-name clause's boundaries, p341, p342
  // and p353, its controls, p363, p366, p367 and p368, the climb's boundary, p365, and the swallow rule's two further witnesses,
  // Promise.allSettled over a bound array and over its spread, p345 and p346); a round-6 builder who adds a row moves R6_LAST to
  // it and, when the row stays green under that census, adds it to
  // R6_HELD with holds set (the round-5 population above is closed)
  const NOT_RERUN6 = " (the discrimination was established by running the census before round 6, the module at the round-5 head, over the plants, recorded in the PR's notes, and is not re-run here, since that census is not in the tree at test time: this assertion holds the table's statement, not the fact)";
  assert.equal(R6_FIRST, R5_LAST + 1, "the round-5 range (to p" + R5_LAST + ") and the round-6 range (from p" + R6_FIRST + ") abut: a builder who moves R5_LAST moves R6_FIRST with it, and a row added to one range is not slid into the other, whose statement is about a different census" + NOT_RERUN6);
  const r6 = PLANT_TABLE.filter(inRound6);
  assert.deepEqual(PLANT_TABLE.filter((p) => num(p) > R6_LAST).map(idOf), [], "every row past p" + R5_LAST + " is a round-6 row and takes a verdict below: a row numbered past R6_LAST (p" + R6_LAST + ") is outside the statement, so a builder who adds a row moves R6_LAST to it" + NOT_RERUN6);
  assert.deepEqual(r6.map(idOf).sort(byNum), Array.from({ length: R6_LAST - R6_FIRST + 1 }, (_, i) => "p" + (R6_FIRST + i)), "the round-6 rows are p" + R6_FIRST + " to p" + R6_LAST + ", " + (R6_LAST - R6_FIRST + 1) + " of them, one row each, so every one takes a verdict below: red under the census before round 6 (no holds field) or green with holds set" + NOT_RERUN6);
  const held6 = r6.filter((p) => p.holds !== undefined);
  assert.deepEqual(held6.map(idOf).sort(byNum), R6_HELD, "the round-6 rows that stay green under the census before round 6 are exactly " + JSON.stringify(R6_HELD) + ", each with holds set: a row marked as holding something else that reds under that census, or a green row left unmarked, is red here" + NOT_RERUN6);
  for (const p of held6) assert.ok(FORMS.some((f) => (p.holds as string).startsWith(f + ": ") && (p.holds as string).length > f.length + 2), idOf(p) + ": holds begins with one of the five forms, a colon and the row's detail: " + JSON.stringify(p.holds));
  const carried6 = r6.filter((p) => p.carried !== undefined);
  assert.deepEqual(carried6.map(idOf).sort(byNum), R6_CARRIED, "the round-6 rows that red under the census before round 6 on a property other than their section's are exactly " + JSON.stringify(R6_CARRIED) + ", each with carried set" + NOT_RERUN6);
  for (const p of carried6) {
    assert.equal(p.holds, undefined, idOf(p) + ": a carried row reds under the census before round 6, so it holds no reason of its own");
    const carriers = [...new Set([...(p.carried as string).slice("a shape another plant carries: ".length).matchAll(/\bp\d+\b/g)].map((m) => m[0]))].filter((x) => x !== idOf(p));
    assert.ok(carriers.length > 0 && carriers.every((c) => rows.has(c)), idOf(p) + ": carried names a table row that carries the property" + NOT_RERUN6);
  }
  assert.equal(r6.length - held6.length, R6_LAST - R6_FIRST + 1 - R6_HELD.length, (R6_LAST - R6_FIRST + 1 - R6_HELD.length) + " round-6 rows red under the census before round 6 (" + (R6_LAST - R6_FIRST + 1) + " rows, " + R6_HELD.length + " with holds)" + NOT_RERUN6);
  assert.deepEqual(PLANT_TABLE.filter((p) => (p.holds !== undefined || p.carried !== undefined) && !inRound3(p) && !inRound4(p) && !inRound5(p) && !inRound6(p)).map(idOf), [], "holds and carried are fields of the round-3 rows (p38 to p88), the round-4 rows (p89 to p" + R4_LAST + "), the round-5 rows (p" + R5_FIRST + " to p" + R5_LAST + ") and the round-6 rows (p" + R6_FIRST + " to p" + R6_LAST + "), the populations the statements are about; an earlier row carries neither");
});

test("the lexical read's scope set is the compiler's grammar, not the shapes a round found (extra5-1, the review's round 7): isLexicalScope and holdsVarScope, the one definition classify's isScope and holdsVarsOf delegate to, agree node by node with the compiler's binder (getContainerFlags: HasLocals for a scope, IsContainer with HasLocals for a var holder, a namespace's locals attributed to its ModuleBlock) over a synthetic source carrying every value-scope kind once; the source covers every kind canHaveLocals admits outside the JSDoc range and a stated type-level list, so a kind a compiler upgrade adds is red here until the walker and the source take it; the internals it reads are asserted present, so an upgrade that drops one fails loudly instead of skipping; before round 7 the set lacked the case block, the namespace body and the static block, which this reds naming them", async () => {
  const census = await load();
  const ts = census.loadTypescript();
  // the binder's own predicate: getContainerFlags and canHaveLocals are exported by the compiler at run time and absent from its
  // typings, so they are read through this any-typed load and asserted functions (typescript 5.9.3 when this was written)
  assert.equal(typeof ts.getContainerFlags, "function", "the compiler exports getContainerFlags at run time (the binder's container kinds, the predicate this test pins the walker's scope set against): an upgrade that drops it fails here by name, never a skip");
  assert.equal(typeof ts.canHaveLocals, "function", "the compiler exports canHaveLocals at run time (the kinds that can carry locals, the coverage rule below): an upgrade that drops it fails here by name, never a skip");
  const HAS_LOCALS = ts.ContainerFlags && ts.ContainerFlags.HasLocals, IS_CONTAINER = ts.ContainerFlags && ts.ContainerFlags.IsContainer;
  assert.ok(typeof HAS_LOCALS === "number" && HAS_LOCALS > 0 && typeof IS_CONTAINER === "number" && IS_CONTAINER > 0, "the compiler exports ContainerFlags.HasLocals and ContainerFlags.IsContainer at run time: " + JSON.stringify([HAS_LOCALS, IS_CONTAINER]));
  const kindName = (k: number): string => { const names = Object.keys(ts.SyntaxKind).filter((n) => ts.SyntaxKind[n] === k); return names.find((n) => !/^(First|Last)/.test(n)) || names[0]; };
  // one snippet per kind, value scopes and type-level ones; no snippet names a browser package or the launcher (this module is read
  // by the census too)
  const SNIPPETS = [
    "function fd(p: string) { void p; }",
    "const fe = function (p: string) { void p; };",
    "const af = (p: string) => { void p; };",
    "class K { m(p: string) { void p; } constructor(p: string) { void p; } get g() { return 1; } set g(p: number) { void p; } static { var sv = 1; void sv; } }",
    "namespace NS { const nc = 1; void nc; }",
    "{ const bc = 1; void bc; }",
    "switch (0 as number) { case 0: const cc = 1; void cc; }",
    "for (let i = 0; i < 1; i++) { void i; }",
    "for (const k in {}) { void k; }",
    "for (const v of [] as number[]) { void v; }",
    "try { void 0; } catch (e) { void e; }",
    "type TA<T> = T; type MT = { [P in \"a\"]: P }; type CT<T> = T extends infer U ? U : never; interface I { (p: string): void; new (p: string): I; ms(p: string): void; [ix: string]: unknown; } type FT = (p: string) => void; type CTor = new (p: string) => object;",
  ];
  const sf = ts.createSourceFile("scopes.ts", SNIPPETS.join("\n") + "\n", ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);
  // the canHaveLocals kinds that hold type parameters or type-position parameters only, never a value declaration a specifier can be
  // bound to: a stated list (ts.isTypeElement cannot build it, being true for a class's get and set accessors, value scopes)
  const TYPE_LEVEL = new Set(["MethodSignature", "CallSignature", "ConstructSignature", "IndexSignature", "FunctionType", "ConstructorType", "ConditionalType", "MappedType", "TypeAliasDeclaration"].map((n) => ts.SyntaxKind[n]));
  const typeLevel = (n: any) => TYPE_LEVEL.has(n.kind);
  const isJSDocKind = (k: number) => k >= ts.SyntaxKind.FirstJSDocNode && k <= ts.SyntaxKind.LastJSDocNode;
  const flagsOf = (n: any): number => ts.getContainerFlags(n);
  // the binder's verdict per node: a namespace's locals live on its ModuleDeclaration, attributed to the ModuleBlock that is its one
  // body (the node the walker reaches going up from a use inside it)
  const compilerScope = (n: any) => ts.isModuleBlock(n) ? (flagsOf(n.parent) & HAS_LOCALS) !== 0 : ts.isModuleDeclaration(n) ? false : (flagsOf(n) & HAS_LOCALS) !== 0 && !typeLevel(n);
  const holder = (f: number) => (f & IS_CONTAINER) !== 0 && (f & HAS_LOCALS) !== 0;
  const compilerVarHolder = (n: any) => ts.isModuleBlock(n) ? holder(flagsOf(n.parent)) : ts.isModuleDeclaration(n) ? false : holder(flagsOf(n)) && !typeLevel(n);
  // the walker's allowed extras: a function's or static block's body Block (the binder holds its locals on the parent and gives the
  // Block no flags) and a type-level function-like (ts.isFunctionLike covers signatures and function types; no value declaration
  // stands in one)
  const allowedExtra = (n: any) => (ts.isBlock(n) && n.parent && (ts.isFunctionLike(n.parent) || ts.isClassStaticBlockDeclaration(n.parent))) || typeLevel(n);
  const nodes: any[] = [];
  const walk = (n: any) => { nodes.push(n); ts.forEachChild(n, walk); };
  walk(sf);
  const dropped = new Set<string>(), extra = new Set<string>(), varDropped = new Set<string>(), varExtra = new Set<string>();
  for (const n of nodes) {
    const C = compilerScope(n), Wk = census.isLexicalScope(ts, n);
    if (C && !Wk) dropped.add(kindName(n.kind));
    if (Wk && !C && !allowedExtra(n)) extra.add(kindName(n.kind));
    const CV = compilerVarHolder(n), WV = census.holdsVarScope(ts, n);
    if (CV && !WV) varDropped.add(kindName(n.kind));
    if (WV && !CV && !typeLevel(n)) varExtra.add(kindName(n.kind));
  }
  assert.deepEqual([...dropped], [], "every node the binder gives locals to for a value declaration is a scope of the walker's lexical read (isLexicalScope, classify's isScope): a kind named here is one the walker skips, so a const declared in it that shares an outer const's name reads as the outer const, the silent-leg class the review's round 6 found for the case block, the namespace body and the static block (p312 to p315 carry it). Holds a PROPERTY, the walker's set against the compiler's");
  assert.deepEqual([...extra], [], "every scope of the walker's lexical read is one the binder gives locals to, a function's or static block's body Block and a type-level function-like excepted: a kind named here is read as a scope the language does not have. Holds a PROPERTY");
  assert.deepEqual([...varDropped], [], "every function-scoped container of the binder (IsContainer with HasLocals, where a var is held) holds vars for the walker (holdsVarScope, classify's holdsVarsOf, which also stops the inner walk): a kind named here lets a var spelled inside it hoist past it, so it shadows, or is read as, an outer name (p316 and p317 carry the stop). Holds a PROPERTY");
  assert.deepEqual([...varExtra], [], "every var holder of the walker is a function-scoped container of the binder: a kind named here stops a var's hoisting where the language does not. Holds a PROPERTY");
  // coverage by rule over SyntaxKind: every kind canHaveLocals admits, less the JSDoc range and the stated type-level list, is carried
  // by the source, so the comparison above cannot pass by leaving a kind out of the snippets
  const allKinds = [...new Set(Object.values(ts.SyntaxKind).filter((v) => typeof v === "number") as number[])];
  const canLocals = allKinds.filter((k) => ts.canHaveLocals({ kind: k }));
  const seen = new Set(nodes.filter((n) => (flagsOf(n) & HAS_LOCALS) !== 0).map((n) => n.kind));
  const valueKinds = canLocals.filter((k) => !isJSDocKind(k) && !TYPE_LEVEL.has(k));
  assert.equal(valueKinds.length, 16, "the coverage rule derives the value-scope kinds from canHaveLocals, never from a list here, and there are 16 at typescript 5.9.3, the version this count was derived at: an empty derivation cannot pass, and a compiler that admits more kinds or fewer reds here, the deliberate re-derivation point (holds a PROPERTY of the compiler in use); got " + JSON.stringify(valueKinds.map(kindName)));
  assert.deepEqual(valueKinds.filter((k) => !seen.has(k)).map(kindName), [], "the synthetic source carries every kind canHaveLocals admits outside the JSDoc range and the stated type-level list: a kind named here (one a compiler upgrade added) is compared by nobody until a snippet carries it and the walker's set is judged against it. Holds a PROPERTY");
  assert.deepEqual([...TYPE_LEVEL].filter((k) => !canLocals.includes(k)).map(kindName), [], "every kind of the stated type-level list is one canHaveLocals admits, so the list names only kinds the rule would otherwise demand: a kind named here is stale in the list. Holds a PROPERTY");
  for (const k of ["CaseBlock", "ModuleDeclaration", "ClassStaticBlockDeclaration"]) assert.ok(seen.has(ts.SyntaxKind[k]), "the synthetic source carries a " + k + " the binder gives locals to, the kinds the review's round 6 found missing from the walker's set (a guard on the comparison's input, beside the coverage rule)");
  // the delegation: the walker reads these two exports and no second definition. A text pin on WHERE the predicates are bound
  // (classify's isScope and holdsVarsOf are each an arrow over the export), read through the compiler's tree of the module; the
  // BEHAVIOUR is executed by the plants p312 to p317 (the readers and the stop), which the comparison above cannot see
  const msf = ts.createSourceFile(MODULE, read(MODULE), ts.ScriptTarget.Latest, true, ts.ScriptKind.JS);
  const bound: Record<string, string[]> = { isScope: [], holdsVarsOf: [] };
  const visit = (n: any) => { if (ts.isVariableDeclaration(n) && ts.isIdentifier(n.name) && n.name.text in bound && n.initializer) bound[n.name.text].push(n.initializer.getText(msf)); ts.forEachChild(n, visit); };
  visit(msf);
  assert.deepEqual(bound, { isScope: ["(n) => isLexicalScope(ts, n)"], holdsVarsOf: ["(n) => holdsVarScope(ts, n)"] }, "classify binds isScope and holdsVarsOf once each, as arrows over the exported isLexicalScope and holdsVarScope, so the set this test pins is the walker's own (a pin on where the predicate is bound, not on what it reads: the plants p312 to p317 execute the readers and the stop)");
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

test("THE SAFETY NET's recipe cannot go stale unnoticed (extra7-1, round 6): a comment-stripped identifier census over the net block, the compiler's own tree of scripts/browser-legs-census.mjs (an identifier node carries no comment), finds the block's free names to be exactly the records and readers the census header's recipe names beside the utilities it states, and both homes of the recipe, the header's parenthetical and the block's own comment, name every one of them; before round 6 the block read PW_PACKAGES through an inline predicate that neither home accounted for, and named driverText and CALL_APPLY_BIND that neither listed", async () => {
  // The recipe is the header's sentence for checking THE SAFETY NET's accounting by hand: grep the net block for the records it reads
  // and the readers it calls, and find no other record or name-set. A reader who followed it before round 6 found three names the
  // sentence did not list (pwText, a substring predicate reading PW_PACKAGES directly; driverText; CALL_APPLY_BIND), and a later
  // drift of the inline predicate narrower than the walker's own pre-filter would have passed both homes' prose unchanged. The
  // pre-filter is one named reader now (namesPwPackage, the one driverLoads and foldSpecifier's placeholder road read), and this
  // test derives the block's free identifiers from the compiler's tree rather than from a grep, so a comment naming a reader does
  // not satisfy it and a reader added to the code without a home in the prose reds it. Holds a PROPERTY (the equality of the
  // derived set and the stated list) and, for each name, the SENTENCE in both homes (a reword that drops or renames one moves the
  // pin too).
  const mod = await load();
  const ts = mod.loadTypescript();
  const source = read(MODULE);
  const sf = ts.createSourceFile(MODULE, source, ts.ScriptTarget.Latest, true, ts.ScriptKind.JS);
  // the net block: the bare block (a block whose parent is a block, classify's body) whose statements declare netWalk; found once
  const blocks: any[] = [];
  const find = (n: any): void => { if (ts.isBlock(n) && n.parent && ts.isBlock(n.parent) && n.statements.some((st: any) => ts.isVariableStatement(st) && st.declarationList.declarations.some((d: any) => ts.isIdentifier(d.name) && d.name.text === "netWalk"))) blocks.push(n); ts.forEachChild(n, find); };
  find(sf);
  assert.equal(blocks.length, 1, "the net block is found once in scripts/browser-legs-census.mjs: a bare block inside classify's body declaring netWalk (a rewrite of the net re-anchors this test rather than passing it over no block)");
  const block = blocks[0];
  // free identifiers: every identifier node that is not a declaration's own name, a member's name or a property assignment's name,
  // minus the names the block itself declares (a comment is no node of the tree, so a name in a comment is neither read nor declared)
  const declared = new Set<string>(), used = new Set<string>();
  const walk = (n: any): void => {
    if (ts.isIdentifier(n)) {
      const p = n.parent;
      const isDecl = (ts.isVariableDeclaration(p) && p.name === n) || (ts.isParameter(p) && p.name === n) || (ts.isFunctionDeclaration(p) && p.name === n) || (ts.isBindingElement(p) && p.name === n);
      const isMemberName = ts.isPropertyAccessExpression(p) && p.name === n;
      const isPropName = ts.isPropertyAssignment(p) && p.name === n;
      if (isDecl) declared.add(n.text); else if (!isMemberName && !isPropName) used.add(n.text);
    }
    ts.forEachChild(n, walk);
  };
  walk(block);
  const free = [...used].filter((k) => !declared.has(k)).sort();
  const RECORDS = ["resolved", "embedded", "loaders", "loaderReexport", "bindingAt"];
  const READERS = ["loaderCall", "resolveSpec", "isPwPackage", "namesPwPackage", "foldText", "memberNames", "declOfUse", "isAssignmentOp", "isCreateRequireId", "isModuleRequire", "driverText", "CALL_APPLY_BIND"];   // isAssignmentOp since round 7, THE BOUND-NAME clause's read of an assignment's right side
  const UTILITIES = ["up", "unwrap", "lineOf", "ts", "sf", "netHits", "String", "undefined"];
  assert.deepEqual(free, [...RECORDS, ...READERS, ...UTILITIES].sort(), "the net block's free identifiers, derived from the compiler's tree, are exactly the five records and twelve readers the header's recipe names plus the eight utilities it states (holds the PROPERTY: a name the block's code reads that this list lacks is a reader the recipe does not account for, PW_PACKAGES through an inline predicate before round 6; a name listed here that the block no longer reads is a stale recipe; either way both homes of the prose are rewritten with this list)");
  assert.ok(!free.includes("PW_PACKAGES"), "the block reads no name-set of its own: PW_PACKAGES is read through namesPwPackage, the one pre-filter the walker's readers share, never inline (before round 6 the block declared pwText over PW_PACKAGES directly)");
  // both homes name every record, reader and utility: the header's recipe, from its checking clause to its closing sentence, and the
  // block's own comment, the // lines directly above `const netHits`
  const header = moduleHeader();
  const from = header.indexOf("a reader checks it by grepping the net block"), to = header.indexOf("so the recipe cannot go stale unnoticed");
  assert.ok(from >= 0 && to > from, "the census header's recipe runs from the checking clause (a reader checks it by grepping the net block) to its closing sentence (so the recipe cannot go stale unnoticed); holds the sentence: a reword of either end moves this pin too");
  const recipe = header.slice(from, to);
  assert.ok(recipe.includes("finding no other record or name-set"), "the recipe's 'no other' is scoped to records and name-sets (finding no other record or name-set), so the position utilities, the compiler and the parse it also names are not a contradiction of it; holds the sentence");
  const lines = source.split("\n");
  const netAt = lines.findIndex((l) => l.trim() === "const netHits = [];");
  assert.ok(netAt > 0, "the net block's comment sits directly above the line `const netHits = [];`, found once");
  let top = netAt; while (top > 0 && lines[top - 1].trim().startsWith("//")) top--;
  const blockComment = lines.slice(top, netAt).map((l) => l.trim().replace(/^\/\/ ?/, "")).join(" ");
  for (const name of [...RECORDS, ...READERS, ...UTILITIES]) {
    const word = new RegExp("(^|[^A-Za-z0-9_])" + name + "(?![A-Za-z0-9_])");
    assert.ok(word.test(recipe), "the census header's recipe names " + name + " (holds the SENTENCE in the header, the first home: a reader following it finds every free name of the block accounted for)");
    assert.ok(word.test(blockComment), "THE SAFETY NET block's own comment names " + name + " (holds the SENTENCE in the block, the second home)");
  }
});

test("THE BOUND-NAME clause says what the arm does (extra6-1, the review's round 6, built in round 7): the census header no longer says the walker's hand-on refusals close a text's name handed to a callee the walker knows no loader for, states the clause's accounting, the return arm's reach (which functions it follows, and the road past it) and the climb's reach, and names exactly the plant rows the clause refuses and the held rows that name it, its boundaries and its controls", () => {
  // The rows are the executed proof of what the arm does (each red under the census before round 6, the held ones green); this pin
  // holds the PROSE to them. It holds the SENTENCE for the retired clause, the accounting phrases and the two reaches (a reword
  // moves the pin too), and a PROPERTY for the witness ids: the ids the clause names equal the ids derived from the table, the rows
  // whose refusal's first mention is the clause's own sentence and the held rows whose holds names the clause (its boundaries and
  // its controls), so a
  // witness dropped from the prose, or a row named that the arm neither refuses nor holds, reds here.
  const header = moduleHeader();
  assert.ok(!header.includes("the hand-on refusals' when it is not"), "the retired clause is absent: no hand-on refusal of the walker reads a name bound to a text, so the header may not say one closes a load through such a name when the callee is no loader (the round-6 review's extra6-1; the arm that does is THE SAFETY NET's bound-name road). Holds the SENTENCE");
  const from = header.indexOf("THE BOUND-NAME clause ("), to = header.indexOf("A let or var written after its declaration is no closed form", from);
  assert.ok(from >= 0 && to > from, "the clause runs from 'THE BOUND-NAME clause (' to 'A let or var written after its declaration is no closed form' (holds the SENTENCE at both ends: a reword of either moves this pin)");
  const clause = header.slice(from, to);
  for (const phrase of ["as a declaration's initializer", "as the right side of any assignment", "ACCOUNTED only when every value reference", "inside the specifier argument of a loader call in `resolved`", "(embedded)", "REFUSED otherwise, naming the bound name"]) assert.ok(clause.includes(phrase), "the clause states the accounting " + JSON.stringify(phrase) + " (holds the SENTENCE; the rows named below are the executed proof)");
  // the return arm's reach, where the boundary list once said a returned text is not read: which functions it follows, and the road past it
  for (const phrase of ["as a return statement's expression or an arrow's expression body, is refused where it stands, in any function of the module", "it follows no call, so the text is refused whoever calls the function", "a text that leaves a function by any other road, a generator's yield, is past its reach"]) assert.ok(clause.includes(phrase), "the clause states the return arm's reach " + JSON.stringify(phrase) + " (holds the SENTENCE: the arm reads every function of the module and follows no caller, and a generator's yield is the road past it, held by its row)");
  // the climb's reach, in the header's sentence on the positions the net reads (one sentence, outside the clause, since the climb serves both)
  for (const phrase of ["the climb from a text to the position its value stands in", "a conditional's two branches and either operand of ??, || and &&", "and no other expression, so a text read through a member of its own"]) assert.ok(header.includes(phrase), "the census header states the climb's reach " + JSON.stringify(phrase) + " (holds the SENTENCE; p344, p350 to p352 and p365 execute it)");
  const idOf = (p: Plant): string => (/^p\d+/.exec(p.file) || [""])[0];
  const byNum = (a: string, b: string): number => Number(a.slice(1)) - Number(b.slice(1));
  const expand = (text: string): string[] => [...text.matchAll(/\bp(\d+)(?: to p(\d+))?\b/g)].flatMap((m) => m[2] === undefined ? ["p" + m[1]] : Array.from({ length: Number(m[2]) - Number(m[1]) + 1 }, (_, i) => "p" + (Number(m[1]) + i)));
  const named = [...new Set(expand(clause))].sort(byNum);
  const SENTENCE = /^(a playwright package's name|the launcher module's name|a relative path into node_modules naming a playwright package) (bound to|returned from a function)/;
  const firstMention = (r: string): string => (r.includes(NET_HEAD) ? r.split(NET_HEAD)[1] : "");
  const refusedRows = PLANT_TABLE.filter((p) => typeof p.refused === "string" && SENTENCE.test(firstMention(p.refused))).map(idOf);
  const heldRows = PLANT_TABLE.filter((p) => typeof p.holds === "string" && p.holds.includes("the bound-name clause")).map(idOf);   // its boundaries and its controls, each holds naming the clause
  assert.ok(refusedRows.length > 0 && heldRows.length > 0, "the clause has rows to name, refused and held: an empty derivation is no evidence (derived: " + JSON.stringify({ refusedRows, heldRows }) + ")");
  assert.deepEqual(named, [...refusedRows, ...heldRows].sort(byNum), "the clause names exactly the rows the bound-name clause refuses (its sentence the refusal's first mention) and the held rows whose holds names the clause, its boundaries and its controls: a witness dropped from the prose, or a row named that the clause neither refuses nor holds, reds here (holds a PROPERTY, the prose's ids against the table's)");
});

test("the script's --list-legs is the census's legs and its --check is green over the tree; the CLI's --tsv carries one line per module with the leg flag, the gap, the engines and the class", async () => {
  const { census, rosterGap, engineNames, classOf } = await load();
  const c = census(REPO);
  const list = spawnSync("bash", [SCRIPT, "--list-legs"], { cwd: EXT, encoding: "utf8" });
  assert.equal(list.status, 0, "the script's --list-legs exits 0 over the tree; stderr:\n" + list.stderr);
  assert.deepEqual(list.stdout.split("\n").filter(Boolean).sort(), c.legs, "the script lists the census's legs (it runs the same module; the script prints them in the census's walk order over LEG_DIRS and census() returns them sorted, so the two are compared sorted)");
  const check = spawnSync("bash", [SCRIPT, "--check"], { cwd: EXT, encoding: "utf8" });
  assert.equal(check.status, 0, "the script's --check is green over the tree, exit 0; stderr:\n" + check.stderr);
  assert.match(check.stdout, /^ci-browser-legs: the roster and the tree agree: \d+ rostered, \d+ browser legs in the census/m, "--check prints the agreement line with the rostered and census counts; stdout:\n" + check.stdout);
  assert.equal(check.stderr, "", "nothing on stderr when the files and the tree agree");
  const tsv = spawnSync(process.execPath, [MODULE, "--tsv"], { cwd: EXT, encoding: "utf8" });
  assert.equal(tsv.status, 0, "the CLI's --tsv exits 0 over the tree; stderr:\n" + tsv.stderr);
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
  assert.match(ok.stdout, /the roster and the tree agree: 1 rostered, 5 browser legs in the census/, "the aliased caller rostered beside four exclusions: the agreement line names 1 rostered and 5 browser legs; stdout:\n" + ok.stdout);
  const refused = (r: ReturnType<typeof run>, ...needles: string[]) => {
    assert.equal(r.status, 1, "exit 1; stderr: " + r.stderr);
    for (const n of needles) assert.ok(r.stderr.includes(n), "stderr names " + JSON.stringify(n) + ":\n" + r.stderr);
    assert.ok(r.stderr.includes("no leg ran"), "a refused run says no leg ran; stderr:\n" + r.stderr);
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
  assert.equal(r.status, 1, "a roster line whose source launches on its own (p09b) is red, exit 1; stderr:\n" + r.stderr);
  // the gate is read first (the leg never imports the launcher); the engine verdict is what the exclusions reason must carry
  assert.ok(r.stderr.includes(ROSTER + " line 2: '" + P09B + "' does not launch through the one shared launcher"), "the roster gate names line 2 and the shared-launcher property; stderr:\n" + r.stderr);
  const excluded = run(P01 + "\n", P09B + "\tlaunches Firefox and WebKit; the gating job installs Chromium only\n");
  assert.equal(excluded.status, 0, "the same leg excluded with the two-engine form is green, exit 0; stderr:\n" + excluded.stderr);
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
  assert.match(absent.stdout, /the roster and the tree agree: 1 rostered, 3 browser legs in the census, 1 pending lines naming absent sources/, "the agreement line counts the pending line naming an absent source; stdout:\n" + absent.stdout);
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
  assert.equal(neither.status, 1, "two legs in neither file are red, exit 1; stderr:\n" + neither.stderr);
  assert.ok(neither.stderr.includes("browser leg '" + P04 + "' is in neither " + ROSTER + " nor " + EXCLUDED + ": pass the roster gate (the source loads playwright itself (playwright)"), "the gate's remedy for the both-class leg:\n" + neither.stderr);
  assert.ok(neither.stderr.includes("browser leg '" + P19 + "' is in neither " + ROSTER + " nor " + EXCLUDED + ": add it to " + EXCLUDED + " with a tab and the engine form its header admits, \"launches WebKit; the gating job installs Chromium only\""), "the engine form for the WebKit leg:\n" + neither.stderr);
  assert.ok(!neither.stderr.includes("or to the exclusions with a tab and a reason"), "no bare add-or-exclude:\n" + neither.stderr);
  for (const b of [P04, P19]) assert.ok(neither.stderr.includes(": " + neitherRemedy(mod, cs.byBundle.get(b), b)), "neitherRemedy, this file's copy of the script's rule, prints the script's sentence for " + b + ":\n" + neither.stderr);
});

test("a form the census cannot classify stops the script with the file and line, judging nothing; without the compiler the census exits 1 naming CI's Shell job and the script stops the same way", (t) => {
  const { run } = syntheticRoot(t, ["p01-alias.test.ts", "p27-parse-error.test.ts"]);
  const P01 = B("p01-alias.test.ts");
  const r = run(P01 + "\n", "");
  assert.equal(r.status, 1, "a parse-error plant stops the script, exit 1; stderr:\n" + r.stderr);
  assert.ok(r.stderr.includes("browser-legs-census: REFUSED ui/webview/p27-parse-error.test.ts:4: the parser reports a diagnostic"), "the refusal names the file, the line and the parser diagnostic; stderr:\n" + r.stderr);
  assert.ok(r.stderr.includes("the census refused a form it cannot classify (above, with file and line)") && r.stderr.includes("nothing else was judged and no leg ran"), "the script says the census refused a form and that nothing else was judged and no leg ran; stderr:\n" + r.stderr);
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
  assert.ok(cli.stderr.includes("the typescript compiler is not installed under vscode-extension/node_modules") && cli.stderr.includes("npm ci") && cli.stderr.includes("Shell job") && cli.stderr.includes("tools/ci-browser-legs.test.mjs"), "without the compiler the CLI names the missing typescript, npm ci, the Shell job and tools/ci-browser-legs.test.mjs; stderr:\n" + cli.stderr);
  fs.writeFileSync(path.join(bare, "vscode-extension", ROSTER), B("p01-alias.test.ts") + "\n");
  fs.writeFileSync(path.join(bare, "vscode-extension", EXCLUDED), "");
  const sh = spawnSync("bash", [path.join(bare, "vscode-extension", "scripts", "ci-browser-legs.sh"), "--check"], { cwd: path.join(bare, "vscode-extension"), encoding: "utf8" });
  assert.equal(sh.status, 1, "without the compiler the script exits 1; stderr:\n" + sh.stderr);
  assert.ok(sh.stderr.includes("the typescript compiler is not installed") && sh.stderr.includes("the census did not run (exit 1, above), so nothing was judged and no leg ran"), "the script says the compiler is missing and the census did not run, so nothing was judged and no leg ran; stderr:\n" + sh.stderr);
  assert.equal(sh.stdout, "", "no agreement line and no legs listed");
});

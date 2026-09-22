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
// refuses: each is classified or refused as recorded here, none is silent. Population figures are derived from the run and
// printed as diagnostics, never asserted as constants. Synthetic: the fixtures' invented modules and a stub launcher.
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
 *  answers are named beside it. */
type Plant = {
  dir: string; file: string; leg: boolean; cls: string; gap: string | null; engines?: string[]; playwright?: string[];
  launches?: string[]; skipTodo?: string[]; swallow?: number[]; refused?: string; strictRefused?: boolean; launcherImported?: boolean;
};
const W = "ui/webview";
/** The shadow refusal's WHOLE sentence after "<file>:<line>: ", as the census emits it (read from a run of the CLI over the plants,
 *  not guessed): the p17 and p47 rows hold the whole sentence, not the prefix "a local declaration shadows an import binding",
 *  because the sentence (why the shadow is refused, and the remedy) is what the round-3 item landed and the prefix predates it;
 *  a reword of the why or the remedy in the module is red at those rows. */
const SHADOW_REFUSAL = "a local declaration shadows an import binding of the launcher or of playwright (a use inside the local's scope reaches the local, not the import; the shadow is refused so an import it leaves uncalled, or whose launches it hides, is not read as an ordinary non-leg without notice: rename the local)";
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
  { dir: W, file: "p41-array-destructure-playwright.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: [], launches: [], refused: "p41-array-destructure-playwright.test.ts:3: an array destructuring of a playwright expression the walker does not follow: [eng]" },
  { dir: W, file: "p42-array-destructure-loaded.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: [], launches: [], refused: "p42-array-destructure-loaded.test.ts:2: an array destructuring of a loaded module the walker does not follow: [x]" },
  { dir: W, file: "p43-object-assign-destructure.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: [], launches: [], refused: "p43-object-assign-destructure.test.ts:4: an object destructuring by assignment of a playwright expression the walker does not follow: { chromium }" },
  // fresh-1: a name is read at its use site by lexical scope, so an inner scope's same-named binding is not the tracked one
  { dir: W, file: "p44-pattern-param-reuses-name.test.ts", leg: true, cls: "both", gap: "loads playwright itself", engines: ["firefox"], launches: [".launch("] }, // a parameter's array pattern reuses pw inside an arrow (the shape PR 853's module holds): the inner pw is the parameter, the module's pw is playwright, and nothing is refused
  { dir: W, file: "p45-catch-and-for-shadow.test.ts", leg: true, cls: "shared", gap: null },                                       // a catch variable and a for-of const named inBrowser, the import called after them: the call reaches the import
  { dir: W, file: "p46-inner-destructured-shadow.test.ts", leg: false, cls: "none", gap: "never calls its inBrowser through that import", launcherImported: true }, // an inner block's destructured inBrowser is what the call reaches, so the import stands uncalled; a destructured shadow has no identifier-named declaration, so no shadow refusal
  { dir: W, file: "p47-shadow-delegates.test.ts", leg: true, cls: "shared", gap: null, refused: "p47-shadow-delegates.test.ts:3: " + SHADOW_REFUSAL }, // fresh-1's twin: the local shadow delegates to a module-level helper that calls the import, so the module IS a shared leg (the call resolves to the import by scope) and the identifier-named shadow is still refused; the row holds the whole refusal sentence (SHADOW_REFUSAL) because the sentence is what round 3 landed and the prefix predates it
  // the round-2 review's roads, section A of its rulings: a loader result used where it stands, in any position
  { dir: W, file: "p48-require-pw-chain.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: ["chromium"], playwright: ["playwright"], launches: [".launch("] }, // correctness-1, extra7-1: require("playwright").chromium.launch(), never bound
  { dir: W, file: "p49-require-launcher-chain.test.ts", leg: true, cls: "shared", gap: null, launcherImported: true },              // correctness-1: require(the launcher).inBrowser(t, ...), the load followed as the object of the member the call arm read
  { dir: W, file: "p50-class-field-loader.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: [], launches: [], playwright: ["playwright"] }, // correctness-1: a class field holding the loader result; the package is recorded where it is resolved, the launch through the field is not derived
  { dir: W, file: "p51-object-property-loader.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: [], launches: [], playwright: ["playwright"] }, // correctness-1: an object property holding it
  { dir: W, file: "p52-wrapper-return.test.ts", leg: false, cls: "none", gap: null, launcherImported: false, refused: "p52-wrapper-return.test.ts:2: THE INVARIANT: the census resolved the shared launcher (./real-viewer-leg) here and its record carries nothing of the load" }, // correctness-1's wrapper return: the load stands in a position the walker does not read, refused by the invariant (before it: class none, no refusal, a false gap sentence)
  { dir: W, file: "p53-createrequire-direct-pw.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: ["chromium"], playwright: ["playwright"], launches: [".launch("] }, // extra6-1: createRequire(__filename)("playwright"), the loader applied directly
  { dir: W, file: "p54-createrequire-direct-launcher.test.ts", leg: true, cls: "shared", gap: null, launcherImported: true },       // extra6-1: the same for the launcher, destructured
  { dir: W, file: "p55-requirecjs-unbound.test.ts", leg: true, cls: "own", gap: "never calls its inBrowser through that import", engines: ["chromium"], playwright: ["playwright"], launches: [".launch("], launcherImported: true }, // extra7-1: requireCjs("playwright").chromium.launch() on the launcher's own loader, unbound
  { dir: W, file: "p56-await-import-unbound.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: ["chromium"], playwright: ["playwright"], launches: [".launch("] }, // extra7-1: (await import("playwright")).chromium.launch()
  { dir: W, file: "p57-import-then.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: [], launches: [], playwright: ["playwright"] }, // extra7-1: import("playwright").then(pw => ...): the package is recorded, the launch on the callback's parameter is not derived
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
  { dir: W, file: "p68-driver-env-piece.test.ts", leg: false, cls: "none", gap: null, launcherImported: false },                   // extra7-5's unfoldable piece: the package name arrives from the environment, the fold leaves a placeholder that spells nothing
  { dir: W, file: "p69-other-driver-package.test.ts", leg: false, cls: "none", gap: null, launcherImported: false },               // extra6-4: another driver package (puppeteer)
  { dir: W, file: "p70-playwright-chromium-package.test.ts", leg: false, cls: "none", gap: null, launcherImported: false },        // extra6-4: a package whose name contains a tracked spelling (playwright-chromium) is not a playwright package to the census
  { dir: W, file: "p71-spawn-binary.test.ts", leg: false, cls: "none", gap: null, launcherImported: false },                       // extra6-4: a browser binary spawned by name
  // extra7-4: the call arm and the value-use arm read one record of the identifier the call resolved through
  { dir: W, file: "p72-namespace-member-call.test.ts", leg: true, cls: "shared", gap: null, launcherImported: true },               // leg.inBrowser.call(null, t, ...): a counted shared call, never also a value use
  { dir: W, file: "p73-namespace-member-bind.test.ts", leg: false, cls: "none", gap: "never calls its inBrowser through that import", launcherImported: true, refused: "p73-namespace-member-bind.test.ts:3: the launcher's module binding handed on as a value (read for inBrowser without a call (.bind makes no call))" }, // leg.inBrowser.bind(null): .bind makes no call, so the bound reference is a value use
  // THE INVARIANT's boundary: text that names playwright or the launcher without a resolution (a title, an array literal, a regex, a message string) trips nothing
  { dir: W, file: "p74-text-names-playwright.test.ts", leg: false, cls: "none", gap: null, launcherImported: false },
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
  { dir: W, file: "p87-hoisted-var.test.ts", leg: true, cls: "own", gap: "never imports the shared launcher", engines: ["firefox"], playwright: ["playwright"], launches: [".launch("] }, // { var pw = require("playwright"); } then pw.firefox.launch() outside the block: the var is the module's, so the engine and the launch are read (before: engines [], launches [])
  { dir: W, file: "p88-bound-promise-await-later.test.ts", leg: false, cls: "none", gap: "never calls its inBrowser through that import", launcherImported: true, refused: "p88-bound-promise-await-later.test.ts:3: the launcher's module binding handed on as a value (awaited into a name the walker does not bind" }, // const p = import(the launcher); const m = await p; m.inBrowser(...): refused, the position named (before: the same refusal listing four forms the line does not hold)
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

test("every grandfather row's source existed at the commit the exclusions header binds the reason to: the header holds one bound line; the commit is fetched at depth 1 when the checkout lacks it, and a fetch or object read that fails is a red hold-off naming the reason, never a pass; a source absent at that commit is refused with the remedy; the bound line says it reads the file's age, not what the file did there", async (t) => {
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
    const r = git(["cat-file", "-e", sha + ":" + rel]);
    if (r.status === 0) continue;
    const where = EXCLUDED + " line " + e.n + " (" + e.bundle + ")";
    if (r.status === 128 && /does not exist in|exists on disk, but not in/.test(r.stderr)) assert.fail(where + ": the grandfather reason is bound to commit " + sha + " and " + rel + " is not in the tree at that commit, so the reason does not apply to this leg: run it in the step and add its bundle to " + ROSTER + " with the step's measured seconds, or, when the source reaches Firefox or WebKit or drives playwright from a string, write the engine form or the embedded-driver sentence");
    assert.fail(where + ": the grandfather check could not read " + sha + ":" + rel + " (git cat-file -e exit " + r.status + ": " + r.stderr.trim() + "); a red hold-off, not a pass");
  }
  t.diagnostic(rows.length + " grandfather rows bound to " + sha + ", every source in the tree at that commit");
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
      assert.ok(r.refusals.some((x) => x.includes(p.refused as string)), at + "refused with file and line; expected a refusal containing " + JSON.stringify(p.refused) + ", got " + JSON.stringify(r.refusals));
      assert.ok(c.refusals.some((x) => x.includes(p.refused as string)), at + "the refusal reaches the census's own list (the CLI exits 2 on it)");
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
  // contains a tracked spelling, a spawned binary), each class none with no refusal.
  const header = read(MODULE).split("\n").filter((l) => l.startsWith("//")).map((l) => l.replace(/^\/\/ ?/, "")).join(" ");
  assert.ok(header.includes("Three residuals, stated"), "the census header states three residuals (the string-typed parameter's fold, the non-loader call, and a browser reached without spelling a playwright package or the launcher); a header counting two has dropped the third, whose plants are the p68 to p71 rows above");
  for (const form of ["another driver package such as puppeteer", "a browser binary it spawns", "a driver source whose package name arrives at run time"]) assert.ok(header.includes(form), "the census header names the third residual's form " + JSON.stringify(form) + " (a text pin on the header's prose: the class that form takes is executed by the p68 to p71 rows above)");
  assert.ok(header.includes("is unread by the walker: class none, no refusal"), "the census header states the third residual's outcome, unread by the walker: class none, no refusal (the outcome the p68 to p71 rows record)");
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

// The browser-legs census, held to the tree and to the planted forms. The gating vscode-extension job runs the legs named in
// vscode-extension/ci-browser-legs.txt after its Chromium install (the step "Browser legs (node --test over
// ci-browser-legs.txt)", scripts/ci-browser-legs.sh); every other browser leg is in ci-browser-legs-excluded.txt with a reason.
// The census that decides what a browser leg IS lives in vscode-extension/scripts/browser-legs-census.mjs, which reads each
// test module's tree with the TypeScript compiler (its header states the rule), and the compiler is installed only under
// vscode-extension/node_modules, so this test, in the extension's own suite (npm test, this job), is where the completeness
// property is executed: the roster PLUS the exclusions EQUALS the census's legs, no refusal, every roster line passes the roster
// gate and reaches Chromium alone, an exclusions reason names Firefox or WebKit when and only when the source reaches it, and
// carries the embedded-driver sentence when and only when the leg is one. tools/ci-browser-legs.test.mjs, in CI's Shell job with
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
  census(root?: string, opts?: { strictComputed?: boolean }): { legs: string[]; byBundle: Map<string, Rec>; refusals: string[] };
  rosterGap(r: Rec): string | null;
  engineNames(r: Rec): string[];
  classOf(r: Rec): string;
  EMBEDDED_PHRASE: string;
  LEG_DIRS: string[];
};
const load = (): Promise<Census> => import(pathToFileURL(MODULE).href) as Promise<Census>;
const read = (p: string): string => fs.readFileSync(p, "utf8");
const sourceOf = (bundle: string): string => path.join(REPO, bundle.replace(/^out-tests\//, "").replace(/\.test\.js$/, ".test.ts"));
/** Roster lines: [{ n, bundle }], comments and blanks dropped. */
const parseRoster = (text: string) => text.split("\n").map((line, i) => ({ n: i + 1, line })).filter(({ line }) => !/^\s*(#|$)/.test(line)).map(({ n, line }) => ({ n, bundle: line }));
/** Exclusions lines: [{ n, bundle, reason }] (reason null when the line has no tab). */
const parseExcluded = (text: string) => text.split("\n").map((line, i) => ({ n: i + 1, line })).filter(({ line }) => !/^\s*(#|$)/.test(line)).map(({ n, line }) => {
  const tab = line.indexOf("\t");
  return tab < 0 ? { n, bundle: line, reason: null as string | null } : { n, bundle: line.slice(0, tab), reason: line.slice(tab + 1) as string | null };
});

test("the roster plus the exclusions equals the census's legs, with no refusal; every roster line passes the roster gate and reaches Chromium alone; an exclusions reason names Firefox or WebKit, or carries the embedded-driver sentence, when and only when the source does", async (t) => {
  const { census, rosterGap, engineNames, classOf, EMBEDDED_PHRASE } = await load();
  const c = census(REPO);
  assert.deepEqual(c.refusals, [], "the census refused a form it cannot classify (file:line above each): rewrite the form, or teach scripts/browser-legs-census.mjs to read it");
  assert.ok(c.legs.length > 100, "the tree holds browser legs (the census found " + c.legs.length + "; a count near zero means the rule stopped matching, not that the legs left)");
  const roster = parseRoster(read(path.join(EXT, ROSTER)));
  const excluded = parseExcluded(read(path.join(EXT, EXCLUDED)));
  const where = (file: string, e: { n: number; bundle: string }) => file + " line " + e.n + " (" + e.bundle + ")";
  for (const e of roster) {
    const r = c.byBundle.get(e.bundle);
    assert.ok(r && r.reaches, where(ROSTER, e) + " names no browser leg" + (r && r.launcherImported ? ": " + rosterGap(r) : " (the source reaches no browser by the census rule): remove the line"));
    assert.equal(rosterGap(r), null, where(ROSTER, e) + " does not launch through the one shared launcher (" + rosterGap(r) + "): only inBrowser reads ROMP_BROWSER_LEGS_REQUIRE, so a launch or a skip of the leg's own stands outside the switch; launch through inBrowser (ui/webview/real-viewer-leg.ts), with no launch, skip or playwright of the leg's own, before rostering it");
    assert.deepEqual(engineNames(r), [], where(ROSTER, e) + " reaches " + engineNames(r).join(" and ") + "; the gating job installs Chromium only, so under the switch that launch is red: keep the leg in " + EXCLUDED + " with that reason");
  }
  for (const e of excluded) {
    const r = c.byBundle.get(e.bundle);
    assert.ok(r && r.reaches, where(EXCLUDED, e) + " names no browser leg" + (r && r.launcherImported ? ": " + rosterGap(r) : " (the source reaches no browser by the census rule): remove the line"));
    assert.ok(e.reason !== null, where(EXCLUDED, e) + " has no tab, so it has no reason to read here: tools/ci-browser-legs.test.mjs refuses it and says how to fix it");
    const engines = engineNames(r);
    for (const eng of ["Firefox", "WebKit"]) {
      const inReason = e.reason.includes(eng), inSource = engines.includes(eng);
      assert.equal(inReason, inSource, where(EXCLUDED, e) + ": the reason " + (inReason ? "names " : "does not name ") + eng + " and the source " + (inSource ? "reaches it" : "does not reach it") + " (engines from playwright-derived expressions, comments and strings excluded); " + (inReason ? "drop the engine from the reason, or, if the source reaches it in a form the census does not read, write the read so the census sees it" : "write \"launches " + eng + "; the gating job installs Chromium only\" in the reason") + "; the reason reads: " + e.reason);
    }
    if (engines.length) assert.ok(e.reason.includes("the gating job installs Chromium only"), where(EXCLUDED, e) + ": an engine reason says why the gating job cannot run the leg");
    const isEmbedded = classOf(r) === "embedded";
    assert.equal(e.reason.includes(EMBEDDED_PHRASE), isEmbedded, where(EXCLUDED, e) + ": the reason " + (e.reason.includes(EMBEDDED_PHRASE) ? "carries" : "does not carry") + " the embedded-driver sentence and the leg " + (isEmbedded ? "is one (its only playwright is in a driver string it runs as a child process)" : "is not one (class " + classOf(r) + ")") + "; the sentence is " + JSON.stringify(EMBEDDED_PHRASE) + "; the reason reads: " + e.reason);
  }
  const listed = new Set([...roster.map((e) => e.bundle), ...excluded.map((e) => e.bundle)]);
  const neither = c.legs.filter((b) => !listed.has(b));
  assert.deepEqual(neither, [], "browser legs in neither " + ROSTER + " nor " + EXCLUDED + " (add each to the roster, or to the exclusions with a tab and a reason): " + JSON.stringify(neither));
  assert.deepEqual([...listed].sort(), c.legs, "the roster plus the exclusions is exactly the census's legs");
  // the population, derived from this run (figures for a PR body come from here, never from a constant kept elsewhere)
  const recs = c.legs.map((b) => c.byBundle.get(b) as Rec);
  const count = (f: (r: Rec) => boolean) => recs.filter(f).length;
  const classes: Record<string, number> = {};
  for (const r of recs) classes[classOf(r)] = (classes[classOf(r)] || 0) + 1;
  const engineSets: Record<string, number> = {};
  for (const r of recs) { const k = (r.engines || []).join("+") || "none"; engineSets[k] = (engineSets[k] || 0) + 1; }
  t.diagnostic("census: " + c.byBundle.size + " modules read, " + c.legs.length + " legs, " + roster.length + " rostered, " + excluded.length + " excluded");
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
  { dir: W, file: "p17-shadow.test.ts", leg: true, cls: "shared", gap: null, refused: "p17-shadow.test.ts:3: a local declaration shadows an import binding" },
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
];
const bundleOf = (p: Plant): string => "out-tests/" + p.dir + "/" + p.file.replace(/\.test\.ts$/, ".test.js");

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
});

test("the script's --list-legs is the census's legs and its --check is green over the tree; the CLI's --tsv carries one line per module with the leg flag, the gap, the engines and the class", async () => {
  const { census, rosterGap, engineNames, classOf } = await load();
  const c = census(REPO);
  const list = spawnSync("bash", [SCRIPT, "--list-legs"], { cwd: EXT, encoding: "utf8" });
  assert.equal(list.status, 0, list.stderr);
  assert.deepEqual(list.stdout.split("\n").filter(Boolean), c.legs, "the script lists the census's legs (it runs the same module)");
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
  refused(neither, "browser leg '" + P19 + "' is in neither " + ROSTER + " nor " + EXCLUDED);
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

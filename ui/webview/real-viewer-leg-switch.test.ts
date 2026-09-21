// The shared launcher's switch, executed: inBrowser in ./real-viewer-leg reads ROMP_BROWSER_LEGS_REQUIRE, and under it a leg
// that cannot launch FAILS naming the switch and the reason, where without it the leg skips naming the reason (CI's
// browser-legs step sets the switch after the job's Chromium install; the Test step, before any install, does not). The one
// test below is fork PR 860's test of this behaviour, copied with its mechanism unchanged (two lines differ: the comment's
// name for the leg it drives, and the --test-name-pattern that picks it), so the two branches carry one test of one helper;
// the leg it drives is this file's own, above it, which opens a page through inBrowser. The mechanism: a child
// `node --test --test-name-pattern=<leg> <this bundle>` with an env BUILT from four variables (never inherited: the runner's
// NODE_TEST_CONTEXT would put the child's report on this process's channel, and an ambient switch would leak into the
// "unset" arm) and PLAYWRIGHT_BROWSERS_PATH pointed at a fresh empty directory, so the real pw.chromium.launch() throws; with
// the switch the child records `# fail 1` and a line carrying the switch's name and this machine's reason, without it
// `# skipped 1` and the reason. On a box with a browser the outer leg launches and passes; the switch test passes on any box,
// since its child never sees the browser. tools/ci-browser-legs.test.mjs pins the phrase the step's script reads a lost
// browser by to the helper's source text and names this file as the test of the behaviour; a green there with a red here is
// a helper that carries the words and not the behaviour. Rostered in vscode-extension/ci-browser-legs.txt, so the step runs
// the outer leg with a browser and reads its record on every CI run. Synthetic: a one-paragraph page.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { spawnSync } from "node:child_process";
import { EXT, inBrowser, playwrightInstalled } from "./real-viewer-leg";   // the launch every browser leg of the fork shares, and its switch read

test("the launcher's own leg opens a page through the shared launch", { timeout: 60000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const page = await browser.newPage();
    await page.setContent("<!DOCTYPE html><p>a page</p>");
    assert.equal(await page.evaluate(() => document.querySelector("p")!.textContent), "a page");
  });
});

test("ROMP_BROWSER_LEGS_REQUIRE, read in the shared launch helper, turns the browser legs' skip into a failure that names the switch and the reason, and without it the skip stands naming the reason: CI's browser-legs step after the Chromium install sets it", { timeout: 120000 }, (t) => {
  // a child run of this file's leg with playwright pointed at an empty browsers directory (the pane bench's probe):
  // under the switch the leg fails naming the switch and the reason; without it the leg skips, as the Test step's run does.
  // The reason the child names is this machine's: with the module installed and its browsers hidden, no browser; with the module
  // absent, no module (the maintainer's round 6, tests-6: the regex demanded the browser reason alone, so a runner without the
  // module reported a FAILURE here where the file's contract says every browser leg skips with a stated reason); derived from
  // the same module read the helper's launch guards on (playwrightInstalled), never a two-way alternation. The assertions read
  // the property (the switch's name and the reason on the failure's line; the reason on the skip) and not the helper's
  // connective wording, which is the shared helper's to choose.
  const why = playwrightInstalled() ? "no playwright browser" : "playwright is not installed under vscode-extension";
  const esc = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  t.diagnostic("the reason a browser leg names on this machine: " + why);
  const empty = fs.mkdtempSync(path.join(EXT, "out-tests", "no-browsers-"));
  try {
    // the child's environment is built, not inherited: under `node --test` this process carries the runner's NODE_TEST_CONTEXT,
    // and a child inheriting it reports on the runner's channel instead of its stdout
    const base: Record<string, string> = {};
    for (const k of ["PATH", "HOME", "TMPDIR", "NODE_OPTIONS"]) if (process.env[k] !== undefined) base[k] = process.env[k] as string;
    const run = (env: Record<string, string>) => spawnSync(process.execPath, ["--test", "--test-name-pattern=launcher's own leg", __filename],
      { cwd: EXT, encoding: "utf8", timeout: 100000, env: { ...base, ...env, PLAYWRIGHT_BROWSERS_PATH: empty } });
    const req = run({ ROMP_BROWSER_LEGS_REQUIRE: "1" });
    assert.match(req.stdout, /^# fail 1$/m, "the leg failed under the switch\n" + req.stdout.slice(-1500));
    assert.match(req.stdout, new RegExp("ROMP_BROWSER_LEGS_REQUIRE[^\\n]*" + esc(why)), "the switch: a failure naming it and the reason (" + why + ") on one line\n" + req.stdout.slice(-1500));
    const plain = run({});
    assert.match(plain.stdout, /^# skipped 1$/m, "without the switch the leg skips\n" + plain.stdout.slice(-1500));
    assert.match(plain.stdout, new RegExp(esc(why)), "and the skip names the reason (" + why + ")\n" + plain.stdout.slice(-1500));
  } finally {
    fs.rmSync(empty, { recursive: true, force: true });
  }
});

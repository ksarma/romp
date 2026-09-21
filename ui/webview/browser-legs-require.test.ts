// browser-legs-require.ts by execution: without ROMP_BROWSER_LEGS_REQUIRE a failed launch or a missing playwright skips the
// test with the reason, as every browser leg did before the switch; with the switch set to "1" the same conditions throw,
// naming the switch, the reason and the remedy (a Chromium launch: "the runner lost its browser: check the Chromium install
// step"). The launch is a stub that rejects, so this module runs under plain node in the Test step and needs no browser;
// the switch is passed as an explicit environment where the test names it, and read from process.env in the one test that
// sets and restores the variable. The last test holds real-viewer-leg.ts's inBrowser to launchBrowser, the road the 82
// legs that import it take to the switch. Synthetic values only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { BROWSER_LEGS_REQUIRE, LOST_BROWSER, browserLegsRequired, launchBrowser, skipOrFail } from "./browser-legs-require";

const ON = { [BROWSER_LEGS_REQUIRE]: "1" };
const OFF = {};
const LAUNCH_ERROR = "browserType.launch: Executable doesn't exist at /nowhere/chrome\n\nLooks like Playwright was just installed";
const failing = (engine: string) => ({ [engine]: { launch: async () => { throw new Error(LAUNCH_ERROR); } } });
/** A node:test context stand-in that records skips. */
function context() {
  const skips: string[] = [];
  return { t: { skip: (why: string) => { skips.push(why); } }, skips };
}

test("without the switch a failed Chromium launch skips with the reason's first line and returns null", async () => {
  const { t, skips } = context();
  const browser = await launchBrowser(t, failing("chromium"), "chromium", {}, OFF);
  assert.equal(browser, null);
  assert.deepEqual(skips, ["no playwright chromium on this box; the browser leg needs it: browserType.launch: Executable doesn't exist at /nowhere/chrome"]);
});

test("under the switch a failed Chromium launch throws naming the switch, the reason and the Chromium install step, and skips nothing", async () => {
  const { t, skips } = context();
  await assert.rejects(launchBrowser(t, failing("chromium"), "chromium", {}, ON), (e: Error) => {
    assert.equal(e.message, "ROMP_BROWSER_LEGS_REQUIRE=1 and this browser leg cannot run: no playwright chromium on this box; the browser leg needs it: browserType.launch: Executable doesn't exist at /nowhere/chrome. " + LOST_BROWSER);
    return true;
  });
  assert.deepEqual(skips, [], "a throw is not also a skip");
  assert.equal(LOST_BROWSER, "the runner lost its browser: check the Chromium install step");
});

test("a failed Firefox launch under the switch names the Chromium-only install instead of the lost browser", async () => {
  const { t, skips } = context();
  await assert.rejects(launchBrowser(t, failing("firefox"), "firefox", {}, ON), (e: Error) => {
    assert.match(e.message, /^ROMP_BROWSER_LEGS_REQUIRE=1 and this browser leg cannot run: no playwright firefox on this box/);
    assert.ok(e.message.endsWith("the gating job installs Chromium only; a leg that launches firefox belongs in ci-browser-legs-excluded.txt with that reason"), e.message);
    assert.ok(!e.message.includes(LOST_BROWSER), "the Chromium remedy is not offered for another engine");
    return true;
  });
  assert.deepEqual(skips, []);
  const off = context();
  assert.equal(await launchBrowser(off.t, failing("firefox"), "firefox", {}, OFF), null);
  assert.equal(off.skips.length, 1, "without the switch the Firefox launch skips");
});

test("a missing playwright skips without the switch and throws under it, naming the package and the install step", async () => {
  const off = context();
  assert.equal(await launchBrowser(off.t, null, "chromium", {}, OFF), null);
  assert.deepEqual(off.skips, ["playwright is not installed under vscode-extension; the browser leg needs it"]);
  const on = context();
  await assert.rejects(launchBrowser(on.t, null, "chromium", {}, ON), (e: Error) => {
    assert.equal(e.message, "ROMP_BROWSER_LEGS_REQUIRE=1 and this browser leg cannot run: playwright is not installed under vscode-extension; the browser leg needs it. run npm ci in vscode-extension (in CI: check the Install deps step)");
    return true;
  });
  assert.deepEqual(on.skips, []);
});

test("a launch that succeeds returns the browser with nothing skipped, switch or no switch, and passes the launch options through", async () => {
  for (const env of [ON, OFF]) {
    const { t, skips } = context();
    const seen: any[] = [];
    const pw = { chromium: { launch: async (opts: any) => { seen.push(opts); return { name: "a browser" }; } } };
    const browser = await launchBrowser(t, pw, "chromium", { args: ["--x"] }, env);
    assert.deepEqual(browser, { name: "a browser" });
    assert.deepEqual(seen, [{ args: ["--x"] }]);
    assert.deepEqual(skips, []);
  }
});

test("only the value 1 arms the switch, and process.env is the default environment", async () => {
  assert.equal(browserLegsRequired({ [BROWSER_LEGS_REQUIRE]: "1" }), true);
  for (const v of ["true", "0", "", "yes", undefined]) assert.equal(browserLegsRequired({ [BROWSER_LEGS_REQUIRE]: v }), false, JSON.stringify(v));
  const had = Object.prototype.hasOwnProperty.call(process.env, BROWSER_LEGS_REQUIRE);
  const was = process.env[BROWSER_LEGS_REQUIRE];
  try {
    process.env[BROWSER_LEGS_REQUIRE] = "1";
    assert.equal(browserLegsRequired(), true);
    const { t, skips } = context();
    await assert.rejects(launchBrowser(t, failing("chromium")), /ROMP_BROWSER_LEGS_REQUIRE=1 and this browser leg cannot run/);
    assert.throws(() => skipOrFail(t, "a reason", "a remedy"), { message: "ROMP_BROWSER_LEGS_REQUIRE=1 and this browser leg cannot run: a reason. a remedy" });
    assert.deepEqual(skips, []);
    process.env[BROWSER_LEGS_REQUIRE] = "true";
    assert.equal(browserLegsRequired(), false);
    skipOrFail(t, "a reason", "a remedy");
    assert.deepEqual(skips, ["a reason"], "any other value leaves the skip a skip");
  } finally {
    if (had) process.env[BROWSER_LEGS_REQUIRE] = was; else delete process.env[BROWSER_LEGS_REQUIRE];
  }
});

test("real-viewer-leg.ts's inBrowser launches through launchBrowser and skips through nothing else (the legs that import it reach the switch; the branches are the executed tests above)", () => {
  const src = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "real-viewer-leg.ts"), "utf8");
  assert.match(src, /import \{ launchBrowser \} from "\.\/browser-legs-require";/);
  assert.match(src, /export async function inBrowser\(t: any, body: \(browser: any\) => Promise<void>\): Promise<void> \{\n  const browser = await launchBrowser\(t, pw, "chromium"\);\n  if \(!browser\) return;\n/);
  assert.ok(!src.includes("t.skip("), "the shared helper has no skip of its own: a skip there would stand outside the switch");
});

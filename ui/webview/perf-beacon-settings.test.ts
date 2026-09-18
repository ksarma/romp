// The beacon extension's two gear switches (the user 2026-09-18, who wanted the phone's timing shared only by choice) as
// the gear renders and wires them, and the one contract their store keys form across the gear (gear.js), the settings
// module (settings.ts), the collector (perf-telemetry.ts), the pane shim and the shell script (kernel.py): every reader
// spells the same two keys under romp:settings and turns a switch on for the literal true alone. Source pins, the way
// dense-chrome.test.ts pins its row.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const UI = path.resolve(process.cwd(), "..", "ui", "webview");
const read = (f: string) => fs.readFileSync(path.join(UI, f), "utf8");
const GEAR = read("gear.js");
const SETTINGS = read("settings.ts");
const PERF = read("perf-telemetry.ts");
const KERNEL = fs.readFileSync(path.resolve(process.cwd(), "..", "kernel", "kernel.py"), "utf8");

test("the two rows sit under Debug > Diagnostics ahead of the analytics button, labelled in plain words, off by default, wired like every boolean", () => {
  const share = GEAR.indexOf("id=rs-perfshare"), mute = GEAR.indexOf("id=rs-perfmute");
  assert.ok(share > 0 && mute > share, "both checkboxes exist, share first");
  assert.ok(GEAR.indexOf(">Diagnostics<") < share, "under the Diagnostics header");
  assert.ok(mute < GEAR.indexOf("id=ra-open"), "ahead of the analytics and log buttons");
  assert.ok(GEAR.indexOf("data-pane=debug") < share, "on the Debug tab");
  assert.ok(GEAR.includes("<b>Share this browser's timing rows</b>"), "the share label");
  assert.ok(GEAR.includes("<b>Stop all timing rows from this browser</b>"), "the kill switch's label");
  const subShare = GEAR.slice(share, mute).match(/<span class=rs-sub>([^<]*)<\/span>/)![1];
  assert.match(subShare, /Numbers and fixed names only, never text\./, "the privacy line, in the user's words");
  assert.match(subShare, /Off by default\.$/);
  const subMute = GEAR.slice(mute, GEAR.indexOf("id=ra-open")).match(/<span class=rs-sub>([^<]*)<\/span>/)![1];
  assert.match(subMute, /the standard ones included/, "the kill switch covers the rows the browser sent before the switch existed");
  assert.match(subMute, /Off by default\.$/);
  for (const sub of [subShare, subMute]) assert.doesNotMatch(sub, /clientDiag|beacon|telemetry|kernel\.py|localStorage/, "no code words in the copy");
  assert.ok(GEAR.includes("psh = document.getElementById('rs-perfshare'), pmu = document.getElementById('rs-perfmute')"), "the handles");
  assert.ok(GEAR.includes("if (psh) psh.addEventListener('change', function () { var s = load(); s.perfShare = psh.checked; save(s); });"), "the share save path: save() raises romp:settings and posts settingsSync, like every boolean here");
  assert.ok(GEAR.includes("if (pmu) pmu.addEventListener('change', function () { var s = load(); s.perfMute = pmu.checked; save(s); });"), "the kill switch's save path");
  assert.ok(GEAR.includes("if (psh) psh.checked = s.perfShare === true; if (pmu) pmu.checked = s.perfMute === true;"), "the open-time fill reads the store, true alone");
  const load = GEAR.slice(GEAR.indexOf("function load()"), GEAR.indexOf("function tabCtxMode"));
  assert.equal((load.match(/perfShare: false/g) || []).length, 2, "both copies of the defaults mirror carry the share default");
  assert.equal((load.match(/perfMute: false/g) || []).length, 2, "and the kill switch's");
  assert.doesNotMatch(GEAR, /perfShare: true|perfMute: true/, "never on by default");
});

test("the store keys are one contract: settings.ts, the collector, the pane shim and the shell script spell perfShare and perfMute under romp:settings and read the literal true alone", () => {
  assert.match(SETTINGS, /^  perfShare: boolean;/m); assert.match(SETTINGS, /^  perfMute: boolean;/m);
  assert.ok(SETTINGS.includes("perfShare: false, perfMute: false,"), "DEFAULT_SETTINGS carries both, off");
  assert.ok(SETTINGS.includes("s.perfShare = s.perfShare === true;"), "loadSettings normalizes the share switch to the literal true");
  assert.ok(SETTINGS.includes("s.perfMute = s.perfMute === true;"), "and the kill switch");
  assert.ok(PERF.includes('export const SETTINGS_KEY = "romp:settings";'));
  assert.ok(PERF.includes('export const SHARE_SETTING = "perfShare";'));
  assert.ok(PERF.includes('export const MUTE_SETTING = "perfMute";'));
  assert.ok(PERF.includes("s[SHARE_SETTING] === true") && PERF.includes("s[MUTE_SETTING] === true"), "the collector reads the literal true");
  // the shim and the shell each carry the one-line reader; both read the kill switch alone (the share switch is the collector's)
  const readers = KERNEL.match(/function diagMuted\(\)\{try\{var st=JSON\.parse\(localStorage\.getItem\('romp:settings'\)\|\|'null'\);return !!\(st&&st\.perfMute===true\);\}catch\(e\)\{return false;\}\}/g) || [];
  assert.equal(readers.length, 2, "the pane shim's and the shell's readers, byte for byte the same");
  assert.equal((KERNEL.match(/perfShare/g) || []).length, 0, "the kernel never reads the share switch: the collector does, per page");
});

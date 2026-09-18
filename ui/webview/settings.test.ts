import { test } from "node:test";
import * as assert from "node:assert/strict";

// Minimal localStorage shim BEFORE importing the module (load/save read it at call time).
const store: Record<string, string> = {};
(globalThis as any).localStorage = {
  getItem: (k: string) => (k in store ? store[k] : null),
  setItem: (k: string, v: string) => { store[k] = v; },
  removeItem: (k: string) => { delete store[k]; },
};
import { loadSettings, saveSettings, DEFAULT_SETTINGS, FIGURE_HOSTS_DEFAULT, figureHosts, figureHostName, paneSet, OPTIONAL_PANES } from "./settings";

test("loadSettings returns defaults when nothing is stored", () => {
  delete store["romp:settings"];
  assert.deepEqual(loadSettings(), DEFAULT_SETTINGS);
});

test("the Sub-goals card pref defaults ON; the old Explanations pref is gone (the user 2026-06-18)", () => {
  assert.equal(DEFAULT_SETTINGS.subgoals, true);
  assert.equal((DEFAULT_SETTINGS as any).explanations, undefined);
});

test("both judge-set toggles default OFF (the user 2026-06-29): the timeline's judging band stays hidden", () => {
  assert.equal(DEFAULT_SETTINGS.showIndexJudges, false);
  assert.equal(DEFAULT_SETTINGS.showTriageJudges, false);
});

test("Default backend defaults to sdk (the user 2026-07-13); Claude Code and Codex coexist", () => {
  assert.equal(DEFAULT_SETTINGS.backend, "sdk");
});

test("a saved default of the retired terminal backend reads as sdk, never an undefined value (T331)", () => {
  localStorage.setItem("romp:settings", JSON.stringify({ ...DEFAULT_SETTINGS, backend: "tmux" }));
  assert.equal(loadSettings().backend, "sdk");
  localStorage.setItem("romp:settings", JSON.stringify({ ...DEFAULT_SETTINGS, backend: "nonsense" }));
  assert.equal(loadSettings().backend, "sdk", "any value no longer offered reads as the default");
  localStorage.setItem("romp:settings", JSON.stringify({ ...DEFAULT_SETTINGS, backend: "codex" }));
  assert.equal(loadSettings().backend, "codex", "an offered pick stands");
  saveSettings({ backend: "sdk" });
});

test("Compact transcript defaults ON (the user 2026-07-14): fresh installs read the tidy transcript", () => {
  assert.equal(DEFAULT_SETTINGS.compact, true);
});

// The tab strip's one-group-per-row layout (upstream's T264 default) is a per-device opt-in on the fork
// (the user 2026-09-08, whose strip of eleven tag groups became eleven rows): off, the groups flow inline.
test("stripGroupRows defaults OFF (the user 2026-09-08): the strip flows inline; the gear's checkbox is the opt-in and round-trips", () => {
  assert.equal(DEFAULT_SETTINGS.stripGroupRows, false);
  store["romp:settings"] = JSON.stringify({ stripGroupRows: true });
  assert.equal(loadSettings().stripGroupRows, true, "the opt-in round-trips");
  store["romp:settings"] = JSON.stringify({});
  assert.equal(loadSettings().stripGroupRows, false, "a store from before the key reads as off");
  delete store["romp:settings"];
});

// The settings change signal must cover every way a change can happen: another
// same-origin tab (storage event), THIS document (the gear now lives in the same
// page — same-document writes never fire storage), and another VS Code webview
// (separate origin + localStorage → the host relays {settingsSync}, applied by
// installSettingsSync). The dead compact toggle (the user 2026-07-14) was the
// same-document gap.
test("settings changes propagate same-document and cross-webview, not just cross-tab", () => {
  const fs = require("node:fs") as typeof import("node:fs");
  const path = require("node:path") as typeof import("node:path");
  const ROOT = path.resolve(process.cwd(), "..");
  const src = fs.readFileSync(path.join(ROOT, "ui", "webview", "settings.ts"), "utf8");
  assert.ok(src.includes('addEventListener("storage"'), "cross-tab: the storage event");
  assert.ok(src.includes('addEventListener("romp:settings"'), "same-document: the gear's save() signal");
  assert.ok(src.includes('"settingsSync"'), "cross-webview: the host-relayed sync applies here");
  const gear = fs.readFileSync(path.join(ROOT, "ui", "webview", "gear.js"), "utf8");
  const save = gear.slice(gear.indexOf("function save(s)"), gear.indexOf("cc.addEventListener"));
  assert.ok(save.includes("dispatchEvent(new Event('romp:settings'))"), "save() always raises the same-doc signal");
  assert.ok(save.includes("settingsSync"), "save() always posts the cross-webview sync");
  const ext = fs.readFileSync(path.join(ROOT, "vscode-extension", "src", "extension.ts"), "utf8");
  assert.ok(ext.includes("function broadcastSettings"), "the host fans a gear save out to the other panes");
  const intercepts = ext.match(/m\.type === "settingsSync"/g) || [];
  assert.equal(intercepts.length, 2, "chat AND feed handlers intercept settingsSync (the two gear hosts)");
});

test("the backend pref roundtrips through storage (the gear writes it; createSession reads it fresh)", () => {
  delete store["romp:settings"];
  saveSettings({ backend: "sdk" });
  assert.equal(loadSettings().backend, "sdk");
});

test("saveSettings persists a patch and merges over defaults", () => {
  delete store["romp:settings"];
  const next = saveSettings({ compact: true });
  assert.equal(next.compact, true);
  assert.equal(loadSettings().compact, true, "the change is read back from storage");
});

test("loadSettings tolerates corrupt JSON → defaults", () => {
  store["romp:settings"] = "{not json";
  assert.deepEqual(loadSettings(), DEFAULT_SETTINGS);
});

test("an unknown key in storage is ignored, known keys still merge", () => {
  store["romp:settings"] = JSON.stringify({ compact: true, future: 42 });
  const s = loadSettings();
  assert.equal(s.compact, true);
  assert.equal((s as any).future, 42, "merge is shallow — extra keys pass through harmlessly");
});

// The file viewer's figures from the web (decision 8 of plans/markdown-viewer.md): the hosts whose pictures load on open.
test("figureHosts defaults to github.com and its image hosts, localhost and 127.0.0.1; a store from before the setting reads as that list; a stored list is trimmed and lower-cased; a foreign value reads as the default", () => {
  delete store["romp:settings"];
  assert.deepEqual(loadSettings().figureHosts, [...FIGURE_HOSTS_DEFAULT]);
  store["romp:settings"] = JSON.stringify({ compact: true });
  assert.deepEqual(loadSettings().figureHosts, [...FIGURE_HOSTS_DEFAULT], "an older store: the default list");
  store["romp:settings"] = JSON.stringify({ figureHosts: ["Remote.TEST", " other.test ", ""] });
  assert.deepEqual(loadSettings().figureHosts, ["remote.test", "other.test"]);
  store["romp:settings"] = JSON.stringify({ figureHosts: "a.test\nb.test" });
  assert.deepEqual(loadSettings().figureHosts, ["a.test", "b.test"], "the textarea's text, should a store hold it");
  store["romp:settings"] = JSON.stringify({ figureHosts: { no: "list" } });
  assert.deepEqual(loadSettings().figureHosts, [...FIGURE_HOSTS_DEFAULT], "a foreign value never reads as no host at all");
  store["romp:settings"] = JSON.stringify({ figureHosts: [] });
  assert.deepEqual(loadSettings().figureHosts, [], "an emptied list is a choice and stands");
  const saved = saveSettings({ figureHosts: ["x.test"] });
  assert.deepEqual(saved.figureHosts, ["x.test"]);
  assert.deepEqual(loadSettings().figureHosts, ["x.test"], "round-trips through storage");
  delete store["romp:settings"];
});

// The Slice 4 review, round 1: the normaliser kept a line as typed, so an address pasted whole, a port, a path, an
// internationalised or a leading-zero spelling never equalled the URL.hostname the gate compares (figure-gate.ts
// remoteHost), and the host it named stayed gated with no sign in the gear.
test("figureHosts reads every entry down to the host name the gate compares: an address, a port, a path, an IDN and an IPv4 spelling come back canonical, once each; a line the URL parser refuses is kept as typed, lower-cased, so the gear can show it back", () => {
  assert.equal(figureHostName("https://cdn.test/a.png"), "cdn.test");
  assert.equal(figureHostName(" HTTPS://Upper.TEST "), "upper.test", "trimmed, the scheme's case and the host's ignored");
  assert.equal(figureHostName("cdn.test/"), "cdn.test");
  assert.equal(figureHostName("cdn.test:8080"), "cdn.test", "a port, not a scheme");
  assert.equal(figureHostName("cdn.test?x=1#f"), "cdn.test");
  assert.equal(figureHostName("//proto.test/x"), "proto.test");
  assert.equal(figureHostName("user@cred.test"), "cred.test");
  assert.equal(figureHostName("bücher.test"), "xn--bcher-kva.test", "the parser's spelling, which the reader also gives");
  assert.equal(figureHostName("127.000.000.001"), "127.0.0.1");
  assert.equal(figureHostName("0x7f.1"), "127.0.0.1");
  assert.equal(figureHostName("[::1]"), "[::1]");
  assert.equal(figureHostName("localhost."), "localhost.", "a trailing dot is another host to the browser too");
  assert.equal(figureHostName("ftp://ftp.test/x"), "ftp.test", "a host is a host whatever the scheme typed");
  for (const bad of ["", "  ", "[bad", "x^y.test", "%zz.test", "http://", "file:///x", "::1", "192.168.1.256", "https:cdn.test"]) assert.equal(figureHostName(bad), null, JSON.stringify(bad));
  assert.deepEqual(figureHosts("https://cdn.test\ncdn.test/, cdn.test:8080 bücher.test\n127.000.000.001 [Bad  github.com"), ["cdn.test", "xn--bcher-kva.test", "127.0.0.1", "[bad", "github.com"], "the textarea's text: one cdn.test for its three spellings, the refused line kept");
  assert.deepEqual(figureHosts(["https://cdn.test", "Other.TEST:8080", "[Bad", 3 as unknown as string]), ["cdn.test", "other.test", "[bad"]);
  store["romp:settings"] = JSON.stringify({ figureHosts: ["https://cdn.test", "Other.TEST:8080", "[Bad"] });
  assert.deepEqual(loadSettings().figureHosts, ["cdn.test", "other.test", "[bad"], "a stored list reads canonical on load");
  assert.deepEqual(figureHosts([...FIGURE_HOSTS_DEFAULT]), [...FIGURE_HOSTS_DEFAULT], "the default list is already canonical");
  delete store["romp:settings"];
});

// Compact tabs and agents (the user 2026-09-08: on a phone, the tab strip and the background-work panel
// left about three lines of transcript in view): OFF by default, so the strip and the panel render exactly
// as before the setting existed until the gear opts in. Distinct from `compact`, the transcript's own
// tidy-up (tool runs collapsed, thinking hidden). The class it drives is dense-chrome.test.ts's subject.
test("Compact tabs and agents defaults OFF (the user 2026-09-08); the opt-in round-trips, and a store from before the key reads as off", () => {
  assert.equal(DEFAULT_SETTINGS.denseChrome, false);
  delete store["romp:settings"];
  assert.equal(loadSettings().denseChrome, false, "a fresh install reads off");
  saveSettings({ denseChrome: true });
  assert.equal(loadSettings().denseChrome, true, "the opt-in survives a reload (localStorage)");
  store["romp:settings"] = JSON.stringify({ compact: true });
  assert.equal(loadSettings().denseChrome, false, "a store written before the key reads as off");
  delete store["romp:settings"];
});

// The file-links preference is GONE (T404, the user 2026-09-13): where a chat file link opens follows whether the Files pane
// is open (file-route.ts fileLinkRoute takes no setting). A store that still carries the old key reads without it and the next
// save leaves it behind, the T317-era filesControl key's way.
test("fileLinkPane: no such setting; a stored value is dropped, never read", () => {
  assert.equal((DEFAULT_SETTINGS as unknown as Record<string, unknown>).fileLinkPane, undefined);
  store["romp:settings"] = JSON.stringify({ fileLinkPane: "pane" });
  assert.equal((loadSettings() as unknown as Record<string, unknown>).fileLinkPane, undefined, "an old store's value is not read");
  saveSettings({ compact: false });
  assert.equal(JSON.parse(store["romp:settings"]).fileLinkPane, undefined, "…and the next save leaves it behind");
  assert.equal(loadSettings().compact, false);
});

// The optional dashboard panes (the user 2026-09-10): Sessions (key timeline), Outline (key fleet) and Feed
// can be hidden from the dashboard in the gear, per browser. All shown by default, so a dashboard that never
// opens the section is unchanged; only an explicit stored false hides a pane (a missing key, a store from
// before the setting, or a corrupt value reads as shown), and every key is present after a load so the
// shell's controller (_LANDING_COLLAPSE_JS) never has to guess. The chat is required and not listed.
test("the optional panes default to shown, a hide round-trips, and only an explicit false hides (the user 2026-09-10)", () => {
  assert.deepEqual(DEFAULT_SETTINGS.panes, { timeline: true, fleet: true, feed: true });
  assert.deepEqual([...OPTIONAL_PANES], ["timeline", "fleet", "feed"], "the chat is required and is not an optional pane");
  delete store["romp:settings"];
  assert.deepEqual(loadSettings().panes, { timeline: true, fleet: true, feed: true }, "a fresh install shows every pane");
  saveSettings({ panes: { timeline: true, fleet: true, feed: false } });
  assert.deepEqual(loadSettings().panes, { timeline: true, fleet: true, feed: false }, "hiding the feed survives a reload");
  store["romp:settings"] = JSON.stringify({ compact: true });
  assert.deepEqual(loadSettings().panes, { timeline: true, fleet: true, feed: true }, "a store from before the key shows every pane");
  store["romp:settings"] = JSON.stringify({ panes: { feed: false } });
  assert.deepEqual(loadSettings().panes, { timeline: true, fleet: true, feed: false }, "a partial set fills the missing panes in as shown");
  store["romp:settings"] = JSON.stringify({ panes: "purple" });
  assert.deepEqual(loadSettings().panes, { timeline: true, fleet: true, feed: true }, "a corrupt value costs nothing but the preference");
  assert.deepEqual(paneSet({ timeline: 0, fleet: "no", feed: null }), { timeline: true, fleet: true, feed: true }, "falsy but not false is not a hide");
  assert.deepEqual(paneSet(undefined), { timeline: true, fleet: true, feed: true });
  delete store["romp:settings"];
});

// The Files CONTROL's own setting (T317, the user 2026-09-10): whether the dashboard bar's Files toggle and the
// phone's Files tab show at all. OFF by default (T317b, the user the same day: the control is asked for, not
// shipped); only the literal true shows them, so a corrupt entry may cost the preference, never surprise the user
// with a control. The shell reads the store key itself (kernel.py _LANDING_COLLAPSE_JS filesCtl), so the key and
// the true-only rule are the contract.
test("the Files control is hidden by default; showing it round-trips, and only the literal true under the fresh key shows it", () => {
  assert.equal(DEFAULT_SETTINGS.showFilesControl, false);
  delete store["romp:settings"];
  assert.equal(loadSettings().showFilesControl, false, "a fresh install hides the control");
  saveSettings({ showFilesControl: true });
  assert.equal(loadSettings().showFilesControl, true, "showing it survives a reload (localStorage)");
  assert.equal(JSON.parse(store["romp:settings"]).showFilesControl, true, "the key the shell reads, the literal true");
  saveSettings({ showFilesControl: false });
  assert.equal(loadSettings().showFilesControl, false, "turning it off again round-trips too");
  assert.equal(JSON.parse(store["romp:settings"]).showFilesControl, false, "on-then-off leaves the literal false");
  store["romp:settings"] = JSON.stringify({ compact: true });
  assert.equal(loadSettings().showFilesControl, false, "a store written before the key hides the control");
  store["romp:settings"] = JSON.stringify({ showFilesControl: "yes" });
  assert.equal(loadSettings().showFilesControl, false, "a foreign stored value hides it: only true shows");
  // the T317-era key: that gear merged its default filesControl: true into the object and saved the whole object on
  // ANY change, so a profile that touched any setting in that window carries filesControl: true without touching the
  // Files box. It is never read, and the next save drops it.
  store["romp:settings"] = JSON.stringify({ compact: true, filesControl: true });
  assert.equal(loadSettings().showFilesControl, false, "the old key's true is a merged-in default, not an opt-in: hidden");
  assert.equal("filesControl" in loadSettings(), false, "the old key is dropped from the loaded object");
  saveSettings({ compact: false });
  assert.deepEqual(Object.keys(JSON.parse(store["romp:settings"])).filter((k) => /filesControl/i.test(k)), ["showFilesControl"], "the next save leaves the old key behind and writes the fresh one");
  delete store["romp:settings"];
});

// The beacon extension's two switches (2026-09-18): the browser's timing rows carry the page-load, resource, environment,
// visibility, byte and frame-gap fields only when perfShare holds the literal true, and perfMute true stops every row.
// Read raw from the store by the collector in every pane and the shell, by the pane shim and by the shell script
// (perf-telemetry.ts readSwitches, kernel.py diagMuted), so the key names and the true-only rule are the contract.
test("the beacon switches are off by default; each round-trips, and only the literal true turns one on", () => {
  assert.equal(DEFAULT_SETTINGS.perfShare, false);
  assert.equal(DEFAULT_SETTINGS.perfMute, false);
  delete store["romp:settings"];
  assert.equal(loadSettings().perfShare, false, "a fresh install shares nothing");
  assert.equal(loadSettings().perfMute, false, "and mutes nothing");
  saveSettings({ perfShare: true });
  assert.equal(loadSettings().perfShare, true, "sharing survives a reload");
  assert.equal(JSON.parse(store["romp:settings"]).perfShare, true, "the key the collector reads, the literal true");
  assert.equal(loadSettings().perfMute, false, "one switch does not move the other");
  saveSettings({ perfMute: true });
  assert.equal(JSON.parse(store["romp:settings"]).perfMute, true, "the key the shim and the shell read");
  saveSettings({ perfShare: false, perfMute: false });
  assert.equal(loadSettings().perfShare, false); assert.equal(loadSettings().perfMute, false);
  store["romp:settings"] = JSON.stringify({ compact: true });
  assert.equal(loadSettings().perfShare, false, "a store written before the keys shares nothing");
  assert.equal(loadSettings().perfMute, false);
  store["romp:settings"] = JSON.stringify({ perfShare: "yes", perfMute: 1 });
  assert.equal(loadSettings().perfShare, false, "a foreign stored value reads off: only true turns a switch on");
  assert.equal(loadSettings().perfMute, false);
  delete store["romp:settings"];
});

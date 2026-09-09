// COMPACT TABS AND AGENTS (the user 2026-09-08, whose phone showed about three lines of transcript between the
// tab strip and the box of background work): one boolean setting, off by default, applied as ONE body class by
// a pure applier and answered by a scoped block in styles.css. Density only: no render path changes, and every
// dense rule shadows a default that stays byte-identical. Executable where the logic is importable
// (settings.ts, dense-chrome.ts); pinned at the source where it lives in a foreign host (gear.js, render.ts,
// styles.css, docs/guide.md), the repo's convention (theme.test.ts, chat-scheme.test.ts).
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { DEFAULT_SETTINGS, type RompSettings } from "./settings";
import { applyDenseChrome, DENSE_CHROME_CLASS } from "./dense-chrome";

const read = (...p: string[]) => fs.readFileSync(path.resolve(process.cwd(), "..", ...p), "utf8");
const CSS = read("ui", "webview", "styles.css");
const FEED = read("ui", "webview", "feed.css");
const RENDER = read("ui", "webview", "render.ts");
const GEAR = read("ui", "webview", "gear.js");
const GUIDE = read("docs", "guide.md");

const esc = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
// the FIRST rule for a selector at the start of a line: the default, written above the dense block
const defaultRule = (sel: string) => {
  const m = CSS.match(new RegExp("(?:^|\\n)" + esc(sel) + " \\{([^}]*)\\}"));
  assert.ok(m, sel + " has a default rule");
  return m![1];
};
const denseRule = (sel: string) => {
  const m = CSS.match(new RegExp("\\nbody\\." + DENSE_CHROME_CLASS + " " + esc(sel) + " \\{([^}]*)\\}"));
  assert.ok(m, sel + " has a dense rule under body." + DENSE_CHROME_CLASS);
  return m![1];
};
const stripComments = (css: string) => css.replace(/\/\*[\s\S]*?\*\//g, "");

test("executable: the applier toggles exactly one body class, on for true alone", () => {
  const classes = new Set<string>();
  const doc = { body: { classList: { toggle: (c: string, on: boolean) => { if (on) classes.add(c); else classes.delete(c); } } } } as unknown as Document;
  applyDenseChrome(doc, { ...DEFAULT_SETTINGS, denseChrome: true });
  assert.deepEqual([...classes], [DENSE_CHROME_CLASS], "on: the class is present");
  applyDenseChrome(doc, { ...DEFAULT_SETTINGS, denseChrome: false });
  assert.deepEqual([...classes], [], "off: the class is absent");
  applyDenseChrome(doc, { ...DEFAULT_SETTINGS, denseChrome: true });
  applyDenseChrome(doc, { ...DEFAULT_SETTINGS });
  assert.deepEqual([...classes], [], "the default is off");
  applyDenseChrome(doc, { ...DEFAULT_SETTINGS, denseChrome: "yes" as unknown as boolean });
  assert.deepEqual([...classes], [], "junk in the store never densifies: only true is on");
  const older = { ...DEFAULT_SETTINGS } as Partial<RompSettings>;
  delete older.denseChrome;
  classes.add(DENSE_CHROME_CLASS);
  applyDenseChrome(doc, older as RompSettings);
  assert.deepEqual([...classes], [], "a store from before the setting existed reads as off");
});

test("the chat applies the class beside the scheme and the theme, at startup and on every settings change", () => {
  assert.match(RENDER, /import \{ applyDenseChrome \} from "\.\/dense-chrome";/);
  const body = RENDER.slice(RENDER.indexOf("function applyChatScheme("), RENDER.indexOf("function setupSettings("));
  assert.match(body, /applyDenseChrome\(document, s\);/, "one applier call inside applyChatScheme");
  // the two moments applyChatScheme runs (chat-scheme.test.ts pins the same lines): the persisted pick at
  // startup, and the same-document / cross-tab / cross-webview settings signal, which is how a gear flip
  // repaints the strip and the box at once (a body class, the cascade does the rest; no rebuild)
  assert.match(RENDER, /applyChatScheme\(settings\);   \/\/ the persisted pick applies at startup/);
  assert.match(RENDER, /onExternalSettingsChange\(\(s\) => \{ settings = s; applyChatScheme\(s\);/);
});

test("the gear row mirrors the other booleans: Chat section, save path, open-time fill, defaults mirror", () => {
  const at = GEAR.indexOf("id=rs-dense");
  assert.ok(at > 0, "the checkbox exists in the gear markup");
  assert.ok(GEAR.indexOf(">Chat<") < at, "in the Chat section");
  assert.ok(at < GEAR.indexOf("id=rs-branch"), "before Show git branch (after Compact transcript)");
  assert.ok(GEAR.includes("<b>Compact tabs and agents</b>"), "the label");
  assert.ok(GEAR.includes("dn = document.getElementById('rs-dense')"), "the handle");
  assert.ok(GEAR.includes("if (dn) dn.addEventListener('change', function () { var s = load(); s.denseChrome = dn.checked; save(s); });"),
    "the save path: save() raises romp:settings and posts settingsSync, like every boolean here");
  assert.ok(GEAR.includes("if (dn) dn.checked = s.denseChrome === true;"), "the open-time fill reads the store");
  const load = GEAR.slice(GEAR.indexOf("function load()"), GEAR.indexOf("function tabCtxMode"));
  assert.equal((load.match(/denseChrome: false/g) || []).length, 2, "both copies of the defaults mirror carry the default");
});

test("the dense rules exist under the class, with these exact values", () => {
  const tab = denseRule(".tab");
  assert.match(tab, /gap: 3px;/); assert.match(tab, /padding: 3px 5px;/); assert.match(tab, /font-size: 0\.86em;/);
  assert.match(denseRule(".tab-add"), /padding: 3px 8px;/);
  const head = denseRule(".tab-group-head");
  assert.match(head, /gap: 4px;/); assert.match(head, /padding: 3px 5px 3px 4px;/);
  assert.doesNotMatch(head, /font-size/, "the group header keeps the surface's one sub-line size (0.82em); its count inherits it and stays legible");
  assert.match(denseRule("#bg-tasks"), /margin: 4px 10px 4px;/);
  assert.match(denseRule(".bg-fold-head"), /padding: 5px 11px;/);
  const list = denseRule(".bg-list");
  assert.match(list, /padding: 2px 2px;/); assert.match(list, /max-height: 100px;/, "about four rows; the inner scroll is the default rule's");
  assert.match(denseRule(".bg-group-head"), /padding: 3px 9px 1px;/);
  const row = denseRule(".bg-head");
  assert.match(row, /gap: 6px;/); assert.match(row, /padding: 3px 9px;/); assert.match(row, /line-height: 1\.3;/);
  assert.match(denseRule(".bg-sum"), /font-size: 11px;/);
  assert.match(denseRule(".bg-since"), /font-size: 10px;/);
});

test("the trailing status word hides only where the dot already says it; the label and the arrow stay", () => {
  const m = CSS.match(/\n(body\.dense-chrome \.bg-task\.bg-[a-z]+ > \.bg-head > \.bg-status,?\n?)+ \{ display: none; \}/);
  assert.ok(m, "one rule hides .bg-status by row status");
  const statuses = Array.from(m![0].matchAll(/\.bg-task\.bg-([a-z]+) >/g)).map((x) => x[1]).sort();
  assert.deepEqual(statuses, ["armed", "completed", "failed", "running"],
    "the four captions that repeat the dot (taskRowSpec / awaitRowSpec: caption === status); a timer's caption stays, its dot says only waiting");
  assert.doesNotMatch(m![0], /bg-sum|bg-open-agent|tool-open-agent/, "the label and the open-transcript arrow are not touched");
  // the render path is unchanged: the caption is still built for every row that has one
  assert.match(RENDER, /if \(t\.caption\) \{ const st = el\("span", "bg-status"\); st\.textContent = t\.caption; rh\.appendChild\(st\); \}/);
});

test("every dense rule is scoped to the body class, and the sheet's defaults are untouched", () => {
  const code = stripComments(CSS);
  for (const line of code.split("\n")) {
    if (!line.includes(DENSE_CHROME_CLASS)) continue;
    assert.match(line, new RegExp("^body\\." + DENSE_CHROME_CLASS + " "), "a dense line is a body-scoped selector: " + line.trim());
  }
  assert.doesNotMatch(FEED, /dense-chrome/, "the strip and the box live in styles.css alone; the feed's sheet has no dense rule");
  // the defaults, byte for byte the values the dense rules shadow
  const tab = defaultRule(".tab");
  assert.match(tab, /gap: 4px;/); assert.match(tab, /padding: 6px 7px; font-size: 0\.92em;/);
  assert.match(defaultRule(".tab-add"), /padding: 6px 10px;/);
  const head = defaultRule(".tab-group-head");
  assert.match(head, /gap: 5px; padding: 6px 7px 6px 6px;/); assert.match(head, /font-size: 0\.82em;/);
  assert.match(defaultRule("#bg-tasks"), /margin: 8px 10px 6px;/);
  assert.match(defaultRule(".bg-fold-head"), /padding: 7px 11px;/);
  const list = defaultRule(".bg-list");
  assert.match(list, /padding: 4px 2px;/); assert.doesNotMatch(list, /max-height/, "the default list has no cap of its own (the box's min(50vh, 340px))");
  assert.match(defaultRule(".bg-group-head"), /padding: 6px 9px 2px; font-size: 10px;/);
  assert.match(defaultRule(".bg-head"), /gap: 8px; padding: 5px 9px;/);
  assert.match(defaultRule(".bg-sum"), /font-size: 12px;/);
  assert.match(defaultRule(".bg-since"), /font-size: 11px;/);
  // the defaults come first, so the tests that read a selector's first rule keep reading the default
  for (const sel of [".tab", ".tab-add", ".tab-group-head", "#bg-tasks", ".bg-fold-head", ".bg-list", ".bg-group-head", ".bg-head", ".bg-sum", ".bg-since"]) {
    assert.ok(CSS.indexOf("\n" + sel + " {") < CSS.indexOf("\nbody." + DENSE_CHROME_CLASS + " " + sel + " {"), sel + ": default before dense");
  }
});

test("the dense sizes are the sheet's own rungs and none is under the 10px floor", () => {
  const block = stripComments(CSS.slice(CSS.indexOf("body." + DENSE_CHROME_CLASS + " .tab {")));
  const sizes = Array.from(block.matchAll(/font-size: ([^;]+);/g)).map((m) => m[1]);
  assert.deepEqual([...new Set(sizes)].sort(), ["0.86em", "10px", "11px"], "0.86em is on the em ladder (css-vocab.test.ts); 11px and 10px are the box's own (.bg-since, .bg-status)");
  for (const s of sizes) {
    const px = s.endsWith("em") ? parseFloat(s) * 13 : parseFloat(s);
    assert.ok(px >= 10, s + " is at or above the 10px floor");
  }
});

test("the guide names the setting by its gear label", () => {
  assert.match(GUIDE, /\*\*Compact tabs and agents\*\*/);
  assert.match(GUIDE, /about four rows/);
});

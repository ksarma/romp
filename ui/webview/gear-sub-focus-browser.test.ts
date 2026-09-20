// The per-setting description opens on a KEYBOARD focus as it opens on hover (2026-09-20; the maintainer's round 3 of the
// wsBytesByHost field, ui-1: the share switch's description under Debug > Diagnostics, the consent text for the phone's timing
// rows with the per-machine socket-byte sentence the maintainer's round 1 of that review ruled in, rendered for a pointer alone,
// so a keyboard or a screen reader never saw it). The focus road is keyed on `:focus-visible` (the maintainer's round 4, ui-2:
// keyed on `:focus-within` it opened on a mouse click too, and since nothing blurs a clicked checkbox the description outlived
// the pointer and covered the next row after every click), in the descendant form `:has(:focus-visible)` since the focused
// element is the control, never the row. ONE tooltip across the PANEL (round 4, correctness-1): a keyboard focus in one row and
// a pointer in another showed two descriptions, the second drawn inside the first on adjacent rows, so a panel-wide stand-down
// hides every description outside the hovered row while a row with a description, or any mixed mark, is hovered: THE POINTER
// WINS, the rule the sheet's other one-tooltip rules follow. And the placement class `rs-up` is re-placed for every host of the
// row on every road's enter and exit (round 4, correctness-2): each exit stripped it unconditionally, so a pointer leaving a row
// whose checkbox held a keyboard focus dropped the placement of a description still shown, and it ran past the card's bottom;
// and a road moving from a row's picker button into its box never left the row, so the row's class stayed behind.
//
// And the row holding the keyboard focus is re-placed on the pointer road's enter and exit too (the author's fixer pass after
// round 4, panel-1): a focus that arrived while the pointer rested on another row with a description measured a popover the
// panel-wide stand-down hid, and the pointer's exit re-placed its own row alone, so the focused row's description appeared
// below it unplaced and past the card's bottom, the T408 clip on a new road.
//
// Two pins over the sources for every runner, and browser legs over the REAL gear module and its stylesheet, the
// gear-judge-fast-browser.test.ts pattern (a fake kernel behind page.route; skips with a stated reason without a playwright
// browser). WHAT THE GATE CHECKS, and where (the maintainer's round 5, tests-1): CI's vscode-extension job runs `npm test` BEFORE
// it installs Chromium, so at that step every browser leg in this file skips and the gate's read of this file is the source
// pins alone (the parsed-sheet pins on the rules and the gear.js wiring pins); the job then installs Chromium and runs this
// file again by name, the "Gear description browser legs" step under ROMP_GEAR_BROWSER_REQUIRE=1, where the browser legs run in
// that Chromium and a skip is a failure naming its reason (the pane bench's stance), pinned by tests/test_served_labs_under_ci.py.
// A developer's machine with playwright's Chromium runs both in one `npm test`. The surface the browser legs exclude: Firefox
// and WebKit (the three-engine readings in the review record came from a scratch matrix, not this file), and every engine
// generation that lacks :has(), which the degradation leg below MODELS rather than installs. And the STATES the legs do not
// enter (the author's fixer pass after round 5, exclusions-1, -4 and -5; the ruler's lesson: name what a surface excludes):
// task tracking OFF (gear.js dressTracking greys seven judge rows and two Debug rows with rs-off, disables their controls, which
// the census skips, and puts the "Enable task tracking" title on the row, so a hover there shows a native title AND the row's
// description); a greyed Fast mode box (disabled, so no focus reaches it: its "why greyed" text is the pointer's alone); the
// panel as its own page (the four pane-toggle rows are hidden under the shell and the census skips them, so their descriptions
// are never read); the login modal (no focus trap: one Tab from the login button lands on the Pictures from the web textarea
// behind the modal and shows that row's description under the dim, upstream's modal from before this branch); and the widget
// rows' titled elements (grips, option wraps, demo spans: a native title beside the widget's description on hover). The house
// dropdowns (gear.js housePick, twelve pickers) WERE outside the legs too, since their rows never wear rs-picking; the
// house-dropdown leg below enters that state and records its reading. The legs read the PANEL, not the
// row: every `.rs-sub` under `#rsettings` that is shown,
// with the host that owns it, over every host in EVERY pane that has a description and a control of any kind (a checkbox, a
// button, a text field; the census form: a two-pane leg was a sample, and the two text controls and the Account row's two
// descriptions lived in the panes it did not open). The keyboard focus comes from a real Tab press (the previous tabbable
// focused, then Tab), the mouse from a real click, so the roads the selector distinguishes are the roads driven. Synthetic
// values only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { spawnSync } from "node:child_process";

const EXT = process.cwd();                                        // npm test runs in vscode-extension
const requireCjs = createRequire(path.join(EXT, "package.json"));
const UI = path.resolve(EXT, "..", "ui", "webview");
const GEAR = fs.readFileSync(path.join(UI, "gear.js"), "utf8");
const GEAR_CSS = fs.readFileSync(path.join(UI, "gear.css"), "utf8");

/** The sheet PARSED (the maintainer's round 5, ui-3 and tests-1): comments blanked as spans (spaces, so offsets hold), then every
 *  rule as its selector list (the arms split on the commas outside parentheses), its declaration block and its span in the
 *  stripped source, whatever lines the selector takes (gear.css writes three selectors over two lines, which a line-keyed read
 *  never saw); a conditional at-rule (@media) is descended and @keyframes is skipped whole (its blocks are keyframe selectors,
 *  not rules over elements). The pins below read rules, never lines; the degradation model below removes rules by span. */
interface CssRule { selector: string; arms: string[]; block: string; start: number; end: number }
const stripCssComments = (src: string) => src.replace(/\/\*[\s\S]*?\*\//g, (m) => " ".repeat(m.length));
function cssRules(src: string): CssRule[] {
  const out: CssRule[] = [];
  const walk = (from: number, to: number) => {
    let i = from;
    while (i < to) {
      const open = src.indexOf("{", i);
      if (open < 0 || open >= to) break;
      const prelude = src.slice(i, open), preludeT = prelude.trim();
      let depth = 1, j = open + 1;   // the matching close, counting nested braces (@media holds rules, @keyframes holds keyframe blocks)
      while (j < to && depth > 0) { if (src[j] === "{") depth++; else if (src[j] === "}") depth--; j++; }
      if (preludeT.startsWith("@keyframes")) { /* keyframe selectors, not rules over elements */ }
      else if (preludeT.startsWith("@")) walk(open + 1, j - 1);
      else if (preludeT) {
        const arms: string[] = []; let arm = "", paren = 0;
        for (const ch of preludeT) { if (ch === "(") paren++; else if (ch === ")") paren--; if (ch === "," && paren === 0) { arms.push(arm); arm = ""; } else arm += ch; }
        arms.push(arm);
        const norm = (s: string) => s.replace(/\s+/g, " ").trim();
        out.push({ selector: arms.map(norm).join(", "), arms: arms.map(norm), block: norm(src.slice(open + 1, j - 1)), start: i + prelude.search(/\S/), end: j });
      }
      i = j;
    }
  };
  walk(0, src.length);
  return out;
}
const GEAR_RULES = cssRules(stripCssComments(GEAR_CSS));
/** The sheet as an engine WITHOUT :has() applies it: every rule whose selector list carries :has() is gone whole (a selector the
 *  engine cannot parse invalidates the whole rule, whatever its other arms), the rest unchanged. The model the degradation leg
 *  drives in a real browser, since the three engines a developer's machine runs all support :has(). */
function withoutHas(css: string): string {
  const src = stripCssComments(css);
  const gone = cssRules(src).filter((r) => /:has\(/.test(r.selector));
  let out = src;
  for (const r of gone) out = out.slice(0, r.start) + " ".repeat(r.end - r.start) + out.slice(r.end);
  return out;
}

test("the sheet shows a description while its row holds a KEYBOARD focus: the show rule is TWO rules with one declaration block, the :hover arms and the :has(:focus-visible) arms, so an engine without :has() loses the keyboard road alone; the up rule and the Fast mode box's twins keyed the same way; no rule mixes a :has() arm with a plain arm and every :has() rule's loss is classified; no :focus-within left in any rule; one tooltip across the panel: the pointer wins", (t) => {
  assert.match(GEAR_CSS, /^#rsettings \.rs-row:hover \.rs-sub, #rsettings \.rs-widget:hover \.rs-sub \{ display: block; position: absolute;/m,
    "the show rule's pointer half: the row's and the widget's hover selectors in a rule of their own");
  assert.match(GEAR_CSS, /^#rsettings \.rs-row:has\(:focus-visible\) \.rs-sub, #rsettings \.rs-widget:has\(:focus-visible\) \.rs-sub \{ display: block; position: absolute;/m,
    "the show rule's keyboard half: the :has(:focus-visible) twins in a rule of their own (a mouse click is not :focus-visible, so a click shows nothing that outlives the pointer); an engine without :has() drops this rule alone and keeps the pointer's (the maintainer's round 5, ui-3: in one selector list the arms it could not parse took the whole rule, and no description showed on any road)");
  const showHover = GEAR_RULES.find((r) => r.selector === "#rsettings .rs-row:hover .rs-sub, #rsettings .rs-widget:hover .rs-sub");
  const showFocus = GEAR_RULES.find((r) => r.selector === "#rsettings .rs-row:has(:focus-visible) .rs-sub, #rsettings .rs-widget:has(:focus-visible) .rs-sub");
  assert.ok(showHover && showFocus, "the parsed sheet holds both halves of the show rule");
  assert.equal(showFocus!.block, showHover!.block, "one declaration block, spelled twice: the keyboard rule declares exactly what the pointer rule declares");
  assert.match(showHover!.block, /^display: block; position: absolute; left: 0; right: 0; top: 100%; z-index: 10;/);
  assert.match(GEAR_CSS, /^#rsettings \.rs-row\.rs-up:has\(:focus-visible\) \.rs-sub, #rsettings \.rs-widget\.rs-up:has\(:focus-visible\) \.rs-sub \{ top: auto; bottom: 100%; margin-top: 0; margin-bottom: 2px; \}/m,
    "the up rule's focus twin, the same declarations as the hover rule beside it");
  assert.match(GEAR_CSS, /^#rsettings \.rs-row:has\(:focus-visible\) \.rs-fastin \.rs-sub \{ display: none; \}/m,
    "the Fast mode box's description stands down while its row holds a keyboard focus (the :hover rule's twin), or a Tab into the box stacks two");
  assert.match(GEAR_CSS, /^#rsettings \.rs-row:has\(\.rs-fastin :focus-visible\) > \.rs-sub \{ display: none; \}\n#rsettings \.rs-row:has\(\.rs-fastin :focus-visible\) \.rs-fastin \.rs-sub \{ display: block; \}/m,
    "the box's hover pair's focus twins, in the descendant form (a :has() cannot nest a :has(), and the box is never the focused element): while a keyboard focus is inside the box the row's description stands down and the box's own shows");
  assert.match(GEAR_CSS, /^#rsettings \.rs-row:has\(:focus-visible\) \.rs-fastin\.rs-up \.rs-sub \{ top: auto; bottom: 100%; margin-top: 0; margin-bottom: 2px; \}/m,
    "the box's up rule's focus twin: a box wearing rs-up opens its description above the row on the keyboard as on hover");
  // the population is RULES, parsed (the maintainer's round 5, tests-1): a line-keyed read saw only the lines holding a brace, so a
  // selector spanning two lines escaped it, and gear.css writes that form (the panel-wide stand-down); comments are outside the
  // population by span, not by line prefix; the failure text names the offending rule
  assert.deepEqual(GEAR_RULES.filter((r) => /:focus-within/.test(r.selector)).map((r) => r.selector), [],
    "no rule keys on :focus-within any more: a mouse click satisfies it, and the description then outlives the pointer (the maintainer's round 4, ui-2)");
  assert.equal(GEAR_RULES.map((r) => r.selector).join("\n").match(/:focus-visible/g)!.length, 9,
    "nine :focus-visible tokens over the rules' selectors: the keyboard show rule's two, the up twin's two, the box's up twin, the box's stand-down twin, the pair's two twins, and the grip's own rule from before this road");
  // the rule walk (round 5, ui-3): a selector list is unforgiving, so no rule may mix a :has() arm with a :has()-free arm, or an
  // engine without :has() drops the plain arms with the rule (the show rule did, and nothing showed on any road there); the
  // failure text names the rule
  const mixed = GEAR_RULES.filter((r) => { const n = r.arms.filter((a) => /:has\(/.test(a)).length; return n > 0 && n < r.arms.length; });
  assert.deepEqual(mixed.map((r) => r.selector), [], "no rule's selector list mixes a :has() arm with a :has()-free arm (an engine without :has() drops the whole rule, the plain arms with it)");
  // and every :has() rule's loss on such an engine is named by its shape, never by a list: a STAND-DOWN (display: none: its loss
  // costs an extra tooltip, never a missing one), a KEYBOARD TWIN (every arm keyed on :focus-visible and a :focus-visible-free rule
  // with the same declarations standing: its loss costs the keyboard road alone), or the BOX's own pointer road (a :hover inside
  // the :has() argument selecting the box's description: the row is selected by its child's hover for the (1,5,0) that beats the
  // row-hover stand-down, the one pointer road this sheet cannot write without :has(), from before this branch; its loss shows
  // the row's description over a hovered box instead of the box's); any other :has() rule is unclassified and reds here until
  // its degradation is stated
  const hasRules = GEAR_RULES.filter((r) => /:has\(/.test(r.selector));
  const classOf = (r: CssRule) => /(^|; )display: none;?$/.test(r.block) || /(^|; )display: none;/.test(r.block) ? "stand-down"
    : r.arms.every((a) => /:focus-visible/.test(a)) && GEAR_RULES.some((o) => !/:focus-visible/.test(o.selector) && o.block === r.block) ? "keyboard twin"
    : r.arms.every((a) => /:has\([^)]*:hover\)/.test(a) && / \.rs-fastin \.rs-sub$/.test(a)) ? "the box's own pointer road"
    : "unclassified";
  const classes = hasRules.map((r) => ({ selector: r.selector, degradation: classOf(r) }));
  assert.ok(hasRules.length >= 12, "the rig: the sheet's :has() rules, twelve when this was written (" + hasRules.length + ")");
  assert.deepEqual(classes.filter((c) => c.degradation === "unclassified"), [], "every :has() rule's loss on an engine without :has() is a stand-down, a keyboard twin or the box's own pointer road");
  assert.ok(classes.some((c) => c.degradation === "keyboard twin") && classes.some((c) => c.degradation === "stand-down"), "the rig: both named shapes occur");
  t.diagnostic("the :has() rules by degradation: " + JSON.stringify(classes.reduce((m: Record<string, number>, c) => { m[c.degradation] = (m[c.degradation] || 0) + 1; return m; }, {})));
  const showTwin = "#rsettings .rs-row:has(.rs-fastin :focus-visible) .rs-fastin .rs-sub { display: block; }";
  const markStand = "#rsettings .rs-row:has(.rs-mixed:hover) .rs-fastin .rs-sub { display: none; }";
  assert.ok(GEAR_CSS.includes(markStand),
    "one tooltip on the keyboard too: the box's description stands down while a mark in its row is hovered, or a focus in the box and a pointer on the row's mark stack it with the mark's title");
  assert.ok(GEAR_CSS.indexOf(markStand) > GEAR_CSS.indexOf(showTwin),
    "and it follows the show twin: the two share a specificity, (1,5,0), so the order is the tie-break");
  // the panel-wide stand-down, read from the parsed sheet (its selector spans two lines): while a row SHOWING a description, a
  // widget row with one or any mixed mark is hovered, every description outside the hovered row stands down, the hovered row's
  // own exempt; a hovered row whose own description its open picker list stood down (rs-picking) has nothing to show and is
  // no trigger (the maintainer's round 5, correctness-1: keyed on the row CONTAINING a description, a list open under the
  // pointer and a keyboard focus in another row showed zero descriptions); a .rs-widget branch because the widget rows live
  // in their grids, not in a .rs-row
  const panelStand = GEAR_RULES.filter((r) => r.arms.every((a) => a.startsWith("#rsettings .rs-card:has(")));
  assert.equal(panelStand.length, 1, "one panel-wide stand-down rule");
  assert.deepEqual(panelStand[0].arms, [
    "#rsettings .rs-card:has(.rs-row:hover:not(.rs-picking) .rs-sub, .rs-widget:hover .rs-sub, .rs-mixed:hover) .rs-row:not(:hover) .rs-sub",
    "#rsettings .rs-card:has(.rs-row:hover:not(.rs-picking) .rs-sub, .rs-widget:hover .rs-sub, .rs-mixed:hover) .rs-widget:not(:hover) .rs-sub",
  ], "the trigger is a hovered row SHOWING a description (:not(.rs-picking): a row whose list is open shows none), a hovered widget row with one, or a hovered mark; the .rs-row and .rs-widget branches");
  assert.equal(panelStand[0].block, "display: none;");
  const pickerStand = GEAR_RULES.find((r) => r.selector === "#rsettings .rs-row.rs-picking .rs-sub");
  assert.ok(pickerStand && pickerStand.block === "display: none;", "the row's own description stands down while its picker list is open, keyed on the same class and never on a list's id (a new list picker joins by calling setListOpen; the house dropdowns do not call it and their rows never wear the class, the state the house-dropdown leg enters)");
  assert.equal(GEAR_RULES.filter((r) => /rs-cmap-list|rs-pal-list/.test(r.selector) && /rs-sub/.test(r.selector)).length, 0, "no description rule keys on a picker list's id any more");
  assert.match(GEAR_CSS, /THE\s+POINTER WINS wherever it has something to show/, "the precedence is stated in the sheet, not left to specificity");
  assert.match(GEAR_CSS, /within a row the box wins whenever either road rests on the\s+box, one description either way; across rows the pointer wins/,
    "the one exception to the pointer-wins rule is stated beside it: within a judge row the BOX's description shows with the focus inside the box and the pointer on the row's label (the census leg pins it)");
  assert.match(GEAR_CSS, /THE TEXT CONTROLS ARE THE ONE EXCEPTION to\s+"never a mouse click"/,
    "the show rule's comment names the exception to 'never a mouse click': a focus in a text field is always :focus-visible, so a click into the two text rows shows the description until the field blurs (the click leg pins it by control kind)");
});

test("placeSub runs on focusin as on mouseover, on the pointer road's host (the box for a focus inside a Fast mode box), and every handler re-places EVERY host of the row rather than one host, the exits never stripping the class", () => {
  assert.match(GEAR, /pcard\.addEventListener\('focusin', function \(e\) \{ var host = hostOf\(e\.target\); if \(host\) placeRowHosts\(host\); \}\);/,
    "the selector shows the popover; only placeSub measures and flips it above a row near the card's bottom; the host is hostOf's, as on mouseover, and the row's other hosts are re-placed with it (a focus arriving in the box from the row's picker button never left the row, so the row's class stayed and placed the box's popover)");
  assert.match(GEAR, /pcard\.addEventListener\('mouseover', function \(e\) \{ var host = hostOf\(e\.target\); if \(host\) placeRowHosts\(host\); \}\);/,
    "the pointer's enter re-places the row's hosts the same way");
  assert.match(GEAR, /pcard\.addEventListener\('focusout', function \(e\) \{ var host = hostOf\(e\.target\); if \(host && !\(e\.relatedTarget && host\.contains\(e\.relatedTarget\)\)\) placeRowHosts\(host\); \}\);/,
    "the focus road's exit re-places the row's hosts: a focus leaving a HOVERED row keeps the placement of the description the pointer still shows (round 4, correctness-2)");
  assert.match(GEAR, /pcard\.addEventListener\('mouseout', function \(e\) \{ var host = hostOf\(e\.target\); if \(host && !\(e\.relatedTarget && host\.contains\(e\.relatedTarget\)\)\) placeRowHosts\(host\); \}\);/,
    "the pointer road's exit re-places the row's hosts: a pointer leaving a row whose checkbox holds a keyboard focus keeps the placement of the description the focus still shows");
  assert.match(GEAR, /function placeRow\(row\) \{\s*\n\s*placeSub\(row\);\s*\n\s*var boxes = row\.querySelectorAll\('\.rs-fastin'\);\s*\n\s*for \(var i = 0; i < boxes\.length; i\+\+\) placeSub\(boxes\[i\]\);/,
    "the whole row and its Fast mode boxes: a focus moving from the row's picker button into its box never leaves the row, so the row's class stayed behind when the box's exit cleared the box's alone");
  assert.match(GEAR, /function placeRowHosts\(host\) \{\s*\n\s*var row = hostRow\(host\);\s*\n\s*placeRow\(row\);\s*\n\s*var focused = hostOf\(document\.activeElement\);\s*\n\s*if \(focused && hostRow\(focused\) !== row\) placeRow\(hostRow\(focused\)\);/,
    "and the row holding the keyboard focus, when it is another row: the panel-wide stand-down hides the focused row's description while the pointer rests on a row with one, so a focus that arrives there is left unplaced, and the pointer's exit must place it (the author's fixer pass after round 4, panel-1)");
  assert.doesNotMatch(GEAR, /host\.classList\.remove\('rs-up'\); \}\);/,
    "no exit handler strips the class unconditionally any more: placeSub drops it and re-adds it only while the host's own popover is shown and does not fit below");
  assert.doesNotMatch(GEAR, /focusHostOf/,
    "no climb from a Fast mode box to its row on the focus road: the sheet shows the box's own description on that focus (its hover pair's focus twins), so the box is the host on both roads and its popover has a height to place");
  // the picker lists' open state has ONE writer (the maintainer's round 5, correctness-1, the refuters' condition): the class the
  // sheet reads (rs-picking on the list's row) moves with the list's hidden in setListOpen and nowhere else, so no site that
  // opens or closes a list can leave the class behind; the census is derived from the source, never a list kept here
  assert.match(GEAR, /function setListOpen\(list, open\) \{ if \(!list\) return; list\.hidden = !open; var row = list\.closest\('\.rs-row'\); if \(row\) row\.classList\.toggle\('rs-picking', !!open\); \}/,
    "the one writer: the list's hidden and its row's rs-picking move together");
  assert.deepEqual(GEAR.match(/\b(cmList|plList)\.hidden\s*=/g) || [], [], "no site writes a picker list's hidden directly: every move goes through setListOpen");
  assert.equal((GEAR.match(/'rs-picking'/g) || []).length, 1, "the class literal is spelled once in gear.js, in the writer");
  const listOpenSites = GEAR.match(/setListOpen\((cmList|plList), [^)]*\)/g) || [];
  assert.equal(listOpenSites.length, 6, "every site that moves a list calls it: the button's toggle, the pick and the outside-click closer, for both pickers: " + listOpenSites.join(" | "));
  assert.deepEqual(listOpenSites.filter((s) => s.startsWith("setListOpen(cmList")).length, 3);
  assert.deepEqual(listOpenSites.filter((s) => s.startsWith("setListOpen(plList")).length, 3);
});

const ENTRY = `
const { initGear } = require("./gear.js");
(window as any).__posts = [];
initGear((m: any) => { (window as any).__posts.push(m); });
`;

function bundle(): string {
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    stdin: { contents: ENTRY, resolveDir: UI, loader: "ts", sourcefile: "gear-sub-focus-entry.ts" },
    bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], logLevel: "silent",
  });
  return r.outputFiles[0].text;
}

const pageHtml = (css: string) => `<!DOCTYPE html><html><head><meta charset=utf-8><style>${css}</style></head><body>
<script src=/dist/gear.js></script></body></html>`;
const MODELS = { models: [{ value: "opus", label: "Opus", versions: [] }, { value: "sonnet", label: "Sonnet", versions: [] }], efforts: [{ value: "", label: "Default" }] };
const VERSION = { judgeModel: "opus", judgeEffort: "", indexModel: "opus", indexEffort: "", distillModel: "triage", distillEffort: "triage",
  judgeConcurrency: "", commentModel: "session", commentEffort: "session", commentFast: "session",
  judgeFast: "on", distillFast: "on", indexFast: "on", fastRefused: {}, autoNudge: true, settingsGt: {}, updateMode: "off" };

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }
// ROMP_GEAR_BROWSER_REQUIRE (CI's step after the Chromium install sets it) turns the browser legs' skip into a failure naming
// the reason: the one CI run of these legs must not read green on a runner that lost its browser
const required = !!process.env.ROMP_GEAR_BROWSER_REQUIRE;
const skipOrFail = (t: any, why: string) => {
  if (required) assert.fail("ROMP_GEAR_BROWSER_REQUIRE is set and this leg cannot run: " + why);
  t.skip(why + " (in CI the Test step runs before the job installs Chromium, so the browser legs skip there and run in the step after the install)");
};

async function withGear(t: any, tab: string, body: (page: any, errors: string[]) => Promise<void>, height = 320, ctxOpts: Record<string, unknown> = {}, css = GEAR_CSS): Promise<void> {
  if (!pw) { skipOrFail(t, "playwright is not installed under vscode-extension; the browser legs need it"); return; }
  let browser: any;
  try { browser = await pw.chromium.launch(); }
  catch (e) { skipOrFail(t, "no playwright browser on this machine; the browser legs need one: " + String((e as Error).message).split("\n")[0]); return; }
  const errors: string[] = [];
  try {
    const js = bundle();
    // a short window: the card (max-height 88vh) is shorter than the Debug pane, so the card scrolls, and the share row sits
    // low enough in it at scrollTop 0 that a popover below would run past the card (the T408 clip placeSub exists for) and
    // high enough at the card's end that one fits (the rig asserts both readings before it reads placeSub's answer)
    const ctx = await browser.newContext({ viewport: { width: 1000, height }, ...ctxOpts });
    const page = await ctx.newPage();
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    await page.route("**/*", (route: any) => {
      const u = new URL(route.request().url());
      const json = (o: unknown) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(o) });
      if (u.hostname !== "romp.test") return route.fulfill({ status: 404, body: "" });
      if (u.pathname === "/gear") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: pageHtml(css) });
      if (u.pathname === "/dist/gear.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: js });
      if (u.pathname === "/models") return json(MODELS);
      if (u.pathname === "/version") return json(VERSION);
      if (u.pathname === "/tunnels") return json({ tunnels: [] });
      return json({});
    });
    await page.goto("http://romp.test/gear");
    await page.waitForFunction(() => Array.isArray((window as any).__posts) && !!document.getElementById("rs-perfshare"), null, { timeout: 10000 });
    await page.evaluate((tb: string) => { window.postMessage({ romp: "openSettings", tab: tb }, "*"); }, tab);
    await page.waitForFunction(() => !(document.getElementById("rsettings") as HTMLElement).hidden, null, { timeout: 10000 });
    if (tab === "tasks") await page.waitForFunction(() => (document.getElementById("rs-judgefast") as HTMLInputElement).checked === true, null, { timeout: 10000 });
    await body(page, errors);
  } finally {
    await browser.close();
  }
}

/** A REAL keyboard focus on the control `id`: the tabbable before it in the panel is focused without a scroll, then one Tab
 *  press moves the focus the way a keyboard user's does (Chromium matches :focus-visible on a Tab and not on a mouse click,
 *  the distinction the sheet keys on; a programmatic .focus() matches it or not by the browser's reading of the last
 *  interaction, so the legs never rely on one). Returns what the rig needs to trust the focus before reading anything. */
async function tabInto(page: any, id: string): Promise<{ landed: boolean; focusVisible: boolean; prev: string | null }> {
  const prev = await page.evaluate((cid: string) => {
    const target = document.getElementById(cid)!;
    const all = Array.from(document.querySelectorAll("#rsettings input, #rsettings button, #rsettings select, #rsettings textarea, #rsettings a[href], #rsettings [tabindex]")) as HTMLElement[];
    const tabbable = all.filter((el) => el.tabIndex >= 0 && !(el as HTMLInputElement).disabled && el.checkVisibility());
    const i = tabbable.indexOf(target);
    if (i <= 0) return null;
    const p = tabbable[i - 1];
    p.focus({ preventScroll: true });
    return p.id || p.tagName + "." + p.className;
  }, id);
  await page.keyboard.press("Tab");
  const r = await page.evaluate((cid: string) => {
    const el = document.getElementById(cid)!;
    return { landed: document.activeElement === el, focusVisible: el.matches(":focus-visible") };
  }, id);
  return { ...r, prev };
}

/** Everything shown in the PANEL: each shown `.rs-sub` with the id of the host that owns it (the box's wrap id for a Fast mode
 *  box, the first control's id for a row, the widget id for a widget row), whether any two shown rects of DIFFERENT hosts
 *  intersect (`intersect`) and whether two of one host do (`intersectWithin`: the Account row's two, see the census leg), the
 *  focused control and its :focus-visible, every host wearing the placement class, and the count of open menus (a picker's
 *  list, a house dropdown, the login modal), so a leg can read that a click left none behind. A house dropdown is told by its
 *  COMPUTED position (the maintainer's round 5, the fixer pass, exclusions-3): housePick writes its menu's style through
 *  cssText, which the browser serialises with a space after each colon, so a selector on the attribute's text
 *  (`div[style*='position:absolute']`) matched no row menu and read "nothing left open" over an open judge picker, while
 *  `.rs-widget-opt div` counted a widget option's menu with its option rows; menus are counted, never their rows (the option
 *  rows are positioned relative) and never a description (a shown `.rs-sub` is positioned absolutely too, and the Account row's
 *  second one is a div: excluded by class). */
const shownPanel = (page: any) => page.evaluate(() => {
  const HOSTS = "#rsettings .rs-fastin, #rsettings .rs-row, #rsettings .rs-widget";
  const hostId = (h: HTMLElement | null) => {
    if (!h) return "?";
    if (h.classList.contains("rs-fastin")) return h.id;
    if (h.classList.contains("rs-widget")) return "widget:" + h.getAttribute("data-widget");
    // the row's first focusable control, the census's rule (a picker row holds a hidden <select> before its button)
    const c = (Array.from(h.querySelectorAll("input, button, textarea, select")) as HTMLElement[]).find((el) => el.closest(HOSTS) === h && el.tabIndex >= 0 && !(el as HTMLInputElement).disabled && el.checkVisibility());
    return c ? c.id : h.className;
  };
  const shown = (Array.from(document.querySelectorAll("#rsettings .rs-sub")) as HTMLElement[]).filter((el) => getComputedStyle(el).display !== "none");
  const rects = shown.map((el) => el.getBoundingClientRect());
  const owners = shown.map((el) => el.closest(HOSTS));
  let intersect = false, intersectWithin = false;
  for (let i = 0; i < rects.length; i++) for (let j = i + 1; j < rects.length; j++) {
    const a = rects[i], b = rects[j];
    if (a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom) { if (owners[i] === owners[j]) intersectWithin = true; else intersect = true; }
  }
  const act = document.activeElement as HTMLElement | null;
  const lm = document.getElementById("rs-login-modal");
  const menus = (Array.from(document.querySelectorAll("#rsettings .rs-row div:not(.rs-sub), #rsettings .rs-widget-opt div, #rs-cmap-list, #rs-pal-list")) as HTMLElement[])
    .filter((m) => getComputedStyle(m).position === "absolute" && !m.hidden && getComputedStyle(m).display !== "none" && m.getBoundingClientRect().height > 0).length + (lm && !lm.hidden ? 1 : 0);
  return { shown: shown.map((el) => hostId(el.closest(HOSTS) as HTMLElement | null)), intersect, intersectWithin, menus,
    active: act && act !== document.body ? (act.id || act.tagName + "." + act.className) : null,
    focusVisible: act && act !== document.body ? act.matches(":focus-visible") : null,
    up: (Array.from(document.querySelectorAll("#rsettings .rs-up")) as HTMLElement[]).map((h) => hostId(h)) };
});

/** Scroll the card (the modal's scroll box) so the row that owns `id` sits as LOW as the card allows ("bottom": scrollTop 0),
 *  as HIGH as it allows ("top": the card's end), or just above the card's bottom edge wherever the row is in the card ("low":
 *  the scroll that puts the row's bottom 4 px above the card's), Tab into the control (a real keyboard focus; the control is
 *  inside the card's visible box at every edge, so the Tab scrolls nothing, which the rig reads back), and read what the
 *  sheet and placeSub did. The HOST is gear.js's hostOf rule (the closest of a Fast mode box, a row or a widget row), so
 *  `own` is the box's description for a control inside a box and the row's otherwise, and `up` is the class on that host.
 *  The short window makes the positions differ in whether a popover below the row fits inside the card (fitsBelow), which
 *  is the one thing placeSub decides on. */
async function focusParked(page: any, id: string, edge: "bottom" | "top" | "low") {
  const scroll0 = await page.evaluate(([cid, where]: [string, string]) => {
    const box = document.getElementById(cid) as HTMLInputElement;
    const row = box.closest("#rsettings .rs-row") as HTMLElement;
    const card = document.querySelector("#rsettings .rs-card") as HTMLElement;
    const host = box.closest("#rsettings .rs-fastin, #rsettings .rs-row, #rsettings .rs-widget") as HTMLElement;
    (document.activeElement as HTMLElement | null)?.blur?.();
    row.classList.remove("rs-up"); host.classList.remove("rs-up");
    card.scrollTop = where === "top" ? card.scrollHeight : 0;
    if (where === "low") {
      const rr0 = row.getBoundingClientRect(), cr0 = card.getBoundingClientRect();
      card.scrollTop = Math.max(0, (rr0.top - cr0.top) - (cr0.height - rr0.height - 4));
    }
    return card.scrollTop;
  }, [id, edge]);
  const tab = await tabInto(page, id);
  const r = await page.evaluate(([cid, s0]: [string, number]) => {
    const box = document.getElementById(cid) as HTMLInputElement;
    const row = box.closest("#rsettings .rs-row") as HTMLElement;
    const card = document.querySelector("#rsettings .rs-card") as HTMLElement;
    const host = box.closest("#rsettings .rs-fastin, #rsettings .rs-row, #rsettings .rs-widget") as HTMLElement;
    const subs = Array.from(row.querySelectorAll(".rs-sub")) as HTMLElement[];
    const hostOfSub = (el: HTMLElement) => el.closest("#rsettings .rs-fastin, #rsettings .rs-row, #rsettings .rs-widget");
    const own = subs.find((el) => hostOfSub(el) === host)!;
    const rowOwn = subs.find((el) => hostOfSub(el) === row)!;
    const sr = own.getBoundingClientRect(), cr = card.getBoundingClientRect(), rr = row.getBoundingClientRect();
    return {
      geom: { row: [rr.top, rr.bottom], card: [cr.top, cr.bottom], sub: [sr.top, sr.bottom, sr.height], scroll: [card.scrollTop, card.scrollHeight, card.clientHeight] },
      scrolledByTab: card.scrollTop !== s0,
      focused: document.activeElement === box,
      hostIsBox: host !== row && host.classList.contains("rs-fastin"),
      display: getComputedStyle(own).display,
      rowDisplay: getComputedStyle(rowOwn).display,
      text: own.textContent || "",
      up: host.classList.contains("rs-up"),
      rowUp: row.classList.contains("rs-up"),
      shownInRow: subs.filter((el) => getComputedStyle(el).display !== "none").length,
      // the popover's own bottom against the card's, as placeSub measured it: above the row when rs-up placed it, else below
      subBelowRow: sr.top >= rr.bottom - 1, subAboveRow: sr.bottom <= rr.top + 1,
      fitsBelow: rr.bottom + sr.height + 2 <= cr.bottom,
    };
  }, [id, scroll0]);
  return { ...r, tab };
}

test("the share switch's description opens on a keyboard focus and is placed: at the card's bottom edge it opens above the row (rs-up), at the top edge below it, and it carries the per-machine sentence", { timeout: 90000 }, async (t) => {
  await withGear(t, "debug", async (page, errors) => {
    const low = await focusParked(page, "rs-perfshare", "bottom");
    assert.equal(low.tab.landed, true, "the rig: one Tab from the tabbable before it landed on the checkbox (from " + low.tab.prev + ")");
    assert.equal(low.tab.focusVisible, true, "the rig: a Tab is a :focus-visible focus");
    assert.equal(low.scrolledByTab, false, "the rig: the Tab scrolled nothing, so the geometry read is the one the focus met " + JSON.stringify(low.geom));
    assert.equal(low.focused, true, "the checkbox took the focus");
    assert.equal(low.display, "block", "the description is shown while the row holds a keyboard focus (it rendered for a pointer alone before)");
    assert.match(low.text, /once per attached machine, by position rather than by name/, "the per-machine socket-byte sentence is in the shown text");
    assert.match(low.text, /Numbers and fixed names only, never text\./);
    assert.equal(low.fitsBelow, false, "the rig: with the row as low as the card allows, a popover below it would run past the card " + JSON.stringify(low.geom));
    assert.equal(low.up, true, "placeSub ran on the focus and flipped it above (the selector alone would leave it clipped below)");
    assert.equal(low.subAboveRow, true, "and the sheet placed it above the row");
    // the class goes with the focus: blur, and the next focus measures afresh
    await page.evaluate(() => (document.activeElement as HTMLElement).blur());
    assert.equal(await page.evaluate(() => (document.getElementById("rs-perfshare") as HTMLElement).closest(".rs-row")!.classList.contains("rs-up")), false, "focusout with nothing shown drops the class");
    const high = await focusParked(page, "rs-perfshare", "top");
    assert.equal(high.tab.landed && high.tab.focusVisible, true, "the rig: a keyboard focus again");
    assert.equal(high.display, "block");
    assert.equal(high.fitsBelow, true, "the rig: with the row as high as the card allows, a popover below it fits " + JSON.stringify(high.geom));
    assert.equal(high.up, false, "so placeSub leaves the default");
    assert.equal(high.subBelowRow, true, "and it shows below the row");
    assert.deepEqual(errors, [], "no page error");
  });
});

test("ROMP_GEAR_BROWSER_REQUIRE turns the browser legs' skip into a failure that names the reason, and without it the skip stands: CI's step after the Chromium install sets it", { timeout: 120000 }, () => {
  // a child run of this file's share-switch leg with playwright pointed at an empty browsers directory (the pane bench's probe):
  // under the switch the leg fails naming the switch and the reason; without it the leg skips, as the Test step's run does
  const empty = fs.mkdtempSync(path.join(EXT, "out-tests", "no-browsers-"));
  try {
    // the child's environment is built, not inherited: under `node --test` this process carries the runner's NODE_TEST_CONTEXT,
    // and a child inheriting it reports on the runner's channel instead of its stdout
    const base: Record<string, string> = {};
    for (const k of ["PATH", "HOME", "TMPDIR", "NODE_OPTIONS"]) if (process.env[k] !== undefined) base[k] = process.env[k] as string;
    const run = (env: Record<string, string>) => spawnSync(process.execPath, ["--test", "--test-name-pattern=share switch", __filename],
      { cwd: EXT, encoding: "utf8", timeout: 100000, env: { ...base, ...env, PLAYWRIGHT_BROWSERS_PATH: empty } });
    const req = run({ ROMP_GEAR_BROWSER_REQUIRE: "1" });
    assert.match(req.stdout, /ROMP_GEAR_BROWSER_REQUIRE is set and this leg cannot run: no playwright browser/, "the switch: a failure naming it and the reason\n" + req.stdout.slice(-1500));
    assert.match(req.stdout, /^# fail 1$/m, "the leg failed under the switch");
    const plain = run({});
    assert.match(plain.stdout, /^# skipped 1$/m, "without the switch the leg skips\n" + plain.stdout.slice(-1500));
    assert.match(plain.stdout, /the Test step runs before the job installs Chromium/, "and the skip's reason states the step order");
  } finally {
    fs.rmSync(empty, { recursive: true, force: true });
  }
});

test("the degradation on an engine without :has(), modelled: with every :has() rule removed from the sheet (such an engine drops a rule it cannot parse whole) a hover still shows the row's description and a keyboard focus shows nothing, the keyboard road alone lost; before the split of the show rule nothing showed on either road", { timeout: 90000 }, async (t) => {
  // the surface the three-engine matrix excludes (the maintainer's round 5, ui-3): Chromium 151, Firefox 153 and WebKit 26.5 all
  // parse :has(), so the engine without it is modelled, not installed: the sheet an engine without :has() applies is this sheet
  // less every rule whose selector list carries it, driven in the browser at hand
  const noHas = withoutHas(GEAR_CSS);
  const kept = cssRules(noHas);
  assert.equal(kept.filter((r) => /:has\(/.test(r.selector)).length, 0, "the rig: no :has() rule survives the model");
  assert.equal(GEAR_RULES.length - kept.length, GEAR_RULES.filter((r) => /:has\(/.test(r.selector)).length, "the rig: exactly the :has() rules are gone, every other rule stands");
  await withGear(t, "debug", async (page, errors) => {
    const read = () => page.evaluate(() => {
      const box = document.getElementById("rs-perfshare")!, row = box.closest("#rsettings .rs-row") as HTMLElement, sub = row.querySelector(".rs-sub") as HTMLElement;
      return { hovered: row.matches(":hover"), focused: document.activeElement === box, display: getComputedStyle(sub).display };
    });
    await hoverOn(page, "#rsettings .rs-row:has(#rs-perfshare) b");
    const on = await read();
    assert.equal(on.hovered, true, "the rig: the pointer is on the share row");
    assert.equal(on.display, "block", "the pointer road survives the loss of :has(): a hover shows the row's description (before the split the four-arm show rule was dropped whole and this read none)");
    assert.deepEqual((await shownPanel(page)).shown, ["rs-perfshare"], "the hovered row's description, alone");
    await page.mouse.move(5, 5);
    assert.equal((await read()).display, "none", "the rig: the pointer gone, nothing shows");
    const tab = await tabInto(page, "rs-perfshare");
    assert.equal(tab.landed && tab.focusVisible, true, "the rig: a real keyboard focus in the row");
    assert.equal((await read()).display, "none", "the keyboard road is what such an engine loses: the focus rule is gone with its :has(), and the description stays hidden (the degradation the sheet had before the keyboard road, stated in the sheet beside the two rules)");
    assert.deepEqual(errors, [], "no page error");
  }, 320, {}, noHas);
  // the mechanism behind the reading: the pointer half is a rule of its own and holds no :has(), so the model keeps it
  assert.ok(kept.some((r) => r.selector === "#rsettings .rs-row:hover .rs-sub, #rsettings .rs-widget:hover .rs-sub"), "the show rule's pointer half stands in the model (it holds no :has())");
});

test("a Tab into a Fast mode box shows one description in its row, the BOX's own, the row's standing down, as a hover on the box does", { timeout: 90000 }, async (t) => {
  await withGear(t, "tasks", async (page, errors) => {
    const r = await focusParked(page, "rs-judgefast", "top");
    assert.equal(r.tab.landed && r.tab.focusVisible, true, "the rig: a Tab landed on the box's checkbox (from " + r.tab.prev + ")");
    assert.equal(r.focused, true);
    assert.equal(r.hostIsBox, true, "the rig: the host of a focus inside the box is the box (hostOf's rule)");
    assert.equal(r.shownInRow, 1, "one description shown in the row while the box holds the focus");
    assert.equal(r.display, "block", "the box's own: what a pointer reads on the box, a keyboard reads on its checkbox");
    assert.match(r.text, /fast mode \(an Opus-only research preview/, "and it is the Fast mode text, not the row's");
    assert.equal(r.rowDisplay, "none", "the row's stands down, as it does while the box is hovered");
    assert.equal(await page.evaluate(() => getComputedStyle(document.getElementById("rs-judgefast-sub")!).display), "block");
    assert.deepEqual(errors, [], "no page error");
  });
});

test("a Tab into a Fast mode box with its row just above the card's bottom places the BOX's description above the row: placeSub runs on the box, the host whose popover the sheet shows, and the box's up rule's focus twin opens it above", { timeout: 90000 }, async (t) => {
  await withGear(t, "tasks", async (page, errors) => {
    const r = await focusParked(page, "rs-judgefast", "low");
    assert.equal(r.tab.landed && r.tab.focusVisible, true, "the rig: a Tab landed on the box's checkbox");
    assert.equal(r.scrolledByTab, false, "the rig: the Tab scrolled nothing " + JSON.stringify(r.geom));
    assert.equal(r.focused, true, "the box's checkbox took the focus");
    assert.equal(r.hostIsBox, true, "the rig: the host is the box");
    assert.equal(r.fitsBelow, false, "the rig: with the row just above the card's bottom in a 260 px window, a popover below it would run past the card " + JSON.stringify(r.geom));
    assert.equal(r.shownInRow, 1, "one description shown in the row, the box's");
    assert.equal(r.display, "block", "the box's own is the shown one");
    assert.equal(r.up, true, "the BOX wears rs-up: placeSub measured the box's popover, the one the sheet shows on this focus (a climb to the row would measure the row's, hidden, and place nothing)");
    assert.equal(r.rowUp, false, "and the row was not placed: the focus road's host is the pointer road's");
    assert.equal(r.subAboveRow, true, "and the sheet opened the box's description above the row (the box's up rule's focus twin; the box is static, so the row is its containing block)");
    await page.evaluate(() => (document.activeElement as HTMLElement).blur());
    assert.equal(await page.evaluate(() => (document.getElementById("rs-judgefast") as HTMLElement).closest(".rs-fastin")!.classList.contains("rs-up")), false, "focusout with nothing shown drops the class from the box");
    assert.deepEqual(errors, [], "no page error");
  }, 260);
});

test("a pointer parked on the row's mixed mark while the focus is inside a Fast mode box: the box's description stands down, so the mark's native title is the one tooltip, and it shows again once the pointer leaves", { timeout: 90000 }, async (t) => {
  await withGear(t, "tasks", async (page, errors) => {
    const r0 = await focusParked(page, "rs-judgefast", "top");
    assert.equal(r0.tab.landed && r0.tab.focusVisible, true, "the rig: a Tab landed on the box's checkbox");
    assert.equal(r0.display, "block", "the rig: the box's description is shown on the focus before any mark is shown or hovered");
    // the row's mark, shown as fillMixedMarks shows it when the attached machines differ (a synthetic title; the mark rules key
    // on the mark's hover, not its text); shown AFTER the focus, so a rule keyed on the mark's presence rather than its hover
    // would pass the stand-down below and fail the restore
    await page.evaluate(() => {
      const row = document.getElementById("rs-judgefast")!.closest("#rsettings .rs-row")!;
      const mark = row.querySelector("b .rs-mixed") as HTMLElement;
      mark.hidden = false; mark.textContent = "mixed"; mark.title = "differs on: TESTHOST";
    });
    const read = () => page.evaluate(() => {
      const box = document.getElementById("rs-judgefast")!, row = box.closest("#rsettings .rs-row")!;
      const subs = Array.from(row.querySelectorAll(".rs-sub")) as HTMLElement[];
      const mark = row.querySelector("b .rs-mixed") as HTMLElement;
      return { markHovered: mark.matches(":hover"), focused: document.activeElement === box,
        boxDisplay: getComputedStyle(document.getElementById("rs-judgefast-sub")!).display,
        shownInRow: subs.filter((el) => getComputedStyle(el).display !== "none").length };
    });
    const mark = await page.evaluateHandle(() => document.getElementById("rs-judgefast")!.closest("#rsettings .rs-row")!.querySelector("b .rs-mixed"));
    await mark.asElement().hover();
    const on = await read();
    assert.equal(on.markHovered, true, "the rig: the pointer is on the row's mark");
    assert.equal(on.focused, true, "and the focus stayed in the box");
    assert.equal(on.boxDisplay, "none", "the box's description stands down while the mark is hovered, as the row's does: the mark's title is the one tooltip");
    assert.equal(on.shownInRow, 0, "no description shown in the row beside the title");
    assert.deepEqual((await shownPanel(page)).shown, [], "and none anywhere in the panel");
    await page.mouse.move(5, 5);
    const off = await read();
    assert.equal(off.markHovered, false, "the rig: the pointer left the mark");
    assert.equal(off.focused, true, "and the focus is still in the box");
    assert.equal(off.boxDisplay, "block", "so the box's description shows again on the focus alone: the stand-down is the pointer's");
    assert.equal(off.shownInRow, 1, "one description in the row, the box's");
    assert.deepEqual(errors, [], "no page error");
  });
});

/** The census of the open pane: every host (a row, a widget row, a Fast mode box) that owns a description and has a visible
 *  control to focus or click, EVERY such control with its kind (a checkbox, a button, a text field; a select or another tag
 *  reads "other", which the click leg refuses until classified), each control given an id when it has none (the picker
 *  buttons), a hover target (the label for a row, the box itself for a box), and the count of descriptions the host owns (one
 *  for every host but the Account row, whose stored-logins heading is a second `.rs-sub`: the census leg names it). */
const census = (page: any) => page.evaluate(() => {
  const HOSTS = "#rsettings .rs-fastin, #rsettings .rs-row, #rsettings .rs-widget";
  const pane = document.querySelector("#rsettings .rs-pane:not([hidden])")!;
  const kindOf = (c: HTMLElement) => {
    if (c.tagName === "TEXTAREA") return "text";
    if (c.tagName === "BUTTON") return "button";
    if (c.tagName === "INPUT") { const t = ((c as HTMLInputElement).type || "text").toLowerCase(); return t === "checkbox" || t === "radio" ? "checkbox" : ["text", "search", "url", "email", "password", "number", "tel"].includes(t) ? "text" : "other"; }
    return "other";
  };
  const out: { host: string; control: string; kind: string; tag: string; controls: { id: string; kind: string; tag: string }[]; hoverSel: string; row: string; box: boolean; hasMark: boolean; subs: number }[] = [];
  let n = 0;
  for (const h of Array.from(pane.querySelectorAll(".rs-row, .rs-widget, .rs-fastin")) as HTMLElement[]) {
    if (!h.checkVisibility()) continue;
    const owned = (Array.from(h.querySelectorAll(".rs-sub")) as HTMLElement[]).filter((sub) => sub.closest(HOSTS) === h);
    if (!owned.length) continue;
    const controls = (Array.from(h.querySelectorAll("input, button, textarea, select")) as HTMLElement[]).filter((c) => c.closest(HOSTS) === h && c.tabIndex >= 0 && !(c as HTMLInputElement).disabled && c.checkVisibility());
    if (!controls.length) continue;
    for (const c of controls) if (!c.id) c.id = "probe-control-" + (n++);
    if (!h.id) h.setAttribute("data-probe", "probe-host-" + (n++));
    const hostSel = h.id ? "#" + h.id : `[data-probe="${h.getAttribute("data-probe")}"]`;
    const box = h.classList.contains("rs-fastin");
    const row = (box ? h.closest("#rsettings .rs-row")! : h) as HTMLElement;
    if (!row.id && !row.getAttribute("data-probe")) row.setAttribute("data-probe", "probe-host-" + (n++));
    const hoverSel = box ? hostSel : hostSel + " b";
    const hostId = box ? h.id : h.classList.contains("rs-widget") ? "widget:" + h.getAttribute("data-widget") : controls[0].id;
    out.push({ host: hostId, control: controls[0].id, kind: kindOf(controls[0]), tag: controls[0].tagName,
      controls: controls.map((c) => ({ id: c.id, kind: kindOf(c), tag: c.tagName })), hoverSel,
      row: row.id || row.getAttribute("data-probe")!, box, hasMark: !box && !!row.querySelector("b .rs-mixed, .rs-mixed"), subs: owned.length });
  }
  return out;
});

const hoverOn = async (page: any, sel: string) => {
  await page.evaluate((s: string) => document.querySelector(s)!.scrollIntoView({ block: "nearest" }), sel);
  const b = await page.locator(sel).first().boundingBox();
  await page.mouse.move(b.x + b.width / 2, b.y + b.height / 2);
};

/** The hosts with something shown, each once: the panel's one-tooltip rule is over HOSTS, whatever number of descriptions a host
 *  owns (the Account row owns two, a synthetic doubled row two), so the pins compare host sets and never counts (the maintainer's
 *  round 5 on panel-3: the count pin named the doubled host by id and its count, and a second doubled row anywhere would have
 *  red it; the invariant holds over however many hosts a row carries and however many descriptions a host owns). */
const hostsShown = (r: { shown: string[] }) => Array.from(new Set(r.shown));

/** A second host owning TWO descriptions, the Account row's shape (a row whose `.rs-sub` count is two), inserted after the open
 *  pane's first direct-child row: the construction the ruling said the round would make. The census reads it like any row (its
 *  host id is its checkbox's), so the count pin this replaced reds on it and the invariant must not. Synthetic text only. */
async function injectDoubledRow(page: any): Promise<void> {
  await page.evaluate(() => {
    const pane = document.querySelector("#rsettings .rs-pane:not([hidden])") as HTMLElement;
    const rows = (Array.from(pane.querySelectorAll(".rs-row")) as HTMLElement[]).filter((r) => r.parentElement === pane);
    const lab = document.createElement("label"); lab.className = "rs-row";
    lab.innerHTML = "<input type=checkbox id=probe-synth-box><span><b>Synthetic doubled row <span class=rs-mixed hidden></span></b>"
      + "<span class=rs-sub>Synthetic description one, a probe row on TESTHOST.</span>"
      + "<span class=rs-sub>Synthetic description two, the second popover of the same row.</span></span>";
    if (rows.length) rows[0].parentNode!.insertBefore(lab, rows[0].nextSibling); else pane.appendChild(lab);
  });
}

/** The pane's populations, DERIVED (the maintainer's round 5, correctness-3 and ui-2: the body had quoted 52 hosts and 63 controls,
 *  a count of what the census skips): every description in the open pane is either a census host's (a visible host owning it with
 *  a visible, enabled, focusable control) or excluded for a stated reason (no host; a hidden host, the four pane-toggle rows when
 *  the panel is not its own page; a host with no focusable control, the Updates row whose select is display:none), else `missed`,
 *  so a description the census silently misses fails the leg rather than shrinking the matrix. Beside the census figures the
 *  WIDER population is derived too: every description-owning host and every control it owns, visible or not, the reading the
 *  body's earlier figure counted; both are printed per pane so the body's figures are re-derived from the log, never by hand. */
const populations = (page: any, known: string[]) => page.evaluate((ids: string[]) => {
  const HOSTS = "#rsettings .rs-fastin, #rsettings .rs-row, #rsettings .rs-widget";
  const pane = document.querySelector("#rsettings .rs-pane:not([hidden])")!;
  const out = { descriptions: 0, covered: 0, excluded: [] as string[], missed: [] as string[], describedHosts: 0, describedControls: 0 };
  const idOf = (h: HTMLElement, controls: HTMLElement[]) => h.classList.contains("rs-fastin") ? h.id : h.classList.contains("rs-widget") ? "widget:" + h.getAttribute("data-widget") : (controls[0] && controls[0].id) || h.className;
  for (const h of Array.from(pane.querySelectorAll(".rs-row, .rs-widget, .rs-fastin")) as HTMLElement[]) {
    const owned = (Array.from(h.querySelectorAll(".rs-sub")) as HTMLElement[]).filter((s) => s.closest(HOSTS) === h);
    if (!owned.length) continue;
    out.describedHosts++;
    out.describedControls += (Array.from(h.querySelectorAll("input, button, textarea, select")) as HTMLElement[]).filter((c) => c.closest(HOSTS) === h).length;
  }
  for (const sub of Array.from(pane.querySelectorAll(".rs-sub")) as HTMLElement[]) {
    out.descriptions++;
    const h = sub.closest(HOSTS) as HTMLElement | null;
    const text = (sub.textContent || "").slice(0, 30);
    if (!h) { out.excluded.push("no host: " + text); continue; }
    if (!h.checkVisibility()) { out.excluded.push("hidden host: " + text); continue; }
    const controls = (Array.from(h.querySelectorAll("input, button, textarea, select")) as HTMLElement[]).filter((c) => c.closest(HOSTS) === h && c.tabIndex >= 0 && !(c as HTMLInputElement).disabled && c.checkVisibility());
    if (!controls.length) { out.excluded.push("no control: " + text); continue; }
    const id = idOf(h, controls);
    if (ids.includes(id)) out.covered++; else out.missed.push(id + ": " + text);
  }
  return out;
}, known);

/** Every pane, with the floor of hosts the census form found there when the leg was written (a census that finds fewer checked
 *  less than this leg did; the Automation pane's rows carry permanent lines, not descriptions, and have none). */
const PANES: ReadonlyArray<readonly [string, string, number]> = [["general", "General", 8], ["chat", "Chat", 21], ["feed", "Feed", 1], ["sessions", "Sessions", 2],
  ["automation", "Automation", 0], ["tasks", "Task tracking", 11], ["debug", "Debug", 4]];

/** The General pane fills the Account row's stored-logins block from the fake kernel's /logins after the open: wait for it, so
 *  the census reads the row as a user sees it. */
async function settled(page: any, tab: string): Promise<void> {
  if (tab === "general") await page.waitForFunction(() => !!document.querySelector("#rs-logins > *"), null, { timeout: 10000 });
}

/** Close whatever a button's click opened: the login modal (its Cancel), a house dropdown (Escape closes it; the page's own
 *  Escape handlers close a dialog one level at a time and never the panel), or a colormap or palette list (its button toggles
 *  it, so a second click closes it, as the earlier two-pane leg did). */
async function settleAfterClick(page: any, id: string): Promise<void> {
  await page.evaluate(() => { const lm = document.getElementById("rs-login-modal"); if (lm && !lm.hidden) (document.getElementById("rs-login-cancel") as HTMLElement).click(); });
  await page.keyboard.press("Escape");
  if ((await shownPanel(page)).menus > 0) await page.click(`#${id}`);
  await page.mouse.move(5, 5);
}

/** The one-tooltip matrix over the census `hosts` of the open pane, the INVARIANT and not a count (the maintainer's round 5 on
 *  panel-3, and its C: correctness-4, tests-2, regression-3, ui-1, extra6-2, extra9-2): a keyboard focus in each host shows that
 *  host's description alone; the pointer on every OTHER host shows that host's alone (the pointer wins), the BOX's within a row
 *  whichever road rests on it; the pointer on nothing shows the focused one; a hovered mark on another row shows none. Every pin
 *  compares the set of hosts shown (hostsShown), so a host owning two descriptions (the Account row; a synthetic doubled row) is
 *  one host shown, and a second doubled host anywhere changes nothing here. The literal list of doubled hosts this replaced
 *  (`tab === "general" ? ["rs-login-btn:2"] : []`) named the exception by id and count; now the doubled hosts are DERIVED and
 *  printed as a diagnostic on every run, which is what keeps a genuinely accidental second `.rs-sub` visible (the defect gear.css's
 *  rs-note comment records once happening), since the derived form no longer reds on one: a reader of the log sees it, the pin
 *  does not. Whether a doubled host's two descriptions intersect each other is a diagnostic too (the Account row's stack at the
 *  row's bottom; a doubled row wrapped otherwise may not stack), never an assertion keyed on the count. */
async function panelMatrix(t: any, page: any, errors: string[], tab: string, pane: string, hosts: any[]): Promise<void> {
  const doubled = hosts.filter((h: any) => h.subs > 1).map((h: any) => h.host + ":" + h.subs);
  const controlsN = hosts.reduce((n: number, h: any) => n + h.controls.length, 0);
  const rowsN = new Set(hosts.map((h: any) => h.row)).size;
  const boxesPerRow = hosts.filter((h: any) => h.box).reduce((m: Record<string, number>, h: any) => { m[h.row] = (m[h.row] || 0) + 1; return m; }, {});
  const maxBoxes = Math.max(0, ...(Object.values(boxesPerRow) as number[]));
  t.diagnostic(`census ${tab}: hosts=${hosts.length} rows=${rowsN} controls=${controlsN} maxBoxesInARow=${maxBoxes} doubled=${doubled.join(",") || "none"}`);
  // the within-row arm below is exact for ONE box per row: the box pair's rules select every box in the row (gear.css), so a row
  // carrying two boxes would show both on either road; the census reads at most one today, and the sheet states the bound
  assert.ok(maxBoxes <= 1, "the rig: at most one Fast mode box per row (the within-row rule is exact for one box per row, as the sheet states)");
  // the population, derived both ways: the census's (visible host, visible focusable control) and the wider one (every
  // description-owning host and its controls, visible or not), with the census's exclusions named; a description the census
  // silently misses reds here
  const pop = await populations(page, hosts.map((h: any) => h.host));
  t.diagnostic(`population ${tab}: census hosts=${hosts.length} controls=${controlsN}; description-owning hosts=${pop.describedHosts} controls=${pop.describedControls}; descriptions=${pop.descriptions} covered=${pop.covered} excluded=${JSON.stringify(pop.excluded)}`);
  assert.deepEqual(pop.missed, [], "the rig: every description in the pane whose host has a focusable control is a census host's");
  assert.equal(pop.covered, hosts.reduce((n: number, h: any) => n + h.subs, 0), "the rig: the census's description count is the pane's covered count");
  assert.equal(pop.describedHosts - pop.excluded.length, hosts.length, "the rig: the wider population less the named exclusions is the census (one exclusion per skipped description; a skipped host owns one)");
  for (const h of hosts) {
    await page.mouse.move(5, 5);
    const tabbed = await tabInto(page, h.control);
    assert.equal(tabbed.landed && tabbed.focusVisible, true, `the rig: a Tab landed a :focus-visible focus on ${h.control} (from ${tabbed.prev})`);
    const alone = await shownPanel(page);
    assert.deepEqual(hostsShown(alone), [h.host], `a keyboard focus in ${h.host} with the pointer on nothing shows its description alone (one host shown, whatever number it owns)`);
    for (const o of hosts) {
      if (o === h) continue;
      await hoverOn(page, o.hoverSel);
      const r = await shownPanel(page);
      assert.equal(r.active, h.control, `the rig: the focus stayed on ${h.control} while the pointer rests on ${o.host}`);
      if (o.row === h.row) {
        // the two hosts share a row (a judge row and its Fast mode box): within a row the BOX's description wins whenever either
        // road rests on the box (the box's pair and its twins, both (1,5,0)), one description either way; the one exception to
        // the pointer-wins rule, stated in the sheet beside the rule; the winner is the box among the pair, whichever road it is on
        const boxes = [h, o].filter((x: any) => x.box);
        const winner = boxes.length === 1 ? boxes[0].host : o.host;   // one box among the pair: the box; none: the pointer's
        assert.deepEqual(hostsShown(r), [winner], `focus in ${h.host}, pointer on ${o.host}, one row: one host's description, the box's (within a row the box wins, whichever road rests on it)`);
      } else {
        assert.deepEqual(hostsShown(r), [o.host], `focus in ${h.host}, pointer on ${o.host}, two rows: one host's description, the pointer's (the pointer wins), never the focused row's beside it, whatever number either host owns`);
      }
      assert.equal(r.intersect, false, "and no two shown descriptions of different hosts intersect");
      if (r.intersectWithin) t.diagnostic(`focus in ${h.host}, pointer on ${o.host}: ${o.host}'s ${o.subs} descriptions intersect each other (a doubled host)`);
    }
    await page.mouse.move(5, 5);
    assert.deepEqual(hostsShown(await shownPanel(page)), [h.host], `the pointer gone, ${h.host}'s description shows again on the focus alone`);
  }
  // a mark on ANOTHER row hovered while a keyboard focus holds a description: the mark's native title is the one tooltip, so
  // nothing is shown (the second road out of the row the author's mirror-and-twins pass left open: a focus-shown description
  // beside another row's title)
  const first = hosts[0], other = hosts.find((h: any) => h.row !== first.row && h.hasMark);
  if (tab === "tasks") assert.ok(other, "the rig: the Task tracking pane has a row with a mark span outside the first host's row");
  if (other) {
    await page.mouse.move(5, 5);
    const tabbed = await tabInto(page, first.control);
    assert.equal(tabbed.landed && tabbed.focusVisible, true, "the rig: a keyboard focus in the first host");
    await page.evaluate((cid: string) => {
      const row = document.getElementById(cid)!.closest("#rsettings .rs-row, #rsettings .rs-widget")!;
      const mark = row.querySelector(".rs-mixed") as HTMLElement;
      mark.hidden = false; mark.textContent = "mixed"; mark.title = "differs on: TESTHOST";
    }, other.control);
    await hoverOn(page, other.hoverSel.replace(/ b$/, " .rs-mixed"));
    const onMark = await shownPanel(page);
    assert.equal(onMark.active, first.control, "the rig: the focus stayed in the first host");
    assert.deepEqual(onMark.shown, [], `the pointer on ${other.host}'s mark while ${first.host} holds the focus: no description beside the mark's title`);
    await page.mouse.move(5, 5);
    assert.deepEqual(hostsShown(await shownPanel(page)), [first.host], "the pointer gone, the focused host's shows again");
  } else t.diagnostic(`the ${pane} pane has no mark span outside the first host's row: the mark road is driven on the Task tracking pane`);
  assert.deepEqual(errors, [], "no page error");
}

for (const [tab, pane, floor] of PANES) {
  test(`one tooltip across the ${pane} pane, the census form: a keyboard focus in each host shows its description alone; the pointer on every OTHER host shows that host's alone (the pointer wins); the pointer on nothing shows the focused one; a hovered mark on another row shows none`, { timeout: 240000 }, async (t) => {
    await withGear(t, tab, async (page, errors) => {
      await settled(page, tab);
      const hosts = await census(page);
      assert.ok(hosts.length >= floor, "the rig: the pane has the hosts the census form expects (" + hosts.length + " of at least " + floor + "): " + hosts.map((h: any) => h.host).join(","));
      if (tab === "tasks") assert.ok(hosts.some((h: any) => h.kind === "checkbox") && hosts.some((h: any) => h.kind === "button") && hosts.some((h: any) => h.host.endsWith("-wrap")),
        "the rig: the Task tracking census spans the control kinds (checkbox rows, picker-button rows, the Fast mode boxes)");
      if (tab === "general") assert.ok(hosts.some((h: any) => h.kind === "text" && h.tag === "TEXTAREA"), "the rig: the General census reaches the Pictures from the web textarea");
      if (tab === "sessions") assert.ok(hosts.some((h: any) => h.kind === "text" && h.tag === "INPUT"), "the rig: the Sessions census reaches the Default directory input");
      await panelMatrix(t, page, errors, tab, pane, hosts);
    });
  });

  test(`a mouse click on every control in the ${pane} pane, then the pointer leaving, by control kind: a checkbox or a button shows nothing with the control still focused (a click is not :focus-visible); a TEXT field shows its row's description until it blurs (a focus in a text field is always :focus-visible)`, { timeout: 240000 }, async (t) => {
    await withGear(t, tab, async (page, errors) => {
      await settled(page, tab);
      const hosts = await census(page);
      assert.ok(hosts.length >= floor, "the rig: the census (" + hosts.length + " of at least " + floor + ")");
      const kinds = new Set<string>();
      for (const h of hosts) for (const c of h.controls) {
        kinds.add(c.kind);
        await page.evaluate(() => (document.activeElement as HTMLElement | null)?.blur?.());
        await page.mouse.move(5, 5);
        assert.equal((await shownPanel(page)).menus, 0, `the rig: no menu or modal left open before the click on ${c.id}`);
        await page.click(`#${c.id}`);
        const on = await shownPanel(page);
        assert.equal(on.active, c.id, `the rig: the click focused ${c.id}`);
        await page.mouse.move(5, 5);
        const off = await shownPanel(page);
        assert.equal(off.active, c.id, `the control keeps the focus after the pointer leaves (${c.id})`);
        if (c.kind === "text") {
          assert.equal(on.focusVisible, true, `a mouse click into a text field IS a :focus-visible focus (${c.id}: the caret is the ring)`);
          assert.deepEqual(hostsShown(off), [h.host], `clicked the text field ${c.id} and left: its row's description shows until the field blurs (the one exception to "never a mouse click", stated in the sheet)`);
          assert.ok(off.up.every((u: string) => u === h.host), "no host but the shown one wears the placement class");
          await page.evaluate(() => (document.activeElement as HTMLElement).blur());
          assert.deepEqual((await shownPanel(page)).shown, [], `and the field blurred, nothing shows (${c.id})`);
        } else if (c.kind === "checkbox" || c.kind === "button") {
          assert.equal(on.focusVisible, false, `the rig: a mouse click on a ${c.kind} is not a :focus-visible focus (${c.id})`);
          assert.deepEqual(off.shown, [], `clicked the ${c.kind} ${c.id} in ${h.host} and left: no description outlives the pointer`);
          assert.deepEqual(off.up, [], "and no host wears the placement class with nothing shown");
        } else {
          assert.fail(`a control kind this leg does not classify (${c.kind}, ${c.tag}#${c.id}): state what a click into it shows`);
        }
        if (c.kind === "button") await settleAfterClick(page, c.id);   // a picker's list, a house dropdown or the login modal opened by the click: closed again
      }
      assert.equal((await shownPanel(page)).menus, 0, "the rig: nothing left open at the end");
      const expectKinds: Record<string, string[]> = { general: ["button", "text", "checkbox"], chat: ["checkbox", "button"], feed: ["checkbox"], sessions: ["text", "button"], automation: [], tasks: ["checkbox", "button"], debug: ["checkbox"] };
      for (const k of expectKinds[tab]) assert.ok(kinds.has(k), `the rig: the ${pane} pane's census drove a ${k} (the kinds it has today)`);
      assert.deepEqual(errors, [], "no page error");
    });
  });
}

test("a synthetic SECOND doubled row (two descriptions under one checkbox row, the Account row's shape) on the Debug pane: the invariant holds over the whole census with it, one host shown whatever it owns, where the count pin this replaced named the Account row as the one doubled host and red on any other", { timeout: 240000 }, async (t) => {
  await withGear(t, "debug", async (page, errors) => {
    await injectDoubledRow(page);
    const hosts = await census(page);
    const synth = hosts.find((h: any) => h.host === "probe-synth-box");
    assert.ok(synth && synth.subs === 2, "the rig: the census reads the synthetic row as a host owning two descriptions: " + JSON.stringify(hosts.map((h: any) => h.host + ":" + h.subs)));
    assert.ok(hosts.some((h: any) => h.subs > 1), "the rig: the multi-description case is exercised in this run (the property, never a host's identity)");
    await panelMatrix(t, page, errors, "debug", "Debug", hosts);
  });
});

test("the picker-open state, the one the panel leg did not enter (the maintainer's round 5, correctness-1): a colormap or palette list open under the pointer stands the hovered row's own description down, so that row has nothing to show and stands nothing down; a keyboard focus in another row shows that row's description alone (zero before), the pointer on another row with a description shows that one alone, and a Tab out of the open picker's button shows the focused row's; the row wears rs-picking exactly while its list is open, at every site that moves a list", { timeout: 120000 }, async (t) => {
  await withGear(t, "general", async (page, errors) => {
    await settled(page, "general");
    const hosts = await census(page);
    const pickerRow = (id: string) => page.evaluate((lid: string) => {
      const list = document.getElementById(lid)!, row = list.closest("#rsettings .rs-row") as HTMLElement;
      return { open: !list.hidden, picking: row.classList.contains("rs-picking"), hovered: row.matches(":hover") };
    }, id);
    // (a) the list open by its button: the pointer rests on the button, inside the Colormap row, whose own description the open
    // list stands down; the row wears the class; nothing shows in the panel
    await page.click("#rs-cmap-btn");
    let cm = await pickerRow("rs-cmap-list");
    assert.deepEqual(cm, { open: true, picking: true, hovered: true }, "the rig: the colormap list is open under the pointer and its row wears rs-picking");
    const a0 = await shownPanel(page);
    assert.equal(a0.menus, 1, "the rig: one menu open");
    assert.deepEqual(a0.shown, [], "the hovered row's own description stands down under its open list, and nothing else shows");
    // a real Tab into another row's control while the list stays open: the focused row's description shows ALONE (before the
    // fix the panel-wide stand-down read the hovered row as a trigger, since it contains a description, and hid this one too)
    const other = hosts.find((h: any) => h.host === "rs-fileedit");
    assert.ok(other, "the rig: the General census holds the File comments row (its control is the first tabbable after the two picker buttons)");
    const tabbed = await tabInto(page, other.control);
    assert.equal(tabbed.landed && tabbed.focusVisible, true, "the rig: a keyboard focus landed in another row (from " + tabbed.prev + ")");
    cm = await pickerRow("rs-cmap-list");
    assert.deepEqual(cm, { open: true, picking: true, hovered: true }, "the rig: the list is still open under the pointer");
    const a1 = await shownPanel(page);
    assert.equal(a1.menus, 1);
    assert.deepEqual(a1.shown, [other.host], "exactly one description, the focused row's: the hovered row has nothing to show, so it stands nothing down");
    assert.equal(a1.intersect, false);
    // the pointer moves to a third row WITH a description while the list stays open: the pointer wins, one shown
    const third = hosts.find((h: any) => h.host !== other.host && h.host !== "rs-cmap-btn" && h.host !== "rs-pal-btn" && !h.box);
    assert.ok(third, "the rig: a third General host with a description");
    await hoverOn(page, third.hoverSel);
    const a2 = await shownPanel(page);
    assert.equal(a2.active, other.control, "the rig: the focus stayed");
    assert.equal((await pickerRow("rs-cmap-list")).open, true, "the rig: the list is still open (a hover closes nothing)");
    assert.deepEqual(Array.from(new Set(a2.shown)), [third.host], "the pointer on a row showing a description wins: that host's description alone (whatever number it owns: the Account row owns two), the focused row's standing down");
    await page.mouse.move(5, 5);
    assert.deepEqual((await shownPanel(page)).shown, [other.host], "the pointer gone, the focused row's shows again");
    // (b) the button's second click closes the list and the class goes with it
    await page.click("#rs-cmap-btn");
    assert.deepEqual(await pickerRow("rs-cmap-list"), { open: false, picking: false, hovered: true }, "closed by its button: hidden and no class");
    assert.equal((await shownPanel(page)).menus, 0);
    // (c) the second road: the list open, then one Tab from its button lands on the palette button (:focus-visible) with the
    // pointer still on the colormap row: the palette row's description shows alone (zero before)
    await page.click("#rs-cmap-btn");
    assert.equal((await pickerRow("rs-cmap-list")).open, true, "the rig: open again");
    await page.keyboard.press("Tab");
    const c1 = await shownPanel(page);
    assert.equal(c1.active, "rs-pal-btn", "the rig: the Tab landed on the palette button");
    assert.equal(c1.focusVisible, true, "the rig: a Tab is :focus-visible");
    assert.equal((await pickerRow("rs-cmap-list")).hovered, true, "the rig: the pointer still rests on the colormap row");
    assert.deepEqual(c1.shown, ["rs-pal-btn"], "exactly one description, the focused palette row's");
    // (d) a pick closes the list through the same writer: the class goes
    await page.click("#rs-cmap-list .rs-cmap-opt");
    assert.deepEqual(await pickerRow("rs-cmap-list"), { open: false, picking: false, hovered: true }, "closed by a pick: hidden and no class");
    // (e) the outside-click closer, on the palette picker: open by its button, close by a click on the card's title
    await page.click("#rs-pal-btn");
    assert.deepEqual(await pickerRow("rs-pal-list"), { open: true, picking: true, hovered: true }, "the palette list open under the pointer, its row wearing the class");
    assert.deepEqual((await shownPanel(page)).shown, [], "and its row's own description stands down");
    await page.click("#rsettings .rs-sec.rs-sec-first");   // the Account section header: inside the card, outside every picker and every row
    assert.deepEqual(await pickerRow("rs-pal-list"), { open: false, picking: false, hovered: false }, "closed by the outside click: hidden and no class");
    assert.equal((await shownPanel(page)).menus, 0, "the rig: nothing left open");
    assert.deepEqual(errors, [], "no page error");
  });
});

test("a HOUSE dropdown open under the pointer (gear.js housePick: the judge rows' model and effort pickers and the widget options' pickers), the state the picker-open leg does not enter: those rows never wear rs-picking, so the pointer-wins rule alone governs it; exactly one description is shown with a keyboard focus in another row (never zero, never two), the open menu is counted by its computed position, and which host shows is recorded", { timeout: 180000 }, async (t) => {
  // the exclusion the sheet states beside its one-tooltip rule (the author's fixer pass after round 5, exclusions-1): housePick
  // writes its menu's hidden itself and never calls setListOpen, so the class the two list pickers wear never reaches these rows
  // and the hovered row's own description shows beside its open menu; whether that row should join the class is the
  // maintainer's call (upstream's picker from before this branch), so the pins here are the invariants that hold either way,
  // and the reading (which host, the class) is a diagnostic
  assert.equal((GEAR.match(/function housePick\(/g) || []).length, 1, "the rig: gear.js holds the house dropdown factory");
  const houseBody = GEAR.slice(GEAR.indexOf("function housePick("), GEAR.indexOf("var SCHEMES = ["));
  assert.equal((houseBody.match(/setListOpen\(/g) || []).length, 0, "housePick does not call the list writer: its rows never wear rs-picking (the exclusion the sheet states; a call here would be the maintainer's behaviour change, and this pin then moves with it)");
  assert.match(houseBody, /menu\.hidden = true;[\s\S]*menu\.hidden = false;/, "the rig: housePick writes its menu's hidden itself, both ways");
  for (const [tab, pane, floor] of [["tasks", "Task tracking", 4], ["chat", "Chat", 5]] as const) {
    await withGear(t, tab, async (page, errors) => {
      await settled(page, tab);
      const hosts = await census(page);
      // every house picker button among the census controls: a button whose next sibling is the menu housePick appends (a div
      // positioned absolutely), derived from the DOM and never listed here
      const house: string[] = await page.evaluate((ids: string[]) => ids.filter((id) => {
        const b = document.getElementById(id); const m = b && (b.nextElementSibling as HTMLElement | null);
        return !!(b && b.tagName === "BUTTON" && m && m.tagName === "DIV" && getComputedStyle(m).position === "absolute");
      }), hosts.flatMap((h: any) => h.controls.map((c: any) => c.id)));
      assert.ok(house.length >= floor, `the rig: the ${pane} pane holds house pickers among the census controls (${house.length} of at least ${floor})`);
      for (const id of house) {
        const host = hosts.find((h: any) => h.controls.some((c: any) => c.id === id));
        await page.evaluate(() => (document.activeElement as HTMLElement | null)?.blur?.());
        await page.mouse.move(5, 5);
        assert.equal((await shownPanel(page)).menus, 0, "the rig: nothing open before the click");
        await page.click(`#${id}`);   // opens the menu; the pointer rests on the button, inside the row
        const st = await page.evaluate((cid: string) => {
          const b = document.getElementById(cid)!, m = b.nextElementSibling as HTMLElement, row = b.closest("#rsettings .rs-row, #rsettings .rs-widget") as HTMLElement;
          return { open: !m.hidden, picking: row.classList.contains("rs-picking"), hovered: row.matches(":hover"), inRow: !!b.closest(".rs-row"), optionTitles: Array.from(m.children).filter((x) => x.getAttribute("title")).length };
        }, id);
        assert.equal(st.open && st.hovered, true, `the rig: the menu of ${id} is open under the pointer`);
        assert.equal(st.optionTitles, 0, "the rig: the menu's option rows carry no native title (so a description beside the menu stacks with no tooltip)");
        const on = await shownPanel(page);
        assert.equal(on.menus, 1, `the rig: the one open house menu is counted by its computed position (${id}; the style attribute's text carries a space the old selector never matched)`);
        assert.ok(hostsShown(on).length <= 1, `at most one description with the house menu of ${id} open under the pointer: ${JSON.stringify(on.shown)}`);
        // a real Tab into another row's control while the menu stays open under the pointer
        const other = hosts.find((o: any) => o.row !== host.row && !o.box);
        assert.ok(other, "the rig: another row with a description in the pane");
        const tabbed = await tabInto(page, other.control);
        assert.equal(tabbed.landed && tabbed.focusVisible, true, `the rig: a keyboard focus landed in another row (from ${tabbed.prev})`);
        const withFocus = await shownPanel(page);
        assert.equal(withFocus.menus, 1, "the rig: the menu is still open (a Tab closes nothing)");
        assert.equal(hostsShown(withFocus).length, 1, `exactly one description with the house menu of ${id} open under the pointer and a keyboard focus in ${other.host}: never zero (the panel-wide stand-down stands the focused row's down only for a hovered row SHOWING one) and never two: ${JSON.stringify(withFocus.shown)}`);
        assert.equal(withFocus.intersect, false, "and no two shown descriptions of different hosts intersect");
        t.diagnostic(`house menu ${id} (${pane}, ${st.inRow ? "a row's picker" : "a widget option's picker"}): rs-picking=${st.picking}; shown under the pointer=${JSON.stringify(hostsShown(on))}; with a focus in ${other.host}=${JSON.stringify(hostsShown(withFocus))}`);
        await page.keyboard.press("Escape");   // housePick's keydown closer
        assert.equal((await shownPanel(page)).menus, 0, `the rig: Escape closed the menu of ${id}`);
        await page.mouse.move(5, 5);
      }
      assert.deepEqual(errors, [], "no page error");
    });
  }
});

test("the roads a browser decides by its own reading of :focus-visible, recorded: a programmatic focus after a mouse click and after a key press (a screen reader's move), and an emulated tap then a Tab; at most one description is shown on each", { timeout: 120000 }, async (t) => {
  await withGear(t, "debug", async (page, errors) => {
    await page.click("#rs-perfmute");
    await page.mouse.move(5, 5);
    await page.evaluate(() => document.getElementById("rs-perfshare")!.focus({ preventScroll: true }));
    const afterClick = await shownPanel(page);
    assert.equal(afterClick.active, "rs-perfshare", "the rig: the programmatic focus landed");
    assert.ok(afterClick.shown.length <= 1, "at most one shown");
    t.diagnostic(`programmatic focus after a mouse click: focus-visible=${afterClick.focusVisible} shown=${JSON.stringify(afterClick.shown)}`);
    await page.keyboard.press("Shift");
    await page.evaluate(() => document.getElementById("rs-perfmute")!.focus({ preventScroll: true }));
    const afterKey = await shownPanel(page);
    assert.equal(afterKey.active, "rs-perfmute", "the rig: the programmatic focus landed");
    assert.ok(afterKey.shown.length <= 1, "at most one shown");
    t.diagnostic(`programmatic focus after a key press: focus-visible=${afterKey.focusVisible} shown=${JSON.stringify(afterKey.shown)}`);
    assert.deepEqual(errors, [], "no page error");
  });
  await withGear(t, "debug", async (page, errors) => {
    await page.tap("#rs-perfshare");
    const tapped = await shownPanel(page);
    assert.equal(tapped.active, "rs-perfshare", "the rig: the tap focused the checkbox");
    assert.ok(tapped.shown.length <= 1, "at most one shown after a tap");
    t.diagnostic(`tap: focus-visible=${tapped.focusVisible} shown=${JSON.stringify(tapped.shown)} (a touch browser leaves the tapped row hovered)`);
    await page.keyboard.press("Tab");
    const thenTab = await shownPanel(page);
    assert.equal(thenTab.active, "rs-perfmute", "the rig: the Tab moved the focus to the next row");
    assert.ok(thenTab.shown.length <= 1, "at most one shown after a tap then a Tab (the tapped row's sticky hover and the Tabbed row's focus are two roads at once)");
    assert.equal(thenTab.intersect, false);
    t.diagnostic(`tap then Tab: shown=${JSON.stringify(thenTab.shown)}`);
    assert.deepEqual(errors, [], "no page error");
  }, 320, { hasTouch: true, isMobile: true });
});

test("the placement survives the other road's exit: a pointer leaving a row whose checkbox holds a keyboard focus, a focus leaving a hovered row, and a pointer entering then leaving a focused row all keep rs-up on the row parked at the card's bottom, and the class is off once both roads are gone", { timeout: 120000 }, async (t) => {
  await withGear(t, "debug", async (page, errors) => {
    const label = "#rsettings .rs-row:has(#rs-perfshare) b";
    const read = () => page.evaluate(() => {
      const box = document.getElementById("rs-perfshare")!, row = box.closest("#rsettings .rs-row") as HTMLElement;
      const sub = row.querySelector(".rs-sub") as HTMLElement, card = document.querySelector("#rsettings .rs-card")!;
      const sr = sub.getBoundingClientRect(), rr = row.getBoundingClientRect(), cr = card.getBoundingClientRect();
      return { hovered: row.matches(":hover"), focused: document.activeElement === box, display: getComputedStyle(sub).display,
        up: row.classList.contains("rs-up"), subAboveRow: sr.bottom <= rr.top + 1, pastCard: sr.bottom > cr.bottom + 1, fitsBelow: rr.bottom + sr.height + 2 <= cr.bottom };
    });
    const park = () => page.evaluate(() => { (document.activeElement as HTMLElement | null)?.blur?.(); (document.querySelector("#rsettings .rs-card") as HTMLElement).scrollTop = 0; });
    // (a) pointer on the row, Tab into it, pointer leaves
    await park(); await page.mouse.move(5, 5);
    await hoverOn(page, label);
    const a0 = await read();
    assert.equal(a0.hovered && a0.display === "block" && a0.up, true, "the rig: the hovered row shows its description placed above " + JSON.stringify(a0));
    assert.equal(a0.fitsBelow, false, "the rig: parked at the card's bottom a popover below would run past the card");
    const ta = await tabInto(page, "rs-perfshare");
    assert.equal(ta.landed && ta.focusVisible, true, "the rig: a keyboard focus in the hovered row");
    await page.mouse.move(5, 5);
    const a1 = await read();
    assert.equal(a1.hovered, false, "the rig: the pointer left");
    assert.equal(a1.display, "block", "the description is still shown on the focus");
    assert.equal(a1.up, true, "the pointer's exit kept the placement the focus still needs (it stripped it, and the popover flipped below the row)");
    assert.equal(a1.subAboveRow, true, "the popover is above the row");
    assert.equal(a1.pastCard, false, "and inside the card");
    // (b) Tab first, pointer enters then leaves
    await park(); await page.mouse.move(5, 5);
    const tb = await tabInto(page, "rs-perfshare");
    assert.equal(tb.landed && tb.focusVisible, true, "the rig: a keyboard focus");
    await hoverOn(page, label);
    await page.mouse.move(5, 5);
    const b1 = await read();
    assert.equal(b1.focused && b1.display === "block", true, "the rig: the description is shown on the focus");
    assert.equal(b1.up && b1.subAboveRow && !b1.pastCard, true, "a pointer passing over the focused row leaves its placement standing " + JSON.stringify(b1));
    // (c) hovered row, the focus leaves it (a Tab onward)
    await park(); await page.mouse.move(5, 5);
    await hoverOn(page, label);
    const tc = await tabInto(page, "rs-perfshare");
    assert.equal(tc.landed, true, "the rig: the focus is in the hovered row");
    await page.keyboard.press("Tab");
    const c1 = await read();
    assert.equal(c1.focused, false, "the rig: the focus left the row");
    assert.equal(c1.hovered && c1.display === "block", true, "the rig: the pointer still shows the description");
    assert.equal(c1.up && c1.subAboveRow && !c1.pastCard, true, "the focus's exit kept the placement the pointer still needs " + JSON.stringify(c1));
    // (d) both gone: the class is off
    await page.mouse.move(5, 5);
    await page.evaluate(() => (document.activeElement as HTMLElement | null)?.blur?.());
    const d1 = await read();
    assert.equal(d1.display, "none", "the rig: nothing shown");
    assert.equal(d1.up, false, "with nothing shown the class is off (placeSub drops it and re-adds it only while a popover is shown)");
    assert.deepEqual(errors, [], "no page error");
  });
});

test("the placement when the focus ARRIVES under the stand-down: the pointer resting on another row with a description (or on its mark) hides the focused row's description at focusin, and the pointer's exit places it; a pointer entering another row drops the class of the description it hides and its exit restores it; the same for a Fast mode box parked low", { timeout: 180000 }, async (t) => {
  // the ordinary sequence: the mouse rests where the gear was clicked, and the person tabs into the panel. At focusin the
  // panel-wide stand-down hides the focused row's description (the pointer wins), so placeSub measures zero height and sets
  // nothing; before the fix the pointer's exit re-placed the pointer's row alone, and the focused row's description appeared
  // below it unplaced, 35 px past the card's bottom with room above (the T408 clip; measured at the head of the author's pass
  // after round 4)
  await withGear(t, "debug", async (page, errors) => {
    const read = (id: string) => page.evaluate((cid: string) => {
      const HOSTS = "#rsettings .rs-fastin, #rsettings .rs-row, #rsettings .rs-widget";
      const box = document.getElementById(cid)!, host = box.closest(HOSTS) as HTMLElement, row = (box.closest("#rsettings .rs-row") || host) as HTMLElement;
      const sub = (Array.from(host.querySelectorAll(".rs-sub")) as HTMLElement[]).find((el) => el.closest(HOSTS) === host)!;
      const card = document.querySelector("#rsettings .rs-card")!;
      const sr = sub.getBoundingClientRect(), rr = row.getBoundingClientRect(), cr = card.getBoundingClientRect();
      return { focused: document.activeElement === box, hovered: row.matches(":hover"), display: getComputedStyle(sub).display, up: host.classList.contains("rs-up"),
        subAboveRow: sr.bottom <= rr.top + 1, pastCard: sr.bottom > cr.bottom + 1, fitsBelow: rr.bottom + sr.height + 2 <= cr.bottom, roomAbove: Math.round(rr.top - cr.top), subH: Math.round(sr.height) };
    }, id);
    const park = () => page.evaluate(() => { (document.activeElement as HTMLElement | null)?.blur?.(); (document.querySelector("#rsettings .rs-card") as HTMLElement).scrollTop = 0; });
    const muteLabel = "#rsettings .rs-row:has(#rs-perfmute) b";
    // (e) the pointer rests on the mute row's label, a real Tab into the share row parked at the card's bottom, the pointer leaves
    await park(); await page.mouse.move(5, 5);
    await hoverOn(page, muteLabel);
    const e0 = await read("rs-perfmute");
    assert.equal(e0.hovered && e0.display === "block", true, "the rig: the pointer's row shows its description " + JSON.stringify(e0));
    const te = await tabInto(page, "rs-perfshare");
    assert.equal(te.landed && te.focusVisible, true, "the rig: a keyboard focus arrived in the share row (from " + te.prev + ")");
    const e1 = await read("rs-perfshare");
    assert.equal(e1.display, "none", "the rig: at focusin the stand-down hides the focused row's description (the pointer wins)");
    assert.deepEqual((await shownPanel(page)).shown, ["rs-perfmute"], "the rig: the pointer's description is the one shown");
    await page.mouse.move(5, 5);
    const e2 = await read("rs-perfshare");
    assert.equal(e2.focused && !e2.hovered && e2.display === "block", true, "the rig: the pointer gone, the focused row's description shows " + JSON.stringify(e2));
    assert.equal(e2.fitsBelow, false, "the rig: parked at the card's bottom a popover below the row would run past the card (read with the popover shown; hidden it has no height) " + JSON.stringify(e2));
    assert.equal(e2.up, true, "the pointer's exit placed the focused row's description (it re-placed the pointer's row alone, and this one appeared unplaced below the row)");
    assert.equal(e2.subAboveRow && !e2.pastCard, true, "so it opens above the row and inside the card " + JSON.stringify(e2));
    assert.deepEqual((await shownPanel(page)).up, ["rs-perfshare"], "and the focused row is the one host wearing the class");
    // (g) the enter half: the focus first (placed), then the pointer enters the mute row (the stand-down hides the focused
    // row's description, so its class says nothing true and is dropped) and leaves (placed again)
    await park(); await page.mouse.move(5, 5);
    const tg = await tabInto(page, "rs-perfshare");
    assert.equal(tg.landed && tg.focusVisible, true, "the rig: a keyboard focus");
    const g0 = await read("rs-perfshare");
    assert.equal(g0.display === "block" && g0.up, true, "the rig: the focus alone shows the description placed above " + JSON.stringify(g0));
    await hoverOn(page, muteLabel);
    const g1 = await shownPanel(page);
    assert.deepEqual(g1.shown, ["rs-perfmute"], "the rig: the pointer's row shows, the focused row's stands down");
    assert.deepEqual(g1.up.filter((u: string) => u === "rs-perfshare"), [], "the pointer's enter dropped the class of the description it hid (a hidden popover is placed by nothing)");
    await page.mouse.move(5, 5);
    const g2 = await read("rs-perfshare");
    assert.equal(g2.display === "block" && g2.up && g2.subAboveRow && !g2.pastCard, true, "and its exit placed it again " + JSON.stringify(g2));
    assert.deepEqual(errors, [], "no page error");
  });
  // (h) the Fast mode box parked low with the pointer on the Task tracking row's label, a real Tab into the box, the pointer leaves
  await withGear(t, "tasks", async (page, errors) => {
    const parkLow = () => page.evaluate(() => {
      (document.activeElement as HTMLElement | null)?.blur?.();
      const box = document.getElementById("rs-judgefast")!, row = box.closest("#rsettings .rs-row") as HTMLElement, card = document.querySelector("#rsettings .rs-card") as HTMLElement;
      card.scrollTop = 0; const rr0 = row.getBoundingClientRect(), cr0 = card.getBoundingClientRect();
      card.scrollTop = Math.max(0, (rr0.top - cr0.top) - (cr0.height - rr0.height - 4));
    });
    const readBox = () => page.evaluate(() => {
      const box = document.getElementById("rs-judgefast")!, fast = box.closest(".rs-fastin") as HTMLElement, row = box.closest("#rsettings .rs-row") as HTMLElement;
      const sub = document.getElementById("rs-judgefast-sub")!, sr = sub.getBoundingClientRect(), rr = row.getBoundingClientRect(), cr = document.querySelector("#rsettings .rs-card")!.getBoundingClientRect();
      return { focused: document.activeElement === box, hovered: row.matches(":hover"), display: getComputedStyle(sub).display, boxUp: fast.classList.contains("rs-up"), rowUp: row.classList.contains("rs-up"),
        subAboveRow: sr.bottom <= rr.top + 1, pastCard: sr.bottom > cr.bottom + 1, fitsBelow: rr.bottom + sr.height + 2 <= cr.bottom };
    });
    await parkLow(); await page.mouse.move(5, 5);
    await hoverOn(page, "#rsettings .rs-row:has(#rs-tasktrack) b");
    assert.deepEqual((await shownPanel(page)).shown, ["rs-tasktrack"], "the rig: the pointer's row shows its description");
    const th = await tabInto(page, "rs-judgefast");
    assert.equal(th.landed && th.focusVisible, true, "the rig: a keyboard focus arrived in the box (from " + th.prev + ")");
    const h1 = await readBox();
    assert.equal(h1.display, "none", "the rig: the box's description stands down under the pointer's row");
    await page.mouse.move(5, 5);
    const h2 = await readBox();
    assert.equal(h2.focused && !h2.hovered && h2.display === "block", true, "the rig: the pointer gone, the box's description shows " + JSON.stringify(h2));
    assert.equal(h2.fitsBelow, false, "the rig: the row is parked just above the card's bottom (read with the popover shown) " + JSON.stringify(h2));
    assert.equal(h2.boxUp, true, "the pointer's exit placed the BOX (the focused host's row and its boxes are re-placed with the pointer's row)");
    assert.equal(h2.rowUp, false, "and the row wears none (its own popover is hidden)");
    assert.equal(h2.subAboveRow && !h2.pastCard, true, "the box's description opens above the row and inside the card " + JSON.stringify(h2));
    // (f) the pointer rests on another row's MARK (the Distilling model row's, a synthetic title; the Debug rows carry no mark
    // span), the same Tab into the box parked low, the pointer leaves
    await parkLow(); await page.mouse.move(5, 5);
    const markSel = "#rsettings .rs-row:has(#rs-distillmodel) b .rs-mixed";
    await page.evaluate((sel: string) => { const m = document.querySelector(sel) as HTMLElement; m.hidden = false; m.textContent = "mixed"; m.title = "differs on: TESTHOST"; }, markSel);
    await hoverOn(page, markSel);
    const tf = await tabInto(page, "rs-judgefast");
    assert.equal(tf.landed && tf.focusVisible, true, "the rig: a keyboard focus arrived in the box while the pointer rests on another row's mark");
    assert.deepEqual((await shownPanel(page)).shown, [], "the rig: the mark's title is the one tooltip, nothing shown");
    await page.mouse.move(5, 5);
    const f1 = await readBox();
    assert.equal(f1.display === "block" && f1.boxUp && f1.subAboveRow && !f1.pastCard, true, "the pointer leaving the mark placed the box's description above the row " + JSON.stringify(f1));
    assert.deepEqual(errors, [], "no page error");
  }, 260);
});

test("the placement is re-placed at ROW scope: a focus that moves from a row's picker button into its Fast mode box and then out leaves no class behind on the row, and the box parked low keeps its own placement while a pointer passes over the row outside the box", { timeout: 120000 }, async (t) => {
  await withGear(t, "tasks", async (page, errors) => {
    // the stale-class road: the picker button and the box share the row, so the button-to-box move never leaves the row
    const r0 = await focusParked(page, "rs-judgefast", "low");
    assert.equal(r0.tab.landed && r0.tab.focusVisible, true, "the rig: a Tab from the row's picker button (" + r0.tab.prev + ") landed in the box");
    assert.match(String(r0.tab.prev), /BUTTON/, "the rig: the tabbable before the box is the row's picker button");
    assert.equal(r0.fitsBelow, false, "the rig: the row is parked just above the card's bottom " + JSON.stringify(r0.geom));
    assert.equal(r0.up, true, "the rig: the box wears rs-up");
    await page.keyboard.press("Tab");
    const after = await page.evaluate(() => {
      const box = document.getElementById("rs-judgefast")!, row = box.closest("#rsettings .rs-row")!;
      return { rowUp: row.classList.contains("rs-up"), boxUp: box.closest(".rs-fastin")!.classList.contains("rs-up"), left: !row.contains(document.activeElement) };
    });
    assert.equal(after.left, true, "the rig: the focus left the row");
    assert.deepEqual(after, { rowUp: false, boxUp: false, left: true }, "neither the row nor the box wears the class once the focus is gone (the row's, set while its button held the focus, was left behind when only the box was cleared)");
    // the box-to-row road: the box holds the focus, the pointer crosses the row outside the box and leaves
    const r1 = await focusParked(page, "rs-judgefast", "low");
    assert.equal(r1.tab.landed && r1.tab.focusVisible && r1.up && r1.display === "block", true, "the rig: the box's description shown and placed above " + JSON.stringify(r1.geom));
    await hoverOn(page, "#rsettings .rs-row:has(#rs-judgefast) b");
    await page.mouse.move(5, 5);
    const r2 = await page.evaluate(() => {
      const box = document.getElementById("rs-judgefast")!, row = box.closest("#rsettings .rs-row") as HTMLElement, fast = box.closest(".rs-fastin")!;
      const sub = document.getElementById("rs-judgefast-sub")!, sr = sub.getBoundingClientRect(), rr = row.getBoundingClientRect(), cr = document.querySelector("#rsettings .rs-card")!.getBoundingClientRect();
      return { focused: document.activeElement === box, hovered: row.matches(":hover"), display: getComputedStyle(sub).display, boxUp: fast.classList.contains("rs-up"), rowUp: row.classList.contains("rs-up"), subAboveRow: sr.bottom <= rr.top + 1, pastCard: sr.bottom > cr.bottom + 1 };
    });
    assert.equal(r2.focused && !r2.hovered, true, "the rig: the focus stayed in the box and the pointer left the row");
    assert.equal(r2.display, "block", "the box's description is still shown on the focus");
    assert.equal(r2.boxUp, true, "the row's exit re-placed the BOX too: the box keeps its placement");
    assert.equal(r2.rowUp, false, "and the row wears none (its own popover is hidden)");
    assert.equal(r2.subAboveRow && !r2.pastCard, true, "the box's description stays above the row and inside the card " + JSON.stringify(r2));
    assert.deepEqual(errors, [], "no page error");
  }, 260);
});

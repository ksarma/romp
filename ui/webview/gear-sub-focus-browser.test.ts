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
// browser, which CI installs none of). The legs read the PANEL, not the row: every `.rs-sub` under `#rsettings` that is shown,
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
  const rules = GEAR_CSS.split("\n").filter((l) => !l.trimStart().startsWith("/*") && !l.trimStart().startsWith("*") && /\{/.test(l));
  assert.deepEqual(rules.filter((l) => /:focus-within/.test(l)), [],
    "no rule keys on :focus-within any more: a mouse click satisfies it, and the description then outlives the pointer (the maintainer's round 4, ui-2)");
  assert.equal(rules.join("\n").match(/:focus-visible/g)!.length, 9,
    "nine :focus-visible tokens in rules: the show rule's two, the up twin's two, the box's up twin, the box's stand-down twin, the pair's two twins, and the grip's own rule from before this road");
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
  const panelStand = "#rsettings .rs-card:has(.rs-row:hover .rs-sub, .rs-widget:hover .rs-sub, .rs-mixed:hover) .rs-row:not(:hover) .rs-sub,\n"
    + "#rsettings .rs-card:has(.rs-row:hover .rs-sub, .rs-widget:hover .rs-sub, .rs-mixed:hover) .rs-widget:not(:hover) .rs-sub { display: none; }";
  assert.ok(GEAR_CSS.includes(panelStand),
    "one tooltip across the PANEL: while a row with a description or any mixed mark is hovered, every description outside the hovered row stands down, the focused row's included, the hovered row's own exempt; a .rs-widget branch because the widget rows live in their grids, not in a .rs-row");
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

async function withGear(t: any, tab: string, body: (page: any, errors: string[]) => Promise<void>, height = 320, ctxOpts: Record<string, unknown> = {}, css = GEAR_CSS): Promise<void> {
  if (!pw) { t.skip("playwright is not installed under vscode-extension; the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw.chromium.launch(); }
  catch (e) { t.skip("no playwright browser on this machine; the browser leg needs one (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
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
 *  list, a house dropdown, the login modal), so a leg can read that a click left none behind. */
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
  const menus = (Array.from(document.querySelectorAll("#rsettings .rs-widget-opt div, #rsettings .rs-row div[style*='position:absolute'], #rs-cmap-list, #rs-pal-list")) as HTMLElement[])
    .filter((m) => !m.hidden && getComputedStyle(m).display !== "none" && m.getBoundingClientRect().height > 0).length + (lm && !lm.hidden ? 1 : 0);
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

/** What a host shows when it is the one with something to show: one description, or the Account row's two. */
const ownShown = (h: any) => Array(h.subs).fill(h.host);

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
      // the Account row owns TWO descriptions (gear.js lgLogins gives the stored-logins heading the class rs-sub, under the row
      // that already holds #rs-login-acct), so a hover or a focus there shows two, stacked at the row's bottom: pre-existing on
      // the hover road (the base has the same line and the same rules), inherited by the focus road, disclosed and pinned here
      // as the one host in the panel with more than one; a fix (a class of its own for the heading) reds this pin and then
      // removes the exception, and a second doubled host reds it too
      assert.deepEqual(hosts.filter((h: any) => h.subs > 1).map((h: any) => h.host + ":" + h.subs), tab === "general" ? ["rs-login-btn:2"] : [],
        "the hosts owning more than one description: the Account row alone (its stored-logins heading is an rs-sub), nowhere else");
      for (const h of hosts) {
        await page.mouse.move(5, 5);
        const tabbed = await tabInto(page, h.control);
        assert.equal(tabbed.landed && tabbed.focusVisible, true, `the rig: a Tab landed a :focus-visible focus on ${h.control} (from ${tabbed.prev})`);
        const alone = await shownPanel(page);
        assert.deepEqual(alone.shown, ownShown(h), `a keyboard focus in ${h.host} with the pointer on nothing shows its description alone`);
        for (const o of hosts) {
          if (o === h) continue;
          await hoverOn(page, o.hoverSel);
          const r = await shownPanel(page);
          assert.equal(r.active, h.control, `the rig: the focus stayed on ${h.control} while the pointer rests on ${o.host}`);
          if (o.row === h.row) {
            // the two hosts share a row (a judge row and its Fast mode box): within a row the BOX's description wins whenever
            // either road rests on the box (the box's pair and its twins, both (1,5,0)), one description either way; the one
            // exception to the pointer-wins rule, stated in the sheet beside the rule
            const boxHost = (h.box ? h : o).host;
            assert.deepEqual(r.shown, [boxHost], `focus in ${h.host}, pointer on ${o.host}, one row: the box's description alone (within a row the box wins, whichever road rests on it)`);
          } else {
            assert.deepEqual(r.shown, ownShown(o), `focus in ${h.host}, pointer on ${o.host}: the pointer's description is the one shown (the pointer wins), never the focused row's beside it`);
          }
          assert.equal(r.intersect, false, "and no two shown descriptions of different hosts intersect");
          assert.equal(r.intersectWithin, o.subs > 1, `two descriptions of one host intersect only on the Account row (${o.host})`);
        }
        await page.mouse.move(5, 5);
        assert.deepEqual((await shownPanel(page)).shown, ownShown(h), `the pointer gone, ${h.host}'s description shows again on the focus alone`);
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
        assert.deepEqual((await shownPanel(page)).shown, ownShown(first), "the pointer gone, the focused host's shows again");
      } else t.diagnostic(`the ${pane} pane has no mark span outside the first host's row: the mark road is driven on the Task tracking pane`);
      assert.deepEqual(errors, [], "no page error");
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
          assert.deepEqual(off.shown, ownShown(h), `clicked the text field ${c.id} and left: its row's description shows until the field blurs (the one exception to "never a mouse click", stated in the sheet)`);
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

// THE FOOTER'S RIGHT-HAND DOCK, measured (the held-mail readers PR's review round 2, ui-2; round 3, ui-1).
// feed-clear-all-offer.test.ts and feed-card-prefs.test.ts pin the rules by their text; a pin cannot see where a flex
// item lands. So a real browser lays out the control bar feed.ts mints (the view menu, the tag lens and its chips, the
// session box, and the two actions Clear all and Undo) under feed.css in six states. On a 900 px bar that folds
// nothing: a mixed board (every control shown), Clear all hidden (a board of held messages alone, the state round 2
// made reachable), and the empty board (the left cluster and Clear all hidden, Undo shown for an undoable clear, the
// bar marked .empty-board as renderBody marks it). On a 540 px bar carrying six tag chips, which folds the actions
// onto a row of their own: the mixed board and Clear all hidden. The sixth (round 4) is the bar minted in the OFF
// ARM's order, on the 900 px bar and the 540 px one: the actions' wrapper the first child of an emptied footer and the
// view controls appended after it, the shape a pane builds when its first feed frame is an off frame (below). Undo's
// right edge is the bar's content edge in every state but the empty board, on the wrapped row too, and its left edge
// is the bar's content edge on the empty board; the view button's left edge is the bar's content edge whatever the
// order the controls were appended in.
// The dock lived on Clear all's own margin-left:auto, so with the button hidden Undo slid left beside Search (a 600 px
// jump on a 900 px bar); round 2 moved it to the session box's margin-right:auto, which held on one line and failed on
// a bar that wraps (the actions' own row has no margin on it: Undo's right edge landed near 130 px where 528 is due);
// since round 3 the two actions sit in one wrapper, #feed-actions, whose margin-left:auto docks the pair on whatever
// row the wrap puts it on; since round 4 the wrapper carries its own flex order too, because a wrapper minted FIRST
// with an auto margin and no order pushed the whole bar right (the view button's left edge near 700 px where 12 is
// due, Undo's right near 690 where 888 is due). Runs only where a Playwright browser exists (CI installs none) and
// SKIPS LOUDLY there, the dense-chrome-layout.test.ts pattern; the CI-safe text pins live in
// feed-clear-all-offer.test.ts (the wrapper rule's exact text, and that it carries an order).
// Synthetic markup only: the footer's own controls and invented tag names, no session names.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const CSS_PATH = path.resolve(process.cwd(), "..", "ui", "webview", "feed.css");
const FEED = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "feed.ts"), "utf8");

// The bar as renderBody's ensure* calls mint it, in their order: the view menu, the tag lens with its chip strip after
// it, the session box (button, chip, input, clear), then the two actions, Clear all (order 10) and Undo (order 11).
// The actions' markup FOLLOWS THE MINT as read from feed.ts: ensureClearAll and ensureUndoClear append into the
// #feed-actions wrapper ensureActions mints (round 3), and before that round each appended straight into #feed-foot;
// the fixture takes whichever this feed.ts does, so the bar measured is the bar this build renders and the sheet is
// judged against its own markup, never against a shape from another head. The sixth shape puts the wrapper FIRST
// because feed.ts does: the off arm of the feed frame's arrival (Task tracking off) calls ensureClearAll, whose
// ensureActions appends the wrapper to a #feed-foot that holds nothing yet, and returns before any renderBody, so on a
// pane whose first feed frame is an off frame the wrapper is the footer's first child and every later built frame
// appends the view menu, the tag lens with its chips and the session box after it. feed-clear-all-offer.test.ts pins
// that arm by its source (feedOff set, Clear all hidden, the return), so the shape is a live road and not an invention.
const ACTIONS_WRAPPED = /w\.id = "feed-actions";/.test(FEED) && /makeClearAllBtn\(\); ensureActions\(\)\.appendChild\(b\);/.test(FEED);
const actions = `<button class="fdismiss" id="feed-clearall">Clear all</button><button class="fdismiss ffollow" id="feed-undoclear">Undo</button>`;
const html = `<body>
<div id="feed-list"></div>
<div id="feed-foot">
  <button class="fdismiss ffollow feed-modetoggle" id="feed-viewbtn" aria-haspopup="menu">View ▴</button>
  <button class="fdismiss ffollow feed-modetoggle" id="feed-taglens"><svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M2 7.5 L7.5 2.5 H14 V9 L8.5 14 Z" stroke="currentColor" stroke-width="1.4"/></svg></button><span id="feed-tagchips" style="display:inline-flex;gap:5px;align-items:center;margin-left:2px;"></span>
  <span id="feed-search"><button class="fdismiss ffollow feed-modetoggle" id="feed-search-btn" aria-haspopup="listbox">Sessions ▴</button><span class="fsm-chip" id="feed-sess-chip" hidden></span><input id="feed-search-input" type="search" placeholder="session or host…"><button id="feed-search-clear" type="button" hidden>×</button></span>
  ${ACTIONS_WRAPPED ? `<span id="feed-actions">${actions}</span>` : actions}
</div>
</body>`;
// six tag chips as tag-menu.ts tagChip mints one (its inline style, a lens union's colour), the load that folds a 540 px
// bar: invented tag names
const chipStyle = "display:inline-flex;align-items:center;gap:5px;padding:2px 7px;border-radius:9px;font-size:0.82em;"
  + "border:1px solid #3366cc;color:#3366cc;background:transparent;white-space:nowrap;font-weight:400;letter-spacing:normal;";
const chips = ["parser", "routing", "storage", "billing", "metrics", "release"].map((t) => `<span style="${chipStyle}">${t}</span>`).join("");

type Box = { left: number; right: number; top: number };
type Snap = { undo: Box; clear: Box; search: Box; view: Box; foot: Box; padL: number; padR: number; first: string };
type Measured = { mixed: Snap; hidden: Snap; empty: Snap; wrapMixed: Snap; wrapHidden: Snap; offFirst: Snap; wrapOffFirst: Snap };

// The measurement runs in a standalone driver process (the T225 served-test pattern): the test bundle is
// CommonJS without top-level await, and esbuild must never try to bundle playwright itself.
const DRIVER = `
import { createRequire } from "node:module";
import fs from "node:fs";
const require = createRequire(process.env.EXT_PKG);
let chromium;
try { chromium = require("playwright").chromium; } catch (e) { process.exit(3); }
let browser;
try { browser = await chromium.launch(); } catch (e) { process.exit(3); }
const page = await browser.newPage({ viewport: { width: 900, height: 300 } });
await page.setContent(fs.readFileSync(process.env.HTML_PATH, "utf8"));
await page.addStyleTag({ path: process.env.CSS_PATH });
const CLUSTER = ["feed-viewbtn", "feed-taglens", "feed-tagchips", "feed-search"];
const snapAll = () => page.evaluate(() => {
  const q = (sel) => document.querySelector(sel);
  const box = (el) => { const b = el.getBoundingClientRect(); return { left: b.left, right: b.right, top: b.top }; };
  const foot = q("#feed-foot"), cs = getComputedStyle(foot);
  return { undo: box(q("#feed-undoclear")), clear: box(q("#feed-clearall")), search: box(q("#feed-search")), view: box(q("#feed-viewbtn")), foot: box(foot),
           padL: parseFloat(cs.paddingLeft), padR: parseFloat(cs.paddingRight),
           first: foot.firstElementChild ? foot.firstElementChild.id : "" };   // the footer's DOM order, which the sixth shape varies
});
const show = (id, on) => page.evaluate(([id, on]) => { document.getElementById(id).style.display = on ? "" : "none"; }, [id, on]);
const mixed = await snapAll();
await show("feed-clearall", false);                                  // a board of held messages alone: renderBody's gate hides the button
const hidden = await snapAll();
for (const id of CLUSTER) await show(id, false);                     // the empty board: the count-gated cluster leaves too...
await page.evaluate(() => { document.getElementById("feed-foot").classList.add("empty-board"); });   // ...and renderBody marks the bar
const empty = await snapAll();
if (process.env.SHOT) await page.screenshot({ path: process.env.SHOT + "-empty.png", fullPage: true });
await page.evaluate(() => { document.getElementById("feed-foot").classList.remove("empty-board"); });   // a card is back
for (const id of [...CLUSTER, "feed-clearall"]) await show(id, true);
await page.setViewportSize({ width: 540, height: 300 });             // a narrow pane...
await page.evaluate((chips) => { document.getElementById("feed-tagchips").innerHTML = chips; }, process.env.CHIPS);   // ...under a six-tag lens: the bar folds
const wrapMixed = await snapAll();
if (process.env.SHOT) await page.screenshot({ path: process.env.SHOT + "-wrapped.png", fullPage: true });
await show("feed-clearall", false);
const wrapHidden = await snapAll();
if (process.env.SHOT) await page.screenshot({ path: process.env.SHOT + "-wrapped-hidden.png", fullPage: true });
// THE OFF ARM'S MINT ORDER: back to the 900 px bar, every control shown, no chips (the mixed board's load)...
await show("feed-clearall", true);
await page.setViewportSize({ width: 900, height: 300 });
await page.evaluate(() => { document.getElementById("feed-tagchips").innerHTML = ""; });
// ...and the footer rebuilt as a pane whose FIRST feed frame is an off frame builds it: emptied, the actions appended
// first (the wrapper where this feed.ts mints one; the two buttons on a flat mint), the view menu, the tag lens with its
// chip strip and the session box appended after them by the built frames that follow
await page.evaluate(() => {
  const q = (id) => document.getElementById(id), foot = q("feed-foot");
  const actions = q("feed-actions") ? [q("feed-actions")] : [q("feed-clearall"), q("feed-undoclear")];
  const later = ["feed-viewbtn", "feed-taglens", "feed-tagchips", "feed-search"].map(q);
  foot.replaceChildren();
  for (const n of [...actions, ...later]) foot.appendChild(n);
});
const offFirst = await snapAll();
if (process.env.SHOT) await page.screenshot({ path: process.env.SHOT + "-off-first.png", fullPage: true });
await page.setViewportSize({ width: 540, height: 300 });             // the same DOM order on the bar that folds
await page.evaluate((chips) => { document.getElementById("feed-tagchips").innerHTML = chips; }, process.env.CHIPS);
const wrapOffFirst = await snapAll();
if (process.env.SHOT) await page.screenshot({ path: process.env.SHOT + "-off-first-wrapped.png", fullPage: true });
fs.writeSync(1, "RESULT:" + JSON.stringify({ mixed, hidden, empty, wrapMixed, wrapHidden, offFirst, wrapOffFirst }) + "\\n");
await browser.close();
process.exit(0);
`;

function measure(): Measured | null {
  const os = require("node:os");
  const cp = require("node:child_process");
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "feed-css-footer-"));
  const driver = path.join(dir, "driver.mjs"); fs.writeFileSync(driver, DRIVER);
  const htmlPath = path.join(dir, "page.html"); fs.writeFileSync(htmlPath, html);
  try {
    const p = cp.spawnSync(process.execPath, [driver], { encoding: "utf8", timeout: 120000,   // the running node, never PATH
      env: { ...process.env, EXT_PKG: path.resolve(process.cwd(), "package.json"), HTML_PATH: htmlPath, CSS_PATH: CSS_PATH, CHIPS: chips,
             SHOT: process.env.FEED_CSS_FOOTER_SHOT || "" } });
    if (p.status === 3) return null;                                  // no playwright / no browser here
    if (p.status !== 0) throw new Error("layout driver failed: " + String(p.stderr || p.stdout || p.error || "").slice(-800));
    const line = (p.stdout || "").split("\n").find((l: string) => l.startsWith("RESULT:"));
    if (!line) throw new Error("layout driver printed no result: " + (p.stdout || "").slice(-400));
    return JSON.parse(line.slice("RESULT:".length));
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
}

const m = measure();
const skip = m ? false : "no Playwright browser here: the layout measurement needs one (CI installs none); the CI-safe text pins live in feed-clear-all-offer.test.ts";
const near = (got: number, want: number, what: string, tol = 0.5) =>
  assert.ok(Math.abs(got - want) <= tol, what + ": " + got.toFixed(2) + "px, wanted about " + want.toFixed(2) + "px");

test("a mixed board: the actions dock at the bar's right content edge, Clear all then Undo, on one row with the view controls", { skip }, () => {
  const { mixed } = m!;
  near(mixed.undo.right, mixed.foot.right - mixed.padR, "Undo's right edge is the bar's content edge");
  assert.ok(mixed.clear.right < mixed.undo.left, "Clear all stands left of Undo");
  assert.ok(mixed.search.right < mixed.clear.left, "the session box stands left of the actions");
  assert.equal(mixed.undo.top, mixed.search.top, "one row: the 900 px bar folds nothing");
});

test("Clear all hidden (a board of held messages alone): Undo keeps the same right edge, not a slide left beside Search", { skip }, () => {
  const { mixed, hidden } = m!;
  near(hidden.undo.right, mixed.undo.right, "Undo's right edge with Clear all hidden equals its edge with Clear all shown");
  near(hidden.undo.right, hidden.foot.right - hidden.padR, "and it is the bar's content edge");
  assert.ok(hidden.undo.left - hidden.search.right > 100, "Undo is docked away from the session box, not beside it: gap " + (hidden.undo.left - hidden.search.right).toFixed(1) + "px");
  assert.equal(hidden.undo.top, hidden.search.top, "still one row");
});

test("the empty board (Undo alone, for an undoable clear; the bar marked .empty-board as renderBody marks it): Undo stays at the bar's left content edge, as before", { skip }, () => {
  const { empty } = m!;
  near(empty.undo.left, empty.foot.left + empty.padL, "Undo's left edge is the bar's content edge");
});

test("a bar that WRAPS (540 px, six tag chips): the actions fold onto a row of their own and dock at ITS right content edge, Clear all then Undo, with the view controls leading the row above", { skip }, () => {
  // ui-1 (round 3): the round 2 dock, margin-right:auto on the session box, sat on the row above the fold and docked
  // nothing on the actions' own row, so Clear all and Undo sat flush left there (Undo's right edge near 130 px on this
  // bar); the wrapper's margin-left:auto travels with the pair onto whatever row it lands on
  const { wrapMixed: w } = m!;
  assert.ok(w.undo.top > w.search.top, "the bar folded: the actions sit on a row below the session box (the load this case needs; a wider bar would measure nothing)");
  assert.equal(w.clear.top, w.undo.top, "Clear all and Undo share the wrapped row: the pair wraps as one item");
  assert.ok(w.clear.right < w.undo.left, "Clear all then Undo");
  near(w.undo.right, w.foot.right - w.padR, "Undo's right edge is the bar's content edge on the wrapped row");
  near(w.view.left, w.foot.left + w.padL, "the view button leads the first row at the bar's left content edge");
  assert.ok(w.view.top < w.undo.top, "and that row is above the actions'");
});

test("a bar that wraps with Clear all hidden: Undo keeps the bar's right content edge on whatever row it lands on", { skip }, () => {
  const { wrapHidden: w } = m!;
  near(w.undo.right, w.foot.right - w.padR, "Undo's right edge is the bar's content edge");
  near(w.view.left, w.foot.left + w.padL, "the view button keeps the left content edge of the first row");
});

// THE OFF ARM'S MINT ORDER (round 4). Round 3 moved the dock's auto margin onto the wrapper and left the flex order on
// the two buttons INSIDE it, so among the footer's own children every item sat at the default order 0 and DOM order
// decided the bar for the first time; the buttons' order 10 and 11 had bought the immunity while the margin rode them
// directly. A wrapper minted first with margin-left:auto then pushed everything after it right: nothing at the left
// content edge, nothing docked at the right, Clear all and Undo left of View and Sessions, for the life of the page.
// The wrapper's own order sorts it after the view controls whatever the DOM order; these two cases vary the DOM order
// and expect the bar the normal order lays out, and each first checks it measured the shape it claims.
const EDGES = ["view", "search", "clear", "undo"] as const;
const actionsLead = ACTIONS_WRAPPED ? "feed-actions" : "feed-clearall";

test("the bar minted in the OFF ARM's order (the actions' wrapper the first child of an empty footer, the view controls appended after it): the view button at the left content edge and Undo docked at the right, the same bar as the normal order", { skip }, () => {
  const { mixed, offFirst: o } = m!;
  assert.equal(o.first, actionsLead, "the shape measured is the off arm's: the actions lead the footer's DOM");
  assert.equal(mixed.first, "feed-viewbtn", "and the normal shape's DOM leads with the view button, so the one thing varied is the order");
  near(o.view.left, o.foot.left + o.padL, "the view button's left edge is the bar's left content edge, with the actions minted first (Undo's right edge "
    + o.undo.right.toFixed(2) + "px against the content edge " + (o.foot.right - o.padR).toFixed(2) + "px)");
  near(o.undo.right, o.foot.right - o.padR, "Undo's right edge is the bar's right content edge, with the actions minted first");
  assert.ok(o.clear.right < o.undo.left, "Clear all stands left of Undo");
  assert.ok(o.search.right < o.clear.left, "the session box stands left of the actions: the actions dock right, they do not lead");
  assert.equal(o.undo.top, o.view.top, "one row: the 900 px bar folds nothing");
  for (const k of EDGES) {
    near(o[k].left, mixed[k].left, k + "'s left edge equals the normal order's");
    near(o[k].right, mixed[k].right, k + "'s right edge equals the normal order's");
  }
});

test("the off arm's order on a bar that WRAPS (540 px, six tag chips): the view controls lead the first row and the actions fold onto a row of their own, docked right, as in the normal order", { skip }, () => {
  const { wrapMixed, wrapOffFirst: w } = m!;
  assert.equal(w.first, actionsLead, "the shape measured is the off arm's: the actions lead the footer's DOM");
  const tops = EDGES.map((k) => w[k].top);
  assert.ok(Math.max(...tops) > Math.min(...tops), "the bar folded: the controls sit on two rows (the load this case needs; a wider bar would measure nothing)");
  assert.ok(w.undo.top > w.view.top, "the actions sit on a row BELOW the view button, with the actions minted first: Undo's row top " + w.undo.top.toFixed(2)
    + "px, the view button's " + w.view.top.toFixed(2) + "px (a first child with an auto margin and no order leads the first row instead of folding under the view controls)");
  near(w.view.left, w.foot.left + w.padL, "the view button leads the first row at the bar's left content edge, with the actions minted first");
  assert.equal(w.clear.top, w.undo.top, "Clear all and Undo share the wrapped row: the pair wraps as one item");
  assert.ok(w.clear.right < w.undo.left, "Clear all then Undo");
  near(w.undo.right, w.foot.right - w.padR, "Undo's right edge is the bar's content edge on the wrapped row, with the actions minted first");
  for (const k of EDGES) {
    near(w[k].left, wrapMixed[k].left, k + "'s left edge equals the normal order's on the wrapped bar");
    near(w[k].top, wrapMixed[k].top, k + "'s row equals the normal order's on the wrapped bar");
  }
});

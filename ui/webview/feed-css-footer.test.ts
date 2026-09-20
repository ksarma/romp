// THE FOOTER'S RIGHT-HAND DOCK, measured (the held-mail readers PR's review round 2, ui-2). feed-clear-all-offer.test.ts and
// feed-card-prefs.test.ts pin the rules by their text; a pin cannot see where a flex item lands. So a real browser lays out
// the control bar feed.ts mints (the view menu, the tag lens and its chips, the session box, Clear all, Undo) under
// feed.css in three states: a mixed board (every control shown), Clear all hidden (a board of held messages alone, the
// state the review made reachable), and the empty board (the left cluster and Clear all hidden, Undo shown for an
// undoable clear). Undo's right edge is the bar's content edge in the first two states, and the same in both, and its
// left edge is the bar's content edge on the empty board, as before the review. The dock lived on Clear all's own
// margin-left:auto, so with the button hidden Undo slid left beside Search (a 600 px jump on a 900 px bar); it rides
// the session box's margin-right:auto now. Runs only where a Playwright browser exists (CI installs none) and SKIPS
// LOUDLY there, the dense-chrome-layout.test.ts pattern; the CI-safe text pins live in feed-clear-all-offer.test.ts.
// Synthetic markup only: the footer's own controls, no session names.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const CSS_PATH = path.resolve(process.cwd(), "..", "ui", "webview", "feed.css");

// the bar as renderBody's ensure* calls mint it, in their order: the view menu, the tag lens with its chip strip after
// it, the session box (button, chip, input, clear), then Clear all (order 10) and Undo (order 11)
const html = `<body>
<div id="feed-list"></div>
<div id="feed-foot">
  <button class="fdismiss ffollow feed-modetoggle" id="feed-viewbtn" aria-haspopup="menu">View ▴</button>
  <button class="fdismiss ffollow feed-modetoggle" id="feed-taglens"><svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M2 7.5 L7.5 2.5 H14 V9 L8.5 14 Z" stroke="currentColor" stroke-width="1.4"/></svg></button><span id="feed-tagchips" style="display:inline-flex;gap:5px;align-items:center;margin-left:2px;"></span>
  <span id="feed-search"><button class="fdismiss ffollow feed-modetoggle" id="feed-search-btn" aria-haspopup="listbox">Sessions ▴</button><span class="fsm-chip" id="feed-sess-chip" hidden></span><input id="feed-search-input" type="search" placeholder="session or host…"><button id="feed-search-clear" type="button" hidden>×</button></span>
  <button class="fdismiss" id="feed-clearall">Clear all</button>
  <button class="fdismiss ffollow" id="feed-undoclear">Undo</button>
</div>
</body>`;

type Box = { left: number; right: number; top: number };
type Snap = { undo: Box; clear: Box; search: Box; foot: Box; padL: number; padR: number };
type Measured = { mixed: Snap; hidden: Snap; empty: Snap };

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
const out = await page.evaluate(() => {
  const q = (sel) => document.querySelector(sel);
  const box = (el) => { const b = el.getBoundingClientRect(); return { left: b.left, right: b.right, top: b.top }; };
  const foot = q("#feed-foot"), cs = getComputedStyle(foot);
  const snap = () => ({ undo: box(q("#feed-undoclear")), clear: box(q("#feed-clearall")), search: box(q("#feed-search")), foot: box(foot),
                        padL: parseFloat(cs.paddingLeft), padR: parseFloat(cs.paddingRight) });
  const mixed = snap();
  q("#feed-clearall").style.display = "none";                       // a board of held messages alone: renderBody's gate hides the button
  const hidden = snap();
  for (const id of ["feed-viewbtn", "feed-taglens", "feed-tagchips", "feed-search"]) q("#" + id).style.display = "none";   // the empty board: the count-gated cluster leaves too
  const empty = snap();
  return { mixed, hidden, empty };
});
if (process.env.SHOT) await page.screenshot({ path: process.env.SHOT, fullPage: true });
fs.writeSync(1, "RESULT:" + JSON.stringify(out) + "\\n");
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
      env: { ...process.env, EXT_PKG: path.resolve(process.cwd(), "package.json"), HTML_PATH: htmlPath, CSS_PATH: CSS_PATH,
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

test("the empty board (Undo alone, for an undoable clear): Undo stays at the bar's left content edge, as before", { skip }, () => {
  const { empty } = m!;
  near(empty.undo.left, empty.foot.left + empty.padL, "Undo's left edge is the bar's content edge");
});

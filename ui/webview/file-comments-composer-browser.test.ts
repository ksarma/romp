// The comment box under a REAL renderer (plans/file-review.md, "The composer follow-on (2026-09-07)"): headless
// Chromium and Firefox lay the worktree's textarea out under the sheet's own .fc-input rule and press its keys. This
// is the leg no stand-in can stand in for — the stand-in tests set scrollHeight by hand and cannot cap anything:
// the browser decides how tall three rows are, whether autosizeNote's height lands where the sheet's max-height caps
// it at twelve rows and scrolls past that, and what a real Enter does in a textarea whose keydown listener left it
// alone (a newline), against a real Ctrl+Enter (no newline; the save). Skips LOUDLY without a playwright browser
// (CI installs none), as the region layer's browser leg does. Synthetic values only: typed placeholder lines.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";

const requireCjs = createRequire(__filename);
const EXT = process.cwd();                                        // npm test runs in vscode-extension
const UI = path.resolve(EXT, "..", "ui", "webview");
const FEED = fs.readFileSync(path.join(UI, "feed.css"), "utf8");

/** The panel's box helpers, bundled as the webview build bundles them (in memory), handed to the page as window.__romp. */
function bundle(): string {
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    stdin: {
      contents: 'import { autosizeNote, composerKeyAction, NOTE_ROWS, NOTE_MAX_ROWS } from "./file-comments";\n(window as any).__romp = { autosizeNote, composerKeyAction, NOTE_ROWS, NOTE_MAX_ROWS };\n',
      resolveDir: UI, loader: "ts", sourcefile: "composer-probe.ts",
    },
    bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], logLevel: "silent",
  });
  return r.outputFiles[0].text;
}
/** The whole file-comments block of the sheet, as the feed page loads it (styles.css is pinned byte-equal to it). */
function sheet(): string {
  const a = FEED.indexOf("/* ── file comments panel (plans/file-review.md Slice 1; file-comments.ts)");
  const b = FEED.indexOf("/* ── end file comments panel ── */");
  assert.ok(a >= 0 && b > a, "the file-comments block's markers in feed.css");
  return FEED.slice(a, b);
}
// the tokens the block reads, resolved to plain values here (a file:// harness loads no theme), and a 13px body
const PAGE = `<!DOCTYPE html><html><head><meta charset=utf-8><style>
:root { --box-border: #555; --input-bg: #222; --fg: #ccc; --dim: #999; --accent: #9cd2ff; --card-border: #444; }
body { margin: 0; padding: 20px; font: 13px sans-serif; color: var(--fg); background: #1e1e1e; }
.fileview-aside { width: 340px; }
${sheet()}</style></head><body><div class="fileview-aside"><div class="fc-panel"><div class="fc-composer">
<div class="fc-composer-ref"><span class="fc-note">On this file</span></div>
<textarea class="fc-input" rows="3" aria-label="Comment text" placeholder="Your comment"></textarea>
<div class="fc-actions"><span class="fc-note fc-hint">Ctrl+Enter saves; Enter adds a line</span><button class="fileview-btn" type="button">Save</button><button class="fileview-btn" type="button">Cancel</button></div>
</div></div></div><script src="/dist/composer.js"></script></body></html>`;

type Box = { height: number; clientHeight: number; scrollHeight: number; lineHeight: number; padBorder: number; width: number; asideWidth: number; resize: string; overflowY: string };

/** Wire the page's box the way the panel wires its own — keydown through composerKeyAction, input through autosizeNote —
 *  and report its layout. */
function setup(page: any): Promise<Box> {
  return page.evaluate(() => {
    const w = window as any;
    const ta = document.querySelector("textarea.fc-input") as HTMLTextAreaElement;
    const calls: string[] = []; w.__calls = calls;
    ta.addEventListener("keydown", (e) => {
      const act = w.__romp.composerKeyAction(e);
      if (act === "save") { e.preventDefault(); calls.push("save"); }
      else if (act === "cancel") { e.preventDefault(); e.stopPropagation(); calls.push("cancel"); }
    });
    ta.addEventListener("input", () => { const h = w.__romp.autosizeNote(ta); calls.push("sized:" + h); });
    ta.focus();
    return w.__measure();
  });
}
const MEASURE = `window.__measure = () => {
  const ta = document.querySelector("textarea.fc-input");
  const cs = getComputedStyle(ta);
  const num = (v) => parseFloat(v) || 0;
  return { height: ta.getBoundingClientRect().height, clientHeight: ta.clientHeight, scrollHeight: ta.scrollHeight, lineHeight: num(cs.lineHeight),
    padBorder: num(cs.paddingTop) + num(cs.paddingBottom) + num(cs.borderTopWidth) + num(cs.borderBottomWidth),
    width: ta.getBoundingClientRect().width, asideWidth: document.querySelector(".fc-panel").getBoundingClientRect().width, resize: cs.resize, overflowY: cs.overflowY };
};`;
const measure = (page: any): Promise<Box> => page.evaluate(() => (window as any).__measure());
const calls = (page: any): Promise<string[]> => page.evaluate(() => (window as any).__calls.splice(0));
const value = (page: any): Promise<string> => page.evaluate(() => (document.querySelector("textarea.fc-input") as HTMLTextAreaElement).value);
const near = (a: number, b: number, msg: string) => assert.ok(Math.abs(a - b) < 1.5, msg + ": " + a + " vs " + b);

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

async function inBrowser(t: any, name: "chromium" | "firefox", body: (page: any) => Promise<void>): Promise<void> {
  if (!pw) { t.skip("playwright is not installed under vscode-extension — the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw[name].launch(); }
  catch (e) { t.skip("no playwright " + name + " on this box — this leg needs it (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  const errors: string[] = [];
  try {
    const js = bundle() + "\n" + MEASURE;
    const page = await browser.newPage({ viewport: { width: 1000, height: 900 } });
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    await page.route("http://romp.test/**", (route: any) => {
      const u = new URL(route.request().url());
      if (u.pathname === "/page") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: PAGE });
      if (u.pathname === "/dist/composer.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: js });
      return route.fulfill({ status: 404, body: "" });
    });
    await page.goto("http://romp.test/page");
    await page.waitForFunction(() => !!(window as any).__romp && !!(window as any).__measure);
    await body(page);
    assert.deepEqual(errors, [], "no script error in the page");
  } finally { await browser.close(); }
}

for (const name of ["chromium", "firefox"] as const) {
  test("in " + name + ": three rows to start, full width, draggable; the box grows a row per line to twelve, then scrolls; Enter is a newline and Ctrl+Enter is the save", async (t) => {
    await inBrowser(t, name, async (page) => {
      const { NOTE_ROWS, NOTE_MAX_ROWS } = await page.evaluate(() => ({ NOTE_ROWS: (window as any).__romp.NOTE_ROWS, NOTE_MAX_ROWS: (window as any).__romp.NOTE_MAX_ROWS }));
      const rows = (m: Box, n: number) => n * m.lineHeight + m.padBorder;
      const m0 = await setup(page);
      assert.ok(m0.lineHeight > 0, "the sheet's line-height resolved");
      near(m0.padBorder, 12, "5+5 padding and 1+1 border, the 12px the sheet's calc() counts");
      near(m0.height, rows(m0, NOTE_ROWS), "empty: exactly NOTE_ROWS rows tall");
      near(m0.width, m0.asideWidth - 24, "the panel's full width (its 12px side padding aside)");
      assert.equal(m0.resize, "vertical", "the person may drag it taller or shorter");
      assert.equal(m0.overflowY, "auto");
      // Enter is the browser's newline: the value gains lines, the box a row per line
      await page.keyboard.type("one\ntwo\nthree\nfour\nfive");
      assert.equal(await value(page), "one\ntwo\nthree\nfour\nfive", "five lines: four Enters went in as newlines");
      const m5 = await measure(page);
      near(m5.height, rows(m5, 5), "five rows tall, grown by autosizeNote on each input");
      assert.ok(m5.scrollHeight <= m5.clientHeight + 1, "nothing to scroll: every line is on screen");
      const c5 = await calls(page);
      assert.equal(c5.filter((x) => x === "save").length, 0, "no save fired from a plain Enter");
      assert.ok(c5.every((x) => x.startsWith("sized:")), JSON.stringify(c5));
      // past the cap the box stops growing and scrolls
      await page.keyboard.type("\nsix\nseven\neight\nnine\nten\neleven\ntwelve\nthirteen\nfourteen\nfifteen");
      const m15 = await measure(page);
      near(m15.height, rows(m15, NOTE_MAX_ROWS), "fifteen lines: capped at NOTE_MAX_ROWS rows by the sheet's max-height");
      assert.ok(m15.scrollHeight > m15.clientHeight + m15.lineHeight, "…and the rest scrolls inside the box");
      assert.equal((await value(page)).split("\n").length, 15);
      await calls(page);
      // the chord: no newline goes in, the save fires
      await page.keyboard.press("Control+Enter");
      assert.deepEqual(await calls(page), ["save"], "Ctrl+Enter is the save, once");
      assert.equal((await value(page)).split("\n").length, 15, "and inserted no line");
      // a shorter comment shrinks the box back, never under the floor
      await page.evaluate(() => { const ta = document.querySelector("textarea.fc-input") as HTMLTextAreaElement; ta.value = "one"; ta.dispatchEvent(new Event("input")); });
      const m1 = await measure(page);
      near(m1.height, rows(m1, NOTE_ROWS), "one line: back to the NOTE_ROWS floor (the sheet's min-height)");
      await calls(page);
      // Escape is the cancel
      await page.keyboard.press("Escape");
      assert.deepEqual(await calls(page), ["cancel"], "Escape cancels");
    });
  });
}

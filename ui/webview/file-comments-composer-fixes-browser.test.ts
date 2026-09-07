// The composer follow-on's review fixes under a REAL renderer (plans/file-review.md, "The composer follow-on
// (2026-09-07)"; the 2026-09-07 review), the two the stand-in cannot lay out or gesture: headless Chromium and Firefox
// under the worktree's sheet. One, the panel's aside is a scroll container (feed.css .fileview-aside, overflow: auto) and
// short on the phone and in a short pane; autosizeComposer's `height: auto` measurement collapsed a grown box for one layout,
// in which the browser clamped a scrolled aside toward its top, so every keystroke at the twelve-row cap jumped the panel
// by nine rows — the leg scrolls a real 300px aside to its bottom and types. Two, the REAL panel (fileCommentsAction.mount,
// a stubbed viewer context) takes a real mouse drag on the box's resize handle BEFORE a word is typed: the browser writes
// the inline height and fires no input, and the first keystroke used to snap the box back to three rows. Three, the same
// real panel at the twelve-row cap: the cap is autosizeComposer's (COMPOSER_MAX_ROWS of the box's computed line-height plus
// its padding), not a max-height in the sheet — the drag and the autosize write the same inline height, so a sheet clamp
// capped the drag too, and a drag at the cap could not make the box taller yet turned autosize off, the box frozen at the
// cap for the rest of the comment (the review consolidation). The leg types past the cap, drags the handle 100px, and
// types again. Skips LOUDLY without a playwright browser (CI installs none), as the composer's other browser leg does.
// Synthetic values only: the notes-api world, placeholder ids and lines.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";

const requireCjs = createRequire(__filename);
const EXT = process.cwd();                                        // npm test runs in vscode-extension
const UI = path.resolve(EXT, "..", "ui", "webview");
const FEED = fs.readFileSync(path.join(UI, "feed.css"), "utf8");

/** The module, bundled as the webview build bundles it (in memory), handed to the page as window.__romp. */
function bundle(): string {
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    stdin: {
      contents: 'import { autosizeComposer, fileCommentsAction, COMPOSER_ROWS, COMPOSER_MAX_ROWS } from "./file-comments";\n(window as any).__romp = { autosizeComposer, fileCommentsAction, COMPOSER_ROWS, COMPOSER_MAX_ROWS };\n',
      resolveDir: UI, loader: "ts", sourcefile: "composer-fixes-probe.ts",
    },
    bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], logLevel: "silent",
  });
  return r.outputFiles[0].text;
}
/** The whole file-comments block of the sheet (styles.css is pinned byte-equal to it), plus the viewer's own layout rules
 *  for the row the panel sits in — the aside is the scroll container this leg is about. */
function sheet(): string {
  const a = FEED.indexOf("/* ── file comments panel (plans/file-review.md Slice 1; file-comments.ts)");
  const b = FEED.indexOf("/* ── end file comments panel ── */");
  assert.ok(a >= 0 && b > a, "the file-comments block's markers in feed.css");
  const rule = (head: string): string => {
    const m = FEED.match(new RegExp("\\n(" + head.replace(/[.]/g, "\\.") + " \\{[^}]*\\})"));
    assert.ok(m, head + " in feed.css");
    return m![1];
  };
  return [rule(".fileview-main"), rule(".fileview-aside"), rule(".fileview-body"), FEED.slice(a, b)].join("\n");
}
// the tokens the block reads, resolved to plain values here (a file:// harness loads no theme), and a 13px body
const HEAD = `<!DOCTYPE html><html><head><meta charset=utf-8><style>
:root { --box-border: #555; --input-bg: #222; --fg: #ccc; --dim: #999; --accent: #9cd2ff; --card-border: #444; --bg: #1e1e1e; }
body { margin: 0; font: 13px sans-serif; color: var(--fg); background: #1e1e1e; }
.fileview-btn { font: inherit; padding: 2px 8px; }
${sheet()}</style></head><body>`;
const COMPOSER = `<div class="fc-composer">
<div class="fc-composer-ref"><span class="fc-note">On this file</span></div>
<textarea class="fc-input" rows="3" aria-label="Comment text" placeholder="Your comment"></textarea>
<div class="fc-actions"><span class="fc-note fc-hint">Ctrl+Enter saves; Enter adds a line</span><button class="fileview-btn" type="button">Save</button><button class="fileview-btn" type="button">Cancel</button></div>
</div>`;
// leg one: the panel's aside as file-view.ts builds it (one node wearing .fileview-aside and .fc-panel) in a 300px row, the
// sections in the panel's order — head, composer, cards, send — so the Save row sits just under a short viewport at the cap
const PAGE_ASIDE = HEAD + `<div class="fileview-main" style="height: 300px"><div class="fileview-body"></div>
<div class="fileview-aside fc-panel">
<div class="fc-sec-head"><div class="fc-row"><span class="fc-note">notes-api · docs/report.md</span></div><div class="fc-row"><button class="fileview-btn" type="button">Comment on this file</button></div></div>
${COMPOSER}
<div class="fc-sec-cards"><div class="fc-empty">No comments yet. Comment on this file to leave one.</div></div>
<div class="fc-sec-send"><button class="fileview-btn" type="button">Send to session</button></div>
</div></div><script src="/dist/composer.js"></script></body></html>`;
// leg two: the viewer's row with an empty body, for the real panel to hang its aside on
const PAGE_PANEL = HEAD + `<div id="romp-fileview"><div class="fileview-main" style="height: 600px"><div class="fileview-body"><div class="fileview-md"><p>Intro text here.</p></div></div></div></div>
<script src="/dist/composer.js"></script></body></html>`;

/** The page's side of leg one: the box wired to autosizeComposer the way the panel wires its own, and the readings. */
const ASIDE_JS = `window.__wire = () => {
  const ta = document.querySelector("textarea.fc-input");
  ta.addEventListener("input", () => { window.__romp.autosizeComposer(ta); });
  ta.focus();
};
window.__read = () => {
  const ta = document.querySelector("textarea.fc-input");
  const aside = document.querySelector(".fileview-aside");
  return { height: ta.getBoundingClientRect().height, inline: ta.style.height, scrollTop: aside.scrollTop, scrollMax: aside.scrollHeight - aside.clientHeight, lines: ta.value.split("\\n").length };
};
window.__toBottom = () => { const aside = document.querySelector(".fileview-aside"); aside.scrollTop = 1e6; return aside.scrollTop; };
window.__scrollTo = (top) => { const aside = document.querySelector(".fileview-aside"); aside.scrollTop = top; return aside.scrollTop; };
window.__input = () => { document.querySelector("textarea.fc-input").dispatchEvent(new Event("input")); };
/* the defect itself, for the leg's own sensitivity: the bare collapse, no hold, then everything put back */
window.__bareCollapse = () => {
  const ta = document.querySelector("textarea.fc-input"); const aside = document.querySelector(".fileview-aside");
  const top = aside.scrollTop; const h = ta.style.height;
  ta.style.height = "auto"; void ta.scrollHeight; const clamped = aside.scrollTop;
  ta.style.height = h; aside.scrollTop = top;
  return { top, clamped, after: aside.scrollTop };
};`;
/** The page's side of leg two: the real panel mounted on a stubbed viewer context (the driven harness's, in the page),
 *  its status asks answered by hand through the window message the host would post. */
const PANEL_JS = `window.__posted = [];
window.__mount = () => {
  const main = document.querySelector(".fileview-main");
  const body = main.querySelector(".fileview-body");
  let aside = null;
  const noop = () => {};
  const ctx = {
    path: "/repo/notes-api/docs/report.md", sid: "11111111-2222-3333-4444-555555555555", todoId: null,
    body: () => body, mode: () => "rendered", text: () => null, mtimeNs: () => "1757145600000000001",
    media: () => null, mediaElement: () => null, renderedImages: () => [], pdfPages: () => [], identity: () => ({ name: "api", color: null }),
    onRendered: noop, onSelection: noop, onSaved: noop, onClose: noop,
    post: (m) => { window.__posted.push(m); }, ensureEditingAllowed: async () => true, setEditBlocked: noop, editing: () => false, setTrackedEdit: noop,
    aside: (el) => { if (el) { el.classList.add("fileview-aside"); aside = el; main.appendChild(el); } else if (aside) { aside.remove(); aside = null; } },
    setMode: noop, scrollToOffset: noop, reload: noop,
  };
  const unit = window.__romp.fileCommentsAction.mount(ctx);
  document.body.appendChild(unit);
  return unit;
};
window.__answer = () => {
  const last = window.__posted[window.__posted.length - 1];
  if (!last || last.verb !== "status") return null;
  window.dispatchEvent(new MessageEvent("message", { data: {
    type: "fileCommentsResult", reqId: last.reqId, verb: "status", root: "/repo/notes-api", storePath: "/repo/notes-api/.trackchanges/docs%2Freport.md.json",
    trackedBy: { kind: "file", entry: "docs/report.md" }, agentTooling: "present",
    fileMtimeNs: "1757145600000000001", storeMtimeNs: "1757145600000000002", configMtimeNs: "1757145600000000003",
    store: { v: 3, path: "docs/report.md", suggestions: [], comments: [] }, hunks: [], log: [],
    unsent: { comments: [], replies: [], accepted: 0, rejected: 0, watermark: null },
  } }));
  return last.reqId;
};
window.__box = () => {
  const ta = document.querySelector(".fc-panel textarea.fc-input");
  const r = ta.getBoundingClientRect();
  const cs = getComputedStyle(ta);
  const num = (v) => parseFloat(v) || 0;
  return { inline: ta.style.height, height: r.height, right: r.right, bottom: r.bottom, value: ta.value, focused: document.activeElement === ta, hidden: ta.closest(".fc-composer").hidden,
    scrollHeight: ta.scrollHeight, clientHeight: ta.clientHeight, lineHeight: num(cs.lineHeight),
    padBorder: num(cs.paddingTop) + num(cs.paddingBottom) + num(cs.borderTopWidth) + num(cs.borderBottomWidth) };
};`;

type Read = { height: number; inline: string; scrollTop: number; scrollMax: number; lines: number };
type BoxRead = { inline: string; height: number; right: number; bottom: number; value: string; focused: boolean; hidden: boolean; scrollHeight: number; clientHeight: number; lineHeight: number; padBorder: number };
const near = (a: number, b: number, msg: string) => assert.ok(Math.abs(a - b) < 1.5, msg + ": " + a + " vs " + b);
const px = (v: string): number => { assert.match(v, /^\d+(\.\d+)?px$/, "an inline pixel height, got " + JSON.stringify(v)); return parseFloat(v); };
/** A real mouse drag on the box's resize handle (its bottom-right corner), dy pixels down: the browser writes the inline
 *  height and fires no input event. */
async function drag(page: any, from: BoxRead, dy: number): Promise<void> {
  await page.mouse.move(from.right - 6, from.bottom - 6);
  await page.mouse.down();
  await page.mouse.move(from.right - 6, from.bottom - 6 + dy, { steps: 8 });
  await page.mouse.up();
}

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

async function inBrowser(t: any, name: "chromium" | "firefox", html: string, js: string, body: (page: any) => Promise<void>): Promise<void> {
  if (!pw) { t.skip("playwright is not installed under vscode-extension — the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw[name].launch(); }
  catch (e) { t.skip("no playwright " + name + " on this box — this leg needs it (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  const errors: string[] = [];
  try {
    const script = bundle() + "\n" + js;
    const page = await browser.newPage({ viewport: { width: 1000, height: 900 } });
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    await page.route("http://romp.test/**", (route: any) => {
      const u = new URL(route.request().url());
      if (u.pathname === "/page") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: html });
      if (u.pathname === "/dist/composer.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: script });
      return route.fulfill({ status: 404, body: "" });
    });
    await page.goto("http://romp.test/page");
    await page.waitForFunction(() => !!(window as any).__romp);
    await body(page);
    assert.deepEqual(errors, [], "no script error in the page");
  } finally { await browser.close(); }
}

for (const name of ["chromium", "firefox"] as const) {
  test("in " + name + ": a keystroke at the twelve-row cap leaves a scrolled aside where the person scrolled it — autosizeComposer's measurement holds the scroll", async (t) => {
    await inBrowser(t, name, PAGE_ASIDE, ASIDE_JS, async (page) => {
      const read = (): Promise<Read> => page.evaluate(() => (window as any).__read());
      const { COMPOSER_MAX_ROWS } = await page.evaluate(() => ({ COMPOSER_MAX_ROWS: (window as any).__romp.COMPOSER_MAX_ROWS }));
      await page.evaluate(() => (window as any).__wire());
      // fourteen lines: the box is at the cap, and the aside — 300px tall — has more content than it can show
      await page.keyboard.type(Array.from({ length: 14 }, (_, i) => "line " + (i + 1)).join("\n"));
      const cap = await read();
      assert.equal(cap.lines, 14);
      near(px(cap.inline), cap.height, "autosizeComposer wrote the cap itself (" + cap.inline + "), the box renders at it (" + cap.height + "px) — no sheet clamp under a taller inline height");
      assert.ok(cap.height < 14 * 16 && cap.height > 12 * 13, "twelve rows, not fourteen: the box is at the cap (" + cap.height + "px)");
      assert.ok(cap.scrollMax > 60, "the aside scrolls: its content overflows the 300px row by " + cap.scrollMax + "px");
      // the person scrolls to the bottom (the Save row, the cards) — the case the phone's short aside makes common
      const bottom: number = await page.evaluate(() => (window as any).__toBottom());
      near(bottom, cap.scrollMax, "scrolled to the bottom");
      // the leg's own sensitivity: the bare collapse the measurement performs does clamp this aside, in this engine
      const bare = await page.evaluate(() => (window as any).__bareCollapse());
      assert.ok(bare.clamped < bare.top - 30, "height: auto with no hold clamps the scrolled aside (the defect; " + bare.top + " -> " + bare.clamped + ") — the hold below is what keeps it");
      near(bare.after, bottom, "put back for the real test");
      // the mechanism under test: an input event runs autosizeComposer — the scroll must not move
      await page.evaluate(() => (window as any).__input());
      const held = await read();
      near(held.scrollTop, bottom, "autosizeComposer left the aside's scroll where it was");
      assert.equal(held.inline, cap.inline, "…and the box at the cap");
      // a real keystroke, the caret at the end of the last line (in view at the bottom): the same
      await page.keyboard.type("x");
      const typed = await read();
      near(typed.scrollTop, bottom, "a typed character at the cap moves the aside by nothing");
      assert.equal(typed.inline, cap.inline);
      // scrolled to the middle rather than the bottom: held there as well
      const mid: number = await page.evaluate((v: number) => (window as any).__scrollTo(v), Math.round(bottom / 2));
      assert.ok(mid > 0 && mid < bottom);
      await page.evaluate(() => (window as any).__input());
      near((await read()).scrollTop, mid, "held at a middle position too");
      assert.equal(COMPOSER_MAX_ROWS, 12);
    });
  });

  test("in " + name + ": the real panel — a resize drag on the box BEFORE the first keystroke stands through the typing that follows; Cancel resets it; no drag, the box follows its content", async (t) => {
    await inBrowser(t, name, PAGE_PANEL, PANEL_JS, async (page) => {
      const box = (): Promise<BoxRead> => page.evaluate(() => (window as any).__box());
      const answer = (): Promise<string | null> => page.evaluate(() => (window as any).__answer());
      await page.evaluate(() => (window as any).__mount());
      assert.ok(await answer(), "the probe's status ask, answered");                       // the unit shows
      await page.click(".fileview-fc button");                                              // Comments: the panel opens
      assert.ok(await answer(), "the open's status ask, answered");
      await page.click('.fc-panel [data-act="fcfile"]');                                    // Comment on this file
      const b0 = await box();
      assert.equal(b0.hidden, false, "the composer is open");
      assert.equal(b0.inline, "", "no inline height yet: the sheet's three rows");
      assert.ok(b0.focused, "the box has the keyboard");
      // the person drags the handle 120px down before typing a word: the browser writes the inline height, no input fires
      await drag(page, b0, 120);
      const dragged = await box();
      const draggedPx = px(dragged.inline);
      assert.ok(draggedPx > b0.height + 60, "the drag took: " + b0.height + " -> " + dragged.inline);
      assert.equal(dragged.value, "", "nothing typed yet");
      // the first keystroke: the dragged height stands (it used to snap back to three rows here)
      await page.keyboard.type("a");
      const typed = await box();
      assert.equal(typed.value, "a");
      assert.equal(typed.inline, dragged.inline, "the first keystroke left the dragged height alone");
      await page.keyboard.type("\nb\nc\nd");
      assert.equal((await box()).inline, dragged.inline, "…and so did the next ones");
      // Cancel: the next composer starts at three rows and autosizes again
      await page.click('.fc-panel [data-act="fccancel"]');
      await page.click('.fc-panel [data-act="fcfile"]');
      const again = await box();
      assert.equal(again.inline, "", "reset by Cancel");
      near(again.height, b0.height, "three rows again");
      await page.keyboard.type("one\ntwo\nthree\nfour\nfive");
      const grown = await box();
      assert.ok(px(grown.inline) > b0.height + 20, "no drag: the box followed its content (" + grown.inline + ")");
      // a drag after typing stands as it always did
      await drag(page, grown, 80);
      const late = await box();
      assert.ok(px(late.inline) > px(grown.inline) + 40, "the second drag took");
      await page.keyboard.type("\nsix");
      assert.equal((await box()).inline, late.inline, "a drag after typing stands");
    });
  });

  test("in " + name + ": the real panel — at the cap the box is twelve rows, inline and rendered, and scrolls; a drag past the cap takes and stands through typing; with no drag the box follows its content back to the floor", async (t) => {
    await inBrowser(t, name, PAGE_PANEL, PANEL_JS, async (page) => {
      const box = (): Promise<BoxRead> => page.evaluate(() => (window as any).__box());
      const answer = (): Promise<string | null> => page.evaluate(() => (window as any).__answer());
      const { COMPOSER_ROWS, COMPOSER_MAX_ROWS } = await page.evaluate(() => ({ COMPOSER_ROWS: (window as any).__romp.COMPOSER_ROWS, COMPOSER_MAX_ROWS: (window as any).__romp.COMPOSER_MAX_ROWS }));
      await page.evaluate(() => (window as any).__mount());
      assert.ok(await answer(), "the probe's status ask, answered");
      await page.click(".fileview-fc button");
      assert.ok(await answer(), "the open's status ask, answered");
      await page.click('.fc-panel [data-act="fcfile"]');
      const b0 = await box();
      assert.ok(b0.lineHeight > 0, "the sheet's line-height resolved");
      const rows = (n: number) => n * b0.lineHeight + b0.padBorder;
      near(b0.height, rows(COMPOSER_ROWS), "three rows to start");
      const twenty = Array.from({ length: 20 }, (_, i) => "line " + (i + 1)).join("\n");
      await page.keyboard.type(twenty);
      const cap = await box();
      near(cap.height, rows(COMPOSER_MAX_ROWS), "twenty lines render at twelve rows");
      near(px(cap.inline), rows(COMPOSER_MAX_ROWS), "…and the inline height IS twelve rows: autosizeComposer's cap, not a sheet clamp under a taller write");
      assert.ok(cap.scrollHeight > cap.clientHeight + b0.lineHeight, "the rest scrolls inside the box");
      // the person drags the handle 100px down at the cap: the box gets taller — past the cap, as a drag may
      await drag(page, cap, 100);
      const dragged = await box();
      assert.ok(dragged.height > cap.height + 80, "the drag past the cap took: " + cap.height + " -> " + dragged.height);
      assert.ok(px(dragged.inline) > px(cap.inline) + 80, "…and the inline height went with it (" + dragged.inline + ")");
      // then types: the dragged height is a real drag now, so it stands (it used to be read as one too, but the box
      // could not get taller, so the drag froze the box at the cap for the rest of the comment)
      await page.keyboard.press("Control+a");
      await page.keyboard.type("one\ntwo");
      const typed = await box();
      assert.equal(typed.value, "one\ntwo");
      assert.equal(typed.inline, dragged.inline, "the dragged height stands through the typing that follows");
      near(typed.height, dragged.height, "…rendered as dragged");
      // the control: the same typing with no drag follows the content back down to the floor
      await page.click('.fc-panel [data-act="fccancel"]');
      await page.click('.fc-panel [data-act="fcfile"]');
      assert.equal((await box()).inline, "", "reset by Cancel");
      await page.keyboard.type(twenty);
      near((await box()).height, rows(COMPOSER_MAX_ROWS), "at the cap again");
      await page.keyboard.press("Control+a");
      await page.keyboard.type("one\ntwo");
      const ctl = await box();
      assert.equal(ctl.value, "one\ntwo");
      near(ctl.height, rows(COMPOSER_ROWS), "no drag: two lines take the box back to the floor (the sheet's min-height)");
      assert.ok(px(ctl.inline) <= rows(COMPOSER_ROWS) + 0.5, "autosize kept following the content: the inline height is at or under the floor (" + ctl.inline + ")");
    });
  });
}

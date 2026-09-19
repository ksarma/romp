// The chat pane's Reply sheet (render.ts showUserTodoReply, the twin of waiting.ts showReply) on a phone with the
// keyboard up, in a real engine (the user 2026-09-19, screenshot; waiting-reply-sheet-browser.test.ts is the pane's
// leg, reply-sheet-keyboard.test.ts the rules and the executed closures). The chat page loads styles.css alone, and
// render.ts is not bundled for a test page; so, as render-todo-file-chip-sheet.test.ts does, the page is the sheet as
// showUserTodoReply builds it — the title, the quoted line, .ut-detail.open with a forty-line detail, the rows=3
// textarea, Cancel and Send — and the fold and the grow handler are the builder's OWN LINES, sliced out of render.ts's
// source and run in the page against the real overlay and textarea: kbFit and its arming, grow and its arming.
//
// The browser legs (Chromium, Firefox, and WebKit when the box has them; CI installs none, so they skip LOUDLY) open
// the page at the phone's width and drive the viewport's HEIGHT as the keyboard would (inside the shell the chat
// iframe is sized to the visible height, so its innerHeight is the keyboard's signal). At 508px, above the fold's
// threshold: the answer box holds three rows (a probe textarea of the same class outside the sheet gives the exact
// three-row height; on the base tree the box was a sliver, the assertion that goes red there), the detail overflows
// its cap and scrolls within itself, the buttons' bottom edge is inside the viewport. At 420px the fold is on from
// the window's own resize: the sheet sits at the top under the 12px frame, three rows still, the buttons reachable.
// Typing grows the box, capped; clearing returns it to the floor. At 900px the fold is off. Synthetic fixtures only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";

const requireCjs = createRequire(__filename);
const EXT = process.cwd();                                        // npm test runs in vscode-extension
const UI = path.resolve(EXT, "..", "ui", "webview");
const STYLES_CSS = fs.readFileSync(path.join(UI, "styles.css"), "utf8");
const RENDER = fs.readFileSync(path.join(UI, "render.ts"), "utf8");
const MODAL = RENDER.slice(RENDER.indexOf("function showUserTodoReply("), RENDER.indexOf("// ── COMMENT THREADS"));
assert.ok(MODAL.length > 200, "showUserTodoReply's slice was found");

// the builder's lines, by regexes (reply-sheet-keyboard.test.ts slices the same ones). A line not found is recorded, not
// thrown here: the page is built with what was found, so that on a tree without the fix the leg reaches the geometry and
// goes red on the squeezed answer box first (the defect), and the test asserts the slices right after that block, so a
// moved anchor is still a loud failure at the head
const MISSING: string[] = [];
const line = (re: RegExp, what: string): string => { const m = MODAL.match(re); if (!m) { MISSING.push(what); return ""; } return m[0]; };
const KBFIT = line(/^\s*const kbFit = .*$/m, "the kbFit line");
const KB_ARM = line(/window\.addEventListener\("resize", kbFit\);\n\s*kbFit\(\);/, "the fold's arming lines");
const GROW = line(/^\s*const grow = .*$/m, "the grow line");
const GROW_ARM = line(/input\.addEventListener\("input", grow\);/, "the grow arming line");

const TEXT = "Which layout should the quarterly report use?";
const DETAIL = Array.from({ length: 40 }, (_, i) => `Option ${i + 1}: the summary section leads and the tables follow, with the notes folded under each table.`).join("\n");
const PHONE_W = 390;
const KEYBOARD_UP = 508;   // above the fold's threshold: the squeeze fix alone
const KEYBOARD_TIGHT = 420;   // under it: the fold too
const TALL = 900;
const esc = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g, "&quot;");
// the chat page: an empty transcript and the Reply sheet as showUserTodoReply builds it, open, with the builder's own
// fold and grow lines run against it
const PAGE_HTML = `<!DOCTYPE html><html><head><meta charset=utf-8><link href=/dist/styles.css rel=stylesheet></head><body>
<div id="content"></div>
<div class="picker-overlay confirm-overlay" id="ut-reply-prompt"><div class="picker-box confirm-box">
<div class="confirm-title">Reply</div>
<div class="confirm-detail ut-reply-quote">${esc(TEXT)}</div>
<div class="ut-detail open">${esc(DETAIL)}</div>
<textarea class="ut-reply-input" rows="3" placeholder="Your answer — it goes straight to the session…"></textarea>
<div class="confirm-actions"><button class="picker-action confirm-btn">Cancel</button><button class="picker-action confirm-btn">Send</button></div>
</div></div>
<script>(function () {
  const overlay = document.getElementById("ut-reply-prompt");
  const input = overlay.querySelector(".ut-reply-input");
${KBFIT}
${GROW}
  ${GROW_ARM}
  ${KB_ARM}
})();</script></body></html>`;

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

type Sheet = {
  frameH: number; tight: boolean; alignItems: string; paddingTop: string;
  inputH: number; floorH: number; lineHeight: string;
  detailScrollH: number; detailClientH: number; detailOverflowY: string;
  actionsBottom: number; boxBottom: number; boxScrollH: number; boxClientH: number; boxOverflowY: string;
};

async function boot(browser: any) {
  const errors: string[] = [];
  const page = await browser.newPage({ viewport: { width: PHONE_W, height: KEYBOARD_UP } });
  page.on("pageerror", (e: Error) => { errors.push(e.message); });
  await page.route("http://romp.test/**", (route: any) => {
    const u = new URL(route.request().url());
    if (u.pathname === "/chat") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: PAGE_HTML });
    if (u.pathname === "/dist/styles.css") return route.fulfill({ status: 200, contentType: "text/css; charset=utf-8", body: STYLES_CSS });
    return route.fulfill({ status: 404, body: "" });
  });
  await page.goto("http://romp.test/chat");
  // the keyboard: the viewport's height, which the page's window sees as its own resize
  const setHeight = async (h: number) => {
    await page.setViewportSize({ width: PHONE_W, height: h });
    await page.waitForFunction((hh: number) => window.innerHeight === hh, h, { timeout: 10000 });
  };
  const measure = (): Promise<Sheet | null> => page.evaluate(() => {
    const overlay = document.getElementById("ut-reply-prompt");
    if (!overlay) return null;
    const box = overlay.querySelector(".confirm-box") as HTMLElement;
    const input = overlay.querySelector(".ut-reply-input") as HTMLTextAreaElement;
    const detail = overlay.querySelector(".ut-detail") as HTMLElement;
    const actions = overlay.querySelector(".confirm-actions") as HTMLElement;
    const cs = (e: Element) => getComputedStyle(e);
    // the three-row height in THIS engine: a probe of the same class, rows=3, outside the sheet where nothing squeezes it
    const probe = document.createElement("textarea"); probe.className = "ut-reply-input"; probe.rows = 3;
    document.body.appendChild(probe);
    const floorH = probe.clientHeight;
    probe.remove();
    return {
      frameH: window.innerHeight, tight: overlay.classList.contains("kb-tight"), alignItems: cs(overlay).alignItems, paddingTop: cs(overlay).paddingTop,
      inputH: input.clientHeight, floorH, lineHeight: cs(input).lineHeight,
      detailScrollH: detail.scrollHeight, detailClientH: detail.clientHeight, detailOverflowY: cs(detail).overflowY,
      actionsBottom: actions.getBoundingClientRect().bottom, boxBottom: box.getBoundingClientRect().bottom,
      boxScrollH: box.scrollHeight, boxClientH: box.clientHeight, boxOverflowY: cs(box).overflowY,
    };
  });
  const waitTight = (on: boolean) => page.waitForFunction((want: boolean) => document.getElementById("ut-reply-prompt")?.classList.contains("kb-tight") === want, on, { timeout: 10000 });
  return { page, setHeight, measure, waitTight, errors };
}

const reachable = (m: Sheet) => m.actionsBottom <= m.frameH + 0.5 || (m.boxOverflowY === "auto" && m.boxScrollH > m.boxClientH + 1);

for (const name of ["chromium", "firefox", "webkit"]) {
  test(`in ${name}: the chat's Reply sheet holds three rows with the keyboard up, the detail scrolls within its cap, the buttons stay in view; the fold follows the window's height`, async (t) => {
    if (!pw) { t.skip("playwright is not installed under vscode-extension — the browser legs need it (CI installs no browsers)"); return; }
    let browser: any;
    try { browser = await pw[name].launch(); }
    catch (e) { t.skip("no playwright " + name + " on this box — this leg needs it (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
    try {
      const { page, setHeight, measure, waitTight, errors } = await boot(browser);
      // ── 508px: the keyboard up on a phone, above the fold's threshold — the squeeze fix alone
      let m = (await measure())!;
      assert.ok(m, "the Reply sheet is up");
      assert.equal(m.frameH, KEYBOARD_UP);
      assert.equal(m.tight, false, "508px is not a short window: no fold, so what follows is the squeeze fix on its own");
      assert.ok(m.floorH > 30, `the probe laid out three rows (${m.floorH}px; line-height ${m.lineHeight})`);
      assert.ok(m.inputH >= m.floorH - 1, `the answer box holds three rows: ${m.inputH}px against the ${m.floorH}px three-row probe (on the base tree it was a sliver)`);
      assert.equal(m.detailOverflowY, "auto", "the detail scrolls within itself");
      assert.ok(m.detailScrollH > m.detailClientH + 8, `the forty-line detail overflows its cap and is a scroll away (${m.detailClientH} of ${m.detailScrollH}px)`);
      assert.ok(m.detailClientH > 20, `the detail still shows some lines (${m.detailClientH}px)`);
      assert.ok(m.actionsBottom > 0 && m.actionsBottom <= m.frameH + 0.5, `Cancel and Send are inside the viewport (bottom edge ${m.actionsBottom.toFixed(1)} of ${m.frameH}px)`);
      assert.ok(m.boxBottom <= m.frameH + 0.5, `the whole box is inside the viewport (${m.boxBottom.toFixed(1)} of ${m.frameH}px)`);
      // the builder's own lines ran in the page: every slice was found, and none carries a type annotation (plain JS there)
      assert.deepEqual(MISSING, [], "not found in showUserTodoReply: " + MISSING.join(", ") + " — re-anchor");
      for (const l of [KBFIT, KB_ARM, GROW, GROW_ARM]) assert.doesNotMatch(l, /: (HTMLTextAreaElement|HTMLElement|KeyboardEvent|string|number)\b/, "the sliced lines carry no type annotation, so they run as plain JS in the page");
      // ── 420px: a short window — the builder's kbFit, on the window's own resize
      await setHeight(KEYBOARD_TIGHT);
      await waitTight(true);
      m = (await measure())!;
      assert.equal(m.tight, true, "under 480px the sheet wears kb-tight");
      assert.equal(m.alignItems, "flex-start", "folded, the sheet sits at the top rather than centering into the keyboard");
      assert.equal(m.paddingTop, "12px", "under the picker's 12px frame");
      assert.ok(m.inputH >= m.floorH - 1, `folded, the answer box still holds three rows (${m.inputH} against ${m.floorH}px)`);
      assert.ok(m.detailScrollH > m.detailClientH + 8, `folded, the detail still scrolls (${m.detailClientH} of ${m.detailScrollH}px)`);
      assert.ok(reachable(m), `folded, the buttons are reachable (bottom edge ${m.actionsBottom.toFixed(1)} of ${m.frameH}px; box ${m.boxClientH} of ${m.boxScrollH}px, overflow-y ${m.boxOverflowY})`);
      assert.ok(m.boxClientH <= KEYBOARD_TIGHT - 24 + 1, `the box is capped at the visible height less the 12px frame (${m.boxClientH}px)`);
      // ── typing: the builder's grow handler, on the real textarea
      const before = m.inputH;
      await page.locator("#ut-reply-prompt .ut-reply-input").fill(Array.from({ length: 12 }, (_, i) => `line ${i + 1}`).join("\n"));
      m = (await measure())!;
      assert.ok(m.inputH > before + 20, `twelve lines grow the box (${before} → ${m.inputH}px)`);
      assert.ok(m.inputH <= Math.round(KEYBOARD_TIGHT * 0.4) + 2, `capped at a share of the window (${m.inputH}px of a ${KEYBOARD_TIGHT}px window)`);
      assert.ok(reachable(m), `with the answer grown the buttons are still reachable (bottom edge ${m.actionsBottom.toFixed(1)} of ${m.frameH}px; box ${m.boxClientH} of ${m.boxScrollH}px)`);
      await page.locator("#ut-reply-prompt .ut-reply-input").fill("");
      m = (await measure())!;
      assert.ok(Math.abs(m.inputH - before) <= 2, `cleared, the box is back at the floor (${m.inputH} vs ${before}px)`);
      // ── 900px: the keyboard down
      await setHeight(TALL);
      await waitTight(false);
      m = (await measure())!;
      assert.equal(m.tight, false, "the room back, the fold comes off");
      assert.notEqual(m.alignItems, "flex-start", "the sheet centers again (.confirm-overlay)");
      assert.ok(m.inputH >= m.floorH - 1, `tall, the answer box holds three rows (${m.inputH} against ${m.floorH}px)`);
      assert.ok(m.actionsBottom <= m.frameH + 0.5, "the buttons are inside the viewport");
      assert.deepEqual(errors, [], "no script error on the page");
    } finally { await browser.close(); }
  });
}

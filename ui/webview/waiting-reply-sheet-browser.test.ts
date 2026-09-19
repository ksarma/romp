// The Waiting-on-you pane's Reply sheet on a phone with the keyboard up, in a real engine (the user 2026-09-19,
// screenshot): a todo's long detail filled the sheet and the answer box was one squeezed line above Cancel and Send.
// The sheet (waiting.ts showReply) is a column flex box capped at the window with overflow hidden; the detail, a
// wrapped text block, never shrinks (its automatic minimum is its content), the textarea shrinks to nothing (a
// textarea's resolves to zero), and the cap clips rather than scrolls. reply-sheet-keyboard.test.ts pins the three
// rules and executes the fold and the grow handler against stand-ins; this leg lays the real thing out.
//
// The browser legs (Chromium, Firefox, and WebKit when the box has them; CI installs none, so they skip LOUDLY) load
// the kernel's /waiting page as it is served — styles.css, then the pane's sheet — with the worktree's waiting.ts
// bundle in a 390px-wide frame, the phone's width, and drive the frame's HEIGHT as the keyboard would: inside the
// shell the pane iframe is sized to the visible height (--app-h), so the frame's innerHeight IS the keyboard's signal
// and a shorter frame is the keyboard up. One todo with a forty-line detail is fed; Reply is tapped. At 508px (a
// phone's visible height with the keyboard up, above the fold's 480px threshold, so the squeeze fix stands on its
// own): the answer box is at least three rows (a probe textarea of the same class laid out outside the sheet gives
// the exact three-row height in this engine; on the base tree the box was a sliver, and this is the assertion that
// goes red there), the detail overflows its cap and scrolls within itself, and the buttons' bottom edge is inside
// the frame. At 420px the fold is on (kb-tight, from the frame's own resize event): the sheet sits at the top under
// the 12px frame, the box still holds three rows, the buttons are still reachable. Typing twelve lines grows the box
// with the answer, capped so the buttons stay; clearing it returns to the floor. At 900px the fold is off again.
// Synthetic fixtures only: the notes-api world, a placeholder sid, TESTHOST.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";

const requireCjs = createRequire(__filename);
const EXT = process.cwd();                                        // npm test runs in vscode-extension
const UI = path.resolve(EXT, "..", "ui", "webview");
const PANE_CSS = fs.readFileSync(path.join(UI, "waiting-pane.css"), "utf8");
const STYLES_CSS = fs.readFileSync(path.join(UI, "styles.css"), "utf8");

// synthetic world: one session of the notes-api demo, one todo whose detail runs to forty lines
const SID = "TESTHOST:11111111-2222-3333-4444-555555555555";
const NAME = "TESTHOST:api";
const TEXT = "Which layout should the quarterly report use?";
const DETAIL = Array.from({ length: 40 }, (_, i) => `Option ${i + 1}: the summary section leads and the tables follow, with the notes folded under each table.`).join("\n");
const TODO = { id: "t1", text: TEXT, detail: DETAIL };
const PHONE_W = 390;
const KEYBOARD_UP = 508;   // above the fold's threshold: the squeeze fix alone
const KEYBOARD_TIGHT = 420;   // under it: the fold too
const TALL = 900;

function bundle(entry: string): string {
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    entryPoints: [path.join(UI, entry)], bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent",
  });
  return r.outputFiles[0].text;
}
// the frame the pane runs in, at the phone's width; its height is the test's input (the shell's --app-h sizing)
const SHELL_HTML = `<!DOCTYPE html><html><head><meta charset=utf-8>
<style>body{margin:0}iframe{display:block;width:${PHONE_W}px;height:${KEYBOARD_UP}px;border:0}</style></head><body>
<iframe id=f-waiting src=/waiting></iframe></body></html>`;
// the kernel's /waiting page, as _waiting_page serves it: the chat's stylesheet, then the pane's sheet in a <style>
// after it (the sheet's @import and font urls 404 here, harmlessly)
const WAITING_HTML = `<!DOCTYPE html><html><head><meta charset=utf-8><link href=/dist/styles.css rel=stylesheet>
<style>${PANE_CSS}</style></head><body>
<div id=waiting-head></div><div id=waiting-list></div><script src=/dist/waiting.js></script></body></html>`;

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

// the sheet's geometry, read in the frame: the frame's height, the fold, the overlay's placement, the answer box's
// height against a three-row probe, the detail's scroll state, the buttons' and the box's bottom edges
type Sheet = {
  frameH: number; tight: boolean; alignItems: string; paddingTop: string;
  inputH: number; floorH: number; lineHeight: string; inputOverflowY: string;
  detailScrollH: number; detailClientH: number; detailOverflowY: string;
  actionsBottom: number; boxBottom: number; boxScrollH: number; boxClientH: number; boxOverflowY: string;
};

async function boot(browser: any) {
  const errors: string[] = [];
  const waitingJs = bundle("waiting.ts");
  const page = await browser.newPage({ viewport: { width: PHONE_W + 30, height: TALL + 40 } });
  page.on("pageerror", (e: Error) => { errors.push(e.message); });
  await page.route("http://romp.test/**", (route: any) => {
    const u = new URL(route.request().url());
    if (u.pathname === "/shell") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: SHELL_HTML });
    if (u.pathname === "/waiting") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: WAITING_HTML });
    if (u.pathname === "/dist/waiting.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: waitingJs });
    if (u.pathname === "/dist/styles.css") return route.fulfill({ status: 200, contentType: "text/css; charset=utf-8", body: STYLES_CSS });
    return route.fulfill({ status: 404, body: "" });
  });
  await page.goto("http://romp.test/shell");   // the load event covers the frame's boot
  await page.evaluate(([sid, name, todo]: [string, string, typeof TODO]) => {
    const f = document.getElementById("f-waiting") as HTMLIFrameElement;
    const now = Math.floor(Date.now() / 1000);
    f.contentWindow!.postMessage({ type: "feed", now, userTodosOn: true, userTodoRows: [{ sid, name, color: { bg: "#123456", fg: "#ffffff" },
      todos: [{ id: todo.id, text: todo.text, createdT: now - 300, detail: todo.detail }] }] }, "*");
  }, [SID, NAME, TODO] as [string, string, typeof TODO]);
  const W = page.frameLocator("#f-waiting");
  await W.locator(`.ut-reply[data-tid="${TODO.id}"]`).waitFor({ timeout: 10000 });
  // the keyboard: the frame's height, and the frame's window sees it as its own resize
  const setHeight = async (h: number) => {
    await page.evaluate((hh: number) => { (document.getElementById("f-waiting") as HTMLIFrameElement).style.height = hh + "px"; }, h);
    await page.waitForFunction((hh: number) => (document.getElementById("f-waiting") as HTMLIFrameElement).contentWindow!.innerHeight === hh, h, { timeout: 10000 });
  };
  const measure = (): Promise<Sheet | null> => page.evaluate(() => {
    const win = (document.getElementById("f-waiting") as HTMLIFrameElement).contentWindow!;
    const d = win.document;
    const overlay = d.getElementById("ut-reply-prompt");
    if (!overlay) return null;
    const box = overlay.querySelector(".confirm-box") as HTMLElement;
    const input = overlay.querySelector(".ut-reply-input") as HTMLTextAreaElement;
    const detail = overlay.querySelector(".ut-detail") as HTMLElement;
    const actions = overlay.querySelector(".confirm-actions") as HTMLElement;
    const cs = (e: Element) => win.getComputedStyle(e);
    // the three-row height in THIS engine: a probe of the same class, rows=3, laid out outside the sheet where nothing
    // squeezes it; measured and removed
    const probe = d.createElement("textarea"); probe.className = "ut-reply-input"; probe.rows = 3;
    d.body.appendChild(probe);
    const floorH = probe.clientHeight;
    probe.remove();
    return {
      frameH: win.innerHeight, tight: overlay.classList.contains("kb-tight"), alignItems: cs(overlay).alignItems, paddingTop: cs(overlay).paddingTop,
      inputH: input.clientHeight, floorH, lineHeight: cs(input).lineHeight, inputOverflowY: cs(input).overflowY,
      detailScrollH: detail.scrollHeight, detailClientH: detail.clientHeight, detailOverflowY: cs(detail).overflowY,
      actionsBottom: actions.getBoundingClientRect().bottom, boxBottom: box.getBoundingClientRect().bottom,
      boxScrollH: box.scrollHeight, boxClientH: box.clientHeight, boxOverflowY: cs(box).overflowY,
    };
  });
  const openReply = async () => {
    await W.locator(`.ut-reply[data-tid="${TODO.id}"]`).click();
    await W.locator("#ut-reply-prompt .ut-reply-input").waitFor({ timeout: 10000 });
  };
  const waitTight = (on: boolean) => page.waitForFunction((want: boolean) => {
    const d = (document.getElementById("f-waiting") as HTMLIFrameElement).contentWindow!.document;
    return d.getElementById("ut-reply-prompt")?.classList.contains("kb-tight") === want;
  }, on, { timeout: 10000 });
  return { page, W, setHeight, measure, openReply, waitTight, errors };
}

// the buttons are reachable: their bottom edge is inside the frame, or the box itself scrolls to them (the fold's
// overflow-y: auto backstop for a window too short for the whole sheet)
const reachable = (m: Sheet) => m.actionsBottom <= m.frameH + 0.5 || (m.boxOverflowY === "auto" && m.boxScrollH > m.boxClientH + 1);

for (const name of ["chromium", "firefox", "webkit"]) {
  test(`in ${name}: with the keyboard up the answer box holds three rows, the detail scrolls within its cap, and Cancel and Send stay in the frame; the fold follows the frame's height`, async (t) => {
    if (!pw) { t.skip("playwright is not installed under vscode-extension — the browser legs need it (CI installs no browsers)"); return; }
    let browser: any;
    try { browser = await pw[name].launch(); }
    catch (e) { t.skip("no playwright " + name + " on this box — this leg needs it (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
    try {
      const { W, setHeight, measure, openReply, waitTight, errors } = await boot(browser);
      await openReply();
      // ── 508px: the keyboard up on a phone, above the fold's threshold — the squeeze fix alone
      let m = (await measure())!;
      assert.ok(m, "the Reply sheet is up");
      assert.equal(m.frameH, KEYBOARD_UP, "the frame is the phone's visible height with the keyboard up");
      assert.equal(m.tight, false, "508px is not a short window: no fold, so what follows is the squeeze fix on its own");
      assert.ok(m.floorH > 30, `the probe laid out three rows (${m.floorH}px; line-height ${m.lineHeight})`);
      assert.ok(m.inputH >= m.floorH - 1, `the answer box holds three rows: ${m.inputH}px against the ${m.floorH}px three-row probe (on the base tree it was a sliver — the textarea took the whole deficit)`);
      assert.equal(m.detailOverflowY, "auto", "the detail scrolls within itself");
      assert.ok(m.detailScrollH > m.detailClientH + 8, `the forty-line detail overflows its cap and is a scroll away, not clipped (${m.detailClientH} of ${m.detailScrollH}px)`);
      assert.ok(m.detailClientH > 20, `the detail still shows some lines (${m.detailClientH}px): the box gave way, not the whole detail`);
      assert.ok(m.actionsBottom > 0 && m.actionsBottom <= m.frameH + 0.5, `Cancel and Send are inside the frame (bottom edge ${m.actionsBottom.toFixed(1)} of ${m.frameH}px)`);
      assert.ok(m.boxBottom <= m.frameH + 0.5, `the whole box is inside the frame (${m.boxBottom.toFixed(1)} of ${m.frameH}px)`);
      // ── 420px: a short window — the fold, on the frame's own resize event
      await setHeight(KEYBOARD_TIGHT);
      await waitTight(true);
      m = (await measure())!;
      assert.equal(m.tight, true, "under 480px the sheet wears kb-tight");
      assert.equal(m.alignItems, "flex-start", "folded, the sheet sits at the top rather than centering into the keyboard");
      assert.equal(m.paddingTop, "12px", "under the picker's 12px frame");
      assert.ok(m.inputH >= m.floorH - 1, `folded, the answer box still holds three rows (${m.inputH} against ${m.floorH}px)`);
      assert.ok(m.detailScrollH > m.detailClientH + 8, `folded, the detail still scrolls within itself (${m.detailClientH} of ${m.detailScrollH}px)`);
      assert.ok(reachable(m), `folded, the buttons are reachable (bottom edge ${m.actionsBottom.toFixed(1)} of ${m.frameH}px; box ${m.boxClientH} of ${m.boxScrollH}px, overflow-y ${m.boxOverflowY})`);
      assert.ok(m.boxClientH <= KEYBOARD_TIGHT - 24 + 1, `the box is capped at the visible height less the 12px frame (${m.boxClientH}px)`);
      // ── typing: the box grows with the answer, capped, and never pushes the buttons out of reach; cleared, it returns to the floor
      const before = m.inputH;
      await W.locator("#ut-reply-prompt .ut-reply-input").fill(Array.from({ length: 12 }, (_, i) => `line ${i + 1}`).join("\n"));
      m = (await measure())!;
      assert.ok(m.inputH > before + 20, `twelve lines grow the box (${before} → ${m.inputH}px)`);
      assert.ok(m.inputH <= Math.round(KEYBOARD_TIGHT * 0.4) + 2, `capped at a share of the window (${m.inputH}px of a ${KEYBOARD_TIGHT}px window)`);
      assert.ok(reachable(m), `with the answer grown the buttons are still reachable (bottom edge ${m.actionsBottom.toFixed(1)} of ${m.frameH}px; box ${m.boxClientH} of ${m.boxScrollH}px)`);
      await W.locator("#ut-reply-prompt .ut-reply-input").fill("");
      m = (await measure())!;
      assert.ok(Math.abs(m.inputH - before) <= 2, `cleared, the box is back at the floor (${m.inputH} vs ${before}px)`);
      // ── 900px: the keyboard down — the same event takes the fold off
      await setHeight(TALL);
      await waitTight(false);
      m = (await measure())!;
      assert.equal(m.tight, false, "the room back, the fold comes off");
      assert.notEqual(m.alignItems, "flex-start", "the sheet centers again (.confirm-overlay)");
      assert.ok(m.inputH >= m.floorH - 1, `tall, the answer box holds three rows (${m.inputH} against ${m.floorH}px)`);
      assert.ok(m.actionsBottom <= m.frameH + 0.5, "the buttons are inside the frame");
      assert.deepEqual(errors, [], "no script error in the frame");
    } finally { await browser.close(); }
  });
}

// The Waiting-on-you pane's two chips under a long label, in a real engine (the review of the todo-file follow-on,
// 2026-09-07). `.wt-file` (the file a todo names: its basename, the full path in the title) and `.wt-sess` (the
// session's name, host-prefixed for a remote one) are pills capped at a share of the row (max-width 32% / 38%) with
// overflow:hidden; white-space:nowrap; text-overflow:ellipsis — and both were display:inline-flex. text-overflow acts
// on block containers only: on a flex container the text sits in an anonymous flex item the property never reaches,
// so a long basename was cut mid-word with a hard edge and nothing to say it was cut, and the full path is
// title-only, out of reach on touch. styles.css's .fileview-sess met the same defect in the review of #970 and is a
// block; the new chip copied .wt-sess's construction instead. Both chips are block containers now (they are flex
// items of .ut-line and of the Reply modal's .confirm-box, so the parent places them either way).
//
// The source leg runs everywhere and pins the two rules. The browser legs (Chromium, and Firefox when the box has
// it; CI installs none, so they skip LOUDLY) load the kernel's /waiting page as it is served — styles.css, then the
// pane's sheet — with the worktree's waiting.ts bundle in a 420px frame, feed one row whose file has a long basename
// from a remote session with a long name, open its Reply modal, and read the layout: each chip overflows (the case
// under test), and text-overflow REACHES its text — setting the chip's own text-overflow to clip changes what is
// painted. A control first: two paints of the unchanged chip are identical, so the difference is the ellipsis and
// not noise. On the inline-flex chips the toggle changed nothing, because the property never reached the text.
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

// ── the source leg ────────────────────────────────────────────────────────────────────────────────
test("source: both chips are block containers wearing the ellipsis triple — no flex container between the property and the text", () => {
  for (const sel of [".wt-sess{", ".wt-file{"]) {
    const at = PANE_CSS.indexOf(sel);
    assert.ok(at >= 0, sel + " is in the pane's sheet");
    const rule = PANE_CSS.slice(at, PANE_CSS.indexOf("}", at));
    assert.match(rule, /;display:block;/, sel + " is a block container (text-overflow acts on block containers only)");
    assert.match(rule, /overflow:hidden;white-space:nowrap;text-overflow:ellipsis;/, sel + " keeps the ellipsis triple");
    assert.doesNotMatch(rule, /inline-flex|align-items/, sel + ": no flex container around the text, which text-overflow could not reach");
    assert.match(rule, /^\S+flex:0 0 auto;/, sel + " stays a fixed flex item of the row");
    assert.match(rule, /max-width:\d+%;/, sel + " is capped at a share of the row — the cap is what makes a long label overflow");
  }
  // the construction .fileview-sess settled on (file-view.test.ts pins it): the three chips agree
  assert.match(STYLES_CSS, /\.fileview-sess \{ flex: 0 0 auto; display: block;/, "the viewer's chip is the precedent");
  assert.ok(PANE_CSS.includes("#ut-reply-prompt .wt-file{align-self:flex-start"), "in the modal's column the chip shrink-wraps its label, never the column's width");
});

// ── the browser legs ──────────────────────────────────────────────────────────────────────────────
// synthetic world: a remote session of the notes-api demo with a long name, a todo naming a file with a long basename
const SID = "TESTHOST:11111111-2222-3333-4444-555555555555";
const NAME = "TESTHOST:notes-api-integration-tests-long-session-name";
const FILE = "/tmp/notes-api/docs/quarterly_report_layout_options_v3_final.md";

function bundle(entry: string): string {
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    entryPoints: [path.join(UI, entry)], bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent",
  });
  return r.outputFiles[0].text;
}
// the frame the pane runs in: framed, so fileChip builds the real path-link chip; 420px wide, the finding's pane
const SHELL_HTML = `<!DOCTYPE html><html><head><meta charset=utf-8>
<style>body{margin:0}iframe{display:block;width:420px;height:400px;border:0}</style></head><body>
<iframe id=f-waiting src=/waiting></iframe></body></html>`;
// the kernel's /waiting page, as _waiting_page serves it: the chat's stylesheet, then the pane's sheet in a <style>
// after it (the sheet's @import and font urls 404 here, harmlessly)
const WAITING_HTML = `<!DOCTYPE html><html><head><meta charset=utf-8><link href=/dist/styles.css rel=stylesheet>
<style>${PANE_CSS}</style></head><body>
<div id=waiting-head></div><div id=waiting-list></div><script src=/dist/waiting.js></script></body></html>`;

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

type Box = { clientWidth: number; scrollWidth: number; display: string; textOverflow: string; text: string } | null;

async function boot(browser: any) {
  const errors: string[] = [];
  const waitingJs = bundle("waiting.ts");
  const page = await browser.newPage({ viewport: { width: 460, height: 440 } });
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
  await page.evaluate(([sid, name, file]: [string, string, string]) => {
    const f = document.getElementById("f-waiting") as HTMLIFrameElement;
    const now = Math.floor(Date.now() / 1000);
    f.contentWindow!.postMessage({ type: "feed", now, userTodosOn: true, userTodoRows: [{ sid, name, color: { bg: "#123456", fg: "#ffffff" },
      todos: [{ id: "t1", text: "Pick the layout", createdT: now - 120, detail: "", file }] }] }, "*");
  }, [SID, NAME, FILE] as [string, string, string]);
  const W = page.frameLocator("#f-waiting");
  await W.locator(".wt-file").first().waitFor({ timeout: 10000 });
  // the chip's box and computed display, read in the frame
  const measure = (sel: string): Promise<Box> => page.evaluate((s: string) => {
    const d = (document.getElementById("f-waiting") as HTMLIFrameElement).contentWindow!.document;
    const e = d.querySelector(s) as HTMLElement | null;
    if (!e) return null;
    const cs = d.defaultView!.getComputedStyle(e);
    return { clientWidth: e.clientWidth, scrollWidth: e.scrollWidth, display: cs.display, textOverflow: cs.textOverflow, text: e.textContent || "" };
  }, sel);
  // the chip's own text-overflow, set inline (clip) or given back to the sheet
  const setClip = (sel: string, on: boolean) => page.evaluate(([s, o]: [string, boolean]) => {
    const d = (document.getElementById("f-waiting") as HTMLIFrameElement).contentWindow!.document;
    const e = d.querySelector(s) as HTMLElement;
    if (o) e.style.textOverflow = "clip"; else e.style.removeProperty("text-overflow");
  }, [sel, on] as [string, boolean]);
  // does text-overflow reach the chip's text? A control (the same paint twice), then the paint with clip set on the
  // chip itself: the ellipsis is the only thing that can change between them
  const paints = async (sel: string) => {
    const loc = W.locator(sel).first();
    const shot = () => loc.screenshot({ animations: "disabled" }) as Promise<Buffer>;
    const a = await shot();
    const b = await shot();
    await setClip(sel, true);
    const c = await shot();
    await setClip(sel, false);
    return { control: a.equals(b), differs: !a.equals(c) };
  };
  return { page, W, measure, paints, errors };
}

for (const name of ["chromium", "firefox"]) {
  test(`in ${name}: a long basename and a long session name end in an ellipsis on the row and in the Reply modal — text-overflow reaches the text`, async (t) => {
    if (!pw) { t.skip("playwright is not installed under vscode-extension — the browser legs need it (CI installs no browsers)"); return; }
    let browser: any;
    try { browser = await pw[name].launch(); }
    catch (e) { t.skip("no playwright " + name + " on this box — this leg needs it (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
    try {
      const { W, measure, paints, errors } = await boot(browser);
      // the row: the session chip and the file chip
      for (const [sel, label] of [[".wt-item .wt-sess", NAME], [".wt-item .wt-file", "quarterly_report_layout_options_v3_final.md"]] as const) {
        const m = await measure(sel);
        assert.ok(m, sel + " is on the row");
        assert.equal(m!.text, label, sel + " carries the whole label; the ellipsis is paint, not text");
        assert.equal(m!.textOverflow, "ellipsis", sel + " asks for the ellipsis");
        assert.ok(m!.scrollWidth > m!.clientWidth + 8, `${sel} overflows its cap (${m!.clientWidth} of ${m!.scrollWidth}px) — the case under test`);
        // the behavior first: does the property reach the text? (on the inline-flex chip this is what failed)
        const p = await paints(sel);
        assert.equal(p.control, true, sel + ": two paints of the unchanged chip are identical (the control)");
        assert.equal(p.differs, true, sel + ": setting text-overflow:clip on the chip changes the paint — the ellipsis was there, so the property reaches the text");
        // then the mechanism: a block container (as a flex item it is blockified either way; text-overflow needs the block)
        assert.equal(m!.display, "block", sel + " is a block container");
      }
      // the Reply modal: the same chip under the quoted line, a flex item of the box's column
      await W.locator(".ut-reply").first().click();
      await W.locator("#ut-reply-prompt .wt-file").waitFor({ timeout: 10000 });
      const sel = "#ut-reply-prompt .wt-file";
      const m = await measure(sel);
      assert.ok(m, "the modal shows the chip");
      assert.ok(m!.scrollWidth > m!.clientWidth + 8, `${sel} overflows its cap in the modal too (${m!.clientWidth} of ${m!.scrollWidth}px)`);
      const p = await paints(sel);
      assert.equal(p.control, true, sel + ": the control holds in the modal");
      assert.equal(p.differs, true, sel + ": the modal's chip ends in an ellipsis, not a hard cut into the pill's padding");
      assert.equal(m!.display, "block");
      assert.deepEqual(errors, [], "no script error in the frame");
    } finally { await browser.close(); }
  });
}

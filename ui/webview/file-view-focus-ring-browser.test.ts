// The ring at a hand-over, over the REAL viewer in headless Chromium (plans/markdown-viewer.md Slice 6, item 1; the review's
// round 3). Both sheets draw no ring on the body's `:focus` and the accent ring on its `:focus-visible`, for the keyboard
// user. Chromium's heuristic for a script focus does not draw that line by itself: it matches :focus-visible on the new
// holder when the old one wore it or a key was pressed since the last mouse press, and ALSO when nothing focusable was last
// pressed (a fresh page, a click on plain text, a chat pill whose press strips its tabindex, a Recent row that is a plain
// div, a relayed open whose click was in another frame), so at 27c56fbf7 the 1 px accent frame sat around the whole note on
// the common pointer opens: the first modal open after a pill click in the chat and in the feed, every open after an Escape
// or a click on plain text, every relayed open into the Files pane. openFileView's takeKeyboard now names the ring through
// the focus call's focusVisible option, read off the holder the body takes the keyboard from (none, or a mouse-focused
// control: none; a control wearing the ring: the ring), and the Outline's closers read it before the popover's removal.
// Measured here with real mouse presses over a REAL path-links pill (markPathLink, as render.ts marks the chat's paths) in
// the chat modal at 900 and 380 px and in the feed modal, and on the Files pane with no gesture (the relay's situation) and
// after a click on plain text (a Recent row's) at 900 and 380 px: the body holds the keyboard, matches no :focus-visible and
// its computed outline is none. The controls in the same runs: a Tab from the bar still earns the ring; a Raw toggle focused
// after a key and activated by Enter hands the keyboard over WITH the ring and a mouse click on Rendered without it; an
// Outline pick by End and Enter lands the heading with the ring and a pick by mouse without. Red over a git archive of
// 27c56fbf7 at the first pill click (fv true, outline solid).
// The ring after a key (the review's round 4): Chromium keeps the verdict the focus call named for the life of that focus,
// so at 7fbced030 a body handed the keyboard without the ring showed none after any number of keys, where the heuristic
// gives a mouse-focused element the ring on its first key. The body's keydown now takes the keyboard again naming the ring
// on the first key without Ctrl, Alt or Meta held (file-view.ts, beside takeKeyboard). The third leg measures it in the chat
// modal, the feed modal and the Files pane: after a pill click or a gestureless open the body holds the keyboard ringless,
// PageDown brings the accent ring and the key's own scroll, a mouse click on A+ hands over ringless again and ArrowDown
// brings the ring back, and Ctrl+C over a selection inside the body brings none and keeps the selection (the heuristic's
// own line: a chord is a shortcut). Red over a git archive of 7fbced030 at the first PageDown (fv false, outline none).
// Skips LOUDLY without a playwright browser (CI installs none), as the other legs do. Synthetic values only: an invented
// note, /repo/notes-api paths, the placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as path from "node:path";
import { inBrowser, pageHtml, frames, paintsReach, requireCjs, UI, EXT, ORIGIN, REPORT, SID, MT, PARA } from "./real-viewer-leg";

// the note: two sections, sixty paragraphs, so every viewport scrolls and the Outline lists three headings
const NOTE = "# Report\n\n## Alpha\n\n" + Array.from({ length: 30 }, (_, i) => PARA(i + 1)).join("\n\n")
  + "\n\n## Beta\n\n" + Array.from({ length: 30 }, (_, i) => PARA(i + 31)).join("\n\n") + "\n";

/** The pill builder from the REAL path-links.ts, bundled as window.PL (render.ts marks the chat's paths through it). */
function pathLinksBundle(): string {
  const r = requireCjs("esbuild").buildSync({
    stdin: { contents: 'export { markPathLink } from "./path-links";', resolveDir: UI, loader: "ts", sourcefile: "focus-ring-leg.ts" },
    bundle: true, write: false, format: "iife", globalName: "PL", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent",
  });
  return r.outputFiles[0].text as string;
}

type Ring = { active: string; fv: boolean; outline: string; outlineColor: string; accent: string; scrollTop: number };
/** In the page: who holds the keyboard, whether the body matches :focus-visible, its computed outline beside the resolved accent, and its scrollTop. */
function readRing(): Ring {
  const b = document.querySelector(".fileview-body") as HTMLElement | null;
  const a = document.activeElement as HTMLElement | null;
  const name = (n: Element | null): string => !n ? "none" : n.tagName + (n.id ? "#" + n.id : "") + (typeof (n as HTMLElement).className === "string" && (n as HTMLElement).className ? "." + (n as HTMLElement).className.split(/\s+/).filter(Boolean).join(".") : "");
  const probe = document.createElement("span"); probe.style.color = "var(--accent)"; document.body.appendChild(probe);
  const accent = getComputedStyle(probe).color; probe.remove();
  const cs = b ? getComputedStyle(b) : null;
  return { active: name(a), fv: b ? b.matches(":focus-visible") : false, outline: cs ? cs.outlineStyle : "no-body", outlineColor: cs ? cs.outlineColor : "no-body", accent, scrollTop: b ? b.scrollTop : -1 };
}
const ringOf = (page: any): Promise<Ring> => page.evaluate(readRing);
const BODY = "DIV.fileview-body";
/** The body holds the keyboard with no ring: a pointer's hand-over. */
function noRing(r: Ring, what: string): void {
  assert.equal(r.active, BODY, what + ": the body took the keyboard (read " + r.active + ")");
  assert.equal(r.fv, false, what + ": the body matches no :focus-visible (read fv " + r.fv + ", outline " + r.outline + "; at 27c56fbf7 Chromium's script-focus heuristic matched it with nothing focusable last pressed, and the accent frame sat around the whole note)");
  assert.equal(r.outline, "none", what + ": the computed outline is none (read " + r.outline + ")");
}
/** The body holds the keyboard with the accent ring: the keyboard's own arrival, or a hand-over from a holder that wore it. */
function ring(r: Ring, what: string): void {
  assert.equal(r.active, BODY, what + ": the body holds the keyboard (read " + r.active + ")");
  assert.equal(r.fv, true, what + ": the body matches :focus-visible");
  assert.notEqual(r.outline, "none", what + ": the ring shows (outline-style " + r.outline + ")");
  assert.equal(r.outlineColor, r.accent, what + ": the ring is the accent (var(--accent), never a status colour)");
}
const closed = (page: any): Promise<unknown> => page.waitForFunction(() => !document.getElementById("romp-fileview"), null, { timeout: 4000 });
/** One more paint than `before`, then three frames (the landing's seat and the keyboard's hand-over follow the paint). */
const painted = async (page: any, before: number): Promise<void> => { await paintsReach(page, before + 1); await frames(page, 3); };
const paints = (page: any): Promise<number> => page.evaluate(() => (window as any).__paints);
/** Splice `wire` before the page's LAST </body></html> (the bundle's own text holds the same bytes earlier). */
function spliced(base: string, wire: string): string {
  const tail = base.lastIndexOf("</body></html>");
  assert.ok(tail > 0, "the page ends with </body></html>");
  return base.slice(0, tail) + wire + base.slice(tail);
}
/** A page of the surface at the viewport size whose body opens with `inner`, serving `html`, with its page errors collected. */
async function pageOf(browser: any, w: number, h: number, html: string): Promise<{ page: any; errors: string[] }> {
  const page = await browser.newPage({ viewport: { width: w, height: h } });
  const errors: string[] = [];
  page.on("pageerror", (e: Error) => { errors.push(e.message); });
  await page.route((u: URL) => u.href.startsWith(ORIGIN), (route: any) => route.fulfill({ status: 200, contentType: "text/html", body: html }));
  await page.goto(ORIGIN + "/");
  return { page, errors };
}

test("in a browser, in the chat modal at 900 and 380 px and in the feed modal: a mouse click on a path pill opens the note with the body holding the keyboard and NO :focus-visible ring, on the fresh page, after an Escape and after a click on plain text alike; a Tab from the bar still earns the ring, a Raw toggle focused after a key and activated by Enter hands the keyboard over with the ring, and a mouse click on Rendered hands it over without", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const PL = pathLinksBundle();
    for (const [mode, w, h] of [["chat", 900, 700], ["chat", 380, 640], ["feed", 900, 700]] as Array<["chat" | "feed", number, number]>) {
      const what = mode + " " + w + "px";
      // the surface's stand-in: a transcript box with plain text and a REAL pill, whose click a delegate opens as render.ts's
      // openpath does (openFileView on the pill's data-path); a function replacer for the body tag (a string would read `$`)
      const base = pageHtml(mode, { [REPORT]: NOTE }, MT).replace('<body class="">', () => '<body class=""><div id="content" style="height:200px;overflow:auto"><p id="plain">plain transcript text</p><p>a line with a <span id="pill">docs/report.md</span> pill</p><div style="height:3000px"></div></div>');
      const wire = "<script>" + PL + "</script><script>PL.markPathLink(document.getElementById('pill'), " + JSON.stringify(REPORT) + ", false, " + JSON.stringify(SID) + ");"
        + " document.body.addEventListener('click', function (e) { var a = e.target && e.target.closest ? e.target.closest('[data-act=\"openpath\"]') : null; if (a) FV.openFileView(a.dataset.path, a.dataset.sid || null, null); });</script>";
      const { page, errors } = await pageOf(browser, w, h, spliced(base, wire));
      const clickPill = async (): Promise<void> => { const b = await paints(page); await page.click("#pill"); await painted(page, b); };
      const pre = await page.evaluate(() => ({ tab: document.getElementById("pill")!.getAttribute("tabindex"), act: document.getElementById("pill")!.dataset.act }));
      assert.equal(pre.tab, "0", what + ": the pill is a Tab stop before the press (markPathLink)");
      assert.equal(pre.act, "openpath", what + ": the pill carries the openpath action");
      // 1 the fresh page, a mouse click on the pill (the press strips its tabindex, so nothing focusable was pressed)
      await clickPill();
      noRing(await ringOf(page), what + ", a pill click on the fresh page");
      // 2 Escape (a key), the pill again
      await page.keyboard.press("Escape"); await closed(page);
      await clickPill();
      noRing(await ringOf(page), what + ", a pill click after Escape");
      // 3 Escape, a click on plain text, the pill
      await page.keyboard.press("Escape"); await closed(page);
      await page.click("#plain");
      await clickPill();
      noRing(await ringOf(page), what + ", a pill click after a click on plain text");
      // the controls, in the same open: a Tab from the bar's X reaches the body with the ring (the keyboard's own arrival)
      await page.evaluate(() => { (document.querySelector(".fileview-close") as HTMLElement).focus(); });
      let reached = false;
      for (let i = 0; i < 8 && !reached; i++) { await page.keyboard.press("Tab"); await frames(page, 1); reached = (await ringOf(page)).active === BODY; }
      assert.ok(reached, what + ": a Tab from the bar reaches the body");
      ring(await ringOf(page), what + ", a Tab into the body");
      // a Raw toggle focused after that key wears the ring; Enter on it repaints and hands the keyboard to the body WITH the ring
      const focusedRaw = await page.evaluate(() => { const b = Array.from(document.querySelectorAll(".fileview-acts button")).find((x) => x.textContent === "Raw") as HTMLElement; b.focus(); return { active: document.activeElement === b, fv: b.matches(":focus-visible") }; });
      assert.equal(focusedRaw.active, true, what + ": the Raw toggle took the focus");
      assert.equal(focusedRaw.fv, true, what + ": the Raw toggle wears the ring after the keyboard's Tab");
      const p1 = await paints(page);
      await page.keyboard.press("Enter");
      await painted(page, p1);
      const raw = await page.evaluate(() => !!document.querySelector(".fileview-body code.hljs"));
      assert.equal(raw, true, what + ": Enter on Raw painted the Raw view");
      ring(await ringOf(page), what + ", Enter on the Tab-focused Raw toggle");
      // a mouse click on Rendered: the button is mouse-focused, and the hand-over passes no ring
      const p2 = await paints(page);
      const rb = await page.evaluate(() => { const b = Array.from(document.querySelectorAll(".fileview-acts button")).find((x) => x.textContent === "Rendered") as HTMLElement; const r = b.getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; });
      await page.mouse.click(rb.x, rb.y);
      await painted(page, p2);
      noRing(await ringOf(page), what + ", a mouse click on Rendered");
      assert.deepEqual(errors, [], what + ": no page errors");
      await page.close();
    }
  });
});

test("in a browser, on the Files pane at 900 and 380 px: an open with no gesture (the relay's situation) and an open after a click on plain text (a Recent row's) land with the body holding the keyboard and NO :focus-visible ring; an Outline pick by End and Enter lands the heading with the ring, a pick by mouse without", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const [w, h] of [[900, 700], [380, 640]] as Array<[number, number]>) {
      const what = "pane " + w + "px";
      const html = pageHtml("pane", { [REPORT]: NOTE }, MT).replace('<body class="fileview-pane">', () => '<body class="fileview-pane"><p id="plain">plain text outside the viewer</p>');
      const { page, errors } = await pageOf(browser, w, h, html);
      const openByScript = async (): Promise<void> => {
        const b = await paints(page);
        await page.evaluate(([p, sid]: [string, string]) => { (window as any).FV.openFileView(p, sid, null); }, [REPORT, SID]);
        await painted(page, b);
      };
      // 1 no gesture at all: the relayed open's situation (the click was in another frame)
      const before = await page.evaluate(() => (document.activeElement as HTMLElement).tagName);
      assert.equal(before, "BODY", what + ": nothing holds the keyboard before the open");
      await openByScript();
      noRing(await ringOf(page), what + ", an open with no gesture");
      // 2 Escape, a click on plain text (a Recent row is a plain div: the focus falls to the document's body), the open
      await page.keyboard.press("Escape"); await closed(page);
      await page.click("#plain");
      await openByScript();
      noRing(await ringOf(page), what + ", an open after a click on plain text");
      if (w >= 900) {
        // the Outline by keyboard: the button focused after a key wears the ring, Enter opens the popover (which takes the
        // focus and the ring with it), End moves to Beta, Enter picks: the heading lands and the body holds the keyboard WITH
        // the ring, read off the popover before its removal
        await page.keyboard.press("Home");
        await frames(page, 2);
        const btnState = await page.evaluate(() => { const b = document.querySelector(".fileview-outline-btn") as HTMLElement; b.focus(); return { hidden: b.hidden, active: document.activeElement === b, fv: b.matches(":focus-visible") }; });
        assert.equal(btnState.hidden, false, what + ": the Outline button shows for the three headings");
        assert.equal(btnState.active, true, what + ": the Outline button took the focus");
        assert.equal(btnState.fv, true, what + ": the Outline button wears the ring after a key");
        await page.keyboard.press("Enter");
        await page.waitForFunction(() => !!document.querySelector(".fileview-outline"), null, { timeout: 4000 });
        await frames(page, 1);
        const popHeld = await page.evaluate(() => { const p = document.querySelector(".fileview-outline") as HTMLElement; return { active: document.activeElement === p, rows: p.querySelectorAll(".fileview-outline-row").length }; });
        assert.equal(popHeld.active, true, what + ": the popover holds the keyboard at its open");
        assert.equal(popHeld.rows, 3, what + ": three rows, one per heading");
        await page.keyboard.press("End");
        await frames(page, 1);
        await page.keyboard.press("Enter");
        await page.waitForFunction(() => !document.querySelector(".fileview-outline"), null, { timeout: 4000 });
        await frames(page, 3);
        const picked = await ringOf(page);
        assert.ok(picked.scrollTop > 0, what + ": the pick landed Beta (scrollTop " + picked.scrollTop + ")");
        ring(picked, what + ", an Outline pick by End and Enter");
        // the Outline by mouse: the button and a row are mouse-pressed, and the hand-over passes no ring
        await page.click(".fileview-outline-btn");
        await page.waitForFunction(() => !!document.querySelector(".fileview-outline"), null, { timeout: 4000 });
        await frames(page, 1);
        await page.click(".fileview-outline-row >> nth=1");
        await page.waitForFunction(() => !document.querySelector(".fileview-outline"), null, { timeout: 4000 });
        await frames(page, 3);
        const mousePicked = await ringOf(page);
        noRing(mousePicked, what + ", an Outline pick by mouse");
        assert.notEqual(mousePicked.scrollTop, picked.scrollTop, what + ": the mouse pick landed Alpha, another place (scrollTop " + mousePicked.scrollTop + " after " + picked.scrollTop + ")");
      }
      assert.deepEqual(errors, [], what + ": no page errors");
      await page.close();
    }
  });
});

/** Press `k` and wait two frames (the lift is synchronous in the keydown; the read follows the paint). */
const pressed = async (page: any, k: string): Promise<void> => { await page.keyboard.press(k); await frames(page, 2); };
/** The body's scrollTop has grown past `from`: the key's own scroll ran (Chromium animates keyboard scrolls, so the read waits
 *  for the first moved frame rather than a fixed count). */
const scrolledPast = (page: any, from: number): Promise<unknown> => page.waitForFunction((f: number) => (document.querySelector(".fileview-body") as HTMLElement).scrollTop > f, from, { timeout: 4000 });
/** In the page: select fourteen characters of the third paragraph's text, and return them. */
function selectInBody(): string {
  const p = document.querySelectorAll(".fileview-md > p")[2] as HTMLElement;
  const r = document.createRange(); r.setStart(p.firstChild!, 6); r.setEnd(p.firstChild!, 20);
  const s = document.getSelection()!; s.removeAllRanges(); s.addRange(r);
  return s.toString();
}
/** T367: A- and A+ ride the zoom glyph's flyout, hidden until the glyph is pressed and closed by any mousedown outside it. When it is
 *  closed, a MOUSE click on the glyph's rectangle opens it (the scenes are about a mouse hand-over, so the glyph is pressed the same way;
 *  the glyph is mouse-focused, and the step's paint reads the mouse-focused A+ or A- it hands the keyboard from). */
async function openZoomByMouse(page: any): Promise<void> {
  const at = await page.evaluate(() => { const m = document.querySelector(".fileview-zoom-menu") as HTMLElement; if (!m.hidden) return null; const r = (document.querySelector(".fileview-zoom-btn") as HTMLElement).getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; });
  if (!at) return;
  await page.mouse.click(at.x, at.y);
  await page.waitForFunction(() => !(document.querySelector(".fileview-zoom-menu") as HTMLElement).hidden, null, { timeout: 4000 });
}
/** A mouse click on the bar's A+ (a text-size step: the paint hands the keyboard to the body, reading a mouse-focused holder). */
async function clickTextUp(page: any): Promise<void> {
  const b = await paints(page);
  await openZoomByMouse(page);
  const at = await page.evaluate(() => { const x = Array.from(document.querySelectorAll(".fileview-bar button")).find((e) => (e.textContent || "").trim() === "A+") as HTMLElement; const r = x.getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; });
  await page.mouse.click(at.x, at.y);
  await painted(page, b);
}
/** The key scenes over an open that handed the body the keyboard without the ring: PageDown brings the ring and the scroll, a
 *  mouse click on A+ hands over ringless and ArrowDown brings it back, Ctrl+C over a selection brings none and keeps the selection. */
async function keyScenes(page: any, what: string): Promise<void> {
  const r0 = await ringOf(page);
  noRing(r0, what + ", before any key");
  await pressed(page, "PageDown");
  ring(await ringOf(page), what + ", PageDown after a ringless hand-over (at 7fbced030 the focus call's verdict held through every key)");
  await scrolledPast(page, r0.scrollTop);
  assert.ok((await ringOf(page)).scrollTop > r0.scrollTop, what + ": PageDown scrolled the body (the lift kept the key's own scroll)");
  await clickTextUp(page);
  noRing(await ringOf(page), what + ", a mouse click on A+ (a mouse-focused holder passes no ring)");
  await pressed(page, "ArrowDown");
  ring(await ringOf(page), what + ", ArrowDown after the mouse click on A+");
  // a mouse click on A- hands over ringless again; a Ctrl+C over a selection in the body is a chord and lifts nothing
  const b = await paints(page);
  await openZoomByMouse(page);
  const dn = await page.evaluate(() => { const x = Array.from(document.querySelectorAll(".fileview-bar button")).find((e) => (e.textContent || "").trim() === "A\u2212") as HTMLElement; const r = x.getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; });
  await page.mouse.click(dn.x, dn.y);
  await painted(page, b);
  noRing(await ringOf(page), what + ", a mouse click on A-");
  const picked = await page.evaluate(selectInBody);
  assert.equal(picked.length, 14, what + ": fourteen characters selected in the body (read " + JSON.stringify(picked) + ")");
  await pressed(page, "Control+c");
  noRing(await ringOf(page), what + ", Ctrl+C over the selection (a chord: the heuristic's own line, no lift)");
  const kept = await page.evaluate(() => document.getSelection()!.toString());
  assert.equal(kept, picked, what + ": the selection stands after the chord");
  await pressed(page, "ArrowDown");
  const after = await ringOf(page);
  ring(after, what + ", ArrowDown after the chord");
  const still = await page.evaluate(() => document.getSelection()!.toString());
  assert.equal(still, picked, what + ": the selection stands through the lift (no blur of the selection, no selectionchange)");
}

test("in a browser, in the chat modal, the feed modal and the Files pane at 900 px: after a hand-over without the ring (a pill click, a gestureless open, a mouse click on A+) the first key pressed on the body brings the accent ring and the key's own scroll; Ctrl+C over a selection inside the body brings none and keeps the selection", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const PL = pathLinksBundle();
    for (const mode of ["chat", "feed"] as Array<"chat" | "feed">) {
      const what = mode + " 900px, keys";
      const base = pageHtml(mode, { [REPORT]: NOTE }, MT).replace('<body class="">', () => '<body class=""><div id="content" style="height:200px;overflow:auto"><p id="plain">plain transcript text</p><p>a line with a <span id="pill">docs/report.md</span> pill</p><div style="height:3000px"></div></div>');
      const wire = "<script>" + PL + "</script><script>PL.markPathLink(document.getElementById('pill'), " + JSON.stringify(REPORT) + ", false, " + JSON.stringify(SID) + ");"
        + " document.body.addEventListener('click', function (e) { var a = e.target && e.target.closest ? e.target.closest('[data-act=\"openpath\"]') : null; if (a) FV.openFileView(a.dataset.path, a.dataset.sid || null, null); });</script>";
      const { page, errors } = await pageOf(browser, 900, 700, spliced(base, wire));
      const b = await paints(page); await page.click("#pill"); await painted(page, b);
      await keyScenes(page, what);
      assert.deepEqual(errors, [], what + ": no page errors");
      await page.close();
    }
    const what = "pane 900px, keys";
    const { page, errors } = await pageOf(browser, 900, 700, pageHtml("pane", { [REPORT]: NOTE }, MT));
    const b = await paints(page);
    await page.evaluate(([p, sid]: [string, string]) => { (window as any).FV.openFileView(p, sid, null); }, [REPORT, SID]);
    await painted(page, b);
    await keyScenes(page, what);
    assert.deepEqual(errors, [], what + ": no page errors");
    await page.close();
  });
});

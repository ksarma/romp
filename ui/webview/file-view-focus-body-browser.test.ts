// The body holds the keyboard, over the REAL viewer in headless Chromium (plans/markdown-viewer.md Slice 6, item 1; the
// audit's "the viewer never takes focus"). `.fileview-body` is a Tab stop (tabindex 0) and openFileView's takeKeyboard gives
// it the keyboard after the open's first paint and after a paint the reader asked for from the viewer's own chrome, unless
// something else holds it. Measured here, through real-viewer-leg.ts's page: on the Files pane at 900 and 380 px and in the
// chat modal, a note opened with NO click scrolls on PageDown, Space and the arrows and closes on Escape (the acceptance:
// PageDown moves scrollTop with no prior click); a Tab from the bar reaches the body and shows the accent `:focus-visible`
// ring, a mouse press inside it shows none; a press on a path link inside the body lands the focus on the body element, the
// nearest focusable ancestor, where path-links-pointer-focus.test.ts:119 pins the document's body for a link outside the
// viewer (the viewer-context variant of that pin); with the Comments panel open and its box focused, the Rendered/Raw
// toggle's paint leaves the keyboard in the box, and a real click on the toggle hands it from the button to the body; a
// press on a highlight mid-press reads the body's tabindex as 0 and the mark's as absent (the panel's pressedMarks strip
// selects marks, never the body) with the focus on the body, and the release focuses the mark, not the body. The chat
// scene runs render.ts's own window keydown handlers, lifted from its source (real-viewer-leg.ts chatKeysScript, shared with
// the Outline leg) as file-view-links-browser.test.ts lifts the chat's click opener, over a composer and a #content stand-in: a printable key with the viewer up lands nowhere
// (typeFromAnywhereTarget stands aside for a full-pane surface), and after Escape the same key lands in the composer; the
// chat's ArrowUp/Down handler scrolls #content for any non-typing target and names no exception for the viewer, so the arrow
// is read as either mover (a render.ts change, not the viewer's; recorded for the unit that owns render.ts). Before item 1
// the body had no tabindex and nothing focused it: red at the first PageDown over a git archive of the base. Skips LOUDLY
// without a playwright browser (CI installs none), as the other legs do. Synthetic values only: an invented note,
// /repo/notes-api paths, the placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, openPanel, pageHtml, frames, paintsReach, chatKeysScript, ORIGIN, REPORT, SID, MT, STATUS, PARA } from "./real-viewer-leg";
import { makeAnchor } from "./anchor-map";

const T0 = 1757145600000;
// the note: an intro with a path link (./report.md resolves to the note itself, so its click is a replace-open of the same
// file) and a passage a comment marks, then forty paragraphs so every viewport scrolls
const INTRO = "See ./report.md for the plan, and check the target words in this sentence before the release.";
const NOTE = "# Report\n\n" + INTRO + "\n\n" + Array.from({ length: 40 }, (_, i) => PARA(i + 1)).join("\n\n") + "\n";
const QUOTE = "target words";
const AT = NOTE.indexOf(QUOTE);
const COMMENT = { id: (T0 + 1) + "-" + AT, author: "you", ts: T0 + 1, body: "Which words?", anchor: makeAnchor(NOTE, { start: AT, end: AT + QUOTE.length }), anchorAt: AT, replies: [], resolved: false };
const status = { ...STATUS, store: { ...STATUS.store, comments: [COMMENT] }, storeMtimeNs: "1757145600000000061", unsent: { comments: [], replies: [], accepted: 0, rejected: 0, watermark: null } };

type Focus = { active: string; bodyTab: string | null; scrollTop: number; outline: string; outlineColor: string; accent: string };
/** In the page: the focused element's name, the body's tabindex, its scrollTop, and its computed outline beside the resolved accent. */
function readFocus(): Focus {
  const body = document.querySelector(".fileview-body") as HTMLElement | null;
  const a = document.activeElement as HTMLElement | null;
  const name = (n: Element | null): string => !n ? "none" : n.tagName + (n.id ? "#" + n.id : "") + (n.className && typeof n.className === "string" ? "." + n.className.split(/\s+/).filter(Boolean).join(".") : "");
  const probe = document.createElement("span"); probe.style.color = "var(--accent)"; document.body.appendChild(probe);
  const accent = getComputedStyle(probe).color; probe.remove();
  const cs = body ? getComputedStyle(body) : null;
  return { active: name(a), bodyTab: body ? body.getAttribute("tabindex") : "no-body", scrollTop: body ? body.scrollTop : -1, outline: cs ? cs.outlineStyle : "no-body", outlineColor: cs ? cs.outlineColor : "no-body", accent };
}
const focusOf = (page: any): Promise<Focus> => page.evaluate(readFocus);
const scrollTopOf = (page: any): Promise<number> => page.evaluate(() => (document.querySelector(".fileview-body") as HTMLElement).scrollTop);
/** Press `key` and wait for the body's scrollTop to pass `from` (Chromium may animate a keyboard scroll), or fail naming the key. */
async function keyScrolls(page: any, key: string, from: number, what: string): Promise<number> {
  await page.keyboard.press(key);
  const moved = await page.waitForFunction((v: number) => (document.querySelector(".fileview-body") as HTMLElement).scrollTop > v, from, { timeout: 4000 }).then(() => true, () => false);
  const now = await scrollTopOf(page);
  assert.ok(moved, what + ": " + key + " moved the body's scrollTop past " + from + " (read " + now + "; before item 1 the body held no focus and the key scrolled nothing)");
  return now;
}
const BODY = "DIV.fileview-body";

async function keysScene(page: any, what: string): Promise<void> {
  const f0 = await focusOf(page);
  assert.equal(f0.active, BODY, what + ": the open's first paint focused the body with no click (read " + f0.active + ")");
  assert.equal(f0.bodyTab, "0", what + ": the body carries tabindex 0");
  assert.equal(f0.scrollTop, 0, what + ": the note opens at its top");
  const s1 = await keyScrolls(page, "PageDown", 0, what);
  const s2 = await keyScrolls(page, "Space", s1, what);
  await keyScrolls(page, "ArrowDown", s2, what);
  await page.keyboard.press("End");
  await page.waitForFunction(() => { const b = document.querySelector(".fileview-body") as HTMLElement; return b.scrollTop >= b.scrollHeight - b.clientHeight - 1; }, null, { timeout: 4000 });
  await page.keyboard.press("Home");
  await page.waitForFunction(() => (document.querySelector(".fileview-body") as HTMLElement).scrollTop === 0, null, { timeout: 4000 });
  await page.keyboard.press("Escape");
  await page.waitForFunction(() => !document.getElementById("romp-fileview"), null, { timeout: 4000 });
}

test("in a browser, on the Files pane at 900 and 380 px: the note opened with no click has the keyboard, PageDown, Space and ArrowDown scroll it, End and Home reach the ends, Escape closes it; a Tab from the bar reaches the body with the accent focus ring and a mouse press inside it shows none; a press on a path link inside the body lands the focus on the body element, and the click's replace-open hands it to the new body", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const [w, h] of [[900, 700], [380, 640]] as Array<[number, number]>) {
      const { page, errors } = await openViewer(browser, "pane", w, h, { docs: { [REPORT]: NOTE } });
      await keysScene(page, "pane " + w + "px");
      assert.deepEqual(errors, [], "no page errors at " + w + "px");
      await page.close();
    }
    // the ring: a Tab from the bar's last control reaches the body and the accent ring shows; a press inside the body that
    // MOVES the focus there (from the bar again: a press on an already focused body changes no focus and so keeps the ring
    // the keyboard earned) lands the keyboard on the body with no ring (a pointer's focus is not :focus-visible)
    const { page, errors } = await openViewer(browser, "pane", 900, 700, { docs: { [REPORT]: NOTE } });
    await page.evaluate(() => { (document.querySelector(".fileview-close") as HTMLElement).focus(); });
    let reached = false;
    for (let i = 0; i < 6 && !reached; i++) { await page.keyboard.press("Tab"); await frames(page, 1); reached = (await focusOf(page)).active === BODY; }
    const tabbed = await focusOf(page);
    assert.ok(reached, "a Tab from the bar reaches the body (read " + tabbed.active + ")");
    assert.notEqual(tabbed.outline, "none", "the keyboard's focus shows the ring (outline-style " + tabbed.outline + ")");
    assert.equal(tabbed.outlineColor, tabbed.accent, "the ring is the accent (var(--accent), never a status colour)");
    await page.evaluate(() => { (document.querySelector(".fileview-close") as HTMLElement).focus(); });
    const para = await page.evaluate(() => { const p = document.querySelectorAll(".fileview-md > p")[1] as HTMLElement; const r = p.getBoundingClientRect(); return { x: r.left + Math.min(40, r.width / 2), y: r.top + 4 }; });
    await page.mouse.click(para.x, para.y);
    await frames(page, 1);
    const pressed = await focusOf(page);
    assert.equal(pressed.active, BODY, "a press on the body's plain text lands the focus on the body element, the nearest focusable ancestor (read " + pressed.active + ")");
    assert.equal(pressed.outline, "none", "…with no ring for a pointer's focus (the :focus rule)");
    // the pin's variant: a press on a path link inside the body (the pointer-focus strip takes the link's tabindex for the
    // press) lands on the body element; the release's click is a replace-open of the same note, whose first paint focuses the
    // NEW body
    const link = await page.evaluate(() => { const a = document.querySelector(".fileview-md .file-uri-link") as HTMLElement; const r = a.getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2, path: a.dataset.path || null, tab: a.getAttribute("tabindex") }; });
    assert.equal(link.path, REPORT, "the intro's ./report.md is a path link to the note itself");
    assert.equal(link.tab, "0", "the link is a Tab stop before the press");
    const oldBody = await page.evaluateHandle(() => document.querySelector(".fileview-body"));
    const paintsBefore: number = await page.evaluate(() => (window as any).__paints);
    await page.mouse.move(link.x, link.y);
    await page.mouse.down();
    await frames(page, 1);
    const mid = await page.evaluate(() => ({ active: (document.activeElement as HTMLElement).className, tab: (document.querySelector(".fileview-md .file-uri-link") as HTMLElement).getAttribute("tabindex") }));
    assert.equal(mid.tab, null, "mid-press the link wears no tabindex (path-links.ts's press)");
    assert.equal(mid.active, "fileview-body", "…so the press landed the focus on the body element (the document's body before item 1)");
    await page.mouse.up();
    await paintsReach(page, paintsBefore + 1);
    await frames(page, 2);
    const after = await page.evaluate((old: Element | null) => { const b = document.querySelector(".fileview-body"); return { same: b === old, active: (document.activeElement as HTMLElement).className }; }, oldBody);
    assert.equal(after.same, false, "the click replaced the viewer with a fresh open of the note");
    assert.equal(after.active, "fileview-body", "…whose first paint gave the new body the keyboard (read " + after.active + ")");
    assert.deepEqual(errors, [], "no page errors");
    await page.close();
  });
});

test("in a browser, in the chat modal under render.ts's own key handlers: the composer keeps the keyboard when it holds it at the open; with nothing focused the body takes it and PageDown, Space, End and Home scroll the note; a typed letter with the viewer up lands nowhere and after Escape lands in the composer; ArrowDown is read against the chat's arrow handler", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const page = await browser.newPage({ viewport: { width: 1000, height: 700 } });
    const errors: string[] = [];
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    // the chat page's sheet and the viewer bundle, plus the chat's composer, its transcript box and its key handlers
    // spliced at the page's LAST `</body></html>` (the viewer bundle's own text holds the same bytes earlier, and a replace at the
    // first occurrence put the script inside the bundle) and with a function replacer for the body tag (a string replacement
    // would read `$` patterns)
    const base = pageHtml("chat", { [REPORT]: NOTE }, MT).replace('<body class="">', () => '<body class=""><textarea id="composer-input"></textarea><div id="content" style="height:120px;overflow:auto"><div style="height:4000px"></div></div>');
    const tail = base.lastIndexOf("</body></html>");
    assert.ok(tail > 0, "the page ends with </body></html>");
    const html = base.slice(0, tail) + "<script>" + chatKeysScript() + "</script>" + base.slice(tail);
    await page.route((u: URL) => u.href.startsWith(ORIGIN), (route: any) => route.fulfill({ status: 200, contentType: "text/html", body: html }));
    await page.goto(ORIGIN + "/");
    const open = async () => {
      const before: number = await page.evaluate(() => (window as any).__paints);
      await page.evaluate(([p, sid]: [string, string]) => { (window as any).FV.openFileView(p, sid, null); }, [REPORT, SID]);
      await paintsReach(page, before + 1);
      await frames(page, 2);
    };
    // the composer holds the keyboard at the open: the paint leaves it there, and PageDown moves the note not at all
    await page.focus("#composer-input");
    await open();
    const held = await focusOf(page);
    assert.equal(held.active, "TEXTAREA#composer-input", "the composer kept the keyboard through the open's first paint (read " + held.active + ")");
    await page.keyboard.press("PageDown");
    await frames(page, 3);
    assert.equal(await scrollTopOf(page), 0, "PageDown with the composer focused scrolls the note nowhere");
    await page.keyboard.press("Escape");
    await page.waitForFunction(() => !document.getElementById("romp-fileview"), null, { timeout: 4000 });
    // nothing focused: the body takes it, and the keys scroll the note
    await page.evaluate(() => { (document.activeElement as HTMLElement | null)?.blur(); });
    await open();
    const f0 = await focusOf(page);
    assert.equal(f0.active, BODY, "chat modal: the first paint focused the body (read " + f0.active + ")");
    const s1 = await keyScrolls(page, "PageDown", 0, "chat modal");
    await keyScrolls(page, "Space", s1, "chat modal");
    await page.keyboard.press("End");
    await page.waitForFunction(() => { const b = document.querySelector(".fileview-body") as HTMLElement; return b.scrollTop >= b.scrollHeight - b.clientHeight - 1; }, null, { timeout: 4000 });
    await page.keyboard.press("Home");
    await page.waitForFunction(() => (document.querySelector(".fileview-body") as HTMLElement).scrollTop === 0, null, { timeout: 4000 });
    // ArrowDown: the chat's own arrow handler scrolls #content for every non-typing target and preventDefaults, with no
    // exception for the viewer (render.ts, the single-key shortcuts): the key moves the note or the transcript box, never
    // nothing. Which one is render.ts's call, recorded for its owner; the viewer's half (the body focused, the key
    // reaching it) is what this reads.
    const content0: number = await page.evaluate(() => (document.getElementById("content") as HTMLElement).scrollTop);
    await page.keyboard.press("ArrowDown");
    const arrow = await page.waitForFunction((c0: number) => (document.querySelector(".fileview-body") as HTMLElement).scrollTop > 0 || (document.getElementById("content") as HTMLElement).scrollTop > c0, content0, { timeout: 4000 }).then(() => true, () => false);
    const read = await page.evaluate((c0: number) => ({ body: (document.querySelector(".fileview-body") as HTMLElement).scrollTop, content: (document.getElementById("content") as HTMLElement).scrollTop - c0, active: (document.activeElement as HTMLElement).className }), content0);
    assert.ok(arrow, "ArrowDown with the body focused moved the note or, under render.ts's arrow handler, the transcript box (read body " + read.body + ", content " + read.content + ")");
    assert.equal(read.active, "fileview-body", "…and the keyboard stayed on the body");
    // a printable key with the viewer up: the chat's type-to-compose stands aside for a full-pane surface, so the letter
    // lands nowhere and the keyboard stays on the body; after Escape the same key lands in the composer (the handler is live)
    await page.keyboard.press("x");
    await frames(page, 2);
    const typed = await page.evaluate(() => ({ active: (document.activeElement as HTMLElement).className, value: (document.getElementById("composer-input") as HTMLTextAreaElement).value }));
    assert.equal(typed.value, "", "a letter typed with the viewer up reached no composer");
    assert.equal(typed.active, "fileview-body", "…and the keyboard stayed on the body");
    await page.keyboard.press("Escape");
    await page.waitForFunction(() => !document.getElementById("romp-fileview"), null, { timeout: 4000 });
    await page.keyboard.press("y");
    await page.waitForFunction(() => (document.getElementById("composer-input") as HTMLTextAreaElement).value === "y", null, { timeout: 4000 });
    assert.equal((await focusOf(page)).active, "TEXTAREA#composer-input", "with the viewer closed the chat's type-to-compose put the letter in the composer (the lifted handler is live)");
    assert.deepEqual(errors, [], "no page errors");
    await page.close();
  });
});

type Pts = { sx: number; sy: number; ex: number; ey: number };
/** In the page: the press and release points over the first `start` and the `end` after it in the Rendered body's text. */
function pointsIn(spec: { start: string; end: string }): Pts {
  const root = document.querySelector(".fileview-md") as HTMLElement;
  const texts: Text[] = [];
  const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  for (let n = w.nextNode(); n; n = w.nextNode()) texts.push(n as Text);
  const si = texts.findIndex((n) => n.data.includes(spec.start));
  if (si < 0) throw new Error("start not in the text: " + spec.start);
  const sNode = texts[si], sOff = sNode.data.indexOf(spec.start);
  let eNode: Text | null = null, eOff = -1;
  for (let i = si; i < texts.length && !eNode; i++) { const j = texts[i].data.indexOf(spec.end, i === si ? sOff : 0); if (j >= 0) { eNode = texts[i]; eOff = j + spec.end.length; } }
  if (!eNode) throw new Error("end not in the text after the start: " + spec.end);
  const rect = (n: Text, off: number) => { const r = document.createRange(); r.setStart(n, off); r.setEnd(n, off + 1); return r.getBoundingClientRect(); };
  const a = rect(sNode, sOff), b = rect(eNode, eOff - 1);
  return { sx: a.left + Math.min(1.5, a.width / 3), sy: a.top + a.height / 2, ex: b.right - Math.min(1.5, b.width / 3), ey: b.top + b.height / 2 };
}
type MarkState = { bodyTab: string | null; markTab: string | null; active: string; activeId: string | null };
function readMark(cid: string): MarkState {
  const body = document.querySelector(".fileview-body") as HTMLElement;
  const m = document.querySelector('.fileview-md mark[data-id="' + cid + '"]');
  const a = document.activeElement as HTMLElement | null;
  return { bodyTab: body.getAttribute("tabindex"), markTab: m ? m.getAttribute("tabindex") : "no-mark", active: a ? a.tagName + "." + String(a.className).split(/\s+/).join(".") : "none", activeId: a && a.dataset ? a.dataset.id || null : null };
}

test("in a browser, with the Comments panel open: a press on a highlight mid-press reads the body's tabindex as 0 and the mark's as absent, the focus on the body, and the release focuses the mark, not the body; the composer's box keeps the keyboard through the Rendered/Raw toggle's paint when its click was not a press on the button, and a real click on the toggle hands the keyboard from the button to the body", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const page = await browser.newPage({ viewport: { width: 900, height: 700 } });
    const errors: string[] = [];
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    const html = pageHtml("pane", { [REPORT]: NOTE }, MT);
    await page.route((u: URL) => u.href.startsWith(ORIGIN), (route: any) => route.fulfill({ status: 200, contentType: "text/html", body: html }));
    await page.goto(ORIGIN + "/");
    await page.evaluate(([p, sid, st]: [string, string, unknown]) => { (window as any).__status = st; (window as any).FV.openFileView(p, sid, null); }, [REPORT, SID, status]);
    await page.waitForFunction(() => !!document.querySelector(".fileview-md > p"), null, { timeout: 10000 });
    await frames(page, 2);
    await openPanel(page);
    await page.waitForFunction((c: string) => !!document.querySelector('.fileview-md mark[data-act="fcopen"][data-id="' + c + '"]'), COMMENT.id, { timeout: 10000 });
    await frames(page, 2);
    // the mark, mid-press and at the release
    const before: MarkState = await page.evaluate(readMark, COMMENT.id);
    assert.equal(before.markTab, "0", "the mark wears tabindex 0 before the press");
    assert.equal(before.bodyTab, "0", "the body wears tabindex 0 before the press");
    const mp = await page.evaluate((c: string) => { const r = (document.querySelector('.fileview-md mark[data-id="' + c + '"]') as HTMLElement).getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; }, COMMENT.id);
    await page.mouse.move(mp.x, mp.y);
    await page.mouse.down();
    await frames(page, 1);
    const mid: MarkState = await page.evaluate(readMark, COMMENT.id);
    assert.equal(mid.markTab, null, "mid-press the mark wears no tabindex (the panel's strip)");
    assert.equal(mid.bodyTab, "0", "mid-press the body still wears tabindex 0 (the strip selects marks, never the body)");
    assert.equal(mid.active, "DIV.fileview-body", "mid-press the focus is on the body, the nearest focusable ancestor of the pressed mark (read " + mid.active + ")");
    await page.mouse.up();
    await frames(page, 3);
    const rel: MarkState = await page.evaluate(readMark, COMMENT.id);
    assert.equal(rel.activeId, COMMENT.id, "the release focused the mark, not the body (read " + rel.active + ")");
    assert.equal(rel.markTab, "0", "the mark's tabindex is back");
    // the composer's box: a drag over plain words, the float, the box focused
    await page.evaluate(() => { getSelection()!.removeAllRanges(); });
    const pts: Pts = await page.evaluate(pointsIn, { start: "Paragraph 2", end: "ipsum" });
    await page.mouse.move(pts.sx, pts.sy);
    await page.mouse.down();
    await page.mouse.move((pts.sx + pts.ex) / 2, (pts.sy + pts.ey) / 2, { steps: 3 });
    await page.mouse.move(pts.ex, pts.ey, { steps: 6 });
    await page.mouse.up();
    await page.waitForFunction(() => { const f = document.querySelector(".fc-float") as HTMLElement | null; return !!f && !f.hidden; }, null, { timeout: 5000 });
    await page.click(".fc-float");
    await frames(page, 2);
    const boxHeld = await page.evaluate(() => { const i = document.querySelector(".fc-composer .fc-input"); return !!i && document.activeElement === i; });
    assert.equal(boxHeld, true, "the composer opened with its box focused");
    // the toggle's paint with the box holding the keyboard (a click that was no press on the button: the button never took
    // the focus, as a keyboard activation or a script's click would not): the box keeps it
    const paints0: number = await page.evaluate(() => (window as any).__paints);
    await page.evaluate(() => { const b = Array.from(document.querySelectorAll(".fileview-acts button")).find((x) => x.textContent === "Raw") as HTMLElement; b.click(); });
    await paintsReach(page, paints0 + 1);
    await frames(page, 2);
    const afterRaw = await page.evaluate(() => { const i = document.querySelector(".fc-composer .fc-input"); return { box: !!i, held: !!i && document.activeElement === i, raw: !!document.querySelector(".fileview-body code.hljs"), active: (document.activeElement as HTMLElement).className }; });
    assert.equal(afterRaw.raw, true, "the Raw paint happened");
    assert.equal(afterRaw.box, true, "the composer's box survived the paint (the panel retargets it)");
    assert.equal(afterRaw.held, true, "…and kept the keyboard through it (read " + afterRaw.active + ")");
    // a real click on the toggle: the press focuses the button, and the paint hands the keyboard from the button to the body
    const paints1: number = await page.evaluate(() => (window as any).__paints);
    const rb = await page.evaluate(() => { const b = Array.from(document.querySelectorAll(".fileview-acts button")).find((x) => x.textContent === "Rendered") as HTMLElement; const r = b.getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; });
    await page.mouse.click(rb.x, rb.y);
    await paintsReach(page, paints1 + 1);
    await frames(page, 2);
    const clicked = await focusOf(page);
    assert.equal(clicked.active, BODY, "a real click on Rendered left the keyboard on the body, not on the button (read " + clicked.active + ")");
    assert.deepEqual(errors, [], "no page errors");
    await page.close();
  });
});

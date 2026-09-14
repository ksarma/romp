// The Outline over the REAL viewer in headless Chromium (plans/markdown-viewer.md Slice 6, item 2; the acceptance: choosing
// the 40th heading in Outline puts it at the top). Through real-viewer-leg.ts's page, on the Files pane at 900 and 380 px
// and in the chat modal under render.ts's own window key handlers (chatKeysScript): the Outline button renders in the
// actions row after the Rendered/Raw toggle; a click opens the popover inside the card, capped to the body's height and
// scrolling within itself, its colours the menu tokens' (the dark theme's, and the light theme's once body.theme-light is
// on); a click on the 40th row lands that heading with its top at the body's edge less its scroll margin (where a `#` link
// puts it) and the body's scrollTop moved, the keyboard back on the body; the row for the heading inside a closed <details>
// opens the fold; Escape closes the popover and the viewer stays; ArrowDown twice and Enter pick the third heading from the
// keyboard, and in the chat modal the arrows never reach the chat's transcript scroller (the popover takes them first);
// the front-matter block has no row and the formula heading's row shows KaTeX's text; the Raw view hides the button. The
// cost is measured over a 500-heading note (the click to the popover's paint, in milliseconds, printed for the record).
// Before item 2: no Outline button (red at the first assertion over a git archive of the base). Skips LOUDLY without a
// playwright browser (CI installs none), as the other legs do. Synthetic values only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, pageHtml, frames, paintsReach, chatKeysScript, ORIGIN, REPORT, SID, MT, MT2 } from "./real-viewer-leg";
import { OUTLINE_NOTE, OUTLINE_HEADINGS, FOLD_HEADING, manyHeadings } from "./file-view-outline-fixture";

const BTN = ".fileview-acts .fileview-outline-btn";
const POP = ".fileview-outline";
type Box = { left: number; top: number; right: number; bottom: number };
type PopRead = { count: number; inCard: boolean; card: Box; pop: Box; clientH: number; scrollH: number; bodyH: number; focused: boolean; expanded: string | null; bg: string; fg: string; border: string; font: string; curBg: string; menuBg: string; menuFg: string; menuBorder: string; menuHover: string; texts: string[]; ids: string[]; depths: string[] };
/** In the page: the open popover against the card and the body, its computed colours beside the tokens' resolutions. */
function readPopover(): PopRead {
  const pop = document.querySelector(".fileview-outline") as HTMLElement;
  const card = document.querySelector(".fileview") as HTMLElement, body = document.querySelector(".fileview-body") as HTMLElement;
  const box = (e: Element): Box => { const r = e.getBoundingClientRect(); return { left: r.left, top: r.top, right: r.right, bottom: r.bottom }; };
  const resolve = (decl: string, prop: "backgroundColor" | "color" | "borderTopColor"): string => { const p = document.createElement("span"); p.style.cssText = decl; card.appendChild(p); const v = getComputedStyle(p)[prop]; p.remove(); return v; };
  const rows = Array.from(pop.querySelectorAll(".fileview-outline-row")) as HTMLElement[];
  const cur = pop.querySelector(".fileview-outline-row.current") as HTMLElement;
  const c = box(card), p = box(pop), cs = getComputedStyle(pop);
  return {
    count: rows.length, inCard: p.left >= c.left - 0.5 && p.right <= c.right + 0.5 && p.top >= c.top - 0.5 && p.bottom <= c.bottom + 0.5, card: c, pop: p,
    clientH: pop.clientHeight, scrollH: pop.scrollHeight, bodyH: body.clientHeight, focused: document.activeElement === pop,
    expanded: (document.querySelector(".fileview-outline-btn") as HTMLElement).getAttribute("aria-expanded"),
    bg: cs.backgroundColor, fg: cs.color, border: cs.borderTopColor, font: cs.fontSize, curBg: getComputedStyle(cur).backgroundColor,
    menuBg: resolve("background: var(--menu-bg)", "backgroundColor"), menuFg: resolve("color: var(--menu-fg)", "color"),
    menuBorder: resolve("border: 1px solid var(--menu-border)", "borderTopColor"), menuHover: resolve("background: var(--menu-hover)", "backgroundColor"),
    texts: rows.map((r) => r.textContent || ""), ids: rows.map((r) => r.dataset.id || ""), depths: rows.map((r) => r.style.getPropertyValue("--fv-ol-depth")),
  };
}
type Landing = { top: number; edge: number; margin: number; scrollTop: number; active: string; popover: boolean; viewer: boolean; expanded: string | null; open: boolean | null };
/** In the page: where heading `id` sits against the body's top edge, and the viewer's state after a pick. */
function readLanding(id: string): Landing {
  const body = document.querySelector(".fileview-body") as HTMLElement;
  const h = document.getElementById(id) as HTMLElement;
  const a = document.activeElement as HTMLElement | null;
  const d = h.closest("details");
  return { top: h.getBoundingClientRect().top, edge: body.getBoundingClientRect().top, margin: parseFloat(getComputedStyle(h).scrollMarginTop) || 0, scrollTop: body.scrollTop,
    active: a ? a.tagName + "." + String(a.className).split(/\s+/).join(".") : "none", popover: !!document.querySelector(".fileview-outline"), viewer: !!document.getElementById("romp-fileview"),
    expanded: (document.querySelector(".fileview-outline-btn") as HTMLElement).getAttribute("aria-expanded"), open: d ? d.hasAttribute("open") : null };
}
/** Click row `i` of the open popover (scrolled into the popover's view first). */
async function clickRow(page: any, i: number): Promise<void> {
  const pt = await page.evaluate((k: number) => { const pop = document.querySelector(".fileview-outline") as HTMLElement; const r = pop.querySelectorAll(".fileview-outline-row")[k] as HTMLElement; pop.scrollTop = Math.max(0, r.offsetTop - 20); const b = r.getBoundingClientRect(); return { x: b.left + Math.min(40, b.width / 2), y: b.top + b.height / 2 }; }, i);
  await page.mouse.click(pt.x, pt.y);
  await frames(page, 2);
}
const BODY = "DIV.fileview-body";
const OUTLINE_BTN = /^BUTTON\.fileview-btn\.fileview-outline-btn(\.romp-acted)?$/;   // the closed button's classes (the `on` dress leaves with the popover; the press pulse's romp-acted may still be on it)
const currentRow = (page: any): Promise<number> => page.evaluate(() => Array.from(document.querySelectorAll(".fileview-outline-row")).findIndex((r) => r.classList.contains("current")));
const assertAtTop = (l: Landing, what: string): void => {
  assert.ok(Math.abs((l.top - l.edge) - l.margin) <= 1, what + ": the heading's top sits at the body's edge less its scroll margin (" + l.margin + "px): read " + (l.top - l.edge).toFixed(1));
  assert.ok(l.scrollTop > 0, what + ": the body scrolled");
  assert.equal(l.popover, false, what + ": the popover closed on the pick");
  assert.equal(l.viewer, true, what + ": the viewer stands");
  assert.equal(l.expanded, "false", what + ": the button reads collapsed");
  assert.equal(l.active, BODY, what + ": the keyboard is back on the body (read " + l.active + ")");
};

test("in a browser, on the Files pane at 900 and 380 px: the Outline button renders after Raw; its popover opens inside the card, capped to the body's height and scrolling within itself, in the menu tokens' colours; the 40th row lands the 40th heading at the top with the keyboard on the body; the fold's row opens the fold; Escape closes the popover alone; ArrowDown twice and Enter pick the third; no front-matter row, the formula's row in KaTeX's text; Raw hides the button; the light theme recolours the popover", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const [w, h] of [[900, 700], [380, 640]] as Array<[number, number]>) {
      const what = "pane " + w + "px";
      const { page, errors } = await openViewer(browser, "pane", w, h, { docs: { [REPORT]: OUTLINE_NOTE } });
      const facts = await page.evaluate(() => {
        const acts = document.querySelector(".fileview-acts") as HTMLElement;
        const labels = (Array.from(acts.querySelectorAll(".fileview-btn")) as HTMLElement[]).filter((b) => b.getClientRects().length > 0).map((b) => b.textContent);
        const b = document.querySelector(".fileview-outline-btn") as HTMLElement | null;
        return { labels, shown: !!b && b.getClientRects().length > 0, popup: b ? b.getAttribute("aria-haspopup") : null, expanded: b ? b.getAttribute("aria-expanded") : null, title: b ? b.title : null,
          frontMatter: !!document.querySelector(".fileview-md details.md-frontmatter"), katex: !!document.querySelector(".fileview-md h3 .katex"), headings: document.querySelectorAll(".fileview-md h1, .fileview-md h2, .fileview-md h3").length };
      });
      assert.equal(facts.shown, true, what + ": the Outline button renders (before item 2 there was none): " + facts.labels.join(","));
      assert.equal(facts.labels.indexOf("Outline"), facts.labels.indexOf("Raw") + 1, what + ": right after the Rendered/Raw toggle: " + facts.labels.join(","));
      assert.equal(facts.popup, "menu"); assert.equal(facts.expanded, "false"); assert.equal(facts.title, "The file's headings");
      assert.equal(facts.headings, 42, what + ": the fixture's forty-two headings rendered");
      assert.equal(facts.frontMatter, true, what + ": the front matter rendered as the folded block");
      assert.equal(facts.katex, true, what + ": the formula heading was filled by KaTeX");
      // the popover
      await page.click(BTN);
      await frames(page, 2);
      const p: PopRead = await page.evaluate(readPopover);
      assert.equal(p.count, 42, what + ": one row per heading");
      assert.ok(p.inCard, what + ": the popover lies inside the card: " + JSON.stringify(p.pop) + " in " + JSON.stringify(p.card));
      assert.ok(p.clientH <= p.bodyH - 16 + 1, what + ": capped to the body's height less a margin (popover " + p.clientH + ", body " + p.bodyH + ")");
      assert.ok(p.scrollH > p.clientH, what + ": …and scrolls within itself (" + p.scrollH + " > " + p.clientH + ")");
      assert.equal(p.focused, true, what + ": the popover holds the keyboard");
      assert.equal(p.expanded, "true", what + ": the button reads expanded");
      assert.equal(p.bg, p.menuBg, what + ": the card colour is --menu-bg's"); assert.equal(p.fg, p.menuFg, what + ": the text is --menu-fg's");
      assert.equal(p.border, p.menuBorder, what + ": the hairline is --menu-border's"); assert.equal(p.curBg, p.menuHover, what + ": the current row wears --menu-hover");
      assert.equal(p.font, "12px", what + ": the menu's size");
      assert.deepEqual(p.ids.slice(0, 11), ["md-report", "md-summary", "md-scope", "md-method", "md-results", "md-latency", "md-throughput", "md-errors", "md-results-1", "md-using-cacheget", "md-ratio-x"], what + ": the minted ids in document order");
      assert.equal(p.ids[39], "md-detail-91", what + ": the 40th");
      assert.equal(p.texts[9], "Using cache.get", what + ": inline code reads as its text");
      assert.equal(p.texts[10], "Ratio x", what + ": the formula heading shows KaTeX's text, no TeX delimiters");
      assert.equal(p.texts[13], FOLD_HEADING, what + ": the heading inside the closed details is listed");
      assert.ok(!p.texts.some((x) => /Front matter|title:/.test(x)), what + ": no row for the front-matter block");
      assert.deepEqual(p.depths, OUTLINE_HEADINGS.map(([d]) => String(d - 1)), what + ": each row's depth under the h1");
      // the pick: the 40th heading at the top
      await clickRow(page, 39);
      assertAtTop(await page.evaluate(readLanding, "md-detail-91"), what + " (the 40th heading)");
      // the fold: the row for the heading inside the closed details opens it first
      const shut = await page.evaluate(() => (document.getElementById("md-inside-the-fold") as HTMLElement).closest("details")!.hasAttribute("open"));
      assert.equal(shut, false, what + ": the fold is shut before the pick");
      await page.click(BTN); await frames(page, 1);
      // the current row at the open is the section under the reader's eye: the 40th heading, just landed at the top (its top sits its
      // scroll margin under the edge, the gap a landing leaves, which the reading allows; the PR review's round 1: the first row before)
      assert.equal(await currentRow(page), 39, what + ": the current row at the open is the 40th heading, the section under the reader's eye (before the fix: the first row)");
      await clickRow(page, 13);
      const fold = await page.evaluate(readLanding, "md-inside-the-fold");
      assert.equal(fold.open, true, what + ": the pick opened the fold above the heading");
      assertAtTop(fold, what + " (the fold's heading)");
      // Escape: the popover's, not the viewer's
      await page.click(BTN); await frames(page, 1);
      assert.equal(await page.evaluate(() => !!document.querySelector(".fileview-outline")), true, what + ": open again");
      await page.keyboard.press("Escape");
      await frames(page, 2);
      const esc = await page.evaluate(readLanding, "md-report");
      assert.equal(esc.popover, false, what + ": Escape closed the popover"); assert.equal(esc.viewer, true, what + ": …and the viewer stands"); assert.match(esc.active, OUTLINE_BTN, what + ": …with the keyboard back on the Outline button, the menu-button pattern (the PR review's round 1; before: the body)");
      // the keyboard: ArrowDown twice, Enter: the third heading (from the note's top, where the first row is current)
      await page.evaluate(() => { (document.querySelector(".fileview-body") as HTMLElement).scrollTop = 0; }); await frames(page, 1);
      await page.click(BTN); await frames(page, 1);
      await page.keyboard.press("ArrowDown"); await page.keyboard.press("ArrowDown");
      const cur = await page.evaluate(() => Array.from(document.querySelectorAll(".fileview-outline-row")).findIndex((r) => r.classList.contains("current")));
      assert.equal(cur, 2, what + ": two ArrowDowns from the first row make the third current");
      await page.keyboard.press("Enter");
      await frames(page, 2);
      assertAtTop(await page.evaluate(readLanding, "md-scope"), what + " (Enter on the third row)");
      // Raw hides the button; Rendered brings it back
      await page.evaluate(() => { (Array.from(document.querySelectorAll(".fileview-acts button")).find((x) => x.textContent === "Raw") as HTMLElement).click(); });
      await frames(page, 2);
      assert.equal(await page.evaluate(() => (document.querySelector(".fileview-outline-btn") as HTMLElement).getClientRects().length), 0, what + ": hidden in Raw");
      await page.evaluate(() => { (Array.from(document.querySelectorAll(".fileview-acts button")).find((x) => x.textContent === "Rendered") as HTMLElement).click(); });
      await frames(page, 2);
      assert.ok(await page.evaluate(() => (document.querySelector(".fileview-outline-btn") as HTMLElement).getClientRects().length > 0), what + ": back on Rendered");
      // the light theme: the same tokens, the theme's values
      await page.evaluate(() => { document.body.classList.add("theme-light"); });
      await page.click(BTN); await frames(page, 2);
      const light: PopRead = await page.evaluate(readPopover);
      assert.equal(light.bg, light.menuBg, what + ": light: the card is --menu-bg's"); assert.equal(light.fg, light.menuFg, what + ": light: the text is --menu-fg's"); assert.equal(light.curBg, light.menuHover, what + ": light: the row wash is --menu-hover's");
      assert.notEqual(light.bg, p.bg, what + ": the theme changed the card colour (" + p.bg + " to " + light.bg + "): the popover reads the tokens, never a literal");
      assert.deepEqual(errors, [], what + ": no page errors");
      await page.close();
    }
    // the cost: a 500-heading note, the click to the popover, printed for the record (ui/CLAUDE.md, the many-items rule; the
    // brief's perf acceptance names two frames and makes a worse number a follow-up, not a blocker)
    const { page, errors } = await openViewer(browser, "pane", 900, 700, { docs: { [REPORT]: manyHeadings(500) } });
    const cost = await page.evaluate(() => { const b = document.querySelector(".fileview-outline-btn") as HTMLElement; const t0 = performance.now(); b.click(); const t1 = performance.now(); const pop = document.querySelector(".fileview-outline") as HTMLElement; return { ms: t1 - t0, rows: pop.querySelectorAll(".fileview-outline-row").length, scrolls: pop.scrollHeight > pop.clientHeight }; });
    assert.equal(cost.rows, 500, "one row per heading");
    assert.ok(cost.scrolls, "the popover scrolls within itself");
    assert.ok(cost.ms < 1000, "the 500-heading popover opened in " + cost.ms.toFixed(1) + " ms");
    console.log("outline: 500 headings, click to popover " + cost.ms.toFixed(1) + " ms");
    assert.deepEqual(errors, [], "no page errors");
    await page.close();
  });
});

test("in a browser, in the chat modal under render.ts's own key handlers: ArrowDown twice and Enter on the popover pick the third heading and the chat's arrow handler scrolls nothing (the popover takes the key first); Escape closes the popover and leaves the viewer up; the composer gets no letter", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const page = await browser.newPage({ viewport: { width: 1000, height: 700 } });
    const errors: string[] = [];
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    const base = pageHtml("chat", { [REPORT]: OUTLINE_NOTE }, MT).replace('<body class="">', () => '<body class=""><textarea id="composer-input"></textarea><div id="content" style="height:120px;overflow:auto"><div style="height:4000px"></div></div>');
    const tail = base.lastIndexOf("</body></html>");
    assert.ok(tail > 0, "the page ends with </body></html>");
    const html = base.slice(0, tail) + "<script>" + chatKeysScript() + "</script>" + base.slice(tail);
    await page.route((u: URL) => u.href.startsWith(ORIGIN), (route: any) => route.fulfill({ status: 200, contentType: "text/html", body: html }));
    await page.goto(ORIGIN + "/");
    await page.evaluate(() => { (document.activeElement as HTMLElement | null)?.blur(); });
    const before: number = await page.evaluate(() => (window as any).__paints);
    await page.evaluate(([p, sid]: [string, string]) => { (window as any).FV.openFileView(p, sid, null); }, [REPORT, SID]);
    await paintsReach(page, before + 1);
    await frames(page, 2);
    await page.click(BTN); await frames(page, 1);
    const p: PopRead = await page.evaluate(readPopover);
    assert.equal(p.count, 42, "chat modal: the popover lists the headings"); assert.ok(p.inCard, "…inside the card"); assert.equal(p.focused, true, "…and holds the keyboard");
    const content0: number = await page.evaluate(() => (document.getElementById("content") as HTMLElement).scrollTop);
    await page.keyboard.press("ArrowDown"); await page.keyboard.press("ArrowDown");
    await frames(page, 2);
    const read = await page.evaluate((c0: number) => ({ cur: Array.from(document.querySelectorAll(".fileview-outline-row")).findIndex((r) => r.classList.contains("current")), content: (document.getElementById("content") as HTMLElement).scrollTop - c0, scrolls: (window as any).__contentScrolls }), content0);
    assert.equal(read.cur, 2, "the third row is current");
    assert.equal(read.content, 0, "the chat's transcript box did not scroll: the popover took the arrows before render.ts's handler");
    assert.equal(read.scrolls, 0, "…and the handler's scroller never ran");
    await page.keyboard.press("Enter");
    await frames(page, 2);
    assertAtTop(await page.evaluate(readLanding, "md-scope"), "chat modal (Enter on the third row)");
    await page.click(BTN); await frames(page, 1);
    await page.keyboard.press("Escape");
    await frames(page, 2);
    const esc = await page.evaluate(readLanding, "md-report");
    assert.equal(esc.popover, false, "Escape closed the popover"); assert.equal(esc.viewer, true, "…and the viewer stands (the document's onKey never saw the key)"); assert.match(esc.active, OUTLINE_BTN, "the keyboard back on the Outline button (the PR review's round 1)");
    const composer = await page.evaluate(() => (document.getElementById("composer-input") as HTMLTextAreaElement).value);
    assert.equal(composer, "", "no key reached the composer");
    assert.deepEqual(errors, [], "no page errors");
    await page.close();
  });
});

// ── the review's round 1: the popover's width against the room left of the button, the closers' keyboard hand-over, an
// image-only heading's row, the button over the failure pane ─────────────────────────────────────────────────────────────
const H45 = "Slice 6: reaching a section without scrolling";                                          // 45 characters
const H60 = "A section heading of about sixty characters would carry this";                           // 60
const H90 = "When a plan or a build report names a section with, yes, a ninety character heading like this";   // 93
const wide = (i: number): string => `Paragraph ${i}: lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor incididunt ut labore.`;
/** A note whose headings are wider than the room between the card's left edge and the Outline button's right edge. */
const LONG_HEADS = ["Title", H45, H60, H90, "Short", "Last"].map((h, i) => (i === 0 ? "# " : i % 2 ? "## " : "### ") + h + "\n\n" + wide(i + 1) + "\n").join("\n") + Array.from({ length: 12 }, (_, i) => wide(i + 7) + "\n").join("\n");
/** A note with one heading whose only content is a picture. */
const IMG_NOTE = "# T\n\n" + wide(1) + "\n\n## ![Figure one](figs/a.png)\n\n" + wide(2) + "\n\n## After\n\n" + Array.from({ length: 30 }, (_, i) => wide(i + 3) + "\n").join("\n");
type RowsRead = { inCard: boolean; popLeft: number; popRight: number; popWidth: number; cardWidth: number; btnRight: number; gapUnderBtn: number; styleLeft: string; rows: Array<{ text: string; textLeftInCard: number; rowRightInCard: number; overflow: string; height: number; title: string }> };
/** In the page: the popover's box against the card's, and each row's TEXT box (a Range's rect, laid out past the row's clip)
 *  and row box from the card's left edge. */
function readRows(): RowsRead {
  const pop = document.querySelector(".fileview-outline") as HTMLElement, card = document.querySelector(".fileview") as HTMLElement, btn = document.querySelector(".fileview-outline-btn") as HTMLElement;
  const c = card.getBoundingClientRect(), p = pop.getBoundingClientRect(), b = btn.getBoundingClientRect();
  const rows = (Array.from(pop.querySelectorAll(".fileview-outline-row")) as HTMLElement[]).map((r) => {
    const rg = document.createRange(); rg.selectNodeContents(r); const t = rg.getBoundingClientRect(); const rr = r.getBoundingClientRect();
    return { text: (r.textContent || "").slice(0, 14), textLeftInCard: Math.round(t.left - c.left), rowRightInCard: Math.round(rr.right - c.left), overflow: getComputedStyle(r).textOverflow, height: Math.round(rr.height * 10) / 10, title: r.title };
  });
  return { inCard: p.left >= c.left - 0.5 && p.right <= c.right + 0.5, popLeft: Math.round(p.left - c.left), popRight: Math.round(p.right - c.left), popWidth: Math.round(p.width), cardWidth: Math.round(c.width), btnRight: Math.round(b.right - c.left), gapUnderBtn: Math.round((p.top - b.bottom) * 10) / 10, styleLeft: pop.style.left, rows };
}
const activeName = (page: any): Promise<string> => page.evaluate(() => { const a = document.activeElement as HTMLElement | null; return a ? a.tagName + "." + String(a.className).split(/\s+/).filter(Boolean).join(".") : "none"; });
/** Press PageDown and wait for the body's scrollTop to pass `from` (Chromium may animate a keyboard scroll); false when it never does. */
const pageDownMoves = (page: any, from: number): Promise<boolean> => page.keyboard.press("PageDown").then(() => page.waitForFunction((v: number) => (document.querySelector(".fileview-body") as HTMLElement).scrollTop > v, from, { timeout: 3000 }).then(() => true, () => false));
const popoverUp = (page: any): Promise<boolean> => page.evaluate(() => !!document.querySelector(".fileview-outline"));

test("in a browser (review round 1): a note with a heading wider than the room left of the button opens a popover that lies inside the card with every row's text starting inside it (before: the box began left of the card and its overflow clipped the start of every row, the short ones to blank strips), at pane 900 and 380 px and in the chat modal, while the forty-two-heading note keeps its right anchor under the button; closing the popover by a second click on the button, by a window resize or by the panel's reload hands the keyboard to the body and PageDown scrolls (before: the keyboard stayed on the button, or fell to the document's body); an image-only heading's row reads its picture's alt text at a text row's height; the fetch-failure pane hides the button", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const [mode, w, h] of [["pane", 900, 700], ["pane", 380, 640], ["chat", 1000, 700]] as Array<["pane" | "chat", number, number]>) {
      const what = mode + " " + w + "px (long headings)";
      const { page, errors } = await openViewer(browser, mode, w, h, { docs: { [REPORT]: LONG_HEADS } });
      await page.click(BTN); await frames(page, 2);
      const r: RowsRead = await page.evaluate(readRows);
      assert.equal(r.rows.length, 6, what + ": one row per heading");
      assert.ok(r.inCard, what + ": the popover lies inside the card (read left " + r.popLeft + ", right " + r.popRight + " of a card starting at 0; before the fix the box started " + "left of the card and was clipped)");
      assert.ok(r.popLeft >= 7.5, what + ": its left edge is at the card's margin or right of it: " + r.popLeft);
      for (const row of r.rows) assert.ok(row.textLeftInCard >= r.popLeft, what + ": the row \"" + row.text + "\" starts inside the popover (text left " + row.textLeftInCard + ", popover left " + r.popLeft + "; before the fix the short rows were wholly left of the card's edge)");
      assert.equal(r.rows[0].text, "Title", what + ": the first row reads the title"); assert.equal(r.rows[4].text, "Short"); assert.equal(r.rows[5].text, "Last");
      assert.ok(r.popWidth <= r.cardWidth - 16 + 1, what + ": the popover's width is capped at the card's less 16 px (" + r.popWidth + " of " + r.cardWidth + ")");
      assert.ok(r.rows[3].title.length > 80 && r.rows[3].rowRightInCard <= r.popRight + 0.5 && r.rows[3].overflow === "ellipsis", what + ": the ninety-character row's box ends inside the popover, its text clipped with an ellipsis, and it carries its whole text as its title");
      assert.deepEqual(errors, [], what + ": no page errors");
      await page.close();
    }
    // the forty-two-heading note in the chat modal: the popover is placed from its containing block, the fixed overlay the card
    // is inset in, so it hangs 4 px under the button with its right edge at the button's (before: 18 px too high, over the
    // button's lower half, and 25 px left of the anchor)
    const chat = await openViewer(browser, "chat", 1000, 700, { docs: { [REPORT]: OUTLINE_NOTE } });
    await chat.page.click(BTN); await frames(chat.page, 2);
    const inChat: RowsRead = await chat.page.evaluate(readRows);
    assert.ok(inChat.inCard, "chat modal: the usual note's popover lies inside the card");
    assert.ok(Math.abs(inChat.popRight - inChat.btnRight) <= 1, "chat modal: right-anchored under the button (popover right " + inChat.popRight + ", button right " + inChat.btnRight + "; before: 25 px left of it)");
    assert.ok(Math.abs(inChat.gapUnderBtn - 4) <= 1, "chat modal: 4 px under the button (read " + inChat.gapUnderBtn + "; before: over the button's lower half)");
    assert.deepEqual(chat.errors, [], "chat modal: no page errors");
    await chat.page.close();
    // the forty-two-heading note at pane 900: the popover keeps its right anchor under the button (the fix touches only a box that would start left of the card)
    const { page, errors } = await openViewer(browser, "pane", 900, 700, { docs: { [REPORT]: OUTLINE_NOTE } });
    await page.click(BTN); await frames(page, 2);
    const ok: RowsRead = await page.evaluate(readRows);
    assert.ok(ok.inCard && ok.popLeft > 8, "the usual note's popover lies inside the card, away from its left margin (left " + ok.popLeft + ")");
    assert.ok(Math.abs(ok.popRight - ok.btnRight) <= 1, "…right-anchored under the button (popover right " + ok.popRight + ", button right " + ok.btnRight + ")");
    assert.ok(Math.abs(ok.gapUnderBtn - 4) <= 1, "…4 px under it (read " + ok.gapUnderBtn + ")");
    assert.equal(ok.styleLeft, "", "…with no left anchor set");
    // the toggle: a second click on the button closes the popover; the keyboard goes to the body and PageDown scrolls
    await page.click(BTN); await frames(page, 2);
    assert.equal(await popoverUp(page), false, "the second click closed the popover");
    assert.equal(await activeName(page), BODY, "…and the body holds the keyboard (before: the button the click focused kept it, and PageDown scrolled nothing)");
    assert.equal(await pageDownMoves(page, 0), true, "PageDown scrolls the note after the toggle close");
    await page.evaluate(() => { (document.querySelector(".fileview-body") as HTMLElement).scrollTop = 0; });
    // the window resize closer (a zoom, a window drag): the popover held the keyboard; the body takes it
    await page.click(BTN); await frames(page, 1);
    assert.equal(await activeName(page), "DIV.fileview-outline", "the popover holds the keyboard when open");
    await page.setViewportSize({ width: 860, height: 700 }); await frames(page, 3);
    assert.equal(await popoverUp(page), false, "the window resize closed the popover");
    assert.equal(await activeName(page), BODY, "…and the body holds the keyboard (before: the document's body, and PageDown scrolled nothing)");
    assert.equal(await pageDownMoves(page, 0), true, "PageDown scrolls the note after the resize close");
    await page.evaluate(() => { (document.querySelector(".fileview-body") as HTMLElement).scrollTop = 0; });
    // the paint closer: the Comments panel's poll reloads the file under the open popover (the seam's reload, the poll's path)
    await page.click(BTN); await frames(page, 1);
    const paints: number = await page.evaluate(() => (window as any).__paints);
    await page.evaluate((m: string) => { (window as any).__mtime = m; (window as any).__seam.reload(); }, MT2);
    await paintsReach(page, paints + 1); await frames(page, 3);
    assert.equal(await popoverUp(page), false, "the reload's paint closed the popover");
    assert.equal(await activeName(page), BODY, "…and the body holds the keyboard (before: the document's body)");
    assert.equal(await pageDownMoves(page, 0), true, "PageDown scrolls the note after the reload's close");
    assert.deepEqual(errors, [], "no page errors (the usual note)");
    await page.close();
    // an image-only heading: its row reads the alt text at a text row's height (before: an 8 px padding-only strip with an empty title)
    const img = await openViewer(browser, "pane", 900, 700, { docs: { [REPORT]: IMG_NOTE } });
    await img.page.click(BTN); await frames(img.page, 2);
    const rows: RowsRead = await img.page.evaluate(readRows);
    assert.deepEqual(rows.rows.map((x) => x.text), ["T", "Figure one", "After"], "the image-only heading's row reads its picture's alt text");
    assert.equal(rows.rows[1].title, "Figure one", "…and carries it as its title");
    assert.ok(Math.abs(rows.rows[1].height - rows.rows[0].height) <= 1, "…at a text row's height (read " + rows.rows[1].height + " against " + rows.rows[0].height + "; before: 8 px)");
    await img.page.keyboard.press("Escape"); await frames(img.page, 2);
    // the failure pane: the file gone, the panel's reload paints the 404 pane, and the Outline button goes with the headings it listed;
    // a popover open at that moment goes with them too (review round 2: it stood over the pane with its stale rows and the keyboard, the
    // hidden button reading expanded), and the body takes the keyboard the popover held, as after every other paint closer
    assert.ok(await img.page.evaluate(() => (document.querySelector(".fileview-outline-btn") as HTMLElement).getClientRects().length > 0), "the button shows over the Rendered note");
    await img.page.click(BTN); await frames(img.page, 1);
    const openBefore = await img.page.evaluate(() => ({ popover: !!document.querySelector(".fileview-outline"), expanded: (document.querySelector(".fileview-outline-btn") as HTMLElement).getAttribute("aria-expanded"), active: (document.activeElement as HTMLElement).className }));
    assert.deepEqual(openBefore, { popover: true, expanded: "true", active: "fileview-outline" }, "the popover is open and holds the keyboard when the file goes");
    await img.page.evaluate((p: string) => { delete (window as any).__docs[p]; (window as any).__seam.reload(); }, REPORT);
    await img.page.waitForFunction(() => !!document.querySelector(".fileview-body > .fileview-err"), null, { timeout: 10000 });
    await frames(img.page, 2);
    assert.equal(await img.page.evaluate(() => (document.querySelector(".fileview-outline-btn") as HTMLElement).getClientRects().length), 0, "the Outline button is hidden over the failure pane (before: shown, and a click flashed it and opened nothing)");
    const overPane = await img.page.evaluate(() => ({ popover: !!document.querySelector(".fileview-outline"), rows: document.querySelectorAll(".fileview-outline-row").length, expanded: (document.querySelector(".fileview-outline-btn") as HTMLElement).getAttribute("aria-expanded"), active: (document.activeElement as HTMLElement).className }));
    assert.equal(overPane.popover, false, "the popover closed with the pane's paint (before the fix: it stood over the pane with " + overPane.rows + " stale rows)");
    assert.equal(overPane.expanded, "false", "the hidden button reads collapsed (before: expanded)");
    assert.equal(overPane.active, "fileview-body", "the body took the keyboard the popover held (the paint closer's rule)");
    assert.deepEqual(img.errors, [], "no page errors (the image heading and the failure pane)");
    await img.page.close();
  });
});

// ── the PR review's round 1: a press on a row under a landing (the click-safe rule, ui/CLAUDE.md), in the hold pattern of
// file-view-copy-held-browser.test.ts ────────────────────────────────────────────────────────────────────────────────────
test("in a browser (PR review round 1): a landing while the pointer is pressed on a row waits for the release: the popover stands, nothing paints, the release's click picks the 40th heading and lands it at the top with the keyboard on the body, and only then do the new bytes paint, the heading still at the top (before the fix: the landing's hold was on the body alone, so the panel's reload painted at once under the press, closeOutline removed the pressed row before the mouseup, and the pick was lost)", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openViewer(browser, "pane", 900, 700, { docs: { [REPORT]: OUTLINE_NOTE } });
    await page.click(BTN); await frames(page, 1);
    const pt = await page.evaluate(() => { const pop = document.querySelector(".fileview-outline") as HTMLElement; const r = pop.querySelectorAll(".fileview-outline-row")[39] as HTMLElement; pop.scrollTop = Math.max(0, r.offsetTop - 20); const b = r.getBoundingClientRect(); return { x: b.left + Math.min(40, b.width / 2), y: b.top + b.height / 2 }; });
    await page.mouse.move(pt.x, pt.y); await frames(page, 1);
    await page.mouse.down(); await frames(page, 1);
    const pressed: { paints: number; fetches: number } = await page.evaluate(() => ({ paints: (window as any).__paints, fetches: (window as any).__fetches }));
    // the panel's poll saw the file move: the reload's fetch answers in microtasks, so two frames on the landing has run or parked
    await page.evaluate((m: string) => { const w = window as any; w.__mtime = m; w.__seam.reload(); }, MT2);
    await page.waitForFunction((n: number) => (window as any).__fetches > n, pressed.fetches, { timeout: 10000 });
    await frames(page, 2);
    const under = await page.evaluate(() => ({ popover: !!document.querySelector(".fileview-outline"), rows: document.querySelectorAll(".fileview-outline-row").length, paints: (window as any).__paints, mt: (window as any).__seam.mtimeNs() }));
    assert.equal(under.popover, true, "the popover stands under the press (before the fix: the landing's paint closed it)");
    assert.equal(under.rows, 42, "with its rows");
    assert.equal(under.paints, pressed.paints, "nothing painted under the press");
    assert.equal(under.mt, MT, "the body shows the file the reader has");
    await page.mouse.up(); await frames(page, 2);
    assertAtTop(await page.evaluate(readLanding, "md-detail-91"), "the release's pick (the 40th heading)");
    await paintsReach(page, pressed.paints + 1); await frames(page, 2);
    const after = await page.evaluate(readLanding, "md-detail-91");
    assert.equal(await page.evaluate(() => (window as any).__seam.mtimeNs()), MT2, "then the landing painted the new bytes");
    assert.ok(Math.abs((after.top - after.edge) - after.margin) <= 1, "the heading the pick landed is still at the top: the reload kept the place (read " + (after.top - after.edge).toFixed(1) + ")");
    assert.equal(after.active, BODY, "and the body holds the keyboard");
    assert.equal(await page.evaluate(() => (window as any).__paints), pressed.paints + 1, "one paint for the one landing");
    assert.deepEqual(errors, [], "no page errors");
    await page.close();
  });
});

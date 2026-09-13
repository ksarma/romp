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
import { inBrowser, openViewer, pageHtml, frames, paintsReach, chatKeysScript, ORIGIN, REPORT, SID, MT } from "./real-viewer-leg";
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
      assert.equal(esc.popover, false, what + ": Escape closed the popover"); assert.equal(esc.viewer, true, what + ": …and the viewer stands"); assert.equal(esc.active, BODY, what + ": …with the keyboard on the body");
      // the keyboard: ArrowDown twice, Enter: the third heading
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
    assert.equal(esc.popover, false, "Escape closed the popover"); assert.equal(esc.viewer, true, "…and the viewer stands (the document's onKey never saw the key)"); assert.equal(esc.active, BODY);
    const composer = await page.evaluate(() => (document.getElementById("composer-input") as HTMLTextAreaElement).value);
    assert.equal(composer, "", "no key reached the composer");
    assert.deepEqual(errors, [], "no page errors");
    await page.close();
  });
});

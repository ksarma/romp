// A figure opens in detail (plans/markdown-viewer.md, "Follow-on: Link navigation", L3 and L4): the contract's case 6 over
// the REAL viewer in headless Chromium (real-viewer-leg.ts: the chat modal, file-view.ts bundled from this tree with the real
// Comments panel, styles.css, a fetch stub for the /file route and a route for the figures' own requests). Read off the DOM
// and the layout: every openable figure of a synthetic report wears an "Open the picture" control as its anchor's next
// sibling (a button of the icon family, titled, in the tab order); the pointer over the figure reveals it and lays it over
// the figure's top-right corner (a right-floated figure's at its top-left); Tab reaches it and Enter opens the picture, the
// bar naming the picture and Back titled with the report's name (L4); a click on the control from deep in the report opens
// the picture and Back returns to the paragraph at its scrollTop; a plain click on the figure opens it while the Comments
// panel is closed; a Ctrl-click on the figure or the control opens the /file URL in a tab (window.open stubbed) and moves
// nothing; a figure inside an author's link keeps the link on its plain click and still has its own control; a remote picture
// on an unlisted host is a gated placeholder with no control until its click loads it, and then opens a tab, never the viewer;
// an inline `data:` picture has no control; with the panel OPEN a plain click on the figure is the panel's comment offer
// (the float), a Ctrl-click on the figure is the offer too and opens no tab (the overlay reads no modifier), a drag on the
// overlay draws a region, and the control's click is not swallowed by the overlay; with the panel
// open on a COARSE pointer the layer's overlay is off, so the plain tap reaches the figure listener itself, which stands down
// to the comment offer (the guard's own execution: nothing opens, the trail does not move) while a Ctrl-click and the control
// keep their opens; print media shows no control even when it holds the focus; a device with no hover keeps it visible; a
// LOADED picture from the web, served by a second http server the test starts, shows where its open goes before any gesture
// (its control's words name the host and the new tab, its class and glyph are the outbound ones, and the picture's own title
// carries the address after the author's title) while the local picture beside it keeps the one control, and a <picture>
// whose candidate changes kind at a media change is re-dressed both ways with no add or remove (the file review's round 11,
// ui-1 with extra8-1); a remote picture inside an author's named anchor or a dead host:port link, bare, captioned and under
// the floor, carries the address line on the picture and, where the floor allows, its control (the captioned one's inside the
// anchor, after the picture), and its plain click opens the tab, while the picture inside a live web link keeps no line (the
// file review's round 12, correctness-1 with ui-1: the three readers of "whose click is this" read one predicate); one relayed
// address carries a written port, which the control's words keep (URL.host, so two servers on one name read apart; the file
// review's round 12, fresh-2); a remote picture under the floor (20 by 20, from the second server) wears no control, carries the
// address in its title and wears the outbound mark on the picture itself, on hover on a fine pointer in one case and, in a case
// of its own under CDP touch emulation (hover none) with no hover ever over it, at rest, where a tap opens the tab at the address,
// the popup and the second server's log read, and the mark's colour is the control's border colour under both themes (the file
// review's round 12, fresh-1 with tests-2). The outbound dress is read as PAINTED too (paintedRatio: a screenshot of the real page,
// so every opacity on the way, the element's own and every ancestor's, is in the pixels): at rest under touch emulation and on the
// touchscreen laptop, the web control alone, after a bare dead link and inside a captioned one, and the mark alone, inside a dead
// link, inside a ==highlight==, in a table header, in an even table row and in a note callout, in both themes, and in the touch case
// on the VS Code editor grounds either side of the stated bound; on a fine pointer, inside a dead link, the control revealed by the
// pointer over its picture, its accent border under the pointer and the mark on hover, and the mark on hover on those four grounds
// too; each at least 3:1 against the ground the sheet controls: for the control its own background (the colour of the gaps between
// its dashes), and for the mark the ground its ring gives it, read by the worst dash-to-ring ratio, every dash pixel on all four sides
// against the pixel one step toward the picture and one step away and the dash against every gap pixel (markWorst; the file review's
// round 14, correctness-2 with extra5-1 and extra5-2: the one ground pixel read before, in the offset above the picture, passed the
// dark highlight at 4.83:1 while its dashes painted 2.40:1 against the tint on both sides). Over a picture the control's outer side is
// the author's pixels, which no colour of the dress clears for every picture, so the read is not against them, and the touch case
// asserts that pixel is the picture's own fill. On a
// fine pointer the control under a keyboard focus inside a dead link is read by pixels too, its focus ring standing 2px off the
// border (the sheets' focus rule: drawn where the browser draws it, the ring covered the border row and the row inside it). The
// control inside the captioned dead link is read HELD PRESSED too, in each of the three cases and both themes, by pixels while the
// press is held and before its release opens the tab (pressedLegible), by a mouse press and, on the fine pointer, by the Space key
// from that keyboard focus: the release that opens the tab comes while it is held, and the sheets' press rule takes the family's
// press cue off the web control (under the cue the line spread over two pixel rows, its modal colour at 1.592:1 dark and 1.386:1
// light, red here over the sheets without that rule). The touch case reads the captioned dead link's words taking the link's dimmed
// colour and its bold words and inline code keeping their own ink, the witness of the residual the sheets' comment states. Those
// reads red at 61d69cba1, where a dead link's opacity 0.7 dimmed the dress inside it and the web control rested at 0.8 (the
// painted-contrast ask of 2026-09-23). The mark's four grounds red over the sheets before its ring of var(--bg): the dark highlight
// at 2.40:1 at rest under touch, at rest on the laptop and on hover on the fine pointer, and on the VS Code editor grounds the
// highlight, the table header, the even row and the callout at #404040, the highlight and the callout at #efefef, and the header and
// the even row at #eeeeee, where they read 3.00:1 past the bound the sheets state; the worst read reds a 2px ring too, on the dark
// highlight, whose outer side keeps the tint. The ring's neighbour pin (ringCoversNoNeighbour) reads a glyph glued to a picture under the floor before
// and after it in a paragraph, a highlight and a table cell, and two glued badges, against the same page with the ring taken off,
// at rest under touch and on hover on the fine pointer, in both themes: green over the sheets before the ring by design, with no ring
// to cover anything, and red over a bare 3px ring with no margin beside it (the file review's round 14, correctness-2). A case of its
// own on the Files pane under touch emulation records the ring's two stated bounds as they stand, the ink an italic letter glued
// before a picture paints past its box covered by the ring while no pixel inside the box changes, and the edge of the text a note
// callout wraps beside a left-floated picture in the ring's outer pixel, the dash's outer side under 3:1 there. The web
// control's focus is read in cases of their own at the file's end (the file review's round 14, ui-1 with extra9-1): no mouse press,
// a click, a press dragged off or a right or a middle press, leaves the keyboard on it, any focus it holds paints its line at 3:1 in
// both themes, and Enter or Space opens it only while it is in view, the body and a table that scrolls on its own each read, on a
// fine pointer, on the laptop and under touch, and in the feed and the Files pane, each pin red over the viewer before those fixes
// and the keep checks beside them green there by design. A picture inside a fold's summary is read in cases of their own after
// those (the file review's round 14, fresh-1): inside a details element's own first summary, a plain click and a Ctrl-click on a
// remote picture under the floor and on a local picture, a plain click on a remote picture over the floor and on one inside a
// named anchor, each toggle the fold and open nothing, the remote pictures wearing no address line and no mark, each red over the
// viewer before the summary predicate by the open beside the toggle and by the line and the mark, while the web control inside the
// summary opens once with the fold shut and the pictures of a stray summary open as anywhere else, controls green there by design. Red over
// the unchanged viewer at the first control assertion (no control exists), the outbound
// case red at the head before it, where the two controls presented one surface, and the link-shapes case red at the round-12
// head, where the title and the control read any anchor while the click did not, and the two under-the-floor cases red at that head too, the hover read and the at-rest read, where no rule dressed the picture. Skips LOUDLY without a playwright browser (in CI the Test step runs before the job's Chromium install, so the leg skips there; the launch is real-viewer-leg.ts's inBrowser, the shared helper). Synthetic values only: the notes-api world, a placeholder session id, example.invalid and example.test addresses,
// /repo/notes-api paths.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as http from "node:http";   // the outbound case's second server (the last test): a real origin of its own for the remote pictures
import * as zlib from "node:zlib";   // paintedRatio's PNG decode: the dress read off the real paint
import { inBrowser, openViewer, openPanel, frames, topBlock, putAtTop, ROOT, REPORT, SID, PARA } from "./real-viewer-leg";

const NOTES = ROOT + "/docs/notes.md";
const PLOT = ROOT + "/docs/figs/plot.svg";
const PLOT2 = ROOT + "/docs/figs/plot2.svg";
const REMOTE = "https://example.invalid/pic.svg";
const INLINE = "data:image/svg+xml;base64," + Buffer.from('<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40"><rect width="40" height="40" fill="#987"/></svg>').toString("base64");
const svg = (fill: string): string => '<svg xmlns="http://www.w3.org/2000/svg" width="300" height="200"><rect width="300" height="200" fill="' + fill + '"/></svg>';
// the report: the first plot right under the heading (the body's first focusable control is its Open control), thirty
// paragraphs, the second plot (the place test: a reader at paragraph 30 has it in view), thirty more, then the linked figure,
// the right-floated one, the remote one (example.invalid is on no host list: gated) and the inline one
const REPORT_TEXT = "# Report\n\n![the plot](figs/plot.svg)\n\n" + Array.from({ length: 30 }, (_, i) => PARA(i + 1)).join("\n\n")
  + "\n\n![the second plot](figs/plot2.svg)\n\n" + Array.from({ length: 30 }, (_, i) => PARA(i + 31)).join("\n\n")
  + "\n\n[![linked](figs/plot.svg)](notes.md)\n\n<p>Prose beside a floated figure. <img src=\"figs/plot.svg\" alt=\"floated\" align=\"right\" width=\"120\"> More prose after it.</p>\n\n"
  + "![remote](" + REMOTE + ")\n\n![inline](" + INLINE + ")\n";
const NOTES_TEXT = "# Notes\n\nA short note.\n";
const DOCS: Record<string, string> = { [REPORT]: REPORT_TEXT, [NOTES]: NOTES_TEXT, [PLOT]: svg("#456"), [PLOT2]: svg("#654") };
const FILE_URL = (p: string): string => "/file?path=" + encodeURIComponent(p) + "&sid=" + encodeURIComponent(SID);

type Ctl = { alt: string; control: boolean; title: string | null; aria: string | null; tag: string | null; type: string | null; tabIndex: number | null; svg: boolean; text: string; classes: string; before: string | null; gated: boolean };
/** Every img of the Rendered box, with the control standing after its anchor (the img, its wrap, or the link holding it). */
const controls = (page: any): Promise<Ctl[]> => page.evaluate(() => {
  const box = document.querySelector(".fileview-md")!;
  return Array.from(box.querySelectorAll("img")).map((img) => {
    let a: Element = img;
    for (let p = a.parentElement; p && (p.localName === "a" || p.classList.contains("fc-imgwrap") || p.localName === "picture"); p = a.parentElement) a = p;
    const n = a.nextElementSibling;
    const c = n && n.hasAttribute("data-fv-figopen") ? n as HTMLButtonElement : null;
    return { alt: img.getAttribute("alt") || "", control: !!c, title: c ? c.title : null, aria: c ? c.getAttribute("aria-label") : null, tag: c ? c.tagName : null, type: c ? c.type : null,
      tabIndex: c ? c.tabIndex : null, svg: !!(c && c.querySelector("svg")), text: c ? (c.textContent || "").trim() : "", classes: c ? c.className : "", before: c ? c.previousElementSibling!.localName : null, gated: !!img.closest('[data-act="fv-load"]') };
  });
});
type Box = { left: number; top: number; right: number; bottom: number; width: number; height: number };
const boxOf = (page: any, sel: string, nth = 0): Promise<Box> => page.evaluate(([sel, nth]: [string, number]) => { const r = document.querySelectorAll(sel)[nth].getBoundingClientRect(); return { left: r.left, top: r.top, right: r.right, bottom: r.bottom, width: r.width, height: r.height }; }, [sel, nth]);
const opacity = (page: any, nth = 0): Promise<string> => page.evaluate((n: number) => getComputedStyle(document.querySelectorAll(".fileview-md [data-fv-figopen]")[n]).opacity, nth);
const waitOpacity = (page: any, nth: number, v: string) => page.waitForFunction(([n, v]: [number, string]) => getComputedStyle(document.querySelectorAll(".fileview-md [data-fv-figopen]")[n]).opacity === v, [nth, v], { timeout: 5000 });
const base = (page: any): Promise<string | null> => page.locator(".fileview-base").textContent();
type Nav = { present: boolean; title?: string; aria?: string | null; disabled?: string | null };
const nav = (page: any): Promise<{ back: Nav; forward: Nav }> => page.evaluate(() => {
  const read = (dir: string): Nav => { const b = document.querySelector(".fileview-nav-" + dir) as HTMLButtonElement | null; return b ? { present: true, title: b.title, aria: b.getAttribute("aria-label"), disabled: b.getAttribute("aria-disabled") } : { present: false }; };
  return { back: read("back"), forward: read("forward") };
});
/** The named file's paint: the bar's base name, and its body (a picture's img, or the Rendered box's first paragraph). */
async function painted(page: any, name: string): Promise<void> {
  await page.locator(".fileview-base", { hasText: name }).waitFor({ timeout: 10000 });
  await page.locator(/\.svg$/.test(name) ? "img.fileview-img" : ".fileview-md > p").first().waitFor({ timeout: 10000 });
  await frames(page, 3);
}
const opened = (page: any): Promise<string[]> => page.evaluate(() => (window as any).__opened.splice(0));
const near = (a: number, b: number, tol: number, msg: string) => assert.ok(Math.abs(a - b) <= tol, msg + ": " + a + " vs " + b);
const enabledTo = (b: Nav, title: string, msg: string) => { assert.equal(b.present, true, msg + ": the button is in the bar"); assert.equal(b.disabled, null, msg + ": no aria-disabled with a target"); assert.equal(b.title, title, msg); };
const disabled = (b: Nav, msg: string) => { assert.equal(b.present, true, msg + ": the button is in the bar"); assert.equal(b.disabled, "true", msg + ": aria-disabled alone when empty"); };

/** The report open in the chat modal at 900 by 600, the figures served, window.open stubbed to a record. */
async function openReport(browser: any): Promise<{ page: any; errors: string[] }> {
  const o = await openViewer(browser, "chat", 900, 600, {
    docs: DOCS,
    serve: (u) => { const p = u.pathname === "/file" ? u.searchParams.get("path") || "" : ""; return DOCS[p] !== undefined && /\.svg$/.test(p) ? { status: 200, type: "image/svg+xml", body: DOCS[p] } : null; },
  });
  await o.page.route(REMOTE, (route: any) => route.fulfill({ status: 200, contentType: "image/svg+xml", body: svg("#333") }));
  await o.page.evaluate(() => { const w = window as any; w.__opened = []; window.open = ((u: unknown) => { w.__opened.push(String(u)); return { opener: null }; }) as unknown as typeof window.open; });
  // every local figure's load, before anything is read: the loads settle the layout the control sits on
  await o.page.waitForFunction(() => Array.from(document.querySelectorAll(".fileview-md img")).filter((i) => !i.closest('[data-act="fv-load"]') && !(i.getAttribute("src") || "").startsWith("data:")).every((i) => (i as HTMLImageElement).complete && (i as HTMLImageElement).naturalWidth > 0), null, { timeout: 10000 });
  await frames(o.page, 2);
  return o;
}

test("in a browser: every openable figure of a rendered file wears an Open the picture control after its anchor, in the icon family and the tab order; the pointer over the figure reveals it at the top-right corner (a right-floated figure's at the top-left); a gated placeholder and an inline data picture have none", async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openReport(browser);
    const c = await controls(page);
    // FAILS BEFORE: over the unchanged viewer no img has a control after it
    assert.equal(c[0].control, true, "the first plot wears the control: " + JSON.stringify(c[0]));
    assert.deepEqual(c.map((x) => [x.alt, x.control, x.gated]), [["the plot", true, false], ["the second plot", true, false], ["linked", true, false], ["floated", true, false], ["remote", false, true], ["inline", false, false]],
      "a control on each local figure, on the linked one and the floated one; none on the gated placeholder, none on the inline data picture");
    for (const x of c.filter((x) => x.control)) {
      assert.deepEqual([x.tag, x.type, x.tabIndex, x.title, x.aria, x.svg, x.text], ["BUTTON", "button", 0, "Open the picture", "Open the picture", true, ""], x.alt + ": a button, in the tab order, the words in the title and aria-label, a glyph and no text");
      assert.match(x.classes, /\bfileview-btn\b.*\bfileview-icon\b.*\bfv-figopen\b/, x.alt + ": the bar's glyph dress and the control's own class");
    }
    assert.equal(c[2].before, "a", "the linked figure's control stands after the link, not inside it");
    assert.equal(c[3].classes.includes("fv-figopen-right"), true, "the right-floated figure's control carries the float class");
    // transparent at rest, revealed by the pointer over the figure, laid over its top-right corner
    assert.equal(await opacity(page, 0), "0", "transparent at rest");
    const img = await boxOf(page, ".fileview-md img", 0);
    await page.mouse.move(img.left + img.width / 2, img.top + img.height / 2);
    await waitOpacity(page, 0, "1");
    const ctl = await boxOf(page, ".fileview-md [data-fv-figopen]", 0);
    near(ctl.width, 22, 1, "22px wide (14px glyph, 3px padding, 1px border)"); near(ctl.height, 22, 1, "22px tall");
    near(ctl.right, img.right - 6, 1, "inset 6px from the figure's right edge"); near(ctl.top, img.top + 6, 1, "inset 6px from the figure's top edge");
    // over the control itself it stays revealed; away from the figure it fades
    await page.mouse.move(ctl.left + ctl.width / 2, ctl.top + ctl.height / 2);
    await frames(page, 2);
    assert.equal(await opacity(page, 0), "1", "revealed under the pointer over itself");
    await page.mouse.move(5, 5);
    await waitOpacity(page, 0, "0");
    // the floated figure: the control floats with it, at the top-left corner (a later right float sits left of the earlier one)
    await page.evaluate(() => { document.querySelectorAll(".fileview-md img")[3].scrollIntoView({ block: "center" }); });
    await frames(page, 2);
    const fl = await boxOf(page, ".fileview-md img", 3);
    const flc = await boxOf(page, ".fileview-md [data-fv-figopen]", 3);
    near(flc.left, fl.left + 6, 1, "the right float's control is 6px in from its left edge"); near(flc.top, fl.top + 6, 1, "and 6px down from its top");
    assert.ok(fl.right <= 900 && fl.left > 450, "the figure floats at the right of the column: " + JSON.stringify(fl));
    assert.deepEqual(errors, [], "no page errors");
    await page.close();
  });
});

test("in a browser: Tab reaches the control and Enter opens the picture, the bar naming it and Back titled with the report; a control deep in the report opens its picture and Back returns to the paragraph at its scrollTop; a plain click on the figure opens it with the panel closed; Ctrl-click on the figure or the control opens the /file URL in a tab and moves nothing", async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openReport(browser);
    disabled((await nav(page)).back, "a fresh open is the trail's root");
    // the keyboard: the body holds the focus, one Tab lands on the first figure's control (the first focusable in the body), which the focus reveals
    await page.evaluate(() => { (document.querySelector(".fileview-body") as HTMLElement).focus(); });
    await page.keyboard.press("Tab");
    assert.equal(await page.evaluate(() => document.activeElement!.hasAttribute("data-fv-figopen") && document.activeElement === document.querySelectorAll(".fileview-md [data-fv-figopen]")[0]), true, "Tab from the body lands on the first control");
    await waitOpacity(page, 0, "1");
    await page.keyboard.press("Enter");
    await painted(page, "plot.svg");
    let n = await nav(page);
    enabledTo(n.back, "Back to report.md", "L4: the picture view reached from the report names the report on Back"); disabled(n.forward, "nothing ahead");
    assert.equal(await base(page), "plot.svg", "the bar shows the picture's name");
    assert.equal(await page.evaluate(() => !!document.querySelector(".fileview-imgbox img.fileview-img")), true, "the picture body (imgBlock)");
    await page.click(".fileview-nav-back");
    await painted(page, "report.md");
    enabledTo((await nav(page)).forward, "Forward to plot.svg", "the picture went ahead");
    // the place: a reader at paragraph 30 opens the second plot from its control and comes back to paragraph 30
    await putAtTop(page, "Paragraph 30");
    await frames(page, 1);
    const before = await topBlock(page);
    assert.ok(before && before.text.startsWith("Paragraph 30"), "the reader stands at paragraph 30: " + JSON.stringify(before));
    await page.locator(".fileview-md [data-fv-figopen]").nth(1).click();   // no force: Playwright's hit-target check proves the control is what receives the pointer (opacity 0 counts as visible), and the click brings the pointer over it
    await painted(page, "plot2.svg");
    enabledTo((await nav(page)).back, "Back to report.md", "the second plot: Back names the report");
    await page.click(".fileview-nav-back");
    await painted(page, "report.md");
    const after = await topBlock(page);
    assert.ok(after && after.text.startsWith("Paragraph 30"), "Back re-seats the paragraph the figure was opened from: " + JSON.stringify(after));
    near(after!.scrollTop, before!.scrollTop, 1, "at the same scrollTop");
    // a plain click on the figure itself, the panel closed: the picture opens
    await page.evaluate(() => { document.querySelectorAll(".fileview-md img")[0].scrollIntoView({ block: "center" }); });
    await frames(page, 1);
    const img = await boxOf(page, ".fileview-md img", 0);
    await page.mouse.click(img.left + img.width * 0.3, img.top + img.height * 0.6);   // away from the control's corner
    await painted(page, "plot.svg");
    enabledTo((await nav(page)).back, "Back to report.md", "the figure's own click pushed the report");
    await page.click(".fileview-nav-back");
    await painted(page, "report.md");
    await page.evaluate(() => { document.querySelectorAll(".fileview-md img")[0].scrollIntoView({ block: "center" }); });
    await frames(page, 1);
    // a modified click on the figure: the /file URL in a tab (window.open stubbed), the viewer and the trail unmoved
    const img2 = await boxOf(page, ".fileview-md img", 0);
    await page.keyboard.down("Control"); await page.mouse.click(img2.left + img2.width * 0.3, img2.top + img2.height * 0.6); await page.keyboard.up("Control");   // mouse.click takes no modifiers option: the key is held around it
    await frames(page, 2);
    assert.deepEqual(await opened(page), [FILE_URL(PLOT)], "one tab at the kernel's /file URL for the plot, with the session");
    assert.equal(await base(page), "report.md", "the viewer still shows the report");
    // …and on the control
    await page.locator(".fileview-md [data-fv-figopen]").nth(0).click({ modifiers: ["Control"] });
    await frames(page, 2);
    assert.deepEqual(await opened(page), [FILE_URL(PLOT)], "the control's modified click: the same tab");
    assert.equal(await base(page), "report.md");
    n = await nav(page);
    disabled(n.back, "a tab pushes nothing"); enabledTo(n.forward, "Forward to plot.svg", "the list ahead stands");
    assert.deepEqual(errors, [], "no page errors");
    await page.close();
  });
});

test("in a browser: a figure inside an author's link keeps the link on its plain click and still has its own control; a remote picture on an unlisted host gets its control once its placeholder is loaded and opens a tab at its own address from the control, the plain click and a Ctrl-click, never the viewer and never a /file URL; print media shows no control even when focused; a device with no hover keeps it visible", async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openReport(browser);
    // the linked figure: the author's link opens the notes; the control after the link opens the picture
    await page.evaluate(() => { document.querySelectorAll(".fileview-md img")[2].scrollIntoView({ block: "center" }); });
    await frames(page, 1);
    const li = await boxOf(page, ".fileview-md img", 2);
    await page.mouse.click(li.left + li.width * 0.3, li.top + li.height * 0.6);
    await painted(page, "notes.md");
    enabledTo((await nav(page)).back, "Back to report.md", "the author's link: a push like any link");
    await page.click(".fileview-nav-back");
    await painted(page, "report.md");
    await page.evaluate(() => { document.querySelectorAll(".fileview-md img")[2].scrollIntoView({ block: "center" }); });
    await frames(page, 1);
    await page.locator(".fileview-md [data-fv-figopen]").nth(2).click();
    await painted(page, "plot.svg");
    enabledTo((await nav(page)).back, "Back to report.md", "the linked figure's control opens the picture itself");
    await page.click(".fileview-nav-back");
    await painted(page, "report.md");
    // the gated remote figure: no control while gated; one click loads it; the control appears on the load and opens a tab
    assert.equal((await controls(page))[4].control, false, "no control on the placeholder");
    await page.evaluate(() => { document.querySelector('[data-act="fv-load"]')!.scrollIntoView({ block: "center" }); });
    await frames(page, 1);
    await page.click('[data-act="fv-load"]');
    await page.waitForFunction(() => { const imgs = document.querySelectorAll(".fileview-md img"); const i = imgs[4] as HTMLImageElement; return !i.closest('[data-act="fv-load"]') && i.complete && i.naturalWidth > 0 && !!(i.nextElementSibling && i.nextElementSibling.hasAttribute("data-fv-figopen")); }, null, { timeout: 10000 });
    await frames(page, 2);   // the picture's box replacing the placeholder's settles the layout the control sits on
    const c = await controls(page);
    assert.deepEqual([c[4].control, c[4].gated, c[4].title], [true, false, "Open the picture in a new tab at example.invalid"], "loaded: the control stands after the img, its words naming the host and the tab (the outbound case visible before the gesture; a property, read off the page)");
    await page.locator(".fileview-md [data-fv-figopen]").nth(4).click();
    await frames(page, 2);
    assert.deepEqual(await opened(page), [REMOTE], "a remote picture opens in a tab, from the control");
    assert.equal(await base(page), "report.md", "never in the viewer");
    await page.evaluate(() => { document.querySelectorAll(".fileview-md img")[4].scrollIntoView({ block: "center" }); });   // the loaded picture is taller than the placeholder was: its lower part had run below the body's edge
    await frames(page, 1);
    const ri = await boxOf(page, ".fileview-md img", 4);
    await page.mouse.click(ri.left + ri.width * 0.3, ri.top + ri.height * 0.6);
    await frames(page, 2);
    assert.deepEqual(await opened(page), [REMOTE], "and from the figure's own plain click");
    assert.equal(await base(page), "report.md");
    // a Ctrl-click on the remote figure, and on its control: the picture's OWN address in a tab, never the kernel's /file URL (the
    // file review's round 2, extra5-3: the record named the plain click and the control as the gestures that open the tab, and a
    // modified click as the /file URL's; on a remote picture every gesture is the address); the viewer and the trail unmoved
    await page.keyboard.down("Control"); await page.mouse.click(ri.left + ri.width * 0.3, ri.top + ri.height * 0.6); await page.keyboard.up("Control");   // mouse.click takes no modifiers option: the key is held around it
    await frames(page, 2);
    assert.deepEqual(await opened(page), [REMOTE], "the Ctrl-click on the remote figure: its own address, not a /file URL");
    await page.locator(".fileview-md [data-fv-figopen]").nth(4).click({ modifiers: ["Control"] });
    await frames(page, 2);
    assert.deepEqual(await opened(page), [REMOTE], "and on its control: the same address");
    assert.equal(await base(page), "report.md", "never the viewer");
    disabled((await nav(page)).back, "a tab pushes nothing");
    assert.deepEqual((await controls(page))[5].control, false, "the inline data picture still has none");
    // print: the reveal rules are screen's, so a control holding the focus prints as its rest, transparent
    await page.evaluate(() => { document.querySelectorAll(".fileview-md img")[0].scrollIntoView({ block: "center" }); (document.querySelector(".fileview-body") as HTMLElement).focus(); });
    await page.keyboard.press("Tab");
    await waitOpacity(page, 0, "1");
    await page.emulateMedia({ media: "print" });
    await frames(page, 2);
    assert.equal(await opacity(page, 0), "0", "print media: transparent though focused");
    await page.emulateMedia({ media: "screen" });
    await waitOpacity(page, 0, "1");
    await page.evaluate(() => { (document.activeElement as HTMLElement).blur(); });
    await waitOpacity(page, 0, "0");
    // no hover (a touch device): the control stays visible at rest. Chromium's `(hover: none)` follows touch emulation
    // (Emulation.setTouchEmulationEnabled flips it live; setEmulatedMedia takes no hover feature), and does not revert when
    // the emulation is turned off, so this is the case's last step.
    assert.equal(await page.evaluate(() => matchMedia("(hover: none)").matches), false, "a fine pointer before the emulation");
    const cdp = await page.context().newCDPSession(page);
    await cdp.send("Emulation.setTouchEmulationEnabled", { enabled: true, maxTouchPoints: 1 });
    assert.equal(await page.evaluate(() => matchMedia("(hover: none)").matches), true, "no hover under the emulation");
    await waitOpacity(page, 0, "0.8");
    assert.deepEqual(errors, [], "no page errors");
    await page.close();
  });
});

test("in a browser, the Comments panel open on a fine pointer: the regions layer wraps the figure and the control stands after the wrap; a plain click on the figure is the panel's comment offer, a Ctrl-click on the figure is the offer too and opens no tab, a drag on the overlay draws a region, and the control's click opens the picture with Back to the report", async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openReport(browser);
    await openPanel(page);
    await page.waitForFunction(() => !!document.querySelector(".fileview-md .fc-imgwrap > img") && !!document.querySelector(".fileview-md .fc-overlay:not(.fc-overlay-off)"), null, { timeout: 5000 });
    const c = await controls(page);
    assert.deepEqual([c[0].control, c[0].before], [true, "span"], "the control stands after the layer's wrap (span.fc-imgwrap), outside it");
    await page.evaluate(() => { document.querySelectorAll(".fileview-md img")[0].scrollIntoView({ block: "center" }); });
    await frames(page, 2);
    const img = await boxOf(page, ".fileview-md img", 0);
    // the pointer over the wrapped figure reveals the control, over the overlay
    await page.mouse.move(img.left + img.width / 2, img.top + img.height / 2);
    await waitOpacity(page, 0, "1");
    const ctl = await boxOf(page, ".fileview-md [data-fv-figopen]", 0);
    near(ctl.right, img.right - 6, 1, "over the top-right corner with the panel open"); near(ctl.top, img.top + 6, 1, "");
    assert.equal(await page.evaluate(([x, y]: [number, number]) => document.elementFromPoint(x, y)!.closest("[data-fv-figopen]") !== null, [ctl.left + ctl.width / 2, ctl.top + ctl.height / 2]), true, "the control, not the overlay, is under the pointer at its place");
    // a plain click on the figure: the overlay's press is handed on to the panel, which offers a comment (the float); the viewer stays
    await page.mouse.click(img.left + img.width * 0.3, img.top + img.height * 0.6);
    await page.waitForFunction(() => { const f = document.querySelector(".fc-float") as HTMLElement | null; return !!f && !f.hidden && f.getBoundingClientRect().width > 0; }, null, { timeout: 5000 });
    assert.equal(await base(page), "report.md", "the plain click offered a comment and opened nothing");
    // a Ctrl-click on the picture, on this fine pointer under the open panel: the overlay takes the press whatever the modifier
    // (file-comments-regions.ts reads none), so no tab opens and the offer stands; the /file tab is the closed panel's and the
    // coarse pointer's (the leg below), and the guide's clause says so (the file review's round 8, fresh-1)
    await page.keyboard.down("Control"); await page.mouse.click(img.left + img.width * 0.3, img.top + img.height * 0.6); await page.keyboard.up("Control");   // mouse.click takes no modifiers option: the key is held around it
    await frames(page, 2);
    assert.deepEqual(await opened(page), [], "the Ctrl-click on the picture under the open panel on a fine pointer opens no tab");
    assert.equal(await base(page), "report.md", "and opens nothing in the viewer");
    assert.equal(await page.evaluate(() => { const f = document.querySelector(".fc-float") as HTMLElement | null; return !!f && !f.hidden && f.getBoundingClientRect().width > 0; }), true, "the panel's offer stands after it");
    // a drag on the overlay draws a region: the pending rectangle stands on the overlay
    await page.mouse.move(img.left + img.width * 0.2, img.top + img.height * 0.3);
    await page.mouse.down();
    await page.mouse.move(img.left + img.width * 0.5, img.top + img.height * 0.7, { steps: 4 });
    await page.mouse.up();
    await page.waitForFunction(() => !!document.querySelector(".fileview-md .fc-overlay .fc-region-pending"), null, { timeout: 5000 });
    assert.equal(await base(page), "report.md", "the drag drew a region and opened nothing");
    // the control's click is its own: not swallowed by the overlay
    await page.mouse.move(img.left + img.width / 2, img.top + img.height / 2);
    await waitOpacity(page, 0, "1");
    const ctl2 = await boxOf(page, ".fileview-md [data-fv-figopen]", 0);
    await page.mouse.click(ctl2.left + ctl2.width / 2, ctl2.top + ctl2.height / 2);
    await painted(page, "plot.svg");
    enabledTo((await nav(page)).back, "Back to report.md", "the control opened the picture from under the open panel");
    assert.deepEqual(errors, [], "no page errors");
    await page.close();
  });
});

test("in a browser, the Comments panel open on a coarse pointer: the layer's overlay is off, so a plain tap on the figure reaches the figure listener itself, which stands down to the panel's comment offer (the float; nothing opens, the trail does not move); a Ctrl-click on the figure is still the /file URL in a tab with no offer, and the control still opens the picture", async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openReport(browser);
    // The finger BEFORE the panel: the layer reads the pointer as it arms (file-comments.ts, `active = this.open && !isCoarsePointer()`),
    // and Chromium's `(pointer: coarse)` follows touch emulation, which does not revert (the leg above), so this is a page of its own.
    const cdp = await page.context().newCDPSession(page);
    await cdp.send("Emulation.setTouchEmulationEnabled", { enabled: true, maxTouchPoints: 1 });
    assert.equal(await page.evaluate(() => matchMedia("(pointer: coarse)").matches), true, "a coarse pointer under the emulation");
    await openPanel(page);
    // the wrap stands and EVERY overlay is off (pointer-events none): the tap's target is the img, not the overlay the fine-pointer leg clicks
    await page.waitForFunction(() => { const o = document.querySelectorAll(".fileview-md .fc-overlay"); return !!document.querySelector(".fileview-md .fc-imgwrap > img") && o.length > 0 && Array.from(o).every((x) => x.classList.contains("fc-overlay-off")); }, null, { timeout: 5000 });
    await page.evaluate(() => { document.querySelectorAll(".fileview-md img")[0].scrollIntoView({ block: "center" }); });
    await frames(page, 2);
    const img = await boxOf(page, ".fileview-md img", 0);
    const at: [number, number] = [img.left + img.width * 0.3, img.top + img.height * 0.6];   // away from the control's corner
    assert.equal(await page.evaluate(([x, y]: [number, number]) => { const e = document.elementFromPoint(x, y)!; return e.localName + (e.closest(".fc-imgwrap") ? " in the wrap" : ""); }, at), "img in the wrap", "the figure itself is under the point: an off overlay takes no pointer events");
    const floatShown = (): Promise<boolean> => page.evaluate(() => { const f = document.querySelector(".fc-float") as HTMLElement | null; return !!f && !f.hidden && f.getBoundingClientRect().width > 0; });
    // a Ctrl-click on the figure: the guard reads the gesture, so the listener runs the tab and stops before the row (no comment offer)
    await page.keyboard.down("Control"); await page.mouse.click(at[0], at[1]); await page.keyboard.up("Control");   // mouse.click takes no modifiers option: the key is held around it
    await frames(page, 2);
    assert.deepEqual(await opened(page), [FILE_URL(PLOT)], "the modified click on a coarse pointer under the open panel: the /file URL in a tab");
    assert.equal(await base(page), "report.md", "the viewer still shows the report");
    assert.equal(await floatShown(), false, "the modified click stopped before the row: no comment offer");
    // FAILS with the guard dead (asideOpen read as false): the plain tap reaches the listener, which opens the picture.
    // With the guard, it stands down, and the panel's row listener offers the comment: the float stands, the report stays, the trail is unmoved.
    await page.mouse.click(at[0], at[1]);
    // the tap's outcome, whichever it is (the offer's float, or the picture's paint replacing the bar's name), then the verdict
    await page.waitForFunction(() => { const f = document.querySelector(".fc-float") as HTMLElement | null; const b = document.querySelector(".fileview-base"); return (!!f && !f.hidden && f.getBoundingClientRect().width > 0) || (b !== null && b.textContent !== "report.md"); }, null, { timeout: 5000 });
    await frames(page, 2);
    assert.equal(await base(page), "report.md", "the figure listener stood down: the tap offered a comment and opened nothing");
    assert.equal(await floatShown(), true, "the panel's comment offer stands");
    assert.equal(await page.evaluate(() => !!document.querySelector(".fileview-imgbox")), false, "no picture body");
    const n = await nav(page);
    disabled(n.back, "the tap pushed nothing"); disabled(n.forward, "nothing ahead");
    // the control keeps its open under the open panel on a coarse pointer (no hover: it stands visible at rest)
    const ctl = await boxOf(page, ".fileview-md [data-fv-figopen]", 0);
    assert.equal(await page.evaluate(([x, y]: [number, number]) => document.elementFromPoint(x, y)!.closest("[data-fv-figopen]") !== null, [ctl.left + ctl.width / 2, ctl.top + ctl.height / 2]), true, "the control is under its own point");
    await page.mouse.click(ctl.left + ctl.width / 2, ctl.top + ctl.height / 2);
    await painted(page, "plot.svg");
    enabledTo((await nav(page)).back, "Back to report.md", "the control opened the picture from under the open panel on a coarse pointer");
    assert.deepEqual(errors, [], "no page errors");
    await page.close();
  });
});

// ── the reader's place on a top-level figure wearing the control, in the real layout ──────────────────────────────────
const PLOT_TOP = ROOT + "/docs/figs/plot-top.svg";
const TOP_FIG = '<img src="figs/plot-top.svg" alt="fig" width="500" height="400">';
/** A report whose figure is a top-level html block (a bare `<img>` line, not a markdown image inside a paragraph): the control
 *  file-view.ts places after it is then a top-level element of the Rendered box, the shape the structural read had counted as
 *  a block's box. Thirty paragraphs after it, so the reader can stand partway into the figure with prose below. */
const TOP_TEXT = "# Report\n\n" + PARA(1) + "\n\n" + TOP_FIG + "\n\n" + Array.from({ length: 30 }, (_, i) => PARA(i + 2)).join("\n\n") + "\n";
const TOP_DOCS: Record<string, string> = { [REPORT]: TOP_TEXT, [PLOT_TOP]: '<svg xmlns="http://www.w3.org/2000/svg" width="500" height="400"><rect width="500" height="400" fill="#456"/></svg>' };
/** The bar's view button by its label (Raw, Rendered). */
const viewBtn = async (page: any, label: string): Promise<void> => { await page.locator("#romp-fileview .fileview-btn", { hasText: new RegExp("^" + label + "$") }).click(); await frames(page, 3); };
/** The Raw view's row at the body's top edge: the first line row whose bottom is below the edge. */
const rowAtTop = (page: any): Promise<{ text: string; top: number } | null> => page.evaluate(() => {
  const body = document.querySelector(".fileview-body")!; const br = body.getBoundingClientRect();
  for (const r of Array.from(body.querySelectorAll("code.hljs .fv-cl"))) { const rr = r.getBoundingClientRect(); if (rr.bottom > br.top + 0.5) return { text: (r.textContent || "").trim().slice(0, 48), top: Math.round((rr.top - br.top) * 10) / 10 }; }
  return null;
});
/** The Rendered box's top-level element at the body's top edge: the first child whose bottom is below the edge, with its box. */
const blockAtTop = (page: any): Promise<{ tag: string; top: number; bottom: number } | null> => page.evaluate(() => {
  const body = document.querySelector(".fileview-body")!; const br = body.getBoundingClientRect();
  for (const e of Array.from(document.querySelectorAll(".fileview-md > *"))) { const r = e.getBoundingClientRect(); if (r.bottom > br.top + 0.5) return { tag: e.tagName, top: Math.round((r.top - br.top) * 10) / 10, bottom: Math.round((r.bottom - br.top) * 10) / 10 }; }
  return null;
});

test("in a browser: a top-level html-block figure wearing the production control (the control a top-level element of the Rendered box, the img's next sibling, 22px tall at the figure's top), the reader 300px into the figure: the Raw switch lands on the img's own row and Rendered puts the figure back at the edge (the structural read passes the control over; before the file review's round 8, correctness-1, the control's box ended above the edge, the level's search took it for a block and read the paragraph after the figure, and the switch landed there; the node scene's control box in file-view-place-blocks.test.ts is a fixture, this is the layout it stands in for)", async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openViewer(browser, "chat", 900, 600, {
      docs: TOP_DOCS,
      serve: (u) => { const p = u.pathname === "/file" ? u.searchParams.get("path") || "" : ""; return p === PLOT_TOP ? { status: 200, type: "image/svg+xml", body: TOP_DOCS[PLOT_TOP] } : null; },
    });
    await page.waitForFunction(() => !!document.querySelector(".fileview-md > button.fv-figopen"), null, { timeout: 10000 });
    await frames(page, 2);
    const shape = await page.evaluate(() => {
      const body = document.querySelector(".fileview-body") as HTMLElement; const br = body.getBoundingClientRect();
      const img = document.querySelector(".fileview-md > img") as HTMLElement; const ctrl = document.querySelector(".fileview-md > button.fv-figopen") as HTMLElement;
      body.scrollTop += img.getBoundingClientRect().top - br.top + 300;   // the reader 300px into the figure
      const rel = (e: Element) => { const q = e.getBoundingClientRect(); return { top: Math.round((q.top - br.top) * 10) / 10, bottom: Math.round((q.bottom - br.top) * 10) / 10 }; };
      return { img: rel(img), ctrl: rel(ctrl), next: ctrl.previousElementSibling === img && ctrl.parentElement === img.parentElement, text: ctrl.textContent };
    });
    assert.equal(shape.next, true, "the control is the img's next sibling in the img's own parent, a top-level element of the box");
    assert.equal(shape.text, "", "a glyph with no text of its own");
    near(shape.ctrl.top, shape.img.top + 6, 1, "the control's top is 6px below the figure's"); near(shape.ctrl.bottom, shape.img.top + 28, 1, "and its bottom 28px below the figure's top: 22px tall, the box the node scene's fixture gives it");
    assert.ok(shape.ctrl.bottom < 0 && shape.img.bottom > 0, "the control's box ends above the edge while the figure's ends below it: " + JSON.stringify(shape));
    await viewBtn(page, "Raw");
    const row = await rowAtTop(page);
    assert.ok(row && row.text.startsWith('<img src="figs/plot-top.svg"'), "the Raw switch lands on the img's own row (the place read was the figure, not the paragraph after it): " + JSON.stringify(row));
    await viewBtn(page, "Rendered");
    const back = await blockAtTop(page);
    assert.equal(back && back.tag, "IMG", "Rendered puts the figure back at the edge: " + JSON.stringify(back));
    assert.deepEqual(errors, [], "no page errors");
    await page.close();
  });
});

// ── the outbound case is visible before it happens: a picture from the web wears its own words, class and glyph ─────────
// (the file review's round 11, ui-1 with extra8-1: the owner's decision of 2026-09-22 kept every gesture that opens a web
// picture's address in a tab and asked that the case be visible before the click; at the head before this, a loaded remote
// picture and a local one presented a byte-identical surface). A second local http server on another port stands for the
// remote origin: the page sees it as http://example.test through a context route that relays the bytes (a loopback
// subresource from the page's routed non-loopback origin is refused by Chromium's private network access), so the figure's
// origin differs from the page's and the bytes come from a real second server the test starts itself.
const WEB = "http://example.test";
const WEB_HOST = "example.test";
const WEB_PORT = "http://example.test:8443";                          // the same name with a written port, relayed to the second server too: the control's words keep the port (URL.host), so two servers on one name read apart (the file review's round 12, fresh-2)
const WEB_PORT_HOST = "example.test:8443";
const WEB_WORDS = "Open the picture in a new tab at " + WEB_HOST;      // the control's title and aria-label for a picture from the web (file-view.ts figureOpenWebTitle)
const WEB_LINE = (href: string): string => "Opens in a new tab: " + href;   // the picture's own title line for the two click roads (file-view.ts figureWebTitleLine)
const AUTHOR_TITLE = "Figure 2: an author's title";
const PLOT3 = ROOT + "/docs/figs/plot3.svg";
// a local figure; a remote one with an author's title; a remote one with none; a <picture> whose wide candidate is remote and
// whose narrow one (the img's src) is local, so a viewport change re-selects the kind with no add or remove of the control; a
// remote one at the same name with a written port
const WEB_TEXT = "# Report\n\n![local](figs/plot.svg)\n\n" + PARA(1) + "\n\n"
  + '<img src="' + WEB + '/pic.svg" alt="remote" title="' + AUTHOR_TITLE + '">\n\n' + PARA(2) + "\n\n"
  + "![bare](" + WEB + "/bare.svg)\n\n" + PARA(3) + "\n\n"
  + '<picture><source media="(min-width: 800px)" srcset="' + WEB + '/wide.svg"><img src="figs/plot3.svg" alt="adaptive" title="Figure 4"></picture>\n\n' + PARA(4) + "\n\n"
  + "![ported](" + WEB_PORT + "/port.svg)\n\n" + PARA(5) + "\n";
const WEB_DOCS: Record<string, string> = { [REPORT]: WEB_TEXT, [PLOT]: svg("#456"), [PLOT3]: svg("#465") };
const sized = (w: number, h: number, fill: string): string => '<svg xmlns="http://www.w3.org/2000/svg" width="' + w + '" height="' + h + '"><rect width="' + w + '" height="' + h + '" fill="' + fill + '"/></svg>';
/** The second server: a real http server on another loopback port, serving every remote picture (300 by 200, or the size `sizes`
 *  gives the path) and logging each request. */
function secondServer(log: string[], sizes: Record<string, [number, number]> = {}): Promise<{ port: number; close: () => Promise<void> }> {
  return new Promise((resolve) => {
    const s = http.createServer((req, res) => { log.push((req.method || "") + " " + (req.url || "")); const [w, h] = sizes[req.url || ""] || [300, 200]; res.writeHead(200, { "Content-Type": "image/svg+xml" }); res.end(sized(w, h, "#333")); });
    s.listen(0, "127.0.0.1", () => { const a = s.address() as { port: number }; resolve({ port: a.port, close: () => new Promise((r) => s.close(() => r())) }); });
  });
}
const fromSecond = (port: number, p: string): Promise<{ status: number; type: string; body: string }> => new Promise((resolve, reject) => {
  http.get({ host: "127.0.0.1", port, path: p }, (res) => { let b = ""; res.on("data", (c) => { b += c; }); res.on("end", () => resolve({ status: res.statusCode || 0, type: String(res.headers["content-type"] || ""), body: b })); }).on("error", reject);
});
type Dress = { alt: string; shown: string; imgTitle: string | null; imgCursor: string; title: string | null; aria: string | null; web: boolean; glyph: string | null; borderStyle: string | null };
/** Every img of the Rendered box with the dress the reader sees before any gesture: the picture's title and cursor, and its control's
 *  words, web class, glyph markup and border style. */
const dress = (page: any): Promise<Dress[]> => page.evaluate(() => {
  const box = document.querySelector(".fileview-md")!;
  return Array.from(box.querySelectorAll("img")).map((img) => {
    let a: Element = img;
    for (let p = a.parentElement; p && (p.localName === "a" || p.classList.contains("fc-imgwrap") || p.localName === "picture"); p = a.parentElement) a = p;
    const n = a.nextElementSibling;
    const c = n && n.hasAttribute("data-fv-figopen") ? n as HTMLElement : null;
    const g = c ? c.querySelector("svg") : null;
    return { alt: img.getAttribute("alt") || "", shown: (img as HTMLImageElement).currentSrc, imgTitle: img.getAttribute("title"), imgCursor: getComputedStyle(img).cursor, title: c ? c.title : null, aria: c ? c.getAttribute("aria-label") : null,
      web: !!c && c.classList.contains("fv-figopen-web"), glyph: g ? g.innerHTML : null, borderStyle: c ? getComputedStyle(c).borderStyle : null };
  });
});

test("in a browser: a LOADED picture from the web beside a local one shows where its open goes before any gesture: its control's title and aria-label name the host and a new tab, it carries the fv-figopen-web class with the sheets' own dress and the outbound glyph, and the picture's own title carries the address on its own line after an author's title (a picture with no title gets the line alone); the local picture keeps the one control and no title; a <picture> whose candidate changes kind at a media change is re-dressed both ways with no add or remove; a property pin: every value is read off the page, and file-figure-open.test.ts holds the spellings", { timeout: 240000 }, async (t) => {
  const served: string[] = [];
  const second = await secondServer(served);
  try {
    await inBrowser(t, async (browser) => {
      const before = async (pg: any): Promise<void> => {
        await pg.context().route((u: URL) => u.href.startsWith(WEB + "/") || u.href.startsWith(WEB_PORT + "/"), async (route: any) => {
          const a = await fromSecond(second.port, new URL(route.request().url()).pathname);
          return route.fulfill({ status: a.status, contentType: a.type, body: a.body });
        });
      };
      const { page, errors } = await openViewer(browser, "chat", 900, 600, {
        docs: WEB_DOCS, before,
        serve: (u) => { const p = u.pathname === "/file" ? u.searchParams.get("path") || "" : ""; return WEB_DOCS[p] !== undefined && /\.svg$/.test(p) ? { status: 200, type: "image/svg+xml", body: WEB_DOCS[p] } : null; },
      });
      await page.waitForFunction(() => { const i = document.querySelectorAll(".fileview-md img")[0] as HTMLImageElement; return i.complete && i.naturalWidth > 0; }, null, { timeout: 10000 });
      // the host is on no list: one click on the first placeholder loads every figure of the host, the <picture>'s wide candidate among them
      await page.click('[data-act="fv-load"]');
      await page.waitForFunction(() => Array.from(document.querySelectorAll(".fileview-md img")).every((i) => !i.closest('[data-act="fv-load"]') && (i as HTMLImageElement).complete && (i as HTMLImageElement).naturalWidth > 0 && (() => { let a: Element = i; for (let p = a.parentElement; p && (p.localName === "picture"); p = a.parentElement) a = p; return !!(a.nextElementSibling && a.nextElementSibling.hasAttribute("data-fv-figopen")); })()), null, { timeout: 10000 });
      await frames(page, 2);
      const d = await dress(page);
      assert.deepEqual(d.map((x) => x.alt), ["local", "remote", "bare", "adaptive", "ported"], "the five figures, each loaded with a control");
      assert.ok(served.some((s) => s.endsWith("/pic.svg")) && served.some((s) => s.endsWith("/wide.svg")) && served.some((s) => s.endsWith("/port.svg")), "the second server served the remote pictures, the ported address's among them: " + JSON.stringify(served));
      assert.ok(d[3].shown.startsWith(WEB + "/"), "at 900 px the <picture> shows its wide, remote candidate: " + d[3].shown);
      // FAILS BEFORE: the remote control wears the local words, Open the picture, no web class and the same glyph
      assert.deepEqual([d[1].title, d[1].aria, d[1].web], [WEB_WORDS, WEB_WORDS, true], "the remote picture's control names the host and the tab, and carries the web class");
      assert.deepEqual([d[0].title, d[0].aria, d[0].web], ["Open the picture", "Open the picture", false], "the local picture's control keeps the one word set and no web class");
      assert.deepEqual([d[2].title, d[2].web, d[3].title, d[3].web], [WEB_WORDS, true, WEB_WORDS, true], "the bare remote picture and the <picture> on its remote candidate wear the web words and class too");
      // the written port is part of the words (URL.host, never hostname: two servers on one name read apart) and of the title's address
      assert.deepEqual([d[4].title, d[4].aria, d[4].web, d[4].imgTitle], ["Open the picture in a new tab at " + WEB_PORT_HOST, "Open the picture in a new tab at " + WEB_PORT_HOST, true, WEB_LINE(WEB_PORT + "/port.svg")], "the ported address: the control's words name the host WITH its port and the picture's title carries the address with it (the file review's round 12, fresh-2: red under a .hostname read, which every fixture without a port left green; a property pin over the control's title property)");
      assert.ok(d[1].glyph && d[0].glyph && d[1].glyph !== d[0].glyph, "the outbound glyph differs from the local control's corner arrows");
      assert.match(d[1].glyph!, /<path /, "the outbound glyph draws a box"); assert.match(d[1].glyph!, /<line /, "with an arrow leaving it");
      assert.equal(d[2].glyph, d[1].glyph, "one outbound drawing for every web control"); assert.equal(d[3].glyph, d[1].glyph);
      assert.notEqual(d[1].borderStyle, d[0].borderStyle, "the sheets dress the web control apart from the local one: " + d[1].borderStyle + " vs " + d[0].borderStyle);
      // the picture itself: the address on its own line after the author's title; the line alone with no author's title; the local one untouched
      assert.equal(d[1].imgTitle, AUTHOR_TITLE + "\n" + WEB_LINE(WEB + "/pic.svg"), "the author's title kept, the address on its own line after it");
      assert.equal(d[2].imgTitle, WEB_LINE(WEB + "/bare.svg"), "no author's title: the line alone");
      assert.equal(d[3].imgTitle, "Figure 4\n" + WEB_LINE(WEB + "/wide.svg"), "the <picture>'s img names the candidate shown, the remote one");
      assert.equal(d[0].imgTitle, null, "the local picture carries no title of the viewer's");
      assert.equal(d[1].imgCursor, d[0].imgCursor, "the cursor is unchanged");
      // the media change: at 600 px the <picture> falls to its img src, a local file; the standing control is re-dressed with no add or remove
      const controlId = await page.evaluate(() => { const c = document.querySelectorAll(".fileview-md [data-fv-figopen]")[3] as HTMLElement; c.dataset.probeId = "standing"; return c.dataset.probeId; });
      assert.equal(controlId, "standing");
      await page.setViewportSize({ width: 600, height: 600 });
      await page.waitForFunction(() => { const i = document.querySelectorAll(".fileview-md img")[3] as HTMLImageElement; return i.complete && i.naturalWidth > 0 && /plot3\.svg/.test(decodeURIComponent(i.currentSrc)); }, null, { timeout: 10000 });
      await frames(page, 3);
      const n = await dress(page);
      assert.equal(await page.evaluate(() => (document.querySelectorAll(".fileview-md [data-fv-figopen]")[3] as HTMLElement).dataset.probeId), "standing", "the same control stands: re-dressed, not replaced");
      assert.deepEqual([n[3].title, n[3].aria, n[3].web, n[3].imgTitle], ["Open the picture", "Open the picture", false, "Figure 4"], "on the local candidate the control wears the local words and no web class, and the picture's title is the author's alone again");
      assert.equal(n[3].glyph, n[0].glyph, "and the local glyph");
      // and back to 900 px: the remote candidate again, the web dress again on the same control
      await page.setViewportSize({ width: 900, height: 600 });
      await page.waitForFunction((web: string) => { const i = document.querySelectorAll(".fileview-md img")[3] as HTMLImageElement; return i.complete && i.naturalWidth > 0 && i.currentSrc.startsWith(web + "/"); }, WEB, { timeout: 10000 });
      await frames(page, 3);
      const w = await dress(page);
      assert.equal(await page.evaluate(() => (document.querySelectorAll(".fileview-md [data-fv-figopen]")[3] as HTMLElement).dataset.probeId), "standing", "still the same control");
      assert.deepEqual([w[3].title, w[3].web, w[3].imgTitle, w[3].glyph === w[1].glyph], [WEB_WORDS, true, "Figure 4\n" + WEB_LINE(WEB + "/wide.svg"), true], "the web dress again");
      assert.deepEqual(errors, [], "no page errors");
      await page.close();
    });
  } finally { await second.close(); }
});

// The link shapes whose click is the figure's own while an anchor stands above the picture (the file review's round 12,
// correctness-1 with ui-1): a remote picture inside an author's named anchor (`<a name>`, no href, never dressed) and inside a
// dead host:port link (`[..](localhost:8080)`: the href removed, fv-dead), each bare and with a caption beside it, and one under
// the floor (100 by 20) inside a named anchor; a picture inside a live web link beside them, the shape the click yields on.
const LINK_TEXT = "# Report\n\n" + '<a name="fig-named"><img src="' + WEB + '/named.svg" alt="named"></a>\n\n' + PARA(1) + "\n\n"
  + '<a name="fig-namedcap"><img src="' + WEB + '/namedcap.svg" alt="namedcap"> Figure 1: a caption beside the picture</a>\n\n' + PARA(2) + "\n\n"
  + "[![dead](" + WEB + "/dead.svg)](localhost:8080)\n\n" + PARA(3) + "\n\n"
  + "[![deadcap](" + WEB + "/deadcap.svg) a caption beside the dead link](localhost:8080)\n\n" + PARA(4) + "\n\n"
  + '<a name="fig-floor"><img src="' + WEB + '/floor.svg" alt="floor"></a>\n\n' + PARA(5) + "\n\n"
  + "[![livelink](" + WEB + "/livelink.svg)](" + WEB + "/page.html)\n\n" + PARA(6) + "\n";
const LINK_DOCS: Record<string, string> = { [REPORT]: LINK_TEXT };
const LINK_ALTS = ["named", "namedcap", "dead", "deadcap", "floor", "livelink"];
type LinkDress = { alt: string; control: boolean; web: boolean; controlAfterImg: boolean; controlInAnchor: boolean; imgTitle: string | null; tooltip: string | null; anchorHref: string | null; anchorDead: boolean; w: number; h: number };
/** Every img of the Rendered box with what the reader sees before any gesture over these shapes: the control (after the img's
 *  anchor by the controls helper's climb, or right after the img inside the anchor), the picture's title, the tooltip the
 *  browser would show (the nearest element with a title), and the anchor's href and dead class. */
const linkDress = (page: any): Promise<LinkDress[]> => page.evaluate(() => {
  const box = document.querySelector(".fileview-md")!;
  return Array.from(box.querySelectorAll("img")).map((img) => {
    let a: Element = img;
    for (let p = a.parentElement; p && (p.localName === "a" || p.classList.contains("fc-imgwrap") || p.localName === "picture") && (p.localName !== "a" || (p.textContent || "").trim() === ""); p = a.parentElement) a = p;
    const n = a.nextElementSibling;
    const c = n && n.hasAttribute("data-fv-figopen") ? n as HTMLElement : null;
    const anchor = img.closest("a");
    const titled = img.closest("[title]");
    const r = img.getBoundingClientRect();
    return { alt: img.getAttribute("alt") || "", control: !!c, web: !!c && c.classList.contains("fv-figopen-web"), controlAfterImg: !!(img.nextElementSibling && img.nextElementSibling.hasAttribute("data-fv-figopen")),
      controlInAnchor: !!(c && c.closest("a")), imgTitle: img.getAttribute("title"), tooltip: titled ? titled.getAttribute("title") : null,
      anchorHref: anchor ? anchor.getAttribute("href") : null, anchorDead: !!anchor && anchor.classList.contains("fv-dead"), w: r.width, h: r.height };
  });
});
/** A click on the named picture at (0.3w, 0.6h), with Control held around it when `ctrl`, after scrolling it into view; what window.open recorded. */
async function clickPicture(page: any, alt: string, ctrl = false): Promise<string[]> {
  const b = await page.evaluate((alt: string) => { const i = Array.from(document.querySelectorAll(".fileview-md img")).find((x) => x.getAttribute("alt") === alt)!; i.scrollIntoView({ block: "center" }); const q = i.getBoundingClientRect(); return { x: q.left + q.width * 0.3, y: q.top + q.height * 0.6 }; }, alt);
  await frames(page, 2);
  if (ctrl) await page.keyboard.down("Control");   // mouse.click takes no modifiers option: the key is held around it (the file review's round 13, extra6-2: passed as an option it was dropped, and the click was plain)
  await page.mouse.click(b.x, b.y);
  if (ctrl) await page.keyboard.up("Control");
  await frames(page, 2);
  return opened(page);
}

test("in a browser: a LOADED remote picture inside an author's named anchor or a dead host:port link, bare or captioned, carries the address line as its own title and tooltip and, where the floor allows, its control (the captioned one's inside the anchor, right after the picture), and its plain click and Ctrl-click open the tab at its address with the viewer unmoved; one under the floor carries the line and no control and opens on the click; the picture inside a live web link keeps no line (the file review's round 12, correctness-1 with ui-1: one predicate for the click, the title and the control)", { timeout: 240000 }, async (t) => {
  const served: string[] = [];
  const second = await secondServer(served, { "/floor.svg": [100, 20] });
  try {
    await inBrowser(t, async (browser) => {
      const before = async (pg: any): Promise<void> => {
        await pg.context().route((u: URL) => u.href.startsWith(WEB + "/"), async (route: any) => {
          const a = await fromSecond(second.port, new URL(route.request().url()).pathname);
          return route.fulfill({ status: a.status, contentType: a.type, body: a.body });
        });
      };
      const { page, errors } = await openViewer(browser, "chat", 900, 600, { docs: LINK_DOCS, before });
      await page.evaluate(() => { const w = window as any; w.__opened = []; window.open = ((u: unknown) => { w.__opened.push(String(u)); return { opener: null }; }) as unknown as typeof window.open; });
      // the host is on no list: one click on the first placeholder loads every figure of the host
      await page.click('[data-act="fv-load"]');
      await page.waitForFunction(() => Array.from(document.querySelectorAll(".fileview-md img")).every((i) => !i.closest('[data-act="fv-load"]') && (i as HTMLImageElement).complete && (i as HTMLImageElement).naturalWidth > 0), null, { timeout: 10000 });
      await frames(page, 3);
      const d = await linkDress(page);
      assert.deepEqual(d.map((x) => x.alt), LINK_ALTS, "the six figures, loaded");
      // the shapes are what they claim: no href on the five (the named anchors never had one, the host:port links lost theirs and are dressed dead), the floor picture 100 by 20, the live link's href kept
      assert.deepEqual(d.slice(0, 5).map((x) => x.anchorHref), [null, null, null, null, null], "no href above the five");
      assert.deepEqual(d.map((x) => x.anchorDead), [false, false, true, true, false, false], "the two host:port links are dressed dead");
      assert.deepEqual([d[4].w, d[4].h], [100, 20], "the floor picture measures under the floor");
      assert.equal(d[5].anchorHref, WEB + "/page.html", "the live web link keeps its href");
      // FAILS BEFORE: the picture's own title carries the address on every one of the five, the click being the figure's own, and it is the tooltip the reader sees (before: null, or the dead link's words)
      for (let i = 0; i < 5; i++) {
        assert.equal(d[i].imgTitle, WEB_LINE(WEB + "/" + d[i].alt + ".svg"), d[i].alt + ": the address line as the picture's title");
        assert.equal(d[i].tooltip, d[i].imgTitle, d[i].alt + ": and the tooltip the browser shows is that line, not the anchor's words");
      }
      assert.equal(d[5].imgTitle, null, "inside a live web link the click is the browser's: no line of the viewer's");
      // the control where the floor allows it: after the anchor of a bare one (as before), inside the anchor right after the picture of a captioned one (FAILS BEFORE: none), none under the floor
      assert.deepEqual(d.map((x) => x.control), [true, true, true, true, false, true], "a control on each but the picture under the floor");
      assert.deepEqual([d[1].controlAfterImg, d[1].controlInAnchor, d[3].controlAfterImg, d[3].controlInAnchor], [true, true, true, true], "the captioned pictures' controls stand inside their anchors right after the picture, since no click of those anchors owns the figure");
      assert.deepEqual([d[0].controlInAnchor, d[2].controlInAnchor], [false, false], "the bare pictures' controls stand after their anchors, as before");
      assert.deepEqual(d.filter((x) => x.control).map((x) => x.web), [true, true, true, true, true], "every control wears the web dress");
      // the plain click on each of the five: the tab at its own address, one open, the viewer unmoved (kept; the case's other half)
      for (let i = 0; i < 5; i++) {
        assert.deepEqual(await clickPicture(page, d[i].alt), [WEB + "/" + d[i].alt + ".svg"], d[i].alt + ": the plain click opens the tab at the picture's address");
        assert.equal(await base(page), "report.md", d[i].alt + ": the viewer shows the report still");
      }
      // a Ctrl-click on a link-shape picture opens once, at the picture's address, and moves the viewer nowhere (a regression routing it
      // to the links listener, or opening twice, reds here); the click's ctrlKey is read back off a capture listener, so the form cannot
      // degrade to a plain click unseen again (the file review's round 13, extra6-2: mouse.click's modifiers option is dropped by Playwright)
      await page.evaluate(() => { const w = window as any; w.__ctrl = []; document.addEventListener("click", (ev) => { w.__ctrl.push((ev as MouseEvent).ctrlKey); }, { capture: true }); });
      assert.deepEqual(await clickPicture(page, "deadcap", true), [WEB + "/deadcap.svg"], "a Ctrl-click on the captioned dead link's picture: the tab at the picture's address, once");
      assert.deepEqual(await page.evaluate(() => (window as any).__ctrl.splice(0)), [true], "the click reached the document with ctrlKey set: a Ctrl-click, not a plain one (mouse.click takes no modifiers option; the key is held around the click)");
      assert.equal(await base(page), "report.md", "and the viewer shows the report still");
      assert.ok(served.some((s) => s.endsWith("/floor.svg")), "the second server served the pictures: " + JSON.stringify(served));
      assert.deepEqual(errors, [], "no page errors");
      await page.close();
    });
  } finally { await second.close(); }
});

// ── a remote picture under the floor: no control, the address in its title, and the outbound mark on the picture itself ──────
// (the file review's round 12, fresh-1 with tests-2: the floor withholds the control under 48 px and the picture's title is a
// hover tooltip, so on a coarse pointer a plain tap opened the credentialed tab with nothing visible before it, and no executed
// case read the title of a remote picture under the floor; the picture now wears the control's dashed dress itself, an outline
// keyed on the mark the decision sets, at rest where hover is none or any pointer is coarse and on hover otherwise, in the outbound
// dress's own token, var(--outbound-line), the one the control's dashed border wears at rest; the file review's round 13, ui-1 with
// extra6-1 and extra7-2: the button family's hairline it first wore read 1.35:1 dark and 1.25:1 light, and (hover: none) alone
// dressed nothing on a touchscreen laptop, whose primary pointer hovers). Since the painted-contrast ask of 2026-09-23 the report
// also holds a remote picture in each shape of an href-less dead link, bare, captioned and under the floor, whose dress the three
// cases below read as painted (paintedRatio)
const TINY_TEXT = "# Report\n\n![local](figs/plot.svg)\n\n" + PARA(1) + "\n\n![build](" + WEB + "/tiny.svg)\n\n" + PARA(2) + "\n\n![big](" + WEB + "/pic.svg)\n\n" + PARA(3) + "\n\n"
  // a remote picture inside a dead host:port link (fv-dead, the href removed), bare (its control after the anchor), captioned (its
  // control inside the anchor, after the picture, its caption carrying bold words and inline code) and under the floor (the mark on
  // the picture, inside the anchor); a dead link owns no click, so a tap or a click opens the tab from inside it (the link-shapes
  // case's click, the press on the control the three painted cases hold and the touch case's tap), and Enter and Space on its
  // control too, and the dress there must paint at 3:1 too (the painted-contrast ask of 2026-09-23)
  + "[![deadbare](" + WEB + "/deadbare.svg)](localhost:8080)\n\n" + PARA(4) + "\n\n"
  + "[![deadcap](" + WEB + "/deadcap.svg) a caption beside the **dead** link and its `code`](localhost:8080)\n\n" + PARA(5) + "\n\n[![deadbuild](" + WEB + "/deadtiny.svg)](localhost:8080)\n\n" + PARA(6) + "\n\n"
  // the grounds the mark's line read against before its ring (the file review's round 14, correctness-2 with extra5-1 and extra5-2),
  // each a remote picture under the floor: inside a ==highlight==, in a table header, in an even table row and in a note callout
  + "A sentence ==![hl](" + WEB + "/hl.svg)== highlighted.\n\n"
  + "| head ![th](" + WEB + "/th.svg) | b |\n|---|---|\n| x | y |\n| z ![even](" + WEB + "/even.svg) | w |\n\n"
  + "> [!note]\n> note words ![conote](" + WEB + "/conote.svg) here\n\n" + PARA(7) + "\n\n"
  // the neighbour pin's scenes (ringCoversNoNeighbour): a glyph glued to a picture under the floor before and after it in a paragraph,
  // a highlight and a table cell of an even row, and two badges glued to each other
  + "word![ngp](" + WEB + "/ngp.svg)word\n\n==ab![ngh](" + WEB + "/ngh.svg)cd==\n\n"
  + "| h1 | h2 |\n|---|---|\n| s | t |\n| q![ngt](" + WEB + "/ngt.svg)q | r |\n\n"
  + "![nb1](" + WEB + "/nb1.svg)![nb2](" + WEB + "/nb2.svg) badges\n\n" + PARA(8) + "\n";
const TINY_DOCS: Record<string, string> = { [REPORT]: TINY_TEXT, [PLOT]: svg("#456") };
/** The tiny report's figures in order, and the second server's sizes for its remote pictures under the floor (20 by 20 each). */
const TINY_ALTS = ["local", "build", "big", "deadbare", "deadcap", "deadbuild", "hl", "th", "even", "conote", "ngp", "ngh", "ngt", "nb1", "nb2"];
const TINY_SIZES: Record<string, [number, number]> = Object.fromEntries(["tiny", "deadtiny", "hl", "th", "even", "conote", "ngp", "ngh", "ngt", "nb1", "nb2"].map((n) => ["/" + n + ".svg", [20, 20] as [number, number]]));
type Under = { alt: string; w: number; h: number; control: boolean; controlOpacity: string | null; controlBorder: string | null; title: string | null; mark: boolean; outline: string; outlineWidth: string; outlineColor: string; border: string };
/** The figures as the reader sees them: the box, the control after the img with its opacity and border colour, the title, the
 *  mark attribute, and the computed outline and border; with the media the page is under and the badge's centre. */
const under = (page: any): Promise<{ hoverNone: boolean; coarse: boolean; imgs: Under[]; centre: { x: number; y: number } }> => page.evaluate(() => {
  const imgs = Array.from(document.querySelectorAll(".fileview-md img")) as HTMLImageElement[];
  const b = imgs[1].getBoundingClientRect();
  return {
    hoverNone: matchMedia("(hover: none)").matches, coarse: matchMedia("(pointer: coarse)").matches, centre: { x: b.left + b.width / 2, y: b.top + b.height / 2 },
    imgs: imgs.map((img) => { const r = img.getBoundingClientRect(); const cs = getComputedStyle(img); const n = img.nextElementSibling; const c = n && n.hasAttribute("data-fv-figopen") ? n as HTMLElement : null;
      return { alt: img.getAttribute("alt") || "", w: r.width, h: r.height, control: !!c, controlOpacity: c ? getComputedStyle(c).opacity : null, controlBorder: c ? getComputedStyle(c).borderColor : null, title: img.getAttribute("title"), mark: img.hasAttribute("data-fv-figweb"), outline: cs.outlineStyle, outlineWidth: cs.outlineWidth, outlineColor: cs.outlineColor, border: cs.borderStyle + " " + cs.borderWidth }; }),
  };
});

/** The first opaque background behind the badge (the ancestors climbed to the first whose background-color has no alpha: the
 *  viewer's card, .fileview, painting var(--bg)); the ground the outline's rgba is composited over, read off the page and never typed. */
const groundOf = (page: any): Promise<string> => page.evaluate(() => {
  for (let e = (document.querySelectorAll(".fileview-md img")[1] as HTMLElement).parentElement; e; e = e.parentElement) { const bg = getComputedStyle(e).backgroundColor; if (/^rgb\(/.test(bg)) return bg; }
  return "";
});
/** WCAG 2 contrast of a computed colour (an rgb or rgba string) composited over an opaque computed ground. */
function contrastOver(fg: string, ground: string): number {
  const parse = (c: string): number[] => { const m = /^rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*(?:,\s*([\d.]+))?\s*\)$/.exec(c); assert.ok(m, "a computed colour: " + c); return [+m![1], +m![2], +m![3], m![4] === undefined ? 1 : +m![4]]; };
  const f = parse(fg), g = parse(ground);
  assert.equal(g[3], 1, "the ground is opaque: " + ground);
  const over = [0, 1, 2].map((i) => f[i] * f[3] + g[i] * (1 - f[3]));
  const lum = (rgb: number[]) => { const ch = (c: number) => { c /= 255; return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); }; return 0.2126 * ch(rgb[0]) + 0.7152 * ch(rgb[1]) + 0.0722 * ch(rgb[2]); };
  const [hi, lo] = [lum(over), lum(g)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}
/** The colour a token computes to on the page: a probe element inside the document wearing it as its color, read and removed. */
const tokenColour = (page: any, token: string): Promise<string> => page.evaluate((tok: string) => { const el = document.createElement("span"); el.style.color = "var(" + tok + ")"; document.querySelector(".fileview-md")!.appendChild(el); const c = getComputedStyle(el).color; el.remove(); return c; }, token);
/** The mark's outline and the control's border, one colour, and that colour at least 3:1 over the first opaque ground (the legibility
 *  floor for a line that is the only sign of a state, WCAG 1.4.11): the file review's round 13, ui-1 with extra6-1, where the family's
 *  10 percent hairline read 1.35:1 dark and 1.25:1 light, present in the DOM as a faint ring under the floor on a 20 px badge. It reads
 *  the token's computed colour over the first opaque ground, not the paint: no element opacity enters it (the web control's own, a
 *  dead link's around the dress), so it holds the token alone, and it stayed green over the old sheet while the dress inside a dead
 *  link painted 2.47:1 dark and 2.40:1 light; the painted read, through every opacity on the way, is paintedRatio (the
 *  painted-contrast ask of 2026-09-23). */
async function oneLegibleColour(page: any, r: { imgs: Under[] }, theme: string): Promise<void> {
  assert.equal(r.imgs[1].outlineColor, r.imgs[2].controlBorder, theme + " theme: the mark's outline colour is the control's border colour, one token (" + r.imgs[1].outlineColor + ")");
  const ground = await groundOf(page);
  const ratio = contrastOver(r.imgs[1].outlineColor, ground);
  // FAILS BEFORE (the file review's round 13): 1.35 dark and 1.25 light over the same ground
  assert.ok(ratio >= 3, theme + " theme: the mark's outline, " + r.imgs[1].outlineColor + " over the first opaque ground " + ground + ", reads " + ratio.toFixed(2) + ":1, under the 3:1 floor for the only sign of the outbound state");
}
/** A PNG (8-bit RGB or RGBA, non-interlaced: what a playwright screenshot is) decoded to raw rows (styles-kept-embed.test.ts's decoder). */
function decodePng(buf: Buffer): { width: number; height: number; bpp: number; data: Buffer } {
  assert.equal(buf.readUInt32BE(0), 0x89504e47, "a PNG");
  let pos = 8, width = 0, height = 0, bitDepth = 0, colorType = 0, interlace = 0;
  const idat: Buffer[] = [];
  while (pos + 8 <= buf.length) {
    const len = buf.readUInt32BE(pos); const type = buf.toString("ascii", pos + 4, pos + 8); const data = buf.subarray(pos + 8, pos + 8 + len);
    if (type === "IHDR") { width = data.readUInt32BE(0); height = data.readUInt32BE(4); bitDepth = data[8]; colorType = data[9]; interlace = data[12]; }
    else if (type === "IDAT") idat.push(data);
    else if (type === "IEND") break;
    pos += 12 + len;
  }
  assert.equal(bitDepth, 8); assert.equal(interlace, 0);
  const bpp = colorType === 6 ? 4 : colorType === 2 ? 3 : 0;
  assert.ok(bpp, "RGB or RGBA");
  const raw = zlib.inflateSync(Buffer.concat(idat)); const stride = width * bpp; const out = Buffer.alloc(stride * height); let p = 0;
  for (let y = 0; y < height; y++) {
    const f = raw[p++]; const row = y * stride; const prev = row - stride;
    for (let x = 0; x < stride; x++) {
      const a = x >= bpp ? out[row + x - bpp] : 0, b = y > 0 ? out[prev + x] : 0, c = x >= bpp && y > 0 ? out[prev + x - bpp] : 0, v = raw[p++];
      let r: number;
      switch (f) {
        case 0: r = v; break; case 1: r = v + a; break; case 2: r = v + b; break; case 3: r = v + ((a + b) >> 1); break;
        case 4: { const pa = Math.abs(b - c), pb = Math.abs(a - c), pc = Math.abs(a + b - 2 * c); r = v + (pa <= pb && pa <= pc ? a : pb <= pc ? b : c); break; }
        default: throw new Error("png filter " + f);
      }
      out[row + x] = r & 255;
    }
  }
  return { width, height, bpp, data: out };
}
type Painted = { ratio: number; dash: string; ground: string; outer: string | null; opacities: string[]; at?: string };
/** The dress's line as PAINTED, read off a screenshot of the real page, so every opacity the compositor applied is in the pixels, the
 *  element's own and every ancestor's, and so is the picture under a control whose opacity is under 1, which oneLegibleColour's
 *  computed colours never read. The line: the control's border rows and columns past its 6 px radius, or the mark's outline ring,
 *  1 px out past its 1 px offset. The control's line is read against the ground the sheet controls, its own background (its padding
 *  pixel, left + 2 at the vertical middle, the colour of the line's inner side and of every gap between its dashes); over a picture
 *  the line's outer side is the author's pixels, which no colour of the dress can clear for every picture, so `outer` (the pixel three
 *  rows above the control's top border, clear of any smoothing at the border's edge and inside the picture, whose top the control sits
 *  6px below) is returned for the case's witness and never read against. The dash is the most frequent colour on the line that is
 *  not the ground; the ground must appear among the line's pixels (the gaps) and the dash cover at least a quarter of them, so a
 *  stray pixel cannot carry the read. The mark's line is read by the worst dash-to-ring ratio (markWorst: every dash pixel against the
 *  pixel one step toward the picture and one step away, whatever paints there, and the dash against every gap pixel, with the worst
 *  read's place in `at`), since the one ground pixel this read took for it, in the offset above the picture, passed the dark theme's
 *  ==highlight== at 4.83:1 while the dashes painted 2.40:1 against its tint on both sides (the file review's round 14, correctness-2
 *  with extra5-1 and extra5-2). Every element on the way whose computed opacity is not 1 is listed for the message. `alt`
 *  names the picture; the control is the one after it (inside a captioned anchor) or after its anchor. A read at rest scrolls the
 *  element to the centre first and asserts the pointer is over neither the picture nor its control (a scroll moves the page under a
 *  resting pointer, and the hover would reveal the control: the first run of this read over the old sheet read a control the
 *  pointer had revealed and took it for one at rest); a hover read neither scrolls nor asserts, since a scroll would move the
 *  picture from under the pointer. */
async function paintedRatio(page: any, alt: string, kind: "control" | "mark", mode: "rest" | "hover" = "rest"): Promise<Painted> {
  const find = (s: boolean) => page.evaluate(([alt, kind, s]: [string, string, boolean]) => {
    const img = Array.from(document.querySelectorAll(".fileview-md img")).find((i) => i.getAttribute("alt") === alt) as HTMLElement;
    let el: HTMLElement | null = img;
    if (kind === "control") {
      let a: Element = img;
      if (!(img.nextElementSibling && img.nextElementSibling.hasAttribute("data-fv-figopen"))) for (let p = a.parentElement; p && (p.localName === "a" || p.classList.contains("fc-imgwrap") || p.localName === "picture"); p = a.parentElement) a = p;
      el = a.nextElementSibling && a.nextElementSibling.hasAttribute("data-fv-figopen") ? a.nextElementSibling as HTMLElement : null;
    }
    if (!el) return null;
    if (s) el.scrollIntoView({ block: "center" });
    const hovered = img.matches(":hover") || (kind === "control" && el.matches(":hover"));
    const opacities: string[] = [];
    for (let e: Element | null = el; e; e = e.parentElement) { const o = getComputedStyle(e).opacity; if (o !== "1") opacities.push(e.localName + "." + Array.from(e.classList).join(".") + " " + o); }
    const r = el.getBoundingClientRect();
    return { left: r.left, top: r.top, right: r.right, bottom: r.bottom, opacities, dpr: window.devicePixelRatio, hovered };
  }, [alt, kind, s]);
  if (mode === "rest") { await find(true); await frames(page, 2); }
  const r = await find(false);
  assert.ok(r, alt + ": the " + kind + " is on the page");
  if (mode === "rest") assert.equal(r.hovered, false, alt + ": at rest, the pointer is over neither the picture nor its " + kind);
  assert.equal(r.dpr, 1, "one device pixel per CSS pixel, so a screenshot pixel is a pixel of the line");
  const ox = Math.floor(r.left) - 8, oy = Math.floor(r.top) - 8;
  const png = decodePng(await page.screenshot({ clip: { x: ox, y: oy, width: Math.ceil(r.right - r.left) + 16, height: Math.ceil(r.bottom - r.top) + 16 } }));
  const at = (x: number, y: number): number[] => { const k = ((y - oy) * png.width + (x - ox)) * png.bpp; return [png.data[k], png.data[k + 1], png.data[k + 2]]; };
  const rgb = (c: number[]) => "rgb(" + c.join(", ") + ")";
  const L = Math.round(r.left), T = Math.round(r.top), R = Math.round(r.right), B = Math.round(r.bottom);
  if (kind === "mark") return { ...markWorst(at, L, T, R, B, alt), outer: null, opacities: r.opacities };
  const line: number[][] = [];
  for (let x = L + 6; x <= R - 7; x++) line.push(at(x, T), at(x, B - 1));
  for (let y = T + 6; y <= B - 7; y++) line.push(at(L, y), at(R - 1, y));
  const ground = at(L + 2, Math.round((T + B) / 2));
  const outer = at(Math.round((L + R) / 2), T - 3);
  const counts = new Map<string, number>();
  for (const p of line) counts.set(rgb(p), (counts.get(rgb(p)) || 0) + 1);
  const g = rgb(ground);
  let dash = "", most = 0;
  for (const [c, n] of counts) if (c !== g && n > most) { dash = c; most = n; }
  // the two guards' messages open on the modal colour's ratio, so a read they refuse still states its figure, then list the line's pixels
  const seen = (dash ? "its modal colour " + dash + " against " + g + " at " + contrastOver(dash, g).toFixed(3) + ":1; " : "") + "the line read " + Array.from(counts).map(([c, n]) => c + " x" + n).join(", ");
  assert.ok((counts.get(g) || 0) > 0, alt + ": the " + kind + "'s ground " + g + " appears among its line's pixels, the gaps between the dashes (" + seen + ")");
  assert.ok(most * 4 >= line.length, alt + ": the " + kind + "'s dash covers at least a quarter of its line's " + line.length + " pixels, so a stray pixel cannot carry the read (" + seen + ")");
  return { ratio: contrastOver(dash, g), dash, ground: g, outer: rgb(outer), opacities: r.opacities };
}
/** The mark's line by the worst dash-to-ring ratio (the file review's round 14, correctness-2 with extra5-1 and extra5-2), over the
 *  outline ring's pixels (1 px out past the 1 px offset from the picture's box L, T, R, B, on all four sides and at the corners), each
 *  with the pixel one step toward the picture and one step away, whatever paints there. The dash is the ring's most frequent colour;
 *  a pixel within 6 per channel of it is a dash pixel, read against both of its neighbours, and every other pixel is a gap, read
 *  against the dash, but for a dash end: Chromium spaces a 1px dashed outline fractionally and paints each dash end as a partial
 *  pixel, a blend of the dash with the pixels beside it, so a pixel that fits such a blend (the dash's weight 0.06 to 0.94, the rest
 *  from its inner and outer neighbours, each channel at most 7 off) is neither and is not read, the read's stated bound (read as a gap,
 *  the plain page's dash ends would red a correct sheet at 1.48:1). paintedRatio's two guards stand here too: the dash covers at least
 *  a quarter of the ring's pixels, so a stray pixel cannot carry the read, and a gap is among them, the ground the dash is read
 *  against. Returns the worst ratio, the dash, the colour read against it there, and where: the side, and inner, outer or gap. */
function markWorst(at: (x: number, y: number) => number[], L: number, T: number, R: number, B: number, alt: string): { ratio: number; dash: string; ground: string; at: string } {
  const rgb = (c: number[]) => "rgb(" + c.join(", ") + ")";
  type Pt = [number, number, number, number, number, number, string];   // the pixel, its neighbour toward the picture, its neighbour away from it, the side
  const pts: Pt[] = [];
  for (let x = L - 1; x <= R; x++) pts.push([x, T - 2, x, T - 1, x, T - 3, "top"], [x, B + 1, x, B, x, B + 2, "bottom"]);
  for (let y = T - 1; y <= B; y++) pts.push([L - 2, y, L - 1, y, L - 3, y, "left"], [R + 1, y, R, y, R + 2, y, "right"]);
  pts.push([L - 2, T - 2, L - 1, T - 1, L - 3, T - 3, "top-left corner"], [R + 1, T - 2, R, T - 1, R + 2, T - 3, "top-right corner"], [L - 2, B + 1, L - 1, B, L - 3, B + 2, "bottom-left corner"], [R + 1, B + 1, R, B, R + 2, B + 2, "bottom-right corner"]);
  const counts = new Map<string, number>();
  for (const [x, y] of pts) { const c = rgb(at(x, y)); counts.set(c, (counts.get(c) || 0) + 1); }
  let dash = "", most = 0;
  for (const [c, n] of counts) if (n > most) { dash = c; most = n; }
  const tk = (dash.match(/\d+/g) || []).map(Number);   // the dash's channels
  const nearDash = (p: number[]) => Math.max(Math.abs(p[0] - tk[0]), Math.abs(p[1] - tk[1]), Math.abs(p[2] - tk[2])) <= 6;
  /** A blend of the dash with the inner and outer neighbours (p = a dash + b inner + c outer, a + b + c = 1), by least squares, or with
   *  one of the two alone. */
  const isEnd = (p: number[], pi: number[], po: number[]): boolean => {
    const fits = (a: number, b: number) => { const c = 1 - a - b; return a >= 0.06 && a <= 0.94 && b >= -0.02 && c >= -0.02 && [0, 1, 2].every((k) => Math.abs(a * tk[k] + b * pi[k] + c * po[k] - p[k]) <= 7); };
    const u = [0, 1, 2].map((k) => tk[k] - po[k]), v = [0, 1, 2].map((k) => pi[k] - po[k]), w = [0, 1, 2].map((k) => p[k] - po[k]);
    const dot = (a: number[], b: number[]) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
    const uu = dot(u, u), vv = dot(v, v), uv = dot(u, v), uw = dot(u, w), vw = dot(v, w), det = uu * vv - uv * uv;
    if (Math.abs(det) > 1e-6 && fits((uw * vv - vw * uv) / det, (vw * uu - uw * uv) / det)) return true;
    for (const g of [pi, po]) {
      const tg = [0, 1, 2].map((k) => tk[k] - g[k]), n = dot(tg, tg);
      if (n < 1) continue;
      const a = dot(tg, [0, 1, 2].map((k) => p[k] - g[k])) / n;
      if (a >= 0.06 && a <= 0.94 && [0, 1, 2].every((k) => Math.abs(a * tk[k] + (1 - a) * g[k] - p[k]) <= 7)) return true;
    }
    return false;
  };
  let worst = Infinity, where = "", against = "", dashes = 0, ends = 0, gaps = 0;
  for (const [x, y, ix, iy, ox, oy, side] of pts) {
    const p = at(x, y), pi = at(ix, iy), po = at(ox, oy);
    if (nearDash(p)) {
      dashes++;
      for (const [q, step] of [[pi, "inner"], [po, "outer"]] as Array<[number[], string]>) { const v = contrastOver(rgb(p), rgb(q)); if (v < worst) { worst = v; where = side + " " + step; against = rgb(q); } }
    } else if (isEnd(p, pi, po)) ends++;
    else { gaps++; const v = contrastOver(dash, rgb(p)); if (v < worst) { worst = v; where = side + " gap"; against = rgb(p); } }
  }
  const seen = "its modal colour " + dash + ", " + dashes + " dash, " + ends + " dash-end and " + gaps + " gap pixels of " + pts.length + "; the ring read " + Array.from(counts).map(([c, n]) => c + " x" + n).join(", ");
  assert.ok(most * 4 >= pts.length, alt + ": the mark's dash covers at least a quarter of its line's " + pts.length + " pixels, so a stray pixel cannot carry the read (" + seen + ")");
  assert.ok(gaps > 0, alt + ": a gap between the mark's dashes is among its line's pixels, the ground the dash is read against (" + seen + ")");
  return { ratio: worst, dash, ground: against, at: where + "; " + dashes + " dash, " + ends + " dash-end and " + gaps + " gap pixels" };
}
/** The grounds the mark's line read against before its ring of var(--bg), a picture under the floor on each (the file review's round
 *  14, correctness-2 with extra5-1 and extra5-2): the tiny report's alt and the words for the ground. */
const RING_GROUNDS: Array<[string, string]> = [["hl", "inside a highlight"], ["th", "in a table header"], ["even", "in an even table row"], ["conote", "in a note callout"]];
/** The dresses at rest the touch and laptop cases read: the web control and the mark, each alone and inside a dead link (the tiny
 *  report's shapes), the control both after a bare dead link and inside a captioned one, and the mark on RING_GROUNDS. */
const DRESSES: Array<[string, "control" | "mark", string]> = [["big", "control", "the web control at rest"], ["deadbare", "control", "the web control at rest after a bare dead link"], ["deadcap", "control", "the web control at rest inside a captioned dead link"], ["build", "mark", "the mark at rest"], ["deadbuild", "mark", "the mark at rest inside a dead link"],
  ...RING_GROUNDS.map(([alt, ground]): [string, "control" | "mark", string] => [alt, "mark", "the mark at rest " + ground])];
/** Reads `reads` as painted (paintedRatio) and pushes onto `fails` each that is under 3:1 (or, with `clears` false, each that is not:
 *  a ground past the stated bound), so a case collects every failing read and asserts once at its end; returns the reads by alt, and
 *  hands each read to `note` (the case's test diagnostic, so the log carries every figure, green or red). The body's scroll is
 *  restored after, since the cases tap at a centre read before the reads scroll. */
async function paintedLegible(page: any, where: string, fails: string[], note: (m: string) => void, clears = true, reads = DRESSES): Promise<Map<string, Painted>> {
  await page.mouse.move(5, 5);   // the pointer off every picture (the gate's click in openTiny, or a tap, left it over one)
  const top = await page.evaluate(() => (document.querySelector(".fileview-body") as HTMLElement).scrollTop);
  const out = new Map<string, Painted>();
  for (const [alt, kind, what] of reads) {
    const p = await paintedRatio(page, alt, kind);
    out.set(alt, p);
    const opac = " (opacities on the way: " + (p.opacities.join(", ") || "none") + ")";
    const worst = p.at ? " (the worst read: " + p.at + ")" : "";
    note("painted, " + where + ": " + what + " " + p.dash + " over " + p.ground + ", " + p.ratio.toFixed(3) + ":1" + worst + opac);
    // FAILS BEFORE (61d69cba1): inside a dead link the control at 0.8 x 0.7 and the mark at 0.7; on a VS Code ground at #404040 the control at 0.8 too.
    // FAILS BEFORE the ring (the file review's round 14, correctness-2 with extra5-1 and extra5-2): the mark inside the dark highlight,
    // and on the VS Code grounds the mark on the tinted grounds of RING_GROUNDS, each read by the worst dash-to-ring ratio
    if (clears && p.ratio < 3) fails.push(where + ": " + what + " paints " + p.dash + " over " + p.ground + ", " + p.ratio.toFixed(3) + ":1, under the 3:1 floor for the outbound dress's line" + worst + opac);
    if (!clears && p.ratio >= 3) fails.push(where + ": " + what + " paints " + p.dash + " over " + p.ground + ", " + p.ratio.toFixed(3) + ":1, past the stated bound, where it should fall under 3:1 (the bound is stated exact)" + worst + opac);
  }
  await page.evaluate((y: number) => { (document.querySelector(".fileview-body") as HTMLElement).scrollTop = y; }, top);
  await frames(page, 2);
  return out;
}
/** The neighbour pin's scenes (the tiny report's last pictures): the alt of the picture whose ring is read, and the scene. */
const NEIGHBOURS: Array<[string, string]> = [["ngp", "a paragraph"], ["ngh", "a highlight"], ["ngt", "a table cell"], ["nb2", "two glued badges"]];
/** The ring covers no neighbouring ink inside the neighbour's own box (the file review's round 14, correctness-2 with extra5-1 and
 *  extra5-2; the ink a glyph paints past its box and the edge of text painted after the picture are the ring's two stated bounds,
 *  which the bound case after the laptop's records by ringOverGlyph and by a float's paintedRatio): a box-shadow takes no
 *  layout and paints with the picture in tree order, so a bare ring covers its width of whatever stands before the picture on its line.
 *  For each scene of NEIGHBOURS, the picture's neighbours (the glyph glued before it and the one glued after it, or the badge glued
 *  before the second badge) are read off a screenshot of the page as it is and of the same clip with every mark's box-shadow
 *  overridden to none, the same page without the ring (the margin kept, so nothing moves), and a neighbour fails when a pixel whose
 *  centre lies inside its rect changes, or an ink pixel of it does (a pixel of the reference more than 24 off the rect's modal colour
 *  on a channel); a pixel only partly inside, in the rect's fractional edge column, is neither and is not read, the pin's stated bound
 *  (the ring's edge meets a glued neighbour there). Guards: the picture wears the mark's outline as it is read (on hover, the pointer
 *  over it, `hover` true; at rest otherwise), each neighbour is found, and the override takes the ring off (the picture's computed
 *  box-shadow none under it) and moves nothing, so the second shot is the page without the ring (on the page's own ground the ring
 *  paints the colour beneath it, and the clip's changed pixels, noted, can be none). Over sheets with no ring the two shots are one paint, a green by design; over a bare 3px ring with no margin
 *  beside it the glyphs before the picture red. Each failure is pushed onto `fails`, each read handed to `note`; the scroll is restored. */
async function ringCoversNoNeighbour(page: any, where: string, fails: string[], note: (m: string) => void, hover = false): Promise<void> {
  type Rect = { left: number; top: number; right: number; bottom: number };
  await page.mouse.move(5, 5);
  const top = await page.evaluate(() => (document.querySelector(".fileview-body") as HTMLElement).scrollTop);
  for (const [alt, scene] of NEIGHBOURS) {
    const layout = (scroll: boolean): Promise<{ img: Rect; near: Record<string, Rect>; outline: string; shadow: string; hovered: boolean }> => page.evaluate(([alt, scroll]: [string, boolean]) => {
      const img = Array.from(document.querySelectorAll(".fileview-md img")).find((x) => x.getAttribute("alt") === alt) as HTMLElement;
      if (scroll) img.scrollIntoView({ block: "center" });
      const box = (r: DOMRect) => ({ left: r.left, top: r.top, right: r.right, bottom: r.bottom });
      const glyph = (node: Node | null, last: boolean) => { if (!node || node.nodeType !== 3 || !(node as Text).length) return null; const t = node as Text; const r = document.createRange(); r.setStart(t, last ? t.length - 1 : 0); r.setEnd(t, last ? t.length : 1); return box(r.getBoundingClientRect()); };
      const near: Record<string, { left: number; top: number; right: number; bottom: number }> = {};
      if (alt === "nb2") { const b = img.previousSibling; if (b && b.nodeType === 1 && (b as Element).getAttribute("alt") === "nb1") near["the badge before it"] = box((b as Element).getBoundingClientRect()); }
      else { const b = glyph(img.previousSibling, true), a = glyph(img.nextSibling, false); if (b) near["the glyph before it"] = b; if (a) near["the glyph after it"] = a; }
      const cs = getComputedStyle(img);
      return { img: box(img.getBoundingClientRect()), near, outline: cs.outlineStyle, shadow: cs.boxShadow, hovered: img.matches(":hover") };
    }, [alt, scroll]);
    await layout(true);
    await frames(page, 2);
    let lay = await layout(false);
    if (hover) {
      await page.mouse.move((lay.img.left + lay.img.right) / 2, (lay.img.top + lay.img.bottom) / 2);
      await page.waitForFunction((alt: string) => getComputedStyle(Array.from(document.querySelectorAll(".fileview-md img")).find((x) => x.getAttribute("alt") === alt)!).outlineStyle === "dashed", alt, { timeout: 5000 }).catch(() => null);
      await frames(page, 2);
      lay = await layout(false);
    }
    const names = Object.keys(lay.near);
    assert.deepEqual(names, alt === "nb2" ? ["the badge before it"] : ["the glyph before it", "the glyph after it"], where + ": " + scene + ": the neighbours the scene glues to the picture are found");
    assert.deepEqual([lay.outline, lay.hovered], ["dashed", hover], where + ": " + scene + ": the picture wears the mark's outline as the pin reads it" + (hover ? ", the pointer over it" : ", at rest"));
    const rects = names.map((k) => [k, lay.near[k]] as [string, Rect]);
    const xs = [lay.img.left - 12, lay.img.right + 12, ...rects.flatMap(([, r]) => [r.left - 2, r.right + 2])], ys = [lay.img.top - 12, lay.img.bottom + 12, ...rects.flatMap(([, r]) => [r.top - 2, r.bottom + 2])];
    const cx = Math.max(0, Math.floor(Math.min(...xs))), cy = Math.max(0, Math.floor(Math.min(...ys))), cw = Math.ceil(Math.max(...xs)) - cx, ch = Math.ceil(Math.max(...ys)) - cy;
    const shot = async () => decodePng(await page.screenshot({ clip: { x: cx, y: cy, width: cw, height: ch } }));
    const withRing = await shot();
    await page.evaluate(() => { const st = document.createElement("style"); st.id = "neighbour-pin-noring"; st.textContent = ".fileview-md img[data-fv-figweb] { box-shadow: none !important; }"; document.head.appendChild(st); });
    await frames(page, 3);
    const noRing = await shot();
    const still = await layout(false);
    await page.evaluate(() => document.getElementById("neighbour-pin-noring")!.remove());
    await frames(page, 2);
    assert.deepEqual([still.img, still.hovered, still.shadow], [lay.img, hover, "none"], where + ": " + scene + ": the override takes the ring off (the picture's computed box-shadow none under it), moves nothing, and the pointer's state holds between the two shots");
    const px = (png: { width: number; bpp: number; data: Buffer }, x: number, y: number) => { const k = ((y - cy) * png.width + (x - cx)) * png.bpp; return [png.data[k], png.data[k + 1], png.data[k + 2]]; };
    let clipChanged = 0;
    for (let y = cy; y < cy + ch; y++) for (let x = cx; x < cx + cw; x++) { const a = px(withRing, x, y), b = px(noRing, x, y); if (a[0] !== b[0] || a[1] !== b[1] || a[2] !== b[2]) clipChanged++; }
    for (const [k, r] of rects) {
      const x0 = Math.floor(r.left), x1 = Math.ceil(r.right) - 1, y0 = Math.floor(r.top), y1 = Math.ceil(r.bottom) - 1;
      const modes = new Map<string, number>();
      for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) { const c = px(noRing, x, y).join(","); modes.set(c, (modes.get(c) || 0) + 1); }
      let mode = "", mn = 0;
      for (const [c, n] of modes) if (n > mn) { mode = c; mn = n; }
      const mc = mode.split(",").map(Number);
      let centre = 0, ink = 0, inkChanged = 0;
      const seen: string[] = [];
      for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) {
        const a = px(withRing, x, y), b = px(noRing, x, y);
        const isInk = Math.max(Math.abs(b[0] - mc[0]), Math.abs(b[1] - mc[1]), Math.abs(b[2] - mc[2])) > 24;
        if (isInk) ink++;
        if (a[0] === b[0] && a[1] === b[1] && a[2] === b[2]) continue;
        const inside = x + 0.5 > r.left && x + 0.5 < r.right && y + 0.5 > r.top && y + 0.5 < r.bottom;
        if (inside) centre++;
        if (isInk) inkChanged++;
        if ((inside || isInk) && seen.length < 4) seen.push((x - x0) + "," + (y - y0) + " rgb(" + b.join(", ") + ") to rgb(" + a.join(", ") + ")");
      }
      const read = where + ": " + scene + ": " + k + " (" + (x1 - x0 + 1) * (y1 - y0 + 1) + " pixels, " + ink + " of them ink): " + centre + " changed with the centre inside, " + inkChanged + " ink pixels changed, the ring " + lay.shadow + ", " + clipChanged + " pixels of the clip changed by it";
      note("neighbour, " + read);
      if (centre > 0 || inkChanged > 0) fails.push(read + ": the ring covers neighbouring ink (" + seen.join("; ") + ")");
    }
    if (hover) await page.mouse.move(5, 5);
  }
  await page.mouse.move(5, 5);
  await page.evaluate((y: number) => { (document.querySelector(".fileview-body") as HTMLElement).scrollTop = y; }, top);
  await frames(page, 2);
}
/** The VS Code editor ground, which the dark theme's --bg follows (var(--vscode-editor-background, #1e1e1e)), set on the root as the
 *  editor's injected variable stands, or taken off with null; the controls' 0.12 s background ease awaited on the big picture's (bounded). */
async function editorGround(page: any, grey: string | null): Promise<void> {
  await page.evaluate((g: string | null) => new Promise<void>((done) => { const c = document.querySelectorAll(".fileview-md img")[2].nextElementSibling as HTMLElement; c.addEventListener("transitionend", () => done(), { once: true }); setTimeout(done, 1500); if (g) document.documentElement.style.setProperty("--vscode-editor-background", g); else document.documentElement.style.removeProperty("--vscode-editor-background"); }), grey);
  await frames(page, 2);
}
/** The web control HELD PRESSED, read as painted (the painted-contrast ask of 2026-09-23, the maintainer's ruling on the press): the
 *  release that opens the tab happens while the button is held, so the pressed state is one a gesture opens the tab from, and its line
 *  clears 3:1 like every other. The picture `alt` names is scrolled to the centre; `by` "mouse" moves the pointer onto its control (the
 *  one paintedRatio finds), eases its hover in and holds a mouse press there, and `by` "Space" holds the Space key on the control, which
 *  the caller has given a keyboard focus, the pointer off it (a button is pressed while Space is down and clicks on its release); held
 *  until the control matches :active and no transition runs on it (bounded), the line is read by pixels (paintedRatio's mode that
 *  neither scrolls nor asserts the pointer away), and only then the release, whose tab is awaited, its address read against the
 *  picture's and closed, so the read is of the pressed paint and the press is shown to open the tab with the viewer unmoved. A read
 *  under 3:1, or a line paintedRatio refuses (a line resampled over two pixel rows can show no ground among its pixels; its guards'
 *  messages open on the modal colour's figure), is pushed onto `fails` with the pressed control's computed transform and border colour;
 *  `note` carries every figure. The body's scroll is restored after, as paintedLegible restores it, and any focus taken off. The mouse
 *  road is also the statement that in Chromium :active holds through the hold of a press the viewer cancels so that no press focuses
 *  the web control (the file review's round 14, ui-1 with extra9-1): `settled` waits for :active and the assertion below requires it. */
async function pressedLegible(page: any, alt: string, where: string, fails: string[], note: (m: string) => void, by: "mouse" | "Space" = "mouse"): Promise<void> {
  const state = (scroll: boolean) => page.evaluate(([alt, scroll]: [string, boolean]) => {
    const img = Array.from(document.querySelectorAll(".fileview-md img")).find((i) => i.getAttribute("alt") === alt) as HTMLImageElement;
    let a: Element = img;
    if (!(img.nextElementSibling && img.nextElementSibling.hasAttribute("data-fv-figopen"))) for (let p = a.parentElement; p && (p.localName === "a" || p.classList.contains("fc-imgwrap") || p.localName === "picture"); p = a.parentElement) a = p;
    const c = a.nextElementSibling as HTMLElement | null;
    if (!c || !c.hasAttribute("data-fv-figopen")) return null;
    if (scroll) img.scrollIntoView({ block: "center" });
    const r = c.getBoundingClientRect(), cs = getComputedStyle(c);
    return { x: r.left + r.width / 2, y: r.top + r.height / 2, src: img.currentSrc, active: c.matches(":active"), hover: c.matches(":hover"), focusVisible: c.matches(":focus-visible"), transform: cs.transform, border: cs.borderTopColor };
  }, [alt, scroll]);
  /** Until the control's :active is `pressed` with no transition running on it, polled on frames and bounded at 3 s. */
  const settled = (pressed: boolean) => page.waitForFunction(([alt, pressed]: [string, boolean]) => {
    const img = Array.from(document.querySelectorAll(".fileview-md img")).find((i) => i.getAttribute("alt") === alt) as HTMLElement;
    let a: Element = img;
    if (!(img.nextElementSibling && img.nextElementSibling.hasAttribute("data-fv-figopen"))) for (let p = a.parentElement; p && (p.localName === "a" || p.classList.contains("fc-imgwrap") || p.localName === "picture"); p = a.parentElement) a = p;
    const c = a.nextElementSibling as HTMLElement;
    return c.matches(":active") === pressed && c.getAnimations().every((x) => x.playState !== "running");
  }, [alt, pressed], { timeout: 3000 });
  await page.mouse.move(5, 5);
  const top = await page.evaluate(() => (document.querySelector(".fileview-body") as HTMLElement).scrollTop);
  const at = await state(true);
  assert.ok(at, where + ": " + alt + ": the web control is on the page");
  await frames(page, 2);
  if (by === "mouse") { const on = await state(false); await page.mouse.move(on.x, on.y); }
  else assert.equal((await state(false)).focusVisible, true, where + ": the web control holds a keyboard focus before the Space press");
  await settled(false);
  await frames(page, 2);
  const opened = page.context().waitForEvent("page", { timeout: 10000 }).catch(() => null);
  if (by === "mouse") await page.mouse.down(); else await page.keyboard.down("Space");
  const held = await settled(true).then(() => true, () => false);
  await frames(page, 2);
  const s = await state(false);
  const p: Painted | Error = await paintedRatio(page, alt, "control", "hover").catch((e: Error) => e);
  const after = await state(false);
  if (by === "mouse") await page.mouse.up(); else await page.keyboard.up("Space");
  const tab = await opened;
  assert.ok(held && s.active && after.active, where + ": the press holds the web control pressed (:active, no transition running) from before the read to after it (settled " + held + ", before " + s.active + ", after " + after.active + ")");
  const pressed = " (pressed: transform " + s.transform + ", border " + s.border + (s.hover ? ", the pointer over it" : ", the pointer off it") + (s.focusVisible ? ", a keyboard focus" : "") + ")";
  if (p instanceof Error) fails.push(where + ": the web control held pressed: its line as painted is refused, " + p.message.split("\n")[0] + pressed);
  else {
    const opac = " (opacities on the way: " + (p.opacities.join(", ") || "none") + ")";
    note("painted, " + where + ": the web control held pressed " + p.dash + " over " + p.ground + ", " + p.ratio.toFixed(3) + ":1" + pressed + opac);
    if (p.ratio < 3) fails.push(where + ": the web control held pressed paints " + p.dash + " over " + p.ground + ", " + p.ratio.toFixed(3) + ":1, under the 3:1 floor for the outbound dress's line" + pressed + opac);
  }
  assert.ok(tab, where + ": the release on the pressed web control opens a tab (none opened in 10 s)");
  await tab.waitForLoadState().catch(() => null);
  assert.equal(tab.url(), at.src, where + ": the tab the release opens is the picture's address (the popup's URL)");
  await tab.close();
  assert.equal(await base(page), "report.md", where + ": the viewer stays on the report after the press");
  await page.evaluate(() => { const f = document.activeElement as HTMLElement | null; if (f && f !== document.body) f.blur(); });   // the reads after it start with nothing holding the keyboard: the Space road leaves it on the control, the mouse road where it was, since no mouse press focuses the web control (the file review's round 14, ui-1 with extra9-1)
  await page.mouse.move(5, 5);
  await page.evaluate((y: number) => { (document.querySelector(".fileview-body") as HTMLElement).scrollTop = y; }, top);
  await frames(page, 2);
}
/** The tiny report open in the chat modal at 900 by 600: the report's remote pictures relayed to the second server (`second`), the
 *  first local figure loaded, the fv-load click lifting the host, then every figure loaded and out of its placeholder; no control is
 *  waited for, since the badge gets none. Shared by the two under-the-floor cases, each on a page of its own: Chromium's
 *  (hover: none) follows touch emulation and does not revert, and the at-rest read must never follow a hover. */
async function openTiny(browser: any, second: { port: number }): Promise<{ page: any; errors: string[] }> {
  const before = async (pg: any): Promise<void> => {
    await pg.context().route((u: URL) => u.href.startsWith(WEB + "/"), async (route: any) => {
      const a = await fromSecond(second.port, new URL(route.request().url()).pathname);
      return route.fulfill({ status: a.status, contentType: a.type, body: a.body });
    });
  };
  const o = await openViewer(browser, "chat", 900, 600, {
    docs: TINY_DOCS, before,
    serve: (u) => { const p = u.pathname === "/file" ? u.searchParams.get("path") || "" : ""; return TINY_DOCS[p] !== undefined && /\.svg$/.test(p) ? { status: 200, type: "image/svg+xml", body: TINY_DOCS[p] } : null; },
  });
  await o.page.waitForFunction(() => { const i = document.querySelectorAll(".fileview-md img")[0] as HTMLImageElement; return i.complete && i.naturalWidth > 0; }, null, { timeout: 10000 });
  await o.page.click('[data-act="fv-load"]');
  await o.page.waitForFunction(() => Array.from(document.querySelectorAll(".fileview-md img")).every((i) => !i.closest('[data-act="fv-load"]') && (i as HTMLImageElement).complete && (i as HTMLImageElement).naturalWidth > 0), null, { timeout: 10000 });
  await frames(o.page, 3);
  return o;
}
test("in a browser: a remote picture under the floor (20 by 20, from the second server) wears no control and carries the address in its title (the executed read of the property file-figure-open.test.ts and file-view-figure-shapes.test.ts pin by spelling); the picture itself wears the outbound mark, the control's dashed dress as an outline, on a fine pointer on hover alone, gone with the pointer and the box unchanged; the loaded picture beside it keeps its control and wears no mark (the file review's round 12, fresh-1 with tests-2)", { timeout: 240000 }, async (t) => {
  const served: string[] = [];
  const second = await secondServer(served, TINY_SIZES);
  try {
    await inBrowser(t, async (browser) => {
      const { page, errors } = await openTiny(browser, second);
      const rest = await under(page);
      assert.equal(rest.hoverNone, false, "a fine pointer");
      assert.deepEqual(rest.imgs.map((x) => x.alt), TINY_ALTS, "the tiny report's figures");
      const badge = rest.imgs[1], big = rest.imgs[2];
      assert.ok(badge.w < 48 && badge.h < 48 && badge.w > 0, "the badge is under the floor on both sides: " + badge.w + " by " + badge.h);
      // tests-2: the title of a remote picture under the floor, read off the real paint
      assert.equal(badge.control, false, "no control under the floor");
      assert.equal(badge.title, WEB_LINE(WEB + "/tiny.svg"), "the picture's own title carries the address, decided before the control's verdict (red when dressFigureTitle moves inside the control's branches)");
      assert.deepEqual([big.control, big.title, big.mark, big.outline], [true, WEB_LINE(WEB + "/pic.svg"), false, "none"], "the loaded picture over the floor: its control and title, and no mark of its own (the mark's population is the title's less the pictures a control stands on)");
      assert.deepEqual([badge.outline, badge.border], ["none", "none 0px"], "at rest on a fine pointer the badge wears no mark: the hover shows it, as it reveals the control");
      await page.mouse.move(rest.centre.x, rest.centre.y);
      await frames(page, 2);
      const hovered = await under(page);
      // FAILS BEFORE: no rule dressed the picture; the only surface was the title, a tooltip
      assert.deepEqual([hovered.imgs[1].mark, hovered.imgs[1].outline, hovered.imgs[1].outlineWidth], [true, "dashed", "1px"], "the pointer over the badge: the outbound mark, the control's dashed dress as an outline on the picture itself");
      assert.deepEqual([hovered.imgs[1].w, hovered.imgs[1].h], [badge.w, badge.h], "an outline, not a border: the badge's box is unchanged by the mark");
      await page.mouse.move(5, 5);
      await frames(page, 2);
      assert.equal((await under(page)).imgs[1].outline, "none", "and gone with the pointer");
      // the web control's rest colour is scoped off :hover (the file review's round 13, ui-1 with extra6-1: a border-color on
      // `.fileview-md .fv-figopen-web` shares .fileview-btn:hover's specificity and stands later in the sheet, so unscoped it would
      // have taken the family's accent hover border off the web control): the pointer over the big picture reveals its control, and
      // over the control the border is the accent, not the rest token
      await page.evaluate(() => { (document.querySelectorAll(".fileview-md img")[2] as HTMLElement).scrollIntoView({ block: "center" }); });
      await frames(page, 2);
      const bigBox = await boxOf(page, ".fileview-md img", 2);
      await page.mouse.move(bigBox.left + bigBox.width / 2, bigBox.top + bigBox.height / 2);
      await waitOpacity(page, 1, "1");
      const ctlBox = await boxOf(page, ".fileview-md [data-fv-figopen]", 1);
      const hoverP = page.evaluate(() => new Promise<void>((done) => { const c = document.querySelectorAll(".fileview-md [data-fv-figopen]")[1] as HTMLElement; c.addEventListener("transitionend", () => done(), { once: true }); setTimeout(done, 1500); }));
      await page.mouse.move(ctlBox.left + ctlBox.width / 2, ctlBox.top + ctlBox.height / 2);
      await hoverP;
      await frames(page, 2);
      const hoveredCtl = await under(page);
      assert.equal(hoveredCtl.imgs[2].controlBorder, await tokenColour(page, "--accent"), "the pointer over the web control: its border is the family's accent, the rest colour scoped off :hover");
      assert.notEqual(hoveredCtl.imgs[2].controlBorder, big.controlBorder, "and not the rest colour it wore before the pointer (" + big.controlBorder + ")");
      // the hover states inside a dead link, as painted (the painted-contrast ask of 2026-09-23): the pointer over the captioned
      // picture reveals its control, over the picture under the floor the mark stands, and on the revealed control its border turns
      // the family's accent over the hover wash, each inside the anchor; a click opens the tab from each (the link-shapes case), so
      // each paints at 3:1 in both themes, every failing read collected and asserted once at the end (FAILS BEFORE, 61d69cba1: the
      // anchor's opacity 0.7 over the whole dress, 2.82:1 light for the reveal and the mark, 2.58:1 light by pixels for the accent
      // border, 2.55:1 composed); the control held pressed there, whose release opens the tab (FAILS BEFORE the sheets' press rule);
      // and the control under a keyboard focus inside the dead link, whose Enter opens the tab too, read by pixels with the focus ring
      // 2px off its border (FAILS BEFORE the sheets' focus rule: the ring covers the border row)
      const fails: string[] = [];
      const imgAt = (alt: string) => page.evaluate((alt: string) => { const i = Array.from(document.querySelectorAll(".fileview-md img")).find((x) => x.getAttribute("alt") === alt) as HTMLElement; i.scrollIntoView({ block: "center" }); const r = i.getBoundingClientRect(); return { x: r.left + r.width * 0.3, y: r.top + r.height * 0.7 }; }, alt);
      const deadCtl = "deadcap";   // the captioned dead link's picture, whose control stands right after it inside the anchor
      const push = (theme: string, what: string, p: Painted) => { const worst = p.at ? " (the worst read: " + p.at + ")" : ""; t.diagnostic("painted, " + theme + " theme: " + what + " " + p.dash + " over " + p.ground + ", " + p.ratio.toFixed(3) + ":1" + worst + " (opacities on the way: " + (p.opacities.join(", ") || "none") + ")"); if (p.ratio < 3) fails.push(theme + " theme: " + what + " paints " + p.dash + " over " + p.ground + ", " + p.ratio.toFixed(3) + ":1, under the 3:1 floor" + worst + " (opacities on the way: " + (p.opacities.join(", ") || "none") + ")"); };
      for (const theme of ["dark", "light"]) {
        await page.mouse.move(5, 5);
        await frames(page, 2);
        if (theme === "light") await page.evaluate(() => new Promise<void>((done) => { const c = document.querySelectorAll(".fileview-md img")[2].nextElementSibling as HTMLElement; c.addEventListener("transitionend", () => done(), { once: true }); setTimeout(done, 1500); document.body.classList.add("theme-light"); }));
        // the control revealed by the pointer over its picture: the reveal read off the control's own computed opacity before the paint
        assert.ok(await page.evaluate((alt: string) => { const n = Array.from(document.querySelectorAll(".fileview-md img")).find((x) => x.getAttribute("alt") === alt)!.nextElementSibling; return !!n && n.hasAttribute("data-fv-figopen"); }, deadCtl), "the captioned dead link's picture has its control right after it, inside the anchor");
        const q = await imgAt("deadcap");
        await frames(page, 2);
        await page.mouse.move(q.x, q.y);
        await page.waitForFunction((alt: string) => getComputedStyle((Array.from(document.querySelectorAll(".fileview-md img")).find((x) => x.getAttribute("alt") === alt)!.nextElementSibling as HTMLElement)).opacity === "1", deadCtl, { timeout: 5000 });
        await frames(page, 2);
        push(theme, "the control revealed by the pointer over its picture inside a dead link", await paintedRatio(page, "deadcap", "control", "hover"));
        // the accent border: the pointer on the revealed control, its border and hover wash eased in (.fileview-btn's 0.12 s, bounded)
        const c = await page.evaluate((alt: string) => { const r = (Array.from(document.querySelectorAll(".fileview-md img")).find((x) => x.getAttribute("alt") === alt)!.nextElementSibling as HTMLElement).getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; }, deadCtl);
        const eased = page.evaluate((alt: string) => new Promise<void>((done) => { (Array.from(document.querySelectorAll(".fileview-md img")).find((x) => x.getAttribute("alt") === alt)!.nextElementSibling as HTMLElement).addEventListener("transitionend", () => done(), { once: true }); setTimeout(done, 1500); }), deadCtl);
        await page.mouse.move(c.x, c.y);
        await eased;
        await frames(page, 2);
        assert.equal(await page.evaluate((alt: string) => getComputedStyle((Array.from(document.querySelectorAll(".fileview-md img")).find((x) => x.getAttribute("alt") === alt)!.nextElementSibling as HTMLElement)).borderTopColor, deadCtl), await tokenColour(page, "--accent"), theme + " theme: the pointer on the control inside the dead link: its border is the family's accent (the state read next)");
        push(theme, "the accent border with the pointer on the control inside a dead link, against the hover wash", await paintedRatio(page, "deadcap", "control", "hover"));
        // the press: the control held pressed inside the dead link, read by pixels while held, then the release, which opens the tab
        // (pressedLegible; FAILS BEFORE the sheets' press rule: the family's press cue scaled the control to 0.96 and its 1px line
        // spread over two pixel rows)
        await pressedLegible(page, deadCtl, theme + " theme, the pointer on the control inside a dead link", fails, (m) => t.diagnostic(m));
        // the mark on hover
        await page.mouse.move(5, 5);
        const m = await imgAt("deadbuild");
        await frames(page, 2);
        await page.mouse.move(m.x, m.y);
        await page.waitForFunction(() => getComputedStyle(Array.from(document.querySelectorAll(".fileview-md img")).find((x) => x.getAttribute("alt") === "deadbuild")!).outlineStyle === "dashed", null, { timeout: 5000 });
        await frames(page, 2);
        push(theme, "the mark on hover inside a dead link", await paintedRatio(page, "deadbuild", "mark", "hover"));
        // the mark on hover on the grounds its line read against before its ring of var(--bg), each by the worst dash-to-ring read (the
        // file review's round 14, correctness-2 with extra5-1 and extra5-2; FAILS BEFORE the ring: the dark highlight at 2.40:1, its
        // tint on both sides of the dashes), and the ring on hover covering no neighbouring ink (ringCoversNoNeighbour)
        for (const [alt, ground] of RING_GROUNDS) {
          await page.mouse.move(5, 5);
          const g = await imgAt(alt);
          await frames(page, 2);
          await page.mouse.move(g.x, g.y);
          await page.waitForFunction((alt: string) => getComputedStyle(Array.from(document.querySelectorAll(".fileview-md img")).find((x) => x.getAttribute("alt") === alt)!).outlineStyle === "dashed", alt, { timeout: 5000 });
          await frames(page, 2);
          push(theme, "the mark on hover " + ground, await paintedRatio(page, alt, "mark", "hover"));
        }
        await ringCoversNoNeighbour(page, theme + " theme, on hover on a fine pointer", fails, (m) => t.diagnostic(m), true);
        // the control under a keyboard focus inside the dead link, the pointer off every picture so the focus alone reveals it: a
        // read that finds no dress on the line (the focus ring over it) is collected as a failure with the rest
        await page.mouse.move(5, 5);
        await frames(page, 2);
        await page.keyboard.press("Shift");   // a key pressed last, so the focus below is a keyboard's (Chromium's :focus-visible heuristic for a script focus)
        assert.equal(await page.evaluate((alt: string) => { const c = Array.from(document.querySelectorAll(".fileview-md img")).find((x) => x.getAttribute("alt") === alt)!.nextElementSibling as HTMLElement; c.focus({ preventScroll: true }); return c.matches(":focus-visible"); }, deadCtl), true, theme + " theme: the control inside the dead link holds a keyboard focus (:focus-visible)");
        await page.waitForFunction((alt: string) => getComputedStyle((Array.from(document.querySelectorAll(".fileview-md img")).find((x) => x.getAttribute("alt") === alt)!.nextElementSibling as HTMLElement)).opacity === "1", deadCtl, { timeout: 5000 });
        const focusRead = await paintedRatio(page, "deadcap", "control").catch((e: Error) => e);
        if (focusRead instanceof Error) fails.push(theme + " theme: the control under a keyboard focus inside a dead link: no dress on its line as painted (" + focusRead.message.split("\n")[0] + ")");
        else push(theme, "the control under a keyboard focus inside a dead link", focusRead);
        // and pressed from that focus by the Space key, the pointer off it, so the pressed control shows the token's border and not
        // the accent: read while Space is held, then released, which opens the tab (pressedLegible; FAILS BEFORE the sheets' press rule)
        await pressedLegible(page, deadCtl, theme + " theme, the Space key on the control under a keyboard focus inside a dead link", fails, (m) => t.diagnostic(m), "Space");
        await page.evaluate(() => (document.activeElement as HTMLElement).blur());
      }
      await page.mouse.move(5, 5);
      await page.evaluate(() => document.body.classList.remove("theme-light"));
      assert.deepEqual(fails, [], "every state a click or a key opens the tab from inside a dead link, the press held included, and the mark on hover on the grounds of a highlight, a table header, an even row and a callout, on a fine pointer, paint the dress at 3:1, and the ring on hover covers no neighbouring ink (a property pin read off the page):\n" + fails.join("\n"));
      assert.deepEqual(errors, [], "no page errors");
      await page.close();
    });
  } finally { await second.close(); }
});
test("in a browser, under CDP touch emulation (hover none, a coarse pointer) enabled after the load and before any read, the pointer over no picture until the case's closing press: the remote picture under the floor wears the outbound mark AT REST, so the tap's open is visible before it happens, the mark's colour the control's border colour in the dark theme and in the light one, and the loaded picture beside it keeps its control visible at rest with no mark of its own; the tap opens the tab at the address (the popup and the second server's log, never a window.open stub) and the viewer stays (the file review's round 12, fresh-1: the at-rest read in a case of its own, so the leg's red over the undressed picture reaches it, where the case above, the hover read first, stops at the hover); last, a mouse press held on the web control inside the captioned dead link paints its line at 3:1 in both themes and its release opens the tab (the painted-contrast ask of 2026-09-23)", { timeout: 240000 }, async (t) => {
  const served: string[] = [];
  const second = await secondServer(served, TINY_SIZES);
  try {
    await inBrowser(t, async (browser) => {
      const { page, errors } = await openTiny(browser, second);
      const cdp = await page.context().newCDPSession(page);
      await cdp.send("Emulation.setTouchEmulationEnabled", { enabled: true, maxTouchPoints: 1 });
      await frames(page, 2);
      const touch = await under(page);
      assert.deepEqual([touch.hoverNone, touch.coarse], [true, true], "hover none and a coarse pointer under the emulation");
      assert.deepEqual(touch.imgs.map((x) => x.alt), TINY_ALTS, "the tiny report's figures");
      assert.deepEqual([touch.imgs[1].control, touch.imgs[1].title], [false, WEB_LINE(WEB + "/tiny.svg")], "the badge: no control under the floor, the address in its title");
      // FAILS BEFORE: outline none, the tap's open shown nowhere
      assert.deepEqual([touch.imgs[1].mark, touch.imgs[1].outline, touch.imgs[1].outlineWidth], [true, "dashed", "1px"], "at rest on a coarse pointer, no pointer ever over it, the badge wears the mark: the open is visible before the tap");
      assert.equal(touch.imgs[2].outline, "none", "the picture with a control: no mark on the picture");
      // the painted dead-link state and its gesture in one case: a tap on the picture under the floor inside the dead link opens the
      // tab at its address, since a dead link owns no click (file-view.ts FIGURE_LINK_SET), and the viewer stays; so the mark read
      // below inside the dead link is a state a tap opens from. First, so a click taken from the dead link reds here on the gesture;
      // the body's scroll is restored after, since the tap on the badge below uses the centre read before any scroll
      const top0 = await page.evaluate(() => (document.querySelector(".fileview-body") as HTMLElement).scrollTop);
      const dt = await page.evaluate(() => { const i = Array.from(document.querySelectorAll(".fileview-md img")).find((x) => x.getAttribute("alt") === "deadbuild")!; i.scrollIntoView({ block: "center" }); const r = i.getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2, dead: !!i.closest("a.fv-dead") && !i.closest("a[href]") }; });
      assert.equal(dt.dead, true, "the picture stands inside an href-less dead link");
      await frames(page, 2);
      const beforeDead = served.filter((s) => s.endsWith("/deadtiny.svg")).length;
      const deadP = page.context().waitForEvent("page", { timeout: 10000 }).catch(() => null);
      await cdp.send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [{ x: dt.x, y: dt.y }] });
      await cdp.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] });
      const deadPopup = await deadP;
      assert.ok(deadPopup, "the tap on the picture under the floor inside the dead link opens a tab (none opened in 10 s)");
      await deadPopup.waitForLoadState().catch(() => null);
      assert.equal(deadPopup.url(), WEB + "/deadtiny.svg", "the tap inside the dead link opens a tab at the picture's address (the popup's URL)");
      assert.ok(served.filter((s) => s.endsWith("/deadtiny.svg")).length > beforeDead, "the second server answered that tab's own request: " + JSON.stringify(served));
      assert.equal(await base(page), "report.md", "the viewer stays on the report");
      await deadPopup.close();
      await page.evaluate((y: number) => { (document.querySelector(".fileview-body") as HTMLElement).scrollTop = y; }, top0);
      await frames(page, 2);
      // one colour token for the two dresses (the owner's call with the ruling): the mark's outline colour is the control's border
      // colour, in the dark theme and, with body.theme-light, in the light one; the two themes resolve it apart, so the read is not one
      // value twice; and that colour, composited over the first opaque ground, clears 3:1 in each theme (oneLegibleColour)
      await oneLegibleColour(page, touch, "dark");
      // and as PAINTED, through every opacity on the way (paintedRatio), the dresses at rest (DRESSES), every failing read collected and
      // asserted once at the case's end, before the control's opacity value is read, so a run over the old sheet shows every clause's
      // red and not a spelling first (the painted-contrast ask of 2026-09-23)
      const fails: string[] = [];
      const dark = await paintedLegible(page, "dark theme", fails, (m) => t.diagnostic(m));
      // the ground ruling's premise, executed: the pixel above the web control's top border is the picture's own fill (the second
      // server's #333) in both themes, so the line's outer side over a picture is the author's pixels, and the read above is against
      // the control's own background, the ground the sheet controls (read in both themes: a pixel the border's edge smoothed can
      // match the fill in one theme by chance, never in both)
      assert.equal(dark.get("big")!.outer, "rgb(51, 51, 51)", "dark theme: the pixel above the web control's top border is the picture's own fill");
      // the ring at rest covers no neighbouring ink (the file review's round 14, correctness-2 with extra5-1 and extra5-2)
      await ringCoversNoNeighbour(page, "dark theme, at rest under touch emulation", fails, (m) => t.diagnostic(m));
      // the theme flipped on the body; the control's border colour TRANSITIONS to the light value (.fileview-btn's 0.12 s
      // border-color ease) while the outline has no transition, so the light read waits for the control's transitionend (bounded)
      await page.evaluate(() => new Promise<void>((done) => { const c = document.querySelectorAll(".fileview-md img")[2].nextElementSibling as HTMLElement; c.addEventListener("transitionend", () => done(), { once: true }); setTimeout(done, 1500); document.body.classList.add("theme-light"); }));
      await frames(page, 2);
      const light = await under(page);
      await oneLegibleColour(page, light, "light");
      const lightRead = await paintedLegible(page, "light theme", fails, (m) => t.diagnostic(m));
      assert.equal(lightRead.get("big")!.outer, "rgb(51, 51, 51)", "light theme: the pixel above the web control's top border is the picture's own fill");
      await ringCoversNoNeighbour(page, "light theme, at rest under touch emulation", fails, (m) => t.diagnostic(m));
      assert.notEqual(light.imgs[1].outlineColor, touch.imgs[1].outlineColor, "the two themes resolve the token apart: " + light.imgs[1].outlineColor + " against " + touch.imgs[1].outlineColor);
      assert.deepEqual([light.imgs[1].mark, light.imgs[1].outline], [true, "dashed"], "the mark stands in the light theme too");
      await page.evaluate(() => document.body.classList.remove("theme-light"));
      await frames(page, 2);
      // the VS Code bound, by pixels (the painted-contrast ask of 2026-09-23): in the dark theme the ground is the editor's, and the
      // dresses clear 3:1 on a neutral editor ground up to #404040 and fall under at #414141, and on a light one from #efefef and
      // not at #eeeeee, the bound the sheets' comment states (theme-parity.test.ts composes the same bound from the declared
      // opacities); at 61d69cba1 the control at rest fell under 3:1 from #303030 and the control inside a captioned dead link on
      // every grey. Read here alone: the touchscreen laptop's case reads byte-identical pixels at rest. Before the mark's ring of
      // var(--bg) the mark on the tinted grounds of RING_GROUNDS read under the bound it states, and past it at #eeeeee in a table
      // (the file review's round 14, correctness-2 with extra5-2)
      for (const [grey, clears] of [["#404040", true], ["#414141", false], ["#efefef", true], ["#eeeeee", false]] as Array<[string, boolean]>) {
        await editorGround(page, grey);
        await paintedLegible(page, "dark theme on a VS Code editor ground " + grey, fails, (m) => t.diagnostic(m), clears);
      }
      await editorGround(page, null);
      const before2 = served.filter((s) => s.endsWith("/tiny.svg")).length;
      const popupP = page.context().waitForEvent("page", { timeout: 10000 });
      await cdp.send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [{ x: touch.centre.x, y: touch.centre.y }] });
      await cdp.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] });
      const popup = await popupP;
      await popup.waitForLoadState().catch(() => null);
      assert.equal(popup.url(), WEB + "/tiny.svg", "the tap opens a tab at the picture's address (the popup's URL)");
      assert.ok(served.filter((s) => s.endsWith("/tiny.svg")).length > before2, "the second server answered the tab's own request: " + JSON.stringify(served));
      assert.equal(await base(page), "report.md", "the viewer stays on the report");
      await popup.close();
      // the press, last, so no pointer hovered any picture before the reads above: the web control inside the captioned dead link held
      // pressed by a mouse press, read by pixels while held, then released, which opens the tab (pressedLegible), in the dark theme and
      // then the light one (FAILS BEFORE the sheets' press rule: the family's press cue scaled the control to 0.96 and its 1px line
      // spread over two pixel rows); the theme back to dark after, each flip awaited on the big control's transitionend (bounded)
      await pressedLegible(page, "deadcap", "dark theme, a mouse press under touch emulation", fails, (m) => t.diagnostic(m));
      await page.evaluate(() => new Promise<void>((done) => { const c = document.querySelectorAll(".fileview-md img")[2].nextElementSibling as HTMLElement; c.addEventListener("transitionend", () => done(), { once: true }); setTimeout(done, 1500); document.body.classList.add("theme-light"); }));
      await frames(page, 2);
      await pressedLegible(page, "deadcap", "light theme, a mouse press under touch emulation", fails, (m) => t.diagnostic(m));
      await page.evaluate(() => new Promise<void>((done) => { const c = document.querySelectorAll(".fileview-md img")[2].nextElementSibling as HTMLElement; c.addEventListener("transitionend", () => done(), { once: true }); setTimeout(done, 1500); document.body.classList.remove("theme-light"); }));
      await frames(page, 2);
      assert.deepEqual(fails, [], "every state a tap or a press opens the tab from paints the dress at 3:1, the VS Code bound is exact, and the ring at rest covers no neighbouring ink (a property pin read off the page):\n" + fails.join("\n"));
      // the web control at rest at full opacity (a local one keeps 0.8), read after the painted reads so their red comes first
      assert.equal(touch.imgs[2].controlOpacity, "1", "the web control visible at rest at full opacity");
      // the dead link's words, a residual the sheets' comment states and this its witness: the rule dims the anchor's colour, so the
      // caption's words that take it are dimmed (the colour carries the 70 percent), while its bold words and inline code, which the
      // sheet colours itself, keep their own ink with no opacity under 1 on the way; a change that dims them too reds here, and the
      // disclosure moves with it. Read after the painted reads, so their red comes first over the old sheet, whose 0.7 opacity dimmed
      // the words and left their colour whole
      const caption = await page.evaluate(() => {
        const a = Array.from(document.querySelectorAll(".fileview-md img")).find((x) => x.getAttribute("alt") === "deadcap")!.closest("a")!;
        const chain = (e: Element | null): string[] => { const o: string[] = []; for (; e; e = e.parentElement) { const v = getComputedStyle(e).opacity; if (v !== "1") o.push(e.localName + " " + v); } return o; };
        const strong = a.querySelector("strong"), code = a.querySelector("code");
        return { dead: a.classList.contains("fv-dead") && !a.hasAttribute("href"), anchor: getComputedStyle(a).color, strong: strong && getComputedStyle(strong).color, code: code && getComputedStyle(code).color, opac: [chain(strong), chain(code)] };
      });
      assert.equal(caption.dead, true, "the captioned picture stands inside an href-less dead link");
      assert.match(caption.anchor, /\/ 0\.7\)$/, "the dead link's own words take its colour dimmed to 70 percent (" + caption.anchor + ")");
      assert.deepEqual([caption.strong, caption.code, caption.opac], [await tokenColour(page, "--fg"), await tokenColour(page, "--code-fg"), [[], []]], "the caption's bold words and inline code keep the sheet's own ink, with no opacity under 1 on the way");
      assert.deepEqual(errors, [], "no page errors");
      await page.close();
    });
  } finally { await second.close(); }
});

// THE TOUCHSCREEN LAPTOP (the file review's round 13, extra7-2): `hover` and `pointer` describe the PRIMARY pointing device, and a
// laptop with a trackpad and a touchscreen reports hover: hover and pointer: fine, so an at-rest rule keyed on (hover: none) alone
// showed neither dress there while a finger's tap opened the tab. CDP's touch emulation cannot build that laptop (it flips the primary
// pointer and the primary hover together), so Chromium is launched with Blink's own device settings, tab-hide-browser.test.ts's
// precedent: available pointer types coarse|fine (2|4) with the primary fine (4), available hover types none|hover (1|2) with the
// primary hover (2). The context is asserted before the dress, so a Chromium that stopped honouring the flag fails on the context.
const LAPTOP = "--blink-settings=availablePointerTypes=6,primaryPointerType=4,availableHoverTypes=3,primaryHoverType=2";
const pointing = (page: any): Promise<{ hoverNone: boolean; hoverHover: boolean; pointerFine: boolean; anyCoarse: boolean }> => page.evaluate(() => { const m = (q: string) => matchMedia(q).matches; return { hoverNone: m("(hover: none)"), hoverHover: m("(hover: hover)"), pointerFine: m("(pointer: fine)"), anyCoarse: m("(any-pointer: coarse)") }; });
test("in Chromium launched as a trackpad-plus-touchscreen laptop (hover: hover, pointer: fine, any-pointer: coarse), the pointer over no picture until the case's closing press: the remote picture under the floor wears the outbound mark AT REST and the loaded picture's control stands visible at rest, one legible colour in both themes, where a rule keyed on (hover: none) alone dressed neither; a finger's tap opens the tab at the address and the viewer stays (the file review's round 13, extra7-2: the hybrid twin of the touch case above); last, the trackpad's press held on the web control inside the captioned dead link paints its line at 3:1 in both themes and its release opens the tab (the painted-contrast ask of 2026-09-23)", { timeout: 240000 }, async (t) => {
  const served: string[] = [];
  const second = await secondServer(served, TINY_SIZES);
  try {
    await inBrowser(t, async (browser) => {
      const { page, errors } = await openTiny(browser, second);
      const laptop = await pointing(page);
      assert.deepEqual([laptop.hoverNone, laptop.hoverHover, laptop.pointerFine, laptop.anyCoarse], [false, true, true, true], "the laptop: the primary pointer fine and hovering, a coarse pointer present (the context, asserted before the dress)");
      const rest = await under(page);
      assert.deepEqual(rest.imgs.map((x) => x.alt), TINY_ALTS, "the tiny report's figures");
      assert.deepEqual([rest.imgs[1].control, rest.imgs[1].title], [false, WEB_LINE(WEB + "/tiny.svg")], "the badge: no control under the floor, the address in its title");
      // FAILS BEFORE: outline none and the control at opacity 0, (hover: none) false on this laptop
      assert.deepEqual([rest.imgs[1].mark, rest.imgs[1].outline, rest.imgs[1].outlineWidth], [true, "dashed", "1px"], "at rest on the laptop, no pointer ever over it, the badge wears the mark: the finger's open is visible before the tap");
      assert.equal(rest.imgs[2].outline, "none", "the picture with a control: no mark on the picture");
      await oneLegibleColour(page, rest, "dark");
      // the dresses at rest as painted (DRESSES), collected and asserted at the case's end, before the opacity values (the touch case's
      // reads, here on the laptop, where the at-rest rules key on the coarse pointer beside the hovering one)
      const fails: string[] = [];
      await paintedLegible(page, "dark theme", fails, (m) => t.diagnostic(m));
      await page.evaluate(() => new Promise<void>((done) => { const c = document.querySelectorAll(".fileview-md img")[2].nextElementSibling as HTMLElement; c.addEventListener("transitionend", () => done(), { once: true }); setTimeout(done, 1500); document.body.classList.add("theme-light"); }));
      await frames(page, 2);
      const light = await under(page);
      await oneLegibleColour(page, light, "light");
      await paintedLegible(page, "light theme", fails, (m) => t.diagnostic(m));
      assert.deepEqual([light.imgs[1].mark, light.imgs[1].outline], [true, "dashed"], "both dresses stand in the light theme too");
      await page.evaluate(() => document.body.classList.remove("theme-light"));
      await frames(page, 2);
      const before2 = served.filter((s) => s.endsWith("/tiny.svg")).length;
      const cdp = await page.context().newCDPSession(page);
      const popupP = page.context().waitForEvent("page", { timeout: 10000 });
      await cdp.send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [{ x: rest.centre.x, y: rest.centre.y }] });
      await cdp.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] });
      const popup = await popupP;
      await popup.waitForLoadState().catch(() => null);
      assert.equal(popup.url(), WEB + "/tiny.svg", "the finger's tap opens a tab at the picture's address (the popup's URL)");
      assert.ok(served.filter((s) => s.endsWith("/tiny.svg")).length > before2, "the second server answered the tab's own request: " + JSON.stringify(served));
      assert.equal(await base(page), "report.md", "the viewer stays on the report");
      await popup.close();
      // the press, last, as in the touch case: the web control inside the captioned dead link held pressed by the trackpad's press, read
      // by pixels while held, then released, which opens the tab (pressedLegible), in both themes (FAILS BEFORE the sheets' press rule)
      await pressedLegible(page, "deadcap", "dark theme, the trackpad's press", fails, (m) => t.diagnostic(m));
      await page.evaluate(() => new Promise<void>((done) => { const c = document.querySelectorAll(".fileview-md img")[2].nextElementSibling as HTMLElement; c.addEventListener("transitionend", () => done(), { once: true }); setTimeout(done, 1500); document.body.classList.add("theme-light"); }));
      await frames(page, 2);
      await pressedLegible(page, "deadcap", "light theme, the trackpad's press", fails, (m) => t.diagnostic(m));
      await page.evaluate(() => new Promise<void>((done) => { const c = document.querySelectorAll(".fileview-md img")[2].nextElementSibling as HTMLElement; c.addEventListener("transitionend", () => done(), { once: true }); setTimeout(done, 1500); document.body.classList.remove("theme-light"); }));
      await frames(page, 2);
      assert.deepEqual(fails, [], "every state a finger's tap or a press opens the tab from paints the dress at 3:1:\n" + fails.join("\n"));
      assert.deepEqual([rest.imgs[2].controlOpacity, light.imgs[2].controlOpacity], ["1", "1"], "the web control visible at rest at full opacity in both themes (a local one keeps 0.8), read after the painted reads so their red comes first");
      assert.deepEqual(errors, [], "no page errors");
      await page.close();
    }, { args: [LAPTOP] });
  } finally { await second.close(); }
});

// ── the ring's two stated bounds ──────────────────────────────────────────────────────────────────────────────────────────────
// (the file review's round 14, correctness-2 with extra5-1 and extra5-2) The margin is the ring's width, so it keeps the ring off
// every pixel whose centre lies in a neighbour's own box and leaves no pixel of slack past that box. Two things stay outside it, the
// bounds the sheets' comment on the mark states, each recorded here as it stands, so a change that closes or widens either turns
// this case red and the sentence moves with it: a glyph whose ink reaches past its own box toward the picture (here an italic run's
// last letter) loses that ink to the ring, where without the margin the picture itself stood; and text painted after the picture can
// put its edge in the ring's outer pixel (here the line a note callout wraps beside a left-floated picture, on the Files pane, where
// the dash's outer side reads that edge under 3:1). The neighbour pin's scenes are glyphs whose ink stays inside their box.
const BOUND_WORDS = "Tall words wrap around the floated picture here and deep gjpqy words ";
const BOUND_TEXT = "# Report\n\n" + PARA(1) + "\n\nItalic *ffff*![ngi](" + WEB + "/ngi.svg) glued\n\n"
  + "> [!note]\n> " + '<img src="' + WEB + '/cfloat.svg" alt="cfloat" align="left">' + "jTW " + BOUND_WORDS.repeat(5) + "\n\n" + PARA(2) + "\n";
type Edges = { left: number; top: number; right: number; bottom: number };
/** The ring over the glyph glued before the picture `alt` (the last letter of the text before it, inside an element or not), read off
 *  three screenshots of one clip: as painted (A), with every mark's box-shadow overridden to none (B, the page without the ring), and
 *  with the ring off and the text of the picture's own block transparent (C, the page without that text's ink). A pixel holds the
 *  text's ink where B and C differ, and the ring covers it where A and B differ there. Returns the covered pixels, how many of them
 *  have their centre inside the glyph's own box (the last letter's range rect), the pixels the ring changed at all, and the first few
 *  covered pixels for the message. Guards: the glyph is found, the picture wears the mark's dashed outline at rest, and the overrides
 *  take the ring off (the computed box-shadow none) and move nothing. */
async function ringOverGlyph(page: any, alt: string): Promise<{ covered: number; inBox: number; changed: number; glyph: Edges; seen: string[] }> {
  await page.mouse.move(5, 5);
  const layout = (scroll: boolean): Promise<{ img: Edges; glyph: Edges | null; outline: string; shadow: string }> => page.evaluate(([alt, scroll]: [string, boolean]) => {
    const img = Array.from(document.querySelectorAll(".fileview-md img")).find((x) => x.getAttribute("alt") === alt) as HTMLElement;
    if (scroll) img.scrollIntoView({ block: "center" });
    const box = (r: DOMRect) => ({ left: r.left, top: r.top, right: r.right, bottom: r.bottom });
    let n: Node | null = img.previousSibling;
    while (n && n.nodeType === 1) n = n.lastChild;
    let glyph = null;
    if (n && n.nodeType === 3 && (n as Text).length) { const r = document.createRange(); r.setStart(n, (n as Text).length - 1); r.setEnd(n, (n as Text).length); glyph = box(r.getBoundingClientRect()); }
    const cs = getComputedStyle(img);
    return { img: box(img.getBoundingClientRect()), glyph, outline: cs.outlineStyle, shadow: cs.boxShadow };
  }, [alt, scroll]);
  await layout(true);
  await frames(page, 2);
  const lay = await layout(false);
  assert.ok(lay.glyph, alt + ": the glyph glued before the picture is found");
  assert.equal(lay.outline, "dashed", alt + ": the picture wears the mark's outline at rest");
  const g = lay.glyph as Edges;
  const cx = Math.max(0, Math.floor(Math.min(g.left, lay.img.left) - 12)), cy = Math.max(0, Math.floor(Math.min(g.top, lay.img.top) - 12));
  const cw = Math.ceil(lay.img.right + 12) - cx, ch = Math.ceil(Math.max(g.bottom, lay.img.bottom) + 12) - cy;
  const shot = async () => decodePng(await page.screenshot({ clip: { x: cx, y: cy, width: cw, height: ch } }));
  const A = await shot();
  await page.evaluate((alt: string) => {
    const img = Array.from(document.querySelectorAll(".fileview-md img")).find((x) => x.getAttribute("alt") === alt) as HTMLElement;
    img.parentElement!.setAttribute("data-bound-line", "");
    const st = document.createElement("style"); st.id = "bound-noring"; st.textContent = ".fileview-md img[data-fv-figweb] { box-shadow: none !important; }"; document.head.appendChild(st);
  }, alt);
  await frames(page, 3);
  const B = await shot();
  const noRing = await layout(false);
  await page.evaluate(() => { const st = document.createElement("style"); st.id = "bound-noink"; st.textContent = "[data-bound-line], [data-bound-line] * { color: transparent !important; -webkit-text-fill-color: transparent !important; text-decoration-color: transparent !important; }"; document.head.appendChild(st); });
  await frames(page, 3);
  const C = await shot();
  const noInk = await layout(false);
  await page.evaluate(() => { document.getElementById("bound-noink")!.remove(); document.getElementById("bound-noring")!.remove(); document.querySelector("[data-bound-line]")!.removeAttribute("data-bound-line"); });
  await frames(page, 2);
  assert.deepEqual([noRing.img, noRing.shadow, noInk.img], [lay.img, "none", lay.img], alt + ": the overrides take the ring off (the picture's computed box-shadow none under them) and move nothing");
  const px = (png: { width: number; bpp: number; data: Buffer }, x: number, y: number) => { const k = ((y - cy) * png.width + (x - cx)) * png.bpp; return [png.data[k], png.data[k + 1], png.data[k + 2]]; };
  const same = (a: number[], b: number[]) => a[0] === b[0] && a[1] === b[1] && a[2] === b[2];
  let covered = 0, inBox = 0, changed = 0;
  const seen: string[] = [];
  for (let y = cy; y < cy + ch; y++) for (let x = cx; x < cx + cw; x++) {
    const a = px(A, x, y), b = px(B, x, y), c = px(C, x, y);
    if (same(a, b)) continue;
    changed++;
    if (same(b, c)) continue;
    covered++;
    if (x + 0.5 > g.left && x + 0.5 < g.right && y + 0.5 > g.top && y + 0.5 < g.bottom) inBox++;
    if (seen.length < 4) seen.push((x - Math.floor(lay.img.left)) + "," + (y - Math.floor(lay.img.top)) + " rgb(" + b.join(", ") + ") to rgb(" + a.join(", ") + ")");
  }
  return { covered, inBox, changed, glyph: g, seen };
}
test("in a browser, under CDP touch emulation on the Files pane, the ring's two stated bounds, each a bound-recording read off the page (a red means a bound moved, closed or widened, and the sheets' sentence on it moves with it): the ink an italic run's last letter glued before a remote picture under the floor paints past its own box is covered by the ring while no pixel whose centre lies inside that box changes, and the edge of the text a note callout wraps beside a left-floated one paints in the ring's outer pixel, where the dash's outer side reads under 3:1 in both themes (the file review's round 14, correctness-2 with extra5-1 and extra5-2: the margin is the ring's width, so it keeps the ring off a neighbour's box and leaves no pixel of slack past it)", { timeout: 240000 }, async (t) => {
  const second = await secondServer([], { "/ngi.svg": [20, 20], "/cfloat.svg": [20, 20] });
  try {
    await inBrowser(t, async (browser) => {
      const before = async (pg: any): Promise<void> => {
        await pg.context().route((u: URL) => u.href.startsWith(WEB + "/"), async (route: any) => {
          const a = await fromSecond(second.port, new URL(route.request().url()).pathname);
          return route.fulfill({ status: a.status, contentType: a.type, body: a.body });
        });
      };
      const { page, errors } = await openViewer(browser, "pane", 900, 600, { docs: { [REPORT]: BOUND_TEXT }, before });
      await page.click('[data-act="fv-load"]');
      await page.waitForFunction(() => { const imgs = Array.from(document.querySelectorAll(".fileview-md img")) as HTMLImageElement[]; return imgs.length === 2 && imgs.every((i) => i.complete && i.naturalWidth > 0 && i.hasAttribute("data-fv-figweb")); }, null, { timeout: 10000 });
      const cdp = await page.context().newCDPSession(page);
      await cdp.send("Emulation.setTouchEmulationEnabled", { enabled: true, maxTouchPoints: 1 });
      await frames(page, 3);
      const float = await page.evaluate(() => getComputedStyle(Array.from(document.querySelectorAll(".fileview-md img")).find((x) => x.getAttribute("alt") === "cfloat")!).float);
      assert.equal(float, "left", "the callout's picture is floated left (the scene)");
      const fails: string[] = [];
      for (const theme of ["dark", "light"] as const) {
        await page.evaluate((light: boolean) => document.body.classList.toggle("theme-light", light), theme === "light");
        await frames(page, 3);
        const o = await ringOverGlyph(page, "ngi");
        const read = theme + " theme: the italic letter before the picture (its box " + [o.glyph.left, o.glyph.top, o.glyph.right, o.glyph.bottom].map((v) => v.toFixed(2)).join(", ") + "): " + o.covered + " ink pixels covered by the ring, " + o.inBox + " of them with the centre inside the box, " + o.changed + " pixels of the clip changed by it (" + o.seen.join("; ") + ")";
        t.diagnostic("bound, " + read);
        if (o.inBox > 0) fails.push(read + ": the ring covers a pixel inside the glyph's own box, which the margin keeps it off");
        if (o.covered === 0) fails.push(read + ": the ring covers none of the ink past the box, so the first bound moved and the sheets' sentence on it moves with it");
        const f = await paintedRatio(page, "cfloat", "mark");
        const fr = theme + " theme: the left-floated picture in the note callout paints " + f.dash + " over " + f.ground + ", " + f.ratio.toFixed(3) + ":1 (the worst read: " + f.at + ")";
        t.diagnostic("bound, " + fr);
        if (!(f.ratio < 3 && /^right outer/.test(f.at || ""))) fails.push(fr + ": the dash's outer side toward the wrapped text reads 3:1 or better, or the worst read stands elsewhere, so the second bound moved and the sheets' sentence on it moves with it");
      }
      await page.evaluate(() => document.body.classList.remove("theme-light"));
      assert.deepEqual(fails, [], "the ring's two bounds stand as the sheets' comment states them (a bound-recording read off the page):\n" + fails.join("\n"));
      assert.deepEqual(errors, [], "no page errors");
      await page.close();
    });
  } finally { await second.close(); }
});

// ── the web control's focus: no mouse press focuses it, any focus it holds is painted, and a key opens it only in view ─────────
// (the file review's round 14, ui-1 with extra9-1: a mouse press on the web control focused it, a click, a press dragged off the
// control and released, which opens nothing, and a right or a middle press alike; on a fine pointer the focused control went
// transparent once the pointer left, since the sheets revealed it for :focus-visible alone, and a later Enter, or a Space with the
// control wheeled out of view, opened the credentialed tab again with nothing shown first; and a keyboard focus scrolled out of
// view by PageDown, or by a table that scrolls on its own, opened it on Space.) The three requirements and their pins: no mouse
// press focuses the web control, pins (a), (b) and (c) and the other-button pin; any focus it holds is painted, pin (e), with (c)'s
// second branch; Enter or Space opens it only while it is in view at the key, the viewport and every ancestor that clips on that
// axis, pins (d) and (f), each by Space and by Enter, and the key-release pin (Space clicks a button on its release, so a Space
// pressed in view and released out of view is read too), with (a)'s scroll. Four keep checks hold what must still work: Space held on a keyboard focus presses the
// control and its release opens once, a control in view inside the scrolling table and one half in view each open on their key,
// and a mouse press held on the control matches :active until its release opens once. The report: a remote picture of 300 by 200
// from the second server ("big") under the first paragraph, thirty paragraphs, a table wider than the Rendered box, which scrolls
// on its own (the sheets' overflow-x: auto), holding a second remote picture ("wide") at full size in its first cell, and thirty
// paragraphs more, both pictures loaded through the gate. Each case runs in a browser of its own (the fine pointer Chromium's
// default, the laptop the LAPTOP flags, touch CDP's emulation enabled after the load), window.open stubbed to count the opens,
// and logs its record as a diagnostic. Every pin is a property pin read off the page, each red over the viewer before these
// fixes by the red its title names; file-figure-open.test.ts and file-view-links.test.ts hold the spellings.
const FOCUS_CELL = "cellword".repeat(40);   // one unbreakable word, so the table is wider than the Rendered box and scrolls on its own
const FOCUS_TEXT = "# Report\n\n" + PARA(1) + "\n\n![big](" + WEB + "/pic.svg)\n\n" + Array.from({ length: 30 }, (_, i) => PARA(i + 2)).join("\n\n")
  // the picture's own cell carries a shorter word (about 400px), so the cell holds the 300px picture at full size, over the control's floor
  + "\n\n| picture | words | more |\n| --- | --- | --- |\n| ![wide](" + WEB + "/wide.svg) " + "picword".repeat(9) + " | " + FOCUS_CELL + " | " + FOCUS_CELL + " |\n\n"
  + Array.from({ length: 30 }, (_, i) => PARA(i + 40)).join("\n\n") + "\n";
type Pointer = "fine" | "laptop" | "touch";
type Surface = "chat" | "feed" | "pane";
type FocusState = { opened: number; active: string; focusVisible: boolean; focus: boolean; pressed: boolean; hover: boolean; opacity: string; ctl: { top: number; bottom: number; left: number; right: number }; body: { top: number; bottom: number }; scrollTop: number };
/** The web control after the picture `alt` names, and where the keyboard is: the opens so far, the holder (the control, the viewer's
 *  body, or another element by tag and classes), the control's :focus-visible, :focus, :active and :hover, its computed opacity and
 *  box, and the viewer body's box and scrollTop. */
const focusState = (page: any, alt: string): Promise<FocusState> => page.evaluate((alt: string) => (window as any).__focusState(alt), alt);
/** The focus report open on `surface` at 900 by 600, both remote pictures relayed to the second server (`port`) and loaded through the
 *  gate, window.open stubbed to count the opens and the page's helpers installed; under touch, CDP's emulation enabled after the load. */
async function openFocus(browser: any, port: number, pointer: Pointer, surface: Surface): Promise<{ page: any; errors: string[]; cdp: any }> {
  const before = async (pg: any): Promise<void> => {
    await pg.context().route((u: URL) => u.href.startsWith(WEB + "/"), async (route: any) => {
      const a = await fromSecond(port, new URL(route.request().url()).pathname);
      return route.fulfill({ status: a.status, contentType: a.type, body: a.body });
    });
  };
  const o = await openViewer(browser, surface, 900, 600, { docs: { [REPORT]: FOCUS_TEXT }, before });
  await o.page.evaluate(() => {
    const w = window as any;
    w.__opened = [];
    window.open = ((u: unknown) => { w.__opened.push(String(u)); return { opener: null }; }) as unknown as typeof window.open;
    w.__img = (alt: string) => Array.from(document.querySelectorAll(".fileview-md img")).find((i) => i.getAttribute("alt") === alt) as HTMLElement;
    w.__ctl = (alt: string) => { const n = w.__img(alt).nextElementSibling; return n && n.hasAttribute("data-fv-figopen") ? n as HTMLElement : null; };
    w.__focusState = (alt: string) => {
      const c = w.__ctl(alt) as HTMLElement, b = document.querySelector(".fileview-body") as HTMLElement, a = document.activeElement as HTMLElement | null;
      const r = c.getBoundingClientRect(), br = b.getBoundingClientRect();
      const named = (e: HTMLElement) => e.localName + (typeof e.className === "string" && e.className.trim() ? "." + e.className.trim().split(/\s+/).join(".") : "");
      return { opened: w.__opened.length, active: a === c ? "control" : a === b ? "fileview-body" : a ? named(a) : "null",
        focusVisible: c.matches(":focus-visible"), focus: c.matches(":focus"), pressed: c.matches(":active"), hover: c.matches(":hover"), opacity: getComputedStyle(c).opacity,
        ctl: { top: Math.round(r.top), bottom: Math.round(r.bottom), left: Math.round(r.left), right: Math.round(r.right) }, body: { top: Math.round(br.top), bottom: Math.round(br.bottom) }, scrollTop: Math.round(b.scrollTop) };
    };
  });
  await o.page.click('[data-act="fv-load"]');
  await o.page.waitForFunction(() => { const imgs = Array.from(document.querySelectorAll(".fileview-md img")) as HTMLImageElement[]; return imgs.length === 2 && imgs.every((i) => i.complete && i.naturalWidth > 0) && document.querySelectorAll(".fileview-md .fv-figopen-web").length === 2; }, null, { timeout: 10000 });
  await frames(o.page, 3);
  let cdp: any = null;
  if (pointer === "touch") { cdp = await o.page.context().newCDPSession(o.page); await cdp.send("Emulation.setTouchEmulationEnabled", { enabled: true, maxTouchPoints: 1 }); await frames(o.page, 2); }
  return { ...o, cdp };
}
/** Until the viewer body's scrollTop holds for four polls two frames apart (a wheel and a Space key scroll smoothly), bounded. */
async function settleScroll(page: any): Promise<number> {
  let last = -1, same = 0;
  for (let i = 0; i < 150; i++) {
    const s = await page.evaluate(() => (document.querySelector(".fileview-body") as HTMLElement).scrollTop);
    if (s === last) { if (++same >= 4) return s; } else same = 0;
    last = s;
    await frames(page, 2);
  }
  return last;
}
const tapAt = async (cdp: any, x: number, y: number): Promise<void> => { await cdp.send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [{ x, y }] }); await cdp.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] }); };
/** The picture `alt` names centred in the body, then a press on the plain text of the first paragraph below it, which gives the viewer's
 *  body the keyboard (its tabindex 0), the pointer left there (a tap under touch); returns that point. */
async function pressPlainText(page: any, cdp: any, pointer: Pointer, alt: string): Promise<{ x: number; y: number }> {
  await page.evaluate((alt: string) => { (window as any).__img(alt).scrollIntoView({ block: "center" }); }, alt);
  await settleScroll(page);
  const p = await page.evaluate((alt: string) => {
    const ib = (window as any).__img(alt).getBoundingClientRect(), br = (document.querySelector(".fileview-body") as HTMLElement).getBoundingClientRect();
    const para = Array.from(document.querySelectorAll(".fileview-md > p")).map((e) => e.getBoundingClientRect()).find((r) => r.top > ib.bottom + 4 && r.top + 6 < br.bottom)!;
    return { x: para.left + 20, y: para.top + 5 };
  }, alt);
  if (pointer === "touch") await tapAt(cdp, p.x, p.y); else await page.mouse.click(p.x, p.y);
  await frames(page, 2);
  return p;
}
const controlCentre = (page: any, alt: string): Promise<{ x: number; y: number }> => page.evaluate((alt: string) => { const r = (window as any).__ctl(alt).getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; }, alt);
/** The pointer over the picture until its control is revealed (opacity 1), then onto the control (not under touch). */
async function revealControl(page: any, alt: string): Promise<void> {
  const ic = await page.evaluate((alt: string) => { const r = (window as any).__img(alt).getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; }, alt);
  await page.mouse.move(ic.x, ic.y);
  await page.waitForFunction((alt: string) => getComputedStyle((window as any).__ctl(alt)).opacity === "1", alt, { timeout: 5000 });
}
/** A click on the web control, the control revealed by the pointer over its picture first; a tap under touch. */
async function clickWebControl(page: any, cdp: any, pointer: Pointer, alt: string): Promise<void> {
  if (pointer !== "touch") await revealControl(page, alt);
  const c = await controlCentre(page, alt);
  if (pointer === "touch") await tapAt(cdp, c.x, c.y); else await page.mouse.click(c.x, c.y);
  await frames(page, 2);
}
/** A press on the web control dragged off onto the plain text at `off` and released there, which is no click. */
async function abortedPress(page: any, alt: string, off: { x: number; y: number }): Promise<void> {
  await revealControl(page, alt);
  const c = await controlCentre(page, alt);
  await page.mouse.move(c.x, c.y);
  await page.mouse.down();
  await frames(page, 2);
  await page.mouse.move(off.x, off.y, { steps: 5 });
  await page.mouse.up();
  await frames(page, 2);
}
const pointerAway = async (page: any, pointer: Pointer): Promise<void> => { if (pointer !== "touch") await page.mouse.move(5, 5); await frames(page, 3); };
/** The theme set on the page's body, the big control's transition awaited (bounded). */
async function focusTheme(page: any, which: "dark" | "light"): Promise<void> {
  await page.evaluate((light: boolean) => new Promise<void>((done) => { const c = (window as any).__ctl("big") as HTMLElement; c.addEventListener("transitionend", () => done(), { once: true }); setTimeout(done, 1500); document.body.classList.toggle("theme-light", light); }), which === "light");
  await frames(page, 2);
}
/** Tab pressed until the web control after `alt` holds the keyboard; returns the presses (bounded at 40). */
async function tabToControl(page: any, alt: string): Promise<number> {
  for (let i = 0; i < 40; i++) {
    await page.keyboard.press("Tab");
    await frames(page, 1);
    if (await page.evaluate((alt: string) => document.activeElement === (window as any).__ctl(alt), alt)) return i + 1;
  }
  throw new Error("Tab never reached the " + alt + " picture's control");
}
/** The web control after `alt`, focused or not, read as painted in both themes when it holds the keyboard: a read under 3:1, or a line
 *  paintedRatio refuses (a control at opacity 0 shows the picture alone, no dash and no ground), is pushed onto `fails`; each read is
 *  noted. Returns whether the control held the keyboard in each theme. */
async function focusedPaints(page: any, alt: string, fails: string[], note: (m: string) => void, onlyIfFocused: boolean): Promise<boolean[]> {
  const held: boolean[] = [];
  for (const th of ["dark", "light"] as const) {
    await focusTheme(page, th);
    const s = await focusState(page, alt);
    held.push(s.active === "control");
    if (onlyIfFocused && s.active !== "control") { note(th + " theme: the keyboard is on " + s.active + ", not on the control"); continue; }
    const p: Painted | Error = await paintedRatio(page, alt, "control").catch((e: Error) => e);
    if (p instanceof Error) fails.push(th + " theme: the control holding the keyboard at opacity " + s.opacity + " (:focus " + s.focus + ", :focus-visible " + s.focusVisible + "): its line as painted is refused, " + p.message.split("\n")[0]);
    else {
      note(th + " theme: the focused control's line " + p.dash + " over " + p.ground + ", " + p.ratio.toFixed(3) + ":1 at opacity " + s.opacity);
      if (p.ratio < 3) fails.push(th + " theme: the control holding the keyboard paints " + p.dash + " over " + p.ground + ", " + p.ratio.toFixed(3) + ":1, under the 3:1 floor");
    }
  }
  await focusTheme(page, "dark");
  return held;
}
/** One case: the second server, a browser for the pointer (the laptop's flags at its launch), the focus report opened on the surface,
 *  `body` run, and the case's record handed to the test's diagnostic whatever happens. */
async function focusCase(t: any, pointer: Pointer, surface: Surface, rec: Record<string, unknown>, body: (page: any, cdp: any) => Promise<void>): Promise<void> {
  const second = await secondServer([]);
  try {
    await inBrowser(t, async (browser) => {
      const { page, errors, cdp } = await openFocus(browser, second.port, pointer, surface);
      try {
        await body(page, cdp);
        assert.deepEqual(errors, [], "no page errors");
      } finally {
        rec.opens = await page.evaluate(() => (window as any).__opened).catch(() => null);
        t.diagnostic("record " + JSON.stringify({ pointer, surface, ...rec }));
        await page.close();
      }
    }, pointer === "laptop" ? { args: [LAPTOP] } : {});
  } finally { await second.close(); }
}
const onWhat = (pointer: Pointer, surface: Surface): string => "(" + (pointer === "fine" ? "a fine pointer" : pointer === "laptop" ? "the touchscreen laptop" : "touch emulation") + (surface === "chat" ? "" : ", the " + (surface === "feed" ? "feed" : "Files pane")) + ")";

for (const [pointer, surface] of [["fine", "chat"], ["laptop", "chat"], ["touch", "chat"], ["fine", "feed"], ["fine", "pane"]] as Array<[Pointer, Surface]>) {
  test("in a browser " + onWhat(pointer, surface) + ", the web control's focus, pin (a): a click on the web control, the pointer away, the body wheeled until the control is out of view, then Space: exactly one open in total, the click's, and Space scrolls the body (the file review's round 14, ui-1 with extra9-1: before the fixes the click left the keyboard on the control, and Space opened a second tab from out of view and scrolled nothing)", { timeout: 120000 }, async (t) => {
    const rec: Record<string, unknown> = { pin: "a" };
    await focusCase(t, pointer, surface, rec, async (page, cdp) => {
      await pressPlainText(page, cdp, pointer, "big");
      await clickWebControl(page, cdp, pointer, "big");
      rec.afterClick = await focusState(page, "big");
      await pointerAway(page, pointer);
      if (pointer === "touch") await page.evaluate(() => { (document.querySelector(".fileview-body") as HTMLElement).scrollBy(0, 3000); });
      else { await page.mouse.move(450, 400); await page.mouse.wheel(0, 3000); }
      await settleScroll(page);
      const w = await focusState(page, "big");
      rec.afterWheel = w;
      assert.ok(w.ctl.bottom <= w.body.top, "the control is out of view above the body (a precondition): " + w.ctl.bottom + " vs " + w.body.top);
      await page.keyboard.press("Space");
      await settleScroll(page);
      const s = await focusState(page, "big");
      rec.afterSpace = s;
      assert.equal(s.opened, 1, "exactly one open in total, the click's: a second is Space opening the tab again from the control out of view (the keyboard on " + s.active + ") (a property pin read off the page)");
      assert.ok(s.scrollTop > w.scrollTop, "Space scrolls the body: " + w.scrollTop + " to " + s.scrollTop + " (the keyboard on " + s.active + ") (a property pin read off the page)");
    });
  });
}
for (const [pointer, surface] of [["fine", "chat"], ["laptop", "chat"], ["fine", "feed"], ["fine", "pane"]] as Array<[Pointer, Surface]>) {
  test("in a browser " + onWhat(pointer, surface) + ", the web control's focus, pin (b): an aborted press on the web control (pressed, dragged off onto the text and released there, no click), the pointer away, then Enter: no open (the file review's round 14, ui-1 with extra9-1: before the fixes the press left the keyboard on the control and Enter opened one)", { timeout: 120000 }, async (t) => {
    const rec: Record<string, unknown> = { pin: "b" };
    await focusCase(t, pointer, surface, rec, async (page, cdp) => {
      const off = await pressPlainText(page, cdp, pointer, "big");
      await abortedPress(page, "big", off);
      const p = await focusState(page, "big");
      rec.afterPress = p;
      assert.equal(p.opened, 0, "the aborted press opens nothing (a precondition)");
      await pointerAway(page, pointer);
      await page.keyboard.press("Enter");
      await frames(page, 3);
      const s = await focusState(page, "big");
      rec.afterEnter = s;
      assert.equal(s.opened, 0, "Enter after an aborted press opens nothing (the keyboard on " + s.active + ") (a property pin read off the page)");
    });
  });
}
for (const pointer of ["fine", "laptop"] as Pointer[]) for (const gesture of ["click", "aborted press"] as const) {
  test("in a browser " + onWhat(pointer, "chat") + ", the web control's focus, pin (c): after " + (gesture === "click" ? "a click" : "an aborted press") + " on the web control, the pointer away, the control does not hold the keyboard, or, held by another road, paints its line at 3:1 or better in both themes (paintedRatio) (the file review's round 14, ui-1 with extra9-1: before the fixes, on the fine pointer, the control held the keyboard at opacity 0 and paintedRatio found no dash; on the laptop the at-rest rule shows the control, so that cell paints on the second branch before the fixes too, green by design)", { timeout: 120000 }, async (t) => {
    const rec: Record<string, unknown> = { pin: "c", gesture };
    const fails: string[] = [];
    await focusCase(t, pointer, "chat", rec, async (page, cdp) => {
      const off = await pressPlainText(page, cdp, pointer, "big");
      if (gesture === "click") await clickWebControl(page, cdp, pointer, "big"); else await abortedPress(page, "big", off);
      await pointerAway(page, pointer);
      rec.held = await focusedPaints(page, "big", fails, (m) => t.diagnostic(m), true);
      assert.deepEqual(fails, [], "after the gesture the web control holds no keyboard focus, or paints its line at 3:1 in both themes (a property pin read off the page):\n" + fails.join("\n"));
    });
  });
}
for (const surface of ["chat", "feed", "pane"] as Surface[]) for (const key of ["Space", "Enter"] as const) {
  test("in a browser " + onWhat("fine", surface) + ", the web control's focus, pin (d): Tab to the web control, PageDown until it is out of view, then " + key + ": no open (the file review's round 14, extra9-1: before the fixes " + key + " opened one from the control out of view)", { timeout: 120000 }, async (t) => {
    const rec: Record<string, unknown> = { pin: "d", key };
    await focusCase(t, "fine", surface, rec, async (page, cdp) => {
      await pressPlainText(page, cdp, "fine", "big");
      await pointerAway(page, "fine");
      rec.tabs = await tabToControl(page, "big");
      const f = await focusState(page, "big");
      assert.equal(f.focusVisible, true, "a keyboard focus on the control, :focus-visible (a precondition)");
      let s = f, n = 0;
      while (s.ctl.bottom > s.body.top && n < 12) { await page.keyboard.press("PageDown"); await settleScroll(page); s = await focusState(page, "big"); n++; }
      rec.pageDowns = n;
      rec.afterPageDown = s;
      assert.ok(s.ctl.bottom <= s.body.top && s.active === "control", "the focused control is out of view above the body (a precondition): " + s.ctl.bottom + " vs " + s.body.top + ", the keyboard on " + s.active);
      await page.keyboard.press(key);
      await settleScroll(page);
      const a = await focusState(page, "big");
      rec.afterKey = a;
      assert.equal(a.opened, 0, key + " on the keyboard-focused control out of view opens nothing (a property pin read off the page)");
    });
  });
}
for (const surface of ["chat", "feed", "pane"] as Surface[]) {
  test("in a browser " + onWhat("fine", surface) + ", the web control's focus, pin (e): after a mouse click on the body's text, the web control focused from script with focusVisible false matches :focus and not :focus-visible, and paints its line at 3:1 or better in both themes (paintedRatio) (the file review's round 14, ui-1: red before the fixes and red at a head without the reveal's :focus member, the control at opacity 0 and no dash found)", { timeout: 120000 }, async (t) => {
    const rec: Record<string, unknown> = { pin: "e" };
    const fails: string[] = [];
    await focusCase(t, "fine", surface, rec, async (page, cdp) => {
      await pressPlainText(page, cdp, "fine", "big");
      await pointerAway(page, "fine");
      const f = await page.evaluate(() => { const c = (window as any).__ctl("big") as HTMLElement; c.focus({ preventScroll: true, focusVisible: false } as FocusOptions & { focusVisible: boolean }); return { active: document.activeElement === c, focus: c.matches(":focus"), focusVisible: c.matches(":focus-visible") }; });
      rec.focused = f;
      assert.deepEqual([f.active, f.focus, f.focusVisible], [true, true, false], "the script's focus holds the control and :focus-visible does not match it in Chromium (the case's premise, asserted first)");
      rec.held = await focusedPaints(page, "big", fails, (m) => t.diagnostic(m), false);
      assert.deepEqual(fails, [], "a web control focused with no ring paints its line at 3:1 in both themes (a property pin read off the page):\n" + fails.join("\n"));
    });
  });
}
for (const key of ["Space", "Enter"] as const) test("in a browser (a fine pointer), the web control's focus, pin (f): a Tab-focused web control in a table wider than the Rendered box, the table scrolled sideways until the control is outside the table's own scrollport while the body still shows its row, then " + key + ": no open (the file review's round 14, extra9-1: before the fixes " + key + " opened one)", { timeout: 120000 }, async (t) => {
  const rec: Record<string, unknown> = { pin: "f", key };
  await focusCase(t, "fine", "chat", rec, async (page, cdp) => {
    await pressPlainText(page, cdp, "fine", "wide");
    await pointerAway(page, "fine");
    rec.tabs = await tabToControl(page, "wide");
    await settleScroll(page);
    await page.evaluate(() => { const tb = (window as any).__img("wide").closest("table") as HTMLElement; tb.scrollLeft = tb.scrollWidth; });
    await frames(page, 3);
    const g = await page.evaluate(() => {
      const c = (window as any).__ctl("wide") as HTMLElement, tb = c.closest("table") as HTMLElement, tr = c.closest("tr") as HTMLElement, b = document.querySelector(".fileview-body") as HTMLElement;
      const cr = c.getBoundingClientRect(), tr0 = tb.getBoundingClientRect(), rr = tr.getBoundingClientRect(), br = b.getBoundingClientRect(), cs = getComputedStyle(tb);
      const pl = tr0.left + tb.clientLeft, pr = pl + tb.clientWidth;
      return { overflowX: cs.overflowX, scrollLeft: Math.round(tb.scrollLeft), scrollWidth: tb.scrollWidth, clientWidth: tb.clientWidth, port: [Math.round(pl), Math.round(pr)], ctl: [Math.round(cr.left), Math.round(cr.right)],
        outside: cr.right <= pl || cr.left >= pr, rowShown: rr.top < br.bottom && rr.bottom > br.top, active: document.activeElement === c };
    });
    rec.geometry = g;
    assert.deepEqual([g.outside, g.rowShown, g.active], [true, true, true], "the focused control is outside the table's scrollport while the body shows its row (a precondition): " + JSON.stringify(g));
    await page.keyboard.press(key);
    await frames(page, 4);
    const s = await focusState(page, "wide");
    rec.afterKey = s;
    assert.equal(s.opened, 0, key + " on the control outside the table's scrollport opens nothing (a property pin read off the page)");
  });
});
test("in a browser (a fine pointer), the web control's focus, the key-release pin: Tab to the web control, Space pressed and held while the control is in view, the body scrolled until the control is out of view, then the release: no open (the file review's round 14, extra9-1: Space clicks a button on its release, so the key gate reads the release too; before the fixes the release opened one from the control out of view)", { timeout: 120000 }, async (t) => {
  const rec: Record<string, unknown> = { pin: "key-release" };
  await focusCase(t, "fine", "chat", rec, async (page, cdp) => {
    await pressPlainText(page, cdp, "fine", "big");
    await pointerAway(page, "fine");
    rec.tabs = await tabToControl(page, "big");
    await settleScroll(page);
    const f = await focusState(page, "big");
    rec.focused = f;
    assert.ok(f.active === "control" && f.ctl.bottom > f.body.top && f.ctl.top < f.body.bottom, "the keyboard-focused control is in view (a precondition): " + JSON.stringify(f));
    await page.keyboard.down("Space");
    await frames(page, 2);
    const held = await focusState(page, "big");
    rec.held = held;
    assert.deepEqual([held.pressed, held.opened], [true, 0], "Space held on the control in view presses it (:active) with nothing opened (a precondition)");
    await page.evaluate(() => { (document.querySelector(".fileview-body") as HTMLElement).scrollTop += 3000; });
    await settleScroll(page);
    const out = await focusState(page, "big");
    rec.beforeRelease = out;
    assert.ok(out.active === "control" && out.ctl.bottom <= out.body.top, "the control, Space still held on it, is out of view above the body (a precondition): " + out.ctl.bottom + " vs " + out.body.top + ", the keyboard on " + out.active);
    await page.keyboard.up("Space");
    await frames(page, 3);
    const s = await focusState(page, "big");
    rec.afterRelease = s;
    assert.equal(s.opened, 0, "the release of a Space pressed in view opens nothing once the control is out of view (a property pin read off the page)");
  });
});
for (const button of ["right", "middle"] as const) {
  test("in a browser (a fine pointer), the web control's focus, the other-button pin: a " + button + " press released on the web control, the pointer away, then Enter: no open and the control never holds the keyboard, while the " + (button === "right" ? "context menu" : "auxclick") + " still comes (the file review's round 14, ui-1 with extra9-1, the maintainer's answer taking a press of any mouse button: before the fixes, and with the press cancelled for the primary button alone, the " + button + " press focused the control and Enter opened one)", { timeout: 120000 }, async (t) => {
    const rec: Record<string, unknown> = { pin: "other-" + button };
    await focusCase(t, "fine", "chat", rec, async (page, cdp) => {
      await pressPlainText(page, cdp, "fine", "big");
      await page.evaluate(() => { const w = window as any; w.__ctx = 0; w.__aux = 0; window.addEventListener("contextmenu", () => { w.__ctx++; }, true); window.addEventListener("auxclick", () => { w.__aux++; }, true); });
      await revealControl(page, "big");
      const c = await controlCentre(page, "big");
      await page.mouse.move(c.x, c.y);
      await page.mouse.down({ button });
      await frames(page, 2);
      await page.mouse.up({ button });
      await frames(page, 2);
      const p = await focusState(page, "big");
      const events = await page.evaluate(() => ({ contextmenu: (window as any).__ctx, auxclick: (window as any).__aux }));
      rec.afterPress = p;
      rec.events = events;
      await pointerAway(page, "fine");
      await page.keyboard.press("Enter");
      await frames(page, 3);
      const s = await focusState(page, "big");
      rec.afterEnter = s;
      assert.deepEqual([p.active === "control", s.opened], [false, 0], "the " + button + " press leaves the keyboard off the control (on " + p.active + ") and Enter opens nothing (opened " + s.opened + ") (a property pin read off the page)");
      assert.ok(button === "right" ? events.contextmenu >= 1 : events.auxclick >= 1, "the " + button + " press still fires its " + (button === "right" ? "contextmenu" : "auxclick") + ": " + JSON.stringify(events));
    });
  });
}
// the keep checks: what must still work under the three requirements, each green over the viewer before the fixes by design
test("in a browser (a fine pointer), the web control's focus, a keep check: Tab to the web control, Space held presses it (:active) with nothing opened, and the release opens once (the file review's round 14, extra9-1: the key's gate stands aside for a control in view)", { timeout: 120000 }, async (t) => {
  const rec: Record<string, unknown> = { pin: "keep-space" };
  await focusCase(t, "fine", "chat", rec, async (page, cdp) => {
    await pressPlainText(page, cdp, "fine", "big");
    await pointerAway(page, "fine");
    rec.tabs = await tabToControl(page, "big");
    await page.keyboard.down("Space");
    await frames(page, 3);
    const h = await focusState(page, "big");
    rec.held = h;
    await page.keyboard.up("Space");
    await frames(page, 3);
    const s = await focusState(page, "big");
    rec.afterRelease = s;
    assert.deepEqual([h.pressed, h.opened, s.opened], [true, 0, 1], "Space holds the control pressed and its release opens once (a keep check, a property read off the page)");
  });
});
test("in a browser (a fine pointer), the web control's focus, a keep check: Tab to the web control in the wide table with the table unscrolled, the control in view inside its scrollport: Space opens once (the file review's round 14, extra9-1: the table's scrollport is read, and a control inside it is in view)", { timeout: 120000 }, async (t) => {
  const rec: Record<string, unknown> = { pin: "keep-table" };
  await focusCase(t, "fine", "chat", rec, async (page, cdp) => {
    await pressPlainText(page, cdp, "fine", "wide");
    await pointerAway(page, "fine");
    rec.tabs = await tabToControl(page, "wide");
    await settleScroll(page);
    const f = await focusState(page, "wide");
    rec.afterTab = f;
    await page.keyboard.press("Space");
    await frames(page, 4);
    const s = await focusState(page, "wide");
    rec.afterSpace = s;
    assert.deepEqual([f.active, s.opened], ["control", 1], "a control in view inside the scrolling table opens on Space (a keep check, a property read off the page)");
  });
});
test("in a browser (a fine pointer), the web control's focus, a keep check: Tab to the web control, the body scrolled until the control straddles its top edge, then Enter: one open, since a control partly in view is in view (the file review's round 14, extra9-1: the rule is intersection)", { timeout: 120000 }, async (t) => {
  const rec: Record<string, unknown> = { pin: "keep-half" };
  await focusCase(t, "fine", "chat", rec, async (page, cdp) => {
    await pressPlainText(page, cdp, "fine", "big");
    await pointerAway(page, "fine");
    rec.tabs = await tabToControl(page, "big");
    await page.evaluate(() => { const c = (window as any).__ctl("big") as HTMLElement, b = document.querySelector(".fileview-body") as HTMLElement; const r = c.getBoundingClientRect(), br = b.getBoundingClientRect(); b.scrollTop += (r.top - br.top) + r.height / 2; });
    await frames(page, 3);
    const f = await focusState(page, "big");
    rec.half = f;
    assert.ok(f.ctl.top < f.body.top && f.ctl.bottom > f.body.top && f.active === "control", "the focused control straddles the body's top edge (a precondition): " + JSON.stringify(f.ctl) + " vs " + f.body.top);
    await page.keyboard.press("Enter");
    await frames(page, 3);
    const s = await focusState(page, "big");
    rec.afterEnter = s;
    assert.equal(s.opened, 1, "a control partly in view opens on Enter (a keep check, a property read off the page)");
  });
});
for (const pointer of ["fine", "laptop"] as Pointer[]) {
  test("in a browser " + onWhat(pointer, "chat") + ", the web control's focus, a keep check: a mouse press held on the web control matches :active while held, with nothing opened, and its release opens once (the file review's round 14, extra9-1: in Chromium the press cancelled so that it focuses nothing still presses the control, so pressedLegible's pressed paint stands)", { timeout: 120000 }, async (t) => {
    const rec: Record<string, unknown> = { pin: "keep-press" };
    await focusCase(t, pointer, "chat", rec, async (page, cdp) => {
      await pressPlainText(page, cdp, pointer, "big");
      await revealControl(page, "big");
      const c = await controlCentre(page, "big");
      await page.mouse.move(c.x, c.y);
      await frames(page, 2);
      await page.mouse.down();
      await frames(page, 3);
      const h = await focusState(page, "big");
      rec.held = h;
      await page.mouse.up();
      await frames(page, 3);
      const s = await focusState(page, "big");
      rec.afterRelease = s;
      assert.deepEqual([h.pressed, h.opened, s.opened], [true, 0, 1], "the press holds :active and its release opens once (a keep check, a property read off the page)");
    });
  });
}

// ── a picture inside a fold's summary: the fold takes the click, plain or modified, and the control stays ───────────────────────
// (the file review's round 14, fresh-1: the figures' click listener read no summary, so one click on a picture inside a details
// element's own first summary toggled the fold AND opened the picture, a remote picture's tab or a local picture's open in the
// viewer in place of the report, and a Ctrl-click toggled the fold too and opened the picture's tab; the picture under the floor
// wore the address line and the outbound mark, which promised the open.) The report: six pictures, each in a summary, the remote
// ones from the second server through the gate: a remote picture under the floor (20 by 20, "stiny"), a local picture ("slocal")
// and a remote picture over the floor ("sbig"), each in a details element's own first summary; a remote picture inside an author's
// named anchor inside such a summary ("snamed"); and a remote and a local picture each in a stray summary outside any details
// ("stray", "straylocal"), which toggles nothing. On a fine pointer in the dark theme, window.open stubbed to a record, each fold's
// toggles recorded by a MutationObserver on its open attribute as the click's task runs (so a navigation that replaces the report
// after the click cannot hide the toggle), a Ctrl-click the key held around the click with its ctrlKey read back at the document,
// and an open that must not happen read after a bounded settle (the viewer's navigation is a fetch and a paint, so the bar's name is
// awaited up to 2 s for a change). Each case collects its cells, logs its record as diagnostics and asserts the cells once. The
// first three are property pins read off the page, red over the viewer before the summary predicate (file-view.ts figureFoldOf) by
// the open beside the toggle and by the title line and the mark; the fourth holds the ruling's two controls, green there by design.
const FOLD_TEXT = "# Report\n\n" + PARA(1) + "\n\n"
  + '<details><summary><img src="' + WEB + '/stiny.svg" alt="stiny"> Build badge</summary>\n\nfolded text one\n\n</details>\n\n' + PARA(2) + "\n\n"
  + '<details><summary><img src="figs/plot.svg" alt="slocal"> Local screenshots</summary>\n\nfolded text two\n\n</details>\n\n' + PARA(3) + "\n\n"
  + '<details><summary><img src="' + WEB + '/sbig.svg" alt="sbig"> Remote screenshots</summary>\n\nfolded text three\n\n</details>\n\n' + PARA(4) + "\n\n"
  + '<details><summary><a name="fig-n"><img src="' + WEB + '/snamed.svg" alt="snamed"></a> A named anchor inside</summary>\n\nfolded text four\n\n</details>\n\n' + PARA(5) + "\n\n"
  + '<summary><img src="' + WEB + '/stray.svg" alt="stray"> A stray summary</summary>\n\n' + PARA(6) + "\n\n"
  + '<summary><img src="figs/plot2.svg" alt="straylocal"> A stray local summary</summary>\n\n' + PARA(7) + "\n";
const FOLD_DOCS: Record<string, string> = { [REPORT]: FOLD_TEXT, [PLOT]: svg("#456"), [PLOT2]: svg("#654") };
const FOLD_ALTS = ["stiny", "slocal", "sbig", "snamed", "stray", "straylocal"];
type FoldFig = { alt: string; inSummary: boolean; ownSummary: boolean; w: number; h: number; title: string | null; mark: boolean; control: boolean };
/** Every picture of the fold report: whether a summary holds it and whether that summary is its details element's own first
 *  summary child, its laid-out box, its title, the outbound mark's attribute and the control standing after its anchor. */
const foldFigs = (page: any): Promise<FoldFig[]> => page.evaluate(() => Array.from(document.querySelectorAll(".fileview-md img")).map((img) => {
  let a: Element = img;
  for (let p = a.parentElement; p && (p.localName === "a" || p.classList.contains("fc-imgwrap") || p.localName === "picture") && (p.localName !== "a" || (p.textContent || "").trim() === ""); p = a.parentElement) a = p;
  const n = a.nextElementSibling;
  const s = img.closest("summary");
  const d = s ? s.parentElement : null;
  const r = img.getBoundingClientRect();
  return { alt: img.getAttribute("alt") || "", inSummary: !!s, ownSummary: !!s && !!d && d.localName === "details" && d.querySelector(":scope > summary") === s, w: r.width, h: r.height,
    title: img.getAttribute("title"), mark: img.hasAttribute("data-fv-figweb"), control: !!n && n.hasAttribute("data-fv-figopen") };
}));
/** Until all six pictures of the fold report are loaded and out of the gate's placeholder, then three frames. */
const foldLoaded = async (page: any): Promise<void> => {
  await page.waitForFunction(() => { const imgs = Array.from(document.querySelectorAll(".fileview-md img")); return imgs.length === 6 && imgs.every((i) => !i.closest('[data-act="fv-load"]') && (i as HTMLImageElement).complete && (i as HTMLImageElement).naturalWidth > 0); }, null, { timeout: 10000 });
  await frames(page, 3);
};
/** The fold report open in the chat modal at 900 by 700: the remote pictures relayed to the second server (`port`), the local ones
 *  loaded, the gate lifted, then all six loaded; window.open stubbed to a record and a capture listener on the document recording
 *  each click's ctrlKey. */
async function openFold(browser: any, port: number): Promise<{ page: any; errors: string[] }> {
  const before = async (pg: any): Promise<void> => {
    await pg.context().route((u: URL) => u.href.startsWith(WEB + "/"), async (route: any) => {
      const a = await fromSecond(port, new URL(route.request().url()).pathname);
      return route.fulfill({ status: a.status, contentType: a.type, body: a.body });
    });
  };
  const o = await openViewer(browser, "chat", 900, 700, {
    docs: FOLD_DOCS, before,
    serve: (u) => { const p = u.pathname === "/file" ? u.searchParams.get("path") || "" : ""; return FOLD_DOCS[p] !== undefined && /\.svg$/.test(p) ? { status: 200, type: "image/svg+xml", body: FOLD_DOCS[p] } : null; },
  });
  await o.page.evaluate(() => { const w = window as any; w.__opened = []; w.__ctrl = []; window.open = ((u: unknown) => { w.__opened.push(String(u)); return { opener: null }; }) as unknown as typeof window.open; document.addEventListener("click", (ev) => { w.__ctrl.push((ev as MouseEvent).ctrlKey); }, { capture: true }); });
  await o.page.waitForFunction(() => Array.from(document.querySelectorAll(".fileview-md img")).filter((i) => !i.closest('[data-act="fv-load"]')).every((i) => (i as HTMLImageElement).complete && (i as HTMLImageElement).naturalWidth > 0), null, { timeout: 10000 });
  await o.page.click('[data-act="fv-load"]');
  await foldLoaded(o.page);
  return o;
}
type FoldClick = { name: string; hit: string | null; toggled: string[]; opened: string[]; base: string | null; ctrlSeen: boolean[] };
/** A click on the picture `alt` names (at 0.3 of its width and 0.6 of its height, scrolled to the body's centre), Control held
 *  around it when `ctrl`, every fold shut first and its toggles recorded from then on: what the fold, window.open and the viewer
 *  did. A navigation is read after the bounded settle and undone by Back, so the next cell starts on the report. */
async function foldClick(page: any, alt: string, ctrl: boolean): Promise<FoldClick> {
  await page.evaluate(() => { for (const d of Array.from(document.querySelectorAll(".fileview-md details"))) (d as HTMLDetailsElement).open = false; });
  await frames(page, 2);
  await page.evaluate(() => { const w = window as any; if (w.__mo) w.__mo.disconnect(); w.__toggled = []; const ds = Array.from(document.querySelectorAll(".fileview-md details")); w.__mo = new MutationObserver((recs) => { for (const r of recs) w.__toggled.push(ds.indexOf(r.target as Element) + ":" + (r.target as HTMLDetailsElement).open); }); for (const d of ds) w.__mo.observe(d, { attributes: true, attributeFilter: ["open"] }); w.__opened.splice(0); w.__ctrl.splice(0); });
  const b = await page.evaluate((alt: string) => { const i = Array.from(document.querySelectorAll(".fileview-md img")).find((x) => x.getAttribute("alt") === alt)!; i.scrollIntoView({ block: "center" }); const q = i.getBoundingClientRect(); return { x: q.left + q.width * 0.3, y: q.top + q.height * 0.6 }; }, alt);
  await frames(page, 2);
  const hit = await page.evaluate(([x, y]: [number, number]) => { const e = document.elementFromPoint(x, y); return e ? e.localName + ":" + (e.getAttribute("alt") || "") : null; }, [b.x, b.y]);
  if (ctrl) await page.keyboard.down("Control");   // mouse.click takes no modifiers option: the key is held around it
  await page.mouse.click(b.x, b.y);
  if (ctrl) await page.keyboard.up("Control");
  const toggled = await page.evaluate(() => (window as any).__toggled.slice());
  try { await page.waitForFunction(() => (document.querySelector(".fileview-base") || { textContent: "" }).textContent !== "report.md", null, { timeout: 2000 }); } catch { /* no navigation within the bound */ }
  await frames(page, 3);
  const at = await base(page);
  const got = { name: alt + (ctrl ? " Ctrl-click" : " plain click"), hit, toggled, opened: await opened(page), base: at, ctrlSeen: await page.evaluate(() => (window as any).__ctrl.splice(0)) };
  if (at !== "report.md") {
    await page.click(".fileview-nav-back");
    await page.locator(".fileview-base", { hasText: "report.md" }).waitFor({ timeout: 10000 });
    await foldLoaded(page);
  }
  return got;
}
/** One fold case on its own browser and second server: the report open and loaded, the six pictures read and checked for the scene
 *  (six, four in a details element's own summary and two in a stray one, stiny under the floor), then `body` run with a `cell`
 *  recorder whose cells are asserted together at the end, every record a diagnostic first. */
async function foldCase(t: any, body: (page: any, figs: FoldFig[], cell: (what: string, want: unknown, got: unknown) => void, log: (r: unknown) => void) => Promise<void>): Promise<void> {
  const served: string[] = [];
  const second = await secondServer(served, { "/stiny.svg": [20, 20] });
  const fails: string[] = [];
  const cell = (what: string, want: unknown, got: unknown): void => { const w = JSON.stringify(want), g = JSON.stringify(got); t.diagnostic((w === g ? "ok " : "FAIL ") + what + ": want " + w + ", got " + g); if (w !== g) fails.push(what + ": want " + w + ", got " + g); };
  try {
    await inBrowser(t, async (browser) => {
      const { page, errors } = await openFold(browser, second.port);
      const figs = await foldFigs(page);
      t.diagnostic("figures " + JSON.stringify(figs));
      assert.deepEqual(figs.map((f) => f.alt), FOLD_ALTS, "the six pictures, loaded (the scene)");
      assert.deepEqual(figs.map((f) => [f.inSummary, f.ownSummary]), [[true, true], [true, true], [true, true], [true, true], [true, false], [true, false]], "four in a details element's own summary, two in a stray summary (the scene)");
      assert.ok(figs[0].w < 48 && figs[0].h < 48 && figs[2].w >= 48 && figs[2].h >= 48, "stiny under the floor and sbig over it (the scene): " + JSON.stringify([figs[0].w, figs[0].h, figs[2].w, figs[2].h]));
      await body(page, figs, cell, (r) => t.diagnostic("record " + JSON.stringify(r)));
      assert.deepEqual(errors, [], "no page errors");
      await page.close();
    });
  } finally { await second.close(); }
  assert.deepEqual(fails, [], "every cell as the fold's click requires (a property pin read off the page):\n" + fails.join("\n"));
}
/** The cells of one click that the fold must take alone: the hit on the picture and, for a Ctrl-click, its ctrlKey read back (both
 *  preconditions, asserted at once), then the fold's one toggle open, no window.open call and the viewer still on the report. */
function foldTakes(c: FoldClick, index: number, cell: (what: string, want: unknown, got: unknown) => void, alt: string, ctrl: boolean): void {
  assert.equal(c.hit, "img:" + alt, c.name + ": the click lands on the picture (a precondition)");
  if (ctrl) assert.deepEqual(c.ctrlSeen, [true], c.name + ": a real Ctrl-click, its ctrlKey read back at the document (a precondition)");
  cell(c.name + ": the fold toggles open, once", [index + ":true"], c.toggled);
  cell(c.name + ": no window.open call", [], c.opened);
  cell(c.name + ": the viewer stays on the report", "report.md", c.base);
}
test("in a browser (a fine pointer), a remote picture under the floor inside a details element's own first summary wears no address line and no outbound mark, and a plain click and a Ctrl-click on it each toggle the fold and open nothing (the file review's round 14, fresh-1: before the summary predicate the picture wore the line and the mark, and each click opened its tab beside the toggle; a property pin read off the page)", { timeout: 240000 }, async (t) => {
  await foldCase(t, async (page, figs, cell, log) => {
    const f = figs[0];
    cell("stiny: no address line in its title", null, f.title);
    cell("stiny: no outbound mark", false, f.mark);
    assert.equal(f.control, false, "stiny wears no control, under the floor (a precondition)");
    for (const ctrl of [false, true]) { const c = await foldClick(page, "stiny", ctrl); log(c); foldTakes(c, 0, cell, "stiny", ctrl); }
  });
});
test("in a browser (a fine pointer), a local picture inside a details element's own first summary keeps its control, and a plain click and a Ctrl-click on the picture each toggle the fold and open nothing: no open in the viewer and no /file tab (the file review's round 14, fresh-1: before the summary predicate the plain click opened the picture in the viewer in place of the report and the Ctrl-click opened its /file URL in a tab, each beside the toggle; a property pin read off the page)", { timeout: 240000 }, async (t) => {
  await foldCase(t, async (page, figs, cell, log) => {
    cell("slocal: its control stays", true, figs[1].control);
    for (const ctrl of [false, true]) { const c = await foldClick(page, "slocal", ctrl); log(c); foldTakes(c, 1, cell, "slocal", ctrl); }
  });
});
test("in a browser (a fine pointer), a remote picture over the floor inside a details element's own first summary, and one inside an author's named anchor inside such a summary, each wear no address line and keep their control, and a plain click on either picture toggles its fold and opens nothing (the file review's round 14, fresh-1, consequences of the one predicate: a named anchor is no link of FIGURE_LINK_SET, so the fold takes the click through it; before the summary predicate each wore the line and opened its tab beside the toggle; a property pin read off the page)", { timeout: 240000 }, async (t) => {
  await foldCase(t, async (page, figs, cell, log) => {
    for (const [i, alt] of [[2, "sbig"], [3, "snamed"]] as Array<[number, string]>) {
      cell(alt + ": no address line in its title", null, figs[i].title);
      cell(alt + ": its control stays", true, figs[i].control);
      const c = await foldClick(page, alt, false); log(c); foldTakes(c, i, cell, alt, false);
    }
  });
});
test("in a browser (a fine pointer), the fold's two controls: the web control of a remote picture over the floor inside a details element's own summary opens its tab once and leaves the fold shut, and a picture inside a stray summary outside any details opens as anywhere else, the remote one's tab on a plain click with its address line in the title, the local one in the viewer on a plain click and its /file URL in a tab on a Ctrl-click (the file review's round 14, fresh-1: controls, green before the summary predicate and after it by design, since a button inside a summary toggles nothing and the predicate reads no stray summary)", { timeout: 240000 }, async (t) => {
  await foldCase(t, async (page, figs, cell, log) => {
    await page.evaluate(() => { for (const d of Array.from(document.querySelectorAll(".fileview-md details"))) (d as HTMLDetailsElement).open = false; });
    await page.evaluate(() => { const w = window as any; if (w.__mo) w.__mo.disconnect(); w.__toggled = []; const ds = Array.from(document.querySelectorAll(".fileview-md details")); w.__mo = new MutationObserver((recs) => { for (const r of recs) w.__toggled.push(ds.indexOf(r.target as Element) + ":" + (r.target as HTMLDetailsElement).open); }); for (const d of ds) w.__mo.observe(d, { attributes: true, attributeFilter: ["open"] }); w.__opened.splice(0); });
    const cb = await page.evaluate(() => { const i = Array.from(document.querySelectorAll(".fileview-md img")).find((x) => x.getAttribute("alt") === "sbig")!; i.scrollIntoView({ block: "center" }); const n = i.nextElementSibling as HTMLElement; const r = n.getBoundingClientRect(); const ir = i.getBoundingClientRect(); return { ok: n.hasAttribute("data-fv-figopen"), x: r.left + r.width / 2, y: r.top + r.height / 2, ix: ir.left + ir.width / 2, iy: ir.top + ir.height / 2 }; });
    assert.ok(cb.ok, "sbig's control stands right after it (a precondition)");
    await page.mouse.move(cb.ix, cb.iy);   // the pointer over the picture reveals its control
    await frames(page, 3);
    await page.mouse.click(cb.x, cb.y);
    await frames(page, 3);
    const control = { toggled: await page.evaluate(() => (window as any).__toggled.slice()), opened: await opened(page), base: await base(page) };
    log({ name: "sbig's control", ...control });
    cell("sbig's web control inside the summary: its tab, once", [WEB + "/sbig.svg"], control.opened);
    cell("sbig's web control inside the summary: the fold stays shut", [], control.toggled);
    cell("stray: the address line in its title, as anywhere else", WEB_LINE(WEB + "/stray.svg"), figs[4].title);
    const s = await foldClick(page, "stray", false); log(s);
    cell("stray plain click: its tab", [WEB + "/stray.svg"], s.opened);
    cell("stray plain click: the viewer stays on the report", "report.md", s.base);
    const l = await foldClick(page, "straylocal", false); log(l);
    cell("straylocal plain click: the picture in the viewer", "plot2.svg", l.base);
    const lc = await foldClick(page, "straylocal", true); log(lc);
    cell("straylocal Ctrl-click: its /file URL in a tab", [FILE_URL(PLOT2)], lc.opened);
    cell("straylocal Ctrl-click: the viewer stays on the report", "report.md", lc.base);
  });
});

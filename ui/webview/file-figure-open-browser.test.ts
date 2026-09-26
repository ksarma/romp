// A figure opens in detail (plans/markdown-viewer.md, "Follow-on: Link navigation", L3 and L4): the contract's case 6 over
// the REAL viewer in headless Chromium (real-viewer-leg.ts: the chat modal, file-view.ts bundled from this tree with the real
// Comments panel, styles.css, a fetch stub for the /file route and a route for the figures' own requests). Read off the DOM
// and the layout: every openable figure of a synthetic report wears an "Open the picture" control as its anchor's next
// sibling (a button of the icon family, titled, in the tab order); the pointer over the figure reveals it and lays it over
// the figure's top-right corner (a right-floated figure's at its top-left, and in right-to-left text at its top-left, its line's
// end, read in cases of their own at the file's end); Tab reaches it and Enter opens the picture, the
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
// and after it in a paragraph, a highlight and a table cell, two glued badges, and runs of f glued to one on both sides, upright,
// italic and bold italic, against the same page with the ring taken off and with the text's ink taken off too, and reads the mark's
// worst dash beside them, at rest under touch and on hover on the fine pointer, in both themes; a case of its own on the Files pane
// under touch emulation reads the runs of f, italic runs in a level-2 and a level-1 heading and a left-floated picture in a note
// callout the same way, at the viewer's default text size and at 150%. Red over a bare 3px ring with no margin beside it (the file
// review's round 14, correctness-2), red at a margin of the ring's width on every side, 56aedf384's, where the runs of f lost the ink
// they paint past their own boxes to the ring and the float's dash read the text it wraps under 3:1 (the margin ruling of
// 2026-09-24), and the pane's case red at a fixed 7px across the line, 5f147e582's, where the heading runs and, at 150%, the italic
// and bold italic runs lost ink to the ring (the second margin ruling that day). The pane's case also reads an italic run glued to a
// picture inside two nested small elements, whose margin, 0.3em of the picture's smaller text, falls short of the run's reach: the ink
// the ring covers there is held within the bound the sheets state (SMALLER_BOUND), 1 to 4 pixels, with the dash beside it at 3:1, so
// a margin that widens the bound or closes it reds (red at 3px plus 0.6em across the line and at 3px); and a bold italic run glued
// to a picture in a sub inside a hundred nested small elements, where the margin has fallen to the ring's 3px, the worst scene the
// sweep below 0.7em read, held within 1 and 30 pixels (FLOOR_BOUND) at those two sizes and at 200%, where that maximum was read (the
// file review's round 15, extra5-3: a residual disclosed and measured, green before the round's fixes by design, red under a margin
// that covers more and under one that covers nothing); and an italic run in a level-2 heading glued to a picture inside a hundred
// nested small elements, the worst scene a sweep of larger f's read, held within 1 and 40 pixels (FLOOR_LARGE_BOUND), its maximum
// read in the 150% pass. A case of its own at a device scale of 2 on the chat modal counts in device pixels the ink a bold italic
// run in a big element loses to the ring beside a picture in sup at the floor, held within 1 and 135 (FLOOR_D2_BOUND) at 200%,
// where that maximum was read, red the same two ways. The ring's line pin
// (ringClearsTheLines), in a case
// of its own at a device scale of 2 on the chat modal, reads a picture under a line of descenders holding an inline code span and
// under a line of keys for the paint the ring covers, and one in a note callout, an even table row and a highlight for the ring's
// pixels past the picture's margin box: red at 2px up and down by a key's bottom row and a row of each tint, and at 1px and with none
// by the code span's box too. The web
// control's focus is read in cases of their own at the file's end (the file review's round 14, ui-1 with extra9-1): no mouse press,
// a click, a press dragged off or a right or a middle press, leaves the keyboard on it, any focus it holds paints its line at 3:1 in
// both themes, and Enter or Space opens it only while it is in view, the body and a table that scrolls on its own each read, on a
// fine pointer, on the laptop and under touch, and in the feed and the Files pane, each pin red over the viewer before those fixes
// and the keep checks beside them green there by design; after them, cases of their own on the chat modal read the key gate under a
// pinch zoom, the viewer as the top page and in the dashboard's same-origin frame, and at a frame of another origin's page (the file
// review's round 15, extra5-2). A picture inside a fold's summary is read in cases of their own after
// those (the file review's round 14, fresh-1): inside a details element's own first summary, a plain click and a Ctrl-click on a
// remote picture under the floor and on a local picture, a plain click on a remote picture over the floor and on one inside a
// named anchor, each toggle the fold and open nothing, the remote pictures wearing no address line and no mark, each red over the
// viewer before the summary predicate by the open beside the toggle and by the line and the mark, while the web control inside the
// summary opens once with the fold shut and the pictures of a stray summary open as anywhere else, controls green there by design;
// and a remote picture under the floor in a details element's second summary, no fold's title, with the details opened carries
// its address line, the origin alone, and the mark and opens its tab once on a plain click, the details staying open (the file
// review's round 15, tests-4: its fold cells green before the round's fixes by design, red with figureFoldOf's loop replaced by
// `return s;`, its title cell red there by the path the title printed before the origin cut). A
// finger's tap on the web control and on the mark is read frame by frame in cases of their own at the file's end (the tap-highlight
// ruling of 2026-09-24): on a phone, under CDP touch emulation and on the touchscreen laptop, on the chat modal, the feed and the
// Files pane, in both themes, each frame read from the tap until the element settles (a frame about every 33 ms, not every frame the
// compositor paints), the tap's pressed frames while it matches :active among them, paints the line at 3:1 or better, red on the phone
// over the sheets without their tap rule, where the browser's default tap highlight painted the control's pressed frames down to
// 2.531:1 in the frames read (2.22:1 dark and 2.41:1 light in a screencast of every frame), and the mark's cells and the other two
// devices' green there by design. The control in right-to-left text is read in cases of their own after those (the file review's round 15, ui-2): a
// picture from the web in a block an author wrote dir="rtl" and a local one in such a paragraph have their control over the
// picture's top-left corner, 6px in and inside the viewer's body, on the chat modal, the feed and the Files pane at 900px and
// 360px, red over the sheets' physical margins, where it stood 6px outside the picture's left edge and at 360px on the chat and
// the feed was clipped by 6px, while a picture in left-to-right text and a left and a right float in a right-to-left block keep
// theirs, controls green there by design. Red over
// the unchanged viewer at the first control assertion (no control exists), the outbound
// case red at the head before it, where the two controls presented one surface, and the link-shapes case red at the round-12
// head, where the title and the control read any anchor while the click did not, and the two under-the-floor cases red at that head too, the hover read and the at-rest read, where no rule dressed the picture. The one gate
// between every gesture and a web picture's tab is read in cases of their own at the file's end (the file review's round 16, extra5-1,
// with the coordinator's decisions 2 to 5 on it): a tap, a phone's tap, the laptop's finger, a click and a Ctrl-click on a picture
// whose control stands off the screen, Enter and Space on that control, a double click, a double tap (Chromium's, whose second tap's
// click carries detail 2) and held keys, the control under
// the Outline popover, the text-size flyout and an author's element, the mark, the anchors, the row, a local picture and a pinch zoom,
// each opening nothing where the sign is off the screen or covered and revealing it, the next gesture opening, the section's own
// header naming each cell's red; and the one gate's tap cells in Chromium (the file review's round 17, tests-1 with regression-1),
// the set file-figure-open-taps.ts holds and file-figure-open-engines-browser.test.ts runs in WebKit and Firefox, and its stacking
// cells in Chromium (the file review's round 17, extra9-1, and the coordinator's decision 4 on it), the set
// file-figure-open-stacking.ts holds and the same leg runs in WebKit and Firefox. The predicate that gate and the key gate read is read for its accuracy in cases of their own after
// those (the file review's round 16, regression-1 with the coordinator's decision 1, and fresh-1): the dashboard's pane wrapper in its
// narrow and touch layout and an author's span around the picture, on which overflow clips nothing, and a body zoom of 1.25, 0.8 and
// 14/13 beside the zoom-1 twins, the floor among them, the section's own header naming each cell's red. Skips LOUDLY without a playwright browser (in CI the Test step runs before the job's Chromium install, so the leg skips there; the launch is real-viewer-leg.ts's inBrowser, the shared helper). Synthetic values only: the notes-api world, a placeholder session id, example.invalid and example.test addresses,
// /repo/notes-api paths.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as http from "node:http";   // the outbound case's second server (the last test): a real origin of its own for the remote pictures
import * as zlib from "node:zlib";   // paintedRatio's PNG decode: the dress read off the real paint
import * as fs from "node:fs";       // the dashboard's pane wrapper, its rules read from kernel/kernel.py at run time (the predicate's cells)
import * as path from "node:path";
import { inBrowser, openViewer, openPanel, frames, topBlock, putAtTop, pageHtml, ROOT, REPORT, SID, PARA, ORIGIN } from "./real-viewer-leg";
import { phonePages, tapCells, type TapDevice as TapCellDevice, type TapSurface } from "./file-figure-open-taps";   // a phone's pages, and the one gate's tap cells, one set for the three engines
import { stackCells, type StackSurface } from "./file-figure-open-stacking";   // the one gate's stacking cells, one set for the three engines

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
const WEB_LINE = (origin: string): string => "Opens in a new tab: " + origin;   // the picture's own title line for the two click roads (file-view.ts figureWebTitleLine over shownAddress: the address's origin alone since the file review's round 15, extra9-2)
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
      assert.deepEqual([d[4].title, d[4].aria, d[4].web, d[4].imgTitle], ["Open the picture in a new tab at " + WEB_PORT_HOST, "Open the picture in a new tab at " + WEB_PORT_HOST, true, WEB_LINE(WEB_PORT)], "the ported address: the control's words name the host WITH its port and the picture's title carries the address with it (the file review's round 12, fresh-2: red under a .hostname read, which every fixture without a port left green; a property pin over the control's title property)");
      assert.ok(d[1].glyph && d[0].glyph && d[1].glyph !== d[0].glyph, "the outbound glyph differs from the local control's corner arrows");
      assert.match(d[1].glyph!, /<path /, "the outbound glyph draws a box"); assert.match(d[1].glyph!, /<line /, "with an arrow leaving it");
      assert.equal(d[2].glyph, d[1].glyph, "one outbound drawing for every web control"); assert.equal(d[3].glyph, d[1].glyph);
      assert.notEqual(d[1].borderStyle, d[0].borderStyle, "the sheets dress the web control apart from the local one: " + d[1].borderStyle + " vs " + d[0].borderStyle);
      // the picture itself: the address's origin on its own line after the author's title; the line alone with no author's title; the local one untouched
      assert.equal(d[1].imgTitle, AUTHOR_TITLE + "\n" + WEB_LINE(WEB), "the author's title kept, the address on its own line after it");
      assert.equal(d[2].imgTitle, WEB_LINE(WEB), "no author's title: the line alone");
      assert.equal(d[3].imgTitle, "Figure 4\n" + WEB_LINE(WEB), "the <picture>'s img carries the line for the candidate shown, the remote one, as its origin (on the local candidate at 600 px the line goes, below)");
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
      assert.deepEqual([w[3].title, w[3].web, w[3].imgTitle, w[3].glyph === w[1].glyph], [WEB_WORDS, true, "Figure 4\n" + WEB_LINE(WEB), true], "the web dress again");
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
        assert.equal(d[i].imgTitle, WEB_LINE(WEB), d[i].alt + ": the address line as the picture's title");
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
/** The neighbour pin's runs of f glued to a picture under the floor on both sides, upright, italic and bold italic (the margin ruling
 *  of 2026-09-24): the ink of an f reaches past its own box toward the picture, 1px for the upright one and up to 4px for the slanted
 *  ones at the viewer's default text size, on the chat modal and on the Files pane alike, so at a margin of the ring's width across the
 *  line the ring covered it. */
const GLYPH_RUNS = "Upright ffff![ngf](" + WEB + "/ngf.svg)ffff glued\n\nItalic *ffff*![ngi](" + WEB + "/ngi.svg)*ffff* glued\n\n"
  + "Bold italic ***ffff***![ngb](" + WEB + "/ngb.svg)***ffff*** glued\n\n";
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
  // a highlight and a table cell of an even row, two badges glued to each other, and runs of f glued to one on both sides, upright,
  // italic and bold italic, whose ink reaches past their own boxes toward the picture (the margin ruling of 2026-09-24)
  + "word![ngp](" + WEB + "/ngp.svg)word\n\n==ab![ngh](" + WEB + "/ngh.svg)cd==\n\n"
  + "| h1 | h2 |\n|---|---|\n| s | t |\n| q![ngt](" + WEB + "/ngt.svg)q | r |\n\n"
  + "![nb1](" + WEB + "/nb1.svg)![nb2](" + WEB + "/nb2.svg) badges\n\n" + GLYPH_RUNS + PARA(8) + "\n";
const TINY_DOCS: Record<string, string> = { [REPORT]: TINY_TEXT, [PLOT]: svg("#456") };
/** The tiny report's figures in order, and the second server's sizes for its remote pictures under the floor (20 by 20 each). */
const TINY_ALTS = ["local", "build", "big", "deadbare", "deadcap", "deadbuild", "hl", "th", "even", "conote", "ngp", "ngh", "ngt", "nb1", "nb2", "ngf", "ngi", "ngb"];
const TINY_SIZES: Record<string, [number, number]> = Object.fromEntries(["tiny", "deadtiny", "hl", "th", "even", "conote", "ngp", "ngh", "ngt", "nb1", "nb2", "ngf", "ngi", "ngb"].map((n) => ["/" + n + ".svg", [20, 20] as [number, number]]));
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
/** A neighbour pin scene: the alt of the picture whose ring is read, the scene, the neighbours the scene glues to the picture, and,
 *  for a picture set in smaller text than the run glued before it, the least and the most pixels of that run's ink the ring covers,
 *  the bound the sheets state for it (none: the ring covers no ink). */
type Scene = [string, string, string[], [number, number]?];
const GLUED = ["the glyph before it", "the glyph after it"];
/** The runs of f glued to a picture on both sides (GLYPH_RUNS), in the tiny report and in the Files pane report alike. */
const RUNS: Scene[] = [["ngf", "an upright f run", GLUED], ["ngi", "an italic f run", GLUED], ["ngb", "a bold italic f run", GLUED]];
/** The tiny report's scenes, read on the chat modal. */
const NEIGHBOURS: Scene[] = [["ngp", "a paragraph", GLUED], ["ngh", "a highlight", GLUED], ["ngt", "a table cell", GLUED], ["nb2", "two glued badges", ["the badge before it"]], ...RUNS];
/** The italic runs of f in a level-2 and a level-1 heading (HEADING_RUNS), where the reach of a slanted f past its own box grows with
 *  the heading's text (the second margin ruling of 2026-09-24). */
const HEADINGS: Scene[] = [["nh2", "an italic f run in a level-2 heading", GLUED], ["nh1", "an italic f run in a level-1 heading", GLUED]];
/** The bound the sheets state for a picture in smaller text than an italic or bold italic f glued before it: the margin across the
 *  line is 3px plus 0.3em of the PICTURE's own text size, short of that f's reach, so the ring covers some of its ink, at most 4
 *  pixels in one read at a device scale of 1 or 2, counted in device pixels (measured by screenshot pixels with the picture inside small, sub and sup, two nested
 *  small elements and text at 0.8em and 0.7em of the f's, in both themes, in the eleven configurations, at every text size from
 *  100% to 200% and with the line moved by each eighth of a pixel), and every dash still reads the token's own ratio, since the f
 *  stands before the picture and the ring paints over its ink. This scene reads 2 in both themes at 100% and at 150%. At least 1:
 *  the scene records the residual, so a margin that closes it reds here as one that widens it does, and the sentences that state
 *  it are reworded: red at 3px plus 0.6em across the line, where it reads 0, and at 3px, where it reads 12 at 100% and 17 at 150%.
 *  Text smaller than 0.7em of the f's is FLOOR_BOUND's. */
const SMALLER_BOUND: [number, number] = [1, 4];
/** The bound the sheets state below 0.7em of the f's, at the floor, for an f in the paragraph's own text (the file review's round 15,
 *  extra5-3, a residual disclosed and measured): Chromium sets no floor on a nested small element's text size, which falls by 1.2 a
 *  level to 3.6e-7px a hundred deep at 200% (1.8e-7px at 100%), so the margin across the line falls to the ring's own 3px, where
 *  0.3em is under a layout unit, and the ring covers the most of an italic or bold italic f glued before the picture there, most
 *  with the picture lowered by a sub inside the deepest. Measured by screenshot pixels over 24,576 reads (the Files pane and the chat
 *  modal under touch, device scales 1 and 2, both themes, text sizes 100% to 200% in the viewer's steps, the line moved by each
 *  eighth of a pixel; small elements nested 3 to 16, 20, 30, 40, 60 and 100 deep, sub and sup inside the deepest, font elements of
 *  size 1, 2 and 3 with sub and sup inside each), the worst read with the f in the paragraph's text is this scene's, a bold italic
 *  run before a picture in sub inside a hundred nested small elements, at 200%: 30 pixels at a device scale of 1 and 102 device
 *  pixels at 2, sampled maxima, since the count moves with the subpixel position. Every dash still reads 4.83:1 dark and 4.90:1
 *  light, and no read covers ink past the margin box. FLOOR_BOUND is read in PANE_NEIGHBOURS at 100% and 150% and once more at 200%,
 *  where that maximum was read; the Files pane reads 29 there at the line's own position, the 30 at a quarter to half a pixel along.
 *  A larger f, in a heading, a font element or a big one, covers more: FLOOR_LARGE_BOUND. At least 1, so the row records the
 *  residual both ways, as SMALLER_BOUND does. */
const FLOOR_BOUND: [number, number] = [1, 30];
/** The bound below 0.7em of the f's at the floor for an f LARGER than the paragraph's text (a verifier of the fixes for the
 *  file review's round 15 found that the first sweep read the paragraph's f alone): over 39,936 more reads by screenshot pixels, the same
 *  configurations with the whole line inside a level-1 to level-6 heading, a font element of size 4 to 7 or one to three nested big
 *  elements, the picture 20 by 20 in two nested small elements or at the floor with a sub or a sup inside the deepest, the worst read
 *  is 40 pixels at a device scale of 1, the scene of this row among those at it, an italic run in a level-2 heading at 150% on the
 *  Files pane at the line's own position (a bold italic f in a big element or a level-3 heading reads it too, at 130% to 175%), and
 *  135 device pixels at 2 (FLOOR_D2_BOUND), every dash still at 4.83:1 dark and 4.90:1 light and none past the margin box. Read in
 *  PANE_NEIGHBOURS at 100% (21) and 150% (40, the configuration of that maximum) and at 200% (22). The count stops growing with the f
 *  near an f of 33px because a 20 by 20 picture's ring reaches no higher than its top; a picture under the floor on its width
 *  alone can be any height, and beside a taller one the count grows with the f without a bound (204 pixels at a device scale of 1
 *  and 753 device pixels at 2 for a bold italic f of 185px, ten nested big elements at 200%, beside a picture 20 by 200, and nested
 *  big elements grow the f without end), which the sheets state and no row holds. */
const FLOOR_LARGE_BOUND: [number, number] = [1, 40];
const FLOOR_LARGE_SCENE = "an italic f run in a level-2 heading glued to a picture inside a hundred nested small elements, the margin across the line at the ring's 3px";
/** The bound at a device scale of 2 below 0.7em of the f's, in device pixels (ringInkDevicePixels): the worst read of both sweeps
 *  there, a bold italic run in a big element before a picture in sup inside a hundred nested small elements, on the chat modal at
 *  200% at the line's own position, 135 device pixels in both themes; the paragraph's own f read at most 102 there. At least 1. */
const FLOOR_D2_BOUND: [number, number] = [1, 135];
const FLOOR_SCENE = "a bold italic f run glued to a picture in sub inside a hundred nested small elements, the margin across the line at the ring's 3px (the floor)";
/** The Files pane report's scenes (PANE_TEXT): the runs, the heading runs, a left-floated picture in a note callout, the text it
 *  wraps starting at its margin box, where at a horizontal margin of the ring's width the dash's outer side read that text's first
 *  glyph, an italic run glued to a picture in two nested small elements (SMALLER_RUN), held to SMALLER_BOUND, a bold italic run
 *  glued to a picture in sub inside a hundred nested small elements (FLOOR_RUN), held to FLOOR_BOUND, and an italic run in a level-2
 *  heading glued to a picture inside a hundred nested small elements (FLOOR_LARGE_RUN), held to FLOOR_LARGE_BOUND. */
const PANE_NEIGHBOURS: Scene[] = [...RUNS, ...HEADINGS, ["cfloat", "a left float in a note callout", ["the glyph after it"]],
  ["nss", "an italic f run glued to a picture in two nested small elements", GLUED, SMALLER_BOUND], ["nfl", FLOOR_SCENE, GLUED, FLOOR_BOUND],
  ["nfh", FLOOR_LARGE_SCENE, GLUED, FLOOR_LARGE_BOUND]];
/** The ring covers no neighbouring ink at the picture's own text size, and the ink of a run glued before a picture in smaller text
 *  only within the scene's bound, and the dash beside a neighbour reads 3:1 on both sides (the file review's round 14,
 *  correctness-2 with extra5-1 and extra5-2, and the margin ruling of 2026-09-24): a box-shadow takes no layout and paints with the
 *  picture in tree order, so the ring covers whatever stands before the picture within its width, and text painted after the picture
 *  paints over the ring, where the dash's outer side reads that text. For each scene the clip around the picture and its neighbours
 *  (the glyph glued before it and the one glued after it, found through any element holding them, or the badge glued before the
 *  second badge) is shot three times: as painted, with every mark's box-shadow overridden to none (the page without the ring, the
 *  margin kept, so nothing moves), and with the ring off and the text of the picture's parent element transparent (the page without
 *  that text's ink). A picture that is the only child of inline elements (two nested small elements) is read through the
 *  outermost: its siblings are the neighbours and its parent holds the text. A neighbour fails when a pixel whose centre lies
 *  inside its rect changes with the ring, or an ink pixel of it
 *  does (a pixel of the ring-off shot more than 24 off the rect's modal colour on a channel); the scene fails when the ring covers
 *  any ink of that text anywhere in the clip (a pixel the ring changes where the ring-off and ink-off shots differ), which reads the
 *  ink a glyph paints past its own box toward the picture, an f's hook or a slanted run's last letter; and when the mark's worst
 *  dash-to-ring read (paintedRatio's mark branch: every dash pixel against the pixel one step in and one step out, and against every
 *  gap) is under 3:1, which reads text painted after the picture in the ring's outer pixel. Guards: the picture wears the mark's
 *  outline as it is read (on hover, the pointer over it, `hover` true; at rest otherwise), each neighbour is found, and the overrides
 *  take the ring off (the picture's computed box-shadow none under them) and move nothing. With a margin of the ring's width on every
 *  side, 56aedf384's, the runs of f red by the ink the ring covers and the Files pane's float by its dash, 2.06:1 dark and 2.91:1
 *  light; at a fixed 7px across the line, 5f147e582's, the heading runs red by the ink the ring covers, and at 150% the italic and
 *  bold italic runs. A scene with a bound (SMALLER_BOUND and FLOOR_BOUND, a picture in smaller text than the run glued before it)
 *  fails when the ink the ring covers anywhere in the clip falls outside it, not when there is any, the glyph after it and its dash
 *  read as above; the glyph before it is that run's, whose ink inside its box is part of the residual the bound counts, not a
 *  failure of its own (at the floor, FLOOR_BOUND's scene, the ring reaches the pixels at the edge of that glyph's box: the file
 *  review's round 15, extra5-3). Each failure is pushed onto `fails`, each read handed to `note`; the scroll is restored. */
async function ringCoversNoNeighbour(page: any, where: string, fails: string[], note: (m: string) => void, hover = false, scenes: Scene[] = NEIGHBOURS): Promise<void> {
  type Rect = { left: number; top: number; right: number; bottom: number };
  await page.mouse.move(5, 5);
  const top = await page.evaluate(() => (document.querySelector(".fileview-body") as HTMLElement).scrollTop);
  for (const [alt, scene, want, bound] of scenes) {
    const layout = (scroll: boolean): Promise<{ img: Rect; near: Record<string, Rect>; outline: string; shadow: string; hovered: boolean }> => page.evaluate(([alt, scroll, want]: [string, boolean, string[]]) => {
      const img = Array.from(document.querySelectorAll(".fileview-md img")).find((x) => x.getAttribute("alt") === alt) as HTMLElement;
      if (scroll) img.scrollIntoView({ block: "center" });
      const box = (r: DOMRect) => ({ left: r.left, top: r.top, right: r.right, bottom: r.bottom });
      /** The letter at the picture's side of a sibling: its last letter before the picture, its first after, through any element holding it. */
      const glyph = (node: Node | null, last: boolean) => {
        while (node && node.nodeType === 1 && (node as Element).localName !== "img") node = last ? node.lastChild : node.firstChild;
        if (!node || node.nodeType !== 3 || !(node as Text).length) return null;
        const t = node as Text; const r = document.createRange(); r.setStart(t, last ? t.length - 1 : 0); r.setEnd(t, last ? t.length : 1); return box(r.getBoundingClientRect());
      };
      const near: Record<string, { left: number; top: number; right: number; bottom: number }> = {};
      // the picture read through the inline elements it is the only child of, so its neighbours are their siblings
      let host: Element = img; while (host.parentElement && getComputedStyle(host.parentElement).display === "inline" && host.parentElement.childNodes.length === 1) host = host.parentElement;
      const b = host.previousSibling;
      if (want.includes("the badge before it") && b && b.nodeType === 1 && (b as Element).localName === "img") near["the badge before it"] = box((b as Element).getBoundingClientRect());
      const g = want.includes("the glyph before it") ? glyph(b, true) : null; if (g) near["the glyph before it"] = g;
      const a = want.includes("the glyph after it") ? glyph(host.nextSibling, false) : null; if (a) near["the glyph after it"] = a;
      const cs = getComputedStyle(img);
      return { img: box(img.getBoundingClientRect()), near, outline: cs.outlineStyle, shadow: cs.boxShadow, hovered: img.matches(":hover") };
    }, [alt, scroll, want]);
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
    assert.deepEqual(names, want, where + ": " + scene + ": the neighbours the scene glues to the picture are found");
    assert.deepEqual([lay.outline, lay.hovered], ["dashed", hover], where + ": " + scene + ": the picture wears the mark's outline as the pin reads it" + (hover ? ", the pointer over it" : ", at rest"));
    const rects = names.map((k) => [k, lay.near[k]] as [string, Rect]);
    const xs = [lay.img.left - 12, lay.img.right + 12, ...rects.flatMap(([, r]) => [r.left - 2, r.right + 2])], ys = [lay.img.top - 12, lay.img.bottom + 12, ...rects.flatMap(([, r]) => [r.top - 2, r.bottom + 2])];
    const cx = Math.max(0, Math.floor(Math.min(...xs))), cy = Math.max(0, Math.floor(Math.min(...ys))), cw = Math.ceil(Math.max(...xs)) - cx, ch = Math.ceil(Math.max(...ys)) - cy;
    const shot = async () => decodePng(await page.screenshot({ clip: { x: cx, y: cy, width: cw, height: ch } }));
    const withRing = await shot();
    await page.evaluate((alt: string) => {
      let host = Array.from(document.querySelectorAll(".fileview-md img")).find((x) => x.getAttribute("alt") === alt) as Element;
      while (host.parentElement && getComputedStyle(host.parentElement).display === "inline" && host.parentElement.childNodes.length === 1) host = host.parentElement;
      host.parentElement!.setAttribute("data-neighbour-line", "");
      const st = document.createElement("style"); st.id = "neighbour-pin-noring"; st.textContent = ".fileview-md img[data-fv-figweb] { box-shadow: none !important; }"; document.head.appendChild(st);
    }, alt);
    await frames(page, 3);
    const noRing = await shot();
    const still = await layout(false);
    await page.evaluate(() => { const st = document.createElement("style"); st.id = "neighbour-pin-noink"; st.textContent = "[data-neighbour-line], [data-neighbour-line] * { color: transparent !important; -webkit-text-fill-color: transparent !important; text-decoration-color: transparent !important; }"; document.head.appendChild(st); });
    await frames(page, 3);
    const noInk = await shot();
    const inkless = await layout(false);
    await page.evaluate(() => { document.getElementById("neighbour-pin-noink")!.remove(); document.getElementById("neighbour-pin-noring")!.remove(); document.querySelector("[data-neighbour-line]")!.removeAttribute("data-neighbour-line"); });
    await frames(page, 2);
    assert.deepEqual([still.img, still.hovered, still.shadow, inkless.img], [lay.img, hover, "none", lay.img], where + ": " + scene + ": the overrides take the ring off (the picture's computed box-shadow none under them), move nothing, and the pointer's state holds between the shots");
    const px = (png: { width: number; bpp: number; data: Buffer }, x: number, y: number) => { const k = ((y - cy) * png.width + (x - cx)) * png.bpp; return [png.data[k], png.data[k + 1], png.data[k + 2]]; };
    const same = (a: number[], b: number[]) => a[0] === b[0] && a[1] === b[1] && a[2] === b[2];
    let clipChanged = 0, covered = 0;
    const lost: string[] = [];
    for (let y = cy; y < cy + ch; y++) for (let x = cx; x < cx + cw; x++) {
      const a = px(withRing, x, y), b = px(noRing, x, y);
      if (same(a, b)) continue;
      clipChanged++;
      if (same(b, px(noInk, x, y))) continue;
      covered++;
      if (lost.length < 4) lost.push((x - Math.floor(lay.img.left)) + "," + (y - Math.floor(lay.img.top)) + " rgb(" + b.join(", ") + ") to rgb(" + a.join(", ") + ")");
    }
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
        if (same(a, b)) continue;
        const inside = x + 0.5 > r.left && x + 0.5 < r.right && y + 0.5 > r.top && y + 0.5 < r.bottom;
        if (inside) centre++;
        if (isInk) inkChanged++;
        if ((inside || isInk) && seen.length < 4) seen.push((x - x0) + "," + (y - y0) + " rgb(" + b.join(", ") + ") to rgb(" + a.join(", ") + ")");
      }
      const read = where + ": " + scene + ": " + k + " (" + (x1 - x0 + 1) * (y1 - y0 + 1) + " pixels, " + ink + " of them ink): " + centre + " changed with the centre inside, " + inkChanged + " ink pixels changed, the ring " + lay.shadow + ", " + clipChanged + " pixels of the clip changed by it";
      note("neighbour, " + read);
      // a scene with a bound is a picture in smaller text than the run glued BEFORE it: that run's ink the ring covers, inside its
      // glyph's box or past it, is the residual the bound counts (below), and the glyph after it still keeps all its ink
      if ((centre > 0 || inkChanged > 0) && !(bound && k === "the glyph before it")) fails.push(read + ": the ring covers neighbouring ink (" + seen.join("; ") + ")");
    }
    const inkRead = where + ": " + scene + ": " + covered + " pixels of the text's ink covered by the ring anywhere in the clip";
    note("neighbour, " + inkRead);
    // FAILS BEFORE (56aedf384, a margin of the ring's width on every side): the runs of f, the ink an f paints past its own box; and
    // at 5f147e582's fixed 7px across the line the heading runs, and at 150% the italic and bold italic runs
    if (!bound && covered > 0) fails.push(inkRead + ": the ring covers ink a neighbour paints past its own box (" + lost.join("; ") + ")");
    // a picture in smaller text than the run glued before it: the ink covered within the bound the sheets state, at least its least
    // (the residual recorded) and at most its most
    if (bound && (covered < bound[0] || covered > bound[1])) fails.push(inkRead + ": outside the bound the sheets state for a picture in smaller text than the run glued before it, " + bound[0] + " to " + bound[1] + " pixels" + (lost.length ? " (" + lost.join("; ") + ")" : ""));
    const p = await paintedRatio(page, alt, "mark", hover ? "hover" : "rest");
    const dashRead = where + ": " + scene + ": the mark paints " + p.dash + " over " + p.ground + ", " + p.ratio.toFixed(3) + ":1 (the worst read: " + p.at + ")";
    note("neighbour, " + dashRead);
    // FAILS BEFORE (56aedf384): the Files pane's float, its dash's outer side on the wrapped text's first glyph
    if (p.ratio < 3) fails.push(dashRead + ": under the 3:1 floor, a neighbour's ink in the ring beside the dash");
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
/** The tiny report open on `surface` (the chat modal unless named) at 900 by 600: the report's remote pictures relayed to the second
 *  server (`second`), the first local figure loaded, the fv-load click lifting the host, then every figure loaded and out of its
 *  placeholder; no control is waited for, since the badge gets none. Shared by the two under-the-floor cases, each on a page of its
 *  own: Chromium's (hover: none) follows touch emulation and does not revert, and the at-rest read must never follow a hover; the
 *  tap cases at the file's end open it on the feed and the Files pane too. */
async function openTiny(browser: any, second: { port: number }, surface: Surface = "chat"): Promise<{ page: any; errors: string[] }> {
  const before = async (pg: any): Promise<void> => {
    await pg.context().route((u: URL) => u.href.startsWith(WEB + "/"), async (route: any) => {
      const a = await fromSecond(second.port, new URL(route.request().url()).pathname);
      return route.fulfill({ status: a.status, contentType: a.type, body: a.body });
    });
  };
  const o = await openViewer(browser, surface, 900, 600, {
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
      assert.equal(badge.title, WEB_LINE(WEB), "the picture's own title carries the address, decided before the control's verdict (red when dressFigureTitle moves inside the control's branches)");
      assert.deepEqual([big.control, big.title, big.mark, big.outline], [true, WEB_LINE(WEB), false, "none"], "the loaded picture over the floor: its control and title, and no mark of its own (the mark's population is the title's less the pictures a control stands on)");
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
        // tint on both sides of the dashes), and the ring on hover covering no neighbouring ink at the picture's own text size with the
        // dash beside it at 3:1 (ringCoversNoNeighbour)
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
      assert.deepEqual(fails, [], "every state a click or a key opens the tab from inside a dead link, the press held included, and the mark on hover on the grounds of a highlight, a table header, an even row and a callout, on a fine pointer, paint the dress at 3:1, and the ring on hover covers no neighbouring ink at the picture's own text size, the dash beside it at 3:1 (a property pin read off the page):\n" + fails.join("\n"));
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
      assert.deepEqual([touch.imgs[1].control, touch.imgs[1].title], [false, WEB_LINE(WEB)], "the badge: no control under the floor, the address in its title");
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
      // the ring at rest covers no neighbouring ink at the picture's own text size, the dash beside it at 3:1 (the file review's
      // round 14, correctness-2 with extra5-1 and extra5-2, and the margin ruling of 2026-09-24)
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
      assert.deepEqual(fails, [], "every state a tap or a press opens the tab from paints the dress at 3:1, the VS Code bound is exact, and the ring at rest covers no neighbouring ink at the picture's own text size, the dash beside it at 3:1 (a property pin read off the page):\n" + fails.join("\n"));
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
      assert.deepEqual([rest.imgs[1].control, rest.imgs[1].title], [false, WEB_LINE(WEB)], "the badge: no control under the floor, the address in its title");
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

// ── the ring's neighbour pin on the Files pane ─────────────────────────────────────────────────────────────────────────────────
// (the margin ruling of 2026-09-24, on the file review's round 14, correctness-2 with extra5-1 and extra5-2) The margin keeps the ring
// off the neighbours on each axis by what they need: across the line, the ink a glyph set in the picture's own text size paints past
// its own box toward the picture (an f's hook, a slanted run's last letter) and the text a float wraps, which starts at the float's
// margin box and paints after the picture; up and down, the lines above and below. At a margin of the ring's width on every side the
// runs of f lost that ink to the
// ring and the text a note callout wraps beside a left-floated picture painted its first glyph in the ring's outer pixel, where the
// dash's outer side read it at 2.06:1 dark and 2.91:1 light on the Files pane. The pane's report holds the runs of f the tiny report
// holds and that float, its words those it wrapped then. Since the second margin ruling of 2026-09-24 the margin across the line is
// 3px plus 0.3em of the picture's own text size, since the reach of a slanted f past its own box grows with the text: at a fixed 7px,
// 5f147e582's, an italic f glued to the picture lost ink to the ring in a level-2 heading (clear at 8px) and a level-1 heading (clear at
// 10px), and the italic and bold italic runs lost ink at a text size of 150%. So the report holds the heading runs too, and the case
// reads every scene again at 150%, the size stepped by the viewer's own control. The em is the picture's own, so a picture in smaller
// text than an italic f glued before it gets less margin than that f's reach needs: the report holds one inside two nested small
// elements after an italic run, whose ink the ring covers within the bound the sheets state (SMALLER_BOUND), read at both sizes.
const FLOAT_WORDS = "Tall words wrap around the floated picture here and deep gjpqy words ";
/** An italic run of f glued to a picture under the floor on both sides in a level-2 heading and in a level-1 heading. */
const HEADING_RUNS = "## Heading *ffff*![nh2](" + WEB + "/nh2.svg)*ffff* glued\n\n# Title *ffff*![nh1](" + WEB + "/nh1.svg)*ffff* glued\n\n";
/** An italic run of f glued on both sides to a picture under the floor inside two nested small elements, text 0.694 of the run's. */
const SMALLER_RUN = "Smaller *ffff*<small><small>![nss](" + WEB + "/nss.svg)</small></small>*ffff* glued\n\n";
/** A bold italic run of f glued on both sides to a picture under the floor in sub inside a hundred nested small elements, the
 *  worst scene the sweep below 0.7em read (FLOOR_BOUND), spelled as the sweep spelled it. */
const FLOOR_RUN = "Bold italic ***ffff***" + "<small>".repeat(100) + "<sub>![nfl](" + WEB + "/nfl.svg)</sub>" + "</small>".repeat(100) + "***ffff*** glued\n\n";
/** An italic run of f in a level-2 heading glued on both sides to a picture under the floor inside a hundred nested small elements,
 *  the worst scene the sweep of larger f's read at a device scale of 1 (FLOOR_LARGE_BOUND), spelled as that sweep spelled it. */
const FLOOR_LARGE_RUN = "## Italic *ffff*" + "<small>".repeat(100) + "![nfh](" + WEB + "/nfh.svg)" + "</small>".repeat(100) + "*ffff* glued\n\n";
const PANE_TEXT = "# Report\n\n" + PARA(1) + "\n\n" + GLYPH_RUNS + HEADING_RUNS + SMALLER_RUN + FLOOR_RUN + FLOOR_LARGE_RUN
  + "> [!note]\n> " + '<img src="' + WEB + '/cfloat.svg" alt="cfloat" align="left">' + "jTW " + FLOAT_WORDS.repeat(5) + "\n\n" + PARA(2) + "\n";
/** The viewer's text size stepped up `n` times by its own control: the zoom glyph opens the flyout, A+ takes one step of the table. */
async function stepTextSizeUp(page: any, n: number): Promise<void> {
  for (let i = 0; i < n; i++) {
    if (await page.evaluate(() => (document.querySelector(".fileview-zoom-menu") as HTMLElement).hidden)) await page.click(".fileview-zoom-btn");
    await page.locator(".fileview-zoom-menu .fileview-size", { hasText: "A+" }).click();
    await frames(page, 3);
  }
}
test("in a browser, under CDP touch emulation on the Files pane, the ring's neighbour pin: runs of f glued to a remote picture under the floor on both sides, upright, italic and bold italic, and italic runs in a level-2 and a level-1 heading keep all their ink, the ink past their own boxes too, and a left-floated one in a note callout, the text it wraps starting at its margin box, reads its dash at 3:1 or better on both sides, and an italic run glued to one inside two nested small elements loses 1 to 4 pixels of ink to the ring, the bound the sheets state for a picture in smaller text than the f before it, and a bold italic run glued to one in a sub inside a hundred nested small elements, the floor below 0.7em of the f's, 1 to 30 pixels, the residual the sheets state there (the file review's round 15, extra5-3; read at 200% too, the configuration of that maximum), and an italic run in a level-2 heading glued to one inside a hundred nested small elements, the larger f's floor, 1 to 40 pixels (its maximum read in the 150% pass), each dash at 3:1 or better, in both themes, at the viewer's default text size and at 150% (ringCoversNoNeighbour; the margin ruling of 2026-09-24: at a margin of the ring's width on every side the runs lost the ink past their boxes to the ring and the float's dash read its wrapped text's first glyph at 2.06:1 dark and 2.91:1 light; the second margin ruling that day: at a fixed 7px across the line the heading runs lost ink to the ring, and at 150% the italic and bold italic runs; a property pin read off the page)", { timeout: 240000 }, async (t) => {
  const second = await secondServer([], Object.fromEntries(["ngf", "ngi", "ngb", "nh2", "nh1", "cfloat", "nss", "nfl", "nfh"].map((n) => ["/" + n + ".svg", [20, 20] as [number, number]])));
  try {
    await inBrowser(t, async (browser) => {
      const before = async (pg: any): Promise<void> => {
        await pg.context().route((u: URL) => u.href.startsWith(WEB + "/"), async (route: any) => {
          const a = await fromSecond(second.port, new URL(route.request().url()).pathname);
          return route.fulfill({ status: a.status, contentType: a.type, body: a.body });
        });
      };
      const { page, errors } = await openViewer(browser, "pane", 900, 600, { docs: { [REPORT]: PANE_TEXT }, before });
      await page.click('[data-act="fv-load"]');
      await page.waitForFunction(() => { const imgs = Array.from(document.querySelectorAll(".fileview-md img")) as HTMLImageElement[]; return imgs.length === 9 && imgs.every((i) => i.complete && i.naturalWidth > 0 && i.hasAttribute("data-fv-figweb")); }, null, { timeout: 10000 });
      const cdp = await page.context().newCDPSession(page);
      await cdp.send("Emulation.setTouchEmulationEnabled", { enabled: true, maxTouchPoints: 1 });
      await frames(page, 3);
      const float = await page.evaluate(() => getComputedStyle(Array.from(document.querySelectorAll(".fileview-md img")).find((x) => x.getAttribute("alt") === "cfloat")!).float);
      assert.equal(float, "left", "the callout's picture is floated left (the scene)");
      const fails: string[] = [];
      for (const theme of ["dark", "light"] as const) {
        await page.evaluate((light: boolean) => document.body.classList.toggle("theme-light", light), theme === "light");
        await frames(page, 3);
        await ringCoversNoNeighbour(page, theme + " theme, at rest under touch emulation on the Files pane", fails, (m) => t.diagnostic(m), false, PANE_NEIGHBOURS);
      }
      // the text size at 150%, three steps of the viewer's own control from its default, the picture's own text size with it (the
      // margin across the line is 3px plus 0.3em of it)
      const sizeOf = () => page.evaluate(() => [(document.querySelector(".fileview") as HTMLElement).dataset.fvText, parseFloat(getComputedStyle(Array.from(document.querySelectorAll(".fileview-md img")).find((x) => x.getAttribute("alt") === "ngi")!).fontSize)]);
      const [pct100, font100] = await sizeOf();
      await stepTextSizeUp(page, 3);
      const [pct150, font150] = await sizeOf();
      assert.deepEqual([pct100, pct150, Math.round((font150 as number) / (font100 as number) * 100)], ["100", "150", 150], "the viewer's own control steps the text size from 100% to 150% in three steps, and the picture's text size with it (" + font100 + "px to " + font150 + "px)");
      for (const theme of ["dark", "light"] as const) {
        await page.evaluate((light: boolean) => document.body.classList.toggle("theme-light", light), theme === "light");
        await frames(page, 3);
        await ringCoversNoNeighbour(page, theme + " theme, at a text size of 150%, at rest under touch emulation on the Files pane", fails, (m) => t.diagnostic(m), false, PANE_NEIGHBOURS);
      }
      // the configuration of the paragraph's f's maximum at a device scale of 1 below 0.7em (FLOOR_BOUND's 30 pixels, read on the Files
      // pane under touch at 200% in both themes; the larger f's maximum, FLOOR_LARGE_BOUND's 40, is the 150% pass's): two more steps
      // of the viewer's own control, the two floor scenes alone
      await stepTextSizeUp(page, 2);
      const [pct200, font200] = await sizeOf();
      const floorMargin = await page.evaluate(() => getComputedStyle(Array.from(document.querySelectorAll(".fileview-md img")).find((x) => x.getAttribute("alt") === "nfl")!).marginLeft);
      t.diagnostic("the floor's picture at 200%: its margin across the line " + floorMargin + " (the ring's 3px under the sheets' rule)");
      assert.deepEqual([pct200, Math.round((font200 as number) / (font100 as number) * 100)], ["200", 200], "two more steps take the text size to 200%, the configuration of the maximum (" + font200 + "px)");
      for (const theme of ["dark", "light"] as const) {
        await page.evaluate((light: boolean) => document.body.classList.toggle("theme-light", light), theme === "light");
        await frames(page, 3);
        await ringCoversNoNeighbour(page, theme + " theme, at a text size of 200%, the configuration of the maximum, at rest under touch emulation on the Files pane", fails, (m) => t.diagnostic(m), false, PANE_NEIGHBOURS.filter(([alt]) => alt === "nfl" || alt === "nfh"));
      }
      await page.evaluate(() => document.body.classList.remove("theme-light"));
      assert.deepEqual(errors, [], "no page errors");
      await page.close();
      assert.deepEqual(fails, [], "the ring covers no ink of the runs of f, in a paragraph and in both headings, at the default text size and at 150%, the float's dash reads 3:1 on both sides, and the run before a picture in smaller text loses ink within the bound the sheets state, at the floor too, for the paragraph's f and a heading's, at 100%, 150% and 200%, its dash at 3:1 (a property pin read off the page):\n" + fails.join("\n"));
    });
  } finally { await second.close(); }
});

// ── the ring's line pin at a device scale of 2 ─────────────────────────────────────────────────────────────────────────────────
// (the second margin ruling of 2026-09-24, on the file review's round 14, correctness-2 with extra5-1 and extra5-2) Up and down, the
// margin keeps the ring off the lines above and below: 3px, the ring's width, so the ring stands inside the picture's margin box on
// every side, and the line holding the picture holds that box. Read at a device scale of 2, where a layout edge can fall on half a
// CSS pixel, on the chat modal under touch emulation: with no margin up and down the ring covered the bottom of an inline code span's
// box on a line of descenders above the picture, and at 1px it still did; at 2px it covered the bottom row of a key on the line above,
// whose box reaches its line's edge, and painted the page's ground one CSS pixel past the margin box over the tint of a note callout,
// an even table row and a highlight the picture stands in; at 3px none of it.
const LINES_TEXT = "# Report\n\n" + PARA(1) + "\n\n"
  + "gjpqy `gjpqy code gjpqy` gjpqy<br>Words ![vchip](" + WEB + "/vchip.svg) words\n\n"
  + "<kbd>Ctrl gjpqy</kbd><kbd>Shift gjpqy</kbd><kbd>K</kbd><br>Words ![vkey](" + WEB + "/vkey.svg) words\n\n"
  + "> [!note]\n> Words ![vcallout](" + WEB + "/vcallout.svg) words\n\n"
  + "| a |\n|---|\n| x |\n| Words ![vrow](" + WEB + "/vrow.svg) words |\n\n"
  + "A sentence ==Words ![vhl](" + WEB + "/vhl.svg) words== highlighted.\n\n" + PARA(2) + "\n";
/** A line pin scene: the alt of the picture whose ring is read, the scene, and what it holds: "ink", paint on the line above standing
 *  near the picture, of which the ring must cover none; "tint", a tinted ground the picture stands in, over which the ring must paint
 *  no pixel past the picture's margin box. */
type LineScene = [string, string, "ink" | "tint"];
const LINE_SCENES: LineScene[] = [
  ["vchip", "a line of descenders holding an inline code span above the picture", "ink"], ["vkey", "a line of keys above the picture", "ink"],
  ["vcallout", "a note callout's tint", "tint"], ["vrow", "an even table row's tint", "tint"], ["vhl", "a highlight's tint", "tint"],
];
/** The ring stands clear of the lines above and below (the second margin ruling of 2026-09-24), read by screenshot pixels at the
 *  page's device scale `k`. For each scene the clip around the picture is shot three times: as painted, with every mark's box-shadow
 *  overridden to none (the ring off, the margin kept, so nothing moves), and with the ring off and the paint of the picture's block
 *  taken off but for the picture and its own ancestors, whose tint stays (the block's text transparent, and every other element's
 *  background, border and box-shadow gone, so a code span's box and a key's are ink here as their glyphs are). The picture is located
 *  by its own fill in the painted shot (the paint's snapping can differ from the layout rect's rounding at a device scale of 2); the
 *  ring's rect is that box grown by the computed box-shadow's spread, the margin box that box grown by the computed margins, in device
 *  pixels. A scene fails when the ring covers ink (a pixel of the ring's rect outside the picture that the ring changes where the
 *  ring-off and paint-off shots differ at all) and when the ring paints past the margin box (a pixel of the ring's rect outside the
 *  margin box that the ring changes, over a tinted ground the page's ground painted on the tint). Guards: the page's device scale is
 *  `k`; the picture wears the mark's outline at rest and a ring; the overrides take the ring off and move nothing; an "ink" scene's
 *  paint stands within 6 CSS px above the picture, so the scene holds a neighbour for the ring to reach; a "tint" scene's ground in
 *  the ring's rect is not the page's own, so it holds a tint for the ring to paint over. At 2px up and down the key's scene reds by the
 *  ink covered and the tints by the pixels past the margin box; at 1px the code span's scene reds too. Each failure is pushed onto
 *  `fails`, each read handed to `note`; the scroll is restored. */
async function ringClearsTheLines(page: any, where: string, fails: string[], note: (m: string) => void, k: number, scenes: LineScene[] = LINE_SCENES): Promise<void> {
  type Rect = { left: number; top: number; right: number; bottom: number };
  await page.mouse.move(5, 5);
  const top = await page.evaluate(() => (document.querySelector(".fileview-body") as HTMLElement).scrollTop);
  for (const [alt, scene, holds] of scenes) {
    const layout = (scroll: boolean): Promise<{ img: Rect; margin: number[]; outline: string; shadow: string; bg: string; dpr: number }> => page.evaluate(([alt, scroll]: [string, boolean]) => {
      const img = Array.from(document.querySelectorAll(".fileview-md img")).find((x) => x.getAttribute("alt") === alt) as HTMLElement;
      if (scroll) img.scrollIntoView({ block: "center" });
      const r = img.getBoundingClientRect(), cs = getComputedStyle(img);
      const probe = document.createElement("span"); probe.style.color = "var(--bg)"; img.parentElement!.appendChild(probe); const bg = getComputedStyle(probe).color; probe.remove();
      return { img: { left: r.left, top: r.top, right: r.right, bottom: r.bottom }, margin: [cs.marginTop, cs.marginRight, cs.marginBottom, cs.marginLeft].map(parseFloat), outline: cs.outlineStyle, shadow: cs.boxShadow, bg, dpr: window.devicePixelRatio };
    }, [alt, scroll]);
    await layout(true);
    await frames(page, 2);
    const lay = await layout(false);
    const spread = /(-?[\d.]+)px$/.exec(lay.shadow.trim());
    assert.deepEqual([lay.dpr, lay.outline, !!spread && Number(spread[1]) > 0], [k, "dashed", true], where + ": " + scene + ": the page's device scale is " + k + " and the picture wears the mark's outline at rest over a ring (" + lay.shadow + ")");
    const ringPx = Number(spread![1]);
    const m = lay.margin;
    const cx = Math.max(0, Math.floor(lay.img.left - m[3] - 12)), cy = Math.max(0, Math.floor(lay.img.top - m[0] - 12));
    const cw = Math.ceil(lay.img.right + m[1] + 12) - cx, ch = Math.ceil(lay.img.bottom + m[2] + 12) - cy;
    const shot = async () => decodePng(await page.screenshot({ clip: { x: cx, y: cy, width: cw, height: ch } }));
    const withRing = await shot();
    await page.evaluate((alt: string) => {
      const img = Array.from(document.querySelectorAll(".fileview-md img")).find((x) => x.getAttribute("alt") === alt) as HTMLElement;
      let blk = img.parentElement!; while (blk.parentElement && !/^(block|list-item|table-cell|flow-root)$/.test(getComputedStyle(blk).display)) blk = blk.parentElement;
      blk.setAttribute("data-line-pin-block", "");
      for (let e: HTMLElement | null = img.parentElement; e && e !== blk; e = e.parentElement) e.setAttribute("data-line-pin-anc", "");
      const st = document.createElement("style"); st.id = "line-pin-noring"; st.textContent = ".fileview-md img[data-fv-figweb] { box-shadow: none !important; }"; document.head.appendChild(st);
    }, alt);
    await frames(page, 3);
    const noRing = await shot();
    const still = await layout(false);
    await page.evaluate(() => {
      const st = document.createElement("style"); st.id = "line-pin-nopaint";
      st.textContent = "[data-line-pin-block], [data-line-pin-block] * { color: transparent !important; -webkit-text-fill-color: transparent !important; text-decoration-color: transparent !important; }"
        + " [data-line-pin-block] *:not(img):not([data-line-pin-anc]) { background: transparent !important; border-color: transparent !important; box-shadow: none !important; }";
      document.head.appendChild(st);
    });
    await frames(page, 3);
    const noPaint = await shot();
    const bare = await layout(false);
    await page.evaluate(() => {
      document.getElementById("line-pin-nopaint")!.remove(); document.getElementById("line-pin-noring")!.remove();
      for (const e of Array.from(document.querySelectorAll("[data-line-pin-block], [data-line-pin-anc]"))) { e.removeAttribute("data-line-pin-block"); e.removeAttribute("data-line-pin-anc"); }
    });
    await frames(page, 2);
    assert.deepEqual([still.img, still.shadow, bare.img], [lay.img, "none", lay.img], where + ": " + scene + ": the overrides take the ring off (the picture's computed box-shadow none under them) and move nothing");
    const W = withRing.width, H = withRing.height;
    const px = (png: { bpp: number; data: Buffer }, x: number, y: number) => { const i = (y * W + x) * png.bpp; return [png.data[i], png.data[i + 1], png.data[i + 2]]; };
    const diff = (a: number[], b: number[]) => Math.max(Math.abs(a[0] - b[0]), Math.abs(a[1] - b[1]), Math.abs(a[2] - b[2]));
    // the picture's own fill (#333, the second server's), located in the painted shot within 3 device pixels of its layout rect
    const e = { l: Math.round((lay.img.left - cx) * k), t: Math.round((lay.img.top - cy) * k), r: Math.round((lay.img.right - cx) * k), b: Math.round((lay.img.bottom - cy) * k) };
    let L = Infinity, T = Infinity, R = -Infinity, B = -Infinity;
    for (let y = Math.max(0, e.t - 3); y < Math.min(H, e.b + 3); y++) for (let x = Math.max(0, e.l - 3); x < Math.min(W, e.r + 3); x++) if (diff(px(withRing, x, y), [0x33, 0x33, 0x33]) <= 2) { L = Math.min(L, x); T = Math.min(T, y); R = Math.max(R, x + 1); B = Math.max(B, y + 1); }
    assert.ok(R - L === e.r - e.l && B - T === e.b - e.t, where + ": " + scene + ": the picture's fill is found at its layout size (" + (R - L) + " by " + (B - T) + " device pixels, the layout " + (e.r - e.l) + " by " + (e.b - e.t) + ")");
    const ring = { l: L - Math.round(ringPx * k), t: T - Math.round(ringPx * k), r: R + Math.round(ringPx * k), b: B + Math.round(ringPx * k) };
    const box = { l: L - Math.round(m[3] * k), t: T - Math.round(m[0] * k), r: R + Math.round(m[1] * k), b: B + Math.round(m[2] * k) };
    const bgc = (lay.bg.match(/\d+/g) || []).slice(0, 3).map(Number);
    let covered = 0, past = 0, tinted = 0, inkAbove = -Infinity;
    const seen: string[] = [];
    for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
      const a = px(withRing, x, y), b = px(noRing, x, y), c = px(noPaint, x, y);
      const inRing = x >= ring.l && x < ring.r && y >= ring.t && y < ring.b, inPic = x >= L && x < R && y >= T && y < B;
      const ink = diff(b, c) > 0;
      if (ink && diff(b, c) > 2 && y < T && x >= ring.l && x < ring.r) inkAbove = Math.max(inkAbove, y);
      if (!inRing || inPic) continue;
      if (diff(b, bgc) > 8) tinted++;
      if (diff(a, b) === 0) continue;
      const inBox = x >= box.l && x < box.r && y >= box.t && y < box.b;
      if (ink) covered++;
      if (!inBox) past++;
      if ((ink || !inBox) && seen.length < 4) seen.push((x - L) + "," + (y - T) + " rgb(" + b.join(", ") + ") to rgb(" + a.join(", ") + ")" + (ink ? " ink" : "") + (inBox ? "" : " past the margin box"));
    }
    const gapAbove = inkAbove === -Infinity ? null : (T - 1 - inkAbove) / k;
    const read = where + ": " + scene + ": the ring " + lay.shadow + ", the margin " + m.join("/") + "px: " + covered + " device pixels of ink covered, " + past + " past the margin box" + (holds === "ink" ? ", the nearest paint above " + gapAbove + " CSS px from the picture" : ", " + tinted + " of the ring's pixels over a tint");
    note("line, " + read);
    if (holds === "ink") assert.ok(gapAbove !== null && gapAbove <= 6, where + ": " + scene + ": the line above holds paint within 6 CSS px of the picture (" + gapAbove + "), a neighbour for the ring to reach");
    else assert.ok(tinted > 0, where + ": " + scene + ": the ground under the ring is a tint, not the page's own (" + tinted + " pixels)");
    // FAILS BEFORE (2px up and down): the key's scene by the ink covered, the tints by the pixels past the margin box; at 1px the code span's scene too
    if (covered > 0 || past > 0) fails.push(read + ": the ring reaches the lines above and below (" + seen.join("; ") + ")");
  }
  await page.mouse.move(5, 5);
  await page.evaluate((y: number) => { (document.querySelector(".fileview-body") as HTMLElement).scrollTop = y; }, top);
  await frames(page, 2);
}
/** The ink the ring covers around one picture under the floor, counted in DEVICE pixels at a device scale of `k` (the file review's
 *  round 15, extra5-3, read at the device scale where the sweep below 0.7em found its maximum there: ringCoversNoNeighbour and
 *  paintedRatio index a screenshot one pixel per CSS pixel, so neither reads a page at a device scale of 2). A clip 40 CSS px round
 *  the picture, the run glued before it inside, is shot three times: as painted, with every mark's box-shadow overridden to none (the
 *  page without the ring, the margin kept, so nothing moves), and with the ring off and the text of the picture's line transparent
 *  (the page without that text's ink). A device pixel counts where the ring changes it and the ring-off shot differs from the
 *  ink-off one, as the sweep counted. Guards: the page's device scale is `k`, the picture wears the mark's outline at rest over a
 *  ring, and the overrides take the ring off and move nothing. Returns the count, each read handed to `note`. */
async function ringInkDevicePixels(page: any, alt: string, k: number, where: string, note: (m: string) => void): Promise<number> {
  await page.mouse.move(5, 5);
  const layout = (scroll: boolean): Promise<{ img: number[]; outline: string; shadow: string; dpr: number }> => page.evaluate(([alt, scroll]: [string, boolean]) => {
    const img = Array.from(document.querySelectorAll(".fileview-md img")).find((x) => x.getAttribute("alt") === alt) as HTMLElement;
    if (scroll) img.scrollIntoView({ block: "center" });
    const r = img.getBoundingClientRect(), cs = getComputedStyle(img);
    return { img: [r.left, r.top, r.right, r.bottom], outline: cs.outlineStyle, shadow: cs.boxShadow, dpr: window.devicePixelRatio };
  }, [alt, scroll]);
  await layout(true);
  await frames(page, 2);
  const lay = await layout(false);
  const spread = /(-?[\d.]+)px$/.exec(lay.shadow.trim());
  assert.deepEqual([lay.dpr, lay.outline, !!spread && Number(spread[1]) > 0], [k, "dashed", true], where + ": " + alt + ": the page's device scale is " + k + " and the picture wears the mark's outline at rest over a ring (" + lay.shadow + ")");
  const cx = Math.max(0, Math.floor(lay.img[0] - 40)), cy = Math.max(0, Math.floor(lay.img[1] - 40));
  const cw = Math.ceil(lay.img[2] + 40) - cx, ch = Math.ceil(lay.img[3] + 40) - cy;
  const shot = async () => decodePng(await page.screenshot({ clip: { x: cx, y: cy, width: cw, height: ch } }));
  const withRing = await shot();
  await page.evaluate((alt: string) => {
    let host = Array.from(document.querySelectorAll(".fileview-md img")).find((x) => x.getAttribute("alt") === alt) as Element;
    while (host.parentElement && getComputedStyle(host.parentElement).display === "inline" && host.parentElement.childNodes.length === 1) host = host.parentElement;
    host.parentElement!.setAttribute("data-device-ink-line", "");
    const st = document.createElement("style"); st.id = "device-ink-noring"; st.textContent = ".fileview-md img[data-fv-figweb] { box-shadow: none !important; }"; document.head.appendChild(st);
  }, alt);
  await frames(page, 3);
  const noRing = await shot();
  const still = await layout(false);
  await page.evaluate(() => { const st = document.createElement("style"); st.id = "device-ink-noink"; st.textContent = "[data-device-ink-line], [data-device-ink-line] * { color: transparent !important; -webkit-text-fill-color: transparent !important; text-decoration-color: transparent !important; }"; document.head.appendChild(st); });
  await frames(page, 3);
  const noInk = await shot();
  const inkless = await layout(false);
  await page.evaluate(() => { document.getElementById("device-ink-noink")!.remove(); document.getElementById("device-ink-noring")!.remove(); document.querySelector("[data-device-ink-line]")!.removeAttribute("data-device-ink-line"); });
  await frames(page, 2);
  assert.deepEqual([still.img, still.shadow, inkless.img], [lay.img, "none", lay.img], where + ": " + alt + ": the overrides take the ring off (the picture's computed box-shadow none under them) and move nothing");
  assert.deepEqual([withRing.width, withRing.height], [cw * k, ch * k], where + ": " + alt + ": the shot holds " + k + " device pixels per CSS pixel on each axis");
  const at = (png: { width: number; bpp: number; data: Buffer }, x: number, y: number) => { const q = (y * png.width + x) * png.bpp; return [png.data[q], png.data[q + 1], png.data[q + 2]]; };
  const same = (a: number[], b: number[]) => a[0] === b[0] && a[1] === b[1] && a[2] === b[2];
  let covered = 0;
  for (let y = 0; y < withRing.height; y++) for (let x = 0; x < withRing.width; x++) {
    const b = at(noRing, x, y);
    if (same(at(withRing, x, y), b) || same(b, at(noInk, x, y))) continue;
    covered++;
  }
  note("device ink, " + where + ": " + alt + ": " + covered + " device pixels of the text's ink covered by the ring (a clip of " + cw + " by " + ch + " CSS px at a device scale of " + k + ")");
  return covered;
}
test("in a browser at a device scale of 2, under CDP touch emulation on the chat modal, the ring's line pin: a remote picture under the floor under a line of descenders holding an inline code span, and under a line of keys, leaves their paint uncovered, and one in a note callout, an even table row and a highlight paints no pixel past its margin box over the tint, in both themes (ringClearsTheLines; the second margin ruling of 2026-09-24: at 1px up and down the ring covered the code span's box, at 2px a key's bottom row and a row of each tint past the margin box; a property pin read off the page)", { timeout: 240000 }, async (t) => {
  const names = LINE_SCENES.map(([alt]) => alt);
  const second = await secondServer([], Object.fromEntries(names.map((n) => ["/" + n + ".svg", [20, 20] as [number, number]])));
  try {
    await inBrowser(t, async (browser) => {
      const before = async (pg: any): Promise<void> => {
        await pg.context().route((u: URL) => u.href.startsWith(WEB + "/"), async (route: any) => {
          const a = await fromSecond(second.port, new URL(route.request().url()).pathname);
          return route.fulfill({ status: a.status, contentType: a.type, body: a.body });
        });
      };
      // openViewer opens its page by the browser's newPage, and a device scale is set where a page's context is made, so the case hands
      // it a browser whose newPage adds the scale
      const scaled = { newPage: (o: Record<string, unknown>) => browser.newPage({ ...o, deviceScaleFactor: 2 }) };
      const { page, errors } = await openViewer(scaled, "chat", 900, 600, { docs: { [REPORT]: LINES_TEXT }, before });
      await page.click('[data-act="fv-load"]');
      await page.waitForFunction((n: number) => { const imgs = Array.from(document.querySelectorAll(".fileview-md img")) as HTMLImageElement[]; return imgs.length === n && imgs.every((i) => i.complete && i.naturalWidth > 0 && i.hasAttribute("data-fv-figweb")); }, names.length, { timeout: 10000 });
      const cdp = await page.context().newCDPSession(page);
      await cdp.send("Emulation.setTouchEmulationEnabled", { enabled: true, maxTouchPoints: 1 });
      await frames(page, 3);
      const fails: string[] = [];
      for (const theme of ["dark", "light"] as const) {
        await page.evaluate((light: boolean) => document.body.classList.toggle("theme-light", light), theme === "light");
        await frames(page, 3);
        await ringClearsTheLines(page, theme + " theme, at a device scale of 2, at rest under touch emulation on the chat modal", fails, (m) => t.diagnostic(m), 2);
      }
      await page.evaluate(() => document.body.classList.remove("theme-light"));
      assert.deepEqual(fails, [], "the ring covers no paint of the lines above and paints no pixel past the picture's margin box over a tint (a property pin read off the page):\n" + fails.join("\n"));
      assert.deepEqual(errors, [], "no page errors");
      await page.close();
    });
  } finally { await second.close(); }
});

/** A bold italic run of f in a big element glued on both sides to a picture under the floor in sup inside a hundred nested small
 *  elements, the worst scene the sweeps below 0.7em read at a device scale of 2 (FLOOR_D2_BOUND), spelled as that sweep spelled it. */
const FLOOR_D2_TEXT = "# Report\n\n" + PARA(1) + "\n\n<big>Bold italic ***ffff***" + "<small>".repeat(100) + "<sup>![nfd](" + WEB + "/nfd.svg)</sup>" + "</small>".repeat(100) + "***ffff*** glued</big>\n\n" + PARA(2) + "\n";
test("in a browser at a device scale of 2, under CDP touch emulation on the chat modal, below 0.7em of the f's at the floor: a bold italic run in a big element glued to a remote picture under the floor in sup inside a hundred nested small elements loses 1 to 135 device pixels of its ink to the ring at 200%, where the sweeps read their maximum at a device scale of 2, in both themes (ringInkDevicePixels, which counts device pixels where the neighbour pin reads one pixel per CSS pixel; the file review's round 15, extra5-3: a residual disclosed and measured, green at the head the round read by design, red under a margin that covers more and under one that covers nothing; a property pin read off the page)", { timeout: 240000 }, async (t) => {
  const second = await secondServer([], { "/nfd.svg": [20, 20] });
  try {
    await inBrowser(t, async (browser) => {
      const before = async (pg: any): Promise<void> => {
        await pg.context().route((u: URL) => u.href.startsWith(WEB + "/"), async (route: any) => {
          const a = await fromSecond(second.port, new URL(route.request().url()).pathname);
          return route.fulfill({ status: a.status, contentType: a.type, body: a.body });
        });
      };
      const scaled = { newPage: (o: Record<string, unknown>) => browser.newPage({ ...o, deviceScaleFactor: 2 }) };
      const { page, errors } = await openViewer(scaled, "chat", 900, 600, { docs: { [REPORT]: FLOOR_D2_TEXT }, before });
      // the gate's placeholder stands inside the hundred nested small elements, with no box a pointer's click can land on: its click
      // is dispatched on the element
      await page.waitForSelector('[data-act="fv-load"]', { state: "attached", timeout: 10000 });
      await page.evaluate(() => { (document.querySelector('[data-act="fv-load"]') as HTMLElement).click(); });
      await page.waitForFunction(() => { const imgs = Array.from(document.querySelectorAll(".fileview-md img")) as HTMLImageElement[]; return imgs.length === 1 && imgs.every((i) => i.complete && i.naturalWidth > 0 && i.hasAttribute("data-fv-figweb")); }, null, { timeout: 10000 });
      const cdp = await page.context().newCDPSession(page);
      await cdp.send("Emulation.setTouchEmulationEnabled", { enabled: true, maxTouchPoints: 1 });
      await frames(page, 3);
      await stepTextSizeUp(page, 5);
      const got = await page.evaluate(() => [(document.querySelector(".fileview") as HTMLElement).dataset.fvText, getComputedStyle(Array.from(document.querySelectorAll(".fileview-md img")).find((x) => x.getAttribute("alt") === "nfd")!).marginLeft]);
      t.diagnostic("the floor's picture at 200%: its margin across the line " + got[1] + " (the ring's 3px under the sheets' rule)");
      assert.equal(got[0], "200", "five steps of the viewer's own control take the text size to 200%, the configuration of the maximum at a device scale of 2 (a precondition)");
      const fails: string[] = [];
      for (const theme of ["dark", "light"] as const) {
        await page.evaluate((light: boolean) => document.body.classList.toggle("theme-light", light), theme === "light");
        await frames(page, 3);
        const where = theme + " theme, at a text size of 200%, at a device scale of 2, at rest under touch emulation on the chat modal";
        const n = await ringInkDevicePixels(page, "nfd", 2, where, (m) => t.diagnostic(m));
        // FAILS under a margin that covers more (more than 135) and under one that covers nothing (0)
        if (n < FLOOR_D2_BOUND[0] || n > FLOOR_D2_BOUND[1]) fails.push(where + ": " + n + " device pixels of the text's ink covered by the ring, outside the bound the sheets state at a device scale of 2 below 0.7em of the f's, " + FLOOR_D2_BOUND[0] + " to " + FLOOR_D2_BOUND[1]);
      }
      await page.evaluate(() => document.body.classList.remove("theme-light"));
      assert.deepEqual(errors, [], "no page errors");
      await page.close();
      assert.deepEqual(fails, [], "the run before a picture at the floor loses ink within the bound the sheets state at a device scale of 2, counted in device pixels (a property pin read off the page):\n" + fails.join("\n"));
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
// axis for pins (d) and (f), and since the file review's round 15 each same-origin frame above the viewer and the top window's
// visual viewport too (the zoom and frame pins in the block below), pins (d) and (f) each by Space, by Enter and by the numeric keypad's Enter (NumpadEnter, which Chromium sends as the key
// Enter under a code of its own, so the key gate, which reads the key, reads it as Enter; each press's key and code are read back
// at the window first, KEY_SENT), each leaving the control unpressed, and pin (d)'s cells at the body's scrollport and pin (f) at the
// table's, where the control stands inside the window, so the scrollport alone refuses the key (the file review's round 15,
// extra6-1 with tests-2), and the key-release pin (Space clicks a button on its release, so a Space
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
/** In the viewer's document `at` (a page, or a frame of one), window.open stubbed to count the opens and the page's helpers
 *  installed, then both remote pictures loaded through the gate, their two web controls standing. */
async function focusReady(at: any): Promise<void> {
  await at.evaluate(() => {
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
  await at.click('[data-act="fv-load"]');
  await at.waitForFunction(() => { const imgs = Array.from(document.querySelectorAll(".fileview-md img")) as HTMLImageElement[]; return imgs.length === 2 && imgs.every((i) => i.complete && i.naturalWidth > 0) && document.querySelectorAll(".fileview-md .fv-figopen-web").length === 2; }, null, { timeout: 10000 });
  await frames(at, 3);
}
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
  await focusReady(o.page);
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
 *  body the keyboard (its tabindex 0), the pointer left there (a tap under touch); returns that point. `at` is the viewer's document,
 *  the page itself or a frame of it at the page's origin (0, 0), so the frame's points are the page's. */
async function pressPlainText(page: any, cdp: any, pointer: Pointer, alt: string, at: any = page): Promise<{ x: number; y: number }> {
  await at.evaluate((alt: string) => { (window as any).__img(alt).scrollIntoView({ block: "center" }); }, alt);
  await settleScroll(at);
  const p = await at.evaluate((alt: string) => {
    const ib = (window as any).__img(alt).getBoundingClientRect(), br = (document.querySelector(".fileview-body") as HTMLElement).getBoundingClientRect();
    const para = Array.from(document.querySelectorAll(".fileview-md > p")).map((e) => e.getBoundingClientRect()).find((r) => r.top > ib.bottom + 4 && r.top + 6 < br.bottom)!;
    return { x: para.left + 20, y: para.top + 5 };
  }, alt);
  if (pointer === "touch") await tapAt(cdp, p.x, p.y); else await page.mouse.click(p.x, p.y);
  await frames(at, 2);
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
/** Tab pressed until the web control after `alt` holds the keyboard; returns the presses (bounded at 40). `at` is the viewer's
 *  document, the page or a frame of it; the keys are the page's. */
async function tabToControl(page: any, alt: string, at: any = page): Promise<number> {
  for (let i = 0; i < 40; i++) {
    await page.keyboard.press("Tab");
    await frames(at, 1);
    if (await at.evaluate((alt: string) => document.activeElement === (window as any).__ctl(alt), alt)) return i + 1;
  }
  throw new Error("Tab never reached the " + alt + " picture's control");
}
/** What a press of each key pins (d) and (f) press sends, as a key and a code: Space and Enter as themselves, and the numeric keypad's
 *  Enter as the key Enter under the code NumpadEnter, so the key gate, which reads the key, reads it as it reads Enter. */
const KEY_SENT: Record<"Space" | "Enter" | "NumpadEnter", [string, string]> = { Space: [" ", "Space"], Enter: ["Enter", "Enter"], NumpadEnter: ["Enter", "NumpadEnter"] };
/** `key` pressed on the keyboard's holder, its keydown read at the window in the capture phase, so before the key gate's listener,
 *  which is on the file view's .fileview-body element. It is not the first listener: the page's one window capture listener for
 *  keydown, the save chord's (file-comments.ts, registered at load), runs before it and acts on that chord alone. Returns the key and
 *  the code the keydown carried. `at` is the viewer's document, the page or a frame of it; the key is the page's. */
async function pressReadingKey(page: any, key: keyof typeof KEY_SENT, at: any = page): Promise<[string, string] | null> {
  await at.evaluate(() => { const w = window as any; w.__keySent = null; window.addEventListener("keydown", (e) => { w.__keySent = [e.key, e.code]; }, { capture: true, once: true }); });
  await page.keyboard.press(key);
  return at.evaluate(() => (window as any).__keySent);
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
for (const surface of ["chat", "feed", "pane"] as Surface[]) for (const key of ["Space", "Enter", "NumpadEnter"] as const) {
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
      const sent = await pressReadingKey(page, key);
      rec.keySent = sent;
      await settleScroll(page);
      const a = await focusState(page, "big");
      rec.afterKey = a;
      assert.deepEqual(sent, KEY_SENT[key], "the press sent the key and the code " + key + " sends (a precondition, KEY_SENT)");
      assert.equal(a.opened, 0, key + " on the keyboard-focused control out of view opens nothing (a property pin read off the page)");
      assert.equal(a.pressed, false, key + " on the keyboard-focused control out of view leaves it unpressed, not :active, so the gate read the key's keydown and not its release alone (a property pin read off the page; the file review's round 15, tests-2)");
    });
  });
  test("in a browser " + onWhat("fine", surface) + ", the web control's focus, pin (d) at the body's scrollport: Tab to the web control, the body scrolled until the control's bottom stands 3px above the body's top edge while the control is still inside the window, then " + key + ": no open and the control unpressed (the file review's round 15, extra6-1 with tests-2: PageDown left the control outside the window too, so the viewport alone refused the key and the body's scrollport went unread; red under a region that reads the viewport alone and under one that clips nothing down, green at the head the round read by design)", { timeout: 120000 }, async (t) => {
    const rec: Record<string, unknown> = { pin: "d-port", key };
    await focusCase(t, "fine", surface, rec, async (page, cdp) => {
      await pressPlainText(page, cdp, "fine", "big");
      await pointerAway(page, "fine");
      rec.tabs = await tabToControl(page, "big");
      const f = await focusState(page, "big");
      assert.equal(f.focusVisible, true, "a keyboard focus on the control, :focus-visible (a precondition)");
      await page.evaluate(() => { const c = (window as any).__ctl("big") as HTMLElement, b = document.querySelector(".fileview-body") as HTMLElement; b.scrollTop += c.getBoundingClientRect().bottom - (b.getBoundingClientRect().top + b.clientTop) + 3; });
      await settleScroll(page);
      const g = await page.evaluate(() => {
        const c = (window as any).__ctl("big") as HTMLElement, b = document.querySelector(".fileview-body") as HTMLElement, cr = c.getBoundingClientRect();
        return { ctl: [cr.top, cr.bottom], port: b.getBoundingClientRect().top + b.clientTop, overflowY: getComputedStyle(b).overflowY, active: document.activeElement === c };
      });
      rec.geometry = g;
      assert.ok(g.ctl[1] <= g.port - 2 && g.ctl[1] >= g.port - 4 && g.ctl[0] >= 0 && g.active, "the focused control's bottom about 3px above the top of the body's padding box and its top inside the window, so the body's scrollport alone leaves it out of view (a precondition): " + JSON.stringify(g));
      const sent = await pressReadingKey(page, key);
      rec.keySent = sent;
      await settleScroll(page);
      const a = await focusState(page, "big");
      rec.afterKey = a;
      assert.deepEqual(sent, KEY_SENT[key], "the press sent the key and the code " + key + " sends (a precondition, KEY_SENT)");
      assert.equal(a.opened, 0, key + " on the keyboard-focused control above the body's scrollport and inside the window opens nothing (a property pin read off the page)");
      assert.equal(a.pressed, false, key + " there leaves the control unpressed, not :active (a property pin read off the page)");
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
for (const key of ["Space", "Enter", "NumpadEnter"] as const) test("in a browser (a fine pointer), the web control's focus, pin (f): a Tab-focused web control in a table wider than the Rendered box, the table scrolled sideways just far enough that the control stands wholly left of the table's own scrollport while it is still inside the window and meets the viewer body's scrollport, its row shown, then " + key + ": no open and the control unpressed (the file review's round 14, extra9-1: before the fixes " + key + " opened one; the file review's round 15, extra6-1 with tests-2: scrolled to the table's end the control was outside the window too, so the viewport alone refused the key and the table's scrollport went unread; red under a region that reads the viewport alone and under one that clips nothing across, green at the head the round read by design)", { timeout: 120000 }, async (t) => {
  const rec: Record<string, unknown> = { pin: "f", key };
  await focusCase(t, "fine", "chat", rec, async (page, cdp) => {
    await pressPlainText(page, cdp, "fine", "wide");
    await pointerAway(page, "fine");
    rec.tabs = await tabToControl(page, "wide");
    await settleScroll(page);
    // the least sideways scroll that takes the control out of the table's scrollport: its right edge about 3px left of the table's
    // padding box, so it stays inside the window and meets the body's padding box (at 900px the body's starts 18px left of the table's
    // and the control is 22px wide, so it cannot lie wholly inside the body's box; the file review's round 15, extra6-1, as measured)
    await page.evaluate(() => { const c = (window as any).__ctl("wide") as HTMLElement, tb = c.closest("table") as HTMLElement; tb.scrollLeft += Math.ceil(c.getBoundingClientRect().right - (tb.getBoundingClientRect().left + tb.clientLeft)) + 3; });
    await frames(page, 3);
    const g = await page.evaluate(() => {
      const c = (window as any).__ctl("wide") as HTMLElement, tb = c.closest("table") as HTMLElement, tr = c.closest("tr") as HTMLElement, b = document.querySelector(".fileview-body") as HTMLElement;
      const cr = c.getBoundingClientRect(), tr0 = tb.getBoundingClientRect(), rr = tr.getBoundingClientRect(), br = b.getBoundingClientRect(), cs = getComputedStyle(tb);
      const pl = tr0.left + tb.clientLeft, pr = pl + tb.clientWidth, bl = br.left + b.clientLeft;
      return { overflowX: cs.overflowX, scrollLeft: tb.scrollLeft, scrollWidth: tb.scrollWidth, clientWidth: tb.clientWidth, port: [pl, pr], bodyPort: bl, ctl: [cr.left, cr.right],
        leftOfPort: cr.right <= pl, inWindow: cr.left >= 0, meetsBody: cr.right > bl, rowShown: rr.top < br.bottom && rr.bottom > br.top, active: document.activeElement === c };
    });
    rec.geometry = g;
    assert.deepEqual([g.leftOfPort, g.inWindow, g.meetsBody, g.rowShown, g.active], [true, true, true, true, true], "the focused control wholly left of the table's padding box, inside the window (its left edge at 0 or right of it) and meeting the body's padding box (its right edge past the body's left one), its row shown and the keyboard on it, so the table's scrollport alone leaves it out of view (a precondition): " + JSON.stringify(g));
    const sent = await pressReadingKey(page, key);
    rec.keySent = sent;
    await frames(page, 4);
    const s = await focusState(page, "wide");
    rec.afterKey = s;
    assert.deepEqual(sent, KEY_SENT[key], "the press sent the key and the code " + key + " sends (a precondition, KEY_SENT)");
    assert.equal(s.opened, 0, key + " on the control outside the table's scrollport opens nothing (a property pin read off the page)");
    assert.equal(s.pressed, false, key + " on the control outside the table's scrollport leaves it unpressed, not :active (a property pin read off the page; the file review's round 15, tests-2)");
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
    // Stated, not pinned: a Space pressed in view and released out of view leaves the control :active once the gate cancels its
    // keyup (afterRelease reads pressed true), so this pin asserts no pressed state; the gate's comment covers a Space pressed out of
    // view alone (the file review's round 15, tests-2, on the coordinator's answer)
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
test("in a browser (a fine pointer), the web control's focus, a keep check: Tab to the web control in the wide table with the table unscrolled, the control inside the window and inside the table's scrollport: Space opens once (the file review's round 14, extra9-1: the table's scrollport is read, and a control inside it is in view)", { timeout: 120000 }, async (t) => {
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

// ── the key gate under a pinch zoom and inside frames (the file review's round 15, extra5-2 with tests-2) ─────────────────────────
// A keyboard focus on the web control inside the layout viewport but off the screen under a pinch zoom opened the tab on Enter or
// Space, in a top-level page and in the dashboard's shape, the viewer's page in a same-origin iframe of a zoomed top page, whose
// own visual viewport is the frame's whole layout viewport. controlInView now reads the visual viewport of the topmost window it
// reaches by walking up the same-origin frames, and a parent of another origin stops the walk without an out. On a fine pointer on
// the chat modal (the walk reads no surface, and pins (d) hold the per-surface terms), each case in a browser of its own, window.open
// stubbed in the viewer's document: (1) the viewer as the top page, Tab to the control, the page zoomed to 3 by CDP's
// Emulation.setPageScaleFactor (exact; touch emulation does not zoom headless Chromium), then Enter, Space or NumpadEnter opens
// nothing and leaves the control unpressed; (2) the same in the dashboard's shape, the top page zoomed; (3) keep cells on both
// shapes, a scale of 1.2 leaving the control on the screen, each key opening once; (4) the viewer's page in an iframe of a top page
// of another origin, at a scale of 1, each key opening once. Each zoom cell asserts its premise first: the top's page scale above
// 1, the control inside its own frame's layout viewport, and off the top's visual viewport (on it for a keep cell). (1) and (2) are
// red at the head the round read by one open per key, and (2) red too under a region that reads the viewer's own visual viewport;
// (3) and (4) are green there by design, (4) red under a walk that reads a parent of another origin as out. Property pins read off
// the page; file-view-outline.test.ts runs the region's terms in CI over the stand-in.
const OTHER_TOP = "http://notes-dash.test";   // a second synthetic origin: the top page of the cross-origin cells, routed like the first
type Host = "top" | "same" | "cross";
/** A size and a touch flag for the dashboard's pane cells: the context's viewport, and CDP's touch emulation through playwright's
 *  hasTouch (a coarse pointer, which the narrow layout's query reads up to 1024px). */
type PaneShape = { width: number; height: number; touch: boolean };
let paneCssMemo: { desk: string; mq: string; narrow: string } | null = null;
/** The dashboard's pane wrapper as the kernel's landing page writes it, lifted from kernel/kernel.py's text at run time so the
 *  shell follows the kernel and is never typed here: the desktop rule (`.pane{...overflow:hidden}`), the query of the narrow and
 *  touch layout (_MOBILE_MQ) and the rule the kernel puts under it (`.pane{display:contents}`), each found once, the desktop rule
 *  before the query's block and the narrow rule after it. */
function paneCss(): { desk: string; mq: string; narrow: string } {
  if (paneCssMemo) return paneCssMemo;
  const K = fs.readFileSync(path.resolve(process.cwd(), "..", "kernel", "kernel.py"), "utf8");
  const mq = /^_MOBILE_MQ = "([^"]+)"$/m.exec(K);
  const rules = Array.from(K.matchAll(/"(\.pane\{[^"{}]*\})"/g), (m) => ({ css: m[1], at: m.index! }));
  const block = K.indexOf('"@media " + _MOBILE_MQ + "{"');
  const desk = rules.filter((r) => r.css.includes("overflow:hidden") && r.at < block);
  const narrow = rules.filter((r) => r.css === ".pane{display:contents}" && r.at > block);
  assert.ok(mq && block > 0 && desk.length === 1 && narrow.length === 1, "kernel/kernel.py's pane wrapper: _MOBILE_MQ, the desktop .pane rule with overflow hidden before the narrow layout's @media block and .pane{display:contents} inside it, each once (the anchors moved; re-anchor): " + JSON.stringify({ mq: mq && mq[1], block, rules: rules.map((r) => r.css) }));
  paneCssMemo = { desk: desk[0].css, mq: mq![1], narrow: narrow[0].css };
  return paneCssMemo;
}
/** The top page of the pane cells: the viewer's iframe inside div.pane, the kernel's id for the column (chat-pane or files-pane),
 *  under the kernel's own pane rules (paneCss), the wrapper sized to the page and the iframe filling it. */
function paneShell(mode: "chat" | "pane"): string {
  const k = paneCss();
  return '<!DOCTYPE html><html><head><meta charset=utf-8><style>html, body { margin: 0; height: 100%; overflow: hidden; } body > .pane { width: 100%; height: 100%; } iframe { border: 0; width: 100%; height: 100%; display: block; } '
    + k.desk + " @media " + k.mq + "{" + k.narrow + '}</style></head><body><div class="pane" id="' + (mode === "pane" ? "files-pane" : "chat-pane") + '"><iframe src="' + ORIGIN + '/inner"></iframe></div></body></html>';
}
/** The focus report in the dashboard's shape at 900 by 600: a top page at `top` holding one iframe at (0, 0), 900 by 600 with no
 *  border, whose page, the viewer's at ORIGIN + "/inner", opens the report, both remote pictures relayed to the second server and
 *  loaded through the gate (focusReady in the frame). Both origins are served by the context's routes, so a top page of another
 *  origin hosts the viewer as an out-of-process frame. Returns the page and the viewer's frame. With a `shape` (the predicate's
 *  cells, the file review's round 16, regression-1) the context takes the shape's size and touch, and the iframe fills the top page
 *  inside the kernel's pane wrapper (paneShell). */
async function openFramed(browser: any, port: number, top: string, mode: "chat" | "pane" = "chat", shape: PaneShape | null = null): Promise<{ page: any; at: any; errors: string[] }> {
  const ctx = await browser.newContext({ viewport: shape ? { width: shape.width, height: shape.height } : { width: 900, height: 600 }, hasTouch: !!(shape && shape.touch) });
  const page = await ctx.newPage();
  const errors: string[] = [];
  page.on("pageerror", (e: Error) => { errors.push(e.message); });
  const inner = pageHtml(mode, { [REPORT]: FOCUS_TEXT });   // the framed page's surface: the chat page (its modal viewer) unless a case names the Files pane
  const shell = shape ? paneShell(mode) : '<!DOCTYPE html><html><head><meta charset=utf-8><style>html, body { margin: 0; height: 100%; overflow: hidden; } iframe { border: 0; width: 900px; height: 600px; display: block; }</style></head><body><iframe src="' + ORIGIN + '/inner"></iframe></body></html>';
  await ctx.route((u: URL) => u.origin === ORIGIN || u.origin === top, (route: any) => {
    const u = new URL(route.request().url());
    return route.fulfill({ status: 200, contentType: "text/html", body: u.origin === top && u.pathname === "/" ? shell : inner });
  });
  await ctx.route((u: URL) => u.href.startsWith(WEB + "/"), async (route: any) => {
    const a = await fromSecond(port, new URL(route.request().url()).pathname);
    return route.fulfill({ status: a.status, contentType: a.type, body: a.body });
  });
  await page.goto(top + "/");
  let at: any = null;
  for (let i = 0; i < 50 && !at; i++) { at = page.frames().find((f: any) => f !== page.mainFrame() && f.url() === ORIGIN + "/inner") || null; if (!at) await frames(page, 2); }
  if (!at) throw new Error("the viewer's frame never attached: " + page.frames().map((f: any) => f.url()).join(", "));
  await at.waitForFunction(() => !!(window as any).FV, null, { timeout: 10000 });
  await at.evaluate(([p, sid]: [string, string]) => { (window as any).FV.openFileView(p, sid, null); }, [REPORT, SID]);
  await at.waitForFunction(() => !!document.querySelector(".fileview-md > p"), null, { timeout: 10000 });
  await focusReady(at);
  return { page, at, errors };
}
/** One case on `host`: the viewer as the top page (openFocus, fine pointer, chat), or in the dashboard's shape with a top page of the
 *  same origin or of another; `body` gets the page (the keys, the mouse, the zoom) and the viewer's document; the record is logged. */
async function hostCase(t: any, host: Host, rec: Record<string, unknown>, body: (page: any, at: any) => Promise<void>, mode: "chat" | "pane" = "chat"): Promise<void> {
  const second = await secondServer([]);
  try {
    await inBrowser(t, async (browser) => {
      const o = host === "top" ? await openFocus(browser, second.port, "fine", mode) : await openFramed(browser, second.port, host === "same" ? ORIGIN : OTHER_TOP, mode);
      const at = host === "top" ? o.page : (o as { at: any }).at;
      try {
        await body(o.page, at);
        assert.deepEqual(o.errors, [], "no page errors");
      } finally {
        rec.opens = await at.evaluate(() => (window as any).__opened).catch(() => null);
        t.diagnostic("record " + JSON.stringify({ host, ...rec }));
        await o.page.close();
      }
    });
  } finally { await second.close(); }
}
type Zoom = { scale: number; vv: number[]; frameAt: number[]; ctl: number[]; layout: number[]; inLayout: boolean; onScreen: boolean; active: boolean };
/** The top page's scale set to `scale` by CDP's Emulation.setPageScaleFactor (none sent at 1), then where the big picture's control
 *  stands: its box in the viewer's document and that document's layout viewport, the frame's content box in the top page (0, 0 for
 *  the top page itself), the top's visual viewport and scale, whether the box lies inside its layout viewport, whether it meets the
 *  top's visual viewport, and whether it holds the keyboard. */
async function zoomTo(page: any, at: any, scale: number): Promise<Zoom> {
  if (scale !== 1) { const cdp = await page.context().newCDPSession(page); await cdp.send("Emulation.setPageScaleFactor", { pageScaleFactor: scale }); }
  await frames(page, 4);
  await frames(at, 2);
  const inner = await at.evaluate(() => { const c = (window as any).__ctl("big") as HTMLElement, r = c.getBoundingClientRect(); return { ctl: [r.left, r.top, r.right, r.bottom], layout: [innerWidth, innerHeight], active: document.activeElement === c }; });
  const top = await page.evaluate(() => { const v = window.visualViewport!, f = document.querySelector("iframe"), b = f ? f.getBoundingClientRect() : null; return { scale: v.scale, vv: [v.offsetLeft, v.offsetTop, v.width, v.height], frameAt: b ? [b.left + f!.clientLeft, b.top + f!.clientTop] : [0, 0] }; });
  const [l, tp, r, b] = inner.ctl, [ox, oy] = top.frameAt, [vx, vy, vw, vh] = top.vv;
  return { ...top, ...inner, inLayout: l >= 0 && tp >= 0 && r <= inner.layout[0] && b <= inner.layout[1], onScreen: r + ox > vx && l + ox < vx + vw && b + oy > vy && tp + oy < vy + vh };
}
/** Tab to the big picture's web control from a press on the body's text, the pointer away, in the viewer's document `at`. */
async function tabToBig(page: any, at: any, rec: Record<string, unknown>): Promise<void> {
  await pressPlainText(page, null, "fine", "big", at);
  await pointerAway(page, "fine");
  rec.tabs = await tabToControl(page, "big", at);
  await settleScroll(at);
}
const onHost = (host: Host): string => host === "top" ? "the viewer as the top page" : host === "same" ? "the viewer's page in a same-origin iframe of the top page, the dashboard's shape" : "the viewer's page in an iframe of a top page of another origin";
for (const host of ["top", "same"] as const) for (const key of ["Space", "Enter", "NumpadEnter"] as const) {
  test("in a browser (a fine pointer), the web control's focus under a pinch zoom, pin (" + (host === "top" ? "1" : "2") + "), " + onHost(host) + ": Tab to the web control, the top page zoomed to 3 so the control, inside its layout viewport, is off the screen, then " + key + ": no open and the control unpressed (the file review's round 15, extra5-2 with tests-2: before the fix " + key + " opened one" + (host === "same" ? ", and under a region reading the viewer's own visual viewport, which is the frame's whole layout viewport, it opened one too" : "") + ")", { timeout: 120000 }, async (t) => {
    const rec: Record<string, unknown> = { pin: "zoom-" + host, key };
    await hostCase(t, host, rec, async (page, at) => {
      await tabToBig(page, at, rec);
      const z = await zoomTo(page, at, 3);
      rec.zoom = z;
      assert.ok(z.scale > 1 && z.inLayout && !z.onScreen && z.active, "the top's page scale above 1, the focused control inside its own layout viewport and off the top's visual viewport (a precondition): " + JSON.stringify(z));
      const sent = await pressReadingKey(page, key, at);
      rec.keySent = sent;
      await frames(at, 4);
      const a = await focusState(at, "big");
      rec.afterKey = a;
      assert.deepEqual(sent, KEY_SENT[key], "the press sent the key and the code " + key + " sends (a precondition, KEY_SENT)");
      assert.equal(a.opened, 0, key + " on the keyboard-focused control off the zoomed screen opens nothing (a property pin read off the page)");
      assert.equal(a.pressed, false, key + " there leaves the control unpressed, not :active (a property pin read off the page)");
    });
  });
}
for (const host of ["top", "same"] as const) for (const key of ["Space", "Enter", "NumpadEnter"] as const) {
  test("in a browser (a fine pointer), the web control's focus under a pinch zoom, a keep check, " + onHost(host) + ": Tab to the web control, the top page zoomed to 1.2 with the control still on the screen, then " + key + ": one open (the file review's round 15, extra5-2: the region reads the visible part of the page, and a control in it opens on its key; green before the fix by design)", { timeout: 120000 }, async (t) => {
    const rec: Record<string, unknown> = { pin: "zoom-keep-" + host, key };
    await hostCase(t, host, rec, async (page, at) => {
      await tabToBig(page, at, rec);
      const z = await zoomTo(page, at, 1.2);
      rec.zoom = z;
      assert.ok(z.scale > 1 && z.inLayout && z.onScreen && z.active, "the top's page scale above 1 and the focused control on the top's visual viewport (a precondition): " + JSON.stringify(z));
      const sent = await pressReadingKey(page, key, at);
      rec.keySent = sent;
      await frames(at, 4);
      const a = await focusState(at, "big");
      rec.afterKey = a;
      assert.deepEqual(sent, KEY_SENT[key], "the press sent the key and the code " + key + " sends (a precondition, KEY_SENT)");
      assert.deepEqual([a.opened, a.pressed], [1, false], key + " on the control on the screen opens once and leaves it unpressed (a keep check, a property read off the page)");
    });
  });
}
for (const key of ["Space", "Enter", "NumpadEnter"] as const) {
  test("in a browser (a fine pointer), the web control's focus, pin (4), " + onHost("cross") + ", at a scale of 1: Tab to the web control, in view in its frame, then " + key + ": one open, since the walk stops at a parent of another origin with the reads made so far and does not read it as out, the frame element reading null there (the file review's round 15, extra5-2: VS Code's webview host is of another origin; green before the fix by design, red under a walk that reads that parent as out)", { timeout: 120000 }, async (t) => {
    const rec: Record<string, unknown> = { pin: "cross", key };
    await hostCase(t, "cross", rec, async (page, at) => {
      await tabToBig(page, at, rec);
      const road = await at.evaluate(() => { let inner: string; try { inner = String((window.parent as any).innerWidth); } catch (e) { inner = "throws " + (e as Error).name; } return { framed: window.parent !== window, frameElement: window.frameElement === null ? "null" : "element", parentInner: inner }; });
      rec.road = road;
      assert.ok(road.framed && road.frameElement === "null" && road.parentInner.startsWith("throws"), "the viewer's window has a parent of another origin: a parent of its own, its frame element null and the parent's innerWidth unreadable (a precondition, the stop's road): " + JSON.stringify(road));
      const z = await zoomTo(page, at, 1);
      rec.zoom = z;
      assert.ok(z.inLayout && z.onScreen && z.active, "the focused control inside its own layout viewport and on the screen (a precondition): " + JSON.stringify(z));
      const sent = await pressReadingKey(page, key, at);
      rec.keySent = sent;
      await frames(at, 4);
      const a = await focusState(at, "big");
      rec.afterKey = a;
      assert.deepEqual(sent, KEY_SENT[key], "the press sent the key and the code " + key + " sends (a precondition, KEY_SENT)");
      assert.deepEqual([a.opened, a.pressed], [1, false], key + " on the control in view in a frame of another origin's page opens once and leaves it unpressed (a property pin read off the page)");
    });
  });
}

// ── a picture inside a fold's summary: the fold takes the click, plain or modified, and the control stays ───────────────────────
// (the file review's round 14, fresh-1: the figures' click listener read no summary, so one click on a picture inside a details
// element's own first summary toggled the fold AND opened the picture, a remote picture's tab or a local picture's open in the
// viewer in place of the report, and a Ctrl-click toggled the fold too and opened the picture's tab; the picture under the floor
// wore the address line and the outbound mark, which promised the open.) The report: seven pictures, each in a summary, the remote
// ones from the second server through the gate: a remote picture under the floor (20 by 20, "stiny"), a local picture ("slocal")
// and a remote picture over the floor ("sbig"), each in a details element's own first summary; a remote picture inside an author's
// named anchor inside such a summary ("snamed"); and a remote and a local picture each in a stray summary outside any details
// ("stray", "straylocal"), which toggles nothing; and a remote picture under the floor in a details element's SECOND summary
// ("slater"), no fold's title, whose details its own case opens first. On a fine pointer in the dark theme, window.open stubbed to a record, each fold's
// toggles recorded by a MutationObserver on its open attribute as the click's task runs (so a navigation that replaces the report
// after the click cannot hide the toggle), a Ctrl-click the key held around the click with its ctrlKey read back at the document,
// and an open that must not happen read after a bounded settle (the viewer's navigation is a fetch and a paint, so the bar's name is
// awaited up to 2 s for a change). Each case collects its cells, logs its record as diagnostics and asserts the cells once. The
// first three are property pins read off the page, red over the viewer before the summary predicate (file-view.ts figureFoldOf) by
// the open beside the toggle and by the title line and the mark; the fourth holds the ruling's two controls, green there by design;
// the fifth, the later summary (the file review's round 15, tests-4), is green there on every fold cell by design and red with
// figureFoldOf's loop replaced by `return s;`, and its title cell, equal to the origin's address line, is red there by the path
// the title printed before the origin cut (the file review's round 15, extra9-2).
const FOLD_TEXT = "# Report\n\n" + PARA(1) + "\n\n"
  + '<details><summary><img src="' + WEB + '/stiny.svg" alt="stiny"> Build badge</summary>\n\nfolded text one\n\n</details>\n\n' + PARA(2) + "\n\n"
  + '<details><summary><img src="figs/plot.svg" alt="slocal"> Local screenshots</summary>\n\nfolded text two\n\n</details>\n\n' + PARA(3) + "\n\n"
  + '<details><summary><img src="' + WEB + '/sbig.svg" alt="sbig"> Remote screenshots</summary>\n\nfolded text three\n\n</details>\n\n' + PARA(4) + "\n\n"
  + '<details><summary><a name="fig-n"><img src="' + WEB + '/snamed.svg" alt="snamed"></a> A named anchor inside</summary>\n\nfolded text four\n\n</details>\n\n' + PARA(5) + "\n\n"
  + '<summary><img src="' + WEB + '/stray.svg" alt="stray"> A stray summary</summary>\n\n' + PARA(6) + "\n\n"
  + '<summary><img src="figs/plot2.svg" alt="straylocal"> A stray local summary</summary>\n\n' + PARA(7) + "\n\n"
  + '<details><summary>Two summaries</summary><summary><img src="' + WEB + '/slater.svg" alt="slater"> A later summary</summary>\n\nfolded text five\n\n</details>\n\n' + PARA(8) + "\n";
const FOLD_DOCS: Record<string, string> = { [REPORT]: FOLD_TEXT, [PLOT]: svg("#456"), [PLOT2]: svg("#654") };
const FOLD_ALTS = ["stiny", "slocal", "sbig", "snamed", "stray", "straylocal", "slater"];   // slater: a remote picture under the floor in a details element's SECOND summary (the file review's round 15, tests-4)
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
/** Until all seven pictures of the fold report are loaded and out of the gate's placeholder, then three frames. */
const foldLoaded = async (page: any): Promise<void> => {
  await page.waitForFunction(() => { const imgs = Array.from(document.querySelectorAll(".fileview-md img")); return imgs.length === 7 && imgs.every((i) => !i.closest('[data-act="fv-load"]') && (i as HTMLImageElement).complete && (i as HTMLImageElement).naturalWidth > 0); }, null, { timeout: 10000 });
  await frames(page, 3);
};
/** The fold report open in the chat modal at 900 by 700: the remote pictures relayed to the second server (`port`), the local ones
 *  loaded, the gate lifted, then all seven loaded; window.open stubbed to a record and a capture listener on the document recording
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
/** One fold case on its own browser and second server: the report open and loaded, the seven pictures read and checked for the scene
 *  (seven, four in a details element's own summary, two in a stray one and one in a details element's second summary, stiny and
 *  slater under the floor), then `body` run with a `cell`
 *  recorder whose cells are asserted together at the end, every record a diagnostic first. */
async function foldCase(t: any, body: (page: any, figs: FoldFig[], cell: (what: string, want: unknown, got: unknown) => void, log: (r: unknown) => void) => Promise<void>): Promise<void> {
  const served: string[] = [];
  const second = await secondServer(served, { "/stiny.svg": [20, 20], "/slater.svg": [20, 20] });
  const fails: string[] = [];
  const cell = (what: string, want: unknown, got: unknown): void => { const w = JSON.stringify(want), g = JSON.stringify(got); t.diagnostic((w === g ? "ok " : "FAIL ") + what + ": want " + w + ", got " + g); if (w !== g) fails.push(what + ": want " + w + ", got " + g); };
  try {
    await inBrowser(t, async (browser) => {
      const { page, errors } = await openFold(browser, second.port);
      const figs = await foldFigs(page);
      t.diagnostic("figures " + JSON.stringify(figs));
      assert.deepEqual(figs.map((f) => f.alt), FOLD_ALTS, "the seven pictures, loaded (the scene)");
      assert.deepEqual(figs.map((f) => [f.inSummary, f.ownSummary]), [[true, true], [true, true], [true, true], [true, true], [true, false], [true, false], [true, false]], "four in a details element's own summary, two in a stray summary and one in a details element's second summary (the scene)");
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
    cell("stray: the address line in its title, as anywhere else", WEB_LINE(WEB), figs[4].title);
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

test("in a browser (a fine pointer), a remote picture under the floor in a details element's SECOND summary is no fold's title line: with the details opened, so the later summary is laid out and the picture decided again over its box, it carries the address line in its title, the origin alone, and the outbound mark, and a plain click on it opens its tab once and toggles nothing, the details staying open and the viewer on the report (the file review's round 15, tests-4: figureFoldOf's rule that only a details element's own first summary is a fold's title had been held by a spelling pin alone; its fold cells green before the round's fixes by design, red with its loop replaced by `return s;`, and its title cell red before the origin cut by the path; a property pin read off the page)", { timeout: 120000 }, async (t) => {
  await foldCase(t, async (page, figs, cell, log) => {
    assert.equal(figs[6].alt, "slater", "slater, the seventh picture (a precondition)");
    // a later summary is not rendered while its details is shut: open it, then wait for the decision over the laid-out box (the
    // ResizeObserver over the figures' boxes re-decides the picture once it has one), read off the mark and the title
    await page.evaluate(() => { const i = Array.from(document.querySelectorAll(".fileview-md img")).find((x) => x.getAttribute("alt") === "slater")!; (i.closest("details") as HTMLDetailsElement).open = true; });
    await page.waitForFunction(() => { const i = Array.from(document.querySelectorAll(".fileview-md img")).find((x) => x.getAttribute("alt") === "slater")!; const r = i.getBoundingClientRect(); return r.width > 0 && r.height > 0 && (i.hasAttribute("data-fv-figweb") || i.getAttribute("title") !== null); }, null, { timeout: 5000 }).catch(() => null);
    await frames(page, 3);
    const now = (await foldFigs(page))[6];
    log({ name: "slater opened", ...now });
    assert.ok(now.w > 0 && now.w < 48 && now.h > 0 && now.h < 48, "slater laid out under the floor once its details is open (a precondition): " + JSON.stringify([now.w, now.h]));
    assert.equal(now.control, false, "slater wears no control, under the floor (a precondition)");
    // FAILS under figureFoldOf's loop replaced by `return s;`: the later summary reads as the fold's title, so the picture wears no
    // address line and no mark, and its click opens nothing
    // the address line equal to the origin's (ruling G: WEB_LINE, showing the origin under the origin cut of the file review's
    // round 15, extra9-2), so this cell alone is red before that cut, by the path the title printed, while the fold cells stay green
    cell("slater: the address line in its title, the origin alone", WEB_LINE(WEB), now.title);
    cell("slater: the outbound mark", true, now.mark);
    await page.evaluate(() => { const w = window as any; if (w.__mo) w.__mo.disconnect(); w.__toggled = []; const ds = Array.from(document.querySelectorAll(".fileview-md details")); w.__mo = new MutationObserver((recs) => { for (const r of recs) w.__toggled.push(ds.indexOf(r.target as Element) + ":" + (r.target as HTMLDetailsElement).open); }); for (const d of ds) w.__mo.observe(d, { attributes: true, attributeFilter: ["open"] }); });
    const b = await page.evaluate(() => { const i = Array.from(document.querySelectorAll(".fileview-md img")).find((x) => x.getAttribute("alt") === "slater")!; i.scrollIntoView({ block: "center" }); const q = i.getBoundingClientRect(); return { x: q.left + q.width * 0.3, y: q.top + q.height * 0.6 }; });
    await frames(page, 2);
    const hit = await page.evaluate(([x, y]: [number, number]) => { const e = document.elementFromPoint(x, y); return e ? e.localName + ":" + (e.getAttribute("alt") || "") : null; }, [b.x, b.y]);
    assert.equal(hit, "img:slater", "the click lands on the picture (a precondition)");
    await page.mouse.click(b.x, b.y);
    try { await page.waitForFunction(() => (window as any).__opened.length > 0, null, { timeout: 2000 }); } catch { /* no open within the bound */ }
    await frames(page, 3);
    const c = { toggled: await page.evaluate(() => (window as any).__toggled.slice()), opened: await opened(page), base: await base(page), open: await page.evaluate(() => (Array.from(document.querySelectorAll(".fileview-md img")).find((x) => x.getAttribute("alt") === "slater")!.closest("details") as HTMLDetailsElement).open) };
    log({ name: "slater plain click", ...c });
    cell("slater plain click: its tab, once", [WEB + "/slater.svg"], c.opened);
    cell("slater plain click: no fold toggles", [], c.toggled);
    cell("slater plain click: its details stays open", true, c.open);
    cell("slater plain click: the viewer stays on the report", "report.md", c.base);
  });
});

// ── A finger's tap, frame by frame (the tap-highlight ruling of 2026-09-24) ──────────────────────────────────────────────────────
// The tap that opens the tab paints frames of its own: from the tap until about 170 ms after it the element tapped matches :active,
// and the browser paints its tap highlight over the element a tap reaches that shows a hand cursor, the web control among them, in
// the computed -webkit-tap-highlight-color: rgba(51, 181, 229, 0.4) on a phone, rgba(0, 0, 0, 0.18) under CDP touch emulation and on
// the touchscreen laptop. On the phone that highlight painted the control's line down to 2.578:1 dark and 2.531:1 light against its
// own ground in the frames this pin reads, which it reads one screenshot at a time, about 33 ms apart, so not every frame the
// compositor paints (a screencast of every frame read 2.22:1 dark and 2.41:1 light), a pressed state a gesture opens the tab from,
// under the 3:1 floor. The sheets take the highlight off the web control and the mark (their tap rule), so the frames of the tap are
// the sheets' own, the transition from the rest dress to the hover dress, at 5.351:1 dark and 3.791:1 light at their lowest in the
// frames read on each device and surface (4.201:1 dark and 3.789:1 light in the screencast of every frame). The mark shows no highlight with the rule or without it,
// since nothing from it up to the root shows a hand cursor, so its reads here are keep cells, green without the rule by design; so
// are the control's under CDP touch and on the laptop, where the 0.18 black darkens the line and its ground alike and the tap's
// lowest read stays above 3:1 (4.211:1 dark, 3.416:1 light). Only the phone's highlight takes the line under 3:1, so the phone's
// cells are the ones red without the rule.
type TapDevice = "phone" | "touch" | "laptop";
const TAP_ON: Record<TapDevice, string> = { phone: "a phone (hasTouch and isMobile at a device scale of 1)", touch: "CDP touch emulation", laptop: "the touchscreen laptop" };
/** The web control after `alt` (kind "control") or the picture `alt` wearing the mark (kind "mark"): its centre, its :active and
 *  :hover, whether a transition runs on it, and its computed tap highlight colour. */
const tapTarget = (page: any, alt: string, kind: "control" | "mark"): Promise<{ x: number; y: number; active: boolean; hover: boolean; running: boolean; highlight: string }> => page.evaluate(([alt, kind]: [string, string]) => {
  const img = Array.from(document.querySelectorAll(".fileview-md img")).find((i) => i.getAttribute("alt") === alt) as HTMLElement;
  const n = img.nextElementSibling;
  const el = kind === "mark" ? img : n && n.hasAttribute("data-fv-figopen") ? n as HTMLElement : null;
  if (!el) throw new Error(alt + ": no control after the picture");
  const r = el.getBoundingClientRect();
  return { x: r.left + r.width / 2, y: r.top + r.height / 2, active: el.matches(":active"), hover: el.matches(":hover"), running: el.getAnimations().some((a) => a.playState === "running"), highlight: (getComputedStyle(el) as any).webkitTapHighlightColor };
}, [alt, kind]);
/** A finger's tap on the dress (the web control after `alt`, or the mark on the picture `alt`), then its frames read as painted, one
 *  after another (paintedRatio's mode that neither scrolls nor asserts the pointer away, each read one screenshot, about 33 ms
 *  apart), from the tap until the first frame read after the pressed frames with no transition running, the settled state (bounded
 *  at 3 s): the tap's pressed frames while the element matches :active, the transition after them and the settled state. First the picture is centred and a tap on the plain text below it moves the hover off, awaited until no transition
 *  runs on the element and nothing in the document matches :active: a tap while the earlier tap's :active still holds leaves its
 *  target without :active, so its pressed frames would not be the ones read. Every frame under 3:1, or one paintedRatio refuses, is
 *  pushed onto `fails`; `note` carries every frame. The tap must open the tab once (window.open, stubbed by the caller), and at least
 *  one frame must be read while the element matches :active (a guard: reads that start after the pressed frames pass over the
 *  highlight). */
async function tapFrames(page: any, cdp: any, alt: string, kind: "control" | "mark", where: string, fails: string[], note: (m: string) => void): Promise<void> {
  await page.evaluate((alt: string) => { (Array.from(document.querySelectorAll(".fileview-md img")).find((i) => i.getAttribute("alt") === alt) as HTMLElement).scrollIntoView({ block: "center" }); }, alt);
  await settleScroll(page);
  const off = await page.evaluate((alt: string) => {
    const ib = (Array.from(document.querySelectorAll(".fileview-md img")).find((i) => i.getAttribute("alt") === alt) as HTMLElement).getBoundingClientRect(), bb = (document.querySelector(".fileview-body") as HTMLElement).getBoundingClientRect();
    const para = Array.from(document.querySelectorAll(".fileview-md > p")).map((e) => e.getBoundingClientRect()).find((r) => r.top > ib.bottom + 4 && r.top + 6 < bb.bottom);
    return para ? { x: para.left + 20, y: para.top + 5 } : null;
  }, alt);
  assert.ok(off, where + ": " + alt + ": a paragraph of plain text below the picture, inside the body, to tap first");
  await tapAt(cdp, off!.x, off!.y);
  await page.waitForFunction(([alt, kind]: [string, string]) => {
    const img = Array.from(document.querySelectorAll(".fileview-md img")).find((i) => i.getAttribute("alt") === alt) as HTMLElement;
    const el = (kind === "mark" ? img : img.nextElementSibling) as HTMLElement;
    return !el.matches(":active") && !el.matches(":hover") && el.getAnimations().every((a) => a.playState !== "running") && document.querySelector(":active") === null;
  }, [alt, kind], { timeout: 3000 });
  await frames(page, 2);
  const before = await tapTarget(page, alt, kind);
  const opens = (await page.evaluate(() => (window as any).__opened.length)) as number;
  await tapAt(cdp, before.x, before.y);
  const t0 = Date.now();
  const reads: Array<{ ms: number; active: boolean; hover: boolean; ratio: number | null; dash: string; ground: string; refused: string | null }> = [];
  let settled = false;
  while (!settled && Date.now() - t0 < 3000) {
    const s = await tapTarget(page, alt, kind);
    const p: Painted | Error = await paintedRatio(page, alt, kind, "hover").catch((e: Error) => e);
    const after = await tapTarget(page, alt, kind);
    const ms = Date.now() - t0;
    if (p instanceof Error) reads.push({ ms, active: s.active, hover: s.hover, ratio: null, dash: "", ground: "", refused: p.message.split("\n")[0] });
    else reads.push({ ms, active: s.active, hover: s.hover, ratio: +p.ratio.toFixed(3), dash: p.dash, ground: p.ground, refused: null });
    settled = reads.some((r) => r.active) && !s.active && !s.running && !after.active && !after.running;   // the read stood wholly after the pressed frames, with no transition running either side of it
  }
  const what = kind === "control" ? "the web control after " + alt : "the mark on " + alt;
  note("tap, " + where + ": " + what + " (tap highlight " + before.highlight + "): " + reads.map((r) => r.ms + " ms" + (r.active ? " :active" : "") + (r.hover ? " :hover" : "") + " " + (r.ratio === null ? "refused" : r.ratio.toFixed(3) + ":1 " + r.dash + " over " + r.ground)).join("; "));
  assert.ok(settled, where + ": the frames of the tap on " + what + " settle within 3 s, the pressed frames over and no transition running (" + reads.length + " read)");
  assert.equal((await page.evaluate(() => (window as any).__opened.length)) - opens, 1, where + ": the tap on " + what + " opens the tab once");
  assert.ok(reads.some((r) => r.active), where + ": a frame of " + what + " is read while it matches :active, so the tap's pressed frames are read (the first read at " + reads[0].ms + " ms)");
  for (const r of reads) {
    // FAILS BEFORE the sheets' tap rule, on the phone alone: the control's pressed frames at 2.578:1 dark and 2.531:1 light in the frames read, the default highlight over the line
    if (r.ratio === null) fails.push(where + ": " + what + " " + r.ms + " ms after the tap" + (r.active ? ", :active" : "") + ": its line as painted is refused, " + r.refused);
    else if (r.ratio < 3) fails.push(where + ": " + what + " " + r.ms + " ms after the tap" + (r.active ? ", :active" : "") + " paints " + r.dash + " over " + r.ground + ", " + r.ratio.toFixed(3) + ":1, under the 3:1 floor (tap highlight " + before.highlight + ")");
  }
}
for (const device of ["phone", "touch", "laptop"] as TapDevice[]) {
  test("in a browser on " + TAP_ON[device] + ", a finger's tap on the web control and on the mark, on the chat modal, the feed and the Files pane in both themes: each frame read from the tap until it settles, one screenshot about every 33 ms, the tap's pressed frames while the element matches :active among them, paints the line at 3:1 or better, and the tap opens the tab once (the tap-highlight ruling of 2026-09-24: on the phone the browser's default tap highlight painted the control's pressed frames down to 2.578:1 dark and 2.531:1 light in the frames read; the mark takes no highlight, and under CDP touch and on the laptop the default highlight stays above 3:1, keep cells green without the sheets' tap rule by design; a property pin read off the paint)", { timeout: 240000 }, async (t) => {
    const fails: string[] = [];
    const note = (m: string) => t.diagnostic(m);
    const second = await secondServer([], TINY_SIZES);
    try {
      await inBrowser(t, async (browser) => {
        for (const surface of ["chat", "feed", "pane"] as Surface[]) {
          const { page, errors } = await openTiny(device === "phone" ? phonePages(browser) : browser, second, surface);
          try {
            await page.evaluate(() => { const w = window as any; w.__opened = []; window.open = ((u: unknown) => { w.__opened.push(String(u)); return { opener: null }; }) as unknown as typeof window.open; });
            const cdp = await page.context().newCDPSession(page);
            if (device === "touch") { await cdp.send("Emulation.setTouchEmulationEnabled", { enabled: true, maxTouchPoints: 1 }); await frames(page, 2); }
            const env = await page.evaluate(() => ({ hoverNone: matchMedia("(hover: none)").matches, coarse: matchMedia("(pointer: coarse)").matches, anyCoarse: matchMedia("(any-pointer: coarse)").matches, dpr: devicePixelRatio, scale: window.visualViewport ? window.visualViewport.scale : null, width: window.innerWidth, meta: !!document.querySelector('meta[name="viewport"]') }));
            note("device " + JSON.stringify({ device, surface, env }));
            assert.equal(env.dpr, 1, surface + ": one device pixel per CSS pixel");
            assert.equal(env.scale, 1, surface + ": the visual viewport at scale 1");
            assert.equal(env.width, 900, surface + ": the layout viewport is the 900 px window");
            if (device === "laptop") assert.ok(!env.hoverNone && !env.coarse && env.anyCoarse, surface + ": the laptop's media, hover and a fine primary pointer beside a coarse one: " + JSON.stringify(env));
            else assert.ok(env.hoverNone && env.coarse, surface + ": no hover, a coarse pointer: " + JSON.stringify(env));
            if (device === "phone") assert.equal(env.meta, true, surface + ": the phone's page carries the viewport meta");
            const where = TAP_ON[device] + ", " + (surface === "chat" ? "the chat modal" : surface === "feed" ? "the feed" : "the Files pane");
            for (const theme of ["dark", "light"] as const) {
              await page.evaluate((light: boolean) => new Promise<void>((done) => { const c = document.querySelectorAll(".fileview-md img")[2].nextElementSibling as HTMLElement; c.addEventListener("transitionend", () => done(), { once: true }); setTimeout(done, 1500); document.body.classList.toggle("theme-light", light); }), theme === "light");
              await frames(page, 2);
              await tapFrames(page, cdp, "big", "control", where + ", " + theme + " theme", fails, note);
              await tapFrames(page, cdp, "build", "mark", where + ", " + theme + " theme", fails, note);
            }
            assert.deepEqual(errors, [], surface + ": no page errors");
          } finally { await page.close(); }
        }
      }, device === "laptop" ? { args: [LAPTOP] } : {});
    } finally { await second.close(); }
    assert.deepEqual(fails, [], "each frame read of a finger's tap on the outbound dress paints its line at 3:1 or better against the ground the sheet controls (a property pin read off the paint, one screenshot about every 33 ms):\n" + fails.join("\n"));
  });
}

// The control in right-to-left text (the file review's round 15, ui-2): the sheets place the control with logical margins, -28px at
// the line's start and 6px at its end, so in a block an author wrote dir="rtl" (the sanitizer keeps it) the control follows the
// picture on its left and stands over the picture's top-left corner, its inline-end corner, as it stands over the top-right in
// left-to-right text; the float twins keep physical margins of their own, since an author's align is physical. With the physical
// margins the sheets had, the control stood beside the picture's left edge, 6px outside it, and at a width of 360px on the chat and the
// feed 6 of its 22px lay outside the viewer's body and were clipped. The right-to-left pictures are red there; the left-to-right
// picture and both floats inside a right-to-left block are controls, green there by design.
const RTL_WORDS = "\u05e9\u05dc\u05d5\u05dd \u05e2\u05d5\u05dc\u05dd \u05d4\u05de\u05e9\u05da \u05d4\u05d8\u05e7\u05e1\u05d8";   // Hebrew words, strong right-to-left text on both sides of the picture
const RTL_TEXT = "# Report\n\n" + PARA(1) + "\n\n"
  + '<div dir="rtl">\n\n<img src="' + WEB + '/rtl-web.svg" alt="rtl-web"> ' + RTL_WORDS + "\n\n</div>\n\n" + PARA(2) + "\n\n"
  + '<p dir="rtl">' + RTL_WORDS + ' <img src="figs/plot.svg" alt="rtl-local"> ' + RTL_WORDS + "</p>\n\n" + PARA(3) + "\n\n"
  + '<img src="' + WEB + '/ltr-web.svg" alt="ltr-web"> after text\n\n' + PARA(4) + "\n\n"
  + '<div dir="rtl">\n\n<img src="' + WEB + '/rtl-left.svg" alt="rtl-left" align="left"> ' + RTL_WORDS + " " + RTL_WORDS + "\n\n</div>\n\n" + PARA(5) + "\n\n" + PARA(6) + "\n\n" + PARA(7) + "\n\n"
  + '<div dir="rtl">\n\n<img src="' + WEB + '/rtl-right.svg" alt="rtl-right" align="right"> ' + RTL_WORDS + " " + RTL_WORDS + "\n\n</div>\n\n" + PARA(8) + "\n\n" + PARA(9) + "\n\n" + PARA(10) + "\n";
const RTL_DOCS: Record<string, string> = { [REPORT]: RTL_TEXT, [PLOT]: svg("#456") };
/** Each picture of the right-to-left report and where its control stands: the corner it must stand over ("left" or "right"), the
 *  direction the picture's line runs, and whether it is a control (green over the physical margins by design). */
const RTL_CELLS: Array<[string, "left" | "right", "rtl" | "ltr", string, boolean]> = [
  ["rtl-web", "left", "rtl", "a picture from the web in a right-to-left block", false],
  ["rtl-local", "left", "rtl", "a local picture in a right-to-left paragraph", false],
  ["ltr-web", "right", "ltr", "a picture from the web in left-to-right text (a control)", true],
  ["rtl-left", "right", "rtl", "a left-floated picture in a right-to-left block (a control)", true],
  ["rtl-right", "left", "rtl", "a right-floated picture in a right-to-left block (a control)", true],
];
type RtlRead = { dir: string; img: Box; ctl: Box | null; classes: string; body: { left: number; right: number }; hit: string | null };
for (const surface of ["chat", "feed", "pane"] as Surface[]) for (const width of [900, 360]) {
  test("in a browser (a fine pointer) on " + (surface === "chat" ? "the chat modal" : surface === "feed" ? "the feed" : "the Files pane") + " at " + width + "px, the control in right-to-left text: a picture from the web in a block an author wrote dir=\"rtl\" and a local one in such a paragraph each have their control over the picture's top-left corner, its line's end, 6px in and inside the picture's box and the viewer's body, while a picture in left-to-right text keeps its control at the top-right and a left and a right float in a right-to-left block keep theirs at the corner away from the float's side (the file review's round 15, ui-2: with physical margins the control stood 6px outside the picture's left edge in right-to-left text, and at 360px on the chat and the feed 6 of its 22px were clipped; a property pin read off the layout)", { timeout: 120000 }, async (t) => {
    const second = await secondServer([]);
    try {
      await inBrowser(t, async (browser) => {
        const before = async (pg: any): Promise<void> => {
          await pg.context().route((u: URL) => u.href.startsWith(WEB + "/"), async (route: any) => {
            const a = await fromSecond(second.port, new URL(route.request().url()).pathname);
            return route.fulfill({ status: a.status, contentType: a.type, body: a.body });
          });
        };
        const { page, errors } = await openViewer(browser, surface, width, 800, { docs: RTL_DOCS, before,
          serve: (u) => { const p = u.pathname === "/file" ? u.searchParams.get("path") || "" : ""; return RTL_DOCS[p] !== undefined && /\.svg$/.test(p) ? { status: 200, type: "image/svg+xml", body: RTL_DOCS[p] } : null; } });
        try {
          await page.click('[data-act="fv-load"]');
          await page.waitForFunction((n: number) => { const imgs = Array.from(document.querySelectorAll(".fileview-md img")) as HTMLImageElement[]; return imgs.length === n && imgs.every((i) => !i.closest('[data-act="fv-load"]') && i.complete && i.naturalWidth > 0 && !!i.nextElementSibling && i.nextElementSibling.hasAttribute("data-fv-figopen")); }, RTL_CELLS.length, { timeout: 15000 });
          await frames(page, 3);
          const fails: string[] = [];
          for (const [alt, corner, dir, what, control] of RTL_CELLS) {
            const r: RtlRead = await page.evaluate((alt: string) => {
              const img = Array.from(document.querySelectorAll(".fileview-md img")).find((i) => i.getAttribute("alt") === alt) as HTMLElement;
              img.scrollIntoView({ block: "center" });
              const box = (e: Element) => { const b = e.getBoundingClientRect(); return { left: b.left, top: b.top, right: b.right, bottom: b.bottom, width: b.width, height: b.height }; };
              const c = img.nextElementSibling && img.nextElementSibling.hasAttribute("data-fv-figopen") ? img.nextElementSibling : null;
              const body = document.querySelector(".fileview-body") as HTMLElement; const bb = body.getBoundingClientRect();
              let hit: string | null = null;
              if (c) { const cb = c.getBoundingClientRect(); const e = document.elementFromPoint(cb.left + 1, cb.top + cb.height / 2); hit = e ? (c.contains(e) ? "the control" : e.localName + (e.className ? "." + String(e.className).split(" ")[0] : "")) : null; }
              return { dir: getComputedStyle(img).direction, img: box(img), ctl: c ? box(c) : null, classes: c ? c.className : "", body: { left: bb.left + body.clientLeft, right: bb.left + body.clientLeft + body.clientWidth }, hit };
            }, alt);
            t.diagnostic(surface + " " + width + " " + alt + ": " + JSON.stringify(r));
            // preconditions: the picture's line runs the way the cell names, the control stands after it, a float's carries its class
            assert.equal(r.dir, dir, surface + " " + width + ": " + what + ": its line runs " + dir);
            assert.ok(r.ctl, surface + " " + width + ": " + what + ": its control stands after it");
            if (alt === "rtl-left" || alt === "rtl-right") assert.ok(r.classes.includes(alt === "rtl-left" ? "fv-figopen-left" : "fv-figopen-right"), surface + " " + width + ": " + what + ": its control carries the float class: " + r.classes);
            const c = r.ctl!, i = r.img;
            const at = corner === "left" ? Math.abs(c.left - (i.left + 6)) <= 1 : Math.abs(c.right - (i.right - 6)) <= 1;
            const inside = c.left >= i.left - 0.5 && c.right <= i.right + 0.5 && c.top >= i.top - 0.5 && c.bottom <= i.bottom + 0.5;
            const inBody = c.left >= r.body.left - 0.5 && c.right <= r.body.right + 0.5;
            const read = surface + " " + width + "px: " + what + ": the control at [" + [c.left, c.top, c.right, c.bottom].map((v) => v.toFixed(1)).join(", ") + "], the picture at [" + [i.left, i.top, i.right, i.bottom].map((v) => v.toFixed(1)).join(", ") + "], the body's box from " + r.body.left.toFixed(1) + " to " + r.body.right.toFixed(1) + ", its left edge hits " + r.hit;
            // FAILS BEFORE (the physical margins) for the two right-to-left pictures that do not float: the control 6px outside
            // the picture's left edge, and at 360px on the chat and the feed 6px of it outside the body's box
            if (!at || Math.abs(c.top - (i.top + 6)) > 1) fails.push(read + ": not over the picture's top-" + corner + " corner, 6px in" + (control ? " (a control)" : ""));
            if (!inside) fails.push(read + ": not inside the picture's box" + (control ? " (a control)" : ""));
            if (!inBody || r.hit !== "the control") fails.push(read + ": not inside the viewer's body, where it would be clipped" + (control ? " (a control)" : ""));
          }
          assert.deepEqual(fails, [], "each picture's control stands over the corner at its line's end, 6px in, inside the picture's box and the viewer's body, in right-to-left text as in left-to-right, a float's at the corner away from its side (a property pin read off the layout):\n" + fails.join("\n"));
          assert.deepEqual(errors, [], "no page errors");
        } finally { await page.close(); }
      });
    } finally { await second.close(); }
  });
}

// ── the one gate between a gesture and a web picture's tab (the file review's round 16, extra5-1, with the coordinator's decisions 2
// to 5 on it) ── A tap, a click, a Cmd/Ctrl-click, Enter or Space on a loaded picture from the web opened its tab while the picture's
// web control stood off the screen, with nothing on the screen saying the open leaves for another host, on every device class: the
// click road had no counterpart of the key gate. The gate (file-view.ts openFigure, webGestureShown, the key gate, signShown) lets a
// gesture open the tab only while the picture's sign, its control or on a picture that wears none its mark, is in view and uncovered,
// read at the gesture's start (a pointer's or a finger's press in the window's capture phase, the first keydown of a key), and a
// refused gesture opens nothing and scrolls the sign into view, moving no focus, so the next gesture opens. The cells, each on the chat
// modal and the Files pane at 900 by 700 unless named, each in a browser of its own, the pictures from the web routed at the context
// (a document request answered with a page of its own and counted, an image request answered with a picture of the path's size), the
// opens counted as the popups the context sees and the document requests the route answered, never a window.open stub (the pinch
// cells alone keep the key gate's stubbed report, focusReady), the gates loaded, every value synthetic:
// - the out-of-view scene, the refuters': a remote picture 300 by 1400, taller than the body, its control's box above the body's padding
//   box (asserted, and the gesture's point hit-testing to the picture, as the case's premise), for a tap under CDP touch emulation, a
//   phone's tap, a finger's tap on the touchscreen laptop (LAPTOP), a fine click and a fine Ctrl-click (the key held around the click):
//   the first gesture opens nothing, leaves the control in view, the viewer on the report and the keyboard off the control, and a
//   second gesture on the picture's visible part, its point read again after the reveal and its click's detail 1 (asserted), opens
//   once; red at the head the file review's round 16 read by one popup and one document request on the first gesture. Beside it, keep cells green there by
//   design: the same gesture with the control centred opens once, and so does the sliver, the control's bottom 2px inside the body
//   (red under a hit test that samples the control's whole box, whose upper points meet the viewer's bar);
// - the keys, a fine pointer: Enter and Space on the control reached by Tab and scrolled out of view: the first key opens nothing and
//   reveals the control, Space leaving it unpressed, and the second opens once (red at the head the file review's round 16 read by the second key, since
//   nothing revealed the control); with the control centred each key opens once (keep);
// - one gesture's later events (decision 2): a double click and, in Chromium, a double tap on the out-of-view picture open nothing
//   (two at the round-16 head), the second click of each carrying detail 2 (in Firefox and WebKit each tap's click carries detail 1,
//   so the second tap is read at its own start and opens once after the first tap's reveal, the tap cells' double tap; the
//   coordinator's decision 1 on the file review's round 17), Enter and Space held on the out-of-view control through two repeats open nothing (none at the head the file review's round 16 read either,
//   by design; red under a gate that reads the repeat and the release afresh, since the first keydown's reveal put the control on the
//   screen);
// - covered signs (decisions 4 and 5), each but the author's overlay red at the head the file review's round 16 read by one open: the Outline popover over the control of a picture
//   490 wide, a click and a tap on the picture's visible part, the popover closed by that press, and a second gesture then opens once;
//   the text-size flyout over the same control with its top 3px inside the body, a click and a tap the same way, and the keyboard,
//   Tab to the control with the flyout opened by Enter still open, then Enter, which opens nothing and closes the flyout, the viewer's
//   own chrome, since no other key but Escape closes it, and a second Enter, which opens once (red under the gate before the key's
//   refusal closed the flyout by the second Enter, the flyout still open); an author's element of two page classes laid over the
//   figure (`picker-overlay tx-starting`), which the sheets would position fixed over the whole Rendered box above the control, has
//   its raising class taken off (dropStackClasses), so it stands static in the flow off the control, and Tab then Enter, fine and
//   under touch, and under touch a tap at the picture's point each open once with the control shown (red at the head the file
//   review's round 16 read by the element's state, its class and its fixed position over the control's centre, and under touch by
//   the tap, which the fixed element took, Enter opening once there; and red at 2f5d29017, before the author's closing pass after
//   the file review's round 17 took the class off, by the state, by Enter and, under touch, by the tap); and an author's element a
//   press would pass through, whose page class, style declaration or inert attribute the viewer takes off (dropPressThrough; the block
//   before the middle button's guard says the rest, and what the drops leave of the cost the file review's round 16 disclosed);
// - the middle button (fact 1 of the rulings): on the picture with its control out of view, on the control and on the picture in view,
//   no open at either head, the auxclick firing (a guard);
// - the mark, under touch emulation: a picture from the web under the floor wearing the mark, scrolled wholly out of the body, and a
//   click dispatched on it (detail 0, which no pointer can deliver there): none at the fix, the picture in view after, and a second
//   dispatched click opens once (red at the head the file review's round 16 read by one open); a tap on the mark in view opens once (keep);
// - the anchors: a picture inside a `<picture>` and one inside a dead link, their controls out of view: the first fine click opens
//   nothing and leaves the control in view, and a second opens once (red at the head the file review's round 16 read by one open on the first click); in view
//   each opens once (keep); the reveal, the second open and the keep cells red under a gate that looks for the control after the img
//   instead of after its anchor;
// - the row: the Comments panel open under touch emulation (a coarse pointer, the layer's overlay off), a Ctrl-click refused on the
//   out-of-view picture opens nothing and stops before the row, whose listener would offer a comment (the row cell green at the head the file review's round 16 read,
//   which stopped the modified click before opening, and the opens cell red there by group A's open, since that head had no gate; red
//   under a gate placed before openFigure's stopPropagation);
// - a local picture, not gated: its control out of view, a Ctrl-click opens the kernel's /file URL in a tab and a plain click opens the
//   picture in the viewer (green at both heads; red under a gate that reads no target kind);
// - the pinch zoom, a fine pointer on the focus report: the top page zoomed to 3 with the big picture's control outside the top's
//   visual viewport and a click on the picture inside it, the viewer as the top page and in the dashboard's same-origin frame: the
//   click opens nothing and the control is inside the visual viewport after, and a second click opens once (red at the head the file review's round 16 read
//   by one open on the first click);
// - the tap cells (the file review's round 17, tests-1 with regression-1): file-figure-open-taps.ts's set, run here in Chromium on a
//   phone's pages and on a hybrid page, after the covered signs, where each tap's click carries its press's pointerId and every cell
//   reads the same at 0ab74924c as at the fix, by design; its header names each cell and the reds in WebKit, which
//   file-figure-open-engines-browser.test.ts runs with Firefox;
// - the stacking cells (the file review's round 17, extra9-1, and the coordinator's decision 4 on it): file-figure-open-stacking.ts's
//   set, run here in Chromium on the chat modal and the Files pane after the stacking shapes, a picture in a top-level table and inside
//   author elements of page classes that would make a stacking context around it, each red at 0ab74924c; its header names each cell,
//   and file-figure-open-engines-browser.test.ts runs the set in WebKit and Firefox.
// Each case collects its cells and asserts them once, so a red names every cell that differs; property pins read off the page, and
// file-view-outline.test.ts runs the gate's click and key guards in CI over the stand-in, WebKit's tap order among them.
const GATE_SIZES: Record<string, [number, number]> = { "/tall.svg": [300, 1400], "/w490.svg": [490, 900], "/tiny.svg": [20, 20], "/pp.svg": [300, 1400], "/dl.svg": [300, 1400], "/ov.svg": [300, 200] };
const GATE_LOCAL = ROOT + "/docs/figs/gate-tall.svg";
const GATE_TEXT = "# Report\n\n" + PARA(1) + "\n\n![tall](" + WEB + "/tall.svg)\n\n" + Array.from({ length: 8 }, (_, i) => PARA(i + 2)).join("\n\n")
  + "\n\n![localtall](figs/gate-tall.svg)\n\n" + Array.from({ length: 8 }, (_, i) => PARA(i + 10)).join("\n\n")
  + '\n\n<picture><img src="' + WEB + '/pp.svg" alt="pp"></picture>\n\n' + Array.from({ length: 8 }, (_, i) => PARA(i + 20)).join("\n\n")
  + "\n\n[![dl](" + WEB + "/dl.svg)](localhost:8080)\n\n" + Array.from({ length: 8 }, (_, i) => PARA(i + 30)).join("\n\n")
  + "\n\nA badge ![tiny](" + WEB + "/tiny.svg) in words.\n\n" + Array.from({ length: 16 }, (_, i) => PARA(i + 40)).join("\n\n") + "\n";
const COVER_TEXT = "# Report\n\n## Alpha\n\n" + PARA(1) + "\n\n![w490](" + WEB + "/w490.svg)\n\n## Beta\n\n" + Array.from({ length: 12 }, (_, i) => PARA(i + 3)).join("\n\n") + "\n\n## Gamma\n\n" + PARA(20) + "\n";
const OVERLAY_TEXT = "# Report\n\n" + PARA(1) + "\n\n![ov](" + WEB + "/ov.svg)\n\n" + '<div id="pt" class="picker-overlay tx-starting"></div>' + "\n\n" + Array.from({ length: 12 }, (_, i) => PARA(i + 3)).join("\n\n") + "\n";
type GateDevice = "fine" | "ctrl" | "touch" | "phone" | "laptop";
type GateOpens = { popups: number; docs: number; urls: string[]; fileTabs: string[] };
type GateRead = { sign: number[]; img: number[]; port: number[]; raw: number[]; z: number; inView: boolean; outside: boolean; signHit: boolean; base: string; active: string; pressed: boolean; pt: { x: number; y: number }; pt2: { x: number; y: number }; hit: string; hit2: string };
type GateScene = { page: any; cdp: any; read: (alt: string) => Promise<GateRead>; place: (alt: string, dy: number) => Promise<GateRead>; placeX: (alt: string, dx: number) => Promise<GateRead>; opens: () => Promise<GateOpens>; gesture: (how: GateDevice | "double" | "doubletap" | "middle", x: number, y: number) => Promise<void>; clicks: () => Promise<Array<{ detail: number; button: number; target: string }>>; cell: (what: string, want: unknown, got: unknown) => void };
/** In the viewer's document: the picture of an alt, its anchor by figureAnchor's climb, its sign (the control after the anchor, else the
 *  picture wearing the mark), the control alone (`__ctl` and `__img`, the names the focus helpers read), a log of every click's detail
 *  at the window, and `__gread`, the sign's and the picture's boxes, the body's padding box, whether the sign meets that box and the
 *  window (in view) or lies wholly outside the box, the bar's name, the keyboard's holder, the sign's :active, and two points on the
 *  picture's visible part with what each hit-tests to: the first near its bottom-left, the second well inside its top half and away from
 *  the first (a finger's second tap there is no double tap). The body's padding box is read in the window's pixels, its border and
 *  client size scaled by its zoom (`z`, currentCSSZoom; 1 on a page with no body zoom), beside what the unscaled client size spans
 *  (`raw`, the read before the file review's round 16, fresh-1), and `signHit` says whether the element at the centre of the sign's
 *  part inside the window is the sign or inside it; `__gplace` puts the sign's top `dy` window pixels below the body's padding top
 *  and `__gplaceX` its left `dx` past the body's padding right, each dividing the move by the zoom, since scrollTop and scrollLeft are
 *  in the body's own CSS pixels. */
const GATE_INSTALL = (): void => {
  const w = window as any;
  w.__img = (alt: string) => Array.from(document.querySelectorAll(".fileview-md img")).find((i) => i.getAttribute("alt") === alt) as HTMLElement;
  w.__ganchor = (img: Element) => { let a: Element = img; for (let p = a.parentElement; p && p.querySelectorAll("img").length === 1 && (p.localName === "picture" || p.classList.contains("fc-imgwrap") || (p.localName === "a" && p.children.length === 1 && p.children[0] === a && (p.textContent || "").trim() === "")); p = a.parentElement) a = p; return a; };
  w.__ctl = (alt: string) => { const n = w.__ganchor(w.__img(alt)).nextElementSibling; return n && n.hasAttribute("data-fv-figopen") ? n as HTMLElement : null; };
  w.__gsign = (alt: string) => w.__ctl(alt) || (w.__img(alt).hasAttribute("data-fv-figweb") ? w.__img(alt) : null);
  if (!w.__gclicks) { w.__gclicks = []; window.addEventListener("click", (e: MouseEvent) => { const t = e.target as Element | null; w.__gclicks.push({ detail: e.detail, button: e.button, target: t ? t.localName + (t.getAttribute("alt") ? ":" + t.getAttribute("alt") : "") : "null" }); }, true); window.addEventListener("auxclick", (e: MouseEvent) => { w.__gclicks.push({ detail: e.detail, button: e.button, target: "auxclick" }); }, true); }
  w.__gread = (alt: string) => {
    const s = w.__gsign(alt) as HTMLElement, img = w.__img(alt) as HTMLElement, b = document.querySelector(".fileview-body") as HTMLElement;
    const sr = s.getBoundingClientRect(), ir = img.getBoundingClientRect(), br = b.getBoundingClientRect(), z = (b as any).currentCSSZoom > 0 ? (b as any).currentCSSZoom : 1;
    const pl = br.left + b.clientLeft * z, pt = br.top + b.clientTop * z, pr = pl + b.clientWidth * z, pb = pt + b.clientHeight * z;
    const raw = [br.left + b.clientLeft, br.top + b.clientTop, br.left + b.clientLeft + b.clientWidth, br.top + b.clientTop + b.clientHeight];
    const sx = (Math.max(sr.left, 0) + Math.min(sr.right, innerWidth)) / 2, sy = (Math.max(sr.top, 0) + Math.min(sr.bottom, innerHeight)) / 2, se = document.elementFromPoint(sx, sy);
    const inView = sr.right > Math.max(pl, 0) && sr.left < Math.min(pr, innerWidth) && sr.bottom > Math.max(pt, 0) && sr.top < Math.min(pb, innerHeight);
    const top = Math.max(ir.top, pt), bottom = Math.min(ir.bottom, pb, innerHeight);
    const p1 = { x: Math.round(ir.left + 40), y: Math.round(bottom - 30) }, p2 = { x: Math.round(ir.left + Math.min(150, ir.width / 2)), y: Math.round(Math.min(top + 140, (top + bottom) / 2)) };
    const hitName = (p: { x: number; y: number }) => { const e = document.elementFromPoint(p.x, p.y); return !e ? "null" : e === img ? "the picture" : s.contains(e) ? "the sign" : e.localName + (typeof e.className === "string" && e.className ? "." + e.className.trim().split(/\s+/).join(".") : ""); };
    const a = document.activeElement;
    const r = (x: DOMRect) => [x.left, x.top, x.right, x.bottom].map((v) => Math.round(v * 10) / 10);
    return { sign: r(sr), img: r(ir), port: [pl, pt, pr, pb].map((v) => Math.round(v * 10) / 10), raw: raw.map((v) => Math.round(v * 10) / 10), z, inView, outside: sr.bottom <= pt || sr.top >= pb || sr.right <= pl || sr.left >= pr, signHit: !!se && s.contains(se),
      base: (document.querySelector(".fileview-base") as HTMLElement | null)?.textContent || "", active: a === s ? "the sign" : a === b ? "the body" : a ? a.localName : "null", pressed: s.matches(":active"), pt: p1, pt2: p2, hit: hitName(p1), hit2: hitName(p2) };
  };
  const zoomOf = (b: HTMLElement): number => ((b as any).currentCSSZoom > 0 ? (b as any).currentCSSZoom : 1);
  w.__gplace = (alt: string, dy: number) => { const s = w.__gsign(alt) as HTMLElement, b = document.querySelector(".fileview-body") as HTMLElement, z = zoomOf(b); b.scrollTop += (s.getBoundingClientRect().top - (b.getBoundingClientRect().top + b.clientTop * z) - dy) / z; };
  w.__gplaceX = (alt: string, dx: number) => { const s = w.__gsign(alt) as HTMLElement, b = document.querySelector(".fileview-body") as HTMLElement, z = zoomOf(b); b.scrollLeft += (s.getBoundingClientRect().left - (b.getBoundingClientRect().left + (b.clientLeft + b.clientWidth) * z) - dx) / z; };
};
/** One case: a browser for the device (the laptop's flags at its launch, a phone's pages), `text` open on the surface at `size` with the
 *  remote pictures routed and loaded through the gate and the local one served at the /file route, CDP's touch emulation after the load
 *  for `touch`, the helpers installed, `body` run with the scene, and the cells asserted once at the end; the record goes to the test's
 *  diagnostic whatever happens. `theme` is CSS inlined after the surface's sheet (openViewer's option), for the body zoom in the VS Code
 *  extension's zoomStyle shape. */
async function gateCase(t: any, device: GateDevice, surface: Surface, text: string, rec: Record<string, unknown>, body: (g: GateScene) => Promise<void>, size: [number, number] = [900, 700], theme = "", forced = 0): Promise<void> {
  const docReqs: string[] = [];
  const cells: Array<[string, unknown, unknown]> = [];
  let ran = false;
  await inBrowser(t, async (browser) => {
    ran = true;
    const before = async (pg: any): Promise<void> => {
      await pg.context().route((u: URL) => u.href.startsWith(WEB + "/"), async (route: any) => {
        const req = route.request();
        if (req.resourceType() === "document") { docReqs.push(req.url()); return route.fulfill({ status: 200, contentType: "text/html", body: "<p>third party</p>" }); }
        const s = GATE_SIZES[new URL(req.url()).pathname] || [300, 200];
        return route.fulfill({ status: 200, contentType: "image/svg+xml", body: sized(s[0], s[1], "#6a3d9a") });
      });
    };
    const serve = (u: URL): { status: number; type: string; body: string } | null => (u.pathname === "/file" && u.searchParams.get("path") === GATE_LOCAL ? { status: 200, type: "image/svg+xml", body: sized(300, 1400, "#456") } : null);
    const host = forced > 0 ? { newPage: () => browser.newPage({ viewport: null }) } : device === "phone" ? phonePages(browser) : browser;   // a forced device scale lays the page out in the window, with no viewport emulation over it
    const { page, errors } = await openViewer(host, surface, size[0], size[1], { docs: { [REPORT]: text, [GATE_LOCAL]: sized(300, 1400, "#456") }, before, serve, theme });
    try {
      for (let i = 0; i < 20 && await page.evaluate(() => !!document.querySelector('.fileview-md [data-act="fv-load"]')); i++) { await page.evaluate(() => { (document.querySelector('.fileview-md [data-act="fv-load"]') as HTMLElement).click(); }); await frames(page, 3); }
      await page.waitForFunction(() => Array.from(document.querySelectorAll(".fileview-md img")).every((i) => (i as HTMLImageElement).complete && (i as HTMLImageElement).naturalWidth > 0), null, { timeout: 15000 });
      await frames(page, 4);
      await page.evaluate(GATE_INSTALL);
      const cdp: any = await page.context().newCDPSession(page);
      if (device === "touch") { await cdp.send("Emulation.setTouchEmulationEnabled", { enabled: true, maxTouchPoints: 1 }); await frames(page, 3); }
      const popups: any[] = [], fileTabs: string[] = [];
      page.context().on("page", (p: any) => { popups.push(p); });
      page.context().on("request", (r: any) => { if (r.resourceType() === "document" && r.url().startsWith(ORIGIN + "/file")) fileTabs.push(r.url()); });   // a tab at the kernel's /file route (a local picture's Cmd/Ctrl-click)
      let p0 = 0, d0 = 0, f0 = 0;
      const touch = async (x: number, y: number): Promise<void> => { await cdp.send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [{ x, y }] }); await cdp.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] }); };
      const scene: GateScene = {
        page, cdp,
        read: (alt) => page.evaluate((a: string) => (window as any).__gread(a), alt),
        place: async (alt, dy) => { await page.evaluate(([a, d]: [string, number]) => (window as any).__gplace(a, d), [alt, dy]); await frames(page, 3); return page.evaluate((a: string) => (window as any).__gread(a), alt); },
        placeX: async (alt, dx) => { await page.evaluate(([a, d]: [string, number]) => (window as any).__gplaceX(a, d), [alt, dx]); await frames(page, 3); return page.evaluate((a: string) => (window as any).__gread(a), alt); },
        opens: async () => {
          for (let i = 0; i < 12; i++) await frames(page, 2);
          await new Promise((r) => setTimeout(r, 350));   // a bounded settle for an open that must not come (a popup is a new page, no event of this one)
          const np = popups.slice(p0), docs = docReqs.slice(d0), files = fileTabs.slice(f0);
          p0 = popups.length; d0 = docReqs.length; f0 = fileTabs.length;
          const urls = np.map((p: any) => p.url());
          for (const p of np) await p.close().catch(() => null);
          await page.bringToFront().catch(() => null);
          return { popups: np.length, docs: docs.length, urls, fileTabs: files };
        },
        gesture: async (how, x, y) => {
          await page.evaluate(() => { (window as any).__gclicks.length = 0; });
          p0 = popups.length; d0 = docReqs.length; f0 = fileTabs.length;
          if (how === "fine") { await page.mouse.move(x, y); await page.mouse.click(x, y); }
          else if (how === "ctrl") { await page.mouse.move(x, y); await page.keyboard.down("Control"); await page.mouse.click(x, y); await page.keyboard.up("Control"); }   // mouse.click takes no modifiers option: the key is held around it
          else if (how === "double") { await page.mouse.move(x, y); await page.mouse.dblclick(x, y); }
          else if (how === "middle") { await page.mouse.move(x, y); await page.mouse.click(x, y, { button: "middle" }); }
          else if (how === "phone") await page.touchscreen.tap(x, y);
          else if (how === "doubletap") { await touch(x, y); await new Promise((r) => setTimeout(r, 90)); await touch(x, y); }   // two taps 90 ms apart at one point: in Chromium, which this leg launches, the second tap's click carries detail 2 (Firefox's and WebKit's carry 1)
          else await touch(x, y);   // CDP touch emulation, and the laptop's finger
          await frames(page, 2);
        },
        clicks: () => page.evaluate(() => (window as any).__gclicks.slice()),
        cell: (what, want, got) => { cells.push([what, want, got]); },
      };
      await body(scene);
      rec.errors = errors;
    } finally {
      rec.cells = cells.map(([what, want, got]) => ({ what, want, got }));
      t.diagnostic("record " + JSON.stringify({ device, surface, ...rec }));
      await page.close();
    }
    assert.deepEqual(errors, [], "no page errors");
  }, device === "laptop" ? { args: [LAPTOP] } : forced > 0 ? { args: ["--force-device-scale-factor=" + forced, "--window-size=" + size.join(",")] } : {});
  if (!ran) return;   // no browser: inBrowser skipped the case loudly
  assert.ok(cells.length > 0, "the case ran its cells");
  assert.deepEqual(cells.map(([what, , got]) => [what, got]), cells.map(([what, want]) => [what, want]), "each cell's reading, [cell, reading] (property pins read off the page)");
}
const gateOn = (device: GateDevice, surface: Surface): string => "(" + (device === "fine" ? "a fine click" : device === "ctrl" ? "a fine Ctrl-click" : device === "touch" ? "a tap under CDP touch emulation" : device === "phone" ? "a phone's tap" : "a finger's tap on the touchscreen laptop") + ", " + (surface === "chat" ? "the chat modal" : "the Files pane") + ")";
/** The number of opens as the case asserts them: the popups and the document requests together, which move as one at every head. */
const opensOf = (o: GateOpens): [number, number] => [o.popups, o.docs];

for (const device of ["touch", "phone", "laptop", "fine", "ctrl"] as GateDevice[]) for (const surface of ["chat", "pane"] as Surface[]) {
  test("in a browser " + gateOn(device, surface) + ", the one gate's out-of-view scene: a remote picture taller than the body, its control above the body's padding box: the first gesture on the picture's visible part opens nothing and leaves the control in view, the viewer on the report and the keyboard off the control, and a second gesture, its click of detail 1, opens once; keep cells: with the control centred the gesture opens once, and with the control's bottom 2px inside the body too (the file review's round 16, extra5-1: red at the head the file review's round 16 read by one popup and one document request on the first gesture; the keep cells green there by design, the sliver red under a hit test over the control's whole box)", { timeout: 180000 }, async (t) => {
    const rec: Record<string, unknown> = { scene: "out-of-view" };
    await gateCase(t, device, surface, GATE_TEXT, rec, async (g) => {
      const out = await g.place("tall", -60);
      rec.out = out;
      assert.ok(out.outside && out.sign[3] <= out.port[1] && out.hit === "the picture", "the control's box above the body's padding box and the gesture's point on the picture (the case's premise): " + JSON.stringify(out));
      await g.gesture(device, out.pt.x, out.pt.y);
      g.cell("the first gesture's opens [popups, document requests]", [0, 0], opensOf(await g.opens()));
      const after = await g.read("tall");
      rec.after = after;
      g.cell("after it: the control in view, the viewer on the report, the keyboard not on the control", [true, "report.md", false], [after.inView, after.base, after.active === "the sign"]);
      assert.equal(after.hit2, "the picture", "the second gesture's point, read after the reveal, on the picture (a precondition): " + JSON.stringify(after));
      await g.gesture(device, after.pt2.x, after.pt2.y);
      const clicks = await g.clicks();
      rec.secondClicks = clicks;
      assert.deepEqual(clicks.map((c) => c.detail), [1], "the second gesture's one click carries detail 1, a new run (a precondition): " + JSON.stringify(clicks));
      g.cell("the second gesture's opens", [1, 1], opensOf(await g.opens()));
      const mid = await g.place("tall", 200);
      assert.ok(mid.inView && mid.hit2 === "the picture", "the control centred in the body (a precondition): " + JSON.stringify(mid));
      await g.gesture(device, mid.pt2.x, mid.pt2.y);
      g.cell("keep: the control centred, the gesture's opens", [1, 1], opensOf(await g.opens()));
      const sliver = await g.place("tall", -20);
      rec.sliver = sliver;
      assert.ok(sliver.inView && sliver.sign[3] > sliver.port[1] && sliver.sign[3] <= sliver.port[1] + 2.5 && sliver.hit2 === "the picture", "the control's bottom 2px inside the body's padding box (a precondition): " + JSON.stringify(sliver));
      await g.gesture(device, sliver.pt2.x, sliver.pt2.y);
      g.cell("keep: the sliver, the gesture's opens", [1, 1], opensOf(await g.opens()));
    });
  });
}
/** Tab to the control of `alt` from a press on the report's first paragraph, the pointer then moved away; returns the presses. */
async function gateTab(g: GateScene, alt: string): Promise<number> {
  await g.page.evaluate(() => { const b = document.querySelector(".fileview-body") as HTMLElement; b.scrollTop = 0; b.scrollLeft = 0; });
  await frames(g.page, 2);
  const p = await g.page.evaluate(() => { const r = (document.querySelector(".fileview-md > p") as HTMLElement).getBoundingClientRect(); return { x: r.left + 20, y: r.top + 5 }; });
  await g.page.mouse.click(p.x, p.y);
  await g.page.mouse.move(5, 5);
  await frames(g.page, 2);
  return tabToControl(g.page, alt);
}
/** A key held on the keyboard's holder through CDP: its keydown, `repeats` keydowns with autoRepeat set (repeat true on the event), and
 *  its keyup. */
async function holdKey(g: GateScene, key: "Enter" | "Space", repeats: number, alt = ""): Promise<{ held: boolean; released: boolean }> {
  const k = key === "Enter" ? { key: "Enter", code: "Enter", windowsVirtualKeyCode: 13, text: "\r", unmodifiedText: "\r" } : { key: " ", code: "Space", windowsVirtualKeyCode: 32, text: " ", unmodifiedText: " " };
  await g.cdp.send("Input.dispatchKeyEvent", { type: "keyDown", ...k });
  for (let i = 0; i < repeats; i++) { await frames(g.page, 1); await g.cdp.send("Input.dispatchKeyEvent", { type: "keyDown", autoRepeat: true, ...k }); }
  await frames(g.page, 1);
  const held = alt ? (await g.read(alt)).pressed : false;   // the control's :active after the last repeat, the key still down
  await g.cdp.send("Input.dispatchKeyEvent", { type: "keyUp", key: k.key, code: k.code, windowsVirtualKeyCode: k.windowsVirtualKeyCode });
  await frames(g.page, 2);
  return { held, released: alt ? (await g.read(alt)).pressed : false };
}
for (const surface of ["chat", "pane"] as Surface[]) for (const key of ["Enter", "Space"] as const) {
  test("in a browser " + gateOn("fine", surface).replace("a fine click", "a fine pointer") + ", the one gate's keys: Tab to the web control, the body scrolled until the control is out of view, then " + key + ": no open, the control revealed" + (key === "Space" ? " and unpressed" : "") + ", and a second " + key + " opens once; keep: with the control centred " + key + " opens once (the file review's round 16, extra5-1: red at the head the file review's round 16 read by the second key, since nothing revealed the control; the keep cell green there by design)", { timeout: 180000 }, async (t) => {
    const rec: Record<string, unknown> = { scene: "keys", key };
    await gateCase(t, "fine", surface, GATE_TEXT, rec, async (g) => {
      rec.tabs = await gateTab(g, "tall");
      const out = await g.place("tall", -60);
      assert.ok(out.outside && out.active === "the sign", "the keyboard on the control, out of view above the body (a precondition): " + JSON.stringify(out));
      await g.page.keyboard.press(key);
      g.cell("the first " + key + "'s opens", [0, 0], opensOf(await g.opens()));
      const after = await g.read("tall");
      g.cell("after it: the control in view, holding the keyboard, unpressed", [true, true, false], [after.inView, after.active === "the sign", after.pressed]);
      await g.page.keyboard.press(key);
      g.cell("the second " + key + "'s opens", [1, 1], opensOf(await g.opens()));
      await g.place("tall", 200);
      await g.page.keyboard.press(key);
      g.cell("keep: the control centred, " + key + "'s opens", [1, 1], opensOf(await g.opens()));
    });
  });
}
for (const surface of ["chat", "pane"] as Surface[]) {
  test("in a browser (" + (surface === "chat" ? "the chat modal" : "the Files pane") + "), the one gate's later events of one gesture (the coordinator's decision 2, by the events' own fields and never by time): a fine double click and, in Chromium under CDP touch emulation, a double tap 90 ms apart on the out-of-view picture open nothing, the second click of each carrying detail 2 (two opens at the head the file review's round 16 read; in Firefox and WebKit each tap's click carries detail 1 and the second tap opens once, the tap cells' double tap); Enter and Space held on the out-of-view control through two repeats open nothing, and the held Space leaves the control unpressed after its second repeat and after its release (none at the head the file review's round 16 read either, and unpressed there, by design; each red under a gate that reads the repeats and the release afresh, the first keydown's reveal having put the control on the screen, where a repeat presses it)", { timeout: 180000 }, async (t) => {
    const rec: Record<string, unknown> = { scene: "one gesture" };
    await gateCase(t, "fine", surface, GATE_TEXT, rec, async (g) => {
      let out = await g.place("tall", -60);
      assert.ok(out.outside && out.hit === "the picture", "the control out of view, the point on the picture (a precondition): " + JSON.stringify(out));
      await g.gesture("double", out.pt.x, out.pt.y);
      const dbl = await g.clicks();
      rec.double = dbl;
      assert.deepEqual(dbl.map((c) => c.detail), [1, 2], "a double click: two clicks, of detail 1 and 2 (a precondition)");
      g.cell("a double click's opens", [0, 0], opensOf(await g.opens()));
      for (const key of ["Enter", "Space"] as const) {
        rec["tabs" + key] = await gateTab(g, "tall");
        out = await g.place("tall", -60);
        assert.ok(out.outside && out.active === "the sign", "the keyboard on the control, out of view (a precondition): " + JSON.stringify(out));
        const pr = await holdKey(g, key, 2, "tall");
        rec["pressed" + key] = pr;
        g.cell(key + " held through two repeats, opens", [0, 0], opensOf(await g.opens()));
        if (key === "Space") g.cell("Space held: the control pressed (:active) after the second repeat and after the release, [held, released] (a property pin read off the page)", [false, false], [pr.held, pr.released]);
      }
      await g.cdp.send("Emulation.setTouchEmulationEnabled", { enabled: true, maxTouchPoints: 1 });
      await frames(g.page, 3);
      out = await g.place("tall", -60);
      assert.ok(out.outside && out.hit === "the picture", "under touch, the control out of view, the point on the picture (a precondition): " + JSON.stringify(out));
      await g.gesture("doubletap", out.pt.x, out.pt.y);
      const taps = await g.clicks();
      rec.doubletap = taps;
      assert.deepEqual(taps.map((c) => c.detail), [1, 2], "a double tap in Chromium: two clicks, of detail 1 and 2 (a precondition)");
      g.cell("a double tap's opens", [0, 0], opensOf(await g.opens()));
    });
  });
}
for (const device of ["fine", "touch"] as GateDevice[]) for (const surface of ["chat", "pane"] as Surface[]) {
  test("in a browser " + gateOn(device, surface) + ", the one gate's covered sign, the Outline popover (the coordinator's decisions 4 and 5): the popover open over the web control of a picture 490 wide, the control 42px inside the body, a gesture on the picture's visible part opens nothing, the popover closed by that press, and a second gesture opens once (red at the head the file review's round 16 read by one open, where the popover's own capture listener closed it before the body read anything)", { timeout: 180000 }, async (t) => {
    const rec: Record<string, unknown> = { scene: "popover" };
    await gateCase(t, device, surface, COVER_TEXT, rec, async (g) => {
      await g.place("w490", 42);
      await g.page.evaluate(() => { (document.querySelector(".fileview-outline-btn") as HTMLElement).click(); });
      await frames(g.page, 3);
      const pre = await g.page.evaluate(() => { const w = window as any; const c = w.__ctl("w490").getBoundingClientRect(); const e = document.elementFromPoint((c.left + c.right) / 2, (c.top + c.bottom) / 2); return { open: !!document.querySelector(".fileview-outline"), overCentre: !!e && !!e.closest(".fileview-outline") }; });
      const r = await g.read("w490");
      rec.pre = { ...pre, read: r };
      assert.ok(pre.open && pre.overCentre && r.inView && r.hit === "the picture", "the popover open and over the control's centre, the control in view, the point on the picture (a precondition): " + JSON.stringify(rec.pre));
      await g.gesture(device, r.pt.x, r.pt.y);
      g.cell("the first gesture's opens", [0, 0], opensOf(await g.opens()));
      g.cell("the popover closed by that press", false, await g.page.evaluate(() => !!document.querySelector(".fileview-outline")));
      const r2 = await g.read("w490");
      await g.gesture(device, r2.pt2.x, r2.pt2.y);
      g.cell("the second gesture's opens", [1, 1], opensOf(await g.opens()));
    });
  });
}
for (const surface of ["chat", "pane"] as Surface[]) {
  for (const device of ["fine", "touch"] as GateDevice[]) test("in a browser " + gateOn(device, surface) + ", the one gate's covered sign, the text-size flyout (the coordinator's decisions 4 and 5, the flyout measured: at 900px it drops 29.6px into the body): the flyout open over the web control of a picture 490 wide, the control's top 3px inside the body, a gesture on the picture's visible part opens nothing, the flyout closed by that press, and a second gesture opens once (red at the head the file review's round 16 read by one open)", { timeout: 180000 }, async (t) => {
    const rec: Record<string, unknown> = { scene: "flyout" };
    await gateCase(t, device, surface, COVER_TEXT, rec, async (g) => {
      await g.place("w490", 3);
      await g.page.evaluate(() => { (document.querySelector(".fileview-zoom-btn") as HTMLElement).click(); });
      await frames(g.page, 3);
      const pre = await g.page.evaluate(() => { const w = window as any; const c = w.__ctl("w490").getBoundingClientRect(); const e = document.elementFromPoint((c.left + c.right) / 2, (c.top + c.bottom) / 2); const m = document.querySelector(".fileview-zoom-menu") as HTMLElement; return { open: !m.hidden, overCentre: !!e && (!!e.closest(".fileview-zoom-menu") || !!e.closest(".fileview-size-reset")) }; });
      const r = await g.read("w490");
      rec.pre = { ...pre, read: r };
      assert.ok(pre.open && pre.overCentre && r.inView && r.hit === "the picture", "the flyout open and over the control's centre, the control in view, the point on the picture (a precondition): " + JSON.stringify(rec.pre));
      await g.gesture(device, r.pt.x, r.pt.y);
      g.cell("the first gesture's opens", [0, 0], opensOf(await g.opens()));
      g.cell("the flyout closed by that press", true, await g.page.evaluate(() => (document.querySelector(".fileview-zoom-menu") as HTMLElement).hidden));
      const r2 = await g.read("w490");
      await g.gesture(device, r2.pt2.x, r2.pt2.y);
      g.cell("the second gesture's opens", [1, 1], opensOf(await g.opens()));
    });
  });
  test("in a browser " + gateOn("fine", surface).replace("a fine click", "a fine pointer") + ", the one gate's covered sign, the text-size flyout from the keyboard (the coordinator's decisions 4 and 5, and the coordinator's word on the key's reveal): Enter on the zoom glyph opens the flyout, Tab walks on to the web control of a picture 490 wide with the flyout still open over it, and Enter there opens nothing and closes the flyout, the viewer's own chrome, since no other key but Escape closes it, and a second Enter opens once (red at the head the file review's round 16 read by one open on the first Enter, and under the gate before the key's refusal closed the flyout by the second Enter, which opened nothing with the flyout still open)", { timeout: 180000 }, async (t) => {
    const rec: Record<string, unknown> = { scene: "flyout keys" };
    await gateCase(t, "fine", surface, COVER_TEXT, rec, async (g) => {
      await g.place("w490", 3);
      await g.page.mouse.move(5, 5);
      await g.page.focus(".fileview-zoom-btn");
      await g.page.keyboard.press("Enter");
      await frames(g.page, 3);
      let tabs = 0;
      for (; tabs < 40; tabs++) { if (await g.page.evaluate(() => document.activeElement === (window as any).__ctl("w490"))) break; await g.page.keyboard.press("Tab"); await frames(g.page, 1); }
      const pre = await g.page.evaluate(() => { const w = window as any; const c = w.__ctl("w490").getBoundingClientRect(); const e = document.elementFromPoint((c.left + c.right) / 2, (c.top + c.bottom) / 2); const m = document.querySelector(".fileview-zoom-menu") as HTMLElement; return { open: !m.hidden, overCentre: !!e && (!!e.closest(".fileview-zoom-menu") || !!e.closest(".fileview-size-reset")), active: document.activeElement === w.__ctl("w490") }; });
      const r = await g.read("w490");
      rec.pre = { ...pre, tabs, read: r };
      assert.ok(pre.open && pre.overCentre && pre.active && r.inView, "the keyboard on the control, in view under the open flyout (a precondition): " + JSON.stringify(rec.pre));
      await g.page.keyboard.press("Enter");
      g.cell("the first Enter's opens, and the flyout still open after it", [[0, 0], false], [opensOf(await g.opens()), await g.page.evaluate(() => !(document.querySelector(".fileview-zoom-menu") as HTMLElement).hidden)]);
      g.cell("the keyboard still on the control after the first Enter", true, await g.page.evaluate(() => document.activeElement === (window as any).__ctl("w490")));
      await g.page.keyboard.press("Enter");
      g.cell("the second Enter's opens, and the flyout still open", [[1, 1], false], [opensOf(await g.opens()), await g.page.evaluate(() => !(document.querySelector(".fileview-zoom-menu") as HTMLElement).hidden)]);
    });
  });
  for (const device of ["fine", "touch"] as GateDevice[]) test("in a browser " + gateOn(device, surface).replace("a fine click", "a fine pointer") + ", the one gate's covered sign, an author's element of a page class the sheets would raise, laid over the figure (the coordinator's decisions 4 and 5, continued): `<div class=\"picker-overlay tx-starting\">`, which the sheets would position fixed over the Rendered box and give a z-index above the control's, has its raising class taken off, so it stands static in the flow off the control; the body focused and Tab to the web control, then Enter opens once, and under touch a tap at the picture's point opens once too, the control shown (red at the head the file review's round 16 read by the element's state, its class and its fixed position over the control's centre, and under touch by the tap, which the fixed element took, Enter opening once there; and red at 2f5d29017, before the author's closing pass after the file review's round 17 took the raising class off, by the element's state, by Enter and, under touch, by the tap, each refused where the element stood over the control)", { timeout: 180000 }, async (t) => {
    const rec: Record<string, unknown> = { scene: "overlay" };
    await gateCase(t, device, surface, OVERLAY_TEXT, rec, async (g) => {
      const st = await g.page.evaluate(() => { const o = document.getElementById("user-content-pt") as HTMLElement | null; const w = window as any; const c = w.__ctl("ov"); const r = c.getBoundingClientRect(); const e = document.elementFromPoint((r.left + r.right) / 2, (r.top + r.bottom) / 2); return { overlay: !!o, classes: o ? o.getAttribute("class") : null, position: o ? getComputedStyle(o).position : null, overCentre: !!e && !!o && (e === o || o.contains(e)) }; });
      rec.state = st;
      assert.ok(st.overlay, "the author's element stands (a precondition): " + JSON.stringify(st));
      g.cell("the author's element after the paint: [its classes, its computed position, over the control's centre]", ["tx-starting", "static", false], [st.classes, st.position, st.overCentre]);
      await g.page.evaluate(() => { (document.querySelector(".fileview-body") as HTMLElement).focus(); });
      let tabs = 0;
      for (; tabs < 20; tabs++) { if (await g.page.evaluate(() => document.activeElement === (window as any).__ctl("ov"))) break; await g.page.keyboard.press("Tab"); await frames(g.page, 1); }
      rec.tabs = tabs;
      assert.ok(await g.page.evaluate(() => document.activeElement === (window as any).__ctl("ov")), "the keyboard on the control (a precondition)");
      await g.page.keyboard.press("Enter");
      g.cell("Enter on the control: its opens", [1, 1], opensOf(await g.opens()));
      if (device === "touch") {
        const r = await g.read("ov");
        await g.gesture("touch", r.pt.x, r.pt.y);
        g.cell("a tap at the picture's point (" + r.hit + "): its opens", [1, 1], opensOf(await g.opens()));
      }
    });
  });
}
// ── the one gate's tap cells in Chromium (the file review's round 17, tests-1 with regression-1, and the coordinator's decisions 1
// to 3 on it) ── file-figure-open-taps.ts holds the cells and says what each reads; file-figure-open-engines-browser.test.ts runs the
// same set in WebKit and Firefox, a leg of its own off the shared roster of browser legs. Chromium gives a tap's click the touch's own
// pointerId, so each tap's click finds the record under it, a precondition each tap cell asserts, and every cell reads the same at
// 0ab74924c as at the fix, by design (the stale records too: there the covered tap's own press was the record its click read);
// the double tap's second click carries detail 2 and opens nothing. The press with no click is a real two-finger touch here.
for (const device of ["phone", "hybrid"] as TapCellDevice[]) for (const surface of ["chat", "pane"] as TapSurface[]) {
  test("in Chromium on " + (device === "phone" ? "a phone's pages (hasTouch and isMobile at a device scale of 1, the kernel's viewport meta)" : "a hybrid page (hasTouch with a mouse)") + ", the " + (surface === "chat" ? "chat modal" : "Files pane") + ": the one gate's tap cells (the file review's round 17, tests-1 with regression-1): a tap on a loaded remote picture with its control in view opens once, on its control once, on a remote picture that wears the mark once; with the control out of view the first tap opens nothing and reveals it and the next opens once; a double tap there opens nothing, its second click of detail 2; under the text-size flyout or the Outline popover a tap opens nothing and closes it and the next opens once; " + (device === "hybrid" ? "after a right press of the mouse, or a mouse drag of the picture, with the control shown, then the flyout over the control, a tap opens nothing and the next opens once; " : "") + "Enter on the control opens once, after a refused tap too; a press with no click (a two-finger touch) begun out of view then Enter in view opens once, and one begun shown then the flyout over the control then a script's click opens nothing (every cell reading the same at 0ab74924c as at the fix, by design, Chromium's tap click carrying its press's pointerId; the Enter cells red under a gate that reads a key's click as a pointer's, the press cells under one that lets a key's or a script's click read the slot with the keydown's clear dropped)", { timeout: 300000 }, async (t) => {
    let cells: Array<[string, unknown, unknown]> = [];
    let ran = false;
    await inBrowser(t, async (browser) => {
      ran = true;
      cells = await tapCells(browser, "chromium", device, surface, (m) => t.diagnostic(m));
    });
    if (!ran) return;   // no browser: inBrowser skipped the case loudly
    for (const [what, , got] of cells) t.diagnostic("cell " + what + ": " + JSON.stringify(got));
    assert.ok(cells.length > 0, "the case ran its cells");
    assert.deepEqual(cells.map(([what, , got]) => [what, got]), cells.map(([what, want]) => [what, want]), "each cell's reading, [cell, reading] (property pins read off the page)");
  });
}
// ── what lets a press pass through an author's element, or raises it over the control, off the markup (the file review's round 16,
// extra5-1, the covered sign) ── The hit test at a gesture's start (elementFromPoint) reads the element a press would reach, and a press
// passes through an element a page class sets pointer-events none on, one whose style attribute does, and an inert one; file-view.ts
// dropPressThrough takes those off a file document's author markup, and dropStackClasses takes off the classes the sheets give a z-index
// at or above the control's, so no author element is left at or above the control's stacking level. Four scenes, each after
// a loaded remote picture 300 by 200 near the report's top: the locate-toast shape (a page class the sheets both position fixed and let a
// press pass through), whose class goes, so the element stands in the flow below the picture and a gesture opens with the control shown;
// and three shapes of a full-screen overlay of picker-overlay tx-starting (the sheets position picker-overlay fixed and give it a z-index
// above the control's): with a page class that sets pointer-events none (fc-overlay-off), with that declaration in its style attribute,
// and inert. In every scene dropStackClasses takes picker-overlay off, so the overlay falls into the flow off the control and the gesture
// opens with the control shown, where before that drop these scenes opened nothing. The drops narrow the cost the file review's round 16
// disclosed (an author's element laid over a picture kept it from opening) and do not close it: an element that a class the drops take
// off had placed over the figure no longer covers the control; an element that a page class the viewer keeps positions over a picture
// that wears the control rests below the control, whose z-index keeps it on top, so the control opens the picture on every gesture,
// while a press on the picture's own body lands on that element and opens nothing, and inside what was a stacking context around the
// picture the same holds, the shape the file review's round 17 found there (extra9-2) closed by the context drop and a top-level table's
// position and left; and an element a kept page class positions over a small picture that wears the mark still keeps that picture from
// opening, since the mark has no stacking level of its own and no button for a key to reach (its round 17, fresh-1). The two-way pin
// holding the raising list to the sheets is file-figure-open.test.ts's.
const PT_WORDS = Array.from({ length: 260 }, (_, i) => "word" + (i % 17)).join(" ");
const PT_OVERLAY = (cover: string): string => "# Report\n\n" + PARA(1) + "\n\n![ov](" + WEB + "/ov.svg)\n\n" + cover + "\n\n" + Array.from({ length: 12 }, (_, i) => PARA(i + 3)).join("\n\n") + "\n";
const PRESS_THROUGH: Array<{ scene: string; what: string; text: string; cls: string }> = [   // each element carries the id pt, which the sanitizer prefixes (user-content-pt), for the read to find it whatever its classes
  { scene: "toast", what: "the locate-toast shape by its page class, `<div class=\"locate-toast\">` holding words", text: "# Report\n\n" + PARA(1) + "\n\n![ov](" + WEB + "/ov.svg)\n\n" + '<div id="pt" class="locate-toast">' + PT_WORDS + "</div>" + "\n", cls: "" },
  { scene: "class", what: "the overlay with a page class that sets pointer-events none, `<div class=\"picker-overlay tx-starting fc-overlay-off\">`", text: PT_OVERLAY('<div id="pt" class="picker-overlay tx-starting fc-overlay-off"></div>'), cls: "tx-starting" },
  { scene: "inline", what: "the overlay with pointer-events none in its style attribute", text: PT_OVERLAY('<div id="pt" class="picker-overlay tx-starting" style="pointer-events: none"></div>'), cls: "tx-starting" },
  { scene: "inert", what: "the overlay inert, `<div class=\"picker-overlay tx-starting\" inert>`", text: PT_OVERLAY('<div id="pt" class="picker-overlay tx-starting" inert></div>'), cls: "tx-starting" },
];
// After the viewer's passes each element holds no class the sheets let a press pass through (dropPressThrough) or raise to the control's
// stacking level (dropStackClasses), no inert attribute and no pointer-events declaration, so it stands in the flow off the control and
// the picture opens with the control shown. The overlay scenes carry the page class picker-overlay, which the sheets both position fixed
// and give a z-index above the control's, so dropStackClasses takes it off and the overlay falls into the flow: those scenes open once
// here where before this pass they opened nothing, which narrows the cost the file review's round 16 disclosed and does not close it
// (the block above says what stays). The toast's page class the sheets let a press pass through, so dropPressThrough already took it off.
for (const surface of ["chat", "pane"] as Surface[]) for (const device of ["fine", "touch"] as GateDevice[]) for (const pt of PRESS_THROUGH) {
  test("in a browser " + gateOn(device, surface).replace("a fine click", "a fine pointer") + ", the one gate's covered sign, an author's element a press would pass through or a page class would raise, " + pt.what + " (the file review's round 16, extra5-1, the covered sign): after the viewer's passes the element holds no class the sheets let a press pass through or raise to the control's stacking level, no inert attribute and no pointer-events declaration, so it stands in the flow off the control and a gesture on the picture and Enter on the control each open once with the control shown (" + (pt.scene === "toast" ? "red at the head the file review's round 16 read, which had no gate, where the element covered the control as a gesture opened" : "red before this pass took the raising page class off, where the overlay stood fixed over the control and no gesture opened, and at the head the file review's round 16 read, which had no gate") + ")", { timeout: 180000 }, async (t) => {
    const rec: Record<string, unknown> = { scene: "press-through " + pt.scene };
    await gateCase(t, device, surface, pt.text, rec, async (g) => {
      const st = await g.page.evaluate(() => {
        const w = window as any, o = document.getElementById("user-content-pt"), c = w.__ctl("ov") as HTMLElement, cr = c.getBoundingClientRect();
        const orr = o ? o.getBoundingClientRect() : null, cs = o ? getComputedStyle(o) : null;
        const e = document.elementFromPoint((cr.left + cr.right) / 2, (cr.top + cr.bottom) / 2);
        return { found: !!o, classes: o ? o.getAttribute("class") : null, inert: o ? o.hasAttribute("inert") : null, style: o ? o.getAttribute("style") : null, position: cs && cs.position, pe: cs && cs.pointerEvents,
          over: !!orr && cs!.position === "fixed" && orr.left <= cr.left && orr.right >= cr.right && orr.top <= cr.top && orr.bottom >= cr.bottom,
          hit: !e ? "null" : e === c || c.contains(e) ? "the control" : o && (e === o || o.contains(e)) ? "the element" : e.localName };
      });
      rec.state = st;
      assert.ok(st.found, "the author's element painted (the case's premise): " + JSON.stringify(st));
      g.cell("the element after the paint: [its classes, inert, its style attribute, its computed pointer-events, over the control, what a press at the control's centre reaches]", [pt.cls, false, null, "auto", false, "the control"], [st.classes, st.inert, st.style, st.pe, st.over, st.hit]);
      const r = await g.read("ov");
      rec.read = r;
      await g.gesture(device, r.pt.x, r.pt.y);
      g.cell("a gesture at the picture's point (" + r.hit + "): its opens", [1, 1], opensOf(await g.opens()));
      await g.page.evaluate(() => { (document.querySelector(".fileview-body") as HTMLElement).focus(); });
      let tabs = 0;
      for (; tabs < 20; tabs++) { if (await g.page.evaluate(() => document.activeElement === (window as any).__ctl("ov"))) break; await g.page.keyboard.press("Tab"); await frames(g.page, 1); }
      rec.tabs = tabs;
      assert.ok(await g.page.evaluate(() => document.activeElement === (window as any).__ctl("ov")), "the keyboard on the control (a precondition)");
      await g.page.keyboard.press("Enter");
      g.cell("Enter on the control: its opens", [1, 1], opensOf(await g.opens()));
    });
  });
}
// ── the classes that would raise author content to the control's stacking level, off the markup (the file review's round 16, extra5-1,
// the covered sign) ── The control rests positioned at z-index 1, and that z-index, not its place in the document, keeps it above author
// content the sheets leave at z-index auto where no stacking context stands around the picture (the stacking cells below read that part).
// An author's element of a page class that gives it a z-index at or above the control's is left at or above the control; file-view.ts
// dropStackClasses takes every such class off a file document's author markup before any pass of the viewer's own, so none is. Four scenes, each an author's svg of a stacking page class (ctx-text: position relative,
// z-index 1, later in document order) after a loaded remote picture, the four svg shapes differing only in their own markup. After the
// viewer's passes the element holds no class the sheets would raise and rests at z-index auto, so it is below the control; the gesture on
// the picture and Enter on the control open with the control shown, and a tap does too. Whether a shape's own content stands above the
// control before the drop is the private witness, kept out of the tree; the pins here read the element's class and computed z-index after
// the viewer's passes, and the opens on the fine click, Enter and the tap.
const STACK_SHAPES: Array<{ scene: string; svg: string }> = [
  { scene: "shape 1", svg: '<svg id="probe" width="60" height="60" filter="drop-shadow(0px 0px 0 red)"><rect width="60" height="60" fill="red"/></svg>' },
  { scene: "shape 2", svg: '<svg id="probe" width="60" height="60" overflow="visible"><rect width="60" height="60" fill="red" filter="drop-shadow(0px 0px 0 red)"/></svg>' },
  { scene: "shape 3", svg: '<svg id="probe" width="60" height="60" overflow="visible"><defs><marker id="mk" markerUnits="userSpaceOnUse" markerWidth="100" markerHeight="100" overflow="visible"><rect x="-30" y="-30" width="60" height="60" fill="red"/></marker></defs><path d="M30 30 l0.01 0" stroke="red" stroke-width="0.1" fill="none" marker-end="url(#user-content-mk)"/></svg>' },
  { scene: "shape 4", svg: '<svg id="probe" width="60" height="60" overflow="visible"><text x="30" y="30" font-size="2" fill="red" stroke="red" stroke-width="90" stroke-linejoin="round">x</text></svg>' },
];
const STACK_TEXT = (svg: string): string => "# Report\n\n" + PARA(1) + "\n\n![ov](" + WEB + "/ov.svg)\n\n" + '<span id="pt" class="ctx-text keep">' + svg + "</span>" + "\n\n" + Array.from({ length: 12 }, (_, i) => PARA(i + 3)).join("\n\n") + "\n";
for (const surface of ["chat", "pane"] as Surface[]) for (const device of ["fine", "touch"] as GateDevice[]) for (const sh of STACK_SHAPES) {
  test("in a browser " + gateOn(device, surface).replace("a fine click", "a fine pointer") + ", the one gate's covered sign, an author's svg of a stacking page class over a picture, " + sh.scene + " (the file review's round 16, extra5-1, the covered sign): after the viewer's passes the author's svg of ctx-text (position relative, z-index 1) holds no raising class and rests at z-index auto, so it is below the control, and a gesture on the picture" + (device === "fine" ? " and Enter on the control each" : "") + " open with the control shown (red at the head the file review's round 16 read, where the class stood and the svg rested at the control's z-index while the gesture opened)", { timeout: 180000 }, async (t) => {
    const rec: Record<string, unknown> = { scene: "stack " + sh.scene };
    await gateCase(t, device, surface, STACK_TEXT(sh.svg), rec, async (g) => {
      const st = await g.page.evaluate(() => { const o = document.getElementById("user-content-pt"); const pr = document.getElementById("user-content-probe"); return { found: !!o && !!pr, classes: o ? o.getAttribute("class") : null, z: o ? getComputedStyle(o).zIndex : null }; });
      rec.state = st;
      assert.ok(st.found, "the author's element and its svg painted (the case's premise): " + JSON.stringify(st));
      g.cell("the author's element after the paint: [its classes, its computed z-index]", ["keep", "auto"], [st.classes, st.z]);
      const r = await g.read("ov");
      rec.read = r;
      await g.gesture(device, r.pt.x, r.pt.y);
      g.cell("a gesture at the picture's point (" + r.hit + "): its opens", [1, 1], opensOf(await g.opens()));
      if (device === "fine") {
        await g.page.evaluate(() => { (document.querySelector(".fileview-body") as HTMLElement).focus(); });
        let tabs = 0;
        for (; tabs < 20; tabs++) { if (await g.page.evaluate(() => document.activeElement === (window as any).__ctl("ov"))) break; await g.page.keyboard.press("Tab"); await frames(g.page, 1); }
        rec.tabs = tabs;
        assert.ok(await g.page.evaluate(() => document.activeElement === (window as any).__ctl("ov")), "the keyboard on the control (a precondition)");
        await g.page.keyboard.press("Enter");
        g.cell("Enter on the control: its opens", [1, 1], opensOf(await g.opens()));
      }
    });
  });
}
// ── the one gate's stacking cells in Chromium (the file review's round 17, extra9-1, and the coordinator's decision 4 on it) ──
// file-figure-open-stacking.ts holds the cells and says what each reads; file-figure-open-engines-browser.test.ts runs the same set in
// WebKit and Firefox. The picture's control keeps its z-index 1 over author content at z-index auto or 0 only where no stacking context
// stands around the picture: the top-level table's shift is a position and a left, and dropStackClasses takes SHEET_CONTEXT_CLASSES off
// each figure and every element above it.
for (const surface of ["chat", "pane"] as StackSurface[]) {
  test("in Chromium on a page with a touchscreen beside the mouse, the " + (surface === "chat" ? "chat modal" : "Files pane") + ": the one gate's stacking cells (the file review's round 17, extra9-1, and the coordinator's decision 4 on it): a remote picture in a top-level table, the table positioned with no translate, then a positioned author element: the control takes the press at its centre, and a click, a tap, Enter and Space on it each open once; the same with the picture inside an author's div of romp-lightbox-img, and inside a span of path-full-wait inside a div of rail-hit, each element holding neither class after the paint; the table, then an svg's shadow placed over the control, and the same with the picture inside a div of meta-held-mark: no red pixel inside the control's box, and a click and Enter open once; the picture inside a div of ask-btn, then the shadow: no red pixel inside the control's box with the mouse held on it, and the release opens once (each scene red at 0ab74924c)", { timeout: 300000 }, async (t) => {
    let cells: Array<[string, unknown, unknown]> = [];
    let ran = false;
    await inBrowser(t, async (browser) => {
      ran = true;
      cells = await stackCells(browser, "chromium", surface, (m) => t.diagnostic(m));
    });
    if (!ran) return;   // no browser: inBrowser skipped the case loudly
    for (const [what, , got] of cells) t.diagnostic("cell " + what + ": " + JSON.stringify(got));
    assert.ok(cells.length > 0, "the case ran its cells");
    assert.deepEqual(cells.map(([what, , got]) => [what, got]), cells.map(([what, want]) => [what, want]), "each cell's reading, [cell, reading] (property pins read off the page)");
  });
}
for (const surface of ["chat", "pane"] as Surface[]) {
  test("in a browser " + gateOn("fine", surface).replace("a fine click", "a fine pointer") + ", the one gate's guard on the middle button (the rulings' fact 1): a middle click on the picture with its control out of view, on the control in view and on the picture in view opens nothing, and each fires its auxclick (no open at the head the file review's round 16 read either: the figures' listener hears click alone, and the auxclick listener reads path and section links alone)", { timeout: 180000 }, async (t) => {
    const rec: Record<string, unknown> = { scene: "middle" };
    await gateCase(t, "fine", surface, GATE_TEXT, rec, async (g) => {
      const out = await g.place("tall", -60);
      assert.ok(out.outside && out.hit === "the picture", "the control out of view, the point on the picture (a precondition): " + JSON.stringify(out));
      await g.gesture("middle", out.pt.x, out.pt.y);
      g.cell("the middle click on the picture, its control out of view: [opens, auxclicks]", [[0, 0], 1], [opensOf(await g.opens()), (await g.clicks()).filter((c) => c.target === "auxclick").length]);
      const mid = await g.place("tall", 200);
      await g.page.mouse.move(mid.pt2.x, mid.pt2.y);
      await frames(g.page, 3);
      const c = await g.page.evaluate(() => { const r = (window as any).__ctl("tall").getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; });
      await g.gesture("middle", c.x, c.y);
      g.cell("the middle click on the control in view", [[0, 0], 1], [opensOf(await g.opens()), (await g.clicks()).filter((x) => x.target === "auxclick").length]);
      await g.gesture("middle", mid.pt2.x, mid.pt2.y);
      g.cell("the middle click on the picture in view", [[0, 0], 1], [opensOf(await g.opens()), (await g.clicks()).filter((x) => x.target === "auxclick").length]);
    });
  });
  test("in a browser (CDP touch emulation, " + (surface === "chat" ? "the chat modal" : "the Files pane") + "), the one gate on the mark: a remote picture under the floor wearing the outbound mark, scrolled wholly out of the body, and a click dispatched on it (detail 0, which no pointer can deliver there): no open, the picture in view after, and a second dispatched click opens once (red at the head the file review's round 16 read by one open on the first); keep: a tap on the mark in view opens once (green there by design)", { timeout: 180000 }, async (t) => {
    const rec: Record<string, unknown> = { scene: "mark" };
    await gateCase(t, "touch", surface, GATE_TEXT, rec, async (g) => {
      const out = await g.place("tiny", -100);
      const m = await g.page.evaluate(() => { const i = (window as any).__img("tiny"); return { mark: i.hasAttribute("data-fv-figweb"), control: !!(window as any).__ctl("tiny") }; });
      rec.out = { ...m, read: out };
      assert.ok(m.mark && !m.control && out.outside, "the picture wears the mark and no control, and lies wholly outside the body (a precondition): " + JSON.stringify(rec.out));
      const dispatch = (): Promise<void> => g.page.evaluate(() => { (window as any).__img("tiny").dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true })); });
      await g.page.evaluate(() => { (window as any).__gclicks.length = 0; });
      await dispatch();
      g.cell("the first dispatched click's opens", [0, 0], opensOf(await g.opens()));
      g.cell("after it: the picture in view", true, (await g.read("tiny")).inView);
      await dispatch();
      g.cell("the second dispatched click's opens", [1, 1], opensOf(await g.opens()));
      const mid = await g.place("tiny", 200);
      const c = { x: (mid.sign[0] + mid.sign[2]) / 2, y: (mid.sign[1] + mid.sign[3]) / 2 };
      await g.gesture("touch", Math.round(c.x), Math.round(c.y));
      g.cell("keep: a tap on the mark in view, opens", [1, 1], opensOf(await g.opens()));
    });
  });
  test("in a browser " + gateOn("fine", surface) + ", the one gate's anchors: a remote picture inside a <picture> and one inside a dead link, each with its control out of view: the first click opens nothing and leaves the control in view, and a second opens once; in view each opens once (the file review's round 16, extra5-1, the first refuter's refinement 2: red at the head the file review's round 16 read by one open on each first click; the reveal, the second open and the keep cells red under a gate that looks for the control after the img instead of after its anchor)", { timeout: 180000 }, async (t) => {
    const rec: Record<string, unknown> = { scene: "anchors" };
    await gateCase(t, "fine", surface, GATE_TEXT, rec, async (g) => {
      for (const alt of ["pp", "dl"]) {
        const kind = alt === "pp" ? "the <picture>" : "the dead link";
        const shape = await g.page.evaluate((a: string) => { const i = (window as any).__img(a); return { parent: i.parentElement.localName, dead: i.parentElement.classList.contains("fv-dead"), control: !!(window as any).__ctl(a) }; }, alt);
        assert.ok(shape.control && (alt === "pp" ? shape.parent === "picture" : shape.parent === "a" && shape.dead), kind + ": the picture inside it, its control after the anchor (a precondition): " + JSON.stringify(shape));
        const out = await g.place(alt, -60);
        assert.ok(out.outside && out.hit === "the picture", kind + ": the control out of view, the point on the picture (a precondition): " + JSON.stringify(out));
        await g.gesture("fine", out.pt.x, out.pt.y);
        g.cell(kind + ": the first click's opens", [0, 0], opensOf(await g.opens()));
        const after = await g.read(alt);
        g.cell(kind + ": after it, the control in view", true, after.inView);
        await g.gesture("fine", after.pt2.x, after.pt2.y);
        g.cell(kind + ": the second click's opens", [1, 1], opensOf(await g.opens()));
        const mid = await g.place(alt, 200);
        await g.gesture("fine", mid.pt2.x, mid.pt2.y);
        g.cell(kind + ": keep, the control centred, the click's opens", [1, 1], opensOf(await g.opens()));
      }
    });
  });
  test("in a browser (CDP touch emulation, " + (surface === "chat" ? "the chat modal" : "the Files pane") + "), the one gate and the row: the Comments panel open on a coarse pointer (the layer's overlay off), a Ctrl-click on the remote picture with its control out of view opens nothing and stops before the row, whose listener would offer a comment (the row cell green at the head the file review's round 16 read, which stopped the modified click before its open, and the opens cell red there by group A's open, since that head had no gate; red under a gate placed before openFigure's stopPropagation, where the refused click reached the row)", { timeout: 180000 }, async (t) => {
    const rec: Record<string, unknown> = { scene: "row" };
    await gateCase(t, "touch", surface, GATE_TEXT, rec, async (g) => {
      assert.equal(await g.page.evaluate(() => matchMedia("(pointer: coarse)").matches), true, "a coarse pointer under the emulation (a precondition)");
      await openPanel(g.page);
      await g.page.waitForFunction(() => { const o = document.querySelectorAll(".fileview-md .fc-overlay"); return o.length > 0 && Array.from(o).every((x) => x.classList.contains("fc-overlay-off")); }, null, { timeout: 5000 });
      await g.page.evaluate(GATE_INSTALL);
      const out = await g.place("tall", -60);
      assert.ok(out.outside && out.hit === "the picture", "the control out of view, the point on the picture under the open panel (a precondition): " + JSON.stringify(out));
      const floatShown = (): Promise<boolean> => g.page.evaluate(() => { const f = document.querySelector(".fc-float") as HTMLElement | null; return !!f && !f.hidden && f.getBoundingClientRect().width > 0; });
      await g.gesture("ctrl", out.pt.x, out.pt.y);
      g.cell("the refused Ctrl-click's opens", [0, 0], opensOf(await g.opens()));
      g.cell("no comment offer: the click stopped before the row", false, await floatShown());
    });
  });
  test("in a browser " + gateOn("fine", surface).replace("a fine click", "a fine pointer") + ", the one gate leaves a local picture alone: its control out of view, a Ctrl-click opens the kernel's /file URL in a tab and a plain click opens the picture in the viewer (green at the head the file review's round 16 read by design; red under a gate that reads no target kind, which refused both)", { timeout: 180000 }, async (t) => {
    const rec: Record<string, unknown> = { scene: "local" };
    await gateCase(t, "fine", surface, GATE_TEXT, rec, async (g) => {
      const out = await g.place("localtall", -60);
      assert.ok(out.outside && out.hit === "the picture", "the local picture's control out of view, the point on the picture (a precondition): " + JSON.stringify(out));
      await g.gesture("ctrl", out.pt.x, out.pt.y);
      const tab = await g.opens();
      rec.tab = tab;
      g.cell("the Ctrl-click: one tab, at the /file URL", [1, true], [tab.popups, tab.fileTabs.length === 1 && tab.fileTabs[0].includes("/file?path=" + encodeURIComponent(GATE_LOCAL))]);
      const again = await g.read("localtall");
      await g.gesture("fine", again.pt.x, again.pt.y);
      const shown = await g.page.locator(".fileview-base", { hasText: "gate-tall.svg" }).waitFor({ timeout: 10000 }).then(() => true, () => false);
      g.cell("the plain click: the picture in the viewer", true, shown);
    });
  });
}
for (const [host, mode] of [["top", "chat"], ["same", "pane"], ["same", "chat"]] as Array<["top" | "same", "chat" | "pane"]>) {
  const limit = host === "same" && mode === "chat";   // the chat modal framed: the stated limit, where the reveal cannot pan the top's visual viewport
  const where = host === "top" ? onHost("top") : mode === "pane" ? "the Files pane's page in a same-origin iframe of the top page, the dashboard's shape" : "the chat page's modal viewer in a same-origin iframe of the top page, the dashboard's chat column";
  test("in a browser (a fine pointer), the one gate under a pinch zoom, " + where + ": the top page zoomed to 3 with the big picture's web control outside the top's visual viewport and a click on the picture inside it: no open, " + (limit ? "and, the stated limit of a reveal that cannot bring the sign into view (the viewer's card is fixed in its frame, and Chromium's scrollIntoView from it pans no visual viewport of the top page), the control still off the visual viewport after and a second click opening nothing too, the gate failing closed until the reader pans the page by hand" : "the control inside the visual viewport after, and a second click opens once") + " (the file review's round 16, extra5-1: red at the head the file review's round 16 read by one open on the first click)", { timeout: 120000 }, async (t) => {
    const rec: Record<string, unknown> = { pin: "gate-zoom-" + host + "-" + mode };
    await hostCase(t, host, rec, async (page, at) => {
      await at.evaluate(() => { const b = document.querySelector(".fileview-body") as HTMLElement; b.scrollTop += (window as any).__img("big").getBoundingClientRect().top - 90; });   // the picture's top at 90, so its lower part lies inside the zoomed visual viewport (0 to 200 down) while its control's corner lies right of it
      await frames(at, 3);
      const z = await zoomTo(page, at, 3);
      rec.zoom = z;
      assert.ok(z.scale > 1 && z.inLayout && !z.onScreen, "the top's page scale above 1, the control inside its own layout viewport and off the top's visual viewport (a precondition): " + JSON.stringify(z));
      /** A point on the big picture inside the top's visual viewport, in the viewer's layout coordinates and in the top's visual viewport's (the mouse's), and what it hit-tests to. */
      const pointIn = async (): Promise<{ x: number; y: number; mx: number; my: number; hit: string }> => {
        const top = await page.evaluate(() => { const v = window.visualViewport!, f = document.querySelector("iframe"), b = f ? f.getBoundingClientRect() : null; return { vv: [v.offsetLeft, v.offsetTop, v.width, v.height], at: b ? [b.left + f!.clientLeft, b.top + f!.clientTop] : [0, 0] }; });
        const ir = await at.evaluate(() => { const r = (window as any).__img("big").getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom]; });
        const [vx, vy, vw, vh] = top.vv, [ox, oy] = top.at;
        const x = Math.max(ir[0], vx - ox) + 30, y = Math.min(ir[3], vy - oy + vh) - 30;
        const hit = await at.evaluate(([px, py]: [number, number]) => { const e = document.elementFromPoint(px, py); return e === (window as any).__img("big") ? "the picture" : e ? e.localName : "null"; }, [x, y]);
        return { x, y, mx: x + ox - vx, my: y + oy - vy, hit };
      };
      const p1 = await pointIn();
      rec.p1 = p1;
      assert.ok(p1.hit === "the picture" && p1.mx >= 0 && p1.mx <= z.vv[2] && p1.my >= 0 && p1.my <= z.vv[3], "the click's point on the picture, inside the top's visual viewport (a precondition): " + JSON.stringify(p1));
      await page.mouse.click(p1.mx, p1.my);
      await frames(at, 4);
      const a = await focusState(at, "big");
      const z2 = await zoomTo(page, at, 1);   // a read at the scale set above: at 1 no scale is sent
      rec.after = { a, z2 };
      assert.equal(a.opened, 0, "the first click on the picture, its control off the zoomed screen, opens nothing (a property pin read off the page)");
      assert.equal(z2.onScreen, !limit, limit ? "the control still off the top's visual viewport after the refused click: the reveal from the framed modal pans nothing (the stated limit's witness, read off the page)" : "the control inside the top's visual viewport after the refused click: the reveal panned it there (a property pin read off the page)");
      const p2 = await pointIn();
      rec.p2 = p2;
      assert.ok(p2.hit === "the picture", "the second click's point on the picture inside the visual viewport (a precondition): " + JSON.stringify(p2));
      await page.mouse.click(p2.mx, p2.my);
      await frames(at, 4);
      assert.equal((await focusState(at, "big")).opened, limit ? 0 : 1, limit ? "the second click opens nothing either: the gate fails closed while the reveal cannot bring the control on the screen (the stated limit's witness)" : "the second click opens once (a property pin read off the page)");
    }, mode);
  });
}

// ── the predicate's accuracy (the file review's round 16, regression-1 with the coordinator's decision 1, and fresh-1) ──────────────
// The one gate and the key gate read one predicate (controlInView), so a misread refuses an honest gesture or opens from a hidden
// control. Two corrections, each read in cases of their own; "the round-16 head" below is the head the file review's round 16 read,
// where every red named here was executed.
// - An ancestor on which overflow clips nothing, display: contents or a display overflow does not apply to (inline, ruby, ruby-text,
//   a table's row or column and their groups), is passed over whatever its overflow reads.
//   (a) The dashboard's narrow and touch layout in the real shape: the viewer's page (the chat page's modal, the Files pane) in a
//   same-origin iframe inside the kernel's pane wrapper, div.pane under the kernel's own rules, which compute overflow hidden and,
//   under the narrow layout's query, display: contents (paneCss lifts both rules and the query from kernel/kernel.py at run time),
//   at 800px on a fine pointer and at 1024px with touch: Tab to the big picture's web control, on the screen, then Enter, Space, a
//   click (a tap with touch) on the control and one on the picture each open once. Enter and Space are red at the round-16 head,
//   where the wrapper's 0 by 0 put every control of the frame out of view (0 opens), and green at 2e9205301 by design, whose region
//   walked no frame; the clicks are green at the round-16 head, which had no gate, and red under the one gate without the skip,
//   which refuses them too (the composition). At 1400px, the desktop layout, the wrapper is a box that clips nothing of the frame
//   and every gesture opens once at both heads (the control cell).
//   (b) An author's element around the picture, on the chat modal and the Files pane: a span of a page class that sets overflow
//   hidden (sub-head-waits: display inline, a client size of 0 by 0), and a span of that class and one that sets display: contents
//   (followup-wrap), each holding a remote picture whose control is on the screen: Enter, Space, a click on the picture and one on
//   the control each open once; the keys red at the round-16 head (0 opens, the span read as a clip), every cell red under the one
//   gate without the skip. Beside them, an author's ruby of that class, a ruby text (rt) of it and a table row of it holding a cell
//   that spans the row below, whose content stands past the row's own height: the same four cells open once each; red on every
//   gesture under a skip of contents and inline alone, which read each of the three as a clip, and the keys red at the round-16
//   head.
// - Every read is in one coordinate space under a body zoom in the VS Code extension's zoomStyle shape (`body{zoom:1.2500;}`), on a
//   harness page without the webviews' policy (in VS Code no figure with a target stands under a zoom, as controlInView's docstring
//   says; these cells hold the predicate's geometry). At 1.25 on both surfaces a control wholly visible in the body's bottom band
//   and the control of a picture as wide as the Rendered column at the body's right edge, each outside what the body's unscaled
//   client size spans, reached by Tab: Enter, Space and a click on the picture each open once (the keys red at the round-16 head,
//   0 opens), and the band once more with the viewer's own text size at 150%, which scales the text and not the coordinate space.
//   At 0.8 a control past the body's bottom edge by less than the gap to the window's bottom (the chat modal; the Files pane's body
//   reaches the window's bottom), and on both surfaces a control past the right edge of a table that scrolls on its own, inside the
//   body and the window (the body itself never scrolls across: the Rendered box's layout containment keeps its overflow out of the
//   body's scroll width, measured, so no control stands past the body's right edge inside the window), each clipped, the element at
//   it not the control (asserted): Enter, Space and a click dispatched on the control open nothing (the keys red at the round-16
//   head by one open each, the direction that opens a tab with the control hidden; the click by group A's open). Beside them a
//   control above the body's top under the same zoom: Enter and Space open nothing at both heads by design, and a dispatched click
//   opens nothing (red at the round-16 head by group A's open). The floor in CSS pixels at 1.25 and 0.8 on both surfaces and at
//   14/13 (VS Code's zoom for its default editor font of 14px) on the chat modal: pictures laid out at 40, 48 and 50 CSS px get the
//   control verdict they get at zoom 1, none for the 40, which wears the mark, and a control for the 48 and the 50 (red at the
//   round-16 head at 1.25 by the 40's control, and at 0.8 by the missing controls of the 48 and the 50, each wearing the mark in
//   their place), and a picture laid out at 47.6 CSS px gets none at every zoom (red at the round-16 head at 1.25 and at 14/13, and
//   at every zoom under a floor read from offsetWidth, which rounds it to 48); the 48 is red at 0.8 and at 14/13 under a floor that
//   divides by the zoom without rounding, where the layout's grid put it at 47.988 and 47.9965 CSS px. And the zoom-1 twin of each
//   cell: its key cells green at both heads by design, its dispatched clicks on a control out of view red at the round-16 head by
//   group A's open.
// Each case collects its cells and asserts them once; property pins read off the page. file-view-outline.test.ts runs the skip and
// the scaled reads in CI over the stand-in.
const PANE_SHAPES: Array<[string, PaneShape, boolean]> = [
  ["800px on a fine pointer", { width: 800, height: 600, touch: false }, true],
  ["1024px with touch", { width: 1024, height: 600, touch: true }, true],
  ["1400px on a fine pointer, the desktop layout (the control cell)", { width: 1400, height: 600, touch: false }, false],
];
for (const [label, shape, narrow] of PANE_SHAPES) for (const mode of ["chat", "pane"] as const) {
  test("in a browser, the predicate's accuracy, the dashboard's " + (narrow ? "narrow and touch layout" : "desktop layout") + " at " + label + ": " + (mode === "chat" ? "the chat page's modal viewer" : "the Files pane's page") + " in a same-origin iframe inside the kernel's pane wrapper (div.pane under the kernel's own rules, lifted from kernel/kernel.py at run time, which compute " + (narrow ? "display: contents" : "a box") + " with overflow hidden here): Tab to the big picture's web control, on the screen, then Enter, Space, a " + (shape.touch ? "tap" : "click") + " on the control and one on the picture each open once (the file review's round 16, regression-1 with the coordinator's decision 1: " + (narrow ? "the keys red at the head the file review's round 16 read, where the wrapper's 0 by 0 put the control out of view, and green at 2e9205301 by design, which walked no frame; the " + (shape.touch ? "taps" : "clicks") + " green at the head the file review's round 16 read, which had no gate, and red under the one gate without the skip" : "every cell green at both heads by design, the wrapper a box that clips nothing of the frame") + ")", { timeout: 180000 }, async (t) => {
    const rec: Record<string, unknown> = { pin: "pane", width: shape.width, touch: shape.touch, mode };
    const cells: Array<[string, unknown, unknown]> = [];
    let ran = false;
    const second = await secondServer([]);
    try {
      await inBrowser(t, async (browser) => {
        ran = true;
        const o = await openFramed(browser, second.port, ORIGIN, mode, shape);
        const { page, at } = o;
        try {
          const k = paneCss();
          const wrap = await page.evaluate((mq: string) => { const p = document.querySelector(".pane") as HTMLElement, cs = getComputedStyle(p), r = p.getBoundingClientRect(); return { display: cs.display, overflow: cs.overflowX, box: [r.width, r.height], client: [p.clientWidth, p.clientHeight], narrowQuery: matchMedia(mq).matches, coarse: matchMedia("(pointer: coarse)").matches }; }, k.mq);
          rec.wrap = wrap;
          assert.deepEqual([wrap.display, wrap.overflow, wrap.narrowQuery, wrap.coarse], [narrow ? "contents" : "block", "hidden", narrow, shape.touch], "the pane wrapper as the kernel's rules compute it at this size, and the pointer (a precondition): " + JSON.stringify(wrap));
          await tabToBig(page, at, rec);
          const z = await zoomTo(page, at, 1);
          const hit = await at.evaluate(() => { const c = (window as any).__ctl("big") as HTMLElement, r = c.getBoundingClientRect(), e = document.elementFromPoint((r.left + r.right) / 2, (r.top + r.bottom) / 2); return !!e && c.contains(e); });
          rec.zoom = z;
          assert.ok(z.inLayout && z.onScreen && z.active && hit, "the web control holding the keyboard, on the screen and uncovered (a precondition): " + JSON.stringify({ z, hit }));
          const opened = async (): Promise<number> => (await focusState(at, "big")).opened;
          const count = async (what: string, act: () => Promise<void>): Promise<void> => { const n = await opened(); await act(); await frames(at, 4); cells.push([what, 1, (await opened()) - n]); };
          await count("Enter's opens", () => page.keyboard.press("Enter"));
          assert.equal((await focusState(at, "big")).active, "control", "the keyboard still on the control (a precondition)");
          await count("Space's opens", () => page.keyboard.press("Space"));
          const pts = await at.evaluate(() => { const c = (window as any).__ctl("big").getBoundingClientRect(), i = (window as any).__img("big").getBoundingClientRect(); return { ctl: { x: c.left + c.width / 2, y: c.top + c.height / 2 }, pic: { x: i.left + 40, y: i.bottom - 30 }, picCentre: { x: i.left + i.width / 2, y: i.top + i.height / 2 } }; });
          rec.pts = pts;
          await count("a " + (shape.touch ? "tap" : "click") + " on the control, its opens", async () => { if (shape.touch) await page.touchscreen.tap(pts.ctl.x, pts.ctl.y); else { await page.mouse.move(pts.picCentre.x, pts.picCentre.y); await frames(at, 3); await page.mouse.click(pts.ctl.x, pts.ctl.y); } });
          await count("a " + (shape.touch ? "tap" : "click") + " on the picture, its opens", async () => { if (shape.touch) await page.touchscreen.tap(pts.pic.x, pts.pic.y); else await page.mouse.click(pts.pic.x, pts.pic.y); });
          assert.deepEqual(o.errors, [], "no page errors");
        } finally {
          rec.cells = cells.map(([what, want, got]) => ({ what, want, got }));
          t.diagnostic("record " + JSON.stringify(rec));
          await page.close();
        }
      });
    } finally { await second.close(); }
    if (!ran) return;
    assert.ok(cells.length === 4, "the case ran its four cells");
    assert.deepEqual(cells.map(([what, , got]) => [what, got]), cells.map(([what, want]) => [what, want]), "each gesture's opens on the control on the screen, [cell, opens] (property pins read off the page)");
  });
}
const WRAP_TEXT = "# Report\n\n" + PARA(1) + "\n\n" + 'Gist words <span class="sub-head-waits"><img src="' + WEB + '/gi.svg" alt="gi"></span> after.' + "\n\n" + Array.from({ length: 8 }, (_, i) => PARA(i + 2)).join("\n\n")
  + "\n\n" + 'Wrap words <span class="followup-wrap sub-head-waits"><img src="' + WEB + '/gc.svg" alt="gc"></span> after.' + "\n\n" + Array.from({ length: 12 }, (_, i) => PARA(i + 10)).join("\n\n") + "\n";
/** The displays overflow does not apply to beyond inline, each an author's element of the same page class around a remote picture:
 *  a ruby, a ruby text, and a table row holding a cell that spans the row below, whose picture stands past the row's own height. */
const WRAP_MORE_TEXT = "# Report\n\n" + PARA(1) + "\n\n" + 'Ruby words <ruby class="sub-head-waits"><img src="' + WEB + '/gr.svg" alt="gr"><rt>r</rt></ruby> after.' + "\n\n" + Array.from({ length: 8 }, (_, i) => PARA(i + 2)).join("\n\n")
  + "\n\n" + 'Ruby text words <ruby>base<rt class="sub-head-waits"><img src="' + WEB + '/gt.svg" alt="gt"></rt></ruby> after.' + "\n\n" + Array.from({ length: 8 }, (_, i) => PARA(i + 10)).join("\n\n")
  + "\n\n" + '<table><tr class="sub-head-waits"><td rowspan="2"><img src="' + WEB + '/gw.svg" alt="gw"></td><td>x</td></tr><tr><td>' + Array.from({ length: 14 }, (_, i) => "line " + i).join("<br>") + "</td></tr></table>"
  + "\n\n" + Array.from({ length: 12 }, (_, i) => PARA(i + 18)).join("\n\n") + "\n";
/** The keyboard on the control of `alt` with the control where `place` puts it: Tab to it from the report's first paragraph if the
 *  keyboard is elsewhere (an open's popup can take the page's focus), then `place`; returns the read after it. */
async function keyOnControl(g: GateScene, alt: string, place: () => Promise<GateRead>): Promise<GateRead> {
  if ((await g.read(alt)).active !== "the sign") await gateTab(g, alt);
  const r = await place();
  if (r.active === "the sign") return r;
  await gateTab(g, alt);
  return place();
}
for (const surface of ["chat", "pane"] as Surface[]) {
  test("in a browser " + gateOn("fine", surface).replace("a fine click", "a fine pointer") + ", the predicate's accuracy, an author's element around the picture on which overflow clips nothing: a remote picture inside a span of a page class that sets overflow hidden (sub-head-waits, display inline, a client size of 0 by 0), and one inside a span of that class and one that sets display: contents (followup-wrap), each control on the screen and uncovered: Enter, Space, a click on the picture and one on the control each open once (the file review's round 16, regression-1 with the coordinator's decision 1: the keys red at the head the file review's round 16 read, where the span read as a clip put the control out of view, 0 opens; every cell red under the one gate without the skip, the clicks refused too)", { timeout: 180000 }, async (t) => {
    const rec: Record<string, unknown> = { scene: "author wrapper" };
    await gateCase(t, "fine", surface, WRAP_TEXT, rec, async (g) => {
      for (const [alt, display] of [["gi", "inline"], ["gc", "contents"]] as const) {
        const st = await g.page.evaluate((a: string) => { const w = window as any, img = w.__img(a), s = img.parentElement as HTMLElement, cs = getComputedStyle(s), r = s.getBoundingClientRect(); return { cls: s.getAttribute("class"), display: cs.display, overflow: cs.overflowX, client: [s.clientWidth, s.clientHeight], box: [Math.round(r.width), Math.round(r.height)], control: !!w.__ctl(a) }; }, alt);
        rec[alt] = st;
        assert.ok(st.display === display && st.overflow === "hidden" && st.client[0] === 0 && st.client[1] === 0 && st.control, alt + ": the author's span computes display " + display + ", overflow hidden and a client size of 0 by 0, and the picture wears its control (a precondition): " + JSON.stringify(st));
        const mid = await keyOnControl(g, alt, () => g.place(alt, 200));
        rec[alt + "Mid"] = mid;
        assert.ok(mid.inView && mid.signHit && mid.active === "the sign", alt + ": the control holding the keyboard, in view and uncovered (a precondition): " + JSON.stringify(mid));
        await g.page.keyboard.press("Enter");
        g.cell(alt + " (display " + display + "): Enter's opens", [1, 1], opensOf(await g.opens()));
        await keyOnControl(g, alt, () => g.place(alt, 200));
        await g.page.keyboard.press("Space");
        g.cell(alt + " (display " + display + "): Space's opens", [1, 1], opensOf(await g.opens()));
        const r = await g.place(alt, 200);
        assert.equal(r.hit2, "the picture", alt + ": the click's point on the picture (a precondition): " + JSON.stringify(r));
        await g.gesture("fine", r.pt2.x, r.pt2.y);
        g.cell(alt + " (display " + display + "): a click on the picture, its opens", [1, 1], opensOf(await g.opens()));
        const c = await g.place(alt, 200);
        await g.gesture("fine", Math.round((c.sign[0] + c.sign[2]) / 2), Math.round((c.sign[1] + c.sign[3]) / 2));
        g.cell(alt + " (display " + display + "): a click on the control, its opens", [1, 1], opensOf(await g.opens()));
      }
    });
  });
}
for (const surface of ["chat", "pane"] as Surface[]) {
  test("in a browser " + gateOn("fine", surface).replace("a fine click", "a fine pointer") + ", the predicate's accuracy, the other displays overflow does not apply to: a remote picture inside an author's ruby of a page class that sets overflow hidden (sub-head-waits, display ruby, a client size of 0 by 0), one inside a ruby text of that class (display ruby-text, 0 by 0), and one in a table cell that spans two rows, inside a table row of that class (display table-row, its box one row tall, the picture and its control past it), each control on the screen and uncovered: Enter, Space, a click on the picture and one on the control each open once (the file review's round 16, regression-1 with the coordinator's decision 1, which passes over every ancestor on which overflow clips nothing: every cell red under a skip of contents and inline alone, which read each element as a clip and refused the picture on every gesture, and the keys red at the head the file review's round 16 read, 0 opens, where its clicks opened with no gate)", { timeout: 180000 }, async (t) => {
    const rec: Record<string, unknown> = { scene: "author wrapper, more displays" };
    await gateCase(t, "fine", surface, WRAP_MORE_TEXT, rec, async (g) => {
      for (const [alt, display, sel] of [["gr", "ruby", "ruby"], ["gt", "ruby-text", "rt"], ["gw", "table-row", "tr"]] as const) {
        const st = await g.page.evaluate(([a, s]: [string, string]) => {
          const w = window as any, img = w.__img(a) as HTMLElement, el = img.closest(s) as HTMLElement, cs = getComputedStyle(el), r = el.getBoundingClientRect(), c = w.__ctl(a) as HTMLElement | null;
          const cr = c ? c.getBoundingClientRect() : null, x0 = r.left + el.clientLeft, y0 = r.top + el.clientTop;
          const meets = !!cr && Math.min(cr.right, x0 + el.clientWidth) > Math.max(cr.left, x0) && Math.min(cr.bottom, y0 + el.clientHeight) > Math.max(cr.top, y0);
          return { tag: el.localName, cls: el.getAttribute("class"), display: cs.display, overflow: cs.overflowX, client: [el.clientWidth, el.clientHeight], box: [Math.round(r.width), Math.round(r.height)], control: !!c, outsideClient: !!cr && !meets };
        }, [alt, sel]);
        rec[alt] = st;
        assert.ok(st.cls === "sub-head-waits" && st.display === display && st.overflow === "hidden" && st.control && st.outsideClient && (display === "table-row" || (st.client[0] === 0 && st.client[1] === 0)), alt + ": the author's " + sel + " computes display " + display + " and overflow hidden, the picture wears its control, and the control stands outside the element's client box" + (display === "table-row" ? " (the row one line tall, the spanning cell's picture below it)" : " (a client size of 0 by 0)") + ", where a read of the element as a clip leaves it out of view (a precondition): " + JSON.stringify(st));
        const mid = await keyOnControl(g, alt, () => g.place(alt, 200));
        rec[alt + "Mid"] = mid;
        assert.ok(mid.inView && mid.signHit && mid.active === "the sign", alt + ": the control holding the keyboard, in view and uncovered (a precondition): " + JSON.stringify(mid));
        await g.page.keyboard.press("Enter");
        g.cell(alt + " (display " + display + "): Enter's opens", [1, 1], opensOf(await g.opens()));
        await keyOnControl(g, alt, () => g.place(alt, 200));
        await g.page.keyboard.press("Space");
        g.cell(alt + " (display " + display + "): Space's opens", [1, 1], opensOf(await g.opens()));
        const r = await g.place(alt, 200);
        assert.equal(r.hit2, "the picture", alt + ": the click's point on the picture (a precondition): " + JSON.stringify(r));
        await g.gesture("fine", r.pt2.x, r.pt2.y);
        g.cell(alt + " (display " + display + "): a click on the picture, its opens", [1, 1], opensOf(await g.opens()));
        const c = await g.place(alt, 200);
        await g.gesture("fine", Math.round((c.sign[0] + c.sign[2]) / 2), Math.round((c.sign[1] + c.sign[3]) / 2));
        g.cell(alt + " (display " + display + "): a click on the control, its opens", [1, 1], opensOf(await g.opens()));
      }
    });
  });
}
GATE_SIZES["/zb.svg"] = [300, 200]; GATE_SIZES["/zr.svg"] = [2000, 300]; GATE_SIZES["/zn.svg"] = [300, 200];
GATE_SIZES["/f40.svg"] = [40, 40]; GATE_SIZES["/f48.svg"] = [48, 48]; GATE_SIZES["/f50.svg"] = [50, 50]; GATE_SIZES["/f476.svg"] = [48, 48];
const ZOOM_PARAS = (from: number, n: number): string => Array.from({ length: n }, (_, i) => PARA(from + i)).join("\n\n");
const ZOOM_TEXT = "# Report\n\n" + ZOOM_PARAS(1, 12) + "\n\n![zb](" + WEB + "/zb.svg)\n\n" + ZOOM_PARAS(13, 12) + "\n\n![zr](" + WEB + "/zr.svg)\n\n" + ZOOM_PARAS(25, 12)
  + "\n\n| words | more | picture |\n| --- | --- | --- |\n| " + FOCUS_CELL + " | " + FOCUS_CELL + " | ![zn](" + WEB + "/zn.svg) " + "picword".repeat(9) + " |\n\n" + ZOOM_PARAS(37, 12)
  + "\n\nThe floor: " + '<img src="' + WEB + '/f40.svg" alt="f40" width="40" height="40"> forty, <img src="' + WEB + '/f48.svg" alt="f48" width="48" height="48"> forty-eight, <img src="' + WEB + '/f50.svg" alt="f50" width="50" height="50"> fifty, <img src="' + WEB + '/f476.svg" alt="f476" width="47.6" height="47.6"> forty-seven point six.'
  + "\n\n" + ZOOM_PARAS(49, 12) + "\n";
type ZoomScene = "band" | "band150" | "right" | "out" | "pastBottom" | "pastRight" | "floor";
const ZOOM_SCENE_WORDS: Record<ZoomScene, string> = {
  band: "a control wholly visible in the body's bottom band: Enter, Space and a click on the picture each open once",
  band150: "the same with the viewer's own text size at 150%",
  right: "the control of a picture as wide as the Rendered column, at the body's right edge: Enter, Space and a click on the picture each open once",
  out: "a control above the body's top: Enter, Space and a click dispatched on it open nothing",
  pastBottom: "a control past the body's bottom edge, inside the window and clipped: Enter, Space and a dispatched click open nothing",
  pastRight: "a control past the right edge of a table that scrolls on its own, inside the body and the window and clipped: Enter, Space and a dispatched click open nothing",
  floor: "pictures laid out at 40, 48, 50 and 47.6 CSS px get the zoom-1 control verdict, a control for the 48 and the 50 and the mark for the others",
};
/** The zoom cells of one case: each scene's premise asserted from the page (the body's padding box read in the window's pixels, beside
 *  what its unscaled client size spans), then its gestures, each cell collected. `zoom` is the body's zoom the case set. */
async function zoomScenes(g: GateScene, zoom: number, scenes: ZoomScene[], rec: Record<string, unknown>): Promise<void> {
  const dispatchOn = (alt: string): Promise<void> => g.page.evaluate((a: string) => { (window as any).__ctl(a).dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true })); }, alt);
  const inViewCells = async (scene: string, alt: string, place: () => Promise<GateRead>, beyondRaw: (r: GateRead) => boolean, click: "pt" | "pt2"): Promise<void> => {
    const r = await keyOnControl(g, alt, place);
    rec[scene] = r;
    assert.ok(Math.abs(r.z - zoom) < 1e-4 && r.inView && r.signHit && r.active === "the sign" && r.sign[0] >= r.port[0] && r.sign[2] <= r.port[2] && r.sign[1] >= r.port[1] && r.sign[3] <= r.port[3] && beyondRaw(r), scene + ": the control holding the keyboard, wholly inside the body's padding box and uncovered" + (zoom > 1 ? ", and outside what the body's unscaled client size spans" : "") + " (a precondition): " + JSON.stringify(r));
    await g.page.keyboard.press("Enter");
    g.cell(scene + ": Enter's opens", [1, 1], opensOf(await g.opens()));
    await keyOnControl(g, alt, place);
    await g.page.keyboard.press("Space");
    g.cell(scene + ": Space's opens", [1, 1], opensOf(await g.opens()));
    const p = await place();
    const at = click === "pt" ? p.pt : p.pt2, hit = click === "pt" ? p.hit : p.hit2;
    assert.equal(hit, "the picture", scene + ": the click's point on the picture (a precondition): " + JSON.stringify(p));
    await g.gesture("fine", at.x, at.y);
    g.cell(scene + ": a click on the picture, its opens", [1, 1], opensOf(await g.opens()));
  };
  const outCells = async (scene: string, alt: string, place: () => Promise<GateRead>, premise: (r: GateRead) => boolean, why: string): Promise<void> => {
    const r = await keyOnControl(g, alt, place);
    rec[scene] = r;
    assert.ok(Math.abs(r.z - zoom) < 1e-4 && r.active === "the sign" && !r.signHit && premise(r), scene + ": the control holding the keyboard, " + why + " (a precondition): " + JSON.stringify(r));
    await g.page.keyboard.press("Enter");
    g.cell(scene + ": Enter's opens", [0, 0], opensOf(await g.opens()));
    await keyOnControl(g, alt, place);
    await g.page.keyboard.press("Space");
    g.cell(scene + ": Space's opens", [0, 0], opensOf(await g.opens()));
    await place();
    await dispatchOn(alt);
    g.cell(scene + ": a click dispatched on the control, its opens", [0, 0], opensOf(await g.opens()));
  };
  for (const scene of scenes) {
    if (scene === "band" || scene === "band150") {
      if (scene === "band150") {
        await stepTextSizeUp(g.page, 3);
        await g.page.keyboard.press("Escape");
        await frames(g.page, 3);
        const size = await g.page.evaluate(() => (document.querySelector(".fileview-size-reset") as HTMLElement).textContent);
        assert.equal(size, "150%", "the viewer's own text size at 150% (a precondition)");
      }
      const placeBand = async (): Promise<GateRead> => { const r0 = await g.read("zb"); return g.place("zb", r0.port[3] - r0.port[1] - 8 - (r0.sign[3] - r0.sign[1])); };
      await inViewCells(scene === "band" ? "the bottom band" : "the bottom band, the viewer's text size at 150%", "zb", placeBand, (r) => zoom <= 1 || r.sign[1] > r.raw[3], "pt");
    } else if (scene === "right") {
      await inViewCells("the right edge, the control of a picture as wide as the Rendered column", "zr", () => g.place("zr", 120), (r) => zoom <= 1 || r.sign[0] > r.raw[2], "pt2");
    } else if (scene === "out") {
      await outCells("above the body", "zb", () => g.place("zb", -60 * zoom), (r) => r.outside && r.sign[3] <= r.port[1], "above the body's padding box");
    } else if (scene === "pastBottom") {
      const placePast = async (): Promise<GateRead> => { const r0 = await g.read("zb"); return g.place("zb", r0.port[3] - r0.port[1] + 4); };
      await outCells("past the body's bottom edge", "zb", placePast, (r) => r.outside && r.sign[1] >= r.port[3] && r.sign[1] < 700 && (zoom >= 1 || r.sign[1] < r.raw[3]), "its top past the body's padding bottom and inside the window, clipped" + (zoom < 1 ? ", and inside what the body's unscaled client size spans" : ""));
    } else if (scene === "pastRight") {
      let table = { right: 0, raw: 0 };
      const placePast = async (): Promise<GateRead> => {
        await g.place("zn", 150);
        table = await g.page.evaluate(() => {
          const s = (window as any).__gsign("zn") as HTMLElement, tb = s.closest("table") as HTMLElement, z = (tb as any).currentCSSZoom > 0 ? (tb as any).currentCSSZoom : 1;
          const edge = (): number => tb.getBoundingClientRect().left + (tb.clientLeft + tb.clientWidth) * z;
          tb.scrollLeft += (s.getBoundingClientRect().left - edge() - 4) / z;   // the control's left 4px past the table's padding right; scrollLeft is in the table's own CSS pixels
          const r = tb.getBoundingClientRect();
          return { right: edge(), raw: r.left + tb.clientLeft + tb.clientWidth };
        });
        await frames(g.page, 3);
        return g.read("zn");
      };
      await outCells("past a table's right edge", "zn", placePast, (r) => r.sign[0] >= table.right && r.sign[0] < Math.min(r.port[2], 900) && (zoom >= 1 || r.sign[0] < table.raw), "its left past the padding right of the table that holds it, which scrolls on its own, and inside the body and the window, clipped by the table" + (zoom < 1 ? ", and inside what the table's unscaled client width spans" : ""));
    } else {
      const floor: Record<string, { css: number; control: boolean; mark: boolean }> = await g.page.evaluate(() => Object.fromEntries(["f40", "f48", "f50", "f476"].map((a) => { const w = window as any, i = w.__img(a) as HTMLElement, r = i.getBoundingClientRect(), z = (i as any).currentCSSZoom || 1; return [a, { css: Math.round(r.width / z * 1000) / 1000, control: !!w.__ctl(a), mark: i.hasAttribute("data-fv-figweb") }]; })));
      rec.floor = floor;
      const FLOOR: Array<[string, number, boolean[]]> = [["f40", 40, [false, true]], ["f48", 48, [true, false]], ["f50", 50, [true, false]], ["f476", 47.6, [false, true]]];
      assert.ok(FLOOR.every(([a, css]) => Math.abs(floor[a].css - css) < 0.05), "the four pictures laid out at 40, 48, 50 and 47.6 CSS px, within the layout's own rounding (a precondition): " + JSON.stringify(floor));
      for (const [a, css, want] of FLOOR) g.cell("the floor: the picture laid out at " + css + " CSS px, [a control, the mark]", want, [floor[a].control, floor[a].mark]);
    }
  }
}
const ZOOM_CASES: Array<[number, Surface, ZoomScene[]]> = [
  [1, "chat", ["band", "right", "out", "pastBottom", "pastRight", "floor"]],
  [1, "pane", ["band", "right", "out", "pastRight", "floor"]],
  [1.25, "chat", ["band", "right", "out", "floor", "band150"]],
  [1.25, "pane", ["band", "right", "out", "floor"]],
  [0.8, "chat", ["out", "pastBottom", "pastRight", "floor"]],
  [0.8, "pane", ["out", "pastRight", "floor"]],
  [14 / 13, "chat", ["floor"]],
];
for (const [zoom, surface, scenes] of ZOOM_CASES) {
  const what = zoom === 1 ? "the zoom-1 twin of the zoom cells" : "under a body zoom of " + zoom.toFixed(4).replace(/0+$/, "") + (zoom === 14 / 13 ? " (14/13, VS Code's zoom for its default editor font of 14px)" : "") + " in the VS Code extension's zoomStyle shape";
  const reds = zoom === 1 ? "the key cells green at the head the file review's round 16 read by design, and the clicks dispatched on a control out of view red there by group A's open"
    : zoom === 14 / 13 ? "the 47.6's floor cell red at the head the file review's round 16 read by a control, and the 48's red under a floor that divides by the zoom without rounding, where it measured 47.9965 CSS px"
    : zoom > 1 ? "the band's and the right edge's keys red at the head the file review's round 16 read, 0 opens, the 40's and the 47.6's floor cells red there by a control, the dispatched click above the body red there by group A's open, and the keys above the body green there by design"
    : "the past cells' keys red at the head the file review's round 16 read by one open each, the direction that opens a tab with the control hidden, their dispatched clicks and the one above the body red there by group A's open, the 48's and the 50's floor cells red there by the mark in place of a control, the 48's red too under a floor that divides by the zoom without rounding, and the keys above the body green there by design; the past cells hold the gate's composition, the predicate or the hit test, since elementFromPoint does not reach a clipped control, so under a region that reads the client size unscaled they stay green, and the node guard in file-view-outline.test.ts alone holds the 0.8 scaling";
  test("in a browser " + gateOn("fine", surface).replace("a fine click", "a fine pointer") + ", the predicate's accuracy, " + what + " (a harness page without the VS Code webviews' policy, which loads no remote picture: the cells hold the predicate's geometry): " + scenes.map((sc) => ZOOM_SCENE_WORDS[sc]).join("; ") + " (the file review's round 16, fresh-1: " + reds + "; the 47.6's cell red at every zoom under a floor read from offsetWidth)", { timeout: 240000 }, async (t) => {
    const rec: Record<string, unknown> = { scene: "zoom", zoom };
    await gateCase(t, "fine", surface, ZOOM_TEXT, rec, async (g) => {
      const z: number[] = await g.page.evaluate(() => [Number(getComputedStyle(document.body).zoom), Number((document.querySelector(".fileview-body") as any).currentCSSZoom)]);
      rec.bodyZoom = z;
      assert.ok(z.every((v) => Math.abs(v - zoom) < 1e-4), "the body's zoom as zoomStyle writes it, and the viewer body's effective zoom (a precondition): " + JSON.stringify(z));
      await zoomScenes(g, zoom, scenes, rec);
    }, [900, 700], zoom === 1 ? "" : "body{zoom:" + zoom.toFixed(4) + ";}");
  });
}

// The browser's own zoom, which the web dashboard's reader sets (Chromium's zoom is in the device scale, so a forced device scale lays
// the page out as that zoom does, with no viewport emulation over it; playwright's deviceScaleFactor does not enter the layout's zoom
// and reads the floor exactly): the floor at 90%. The layout snaps a box to 1/64 of a layout pixel, here 0.9 of a CSS pixel, so a
// picture laid out at 48 CSS px measures 47.986 and, unrounded, fell under the floor.
test("in a browser (a fine pointer, the chat modal), the floor under the browser's own zoom of 90% (a forced device scale of 0.9, the layout zoom the web dashboard's reader sets): pictures laid out at 40, 48, 50 and 47.6 CSS px get the zoom-1 control verdict, a control for the 48 and the 50 and the mark for the others (the file review's round 16, fresh-1: the 48's cell red at the head the file review's round 16 read, where it measured 47.986 CSS px and wore the mark in place of a control, and red under a floor that divides by the zoom without rounding; the others green there by design)", { timeout: 240000 }, async (t) => {
  const rec: Record<string, unknown> = { scene: "browser zoom", forced: 0.9 };
  await gateCase(t, "fine", "chat", ZOOM_TEXT, rec, async (g) => {
    const dpr: number = await g.page.evaluate(() => devicePixelRatio);
    rec.dpr = dpr;
    assert.ok(Math.abs(dpr - 0.9) < 1e-4, "the page's device pixel ratio is the forced 0.9, the layout zoom the browser's own zoom gives (a precondition): " + dpr);
    await zoomScenes(g, 1, ["floor"], rec);
  }, [900, 700], "", 0.9);
});

// ── the dimming classes off a figure's ancestors, on the paint (the file review's round 16, extra5-2) ── Under CDP touch emulation, where
// the web control and the mark stand at rest and a tap opens the tab from that state: an author's span of tag-chip-off (an opacity of
// 0.45 in the sheets) around a loaded remote picture wearing the control and around one under the floor wearing the mark, and an
// author's img wearing fv-figopen, the control's own class (0.8 at rest on a coarse pointer). file-view.ts takes every class the sheets
// dim off the markup around each figure of a file document (dropDimmingClasses over SHEET_DIM_CLASSES), so the span keeps its other
// class alone, the opacity composed from the dress up to the Rendered box is the dress's own, the dress paints at 3:1 or better by
// screenshot pixels (paintedRatio) in both themes, the author's img stands at full opacity, and a tap on each picture opens its tab as
// before. At the head the file review's round 16 read the span kept its class and the dress painted under it at 0.45 (2.00:1 dark and
// 1.86:1 light by that round's refuter), and the img computed 0.8.
const DIM_TEXT = "# Report\n\n" + PARA(1) + '\n\nChip <span class="tag-chip-off keep"><img src="' + WEB + '/fchip.svg" alt="fchip"></span> words.\n\n' + PARA(2)
  + '\n\nMark <span class="tag-chip-off keep"><img src="' + WEB + '/tiny.svg" alt="fmark"></span> words.\n\n' + PARA(3)
  + '\n\n<img class="fv-figopen keep" src="' + WEB + '/fimg.svg" alt="fimg">\n\n' + Array.from({ length: 10 }, (_, i) => PARA(i + 4)).join("\n\n") + "\n";
type DimRead = { kind: string; span: string[]; own: number; composed: number };
for (const surface of ["chat", "pane"] as Surface[]) {
  test("in a browser " + gateOn("touch", surface) + ", the dimming classes off a figure's ancestors: an author's span of tag-chip-off and keep around a loaded remote picture wearing the web control, and one around a remote picture under the floor wearing the mark, each keep the class keep alone; the opacity composed from the control, and from the marked picture, up to the Rendered box is the element's own; each dress paints at 3:1 or better by screenshot pixels at rest, in the dark theme and in the light one; an author's img wearing fv-figopen keeps its other class and stands at full opacity; and a tap on each picture, its sign in view, opens its tab once (the file review's round 16, extra5-2: red at the head that round read, where each span kept tag-chip-off, the composed opacity was 0.45 and the dress painted under 3:1, and the img computed 0.8 at rest; the taps green there by design; property pins read off the page)", { timeout: 180000 }, async (t) => {
    const rec: Record<string, unknown> = { scene: "the dimming classes" };
    await gateCase(t, "touch", surface, DIM_TEXT, rec, async (g) => {
      const d: { coarse: boolean; fchip: DimRead; fmark: DimRead; fimg: { classes: string[]; opacity: string } } = await g.page.evaluate(() => {
        const w = window as any, box = document.querySelector(".fileview-md") as HTMLElement;
        const composed = (e: Element): number => { let o = 1; for (let n: Element | null = e; n && n !== box.parentElement; n = n.parentElement) o *= Number(getComputedStyle(n).opacity); return Math.round(o * 1000) / 1000; };
        const one = (alt: string) => { const s = w.__gsign(alt) as HTMLElement, img = w.__img(alt) as HTMLElement; return { kind: s === img ? "mark" : "control", span: Array.from((img.parentElement as HTMLElement).classList), own: Number(getComputedStyle(s).opacity), composed: composed(s) }; };
        const fimg = w.__img("fimg") as HTMLElement;
        return { coarse: matchMedia("(pointer: coarse)").matches, fchip: one("fchip"), fmark: one("fmark"), fimg: { classes: Array.from(fimg.classList), opacity: getComputedStyle(fimg).opacity } };
      });
      rec.read = d;
      assert.deepEqual([d.coarse, d.fchip.kind, d.fmark.kind], [true, "control", "mark"], "a coarse pointer, the loaded picture's sign its web control and the small picture's its mark (the case's premise): " + JSON.stringify(d));
      g.cell("the span around the picture with the control: its classes", ["keep"], d.fchip.span);
      g.cell("the span around the picture with the mark: its classes", ["keep"], d.fmark.span);
      g.cell("the control's opacity, [its own, composed up to the Rendered box]", [d.fchip.own, d.fchip.own], [d.fchip.own, d.fchip.composed]);
      g.cell("the marked picture's opacity, [its own, composed up to the Rendered box]", [d.fmark.own, d.fmark.own], [d.fmark.own, d.fmark.composed]);
      g.cell("the author's img wearing fv-figopen: [its classes, its computed opacity at rest]", [["keep"], "1"], [d.fimg.classes, d.fimg.opacity]);
      const painted: Record<string, unknown> = {};
      for (const theme of ["dark", "light"] as const) {
        if (theme === "light") {
          await g.page.evaluate(() => new Promise<void>((done) => { const c = (window as any).__ctl("fchip") as HTMLElement; c.addEventListener("transitionend", () => done(), { once: true }); setTimeout(done, 1500); document.body.classList.add("theme-light"); }));
          await frames(g.page, 3);
        }
        const control = await paintedRatio(g.page, "fchip", "control"), mark = await paintedRatio(g.page, "fmark", "mark");
        painted[theme] = { control, mark };
        t.diagnostic("painted, " + theme + " theme: the control " + control.dash + " over " + control.ground + ", " + control.ratio.toFixed(3) + ":1 (opacities on the way: " + (control.opacities.join(", ") || "none") + "); the mark " + mark.dash + " against " + mark.ground + ", " + mark.ratio.toFixed(3) + ":1 (the worst read: " + mark.at + ")");
        g.cell("painted, " + theme + " theme: the web control inside the author's span at 3:1 or better", true, control.ratio >= 3);
        g.cell("painted, " + theme + " theme: the mark inside the author's span at 3:1 or better", true, mark.ratio >= 3);
      }
      rec.painted = painted;
      await g.page.evaluate(() => { document.body.classList.remove("theme-light"); });
      for (const alt of ["fchip", "fmark"]) {
        const at = await g.place(alt, 120);
        assert.ok(at.inView && at.hit2 === "the picture", alt + ": its sign in view and the tap's point on the picture (a precondition): " + JSON.stringify(at));
        await g.gesture("touch", at.pt2.x, at.pt2.y);
        g.cell("a tap on " + alt + ", its sign in view: its opens [popups, document requests]", [1, 1], opensOf(await g.opens()));
      }
    });
  });
}

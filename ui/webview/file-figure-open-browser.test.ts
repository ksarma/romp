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
// review's round 12, fresh-1 with tests-2). Red over
// the unchanged viewer at the first control assertion (no control exists), the outbound
// case red at the head before it, where the two controls presented one surface, and the link-shapes case red at the round-12
// head, where the title and the control read any anchor while the click did not, and the two under-the-floor cases red at that head too, the hover read and the at-rest read, where no rule dressed the picture. Skips LOUDLY without a playwright browser (in CI the Test step runs before the job's Chromium install, so the leg skips there; the launch is real-viewer-leg.ts's inBrowser, the shared helper). Synthetic values only: the notes-api world, a placeholder session id, example.invalid and example.test addresses,
// /repo/notes-api paths.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as http from "node:http";   // the outbound case's second server (the last test): a real origin of its own for the remote pictures
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
// dressed nothing on a touchscreen laptop, whose primary pointer hovers)
const TINY_TEXT = "# Report\n\n![local](figs/plot.svg)\n\n" + PARA(1) + "\n\n![build](" + WEB + "/tiny.svg)\n\n" + PARA(2) + "\n\n![big](" + WEB + "/pic.svg)\n\n" + PARA(3) + "\n";
const TINY_DOCS: Record<string, string> = { [REPORT]: TINY_TEXT, [PLOT]: svg("#456") };
type Under = { alt: string; w: number; h: number; control: boolean; controlOpacity: string | null; controlBorder: string | null; title: string | null; mark: boolean; outline: string; outlineWidth: string; outlineColor: string; border: string };
/** The three figures as the reader sees them: the box, the control after the img with its opacity and border colour, the title, the
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
 *  10 percent hairline read 1.35:1 dark and 1.25:1 light, present in the DOM as a faint ring under the floor on a 20 px badge. */
async function oneLegibleColour(page: any, r: { imgs: Under[] }, theme: string): Promise<void> {
  assert.equal(r.imgs[1].outlineColor, r.imgs[2].controlBorder, theme + " theme: the mark's outline colour is the control's border colour, one token (" + r.imgs[1].outlineColor + ")");
  const ground = await groundOf(page);
  const ratio = contrastOver(r.imgs[1].outlineColor, ground);
  // FAILS BEFORE (the file review's round 13): 1.35 dark and 1.25 light over the same ground
  assert.ok(ratio >= 3, theme + " theme: the mark's outline, " + r.imgs[1].outlineColor + " over the first opaque ground " + ground + ", reads " + ratio.toFixed(2) + ":1, under the 3:1 floor for the only sign of the outbound state");
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
  const second = await secondServer(served, { "/tiny.svg": [20, 20] });
  try {
    await inBrowser(t, async (browser) => {
      const { page, errors } = await openTiny(browser, second);
      const rest = await under(page);
      assert.equal(rest.hoverNone, false, "a fine pointer");
      assert.deepEqual(rest.imgs.map((x) => x.alt), ["local", "build", "big"], "the three figures");
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
      assert.deepEqual(errors, [], "no page errors");
      await page.close();
    });
  } finally { await second.close(); }
});
test("in a browser, under CDP touch emulation (hover none, a coarse pointer) enabled after the load and before any read, the pointer never over the picture: the remote picture under the floor wears the outbound mark AT REST, so the tap's open is visible before it happens, the mark's colour the control's border colour in the dark theme and in the light one, and the loaded picture beside it keeps its control visible at rest with no mark of its own; the tap opens the tab at the address (the popup and the second server's log, never a window.open stub) and the viewer stays (the file review's round 12, fresh-1: the at-rest read in a case of its own, so the leg's red over the undressed picture reaches it, where the case above, the hover read first, stops at the hover)", { timeout: 240000 }, async (t) => {
  const served: string[] = [];
  const second = await secondServer(served, { "/tiny.svg": [20, 20] });
  try {
    await inBrowser(t, async (browser) => {
      const { page, errors } = await openTiny(browser, second);
      const cdp = await page.context().newCDPSession(page);
      await cdp.send("Emulation.setTouchEmulationEnabled", { enabled: true, maxTouchPoints: 1 });
      await frames(page, 2);
      const touch = await under(page);
      assert.deepEqual([touch.hoverNone, touch.coarse], [true, true], "hover none and a coarse pointer under the emulation");
      assert.deepEqual(touch.imgs.map((x) => x.alt), ["local", "build", "big"], "the three figures");
      assert.deepEqual([touch.imgs[1].control, touch.imgs[1].title], [false, WEB_LINE(WEB + "/tiny.svg")], "the badge: no control under the floor, the address in its title");
      // FAILS BEFORE: outline none, the tap's open shown nowhere
      assert.deepEqual([touch.imgs[1].mark, touch.imgs[1].outline, touch.imgs[1].outlineWidth], [true, "dashed", "1px"], "at rest on a coarse pointer, no pointer ever over it, the badge wears the mark: the open is visible before the tap");
      assert.deepEqual([touch.imgs[2].controlOpacity, touch.imgs[2].outline], ["0.8", "none"], "the picture with a control: the control visible at rest, no mark on the picture");
      // one colour token for the two dresses (the owner's call with the ruling): the mark's outline colour is the control's border
      // colour, in the dark theme and, with body.theme-light, in the light one; the two themes resolve it apart, so the read is not one
      // value twice; and that colour, composited over the first opaque ground, clears 3:1 in each theme (oneLegibleColour)
      await oneLegibleColour(page, touch, "dark");
      // the theme flipped on the body; the control's border colour TRANSITIONS to the light value (.fileview-btn's 0.12 s
      // border-color ease) while the outline has no transition, so the light read waits for the control's transitionend (bounded)
      await page.evaluate(() => new Promise<void>((done) => { const c = document.querySelectorAll(".fileview-md img")[2].nextElementSibling as HTMLElement; c.addEventListener("transitionend", () => done(), { once: true }); setTimeout(done, 1500); document.body.classList.add("theme-light"); }));
      await frames(page, 2);
      const light = await under(page);
      await oneLegibleColour(page, light, "light");
      assert.notEqual(light.imgs[1].outlineColor, touch.imgs[1].outlineColor, "the two themes resolve the token apart: " + light.imgs[1].outlineColor + " against " + touch.imgs[1].outlineColor);
      assert.deepEqual([light.imgs[1].mark, light.imgs[1].outline], [true, "dashed"], "the mark stands in the light theme too");
      await page.evaluate(() => document.body.classList.remove("theme-light"));
      await frames(page, 2);
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
test("in Chromium launched as a trackpad-plus-touchscreen laptop (hover: hover, pointer: fine, any-pointer: coarse), the pointer never over the picture: the remote picture under the floor wears the outbound mark AT REST and the loaded picture's control stands visible at rest, one legible colour in both themes, where a rule keyed on (hover: none) alone dressed neither; a finger's tap opens the tab at the address and the viewer stays (the file review's round 13, extra7-2: the hybrid twin of the touch case above)", { timeout: 240000 }, async (t) => {
  const served: string[] = [];
  const second = await secondServer(served, { "/tiny.svg": [20, 20] });
  try {
    await inBrowser(t, async (browser) => {
      const { page, errors } = await openTiny(browser, second);
      const laptop = await pointing(page);
      assert.deepEqual([laptop.hoverNone, laptop.hoverHover, laptop.pointerFine, laptop.anyCoarse], [false, true, true, true], "the laptop: the primary pointer fine and hovering, a coarse pointer present (the context, asserted before the dress)");
      const rest = await under(page);
      assert.deepEqual(rest.imgs.map((x) => x.alt), ["local", "build", "big"], "the three figures");
      assert.deepEqual([rest.imgs[1].control, rest.imgs[1].title], [false, WEB_LINE(WEB + "/tiny.svg")], "the badge: no control under the floor, the address in its title");
      // FAILS BEFORE: outline none and the control at opacity 0, (hover: none) false on this laptop
      assert.deepEqual([rest.imgs[1].mark, rest.imgs[1].outline, rest.imgs[1].outlineWidth], [true, "dashed", "1px"], "at rest on the laptop, no pointer ever over it, the badge wears the mark: the finger's open is visible before the tap");
      assert.deepEqual([rest.imgs[2].controlOpacity, rest.imgs[2].outline], ["0.8", "none"], "the picture with a control: the control visible at rest, no mark on the picture");
      await oneLegibleColour(page, rest, "dark");
      await page.evaluate(() => new Promise<void>((done) => { const c = document.querySelectorAll(".fileview-md img")[2].nextElementSibling as HTMLElement; c.addEventListener("transitionend", () => done(), { once: true }); setTimeout(done, 1500); document.body.classList.add("theme-light"); }));
      await frames(page, 2);
      const light = await under(page);
      await oneLegibleColour(page, light, "light");
      assert.deepEqual([light.imgs[1].mark, light.imgs[1].outline, light.imgs[2].controlOpacity], [true, "dashed", "0.8"], "both dresses stand in the light theme too");
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
      assert.deepEqual(errors, [], "no page errors");
      await page.close();
    }, { args: [LAPTOP] });
  } finally { await second.close(); }
});

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
// keep their opens; print media shows no control even when it holds the focus; a device with no hover keeps it visible. Red
// over the unchanged viewer at the first control assertion (no control exists). Skips LOUDLY without a playwright browser (in CI the Test step runs before the job's Chromium install, so the leg skips there; the launch is real-viewer-leg.ts's inBrowser, the shared helper). Synthetic values only: the notes-api world, a placeholder session id, example.invalid addresses,
// /repo/notes-api paths.
import { test } from "node:test";
import * as assert from "node:assert/strict";
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
    assert.deepEqual([c[4].control, c[4].gated, c[4].title], [true, false, "Open the picture"], "loaded: the control stands after the img");
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

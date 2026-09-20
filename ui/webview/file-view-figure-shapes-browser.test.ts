// The figure control over the shapes the first review of the link-navigation follow-on (plans/markdown-viewer.md, L3) found
// it wrong on, driven through the REAL viewer in headless Chromium (real-viewer-leg.ts: the chat modal, file-view.ts bundled
// from this tree, styles.css, the /file fetch stub, a route for the figures' own requests). The source pins are in
// file-view-figure-shapes.test.ts. Read off the DOM, the layout and the trail: (1) a figure inside a link that holds more than
// the figure (text beside it, in markdown or in an author's <a>) wears NO control, and no control stands inside any link;
// the figure's plain click is the author's link, one open and one entry on the trail (before: the control went inside the
// link and one click opened the link's target AND the picture, so Back landed on a file the reader never asked for); (2) a
// figure alone in a link to a web address: the control stands after the link and the figure's plain click is the browser's
// own open of the address, never the picture (before: the tab AND the picture); (3) a badge (100 by 20) and an inline icon
// (16 by 16) wear no control, so the point beside the badge's edge is the badge and its click follows its link, and the
// point over the word before the icon is the prose (before: an invisible button hung there and opened the picture); a
// figure at the floor (48 by 48) keeps its control inside its own box; one a pixel under it on one side has none; (4) a
// protocol-relative source (`//host/pic.svg`, a gated placeholder until its click) opens a TAB from its control and from its
// plain click, the viewer and the trail unmoved (before: the viewer opened on the kernel's /file route at that path, a 404,
// and Back was armed); (5) a captioned picture inside a DEAD link (an `<a>` whose href the sanitizer removed, dressed fv-dead)
// wears no control either, since linkAbove reads any anchor (before: `a[href]` alone, so the control went inside the dead
// anchor); its plain click, with no link the links listener or the browser will act on, opens the picture. Skipped LOUDLY where playwright has no browser (CI installs none). Synthetic values only: the
// notes-api world, a placeholder session id, example.invalid addresses, /repo/notes-api paths.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, frames, ROOT, REPORT, SID, PARA } from "./real-viewer-leg";

const NOTES = ROOT + "/docs/notes.md";
const FIGS = ROOT + "/docs/figs/";
const WEB = "https://example.invalid/elsewhere";
const WEB_ALONE = "https://example.invalid/alone";
const PROTO = "//example.invalid/pic.svg";
const PROTO_ABS = "http://example.invalid/pic.svg";   // the page's origin is http, so the browser and absUrl resolve `//` to it
const DEAD_HREF = "javascript:void(0)";             // a scheme the sanitizer refuses: the anchor keeps no href and the viewer dresses it dead (file-view-links.ts DEAD_LINK_CLASS)
const svg = (w: number, h: number, fill: string): string => '<svg xmlns="http://www.w3.org/2000/svg" width="' + w + '" height="' + h + '"><rect width="' + w + '" height="' + h + '" fill="' + fill + '"/></svg>';
const SIZES: Record<string, [number, number]> = { "plot.svg": [300, 200], "badge.svg": [100, 20], "icon.svg": [16, 16], "mid.svg": [48, 48], "small.svg": [47, 60] };
// the report, one shape per paragraph: a bare figure; a figure with a caption inside a markdown link to a file; the same as an
// author's <a>; a figure with a caption inside a link to a web address; a figure alone in a link to a web address; a figure
// with a caption inside a section link; a linked badge; a sentence with an inline icon; a figure at the floor; one under it;
// a protocol-relative figure on an unlisted host (gated); the section the frag link names; enough prose after it to scroll
const REPORT_TEXT = "# Report\n\n![the plot](figs/plot.svg)\n\n"
  + "[![linked](figs/plot.svg) see the notes](notes.md)\n\n"
  + '<p><a href="notes.md"><img src="figs/plot.svg" alt="html"> caption</a></p>\n\n'
  + "[![weblinked](figs/plot.svg) the web](" + WEB + ")\n\n"
  + "[![alone](figs/plot.svg)](" + WEB_ALONE + ")\n\n"
  + "[![frag](figs/plot.svg) see results](#results)\n\n"
  + "[![ci](figs/badge.svg)](notes.md)\n\n"
  + "Click the ![icon](figs/icon.svg) button to run it.\n\n"
  + "![mid](figs/mid.svg)\n\n![small](figs/small.svg)\n\n"
  + "![proto](" + PROTO + ")\n\n"
  + "[![dead](figs/plot.svg) dead caption](" + DEAD_HREF + ")\n\n"
  + "## Results\n\n" + Array.from({ length: 30 }, (_, i) => PARA(i + 1)).join("\n\n") + "\n";
const NOTES_TEXT = "# Notes\n\nA short note.\n";
const DOCS: Record<string, string> = { [REPORT]: REPORT_TEXT, [NOTES]: NOTES_TEXT };
for (const [name, [w, h]] of Object.entries(SIZES)) DOCS[FIGS + name] = svg(w, h, "#468");
const ALTS = ["the plot", "linked", "html", "weblinked", "alone", "frag", "ci", "icon", "mid", "small", "proto", "dead"];

type Ctl = { alt: string; control: boolean; before: string | null; inLink: boolean; gated: boolean; w: number; h: number };
/** Every img of the Rendered box: whether a control stands after its anchor (the img, its wrap, or the link holding it alone),
 *  what stands before that control, whether the img sits inside any link, whether it is gated, and its box. */
const controls = (page: any): Promise<Ctl[]> => page.evaluate(() => {
  const box = document.querySelector(".fileview-md")!;
  return Array.from(box.querySelectorAll("img")).map((img) => {
    let a: Element = img;
    for (let p = a.parentElement; p && (p.localName === "a" || p.classList.contains("fc-imgwrap") || p.localName === "picture") && p.querySelectorAll("img").length === 1 && (p.localName !== "a" || (p.textContent || "").trim() === ""); p = a.parentElement) a = p;
    const n = a.nextElementSibling;
    const c = n && n.hasAttribute("data-fv-figopen") ? n : null;
    const r = img.getBoundingClientRect();
    return { alt: img.getAttribute("alt") || "", control: !!c, before: c ? c.previousElementSibling!.localName : null, inLink: !!img.closest("a"), gated: !!img.closest('[data-act="fv-load"]'), w: r.width, h: r.height };
  });
});
type Box = { left: number; top: number; right: number; bottom: number; width: number; height: number };
const boxOf = (page: any, sel: string, nth = 0): Promise<Box> => page.evaluate(([sel, nth]: [string, number]) => { const r = document.querySelectorAll(sel)[nth].getBoundingClientRect(); return { left: r.left, top: r.top, right: r.right, bottom: r.bottom, width: r.width, height: r.height }; }, [sel, nth]);
/** The element under a viewport point: its tag, and whether it is (or is inside) a figure control. */
const under = (page: any, x: number, y: number): Promise<{ tag: string; control: boolean; alt: string | null }> => page.evaluate(([x, y]: [number, number]) => {
  const e = document.elementFromPoint(x, y);
  return { tag: e ? e.localName : "", control: !!(e && e.closest("[data-fv-figopen]")), alt: e ? e.getAttribute("alt") : null };
}, [x, y]);
const base = (page: any): Promise<string | null> => page.locator(".fileview-base").textContent();
type Nav = { present: boolean; title?: string; disabled?: string | null };
const nav = (page: any): Promise<{ back: Nav; forward: Nav }> => page.evaluate(() => {
  const read = (dir: string): Nav => { const b = document.querySelector(".fileview-nav-" + dir) as HTMLButtonElement | null; return b ? { present: true, title: b.title, disabled: b.getAttribute("aria-disabled") } : { present: false }; };
  return { back: read("back"), forward: read("forward") };
});
/** The named file's paint: the bar's base name, and its body (a picture's img, or the Rendered box's first paragraph). */
async function painted(page: any, name: string): Promise<void> {
  await page.locator(".fileview-base", { hasText: name }).waitFor({ timeout: 10000 });
  await page.locator(/\.svg$/.test(name) ? "img.fileview-img" : ".fileview-md > p").first().waitFor({ timeout: 10000 });
  await frames(page, 3);
}
const opened = (page: any): Promise<string[]> => page.evaluate(() => (window as any).__opened.splice(0));
const enabledTo = (b: Nav, title: string, msg: string) => { assert.equal(b.present, true, msg + ": the button is in the bar"); assert.equal(b.disabled, null, msg + ": no aria-disabled with a target"); assert.equal(b.title, title, msg); };
const disabled = (b: Nav, msg: string) => { assert.equal(b.present, true, msg + ": the button is in the bar"); assert.equal(b.disabled, "true", msg + ": aria-disabled alone when empty"); };
/** Scroll the nth img of the box into the middle and return its box. */
async function centred(page: any, nth: number): Promise<Box> {
  await page.evaluate((n: number) => { document.querySelectorAll(".fileview-md img")[n].scrollIntoView({ block: "center" }); }, nth);
  await frames(page, 2);
  return boxOf(page, ".fileview-md img", nth);
}

/** The report open in the chat modal at 900 by 600, the local figures served from the /file route and the web ones from a
 *  route on their hosts (the popups too), window.open stubbed to a record, every local figure loaded and the controls settled
 *  (three: the bare plot, the figure alone in a web link, the figure at the floor). */
async function openReport(browser: any): Promise<{ page: any; errors: string[]; popups: string[] }> {
  const o = await openViewer(browser, "chat", 900, 600, {
    docs: DOCS,
    serve: (u) => { const p = u.pathname === "/file" ? u.searchParams.get("path") || "" : ""; return DOCS[p] !== undefined && /\.svg$/.test(p) ? { status: 200, type: "image/svg+xml", body: DOCS[p] } : null; },
  });
  const ctx = o.page.context();
  await ctx.route(/^https?:\/\/example\.invalid\//, (route: any) => {
    const u = route.request().url();
    if (/\.svg$/.test(u)) return route.fulfill({ status: 200, contentType: "image/svg+xml", body: svg(300, 200, "#333") });
    return route.fulfill({ status: 200, contentType: "text/html", body: "<!DOCTYPE html><p>the web</p>" });
  });
  const popups: string[] = [];
  ctx.on("page", (p: any) => { p.waitForLoadState().catch(() => null).then(() => { popups.push(p.url()); return p.close(); }).catch(() => null); });
  await o.page.evaluate(() => { const w = window as any; w.__opened = []; window.open = ((u: unknown) => { w.__opened.push(String(u)); return { opener: null }; }) as unknown as typeof window.open; });
  // every local figure's load, and the controls the loads settle (the paint adds one before a size is known; the load removes it on a figure under the floor)
  await o.page.waitForFunction(() => Array.from(document.querySelectorAll(".fileview-md img")).filter((i) => !i.closest('[data-act="fv-load"]')).every((i) => (i as HTMLImageElement).complete && (i as HTMLImageElement).naturalWidth > 0), null, { timeout: 10000 });
  await o.page.waitForFunction(() => document.querySelectorAll(".fileview-md [data-fv-figopen]").length === 3, null, { timeout: 10000 });
  await frames(o.page, 2);
  return { ...o, popups };
}
/** A popup the browser opens for an anchor's own activation (target _blank): awaited on the context's page event, never a timer. */
const popupAfter = async (page: any, act: () => Promise<void>): Promise<string> => {
  const p = page.context().waitForEvent("page", { timeout: 10000 });
  await act();
  const popup = await p;
  await popup.waitForLoadState().catch(() => null);
  return popup.url();
};

test("in a browser: no control stands inside a link; a figure with a caption inside a link (markdown or an author's <a>, to a file, a web address or a section) wears none, a figure alone in a link wears its control after the link; a badge, an inline icon and a figure a pixel under the floor wear none, one at the floor keeps its control inside its own box", async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openReport(browser);
    const c = await controls(page);
    assert.deepEqual(c.map((x) => x.alt), ALTS, "the twelve figures in order");
    // FAILS BEFORE: the captioned links' controls stood inside the <a>, the badge, the icon and the small figure wore one; and at the
    // round-2 head the captioned picture inside the DEAD link wore its control inside the dead anchor (linkAbove read `a[href]` alone)
    assert.deepEqual(c.map((x) => [x.alt, x.control]), [["the plot", true], ["linked", false], ["html", false], ["weblinked", false], ["alone", true], ["frag", false], ["ci", false], ["icon", false], ["mid", true], ["small", false], ["proto", false], ["dead", false]],
      "a control on the bare plot, on the figure alone in a web link, and on the figure at the floor; none inside a captioned link (a dead one too), on a badge, an icon, a figure under the floor, a gated placeholder");
    assert.equal(await page.evaluate(() => document.querySelectorAll(".fileview-md a [data-fv-figopen]").length), 0, "no control anywhere inside a link (nested interactive content, and the links listener's click)");
    const dead = await page.evaluate(() => { const a = document.querySelectorAll(".fileview-md img")[11].closest("a")!; return { href: a.getAttribute("href"), dead: a.classList.contains("fv-dead"), inside: a.querySelectorAll("[data-fv-figopen]").length }; });
    assert.deepEqual(dead, { href: null, dead: true, inside: 0 }, "the dead link: no href, dressed dead, and no control inside it");
    assert.equal(c[4].before, "a", "the figure alone in a web link: its control stands after the link");
    assert.deepEqual(c.slice(1, 4).map((x) => x.inLink), [true, true, true], "the captioned figures do sit inside their links (the shape under test)");
    assert.deepEqual([c[6].w, c[6].h, c[7].w, c[7].h, c[8].w, c[8].h, c[9].w, c[9].h], [100, 20, 16, 16, 48, 48, 47, 60], "the badge, the icon, the figure at the floor and the one under it measure as served");
    // the badge: the point 12px in from its right edge at mid height is the badge itself (before: the invisible control, 22px wide from right-28)
    const badge = await centred(page, 6);
    const atBadge = await under(page, badge.right - 12, badge.top + badge.height / 2);
    assert.deepEqual([atBadge.control, atBadge.tag, atBadge.alt], [false, "img", "ci"], "the badge's own pixels are the badge: " + JSON.stringify(atBadge));
    // the icon: the point 4px left of it, over the last letters of the word before it, is the prose (before: the control's box, from left-12 to left+10)
    const icon = await centred(page, 7);
    const atProse = await under(page, icon.left - 4, icon.top + 8);
    assert.deepEqual([atProse.control, atProse.tag], [false, "p"], "the prose before the icon is the prose: " + JSON.stringify(atProse));
    // the figure at the floor: its control lies inside its box, 6px in from the corner
    const mid = await centred(page, 8);
    const midCtl = await boxOf(page, ".fileview-md [data-fv-figopen]", 2);
    assert.ok(midCtl.left >= mid.left && midCtl.right <= mid.right + 0.5 && midCtl.top >= mid.top && midCtl.bottom <= mid.bottom + 0.5, "inside the 48px figure: " + JSON.stringify([mid, midCtl]));
    assert.ok(Math.abs(midCtl.right - (mid.right - 6)) <= 1 && Math.abs(midCtl.top - (mid.top + 6)) <= 1, "at the top-right corner, 6px in");
    assert.deepEqual(errors, [], "no page errors");
    await page.close();
  });
});

test("in a browser: the plain click on a captioned linked figure is the author's link alone (one open, one entry on the trail, Back to the report, then the root); on a badge it follows the badge's link; on a figure inside a link to a web address it is the browser's own open and never the picture; the control of a figure alone in a web link opens the picture", async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors, popups } = await openReport(browser);
    // the captioned link to a file: the link's open and nothing else (before: the control inside the <a> was the only click target at the corner, and its click opened notes.md AND the picture)
    let b = await centred(page, 1);
    await page.mouse.click(b.left + b.width * 0.3, b.top + b.height * 0.6);
    await painted(page, "notes.md");
    enabledTo((await nav(page)).back, "Back to report.md", "the author's link: one push");
    await page.click(".fileview-nav-back");
    await painted(page, "report.md");
    let n = await nav(page);
    disabled(n.back, "back at the root: nothing behind the report"); enabledTo(n.forward, "Forward to notes.md", "the notes ahead");
    await page.waitForFunction(() => document.querySelectorAll(".fileview-md [data-fv-figopen]").length === 3, null, { timeout: 10000 });
    // the author's <a> with a caption: the same
    b = await centred(page, 2);
    await page.mouse.click(b.left + b.width * 0.3, b.top + b.height * 0.6);
    await painted(page, "notes.md");
    enabledTo((await nav(page)).back, "Back to report.md", "the author's <a>: one push");
    await page.click(".fileview-nav-back");
    await painted(page, "report.md");
    await page.waitForFunction(() => document.querySelectorAll(".fileview-md [data-fv-figopen]").length === 3, null, { timeout: 10000 });
    // the badge: its whole face follows its link (before: the corner 12px in opened badge.svg in the viewer)
    b = await centred(page, 6);
    await page.mouse.click(b.right - 12, b.top + b.height / 2);
    await painted(page, "notes.md");
    enabledTo((await nav(page)).back, "Back to report.md", "the badge's link");
    await page.click(".fileview-nav-back");
    await painted(page, "report.md");
    await page.waitForFunction(() => document.querySelectorAll(".fileview-md [data-fv-figopen]").length === 3, null, { timeout: 10000 });
    n = await nav(page);
    disabled(n.back, "the root again");
    // the captioned link to a web address: the browser's own popup, the viewer unmoved
    b = await centred(page, 3);
    const u1 = await popupAfter(page, () => page.mouse.click(b.left + b.width * 0.3, b.top + b.height * 0.6));
    assert.equal(u1, WEB, "the anchor's own activation opened the address");
    await frames(page, 3);
    assert.equal(await base(page), "report.md", "the viewer shows the report still");
    assert.deepEqual(await opened(page), [], "window.open was not called: the popup is the anchor's");
    disabled((await nav(page)).back, "the trail did not move");
    // FAILS BEFORE: the figure alone in a web link: its plain click opened the tab AND the picture (a markdown web anchor carries no class, so linkOf read none)
    b = await centred(page, 4);
    const u2 = await popupAfter(page, () => page.mouse.click(b.left + b.width * 0.3, b.top + b.height * 0.6));
    assert.equal(u2, WEB_ALONE, "the anchor's own activation opened the address");
    await frames(page, 3);
    assert.equal(await base(page), "report.md", "never the picture from the figure's own click inside a link");
    assert.deepEqual(await opened(page), []);
    disabled((await nav(page)).back, "the trail did not move");
    // its control, after the link, is its own: the picture, Back to the report
    await centred(page, 4);
    await page.locator(".fileview-md [data-fv-figopen]").nth(1).click();
    await painted(page, "plot.svg");
    enabledTo((await nav(page)).back, "Back to report.md", "the control opens the picture itself");
    await page.click(".fileview-nav-back");
    await painted(page, "report.md");
    // the captioned picture inside a DEAD link: no link the links listener or the browser will act on, so the plain click opens
    // the picture (the figure listener yields to a path link, a web anchor with an href and a section link; a dead anchor is none)
    b = await centred(page, 11);
    await page.mouse.click(b.left + b.width * 0.3, b.top + b.height * 0.6);
    await painted(page, "plot.svg");
    enabledTo((await nav(page)).back, "Back to report.md", "inside a dead link the plain click opens the picture: the trail's push");
    await page.click(".fileview-nav-back");
    await painted(page, "report.md");
    assert.equal(popups.length, 2, "two popups in all, both the anchors' own: " + JSON.stringify(popups));
    assert.deepEqual(errors, [], "no page errors");
    await page.close();
  });
});

test("in a browser: a protocol-relative figure on an unlisted host is a gated placeholder; loaded, its control and its plain click open a TAB at the address the browser resolved, the viewer and the trail unmoved (before: the viewer opened on the kernel's /file route at path //host/pic.svg, a 404, and Back was armed)", async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors, popups } = await openReport(browser);
    const g = (await controls(page))[10];
    assert.deepEqual([g.alt, g.control, g.gated], ["proto", false, true], "gated: no control on the placeholder");
    await page.evaluate(() => { document.querySelector('[data-act="fv-load"]')!.scrollIntoView({ block: "center" }); });
    await frames(page, 1);
    await page.click('[data-act="fv-load"]');
    await page.waitForFunction(() => { const i = document.querySelectorAll(".fileview-md img")[10] as HTMLImageElement; return !!i && !i.closest('[data-act="fv-load"]') && i.complete && i.naturalWidth > 0 && !!(i.nextElementSibling && i.nextElementSibling.hasAttribute("data-fv-figopen")); }, null, { timeout: 10000 });
    await frames(page, 2);
    const c = (await controls(page))[10];
    assert.deepEqual([c.alt, c.control, c.gated], ["proto", true, false], "loaded: the control stands after the img");
    assert.equal(await page.evaluate(() => (document.querySelectorAll(".fileview-md img")[10] as HTMLImageElement).currentSrc), PROTO_ABS, "the browser fetched it from the web");
    await page.locator(".fileview-md [data-fv-figopen]").nth(3).click();
    await frames(page, 3);
    // FAILS BEFORE: the base read pic.svg, the body the kernel's not-found line, Back "Back to report.md", and nothing was opened
    assert.deepEqual(await opened(page), [PROTO_ABS], "a tab at the address, from the control");
    assert.equal(await base(page), "report.md", "never the viewer");
    disabled((await nav(page)).back, "the trail did not move");
    const b = await centred(page, 10);
    await page.mouse.click(b.left + b.width * 0.3, b.top + b.height * 0.6);
    await frames(page, 3);
    assert.deepEqual(await opened(page), [PROTO_ABS], "and from the figure's own plain click");
    assert.equal(await base(page), "report.md");
    disabled((await nav(page)).back, "the trail did not move");
    assert.equal(await page.evaluate(() => document.querySelector("#romp-fileview .fileview-err")), null, "no not-found line anywhere");
    assert.deepEqual(popups, [], "no popup: window.open is the viewer's road to a tab");
    assert.deepEqual(errors, [], "no page errors");
    await page.close();
  });
});

// The figure control decided from the figure's CURRENT state (plans/markdown-viewer.md, "Follow-on: Link navigation", L3; the
// file review: five findings, one cause, the control decided once at the paint from what was known then), driven through
// the REAL viewer in headless Chromium (real-viewer-leg.ts: the chat modal, file-view.ts bundled from this tree, styles.css,
// the /file fetch stub, a route for the figures' own requests). Three states beside the floor's (file-view-figure-floor-
// browser.test.ts), each red at the head before the one decision (decideFigureControl over figureState), and a fourth case
// (the file review's round 2, regression-3 with extra5-4): a FAILED figure WITH a box (a non-empty alt, which Chromium lays
// out as text where an empty alt is 0 by 0) opens nothing on a plain click and nothing on a Ctrl-click, as it wears no control, since figureTarget
// refuses the failed state as it refuses the fetching one (FAILS BEFORE: figureTarget refused fetching alone, so the plain click
// opened the missing path in the viewer and pushed it onto the trail while the control was withheld):
// (1) FAILED: a figure whose file is missing, with an empty alt, is a 0 by 0 box; the control the paint added stood 28 px to
//     its left over the link before it and took the click meant for the link (the click opened the missing picture's path in
//     the viewer). Now a failed figure wears no control and the click reaches the link.
// (2) FETCHING: a `<picture>` whose `<source>` is still on the wire has an empty currentSrc, which chosenSource read as the
//     src, so the control the paint added, and the figure's plain click, opened the fallback the browser never asked for and
//     put that file on the trail. Now a fetching figure wears no control and its plain click opens nothing; the load brings the control, which
//     opens the source's file.
// (3) A `data:` CANDIDATE: a srcset figure whose chosen candidate is a `data:` URI wore the control the paint added from the
//     src, and its click did nothing (figureTarget answers null for a data: URL). Now the load decides against it: no
//     control.
// Skipped LOUDLY where playwright has no browser (CI installs none). Synthetic values only: the notes-api world, a placeholder
// session id, /repo/notes-api paths.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, frames, ROOT, REPORT, SID, ORIGIN, PARA } from "./real-viewer-leg";
import type { Served } from "./real-viewer-leg";

const NOTES = ROOT + "/docs/notes.md";
const FIGS = ROOT + "/docs/figs/";
const PLOT = FIGS + "plot.svg";
const SLOW = FIGS + "slow.svg";
const MISSING = FIGS + "missing.svg";
const GONE = FIGS + "gone.svg";        // a missing local figure WITH a box: a non-empty alt, which Chromium lays out as text
const svg =(w: number, h: number, fill: string): string => '<svg xmlns="http://www.w3.org/2000/svg" width="' + w + '" height="' + h + '"><rect width="' + w + '" height="' + h + '" fill="' + fill + '"/></svg>';
/** A `data:` candidate with no whitespace (a srcset splits candidates on whitespace), put SECOND in the value: DOMPurify drops a
 *  srcset whose first candidate is a data: URL. At a device scale of 1 the browser takes the 1x candidate, this one. */
const INLINE = "data:image/svg+xml," + encodeURIComponent(svg(100, 100, "#987"));
// the report: a link with the missing figure right after its text (no space, so the stale control's 28 px overhang lay over
// the link's last letters), the fetching <picture> (a box from its attributes, so the plain click has somewhere to land), the
// srcset figure whose 1x candidate is inline, and prose
const REPORT_TEXT = "# Report\n\nSee [the notes](notes.md)![](figs/missing.svg) for more.\n\n"
  + '<picture><source srcset="figs/slow.svg"><img src="figs/plot.svg" alt="slow" width="300" height="200"></picture>\n\n'
  + '<img src="figs/plot.svg" srcset="figs/plot.svg 2x, ' + INLINE + ' 1x" alt="inline candidate">\n\n'
  + Array.from({ length: 10 }, (_, i) => PARA(i + 1)).join("\n\n") + "\n";
const NOTES_TEXT = "# Notes\n\nA short note.\n";
const DOCS: Record<string, string> = { [REPORT]: REPORT_TEXT, [NOTES]: NOTES_TEXT, [PLOT]: svg(300, 200, "#456"), [SLOW]: svg(300, 200, "#654") };
const FILE_URL = (p: string): string => ORIGIN + "/file?path=" + encodeURIComponent(p) + "&sid=" + encodeURIComponent(SID);

type Fig = { alt: string; control: boolean; state: string; currentSrc: string; box: [number, number] };
/** Every img of the Rendered box: the control after its anchor (the img or its picture), the state as the viewer reads it
 *  (`complete` and `naturalWidth`), currentSrc, and its laid-out box. */
const figures = (page: any): Promise<Fig[]> => page.evaluate(() => {
  const box = document.querySelector(".fileview-md")!;
  return Array.from(box.querySelectorAll("img")).map((img) => {
    let a: Element = img;
    for (let p = a.parentElement; p && (p.localName === "picture" || p.classList.contains("fc-imgwrap")); p = a.parentElement) a = p;
    const n = a.nextElementSibling;
    const i = img as HTMLImageElement;
    const r = i.getBoundingClientRect();
    return { alt: img.getAttribute("alt") || "", control: !!(n && n.hasAttribute("data-fv-figopen")), state: !i.complete ? "fetching" : i.naturalWidth > 0 ? "loaded" : "failed", currentSrc: i.currentSrc || "", box: [Math.round(r.width), Math.round(r.height)] as [number, number] };
  });
});
type Box = { left: number; top: number; right: number; bottom: number; width: number; height: number };
const boxOf = (page: any, sel: string, nth = 0): Promise<Box> => page.evaluate(([sel, nth]: [string, number]) => { const r = document.querySelectorAll(sel)[nth].getBoundingClientRect(); return { left: r.left, top: r.top, right: r.right, bottom: r.bottom, width: r.width, height: r.height }; }, [sel, nth]);
/** The element under a viewport point: its tag, whether it is (or is inside) a figure control, and whether it is inside a link. */
const under = (page: any, x: number, y: number): Promise<{ tag: string; control: boolean; inLink: boolean }> => page.evaluate(([x, y]: [number, number]) => {
  const e = document.elementFromPoint(x, y);
  return { tag: e ? e.localName : "", control: !!(e && e.closest("[data-fv-figopen]")), inLink: !!(e && e.closest("a")) };
}, [x, y]);
const base = (page: any): Promise<string | null> => page.locator(".fileview-base").textContent();
type Nav = { present: boolean; title?: string; disabled?: string | null };
const backNav = (page: any): Promise<Nav> => page.evaluate(() => { const b = document.querySelector(".fileview-nav-back") as HTMLButtonElement | null; return b ? { present: true, title: b.title, disabled: b.getAttribute("aria-disabled") } : { present: false }; });
/** The named file's paint: the bar's base name, and its body (a picture's img, or the Rendered box's first paragraph). */
async function painted(page: any, name: string): Promise<void> {
  await page.locator(".fileview-base", { hasText: name }).waitFor({ timeout: 10000 });
  await page.locator(/\.svg$/.test(name) ? "img.fileview-img" : ".fileview-md > p").first().waitFor({ timeout: 10000 });
  await frames(page, 3);
}
/** The GET /file requests the viewer's own fetch made since the last read, as absolute URLs. */
const gotFiles = async (page: any): Promise<string[]> => {
  const got: Array<{ u: string; m: string }> = await page.evaluate(() => (window as any).__fetched.splice(0));
  return got.filter((r) => r.m === "GET" && /[?&]path=/.test(r.u)).map((r) => new URL(r.u, ORIGIN).href);
};

/** The figures' own requests at the /file route: the plot and the notes as served, the missing figure the kernel's 404, the
 *  slow figure HELD until the test releases it (a route registered on the page after the open outranks the harness's, so the
 *  hold is this leg's own; `serve` is synchronous and cannot hold). */
const serve = (u: URL): Served | null => {
  if (u.pathname !== "/file") return null;
  const p = u.searchParams.get("path") || "";
  if (p === MISSING || p === GONE) return { status: 404, type: "text/plain; charset=utf-8", body: "not found: " + p };
  return DOCS[p] !== undefined && /\.svg$/.test(p) ? { status: 200, type: "image/svg+xml", body: DOCS[p] } : null;
};

test("in a browser: a FAILED figure (missing file, empty alt) wears no control, so the click at the link's last letters is the link's; a FETCHING <picture> wears none and its plain click opens nothing until the source lands, then the control opens the source's file; a srcset figure whose chosen candidate is a data: URI wears none once loaded", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    // the slow figure's hold: a page route registered after the harness's, so it wins the match, holding the response until released
    let release: (() => void) | null = null;
    const held = new Promise<void>((r) => { release = r; });
    let slowAsked = 0;
    const { page, errors } = await openViewer(browser, "chat", 900, 600, {
      docs: { [REPORT]: "# Report\n\nA placeholder note.\n", [NOTES]: NOTES_TEXT, [PLOT]: DOCS[PLOT], [SLOW]: DOCS[SLOW] },
      serve,
    });
    await page.route((u: URL) => u.pathname === "/file" && u.searchParams.get("path") === SLOW, async (route: any) => {
      slowAsked++;
      await held;
      try { await route.fulfill({ status: 200, contentType: "image/svg+xml", body: DOCS[SLOW] }); } catch { /* the figure that asked is gone: the report was re-opened while the answer was held */ }
    });
    await page.evaluate(([docs]: [Record<string, string>]) => {
      const w = window as any;
      Object.assign(w.__docs, docs);
      const f = window.fetch; w.__fetched = [];
      window.fetch = function (u: any, i?: any) { w.__fetched.push({ u: String(u), m: (i && i.method) || "GET" }); return f.call(window, u, i); } as typeof window.fetch;
    }, [{ [REPORT]: REPORT_TEXT }]);
    // the report proper, opened over the placeholder note once the hold is armed
    await page.evaluate(([p, sid]: [string, string]) => { (window as any).FV.openFileView(p, sid, null); }, [REPORT, SID]);
    await page.locator(".fileview-md > p").first().waitFor({ timeout: 10000 });
    // the missing figure's error and the inline candidate's load, before anything is read; the slow picture stays on the wire
    await page.waitForFunction(() => { const imgs = Array.from(document.querySelectorAll(".fileview-md img")) as HTMLImageElement[]; return imgs.length === 3 && imgs[0].complete && imgs[2].complete; }, null, { timeout: 10000 });
    await frames(page, 3);
    await gotFiles(page);   // the report's own GET: not the opens'
    const at = await figures(page);
    t.diagnostic("after the paint: " + JSON.stringify(at));
    assert.deepEqual(at.map((f) => [f.alt, f.state]), [["", "failed"], ["slow", "fetching"], ["inline candidate", "loaded"]], "the three states on the page: failed, fetching, loaded");
    assert.equal(slowAsked, 1, "the slow source was asked for once and is held");
    assert.deepEqual(at[0].box, [0, 0], "the failed figure with an empty alt is a 0 by 0 box");
    assert.equal(at[1].currentSrc, "", "while its source is on the wire the <picture> names nothing in currentSrc (the read chosenSource took as the fallback src, which opened the wrong file)");
    assert.equal(at[2].currentSrc.slice(0, 19), "data:image/svg+xml,", "the browser chose the inline 1x candidate");
    // (1) FAILS BEFORE: the failed figure wore a control (figureBox answered null for it, so the floor never applied), laid 28 px
    // to its left over the link's last letters
    assert.equal(at[0].control, false, "a failed figure wears no control");
    // (3) FAILS BEFORE: the control added at the paint from the src was never re-judged against the data: candidate the browser chose
    assert.equal(at[2].control, false, "a figure whose chosen candidate is a data: URI wears no control");
    // (2) FAILS BEFORE: the control stood at the paint, opening the fallback src the browser never asked for
    assert.equal(at[1].control, false, "a fetching figure wears no control");
    assert.equal(await page.evaluate(() => document.querySelectorAll(".fileview-md [data-fv-figopen]").length), 0, "no control anywhere on the page yet");
    // (1) the point 10 px left of the failed figure, over the link's last letters, at the line's middle: the link, and its click
    // opens the notes (before: the invisible control, whose click opened the missing picture's path in the viewer)
    const miss = await boxOf(page, ".fileview-md img", 0);
    const line = await boxOf(page, ".fileview-md > p", 0);
    const pt: [number, number] = [miss.left - 10, line.top + Math.min(line.height, 22) / 2];
    const atLink = await under(page, pt[0], pt[1]);
    assert.deepEqual([atLink.control, atLink.inLink], [false, true], "the link's own pixels beside the failed figure: " + JSON.stringify(atLink));
    await page.mouse.click(pt[0], pt[1]);
    await painted(page, "notes.md");
    assert.equal(await base(page), "notes.md", "the click was the link's");
    assert.deepEqual(await gotFiles(page), [FILE_URL(NOTES)], "one GET, the notes (before: missing.svg, the failed picture's path, from the stale control)");
    await page.click(".fileview-nav-back");
    await painted(page, "report.md");
    await gotFiles(page);   // the report's re-open
    await page.waitForFunction(() => { const i = document.querySelectorAll(".fileview-md img")[0] as HTMLImageElement | undefined; return !!i && i.complete; }, null, { timeout: 10000 });
    await frames(page, 2);
    // (2) the plain click on the fetching <picture> (its 300 by 200 box from the attributes): nothing opens, nothing is fetched
    // (before: plot.svg, the fallback, opened in the viewer and went onto the trail)
    const slow = await boxOf(page, ".fileview-md img", 1);
    assert.ok(slow.width >= 290 && slow.height >= 190, "the fetching picture has its attributes' box to click on: " + JSON.stringify(slow));
    await page.mouse.click(slow.left + slow.width * 0.3, slow.top + slow.height * 0.6);
    await frames(page, 3);
    assert.equal(await base(page), "report.md", "a plain click on a fetching figure opens nothing");
    assert.deepEqual(await gotFiles(page), [], "and fetches nothing");
    assert.deepEqual(await backNav(page), { present: true, title: "Back", disabled: "true" }, "the trail did not move");
    assert.equal((await figures(page))[1].state, "fetching", "still on the wire");
    // the source lands: the load decides again, the control arrives, and it opens the SOURCE's file (never the fallback)
    release!();
    await page.waitForFunction(() => { const i = document.querySelectorAll(".fileview-md img")[1] as HTMLImageElement; return i.complete && i.naturalWidth > 0 && !!(i.parentElement!.nextElementSibling && i.parentElement!.nextElementSibling!.hasAttribute("data-fv-figopen")); }, null, { timeout: 10000 });
    await frames(page, 2);
    const loaded = await figures(page);
    t.diagnostic("after the slow load: " + JSON.stringify(loaded));
    assert.deepEqual([loaded[1].state, loaded[1].control, loaded[1].currentSrc], ["loaded", true, FILE_URL(SLOW)], "loaded from the source: the control stands after the picture");
    assert.deepEqual(loaded.map((f) => f.control), [false, true, false], "one control on the page, the loaded picture's; the failed and the inline-candidate figures still have none");
    await page.locator(".fileview-md [data-fv-figopen]").nth(0).click();
    await painted(page, "slow.svg");
    assert.equal(await base(page), "slow.svg", "the control opens the source's file");
    assert.deepEqual(await gotFiles(page), [FILE_URL(SLOW)], "through the URL the paint fetched it by");
    assert.deepEqual(await backNav(page), { present: true, title: "Back to report.md", disabled: null }, "the trail's push");
    await page.click(".fileview-nav-back");
    await painted(page, "report.md");
    // (3) the inline-candidate figure's corner is the figure, not a control (before: a dead button)
    const inl = await boxOf(page, ".fileview-md img", 2);
    const corner = await under(page, inl.right - 17, inl.top + 17);
    assert.deepEqual([corner.control, corner.tag], [false, "img"], "the corner of the inline-candidate figure is the figure: " + JSON.stringify(corner));
    assert.deepEqual(errors, [], "no page errors");
    await page.close();
  });
});

// the report for the fourth case: a missing local figure with a box to click on (a non-empty alt, laid out as text; the width and
// height attributes are written as an author would, and Chromium does not size the alt text by them), a sentence under it, and prose
const GONE_TEXT = "# Report\n\n<img src=\"figs/gone.svg\" alt=\"gone\" width=\"300\" height=\"200\">\n\nA sentence under the missing picture.\n\n"
  + Array.from({ length: 10 }, (_, i) => PARA(i + 1)).join("\n\n") + "\n";

test("in a browser: a FAILED local figure with a box (a non-empty alt, laid out as text) wears no control, and its plain click opens nothing (the viewer shows the report still, no GET, the trail unmoved) while its label names the missing source; a Ctrl-click opens no tab either", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openViewer(browser, "chat", 900, 600, { docs: { [REPORT]: GONE_TEXT, [PLOT]: DOCS[PLOT] }, serve });
    await page.evaluate(() => {
      const w = window as any;
      w.__opened = []; window.open = ((u: unknown) => { w.__opened.push(String(u)); return { opener: null }; }) as unknown as typeof window.open;
      const f = window.fetch; w.__fetched = [];
      window.fetch = function (u: any, i?: any) { w.__fetched.push({ u: String(u), m: (i && i.method) || "GET" }); return f.call(window, u, i); } as typeof window.fetch;
    });
    await page.waitForFunction(() => { const i = document.querySelector(".fileview-md img") as HTMLImageElement | null; return !!i && i.complete; }, null, { timeout: 10000 });
    await frames(page, 3);
    await gotFiles(page);   // anything since the open: not the click's
    const at = await figures(page);
    t.diagnostic("the failed figure: " + JSON.stringify(at));
    assert.deepEqual([at[0].alt, at[0].state, at[0].control], ["gone", "failed", false], "failed, and no control (the file review's round-1 state)");
    // Chromium lays a failed img with a non-empty alt out as its alt text (53 by 22 here, measured), not as its width and height
    // attributes: a box all the same, and the click lands on the img
    assert.ok(at[0].box[0] > 0 && at[0].box[1] > 0, "the alt gives it a box to click on: " + JSON.stringify(at[0].box));
    assert.match(await page.evaluate(() => (document.querySelector(".fileview-md [data-fv-figerr]") as HTMLElement | null)?.textContent || ""), /gone\.svg/, "the label names the missing source");
    // the plain click on the failed figure's box: nothing opens, nothing is fetched, the trail stands. FAILS BEFORE: the viewer
    // opened gone.svg (the kernel's not-found pane), Back read "Back to report.md", and one GET of gone.svg left
    const b = await boxOf(page, ".fileview-md img", 0);
    assert.equal(await page.evaluate(([x, y]: [number, number]) => { const e = document.elementFromPoint(x, y); return e ? e.localName : ""; }, [b.left + b.width / 2, b.top + b.height / 2]), "img", "the img is under the point clicked");
    await page.mouse.click(b.left + b.width / 2, b.top + b.height / 2);
    await frames(page, 3);
    assert.equal(await base(page), "report.md", "a plain click on a failed figure opens nothing");
    assert.deepEqual(await gotFiles(page), [], "and fetches nothing");
    assert.deepEqual(await backNav(page), { present: true, title: "Back", disabled: "true" }, "the trail did not move");
    // a Ctrl-click: no tab either (the same target, none)
    await page.keyboard.down("Control"); await page.mouse.click(b.left + b.width / 2, b.top + b.height / 2); await page.keyboard.up("Control");
    await frames(page, 3);
    assert.deepEqual(await page.evaluate(() => (window as any).__opened.splice(0)), [], "no tab from a Ctrl-click on a failed figure");
    assert.equal(await base(page), "report.md");
    assert.deepEqual(await gotFiles(page), []);
    assert.deepEqual(errors, [], "no page errors");
    await page.close();
  });
});

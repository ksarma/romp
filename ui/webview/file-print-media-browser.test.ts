// Print for the two media kinds (file-print.ts, parts P3 and P4 of the print follow-on to plans/markdown-viewer.md's Slice 3,
// item 12), over the real viewer in headless Chromium the way file-print-browser.test.ts drives the document kinds.
// (5) A picture opened directly (file-view.ts imgBlock, `img.fileview-img`) kept the screen rule's `max-height: 82vh` on
// paper, under its box's 14px padding, its corners clipped by the radius; the print block now fits it to the page: under
// print media, emulated as file-view-print-browser.test.ts emulates it, the computed max-height is 100vh (the viewport's
// height under the emulation; the page area at print layout), the max-width 100%, the radius 0, no shadow, the box
// unpadded, and a tall picture is one A4 page; the screen values return under screen media; and the Print button prints
// the picture as a document, at once, since its one picture is complete. FAILS BEFORE: the max-height under print media
// read 574px, the screen's 82vh of a 700px viewport. Measured on the pane (styles.css) and the feed modal (feed.css).
// (6) A PDF (pdfBlock: an iframe at a blob URL) prints itself. The frame's window is read at the press (pdfFrameWindow):
// when it holds the PDF (in the full Chromium build the blob frame's document is the PDF viewer's, content type
// application/pdf, print a function the parent may call) the flow calls the frame's print, stubbed here on that window to
// record the call; when it does not, the kernel's /file URL opens in a new tab through window.open, stubbed on the page,
// and the line under the bar reads "Print from the tab that opened."; a tab the browser did not open (the stub answers
// null) is said in the line instead. The page's own window.print, stubbed too, never fires for a PDF. FAILS BEFORE: at
// Part A's viewer the press printed the page, one viewport of the frame, and the page's print recorded one call. Run over
// two launches: Playwright's default headless shell, which ships no PDF viewer (a probe on 2026-09-19 saw the frame's
// navigation become a download and its window stay at about:blank, print still a function there, headless Firefox the
// same), where the fallback is the natural path; and the full Chromium build (channel "chromium"), where the frame holds
// the document and prints it, and the fallback is forced by taking the frame window's print away and the blocked tab by
// the stub. A launch this box lacks is skipped with a note, the leg skipping loudly when neither launches (CI installs no
// browsers). Synthetic values only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, frames, requireCjs, REPORT, ROOT, SID, type Mode } from "./real-viewer-leg";
import { fileUrl } from "./preview";
import { TAB_WORDS, NO_TAB_WORDS } from "./file-print";

const SHORT = "# A short note\n\nOne paragraph, and that is all.\n";
const PNG = ROOT + "/docs/figure.png";
const PDF = ROOT + "/docs/paper.pdf";
const PNG_W = 400, PNG_H = 3000;              // a tall picture: taller than any page, so the fit is what keeps it to one
const PDF_BYTES = "%PDF-1.4\n1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >> endobj\ntrailer << /Root 1 0 R >>\n%%EOF\n";

type Bar = { present: boolean; phase: string | null; busy: boolean; line: string | null; lines: number; role: string | null; buttons: number; cardUp: boolean };
/** The page's stubs and probes: window.print and window.open record their calls; the bar and the print line are read. */
const PAGE_PROBES = () => {
  const w = window as any;
  w.__prints = []; w.__opens = []; w.__framePrints = []; w.__blockTab = false;
  w.print = () => { w.__prints.push({ frame: !!document.querySelector("#romp-fileview iframe.fileview-frame"), imgComplete: Array.from(document.querySelectorAll("#romp-fileview img")).every((i: any) => i.complete) }); };
  w.open = (url: unknown, target: unknown) => { w.__opens.push({ url: String(url), target: String(target) }); return w.__blockTab ? null : { opener: {} }; };
  w.__bar = (): Bar => {
    const b = document.querySelector("#romp-fileview .fileview-bar .fileview-print") as HTMLButtonElement | null;
    const lines = Array.from(document.querySelectorAll("#romp-fileview .fileview-print-line"));
    const line = lines[0] as HTMLElement | undefined;
    return { present: !!b, phase: b ? (b.dataset.print || null) : null, busy: !!b && b.classList.contains("fileview-busy"), line: line ? line.textContent : null, lines: lines.length,
      role: line ? line.getAttribute("role") : null, buttons: line ? line.querySelectorAll("button").length : 0, cardUp: !!document.getElementById("romp-fileview") };
  };
};
const bar = (page: any): Promise<Bar> => page.evaluate(() => (window as any).__bar());
const counts = (page: any): Promise<{ prints: number; opens: Array<{ url: string; target: string }>; framePrints: number }> =>
  page.evaluate(() => { const w = window as any; return { prints: w.__prints.length, opens: w.__opens, framePrints: w.__framePrints.length }; });
/** Click Print and, in the same task, read what fired before the handler returned. */
const clickPrint = (page: any): Promise<{ prints: number; opens: number; framePrints: number }> => page.evaluate(() => {
  (document.querySelector("#romp-fileview .fileview-print") as HTMLButtonElement).click();
  const w = window as any; return { prints: w.__prints.length, opens: w.__opens.length, framePrints: w.__framePrints.length };
});

/** Open a binary file through the harness (the scrollbar leg's idiom): the page's fetch answers the path with the blob, a
 *  PNG drawn on a canvas at PNG_W by PNG_H or the one-page PDF, under the kernel's Content-Type; the viewer's media branch
 *  paints the picture or the frame. */
async function openMedia(page: any, path: string, kind: "png" | "pdf"): Promise<void> {
  await page.evaluate(async ([p, sid, k, pdf, pw, ph]: [string, string, string, string, number, number]) => {
    const w = window as any; let blob: Blob;
    if (k === "png") { const c = document.createElement("canvas"); c.width = pw; c.height = ph; const g = c.getContext("2d")!; g.fillStyle = "#3a7bd5"; g.fillRect(0, 0, pw, ph); blob = await new Promise<Blob>((r) => c.toBlob((b) => r(b!), "image/png")); }
    else blob = new Blob([pdf], { type: "application/pdf" });
    const prev = w.fetch;
    w.fetch = async function (url: any, init: any) { const m = /[?&]path=([^&]*)/.exec(String(url)); if (m && decodeURIComponent(m[1]) === p) return new Response(blob, { status: 200, headers: { "Content-Type": k === "png" ? "image/png" : "application/pdf", "X-Romp-Mtime-Ns": w.__mtime } }); return prev(url, init); };
    w.FV.openFileView(p, sid, null);
  }, [path, SID, kind, PDF_BYTES, PNG_W, PNG_H]);
  if (kind === "png") await page.waitForFunction(() => { const i = document.querySelector("#romp-fileview img.fileview-img") as HTMLImageElement | null; return !!i && i.complete && i.naturalWidth > 0; }, null, { timeout: 10000 });
  else await page.waitForFunction(() => !!document.querySelector("#romp-fileview iframe.fileview-frame"), null, { timeout: 10000 });
  await frames(page, 3);
}
const pagesOf = (pdf: Buffer): number => (pdf.toString("latin1").match(/\/Type\s*\/Page(?![s\w])/g) || []).length;

// ── (5) the picture rule ───────────────────────────────────────────────────────────────────────────

type Pic = Record<string, any>;
function picFacts(): Pic {
  const img = document.querySelector("#romp-fileview img.fileview-img") as HTMLImageElement, box = img.closest(".fileview-imgbox") as HTMLElement, cs = getComputedStyle(img), r = img.getBoundingClientRect();   // closest: the Comments module wraps the picture in a span of its own (.fc-imgwrap)
  return { matchesPrint: matchMedia("print").matches, maxHeight: cs.maxHeight, maxWidth: cs.maxWidth, radius: cs.borderTopLeftRadius, shadow: cs.boxShadow, fit: cs.objectFit, boxPad: getComputedStyle(box).paddingTop,
    width: r.width, height: r.height, natural: [img.naturalWidth, img.naturalHeight], complete: img.complete, viewportH: innerHeight, boxClass: box.className };
}

test("case 5: a picture opened directly prints fitted to the page. Under print media img.fileview-img is capped at 100vh and 100% (FAILS BEFORE: the screen's 82vh, 574px at this viewport), square-cornered, unshadowed, in an unpadded box; a tall picture is one A4 page; the screen values return; Print prints it at once as a document", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const mode of ["pane", "feed"] as Mode[]) {
      const { page, errors } = await openViewer(browser, mode, 900, 700, { docs: { [REPORT]: SHORT }, before: async (pg: any) => { await pg.evaluate(PAGE_PROBES); } });
      await openMedia(page, PNG, "png");
      const s0 = await page.evaluate(picFacts);
      assert.equal(s0.matchesPrint, false);
      assert.equal(s0.boxClass, "fileview-imgbox", mode + ": the picture's box");
      assert.deepEqual(s0.natural, [PNG_W, PNG_H], mode + ": the tall picture decoded");
      assert.equal(s0.viewportH, 700);
      assert.equal(s0.maxHeight, "574px", mode + ": on screen the picture is capped at 82vh of the 700px viewport");
      assert.ok(Math.abs(s0.height - 574) < 1, mode + ": ...and stands at that cap (" + s0.height + ")");
      assert.equal(s0.boxPad, "14px", mode + ": the box's screen padding"); assert.equal(s0.radius, "8px", mode + ": the screen radius"); assert.notEqual(s0.shadow, "none", mode + ": the screen shadow");
      await page.emulateMedia({ media: "print" }); await frames(page, 2);
      const pr = await page.evaluate(picFacts);
      assert.equal(pr.matchesPrint, true);
      assert.equal(pr.maxHeight, "700px", mode + ": FAILS BEFORE: under print media the cap is the page's height, 100vh of the emulated viewport (the screen's 82vh read 574px here)");
      assert.equal(pr.maxWidth, "100%", mode + ": ...and the page's width");
      assert.equal(pr.radius, "0px", mode + ": square corners on paper (the radius clipped the picture's corners)");
      assert.equal(pr.shadow, "none", mode + ": no shadow on paper");
      assert.equal(pr.boxPad, "0px", mode + ": the box is unpadded, so the picture at 100vh does not push past the page");
      assert.equal(pr.fit, "contain", mode + ": object-fit stands");
      assert.ok(Math.abs(pr.height - 700) < 1, mode + ": the tall picture stands at the page's height (" + pr.height + ")");
      assert.ok(Math.abs(pr.width / pr.height - PNG_W / PNG_H) < 0.01, mode + ": the ratio is kept (" + pr.width + " by " + pr.height + ")");
      const pages = pagesOf(await page.pdf({ format: "A4", printBackground: true }));
      assert.equal(pages, 1, mode + ": the tall picture prints on one A4 page (" + pages + ")");
      await page.emulateMedia({ media: "screen" }); await frames(page, 2);
      const s1 = await page.evaluate(picFacts);
      assert.equal(s1.maxHeight, "574px", mode + ": the screen cap is back"); assert.equal(s1.boxPad, "14px"); assert.equal(s1.radius, "8px");
      // the flow: a picture is a document whose one picture is complete, so one click prints at once, with no line
      const fired = await clickPrint(page);
      assert.equal(fired.prints, 1, mode + ": one click printed the page at once, before the handler returned");
      assert.equal(fired.opens, 0); assert.equal(fired.framePrints, 0);
      const c = await counts(page);
      assert.equal(c.prints, 1);
      const b = await bar(page);
      assert.equal(b.present, true); assert.equal(b.phase, null, mode + ": the bar rests"); assert.equal(b.line, null, mode + ": no line");
      assert.deepEqual(errors, [], mode + ": no script error");
      await page.close();
    }
  });
});

// ── (6) the PDF ────────────────────────────────────────────────────────────────────────────────────

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }
type Variant = "shell" | "chromium";
/** Run `body` in each launch this box has: Playwright's default headless shell and the full Chromium build (channel
 *  "chromium"); a launch that fails is noted and skipped, and the test skips loudly when neither launches. */
async function inBrowsers(t: any, body: (browser: any, variant: Variant) => Promise<void>): Promise<void> {
  if (!pw) { t.skip("playwright is not installed under vscode-extension; the browser leg needs it (CI installs no browsers)"); return; }
  let ran = 0;
  for (const [variant, launch] of [["shell", () => pw.chromium.launch()], ["chromium", () => pw.chromium.launch({ channel: "chromium" })]] as Array<[Variant, () => Promise<any>]>) {
    let browser: any;
    try { browser = await launch(); }
    catch (e) { t.diagnostic(variant + ": no such browser on this box (CI installs none): " + String((e as Error).message).split("\n")[0]); continue; }
    try { await body(browser, variant); ran++; } finally { await browser.close(); }
  }
  if (ran === 0) t.skip("no playwright browser on this box; the browser leg needs one (CI installs none)");
}

type FrameFacts = { present: boolean; holds: boolean; src: string | null; href: string | null; type: string | null; printType: string | null; err: string | null };
const frameFacts = (page: any): Promise<FrameFacts> => page.evaluate(() => {
  const f = document.querySelector("#romp-fileview iframe.fileview-frame") as HTMLIFrameElement | null;
  if (!f) return { present: false, holds: false, src: null, href: null, type: null, printType: null, err: null };
  try { const w = f.contentWindow as any; return { present: true, holds: w.document.contentType === "application/pdf", src: f.src, href: w.location.href, type: w.document.contentType, printType: typeof w.print, err: null }; }
  catch (e) { return { present: true, holds: false, src: f.src, href: null, type: null, printType: null, err: String(e) }; }
});
/** Stub the frame window's print to record its calls (the parent may set it on a same-origin blob frame). */
const stubFramePrint = (page: any): Promise<string> => page.evaluate(() => {
  const f = document.querySelector("#romp-fileview iframe.fileview-frame") as HTMLIFrameElement; const w = f.contentWindow as any;
  w.print = () => { (window as any).__framePrints.push({ href: w.location.href, type: w.document.contentType }); };
  return typeof w.print;
});
const unprintableFrame = (page: any): Promise<string> => page.evaluate(() => {
  const w = (document.querySelector("#romp-fileview iframe.fileview-frame") as HTMLIFrameElement).contentWindow as any; w.print = undefined; return typeof w.print;
});
const setBlock = (page: any, on: boolean): Promise<void> => page.evaluate((b: boolean) => { (window as any).__blockTab = b; }, on);
const bare = (u: string): string => u.replace(/#.*$/, "");
const TAB = { url: fileUrl(PDF, SID), target: "_blank" };

/** The fallback: the /file URL in a new tab and the line saying so; then the browser blocking the tab; then a tab again. */
async function fallbackCases(page: any, label: string, before: { prints: number; opens: number; framePrints: number }): Promise<void> {
  let fired = await clickPrint(page);
  assert.equal(fired.prints, before.prints, label + ": FAILS BEFORE: the page's own print does not fire for a PDF (Part A printed the page, one viewport of the frame)");
  assert.equal(fired.framePrints, before.framePrints, label + ": the frame's print is not called when the frame does not hold the PDF or cannot print");
  assert.equal(fired.opens, before.opens + 1, label + ": one tab opened, inside the click's own task (a popup blocker passes it there)");
  let c = await counts(page);
  assert.deepEqual(c.opens[c.opens.length - 1], TAB, label + ": the kernel's /file URL in a new tab, the modified click's opener");
  let b = await bar(page);
  assert.equal(b.line, TAB_WORDS, label + ": the line says to print from the tab");
  assert.equal(b.lines, 1); assert.equal(b.buttons, 0, label + ": a notice, no buttons"); assert.equal(b.role, "status");
  assert.equal(b.phase, null, label + ": the bar rests under the notice"); assert.equal(b.busy, false);
  // the browser blocks the tab: the line says so, in place of the last one
  await setBlock(page, true);
  fired = await clickPrint(page);
  assert.equal(fired.opens, before.opens + 2, label + ": the tab was tried again");
  assert.equal(fired.prints, before.prints);
  b = await bar(page);
  assert.equal(b.line, NO_TAB_WORDS, label + ": the blocked tab is said"); assert.equal(b.lines, 1, label + ": one line at a time: the press dropped the last notice");
  await setBlock(page, false);
  fired = await clickPrint(page);
  assert.equal(fired.opens, before.opens + 3);
  b = await bar(page);
  assert.equal(b.line, TAB_WORDS); assert.equal(b.lines, 1); assert.equal(b.cardUp, true, label + ": the viewer stays up");
  c = await counts(page);
  assert.equal(c.prints, before.prints, label + ": the page's print never fired");
  assert.equal(c.framePrints, before.framePrints);
}

test("case 6: a PDF prints itself. The frame's own print when the frame holds the PDF (the full Chromium build); else the /file URL opens in a new tab and the line says so, a blocked tab said instead (the headless shell, which ships no PDF viewer, takes this path of itself); the page's print never fires (FAILS BEFORE: it did)", { timeout: 180000 }, async (t) => {
  await inBrowsers(t, async (browser, variant) => {
    const downloads: string[] = [];
    const { page, errors } = await openViewer(browser, "pane", 900, 700, { docs: { [REPORT]: SHORT }, before: async (pg: any) => { pg.on("download", (d: any) => { downloads.push(d.suggestedFilename()); }); await pg.evaluate(PAGE_PROBES); } });
    await openMedia(page, PDF, "pdf");
    // the frame's document, once the browser has decided it: the PDF viewer's, or a download with the window left blank
    let facts = await frameFacts(page);
    for (let i = 0; i < 50 && !facts.holds && downloads.length === 0; i++) { await new Promise((r) => setTimeout(r, 100)); facts = await frameFacts(page); }
    assert.equal(facts.present, true, variant + ": the frame is in the body");
    assert.equal(facts.err, null, variant + ": the blob frame's window is same-origin: reachable");
    assert.equal(facts.printType, "function", variant + ": print is a function on the frame's window whether or not it holds the PDF (" + facts.href + ")");
    assert.ok(facts.src && facts.src.startsWith("blob:"), variant + ": the frame is aimed at the blob URL");
    assert.equal((await bar(page)).present, true, variant + ": the Print button is in the bar over a PDF");
    if (variant === "chromium") assert.equal(facts.holds, true, variant + ": the full build's PDF viewer holds the document in the frame (type " + facts.type + ", at " + facts.href + "); without it the frame-print path is untested");
    if (facts.holds) {
      t.diagnostic(variant + ": the PDF viewer holds the document in the frame (type " + facts.type + ", at " + facts.href + "); the frame-print path is measured");
      assert.equal(bare(facts.href!), bare(facts.src!), variant + ": the frame's window is at the frame's own URL");
      assert.equal(await stubFramePrint(page), "function");
      const fired = await clickPrint(page);
      assert.equal(fired.framePrints, 1, variant + ": the frame's print was called once, inside the click's own task");
      assert.equal(fired.prints, 0, variant + ": FAILS BEFORE: the page's print did not fire (Part A printed the page, one viewport of the frame)");
      assert.equal(fired.opens, 0, variant + ": no tab: the frame printed the document");
      const b = await bar(page);
      assert.equal(b.phase, null, variant + ": the bar rests"); assert.equal(b.line, null, variant + ": no line: nothing to say");
      // the frame's print taken away: the tab is the way, and the line says so
      assert.equal(await unprintableFrame(page), "undefined");
      await fallbackCases(page, variant + " (print taken from the frame's window)", { prints: 0, opens: 0, framePrints: 1 });
    } else {
      t.diagnostic(variant + ": no PDF viewer in this launch: the frame's navigation became a download (" + downloads.join(", ") + ") and the window is at " + facts.href + "; the natural fallback is measured");
      assert.equal(facts.href, "about:blank", variant + ": the frame's window never left about:blank");
      assert.ok(downloads.length >= 1, variant + ": the browser took the bytes as a download");
      assert.equal(await stubFramePrint(page), "function", variant + ": the blank window's print, stubbed, must not be called: it would print a blank page");
      await fallbackCases(page, variant + " (no PDF viewer)", { prints: 0, opens: 0, framePrints: 0 });
    }
    assert.deepEqual(errors, [], variant + ": no script error");
    await page.close();
  });
});

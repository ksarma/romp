// The reader's place in an SVG's SOURCE view, in headless Chromium over the REAL module (plans/markdown-viewer.md Slice 2;
// file-view.ts renderBody's svgSource branch; the Slice 2 review's third round). The Source view is a text view (the
// highlighted XML, codeBlock output, textShowing true), and the plan says every paint of a text view keeps the reader's
// place, but its paint read, recorded and seated nothing: a reload under the Source view left the numeric scrollTop over
// the re-laid rows (row 200 at the edge became row 173, 27 rows off, where a .txt file kept row 200), and the Comments
// panel's close moved the top row by a row (a pane drag and a text-size step held through the browser's own anchoring).
// The branch now reads the place, swaps, runs the hooks, records the XML as the text painted and seats, the Raw view's
// order; the media paint records no text. Two scenes in the Files pane at 900px, the reader on row 200 of a 400-row SVG:
// a reload inserting forty lines above keeps row 200 at the edge with scrollTop grown by them; the panel opened and
// closed keeps row 200 at its height after each. The leg opens the SVG itself (the shared page serves an .svg as an
// image, the kernel's Content-Type and no text header), clicks Source and waits for the rows. Legs await frames and paint
// counts, never a timer. Skips LOUDLY without a playwright browser, as the other legs do. Synthetic values only: an
// invented diagram, /repo/notes-api paths, the placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, pageHtml, openPanel, closePanel, frames, paintsReach, ROOT, SID, MT, MT2, ORIGIN } from "./real-viewer-leg";

const near = (a: number, b: number, what: string, tol = 1.5) => assert.ok(Math.abs(a - b) <= tol, `${what}: ${a} vs ${b}`);
const DIAGRAM = ROOT + "/docs/diagram.svg";
/** A 400-row diagram: one <svg> root, a <text> element per row (no blank lines, so the XML is one html block to the lexer). */
const ROW = (n: number) => `  <text id="r${n}" x="10" y="${20 * n}">Row ${n} of the diagram: lorem ipsum dolor sit amet</text>`;
const svgOf = (inserted: number) => '<svg xmlns="http://www.w3.org/2000/svg" width="600" height="8100">\n'
  + Array.from({ length: inserted }, (_, i) => `  <rect id="inserted${i + 1}" x="0" y="${i}" width="1" height="1"/>`).join("\n") + (inserted ? "\n" : "")
  + Array.from({ length: 400 }, (_, i) => ROW(i + 1)).join("\n") + "\n</svg>\n";

/** The first Raw row ending below the body's top edge: its text, its top and the body's scrollTop. */
const rowAtTop = (page: any) => page.evaluate(() => {
  const body = document.querySelector(".fileview-body")!; const br = body.getBoundingClientRect();
  for (const r of Array.from(body.querySelectorAll("code.hljs .fv-cl"))) { const rr = r.getBoundingClientRect(); if (rr.bottom > br.top + 0.5) return { text: (r.textContent || "").trim().slice(0, 40), top: Math.round((rr.top - br.top) * 10) / 10, scrollTop: body.scrollTop }; }
  return null;
});
/** Scroll so the Raw row whose text includes `text` has its top at the body's top edge. */
const rowToEdge = (page: any, text: string) => page.evaluate((t: string) => {
  const body = document.querySelector(".fileview-body")!;
  const row = Array.from(body.querySelectorAll("code.hljs .fv-cl")).find((r) => (r.textContent || "").includes(t))!;
  body.scrollTop += row.getBoundingClientRect().top - body.getBoundingClientRect().top;
}, text);

/** The Files pane at 900 by 600 with the diagram open in its Source view, row 200 at the body's top edge. */
async function openSource(browser: any): Promise<{ page: any; errors: string[] }> {
  const page = await browser.newPage({ viewport: { width: 900, height: 600 } });
  const errors: string[] = [];
  page.on("pageerror", (e: Error) => { errors.push(e.message); });
  const html = pageHtml("pane", { [DIAGRAM]: svgOf(0) }, MT);
  await page.route((u: URL) => u.href.startsWith(ORIGIN), (route: any) => route.fulfill({ status: 200, contentType: "text/html", body: html }));
  await page.goto(ORIGIN + "/");
  await page.evaluate(([p, sid]: [string, string]) => { (window as any).FV.openFileView(p, sid, null); }, [DIAGRAM, SID]);
  await page.locator("#romp-fileview .fileview-btn", { hasText: /^Source$/ }).waitFor({ state: "visible", timeout: 10000 });
  await page.locator("#romp-fileview .fileview-btn", { hasText: /^Source$/ }).click();
  await page.waitForFunction(() => document.querySelectorAll("code.hljs .fv-cl").length > 300, null, { timeout: 10000 });
  await frames(page, 2);
  await rowToEdge(page, 'id="r200"');
  await frames(page, 3);                                                     // the scroll-time read
  const row = (await rowAtTop(page))!;
  assert.ok(row.text.includes('id="r200"'), `the scene starts with row 200 at the edge (got ${JSON.stringify(row.text)})`);
  near(row.top, 0, "at the edge", 1);
  return { page, errors };
}

test("in a browser, the real module: the SVG Source view keeps the reader's row across a reload that inserts forty lines above it (before: the numeric scrollTop stood and row 173 came to the edge)", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openSource(browser);
    const before = (await rowAtTop(page))!;
    const paints: number = await page.evaluate(() => (window as any).__paints);
    await page.evaluate(([p, text, m]: [string, string, string]) => { (window as any).__docs[p] = text; (window as any).__mtime = m; (window as any).__seam.reload(); }, [DIAGRAM, svgOf(40), MT2]);
    await paintsReach(page, paints + 1);
    await frames(page, 2);
    const after = (await rowAtTop(page))!;
    assert.ok(after.text.includes('id="r200"'), `row 200 is still the top row (got ${JSON.stringify(after.text)}; before the fix: row 173, the numeric scrollTop over forty new rows)`);
    near(after.top, before.top, "at the same height");
    assert.ok(after.scrollTop > before.scrollTop + 500, `the body scrolled down by the inserted rows (${before.scrollTop} to ${after.scrollTop})`);
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});

test("in a browser, the real module: the SVG Source view keeps the reader's row across the Comments panel's open and close (before: the close left the numeric scrollTop over the wider rows and the top row moved by a row)", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openSource(browser);
    const before = (await rowAtTop(page))!;
    for (const step of ["open", "close"] as const) {
      const paints: number = await page.evaluate(() => (window as any).__paints);
      if (step === "open") await openPanel(page); else await closePanel(page);
      await paintsReach(page, paints + 1);
      await frames(page, 2);
      const now = (await rowAtTop(page))!;
      assert.ok(now.text.includes('id="r200"'), `${step}: row 200 is still the top row (got ${JSON.stringify(now.text)})`);
      near(now.top, before.top, `${step}: at the same height (before the fix the close moved the top row from 56 to 84)`, 2);
    }
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});

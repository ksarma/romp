// A fence's BLANK rows and the reader's place (Slice 3 of plans/markdown-viewer.md, review round 2; reader-place.ts). The
// viewer wraps every fence in per-line rows (code-block.ts), and a blank line's row is `<span class="cl"><span
// class="ct"></span></span>`: a row with no text. The reader's place read the code line at the body's top edge through the
// browser's hit test and a one-character Range, and seated a line by the Range around its first character, so a blank row
// broke the Rendered/Raw round trip twice over. Read: the hit on the empty `.ct` had no character to measure, the line was
// dropped, and the Raw seat fell to the block fraction, which lands elsewhere when the two views' blank rows differ in
// height (11px Rendered against 18px Raw). Seat: a Range around the empty row read back one zero-height rect at the row's
// BASELINE, 9px under its top, so the row was seated 9px high. And a text row was read at its glyph's top, 2px under the
// row's top, so the Raw seat left the row above it showing 2px at the edge and the way back kept THAT row: every code line
// right after a blank line came back 14px high (16 at 115 percent, 20 at 150), a blank row 16 to 17px high, walking
// further on each trip in some cells. Now a wrapped code element's line at the edge is read as the Raw rows are (the first
// row whose box ends below the edge, its box's top) and a line is seated by its row's top, so a blank row, a row after
// blank rows and a row the edge cuts inside the blank row above it all come back to the same pixel. Measured over the real
// bundle on the pane and the chat, at 100 and 150 percent. Skips loudly without a browser. Synthetic values only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as path from "node:path";
import { inBrowser, openViewer, frames, requireCjs, REPORT, UI, EXT, type Mode } from "./real-viewer-leg";

const F = "```";
const P = (i: number) => "Paragraph " + i + ": " + "lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor ".repeat(3).trim() + ".";
// rows: 1 comment, 2 def, 3 return, 4 BLANK, 5 y=, 6 BLANK, 7 BLANK, 8 z=, 9 print
const CODE = ["# a comment line", "def f(x):", "    return x  # spaces", "", "y = f(1)", "", "", "z = f(2)", "print(y, z)"];
const NOTE = ["# Report", "", "## Section two", "", ...Array.from({ length: 5 }, (_, i) => P(i + 1) + "\n"), F + "python", ...CODE, F, "", ...Array.from({ length: 60 }, (_, i) => P(i + 6) + "\n")].join("\n");

/** reader-place.ts as the page's window.RP, so a scene can read the place the viewer reads before it seats a switch. */
function bundleReaderPlace(): string {
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    stdin: { contents: 'export { readPlace } from "./reader-place";', resolveDir: UI, loader: "ts", sourcefile: "file-view-fence-blank-rows-browser.test.ts" },
    bundle: true, write: false, format: "iife", globalName: "RP", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent",
  });
  return r.outputFiles[0].text as string;
}

/** Row `k` (1-based) of the fence in the Rendered view: its top from the body's top edge, its height, the scrollTop. */
const rowTop = (page: any, k: number) => page.evaluate((i: number) => {
  const body = document.querySelector(".fileview-body")!; const br = body.getBoundingClientRect();
  const rows = Array.from(document.querySelectorAll(".fileview-md pre code > .cl")) as HTMLElement[]; const r = rows[i - 1].getBoundingClientRect();
  return { top: r.top - br.top, height: r.height, scrollTop: body.scrollTop };
}, k);
/** The place the viewer would read now: the kept line's text and its top from the body's top edge, or null for no line. */
const placeLine = (page: any) => page.evaluate((p: string) => {
  const body = document.querySelector(".fileview-body") as HTMLElement; const src = (window as any).__docs[p] as string;
  const place = (window as any).RP.readPlace(body, src);
  return place ? { line: place.line ? { text: src.slice(place.line.start, place.line.end), top: place.line.top } : null } : null;
}, REPORT);
/** The first Raw row whose box ends below the body's top edge: its text and its top. */
const rawEdgeRow = (page: any) => page.evaluate(() => {
  const body = document.querySelector(".fileview-body")!; const br = body.getBoundingClientRect();
  for (const r of Array.from(body.querySelectorAll("code.hljs .fv-cl")) as HTMLElement[]) { const rr = r.getBoundingClientRect(); if (rr.bottom > br.top + 0.5) return { text: r.textContent || "", top: rr.top - br.top }; }
  return null;
});
const click = async (page: any, label: string, until: string) => { await page.locator("#romp-fileview .fileview-btn", { hasText: new RegExp("^" + label + "$") }).click(); await page.waitForFunction((s: string) => !!document.querySelector(s), until, { timeout: 5000 }); await frames(page, 3); };

/** Each scene puts row `row`'s top `below` px under the body's top edge (0: at the edge), on a whole pixel, as a person's scroll
 *  leaves it; `kept` is the row the edge then lies in, the one both views keep. */
const SCENES: { row: number; below: number; kept: number; what: string }[] = [
  { row: 8, below: 0, kept: 8, what: "a text row after two blank rows" },
  { row: 4, below: 0, kept: 4, what: "a blank row" },
  { row: 6, below: 0, kept: 6, what: "a blank row before another blank row" },
  { row: 5, below: 0, kept: 5, what: "a text row after one blank row" },
  { row: 8, below: 6, kept: 7, what: "a text row with the edge inside the blank row above it" },
];

async function roundTrips(page: any, cell: string, errors: string[], scenes = SCENES): Promise<void> {
  for (const s of scenes) {
    const tag = `${cell}, row ${s.row} (${s.what})`;
    const g0 = await rowTop(page, s.row);
    await page.evaluate(([top, below]: [number, number]) => { const b = document.querySelector(".fileview-body")!; b.scrollTop = Math.round(b.scrollTop + top - below); }, [g0.top, s.below]); await frames(page, 3);
    const start = await rowTop(page, s.row), kept = await rowTop(page, s.kept);
    assert.ok(Math.abs(start.top - s.below) < 1, tag + `: the row starts ${s.below}px under the edge (${start.top})`);
    const p0 = await placeLine(page);   // the place the viewer reads before the switch, asserted after the trips: the drift first
    for (let trip = 1; trip <= 3; trip++) {
      await click(page, "Raw", ".fileview-body .fv-cl");
      const raw = (await rawEdgeRow(page))!;
      assert.equal(raw.text, CODE[s.kept - 1], tag + `: trip ${trip}, the Raw row at the edge is the kept row (before: the row above it)`);
      assert.ok(Math.abs(raw.top - kept.top) < 1, tag + `: trip ${trip}, the Raw row's top where the Rendered row's was (${raw.top} vs ${kept.top})`);
      await click(page, "Rendered", ".fileview-md pre code > .cl");
      const back = await rowTop(page, s.row);
      assert.equal(back.top, start.top, tag + `: trip ${trip} brings the row back to the same pixel (before: 14 to 17px high, walking on some trips; scrollTop ${back.scrollTop} vs ${start.scrollTop})`);
    }
    // the mechanism: the row the edge lies in, at its row's top (before: no line for a blank row, so the seat fell to the
    // block fraction; a text row at its glyph's top, 2px under the row's)
    assert.ok(p0 && p0.line, tag + ": the place keeps a line (before: a blank row read no line)");
    assert.equal(p0!.line!.text, CODE[s.kept - 1], tag + ": the kept line is the row's");
    assert.ok(Math.abs(p0!.line!.top - kept.top) < 0.01, tag + `: the kept line's top is the row's top (${p0!.line!.top} vs ${kept.top}; before: the glyph's, 2px under)`);
    assert.deepEqual(errors, [], tag + ": no script error");
  }
}

test("a blank fence row, a row after blank rows and a row the edge cuts above all come back to the same pixel after Rendered to Raw to Rendered, three trips, on pane 900, pane 380 and chat 900", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const rp = bundleReaderPlace();
    for (const [mode, width] of [["pane", 900], ["pane", 380], ["chat", 900]] as [Mode, number][]) {
      const { page, errors } = await openViewer(browser, mode, width, 600, { docs: { [REPORT]: NOTE } });
      await page.addScriptTag({ content: rp });
      await roundTrips(page, `${mode} ${width}px`, errors);
      await page.close();
    }
  });
});

test("the same at 150 percent on pane 900, where a blank row's height differs most between the views", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const rp = bundleReaderPlace();
    const { page, errors } = await openViewer(browser, "pane", 900, 600, { docs: { [REPORT]: NOTE } });
    await page.addScriptTag({ content: rp });
    for (let i = 0; i < 3; i++) await page.click('button[aria-label="Larger text"]');
    await page.waitForFunction(() => getComputedStyle(document.querySelector(".fileview-md")!).getPropertyValue("--fv-scale").trim() === "1.5", null, { timeout: 5000 }); await frames(page, 2);
    await roundTrips(page, "pane 900px at 150 percent", errors, SCENES.filter((s) => s.row === 8 || s.row === 4));
    await page.close();
  });
});

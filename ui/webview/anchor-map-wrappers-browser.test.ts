// The flattened walk over the REAL viewer and the REAL Comments panel in headless Chromium (plans/markdown-viewer.md,
// Slice 5: "pair blocks inside an unclosed HTML container"; acceptance: selections after the wrapper and details
// containers map). The synthetic fixtures anchor-map-fixtures/wrappers-plain.md and wrappers-2block.md are opened as file
// documents through real-viewer-leg.ts under the Files pane's sheet (900 px, the margin layout, and 380 px, the list
// layout) and under the chat modal's, and each passage after or inside a `<div align="center">` or a `<details><summary>`
// wrapper is selected with a REAL mouse drag over its first and last characters' boxes (the way the slice's probe made
// them): the panel's mouseup offers the Comment float, its click opens the composer on the passage (the quote is the source
// slice, Save is offered), and the same selection read through the anchor map's own export maps to the passage's indexOf
// offsets. Before this slice the probe recorded every one of these refused as "an HTML block" at the wrapper's offset, the
// composer offering Switch to Raw and no Save (the div's block took nine elements; the two-block fixture refused all four
// selections after its div). The block table is read off the real DOM too: the wrapper's block owns the wrapper (and its
// summary), renderedBlockWrappers names the wrapper, the nested paragraph owns its own <p>. The closed details is opened
// by a click on its summary first, so its hidden paragraph is laid out for the drag. Skips LOUDLY without a playwright
// browser (CI installs none), as the other browser legs do. Synthetic values only: an invented note, /repo/notes-api paths,
// the placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { inBrowser, openViewer, openPanel, frames, requireCjs, UI, REPORT, type Mode } from "./real-viewer-leg";

const PLAIN = fs.readFileSync(path.join(UI, "anchor-map-fixtures", "wrappers-plain.md"), "utf8");
const TWO = fs.readFileSync(path.join(UI, "anchor-map-fixtures", "wrappers-2block.md"), "utf8");

/** The anchor map's block-table reads and the selection map, bundled alone as window.__am for the assertions over the page's DOM
 *  (the panel maps and paints with its own copy inside the viewer's bundle; the answers are a function of the DOM and the source). */
function probeBundle(): string {
  const contents = 'import { mapRenderedSelection, sourceBlockSpans, renderedBlockIndex, renderedBlockElements, renderedBlockWrappers } from "./anchor-map";\n'
    + '(window as any).__am = { mapRenderedSelection, sourceBlockSpans, renderedBlockIndex, renderedBlockElements, renderedBlockWrappers };\n';
  const r = requireCjs("esbuild").buildSync({ stdin: { contents, resolveDir: UI, loader: "ts", sourcefile: "wrappers-probe.ts" },
    bundle: true, write: false, format: "iife", platform: "browser", target: "es2020", nodePaths: [path.join(process.cwd(), "node_modules")],
    external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent" });
  return r.outputFiles[0].text as string;
}

/** A passage to select: its first and last words (each inside one text node) and the source slice the quote must be. */
type Scene = { start: string; end: string; quote: string; reveal?: string };
const PLAIN_SCENES: Scene[] = [
  { start: "Centered", end: "inside the div.", quote: "Centered **bold** paragraph inside the div." },
  { start: "Paragraph after the div", end: "div wrapper.", quote: "Paragraph after the div wrapper." },
  { start: "Hidden paragraph", end: "inside details.", quote: "Hidden paragraph inside details.", reveal: "Click me" },
  { start: "Paragraph after the details", end: "the details.", quote: "Paragraph after the details." },
  { start: "Final paragraph", end: "here.", quote: "Final paragraph here." },
];
const TWO_SCENES: Scene[] = [
  { start: "Centered", end: "Title", quote: "Centered Title" },
  { start: "Tagline", end: "paragraph.", quote: "Tagline paragraph." },
  { start: "After the two-block", end: "div.", quote: "After the two-block div." },
  { start: "Final paragraph", end: "here.", quote: "Final paragraph here." },
];

type Points = { sx: number; sy: number; ex: number; ey: number; expected: string };
/** In the page: the boxes of the passage's first and last characters, the start's block scrolled into the body's middle first. */
function pointsFor(spec: { start: string; end: string }): Points {
  const md = document.querySelector(".fileview-md") as HTMLElement;
  const texts: Text[] = [];
  const w = document.createTreeWalker(md, NodeFilter.SHOW_TEXT);
  for (let t = w.nextNode(); t; t = w.nextNode()) texts.push(t as Text);
  const si = texts.findIndex((t) => t.data.includes(spec.start));
  if (si < 0) throw new Error("start not in the rendered text: " + spec.start);
  const sNode = texts[si], sOff = sNode.data.indexOf(spec.start);
  let eNode: Text | null = null, eOff = -1;
  for (let i = si; i < texts.length && !eNode; i++) { const j = texts[i].data.indexOf(spec.end, i === si ? sOff : 0); if (j >= 0) { eNode = texts[i]; eOff = j + spec.end.length; } }
  if (!eNode) throw new Error("end not in the rendered text after the start: " + spec.end);
  (sNode.parentElement as HTMLElement).scrollIntoView({ block: "center" });
  const rect = (n: Text, off: number) => { const r = document.createRange(); r.setStart(n, off); r.setEnd(n, off + 1); return r.getBoundingClientRect(); };
  const a = rect(sNode, sOff), b = rect(eNode, eOff - 1);
  const whole = document.createRange(); whole.setStart(sNode, sOff); whole.setEnd(eNode, eOff);
  return { sx: a.left + Math.min(1.5, a.width / 3), sy: a.top + a.height / 2, ex: b.right - Math.min(1.5, b.width / 3), ey: b.top + b.height / 2, expected: whole.toString() };
}
/** Select the passage with a real drag, wait for the float, and read the map's own answer for the live selection. */
async function drag(page: any, spec: Scene, src: string): Promise<{ selected: string; expected: string; map: any }> {
  await page.evaluate(() => { getSelection()!.removeAllRanges(); });
  const pts: Points = await page.evaluate(pointsFor, { start: spec.start, end: spec.end });
  await frames(page, 1);
  await page.mouse.move(pts.sx, pts.sy);
  await page.mouse.down();
  await page.mouse.move((pts.sx + pts.ex) / 2, (pts.sy + pts.ey) / 2, { steps: 3 });
  await page.mouse.move(pts.ex, pts.ey, { steps: 6 });
  await page.mouse.up();
  await frames(page, 1);
  const selected: string = await page.evaluate(() => String(getSelection()));
  const map = await page.evaluate((s: string) => JSON.parse(JSON.stringify((window as any).__am.mapRenderedSelection(getSelection(), document.querySelector(".fileview-md"), s))), src);
  return { selected, expected: pts.expected, map };
}
type Composer = { open: boolean; quote: string | null; refused: string | null; save: boolean | null; raw: boolean };
/** The composer as the panel shows it after the float's click. */
const composer = (page: any): Promise<Composer> => page.evaluate(() => {
  const box = document.querySelector(".fc-composer") as HTMLElement | null;
  if (!box || !document.contains(box) || box.getClientRects().length === 0) return { open: false, quote: null, refused: null, save: null, raw: false };
  const save = box.querySelector('[data-act="fcsave"]') as HTMLButtonElement | null;
  return { open: true, quote: box.querySelector(".fc-quote")?.textContent ?? null, refused: box.querySelector(".fc-refused")?.textContent ?? null, save: save ? !save.disabled : null, raw: !!box.querySelector('[data-act="fcraw"]') };
});
const norm = (s: string): string => s.replace(/\s+/g, "");

/** Every scene of a fixture on one page: drag, map, float, composer, Cancel. */
async function runScenes(page: any, what: string, src: string, scenes: Scene[]): Promise<void> {
  for (const sc of scenes) {
    const name = what + " " + JSON.stringify(sc.quote);
    if (sc.reveal) {
      // a real click on the summary's box opens the closed details, as a person opens it, so its paragraph is laid out for the drag
      const box: { x: number; y: number } = await page.evaluate((t: string) => {
        const s = Array.from(document.querySelectorAll(".fileview-md summary")).find((e) => (e.textContent || "").includes(t)) as HTMLElement;
        s.scrollIntoView({ block: "center" });
        const r = s.getBoundingClientRect();
        return { x: r.left + Math.min(12, r.width / 2), y: r.top + r.height / 2 };
      }, sc.reveal);
      await frames(page, 1);
      await page.mouse.click(box.x, box.y);
      await frames(page, 2);
      assert.equal(await page.evaluate((t: string) => { const s = Array.from(document.querySelectorAll(".fileview-md summary")).find((e) => (e.textContent || "").includes(t)) as HTMLElement; return (s.parentElement as HTMLDetailsElement).open; }, sc.reveal), true, name + ": the details opened on its summary's click");
    }
    const r = await drag(page, sc, src);
    assert.equal(norm(r.selected), norm(r.expected), name + ": the drag selected the passage");
    assert.equal(r.map.ok, true, name + ": maps: " + JSON.stringify(r.map));
    assert.deepEqual(r.map.range, { start: src.indexOf(sc.quote), end: src.indexOf(sc.quote) + sc.quote.length }, name + ": to its own offsets");
    assert.equal(r.map.quote, sc.quote, name + ": the quote is the source slice");
    await page.waitForFunction(() => { const f = document.querySelector(".fc-float") as HTMLElement | null; return !!f && !f.hidden; }, null, { timeout: 5000 });
    await page.click(".fc-float");
    await frames(page, 2);
    const c = await composer(page);
    assert.equal(c.open, true, name + ": the composer opens");
    assert.equal(c.refused, null, name + ": no refusal (before: an HTML block, with Switch to Raw)");
    assert.equal(c.raw, false, name + ": no Switch to Raw");
    assert.equal(c.quote, sc.quote.replace(/\s+/g, " ").trim(), name + ": the composer quotes the passage");
    assert.equal(c.save, true, name + ": Save is offered");
    await page.click('.fc-composer [data-act="fccancel"]');
    await frames(page, 2);
    assert.equal((await composer(page)).open, false, name + ": Cancel closes the box");
  }
}
type Table = { tags: string[]; owners: number[]; div: { els: string[]; wraps: string[] }; details: { els: string[]; wraps: string[] } | null; nested: number[]; blocks: number };
/** The block table over the page's own DOM: the top-level children with their blocks, the wrapper blocks' elements and wrappers, the nested paragraphs' blocks. */
function readTable(src: string): Table {
  const am = (window as any).__am;
  const md = document.querySelector(".fileview-md") as HTMLElement;
  const spans: Array<{ start: number; end: number }> = am.sourceBlockSpans(src);
  const blockAt = (head: string) => spans.findIndex((sp) => src.slice(sp.start, sp.end).startsWith(head));
  const show = (e: Element) => e.tagName + ":" + JSON.stringify((e.textContent || "").trim().split(/\s+/).slice(0, 3).join(" "));
  const read = (b: number) => ({ els: (am.renderedBlockElements(md, src, b) as Element[]).map(show), wraps: (am.renderedBlockWrappers(md, src, b) as Element[]).map((e) => e.tagName) });
  const kids = Array.from(md.children);
  const det = blockAt("<details>");
  return {
    tags: kids.map((k) => k.tagName), owners: kids.map((k) => am.renderedBlockIndex(md, src, k)),
    div: read(blockAt("<div align")), details: det >= 0 ? read(det) : null,
    nested: Array.from(md.querySelectorAll(":scope > div > p, :scope > details:not(.md-callout) > p, :scope > div > h1")).map((p) => am.renderedBlockIndex(md, src, p)),
    blocks: spans.length,
  };
}

test("in a browser, the real viewer and panel: on the Files pane at 900 and 380 px, a real drag over each passage after or inside the div and details wrappers maps to its offsets, offers the float, and opens the composer on the passage with Save (before: refused as an HTML block with Switch to Raw); the block table pairs the wrapper's block to the wrapper and the nested paragraph to its own <p>", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const probe = probeBundle();
    for (const width of [900, 380]) {
      const what = "pane " + width + "px";
      const { page, errors } = await openViewer(browser, "pane", width, 900, { docs: { [REPORT]: PLAIN } });
      await page.addScriptTag({ content: probe });
      await openPanel(page);
      const table: Table = await page.evaluate(readTable, PLAIN);
      assert.deepEqual(table.tags.slice(-4), ["DIV", "P", "DETAILS", "P"], what + ": the browser nests the markdown after each wrapper inside it");
      const spansOf = (head: string) => { const i = PLAIN.indexOf(head); return i; };
      assert.ok(spansOf("<div align") > 0 && spansOf("<details>") > 0);
      assert.deepEqual(table.div, { els: ['DIV:"Centered bold paragraph"'], wraps: ["DIV"] }, what + ": the div's block owns the div, a wrapper");
      assert.deepEqual(table.details, { els: ['DETAILS:"Click me Hidden"', 'SUMMARY:"Click me"'], wraps: ["DETAILS"] }, what + ": the details' block owns the details and its summary; the details is the wrapper");
      assert.equal(table.nested.length, 2, what + ": two nested paragraphs");
      assert.ok(table.nested.every((b) => b >= 0), what + ": each nested paragraph is its own block's: " + JSON.stringify(table.nested));
      assert.ok(table.owners.slice(-4).every((b) => b >= 0), what + ": the top-level children after the wrappers are blocks' own: " + JSON.stringify(table.owners));
      await runScenes(page, what, PLAIN, PLAIN_SCENES);
      assert.deepEqual(errors, [], what + ": no script error");
      await page.close();
    }
  });
});

test("in a browser, the real viewer and panel: the two-block div (a heading and a paragraph nested in it) on the Files pane: each nested block and the paragraphs after the div map, offer the float and open the composer with Save (before: all four refused as an HTML block)", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openViewer(browser, "pane", 900, 900, { docs: { [REPORT]: TWO } });
    await page.addScriptTag({ content: probeBundle() });
    await openPanel(page);
    const table: Table = await page.evaluate(readTable, TWO);
    assert.deepEqual(table.tags, ["H1", "P", "DIV", "P", "P"], "the div holds its heading and paragraph");
    assert.deepEqual(table.div, { els: ['DIV:"Centered Title Tagline"'], wraps: ["DIV"] });
    assert.deepEqual(table.nested.map((b) => b >= 0), [true, true], "the nested heading and paragraph are their own blocks': " + JSON.stringify(table.nested));
    await runScenes(page, "pane 900px two-block", TWO, TWO_SCENES);
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});

test("in a browser, the real viewer and panel: the same passages in the chat modal map, offer the float and open the composer with Save", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openViewer(browser, "chat" as Mode, 1000, 900, { docs: { [REPORT]: PLAIN } });
    await page.addScriptTag({ content: probeBundle() });
    await openPanel(page);
    const table: Table = await page.evaluate(readTable, PLAIN);
    assert.deepEqual(table.div, { els: ['DIV:"Centered bold paragraph"'], wraps: ["DIV"] }, "chat: the div's block owns the div");
    await runScenes(page, "chat modal", PLAIN, PLAIN_SCENES);
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});

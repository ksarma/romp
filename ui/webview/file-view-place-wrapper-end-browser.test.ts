// The reader's place under an html WRAPPER THAT ENCLOSES THE REST OF THE DOCUMENT, in headless Chromium over the REAL
// module (plans/markdown-viewer.md Slices 2 and 5; reader-place.ts readRendered and ownedElements; the Slice 2 review's
// fourth round, rewritten for Slice 5's flattened walk). An html block that opens a wrapper the browser nests the
// following markdown into (`<div align="center">`, `<details>` with a blank line after its summary) was paired, as the
// anchor map stood, to every top-level element after it, and the third round refused that pairing because the block's
// own source parses to one element where the map paired many. When the wrapper's closing tag is the document's last
// block, or is missing, nothing follows the wrapper at the top level: the map paired the block to exactly ONE element,
// the wrapper itself, whose box holds every swallowed paragraph, and the third round trusted any one-element pairing
// without the parse. So from a swallowed paragraph the place read was the wrapper's block, hundreds of pixels deep, and
// the seat mapped that depth as a fraction onto the wrapper's one Raw row: the Raw switch from paragraph 60 landed on
// the `<div align="center">` row with the passage 1395px below the viewport (paragraph 60 came back 42px off), and the
// Raw row of a swallowed paragraph switched to Rendered borrowed the wrapper's box and landed on paragraph 43. The fourth
// round parsed an html block paired to one element too, so the wrapper's pairing was refused from either side and the
// viewer seated nothing. Slice 5's flattened walk (anchor-map.ts: the tag scan over the block's raw, the open element's
// children taken into the block table) pairs the wrapper's block to the wrapper alone and every paragraph nested in it to
// its own element, and the reader's place descends into the wrapper (readRendered), so the round trip from a nested
// paragraph is exact both ways, while a Raw row of the wrapper's own still seats nothing (the owner's ruling 2: the
// block's source parses to one element whose text is not the nested paragraphs'). The scenes, Files pane 900px:
//   - a centred `<div>` closed as the document's last block, the same `<div>` never closed, and `<details open>` closed
//     at the end (the README changelog shape), paragraph 60 nested in each: the Raw switch lands on paragraph 60's own
//     row and the return puts it back where it was (before Slice 5: no scrollTop written, the browser's own landing);
//   - the Raw row of nested paragraph 60 switched to Rendered seats paragraph 60's own element at the row's depth,
//     scaled by the paragraph's height over the row's (before Slice 5: nothing seated);
//   - the controls the widened rule must keep: a one-tag html block (`<p align="center">`), a paragraph that opens
//     with an inline tag (`<b>Note:</b> ...`) and one that opens with an autolink read as their own blocks, the Raw
//     switch landing on their own row and the return within 1.5px.
// Legs await frames, never a timer. Skips LOUDLY without a playwright browser, as the other legs do.
// Synthetic values only: an invented report, /repo/notes-api paths, the placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, frames, PARA, REPORT } from "./real-viewer-leg";

const near = (a: number, b: number, what: string, tol = 1.5) => assert.ok(Math.abs(a - b) <= tol, `${what}: ${a} vs ${b}`);
const paras = (a: number, b: number) => Array.from({ length: b - a + 1 }, (_, i) => PARA(a + i)).join("\n\n");
const WRAP_ROW = /^<\/?(div|details|summary)/;
/** The three wrapper shapes, each with paragraph 60 nested inside the wrapper and nothing after it at the top level. */
const SHAPES: Array<[string, string, string]> = [
  ["a centred div closed as the document's last block", "# Report\n\n" + paras(1, 40) + "\n\n<div align=\"center\">\n\n" + paras(41, 80) + "\n\n</div>\n", "div"],
  ["a centred div never closed", "# Report\n\n" + paras(1, 40) + "\n\n<div align=\"center\">\n\n" + paras(41, 80) + "\n", "div"],
  ["details closed at the document's end", "# Report\n\n" + paras(1, 10) + "\n\n<details open>\n<summary>Changelog</summary>\n\n" + paras(11, 90) + "\n\n</details>\n", "details"],
];

const click = async (page: any, label: string) => { await page.locator("#romp-fileview .fileview-btn", { hasText: new RegExp("^" + label + "$") }).click(); await frames(page, 3); };
/** The first Raw row ending below the body's top edge: its text, its top and the body's scrollTop; null when no Raw view shows. */
const rowAtTop = (page: any) => page.evaluate(() => {
  const body = document.querySelector(".fileview-body")!; const br = body.getBoundingClientRect();
  for (const r of Array.from(body.querySelectorAll("code.hljs .fv-cl"))) { const rr = r.getBoundingClientRect(); if (rr.bottom > br.top + 0.5) return { text: (r.textContent || "").trim().slice(0, 48), top: Math.round((rr.top - br.top) * 10) / 10, scrollTop: body.scrollTop }; }
  return null;
});
/** The box of the first element under the body matching `sel` whose text includes `text`, from the body's top edge. */
const box = (page: any, sel: string, text: string) => page.evaluate(([s, t]: [string, string]) => {
  const body = document.querySelector(".fileview-body")!; const br = body.getBoundingClientRect();
  const el = Array.from(body.querySelectorAll(s)).find((e) => (e.textContent || "").includes(t)); if (!el) return null;
  const r = el.getBoundingClientRect(); return { top: Math.round((r.top - br.top) * 10) / 10, bottom: Math.round((r.bottom - br.top) * 10) / 10, scrollTop: body.scrollTop, tag: el.tagName };
}, [sel, text]);
/** Scroll so that element's top sits `extra` px above the body's top edge. */
const scrollInto = (page: any, sel: string, text: string, extra = 0) => page.evaluate(([s, t, x]: [string, string, number]) => {
  const body = document.querySelector(".fileview-body")!;
  const el = Array.from(body.querySelectorAll(s)).find((e) => (e.textContent || "").includes(t))!;
  body.scrollTop += el.getBoundingClientRect().top - body.getBoundingClientRect().top + x;
}, [sel, text, extra]);
/** Scroll so the Raw row whose text includes `text` has its top `above` px above the body's top edge. */
const rowToEdge = (page: any, text: string, above = 0) => page.evaluate(([t, a]: [string, number]) => {
  const body = document.querySelector(".fileview-body")!;
  const row = Array.from(body.querySelectorAll("code.hljs .fv-cl")).find((r) => (r.textContent || "").includes(t))!;
  body.scrollTop += row.getBoundingClientRect().top - body.getBoundingClientRect().top + a;
}, [text, above]);
/** The wrapper as the browser built it: the last top-level element of the Rendered view, its tag, its element children,
 *  and whether paragraph 60 is nested inside it. */
const wrapperShape = (page: any) => page.evaluate(() => {
  const md = document.querySelector(".fileview-md")!; const kids = Array.from(md.children);
  const last = kids[kids.length - 1];
  const p60 = Array.from(md.querySelectorAll("p")).find((p) => (p.textContent || "").startsWith("Paragraph 60:"))!;
  return { topLevel: kids.length, lastTag: last.tagName.toLowerCase(), lastKids: last.children.length, nested: last.contains(p60) && p60.parentElement !== md };
});

test("in a browser, the real module: a wrapper that encloses the rest of the document (a centred div closed as the last block or never closed, details closed at the end) is paired to its one element and the paragraphs nested in it to their own (Slice 5's flattened walk; before it the one element held every paragraph after it, its pairing was refused and the Raw switch wrote no scrollTop; the third round trusted the one element and landed on the `<div align=\"center\">` row, the passage 1395px below): from nested paragraph 60 the Raw switch lands on paragraph 60's own row and the return puts it back where it was", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const [what, DOC, tag] of SHAPES) {
      const { page, errors } = await openViewer(browser, "pane", 900, 600, { docs: { [REPORT]: DOC } });
      const shape = await wrapperShape(page);
      assert.equal(shape.lastTag, tag, what + `: the fixture's last top-level element is the wrapper (got ${JSON.stringify(shape)})`);
      assert.ok(shape.nested && shape.lastKids >= 40, what + `: the wrapper holds the paragraphs after it, paragraph 60 among them (got ${JSON.stringify(shape)})`);
      await scrollInto(page, ".fileview-md p", "Paragraph 60:", 3); await frames(page, 2);
      const before = (await box(page, ".fileview-md p", "Paragraph 60:"))!;
      near(before.top, -3, what + ": the scene starts with paragraph 60 3px past the edge", 1);
      await click(page, "Raw");
      const row = (await rowAtTop(page))!;
      assert.ok(row, what + ": the Raw view painted");
      assert.ok(row.text.startsWith("Paragraph 60:"), what + `: the Raw top row is paragraph 60's own (got ${JSON.stringify(row.text)} at ${row.scrollTop} for ${before.scrollTop}; before Slice 5 the wrapper's one-element pairing was refused and the viewer wrote nothing, the browser's own landing; the third round wrote the wrapper's row at the depth's fraction)`);
      assert.ok(!WRAP_ROW.test(row.text), what + `: the Raw top row is not the wrapper's tag row (got ${JSON.stringify(row.text)})`);
      await click(page, "Rendered");
      const back = (await box(page, ".fileview-md p", "Paragraph 60:"))!;
      near(back.top, before.top, what + ": back in Rendered paragraph 60 is where it was (the third round: 42px off; before Slice 5: the browser's own landing)");
      assert.deepEqual(errors, [], what + ": no script error");
      await page.close();
    }
  });
});

test("in a browser, the real module: the Raw row of a paragraph nested in a wrapper that encloses the rest of the document, switched to Rendered, seats the paragraph's own element at the row's depth scaled by the paragraph's height over the row's (Slice 5's flattened walk; before it the paragraph's block had no element of its own and the block before it with one was the wrapper, refused, so nothing was seated; the third round borrowed the wrapper's box and landed on paragraph 43)", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const [what, DOC] of SHAPES) {
      const { page, errors } = await openViewer(browser, "pane", 900, 600, { docs: { [REPORT]: DOC }, raw: true });
      await rowToEdge(page, "Paragraph 60:", 3); await frames(page, 2);
      const row = (await rowAtTop(page))!;
      assert.ok(row.text.startsWith("Paragraph 60:"), what + `: the scene starts on paragraph 60's row (got ${JSON.stringify(row.text)})`);
      const rowBox = (await box(page, "code.hljs .fv-cl", "Paragraph 60:"))!;
      near(rowBox.top, -3, what + ": 3px above the edge", 1);
      await click(page, "Rendered");
      const back = (await box(page, ".fileview-md p", "Paragraph 60:"))!;
      // the depth as a fraction: 3px of the row's height becomes the same fraction of the paragraph's (reader-place.ts seatedTop)
      const want = rowBox.top * (back.bottom - back.top) / (rowBox.bottom - rowBox.top);
      near(back.top, want, what + `: paragraph 60's element seated at the row's depth (row ${rowBox.top} of ${rowBox.bottom - rowBox.top}px, paragraph ${back.bottom - back.top}px; before Slice 5 nothing was seated and the top block was the browser's own landing)`);
      assert.ok(back.top < 0 && back.bottom > 0, what + ": paragraph 60 straddles the edge");
      assert.deepEqual(errors, [], what + ": no script error");
      await page.close();
    }
  });
});

test("in a browser, the real module: the blocks the widened rule must keep read as their own: a one-tag html block, a paragraph opening with an inline tag and one opening with an autolink each land the Raw switch on their own row and return within 1.5px", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const CTRL: Array<[string, string, string, string]> = [
      ["a one-tag html block", "<p align=\"center\">Centered caption: one tag, its own block, long enough to wrap once in the pane.</p>", "Centered caption:", "P"],
      ["a paragraph opening with an inline tag", "<b>Note:</b> a paragraph that opens with an inline tag and runs on for a sentence or two more.", "Note:", "P"],
      ["a paragraph opening with an autolink", "<https://example.test/docs> starts this paragraph with an autolink and runs on for a sentence more.", "starts this paragraph", "P"],
    ];
    const DOC = "# Report\n\n" + paras(1, 40) + "\n\n" + CTRL.map((c) => c[1]).join("\n\n") + "\n\n" + paras(41, 80) + "\n";
    for (const [what, src, key, tag] of CTRL) {
      const { page, errors } = await openViewer(browser, "pane", 900, 600, { docs: { [REPORT]: DOC } });
      await scrollInto(page, ".fileview-md > *", key, 3); await frames(page, 2);
      const before = (await box(page, ".fileview-md > *", key))!;
      assert.equal(before.tag, tag, what + ": the fixture renders it as one top-level element of that tag");
      near(before.top, -3, what + ": the scene starts with the block 3px past the edge", 1);
      await click(page, "Raw");
      const row = (await rowAtTop(page))!;
      assert.ok(row.text.startsWith(src.slice(0, 20)), what + `: the Raw top row is the block's own (got ${JSON.stringify(row.text)})`);
      await click(page, "Rendered");
      const back = (await box(page, ".fileview-md > *", key))!;
      near(back.top, before.top, what + ": back in Rendered the block is where it was");
      assert.deepEqual(errors, [], what + ": no script error");
      await page.close();
    }
  });
});

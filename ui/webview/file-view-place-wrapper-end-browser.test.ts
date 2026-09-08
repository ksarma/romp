// The reader's place under an html WRAPPER THAT ENCLOSES THE REST OF THE DOCUMENT, in headless Chromium over the REAL
// module (plans/markdown-viewer.md Slice 2; reader-place.ts ownedElements; the Slice 2 review's fourth round). An html
// block that opens a wrapper the browser nests the following markdown into (`<div align="center">`, `<details>` with a
// blank line after its summary) is paired, as the anchor map stands, to every top-level element after it, and the third
// round refused that pairing because the block's own source parses to one element where the map paired many. When the
// wrapper's closing tag is the document's last block, or is missing, nothing follows the wrapper at the top level: the
// map pairs the block to exactly ONE element, the wrapper itself, whose box holds every swallowed paragraph, and the
// third round trusted any one-element pairing without the parse. So from a swallowed paragraph the place read was the
// wrapper's block, hundreds of pixels deep, and the seat mapped that depth as a fraction onto the wrapper's one Raw row:
// the Raw switch from paragraph 60 landed on the `<div align="center">` row with the passage 1395px below the viewport
// (paragraph 60 came back 42px off), and the Raw row of a swallowed paragraph switched to Rendered borrowed the
// wrapper's box and landed on paragraph 43. The rule now parses an html block paired to one element too, so the
// wrapper's pairing is refused from either side and the viewer seats nothing; where the body lands is the browser's
// own (the html leg's setter-trap idiom: a refusal is no scrollTop written by the viewer). The scenes, Files pane 900px:
//   - a centred `<div>` closed as the document's last block, the same `<div>` never closed, and `<details open>` closed
//     at the end (the README changelog shape), paragraph 60 nested in each: the Raw switch writes no scrollTop and the
//     top Raw row is not the wrapper's tag row; the return to Rendered puts a paragraph on top without error;
//   - the Raw row of nested paragraph 60 switched to Rendered writes no scrollTop;
//   - the controls the widened rule must keep: a one-tag html block (`<p align="center">`), a paragraph that opens
//     with an inline tag (`<b>Note:</b> ...`) and one that opens with an autolink read as their own blocks, the Raw
//     switch landing on their own row and the return within 1.5px.
// Legs await frames, never a timer. Skips LOUDLY without a playwright browser, as the other legs do.
// Synthetic values only: an invented report, /repo/notes-api paths, the placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, frames, topBlock, PARA, REPORT } from "./real-viewer-leg";

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
/** Trap every script write of the body's scrollTop from now on (the viewer's seat is one; the browser's own scrolls are not
 *  writes), so a switch can be shown to have seated nothing. Installed after the scene's own scroll. */
const trapWrites = (page: any) => page.evaluate(() => {
  const body = document.querySelector(".fileview-body") as HTMLElement;
  const proto = Object.getOwnPropertyDescriptor(Element.prototype, "scrollTop")!;
  (window as any).__writes = [];
  Object.defineProperty(body, "scrollTop", { get() { return proto.get!.call(this); }, set(v) { (window as any).__writes.push(v); proto.set!.call(this, v); }, configurable: true });
});
const writes = (page: any): Promise<number[]> => page.evaluate(() => (window as any).__writes as number[]);

test("in a browser, the real module: a wrapper that encloses the rest of the document (a centred div closed as the last block or never closed, details closed at the end) is paired to its one element, and that pairing is refused: from a nested paragraph the Raw switch writes no scrollTop and the top Raw row is not the wrapper's (the third round trusted the one element and landed on the `<div align=\"center\">` row, the passage 1395px below)", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const [what, DOC, tag] of SHAPES) {
      const { page, errors } = await openViewer(browser, "pane", 900, 600, { docs: { [REPORT]: DOC } });
      const shape = await wrapperShape(page);
      assert.equal(shape.lastTag, tag, what + `: the fixture's last top-level element is the wrapper (got ${JSON.stringify(shape)})`);
      assert.ok(shape.nested && shape.lastKids >= 40, what + `: the wrapper holds the paragraphs after it, paragraph 60 among them (got ${JSON.stringify(shape)})`);
      await scrollInto(page, ".fileview-md p", "Paragraph 60:", 3); await frames(page, 2);
      const before = (await box(page, ".fileview-md p", "Paragraph 60:"))!;
      near(before.top, -3, what + ": the scene starts with paragraph 60 3px past the edge", 1);
      await trapWrites(page);
      await click(page, "Raw");
      const row = (await rowAtTop(page))!;
      assert.ok(row, what + ": the Raw view painted");
      assert.deepEqual(await writes(page), [], what + `: the viewer wrote no scrollTop across the switch, the wrapper's one-element pairing refused (the Raw top row is ${JSON.stringify(row.text)} at ${row.scrollTop} for ${before.scrollTop}, the browser's own landing; the third round wrote the wrapper's row at the depth's fraction)`);
      assert.ok(!WRAP_ROW.test(row.text), what + `: the Raw top row is not the wrapper's tag row (got ${JSON.stringify(row.text)})`);
      await click(page, "Rendered");
      const back = (await topBlock(page))!;
      // the top-level element on top is a paragraph before the wrapper or the wrapper itself (its text opens with its first paragraph's, or the summary's)
      assert.ok(back && /^(Paragraph \d+:|Changelog)/.test(back.text), what + `: back in Rendered the view painted, a paragraph or the wrapper on top (got ${JSON.stringify(back && back.text)})`);
      assert.deepEqual(errors, [], what + ": no script error");
      await page.close();
    }
  });
});

test("in a browser, the real module: the Raw row of a paragraph nested in a wrapper that encloses the rest of the document, switched to Rendered, seats nothing: the paragraph's block has no element of its own and the block before it with one is the wrapper, whose pairing is refused (the third round borrowed the wrapper's box and landed on paragraph 43)", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const [what, DOC] of SHAPES) {
      const { page, errors } = await openViewer(browser, "pane", 900, 600, { docs: { [REPORT]: DOC }, raw: true });
      await rowToEdge(page, "Paragraph 60:", 3); await frames(page, 2);
      const row = (await rowAtTop(page))!;
      assert.ok(row.text.startsWith("Paragraph 60:"), what + `: the scene starts on paragraph 60's row (got ${JSON.stringify(row.text)})`);
      await trapWrites(page);
      await click(page, "Rendered");
      const back = (await topBlock(page))!;
      assert.deepEqual(await writes(page), [], what + `: the viewer wrote no scrollTop across the switch (the top block is ${JSON.stringify(back.text)} at ${back.scrollTop} for ${row.scrollTop}, the browser's own landing)`);
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

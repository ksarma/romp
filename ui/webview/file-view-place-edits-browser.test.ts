// The reader's place across a session's EDIT inside or around the kept block, and past an html wrapper, in headless
// Chromium over the REAL module (plans/markdown-viewer.md Slice 2; reader-place.ts; the Slice 2 review's second round).
// Each scene puts the reader somewhere the first round's rules lost them and reads where they land:
//   - an html block that opens a wrapper the browser nests the following markdown into (`<details>` with a blank line
//     after its summary, the same on one line, a centred `<div>` around a heading): the anchor map, as it stands,
//     pairs every later element to the wrapper's block, and the place read from paragraph 80 was the wrapper: the Raw
//     switch landed on `<summary>`, 3500px up. Now an element the wrapper swallowed reads as no place (the numeric
//     scrollTop stands), so the Raw view opens after the wrapper and the return lands after it too. Once the map pairs
//     the wrapper right (anchor-map.ts), the round trip is exact, and these assertions still hold;
//   - the Raw row at the edge, `return x + 50` of a 120-line code block: five lines inserted above it inside the block,
//     forty inserted, five deleted below it, and the row itself rewritten with its neighbours (the first round kept
//     the block's top edge or its loss in pixels, so line 45 stood at the edge after the insertion, and the inserted
//     line after forty);
//   - the same edits with line 50 at the edge of the Rendered code block, read through the browser's hit test; and the
//     Rendered, Raw, Rendered round trip on line 50, exact now (the first round: within three lines);
//   - the paragraph under the reader's eye deleted (30px in): the paragraph after it at the edge, whole (the first
//     round: its first line 30px above the edge, a depth into a block that was gone);
//   - paragraphs 39 to 41 deleted and twenty inserted above, with 40 at the edge: paragraph 42 at the edge (the first
//     round: the edit's start, Inserted 1 at the top of the document); the same three rewritten as one: the
//     replacement, at the edge.
// Legs await frames and paint counts, never a timer. Skips LOUDLY without a playwright browser, as the other legs do.
// Synthetic values only: an invented report, /repo/notes-api paths, the placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, frames, paintsReach, topBlock, putAtTop, PARA, REPORT, MT2 } from "./real-viewer-leg";

const near = (a: number, b: number, what: string, tol = 1.5) => assert.ok(Math.abs(a - b) <= tol, `${what}: ${a} vs ${b}`);
const paras = (a: number, b: number) => Array.from({ length: b - a + 1 }, (_, i) => PARA(a + i)).join("\n\n");
const INSERTED = Array.from({ length: 20 }, (_, i) => `Inserted ${i + 1}: new text a session wrote above the reader's place, long enough to wrap once or twice in a narrow pane.`).join("\n\n");
/** The report with block `n` replaced by `block` (null drops it), and, with `above`, twenty paragraphs inserted under the heading. */
const report = (replace: Record<number, string | null> = {}, above = false) => "# Report\n\n" + (above ? INSERTED + "\n\n" : "")
  + Array.from({ length: 100 }, (_, i) => (i + 1 in replace ? replace[i + 1] : PARA(i + 1))).filter((p) => p !== null).join("\n\n") + "\n";
/** A 120-line python block: line 1 a def, line i `    return x + i`. */
const LINES = Array.from({ length: 120 }, (_, i) => (i === 0 ? "def f1(x):  # line 1 of a long code block" : `    return x + ${i + 1}`));
const fence = (lines: string[]) => "```python\n" + lines.join("\n") + "\n```";
const withCode = (lines: string[]) => "# Report\n\n" + paras(1, 20) + "\n\n" + fence(lines) + "\n\n" + paras(21, 60) + "\n";
const insertAt = (line: number, n: number) => [...LINES.slice(0, line), ...Array.from({ length: n }, (_, i) => `    y${i} = ${i}  # inserted`), ...LINES.slice(line)];
const deleteAt = (line: number, n: number) => [...LINES.slice(0, line - 1), ...LINES.slice(line - 1 + n)];

const click = async (page: any, label: string) => { await page.locator("#romp-fileview .fileview-btn", { hasText: new RegExp("^" + label + "$") }).click(); await frames(page, 3); };
const reload = async (page: any, text: string) => {
  const paints: number = await page.evaluate(() => (window as any).__paints);
  await page.evaluate(([p, t, m]: [string, string, string]) => { (window as any).__docs[p] = t; (window as any).__mtime = m; (window as any).__seam.reload(); }, [REPORT, text, MT2]);
  await paintsReach(page, paints + 1);
  await frames(page, 2);
};
const scrollTopOf = (page: any): Promise<number> => page.evaluate(() => document.querySelector(".fileview-body")!.scrollTop);
/** The first Raw row ending below the body's top edge: its text, its top and the body's scrollTop. */
const rowAtTop = (page: any) => page.evaluate(() => {
  const body = document.querySelector(".fileview-body")!; const br = body.getBoundingClientRect();
  for (const r of Array.from(body.querySelectorAll("code.hljs .fv-cl"))) { const rr = r.getBoundingClientRect(); if (rr.bottom > br.top + 0.5) return { text: (r.textContent || "").trim().slice(0, 32), top: Math.round((rr.top - br.top) * 10) / 10, scrollTop: body.scrollTop }; }
  return null;
});
/** Scroll so the Raw row whose text includes `text` has its top at the body's top edge. */
const rowToEdge = (page: any, text: string) => page.evaluate((t: string) => {
  const body = document.querySelector(".fileview-body")!;
  const row = Array.from(body.querySelectorAll("code.hljs .fv-cl")).find((r) => (r.textContent || "").includes(t))!;
  body.scrollTop += row.getBoundingClientRect().top - body.getBoundingClientRect().top;
}, text);
/** The code line under the body's top edge in the Rendered code block, through the browser's own hit test, with the
 *  block's top and the scrollTop. */
const lineAtEdge = (page: any) => page.evaluate(() => {
  const body = document.querySelector(".fileview-body")!; const br = body.getBoundingClientRect();
  const pre = document.querySelector(".fileview-md > pre")!; const code = pre.querySelector("code")!; const cr = code.getBoundingClientRect();
  const r = (document as any).caretRangeFromPoint(cr.left + 2, br.top + 1);
  let acc = 0, off = -1;
  const walk = (n: Node): boolean => { if (n === r.startContainer) { off = acc + (n.nodeType === 3 ? r.startOffset : 0); return true; } if (n.nodeType === 3) { acc += (n as Text).data.length; return false; } for (const c of Array.from(n.childNodes)) if (walk(c)) return true; return false; };
  walk(code);
  const text = code.textContent || ""; const line = text.slice(0, off).split("\n").length - 1;
  return { line: line + 1, text: text.split("\n")[line].trim(), preTop: Math.round((pre.getBoundingClientRect().top - br.top) * 10) / 10, scrollTop: body.scrollTop };
});
/** Scroll so line `n` (1-based) of the Rendered code block starts 3px above the body's top edge. */
const codeLineToEdge = (page: any, n: number) => page.evaluate((k: number) => {
  const body = document.querySelector(".fileview-body")!; const code = document.querySelector(".fileview-md > pre code")!;
  const cr = code.getBoundingClientRect(); const lh = cr.height / 120;
  body.scrollTop += cr.top - body.getBoundingClientRect().top + (k - 1) * lh + 3;
}, n);

const WRAPPERS: Record<string, string> = {
  "details with a paragraph after its summary": "<details>\n<summary>More</summary>\n\nHidden details text here.\n\n</details>",
  "details with the summary on its line": "<details><summary>More</summary>\n\nHidden details text here.\n\n</details>",
  "a centred div around a heading and a tagline": "<div align=\"center\">\n\n# Project\n\nA tagline sentence.\n\n</div>",
};

test("in a browser, the real module: from paragraph 80 below an html wrapper the browser nests markdown into, the Raw switch lands after the wrapper and the return lands after it too; the same document without the wrapper round-trips exactly", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const [shape, html] of Object.entries(WRAPPERS)) {
      const DOC = "# Report\n\n" + paras(1, 4) + "\n\n" + html + "\n\n" + paras(5, 100) + "\n";
      const { page, errors } = await openViewer(browser, "pane", 900, 600, { docs: { [REPORT]: DOC } });
      const nested = await page.evaluate(() => { const w = document.querySelector(".fileview-md > details, .fileview-md > div[align]")!; return { tag: w.tagName, kids: w.children.length, hasP: !!w.querySelector("p, h1") }; });
      assert.equal(nested.kids, 2, shape + ": the fixture: the browser nests the inner block inside the wrapper (" + JSON.stringify(nested) + ")");
      await putAtTop(page, "Paragraph 80:"); await frames(page, 2);
      const before = (await topBlock(page))!;
      assert.equal(before.text, "Paragraph 80:");
      await click(page, "Raw");
      const row = (await rowAtTop(page))!;
      const wrapperRow = /^<(details|summary|div|\/details|\/div)|^# Project|^A tagline|^Hidden details/.test(row.text);
      assert.ok(!wrapperRow, shape + `: the Raw top row is not the wrapper's (got ${JSON.stringify(row.text)} at scrollTop ${row.scrollTop}: the first round landed on the wrapper, 3500px up)`);
      const m = /^Paragraph (\d+):/.exec(row.text);
      assert.ok(m && Number(m[1]) >= 5, shape + `: the Raw top row is a paragraph after the wrapper (got ${JSON.stringify(row.text)})`);
      await click(page, "Rendered");
      const back = (await topBlock(page))!;
      const mb = /^Paragraph (\d+):/.exec(back.text);
      assert.ok(mb && Number(mb[1]) >= 5, shape + `: back in Rendered, a paragraph after the wrapper (got ${JSON.stringify(back.text)})`);
      assert.deepEqual(errors, [], shape + ": no script error");
      await page.close();
    }
    // the control: the same report with a plain paragraph in the wrapper's place round-trips exactly
    const { page, errors } = await openViewer(browser, "pane", 900, 600, { docs: { [REPORT]: "# Report\n\n" + paras(1, 4) + "\n\nA plain paragraph where the wrapper was.\n\n" + paras(5, 100) + "\n" } });
    await putAtTop(page, "Paragraph 80:"); await frames(page, 2);
    const before = (await topBlock(page))!;
    await click(page, "Raw");
    assert.match((await rowAtTop(page))!.text, /^Paragraph 80:/, "control: paragraph 80's row on top");
    await click(page, "Rendered");
    const back = (await topBlock(page))!;
    assert.equal(back.text, "Paragraph 80:", "control: paragraph 80 back on top");
    near(back.top, before.top, "control: at the same height");
    assert.deepEqual(errors, [], "control: no script error");
    await page.close();
  });
});

test("in a browser, the real module, Raw: the row at the edge stays the row at the edge through a reload that inserts five or forty lines above it inside the block, deletes five below it, or rewrites the lines around it (the first round: the block's top edge held, and line 45 stood at the edge)", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const edits: [string, string[], RegExp][] = [
      ["five lines inserted at line 10, above the row", insertAt(10, 5), /^return x \+ 50$/],
      ["forty lines inserted at line 10, above the row", insertAt(10, 40), /^return x \+ 50$/],
      ["five lines deleted at line 60, below the row", deleteAt(60, 5), /^return x \+ 50$/],
      ["lines 48 to 52 rewritten as two", [...LINES.slice(0, 47), "    z = 1  # rewritten", "    z = 2  # rewritten", ...LINES.slice(52)], /^z = 1 {2}# rewritten$/],
    ];
    for (const [edit, lines, want] of edits) {
      const { page, errors } = await openViewer(browser, "pane", 900, 600, { docs: { [REPORT]: withCode(LINES) }, raw: true });
      await rowToEdge(page, "return x + 50"); await frames(page, 2);
      const before = (await rowAtTop(page))!;
      assert.equal(before.text, "return x + 50", edit + ": the scene starts with line 50's row at the edge");
      near(before.top, 0, edit + ": at the edge", 1);
      await reload(page, withCode(lines));
      const after = (await rowAtTop(page))!;
      assert.match(after.text, want, edit + `: the row at the edge (got ${JSON.stringify(after.text)}; the first round: ${edit.startsWith("five lines inserted") ? "return x + 45" : edit.startsWith("forty") ? "the inserted line y39" : edit.startsWith("five lines deleted") ? "return x + 45" : "return x + 46"})`);
      near(after.top, before.top, edit + ": at the same height", 1);
      assert.deepEqual(errors, [], edit + ": no script error");
      await page.close();
    }
  });
});

test("in a browser, the real module, Rendered: line 50 at the edge of the code block stays line 50 through a reload that inserts five lines above it or deletes five below it; the Rendered, Raw, Rendered round trip on line 50 is exact; the lines around it rewritten seat the first replacement line", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const edits: [string, string[], string][] = [
      ["five lines inserted at line 10, above the line", insertAt(10, 5), "return x + 50"],
      ["five lines deleted at line 60, below the line", deleteAt(60, 5), "return x + 50"],
      ["lines 48 to 52 rewritten as two", [...LINES.slice(0, 47), "z = 1  # rewritten", "z = 2  # rewritten", ...LINES.slice(52)], "z = 1  # rewritten"],
    ];
    for (const [edit, lines, want] of edits) {
      const { page, errors } = await openViewer(browser, "pane", 900, 600, { docs: { [REPORT]: withCode(LINES) } });
      await codeLineToEdge(page, 50); await frames(page, 2);
      const before = await lineAtEdge(page);
      assert.equal(before.text, "return x + 50", edit + ": the scene starts with line 50 at the edge");
      await reload(page, withCode(lines));
      const after = await lineAtEdge(page);
      assert.equal(after.text, want, edit + `: the line at the edge (the first round: the block's top held at ${before.preTop}, and line 45 stood at the edge)`);
      assert.deepEqual(errors, [], edit + ": no script error");
      await page.close();
    }
    // the round trip: line 50 exactly, both ways
    const { page, errors } = await openViewer(browser, "pane", 900, 600, { docs: { [REPORT]: withCode(LINES) } });
    await codeLineToEdge(page, 50); await frames(page, 2);
    const before = await lineAtEdge(page);
    assert.equal(before.text, "return x + 50");
    await click(page, "Raw");
    const row = (await rowAtTop(page))!;
    assert.equal(row.text, "return x + 50", "Raw: line 50's row on top (the first round: within three lines)");
    await click(page, "Rendered");
    const back = await lineAtEdge(page);
    assert.equal(back.text, "return x + 50", "back in Rendered: line 50 at the edge");
    near(back.preTop, before.preTop, "the block where it was", 2);
    assert.deepEqual(errors, [], "round trip: no script error");
    await page.close();
  });
});

test("in a browser, the real module: the paragraph under the reader's eye deleted seats the paragraph after it at the edge, whole; paragraphs 39 to 41 deleted with twenty inserted above seat paragraph 42 at the edge; the same three rewritten as one seat the replacement", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    // 30px into paragraph 40, then paragraph 40 deleted
    let { page, errors } = await openViewer(browser, "pane", 900, 600);
    await putAtTop(page, "Paragraph 40:"); await page.evaluate(() => { document.querySelector(".fileview-body")!.scrollTop += 30; }); await frames(page, 2);
    const p40 = (await topBlock(page))!;
    assert.equal(p40.text, "Paragraph 40:"); near(p40.top, -30, "the scene starts 30px into paragraph 40", 1);
    await reload(page, report({ 40: null }));
    const p41 = (await topBlock(page))!;
    assert.equal(p41.text, "Paragraph 41:", "paragraph 41 is the top block");
    near(p41.top, 0, "at the edge, whole (the first round: 30px above it, the reader's depth into a paragraph that was gone)", 1);
    assert.deepEqual(errors, [], "deleted: no script error");
    await page.close();
    // paragraphs 39 to 41 deleted, twenty inserted above
    ({ page, errors } = await openViewer(browser, "pane", 900, 600));
    await putAtTop(page, "Paragraph 40:"); await frames(page, 2);
    const b0 = (await topBlock(page))!;
    await reload(page, report({ 39: null, 40: null, 41: null }, true));
    const a0 = (await topBlock(page))!;
    assert.equal(a0.text, "Paragraph 42:", "paragraph 42 on top (the first round: Inserted 1, the document's top)");
    near(a0.top, b0.top, "at the edge, where paragraph 40 was", 1);
    assert.ok((await scrollTopOf(page)) > 1000, "the body is far from the top");
    assert.deepEqual(errors, [], "three deleted: no script error");
    await page.close();
    // the same three rewritten as one, twenty inserted above
    ({ page, errors } = await openViewer(browser, "pane", 900, 600));
    await putAtTop(page, "Paragraph 40:"); await frames(page, 2);
    const b1 = (await topBlock(page))!;
    await reload(page, report({ 39: "Rewritten 39 to 41: the session folded three paragraphs into this one.", 40: null, 41: null }, true));
    const a1 = (await topBlock(page))!;
    assert.equal(a1.text, "Rewritten 39 t", "the replacement on top");
    near(a1.top, b1.top, "where paragraph 40 was", 1);
    assert.deepEqual(errors, [], "three rewritten: no script error");
    await page.close();
  });
});

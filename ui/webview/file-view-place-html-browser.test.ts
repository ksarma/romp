// The reader's place around HTML BLOCKS, in headless Chromium over the REAL module (plans/markdown-viewer.md Slice 2;
// reader-place.ts ownedElements and codeOf; the Slice 2 review's third round). An html block of sibling tags is the one
// block that renders as several elements, and the anchor map's pairing across one is a resync on the blocks after it,
// which the map as it stands gets wrong for a wrapper the browser nests later markdown into and for two adjacent html
// blocks. The second round told a block's own element from a swallowed one by decoding the block's source by hand and
// looking for the element's text in it; the third round replaced that with a trusted pairing (the block's own source,
// parsed by DOMParser, yields as many elements with the same text) and refused every pairing the parse does not confirm.
// The scenes, each in the Files pane at 900px:
//   - a two-tag block whose first tag hangs on an entity past U+10FFFF (decimal, hex, a 100,003-character entity): the
//     round-2 decoder threw a RangeError inside the Raw click and the text-size step, so the view stayed Rendered and the
//     size was stored but never painted (2 page errors); now the Raw switch lands on the tag's own row and returns to it,
//     and A+ paints;
//   - a two-tag block whose first tag carries inline tags, a line break, the README badge-and-tagline pair, named
//     entities beyond the six the decoder knew, an entity with no semicolon: round 2 read the tag as swallowed and kept
//     the numeric scrollTop (the Raw view opened on paragraph 28, the return on paragraph 28 again); now the tag's own
//     row and the return to the tag;
//   - a textless element inside a wrapper's swallowed run (a picture the reader is 100px into, a rule at the edge):
//     round 2 took a textless element for the wrapper's own and read the run's union box, so the Raw switch jumped
//     1750px up to `<details>`; now the run's pairing is refused from any element, the viewer seats nothing, and a
//     paragraph is on top both ways;
//   - a Raw row of the wrapper's own (`<summary>`) switched to Rendered: round 2 seated the whole swallowed run at the
//     row's fraction (paragraph 74 at scrollTop 3585 for 360); now no seat;
//   - two html blocks a blank line apart: the map pairs the first to nothing and the second to both elements; round 2
//     read the second element as its block and put the Raw view one row off; now neither element is a place and the
//     Raw click seats nothing (the anchor-map half is Slice 5's);
//   - an html `<pre>` of forty lines with the Raw row `html line 10` near the edge: round 2's line rule mapped the row to
//     the code's line of the same index, one off (the block's first line is the tag), and seated line 11 at the edge;
//     the block keeps the depth rule now, line 10 at the edge within a line, where a markdown code block stays exact;
//   - a Rendered code block of long lines in a 380px pane, the reader partway into line 50's wrapped rows: round 2
//     recorded the hit row's top and seated the line's first character there, so the first pane drag moved the passage
//     by a wrapped row (the first character from -20.4 to -2.1); now the first character's top is what is kept, and the
//     drag to 900px and back holds it within 2px. Two passes over the same drags: with the sheets' default overflow-anchor
//     Chromium's own anchoring lands the character within 0.2px, so the seat's delta is under its half-pixel threshold
//     and the viewer writes nothing (the base commit, with no seat, is green here); that pass pins the POINT the seat
//     computes, since a wrong rule seats another point over the browser's landing (round 2's row top, -2.1; the block's
//     fraction, +0.95). With anchoring off (a test-only style on the body) only the viewer's seat can hold the
//     character; that pass pins the seat's PRESENCE (the base keeps the numeric scrollTop, clamped to 4787 at 900px,
//     and the character goes to -2502, then +922 back at 380).
// A refusal is pinned as what the viewer does, not where the body lands: a setter trap on the body's scrollTop records
// every script write across the switch, and a refused switch makes none. Where the body lands is then the browser's
// own: with the sheets' default overflow-anchor Chromium's scroll anchoring re-finds an anchor in the new content and
// moves the body with it (pane 900, Alpha 3px past the edge: 1969 to 2617 on the swap, no script write; with
// overflow-anchor none the number stands), so the numeric scrollTop the plan speaks of is what the viewer leaves alone,
// not always what the reader sees.
// Legs await frames and paint counts, never a timer. Skips LOUDLY without a playwright browser, as the other legs do.
// Synthetic values only: an invented report, /repo/notes-api paths, the placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, frames, paintsReach, topBlock, PARA, REPORT } from "./real-viewer-leg";

const near = (a: number, b: number, what: string, tol = 1.5) => assert.ok(Math.abs(a - b) <= tol, `${what}: ${a} vs ${b}`);
const paras = (a: number, b: number) => Array.from({ length: b - a + 1 }, (_, i) => PARA(a + i)).join("\n\n");
const WRAP = "<details>\n<summary>More</summary>\n\nHidden details text here.\n\n</details>";
const WRAP_ROW = /^<(details|summary|\/details)|^Hidden details/;
const SVG = "data:image/svg+xml;utf8," + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="900" height="600"><rect width="900" height="600" fill="steelblue"/></svg>');

const click = async (page: any, label: string) => { await page.locator("#romp-fileview .fileview-btn", { hasText: new RegExp("^" + label + "$") }).click(); await frames(page, 3); };
const scrollTopOf = (page: any): Promise<number> => page.evaluate(() => document.querySelector(".fileview-body")!.scrollTop);
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
  const r = el.getBoundingClientRect(); return { top: Math.round((r.top - br.top) * 10) / 10, bottom: Math.round((r.bottom - br.top) * 10) / 10, scrollTop: body.scrollTop };
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
const imagesDone = (page: any) => page.waitForFunction(() => Array.from(document.querySelectorAll(".fileview-md img")).every((i) => (i as HTMLImageElement).complete), null, { timeout: 10000 });
/** Trap every script write of the body's scrollTop from now on (the viewer's seat is one; the browser's own scrolls are not
 *  writes), so a switch can be shown to have seated nothing. Installed after the scene's own scroll. */
const trapWrites = (page: any) => page.evaluate(() => {
  const body = document.querySelector(".fileview-body") as HTMLElement;
  const proto = Object.getOwnPropertyDescriptor(Element.prototype, "scrollTop")!;
  (window as any).__writes = [];
  Object.defineProperty(body, "scrollTop", { get() { return proto.get!.call(this); }, set(v) { (window as any).__writes.push(v); proto.set!.call(this, v); }, configurable: true });
});
const writes = (page: any): Promise<number[]> => page.evaluate(() => (window as any).__writes as number[]);
const fontSizeOf = (page: any): Promise<number> => page.evaluate(() => parseFloat(getComputedStyle(document.querySelector(".fileview-md > p")!).fontSize));

test("in a browser, the real module: a two-tag html block whose first tag hangs on an entity past U+10FFFF is read without a throw: the Raw switch lands on the tag's own row and returns to the tag, and a text-size step paints (the second round's decoder threw a RangeError inside both clicks)", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const ENTITIES: Array<[string, string]> = [
      ["a decimal entity past U+10FFFF", "&#1114112;"],
      ["a hex entity past U+10FFFF", "&#x110000;"],
      ["a 100,003-character entity", "&#" + "1".repeat(100_000) + ";"],
    ];
    for (const [what, ent] of ENTITIES) {
      const DOC = "# Report\n\n" + paras(1, 40) + "\n\n" + `<p>First tag ${ent} here.</p>\n<p>Second tag.</p>` + "\n\n" + paras(41, 80) + "\n";
      const { page, errors } = await openViewer(browser, "pane", 900, 600, { docs: { [REPORT]: DOC } });
      await scrollInto(page, ".fileview-md > p", "First tag", 3); await frames(page, 2);
      const before = (await box(page, ".fileview-md > p", "First tag"))!;
      near(before.top, -3, what + ": the scene starts with the first tag 3px past the edge", 1);
      await click(page, "Raw");
      const row = await rowAtTop(page);
      assert.ok(row, what + ": the Raw view painted (the second round threw inside the click and the view stayed Rendered)");
      assert.ok(row!.text.startsWith("<p>First tag"), what + `: the Raw top row is the first tag's own (got ${JSON.stringify(row!.text)})`);
      await click(page, "Rendered");
      const back = (await box(page, ".fileview-md > p", "First tag"))!;
      near(back.top, before.top, what + ": back in Rendered the tag is where it was");
      // a text-size step reads the place too: it must paint, not throw
      const p0: number = await page.evaluate(() => (window as any).__paints);
      const fs0 = await fontSizeOf(page);
      await page.locator('#romp-fileview button[aria-label="Larger text"]').click();
      await paintsReach(page, p0 + 1); await frames(page, 2);
      const fs1 = await fontSizeOf(page);
      assert.ok(fs1 > fs0, what + `: A+ painted a larger text (${fs0} to ${fs1}; the second round stored the step and threw before the paint)`);
      assert.deepEqual(errors, [], what + ": no script error");
      await page.close();
    }
  });
});

test("in a browser, the real module: a two-tag html block whose first tag carries inline tags, a line break, the README badge-and-tagline pair, named entities or an entity with no semicolon is its block: the Raw switch lands on the tag's own row and returns to it (the second round read the tag as swallowed and kept the numeric scrollTop, paragraph 28 on top both ways)", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const SHAPES: Array<[string, string]> = [
      ["inline tags", "<p>A <b>bold</b> and <a href=\"https://example.test\">linked</a> <code>tag</code> first.</p>\n<p>Second tag.</p>"],
      ["a line break", "<p>First line<br>second line of the first tag.</p>\n<p>Second tag.</p>"],
      ["the README pair", `<p align="center"><a href="https://example.test"><img src="${SVG}" width="300" height="200" alt=""></a></p>\n<p align="center"><b>notes-api</b> keeps your notes in sync.</p>`],
      ["named entities", "<p>Caption &mdash; one &copy; &hellip; here.</p>\n<p>Caption two.</p>"],
      ["an entity with no semicolon", "<p>Tom &amp Jerry, a first tag.</p>\n<p>Second tag.</p>"],
    ];
    for (const [what, html] of SHAPES) {
      const DOC = "# Report\n\n" + paras(1, 40) + "\n\n" + html + "\n\n" + paras(41, 80) + "\n";
      const firstTag = html.split("\n")[0], lead = firstTag.slice(0, 14);
      const { page, errors } = await openViewer(browser, "pane", 900, 600, { docs: { [REPORT]: DOC } });
      await imagesDone(page);
      // the first tag's element: the one whose outer HTML the block's first line renders (the README pair's is textless)
      const sel = ".fileview-md > p", key = what === "the README pair" ? "" : (firstTag.replace(/<[^>]+>/g, " ").trim().split(/\s+/)[0]);
      const found = await page.evaluate(([s, k]: [string, string]) => {
        const body = document.querySelector(".fileview-body")!;
        const el = Array.from(body.querySelectorAll(s)).find((e) => (k === "" ? !!e.querySelector("img") : (e.textContent || "").includes(k)))!;
        body.scrollTop += el.getBoundingClientRect().top - body.getBoundingClientRect().top + 3;
        return (el.textContent || "").slice(0, 20);
      }, [sel, key]);
      await frames(page, 2);
      const before = await page.evaluate(([s, k]: [string, string]) => {
        const body = document.querySelector(".fileview-body")!; const br = body.getBoundingClientRect();
        const el = Array.from(body.querySelectorAll(s)).find((e) => (k === "" ? !!e.querySelector("img") : (e.textContent || "").includes(k)))!;
        return { top: Math.round((el.getBoundingClientRect().top - br.top) * 10) / 10, scrollTop: body.scrollTop };
      }, [sel, key]);
      near(before.top, -3, what + `: the scene starts with the first tag (${JSON.stringify(found)}) 3px past the edge`, 1);
      await click(page, "Raw");
      const row = (await rowAtTop(page))!;
      assert.ok(row.text.startsWith(lead), what + `: the Raw top row is the first tag's own (got ${JSON.stringify(row.text)} at scrollTop ${row.scrollTop}; the second round: paragraph 28's row, the numeric scrollTop ${before.scrollTop} kept)`);
      await click(page, "Rendered");
      const back = await page.evaluate(([s, k]: [string, string]) => {
        const body = document.querySelector(".fileview-body")!; const br = body.getBoundingClientRect();
        const el = Array.from(body.querySelectorAll(s)).find((e) => (k === "" ? !!e.querySelector("img") : (e.textContent || "").includes(k)))!;
        return { top: Math.round((el.getBoundingClientRect().top - br.top) * 10) / 10, scrollTop: body.scrollTop };
      }, [sel, key]);
      near(back.top, before.top, what + ": back in Rendered the tag is where it was");
      assert.deepEqual(errors, [], what + ": no script error");
      await page.close();
    }
  });
});

test("in a browser, the real module: inside a wrapper's swallowed run, a picture the reader is 100px into or a rule at the edge reads as no place, so the Raw switch seats nothing and a paragraph is on top both ways (the second round took a textless element for the wrapper's own and the Raw switch jumped 1750px up to <details>); a Raw row of the wrapper's own switched to Rendered seats nothing (the second round seated the run, paragraph 74 at 3585 for 360)", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const DOC = "# Report\n\n" + paras(1, 4) + "\n\n" + WRAP + "\n\n" + paras(5, 40) + "\n\n" + `![a picture](${SVG})` + "\n\n" + paras(41, 60) + "\n\n---\n\n" + paras(61, 80) + "\n";
    // the fixture: the browser nests the inner paragraph inside <details>, the paragraphs after </details> are siblings
    for (const [what, sel, extra] of [["the picture, 100px in", ".fileview-md > p > img", 100], ["the rule at the edge", ".fileview-md > hr", 0]] as const) {
      const { page, errors } = await openViewer(browser, "pane", 900, 600, { docs: { [REPORT]: DOC } });
      await imagesDone(page);
      const nested = await page.evaluate(() => { const w = document.querySelector(".fileview-md > details")!; return { kids: w.children.length, tall: (document.querySelector(".fileview-md > p > img") as HTMLElement).getBoundingClientRect().height }; });
      assert.equal(nested.kids, 2, what + ": the fixture nests the summary and the inner paragraph in the wrapper");
      assert.ok(nested.tall > 300, what + `: the picture is tall (${nested.tall})`);
      await page.evaluate(([s, x]: [string, number]) => {
        const body = document.querySelector(".fileview-body")!; const el = document.querySelector(s)!;
        const target = s.endsWith("img") ? el.parentElement! : el;
        body.scrollTop += target.getBoundingClientRect().top - body.getBoundingClientRect().top + x;
      }, [sel, extra]);
      await frames(page, 2);
      const st0 = await scrollTopOf(page);
      const topEl = await page.evaluate((s: string) => {
        const body = document.querySelector(".fileview-body")!; const br = body.getBoundingClientRect();
        const el = document.querySelector(s)!; const target = s.endsWith("img") ? el.parentElement! : el;
        return Math.round((target.getBoundingClientRect().top - br.top) * 10) / 10;
      }, sel);
      near(topEl, -extra, what + ": the scene starts with the element at its depth", 1);
      await trapWrites(page);
      await click(page, "Raw");
      const row = (await rowAtTop(page))!;
      assert.ok(!WRAP_ROW.test(row.text), what + `: the Raw top row is not the wrapper's (got ${JSON.stringify(row.text)} at scrollTop ${row.scrollTop}; the second round: <details>, 1750px up)`);
      assert.deepEqual(await writes(page), [], what + `: the viewer wrote no scrollTop across the switch (no place read, so no seat; the body's landing, ${row.scrollTop} for ${st0}, is the browser's own)`);
      await click(page, "Rendered");
      const back = (await topBlock(page))!;
      assert.ok(/^Paragraph \d+:/.test(back.text), what + `: back in Rendered a paragraph is on top (got ${JSON.stringify(back.text)})`);
      assert.deepEqual(errors, [], what + ": no script error");
      await page.close();
    }
    // a Raw row of the wrapper's own: <summary> 8px above the edge, switched to Rendered
    const { page, errors } = await openViewer(browser, "pane", 900, 600, { docs: { [REPORT]: DOC }, raw: true });
    await rowToEdge(page, "<summary>More</summary>", 8); await frames(page, 2);
    const row = (await rowAtTop(page))!;
    assert.equal(row.text, "<summary>More</summary>", "the scene starts on the summary row");
    near(row.top, -8, "8px above the edge", 1);
    await trapWrites(page);
    await click(page, "Rendered");
    const back = (await topBlock(page))!;
    assert.deepEqual(await writes(page), [], `the viewer wrote no scrollTop across the switch: the wrapper's pairing is refused, so no seat (the top block is ${JSON.stringify(back.text)} at ${back.scrollTop} for ${row.scrollTop}; the second round seated the run, paragraph 74 at 3585)`);
    const m = /^Paragraph (\d+):/.exec(back.text);
    assert.ok(/^More/.test(back.text) || (m && Number(m[1]) < 20), `the top block is near the wrapper, not deep in its run (got ${JSON.stringify(back.text)})`);
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});

test("in a browser, the real module: two html blocks a blank line apart read as no place from either element, so the Raw click seats nothing (the second round read the second element as its block and put the Raw view one row off)", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const DOC = "# Report\n\n" + paras(1, 40) + "\n\n<p>Alpha: the first of two adjacent html blocks.</p>\n\n<p>Beta: the second, a blank line after the first.</p>\n\n" + paras(41, 80) + "\n";
    for (const who of ["Alpha:", "Beta:"]) {
      const { page, errors } = await openViewer(browser, "pane", 900, 600, { docs: { [REPORT]: DOC } });
      await scrollInto(page, ".fileview-md > p", who, 3); await frames(page, 2);
      const before = (await box(page, ".fileview-md > p", who))!;
      near(before.top, -3, who + " the scene starts with the element 3px past the edge", 1);
      await trapWrites(page);
      await click(page, "Raw");
      const row = (await rowAtTop(page))!;
      assert.deepEqual(await writes(page), [], who + ` the viewer wrote no scrollTop across the switch, the pairing refused (the Raw top row is ${JSON.stringify(row.text)} at ${row.scrollTop} for ${before.scrollTop}, the browser's own landing; the second round seated ${who === "Beta:" ? "Beta's block, one row off" : "nothing here either"})`);
      await click(page, "Rendered");
      assert.ok(/^Paragraph \d+:|^Alpha|^Beta/.test((await topBlock(page))!.text), who + " back in Rendered without error");
      assert.deepEqual(errors, [], who + " no script error");
      await page.close();
    }
  });
});

test("in a browser, the real module: an html <pre> block keeps the depth rule across the Raw to Rendered switch (line 10 at the edge within a line, where the second round's line rule seated line 11, one off); a fenced code block stays exact", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const HTML_PRE = "<pre>\n" + Array.from({ length: 40 }, (_, i) => `html line ${i + 1}: some words in a preformatted html block`).join("\n") + "\n</pre>";
    const FENCED = "```text\n" + Array.from({ length: 40 }, (_, i) => `fenced line ${i + 1}: some words in a fenced code block`).join("\n") + "\n```";
    const DOC = "# Report\n\n" + paras(1, 20) + "\n\n" + HTML_PRE + "\n\n" + paras(21, 30) + "\n\n" + FENCED + "\n\n" + paras(31, 60) + "\n";
    /** The line of the given <pre> under the body's top edge, through the browser's hit test: 1-based, with its text. A
     *  fenced block is cut into per-line rows since Slice 3 of plans/markdown-viewer.md (code-block.ts): its first column
     *  is the line-number gutter, so the hit test lands on the first text column and the line is the row under the caret;
     *  the html <pre> has no rows and is read by its text's newlines. */
    const lineAtEdge = (page: any, holds: string) => page.evaluate((h: string) => {
      const body = document.querySelector(".fileview-body")!; const br = body.getBoundingClientRect();
      const pre = Array.from(document.querySelectorAll(".fileview-md > pre")).find((p) => (p.textContent || "").includes(h))!;
      const root = pre.querySelector("code") || pre; const cr = root.getBoundingClientRect();
      const rows = Array.from(root.querySelectorAll(":scope > .cl"));
      const ct = root.querySelector(":scope > .cl > .ct"); const x = (ct ? ct.getBoundingClientRect().left : cr.left) + 2;
      const r = (document as any).caretRangeFromPoint(x, br.top + 1);
      if (rows.length) {
        const n: Node = r.startContainer;
        let row: Element | null = n.nodeType === 3 ? (n.parentElement as Element).closest(".cl") : (n as Element).closest(".cl");
        if (!row && n === root) row = (root.childNodes[r.startOffset] as Element | undefined) || null;
        const line = row ? rows.indexOf(row) : -1;
        return { line: line + 1, text: (row ? row.textContent || "" : "").trim(), preTop: Math.round((pre.getBoundingClientRect().top - br.top) * 10) / 10 };
      }
      let acc = 0, off = -1;
      const walk = (n: Node): boolean => { if (n === r.startContainer) { off = acc + (n.nodeType === 3 ? r.startOffset : 0); return true; } if (n.nodeType === 3) { acc += (n as Text).data.length; return false; } for (const c of Array.from(n.childNodes)) if (walk(c)) return true; return false; };
      walk(root);
      const text = root.textContent || ""; const line = text.slice(0, off).split("\n").length - 1;
      return { line: line + 1, text: text.split("\n")[line].trim(), preTop: Math.round((pre.getBoundingClientRect().top - br.top) * 10) / 10 };
    }, holds);
    for (const [what, rowText, holds, want] of [["the html <pre>", "html line 10:", "html line", /^html line (9|10|11):/], ["the fenced block", "fenced line 10:", "fenced line", /^fenced line 10:/]] as const) {
      const { page, errors } = await openViewer(browser, "pane", 900, 600, { docs: { [REPORT]: DOC }, raw: true });
      await rowToEdge(page, rowText, 3); await frames(page, 2);
      const row = (await rowAtTop(page))!;
      assert.ok(row.text.startsWith(rowText), what + `: the scene starts on the row (got ${JSON.stringify(row.text)})`);
      await click(page, "Rendered");
      const at = await lineAtEdge(page, holds);
      assert.match(at.text, want, what + `: the line at the edge (got line ${at.line}, ${JSON.stringify(at.text)}; the second round: html line 11, the code's line of the row's index, one off since the block's first line is the tag)`);
      if (what === "the html <pre>") assert.ok(at.line >= 9 && at.line <= 11 && at.line !== 11, what + `: within a line of 10 and not the one-off answer (got ${at.line})`);
      assert.deepEqual(errors, [], what + ": no script error");
      await page.close();
    }
  });
});

test("in a browser, the real module: a Rendered code block of long lines in a 380px pane, the reader partway into line 50's wrapped rows: the line's first character is what the place keeps, so a drag to 900px and back holds it within 2px, with the browser's scroll anchoring on (the second round kept the hit row's top and the first drag moved the passage by a wrapped row) and off, where only the viewer's seat can hold it (the base keeps the numeric scrollTop and the character goes 2500px off)", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const LINES = Array.from({ length: 120 }, (_, i) => (i === 0 ? "def f1(x):  # line 1 of a long code block" : `    return x + ${i + 1}  # ` + "a long trailing comment that wraps in a narrow pane ".repeat(3).trim()));
    const DOC = "# Report\n\n" + paras(1, 10) + "\n\n```python\n" + LINES.join("\n") + "\n```\n\n" + paras(11, 20) + "\n";
    /** The top of the first character of code line `n` (1-based), from the body's top edge: the first text node of row
     *  `n - 1` since Slice 3 cut every fence into per-line rows (code-block.ts), else the character after the (n - 1)th
     *  newline of the code's text. */
    const firstCharTop = (page: any, n: number): Promise<number> => page.evaluate((k: number) => {
      const body = document.querySelector(".fileview-body")!; const br = body.getBoundingClientRect();
      const code = document.querySelector(".fileview-md > pre code")!;
      const texts: Text[] = []; const walk = (nd: Node) => { for (const c of Array.from(nd.childNodes)) { if (c.nodeType === 3) texts.push(c as Text); else walk(c); } };
      const rows = Array.from(code.querySelectorAll(":scope > .cl"));
      if (rows.length) {
        if (!rows[k - 1]) return NaN;
        walk(rows[k - 1]);
        const t = texts.find((x) => x.data.length > 0);
        if (!t) return NaN;
        const rg = document.createRange(); rg.setStart(t, 0); rg.setEnd(t, 1);
        return rg.getClientRects()[0].top - br.top;
      }
      walk(code);
      let seen = 0;
      for (let i = 0; i < texts.length; i++) {
        const d = texts[i].data;
        if (k === 1) { const rg = document.createRange(); rg.setStart(texts[0], 0); rg.setEnd(texts[0], 1); return rg.getClientRects()[0].top - br.top; }
        for (let j = 0; j < d.length; j++) {
          if (d.charCodeAt(j) !== 10 || ++seen < k - 1) continue;
          const pos = j + 1 < d.length ? { node: texts[i], offset: j + 1 } : { node: texts[i + 1], offset: 0 };
          const rg = document.createRange(); rg.setStart(pos.node, pos.offset); rg.setEnd(pos.node, pos.offset + 1);
          return rg.getClientRects()[0].top - br.top;
        }
      }
      return NaN;
    }, n);
    const { page, errors } = await openViewer(browser, "pane", 380, 600, { docs: { [REPORT]: DOC } });
    const rows = await page.evaluate(() => { const code = document.querySelector(".fileview-md > pre code")!; const lh = parseFloat(getComputedStyle(code).lineHeight); return code.getBoundingClientRect().height / lh / 120; });
    assert.ok(rows > 2, `the fixture: each line wraps to several rows at 380px (${rows.toFixed(1)} rows per line)`);
    const t0 = await firstCharTop(page, 50);
    await page.evaluate((d: number) => { document.querySelector(".fileview-body")!.scrollTop += d; }, t0 + 20.4);
    await frames(page, 3);                                                   // the scroll-time read
    const start = await firstCharTop(page, 50);
    near(start, -20.4, "the scene starts with line 50's first character 20.4px above the edge (the hit a pixel below the edge is on its second wrapped row)", 1);
    // Two passes over the same drags (the header): with the sheets' default overflow-anchor Chromium's own anchoring
    // lands the character within 0.2px and the viewer writes nothing, so the pass pins the point the seat computes (a
    // wrong rule seats another point over the browser's landing); with anchoring off, a test-only style on the body
    // (the sheets declare none, plan item 5), only the viewer's seat can hold the character, so the pass pins the seat
    // itself: the base commit, with no seat, keeps the numeric scrollTop and the character goes 2500px off.
    for (const anchoring of ["on", "off"] as const) {
      if (anchoring === "off") await page.evaluate(() => { (document.querySelector(".fileview-body") as HTMLElement).style.overflowAnchor = "none"; });
      for (const width of [900, 380] as const) {
        await trapWrites(page);
        const paints: number = await page.evaluate(() => (window as any).__paints);
        await page.setViewportSize({ width, height: 600 });
        await paintsReach(page, paints + 1);
        await frames(page, 2);
        const now = await firstCharTop(page, 50);
        near(now, -20.4, `with the browser's anchoring ${anchoring}, at ${width}px line 50's first character is where it was (the viewer's scrollTop writes across the drag: ${JSON.stringify(await writes(page))}; the second round: -2.1 at the first drag with anchoring on, the hit row's top seated as the line's; the base with anchoring off: -2502 at 900px, no write)`, 2);
      }
    }
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});

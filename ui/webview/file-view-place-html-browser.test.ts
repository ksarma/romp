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
//   - a textless element after a `<details>` wrapper (a picture the reader is 100px into, a rule at the edge): round 2
//     took a textless element for the wrapper's own and read the run's union box, so the Raw switch jumped 1750px up to
//     `<details>`; the third round refused the run's pairing from any element and seated nothing; since Slice 5's
//     flattened walk (anchor-map.ts pairs the wrapper's block to the wrapper and its summary, and every block after it
//     to its own element) the picture and the rule are their own blocks, so the Raw switch lands on the picture's own row
//     and the return puts the picture back at its depth, within the Raw row's whole-pixel snap scaled by the picture's
//     height over the row's, and the rule at the edge round-trips exactly;
//   - a Raw row of the wrapper's own (`<summary>`) switched to Rendered: round 2 seated the whole swallowed run at the
//     row's fraction (paragraph 74 at scrollTop 3585 for 360); the third round and Slice 5's build seated nothing (the
//     owner's ruling 2: the wrapper's own block is never seated); since the Slice 5 review's round 2 the row reads as
//     the first block nested in the wrapper (the owner's ruling extended the closing-row rule to the opener rows), which
//     the shut fold hides, so the seat stands on the block after the fold where its own row was (Place.after);
//   - the same ruling's round trips (the last three tests): a fold title at the pane's top, open or shut, at 900 and
//     380px, back within 1.5px (before: the summary's row on top of Raw after the switch, its seat refused, and the way
//     back off by 26px at 900 and 203 at 380 for an open fold); a `</details>` row followed by a comment block (before:
//     the comment was the place and the block after it landed 39px low); a README's centred `<h1>`, whose Raw rows
//     (the opener, the `<h1>`, the `<p>` tagline, an `<img>` line, the blank row before the opener) all read as the
//     first nested block (before: the wrapper's block, its seat refused, 44 to 153px lost each way);
//   - two html blocks a blank line apart: the map paired the first to nothing and the second to both elements; round 2
//     read the second element as its block and put the Raw view one row off, the third round read neither as a place
//     and seated nothing; since Slice 5's walk each is its own block, so from either element the Raw switch lands on the
//     block's own row and the return puts it back where it was;
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
//     and the character goes to -2502, then +922 back at 380);
//   - the Slice 5 review's rounds 3 to 5 (tests 9 to 15): a wrapper's own picture in both directions (Place.pic), from the
//     rows before its tag row, through a run of blocks before the wrapper (a comment's row, a closer's, the outer opener of a
//     wrapper two deep), the picture at the edge among several on one line, a picture in a row beside text, the shown row of
//     the wrapper's own kept across a same-view reflow (Place.lead: a wrapping fold title across a pane drag, the aside and a
//     text-size step), and a commented-out tag counted for no picture.
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
import { inBrowser, openViewer, openPanel, closePanel, frames, paintsReach, topBlock, PARA, REPORT } from "./real-viewer-leg";

const near = (a: number, b: number, what: string, tol = 1.5) => assert.ok(Math.abs(a - b) <= tol, `${what}: ${a} vs ${b}`);
const paras = (a: number, b: number) => Array.from({ length: b - a + 1 }, (_, i) => PARA(a + i)).join("\n\n");
const WRAP = "<details>\n<summary>More</summary>\n\nHidden details text here.\n\n</details>";
const WRAP_ROW = /^<(details|summary|\/details)|^Hidden details/;
const SVG = "data:image/svg+xml;utf8," + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="900" height="600"><rect width="900" height="600" fill="steelblue"/></svg>');

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
/** The box of the element `sel` names (for an `img`, its parent `<p>`, the block's element), from the body's top edge. */
const targetBox = (page: any, sel: string) => page.evaluate((s: string) => {
  const body = document.querySelector(".fileview-body")!; const br = body.getBoundingClientRect();
  const el = document.querySelector(s)!; const target = s.endsWith("img") ? el.parentElement! : el;
  const r = target.getBoundingClientRect();
  return { top: Math.round((r.top - br.top) * 10) / 10, height: Math.round(r.height * 10) / 10, scrollTop: body.scrollTop };
}, sel);
/** The first top-level element of the Rendered view ending below the body's top edge: its tag, whether it holds a picture, its top. */
const topElement = (page: any) => page.evaluate(() => {
  const body = document.querySelector(".fileview-body")!; const br = body.getBoundingClientRect();
  for (const e of Array.from(body.querySelectorAll(".fileview-md > *"))) { const r = e.getBoundingClientRect(); if (r.bottom > br.top + 0.5) return { tag: e.tagName, hasImg: !!e.querySelector("img"), top: Math.round((r.top - br.top) * 10) / 10 }; }
  return null;
});

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

test("in a browser, the real module: after a <details> wrapper the browser nests markdown into, a picture the reader is 100px into and a rule at the edge are their own blocks (Slice 5's flattened walk; before it the wrapper's block took every element after it, the place refused the run and the Raw switch seated nothing; the second round took a textless element for the wrapper's own and the switch jumped 1750px up to <details>): the Raw switch lands on the picture's own row and the return puts the picture back at its depth, within the row's snap scaled by the picture's height; the rule round-trips exactly, the rule's row at the edge in Raw; a Raw row of the wrapper's own (`<summary>`) switched to Rendered seats the block after the shut fold where its own row was (the Slice 5 review's round 2: the opener rows read as the first nested block, which the shut fold hides, so the carried block after the fold stands; before: no seat under ruling 2; the second round seated the run, paragraph 74 at 3585 for 360)", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const DOC = "# Report\n\n" + paras(1, 4) + "\n\n" + WRAP + "\n\n" + paras(5, 40) + "\n\n" + `![a picture](${SVG})` + "\n\n" + paras(41, 60) + "\n\n---\n\n" + paras(61, 80) + "\n";
    // the fixture: the browser nests the inner paragraph inside <details>, the paragraphs after </details> are siblings
    // the rule sits 2px BELOW the edge, not on it: a 1px hairline whose top is at the edge ends at the edge plus a pixel, the very
    // bound the place reads a box against, so which block the place keeps (the rule, or the paragraph after it) would turn on the
    // browser's sub-pixel snap; both round-trip the rule to where it was, but only one puts the rule's own row at a known place
    for (const [what, sel, extra] of [["the picture, 100px in", ".fileview-md > p > img", 100], ["the rule 2px below the edge", ".fileview-md > hr", -2]] as const) {
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
      const before = await targetBox(page, sel);
      near(before.top, -extra, what + ": the scene starts with the element at its depth", 1);
      await click(page, "Raw");
      const row = (await rowAtTop(page))!;
      assert.ok(!WRAP_ROW.test(row.text), what + `: the Raw top row is not the wrapper's (got ${JSON.stringify(row.text)} at scrollTop ${row.scrollTop}; the second round: <details>, 1750px up)`);
      let tol = 1.5;
      if (what === "the picture, 100px in") {
        // the picture's block is one Raw row (its data: URI, wrapped): the seat puts it 100px of the picture's height into the row, the
        // browser snaps that to a whole pixel, and the way back scales the snap by the picture's height over the row's
        assert.ok(row.text.startsWith("![a picture]("), what + `: the Raw top row is the picture's own (got ${JSON.stringify(row.text)}; before Slice 5 no seat, the browser's own landing)`);
        const rowBox = (await box(page, "code.hljs .fv-cl", "![a picture]("))!;
        tol = Math.max(1.5, 0.5 * before.height / (rowBox.bottom - rowBox.top) + 1);
      } else {
        // the rule started below the edge, so its row keeps that distance: the rule's own row 2px below the edge, the blank row before
        // it the top row
        const hrRow = (await box(page, "code.hljs .fv-cl", "---"))!;
        near(hrRow.top, 2, what + `: the rule's own row 2px below the edge (the top row is ${JSON.stringify(row.text)}; before Slice 5 no seat, the browser's own landing at ${row.scrollTop})`, 1);
      }
      await click(page, "Rendered");
      const back = await targetBox(page, sel);
      near(back.top, before.top, what + `: back in Rendered the element is where it was (before Slice 5: no seat either way, a paragraph on top by the browser's own landing)`, tol);
      const top = (await topElement(page))!;
      assert.ok(what === "the picture, 100px in" ? top.tag === "P" && top.hasImg : top.tag === "HR", what + `: the element is the top block again (got ${JSON.stringify(top)})`);
      assert.deepEqual(errors, [], what + ": no script error");
      await page.close();
    }
    // a Raw row of the wrapper's own: <summary> 8px above the edge, switched to Rendered. The row reads as the first nested block
    // (the hidden paragraph), which the shut fold does not show, so the seat stands on the block after the fold, paragraph 5, no
    // lower than the fold's summary at the edge (the Slice 5 review's round 3; round 2 stood on paragraph 5 where its own row was,
    // 100px down, the summary 70px under the edge; the wrapper's own block is still never seated: ruling 2)
    const { page, errors } = await openViewer(browser, "pane", 900, 600, { docs: { [REPORT]: DOC }, raw: true });
    await rowToEdge(page, "<summary>More</summary>", 8); await frames(page, 2);
    const row = (await rowAtTop(page))!;
    assert.equal(row.text, "<summary>More</summary>", "the scene starts on the summary row");
    near(row.top, -8, "8px above the edge", 1);
    const p5Row = (await box(page, "code.hljs .fv-cl", "Paragraph 5:"))!;
    assert.ok(p5Row.top > 30 && p5Row.top < 120, `paragraph 5's row, the block after the fold, is below the edge by more than the summary's box (top ${p5Row.top})`);
    await trapWrites(page);
    await click(page, "Rendered");
    assert.equal((await writes(page)).length, 1, `the viewer seated once across the switch (before: no write, the wrapper's block refused; the second round seated the run, paragraph 74 at 3585)`);
    const p5 = (await box(page, ".fileview-md > p", "Paragraph 5:"))!;
    const sum = (await box(page, ".fileview-md summary", "More"))!;
    near(sum.top, 0, `the fold's summary is at the edge (round 2: paragraph 5 where its own row was, ${p5Row.top}px down; before: the numeric scrollTop standing)`);
    assert.ok(p5.top > sum.bottom && p5.top < p5Row.top, `paragraph 5, the block after the shut fold, follows the summary, above where its row was (top ${p5.top}, the row at ${p5Row.top})`);
    const back = (await topBlock(page))!;
    assert.ok(/^More/.test(back.text), `the top block is the fold (got ${JSON.stringify(back.text)})`);
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});

test("in a browser, the real module: two html blocks a blank line apart are their own blocks (Slice 5's flattened walk; before it the map paired the first to nothing and the second to both, the place refused both elements and the Raw click seated nothing; the second round read the second element as its block and put the Raw view one row off): from either element the Raw switch lands on the block's own row and the return puts it back where it was", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const DOC = "# Report\n\n" + paras(1, 40) + "\n\n<p>Alpha: the first of two adjacent html blocks.</p>\n\n<p>Beta: the second, a blank line after the first.</p>\n\n" + paras(41, 80) + "\n";
    for (const who of ["Alpha:", "Beta:"]) {
      const { page, errors } = await openViewer(browser, "pane", 900, 600, { docs: { [REPORT]: DOC } });
      await scrollInto(page, ".fileview-md > p", who, 3); await frames(page, 2);
      const before = (await box(page, ".fileview-md > p", who))!;
      near(before.top, -3, who + " the scene starts with the element 3px past the edge", 1);
      await click(page, "Raw");
      const row = (await rowAtTop(page))!;
      assert.ok(row.text.startsWith("<p>" + who), who + ` the Raw top row is the block's own (got ${JSON.stringify(row.text)} at ${row.scrollTop} for ${before.scrollTop}; before Slice 5 the pairing was refused and the viewer seated nothing, the browser's own landing; the second round seated ${who === "Beta:" ? "Beta's block, one row off" : "nothing here"})`);
      await click(page, "Rendered");
      const back = (await box(page, ".fileview-md > p", who))!;
      near(back.top, before.top, who + " back in Rendered the element is where it was");
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

/** paragraphs 1 to 10, a details (open or shut) with a one-line summary holding paragraphs 11 to 15, then `tail` and paragraphs 16 to 30 */
const foldDoc = (open: boolean, tail = "") => "# Report\n\n" + paras(1, 10) + "\n\n<details" + (open ? " open" : "") + ">\n<summary>Fold title</summary>\n\n" + paras(11, 15) + "\n\n</details>\n\n" + tail + paras(16, 30) + "\n";
const FOLD_ROW = /^(<details|<summary>|<\/details>|Paragraph 1[1-5]:|$)/;

test("in a browser, the real module: Rendered to Raw to Rendered from a fold title at the pane's top edge is exact for an open and a shut fold at 900 and 380px (the summary passed over, the Rendered read names the first nested block, or the block after a shut fold; the Raw seat puts its row there, so a row of the fold's own is on top of Raw; the way back reads that row as the first nested block, carrying the block after the fold, and seats what the view shows; before: the wrapper's block was the place from its own rows, its seat refused, and the way back lost 26px at 900 and 203 at 380 for the open fold); and from Raw, a `</details>` row 9px above the edge followed by a comment block puts the block after both where its row was (before: the comment was the place, seated through the block before it, and the block after landed 39px low)", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const open of [true, false]) {
      for (const width of [900, 380]) {
        const what = `${open ? "open" : "shut"} fold, pane ${width}`;
        const { page, errors } = await openViewer(browser, "pane", width, 600, { docs: { [REPORT]: foldDoc(open) } });
        await scrollInto(page, ".fileview-md summary", "Fold title", 0); await frames(page, 2);
        const summary = (await box(page, ".fileview-md summary", "Fold title"))!;
        near(summary.top, 0, what + ": the scene starts with the summary's top at the edge", 1);
        const inner = open ? ".fileview-md details > p" : ".fileview-md > p", innerText = open ? "Paragraph 11:" : "Paragraph 16:";
        const before = (await box(page, inner, innerText))!;
        assert.ok(before.top > 0, what + `: ${innerText} is below the edge (top ${before.top})`);
        await click(page, "Raw");
        const row = (await rowAtTop(page))!;
        assert.ok(FOLD_ROW.test(row.text), what + `: the top Raw row is one of the fold's own, the scene the way back reads from (got ${JSON.stringify(row.text)} at ${row.top})`);
        const innerRow = (await box(page, "code.hljs .fv-cl", innerText))!;
        near(innerRow.top, before.top, what + `: ${innerText}'s own row is where the block was`, 1);
        await click(page, "Rendered");
        const back = (await box(page, inner, innerText))!;
        near(back.top, before.top, what + `: back in Rendered ${innerText} is where it was (before: ${open ? (width === 900 ? "26" : "203") + "px off, the summary row's seat refused" : "exact since round 1 through the closing row"})`);
        const sum2 = (await box(page, ".fileview-md summary", "Fold title"))!;
        near(sum2.top, 0, what + ": the summary's top is at the edge again");
        assert.deepEqual(errors, [], what + ": no script error");
        await page.close();
      }
    }
    // the closing row 9px above the edge, a comment block after it: from Raw, the block after both where its row was
    const withComment = foldDoc(false, "<!-- a note to self -->\n\n");
    const { page, errors } = await openViewer(browser, "pane", 900, 600, { docs: { [REPORT]: withComment }, raw: true });
    await rowToEdge(page, "</details>", 9); await frames(page, 2);
    const row = (await rowAtTop(page))!;
    assert.equal(row.text, "</details>", `the scene starts on the closing row (got ${JSON.stringify(row.text)})`);
    const p16Row = (await box(page, "code.hljs .fv-cl", "Paragraph 16:"))!;
    assert.ok(p16Row.top > 30 && p16Row.top < 90, `paragraph 16's row is below the closer, the comment's row and two blanks, more than the summary's box below the edge (top ${p16Row.top})`);
    await click(page, "Rendered");
    const p16 = (await box(page, ".fileview-md > p", "Paragraph 16:"))!;
    const sum = (await box(page, ".fileview-md summary", "Fold title"))!;
    near(sum.top, 0, `the shut fold's summary is at the edge, paragraph 16 seated no lower than that (the review's round 3; round 2: paragraph 16 where its row was, ${p16Row.top}px down, the tail of paragraph 10 under the edge; before: the comment block was the place, paragraph 15 seated at the row's depth, and paragraph 16 39px low)`);
    assert.ok(p16.top > sum.bottom && p16.top < p16Row.top, `paragraph 16 follows the summary, above where its row was (top ${p16.top}, the row at ${p16Row.top})`);
    // and the round trip from the summary at the edge over the same note, the recheck's residual scene
    await scrollInto(page, ".fileview-md summary", "Fold title", 0); await frames(page, 2);
    const before = (await box(page, ".fileview-md > p", "Paragraph 16:"))!;
    await click(page, "Raw"); await click(page, "Rendered");
    const back = (await box(page, ".fileview-md > p", "Paragraph 16:"))!;
    near(back.top, before.top, "Rendered to Raw to Rendered from the summary at the edge, the comment after the closer: paragraph 16 where it was");
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});

const LOGO = "data:image/svg+xml;utf8," + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="200" height="120"><rect width="200" height="120" fill="darkseagreen"/></svg>');
/** paragraphs 1 to 5, a centred div whose block holds `lead` (its own rows), then paragraphs 6 to 8 nested, `</div>`, paragraphs 9 to 25 */
const readme = (lead: string) => "# Report\n\n" + paras(1, 5) + "\n\n<div align=\"center\">\n" + lead + "\n\n" + paras(6, 8) + "\n\n</div>\n\n" + paras(9, 25) + "\n";
const README = readme("<h1>Project</h1>\n<p>A tagline for the project</p>");
// the logo carries its dimensions, as a README's usually does: the viewer seats at paint time, and an image with none is laid out at
// no height until it loads, moving every block below it after the seat (a load, not the place, is then what the scene would measure)
const IMG_LEAD = readme(`<img src="${LOGO}" alt="logo" width="200" height="120">\n\n## Centred title`);
/** the same with a 900 by 600 banner, laid out at the column's width: about 508px tall at 900 and 229 at 380 */
const BANNER_LEAD = readme(`<img src="${SVG}" alt="banner" width="900" height="600">\n\n## Centred title`);
const WRAPPER_ROW = /^(<div align|<h1>|<p>A tagline|<img src|$)/;
/** The box of the wrapper's own picture (`.fileview-md div > img`), from the body's top edge. */
const imgBox = (page: any) => page.evaluate(() => {
  const body = document.querySelector(".fileview-body")!; const br = body.getBoundingClientRect(); const r = (x: number) => Math.round(x * 10) / 10;
  const i = document.querySelector(".fileview-md div > img")!.getBoundingClientRect();
  return { top: r(i.top - br.top), bottom: r(i.bottom - br.top), height: r(i.height), scrollTop: body.scrollTop };
});

test("in a browser, the real module: a README's centred header. Rendered to Raw to Rendered with the `<h1>` at the top edge is exact at 900 and 380px (the Rendered read passes over the wrapper's own `<h1>` and `<p>` for the first nested paragraph; the Raw seat puts its row there and a row of the wrapper's block, or the blank row before it, is on top; the way back reads that row as the first nested block; before: the blank row resolved to the wrapper's block, its seat was refused, and the `<h1>` came back 64px low at 900 and 153 at 380); from Raw, the `<h1>` and the `<p>` tagline rows at the edge at 900 and 380px, and an `<img>` lead row at 900, switched to Rendered and back come back within 1.5px (before: no seat from any of them, 44 to 121px lost); and a small logo's top at the edge at 380px round-trips exactly (the `<div align=\"center\">` row on top of Raw; before: 112px lost)", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const width of [900, 380]) {
      const what = `pane ${width}`;
      const { page, errors } = await openViewer(browser, "pane", width, 600, { docs: { [REPORT]: README } });
      await scrollInto(page, ".fileview-md h1", "Project", 0); await frames(page, 2);
      const before = (await box(page, ".fileview-md h1", "Project"))!;
      near(before.top, 0, what + ": the scene starts with the h1's top at the edge", 1);
      const p6 = (await box(page, ".fileview-md div > p", "Paragraph 6:"))!;
      await click(page, "Raw");
      const row = (await rowAtTop(page))!;
      assert.ok(WRAPPER_ROW.test(row.text), what + `: the top Raw row is the wrapper's own or the blank before it (got ${JSON.stringify(row.text)} at ${row.top})`);
      const p6Row = (await box(page, "code.hljs .fv-cl", "Paragraph 6:"))!;
      near(p6Row.top, p6.top, what + ": paragraph 6's own row is where the paragraph was", 1);
      await click(page, "Rendered");
      const back = (await box(page, ".fileview-md h1", "Project"))!;
      near(back.top, before.top, what + `: back in Rendered the h1 is where it was (before: ${width === 900 ? 64 : 153}px low, the wrapper's block refused from the blank row)`);
      assert.deepEqual(errors, [], what + ": no script error");
      await page.close();
    }
    // from Raw: the wrapper's own rows at the edge, to Rendered and back. The `<h1>` and `<p>` rows read as the first nested block,
    // seated where its row was; the `<img>` row is the tag line of the wrapper's own picture (reader-place.ts Place.pic, the Slice 5
    // review's round 3), so the picture's top goes to the edge and the way back puts the row there: at 380px the data: URI row
    // wraps to 8 rows (144px), taller than the picture (120px), and the round-2 seat of the heading where its row was left the
    // paragraph before the wrapper 5.5px above the picture, the top block, whose fraction put the row 40px low on the way back
    for (const [doc, rowText, nestedSel, nestedText, widths] of [[README, "<h1>Project</h1>", ".fileview-md div > p", "Paragraph 6:", [900, 380]], [README, "<p>A tagline for the project</p>", ".fileview-md div > p", "Paragraph 6:", [900, 380]], [IMG_LEAD, "<img src=", ".fileview-md div > h2", "Centred title", [900, 380]]] as const) {
      for (const width of widths) {
        const what = `${JSON.stringify(rowText)} row, pane ${width}`;
        const { page, errors } = await openViewer(browser, "pane", width, 600, { docs: { [REPORT]: doc }, raw: true });
        await rowToEdge(page, rowText, 0); await frames(page, 2);
        const row = (await rowAtTop(page))!;
        assert.ok(row.text.startsWith(rowText.slice(0, 8)), what + `: the scene starts on the row (got ${JSON.stringify(row.text)})`);
        const nestedRow = (await box(page, "code.hljs .fv-cl", nestedText))!;
        assert.ok(nestedRow.top > 0, what + `: the first nested block's row is below the edge (top ${nestedRow.top})`);
        await click(page, "Rendered");
        if (doc === IMG_LEAD) await imagesDone(page);
        const nested = (await box(page, nestedSel, nestedText))!;
        if (doc === IMG_LEAD) {
          const pic = await imgBox(page);
          near(pic.top, 0, what + `: the picture's top is at the edge, its tag's row at the edge in Raw (round 2: the heading where its row was, the picture ${Math.round(nested.top - nestedRow.top)}px above the edge at 900 and the paragraph before the wrapper on top at 380; before: no seat)`);
          assert.ok(nested.top > pic.bottom, what + `: the heading follows the picture (top ${nested.top}, the picture's bottom ${pic.bottom})`);
        } else {
          near(nested.top, nestedRow.top, what + ": the first nested block is where its row was (before: no seat, the wrapper's block refused)");
        }
        await click(page, "Raw");
        const rowBack = (await box(page, "code.hljs .fv-cl", rowText))!;
        near(rowBack.top, 0, what + `: the row is back at the edge (before: 44 to 121px low${doc === IMG_LEAD && width === 380 ? "; round 2: 40px low, the paragraph before the wrapper's fraction" : ""})`);
        assert.deepEqual(errors, [], what + ": no script error");
        await page.close();
      }
    }
    // the logo's top at the edge at 380px: the Raw seat leaves the opener's row on top, and the way back is exact
    const { page, errors } = await openViewer(browser, "pane", 380, 600, { docs: { [REPORT]: IMG_LEAD } });
    await imagesDone(page);
    const logo = await page.evaluate(() => { const i = document.querySelector(".fileview-md div > img") as HTMLElement; const r = i.getBoundingClientRect(); return { h: r.height, ok: i.parentElement!.tagName === "DIV" }; });
    assert.ok(logo.ok && logo.h > 100, `the fixture: the logo is the wrapper's own child and laid out (${JSON.stringify(logo)})`);
    await page.evaluate(() => { const body = document.querySelector(".fileview-body")!; const i = document.querySelector(".fileview-md div > img")!; body.scrollTop += i.getBoundingClientRect().top - body.getBoundingClientRect().top; });
    await frames(page, 2);
    const before = await page.evaluate(() => { const body = document.querySelector(".fileview-body")!; return document.querySelector(".fileview-md div > img")!.getBoundingClientRect().top - body.getBoundingClientRect().top; });
    near(before, 0, "the scene starts with the logo's top at the edge", 1);
    await click(page, "Raw");
    const row = (await rowAtTop(page))!;
    assert.ok(/^<div align|^<img src/.test(row.text), `the top Raw row is the wrapper's own (got ${JSON.stringify(row.text)} at ${row.top}); a paragraph before the wrapper on top would round-trip by that paragraph's fraction instead`);
    await click(page, "Rendered"); await imagesDone(page);
    const back = await page.evaluate(() => { const body = document.querySelector(".fileview-body")!; return document.querySelector(".fileview-md div > img")!.getBoundingClientRect().top - body.getBoundingClientRect().top; });
    near(back, before, "back in Rendered the logo is where it was (before: 112px low, the opener's row's seat refused)");
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});

test("in a browser, the real module: the edge inside a wrapper's own lead picture (a README's logo or banner in a centred div) round-trips Rendered to Raw to Rendered at 900 and 380px, from the picture's top at the edge to 300px into the banner: the picture is a row of the wrapper's block the seat stands on in both directions (reader-place.ts Place.pic, the Slice 5 review's round 3), its depth kept as a fraction of its height, so its tag's row is the top Raw row at the same fraction and the picture comes back within the row's whole-pixel snap scaled by the picture's height over the row's, as a top-level picture does (test 3); and from Raw, the `<img src=` row at the edge and 9px above it comes back within 1.5px, the picture at the row's fraction between (round 2: the picture was passed over for the heading nested below it, seated where its row was, so whenever the picture's height above the edge exceeded the wrapper's rows the paragraph before the wrapper was the top Raw row and the way back was its fraction seat: 36px lost for the logo's top at the edge at 900, 430 to 442 for the banner 50 to 300px in, 70 to 82 for the banner at 380, and 40 in reverse from the wrapping data: URI row at 380)", { timeout: 300000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const [what, doc, width, depths] of [["the logo", IMG_LEAD, 900, [0, 30, 60, 100]], ["the logo", IMG_LEAD, 380, [0, 30, 60, 100]], ["the banner", BANNER_LEAD, 900, [0, 50, 150, 300]], ["the banner", BANNER_LEAD, 380, [0, 50, 100, 200]]] as const) {
      for (const depth of depths) {
        const where = `${what}, pane ${width}, ${depth}px in`;
        const { page, errors } = await openViewer(browser, "pane", width, 600, { docs: { [REPORT]: doc } });
        await imagesDone(page);
        await page.evaluate((d: number) => { const body = document.querySelector(".fileview-body")!; const i = document.querySelector(".fileview-md div > img")!; body.scrollTop += i.getBoundingClientRect().top - body.getBoundingClientRect().top + d; }, depth);
        await frames(page, 2);
        const before = await imgBox(page);
        near(before.top, -depth, where + ": the scene starts with the picture at its depth", 1);
        assert.ok(before.height > (what === "the banner" ? 200 : 100), where + `: the fixture: the picture is laid out (${before.height}px tall)`);
        await click(page, "Raw");
        const row = (await rowAtTop(page))!;
        assert.ok(row.text.startsWith("<img src="), where + `: the picture's tag row is the top Raw row (got ${JSON.stringify(row.text)} at ${row.top}; round 2: a paragraph before the wrapper, or the wrapper's opener, when the picture's height above the edge exceeded the wrapper's rows)`);
        const rowBox = (await box(page, "code.hljs .fv-cl", "<img src="))!;
        const rowH = rowBox.bottom - rowBox.top;
        near(rowBox.top, -depth * rowH / before.height, where + `: the row at the picture's fraction of its height (the row ${rowH}px tall)`, 1);
        await click(page, "Rendered"); await imagesDone(page);
        const after = await imgBox(page);
        // the Raw seat lands within the browser's whole-pixel snap of the row, which the way back scales by the picture's height over the row's (test 3's idiom)
        near(after.top, before.top, where + `: back in Rendered the picture is at its depth (round 2: ${what === "the banner" ? (width === 900 ? "430 to 442" : "70 to 82") : "36"}px off when a block before the wrapper topped the Raw view)`, Math.max(1.5, 0.5 * before.height / rowH + 1));
        assert.deepEqual(errors, [], where + ": no script error");
        await page.close();
      }
    }
    // from Raw: the picture's tag row at the edge and 9px above it, at both widths (at 380 the data: URI row wraps to 144px, taller than the logo)
    for (const [what, doc, width] of [["the logo", IMG_LEAD, 900], ["the logo", IMG_LEAD, 380], ["the banner", BANNER_LEAD, 900], ["the banner", BANNER_LEAD, 380]] as const) {
      for (const above of [0, 9]) {
        const where = `${what}, pane ${width}, the tag row ${above}px above the edge`;
        const { page, errors } = await openViewer(browser, "pane", width, 600, { docs: { [REPORT]: doc }, raw: true });
        await rowToEdge(page, "<img src=", above); await frames(page, 2);
        const row0 = (await box(page, "code.hljs .fv-cl", "<img src="))!;
        near(row0.top, -above, where + ": the scene starts on the row", 1);
        await click(page, "Rendered"); await imagesDone(page);
        const pic = await imgBox(page);
        const rowH = row0.bottom - row0.top;
        near(pic.top, -above * pic.height / rowH, where + `: the picture at the row's fraction of its height (round 2: the heading nested below it where its row was, the picture above the edge)`, Math.max(1.5, 0.5 * pic.height / rowH + 1));
        await click(page, "Raw");
        const row1 = (await box(page, "code.hljs .fv-cl", "<img src="))!;
        near(row1.top, row0.top, where + `: the row is back where it was (round 2: ${width === 380 && what === "the logo" ? "40px low, the paragraph before the wrapper's fraction" : "exact by way of the heading"})`);
        assert.deepEqual(errors, [], where + ": no script error");
        await page.close();
      }
    }
  });
});

// ── round 4: the wrapper's picture from a row of the block's own before its tag row, in either view ─────────────
/** the banner after an `<h1>` lead row, a `<p>` tagline after it: three rows of the wrapper's own, the picture the second */
const H1_BANNER = readme(`<h1>Project</h1>\n<img src="${SVG}" alt="banner" width="900" height="600">\n<p>A tagline for the project</p>`);
/** Scroll so the Raw row `offset` rows after the first whose text includes `text` has its top at the edge. */
const rowNearToEdge = (page: any, text: string, offset: number) => page.evaluate(([t, o]: [string, number]) => {
  const body = document.querySelector(".fileview-body")!;
  const rows = Array.from(body.querySelectorAll("code.hljs .fv-cl"));
  const row = rows[rows.findIndex((r) => (r.textContent || "").includes(t)) + o];
  body.scrollTop += row.getBoundingClientRect().top - body.getBoundingClientRect().top;
}, [text, offset]);
/** The Raw row `offset` rows after the first whose text includes `text`: its text and its top from the body's top edge. */
const rowNear = (page: any, text: string, offset: number) => page.evaluate(([t, o]: [string, number]) => {
  const body = document.querySelector(".fileview-body")!; const br = body.getBoundingClientRect();
  const rows = Array.from(body.querySelectorAll("code.hljs .fv-cl")); const r = rows[rows.findIndex((x) => (x.textContent || "").includes(t)) + o]; const rr = r.getBoundingClientRect();
  return { text: (r.textContent || "").trim().slice(0, 48), top: Math.round((rr.top - br.top) * 10) / 10 };
}, [text, offset]);

test("in a browser, the real module: from Raw, a row of the wrapper's block BEFORE its lead picture's tag row at the top edge (the `<div align=\"center\">` opener and the blank row before it, for the logo and the banner at 900 and 380px; the `<h1>` lead row and the opener of a README whose banner follows its `<h1>`) switched to Rendered puts the picture where its tag's row was, below the edge, the first nested block after the picture (the review's round 4; round 3 carried the tag row alone, so the nested block seated at its row's distance with the picture between them, 120 to 508px tall against one Raw row, put the logo's top 40px above the edge and the banner's 428); the way back returns the `<h1>` README's rows exactly and the logo's and banner's opener in view, at most the tail of the paragraph before the wrapper low (round 3: the picture's row seated at the picture's fraction left the opener 32 to 109px above the edge, off the pane; before the slice it came back 38 to 45px low); Rendered to Raw to Rendered with the picture's top 2px below the edge is exact for the three shapes (round 3: 59 to 447px lost at 900); and the `<h1>` 10px into the edge with the banner under it puts the tag's row in Raw where the picture was (round 3: the nested paragraph at its distance below the banner, the write clamped at the document's top)", { timeout: 300000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const FROM_RAW: Array<[string, string, string, number, string, string]> = [
      ["the logo, the opener's row", IMG_LEAD, "<div align", 0, ".fileview-md div > h2", "Centred title"],
      ["the logo, the blank row before the opener", IMG_LEAD, "<div align", -1, ".fileview-md div > h2", "Centred title"],
      ["the banner, the opener's row", BANNER_LEAD, "<div align", 0, ".fileview-md div > h2", "Centred title"],
      ["the banner, the blank row before the opener", BANNER_LEAD, "<div align", -1, ".fileview-md div > h2", "Centred title"],
      ["the banner after an <h1>, the <h1>'s row", H1_BANNER, "<h1>Project", 0, ".fileview-md div > p", "Paragraph 6:"],
      ["the banner after an <h1>, the opener's row", H1_BANNER, "<div align", 0, ".fileview-md div > p", "Paragraph 6:"],
    ];
    for (const width of [900, 380]) {
      for (const [what, doc, text, offset, nestedSel, nestedText] of FROM_RAW) {
        const where = `pane ${width}, ${what}`;
        const { page, errors } = await openViewer(browser, "pane", width, 600, { docs: { [REPORT]: doc }, raw: true });
        await rowNearToEdge(page, text, offset); await frames(page, 2);
        const row0 = await rowNear(page, text, offset);
        near(row0.top, 0, where + `: the scene starts with the row at the edge (${JSON.stringify(row0.text)})`, 1);
        const imgRow0 = (await box(page, "code.hljs .fv-cl", "<img src="))!;
        assert.ok(imgRow0.top > 0, where + `: the fixture: the picture's tag row is below the edge (top ${imgRow0.top})`);
        await click(page, "Rendered"); await imagesDone(page);
        const pic = await imgBox(page);
        near(pic.top, imgRow0.top, where + `: the picture's top is where its tag's row was, below the edge (round 3: the nested block at its row's distance, the picture between the two above the edge, the logo's top at -40 and the banner's at -428 at 900)`);
        const nested = (await box(page, nestedSel, nestedText))!;
        assert.ok(nested.top > pic.bottom, where + `: the first nested block follows the picture (top ${nested.top}, the picture's bottom ${pic.bottom})`);
        await click(page, "Raw");
        const row1 = await rowNear(page, text, offset);
        if (doc === H1_BANNER) near(row1.top, row0.top, where + ": the row is back at the edge (round 3: 65 to 109px above it, off the pane)");
        else assert.ok(row1.top > -1 && row1.top <= 35, where + `: the row is back in view, at most the tail of the paragraph before the wrapper low (got ${row1.top}; round 3: 32 to 94px above the edge, off the pane; before the slice: 38 to 45px low)`);
        assert.deepEqual(errors, [], where + ": no script error");
        await page.close();
      }
      for (const [what, doc, lost] of [["the logo", IMG_LEAD, 59], ["the banner", BANNER_LEAD, 447], ["the banner after an <h1>", H1_BANNER, 444]] as const) {
        const where = `pane ${width}, ${what}, the picture's top 2px below the edge`;
        const { page, errors } = await openViewer(browser, "pane", width, 600, { docs: { [REPORT]: doc } }); await imagesDone(page);
        await page.evaluate(() => { const body = document.querySelector(".fileview-body")!; const i = document.querySelector(".fileview-md div > img")!; body.scrollTop += i.getBoundingClientRect().top - body.getBoundingClientRect().top - 2; }); await frames(page, 2);
        const before = await imgBox(page);
        near(before.top, 2, where + ": the scene starts with the picture's top 2px below the edge", 1);
        await click(page, "Raw");
        const row = (await rowAtTop(page))!;
        assert.ok(/^<div align|^<h1>/.test(row.text), where + `: the top Raw row is one of the wrapper's own before the tag row, the scene the way back reads from (got ${JSON.stringify(row.text)} at ${row.top})`);
        await click(page, "Rendered"); await imagesDone(page);
        const after = await imgBox(page);
        near(after.top, before.top, where + `: back in Rendered the picture is where it was (round 3: ${lost}px lost at 900)`);
        assert.deepEqual(errors, [], where + ": no script error");
        await page.close();
      }
      {
        const where = `pane ${width}, the <h1> 10px into the edge, the banner under it`;
        const { page, errors } = await openViewer(browser, "pane", width, 600, { docs: { [REPORT]: H1_BANNER } }); await imagesDone(page);
        await scrollInto(page, ".fileview-md div > h1", "Project", 10); await frames(page, 2);
        const h1 = (await box(page, ".fileview-md div > h1", "Project"))!;
        near(h1.top, -10, where + ": the scene starts with the <h1> 10px in", 1);
        const pic = await imgBox(page);
        assert.ok(pic.top > 20, where + `: the fixture: the banner starts below the <h1> (top ${pic.top})`);
        await click(page, "Raw");
        const imgRow = (await box(page, "code.hljs .fv-cl", "<img src="))!;
        near(imgRow.top, pic.top, where + ": the picture's tag row is where the picture was, the <h1>'s row and the opener above it (round 3: the nested paragraph at its distance below the banner, the write clamped at the document's top)");
        assert.deepEqual(errors, [], where + ": no script error");
        await page.close();
      }
    }
  });
});

// ── round 5: the picture through a run of blocks, the picture at the edge among several, a picture beside text, the row kept across a reflow, a commented tag ──
const LOGO_IMG = `<img src="${LOGO}" alt="logo" width="200" height="120">`;
/** the nested heading and paragraphs after the wrapper's own rows, the wrapper's end, paragraphs 9 to 25 */
const NESTED_TAIL = "\n\n## Centred title\n\n" + paras(6, 8) + "\n\n</div>\n\n" + paras(9, 25) + "\n";
const COMMENT_LEAD = "# Report\n\n" + paras(1, 5) + "\n\n<!-- project logo -->\n\n<div align=\"center\">\n" + LOGO_IMG + NESTED_TAIL;
const COMMENT_TIGHT = "# Report\n\n" + paras(1, 5) + "\n\n<!-- project logo -->\n<div align=\"center\">\n" + LOGO_IMG + NESTED_TAIL;
const CLOSER_LEAD = "# Report\n\n" + paras(1, 5) + "\n\n<div align=\"center\">\n\n" + paras(6, 7) + "\n\n</div>\n\n<div align=\"center\">\n" + LOGO_IMG + "\n\n## Centred title\n\n" + PARA(8) + "\n\n</div>\n\n" + paras(9, 25) + "\n";
const FOLD_CLOSER_LEAD = "# Report\n\n" + paras(1, 5) + "\n\n<details>\n<summary>More</summary>\n\nHidden text.\n\n</details>\n\n<div align=\"center\">\n" + LOGO_IMG + NESTED_TAIL;
const NEST2_LEAD = "# Report\n\n" + paras(1, 5) + "\n\n<div align=\"center\">\n\n<div>\n" + LOGO_IMG + "\n\n## Centred title\n\n" + paras(6, 8) + "\n\n</div>\n\n</div>\n\n" + paras(9, 25) + "\n";
const TINY = "data:image/svg+xml;utf8," + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24"><rect width="24" height="24" fill="tomato"/></svg>');
const badge = (n: string) => `<img src="${TINY}" alt="${n}" width="24" height="24">`;
/** an `<h1>`, a line of three 24px badges, the logo on the next line, then the nested heading: the badges and the logo share one line box */
const BADGES_LOGO = "# Report\n\n" + paras(1, 5) + "\n\n<div align=\"center\">\n<h1>Project</h1>\n" + badge("b1") + " " + badge("b2") + " " + badge("b3") + "\n" + LOGO_IMG + NESTED_TAIL;
/** the logo inside a centred `<p>` beside a line break and the project's name */
const P_IMG_LEAD = "# Report\n\n" + paras(1, 5) + "\n\n<div align=\"center\">\n<p align=\"center\">" + LOGO_IMG + "<br><b>Project</b></p>" + NESTED_TAIL;
/** a commented-out old tag on the line above the live one */
const COMMENTED_IMG = readme('<!-- <img src="old.svg" alt="old"> -->\n' + LOGO_IMG + "\n\n## Centred title");
const LONG_SUMMARY = "A rather long summary line that wraps onto several rows in a narrow pane, so that the title of the fold is tall enough to push the block after it well below the edge, and long enough again that the second and third rows wrap too at the wider pane";
const foldLong = (open: boolean) => "# Report\n\n" + paras(1, 10) + "\n\n<details" + (open ? " open" : "") + ">\n<summary>" + LONG_SUMMARY + "</summary>\n\n" + paras(11, 15) + "\n\n</details>\n\n" + paras(16, 30) + "\n";
/** The box of the picture whose alt is `alt`, from the body's top edge. */
const imgByAlt = (page: any, alt: string) => page.evaluate((a: string) => {
  const body = document.querySelector(".fileview-body")!; const br = body.getBoundingClientRect(); const r = (x: number) => Math.round(x * 10) / 10;
  const i = document.querySelector(`.fileview-md img[alt="${a}"]`)!.getBoundingClientRect();
  return { top: r(i.top - br.top), bottom: r(i.bottom - br.top), height: r(i.height), scrollTop: body.scrollTop };
}, alt);
/** Scroll so the picture whose alt is `alt` has its top `above` px above the body's top edge. */
const imgToEdge = (page: any, alt: string, above = 0) => page.evaluate(([a, x]: [string, number]) => {
  const body = document.querySelector(".fileview-body")!;
  const i = document.querySelector(`.fileview-md img[alt="${a}"]`)!;
  body.scrollTop += i.getBoundingClientRect().top - body.getBoundingClientRect().top + x;
}, [alt, above]);
/** One press of a text-size button, awaited through the seam's paint count (the reflow's own paint), never a timer. */
const sizeStep = async (page: any, label: string) => { const p: number = await page.evaluate(() => (window as any).__paints); await page.locator(`#romp-fileview button[aria-label="${label}"]`).click(); await paintsReach(page, p + 1); await frames(page, 3); };
/** The pane dragged to `width`: the viewport resized, the reflow's paint awaited. */
const dragTo = async (page: any, width: number) => { const p: number = await page.evaluate(() => (window as any).__paints); await page.setViewportSize({ width, height: 600 }); await paintsReach(page, p + 1); await frames(page, 3); };
/** near, with the tolerance a Raw row's whole-pixel snap scales to by the picture's height over the row's (test 3's idiom). */
const nearScaled = (a: number, b: number, what: string, picH: number, rowH: number) => near(a, b, what, Math.max(1.5, 0.5 * picH / rowH + 1));

test("in a browser, the real module: from Raw, a row that reads as the block after it through a RUN of blocks before the wrapper's (a comment's row before the opener, with and without a blank line between, the blank rows beside the comment, the `</div>` closing a wrapper right before a second one and the blank after it, the `</details>` of a shut fold before the opener, the outer opener of a wrapper two deep and the blanks beside it), at the top edge at 900 and 380px, switched to Rendered puts the wrapper's picture where its tag's row was, below the edge, the first nested block after the picture, and the way back returns the row in view; from the shut fold's closer the picture goes no lower than the fold's summary at the edge, the cap a block read through the closer keeps, and the row returns above the edge by the rows' excess over the summary's box (the review's round 5; round 4 asked the row's own block for the picture, so these rows carried nothing, the nested heading seated at its row's distance put the logo 4 to 22px above the edge at 900 and the row came back 44 to 59px above it, off the pane, where main kept it in view 72 to 82px low)", { timeout: 300000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const SCENES: Array<[string, string, string, number]> = [
      ["a comment's row before the opener", COMMENT_LEAD, "<!-- project logo", 0],
      ["the blank row before the comment", COMMENT_LEAD, "<!-- project logo", -1],
      ["the blank row between the comment and the opener", COMMENT_LEAD, "<!-- project logo", 1],
      ["a comment's row right above the opener", COMMENT_TIGHT, "<!-- project logo", 0],
      ["the `</div>` closing a wrapper before a second one", CLOSER_LEAD, "</div>", 0],
      ["the blank row after that `</div>`", CLOSER_LEAD, "</div>", 1],
      ["the `</details>` of a shut fold before the opener", FOLD_CLOSER_LEAD, "</details>", 0],
      ["the outer opener of a wrapper two deep", NEST2_LEAD, "<div align", 0],
      ["the blank row before the outer opener", NEST2_LEAD, "<div align", -1],
      ["the blank row between the two openers", NEST2_LEAD, "<div align", 1],
    ];
    for (const width of [900, 380]) {
      for (const [what, doc, text, offset] of SCENES) {
        const where = `pane ${width}, ${what}`;
        const { page, errors } = await openViewer(browser, "pane", width, 600, { docs: { [REPORT]: doc }, raw: true });
        await rowNearToEdge(page, text, offset); await frames(page, 2);
        const row0 = await rowNear(page, text, offset);
        near(row0.top, 0, where + `: the scene starts with the row at the edge (${JSON.stringify(row0.text)})`, 1);
        const imgRow0 = (await box(page, "code.hljs .fv-cl", "<img src="))!;
        assert.ok(imgRow0.top > 0, where + `: the fixture: the picture's tag row is below the edge (top ${imgRow0.top})`);
        await click(page, "Rendered"); await imagesDone(page);
        const pic = await imgBox(page);
        const nested = (await box(page, ".fileview-md div > h2", "Centred title"))!;
        assert.ok(nested.top > pic.bottom, where + `: the first nested block follows the picture (top ${nested.top}, the picture's bottom ${pic.bottom})`);
        if (doc === FOLD_CLOSER_LEAD) {
          // the shut fold right before the wrapper: the picture goes no lower than the fold's summary at the edge (the cap every block read
          // through a shut fold's closing row keeps; seated at its row's distance, 54px, the picture left paragraph 5's tail 24px under the edge
          // and the way back, that tail's fraction seat, brought the fold's five Raw rows back between, the closer 127px low), and the way back
          // returns the row above the edge by the Raw rows' excess over the summary's box, the recorded closing-row class
          const sum = (await box(page, ".fileview-md summary", "More"))!;
          near(sum.top, 0, where + `: the fold's summary is at the edge, the picture under it (top ${pic.top}; its row's distance, ${imgRow0.top}, would put paragraph 5's tail under the edge)`);
          await click(page, "Raw");
          const row1 = await rowNear(page, text, offset);
          near(row1.top, pic.top - imgRow0.top, where + `: the row is back above the edge by the three Raw rows' excess over the summary's box (round 4: 57px above it; main 198)`, 2);
        } else {
          near(pic.top, imgRow0.top, where + `: the picture's top is where its tag's row was, below the edge (round 4: the nested heading at its row's distance and the picture between the two, its top 4 to 22px above the edge at 900)`);
          await click(page, "Raw");
          const row1 = await rowNear(page, text, offset);
          assert.ok(row1.top > -1 && row1.top <= 65, where + `: the row is back in view, the tail of the paragraph before the wrapper low by its fraction, 41 to 59px measured at both widths (got ${row1.top}; round 4: 44 to 59px above the edge, off the pane; main 72 to 82px low)`);
        }
        assert.deepEqual(errors, [], where + ": no script error");
        await page.close();
      }
    }
  });
});

test("in a browser, the real module: a README header with three 24px badges and a 200x120 logo on consecutive source lines inside `<div align=\"center\">`, which the browser lays on ONE line box with a common baseline (the badges' tops 96px below the logo's while they come first in the DOM): Rendered to Raw to Rendered with the logo's top at the edge is exact at 900 and 380px, the logo's own tag row the top Raw row between (the review's round 5; rounds 3 and 4 carried the first picture in DOM order, the badges' line, so the Raw seat put the badges' row 96px down and the logo's 276 and the trip lost 129 to 130px; main refused these rows, 108 off); from Raw, the logo's tag row at the edge round-trips within 1.5px (before: 276 at 900 and 438 at 380 low), and from the badges' row too, as before, the badges at the edge and the logo above them", { timeout: 300000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    // the logo's top AT the edge only: 2px below it, the badges' data: URI row (180px at 900, 342 at 380) leaves a 2px tail above the logo's
    // row in Raw, which the way back reads by its fraction as it reads a paragraph's tail, the recorded class, here with a picture's row
    // (the badges' picture at 99% of its height above the edge, the logo 120px above it: measured -122 at both widths)
    for (const width of [900, 380]) {
      for (const above of [0]) {
        const where = `pane ${width}, the logo's top ${above ? "2px below" : "at"} the edge`;
        const { page, errors } = await openViewer(browser, "pane", width, 600, { docs: { [REPORT]: BADGES_LOGO } }); await imagesDone(page);
        const shape = await page.evaluate(() => { const r = (a: string) => document.querySelector(`.fileview-md img[alt="${a}"]`)!.getBoundingClientRect(); const l = r("logo"), b = r("b1"); return { dTop: Math.round(b.top - l.top), dBottom: Math.round(b.bottom - l.bottom), parent: document.querySelector('.fileview-md img[alt="logo"]')!.parentElement!.tagName }; });
        assert.deepEqual(shape, { dTop: 96, dBottom: 0, parent: "DIV" }, where + ": the fixture: the badges share the logo's line box, their tops 96px below its top, all rows of the div's block");
        await imgToEdge(page, "logo", above); await frames(page, 2);
        const before = await imgByAlt(page, "logo");
        near(before.top, -above, where + ": the scene starts with the logo at its place", 1);
        await click(page, "Raw");
        const row = (await rowAtTop(page))!;
        const logoRow = (await box(page, "code.hljs .fv-cl", 'alt="logo"'))!;
        assert.ok(row.text.startsWith("<img src=") && /alt="logo"/.test(await page.evaluate(() => { const body = document.querySelector(".fileview-body")!; const br = body.getBoundingClientRect(); for (const r of Array.from(body.querySelectorAll("code.hljs .fv-cl"))) { if (r.getBoundingClientRect().bottom > br.top + 0.5) return r.textContent || ""; } return ""; })), where + `: the LOGO's tag row is the top Raw row (got ${JSON.stringify(row.text)} at ${row.top}; before: the badges' row, the logo's ${Math.round(logoRow.top)}px down)`);
        near(logoRow.top, before.top, where + ": the logo's row at the logo's distance", 1.5);
        await click(page, "Rendered"); await imagesDone(page);
        const after = await imgByAlt(page, "logo");
        nearScaled(after.top, before.top, where + `: back in Rendered the logo is where it was (before: 129 to 130px low)`, before.height, logoRow.bottom - logoRow.top);
        assert.deepEqual(errors, [], where + ": no script error");
        await page.close();
      }
      for (const [what, alt] of [["the logo's tag row", "logo"], ["the badges' row", "b1"]] as const) {
        const where = `pane ${width}, from Raw, ${what} at the edge`;
        const { page, errors } = await openViewer(browser, "pane", width, 600, { docs: { [REPORT]: BADGES_LOGO }, raw: true });
        await rowToEdge(page, `alt="${alt}"`, 0); await frames(page, 2);
        const row0 = (await box(page, "code.hljs .fv-cl", `alt="${alt}"`))!;
        near(row0.top, 0, where + ": the scene starts on the row", 1);
        await click(page, "Rendered"); await imagesDone(page);
        const pic = await imgByAlt(page, alt);
        near(pic.top, 0, where + `: the picture of that row has its top at the edge${alt === "b1" ? ", the logo above it" : ", the badges 96px below it"}`, 1.5);
        await click(page, "Raw");
        const row1 = (await box(page, "code.hljs .fv-cl", `alt="${alt}"`))!;
        // within the picture's whole-pixel snap scaled by the row's height over the picture's (test 9's bound the other way round: the
        // badges' three data: URIs make a row of 180px at 900 and 342 at 380 against a 24px picture, so the snap reads back as 4px there)
        nearScaled(row1.top, row0.top, where + `: the row is back at the edge (before: ${alt === "logo" ? (width === 900 ? "276" : "438") + "px low, the badges' line read from Rendered" : "exact, as here"})`, row0.bottom - row0.top, pic.height);
        assert.deepEqual(errors, [], where + ": no script error");
        await page.close();
      }
    }
  });
});

test("in a browser, the real module: a README header whose logo sits inside a centred `<p>` beside a line break and the project's name (`<p align=\"center\"><img><br><b>Project</b></p>`) round-trips Rendered to Raw to Rendered with the picture's top at the edge, 2px below it and 48px into it at 900 and 380px, the `<p>`'s tag row the top Raw row at the picture's distance or fraction between, and from Raw the `<p>`'s row at the edge and 9px above it comes back within 1.5px, the picture at the row's fraction between (the review's round 5: the Rendered read refused a row holding text while the Raw read counted every tag, so the nested heading was seated at its distance and the way back seated the picture, 64 to 82px lost at 900; main 144 to 162 off)", { timeout: 300000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const width of [900, 380]) {
      for (const above of [0, -2, 48]) {
        const where = `pane ${width}, the picture's top ${above > 0 ? above + "px above" : above < 0 ? -above + "px below" : "at"} the edge`;
        const { page, errors } = await openViewer(browser, "pane", width, 600, { docs: { [REPORT]: P_IMG_LEAD } }); await imagesDone(page);
        const parent = await page.evaluate(() => { const i = document.querySelector('.fileview-md img[alt="logo"]')!; return { p: i.parentElement!.tagName, text: (i.parentElement!.textContent || "").trim(), grand: i.parentElement!.parentElement!.tagName }; });
        assert.deepEqual(parent, { p: "P", text: "Project", grand: "DIV" }, where + ": the fixture: the logo is inside the centred <p> with the name, a row of the div's block");
        await imgToEdge(page, "logo", above); await frames(page, 2);
        const before = await imgByAlt(page, "logo");
        near(before.top, -above, where + ": the scene starts with the picture at its depth", 1);
        await click(page, "Raw");
        const row = (await rowAtTop(page))!;
        assert.ok(row.text.startsWith('<p align="center"><img') || (above < 0 && row.text.startsWith("<div align")), where + `: the <p>'s tag row is the top Raw row, or the opener's tail above it when the picture is below the edge (got ${JSON.stringify(row.text)} at ${row.top}; before: the nested heading where it was, a paragraph before the wrapper or the opener on top)`);
        const pRow = (await box(page, "code.hljs .fv-cl", '<p align="center"><img'))!;
        const rowH = pRow.bottom - pRow.top;
        near(pRow.top, above > 0 ? -above * rowH / before.height : -above, where + `: the row at the picture's ${above > 0 ? "fraction of its height" : "distance"} (the row ${rowH}px tall)`, 1);
        await click(page, "Rendered"); await imagesDone(page);
        const after = await imgByAlt(page, "logo");
        nearScaled(after.top, before.top, where + `: back in Rendered the picture is where it was (before: ${above > 0 ? "82" : "64 to 65"}px low at 900)`, before.height, rowH);
        assert.deepEqual(errors, [], where + ": no script error");
        await page.close();
      }
      for (const above of [0, 9]) {
        const where = `pane ${width}, from Raw, the <p>'s row ${above}px above the edge`;
        const { page, errors } = await openViewer(browser, "pane", width, 600, { docs: { [REPORT]: P_IMG_LEAD }, raw: true });
        await rowToEdge(page, '<p align="center"><img', above); await frames(page, 2);
        const row0 = (await box(page, "code.hljs .fv-cl", '<p align="center"><img'))!;
        near(row0.top, -above, where + ": the scene starts on the row", 1);
        await click(page, "Rendered"); await imagesDone(page);
        const pic = await imgByAlt(page, "logo");
        const rowH = row0.bottom - row0.top;
        nearScaled(pic.top, -above * pic.height / rowH, where + ": the picture at the row's fraction of its height", pic.height, rowH);
        await click(page, "Raw");
        const row1 = (await box(page, "code.hljs .fv-cl", '<p align="center"><img'))!;
        near(row1.top, row0.top, where + `: the row is back where it was (before: ${width === 900 ? "82" : "9 to 11"}px low)`);
        assert.deepEqual(errors, [], where + ": no script error");
        await page.close();
      }
    }
  });
});

test("in a browser, the real module: a same-view reflow in RENDERED with a shown row of a wrapper's block's own at the top edge keeps that row (reader-place.ts Place.lead, the review's round 5): a fold title that wraps to three lines at 900px and six at 380, shut and open, at the edge and 10px into it, holds across a pane drag from 900 to 380 and back (at the edge within 1.5px; 10px in at the same fraction of its height), and from 380 to 900 and back; the Comments aside opening at 900 with the title at the edge holds it, and closing restores it; a text-size step (A+, then A-) holds it; a README's lead `<h1>` at the edge with the banner under it holds across A+ (round 4 kept the kept block's distance, the block after the shut fold or the first nested one, so the title's own growth landed above the edge: 90px on the drag to 380, 180 to 190 down after the drag back, 23 on the aside's open, 4.5 to 4.9 per step, 7.6 for the <h1>; before the slice the browser's own anchoring held every one within 0.2px)", { timeout: 300000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const summary = (page: any) => box(page, ".fileview-md summary", "A rather long");
    for (const open of [false, true]) {
      for (const at of [0, 10]) {
        const where = `${open ? "the open fold" : "the shut fold"}, the title ${at ? at + "px in" : "at the edge"}, pane 900`;
        const { page, errors } = await openViewer(browser, "pane", 900, 600, { docs: { [REPORT]: foldLong(open) } });
        await scrollInto(page, ".fileview-md summary", "A rather long", at); await frames(page, 2);
        const s0 = (await summary(page))!;
        near(s0.top, -at, where + ": the scene starts with the title at its place", 1);
        assert.ok(s0.bottom - s0.top > 60, where + `: the fixture: the title wraps (${s0.bottom - s0.top}px tall)`);
        await dragTo(page, 380);
        const s1 = (await summary(page))!;
        assert.ok(s1.bottom - s1.top > 1.5 * (s0.bottom - s0.top), where + `: the fixture: the title grew on the drag (${s0.bottom - s0.top} to ${s1.bottom - s1.top}px)`);
        near(s1.top, at ? s0.top * (s1.bottom - s1.top) / (s0.bottom - s0.top) : 0, where + `: after the drag to 380 the title is ${at ? "at its fraction of its height" : "at the edge"} (round 4: ${Math.round(s0.bottom - s0.top - (s1.bottom - s1.top))}px, its own growth above the edge)`);
        await dragTo(page, 900);
        const s2 = (await summary(page))!;
        near(s2.top, s0.top, where + ": after the drag back to 900 the title is where it was");
        assert.deepEqual(errors, [], where + ": no script error");
        await page.close();
      }
    }
    {
      const where = "the shut fold, the title at the edge, pane 380, dragged to 900 and back";
      const { page, errors } = await openViewer(browser, "pane", 380, 600, { docs: { [REPORT]: foldLong(false) } });
      await scrollInto(page, ".fileview-md summary", "A rather long", 0); await frames(page, 2);
      const s0 = (await summary(page))!;
      near(s0.top, 0, where + ": the scene starts with the title at the edge", 1);
      await dragTo(page, 900);
      near((await summary(page))!.top, 0, where + ": after the drag to 900 the title is at the edge (round 4: 90px down)");
      await dragTo(page, 380);
      near((await summary(page))!.top, 0, where + ": after the drag back the title is at the edge (round 4: 180 to 190px down)");
      assert.deepEqual(errors, [], where + ": no script error");
      await page.close();
    }
    {
      const where = "the shut fold, the title at the edge, pane 900, the Comments aside";
      const { page, errors } = await openViewer(browser, "pane", 900, 600, { docs: { [REPORT]: foldLong(false) } });
      await scrollInto(page, ".fileview-md summary", "A rather long", 0); await frames(page, 2);
      const s0 = (await summary(page))!;
      near(s0.top, 0, where + ": the scene starts with the title at the edge", 1);
      await openPanel(page);
      const s1 = (await summary(page))!;
      assert.ok(s1.bottom - s1.top > s0.bottom - s0.top + 10, where + `: the fixture: the title grew when the aside took its width (${s0.bottom - s0.top} to ${s1.bottom - s1.top}px)`);
      near(s1.top, 0, where + ": with the aside open the title is at the edge (round 4: 23px above it)");
      await closePanel(page);
      near((await summary(page))!.top, 0, where + ": with the aside closed the title is at the edge");
      assert.deepEqual(errors, [], where + ": no script error");
      await page.close();
    }
    {
      const where = "the shut fold, the title at the edge, pane 900, a text-size step";
      const { page, errors } = await openViewer(browser, "pane", 900, 600, { docs: { [REPORT]: foldLong(false) } });
      await scrollInto(page, ".fileview-md summary", "A rather long", 0); await frames(page, 2);
      near((await summary(page))!.top, 0, where + ": the scene starts with the title at the edge", 1);
      await sizeStep(page, "Larger text");
      near((await summary(page))!.top, 0, where + ": after A+ the title is at the edge (round 4: 4.5 to 4.9px above it)", 1);
      await sizeStep(page, "Smaller text");
      near((await summary(page))!.top, 0, where + ": after A- the title is at the edge", 1);
      assert.deepEqual(errors, [], where + ": no script error");
      await page.close();
    }
    {
      const where = "the <h1> lead with the banner under it, pane 900, a text-size step";
      const { page, errors } = await openViewer(browser, "pane", 900, 600, { docs: { [REPORT]: H1_BANNER } }); await imagesDone(page);
      await scrollInto(page, ".fileview-md div > h1", "Project", 0); await frames(page, 2);
      near((await box(page, ".fileview-md div > h1", "Project"))!.top, 0, where + ": the scene starts with the <h1> at the edge", 1);
      await sizeStep(page, "Larger text");
      near((await box(page, ".fileview-md div > h1", "Project"))!.top, 0, where + ": after A+ the <h1> is at the edge (round 4: 7.6px above it, the banner keeping its distance)", 1);
      await sizeStep(page, "Smaller text");
      near((await box(page, ".fileview-md div > h1", "Project"))!.top, 0, where + ": after A- the <h1> is at the edge", 1);
      assert.deepEqual(errors, [], where + ": no script error");
      await page.close();
    }
  });
});

test("in a browser, the real module: a commented-out `<img` tag on the line above the live one in a wrapper's block (`<!-- <img src=\"old.svg\"> -->`, a README's leftover) counts for no picture: Rendered to Raw with the logo's top at the edge puts the LIVE tag's row at the edge at 900 and 380px, the comment's row above it, and from Raw the opener's row at the edge switched to Rendered puts the logo where its tag's row was (the review's round 5; before, the comment's tag was counted, so the k-th picture took the tag before its own: the comment's row landed at the edge with the live row 18px below it, and from the opener the logo landed a row higher than its tag row)", { timeout: 300000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const width of [900, 380]) {
      {
        const where = `pane ${width}, Rendered to Raw with the logo at the edge`;
        const { page, errors } = await openViewer(browser, "pane", width, 600, { docs: { [REPORT]: COMMENTED_IMG } }); await imagesDone(page);
        assert.equal(await page.evaluate(() => document.querySelectorAll(".fileview-md img").length), 1, where + ": the fixture: one picture rendered (the comment makes none)");
        await imgToEdge(page, "logo", 0); await frames(page, 2);
        near((await imgBox(page)).top, 0, where + ": the scene starts with the logo's top at the edge", 1);
        await click(page, "Raw");
        const row = (await rowAtTop(page))!;
        assert.ok(row.text.startsWith("<img src="), where + `: the live tag's row is the top Raw row (got ${JSON.stringify(row.text)} at ${row.top}; before: the comment's row)`);
        near(row.top, 0, where + ": at the edge", 1.5);
        const comment = (await box(page, "code.hljs .fv-cl", "<!-- <img"))!;
        assert.ok(comment.bottom <= row.top + 0.5, where + `: the comment's row is above it (bottom ${comment.bottom})`);
        assert.deepEqual(errors, [], where + ": no script error");
        await page.close();
      }
      {
        const where = `pane ${width}, from Raw, the opener's row at the edge`;
        const { page, errors } = await openViewer(browser, "pane", width, 600, { docs: { [REPORT]: COMMENTED_IMG }, raw: true });
        await rowToEdge(page, "<div align", 0); await frames(page, 2);
        const liveRow = (await box(page, "code.hljs .fv-cl", 'alt="logo"'))!, commentRow = (await box(page, "code.hljs .fv-cl", "<!-- <img"))!;
        assert.ok(commentRow.top > 0 && liveRow.top > commentRow.top, where + `: the fixture: the comment's row (${commentRow.top}) then the live tag's (${liveRow.top}) below the edge`);
        await click(page, "Rendered"); await imagesDone(page);
        const pic = await imgBox(page);
        near(pic.top, liveRow.top, where + `: the logo's top is where the live tag's row was (before: where the comment's row was, ${Math.round(commentRow.top)})`);
        assert.deepEqual(errors, [], where + ": no script error");
        await page.close();
      }
    }
  });
});

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
import { inBrowser, openViewer, openPanel, frames, requireCjs, pageHtml, ORIGIN, UI, REPORT, SID, MT, STATUS, type Mode } from "./real-viewer-leg";
import { makeAnchor } from "./anchor-map";

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

// ── the Slice 5 review, round 2: a standalone <img> block with the panel OPEN, and the seeded inline-closer shape ──
const P3 = "Para 003 delta echo foxtrot golf.";
/** The notes: a lead-text div closed in the img's block, a fold closed in the img's block, a README's pictures, an <img> then
 *  a <div> in one block, and the seeded shape (a lead-text div closed inline on its only paragraph, then an img). */
const IMG_NOTES: Array<{ name: string; src: string; passages: string[]; imgBlock: string }> = [
  { name: "lead-text div, </div> and <img> in one block", src: `Intro.\n\n<div align="center">Lead 002 charlie.\n\n${P3}\n\n</div>\n<img src="c004.png" alt="c">\n\nAfter 005 hotel india.\n`, passages: [P3, "After 005 hotel india."], imgBlock: "</div>\n<img" },
  { name: "details, </details> and <img> in one block", src: `Intro.\n\n<details><summary>More</summary>\n\n${P3}\n\n</details>\n<img src="c004.png" alt="c">\n\nAfter 005 hotel india.\n`, passages: [P3, "After 005 hotel india."], imgBlock: "</details>\n<img" },
  { name: "a README: logo in the div, a screenshot, a fold, a demo", src: `<div align="center">\n<img src="logo.png" alt="logo">\n\nTag 002 line here.\n\n</div>\n\n<img src="shot.png" alt="s">\n\nIntro 003 text.\n\n<details>\n<summary>More</summary>\n\nHidden 005 text here.\n\n</details>\n\n<img src="demo.gif" alt="d">\n\nAfter 006 text.\n`, passages: ["Tag 002 line here.", "Intro 003 text.", "Hidden 005 text here.", "After 006 text."], imgBlock: "<img src=\"shot" },
  { name: "<img> then <div align=center> in one block", src: `<img src="logo.png" alt="l">\n<div align="center">\n\n# Head 003\n\n${P3.replace("003", "004")}\n\n</div>\n\nAfter 005 hotel india.\n`, passages: ["Head 003", P3.replace("003", "004"), "After 005 hotel india."], imgBlock: "<img src=\"logo" },
  { name: "the seeded shape: a lead-text div closed inline on its only paragraph, then an img", src: `<div align="center">Lead\n\n**Bold** </div>\n\n<img src="a.png" alt="x">\n\nAfter 005 hotel india.\n`, passages: ["Bold", "After 005 hotel india."], imgBlock: "<img src=\"a.png" },
];
const T0 = 1757145600000;
/** A comment in the host's shape on `quote` (its k-th occurrence 0) in `src`: the exact source slice, its context, its position. */
function commentOn(src: string, quote: string, k: number): Record<string, unknown> {
  const at = src.indexOf(quote);
  assert.ok(at >= 0, "the note holds " + JSON.stringify(quote));
  return { id: (T0 + k) + "-" + at, author: "you", ts: T0 + k, body: "Check this passage.", anchor: makeAnchor(src, { start: at, end: at + quote.length }), anchorAt: at, replies: [], resolved: false };
}
type Painted = { marks: number; text: string; card: boolean; goto: boolean };
/** In the page: the passage selected programmatically (a Selection-like over its first and last characters' text nodes) and mapped
 *  through the probe; the comment's marks and its card's Scroll link; the top-level tag names with their blocks. */
function readImgScene(args: { src: string; passages: string[]; ids: string[] }): { maps: Array<{ ok: boolean; reason?: string; range?: { start: number; end: number }; quote?: string }>; painted: Painted[]; tops: string[] } {
  const am = (window as any).__am;
  const md = document.querySelector(".fileview-md") as HTMLElement;
  const texts: Text[] = [];
  const w = document.createTreeWalker(md, NodeFilter.SHOW_TEXT);
  for (let t = w.nextNode(); t; t = w.nextNode()) texts.push(t as Text);
  const maps = args.passages.map((p) => {
    const si = texts.findIndex((t) => t.data.includes(p));
    if (si < 0) return { ok: false, reason: "not in the rendered text: " + p };
    const sNode = texts[si], sOff = sNode.data.indexOf(p);
    const sel = { anchorNode: sNode, anchorOffset: sOff, focusNode: sNode, focusOffset: sOff + p.length, isCollapsed: false };
    return am.mapRenderedSelection(sel, md, args.src);
  });
  const painted = args.ids.map((id) => {
    const marks = Array.from(md.querySelectorAll('.fc-hl[data-act="fcopen"][data-id="' + id + '"]')) as HTMLElement[];
    const card = document.querySelector('.fileview-aside .fc-card[data-id="' + id + '"]');
    return { marks: marks.length, text: marks.map((m) => m.textContent).join("").replace(/\s+/g, " ").trim(), card: !!card, goto: !!card && !!card.querySelector('[data-act="fcgoto"]') };
  });
  const tops = Array.from(md.children).map((k) => k.tagName + (k.classList.contains("fc-imgwrap") ? ".fc-imgwrap" : "") + "(" + am.renderedBlockIndex(md, args.src, k) + ")");
  return { maps, painted, tops };
}

test("in a browser, the real viewer and panel with the panel OPEN, so the regions layer has wrapped every <img> in its span: a standalone <img> block after a lead-text div (closed in the img's block), after a details fold, a README's logo, screenshot and demo pictures, an <img> then <div> block, and the seeded lead-text div closed inline on its only paragraph then an img: every nested passage maps to its own offsets and the comment served on it paints with a Scroll link (before: with the panel open the passage was refused as an HTML block at the img block's offset while it mapped with the panel closed, and its comment showed 0 marks and Reveal; the seeded shape's closer was refused at the img's offset with the panel open or closed)", { timeout: 300000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const probe = probeBundle();
    for (const scene of IMG_NOTES) {
      const comments = scene.passages.map((p, k) => commentOn(scene.src, p, k + 1));
      const status = { ...STATUS, store: { ...STATUS.store, comments }, storeMtimeNs: "17571456000000000" + (30 + comments.length) };
      const page = await browser.newPage({ viewport: { width: 900, height: 800 } });
      const errors: string[] = [];
      page.on("pageerror", (e: Error) => { errors.push(e.message); });
      const html = pageHtml("pane", { [REPORT]: scene.src }, MT);
      await page.route((u: URL) => u.href.startsWith(ORIGIN), (route: any) => route.fulfill({ status: 200, contentType: "text/html", body: html }));
      await page.goto(ORIGIN + "/");
      await page.evaluate(([p, sid, st]: [string, string, unknown]) => { (window as any).__status = st; (window as any).FV.openFileView(p, sid, null); }, [REPORT, SID, status]);
      await page.waitForFunction(() => !!document.querySelector(".fileview-md > p, .fileview-md > div"), null, { timeout: 10000 });
      await frames(page, 2);
      await page.addScriptTag({ content: probe });
      await openPanel(page);
      // the last passage's comment is the pass's sentinel: the paint is one pass over every card
      const last = comments[comments.length - 1].id as string;
      await page.waitForFunction((c: string) => !!document.querySelector('.fileview-aside .fc-card[data-id="' + c + '"]'), last, { timeout: 10000 });
      await frames(page, 3);
      const r = await page.evaluate(readImgScene, { src: scene.src, passages: scene.passages, ids: comments.map((c) => c.id as string) });
      assert.ok(r.tops.some((x: string) => x.startsWith("SPAN.fc-imgwrap(")), scene.name + ": the panel wrapped a top-level picture in its span: " + JSON.stringify(r.tops));
      const imgBlock = scene.src.indexOf(scene.imgBlock);
      assert.ok(imgBlock >= 0);
      scene.passages.forEach((p, i) => {
        const m = r.maps[i];
        assert.equal(m.ok, true, scene.name + ": " + JSON.stringify(p) + " maps with the panel open (before: refused at the img block's offset): " + JSON.stringify(m));
        assert.deepEqual(m.range, { start: scene.src.indexOf(p), end: scene.src.indexOf(p) + p.length }, scene.name + ": to its own offsets");
        assert.ok(r.painted[i].marks >= 1, scene.name + ": the comment on " + JSON.stringify(p) + " paints (before: 0 marks): " + JSON.stringify(r.painted[i]));
        assert.equal(r.painted[i].text, p, scene.name + ": the marks read the passage");
        assert.equal(r.painted[i].card && r.painted[i].goto, true, scene.name + ": its card offers Scroll to the passage (before: Reveal)");
      });
      assert.deepEqual(errors, [], scene.name + ": no script error");
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

// ── the Slice 5 review, round 3: the pairing shapes the round found, over the real viewer ──────────
const P003 = "Para 003 delta echo.", P004 = "Para 004 foxtrot golf.", A005 = "After 005 hotel india.", A006 = "After 006 juliet kilo.";
type R3Note = { name: string; src: string; passages: string[]; refused?: string[]; blocks?: Array<[string, string[]]> };
/** The notes: each passage must map to its own offsets; a `refused` passage must be refused as an HTML block; `blocks` are html blocks
 *  with the tag names of the elements they must own (the regions layer's span reads as IMG with the panel open; these legs keep it closed). */
const R3_NOTES: R3Note[] = [
  { name: "an open <p> then <br>, <img> and <span class=w> blocks, which nest in it, and a later top-level <img>", src: `<p>Lead 002 charlie.\n\n<br>\n\n<img src="a.png">\n\n<span class="w">\n\n${P003}\n\n${P004}\n\n<img src="b.png">\n\n${A005}\n\n${A006}\n`, passages: [P003, P004, A005, A006], blocks: [["<p>Lead", ["P"]], ["<br>", []], ["<img src=\"a.png\">", []], ["<span class", []], ["<img src=\"b.png\">", ["IMG"]]] },
  { name: "an open <p> then a markdown table, which nests in it in DOMPurify's quirks-mode document", src: `<p>Lead 002 charlie.\n\n| a | b |\n|---|---|\n| c | d |\n\n${A005}\n\n${A006}\n`, passages: [A005, A006], blocks: [["<p>Lead", ["P"]]] },
  { name: "two </p> blocks after an open <p>, then a heading, a paragraph, an image paragraph and a paragraph", src: `Intro 001 alpha bravo.\n\n<p>Lead 002 charlie.\n\n</p>\n\n</p>\n\n## Head 003 delta.\n\nPara 004 echo foxtrot.\n\n![pic](pic.png)\n\nAfter 005 golf hotel.\n`, passages: ["Head 003 delta.", "Para 004 echo foxtrot.", "After 005 golf hotel."], blocks: [["</p>", []], ["## Head", ["H2"]], ["![pic]", ["P"]]] },
  { name: "one </p> block after an open <p>, then the same", src: `Intro 001 alpha bravo.\n\n<p>Lead 002 charlie.\n\n</p>\n\n## Head 003 delta.\n\nPara 004 echo foxtrot.\n\n![pic](pic.png)\n\nAfter 005 golf hotel.\n`, passages: ["Head 003 delta.", "Para 004 echo foxtrot.", "After 005 golf hotel."] },
  { name: "a README's centred <p> of a picture closed by its own </p> block, then prose and an image paragraph", src: `<p align="center">\n<img src="logo.png" alt="">\n\n</p>\n\n## Head 003 delta.\n\nPara 004 echo foxtrot.\n\n![pic](pic.png)\n\nAfter 005 golf hotel.\n`, passages: ["Head 003 delta.", "Para 004 echo foxtrot.", "After 005 golf hotel."] },
  { name: "a wrapper whose raw holds a closed child of the next html block's tag", src: `Intro 001 alpha bravo.\n\n<div align="center"><div>Lead 002 charlie.</div>\n\n<div class="in">\n\n${P003}\n\n</div>\n\n</div>\n\nAfter 004 foxtrot golf.\n\n${A005}\n`, passages: [P003, "After 004 foxtrot golf.", A005], blocks: [["<div class=\"in\">", ["DIV"]]] },
  { name: "a <label> closed inline on its paragraph (the parser ignores the closer), then an html <p></p> block", src: `Intro 001 alpha bravo.\n\n<label>\n\n${P003} </label>\n\n<p></p>\n\n${A005}\n\n${A006}\n`, passages: [P003, A005, A006], blocks: [["<p></p>", ["P"]]] },
  { name: "a <button> opener whose paragraph's own <button> closes it, then a <div> block and paragraphs", src: `Intro one here.\n\n<button>\n\n<button>probe xray quebec</button>\n\nNovember table bravo.\n\nLast line kilo.\n\n<div>marker</div>\n\nAfter one lima.\n\nAfter two mike.\n`, passages: ["After one lima.", "After two mike."], refused: ["November table bravo."], blocks: [["<div>marker", ["DIV"]]] },
  // the review's round 6: the node leg's `<p>` scene (anchor-map-wrappers.test.ts test 37) over the real parser, which mints the
  // unwrapped button opener's `<p></p>` pair as the stand-in does; the `<p></p>` block owns its OWN element alone and the dropped note's
  // block, the swallower, owns the run's four (nextAnchor's by-tag candidate is confirmed by the blocks after it lining up, so the
  // run's minted `<p></p>` is passed over; before the round the `<p>` block took it and owned the run, the note's block nothing)
  { name: "a <tr><td> note the parser drops, a <button> opener, then an html <p></p> block and paragraphs", src: `Intro one here.\n\n<tr><td>xray golf juliet.</td></tr>\n\n<button>\n\n<button>probe xray quebec</button>\n\nNovember table bravo.\n\nLast line kilo.\n\n<p></p>\n\nAfter one lima.\n\nAfter two mike.\n`, passages: ["After one lima.", "After two mike."], refused: ["November table bravo.", "Last line kilo."], blocks: [["<p></p>", ["P"]], ["<tr>", ["P", "P", "P", "P"]], ["<button>", []]] },
  // the review's round 6: an unwrapped kid that leaves an ELEMENT before the depth-1 wrapper (a `<button>` holding a badge picture): the
  // unwrap leaves the picture where the button stood, the opener's block owns the outer div, the badge and the inner div, and the nested
  // paragraph and the one after the wrapper map (before the round: the button was listed by name and read as its text, the picture was
  // left at k unread, the inner wrapper was not found and the nested paragraph was refused as a mismatch)
  { name: "a centred div whose raw holds a <button> around a badge picture before its inner <div> wrapper", src: `<div align="center"><button><img src="badge.svg" alt="b"></button><div>\n\nAlpha para one.\n\n</div></div>\n\nAfter para two.\n`, passages: ["Alpha para one.", "After para two."], blocks: [["<div align", ["DIV", "IMG", "DIV"]]] },
  // the review's round 7: an element the parser closes implicitly at the unwrapped element's END tag (a `<p>` left open in a `<form>`,
  // the `<option>`s of a `<select>` written without their end tags) is listed among the wrapper's kids, so the depth-1 wrapper is found
  // past it (before the round the kid list held only the children closed by name, the `<p>` stood at k where the inner div was expected,
  // the nested paragraph was refused as a mismatch and the paragraph after could not be matched; 701728eae mapped both)
  { name: "a centred div whose raw holds a <form> with an open <p> before its inner <div> wrapper", src: `<div align="center"><form><p>Lead mp1</form><div>\n\nAlpha para one.\n\n</div></div>\n\nAfter para two.\n`, passages: ["Alpha para one.", "After para two."], blocks: [["<div align", ["DIV", "P", "DIV"]]] },
  { name: "a centred div whose raw holds a <label> with an open <p> (the parser ignores the label's end tag) before its inner <div> wrapper", src: `<div align="center"><label><p>Lead mp1</label><div>\n\nAlpha para one.\n\n</div></div>\n\nAfter para two.\n`, passages: ["Alpha para one.", "After para two."], blocks: [["<div align", ["DIV", "P", "DIV"]]] },
  { name: "a centred div whose raw holds a <select> with two options written without end tags before its inner <div> wrapper", src: `<div align="center"><select><option>a<option>b</select><div>\n\nAlpha para one.\n\n</div></div>\n\nAfter para two.\n`, passages: ["Alpha para one.", "After para two."], blocks: [["<div align", ["DIV", "DIV"]]] },
  // the parser's own rule for `</form>`: the form alone is removed from the stack and a `<span>` left open inside it stays open, so the
  // inner div nests in the span and the opener's block holds three wrappers (before the round the span was read as closed with the form)
  { name: "a div whose raw holds a <form> closed with a <span> still open before its inner <div> wrapper", src: `<div><form>Lead<span>x</form><div>\n\nAlpha para one.\n\n</div></div>\n\nAfter para two.\n`, passages: ["Alpha para one.", "After para two."], blocks: [["<div>", ["DIV", "SPAN", "DIV"]]] },
  // the review's round 7: after a `<button>` opener's run and a `</center>` alone, a tail whose SECOND paragraph the sanitizer shortened
  // (`Weird <style>x{}</style> line.`): the run check's lookahead reads the one mismatch before two confirmations, so the other tail
  // paragraphs map to their own offsets and the button's block owns the run's four (before the round the swallow ran to the document's
  // end and every tail paragraph was refused as an HTML block at the button's offset; main mapped the three)
  { name: "a <button> opener's run, a </center> alone, then a tail whose second paragraph the sanitizer shortened", src: `Intro alpha bravo charlie.\n\n<button>\n\n<button>probe xray</button>\n\nNovember tango sierra.\n\nLast kilo lima.\n\n</center>\n\nNote tango sierra.\n\nWeird <style>x{}</style> line.\n\nFinal para after tail.\n\nAfter all done.\n`, passages: ["Note tango sierra.", "Final para after tail.", "After all done."], refused: ["November tango sierra.", "Last kilo lima."], blocks: [["<button>", ["P", "P", "P", "P"]]] },
];
type R3Read = { maps: any[]; refusedMaps: any[]; blocks: string[][]; painted: Painted[]; tops: string[] };
/** In the page: each passage mapped through the probe from a Selection-like over the text nodes holding its head and its tail (a paint
 *  may have split it), the named blocks' elements, the comments' marks and cards, and the top-level tags. */
function readR3(args: { src: string; passages: string[]; refused: string[]; ids: string[]; blocks: string[] }): R3Read {
  const am = (window as any).__am;
  const md = document.querySelector(".fileview-md") as HTMLElement;
  const texts: Text[] = [];
  const w = document.createTreeWalker(md, NodeFilter.SHOW_TEXT);
  for (let t = w.nextNode(); t; t = w.nextNode()) texts.push(t as Text);
  const mapP = (p: string) => {
    // the text node holding the passage whole, else (a paint split it) the first holding the longest head some node holds, the tail
    // found from there
    let head = p, si = -1;
    for (const len of [p.length, 12, 8]) { head = p.slice(0, Math.min(len, p.length)); si = texts.findIndex((t) => t.data.includes(head)); if (si >= 0) break; }
    const tail = p.slice(-Math.min(8, p.length));
    if (si < 0) return { ok: false, reason: "not in the rendered text: " + p };
    const s = texts[si], sOff = s.data.indexOf(head);
    for (let i = si; i < texts.length; i++) {
      const j = texts[i].data.indexOf(tail, i === si ? sOff : 0);
      if (j >= 0) return am.mapRenderedSelection({ anchorNode: s, anchorOffset: sOff, focusNode: texts[i], focusOffset: j + tail.length, isCollapsed: false }, md, args.src);
    }
    return { ok: false, reason: "the tail is not in the rendered text after the head: " + p };
  };
  const spans: Array<{ start: number; end: number }> = am.sourceBlockSpans(args.src);
  const blocks = args.blocks.map((head) => { const b = spans.findIndex((sp) => args.src.slice(sp.start, sp.end).startsWith(head)); return b < 0 ? ["no block " + head] : (am.renderedBlockElements(md, args.src, b) as Element[]).map((e) => e.classList.contains("fc-imgwrap") ? "IMG" : e.tagName); });
  const painted = args.ids.map((id) => {
    const marks = Array.from(md.querySelectorAll('.fc-hl[data-act="fcopen"][data-id="' + id + '"]')) as HTMLElement[];
    const card = document.querySelector('.fileview-aside .fc-card[data-id="' + id + '"]');
    return { marks: marks.length, text: marks.map((m) => m.textContent).join("").replace(/\s+/g, " ").trim(), card: !!card, goto: !!card && !!card.querySelector('[data-act="fcgoto"]') };
  });
  return { maps: args.passages.map(mapP), refusedMaps: args.refused.map(mapP), blocks, painted, tops: Array.from(md.children).map((k) => k.tagName) };
}

test("in a browser, the real viewer: the pairing shapes the review's round 3 found, each a regression from main or from round 1, map over the real DOM: an open html <p> that <br>, <img> and <span> blocks nest in (and a table, in DOMPurify's quirks-mode document), a stray </p> that closes such a p, a wrapper's own same-tag child before the next html block, a <label>'s ignored inline closer before an html <p></p>, and a <button> opener whose paragraph's own <button> closes it, then a <div> block, or after a dropped <tr><td> note then an html <p></p> block (every passage after the next html block maps, the ones inside its run refused as an HTML block at the note's block, the <p></p> block owning its own element alone), and the review's round 6's centred div holding a <button> around a badge picture before its inner wrapper (the nested paragraph and the one after map, the opener's block owning the outer div, the badge and the inner div)", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const probe = probeBundle();
    for (const note of R3_NOTES) {
      const { page, errors } = await openViewer(browser, "pane", 900, 800, { docs: { [REPORT]: note.src } });
      await page.addScriptTag({ content: probe });
      const r: R3Read = await page.evaluate(readR3, { src: note.src, passages: note.passages, refused: note.refused || [], ids: [], blocks: (note.blocks || []).map(([h]) => h) });
      note.passages.forEach((p, i) => {
        assert.equal(r.maps[i].ok, true, note.name + ": " + JSON.stringify(p) + " maps: " + JSON.stringify(r.maps[i]) + " (tops " + JSON.stringify(r.tops) + ")");
        assert.deepEqual(r.maps[i].range, { start: note.src.indexOf(p), end: note.src.indexOf(p) + p.length }, note.name + ": " + JSON.stringify(p) + " to its own offsets");
      });
      (note.refused || []).forEach((p, i) => { assert.equal(r.refusedMaps[i].ok, false, note.name + ": " + JSON.stringify(p) + " is refused"); assert.match(r.refusedMaps[i].reason, /an HTML block/, note.name + ": " + JSON.stringify(p)); });
      (note.blocks || []).forEach(([head, tags], i) => assert.deepEqual(r.blocks[i], tags, note.name + ": the block " + JSON.stringify(head) + " owns " + JSON.stringify(tags)));
      assert.deepEqual(errors, [], note.name + ": no script error");
      await page.close();
    }
  });
});

test("in a browser, the real viewer and panel: a comment on a wrapper's own leftover (a details' summary, a centred div's lead line, a README banner's tagline and heading) paints with a Scroll link (HIGH, the review's round 3: the fallback counted the passage twice against the block's rendering once and refused; main painted each); and a comment spanning from the paragraph before a <form>'s lead into its nested paragraph, served before a fresh open, paints, after which every passage still maps (the run check reads the mark over the hoisted lead as that text; before: every later selection refused as an HTML block at the dropped <tr> block)", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const probe = probeBundle();
    const LEFTOVERS = `Intro 001 alpha.\n\n<details><summary>Sum 002 charlie.</summary>\n\n${P003}\n\n</details>\n\n<details>\n<summary>Click to expand</summary>\n\nHidden 004 text here.\n\n</details>\n\n<div align="center">Lead 005 bravo.\n\nPara 006 golf hotel.\n\n</div>\n\n<div align="center"><img src="logo.png" alt="logo"><h1>Project</h1><p>A tagline here.</p>\n\nIntro 007 text.\n\n</div>\n\nAfter 008 foxtrot.\n`;
    const HOIST = `Intro 001 alpha bravo.\n\n<tr><td>Cell 002 charlie.</td></tr>\n\n${P003}\n\n<form>Lead 004 foxtrot.\n\nPara 005 golf hotel.\n\nPara 006 india juliet. </form>\n\nAfter 007 kilo lima.\n\nAfter 008 mike november.`;
    const scenes: Array<{ name: string; src: string; quotes: Array<{ q: string; text: string }>; passages: string[] }> = [
      { name: "leftovers", src: LEFTOVERS, quotes: [{ q: "Sum 002 charlie.", text: "Sum 002 charlie." }, { q: "Click to expand", text: "Click to expand" }, { q: "Lead 005 bravo.", text: "Lead 005 bravo." }, { q: "A tagline here.", text: "A tagline here." }, { q: "Project", text: "Project" }, { q: P003, text: P003 }, { q: "After 008 foxtrot.", text: "After 008 foxtrot." }], passages: [P003, "Hidden 004 text here.", "Para 006 golf hotel.", "Intro 007 text.", "After 008 foxtrot."] },
      { name: "a span into the form's lead", src: HOIST, quotes: [{ q: "delta echo.\n\n<form>Lead 004 foxtrot.\n\nPara 005", text: "delta echo. Lead 004 foxtrot. Para 005" }, { q: "After 008 mike november.", text: "After 008 mike november." }], passages: [P003, "Para 005 golf hotel.", "Para 006 india juliet.", "After 007 kilo lima.", "After 008 mike november."] },
    ];
    for (const scene of scenes) {
      const comments = scene.quotes.map(({ q }, k) => commentOn(scene.src, q, k + 1));
      const status = { ...STATUS, store: { ...STATUS.store, comments }, storeMtimeNs: "17571456000000000" + (50 + comments.length) };
      const page = await browser.newPage({ viewport: { width: 900, height: 800 } });
      const errors: string[] = [];
      page.on("pageerror", (e: Error) => { errors.push(e.message); });
      const html = pageHtml("pane", { [REPORT]: scene.src }, MT);
      await page.route((u: URL) => u.href.startsWith(ORIGIN), (route: any) => route.fulfill({ status: 200, contentType: "text/html", body: html }));
      await page.goto(ORIGIN + "/");
      await page.evaluate(([p, sid, st]: [string, string, unknown]) => { (window as any).__status = st; (window as any).FV.openFileView(p, sid, null); }, [REPORT, SID, status]);
      await page.waitForFunction(() => !!document.querySelector(".fileview-md > p, .fileview-md > div, .fileview-md > details"), null, { timeout: 10000 });
      await frames(page, 2);
      await page.addScriptTag({ content: probe });
      await openPanel(page);
      const last = comments[comments.length - 1].id as string;
      await page.waitForFunction((c: string) => !!document.querySelector('.fileview-body [data-act="fcopen"][data-id="' + c + '"]'), last, { timeout: 10000 });
      await frames(page, 3);
      const r: R3Read = await page.evaluate(readR3, { src: scene.src, passages: scene.passages, refused: [], ids: comments.map((c) => c.id as string), blocks: [] });
      scene.quotes.forEach(({ q, text }, i) => {
        assert.ok(r.painted[i].marks >= 1, scene.name + ": the comment on " + JSON.stringify(q) + " paints (before: 0 marks): " + JSON.stringify(r.painted[i]));
        assert.equal(r.painted[i].text.replace(/\s+/g, ""), text.replace(/\s+/g, ""), scene.name + ": the marks read the passage");
        assert.equal(r.painted[i].card && r.painted[i].goto, true, scene.name + ": its card offers Scroll (before: Reveal)");
      });
      scene.passages.forEach((p, i) => {
        assert.equal(r.maps[i].ok, true, scene.name + ": " + JSON.stringify(p) + " maps with the comments painted: " + JSON.stringify(r.maps[i]));
        assert.deepEqual(r.maps[i].range, { start: scene.src.indexOf(p), end: scene.src.indexOf(p) + p.length }, scene.name + ": " + JSON.stringify(p) + " to its own offsets");
      });
      assert.deepEqual(errors, [], scene.name + ": no script error");
      await page.close();
    }
  });
});

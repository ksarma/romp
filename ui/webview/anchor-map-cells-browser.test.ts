// A table cell commented from the Rendered view, over the REAL viewer and the REAL Comments panel in headless Chromium
// (plans/markdown-viewer.md, Slice 8, items 1 and 3; acceptance: a comment on a cell made from Rendered paints in both views
// after a reload, and a selection spanning two cells is refused with the reason named). The synthetic fixture
// anchor-map-fixtures/wrappers-plain.md (the Slice 5 probe's, read-only) is opened in the RENDERED view through
// real-viewer-leg.ts, on the Files pane at 900 and 380 px and in the chat modal, and a REAL mouse drag selects `cell one` in
// its `<td>`: the panel's mouseup offers the Comment float, its click opens the composer quoting `cell one` with Save, the
// save posts the exact source slice with the cell's offset as the hint (the anchor the host stores byte for byte), the mark
// stands inside that `<td>` once the store answers, and a switch to Raw shows the same comment's mark on the table's row.
// The same comment served before a fresh open paints in both views. Then a drag from `cell one` into `cell two` is refused
// with the one-cell sentence, the Raw button promising the passage, and Switch to Raw preselects `cell one | cell two` on the
// row with the composer quoting it and Save offered. Before this slice the probe (the Slice 5 report's section (j)) recorded
// the cell drag refused as "touches a table" with the Raw view preselecting the cell after the switch, and the two-cell drag
// refused with no preselect. The table's width is read before and after the cell's mark paints, for the build note (the
// brief's open question 15). A last leg times the index, one map and forty marks over a 1,000-row table for the build note
// (the brief's open question 13; diagnostics, not a bound). A leg of the Slice 8 review's round 1 serves a table whose hole cell
// holds an emoji beside an entity (an astral character the per-cell fallback shows): the served comment and deletion point on
// later cells land in their own cells and a real drag's Save posts the exact slice, where the build's head, counting a hole's
// characters by code point, shifted every later cell of the table by one code unit and stored a quote spanning the pipe into
// the next row. A leg of the review's round 4 serves a table whose header row is two formulas alone over the REAL KaTeX fill:
// a real drag from the paragraph before the table to past the second header formula's glyphs is refused with the one-cell
// sentence and Switch to Raw preselects `$h$ | $k$`, the table's covered cells (before: the composer quoted `Intro para. |
// $h$ | $k$` with Save, the pipe between two cells inside a Rendered quote, since a cell holding a formula alone had no record
// and the count never saw two), while a drag to past the first formula's glyphs maps `Intro para.\n\n| $h$`, one cell and the
// prose before it. A leg of the review's round 5 serves a note with a table whose last body cell is a picture alone and one whose
// last body cell is a formula alone (the real KaTeX fill): a real drag from the positioned cell beside either into the paragraph
// after the table is refused with the one-cell sentence and Switch to Raw preselects the two cells, `pl-a | ![p](x.png)` and
// `fl-a | $n$` (before: the composer quoted the cells with the pipe and the prose after them, Save offered, and the save posted
// that quote, since a cell that emits no positioned character was counted only through a formula at the drag's end), while a
// drag over the positioned cell alone maps it. Skips LOUDLY without a playwright browser (CI installs none), as the other browser
// legs do. Synthetic values only: an invented note, /repo/notes-api paths, the placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { inBrowser, openPanel, openViewer, frames, pageHtml, requireCjs, ORIGIN, REPORT, SID, MT, STATUS, UI, EXT, type Mode } from "./real-viewer-leg";
import { makeAnchor } from "./anchor-map";

const PLAIN = fs.readFileSync(path.join(UI, "anchor-map-fixtures", "wrappers-plain.md"), "utf8");
const T0 = 1757145600000;
const NOTE = "Check this cell against the spec.";
const CELL_Q = "cell one";
const ROW_Q = "cell one | cell two";
const FINAL_Q = "Final paragraph here.";
const ONE_CELL = "This selection spans more than one cell of a table; select within one cell, or comment on it from the Raw view.";

/** A comment in the host's shape on the fixture's passage `quote`: the exact source slice, its context, its position. */
function comment(quote: string, k: number): Record<string, unknown> {
  const at = PLAIN.indexOf(quote);
  assert.ok(at >= 0, "the fixture holds " + JSON.stringify(quote));
  return { id: (T0 + k) + "-" + at, author: "you", ts: T0 + k, body: NOTE, anchor: makeAnchor(PLAIN, { start: at, end: at + quote.length }), anchorAt: at, replies: [], resolved: false };
}
const FINAL = comment(FINAL_Q, 1);
const CELL = comment(CELL_Q, 2);
const id = (c: Record<string, unknown>): string => c.id as string;
/** The kernel's status with `comments` in the store, `n` bumping the store's mtime so each reply reads as a new write. */
const withComments = (comments: Record<string, unknown>[], n: number): Record<string, unknown> =>
  ({ ...STATUS, store: { ...STATUS.store, comments }, storeMtimeNs: "17571456000000000" + (40 + n), unsent: { comments: [], replies: [], accepted: 0, rejected: 0, watermark: null } });

/** The page: the fixture open in the Rendered view, `status` served before the open, the panel open, the sentinel's mark painted. */
async function openWith(browser: any, mode: Mode, width: number, status: Record<string, unknown>): Promise<{ page: any; errors: string[] }> {
  const page = await browser.newPage({ viewport: { width, height: 700 } });
  const errors: string[] = [];
  page.on("pageerror", (e: Error) => { errors.push(e.message); });
  const html = pageHtml(mode, { [REPORT]: PLAIN }, MT);
  await page.route((u: URL) => u.href.startsWith(ORIGIN), (route: any) => route.fulfill({ status: 200, contentType: "text/html", body: html }));
  await page.goto(ORIGIN + "/");
  await page.evaluate(([p, sid, st]: [string, string, unknown]) => { (window as any).__status = st; (window as any).FV.openFileView(p, sid, null); }, [REPORT, SID, status]);
  await page.waitForFunction(() => !!document.querySelector(".fileview-md > p"), null, { timeout: 10000 });
  await frames(page, 2);
  await openPanel(page);
  await markPainted(page, id(FINAL));
  return { page, errors };
}
/** Wait for the comment's highlight in the view's body (the pass painted it). */
const markPainted = (page: any, cid: string): Promise<unknown> =>
  page.waitForFunction((c: string) => !!document.querySelector('.fileview-body [data-act="fcopen"][data-id="' + c + '"]'), cid, { timeout: 10000 });

type Points = { sx: number; sy: number; ex: number; ey: number; selected: string };
/** In the page: the boxes of the passage's first and last characters under `rootSel`, its start scrolled to the body's middle first. */
function pointsIn(spec: { rootSel: string; start: string; end: string }): Points {
  const root = document.querySelector(spec.rootSel) as HTMLElement;
  const texts: Text[] = [];
  const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  for (let t = w.nextNode(); t; t = w.nextNode()) texts.push(t as Text);
  const si = texts.findIndex((t) => t.data.includes(spec.start));
  if (si < 0) throw new Error("start not in the view's text: " + spec.start);
  const sNode = texts[si], sOff = sNode.data.indexOf(spec.start);
  let eNode: Text | null = null, eOff = -1;
  for (let i = si; i < texts.length && !eNode; i++) { const j = texts[i].data.indexOf(spec.end, i === si ? sOff : 0); if (j >= 0) { eNode = texts[i]; eOff = j + spec.end.length; } }
  if (!eNode) throw new Error("end not in the view's text after the start: " + spec.end);
  (sNode.parentElement as HTMLElement).scrollIntoView({ block: "center" });
  const rect = (n: Text, off: number) => { const r = document.createRange(); r.setStart(n, off); r.setEnd(n, off + 1); return r.getBoundingClientRect(); };
  const a = rect(sNode, sOff), b = rect(eNode, eOff - 1);
  const whole = document.createRange(); whole.setStart(sNode, sOff); whole.setEnd(eNode, eOff);
  return { sx: a.left + Math.min(1.5, a.width / 3), sy: a.top + a.height / 2, ex: b.right - Math.min(1.5, b.width / 3), ey: b.top + b.height / 2, selected: whole.toString() };
}
/** Select the passage in the Rendered view with a real drag over its first and last characters' boxes. */
async function dragRendered(page: any, start: string, end: string): Promise<string> {
  await page.evaluate(() => { getSelection()!.removeAllRanges(); });
  const pts: Points = await page.evaluate(pointsIn, { rootSel: ".fileview-md", start, end });
  await frames(page, 1);
  await page.mouse.move(pts.sx, pts.sy);
  await page.mouse.down();
  await page.mouse.move((pts.sx + pts.ex) / 2, (pts.sy + pts.ey) / 2, { steps: 3 });
  await page.mouse.move(pts.ex, pts.ey, { steps: 6 });
  await page.mouse.up();
  await frames(page, 2);
  return page.evaluate(() => String(getSelection()));
}
type ComposerState = { open: boolean; refused: string | null; rawTitle: string | null; quote: string | null; save: boolean | null; raw: boolean };
/** The composer as the panel shows it: the refusal line, the Raw button's title, the quote, whether Save is offered. */
const composerState = (page: any): Promise<ComposerState> => page.evaluate(() => {
  const box = document.querySelector(".fc-composer") as HTMLElement | null;
  if (!box || !document.contains(box) || box.getClientRects().length === 0) return { open: false, refused: null, rawTitle: null, quote: null, save: null, raw: false };
  const sw = box.querySelector('[data-act="fcraw"]') as HTMLElement | null;
  const save = box.querySelector('[data-act="fcsave"]') as HTMLButtonElement | null;
  return { open: true, refused: box.querySelector(".fc-refused")?.textContent ?? null, rawTitle: sw ? sw.title : null, quote: box.querySelector(".fc-quote")?.textContent ?? null, save: save ? !save.disabled : null, raw: !!sw };
});
const floatShown = (page: any): Promise<unknown> => page.waitForFunction(() => { const f = document.querySelector(".fc-float") as HTMLElement | null; return !!f && !f.hidden; }, null, { timeout: 5000 });
/** The float's click, the note typed, the save; the harness answers with `next`, whose new comment's card and mark are awaited. */
async function saveComment(page: any, c: Record<string, unknown>, next: Record<string, unknown>): Promise<void> {
  await page.keyboard.type(NOTE);
  await page.evaluate((st: unknown) => { (window as any).__status = st; }, next);
  await page.click('.fileview-aside [data-act="fcsave"]');
  await page.waitForFunction((cid: string) => !!document.querySelector('.fileview-aside .fc-card[data-id="' + cid + '"]'), id(c), { timeout: 10000 });
  await markPainted(page, id(c));
  await frames(page, 2);
}
const posted = (page: any): Promise<any[]> => page.evaluate(() => (window as any).__posted);

type CellRead = { marks: number; text: string; cell: { tag: string; index: number; row: number } | null; tableWidth: number };
/** The comment's marks in the Rendered view: their count, their text, the cell and row the first stands in, and the table's width. */
const readCell = (page: any, cid: string): Promise<CellRead> => page.evaluate((c: string) => {
  const md = document.querySelector(".fileview-md") as HTMLElement;
  const marks = Array.from(md.querySelectorAll('.fc-hl[data-act="fcopen"][data-id="' + c + '"]')) as HTMLElement[];
  const m = marks[0];
  const td = m ? m.closest("td, th") : null;
  const tr = td ? td.parentElement as HTMLElement : null;
  const tbody = tr ? tr.parentElement as HTMLElement : null;
  const table = md.querySelector("table") as HTMLElement;
  return {
    marks: marks.length, text: marks.map((x) => x.textContent).join(" ").replace(/\s+/g, " ").trim(),
    cell: td && tr && tbody ? { tag: td.tagName, index: Array.from(tr.children).indexOf(td), row: Array.from(tbody.children).indexOf(tr) } : null,
    tableWidth: table ? table.getBoundingClientRect().width : -1,
  };
}, cid);
const tableWidth = (page: any): Promise<number> => page.evaluate(() => { const t = document.querySelector(".fileview-md table") as HTMLElement | null; return t ? t.getBoundingClientRect().width : -1; });
/** The comment's marks in the Raw view: their count and the text of the row the first stands on. */
const readRaw = (page: any, cid: string): Promise<{ marks: number; row: string; text: string }> => page.evaluate((c: string) => {
  const body = document.querySelector(".fileview-body") as HTMLElement;
  const marks = Array.from(body.querySelectorAll('.fc-hl[data-act="fcopen"][data-id="' + c + '"]')) as HTMLElement[];
  const row = marks[0] ? marks[0].closest(".fv-cl") : null;
  return { marks: marks.length, row: row ? (row.textContent || "").trim() : "", text: marks.map((m) => m.textContent).join("") };
}, cid);
/** The Raw view's preselection: the marks' text in order and the rows they stand on. */
const preselRead = (page: any): Promise<{ text: string; rows: number }> => page.evaluate(() => {
  const body = document.querySelector(".fileview-body") as HTMLElement;
  const marks = Array.from(body.querySelectorAll(".fc-presel")) as HTMLElement[];
  return { text: marks.map((m) => m.textContent).join(""), rows: new Set(marks.map((m) => m.closest(".fv-cl"))).size };
});
const squash = (s: string): string => s.replace(/\s+/g, "");
async function toRaw(page: any): Promise<void> {
  await page.click('.fileview-acts .fileview-btn:text-is("Raw")');
  await page.waitForFunction(() => !!document.querySelector(".fileview-body .fv-cl"), null, { timeout: 10000 });
  await frames(page, 3);
}
async function toRendered(page: any): Promise<void> {
  await page.click('.fileview-acts .fileview-btn:text-is("Rendered")');
  await page.waitForFunction(() => !!document.querySelector(".fileview-md > p"), null, { timeout: 10000 });
  await frames(page, 3);
}

test("in a browser, the real viewer and panel on the Files pane at 900 and 380 px and in the chat modal: a REAL drag over `cell one` in Rendered offers the float, the composer quotes the cell with Save (before: the refusal `touches a table` and Switch to Raw), the save posts the exact slice at the cell's offset, the mark stands in the row's first cell, the Raw view shows it on the row; then a drag from `cell one` into `cell two` is refused with the one-cell sentence and Switch to Raw preselects the row's span with the composer quoting it (before: refused with nothing preselected)", { timeout: 300000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const [mode, width] of [["pane", 900], ["pane", 380], ["chat", 1000]] as [Mode, number][]) {
      const what = mode + " " + width + "px";
      const { page, errors } = await openWith(browser, mode, width, withComments([FINAL], 0));
      const widthBefore = await tableWidth(page);
      // the cell: a real drag, the float, the composer, the save
      const selected = await dragRendered(page, "cell one", "cell one");
      assert.equal(selected.trim(), CELL_Q, what + ": the drag selected the cell's text");
      await floatShown(page);
      await page.click(".fc-float");
      await frames(page, 2);
      const c1 = await composerState(page);
      assert.equal(c1.open, true, what + ": the composer opens");
      assert.equal(c1.refused, null, what + ": no refusal (before: touches a table, with Switch to Raw): " + JSON.stringify(c1));
      assert.equal(c1.raw, false, what + ": no Switch to Raw");
      assert.equal(c1.quote, CELL_Q, what + ": the composer quotes the cell");
      assert.equal(c1.save, true, what + ": Save is offered");
      assert.equal(await page.evaluate(() => { const i = document.querySelector(".fc-composer .fc-input"); return !!i && document.activeElement === i; }), true, what + ": the composer's box has the focus");
      await saveComment(page, CELL, withComments([FINAL, CELL], 1));
      const writes = (await posted(page)).filter((x: any) => x.type === "fileComments" && x.verb === "comment");
      assert.deepEqual(writes.map((w: any) => [w.args.anchor.quote, w.args.hintOffset]), [[CELL_Q, PLAIN.indexOf(CELL_Q)]], what + ": the stored quote is the exact source slice at the cell's offset");
      const r = await readCell(page, id(CELL));
      assert.ok(r.marks >= 1, what + ": the cell's mark painted: " + JSON.stringify(r));
      assert.equal(r.text, CELL_Q, what + ": the mark reads the cell's text");
      assert.deepEqual(r.cell, { tag: "TD", index: 0, row: 0 }, what + ": inside the first body row's first cell");
      t.diagnostic(what + ": table width before the mark " + widthBefore + " px, after " + r.tableWidth + " px (the mark's side padding; the brief's open question 15)");
      // the Raw view: the same comment's mark on the table's row
      await toRaw(page);
      await markPainted(page, id(CELL));
      const raw = await readRaw(page, id(CELL));
      assert.ok(raw.marks >= 1, what + ": the Raw view paints the comment: " + JSON.stringify(raw));
      assert.equal(raw.text, CELL_Q, what + ": over the cell's characters");
      assert.ok(raw.row.includes("| cell one | cell two |"), what + ": on the table's row: " + JSON.stringify(raw.row));
      // back in Rendered: two cells
      await toRendered(page);
      await markPainted(page, id(CELL));
      const two = await dragRendered(page, "cell one", "cell two");
      assert.equal(squash(two), squash(ROW_Q.replace(" | ", " ")), what + ": the drag selected the two cells: " + JSON.stringify(two));
      await floatShown(page);
      await page.click(".fc-float");
      await frames(page, 2);
      const c2 = await composerState(page);
      assert.equal(c2.open, true, what + ": the composer opens on the two cells");
      assert.equal(c2.refused, ONE_CELL, what + ": the one-cell sentence (before: touches a table)");
      assert.equal(c2.rawTitle, "Raw view, with this passage selected", what + ": the Raw button promises the passage (before: 'scrolled to the block; select the passage there')");
      assert.equal(c2.save, null, what + ": no Save under the refusal");
      await page.click('.fc-composer [data-act="fcraw"]');
      await page.waitForFunction(() => !!document.querySelector(".fileview-body .fv-cl"), null, { timeout: 10000 });
      await frames(page, 3);
      const p = await preselRead(page);
      assert.equal(squash(p.text), squash(ROW_Q), what + ": the Raw view preselects the row's span, pipe included (before: nothing): " + JSON.stringify(p));
      assert.equal(p.rows, 1, what + ": one row");
      const c3 = await composerState(page);
      assert.equal(c3.refused, null, what + ": the refusal is answered");
      assert.equal(c3.quote, ROW_Q, what + ": the composer quotes the span");
      assert.equal(c3.save, true, what + ": Save is offered from Raw");
      await page.click('.fc-composer [data-act="fccancel"]');
      await frames(page, 2);
      assert.equal((await composerState(page)).open, false, what + ": Cancel closes the box");
      assert.deepEqual(errors, [], what + ": no script error");
      await page.close();
    }
  });
});

test("in a browser, the real viewer and panel: the cell comment served before a fresh open paints in Rendered inside its <td> and in Raw on the table's row (the plan's acceptance: a comment on a cell paints in both views after a reload; a control, green before this slice through the fallback's ordinal and now through the exact path), on the Files pane and in the chat modal", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const [mode, width] of [["pane", 900], ["chat", 1000]] as [Mode, number][]) {
      const what = mode + " " + width + "px, fresh open";
      const { page, errors } = await openWith(browser, mode, width, withComments([FINAL, CELL], 3));
      await markPainted(page, id(CELL));
      await frames(page, 2);
      const r = await readCell(page, id(CELL));
      assert.ok(r.marks >= 1, what + ": painted in Rendered: " + JSON.stringify(r));
      assert.equal(r.text, CELL_Q, what + ": the cell's text");
      assert.deepEqual(r.cell, { tag: "TD", index: 0, row: 0 }, what + ": inside the cell");
      await toRaw(page);
      await markPainted(page, id(CELL));
      const raw = await readRaw(page, id(CELL));
      assert.equal(raw.text, CELL_Q, what + ": painted in Raw over the cell's characters");
      assert.ok(raw.row.includes("| cell one | cell two |"), what + ": on the row");
      assert.deepEqual(errors, [], what + ": no script error");
      await page.close();
    }
  });
});

/** anchor-map's mapping and paint, bundled from this tree, as window.AM (the code-lines leg's probe). */
function anchorMapBundle(): string {
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    stdin: { contents: 'import { mapRenderedSelection, paintRendered } from "./anchor-map"; (window as any).AM = { mapRenderedSelection, paintRendered };', resolveDir: UI, loader: "ts", sourcefile: "am-probe.ts" },
    bundle: true, write: false, format: "iife", platform: "browser", target: "es2020", nodePaths: [path.join(EXT, "node_modules")], logLevel: "silent",
  });
  return r.outputFiles[0].text as string;
}

test("in a browser, the real viewer: a 1,000-row table, the index build plus one map and forty marks timed for the build note (the brief's open question 13: diagnostics, not a bound); the map lands on the selected cell and every mark in its own cell (before this slice the cell refused as a table)", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const rows = Array.from({ length: 1000 }, (_, i) => "| route_" + i + " | budget_" + i + " ms |");
    const big = "# Big\n\nIntro paragraph.\n\n| Route | Budget |\n|-------|--------|\n" + rows.join("\n") + "\n\nAfter paragraph.\n";
    const { page, errors } = await openViewer(browser, "pane", 900, 700, { docs: { [REPORT]: big } });
    await page.waitForFunction(() => document.querySelectorAll(".fileview-md table tbody tr").length === 1000, null, { timeout: 20000 });
    await page.addScriptTag({ content: anchorMapBundle() });
    const out = await page.evaluate((src: string) => {
      const AM = (window as any).AM;
      const root = document.querySelector(".fileview-md")!;
      const table = root.querySelector("table")!;
      const needle = "route_500";
      const walker = document.createTreeWalker(table, NodeFilter.SHOW_TEXT);
      let tn: Text | null = null;
      for (let n = walker.nextNode() as Text | null; n; n = walker.nextNode() as Text | null) { if (n.data === needle) { tn = n; break; } }
      const t0 = performance.now();
      const mapped = AM.mapRenderedSelection({ anchorNode: tn, anchorOffset: 0, focusNode: tn, focusOffset: needle.length, isCollapsed: false }, root, src);
      const tMap = performance.now() - t0;
      const t1 = performance.now();
      let painted = 0;
      const cells = new Set<Element>();
      for (let k = 0; k < 40; k++) {
        const q = "budget_" + (k * 25) + " ms";
        const start = src.indexOf(q);
        const marks = AM.paintRendered(root, src, { start, end: start + q.length }, "fc-probe", { act: "fcopen", id: "p" + k });
        for (const m of marks || []) { if ((m.textContent || "").trim()) { painted++; const td = m.closest("td"); if (td) cells.add(td); } }
      }
      const tPaint = performance.now() - t1;
      return { rows: table.querySelectorAll("tbody tr").length, mapped, tMap, painted, cells: cells.size, tPaint };
    }, big);
    assert.equal(out.rows, 1000, "a thousand body rows");
    assert.equal(out.mapped.ok, true, "the deep cell maps: " + JSON.stringify(out.mapped));
    assert.equal(out.mapped.quote, "route_500");
    assert.equal(out.mapped.range.start, big.indexOf("route_500"));
    assert.ok(out.painted === 40 && out.cells === 40, "forty marks in forty cells: " + JSON.stringify([out.painted, out.cells]));
    t.diagnostic("1,000-row table in Chromium: index build plus one map " + out.tMap.toFixed(1) + " ms, forty marks " + out.tPaint.toFixed(1) + " ms");
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});

// ── the Slice 8 review, round 1: an astral character in a cell the per-cell fallback holds ──
const ASTRAL = "Status marks.\n\n| E1 | E2 |\n|----|----|\n| \u{1F600} &amp; | ue2 |\n| ue3 | ue4 |\n\nNumeric.\n\n| N1 | N2 |\n|----|----|\n| &#128512; grin | nb2 |\n| nb3 | nb4 |\n\nAfter.\n";
/** A comment in the host's shape on the passage `quote` of `note`: the exact source slice, its context, its position. */
function commentIn(note: string, quote: string, k: number): Record<string, unknown> {
  const at = note.indexOf(quote);
  assert.ok(at >= 0, "the note holds " + JSON.stringify(quote));
  return { id: (T0 + k) + "-" + at, author: "you", ts: T0 + k, body: NOTE, anchor: makeAnchor(note, { start: at, end: at + quote.length }), anchorAt: at, replies: [], resolved: false };
}
const UE2 = commentIn(ASTRAL, "ue2", 6);
const NB2_AT = ASTRAL.indexOf("nb2") + 1;
/** A session's pending deletion one character into `nb2`, in the shape the kernel's status carries. */
const NB2_DEL = { id: "d-nb2", author: "web", ts: T0, kind: "del", curFrom: NB2_AT, curTo: NB2_AT, baseFrom: NB2_AT, baseTo: NB2_AT + 1, oldText: "x", newText: "", anchor: null };

test("in a browser, the real viewer and panel on the Files pane over a table whose hole cell holds an emoji beside an entity, and one whose numeric reference decodes to an emoji: a served comment on `ue2` paints one mark inside its own cell (before: `&` in the emoji's cell and `ue` in its own), a served deletion one character into `nb2` sits between `n` and `b2` (before: before the cell), and a REAL drag over `ue3` opens the composer quoting `ue3` with Save, whose click posts the exact slice at the cell's offset (before: the quote `e3 | u`, the pipe and the next row's first letter inside a passage the person did not select, posted with no refusal): a hole's characters are counted per UTF-16 code unit as positioned text is", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const page = await browser.newPage({ viewport: { width: 900, height: 700 } });
    const errors: string[] = [];
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    const html = pageHtml("pane", { [REPORT]: ASTRAL }, MT);
    await page.route((u: URL) => u.href.startsWith(ORIGIN), (route: any) => route.fulfill({ status: 200, contentType: "text/html", body: html }));
    await page.goto(ORIGIN + "/");
    await page.evaluate(([p, sid, st]: [string, string, unknown]) => { (window as any).__status = st; (window as any).FV.openFileView(p, sid, null); }, [REPORT, SID, { ...withComments([UE2], 6), hunks: [NB2_DEL] }]);
    await page.waitForFunction(() => !!document.querySelector(".fileview-md > p"), null, { timeout: 10000 });
    await frames(page, 2);
    await openPanel(page);
    await markPainted(page, id(UE2));
    await page.waitForFunction(() => !!document.querySelector('.fileview-md .fc-del[data-id="d-nb2"]'), null, { timeout: 10000 });
    await frames(page, 2);
    const read = await page.evaluate((cid: string) => {
      const marks = Array.from(document.querySelectorAll('.fileview-md .fc-hl[data-id="' + cid + '"]')) as HTMLElement[];
      const pt = document.querySelector('.fileview-md .fc-del[data-id="d-nb2"]') as HTMLElement;
      const cells = Array.from(document.querySelectorAll(".fileview-md td")).map((c) => c.textContent);
      return { served: marks.map((m) => ({ text: m.textContent, cell: m.closest("td")?.textContent })), point: { cell: pt.closest("td")?.textContent, prev: pt.previousSibling?.textContent ?? null, next: pt.nextSibling?.textContent ?? null }, cells };
    }, id(UE2));
    assert.deepEqual(read.cells, ["\u{1F600} &", "ue2", "ue3", "ue4", "\u{1F600} grin", "nb2", "nb3", "nb4"], "the browser shows the entities decoded, the emoji's two code units in one cell");
    assert.deepEqual(read.served, [{ text: "ue2", cell: "ue2" }], "the served comment on ue2: one mark in its own cell (before: `&` in the emoji's cell and `ue` in ue2's)");
    assert.deepEqual(read.point, { cell: "nb2", prev: "n", next: "b2" }, "the served deletion one character into nb2: between n and b2 (before: before the cell)");
    const selected = await dragRendered(page, "ue3", "ue3");
    assert.equal(selected.trim(), "ue3", "the drag selected the cell's text");
    await floatShown(page);
    await page.click(".fc-float");
    await frames(page, 2);
    const c = await composerState(page);
    assert.deepEqual([c.open, c.refused, c.quote, c.save], [true, null, "ue3", true], "the composer quotes the cell with Save (before: the quote `e3 | u`): " + JSON.stringify(c));
    await page.keyboard.type(NOTE);
    await page.click('.fileview-aside [data-act="fcsave"]');
    await frames(page, 4);
    const writes = (await posted(page)).filter((x: any) => x.type === "fileComments" && x.verb === "comment");
    assert.deepEqual(writes.map((w: any) => [w.args.anchor.quote, w.args.hintOffset]), [["ue3", ASTRAL.indexOf("ue3")]], "the stored quote is the exact source slice at the cell's offset (before: `e3 | u` one character after)");
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});

// ── the Slice 8 review, round 4: a header row of formulas alone, dragged into from the prose before the table ──
const FORMULAS = "Intro para.\n\n| $h$ | $k$ |\n|---|---|\n| $a$ | $b$ |\n\nAfter.\n";
/** In the page: the box of the first character of the paragraph holding `start`, and the right edge of the n-th KaTeX formula
 *  inside the table (its `.katex-html` box), the drag's two points. */
function proseToFormulaPoints(spec: { start: string; katexIndex: number }): { sx: number; sy: number; ex: number; ey: number } {
  const md = document.querySelector(".fileview-md") as HTMLElement;
  const texts: Text[] = [];
  const w = document.createTreeWalker(md, NodeFilter.SHOW_TEXT);
  for (let t = w.nextNode(); t; t = w.nextNode()) texts.push(t as Text);
  const sNode = texts.find((t) => t.data.startsWith(spec.start));
  if (!sNode) throw new Error("start not in the view's text: " + spec.start);
  const r = document.createRange(); r.setStart(sNode, 0); r.setEnd(sNode, 1);
  const a = r.getBoundingClientRect();
  const boxes = Array.from(md.querySelectorAll("table .katex .katex-html")) as HTMLElement[];
  const k = boxes[spec.katexIndex];
  if (!k) throw new Error("no formula " + spec.katexIndex + " in the table (" + boxes.length + ")");
  const b = k.getBoundingClientRect();
  return { sx: a.left + Math.min(1.5, a.width / 3), sy: a.top + a.height / 2, ex: b.right + 2, ey: b.top + b.height / 2 };
}
/** A real drag from the first character of `start` to just past the n-th formula's glyphs inside the table. */
async function dragProseToFormula(page: any, start: string, katexIndex: number): Promise<string> {
  await page.evaluate(() => { getSelection()!.removeAllRanges(); });
  const pts = await page.evaluate(proseToFormulaPoints, { start, katexIndex });
  await frames(page, 1);
  await page.mouse.move(pts.sx, pts.sy);
  await page.mouse.down();
  await page.mouse.move((pts.sx + pts.ex) / 2, (pts.sy + pts.ey) / 2, { steps: 3 });
  await page.mouse.move(pts.ex, pts.ey, { steps: 6 });
  await page.mouse.up();
  await frames(page, 2);
  return page.evaluate(() => String(getSelection()));
}

test("in a browser, the real viewer and panel on the Files pane over a table whose header row is two formulas alone, rendered by the real KaTeX fill: a REAL drag from the paragraph before the table to past the second header formula's glyphs is refused with the one-cell sentence, the Raw button promising the passage, and Switch to Raw preselects `$h$ | $k$`, the table's covered cells, with the composer quoting it and Save offered (the review's round 4; before: the composer quoted `Intro para. | $h$ | $k$` with Save, two cells and the pipe between them inside a Rendered quote, since a cell holding a formula alone had no record and the one-cell count never saw two); a drag to past the FIRST header formula's glyphs maps one cell and the prose before it, the control", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const page = await browser.newPage({ viewport: { width: 900, height: 700 } });
    const errors: string[] = [];
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    const html = pageHtml("pane", { [REPORT]: FORMULAS }, MT);
    await page.route((u: URL) => u.href.startsWith(ORIGIN), (route: any) => route.fulfill({ status: 200, contentType: "text/html", body: html }));
    await page.goto(ORIGIN + "/");
    await page.evaluate(([p, sid, st]: [string, string, unknown]) => { (window as any).__status = st; (window as any).FV.openFileView(p, sid, null); }, [REPORT, SID, withComments([], 0)]);
    await page.waitForFunction(() => !!document.querySelector(".fileview-md > p"), null, { timeout: 10000 });
    await page.waitForFunction(() => document.querySelectorAll(".fileview-md table .katex .katex-html").length === 4 && !document.querySelector(".fileview-md .md-math-inline"), null, { timeout: 10000 });
    await frames(page, 2);
    await openPanel(page);
    const cells = await page.evaluate(() => Array.from(document.querySelectorAll(".fileview-md th, .fileview-md td")).map((c) => (c.textContent || "").trim()));
    assert.deepEqual(cells, ["h", "k", "a", "b"], "every cell a formula alone, KaTeX's glyphs");
    // two formula-only header cells: refused, the Raw view on the cells' span
    const two = await dragProseToFormula(page, "Intro para.", 1);
    assert.ok(two.startsWith("Intro para.") && two.includes("k"), "the drag selected the paragraph and both header formulas: " + JSON.stringify(two));
    await floatShown(page);
    await page.click(".fc-float");
    await frames(page, 2);
    const c1 = await composerState(page);
    assert.equal(c1.open, true, "the composer opens");
    assert.equal(c1.refused, ONE_CELL, "the one-cell sentence (before: no refusal, the quote `Intro para. | $h$ | $k$` with Save): " + JSON.stringify(c1));
    assert.equal(c1.rawTitle, "Raw view, with this passage selected", "the Raw button promises the passage");
    assert.equal(c1.save, null, "no Save under the refusal");
    await page.click('.fc-composer [data-act="fcraw"]');
    await page.waitForFunction(() => !!document.querySelector(".fileview-body .fv-cl"), null, { timeout: 10000 });
    await frames(page, 3);
    const p = await preselRead(page);
    assert.equal(squash(p.text), squash("$h$ | $k$"), "the Raw view preselects the table's covered cells, the pipe between them (not the prose, not the formula alone): " + JSON.stringify(p));
    assert.equal(p.rows, 1, "one row");
    const c2 = await composerState(page);
    assert.deepEqual([c2.refused, c2.quote, c2.save], [null, "$h$ | $k$", true], "the refusal is answered, the composer quotes the span, Save is offered from Raw");
    await page.click('.fc-composer [data-act="fccancel"]');
    await frames(page, 2);
    await toRendered(page);
    // the control: one formula-only header cell and the prose before it map
    const one = await dragProseToFormula(page, "Intro para.", 0);
    assert.ok(one.startsWith("Intro para.") && one.includes("h") && !one.includes("k"), "the drag selected the paragraph and the first header formula: " + JSON.stringify(one));
    await floatShown(page);
    await page.click(".fc-float");
    await frames(page, 2);
    const c3 = await composerState(page);
    assert.deepEqual([c3.open, c3.refused, c3.quote, c3.save], [true, null, "Intro para. | $h$", true], "one cell and the prose before it map, the formula with its delimiters inside the quote: " + JSON.stringify(c3));
    await page.click('.fc-composer [data-act="fccancel"]');
    await frames(page, 2);
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});

// ── the Slice 8 review, round 5: a picture-only or formula-only cell the drag runs THROUGH, counted by its source span ──
const EDGE_CELLS = "Intro para.\n\n| PL1 | PL2 |\n|-----|-----|\n| pl-a | ![p](x.png) |\n\nAfter the picture-last table.\n\n| FL1 | FL2 |\n|-----|-----|\n| fl-a | $n$ |\n\nAfter the formula-last table.\n";

test("in a browser, the real viewer and panel on the Files pane over a table whose last body cell is a picture alone and one whose last body cell is a formula alone, rendered by the real KaTeX fill: a REAL drag from the positioned cell beside either into the paragraph after the table is refused with the one-cell sentence, the Raw button promising the passage, and Switch to Raw preselects the two cells, `pl-a | ![p](x.png)` and `fl-a | $n$`, with the composer quoting them and Save offered (the review's round 5; before: the composer quoted the cells with the pipe between them and the prose after, Save offered, and the save posted that quote, since a cell emitting no positioned character was counted only through a formula at the drag's end and the pass counted positioned characters); a drag over the positioned cell alone maps it, the control", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const page = await browser.newPage({ viewport: { width: 900, height: 700 } });
    const errors: string[] = [];
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    const html = pageHtml("pane", { [REPORT]: EDGE_CELLS }, MT);
    await page.route((u: URL) => u.href.startsWith(ORIGIN), (route: any) => route.fulfill({ status: 200, contentType: "text/html", body: html }));
    await page.goto(ORIGIN + "/");
    await page.evaluate(([p, sid, st]: [string, string, unknown]) => { (window as any).__status = st; (window as any).FV.openFileView(p, sid, null); }, [REPORT, SID, withComments([], 0)]);
    await page.waitForFunction(() => !!document.querySelector(".fileview-md > p"), null, { timeout: 10000 });
    await page.waitForFunction(() => document.querySelectorAll(".fileview-md table .katex .katex-html").length === 1 && !document.querySelector(".fileview-md .md-math-inline"), null, { timeout: 10000 });
    await frames(page, 2);
    await openPanel(page);
    const cells = await page.evaluate(() => Array.from(document.querySelectorAll(".fileview-md td")).map((c) => [(c.textContent || "").trim(), c.querySelectorAll("img").length, c.querySelectorAll(".katex").length]));
    assert.deepEqual(cells, [["pl-a", 0, 0], ["", 1, 0], ["fl-a", 0, 0], ["n", 0, 1]], "the two tables' body cells: a positioned cell, then a picture alone; a positioned cell, then a formula alone");
    for (const [label, start, end, span] of [["the picture-last table", "pl-a", "After the picture-last table.", "pl-a | ![p](x.png)"], ["the formula-last table", "fl-a", "After the formula-last table.", "fl-a | $n$"]] as const) {
      const selected = await dragRendered(page, start, end);
      assert.ok(selected.startsWith(start) && selected.endsWith(end), label + ": the drag selected the cell and the paragraph after: " + JSON.stringify(selected));
      await floatShown(page);
      await page.click(".fc-float");
      await frames(page, 2);
      const c1 = await composerState(page);
      assert.equal(c1.open, true, label + ": the composer opens");
      assert.equal(c1.refused, ONE_CELL, label + ": the one-cell sentence (before: no refusal, the quote with the pipe and the prose after, Save offered): " + JSON.stringify(c1));
      assert.equal(c1.rawTitle, "Raw view, with this passage selected", label + ": the Raw button promises the passage");
      assert.equal(c1.save, null, label + ": no Save under the refusal");
      await page.click('.fc-composer [data-act="fcraw"]');
      await page.waitForFunction(() => !!document.querySelector(".fileview-body .fv-cl"), null, { timeout: 10000 });
      await frames(page, 3);
      const p = await preselRead(page);
      assert.equal(squash(p.text), squash(span), label + ": the Raw view preselects the two cells, the pipe between them, and not the prose: " + JSON.stringify(p));
      assert.equal(p.rows, 1, label + ": one row");
      const c2 = await composerState(page);
      assert.deepEqual([c2.refused, c2.quote, c2.save], [null, span, true], label + ": the refusal is answered, the composer quotes the span, Save is offered from Raw");
      await page.click('.fc-composer [data-act="fccancel"]');
      await frames(page, 2);
      await toRendered(page);
    }
    // the control: the positioned cell alone maps
    const one = await dragRendered(page, "pl-a", "pl-a");
    assert.equal(one, "pl-a", "the drag selected the cell alone");
    await floatShown(page);
    await page.click(".fc-float");
    await frames(page, 2);
    const c3 = await composerState(page);
    assert.deepEqual([c3.open, c3.refused, c3.quote, c3.save], [true, null, "pl-a", true], "one cell maps: " + JSON.stringify(c3));
    await page.click('.fc-composer [data-act="fccancel"]');
    await frames(page, 2);
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});

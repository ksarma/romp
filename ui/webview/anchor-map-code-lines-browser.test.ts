// A code line commented from the Rendered view, over the REAL viewer and the REAL Comments panel in headless Chromium
// (plans/markdown-viewer.md, Slice 8, item 2; acceptance: a comment on a code line made from Rendered paints in both views after
// a reload). The synthetic fixture anchor-map-fixtures/wrappers-plain.md (the Slice 5 probe's, read-only) is opened in the
// RENDERED view through real-viewer-leg.ts, on the Files pane at 900 and 380 px and in the chat modal, and a REAL mouse drag
// selects `total = a * b * 2` inside the fence's hljs spans: the panel's mouseup offers the Comment float, its click opens the
// composer quoting the line with Save, the save posts the exact source slice with the line's offset as the hint (the anchor the
// host stores byte for byte), the marks stand in the fence's first row once the store answers (one mark per run of adjacent
// hljs nodes, wrapRuns), and a switch to Raw shows the same comment's mark on the line's row. A second drag across two lines
// posts the two lines with the line feed between them and paints both rows. The same comments served before a fresh open paint
// in both views. Over anchor-map-fixtures/refusals.md a drag from `def handler` into the tab-indented `return respond(request)`
// posts a quote holding the TAB byte where the rows show four spaces (the position is the source's, not a text search's). Before
// this slice the probe (the Slice 5 report's section (j)) recorded the code drag refused as "touches a code block" with the Raw
// view preselecting the line after the switch. A last leg times the index, one map and forty marks over a 5,000-line fence for
// the build note (the brief's open question 13; diagnostics, not a bound). Skips LOUDLY without a playwright browser (CI
// installs none), as the other browser legs do. Synthetic values only: an invented note, /repo/notes-api paths, the placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { inBrowser, openPanel, openViewer, frames, pageHtml, requireCjs, ORIGIN, REPORT, SID, MT, STATUS, UI, EXT, type Mode } from "./real-viewer-leg";
import { makeAnchor } from "./anchor-map";

const PLAIN = fs.readFileSync(path.join(UI, "anchor-map-fixtures", "wrappers-plain.md"), "utf8");
const REFUSALS = fs.readFileSync(path.join(UI, "anchor-map-fixtures", "refusals.md"), "utf8");
const T0 = 1757145600000;
const NOTE = "Check this line against the spec.";
const CODE_Q = "total = a * b * 2";
const TWO_Q = "total = a * b * 2\nname_ = under_score  # trailing comment";
const FINAL_Q = "Final paragraph here.";
const TAB_Q = "def handler(request):\n\treturn respond(request)";
const R_FINAL_Q = "An aligned paragraph after everything.";

/** A comment in the host's shape on the note's passage `quote`: the exact source slice, its context, its position. */
function comment(note: string, quote: string, k: number): Record<string, unknown> {
  const at = note.indexOf(quote);
  assert.ok(at >= 0, "the fixture holds " + JSON.stringify(quote));
  return { id: (T0 + k) + "-" + at, author: "you", ts: T0 + k, body: NOTE, anchor: makeAnchor(note, { start: at, end: at + quote.length }), anchorAt: at, replies: [], resolved: false };
}
const FINAL = comment(PLAIN, FINAL_Q, 1);
const CODE = comment(PLAIN, CODE_Q, 2);
const TWO = comment(PLAIN, TWO_Q, 3);
const R_FINAL = comment(REFUSALS, R_FINAL_Q, 4);
const TAB = comment(REFUSALS, TAB_Q, 5);
const id = (c: Record<string, unknown>): string => c.id as string;
/** The kernel's status with `comments` in the store, `n` bumping the store's mtime so each reply reads as a new write. */
const withComments = (comments: Record<string, unknown>[], n: number): Record<string, unknown> =>
  ({ ...STATUS, store: { ...STATUS.store, comments }, storeMtimeNs: "17571456000000000" + (60 + n), unsent: { comments: [], replies: [], accepted: 0, rejected: 0, watermark: null } });

/** The page: `note` open in the Rendered view, `status` served before the open, the panel open, the sentinel's mark painted. */
async function openWith(browser: any, mode: Mode, width: number, note: string, sentinel: Record<string, unknown>, status: Record<string, unknown>): Promise<{ page: any; errors: string[] }> {
  const page = await browser.newPage({ viewport: { width, height: 700 } });
  const errors: string[] = [];
  page.on("pageerror", (e: Error) => { errors.push(e.message); });
  const html = pageHtml(mode, { [REPORT]: note }, MT);
  await page.route((u: URL) => u.href.startsWith(ORIGIN), (route: any) => route.fulfill({ status: 200, contentType: "text/html", body: html }));
  await page.goto(ORIGIN + "/");
  await page.evaluate(([p, sid, st]: [string, string, unknown]) => { (window as any).__status = st; (window as any).FV.openFileView(p, sid, null); }, [REPORT, SID, status]);
  await page.waitForFunction(() => !!document.querySelector(".fileview-md > pre .cl"), null, { timeout: 10000 });
  await frames(page, 2);
  await openPanel(page);
  await markPainted(page, id(sentinel));
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
/** Select the passage in the Rendered view's fence with a real drag over its first and last characters' boxes. */
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
const squash = (s: string): string => s.replace(/\s+/g, "");

type CodeRead = { marks: number; text: string; rows: number[]; inPre: boolean; preRows: number };
/** The comment's marks in the Rendered view: their count, their text, the fence rows they stand in, whether every mark is inside a pre, and the fence's row count. */
const readCode = (page: any, cid: string): Promise<CodeRead> => page.evaluate((c: string) => {
  const md = document.querySelector(".fileview-md") as HTMLElement;
  const marks = Array.from(md.querySelectorAll('.fc-hl[data-act="fcopen"][data-id="' + c + '"]')) as HTMLElement[];
  const withText = marks.filter((m) => (m.textContent || "").trim() !== "");
  const rowOf = (m: HTMLElement) => { const pre = m.closest("pre"); return pre ? Array.from(pre.querySelectorAll(".cl")).findIndex((r) => r.contains(m)) : -1; };
  const pre = withText[0] ? withText[0].closest("pre") : null;
  return {
    marks: marks.length, text: withText.map((x) => x.textContent).join(""),
    rows: Array.from(new Set(withText.map(rowOf))).sort(), inPre: withText.length > 0 && withText.every((m) => !!m.closest("pre")),
    preRows: pre ? pre.querySelectorAll(".cl").length : -1,
  };
}, cid);
/** The comment's marks in the Raw view: their count, the rows they stand on, their text. */
const readRaw = (page: any, cid: string): Promise<{ marks: number; rows: string[]; text: string }> => page.evaluate((c: string) => {
  const body = document.querySelector(".fileview-body") as HTMLElement;
  const marks = Array.from(body.querySelectorAll('.fc-hl[data-act="fcopen"][data-id="' + c + '"]')) as HTMLElement[];
  const rows = Array.from(new Set(marks.map((m) => m.closest(".fv-cl")))).map((r) => (r && r.textContent || "").trim());
  return { marks: marks.length, rows, text: marks.map((m) => m.textContent).join("") };
}, cid);
async function toRaw(page: any): Promise<void> {
  await page.click('.fileview-acts .fileview-btn:text-is("Raw")');
  await page.waitForFunction(() => !!document.querySelector(".fileview-body .fv-cl"), null, { timeout: 10000 });
  await frames(page, 3);
}
async function toRendered(page: any): Promise<void> {
  await page.click('.fileview-acts .fileview-btn:text-is("Rendered")');
  await page.waitForFunction(() => !!document.querySelector(".fileview-md > pre .cl"), null, { timeout: 10000 });
  await frames(page, 3);
}
/** A real drag over the passage, the float, the composer quoting it with Save; returns the composer's state. */
async function dragAndOpen(page: any, what: string, start: string, end: string, quote: string): Promise<ComposerState> {
  const selected = await dragRendered(page, start, end);
  assert.equal(squash(selected), squash(quote), what + ": the drag selected the passage: " + JSON.stringify(selected));
  await floatShown(page);
  await page.click(".fc-float");
  await frames(page, 2);
  const c = await composerState(page);
  assert.equal(c.open, true, what + ": the composer opens");
  assert.equal(c.refused, null, what + ": no refusal (before: touches a code block, with Switch to Raw): " + JSON.stringify(c));
  assert.equal(c.raw, false, what + ": no Switch to Raw");
  assert.equal(c.quote, quote.replace(/\s+/g, " ").trim(), what + ": the composer quotes the passage (its whitespace collapsed for display; the posted anchor below is the byte check)");
  assert.equal(c.save, true, what + ": Save is offered");
  return c;
}

test("in a browser, the real viewer and panel on the Files pane at 900 and 380 px and in the chat modal: a REAL drag over `total = a * b * 2` inside the fence's hljs spans offers the float, the composer quotes the line with Save (before: the refusal `touches a code block` and Switch to Raw), the save posts the exact slice at the line's offset, the marks stand in the fence's first row, the Raw view shows the mark on the row; a two-line drag posts the two lines with their line feed and paints both rows", { timeout: 300000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const [mode, width] of [["pane", 900], ["pane", 380], ["chat", 1000]] as [Mode, number][]) {
      const what = mode + " " + width + "px";
      const { page, errors } = await openWith(browser, mode, width, PLAIN, FINAL, withComments([FINAL], 0));
      // the line: a real drag, the float, the composer, the save
      await dragAndOpen(page, what, "total", "2", CODE_Q);
      assert.equal(await page.evaluate(() => { const i = document.querySelector(".fc-composer .fc-input"); return !!i && document.activeElement === i; }), true, what + ": the composer's box has the focus");
      await saveComment(page, CODE, withComments([FINAL, CODE], 1));
      let writes = (await posted(page)).filter((x: any) => x.type === "fileComments" && x.verb === "comment");
      assert.deepEqual(writes.map((w: any) => [w.args.anchor.quote, w.args.hintOffset]), [[CODE_Q, PLAIN.indexOf(CODE_Q)]], what + ": the stored quote is the exact source slice at the line's offset");
      const r = await readCode(page, id(CODE));
      assert.ok(r.marks >= 1, what + ": the line's marks painted: " + JSON.stringify(r));
      assert.equal(squash(r.text), squash(CODE_Q), what + ": the marks read the whole line, asterisks included");
      assert.deepEqual(r.rows, [0], what + ": inside the fence's first row");
      assert.equal(r.inPre, true, what + ": every mark inside the pre");
      t.diagnostic(what + ": the fence has " + r.preRows + " rows; the line's marks: " + r.marks);
      // the Raw view: the same comment's mark on the line's row
      await toRaw(page);
      await markPainted(page, id(CODE));
      const raw = await readRaw(page, id(CODE));
      assert.ok(raw.marks >= 1, what + ": the Raw view paints the comment: " + JSON.stringify(raw));
      assert.equal(raw.text, CODE_Q, what + ": over the line's characters");
      assert.deepEqual(raw.rows, [CODE_Q], what + ": on the line's row");
      // back in Rendered: two lines
      await toRendered(page);
      await markPainted(page, id(CODE));
      await dragAndOpen(page, what + ", two lines", "total", "comment", TWO_Q);
      await saveComment(page, TWO, withComments([FINAL, CODE, TWO], 2));
      writes = (await posted(page)).filter((x: any) => x.type === "fileComments" && x.verb === "comment");
      assert.deepEqual(writes.map((w: any) => [w.args.anchor.quote, w.args.hintOffset]), [[CODE_Q, PLAIN.indexOf(CODE_Q)], [TWO_Q, PLAIN.indexOf(TWO_Q)]], what + ": the two-line quote carries the line feed the rows dropped");
      const two = await readCode(page, id(TWO));
      assert.deepEqual(two.rows, [0, 1], what + ": both rows carry the two-line comment's marks: " + JSON.stringify(two));
      assert.equal(squash(two.text), squash(TWO_Q), what + ": the two lines' characters");
      await page.click('.fileview-aside .fc-card[data-id="' + id(TWO) + '"] .fc-card-head .fc-time').catch(() => null);
      assert.deepEqual(errors, [], what + ": no script error");
      await page.close();
    }
  });
});

test("in a browser, the real viewer and panel: the code comments served before a fresh open paint in Rendered inside the fence's rows and in Raw on the lines' rows (the plan's acceptance: a comment on a code line paints in both views after a reload; a control, green before this slice through the fallback's raw reading and now through the exact path), on the Files pane and in the chat modal", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const [mode, width] of [["pane", 900], ["chat", 1000]] as [Mode, number][]) {
      const what = mode + " " + width + "px, fresh open";
      const { page, errors } = await openWith(browser, mode, width, PLAIN, FINAL, withComments([FINAL, CODE, TWO], 3));
      await markPainted(page, id(CODE));
      await markPainted(page, id(TWO));
      await frames(page, 2);
      const r = await readCode(page, id(CODE));
      assert.deepEqual([squash(r.text), r.rows, r.inPre], [squash(CODE_Q), [0], true], what + ": the one-line comment in the first row: " + JSON.stringify(r));
      const two = await readCode(page, id(TWO));
      assert.deepEqual([squash(two.text), two.rows], [squash(TWO_Q), [0, 1]], what + ": the two-line comment across both rows: " + JSON.stringify(two));
      await toRaw(page);
      await markPainted(page, id(CODE));
      const raw = await readRaw(page, id(CODE));
      assert.deepEqual([raw.text, raw.rows], [CODE_Q, [CODE_Q]], what + ": painted in Raw on the line's row");
      const rawTwo = await readRaw(page, id(TWO));
      assert.equal(rawTwo.rows.length, 2, what + ": the two-line comment on two Raw rows: " + JSON.stringify(rawTwo));
      assert.deepEqual(errors, [], what + ": no script error");
      await page.close();
    }
  });
});

test("in a browser, the real viewer and panel on the Files pane: a drag from `def handler` into the tab-indented `return respond(request)` posts a quote holding the TAB byte where the rows show four spaces (the position is the source's), the marks stand in the fence's two rows, and the Raw view shows the comment on both lines", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const what = "pane 900px, the tab-indented line";
    const { page, errors } = await openWith(browser, "pane", 900, REFUSALS, R_FINAL, withComments([R_FINAL], 4));
    const shown: string[] = await page.evaluate(() => Array.from(document.querySelectorAll(".fileview-md > pre")[0].querySelectorAll(".cl")).map((r) => r.textContent || ""));
    assert.deepEqual(shown, ["def handler(request):", "    return respond(request)"], "the fence's rows show the tab as four spaces");
    await dragAndOpen(page, what, "def", "respond(request)", TAB_Q);
    await saveComment(page, TAB, withComments([R_FINAL, TAB], 5));
    const writes = (await posted(page)).filter((x: any) => x.type === "fileComments" && x.verb === "comment");
    assert.deepEqual(writes.map((w: any) => [w.args.anchor.quote, w.args.hintOffset]), [[TAB_Q, REFUSALS.indexOf(TAB_Q)]], what + ": the stored quote holds the tab byte (before: refused, no store write)");
    assert.ok((writes[0].args.anchor.quote as string).includes("\t"), what + ": a real tab in the quote");
    const r = await readCode(page, id(TAB));
    assert.deepEqual(r.rows, [0, 1], what + ": both rows painted: " + JSON.stringify(r));
    assert.equal(squash(r.text), squash(TAB_Q), what + ": the two lines' characters");
    await toRaw(page);
    await markPainted(page, id(TAB));
    const raw = await readRaw(page, id(TAB));
    assert.equal(raw.rows.length, 2, what + ": two Raw rows: " + JSON.stringify(raw));
    assert.equal(raw.text, TAB_Q.replace("\n", ""), what + ": the Raw marks read the two lines, tab included (the rows drop the line feed between them)");
    assert.deepEqual(errors, [], what + ": no script error");
    await page.close();
  });
});

/** anchor-map's mapping and paint, bundled from this tree, as window.AM (the wrapped-code leg's probe). */
function anchorMapBundle(): string {
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    stdin: { contents: 'import { mapRenderedSelection, paintRendered } from "./anchor-map"; (window as any).AM = { mapRenderedSelection, paintRendered };', resolveDir: UI, loader: "ts", sourcefile: "am-probe.ts" },
    bundle: true, write: false, format: "iife", platform: "browser", target: "es2020", nodePaths: [path.join(EXT, "node_modules")], logLevel: "silent",
  });
  return r.outputFiles[0].text as string;
}

test("in a browser, the real viewer: a 5,000-line fence, the index build plus one map and forty marks timed for the build note (the brief's open question 13: diagnostics, not a bound); the map lands on the selected line and every mark on its own row", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const lines = Array.from({ length: 5000 }, (_, i) => "line_" + i + " = value_" + i);
    const big = "# Big\n\nIntro paragraph.\n\n```\n" + lines.join("\n") + "\n```\n\nAfter paragraph.\n";
    const { page, errors } = await openViewer(browser, "pane", 900, 700, { docs: { [REPORT]: big } });
    await page.waitForFunction(() => !!document.querySelector(".fileview-md > pre .cl"), null, { timeout: 20000 });
    await page.addScriptTag({ content: anchorMapBundle() });
    const out = await page.evaluate((src: string) => {
      const AM = (window as any).AM;
      const root = document.querySelector(".fileview-md")!;
      const pre = root.querySelector("pre")!;
      const rows = Array.from(pre.querySelectorAll(".cl")) as HTMLElement[];
      const needle = "line_2500 = value_2500";
      const walker = document.createTreeWalker(pre, NodeFilter.SHOW_TEXT);
      let tn: Text | null = null;
      for (let n = walker.nextNode() as Text | null; n; n = walker.nextNode() as Text | null) { if (n.data.indexOf(needle) >= 0) { tn = n; break; } }
      const i = tn!.data.indexOf(needle);
      const t0 = performance.now();
      const mapped = AM.mapRenderedSelection({ anchorNode: tn, anchorOffset: i, focusNode: tn, focusOffset: i + needle.length, isCollapsed: false }, root, src);
      const tMap = performance.now() - t0;
      const t1 = performance.now();
      let painted = 0;
      const rowsHit = new Set<number>();
      for (let k = 0; k < 40; k++) {
        const q = "line_" + (k * 100) + " = value_" + (k * 100);
        const start = src.indexOf(q);
        const marks = AM.paintRendered(root, src, { start, end: start + q.length }, "fc-probe", { act: "fcopen", id: "p" + k });
        for (const m of marks || []) { if ((m.textContent || "").trim()) { painted++; rowsHit.add(rows.findIndex((r) => r.contains(m))); } }
      }
      const tPaint = performance.now() - t1;
      return { rows: rows.length, mapped, tMap, painted, rowsHit: rowsHit.size, tPaint };
    }, big);
    assert.equal(out.rows, 5000, "five thousand rows");
    assert.equal(out.mapped.ok, true, "the deep line maps: " + JSON.stringify(out.mapped));
    assert.equal(out.mapped.quote, "line_2500 = value_2500");
    assert.equal(out.mapped.range.start, big.indexOf("line_2500 = value_2500"));
    assert.ok(out.painted >= 40 && out.rowsHit === 40, "forty marks on forty rows: " + JSON.stringify([out.painted, out.rowsHit]));
    t.diagnostic("5,000-line fence in Chromium: index build plus one map " + out.tMap.toFixed(1) + " ms, forty marks " + out.tPaint.toFixed(1) + " ms");
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});

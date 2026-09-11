// The painter's two hole readings over the REAL viewer and the REAL Comments panel in headless Chromium (plans/markdown-viewer.md,
// Slice 5, items 2 and 8: "match code quotes raw" and "strip cell delimiters from a table quote", the second read at paint time
// under the owner's ruling 5; acceptance: the `total = a * b * 2` comment paints in Rendered, a Raw comment across two cells
// paints). The synthetic fixture anchor-map-fixtures/wrappers-plain.md is opened in the RAW view under the Files pane's sheet
// through real-viewer-leg.ts, and a REAL mouse drag selects the code line `total = a * b * 2`, then the row's `cell one | cell
// two`; each is saved through the float and the composer, the harness answering the save with the store holding the comment in
// the host's shape (the quote the exact source slice, the pipe kept; the posted anchor is checked to be that), and the view is
// switched to Rendered: the code comment's marks read the whole line inside the fence's first row, the table comment's marks sit
// one in each of the row's two cells, and each card, opened from its head, offers Scroll to the passage and no Reveal (a folded
// card renders its preview and no actions row, so Reveal's absence is read on the OPEN card; the review's round 1 found the read
// over a folded card vacuous). The same comments served before a fresh open paint the same on the Files pane and in the chat
// modal. Before this slice the probe recorded 0 marks for both in Rendered, the open cards offering Reveal: the code needle lost
// its asterisks to the emphasis strip and matched nothing, the table needle kept its pipe and the cells' text has none. A comment
// on the note's last paragraph is served throughout as the pass's sentinel: its mark is what the legs wait for before reading the
// others (the paint is one pass over every card). Skips LOUDLY without a playwright browser (CI installs none), as the other
// browser legs do. Synthetic values only: an invented note, /repo/notes-api paths, the placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { inBrowser, openPanel, frames, pageHtml, ORIGIN, REPORT, SID, MT, STATUS, UI, type Mode } from "./real-viewer-leg";
import { makeAnchor } from "./anchor-map";

const PLAIN = fs.readFileSync(path.join(UI, "anchor-map-fixtures", "wrappers-plain.md"), "utf8");
const T0 = 1757145600000;
const NOTE = "Check this line against the spec.";

/** A comment in the host's shape on the fixture's passage `quote`: the exact source slice, its 24-character context, its position. */
function comment(quote: string, k: number): Record<string, unknown> {
  const at = PLAIN.indexOf(quote);
  assert.ok(at >= 0, "the fixture holds " + JSON.stringify(quote));
  return { id: (T0 + k) + "-" + at, author: "you", ts: T0 + k, body: NOTE, anchor: makeAnchor(PLAIN, { start: at, end: at + quote.length }), anchorAt: at, replies: [], resolved: false };
}
const CODE_Q = "total = a * b * 2";
const CELLS_Q = "cell one | cell two";
const FINAL_Q = "Final paragraph here.";
const FINAL = comment(FINAL_Q, 1);
const CODE = comment(CODE_Q, 2);
const CELLS = comment(CELLS_Q, 3);
const id = (c: Record<string, unknown>): string => c.id as string;
/** The kernel's status with `comments` in the store, `n` bumping the store's mtime so each reply reads as a new write. */
const withComments = (comments: Record<string, unknown>[], n: number): Record<string, unknown> =>
  ({ ...STATUS, store: { ...STATUS.store, comments }, storeMtimeNs: "17571456000000000" + (20 + n), unsent: { comments: [], replies: [], accepted: 0, rejected: 0, watermark: null } });

/** The page: the fixture open in the view (Raw when `raw`), `status` served before the open, the panel open, the sentinel's mark painted. */
async function openWith(browser: any, mode: Mode, width: number, raw: boolean, status: Record<string, unknown>): Promise<{ page: any; errors: string[] }> {
  const page = await browser.newPage({ viewport: { width, height: 700 } });
  const errors: string[] = [];
  page.on("pageerror", (e: Error) => { errors.push(e.message); });
  const html = pageHtml(mode, { [REPORT]: PLAIN }, MT);
  await page.route((u: URL) => u.href.startsWith(ORIGIN), (route: any) => route.fulfill({ status: 200, contentType: "text/html", body: html }));
  await page.goto(ORIGIN + "/");
  if (raw) await page.evaluate(() => { localStorage.setItem("romp:fileviewFmt", JSON.stringify({ md: "raw" })); });
  await page.evaluate(([p, sid, st]: [string, string, unknown]) => { (window as any).__status = st; (window as any).FV.openFileView(p, sid, null); }, [REPORT, SID, status]);
  await page.waitForFunction((raw: boolean) => !!document.querySelector(raw ? ".fileview-body .fv-cl" : ".fileview-md > p"), raw, { timeout: 10000 });
  await frames(page, 2);
  await openPanel(page);
  await markPainted(page, id(FINAL));
  return { page, errors };
}
/** Wait for the comment's highlight in the view's body (the pass painted it). */
const markPainted = (page: any, cid: string): Promise<unknown> =>
  page.waitForFunction((c: string) => !!document.querySelector('.fileview-body [data-act="fcopen"][data-id="' + c + '"]'), cid, { timeout: 10000 });
/** Open the comment's card from its head, and wait for it: a folded card renders its preview and no actions row (renderCard
 *  returns before the row), so Reveal, or its absence, is only readable on the open card. The head's centre is the quote, which
 *  is the Scroll link once the comment painted (fcgoto stops the click), so the click lands on the head's clock, which the
 *  panel's delegate resolves to the head's fccard. Neither test writes a reply, so no card is held open and the click is a plain open. */
async function openCard(page: any, cid: string): Promise<void> {
  const card = '.fileview-aside .fc-card[data-id="' + cid + '"]';
  assert.equal(await page.evaluate((k: string) => { const c = document.querySelector(k); return !!c && !c.classList.contains("open"); }, card), true, "the card " + cid + " is there and folded before its head is clicked");
  await page.click(card + " .fc-card-head .fc-time");
  await page.waitForFunction((k: string) => { const c = document.querySelector(k); return !!c && c.classList.contains("open"); }, card, { timeout: 5000 });
  await frames(page, 2);
}

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
/** Select the passage in the Raw view with a real drag over its first and last characters' boxes. */
async function dragRaw(page: any, start: string, end: string): Promise<string> {
  await page.evaluate(() => { getSelection()!.removeAllRanges(); });
  const pts: Points = await page.evaluate(pointsIn, { rootSel: ".fileview-body code.hljs", start, end });
  await frames(page, 1);
  await page.mouse.move(pts.sx, pts.sy);
  await page.mouse.down();
  await page.mouse.move((pts.sx + pts.ex) / 2, (pts.sy + pts.ey) / 2, { steps: 3 });
  await page.mouse.move(pts.ex, pts.ey, { steps: 6 });
  await page.mouse.up();
  await frames(page, 2);
  return page.evaluate(() => String(getSelection()));
}
/** The float's click, the note typed, the save; the harness answers with `next`, whose new comment's card and Raw mark are awaited. */
async function saveComment(page: any, c: Record<string, unknown>, next: Record<string, unknown>): Promise<void> {
  await page.waitForFunction(() => { const f = document.querySelector(".fc-float") as HTMLElement | null; return !!f && !f.hidden; }, null, { timeout: 5000 });
  await page.click(".fc-float");
  await frames(page, 2);
  assert.equal(await page.evaluate(() => { const i = document.querySelector(".fc-composer .fc-input"); return !!i && document.activeElement === i; }), true, "the composer opened with its box focused");
  await page.keyboard.type(NOTE);
  await page.evaluate((st: unknown) => { (window as any).__status = st; }, next);
  await page.click('.fileview-aside [data-act="fcsave"]');
  await page.waitForFunction((cid: string) => !!document.querySelector('.fileview-aside .fc-card[data-id="' + cid + '"]'), id(c), { timeout: 10000 });
  await markPainted(page, id(c));
  await frames(page, 2);
}
const posted = (page: any): Promise<any[]> => page.evaluate(() => (window as any).__posted);

type Read = { marks: number; text: string; rows: number[]; cells: ({ tag: string; index: number } | null)[]; sameRow: boolean; card: boolean; open: boolean; goto: boolean; reveal: boolean };
/** The comment's marks in the Rendered view: their count, their text (the ones with text of their own), the fence rows and the table cells they
 *  sit in, and what its card offers, with whether the card is open (`reveal` means nothing on a folded card, which renders no actions row). */
const readMarks = (page: any, cid: string): Promise<Read> => page.evaluate((c: string) => {
  const md = document.querySelector(".fileview-md") as HTMLElement;
  const marks = Array.from(md.querySelectorAll('.fc-hl[data-act="fcopen"][data-id="' + c + '"]')) as HTMLElement[];
  const withText = marks.filter((m) => (m.textContent || "").trim() !== "");
  // the fence the marks sit in (the note's front matter renders a pre of its own before it), and its wrapped rows
  const rowOf = (m: HTMLElement) => { const pre = m.closest("pre"); return pre ? Array.from(pre.querySelectorAll(".cl")).findIndex((r) => r.contains(m)) : -1; };
  const cellOf = (m: HTMLElement) => { const td = m.closest("td, th"); return td ? { tag: td.tagName, index: Array.from((td.parentElement as HTMLElement).children).indexOf(td), row: td.parentElement } : null; };
  const cells = withText.map(cellOf);
  const card = document.querySelector('.fileview-aside .fc-card[data-id="' + c + '"]');
  return {
    marks: marks.length, text: withText.map((m) => m.textContent).join(" ").replace(/\s+/g, " ").trim(),
    rows: Array.from(new Set(withText.map(rowOf))).sort(), cells: cells.map((x) => x && { tag: x.tag, index: x.index }),
    sameRow: cells.length === 2 && !!cells[0] && !!cells[1] && cells[0].row === cells[1].row,
    card: !!card, open: !!card && card.classList.contains("open"),
    goto: !!card && !!card.querySelector('[data-act="fcgoto"]'), reveal: !!card && !!card.querySelector('[data-act="fcreveal"]'),
  };
}, cid);
/** The two comments' paint in Rendered, as items 2 and 8 promise it; `code` and `cells` are read with their cards OPEN (openCard), the
 *  only state in which the actions row, and so a Reveal button, renders. */
function assertPainted(what: string, code: Read, cells: Read): void {
  assert.ok(code.marks > 0, what + ": the code comment paints (before: 0 marks, the needle read `total = a  b  2`)");
  assert.equal(code.text, CODE_Q, what + ": the code marks read the whole line, asterisks included");
  assert.deepEqual(code.rows, [0], what + ": inside the fence's first row");
  assert.equal(code.card && code.goto, true, what + ": the code card offers Scroll to the passage");
  assert.equal(code.open, true, what + ": the code card is open, so its actions row is rendered and Reveal is readable");
  assert.equal(code.reveal, false, what + ": ...and the open card offers no Reveal (before: Reveal, no Scroll link)");
  assert.ok(cells.marks > 0, what + ": the across-cells comment paints (before: 0 marks, the needle kept the pipe)");
  assert.equal(cells.text, "cell one cell two", what + ": the two cells' text, nothing of the pipe");
  assert.deepEqual(cells.cells, [{ tag: "TD", index: 0 }, { tag: "TD", index: 1 }], what + ": one mark in each of the row's two cells");
  assert.equal(cells.sameRow, true, what + ": the same row");
  assert.equal(cells.card && cells.goto, true, what + ": the table card offers Scroll to the passage");
  assert.equal(cells.open, true, what + ": the table card is open, so its actions row is rendered and Reveal is readable");
  assert.equal(cells.reveal, false, what + ": ...and the open card offers no Reveal (before: Reveal)");
}

test("in a browser, the real viewer and panel on the Files pane: a comment saved from a Raw drag over `total = a * b * 2` and one over `cell one | cell two` (the quote the exact source slice, pipe kept) paint in Rendered after the view switch: the code line whole in the fence's first row, the two cells one mark each; the cards, opened, offer Scroll to the passage and no Reveal (before: no marks, Reveal)", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openWith(browser, "pane", 900, true, withComments([FINAL], 0));
    // the code line
    let selected = await dragRaw(page, "total", "* 2");
    assert.equal(selected.trim(), CODE_Q, "the drag selected the code line");
    await saveComment(page, CODE, withComments([FINAL, CODE], 1));
    // the two cells
    selected = await dragRaw(page, "cell one", "cell two");
    assert.equal(selected.trim(), CELLS_Q, "the drag selected the two cells with the pipe between them");
    await saveComment(page, CELLS, withComments([FINAL, CODE, CELLS], 2));
    const writes = (await posted(page)).filter((x: any) => x.type === "fileComments" && x.verb === "comment");
    assert.deepEqual(writes.map((w: any) => w.args.anchor.quote), [CODE_Q, CELLS_Q], "the stored quotes are the exact source slices: the asterisks and the pipe kept (the composer and the host untouched; ruling 5 reads the plan's strip at paint time)");
    assert.deepEqual(writes.map((w: any) => w.args.hintOffset), [PLAIN.indexOf(CODE_Q), PLAIN.indexOf(CELLS_Q)], "...at their offsets");
    // Rendered
    await page.click('.fileview-acts .fileview-btn:text-is("Rendered")');
    await page.waitForFunction(() => !!document.querySelector(".fileview-md > p"), null, { timeout: 10000 });
    await markPainted(page, id(FINAL));
    await frames(page, 3);
    await openCard(page, id(CODE));
    await openCard(page, id(CELLS));
    assertPainted("pane 900px after the Raw saves", await readMarks(page, id(CODE)), await readMarks(page, id(CELLS)));
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});

// ── the Slice 5 review, round 2: the strip's cell cases over the real viewer and panel ──
const CELLS_NOTE = "# Cells\n\n| Cell | Note |\n|------|------|\n| *a *b* c* | nested |\n| **a **b** c** | strong |\n| `a \\| b` | span |\n| `string \\| number` | union |\n| \\*\\*kwargs | py |\n| \\*required\\* | req |\n| costs \\$5 | price |\n| **Note:**_draft_ | adj |\n| Ctrl<kbd>C</kbd> | kbd |\n| C:\\Users\\ | path |\n| x * y * z | stars |\n\nLast paragraph here.\n";
/** The round 2 cells: the quote a Raw comment stores (the exact source slice) and the cell's text the marks must read. */
const ROUND2_CELLS: Array<[string, string]> = [
  ["*a *b* c*", "a b c"], ["**a **b** c**", "a b c"], ["`a \\| b`", "a | b"], ["`string \\| number`", "string | number"],
  ["\\*\\*kwargs", "**kwargs"], ["\\*required\\*", "*required*"], ["costs \\$5", "costs $5"], ["**Note:**_draft_", "Note:draft"],
  ["Ctrl<kbd>C</kbd>", "CtrlC"], ["C:\\Users\\", "C:\\Users\\"], ["x * y * z", "x * y * z"],
];
function cellComment(quote: string, k: number): Record<string, unknown> {
  const at = CELLS_NOTE.indexOf(quote);
  assert.ok(at >= 0, "the note holds " + JSON.stringify(quote));
  return { id: (T0 + 100 + k) + "-" + at, author: "you", ts: T0 + 100 + k, body: NOTE, anchor: makeAnchor(CELLS_NOTE, { start: at, end: at + quote.length }), anchorAt: at, replies: [], resolved: false };
}

test("in a browser, the real viewer and panel: Raw comments on the round 2 cells, served before a fresh open, paint in Rendered as the cells show them: same-delimiter nested emphasis (`*a *b* c*`, `**a **b** c**`) as `a b c`, a code span with an escaped pipe (`` `a \\| b` ``) as `a | b`, escaped asterisks (`\\*\\*kwargs`, `\\*required\\*`) with their asterisks, `costs \\$5`, an underscore emphasis beside a strong, an inline html tag's text, a cell ending in a backslash whole, and `x * y * z` still; each card offers Scroll (before: 0 marks and Reveal for all but the last)", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const sentinel = { id: (T0 + 99) + "-" + CELLS_NOTE.indexOf("Last paragraph here."), author: "you", ts: T0 + 99, body: NOTE, anchor: makeAnchor(CELLS_NOTE, { start: CELLS_NOTE.indexOf("Last paragraph here."), end: CELLS_NOTE.indexOf("Last paragraph here.") + "Last paragraph here.".length }), anchorAt: CELLS_NOTE.indexOf("Last paragraph here."), replies: [], resolved: false };
    const comments = [sentinel, ...ROUND2_CELLS.map(([q], k) => cellComment(q, k))];
    const status = { ...STATUS, store: { ...STATUS.store, comments }, storeMtimeNs: "1757145600000000041", unsent: { comments: [], replies: [], accepted: 0, rejected: 0, watermark: null } };
    const page = await browser.newPage({ viewport: { width: 900, height: 700 } });
    const errors: string[] = [];
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    const html = pageHtml("pane", { [REPORT]: CELLS_NOTE }, MT);
    await page.route((u: URL) => u.href.startsWith(ORIGIN), (route: any) => route.fulfill({ status: 200, contentType: "text/html", body: html }));
    await page.goto(ORIGIN + "/");
    await page.evaluate(([p, sid, st]: [string, string, unknown]) => { (window as any).__status = st; (window as any).FV.openFileView(p, sid, null); }, [REPORT, SID, status]);
    await page.waitForFunction(() => !!document.querySelector(".fileview-md > p"), null, { timeout: 10000 });
    await frames(page, 2);
    await openPanel(page);
    await markPainted(page, sentinel.id);
    await frames(page, 3);
    const shown: string[] = await page.evaluate(() => Array.from(document.querySelectorAll(".fileview-md td:first-child")).map((td) => (td.textContent || "").replace(/\s+/g, " ").trim()));
    assert.deepEqual(shown, ROUND2_CELLS.map(([, s]) => s), "the cells render as the cases expect");
    for (let k = 0; k < ROUND2_CELLS.length; k++) {
      const [quote, text] = ROUND2_CELLS[k];
      const r = await readMarks(page, cellComment(quote, k).id as string);
      assert.ok(r.marks > 0, quote + ": painted (before: 0 marks): " + JSON.stringify(r));
      assert.equal(r.text.replace(/\s+/g, ""), text.replace(/\s+/g, ""), quote + ": the marks read the cell's whole text (a mark per text node: a nested emphasis or a tag splits the cell's text)");
      assert.ok(r.cells.length >= 1 && r.cells.every((c) => !!c && c.tag === "TD" && c.index === 0), quote + ": every mark in the first cell: " + JSON.stringify(r.cells));
      assert.equal(r.card && r.goto, true, quote + ": the card offers Scroll to the passage");
    }
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});

test("in a browser, the real viewer and panel: the same comments served before a fresh open paint the same in Rendered, on the Files pane and in the chat modal", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const [mode, width] of [["pane", 900], ["chat", 1000]] as [Mode, number][]) {
      const what = mode + " " + width + "px, fresh open";
      const { page, errors } = await openWith(browser, mode, width, false, withComments([FINAL, CODE, CELLS], 3));
      await frames(page, 2);
      await openCard(page, id(CODE));
      await openCard(page, id(CELLS));
      assertPainted(what, await readMarks(page, id(CODE)), await readMarks(page, id(CELLS)));
      assert.deepEqual(errors, [], what + ": no script error");
      await page.close();
    }
  });
});

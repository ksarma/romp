// A real drag that begins on the FIRST glyph of a comment's highlight selects the passage, over the REAL viewer and the REAL Comments
// panel in headless Chromium (plans/markdown-viewer.md Slice 8; the review's round 3). A highlight is a control with a tabindex, so
// a press on one moved the browser's focus onto the mark before the press placed its caret, and Chromium never extends a selection
// anchored outside the element the press focused: a press on the leading half of the first glyph anchors the caret at the end of
// the text node BEFORE the mark (the same caret, another node), so a drag begun there, the natural place to re-select a highlighted
// passage, selected nothing, offered no Comment, and its release opened the card instead; a drag begun one glyph in selected as
// usual. Identical on main 696229f84 for a paragraph, so no doing of the slice's; the slice's code-line marks widened where it
// showed. The panel now takes the tabindex off every mark of ours the press began on for the length of the press and puts it back
// at the release, when the innermost pressed mark takes the focus the press would have given it (file-comments.ts pressedMarks).
// Here a synthetic note is opened in the Rendered view on the Files pane through real-viewer-leg.ts with four comments served: one
// on a paragraph's words, two on the same words of another paragraph (a nest of marks, the later comment's inside the earlier's),
// one on a word in a fence's row. For each, a REAL drag from the leading half of the first glyph (two fractions of its width) to
// the last glyph: mid-press the pressed marks wear no tabindex and none holds the focus; at the release the selection is the
// passage, the float is offered, no card opened, every mark wears tabindex 0 and role button again, and the innermost pressed mark
// holds the focus. Then a plain click at the same point opens the card as before, and Tab then Shift+Tab returns to the mark, so
// it stands in the tab order after the press. Fails over a `git archive` of 2136fa7d2 (the review's round 2 fix commit): the marks
// keep their tabindex mid-press, the selection is empty at the release, no float, and the card opens. Skips LOUDLY without a
// playwright browser (CI installs none), as the other browser legs do. Synthetic values only: an invented note, /repo/notes-api
// paths, the placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openPanel, frames, pageHtml, ORIGIN, REPORT, SID, MT, STATUS } from "./real-viewer-leg";
import { makeAnchor } from "./anchor-map";

const NOTE = "Intro paragraph here.\n\nA paragraph with target words inside it and more text.\n\nA second paragraph with shared words in it.\n\n```\nsee plain_line here\nother = 22\n```\n\nAfter paragraph here.\n";
const T0 = 1757145600000;
const BODY = "Check this passage against the spec.";
const FRACS = [0.2, 0.4];                    // presses within the leading half of the first glyph, where the caret snaps to the glyph's start

/** A comment in the host's shape on the first occurrence of `quote`: the exact source slice, its context, its position. */
function comment(quote: string, n: number): Record<string, unknown> {
  const at = NOTE.indexOf(quote);
  assert.ok(at >= 0, "the note holds " + JSON.stringify(quote));
  return { id: (T0 + n) + "-" + at, author: "you", ts: T0 + n, body: BODY, anchor: makeAnchor(NOTE, { start: at, end: at + quote.length }), anchorAt: at, replies: [], resolved: false };
}
const PROSE = comment("target words", 1);    // a paragraph's words
const NEST_A = comment("shared words", 2);   // two comments on one passage: the later paint wraps inside the earlier's mark
const NEST_B = comment("shared words", 3);
const CODE = comment("plain_line", 4);       // a word in a fence's row
const id = (c: Record<string, unknown>): string => c.id as string;
const status = { ...STATUS, store: { ...STATUS.store, comments: [PROSE, NEST_A, NEST_B, CODE] }, storeMtimeNs: "1757145600000000061", unsent: { comments: [], replies: [], accepted: 0, rejected: 0, watermark: null } };

const markPainted = (page: any, cid: string): Promise<unknown> =>
  page.waitForFunction((c: string) => !!document.querySelector('.fileview-md mark[data-act="fcopen"][data-id="' + c + '"]'), cid, { timeout: 10000 });

type Points = { sx: number; sy: number; ex: number; ey: number; glyphW: number };
/** In the page: the press point on the first glyph of the mark with `cid`, at `frac` of the glyph's width, and the release point
 *  on its last glyph. */
function pointsOf(spec: { cid: string; frac: number }): Points {
  const mark = document.querySelector('.fileview-md mark[data-id="' + spec.cid + '"]') as HTMLElement | null;
  if (!mark) throw new Error("no mark for " + spec.cid);
  const w = document.createTreeWalker(mark, NodeFilter.SHOW_TEXT);
  const texts: Text[] = [];
  for (let t = w.nextNode() as Text | null; t; t = w.nextNode() as Text | null) if (t.data.length) texts.push(t);
  if (!texts.length) throw new Error("the mark holds no text");
  const first = texts[0], last = texts[texts.length - 1];
  const rect = (t: Text, off: number) => { const r = document.createRange(); r.setStart(t, off); r.setEnd(t, off + 1); return r.getBoundingClientRect(); };
  const a = rect(first, 0), b = rect(last, last.data.length - 1);
  return { sx: a.left + a.width * spec.frac, sy: a.top + a.height / 2, ex: b.right - b.width * 0.2, ey: b.top + b.height / 2, glyphW: a.width };
}
type MarkState = { id: string; tabindex: string | null; role: string | null };
type State = { marks: MarkState[]; active: string; activeId: string | null; selection: string; anchor: string; float: boolean; cards: Record<string, string | null> };
/** In the page: the marks with `ids`, the focused element, the selection and its anchor, the float, the cards' open state. */
function readState(ids: string[]): State {
  const marks = ids.map((cid) => { const m = document.querySelector('.fileview-md mark[data-id="' + cid + '"]'); return { id: cid, tabindex: m ? m.getAttribute("tabindex") : "no-mark", role: m ? m.getAttribute("role") : "no-mark" }; });
  const a = document.activeElement as HTMLElement | null;
  const sel = getSelection();
  const name = (n: Node | null): string => !n ? "none" : n.nodeType === 3 ? "#text(" + JSON.stringify((n as Text).data.slice(0, 16)) + ")" : (n as Element).tagName + ((n as Element).className ? "." + String((n as Element).className).split(/\s+/).join(".") : "");
  const f = document.querySelector(".fc-float") as HTMLElement | null;
  const cards: Record<string, string | null> = {};
  for (const cid of ids) { const h = document.querySelector('.fc-card-head[data-id="' + cid + '"]'); cards[cid] = h ? h.getAttribute("aria-expanded") : "no-head"; }
  return { marks, active: name(a), activeId: a && a.dataset ? a.dataset.id || null : null, selection: sel ? String(sel) : "", anchor: sel ? name(sel.anchorNode) + "@" + sel.anchorOffset : "none", float: !!f && !f.hidden, cards };
}
const clearSelection = (page: any): Promise<void> => page.evaluate(() => { getSelection()!.removeAllRanges(); });
const floatShown = (page: any): Promise<boolean> =>
  page.waitForFunction(() => { const f = document.querySelector(".fc-float") as HTMLElement | null; return !!f && !f.hidden; }, null, { timeout: 5000 }).then(() => true, () => false);

type Case = { what: string; pressed: string; ids: string[]; passage: string };
const CASES: Case[] = [
  { what: "a paragraph's words", pressed: id(PROSE), ids: [id(PROSE)], passage: "target words" },
  { what: "a nest of two marks on one passage, pressed on the inner", pressed: id(NEST_B), ids: [id(NEST_A), id(NEST_B)], passage: "shared words" },
  { what: "a word in a fence's row", pressed: id(CODE), ids: [id(CODE)], passage: "plain_line" },
];

test("in a browser, the real viewer and panel on the Files pane: a real drag begun on the leading half of a highlight's first glyph selects the passage and offers Comment with no card opened, in a paragraph, on a nest of two marks and in a fence's row alike (before: nothing selected, no float, the card opened), the marks wear no tabindex for the length of the press and wear it again at the release, when the pressed mark takes the focus; a plain click at the same point still opens the card, and the mark stands in the tab order after it", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const page = await browser.newPage({ viewport: { width: 900, height: 700 } });
    const errors: string[] = [];
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    const html = pageHtml("pane", { [REPORT]: NOTE }, MT);
    await page.route((u: URL) => u.href.startsWith(ORIGIN), (route: any) => route.fulfill({ status: 200, contentType: "text/html", body: html }));
    await page.goto(ORIGIN + "/");
    await page.evaluate(([p, sid, st]: [string, string, unknown]) => { (window as any).__status = st; (window as any).FV.openFileView(p, sid, null); }, [REPORT, SID, status]);
    await page.waitForFunction(() => document.querySelectorAll(".fileview-md pre .cl").length === 2, null, { timeout: 10000 });
    await frames(page, 2);
    await openPanel(page);
    for (const c of [PROSE, NEST_A, NEST_B, CODE]) await markPainted(page, id(c));
    await frames(page, 2);
    // the nest: the later comment's mark stands inside the earlier's
    const nested: boolean = await page.evaluate(([a, b]: [string, string]) => { const outer = document.querySelector('.fileview-md mark[data-id="' + a + '"]'); return !!outer && !!outer.querySelector('mark[data-id="' + b + '"]'); }, [id(NEST_A), id(NEST_B)]);
    assert.ok(nested, "the two comments on one passage nest their marks, the later inside the earlier");
    for (const c of CASES) {
      for (const frac of FRACS) {
        const what = c.what + ", pressed at " + frac + " of the first glyph";
        await clearSelection(page);
        await frames(page, 1);
        const before: State = await page.evaluate(readState, c.ids);
        for (const m of before.marks) assert.equal(m.tabindex, "0", what + ": the mark " + m.id + " wears tabindex 0 before the press");
        for (const cid of c.ids) assert.equal(before.cards[cid], "false", what + ": the card " + cid + " is closed before the press");
        const pts: Points = await page.evaluate(pointsOf, { cid: c.pressed, frac });
        assert.ok(pts.glyphW > 2, what + ": the first glyph has a width to press within: " + pts.glyphW);
        await page.mouse.move(pts.sx, pts.sy);
        await page.mouse.down();
        await frames(page, 1);
        const mid: State = await page.evaluate(readState, c.ids);
        for (const m of mid.marks) assert.equal(m.tabindex, null, what + ": mid-press the mark " + m.id + " wears no tabindex (before: 0, and the press focused it)");
        assert.ok(!c.ids.includes(mid.activeId || ""), what + ": mid-press no mark of the passage holds the focus: " + mid.active);
        assert.equal(mid.float, false, what + ": the press hid the float");
        await page.mouse.move((pts.sx + pts.ex) / 2, (pts.sy + pts.ey) / 2, { steps: 3 });
        await page.mouse.move(pts.ex, pts.ey, { steps: 6 });
        await page.mouse.up();
        await frames(page, 2);
        const shown = await floatShown(page);
        const after: State = await page.evaluate(readState, c.ids);
        assert.equal(after.selection.trim(), c.passage, what + ": the drag selected the passage (before: nothing; the anchor " + after.anchor + ")");
        assert.ok(shown, what + ": the release offered Comment (before: no float)");
        for (const cid of c.ids) assert.equal(after.cards[cid], "false", what + ": the release's click on the mark opened no card, the drag's own click stood down (before: the card opened)");
        for (const m of after.marks) assert.equal(m.tabindex + " " + m.role, "0 button", what + ": the mark " + m.id + " wears tabindex 0 and role button again at the release");
        assert.equal(after.activeId, c.pressed, what + ": the pressed mark holds the focus at the release, as the press would have given it: " + after.active);
      }
    }
    // a plain click at the same point: the card opens as before, the mark holds the focus, and Tab then Shift+Tab returns to it
    await clearSelection(page);
    await frames(page, 1);
    const pts: Points = await page.evaluate(pointsOf, { cid: id(PROSE), frac: FRACS[0] });
    await page.mouse.move(pts.sx, pts.sy);
    await page.mouse.down();
    await frames(page, 1);
    await page.mouse.up();
    await frames(page, 3);
    const clicked: State = await page.evaluate(readState, [id(PROSE)]);
    assert.equal(clicked.selection, "", "the click selected nothing");
    assert.equal(clicked.cards[id(PROSE)], "true", "the click opened the card");
    assert.equal(clicked.marks[0].tabindex, "0", "the clicked mark wears tabindex 0 after the click");
    assert.equal(clicked.activeId, id(PROSE), "the clicked mark holds the focus after the click: " + clicked.active);
    await page.keyboard.press("Tab");
    await frames(page, 1);
    const away: State = await page.evaluate(readState, [id(PROSE)]);
    assert.notEqual(away.activeId, id(PROSE), "Tab moves the focus off the mark: " + away.active);
    await page.keyboard.press("Shift+Tab");
    await frames(page, 1);
    const back: State = await page.evaluate(readState, [id(PROSE)]);
    assert.equal(back.activeId, id(PROSE), "Shift+Tab returns the focus to the mark, a Tab stop after the press: " + back.active);
    assert.deepEqual(errors, [], "no page errors");
    await page.close();
  });
});

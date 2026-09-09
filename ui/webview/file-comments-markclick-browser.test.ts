// A drag that selects text INSIDE a change mark ends in the Comment float, not the change card, over the REAL viewer and
// the REAL panel (plans/file-review.md, Slice 2, the marks' click rule; the fix of 2026-09-09). The user's requirement: a
// comment must be possible inside a tracked change other than by replying to the change. The mapping, startComment and
// the save already took such a passage; what blocked it by mouse was the mark itself, a control (tabIndex, role=button,
// data-act="fcchange"): a drag begun and ended inside one mark fires a click on the mark (the common ancestor of the press
// and the release), the click opened the card, showCard's centerOn scrolled the mark to the body's centre, and that
// scroll hid the float the same mouseup had just offered beside the selection (hideFloatOnScroll). The guard (the
// panel's dragClick): the click that ends a drag inside the mark is not a tap, and the mark's handler does nothing. The
// first test per engine drags a real mouse inside an insertion's mark, in Rendered (marks on) and in Raw, with the mark
// put OFF the body's centre so the old behaviour scrolled, in Chromium and Firefox, and reads: the change card not
// opened, the body not scrolled, the float standing, the composer opening on the selection from the float, Save posting
// an ordinary passage comment (no suggestionId) that the harness's canned reply then paints as its own card and
// highlight; a plain click on the mark still opening its card, with the scroll; and Enter on the focused mark, with the
// selection standing, still opening it (a click with no pointer behind it is never a drag's).
// The second test per engine holds the guard to the DRAG'S click, not to any selection's: a click on a mark while a
// selection stands elsewhere in the body is a click, and the card opens (the plan's Slice 2 sentence: a click or a tap on
// a change mark or a comment highlight opens its card). On ordinary text the press collapses a standing selection, so a
// plain mark never sees one; two marks do, in both engines (probed 2026-09-09): a deletion's label, whose struck text is
// generated content under user-select: none, and a mark inside an author's link, whose press collapses nothing. Before
// this test the guard read any non-collapsed selection with both ends in the body as a drag's, and with words selected
// in another paragraph a click on a deletion's label, or on a mark or a highlight inside a link, opened nothing and
// scrolled nothing, in Rendered and Raw and both engines, while the same click with no selection opened the card. The
// document carries the shapes: paragraph 30 ends in the session's insertion, paragraph 31 has a deletion's point after
// its second word, and paragraph 32 opens with an author's link whose label holds a second insertion and a comment's
// highlight. Raw shows the link's label as plain text, in no anchor: the press collapses the selection there and the
// card opens, the control beside the Rendered case.
// Skips LOUDLY without a playwright browser (CI installs none), as the other browser legs do. Legs await frames, never a
// timer. Synthetic values only: an invented report, /repo/notes-api paths, the placeholder sid, the session name "api",
// a link to example.invalid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as path from "node:path";
import { createRequire } from "node:module";
import { pageHtml, frames, openPanel, putAtTop, PARA, REPORT, SID, MT, ORIGIN, EXT, STATUS as BASE_STATUS } from "./real-viewer-leg";

const requireCjs = createRequire(path.join(EXT, "package.json"));
let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

// ── the document: sixty paragraphs; a session's insertion at the end of the thirtieth, its deletion in the thirty-first,
// an author's link opening the thirty-second with the session's second insertion and a comment of its own inside the label ─
const T0 = 1757145600000;
const INS = ", and the session added a warm-up step for the cache before the first request lands";
const P30 = PARA(30).slice(0, -1) + INS + ".";
/** Paragraph 31 lost a phrase after its second word: a deletion's zero-width point, whose struck label the sheet draws as
 *  generated content (`.fc-del::before`) under `user-select: none`, so a press on it collapses no selection. */
const DEL_AFTER = "Paragraph 31: lorem ipsum ";
const OLD = "for a while ";
/** Paragraph 32 opens with an author's link: its label holds the session's second insertion and a comment's highlight, so
 *  in Rendered both marks stand inside an anchor. */
const LINK_LABEL = "the cache notes for the warm-up step";
const LINK_URL = "https://example.invalid/cache";
const P32 = "Paragraph 32: see [" + LINK_LABEL + "](" + LINK_URL + ") " + PARA(32).slice("Paragraph 32: ".length);
const SRC = "# Report\n\n" + Array.from({ length: 60 }, (_, i) => (i + 1 === 30 ? P30 : i + 1 === 32 ? P32 : PARA(i + 1))).join("\n\n") + "\n";
const INS_AT = SRC.indexOf(INS);
const DEL_AT = SRC.indexOf(DEL_AFTER) + DEL_AFTER.length;
const LINK_AT = SRC.indexOf("[" + LINK_LABEL);
const INS2 = "for the warm-up step";
const INS2_AT = SRC.indexOf(INS2, LINK_AT);
const HL = "cache notes";
const HL_AT = SRC.indexOf(HL, LINK_AT);
const HUNK = { id: "h1", author: "api", ts: T0 - 30000, kind: "ins", curFrom: INS_AT, curTo: INS_AT + INS.length, baseFrom: INS_AT, baseTo: INS_AT, oldText: "", newText: INS, anchor: null };
const DEL = { id: "h2", author: "api", ts: T0 - 20000, kind: "del", curFrom: DEL_AT, curTo: DEL_AT, baseFrom: DEL_AT, baseTo: DEL_AT + OLD.length, oldText: OLD, newText: "", anchor: null };
const LINK_INS = { id: "h3", author: "api", ts: T0 - 10000, kind: "ins", curFrom: INS2_AT, curTo: INS2_AT + INS2.length, baseFrom: INS2_AT, baseTo: INS2_AT, oldText: "", newText: INS2, anchor: null };
const C0_ID = (T0 - 5000) + "-1";
/** The session's own comment on two words of the link's label, in the host's anchor shape. */
const C0 = { id: C0_ID, author: "api", authorId: SID, ts: T0 - 5000, body: "Which run's notes are these?", anchor: { quote: HL, prefix: SRC.slice(HL_AT - 24, HL_AT), suffix: SRC.slice(HL_AT + HL.length, HL_AT + HL.length + 24) }, replies: [], resolved: false };
const STATUS = { ...BASE_STATUS, hunks: [HUNK, DEL, LINK_INS], store: { ...BASE_STATUS.store, comments: [C0] } };
const NOTE = "Warm the cache from the last run, not from scratch.";
/** The status after the save: the same changes and the standing comment, plus the comment the harness's reply carries — an
 *  ordinary passage comment on the words selected inside the change's new text, no suggestionId, its anchor the host's shape. */
function saved(quote: string): Record<string, unknown> {
  const at = SRC.indexOf(quote, INS_AT);
  assert.ok(at >= 0, "the selected words are in the source");
  const c = { id: (T0 + 5) + "-3", author: "you", ts: T0 + 5, body: NOTE, anchor: { quote, prefix: SRC.slice(Math.max(0, at - 24), at), suffix: SRC.slice(at + quote.length, at + quote.length + 24) }, replies: [], resolved: false };
  return { ...STATUS, store: { ...STATUS.store, comments: [C0, c] }, storeMtimeNs: "1757145600000000012", unsent: { comments: [c.id], replies: [], accepted: 0, rejected: 0, watermark: null } };
}
const CID = (T0 + 5) + "-3";
const MARK = '.fileview-body [data-act="fcchange"][data-id="h1"]';
const DEL_MARK = '.fileview-body span.fc-del[data-act="fcchange"][data-id="h2"]';
const LINK_MARK = '.fileview-body mark.fc-ins[data-act="fcchange"][data-id="h3"]';
const HL_MARK = '.fileview-body mark.fc-hl[data-act="fcopen"][data-id="' + C0_ID + '"]';

type Scene = { cardOpen: boolean; cards: number; scrollTop: number; floatHidden: boolean; selected: string; composer: boolean; quote: string | null; focusedInput: boolean; view: "rendered" | "raw" };
const scene = (page: any): Promise<Scene> => page.evaluate(() => {
  const body = document.querySelector(".fileview-body") as HTMLElement;
  const aside = document.querySelector(".fileview-aside") as HTMLElement | null;
  const card = aside ? aside.querySelector('.fc-card[data-id="chg:h1"]') : null;
  const box = aside ? aside.querySelector(".fc-composer") as HTMLElement | null : null;
  const input = box ? box.querySelector(".fc-input") : null;
  return {
    cardOpen: !!card && card.classList.contains("open"), cards: aside ? aside.querySelectorAll(".fc-card").length : 0,
    scrollTop: body.scrollTop, floatHidden: (document.querySelector(".fc-float") as HTMLElement).hidden, selected: String(getSelection()),
    composer: !!box && !box.hidden && !!input, quote: box && !box.hidden ? (box.querySelector(".fc-quote")?.textContent ?? null) : null,   // the box is one element, hidden when no composer is open (renderComposer)
    focusedInput: !!input && document.activeElement === input, view: document.querySelector(".fileview-md") ? "rendered" : "raw",
  };
});

/** The page: the report open in the view, the status carrying the changes and the comment set before the open, the panel open,
 *  the marks painted. */
async function openWith(browser: any, raw: boolean): Promise<{ page: any; errors: string[] }> {
  const page = await browser.newPage({ viewport: { width: 1000, height: 600 } });
  const errors: string[] = [];
  page.on("pageerror", (e: Error) => { errors.push(e.message); });
  const html = pageHtml("pane", { [REPORT]: SRC }, MT);
  await page.route((u: URL) => u.href.startsWith(ORIGIN), (route: any) => route.fulfill({ status: 200, contentType: "text/html", body: html }));
  await page.goto(ORIGIN + "/");
  if (raw) await page.evaluate(() => { localStorage.setItem("romp:fileviewFmt", JSON.stringify({ md: "raw" })); });
  await page.evaluate(([p, sid, st]: [string, string, unknown]) => { (window as any).__status = st; (window as any).FV.openFileView(p, sid, null); }, [REPORT, SID, STATUS]);
  await page.waitForFunction((raw: boolean) => !!document.querySelector(raw ? ".fileview-body .fv-cl" : ".fileview-md > p"), raw, { timeout: 10000 });
  await frames(page, 2);
  await openPanel(page);
  await page.waitForFunction((sels: string[]) => sels.every((s) => !!document.querySelector(s)), [MARK, DEL_MARK, LINK_MARK, HL_MARK], { timeout: 10000 });
  await frames(page, 2);
  return { page, errors };
}

/** Paragraph 29 to the body's top edge, so the marks in paragraphs 30 to 32 stand in view, well above the centre: a click on
 *  one scrolls (centerOn brings the mark to the centre), and a drag over it stays clear of the top edge, where Chromium
 *  autoscrolls a selection drag. */
async function offCentre(page: any): Promise<void> {
  await page.evaluate(() => { getSelection()!.removeAllRanges(); });
  await putAtTop(page, "Paragraph 29:");
  await frames(page, 2);
}
/** The drag's line: a range over `from`..`to` of the first (or, with `last`, the last) text node of `to` characters or more
 *  directly inside one of the change's mark elements — one line of one element — its ends a pixel in. The comment's
 *  highlight, once painted, splits the mark around the selected words, so the last such node is the mark's tail. */
type Line = { x1: number; x2: number; y: number; text: string };
const lineIn = (page: any, from: number, to: number, last = false): Promise<Line> => page.evaluate(([sel, from, to, last]: [string, number, number, boolean]) => {
  const marks = Array.from(document.querySelectorAll(sel)) as HTMLElement[];
  const texts = marks.flatMap((m) => Array.from(m.childNodes).filter((n) => n.nodeType === 3 && (n.textContent || "").length >= to) as Text[]);
  const t = last ? texts[texts.length - 1] : texts[0];
  if (!t) throw new Error("no text node of " + to + " characters directly inside the mark: " + marks.map((m) => m.outerHTML).join(" | "));
  const r = document.createRange(); r.setStart(t, from); r.setEnd(t, to);
  const b = r.getBoundingClientRect();
  return { x1: b.left + 1, x2: b.right - 1, y: b.top + b.height / 2, text: t.data.slice(from, to) };
}, [MARK, from, to, last]);
/** A line over `from`..`to` of the first text node of `to` characters or more under the block (a Rendered block, a Raw row)
 *  whose text starts with `start`, as putAtTop finds blocks: the words of another paragraph, for a selection that stands in
 *  the body and touches no mark. */
const lineInBlock = (page: any, start: string, from: number, to: number): Promise<Line> => page.evaluate(([start, from, to]: [string, number, number]) => {
  const body = document.querySelector(".fileview-body")!;
  const blocks = document.querySelector(".fileview-md") ? ".fileview-md > *" : "code.hljs .fv-cl";
  const el = Array.from(body.querySelectorAll(blocks)).filter((e) => (e.textContent || "").indexOf(start) === 0)[0];
  if (!el) throw new Error("no block starting with " + JSON.stringify(start));
  const w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
  let t: Text | null = null;
  while ((t = w.nextNode() as Text | null)) if (t.data.length >= to) break;
  if (!t) throw new Error("no text node of " + to + " characters in the block: " + el.outerHTML.slice(0, 200));
  const r = document.createRange(); r.setStart(t, from); r.setEnd(t, to);
  const b = r.getBoundingClientRect();
  return { x1: b.left + 1, x2: b.right - 1, y: b.top + b.height / 2, text: t.data.slice(from, to) };
}, [start, from, to]);
/** A real drag along the line, left to right: press, four steps, release. */
async function drag(page: any, l: Line): Promise<void> {
  await page.mouse.move(l.x1, l.y);
  await page.mouse.down();
  await page.mouse.move(l.x2, l.y, { steps: 4 });
  await page.mouse.up();
  await frames(page, 3);                                 // the click after the release, then the scroll event a card's open would have fired
}
const posted = (page: any): Promise<any[]> => page.evaluate(() => (window as any).__posted);

// ── the second test's readings ──
/** The live selection against the body and the panel's marks: its text, whether both ends lie in the body, and whether either
 *  end lies in any element the panel painted as a control — the guard's inputs, read where the click reads them. */
type Standing = { text: string; collapsed: boolean; inBody: boolean; inMark: boolean };
const standing = (page: any): Promise<Standing> => page.evaluate(() => {
  const s = getSelection()!;
  const body = document.querySelector(".fileview-body")!;
  const marks = Array.from(body.querySelectorAll("[data-act]"));
  const a = s.anchorNode, f = s.focusNode;
  return { text: String(s), collapsed: s.isCollapsed, inBody: !!a && !!f && body.contains(a) && body.contains(f), inMark: marks.some((m) => (!!a && m.contains(a)) || (!!f && m.contains(f))) };
});
/** The mark's centre in the viewport, and whether a press there lands on the mark (elementFromPoint), with whether it stands
 *  inside an anchor and the user-select the sheet gives it. A deletion's point has no text of its own: its box is the
 *  generated label's. */
type Spot = { x: number; y: number; hit: boolean; inAnchor: boolean; userSelect: string };
const spotOf = (page: any, sel: string): Promise<Spot> => page.evaluate((sel: string) => {
  const el = document.querySelector(sel) as HTMLElement | null;
  if (!el) throw new Error("no mark " + sel);
  const b = el.getBoundingClientRect();
  const x = b.left + b.width / 2, y = b.top + b.height / 2;
  const hit = document.elementFromPoint(x, y);
  return { x, y, hit: hit === el || (!!hit && el.contains(hit)), inAnchor: !!el.closest("a[href]"), userSelect: getComputedStyle(el).userSelect };
}, sel);
/** Whether the card with this key is open, and the body's scrollTop. */
const cardAt = (page: any, key: string): Promise<{ open: boolean; scrollTop: number }> => page.evaluate((key: string) => {
  const card = document.querySelector('.fileview-aside .fc-card[data-id="' + key + '"]');
  return { open: !!card && card.classList.contains("open"), scrollTop: (document.querySelector(".fileview-body") as HTMLElement).scrollTop };
}, key);
/** Fold every open card (a click on its head), so the next case starts with the card closed. */
async function foldCards(page: any): Promise<void> {
  await page.evaluate(() => { for (const h of document.querySelectorAll(".fileview-aside .fc-card.open .fc-card-head")) (h as HTMLElement).click(); });
  await frames(page, 2);
}
/** The words of paragraph 33 selected by a real drag, the selection read back: non-collapsed, both ends in the body, neither
 *  in any mark — a selection the mark's click finds standing elsewhere. */
async function selectElsewhere(page: any, cell: string): Promise<void> {
  const l = await lineInBlock(page, "Paragraph 33:", 14, 25);
  await drag(page, l);
  const s = await standing(page);
  assert.equal(s.text, l.text, cell + ": the drag selected words of paragraph 33");
  assert.equal(s.collapsed, false, cell + ": …a non-collapsed selection");
  assert.equal(s.inBody, true, cell + ": …with both ends in the body");
  assert.equal(s.inMark, false, cell + ": …and neither end in any mark");
}
/** A real click on the mark's centre, with whatever selection stands: the card opens and the body scrolls to the mark, and no
 *  page opens (a mark inside an anchor: the click cancels the anchor's open). `key` is the card's. */
async function clickOpens(page: any, sel: string, key: string, cell: string, what: string): Promise<Spot> {
  const spot = await spotOf(page, sel);
  assert.equal(spot.hit, true, cell + ": a press at the centre of " + what + " lands on it");
  const before = await cardAt(page, key);
  assert.equal(before.open, false, cell + ": the card of " + what + " starts closed");
  const pages = page.context().pages().length;
  const sel0 = await standing(page);
  await page.mouse.click(spot.x, spot.y);
  await frames(page, 3);
  const after = await cardAt(page, key);
  assert.equal(after.open, true, cell + ": a click on " + what + (sel0.collapsed ? " with no selection" : " with a selection standing elsewhere in the body (" + JSON.stringify(sel0.text) + ")") + " opens its card");
  assert.notEqual(after.scrollTop, before.scrollTop, cell + ": …and scrolls the body to it");
  assert.equal(page.context().pages().length, pages, cell + ": …and opens no page (" + what + ")");
  return spot;
}

async function inEngine(t: any, name: string, body: (browser: any) => Promise<void>): Promise<void> {
  if (!pw) { t.skip("playwright is not installed under vscode-extension; the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw[name].launch(); }
  catch (e) { t.skip("no playwright " + name + " on this box; this leg needs it (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  try { await body(browser); } finally { await browser.close(); }
}

for (const name of ["chromium", "firefox"]) {
  test(`in ${name}, the real viewer, pane 1000x600, Rendered and Raw: a drag inside an insertion's mark opens no card and scrolls nothing, the float stands and the composer opens on the selection, Save posts a passage comment the reply paints as its own card and highlight; a plain click on the mark still opens its card and scrolls; Enter on the focused mark with the selection standing still opens it`, { timeout: 240000 }, async (t) => {
    await inEngine(t, name, async (browser) => {
      for (const raw of [false, true]) {
        const cell = name + (raw ? " Raw" : " Rendered");
        // ── the drag, the float, the composer, the save ──
        let { page, errors } = await openWith(browser, raw);
        await offCentre(page);
        let s = await scene(page);
        assert.equal(s.view, raw ? "raw" : "rendered", cell + ": the view");
        assert.equal(s.cardOpen, false, cell + ": the change card starts closed");
        const top0 = s.scrollTop;
        assert.ok(top0 > 0, cell + ": the body is scrolled to paragraph 29 (" + top0 + ")");
        const l = await lineIn(page, 2, 14);
        await drag(page, l);
        s = await scene(page);
        assert.equal(s.selected, l.text, cell + ": the drag selected the words inside the mark");
        assert.equal(s.cardOpen, false, cell + ": the click that ended the drag opened no card");
        assert.equal(s.scrollTop, top0, cell + ": …and the body did not scroll");
        assert.equal(s.floatHidden, false, cell + ": the Comment float stands beside the selection");
        await page.click(".fc-float");
        await frames(page, 2);
        s = await scene(page);
        assert.equal(s.composer, true, cell + ": the composer opened from the float");
        assert.equal(s.quote, l.text, cell + ": …on the selected words");
        assert.equal(s.focusedInput, true, cell + ": …with the box focused");
        assert.equal(s.cardOpen, false, cell + ": the change card is still closed");
        await page.keyboard.type(NOTE);
        await page.evaluate((st: unknown) => { (window as any).__status = st; }, saved(l.text));
        await page.click('.fileview-aside [data-act="fcsave"]');
        await page.waitForFunction((cid: string) => !!document.querySelector('.fileview-aside .fc-card[data-id="' + cid + '"]'), CID, { timeout: 10000 });
        await page.waitForFunction((cid: string) => !!document.querySelector('.fileview-body [data-act="fcopen"][data-id="' + cid + '"]'), CID, { timeout: 10000 });
        const m = (await posted(page)).filter((x: any) => x.type === "fileComments" && x.verb === "comment");
        assert.equal(m.length, 1, cell + ": one comment write went");
        assert.equal(m[0].args.note, NOTE, cell + ": …with the words typed");
        assert.equal(m[0].args.anchor && m[0].args.anchor.quote, l.text, cell + ": …anchored on the selected words");
        assert.equal("suggestionId" in m[0].args, false, cell + ": …an ordinary passage comment, not a reply on the change");
        s = await scene(page);
        assert.equal(s.composer, false, cell + ": the composer closed on the save");
        // ── the control: a plain click on the mark, on words the highlight does not cover, opens the change card and scrolls ──
        await offCentre(page);
        s = await scene(page);
        const top1 = s.scrollTop;
        const tail = await lineIn(page, 4, 6, true);
        await page.mouse.click((tail.x1 + tail.x2) / 2, tail.y);
        await frames(page, 3);
        s = await scene(page);
        assert.equal(s.cardOpen, true, cell + ": a plain click on the mark opens its card");
        assert.notEqual(s.scrollTop, top1, cell + ": …and scrolls the body to it (the scroll the guard spares a drag)");
        assert.deepEqual(errors, [], cell + ": no script error in the page");
        await page.close();
        // ── the keyboard: Enter on the focused mark opens its card whatever selection stands ──
        ({ page, errors } = await openWith(browser, raw));
        await offCentre(page);
        const top2 = (await scene(page)).scrollTop;
        const l2 = await lineIn(page, 2, 14);
        await drag(page, l2);
        s = await scene(page);
        assert.equal(s.selected, l2.text, cell + ": the drag selected the words again");
        assert.equal(s.cardOpen, false, cell + ": …and opened no card");
        assert.equal(s.scrollTop, top2, cell + ": …and scrolled nothing");
        await page.evaluate((sel: string) => { (document.querySelector(sel) as HTMLElement).focus(); }, MARK);
        await page.keyboard.press("Enter");
        await frames(page, 3);
        s = await scene(page);
        assert.equal(s.selected, l2.text, cell + ": the selection stood through the focus and the key");
        assert.equal(s.cardOpen, true, cell + ": Enter on the mark opens its card, the selection notwithstanding");
        assert.deepEqual(errors, [], cell + ": no script error in the page (keyboard)");
        await page.close();
      }
    });
  });

  test(`in ${name}, the real viewer, Rendered and Raw: a selection standing elsewhere in the body leaves a click on a mark a click — a deletion's label, whose press collapses no selection (user-select none), and, in Rendered, an insertion's mark and a comment's highlight inside an author's link, whose press collapses none either, open their cards and scroll as with no selection; in Raw the link's label is plain text, the press collapses the selection, and the card opens`, { timeout: 240000 }, async (t) => {
    await inEngine(t, name, async (browser) => {
      for (const raw of [false, true]) {
        const cell = name + (raw ? " Raw" : " Rendered");
        const { page, errors } = await openWith(browser, raw);
        assert.equal((await scene(page)).view, raw ? "raw" : "rendered", cell + ": the view");
        // ── the deletion's label, no selection: the control ──
        await offCentre(page);
        assert.equal((await standing(page)).collapsed, true, cell + ": no selection stands");
        const del = await clickOpens(page, DEL_MARK, "chg:h2", cell, "the deletion's label");
        assert.equal(del.userSelect, "none", cell + ": the label is under user-select none (its struck text is generated content)");
        // ── the deletion's label, with words of paragraph 33 selected: the press collapses nothing, and the click is a click ──
        await foldCards(page);
        await offCentre(page);
        await selectElsewhere(page, cell);
        await clickOpens(page, DEL_MARK, "chg:h2", cell, "the deletion's label");
        // ── the insertion's mark inside the author's link (Rendered; plain text in Raw), with the selection standing ──
        await foldCards(page);
        await offCentre(page);
        await selectElsewhere(page, cell);
        const ins = await clickOpens(page, LINK_MARK, "chg:h3", cell, "the insertion's mark in the link's label");
        assert.equal(ins.inAnchor, !raw, cell + (raw ? ": in Raw the label's words stand in no anchor" : ": in Rendered the mark stands inside the author's anchor"));
        // ── the comment's highlight inside the author's link, with the selection standing (fcopen) ──
        await foldCards(page);
        await offCentre(page);
        await selectElsewhere(page, cell);
        const hl = await clickOpens(page, HL_MARK, C0_ID, cell, "the comment's highlight in the link's label");
        assert.equal(hl.inAnchor, !raw, cell + (raw ? ": in Raw the highlight stands in no anchor" : ": in Rendered the highlight stands inside the author's anchor"));
        assert.deepEqual(errors, [], cell + ": no script error in the page");
        await page.close();
      }
    });
  });
}

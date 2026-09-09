// A drag that selects text INSIDE a change mark ends in the Comment float, not the change card, over the REAL viewer and
// the REAL panel (plans/file-review.md, Slice 2, the marks' click rule; the fix of 2026-09-09). The user's requirement: a
// comment must be possible inside a tracked change other than by replying to the change. The mapping, startComment and
// the save already took such a passage; what blocked it by mouse was the mark itself, a control (tabIndex, role=button,
// data-act="fcchange"): a drag begun and ended inside one mark fires a click on the mark (the common ancestor of the press
// and the release), the click opened the card, showCard's centerOn scrolled the mark to the body's centre, and that
// scroll hid the float the same mouseup had just offered beside the selection (hideFloatOnScroll). The guard (the
// panel's dragClick): a click arriving with a non-collapsed selection whose ends both lie in the body is the end of a
// drag, and the mark's handler does nothing. This leg drags a real mouse inside an insertion's mark, in Rendered (marks
// on) and in Raw, with the mark put OFF the body's centre so the old behaviour scrolled, in Chromium and Firefox, and
// reads: the change card not opened, the body not scrolled, the float standing, the composer opening on the selection
// from the float, Save posting an ordinary passage comment (no suggestionId) that the harness's canned reply then
// paints as its own card and highlight; a plain click on the mark still opening its card, with the scroll; and Enter on
// the focused mark, with the selection standing, still opening it (a click with no pointer behind it is never a drag's).
// Skips LOUDLY without a playwright browser (CI installs none), as the other browser legs do. Legs await frames, never a
// timer. Synthetic values only: an invented report, /repo/notes-api paths, the placeholder sid, the session name "api".
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as path from "node:path";
import { createRequire } from "node:module";
import { pageHtml, frames, openPanel, putAtTop, PARA, REPORT, SID, MT, ORIGIN, EXT, STATUS as BASE_STATUS } from "./real-viewer-leg";

const requireCjs = createRequire(path.join(EXT, "package.json"));
let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

// ── the document: sixty paragraphs, a session's insertion at the end of the thirtieth ─────────────────────────────
const T0 = 1757145600000;
const INS = ", and the session added a warm-up step for the cache before the first request lands";
const P30 = PARA(30).slice(0, -1) + INS + ".";
const SRC = "# Report\n\n" + Array.from({ length: 60 }, (_, i) => (i + 1 === 30 ? P30 : PARA(i + 1))).join("\n\n") + "\n";
const INS_AT = SRC.indexOf(INS);
const HUNK = { id: "h1", author: "api", ts: T0 - 30000, kind: "ins", curFrom: INS_AT, curTo: INS_AT + INS.length, baseFrom: INS_AT, baseTo: INS_AT, oldText: "", newText: INS, anchor: null };
const STATUS = { ...BASE_STATUS, hunks: [HUNK] };
const NOTE = "Warm the cache from the last run, not from scratch.";
/** The status after the save: the same change, and the comment the harness's reply carries — an ordinary passage comment on
 *  the words selected inside the change's new text, no suggestionId, its anchor the host's shape. */
function saved(quote: string): Record<string, unknown> {
  const at = SRC.indexOf(quote, INS_AT);
  assert.ok(at >= 0, "the selected words are in the source");
  const c = { id: (T0 + 5) + "-3", author: "you", ts: T0 + 5, body: NOTE, anchor: { quote, prefix: SRC.slice(Math.max(0, at - 24), at), suffix: SRC.slice(at + quote.length, at + quote.length + 24) }, replies: [], resolved: false };
  return { ...STATUS, store: { ...STATUS.store, comments: [c] }, storeMtimeNs: "1757145600000000012", unsent: { comments: [c.id], replies: [], accepted: 0, rejected: 0, watermark: null } };
}
const CID = (T0 + 5) + "-3";
const MARK = '.fileview-body [data-act="fcchange"][data-id="h1"]';

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

/** The page: the report open in the view, the status carrying the insertion set before the open, the panel open, the mark painted. */
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
  await page.waitForFunction((sel: string) => !!document.querySelector(sel), MARK, { timeout: 10000 });
  await frames(page, 2);
  return { page, errors };
}

/** Paragraph 29 to the body's top edge, so the mark at the end of paragraph 30 stands in view, well above the centre: a click
 *  on it scrolls (centerOn brings the mark to the centre), and a drag over it stays clear of the top edge, where Chromium
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
/** A real drag along the line, left to right: press, four steps, release. */
async function drag(page: any, l: Line): Promise<void> {
  await page.mouse.move(l.x1, l.y);
  await page.mouse.down();
  await page.mouse.move(l.x2, l.y, { steps: 4 });
  await page.mouse.up();
  await frames(page, 3);                                 // the click after the release, then the scroll event a card's open would have fired
}
const posted = (page: any): Promise<any[]> => page.evaluate(() => (window as any).__posted);

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
}

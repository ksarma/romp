// The focus follow-on (plans/file-review.md, "The focus follow-on (2026-09-08)" under the margin-layout note) under the
// REAL viewer, in headless Chromium over real-viewer-leg.ts's page: file-view.ts bundled as the webview build bundles it,
// the Comments panel registered by the module itself, the Files pane's sheet, a pane of 1000x600. The panel-alone legs
// (file-comments-focus-browser.test.ts, file-comments-margin-fixes-browser.test.ts) mount the panel over a body they paint
// themselves, with a seam whose setMode, reload and scrollToOffset do nothing and whose onRendered hooks the test fires by
// hand; none of them drives the viewer's own order of events around a focused card — the pass inside fireRendered, then the
// seat that puts the reader's top block back (renderBody, textSizeControl's step, the width repaint), the landing pressHold parks
// while a pointer is pressed over the body — and the merge audit of 2026-09-09 named the gap (its F4). This leg opens the
// panel, arms the focus with a click on a comment's highlight, and after each of Raw and Rendered, one A+, a session's
// write landing through the poll and a reload run under a held press asserts the card level with its mark within a pixel,
// the track's scroll the body's within a pixel after two frames, and no script error. Whole-in-the-track is asserted after
// the click and after the view round trip only: after A+ or a reload the seat keeps the reader's top block, so a level card
// may sit past the track's box with nothing wrong. Then the Reveal step, the defect the audit confirmed (its F1): a tall
// change card unfolded with Show more is the focus; the Reveal of a card standing under it — a deletion's, and a comment's
// whose passage is an HTML comment block the Rendered view cannot paint — switches to Raw, and the revealed card lands
// level with its Raw mark, whole in the track's box, not pushed. Before the fix reveal() never set the focus, so the swap's
// pass laid the margin on the tall card still and pushed the revealed card under it, wholly outside the track's box while
// its passage was centered in the body. Legs await frames and paint counts, never a timer. Skips LOUDLY without a
// playwright browser (CI installs none), as the other legs do. Synthetic values only: an invented report, /repo/notes-api
// paths, the placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, pageHtml, frames, paintsReach, REPORT, SID, MT, MT2, ORIGIN, STATUS as BASE_STATUS } from "./real-viewer-leg";

const T0 = 1757145600000;
const MT3 = "1757145600000000019";
const PARA = (i: number): string => "Paragraph " + i + " of the report says something about the cache, the latency and the plan for the next release, in enough words to wrap onto a second line.";
// the replaced paragraph: the session rewrote a one-line paragraph 5 as ten sentences, so its card, open and unfolded,
// stands several hundred pixels tall over the paragraphs under it
const OLD = "Paragraph 5 of the report was one line about the cache.";
const SENTENCE = (i: number): string => "Sentence " + i + " of the new paragraph 5 says more about the cache, the latency budget, the plan for the next release and the reasons the team settled on it.";
const NEW = Array.from({ length: 10 }, (_, i) => SENTENCE(i + 1)).join(" ");
// an HTML comment block after paragraph 7: the Rendered view drops it, so a comment on its words has no highlight there
// and its card is loose, with Reveal; the Raw view shows the row and paints the highlight
const NOTE = "<!-- Reviewer note: check the latency figure against the staging run before the release goes out. -->";
const blocks = (): string[] => { const out: string[] = []; for (let i = 1; i <= 60; i++) { out.push(i === 5 ? NEW : PARA(i)); if (i === 7) out.push(NOTE); } return out; };
const SRC = "# Report\n\n" + blocks().join("\n\n") + "\n";
const ABOVE = Array.from({ length: 12 }, (_, i) => "Inserted " + (i + 1) + ": new text a session wrote above the reader's place, long enough to wrap once or twice.").join("\n\n") + "\n\n";
const SRC2 = "# Report\n\n" + ABOVE + blocks().join("\n\n") + "\n";                  // a write ABOVE the marks: every offset moves
const SRC3 = SRC2 + "\n" + Array.from({ length: 5 }, (_, i) => "Appended " + (i + 1) + ": text added at the end.").join("\n\n") + "\n";   // a write BELOW: the offsets stand
const A = { id: (T0 + 1) + "-6", author: "you", ts: T0 + 1, body: "Say which cache.", anchor: { quote: "Sentence 4 of the new paragraph 5", prefix: "settled on it. ", suffix: " says more" }, replies: [], resolved: false };
const B = { id: (T0 + 2) + "-9", author: "you", ts: T0 + 2, body: "Which run is that?", anchor: { quote: "check the latency figure", prefix: "Reviewer note: ", suffix: " against the staging" }, replies: [], resolved: false };
/** The hunks over `src`: the substitution of paragraph 5, and a deletion's point inside paragraph 7 (a word the session took out). */
const hunksFor = (src: string) => {
  const at = src.indexOf(NEW), del = src.indexOf(PARA(7)) + "Paragraph 7 of the report ".length;
  return [
    { id: "h1", author: "api", ts: T0 - 30000, kind: "sub", curFrom: at, curTo: at + NEW.length, baseFrom: at, baseTo: at + OLD.length, oldText: OLD, newText: NEW, anchor: null },
    { id: "h2", author: "api", ts: T0 - 20000, kind: "del", curFrom: del, curTo: del, baseFrom: del, baseTo: del + 5, oldText: "once ", newText: "", anchor: null },
  ];
};
const statusFor = (src: string) => ({ ...BASE_STATUS, store: { ...BASE_STATUS.store, comments: [A, B] }, hunks: hunksFor(src), unsent: { comments: [A.id, B.id], replies: [], accepted: 0, rejected: 0, watermark: null } });
const KEYS: Record<string, string> = { chg: "chg:h1", del: "chg:h2", a: A.id, b: B.id };

type Box = { top: number; bottom: number; height: number };
type Card = Box & { open: boolean; more: boolean; pushed: string | null; reveal: boolean };
type Scene = {
  margin: boolean; view: "rendered" | "raw"; cards: Record<string, Card | null>; marks: Record<string, Box | null>;
  bodyScroll: number; trackScroll: number; bodyBox: Box; trackBox: Box; paints: number; size: string | undefined; fetches: number;
};
/** The scene: each card's box, state and Reveal button; each mark's box (a change's marks are several: the highest is the
 *  card's, as the pass reads it — markTop skips a mark with no box at all, and so does this). */
const scene = (page: any): Promise<Scene> => page.evaluate((keys: Record<string, string>) => {
  const body = document.querySelector(".fileview-body") as HTMLElement;
  const aside = document.querySelector(".fileview-aside") as HTMLElement;
  const track = aside.querySelector(".fc-sec-cards") as HTMLElement;
  const box = (el: Element): Box => { const r = el.getBoundingClientRect(); return { top: r.top, bottom: r.bottom, height: r.height }; };
  const cards: Record<string, Card | null> = {}, marks: Record<string, Box | null> = {};
  for (const [name, key] of Object.entries(keys)) {
    const card = aside.querySelector('.fc-card[data-id="' + key + '"]') as HTMLElement | null;
    cards[name] = card ? { ...box(card), open: card.classList.contains("open"), more: card.classList.contains("fc-more"), pushed: card.dataset.pushed ?? null, reveal: !!card.querySelector('[data-act="fcreveal"]') } : null;
    const act = key.startsWith("chg:") ? "fcchange" : "fcopen", id = key.startsWith("chg:") ? key.slice(4) : key;
    const ms = Array.from(body.querySelectorAll('[data-act="' + act + '"][data-id="' + id + '"]')).map((m) => m.getBoundingClientRect()).filter((r) => !(r.width === 0 && r.height === 0)).map((r) => ({ top: r.top, bottom: r.bottom, height: r.height }));
    marks[name] = ms.length ? ms.reduce((a, b) => (b.top < a.top ? b : a)) : null;
  }
  const w = window as any;
  return {
    margin: aside.classList.contains("fc-margin"), view: document.querySelector(".fileview-md") ? "rendered" : "raw", cards, marks,
    bodyScroll: body.scrollTop, trackScroll: track.scrollTop, bodyBox: box(body), trackBox: box(track), paints: w.__paints,
    size: (document.querySelector(".fileview") as HTMLElement).dataset.fvText, fetches: w.__fetches,
  };
}, KEYS);
const near = (a: number, b: number, msg: string, tol = 1): void => assert.ok(Math.abs(a - b) <= tol, msg + ": " + a + " vs " + b);
const wholeIn = (c: Box, of: Box): boolean => c.top >= of.top - 1 && c.bottom <= of.bottom + 1;
const markSel = (key: string): string => key.startsWith("chg:") ? '.fileview-body [data-act="fcchange"][data-id="' + key.slice(4) + '"]' : '.fileview-body [data-act="fcopen"][data-id="' + key + '"]';
const cardSel = (key: string, inner = ""): string => '.fileview-aside .fc-card[data-id="' + key + '"]' + (inner ? " " + inner : "");
const click = (page: any, sel: string): Promise<void> => page.evaluate((sel: string) => { const n = document.querySelector(sel) as HTMLElement | null; if (!n) throw new Error("nothing at " + sel); n.click(); }, sel);
/** The action bar's view toggle: the button whose label is the view's name. */
const clickView = (page: any, label: "Raw" | "Rendered"): Promise<void> => page.evaluate((label: string) => { const b = Array.from(document.querySelectorAll(".fileview .fileview-btn")).find((x) => x.textContent === label) as HTMLElement | undefined; if (!b) throw new Error("no view button " + label); b.click(); }, label);
const paints = (page: any): Promise<number> => page.evaluate(() => (window as any).__paints);
const changeMarked = (page: any): Promise<unknown> => page.waitForFunction(() => !!document.querySelector('.fileview-body [data-act="fcchange"][data-id="h1"]'), null, { timeout: 10000 });

/** The focused card's seat: level with its mark within a pixel, the track's scroll the body's within a pixel, not pushed;
 *  whole in the track's box only where the step's own scroll put it there (`inTrack`). */
function seated(s: Scene, name: string, cell: string, inTrack: boolean): void {
  assert.equal(s.margin, true, cell + ": the margin layout");
  const card = s.cards[name], mark = s.marks[name];
  assert.ok(card && mark, cell + ": the card and its mark are present: " + JSON.stringify({ card, mark }));
  near(card!.top, mark!.top, cell + ": the card is level with its mark");
  near(s.trackScroll, s.bodyScroll, cell + ": the track's scroll is the body's");
  assert.equal(card!.pushed, null, cell + ": the focused card is not pushed");
  if (inTrack) assert.ok(wholeIn(card!, s.trackBox), cell + ": the card is whole in the track's box: " + JSON.stringify(card) + " in " + JSON.stringify(s.trackBox));
}

test("in a browser, the real viewer, pane 1000x600: a comment's card made the focus by its highlight stays level with its mark, the track locked to the body, across Raw and Rendered, one A+, a session's write landing through the poll and a reload run under a held press; then Reveal on a card under an unfolded tall change card — a deletion's, and a comment's on an HTML comment block Rendered cannot paint — lays the card level with its Raw mark, whole in the track's box, not pushed (before the fix the swap's pass kept the tall card as the focus and pushed the revealed card under it, outside the track)", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const page = await browser.newPage({ viewport: { width: 1000, height: 600 } });
    const errors: string[] = [];
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    const html = pageHtml("pane", { [REPORT]: SRC }, MT);
    await page.route((u: URL) => u.href.startsWith(ORIGIN), (route: any) => route.fulfill({ status: 200, contentType: "text/html", body: html }));
    await page.goto(ORIGIN + "/");
    await page.evaluate(([p, sid, st]: [string, string, unknown]) => { (window as any).__status = st; (window as any).FV.openFileView(p, sid, null); }, [REPORT, SID, statusFor(SRC)]);
    await page.waitForFunction(() => !!document.querySelector(".fileview-md > p"), null, { timeout: 10000 });
    await page.waitForFunction(() => { const u = document.querySelector(".fileview-fc"); return !!u && !(u as HTMLElement).hidden; }, null, { timeout: 5000 });
    await page.click(".fileview-fc button");
    await page.waitForFunction(() => !!document.querySelector(".fileview-aside .fc-card"), null, { timeout: 5000 });
    await frames(page, 3);
    let s = await scene(page);
    // the fixture: the change and the comment on its new text are marked in Rendered; the comment on the HTML comment block
    // is not (its card is loose)
    assert.equal(s.margin, true, "the margin layout at 1000px");
    assert.ok(s.marks.chg && s.marks.a, "the change and comment A are marked in Rendered: " + JSON.stringify(s.marks));
    assert.equal(s.marks.b, null, "comment B's passage, an HTML comment block, has no Rendered mark");
    // the tall change card open from its mark, then the focus on comment A's card by its highlight
    await click(page, markSel(KEYS.chg)); await frames(page, 3);
    await click(page, markSel(KEYS.a)); await frames(page, 3);
    s = await scene(page);
    assert.equal(s.cards.a!.open, true, "comment A's card opened");
    seated(s, "a", "after the highlight click", true);
    assert.ok(s.cards.chg!.top < s.marks.chg!.top - 1, "the change card moved up from its mark to clear the focus: " + s.cards.chg!.top + " vs " + s.marks.chg!.top);
    // (a) Raw, then Rendered: renderBody's pass inside fireRendered, then the seat of the reader's top block
    let n = s.paints;
    await clickView(page, "Raw"); await paintsReach(page, n + 1); await frames(page, 3);
    s = await scene(page); assert.equal(s.view, "raw", "(a) the Raw view"); seated(s, "a", "(a) after Raw", false);
    n = s.paints;
    await clickView(page, "Rendered"); await paintsReach(page, n + 1); await frames(page, 3);
    s = await scene(page); assert.equal(s.view, "rendered", "(a) the Rendered view"); seated(s, "a", "(a) after Rendered", true);
    // (b) A+: textSizeControl's set runs the step bracket: its repaint, then its seat
    n = s.paints;
    await page.click('button[aria-label="Larger text"]'); await paintsReach(page, n + 1); await frames(page, 3);
    s = await scene(page); assert.notEqual(s.size, "100", "(b) the text size stepped: " + s.size); seated(s, "a", "(b) after A+", false);
    // (c) a session's write above the marks lands through the poll: the status names the new mtime, the panel asks the
    // viewer to reload, the fetch brings the new bytes, renderBody paints (the pass) and seats the top block
    n = s.paints;
    await page.evaluate(([p, src, mt, st]: [string, string, string, unknown]) => { const w = window as any; w.__docs[p] = src; w.__mtime = mt; w.__status = st; }, [REPORT, SRC2, MT2, statusFor(SRC2)]);
    await paintsReach(page, n + 1); await frames(page, 3);
    s = await scene(page); seated(s, "a", "(c) after the poll's reload", false);
    await changeMarked(page); await frames(page, 3);
    s = await scene(page); seated(s, "a", "(c) once the change is marked again", false);
    // (d) a reload under a held press: the landing waits while a primary pointer is pressed over the body (pressHold) and
    // runs on the release
    n = s.paints;
    await page.evaluate(([p, src, mt, st]: [string, string, string, unknown]) => { const w = window as any; w.__docs[p] = src; w.__mtime = mt; w.__status = st; }, [REPORT, SRC3, MT3, statusFor(SRC3)]);
    await page.mouse.move(40, s.bodyBox.top + 20); await page.mouse.down();
    const fetched: number = await page.evaluate(() => { const w = window as any; w.__seam.reload(); return w.__fetches; });
    await frames(page, 3);
    assert.equal(await paints(page), n, "(d) the landing is parked while the pointer is pressed (fetched " + fetched + ")");
    await page.mouse.up();
    await paintsReach(page, n + 1); await frames(page, 3);
    s = await scene(page); seated(s, "a", "(d) after the release ran the parked landing", false);
    await changeMarked(page); await frames(page, 3);
    s = await scene(page); seated(s, "a", "(d) once the change is marked again", false);
    assert.deepEqual(errors, [], "no script error through the seat steps");
    // (e) the Reveal step, in the audit's order. The deletion's card and comment B's are opened by their heads first (a
    // card offers Reveal in its action row, rendered open; the head click makes the opened card the focus, which the pass
    // spends on a loose one). Then the change card is the focus again and unfolded with Show more, so it stands several
    // hundred pixels over the cards under it; Reveal on the deletion's card switches to Raw, and the card lands level with
    // its Raw mark, whole in the track's box, not pushed
    await click(page, cardSel(KEYS.del, ".fc-card-head")); await frames(page, 3);
    await click(page, cardSel(KEYS.b, ".fc-card-head")); await frames(page, 3);
    s = await scene(page);
    assert.equal(s.cards.del!.open && s.cards.b!.open, true, "(e) the deletion's card and comment B's are open");
    assert.equal(s.cards.del!.reveal, true, "(e) the deletion's card offers Reveal");
    assert.equal(s.cards.b!.reveal, true, "(e) comment B's card offers Reveal, its passage unpainted in Rendered");
    await click(page, markSel(KEYS.chg)); await frames(page, 3);
    await click(page, cardSel(KEYS.chg, '[data-act="fcclip"]')); await frames(page, 3);
    s = await scene(page);
    assert.equal(s.cards.chg!.more, true, "(e) the change card is unfolded");
    assert.ok(s.cards.chg!.height > 400, "(e) the unfolded change card is tall: " + s.cards.chg!.height);
    near(s.cards.chg!.top, s.marks.chg!.top, "(e) the change card is the focus, level with its mark");
    n = s.paints;
    await click(page, cardSel(KEYS.del, '[data-act="fcreveal"]')); await paintsReach(page, n + 1); await frames(page, 3);
    s = await scene(page);
    assert.equal(s.view, "raw", "(e) Reveal switched to Raw");
    assert.ok(s.marks.del, "(e) the deletion's point is marked in Raw");
    // the fixture holds: at its mark the unfolded change card would reach past the deletion's mark, so the push-down rule
    // alone would lay the deletion's card under it
    assert.ok(s.marks.chg!.top + s.cards.chg!.height + 8 > s.marks.del!.top, "(e) the tall card at its mark reaches past the deletion's mark: " + (s.marks.chg!.top + s.cards.chg!.height + 8) + " vs " + s.marks.del!.top);
    seated(s, "del", "(e) after Reveal on the deletion's card", true);
    // the second case: back in Rendered with the change card the focus, Reveal on comment B's loose card
    n = s.paints;
    await clickView(page, "Rendered"); await paintsReach(page, n + 1); await frames(page, 3);
    await click(page, markSel(KEYS.chg)); await frames(page, 3);
    s = await scene(page);
    assert.equal(s.view, "rendered", "(e) the Rendered view again");
    assert.equal(s.marks.b, null, "(e) comment B is loose in Rendered");
    assert.equal(s.cards.b!.open && s.cards.b!.reveal, true, "(e) and its open card offers Reveal");
    near(s.cards.chg!.top, s.marks.chg!.top, "(e) the change card is the focus, level with its mark");
    n = s.paints;
    await click(page, cardSel(KEYS.b, '[data-act="fcreveal"]')); await paintsReach(page, n + 1); await frames(page, 3);
    s = await scene(page);
    assert.equal(s.view, "raw", "(e) Reveal switched to Raw");
    assert.ok(s.marks.b, "(e) comment B's passage is highlighted in Raw");
    assert.ok(s.marks.chg!.top + s.cards.chg!.height + 8 > s.marks.b!.top, "(e) the tall card at its mark reaches past comment B's mark: " + (s.marks.chg!.top + s.cards.chg!.height + 8) + " vs " + s.marks.b!.top);
    seated(s, "b", "(e) after Reveal on comment B's card", true);
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});

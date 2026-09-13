// The arrivals dot on a display formula's stamped box that TWO arrivals cover, seen one at a time, over the REAL viewer and the REAL
// Comments panel in headless Chromium (plans/markdown-viewer.md Slice 8, item 5; the landing's review, round 1 over the branch
// offered as the PR). Two comments on one formula share the one `.katex-display` box (file-comments.ts coverBox: `data-ids` the
// covering set, `data-id` the front), and a comment of the session's arriving after the open puts `data-new`, the dot, on its card
// and on its elements (markNew). A gesture of the person's marks every arrival whose card is on screen seen and takes the dot off
// its card and its elements in place (reflectSeen); for a stamped box that rule has a guard: the box keeps `data-new` while another
// comment covering it stands unseen, since the dot says a comment on the formula is unread, and one still is. No suite reached
// that guard, so a mutation deleting the box's `data-new` unconditionally left every suite green (the review's finding);
// file-comments-block-paint.test.ts pins it over the stand-in, this leg over the real layout. Here a long note (twelve paragraphs
// before the formula, so the body scrolls) is opened on the Files pane at 900 px, where the aside is the margin layout: each
// card is placed level with its mark in a track (`.fc-sec-cards`) that mirrors the body's scroll, and a card's place is on screen
// when its top lies inside the track's box (entryShown). Three comments of the session's are delivered as the reply to the
// panel's status ask: two on the formula (the later placed under the earlier: two cards cannot share a place) and one on the
// paragraph above it, the control. The track is scrolled so the earlier formula card's top and the control's lie inside its box
// and the later formula card's top sits exactly at the box's bottom edge, outside (the rule is a strict `<`); a real click on
// the body's text is the gesture: the two cards inside lose their dots, the control's mark loses its dot, and the box KEEPS
// data-new while the later card stands unseen (before: the box's dot came off here). The track scrolled forty pixels on, the
// later card inside, a second click takes the dot off that card and off the box. The scene asserts its own geometry (the
// layout is the margin's, every card placed, the predicate as stated for each card) so a layout change fails it loudly instead
// of passing it vacuously. Skips LOUDLY without a playwright browser (CI installs none), as the other browser legs do.
// Synthetic values only: an invented note, /repo/notes-api paths, the placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { inBrowser, openPanel, frames, pageHtml, ORIGIN, REPORT, SID, MT, STATUS, EXT, PARA } from "./real-viewer-leg";
import { makeAnchor } from "./anchor-map";

const KATEX_CSS = fs.readFileSync(path.join(EXT, "node_modules", "katex", "dist", "katex.min.css"), "utf8");
const FORMULA_Q = "$$\n\\sum_i i\n$$";
const NOTE = "# Title\n\n" + Array.from({ length: 12 }, (_, i) => PARA(i + 1)).join("\n\n") + "\n\n" + FORMULA_Q + "\n\nPara after the formula.\n\nLast para.\n";
const T0 = 1757145600000;
const BODY = "Check this against the spec.";

/** A comment in the host's shape on the note's passage `quote`: the exact source slice, its context, its position; the person's
 *  by default, the session's (another author, so an arrival) with `session`. */
function comment(quote: string, k: number, session = false): Record<string, unknown> {
  const at = NOTE.indexOf(quote);
  assert.ok(at >= 0, "the note holds " + JSON.stringify(quote));
  const c: Record<string, unknown> = { id: (T0 + k) + "-" + at, author: "you", ts: T0 + k, body: BODY, anchor: makeAnchor(NOTE, { start: at, end: at + quote.length }), anchorAt: at, replies: [], resolved: false };
  return session ? { ...c, author: "api", authorId: SID } : c;
}
const FINAL = comment("Last para.", 1);                    // the pass's sentinel: its mark is what the open waits for
const CONTROL = comment("Paragraph 12: lorem", 10, true);  // the paragraph above the formula: its card placed above the formula's, its mark the control
const A = comment(FORMULA_Q, 11, true);                    // the earlier comment on the formula: its card level with the box
const B = comment(FORMULA_Q, 12, true);                    // the later: pushed under A's card (two cards cannot share a place)
const id = (c: Record<string, unknown>): string => c.id as string;
const withComments = (comments: Record<string, unknown>[], n: number): Record<string, unknown> =>
  ({ ...STATUS, store: { ...STATUS.store, comments }, storeMtimeNs: "17571456000000000" + (30 + n), unsent: { comments: [], replies: [], accepted: 0, rejected: 0, watermark: null } });

/** Wait for the comment's element in the view's body: a mark or a box carrying its id, or a box whose covering set names it (the
 *  earlier of two comments on one formula stands in `data-ids` alone, the later being the front). */
const markPainted = (page: any, cid: string): Promise<unknown> =>
  page.waitForFunction((c: string) => !!document.querySelector('.fileview-body [data-act="fcopen"][data-id="' + c + '"]')
    || Array.from(document.querySelectorAll('.fileview-body [data-act="fcopen"][data-ids]')).some((e) => (e.getAttribute("data-ids") || "").split(" ").includes(c)), cid, { timeout: 10000 });
/** Deliver `status` as the reply to the panel's LAST status ask (a fileCommentsResult, as the harness's poster answers one), then
 *  wait for every comment of `ids` to be painted (md-config-math-block-paint-browser.test.ts's deliver). */
async function deliver(page: any, status: Record<string, unknown>, ids: string[]): Promise<void> {
  await page.evaluate((st: Record<string, unknown>) => {
    const w = window as any;
    w.__status = st;
    const last = (w.__posted as { type?: string; reqId?: unknown }[]).filter((m) => m && m.type === "fileComments").pop();
    window.dispatchEvent(new MessageEvent("message", { data: Object.assign({ type: "fileCommentsResult", reqId: last ? last.reqId : undefined, fileMtimeNs: w.__mtime }, st) }));
  }, status);
  for (const c of ids) await markPainted(page, c);
  await frames(page, 2);
}
type Geo = { margin: boolean; track: { scrollTop: number; clientHeight: number; scrollHeight: number }; tops: Record<string, number | null>; shown: Record<string, boolean> };
/** In the page: the layout (the aside wears fc-margin), the track's scroll state, and each card's placed top (its style.top in px;
 *  null when unplaced) with entryShown's rule applied to it: the top inside [scrollTop, scrollTop + clientHeight). */
function readGeo(ids: string[]): Geo {
  const root = document.querySelector(".fileview-aside") as HTMLElement;
  const track = root.querySelector(".fc-sec-cards") as HTMLElement;
  const tops: Record<string, number | null> = {}, shown: Record<string, boolean> = {};
  for (const c of ids) {
    const card = track.querySelector('.fc-card[data-id="' + c + '"]') as HTMLElement | null;
    const t = card && card.style.top ? parseFloat(card.style.top) : null;
    tops[c] = t;
    shown[c] = t !== null && t >= track.scrollTop && t < track.scrollTop + track.clientHeight;
  }
  return { margin: root.classList.contains("fc-margin"), track: { scrollTop: track.scrollTop, clientHeight: track.clientHeight, scrollHeight: track.scrollHeight }, tops, shown };
}
type Dots = { box: string | null; ids: string | null; cards: Record<string, string | null>; controlMark: string | null };
/** In the page: data-new on the formula's box, its covering set, data-new on each card, and on the control's mark. */
function readDots(spec: { ids: string[]; control: string }): Dots {
  const d = document.querySelector(".fileview-md > .katex-display") as HTMLElement | null;
  const cards: Record<string, string | null> = {};
  for (const c of spec.ids) { const k = document.querySelector('.fileview-aside .fc-card[data-id="' + c + '"]'); cards[c] = k ? k.getAttribute("data-new") : "no-card"; }
  const m = document.querySelector('.fileview-md mark.fc-hl[data-id="' + spec.control + '"]');
  return { box: d ? d.getAttribute("data-new") : "no-box", ids: d ? d.getAttribute("data-ids") : null, cards, controlMark: m ? m.getAttribute("data-new") : "no-mark" };
}
/** Scroll the track (the margin's card column, which the body follows) to `y` and settle. */
async function scrollTrack(page: any, y: number): Promise<void> {
  await page.evaluate((v: number) => { (document.querySelector(".fileview-aside .fc-sec-cards") as HTMLElement).scrollTop = v; }, y);
  await frames(page, 3);
}
/** A gesture of the person's: a real primary click on the body's text, in a paragraph on screen that carries no mark (a press on a
 *  highlight would open a card; the body's own text opens nothing). */
async function clickBodyText(page: any): Promise<void> {
  const pt: { x: number; y: number } | null = await page.evaluate(() => {
    const body = document.querySelector(".fileview-body") as HTMLElement;
    const box = body.getBoundingClientRect();
    for (const p of Array.from(document.querySelectorAll(".fileview-md > p")) as HTMLElement[]) {
      if (p.querySelector("mark")) continue;
      const r = p.getBoundingClientRect();
      if (r.top >= box.top + 4 && r.bottom <= box.bottom - 4 && r.height > 0) return { x: r.left + 12, y: r.top + r.height / 2 };
    }
    return null;
  });
  assert.ok(pt, "a paragraph without a mark stands whole inside the body's box to click on");
  await page.mouse.click(pt!.x, pt!.y);
  await frames(page, 3);
}

test("in a browser, the real viewer and panel on the Files pane at 900 px (the margin layout): two comments of the session's on the one `$$` block and one on the paragraph above it arriving after the open put data-new on the shared box, the three cards and the paragraph's mark; with the track scrolled so the earlier formula card and the paragraph's card lie inside its box and the later formula card's top sits at the box's bottom edge, a real click on the body's text marks the two inside seen, takes the dots off their cards and off the paragraph's mark (the control), and the box KEEPS data-new while the other comment covering it stands unseen; the track scrolled on so the later card lies inside, a second click takes the dot off that card and off the box (before: the box's dot came off at the first click, saying nothing on the formula was unread while one comment on it was)", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const page = await browser.newPage({ viewport: { width: 900, height: 700 } });
    const errors: string[] = [];
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    const html = pageHtml("pane", { [REPORT]: NOTE }, MT);
    await page.route((u: URL) => u.href.startsWith(ORIGIN), (route: any) => route.fulfill({ status: 200, contentType: "text/html", body: html }));
    await page.goto(ORIGIN + "/");
    await page.addStyleTag({ content: KATEX_CSS });
    await page.evaluate(([p, sid, st]: [string, string, unknown]) => { (window as any).__status = st; (window as any).FV.openFileView(p, sid, null); }, [REPORT, SID, withComments([FINAL], 1)]);
    await page.waitForFunction(() => !document.querySelector(".fileview-md .md-math-inline, .fileview-md .md-math-display") && !!document.querySelector(".fileview-md > .katex-display"), null, { timeout: 15000 });
    await frames(page, 2);
    await openPanel(page);
    await markPainted(page, id(FINAL));
    const ids = [id(CONTROL), id(A), id(B)];
    await deliver(page, withComments([FINAL, CONTROL, A, B], 2), ids);
    // the render after the pass marks the arrivals' elements (markNew) and the layout's frame places the cards: wait for both
    await page.waitForFunction((c: string) => { const d = document.querySelector(".fileview-md > .katex-display"); return !!d && d.getAttribute("data-ids") === c && d.hasAttribute("data-new"); }, id(A) + " " + id(B), { timeout: 10000 });
    await page.waitForFunction((cs: string[]) => cs.every((c) => { const k = document.querySelector('.fileview-aside .fc-sec-cards .fc-card[data-id="' + c + '"]') as HTMLElement | null; return !!k && !!k.style.top; }), ids, { timeout: 10000 });
    let dots: Dots = await page.evaluate(readDots, { ids, control: id(CONTROL) });
    assert.deepEqual([dots.box, dots.ids, dots.controlMark], ["1", id(A) + " " + id(B), "1"], "the box wears data-new over the covering set of both arrivals; the control's mark wears it too");
    assert.deepEqual(dots.cards, { [id(CONTROL)]: "1", [id(A)]: "1", [id(B)]: "1" }, "every arrival's card wears the dot");
    // the scene: the margin layout, the later formula card placed under the earlier's, the control's above it
    let geo: Geo = await page.evaluate(readGeo, ids);
    assert.equal(geo.margin, true, "the aside is the margin layout at 900 px");
    const [tc, ta, tb] = ids.map((c) => geo.tops[c]);
    assert.ok(tc !== null && ta !== null && tb !== null, "every card placed: " + JSON.stringify(geo.tops));
    assert.ok(tc! < ta! && ta! < tb!, "the control's card above the earlier formula card, the later one under it: " + JSON.stringify(geo.tops));
    assert.ok(tb! - tc! < geo.track.clientHeight, "the three cards fit one track box, so one scroll can show two and hide the third: " + JSON.stringify(geo));
    // the track scrolled so B's top sits at or just past the box's bottom edge: A and the control inside, B outside (entryShown's
    // strict `<`); a placed top is fractional and Chromium's scrollTop whole, so the position is floored, never rounded up past it
    const edge = Math.floor(tb! - geo.track.clientHeight);
    assert.ok(edge >= 0 && edge <= geo.track.scrollHeight - geo.track.clientHeight, "the edge position is reachable: " + edge + " of " + JSON.stringify(geo.track));
    await scrollTrack(page, edge);
    geo = await page.evaluate(readGeo, ids);
    assert.ok(Math.abs(geo.track.scrollTop - edge) < 1, "the track stands at the edge position: " + geo.track.scrollTop + " for " + edge);
    assert.deepEqual(geo.shown, { [id(CONTROL)]: true, [id(A)]: true, [id(B)]: false }, "the scene: the control and the earlier formula card on screen, the later formula card not: " + JSON.stringify(geo));
    dots = await page.evaluate(readDots, { ids, control: id(CONTROL) });
    assert.deepEqual([dots.box, dots.cards[id(A)], dots.cards[id(B)]], ["1", "1", "1"], "a scroll is no gesture: every dot stands");
    // 1. the gesture with the later formula card off screen
    await clickBodyText(page);
    dots = await page.evaluate(readDots, { ids, control: id(CONTROL) });
    assert.deepEqual([dots.cards[id(CONTROL)], dots.cards[id(A)], dots.controlMark], [null, null, null], "the click marked the two cards on screen seen: their dots off, and the control mark's with its card's");
    assert.equal(dots.cards[id(B)], "1", "the later formula card, off screen, stands unseen");
    assert.equal(dots.box, "1", "the box keeps its dot while the later comment covering it stands unseen (before: off at this click)");
    assert.equal(dots.ids, id(A) + " " + id(B), "the covering set untouched");
    // 2. the later card scrolled on screen, and the next gesture
    await scrollTrack(page, edge + 40);
    geo = await page.evaluate(readGeo, ids);
    assert.equal(geo.shown[id(B)], true, "the later formula card on screen now: " + JSON.stringify(geo));
    dots = await page.evaluate(readDots, { ids, control: id(CONTROL) });
    assert.deepEqual([dots.box, dots.cards[id(B)]], ["1", "1"], "the scroll itself marked nothing");
    await clickBodyText(page);
    dots = await page.evaluate(readDots, { ids, control: id(CONTROL) });
    assert.deepEqual([dots.cards[id(B)], dots.box], [null, null], "the later card seen: its dot off, and the box's off with the last unseen comment's");
    assert.equal(dots.ids, id(A) + " " + id(B), "the box's covering set as the pass left it");
    assert.deepEqual(errors, [], "no page errors");
    await page.close();
  });
});

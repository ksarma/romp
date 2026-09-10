// The Comments panel's cards after the pending target's repaint re-files a change (file-comments.ts repaintPresel; the Slice 4
// review's round 17), in headless Chromium over the REAL viewer and panel (real-viewer-leg.ts: the Files pane under styles.css and
// files-pane.css, the kernel's status answered from the page, the poll answered quietly). The repaint is a paint pass over the line
// boxes the target enters and leaves (round 15): the change marks standing there are painted again, whole-document, and trimmed with
// the rest, and the repaint files them as the pass does (paintAll): a change whose every mark the trim removed as not shown, one
// whose mark stands again as shown. The cards read the filing at render time (renderChangeCard: the "not shown" tag, Reveal and the
// reference's link), and the callers of the repaint after a passage's Comment and after Cancel render the composer alone
// (renderFrom), so a card whose filing the repaint moved kept saying the opposite of the body until the next render (a status, a
// toggle). Now the repaint renders the cards when a filing moved, in the same call, and nothing when none did.
// The shape that moves a filing: a session's insertion of ONE SOFT HYPHEN (U+00AD), a character the index records (not \s) and the
// trim measures (anchor-map.ts TRIM_CANDIDATE: no letter, digit, punctuation or symbol), which renders a hyphen at a line break and
// nothing elsewhere, so whether its mark stands after the trim is where the wrap point falls, and the target's 2 px side padding on
// every one of its marks moves the wrap point. A plain space cannot reach the shape: the index skips whitespace, so it is never
// painted. The legs make the wrap point the design's, not the face's: the paragraph is set in the generic monospace face at a
// measure of 60ch (a style added to the page, nothing else touched), so every character is one ch wide and the arithmetic below
// holds for any monospace face at any size. Ten two-character links (29ch) are the target, nineteen marks when painted, 76 px of
// padding (the flips need more than 3ch of it and less than 17ch: 25 to 143 px at the 8.4 px advance of a 14 px face). A second
// insertion in the paragraph always stands, so the repaint finds a change mark in the target's box and paints the changes again on
// the open and on Cancel alike.
//  leg 1, shown to not shown: the word is 26 a's, the soft hyphen, 20 b's. Without the target "links, space, a's, hyphen" is 57ch
//    and fits the measure while the whole word does not (76ch from the line's start), so the line breaks at the soft hyphen and the
//    hyphen renders: the mark stands, the card links. Under the target's padding (66ch) the a's no longer fit, the line breaks at
//    the space before the word, and the whole word (46ch) stands unbroken on the next line: no hyphen, the mark is padding around
//    nothing, the trim removes it, the change is filed as not shown.
//  leg 2, not shown to shown: 12 a's, the soft hyphen, 15 b's. Without the target the whole word fits the first line (57ch): no
//    break, no hyphen, not shown. Under the padding (66ch) it does not, while "links, space, a's, hyphen" (52ch) does: the line
//    breaks at the soft hyphen, the hyphen renders, the change is shown.
// Each leg reads the card against the body before the click, while the composer stands (and after a paint pass under the same
// target: the pass's own filing, which the repaint's must equal), after Cancel and after the next pass. Legs await the DOM's own
// states and frames, never a timer. Skips LOUDLY without a playwright browser (CI installs none). Synthetic values only: an invented
// report, /repo/notes-api paths, the placeholder sid, placeholder ids.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openPanel, pageHtml, frames, REPORT, SID, MT, ORIGIN, STATUS } from "./real-viewer-leg";

const T0 = 1757145600000;
const SHY = "\u00ad";
const LINKS = Array.from({ length: 10 }, (_, i) => "[L" + i + "](#l" + i + ")").join(" ");   // the target: "L0 L1 ... L9", 29ch, 19 text nodes
const TARGET = Array.from({ length: 10 }, (_, i) => "L" + i).join(" ");
/** The paragraph: the links, a space, the word around the soft hyphen, a space, a tail holding the insertion that always stands. */
const noteWith = (word: string): string => "# Report\n\nIntro para. with a few words before.\n\n" + LINKS + " " + word + " cc dd zz ff.\n\nAfter para. closing the report.\n";
const WORD_SHOWN = "a".repeat(26) + SHY + "b".repeat(20);       // leg 1: the hyphen renders before the click
const WORD_HIDDEN = "a".repeat(12) + SHY + "b".repeat(15);      // leg 2: it renders under the target alone
/** A session's insertion of `text` (the hunk indexes the note's text, as the host's do). */
const insertion = (note: string, id: string, text: string) => { const at = note.indexOf(text); return { id, author: "api", ts: T0 + 500, kind: "ins", curFrom: at, curTo: at + text.length, baseFrom: at, baseTo: at, oldText: "", newText: text, anchor: null }; };
/** The scaffold (the header): the paragraph in the generic monospace face at a measure of 60ch; the sheet's other rules stand. */
const SCAFFOLD = ".fileview-md > p:nth-of-type(2) { font-family: monospace; width: 60ch; max-width: none; overflow-wrap: normal; hyphens: manual; }";

/** The panel's poll answered quietly: the two HEADs return the status's own mtimes, so no tick refreshes and repaints. */
const quietPoll = (page: any, status: any): Promise<void> => page.evaluate((st: any) => {
  const w = window as any; const real = w.fetch;
  w.fetch = async function (url: string, init?: RequestInit) {
    if (init && init.method === "HEAD") {
      const m = /[?&]path=([^&]*)/.exec(String(url)); const p = m ? decodeURIComponent(m[1]) : "";
      if (p.endsWith(".json")) return new Response("", { status: 200, headers: { "X-Romp-Mtime-Ns": p.endsWith("/config.json") ? st.configMtimeNs : st.storeMtimeNs } });
    }
    return real(url, init);
  };
}, status);
/** A paint pass with everything as it stands, the composer included (the shared settings signal: Show changes inline off and on). */
const paintPass = (page: any): Promise<void> => page.evaluate(() => {
  const cur = JSON.parse(localStorage.getItem("romp:settings") || "{}");
  for (const v of [false, true]) { localStorage.setItem("romp:settings", JSON.stringify({ ...cur, changesInline: v })); window.dispatchEvent(new Event("romp:settings")); }
});
/** Every card has its place (style.top written): the margin layout's pass ran. */
const placed = (page: any): Promise<unknown> => page.waitForFunction(() => {
  const cards = Array.from(document.querySelectorAll(".fc-sec-cards .fc-card[data-id]"));
  return cards.length > 0 && cards.every((c) => (c as HTMLElement).style.top !== "");
}, null, { timeout: 10000 });

/** A page of the Files pane at `width`, `note` open with `hunks` in the kernel's status, the scaffold on the paragraph, the poll
 *  quiet, the REAL panel opened and its pass painted (the standing insertion's mark awaited); in the margin layout the cards placed. */
async function openWith(browser: any, width: number, note: string, hunks: any[]): Promise<{ page: any; errors: string[] }> {
  const page = await browser.newPage({ viewport: { width, height: 700 } });
  const errors: string[] = [];
  page.on("pageerror", (e: Error) => { errors.push(e.message); });
  const html = pageHtml("pane", { [REPORT]: note }, MT);
  await page.route((u: URL) => u.href.startsWith(ORIGIN), (route: any) => route.fulfill({ status: 200, contentType: "text/html", body: html }));
  await page.goto(ORIGIN + "/");
  const status = { ...STATUS, hunks, store: { ...STATUS.store, suggestions: hunks.map((h) => ({ id: h.id, authorId: SID })) } };
  await quietPoll(page, status);
  await page.evaluate(([p, sid, st]: [string, string, unknown]) => { (window as any).__status = st; (window as any).FV.openFileView(p, sid, null); }, [REPORT, SID, status]);
  await page.waitForFunction(() => !!document.querySelector(".fileview-md > p:nth-of-type(2)"), null, { timeout: 10000 });
  await page.addStyleTag({ content: SCAFFOLD });
  await frames(page, 2);
  await openPanel(page);
  await page.waitForFunction(() => document.querySelectorAll('.fileview-body [data-act="fcchange"][data-id="zz2"]').length > 0, null, { timeout: 10000 });
  const column: boolean = await page.evaluate(() => getComputedStyle((document.querySelector(".fileview-body") as HTMLElement).parentElement!).flexDirection === "column");
  if (!column) await placed(page);
  await frames(page, 3);
  return { page, errors };
}
/** The links selected as a person selects them: a Range from the first link's text node to the end of the last one's, the document's
 *  selection set to it, a mouseup on the paragraph, which the seam's onSelect hears and the panel answers with its float. */
const selectLinks = (page: any): Promise<string> => page.evaluate(() => {
  const el = document.querySelector(".fileview-md > p:nth-of-type(2)") as HTMLElement;
  const nodes: Text[] = []; const walk = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
  for (let t = walk.nextNode(); t; t = walk.nextNode()) nodes.push(t as Text);
  const a = nodes.find((t) => t.data === "L0")!, b = nodes.find((t) => t.data === "L9")!;
  const range = document.createRange(); range.setStart(a, 0); range.setEnd(b, b.data.length);
  const sel = window.getSelection()!; sel.removeAllRanges(); sel.addRange(range);
  el.dispatchEvent(new MouseEvent("mouseup", { bubbles: true, cancelable: true, clientX: 50, clientY: 50 }));
  return sel.toString();
});
/** The float's Comment clicked: the composer opens and the pending target is painted. */
async function openComposer(page: any): Promise<void> {
  await page.waitForFunction(() => { const f = document.querySelector(".fc-float") as HTMLElement | null; return !!f && !f.hidden; }, null, { timeout: 5000 });
  await page.click(".fc-float");
  await page.waitForFunction(() => document.querySelectorAll(".fileview-body mark.fc-presel").length > 0, null, { timeout: 5000 });
  await frames(page, 2);
}
/** Cancel: the target unpainted. */
async function cancel(page: any): Promise<void> {
  await page.click('.fileview-aside [data-act="fccancel"]');
  await page.waitForFunction(() => document.querySelectorAll(".fileview-body mark.fc-presel").length === 0, null, { timeout: 5000 });
  await frames(page, 2);
}

type Read = { marks: number; link: boolean; notShown: boolean; reveal: boolean; presel: number; hyphen: number; measure: number; scaffold: boolean };
/** The soft hyphen's change against its card: the marks the body holds for it, the card's reference as a link, its "not shown" tag and
 *  its Reveal; the target's marks; the rendered width of the soft hyphen itself (a Range over the one character, wherever the trim
 *  left its text node); the paragraph's measure in ch and whether the scaffold took (the preconditions). */
const read = (page: any): Promise<Read> => page.evaluate(() => {
  const body = document.querySelector(".fileview-body") as HTMLElement;
  const p = document.querySelector(".fileview-md > p:nth-of-type(2)") as HTMLElement;
  const card = document.querySelector('.fileview-aside .fc-card.fc-change[data-change="sp1"]');
  const ref = card ? card.querySelector(".fc-ref") : null;
  let hyphen = 0;
  const walk = document.createTreeWalker(p, NodeFilter.SHOW_TEXT);
  for (let t = walk.nextNode(); t; t = walk.nextNode()) {
    const i = (t as Text).data.indexOf("\u00ad"); if (i < 0) continue;
    const r = document.createRange(); r.setStart(t, i); r.setEnd(t, i + 1);
    for (const b of Array.from(r.getClientRects())) hyphen += b.width;
  }
  const probe = document.createElement("span"); probe.textContent = "0"; probe.style.cssText = "position:absolute;visibility:hidden;white-space:pre"; p.appendChild(probe);
  const ch = probe.getBoundingClientRect().width; probe.remove();
  return {
    marks: body.querySelectorAll('[data-act="fcchange"][data-id="sp1"]').length,
    link: !!ref && ref.classList.contains("fc-link"),
    notShown: !!card && Array.from(card.querySelectorAll(".fc-tag")).some((x) => x.textContent === "not shown"),
    reveal: !!card && !!card.querySelector('[data-act="fcreveal"]'),
    presel: body.querySelectorAll("mark.fc-presel").length,
    hyphen: Math.round(hyphen * 100) / 100,
    measure: Math.round(p.getBoundingClientRect().width / ch * 10) / 10,
    scaffold: getComputedStyle(p).fontFamily === "monospace",
  };
});
/** Whether the card says what the body shows: a link exactly when a mark stands, the tag and Reveal exactly when none does. */
const consistent = (r: Read): boolean => r.link === (r.marks > 0) && r.notShown === (r.marks === 0) && r.reveal === (r.marks === 0);
/** The card and the body's filing alone, for the comparisons across a paint pass. */
const filing = (r: Read) => ({ marks: r.marks, link: r.link, notShown: r.notShown, reveal: r.reveal });

test("md-config: a change whose filing the pending target's repaint moves (one soft hyphen inserted, rendered at a line break alone) has its card re-rendered in the same call: the tag, Reveal and the link follow the body on the composer's open and on Cancel, in both directions, and a pass under the same target files it the same", { timeout: 300000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const legs: Array<[string, string, boolean]> = [["leg 1, shown to not shown", WORD_SHOWN, true], ["leg 2, not shown to shown", WORD_HIDDEN, false]];
    for (const [name, word, shownFirst] of legs) {
      const at = name + ": ";
      const note = noteWith(word);
      const { page, errors } = await openWith(browser, 900, note, [insertion(note, "sp1", SHY), insertion(note, "zz2", "zz")]);
      const r0 = await read(page);
      assert.ok(r0.scaffold && r0.measure === 60, at + "the scaffold took: the paragraph in the monospace face at 60ch: " + JSON.stringify(r0));
      assert.equal(r0.marks > 0, shownFirst, at + "the pass's filing before the click is the design's (the hyphen " + (shownFirst ? "renders at the break" : "does not render") + "): " + JSON.stringify(r0));
      assert.equal(r0.hyphen > 0, shownFirst, at + "and the soft hyphen's own rendered width says why: " + JSON.stringify(r0));
      assert.ok(consistent(r0), at + "the card says what the pass painted: " + JSON.stringify(r0));
      // the composer opened on the links: the target's padding moves the wrap point across the soft hyphen
      assert.equal(await selectLinks(page), TARGET, at + "the ten links selected");
      await openComposer(page);
      const r1 = await read(page);
      assert.ok(r1.presel >= 10, at + "the target is painted, one mark per text node: " + r1.presel);
      assert.equal(r1.marks > 0, !shownFirst, at + "under the target the body's filing moved (the design): " + JSON.stringify(r1));
      assert.equal(r1.hyphen > 0, !shownFirst, at + "and the soft hyphen's rendered width moved with it: " + JSON.stringify(r1));
      assert.ok(consistent(r1), at + "while the composer stands the card says what the body shows (the round 17 finding: the repaint re-filed the change and rendered no card, so the card kept the pass's " + (shownFirst ? "link with no tag while the body held no mark" : "tag and Reveal while the body showed the tinted hyphen") + "): " + JSON.stringify(r1));
      await paintPass(page); await frames(page, 2);
      const r1b = await read(page);
      assert.deepEqual(filing(r1b), filing(r1), at + "a paint pass under the same target files the change as the repaint did, and its card is the repaint's: " + JSON.stringify(r1b) + " against " + JSON.stringify(r1));
      // Cancel: the wrap point goes back, and so does the filing; the card follows in the same call
      await cancel(page);
      const r2 = await read(page);
      assert.equal(r2.marks > 0, shownFirst, at + "after Cancel the body's filing is the pass's before the click: " + JSON.stringify(r2));
      assert.ok(consistent(r2), at + "and the card says so (the other direction of the finding: the card kept the standing target's filing): " + JSON.stringify(r2));
      await paintPass(page); await frames(page, 2);
      const r3 = await read(page);
      assert.deepEqual(filing(r3), filing(r2), at + "and the next pass changes nothing: " + JSON.stringify(r3));
      assert.deepEqual(errors, [], at + "no script error");
      await page.close();
    }
  });
});

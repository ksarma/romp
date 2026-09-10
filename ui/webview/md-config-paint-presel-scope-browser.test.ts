// The scope and the order of the Comments panel's repaint when the pending target alone is painted or unpainted (file-comments.ts
// repaintPresel and lineBoxOf; the Slice 4 review's round 16), in headless Chromium over the REAL viewer and panel (real-viewer-leg.ts:
// the Files pane under styles.css and files-pane.css, the kernel's status answered from the page, the poll answered quietly). Round 15
// made that repaint a paint pass over the line boxes the target enters and leaves: the highlights standing there are unwrapped and
// painted again with the target inside them, then the one trim. Round 16 found three ways its result differed from paintAll's, each a
// card move on no new information (a composer's open and close say nothing about the comments), and one shape it never repainted:
// 1. The highlights were painted again in the document order of their first marks, where the pass paints them in cards() order (the
//    model's order by time, so the later comment nests inside the earlier where two overlap). Two overlapping comments whose order by
//    time is not their order in the text swapped nesting at every open and close and swapped back at the next pass; the delegate opens
//    the innermost mark's card on a click over the overlap (actions.ts delegate, closest("[data-act]")), so the click opened the other
//    card meanwhile. Now the set is painted in cards() order: the nesting, the click target and the ring of marks around the overlap
//    are the pass's before the composer opens, while it stands, after Cancel and after the next pass, at 300 and 800 px.
// 2. A highlight found in a touched box was unwrapped whole and painted again over its full range, so in a box the target never
//    touched its text now sat inside the marks standing there, and it was painted inside them: the nesting inverted with no mark of
//    the target near. Now the boxes are closed under the repainted highlights (every box a repainted highlight's own marks stand in is
//    read too, until no highlight is new): a comment across two paragraphs, overlapped in the first by a later comment, keeps the
//    pass's nesting when the target is selected in the second.
// 3. The change marks were painted again only when one stood in a TOUCHED box, so a highlight repainted around a change mark in an
//    untouched box landed inside it (a click on the inserted word opened the comment, not the change) and around a deletion point
//    split on either side of it. The closed boxes decide now: an insertion inside the highlight stays inside it, a deletion point too.
// 4. lineBoxOf stopped at an inline-block: the embed chip (`a.fv-embed`, the constructs note's `![[Note]]`) is one, and its width is
//    its text's, so a target selected on the chip's text alone grew the chip by the target's padding and moved the wrap points of the
//    paragraph around it while no highlight of the paragraph was repainted; its blanks trimmed at the pending wrap points stood bare
//    after Cancel, round 14's symptom in a new shape. Now the box is the block whose width does not follow its content: the paragraph's
//    highlight is painted again (every mark of it fresh) and after Cancel its blank marks and the paragraph's bare blanks are the
//    pass's before the click; while the composer stands they are a pass's under the same target.
// The pass the comparisons read is paintAll through the shared settings signal (settings.ts onExternalSettingsChange: Show changes
// inline flipped off and on; the notes here carry a change only in leg 3, whose marks that pass paints again like the panel's own).
// Legs await the DOM's own states and frames, never a timer. Skips LOUDLY without a playwright browser (CI installs none). Synthetic
// values only: an invented report, /repo/notes-api paths, the placeholder sid, placeholder comment ids.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openPanel, pageHtml, frames, REPORT, SID, MT, ORIGIN, STATUS } from "./real-viewer-leg";

const T0 = 1757145600000;
const L = (i: number) => "[Link" + i + " docs](#l" + i + ")";
const links = (a: number, b: number) => Array.from({ length: b - a + 1 }, (_, i) => L(a + i)).join(" ");
/** A comment anchored on a passage (the shape the kernel's status carries); every quote recurs nowhere in its note. */
const commentOn = (id: string, ts: number, quote: string, prefix: string, suffix: string) => ({ id, author: "you", ts, body: `Note ${id}.`, anchor: { quote, prefix, suffix }, replies: [], resolved: false });

// leg 1: the list item of fourteen links; A the EARLIER comment (by time) on Link4 to Link9, B the LATER one on Link1 to Link6, so
// B's passage starts before A's and the two overlap on Link4 to Link6
const NOTE_ITEM = "# Report\n\nIntro para. with a few words before the list.\n\n- " + links(0, 13) + "\n\nBetween para. with a few more words.\n\nAfter para. closing the report.\n";
const A1 = commentOn("aaaa-1", T0 + 1, links(4, 9), L(3) + " ", " " + L(10));
const B1 = commentOn("bbbb-2", T0 + 2, links(1, 6), L(0) + " ", " " + L(7));

// legs 2 and 3: two paragraphs; A (earlier) from P1's "five" across the break into P2's "gamma", B (later) on P1's "three four five
// six", overlapping A on "five six"; the target is "theta iota" in P2, a box no mark of B and no change mark stands in
const P1 = "First para one two three four five six seven eight nine ten.";
const P2 = "Second para alpha beta gamma delta epsilon zeta eta theta iota kappa.";
const NOTE_PARAS = "# Report\n\nIntro para. with a few words before.\n\n" + P1 + "\n\n" + P2 + "\n\nAfter para. closing the report.\n";
const A2 = commentOn("aaaa-1", T0 + 1, "five six seven eight nine ten.\n\nSecond para alpha beta gamma", "four ", " delta");
const B2 = commentOn("bbbb-2", T0 + 2, "three four five six", "two ", " seven");
/** A session's insertion of `word` (the hunk indexes the note's text, as the host's do). */
const insertion = (id: string, word: string) => { const at = NOTE_PARAS.indexOf(word); return { id, author: "api", ts: T0 + 500, kind: "ins", curFrom: at, curTo: at + word.length, baseFrom: at, baseTo: at, oldText: "", newText: word, anchor: null }; };
/** A session's deletion, its point right after `word`. */
const deletionAfter = (id: string, word: string) => { const at = NOTE_PARAS.indexOf(word) + word.length; return { id, author: "api", ts: T0 + 500, kind: "del", curFrom: at, curTo: at, baseFrom: 0, baseTo: 0, oldText: "X", newText: "", anchor: null }; };

// leg 4: a paragraph opening with the embed chip, then forty links under one comment, which wraps at every width the leg opens
const LINKS40 = Array.from({ length: 40 }, (_, i) => "[w" + i + " docs](#a" + i + ")").join(" ");
const NOTE_CHIP = "# Report\n\nIntro para. with a few words before.\n\nSee the embed ![[Note]] " + LINKS40 + " and the end.\n\nAfter para. closing the report.\n";
const C4 = commentOn("bbbb-2", T0 + 2, LINKS40, "![[Note]] ", " and the end.");

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
/** A paint pass with everything as it stands, the composer included (the header). */
const paintPass = (page: any): Promise<void> => page.evaluate(() => {
  const cur = JSON.parse(localStorage.getItem("romp:settings") || "{}");
  for (const v of [false, true]) { localStorage.setItem("romp:settings", JSON.stringify({ ...cur, changesInline: v })); window.dispatchEvent(new Event("romp:settings")); }
});
/** Every card has its place (style.top written): the margin layout's pass ran. */
const placed = (page: any): Promise<unknown> => page.waitForFunction(() => {
  const cards = Array.from(document.querySelectorAll(".fc-sec-cards .fc-card[data-id]"));
  return cards.length > 0 && cards.every((c) => (c as HTMLElement).style.top !== "");
}, null, { timeout: 10000 });

/** A page of the Files pane at `width`, `note` open with `comments` (and `hunks`) in the kernel's status, the poll quiet, the REAL
 *  panel opened and its pass painted; in the margin layout the cards placed. */
async function openWith(browser: any, width: number, note: string, comments: any[], hunks: any[] = []): Promise<{ page: any; errors: string[] }> {
  const page = await browser.newPage({ viewport: { width, height: 700 } });
  const errors: string[] = [];
  page.on("pageerror", (e: Error) => { errors.push(e.message); });
  const html = pageHtml("pane", { [REPORT]: note }, MT);
  await page.route((u: URL) => u.href.startsWith(ORIGIN), (route: any) => route.fulfill({ status: 200, contentType: "text/html", body: html }));
  await page.goto(ORIGIN + "/");
  const status = { ...STATUS, hunks, store: { ...STATUS.store, comments }, unsent: { ...STATUS.unsent, comments: comments.map((c) => c.id) } };
  await quietPoll(page, status);
  await page.evaluate(([p, sid, st]: [string, string, unknown]) => { (window as any).__status = st; (window as any).FV.openFileView(p, sid, null); }, [REPORT, SID, status]);
  await page.waitForFunction(() => !!document.querySelector(".fileview-md > p"), null, { timeout: 10000 });
  await openPanel(page);
  await page.waitForFunction(() => document.querySelectorAll(".fileview-body mark.fc-hl").length > 0, null, { timeout: 10000 });
  const column: boolean = await page.evaluate(() => getComputedStyle((document.querySelector(".fileview-body") as HTMLElement).parentElement!).flexDirection === "column");
  if (!column) await placed(page);
  await frames(page, 3);
  return { page, errors };
}
/** A passage selected as a person selects it: a Range from `at` characters into the text node under `scope` that starts with `from`
 *  to the end of the one that starts with `to` (or `at + length` into the same node with `length`), the document's selection set to
 *  it, a mouseup on the scope, which the seam's onSelect hears and the panel answers with its float. */
const select = (page: any, scope: string, from: string, to: string, at = 0, length = 0): Promise<string> => page.evaluate(([scope, from, to, at, length]: [string, string, string, number, number]) => {
  const el = document.querySelector(scope) as HTMLElement;
  const nodes: Text[] = []; const walk = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
  for (let t = walk.nextNode(); t; t = walk.nextNode()) nodes.push(t as Text);
  const a = nodes.find((t) => t.data.indexOf(from) >= 0)!;
  const range = document.createRange();
  if (length) { const i = a.data.indexOf(from) + at; range.setStart(a, i); range.setEnd(a, i + length); }
  else { const b = nodes.find((t) => t.data.startsWith(to))!; range.setStart(a, 0); range.setEnd(b, b.data.length); }
  const sel = window.getSelection()!; sel.removeAllRanges(); sel.addRange(range);
  el.dispatchEvent(new MouseEvent("mouseup", { bubbles: true, cancelable: true, clientX: 50, clientY: 50 }));
  return sel.toString();
}, [scope, from, to, at, length]);
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

type Nest = { BinA: number; AinB: number; hlA: number; hlB: number; presel: number; target: string; ring: string[] };
/** The two comments' nesting (B's marks inside A's and the inverse), their mark counts, and at the text node starting with `word`: the
 *  control a click resolves to (the delegate's closest("[data-act]"), act:id) and the ring of marks around it, innermost first, up to
 *  the block (the pending target's mark by its class, a highlight by its id). */
const readNest = (page: any, word: string): Promise<Nest> => page.evaluate((w: string) => {
  const body = document.querySelector(".fileview-body")!; const q = (s: string) => body.querySelectorAll(s).length;
  let target = "(none)"; const ring: string[] = [];
  const walk = document.createTreeWalker(document.querySelector(".fileview-md")!, NodeFilter.SHOW_TEXT);
  for (let t = walk.nextNode(); t; t = walk.nextNode()) if ((t as Text).data.startsWith(w)) {
    const c = (t.parentElement as HTMLElement).closest("[data-act]") as HTMLElement | null; target = c ? c.dataset.act + ":" + c.dataset.id : "(none)";
    for (let e = t.parentElement; e && e.tagName !== "LI" && e.tagName !== "P"; e = e.parentElement) if (e.tagName === "MARK") ring.push((e as HTMLElement).dataset.id || e.className);
    break;
  }
  return { BinA: q('mark.fc-hl[data-id="aaaa-1"] mark.fc-hl[data-id="bbbb-2"]'), AinB: q('mark.fc-hl[data-id="bbbb-2"] mark.fc-hl[data-id="aaaa-1"]'), hlA: q('mark.fc-hl[data-id="aaaa-1"]'), hlB: q('mark.fc-hl[data-id="bbbb-2"]'), presel: q("mark.fc-presel"), target, ring };
}, word);
/** The pass's shape of `r`, the target's own mark left out of the ring (a pass under the standing target puts it innermost). */
const shape = (r: Nest) => ({ BinA: r.BinA, AinB: r.AinB, hlA: r.hlA, hlB: r.hlB, target: r.target, ring: r.ring.filter((k) => k !== "fc-presel") });
/** The order alone: which comment nests inside which, the click target and the ring; the counts are the trim's, and the trim's result
 *  under the standing target differs from the one without it where the target's padding moves a wrap point onto a blank mark (leg 1
 *  compares the counts with a pass's under the same target, and after Cancel with the pass's before the click). */
const order = (r: Nest) => ({ BinA: r.BinA > 0, AinB: r.AinB, target: r.target, ring: r.ring.filter((k) => k !== "fc-presel") });
const counts = (r: Nest) => ({ BinA: r.BinA, AinB: r.AinB, hlA: r.hlA, hlB: r.hlB });

test("md-config: two overlapping comments whose order by time is not their order in the text keep the pass's nesting, click target and ring while the composer stands, after Cancel and after the next pass (the repaint paints the highlights in cards() order)", { timeout: 300000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const width of [300, 800]) for (const [from, to] of [["Link11 docs", "Link12 docs"], ["Link4 docs", "Link6 docs"]]) {
      const at = "@" + width + "px, " + from + " to " + to + ": ";
      const { page, errors } = await openWith(browser, width, NOTE_ITEM, [A1, B1]);
      const r0 = await readNest(page, "Link5 docs");
      assert.ok(r0.BinA >= 3 && r0.AinB === 0, at + "the pass nests the later comment (B) inside the earlier (A) over the overlap: " + JSON.stringify(r0));
      assert.equal(r0.target, "fcopen:bbbb-2", at + "a click on the overlap opens the later comment, the innermost mark's");
      assert.deepEqual(r0.ring, ["bbbb-2", "aaaa-1"], at + "the ring around the overlap, innermost first");
      // the composer opened on the target (outside both comments, or inside the overlap): the same shape
      const selected = await select(page, ".fileview-md > ul > li", from, to);
      assert.ok(selected.startsWith(from) && selected.endsWith(to), at + "the selection spans the links: " + JSON.stringify(selected));
      await openComposer(page);
      const r1 = await readNest(page, "Link5 docs");
      assert.ok(r1.presel > 0, at + "the target is painted");
      assert.deepEqual(order(r1), order(r0), at + "while the composer stands B nests inside A, the click target and the ring are the pass's (round 15 painted the highlights in the order of their first marks, so B's whole range went first and A landed inside it: the click on Link5 opened A)");
      await paintPass(page); await frames(page, 2);
      const r1b = await readNest(page, "Link5 docs");
      assert.deepEqual(shape(r1b), shape(r1), at + "a paint pass under the same target leaves the same shape and the same counts: " + JSON.stringify(counts(r1b)) + " against the repaint's " + JSON.stringify(counts(r1)));
      assert.equal(r1b.presel, r1.presel, at + "and the same target marks");
      // Cancel and the next pass: the shape before the click
      await cancel(page);
      const r2 = await readNest(page, "Link5 docs");
      assert.deepEqual(shape(r2), shape(r0), at + "after Cancel the nesting, the click target, the ring and the counts are the pass's before the click (round 15 left the nesting inverted until the next pass)");
      await paintPass(page); await frames(page, 2);
      const r3 = await readNest(page, "Link5 docs");
      assert.deepEqual(shape(r3), shape(r0), at + "and the next pass changes nothing");
      assert.deepEqual(errors, [], at + "no script error");
      await page.close();
    }
  });
});

test("md-config: a comment across two paragraphs, overlapped in the first by a later comment, keeps the pass's nesting and mark count when the target is selected in the second (the boxes closed under the repainted highlights)", { timeout: 300000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const width of [300, 800]) {
      const at = "@" + width + "px: ";
      const { page, errors } = await openWith(browser, width, NOTE_PARAS, [A2, B2]);
      const r0 = await readNest(page, "five");
      assert.deepEqual([r0.BinA, r0.AinB, r0.hlA, r0.target, r0.ring], [1, 0, 2, "fcopen:bbbb-2", ["bbbb-2", "aaaa-1"]], at + "the pass: B inside A over 'five six', A in two marks (one per paragraph), the click on 'five' opening B: " + JSON.stringify(r0));
      const selected = await select(page, ".fileview-md > p:nth-of-type(3)", "theta iota", "", 0, "theta iota".length);
      assert.equal(selected, "theta iota", at + "the target selected in the second paragraph");
      await openComposer(page);
      const r1 = await readNest(page, "five");
      assert.equal(r1.presel, 1, at + "the target is one mark in the second paragraph");
      assert.deepEqual(shape(r1), shape(r0), at + "while the composer stands the first paragraph's nesting is the pass's (round 15 repainted A whole, so in the first paragraph, a box the target never touched, A landed inside B's standing marks: A in three marks, the click on 'five' opening A)");
      await cancel(page);
      const r2 = await readNest(page, "five");
      assert.deepEqual(shape(r2), shape(r0), at + "after Cancel too");
      await paintPass(page); await frames(page, 2);
      assert.deepEqual(shape(await readNest(page, "five")), shape(r0), at + "and the next pass changes nothing");
      assert.deepEqual(errors, [], at + "no script error");
      await page.close();
    }
  });
});

type Changes = { insInHl: number; hlInIns: number; delInHl: number; hlA: number; ins: number; del: number; presel: number; target: string };
/** The change marks against the highlight: an insertion inside it (the pass's shape) or the highlight inside the insertion, a deletion
 *  point directly inside a highlight mark; the counts; the control a click on the first text node holding `word` resolves to (the
 *  inserted word is a text node of its own inside the insertion's mark; a word beside a deletion point shares its node with the words
 *  before it). */
const readChanges = (page: any, word: string): Promise<Changes> => page.evaluate((w: string) => {
  const body = document.querySelector(".fileview-body")!; const q = (s: string) => body.querySelectorAll(s).length;
  let target = "(none)";
  const walk = document.createTreeWalker(document.querySelector(".fileview-md")!, NodeFilter.SHOW_TEXT);
  for (let t = walk.nextNode(); t; t = walk.nextNode()) if ((t as Text).data.indexOf(w) >= 0) { const c = (t.parentElement as HTMLElement).closest("[data-act]") as HTMLElement | null; target = c ? c.dataset.act + ":" + c.dataset.id : "(none)"; break; }
  return { insInHl: q("mark.fc-hl mark.fc-ins"), hlInIns: q("mark.fc-ins mark.fc-hl"), delInHl: q("mark.fc-hl > span.fc-del"), hlA: q('mark.fc-hl[data-id="aaaa-1"]'), ins: q("mark.fc-ins"), del: q("span.fc-del"), presel: q("mark.fc-presel"), target };
}, word);
const changeShape = (r: Changes) => ({ insInHl: r.insInHl, hlInIns: r.hlInIns, delInHl: r.delInHl, hlA: r.hlA, ins: r.ins, del: r.del, target: r.target });

test("md-config: a change mark in a block the target never touched keeps the pass's nesting with the highlight painted again around it: an insertion inside the highlight opens the change on a click, a deletion point stays inside one highlight mark", { timeout: 300000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const scenes: Array<[string, any, string, Partial<Changes>]> = [
      ["an insertion of 'seven ' inside the highlight in the first paragraph", insertion("s1", "seven "), "seven", { insInHl: 1, hlInIns: 0, hlA: 2, ins: 1, target: "fcchange:s1" }],
      ["a deletion point after 'seven' inside the highlight in the first paragraph", deletionAfter("s3", "seven"), "seven", { delInHl: 1, hlA: 2, del: 1, target: "fcopen:aaaa-1" }],
    ];
    for (const width of [300, 800]) for (const [name, hunk, word, expect] of scenes) {
      const at = "@" + width + "px, " + name + ": ";
      const { page, errors } = await openWith(browser, width, NOTE_PARAS, [A2], [hunk]);
      await page.waitForFunction(() => document.querySelectorAll(".fileview-body [data-act=\"fcchange\"]").length > 0, null, { timeout: 10000 });
      const r0 = await readChanges(page, word);
      for (const k of Object.keys(expect) as Array<keyof Changes>) assert.equal(r0[k], expect[k], at + "the pass's shape, " + k + ": " + JSON.stringify(r0));
      const selected = await select(page, ".fileview-md > p:nth-of-type(3)", "theta iota", "", 0, "theta iota".length);
      assert.equal(selected, "theta iota", at + "the target selected in the second paragraph");
      await openComposer(page);
      const r1 = await readChanges(page, word);
      assert.equal(r1.presel, 1, at + "the target is one mark in the second paragraph");
      assert.deepEqual(changeShape(r1), changeShape(r0), at + "while the composer stands the change mark's nesting is the pass's (round 15 repainted the highlight whole and the change marks only when one stood in a touched box, so the highlight landed inside the insertion, the click on 'seven' opening the comment, and the deletion point stood between two highlight marks)");
      await cancel(page);
      const r2 = await readChanges(page, word);
      assert.deepEqual(changeShape(r2), changeShape(r0), at + "after Cancel too");
      await paintPass(page); await frames(page, 2);
      assert.deepEqual(changeShape(await readChanges(page, word)), changeShape(r0), at + "and the next pass changes nothing");
      assert.deepEqual(errors, [], at + "no script error");
      await page.close();
    }
  });
});

type Chip = { paints: number; chipDisplay: string; preselParent: string; hl: { n: number; blank: number; tagged: number; paddingOnly: string[] }; bare: string[] };
/** The chip paragraph: the chip's computed display and the pending target's parent (the shape's preconditions), the comment's marks
 *  (their count, the blank ones, the ones still carrying the tag `tag` set before the click, the padding-only ones: the trim's own
 *  oracle, every text node at zero width and a box of its own), and the paragraph's blank text nodes that render with a width and
 *  carry no mark (bare). */
const readChip = (page: any): Promise<Chip> => page.evaluate(() => {
  const w = window as any; const p = document.querySelector(".fileview-md > p:nth-of-type(2)") as HTMLElement;
  const BLANK = /^(?:[^\p{L}\p{N}\p{P}\p{S}]|[\u115f\u1160\u3164\uffa0])*$/u;
  const width = (n: Node) => { const r = document.createRange(); r.selectNodeContents(n); let x = 0; for (const b of Array.from(r.getClientRects())) x += b.width; return x; };
  const textWidth = (k: Element) => { let x = 0; const walk = document.createTreeWalker(k, NodeFilter.SHOW_TEXT); for (let t = walk.nextNode(); t; t = walk.nextNode()) x += width(t); return x; };
  const marks = Array.from(p.querySelectorAll('mark.fc-hl[data-id="bbbb-2"]'));
  const blanks = marks.filter((k) => BLANK.test(k.textContent || ""));
  const paddingOnly = blanks.filter((k) => textWidth(k) === 0 && k.getClientRects().length > 0).map((k) => JSON.stringify(k.textContent));
  const bare: string[] = [];
  const walk = document.createTreeWalker(p, NodeFilter.SHOW_TEXT);
  for (let t = walk.nextNode(); t; t = walk.nextNode()) if (BLANK.test((t as Text).data) && width(t) > 0 && !(t.parentElement && t.parentElement.closest("mark"))) bare.push(t.parentNode!.nodeName + " " + JSON.stringify((t as Text).data) + " after " + JSON.stringify((t.previousSibling && t.previousSibling.textContent || "").slice(-8)));
  const presel = p.querySelector("mark.fc-presel") as HTMLElement | null;
  const chip = p.querySelector("a.fv-embed") as HTMLElement;
  return { paints: w.__paints, chipDisplay: getComputedStyle(chip).display, preselParent: presel ? presel.parentElement!.tagName + "." + String(presel.parentElement!.className).split(" ")[0] : "", hl: { n: marks.length, blank: blanks.length, tagged: marks.filter((k) => (k as any).__tag === true).length, paddingOnly }, bare };
});
/** Every mark of the comment tagged, so a later read tells the marks the repaint painted (untagged) from the ones it left standing. */
const tag = (page: any): Promise<void> => page.evaluate(() => { for (const m of Array.from(document.querySelectorAll('.fileview-md mark.fc-hl[data-id="bbbb-2"]'))) (m as any).__tag = true; });

test("md-config: a target selected on the embed chip's text alone repaints the highlight of the paragraph around the chip (lineBoxOf climbs past the inline-block), so after Cancel the paragraph's bare blanks and the highlight's blank marks are the pass's before the click, and while the composer stands a pass's under the same target", { timeout: 300000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const width of [385, 500, 605, 725]) {
      const at = "@" + width + "px: ";
      const { page, errors } = await openWith(browser, width, NOTE_CHIP, [C4]);
      const r0 = await readChip(page);
      assert.equal(r0.chipDisplay, "inline-block", at + "the chip is an inline-block (the shape's precondition)");
      assert.ok(r0.hl.blank >= 20, at + "the comment's marks over the spaces between the links stand after the pass: " + r0.hl.blank);
      assert.deepEqual(r0.hl.paddingOnly, [], at + "the pass left no padding-only mark");
      await tag(page);
      const selected = await select(page, ".fileview-md > p:nth-of-type(2) a.fv-embed", "Note", "", 0, 4);
      assert.equal(selected, "Note", at + "the chip's text selected");
      await openComposer(page);
      const r1 = await readChip(page);
      assert.equal(r1.preselParent, "A.fv-embed", at + "the target stands inside the chip");
      assert.equal(r1.paints, r0.paints, at + "no paint pass and no reflow for the click: the repaint's own path");
      assert.equal(r1.hl.tagged, 0, at + "every mark of the paragraph's highlight is the repaint's (round 15 took the chip as the box, found no highlight in it and left the paragraph's " + r1.hl.n + " marks standing while the chip's growth moved its wrap points: " + r1.hl.tagged + " still stand)");
      assert.deepEqual(r1.hl.paddingOnly, [], at + "no padding-only mark while the composer stands");
      await paintPass(page); await frames(page, 2);
      const r1b = await readChip(page);
      assert.equal(r1b.hl.blank, r1.hl.blank, at + "the highlight's blank marks are a pass's under the same target: " + r1b.hl.blank + " against the repaint's " + r1.hl.blank);
      assert.deepEqual(r1b.bare, r1.bare, at + "and the paragraph's bare blanks are the pass's own under it");
      await cancel(page);
      const r2 = await readChip(page);
      assert.equal(r2.paints, r1b.paints, at + "no paint pass and no reflow for the cancel either");
      assert.deepEqual(r2.hl.paddingOnly, [], at + "no padding-only mark after Cancel");
      assert.equal(r2.hl.blank, r0.hl.blank, at + "the highlight's blank marks after Cancel are the pass's before the click: " + r2.hl.blank + " against " + r0.hl.blank + " (round 15 left the ones trimmed at the pending wrap points unwrapped)");
      assert.deepEqual(r2.bare, r0.bare, at + "the paragraph's bare blanks after Cancel are the pass's before the click (round 15 left the trimmed blanks bare where they render again, the ring gapped until the next pass)");
      assert.deepEqual(errors, [], at + "no script error");
      await page.close();
    }
  });
});

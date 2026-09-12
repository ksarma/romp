// The block-level paint on a display formula over the REAL viewer and the REAL Comments panel in headless Chromium
// (plans/markdown-viewer.md Slice 8, item 5; the Slice 8 contract line). A display formula is a block of its own line, which no
// inline mark can wrap (anchor-map.ts isInlineFormula), so a comment on `$$ ... $$` alone painted nothing in Rendered and its
// card offered Reveal (the Slice 4 note's item 10, pinned by anchor-map-obsidian.test.ts until this slice). Now the anchor map's
// paint STAMPS the formula's own `.katex-display` element with the block class (`fc-hl-block`, `fc-presel-block` for the
// composer's pending target) and the paint's data attributes and returns it among the marks; the panel treats it as one of its
// marks and, where a mark is unwrapped, strips it in place (file-comments.ts unwrapMarks); the sheets dress the class on the
// formula's box (styles.css and feed.css, the .fc-hl region, byte-equal). Read through real-viewer-leg.ts (the panel registered by
// the viewer's own module) under the Files pane's sheet and the chat modal's, KaTeX's own sheet added to the page as
// md-config-math-map-browser.test.ts adds it (real-viewer-leg.ts drops the sheet's `@import`). Three legs. The first two are the
// slice's acceptance and need BOTH halves: a comment on the formula served before a fresh open shows the wash (computed
// background not transparent) in Rendered, its card offers Scroll and a click on the formula opens it, a reload paints it the
// same, print media strips it; and the composer's pending target on the formula, made in the Raw view and carried into
// Rendered by the view switch, wears the accent and Cancel leaves no class behind. Until the anchor map's half (unit A's
// formulas-path commit, coded against the same contract line) is on the tree these two legs are red: the box wears no class.
// The third leg reads the panel's half alone, over the box stamped by hand as the paint will stamp it: the sheets' dress on the
// stamped box (the wash and ring, the context cue's dashed outline with the ring dropped, the pending target's accent), no layout
// change (the box the same size stamped and bare), and the pass's unpaint stripping the box in place when the same body is
// repainted (a filter change repaints from the status already here). The click through the delegate is the first leg's alone:
// the body's delegate answers the panel's OWN marks (owns, the elements the pass recorded), so a box stamped by hand is not a
// control until the paint returns it to the pass. Two legs from the Slice 8 review's round 1: two comments on the one formula
// share the box, so the pass keeps the covering set on it (`data-ids`, the later comment's id in front; file-comments.ts
// coverBox), a click opens both cards and each card's Scroll finds the box (before: the later paint's id overwrote the
// earlier's, the click opened one card, the earlier card's Scroll fell to Reveal); and the pending target's unpaint strips its
// own class alone, so Cancel over a highlighted formula leaves the highlight standing (before: it stripped both classes and
// every attribute off the shared box, and the formula went bare and dead until the next full pass). One leg from round 2: a
// display formula inside a blockquote with a quote line after its closer, whose natural Raw quote (the opener through the
// closing `$$`) never covered it, since the formula's hole ran past the next quote line's `> ` marker (anchor-map.ts, the
// mathBlock hole's end); a served comment on it now stamps the quote's box and a Raw drag over its rows carries the pending
// target onto it. Skips LOUDLY without a playwright browser (CI installs none), as the other browser legs do. Synthetic values
// only: an invented note, /repo/notes-api paths, the placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { inBrowser, openPanel, frames, pageHtml, ORIGIN, REPORT, SID, MT, STATUS, EXT, type Mode } from "./real-viewer-leg";
import { makeAnchor } from "./anchor-map";

const KATEX_CSS = fs.readFileSync(path.join(EXT, "node_modules", "katex", "dist", "katex.min.css"), "utf8");
const NOTE = "# Title\n\nPara before the formula.\n\n$$\n\\sum_i i\n$$\n\nPara after the formula.\n\nLast para.\n";
const FORMULA_Q = "$$\n\\sum_i i\n$$";
const T0 = 1757145600000;
const BODY = "Check this formula against the spec.";
const TRANSPARENT = "rgba(0, 0, 0, 0)";
const OPEN_TITLE = "Open the comment on this passage";

/** A comment in the host's shape on the note's passage `quote`: the exact source slice, its context, its position. */
function comment(quote: string, k: number, note = NOTE): Record<string, unknown> {
  const at = note.indexOf(quote);
  assert.ok(at >= 0, "the note holds " + JSON.stringify(quote));
  return { id: (T0 + k) + "-" + at, author: "you", ts: T0 + k, body: BODY, anchor: makeAnchor(note, { start: at, end: at + quote.length }), anchorAt: at, replies: [], resolved: false };
}
const FINAL = comment("Last para.", 1);       // the pass's sentinel: its mark is what the legs wait for (the paint is one pass over every card)
const FORMULA = comment(FORMULA_Q, 2);
const FORMULA_B = comment(FORMULA_Q, 3);      // a second comment on the same formula, later by time: the pass paints it after FORMULA, so it is the one in front
// the round 2 leg's note: the display formula inside a blockquote, a blank `>` line and a quote line after its closer
const NOTE_Q = "# Title\n\nPara before the quote.\n\n> Quote lead.\n>\n> $$\n> \\int_0^1 x\\,dx\n> $$\n>\n> Quote tail.\n\nLast para.\n";
const QUOTED_Q = "$$\n> \\int_0^1 x\\,dx\n> $$";   // the natural Raw quote of the quoted block: the opener through the closing `$$`
const FINAL_Q = comment("Last para.", 1, NOTE_Q);
const QUOTED = comment(QUOTED_Q, 4, NOTE_Q);
const id = (c: Record<string, unknown>): string => c.id as string;
/** The kernel's status with `comments` in the store, `n` bumping the store's mtime so each reply reads as a new write. */
const withComments = (comments: Record<string, unknown>[], n: number): Record<string, unknown> =>
  ({ ...STATUS, store: { ...STATUS.store, comments }, storeMtimeNs: "17571456000000000" + (20 + n), unsent: { comments: [], replies: [], accepted: 0, rejected: 0, watermark: null } });

/** The page: the note open in the view (Raw when `raw`), KaTeX's sheet added, `status` served before the open, the panel open, the
 *  sentinel's mark painted; in Rendered the math fill has run. */
async function openWith(browser: any, mode: Mode, width: number, raw: boolean, status: Record<string, unknown>, note = NOTE, sentinel = FINAL): Promise<{ page: any; errors: string[] }> {
  const page = await browser.newPage({ viewport: { width, height: 700 } });
  const errors: string[] = [];
  page.on("pageerror", (e: Error) => { errors.push(e.message); });
  const html = pageHtml(mode, { [REPORT]: note }, MT);
  await page.route((u: URL) => u.href.startsWith(ORIGIN), (route: any) => route.fulfill({ status: 200, contentType: "text/html", body: html }));
  await page.goto(ORIGIN + "/");
  await page.addStyleTag({ content: KATEX_CSS });
  if (raw) await page.evaluate(() => { localStorage.setItem("romp:fileviewFmt", JSON.stringify({ md: "raw" })); });
  await page.evaluate(([p, sid, st]: [string, string, unknown]) => { (window as any).__status = st; (window as any).FV.openFileView(p, sid, null); }, [REPORT, SID, status]);
  await page.waitForFunction((raw: boolean) => !!document.querySelector(raw ? ".fileview-body .fv-cl" : ".fileview-md > p"), raw, { timeout: 10000 });
  if (!raw) await filled(page);
  await frames(page, 2);
  await openPanel(page);
  await markPainted(page, id(sentinel));
  return { page, errors };
}
/** The math fill ran: no placeholder left, the display formula's box in the page. */
const filled = (page: any): Promise<unknown> =>
  page.waitForFunction(() => !document.querySelector(".fileview-md .md-math-inline, .fileview-md .md-math-display") && !!document.querySelector(".fileview-md .katex-display"), null, { timeout: 15000 });
/** Wait for the comment's highlight in the view's body (the pass painted it). */
const markPainted = (page: any, cid: string): Promise<unknown> =>
  page.waitForFunction((c: string) => !!document.querySelector('.fileview-body [data-act="fcopen"][data-id="' + c + '"]'), cid, { timeout: 10000 });

type Box = { found: boolean; cls: string; act: string | null; id: string | null; tab: string | null; role: string | null; title: string | null;
  bg: string; shadow: string; outline: string; cursor: string; width: number; height: number; katexChild: boolean; marksInside: number; topMarks: number; presel: number; preselMarks: number; hlMarks: number };
/** The display formula's box as the page shows it: its class and the attributes the paint and the pass set, its computed dress,
 *  its size, whether KaTeX's root is still its one child, and the marks around it. The top-level box by default; `sel` names
 *  another (a quote's, `blockquote .katex-display`). */
const readBox = (page: any, sel = ":scope > .katex-display"): Promise<Box> => page.evaluate((s: string) => {
  const md = document.querySelector(".fileview-md") as HTMLElement;
  const d = md.querySelector(s) as HTMLElement | null;
  const around = { topMarks: md.querySelectorAll(":scope > mark").length, presel: md.querySelectorAll(".fc-presel, .fc-presel-block").length, preselMarks: md.querySelectorAll("mark.fc-presel").length, hlMarks: md.querySelectorAll("mark.fc-hl").length };
  if (!d) return { found: false, cls: "", act: null, id: null, tab: null, role: null, title: null, bg: "", shadow: "", outline: "", cursor: "", width: 0, height: 0, katexChild: false, marksInside: 0, ...around };
  const cs = getComputedStyle(d), r = d.getBoundingClientRect();
  return { found: true, cls: d.className, act: d.getAttribute("data-act"), id: d.getAttribute("data-id"), tab: d.getAttribute("tabindex"), role: d.getAttribute("role"), title: d.getAttribute("title"),
    bg: cs.backgroundColor, shadow: cs.boxShadow, outline: cs.outlineStyle, cursor: cs.cursor, width: r.width, height: r.height,
    katexChild: d.children.length === 1 && d.firstElementChild!.classList.contains("katex"), marksInside: d.querySelectorAll("mark").length, ...around };
}, sel);
type Card = { card: boolean; open: boolean; goto: boolean; reveal: boolean };
/** The comment's card: there, open, offering Scroll (the reference link) or Reveal (readable on the OPEN card alone: a folded card renders no actions row). */
const readCard = (page: any, cid: string): Promise<Card> => page.evaluate((c: string) => {
  const card = document.querySelector('.fileview-aside .fc-card[data-id="' + c + '"]');
  return { card: !!card, open: !!card && card.classList.contains("open"), goto: !!card && !!card.querySelector('[data-act="fcgoto"]'), reveal: !!card && !!card.querySelector('[data-act="fcreveal"]') };
}, cid);
/** A real click on the formula's glyphs (KaTeX's HTML layout, the visible one), then the card's open state awaited. */
async function clickFormula(page: any, cid: string): Promise<void> {
  await page.locator(".fileview-md .katex-display .katex-html").first().click();
  await page.waitForFunction((c: string) => { const k = document.querySelector('.fileview-aside .fc-card[data-id="' + c + '"]'); return !!k && k.classList.contains("open"); }, cid, { timeout: 5000 });
  await frames(page, 2);
}
/** The one stamp a paint leaves (the contract): the class list holds the block class once beside `katex-display`. */
const stampedOnce = (cls: string, block: string): boolean => cls.split(/\s+/).filter(Boolean).sort().join(" ") === ["katex-display", block].sort().join(" ");
const composerQuote = (page: any): Promise<{ open: boolean; quote: string | null; refused: string | null; save: boolean | null }> => page.evaluate(() => {
  const box = document.querySelector(".fc-composer") as HTMLElement | null;
  if (!box) return { open: false, quote: null, refused: null, save: null };
  const save = box.querySelector('[data-act="fcsave"]') as HTMLButtonElement | null;
  return { open: true, quote: box.querySelector(".fc-quote")?.textContent ?? null, refused: box.querySelector(".fc-refused")?.textContent ?? null, save: save ? !save.disabled : null };
});
const squash = (s: string): string => s.replace(/\s+/g, "");
const sortedClasses = (cls: string): string[] => cls.split(/\s+/).filter(Boolean).sort();
/** The covering set on the display formula's box (file-comments.ts coverBox): every covering comment's id, in the pass's order. */
const readIds = (page: any): Promise<string | null> => page.evaluate(() => (document.querySelector(".fileview-md > .katex-display") as HTMLElement | null)?.getAttribute("data-ids") ?? null);
/** Which view stands: the Rendered root, or the Raw rows (Reveal's switch). */
const viewState = (page: any): Promise<{ md: boolean; raw: boolean }> => page.evaluate(() => ({ md: !!document.querySelector(".fileview-md"), raw: !!document.querySelector(".fileview-body .fv-cl") }));

test("a comment on `$$ ... $$` served before a fresh open, on the Files pane at 900 and 380 px and in the chat modal: the .katex-display wears fc-hl-block with the paint's data and the pass's control attributes, the panel's wash and ring (computed background not transparent), KaTeX's root still its one child and no mark at the top level or inside; the card offers Scroll and no Reveal once a click on the formula's glyphs opens it; under print media the wash and ring come off; a reload paints the new box the same, stamped once (before: no class, no wash, the card offering Reveal)", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const [mode, width] of [["pane", 900], ["pane", 380], ["chat", 1000]] as [Mode, number][]) {
      const what = mode + " " + width + "px";
      const { page, errors } = await openWith(browser, mode, width, false, withComments([FINAL, FORMULA], 1));
      const r = await readBox(page);
      assert.equal(r.found, true, what + ": the filled display formula's box");
      assert.equal(stampedOnce(r.cls, "fc-hl-block"), true, what + ": the box wears fc-hl-block once beside katex-display (before: bare): " + JSON.stringify(r.cls));
      assert.deepEqual([r.act, r.id], ["fcopen", id(FORMULA)], what + ": the paint's data on the box");
      assert.deepEqual([r.tab, r.role, r.title], ["0", "button", OPEN_TITLE], what + ": the pass makes it a control, as it makes every mark");
      assert.notEqual(r.bg, TRANSPARENT, what + ": the highlight's wash on the box (before: transparent)");
      assert.notEqual(r.shadow, "none", what + ": ...and its ring");
      assert.equal(r.katexChild, true, what + ": KaTeX's root still the box's one child (no mark between them)");
      assert.deepEqual([r.marksInside, r.topMarks], [0, 0], what + ": no mark inside the formula and none at the top level");
      assert.ok(r.hlMarks >= 1, what + ": the sentinel's mark stands in its paragraph");
      // the click: the nearest data-act above KaTeX's glyphs is the stamped box, so the delegate opens the card
      await clickFormula(page, id(FORMULA));
      const card = await readCard(page, id(FORMULA));
      assert.deepEqual(card, { card: true, open: true, goto: true, reveal: false }, what + ": the open card offers Scroll to the passage and no Reveal (before: Reveal)");
      // print: the wash and ring come off the box as they come off a mark
      await page.emulateMedia({ media: "print" });
      await frames(page, 2);
      const p = await readBox(page);
      assert.deepEqual([p.bg, p.shadow], [TRANSPARENT, "none"], what + ": under print media the box prints bare");
      await page.emulateMedia({ media: "screen" });
      await frames(page, 2);
      // a reload over the same bytes: a new body, the pass stamps the new box once and the same
      const paints = await page.evaluate(() => (window as any).__paints as number);
      await page.evaluate(() => { (window as any).__seam.reload(); });
      await page.waitForFunction((n: number) => (window as any).__paints > n, paints, { timeout: 10000 });
      await filled(page);
      await markPainted(page, id(FINAL));
      await frames(page, 2);
      const again = await readBox(page);
      assert.equal(stampedOnce(again.cls, "fc-hl-block"), true, what + ": after the reload the box is stamped once: " + JSON.stringify(again.cls));
      assert.deepEqual([again.act, again.id, again.katexChild, again.topMarks], ["fcopen", id(FORMULA), true, 0], what + ": the same paint after the reload");
      assert.notEqual(again.bg, TRANSPARENT, what + ": the wash after the reload");
      assert.deepEqual(errors, [], what + ": no script error");
      await page.close();
    }
  });
});

/** A real drag in the Raw view from the first character of the first row whose text is `first` to the last character of the LAST row
 *  whose text is `last` (the fixture's `$$` rows: the same text opens and closes the block, so the rows are found by text and order). */
async function dragRows(page: any, first: string, last: string): Promise<string> {
  await page.evaluate(() => { getSelection()!.removeAllRanges(); });
  const pts = await page.evaluate(([a, b]: [string, string]) => {
    const rows = Array.from(document.querySelectorAll(".fileview-body code.hljs .fv-ct")) as HTMLElement[];
    const from = rows.find((r) => r.textContent === a), to = rows.filter((r) => r.textContent === b).pop();
    if (!from || !to) throw new Error("rows not found: " + JSON.stringify([a, b]));
    from.scrollIntoView({ block: "center" });
    const text = (r: HTMLElement): Text => { const w = document.createTreeWalker(r, NodeFilter.SHOW_TEXT); const t = w.nextNode() as Text | null; if (!t) throw new Error("no text in row"); return t; };
    const rect = (n: Text, off: number) => { const rg = document.createRange(); rg.setStart(n, off); rg.setEnd(n, off + 1); return rg.getBoundingClientRect(); };
    const ft = text(from), lt = text(to);
    const s = rect(ft, 0), e = rect(lt, lt.data.length - 1);
    return { sx: s.left + Math.min(1.5, s.width / 3), sy: s.top + s.height / 2, ex: e.right - Math.min(1.5, e.width / 3), ey: e.top + e.height / 2 };
  }, [first, last]);
  await frames(page, 1);
  await page.mouse.move(pts.sx, pts.sy);
  await page.mouse.down();
  await page.mouse.move((pts.sx + pts.ex) / 2, (pts.sy + pts.ey) / 2, { steps: 3 });
  await page.mouse.move(pts.ex, pts.ey, { steps: 6 });
  await page.mouse.up();
  await frames(page, 2);
  return page.evaluate(() => String(getSelection()));
}

test("the composer's pending target on the formula, made in the Raw view (a real drag over the three `$$` rows, the float, the composer quoting the block with Save) and carried into Rendered by the view switch, on the Files pane and in the chat modal: the .katex-display wears fc-presel-block once with the accent wash and no mark.fc-presel stands anywhere; Cancel leaves no class and no attribute on the box, KaTeX's root in place and the other comment's highlight as it was (before: no target painted in Rendered for a formula alone)", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const [mode, width] of [["pane", 900], ["chat", 1000]] as [Mode, number][]) {
      const what = mode + " " + width + "px";
      const { page, errors } = await openWith(browser, mode, width, true, withComments([FINAL], 1));
      const selected = await dragRows(page, "$$", "$$");
      assert.equal(squash(selected), squash(FORMULA_Q), what + ": the drag selected the block over its three rows: " + JSON.stringify(selected));
      await page.waitForFunction(() => { const f = document.querySelector(".fc-float") as HTMLElement | null; return !!f && !f.hidden; }, null, { timeout: 5000 });
      await page.click(".fc-float");
      await frames(page, 2);
      const c = await composerQuote(page);
      assert.equal(c.open, true, what + ": the composer opened");
      assert.equal(c.refused, null, what + ": a Raw selection maps");
      assert.equal(squash(c.quote || ""), squash(FORMULA_Q), what + ": the composer quotes the block: " + JSON.stringify(c.quote));
      assert.equal(c.save, true, what + ": Save is offered");
      // the switch to Rendered: the target follows the passage into the new view (retargetComposer) and the pass paints it
      await page.evaluate(() => { (window as any).__seam.setMode("rendered"); });
      await page.waitForFunction(() => !!document.querySelector(".fileview-md > p"), null, { timeout: 10000 });
      await filled(page);
      await markPainted(page, id(FINAL));
      await frames(page, 3);
      const r = await readBox(page);
      assert.equal(stampedOnce(r.cls, "fc-presel-block"), true, what + ": the box wears fc-presel-block once (before: bare): " + JSON.stringify(r.cls));
      assert.notEqual(r.bg, TRANSPARENT, what + ": the pending target's wash on the box");
      assert.notEqual(r.shadow, "none", what + ": ...and its ring");
      assert.deepEqual([r.presel, r.preselMarks, r.marksInside, r.topMarks], [1, 0, 0, 0], what + ": the box is the target's one element: no mark.fc-presel, nothing inside the formula, nothing at the top level");
      assert.equal(r.katexChild, true, what + ": KaTeX's root still the box's one child");
      const hl = r.hlMarks;
      assert.ok(hl >= 1, what + ": the sentinel's highlight stands");
      await page.click('.fc-composer [data-act="fccancel"]');
      await frames(page, 3);
      const after = await readBox(page);
      assert.equal(after.cls, "katex-display", what + ": Cancel leaves no class behind: " + JSON.stringify(after.cls));
      assert.deepEqual([after.act, after.id, after.tab, after.role, after.title], [null, null, null, null, null], what + ": ...and no attribute");
      assert.deepEqual([after.bg, after.shadow], [TRANSPARENT, "none"], what + ": the box bare again");
      assert.deepEqual([after.presel, after.katexChild, after.hlMarks], [0, true, hl], what + ": no target anywhere, KaTeX's root in place, the highlight as it was");
      assert.deepEqual(errors, [], what + ": no script error");
      await page.close();
    }
  });
});

test("the panel's half alone, over the box stamped by hand as the paint will stamp it (the anchor map's half is unit A's): the sheets dress the stamped box with the highlight's wash and ring at no change of size, the context cue drops the ring for its dashed outline, the pending target's class wears the accent; and a repaint of the same body (a filter change) strips the box in place, KaTeX's root its child (before: paintAll's unpaint never selected the class, and unwrapMarks would have hoisted KaTeX's root to the top level)", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openWith(browser, "pane", 900, false, withComments([FINAL], 1));
    const bare = await readBox(page);
    assert.deepEqual([bare.found, bare.cls, bare.bg, bare.shadow], [true, "katex-display", TRANSPARENT, "none"], "the box bare before any stamp (no comment on the formula)");
    const stamp = (cls: string) => page.evaluate(([c, cid]: [string, string]) => {
      const d = document.querySelector(".fileview-md > .katex-display") as HTMLElement;
      d.className = "katex-display " + c; d.dataset.act = "fcopen"; d.dataset.id = cid;
    }, [cls, id(FINAL)]);
    await stamp("fc-hl-block");
    await frames(page, 2);
    const hl = await readBox(page);
    assert.notEqual(hl.bg, TRANSPARENT, "fc-hl-block: the wash");
    assert.notEqual(hl.shadow, "none", "fc-hl-block: the ring");
    assert.equal(hl.cursor, "pointer", "fc-hl-block: a control's cursor, as a mark's");
    assert.deepEqual([hl.width, hl.height], [bare.width, bare.height], "the stamp changes no layout: the box the same size (no padding)");
    await stamp("fc-hl-block fc-hl-context");
    await frames(page, 2);
    const ctx = await readBox(page);
    assert.deepEqual([ctx.shadow, ctx.outline], ["none", "dashed"], "the context cue drops the ring and stands its dashed outline, as on a mark");
    assert.notEqual(ctx.bg, TRANSPARENT, "...the wash stays");
    await stamp("fc-presel-block");
    await frames(page, 2);
    const presel = await readBox(page);
    assert.notEqual(presel.bg, TRANSPARENT, "fc-presel-block: the pending target's wash");
    assert.notEqual(presel.bg, hl.bg, "...in the accent, not the highlight's amber");
    assert.notEqual(presel.shadow, "none", "fc-presel-block: its ring");
    await stamp("fc-hl-block");
    await frames(page, 1);
    // the pass's unpaint over the same body: a filter change repaints from the status already here (setFilter, paintAll)
    await page.click('.fileview-aside [data-act="fcfilter"][data-key="comments"]');
    await frames(page, 3);
    const after = await readBox(page);
    assert.equal(after.cls, "katex-display", "the repaint stripped the stamp in place: " + JSON.stringify(after.cls));
    assert.deepEqual([after.act, after.id], [null, null], "...and its data");
    assert.deepEqual([after.katexChild, after.topMarks, after.bg], [true, 0, TRANSPARENT], "KaTeX's root still the box's one child, no mark at the top level, the box bare");
    assert.ok(after.hlMarks >= 1, "the sentinel's highlight painted again by the pass");
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});

test("two comments on one `$$ ... $$` block served before a fresh open, on the Files pane at 900 px and in the chat modal: the one box wears fc-hl-block once, the LATER comment's id as data-id (in front, as the innermost mark is under an inline overlap) and both ids in data-ids in the pass's order; a click on the formula's glyphs opens BOTH cards, each offering Scroll; the earlier card's Scroll finds the box and the view stays Rendered; a reload rebuilds the set the same (before: the later paint's id overwrote the earlier's, the click opened one card, and the earlier card's Scroll fell to Reveal and switched to Raw)", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const [mode, width] of [["pane", 900], ["chat", 1000]] as [Mode, number][]) {
      const what = mode + " " + width + "px";
      const { page, errors } = await openWith(browser, mode, width, false, withComments([FINAL, FORMULA, FORMULA_B], 1));
      const r = await readBox(page);
      assert.equal(stampedOnce(r.cls, "fc-hl-block"), true, what + ": the box stamped once by the two paints: " + JSON.stringify(r.cls));
      assert.deepEqual([r.act, r.id], ["fcopen", id(FORMULA_B)], what + ": the later comment in front");
      assert.equal(await readIds(page), id(FORMULA) + " " + id(FORMULA_B), what + ": every covering id on the box, in the pass's order (before: no such attribute)");
      assert.deepEqual([r.katexChild, r.marksInside, r.topMarks], [true, 0, 0], what + ": KaTeX's root the box's one child, no mark inside or at the top level");
      const before = [await readCard(page, id(FORMULA)), await readCard(page, id(FORMULA_B))];
      assert.deepEqual(before.map((c) => [c.card, c.open]), [[true, false], [true, false]], what + ": both cards there and folded before the click");
      await page.locator(".fileview-md .katex-display .katex-html").first().click();
      await page.waitForFunction((cs: string[]) => cs.every((c) => !!document.querySelector('.fileview-aside .fc-card[data-id="' + c + '"].open')), [id(FORMULA), id(FORMULA_B)], { timeout: 5000 });
      await frames(page, 2);
      assert.deepEqual(await readCard(page, id(FORMULA)), { card: true, open: true, goto: true, reveal: false }, what + ": the earlier comment's card opened by the click, offering Scroll (before: folded, unreachable from the formula)");
      assert.deepEqual(await readCard(page, id(FORMULA_B)), { card: true, open: true, goto: true, reveal: false }, what + ": ...and the later one's");
      await page.click('.fileview-aside .fc-card[data-id="' + id(FORMULA) + '"] [data-act="fcgoto"]');
      await frames(page, 3);
      assert.deepEqual(await viewState(page), { md: true, raw: false }, what + ": Scroll on the earlier card found the box: the view stays Rendered (before: no element carried its id, so Reveal switched to Raw)");
      // a reload over the same bytes: the new box carries the same set and the same front
      const paints = await page.evaluate(() => (window as any).__paints as number);
      await page.evaluate(() => { (window as any).__seam.reload(); });
      await page.waitForFunction((n: number) => (window as any).__paints > n, paints, { timeout: 10000 });
      await filled(page);
      await markPainted(page, id(FINAL));
      await frames(page, 2);
      const again = await readBox(page);
      assert.deepEqual([stampedOnce(again.cls, "fc-hl-block"), again.id, await readIds(page)], [true, id(FORMULA_B), id(FORMULA) + " " + id(FORMULA_B)], what + ": after the reload the same set and the same front");
      assert.deepEqual(errors, [], what + ": no script error");
      await page.close();
    }
  });
});

test("the composer's pending target on a formula a comment already highlights, made in the Raw view (the drag over the three `$$` rows, the float, the composer) and carried into Rendered by the view switch, on the Files pane at 900 px: the one box wears both block classes with the highlight's data under the target; Cancel takes the target's class off and leaves the highlight standing, its class once, its data, the control attributes, its own wash and ring, and a click on the formula opens its card, which offers Scroll (before: the target's unpaint stripped both classes and every attribute off the shared box, so the formula went bare and opened nothing while its card still offered Scroll, until the next full pass)", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openWith(browser, "pane", 900, true, withComments([FINAL, FORMULA], 1));
    const selected = await dragRows(page, "$$", "$$");
    assert.equal(squash(selected), squash(FORMULA_Q), "the drag selected the block over its three rows: " + JSON.stringify(selected));
    await page.waitForFunction(() => { const f = document.querySelector(".fc-float") as HTMLElement | null; return !!f && !f.hidden; }, null, { timeout: 5000 });
    await page.click(".fc-float");
    await frames(page, 2);
    const c = await composerQuote(page);
    assert.deepEqual([c.open, c.refused, c.save], [true, null, true], "the composer quotes the block with Save: " + JSON.stringify(c.quote));
    await page.evaluate(() => { (window as any).__seam.setMode("rendered"); });
    await page.waitForFunction(() => !!document.querySelector(".fileview-md > p"), null, { timeout: 10000 });
    await filled(page);
    await markPainted(page, id(FINAL));
    await frames(page, 3);
    const pending = await readBox(page);
    assert.deepEqual(sortedClasses(pending.cls), ["fc-hl-block", "fc-presel-block", "katex-display"], "the two paints share the box: " + JSON.stringify(pending.cls));
    assert.deepEqual([pending.act, pending.id, pending.presel, pending.preselMarks], ["fcopen", id(FORMULA), 1, 0], "the highlight's data stands under the target; the box is the target's one element");
    await page.click('.fc-composer [data-act="fccancel"]');
    await frames(page, 3);
    const after = await readBox(page);
    assert.equal(stampedOnce(after.cls, "fc-hl-block"), true, "after Cancel the highlight's class stands alone on the box (before: stripped with the target's): " + JSON.stringify(after.cls));
    assert.deepEqual([after.act, after.id, after.tab, after.role, after.title], ["fcopen", id(FORMULA), "0", "button", OPEN_TITLE], "...with the highlight's data and the pass's control attributes (before: none)");
    assert.notEqual(after.bg, TRANSPARENT, "the highlight's wash stands (before: transparent)");
    assert.notEqual(after.bg, pending.bg, "...its own, not the target's accent");
    assert.notEqual(after.shadow, "none", "...and its ring");
    assert.deepEqual([after.presel, after.katexChild, after.topMarks], [0, true, 0], "no target left anywhere, KaTeX's root in place, no mark at the top level");
    await clickFormula(page, id(FORMULA));
    assert.deepEqual(await readCard(page, id(FORMULA)), { card: true, open: true, goto: true, reveal: false }, "a click on the formula opens its card, which offers Scroll (before: the click opened nothing)");
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});

test("a display formula inside a blockquote with a blank `>` line and a quote line after its closer, on the Files pane at 900 px (the Slice 8 review, round 2): a comment whose quote is the quoted block, the opener through the closing `$$` (the natural Raw quote), served before a fresh open stamps the quote's .katex-display with fc-hl-block, the paint's data and the pass's control attributes, the wash and ring, KaTeX's root its one child, and a click on the glyphs opens its card offering Scroll and no Reveal; the composer's pending target made by a real drag over the three quoted rows in Raw and carried into Rendered by the view switch stamps the same box with fc-presel-block, and Cancel leaves it bare (before: the formula's hole ran to the raw's end, past the `> ` marker of the quote line after it, where the span's trim stopped, so the exact quote never covered the formula: no class, no wash, the card offering Reveal, and no target on the box)", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const QBOX = "blockquote .katex-display";
    // the served comment
    {
      const { page, errors } = await openWith(browser, "pane", 900, false, withComments([FINAL_Q, QUOTED], 1), NOTE_Q, FINAL_Q);
      const r = await readBox(page, QBOX);
      assert.equal(r.found, true, "the quoted display formula's box");
      assert.equal(stampedOnce(r.cls, "fc-hl-block"), true, "the quoted box wears fc-hl-block once (before: bare): " + JSON.stringify(r.cls));
      assert.deepEqual([r.act, r.id], ["fcopen", id(QUOTED)], "the paint's data on the box");
      assert.deepEqual([r.tab, r.role, r.title], ["0", "button", OPEN_TITLE], "the pass makes it a control");
      assert.notEqual(r.bg, TRANSPARENT, "the highlight's wash on the box (before: transparent)");
      assert.notEqual(r.shadow, "none", "...and its ring");
      assert.deepEqual([r.katexChild, r.marksInside, r.topMarks], [true, 0, 0], "KaTeX's root the box's one child, no mark inside or at the top level");
      await clickFormula(page, id(QUOTED));
      assert.deepEqual(await readCard(page, id(QUOTED)), { card: true, open: true, goto: true, reveal: false }, "the open card offers Scroll and no Reveal (before: Reveal)");
      assert.deepEqual(errors, [], "no script error");
      await page.close();
    }
    // the pending target from a Raw drag over the quoted rows
    {
      const { page, errors } = await openWith(browser, "pane", 900, true, withComments([FINAL_Q], 1), NOTE_Q, FINAL_Q);
      const selected = await dragRows(page, "> $$", "> $$");
      assert.equal(squash(selected), squash("> " + QUOTED_Q), "the drag selected the quoted block over its three rows: " + JSON.stringify(selected));
      await page.waitForFunction(() => { const f = document.querySelector(".fc-float") as HTMLElement | null; return !!f && !f.hidden; }, null, { timeout: 5000 });
      await page.click(".fc-float");
      await frames(page, 2);
      const c = await composerQuote(page);
      assert.deepEqual([c.open, c.refused, c.save], [true, null, true], "the composer quotes the quoted block with Save: " + JSON.stringify(c.quote));
      assert.equal(squash(c.quote || ""), squash("> " + QUOTED_Q), "...the rows' text, markers included");
      await page.evaluate(() => { (window as any).__seam.setMode("rendered"); });
      await page.waitForFunction(() => !!document.querySelector(".fileview-md > p"), null, { timeout: 10000 });
      await filled(page);
      await markPainted(page, id(FINAL_Q));
      await frames(page, 3);
      const r = await readBox(page, QBOX);
      assert.equal(stampedOnce(r.cls, "fc-presel-block"), true, "the quoted box wears fc-presel-block once (before: bare): " + JSON.stringify(r.cls));
      assert.deepEqual([r.presel, r.preselMarks, r.marksInside, r.katexChild], [1, 0, 0, true], "the box is the target's one element");
      assert.notEqual(r.bg, TRANSPARENT, "the pending target's wash");
      await page.click('.fc-composer [data-act="fccancel"]');
      await frames(page, 3);
      const after = await readBox(page, QBOX);
      assert.deepEqual([after.cls, after.act, after.id, after.presel], ["katex-display", null, null, 0], "Cancel leaves the box bare and no target anywhere");
      assert.deepEqual(errors, [], "no script error");
      await page.close();
    }
  });
});

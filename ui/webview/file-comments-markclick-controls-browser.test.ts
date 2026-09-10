// The marks' drag guard, judged against the CLICKED mark, over the REAL viewer and the REAL panel with a real mouse
// (plans/file-review.md, Slice 2, the marks' click rule; the review of 2026-09-09 of the fix of that day; file-comments.ts
// dragClick and endInside). The first guard read any non-collapsed selection with both ends in the body as this click's
// drag, and a press collapses a standing selection only through text it can select, so every control whose press leaves
// the selection standing went dead while words stood selected anywhere in the body: a deletion's struck label
// (`span.fc-del`, user-select: none, its text CSS-generated), a region rectangle over a figure (the overlay cancels its
// pointerdown), a change mark inside an author's link (a draggable anchor), a framed picture with the panel closed (no
// overlay stands over it, so the click is the browser's own, detail 1). This leg makes the state a reader leaves behind —
// a real drag over words in another paragraph — and clicks each of those controls, reading that the card opens and that
// the selection stood through the press (the case the finding names, not a press that collapsed it); that a drag inside
// an insertion's mark still opens nothing, scrolls nothing and leaves the float standing, with no press pulse on the mark
// (the delegate's `.romp-acted` comes off in the click's own task); that a drag ending at the mark's last character, whose
// end an engine may report at the mark's edge rather than in it, is the drag's too; that a tap on the deletion label with
// a selection standing (Chromium, a touch screen) opens the card; and, with the panel CLOSED, that the framed figure's and
// the label's clicks open the panel and the card while a drag inside the mark opens neither (the review's ruling: a drag
// with the panel closed behaves as one over any passage). Chromium and Firefox, Rendered and Raw where the shape exists
// (the link and the figures are Rendered's). Skips LOUDLY without a playwright browser (CI installs none), as the other
// browser legs do. Legs await frames, never a timer. Synthetic values only: an invented report, /repo/notes-api paths,
// the placeholder sid, the session name "api", a figure painted on a canvas.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as path from "node:path";
import { createRequire } from "node:module";
import { pageHtml, frames, openPanel, putAtTop, PARA, REPORT, SID, MT, ORIGIN, EXT, STATUS as BASE_STATUS } from "./real-viewer-leg";

const requireCjs = createRequire(path.join(EXT, "package.json"));
let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

// ── the document: sixty paragraphs; a session's insertion at the end of the thirtieth, a deletion in the thirty-first, an
// insertion inside an author's link in the thirty-second, then two figures, one with a region comment, one framed by an
// embed-line comment ────────────────────────────────────────────────────────────────────────────────────────────────
const T0 = 1757145600000;
const INS = ", and the session added a warm-up step for the cache before the first request lands";
const P30 = PARA(30).slice(0, -1) + INS + ".";
const P32 = "Paragraph 32: the runbook now points at [the cache warm-up docs](https://example.test/docs) for the first request, and the rest of the paragraph runs on as before so that it wraps.";
const LINK_INS = " warm-up";
const FIG = "![Figure](figure.png)", CHART = "![Chart](chart.png)";
const SRC = "# Report\n\n" + Array.from({ length: 60 }, (_, i) => (i + 1 === 30 ? P30 : i + 1 === 32 ? P32 + "\n\n" + FIG + "\n\n" + CHART : PARA(i + 1))).join("\n\n") + "\n";
const INS_AT = SRC.indexOf(INS);
const DEL_AT = SRC.indexOf("dolor", SRC.indexOf("Paragraph 31:"));
const LINK_INS_AT = SRC.indexOf(LINK_INS, SRC.indexOf("Paragraph 32:"));
const HUNKS = [
  { id: "h1", author: "api", ts: T0 - 30000, kind: "ins", curFrom: INS_AT, curTo: INS_AT + INS.length, baseFrom: INS_AT, baseTo: INS_AT, oldText: "", newText: INS, anchor: null },
  { id: "h2", author: "api", ts: T0 - 20000, kind: "del", curFrom: DEL_AT, curTo: DEL_AT, baseFrom: DEL_AT, baseTo: DEL_AT + 8, oldText: "quickly ", newText: "", anchor: null },
  { id: "h3", author: "api", ts: T0 - 10000, kind: "ins", curFrom: LINK_INS_AT, curTo: LINK_INS_AT + LINK_INS.length, baseFrom: LINK_INS_AT, baseTo: LINK_INS_AT, oldText: "", newText: LINK_INS, anchor: null },
];
const around = (quote: string) => { const at = SRC.indexOf(quote); assert.ok(at >= 0, quote); return { quote, prefix: SRC.slice(Math.max(0, at - 24), at), suffix: SRC.slice(at + quote.length, at + quote.length + 24) }; };
const REGION_ID = T0 + "-1", CHART_ID = T0 + "-2";
// the region comment on the first figure (no hash: the rectangle is the dotted fc-unknown one, a region all the same), and
// the comment whose passage is the second figure's embed line, which frames the picture in Rendered
const REGION = { id: REGION_ID, author: "you", ts: T0, body: "Crop this band.", replies: [], resolved: false, anchor: around(FIG), target: { kind: "image", region: { x: 0.15, y: 0.2, w: 0.4, h: 0.4 }, src: "figure.png" } };
const CHARTC = { id: CHART_ID, author: "you", ts: T0 + 1, body: "Label the axes.", replies: [], resolved: false, anchor: around(CHART) };
const STATUS = { ...BASE_STATUS, hunks: HUNKS, store: { ...BASE_STATUS.store, comments: [REGION, CHARTC] }, unsent: { comments: [REGION_ID, CHART_ID], replies: [], accepted: 0, rejected: 0, watermark: null } };

const MARK = '.fileview-body [data-act="fcchange"][data-id="h1"]';
const DEL = '.fileview-body .fc-del[data-act="fcchange"][data-id="h2"]';
const LINKMARK = '.fileview-body [data-act="fcchange"][data-id="h3"]';
const RECT = '.fileview-body .fc-region[data-act="fcopen"][data-id="' + REGION_ID + '"]';
const FRAME = '.fileview-body img.fc-img[data-act="fcopen"][data-id="' + CHART_ID + '"]';

type Sel = { text: string; collapsed: boolean; inBody: boolean };
type Scene = { aside: boolean; open: string[]; scrollTop: number; floatHidden: boolean; sel: Sel; acted: string[]; last: any; view: "rendered" | "raw" };
/** What the leg reads: the aside, the open cards' keys, the body's scroll, the float, the live selection, the marks wearing
 *  the press pulse, and the last click the page's recorder saw. */
const scene = (page: any): Promise<Scene> => page.evaluate(() => {
  const body = document.querySelector(".fileview-body") as HTMLElement;
  const aside = document.querySelector(".fileview-aside") as HTMLElement | null;
  const s = getSelection();
  const fl = document.querySelector(".fc-float") as HTMLElement | null;
  return {
    aside: !!aside, open: aside ? Array.from(aside.querySelectorAll(".fc-card.open")).map((c) => (c as HTMLElement).dataset.id || "") : [],
    scrollTop: body.scrollTop, floatHidden: fl ? fl.hidden : true,
    sel: { text: String(s), collapsed: !s || s.isCollapsed, inBody: !!s && !!s.anchorNode && !!s.focusNode && body.contains(s.anchorNode) && body.contains(s.focusNode) },
    acted: Array.from(body.querySelectorAll(".romp-acted")).map((m) => (m as HTMLElement).dataset.id || (m as HTMLElement).className),
    last: (window as any).__lastClick || null, view: document.querySelector(".fileview-md") ? "rendered" : "raw",
  };
});

/** A 600x300 PNG, drawn in a page, for the figures the note embeds (the kernel's /file route is answered with it). */
async function figurePng(browser: any): Promise<Buffer> {
  const p = await browser.newPage();
  const url: string = await p.evaluate(() => { const c = document.createElement("canvas"); c.width = 600; c.height = 300; const cx = c.getContext("2d")!; cx.fillStyle = "rgb(100,120,110)"; cx.fillRect(0, 0, 600, 300); cx.fillStyle = "rgb(200,180,60)"; cx.fillRect(60, 40, 240, 120); return c.toDataURL("image/png"); });
  await p.close();
  return Buffer.from(url.slice(url.indexOf(",") + 1), "base64");
}

/** The page: the report open in the view, the status set before the open, the figures loaded, the panel open or left closed,
 *  the marks painted, and a capture-phase recorder of the last click's target, count and the selection it arrived with. */
async function openWith(ctx: any, png: Buffer, raw: boolean, panel: boolean): Promise<{ page: any; errors: string[] }> {
  const page = await ctx.newPage({ viewport: { width: 1000, height: 900 } });
  const errors: string[] = [];
  page.on("pageerror", (e: Error) => { errors.push(e.message); });
  const html = pageHtml("pane", { [REPORT]: SRC }, MT);
  await page.route((u: URL) => u.href.startsWith(ORIGIN), (route: any) => route.fulfill({ status: 200, contentType: "text/html", body: html }));
  await page.route((u: URL) => u.href.startsWith(ORIGIN) && u.pathname === "/file", (route: any) => route.fulfill({ status: 200, contentType: "image/png", body: png }));   // registered later, so matched first: the figures' bytes
  await page.goto(ORIGIN + "/");
  if (raw) await page.evaluate(() => { localStorage.setItem("romp:fileviewFmt", JSON.stringify({ md: "raw" })); });
  await page.evaluate(([p, sid, st]: [string, string, unknown]) => {
    (window as any).__status = st;
    document.addEventListener("click", (ev) => {
      const t = ev.target as Element | null;
      const c = t && typeof t.closest === "function" ? (t.closest("[data-act]") as HTMLElement | null) : null;
      const s = getSelection();
      (window as any).__lastClick = { act: c ? c.dataset.act : null, id: c ? c.dataset.id : null, detail: (ev as MouseEvent).detail, collapsed: !s || s.isCollapsed,
        focus: s && s.focusNode ? (s.focusNode.nodeType === 3 ? "#text" : s.focusNode.nodeName) + "@" + s.focusOffset + (c && c.contains(s.focusNode) ? " in the mark" : c ? " outside the mark" : "") : null };
    }, true);
    (window as any).FV.openFileView(p, sid, null);
  }, [REPORT, SID, STATUS]);
  await page.waitForFunction((raw: boolean) => !!document.querySelector(raw ? ".fileview-body .fv-cl" : ".fileview-md > p"), raw, { timeout: 10000 });
  if (!raw) await page.waitForFunction(() => { const is = Array.from(document.querySelectorAll(".fileview-md img")) as HTMLImageElement[]; return is.length === 2 && is.every((i) => i.complete && i.naturalWidth === 600); }, null, { timeout: 10000 });
  await frames(page, 2);
  if (panel) await openPanel(page);
  else await page.waitForFunction(() => { const u = document.querySelector(".fileview-fc"); return !!u && !(u as HTMLElement).hidden; }, null, { timeout: 5000 });
  await page.waitForFunction((sel: string) => !!document.querySelector(sel), MARK, { timeout: 10000 });
  await frames(page, 2);
  return { page, errors };
}

/** The block starting with `text` at the body's top edge, the selection cleared, so the controls below it stand in view. */
async function topAt(page: any, text: string): Promise<void> {
  await page.evaluate(() => { getSelection()!.removeAllRanges(); });
  await putAtTop(page, text);
  await frames(page, 2);
}
type Line = { x1: number; y1: number; x2: number; y2: number; text: string };
/** A drag's line over `from`..`to` of the first text node of a block or mark: the words of a plain paragraph (`starts`: the
 *  block's opening text; a Raw row's text sits in its .fv-ct) or of a mark (`sel`). The press lands a pixel into the first
 *  character, the release a pixel before the last one's right edge, each on its own line (a mark wraps). With `toEdge`, the
 *  range runs to the node's last character. */
const lineOf = (page: any, where: { starts?: string; sel?: string }, from: number, to: number, toEdge = false): Promise<Line> => page.evaluate(([where, from, to, toEdge]: [{ starts?: string; sel?: string }, number, number, boolean]) => {
  const body = document.querySelector(".fileview-body")!;
  let host: Element | null = null;
  if (where.sel) host = body.querySelector(where.sel);
  else { const blocks = Array.from(body.querySelectorAll(document.querySelector(".fileview-md") ? ".fileview-md > *" : "code.hljs .fv-cl")); host = blocks.find((b) => (b.textContent || "").startsWith(where.starts!)) || null; }
  if (!host) throw new Error("no host for " + JSON.stringify(where));
  const h = host.querySelector(".fv-ct") || host;
  const t = (Array.from(h.childNodes).find((n) => n.nodeType === 3 && (n.textContent || "").length >= to) as Text | undefined) || null;
  if (!t) throw new Error("no text node of " + to + " characters directly in " + JSON.stringify(where) + ": " + h.outerHTML.slice(0, 200));
  const end = toEdge ? t.data.length : to;
  const first = document.createRange(); first.setStart(t, from); first.setEnd(t, from + 1);
  const last = document.createRange(); last.setStart(t, end - 1); last.setEnd(t, end);
  const fb = first.getBoundingClientRect(), lb = last.getBoundingClientRect();
  return { x1: fb.left + 1, y1: fb.top + fb.height / 2, x2: lb.right - 1, y2: lb.top + lb.height / 2, text: t.data.slice(from, end) };
}, [where, from, to, toEdge]);
/** A real drag along the line, left to right: press, four steps, release; the frames after it, unless the caller reads first. */
async function drag(page: any, l: Line, settle = true): Promise<void> {
  await page.mouse.move(l.x1, l.y1);
  await page.mouse.down();
  await page.mouse.move(l.x2, l.y2, { steps: 4 });
  await page.mouse.up();
  if (settle) await frames(page, 3);
}
/** The words of paragraph `n` selected by a real drag (the standing selection), the float offered when the panel is open. */
async function standing(page: any, n: number): Promise<string> {
  const l = await lineOf(page, { starts: "Paragraph " + n + ":" }, 2, 12);
  await drag(page, l);
  const s = await scene(page);
  assert.equal(s.sel.text, l.text, "the drag selected paragraph " + n + "'s words");
  return l.text;
}
/** The centre of a control, checked to be inside the body's box (a click off-screen would prove nothing). */
const centre = (page: any, sel: string): Promise<{ x: number; y: number; w: number; h: number }> => page.evaluate((sel: string) => {
  const el = document.querySelector(sel) as HTMLElement | null;
  if (!el) throw new Error("no control " + sel);
  const r = el.getBoundingClientRect(), b = document.querySelector(".fileview-body")!.getBoundingClientRect();
  if (!(r.width > 0 && r.height > 0)) throw new Error("no box for " + sel + ": " + JSON.stringify(r));
  if (r.top < b.top || r.bottom > b.bottom || r.left < b.left || r.right > b.right) throw new Error("the control " + sel + " is not wholly in the body's box: " + JSON.stringify(r) + " vs " + JSON.stringify(b));
  return { x: r.left + r.width / 2, y: r.top + r.height / 2, w: r.width, h: r.height };
}, sel);
async function clickOn(page: any, sel: string): Promise<void> {
  const c = await centre(page, sel);
  await page.mouse.click(c.x, c.y);
  await frames(page, 3);
}

async function inEngine(t: any, name: string, body: (browser: any) => Promise<void>): Promise<void> {
  if (!pw) { t.skip("playwright is not installed under vscode-extension; the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw[name].launch(); }
  catch (e) { t.skip("no playwright " + name + " on this box; this leg needs it (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  try { await body(browser); } finally { await browser.close(); }
}

for (const name of ["chromium", "firefox"]) {
  test(`in ${name}, the real viewer, pane 1000x900: with words selected in another paragraph a click on a deletion's label, on a mark inside an author's link, on a region rectangle and on a framed figure opens its card; a drag inside an insertion's mark still opens nothing and leaves no press pulse; the panel closed, the label and the frame open the panel and the card, the drag neither`, { timeout: 300000 }, async (t) => {
    await inEngine(t, name, async (browser) => {
      const png = await figurePng(browser);
      for (const raw of [false, true]) {
        const cell = name + (raw ? " Raw" : " Rendered");
        const { page, errors } = await openWith(browser, png, raw, true);
        let s = await scene(page);
        assert.equal(s.view, raw ? "raw" : "rendered", cell + ": the view");
        assert.equal(s.aside, true, cell + ": the panel is open");
        // ── the deletion's label: its press collapses nothing (user-select: none, generated text), so the selection stands through it ──
        await topAt(page, "Paragraph 28:");
        let words = await standing(page, 29);
        s = await scene(page);
        assert.equal(s.floatHidden, false, cell + ": the Comment float stands beside the words");
        assert.ok(!s.open.includes("chg:h2"), cell + ": the deletion's card starts closed");
        await clickOn(page, DEL);
        s = await scene(page);
        assert.deepEqual([s.last.act, s.last.id, s.last.detail], ["fcchange", "h2", 1], cell + ": the click landed on the label, the browser's own: " + JSON.stringify(s.last));
        assert.equal(s.last.collapsed, false, cell + ": …and arrived with the selection standing (the press collapsed nothing)");
        assert.ok(s.open.includes("chg:h2"), cell + ": the deletion's card opened: " + JSON.stringify(s.open));
        assert.equal(s.sel.text, words, cell + ": the selection still stands after the open");
        // ── the mark inside the author's link (Rendered: the anchor is draggable, so its press collapses nothing; Raw: the label is plain text) ──
        await topAt(page, "Paragraph 28:");
        words = await standing(page, 29);
        const pages0 = browser.contexts().reduce((n: number, c: any) => n + c.pages().length, 0);
        const linked = await page.evaluate((sel: string) => { const m = document.querySelector(sel)!; const a = m.closest("a"); return a ? { target: a.getAttribute("target"), draggable: (a as HTMLElement).draggable } : null; }, LINKMARK);
        if (!raw) assert.deepEqual(linked, { target: "_blank", draggable: true }, cell + ": the mark stands inside the author's link, a draggable anchor");
        await clickOn(page, LINKMARK);
        s = await scene(page);
        assert.deepEqual([s.last.act, s.last.id, s.last.detail], ["fcchange", "h3", 1], cell + ": the click landed on the link's mark: " + JSON.stringify(s.last));
        if (!raw) assert.equal(s.last.collapsed, false, cell + ": …with the selection standing (the anchor's press collapsed nothing)");
        assert.ok(s.open.includes("chg:h3"), cell + ": the change's card opened: " + JSON.stringify(s.open));
        if (!raw) assert.equal(s.sel.text, words, cell + ": the selection still stands");
        assert.equal(browser.contexts().reduce((n: number, c: any) => n + c.pages().length, 0), pages0, cell + ": no tab opened to the author's URL (the click is cancelled as before)");
        // ── the region rectangle (Rendered: the overlay cancels its pointerdown, so the selection stands through the press) ──
        if (!raw) {
          await topAt(page, "Paragraph 31:");
          words = await standing(page, 32);
          await clickOn(page, RECT);
          s = await scene(page);
          assert.deepEqual([s.last.act, s.last.id, s.last.detail], ["fcopen", REGION_ID, 1], cell + ": the browser's own click landed on the rectangle: " + JSON.stringify(s.last));
          assert.equal(s.last.collapsed, false, cell + ": …with the selection standing (the cancelled press collapsed nothing)");
          assert.ok(s.open.includes(REGION_ID), cell + ": the region comment's card opened: " + JSON.stringify(s.open));
          assert.equal(s.sel.text, words, cell + ": the selection still stands");
        }
        // ── the drag inside the insertion's mark: no card, no scroll, the float stands, and no press pulse on the mark ──
        await topAt(page, "Paragraph 29:");
        s = await scene(page);
        const top0 = s.scrollTop;
        const open0 = s.open.length;
        const l = await lineOf(page, { sel: MARK }, 2, 14);
        await drag(page, l, false);
        s = await scene(page);                          // read in the click's wake, well inside flash's 280 ms
        assert.equal(s.sel.text, l.text, cell + ": the drag selected the words inside the mark");
        assert.deepEqual([s.last.act, s.last.id, s.last.detail], ["fcchange", "h1", 1], cell + ": the click that ended the drag landed on the mark: " + JSON.stringify(s.last));
        assert.equal(s.open.length, open0, cell + ": …and opened no card: " + JSON.stringify(s.open));
        assert.equal(s.scrollTop, top0, cell + ": …and the body did not scroll");
        assert.equal(s.floatHidden, false, cell + ": the Comment float stands beside the selection");
        assert.equal(s.acted.includes("h1"), false, cell + ": the mark wears no press pulse: the click stood down shows nothing (pulsed now: " + JSON.stringify(s.acted) + ", a control clicked a moment ago may still be within flash's 280 ms)");
        await frames(page, 3);
        s = await scene(page);
        assert.equal(s.open.length, open0, cell + ": still no card after the frames");
        assert.equal(s.acted.includes("h1"), false, cell + ": …and still no pulse on the mark");
        // ── a drag to the mark's last character: an end an engine may report at the mark's edge is the drag's too ──
        await topAt(page, "Paragraph 29:");
        const e = await lineOf(page, { sel: MARK }, 2, 14, true);
        await drag(page, e);
        s = await scene(page);
        assert.ok(s.sel.text.length >= e.text.length - 1 && e.text.startsWith(s.sel.text), cell + ": the drag to the edge selected the mark's words to its last character: " + JSON.stringify(s.sel.text));
        assert.deepEqual([s.last.act, s.last.id, s.last.detail], ["fcchange", "h1", 1], cell + ": the click landed on the mark: " + JSON.stringify(s.last));
        assert.equal(s.open.length, open0, cell + ": no card opened for the drag to the mark's edge (the selection's end reported " + s.last.focus + ")");
        t.diagnostic(cell + ": the drag to the mark's last character ended with the selection's focus at " + s.last.focus);
        assert.deepEqual(errors, [], cell + ": no script error in the page");
        await page.close();
        // ── the panel CLOSED: the marks are painted; the label's and the frame's clicks open the panel and the card; the drag opens neither ──
        for (const ctl of raw ? [DEL] : [DEL, FRAME]) {
          const { page: p2, errors: err2 } = await openWith(browser, png, raw, false);
          s = await scene(p2);
          assert.equal(s.aside, false, cell + ": the panel starts closed");
          await topAt(p2, ctl === FRAME ? "Paragraph 31:" : "Paragraph 28:");
          words = await standing(p2, ctl === FRAME ? 32 : 29);
          await clickOn(p2, ctl);
          s = await scene(p2);
          const key = ctl === FRAME ? CHART_ID : "chg:h2";
          assert.equal(s.last.detail, 1, cell + ": the browser's own click on " + ctl + ": " + JSON.stringify(s.last));
          assert.equal(s.last.collapsed, false, cell + ": …with the selection standing");
          assert.equal(s.aside, true, cell + ": the click on " + (ctl === FRAME ? "the framed figure" : "the deletion's label") + " opened the panel");
          assert.ok(s.open.includes(key), cell + ": …and its card: " + JSON.stringify(s.open));
          assert.deepEqual(err2, [], cell + ": no script error (panel closed, " + ctl + ")");
          await p2.close();
        }
        const { page: p3, errors: err3 } = await openWith(browser, png, raw, false);
        await topAt(p3, "Paragraph 29:");
        const l3 = await lineOf(p3, { sel: MARK }, 2, 14);
        await drag(p3, l3);
        s = await scene(p3);
        assert.equal(s.sel.text, l3.text, cell + ": panel closed, the drag selected the words inside the mark");
        assert.deepEqual([s.last.act, s.last.id, s.last.detail], ["fcchange", "h1", 1], cell + ": …its click landed on the mark");
        assert.equal(s.aside, false, cell + ": …and opened no panel: a drag with the panel closed is a drag over any passage (the ruling of 2026-09-09)");
        assert.equal(s.acted.includes("h1"), false, cell + ": …and left no press pulse on the mark: " + JSON.stringify(s.acted));
        assert.deepEqual(err3, [], cell + ": no script error (panel closed, the drag)");
        await p3.close();
      }
      // ── a touch screen (Chromium): a tap on the deletion's label with a selection standing opens the card ──
      if (name === "chromium") {
        const ctx = await browser.newContext({ hasTouch: true });
        try {
          const { page, errors } = await openWith(ctx, png, false, true);
          await topAt(page, "Paragraph 28:");
          const words = await page.evaluate(() => {
            const p = Array.from(document.querySelectorAll(".fileview-md > p")).find((b) => (b.textContent || "").startsWith("Paragraph 29:"))!;
            const t = Array.from(p.childNodes).find((n) => n.nodeType === 3) as Text;
            getSelection()!.setBaseAndExtent(t, 2, t, 12);
            return t.data.slice(2, 12);
          });
          const c = await centre(page, DEL);
          await page.touchscreen.tap(c.x, c.y);
          await frames(page, 3);
          const s = await scene(page);
          assert.deepEqual([s.last.act, s.last.id], ["fcchange", "h2"], "touch: the tap's click landed on the label: " + JSON.stringify(s.last));
          assert.ok(s.last.detail !== 0, "touch: the tap's click has a pointer behind it (detail " + s.last.detail + ")");
          assert.ok(s.open.includes("chg:h2"), "touch: the deletion's card opened with the selection standing (" + JSON.stringify(words) + "): " + JSON.stringify(s.open) + " " + JSON.stringify(s.last));
          assert.deepEqual(errors, [], "touch: no script error in the page");
          await page.close();
        } finally { await ctx.close(); }
      }
    });
  });
}

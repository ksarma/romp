// The about follow-on over the REAL viewer and the REAL panel, in Chromium and Firefox (plans/file-review.md, "The about
// follow-on (2026-09-10)" under Slice 2; decision 45; section 3's rule under decision 44's neighbour). What a stand-in
// cannot show is measured here: the composer opened by Comment on this change anchored over the change's real span, with
// its presel painted and the about option checked; a real drag inside an insertion's mark and inside a substitution's new
// text opening the passage composer with the option checked, in Rendered with the marks shown and hidden and in Raw,
// the saved comment an ordinary passage comment carrying changeIds and painting as its own card and highlight; the
// option unchecked saving no changeIds; a real drag from inside the insertion's last word across the mark's end into the
// plain text after it (the contract's "spanning a boundary") a passage comment over the whole selection with the option
// checked, its highlight painted in pieces on both sides of the mark's edge, and that comment and the one inside the
// mark painting in the OTHER view once the Rendered/Raw toggle is clicked (the contract's "paints in the other view");
// a selection over a deletion's struck label alone (the label is generated text, so a range over the point holds no
// text of the file) offering the comment about that change by id, and the saved card laid level with the deletion's
// mark in the margin layout (the markTop fallback); the tags on both cards, the pointer over a comment's tag ringing
// the change's marks (a real computed outline), and the change card's count tag bringing the first comment about the
// change into view with All chosen; a legacy suggestionId comment wearing "answered by a change". Skips LOUDLY without
// a playwright browser (CI installs none), as the other browser legs do. Legs await frames, never a timer. Synthetic
// values only: an invented report, /repo/notes-api paths, the placeholder sid, the session name "api".
//
// The page's stub is armed against the panel's poll before the file opens (armHarness): the kernel HEADs the sidecar and
// config.json every 2.5 s and answers their mtimes; the harness's fetch stub has no such files and answered 404, which
// the poll read as a move on every tick and re-asked status, whose apply re-wraps every mark and highlight. A re-wrap
// under a live selection collapses it, so the float's click opened nothing and the box still showed the previous
// composer's words; one landing between the test's setting of the post-save status and its click on Save handed the
// panel the saved comment BEFORE the write, so the reply named no fresh card to focus and the deletion's card was laid
// under the change's card sharing its mark (the review of this slice, 2026-09-10: red in about half the runs on a loaded
// box, at shifting assertions in both engines). The shim answers the two HEADs with the mtimes of the status the poster
// last answered with, as the kernel would (a sidecar's mtime moves only when something writes it, and in this leg the
// one writer is the person's Save), and swaps the post-save status in at the comment write itself, never before it.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as path from "node:path";
import { createRequire } from "node:module";
import { pageHtml, frames, openPanel, putAtTop, PARA, REPORT, SID, MT, ORIGIN, EXT, STATUS as BASE_STATUS } from "./real-viewer-leg";

const requireCjs = createRequire(path.join(EXT, "package.json"));
let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

// ── the document: sixty paragraphs; an insertion at the end of the thirtieth, a deletion in the thirty-first, a
// substitution in the thirty-second; a legacy comment the session's track-edit --thread bound to the insertion ──
const T0 = 1757145600000;
const INS = ", and the session added a warm-up step for the cache before the first request lands";
const P30 = PARA(30).slice(0, -1) + INS + ".";
const DEL_AFTER = "Paragraph 31: lorem ipsum ";
const OLD = "for a while ";
const NEW32 = "the warm cache";
const P32 = PARA(32).replace("dolor", NEW32);
const SRC = "# Report\n\n" + Array.from({ length: 60 }, (_, i) => (i + 1 === 30 ? P30 : i + 1 === 32 ? P32 : PARA(i + 1))).join("\n\n") + "\n";
const INS_AT = SRC.indexOf(INS);
const DEL_AT = SRC.indexOf(DEL_AFTER) + DEL_AFTER.length;
const SUB_AT = SRC.indexOf(NEW32);
const HUNK = { id: "h1", author: "api", ts: T0 - 30000, kind: "ins", curFrom: INS_AT, curTo: INS_AT + INS.length, baseFrom: INS_AT, baseTo: INS_AT, oldText: "", newText: INS, anchor: null };
const DEL = { id: "h2", author: "api", ts: T0 - 20000, kind: "del", curFrom: DEL_AT, curTo: DEL_AT, baseFrom: DEL_AT, baseTo: DEL_AT + OLD.length, oldText: OLD, newText: "", anchor: null };
const SUB = { id: "h3", author: "api", ts: T0 - 10000, kind: "sub", curFrom: SUB_AT, curTo: SUB_AT + NEW32.length, baseFrom: SUB_AT, baseTo: SUB_AT + "dolor".length, oldText: "dolor", newText: NEW32, anchor: null };
const SUGG = [{ id: "h1", authorId: SID }, { id: "h2", authorId: SID }, { id: "h3", authorId: SID }];
const C0_ID = (T0 - 5000) + "-" + INS_AT;
/** The legacy shape: the person's Reply on the insertion's card, bound by the format's own field. */
const C0 = { id: C0_ID, author: "you", ts: T0 - 5000, body: "Say which cache.", suggestionId: "h1", replies: [{ author: "api", authorId: SID, ts: T0 - 4000, body: "The response cache; the sentence names it now." }], resolved: false };
const STATUS = { ...BASE_STATUS, hunks: [HUNK, DEL, SUB], store: { ...BASE_STATUS.store, suggestions: SUGG, comments: [C0] } };
const NOTE = "Warm the cache from the last run, not from scratch.";
type Comment = Record<string, unknown>;
/** The status after a save: the standing comments plus the saved one, as the host would write it. */
function withSaved(comments: Comment[], n: number): Record<string, unknown> {
  return { ...STATUS, store: { ...STATUS.store, comments: [C0, ...comments] }, storeMtimeNs: "17571456000000000" + (20 + n), unsent: { comments: comments.map((c) => c.id as string), replies: [], accepted: 0, rejected: 0, watermark: null } };
}
const anchorOf = (quote: string, from: number) => { const at = SRC.indexOf(quote, from); assert.ok(at >= 0, "the quote is in the source: " + quote); return { anchor: { quote, prefix: SRC.slice(Math.max(0, at - 24), at), suffix: SRC.slice(at + quote.length, at + quote.length + 24) }, anchorAt: at }; };

const INS_MARK = '.fileview-body [data-act="fcchange"][data-id="h1"]';
const SUB_MARK = '.fileview-body .fc-ins[data-act="fcchange"][data-id="h3"]';
const DEL_MARK = '.fileview-body span.fc-del[data-act="fcchange"][data-id="h2"]';

type Composer = { open: boolean; quote: string | null; opt: { checked: boolean; label: string } | null; ref: string[]; presel: string };
/** The composer as the page shows it. A closed box keeps the previous composer's reference row (renderComposer returns
 *  before rebuilding it), so its words are read only while the box is OPEN: a gesture that opened nothing reads a null
 *  quote and no option, never the previous composer's (the review, 2026-09-10: a failure here once reported the earlier
 *  drag's words as the wrong quote, when the box had not opened at all). */
const composer = (page: any): Promise<Composer> => page.evaluate(() => {
  const box = document.querySelector(".fileview-aside .fc-composer") as HTMLElement | null;
  const open = !!box && !box.hidden;
  const opt = open ? box!.querySelector('input[data-opt="about"]') as HTMLInputElement | null : null;
  return {
    open, quote: open ? (box!.querySelector(".fc-quote")?.textContent ?? null) : null,
    opt: opt ? { checked: opt.checked, label: (opt.parentElement as HTMLElement).textContent || "" } : null,
    ref: open ? Array.from(box!.querySelector(".fc-composer-ref")?.childNodes || []).map((n) => (n as HTMLElement).className + ":" + (n.textContent || "")) : [],
    presel: Array.from(document.querySelectorAll(".fileview-body .fc-presel")).map((m) => m.textContent || "").join(""),
  };
});
/** The words under a comment's highlight in the body, its pieces joined in document order: a highlight that crosses a
 *  mark's edge is painted in pieces, one inside the mark and one outside; "" while none is painted. */
const hlText = (page: any, cid: string): Promise<string> => page.evaluate((cid: string) => Array.from(document.querySelectorAll('.fileview-body [data-act="fcopen"][data-id="' + cid + '"]')).map((n) => n.textContent || "").join(""), cid);
const hlPainted = (page: any, cid: string): Promise<unknown> => page.waitForFunction((cid: string) => !!document.querySelector('.fileview-body [data-act="fcopen"][data-id="' + cid + '"]'), cid, { timeout: 10000 });
const posted = (page: any): Promise<any[]> => page.evaluate(() => (window as any).__posted);
const commentsPosted = async (page: any): Promise<any[]> => (await posted(page)).filter((x: any) => x.type === "fileComments" && x.verb === "comment");
/** A card's head tags, and whether it is open. */
const cardOf = (page: any, key: string): Promise<{ present: boolean; open: boolean; tags: string[]; ref: string | null; kindTitle: string | null }> => page.evaluate((key: string) => {
  const c = document.querySelector('.fileview-aside .fc-card[data-id="' + key + '"]');
  return { present: !!c, open: !!c && c.classList.contains("open"), tags: c ? Array.from(c.querySelectorAll(".fc-card-head .fc-tag")).map((t) => t.textContent || "") : [],
    ref: c ? (c.querySelector(".fc-ref")?.textContent ?? null) : null, kindTitle: c ? ((c.querySelector(".fc-kind") as HTMLElement | null)?.title ?? null) : null };
}, key);
/** The ids of the change marks ringed (.fc-lit), and the computed outline style of the first one. */
const litMarks = (page: any): Promise<{ ids: string[]; outline: string }> => page.evaluate(() => {
  const ms = Array.from(document.querySelectorAll(".fileview-body [data-act=\"fcchange\"].fc-lit")) as HTMLElement[];
  const first = ms[0];
  const cs = first ? getComputedStyle(first, first.classList.contains("fc-del") ? "::before" : null) : null;
  return { ids: Array.from(new Set(ms.map((m) => m.dataset.id || ""))), outline: cs ? cs.outlineStyle + " " + cs.outlineWidth : "" };
});
const filterOn = (page: any): Promise<string | null> => page.evaluate(() => (document.querySelector('.fileview-aside [data-act="fcfilter"][data-on="1"]') as HTMLElement | null)?.dataset.key ?? null);

/** The harness's stub armed against the panel's poll, before the file opens (the header says why). Two things, both as
 *  the kernel behaves: a HEAD of the sidecar or of config.json is answered 200 with the mtime the status the poster LAST
 *  answered with carries (`window.__answered`, taken at each post from the harness's own `__status`, the value that reply
 *  is built from), so the poll's baseline and its reading agree until a write moves them together; and the status a
 *  comment write is answered with (`window.__next`, saveAs queues it) becomes `__status` at the moment the write is
 *  POSTED, never earlier, since a sidecar changes at the write and no status asked before Save can carry the saved
 *  comment. Every other fetch, the file's own HEAD among them, falls through to the harness. The poster's record is the
 *  seam: `window.__posted.push` is the first thing it does with a post, and it reads `__status` after it. */
const armHarness = (page: any): Promise<void> => page.evaluate(() => {
  const w = window as any;
  w.__next = null;
  w.__answered = w.__status;
  const rec = w.__posted as any[];
  rec.push = function (m: any) {
    if (m && m.type === "fileComments" && m.verb === "comment" && w.__next) { w.__status = w.__next; w.__next = null; }
    if (m && m.type === "fileComments") w.__answered = w.__status;
    return Array.prototype.push.call(this, m);
  };
  const through = w.fetch;
  w.fetch = async function (url: unknown, init?: { method?: string }) {
    if (init && init.method === "HEAD") {
      const m = /[?&]path=([^&]*)/.exec(String(url)); const p = m ? decodeURIComponent(m[1]) : "";
      const a = w.__answered;
      if (a && p === a.storePath) return new Response(null, { status: 200, headers: { "X-Romp-Mtime-Ns": a.storeMtimeNs } });
      if (a && a.root && p === a.root.replace(/\/$/, "") + "/.trackchanges/config.json") return new Response(null, { status: 200, headers: { "X-Romp-Mtime-Ns": a.configMtimeNs } });
    }
    return through.apply(this, arguments as any);
  };
});
/** What a HEAD of `p` through the page's fetch answers: the status and the mtime header, as the poll reads them. */
const headOf = (page: any, p: string): Promise<string> => page.evaluate(([p, sid]: [string, string]) => fetch("/file?path=" + encodeURIComponent(p) + "&sid=" + encodeURIComponent(sid), { method: "HEAD", cache: "no-store" }).then((r) => r.status + " " + r.headers.get("X-Romp-Mtime-Ns")), [p, SID]);
async function openWith(browser: any, raw: boolean): Promise<{ page: any; errors: string[] }> {
  const page = await browser.newPage({ viewport: { width: 1000, height: 600 } });
  const errors: string[] = [];
  page.on("pageerror", (e: Error) => { errors.push(e.message); });
  const html = pageHtml("pane", { [REPORT]: SRC }, MT);
  await page.route((u: URL) => u.href.startsWith(ORIGIN), (route: any) => route.fulfill({ status: 200, contentType: "text/html", body: html }));
  await page.goto(ORIGIN + "/");
  await armHarness(page);
  if (raw) await page.evaluate(() => { localStorage.setItem("romp:fileviewFmt", JSON.stringify({ md: "raw" })); });
  await page.evaluate(([p, sid, st]: [string, string, unknown]) => { (window as any).__status = st; (window as any).FV.openFileView(p, sid, null); }, [REPORT, SID, STATUS]);
  await page.waitForFunction((raw: boolean) => !!document.querySelector(raw ? ".fileview-body .fv-cl" : ".fileview-md > p"), raw, { timeout: 10000 });
  await frames(page, 2);
  await openPanel(page);
  await page.waitForFunction((sels: string[]) => sels.every((s) => !!document.querySelector(s)), [INS_MARK, SUB_MARK, DEL_MARK], { timeout: 10000 });
  await frames(page, 2);
  return { page, errors };
}
/** Paragraph 29 to the body's top edge, so the marks in paragraphs 30 to 32 stand in view, clear of the top edge where a
 *  selection drag autoscrolls. */
async function offCentre(page: any): Promise<void> {
  await page.evaluate(() => { getSelection()!.removeAllRanges(); });
  await putAtTop(page, "Paragraph 29:");
  await frames(page, 2);
}
type Line = { x1: number; x2: number; y: number; text: string };
/** A range over `from`..`to` of the first text node of `to` characters or more directly inside the element `sel` names. */
const lineIn = (page: any, sel: string, from: number, to: number): Promise<Line> => page.evaluate(([sel, from, to]: [string, number, number]) => {
  const marks = Array.from(document.querySelectorAll(sel)) as HTMLElement[];
  const texts = marks.flatMap((m) => Array.from(m.childNodes).filter((n) => n.nodeType === 3 && (n.textContent || "").length >= to) as Text[]);
  const t = texts[0];
  if (!t) throw new Error("no text node of " + to + " characters directly inside " + sel + ": " + marks.map((m) => m.outerHTML).join(" | "));
  const r = document.createRange(); r.setStart(t, from); r.setEnd(t, to);
  const b = r.getBoundingClientRect();
  return { x1: b.left + 1, x2: b.right - 1, y: b.top + b.height / 2, text: t.data.slice(from, to) };
}, [sel, from, to]);
/** A range spanning the END of the element `sel` names: from `back` characters before the end of the last text node directly
 *  inside it to the end of the first character of the text that follows it (the "." closing paragraph 30 after the
 *  insertion's mark: `next` says which character is expected). One line, checked: no break opportunity stands before
 *  a period, so a range that wraps is a fixture error, said loudly. */
const lineAcross = (page: any, sel: string, back: number, next: string): Promise<Line> => page.evaluate(([sel, back, next]: [string, number, string]) => {
  const marks = Array.from(document.querySelectorAll(sel)) as HTMLElement[];
  const m = marks[marks.length - 1];
  if (!m) throw new Error("no element matches " + sel);
  const inside = Array.from(m.childNodes).filter((n) => n.nodeType === 3 && (n.textContent || "").length >= back) as Text[];
  const t = inside[inside.length - 1];
  if (!t) throw new Error("no text node of " + back + " characters directly inside " + sel + ": " + m.outerHTML);
  const w = document.createTreeWalker(document.querySelector(".fileview-body")!, NodeFilter.SHOW_TEXT);
  w.currentNode = m;
  let after: Text | null = null;
  while ((after = w.nextNode() as Text | null)) if (!m.contains(after) && after.data.length) break;
  if (!after) throw new Error("no text follows " + sel);
  if (after.data.slice(0, next.length) !== next) throw new Error("the text after " + sel + " starts " + JSON.stringify(after.data.slice(0, 12)) + ", not " + JSON.stringify(next));
  const r = document.createRange(); r.setStart(t, t.data.length - back); r.setEnd(after, next.length);
  const rects = Array.from(r.getClientRects());
  if (rects.some((x) => Math.abs(x.top - rects[0].top) > 1)) throw new Error("the range across the mark's end wraps: " + rects.map((x) => x.left + "," + x.top + " " + x.width + "x" + x.height).join(" | "));
  const b = r.getBoundingClientRect();
  return { x1: b.left + 1, x2: b.right - 1, y: b.top + b.height / 2, text: r.toString() };
}, [sel, back, next]);
/** With the marks hidden the insertion's words are plain text of paragraph 30: a range over the words of INS inside that block. */
const lineInBlock = (page: any, start: string, needle: string, len: number): Promise<Line> => page.evaluate(([start, needle, len]: [string, string, number]) => {
  const body = document.querySelector(".fileview-body")!;
  const blocks = document.querySelector(".fileview-md") ? ".fileview-md > *" : "code.hljs .fv-cl";
  const el = Array.from(body.querySelectorAll(blocks)).filter((e) => (e.textContent || "").indexOf(start) === 0)[0];
  if (!el) throw new Error("no block starting with " + JSON.stringify(start));
  const w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
  let t: Text | null = null;
  while ((t = w.nextNode() as Text | null)) if (t.data.indexOf(needle) >= 0) break;
  if (!t) throw new Error("no text node holding " + JSON.stringify(needle) + " in the block: " + el.outerHTML.slice(0, 200));
  const from = t.data.indexOf(needle);
  const r = document.createRange(); r.setStart(t, from); r.setEnd(t, from + len);
  const b = r.getBoundingClientRect();
  return { x1: b.left + 1, x2: b.right - 1, y: b.top + b.height / 2, text: t.data.slice(from, from + len) };
}, [start, needle, len]);
/** A selection over `needle` in the block that starts with `start`, made as a range and settled with a mouseup on the body. */
const selectWords = (page: any, start: string, needle: string): Promise<void> => page.evaluate(([start, needle]: [string, string]) => {
  const body = document.querySelector(".fileview-body")!;
  const blocks = document.querySelector(".fileview-md") ? ".fileview-md > *" : "code.hljs .fv-cl";
  const el = Array.from(body.querySelectorAll(blocks)).filter((e) => (e.textContent || "").indexOf(start) === 0)[0];
  if (!el) throw new Error("no block starting with " + JSON.stringify(start));
  const w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
  let t: Text | null = null;
  while ((t = w.nextNode() as Text | null)) if (t.data.indexOf(needle) >= 0) break;
  if (!t) throw new Error("no text node holding " + JSON.stringify(needle) + " in the block: " + el.outerHTML.slice(0, 200));
  const from = t.data.indexOf(needle);
  const r = document.createRange(); r.setStart(t, from); r.setEnd(t, from + needle.length);
  const s = getSelection()!; s.removeAllRanges(); s.addRange(r);
  const b = r.getBoundingClientRect();
  body.dispatchEvent(new MouseEvent("mouseup", { bubbles: true, clientX: b.left + 2, clientY: b.top + b.height / 2 }));
}, [start, needle]).then(() => frames(page, 2));
async function drag(page: any, l: Line): Promise<void> {
  await page.mouse.move(l.x1, l.y);
  await page.mouse.down();
  await page.mouse.move(l.x2, l.y, { steps: 4 });
  await page.mouse.up();
  await frames(page, 3);
}
/** Save the composer's words: the reply the harness posts is `status`, so the saved comment paints; the card is awaited,
 *  and its highlight in the text when the comment has a passage (`anchored`; a comment about a deletion alone has none).
 *  The post-save status is QUEUED (`__next`), not set: the armed poster swaps it in at the write (armHarness). */
async function saveAs(page: any, status: Record<string, unknown>, cid: string, anchored = true): Promise<void> {
  await page.focus(".fileview-aside .fc-input");        // a click on the option took the keyboard from the box
  await page.keyboard.type(NOTE);
  await page.evaluate((st: unknown) => { (window as any).__next = st; }, status);
  await page.click('.fileview-aside [data-act="fcsave"]');
  await page.waitForFunction((cid: string) => !!document.querySelector('.fileview-aside .fc-card[data-id="' + cid + '"]'), cid, { timeout: 10000 });
  if (anchored) await hlPainted(page, cid);
  await frames(page, 3);
}
/** Click the viewer's Rendered/Raw toggle to `to`, and wait for that view's body, the three marks painted in it and, for
 *  each id in `hls`, the comment's highlight: the saved comments paint in the other view too (the contract, section 3). */
async function switchView(page: any, to: "rendered" | "raw", hls: string[]): Promise<void> {
  await page.click('.fileview-acts .fileview-btn:text-is("' + (to === "raw" ? "Raw" : "Rendered") + '")');
  await page.waitForFunction((raw: boolean) => !!document.querySelector(raw ? ".fileview-body .fv-cl" : ".fileview-md > p"), to === "raw", { timeout: 10000 });
  await page.waitForFunction((sels: string[]) => sels.every((s) => !!document.querySelector(s)), [INS_MARK, SUB_MARK, DEL_MARK], { timeout: 10000 });
  for (const cid of hls) await hlPainted(page, cid);
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
  test(`in ${name}, the real viewer, Rendered (marks shown and hidden) and Raw: Comment on this change anchors over the change's span with the option checked; a drag inside an insertion and inside a substitution's new text is a passage comment with the option, unchecked a plain one; a drag across the insertion's end is a passage comment over the whole selection with the option, its highlight and the one inside the mark painting in the other view too; a selection over a deletion's label alone is a comment about the change by id, laid at the mark; the tags, the ring under the pointer, the count tag's click; the legacy answered tag`, { timeout: 300000 }, async (t) => {
    await inEngine(t, name, async (browser) => {
      for (const raw of [false, true]) {
        const cell = name + (raw ? " Raw" : " Rendered");
        const { page, errors } = await openWith(browser, raw);
        const saved: Comment[] = [];
        let n = 0;
        let insideId = "", insideQuote = "";          // the comment saved inside the insertion's mark, read again in the other view
        // the armed stub answers the sidecar's HEAD as the kernel would: its mtime as the last status read it, so the poll
        // sees no move (armHarness); the file's own HEAD still comes from the harness
        assert.equal(await headOf(page, STATUS.storePath), "200 " + STATUS.storeMtimeNs, cell + ": the sidecar's HEAD answers the status's mtime");
        assert.equal(await headOf(page, REPORT), "200 " + MT, cell + ": the file's HEAD is the harness's own");
        // ── the legacy comment: its own card, the answered tag; the change card's count ──
        let c0 = await cardOf(page, C0_ID);
        assert.equal(c0.present, true, cell + ": the legacy comment has its own card (before: drawn inside the change card)");
        assert.deepEqual(c0.tags, ["answered by a change", "1"], cell + ": the answered tag, and the turn count while collapsed");
        assert.equal(c0.ref, "added " + INS.slice(0, 59) + "…", cell + ": no passage: the change's words as its reference");
        assert.equal(c0.kindTitle, "A comment the session answered with a change", cell + ": the legacy binding's title says the session answered, not that the person named the change");
        let h1 = await cardOf(page, "chg:h1");
        assert.deepEqual(h1.tags, ["1 comment"], cell + ": the change card counts the comment naming it");
        assert.equal(await page.evaluate(() => document.querySelectorAll(".fileview-aside .fc-hosted").length), 0, cell + ": no comment inside a change card");
        assert.deepEqual(await page.evaluate(() => Array.from(document.querySelectorAll('.fileview-aside .fc-card[data-id="chg:h1"] .fc-actions button')).map((b) => b.textContent)), ["Accept", "Reject", "Comment on this change"], cell + ": Reply became Comment on this change");
        // ── the pointer over the answered tag rings the insertion's marks; leaving unrings them ──
        await offCentre(page);
        await page.hover('.fileview-aside .fc-card[data-id="' + C0_ID + '"] .fc-tag.fc-about');
        await frames(page, 2);
        let lit = await litMarks(page);
        assert.deepEqual(lit.ids, ["h1"], cell + ": the tag lights the change's marks");
        assert.match(lit.outline, /^solid 2px$/, cell + ": a real ring: " + lit.outline);
        await page.hover(".fileview-aside .fc-head");
        await frames(page, 2);
        assert.deepEqual((await litMarks(page)).ids, [], cell + ": the ring goes when the pointer leaves");
        // ── Comment on this change on the substitution: the composer over its new text, the option checked, the presel ──
        await page.click('.fileview-aside .fc-card[data-id="chg:h3"] [data-act="fcchangecomment"]');
        await frames(page, 2);
        let c = await composer(page);
        assert.equal(c.open, true, cell + ": the composer opened");
        assert.equal(c.quote, NEW32, cell + ": anchored over the change's new text");
        assert.equal(c.presel, NEW32, cell + ": the presel is painted over the span");
        assert.deepEqual(c.opt, { checked: true, label: "about this change" }, cell + ": the option, checked");
        assert.equal(await page.evaluate(() => !!document.querySelector('.fileview-aside .fc-card .fc-composer')), false, cell + ": the box stands in the slot, not in a card");
        let cid = (T0 + 100 + n) + "-" + SUB_AT;
        saved.push({ id: cid, author: "you", ts: T0 + 100 + n, ...anchorOf(NEW32, SUB_AT), changeIds: ["h3"], body: NOTE, replies: [], resolved: false });
        await saveAs(page, withSaved(saved, ++n), cid);
        let ms = await commentsPosted(page);
        assert.equal(ms.length, n, cell + ": one comment write per save");
        assert.deepEqual(ms[n - 1].args.changeIds, ["h3"], cell + ": the change's id rides the request");
        assert.equal(ms[n - 1].args.anchor.quote, NEW32, cell + ": with the passage anchor");
        assert.equal("suggestionId" in ms[n - 1].args, false, cell + ": never suggestionId");
        assert.deepEqual((await cardOf(page, cid)).tags, ["about a change"], cell + ": the saved comment's own card wears the about tag");
        assert.deepEqual((await cardOf(page, "chg:h3")).tags, ["1 comment"], cell + ": …and the change card counts it");
        assert.equal(await headOf(page, STATUS.storePath), "200 " + withSaved(saved, n).storeMtimeNs, cell + ": the sidecar's mtime moved with the write, as the poll's baseline did (armHarness)");
        // ── a drag inside the insertion's mark: a passage comment with the option checked; saved with the change's id ──
        await offCentre(page);
        let l = await lineIn(page, INS_MARK, 2, 14);
        await drag(page, l);
        assert.equal((await cardOf(page, "chg:h1")).open, false, cell + ": the drag opened no card (the mark-click guard)");
        await page.click(".fc-float");
        await frames(page, 2);
        c = await composer(page);
        assert.equal(c.open, true, cell + ": the composer opened on the drag inside the mark");
        assert.equal(c.quote, l.text, cell + ": the passage comment on the selected words");
        assert.deepEqual(c.opt, { checked: true, label: "about this change" }, cell + ": the option for the change the words lie in");
        cid = (T0 + 100 + n) + "-" + SRC.indexOf(l.text, INS_AT);
        saved.push({ id: cid, author: "you", ts: T0 + 100 + n, ...anchorOf(l.text, INS_AT), changeIds: ["h1"], body: NOTE, replies: [], resolved: false });
        await saveAs(page, withSaved(saved, ++n), cid);
        insideId = cid; insideQuote = l.text;
        ms = await commentsPosted(page);
        assert.equal(ms.length, n, cell + ": the drag's save posted one comment write");
        assert.deepEqual(ms[n - 1].args.changeIds, ["h1"], cell);
        assert.equal(ms[n - 1].args.anchor.quote, l.text, cell + ": an ordinary passage comment, anchored in the new text");
        assert.equal(await hlText(page, cid), l.text, cell + ": its highlight is painted inside the mark");
        assert.deepEqual((await cardOf(page, "chg:h1")).tags, ["2 comments"], cell + ": the legacy one and this one");
        // ── the same drag, the option unchecked: a plain passage comment, no changeIds ──
        await offCentre(page);
        l = await lineIn(page, INS_MARK, 20, 31);
        await drag(page, l);
        await page.click(".fc-float");
        await frames(page, 2);
        c = await composer(page);
        assert.equal(c.open, true, cell + ": the composer opened on the second drag inside the mark");
        assert.equal(c.quote, l.text, cell);
        await page.click('.fileview-aside input[data-opt="about"]');
        await frames(page, 1);
        assert.equal((await composer(page)).opt!.checked, false, cell + ": unchecked");
        cid = (T0 + 100 + n) + "-" + SRC.indexOf(l.text, INS_AT);
        saved.push({ id: cid, author: "you", ts: T0 + 100 + n, ...anchorOf(l.text, INS_AT), body: NOTE, replies: [], resolved: false });
        await saveAs(page, withSaved(saved, ++n), cid);
        ms = await commentsPosted(page);
        assert.equal(ms.length, n, cell + ": the unchecked save posted one comment write");
        assert.equal("changeIds" in ms[n - 1].args, false, cell + ": unchecked, no changeIds: a passage comment like any other");
        assert.deepEqual((await cardOf(page, cid)).tags, [], cell + ": no about tag on it");
        assert.deepEqual((await cardOf(page, "chg:h1")).tags, ["2 comments"], cell + ": not counted on the change");
        // ── a drag inside the substitution's new text: the same rule ──
        await offCentre(page);
        l = await lineIn(page, SUB_MARK, 4, 14);
        await drag(page, l);
        await page.click(".fc-float");
        await frames(page, 2);
        c = await composer(page);
        assert.equal(c.open, true, cell + ": the composer opened on the drag inside the substitution's new text");
        assert.equal(c.quote, l.text, cell + ": inside a substitution's new text: a passage comment");
        assert.deepEqual(c.opt, { checked: true, label: "about this change" }, cell);
        await page.click('.fileview-aside [data-act="fccancel"]');
        await frames(page, 1);
        // ── a drag from inside the insertion's last word across the mark's end into the "." after it (the contract's "spanning
        // a boundary"): the passage is the whole selection, the option names the change the words partly lie in, and the
        // saved highlight is painted on both sides of the mark's edge ──
        await offCentre(page);
        l = await lineAcross(page, INS_MARK, 5, ".");
        assert.equal(l.text, INS.slice(-5) + ".", cell + ": the range runs across the mark's end: " + JSON.stringify(l.text));
        await drag(page, l);
        assert.equal((await cardOf(page, "chg:h1")).open, false, cell + ": the drag across the edge opened no card");
        await page.click(".fc-float");
        await frames(page, 2);
        c = await composer(page);
        assert.equal(c.open, true, cell + ": the composer opened on the selection across the mark's end");
        assert.equal(c.quote, l.text, cell + ": the passage is the whole selection, the character outside the mark included");
        assert.deepEqual(c.opt, { checked: true, label: "about this change" }, cell + ": the option names the change the selection partly lies in");
        cid = (T0 + 100 + n) + "-" + SRC.indexOf(l.text, INS_AT);
        saved.push({ id: cid, author: "you", ts: T0 + 100 + n, ...anchorOf(l.text, INS_AT), changeIds: ["h1"], body: NOTE, replies: [], resolved: false });
        await saveAs(page, withSaved(saved, ++n), cid);
        ms = await commentsPosted(page);
        assert.equal(ms.length, n, cell + ": the save across the edge posted one comment write");
        assert.deepEqual(ms[n - 1].args.changeIds, ["h1"], cell);
        assert.equal(ms[n - 1].args.anchor.quote, l.text, cell + ": anchored in the current text, across the mark's end");
        assert.equal(await hlText(page, cid), l.text, cell + ": its highlight is painted on both sides of the mark's edge");
        assert.deepEqual((await cardOf(page, cid)).tags, ["about a change"], cell);
        assert.deepEqual((await cardOf(page, "chg:h1")).tags, ["3 comments"], cell + ": counted on the change");
        // ── the other view (the contract's "paints in the other view"): the toggle clicked, the comment inside the mark and
        // the one across its edge paint over the same words there, and again once the view is switched back ──
        const acrossId = cid;
        await switchView(page, raw ? "rendered" : "raw", [insideId, acrossId]);
        assert.equal(await hlText(page, insideId), insideQuote, cell + " -> the other view: the comment inside the mark paints over its words");
        assert.equal(await hlText(page, acrossId), l.text, cell + " -> the other view: the comment across the mark's edge paints over its words");
        assert.deepEqual((await cardOf(page, "chg:h1")).tags, ["3 comments"], cell + " -> the other view: the change card stands as it was");
        await switchView(page, raw ? "raw" : "rendered", [insideId, acrossId]);
        assert.equal(await hlText(page, acrossId), l.text, cell + ": ...and in this view again once switched back");
        if (!raw) {
          // ── Rendered with the marks hidden: the same words are plain text; the option still names the change ──
          await page.click('.fileview-aside [data-act="fcinline"]');
          await frames(page, 3);
          assert.equal(await page.evaluate(() => document.querySelectorAll('.fileview-body [data-act="fcchange"]').length), 0, cell + ": the marks are off");
          await offCentre(page);
          // the words are plain text of a wrapped paragraph now, so the selection is made as a range over them and settled
          // with a real mouseup on the body, as a drag settles (a drag along one line could span the wrap)
          await selectWords(page, "Paragraph 30:", "before the first");
          await page.click(".fc-float");
          await frames(page, 2);
          c = await composer(page);
          assert.equal(c.open, true, cell + " marks off: the composer opened on the selection");
          assert.equal(c.quote, "before the first", cell + " marks off: the passage comment");
          assert.deepEqual(c.opt, { checked: true, label: "about this change" }, cell + " marks off: the option still names the change the words lie in");
          await page.click('.fileview-aside [data-act="fccancel"]');
          await page.click('.fileview-aside [data-act="fcinline"]');
          await frames(page, 3);
          await page.waitForFunction((s: string) => !!document.querySelector(s), DEL_MARK, { timeout: 10000 });
        }
        // ── the deletion's struck label alone: a range over the point, no text of the file; the comment about the change by id ──
        await offCentre(page);
        await page.evaluate((sel: string) => {
          const m = document.querySelector(sel)!;
          const r = document.createRange(); r.selectNode(m);
          const s = getSelection()!; s.removeAllRanges(); s.addRange(r);
          const body = document.querySelector(".fileview-body")!;
          const b = m.getBoundingClientRect();
          body.dispatchEvent(new MouseEvent("mouseup", { bubbles: true, clientX: b.left + b.width / 2, clientY: b.top + b.height / 2 }));
        }, DEL_MARK);
        await frames(page, 2);
        assert.equal(await page.evaluate(() => (document.querySelector(".fc-float") as HTMLElement).hidden), false, cell + ": the float is offered over the label");
        await page.click(".fc-float");
        await frames(page, 2);
        c = await composer(page);
        assert.equal(c.open, true, cell + ": the composer opened on the label");
        assert.equal(c.opt, null, cell + ": no option: the comment can only be about the change");
        assert.deepEqual(c.ref, ["fc-note:About the change ", "fc-quote:removed for a while", "fc-note:The removed text is not in the file, so the comment is laid at the change's point."], cell);
        cid = (T0 + 100 + n) + "-" + DEL_AT;
        saved.push({ id: cid, author: "you", ts: T0 + 100 + n, changeIds: ["h2"], body: NOTE, replies: [], resolved: false });
        await saveAs(page, withSaved(saved, ++n), cid, false);   // no passage, so no highlight to await
        ms = await commentsPosted(page);
        assert.equal(ms.length, n, cell + ": the label's save posted one comment write");
        assert.deepEqual(ms[n - 1].args, { note: NOTE, changeIds: ["h2"] }, cell + ": the change alone, no anchor");
        await frames(page, 4);                           // the pass after the composer's close re-lays the cards; a slower engine needs the frames
        const laid = await page.evaluate(([cid, sel]: [string, string]) => {
          const card = document.querySelector('.fileview-aside .fc-card[data-id="' + cid + '"]') as HTMLElement;
          const mark = document.querySelector(sel) as HTMLElement;
          const mr = mark.getBoundingClientRect();
          return { card: card.getBoundingClientRect().top, mark: mr.top, markBox: mr.width + "x" + mr.height, pushed: card.dataset.pushed || "", pulled: card.dataset.pulled || "", top: card.style.top,
            margin: !!document.querySelector(".fc-margin"), scroll: (document.querySelector(".fileview-body") as HTMLElement).scrollTop, track: (document.querySelector(".fileview-aside .fc-sec-cards") as HTMLElement).scrollTop };
        }, [cid, DEL_MARK]);
        assert.equal(laid.margin, true, cell + ": the margin layout is on at this width");
        assert.ok(Math.abs(laid.card - laid.mark) <= 3, cell + ": the card is laid level with the deletion's mark " + JSON.stringify(laid));
        assert.deepEqual((await cardOf(page, cid)).tags, ["about a change"], cell);
        assert.deepEqual((await cardOf(page, "chg:h2")).tags, ["1 comment"], cell);
        // ── the count tag under Changes: All chosen, the first comment about the change open and in view ──
        await page.click('.fileview-aside [data-act="fcfilter"][data-key="changes"]');
        await frames(page, 2);
        assert.equal(await page.evaluate(() => document.querySelectorAll('.fileview-aside .fc-card:not(.fc-change)').length), 0, cell + ": Changes hides the comment cards");
        await page.click('.fileview-aside .fc-card[data-id="chg:h1"] [data-act="fcaboutfirst"]');
        await frames(page, 3);
        assert.equal(await filterOn(page), "all", cell + ": the count's click chooses All");
        c0 = await cardOf(page, C0_ID);
        assert.equal(c0.open, true, cell + ": the first comment about the insertion (the legacy one, oldest) is open");
        const inView = await page.evaluate((key: string) => { const c = document.querySelector('.fileview-aside .fc-card[data-id="' + key + '"]')!.getBoundingClientRect(); const t = document.querySelector(".fileview-aside .fc-sec-cards")!.getBoundingClientRect(); return c.top >= t.top - 1 && c.bottom <= t.bottom + 1; }, C0_ID);
        assert.equal(inView, true, cell + ": …and in the track's box");
        assert.deepEqual(errors, [], cell + ": no script error in the page");
        await page.close();
      }
    });
  });
}

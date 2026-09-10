// The about follow-on over the REAL viewer and the REAL panel, in Chromium and Firefox (plans/file-review.md, "The about
// follow-on (2026-09-10)" under Slice 2; decision 45; section 3's rule under decision 44's neighbour). What a stand-in
// cannot show is measured here: the composer opened by Comment on this change anchored over the change's real span, with
// its presel painted and the about option checked; a real drag inside an insertion's mark and inside a substitution's new
// text opening the passage composer with the option checked, in Rendered with the marks shown and hidden and in Raw,
// the saved comment an ordinary passage comment carrying changeIds and painting as its own card and highlight; the
// option unchecked saving no changeIds; a selection over a deletion's struck label alone (the label is generated text,
// so a range over the point holds no text of the file) offering the comment about that change by id, and the saved
// card laid level with the deletion's mark in the margin layout (the markTop fallback); the tags on both cards, the
// pointer over a comment's tag ringing the change's marks (a real computed outline), and the change card's count tag
// bringing the first comment about the change into view with All chosen; a legacy suggestionId comment wearing
// "answered by a change". Skips LOUDLY without a playwright browser (CI installs none), as the other browser legs do.
// Legs await frames, never a timer. Synthetic values only: an invented report, /repo/notes-api paths, the placeholder
// sid, the session name "api".
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
const composer = (page: any): Promise<Composer> => page.evaluate(() => {
  const box = document.querySelector(".fileview-aside .fc-composer") as HTMLElement | null;
  const opt = box ? box.querySelector('input[data-opt="about"]') as HTMLInputElement | null : null;
  return {
    open: !!box && !box.hidden, quote: box ? (box.querySelector(".fc-quote")?.textContent ?? null) : null,
    opt: opt ? { checked: opt.checked, label: (opt.parentElement as HTMLElement).textContent || "" } : null,
    ref: box ? Array.from(box.querySelector(".fc-composer-ref")?.childNodes || []).map((n) => (n as HTMLElement).className + ":" + (n.textContent || "")) : [],
    presel: Array.from(document.querySelectorAll(".fileview-body .fc-presel")).map((m) => m.textContent || "").join(""),
  };
});
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
/** Save the composer's words: the reply the harness posts is `status`, so the saved comment paints; the card is awaited. */
async function saveAs(page: any, status: Record<string, unknown>, cid: string): Promise<void> {
  await page.focus(".fileview-aside .fc-input");        // a click on the option took the keyboard from the box
  await page.keyboard.type(NOTE);
  await page.evaluate((st: unknown) => { (window as any).__status = st; }, status);
  await page.click('.fileview-aside [data-act="fcsave"]');
  await page.waitForFunction((cid: string) => !!document.querySelector('.fileview-aside .fc-card[data-id="' + cid + '"]'), cid, { timeout: 10000 });
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
  test(`in ${name}, the real viewer, Rendered (marks shown and hidden) and Raw: Comment on this change anchors over the change's span with the option checked; a drag inside an insertion and inside a substitution's new text is a passage comment with the option, unchecked a plain one; a selection over a deletion's label alone is a comment about the change by id, laid at the mark; the tags, the ring under the pointer, the count tag's click; the legacy answered tag`, { timeout: 300000 }, async (t) => {
    await inEngine(t, name, async (browser) => {
      for (const raw of [false, true]) {
        const cell = name + (raw ? " Raw" : " Rendered");
        const { page, errors } = await openWith(browser, raw);
        const saved: Comment[] = [];
        let n = 0;
        // ── the legacy comment: its own card, the answered tag; the change card's count ──
        let c0 = await cardOf(page, C0_ID);
        assert.equal(c0.present, true, cell + ": the legacy comment has its own card (before: drawn inside the change card)");
        assert.deepEqual(c0.tags, ["answered by a change", "1"], cell + ": the answered tag, and the turn count while collapsed");
        assert.equal(c0.ref, "added " + INS.slice(0, 59) + "…", cell + ": no passage: the change's words as its reference");
        assert.equal(c0.kindTitle, "A comment about a change", cell);
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
        // ── a drag inside the insertion's mark: a passage comment with the option checked; saved with the change's id ──
        await offCentre(page);
        let l = await lineIn(page, INS_MARK, 2, 14);
        await drag(page, l);
        assert.equal((await cardOf(page, "chg:h1")).open, false, cell + ": the drag opened no card (the mark-click guard)");
        await page.click(".fc-float");
        await frames(page, 2);
        c = await composer(page);
        assert.equal(c.quote, l.text, cell + ": the passage comment on the selected words");
        assert.deepEqual(c.opt, { checked: true, label: "about this change" }, cell + ": the option for the change the words lie in");
        cid = (T0 + 100 + n) + "-" + SRC.indexOf(l.text, INS_AT);
        saved.push({ id: cid, author: "you", ts: T0 + 100 + n, ...anchorOf(l.text, INS_AT), changeIds: ["h1"], body: NOTE, replies: [], resolved: false });
        await saveAs(page, withSaved(saved, ++n), cid);
        ms = await commentsPosted(page);
        assert.equal(ms.length, n, cell + ": the drag's save posted one comment write");
        assert.deepEqual(ms[n - 1].args.changeIds, ["h1"], cell);
        assert.equal(ms[n - 1].args.anchor.quote, l.text, cell + ": an ordinary passage comment, anchored in the new text");
        await page.waitForFunction((cid: string) => !!document.querySelector('.fileview-body [data-act="fcopen"][data-id="' + cid + '"]'), cid, { timeout: 10000 });
        assert.deepEqual((await cardOf(page, "chg:h1")).tags, ["2 comments"], cell + ": the legacy one and this one");
        // ── the same drag, the option unchecked: a plain passage comment, no changeIds ──
        await offCentre(page);
        l = await lineIn(page, INS_MARK, 20, 31);
        await drag(page, l);
        await page.click(".fc-float");
        await frames(page, 2);
        c = await composer(page);
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
        assert.equal(c.quote, l.text, cell + ": inside a substitution's new text: a passage comment");
        assert.deepEqual(c.opt, { checked: true, label: "about this change" }, cell);
        await page.click('.fileview-aside [data-act="fccancel"]');
        await frames(page, 1);
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
        await saveAs(page, withSaved(saved, ++n), cid);
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

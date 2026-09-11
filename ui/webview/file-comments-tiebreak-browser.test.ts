// The recurring-passage tie-break over the REAL viewer and the REAL panel, in Chromium and Firefox (plans/file-review.md,
// Commenting from either view, the anchors follow-on note and decision 51). The user's case, end to end: a report holds the
// same paragraph twice under different headings, a comment sits on the second copy, and a paragraph is then inserted
// above by a raw write the host never records (an editor save, a write outside the tracked path), longer than half the
// gap between the copies, so nearest-wins from the stale stored position picks the FIRST copy. The poll sees the file's
// mtime move, reloads the text and re-asks status; the host's reply carries the store as it stands (the position stale)
// and the tie-break's verdict (`placed`: the ordinal's copy, the count unchanged, confirmed). What a stand-in cannot show
// is measured here: after the refresh the highlight lands on the second copy, under the "Second pass" heading, as a plain
// mark (no dashed cue), with no "passage recurs" tag on the card, in Rendered and in Raw; and the control, the same raw
// write answered by a status with no verdict (an older host), paints the first copy as a guess with the tag, so the leg
// tells the two apart. Skips LOUDLY without a playwright browser (CI installs none), as the other browser legs do. Legs
// await frames and the page's own state, never a timer. Synthetic values only: an invented report, /repo/notes-api paths,
// the placeholder sid.
//
// The raw write is the harness's file table and mtime changing under the open panel (`window.__docs`, `window.__mtime`),
// with `window.__status` set to what the host would answer afterwards; the poll's HEAD of the file reads the new mtime,
// the reload fetches the new text, and the status ask is answered from the table. Nothing is posted through the host.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as path from "node:path";
import { createRequire } from "node:module";
import { pageHtml, frames, openPanel, REPORT, SID, MT, MT2, ORIGIN, EXT, STATUS as BASE_STATUS } from "./real-viewer-leg";

const requireCjs = createRequire(path.join(EXT, "package.json"));
let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

// ── the document: one paragraph over a thousand characters, twice, each under its own heading ──
const T0 = 1757145600000;
const PARA = ("The quick brown fox jumps over the lazy dog. ".repeat(12)
  + "Here is the marker phrase to comment on. "
  + "Pack my box with five dozen liquor jugs. ".repeat(12)).trim();
const MARKER = "the marker phrase";
const HEAD = "# Report\n\n";
const SRC = HEAD + "## First pass\n\n" + PARA + "\n\n## Second pass\n\n" + PARA + "\n";
const FIRST = SRC.indexOf(MARKER);
const SECOND = SRC.indexOf(MARKER, FIRST + 1);
assert.ok(FIRST > 0 && SECOND > FIRST && SRC.indexOf(MARKER, SECOND + 1) === -1, "the fixture holds the passage twice");
const GAP = SECOND - FIRST;
// the anchor the host stores at its cap for the second copy: 480 characters of context either side, the same for both copies
const CAP_ANCHOR = { quote: MARKER, prefix: SRC.slice(SECOND - 480, SECOND), suffix: SRC.slice(SECOND + MARKER.length, SECOND + MARKER.length + 480) };
assert.deepEqual(CAP_ANCHOR, { quote: MARKER, prefix: SRC.slice(FIRST - 480, FIRST), suffix: SRC.slice(FIRST + MARKER.length, FIRST + MARKER.length + 480) }, "the fixture: the copies tie at the cap");
const C_ID = T0 + "-" + SECOND;
/** The comment as the host wrote it on the second copy: the position, and the copy fields (2 of 2 under Second pass). */
const C = { id: C_ID, author: "you", ts: T0, body: "Say it once.", anchor: CAP_ANCHOR, anchorAt: SECOND, ordinal: 2, copies: 2, section: "Report > Second pass", replies: [], resolved: false };
const STATUS0 = { ...BASE_STATUS, store: { ...BASE_STATUS.store, comments: [C] } };
// the raw write: a paragraph above the first heading, longer than half the gap between the copies and shorter than the gap
const INSERTED = "The person added this paragraph in an editor, outside the tracked path. ".repeat(9).trim();
const SRC2 = HEAD + INSERTED + "\n\n" + SRC.slice(HEAD.length);
const SHIFT = SRC2.length - SRC.length;
assert.ok(SHIFT > GAP / 2 && SHIFT < GAP, "the fixture: nearest-wins from the stale position picks the first copy");
/** The status the host answers after the raw write: the store as it stands (the position stale), and the verdict. */
const STATUS1 = { ...STATUS0, storeMtimeNs: "1757145600000000012", placed: { [C_ID]: { at: SECOND + SHIFT, confirmed: true, by: "ordinal" } } };
/** The control: the same, answered by a host with no verdict to give. */
const STATUS1_OLD = { ...STATUS0, storeMtimeNs: "1757145600000000012" };
const RAW_ROW = (src: string, at: number): number => src.slice(0, at).split("\n").length - 1;

type Mark = { count: number; dashed: boolean; title: string; text: string; heading: string | null; row: number | null };
/** The comment's highlight as the page shows it: how many marks, whether any wears the dashed cue, the first one's title and
 *  words, and where it sits: in Rendered the text of the heading before its paragraph, in Raw its row (0-based line). */
const markOf = (page: any, cid: string): Promise<Mark> => page.evaluate((cid: string) => {
  const ms = Array.from(document.querySelectorAll('.fileview-body [data-act="fcopen"][data-id="' + cid + '"]')) as HTMLElement[];
  const m = ms[0];
  let heading: string | null = null; let row: number | null = null;
  if (m) {
    const p = m.closest(".fileview-md > *");
    if (p) { let h: Element | null = p.previousElementSibling; while (h && !/^H[1-6]$/.test(h.tagName)) h = h.previousElementSibling; heading = h ? (h.textContent || "").trim() : null; }
    const cl = m.closest(".fv-cl");
    if (cl && cl.parentElement) row = Array.from(cl.parentElement.children).indexOf(cl);
  }
  return { count: ms.length, dashed: ms.some((x) => x.classList.contains("fc-hl-context")), title: m ? m.title : "", text: ms.map((x) => x.textContent || "").join(""), heading, row };
}, cid);
/** The card's head tags and whether the open card carries a note. */
const cardOf = (page: any, cid: string): Promise<{ present: boolean; tags: string[]; note: string | null }> => page.evaluate((cid: string) => {
  const c = document.querySelector('.fileview-aside .fc-card[data-id="' + cid + '"]');
  return { present: !!c, tags: c ? Array.from(c.querySelectorAll(".fc-card-head .fc-tag")).map((t) => t.textContent || "") : [], note: c ? (c.querySelector(".fc-note")?.textContent ?? null) : null };
}, cid);
const statusAsks = (page: any): Promise<number> => page.evaluate(() => ((window as any).__posted as any[]).filter((x) => x.type === "fileComments" && x.verb === "status").length);

async function openWith(browser: any, raw: boolean): Promise<{ page: any; errors: string[] }> {
  const page = await browser.newPage({ viewport: { width: 1000, height: 700 } });
  const errors: string[] = [];
  page.on("pageerror", (e: Error) => { errors.push(e.message); });
  const html = pageHtml("pane", { [REPORT]: SRC }, MT);
  await page.route((u: URL) => u.href.startsWith(ORIGIN), (route: any) => route.fulfill({ status: 200, contentType: "text/html", body: html }));
  await page.goto(ORIGIN + "/");
  if (raw) await page.evaluate(() => { localStorage.setItem("romp:fileviewFmt", JSON.stringify({ md: "raw" })); });
  await page.evaluate(([p, sid, st]: [string, string, unknown]) => { (window as any).__status = st; (window as any).FV.openFileView(p, sid, null); }, [REPORT, SID, STATUS0]);
  await page.waitForFunction((raw: boolean) => !!document.querySelector(raw ? ".fileview-body .fv-cl" : ".fileview-md > p"), raw, { timeout: 10000 });
  await frames(page, 2);
  await openPanel(page);
  await page.waitForFunction((cid: string) => !!document.querySelector('.fileview-body [data-act="fcopen"][data-id="' + cid + '"]'), C_ID, { timeout: 10000 });
  await frames(page, 2);
  return { page, errors };
}
/** The raw write under the open panel, then the poll's reload and status refresh: the text with the inserted paragraph is
 *  awaited in the body, then a status ask issued after the write and its paint (the panel re-asks status once the file's
 *  HEAD moves, tick by tick; the answer is `status`). */
async function rawWriteAndRefresh(page: any, status: Record<string, unknown>): Promise<void> {
  const asked = await statusAsks(page);
  await page.evaluate(([src, mt, st, p]: [string, string, unknown, string]) => { const w = window as any; w.__docs[p] = src; w.__mtime = mt; w.__status = st; }, [SRC2, MT2, status, REPORT]);
  await page.waitForFunction((needle: string) => (document.querySelector(".fileview-body")?.textContent || "").includes(needle), INSERTED.slice(0, 40), { timeout: 15000 });
  await page.waitForFunction((n: number) => ((window as any).__posted as any[]).filter((x) => x.type === "fileComments" && x.verb === "status").length > n, asked, { timeout: 15000 });
  // the status answers on a timer of 0 and its apply repaints; two more frames settle the paint
  await page.waitForFunction((cid: string) => !!document.querySelector('.fileview-body [data-act="fcopen"][data-id="' + cid + '"]'), C_ID, { timeout: 10000 });
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
  test(`in ${name}, the real viewer, Rendered and Raw: a comment on the second of two copies, a paragraph inserted above by a raw write, the status refreshed with the host's verdict: the highlight lands on the second copy plainly, with no tag; the control without a verdict paints the first copy as a guess with the tag`, { timeout: 300000 }, async (t) => {
    await inEngine(t, name, async (browser) => {
      for (const raw of [false, true]) {
        const cell = name + (raw ? " Raw" : " Rendered");
        // ── the verdict: confirmed by the ordinal ──
        {
          const { page, errors } = await openWith(browser, raw);
          let m = await markOf(page, C_ID);
          assert.equal(m.count >= 1 && m.text === MARKER, true, cell + ": the comment paints on its passage: " + JSON.stringify(m));
          assert.equal(m.dashed, false, cell + ": the position names its copy: painted plainly");
          if (raw) assert.equal(m.row, RAW_ROW(SRC, SECOND), cell + ": the second copy's row"); else assert.equal(m.heading, "Second pass", cell + ": under the second heading");
          assert.deepEqual((await cardOf(page, C_ID)).tags, [], cell + ": no tag before the write");
          await rawWriteAndRefresh(page, STATUS1);
          m = await markOf(page, C_ID);
          assert.equal(m.count >= 1 && m.text === MARKER, true, cell + ": the highlight is painted after the refresh: " + JSON.stringify(m));
          if (raw) assert.equal(m.row, RAW_ROW(SRC2, SECOND + SHIFT), cell + ": the second copy, where the raw write moved it"); else assert.equal(m.heading, "Second pass", cell + ": the second copy, under its heading, not the nearest to the stale position");
          assert.equal(m.dashed, false, cell + ": no dashed cue: the host confirmed the copy");
          assert.equal(m.title, "Open the comment on this passage", cell + ": the plain title");
          const card = await cardOf(page, C_ID);
          assert.equal(card.present, true, cell);
          assert.deepEqual(card.tags, [], cell + ": no 'passage recurs' tag");
          await page.click('.fileview-aside .fc-card[data-id="' + C_ID + '"] .fc-card-head');
          await frames(page, 2);
          assert.equal((await cardOf(page, C_ID)).note, null, cell + ": no note on the open card");
          assert.deepEqual(errors, [], cell + ": no page errors");
          await page.close();
        }
        // ── the control: the same write, a status with no verdict ──
        {
          const { page, errors } = await openWith(browser, raw);
          await rawWriteAndRefresh(page, STATUS1_OLD);
          const m = await markOf(page, C_ID);
          assert.equal(m.count >= 1 && m.text === MARKER, true, cell + " (control): painted: " + JSON.stringify(m));
          if (raw) assert.equal(m.row, RAW_ROW(SRC2, FIRST + SHIFT), cell + " (control): the first copy, nearest the stale position"); else assert.equal(m.heading, "First pass", cell + " (control): the first copy, nearest the stale position");
          assert.equal(m.dashed, true, cell + " (control): a guess wears the dashed cue");
          assert.match(m.title, /not a confirmed one$/, cell + " (control): the unsure title");
          const card = await cardOf(page, C_ID);
          assert.deepEqual(card.tags, ["passage recurs"], cell + " (control): the tag");
          assert.deepEqual(errors, [], cell + " (control): no page errors");
          await page.close();
        }
      }
    });
  });
}

// Refused comments waiting in notes under the open composer (file-comments.ts heldRows), measured in a real engine: the parts
// of one note stand 6 px apart and two notes 12 px apart, on a fine pointer and on a coarse one, in the pane (styles.css) and
// the feed (feed.css). Before, the notes stacked with nothing between them: a note's buttons sat flush against the next
// note's label while the parts of one note were 6 px apart, and on a coarse pointer the reason's line, a sibling of its note,
// sat flush against both its own note and the next one, so the parts of two notes grouped more tightly than the parts of
// one. The line now stands inside its note on a line of its own (.fc-held-why), and each note has 6 px above and below it
// (.fc-held-save), byte-equal in both sheets. The DOM stand-in tests cannot measure this: file-comments-save-held-composer
// .test.ts holds the line's parent and the reasons. The real viewer and the real panel (real-viewer-leg.ts), a comment's
// write held at the poster and refused when the test says, so two refusals land under a composer holding typed words.
// Synthetic values only: the notes-api report, the placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { pageHtml, frames, openPanel, inBrowser, PARA, REPORT, SID, MT, ORIGIN, STATUS as BASE } from "./real-viewer-leg";

const T0 = 1757145600000;
const SRC = "# Report\n\n" + Array.from({ length: 8 }, (_, i) => PARA(i + 1)).join("\n\n") + "\n";
const WHOLE = { id: T0 + "-119", author: "you", ts: T0 + 4000, body: "Lead with the numbers.", replies: [], resolved: false };
const STATUS = { ...BASE, store: { ...BASE.store, comments: [WHOLE] }, unsent: { ...BASE.unsent, comments: [WHOLE.id] } };
const REFUSAL = "The comments file could not be written; nothing was saved.";

/** The page's poster holds every comment write (window.__held) while `window.__hold` is on and answers everything else. */
const arm = (page: any): Promise<void> => page.evaluate(() => {
  const w = window as any;
  w.__held = []; w.__hold = false;
  const rec = w.__posted as any[];
  rec.push = function (m: any) {
    const write = !!m && m.type === "fileComments" && (m.verb === "comment" || m.verb === "reply");
    if (write && w.__hold) { w.__held.push(m); w.__autoReply = false; } else w.__autoReply = true;
    return Array.prototype.push.call(this, m);
  };
});
/** Refuse the held write `i`, as the kernel answers a write that could not be made. */
const refuse = (page: any, i: number): Promise<void> => page.evaluate(([k, error]: [number, string]) => {
  const m = (window as any).__held[k];
  window.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsFailed", reqId: m.reqId, verb: m.verb, code: "failed", error } }));
}, [i, REFUSAL]);
/** Type into the panel's box. */
async function typeIn(page: any, words: string): Promise<void> {
  await page.focus(".fileview-aside .fc-input");
  await page.keyboard.press("Control+A"); await page.keyboard.press("Delete");
  await page.keyboard.type(words);
}

for (const mode of ["pane", "feed"] as const) {
  for (const [pointer, touch] of [["a fine pointer", false], ["a coarse pointer", true]] as Array<[string, boolean]>) {
    test("in the " + mode + ", on " + pointer + ": the parts of one waiting note stand 6 px apart and two notes 12 px apart", { timeout: 120000 }, async (t) => {
      await inBrowser(t, async (browser: any) => {
        const ctx = await browser.newContext({ viewport: { width: 1100, height: 900 }, hasTouch: touch, isMobile: touch });
        const page = await ctx.newPage();
        const errors: string[] = [];
        page.on("pageerror", (e: Error) => { errors.push(e.message); });
        const html = pageHtml(mode, { [REPORT]: SRC }, MT);
        await page.route((u: URL) => u.href.startsWith(ORIGIN), (route: any) => route.fulfill({ status: 200, contentType: "text/html", body: html }));
        await page.goto(ORIGIN + "/");
        assert.equal(await page.evaluate(() => matchMedia("(pointer: coarse)").matches), touch, "the precondition: the context reads as " + pointer);
        await page.evaluate((st: unknown) => { (window as any).__status = st; }, STATUS);
        await arm(page);
        await page.evaluate(([p, sid]: [string, string]) => { (window as any).FV.openFileView(p, sid, null); }, [REPORT, SID]);
        await page.waitForFunction(() => !!document.querySelector(".fileview-md > p"), null, { timeout: 10000 });
        await frames(page, 2);
        await openPanel(page);
        await page.waitForSelector('.fileview-aside .fc-card[data-id="' + WHOLE.id + '"]');
        // a comment's write held; a second comment typed and saved, held too; a third typed; the two refused in turn
        await page.evaluate(() => { (window as any).__hold = true; });
        await page.click('.fileview-aside [data-act="fcfile"]');
        await typeIn(page, "Say which cache, and cite the run the p99 came from.");
        await page.click('.fileview-aside [data-act="fcsave"]');
        await page.waitForFunction(() => (window as any).__held.length === 1, null, { timeout: 5000 });
        await page.click('.fileview-aside [data-act="fcfile"]');
        await typeIn(page, "Lead with the numbers, then the method.");
        await refuse(page, 0);
        await page.waitForFunction(() => document.querySelectorAll(".fileview-aside .fc-held-save").length === 1, null, { timeout: 5000 });
        await page.click('.fileview-aside [data-act="fcsave"]');
        await page.waitForFunction(() => (window as any).__held.length === 2, null, { timeout: 5000 });
        await page.click('.fileview-aside [data-act="fcfile"]');
        await typeIn(page, "Number the figures.");
        await refuse(page, 1);
        await page.waitForFunction(() => document.querySelectorAll(".fileview-aside .fc-held-save").length === 2, null, { timeout: 5000 });
        await frames(page, 3);
        // each note's parts: its own elements and, where the line stood outside it, the reason's line that follows it; grouped
        // into visual lines by top edge; the gaps between one note's lines, and between one note's last line and the next's first
        const m = await page.evaluate(() => {
          const notes = Array.from(document.querySelectorAll(".fileview-aside .fc-held-save")) as HTMLElement[];
          const parts = (n: HTMLElement): HTMLElement[] => {
            const own = (Array.from(n.children) as HTMLElement[]);
            const next = n.nextElementSibling as HTMLElement | null;
            return own.concat(next && next.classList.contains("fc-held-why") ? [next] : []).filter((e) => !e.hidden && e.getBoundingClientRect().height > 0);
          };
          const lines = (n: HTMLElement): Array<{ top: number; bottom: number }> => {
            const out: Array<{ top: number; bottom: number }> = [];
            for (const r of parts(n).map((e) => e.getBoundingClientRect()).sort((a, b) => a.top - b.top)) {
              const last = out[out.length - 1];
              if (last && r.top < last.bottom - 0.5) last.bottom = Math.max(last.bottom, r.bottom);
              else out.push({ top: r.top, bottom: r.bottom });
            }
            return out;
          };
          const r1 = (x: number) => Math.round(x * 10) / 10;
          const ls = notes.map(lines);
          return {
            within: ls.map((l) => l.slice(1).map((x, i) => r1(x.top - l[i].bottom))),
            between: ls.slice(1).map((l, i) => r1(l[0].top - ls[i][ls[i].length - 1].bottom)),
            whyInNote: notes.map((n) => !!n.querySelector(".fc-held-why")),
            whyShown: Array.from(document.querySelectorAll(".fileview-aside .fc-held-why")).filter((e) => !(e as HTMLElement).hidden).length,
          };
        });
        assert.equal(m.whyShown, touch ? 2 : 0, "the precondition: the reason's line shows on a coarse pointer alone: " + JSON.stringify(m));
        for (const w of m.within) {
          assert.ok(w.length >= 1, "the precondition: a note's parts take more than one line: " + JSON.stringify(m));
          for (const g of w) assert.ok(Math.abs(g - 6) <= 0.5, "the parts of one note stand 6 px apart: " + JSON.stringify(m));
        }
        assert.equal(m.between.length, 1, "the precondition: two notes: " + JSON.stringify(m));
        assert.ok(Math.abs(m.between[0] - 12) <= 0.5, "two notes stand 12 px apart, farther than the parts of one note: " + JSON.stringify(m));
        assert.deepEqual(errors, [], "no page error");
        await ctx.close();
      });
    });
  }
}

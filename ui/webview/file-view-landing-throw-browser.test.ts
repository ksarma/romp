// A fetch landing the press hold parked, whose paint throws, still says so in the body (review of Slice 3 of
// plans/markdown-viewer.md, round 2, 2026-09-08). A reload's landing runs through actions.ts pressHold: at once when
// nothing is pressed, else at the release, on a zero timer outside the fetch's promise chain. Round 1 wired the landing
// as `.then((t) => hold.defer(() => {...}))`, so a throw from a PARKED landing (renderBody's DOM passes, after the
// landing had already taken the new mtime) reached nobody: an uncaught page error, the OLD text standing in the body
// under the NEW mtime, no error row, while the same throw from an immediate landing reached the chain's `.catch` and
// painted `.fileview-err`. The Comments panel trusts mtimeNs() to say which text the body shows (file-view.ts, the
// landing's header), so that body lied twice over. The landing now runs through a promise that settles with the parked
// run, so its throw rejects into the same `.catch` (actions.ts `defer` returns it). Two scenes over the real viewer
// (real-viewer-leg.ts), the pane surface, `body.replaceChildren` made to throw when handed the rendered note: (1) a
// press over the note, the reload's fetch lands under it, the release; (2) the same reload with nothing pressed. Both
// paint the failure into the body, both leave no uncaught error, and the parked scene shows exactly what the
// immediate one does. The wait is for the injected throw itself (a counter the patch bumps), never a timer. Skips
// LOUDLY without a playwright browser (CI installs none), as the other legs do. Synthetic values only: an invented
// note, the placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, frames, REPORT, MT, MT2 } from "./real-viewer-leg";

const F = "```";
const note = (intro: string): string => ["# Report", "", intro, "", F + "python", "# a comment\ndef f(x):\n    return x + 1", F, "", "A paragraph after the fence.", ""].join("\n");
const INTRO1 = "An intro paragraph before the fence.";
const DOC1 = note(INTRO1);
const DOC2 = note("An intro paragraph before the fence, rewritten by a session.");
const WHY = "synthetic renderBody failure";

/** Make the body's replaceChildren throw when handed a rendered note (the landing's paint), and count the throws; the
 *  failure row (`.fileview-err`) and every other body still go through. */
const inject = (page: any): Promise<void> => page.evaluate((why: string) => {
  const w = window as any;
  const body = document.querySelector(".fileview-body") as HTMLElement;
  const orig = body.replaceChildren.bind(body);
  w.__threw = 0;
  body.replaceChildren = function (...nodes: any[]) {
    if (nodes.some((n) => n && n.classList && n.classList.contains("fileview-md"))) { w.__threw++; throw new Error(why); }
    return orig(...nodes);
  } as any;
}, WHY);
const centre = (page: any, sel: string, dx = 0): Promise<{ x: number; y: number }> => page.evaluate(([s, d]: [string, number]) => {
  const r = document.querySelector(s)!.getBoundingClientRect();
  return { x: d ? r.x + d : r.x + r.width / 2, y: r.y + r.height / 2 };
}, [sel, dx]);
const counts = (page: any): Promise<{ fetches: number; paints: number; threw: number }> => page.evaluate(() => ({ fetches: (window as any).__fetches, paints: (window as any).__paints, threw: (window as any).__threw }));
/** A session's write: new bytes under a new mtime, and the reload the panel's poll would ask for. */
const reload = async (page: any, text: string, mtime: string): Promise<void> => {
  const before = await counts(page);
  await page.evaluate(([p, t, m]: [string, string, string]) => { const w = window as any; w.__docs[p] = t; w.__mtime = m; w.__seam.reload(); }, [REPORT, text, mtime]);
  await page.waitForFunction((n: number) => (window as any).__fetches > n, before.fetches, { timeout: 10000 });
  await frames(page, 2);
};
/** Wait for the injected throw (the landing ran), then two frames: the rejection's microtasks are long drained. */
const thrown = async (page: any, n: number): Promise<void> => {
  await page.waitForFunction((k: number) => (window as any).__threw >= k, n, { timeout: 10000 });
  await frames(page, 2);
};
type Shown = { bodyErr: string | null; errRows: number; intro: string | null; mt: string; paints: number; threw: number };
const shown = (page: any): Promise<Shown> => page.evaluate(() => {
  const w = window as any;
  const err = document.querySelector(".fileview-body .fileview-err");
  const p = document.querySelector(".fileview-md p");
  return {
    bodyErr: err ? (err.textContent || "").trim() : null,
    errRows: document.querySelectorAll(".fileview-body .fileview-err").length,
    intro: p ? (p.textContent || "").trim() : null,
    mt: w.__seam.mtimeNs(), paints: w.__paints, threw: w.__threw,
  };
});

test("in a browser: a reload landing parked under a press whose paint throws paints the failure into the body at the release, with no uncaught error and no stale text", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openViewer(browser, "pane", 900, 700, { docs: { [REPORT]: DOC1 } });
    assert.equal(await page.evaluate(() => (window as any).__seam.mtimeNs()), MT);
    await inject(page);
    const p = await centre(page, ".fileview-md p", 10);
    await page.mouse.move(p.x, p.y); await frames(page, 1);
    await page.mouse.down(); await frames(page, 1);
    const pressed = await counts(page);
    await reload(page, DOC2, MT2);
    const under = await shown(page);
    assert.equal(under.threw, 0, "the landing waits under the press: nothing painted, nothing thrown");
    assert.equal(under.intro, INTRO1, "the old text stands while the press holds");
    assert.equal(under.mt, MT, "and the old mtime with it");
    await page.mouse.up();
    await thrown(page, 1);
    const after = await shown(page);
    assert.equal(after.threw, 1, "the release ran the parked landing, whose paint threw");
    assert.equal(after.bodyErr, WHY + REPORT, "the failure is in the body, the way an immediate landing's is (the chain's .catch: the message, then the path as the hint)");
    assert.equal(after.errRows, 1, "one failure row");
    assert.equal(after.intro, null, "the old text is gone with it: a body that says the new mtime shows no stale note");
    assert.equal(after.mt, MT2, "the landing took the mtime before its paint, as it always has");
    assert.equal(after.paints, pressed.paints, "a paint that threw fired no onRendered");
    assert.deepEqual(errors, [], "no uncaught page error: the throw went to the landing's .catch");
    await page.close();
  });
});

test("in a browser: the same throw from an immediate landing (nothing pressed) paints the same failure row, so the two paths agree", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openViewer(browser, "pane", 900, 700, { docs: { [REPORT]: DOC1 } });
    await inject(page);
    const before = await counts(page);
    await reload(page, DOC2, MT2);
    await thrown(page, 1);
    const after = await shown(page);
    assert.equal(after.threw, 1);
    assert.equal(after.bodyErr, WHY + REPORT);
    assert.equal(after.errRows, 1);
    assert.equal(after.intro, null);
    assert.equal(after.mt, MT2);
    assert.equal(after.paints, before.paints);
    assert.deepEqual(errors, [], "no uncaught page error");
    await page.close();
  });
});

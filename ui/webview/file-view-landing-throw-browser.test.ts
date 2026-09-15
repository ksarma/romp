// A fetch landing whose paint throws, parked under a press or immediate, still says so in the body (review of Slice 3 of
// plans/markdown-viewer.md, round 2, 2026-09-08; re-aimed by Slice 7, item 1). A reload's landing runs through actions.ts
// pressHold: at once when nothing is pressed, else at the release, on a zero timer outside the fetch's promise chain. Round 1
// wired the landing as `.then((t) => hold.defer(() => {...}))`, so a throw from a PARKED landing (renderBody's DOM passes,
// after the landing had already taken the new mtime) reached nobody: an uncaught page error, the OLD text standing in the
// body under the NEW mtime, no error row, while the same throw from an immediate landing reached the chain's `.catch` and
// painted `.fileview-err`. The Comments panel trusts mtimeNs() to say which text the body shows (file-view.ts, the
// landing's header), so that body lied twice over. The landing runs through a promise that settles with the parked run,
// so a throw rejects into the same `.catch` (actions.ts `defer` returns it).
// Since Slice 7 (item 1: every failure says what happened) the paint's own throw never reaches that `.catch`: renderBody
// wraps the block's build and the swap in one try, and its catch paints the RENDER_FELL line (the sentence and the error's
// message) as the body's first child and the NEW text as Raw rows under it, then runs the rest of the pass, so the hooks
// fire once for the fallback (`__paints` grows by one), `mode()` answers "raw" over the rows while the Rendered button stays
// pressed, and mtimeNs() says the new mtime of the text that shows. The chain's `.catch` keeps its role for a refused
// fetch and for a throw from the fallback itself. Two scenes over the real viewer (real-viewer-leg.ts), the pane surface,
// `body.replaceChildren` made to throw when handed the rendered note: (1) a press over the note, the reload's fetch lands
// under it, the release; (2) the same reload with nothing pressed, then the Raw click (rows, no line) and, the injection
// lifted, the Rendered click (the note renders again). Both paint the line and the rows, both leave no uncaught error, and
// the parked scene shows exactly what the immediate one does. The wait is for the injected throw itself (a counter the
// patch bumps), never a timer. Skips LOUDLY without a playwright browser (CI installs none), as the other legs do. Before
// Slice 7: the body held the chain's pane (the message, then the path as the hint), no rows, no paint fired, mode()
// "rendered" (red over a git archive of the base with RENDER_FELL stubbed). Synthetic values only: an invented note, the
// placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { inBrowser, openViewer, frames, REPORT, MT, MT2, UI } from "./real-viewer-leg";

const F = "```";
const note = (intro: string): string => ["# Report", "", intro, "", F + "python", "# a comment\ndef f(x):\n    return x + 1", F, "", "A paragraph after the fence.", ""].join("\n");
const INTRO1 = "An intro paragraph before the fence.";
const DOC1 = note(INTRO1);
const DOC2 = note("An intro paragraph before the fence, rewritten by a session.");
const WHY = "synthetic renderBody failure";
/** The line's sentence, read off the viewer's source (the exported constant the guide's pins hold; the page's bundle exports no
 *  constants), so the leg names the words once. */
const RENDER_FELL = (/^export const RENDER_FELL = "([^"]+)";$/m.exec(fs.readFileSync(path.join(UI, "file-view.ts"), "utf8")) || [])[1];
/** DOC2 as codeBlock rows it: one row per line, the trailing newline no row. */
const ROWS2 = DOC2.split("\n").length - 1;

/** Make the body's replaceChildren throw when handed a rendered note (the landing's paint), and count the throws; the
 *  failure line, the Raw rows and every other body still go through. `uninject` puts the browser's own back. */
const inject = (page: any): Promise<void> => page.evaluate((why: string) => {
  const w = window as any;
  const body = document.querySelector(".fileview-body") as HTMLElement;
  const orig = body.replaceChildren.bind(body);
  w.__threw = 0;
  w.__uninject = () => { body.replaceChildren = orig as any; };
  body.replaceChildren = function (...nodes: any[]) {
    if (nodes.some((n) => n && n.classList && n.classList.contains("fileview-md"))) { w.__threw++; throw new Error(why); }
    return orig(...nodes);
  } as any;
}, WHY);
const uninject = (page: any): Promise<void> => page.evaluate(() => { (window as any).__uninject(); });
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
/** Wait for the injected throw (the landing ran), then two frames: the catch's paint is synchronous, the microtasks long drained. */
const thrown = async (page: any, n: number): Promise<void> => {
  await page.waitForFunction((k: number) => (window as any).__threw >= k, n, { timeout: 10000 });
  await frames(page, 2);
};
/** The Rendered/Raw button by label, clicked in the page (the buttons are the action row's). */
const clickSeg = (page: any, label: string): Promise<void> => page.evaluate((l: string) => {
  const b = Array.from(document.querySelectorAll(".fileview-acts button")).find((x) => x.textContent === l) as HTMLButtonElement;
  b.click();
}, label);
type Shown = { bodyErr: string | null; errRows: number; first: string | null; rows: number; mdBox: boolean; intro: string | null; mode: string; pressed: string | null; mt: string; paints: number; threw: number };
const shown = (page: any): Promise<Shown> => page.evaluate(() => {
  const w = window as any;
  const body = document.querySelector(".fileview-body")!;
  const err = body.querySelector(".fileview-err");
  const p = document.querySelector(".fileview-md p");
  const pressed = document.querySelector('.fileview-acts button[aria-pressed="true"]');
  return {
    bodyErr: err ? (err.textContent || "").trim() : null,
    errRows: body.querySelectorAll(".fileview-err").length,
    first: body.firstElementChild ? body.firstElementChild.className : null,
    rows: body.querySelectorAll("code.hljs .fv-cl").length,
    mdBox: !!body.querySelector(".fileview-md"),
    intro: p ? (p.textContent || "").trim() : null,
    mode: w.__seam.mode(), pressed: pressed ? pressed.textContent : null,
    mt: w.__seam.mtimeNs(), paints: w.__paints, threw: w.__threw,
  };
});
/** What a landing whose paint threw shows: the line first with the sentence and the message, the new text's rows under it, no
 *  Rendered box, mode() raw with the Rendered button still pressed, the new mtime, one throw, one more paint than before. */
const assertFell = (after: Shown, paintsBefore: number, scene: string): void => {
  assert.ok(RENDER_FELL, "the RENDER_FELL constant is exported by file-view.ts");
  assert.equal(after.threw, 1, scene + ": the landing ran, and its paint threw once");
  assert.equal(after.first, "fileview-err", scene + ": the failure line is the body's first child");
  assert.equal(after.bodyErr, RENDER_FELL + " (" + WHY + ").", scene + ": the line names what happened: the sentence, then the message (no hint, no Download)");
  assert.equal(after.errRows, 1, scene + ": one failure line");
  assert.equal(after.rows, ROWS2, scene + ": the NEW text as Raw rows under the line, one per line");
  assert.equal(after.mdBox, false, scene + ": no Rendered box");
  assert.equal(after.intro, null, scene + ": the old text is gone with it: a body that says the new mtime shows no stale note");
  assert.equal(after.mode, "raw", scene + ": mode() answers raw over the rows");
  assert.equal(after.pressed, "Rendered", scene + ": the Rendered button stays pressed (the saved choice; the line says why rows show)");
  assert.equal(after.mt, MT2, scene + ": the landing took the mtime before its paint, as it always has");
  assert.equal(after.paints, paintsBefore + 1, scene + ": the fallback paint fired the hooks once");
};

test("in a browser: a reload landing parked under a press whose paint throws paints the failure line and the new text's Raw rows into the body at the release, with the hooks fired once, mode() raw, no uncaught error and no stale text", { timeout: 180000 }, async (t) => {
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
    assert.equal(under.mode, "rendered");
    await page.mouse.up();
    await thrown(page, 1);
    assertFell(await shown(page), pressed.paints, "parked");
    assert.deepEqual(errors, [], "no uncaught page error: the throw went to renderBody's catch");
    await page.close();
  });
});

test("in a browser: the same throw from an immediate landing (nothing pressed) paints the same line and rows, so the two paths agree; the Raw click leaves rows and no line, and the Rendered click with the injection lifted renders the note again", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openViewer(browser, "pane", 900, 700, { docs: { [REPORT]: DOC1 } });
    await inject(page);
    const before = await counts(page);
    await reload(page, DOC2, MT2);
    await thrown(page, 1);
    const after = await shown(page);
    assertFell(after, before.paints, "immediate");
    // the Raw click: the rows alone, the record cleared, one more paint
    await clickSeg(page, "Raw"); await frames(page, 2);
    const raw = await shown(page);
    assert.equal(raw.first, "fileview-code", "rows alone: the line went with the Rendered attempt");
    assert.equal(raw.errRows, 0); assert.equal(raw.rows, ROWS2); assert.equal(raw.mode, "raw"); assert.equal(raw.pressed, "Raw");
    assert.equal(raw.paints, after.paints + 1);
    // the Rendered click, the injection lifted: the note renders, mode() rendered
    await uninject(page);
    await clickSeg(page, "Rendered"); await frames(page, 2);
    const back = await shown(page);
    assert.equal(back.mdBox, true, "the Rendered box is back"); assert.equal(back.errRows, 0); assert.equal(back.mode, "rendered"); assert.equal(back.pressed, "Rendered");
    assert.equal(back.intro, "An intro paragraph before the fence, rewritten by a session.", "the new text, rendered");
    assert.equal(back.threw, 1, "no further throw"); assert.equal(back.paints, raw.paints + 1);
    assert.deepEqual(errors, [], "no uncaught page error");
    await page.close();
  });
});

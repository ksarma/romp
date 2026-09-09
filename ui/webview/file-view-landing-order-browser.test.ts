// Two answers to the viewer's reload under one press land the NEWEST, and a landing parked under a press paints nothing
// into a viewer a later open replaced (review of Slice 3 of plans/markdown-viewer.md, round 3, 2026-09-09). A reload's
// fetch landing runs through actions.ts pressHold (file-view.ts fetchFile): at once when nothing is pressed over the body,
// else parked for the release, and a later defer under the same press REPLACES the parked run. The chain read fetchSeq
// (the newest fetch wins) inside the parked run only, so an OLDER fetch's answer arriving under the press after the newer
// one had parked reached defer, displaced the newer landing (resolved, unpainted) and parked itself, then bailed at the
// release on fetchSeq: the body kept the old text under the old mtime, and the Comments panel's askReload never re-asks
// for a mtime it has asked for. The chain reads its guards BEFORE the defer now as well (`stands`: this fetch is the newest
// out and its viewer is connected), so an answer that cannot land never reaches the hold. The same guard closes the
// replace-open hole: the landing's first guard was the viewer's id, which the NEW viewer satisfies after a replace-open,
// so a parked landing (or one whose fetch was in flight across the replace) painted into the replaced viewer's detached
// body and fired its onRendered hooks; `wrap.isConnected` is the check now, in the text branch and the failure path as it
// was in the Blob branch. Four scenes over the real viewer (real-viewer-leg.ts), the pane surface, the fetch stub gated
// so the test answers each reload's fetch by hand: (1) a press over the note, two reloads, the newer answered first and
// the older second, the release: the newest bytes and mtime land, once; (2) the same with the older fetch FAILING after
// the newer parked: the newest bytes land and no failure row; (3) a parked landing, a replace-open during the press, the
// release: the old body, mtime and hooks untouched, the new viewer standing; (4) the same replace with the reload's fetch
// in flight and nothing pressed. The waits are for the stub's own counts, the seam's paints and a zero timer queued after
// the hold's (ordering, not a sleep), never a duration. Skips LOUDLY without a playwright browser (CI installs none), as
// the other legs do. Synthetic values only: an invented note, /repo/notes-api paths, the placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, frames, paintsReach, REPORT, ROOT, SID, MT, MT2 } from "./real-viewer-leg";

const F = "```";
const note = (intro: string): string => ["# Report", "", intro, "", F + "python", "# a comment\ndef f(x):\n    return x + 1", F, "", "A paragraph after the fence.", ""].join("\n");
const INTRO1 = "An intro paragraph before the fence.";
const INTRO2 = "Rewritten once by a session.";
const INTRO3 = "Rewritten twice by a session.";
const DOC1 = note(INTRO1), DOC2 = note(INTRO2), DOC3 = note(INTRO3);
const MT3 = "1757145600000000017";
const OTHER = ROOT + "/docs/other.md";
const OTHER_DOC = "# Other\n\nThe other file's paragraph.\n";

/** Gate the report's fetches: each is parked in `window.__gated` (in the order made) until the test answers it, with a
 *  status and, for a 200, the kernel's text headers under the given mtime. Every other fetch (another file, the version
 *  and sessions asks) goes to the harness's stub as before. */
const gate = (page: any): Promise<void> => page.evaluate((report: string) => {
  const w = window as any;
  w.__gated = [];
  const orig = w.fetch;
  w.fetch = function (url: string) {
    url = String(url);
    const m = /[?&]path=([^&]*)/.exec(url);
    if (!m || decodeURIComponent(m[1]) !== report) return orig(url);
    w.__fetches++;
    return new Promise((resolve) => {
      w.__gated.push({ url, answer: (text: string, mtime: string, status: number) => {
        if (status !== 200) { resolve(new Response(text, { status })); return; }
        resolve(new Response(text, { status: 200, headers: { "Content-Type": "text/plain; charset=utf-8", "X-Romp-Mtime-Ns": mtime, "X-Romp-Text-Utf8": "1" } }));
      } });
    });
  };
}, REPORT);
const answer = (page: any, i: number, text: string, mtime: string, status = 200): Promise<void> =>
  page.evaluate(([k, t, m, s]: [number, string, string, number]) => { (window as any).__gated[k].answer(t, m, s); }, [i, text, mtime, status]);
/** Wait until `n` of the report's fetches are gated. */
const gated = (page: any, n: number): Promise<unknown> => page.waitForFunction((k: number) => (window as any).__gated.length >= k, n, { timeout: 10000 });
const centre = (page: any, sel: string, dx = 0): Promise<{ x: number; y: number }> => page.evaluate(([s, d]: [string, number]) => {
  const r = document.querySelector(s)!.getBoundingClientRect();
  return { x: d ? r.x + d : r.x + r.width / 2, y: r.y + r.height / 2 };
}, [sel, dx]);
/** A zero timer queued after the hold's own (queued at the pointerup): when it fires, the parked run has run or stood down. */
const afterTimers = (page: any): Promise<void> => page.evaluate(() => new Promise<void>((r) => { setTimeout(() => r(), 0); }));
type Shown = { intro: string | null; mt: string; paints: number; errRows: number };
const shown = (page: any): Promise<Shown> => page.evaluate(() => {
  const w = window as any;
  const p = document.querySelector("#romp-fileview .fileview-md p");
  return { intro: p ? (p.textContent || "").trim() : null, mt: w.__seam.mtimeNs(), paints: w.__paints, errRows: document.querySelectorAll("#romp-fileview .fileview-body .fileview-err").length };
});
/** Press the primary button over the note's intro paragraph and leave it pressed. */
const pressNote = async (page: any): Promise<void> => {
  const p = await centre(page, ".fileview-md p", 10);
  await page.mouse.move(p.x, p.y); await frames(page, 1);
  await page.mouse.down(); await frames(page, 1);
};

test("in a browser: two reloads under a press, the newer fetch answered first and the older second, land the newest bytes and mtime at the release", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openViewer(browser, "pane", 900, 700, { docs: { [REPORT]: DOC1 } });
    await gate(page);
    await pressNote(page);
    const pressed = await shown(page);
    assert.equal(pressed.mt, MT);
    await page.evaluate(() => { const w = window as any; w.__seam.reload(); w.__seam.reload(); });   // two writes within a poll interval: two fetches out
    await gated(page, 2);
    await answer(page, 1, DOC3, MT3); await frames(page, 3);   // the NEWER fetch answers first and parks under the press
    const parked = await shown(page);
    assert.equal(parked.intro, INTRO1, "the newer landing waits under the press");
    assert.equal(parked.mt, MT, "and the mtime with it");
    assert.equal(parked.paints, pressed.paints);
    await answer(page, 0, DOC2, MT2); await frames(page, 3);   // the OLDER fetch answers while the press continues
    const both = await shown(page);
    assert.equal(both.intro, INTRO1, "still nothing painted under the press");
    assert.equal(both.mt, MT);
    assert.equal(both.paints, pressed.paints);
    await page.mouse.up();
    await paintsReach(page, pressed.paints + 1);
    await frames(page, 2);
    const after = await shown(page);
    assert.equal(after.intro, INTRO3, "the release lands the NEWEST fetch's bytes: the older answer, arriving second, must not displace the newer fetch's parked landing (the Slice 3 tree kept the old text)");
    assert.equal(after.mt, MT3, "under the newest mtime (the Slice 3 tree kept the old one, and nothing re-asks for a mtime the panel has asked for)");
    assert.equal(after.paints, pressed.paints + 1, "one paint");
    assert.equal(after.errRows, 0, "no failure row");
    await afterTimers(page); await frames(page, 2);
    assert.equal((await shown(page)).paints, pressed.paints + 1, "and only one: the overtaken answer painted nothing afterwards");
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});

test("in a browser: the older fetch FAILING after the newer landing parked leaves the newest bytes to land at the release, and paints no failure row", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openViewer(browser, "pane", 900, 700, { docs: { [REPORT]: DOC1 } });
    await gate(page);
    await pressNote(page);
    const pressed = await shown(page);
    await page.evaluate(() => { const w = window as any; w.__seam.reload(); w.__seam.reload(); });
    await gated(page, 2);
    await answer(page, 1, DOC3, MT3); await frames(page, 3);                       // the newer parks
    await answer(page, 0, "synthetic server failure", "", 500); await frames(page, 3);   // the older fails under the same press
    const both = await shown(page);
    assert.equal(both.intro, INTRO1); assert.equal(both.mt, MT); assert.equal(both.errRows, 0);
    await page.mouse.up();
    await paintsReach(page, pressed.paints + 1);
    await frames(page, 2);
    const after = await shown(page);
    assert.equal(after.intro, INTRO3, "the newest bytes land: an overtaken failure displaces nothing (the Slice 3 tree kept the old text and showed no row either)");
    assert.equal(after.mt, MT3);
    assert.equal(after.errRows, 0, "an overtaken failure paints no row: nobody awaits it");
    assert.equal(after.paints, pressed.paints + 1);
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});

type Replaced = { shownH1: string | null; viewers: number; oldBodyConnected: boolean; oldBodyIntro: string | null; oldSeamMt: string; oldSeamPaints: number; seamIsOld: boolean; paints: number };
/** The old viewer's body, seam and hooks against the one standing: stashed by `stash`, read by `state`. */
const stash = (page: any): Promise<void> => page.evaluate(() => {
  const w = window as any;
  w.__oldSeam = w.__seam; w.__oldBody = document.querySelector(".fileview-body"); w.__oldSeamPaints = 0;
  w.__oldSeam.onRendered(() => { w.__oldSeamPaints++; });
});
const state = (page: any): Promise<Replaced> => page.evaluate(() => {
  const w = window as any;
  const h1 = document.querySelector("#romp-fileview .fileview-md h1");
  const oldP = w.__oldBody.querySelector(".fileview-md p");
  return {
    shownH1: h1 ? (h1.textContent || "").trim() : null, viewers: document.querySelectorAll("#romp-fileview").length,
    oldBodyConnected: w.__oldBody.isConnected, oldBodyIntro: oldP ? (oldP.textContent || "").trim() : null,
    oldSeamMt: w.__oldSeam.mtimeNs(), oldSeamPaints: w.__oldSeamPaints, seamIsOld: w.__seam === w.__oldSeam, paints: w.__paints,
  };
});
const replaceOpen = async (page: any): Promise<void> => {
  await page.evaluate(([o, sid]: [string, string]) => { (window as any).FV.openFileView(o, sid, null); }, [OTHER, SID]);
  await page.waitForFunction(() => { const h = document.querySelector("#romp-fileview .fileview-md h1"); return !!h && (h.textContent || "").trim() === "Other"; }, null, { timeout: 10000 });
  await frames(page, 2);
};

test("in a browser: a landing parked under a press paints nothing into a viewer a replace-open removed during the press, and fires none of its hooks", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openViewer(browser, "pane", 900, 700, { docs: { [REPORT]: DOC1, [OTHER]: OTHER_DOC } });
    await gate(page);
    await stash(page);
    await pressNote(page);
    const pressed = await state(page);
    await page.evaluate(() => { (window as any).__seam.reload(); });
    await gated(page, 1);
    await answer(page, 0, DOC2, MT2); await frames(page, 3);   // parked under the press
    const parked = await state(page);
    assert.equal(parked.oldBodyIntro, INTRO1, "parked: the old text stands");
    assert.equal(parked.oldSeamMt, MT);
    assert.equal(parked.paints, pressed.paints);
    await replaceOpen(page);                                      // another file opened over this one, with no pointer route (a relay, the Files pane)
    const replaced = await state(page);
    assert.equal(replaced.shownH1, "Other"); assert.equal(replaced.viewers, 1);
    assert.equal(replaced.seamIsOld, false, "a new open, a new seam");
    assert.equal(replaced.oldBodyConnected, false, "the old body is detached");
    assert.equal(replaced.oldBodyIntro, INTRO1);
    await page.mouse.up();
    await afterTimers(page); await frames(page, 2);
    const after = await state(page);
    assert.equal(after.oldBodyIntro, INTRO1, "the release ran no landing into the replaced viewer's detached body (the Slice 3 tree painted the new bytes into it: its guard was the viewer id, which the new viewer satisfies)");
    assert.equal(after.oldSeamMt, MT, "the replaced viewer's mtime did not move");
    assert.equal(after.oldSeamPaints, 0, "and its onRendered hooks did not fire (the Slice 3 tree fired them, over a disposed panel)");
    assert.equal(after.paints, replaced.paints, "no paint anywhere after the release");
    assert.equal(after.shownH1, "Other", "the new viewer stands untouched");
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});

test("in a browser: the same replace-open while the reload's fetch is in flight, nothing pressed, paints nothing into the replaced viewer either", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openViewer(browser, "pane", 900, 700, { docs: { [REPORT]: DOC1, [OTHER]: OTHER_DOC } });
    await gate(page);
    await stash(page);
    await page.evaluate(() => { (window as any).__seam.reload(); });
    await gated(page, 1);                                         // the fetch is out and unanswered
    await replaceOpen(page);
    const replaced = await state(page);
    assert.equal(replaced.oldBodyConnected, false);
    await answer(page, 0, DOC2, MT2); await frames(page, 3);      // the answer lands after the replace
    await afterTimers(page); await frames(page, 2);
    const after = await state(page);
    assert.equal(after.oldBodyIntro, INTRO1, "the answer painted nothing into the detached body (the base tree had the same hole over the fetch's latency; the hold widened it to the press)");
    assert.equal(after.oldSeamMt, MT);
    assert.equal(after.oldSeamPaints, 0);
    assert.equal(after.paints, replaced.paints);
    assert.equal(after.shownH1, "Other");
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});

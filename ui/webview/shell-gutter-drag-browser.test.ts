// The dashboard shell's divider drag, run in headless Chromium over the REAL landing script extracted from kernel.py
// (shell-drag-leg.ts). Pinned here (2026-09-09): while the pointer moves, the panes hold their widths and only the ghost line
// (#gv-ghost) follows it; the two grows are written once, at mouseup, and persisted. Before this, every mousemove wrote the
// two grows, and each write re-laid out every same-origin pane document in that frame; with a big reviewed file in the
// Files pane one step cost over a second and a drag of sixty steps was a 20 s main-thread block. The ghost's clamp is the
// drag's clamp (a pane never goes under min(120px, a quarter of the pair)). Synthetic page, no session data.
import { test } from "node:test";
import assert from "node:assert/strict";
import { inBrowser, ORIGIN, frames } from "./real-viewer-leg";
import { shellPage, readKernel } from "./shell-drag-leg";

type Shot = { chat: number; files: number; chatLeft: number; writes: number; ghost: string; ghostLeft: number; ghostW: number; drag: boolean; stored: string | null };
const shot = (page: any): Promise<Shot> => page.evaluate(() => {
  const w = window as any; const el = (id: string) => document.getElementById(id) as HTMLElement;
  const ghost = el("gv-ghost"); const gr = ghost.getBoundingClientRect();
  return { chat: el("chat-pane").offsetWidth, files: el("files-pane").offsetWidth, chatLeft: el("chat-pane").getBoundingClientRect().left,
    writes: w.__writes.length, ghost: getComputedStyle(ghost).display, ghostLeft: gr.left, ghostW: gr.width, drag: document.body.classList.contains("drag"),
    stored: localStorage.getItem("romp-pane-grow") };
});

test("a divider drag moves a ghost line; the panes take their widths once, on release", async (t) => {
  await inBrowser(t, async (browser) => {
    const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
    const errors: string[] = []; page.on("pageerror", (e: Error) => { errors.push(e.message); });
    const html = shellPage({ py: readKernel(), viewportW: 1600, filesW: 1000, filesSrc: "about:blank" });
    await page.route((u: URL) => u.href.startsWith(ORIGIN), (route: any) => route.fulfill({ status: 200, contentType: "text/html", body: html }));
    await page.goto(ORIGIN + "/");
    await frames(page, 2);
    // count every grow write from here on (the row's inline style is the one object the shell writes them to)
    await page.evaluate(() => {
      const row = document.querySelector(".row") as HTMLElement; const w = window as any; w.__writes = [];
      const orig = row.style.setProperty.bind(row.style);
      (row.style as any).setProperty = (k: string, v: string) => { if (k.startsWith("--g-")) w.__writes.push([k, v]); return orig(k, v); };
    });
    const g: { x: number; y: number } = await page.evaluate(() => (window as any).__gutter());
    const before = await shot(page);
    assert.equal(before.files, 1000);

    // grab: the shell normalises the shown panes' grows to their widths (writes, no width change)
    await page.mouse.move(g.x, g.y); await page.mouse.down();
    await frames(page, 2);
    const down = await shot(page);
    assert.equal(down.files, 1000, "the grab changes no width"); assert.equal(down.chat, before.chat);
    assert.ok(down.drag, "body.drag during the drag");

    // move 200 px left in ten steps: the panes hold and no grow is written (the shell before 2026-09-09 wrote two per move
    // and the Files pane followed the pointer); the ghost line showed on grab at the divider and now follows the pointer
    await page.mouse.move(g.x - 200, g.y, { steps: 10 });
    await frames(page, 2);
    const mid = await shot(page);
    assert.equal(mid.writes, down.writes, "no grow written while the pointer moves");
    assert.equal(mid.files, 1000, "the Files pane holds its width during the drag");
    assert.equal(mid.chat, down.chat, "the chat pane holds its width during the drag");
    assert.equal(before.ghost, "none", "no ghost before the grab");
    assert.equal(down.ghost, "block", "the ghost shows on grab");
    assert.ok(Math.abs(down.ghostLeft - (down.chatLeft + down.chat)) <= 1, `the ghost sits at the divider on grab: ${down.ghostLeft} vs ${down.chatLeft + down.chat}`);
    assert.equal(down.ghostW, 7);
    assert.equal(mid.ghost, "block");
    assert.ok(Math.abs(mid.ghostLeft - (mid.chatLeft + down.chat - 200)) <= 1, `the ghost follows the pointer: ${mid.ghostLeft} vs ${mid.chatLeft + down.chat - 200}`);

    // release: the two grows are written once, the panes take the widths the ghost showed, the ghost hides, the grows persist
    await page.mouse.up();
    await frames(page, 2);
    const up = await shot(page);
    assert.equal(up.writes, down.writes + 2, "exactly the pair's two grows are written at release");
    assert.ok(Math.abs(up.files - 1200) <= 1, `Files takes the width at release: ${up.files}`);
    assert.ok(Math.abs(up.chat - (down.chat - 200)) <= 1, `chat gives it: ${up.chat}`);
    assert.equal(up.ghost, "none", "the ghost hides at release");
    assert.ok(!up.drag, "body.drag cleared");
    const stored = JSON.parse(up.stored || "{}");
    assert.ok(Math.abs(stored.files - 1200) <= 1, "the grows persist at release: " + up.stored);

    // a second drag, far right: the ghost and the release both clamp at the pair's minimum (min(120px, a quarter))
    const g2: { x: number; y: number } = await page.evaluate(() => (window as any).__gutter());
    await page.mouse.move(g2.x, g2.y); await page.mouse.down();
    await page.mouse.move(1590, g2.y, { steps: 5 });
    await frames(page, 2);
    const far = await shot(page);
    const sum = far.chat + far.files, mn = Math.min(120, sum * 0.25);
    assert.equal(far.files, up.files, "still holding during the second drag");
    assert.ok(Math.abs(far.ghostLeft - (far.chatLeft + sum - mn)) <= 1, `the ghost clamps at the minimum: ${far.ghostLeft} vs ${far.chatLeft + sum - mn}`);
    await page.mouse.up();
    await frames(page, 2);
    const end = await shot(page);
    assert.ok(Math.abs(end.files - mn) <= 1, `Files clamps at ${mn}: ${end.files}`);
    assert.equal(end.writes, up.writes + 2 + 2, "the grab's normalisation and the release, nothing per move");
    assert.deepEqual(errors, []);
    await page.close();
  });
});

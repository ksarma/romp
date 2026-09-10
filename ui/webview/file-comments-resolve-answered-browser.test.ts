// Resolve answered over the REAL viewer and the REAL panel, in Chromium and Firefox (plans/file-review.md, "The about
// follow-on (2026-09-10)" under Slice 2; decision 46). What a stand-in cannot show is measured here: the header action's
// place and count, the confirm's one line, the two resolve requests going out one after the other and the cards leaving
// the open list, the "Reopen all" offer standing where the sent acknowledgment stands (the Send section at the panel's
// foot) in its dress, a real wheel over the body ending it, and a real click on it reopening the same two comments.
// Skips LOUDLY without a playwright browser (CI installs none), as the other browser legs do. Legs await frames, never a
// timer. Synthetic values only: an invented report, /repo/notes-api paths, the placeholder sid, the session name "api".
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as path from "node:path";
import { createRequire } from "node:module";
import { pageHtml, frames, openPanel, PARA, REPORT, SID, MT, ORIGIN, EXT, STATUS as BASE_STATUS } from "./real-viewer-leg";

const requireCjs = createRequire(path.join(EXT, "package.json"));
let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

const T0 = 1757145600000;
const SRC = "# Report\n\n" + Array.from({ length: 40 }, (_, i) => PARA(i + 1)).join("\n\n") + "\n";
const anchorOf = (quote: string) => { const at = SRC.indexOf(quote); assert.ok(at >= 0, quote); return { anchor: { quote, prefix: SRC.slice(Math.max(0, at - 24), at), suffix: SRC.slice(at + quote.length, at + quote.length + 24) }, anchorAt: at }; };
const A_ID = T0 + "-" + SRC.indexOf("Paragraph 3:"), B_ID = (T0 + 1000) + "-" + SRC.indexOf("Paragraph 5:"), C_ID = (T0 + 2000) + "-" + SRC.indexOf("Paragraph 7:");
/** Two comments of the person's the session answered (one in words, one by a revision), and one where the person had the last word. */
const A = { id: A_ID, author: "you", ts: T0, body: "Name the cache here.", ...anchorOf("Paragraph 3:"), replies: [{ author: "api", authorId: SID, ts: T0 + 500, body: "The response cache; named now." }], resolved: false };
const B = { id: B_ID, author: "you", ts: T0 + 1000, body: "Say cut, not reduced.", ...anchorOf("Paragraph 5:"), replies: [{ author: "api", authorId: SID, ts: T0 + 1500, kind: "edit", oldText: "reduced", newText: "cut" }], resolved: false };
const C = { id: C_ID, author: "you", ts: T0 + 2000, body: "Cite the run.", ...anchorOf("Paragraph 7:"), replies: [{ author: "api", authorId: SID, ts: T0 + 2500, body: "Done." }, { author: "you", ts: T0 + 2600, body: "Which run?" }], resolved: false };
const STATUS = { ...BASE_STATUS, store: { ...BASE_STATUS.store, comments: [A, B, C] } };
const resolved = (ids: string[], n: number) => ({ ...STATUS, storeMtimeNs: "17571456000000000" + (20 + n), store: { ...STATUS.store, comments: [A, B, C].map((c) => (ids.includes(c.id) ? { ...c, resolved: true } : c)) } });

type Scene = { head: string | null; confirm: string | null; reopen: { text: string; inSend: boolean; color: string } | null; open: string[]; resolves: Array<{ commentId: string; on: boolean }> };
const scene = (page: any): Promise<Scene> => page.evaluate(() => {
  const aside = document.querySelector(".fileview-aside")!;
  const head = aside.querySelector('[data-act="fcresolveanswered"]') as HTMLElement | null;
  const row = aside.querySelector('[data-act="fcresolveanswereddo"]')?.parentElement as HTMLElement | null;
  const line = aside.querySelector(".fc-reopen") as HTMLElement | null;
  const btn = line ? line.querySelector('[data-act="fcreopenall"]') as HTMLElement | null : null;
  return {
    head: head ? head.textContent : null,
    confirm: row ? (row.querySelector(".fc-note")?.textContent ?? null) : null,
    reopen: line && btn ? { text: line.textContent || "", inSend: !!line.closest(".fc-send"), color: getComputedStyle(btn).color } : null,
    open: Array.from(aside.querySelectorAll(".fc-card:not(.fc-change)")).map((c) => (c as HTMLElement).dataset.id || ""),
    resolves: ((window as any).__posted as any[]).filter((m) => m.type === "fileComments" && m.verb === "resolve").map((m) => m.args),
  };
});

async function inEngine(t: any, name: string, body: (browser: any) => Promise<void>): Promise<void> {
  if (!pw) { t.skip("playwright is not installed under vscode-extension; the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw[name].launch(); }
  catch (e) { t.skip("no playwright " + name + " on this box; this leg needs it (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  try { await body(browser); } finally { await browser.close(); }
}

for (const name of ["chromium", "firefox"]) {
  test(`in ${name}, the real viewer: Resolve answered (2) in the header, the confirm's line, two resolves in order and the cards leaving the open list, Reopen all in the sent acknowledgment's place and dress, a real wheel ending it, a real click reopening both`, { timeout: 240000 }, async (t) => {
    await inEngine(t, name, async (browser) => {
      const page = await browser.newPage({ viewport: { width: 1000, height: 600 } });
      const errors: string[] = [];
      page.on("pageerror", (e: Error) => { errors.push(e.message); });
      const html = pageHtml("pane", { [REPORT]: SRC }, MT);
      await page.route((u: URL) => u.href.startsWith(ORIGIN), (route: any) => route.fulfill({ status: 200, contentType: "text/html", body: html }));
      await page.goto(ORIGIN + "/");
      await page.evaluate(([p, sid, st]: [string, string, unknown]) => { (window as any).__status = st; (window as any).FV.openFileView(p, sid, null); }, [REPORT, SID, STATUS]);
      await page.waitForFunction(() => !!document.querySelector(".fileview-md > p"), null, { timeout: 10000 });
      await frames(page, 2);
      await openPanel(page);
      let s = await scene(page);
      assert.equal(s.head, "Resolve answered (2)", name + ": the header action, the person's two answered comments (words, and a revision)");
      assert.deepEqual(s.open, [A_ID, B_ID, C_ID], name + ": three open cards");
      await page.click('.fileview-aside [data-act="fcresolveanswered"]');
      await frames(page, 2);
      s = await scene(page);
      assert.equal(s.confirm, "Resolve the 2 comments the session has answered?", name + ": the one plain line");
      // the harness answers every ask from __status: the first resolve's reply must already show A resolved, the second both
      await page.evaluate((st: unknown) => { (window as any).__status = st; }, resolved([A_ID, B_ID], 1));
      await page.click('.fileview-aside [data-act="fcresolveanswereddo"]');
      await page.waitForFunction(() => ((window as any).__posted as any[]).filter((m) => m.type === "fileComments" && m.verb === "resolve").length >= 2, null, { timeout: 10000 });
      await page.waitForFunction(() => !!document.querySelector(".fileview-aside .fc-reopen"), null, { timeout: 10000 });
      await frames(page, 3);
      s = await scene(page);
      assert.deepEqual(s.resolves, [{ commentId: A_ID, on: true }, { commentId: B_ID, on: true }], name + ": one resolve per comment, oldest first");
      assert.equal(s.head, null, name + ": nothing answered is open: the action is gone");
      assert.deepEqual(s.open, [C_ID], name + ": the two resolved cards left the open list");
      assert.ok(s.reopen, name + ": the offer stands");
      assert.equal(s.reopen!.text, "Resolved 2 commentsReopen all", name + ": the acknowledgment and the offer");
      assert.equal(s.reopen!.inSend, true, name + ": in the Send section, where the sent acknowledgment stands");
      const green = await page.evaluate(() => { const probe = document.createElement("span"); probe.className = "fc-note fc-sent"; document.querySelector(".fileview-aside .fc-send")!.appendChild(probe); const c = getComputedStyle(probe).color; probe.remove(); return c; });
      assert.equal(s.reopen!.color, green, name + ": in the sent acknowledgment's dress");
      // a real wheel over the body ends the offer
      const body = await page.$(".fileview-body");
      const box = await body.boundingBox();
      await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
      await page.mouse.wheel(0, 60);
      await frames(page, 3);
      s = await scene(page);
      assert.equal(s.reopen, null, name + ": the wheel ends the offer");
      assert.equal(s.resolves.length, 2, name + ": and reopens nothing");
      // again, and a real click on Reopen all reopens both
      await page.evaluate((st: unknown) => { (window as any).__status = st; }, resolved([], 2));
      // both are resolved in the store now, so the action is not offered; reopen them the other way: the store says they are
      // resolved, and the person's next Resolve answered would find nothing. To drive the click, resolve C's twin instead:
      await page.evaluate((st: unknown) => { (window as any).__status = st; }, { ...resolved([A_ID, B_ID], 3), store: { ...STATUS.store, comments: [A, B, C].map((c) => (c.id === C_ID ? { ...c, replies: [...c.replies, { author: "api", authorId: SID, ts: T0 + 2700, body: "The nightly one." }] } : { ...c, resolved: true })) } });
      await page.click(".fileview-fc button"); await frames(page, 2);   // close and reopen the panel: a fresh status
      await page.click(".fileview-fc button"); await page.waitForFunction(() => !!document.querySelector('.fileview-aside [data-act="fcresolveanswered"]'), null, { timeout: 10000 });
      await frames(page, 2);
      s = await scene(page);
      assert.equal(s.head, "Resolve answered (1)", name + ": the third, answered again after the person's last word");
      await page.click('.fileview-aside [data-act="fcresolveanswered"]');
      await frames(page, 2);
      await page.evaluate((st: unknown) => { (window as any).__status = st; }, resolved([A_ID, B_ID, C_ID], 4));
      await page.click('.fileview-aside [data-act="fcresolveanswereddo"]');
      await page.waitForFunction(() => !!document.querySelector(".fileview-aside .fc-reopen"), null, { timeout: 10000 });
      await frames(page, 2);
      await page.evaluate((st: unknown) => { (window as any).__status = st; }, resolved([A_ID, B_ID], 5));
      await page.click('.fileview-aside [data-act="fcreopenall"]');
      await page.waitForFunction(() => ((window as any).__posted as any[]).filter((m) => m.type === "fileComments" && m.verb === "resolve" && m.args.on === false).length >= 1, null, { timeout: 10000 });
      await frames(page, 3);
      s = await scene(page);
      assert.deepEqual(s.resolves.slice(-2), [{ commentId: C_ID, on: true }, { commentId: C_ID, on: false }], name + ": the resolve, then the reopen of the same comment");
      assert.equal(s.reopen, null, name + ": the offer is taken");
      assert.deepEqual(errors, [], name + ": no script error in the page");
      await page.close();
    });
  });
}

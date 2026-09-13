// A note reopened from Recent returns to its place, in a browser (Slice 6 of plans/markdown-viewer.md, item 3): the
// real Files page (files.ts, the shared viewer, the Recent list) in headless Chromium. Open a long note, put block 40
// at the top, close the viewer: the viewer hands the pane the reader's place (file-view.ts RememberedPlace through
// initFileView's onLeave), the pane writes it on the note's Recent row (files-recent.ts placeRecent), and the row's
// click hands it back (openFileView's `place`), so the same block is at the top and the body's scrollTop is the
// pre-close value within a pixel (the plan's acceptance). Then the note rewritten below the block (the span is still a
// block of the text: the same seat), rewritten above it (the span is no block of the new text: the numeric scrollTop,
// clamped), a page reload (localStorage survives, and the shell's relay as the FIRST open after it returns to the block
// and keeps the row's record: the pane reads the row's record for every open, not for the row's click alone; the Slice 6
// review, round 1), a second note opened OVER the first (the replace path writes the first's place; both rows hold
// theirs), and a relay re-open with no row (the viewer's own in-page memory). Leg 3 holds a note's pictures in flight
// (the route answers an .svg when the test says so) for the seat written again at each picture's load, and for the events
// that retire it: the reader's own scroll, and the next text paint (the review's rounds 3 and 4). The
// record holds no text: its JSON in localStorage names no word of the note. Skips LOUDLY without a playwright
// browser (CI installs none). Synthetic values only: the notes-api world, a placeholder session id, invented notes.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { LONG, LONG2, rewritten, MT, MT2, PARA } from "./real-viewer-leg";

const EXT = process.cwd();                                        // npm test runs in vscode-extension
const requireCjs = createRequire(path.join(EXT, "package.json"));
const UI = path.resolve(EXT, "..", "ui", "webview");
const SID = "11111111-2222-3333-4444-555555555555";
const ROOT = "/repo/notes-api";
const REPORT = ROOT + "/docs/report.md";
const NOTES = ROOT + "/docs/notes.md";
const NOTES_TEXT = "# Notes\n\n" + Array.from({ length: 60 }, (_, i) => `Note ${i + 1}: ` + "a short line of notes that wraps once in a narrow pane and no more than that ".repeat(2).trim() + ".").join("\n\n") + "\n";

const BUILD = { bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
  nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent" };
function filesBundle(): string {
  const r = requireCjs("esbuild").buildSync({ ...BUILD, entryPoints: [path.join(UI, "files.ts")] });
  return r.outputFiles[0].text;
}
// the Files page as the kernel serves it: the chat's sheet and the pane's own, the empty state's root, the shim's poster
const PAGE = `<!DOCTYPE html><html><head><meta charset=utf-8><style>
${fs.readFileSync(path.join(UI, "styles.css"), "utf8")}
${fs.readFileSync(path.join(UI, "files-pane.css"), "utf8")}
</style></head><body class=fileview-pane><div id=files-empty></div>
<script>window.__posts=[];window.acquireVsCodeApi=function(){return{postMessage:function(m){window.__posts.push(m);}}};
// what the legs read: the top-visible block of the Rendered view, its first characters and its top edge from the body's top
window.topBlock = function () {
  var body = document.querySelector("#romp-fileview .fileview-body"); if (!body) return null; var br = body.getBoundingClientRect();
  var els = Array.prototype.slice.call(body.querySelectorAll(".fileview-md > *"));
  for (var i = 0; i < els.length; i++) { var r = els[i].getBoundingClientRect(); if (r.bottom > br.top + 0.5) return { text: (els[i].textContent || "").trim().slice(0, 14).trim(), top: Math.round((r.top - br.top) * 10) / 10, scrollTop: body.scrollTop }; }
  return null;
};
// scroll the body so the block whose text starts with the given text sits at the body's top edge
window.putAtTop = function (text) {
  var body = document.querySelector("#romp-fileview .fileview-body");
  var k = Array.prototype.slice.call(body.querySelectorAll(".fileview-md > *")).filter(function (e) { return (e.textContent || "").indexOf(text) === 0; })[0];
  body.scrollTop += k.getBoundingClientRect().top - body.getBoundingClientRect().top;
};
</script><script src=/dist/files.js></script></body></html>`;

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

type Top = { text: string; top: number; scrollTop: number } | null;
type Hold = { on: boolean; wait: Promise<void>; release: () => void };   // a picture's answer held until the test releases it
type H = {
  page: any; docs: Record<string, string>; mtime: { v: string }; hold: (p: string) => () => void;   // hold the picture at the path; the return releases it
  open: (p: string) => Promise<void>; close: () => Promise<void>; reopen: (base: string) => Promise<void>;
  top: () => Promise<Top>; putAtTop: (t: string) => Promise<void>; recent: () => Promise<any[]>;
};
async function inBrowser(t: any, body: (h: H) => Promise<void>): Promise<void> {
  if (!pw) { t.skip("playwright is not installed under vscode-extension: the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw.chromium.launch(); }
  catch (e) { t.skip("no playwright browser on this box, and the browser leg needs one (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  const errors: string[] = [];
  const docs: Record<string, string> = { [REPORT]: LONG, [NOTES]: NOTES_TEXT };
  const mtime = { v: MT };
  const holds: Record<string, Hold> = {};   // by the picture's path: a leg holds two figures and releases them one at a time
  const hold = (p: string): (() => void) => {
    let release = (): void => { /* set by the promise */ };
    const wait = new Promise<void>((r) => { release = r; });
    const hd: Hold = { on: true, wait, release };
    holds[p] = hd;
    return () => { hd.on = false; hd.release(); };
  };
  try {
    const filesJs = filesBundle();
    const ctx = await browser.newContext({ viewport: { width: 900, height: 520 } });
    const page = await ctx.newPage();
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    await ctx.route("http://romp.test/**", async (route: any) => {
      const u = new URL(route.request().url());
      if (u.pathname === "/files") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: PAGE });
      if (u.pathname === "/dist/files.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: filesJs });
      if (u.pathname === "/file") {
        const p = u.searchParams.get("path") || "";
        const text = docs[p];
        if (text === undefined) return route.fulfill({ status: 404, contentType: "text/plain", body: "no such file: " + p });
        if (/\.svg$/i.test(p)) {   // a picture a note shows: image/svg+xml with no text header, never cached (the kernel sends no-cache), held while the test says so
          const hd = holds[p]; if (hd && hd.on) await hd.wait;
          return route.fulfill({ status: 200, contentType: "image/svg+xml", headers: { "X-Romp-Mtime-Ns": mtime.v, "Cache-Control": "no-store" }, body: text });
        }
        if (route.request().method() === "HEAD") return route.fulfill({ status: 200, headers: { "X-Romp-Mtime-Ns": mtime.v, "Last-Modified": "Sat, 06 Sep 2025 08:00:00 GMT" }, body: "" });
        return route.fulfill({ status: 200, contentType: "text/plain; charset=utf-8", headers: { "X-Romp-Mtime-Ns": mtime.v, "X-Romp-Text-Utf8": "1" }, body: text });
      }
      return route.fulfill({ status: 404, body: "" });
    });
    await page.goto("http://romp.test/files");
    await page.waitForFunction(() => (window as any).__posts.some((m: any) => m && m.type === "ready"));
    const frames = (n = 2) => page.evaluate((k: number) => new Promise<null>((r) => { const f = () => (k-- <= 0 ? r(null) : requestAnimationFrame(f)); f(); }), n);
    const painted = async (p: string) => {
      await page.locator("#romp-fileview .fileview-base", { hasText: p.slice(p.lastIndexOf("/") + 1) }).waitFor({ timeout: 10000 });
      await page.locator("#romp-fileview .fileview-md > p").first().waitFor({ timeout: 10000 });
      await frames(3);
    };
    const open = async (p: string) => {   // the shell's relay, as a chat click reaches this pane
      await page.evaluate(([p, sid]: string[]) => { window.postMessage({ romp: "viewFile", path: p, sid }, "*"); }, [p, SID]);
      await painted(p);
    };
    const close = async () => {
      await page.click("#romp-fileview .fileview-close");
      await page.waitForFunction(() => !document.getElementById("romp-fileview"), null, { timeout: 5000 });
      await page.locator("#files-empty .fs-row").first().waitFor({ timeout: 5000 });
    };
    const reopen = async (base: string) => {   // the Recent row's click
      await page.locator("#files-empty .fs-row", { hasText: base }).first().click();
      await painted(base);
    };
    const top = (): Promise<Top> => page.evaluate(() => (window as any).topBlock());
    const putAtTop = async (t: string) => { await page.evaluate((t: string) => (window as any).putAtTop(t), t); await frames(1); };
    const recent = () => page.evaluate(() => JSON.parse(localStorage.getItem("romp:files-recent") || "[]"));
    await body({ page, docs, mtime, hold, open, close, reopen, top, putAtTop, recent });
    assert.deepEqual(errors, [], "no page errors");
    await ctx.close();
  } finally {
    await browser.close();
  }
}
const near = (a: number, b: number, tol = 1) => Math.abs(a - b) <= tol;

test("in a browser: a note reopened from Recent returns to its block and its scrollTop; the row's record holds spans and pixels, never text; a change below the block keeps the seat, a change above falls to the clamped scrollTop; the record survives a page reload, and the relay's open after it returns to the block and keeps the record", async (t) => {
  await inBrowser(t, async (h) => {
    await h.open(REPORT);
    assert.equal((await h.top())!.scrollTop, 0, "a first open starts at the top");
    await h.putAtTop("Paragraph 40");
    const before = (await h.top())!;
    assert.equal(before.text.slice(0, 13), "Paragraph 40:"); assert.ok(before.scrollTop > 500, "block 40 is well down the note: " + before.scrollTop);
    await h.close();
    // the row's record, as localStorage holds it
    const rows = await h.recent();
    assert.equal(rows.length, 1); assert.equal(rows[0].path, REPORT);
    const rec = rows[0].place;
    assert.ok(rec && typeof rec.start === "number" && rec.end > rec.start, "a source span: " + JSON.stringify(rec));
    assert.equal(rec.view, "rendered"); assert.equal(rec.mtimeNs, MT); assert.equal(rec.atTop, false);
    assert.ok(near(rec.scrollTop, before.scrollTop), "the numeric scrollTop: " + rec.scrollTop + " vs " + before.scrollTop);
    assert.deepEqual(Object.keys(rec).sort(), ["atTop", "end", "mtimeNs", "scrollTop", "start", "t", "top", "view"], "the eight fields; a note with no fold records no fold state (the ninth field, `folds`, is a Rendered read's of a note with one: file-view-place-memory-fold-browser.test.ts; review round 3)");
    assert.doesNotMatch(JSON.stringify(rows), /Paragraph|lorem|ipsum/, "no word of the note in the store");
    // ── the acceptance: the row's click returns to the block, scrollTop within a pixel
    await h.reopen("report.md");
    let now = (await h.top())!;
    assert.equal(now.text.slice(0, 13), "Paragraph 40:", "the same block is at the top: " + JSON.stringify(now));
    assert.ok(near(now.scrollTop, before.scrollTop), "scrollTop " + now.scrollTop + " vs " + before.scrollTop);
    await h.close();
    // ── the note changed BELOW the block (paragraph 80 rewritten, a new mtime): the span is still a block, the same seat
    h.docs[REPORT] = rewritten(80); h.mtime.v = MT2;
    await h.reopen("report.md");
    now = (await h.top())!;
    assert.equal(now.text.slice(0, 13), "Paragraph 40:", "a change below the block leaves the block where it was: " + JSON.stringify(now));
    assert.ok(near(now.scrollTop, before.scrollTop));
    await h.close();
    const rec2 = (await h.recent())[0].place;
    assert.equal(rec2.mtimeNs, MT2, "the leave re-recorded the place against the new mtime");
    // ── the note changed ABOVE the block (twenty paragraphs inserted under the heading): the span names no block of the
    // new text, the old text is not kept, so the numeric scrollTop is written and clamped (the brief's design, item 3)
    h.docs[REPORT] = LONG2; h.mtime.v = "1757145600000000011";
    await h.reopen("report.md");
    now = (await h.top())!;
    assert.ok(near(now.scrollTop, before.scrollTop, 2), "the clamped scrollTop stands in: " + JSON.stringify(now) + " vs " + before.scrollTop);
    assert.notEqual(now.text.slice(0, 13), "Paragraph 40:", "…and the block under the eye is the one at that pixel now, not block 40 (the record holds no text to find it by)");
    await h.close();
    // ── a page reload: localStorage survives (the row's record is the pre-reload one), and the FIRST open after it is the
    // shell's relay, a chat click on the same path (the routine order on a kernel restart, which reloads the panes): the
    // viewer's in-page map is empty, so the row's record seats the block, and the relay open's close keeps the record on
    // the row (the Slice 6 review, round 1: with the row's click alone handing the place back, the relay opened the note
    // at the top and its leave wrote the top over the row, so the row's own click then landed at the top as well)
    h.docs[REPORT] = LONG; h.mtime.v = MT;
    await h.reopen("report.md"); await h.putAtTop("Paragraph 40"); const again = (await h.top())!; await h.close();
    const stored = (await h.recent())[0].place;
    await h.page.reload();
    await h.page.waitForFunction(() => (window as any).__posts.some((m: any) => m && m.type === "ready"));
    await h.page.locator("#files-empty .fs-row").first().waitFor({ timeout: 5000 });
    assert.deepEqual((await h.recent())[0].place, stored, "the record survives the reload as it was");
    await h.open(REPORT);                                            // the relay, not the row
    now = (await h.top())!;
    assert.equal(now.text.slice(0, 13), "Paragraph 40:", "after a reload, the relay's open returns to the block: " + JSON.stringify(now));
    assert.ok(near(now.scrollTop, again.scrollTop), "scrollTop " + now.scrollTop + " vs " + again.scrollTop);
    await h.close();
    const kept = (await h.recent())[0].place;
    assert.equal(kept.start, stored.start, "the relay open's close keeps block 40 on the row: " + JSON.stringify(kept));
    assert.equal(kept.atTop, false); assert.ok(near(kept.scrollTop, again.scrollTop));
    // …and the row's click after that lands there as well
    await h.reopen("report.md");
    now = (await h.top())!;
    assert.equal(now.text.slice(0, 13), "Paragraph 40:", "the row's click after the relay: " + JSON.stringify(now));
    assert.ok(near(now.scrollTop, again.scrollTop));
    await h.close();
  });
});

test("in a browser: a second note opened OVER the first writes the first's place (the replace path); both rows return to theirs; a relay re-open with no row's record still returns to the block (the viewer's own in-page memory)", async (t) => {
  await inBrowser(t, async (h) => {
    await h.open(REPORT); await h.putAtTop("Paragraph 40"); const a = (await h.top())!;
    await h.open(NOTES);                                          // the relay again: a replace-open over the report
    assert.equal((await h.top())!.scrollTop, 0, "the second note starts at its top");
    await h.putAtTop("Note 20"); const b = (await h.top())!;
    await h.close();
    const rows = await h.recent();
    assert.deepEqual(rows.map((r: any) => r.path), [NOTES, REPORT], "both rows, newest first");
    assert.ok(rows[1].place && near(rows[1].place.scrollTop, a.scrollTop), "the report's place was written when the notes replaced it: " + JSON.stringify(rows[1].place));
    assert.ok(rows[0].place && near(rows[0].place.scrollTop, b.scrollTop), "the notes' place at the close");
    await h.reopen("report.md");
    let now = (await h.top())!;
    assert.equal(now.text.slice(0, 13), "Paragraph 40:"); assert.ok(near(now.scrollTop, a.scrollTop));
    await h.close();
    await h.reopen("notes.md");
    now = (await h.top())!;
    assert.equal(now.text.slice(0, 8), "Note 20:"); assert.ok(near(now.scrollTop, b.scrollTop));
    await h.close();
    // the shell's relay opens the report again, passing no place: the viewer's module memory for this page's lifetime seats it
    await h.open(REPORT);
    now = (await h.top())!;
    assert.equal(now.text.slice(0, 13), "Paragraph 40:", "the in-page memory: " + JSON.stringify(now));
    assert.ok(near(now.scrollTop, a.scrollTop));
    await h.close();
  });
});

// A picture above the passage that loads after the seat (review round 3; the round 2 refuter's measurement). After a page reload
// the note's pictures are fetched anew and have no height at the first paint, so the record's numeric scrollTop, written over the
// shorter layout, selected the block that sat at that pixel there, and Chromium's scroll anchoring then kept THAT block in view
// as the picture grew the layout: the body ended a picture's height past the record. The viewer now writes the seat again at the
// picture's load while the body stands where the seat and the browser's adjustment left it (file-view.ts armReseat). The re-seat
// is retired by the reader's own scroll (the guard: the body no longer stands where the seat left it), by the next text paint and
// by the close (review round 4: the two the page can show, a second figure released after the reader scrolled on and after a
// Rendered/Raw round trip, each leaving the block at the top where it was and the record's number written back nowhere; the
// close discards the body with the listener, so nothing of it can show).
test("in a browser (review round 3): a note with two figures above the passage, changed above the passage and reopened from Recent after a page reload with the figures still in flight: the numeric seat lands over the short layout, and the first figure's load seats the record's scrollTop again, so the body ends at the record's number with the block that sits there in the full layout (before: a figure's height past the record, the short layout's block carried along by scroll anchoring); (review round 4) the reader then scrolls on, and the second figure's load moves nothing: the reader's block stays at the top and the record's number is not written back; after a second reload the figures held again, a Rendered/Raw round trip before their loads ends the re-seat: the paint's own seat stands and the record's number is not written back", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (h) => {
    const FIG = ROOT + "/docs/figure.svg", FIG2 = ROOT + "/docs/figure2.svg";
    const SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="600" height="400" viewBox="0 0 600 400"><rect width="600" height="400" fill="#888"/></svg>';
    const BODY_PARAS = Array.from({ length: 140 }, (_, i) => PARA(i + 1)).join("\n\n") + "\n";
    const FIGS = "![late figure](figure.svg)\n\n![second late figure](figure2.svg)\n\n";
    const inserted = (n: number): string => Array.from({ length: n }, (_, i) => `Inserted ${i + 1}: new text a session wrote above the figures and the reader's place, long enough to wrap in the pane.`).join("\n\n") + "\n\n";
    const FIG_DOC = "# Report\n\n" + FIGS + BODY_PARAS;
    const FIG_CHANGED = "# Report\n\n" + inserted(20) + FIGS + BODY_PARAS;
    const FIG_CHANGED2 = "# Report\n\n" + inserted(5) + FIGS + BODY_PARAS;   // fewer above the passage than the record's twenty and two figures: the block at the record's pixel is a later one
    const MT3 = "1757145600000000021";
    h.docs[FIG] = SVG; h.docs[FIG2] = SVG; h.docs[REPORT] = FIG_DOC;
    const imgsDone = (n: number) => h.page.waitForFunction((k: number) => {
      const is = Array.from(document.querySelectorAll("#romp-fileview .fileview-md img")) as HTMLImageElement[];
      return is.length === 2 && is.filter((i) => i.complete && i.naturalHeight > 0).length === k;
    }, n, { timeout: 10000 });
    const imgState = (): Promise<{ complete: boolean[]; heights: number[]; scrollHeight: number }> => h.page.evaluate(() => {
      const is = Array.from(document.querySelectorAll("#romp-fileview .fileview-md img")) as HTMLImageElement[]; const b = document.querySelector("#romp-fileview .fileview-body") as HTMLElement;
      return { complete: is.map((i) => i.complete), heights: is.map((i) => i.getBoundingClientRect().height), scrollHeight: b.scrollHeight };
    });
    const twoFrames = () => h.page.evaluate(() => new Promise<null>((r) => requestAnimationFrame(() => requestAnimationFrame(() => r(null)))));
    const reloaded = async () => {
      await h.page.reload();
      await h.page.waitForFunction(() => (window as any).__posts.some((m: any) => m && m.type === "ready"));
      await h.page.locator("#files-empty .fs-row").first().waitFor({ timeout: 5000 });
    };
    const n = (s: string): number => { const m = /Paragraph (\d+)/.exec(s); return m ? Number(m[1]) : 0; };
    await h.open(REPORT); await imgsDone(2);
    await h.putAtTop("Paragraph 65"); await twoFrames();
    const before = (await h.top())!;
    assert.equal(before.text.slice(0, 13), "Paragraph 65:");
    const full = await imgState(); assert.ok(full.heights.every((x) => x >= 300), "the figures have their height in the layout the record is read over: " + full.heights);
    await h.close();
    const rec = (await h.recent())[0].place;
    assert.ok(rec && near(rec.scrollTop, before.scrollTop), "the record's scrollTop: " + JSON.stringify(rec) + " vs " + before.scrollTop);
    // a page reload: the pictures are fetched anew; the note changed ABOVE the passage, so the span is no block of the new text and the numeric scrollTop is what seats
    await reloaded();
    h.docs[REPORT] = FIG_CHANGED; h.mtime.v = MT2;
    const release1 = h.hold(FIG), release2 = h.hold(FIG2);
    await h.reopen("report.md");
    const landed = (await h.top())!; const short = await imgState();
    assert.deepEqual(short.complete, [false, false], "the figures are still in flight at the landing");
    assert.ok(short.heights.every((x) => x < 50), "…with no height in the layout yet: " + short.heights);
    assert.ok(near(landed.scrollTop, rec.scrollTop), "the numeric seat wrote the record's number over the short layout: " + landed.scrollTop + " vs " + rec.scrollTop);
    release1();
    await imgsDone(1); await twoFrames();
    const after = (await h.top())!; const grown = await imgState();
    assert.ok(grown.scrollHeight > short.scrollHeight + 300, "the first figure's load grew the layout: " + short.scrollHeight + " -> " + grown.scrollHeight);
    assert.ok(near(after.scrollTop, rec.scrollTop), "the body ends at the record's number (before the fix: the number plus the figure's height; read " + after.scrollTop + " for " + rec.scrollTop + ")");
    assert.ok(n(after.text) > 0 && n(after.text) < n(landed.text), "the block at that pixel in the full layout comes before the short layout's (before: the short layout's block, carried along by scroll anchoring): " + landed.text + " -> " + after.text);
    // ── (review round 4) the reader's own scroll retires the re-seat: the second figure's load, with the body no longer standing where
    // the seat left it, writes nothing; the block the reader put at the top stays there (the browser's anchoring carries it as the
    // figure grows the layout above), and the record's number is not written back
    await h.page.evaluate(() => { (document.querySelector("#romp-fileview .fileview-body") as HTMLElement).scrollTop += 400; }); await twoFrames();
    const moved = (await h.top())!;
    assert.ok(moved.scrollTop > rec.scrollTop + 300 && moved.text !== after.text, "the premise: the reader's scroll took the body off the seat: " + JSON.stringify(moved) + " from " + JSON.stringify(after));
    release2();
    await imgsDone(2); await twoFrames();
    const stayed = (await h.top())!; const grown2 = await imgState();
    assert.ok(grown2.scrollHeight > grown.scrollHeight + 300, "the second figure's load grew the layout: " + grown.scrollHeight + " -> " + grown2.scrollHeight);
    assert.equal(stayed.text, moved.text, "the block the reader put at the top is still there after the second figure's load (a re-seat the scroll did not retire writes the record's number back and shows the block at that pixel; scrollTop " + stayed.scrollTop + ", the record's " + rec.scrollTop + ")");
    assert.ok(!near(stayed.scrollTop, rec.scrollTop, 2), "the record's scrollTop was not written back over the reader's scroll: " + stayed.scrollTop + " vs " + rec.scrollTop);
    await h.close();
    const rec2 = (await h.recent())[0].place;
    assert.equal(rec2.mtimeNs, MT2, "the leave wrote the reader's place at the changed note's mtime");
    assert.ok(near(rec2.scrollTop, stayed.scrollTop), "…where the reader left it: " + rec2.scrollTop + " vs " + stayed.scrollTop);
    // ── (review round 4) the next text paint retires it: a second reload, the note changed above the passage again (five inserted
    // paragraphs for twenty: the span is no block of the new text, the numeric scrollTop seats, a later block at the top), both
    // figures held; a Rendered/Raw round trip before their loads is two paints, each with its own seat (the same block back at the
    // top edge); the figures' loads then leave that block where the paint put it, the record's number written back nowhere
    await reloaded();
    h.docs[REPORT] = FIG_CHANGED2; h.mtime.v = MT3;
    const release3 = h.hold(FIG), release4 = h.hold(FIG2);
    await h.reopen("report.md");
    const landed2 = (await h.top())!; const short2 = await imgState();
    assert.deepEqual(short2.complete, [false, false], "the figures are in flight at the second landing");
    assert.ok(near(landed2.scrollTop, rec2.scrollTop), "the numeric seat again: " + landed2.scrollTop + " vs " + rec2.scrollTop);
    assert.ok(n(landed2.text) > n(stayed.text) + 5, "the premise: the record's block is no block of the new text, so the pixel selects a later block over the shorter layout: " + landed2.text + " for " + stayed.text);
    await h.page.locator("#romp-fileview .fileview-btn", { hasText: "Raw" }).click();
    await h.page.locator("#romp-fileview .fileview-body code.hljs").waitFor({ timeout: 10000 }); await twoFrames();
    await h.page.locator("#romp-fileview .fileview-btn", { hasText: "Rendered" }).click();
    await h.page.locator("#romp-fileview .fileview-md > p").first().waitFor({ timeout: 10000 }); await twoFrames();
    const tripped = (await h.top())!; const short3 = await imgState();
    assert.equal(tripped.text, landed2.text, "the round trip's own place-keeping: the block at the top before it is at the top after it: " + JSON.stringify(tripped) + " for " + JSON.stringify(landed2));
    assert.deepEqual(short3.complete, [false, false], "the round trip's new pictures are still in flight");
    release3(); release4();
    await imgsDone(2); await twoFrames();
    const settled = (await h.top())!; const grown3 = await imgState();
    assert.ok(grown3.scrollHeight > short3.scrollHeight + 700, "both figures' loads grew the layout: " + short3.scrollHeight + " -> " + grown3.scrollHeight);
    assert.equal(settled.text, tripped.text, "the paint retired the re-seat: the figures' loads leave the block the paint seated at the top (a re-seat the paint did not retire writes the record's number back and shows an earlier block; scrollTop " + settled.scrollTop + ", the record's " + rec2.scrollTop + ")");
    assert.ok(!near(settled.scrollTop, rec2.scrollTop, 2), "the record's scrollTop is not written back after the round trip: " + settled.scrollTop + " vs " + rec2.scrollTop);
    await h.close();
  });
});

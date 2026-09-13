// A note reopened from Recent returns to its place, in a browser (Slice 6 of plans/markdown-viewer.md, item 3): the
// real Files page (files.ts, the shared viewer, the Recent list) in headless Chromium. Open a long note, put block 40
// at the top, close the viewer: the viewer hands the pane the reader's place (file-view.ts RememberedPlace through
// initFileView's onLeave), the pane writes it on the note's Recent row (files-recent.ts placeRecent), and the row's
// click hands it back (openFileView's `place`), so the same block is at the top and the body's scrollTop is the
// pre-close value within a pixel (the plan's acceptance). Then the note rewritten below the block (the span is still a
// block of the text: the same seat), rewritten above it (the span is no block of the new text: the numeric scrollTop,
// clamped), a page reload (localStorage survives), a second note opened OVER the first (the replace path writes the
// first's place; both rows hold theirs), and a relay re-open with no row (the viewer's own in-page memory). The
// record holds no text: its JSON in localStorage names no word of the note. Skips LOUDLY without a playwright
// browser (CI installs none). Synthetic values only: the notes-api world, a placeholder session id, invented notes.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { LONG, LONG2, rewritten, MT, MT2 } from "./real-viewer-leg";

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
type H = {
  page: any; docs: Record<string, string>; mtime: { v: string };
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
  try {
    const filesJs = filesBundle();
    const ctx = await browser.newContext({ viewport: { width: 900, height: 520 } });
    const page = await ctx.newPage();
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    await ctx.route("http://romp.test/**", (route: any) => {
      const u = new URL(route.request().url());
      if (u.pathname === "/files") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: PAGE });
      if (u.pathname === "/dist/files.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: filesJs });
      if (u.pathname === "/file") {
        const p = u.searchParams.get("path") || "";
        const text = docs[p];
        if (text === undefined) return route.fulfill({ status: 404, contentType: "text/plain", body: "no such file: " + p });
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
    await body({ page, docs, mtime, open, close, reopen, top, putAtTop, recent });
    assert.deepEqual(errors, [], "no page errors");
    await ctx.close();
  } finally {
    await browser.close();
  }
}
const near = (a: number, b: number, tol = 1) => Math.abs(a - b) <= tol;

test("in a browser: a note reopened from Recent returns to its block and its scrollTop; the row's record holds spans and pixels, never text; a change below the block keeps the seat, a change above falls to the clamped scrollTop; the record survives a page reload", async (t) => {
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
    assert.deepEqual(Object.keys(rec).sort(), ["atTop", "end", "mtimeNs", "scrollTop", "start", "t", "top", "view"]);
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
    // ── a page reload: localStorage survives, the row reopens to the block (the note back as it was)
    h.docs[REPORT] = LONG; h.mtime.v = MT;
    await h.reopen("report.md"); await h.putAtTop("Paragraph 40"); const again = (await h.top())!; await h.close();
    await h.page.reload();
    await h.page.waitForFunction(() => (window as any).__posts.some((m: any) => m && m.type === "ready"));
    await h.page.locator("#files-empty .fs-row").first().waitFor({ timeout: 5000 });
    await h.reopen("report.md");
    now = (await h.top())!;
    assert.equal(now.text.slice(0, 13), "Paragraph 40:", "after a reload: " + JSON.stringify(now));
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

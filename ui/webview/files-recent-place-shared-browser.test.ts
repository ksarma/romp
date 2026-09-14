// Two sessions naming one absolute path, in a browser (Slice 6 of plans/markdown-viewer.md, item 3; the review's round 5): the
// real Files page (files.ts, the shared viewer, the Recent list) in headless Chromium. The Recent rows are per path + session;
// the viewer's in-page memory is per FILE (file-view.ts placeKey: an absolute or `~` path is one file for every session that
// names it, the review's round 2), so in one page a second session's open of the same absolute path lands at the first's place
// and either session's row lands at the file's latest place. A page reload empties that memory and leaves the rows, and with
// the open's own row alone read the same row then landed at its session's older place: two rows reading the same path, one
// landing at Paragraph 60 and the other at Paragraph 20, and the landing of one row depending on whether the page had reloaded.
// The pane now reads the later record among the rows the viewer's rule says name one file (files-recent.ts latestPlace over
// placeKey), so after a reload either row lands where the file was last read, as before one. A relative path stays a file per
// session (the kernel resolves it against the session's cwd): each session's row keeps its own place across the reload. Skips
// LOUDLY without a playwright browser (CI installs none). Synthetic values only: the notes-api world, placeholder session ids,
// invented notes; the store holds no word of the note.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { LONG, MT } from "./real-viewer-leg";

const EXT = process.cwd();                                        // npm test runs in vscode-extension
const requireCjs = createRequire(path.join(EXT, "package.json"));
const UI = path.resolve(EXT, "..", "ui", "webview");
const SID_A = "11111111-2222-3333-4444-555555555555";
const SID_B = "22222222-3333-4444-5555-666666666666";
const WEB = { name: "web", color: { bg: "#224466", fg: "#ffffff" } };   // what the shell's relay carries for a chat click (render.ts openPath)
const API = { name: "api", color: { bg: "#664422", fg: "#ffffff" } };
const REPORT = "/repo/notes-api/docs/report.md";
const REL = "docs/report.md";                                     // the same spelling in two sessions: two files (the kernel resolves it per session)

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
// the top-visible block of the Rendered view: its first characters and the body's scrollTop
window.topBlock = function () {
  var body = document.querySelector("#romp-fileview .fileview-body"); if (!body) return null; var br = body.getBoundingClientRect();
  var els = Array.prototype.slice.call(body.querySelectorAll(".fileview-md > *"));
  for (var i = 0; i < els.length; i++) { var r = els[i].getBoundingClientRect(); if (r.bottom > br.top + 0.5) return { text: (els[i].textContent || "").trim().slice(0, 13), scrollTop: body.scrollTop }; }
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

type Top = { text: string; scrollTop: number } | null;
type Identity = { name: string; color: { bg: string; fg: string } };
type Row = { sid: string | null; path: string; chip: string | null; scrollTop: number | null; start: number | null; t: number | null };
type H = {
  open: (p: string, sid: string, identity: Identity) => Promise<void>;   // the shell's relay: a chat click in that session
  clickRow: (p: string, sid: string) => Promise<void>;                   // the Recent row for the path and the session
  close: () => Promise<void>; reload: () => Promise<void>;
  top: () => Promise<Top>; putAtTop: (t: string) => Promise<void>;
  rows: () => Promise<Row[]>; shown: () => Promise<{ path: string; chip: string | null }[]>; store: () => Promise<string>;
};
async function inBrowser(t: any, body: (h: H) => Promise<void>): Promise<void> {
  if (!pw) { t.skip("playwright is not installed under vscode-extension: the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw.chromium.launch(); }
  catch (e) { t.skip("no playwright browser on this box, and the browser leg needs one (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  const errors: string[] = [];
  const docs: Record<string, string> = { [REPORT]: LONG, [REL]: LONG };
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
        if (route.request().method() === "HEAD") return route.fulfill({ status: 200, headers: { "X-Romp-Mtime-Ns": MT, "Last-Modified": "Sat, 06 Sep 2025 08:00:00 GMT" }, body: "" });
        return route.fulfill({ status: 200, contentType: "text/plain; charset=utf-8", headers: { "X-Romp-Mtime-Ns": MT, "X-Romp-Text-Utf8": "1" }, body: text });
      }
      return route.fulfill({ status: 404, body: "" });
    });
    const ready = async () => { await page.waitForFunction(() => (window as any).__posts.some((m: any) => m && m.type === "ready")); };
    const frames = (n = 2) => page.evaluate((k: number) => new Promise<null>((r) => { const f = () => (k-- <= 0 ? r(null) : requestAnimationFrame(f)); f(); }), n);
    const painted = async (p: string) => {
      await page.locator("#romp-fileview .fileview-base", { hasText: p.slice(p.lastIndexOf("/") + 1) }).waitFor({ timeout: 10000 });
      await page.locator("#romp-fileview .fileview-md > p").first().waitFor({ timeout: 10000 });
      await frames(3);
    };
    await page.goto("http://romp.test/files");
    await ready();
    const open = async (p: string, sid: string, identity: Identity) => {
      await page.evaluate(([p, sid, id]: any[]) => { window.postMessage({ romp: "viewFile", path: p, sid, identity: id }, "*"); }, [p, sid, identity]);
      await painted(p);
    };
    const rowsRaw = () => page.evaluate(() => JSON.parse(localStorage.getItem("romp:files-recent") || "[]"));
    const clickRow = async (p: string, sid: string) => {   // the rows are painted in the store's order, data-i by index (files.ts paint)
      const i = (await rowsRaw()).findIndex((r: any) => r.path === p && r.sid === sid);
      assert.ok(i >= 0, "a row for " + p + " in session " + sid.slice(0, 8));
      await page.locator(`#files-empty .fs-row[data-i="${i}"]`).click();
      await painted(p);
    };
    const close = async () => {
      await page.click("#romp-fileview .fileview-close");
      await page.waitForFunction(() => !document.getElementById("romp-fileview"), null, { timeout: 5000 });
      await page.locator("#files-empty .fs-row").first().waitFor({ timeout: 5000 });
    };
    const reload = async () => {   // the routine order on a kernel restart, which reloads the panes: localStorage survives, the viewer's in-page memory does not
      await page.reload();
      await ready();
      await page.locator("#files-empty .fs-row").first().waitFor({ timeout: 5000 });
    };
    const top = (): Promise<Top> => page.evaluate(() => (window as any).topBlock());
    const putAtTop = async (t: string) => { await page.evaluate((t: string) => (window as any).putAtTop(t), t); await frames(1); };
    const rows = async (): Promise<Row[]> => (await rowsRaw()).map((r: any) => ({ sid: r.sid, path: r.path, chip: r.identity ? r.identity.name : null,
      scrollTop: r.place ? r.place.scrollTop : null, start: r.place ? r.place.start : null, t: r.place ? r.place.t : null }));
    const shown = () => page.evaluate(() => Array.from(document.querySelectorAll("#files-empty .fs-row")).map((r) => ({
      path: (r.querySelector(".fileview-name") as HTMLElement).textContent || "", chip: (r.querySelector(".fileview-sess") as HTMLElement | null)?.textContent ?? null })));
    const store = () => page.evaluate(() => localStorage.getItem("romp:files-recent") || "");
    await body({ open, clickRow, close, reload, top, putAtTop, rows, shown, store });
    assert.deepEqual(errors, [], "no page errors");
    await ctx.close();
  } finally {
    await browser.close();
  }
}
const near = (a: number, b: number, tol = 1) => Math.abs(a - b) <= tol;
const head = (t: Top) => (t ? t.text : "(no body)");

test("in a browser (review round 5): two sessions read one absolute path; after a page reload either session's Recent row lands where the file was last read, as it does before one; a relative path stays a file per session", { timeout: 300000 }, async (t) => {
  await inBrowser(t, async (h) => {
    // session A reads the report to Paragraph 20 and closes; a chat click in session B opens the same absolute path
    await h.open(REPORT, SID_A, WEB);
    assert.equal((await h.top())!.scrollTop, 0, "a first open starts at the top");
    await h.putAtTop("Paragraph 20"); const a20 = (await h.top())!; assert.equal(a20.text, "Paragraph 20:");
    await h.close();
    await h.open(REPORT, SID_B, API);
    let now = await h.top();
    assert.equal(head(now), "Paragraph 20:", "in one page the second session lands at the first's place: an absolute path is one file for every session (the viewer's placeKey)");
    await h.putAtTop("Paragraph 60"); const b60 = (await h.top())!; assert.equal(b60.text, "Paragraph 60:"); assert.ok(b60.scrollTop > a20.scrollTop + 500);
    await h.close();
    // two rows for one path, each with its session's record, both reading the same path with their chips telling them apart
    let rows = await h.rows();
    assert.deepEqual(rows.map((r) => [r.path, r.sid, r.chip]), [[REPORT, SID_B, "api"], [REPORT, SID_A, "web"]], "one row per path + session, newest first");
    assert.ok(near(rows[0].scrollTop!, b60.scrollTop) && near(rows[1].scrollTop!, a20.scrollTop), "each row holds its own session's record: " + JSON.stringify(rows));
    assert.ok(rows[0].t! > rows[1].t!, "the second session's record is the later");
    assert.doesNotMatch(await h.store(), /Paragraph|lorem|ipsum/, "no word of the note in the store");
    // ── the same page: session A's row lands at the file's latest place (the in-page memory's shared key; unchanged)
    await h.clickRow(REPORT, SID_A);
    now = await h.top();
    assert.equal(head(now), "Paragraph 60:", "before a reload, A's row lands where the file was last read: " + JSON.stringify(now));
    assert.ok(near(now!.scrollTop, b60.scrollTop));
    await h.close();
    // A's leave wrote the file's place on A's row too; put A's own record back to Paragraph 20 for the reload scene by reading there
    await h.clickRow(REPORT, SID_A); await h.putAtTop("Paragraph 20"); await h.close();
    rows = await h.rows();
    assert.ok(near(rows.find((r) => r.sid === SID_A)!.scrollTop!, a20.scrollTop) && near(rows.find((r) => r.sid === SID_B)!.scrollTop!, b60.scrollTop), "A's row at 20 again, B's at 60: " + JSON.stringify(rows));
    assert.ok(rows.find((r) => r.sid === SID_A)!.t! > rows.find((r) => r.sid === SID_B)!.t!, "…and A's record is now the later one");
    await h.clickRow(REPORT, SID_B);
    now = await h.top();
    assert.equal(head(now), "Paragraph 20:", "in the same page, B's row lands at the file's latest place, A's Paragraph 20: " + JSON.stringify(now));
    await h.putAtTop("Paragraph 60"); await h.close();   // B back to 60, the later record once more
    rows = await h.rows();
    assert.ok(rows.find((r) => r.sid === SID_B)!.t! > rows.find((r) => r.sid === SID_A)!.t!);
    // ── a page reload: the viewer's in-page memory is empty, the two rows stand. With the open's own row alone read, A's row
    // landed at its Paragraph 20 here while the identical click landed at Paragraph 60 before the reload (the finding). The pane
    // reads the later record among the rows for the FILE, so A's row lands at Paragraph 60 after the reload as before it.
    await h.reload();
    const shown = await h.shown();
    assert.deepEqual(shown.map((r) => r.path), [REPORT, REPORT], "two rows reading the same path");
    assert.deepEqual(shown.map((r) => r.chip), ["api", "web"], "…told apart by their session chips");
    assert.deepEqual((await h.rows()).map((r) => r.sid), [SID_B, SID_A], "the rows survive the reload as they were");
    await h.clickRow(REPORT, SID_A);
    now = await h.top();
    assert.equal(head(now), "Paragraph 60:", "after a reload, A's row lands where the file was last read (B's Paragraph 60), as it did before the reload: " + JSON.stringify(now));
    assert.ok(near(now!.scrollTop, b60.scrollTop), "scrollTop " + now!.scrollTop + " vs " + b60.scrollTop);
    await h.close();
    await h.clickRow(REPORT, SID_B);
    now = await h.top();
    assert.equal(head(now), "Paragraph 60:", "B's row after A's post-reload read and close: still the file's latest place: " + JSON.stringify(now));
    // A reads on to Paragraph 80 and closes: B's row follows in the same page and after another reload alike
    await h.close();
    await h.clickRow(REPORT, SID_A); await h.putAtTop("Paragraph 80"); const a80 = (await h.top())!; await h.close();
    await h.clickRow(REPORT, SID_B);
    now = await h.top();
    assert.equal(head(now), "Paragraph 80:", "the same page: B's row lands at A's later read: " + JSON.stringify(now));
    await h.close();
    await h.reload();
    await h.clickRow(REPORT, SID_B);
    now = await h.top();
    assert.equal(head(now), "Paragraph 80:", "after a reload: the same landing: " + JSON.stringify(now));
    assert.ok(near(now!.scrollTop, a80.scrollTop));
    await h.close();
    rows = await h.rows();
    assert.deepEqual(rows.map((r) => [r.path, r.sid]), [[REPORT, SID_B], [REPORT, SID_A]], "still one row per path + session: the read joins the rows, the write does not");
    // ── a RELATIVE path is a file per session: session A reads its docs/report.md to Paragraph 30, session B's docs/report.md
    // opens at the top (another file), and after a reload each session's row keeps its own place
    await h.open(REL, SID_A, WEB); await h.putAtTop("Paragraph 30"); const a30 = (await h.top())!; await h.close();
    await h.open(REL, SID_B, API);
    now = await h.top();
    assert.equal(now!.scrollTop, 0, "another session's relative path is another file: the top, not A's place: " + JSON.stringify(now));
    await h.close();
    await h.reload();
    await h.clickRow(REL, SID_A);
    now = await h.top();
    assert.equal(head(now), "Paragraph 30:", "A's relative row after the reload: A's own place: " + JSON.stringify(now));
    assert.ok(near(now!.scrollTop, a30.scrollTop));
    await h.close();
    await h.clickRow(REL, SID_B);
    now = await h.top();
    assert.equal(now!.scrollTop, 0, "B's relative row after the reload: B's own place, the top, not A's Paragraph 30: " + JSON.stringify(now));
    await h.close();
    assert.equal((await h.rows()).length, 4, "four rows: two files' worth for the relative spelling, one file's two rows for the absolute one");
  });
});

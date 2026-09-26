// A picture opened from a figure takes no Recent row (plans/markdown-viewer.md, "Follow-on: Link navigation", L3; the file
// review, regression-1): headless Chromium boots the real Files page (files.ts: the shared viewer, the pane's own opener and
// its Recent list of eight rows), opens a synthetic report holding a figure and a link, and reads the Recent rows off
// localStorage after each open. Before: every figure open, from the control and from the plain click, went through the pane's
// opener (files.ts openHere) and minted a row for the picture, so eight figures opened in one report evicted every other file's
// row and the reading place stored on it; the link's open did the same by design and still does. Now the figure's open goes
// through the viewer's own door (file-view.ts openFigureInViewer): the trail's push, so Back returns to the report at its
// place, and no row for the picture. Read off the DOM and the store: the rows' paths after the control's open and after the
// plain click's (FAILS BEFORE: plot.svg at the head of the list), Back enabled to the report each time and returning to the
// reader's block, and the link's open still adding its row (the contrast that shows the door and not the store changed). The
// exception L2 states is driven too (the file review's round 2, extra8-1): a Forward step to the picture is a Back or Forward
// open, which the Files pane records as any open there (openFromViewer through the host's opener), so it DOES mint the
// picture's row, one per step, where the figure's own open did not; open point 12 states it beside the default.
// Skips LOUDLY without a playwright browser (in CI the Test step runs before the job's Chromium install, so the leg skips there; the launch is real-viewer-leg.ts's inBrowser, the shared helper). Synthetic values only: the notes-api world, a placeholder
// session id, /repo/notes-api paths.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { inBrowser } from "./real-viewer-leg";

const EXT = process.cwd();                                        // npm test runs in vscode-extension
const requireCjs = createRequire(path.join(EXT, "package.json"));
const UI = path.resolve(EXT, "..", "ui", "webview");
const SID = "11111111-2222-3333-4444-555555555555";
const ROOT = "/repo/notes-api";
const REPORT = ROOT + "/docs/report.md";
const NOTES = ROOT + "/docs/notes.md";
const PLOT = ROOT + "/docs/figs/plot.svg";
const RECENT_KEY = "romp:files-recent";                           // files-recent.ts RECENT_KEY, pinned below against the source
const PARA = (i: number): string => `Paragraph ${i}: ` + "lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor ".repeat(3).trim() + ".";
// the report: twenty paragraphs, the figure and the link (in view for a reader put at paragraph 20), twenty more
const REPORT_TEXT = "# Report\n\n" + Array.from({ length: 20 }, (_, i) => PARA(i + 1)).join("\n\n")
  + "\n\n![the plot](figs/plot.svg)\n\nRead [the notes](notes.md) too.\n\n" + Array.from({ length: 20 }, (_, i) => PARA(i + 21)).join("\n\n") + "\n";
const NOTES_TEXT = "# Notes\n\nA short note.\n";
const PLOT_SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="300" height="200"><rect width="300" height="200" fill="#456"/></svg>';
const DOCS: Record<string, string> = { [REPORT]: REPORT_TEXT, [NOTES]: NOTES_TEXT, [PLOT]: PLOT_SVG };
const MT = "1757145600000000001";

const BUILD = { bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
  nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent" };
/** The Files page's bundle with a probe reading the trail's live state. */
function bundle(): string {
  const contents = 'import "./files";\nimport { liveTrail } from "./file-trail";\n(window as any).__trail = liveTrail;\n';
  const r = requireCjs("esbuild").buildSync({ ...BUILD, stdin: { contents, resolveDir: UI, loader: "ts", sourcefile: "recent-probe.ts" } });
  return r.outputFiles[0].text;
}
const READERS = `
window.topBlock = function () {
  var body = document.querySelector("#romp-fileview .fileview-body"); if (!body) return null; var br = body.getBoundingClientRect();
  var els = Array.prototype.slice.call(document.querySelectorAll("#romp-fileview .fileview-md > *"));
  for (var i = 0; i < els.length; i++) { var r = els[i].getBoundingClientRect(); if (r.bottom > br.top + 0.5) return { text: (els[i].textContent || "").trim().slice(0, 12).trim(), scrollTop: body.scrollTop }; }
  return null;
};
window.putAtTop = function (text) {
  var body = document.querySelector("#romp-fileview .fileview-body");
  var k = Array.prototype.slice.call(document.querySelectorAll("#romp-fileview .fileview-md > *")).filter(function (e) { return (e.textContent || "").indexOf(text) === 0; })[0];
  body.scrollTop += k.getBoundingClientRect().top - body.getBoundingClientRect().top;
};
window.trailShape = function () { var s = window.__trail(); var n = function (e) { return e.path.slice(e.path.lastIndexOf("/") + 1); }; return { back: s.back.map(n), current: s.current ? n(s.current) : null, forward: s.forward.map(n) }; };
`;
const PAGE = `<!DOCTYPE html><html><head><meta charset=utf-8><style>
${fs.readFileSync(path.join(UI, "styles.css"), "utf8")}
${fs.readFileSync(path.join(UI, "files-pane.css"), "utf8")}
</style></head><body class="fileview-pane"><div id=files-empty></div>
<script>window.__posts=[];window.acquireVsCodeApi=function(){return{postMessage:function(m){window.__posts.push(m);}}};${READERS}</script>
<script src=/dist/files.js></script></body></html>`;

type Top = { text: string; scrollTop: number } | null;
type Nav = { present: boolean; title?: string; disabled?: string | null };
type H = {
  page: any;
  open: (p: string) => Promise<void>;                 // the shell's relay: an open from OUTSIDE the viewer
  painted: (base: string) => Promise<void>;
  recent: () => Promise<string[]>;                    // the Recent rows' file names, most recent first, read off localStorage
  back: () => Promise<Nav>; shape: () => Promise<{ back: string[]; current: string | null; forward: string[] }>;
  top: () => Promise<Top>; putAtTop: (t: string) => Promise<void>; base: () => Promise<string | null>; frames: (n?: number) => Promise<null>;
};
/** This leg's harness over the shared launch (real-viewer-leg.ts inBrowser: the skip on either road,
 *  the close), so one home carries the stand-down; the page here is the leg's own, not the shared module's. */
async function inViewer(t: any, body: (h: H) => Promise<void>): Promise<void> {
  await inBrowser(t, async (browser: any) => {
    const errors: string[] = [];
    const js = bundle();
    const ctx = await browser.newContext({ viewport: { width: 900, height: 600 } });
    const page = await ctx.newPage();
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    await ctx.route("http://romp.test/**", async (route: any) => {
      const u = new URL(route.request().url());
      if (u.pathname === "/files") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: PAGE });
      if (u.pathname === "/dist/files.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: js });
      if (u.pathname === "/file") {
        const p = u.searchParams.get("path") || "";
        const text = DOCS[p];
        if (text === undefined) return route.fulfill({ status: 404, contentType: "text/plain", body: "no such file: " + p });
        if (/\.svg$/i.test(p)) return route.fulfill({ status: 200, contentType: "image/svg+xml", headers: { "X-Romp-Mtime-Ns": MT, "Cache-Control": "no-store" }, body: text });
        if (route.request().method() === "HEAD") return route.fulfill({ status: 200, headers: { "X-Romp-Mtime-Ns": MT }, body: "" });
        return route.fulfill({ status: 200, contentType: "text/plain; charset=utf-8", headers: { "X-Romp-Mtime-Ns": MT, "X-Romp-Text-Utf8": "1" }, body: text });
      }
      return route.fulfill({ status: 404, body: "" });
    });
    await page.goto("http://romp.test/files");
    await page.waitForFunction(() => (window as any).__posts.some((m: any) => m && m.type === "ready"));
    const frames = (n = 2) => page.evaluate((k: number) => new Promise<null>((r) => { const f = () => (k-- <= 0 ? r(null) : requestAnimationFrame(f)); f(); }), n);
    const painted = async (base: string) => {
      await page.locator("#romp-fileview .fileview-base", { hasText: base }).waitFor({ timeout: 10000 });
      if (/\.svg$/.test(base)) await page.locator("#romp-fileview img.fileview-img").waitFor({ timeout: 10000 });
      else {
        await page.locator("#romp-fileview .fileview-md > p").first().waitFor({ timeout: 10000 });
        // the figure loaded and its control decided (the control arrives at the load)
        await page.waitForFunction(() => { const i = document.querySelector("#romp-fileview .fileview-md img") as HTMLImageElement | null; return !!i && i.complete && i.naturalWidth > 0 && !!(i.nextElementSibling && i.nextElementSibling.hasAttribute("data-fv-figopen")); }, null, { timeout: 10000 });
      }
      await frames(3);
    };
    const open = async (p: string) => {
      await page.evaluate(([p, sid]: [string, string]) => { window.postMessage({ romp: "viewFile", path: p, sid }, "*"); }, [p, SID]);
      await painted(p.slice(p.lastIndexOf("/") + 1));
    };
    const recent = (): Promise<string[]> => page.evaluate((key: string) => { const raw = localStorage.getItem(key); const rows = raw ? JSON.parse(raw) as Array<{ path: string }> : []; return rows.map((r) => r.path.slice(r.path.lastIndexOf("/") + 1)); }, RECENT_KEY);
    const back = (): Promise<Nav> => page.evaluate(() => { const b = document.querySelector("#romp-fileview .fileview-nav-back") as HTMLButtonElement | null; return b ? { present: true, title: b.title, disabled: b.getAttribute("aria-disabled") } : { present: false }; });
    const shape = () => page.evaluate(() => (window as any).trailShape());
    const top = (): Promise<Top> => page.evaluate(() => (window as any).topBlock());
    const putAtTop = async (t: string) => { await page.evaluate((t: string) => (window as any).putAtTop(t), t); await frames(1); };
    const base = () => page.locator("#romp-fileview .fileview-base").textContent();
    await body({ page, open, painted, recent, back, shape, top, putAtTop, base, frames });
    assert.deepEqual(errors, [], "no page errors");
    await ctx.close();
  });
}
const near = (a: number, b: number, tol = 1) => Math.abs(a - b) <= tol;

test("the Recent key this leg reads is files-recent.ts's", () => {
  assert.match(fs.readFileSync(path.join(UI, "files-recent.ts"), "utf8"), new RegExp('^export const RECENT_KEY = "' + RECENT_KEY.replace(/[.*+?^${}()|[\\]\\\\]/g, "\\\\$&") + '";$', "m"));
});

test("in a browser, the Files page: a picture opened from a figure, by the control and by the plain click, takes no Recent row while Back returns to the report at the reader's block; a Forward step to that picture mints its row (L2's rule, the exception open point 12 states); a link's open still takes its row", async (t) => {
  await inViewer(t, async (h) => {
    await h.open(REPORT);
    assert.deepEqual(await h.recent(), ["report.md"], "the relay's open is the pane's: one row");
    await h.putAtTop("Paragraph 20");
    const before = await h.top();
    assert.ok(before && before.text.startsWith("Paragraph 20"), "the reader stands at paragraph 20: " + JSON.stringify(before));
    // the control: the picture opens, Back names the report, and the Recent list is as it was
    await h.page.locator("#romp-fileview .fileview-md [data-fv-figopen]").click();
    await h.painted("plot.svg");
    assert.deepEqual(await h.back(), { present: true, title: "Back to report.md", disabled: null }, "the trail's push: Back to the report");
    // FAILS BEFORE: ["plot.svg", "report.md"], the picture's row at the head of the list (the pane's opener recorded it)
    assert.deepEqual(await h.recent(), ["report.md"], "no row for the picture opened from its figure's control");
    assert.deepEqual(await h.shape(), { back: ["report.md"], current: "plot.svg", forward: [] });
    await h.page.click("#romp-fileview .fileview-nav-back");
    await h.painted("report.md");
    const after = await h.top();
    assert.ok(after && after.text.startsWith("Paragraph 20") && near(after.scrollTop, before!.scrollTop), "Back re-seats the reader's block: " + JSON.stringify(after) + " vs " + JSON.stringify(before));
    assert.deepEqual(await h.recent(), ["report.md"], "Back's open of the report moves its own row to the head, where it already was");
    // the plain click: the same door
    const img = await h.page.evaluate(() => { const r = document.querySelector("#romp-fileview .fileview-md img")!.getBoundingClientRect(); return { left: r.left, top: r.top, width: r.width, height: r.height }; });
    await h.page.mouse.click(img.left + img.width * 0.3, img.top + img.height * 0.6);
    await h.painted("plot.svg");
    assert.deepEqual(await h.back(), { present: true, title: "Back to report.md", disabled: null });
    // FAILS BEFORE: the plain click minted the row too
    assert.deepEqual(await h.recent(), ["report.md"], "no row for the picture opened by the plain click either");
    await h.page.click("#romp-fileview .fileview-nav-back");
    await h.painted("report.md");
    assert.ok((await h.top())!.text.startsWith("Paragraph 20"), "back at the block again");
    assert.deepEqual(await h.shape(), { back: [], current: "report.md", forward: ["plot.svg"] }, "the picture stands ahead");
    // the exception L2 states (the file review's round 2, extra8-1): a Forward step to the picture is a Back or Forward open, the
    // pane's own (openFromViewer through the host's opener, files.ts openHere), so it mints the picture's row where the figure's
    // open did not; one row per step, at the head, and Back then moves the report's row back to the head over it
    await h.page.click("#romp-fileview .fileview-nav-forward");
    await h.painted("plot.svg");
    assert.deepEqual(await h.shape(), { back: ["report.md"], current: "plot.svg", forward: [] }, "Forward retraced the step");
    assert.deepEqual(await h.recent(), ["plot.svg", "report.md"], "a Forward step to the picture mints its row (L2's rule), where the figure's own open did not");
    await h.page.click("#romp-fileview .fileview-nav-back");
    await h.painted("report.md");
    assert.deepEqual(await h.recent(), ["report.md", "plot.svg"], "Back moves the report's row to the head; the picture's row stands");
    // the contrast: a link followed inside the report goes through the pane's opener and takes its row, as before
    await h.page.locator("#romp-fileview .fileview-md .file-uri-link, #romp-fileview .fileview-md a", { hasText: "the notes" }).first().click();
    await h.page.locator("#romp-fileview .fileview-base", { hasText: "notes.md" }).waitFor({ timeout: 10000 });
    await h.frames(3);
    assert.deepEqual(await h.recent(), ["notes.md", "report.md", "plot.svg"], "a link's open still enters the Recent list: the door changed for the figure alone");
    assert.deepEqual(await h.back(), { present: true, title: "Back to report.md", disabled: null }, "and is the trail's push too");
  });
});

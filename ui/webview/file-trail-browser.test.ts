// The viewer's Back and Forward in a browser (file-trail.ts, file-view.ts; plans/markdown-viewer.md, "Follow-on: Link
// navigation", L1 and L2): headless Chromium boots the real Files page (files.ts: the shared viewer, the pane's own
// opener and its Recent list) and a chat-modal page (the viewer with its default opener), opens synthetic notes and
// follows the links inside them. Read off the real DOM: the two glyph buttons at the left of the bar, their titles and
// aria-disabled state after each step, the file the card shows, the reader's block and scrollTop after a Back, the view
// it opened in and the saved preference it left alone, the trail's state through the bundle's probe. On an open with nothing
// to step to either way (a fresh open from outside) the GROUP is hidden and takes no room, and it shows once a step exists
// one way, the other button wearing aria-disabled alone (T367, the rule the greyed GitHub link follows; the file review's round
// 2, extra8-2), read here off the group's hidden attribute and its client rects. The cases are the
// contract's: (1) a link followed, Back present and returning to the report at its place and view, red over the
// unchanged viewer at the first Back assertion (no Back button existed); (2) Forward after Back; (3) an open from
// outside, the Recent row and the shell's relay, starts the trail over; (4) the chords, with and without a text field
// holding the keyboard, and a key another listener prevented; (5) a section link, a web address and a same-file line
// target push nothing; (7) closing the viewer ends the trail. Skips LOUDLY without a playwright browser (in CI the Test step runs before the job's Chromium install, so the leg skips there and runs in the step after the install under ROMP_FILEVIEW_BROWSER_REQUIRE, where the skip is a failure: real-viewer-leg.ts inBrowser). Synthetic values only: the notes-api world, a placeholder session id, example.invalid addresses.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { inBrowser as withBrowser } from "./real-viewer-leg";

const EXT = process.cwd();                                        // npm test runs in vscode-extension
const requireCjs = createRequire(path.join(EXT, "package.json"));
const UI = path.resolve(EXT, "..", "ui", "webview");
const SID = "11111111-2222-3333-4444-555555555555";
const ROOT = "/repo/notes-api";
const REPORT = ROOT + "/docs/report.md";
const NOTES = ROOT + "/docs/notes.md";
const GUIDE = ROOT + "/docs/guide.md";
const PLOT = ROOT + "/docs/figs/plot.svg";
const WEB = "https://example.invalid/elsewhere";
const PARA = (i: number): string => `Paragraph ${i}: ` + "lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor ".repeat(3).trim() + ".";
// the report: forty paragraphs, then the links paragraph (a link to the notes, `./notes.md`: a slash, so the Raw view's path
// grammar links the token too; a web address; a same-document section link; a same-file line target; a picture; a
// wikilink, which md-config.ts renders as an anchor to guide.md beside the report), forty more paragraphs and the section. The links stand AFTER paragraph 40 so that a reader put at paragraph 40 has them in
// view: a click on a link out of view scrolls the body to it first, and the place the leave then records is the
// link's, not the reader's.
const LINKS_PARA = "Read [the notes](./notes.md) and [the web](" + WEB + "); jump to [results](#results), to [line forty](report.md:40), to [the plot](figs/plot.svg) or to [[guide]].";
const REPORT_TEXT = "# Report\n\n" + Array.from({ length: 40 }, (_, i) => PARA(i + 1)).join("\n\n") + "\n\n" + LINKS_PARA + "\n\n"
  + Array.from({ length: 40 }, (_, i) => PARA(i + 41)).join("\n\n") + "\n\n## Results\n\nThe results paragraph.\n";
const NOTES_TEXT = "# Notes\n\nBack to [the report](report.md) or on to [the guide](guide.md).\n\n" + Array.from({ length: 30 }, (_, i) => `Note ${i + 1}: a short line of notes.`).join("\n\n") + "\n";
const GUIDE_TEXT = "# Guide\n\nOne rule per line.\n";
const PLOT_SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="120" height="40"><rect width="120" height="40" fill="#456"/></svg>';
const DOCS: Record<string, string> = { [REPORT]: REPORT_TEXT, [NOTES]: NOTES_TEXT, [GUIDE]: GUIDE_TEXT, [PLOT]: PLOT_SVG };
const MT = "1757145600000000001";

const BUILD = { bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
  nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent" };
/** The Files page's bundle with a probe reading the trail's live state, or the viewer alone (the chat modal's default opener) as FV. */
function bundle(host: "files" | "chat"): string {
  const contents = host === "files"
    ? 'import "./files";\nimport { liveTrail } from "./file-trail";\n(window as any).__trail = liveTrail;\n'
    : 'export { initFileView, openFileView, closeFileView } from "./file-view";\nimport { liveTrail } from "./file-trail";\n(window as any).__trail = liveTrail;\n';
  const r = requireCjs("esbuild").buildSync({ ...BUILD, stdin: { contents, resolveDir: UI, loader: "ts", sourcefile: "trail-probe.ts" }, globalName: host === "chat" ? "FV" : undefined });
  return r.outputFiles[0].text;
}
// what the legs read: the top-visible block (Rendered) or row (Raw), its first characters and its top edge from the body's top
const READERS = `
window.topBlock = function () {
  var body = document.querySelector("#romp-fileview .fileview-body"); if (!body) return null; var br = body.getBoundingClientRect();
  var sel = document.querySelector("#romp-fileview .fileview-md") ? "#romp-fileview .fileview-md > *" : "#romp-fileview code.hljs .fv-cl";
  var els = Array.prototype.slice.call(document.querySelectorAll(sel));
  for (var i = 0; i < els.length; i++) { var r = els[i].getBoundingClientRect(); if (r.bottom > br.top + 0.5) return { text: (els[i].textContent || "").trim().slice(0, 12).trim(), top: Math.round((r.top - br.top) * 10) / 10, scrollTop: body.scrollTop, view: sel.indexOf("fileview-md") >= 0 ? "rendered" : "raw" }; }
  return null;
};
window.putAtTop = function (text) {
  var body = document.querySelector("#romp-fileview .fileview-body");
  var sel = document.querySelector("#romp-fileview .fileview-md") ? "#romp-fileview .fileview-md > *" : "#romp-fileview code.hljs .fv-cl";
  var k = Array.prototype.slice.call(document.querySelectorAll(sel)).filter(function (e) { return (e.textContent || "").indexOf(text) === 0; })[0];
  body.scrollTop += k.getBoundingClientRect().top - body.getBoundingClientRect().top;
};
window.nav = function () {
  var read = function (dir) { var b = document.querySelector("#romp-fileview .fileview-nav-" + dir); return b ? { present: true, title: b.title, aria: b.getAttribute("aria-label"), disabled: b.getAttribute("aria-disabled"), svg: !!b.querySelector("svg"), text: (b.textContent || "").trim(), first: b.closest(".fileview-bar").firstElementChild === b.parentElement, groupHidden: b.parentElement.hidden, groupBoxes: b.parentElement.getClientRects().length } : { present: false }; };
  return { back: read("back"), forward: read("forward") };
};
window.trailShape = function () { var s = window.__trail(); var n = function (e) { return e.path.slice(e.path.lastIndexOf("/") + 1) + (e.view ? "@" + e.view : ""); }; return { back: s.back.map(n), current: s.current ? n(s.current) : null, forward: s.forward.map(n) }; };
`;
const PAGE = (host: "files" | "chat") => `<!DOCTYPE html><html><head><meta charset=utf-8><style>
${fs.readFileSync(path.join(UI, "styles.css"), "utf8")}
${host === "files" ? fs.readFileSync(path.join(UI, "files-pane.css"), "utf8") : ""}
</style></head><body class="${host === "files" ? "fileview-pane" : ""}">${host === "files" ? "<div id=files-empty></div>" : ""}
<script>window.__posts=[];window.acquireVsCodeApi=function(){return{postMessage:function(m){window.__posts.push(m);}}};${READERS}</script>
<script src=/dist/${host}.js></script>${host === "chat" ? "<script>FV.initFileView(function (m) { window.__posts.push(m); });</script>" : ""}</body></html>`;

type Top = { text: string; top: number; scrollTop: number; view: "rendered" | "raw" } | null;
type Nav = { back: any; forward: any };
type Shape = { back: string[]; current: string | null; forward: string[] };
type H = {
  page: any; ctx: any; errors: string[];
  open: (p: string, at?: Record<string, unknown> | null) => Promise<void>;   // an open from OUTSIDE: the shell's relay (files) or openFileView (chat)
  follow: (text: string, base: string, raw?: boolean) => Promise<void>;     // a click on the link with that text, awaited on the named file's paint
  painted: (base: string, raw?: boolean) => Promise<void>;
  nav: () => Promise<Nav>; shape: () => Promise<Shape>; top: () => Promise<Top>; putAtTop: (t: string) => Promise<void>; base: () => Promise<string | null>;
  frames: (n?: number) => Promise<null>; fmt: () => Promise<string | null>;
};
/** This leg's harness over the shared launch (real-viewer-leg.ts inBrowser: the skip on either road, the failure under CI's switch,
 *  the close), so one home carries the stand-down; the page here is the leg's own, not the shared module's. */
async function inBrowser(t: any, host: "files" | "chat", body: (h: H) => Promise<void>): Promise<void> {
  await withBrowser(t, async (browser: any) => {
    const errors: string[] = [];
    const js = bundle(host);
    const ctx = await browser.newContext({ viewport: { width: 900, height: 520 } });
    const page = await ctx.newPage();
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    await ctx.route("https://example.invalid/**", (route: any) => route.fulfill({ status: 200, contentType: "text/html", body: "<title>elsewhere</title>" }));
    await ctx.route("http://romp.test/**", async (route: any) => {
      const u = new URL(route.request().url());
      if (u.pathname === "/files" || u.pathname === "/chat") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: PAGE(host) });
      if (u.pathname === "/dist/" + host + ".js") return route.fulfill({ status: 200, contentType: "application/javascript", body: js });
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
    await page.goto("http://romp.test/" + (host === "files" ? "files" : "chat"));
    if (host === "files") await page.waitForFunction(() => (window as any).__posts.some((m: any) => m && m.type === "ready"));
    else await page.waitForFunction(() => typeof (window as any).FV === "object" && typeof (window as any).__trail === "function");
    const frames = (n = 2) => page.evaluate((k: number) => new Promise<null>((r) => { const f = () => (k-- <= 0 ? r(null) : requestAnimationFrame(f)); f(); }), n);
    const painted = async (base: string, raw = false) => {
      await page.locator("#romp-fileview .fileview-base", { hasText: base }).waitFor({ timeout: 10000 });
      if (/\.svg$/.test(base)) await page.locator("#romp-fileview img.fileview-img").waitFor({ timeout: 10000 });
      else await page.locator(raw ? "#romp-fileview .fileview-body .fv-cl" : "#romp-fileview .fileview-md > p").first().waitFor({ timeout: 10000 });
      await frames(3);
    };
    const open = async (p: string, at: Record<string, unknown> | null = null) => {
      if (host === "files") await page.evaluate(([p, sid, at]: [string, string, unknown]) => { window.postMessage({ romp: "viewFile", path: p, sid, at }, "*"); }, [p, SID, at]);
      else await page.evaluate(([p, sid, at]: [string, string, unknown]) => { (window as any).FV.openFileView(p, sid, { at }); }, [p, SID, at]);
      await painted(p.slice(p.lastIndexOf("/") + 1), at !== null && typeof (at as any).line === "number");
    };
    const follow = async (text: string, base: string, raw = false) => {
      await page.locator("#romp-fileview .fileview-body a, #romp-fileview .fileview-body .file-uri-link", { hasText: text }).first().click();
      await painted(base, raw);
    };
    const nav = (): Promise<Nav> => page.evaluate(() => (window as any).nav());
    const shape = (): Promise<Shape> => page.evaluate(() => (window as any).trailShape());
    const top = (): Promise<Top> => page.evaluate(() => (window as any).topBlock());
    const putAtTop = async (t: string) => { await page.evaluate((t: string) => (window as any).putAtTop(t), t); await frames(1); };
    const base = () => page.locator("#romp-fileview .fileview-base").textContent();
    const fmt = () => page.evaluate(() => localStorage.getItem("romp:fileviewFmt"));
    await body({ page, ctx, errors, open, follow, painted, nav, shape, top, putAtTop, base, frames, fmt });
    assert.deepEqual(errors, [], "no page errors");
    await ctx.close();
  });
}
const near = (a: number, b: number, tol = 1) => Math.abs(a - b) <= tol;
const disabled = (b: any, msg: string) => { assert.equal(b.present, true, msg + ": the button is in the bar"); assert.equal(b.disabled, "true", msg + ": aria-disabled alone when empty: " + JSON.stringify(b)); };
const enabledTo = (b: any, title: string, msg: string) => { assert.equal(b.present, true, msg + ": the button is in the bar"); assert.equal(b.disabled, null, msg + ": no aria-disabled with a target: " + JSON.stringify(b)); assert.equal(b.title, title, msg); assert.equal(b.aria, title, msg + ": the aria-label says the same"); assert.equal(b.groupHidden, false, msg + ": the group shows with a target that way"); assert.ok(b.groupBoxes > 0, msg + ": and has a box"); };
/** Nothing to step to either way (an open from outside the viewer, a trail of one file): the GROUP is hidden and takes no room
 *  (T367, the rule the greyed GitHub link follows, removed rather than dimmed; the file review's round 2, extra8-2), and each
 *  button still carries aria-disabled for a reader that reaches it by other means (the pair is built once per open). */
const hiddenPair = (n: any, msg: string) => {
  for (const [dir, b] of [["back", n.back], ["forward", n.forward]] as Array<[string, any]>) {
    assert.equal(b.present, true, msg + ": the " + dir + " button is in the bar");
    assert.equal(b.disabled, "true", msg + ": " + dir + " wears aria-disabled: " + JSON.stringify(b));
    assert.equal(b.groupHidden, true, msg + ": the group is hidden (T367)");
    assert.equal(b.groupBoxes, 0, msg + ": and takes no room");
  }
};

test("in a browser, the Files page: a link followed from the report replaces the card; Back is a glyph at the bar's left titled with the report's name and returns to the report at its block, its scrollTop and its view (a Raw open for a line target comes back Raw with the saved preference untouched); Forward then retraces the step", async (t) => {
  await inBrowser(t, "files", async (h) => {
    await h.open(REPORT);
    let n = await h.nav();
    // (1) FAILS BEFORE: the unchanged viewer has no Back button
    assert.equal(n.back.present, true, "a Back button in the viewer's bar");
    assert.deepEqual([n.back.svg, n.back.text, n.back.first], [true, "", true], "a glyph, no word, in the bar's first group: " + JSON.stringify(n.back));
    hiddenPair(n, "a fresh open from the relay is the trail's root: nothing either way, so the group is hidden");
    assert.deepEqual(await h.shape(), { back: [], current: "report.md", forward: [] });
    await h.putAtTop("Paragraph 40");
    const before = await h.top();
    assert.ok(before && before.text.startsWith("Paragraph 40"), "the reader stands at paragraph 40: " + JSON.stringify(before));
    await h.follow("the notes", "notes.md");
    n = await h.nav();
    enabledTo(n.back, "Back to report.md", "after following the link");
    disabled(n.forward, "a push clears the steps ahead");
    assert.deepEqual(await h.shape(), { back: ["report.md@rendered"], current: "notes.md", forward: [] }, "the report went behind with the view it was read in");
    await h.page.click("#romp-fileview .fileview-nav-back");
    await h.painted("report.md");
    const after = await h.top();
    assert.ok(after && after.text.startsWith("Paragraph 40"), "Back re-seats the remembered place: " + JSON.stringify(after));
    assert.ok(near(after!.scrollTop, before!.scrollTop), "at the same scrollTop within a pixel: " + after!.scrollTop + " vs " + before!.scrollTop);
    assert.equal(after!.view, "rendered", "in the view it was left in");
    n = await h.nav();
    disabled(n.back, "the root again"); enabledTo(n.forward, "Forward to notes.md", "the file just left went ahead");
    assert.deepEqual(await h.shape(), { back: [], current: "report.md@rendered", forward: ["notes.md@rendered"] });
    // (2) Forward after Back
    await h.page.click("#romp-fileview .fileview-nav-forward");
    await h.painted("notes.md");
    n = await h.nav();
    enabledTo(n.back, "Back to report.md", "forward retraced the step"); disabled(n.forward, "the end of the trail");
    assert.deepEqual(await h.shape(), { back: ["report.md@rendered"], current: "notes.md@rendered", forward: [] });
    // a longer trail: notes to guide, then two Backs land on the report
    await h.follow("the guide", "guide.md");
    assert.deepEqual(await h.shape(), { back: ["report.md@rendered", "notes.md@rendered"], current: "guide.md", forward: [] });
    await h.page.click("#romp-fileview .fileview-nav-back"); await h.painted("notes.md");
    await h.page.click("#romp-fileview .fileview-nav-back"); await h.painted("report.md");
    n = await h.nav();
    disabled(n.back, "back at the root"); enabledTo(n.forward, "Forward to notes.md", "two files ahead, the nearest named");
    assert.deepEqual(await h.shape(), { back: [], current: "report.md@rendered", forward: ["notes.md@rendered", "guide.md@rendered"] });
    // the view: a line target opens the report Raw for that open; the link followed from the Raw rows, and Back comes back Raw
    // while the saved preference (absent: Rendered) is untouched; the picture is a file of the trail like any other
    await h.page.click("#romp-fileview .fileview-close");
    await h.page.waitForFunction(() => !document.getElementById("romp-fileview"), null, { timeout: 5000 });
    await h.open(REPORT, { line: 30 });
    assert.equal((await h.top())!.view, "raw", "a line target opens the Raw view for this open");
    await h.follow("./notes.md", "notes.md");
    assert.equal((await h.top())!.view, "rendered", "the notes open in the saved view, Rendered");
    assert.deepEqual(await h.shape(), { back: ["report.md@raw"], current: "notes.md", forward: [] }, "the report went behind as read: Raw");
    await h.page.click("#romp-fileview .fileview-nav-back");
    await h.painted("report.md", true);
    assert.equal((await h.top())!.view, "raw", "Back opens the report in the view the entry recorded");
    assert.equal(await h.fmt(), null, "and the saved preference was never written");
    await h.follow("figs/plot.svg", "plot.svg");   // the Raw row's path token (the Markdown label is not a link there)
    n = await h.nav();
    enabledTo(n.back, "Back to report.md", "a picture reached from the report: Back names the report");
    await h.page.click("#romp-fileview .fileview-nav-back");
    await h.painted("report.md", true);
    assert.deepEqual(await h.shape(), { back: [], current: "report.md@raw", forward: ["plot.svg"] }, "the picture ahead, with no view to record");
  });
});

test("in a browser, the Files page: a wikilink pushes like any path link; an open from OUTSIDE the viewer starts the trail over (a Recent row after a close, the shell's relay over an open viewer), so Back and Forward are empty; closing the viewer ends the trail", async (t) => {
  await inBrowser(t, "files", async (h) => {
    await h.open(REPORT);
    // a wikilink: md-config.ts renders `[[guide]]` as an anchor to guide.md beside the report, linkMarkdownAnchors marks it a path link, the delegate pushes
    await h.follow("guide", "guide.md");
    assert.deepEqual(await h.shape(), { back: ["report.md@rendered"], current: "guide.md", forward: [] }, "a wikilink's open is a push");
    await h.page.click("#romp-fileview .fileview-nav-back");
    await h.painted("report.md");
    await h.follow("the notes", "notes.md");
    assert.deepEqual(await h.shape(), { back: ["report.md@rendered"], current: "notes.md", forward: [] }, "the push after the Back dropped the guide from the list ahead");
    enabledTo((await h.nav()).back, "Back to report.md", "a trail stands");
    // (7) the close ends it
    await h.page.keyboard.press("Escape");
    await h.page.waitForFunction(() => !document.getElementById("romp-fileview"), null, { timeout: 5000 });
    assert.deepEqual(await h.shape(), { back: [], current: null, forward: [] }, "no trail after the close");
    // (3) the Recent row: a fresh root
    await h.page.locator("#files-empty .fs-row", { hasText: "report.md" }).first().click();
    await h.painted("report.md");
    let n = await h.nav();
    hiddenPair(n, "a Recent row's open is outside the viewer: nothing either way, the group hidden");
    assert.deepEqual(await h.shape(), { back: [], current: "report.md", forward: [] });
    // (3) the relay over an open viewer with a trail: a fresh root too
    await h.follow("the notes", "notes.md");
    await h.follow("the guide", "guide.md");
    assert.deepEqual((await h.shape()).back, ["report.md@rendered", "notes.md@rendered"]);
    await h.open(NOTES);
    n = await h.nav();
    hiddenPair(n, "the shell's relay is an open from outside: the group hidden again");
    assert.deepEqual(await h.shape(), { back: [], current: "notes.md", forward: [] });
    // the Recent list keeps its meaning: one row per file, the files this page opened
    await h.page.click("#romp-fileview .fileview-close");
    await h.page.waitForFunction(() => !document.getElementById("romp-fileview"), null, { timeout: 5000 });
    const recent = await h.page.evaluate(() => Array.from(document.querySelectorAll("#files-empty .fs-row .fileview-base")).map((e) => e.textContent));
    assert.deepEqual(recent, ["notes.md", "guide.md", "report.md"], "most recent first, one row per file, a Back or Forward open moving its row up like any open here");
    // the trail ended at the close; a Back that was never armed opens nothing: no viewer, the chord is nobody's
    await h.page.keyboard.press("Alt+ArrowLeft");
    await h.frames(2);
    assert.equal(await h.page.evaluate(() => !!document.getElementById("romp-fileview")), false, "no viewer opened by a chord with none up");
  });
});

test("in a browser, the Files page: Alt+Left and Alt+Right step the trail while the viewer is open; a text field holding the keyboard keeps the chord, and so does a key another listener prevented first; the chord takes the browser's default while the viewer is up", async (t) => {
  await inBrowser(t, "files", async (h) => {
    await h.open(REPORT);
    await h.putAtTop("Paragraph 40");
    const before = await h.top();
    await h.follow("the notes", "notes.md");
    // (4) the chord
    await h.page.keyboard.press("Alt+ArrowLeft");
    await h.painted("report.md");
    const after = await h.top();
    assert.ok(after && after.text.startsWith("Paragraph 40") && near(after.scrollTop, before!.scrollTop), "Alt+Left is Back, at the remembered place: " + JSON.stringify(after));
    await h.page.keyboard.press("Alt+ArrowRight");
    await h.painted("notes.md");
    assert.deepEqual(await h.shape(), { back: ["report.md@rendered"], current: "notes.md@rendered", forward: [] }, "Alt+Right is Forward");
    // a text field with the keyboard: the chord is the field's (the caret's word step on a Mac, nothing here), the viewer stays
    await h.page.evaluate(() => { const i = document.createElement("input"); i.id = "probe-input"; i.type = "text"; i.value = "a note being typed"; document.body.appendChild(i); i.focus(); });
    await h.page.keyboard.press("Alt+ArrowLeft");
    await h.frames(3);
    assert.equal(await h.base(), "notes.md", "a text field holds the keyboard: no step");
    assert.deepEqual((await h.shape()).current, "notes.md@rendered");
    await h.page.evaluate(() => { const i = document.getElementById("probe-input") as HTMLInputElement; i.blur(); i.remove(); });
    // a key another listener already took (a window capture listener runs before the document's): the viewer stands down
    await h.page.evaluate(() => { (window as any).__eat = (e: KeyboardEvent) => { if (e.altKey && e.key === "ArrowLeft") e.preventDefault(); }; window.addEventListener("keydown", (window as any).__eat, true); });
    await h.page.keyboard.press("Alt+ArrowLeft");
    await h.frames(3);
    assert.equal(await h.base(), "notes.md", "a prevented key asks nothing of the viewer");
    await h.page.evaluate(() => { window.removeEventListener("keydown", (window as any).__eat, true); });
    // with the keyboard on the body (a click in the note), the chord works and its default is taken; with nothing behind, Alt+Left still takes the default (the browser must not leave the page under an open viewer)
    await h.page.click("#romp-fileview .fileview-body");
    const taken = await h.page.evaluate(() => new Promise<{ back: boolean; none: boolean }>((resolve) => {
      const seen: boolean[] = [];
      const bubble = (e: KeyboardEvent) => { if (e.altKey && e.key === "ArrowLeft") seen.push(e.defaultPrevented); };
      window.addEventListener("keydown", bubble);
      const fire = () => document.activeElement!.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowLeft", altKey: true, bubbles: true, cancelable: true }));
      fire();   // on notes.md with the report behind: a Back, prevented
      const wait = () => { if (!document.querySelector("#romp-fileview .fileview-md > p") || !/report\.md/.test(document.querySelector("#romp-fileview .fileview-base")!.textContent || "")) { requestAnimationFrame(wait); return; }
        (document.querySelector("#romp-fileview .fileview-body") as HTMLElement).focus();
        fire();   // on the report with nothing behind: prevented, nothing opens
        requestAnimationFrame(() => { window.removeEventListener("keydown", bubble); resolve({ back: seen[0], none: seen[1] }); }); };
      requestAnimationFrame(wait);
    }));
    assert.deepEqual(taken, { back: true, none: true }, "the browser's history step is taken over while the viewer is up, with a target and without one");
    await h.painted("report.md");
    assert.equal(await h.base(), "report.md");
    // the editor's stand-down (the guide's sentence; the file review held it by source text alone): with the editor up the chord
    // asks nothing, though the keyboard is on a bar button and not in a text field; leaving edit mode gives the chord back. Edit's
    // consent ask is a confirm dialog here (/version is not served by this harness), accepted; the editor chunk is not served either,
    // so the plain fallback editor comes up, which is enough: `editing` is the guard, whichever editor holds the text.
    await h.follow("the notes", "notes.md");
    const s1 = await h.shape();
    assert.deepEqual(s1.back, ["report.md@rendered"], "a step behind, so the chord has a target to refuse");
    h.page.once("dialog", (d: any) => d.accept());
    await h.page.click('#romp-fileview button[aria-label="Edit"]');
    await h.page.waitForFunction(() => !!document.querySelector("#romp-fileview textarea, #romp-fileview .cm-editor"), null, { timeout: 10000 });
    await h.frames(2);
    await h.page.focus("#romp-fileview .fileview-nav-back");
    assert.equal(await h.page.evaluate(() => document.activeElement!.className.includes("fileview-nav-back")), true, "the keyboard is on the Back button, no text field");
    await h.page.keyboard.press("Alt+ArrowLeft");
    await h.frames(3);
    // FAILS BEFORE the guard: the chord replaced the card under the open editor and dropped edit mode
    assert.equal(await h.base(), "notes.md", "the editor holds the viewer: the chord steps nothing");
    assert.deepEqual(await h.shape(), s1, "the trail did not move");
    assert.equal(await h.page.evaluate(() => !!document.querySelector("#romp-fileview textarea, #romp-fileview .cm-editor")), true, "and the editor is still up");
    // leave edit mode (Escape peels it first; the buffer is unmodified, so no discard ask) and the chord steps again, with nothing
    // focused but the document's body, which the typing-target stand-down lets through
    await h.page.keyboard.press("Escape");
    await h.page.waitForFunction(() => !document.querySelector("#romp-fileview textarea, #romp-fileview .cm-editor") && !!document.querySelector("#romp-fileview .fileview-body .fv-cl, #romp-fileview .fileview-md"), null, { timeout: 10000 });
    await h.frames(2);
    await h.page.evaluate(() => { (document.activeElement as HTMLElement | null)?.blur(); });
    assert.equal(await h.page.evaluate(() => document.activeElement === document.body), true, "nothing focused: the document's body");
    await h.page.keyboard.press("Alt+ArrowLeft");
    await h.painted("report.md");
    assert.equal(await h.base(), "report.md", "out of edit mode the chord is Back again");
    assert.deepEqual((await h.shape()).current, "report.md@rendered");
  });
});

test("in a browser, the Files page: a section link scrolls and pushes nothing, a web address opens a tab and pushes nothing, and a same-file line target replaces the card without pushing", async (t) => {
  await inBrowser(t, "files", async (h) => {
    await h.open(REPORT);
    const s0 = await h.shape();
    // (5) a same-document section link: the body scrolls, the trail stands
    const top0 = (await h.top())!.scrollTop;
    await h.page.locator("#romp-fileview .fileview-md a", { hasText: "results" }).click();
    await h.frames(3);
    const top1 = (await h.top())!.scrollTop;
    assert.ok(top1 > top0, "the section link scrolled the body: " + top0 + " to " + top1);
    assert.deepEqual(await h.shape(), s0, "a section link pushes nothing");
    hiddenPair(await h.nav(), "still the root: the group stays hidden");
    // a web address: a tab, the trail unchanged
    const [tab] = await Promise.all([h.ctx.waitForEvent("page", { timeout: 10000 }), h.page.locator("#romp-fileview .fileview-md a", { hasText: "the web" }).click()]);
    await tab.waitForLoadState();
    assert.equal(tab.url(), WEB, "the web address opened in a tab of its own");
    await tab.close();
    assert.deepEqual(await h.shape(), s0, "a web address pushes nothing");
    assert.equal(await h.base(), "report.md", "and the viewer still shows the report");
    // a same-file line target: the card is replaced (Raw at the line), the trail's one entry stands
    await h.page.locator("#romp-fileview .fileview-md a", { hasText: "line forty" }).click();
    await h.painted("report.md", true);
    assert.equal((await h.top())!.view, "raw", "the line target took the Raw view for this open");
    assert.deepEqual(await h.shape(), { back: [], current: "report.md@rendered", forward: [] }, "a target inside the same file is no step between files: nothing behind, the entry's view the Rendered leave's");
    hiddenPair(await h.nav(), "no Back for a jump inside the file: the group stays hidden");
  });
});

test("in a browser, the chat modal (the viewer's default opener, no host): a link followed pushes, Back returns to the report at its place, Forward retraces, and the close ends the trail", async (t) => {
  await inBrowser(t, "chat", async (h) => {
    await h.open(REPORT);
    const n0 = await h.nav();
    assert.equal(n0.back.present, true, "the Back glyph over the chat too");
    hiddenPair(n0, "the root: nothing either way, the group hidden over the chat too");
    await h.putAtTop("Paragraph 40");
    const before = await h.top();
    await h.follow("the notes", "notes.md");
    enabledTo((await h.nav()).back, "Back to report.md", "the default opener's open is the viewer's own");
    await h.page.click("#romp-fileview .fileview-nav-back");
    await h.painted("report.md");
    const after = await h.top();
    assert.ok(after && after.text.startsWith("Paragraph 40") && near(after.scrollTop, before!.scrollTop), "Back re-seats the remembered place: " + JSON.stringify(after));
    enabledTo((await h.nav()).forward, "Forward to notes.md", "the notes ahead");
    await h.page.keyboard.press("Alt+ArrowRight");
    await h.painted("notes.md");
    assert.deepEqual(await h.shape(), { back: ["report.md@rendered"], current: "notes.md@rendered", forward: [] });
    await h.page.evaluate(() => { (window as any).FV.closeFileView(); });
    await h.page.waitForFunction(() => !document.getElementById("romp-fileview"), null, { timeout: 5000 });
    assert.deepEqual(await h.shape(), { back: [], current: null, forward: [] }, "the close ends the trail");
  });
});

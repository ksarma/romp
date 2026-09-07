// Links inside a shown file, in a browser (file-view-links.ts; the user 2026-09-07): headless Chromium boots the Files
// pane's real bundle, opens synthetic files through the pane's relay, and drives the mouse and the keyboard over the
// viewer's real DOM: the rows hljs built and the pass marked, the body's click delegate and its gesture, the fetch a
// path link causes, the line a `:30` link scrolls to, the Raw view a markdown file takes for that open, the tab a URL
// anchor opens, and the clicks that must NOT open anything. This is the leg no stand-in can stand in for: the browser
// decides where a press-drag-release sends its click and whether a focusable span's press ends the selection
// (path-links.ts's press handler exists for exactly that); DOMPurify decides which Markdown targets survive; hljs
// decides where a substitution span cuts a path; the comments panel, driven by a fake host answering its status asks,
// paints its highlight and change marks INTO the links, and the browser decides which element a click on a mark lands
// on; a confirm dialog is a real one. Two more pages run the chat's and the feed's own click handlers (their source,
// transformed and installed over the same bundle) so the three documents' routing is exercised, not pinned. Skips
// LOUDLY without a playwright browser (CI installs none), as waiting-link-focus.test.ts does. Synthetic values only:
// the notes-api world under /tmp/TESTHOST, a placeholder session id, example.invalid addresses.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { makeAnchor } from "./anchor-map";
import { DEAD_LINK_TITLE, noSectionTitle } from "./file-view-links";

const requireCjs = createRequire(__filename);
const EXT = process.cwd();                                        // npm test runs in vscode-extension
const UI = path.resolve(EXT, "..", "ui", "webview");
const SID = "11111111-2222-3333-4444-555555555555";
const ROOT = "/tmp/TESTHOST/notes-api";
const APP = ROOT + "/src/app.py";
const GUIDE = ROOT + "/docs/guide.md";
const NOTES = ROOT + "/docs/notes.md";
const README = ROOT + "/README.md";
const CONFIG = ROOT + "/src/data/config.json";
const RUN = ROOT + "/scripts/run.sh";
const XTS = ROOT + "/ui/x.ts";
const URL_SETUP = "https://example.invalid/docs/setup.html";

const APP_TEXT = [
  "# notes-api: see https://example.invalid/docs/setup.html, then ../docs/guide.md:30.",
  "import json",
  'cfg = json.load(open("data/config.json"))',
  "from . import util  # and/or 24/7 x = 1/2.5 /api/users ./foo",
  "readme = 'file:///tmp/TESTHOST/notes-api/README.md'",
  "# see www.example.org/docs/index.html or git@github.invalid:user/repo.git",
  'far = "file://evil.invalid/share/x.md"',
  "",
].join("\n");
const GUIDE_TEXT = [
  "# Guide", "",
  "Read [the app](../src/app.py) and [the web](https://example.invalid/doc).",
  "Bare ../src/app.py:3 links too, and https://example.invalid/prose is a URL.", "",
  "Also [same](notes.md:7), [uri](file:///tmp/TESTHOST/notes-api/README.md), [far](file://evil.invalid/x.md), [q](?foo=1), [here](#section), [go](#top), [past](../src/app.py:400).", "",
  '<svg width="120" height="14"><a href="https://example.invalid/s"><text y="11">svgweb</text></a><a href="x.md"><text x="60" y="11">svgfile</text></a></svg>', "",
  "```bash", "curl https://example.invalid/dl -o data/x.json", "```", "",
  ...Array.from({ length: 32 }, (_, i) => "line " + (i + 10) + "\n"),   // one paragraph each (a blank line between), so the rendered body scrolls
  '<h2 id="top">Top</h2>', "",
].join("\n");
const NOTES_TEXT = Array.from({ length: 12 }, (_, i) => "note " + (i + 1)).join("\n") + "\n";
// what a highlighter cuts: bash puts `$HOME` and `${ROOT}` in spans of their own; typescript does the same to a template's `${x}`
const RUN_TEXT = ["#!/bin/bash", 'cp "$HOME/docs/a.md" ./out/', "cat ${ROOT}/src/x.py", 'echo "see ./docs/b.md"', ""].join("\n");
const XTS_TEXT = ['import b from "lodash/fp.js";', 'import c from "@scope/pkg/dist/index.js";', 'import d from "./util.ts";', "const s = `tmpl/${x}/file.ts`;", ""].join("\n");
const FILES: Record<string, string> = { [APP]: APP_TEXT, [GUIDE]: GUIDE_TEXT, [NOTES]: NOTES_TEXT, [README]: "# notes-api\n", [CONFIG]: '{"a": 1}\n', [RUN]: RUN_TEXT, [XTS]: XTS_TEXT };

// ── the fake comments host: what the kernel answers a status ask with ─────────────────────────────
// An EMPTY status (nothing kept beside the file) makes the Comments action appear and paints nothing; the MARKED one,
// for app.py, carries one comment anchored on the `data/config.json` passage (a highlight over the whole path link) and
// one pending insertion of the URL on line 1 (a change mark inside the URL anchor).
type StatusLike = Record<string, unknown>;
const UNSENT = { comments: [], replies: [], accepted: 0, rejected: 0, watermark: null };
function emptyStatus(p: string): StatusLike {
  return { verb: "status", root: ROOT, storePath: ROOT + "/.trackchanges/" + p.slice(ROOT.length + 1) + ".json", trackedBy: null, agentTooling: "present",
    fileMtimeNs: "1", storeMtimeNs: null, configMtimeNs: null, store: null, hunks: [], unsent: UNSENT, log: [] };
}
const CFG_AT = APP_TEXT.indexOf("data/config.json"), URL_AT = APP_TEXT.indexOf(URL_SETUP);
const MARKED: StatusLike = { ...emptyStatus(APP), storeMtimeNs: "2",
  store: { v: 3, path: "src/app.py", suggestions: [], comments: [
    { id: "c1", author: "api", authorId: SID, ts: 1757145600000, body: "is this the config we ship?", anchor: makeAnchor(APP_TEXT, { start: CFG_AT, end: CFG_AT + "data/config.json".length }) },
  ] },
  hunks: [{ id: "h1", author: "api", ts: 1757145600000, kind: "ins", curFrom: URL_AT, curTo: URL_AT + URL_SETUP.length, baseFrom: URL_AT, baseTo: URL_AT, oldText: "", newText: URL_SETUP, anchor: null }],
};

/** The Files pane's bundle, plus the panel's registry handed to the page (the chat stand-in's handler asks it, as render.ts does). */
function bundle(): string {
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    stdin: { contents: 'import "./files";\nimport { panelMark } from "./file-comments";\n(window as any).__rompProbe = { panelMark };\n', resolveDir: UI, loader: "ts", sourcefile: "files-probe.ts" },
    bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent",
  });
  return r.outputFiles[0].text;
}
/** The hosting document's OWN click handler, lifted from its source: the chat's document-level anchor opener
 *  (render.ts; capture phase, window.open for a scheme href, panelMark asked first) or the feed's window listener that
 *  returns focus to the chat after a click (feed.ts). Installed over the Files bundle, so the viewer runs under it. */
function hostScript(kind: "chat" | "feed"): string {
  const esbuild = requireCjs("esbuild");
  let ts: string;
  if (kind === "chat") {
    const RENDER = fs.readFileSync(path.join(UI, "render.ts"), "utf8");
    const head = 'document.addEventListener("click", (e) => {\n  const a = (e.target as HTMLElement)?.closest?.("a[href]") as HTMLAnchorElement | null;';
    const start = RENDER.indexOf(head);
    const end = RENDER.indexOf("}, true);", start) + "}, true);".length;
    assert.ok(start > 0 && end > start, "render.ts's document-level anchor opener");
    ts = "const vscodeApi: { postMessage(m: unknown): void } | null = null;\nconst panelMark = (window as any).__rompProbe.panelMark as (t: Element | null) => boolean;\n" + RENDER.slice(start, end);
    // …and the chat's BODY delegate (actions.ts delegate, the real one, on document.body as render.ts installs it), whose
    // openpath opens the todo card's path links. A path link inside the viewer carries the same data-act, so a click the
    // viewer let bubble would open the file there a second time; the handler here records the path, and the chat-page
    // test asserts the record stays empty. render.ts's own handler is pinned by user-todo-title-links.test.ts.
    const ACTIONS = fs.readFileSync(path.join(UI, "actions.ts"), "utf8");
    const fStart = ACTIONS.indexOf("export function flash(el: HTMLElement): void {");
    const dStart = ACTIONS.indexOf("export function delegate(root: HTMLElement | Document, handlers: Record<string, ActionHandler>): void {");
    const dEnd = ACTIONS.indexOf("\n}\n", dStart) + 3;
    assert.ok(fStart > 0 && dStart > fStart && dEnd > dStart, "actions.ts's flash and delegate");
    assert.match(RENDER, /\n    openpath: \(elx\) => openLinkedPath\(elx\),\n/, "render.ts's body delegate routes openpath");
    ts += "\ntype ActionHandler = (el: HTMLElement, ev: Event) => void;\n" + ACTIONS.slice(fStart, dEnd).replace(/^export /gm, "")
      + "\n(window as any).__bodyOpens = [];\ndelegate(document.body, { openpath: (elx) => { (window as any).__bodyOpens.push(elx.dataset.path); } });\n";
  } else {
    const FEED = fs.readFileSync(path.join(UI, "feed.ts"), "utf8");
    const start = FEED.indexOf("function feedWantsKeys(t: EventTarget | null): boolean {");
    const at = FEED.indexOf('window.addEventListener("click", (e) => {', start);
    const end = FEED.indexOf("});", at) + 3;
    assert.ok(start > 0 && at > start && end > at, "feed.ts's window click listener");
    ts = "let kbMode = false;\n" + FEED.slice(start, end);
  }
  return esbuild.transformSync(ts, { loader: "ts", target: "es2020" }).code;
}
const PAGE = (host: "files" | "chat" | "feed") => `<!DOCTYPE html><html><head><meta charset=utf-8><style>
${fs.readFileSync(path.join(UI, "styles.css"), "utf8")}
${fs.readFileSync(path.join(UI, "files-pane.css"), "utf8")}
</style></head><body class=fileview-pane><div id=files-empty></div>
<script>
// the pane's poster, as the kernel page's shim provides it: the panel's status asks are answered by the test's status function
window.__posts = []; window.__status = null;
window.acquireVsCodeApi = function () { return { postMessage: function (m) {
  window.__posts.push(m);
  if (m.type === "fileComments" && window.__status) {
    var s = window.__status(m.path);
    if (s) setTimeout(function () { window.postMessage(Object.assign({ type: "fileCommentsResult", reqId: m.reqId }, s), "*"); }, 0);
  }
} }; };
</script>
<script src=/dist/files.js></script>${host === "files" ? "" : "<script src=/dist/host.js></script>"}</body></html>`;

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

type Info = { text: string | null; path: string | null; line: string | null; act: string | null; href: string | null; target: string | null; rel: string | null; cls: string; title: string | null };
type Harness = {
  page: any; ctx: any; served: Array<{ path: string; sid: string | null }>; errors: string[];
  open: (p: string) => Promise<void>; status: (kind: "empty" | "marked") => Promise<void>; settle: () => Promise<void>;
  linkInfo: (sel: string) => Promise<Info[]>; base: () => Promise<string | null>; newPages: () => number; openCards: () => Promise<number>;
};
async function inBrowser(t: any, host: "files" | "chat" | "feed", body: (h: Harness) => Promise<void>): Promise<void> {
  if (!pw) { t.skip("playwright is not installed under vscode-extension: the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw.chromium.launch(); }
  catch (e) { t.skip("no playwright browser on this box, and the browser leg needs one (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  const errors: string[] = [];
  const served: Array<{ path: string; sid: string | null }> = [];
  try {
    const filesJs = bundle();
    const hostJs = host === "files" ? "" : hostScript(host);
    const ctx = await browser.newContext({ viewport: { width: 900, height: 480 } });
    let pages = 0;
    ctx.on("page", () => { pages++; });
    await ctx.route("https://example.invalid/**", (route: any) => route.fulfill({ status: 200, contentType: "text/html", body: "<title>elsewhere</title>" }));
    const page = await ctx.newPage();
    pages = 0;
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    // on the CONTEXT, not the page: a tab a link opens (an anchor's, window.open's) fetches its own page from here too
    await ctx.route("http://romp.test/**", (route: any) => {
      const u = new URL(route.request().url());
      if (u.pathname === "/files") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: PAGE(host) });
      if (u.pathname === "/dist/files.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: filesJs });
      if (u.pathname === "/dist/host.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: hostJs });
      if (u.pathname === "/file") {                                   // the viewer's fetch: what the kernel serves for a text file
        const p = u.searchParams.get("path") || "";
        if (route.request().method() === "GET" && route.request().isNavigationRequest() === false) served.push({ path: p, sid: u.searchParams.get("sid") });
        const body = FILES[p];                                        // the viewer normalizes `..` itself now: the spelling asked for must be the plain one
        if (body === undefined) return route.fulfill({ status: 404, contentType: "text/plain", body: "no such file: " + p });
        return route.fulfill({ status: 200, contentType: "text/plain; charset=utf-8", headers: { "X-Romp-Mtime-Ns": "1", "X-Romp-Text-Utf8": "1" }, body });
      }
      return route.fulfill({ status: 404, body: "" });
    });
    await page.goto("http://romp.test/files");
    await page.waitForFunction(() => !!(window as any).__rompProbe);
    const status = async (kind: "empty" | "marked") => {
      await page.evaluate(([kind, marked, app]: [string, StatusLike, string]) => {
        (window as any).__status = (p: string) => {
          const root = "/tmp/TESTHOST/notes-api";
          const empty = { verb: "status", root, storePath: root + "/.trackchanges/" + p.slice(root.length + 1) + ".json", trackedBy: null, agentTooling: "present",
            fileMtimeNs: "1", storeMtimeNs: null, configMtimeNs: null, store: null, hunks: [], unsent: { comments: [], replies: [], accepted: 0, rejected: 0, watermark: null }, log: [] };
          return kind === "marked" && p === app ? marked : empty;
        };
      }, [kind, MARKED, APP]);
    };
    await status("empty");
    const open = async (p: string) => {
      await page.evaluate(([p, sid]: string[]) => { window.postMessage({ romp: "viewFile", path: p, sid }, "*"); }, [p, SID]);
      await page.locator("#romp-fileview .fileview-base", { hasText: p.slice(p.lastIndexOf("/") + 1) }).waitFor({ timeout: 10000 });
      await page.locator("#romp-fileview .fileview-body code.hljs .fv-cl, #romp-fileview .fileview-body .fileview-md").first().waitFor({ timeout: 10000 });
    };
    const settle = () => page.evaluate(() => new Promise((r) => requestAnimationFrame(() => setTimeout(r, 80))));
    const linkInfo = (sel: string): Promise<Info[]> => page.evaluate((sel: string) => Array.from(document.querySelectorAll(sel)).map((x) => {
      const e = x as HTMLElement;
      return { text: e.textContent, path: e.dataset.path ?? null, line: e.dataset.line ?? null, act: e.dataset.act ?? null, href: e.getAttribute("href"), target: e.getAttribute("target"), rel: e.getAttribute("rel"), cls: e.getAttribute("class") || "", title: e.getAttribute("title") };
    }), sel);
    const base = () => page.locator("#romp-fileview .fileview-base").textContent();
    const openCards = () => page.evaluate(() => document.querySelectorAll("#romp-fileview .fc-card.open").length);
    await body({ page, ctx, served, errors, open, status, settle, linkInfo, base, newPages: () => pages, openCards });
    assert.deepEqual(errors, [], "no page errors");
    await ctx.close();
  } finally {
    await browser.close();
  }
}
const rowTexts = (page: any) => page.evaluate(() => Array.from(document.querySelectorAll("#romp-fileview code.hljs .fv-cl")).map((r) => r.textContent));
/** The next page the context opens (a new tab from an anchor or window.open, opener or not), and its URL once loaded. */
async function nextTab(h: Harness, act: () => Promise<unknown>): Promise<string> {
  const [tab] = await Promise.all([h.ctx.waitForEvent("page", { timeout: 10000 }), act()]);
  await tab.waitForLoadState();
  const url = tab.url();
  await tab.close();
  return url;
}

test("in a browser: a shown file's URLs and paths are links (a site, a far host and an import stay text); a path link opens the file (into Recent, normalized) and a :line scrolls its row in Raw; a Markdown link to a file opens it; a URL opens a tab; a drag across, inside or from a link selects and opens nothing; Enter opens", async (t) => {
  await inBrowser(t, "files", async (h) => {
    const { page, served, open, settle, linkInfo, base } = h;
    // ── the code view: what the pass marked, on hljs's rows, with every row's text intact ──────────
    await open(APP);
    assert.deepEqual(await rowTexts(page), APP_TEXT.split("\n").slice(0, -1), "every row reads as the file's line");
    const urls = await linkInfo("#romp-fileview a.fv-url");
    assert.deepEqual(urls.map((u) => [u.text, u.href, u.target, u.rel]), [[URL_SETUP, URL_SETUP, "_blank", "noopener noreferrer"]]);
    assert.equal(await page.evaluate(() => document.querySelector("#romp-fileview a.fv-url")!.getAttribute("draggable")), "false");
    const links = await linkInfo("#romp-fileview .file-uri-link");
    assert.deepEqual(links.map((l) => [l.text, l.path, l.line, l.act]), [
      ["../docs/guide.md:30", GUIDE, "30", "openpath"],
      ["data/config.json", CONFIG, null, "openpath"],
      ["file:///tmp/TESTHOST/notes-api/README.md", README, null, "openpath"],
    ], "the three paths, resolved and normalized; and/or, 1/2.5, /api/users, ./foo, the import, www.example.org/…, user/repo.git and file://evil.invalid/… are prose");
    // the dress is light: the link keeps its highlight colour, under a dotted underline that is solid only under the pointer
    const dress = await page.evaluate(() => {
      const l = document.querySelector("#romp-fileview .file-uri-link") as HTMLElement;
      const cs = getComputedStyle(l), ps = getComputedStyle(l.parentElement!);
      return { same: cs.color === ps.color, line: cs.textDecorationLine, style: cs.textDecorationStyle, cursor: cs.cursor };
    });
    assert.deepEqual(dress, { same: true, line: "underline", style: "dotted", cursor: "pointer" });
    await page.locator("#romp-fileview .file-uri-link").nth(1).hover();
    assert.equal(await page.evaluate(() => getComputedStyle(document.querySelectorAll("#romp-fileview .file-uri-link")[1]).textDecorationStyle), "solid", "solid under the pointer");
    assert.equal(served.length, 1, "one fetch so far: the file itself");

    // ── a path link opens the file it names, with the viewer's session, and the pane records it as recent ─
    await page.locator("#romp-fileview .file-uri-link", { hasText: "data/config.json" }).click();
    await page.locator("#romp-fileview .fileview-base", { hasText: "config.json" }).waitFor({ timeout: 10000 });
    assert.deepEqual(served[1], { path: CONFIG, sid: SID }, "the resolved path, the session the file belongs to");
    const recent = await page.evaluate(() => JSON.parse(localStorage.getItem("romp:files-recent") || "[]").map((r: { path: string }) => r.path));
    assert.ok(recent.includes(CONFIG), "opened through the pane's own open: the Recent list has it");

    // ── a :line link: the markdown file opens in Raw for this open, scrolled to its row; the preference is untouched ─
    await open(APP);
    await page.locator("#romp-fileview .file-uri-link", { hasText: "../docs/guide.md:30" }).click();
    await page.locator("#romp-fileview .fileview-base", { hasText: "guide.md" }).waitFor({ timeout: 10000 });
    await page.locator("#romp-fileview code.hljs .fv-cl").first().waitFor({ timeout: 10000 });
    assert.deepEqual(served[served.length - 1], { path: GUIDE, sid: SID }, "the `..` resolved before the fetch");
    const raw = await page.evaluate(() => {
      const on = Array.from(document.querySelectorAll("#romp-fileview .fileview-btn.on")).map((b) => b.textContent);
      const rows = document.querySelectorAll("#romp-fileview code.hljs .fv-cl");
      const body = document.querySelector("#romp-fileview .fileview-body")!.getBoundingClientRect();
      const r30 = rows[29].getBoundingClientRect(), r1 = rows[0].getBoundingClientRect();
      return { on, rows: rows.length, row30In: r30.top >= body.top && r30.bottom <= body.bottom, row1Out: r1.bottom < body.top, pref: localStorage.getItem("romp:fileviewFmt"), notice: !!document.getElementById("fileview-save-err") };
    });
    assert.deepEqual(raw.on, ["Raw"], "the Raw view for this open");
    assert.equal(raw.rows, GUIDE_TEXT.split("\n").length - 1);
    assert.equal(raw.row30In, true, "line 30's row is in view"); assert.equal(raw.row1Out, true, "and the top of the file is scrolled away");
    assert.equal(raw.notice, false, "a line the file has: no notice");
    assert.ok(raw.pref === null || !/"raw"/.test(raw.pref), "the saved preference did not follow");

    // ── rendered markdown: a link to a file becomes a path link, a link to the web stays a tab, bare paths and fenced URLs link ─
    await open(GUIDE);
    await page.locator("#romp-fileview .fileview-md").waitFor({ timeout: 10000 });
    const mdLinks = await linkInfo("#romp-fileview .fileview-md a, #romp-fileview .fileview-md .file-uri-link");
    const byText = (t: string) => mdLinks.find((l) => l.text === t)!;
    assert.deepEqual([byText("the app").href, byText("the app").path, byText("the app").act, /file-uri-link/.test(byText("the app").cls)], [null, APP, "openpath", true], "resolved and normalized");
    assert.deepEqual([byText("the web").href, byText("the web").target, byText("the web").act], ["https://example.invalid/doc", "_blank", null]);
    assert.deepEqual([byText("../src/app.py:3").path, byText("../src/app.py:3").line], [APP, "3"], "a bare path in the prose, with its line");
    assert.deepEqual([byText("https://example.invalid/prose").target, /fv-url/.test(byText("https://example.invalid/prose").cls)], ["_blank", false], "marked's own autolink, not wrapped twice");
    assert.deepEqual([byText("https://example.invalid/dl").href, /fv-url/.test(byText("https://example.invalid/dl").cls)], ["https://example.invalid/dl", true], "a URL inside the fenced block");
    assert.equal(byText("data/x.json").path, ROOT + "/docs/data/x.json");
    const before = served.length;
    await page.locator("#romp-fileview .fileview-md a", { hasText: "the app" }).click();
    await page.locator("#romp-fileview .fileview-base", { hasText: "app.py" }).waitFor({ timeout: 10000 });
    assert.deepEqual(served[before], { path: APP, sid: SID }, "the Markdown link opened the file in the viewer, under its plain path");
    const bar = await page.evaluate(() => ({ dir: document.querySelector("#romp-fileview .fileview-dir")!.textContent, base: document.querySelector("#romp-fileview .fileview-base")!.textContent }));
    assert.deepEqual(bar, { dir: ROOT + "/src/", base: "app.py" }, "the title bar shows the normalized directory");
    const recent2 = await page.evaluate(() => JSON.parse(localStorage.getItem("romp:files-recent") || "[]").map((r: { path: string }) => r.path));
    assert.equal(recent2.filter((p: string) => p.endsWith("/app.py")).length, 1, "Recent holds app.py once, under one spelling: " + JSON.stringify(recent2));

    // ── a URL anchor opens a new tab and the viewer stays; nothing is fetched ──────────────────────
    await open(APP);
    const n0 = served.length;
    assert.equal(await nextTab(h, () => page.locator("#romp-fileview a.fv-url").click()), URL_SETUP);
    assert.equal(await base(), "app.py", "the viewer is still up");
    assert.equal(served.length, n0, "a URL fetches no file");

    // ── selections: a drag across a link selects; a drag that begins and ends on the link selects; one that begins on a URL anchor selects; none opens ─
    const row3 = page.locator("#romp-fileview code.hljs .fv-cl").nth(2);
    const link = page.locator("#romp-fileview .file-uri-link", { hasText: "data/config.json" });
    const rb = (await row3.boundingBox())!, lb = (await link.boundingBox())!;
    await page.mouse.move(rb.x + 2, rb.y + rb.height / 2); await page.mouse.down();
    await page.mouse.move(lb.x + lb.width + 20, lb.y + lb.height / 2, { steps: 10 }); await page.mouse.up();
    await settle();
    let sel = await page.evaluate(() => getSelection()!.toString());
    assert.ok(sel.includes("data/config.json"), "the drag across the link selected its text: " + JSON.stringify(sel));
    assert.equal(served.length, n0, "and opened nothing");
    await page.evaluate(() => getSelection()!.removeAllRanges());
    await page.mouse.move(lb.x + 3, lb.y + lb.height / 2); await page.mouse.down();
    await page.mouse.move(lb.x + lb.width - 3, lb.y + lb.height / 2, { steps: 10 }); await page.mouse.up();
    await settle();
    sel = await page.evaluate(() => getSelection()!.toString());
    assert.ok(sel.length > 3 && "data/config.json".includes(sel), "a drag inside the link selects its text (the press does not focus the span): " + JSON.stringify(sel));
    assert.equal(served.length, n0, "the click that ends the drag opens nothing");
    assert.equal(await base(), "app.py");
    await page.evaluate(() => getSelection()!.removeAllRanges());
    const ub = (await page.locator("#romp-fileview a.fv-url").boundingBox())!;
    const tabs0 = h.newPages();
    await page.mouse.move(ub.x + 8, ub.y + ub.height / 2); await page.mouse.down();
    await page.mouse.move(ub.x + ub.width - 8, ub.y + ub.height / 2, { steps: 10 }); await page.mouse.up();
    await settle();
    sel = await page.evaluate(() => getSelection()!.toString());
    assert.ok(sel.length > 5 && URL_SETUP.includes(sel), "a drag that starts inside the URL anchor selects its text, not a link drag: " + JSON.stringify(sel));
    assert.equal(h.newPages(), tabs0, "and opens no tab");
    await page.evaluate(() => getSelection()!.removeAllRanges());

    // ── the keyboard: a focused path link opens on Enter ─────────────────────────────────────────
    await link.focus();
    await page.keyboard.press("Enter");
    await page.locator("#romp-fileview .fileview-base", { hasText: "config.json" }).waitFor({ timeout: 10000 });
    assert.deepEqual(served[served.length - 1], { path: CONFIG, sid: SID });
  });
});

test("in a browser, through the real sanitizer: a same-directory `notes.md:7` and a `file:///` target open; a far host is a dead link that says why; a query alone opens a tab; a section link never moves the document (and scrolls to an anchor the document has); an inline SVG's anchors are marked; a line past the end says so", async (t) => {
  await inBrowser(t, "files", async (h) => {
    const { page, served, open, linkInfo, base } = h;
    await open(GUIDE);
    await page.locator("#romp-fileview .fileview-md").waitFor({ timeout: 10000 });
    const md = await linkInfo("#romp-fileview .fileview-md a");
    const byText = (t: string) => md.find((l) => l.text === t)!;
    assert.deepEqual([byText("same").href, byText("same").path, byText("same").line, byText("same").title], [null, NOTES, "7", "Open " + NOTES + ":7"], "the hook put ./ before it, so the sanitizer kept it");
    assert.deepEqual([byText("uri").href, byText("uri").path, byText("uri").act], [null, README, "openpath"], "a local file:// URI is its path");
    assert.deepEqual([byText("far").href, byText("far").act, /fv-dead/.test(byText("far").cls), byText("far").title], [null, null, true, DEAD_LINK_TITLE], "the sanitizer removed it: dead, and it says why");
    assert.deepEqual([byText("q").href, byText("q").target, byText("q").rel, byText("q").act], ["?foo=1", "_blank", "noopener noreferrer", null], "a query alone: a tab, as main had it");
    assert.deepEqual([byText("here").href, /fv-frag/.test(byText("here").cls), /fv-dead/.test(byText("here").cls), byText("here").title], ["#section", true, true, noSectionTitle("section")]);
    assert.deepEqual([byText("go").href, /fv-frag/.test(byText("go").cls), /fv-dead/.test(byText("go").cls), byText("go").title], ["#top", true, false, "Go to top"]);
    const svg = await linkInfo("#romp-fileview .fileview-md svg a");
    assert.deepEqual(svg.map((a) => [a.text, a.href, a.target, a.rel, /file-uri-link/.test(a.cls), a.act, a.path, a.title]), [
      ["svgweb", "https://example.invalid/s", "_blank", "noopener", false, null, null, null],
      ["svgfile", null, null, null, true, "openpath", ROOT + "/docs/x.md", "Open " + ROOT + "/docs/x.md"],
    ], "an SVG <a> takes its attributes too");
    const dead = await page.evaluate(() => getComputedStyle(Array.from(document.querySelectorAll("#romp-fileview .fileview-md a")).find((a) => a.textContent === "far")!).cursor);
    assert.equal(dead, "help", "the dead link's dress says there is a reason to read");
    // a query alone: a new tab, this document untouched
    const url0 = page.url();
    const qTab = await nextTab(h, () => page.locator("#romp-fileview .fileview-md a", { hasText: "q" }).click());
    assert.equal(new URL(qTab).search, "?foo=1");
    assert.equal(page.url(), url0, "the pane's own document did not navigate"); assert.equal(await base(), "guide.md");
    // a section link: nothing moves the document's location; a target the document has is scrolled to
    const tabs = h.newPages();
    await page.locator("#romp-fileview .fileview-md a", { hasText: "here" }).click();
    await h.settle();
    assert.equal(page.url(), url0, "no hash on the document"); assert.equal(await base(), "guide.md"); assert.equal(h.newPages(), tabs);
    const topBefore = await page.evaluate(() => { const b = document.querySelector("#romp-fileview .fileview-body")!.getBoundingClientRect(); const r = document.getElementById("top")!.getBoundingClientRect(); return r.top < b.bottom; });
    assert.equal(topBefore, false, "the anchor is below the fold to begin with");
    await page.locator("#romp-fileview .fileview-md a", { hasText: "go" }).click();
    await h.settle();
    const topAfter = await page.evaluate(() => { const b = document.querySelector("#romp-fileview .fileview-body")!.getBoundingClientRect(); const r = document.getElementById("top")!.getBoundingClientRect(); return r.top >= b.top - 1 && r.bottom <= b.bottom; });
    assert.equal(topAfter, true, "scrolled to the anchor"); assert.equal(page.url(), url0);
    // the same-directory :line target opens its file, in Raw, at the line
    const n = served.length;
    await page.locator("#romp-fileview .fileview-md a", { hasText: "same" }).click();
    await page.locator("#romp-fileview .fileview-base", { hasText: "notes.md" }).waitFor({ timeout: 10000 });
    await page.locator("#romp-fileview code.hljs .fv-cl").first().waitFor({ timeout: 10000 });
    assert.deepEqual(served[n], { path: NOTES, sid: SID });
    assert.deepEqual(await page.evaluate(() => Array.from(document.querySelectorAll("#romp-fileview .fileview-btn.on")).map((b) => b.textContent)), ["Raw"]);
    // the file:// target opens its file
    await open(GUIDE);
    await page.locator("#romp-fileview .fileview-md a", { hasText: "uri" }).click();
    await page.locator("#romp-fileview .fileview-base", { hasText: "README.md" }).waitFor({ timeout: 10000 });
    assert.deepEqual(served[served.length - 1], { path: README, sid: SID });
    // a line past the end: the last row, and a notice that says so
    await open(GUIDE);
    await page.locator("#romp-fileview .fileview-md a", { hasText: "past" }).click();
    await page.locator("#romp-fileview .fileview-base", { hasText: "app.py" }).waitFor({ timeout: 10000 });
    await page.locator("#fileview-save-err").waitFor({ timeout: 10000 });
    assert.equal(await page.locator("#fileview-save-err").textContent(), "Line 400 is past the end of this file, which has 7 lines; showing the last line.");
    await page.locator("#romp-fileview .fileview-md a", { hasText: "far" }).count();   // the dead link: nothing to click on (no href, no act); its title is the answer
  });
});

test("in a browser, over the real highlighter: a substitution span cannot turn a path's tail into a link, and an import's specifier stays text", async (t) => {
  await inBrowser(t, "files", async (h) => {
    const { page, open, linkInfo } = h;
    await open(RUN);
    assert.ok(await page.evaluate(() => document.querySelectorAll("#romp-fileview code.hljs .hljs-variable").length) >= 2, "bash's grammar put $HOME and ${ROOT} in spans of their own");
    assert.deepEqual((await linkInfo("#romp-fileview .file-uri-link")).map((l) => [l.text, l.path]), [["./docs/b.md", ROOT + "/scripts/docs/b.md"]], "no /docs/a.md, no /src/x.py");
    assert.deepEqual(await rowTexts(page), RUN_TEXT.split("\n").slice(0, -1));
    await open(XTS);
    assert.ok(await page.evaluate(() => document.querySelectorAll("#romp-fileview code.hljs .hljs-subst").length) >= 1, "typescript's grammar put ${x} in a span of its own");
    assert.deepEqual((await linkInfo("#romp-fileview .file-uri-link")).map((l) => [l.text, l.path]), [["./util.ts", ROOT + "/ui/util.ts"]], "the relative import links; lodash/fp.js, @scope/pkg/dist/index.js and the template's /file.ts do not");
  });
});

test("in a browser, with the comments panel's marks over the links: a plain click or Enter on a mark opens the card and nothing else (no tab, no file); a Cmd/Ctrl-click or a middle-click on a marked link opens the link's own tab and no card", async (t) => {
  await inBrowser(t, "files", async (h) => {
    const { page, served, open, status, settle, base, openCards } = h;
    await status("marked");
    await open(APP);
    const button = page.locator("#romp-fileview .fileview-fc:not([hidden]) button");
    await button.waitFor({ timeout: 10000 });
    await button.click();
    const hl = page.locator("#romp-fileview .file-uri-link mark.fc-hl[data-act=fcopen]");
    const ins = page.locator("#romp-fileview a.fv-url mark.fc-ins[data-act=fcchange]");
    await hl.waitFor({ timeout: 10000 }); await ins.waitFor({ timeout: 10000 });
    assert.deepEqual(await rowTexts(page), APP_TEXT.split("\n").slice(0, -1), "the marks changed no character");
    assert.equal(await hl.textContent(), "data/config.json", "the highlight covers the whole link"); assert.equal(await ins.textContent(), URL_SETUP, "the change mark covers the whole URL");
    const n0 = served.length, tabs0 = h.newPages();
    // a plain click on the change mark inside the URL anchor: the card, and no tab
    await ins.click(); await settle();
    assert.ok(await openCards() >= 1, "the change card opened");
    assert.equal(h.newPages(), tabs0, "no tab opened with it"); assert.equal(await base(), "app.py"); assert.equal(served.length, n0);
    // Enter on the focused mark: the same route (KEY_ACTS clicks it)
    await page.evaluate(() => { for (const c of document.querySelectorAll("#romp-fileview .fc-card.open .fc-card-head")) (c as HTMLElement).click(); });   // fold the cards first
    await settle(); assert.equal(await openCards(), 0);
    await ins.focus(); await page.keyboard.press("Enter"); await settle();
    assert.ok(await openCards() >= 1, "Enter opened the card"); assert.equal(h.newPages(), tabs0, "and no tab");
    // a plain click on the highlight inside the path link: the card, and no file
    await page.evaluate(() => { for (const c of document.querySelectorAll("#romp-fileview .fc-card.open .fc-card-head")) (c as HTMLElement).click(); });
    await settle(); assert.equal(await openCards(), 0);
    await hl.click(); await settle();
    assert.equal(await openCards(), 1, "the comment card opened"); assert.equal(await base(), "app.py"); assert.equal(served.length, n0, "no file fetched");
    await page.evaluate(() => { for (const c of document.querySelectorAll("#romp-fileview .fc-card.open .fc-card-head")) (c as HTMLElement).click(); });
    await settle(); assert.equal(await openCards(), 0);
    // a Ctrl-click on the highlight: the LINK's own tab, off the kernel's /file route, and no card
    const linkTab = await nextTab(h, () => hl.click({ modifiers: ["Control"] }));
    const lu = new URL(linkTab);
    assert.deepEqual([lu.pathname, lu.searchParams.get("path"), lu.searchParams.get("sid")], ["/file", CONFIG, SID], "the file in a tab of its own");
    assert.equal(await openCards(), 0, "no card"); assert.equal(await base(), "app.py", "the viewer kept its file");
    // a middle-click on the highlighted link: the same tab
    const midTab = await nextTab(h, () => hl.click({ button: "middle" }));
    assert.equal(new URL(midTab).searchParams.get("path"), CONFIG);
    assert.equal(await openCards(), 0); assert.equal(await base(), "app.py");
    // a Ctrl-click on the change mark inside the URL anchor: one tab to the URL, no card
    const urlTab = await nextTab(h, () => ins.click({ modifiers: ["Control"] }));
    assert.equal(urlTab, URL_SETUP); assert.equal(await openCards(), 0); assert.equal(await base(), "app.py");
    // Ctrl+Enter on the focused path link: the keyboard's own tab
    const kbTab = await nextTab(h, async () => { await page.locator("#romp-fileview .file-uri-link", { hasText: "data/config.json" }).focus(); await page.keyboard.press("Control+Enter"); });
    assert.equal(new URL(kbTab).searchParams.get("path"), CONFIG); assert.equal(await base(), "app.py");
    // the plain keyboard route on the link itself (not the mark): Enter opens the file in the viewer, as before
    await page.locator("#romp-fileview .file-uri-link", { hasText: "data/config.json" }).focus(); await page.keyboard.press("Enter");
    await page.locator("#romp-fileview .fileview-base", { hasText: "config.json" }).waitFor({ timeout: 10000 });
    assert.deepEqual(served[served.length - 1], { path: CONFIG, sid: SID });
  });
});

test("in a browser, a comment typed and not yet saved survives a link click: the viewer asks in the editor's words; declined, the file and the note stay; accepted, the link is followed", async (t) => {
  await inBrowser(t, "files", async (h) => {
    const { page, served, open, settle, base } = h;
    await open(APP);
    const button = page.locator("#romp-fileview .fileview-fc:not([hidden]) button");
    await button.waitFor({ timeout: 10000 });
    await button.click();
    await page.locator("#romp-fileview .fc-panel").waitFor({ timeout: 10000 });
    // a selection across the link offers Comment; the composer's passage highlight is painted over the link
    const row3 = page.locator("#romp-fileview code.hljs .fv-cl").nth(2);
    const link = page.locator("#romp-fileview .file-uri-link", { hasText: "data/config.json" });
    const rb = (await row3.boundingBox())!, lb = (await link.boundingBox())!;
    await page.mouse.move(rb.x + 2, rb.y + rb.height / 2); await page.mouse.down();
    await page.mouse.move(lb.x + lb.width + 20, lb.y + lb.height / 2, { steps: 10 }); await page.mouse.up();
    const float = page.locator("button.fc-float");
    await float.waitFor({ state: "visible", timeout: 10000 });
    await float.click();
    await page.locator("#romp-fileview .fc-input").waitFor({ timeout: 10000 });
    assert.ok(await page.locator("#romp-fileview .file-uri-link mark.fc-presel").count() >= 1, "the passage highlight reaches into the link");
    await page.keyboard.type("is this the config we ship");
    assert.equal(await page.locator("#romp-fileview .fc-input").inputValue(), "is this the config we ship");
    // the link under the pending passage: the ask, declined
    const asked: string[] = [];
    page.once("dialog", (d: any) => { asked.push(d.message()); void d.dismiss(); });
    const n0 = served.length;
    await link.click(); await settle();
    assert.deepEqual(asked, ["Discard the unsaved comment on app.py?"], "the editor's ask, for the note");
    assert.equal(await base(), "app.py", "declined: the file stays"); assert.equal(served.length, n0, "nothing fetched");
    assert.equal(await page.locator("#romp-fileview .fc-input").inputValue(), "is this the config we ship", "and the note stays");
    // accepted: the link is followed
    page.once("dialog", (d: any) => { asked.push(d.message()); void d.accept(); });
    await link.click();
    await page.locator("#romp-fileview .fileview-base", { hasText: "config.json" }).waitFor({ timeout: 10000 });
    assert.equal(asked.length, 2); assert.deepEqual(served[served.length - 1], { path: CONFIG, sid: SID });
    // with nothing typed there is no ask: a link click opens at once
    await open(APP);
    await page.locator("#romp-fileview .fileview-fc:not([hidden]) button").click();
    await page.locator("#romp-fileview .fc-panel").waitFor({ timeout: 10000 });
    await page.locator("#romp-fileview [data-act=fcfile]").click();
    await page.locator("#romp-fileview .fc-input").waitFor({ timeout: 10000 });
    let dialogs = 0;
    page.on("dialog", (d: any) => { dialogs++; void d.dismiss(); });
    await link.click();
    await page.locator("#romp-fileview .fileview-base", { hasText: "config.json" }).waitFor({ timeout: 10000 });
    assert.equal(dialogs, 0, "an empty composer has nothing to lose");
  });
});

test("in a browser, under the chat's own document-level opener and its body delegate: a plain URL click is one tab, a plain click on a change mark inside the URL opens the card and no tab, a modified click on that mark is one tab and no card, and a path link (a span or a Markdown anchor) opens in place ONCE, never reaching the delegate's openpath", async (t) => {
  await inBrowser(t, "chat", async (h) => {
    const { page, served, open, status, settle, base, openCards } = h;
    await open(APP);
    const n0 = served.length;
    assert.equal(await nextTab(h, () => page.locator("#romp-fileview a.fv-url").click()), URL_SETUP, "the chat's capture-phase opener: one tab");
    assert.equal(await base(), "app.py"); assert.equal(served.length, n0);
    await status("marked");
    await open(APP);
    await page.locator("#romp-fileview .fileview-fc:not([hidden]) button").click();
    const ins = page.locator("#romp-fileview a.fv-url mark.fc-ins[data-act=fcchange]");
    await ins.waitFor({ timeout: 10000 });
    const tabs0 = h.newPages();
    await ins.click(); await settle();
    assert.ok(await openCards() >= 1, "the card opened"); assert.equal(h.newPages(), tabs0, "the opener yielded to the mark and the anchor did not open its tab either");
    await page.evaluate(() => { for (const c of document.querySelectorAll("#romp-fileview .fc-card.open .fc-card-head")) (c as HTMLElement).click(); });
    await settle(); assert.equal(await openCards(), 0);
    assert.equal(await nextTab(h, () => ins.click({ modifiers: ["Control"] })), URL_SETUP, "a modified click on the mark: the link's tab, once");
    assert.equal(await openCards(), 0, "and no card");
    await page.locator("#romp-fileview .file-uri-link", { hasText: "../docs/guide.md:30" }).click();
    await page.locator("#romp-fileview .fileview-base", { hasText: "guide.md" }).waitFor({ timeout: 10000 });
    assert.deepEqual(served[served.length - 1], { path: GUIDE, sid: SID }, "a path link (no href) is the viewer's, not the opener's");
    const bodyOpens = () => page.evaluate(() => (window as any).__bodyOpens as string[]);
    assert.deepEqual(await bodyOpens(), [], "the viewer stopped the click: the body delegate's openpath (the todo card's route) never saw it, so the file opened once");
    await open(GUIDE);
    await page.locator("#romp-fileview .fileview-md").waitFor({ timeout: 10000 });
    await page.locator("#romp-fileview .fileview-md a", { hasText: "the app" }).click();
    await page.locator("#romp-fileview .fileview-base", { hasText: "app.py" }).waitFor({ timeout: 10000 });
    assert.deepEqual(served[served.length - 1], { path: APP, sid: SID });
    assert.deepEqual(await bodyOpens(), [], "a Markdown anchor marked as a path link: the same, one open");
    await page.locator("#romp-fileview .file-uri-link", { hasText: "data/config.json" }).click({ modifiers: ["Control"] });
    await settle();
    assert.deepEqual(await bodyOpens(), [], "a modified click on a path link: its own tab or the viewer, and the delegate saw nothing");
    // The reachable double: an open the viewer's guard DECLINES (an unsaved comment) leaves the viewer, and the span, in
    // the document, so a click that bubbled on would reach the delegate and open the very file the person just kept
    // away from (a second ask on the web, the editor in VS Code). A plain open tears the old viewer down synchronously,
    // which detaches the span before the delegate's contains() check; this is the case the stop is for.
    await status("empty"); await open(APP);
    await page.locator("#romp-fileview .fileview-fc:not([hidden]) button").click();
    await page.locator("#romp-fileview .fc-panel").waitFor({ timeout: 10000 });
    const row3 = page.locator("#romp-fileview code.hljs .fv-cl").nth(2);
    const link = page.locator("#romp-fileview .file-uri-link", { hasText: "data/config.json" });
    const rb = (await row3.boundingBox())!, lb = (await link.boundingBox())!;
    await page.mouse.move(rb.x + 2, rb.y + rb.height / 2); await page.mouse.down();
    await page.mouse.move(lb.x + lb.width + 20, lb.y + lb.height / 2, { steps: 10 }); await page.mouse.up();
    const float = page.locator("button.fc-float");
    await float.waitFor({ state: "visible", timeout: 10000 });
    await float.click();
    await page.locator("#romp-fileview .fc-input").waitFor({ timeout: 10000 });
    await page.keyboard.type("keep this one");
    const asked: string[] = [];
    page.once("dialog", (d: any) => { asked.push(d.message()); void d.dismiss(); });
    const n1 = served.length;
    await link.click(); await settle();
    assert.equal(asked.length, 1, "the viewer asked"); assert.equal(await base(), "app.py", "declined: the file stays"); assert.equal(served.length, n1, "nothing fetched");
    assert.deepEqual(await bodyOpens(), [], "declined, with the span still in the document: the delegate saw nothing, so the click stopped at the viewer and the declined file was not opened behind the person's back");
    // the recorder is live, so the empties above mean something: a span outside the viewer reaches the delegate
    assert.deepEqual(await page.evaluate(() => {
      const s = document.createElement("span"); s.dataset.act = "openpath"; s.dataset.path = "/tmp/TESTHOST/elsewhere.md";
      document.body.appendChild(s); s.click(); s.remove();
      return ((window as any).__bodyOpens as string[]).splice(0);
    }), ["/tmp/TESTHOST/elsewhere.md"], "the body delegate is installed and live");
  });
});

test("in a browser, under the feed's window click listener: a path link opens in place and a URL opens a tab", async (t) => {
  await inBrowser(t, "feed", async (h) => {
    const { page, served, open, base } = h;
    await open(APP);
    await page.locator("#romp-fileview .file-uri-link", { hasText: "data/config.json" }).click();
    await page.locator("#romp-fileview .fileview-base", { hasText: "config.json" }).waitFor({ timeout: 10000 });
    assert.deepEqual(served[served.length - 1], { path: CONFIG, sid: SID });
    await open(APP);
    const n0 = served.length;
    assert.equal(await nextTab(h, () => page.locator("#romp-fileview a.fv-url").click()), URL_SETUP);
    assert.equal(await base(), "app.py"); assert.equal(served.length, n0);
  });
});

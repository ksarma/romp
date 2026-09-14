// A todo link with a target after its path, in a browser (Slice 6 of plans/markdown-viewer.md, item 4): a todo card's
// text names `docs/report.md#results`, and the click opens the file AT that heading; `docs/report.md:13` opens the
// Raw view at that row; `docs/report.md#nowhere` opens the file and the notice bar names the section it could not
// find; a bare path opens as it always did. The chat's own code runs the click: render.ts's openPath, openLinkedPath,
// linkTodoLinePaths and linkTodoDetailPaths and its body delegate's openpath handler, lifted verbatim and transpiled
// over a prelude that stands in for the chat's module state (its tabs, its settings, its pane set), installed over the
// Files pane's real bundle (the shared viewer, the real walk with `targetSuffix`, the real linkTarget, the real
// fileLinkRoute and openFileClick), the idiom file-view-links-browser.test.ts set for the chat's anchor opener. Two
// pages: an unframed one, where the route is "here" and the viewer opens in the document, and one inside an iframe of a
// recording parent, where the File-links preference names the Files pane and the click posts the shell's viewFile relay
// with `at`. Skips LOUDLY without a playwright browser (CI installs none). Synthetic values only: the notes-api world, a
// placeholder session id, an invented report.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";

const EXT = process.cwd();                                        // npm test runs in vscode-extension
const requireCjs = createRequire(path.join(EXT, "package.json"));   // playwright and esbuild from the extension, wherever this bundle was written
const UI = path.resolve(EXT, "..", "ui", "webview");
const SID = "11111111-2222-3333-4444-555555555555";
const REL = "docs/report.md";
const ABS = "/repo/notes-api/docs/report.md";
const PARA = (i: number): string => `Paragraph ${i}: ` + "lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor ".repeat(2).trim() + ".";
// the report: a title, sixty paragraphs, the Results heading, forty more (so the heading can reach the body's top)
const REPORT = "# Report\n\n" + Array.from({ length: 60 }, (_, i) => PARA(i + 1)).join("\n\n") + "\n\n## Results\n\n"
  + Array.from({ length: 40 }, (_, i) => PARA(61 + i)).join("\n\n") + "\n";
const ROW = 13;                                                   // a row of the Raw view: paragraph 6 (line 1 the title, a blank line between paragraphs)
const TODO_TEXT = `see ${REL}#results and ${REL}:${ROW}, then ${REL}#nowhere, plus ${REL} alone`;
const FILES: Record<string, string> = { [REL]: REPORT, [ABS]: REPORT };

const BUILD = { bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
  nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent" };
/** The Files pane's bundle plus what the chat's lifted code names from it, on window.__rompProbe. */
function filesBundle(): string {
  const contents = [
    'import "./files";',
    'import { linkifyPathTokens, linkTarget } from "./path-links";',
    'import { linkifyUrls } from "./url-links";',
    'import { openFileClick } from "./file-view";',
    'import { fileLinkRoute } from "./file-route";',
    'import { delegate } from "./actions";',
    "(window as any).__rompProbe = { linkifyPathTokens, linkTarget, linkifyUrls, openFileClick, fileLinkRoute, delegate };",
  ].join("\n");
  const r = requireCjs("esbuild").buildSync({ ...BUILD, stdin: { contents, resolveDir: UI, loader: "ts", sourcefile: "files-probe.ts" } });
  return r.outputFiles[0].text;
}
const RENDER = fs.readFileSync(path.join(UI, "render.ts"), "utf8");
/** A verbatim function of render.ts, from its `function name(` line to its closing brace. */
function liftRender(name: string): string {
  const at = RENDER.indexOf("\nfunction " + name + "(");
  const end = RENDER.indexOf("\n}\n", at);
  assert.ok(at > 0 && end > at, "anchor not found: render.ts's " + name + " moved; re-anchor");
  return RENDER.slice(at, end + 3);
}
/** The chat's click over the Files bundle: a prelude for the module state the lifted code reads, then the code itself. The
 *  route and the pane set are read at CLICK time off window.__route and window.__filesOn, so one page runs both routes. */
function chatScript(): string {
  const bodyMap = RENDER.slice(RENDER.indexOf("delegate(document.body, {"), RENDER.indexOf("delegate(tabs, {"));
  const ln = bodyMap.split("\n").find((l) => /^\s*openpath: /.test(l));
  assert.ok(ln, "render.ts's body delegate routes openpath (the handler line moved; re-anchor)");
  const handler = ln!.trim().replace(/^openpath:\s*/, "").replace(/,$/, "");
  const ts = [
    "const P = (window as any).__rompProbe;",
    "const vscodeApi = { postMessage: (m: unknown) => { (window as any).__hostPosts.push(m); } };",   // the web shim's poster: truthy, as openPath requires
    `const activeId: string | null = ${JSON.stringify(SID)};`,
    `const sessions = new Map<string, { name: string; color: { bg: string; fg: string } | null }>([[${JSON.stringify(SID)}, { name: "api", color: { bg: "#123456", fg: "#ffffff" } }]]);`,
    "const tabMeta = new Map<string, { name: string; color: { bg: string; fg: string } | null }>();",
    'const settings = { get fileLinkPane() { return (window as any).__route || "here"; } };',
    "const panesOn: Record<string, boolean> = { get files() { return !!(window as any).__filesOn; } } as any;",
    "const fileLinkRoute = P.fileLinkRoute, openFileClick = P.openFileClick, linkifyUrls = P.linkifyUrls, linkifyPathTokens = P.linkifyPathTokens, linkTarget = P.linkTarget, delegate = P.delegate;",
    // the detail's linker is the transcript's figure pass; its walk is what is under test, so the pass is the walk alone here
    "const linkifyFileUris = (node: HTMLElement, _a: unknown, _b: unknown, _c: unknown, _d: unknown, sid: string | null, _delegated: boolean, walkOpts?: unknown) => { linkifyPathTokens(node, sid, undefined, walkOpts); };",
    liftRender("openPath"), liftRender("openLinkedPath"), liftRender("linkTodoLinePaths"), liftRender("linkTodoDetailPaths"),
    "const openpath: (elx: HTMLElement, ev: Event) => void = " + handler + ";",
    "delegate(document.body, { openpath });",
    "(window as any).__linkLine = (id: string) => { linkTodoLinePaths(document.getElementById(id) as HTMLElement, " + JSON.stringify(SID) + "); };",
    "(window as any).__linkDetail = (id: string) => { linkTodoDetailPaths(document.getElementById(id) as HTMLElement, " + JSON.stringify(SID) + "); };",
  ].join("\n");
  return requireCjs("esbuild").transformSync(ts, { loader: "ts", target: "es2020" }).code;
}
const PAGE = `<!DOCTYPE html><html><head><meta charset=utf-8><style>
${fs.readFileSync(path.join(UI, "styles.css"), "utf8")}
${fs.readFileSync(path.join(UI, "files-pane.css"), "utf8")}
</style></head><body class=fileview-pane><div id=files-empty></div>
<div class="todo-card"><div class="ut-item"><div class="ut-line"><span class="ut-text" data-act="uttoggle" id="t-line">${TODO_TEXT}</span></div>
<div class="ut-detail open" id="t-detail">${TODO_TEXT}</div></div></div>
<script>window.__posts=[];window.__hostPosts=[];window.acquireVsCodeApi=function(){return{postMessage:function(m){window.__posts.push(m);}}};</script>
<script src=/dist/files.js></script><script src=/dist/chat.js></script></body></html>`;
const FRAMED = `<!DOCTYPE html><html><head><meta charset=utf-8></head><body>
<script>window.__relay=[];window.addEventListener("message",function(e){window.__relay.push(e.data);});</script>
<iframe id=f-files src="/files" style="width:900px;height:500px"></iframe></body></html>`;

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

type Info = { text: string | null; path: string | null; line: string | null; frag: string | null };
async function inBrowser(t: any, body: (page: any, errors: string[]) => Promise<void>): Promise<void> {
  if (!pw) { t.skip("playwright is not installed under vscode-extension: the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw.chromium.launch(); }
  catch (e) { t.skip("no playwright browser on this box, and the browser leg needs one (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  const errors: string[] = [];
  try {
    const filesJs = filesBundle(), chatJs = chatScript();
    const ctx = await browser.newContext({ viewport: { width: 900, height: 500 } });
    const page = await ctx.newPage();
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    await ctx.route("http://romp.test/**", (route: any) => {
      const u = new URL(route.request().url());
      if (u.pathname === "/files") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: PAGE });
      if (u.pathname === "/framed") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: FRAMED });
      if (u.pathname === "/dist/files.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: filesJs });
      if (u.pathname === "/dist/chat.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: chatJs });
      if (u.pathname === "/file") {
        const p = u.searchParams.get("path") || "";
        const text = FILES[p];
        if (text === undefined) return route.fulfill({ status: 404, contentType: "text/plain", body: "no such file: " + p });
        return route.fulfill({ status: 200, contentType: "text/plain; charset=utf-8", headers: { "X-Romp-Mtime-Ns": "1", "X-Romp-Text-Utf8": "1" }, body: text });
      }
      return route.fulfill({ status: 404, body: "" });
    });
    await body(page, errors);
    assert.deepEqual(errors, [], "no page errors");
    await ctx.close();
  } finally {
    await browser.close();
  }
}
const frames = (page: any, n = 2): Promise<null> => page.evaluate((k: number) => new Promise<null>((r) => { const f = () => (k-- <= 0 ? r(null) : requestAnimationFrame(f)); f(); }), n);
const linkInfo = (frame: any, sel: string): Promise<Info[]> => frame.evaluate((sel: string) => Array.from(document.querySelectorAll(sel)).map((x) => {
  const e = x as HTMLElement; return { text: e.textContent, path: e.dataset.path ?? null, line: e.dataset.line ?? null, frag: e.dataset.frag ?? null };
}), sel);
const EXPECT: Info[] = [
  { text: REL + "#results", path: REL, line: null, frag: "results" },
  { text: REL + ":" + ROW, path: REL, line: String(ROW), frag: null },
  { text: REL + "#nowhere", path: REL, line: null, frag: "nowhere" },
  { text: REL, path: REL, line: null, frag: null },
];
/** The heading's top edge measured from the body's top, and the body's scrollTop. */
const headingTop = (page: any, id: string) => page.evaluate((id: string) => {
  const body = document.querySelector("#romp-fileview .fileview-body") as HTMLElement, h = document.getElementById(id);
  if (!body || !h) return null;
  return { top: Math.round((h.getBoundingClientRect().top - body.getBoundingClientRect().top) * 10) / 10, scrollTop: body.scrollTop };
}, id);
async function closeViewer(page: any): Promise<void> {
  await page.click("#romp-fileview .fileview-close");
  await page.waitForFunction(() => !document.getElementById("romp-fileview"), null, { timeout: 5000 });
}

test("in a browser: a todo's text links its targets; a heading target opens the file AT the heading, a line target the Raw row, a missing section opens the file and says so, a bare path opens at the top (the route here, in the document)", async (t) => {
  await inBrowser(t, async (page, errors) => {
    await page.goto("http://romp.test/files");
    await page.waitForFunction(() => !!(window as any).__rompProbe && !!(window as any).__linkLine);
    await page.evaluate(() => { (window as any).__linkLine("t-line"); (window as any).__linkDetail("t-detail"); });
    assert.deepEqual(await linkInfo(page, "#t-line .file-uri-link"), EXPECT, "the line's walk (linkTodoLinePaths) reads the targets");
    assert.deepEqual(await linkInfo(page, "#t-detail .file-uri-link"), EXPECT, "the detail's walk (linkTodoDetailPaths, through linkifyFileUris) reads them too");
    assert.equal(await page.evaluate(() => document.getElementById("t-line")!.textContent), TODO_TEXT, "the text reads as written: the suffixes moved into the links, none dropped");
    // ── the heading: the viewer opens in this document and the first Rendered paint lands on it
    await page.locator("#t-line .file-uri-link", { hasText: REL + "#results" }).click();
    await page.locator("#romp-fileview .fileview-md h2#md-results").waitFor({ timeout: 10000 });
    await frames(page, 3);
    const at = await headingTop(page, "md-results");
    // the heading's border box sits inside the 10px scroll-margin-top the sheets give a landed heading (styles.css and feed.css,
    // `.fileview-md h1 ... h6 { scroll-margin-top: 10px; }`), the bound md-config-fragment-landing-browser.test.ts reads too
    assert.ok(at && at.top >= -1 && at.top <= 12, "the Results heading's top sits at the body's top edge, under its scroll margin: " + JSON.stringify(at));
    assert.ok(at!.scrollTop > 100, "…which took a scroll (the heading is sixty paragraphs down)");
    assert.equal(await page.evaluate(() => document.querySelectorAll("#fileview-save-err").length), 0, "no notice: the section was found");
    assert.deepEqual(await page.evaluate(() => (window as any).__hostPosts), [], "the web route never posts the host's openFile");
    await closeViewer(page);
    // ── the line: the Raw view for this open, the row in view and centred
    await page.locator("#t-line .file-uri-link", { hasText: REL + ":" + ROW }).click();
    await page.locator("#romp-fileview .fileview-body code.hljs .fv-cl").first().waitFor({ timeout: 10000 });
    await frames(page, 3);
    const row = await page.evaluate((n: number) => {
      const body = document.querySelector("#romp-fileview .fileview-body") as HTMLElement;
      const rows = body.querySelectorAll("code.hljs .fv-cl"); const r = rows[n - 1] as HTMLElement;
      const br = body.getBoundingClientRect(), rr = r.getBoundingClientRect();
      return { rows: rows.length, text: (r.textContent || "").slice(0, 12), inView: rr.top >= br.top && rr.bottom <= br.bottom, off: Math.abs((rr.top + rr.bottom) / 2 - (br.top + br.bottom) / 2), h: rr.height };
    }, ROW);
    assert.ok(row.rows > ROW, "the Raw rows are up: " + row.rows);
    assert.equal(row.text, "Paragraph 6:", "row " + ROW + " is paragraph 6");
    assert.ok(row.inView && row.off <= row.h, "row " + ROW + " is in view, centred: " + JSON.stringify(row));
    await closeViewer(page);
    // ── a section the file has no heading for: the file opens, at its top, and the notice bar names it
    await page.locator("#t-line .file-uri-link", { hasText: REL + "#nowhere" }).click();
    await page.locator("#romp-fileview .fileview-md > p").first().waitFor({ timeout: 10000 });
    await page.locator("#romp-fileview #fileview-save-err").waitFor({ timeout: 5000 });
    await frames(page, 2);
    const bar = await page.evaluate(() => (document.getElementById("fileview-save-err")!.textContent || ""));
    assert.match(bar, /nowhere/, "the bar names the section: " + JSON.stringify(bar));
    assert.equal(await page.evaluate(() => (document.querySelector("#romp-fileview .fileview-body") as HTMLElement).scrollTop), 0, "nothing scrolled: the top of the file, said so, never a silent open");
    await closeViewer(page);
    // ── a bare path: as before
    await page.locator("#t-line .file-uri-link", { hasText: /^docs\/report\.md$/ }).click();
    await page.locator("#romp-fileview .fileview-md > p").first().waitFor({ timeout: 10000 });
    await frames(page, 2);
    assert.equal(await page.evaluate(() => (document.querySelector("#romp-fileview .fileview-body") as HTMLElement).scrollTop), 0);
    assert.equal(await page.evaluate(() => document.querySelectorAll("#fileview-save-err").length), 0, "no notice for a bare path");
    await closeViewer(page);
    assert.deepEqual(errors, []);
  });
});

test("in a browser, framed, with File links set to the Files pane: the click posts the shell's viewFile relay with `at` (a heading, a line, null for a bare path) and opens nothing in place", async (t) => {
  await inBrowser(t, async (page) => {
    await page.goto("http://romp.test/framed");
    const inner = page.frameLocator("#f-files");
    const frame = page.frame({ url: /\/files$/ });
    assert.ok(frame, "the Files page is framed");
    await frame.waitForFunction(() => !!(window as any).__rompProbe && !!(window as any).__linkLine);
    await frame.evaluate(() => { (window as any).__route = "pane"; (window as any).__filesOn = true; (window as any).__linkLine("t-line"); });
    assert.deepEqual(await linkInfo(frame, "#t-line .file-uri-link"), EXPECT);
    for (const text of [REL + "#results", REL + ":" + ROW]) await inner.locator("#t-line .file-uri-link", { hasText: text }).click();
    await inner.locator("#t-line .file-uri-link", { hasText: /^docs\/report\.md$/ }).click();
    await page.waitForFunction(() => (window as any).__relay.filter((m: any) => m && m.romp === "viewFile").length >= 3, null, { timeout: 5000 });
    const relay = await page.evaluate(() => (window as any).__relay.filter((m: any) => m && m.romp === "viewFile"));
    const identity = { name: "api", color: { bg: "#123456", fg: "#ffffff" } };
    assert.deepEqual(relay, [
      { romp: "viewFile", path: REL, sid: SID, pane: "pane", identity, at: { heading: "results" } },
      { romp: "viewFile", path: REL, sid: SID, pane: "pane", identity, at: { line: ROW } },
      { romp: "viewFile", path: REL, sid: SID, pane: "pane", identity, at: null },
    ], "the relay carries the target the link named, and null for none; the shell's forwarders copy the field (kernel.py; files.test.ts runs them)");
    assert.equal(await frame.evaluate(() => document.querySelectorAll("#romp-fileview").length), 0, "a relayed open is the target pane's viewer, never this document's");
  });
});

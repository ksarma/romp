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
import { DEAD_LINK_TITLE, HOST_PORT_TITLE, noSectionTitle } from "./file-view-links";

const EXT = process.cwd();                                        // npm test runs in vscode-extension
// resolve playwright and esbuild from the extension, not from wherever this bundle was written (a single-file run lands it under TMPDIR)
const requireCjs = createRequire(path.join(EXT, "package.json"));
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
const BLANK = ROOT + "/src/blank.py";
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
  "Bare ../src/app.py:3 links too, and https://example.invalid/prose is a URL.",
  "docs/first.md starts a soft-broken line of the same paragraph, and a hard break follows  ",   // two trailing spaces: marked's <br>
  "docs/second.md starts the line after the break.", "",
  "Also [same](notes.md:7), [uri](file:///tmp/TESTHOST/notes-api/README.md), [far](file://evil.invalid/x.md), [q](?foo=1), [here](#section), [go](#top), [past](../src/app.py:400), [collide](#fileview-save-err), [install](#install), [api](api.example.com:8443), [spec](app.test.ts:12), [results](#results), [self](guide.md#install), [vue](app.component.vue:3), [el](init.el:12), [ip](127.0.0.1:3000), [two](example.com:8443).", "",
  "A glob `**/docs/glob.md` or `src/**/x.md` links nothing, nor does an operand 2*docs/times.md or 3*w/h.px.", "",   // a star opens a path only when not slash-led and closed by a star (rounds 4 and 5); two lone stars, so hljs's emphasis mode closes on the line (an unclosed one runs to the end of the file and its closing tag makes a phantom row)
  'Copied from "docs/from.md", and the export "out/data.json" is stale.', "",   // the English from and export: prose that names files (round 3)
  "**docs/strong.md** and *docs/em.md*, then \u200bdocs/zwsp.md after a zero-width space.", "",   // Markdown emphasis and a zero-width space before a path: openers in the Raw view (round 3)
  "**./docs/dot.md** runs first, then *../docs/dotdot.md* is read.", "",   // emphasis around an anchored path: no glob puts ./ or ../ after its star (round 4 refused these; round 5)
  '<svg width="200" height="30"><a href="https://example.invalid/s"><text y="11">svgweb</text></a><a href="x.md"><text x="60" y="11">svgfile</text></a><text y="26">label docs/label.md in the figure</text></svg>', "",   // a bare path only: marked autolinks a URL inside inline HTML itself
  "```bash", "curl https://example.invalid/dl -o data/x.json", "docs/fence2.md", "  ./docs/fence3.md", "```", "",
  ...Array.from({ length: 32 }, (_, i) => "line " + (i + 10) + "\n"),   // one paragraph each (a blank line between), so the rendered body scrolls
  "## Results", "",                                // a heading: the viewer mints it the id md-results, and `#results` finds it by that slug
  '<p id="top">Top</p>', "",                        // an author's id on an element that is not a heading (a heading's own id is replaced by the minted one); rendered as user-content-top (md-sanitize.ts)
  '<p id="fileview-save-err">Collide</p>', "",     // an author's id spelled like the viewer's own notice bar: rendered prefixed, so the collision cannot occur
  '<a name="install"></a>', "", "## Install", "",   // the README idiom for a stable anchor: a named <a> above a heading; the name is read before the heading's minted id, under the prefix
].join("\n");
const NOTES_TEXT = Array.from({ length: 12 }, (_, i) => "note " + (i + 1)).join("\n") + "\n";
// what a highlighter cuts: bash puts `$HOME` and `${ROOT}` in spans of their own; typescript does the same to a template's `${x}`
// …and a URL a substitution cuts, with an absolute path as a query value: the URL stays text, and the path inside it is the URL's (round 3)
// …and the shapes round 4 refused: a glob's tail after a star, an operand after one, a multi-line import's specifier
// …and a whole statement (a shell's export, a finished export) above a comment's English from, which opens no import (round 5)
// …and a hand-split import past a blank row, or under `import * as ns`: the from line's own shape refuses its specifier (round 6)
const RUN_TEXT = ["#!/bin/bash", 'cp "$HOME/docs/a.md" ./out/', "cat ${ROOT}/src/x.py", 'echo "see ./docs/b.md"', "curl https://example.invalid/q?x=/docs/a.md/$V",
  "find . -path '**/docs/a.md'", "cp src/**/index.ts out/", "ls packages/*/package.json", "export DATA=/data", '# copied from "docs/c.md"', ""].join("\n");
const XTS_TEXT = ['import b from "lodash/fp.js";', 'import c from "@scope/pkg/dist/index.js";', 'import d from "./util.ts";', "const s = `tmpl/${x}/file.ts`;", "const u = `https://example.invalid/q?x=/docs/a.md/${v}`;",
  "const area = w*h/img.size;", "import {", '  e, f } from "pkg/multi.js";', "import { g }", '  from "pkg/cont.js";', "import {", "", '  h } from "pkg/gap.js";', "import * as ns", '  from "pkg/ns.js";', "export const z = 2;", '// ported from "docs/z.md"', ""].join("\n");
// a code view's blank row holds no text node, and is a row to the walk all the same; Python's whole `import os` above a comment's from opens no import (round 5)
const BLANK_TEXT = ["import json", "", '# see from "docs/c.md"', "import os", "import sys", '# adapted from "docs/a.md"', 'x = "docs/b.md"', "", "y = 1", "import numpy as np", '# data from "data/raw.csv"', ""].join("\n");
const FILES: Record<string, string> = { [APP]: APP_TEXT, [GUIDE]: GUIDE_TEXT, [NOTES]: NOTES_TEXT, [README]: "# notes-api\n", [CONFIG]: '{"a": 1}\n', [RUN]: RUN_TEXT, [XTS]: XTS_TEXT, [BLANK]: BLANK_TEXT };

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
    stdin: { contents: 'import "./files";\nimport { panelMark } from "./file-comments";\nimport { selectionOpenIn } from "./path-links";\nimport { isMarkdownUrl, LINK_SEL, linkHref, browserTabClick } from "./md-links";\nimport { userContentTarget } from "./md-sanitize";\nimport { openUrlView } from "./file-view";\n(window as any).__rompProbe = { panelMark, selectionOpenIn, isMarkdownUrl, openUrlView, LINK_SEL, linkHref, userContentTarget, browserTabClick };\n', resolveDir: UI, loader: "ts", sourcefile: "files-probe.ts" },
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
    const head = 'document.addEventListener("click", (e) => {\n  const a = (e.target as Element)?.closest?.(LINK_SEL) as HTMLElement | SVGElement | null;';   // LINK_SEL: every link element, the SVG anchor included (md-links.ts)
    const start = RENDER.indexOf(head);
    const end = RENDER.indexOf("}, true);", start) + "}, true);".length;
    assert.ok(start > 0 && end > start, "render.ts's document-level anchor opener");
    // …with what the opener names from the bundle: the panel's registry, the selection test, the same-origin .md route (md-links.ts
    // isMarkdownUrl, the real one; file-view.ts openUrlView, the real viewer; the fixture's URLs are example.invalid, so none takes it),
    // the `#` branch's target lookup and its browser's-tab test (md-sanitize.ts userContentTarget, md-links.ts browserTabClick), and
    // the platform read that test is handed, lifted from render.ts as the line it is (chat-link-open.test.ts pins its spelling)
    const isMac = /^const IS_MAC = .*;$/m.exec(RENDER);
    assert.ok(isMac, "render.ts's IS_MAC, the platform read the opener's `#` branch hands browserTabClick");
    ts = "const vscodeApi: { postMessage(m: unknown): void } | null = null;\nconst panelMark = (window as any).__rompProbe.panelMark as (t: Element | null) => boolean;\nconst selectionOpenIn = (window as any).__rompProbe.selectionOpenIn as (el: Node) => boolean;\n"
      + "const isMarkdownUrl = (window as any).__rompProbe.isMarkdownUrl as (href: string, origin: string) => boolean;\nconst openUrlView = (window as any).__rompProbe.openUrlView as (href: string) => void;\n"
      + "const LINK_SEL = (window as any).__rompProbe.LINK_SEL as string;\nconst linkHref = (window as any).__rompProbe.linkHref as (a: Element) => string;\nconst userContentTarget = (window as any).__rompProbe.userContentTarget as (root: ParentNode, id: string) => Element | undefined;\n"
      + "const browserTabClick = (window as any).__rompProbe.browserTabClick as (e: { ctrlKey?: boolean; metaKey?: boolean; shiftKey?: boolean; altKey?: boolean }, mac: boolean) => boolean;\n" + isMac![0] + "\n";
    // Every name the lifted opener uses that render.ts imports from a sibling module or declares at its top level must be one
    // of the consts above: a missing one throws a ReferenceError at the first click that reaches its branch, and the leg then
    // reads a page error where the viewer did nothing wrong (round 2 added browserTabClick and IS_MAC to the `#` branch and
    // the prelude defined neither, so the chat-host test could click no section link; the round-3 review). Read over the lift
    // with its comments and string literals removed, the lift's own locals set aside, and a property read (`.name`) not counted.
    const lifted = RENDER.slice(start, end);
    const code = lifted.replace(/\/\*[\s\S]*?\*\/|\/\/.*$|"(?:[^"\\\n]|\\.)*"|'(?:[^'\\\n]|\\.)*'|`(?:[^`\\]|\\.)*`/gm, (m) => (m[0] === "/" ? "" : '""'));
    const locals = new Set(Array.from(code.matchAll(/\b(?:const|let|var|function|class)\s+([A-Za-z_$][\w$]*)/g), (m) => m[1]));
    const named = new Set<string>();
    for (const m of RENDER.matchAll(/^import \{([^}]*)\} from "\.\/[^"]+";/gm)) for (const part of m[1].split(",")) { const name = part.trim().replace(/^type\s+/, "").split(/\s+as\s+/).pop()!.trim(); if (name) named.add(name); }
    for (const m of RENDER.matchAll(/^const ([A-Za-z_$][\w$]*)/gm)) named.add(m[1]);
    const declared = new Set(Array.from(ts.matchAll(/^const ([A-Za-z_$][\w$]*)/gm), (m) => m[1]));
    const free = Array.from(named).filter((n) => !locals.has(n) && !declared.has(n) && new RegExp("(?<![.\\w$])" + n.replace(/\$/g, "\\$") + "\\b").test(code));
    assert.deepEqual(free, [], "render.ts's opener names these and the prelude defines none of them: export each from the bundle's __rompProbe (bundle() above) and define it here, or the lifted handler throws where a click reaches it");
    ts += lifted;
    // …and the chat's BODY delegate (actions.ts delegate, the real one, on document.body as render.ts installs it) with
    // render.ts's own openpath handler, lifted from its source: it opens the todo card's and the Reply modal's path links
    // and, since the viewer's links carry the same data-act and the viewer lets a plain click go on to the document,
    // checks the host before opening. openLinkedPath is a recorder here; a second recorder notes every span the handler
    // was handed, so a test can tell "the click never reached the delegate" from "it reached it and was refused".
    const ACTIONS = fs.readFileSync(path.join(UI, "actions.ts"), "utf8");
    const fStart = ACTIONS.indexOf("export function flash(el: HTMLElement): void {");
    const dStart = ACTIONS.indexOf("export function delegate(root: HTMLElement | Document, handlers: Record<string, ActionHandler>): void {");
    const dEnd = ACTIONS.indexOf("\n}\n", dStart) + 3;
    assert.ok(fStart > 0 && dStart > fStart && dEnd > dStart, "actions.ts's flash and delegate");
    const bodyMap = RENDER.slice(RENDER.indexOf("delegate(document.body, {"), RENDER.indexOf("delegate(tabs, {"));
    const ln = bodyMap.split("\n").find((l) => /^\s*openpath: /.test(l));
    assert.ok(ln, "render.ts's body delegate routes openpath (the handler line moved; re-anchor)");
    const handler = ln!.trim().replace(/^openpath:\s*/, "").replace(/,$/, "");
    ts += "\ntype ActionHandler = (el: HTMLElement, ev: Event) => void;\n" + ACTIONS.slice(fStart, dEnd).replace(/^export /gm, "")
      + "\n(window as any).__bodyOpens = []; (window as any).__bodySeen = [];\n"
      + "const openLinkedPath = (a: HTMLElement, _e?: MouseEvent | null) => { (window as any).__bodyOpens.push(a.dataset.path); };\n"
      + "const openpath: (elx: HTMLElement, ev: Event) => void = " + handler + ";\n"
      + "delegate(document.body, { openpath: (elx, ev) => { (window as any).__bodySeen.push(elx.dataset.path); openpath(elx, ev); } });\n";
  } else {
    const FEED = fs.readFileSync(path.join(UI, "feed.ts"), "utf8");
    const start = FEED.indexOf("function typingIn(t: EventTarget | null): boolean {");   // the helpers feedWantsKeys reads, then the listener
    const at = FEED.indexOf('window.addEventListener("click", (e) => {', start);
    const end = FEED.indexOf("});", at) + 3;
    assert.ok(start > 0 && at > start && end > at, "feed.ts's window click listener");
    ts = "let kbMode = false;\n" + FEED.slice(start, end);
  }
  // a listener on the window, after the host's own: a click that reaches it reached every document-level listener too
  // (the feed's focus return above, the chat's menu closers), which a stop at the viewer's body starved (the 2026-09-07 review)
  ts += "\n(window as any).__windowClicks = [];\nwindow.addEventListener(\"click\", (e) => { (window as any).__windowClicks.push((e.target as HTMLElement).textContent); });\n";
  return esbuild.transformSync(ts, { loader: "ts", target: "es2020" }).code;
}
const PAGE = (host: "files" | "chat" | "feed") => `<!DOCTYPE html><html><head><meta charset=utf-8><style>
${fs.readFileSync(path.join(UI, "styles.css"), "utf8")}
${fs.readFileSync(path.join(UI, "files-pane.css"), "utf8")}
</style></head><body class=fileview-pane>${host === "chat" ? '<p id=chat-para><a href="https://example.invalid/pr">alpha beta gamma delta</a> is ready, and the prose after it runs on.</p>' : ""}<div id=files-empty></div>
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
    // ── a text-size step (A+; the viewer restyles and repaints its marks, keeping the selection): the links stand, the rows read
    //    as before, the selection survives the repaint, and the click that follows still opens the file ──
    await page.evaluate(() => { const l = document.querySelector("#romp-fileview .file-uri-link")!; getSelection()!.selectAllChildren(l.parentElement!); });
    await page.locator("#romp-fileview .fileview-size", { hasText: "A+" }).click(); await settle();
    assert.match((await page.locator("#romp-fileview .fileview-size-reset").textContent()) || "", /115/, "one step up from 100%");
    assert.deepEqual((await linkInfo("#romp-fileview .file-uri-link")).map((l) => l.text), links.map((l) => l.text), "the links stand at the new size");
    assert.deepEqual(await rowTexts(page), APP_TEXT.split("\n").slice(0, -1), "every row still reads as the file's line");
    assert.equal(await page.evaluate(() => !getSelection()!.isCollapsed), true, "the repaint kept the selection");
    await page.evaluate(() => getSelection()!.removeAllRanges());
    await page.locator("#romp-fileview .fileview-size-reset").click(); await settle();   // back to 100% for the row-in-view checks below

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
    // the Raw view's rows: the English from and export before a quoted path are prose, Markdown's emphasis marks and a
    // zero-width space are openers (the 2026-09-07 review, round 3), and the rows read as the file's lines
    const rawLinks = (await linkInfo("#romp-fileview .file-uri-link")).map((l) => l.text);
    for (const t of ["docs/from.md", "out/data.json", "docs/strong.md", "docs/em.md", "docs/zwsp.md", "./docs/dot.md", "../docs/dotdot.md"]) assert.ok(rawLinks.includes(t), "Raw links " + t + ": " + JSON.stringify(rawLinks));
    for (const t of ["/docs/glob.md", "docs/glob.md", "/x.md", "docs/times.md", "w/h.px"]) assert.ok(!rawLinks.includes(t), "no link for a glob's tail or an operand after a star (round 4): " + t);
    assert.ok(await page.evaluate(() => document.querySelectorAll("#romp-fileview code.hljs .hljs-strong, #romp-fileview code.hljs .hljs-emphasis").length >= 2), "hljs marked the emphasis, so the ** and * stand in the row's text");
    assert.deepEqual(await rowTexts(page), GUIDE_TEXT.split("\n").slice(0, -1), "every row reads as the file's line");

    // ── rendered markdown: a link to a file becomes a path link, a link to the web stays a tab, bare paths and fenced URLs link ─
    await open(GUIDE);
    await page.locator("#romp-fileview .fileview-md").waitFor({ timeout: 10000 });
    const mdLinks = await linkInfo("#romp-fileview .fileview-md a, #romp-fileview .fileview-md .file-uri-link");
    const byText = (t: string) => mdLinks.find((l) => l.text === t)!;
    for (const t of ["/docs/glob.md", "docs/glob.md", "/x.md", "docs/times.md", "w/h.px"]) assert.equal(byText(t), undefined, "rendered: no link for a glob's tail or an operand after a star (round 4): " + t);
    assert.deepEqual([byText("the app").href, byText("the app").path, byText("the app").act, /file-uri-link/.test(byText("the app").cls)], [null, APP, "openpath", true], "resolved and normalized");
    assert.deepEqual([byText("the web").href, byText("the web").target, byText("the web").act], ["https://example.invalid/doc", "_blank", null]);
    assert.deepEqual([byText("../src/app.py:3").path, byText("../src/app.py:3").line], [APP, "3"], "a bare path in the prose, with its line");
    assert.deepEqual([byText("https://example.invalid/prose").target, /fv-url/.test(byText("https://example.invalid/prose").cls)], ["_blank", false], "marked's own autolink, not wrapped twice");
    assert.deepEqual([byText("https://example.invalid/dl").href, /fv-url/.test(byText("https://example.invalid/dl").cls)], ["https://example.invalid/dl", true], "a URL inside the fenced block");
    assert.equal(byText("data/x.json").path, ROOT + "/docs/data/x.json");
    // a path starting a soft-broken line, one starting the line after a hard break (<br>), the fence's second and third
    // lines: the break before each is whitespace to the gate, not glue (the 2026-09-07 review, round 2)
    assert.equal(byText("docs/first.md").path, ROOT + "/docs/docs/first.md", "a path starting a soft-broken line of the paragraph");
    assert.equal(byText("docs/second.md").path, ROOT + "/docs/docs/second.md", "a path starting the line after a <br>");
    assert.equal(byText("docs/fence2.md").path, ROOT + "/docs/docs/fence2.md", "the fence's second line");
    assert.equal(byText("./docs/fence3.md").path, ROOT + "/docs/docs/fence3.md", "its third, indented");
    // the rendered prose: a quoted path after the English from or export links (round 3), and so does one after a zero-width space, or inside emphasis
    for (const [t, tail] of [["docs/from.md", "docs/from.md"], ["out/data.json", "out/data.json"], ["docs/strong.md", "docs/strong.md"], ["docs/em.md", "docs/em.md"], ["docs/zwsp.md", "docs/zwsp.md"], ["./docs/dot.md", "docs/dot.md"], ["../docs/dotdot.md", "dotdot.md"]] as const) {
      assert.equal(byText(t)?.path, ROOT + "/docs/" + tail, "rendered: " + t);
    }
    assert.equal(await page.evaluate(() => document.querySelector("#romp-fileview .fileview-md p br") !== null), true, "marked made the hard break a <br>");
    // the SVG label: its path stays text (an element inserted into SVG text does not render), and the label reads whole
    assert.deepEqual(await page.evaluate(() => { const t = Array.from(document.querySelectorAll("#romp-fileview .fileview-md svg text")).pop()!; return { text: t.textContent, marks: t.querySelectorAll("a, span").length, nodes: t.childNodes.length }; }),
      { text: "label docs/label.md in the figure", marks: 0, nodes: 1 }, "no link inside the SVG's text");
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

test("in a browser, through the real sanitizer: a same-directory `notes.md:7` and a `file:///` target open (a host with a port does not); a far host is a dead link that says why; a query alone opens a tab; a section link never moves the document (and scrolls to an id or a named anchor the document has, under a middle-click too); an inline SVG's anchors are marked; a line past the end says so", async (t) => {
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
    assert.deepEqual([byText("collide").href, /fv-frag/.test(byText("collide").cls), /fv-dead/.test(byText("collide").cls), byText("collide").title], ["#fileview-save-err", true, false, "Go to fileview-save-err"], "the author's element carries that id");
    // a heading: no author id, and the link finds it through the slug the viewer minted its id from (round 4, the upstream fold)
    assert.deepEqual([byText("results").href, /fv-frag/.test(byText("results").cls), /fv-dead/.test(byText("results").cls), byText("results").title], ["#results", true, false, "Go to results"]);
    assert.equal(await page.evaluate(() => document.querySelector("#romp-fileview .fileview-md h2#md-results")!.textContent), "Results", "the minted id, md- prefixed");
    // a sibling link's own #fragment rides the path link and lands once the file is open (below)
    assert.deepEqual([byText("self").href, byText("self").act, byText("self").path, byText("self").title], [null, "openpath", GUIDE, "Open " + GUIDE + "#install"]);
    assert.equal(await page.evaluate(() => (Array.from(document.querySelectorAll("#romp-fileview .fileview-md a")).find((a) => a.textContent === "self") as HTMLElement).dataset.frag), "install");
    // a GitHub-style <a name> is a target (the sanitizer kept it): live, by name (round 3)
    assert.equal(await page.evaluate(() => document.querySelectorAll('#romp-fileview .fileview-md a[name="user-content-install"]').length), 1, "the named anchor survived the sanitizer, under its user-content- prefix (md-sanitize.ts, SANITIZE_NAMED_PROPS)");
    assert.deepEqual([byText("install").href, /fv-frag/.test(byText("install").cls), /fv-dead/.test(byText("install").cls), byText("install").title], ["#install", true, false, "Go to install"]);
    // a host with a port in the `name.ext:N` shape is left as written, so the sanitizer removes it and the anchor says why; a three-label file is a file (round 3)
    assert.deepEqual([byText("api").href, byText("api").act, /fv-dead/.test(byText("api").cls), byText("api").title], [null, null, true, DEAD_LINK_TITLE], "api.example.com:8443 is not a same-directory file");
    assert.deepEqual([byText("spec").href, byText("spec").path, byText("spec").line, byText("spec").act], [null, ROOT + "/docs/app.test.ts", "12", "openpath"], "app.test.ts:12 is");
    // round 4: a `name.ext:N` whose extension the chat does not know is a file too; a host by shape, an IPv4 address with a port, is not
    assert.deepEqual([byText("vue").path, byText("vue").line, byText("vue").act], [ROOT + "/docs/app.component.vue", "3", "openpath"], "app.component.vue:3 is a file beside the README");
    assert.deepEqual([byText("el").path, byText("el").line, byText("el").act], [ROOT + "/docs/init.el", "12", "openpath"], "init.el:12 is a file (a two-letter label is a country code only under a registry's second-level label)");
    assert.deepEqual([byText("ip").href, byText("ip").act, /fv-dead/.test(byText("ip").cls), byText("ip").title], [null, null, true, HOST_PORT_TITLE], "127.0.0.1:3000 passed the sanitizer and is a host with a port, said so");
    assert.deepEqual([byText("two").href, byText("two").act, /fv-dead/.test(byText("two").cls), byText("two").title], [null, null, true, DEAD_LINK_TITLE], "example.com:8443 is a host by its top-level domain: left as written, removed by the sanitizer, dead with the reason");
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
    // an author's id spelled like the viewer's own chrome is prefixed by the sanitizer, so nothing inside the note answers to the
    // chrome's id, and every id inside the rendered note is either the viewer's minted md- one or a prefixed author one
    assert.equal(await page.evaluate(() => document.querySelectorAll("#romp-fileview #fileview-save-err").length), 0, "no notice is up, and the author's <p id=\"fileview-save-err\"> does not carry that id");
    assert.equal(await page.evaluate(() => document.querySelectorAll('#romp-fileview .fileview-md [id]:not([id^="md-"]):not([id^="user-content-"]), #romp-fileview .fileview-md [name]:not([name^="user-content-"])').length), 0, "minted or prefixed, nothing else");
    assert.equal(await page.evaluate(() => document.querySelectorAll("#romp-fileview .fileview-md p#user-content-fileview-save-err").length), 1, "the author's paragraph, under the prefix");
    const topBefore = await page.evaluate(() => { const b = document.querySelector("#romp-fileview .fileview-body")!.getBoundingClientRect(); const r = document.getElementById("user-content-top")!.getBoundingClientRect(); return r.top < b.bottom; });
    assert.equal(topBefore, false, "the anchor is below the fold to begin with");
    await page.locator("#romp-fileview .fileview-md a", { hasText: "go" }).click();
    await h.settle();
    const topAfter = await page.evaluate(() => { const b = document.querySelector("#romp-fileview .fileview-body")!.getBoundingClientRect(); const r = document.getElementById("user-content-top")!.getBoundingClientRect(); return r.top >= b.top - 1 && r.bottom <= b.bottom; });
    assert.equal(topAfter, true, "scrolled to the anchor"); assert.equal(page.url(), url0);
    // a colliding id: the viewer's own chrome wears ids too (its notice bar is #fileview-save-err). A stand-in for the bar
    // sits above the rendered document, as the bar does, and the section link still scrolls to the AUTHOR's element, the
    // rendered document's own element: a lookup over the whole viewer took the bar (the 2026-09-07 review, round 2). Two
    // guards now: the lookup's scope (.fileview-md), and the sanitizer's prefix, under which the author's element is
    // user-content-fileview-save-err and never the chrome's id at all (the stand-in is the viewer's own, never sanitized)
    await page.evaluate(() => {
      const d = document.createElement("div"); d.id = "fileview-save-err"; d.className = "fileview-err"; d.textContent = "a notice";
      const body = document.querySelector("#romp-fileview .fileview-body")!;
      body.prepend(d);
      for (const e of [body, body.querySelector(".fileview-md")!]) e.scrollTop = 0;
    });
    const inView = () => page.evaluate(() => { const b = document.querySelector("#romp-fileview .fileview-body")!.getBoundingClientRect(); const r = document.querySelector("#romp-fileview .fileview-md p#user-content-fileview-save-err")!.getBoundingClientRect(); return r.top >= b.top - 1 && r.bottom <= b.bottom; });
    assert.equal(await inView(), false, "the author's element is below the fold again");
    await page.locator("#romp-fileview .fileview-md a", { hasText: "collide" }).click();
    await h.settle();
    assert.equal(await inView(), true, "scrolled to the author's element, not to the viewer's own element of that id");
    assert.equal(page.url(), url0);
    await page.evaluate(() => document.querySelector("#romp-fileview .fileview-body > #fileview-save-err")!.remove());
    // the named anchor: a click scrolls to it (the heading under it comes into view), and the page's location stays
    await page.evaluate(() => { for (const e of [document.querySelector("#romp-fileview .fileview-body")!, document.querySelector("#romp-fileview .fileview-md")!]) e.scrollTop = 0; });
    const installIn = () => page.evaluate(() => { const b = document.querySelector("#romp-fileview .fileview-body")!.getBoundingClientRect(); const r = Array.from(document.querySelectorAll("#romp-fileview .fileview-md h2")).find((h) => h.textContent === "Install")!.getBoundingClientRect(); return r.top >= b.top - 1 && r.bottom <= b.bottom; });
    assert.equal(await installIn(), false, "the Install heading is below the fold");
    await page.locator("#romp-fileview .fileview-md a", { hasText: "install" }).click();
    await h.settle();
    assert.equal(await installIn(), true, "scrolled to the named anchor above the heading"); assert.equal(page.url(), url0);
    // a heading with no author id: the link lands on it through the slug the viewer minted its id from
    await page.evaluate(() => { for (const e of [document.querySelector("#romp-fileview .fileview-body")!, document.querySelector("#romp-fileview .fileview-md")!]) e.scrollTop = 0; });
    const resultsIn = () => page.evaluate(() => { const b = document.querySelector("#romp-fileview .fileview-body")!.getBoundingClientRect(); const r = document.querySelector("#romp-fileview .fileview-md h2#md-results")!.getBoundingClientRect(); return r.top >= b.top - 1 && r.bottom <= b.bottom; });
    assert.equal(await resultsIn(), false, "the Results heading is below the fold");
    await page.locator("#romp-fileview .fileview-md a", { hasText: "results" }).click();
    await h.settle();
    assert.equal(await resultsIn(), true, "scrolled to the heading by its slug"); assert.equal(page.url(), url0);
    // a sibling link's own #fragment (`guide.md#install`: this file again): the file opens and, once the first rendered paint
    // lands, the section is scrolled into view (openFileView's frag option, the upstream fold's landing)
    await page.evaluate(() => { for (const e of [document.querySelector("#romp-fileview .fileview-body")!, document.querySelector("#romp-fileview .fileview-md")!]) e.scrollTop = 0; });
    const nSelf = served.length;
    await page.locator("#romp-fileview .fileview-md a", { hasText: "self" }).click();
    await page.locator("#romp-fileview .fileview-md").waitFor({ timeout: 10000 });
    await h.settle(); await h.settle();
    assert.deepEqual(served[nSelf], { path: GUIDE, sid: SID }, "the sibling was fetched (this file again)");
    assert.equal(await installIn(), true, "…and its section came into view once the render landed"); assert.equal(page.url(), url0);
    // a middle-click on a section link: this document's scroll, as a plain click, and NO tab (the browser's own opened a second
    // copy of the hosting page at /files#top; the 2026-09-07 review, round 3); on a dead section link, nothing, and no tab either
    await page.evaluate(() => { for (const e of [document.querySelector("#romp-fileview .fileview-body")!, document.querySelector("#romp-fileview .fileview-md")!]) e.scrollTop = 0; });
    const topIn = () => page.evaluate(() => { const b = document.querySelector("#romp-fileview .fileview-body")!.getBoundingClientRect(); const r = document.getElementById("user-content-top")!.getBoundingClientRect(); return r.top >= b.top - 1 && r.bottom <= b.bottom; });
    assert.equal(await topIn(), false);
    const tabsMid = h.newPages();
    await page.locator("#romp-fileview .fileview-md a", { hasText: "go" }).click({ button: "middle" });
    await h.settle();
    assert.equal(h.newPages(), tabsMid, "no tab for a middle-click on a section link"); assert.equal(await topIn(), true, "it scrolled, as a plain click does"); assert.equal(page.url(), url0);
    await page.locator("#romp-fileview .fileview-md a", { hasText: "here" }).click({ button: "middle" });
    await h.settle();
    assert.equal(h.newPages(), tabsMid, "no tab for a middle-click on a dead section link"); assert.equal(page.url(), url0); assert.equal(await base(), "guide.md");
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

test("in a browser, over the real highlighter: a substitution span cannot turn a path's tail into a link, nor a query value inside the URL it cut, and an import's specifier stays text, a hand-split one's past a blank row too; a whole statement above a comment's from opens no import", async (t) => {
  await inBrowser(t, "files", async (h) => {
    const { page, open, linkInfo } = h;
    await open(RUN);
    assert.ok(await page.evaluate(() => document.querySelectorAll("#romp-fileview code.hljs .hljs-variable").length) >= 3, "bash's grammar put $HOME, ${ROOT} and $V in spans of their own");
    assert.deepEqual((await linkInfo("#romp-fileview .file-uri-link")).map((l) => [l.text, l.path]), [["./docs/b.md", ROOT + "/scripts/docs/b.md"], ["docs/c.md", ROOT + "/scripts/docs/c.md"]], "no /docs/a.md (neither the one after $HOME nor the one inside the cut URL's query), no /src/x.py; no /docs/a.md, /index.ts or /package.json off a glob's star (round 4); the comment's from under a whole `export DATA=/data` names a file (round 5)");
    assert.deepEqual(await linkInfo("#romp-fileview a.fv-url"), [], "the URL $V cuts is left as text, not wrapped in part");
    assert.deepEqual(await rowTexts(page), RUN_TEXT.split("\n").slice(0, -1));
    await open(XTS);
    assert.ok(await page.evaluate(() => document.querySelectorAll("#romp-fileview code.hljs .hljs-subst").length) >= 2, "typescript's grammar put ${x} and ${v} in spans of their own");
    assert.deepEqual((await linkInfo("#romp-fileview .file-uri-link")).map((l) => [l.text, l.path]), [["./util.ts", ROOT + "/ui/util.ts"], ["docs/z.md", ROOT + "/ui/docs/z.md"]],
      "the relative import links; lodash/fp.js, @scope/pkg/dist/index.js, the template's /file.ts and the cut URL's /docs/a.md do not; nor h/img.size after the operator's star, nor the multi-line imports' pkg/multi.js and pkg/cont.js (round 4), nor pkg/gap.js past a blank row or pkg/ns.js under `import * as ns` (round 5 linked pkg/gap.js; round 6 reads the from line's own shape); the comment's from under a whole `export const` names a file (round 5)");
    assert.deepEqual(await linkInfo("#romp-fileview a.fv-url"), [], "the template's URL ${v} cuts is left as text");
    assert.deepEqual(await rowTexts(page), XTS_TEXT.split("\n").slice(0, -1));
    // the primary surface for the round-5 finding: a Python file's blank row is `<span class=fv-cl><span class=fv-ct></span></span>`, no text node
    await open(BLANK);
    assert.equal(await page.evaluate(() => document.querySelectorAll("#romp-fileview code.hljs .fv-cl")[1].querySelector(".fv-ct")!.childNodes.length), 0, "the blank row holds no text node (the shape that hid it from the walk)");
    assert.deepEqual((await linkInfo("#romp-fileview .file-uri-link")).map((l) => [l.text, l.path]), [["docs/c.md", ROOT + "/src/docs/c.md"], ["docs/a.md", ROOT + "/src/docs/a.md"], ["docs/b.md", ROOT + "/src/docs/b.md"], ["data/raw.csv", ROOT + "/src/data/raw.csv"]],
      "the comment's from under a blank row, under `import os` / `import sys`, and under `import numpy as np` names a file each time (round 4 linked docs/b.md alone; round 5)");
    assert.deepEqual(await rowTexts(page), BLANK_TEXT.split("\n").slice(0, -1), "every row reads as the file's line, the blank ones included");
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

test("in a browser, under the chat's own document-level opener and its body delegate: a plain URL click is one tab, a drag inside the URL anchor selects and opens none, a plain click on a change mark inside the URL opens the card and no tab, a modified click on that mark is one tab and no card, a path link (a span or a Markdown anchor) opens in place ONCE: the delegate's openpath, which serves the todo card alone, opens nothing for it, and a plain click still reaches the window; a section link, plain or Ctrl-clicked, is the viewer's scroll under the opener's `#` branch and no tab, and a query alone is one tab", async (t) => {
  await inBrowser(t, "chat", async (h) => {
    const { page, served, open, status, settle, base, openCards } = h;
    // The chat's OWN anchor (draggable, as every anchor with an href is), first in its paragraph: a triple-click on the prose
    // after it selects the whole paragraph, and the browser anchors that selection at the paragraph's first text, inside the
    // link. A press on a draggable anchor starts no selection and collapses none, so the selection stays open around the link
    // and the plain click after it must still open the link: the opener reads the selection for a non-draggable anchor only
    // (round 4, the regression: it read it for every anchor, and every click on the link was dead until a click elsewhere)
    const chatA = page.locator("#chat-para a");
    assert.equal(await chatA.evaluate((a: HTMLAnchorElement) => a.draggable), true, "the chat's anchor is draggable");
    const prose = await page.evaluate(() => { const p = document.getElementById("chat-para")!; const r = document.createRange(); r.selectNodeContents(p.lastChild!); const b = r.getBoundingClientRect(); return { x: b.x + b.width / 2, y: b.y + b.height / 2 }; });
    const tabsTriple = h.newPages();
    await page.mouse.click(prose.x, prose.y, { clickCount: 3 }); await settle();
    const sel = await page.evaluate(() => { const s = getSelection()!; const a = document.querySelector("#chat-para a")!; return { open: !s.isCollapsed, inLink: a.contains(s.anchorNode), text: s.toString() }; });
    assert.ok(sel.open && sel.inLink && sel.text.includes("alpha beta gamma delta") && sel.text.includes("runs on"), "the triple-click on the prose left the paragraph selected, anchored inside the link's text: " + JSON.stringify(sel));
    assert.equal(h.newPages(), tabsTriple, "a triple-click on the prose opened nothing");
    assert.equal(await nextTab(h, () => chatA.click()), "https://example.invalid/pr", "the click on the link after it opens the link: one tab");
    await page.evaluate(() => getSelection()!.removeAllRanges());
    await open(APP);
    const n0 = served.length;
    assert.equal(await nextTab(h, () => page.locator("#romp-fileview a.fv-url").click()), URL_SETUP, "the chat's capture-phase opener: one tab");
    assert.equal(await base(), "app.py"); assert.equal(served.length, n0);
    // a press-drag-release inside the URL anchor: the text under it is selected and NO tab opens. The anchor is not draggable,
    // so the click that ends the drag fires, and the chat's opener, running first at the capture phase, opened the URL as well
    // until it read the selection open inside the anchor (the 2026-09-07 review, round 3). A plain click after it is one tab.
    const ub = (await page.locator("#romp-fileview a.fv-url").boundingBox())!;
    const tabsDrag = h.newPages();
    await page.mouse.move(ub.x + 8, ub.y + ub.height / 2); await page.mouse.down();
    await page.mouse.move(ub.x + ub.width - 8, ub.y + ub.height / 2, { steps: 10 }); await page.mouse.up();
    await settle();
    const dragSel = await page.evaluate(() => getSelection()!.toString());
    assert.ok(dragSel.length > 5 && URL_SETUP.includes(dragSel), "the drag selected the URL's text: " + JSON.stringify(dragSel));
    assert.equal(h.newPages(), tabsDrag, "and no tab opened for the click that ended it"); assert.equal(await base(), "app.py"); assert.equal(served.length, n0);
    await page.evaluate(() => getSelection()!.removeAllRanges());
    assert.equal(await nextTab(h, () => page.locator("#romp-fileview a.fv-url").click()), URL_SETUP, "a plain click after the drag: one tab again");
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
    const bodyOpens = () => page.evaluate(() => (window as any).__bodyOpens as string[]);
    const bodySeen = () => page.evaluate(() => (window as any).__bodySeen as string[]);
    const windowClicks = () => page.evaluate(() => ((window as any).__windowClicks as string[]).length);
    const w0 = await windowClicks();
    await page.locator("#romp-fileview .file-uri-link", { hasText: "../docs/guide.md:30" }).click();
    await page.locator("#romp-fileview .fileview-base", { hasText: "guide.md" }).waitFor({ timeout: 10000 });
    assert.deepEqual(served[served.length - 1], { path: GUIDE, sid: SID }, "a path link (no href) is the viewer's, not the opener's");
    assert.deepEqual(await bodyOpens(), [], "the body delegate's openpath (the todo card's route) opened nothing: the file opened once, from the viewer");
    assert.equal(await windowClicks(), w0 + 1, "the plain click went on to the window: the viewer does not stop it");
    await open(GUIDE);
    await page.locator("#romp-fileview .fileview-md").waitFor({ timeout: 10000 });
    // The viewer's section links under the chat's opener: its `#` branch runs first, at the capture phase, and reads the
    // browser's tab gesture (browserTabClick, IS_MAC) and the message-body scope before the viewer's own delegate lands the
    // section. A plain click and the browser's gesture both reach it, so a name the lifted handler uses that the prelude
    // left undefined throws here and is read at once (round 2 added browserTabClick and IS_MAC to that branch and the
    // prelude defined neither, so this leg could click no section link; the round-3 review).
    const url0 = page.url();
    const topInBody = () => page.evaluate(() => { const b = document.querySelector("#romp-fileview .fileview-body")!.getBoundingClientRect(); const r = document.getElementById("user-content-top")!.getBoundingClientRect(); return r.top >= b.top - 1 && r.bottom <= b.bottom; });
    assert.equal(await topInBody(), false, "the anchor is below the fold to begin with");
    const tabsFrag = h.newPages(), wFrag = await windowClicks();
    await page.locator("#romp-fileview .fileview-md a.fv-frag", { hasText: "go" }).click(); await settle();
    assert.deepEqual(h.errors, [], "the lifted opener ran its section-link branch: every name it uses is one the prelude defines");
    assert.equal(await topInBody(), true, "the viewer landed the section"); assert.equal(page.url(), url0, "no hash on the chat's document"); assert.equal(h.newPages(), tabsFrag, "and no tab");
    assert.equal(await base(), "guide.md"); assert.equal(await windowClicks(), wFrag + 1, "the plain click went on to the window: the opener's `#` branch is a message's, and it stops nothing for the viewer's link");
    await page.evaluate(() => { document.querySelector("#romp-fileview .fileview-body")!.scrollTop = 0; }); await settle();
    assert.equal(await topInBody(), false, "scrolled back up");
    await page.locator("#romp-fileview .fileview-md a.fv-frag", { hasText: "go" }).click({ modifiers: ["Control"] }); await settle();
    assert.deepEqual(h.errors, [], "the browser's tab gesture reached the opener's browserTabClick and IS_MAC");
    assert.equal(await topInBody(), true, "a Ctrl-click on a section link is this document's scroll too (a section of the shown file has no tab of its own)"); assert.equal(h.newPages(), tabsFrag, "and no tab"); assert.equal(page.url(), url0);
    // a query alone (`[q](?foo=1)`, the scheme-less shape): one tab at the resolved address, the chat's document where it was
    const qTab = await nextTab(h, () => page.locator("#romp-fileview .fileview-md a", { hasText: "q" }).click());
    assert.equal(new URL(qTab).search, "?foo=1", "the query rides the tab"); assert.equal(page.url(), url0, "the chat's document did not navigate"); assert.equal(await base(), "guide.md");
    await page.locator("#romp-fileview .fileview-md a", { hasText: "the app" }).click();
    await page.locator("#romp-fileview .fileview-base", { hasText: "app.py" }).waitFor({ timeout: 10000 });
    assert.deepEqual(served[served.length - 1], { path: APP, sid: SID });
    assert.deepEqual(await bodyOpens(), [], "a Markdown anchor marked as a path link: the same, one open");
    const w1 = await windowClicks(), seen1 = (await bodySeen()).length;
    await page.locator("#romp-fileview .file-uri-link", { hasText: "data/config.json" }).click({ modifiers: ["Control"] });
    await settle();
    assert.deepEqual(await bodyOpens(), [], "a modified click on a path link: its own tab or the viewer, and the delegate opened nothing");
    assert.equal((await bodySeen()).length, seen1); assert.equal(await windowClicks(), w1, "the modified click stops at the viewer's body (the row's delegate must not open a mark's card for it)");
    // The reachable double: an open the viewer's guard DECLINES (an unsaved comment) leaves the viewer, and the span, in
    // the document, so the click reaches the delegate (a plain open tears the old viewer down synchronously, which detaches
    // the span before the delegate's contains() check). The delegate's host check is what keeps the very file the person
    // just kept away from closed (a second ask on the web, the editor in VS Code); the click is not stopped.
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
    const n1 = served.length, w2 = await windowClicks();
    await link.click(); await settle();
    assert.equal(asked.length, 1, "the viewer asked"); assert.equal(await base(), "app.py", "declined: the file stays"); assert.equal(served.length, n1, "nothing fetched");
    assert.deepEqual(await bodySeen(), [CONFIG], "declined, with the span still in the document, the click reached the delegate (the viewer did not stop it; the plain opens above detached their spans first)");
    assert.deepEqual(await bodyOpens(), [], "and the delegate's host check refused it: the declined file was not opened behind the person's back");
    assert.equal(await windowClicks(), w2 + 1, "and the window's listeners saw the click");
    // the recorders are live, so the empties above mean something: a span in a todo card opens through the delegate; a span
    // loose in the body (no todo host) is seen and refused, as the viewer's are
    assert.deepEqual(await page.evaluate(() => {
      const card = document.createElement("div"); card.className = "todo-card";
      const s = document.createElement("span"); s.dataset.act = "openpath"; s.dataset.path = "/tmp/TESTHOST/elsewhere.md";
      card.appendChild(s); document.body.appendChild(card); s.click(); card.remove();
      const loose = document.createElement("span"); loose.dataset.act = "openpath"; loose.dataset.path = "/tmp/TESTHOST/loose.md";
      document.body.appendChild(loose); loose.click(); loose.remove();
      return { opened: ((window as any).__bodyOpens as string[]).splice(0), seen: ((window as any).__bodySeen as string[]).splice(0) };
    }), { opened: ["/tmp/TESTHOST/elsewhere.md"], seen: [CONFIG, "/tmp/TESTHOST/elsewhere.md", "/tmp/TESTHOST/loose.md"] }, "the body delegate is installed and live, and opens for its own hosts only");
  });
});

test("in a browser, under the feed's window click listener: a path link opens in place and the listener sees the click (it returns focus to the chat after one), and a URL opens a tab", async (t) => {
  await inBrowser(t, "feed", async (h) => {
    const { page, served, open, base } = h;
    await open(APP);
    const windowClicks = () => page.evaluate(() => ((window as any).__windowClicks as string[]).length);
    const w0 = await windowClicks();
    await page.locator("#romp-fileview .file-uri-link", { hasText: "data/config.json" }).click();
    await page.locator("#romp-fileview .fileview-base", { hasText: "config.json" }).waitFor({ timeout: 10000 });
    assert.deepEqual(served[served.length - 1], { path: CONFIG, sid: SID });
    assert.equal(await windowClicks(), w0 + 1, "the click reached the window, so the feed's own listener ran too (a stop at the viewer's body starved it; the 2026-09-07 review)");
    await open(APP);
    const n0 = served.length;
    assert.equal(await nextTab(h, () => page.locator("#romp-fileview a.fv-url").click()), URL_SETUP);
    assert.equal(await base(), "app.py"); assert.equal(served.length, n0);
  });
});

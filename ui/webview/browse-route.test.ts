// Where a FOLDER click opens (the user 2026-09-06): the folder at the bottom of the chat, the System-context
// Directory row and a tab menu's Browse files used to open the file browser as an overlay over the transcript
// (the 2026-08-24 pane-local cut, itself the answer to a listing over the FEED CARDS while the person read the
// chat). The listing now follows the file-link ladder: the Files pane while it is on screen or the File-links
// setting names it, the feed pane's browser otherwise, and in place only where neither surface exists
// (standalone /chat). VS Code keeps its configured opener.
//
// Four legs: the ladder itself, executed (file-route.ts is pure); the wiring at source (render.ts, file-browse.ts,
// files.ts, feed.ts, kernel.py); the shell's browse arms EXTRACTED from kernel.py and run against a shimmed
// window/document (the files.test.ts idiom); and the Files pane under the real shell script in Firefox and
// Chromium (the waiting-pane-browser.test.ts harness): the relay opens the listing in the pane, a picked file
// opens over the listing with a way back, Escape peels one layer at a time, and the pane tells the shell only
// when nothing is left up. The browser legs skip LOUDLY without playwright or the browsers (CI installs none).
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { browseRoute, fileLinkRoute } from "./file-route";

const requireCjs = createRequire(__filename);
const EXT = process.cwd();                                        // npm test runs in vscode-extension
const UI = path.resolve(EXT, "..", "ui", "webview");
const read = (f: string) => fs.readFileSync(path.join(UI, f), "utf8");
const RENDER = read("render.ts");
const BROWSE = read("file-browse.ts");
const FILES = read("files.ts");
const FEED = read("feed.ts");
const CHAT_CSS = read("styles.css");
const KERNEL = fs.readFileSync(path.resolve(EXT, "..", "kernel", "kernel.py"), "utf8");
const GUIDE = fs.readFileSync(path.resolve(EXT, "..", "docs", "guide.md"), "utf8");

// synthetic world: the notes-api demo, placeholder sids
const SID = "11111111-2222-3333-4444-555555555555";
const IDENTITY = { name: "web", color: { bg: "#123456", fg: "#ffffff" } };
const SETTINGS = ["chat", "feed", "pane", undefined, "purple"];   // the gear's three values, an unset store, a foreign value

// ── the ladder, executed ──────────────────────────────────────────────────────────────────────────

test("browseRoute: VS Code keeps the editor's opener whatever the panes say", () => {
  for (const setting of SETTINGS) for (const framed of [true, false]) for (const open of [true, false]) {
    assert.equal(browseRoute(false, setting, framed, open), "editor", `VS Code, setting=${String(setting)}, framed=${framed}, filesOpen=${open}`);
  }
});

test("browseRoute: web dashboard, Files pane OPEN: the listing opens in the Files pane, whatever the setting", () => {
  for (const setting of SETTINGS) assert.equal(browseRoute(true, setting, true, true), "pane", `setting=${String(setting)}`);
});

test("browseRoute: web dashboard, Files pane CLOSED: the setting's Files pane brings it forward; everything else lands on the feed, never over the chat", () => {
  assert.equal(browseRoute(true, "pane", true, false), "pane", "the setting names the Files pane: it comes forward for the listing, as it does for a file");
  assert.equal(browseRoute(true, "feed", true, false), "feed");
  assert.equal(browseRoute(true, "chat", true, false), "feed", "the DEFAULT: a file would open over the chat; a listing goes to the feed pane's browser");
  assert.equal(browseRoute(true, undefined, true, false), "feed", "an unset store reads as the default");
  assert.equal(browseRoute(true, "purple", true, false), "feed", "a foreign stored value falls to the default");
  // the one place the chat's own overlay still shows: unframed (standalone /chat), where neither surface exists
  for (const setting of SETTINGS) for (const open of [true, false]) {
    assert.equal(browseRoute(true, setting, false, open), "here", `standalone /chat, setting=${String(setting)}, filesOpen=${open}`);
  }
});

test("browseRoute is fileLinkRoute with exactly one substitution: a framed 'here' becomes 'feed'", () => {
  for (const setting of SETTINGS) for (const framed of [true, false]) for (const open of [true, false]) {
    const file = fileLinkRoute(setting, framed, open);
    const want = framed && file === "here" ? "feed" : file;
    assert.equal(browseRoute(true, setting, framed, open), want, `setting=${String(setting)}, framed=${framed}, filesOpen=${open}`);
  }
});

// ── the wiring at source ──────────────────────────────────────────────────────────────────────────

test("render.ts: the chat reads the ladder live at the click and posts its target up; in place only for 'here'", () => {
  assert.match(RENDER, /import \{ fileLinkRoute, browseRoute, type BrowseRoute \} from "\.\/file-route";/);
  assert.doesNotMatch(RENDER, /function fileLinkRoute\(/, "one definition of the ladder, in file-route.ts");
  // one reader of the live inputs, shared by openBrowse and the tab menu's sub-line
  assert.match(RENDER, /function browseRouteNow\(\): BrowseRoute \{\n\s*const web = location\.protocol === "http:" \|\| location\.protocol === "https:";\n\s*return browseRoute\(web, settings\.fileLinkPane, window\.parent !== window, panesOn\.files === true\);\n\}/);
  const fn = RENDER.split("function openBrowse(path: string, sid?: string | null): void {")[1].split("\n}")[0];
  assert.match(fn, /const route = browseRouteNow\(\);\n\s*if \(route === "editor"\) return;/);
  assert.match(fn, /if \(route === "here"\) \{ openFileBrowse\(path \|\| "\.", to\); return; \}/, "standalone /chat: the pane-local browser");
  // a viewer up over the chat closes first; a dirty-edit veto keeps it AND stands the click down whole
  assert.match(fn, /if \(document\.getElementById\("romp-fileview"\)\) \{\n\s*closeFileView\(\);\n\s*if \(document\.getElementById\("romp-fileview"\)\) return;/);
  assert.ok(fn.indexOf("closeFileView()") < fn.indexOf('romp: "browseFiles"'), "the close precedes the relay");
  // the message names its target and carries the session's identity for the Files pane's chip (openPath's shape)
  assert.match(fn, /window\.parent\.postMessage\(\{ romp: "browseFiles", path: path \|\| "\.", sid: to, pane: route,\n\s*identity: s && s\.name \? \{ name: s\.name, color: s\.color \?\? null \} : null \}, "\*"\);/);
  assert.match(RENDER, /import \{ closeFileView \} from "\.\/file-view";/);
});

test("render.ts: every folder surface goes through openBrowse, click-safe by delegation", () => {
  // the folder link's act rides a data-act caught by the BODY delegate (a stable root across every per-push
  // rebuild), and the act names the intent; where it lands is decided at the click
  assert.match(RENDER, /elem\.dataset\.act = web \? "browseFiles" : "openFolder";/);
  assert.match(RENDER, /delegate\(document\.body, \{\n\s*openFolder: \(el\) => \{/);
  assert.match(RENDER, /browseFiles: \(el\) => \{\n\s*const cwd = el\.dataset\.cwd; if \(!cwd\) return;\n\s*openBrowse\(cwd, el\.dataset\.id\);/);
  // the tab menu's Browse files: same call, and its sub-line tells the person where the listing will open
  assert.match(RENDER, /openBrowse\(s\?\.cwd \|\| "\.", id\);/);
  assert.match(RENDER, /const where = browseRouteNow\(\);\n\s*const sb = el\("span", "ctx-item-sub"\);\n\s*sb\.textContent = "the session's working tree, " \+ \(where === "pane" \? "in the Files pane" : where === "feed" \? "in the feed pane" : "in a viewer over this chat"\);/);
  // a chat-hosted viewer's directory link (file-view.ts posts browseFiles to its own window) walks the ladder too
  assert.match(RENDER, /initFileBrowse\(\(m\) => vscodeApi\?\.postMessage\(m\), \{\n\s*shellRestore: false,\n\s*onRelay: \(m\) => openBrowse\(m\.path, typeof m\.sid === "string" \? m\.sid : null\),\n\}\);/);
});

test("file-browse.ts: each hosting document states its contract; only the feed's close tells the shell", () => {
  assert.match(BROWSE, /export type BrowseHost = \{/);
  assert.match(BROWSE, /export function initFileBrowse\(poster: \(m: Record<string, unknown>\) => void, host: BrowseHost = \{\}\): void \{\n\s*post = poster;\n\s*shellRestore = host\.shellRestore !== false;/);
  // the relay guard runs BEFORE the in-place open, and returns
  assert.match(BROWSE, /if \(m\.romp === "browseFiles" && typeof m\.path === "string"\) \{\n\s*if \(host\.onRelay\) \{ host\.onRelay\(\{ path: m\.path, sid: m\.sid, identity: m\.identity \}\); return; \}\n\s*openFileBrowse\(m\.path \|\| "\.", typeof m\.sid === "string" \? m\.sid : null\);/);
  const tell = BROWSE.split("function tellShellClosed(): void {")[1].split("\n}")[0];
  assert.match(tell, /^\n\s*if \(!shellRestore\) return;/, "the gate is the first statement of the one close notice");
  assert.match(tell, /window\.parent\.postMessage\(\{ romp: "browseClosed" \}, "\*"\);/);
  // the feed keeps the default contract (it owes the restore); the Files pane and the chat opt out
  assert.match(FEED, /initFileBrowse\(\(m\) => vscodeApi\?\.postMessage\(m\)\);/);
  assert.equal((FILES.match(/shellRestore: false/g) || []).length, 1);
  assert.equal((RENDER.match(/shellRestore: false/g) || []).length, 1);
  // Escape closes the TOPMOST layer, the browser last: the Files pane inherits the same keydown story
  assert.match(BROWSE, /if \(document\.getElementById\("romp-fileview"\)\) return;   \/\/ the viewer is topmost/);
  assert.match(BROWSE, /if \(e\.key === "Escape"\) \{ e\.preventDefault\(\); closeFileBrowse\(\); return; \}/);
});

test("files.ts: the Files pane hosts the listing as a column: identity cached, the browser is a pane surface, one close edge", () => {
  assert.match(FILES, /import \{ initFileBrowse, openFileBrowse \} from "\.\/file-browse";/);
  assert.match(FILES, /onRelay: \(m\) => \{\n\s*const sid = typeof m\.sid === "string" \? m\.sid : null;\n\s*const id = asIdentity\(m\.identity\);\n\s*if \(sid && id\) identities\.set\(sid, id\);[^\n]*\n\s*openFileBrowse\(m\.path \|\| "\.", sid\);\n\s*\},/);
  // presence of either element is "something is up": the empty state hides, and the close edge is nothing left
  assert.match(FILES, /function surfaceUp\(\): boolean \{\n\s*return !!\(document\.getElementById\("romp-fileview"\) \|\| document\.getElementById\("romp-filebrowse"\)\);\n\}/);
  assert.match(FILES, /const open = surfaceUp\(\);\n\s*empty\.hidden = open;/);
  assert.match(FILES, /let viewerUp = surfaceUp\(\);/);
  assert.match(FILES, /const up = surfaceUp\(\);\n\s*if \(viewerUp && !up && window\.parent !== window\) window\.parent\.postMessage\(\{ romp: "filesViewerClosed" \}, "\*"\);/);
  // the listing fills the pane: the files page loads the chat sheet, whose .filebrowse is a fixed inset-0 box
  assert.match(KERNEL, /<link href=\/dist\/styles\.css\?v=%d rel=stylesheet>/);
  assert.match(CHAT_CSS, /\.filebrowse \{ position: fixed; inset: 0; z-index: 890;/);
});

test("the guide names the folder link and where its listing opens", () => {
  assert.match(GUIDE, /The folder under the chat \(the session's working directory\) opens a\s+listing of that folder by the same rule/);
});

// ── the shell's browse arms, executed ─────────────────────────────────────────────────────────────
// EXTRACTED from kernel.py's landing shell (the files.test.ts idiom): from the Files-pane browse branch to the
// end of the listener, run against a shimmed window/document. A `pane:'pane'` browse drives the Files branch and
// never touches the feed's flags; 'feed' (or no pane, an older sender) takes the feed route exactly as before.
function arms(): (w: unknown, d: unknown, m: unknown) => void {
  const start = KERNEL.indexOf("if(m.romp==='browseFiles'&&m.pane==='pane'){");
  const stop = KERNEL.indexOf("// One id per dashboard", start);
  assert.ok(start >= 0 && stop > start, "arm anchors not found: re-anchor this extraction");
  let js = KERNEL.slice(start, stop).trimEnd();
  assert.ok(js.endsWith("}});"));
  js = js.slice(0, -3);
  return new Function("window", "document", "m", js) as (w: unknown, d: unknown, m: unknown) => void;
}
// a shell to send messages through: desktop by default; `mobile` answers __rompMobileOn true with `tab` showing;
// `feedOn` is the po-feed class (the feed pane on screen)
function shell(opts: { mobile?: boolean; tab?: string; feedOn?: boolean } = {}) {
  const run = arms();
  const toggles: Array<[string, boolean]> = [], tabs: string[] = [];
  const posted: Record<string, unknown[]> = { "f-files": [], "f-feed": [], "f-chat": [] };
  const win: any = { __rompPaneToggle: (p: string, on: boolean) => { toggles.push([p, on]); if (p === "feed") feedOn = on; },
    __rompMobileTab: (t: string) => tabs.push(t), __rompMobileOn: () => !!opts.mobile };
  let feedOn = opts.feedOn !== false;
  const doc = {
    body: { classList: { contains: (c: string) => c === "po-feed" && feedOn },
            getAttribute: (a: string) => (a === "data-tab" ? opts.tab ?? "chat" : null) },
    getElementById: (id: string) => (id in posted ? { contentWindow: { postMessage: (x: unknown) => posted[id].push(x) } } : null),
  };
  const send = (m: unknown) => { run(win, doc, m); return { toggles, tabs, posted, from: win.__rompFilesTabFrom, wasOff: win.__rompFeedWasOff, pend: win.__rompFeedWasOffViewPend }; };
  return { send, win };
}

test("shell, executed: pane:'pane' brings the Files pane forward and forwards the ask with the identity; the feed is untouched", () => {
  const s = shell().send({ romp: "browseFiles", pane: "pane", path: "/repo/notes-api", sid: SID, identity: IDENTITY });
  assert.deepEqual(s.toggles, [["files", true]], "the folder click is the gesture that brings the pane forward");
  assert.deepEqual(s.tabs, [], "desktop: no mobile tab switch");
  assert.equal(s.from, undefined);
  assert.deepEqual(s.posted["f-files"], [{ romp: "browseFiles", path: "/repo/notes-api", sid: SID, identity: IDENTITY }]);
  assert.deepEqual(s.posted["f-feed"], [], "nothing reaches the feed");
  assert.equal(s.wasOff, undefined, "the feed's was-off flag is never armed by the Files route");
  assert.equal(s.pend, undefined);
  // no identity on the relay (an older chat bundle): the forward carries null, and files.ts falls to the stub
  const bare = shell().send({ romp: "browseFiles", pane: "pane", path: ".", sid: SID });
  assert.equal((bare.posted["f-files"][0] as any).identity, null);
  // a remote session's folder: the prefixed sid rides through untouched (the owning kernel lists it)
  const remote = shell().send({ romp: "browseFiles", pane: "pane", path: ".", sid: "TESTHOST:" + SID });
  assert.equal((remote.posted["f-files"][0] as any).sid, "TESTHOST:" + SID);
});

test("shell, executed: on a phone the Files tab comes forward and the pane's close edge puts the person back, once", () => {
  const phone = shell({ mobile: true, tab: "chat" });
  const opened = phone.send({ romp: "browseFiles", pane: "pane", path: "/repo/notes-api", sid: SID, identity: IDENTITY });
  assert.deepEqual(opened.tabs, ["files"]);
  assert.equal(opened.from, "chat", "the tab the click came from is remembered");
  const closed = phone.send({ romp: "filesViewerClosed" });
  assert.deepEqual(closed.tabs, ["files", "chat"], "the listing closed with nothing else up: back to the remembered tab");
  assert.equal(closed.from, null, "the memory is consumed");
  assert.deepEqual(phone.send({ romp: "filesViewerClosed" }).tabs, ["files", "chat"], "a second close switches nothing");
  // already on the Files tab: nothing to switch, nothing to remember
  const already = shell({ mobile: true, tab: "files" }).send({ romp: "browseFiles", pane: "pane", path: ".", sid: SID });
  assert.deepEqual(already.tabs, []); assert.equal(already.from, undefined);
  // an older shell without __rompMobileOn: the arm must not throw
  const bareWin = shell(); delete bareWin.win.__rompMobileOn;
  assert.deepEqual(bareWin.send({ romp: "browseFiles", pane: "pane", path: ".", sid: SID }).tabs, []);
});

test("shell, executed: pane:'feed' (and no pane) take the feed route exactly as before: lift, remember, put back on browseClosed", () => {
  for (const m of [{ romp: "browseFiles", pane: "feed", path: ".", sid: SID, identity: IDENTITY }, { romp: "browseFiles", path: ".", sid: SID }]) {
    const on = shell().send(m);
    assert.deepEqual(on.posted["f-feed"], [{ romp: "browseFiles", path: ".", sid: SID }], "path + sid only; the feed resolves its own identity");
    assert.deepEqual(on.posted["f-files"], []);
    assert.deepEqual(on.tabs, ["feed"], "phone: one pane at a time");
    assert.deepEqual(on.toggles, [], "the feed pane was on: nothing to lift");
    assert.equal(on.wasOff, undefined);
    // the feed pane OFF: lifted for the listing, remembered, and put back by the FEED's browseClosed
    const off = shell({ feedOn: false });
    const lifted = off.send(m);
    assert.deepEqual(lifted.toggles, [["feed", true]]);
    assert.equal(lifted.wasOff, true);
    const back = off.send({ romp: "browseClosed" });
    assert.deepEqual(back.toggles, [["feed", true], ["feed", false]]);
    assert.equal(back.wasOff, false);
  }
  // a browseClosed with nothing lifted moves nothing: the Files pane and the chat never send one (shellRestore
  // false at the source), and even an unexpected one cannot hide a feed the shell did not turn on
  assert.deepEqual(shell().send({ romp: "browseClosed" }).toggles, []);
});

// ── the Files pane under the real shell script, in a browser ──────────────────────────────────────
// the kernel's shell scripts, verbatim: plain JS in a non-raw Python string, so a backslash would mean the
// Python text and the served text differ; checked, so the slice can be trusted
function kernelJs(name: string): string {
  const open = name + ' = """';
  const at = KERNEL.indexOf(open);
  assert.ok(at > 0, name + " not found in kernel.py: re-anchor");
  const start = at + open.length;
  const js = KERNEL.slice(start, KERNEL.indexOf('"""', start));
  assert.ok(!js.includes("\\"), name + " carries a backslash: Python would alter it; slice differently");
  return js;
}
function collapseJs(): string {
  const at = KERNEL.indexOf("_PANE_ORDER = (");
  assert.ok(at > 0, "_PANE_ORDER not found in kernel.py: re-anchor");
  const keys = Array.from(KERNEL.slice(at, KERNEL.indexOf("\n\n", at)).matchAll(/\("(\w+)", "/g)).map((m) => m[1]);
  assert.ok(keys.includes("feed") && keys.includes("files"), "the pane keys parsed from _PANE_ORDER: " + keys.join(","));
  return kernelJs("_LANDING_COLLAPSE_JS").replace("__PANE_KEYS__", JSON.stringify(keys));
}
function paneCss(): string {
  const a = KERNEL.indexOf('"body:not(.po-chat) #chat-pane{display:none}');
  assert.ok(a > 0, "the landing's pane-hiding rule moved: re-anchor");
  return KERNEL.slice(a + 1, KERNEL.indexOf('"', a + 1));
}
// the shell's browse arms and the Files pane's close edge, as the landing ships them (the extraction above)
function relayJs(): string {
  const start = KERNEL.indexOf("if(m.romp==='browseFiles'&&m.pane==='pane'){");
  const stop = KERNEL.indexOf("// One id per dashboard", start);
  return KERNEL.slice(start, stop).trimEnd().slice(0, -3);
}
function bundle(entry: string): string {
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    entryPoints: [path.join(UI, entry)], bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent",
  });
  return r.outputFiles[0].text;
}
const SHELL_HTML = `<!DOCTYPE html><html><head><meta charset=utf-8>
<style>${paneCss()}.pane{display:inline-block;vertical-align:top}iframe{width:480px;height:420px;border:0}</style></head><body>
<div id=feed-pane class=pane><iframe id=f-feed src=/feed></iframe></div>
<div id=files-pane class=pane><iframe id=f-files src=/files></iframe></div>
<script>${collapseJs()}</script>
<script>window.__shellGot=[];window.addEventListener('message',function(e){var m=e.data||{};if(/Closed$|Opened$/.test(m.romp||''))window.__shellGot.push(m.romp);
${relayJs()}
});</script>
</body></html>`;
// the feed stands in as a recorder of the browse asks forwarded into it (the shell's panes broadcast, which every
// pane iframe receives on each apply, is not the question here)
const FEED_HTML = `<!DOCTYPE html><html><head><meta charset=utf-8></head><body><script>
window.__got=[];window.addEventListener('message',function(e){if(e.data&&e.data.romp==='browseFiles')window.__got.push(e.data);});</script></body></html>`;
// the Files page as the kernel serves it (the chat sheet for the browser's dress, the pane sheet for the layout),
// with the shim's fake acquireVsCodeApi replaced by a recorder so the listDir ask can be answered by hand
const FILES_HTML = (css: string) => `<!DOCTYPE html><html><head><meta charset=utf-8><style>${css}</style></head><body class=fileview-pane>
<div id=files-empty></div><script>window.__posted=[];window.acquireVsCodeApi=function(){return {postMessage:function(m){window.__posted.push(m);}};};</script>
<script src=/dist/files.js></script></body></html>`;

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

for (const name of ["firefox", "chromium"]) {
  test(`in ${name}: a folder relayed to the Files pane lists there, a picked file opens over the listing with a way back, Escape peels one layer, and the shell hears one close`, async (t) => {
    if (!pw) { t.skip("playwright is not installed under vscode-extension: the browser legs need it (CI installs no browsers)"); return; }
    let browser: any;
    try { browser = await pw[name].launch(); }
    catch (e) { t.skip("no playwright " + name + " on this box: this leg needs it (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
    try {
      const errors: string[] = [];
      const served: string[] = [];
      const filesJs = bundle("files.ts");
      const css = CHAT_CSS + "\n" + read("files-pane.css");
      const page = await browser.newPage({ viewport: { width: 1000, height: 500 } });
      page.on("pageerror", (e: Error) => { errors.push(e.message); });
      await page.route("http://romp.test/**", (route: any) => {
        const u = new URL(route.request().url());
        const html = (b: string) => route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: b });
        if (u.pathname === "/shell") return html(SHELL_HTML);
        if (u.pathname === "/feed") return html(FEED_HTML);
        if (u.pathname === "/files") return html(FILES_HTML(css));
        if (u.pathname === "/dist/files.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: filesJs });
        if (u.pathname === "/file") {
          served.push(u.search);
          return route.fulfill({ status: 200, contentType: "text/plain; charset=utf-8", headers: { "X-Romp-Mtime-Ns": "1", "X-Romp-Text-Utf8": "1" }, body: "# notes-api\n\nTwo services.\n" });
        }
        return route.fulfill({ status: 404, body: "" });
      });
      await page.goto("http://romp.test/shell?panes=feed");   // the Files pane OFF, the feed on: the default layout's relevant half
      const F = page.frameLocator("#f-files");
      const state = () => page.evaluate(() => {
        const f = (document.getElementById("f-files") as HTMLIFrameElement).contentWindow!;
        const box = f.document.getElementById("romp-filebrowse");
        const r = box ? box.getBoundingClientRect() : null;
        return {
          filesShown: getComputedStyle(document.getElementById("files-pane")!).display !== "none",
          filesOn: document.body.classList.contains("po-files"),
          shellGot: (window as any).__shellGot as string[],   // the close/open notices only (the recorder's filter)
          feedGot: ((document.getElementById("f-feed") as HTMLIFrameElement).contentWindow as any).__got as unknown[],
          posted: ((f as any).__posted as Array<Record<string, unknown>>).filter((m) => m.type === "listDir"),   // past the boot's ready handshake
          browser: !!box, viewer: !!f.document.getElementById("romp-fileview"),
          fills: r ? r.left === 0 && r.top === 0 && r.width === f.innerWidth && r.height === f.innerHeight : null,
          emptyHidden: (f.document.getElementById("files-empty") as HTMLElement).hidden,
          crumbs: Array.from(f.document.querySelectorAll("#fb-crumbs .fb-crumb")).map((c) => c.textContent),
          rows: Array.from(f.document.querySelectorAll(".fb-row")).map((c) => (c as HTMLElement).dataset.act + ":" + c.querySelector(".fb-name")!.textContent),
          back: !!f.document.querySelector(".fileview-back"),
          chip: f.document.querySelector(".fileview-sess")?.textContent ?? null,
        };
      });
      let s = await state();
      assert.equal(s.filesShown, false, "the Files pane starts off");
      // the chat's relay, as openBrowse posts it for route 'pane' (the shell's own window receives its message)
      await page.evaluate(([sid, identity]: [string, unknown]) => {
        window.postMessage({ romp: "browseFiles", pane: "pane", path: "/repo/notes-api", sid, identity }, "*");
      }, [SID, IDENTITY] as [string, unknown]);
      await F.locator("#romp-filebrowse").waitFor({ timeout: 10000 });
      s = await state();
      assert.equal(s.filesOn, true, "the shell brought the pane forward through its own state (po.files)");
      assert.equal(s.filesShown, true);
      assert.equal(s.fills, true, "the listing fills the pane: the fixed inset-0 box, in " + name);
      assert.equal(s.emptyHidden, true, "the empty state stands down while the listing is up");
      assert.deepEqual(s.feedGot, [], "nothing reached the feed");
      assert.equal(s.posted.length, 1, "one listDir ask");
      assert.equal(s.posted[0].type, "listDir"); assert.equal(s.posted[0].path, "/repo/notes-api"); assert.equal(s.posted[0].sid, SID);
      // the kernel's reply, by hand: a directory and a viewable file
      await page.evaluate(([sid, reqId]: [string, unknown]) => {
        const f = (document.getElementById("f-files") as HTMLIFrameElement).contentWindow!;
        f.postMessage({ type: "dirListing", reqId, host: "", sid, base: "/repo/notes-api", parent: "/repo",
          entries: [{ name: "src", isDir: true, isLink: false, size: 0, mtime: 1 }, { name: "README.md", isDir: false, isLink: false, size: 120, mtime: 1, viewable: true }],
          total: 2, truncated: false }, "*");
      }, [SID, s.posted[0].reqId] as [string, unknown]);
      await F.locator(".fb-row").first().waitFor({ timeout: 10000 });
      s = await state();
      assert.deepEqual(s.crumbs, ["/", "repo", "notes-api"], "the breadcrumb trail, every ancestor a click");
      assert.deepEqual(s.rows, ["dir:src/", "file:README.md"], "the listing renders in the pane");
      // pick the file: the viewer opens HERE, pane-resident, over the listing, with the way back and the chip
      // naming the session the relay carried (the identity cache the Files pane keeps for its viewer)
      await F.locator('.fb-row[data-act="file"]').click();
      await F.locator("#romp-fileview").waitFor({ timeout: 10000 });
      s = await state();
      assert.equal(s.browser, true, "the listing stays beneath the viewer");
      assert.equal(s.back, true, "the viewer offers the way back to the listing");
      assert.equal(s.chip, "web", "the chip names the session from the relayed identity, not the kernel's stub");
      assert.equal(served.length, 1); assert.match(served[0], /path=%2Frepo%2Fnotes-api%2FREADME\.md/);
      assert.deepEqual(s.shellGot, [], "nothing told the shell yet: the viewer is up over the listing");
      // Escape: the viewer (topmost) goes, the listing stays, and the pane says NOTHING (a viewer closing back onto
      // its listing is not the pane's close edge)
      await page.keyboard.press("Escape");
      await F.locator("#romp-fileview").waitFor({ state: "detached", timeout: 10000 });
      s = await state();
      assert.equal(s.browser, true, "back on the listing");
      assert.deepEqual(s.shellGot, [], "no filesViewerClosed while the listing is still up");
      // Escape again: the listing goes, the empty state repaints, and the shell hears exactly one close and NO
      // browseClosed (the Files pane owes the shell no restore; that message is the feed's)
      await page.keyboard.press("Escape");
      await F.locator("#romp-filebrowse").waitFor({ state: "detached", timeout: 10000 });
      // the notice is a postMessage to the parent, a task after the element's removal: wait for it, do not race it
      await page.waitForFunction(() => ((window as any).__shellGot as string[]).length >= 1, null, { timeout: 10000 });
      s = await state();
      assert.equal(s.emptyHidden, false, "the empty state is back");
      assert.deepEqual(s.shellGot, ["filesViewerClosed"]);
      assert.equal(s.filesOn, true, "the pane stays up: nothing to put back");
      // the feed route, for contrast: the shell forwards path + sid into the feed and the Files pane hears nothing
      await page.evaluate((sid: string) => { window.postMessage({ romp: "browseFiles", pane: "feed", path: ".", sid }, "*"); }, SID);
      await page.waitForFunction(() => (((document.getElementById("f-feed") as HTMLIFrameElement).contentWindow as any).__got as unknown[]).length === 1, null, { timeout: 10000 });
      s = await state();
      assert.deepEqual(s.feedGot, [{ romp: "browseFiles", path: ".", sid: SID }]);
      assert.equal(s.browser, false, "the Files pane did not open a listing for a feed-bound browse");
      assert.deepEqual(errors, [], "no script error in any frame");
    } finally { await browser.close(); }
  });
}

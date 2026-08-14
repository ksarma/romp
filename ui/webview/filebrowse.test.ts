// The file BROWSER in the FEED pane (plans/file-browser.md, the user 2026-08-14): breadcrumb over one
// directory's entries, riding the listDir WS op with the dirComplete staleness protocol, opening files
// through the existing viewer. Source pins (no jsdom for these modules), the repo convention.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const web = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const BROWSE = web("file-browse.ts");
const VIEW = web("file-view.ts");
const RENDER = web("render.ts");
const FEED = web("feed.ts");
const FEED_CSS = web("feed.css");
const KERNEL = fs.readFileSync(path.resolve(process.cwd(), "..", "kernel", "kernel.py"), "utf8");

test("the browser is the viewer's sibling overlay, one z layer BENEATH it", () => {
  // beneath by design: a file opened from a listing overlays the listing, and closing it returns there
  assert.match(FEED_CSS, /\.filebrowse \{ position: fixed; inset: 0; z-index: 890;/);
  assert.match(FEED_CSS, /\.fileview \{ position: fixed; inset: 0; z-index: 900;/);
  assert.match(BROWSE, /box\.id = "romp-filebrowse";/);
  assert.match(BROWSE, /document\.body\.classList\.add\("filebrowse-open"\);/);
});

test("the close contract is ownership-aware: the restore fires exactly once", () => {
  // the viewer stands down while the browser sits beneath — the browser's close does the restore
  assert.match(VIEW, /if \(document\.getElementById\("romp-filebrowse"\)\) return;/);
  assert.match(BROWSE, /window\.parent\.postMessage\(\{ romp: "browseClosed" \}, "\*"\);/);
  // and the shell treats either close as "the last overlay left"
  assert.match(KERNEL, /if\(\(m\.romp==='viewFileClosed'\|\|m\.romp==='browseClosed'\)&&window\.__rompFeedWasOff\)/);
});

test("the shell relays browseFiles exactly like viewFile: pane forward, remembered, phone tab", () => {
  assert.match(KERNEL, /if\(m\.romp==='browseFiles'\)\{var bf=document\.getElementById\('f-feed'\);/);
  const relay = KERNEL.split("if(m.romp==='browseFiles')")[1].split("if((m.romp==='viewFileClosed'")[0];
  assert.ok(relay.includes("window.__rompFeedWasOff=true;"), "a pane turned on for the browser is remembered");
  assert.ok(relay.includes("window.__rompMobileTab&&window.__rompMobileTab('feed')"), "phone: one pane at a time");
  assert.ok(relay.includes("postMessage({romp:'browseFiles',path:m.path,sid:m.sid}"), "forwarded into the feed iframe");
});

test("the listing rides the dirComplete staleness protocol: reqId stale-drop, in-flight coalescing", () => {
  assert.match(BROWSE, /post\(\{ type: "listDir", path, sid: curSid \|\| undefined, reqId: \+\+reqSeq, hidden: showHidden \}\);/);
  assert.match(BROWSE, /if \(m\.reqId !== reqSeq\) return;/);
  // no debounce: ONE in-flight ask, the newest navigation queued behind it — the round-trip is the pacing
  assert.match(BROWSE, /if \(inflight\) \{ queued = path; return; \}/);
  assert.match(BROWSE, /if \(queued !== null\) \{ const q = queued; queued = null; ask\(q\); return; \}/);
});

test("the kernel's listDir answers with the echo, the entries, and LOUD path-naming errors", () => {
  assert.match(KERNEL, /elif msg and msg\.get\("type"\) == "listDir":/);
  assert.match(KERNEL, /"type": "dirListing", "reqId": msg\.get\("reqId"\), "host": ""/);
  assert.match(KERNEL, /def _list_dir\(raw, sid=None, hidden=False, limit=DIR_LIST_MAX\):/);
  assert.match(KERNEL, /cannot list %s: not a directory/);
  assert.match(KERNEL, /DIR_LIST_MAX = 500/);
  // resolution is /file's own, so a listed path feeds the /file URL builder unchanged
  assert.match(KERNEL, /p = _resolve_open_path\(str\(raw or ""\), sid\)/);
});

test("waiting shows the romp loader, never a blank or a frozen listing", () => {
  assert.match(BROWSE, /el\("div", "fileview-load"\)/);
  assert.match(BROWSE, /romp-swirl-glyph\.svg/);
});

test("rows carry an honest verdict: download-only files are dimmed and download on click", () => {
  // server-side `viewable` (the same tables /file applies) marks the rows up front
  assert.match(BROWSE, /const dlOnly = en\.viewable === false;/);
  assert.match(BROWSE, /row\.dataset\.act = dlOnly \? "dl" : "file";/);
  assert.match(BROWSE, /if \(row\.dataset\.act === "dl"\) startDownload\(p\);/);
  assert.match(FEED_CSS, /\.fb-dlonly \.fb-name \{ color: var\(--dim\); \}/);
  // viewable files open through the EXISTING viewer — one leaf open action for the whole dashboard
  assert.match(BROWSE, /if \(row\.dataset\.act === "file"\) \{ openFileView\(p, curSid\); return; \}/);
});

test("clicks are delegated to stable roots and the cap is stated in-band", () => {
  // rows rebuild per navigation, so the listener lives on the persistent list container
  assert.match(BROWSE, /list\.addEventListener\("click", \(ev\) => \{/);
  assert.match(BROWSE, /crumbs\.addEventListener\("click", \(ev\) => \{/);
  assert.match(BROWSE, /entries — the rest aren't shown"/);
  assert.match(BROWSE, /"empty directory"/, "an empty dir says so — never a blank");
});

test("Escape closes the TOPMOST surface only, and Backspace walks up", () => {
  // the browser's key handler stands down while the viewer exists above it
  assert.match(BROWSE, /if \(document\.getElementById\("romp-fileview"\)\) return;/);
  assert.match(BROWSE, /if \(e\.key === "Escape"\) \{ e\.preventDefault\(\); closeFileBrowse\(\); return; \}/);
  assert.match(BROWSE, /if \(e\.key === "Backspace" \|\| e\.key === "ArrowLeft"\) \{/);
});

test("every entry point is gated to where the click can land, and posts the one shell message", () => {
  // chat: openBrowse posts {romp:'browseFiles'} to the shell, web-only
  assert.match(RENDER, /window\.parent\.postMessage\(\{ romp: "browseFiles", path: path \|\| "\.", sid: sid \|\| activeId \|\| null \}, "\*"\);/);
  // tab right-click menu row, web-only
  assert.match(RENDER, /browse\.textContent = "Browse files";/);
  // feed card menu row rides canPreview like the artifact chips, and sends only the sid — the kernel
  // resolves "." against the session's cwd authoritatively
  assert.match(FEED, /openFileBrowse\("\.", it\.sid\);/);
  assert.match(FEED, /if \(canPreview\(\)\) \{\n    const browse = el\("div", "ctx-item"\);/);
});

test("the statusline folder link BROWSES on the web; OS-open lives on its right-click (the user 2026-08-14)", () => {
  assert.match(RENDER, /elem\.dataset\.act = web && window\.parent !== window \? "browseFiles" : "openFolder";/);
  assert.match(RENDER, /click to browse this folder/);
  // the demoted OS-open: one document-level contextmenu on folder links, posting the old openFolder
  assert.match(RENDER, /item\.textContent = "Open folder window";/);
  assert.match(RENDER, /browseFiles: \(el\) => \{/, "the body delegate carries the new act");
});

test("the viewer's directory half is the click INTO the browser — no import cycle", () => {
  assert.match(VIEW, /dir\.classList\.add\("fileview-dir-link"\);/);
  // posted to our OWN window: initFileBrowse listens on the same channel the shell relays into
  assert.match(VIEW, /window\.postMessage\(\{ romp: "browseFiles", path: path\.slice\(0, cut\) \|\| "\/", sid \}, "\*"\);/);
  assert.match(BROWSE, /m\.romp === "browseFiles" && typeof m\.path === "string"/);
  assert.match(FEED_CSS, /\.fileview-dir-link \{ cursor: pointer; \}/);
});

test("the feed boots both overlays side by side", () => {
  assert.match(FEED, /initFileView\(\);/);
  assert.match(FEED, /initFileBrowse\(\(m\) => vscodeApi\?\.postMessage\(m\)\);/);
});

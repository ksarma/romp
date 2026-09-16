// The Waiting-on-you pane under the shell, in Firefox AND Chromium (plans/file-review.md, Slice 0; the
// 2026-09-06 review, round 3; the 2026-09-15 upstream pull-in, SWEEP-TRIAGE-2 D2). Three mechanisms:
//
// 1. WHERE a todo's file link opens (T404, adopted whole at the pull-in: the route follows the OPEN Files pane and no
//    setting names a closed one; file-route.ts fileLinkRoute, the chat's ladder, read off the shell's own panes broadcast).
//    With the Files pane on screen the click relays there and the keyboard follows it: the shell's own toggle first, then
//    the frame's focus, because Firefox refuses to focus a display:none frame's window (the 2026-09-06 round found the
//    ordering; Chromium focuses a hidden frame's window and hid it). With the pane closed, or its gear control hidden (the
//    fresh-install default since upstream's T317b, whose shell REFUSES to bring the Files pane forward while the control
//    is off), the viewer opens over the Waiting pane itself; Escape closes it there while the Reply modal and its text
//    stay, and the keyboard returns to the box. Before the route every click relayed and brought the pane forward itself,
//    which under T317b opened the viewer inside a display:none pane on a default install. The case that pinned that
//    bring-forward, "Files pane closed: Enter on a Reply-modal link brings the pane forward AND moves focus there; Escape
//    closes the viewer, the modal and its text stay", retires here by name, twin T317b plus T404
//    (https://github.com/romp-on/romp/pull/1596); its browser assertions (the focus hand-off, Escape, the return trip into
//    the box) live on in the Files-pane-open case, and the Reply modal's focus-return listener is pinned at source and
//    executed in waiting-reply-focus.test.ts (the pull-in's fixer round 7w, R5). The same file's executed case for openTodoPath's
//    guards against a shell the pane cannot trust (a parent whose document throws, no f-files, an f-files that is no iframe, an
//    iframe with no window yet) is restored below in the source leg (fixer round 7t, R5), with the exact calls per shape; its
//    twin is user-todo-links.test.ts's document-less parent (the try/catch arm) plus that case, not T404 whole.
// 2. A click whose pressed node a re-render replaced mid-press never fires (ui/CLAUDE.md, click safety):
//    with a Dismiss armed on another row the document pointerdown listener disarmed and re-rendered
//    synchronously, and a feed frame between mousedown and mouseup rebuilt the list — either dropped the
//    click on a detail link, and on Reply. The pane now HOLDS re-renders while a pointer is pressed on the
//    list and flushes after the release, a tick later so the click fires against the still-present node
//    (the tab strip's and the timeline's idiom, render.ts / romp-timeline-view.js).
// 3. The shared file BROWSER over this pane (the pull-in's review, round 1): the viewer's title has a directory half that posts
//    browseFiles to its own window, and only a document that installed initFileBrowse hears it. waiting.ts installs it under
//    the chat's and the Files pane's contract: the listing replaces the viewer (file-browse.ts's one-directional stack) and asks
//    the kernel for the folder over this pane's socket, a pick opens the viewer here, and the close tells the shell nothing
//    (shellRestore false: this pane never asked the shell to lift a pane). One browser leg drives it from a row's link, a
//    second through the Reply modal's own link (the review's round 2, item 5): there the listing draws ABOVE the modal's
//    backdrop (styles.css lifts #romp-filebrowse to 1100 and #fb-ctx to 1150 in this document alone, by #waiting-list's later
//    siblings, over .picker-overlay's 1000 and under #romp-fileview's 1200; the chat sheet's base rules keep feed.css's 890 and
//    950) and the modal's Escape stands aside for it as for the viewer, so the listing closes first and the typed answer
//    survives. The four numbers' order is pinned at source below, and every read of the shell's recorder after a close waits
//    for a sentinel the pane posts behind it (round 2, item 7).
//
// The shell stand-in is the kernel's own: _LANDING_COLLAPSE_JS (the po state, the body classes, the panes
// broadcast), the landing CSS rule that hides a pane, _LANDING_FOCUS_JS, _LANDING_ESC_JS and the Files-pane
// viewFile relay, all sliced from kernel.py at run time; the panes are the worktree's waiting.ts and files.ts
// bundles (esbuild, the webview build's options). The browser legs skip LOUDLY without playwright or the
// browser (CI installs none); the source leg runs everywhere and pins the mechanisms as written.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";

const requireCjs = createRequire(__filename);
const EXT = process.cwd();                                        // npm test runs in vscode-extension
const UI = path.resolve(EXT, "..", "ui", "webview");
const WAITING = fs.readFileSync(path.join(UI, "waiting.ts"), "utf8");
const KERNEL = fs.readFileSync(path.resolve(EXT, "..", "kernel", "kernel.py"), "utf8");

// synthetic world: the notes-api demo, a placeholder sid
const SID = "11111111-2222-3333-4444-555555555555";
const DETAIL = "Please read docs/design.md and say which of the two layouts to keep.";
const DETAIL2 = "The second question is in docs/rollout.md, near the top.";
const ROWS = [{ sid: SID, name: "api", color: { bg: "#123456", fg: "#ffffff" }, todos: [] }];

// ── the source leg ────────────────────────────────────────────────────────────────────────────────
// openTodoPath's body, executed with the names it reads handed in: the rows, the window, the route (todoLinkRoute, the
// shell's word through file-route.ts) and the viewer's opener for the "here" arm (user-todo-links.test.ts runs the
// same body the same way)
type Route = "pane" | "here";
type Fn = (rows: unknown[], w: unknown, path: string, sid: string, todoId: string, at: unknown, route: () => Route, openHere: (...a: unknown[]) => void) => void;
function openTodoPath(): Fn {
  const body = WAITING.split("function openTodoPath(path: string, sid: string, todoId: string, at: LinkTarget | null = null): void {")[1].split("\n}")[0];
  return new Function("rows", "window", "path", "sid", "todoId", "at", "todoLinkRoute", "openFileView", body) as Fn;
}
class ShellIFrame { constructor(public contentWindow: { focus(): void } | null) {} }
// the shell as the pane reads it: an iframe of the SHELL's realm (its own HTMLIFrameElement, reached through defaultView: the
// check waiting.ts makes, since an element is never an instance of another document's constructor), and the shell's pane
// toggle on its window. `hostile` bends the shell into a shape the pane must survive: `ff` replaces what getElementById answers
// for f-files (null, a node that is no iframe, an iframe the shell has not loaded), `unreadable` makes the parent's document
// getter throw, as a cross-origin parent's does
type Hostile = { ff?: unknown; unreadable?: boolean };
function shell(calls: string[], withToggle: boolean, hostile: Hostile = {}) {
  const files = "ff" in hostile ? hostile.ff : new ShellIFrame({ focus: () => { calls.push("focus"); } });
  const view: Record<string, unknown> = { HTMLIFrameElement: ShellIFrame };
  if (withToggle) view.__rompPaneToggle = (k: string, to: unknown) => { calls.push("toggle " + k + " " + String(to)); };
  const post = (m: any) => { calls.push("post " + m.romp + " " + m.pane); };
  if (hostile.unreadable) return { parent: { postMessage: post, get document(): never { throw new Error("SecurityError: Blocked a frame with origin"); } } };
  return { parent: { postMessage: post, document: { getElementById: (id: string) => (id === "f-files" ? files : null), defaultView: view } } };
}

test("openTodoPath routes by the shell's word: the Files pane on screen takes the click (the toggle, then the focus); otherwise the viewer opens over this pane and nothing is posted", () => {
  const opened: unknown[][] = [];
  const openHere = (...a: unknown[]) => { opened.push(a); };
  // the pane: the message, then the bring-forward, then the focus (a display:none frame's window takes no focus in Firefox)
  const calls: string[] = [];
  openTodoPath()(ROWS, shell(calls, true), "docs/design.md", SID, "t1", null, () => "pane", openHere);
  assert.deepEqual(calls, ["post viewFile pane", "toggle files true", "focus"], "the message, the bring-forward, the focus, in that order");
  assert.deepEqual(opened, [], "nothing opened over this pane");
  // a shell without the toggle (an older landing, or a bare parent): the focus still goes, nothing throws
  const bare: string[] = [];
  openTodoPath()(ROWS, shell(bare, false), "docs/design.md", SID, "t1", null, () => "pane", openHere);
  assert.deepEqual(bare, ["post viewFile pane", "focus"]);
  // here: the viewer over this pane, with the todo and the link's target; the shell hears nothing and no frame is focused
  const quiet: string[] = [];
  openTodoPath()(ROWS, shell(quiet, true), "docs/design.md", SID, "t1", { line: 12 }, () => "here", openHere);
  assert.deepEqual(quiet, [], "no relay, no toggle, no focus: the Files pane is not on screen");
  assert.deepEqual(opened, [["docs/design.md", SID, { todoId: "t1", at: { line: 12 } }]], "openFileView(path, sid, { todoId, at })");
  // the route is the chat's ladder over the shell's broadcast, cached whole (render.ts's two names), and the viewer is
  // booted in this document the way the feed boots it
  assert.match(WAITING, /import \{ fileLinkRoute \} from "\.\/file-route";/);
  assert.match(WAITING, /import \{ initFileView, openFileView, setFileViewIdentity, hostStub \} from "\.\/file-view";/);
  assert.match(WAITING, /function todoLinkRoute\(\): "pane" \| "here" \{\n\s*return fileLinkRoute\(framed, panesOn\.files === true, panesAvail\.files !== false\);\n\}/);
  assert.match(WAITING, /if \(!m \|\| m\.romp !== "panes"\) return;\n\s*if \(m\.on && typeof m\.on === "object"\) \{\n\s*const on: Record<string, boolean> = \{\};\n\s*for \(const k of Object\.keys\(m\.on\)\) on\[k\] = m\.on\[k\] === true;\n\s*panesOn = on;\n\s*\}/);
  assert.match(WAITING, /if \(m\.avail && typeof m\.avail === "object"\) for \(const k of Object\.keys\(m\.avail\)\) avail\[k\] = m\.avail\[k\] !== false;\n\s*panesAvail = avail;/);
  assert.match(WAITING, /\ninitFileView\(\(m\) => vscodeApi\?\.postMessage\(m\)\);\n/);
  assert.match(WAITING, /\nsetFileViewIdentity\(\(id\) => \{ const r = rows\.find\(\(x\) => x\.sid === id\); return r && r\.name \? \{ name: r\.name, color: r\.color \} : hostStub\(id\); \}\);\n/);
  // the shared browser is booted beside it under the chat's and the Files pane's contract (a pick opens the viewer here, the
  // close owes the shell nothing): the viewer's directory link posts to this window and only this listener hears it (the
  // pull-in's review round 1; the browser leg below drives the click). Pinned at source too: CI installs no browsers.
  assert.match(WAITING, /import \{ initFileBrowse \} from "\.\/file-browse";/);
  assert.match(WAITING, /\ninitFileBrowse\(\(m\) => vscodeApi\?\.postMessage\(m\), \{ shellRestore: false \}\);\n/);
  // the Reply modal's Escape stands aside while the viewer OR the listing is up over this pane, and takes the keyboard back
  // once BOTH are gone (executed against stand-ins in waiting-reply-focus.test.ts; the review's round 2, item 5)
  const modal = WAITING.slice(WAITING.indexOf("function showReply("), WAITING.indexOf("// ── render"));
  assert.match(modal, /const onKey = \(e: KeyboardEvent\) => \{\n\s*if \(e\.key !== "Escape"\) return;\n\s*if \(document\.getElementById\("romp-fileview"\) \|\| document\.getElementById\("romp-filebrowse"\)\) \{\n\s*setTimeout\(\(\) => \{ if \(overlay\.isConnected && !document\.getElementById\("romp-fileview"\) && !document\.getElementById\("romp-filebrowse"\)\) input\.focus\(\); \}, 0\);\n\s*return;\n\s*\}\n\s*e\.stopPropagation\(\); close\(\);\n\s*\};/);
});

// openTodoPath's guards against a shell the pane cannot trust, restored at the pull-in's fixer round 7t (R5) from the deleted
// waiting-link-focus.test.ts; this case's twin is user-todo-links.test.ts's document-less parent (the try/catch arm) plus this
// one. The exact calls per shape, not "nothing throws": the instanceof gate stands BEFORE the toggle, so a shell the gate
// refuses gets the relay and nothing else; a gate that was missing would toggle first and then throw into the catch, which a
// no-throw check cannot see. The payload's fields ride the relay as user-todo-links.test.ts's executed case pins them
test("a parent this pane cannot read, a shell with no Files iframe, an f-files that is no iframe: the relay goes and nothing else; an iframe with no window yet is brought forward and not focused", () => {
  const route = () => "pane" as Route, openHere = () => undefined;
  // the parent's document getter throws (a cross-origin parent): the catch, before the shell is read
  const unreadable: string[] = [];
  openTodoPath()(ROWS, shell(unreadable, true, { unreadable: true }), "docs/design.md", SID, "t1", null, route, openHere);
  assert.deepEqual(unreadable, ["post viewFile pane"], "the relay, then the catch: no toggle, no focus");
  // no f-files element: the gate refuses null before the toggle
  const missing: string[] = [];
  openTodoPath()(ROWS, shell(missing, true, { ff: null }), "docs/design.md", SID, "t1", null, route, openHere);
  assert.deepEqual(missing, ["post viewFile pane"], "no element: nothing toggled, nothing focused");
  // an f-files that is no iframe of the shell's realm: the gate refuses it, so its window is never reached
  const notAFrame = { contentWindow: { focus: () => { throw new Error("must not be reached"); } } };
  const other: string[] = [];
  openTodoPath()(ROWS, shell(other, true, { ff: notAFrame }), "docs/design.md", SID, "t1", null, route, openHere);
  assert.deepEqual(other, ["post viewFile pane"], "not an iframe: no toggle (a missing gate would toggle, then throw into the catch)");
  // an iframe the shell has not loaded yet has no window: brought forward, nothing to focus, nothing thrown
  const unloaded: string[] = [];
  openTodoPath()(ROWS, shell(unloaded, true, { ff: new ShellIFrame(null) }), "docs/design.md", SID, "t1", null, route, openHere);
  assert.deepEqual(unloaded, ["post viewFile pane", "toggle files true"], "the bring-forward, and no focus on a window that is not there");
});

test("re-renders are HELD while a pointer is pressed on the list and flushed a tick after the release", () => {
  const render = WAITING.slice(WAITING.indexOf("function render(): void {"), WAITING.indexOf("// ── frames"));
  assert.match(render, /if \(listPointerHeld\) \{ renderPendingWhilePressed = true; return; \}/, "render() defers while pressed");
  const release = WAITING.slice(WAITING.indexOf("function releaseList(): void {"), WAITING.indexOf("function render(): void {"));
  assert.match(release, /if \(!listPointerHeld\) return;\n\s*listPointerHeld = false;\n\s*if \(renderPendingWhilePressed\) \{ renderPendingWhilePressed = false; setTimeout\(\(\) => render\(\), 0\); \}/,
    "the flush waits a tick: the click dispatches right after pointerup, against the still-present node");
  // the press is latched in the SAME document capture listener that disarms, and before the disarm's render()
  const wiring = WAITING.slice(WAITING.indexOf("// A tap anywhere that is NOT an armed Dismiss"), WAITING.indexOf("// keep every \"Xm ago\" honest"));
  assert.match(wiring, /document\.addEventListener\("pointerdown", \(ev\) => \{\n\s*const t = ev\.target as HTMLElement \| null;\n\s*if \(t && list\.contains\(t\)\) listPointerHeld = true;\n[\s\S]*?armedDismiss\.clear\(\); render\(\);\n\s*\}, true\);/);
  // every press reaches a release: pointerup, pointercancel, or the window losing focus (released in another frame)
  for (const ev of ["pointerup", "pointercancel", "blur"]) assert.ok(wiring.includes(`window.addEventListener("${ev}", releaseList);`), ev + " releases the hold");
});

// ── the browser legs ──────────────────────────────────────────────────────────────────────────────
// the kernel's shell scripts, verbatim: plain JS in a non-raw Python string, so a backslash would mean the
// Python text and the served text differ — checked, so the slice can be trusted
function kernelJs(name: string): string {
  const open = name + ' = """';
  const at = KERNEL.indexOf(open);
  assert.ok(at > 0, name + " not found in kernel.py — re-anchor");
  const start = at + open.length;
  const js = KERNEL.slice(start, KERNEL.indexOf('"""', start));
  assert.ok(!js.includes("\\"), name + " carries a backslash: Python would alter it — slice differently");
  return js;
}
// the pane controller, with the keys _landing() splices in from _PANE_ORDER. The kernel splices them inline
// (`var KEYS=""" + json.dumps([k for k, _ in _PANE_ORDER]) + """;`, the placeholder-free form the 2026-09-15
// upstream pull-in took, F2), so kernelJs()'s slice to the first triple quote would stop at `var KEYS=`: cut
// at the splice instead and join the two literal halves with the keys parsed above (browse-route.test.ts's idiom)
function collapseJs(): string {
  const at = KERNEL.indexOf("_PANE_ORDER = (");
  assert.ok(at > 0, "_PANE_ORDER not found in kernel.py — re-anchor");
  const keys = Array.from(KERNEL.slice(at, KERNEL.indexOf("\n\n", at)).matchAll(/\("(\w+)", "/g)).map((m) => m[1]);
  assert.ok(keys.includes("waiting") && keys.includes("files"), "the pane keys parsed from _PANE_ORDER: " + keys.join(","));
  const open = '_LANDING_COLLAPSE_JS = """';
  const at2 = KERNEL.indexOf(open);
  assert.ok(at2 > 0, "_LANDING_COLLAPSE_JS not found in kernel.py: re-anchor");
  const start = at2 + open.length;
  const splice = '""" + json.dumps([k for k, _ in _PANE_ORDER]) + """';
  const cut = KERNEL.indexOf(splice, start);
  assert.ok(cut > start, "the pane-keys splice in _LANDING_COLLAPSE_JS moved: re-anchor (the inline json.dumps of _PANE_ORDER)");
  const rest = cut + splice.length;
  const js = KERNEL.slice(start, cut) + JSON.stringify(keys) + KERNEL.slice(rest, KERNEL.indexOf('"""', rest));
  assert.ok(!js.includes("\\"), "_LANDING_COLLAPSE_JS carries a backslash: Python would alter it; slice differently");
  return js;
}
// the landing CSS that hides a toggled-off pane — display:none, the property Firefox's focus refuses
function paneCss(): string {
  const a = KERNEL.indexOf('"body:not(.po-chat) #chat-pane{display:none}');
  assert.ok(a > 0, "the landing's pane-hiding rule moved — re-anchor");
  return KERNEL.slice(a + 1, KERNEL.indexOf('"', a + 1));
}
// the shell's Files-pane viewFile branch, from its test to its own closing brace (brace-matched: the branch that used to
// follow it, the feed's viewFile arm, retired with T404 at the 2026-09-15 pull-in, so no neighbour anchors the end)
function relayJs(): string {
  const a = KERNEL.indexOf("if(m.romp==='viewFile'&&m.pane==='pane'){");
  assert.ok(a > 0, "the shell's Files-pane viewFile branch moved: re-anchor");
  let depth = 0, i = KERNEL.indexOf("{", a);
  for (; i < KERNEL.length; i++) {
    if (KERNEL[i] === "{") depth++;
    else if (KERNEL[i] === "}" && --depth === 0) break;
  }
  assert.ok(depth === 0 && i > a, "the Files-pane viewFile branch's braces do not close: re-anchor");
  return KERNEL.slice(a, i + 1);
}
function bundle(entry: string): string {
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    entryPoints: [path.join(UI, entry)], bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent",
  });
  return r.outputFiles[0].text;
}
// the shell: the kernel's pane controller owns what is on screen (the URL's ?panes= names the open panes; a fresh
// install has the Files pane OFF and its gear control hidden, and the controller closes the pane and refuses to bring
// it forward while the control is off, T317b), its CSS hides the off panes, and its focus, Escape and relay wiring run
const SHELL_HTML = `<!DOCTYPE html><html><head><meta charset=utf-8>
<style>${paneCss()}.pane{display:inline-block;vertical-align:top}iframe{width:480px;height:420px;border:0}</style></head><body>
<div id=waiting-pane class=pane><iframe id=f-waiting src=/waiting></iframe></div>
<div id=files-pane class=pane><iframe id=f-files src=/files></iframe></div>
<script>${collapseJs()}</script>
<script>${kernelJs("_LANDING_FOCUS_JS")}</script>
<script>${kernelJs("_LANDING_ESC_JS")}</script>
<script>window.addEventListener('message',function(e){var m=e.data||{};
${relayJs()}
});</script>
</body></html>`;
const WAITING_HTML = `<!DOCTYPE html><html><head><meta charset=utf-8></head><body>
<div id=waiting-head></div><div id=waiting-list></div><script src=/dist/waiting.js></script></body></html>`;
// the same page with the chat's stylesheet, as _waiting_page links it (the .ut-* dress, and the overlays stack as served), and a
// poster stand-in where the served page's pane shim defines acquireVsCodeApi (inline, ahead of the bundle, as kernel.py does):
// every message the pane posts lands on its window.__posted. Inline on purpose: an addInitScript with a pathname guard never
// reaches this frame in Firefox, which runs it once on the iframe's initial about:blank and then reuses that window
const WAITING_CSS_HTML = WAITING_HTML.replace("<meta charset=utf-8>", "<meta charset=utf-8><link href=/dist/styles.css rel=stylesheet>"
  + "<script>window.acquireVsCodeApi=function(){return{postMessage:function(m){(window.__posted=window.__posted||[]).push(m);}};};</script>");
const styles = () => fs.readFileSync(path.join(UI, "styles.css"), "utf8");

// The stacking the modal flow depends on, pinned in numbers so CI, which runs no browser, holds it (the review's round 2,
// item 5): in the Waiting pane's document the Reply modal's overlay (.picker-overlay) sits under the listing (#waiting-list ~
// #romp-filebrowse, the Waiting pane's lift), the listing under its own row menu (#waiting-list ~ #fb-ctx) and the menu under
// the viewer (#romp-fileview), so a pick from the listing still overlays it (the one-directional stack). The two scoped rules
// are what the served page's markup selects (kernel.py _waiting_page: #waiting-list a direct child of the body, the browser and
// its menu appended to the body after it); the chat sheet's base rules stay the mirror of feed.css's
// (filebrowse-chat-overlay.test.ts pins the pair), so the chat's own modal keeps its order
test("the Waiting pane's stacking: .picker-overlay 1000 < the listing 1100 < its row menu 1150 < the viewer 1200 (styles.css, the served markup)", () => {
  const css = styles();
  const z = (head: string): number => {
    const at = css.indexOf(head);
    assert.ok(at >= 0, head + " present in styles.css");
    const rule = css.slice(at, css.indexOf("}", at) + 1);
    const m = rule.match(/z-index: (\d+);/);
    assert.ok(m, head + " carries a z-index: " + rule);
    return Number(m![1]);
  };
  const modal = z(".picker-overlay {"), listing = z("#waiting-list ~ #romp-filebrowse {"), menu = z("#waiting-list ~ #fb-ctx {"), viewer = z("#romp-fileview {");
  assert.deepEqual([modal, listing, menu, viewer], [1000, 1100, 1150, 1200], "the four layers, bottom to top");
  assert.ok(modal < listing && listing < menu && menu < viewer, "the order the modal flow needs");
  // the served page selects the two: #waiting-list is a direct child of the body, and the browser is appended to the body after it.
  // The pins hold that adjacency: each spans from the head's close and the body's open tag through the two divs (the kernel's
  // across its literal's line break), so a wrapper element between the body and #waiting-list fails them instead of passing unseen
  assert.match(KERNEL, /<\/head><body>(?:"\s*")?<div id=waiting-head><\/div><div id=waiting-list><\/div>/,
    "the served Waiting page's markup: #waiting-list a direct child of the body, nothing between");
  assert.match(WAITING_HTML, /<\/head><body>\n<div id=waiting-head><\/div><div id=waiting-list><\/div>/, "the harness's page carries the same");
});
const FILES_HTML = `<!DOCTYPE html><html><head><meta charset=utf-8></head><body class=fileview-pane>
<div id=files-empty></div><script src=/dist/files.js></script></body></html>`;

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

type Todo = { id: string; text: string; age: number; detail: string };
// `panes`: the ?panes= set the shell opens with (the default leaves the Files pane off, as a fresh install does);
// `filesControl`: the gear's Files control shown (romp:settings.showFilesControl, written into the shell's store before its
// scripts run, the way the gear would have left it); absent, the fresh-install default, hidden;
// `kernel`: the pane's page carries a poster stand-in (acquireVsCodeApi, the name the served pane shim defines; every message
// the pane posts lands on its window.__posted, read back by posted()) and the chat's stylesheet, so the file browser's ask and
// the overlays' stacking can be read; absent, the pane posts into nothing, as before
type Boot = { panes?: string; filesControl?: boolean; kernel?: boolean };
async function boot(browser: any, todos: Todo[], opts: Boot = {}) {
  const errors: string[] = [];
  const served: string[] = [];
  const waitingJs = bundle("waiting.ts"), filesJs = bundle("files.ts");
  const page = await browser.newPage({ viewport: { width: 1000, height: 500 } });
  page.on("pageerror", (e: Error) => { errors.push(e.message); });
  if (opts.filesControl) {
    // the top document only: the shell's pane controller reads the store at boot (filesCtl), the panes read it for the theme
    await page.addInitScript(() => {
      if (window.top !== window) return;
      try { localStorage.setItem("romp:settings", JSON.stringify({ showFilesControl: true })); } catch { /* storage denied */ }
    });
  }
  await page.route("http://romp.test/**", (route: any) => {
    const u = new URL(route.request().url());
    const html = (b: string) => route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: b });
    const js = (b: string) => route.fulfill({ status: 200, contentType: "application/javascript", body: b });
    if (u.pathname === "/shell") return html(SHELL_HTML);
    if (u.pathname === "/waiting") return html(opts.kernel ? WAITING_CSS_HTML : WAITING_HTML);
    if (u.pathname === "/dist/styles.css") return route.fulfill({ status: 200, contentType: "text/css; charset=utf-8", body: styles() });
    if (u.pathname === "/files") return html(FILES_HTML);
    if (u.pathname === "/dist/waiting.js") return js(waitingJs);
    if (u.pathname === "/dist/files.js") return js(filesJs);
    if (u.pathname === "/file") {   // the viewer's fetch — what the kernel would serve for a text file
      served.push(u.search);
      return route.fulfill({ status: 200, contentType: "text/plain; charset=utf-8", headers: { "X-Romp-Mtime-Ns": "1", "X-Romp-Text-Utf8": "1" }, body: "# Design\n\nTwo layouts.\n" });
    }
    return route.fulfill({ status: 404, body: "" });
  });
  await page.goto("http://romp.test/shell?panes=" + (opts.panes ?? "waiting"));   // the load event covers both frames' boots
  const feed = (rows: Todo[]) => page.evaluate(([sid, list]: [string, Todo[]]) => {
    const f = document.getElementById("f-waiting") as HTMLIFrameElement;
    const now = Math.floor(Date.now() / 1000);
    f.contentWindow!.postMessage({ type: "feed", now, userTodosOn: true, userTodoRows: [{ sid, name: "api", color: { bg: "#123456", fg: "#ffffff" },
      todos: list.map((t) => ({ id: t.id, text: t.text, createdT: now - t.age, detail: t.detail })) }] }, "*");
  }, [SID, rows] as [string, Todo[]]);
  await feed(todos);
  const W = page.frameLocator("#f-waiting"), F = page.frameLocator("#f-files");
  await W.locator(".ut-reply").first().waitFor({ timeout: 10000 });
  const state = () => page.evaluate(() => {
    const w = (document.getElementById("f-waiting") as HTMLIFrameElement).contentWindow!;
    const f = (document.getElementById("f-files") as HTMLIFrameElement).contentWindow!;
    const act = (d: Document) => { const a = d.activeElement; return a ? (a.className || a.tagName) : ""; };
    return {
      ring: (document.querySelector(".pane-focused") || { id: "" }).id,
      filesShown: getComputedStyle(document.getElementById("files-pane")!).display !== "none",
      filesOn: document.body.classList.contains("po-files"),
      waitingHas: w.document.hasFocus(), filesHas: f.document.hasFocus(),
      waitingActive: act(w.document),
      viewer: !!f.document.getElementById("romp-fileview"),        // the viewer in the FILES pane
      viewerHere: !!w.document.getElementById("romp-fileview"),    // the viewer over the WAITING pane
      modal: !!w.document.getElementById("ut-reply-prompt"),
      box: (w.document.querySelector(".ut-reply-input") as HTMLTextAreaElement | null)?.value ?? null,
    };
  });
  // the keyboard is back in the Reply box (the modal takes it after the viewer over this pane closes, a tick later)
  const boxFocused = () => page.waitForFunction(() => {
    const d = (document.getElementById("f-waiting") as HTMLIFrameElement).contentWindow!.document;
    return d.hasFocus() && !!d.activeElement && d.activeElement.className === "ut-reply-input";
  }, null, { timeout: 10000 });
  // one raw press: mouse down and up at the element's centre, no retry on a hit-target change (locator.click
  // retries, which is exactly what would hide a dropped click)
  const press = async (loc: any) => {
    const b = await loc.boundingBox();
    assert.ok(b, "the pressed element has a box");
    await page.mouse.move(b.x + b.width / 2, b.y + b.height / 2);
    await page.mouse.down();
    await page.mouse.up();
  };
  // what the pane posted to its kernel stand-in (opts.kernel), and the browse messages the SHELL's window received: the two
  // the file browser can send up (browseFiles, a relay ask; browseClosed, the feed's restore), recorded from here on, plus the
  // test's own sentinel (below)
  const posted = () => page.evaluate(() => ((((document.getElementById("f-waiting") as HTMLIFrameElement).contentWindow as any).__posted) || []) as any[]);
  await page.evaluate(() => {
    const w = window as any; w.__shellSaw = [];
    window.addEventListener("message", (e) => { const m = (e as MessageEvent).data || {}; if (m.romp === "browseFiles" || m.romp === "browseClosed" || m.romp === "testSentinel") w.__shellSaw.push(m.romp); });
  });
  const shellSaw = () => page.evaluate(() => (window as any).__shellSaw as string[]);
  // A read of the shell's recorder right after the listing detached runs AHEAD of the message task a browseClosed would queue in
  // the shell (15 of 17 Chromium runs read early; the review's round 2, item 7), so a close that wrongly sent one passed. The
  // read waits for a sentinel the PANE's frame posts to the shell after the detach: one source, one target, so the sentinel
  // arrives behind anything the close posted, and a recorder that holds the sentinel alone heard no browseClosed
  const paneFrame = () => {
    const f = page.frames().find((fr: any) => { try { return new URL(fr.url()).pathname === "/waiting"; } catch { return false; } });
    assert.ok(f, "the Waiting pane's frame is in the page");
    return f;
  };
  const sentinel = async () => {
    await paneFrame().evaluate(() => { window.parent.postMessage({ romp: "testSentinel" }, "*"); });
    await page.waitForFunction(() => ((window as any).__shellSaw as string[]).includes("testSentinel"), null, { timeout: 10000 });
  };
  return { page, W, F, feed, state, boxFocused, press, posted, shellSaw, sentinel, errors, served };
}

// the two ways the Files pane is not on screen: its control hidden (a fresh install: the shell closes the pane and refuses
// to bring it forward, T317b), and the control shown with the pane closed (T404: a closed pane is not brought forward)
const HERE: Array<{ name: string; opts: Boot }> = [
  { name: "the Files control hidden (the fresh-install default)", opts: {} },
  { name: "the control shown and the Files pane closed", opts: { filesControl: true } },
];

for (const name of ["firefox", "chromium"]) {
  for (const fx of HERE) {
    test(`in ${name}, ${fx.name}: Enter on a Reply-modal link opens the viewer OVER the Waiting pane; Escape closes it there, the modal and its text stay, and the keyboard returns to the box`, async (t) => {
      if (!pw) { t.skip("playwright is not installed under vscode-extension: the browser legs need it (CI installs no browsers)"); return; }
      let browser: any;
      try { browser = await pw[name].launch(); }
      catch (e) { t.skip("no playwright " + name + " on this box, and this leg needs it (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
      try {
        const { page, W, state, boxFocused, errors, served } = await boot(browser, [{ id: "t1", text: "Pick the layout", age: 120, detail: DETAIL }], fx.opts);
        let s = await state();
        assert.equal(s.filesShown, false, "the Files pane starts off");
        assert.equal(s.filesOn, false);
        // Reply; half an answer typed; Shift+Tab to the link; Enter
        await W.locator(".ut-reply").click();
        await page.keyboard.type("the first, because");
        await page.keyboard.press("Shift+Tab");
        s = await state();
        assert.equal(s.waitingActive, "file-uri-link", "Shift+Tab reaches the link");
        await page.keyboard.press("Enter");
        await W.locator("#romp-fileview").waitFor({ timeout: 10000 });
        s = await state();
        assert.equal(s.viewerHere, true, "the viewer opened over the Waiting pane");
        assert.equal(s.viewer, false, "nothing reached the Files pane");
        assert.equal(s.filesShown, false, "the Files pane stays off: no closed pane is brought forward (T404), and a hidden control cannot be (T317b)");
        assert.equal(s.filesOn, false, "the shell's own state agrees (po.files)");
        assert.equal(s.waitingHas, true, "the keyboard stayed in this document, with the viewer, in " + name);
        assert.equal(s.modal, true, "the Reply modal is still up behind the viewer");
        assert.equal(served.length, 1, "the viewer fetched the file once");
        assert.match(served[0], /path=docs%2Fdesign\.md/); assert.match(served[0], /sid=11111111-2222/);
        // Escape closes the VIEWER, not the modal; the typed answer is intact; the keyboard comes back into the box
        await page.keyboard.press("Escape");
        await W.locator("#romp-fileview").waitFor({ state: "detached", timeout: 10000 });
        s = await state();
        assert.equal(s.modal, true, "the modal's Escape stood aside for the viewer's");
        assert.equal(s.box, "the first, because", "the half-typed answer survived");
        await boxFocused();
        // the next Escape is the modal's
        await page.keyboard.press("Escape");
        await W.locator("#ut-reply-prompt").waitFor({ state: "detached", timeout: 10000 });
        assert.deepEqual(errors, [], "no script error in any frame");
      } finally { await browser.close(); }
    });
  }

  test(`in ${name}, the Files pane on screen: Enter on a Reply-modal link opens the file THERE and moves focus there; Escape closes the viewer, the modal and its text stay`, async (t) => {
    if (!pw) { t.skip("playwright is not installed under vscode-extension — the browser legs need it (CI installs no browsers)"); return; }
    let browser: any;
    try { browser = await pw[name].launch(); }
    catch (e) { t.skip("no playwright " + name + " on this box — this leg needs it (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
    try {
      const { page, W, F, state, errors, served } = await boot(browser, [{ id: "t1", text: "Pick the layout", age: 120, detail: DETAIL }], { panes: "waiting,files", filesControl: true });
      let s = await state();
      assert.equal(s.filesShown, true, "the Files pane is on screen: its control shown and the pane open");
      assert.equal(s.filesOn, true, "through the shell's own state (po.files)");
      // Reply; half an answer typed; Shift+Tab to the link; Enter
      await W.locator(".ut-reply").click();
      await page.keyboard.type("the first, because");
      await page.keyboard.press("Shift+Tab");
      s = await state();
      assert.equal(s.waitingActive, "file-uri-link", "Shift+Tab reaches the link");
      await page.keyboard.press("Enter");
      await F.locator("#romp-fileview").waitFor({ timeout: 10000 });
      s = await state();
      assert.equal(s.viewer, true, "the open Files pane took the click");
      assert.equal(s.viewerHere, false, "nothing opened over the Waiting pane");
      assert.equal(s.filesHas, true, "the Files document holds focus, in " + name);
      assert.equal(s.waitingHas, false);
      assert.equal(s.ring, "files-pane", "the shell's focus ring followed");
      assert.equal(s.modal, true, "the Reply modal is still up behind");
      assert.equal(served.length, 1, "the viewer fetched the file once");
      assert.match(served[0], /path=docs%2Fdesign\.md/); assert.match(served[0], /sid=11111111-2222/);
      // Escape closes the VIEWER, not the modal; the typed answer is intact
      await page.keyboard.press("Escape");
      await F.locator("#romp-fileview").waitFor({ state: "detached", timeout: 10000 });
      s = await state();
      assert.equal(s.modal, true, "the Reply modal never saw the key");
      assert.equal(s.box, "the first, because", "the half-typed answer survived");
      // back by the shell's own pane nav: the modal takes the focus into its box
      await page.keyboard.press("Alt+ArrowLeft");
      await page.waitForFunction(() => (document.getElementById("f-waiting") as HTMLIFrameElement).contentWindow!.document.hasFocus(), null, { timeout: 10000 });
      s = await state();
      assert.equal(s.waitingActive, "ut-reply-input", "focus returns to the box, not the body behind the overlay");
      assert.deepEqual(errors, [], "no script error in any frame");
    } finally { await browser.close(); }
  });

  test(`in ${name}: the viewer's folder link opens the file BROWSER over the Waiting pane, the listing asks the kernel over this pane's socket, a pick opens the viewer here, and neither close reaches the shell`, async (t) => {
    if (!pw) { t.skip("playwright is not installed under vscode-extension: the browser legs need it (CI installs no browsers)"); return; }
    let browser: any;
    try { browser = await pw[name].launch(); }
    catch (e) { t.skip("no playwright " + name + " on this box, and this leg needs it (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
    try {
      // the fresh-install default (the Files pane off: the route is here), the pane's poster stand-in and the chat's stylesheet
      const { page, W, state, posted, shellSaw, sentinel, errors, served } = await boot(browser, [{ id: "t1", text: "Pick the layout", age: 120, detail: DETAIL }], { kernel: true });
      // a row's fold and its link: the viewer over this pane, no modal in this flow
      await W.locator(".ut-text.ut-has-detail").click();
      await W.locator(".ut-detail.open .file-uri-link").click();
      await W.locator("#romp-fileview").waitFor({ timeout: 10000 });
      assert.equal(served.length, 1, "the viewer fetched the file");
      const dir = W.locator("#romp-fileview .fileview-dir-link");
      assert.equal(await dir.textContent(), "docs/", "the title's directory half");
      assert.equal(await dir.getAttribute("title"), "Browse this file's folder");
      await dir.click();
      await W.locator("#romp-filebrowse").waitFor({ timeout: 10000 });
      await W.locator("#romp-fileview").waitFor({ state: "detached", timeout: 10000 });   // the one-directional stack: the listing replaces the viewer
      let s = await state();
      assert.equal(s.viewerHere, false);
      assert.equal(s.filesShown, false, "the Files pane stays off: the ask stayed in this window");
      assert.equal(s.waitingHas, true, "the keyboard stayed in this document, in " + name);
      const asks = (await posted()).filter((m: any) => m.type === "listDir");
      assert.deepEqual(asks, [{ type: "listDir", path: "docs", sid: SID, reqId: 1, hidden: false }], "one listDir over this pane's socket, for the file's folder and session");
      assert.deepEqual(await shellSaw(), [], "the shell heard nothing: no relay went up");
      // the listing is the topmost surface at its centre (the browser's backdrop over the rows, styles.css), a live click target
      assert.equal(await page.evaluate(() => {
        const d = (document.getElementById("f-waiting") as HTMLIFrameElement).contentWindow!.document;
        const card = d.querySelector("#romp-filebrowse .filebrowse")!.getBoundingClientRect();
        const hit = d.elementFromPoint(card.left + card.width / 2, card.top + card.height / 2);
        return !!hit && !!hit.closest("#romp-filebrowse");
      }), true, "a click at the card's centre lands on the browser");
      // the kernel's listing, as the pane shim would dispatch it: the rows render; a file row picked opens the viewer HERE (the
      // default openFile), over the listing
      await page.evaluate(([sid, reqId]: [string, number]) => {
        const f = document.getElementById("f-waiting") as HTMLIFrameElement;
        f.contentWindow!.postMessage({ type: "dirListing", reqId, sid, base: "docs", parent: ".", entries: [
          { name: "img", isDir: true, isLink: false, size: 0, mtime: 1700000000 },
          { name: "design.md", isDir: false, isLink: false, size: 24, mtime: 1700000000, viewable: true },
        ] }, "*");
      }, [SID, asks[0].reqId] as [string, number]);
      const row = W.locator('#romp-filebrowse .fb-row[data-act="file"]');
      await row.waitFor({ timeout: 10000 });
      assert.equal(await row.locator(".fb-name").textContent(), "design.md");
      assert.equal(await W.locator('#romp-filebrowse .fb-row[data-act="dir"] .fb-name').textContent(), "img/");
      await row.click();
      await W.locator("#romp-fileview").waitFor({ timeout: 10000 });
      assert.equal(served.length, 2, "the pick fetched the file: the viewer here");
      assert.match(served[1], /path=docs%2Fdesign\.md/); assert.match(served[1], /sid=11111111-2222/, "the listing's session rides the pick");
      s = await state();
      assert.equal(s.viewerHere, true);
      assert.equal(await W.locator("#romp-filebrowse").count(), 1, "the listing stays under the viewer");
      // Escape closes the viewer (topmost), the next the listing; neither close reaches the shell
      await page.keyboard.press("Escape");
      await W.locator("#romp-fileview").waitFor({ state: "detached", timeout: 10000 });
      assert.equal(await W.locator("#romp-filebrowse").count(), 1, "the listing is still up after the viewer's close");
      await page.keyboard.press("Escape");
      await W.locator("#romp-filebrowse").waitFor({ state: "detached", timeout: 10000 });
      await sentinel();   // posted from the pane after the detach: a browseClosed the close had sent would sit ahead of it
      assert.deepEqual(await shellSaw(), ["testSentinel"], "no browseClosed: this pane's close owes the shell nothing (shellRestore false)");
      assert.deepEqual(errors, [], "no script error in any frame");
    } finally { await browser.close(); }
  });

  test(`in ${name}: a listing reached through the Reply modal's own link draws ABOVE the modal and its rows take the click; Escape closes the listing first, the typed answer survives, and the next Escape closes the modal`, async (t) => {
    if (!pw) { t.skip("playwright is not installed under vscode-extension: the browser legs need it (CI installs no browsers)"); return; }
    let browser: any;
    try { browser = await pw[name].launch(); }
    catch (e) { t.skip("no playwright " + name + " on this box, and this leg needs it (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
    try {
      // the fresh-install default (the Files pane off: the route is here), the poster stand-in and the chat's stylesheet, so the
      // overlays stack as served
      const { page, W, state, boxFocused, posted, shellSaw, sentinel, errors, served } = await boot(browser, [{ id: "t1", text: "Pick the layout", age: 120, detail: DETAIL }], { kernel: true });
      // Reply; half an answer typed; Shift+Tab to the link; Enter: the viewer over this pane, the modal behind it
      await W.locator(".ut-reply").click();
      await page.keyboard.type("the first, because");
      await page.keyboard.press("Shift+Tab");
      await page.keyboard.press("Enter");
      await W.locator("#romp-fileview").waitFor({ timeout: 10000 });
      assert.equal(served.length, 1, "the viewer fetched the file");
      // the viewer's directory link: the listing replaces the viewer (the one-directional stack); the modal is still up
      await W.locator("#romp-fileview .fileview-dir-link").click();
      await W.locator("#romp-filebrowse").waitFor({ timeout: 10000 });
      await W.locator("#romp-fileview").waitFor({ state: "detached", timeout: 10000 });
      let s = await state();
      assert.equal(s.modal, true, "the Reply modal is still up");
      assert.equal(s.box, "the first, because", "with its half-typed answer");
      const asks = (await posted()).filter((m: any) => m.type === "listDir");
      assert.deepEqual(asks, [{ type: "listDir", path: "docs", sid: SID, reqId: 1, hidden: false }], "one listDir over this pane's socket, for the file's folder");
      // the STACKING (styles.css: the Waiting pane's lift, 1100 over the modal's 1000): a point at the card's centre hits the
      // browser, not the modal's overlay. Before the lift the overlay took every click there, and its backdrop close threw the
      // answer away with the listing still up
      const top = await page.evaluate(() => {
        const d = (document.getElementById("f-waiting") as HTMLIFrameElement).contentWindow!.document;
        const card = d.querySelector("#romp-filebrowse .filebrowse")!.getBoundingClientRect();
        const hit = d.elementFromPoint(card.left + card.width / 2, card.top + card.height / 2);
        const cs = (id: string) => d.defaultView!.getComputedStyle(d.getElementById(id)!).zIndex;
        return { browser: !!hit && !!hit.closest("#romp-filebrowse"), modal: !!hit && !!hit.closest("#ut-reply-prompt"), z: [cs("ut-reply-prompt"), cs("romp-filebrowse")] };
      });
      assert.deepEqual(top, { browser: true, modal: false, z: ["1000", "1100"] }, "the listing is the topmost surface at its centre, over the modal");
      // the kernel's listing, as the pane shim would dispatch it; a DIRECTORY row clicked descends (a second listDir): the rows are
      // live click targets over the modal
      await page.evaluate(([sid, reqId]: [string, number]) => {
        const f = document.getElementById("f-waiting") as HTMLIFrameElement;
        f.contentWindow!.postMessage({ type: "dirListing", reqId, sid, base: "docs", parent: ".", entries: [
          { name: "img", isDir: true, isLink: false, size: 0, mtime: 1700000000 },
          { name: "design.md", isDir: false, isLink: false, size: 24, mtime: 1700000000, viewable: true },
        ] }, "*");
      }, [SID, asks[0].reqId] as [string, number]);
      const dirRow = W.locator('#romp-filebrowse .fb-row[data-act="dir"]');
      await dirRow.waitFor({ timeout: 10000 });
      assert.equal(await dirRow.locator(".fb-name").textContent(), "img/");
      await dirRow.click();
      await page.waitForFunction(() => ((((document.getElementById("f-waiting") as HTMLIFrameElement).contentWindow as any).__posted) || []).filter((m: any) => m.type === "listDir").length === 2, null, { timeout: 10000 });
      const asks2 = (await posted()).filter((m: any) => m.type === "listDir");
      assert.deepEqual(asks2[1], { type: "listDir", path: "docs/img", sid: SID, reqId: 2, hidden: false }, "the click landed on the row: the listing descends");
      s = await state();
      assert.equal(s.modal, true, "the modal is untouched by the click");
      assert.equal(s.box, "the first, because");
      // Escape closes the LISTING, not the modal (the modal's capture handler stands aside, the browser's own closes it): the
      // typed answer is intact, the keyboard comes back into the box, and the shell heard nothing (no relay, no browseClosed)
      await page.keyboard.press("Escape");
      await W.locator("#romp-filebrowse").waitFor({ state: "detached", timeout: 10000 });
      s = await state();
      assert.equal(s.modal, true, "the modal's Escape stood aside for the listing's");
      assert.equal(s.box, "the first, because", "the half-typed answer survived");
      await boxFocused();
      await sentinel();
      assert.deepEqual(await shellSaw(), ["testSentinel"], "the shell heard no relay and no browseClosed");
      // the next Escape is the modal's
      await page.keyboard.press("Escape");
      await W.locator("#ut-reply-prompt").waitFor({ state: "detached", timeout: 10000 });
      assert.deepEqual(errors, [], "no script error in any frame");
    } finally { await browser.close(); }
  });

  test(`in ${name}: a detail link's click lands with a Dismiss armed on another row, and across a feed frame between mouse down and up; so does Reply`, async (t) => {
    if (!pw) { t.skip("playwright is not installed under vscode-extension — the browser legs need it (CI installs no browsers)"); return; }
    let browser: any;
    try { browser = await pw[name].launch(); }
    catch (e) { t.skip("no playwright " + name + " on this box — this leg needs it (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
    try {
      const todos: Todo[] = [{ id: "t1", text: "Pick the layout", age: 300, detail: DETAIL }, { id: "t2", text: "Approve the rollout", age: 120, detail: DETAIL2 }];
      // the fresh-install default: the Files pane off, so every open here lands over the Waiting pane (the route above)
      const { page, W, feed, state, press, errors, served } = await boot(browser, todos);
      const row1 = W.locator('.ut-item[data-tid="t1"]'), row2 = W.locator('.ut-item[data-tid="t2"]');
      await row2.locator(".ut-text.ut-has-detail").click();          // row 2's fold open: its link is on screen
      const link2 = row2.locator(".ut-detail.open .file-uri-link");
      await link2.waitFor({ timeout: 10000 });
      // (a) Dismiss armed on row 1, then ONE raw press on row 2's link: the disarm's re-render is held until
      // the release, so the pressed span is still the one under the pointer when the click fires
      await row1.locator(".ut-dismiss").click();
      assert.equal(await row1.locator(".ut-dismiss").textContent(), "Really dismiss?");
      await press(link2);
      await W.locator("#romp-fileview").waitFor({ timeout: 10000 });
      assert.equal(served.length, 1, "the file opened on the first press");
      assert.match(served[0], /path=docs%2Frollout\.md/);
      // the held re-render ran after the release: the arm is gone. Waited for EXPLICITLY before the next read
      // of the list: the flush is a timer, and Chromium runs it a frame (~16ms) after the release, so a
      // locator that resolves a row's node before the rebuild and measures it after gets a detached node
      const disarmed = () => page.waitForFunction(() => {
        const d = (document.getElementById("f-waiting") as HTMLIFrameElement).contentWindow!.document;
        return d.querySelector('.ut-item[data-tid="t1"] .ut-dismiss')!.textContent === "Dismiss";
      }, null, { timeout: 10000 });
      await disarmed();
      let s = await state();
      assert.equal(s.viewerHere, true, "over the Waiting pane: the Files pane is off, so the route is here");
      assert.equal(s.waitingHas, true, "and the keyboard stayed in this document, with the viewer");
      await page.keyboard.press("Escape");
      await W.locator("#romp-fileview").waitFor({ state: "detached", timeout: 10000 });
      // (b) mouse down on the link, a feed frame while it is down (the list would rebuild), mouse up
      const b = await link2.boundingBox();
      assert.ok(b);
      await page.mouse.move(b!.x + b!.width / 2, b!.y + b!.height / 2);
      await page.mouse.down();
      await feed([todos[0], { ...todos[1], text: "Approve the rollout (v2)" }]);
      // the row's one-line text is the .ut-text's first text node (the fold hint follows it in the same span)
      const rowText = (tid: string) => page.evaluate((id: string) => {
        const d = (document.getElementById("f-waiting") as HTMLIFrameElement).contentWindow!.document;
        return d.querySelector(`.ut-item[data-tid="${id}"] .ut-text`)!.firstChild!.textContent;
      }, tid);
      assert.equal(await rowText("t2"), "Approve the rollout", "the frame is HELD while the pointer is down");
      await page.mouse.up();
      await W.locator("#romp-fileview").waitFor({ timeout: 10000 });
      assert.equal(served.length, 2, "the click landed on the node it pressed");
      await page.waitForFunction(() => {
        const d = (document.getElementById("f-waiting") as HTMLIFrameElement).contentWindow!.document;
        return d.querySelector('.ut-item[data-tid="t2"] .ut-text')!.firstChild!.textContent === "Approve the rollout (v2)";
      }, null, { timeout: 10000 });   // …and the held frame landed after the release
      s = await state();
      assert.equal(s.viewerHere, true);
      await page.keyboard.press("Escape");
      await W.locator("#romp-fileview").waitFor({ state: "detached", timeout: 10000 });
      // (c) the same two presses on Reply — the control the finding measured against
      await row1.locator(".ut-dismiss").click();
      assert.equal(await row1.locator(".ut-dismiss").textContent(), "Really dismiss?");
      await press(row2.locator(".ut-reply"));
      await W.locator("#ut-reply-prompt").waitFor({ timeout: 10000 });
      await disarmed();   // the disarm's held rebuild has replaced row 2's Reply: measure the new node, not the old
      await page.keyboard.press("Escape");
      await W.locator("#ut-reply-prompt").waitFor({ state: "detached", timeout: 10000 });
      const rb = await row2.locator(".ut-reply").boundingBox();
      assert.ok(rb);
      await page.mouse.move(rb!.x + rb!.width / 2, rb!.y + rb!.height / 2);
      await page.mouse.down();
      await feed(todos);
      await page.mouse.up();
      await W.locator("#ut-reply-prompt").waitFor({ timeout: 10000 });
      assert.deepEqual(errors, [], "no script error in any frame");
    } finally { await browser.close(); }
  });
}

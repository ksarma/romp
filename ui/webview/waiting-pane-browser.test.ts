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
//    (https://github.com/romp-on/romp/pull/1596); its focus and Escape assertions live on in the Files-pane-open case.
// 2. A click whose pressed node a re-render replaced mid-press never fires (ui/CLAUDE.md, click safety):
//    with a Dismiss armed on another row the document pointerdown listener disarmed and re-rendered
//    synchronously, and a feed frame between mousedown and mouseup rebuilt the list — either dropped the
//    click on a detail link, and on Reply. The pane now HOLDS re-renders while a pointer is pressed on the
//    list and flushes after the release, a tick later so the click fires against the still-present node
//    (the tab strip's and the timeline's idiom, render.ts / romp-timeline-view.js).
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
// shell's word through file-route.ts) and the viewer's opener for the "here" arm (user-todo-links.test.ts and
// waiting-link-focus.test.ts run the same body the same way)
type Route = "pane" | "here";
type Fn = (rows: unknown[], w: unknown, path: string, sid: string, todoId: string, at: unknown, route: () => Route, openHere: (...a: unknown[]) => void) => void;
function openTodoPath(): Fn {
  const body = WAITING.split("function openTodoPath(path: string, sid: string, todoId: string, at: LinkTarget | null = null): void {")[1].split("\n}")[0];
  return new Function("rows", "window", "path", "sid", "todoId", "at", "todoLinkRoute", "openFileView", body) as Fn;
}
class ShellIFrame { constructor(public contentWindow: { focus(): void } | null) {} }
// the shell as the pane reads it: an iframe of the SHELL's realm, and the shell's pane toggle on its window
function shell(calls: string[], withToggle: boolean) {
  const files = new ShellIFrame({ focus: () => { calls.push("focus"); } });
  const view: Record<string, unknown> = { HTMLIFrameElement: ShellIFrame };
  if (withToggle) view.__rompPaneToggle = (k: string, to: unknown) => { calls.push("toggle " + k + " " + String(to)); };
  return { parent: { postMessage: (m: any) => { calls.push("post " + m.romp + " " + m.pane); }, document: { getElementById: (id: string) => (id === "f-files" ? files : null), defaultView: view } } };
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
  // the Reply modal's Escape stands aside while the viewer is up over this pane, and takes the keyboard back once it is gone
  const modal = WAITING.slice(WAITING.indexOf("function showReply("), WAITING.indexOf("// ── render"));
  assert.match(modal, /const onKey = \(e: KeyboardEvent\) => \{\n\s*if \(e\.key !== "Escape"\) return;\n\s*if \(document\.getElementById\("romp-fileview"\)\) \{ setTimeout\(\(\) => \{ if \(overlay\.isConnected && !document\.getElementById\("romp-fileview"\)\) input\.focus\(\); \}, 0\); return; \}\n\s*e\.stopPropagation\(\); close\(\);\n\s*\};/);
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
const FILES_HTML = `<!DOCTYPE html><html><head><meta charset=utf-8></head><body class=fileview-pane>
<div id=files-empty></div><script src=/dist/files.js></script></body></html>`;

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

type Todo = { id: string; text: string; age: number; detail: string };
// `panes`: the ?panes= set the shell opens with (the default leaves the Files pane off, as a fresh install does);
// `filesControl`: the gear's Files control shown (romp:settings.showFilesControl, written into the shell's store before its
// scripts run, the way the gear would have left it); absent, the fresh-install default, hidden
type Boot = { panes?: string; filesControl?: boolean };
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
    if (u.pathname === "/waiting") return html(WAITING_HTML);
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
  return { page, W, F, feed, state, boxFocused, press, errors, served };
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

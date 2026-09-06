// The keyboard follows a Waiting-on-you detail link into the Files pane (plans/file-review.md, Slice 0;
// the 2026-09-06 review). The link opens the file in ANOTHER iframe, and the viewer's only keyboard close
// is a document-level Escape in that iframe's document; a keydown never crosses an iframe boundary. So a
// keyboard user who opened a file from the Reply modal (Shift+Tab to the link, Enter) and pressed Escape
// closed the modal and left the viewer up, and the mouse route did the same. waiting.ts now hands the
// Files pane's window the focus after posting the click (openTodoPath), and the Reply modal takes the
// focus back into its box when the pane regains it (showReply), so the return trip does not land on the
// body behind the overlay.
//
// Two legs. The first executes openTodoPath's body out of waiting.ts's source with a window stand-in (the
// user-todo-links.test.ts idiom) and pins the modal's listener at source — no browser. The second is the
// real thing: the worktree's waiting.ts and files.ts bundles (esbuild, the webview build's options) in two
// same-origin iframes under a shell stand-in that runs the kernel's own _LANDING_FOCUS_JS and
// _LANDING_ESC_JS and the shell's Files-pane viewFile branch, all sliced from kernel.py at run time;
// headless Chromium drives the keyboard and the mouse. It skips LOUDLY without a playwright browser (CI
// installs none), as the served legs of tests/test_awaiting_box_sync.py and its siblings do.
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
const ROWS = [{ sid: SID, name: "api", color: { bg: "#123456", fg: "#ffffff" }, todos: [] }];

// ── leg 1: openTodoPath, executed out of the source ───────────────────────────────────────────────
type Fn = (rows: unknown[], w: unknown, path: string, sid: string, todoId: string) => void;
function openTodoPath(): Fn {
  const body = WAITING.split("function openTodoPath(path: string, sid: string, todoId: string): void {")[1].split("\n}")[0];
  return new Function("rows", "window", "path", "sid", "todoId", body) as Fn;
}

// the shell's document as the pane reads it: an iframe of the SHELL's realm (its own HTMLIFrameElement, reached
// through defaultView — the check waiting.ts makes, since an element is never an instance of another
// document's constructor), and a parent that is not an iframe at all
class ShellIFrame { constructor(public contentWindow: { focus(): void } | null) {} }
function shell(post: (m: any) => void, byId: (id: string) => unknown) {
  return { parent: { postMessage: post, document: { getElementById: byId, defaultView: { HTMLIFrameElement: ShellIFrame } } } };
}

test("openTodoPath posts the click to the shell, then hands the Files pane's window the keyboard", () => {
  const calls: string[] = [];
  const files = new ShellIFrame({ focus: () => { calls.push("focus"); } });
  const win = shell((m) => { calls.push("post " + m.romp + " " + m.pane + " " + m.path + " " + m.todoId); }, (id) => (id === "f-files" ? files : null));
  openTodoPath()(ROWS, win, "docs/design.md", SID, "t1");
  assert.deepEqual(calls, ["post viewFile pane docs/design.md t1", "focus"], "the message first, the focus after it, once");
});

test("a parent this pane cannot read, a shell with no Files iframe, an f-files that is no iframe: the message still goes, nothing throws", () => {
  const posted: any[] = [];
  const post = (m: unknown) => { posted.push(m); };
  const hostile = { parent: { postMessage: post, get document() { throw new Error("SecurityError: Blocked a frame with origin"); } } };
  openTodoPath()(ROWS, hostile, "docs/design.md", SID, "t1");
  openTodoPath()(ROWS, shell(post, () => null), "docs/design.md", SID, "t1");
  const notAFrame = { contentWindow: { focus: () => { throw new Error("must not be reached"); } } };
  openTodoPath()(ROWS, shell(post, () => notAFrame), "docs/design.md", SID, "t1");
  // an iframe the shell has not loaded yet has no window — nothing to focus, nothing thrown
  openTodoPath()(ROWS, shell(post, () => new ShellIFrame(null)), "docs/design.md", SID, "t1");
  assert.equal(posted.length, 4);
  assert.ok(posted.every((m) => m.romp === "viewFile" && m.pane === "pane" && m.sid === SID && m.todoId === "t1"));
});

test("the Reply modal takes the focus back into its box when the pane regains it, and the listener goes with the modal", () => {
  const modal = WAITING.slice(WAITING.indexOf("function showReply("), WAITING.indexOf("// ── render"));
  assert.match(modal, /const onFocus = \(\) => \{ if \(!overlay\.isConnected\) \{ window\.removeEventListener\("focus", onFocus\); return; \} input\.focus\(\); \};/);
  assert.match(modal, /const close = \(\) => \{ overlay\.remove\(\); document\.removeEventListener\("keydown", onKey, true\); window\.removeEventListener\("focus", onFocus\); \};/);
  assert.match(modal, /window\.addEventListener\("focus", onFocus\);\n\s*input\.focus\(\);\n\}/, "armed at open, after the modal is in the document");
});

// ── leg 2: the real bundles, in a real browser ────────────────────────────────────────────────────
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
// the shell's Files-pane viewFile branch, from its test to the feed branch that follows it
function relayJs(): string {
  const a = KERNEL.indexOf("if(m.romp==='viewFile'&&m.pane==='pane'){");
  const b = KERNEL.indexOf("else if(m.romp==='viewFile'){", a);
  assert.ok(a > 0 && b > a, "the shell's Files-pane viewFile branch moved — re-anchor");
  return KERNEL.slice(a, b);
}
// a pane's bundle, built the way vscode-extension/esbuild.js builds the webview (in memory — nothing on disk)
function bundle(entry: string): string {
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    entryPoints: [path.join(UI, entry)], bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent",
  });
  return r.outputFiles[0].text;
}
// the shell: the two panes side by side, the Files pane toggled OFF (so the relay's bring-forward runs, and
// the focus call lands on a display:none frame — the ordering the fix relies on), the kernel's focus and
// Escape wiring, and the pane controller reduced to what the relay calls
const SHELL_HTML = `<!DOCTYPE html><html><head><meta charset=utf-8>
<style>.pane{display:inline-block;vertical-align:top}iframe{width:480px;height:420px;border:0}</style></head><body>
<div id=waiting-pane class=pane><iframe id=f-waiting src=/waiting></iframe></div>
<div id=files-pane class=pane style="display:none"><iframe id=f-files src=/files></iframe></div>
<script>
window.__rompPaneToggle=function(k,to){var el=document.getElementById(k+'-pane');if(!el)return;
  var on=(to===undefined)?el.style.display==='none':!!to;el.style.display=on?'':'none';};
</script>
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

test("in a browser: Enter on a Reply-modal link opens the file in the Files pane and puts the keyboard there; Escape closes the viewer, the modal stays, Alt+Left returns to the box; a mouse click hands over the same way", async (t) => {
  if (!pw) { t.skip("playwright is not installed under vscode-extension — the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw.chromium.launch(); }
  catch (e) { t.skip("no playwright browser on this box — the browser leg needs one (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  const errors: string[] = [];
  const served: string[] = [];
  try {
    const waitingJs = bundle("waiting.ts"), filesJs = bundle("files.ts");
    const page = await browser.newPage({ viewport: { width: 1000, height: 500 } });
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
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
    await page.goto("http://romp.test/shell");   // the load event covers both frames' boots
    const W = page.frameLocator("#f-waiting"), F = page.frameLocator("#f-files");
    // one feed frame with one todo whose detail names a file — what build_feed ships (no shim here)
    await page.evaluate(([sid, detail]: string[]) => {
      const f = document.getElementById("f-waiting") as HTMLIFrameElement;
      const now = Math.floor(Date.now() / 1000);
      f.contentWindow!.postMessage({ type: "feed", now, userTodosOn: true, userTodoRows: [{ sid, name: "api", color: { bg: "#123456", fg: "#ffffff" },
        todos: [{ id: "t1", text: "Pick the layout", createdT: now - 120, detail }] }] }, "*");
    }, [SID, DETAIL]);
    await W.locator(".ut-reply").waitFor({ timeout: 10000 });
    const state = () => page.evaluate(() => {
      const w = (document.getElementById("f-waiting") as HTMLIFrameElement).contentWindow!;
      const f = (document.getElementById("f-files") as HTMLIFrameElement).contentWindow!;
      const act = (d: Document) => { const a = d.activeElement; return a ? (a.className || a.tagName) : ""; };
      return {
        ring: (document.querySelector(".pane-focused") || { id: "" }).id,
        filesShown: document.getElementById("files-pane")!.style.display !== "none",
        waitingHas: w.document.hasFocus(), filesHas: f.document.hasFocus(),
        waitingActive: act(w.document),
        viewer: !!f.document.getElementById("romp-fileview"),
        modal: !!w.document.getElementById("ut-reply-prompt"),
        box: (w.document.querySelector(".ut-reply-input") as HTMLTextAreaElement | null)?.value ?? null,
      };
    });

    // the keyboard route: Reply (its box takes the focus), Shift+Tab to the link, Enter
    await W.locator(".ut-reply").click();
    let s = await state();
    assert.equal(s.waitingActive, "ut-reply-input", "the modal opens on its box");
    assert.equal(s.filesShown, false, "the Files pane starts toggled off — the relay brings it forward");
    await page.keyboard.press("Shift+Tab");
    s = await state();
    assert.equal(s.waitingActive, "file-uri-link", "Shift+Tab reaches the link (its tab stop is path-links.ts's)");
    await page.keyboard.press("Enter");
    await F.locator("#romp-fileview").waitFor({ timeout: 10000 });
    s = await state();
    assert.equal(s.filesShown, true, "the shell's branch brought the pane forward");
    assert.equal(s.filesHas, true, "the Files document holds the keyboard");
    assert.equal(s.waitingHas, false);
    assert.equal(s.ring, "files-pane", "the shell's focus ring followed (its window-focus wiring)");
    assert.equal(s.modal, true, "the Reply modal is still up behind");
    assert.equal(served.length, 1, "the viewer fetched the file once");
    assert.match(served[0], /path=docs%2Fdesign\.md/); assert.match(served[0], /sid=11111111-2222/, "resolved against the todo's session");
    // Escape closes the VIEWER: the keydown lands in the Files document, where its handler lives
    await page.keyboard.press("Escape");
    await F.locator("#romp-fileview").waitFor({ state: "detached", timeout: 10000 });
    s = await state();
    assert.equal(s.modal, true, "and not the Reply modal, which never saw the key");
    // back by the shell's own pane nav: the modal takes the focus into its box, and typing lands there
    await page.keyboard.press("Alt+ArrowLeft");
    await page.waitForFunction(() => (document.getElementById("f-waiting") as HTMLIFrameElement).contentWindow!.document.hasFocus(), null, { timeout: 10000 });
    s = await state();
    assert.equal(s.waitingActive, "ut-reply-input", "the return trip lands in the box, not on the body behind the overlay");
    assert.equal(s.ring, "waiting-pane");
    await page.keyboard.type("the first");
    s = await state();
    assert.equal(s.box, "the first");

    // the mouse route shares the handoff: Escape here closes the MODAL (the keyboard is in this pane), then
    // the row's fold opens and its link is clicked
    await page.keyboard.press("Escape");
    await W.locator("#ut-reply-prompt").waitFor({ state: "detached", timeout: 10000 });
    await W.locator(".ut-text.ut-has-detail").click();
    await W.locator(".ut-detail.open .file-uri-link").click();
    await F.locator("#romp-fileview").waitFor({ timeout: 10000 });
    s = await state();
    assert.equal(s.filesHas, true, "a pointer click hands the keyboard over the same way");
    assert.equal(s.ring, "files-pane");
    await page.keyboard.press("Escape");
    await F.locator("#romp-fileview").waitFor({ state: "detached", timeout: 10000 });
    assert.equal(served.length, 2);
    assert.deepEqual(errors, [], "no script error in any frame");
  } finally { await browser.close(); }
});

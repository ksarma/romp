// The Waiting-on-you pane under the shell, in Firefox AND Chromium (plans/file-review.md, Slice 0; the
// 2026-09-06 review, round 3). Two defects waiting-link-focus.test.ts's Chromium-only leg could not see:
//
// 1. Firefox refuses to focus a display:none frame's window. openTodoPath focused the Files iframe's window
//    right after posting viewFile — a task BEFORE the shell's relay ran __rompPaneToggle('files', true) — so
//    with the Files pane closed (the default, and the case the guide advertises) the focus silently did not
//    land in Firefox: Escape then closed the Reply modal, the typed answer with it, and left the viewer up.
//    Chromium focuses a hidden frame's window and hid the ordering. The pane now brings the Files pane
//    forward itself, through the shell's own toggle (the same call the relay makes, which then finds nothing
//    to change), and focuses after that.
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
// browser (CI installs none); the source leg runs everywhere and pins the two mechanisms as written.
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
type Fn = (rows: unknown[], w: unknown, path: string, sid: string, todoId: string) => void;
function openTodoPath(): Fn {
  const body = WAITING.split("function openTodoPath(path: string, sid: string, todoId: string): void {")[1].split("\n}")[0];
  return new Function("rows", "window", "path", "sid", "todoId", body) as Fn;
}
class ShellIFrame { constructor(public contentWindow: { focus(): void } | null) {} }
// the shell as the pane reads it: an iframe of the SHELL's realm, and the shell's pane toggle on its window
function shell(calls: string[], withToggle: boolean) {
  const files = new ShellIFrame({ focus: () => { calls.push("focus"); } });
  const view: Record<string, unknown> = { HTMLIFrameElement: ShellIFrame };
  if (withToggle) view.__rompPaneToggle = (k: string, to: unknown) => { calls.push("toggle " + k + " " + String(to)); };
  return { parent: { postMessage: (m: any) => { calls.push("post " + m.romp + " " + m.pane); }, document: { getElementById: (id: string) => (id === "f-files" ? files : null), defaultView: view } } };
}

test("openTodoPath brings the Files pane forward through the shell's own toggle BEFORE it focuses the pane's window", () => {
  const calls: string[] = [];
  openTodoPath()(ROWS, shell(calls, true), "docs/design.md", SID, "t1");
  assert.deepEqual(calls, ["post viewFile pane", "toggle files true", "focus"],
    "the message, then the bring-forward, then the focus — a display:none frame's window takes no focus in Firefox");
  // a shell without the toggle (an older landing, or a bare parent): the focus still goes, nothing throws
  const bare: string[] = [];
  openTodoPath()(ROWS, shell(bare, false), "docs/design.md", SID, "t1");
  assert.deepEqual(bare, ["post viewFile pane", "focus"]);
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
// the pane controller, with the keys _landing() splices in from _PANE_ORDER
function collapseJs(): string {
  const at = KERNEL.indexOf("_PANE_ORDER = (");
  assert.ok(at > 0, "_PANE_ORDER not found in kernel.py — re-anchor");
  const keys = Array.from(KERNEL.slice(at, KERNEL.indexOf("\n\n", at)).matchAll(/\("(\w+)", "/g)).map((m) => m[1]);
  assert.ok(keys.includes("waiting") && keys.includes("files"), "the pane keys parsed from _PANE_ORDER: " + keys.join(","));
  return kernelJs("_LANDING_COLLAPSE_JS").replace("__PANE_KEYS__", JSON.stringify(keys));
}
// the landing CSS that hides a toggled-off pane — display:none, the property Firefox's focus refuses
function paneCss(): string {
  const a = KERNEL.indexOf('"body:not(.po-chat) #chat-pane{display:none}');
  assert.ok(a > 0, "the landing's pane-hiding rule moved — re-anchor");
  return KERNEL.slice(a + 1, KERNEL.indexOf('"', a + 1));
}
// the shell's Files-pane viewFile branch, from its test to the feed branch that follows it
function relayJs(): string {
  const a = KERNEL.indexOf("if(m.romp==='viewFile'&&m.pane==='pane'){");
  const b = KERNEL.indexOf("else if(m.romp==='viewFile'){", a);
  assert.ok(a > 0 && b > a, "the shell's Files-pane viewFile branch moved — re-anchor");
  return KERNEL.slice(a, b);
}
function bundle(entry: string): string {
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    entryPoints: [path.join(UI, entry)], bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent",
  });
  return r.outputFiles[0].text;
}
// the shell: the kernel's pane controller owns what is on screen (the URL's ?panes=waiting leaves the Files
// pane OFF, as a fresh install does), its CSS hides the off panes, and its focus, Escape and relay wiring run
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
async function boot(browser: any, todos: Todo[]) {
  const errors: string[] = [];
  const served: string[] = [];
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
  await page.goto("http://romp.test/shell?panes=waiting");   // the load event covers both frames' boots
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
      viewer: !!f.document.getElementById("romp-fileview"),
      modal: !!w.document.getElementById("ut-reply-prompt"),
      box: (w.document.querySelector(".ut-reply-input") as HTMLTextAreaElement | null)?.value ?? null,
    };
  });
  // one raw press: mouse down and up at the element's centre, no retry on a hit-target change (locator.click
  // retries, which is exactly what would hide a dropped click)
  const press = async (loc: any) => {
    const b = await loc.boundingBox();
    assert.ok(b, "the pressed element has a box");
    await page.mouse.move(b.x + b.width / 2, b.y + b.height / 2);
    await page.mouse.down();
    await page.mouse.up();
  };
  return { page, W, F, feed, state, press, errors, served };
}

for (const name of ["firefox", "chromium"]) {
  test(`in ${name}, Files pane closed: Enter on a Reply-modal link brings the pane forward AND moves focus there; Escape closes the viewer, the modal and its text stay`, async (t) => {
    if (!pw) { t.skip("playwright is not installed under vscode-extension — the browser legs need it (CI installs no browsers)"); return; }
    let browser: any;
    try { browser = await pw[name].launch(); }
    catch (e) { t.skip("no playwright " + name + " on this box — this leg needs it (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
    try {
      const { page, W, F, state, errors, served } = await boot(browser, [{ id: "t1", text: "Pick the layout", age: 120, detail: DETAIL }]);
      let s = await state();
      assert.equal(s.filesShown, false, "the Files pane starts off — the shell's default, and the guide's case");
      assert.equal(s.filesOn, false);
      // Reply; half an answer typed; Shift+Tab to the link; Enter
      await W.locator(".ut-reply").click();
      await page.keyboard.type("the first, because");
      await page.keyboard.press("Shift+Tab");
      s = await state();
      assert.equal(s.waitingActive, "file-uri-link", "Shift+Tab reaches the link");
      await page.keyboard.press("Enter");
      await F.locator("#romp-fileview").waitFor({ timeout: 10000 });
      s = await state();
      assert.equal(s.filesShown, true, "the pane came forward");
      assert.equal(s.filesOn, true, "through the shell's own state (po.files), not a stray style");
      assert.equal(s.filesHas, true, "the Files document holds focus — in " + name);
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
      const { page, W, F, feed, state, press, errors, served } = await boot(browser, todos);
      const row1 = W.locator('.ut-item[data-tid="t1"]'), row2 = W.locator('.ut-item[data-tid="t2"]');
      await row2.locator(".ut-text.ut-has-detail").click();          // row 2's fold open: its link is on screen
      const link2 = row2.locator(".ut-detail.open .file-uri-link");
      await link2.waitFor({ timeout: 10000 });
      // (a) Dismiss armed on row 1, then ONE raw press on row 2's link: the disarm's re-render is held until
      // the release, so the pressed span is still the one under the pointer when the click fires
      await row1.locator(".ut-dismiss").click();
      assert.equal(await row1.locator(".ut-dismiss").textContent(), "Really dismiss?");
      await press(link2);
      await F.locator("#romp-fileview").waitFor({ timeout: 10000 });
      assert.equal(served.length, 1, "the file opened on the first press");
      assert.match(served[0], /path=docs%2Frollout\.md/);
      await page.waitForFunction(() => {
        const d = (document.getElementById("f-waiting") as HTMLIFrameElement).contentWindow!.document;
        return d.querySelector('.ut-item[data-tid="t1"] .ut-dismiss')!.textContent === "Dismiss";
      }, null, { timeout: 10000 });   // the held re-render ran after the release: the arm is gone
      let s = await state();
      assert.equal(s.filesHas, true, "and focus moved to the Files pane with the file");
      await page.keyboard.press("Escape");
      await F.locator("#romp-fileview").waitFor({ state: "detached", timeout: 10000 });
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
      await F.locator("#romp-fileview").waitFor({ timeout: 10000 });
      assert.equal(served.length, 2, "the click landed on the node it pressed");
      await page.waitForFunction(() => {
        const d = (document.getElementById("f-waiting") as HTMLIFrameElement).contentWindow!.document;
        return d.querySelector('.ut-item[data-tid="t2"] .ut-text')!.firstChild!.textContent === "Approve the rollout (v2)";
      }, null, { timeout: 10000 });   // …and the held frame landed after the release
      s = await state();
      assert.equal(s.viewer, true);
      await page.keyboard.press("Escape");
      await F.locator("#romp-fileview").waitFor({ state: "detached", timeout: 10000 });
      // (c) the same two presses on Reply — the control the finding measured against
      await row1.locator(".ut-dismiss").click();
      assert.equal(await row1.locator(".ut-dismiss").textContent(), "Really dismiss?");
      await press(row2.locator(".ut-reply"));
      await W.locator("#ut-reply-prompt").waitFor({ timeout: 10000 });
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

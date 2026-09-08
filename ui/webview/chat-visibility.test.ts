// The chat page's word for the kernel's pane shim (round 3 of the 2026-09-08 fold). The shim gates its stale
// banner on paneHidden(): hidden when its zero-viewport probe OR the word a pane published says so. In Chromium
// the probe is right for a pane hidden since load and blind to one the shell hides after the user has looked at
// it (the iframe keeps its size), and on the phone shell the chat is the pane shown first, so every switch to
// another tab left the chat's watchdog free to raise the shell banner over a working dashboard (the 2026-08-15
// failure, re-opened when steer 2 dropped the fork's federation-level hold that had published the word for the
// chat). Firefox is the mirror image, measured here: the hidden iframe's viewport reads 0 (the probe is right) and
// its IntersectionObserver does not run (the word goes stale), which is why the shim takes the union and not the
// word first. render.ts has no paint gate (every frame paints), so chat-visibility.ts publishes the same two
// measures the gating panes do, from the same events. Three legs: the module over stand-ins (the ordering rule:
// nothing before the observer's first word), the source pins (render.ts installs it once, on the body, from its
// own visibility), and real browsers: a chat page in the shell's iframe, shown, then hidden each way the shell
// hides a pane (the desktop rail's rule takes the pane WRAPPER to display:none; the phone shell's tab switch
// takes the IFRAME itself to display:none by moving m-on to another tab), with the kernel's own CSS and
// paneHidden() text deciding. The browser legs skip LOUDLY without playwright or a browser (CI installs none).
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { watchChatVisibility, type ChatVisibilityDeps, type ObserverEntryLike } from "./chat-visibility";
import type { PaneHiddenHost } from "./paint-gate";

const requireCjs = createRequire(__filename);
const EXT = process.cwd();                                        // npm test runs in vscode-extension
const UI = path.resolve(EXT, "..", "ui", "webview");
const RENDER = fs.readFileSync(path.join(UI, "render.ts"), "utf8");
const SRC = fs.readFileSync(path.join(UI, "chat-visibility.ts"), "utf8");
const KERNEL = fs.readFileSync(path.resolve(EXT, "..", "kernel", "kernel.py"), "utf8");
const SKEL = fs.readFileSync(path.resolve(EXT, "src", "page-skeleton.ts"), "utf8");

// ── the module, over stand-ins ────────────────────────────────────────────────────────────────────
type Cb = (entries: ObserverEntryLike[]) => void;
function world() {
  const host: PaneHiddenHost = {};
  const listeners: Array<() => void> = [];
  const doc = { hidden: false, addEventListener: (_t: "visibilitychange", fn: () => void) => { listeners.push(fn); } };
  const observed: Element[] = [];
  let cb: Cb | null = null;
  class FakeIO { constructor(f: Cb) { cb = f; } observe(t: Element) { observed.push(t); } }
  const deps: ChatVisibilityDeps = { doc, win: host, Observer: FakeIO };
  return {
    host, doc, deps, observed,
    /** the tab's visibilitychange, in the given state */
    tab(state: "hidden" | "visible") { doc.hidden = state === "hidden"; for (const fn of listeners) fn(); },
    /** the observer's callback over the body */
    entry(intersecting: boolean) { assert.ok(cb, "the observer was constructed"); cb!([{ isIntersecting: intersecting }]); },
    listeners,
  };
}

test("nothing before the observer's first word, on either arm; then the union of both measures on every event", () => {
  const w = world();
  const body = {} as Element;
  watchChatVisibility(body, w.deps);
  assert.deepEqual(w.observed, [body], "the observer watches the element it was given: the page's body");
  assert.equal(w.listeners.length, 1, "one visibilitychange listener");
  w.tab("visible");
  assert.equal(typeof w.host.__rompPaneHidden, "undefined", "a return before the observer's first entry publishes nothing: the shim's probe is right at boot");
  w.tab("hidden");
  assert.equal(typeof w.host.__rompPaneHidden, "undefined", "nor does the hidden arm");
  w.doc.hidden = false;
  w.entry(true);
  assert.equal(w.host.__rompPaneHidden, false, "the first entry: on screen");
  w.entry(false);
  assert.equal(w.host.__rompPaneHidden, true, "hidden after a first show: the case the probe misses (the iframe keeps its size)");
  w.tab("hidden"); assert.equal(w.host.__rompPaneHidden, true);
  w.tab("visible"); assert.equal(w.host.__rompPaneHidden, true, "the tab's return is not a show for a display:none pane");
  w.entry(true); assert.equal(w.host.__rompPaneHidden, false, "the re-show publishes on the observer's callback");
  w.tab("hidden"); assert.equal(w.host.__rompPaneHidden, true, "the tab hidden with the pane on screen: hidden");
  w.tab("visible"); assert.equal(w.host.__rompPaneHidden, false, "the return publishes on visibilitychange");
  assert.equal(typeof w.host.__rompPaneHidden, "boolean", "a boolean, the type the shim tests for");
});

test("no observer, or no body: nothing is installed and nothing published; the shim's probe stands", () => {
  const bare = world();
  bare.deps.Observer = null;
  watchChatVisibility({} as Element, bare.deps);
  assert.equal(bare.listeners.length, 0, "no listener either: a page that published document.hidden alone would read hidden forever after its first tab hide");
  bare.tab("hidden"); bare.tab("visible");
  assert.equal(typeof bare.host.__rompPaneHidden, "undefined");
  const noRoot = world();
  watchChatVisibility(null, noRoot.deps);
  assert.deepEqual(noRoot.observed, []);
  assert.equal(noRoot.listeners.length, 0);
});

test("source pins: render.ts installs the publisher once, at top level, over the page's body, and gates no paint; the module reads the frame's own visibility, never the shell's word", () => {
  assert.match(RENDER, /^import \{ watchChatVisibility, browserChatVisibilityDeps \} from "\.\/chat-visibility";/m);
  assert.match(RENDER, /^watchChatVisibility\(document\.body, browserChatVisibilityDeps\(\)\);/m, "top level, so it runs when the bundle loads (the script sits at the end of the body in both skeletons)");
  assert.equal(RENDER.split("watchChatVisibility(").length - 1, 1, "once");
  assert.ok(!RENDER.includes("paintHeld(") && !RENDER.includes("paintReleased("), "the chat gates no paint: every frame paints");
  assert.ok(!RENDER.includes("__rompPaneHidden") && !SRC.includes("__rompPaneHidden"), "the flag's name lives in paint-gate.ts");
  assert.match(SRC, /import \{ publishPaneHidden, type PaneHiddenHost \} from "\.\/paint-gate";/, "the shared publisher, so the shim's word has one shape");
  assert.match(SRC, /let intersecting: boolean \| null = null;/, "the observer's word starts null: nothing is published before it speaks");
  assert.match(SRC, /new deps\.Observer\(\(entries\) => \{ intersecting = entries\.some\(\(e\) => e\.isIntersecting\); publish\(\); \}\)\.observe\(root\);/);
  assert.match(SRC, /deps\.doc\.addEventListener\("visibilitychange", publish\);/);
  assert.ok(!/set(Interval|Timeout)|requestAnimationFrame/.test(SRC), "on events only, never a timer");
  assert.ok(!SRC.includes('"panes"') && !SRC.includes("romp:") && !SRC.includes("postMessage") && !SRC.includes("parent"), "the frame's own visibility: no shell message, no parent read");
  assert.match(SRC, /Observer: typeof IntersectionObserver === "undefined" \? null : IntersectionObserver,/, "the browser deps: the page's own observer, or none");
  // the kernel's side: the chat page carries the shim, and the shim reads the word before its probe
  assert.match(KERNEL, /_shim\("chat", v, caps=READY_GATE_CAP\)/, "the chat page carries the pane shim");
  const shim = /function paneHidden\(\)\{[^\n]*/.exec(KERNEL)?.[0] ?? "";
  assert.match(shim, /\(window\.parent!==window&&\(window\.innerWidth===0\|\|window\.innerHeight===0\)\)\|\|window\.__rompPaneHidden===true/, "the shim: the probe OR a published word of true (Firefox zeroes the viewport and stalls the observer; Chromium keeps the size and runs it)");
  assert.doesNotMatch(shim, /typeof window\.__rompPaneHidden==="boolean"\)return window\.__rompPaneHidden/, "never the word first: a stale word must not override a probe that says zero viewport");
  assert.match(KERNEL, /"body:not\(\.po-chat\) #chat-pane\{display:none\}/, "the desktop rail hides a toggled-off pane's WRAPPER by display:none (body loses po-chat), the case the probe misses after a first show");
  // the phone shell hides differently: the wrappers dissolve, and the iframe itself is display:none unless it carries
  // m-on, which the tab switch moves; the phone browser leg drives that mechanism
  assert.match(KERNEL, /"#chat-pane,#fleet-pane,#feed-pane,#waiting-pane,#files-pane,#tl-pane\{display:contents!important\}"/, "the phone shell dissolves the pane wrappers: the desktop rule hides nothing there");
  assert.match(KERNEL, /"iframe\{position:static;display:none;width:100%;height:100%;border:0\}"/, "...and hides the iframes themselves");
  assert.match(KERNEL, /"#f-chat\.m-on,#f-fleet\.m-on,#f-feed\.m-on,#f-waiting\.m-on,#f-files\.m-on\{display:block\}"/, "...except the one tab carrying m-on");
  assert.match(KERNEL, /function show\(p\)\{[^\n]*for\(var k in F\)F\[k\]\.classList\.toggle\('m-on',k===p\);/, "the tab switch moves m-on across the iframes: what the phone leg drives");
});

// ── the browser legs ──────────────────────────────────────────────────────────────────────────────
// The shell hides a pane two ways, and a leg drives each with the kernel's own CSS, lifted verbatim:
//   desktop: the rail takes po-<pane> off the body, and `body:not(.po-chat) #chat-pane{display:none}` hides the pane
//            WRAPPER (the iframe keeps its own display);
//   phone:   the media block forces the wrappers to display:contents (so that desktop rule hides nothing there), sets
//            every iframe display:none and shows the one carrying m-on, which show(p) moves on a tab switch.
// The phone rules sit inside `@media _MOBILE_MQ{...}` in kernel.py; the leg applies them unconditionally, since the
// test's viewport is a desktop's.
type Shell = "desktop" | "phone";
function kernelRule(rule: string, what: string): string {
  assert.ok(KERNEL.includes('"' + rule + '"'), what + " moved in kernel.py: re-anchor");
  return rule;
}
const DESKTOP_RULE = () => {
  const a = KERNEL.indexOf('"body:not(.po-chat) #chat-pane{display:none}');
  assert.ok(a > 0, "the desktop rail's pane-hiding rule moved in kernel.py: re-anchor");
  return KERNEL.slice(a + 1, KERNEL.indexOf('"', a + 1));      // the whole rule: every pane's po-* clause
};
const PHONE_RULES = () =>
  kernelRule("#chat-pane,#fleet-pane,#feed-pane,#waiting-pane,#files-pane,#tl-pane{display:contents!important}", "the phone shell's wrapper rule") +
  kernelRule("iframe{position:static;display:none;width:100%;height:100%;border:0}", "the phone shell's iframe rule") +
  kernelRule("#f-chat.m-on,#f-fleet.m-on,#f-feed.m-on,#f-waiting.m-on,#f-files.m-on{display:block}", "the phone shell's m-on rule");
// the shim's paneHidden(), the one line, verbatim (no backslash in it, so Python served it as written)
function shimPaneHidden(): string {
  const line = /function paneHidden\(\)\{[^\n]*/.exec(KERNEL)?.[0] ?? "";
  assert.ok(line.endsWith("}}"), "the shim's paneHidden is one line: re-anchor");
  assert.ok(!line.includes("\\"), "the shim line carries a backslash: Python would alter it: slice differently");
  return line;
}
// the chat body, from the extension's skeleton (the kernel's _chat_body is its hand-ported twin, pinned elsewhere)
function chatSkeleton(): string {
  const at = SKEL.indexOf("export function chatBody(");
  const open = SKEL.indexOf("return `", at) + "return `".length;
  const close = SKEL.indexOf("`;", open);
  assert.ok(at > 0 && open > at && close > open, "page-skeleton.ts chatBody moved: re-anchor");
  return SKEL.slice(open, close).replace("${attachTitle}", "Attach a file");
}
// the publisher as render.ts installs it, bundled from the worktree's module (the source pin above holds the call)
function bundleInstall(): string {
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    stdin: { contents: 'import { watchChatVisibility, browserChatVisibilityDeps } from "./chat-visibility";\nwatchChatVisibility(document.body, browserChatVisibilityDeps());\n', resolveDir: UI, loader: "ts", sourcefile: "chat-visibility-install.ts" },
    bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], logLevel: "silent",
  });
  return r.outputFiles[0].text;
}
// Both shells carry the desktop rule (the real stylesheet does; on the phone the media block overrides it), show the
// chat first (po-chat on the body, m-on on its iframe: the phone's default tab, which no desktop rule reads) and hold
// two panes the shell never shows. The test's iframe size comes last so the phone rule's 100% sizing yields to it.
const SHELL_HTML = (shell: Shell) => `<!DOCTYPE html><html><head><meta charset=utf-8>
<style>${DESKTOP_RULE()}${shell === "phone" ? PHONE_RULES() : ".pane{display:inline-block;vertical-align:top}"}iframe{width:600px;height:400px;border:0}</style></head>
<body class="po-chat">
<div id=chat-pane class=pane><iframe id=f-chat class=m-on src=/chat></iframe></div>
<div id=feed-pane class=pane><iframe id=f-feed src=/chat></iframe></div>
<div id=waiting-pane class=pane><iframe id=f-waiting src=/chat></iframe></div>
</body></html>`;
const CHAT_HTML = () => `<!DOCTYPE html><html><head><meta charset=utf-8></head><body>${chatSkeleton()}
<script>${shimPaneHidden()}</script>
<script src=/dist/chat-visibility.js></script></body></html>`;

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

const SHELLS: Array<[Shell, string]> = [
  ["desktop", "the desktop rail's rule (the pane wrapper goes display:none)"],
  ["phone", "the phone shell's tab switch (the iframe itself goes display:none as m-on moves)"],
];
for (const name of ["chromium", "firefox", "webkit"]) for (const [shell, how] of SHELLS) {
  test(`in ${name}, hidden by ${how}: the chat page hidden after a first show reads hidden (by the word where the iframe kept its size, by the probe where it went to zero); shown again, it reads shown; a pane hidden since load reads hidden`, async (t) => {
    if (!pw) { t.skip("playwright is not installed under vscode-extension; the browser legs need it (CI installs no browsers)"); return; }
    let browser: any;
    try { browser = await pw[name].launch(); }
    catch (e) { t.skip("no playwright " + name + " on this box; this leg needs it (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
    try {
      const errors: string[] = [];
      const install = bundleInstall();
      const page = await browser.newPage({ viewport: { width: 1000, height: 600 } });
      page.on("pageerror", (e: Error) => { errors.push(e.message); });
      await page.route("http://romp.test/**", (route: any) => {
        const u = new URL(route.request().url());
        if (u.pathname === "/shell") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: SHELL_HTML(shell) });
        if (u.pathname === "/chat") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: CHAT_HTML() });
        if (u.pathname === "/dist/chat-visibility.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: install });
        return route.fulfill({ status: 404, body: "" });
      });
      await page.goto("http://romp.test/shell");
      // what the frame's shim would decide, and its inputs: the published word, the viewport, the probe alone
      const read = (id: string) => page.evaluate((fid: string) => {
        const w = (document.getElementById(fid) as HTMLIFrameElement).contentWindow as any;
        return { word: w.__rompPaneHidden, iw: w.innerWidth, ih: w.innerHeight, shim: w.paneHidden(),
                 probe: w.parent !== w && (w.innerWidth === 0 || w.innerHeight === 0),
                 body: !!w.document.getElementById("composer-input") };
      }, id);
      const wordIs = (id: string, v: boolean) => page.waitForFunction(([fid, want]: [string, boolean]) =>
        ((document.getElementById(fid) as HTMLIFrameElement).contentWindow as any).__rompPaneHidden === want, [id, v] as [string, boolean], { timeout: 10000 });
      const shimIs = (id: string, v: boolean) => page.waitForFunction(([fid, want]: [string, boolean]) =>
        ((document.getElementById(fid) as HTMLIFrameElement).contentWindow as any).paneHidden() === want, [id, v] as [string, boolean], { timeout: 10000 });
      const display = (id: string) => page.evaluate((i: string) => getComputedStyle(document.getElementById(i)!).display, id);
      // the shell's two switches, as the kernel makes them: the rail takes po-chat off the body; the phone's show(p)
      // sets data-tab and toggles m-on across the iframes (kernel.py: for(var k in F)F[k].classList.toggle('m-on',k===p))
      const tab = (p: string) => page.evaluate((want: string) => {
        document.body.setAttribute("data-tab", want);
        for (const f of Array.from(document.querySelectorAll("iframe"))) f.classList.toggle("m-on", f.id === "f-" + want);
      }, p);
      const hideChat = () => shell === "desktop" ? page.evaluate(() => document.body.classList.remove("po-chat")) : tab("feed");
      const showChat = () => shell === "desktop" ? page.evaluate(() => document.body.classList.add("po-chat")) : tab("chat");
      // shown first (po-chat on the body; the chat is the phone's default tab): the observer's first word says on screen
      await wordIs("f-chat", false);
      let s = await read("f-chat");
      assert.equal(s.body, true, "the chat skeleton is up in the frame");
      assert.ok(s.iw > 0 && s.ih > 0, "a shown frame has a viewport");
      assert.equal(s.shim, false, "shown: the shim says not hidden");
      // the shell hides the chat, its way
      await hideChat();
      await shimIs("f-chat", true);
      s = await read("f-chat");
      if (shell === "desktop") {
        assert.equal(await display("chat-pane"), "none", "the rail's rule: the pane wrapper is display:none");
      } else {
        assert.equal(await display("chat-pane"), "contents", "the phone shell dissolves the wrapper: the rail's rule hides nothing here");
        assert.equal(await display("f-chat"), "none", "...the iframe itself is display:none once m-on moved off it");
        assert.equal(await display("f-feed"), "block", "...and the feed tab shows with no po-feed on the body: the media block's !important beats the rail's rule");
      }
      assert.equal(s.shim, true, "the shim reads hidden: no banner from a pane nobody can see");
      // which measure carried it is the browser's business, and the two disagree: Chromium keeps the hidden
      // iframe's size (the probe is blind, the observer fires, the word says hidden); Firefox zeroes the viewport
      // (the probe is right) and does not run the observer (the word stays at its last verdict). The union is
      // right in both, and the boolean-first read of round 2 would have raised from the hidden pane in Firefox.
      if (s.iw > 0 || s.ih > 0) {
        assert.equal(s.probe, false, "a frame that kept its size: the probe alone would read it as shown");
        assert.equal(s.word, true, "...so the published word is what carries the verdict (" + name + ")");
      } else {
        assert.equal(s.probe, true, "a frame whose viewport went to zero: the probe carries the verdict (" + name + ")");
      }
      // shown again: no resize for a same-size re-show, so the observer's callback (or the viewport) is the event
      await showChat();
      await shimIs("f-chat", false);
      s = await read("f-chat");
      assert.equal(s.shim, false, "re-shown: the shim raises again if genuinely stale");
      assert.ok(s.iw > 0 && s.ih > 0);
      // a chat frame hidden SINCE LOAD (a pane the shell never showed: no po-waiting on the body, no m-on on its
      // iframe): hidden either way, by the word or the probe
      const c = await read("f-waiting");
      assert.equal(c.shim, true, "hidden since load reads hidden: the word if the observer spoke, the probe (zero viewport) otherwise");
      assert.equal(c.probe, true, "a never-shown iframe has a zero viewport in every browser: the probe is right at boot, which is why nothing need be published before the observer speaks");
      assert.ok(c.word === true || c.word === undefined, "the word, if any, agrees: " + JSON.stringify(c));
      assert.deepEqual(errors, [], "no script error in any frame");
    } finally { await browser.close(); }
  });
}

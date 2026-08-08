// The file viewer in the FEED pane (the user 2026-08-08). Clicking a file path in the chat used to post
// `openFile`, which the kernel served by running an opener on ITS OWN machine — the wrong screen when the
// dashboard is read from another device, and nothing at all on a kernel with no desktop, because the
// opener was macOS-only. The bytes have to reach the browser, so the click now routes to a viewer fed by
// the same /file route the image thumbnails use. Source pins (no jsdom for these modules) + executed
// replicas of the pure helpers.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const web = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const VIEW = web("file-view.ts");
const RENDER = web("render.ts");
const FEED = web("feed.ts");
const FEED_CSS = web("feed.css");

test("openPath routes by HOST: the feed viewer on the web, the editor in VS Code", () => {
  assert.match(RENDER, /function openPath\(path: string, sid\?: string \| null\): void/);
  // web dashboard inside the shell → relay up; the chat and the feed are different documents
  assert.match(RENDER, /const web = location\.protocol === "http:" \|\| location\.protocol === "https:";/);
  assert.match(RENDER, /if \(web && window\.parent !== window\) \{/);
  assert.match(RENDER, /window\.parent\.postMessage\(\{ romp: "viewFile", path, sid: sid \|\| activeId \|\| null \}, "\*"\);/);
  // everything else (VS Code, or /chat opened standalone with no shell) keeps the kernel-side opener
  assert.match(RENDER, /vscodeApi\.postMessage\(sid \? \{ type: "openFile", path, id: sid \} : \{ type: "openFile", path \}\);/);
});

test("every file-link surface in the chat goes through openPath — no direct openFile posts left", () => {
  for (const call of [/openPath\(path\);/, /openPath\(open, relative \? activeId : null\);/,
                      /openPath\(p, id \|\| null\);/]) assert.match(RENDER, call);
  // the ONLY openFile postMessage left in render.ts is openPath's own fallback branch
  assert.equal((RENDER.match(/type: "openFile"/g) || []).length, 2,
               "both remaining mentions are the two arms of openPath's fallback");
});

test("the shell relays chat → feed, and restores a pane it had to turn on", () => {
  const KERNEL = fs.readFileSync(path.resolve(process.cwd(), "..", "kernel", "kernel.py"), "utf8");
  assert.match(KERNEL, /if\(m\.romp==='viewFile'\)\{var vf=document\.getElementById\('f-feed'\);/);
  // a feed pane the user had toggled OFF is turned on for the viewer and put back on close — the viewer
  // must never silently rearrange the layout they chose
  assert.match(KERNEL, /window\.__rompFeedWasOff=true;/);
  assert.match(KERNEL, /if\(m\.romp==='viewFileClosed'&&window\.__rompFeedWasOff\)\{window\.__rompFeedWasOff=false;/);
  assert.match(KERNEL, /window\.__rompMobileTab&&window\.__rompMobileTab\('feed'\)/, "phone: one pane at a time");
  assert.match(KERNEL, /window\.__rompMobileTab=show;/, "…which means the mobile switcher has to be exposed");
});

test("the viewer is a singleton that fills the pane and always tells the shell when it closes", () => {
  assert.match(VIEW, /document\.getElementById\("romp-fileview"\)\?\.remove\(\);/, "re-opening replaces, never stacks");
  assert.match(VIEW, /window\.parent\.postMessage\(\{ romp: "viewFileClosed" \}, "\*"\);/);
  // Esc and ✕ are the same close path, so the shell's restore can't be skipped by one of them
  assert.match(VIEW, /close\.addEventListener\("click", closeFileView\);/);
  assert.match(VIEW, /if \(e\.key !== "Escape" \|\| !document\.getElementById\("romp-fileview"\)\) return;/);
  assert.match(FEED, /initFileView\(\);/, "the feed boots the listener");
  assert.match(FEED_CSS, /\.fileview \{ position: fixed; inset: 0;/);
});

test("it waits with the romp loader and fails with the kernel's own words, never a blank pane", () => {
  assert.match(VIEW, /romp-swirl-glyph\.svg/, "loading-state rule: the swirl goes up first");
  assert.match(VIEW, /fileview-dot/);
  // a 404/413/415 body IS the explanation (the 413 names the size and the cap) — show it, don't swallow it
  assert.match(VIEW, /if \(!r\.ok\) return r\.text\(\)\.then\(\(t\) => \{ throw new Error\(t \|\| \("HTTP " \+ r\.status\)\); \}\);/);
  assert.match(VIEW, /const why = el\("div", "fileview-err"\);/);
  // a reply that lands after the user closed the viewer paints nothing
  assert.match(VIEW, /if \(!document\.getElementById\("romp-fileview"\)\) return;/);
});

test("it reuses fileUrl, so a REMOTE session's file is relayed from the host that owns it", () => {
  assert.match(VIEW, /import \{ fileUrl \} from "\.\/preview";/);
  assert.match(VIEW, /fetch\(fileUrl\(path, sid\), \{ cache: "no-store" \}\)/);
});

// executed: the extension→language map must never GUESS. highlightAuto on a config file or a log picks a
// language at random and paints it as information the file does not contain.
test("langFor maps known extensions and returns null rather than guessing", () => {
  const LANG: Record<string, string> = {
    py: "python", pyi: "python", js: "javascript", jsx: "javascript", mjs: "javascript",
    cjs: "javascript", ts: "typescript", tsx: "typescript", json: "json", jsonc: "json",
    yaml: "yaml", yml: "yaml", sh: "bash", bash: "bash", zsh: "bash", bats: "bash",
    html: "xml", htm: "xml", xml: "xml", svg: "xml", vue: "xml", css: "css", scss: "css",
    md: "markdown", markdown: "markdown", diff: "diff", patch: "diff",
  };
  const langFor = (p: string): string | null => LANG[p.slice(p.lastIndexOf(".") + 1).toLowerCase()] || null;
  assert.equal(langFor("kernel/kernel.py"), "python");
  assert.equal(langFor("ui/webview/render.TS"), "typescript");   // case-insensitive
  assert.equal(langFor("notes.md"), "markdown");
  for (const p of ["server.log", "Makefile", "a.conf", "data.csv", "x.rs"]) {
    assert.equal(langFor(p), null, p + " has no registered grammar → plain, not a guess");
  }
  assert.doesNotMatch(VIEW, /hljs\.highlightAuto\(/, "auto-detection is what this map exists to avoid");
});

// executed: the gutter is a SIBLING of the code, so selecting the code copies it without line numbers
test("the line gutter numbers every line and drops a trailing newline's phantom line", () => {
  const lines = (text: string): string[] => {
    const l = text.split("\n");
    if (l.length && l[l.length - 1] === "") l.pop();
    return l;
  };
  assert.deepEqual(lines("a\nb\nc\n").length, 3, "a trailing newline is not a fourth line");
  assert.deepEqual(lines("a\nb\nc").length, 3);
  assert.deepEqual(lines(""), []);
  assert.match(VIEW, /gutter\.textContent = lines\.map\(\(_, i\) => String\(i \+ 1\)\)\.join\("\\n"\);/);
  assert.match(VIEW, /wrap\.appendChild\(gutter\); wrap\.appendChild\(pre\);/, "sibling, not inside the pre");
  assert.match(FEED_CSS, /\.fileview-gutter \{[\s\S]*?user-select: none;/);
});

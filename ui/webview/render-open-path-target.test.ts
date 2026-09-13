// The chat's producer half of an open-at target (Slice 6 of plans/markdown-viewer.md, item 4): render.ts's openPath
// and openLinkedPath, lifted out of the source, transpiled and executed with the chat's module state handed in. A
// todo link that named a target after its path (`docs/report.md#results`, `docs/report.md:12`; path-links.ts
// `targetSuffix`) reaches openLinkedPath as data-frag or data-line; it reads them through path-links.ts linkTarget and
// hands the target to openPath, which carries it to the viewer here through openFileClick, to a pane's viewer as the
// relay's `at`, and to the VS Code host as `line` when it is a line (the host's openFileInEditor reads that field,
// 1-based, and has no equivalent for a heading, which posts nothing extra). The rest of openPath's routing (fileLinkRoute,
// the identity the relay carries, the gesture) is pinned by file-view.test.ts and pdf-new-tab.test.ts and is not
// re-pinned here. Synthetic values: the notes-api world, a placeholder session id.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { linkTarget } from "./path-links";
import { hideEdges, staysEnumerable } from "../test-dom-shim";   // the window stand-in's parent is an edge: hidden, so a failing dump never walks the cycle

const EXT = process.cwd();                                        // npm test runs in vscode-extension
const requireCjs = createRequire(path.join(EXT, "package.json"));   // esbuild from the extension, wherever this bundle was written
const UI = path.resolve(EXT, "..", "ui", "webview");
const RENDER = fs.readFileSync(path.join(UI, "render.ts"), "utf8");
const SID = "11111111-2222-3333-4444-555555555555";
const REL = "docs/report.md";

function transpile(src: string): string { return requireCjs("esbuild").transformSync(src, { loader: "ts", target: "es2020" }).code; }
/** A verbatim function of render.ts, from its `function name(` line to its closing brace. */
function lift(name: string): string {
  const at = RENDER.indexOf("\nfunction " + name + "(");
  const end = RENDER.indexOf("\n}\n", at);
  assert.ok(at > 0 && end > at, "anchor not found: render.ts's " + name + " moved; re-anchor");
  return RENDER.slice(at, end + 3);
}
type Posted = Record<string, unknown>;
type World = {
  protocol: string; route: string; framed: boolean; sid?: string | null;
};
/** openPath as render.ts spells it, over a world: the page's protocol, the route fileLinkRoute would answer, whether a shell
 *  frames the page. Returns what reached the host (vscodeApi), the shell (window.parent) and openFileClick. */
function openPathIn(w: World) {
  const hostPosts: Posted[] = [], shellPosts: Posted[] = [], clicks: unknown[][] = [];
  const code = transpile(lift("openPath") + "\nreturn openPath;");
  const fn = new Function("vscodeApi", "location", "activeId", "fileLinkRoute", "settings", "window", "panesOn", "sessions", "tabMeta", "openFileClick", code) as
    (...a: unknown[]) => (path: string, sid?: string | null, ev?: unknown, at?: unknown) => void;
  const parent = { postMessage: (m: Posted, _o: string) => { shellPosts.push(m); } };
  const win: Record<string, unknown> = { parent: w.framed ? parent : null };
  if (!w.framed) win.parent = win;                                 // unframed: window.parent === window
  hideEdges(win);                                                  // parent non-enumerable (ui/test-dom-shim.ts): a failing assertion over the window dumps primitives, never the cycle
  const openPath = fn(
    { postMessage: (m: Posted) => { hostPosts.push(m); } }, { protocol: w.protocol }, SID,
    () => w.route, { fileLinkPane: w.route }, win, { files: true },
    new Map([[SID, { name: "api", color: { bg: "#123456", fg: "#ffffff" } }]]), new Map(),
    (...a: unknown[]) => { clicks.push(a); },
  );
  return { openPath, hostPosts, shellPosts, clicks };
}

test("on the web, the route here: the target reaches openFileClick as its fifth argument, after the relay slot", () => {
  const w = openPathIn({ protocol: "http:", route: "here", framed: false });
  const ev = { type: "click" };
  w.openPath(REL, SID, ev, { heading: "results" });
  assert.deepEqual(w.clicks, [[ev, REL, SID, undefined, { heading: "results" }]], "no relay for here; the target rides to the viewer in this document");
  w.openPath(REL, null, null, null);
  assert.deepEqual(w.clicks[1], [null, REL, SID, undefined, null], "no session named: the active tab's; no target: null");
  assert.deepEqual(w.hostPosts, [], "the web never posts the host's openFile");
});

test("on the web, the route pane: the relay openFileClick is handed posts the shell's viewFile with `at`, whatever the target", () => {
  const w = openPathIn({ protocol: "https:", route: "pane", framed: true });
  for (const at of [{ heading: "results" }, { line: 12 }, null]) {
    w.clicks.length = 0; w.shellPosts.length = 0;
    w.openPath(REL, SID, null, at);
    const [, p, to, relay, passed] = w.clicks[0] as [unknown, string, string, (p: string, s: string | null, a: unknown) => void, unknown];
    assert.equal(typeof relay, "function", "a pane route hands openFileClick the relay");
    assert.deepEqual(passed, at, "…and the target beside it, so openFileClick can hand the relay the target of the click it lets through");
    relay(p, to, passed);
    assert.deepEqual(w.shellPosts, [{ romp: "viewFile", path: REL, sid: SID, pane: "pane", identity: { name: "api", color: { bg: "#123456", fg: "#ffffff" } }, at }],
      "the message the shell forwards (kernel.py copies `at`; files.ts reads it through readAt): " + JSON.stringify(at));
  }
});

test("in VS Code: a line target posts `line` on openFile (the host's editor arm reads it); a heading posts nothing extra", () => {
  const w = openPathIn({ protocol: "vscode-webview:", route: "here", framed: false });
  w.openPath(REL, SID, null, { line: 12 });
  w.openPath(REL, SID, null, { heading: "results" });
  w.openPath(REL, null, null, null);
  w.openPath(REL, null, null, { line: 3 });
  assert.deepEqual(w.hostPosts, [
    { type: "openFile", path: REL, id: SID, line: 12 },
    { type: "openFile", path: REL, id: SID },
    { type: "openFile", path: REL },
    { type: "openFile", path: REL, line: 3 },
  ]);
  assert.deepEqual(w.clicks, [], "the host branch never runs openFileClick");
  // at source: the arm reads `line` alone, 1-based as the host takes it
  assert.match(RENDER, /const m: Record<string, unknown> = sid \? \{ type: "openFile", path, id: sid \} : \{ type: "openFile", path \};\n\s*if \(at && "line" in at\) m\.line = at\.line;\n\s*vscodeApi\.postMessage\(m\);/);
  assert.match(fs.readFileSync(path.resolve(EXT, "src", "extension.ts"), "utf8"), /if \(m\.type === "openFile" && m\.path\) \{ openFileInEditor\(String\(m\.path\), m\.line\); return; \}/, "the host's arm the post feeds");
});

test("openLinkedPath reads the link's target through linkTarget and hands it to openPath with the click", () => {
  const opened: unknown[][] = [];
  const code = transpile(lift("openLinkedPath") + "\nreturn openLinkedPath;");
  const fn = new Function("openPath", "activeId", "linkTarget", code) as (...a: unknown[]) => (a: unknown, e?: unknown) => void;
  const openLinkedPath = fn((...a: unknown[]) => { opened.push(a); }, SID, linkTarget);
  const ev = { type: "click" };
  openLinkedPath({ dataset: { path: REL, rel: "1", sid: SID, frag: "results" } }, ev);
  openLinkedPath({ dataset: { path: REL, rel: "1", sid: SID, line: "12" } }, ev);
  openLinkedPath({ dataset: { path: "/repo/notes-api/docs/report.md" } }, null);   // a file:// URI's span: absolute, no session, no target
  assert.deepEqual(opened, [
    [REL, SID, ev, { heading: "results" }],
    [REL, SID, ev, { line: 12 }],
    ["/repo/notes-api/docs/report.md", null, null, null],
  ]);
  assert.match(RENDER, /openPath\(open, relative \? \(sid \?\? activeId\) : null, e, linkTarget\(a\)\);/);
  assert.match(RENDER, /openFileClick\(ev, path, to, relay, at\);/);
  assert.match(RENDER, /identity: meta && meta\.name \? \{ name: meta\.name, color: meta\.color \?\? null \} : null, at: a \}, "\*"\);/);
});

// ── the window stand-in is a projection (ui/test-dom-shim.ts): a failing assertion over it dumps primitives, never a cycle through parent ──
test("the window stand-in enumerates its primitives alone: parent is hidden by hideEdges, so a failing dump never walks the self-cycle", () => {
  const win: Record<string, unknown> = { parent: null, framed: false }; win.parent = win; hideEdges(win);
  assert.ok(Object.keys(win).every((k) => staysEnumerable(win[k])), "the stand-in keeps an enumerable edge: " + Object.keys(win).join(","));
  assert.equal(win.parent, win, "the edge is still there, read through the property");
});

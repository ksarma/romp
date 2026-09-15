// Where a FOLDER click opens: the folder shown under the chat, the system-context card's Directory row and a
// tab menu's Browse files walk the file link's own ladder (file-route.ts browseRoute): an open Files pane
// takes the listing whatever the gear says, a closed one only when the gear's "File links open in" names it,
// and otherwise, framed, the listing opens in the FEED pane's browser (this fork's rule, the user 2026-09-06:
// never over the chat while a shell frames it); only standalone /chat, where neither surface exists, opens it
// in place. VS Code keeps its own folder opener. Six legs. The ladder itself, executed (pure). The chat's end
// (render.ts browseRouteNow, openBrowse, the tab menu's sub-line and the host contract the chat hands its
// browser instance), lifted and run over stubs (the open-path-exec.test.ts idiom). The pane's end (files.ts's
// host contract for the same browser), lifted and run the same way. The wiring at source (render.ts,
// file-browse.ts, files.ts, feed.ts, the sheets, docs/guide.md). The shell's browse arms EXTRACTED from
// kernel.py and run against a shimmed window/document (the files.test.ts idiom). The browser module's host
// contract (file-browse.ts BrowseHost), run for real over a DOM stand-in in this file's own process: the module
// binds its host once per document, so these cases cannot share filebrowse.test.ts's instance. And the Files pane
// under the real shell script in Firefox and Chromium: the relay lists the folder in the pane, a picked file
// opens over the listing with a way back, Escape peels one layer at a time, and the pane tells the shell only
// when nothing is left up. The browser legs skip, and say why, without the playwright package or a browser it
// can launch. Synthetic values only: the notes-api demo world, placeholder session ids.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { browseRoute, fileLinkRoute, type BrowseRoute } from "./file-route";
import { asIdentity } from "./files-recent";
import { hideEdges } from "../test-dom-shim";

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

const SID = "11111111-2222-3333-4444-555555555555";       // a session on the tab strip, named and coloured
const SID_TAB = "11111111-2222-3333-4444-666666666666";   // a session the tab set names but the session list does not
const SID_NONE = "11111111-2222-3333-4444-777777777777";  // a sid neither names
const COLOR = { bg: "#123456", fg: "#ffffff" };
const IDENTITY = { name: "web", color: COLOR };
const SETTINGS: unknown[] = ["chat", "feed", "pane", undefined, null, "purple", 42];   // the gear's three values (this fork's "feed"), an unset store, foreign values
const GRID: Array<[unknown, boolean, boolean]> = [];
for (const s of SETTINGS) for (const framed of [true, false]) for (const open of [true, false]) GRID.push([s, framed, open]);
const label = (s: unknown, framed: boolean, open: boolean) => `setting=${String(s)}, framed=${framed}, filesOpen=${open}`;

// ── the ladder, executed ──────────────────────────────────────────────────────────────────────────

test("browseRoute: VS Code keeps the editor's own folder opener, whatever the setting or the panes say", () => {
  for (const [s, framed, open] of GRID) assert.equal(browseRoute(false, s, framed, open), "editor", label(s, framed, open));
});

test("browseRoute: web dashboard, Files pane OPEN: the listing opens in the Files pane, whatever the setting", () => {
  for (const s of SETTINGS) assert.equal(browseRoute(true, s, true, true), "pane", `setting=${String(s)}`);
});

test("browseRoute: web dashboard, Files pane CLOSED: the setting's Files pane brings it forward; everything else lands on the feed, never over the chat", () => {
  assert.equal(browseRoute(true, "pane", true, false), "pane", "the setting names the Files pane: it comes forward for the listing, as it does for a file");
  assert.equal(browseRoute(true, "feed", true, false), "feed");
  assert.equal(browseRoute(true, "chat", true, false), "feed", "the DEFAULT: a file would open over the chat; a listing goes to the feed pane's browser");
  assert.equal(browseRoute(true, undefined, true, false), "feed", "an unset store reads as the default");
  assert.equal(browseRoute(true, "purple", true, false), "feed", "a foreign stored value falls to the default");
});

test("browseRoute: no shell (standalone /chat): the browser over this document, whatever the setting or the cache", () => {
  for (const s of SETTINGS) for (const open of [true, false]) assert.equal(browseRoute(true, s, false, open), "here", label(s, false, open));
});

test("browseRoute is fileLinkRoute with exactly one substitution: a framed 'here' becomes 'feed'", () => {
  for (const setting of SETTINGS) for (const framed of [true, false]) for (const open of [true, false]) {
    const file = fileLinkRoute(setting, framed, open);
    const want = framed && file === "here" ? "feed" : file;
    assert.equal(browseRoute(true, setting, framed, open), want, `setting=${String(setting)}, framed=${framed}, filesOpen=${open}`);
  }
});

test("browseRoute names four targets: the editor, the Files pane, the feed pane's browser and this document", () => {
  const seen = new Set<BrowseRoute>();
  for (const web of [true, false]) for (const [s, framed, open] of GRID) seen.add(browseRoute(web, s, framed, open));
  assert.deepEqual([...seen].sort(), ["editor", "feed", "here", "pane"]);
});

// ── the chat's end, executed ──────────────────────────────────────────────────────────────────────
// render.ts from browseRouteNow through the chat's initFileBrowse call (openBrowse between them), lifted whole
// and run with the real ladder under it and stubs for the rest: the shell (window.parent), the settings, the
// pane cache, the session list and tab set the identity is looked up in, the chat's own browser (openFileBrowse)
// and the browser module's init, which records the host contract the chat hands it.
function sliceOf(src: string, startAnchor: string, endAnchor: string, name: string): string {
  const a = src.indexOf(startAnchor), b = src.indexOf(endAnchor, a);
  assert.ok(a > 0 && b > a, name + ": anchors not found (" + startAnchor.slice(0, 40) + " / " + endAnchor.slice(0, 40) + "); re-anchor");
  return src.slice(a, b);
}
const ts = (code: string): string => requireCjs("esbuild").transformSync(code, { loader: "ts" }).code;

type Host = { shellRestore?: boolean; onRelay?: (m: { path: string; sid?: unknown; identity?: unknown }) => void; openFile?: (path: string, sid: string | null) => void } | undefined;
type ChatHooks = {
  up: Array<[unknown, string]>; here: Array<[string, string | null]>; vs: unknown[];
  settings: { fileLinkPane: unknown }; framed: boolean; protocol: string; activeId: string | null; panes: Record<string, boolean>;
  host: Host; poster: ((m: unknown) => void) | null;
};
type ChatApi = { openBrowse: (p: string, sid?: string | null) => void; browseRouteNow: () => BrowseRoute; setPanes: (on: Record<string, boolean>) => void };
function liftChat(over: Partial<ChatHooks> = {}): { H: ChatHooks; api: ChatApi } {
  const H: ChatHooks = { up: [], here: [], vs: [], settings: { fileLinkPane: "chat" }, framed: true, protocol: "http:", activeId: SID, panes: {}, host: undefined, poster: null, ...over };
  const code = ts(sliceOf(RENDER, "function browseRouteNow(): BrowseRoute {", "\n// A clickable file name that opens the real file", "browseRouteNow through the chat's browser host"));
  const prelude = `
    const H = HOOKS;
    const location = { get protocol() { return H.protocol; } };
    const window = {};
    window.parent = H.framed ? { postMessage: (m, origin) => { H.up.push([m, origin]); } } : window;
    const settings = H.settings;
    let panesOn = H.panes;
    let activeId = H.activeId;
    const sessions = new Map([[${JSON.stringify(SID)}, { id: ${JSON.stringify(SID)}, name: "web", color: ${JSON.stringify(COLOR)} }]]);
    const tabMeta = new Map([[${JSON.stringify(SID_TAB)}, { name: "api", color: null }]]);
    const vscodeApi = { postMessage: (m) => { H.vs.push(m); } };
    const openFileBrowse = (p, sid) => { H.here.push([p, sid]); };
    const initFileBrowse = (poster, host) => { H.poster = poster; H.host = host; };
  `;
  const epilogue = "return { openBrowse, browseRouteNow, setPanes: (on) => { panesOn = on; } };";
  const api = (new Function("HOOKS", "browseRoute", prelude + code + epilogue) as (h: ChatHooks, r: typeof browseRoute) => ChatApi)(H, browseRoute);
  return { H, api };
}
const relayedUp = (H: ChatHooks) => H.up.map(([m]) => m);

test("the chat's end, executed: with the Files pane on screen a folder click posts the pane route up with the session's looked-up identity, and the chat's own browser stays shut", () => {
  const { H, api } = liftChat({ panes: { chat: true, feed: true, files: true } });
  api.openBrowse("/repo/notes-api", SID);
  assert.deepEqual(H.up, [[{ romp: "browseFiles", path: "/repo/notes-api", sid: SID, pane: "pane", identity: IDENTITY }, "*"]],
    "one message up, naming the target pane, with the name and colour the tab strip shows for the session");
  assert.deepEqual(H.here, [], "nothing opened over the chat");
  // the identity is LOOKED UP, never invented: a session only the tab set names sends its name with no colour; a
  // sid neither list names sends null, and the pane falls to the kernel's stub; no sid means the active session
  api.openBrowse("/repo/notes-api/src", SID_TAB);
  assert.deepEqual(relayedUp(H)[1], { romp: "browseFiles", path: "/repo/notes-api/src", sid: SID_TAB, pane: "pane", identity: { name: "api", color: null } });
  api.openBrowse("/repo/notes-api/docs", SID_NONE);
  assert.deepEqual(relayedUp(H)[2], { romp: "browseFiles", path: "/repo/notes-api/docs", sid: SID_NONE, pane: "pane", identity: null });
  api.openBrowse("", null);
  assert.deepEqual(relayedUp(H)[3], { romp: "browseFiles", path: ".", sid: SID, pane: "pane", identity: IDENTITY }, "no path is the session's cwd, no sid the active session");
  assert.deepEqual(H.here, []);
});

test("the chat's end, executed: with the pane off the setting decides, read at the click: the Files pane when it names it, else the feed pane's browser (the default, a foreign value and the feed setting alike, this fork's rule: framed, never over the chat); the pane coming on screen overrides it", () => {
  const { H, api } = liftChat({ panes: { chat: true, feed: true, files: false } });
  api.openBrowse("/repo/notes-api", SID);
  assert.deepEqual(relayedUp(H), [{ romp: "browseFiles", path: "/repo/notes-api", sid: SID, pane: "feed", identity: IDENTITY }], "the default: handed up for the feed pane's browser, naming that pane");
  assert.deepEqual(H.here, [], "nothing over the chat while a shell frames it");
  H.settings.fileLinkPane = "pane";
  api.openBrowse("/repo/notes-api", SID);
  assert.deepEqual(relayedUp(H)[1], { romp: "browseFiles", path: "/repo/notes-api", sid: SID, pane: "pane", identity: IDENTITY }, "the setting names the pane: handed up, the shell brings it forward");
  H.settings.fileLinkPane = "purple";
  api.openBrowse("", SID);
  assert.deepEqual(relayedUp(H)[2], { romp: "browseFiles", path: ".", sid: SID, pane: "feed", identity: IDENTITY }, "a foreign stored value is the default (the feed), and no path is the cwd");
  H.settings.fileLinkPane = "feed";
  api.openBrowse("/repo/notes-api/docs", SID);
  assert.deepEqual(relayedUp(H)[3], { romp: "browseFiles", path: "/repo/notes-api/docs", sid: SID, pane: "feed", identity: IDENTITY }, "the feed setting names the feed");
  api.setPanes({ chat: true, files: true });
  api.openBrowse("/repo/notes-api", SID);
  assert.equal((relayedUp(H)[4] as { pane: string }).pane, "pane", "on screen: the pane takes it whatever the setting says");
  assert.deepEqual(H.here, []);
});

test("the chat's end, executed: no shell (standalone /chat) never relays; VS Code opens nothing here at all, the folder link's own act keeps the editor's opener", () => {
  const solo = liftChat({ framed: false, settings: { fileLinkPane: "pane" }, panes: { files: true } });
  solo.api.openBrowse("/repo/notes-api", SID);
  assert.deepEqual(solo.H.here, [["/repo/notes-api", SID]], "unframed: over this document, whatever the cache or setting says");
  assert.deepEqual(solo.H.up, []);
  const code = liftChat({ protocol: "vscode-webview:", settings: { fileLinkPane: "pane" }, panes: { files: true } });
  code.api.openBrowse("/repo/notes-api", SID);
  assert.deepEqual([code.H.here, code.H.up, code.H.vs], [[], [], []], "the webview cannot reach the kernel origin; asFolderLink gave the click openFolder instead");
});

test("the chat's end, executed: the host the chat hands its browser owes the shell no close notice, and a viewer's directory link relayed to this window walks the same ladder", () => {
  const { H, api } = liftChat({ panes: { files: true } });
  assert.ok(H.host, "initFileBrowse was called with a host");
  assert.equal(H.host!.shellRestore, false, "the chat never asks the shell to lift a pane for its browser, so its close restores nothing");
  assert.equal(typeof H.host!.onRelay, "function");
  assert.equal(H.host!.openFile, undefined, "a pick in the chat's own listing opens the viewer here, the default");
  // a chat-hosted viewer's directory link posts browseFiles to its own window (file-view.ts); the host's relay
  // routes it exactly as a folder click: the Files pane while it is on screen, in place otherwise
  H.host!.onRelay!({ path: "/repo/notes-api/src", sid: SID });
  assert.deepEqual(relayedUp(H), [{ romp: "browseFiles", path: "/repo/notes-api/src", sid: SID, pane: "pane", identity: IDENTITY }]);
  assert.deepEqual(H.here, []);
  api.setPanes({});
  H.host!.onRelay!({ path: "/repo/notes-api/src", sid: 42 });
  assert.deepEqual(relayedUp(H)[1], { romp: "browseFiles", path: "/repo/notes-api/src", sid: SID, pane: "feed", identity: IDENTITY }, "pane off, the default setting: the feed pane's browser (this fork's rule); a sid that is not a string reads as the active session");
  assert.deepEqual(H.here, [], "never in place while a shell frames the chat");
  // the poster is the chat's socket, as before
  H.poster!({ type: "listDir", path: "/repo/notes-api", reqId: 1 });
  assert.deepEqual(H.vs, [{ type: "listDir", path: "/repo/notes-api", reqId: 1 }]);
});

test("browseRouteNow reads the cache and the setting at the call, so the tab menu's sub-line and the click cannot disagree", () => {
  const { H, api } = liftChat({ panes: { files: true } });
  assert.equal(api.browseRouteNow(), "pane");
  api.setPanes({ chat: true });
  assert.equal(api.browseRouteNow(), "feed", "the pane off under the default setting: the feed pane's browser (framed)");
  H.settings.fileLinkPane = "pane";
  assert.equal(api.browseRouteNow(), "pane");
  H.protocol = "vscode-webview:";
  assert.equal(api.browseRouteNow(), "editor", "the host is read at the call too");
});

test("the tab menu's sub-line, executed: it names where Browse files will land, from the reader the click uses", () => {
  const code = ts(sliceOf(RENDER, "const where = browseRouteNow();", "bodyEl.appendChild(sb);", "the tab menu's Browse files sub-line"));
  const subLine = (where: BrowseRoute): string =>
    (new Function("browseRouteNow", "el", code + "return sb.textContent;") as (r: () => BrowseRoute, e: (t: string, c?: string) => { textContent: string }) => string)(() => where, () => ({ textContent: "" }));
  assert.equal(subLine("pane"), "the session's working tree, in the Files pane");
  assert.equal(subLine("feed"), "the session's working tree, in the feed pane");
  assert.equal(subLine("here"), "the session's working tree, in a viewer over this chat");
});

// ── the pane's end, executed ──────────────────────────────────────────────────────────────────────
// files.ts's initFileBrowse call (the contract the Files pane hands the same browser), lifted whole and run with
// the real asIdentity under it and stubs for the rest: the identity cache, the browser's open (which reads the
// cache at the call, as the viewer's chip does later), the pane's own open (openHere) and the browser's init.
type PaneHooks = { vs: unknown[]; listed: Array<[string, string | null, unknown]>; opened: Array<[string, string | null, unknown]>; host: Host; poster: ((m: unknown) => void) | null };
function liftPane(): { H: PaneHooks; identities: Map<string, unknown> } {
  const H: PaneHooks = { vs: [], listed: [], opened: [], host: undefined, poster: null };
  const code = ts(sliceOf(FILES, "initFileBrowse((m) => vscodeApi?.postMessage(m), {", "\n\n// re-open rows", "files.ts's browser host"));
  const prelude = `
    const H = HOOKS;
    const vscodeApi = { postMessage: (m) => { H.vs.push(m); } };
    const identities = new Map();
    const openFileBrowse = (p, sid) => { H.listed.push([p, sid, sid ? (identities.get(sid) ?? null) : null]); };
    const openHere = (p, sid, id) => { H.opened.push([p, sid, id]); };
    const initFileBrowse = (poster, host) => { H.poster = poster; H.host = host; };
  `;
  const identities = (new Function("HOOKS", "asIdentity", prelude + code + "return identities;") as (h: PaneHooks, a: typeof asIdentity) => Map<string, unknown>)(H, asIdentity);
  return { H, identities };
}

test("the pane's end, executed: the Files pane's host caches the relayed identity before the listing opens, asks the listing for the session, routes a pick through its own open, and owes the shell no close notice", () => {
  const { H, identities } = liftPane();
  assert.ok(H.host, "initFileBrowse was called with a host");
  assert.equal(H.host!.shellRestore, false, "the pane stays up: its close tells the shell nothing");
  assert.equal(typeof H.host!.onRelay, "function");
  assert.equal(typeof H.host!.openFile, "function");
  // the shell's forward: the identity is cached FIRST, so the listing (and the chip of a file picked from it) sees it
  H.host!.onRelay!({ path: "/repo/notes-api", sid: SID, identity: IDENTITY });
  assert.deepEqual(H.listed, [["/repo/notes-api", SID, IDENTITY]], "the listing asked for the session, its identity already in the cache");
  assert.deepEqual(identities.get(SID), IDENTITY);
  // no identity (the chat found no name for the sid): nothing cached, the pane falls to the kernel's stub; no path is the cwd
  H.host!.onRelay!({ path: "", sid: SID_NONE, identity: null });
  assert.deepEqual(H.listed[1], [".", SID_NONE, null]);
  assert.equal(identities.has(SID_NONE), false);
  // a sid that is not a string reads as none; a malformed identity is never cached
  H.host!.onRelay!({ path: "/repo", sid: 42, identity: IDENTITY });
  assert.deepEqual(H.listed[2], ["/repo", null, null]);
  H.host!.onRelay!({ path: "/repo", sid: SID_TAB, identity: { name: "" } });
  assert.deepEqual(H.listed[3], ["/repo", SID_TAB, null]);
  assert.deepEqual([...identities.keys()], [SID], "one identity cached, the well-formed one");
  // a pick from the listing goes through the pane's own open, which records Recent and resolves the chip from the cache
  assert.deepEqual(H.opened, []);
  H.host!.openFile!("/repo/notes-api/README.md", SID);
  assert.deepEqual(H.opened, [["/repo/notes-api/README.md", SID, null]], "openHere, with no identity of the pick's own");
  // the poster is the pane's socket
  H.poster!({ type: "listDir", path: "/repo", reqId: 1 });
  assert.deepEqual(H.vs, [{ type: "listDir", path: "/repo", reqId: 1 }]);
});

// ── the wiring at source ──────────────────────────────────────────────────────────────────────────

test("render.ts: the import; browseRouteNow beside openBrowse, outside the openPath slice open-path-exec.test.ts executes; the three arms (editor, here, the relay naming its pane); the sub-line", () => {
  assert.match(RENDER, /^import \{ fileLinkRoute, browseRoute, type BrowseRoute \} from "\.\/file-route";/m);
  const panesAt = RENDER.indexOf("let panesOn: Record<string, boolean> = {};");
  const midAt = RENDER.indexOf("\n// A middle-click on a path pill is the same open", panesAt);
  const nowAt = RENDER.indexOf("function browseRouteNow(): BrowseRoute {");
  const openAt = RENDER.indexOf("function openBrowse(path: string, sid?: string | null): void {");
  assert.ok(panesAt > 0 && midAt > panesAt, "open-path-exec.test.ts's anchors stand");
  assert.ok(nowAt > midAt && openAt > nowAt, "browseRouteNow sits after the middle-click block, right before openBrowse");
  assert.doesNotMatch(RENDER.slice(panesAt, midAt), /browseRoute/, "the executed openPath slice names no browse route");
  assert.match(RENDER, /const route = browseRouteNow\(\);\n\s*if \(route === "editor"\) return;/);
  assert.match(RENDER, /if \(route === "here"\) \{ openFileBrowse\(path \|\| "\.", to\); return; \}/, "in place only for 'here'");
  assert.match(RENDER, /window\.parent\.postMessage\(\{ romp: "browseFiles", path: path \|\| "\.", sid: to, pane: route,/, "the relayed routes post up, each naming its target (the Files pane, or this fork's feed pane)");
  assert.equal((RENDER.match(/romp: "browseFiles"/g) || []).length, 1, "one post site");
  assert.match(RENDER, /initFileBrowse\(\(m\) => vscodeApi\?\.postMessage\(m\), \{\n\s*shellRestore: false,\n\s*onRelay: \(m\) => openBrowse\(m\.path, typeof m\.sid === "string" \? m\.sid : null\),\n\}\);/,
    "the chat's own browser instance, with the chat's contract");
  assert.match(RENDER, /const where = browseRouteNow\(\);/);
  assert.match(RENDER, /sb\.textContent = "the session's working tree, " \+ \(where === "pane" \? "in the Files pane" : where === "feed" \? "in the feed pane" : "in a viewer over this chat"\);/,
    "the sub-line names where Browse files will land, the feed pane among the three");
  assert.equal((RENDER.match(/= browseRouteNow\(\);/g) || []).length, 2, "two readers: the click and the menu's sub-line");
});

test("file-browse.ts: the host contract; the close notice gated to the feed's contract; the relay guard before the default open; the pick under the gesture reader", () => {
  assert.match(BROWSE, /export type BrowseAsk = \{ path: string; sid\?: unknown; identity\?: unknown \};/);
  assert.match(BROWSE, /export type BrowseHost = \{/);
  assert.match(BROWSE, /onRelay\?: \(m: BrowseAsk\) => void;/);
  assert.match(BROWSE, /openFile\?: \(path: string, sid: string \| null\) => void;/);
  assert.match(BROWSE, /shellRestore\?: boolean;/);
  assert.match(BROWSE, /^let shellRestore = true;/m);
  assert.match(BROWSE, /^let openPick: \(\(path: string, sid: string \| null\) => void\) \| null = null;/m);
  assert.match(BROWSE, /function tellShellClosed\(\): void \{\n  if \(!shellRestore\) return;/, "the gate is the first line: no close notice from a document that owes none");
  assert.match(BROWSE, /export function initFileBrowse\(poster: \(m: Record<string, unknown>\) => void, host: BrowseHost = \{\}\): void \{/);
  assert.match(BROWSE, /shellRestore = host\.shellRestore !== false;/, "the feed's contract by default");
  assert.match(BROWSE, /openPick = host\.openFile \?\? null;/);
  const branch = BROWSE.split('if (m.romp === "browseFiles" && typeof m.path === "string") {')[1].split("} else if")[0];
  const guard = "if (host.onRelay) { host.onRelay({ path: m.path, sid: m.sid, identity: m.identity }); return; }";
  assert.ok(branch.indexOf(guard) >= 0, "the relay guard is present");
  assert.ok(branch.indexOf('openFileBrowse(m.path || "."') >= 0, "the default open is present");
  assert.ok(branch.indexOf(guard) < branch.indexOf('openFileBrowse(m.path || "."'), "a document's own contract takes the ask before the default open runs");
  // the host's open sits UNDER the gesture reader: a Cmd/Ctrl- or middle-clicked PDF row still takes its own tab in every host
  assert.match(BROWSE, /if \(row\.dataset\.act === "file"\) \{ openFileClick\(ev, p, curSid, openPick \?\? undefined\); return; \}/);
  // this fork's OPEN notice (fork PR 280, review round 2): the shell arms a phone's way back on this ack, never at its relay, so a
  // relay the feed stands down (the viewer's veto) leaves nothing cocked. The same gate: the feed's contract only
  const told = BROWSE.split("function tellShellOpened(): void {")[1].split("\n}")[0];
  assert.match(told, /^\n\s*if \(!shellRestore\) return;/, "the gate is the first statement of the open notice too");
  assert.match(told, /window\.parent\.postMessage\(\{ romp: "browseOpened" \}, "\*"\);/);
  const open = BROWSE.split("export function openFileBrowse")[1].split("\nfunction unbuild")[0];
  assert.match(open, /\n  ask\(path\);\n  tellShellOpened\(\);\n\}\n/, "the ack follows the ask: the last thing a real open does");
  assert.equal((BROWSE.match(/tellShellOpened\(\);/g) || []).length, 1, "one call site, the real open");
});

test("files.ts hosts the listing as a column under its own contract; feed.ts keeps the default", () => {
  assert.match(FILES, /^import \{ initFileBrowse, openFileBrowse \} from "\.\/file-browse";/m);
  assert.match(FILES, /initFileBrowse\(\(m\) => vscodeApi\?\.postMessage\(m\), \{\n\s*shellRestore: false,/, "the pane stays up: its close owes the shell nothing");
  assert.match(FILES, /onRelay: \(m\) => \{\n\s*const sid = typeof m\.sid === "string" \? m\.sid : null;\n\s*const id = asIdentity\(m\.identity\);\n\s*if \(sid && id\) identities\.set\(sid, id\);\n\s*openFileBrowse\(m\.path \|\| "\.", sid\);\n\s*\},/,
    "the identity is cached before the listing opens, so a picked file's chip names its session");
  assert.match(FILES, /openFile: \(p, sid, at\) => openHere\(p, sid, null, null, at\),/, "a pick enters Recent through the pane's own open, the link's target handed on (this fork's Slice 6 of plans/markdown-viewer.md)");
  assert.equal((FILES.match(/rememberRecent\(/g) || []).length, 1, "one writer of the recent list, inside openHere");
  assert.match(FILES, /a file or folder clicked in the chat opens here/, "the empty state says so");
  assert.match(FEED, /initFileBrowse\(\(m\) => vscodeApi\?\.postMessage\(m\)\);/, "the feed's browser keeps the default contract: its close still restores the feed pane");
  // the listing fills the pane: the files page loads the chat sheet, whose #romp-filebrowse is the fixed inset-0 backdrop, and
  // files-pane.css un-dresses the centered card for the column exactly as it does the viewer's (the fork's sheet pins)
  assert.match(KERNEL, /<link href=\/dist\/styles\.css\?v=%d rel=stylesheet>/);
  assert.match(CHAT_CSS, /#romp-filebrowse \{ position: fixed; inset: 0; z-index: 890;/);
  const PANE = read("files-pane.css");
  assert.match(PANE, /body\.fileview-pane #romp-filebrowse\{background:none\}/, "no dim behind a listing that is the pane");
  assert.match(PANE, /body\.fileview-pane \.filebrowse\{width:100%;height:100%;border:0;border-radius:0;box-shadow:none\}/, "the card takes the whole box");
  assert.match(PANE, /body\.fileview-pane \.fileview\{width:100%;height:100%;border:0;border-radius:0;box-shadow:none\}/, "the same un-dress the viewer gets");
});

test("the viewer's title bar wraps in every sheet: the path and its directory link keep their width, and the action row wraps inside the pane or the card", () => {
  // the row of action buttons alone outgrows a 480px pane. The pane variant wrapped first (review 2026-09-07, two rounds:
  // the directory link at 0px, then a phone-wide pane clipping the close button off an overflow:hidden viewer, with no
  // backdrop to tap and no Escape on a phone); the text-size control's three buttons then clipped the MODAL's row below
  // about 600px the same way, so the wrap moved into the base rules of styles.css / feed.css (the parity pair) and
  // files-pane.css adds nothing to the bar. Measured in the browser legs below at 320 and 360px, and in
  // file-view-text-size.test.ts at 380-600px in both modals.
  const pane = read("files-pane.css").replace(/\/\*[\s\S]*?\*\//g, "");
  assert.doesNotMatch(pane, /\.fileview-bar|\.fileview-acts|\.fileview-name/, "the pane sheet leaves the bar to the base rules");
  for (const css of [CHAT_CSS, read("feed.css")]) {
    assert.match(css, /\.fileview-bar \{ flex: 0 0 auto; display: flex; flex-wrap: wrap; align-items: center; gap: 6px 10px; min-width: 0;/);
    assert.match(css, /\.fileview-bar \.fileview-name \{ flex: 1 1 0; min-width: 12em; \}/);
    assert.match(css, /\.fileview-bar \.fileview-acts \{ flex: 0 1 auto; min-width: 0; margin-left: auto; flex-wrap: wrap; justify-content: flex-end; \}/);
    // scoped to the BAR (round 2): the browser's action row (.fb-bar, one line at every width) and the Files pane's
    // Recent rows wear the two classes outside any bar, and keep the plain flex they had before the control
    assert.match(css, /\n\.fileview-acts \{ flex: 0 0 auto; display: flex; align-items: center; gap: 6px; \}/);
    assert.match(css, /\n\.fileview-name \{ flex: 1 1 auto; min-width: 0;/);
    assert.doesNotMatch(css, /\.fb-bar \{[^}]*flex-wrap/, "the browser's bar never wraps");
  }
});

test("the guide names the folder link and where its listing opens", () => {
  assert.match(GUIDE, /The folder under the chat \(the session's working directory\) opens a\s+listing of that folder by the same rule/);
});

// ── the shell's browse arms, executed ─────────────────────────────────────────────────────────────
// EXTRACTED from kernel.py's landing shell (the files.test.ts idiom): from the viewer's Files-pane arm, which leads the
// files arms since the 2026-09-15 pull-in (#1305 as landed), to the end of the listener, run against a shimmed window/document. A `pane:'pane'` browse drives the Files branch and
// never touches the feed's flags; 'feed' (or no pane, an older sender) takes the feed route exactly as before.
// The stop is the comment right after the listener's close: the dashboard-id minting that followed the listener
// moved to the head script (upstream #1127, taken in the 2026-09-09 fold) and left this comment in its place.
function arms(): (w: unknown, d: unknown, m: unknown) => void {
  const start = KERNEL.indexOf("if(m.romp==='viewFile'&&m.pane==='pane'){");
  const stop = KERNEL.indexOf("// The dashboard's one id", start);
  assert.ok(start >= 0 && stop > start, "arm anchors not found: re-anchor this extraction");
  let js = KERNEL.slice(start, stop).trimEnd();
  assert.ok(js.endsWith("}});"));
  js = js.slice(0, -3);
  return new Function("window", "document", "m", js) as (w: unknown, d: unknown, m: unknown) => void;
}
// a shell to send messages through: desktop by default; `mobile` answers __rompMobileOn true with `tab` showing;
// `feedOn` is the po-feed class (the feed pane on screen). data-tab follows every switch, the arms' and the
// person's alike (the shell's show() sets it); `tap` is the person's own tap on the tab bar, which no arm sees.
function shell(opts: { mobile?: boolean; tab?: string; feedOn?: boolean } = {}) {
  const run = arms();
  const toggles: Array<[string, boolean]> = [], tabs: string[] = [];
  const posted: Record<string, unknown[]> = { "f-files": [], "f-feed": [], "f-chat": [] };
  let feedOn = opts.feedOn !== false;
  let tab = opts.tab ?? "chat";
  const win: any = { __rompPaneToggle: (p: string, on: boolean) => { toggles.push([p, on]); if (p === "feed") feedOn = on; },
    __rompMobileTab: (t: string) => { tabs.push(t); tab = t; }, __rompMobileOn: () => !!opts.mobile };
  const doc = {
    body: { classList: { contains: (c: string) => c === "po-feed" && feedOn },
            getAttribute: (a: string) => (a === "data-tab" ? tab : null) },
    // a loaded page: the pane arms forward at once (a page still loading would hold the message for its load event)
    getElementById: (id: string) => (id in posted ? { contentWindow: { postMessage: (x: unknown) => posted[id].push(x) }, contentDocument: { readyState: "complete" } } : null),
  };
  const send = (m: unknown) => { run(win, doc, m); return { toggles, tabs, posted, from: win.__rompFilesTabFrom, wasOff: win.__rompFeedWasOff, pend: win.__rompFeedWasOffViewPend }; };
  return { send, win, tap: (t: string) => { tab = t; }, tab: () => tab };
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

test("shell, executed: pane:'feed' (and no pane) take the feed route: lift, remember, put back on browseClosed; desktop switches no tab", () => {
  for (const m of [{ romp: "browseFiles", pane: "feed", path: ".", sid: SID, identity: IDENTITY }, { romp: "browseFiles", path: ".", sid: SID }]) {
    const desk = shell();
    const on = desk.send(m);
    assert.deepEqual(on.posted["f-feed"], [{ romp: "browseFiles", path: ".", sid: SID }], "path + sid only; the feed resolves its own identity");
    assert.deepEqual(on.posted["f-files"], []);
    // DESKTOP: no mobile tab switch (review 2026-09-07: the unconditional show() persisted romp-mobile-tab=feed, and a
    // later narrow layout booted on the Feed tab), and nothing to remember, at the relay or at the feed's ack
    assert.deepEqual(on.tabs, []);
    assert.equal(desk.win.__rompFeedTabFrom, undefined);
    assert.deepEqual(desk.send({ romp: "browseOpened" }).tabs, []);
    assert.equal(desk.win.__rompFeedTabFrom, undefined);
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

test("shell, executed: on a phone the feed route switches to the Feed tab and the listing's close puts the person back, once", () => {
  // the review's medium finding (2026-09-07): with the default setting a phone's folder click showed the listing on
  // the Feed tab and its close left the person on the feed cards; the pane route already returned (filesViewerClosed)
  // The switch and the memory ride the feed's browseOpened ACK, not the relay (review round 2, 2026-09-07: armed at
  // the relay, the memory outlived a dirty-edit veto in the feed; the veto scenario is the test below)
  const phone = shell({ mobile: true, tab: "chat" });
  const relayed = phone.send({ romp: "browseFiles", pane: "feed", path: ".", sid: SID });
  assert.deepEqual(relayed.tabs, [], "the relay itself switches nothing: the feed has opened nothing yet");
  assert.equal(phone.win.__rompFeedTabFrom, undefined, "and remembers nothing");
  const opened = phone.send({ romp: "browseOpened" });
  assert.deepEqual(opened.tabs, ["feed"], "the feed's ack: the listing is up, the Feed tab comes forward");
  assert.equal(phone.win.__rompFeedTabFrom, "chat", "the tab the click came from is remembered");
  const closed = phone.send({ romp: "browseClosed" });
  assert.deepEqual(closed.tabs, ["feed", "chat"], "the listing closed: back to the remembered tab");
  assert.equal(phone.win.__rompFeedTabFrom, null, "the memory is consumed");
  assert.deepEqual(closed.toggles, [], "the feed pane was on: nothing to put back");
  assert.deepEqual(phone.send({ romp: "browseClosed" }).tabs, ["feed", "chat"], "a second close switches nothing");
  // the feed's own dir-link route (no browseFiles through the shell): its ack finds the Feed tab showing, so it
  // remembers nothing, and its close moves no tab
  const own = shell({ mobile: true, tab: "feed" });
  assert.deepEqual(own.send({ romp: "browseOpened" }).tabs, []);
  assert.equal(own.win.__rompFeedTabFrom, undefined);
  assert.deepEqual(own.send({ romp: "browseClosed" }).tabs, []);
  // already on the Feed tab when the relay lands: nothing to switch, nothing to remember
  const already = shell({ mobile: true, tab: "feed" });
  already.send({ romp: "browseFiles", pane: "feed", path: ".", sid: SID });
  assert.deepEqual(already.send({ romp: "browseOpened" }).tabs, []);
  assert.equal(already.win.__rompFeedTabFrom, undefined);
  // the feed pane OFF on a phone: the tab return and the pane restore ride the one close
  const off = shell({ mobile: true, tab: "chat", feedOn: false });
  off.send({ romp: "browseFiles", pane: "feed", path: ".", sid: SID });
  off.send({ romp: "browseOpened" });
  const back = off.send({ romp: "browseClosed" });
  assert.deepEqual(back.toggles, [["feed", true], ["feed", false]]);
  assert.deepEqual(back.tabs, ["feed", "chat"]);
  // a rotation to desktop between open and close: the memory is dropped, never replayed later
  const rotated = shell({ mobile: true, tab: "chat" });
  rotated.send({ romp: "browseFiles", pane: "feed", path: ".", sid: SID });
  rotated.send({ romp: "browseOpened" });
  rotated.win.__rompMobileOn = () => false;
  assert.deepEqual(rotated.send({ romp: "browseClosed" }).tabs, ["feed"]);
  assert.equal(rotated.win.__rompFeedTabFrom, null);
  // the Files route keeps its own memory: a pane browse then a feed close touch different slots
  const mixed = shell({ mobile: true, tab: "chat" });
  mixed.send({ romp: "browseFiles", pane: "pane", path: ".", sid: SID });
  assert.equal(mixed.win.__rompFilesTabFrom, "chat"); assert.equal(mixed.win.__rompFeedTabFrom, undefined);
  assert.deepEqual(mixed.send({ romp: "browseClosed" }).tabs, ["files"], "a feed close moves nothing for a listing the Files pane holds");
  // an older shell without __rompMobileOn: no arm throws, and nothing switches
  const bare = shell(); delete bare.win.__rompMobileOn;
  assert.deepEqual(bare.send({ romp: "browseFiles", pane: "feed", path: ".", sid: SID }).tabs, []);
  assert.deepEqual(bare.send({ romp: "browseOpened" }).tabs, []);
  assert.deepEqual(bare.send({ romp: "browseClosed" }).tabs, []);
});

test("shell, executed: a relay the feed stood down (the dirty-edit veto) arms nothing, so a listing the feed later opens for itself closes without a tab switch", () => {
  // review round 2 (2026-09-07): the memory was armed at the relay and only browseClosed consumed it. A vetoed relay
  // (file-browse.ts unbuild: no listDir, no notice of any kind) left it cocked, and the feed's next self-opened
  // listing, a viewer's directory link, replayed the stale tab at its close, moving the person off the Feed tab they
  // had chosen. Armed on the feed's browseOpened ack now, which a veto never sends, and which a self-opened
  // listing sends with the Feed tab already showing.
  const phone = shell({ mobile: true, tab: "chat" });
  phone.send({ romp: "browseFiles", pane: "feed", path: ".", sid: SID });   // relayed, then vetoed in the feed: no ack follows
  assert.equal(phone.tab(), "chat", "the click stood down whole: the person stays where they clicked");
  assert.equal(phone.win.__rompFeedTabFrom, undefined, "nothing remembered for a listing that never opened");
  phone.tap("feed");                                                        // later, on their own, to the feed
  const own = phone.send({ romp: "browseOpened" });                         // a viewer's directory link there: the feed's own listing
  assert.deepEqual(own.tabs, [], "its ack finds the Feed tab showing: nothing to switch, nothing to remember");
  assert.equal(phone.win.__rompFeedTabFrom, undefined);
  const closed = phone.send({ romp: "browseClosed" });
  assert.deepEqual(closed.tabs, [], "the self-opened listing's close moves nothing: no stale tab replays");
  assert.equal(phone.tab(), "feed", "still on the tab they chose");
  // the same relay answered with OK instead: the ack arms the return trip and the close makes it
  const ok = shell({ mobile: true, tab: "chat" });
  ok.send({ romp: "browseFiles", pane: "feed", path: ".", sid: SID });
  ok.send({ romp: "browseOpened" });
  assert.equal(ok.tab(), "feed"); assert.equal(ok.win.__rompFeedTabFrom, "chat");
  ok.send({ romp: "browseClosed" });
  assert.equal(ok.tab(), "chat");
});

// ── the browser module's host contract, executed over a DOM stand-in ───────────────────────────────
// The real file-browse.ts and file-view.ts (the pick goes through the viewer's gesture reader) against a DOM
// stand-in (the filebrowse.test.ts idiom: a tree, attributes and dataset, bubbling events, a small selector
// matcher; every node through the shared shim's hideEdges), bound ONCE to a host with every field set. Synthetic fixtures: a notes-api world, placeholder sids.
class Ev {
  target: El | null = null;
  currentTarget: El | null = null;
  defaultPrevented = false;
  stopped = false;
  ctrlKey: boolean; metaKey: boolean; button: number; key: string;
  constructor(public type: string, init: { ctrlKey?: boolean; metaKey?: boolean; button?: number; key?: string } = {}) {
    this.ctrlKey = !!init.ctrlKey; this.metaKey = !!init.metaKey; this.button = init.button ?? 0; this.key = init.key ?? "";
    hideEdges(this);   // the target edges hide (ui/test-dom-shim.ts): a failing assertion dumps the event, never the tree
  }
  preventDefault(): void { this.defaultPrevented = true; }
  stopPropagation(): void { this.stopped = true; }
}
type Listener = (ev: Ev) => void;
type Part = { tag: string; id: string; classes: string[]; attrs: Array<[string, string | null]>; known: boolean };
const kebab = (k: string) => k.replace(/[A-Z]/g, (c) => "-" + c.toLowerCase());
/** One compound selector (`tag#id.class[attr="v"]`); a shape the matcher does not know fits nothing. */
function part(s: string): Part {
  const m = /^([a-zA-Z][\w-]*|\*)?(#[\w-]+)?((?:\.[\w-]+)*)((?:\[[^\]]+\])*)$/.exec(s);
  if (!m) return { tag: "", id: "", classes: [], attrs: [], known: false };
  const attrs: Array<[string, string | null]> = [];
  let known = true;
  for (const a of m[4].match(/\[[^\]]+\]/g) || []) {
    const am = /^\[([\w-]+)(?:="([^"]*)")?\]$/.exec(a);
    if (am) attrs.push([am[1], am[2] ?? null]); else known = false;
  }
  return { tag: (m[1] || "").toLowerCase(), id: m[2] ? m[2].slice(1) : "", classes: (m[3].match(/\.[\w-]+/g) || []).map((c) => c.slice(1)), attrs, known };
}
class El {
  parentNode: El | null = null;
  childNodes: Array<El | string> = [];
  title = ""; hidden = false; type = ""; disabled = false; tabIndex = -1; innerHTML = ""; scrollTop = 0;
  href = ""; target = ""; rel = ""; spellcheck = true; value = ""; src = ""; alt = ""; download = "";
  style: Record<string, string> = {};
  onclick: ((ev: Ev) => void) | null = null;
  private attrs = new Map<string, string>();
  private listeners: Array<{ type: string; fn: Listener; once: boolean }> = [];
  constructor(public tagName: string) { hideEdges(this); }   // the node enumerates its primitives alone (ui/test-dom-shim.ts)
  get id(): string { return this.attrs.get("id") ?? ""; }
  set id(v: string) { this.attrs.set("id", v); }
  get className(): string { return this.attrs.get("class") ?? ""; }
  set className(v: string) { this.attrs.set("class", v.trim()); }
  private get classes(): string[] { return this.className.split(/\s+/).filter(Boolean); }
  classList = {
    add: (...c: string[]) => { const s = new Set(this.classes); for (const x of c) s.add(x); this.className = [...s].join(" "); },
    remove: (...c: string[]) => { const s = new Set(this.classes); for (const x of c) s.delete(x); this.className = [...s].join(" "); },
    toggle: (c: string, on?: boolean): boolean => { const want = on ?? !this.classes.includes(c); if (want) this.classList.add(c); else this.classList.remove(c); return want; },
    contains: (c: string) => this.classes.includes(c),
  };
  dataset: Record<string, string | undefined> = new Proxy({} as Record<string, string | undefined>, {
    get: (_, k) => this.attrs.get("data-" + kebab(String(k))),
    set: (_, k, v) => { this.attrs.set("data-" + kebab(String(k)), String(v)); return true; },
    has: (_, k) => this.attrs.has("data-" + kebab(String(k))),
    deleteProperty: (_, k) => { this.attrs.delete("data-" + kebab(String(k))); return true; },
  });
  get textContent(): string { return this.childNodes.map((c) => (typeof c === "string" ? c : c.textContent)).join(""); }
  set textContent(v: string) { this.replaceChildren(...(v === "" ? [] : [v])); }
  get children(): El[] { return this.childNodes.filter((c): c is El => c instanceof El); }
  get isConnected(): boolean { let n: El = this; while (n.parentNode) n = n.parentNode; return n === docBody; }
  private adopt(c: El | string): void { if (c instanceof El) { c.remove(); c.parentNode = this; } }
  appendChild<T extends El>(c: T): T { this.adopt(c); this.childNodes.push(c); return c; }
  append(...cs: Array<El | string>): void { for (const c of cs) { this.adopt(c); this.childNodes.push(c); } }
  prepend(...cs: Array<El | string>): void { for (const c of cs) this.adopt(c); this.childNodes.unshift(...cs); }
  insertBefore<T extends El>(c: T, ref: El | null): T {
    this.adopt(c);
    const i = ref ? this.childNodes.indexOf(ref) : -1;
    if (i < 0) this.childNodes.push(c); else this.childNodes.splice(i, 0, c);
    return c;
  }
  replaceChildren(...cs: Array<El | string>): void {
    for (const c of this.childNodes) if (c instanceof El) c.parentNode = null;
    this.childNodes = [];
    for (const c of cs) this.adopt(c);
    this.childNodes = [...cs];
  }
  remove(): void {
    const p = this.parentNode;
    if (!p) return;
    const i = p.childNodes.indexOf(this);
    if (i >= 0) p.childNodes.splice(i, 1);
    this.parentNode = null;
  }
  contains(n: El | null): boolean { for (let x: El | null = n; x; x = x.parentNode) if (x === this) return true; return false; }
  setAttribute(k: string, v: string): void { this.attrs.set(k, v); }
  removeAttribute(k: string): void { this.attrs.delete(k); }
  getAttribute(k: string): string | null { return this.attrs.get(k) ?? null; }
  hasAttribute(k: string): boolean { return this.attrs.has(k); }
  addEventListener(type: string, fn: Listener, opts?: boolean | { once?: boolean; passive?: boolean; capture?: boolean }): void {
    this.listeners.push({ type, fn, once: typeof opts === "object" && !!opts.once });
  }
  removeEventListener(type: string, fn: Listener): void { this.listeners = this.listeners.filter((l) => !(l.type === type && l.fn === fn)); }
  /** Bubble `ev` from this element to the root: each element's listeners in registration order, then its onclick for a click. */
  dispatchEvent(ev: Ev): boolean {
    ev.target = this;
    for (let n: El | null = this; n && !ev.stopped; n = n.parentNode) {
      ev.currentTarget = n;
      for (const l of n.listeners.slice()) {
        if (l.type !== ev.type) continue;
        if (l.once) n.listeners = n.listeners.filter((x) => x !== l);
        l.fn.call(n, ev);
      }
      if (ev.type === "click" && n.onclick) n.onclick(ev);
    }
    return !ev.defaultPrevented;
  }
  click(): void { this.dispatchEvent(new Ev("click")); }
  focus(): void { doc.activeElement = this; }
  scrollIntoView(): void { /* inert */ }
  getBoundingClientRect(): { left: number; top: number; width: number; height: number } { return { left: 0, top: 0, width: 100, height: 20 }; }
  private fits(p: Part): boolean {
    if (!p.known) return false;
    if (p.tag && p.tag !== "*" && p.tag !== this.tagName.toLowerCase()) return false;
    if (p.id && p.id !== this.id) return false;
    if (!p.classes.every((c) => this.classes.includes(c))) return false;
    return p.attrs.every(([a, v]) => this.attrs.has(a) && (v === null || this.attrs.get(a) === v));
  }
  matches(sel: string): boolean {
    return sel.split(",").some((group) => {
      const chain = group.trim().split(/\s+/).filter(Boolean).map(part);
      if (!chain.length || !this.fits(chain[chain.length - 1])) return false;
      let k = chain.length - 2;
      for (let a = this.parentNode; a && k >= 0; a = a.parentNode) if (a.fits(chain[k])) k--;
      return k < 0;
    });
  }
  closest(sel: string): El | null { for (let n: El | null = this; n; n = n.parentNode) if (n.matches(sel)) return n; return null; }
  querySelectorAll(sel: string): El[] {
    const out: El[] = [];
    const walk = (n: El) => { for (const c of n.children) { if (c.matches(sel)) out.push(c); walk(c); } };
    walk(this);
    return out;
  }
  querySelector(sel: string): El | null { return this.querySelectorAll(sel)[0] ?? null; }
}
const docBody = new El("body");
const docKeys: Listener[] = [];                  // the document's keydown handlers: the browser binds one per overlay
const doc = {
  body: docBody,
  head: new El("head"),
  activeElement: null as El | null,
  createElement: (tag: string) => new El(tag),
  createTextNode: (s: string) => s,
  getElementById: (id: string): El | null => docBody.querySelector("#" + id),
  querySelectorAll: (sel: string): El[] => docBody.querySelectorAll(sel),
  querySelector: (sel: string): El | null => docBody.querySelector(sel),
  addEventListener: (type: string, fn: Listener) => { if (type === "keydown") docKeys.push(fn); },
  removeEventListener: (type: string, fn: Listener) => { const i = docKeys.indexOf(fn); if (i >= 0) docKeys.splice(i, 1); },
};
const win: any = new EventTarget();
win.parent = win;                                // no shell unless a case installs one
win.confirm = () => true;
win.getSelection = () => null;
win.innerWidth = 1000; win.innerHeight = 600;
const opens: Array<[string, string]> = [];        // the browser tabs asked for (window.open)
let tabOpens = true;                             // whether the popup is allowed
win.open = (url: string, target: string) => { opens.push([url, target]); return tabOpens ? {} : null; };
win.postMessage = (m: unknown) => { win.dispatchEvent(new MessageEvent("message", { data: m })); };
(globalThis as any).window = win;
(globalThis as any).document = doc;
(globalThis as any).location = { protocol: "http:", origin: "http://TESTHOST:1", host: "TESTHOST:1" };   // the web: the PDF tab opener's gate (preview.ts canPreview)
const store = new Map<string, string>();
(globalThis as any).localStorage = {
  getItem: (k: string) => (store.has(k) ? store.get(k)! : null),
  setItem: (k: string, v: string) => { store.set(k, String(v)); },
  removeItem: (k: string) => { store.delete(k); },
};
(globalThis as any).fetch = () => Promise.resolve({ ok: false, status: 404, headers: { get: () => null }, text: () => Promise.resolve("") });

const ROOT = "/tmp/notes-api";
const SRC = ROOT + "/src";
const APP = SRC + "/app.py";
const PDF = SRC + "/spec.pdf";
const posted: Array<Record<string, unknown>> = [];   // what the browser posts to the kernel
const listDirs = () => posted.filter((m) => m.type === "listDir");
const relayed: unknown[] = [];                       // the asks the host's onRelay took
const picks: Array<[string, string | null]> = [];    // the files the host's openFile was handed
type Mods = { fb: typeof import("./file-browse") };
let bound: Promise<Mods> | null = null;
/** The browser module, bound once to a host with every field set (the Files pane's contract, with recorders). */
function browser(): Promise<Mods> {
  if (!bound) bound = import("./file-browse").then((fb) => {
    fb.initFileBrowse((m) => posted.push(m), {
      shellRestore: false,
      onRelay: (m) => { relayed.push(m); },
      openFile: (p, sid) => { picks.push([p, sid]); },
    });
    return { fb };
  });
  return bound;
}
function answerListing(base: string, names: string[]): void {
  const asks = listDirs();
  assert.ok(asks.length > 0, "a listDir was asked");
  const ask = asks[asks.length - 1];
  const entries = names.map((n) => (n.endsWith("/")
    ? { name: n.slice(0, -1), isDir: true, isLink: false, size: 0, mtime: 1700000000 }
    : { name: n, isDir: false, isLink: false, size: 12, mtime: 1700000000, viewable: true }));
  win.dispatchEvent(new MessageEvent("message", { data: {
    type: "dirListing", reqId: ask.reqId, host: "", sid: ask.sid, base, parent: base.slice(0, base.lastIndexOf("/")) || "/",
    entries, total: entries.length, truncated: false,
  } }));
}
const rowFor = (p: string) => { const r = doc.getElementById("fb-list")!.querySelectorAll("[data-act]").find((x) => x.dataset.path === p); assert.ok(r, "the row for " + p); return r!; };
async function reset(): Promise<void> {
  const { fb } = await browser();
  fb.closeFileBrowse();
  for (let i = 0; i < 2; i++) win.dispatchEvent(new MessageEvent("message", { data: { type: "dirListing", reqId: -1 } }));   // the latch, as filebrowse.test.ts resets it
  posted.length = 0; relayed.length = 0; picks.length = 0; opens.length = 0; tabOpens = true; win.parent = win;
}

test("BrowseHost, executed: a browseFiles message on this window is taken whole by the host's relay, and the browser does not open; a message with no path is not an ask", async (t) => {
  await browser();
  t.after(reset);
  win.postMessage({ romp: "browseFiles", path: "/repo/notes-api", sid: SID, identity: IDENTITY });
  assert.deepEqual(relayed, [{ path: "/repo/notes-api", sid: SID, identity: IDENTITY }], "the ask, whole");
  assert.equal(doc.getElementById("romp-filebrowse"), null, "no overlay: the host decides where the listing goes");
  assert.deepEqual(listDirs(), [], "no listing asked");
  win.postMessage({ romp: "browseFiles", sid: SID });
  win.postMessage({ romp: "browseFiles", path: 42 });
  win.postMessage({ type: "warn", text: "x" });
  assert.equal(relayed.length, 1, "the outer guard still filters");
});

test("BrowseHost, executed: a close under shellRestore false tells the shell nothing, though a shell is listening", async (t) => {
  const { fb } = await browser();
  const shell: unknown[] = [];
  win.parent = { postMessage: (m: unknown) => { shell.push(m); } };
  t.after(reset);
  fb.openFileBrowse(SRC, SID);
  answerListing(SRC, ["app.py", "lib/"]);
  assert.ok(doc.getElementById("romp-filebrowse"), "the overlay is up");
  assert.equal(listDirs().length, 1);
  fb.closeFileBrowse();
  assert.equal(doc.getElementById("romp-filebrowse"), null, "closed");
  assert.equal(docBody.classList.contains("filebrowse-open"), false);
  assert.deepEqual(shell, [], "no browseClosed: this document never asked the shell to lift a pane (the feed's default contract does post it, filebrowse.test.ts)");
  // and the Escape path closes the same way
  fb.openFileBrowse(SRC, SID);
  answerListing(SRC, ["app.py"]);
  for (const k of docKeys.slice()) k(new Ev("keydown", { key: "Escape" }));
  assert.equal(doc.getElementById("romp-filebrowse"), null);
  assert.deepEqual(shell, []);
});

test("BrowseHost, executed: a plain click on a file row goes to the host's openFile; a modified click on a PDF row takes the browser's own tab first, a blocked tab falls to the host; Enter follows the active row; a folder row navigates", async (t) => {
  const { fb } = await browser();
  t.after(reset);
  fb.openFileBrowse(SRC, SID);
  answerListing(SRC, ["app.py", "spec.pdf", "lib/"]);
  rowFor(APP).click();
  assert.deepEqual(picks, [[APP, SID]], "the host's open, with the listing's session");
  assert.equal(doc.getElementById("romp-fileview"), null, "no viewer built here: the host owns the open");
  assert.deepEqual(opens, [], "a plain click asks for no tab");
  // the gesture reader sits ABOVE the host's open: a Cmd-click on a PDF row is the browser's own tab, whatever the host
  rowFor(PDF).dispatchEvent(new Ev("click", { metaKey: true }));
  assert.equal(opens.length, 1, "one tab asked for");
  assert.match(opens[0][0], /\/file\?path=%2Ftmp%2Fnotes-api%2Fsrc%2Fspec\.pdf/);
  assert.equal(opens[0][1], "_blank");
  assert.equal(picks.length, 1, "the tab took it: the host was not asked");
  // the popup blocked: the host's open, so the file is never unreachable
  tabOpens = false;
  rowFor(PDF).dispatchEvent(new Ev("click", { ctrlKey: true }));
  assert.equal(opens.length, 2);
  assert.deepEqual(picks[1], [PDF, SID], "falls through to the host");
  // a modified click on a NON-PDF is not the tab opener's business: straight to the host
  rowFor(APP).dispatchEvent(new Ev("click", { metaKey: true }));
  assert.equal(opens.length, 2, "no tab asked for a .py file");
  assert.deepEqual(picks[2], [APP, SID]);
  // Enter acts on the active row through the same door
  rowFor(APP).classList.add("active");
  for (const k of docKeys.slice()) k(new Ev("keydown", { key: "Enter" }));
  assert.deepEqual(picks[3], [APP, SID], "Enter on the active row");
  assert.equal(picks.length, 4);
  // a folder row is a navigation: another listing asked, the host not involved
  const before = listDirs().length;
  rowFor(SRC + "/lib").click();
  assert.equal(listDirs().length, before + 1, "one more listing asked");
  assert.equal(listDirs()[before].path, SRC + "/lib");
  assert.equal(picks.length, 4);
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
  // the pane keys are spliced into the script inline (kernel.py: `""" + json.dumps([...]) + """`, the placeholder-free form the
  // 2026-09-15 pull-in took): the two literal halves around the splice, the keys parsed above between them
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
function paneCss(): string {
  const a = KERNEL.indexOf('"body:not(.po-chat) #chat-pane{display:none}');
  assert.ok(a > 0, "the landing's pane-hiding rule moved: re-anchor");
  return KERNEL.slice(a + 1, KERNEL.indexOf('"', a + 1));
}
// the shell's browse arms and the Files pane's close edge, as the landing ships them (the extraction above).
// The anchors are asserted here too: a missing stop made slice() run to the end of kernel.py, and the landing
// template it dragged into SHELL_HTML's script put a second #f-files on the page (a strict-mode violation in the
// browser legs that pointed nowhere near the cause)
function relayJs(): string {
  const start = KERNEL.indexOf("if(m.romp==='viewFile'&&m.pane==='pane'){");   // the viewer's pane arm leads the files arms (#1305 as landed); the browse arms follow
  const stop = KERNEL.indexOf("// The dashboard's one id", start);
  assert.ok(start >= 0 && stop > start, "relay anchors not found: re-anchor this extraction (see arms())");
  const js = KERNEL.slice(start, stop).trimEnd();
  assert.ok(js.endsWith("}});"), "the relay slice no longer ends at the listener's close: re-anchor");
  return js.slice(0, -3);
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
          // the CARD inside the backdrop too: the chat sheet centers it at min(720px,95%) since 2026-09-04, and the pane's
          // sheet must undo that (files-pane.css), else the listing floats in a dim pane while the backdrop still "fills"
          cardFills: (() => { const c = box && box.querySelector(".filebrowse"); if (!c) return null; const q = c.getBoundingClientRect(); return q.left === 0 && q.top === 0 && q.width === f.innerWidth && q.height === f.innerHeight; })(),
          dim: box ? getComputedStyle(box).backgroundColor : null,
          emptyHidden: (f.document.getElementById("files-empty") as HTMLElement).hidden,
          crumbs: Array.from(f.document.querySelectorAll("#fb-crumbs .fb-crumb")).map((c) => c.textContent),
          rows: Array.from(f.document.querySelectorAll(".fb-row")).map((c) => (c as HTMLElement).dataset.act + ":" + c.querySelector(".fb-name")!.textContent),
          back: !!f.document.querySelector(".fileview-back"),
          chip: f.document.querySelector(".fileview-sess")?.textContent ?? null,
          // the directory half of the title (the click back into the listing), as laid out in this 480px pane
          dirLink: (() => { const d = f.document.querySelector(".fileview-dir-link"); return d ? Math.round(d.getBoundingClientRect().width) : null; })(),
          // the pane's Recent list: the stored entries, and the rows the empty state paints from them
          recent: (() => { try { return JSON.parse(f.localStorage.getItem("romp:files-recent") || "[]").map((r: { path: string }) => r.path); } catch { return null; } })(),
          recentRows: Array.from(f.document.querySelectorAll("#files-empty .fs-row")).map((r) => (r as HTMLElement).title),
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
      assert.equal(s.cardFills, true, "and the listing card fills that box: no centered-card inset in a column, in " + name);
      assert.ok(s.dim === "rgba(0, 0, 0, 0)" || s.dim === "transparent", "no dimmed backdrop behind a listing that is the pane: " + s.dim);
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
      // the pick was remembered (files.ts openHere, through BrowseHost.openFile; review 2026-09-07: a file picked
      // from the listing never entered the Recent list), and the directory link is on screen in a 480px pane
      // (files-pane.css wraps the title bar; before, the row of buttons squeezed the link to 0px, in " + name + ")
      assert.deepEqual(s.recent, ["/repo/notes-api/README.md"]);
      assert.ok((s.dirLink ?? 0) > 40, "the directory link has width in a 480px pane: " + s.dirLink + "px in " + name);
      // phone widths (review round 2, 2026-09-07): a markdown file's six buttons ran 368px as one rigid row, and a pane
      // narrower than about 390px clipped the close button off it (.fileview is overflow:hidden); pane mode has no
      // backdrop to tap and a phone no Escape, so the file could not be closed from inside the pane. The row shrinks
      // and wraps now: every button's box lies inside the pane, above the body, and the bar overflows nothing
      for (const w of [320, 360]) {
        await page.evaluate((w: number) => { (document.getElementById("f-files") as HTMLIFrameElement).style.width = w + "px"; }, w);
        await page.waitForFunction((w: number) => (document.getElementById("f-files") as HTMLIFrameElement).contentWindow!.innerWidth === w, w, { timeout: 10000 });
        const m = await page.evaluate(() => {
          const f = (document.getElementById("f-files") as HTMLIFrameElement).contentWindow!;
          const bar = f.document.querySelector(".fileview-bar") as HTMLElement;
          const btns = Array.from(bar.querySelectorAll<HTMLElement>(".fileview-acts .fileview-btn"));
          const box = (e: Element) => { const b = e.getBoundingClientRect(); return { left: Math.round(b.left), right: Math.round(b.right), top: Math.round(b.top), bottom: Math.round(b.bottom) }; };
          return {
            labels: btns.map((b) => b.textContent),
            minLeft: Math.min(...btns.map((b) => box(b).left)), maxRight: Math.max(...btns.map((b) => box(b).right)),
            close: box(bar.querySelector(".fileview-close")!), body: box(f.document.querySelector(".fileview-main")!),
            barOver: bar.scrollWidth - bar.clientWidth,
          };
        });
        assert.ok(m.labels.includes("Copy path") && m.labels.includes("✕") && m.labels.length >= 5, "the markdown file's full action row is what is measured: " + m.labels.join(","));
        assert.ok(m.close.left >= 0 && m.close.right <= w && m.close.right > m.close.left, `the close button lies inside a ${w}px pane: x ${m.close.left}-${m.close.right} in ${name}`);
        assert.ok(m.minLeft >= 0 && m.maxRight <= w, `every action lies inside a ${w}px pane: x ${m.minLeft}-${m.maxRight} in ${name}`);
        assert.ok(m.close.bottom <= m.body.top, `the wrapped actions sit above the body, not over it, at ${w}px in ${name}`);
        assert.equal(m.barOver, 0, `the title bar overflows nothing at ${w}px in ${name}`);
      }
      await page.evaluate(() => { (document.getElementById("f-files") as HTMLIFrameElement).style.width = "480px"; });
      await page.waitForFunction(() => (document.getElementById("f-files") as HTMLIFrameElement).contentWindow!.innerWidth === 480, null, { timeout: 10000 });
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
      assert.deepEqual(s.recentRows, ["/repo/notes-api/README.md"], "the empty state lists the picked file under Recent");
      // the feed route, for contrast: the shell forwards path + sid into the feed and the Files pane hears nothing
      await page.evaluate((sid: string) => { window.postMessage({ romp: "browseFiles", pane: "feed", path: ".", sid }, "*"); }, SID);
      await page.waitForFunction(() => (((document.getElementById("f-feed") as HTMLIFrameElement).contentWindow as any).__got as unknown[]).length === 1, null, { timeout: 10000 });
      s = await state();
      assert.deepEqual(s.feedGot, [{ romp: "browseFiles", path: ".", sid: SID }]);
      assert.equal(s.browser, false, "the Files pane did not open a listing for a feed-bound browse");
      assert.deepEqual(errors, [], "no script error in any frame");
    } finally { await browser.close(); }
  });

  // review 2026-09-07: the Files pane's relay ran straight into openFileBrowse, which built the box, was vetoed by
  // the viewer's dirty-edit guard, and still sent listDir, so the listing loaded beneath the kept viewer (and on a
  // phone the tab had already switched). The stand-down now lives in openFileBrowse, for every host: a kept viewer
  // ends the click, nothing is fetched, and a box built for it is unbuilt. Both shapes, with the real editor chunk:
  // a viewer with no listing beneath (the viewFile relay), and one over a listing (a pick from the rows).
  test(`in ${name}: a viewer with unsaved edits in the Files pane stands a relayed browse down whole, with and without a listing beneath`, async (t) => {
    if (!pw) { t.skip("playwright is not installed under vscode-extension: the browser legs need it (CI installs no browsers)"); return; }
    let browser: any;
    try { browser = await pw[name].launch(); }
    catch (e) { t.skip("no playwright " + name + " on this box: this leg needs it (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
    try {
      const errors: string[] = [];
      const filesJs = bundle("files.ts");
      const editorJs = bundle("editor-chunk.ts");   // the on-demand CodeMirror bundle file-view.ts loads at the first Edit
      const css = CHAT_CSS + "\n" + read("files-pane.css");
      const page = await browser.newPage({ viewport: { width: 1000, height: 500 } });
      page.on("pageerror", (e: Error) => { errors.push(e.message); });
      await page.route("http://romp.test/**", (route: any) => {
        const u = new URL(route.request().url());
        const html = (b: string) => route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: b });
        const js = (b: string) => route.fulfill({ status: 200, contentType: "application/javascript", body: b });
        if (u.pathname === "/shell") return html(SHELL_HTML);
        if (u.pathname === "/feed") return html(FEED_HTML);
        if (u.pathname === "/files") return html(FILES_HTML(css));
        if (u.pathname === "/dist/files.js") return js(filesJs);
        if (u.pathname === "/dist/editor-chunk.js") return js(editorJs);
        // editing is allowed on this kernel, so the Edit button's consent gate asks nothing (file-view.ts ensureEditingAllowed)
        if (u.pathname === "/version") return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ fileEditing: true }) });
        if (u.pathname === "/file") {
          return route.fulfill({ status: 200, contentType: "text/plain; charset=utf-8", headers: { "X-Romp-Mtime-Ns": "1", "X-Romp-Text-Utf8": "1" }, body: "# notes-api\n\nTwo services.\n" });
        }
        return route.fulfill({ status: 404, body: "" });
      });
      await page.goto("http://romp.test/shell?panes=feed");
      const F = page.frameLocator("#f-files");
      const state = () => page.evaluate(() => {
        const f = (document.getElementById("f-files") as HTMLIFrameElement).contentWindow!;
        return {
          viewer: !!f.document.getElementById("romp-fileview"),
          editing: !!f.document.querySelector(".fileview-cm .cm-content"),
          browser: !!f.document.getElementById("romp-filebrowse"),
          browseClass: f.document.body.classList.contains("filebrowse-open"),
          listDirs: ((f as any).__posted as Array<Record<string, unknown>>).filter((m) => m.type === "listDir").map((m) => m.path),
          crumbs: Array.from(f.document.querySelectorAll("#fb-crumbs .fb-crumb")).map((c) => c.textContent),
          shellGot: (window as any).__shellGot as string[],
        };
      });
      // enter edit mode on the open file and type one character: the viewer's close guard now asks before discarding
      const editAndDirty = async () => {
        await F.getByRole("button", { name: "Edit", exact: true }).click();
        await F.locator(".fileview-cm .cm-content").waitFor({ timeout: 10000 });
        await F.locator(".fileview-cm .cm-content").click();
        await page.keyboard.type("x");
      };
      // the chat's relay for route 'pane' while the guard is armed: the confirm is the one announcement; `keep` answers it
      const browse = async (path: string, keep: boolean) => {
        const dlg = page.waitForEvent("dialog");
        await page.evaluate(([p, sid]: [string, string]) => { window.postMessage({ romp: "browseFiles", pane: "pane", path: p, sid }, "*"); }, [path, SID] as [string, string]);
        const d = await dlg;
        assert.equal(d.message(), "Discard unsaved changes to README.md?");
        if (keep) await d.dismiss(); else await d.accept();
      };
      // NO listing beneath: the file arrived by the viewFile relay
      await page.evaluate(([sid, identity]: [string, unknown]) => {
        window.postMessage({ romp: "viewFile", pane: "pane", path: "/repo/notes-api/README.md", sid, identity }, "*");
      }, [SID, IDENTITY] as [string, unknown]);
      await F.locator("#romp-fileview").waitFor({ timeout: 10000 });
      await editAndDirty();
      await browse("/repo/notes-api", true);
      let s = await state();
      assert.equal(s.viewer, true, "the viewer the person chose to keep is still up");
      assert.equal(s.editing, true, "still in edit mode, the edit intact");
      assert.equal(s.browser, false, "the box built for this click is unbuilt again");
      assert.equal(s.browseClass, false, "and its body class with it");
      assert.deepEqual(s.listDirs, [], "no listDir: nothing is fetched to sit beneath the kept viewer");
      assert.deepEqual(s.shellGot, [], "nothing told the shell");
      // the same click answered with OK: the edits go and the listing opens
      await browse("/repo/notes-api", false);
      await F.locator("#romp-filebrowse").waitFor({ timeout: 10000 });
      s = await state();
      assert.equal(s.viewer, false);
      assert.deepEqual(s.listDirs, ["/repo/notes-api"]);
      assert.deepEqual(s.shellGot, [], "the viewer closed onto the listing: not the pane's close edge");
      // WITH a listing beneath: answer the ask, pick the file from the rows, edit it, then browse elsewhere
      const reqId = await page.evaluate(() => {
        const f = (document.getElementById("f-files") as HTMLIFrameElement).contentWindow as any;
        return f.__posted.filter((m: { type: string }) => m.type === "listDir")[0].reqId;
      });
      await page.evaluate(([sid, reqId]: [string, unknown]) => {
        const f = (document.getElementById("f-files") as HTMLIFrameElement).contentWindow!;
        f.postMessage({ type: "dirListing", reqId, host: "", sid, base: "/repo/notes-api", parent: "/repo",
          entries: [{ name: "README.md", isDir: false, isLink: false, size: 120, mtime: 1, viewable: true }], total: 1, truncated: false }, "*");
      }, [SID, reqId] as [string, unknown]);
      await F.locator('.fb-row[data-act="file"]').click();
      await F.locator("#romp-fileview").waitFor({ timeout: 10000 });
      await editAndDirty();
      await browse("/repo", true);
      s = await state();
      assert.equal(s.viewer, true); assert.equal(s.editing, true);
      assert.equal(s.browser, true, "the listing beneath stays");
      assert.deepEqual(s.listDirs, ["/repo/notes-api"], "no second ask: the listing beneath is not moved under a kept viewer");
      assert.deepEqual(s.crumbs, ["/", "repo", "notes-api"], "as it was");
      await browse("/repo", false);
      await F.locator("#romp-fileview").waitFor({ state: "detached", timeout: 10000 });
      s = await state();
      assert.deepEqual(s.listDirs, ["/repo/notes-api", "/repo"], "OK: the edits go and the listing moves");
      assert.equal(s.browser, true);
      assert.deepEqual(errors, [], "no script error in any frame");
    } finally { await browser.close(); }
  });
}

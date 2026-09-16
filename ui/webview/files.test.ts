// The Files pane (files.ts): the file viewer as its own column of the dashboard, hosting the shared viewer
// pane-resident, with an empty state that lists the files most recently open there. No jsdom harness, so
// the boot wiring is pinned at source; what can run, runs: the pure half (the recent list and the relayed
// identity's validation, files-recent.ts), the viewer's relay guard (lifted from file-view.ts, plain JS
// inside the listener), and the pane's own open and close-edge functions (openHere, onBodyChange, lifted
// from files.ts with esbuild at run time, the chat-exact-tail-exec.test.ts idiom) over stubs for the viewer,
// the store and the shell. The shell's own relay arms run in tests/test_pane_state_broadcast.py and, lifted from
// kernel.py's landing shell, in the relay case below (a click naming no pane is not the shell's since T404). Synthetic rows: the notes-api demo world, placeholder sids, TESTHOST for a remote host.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { asIdentity, asPlace, parseRecent, rememberRecent, placeRecent, latestPlace, RECENT_MAX, type RecentFile, type RecentPlace } from "./files-recent";
import { hostOf } from "./host-prefix";   // the viewer's placeKey reads a remote session's host through it (the lifted rule below is bound to the real one)

const requireCjs = createRequire(__filename);

const UI = path.resolve(process.cwd(), "..", "ui", "webview");
const read = (f: string) => fs.readFileSync(path.join(UI, f), "utf8");
const SRC = read("files.ts");
const HELPERS = read("files-recent.ts");
const VIEW = read("file-view.ts");
const CSS = read("files-pane.css");
const KERNEL = fs.readFileSync(path.resolve(process.cwd(), "..", "kernel", "kernel.py"), "utf8");
const ESBUILD = fs.readFileSync(path.resolve(process.cwd(), "esbuild.js"), "utf8");

// synthetic rows: the notes-api demo world, placeholder sids, TESTHOST for the remote
const SID = "11111111-2222-3333-4444-555555555555";
const SID2 = "11111111-2222-3333-4444-666666666666";
const row = (p: string, sid: string | null, name = "web", t = 1, place: RecentPlace | null = null): RecentFile =>
  ({ path: p, sid, identity: { name, color: { bg: "#123456", fg: "#ffffff" } }, t, place });
// a reader's place as the viewer records it (file-view.ts RememberedPlace; contract C2): a span, pixels, a view, an mtime, a time; no text
const PLACE: RecentPlace = { start: 1200, end: 1480, top: -12.5, atTop: false, view: "rendered", mtimeNs: "1757145600000000001", scrollTop: 3312, t: 7 };

// files.ts's own functions, lifted whole (an anchored function, to its closing brace at column 0) and run
// over stubs: the viewer (openFileView answers H.openOk; this fork's open takes an options bag, ignored by the stub and records the identity it could resolve at that
// moment), the store, the repaint, the document (which surfaces are up, by id) and the shell (window.parent).
const ts = (code: string): string => requireCjs("esbuild").transformSync(code, { loader: "ts" }).code;
function fnSlice(startAnchor: string): string {
  const a = SRC.indexOf(startAnchor);
  assert.ok(a > 0, startAnchor.slice(0, 40) + " moved; re-anchor");
  const b = SRC.indexOf("\n}\n", a);
  assert.ok(b > a);
  return SRC.slice(a, b + 3);
}
type PaneHooks = { up: Set<string>; openOk: boolean; opens: Array<[string, string | null, unknown]>; writes: RecentFile[][]; paints: number; framed: boolean; posted: unknown[] };
type PaneApi = { openHere: (p: string, sid: string | null, identity: unknown) => void; onBodyChange: () => void; recent: () => RecentFile[]; identities: Map<string, unknown> };
function liftPane(over: Partial<PaneHooks> = {}): { H: PaneHooks; api: PaneApi } {
  const H: PaneHooks = { up: new Set(), openOk: true, opens: [], writes: [], paints: 0, framed: true, posted: [], ...over };
  const js = ts(fnSlice("function surfaceUp(): boolean {") + fnSlice("function openHere(") + fnSlice("let viewerUp = surfaceUp();\nfunction onBodyChange(): void {"));
  const prelude = `
    const H = HOOKS;
    const identities = new Map();
    let recent = [];
    const writeStore = () => { H.writes.push(recent.slice()); };
    const paint = () => { H.paints++; };
    const openFileView = (p, sid) => { H.opens.push([p, sid, (sid && identities.get(sid)) || null]); return H.openOk; };
    const document = { getElementById: (id) => (H.up.has(id) ? { id } : null) };
    const window = {};
    window.parent = H.framed ? { postMessage: (m) => { H.posted.push(m); } } : window;
    const Date = { now: () => 777 };
    const placeKey = (p, sid) => p + "\u0000" + (sid ?? "");   // one row per path and session here; the viewer's real rule is pinned in the openHere place case below
  `;
  const api = (new Function("HOOKS", "rememberRecent", "latestPlace", prelude + js + "return { openHere, onBodyChange, recent: () => recent, identities };") as
    (h: PaneHooks, rr: typeof rememberRecent, lp: typeof latestPlace) => PaneApi)(H, rememberRecent, latestPlace);
  return { H, api };
}


test("the pane hosts the shared viewer and takes the shell's relay WHOLE: its own contract, not the default open", () => {
  // initFileView's second argument replaces the default relay branch for this document: the relay carries
  // the session's identity, which the pane caches before opening, and the open enters the Recent list
  assert.match(SRC, /initFileView\(\(m\) => vscodeApi\?\.postMessage\(m\), \(m\) => \{\n\s*openHere\(m\.path, typeof m\.sid === "string" \? m\.sid : null, asIdentity\(m\.identity\), typeof m\.todoId === "string" \? m\.todoId : null, readAt\(m\.at\)\);\n\}, \{/,
    "…and the link's target the relay carries, validated by the viewer's readAt (it crossed a frame; Slice 6 of plans/markdown-viewer.md; a section rides as its heading arm, so the relay's frag slot is not read here)");
  // …and the third argument is the pane's opener for a link inside the shown file (file-view-links.test.ts pins its shape)
  assert.match(SRC, /initFileBrowse\(\(m\) => vscodeApi\?\.postMessage\(m\), \{\n\s*shellRestore: false,/,
    "the browser opens here too, owing the shell no restore (browse-route.test.ts pins the contract)");
  assert.match(VIEW, /onRelay\?: \(m: \{ path: string; sid\?: unknown; identity\?: unknown; todoId\?: unknown; at\?: unknown \}\) => void,/);
  assert.match(VIEW, /host\?: \{ openFile\?: \(path: string, sid: string \| null, at: At \| null\) => void/, "a link inside a shown file hands the host its target (C1)");
  const relayBranch = VIEW.split('if (m.romp === "viewFile"')[1].split("} else if")[0];
  const guard = "if (onRelay) { onRelay(m); return; }";
  // presence first: indexOf's -1 for an ABSENT guard is less than any index, so the ordering check alone
  // stayed green with the dispatch deleted (the 2026-09-03 review)
  assert.ok(relayBranch.indexOf(guard) >= 0, "the dispatch guard is present");
  assert.ok(relayBranch.indexOf("openFileView(m.path") >= 0, "the default open is present");
  assert.ok(relayBranch.indexOf(guard) < relayBranch.indexOf("openFileView(m.path"),
    "a document's own contract takes the message before the default open runs");
  // not a feed consumer: no frame parsing of any kind
  assert.doesNotMatch(SRC, /m\.type === "feed"|feedDelta|userTodoRows|ledgers|\.asks\b|needFullFeed/);
  assert.match(SRC, /vscodeApi\?\.postMessage\(\{ type: "ready" \}\)/, "the ready handshake lifts the shim's hold");
});

// executed: the relay branch of initFileView's listener, lifted from file-view.ts (plain JS inside the TS
// listener, so it runs as written) with openFileView stubbed. With onRelay the message is taken whole and
// the branch returns before the default open; without it the default open runs exactly as before.
test("the relay guard, executed: onRelay takes the message and short-circuits the default open", () => {
  const branch = VIEW.split('if (m.romp === "viewFile"')[1].split("} else if")[0];
  const body = '(function () { if (m.romp === "viewFile"' + branch + "} })();";
  // readAt (file-view.ts): the receiver's validation of the relay's `at` (Slice 6 of plans/markdown-viewer.md); a stand-in here
  // that passes an object through and refuses the rest, so the branch's call shape is what is under test, not the validator
  const readAt = (x: unknown) => (x && typeof x === "object" ? x : null);
  const fn = new Function("m", "onRelay", "openFileView", "readAt", body) as
    (m: unknown, onRelay: ((m: unknown) => void) | undefined, open: (p: string, sid: string | null, opts: unknown) => boolean, readAt: (x: unknown) => unknown) => void;
  const run = (m: unknown, onRelay: ((m: unknown) => void) | undefined) => {
    const opened: Array<[string, string | null, unknown]> = [];
    fn(m, onRelay, (p, sid, opts) => { opened.push([p, sid, opts]); return true; }, readAt);
    return opened;
  };
  const identity = { name: "web", color: { bg: "#123456", fg: "#ffffff" } };
  const msg = { romp: "viewFile", path: "/repo/notes-api/src/app.py", sid: SID, identity };
  const taken: unknown[] = [];
  assert.deepEqual(run(msg, (m) => taken.push(m)), [], "the default open never runs");
  assert.deepEqual(taken, [msg], "the pane's contract gets the message WHOLE, identity included");
  assert.deepEqual(run(msg, undefined), [["/repo/notes-api/src/app.py", SID, { at: null }]], "no contract of its own: the default open, with no target");
  assert.deepEqual(run({ ...msg, at: { heading: "results" } }, undefined), [["/repo/notes-api/src/app.py", SID, { at: { heading: "results" } }]],
    "…and with the relay's target, read through readAt (C1)");
  const junk: unknown[] = [];
  run({ romp: "viewFile", path: "" }, (m) => junk.push(m));
  run({ romp: "viewFile", path: 42 }, (m) => junk.push(m));
  run({ type: "fileSaved", reqId: 1 }, (m) => junk.push(m));
  assert.deepEqual(junk, [], "the outer guard still filters: no path, no relay");
});

test("the session chip resolves from what the relay carried, cached per sid, else the kernel's stub", () => {
  assert.match(SRC, /setFileViewIdentity\(\(id\) => identities\.get\(id\) \?\? hostStub\(id\)\);/);
  const openFn = SRC.split("function openHere(")[1].split("\n}")[0];
  assert.ok(openFn.indexOf("identities.set(sid, identity);") >= 0 && openFn.indexOf("openFileView(path, sid, { todoId, at, place })") >= 0
    && openFn.indexOf("identities.set(sid, identity);") < openFn.indexOf("openFileView(path, sid, { todoId, at, place })"),
    "the cache is filled BEFORE the open, so the title bar's chip resolves on the first paint");
  assert.match(openFn, /if \(sid && identity\) identities\.set\(sid, identity\);/);
  assert.doesNotMatch(SRC, /sessionsMeta|tabMeta|sessions\.get/, "the pane has no session list of its own");
});

// executed: openHere as files.ts spells it. The identity is cached BEFORE the viewer opens (the chip's resolver
// runs during the open, so a cache filled after it would miss on the first paint); a vetoed open (the viewer
// kept a dirty edit, openFileView false) records nothing and repaints nothing; a real one enters Recent with
// the identity the relay carried, else the one cached for the sid, else none, and persists.
test("openHere, executed: the identity is cached before the open, a vetoed open records nothing, a real one enters Recent and persists", () => {
  const identity = { name: "web", color: { bg: "#123456", fg: "#ffffff" } };
  const { H, api } = liftPane({ openOk: false });
  api.openHere("/repo/notes-api/src/app.py", SID, identity);
  assert.deepEqual(H.opens, [["/repo/notes-api/src/app.py", SID, identity]], "the viewer was asked, and could already resolve the chip");
  assert.deepEqual(api.recent(), [], "the veto: nothing recorded");
  assert.deepEqual(H.writes, [], "nothing persisted");
  assert.equal(H.paints, 0, "nothing repainted");
  H.openOk = true;
  api.openHere("/repo/notes-api/src/app.py", SID, identity);
  assert.deepEqual(api.recent(), [{ path: "/repo/notes-api/src/app.py", sid: SID, identity, t: 777, place: null }], "a real open enters Recent");
  assert.deepEqual(H.writes, [api.recent()], "and persists once");
  assert.equal(H.paints, 1, "and repaints the rows once");
  // a recent row re-opened carries its own identity; a relay with none falls to the identity cached for the sid
  api.openHere("/repo/notes-api/README.md", SID, null);
  assert.deepEqual(api.recent()[0], { path: "/repo/notes-api/README.md", sid: SID, identity, t: 777, place: null }, "the cached identity");
  assert.equal(api.recent().length, 2);
  // no sid and no identity: a row with no chip, never an invented one
  api.openHere("/repo/notes-api/notes.md", null, null);
  assert.deepEqual(api.recent()[0], { path: "/repo/notes-api/notes.md", sid: null, identity: null, t: 777, place: null });
  assert.equal(H.opens.length, 4);
  assert.equal(H.writes.length, 3); assert.equal(H.paints, 3);
});

test("recent files: recorded only on a REAL open, painted as re-open rows in the viewer's own dress, click-safe", () => {
  const openFn = SRC.split("function openHere(")[1].split("\n}")[0];
  assert.match(openFn, /if \(!openFileView\(path, sid, \{ todoId, at, place \}\)\) return;[^\n]*\n\s*const known = /, "a dirty-edit veto records nothing (a trailing comment on the line is allowed, nothing else)");
  assert.match(SRC, /openFile: \(p, sid, at\) => openHere\(p, sid, null, null, at\),/, "a link inside the shown file hands its target on (Slice 6 of plans/markdown-viewer.md)");
  assert.match(openFn, /recent = rememberRecent\(recent, \{ path, sid, identity: known, t: Date\.now\(\), place: null \}\);/, "the entry brings no place: rememberRecent keeps the row's (a relay re-open after the leave stored one)");
  assert.match(SRC, /let recent: RecentFile\[\] = parseRecent\(readStore\(\)\);/, "persisted per browser");
  assert.match(SRC, /"No file open"/);
  // the rows wear the viewer's title-bar classes, so a path and its chip read as they do above an open file
  for (const cls of ['"fileview-name"', '"fileview-dir"', '"fileview-base"', '"fileview-sess"']) assert.ok(SRC.includes(cls), cls);
  assert.match(SRC, /sess\.replaceChildren\(\.\.\.hostNameNodes\(r\.identity\.name, r\.sid\)\)/);
  // delegated on the stable container (actions.ts): a repaint between mousedown and mouseup still lands
  assert.match(SRC, /delegate\(empty, \{\n\s*open: \(x\) => \{ const r = recent\[Number\(x\.dataset\.i\)\]; if \(r\) openHere\(r\.path, r\.sid, r\.identity\); \},/,
    "the row's click opens through openHere like every other open; the place rides back from the store inside it (Slice 6 of plans/markdown-viewer.md, item 3)");
  assert.match(openFn, /const key = placeKey\(path, sid\);[^\n]*\n\s*const place = latestPlace\(recent, \(r\) => placeKey\(r\.path, r\.sid\) === key\);[^\n]*\n\s*if \(!openFileView\(path, sid, \{ todoId, at, place \}\)\) return;/,
    "openHere reads the rows' latest record for the FILE itself, before the open, and hands it to the viewer on EVERY open (the Slice 6 review, round 1: the relay's open after a reload landed at the top; round 5: two sessions' rows for one absolute path each seated their own record after a reload)");
  assert.match(SRC, /import \{ [^}]*\bplaceKey\b[^}]* \} from "\.\/file-view";/, "the rows for one file are told apart by the viewer's own rule (file-view.ts placeKey), not a copy of it");
  // the leave: the viewer's onLeave writes the record on the file's row (placeRecent) and persists the list; a file the pane
  // did not open has no row and gets nothing (executed: the host's arrow, lifted, over a list and a store recorder)
  const leave = /onLeave: (\(p, sid, rec\) => \{ recent = placeRecent\(recent, p, sid, rec\); writeStore\(\); \}),/.exec(SRC);
  assert.ok(leave, "the host's onLeave, as files.ts spells it");
  const writes: number[] = [];
  const world = new Function("placeRecent", "writeStore", "list", "let recent = list; const run = " + leave![1] + "; return { run, get recent() { return recent; } };")(
    placeRecent, () => { writes.push(1); }, [row("/repo/notes-api/a.md", SID), row("/repo/notes-api/b.md", SID2)]) as { run: (p: string, sid: string | null, rec: RecentPlace) => void; recent: RecentFile[] };
  world.run("/repo/notes-api/a.md", SID, PLACE);
  assert.deepEqual(world.recent.map((r) => [r.path, r.place]), [["/repo/notes-api/a.md", PLACE], ["/repo/notes-api/b.md", null]], "the record lands on its row alone");
  assert.equal(writes.length, 1, "…and the store is written once");
  world.run("/repo/notes-api/zzz.md", SID, PLACE);
  assert.deepEqual(world.recent.map((r) => r.place), [PLACE, null], "no row, nothing invented");
  assert.equal(writes.length, 2);
  assert.match(VIEW, /onLeave\?: \(path: string, sid: string \| null, rec: RememberedPlace\) => void/, "the host callback the viewer calls at a close, a replace-open and pagehide (C2)");
  assert.match(SRC, /row\.dataset\.act = "open"; row\.dataset\.i = String\(i\);/);
});

test("close returns to the empty state: the placeholder repaints on the viewer element's removal, never a hidden pane", () => {
  // closeFileView only removes #romp-fileview; the body's childList mutation IS the close event, and one
  // observer covers every open/close path (relay, recent row, the browser's rows and back, the close button, Escape, Reload)
  assert.match(SRC, /new MutationObserver\(onBodyChange\)\.observe\(document\.body, \{ childList: true \}\);/);
  assert.match(SRC, /function onBodyChange\(\): void \{\n\s*paint\(\);/, "the repaint rides the observer");
  // "open" is either surface: the viewer OR the browser, by element presence
  assert.match(SRC, /const open = surfaceUp\(\);\n\s*empty\.hidden = open;\n\s*if \(open\) return;/);
  assert.match(SRC, /function surfaceUp\(\): boolean \{\n\s*return !!\(document\.getElementById\("romp-fileview"\) \|\| document\.getElementById\("romp-filebrowse"\)\);\n\}/);
  assert.doesNotMatch(SRC, /setInterval|setTimeout/, "event-based, no polling");
});

// The close is also told to the SHELL: on a phone the viewFile relay switched tabs to show this pane, and
// closing the file would otherwise strand the person on the Files tab's recent list. The shell restores the
// tab the click came from, mobile only (kernel.py filesViewerClosed; tests/test_pane_state_broadcast.py).
test("the viewer's close EDGE posts filesViewerClosed up to the shell: once, framed only, never on an open-over-open", () => {
  assert.match(SRC, /let viewerUp = surfaceUp\(\);/);
  assert.match(SRC, /const up = surfaceUp\(\);\n\s*if \(viewerUp && !up && window\.parent !== window\) window\.parent\.postMessage\(\{ romp: "filesViewerClosed" \}, "\*"\);\n\s*viewerUp = up;/);
  assert.equal((SRC.match(/filesViewerClosed/g) || []).length, 2, "one post site (plus its comment)");
  // executed: onBodyChange as files.ts spells it, the observer's callback, driven by what is up in the document
  // (the viewer's wrap, the browser's overlay, by id) between calls
  const run = (states: string[][], framed: boolean): { posts: unknown[]; paints: number } => {
    const { H, api } = liftPane({ framed, up: new Set(states[0]) });   // the module's initial viewerUp reads the document at boot
    for (const up of states.slice(1)) { H.up = new Set(up); api.onBodyChange(); }
    return { posts: H.posted, paints: H.paints };
  };
  const V = "romp-fileview", B = "romp-filebrowse";
  assert.deepEqual(run([[], [V], []], true), { posts: [{ romp: "filesViewerClosed" }], paints: 2 }, "open then close: one notice, a repaint per mutation");
  assert.deepEqual(run([[], [V], [V], []], true).posts, [{ romp: "filesViewerClosed" }], "the Reload replace / open-over-open (still up when the observer runs) is not a close");
  assert.deepEqual(run([[], [V], [], [V], []], true).posts, [{ romp: "filesViewerClosed" }, { romp: "filesViewerClosed" }], "two closes: two notices");
  assert.deepEqual(run([[], []], true).posts, [], "an unrelated body mutation with nothing open posts nothing");
  assert.deepEqual(run([[V, B], [B], []], true).posts, [{ romp: "filesViewerClosed" }], "a viewer closing onto the listing beneath it is no edge; the listing's close is");
  assert.deepEqual(run([[], [V], []], false), { posts: [], paints: 2 }, "unframed (no shell): nothing to tell, the repaint still runs");
});

test("the pane-resident variant is keyed on the page's body class and lives ONLY in the pane sheet", () => {
  assert.match(KERNEL, /<body class=fileview-pane>/);   // the kernel serves the pane's page under it (this fork pins the served side too)
  assert.ok(CSS.includes("body.fileview-pane #romp-fileview{position:relative;inset:auto;flex:1 1 auto;min-height:0;background:none}"));
  assert.ok(CSS.includes("body.fileview-pane .fileview{width:100%;height:100%;border:0;border-radius:0;box-shadow:none}"));
  // relative, not static: the viewer keeps its z-index, so a file opened from a browser row still paints
  // above the browser's fixed overlay (styles.css .filebrowse) and the back button has something to go back to
  assert.doesNotMatch(CSS, /position:static/);
  for (const sheet of ["styles.css", "feed.css"]) assert.doesNotMatch(read(sheet), /fileview-pane/, sheet + " stays a mirror");
  for (const sel of ["#files-empty{", ".fs-title{", ".fs-hint{", ".fs-recent{", ".fs-row{"]) assert.ok(CSS.includes(sel), sel);
  // print: the pane's own screen rules (a clipped, flexed page) are undone so a file prints as a document,
  // the way the base sheets' print block does for the modal
  assert.match(CSS, /@media print\{html,body\{height:auto;overflow:visible;display:block/);
});

test("wired and vocabulary-clean: esbuild entries, no federation import, no fleet identifiers or prose", () => {
  assert.match(ESBUILD, /"\.\.\/ui\/webview\/files\.ts",/);
  assert.match(ESBUILD, /"\.\.\/ui\/webview\/files-pane\.css",/);
  for (const [name, src] of [["files.ts", SRC], ["files-recent.ts", HELPERS], ["files-pane.css", CSS]] as const) {
    assert.doesNotMatch(src, /from "\.\/federation"/, name + ": importing it boots a second FederationManager");
    assert.doesNotMatch(src, /fleet/i, name + ": no fleet identifiers or prose");
  }
});

// executed: the shell's relay arms, EXTRACTED from kernel.py's landing shell and run against a shimmed
// window/document: a `pane:"pane"` click drives the Files branch and never touches the feed; a click naming
// no pane (or the retired "feed" value) matches no arm and is not the shell's since T404 (the chat opens those
// in place; this fork's feed route retired with it, option c, 2026-09-15)
test("the shell's viewFile relay, executed: pane:'pane' brings the Files pane forward and forwards identity; a click naming no pane is not the shell's", () => {
  const start = KERNEL.indexOf("if(m.romp==='viewFile'&&m.pane==='pane'){");   // the viewer's pane arm leads the files arms (#1305 as landed, 2026-09-15); the feed route that was its else branch retired with T404 (option c)
  const stop = KERNEL.indexOf("// The dashboard's one id", start);   // the comment after the listener's close (2026-09-09 fold)
  assert.ok(start >= 0 && stop > start, "arm anchors not found — re-anchor this extraction");
  let arms = KERNEL.slice(start, stop).trimEnd();
  assert.ok(arms.endsWith("}});"));
  arms = arms.slice(0, -3);
  const armsFn = new Function("window", "document", "m", arms) as (w: unknown, d: unknown, m: unknown) => void;
  // a shell to send messages through: desktop by default; `mobile` answers __rompMobileOn true with `tab` showing
  const shell = (opts: { mobile?: boolean; tab?: string } = {}) => {
    const toggles: Array<[string, boolean]> = [], tabs: string[] = [];
    const posted: Record<string, unknown[]> = { "f-files": [], "f-feed": [], "f-chat": [] };
    const win: any = { __rompPaneToggle: (p: string, on: boolean) => toggles.push([p, on]), __rompMobileTab: (t: string) => tabs.push(t),
      __rompMobileOn: () => !!opts.mobile };
    const doc = {
      body: { classList: { contains: (c: string) => c === "po-feed" },   // feed on, files off
              getAttribute: (a: string) => (a === "data-tab" ? opts.tab ?? "chat" : null) },
      // a loaded page: the pane arms forward at once (a page still loading would hold the message for its load event)
      getElementById: (id: string) => (id in posted ? { contentWindow: { postMessage: (x: unknown) => posted[id].push(x) }, contentDocument: { readyState: "complete" } } : null),
    };
    const send = (m: unknown) => { armsFn(win, doc, m); return { toggles, tabs, posted, from: win.__rompFilesTabFrom }; };
    return { send, win };
  };
  const run = (m: unknown) => shell().send(m);
  const identity = { name: "web", color: { bg: "#123456", fg: "#ffffff" } };
  const pane = run({ romp: "viewFile", pane: "pane", path: "/repo/notes-api/src/app.py", sid: SID, identity });
  assert.deepEqual(pane.toggles, [["files", true]], "the Files pane comes forward; the feed is not touched");
  assert.deepEqual(pane.tabs, [], "DESKTOP: no mobile tab switch — the column is already visible, and show() would only persist a stale romp-mobile-tab");
  assert.equal(pane.from, undefined, "…and nothing to remember");
  assert.deepEqual(pane.posted["f-files"], [{ romp: "viewFile", path: "/repo/notes-api/src/app.py", sid: SID, identity, todoId: null, at: null, frag: null }],
    "a chat click names no todo and no target: the pane sees null, never undefined (frag: upstream's T351 slot, forwarded as is and unread by the pane, whose target is `at`)");
  assert.deepEqual(pane.posted["f-feed"], [], "nothing reaches the feed");
  // a Waiting-on-you detail link names the todo the path came from (plans/file-review.md Slice 0); forwarded as-is
  const fromTodo = run({ romp: "viewFile", pane: "pane", path: "docs/design.md", sid: SID, identity, todoId: "t1" });
  assert.deepEqual(fromTodo.posted["f-files"], [{ romp: "viewFile", path: "docs/design.md", sid: SID, identity, todoId: "t1", at: null, frag: null }]);
  // a todo link's target after its path (Slice 6 of plans/markdown-viewer.md): the forwarder copies `at` WHOLE, whatever
  // its shape (the receiver validates it, file-view.ts readAt; files.ts hands readAt(m.at) to the open); the forwarder
  // rebuilds the message field by field, so a field not copied is dropped in transit
  for (const at of [{ heading: "results" }, { line: 12 }, { offset: 400 }, { bogus: 1 }]) {
    const aimed = run({ romp: "viewFile", pane: "pane", path: "docs/report.md", sid: SID, identity, todoId: "t1", at });
    assert.deepEqual((aimed.posted["f-files"][0] as any).at, at, "the Files branch forwards at " + JSON.stringify(at));
    const unnamed = run({ romp: "viewFile", path: "docs/report.md", sid: SID, at });
    assert.deepEqual(unnamed.posted, { "f-files": [], "f-feed": [], "f-chat": [] }, "a click naming no pane forwards nothing, target or not: no arm is its (T404)");
  }
  // MOBILE (one tab at a time): the relay brings the Files tab forward and remembers the tab the click came
  // from; the Files pane's viewer close (files.ts posts filesViewerClosed) puts that tab back, once
  const phone = shell({ mobile: true, tab: "chat" });
  const onPhone = phone.send({ romp: "viewFile", pane: "pane", path: "/repo/notes-api/src/app.py", sid: SID, identity });
  assert.deepEqual(onPhone.tabs, ["files"]);
  assert.equal(onPhone.from, "chat", "the tab the click came from is remembered");
  assert.deepEqual(onPhone.toggles, [["files", true]], "the desktop bring-forward still runs (harmless; keeps po in step)");
  const closed = phone.send({ romp: "filesViewerClosed" });
  assert.deepEqual(closed.tabs, ["files", "chat"], "close → back to the remembered tab");
  assert.equal(closed.from, null, "…and the memory is consumed");
  assert.deepEqual(phone.send({ romp: "filesViewerClosed" }).tabs, ["files", "chat"], "a second close with nothing remembered switches nothing");
  // a phone already ON the Files tab: nothing to switch, nothing to remember
  const already = shell({ mobile: true, tab: "files" }).send({ romp: "viewFile", pane: "pane", path: "/p", sid: SID });
  assert.deepEqual(already.tabs, []); assert.equal(already.from, undefined);
  // desktop close: a no-op even if a memory were left (a rotation to desktop between open and close)
  const desk = shell(); desk.win.__rompFilesTabFrom = "chat";
  const deskClosed = desk.send({ romp: "filesViewerClosed" });
  assert.deepEqual(deskClosed.tabs, []); assert.equal(deskClosed.from, null, "dropped, never replayed later");
  // an older shell script without __rompMobileOn (no such thing after this change, but the arm must not throw)
  const bareWin = shell(); delete bareWin.win.__rompMobileOn;
  assert.deepEqual(bareWin.send({ romp: "viewFile", pane: "pane", path: "/p", sid: SID }).tabs, []);
  // a remote session's file: the prefixed sid rides through untouched (files.ts hands it to fileUrl, host-routed)
  const remote = run({ romp: "viewFile", pane: "pane", path: "/repo/notes-api/README.md", sid: "TESTHOST:" + SID2, identity: { name: "TESTHOST:api", color: null } });
  assert.equal((remote.posted["f-files"][0] as any).sid, "TESTHOST:" + SID2);
  // no identity on the relay (an older chat bundle): the forward carries null, and files.ts falls to the stub
  const bare = run({ romp: "viewFile", pane: "pane", path: "/repo/notes-api/README.md", sid: SID });
  assert.equal((bare.posted["f-files"][0] as any).identity, null);
  // a click naming no pane, or the retired "feed" value (this fork's File links setting, retired with T404, option c,
  // 2026-09-15): no arm matches, so the shell forwards nothing, switches no tab and toggles no pane; the chat opens those
  // in place (upstream's rule, kernel.py's pane-arm comment)
  for (const m of [{ romp: "viewFile", pane: "feed", path: "/p", sid: SID }, { romp: "viewFile", path: "/p", sid: SID }]) {
    const none = run(m);
    assert.deepEqual(none.posted, { "f-files": [], "f-feed": [], "f-chat": [] }, "nothing forwarded for " + JSON.stringify(m));
    assert.deepEqual(none.tabs, [], "no tab switch");
    assert.deepEqual(none.toggles, [], "no pane toggle");
    assert.equal(none.from, undefined, "nothing remembered");
  }
  // the quote-seed forward: the chat frame gets the message whole
  const seed = run({ type: "editorSelection", text: "the auth check", sid: SID, src: "src/app.py:12" });
  assert.deepEqual(seed.posted["f-chat"], [{ type: "editorSelection", text: "the auth check", sid: SID, src: "src/app.py:12" }]);
});

// ── executed: the pure half ──────────────────────────────────────────────────────────────────────

test("rememberRecent: most recent first, one row per path + session, capped", () => {
  let list: RecentFile[] = [];
  list = rememberRecent(list, row("/repo/notes-api/src/app.py", SID));
  list = rememberRecent(list, row("/repo/notes-api/README.md", SID, "web", 2));
  assert.deepEqual(list.map((r) => r.path), ["/repo/notes-api/README.md", "/repo/notes-api/src/app.py"]);
  // a re-open moves the row up and refreshes it (a renamed session's new identity lands)
  list = rememberRecent(list, row("/repo/notes-api/src/app.py", SID, "web-2", 3));
  assert.deepEqual(list.map((r) => [r.path, r.identity!.name]), [["/repo/notes-api/src/app.py", "web-2"], ["/repo/notes-api/README.md", "web"]]);
  // the same path from ANOTHER session is another row: the chip is what tells them apart
  list = rememberRecent(list, row("/repo/notes-api/src/app.py", SID2, "api", 4));
  assert.equal(list.length, 3);
  assert.deepEqual(list[0].sid, SID2);
  // capped at RECENT_MAX, dropping the oldest
  for (let i = 0; i < RECENT_MAX + 3; i++) list = rememberRecent(list, row("/repo/notes-api/f" + i + ".txt", SID, "web", 10 + i));
  assert.equal(list.length, RECENT_MAX);
  assert.equal(list[0].path, "/repo/notes-api/f" + (RECENT_MAX + 2) + ".txt");
  assert.ok(!list.some((r) => r.path === "/repo/notes-api/README.md"), "the oldest rows fell off");
});

test("parseRecent tolerates junk: a corrupt store costs the list, never the pane", () => {
  assert.deepEqual(parseRecent(null), []);
  assert.deepEqual(parseRecent("not json"), []);
  assert.deepEqual(parseRecent('{"path":"/x"}'), [], "not an array");
  const raw = JSON.stringify([
    { path: "/repo/notes-api/a.md", sid: SID, identity: { name: "web", color: { bg: "#123456", fg: "#fff" } }, t: 5 },
    { path: "", sid: SID },                       // no path → skipped
    { sid: SID2 },                                // no path → skipped
    { path: "/repo/notes-api/b.md", sid: 42, identity: "web", t: "soon" },   // foreign fields normalise
    "junk", null,
  ]);
  const got = parseRecent(raw);
  assert.deepEqual(got, [
    { path: "/repo/notes-api/a.md", sid: SID, identity: { name: "web", color: { bg: "#123456", fg: "#fff" } }, t: 5, place: null },
    { path: "/repo/notes-api/b.md", sid: null, identity: null, t: 0, place: null },
  ]);
  // an overlong store is capped on read, so a bloated entry cannot grow the list past the cap
  const many = JSON.stringify(Array.from({ length: RECENT_MAX + 5 }, (_, i) => ({ path: "/p" + i, sid: null })));
  assert.equal(parseRecent(many).length, RECENT_MAX);
});

test("asIdentity validates the relayed identity to the chip's shape; anything else is no identity", () => {
  assert.deepEqual(asIdentity({ name: "web", color: { bg: "#123456", fg: "#ffffff" } }), { name: "web", color: { bg: "#123456", fg: "#ffffff" } });
  assert.deepEqual(asIdentity({ name: "TESTHOST:api", color: null }), { name: "TESTHOST:api", color: null }, "a remote session's prefixed name, uncolored");
  assert.deepEqual(asIdentity({ name: "web", color: { bg: 1 } }), { name: "web", color: null }, "a malformed colour is dropped, the name kept");
  assert.equal(asIdentity({ name: "" }), null);
  assert.equal(asIdentity({ color: { bg: "#123456", fg: "#fff" } }), null, "no name, no chip: never invented");
  assert.equal(asIdentity(null), null);
  assert.equal(asIdentity("web"), null);
});

// ── the reader's place on a row (plans/markdown-viewer.md, Slice 6, item 3) ─────────────────────────
// The viewer hands the pane the place of a file being left (initFileView's onLeave: the top block's source span and
// pixel offset, the view, the file's mtime, the numeric scrollTop, the time); the pane stores it on the file's row
// and hands it back when the row is clicked (openFileView's `place`), so a note reopened from Recent returns to
// where it was read. The record is validated field by field on read, as the identity is; never a word of the file.
test("parseRecent keeps a well-formed place on its row and drops a malformed one, keeping the row", () => {
  const raw = JSON.stringify([
    { path: "/repo/notes-api/a.md", sid: SID, t: 5, place: PLACE },
    { path: "/repo/notes-api/b.md", sid: SID, t: 4, place: "3312" },                                  // a string: no place
    { path: "/repo/notes-api/c.md", sid: SID, t: 3, place: { ...PLACE, start: 1500 } },               // end before start: no place
    { path: "/repo/notes-api/d.md", sid: SID, t: 2, place: { ...PLACE, start: -1 } },                 // a negative offset
    { path: "/repo/notes-api/e.md", sid: SID, t: 1, place: (({ mtimeNs, ...rest }) => rest)(PLACE) },   // a missing field
    { path: "/repo/notes-api/f.md", sid: SID, t: 1, place: { ...PLACE, view: "source" } },            // a view the viewer has no name for
    { path: "/repo/notes-api/g.md", sid: SID, t: 1, place: { ...PLACE, scrollTop: -4 } },             // a scrollTop below the top
    { path: "/repo/notes-api/h.md", sid: SID, t: 1, place: { ...PLACE, top: "12" } },                 // a pixel offset as a string
    { path: "/repo/notes-api/i.md", sid: SID, t: 1, place: { ...PLACE, atTop: 1 } },                  // a truthy number is not the boolean
    { path: "/repo/notes-api/j.md", sid: SID, t: 1, place: { ...PLACE, t: NaN } },                    // NaN serialises to null: no time
    { path: "/repo/notes-api/k.md", sid: SID, t: 1 },                                                 // no place at all
  ]);
  const got = parseRecent(raw);
  assert.equal(got.length, 8, "the cap, not the malformed places, bounds the list (RECENT_MAX rows)");
  assert.deepEqual(got[0].place, PLACE, "a well-formed record survives whole");
  for (const r of got.slice(1)) assert.equal(r.place, null, r.path + ": a malformed record costs the place, never the row");
  assert.deepEqual(got.map((r) => r.path.slice(-4, -3)), ["a", "b", "c", "d", "e", "f", "g", "h"], "every row kept, in order");
  // the validator alone, and what it never does: widen the record with a field it does not know
  assert.deepEqual(asPlace({ ...PLACE, source: "lorem ipsum", text: "dolor" }), PLACE, "a stray text field is dropped on read: nothing but the record's fields reaches the store");
  assert.deepEqual(asPlace({ ...PLACE, top: 0, scrollTop: 0, atTop: true, view: "raw" }), { ...PLACE, top: 0, scrollTop: 0, atTop: true, view: "raw" }, "the top of a file in the Raw view is a place too");
  assert.equal(asPlace(null), null); assert.equal(asPlace(PLACE.start), null); assert.equal(asPlace({ ...PLACE, end: Infinity }), null);
  // the open folds (review round 3): a list of non-negative integers, the ordinals of the Rendered view's open <details>; absent
  // is fine (a Raw read, a note with no fold, a record an older store wrote); anything else is no place
  assert.deepEqual(asPlace({ ...PLACE, folds: [0, 2] }), { ...PLACE, folds: [0, 2] }, "the fold ordinals ride along");
  assert.deepEqual(asPlace({ ...PLACE, folds: [] }), { ...PLACE, folds: [] }, "an empty list: no fold open, which is a state too");
  assert.equal(Object.prototype.hasOwnProperty.call(asPlace(PLACE)!, "folds"), false, "absent stays absent");
  for (const bad of [[1.5], [-1], ["0"], "0,2", 2, null, {}]) assert.equal(asPlace({ ...PLACE, folds: bad }), null, "malformed folds " + JSON.stringify(bad) + ": no place");
  const src = [3]; assert.notEqual(asPlace({ ...PLACE, folds: src })!.folds, src, "a copy of the list, not the stored array");
});

test("rememberRecent carries the newest record, and a re-open that brings none keeps the row's", () => {
  let list: RecentFile[] = [];
  list = rememberRecent(list, row("/repo/notes-api/a.md", SID, "web", 1));
  assert.equal(list[0].place, null, "a first open has no place yet");
  list = placeRecent(list, "/repo/notes-api/a.md", SID, PLACE);
  assert.deepEqual(list[0].place, PLACE, "the leave writes the record on the row");
  // the shell's relay re-opens the same file: openHere builds an entry with no place AFTER the viewer's leave stored one
  list = rememberRecent(list, row("/repo/notes-api/a.md", SID, "web-2", 2));
  assert.deepEqual(list.map((r) => [r.identity!.name, r.place]), [["web-2", PLACE]], "the row moves up, its identity refreshes, its place stays");
  // an entry that brings a record wins
  const later = { ...PLACE, start: 2000, end: 2300, scrollTop: 5000, t: 9 };
  list = rememberRecent(list, row("/repo/notes-api/a.md", SID, "web-2", 3, later));
  assert.deepEqual(list[0].place, later);
  // another session's row for the same path is another row, with a place of its own
  list = rememberRecent(list, row("/repo/notes-api/a.md", SID2, "api", 4));
  assert.deepEqual(list.map((r) => [r.sid, r.place]), [[SID2, null], [SID, later]]);
  // placeRecent writes the matching row and no other; no such row, the list stands
  const placed = placeRecent(list, "/repo/notes-api/a.md", SID2, PLACE);
  assert.deepEqual(placed.map((r) => [r.sid, r.place]), [[SID2, PLACE], [SID, later]]);
  assert.deepEqual(placeRecent(list, "/repo/notes-api/zzz.md", SID, PLACE), list, "nothing is invented for a file the pane did not open");
  assert.notEqual(placed, list, "a new list, not a write into the old one");
  // the record's JSON, as localStorage will hold it: the eight fields (nine with the fold ordinals of a Rendered read) and nothing
  // that could hold the file's text
  const json = JSON.stringify(placed[0]);
  assert.deepEqual(Object.keys(JSON.parse(json).place).sort(), ["atTop", "end", "mtimeNs", "scrollTop", "start", "t", "top", "view"]);
  assert.doesNotMatch(json, /source|text|quote|lorem/, "no text field, no quote");
  const withFolds = JSON.stringify(placeRecent(list, "/repo/notes-api/a.md", SID2, { ...PLACE, folds: [1, 4] })[0]);
  assert.deepEqual(Object.keys(JSON.parse(withFolds).place).sort(), ["atTop", "end", "folds", "mtimeNs", "scrollTop", "start", "t", "top", "view"]);
  assert.deepEqual(JSON.parse(withFolds).place.folds, [1, 4], "the folds are numbers in the store, never text");
});

// The rows' record for a FILE (files-recent.ts latestPlace): the rows are per path + session, the viewer's in-page memory per
// file (file-view.ts placeKey), so the pane reads the later record among the rows the viewer's rule says name one file. The
// admitting rule is the caller's; this is the pure half.
test("latestPlace: the later record among the rows the caller admits, whichever row holds it; none admitted or none with a place, null; a tie keeps the first row", () => {
  const REPORT = "/repo/notes-api/docs/report.md", NOTES = "/repo/notes-api/docs/notes.md";
  const a: RecentPlace = { ...PLACE, t: 5 }, b: RecentPlace = { ...PLACE, start: 900, end: 950, scrollTop: 2000, t: 8 }, c: RecentPlace = { ...PLACE, start: 20, end: 40, scrollTop: 0, atTop: true, t: 99 };
  const list = [row(REPORT, SID, "web", 3, a), row(REPORT, SID2, "api", 2, b), row(NOTES, SID, "web", 1, c), row("docs/report.md", SID, "web", 0, null)];
  assert.deepEqual(latestPlace(list, (r) => r.path === REPORT), b, "the later record, on the other session's row");
  assert.deepEqual(latestPlace(list, (r) => r.path === REPORT && r.sid === SID), a, "admitting one row reads that row");
  assert.deepEqual(latestPlace(list, () => true), c, "the admitting rule is the caller's");
  assert.equal(latestPlace(list, (r) => r.path === "/repo/notes-api/README.md"), null, "no row admitted");
  assert.equal(latestPlace(list, (r) => r.path === "docs/report.md"), null, "a row with no place holds nothing to seat");
  assert.equal(latestPlace([], () => true), null);
  const tie: RecentPlace = { ...b, scrollTop: 2222 };
  assert.deepEqual(latestPlace([row(REPORT, SID, "web", 3, tie), row(REPORT, SID2, "api", 2, b)], (r) => r.path === REPORT), tie, "a tie keeps the first row, the most recent");
  assert.deepEqual(list.map((r) => r.place), [a, b, c, null], "the list is read, never changed");
});

// EXECUTED: openHere as files.ts spells it, its body lifted from the source (the signature's types stripped) and run over
// stubs for the viewer's open, the store and the paint, with the real list functions and the viewer's placeKey lifted from its
// source as well. The Slice 6 review's round 1: the row's click alone passed the row's place, so after a page reload (the
// viewer's in-page map empty) a chat click on a file whose row held a record opened it at the top, and that open's leave
// wrote the top over the row. Every open through openHere now hands a record back; the viewer seats the later of that and its
// own (file-view.ts newerPlace) and ignores both under an `at` (openFileView's doc), so the pane hands it over regardless.
// Round 5: the record is the latest among the rows that name the same FILE by the viewer's rule (placeKey: an absolute or ~
// path is one file for every session, a relative one is per session), not the open's own row alone, which seated the file's
// latest place before a reload (the shared in-page key) and the session's older place after one.
test("openHere, executed: every open of a file with a row hands the rows' latest record to the viewer (the relay, a link, the row's click, another session's row for the same absolute path), none for a path with no row or another session's relative path; a veto records nothing; the row keeps a fresher record its leave wrote during the open", () => {
  const src = SRC.split("function openHere(")[1].split("\n}")[0];
  const sig = src.slice(0, src.indexOf("{") + 1);
  const js = "function openHere(" + sig.replace(/: [A-Za-z]+(?: \| null)?/g, "") + src.slice(src.indexOf("{") + 1) + "\n}";   // the source's own parameters, their types stripped
  const keySrc = VIEW.split("export function placeKey(")[1].split("\n}")[0];   // the viewer's rule for one file, as file-view.ts spells it
  const lifted = new Function("path", "sid", "hostOf", keySrc.slice(keySrc.indexOf("{") + 1)) as (p: string, sid: string | null, h: typeof hostOf) => string;
  const placeKey = (p: string, sid: string | null): string => lifted(p, sid, hostOf);   // the rule reads the sid's host through host-prefix.ts (PR review round 1)
  assert.equal(placeKey("/repo/notes-api/docs/report.md", SID2), "/repo/notes-api/docs/report.md", "the lifted rule: an absolute path is one file for every session of this kernel");
  assert.notEqual(placeKey("docs/report.md", SID), placeKey("docs/report.md", SID2), "…a relative path one per session");
  const REMOTE = "TESTHOST:" + SID2;                                             // a session attached from another kernel, as federation prefixes its sid
  assert.equal(placeKey("/repo/notes-api/docs/report.md", REMOTE), "TESTHOST\u0000/repo/notes-api/docs/report.md", "…and a remote session's absolute path carries its host: that kernel's disk is another file (PR review round 1)");
  const opens: unknown[][] = []; const writes: number[] = []; const paints: number[] = [];
  const last = () => opens[opens.length - 1];
  const handed = () => (last()[2] as { place: unknown }).place;
  let veto = false;
  let leaveOnOpen: (() => void) | null = null;   // the viewer's runLeave on a replace-open reaches the host's onLeave BEFORE openFileView returns
  const identities = new Map<string, unknown>();
  const REPORT = "/repo/notes-api/docs/report.md", NOTES = "/repo/notes-api/docs/notes.md", DESIGN = "/repo/notes-api/docs/design.md";
  const REL_PLACE: RecentPlace = { ...PLACE, start: 400, end: 520, scrollTop: 900, t: 6 };   // session A's read of its own docs/report.md
  const world = new Function("openFileView", "rememberRecent", "latestPlace", "placeKey", "writeStore", "paint", "identities", "list",
    "let recent = list; " + js + " return { openHere, get recent() { return recent; }, set recent(v) { recent = v; } };")(
    (p: string, sid: string | null, opts: unknown) => { opens.push([p, sid, opts]); if (leaveOnOpen) { const f = leaveOnOpen; leaveOnOpen = null; f(); } return !veto; },
    rememberRecent, latestPlace, placeKey, () => { writes.push(1); }, () => { paints.push(1); }, identities,
    [row(NOTES, SID2, "api", 3), row(REPORT, SID, "web", 2, PLACE), row(DESIGN, SID, "web", 1), row("docs/report.md", SID, "web", 0, REL_PLACE)],
  ) as { openHere: (p: string, sid: string | null, id: unknown, todoId?: string | null, at?: unknown) => void; recent: RecentFile[] };
  const identity = { name: "web", color: { bg: "#123456", fg: "#ffffff" } };
  // the shell's relay (a chat click) after a reload: no place in hand, the row's record rides
  world.openHere(REPORT, SID, identity, null, null);
  assert.deepEqual(last(), [REPORT, SID, { todoId: null, at: null, place: PLACE }], "the relay's open hands the row's record back");
  assert.deepEqual(world.recent.map((r) => [r.path, r.place]), [[REPORT, PLACE], [NOTES, null], [DESIGN, null], ["docs/report.md", REL_PLACE]], "the row moves up and keeps its place");
  assert.equal(writes.length, 1); assert.equal(paints.length, 1);
  // a link inside a shown file (no identity in hand; the cache the relay filled names the chip): the same record
  world.openHere(REPORT, SID, null, null, null);
  assert.deepEqual(last(), [REPORT, SID, { todoId: null, at: null, place: PLACE }], "a link's open too");
  assert.deepEqual(world.recent[0].identity, identity, "the chip's identity from the cache");
  // the row's click: the same call, the same record (one source, the store)
  world.openHere(REPORT, SID, identity);
  assert.deepEqual(handed(), PLACE, "the row's click");
  // rows are per path + session, but an ABSOLUTE path is one file for every session (the viewer's placeKey): another session's
  // open of the report finds the file's record on the first session's row, as the viewer's in-page memory hands it before a
  // reload (round 5: reading the open's own row alone, this open handed null after a reload and the shared key's record before one)
  world.openHere(REPORT, SID2, null);
  assert.deepEqual(last(), [REPORT, SID2, { todoId: null, at: null, place: PLACE }], "another session's open of the same absolute path: the file's record, from the first session's row");
  assert.deepEqual(world.recent.map((r) => [r.sid, r.place]), [[SID2, null], [SID, PLACE], [SID2, null], [SID, null], [SID, REL_PLACE]], "a new row for it with no place of its own yet; the first session's stands");
  // …and of two rows for one file the LATER record seats, whichever row is clicked (the second session's leave wrote its row)
  const later: RecentPlace = { ...PLACE, start: 1500, end: 1700, scrollTop: 4100, t: 8 };
  world.recent = placeRecent(world.recent, REPORT, SID2, later);
  world.openHere(REPORT, SID, identity);
  assert.deepEqual(handed(), later, "the first session's row click seats the later record, the other row's");
  world.openHere(REPORT, SID2, null);
  assert.deepEqual(handed(), later, "the second session's too");
  assert.deepEqual(world.recent.map((r) => [r.sid, r.place]).slice(0, 2), [[SID2, later], [SID, PLACE]], "each row keeps its own record; the read joins them, the write does not");
  // a RELATIVE path is a file per session (the kernel resolves it against the session's cwd): another session's row hands nothing
  world.openHere("docs/report.md", SID, null);
  assert.deepEqual(handed(), REL_PLACE, "the session's own relative row");
  world.openHere("docs/report.md", SID2, null);
  assert.deepEqual(last(), ["docs/report.md", SID2, { todoId: null, at: null, place: null }], "another session's docs/report.md is another file: no record");
  // a path with no row: nothing to hand back
  world.openHere("/repo/notes-api/README.md", SID, null);
  assert.deepEqual(handed(), null);
  // an `at` open (a todo's target): the pane hands the record all the same; the viewer lands on the target and ignores it
  world.openHere(REPORT, SID, null, "t1", { heading: "results" });
  assert.deepEqual(last(), [REPORT, SID, { todoId: "t1", at: { heading: "results" }, place: later }]);
  // the same file opened over itself: the viewer's leave writes a fresher record on the row DURING the open; the pane read
  // the rows before it and hands the older one (the viewer seats the later of the two), and the row keeps the fresh record
  // afterwards, since the entry openHere writes brings none
  const fresh: RecentPlace = { ...PLACE, start: 2000, end: 2300, scrollTop: 5000, t: 9 };
  leaveOnOpen = () => { world.recent = placeRecent(world.recent, REPORT, SID, fresh); };
  world.openHere(REPORT, SID, null);
  assert.deepEqual(handed(), later, "read before the open");
  assert.deepEqual(world.recent[0].place, fresh, "the leave's fresher record stands on the row");
  // a dirty-edit veto: the open did not happen, so nothing is recorded, written or painted
  const n = opens.length, w = writes.length, k = paints.length, before = world.recent;
  veto = true;
  world.openHere(NOTES, SID2, null);
  assert.equal(opens.length, n + 1); assert.equal(writes.length, w); assert.equal(paints.length, k); assert.equal(world.recent, before, "the list is untouched");
  veto = false;
  // a session attached from another kernel naming the same absolute path reads that kernel's disk, another file: the local rows'
  // record is not handed to it (PR review round 1: before, the shared key handed the file's latest record across the kernels)
  world.openHere(REPORT, REMOTE, { name: "TESTHOST:api", color: { bg: "#654321", fg: "#ffffff" } });
  assert.deepEqual(last(), [REPORT, REMOTE, { todoId: null, at: null, place: null }], "the remote session's open of the same absolute path: no record, the local rows naming another file");
  assert.deepEqual(world.recent[0].sid, REMOTE, "…and a row of its own");
  world.recent = placeRecent(world.recent, REPORT, REMOTE, { ...PLACE, start: 900, scrollTop: 2500, t: 20 });
  world.openHere(REPORT, SID, identity);
  assert.deepEqual(handed(), fresh, "the local session's open ignores the remote row's newer record");
  world.openHere(REPORT, REMOTE, null);
  assert.deepEqual(handed(), { ...PLACE, start: 900, scrollTop: 2500, t: 20 }, "the remote session's open hands its own row's record");
  // the shape that makes this so: five parameters and no `place`, the rows' record read inside, so no caller can pass a stale one or forget it
  assert.equal(sig, "path: string, sid: string | null, identity: FileViewIdentity | null, todoId: string | null = null, at: At | null = null): void {");
});

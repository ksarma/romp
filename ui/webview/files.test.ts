// The "Files" pane (files.ts): the file VIEWER as its own column of the dashboard, hosting the shared
// viewer pane-resident, with an empty state that lists the files most recently open there. No jsdom
// harness, so the wiring is pinned at source (the waiting.test.ts idiom); the pure half — the recent
// list and the relayed identity's validation (files-recent.ts) — runs for real.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { asIdentity, parseRecent, rememberRecent, RECENT_MAX, type RecentFile } from "./files-recent";

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
const row = (p: string, sid: string | null, name = "web", t = 1): RecentFile =>
  ({ path: p, sid, identity: { name, color: { bg: "#123456", fg: "#ffffff" } }, t });

test("the pane hosts the shared viewer and takes the shell's relay WHOLE: its own contract, not the feed's", () => {
  // initFileView's second argument replaces the default relay branch — the feed's viaRelay + ack —
  // for this document; the pane owes the shell no pane restore, it stays up
  assert.match(SRC, /initFileView\(\(m\) => vscodeApi\?\.postMessage\(m\), \(m\) => \{\n\s*openHere\(m\.path, typeof m\.sid === "string" \? m\.sid : null, asIdentity\(m\.identity\), typeof m\.todoId === "string" \? m\.todoId : null\);\n\}\);/);
  assert.match(SRC, /initFileBrowse\(\(m\) => vscodeApi\?\.postMessage\(m\), \{\n\s*shellRestore: false,/,
    "the browser opens here too, owing the shell no restore (browse-route.test.ts pins the contract)");
  assert.match(VIEW, /onRelay\?: \(m: \{ path: string; sid\?: unknown; identity\?: unknown; todoId\?: unknown \}\) => void\): void \{/);
  const relayBranch = VIEW.split('if (m.romp === "viewFile"')[1].split("} else if")[0];
  const guard = "if (onRelay) { onRelay(m); return; }";
  // presence first: indexOf's -1 for an ABSENT guard is less than any index, so the ordering check alone
  // stayed green with the dispatch deleted (the 2026-09-03 review)
  assert.ok(relayBranch.indexOf(guard) >= 0, "the dispatch guard is present");
  assert.ok(relayBranch.indexOf("viaRelay = true;") >= 0, "the feed's arm is present");
  assert.ok(relayBranch.indexOf(guard) < relayBranch.indexOf("viaRelay = true;"),
    "a document's own contract takes the message before the feed's arms run");
  const code = SRC.replace(/^\s*\/\/.*$/gm, "");   // the header names the feed's contract to say the pane has none; the code must not touch it
  assert.doesNotMatch(code, /viaRelay|viewFileOpened|viewFileClosed|__rompFeedWasOff/, "none of the feed route's restore machinery");
  // not a feed consumer: no frame parsing of any kind
  assert.doesNotMatch(SRC, /m\.type === "feed"|feedDelta|userTodoRows|ledgers|\.asks\b|needFullFeed/);
  assert.match(SRC, /vscodeApi\?\.postMessage\(\{ type: "ready" \}\)/, "the ready handshake lifts the shim's hold");
});

// executed: the relay branch of initFileView's listener, EXTRACTED from file-view.ts (plain JS inside the
// TS listener, so it runs as written) with the feed's arms — openFileView, viaRelay, the shell ack — stubbed.
// With onRelay the message is taken whole and the function RETURNS before any of them; without it the feed
// route runs exactly as before. Deleting the guard turns the first case into the second.
test("the relay guard, executed: onRelay takes the message and short-circuits the feed's arms; no onRelay, the feed route", () => {
  const branch = VIEW.split('if (m.romp === "viewFile"')[1].split("} else if")[0];
  const body = 'var viaRelay = false; (function () { if (m.romp === "viewFile"' + branch + "} })(); return viaRelay;";
  const fn = new Function("m", "onRelay", "openFileView", "window", body) as
    (m: unknown, onRelay: ((m: unknown) => void) | undefined, open: (p: string, sid: string | null) => boolean, w: unknown) => boolean;
  const run = (m: unknown, onRelay: ((m: unknown) => void) | undefined, verdict = true) => {
    const opened: Array<[string, string | null]> = [], posted: unknown[] = [];
    const win = { parent: { postMessage: (x: unknown) => posted.push(x) } };   // embedded: parent !== window
    const viaRelay = fn(m, onRelay, (p, sid) => { opened.push([p, sid]); return verdict; }, win);
    return { opened, posted, viaRelay };
  };
  const identity = { name: "web", color: { bg: "#123456", fg: "#ffffff" } };
  const msg = { romp: "viewFile", path: "/repo/notes-api/src/app.py", sid: SID, identity };
  const taken: unknown[] = [];
  const pane = run(msg, (m) => taken.push(m));
  assert.deepEqual(taken, [msg], "the pane's contract gets the message WHOLE — identity included");
  assert.deepEqual(pane.opened, [], "the feed's open never runs");
  assert.equal(pane.viaRelay, false, "…nor its relay flag");
  assert.deepEqual(pane.posted, [], "…nor its viewFileOpened ack");
  const feed = run(msg, undefined);
  assert.deepEqual(feed.opened, [["/repo/notes-api/src/app.py", SID]], "no contract of its own: the feed route opens");
  assert.equal(feed.viaRelay, true);
  assert.deepEqual(feed.posted, [{ romp: "viewFileOpened" }], "and acks the shell so it arms its pane restore");
  const veto = run(msg, undefined, false);
  assert.equal(veto.viaRelay, false, "a dirty-edit veto opens nothing and earns no ack");
  assert.deepEqual(veto.posted, []);
  const junk: unknown[] = [];
  run({ romp: "viewFile", path: "" }, (m) => junk.push(m));
  run({ romp: "viewFile", path: 42 }, (m) => junk.push(m));
  run({ type: "fileSaved", reqId: 1 }, (m) => junk.push(m));
  assert.deepEqual(junk, [], "the outer guard still filters: no path, no relay");
});

test("the session chip resolves from what the relay carried, cached per sid, else the kernel's stub", () => {
  assert.match(SRC, /setFileViewIdentity\(\(id\) => identities\.get\(id\) \?\? hostStub\(id\)\);/);
  const openFn = SRC.split("function openHere(")[1].split("\n}")[0];
  assert.ok(openFn.indexOf("identities.set(sid, identity);") >= 0 && openFn.indexOf("openFileView(path, sid, { todoId })") >= 0
    && openFn.indexOf("identities.set(sid, identity);") < openFn.indexOf("openFileView(path, sid, { todoId })"),
    "the cache is filled BEFORE the open, so the title bar's chip resolves on the first paint");
  assert.match(openFn, /if \(sid && identity\) identities\.set\(sid, identity\);/);
  assert.doesNotMatch(SRC, /sessionsMeta|tabMeta|sessions\.get/, "the pane has no session list of its own");
});

test("recent files: recorded only on a REAL open, painted as re-open rows in the viewer's own dress, click-safe", () => {
  const openFn = SRC.split("function openHere(")[1].split("\n}")[0];
  assert.match(openFn, /if \(!openFileView\(path, sid, \{ todoId \}\)\) return;\n\s*const known = /, "a dirty-edit veto records nothing");
  assert.match(openFn, /recent = rememberRecent\(recent, \{ path, sid, identity: known, t: Date\.now\(\) \}\);/);
  assert.match(SRC, /let recent: RecentFile\[\] = parseRecent\(readStore\(\)\);/, "persisted per browser");
  assert.match(SRC, /"No file open"/);
  // the rows wear the viewer's title-bar classes, so a path and its chip read as they do above an open file
  for (const cls of ['"fileview-name"', '"fileview-dir"', '"fileview-base"', '"fileview-sess"']) assert.ok(SRC.includes(cls), cls);
  assert.match(SRC, /sess\.replaceChildren\(\.\.\.hostNameNodes\(r\.identity\.name, r\.sid\)\)/);
  // delegated on the stable container (actions.ts): a repaint between mousedown and mouseup still lands
  assert.match(SRC, /delegate\(empty, \{\n\s*open: \(x\) => \{ const r = recent\[Number\(x\.dataset\.i\)\]; if \(r\) openHere\(r\.path, r\.sid, r\.identity\); \},/);
  assert.match(SRC, /row\.dataset\.act = "open"; row\.dataset\.i = String\(i\);/);
});

test("close returns to the empty state: the placeholder repaints on the viewer element's removal, never a hidden pane", () => {
  // closeFileView only removes #romp-fileview; the body's childList mutation IS the close event, and one
  // observer covers every open/close path (relay, recent row, browser rows and back, ✕, Esc, Reload)
  assert.match(SRC, /new MutationObserver\(onBodyChange\)\.observe\(document\.body, \{ childList: true \}\);/);
  assert.match(SRC, /function onBodyChange\(\): void \{\n\s*paint\(\);/, "the repaint still rides the observer");
  // "open" is either surface: the viewer OR the browser (2026-09-06, the listing as a column), by element presence
  assert.match(SRC, /const open = surfaceUp\(\);\n\s*empty\.hidden = open;\n\s*if \(open\) return;/);
  assert.match(SRC, /function surfaceUp\(\): boolean \{\n\s*return !!\(document\.getElementById\("romp-fileview"\) \|\| document\.getElementById\("romp-filebrowse"\)\);\n\}/);
  assert.doesNotMatch(SRC, /setInterval|setTimeout/, "event-based, no polling");
});

// The close is also told to the SHELL (the 2026-09-04 review): on a phone the viewFile relay switched tabs
// to show this pane, and closing the file otherwise stranded the person on the Files tab's recent list
// (the feed route resets to chat on viewFileClosed; this pane never posted anything). The shell restores
// the tab the click came from, mobile only (kernel.py filesViewerClosed; tests/test_pane_state_broadcast.py).
test("the viewer's close EDGE posts filesViewerClosed up to the shell — once, framed only, never on an open-over-open", () => {
  // the edge is "nothing left up": a viewer closing back onto the listing beneath it is not a close (2026-09-06)
  assert.match(SRC, /let viewerUp = surfaceUp\(\);/);
  assert.match(SRC, /const up = surfaceUp\(\);\n\s*if \(viewerUp && !up && window\.parent !== window\) window\.parent\.postMessage\(\{ romp: "filesViewerClosed" \}, "\*"\);\n\s*viewerUp = up;/);
  assert.equal((SRC.match(/filesViewerClosed/g) || []).length, 2, "one post site (plus its comment)");
  // executed: the edge detector as the source spells it — a post only on up→down, framed
  const run = (states: boolean[], framed: boolean): number => {
    let viewerUp = states[0], posts = 0;
    for (const up of states.slice(1)) { if (viewerUp && !up && framed) posts++; viewerUp = up; }
    return posts;
  };
  assert.equal(run([false, true, false], true), 1, "open then close → one notice");
  assert.equal(run([false, true, true, false], true), 1, "the Reload replace / open-over-open (still up when the observer runs) is not a close");
  assert.equal(run([false, true, false, true, false], true), 2, "two closes → two notices");
  assert.equal(run([false, false], true), 0, "an unrelated body mutation with nothing open posts nothing");
  assert.equal(run([false, true, false], false), 0, "unframed (no shell): nothing to tell");
});

test("the pane-resident variant is keyed on the page's body class and lives ONLY in the pane sheet", () => {
  assert.match(KERNEL, /<body class=fileview-pane>/);
  assert.ok(CSS.includes("body.fileview-pane #romp-fileview{position:relative;inset:auto;flex:1 1 auto;min-height:0;background:none}"));
  assert.ok(CSS.includes("body.fileview-pane .fileview{width:100%;height:100%;border:0;border-radius:0;box-shadow:none}"));
  // relative, not static: the viewer keeps its z-index, so a file opened from a browser row still paints
  // above the browser's fixed overlay (styles.css .filebrowse) and "‹ Files" has something to go back to
  assert.doesNotMatch(CSS, /position:static/);
  for (const sheet of ["styles.css", "feed.css"]) assert.doesNotMatch(read(sheet), /fileview-pane/, sheet + " stays a mirror");
  for (const sel of ["#files-empty{", ".fs-title{", ".fs-hint{", ".fs-recent{", ".fs-row{"]) assert.ok(CSS.includes(sel), sel);
});

test("wired and vocabulary-clean: esbuild entries, no federation import, no fleet identifiers or prose", () => {
  assert.match(ESBUILD, /"\.\.\/ui\/webview\/files\.ts",/);
  assert.match(ESBUILD, /"\.\.\/ui\/webview\/files-pane\.css",/);
  for (const [name, src] of [["files.ts", SRC], ["files-recent.ts", HELPERS], ["files-pane.css", CSS]] as const) {
    assert.doesNotMatch(src, /from "\.\/federation"/, name + ": importing it boots a second FederationManager");
    assert.doesNotMatch(src, /fleet/i, name + ": no new fleet identifiers or prose (repo vocabulary rule)");
  }
});

// executed: the shell's relay arms, EXTRACTED from kernel.py's landing shell (the file-view.test.ts
// flag-algebra idiom) and run against a shimmed window/document — a `pane:"pane"` click drives the
// Files branch and never touches the feed's flags; the same click without `pane` still takes the feed route
test("the shell's viewFile relay, executed: pane:'pane' brings the Files pane forward and forwards identity; the feed route is untouched", () => {
  const start = KERNEL.indexOf("if(m.romp==='browseFiles'&&m.pane==='pane'){");   // the first browse arm (2026-09-06)
  const stop = KERNEL.indexOf("// One id per dashboard", start);
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
      getElementById: (id: string) => (id in posted ? { contentWindow: { postMessage: (x: unknown) => posted[id].push(x) } } : null),
    };
    const send = (m: unknown) => { armsFn(win, doc, m); return { toggles, tabs, posted, pend: win.__rompFeedWasOffViewPend, from: win.__rompFilesTabFrom }; };
    return { send, win };
  };
  const run = (m: unknown) => shell().send(m);
  const identity = { name: "web", color: { bg: "#123456", fg: "#ffffff" } };
  const pane = run({ romp: "viewFile", pane: "pane", path: "/repo/notes-api/src/app.py", sid: SID, identity });
  assert.deepEqual(pane.toggles, [["files", true]], "the Files pane comes forward; the feed is not touched");
  assert.deepEqual(pane.tabs, [], "DESKTOP: no mobile tab switch — the column is already visible, and show() would only persist a stale romp-mobile-tab");
  assert.equal(pane.from, undefined, "…and nothing to remember");
  assert.deepEqual(pane.posted["f-files"], [{ romp: "viewFile", path: "/repo/notes-api/src/app.py", sid: SID, identity, todoId: null }],
    "a chat click names no todo — the pane sees null, never undefined");
  assert.deepEqual(pane.posted["f-feed"], [], "nothing reaches the feed");
  // a Waiting-on-you detail link names the todo the path came from (plans/file-review.md Slice 0); forwarded as-is
  const fromTodo = run({ romp: "viewFile", pane: "pane", path: "docs/design.md", sid: SID, identity, todoId: "t1" });
  assert.deepEqual(fromTodo.posted["f-files"], [{ romp: "viewFile", path: "docs/design.md", sid: SID, identity, todoId: "t1" }]);
  assert.equal(pane.pend, undefined, "the feed's was-off stash is never armed by the Files route");
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
  // the feed route: a click with pane:"feed" (or none) takes the else branch exactly as before
  for (const m of [{ romp: "viewFile", pane: "feed", path: "/p", sid: SID }, { romp: "viewFile", path: "/p", sid: SID }]) {
    const feed = run(m);
    assert.deepEqual(feed.posted["f-feed"], [{ romp: "viewFile", path: "/p", sid: SID }]);
    assert.deepEqual(feed.posted["f-files"], []);
    assert.deepEqual(feed.tabs, ["feed"]);
    assert.equal(feed.pend, false, "the feed pane was on, so nothing is stashed — but the stash IS written by this route");
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
    { path: "/repo/notes-api/a.md", sid: SID, identity: { name: "web", color: { bg: "#123456", fg: "#fff" } }, t: 5 },
    { path: "/repo/notes-api/b.md", sid: null, identity: null, t: 0 },
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
  assert.equal(asIdentity({ color: { bg: "#123456", fg: "#fff" } }), null, "no name, no chip — never invented");
  assert.equal(asIdentity(null), null);
  assert.equal(asIdentity("web"), null);
});

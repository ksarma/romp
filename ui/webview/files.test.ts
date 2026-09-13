// The "Files" pane (files.ts): the file VIEWER as its own column of the dashboard, hosting the shared
// viewer pane-resident, with an empty state that lists the files most recently open there. No jsdom
// harness, so the wiring is pinned at source (the waiting.test.ts idiom); the pure half — the recent
// list and the relayed identity's validation (files-recent.ts) — runs for real.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { asIdentity, asPlace, parseRecent, rememberRecent, placeRecent, RECENT_MAX, type RecentFile, type RecentPlace } from "./files-recent";

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

test("the pane hosts the shared viewer and takes the shell's relay WHOLE: its own contract, not the feed's", () => {
  // initFileView's second argument replaces the default relay branch — the feed's viaRelay + ack —
  // for this document; the pane owes the shell no pane restore, it stays up
  assert.match(SRC, /initFileView\(\(m\) => vscodeApi\?\.postMessage\(m\), \(m\) => \{\n\s*openHere\(m\.path, typeof m\.sid === "string" \? m\.sid : null, asIdentity\(m\.identity\), typeof m\.todoId === "string" \? m\.todoId : null, readAt\(m\.at\)\);\n\}, \{/,
    "…and the link's target the relay carries, validated by the viewer's readAt (it crossed a frame; Slice 6 of plans/markdown-viewer.md)");
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
  // readAt (file-view.ts): the receiver's validation of the relay's `at` (Slice 6 of plans/markdown-viewer.md); a stand-in here
  // that passes an object through and refuses the rest, so the branch's call shape is what is under test, not the validator
  const readAt = (x: unknown) => (x && typeof x === "object" ? x : null);
  const fn = new Function("m", "onRelay", "openFileView", "window", "readAt", body) as
    (m: unknown, onRelay: ((m: unknown) => void) | undefined, open: (p: string, sid: string | null, opts: unknown) => boolean, w: unknown, readAt: (x: unknown) => unknown) => boolean;
  const run = (m: unknown, onRelay: ((m: unknown) => void) | undefined, verdict = true) => {
    const opened: Array<[string, string | null, unknown]> = [], posted: unknown[] = [];
    const win = { parent: { postMessage: (x: unknown) => posted.push(x) } };   // embedded: parent !== window
    const viaRelay = fn(m, onRelay, (p, sid, opts) => { opened.push([p, sid, opts]); return verdict; }, win, readAt);
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
  assert.deepEqual(feed.opened, [["/repo/notes-api/src/app.py", SID, { at: null }]], "no contract of its own: the feed route opens, with no target");
  const aimed = run({ ...msg, at: { heading: "results" } }, undefined);
  assert.deepEqual(aimed.opened, [["/repo/notes-api/src/app.py", SID, { at: { heading: "results" } }]], "…and with the relay's target, read through readAt (C1)");
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
  assert.ok(openFn.indexOf("identities.set(sid, identity);") >= 0 && openFn.indexOf("openFileView(path, sid, { todoId, at, place })") >= 0
    && openFn.indexOf("identities.set(sid, identity);") < openFn.indexOf("openFileView(path, sid, { todoId, at, place })"),
    "the cache is filled BEFORE the open, so the title bar's chip resolves on the first paint");
  assert.match(openFn, /if \(sid && identity\) identities\.set\(sid, identity\);/);
  assert.doesNotMatch(SRC, /sessionsMeta|tabMeta|sessions\.get/, "the pane has no session list of its own");
});

test("recent files: recorded only on a REAL open, painted as re-open rows in the viewer's own dress, click-safe", () => {
  const openFn = SRC.split("function openHere(")[1].split("\n}")[0];
  assert.match(openFn, /if \(!openFileView\(path, sid, \{ todoId, at, place \}\)\) return;\n\s*const known = /, "a dirty-edit veto records nothing");
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
  assert.match(openFn, /const place = recent\.find\(\(r\) => r\.path === path && r\.sid === sid\)\?\.place \?\? null;[^\n]*\n\s*if \(!openFileView\(path, sid, \{ todoId, at, place \}\)\) return;/,
    "openHere reads the row's record itself, before the open, and hands it to the viewer on EVERY open of the path (the Slice 6 review, round 1: the relay's open after a reload landed at the top)");
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
  assert.deepEqual(pane.posted["f-files"], [{ romp: "viewFile", path: "/repo/notes-api/src/app.py", sid: SID, identity, todoId: null, at: null }],
    "a chat click names no todo and no target: the pane sees null, never undefined");
  assert.deepEqual(pane.posted["f-feed"], [], "nothing reaches the feed");
  // a Waiting-on-you detail link names the todo the path came from (plans/file-review.md Slice 0); forwarded as-is
  const fromTodo = run({ romp: "viewFile", pane: "pane", path: "docs/design.md", sid: SID, identity, todoId: "t1" });
  assert.deepEqual(fromTodo.posted["f-files"], [{ romp: "viewFile", path: "docs/design.md", sid: SID, identity, todoId: "t1", at: null }]);
  // a todo link's target after its path (Slice 6 of plans/markdown-viewer.md): the forwarder copies `at` WHOLE, whatever
  // its shape (the receiver validates it, file-view.ts readAt; files.ts hands readAt(m.at) to the open); both forwarders
  // rebuild the message field by field, so a field not copied is dropped in transit
  for (const at of [{ heading: "results" }, { line: 12 }, { offset: 400 }, { bogus: 1 }]) {
    const aimed = run({ romp: "viewFile", pane: "pane", path: "docs/report.md", sid: SID, identity, todoId: "t1", at });
    assert.deepEqual((aimed.posted["f-files"][0] as any).at, at, "the Files branch forwards at " + JSON.stringify(at));
    const feedAimed = run({ romp: "viewFile", pane: "feed", path: "docs/report.md", sid: SID, at });
    assert.deepEqual(feedAimed.posted["f-feed"], [{ romp: "viewFile", path: "docs/report.md", sid: SID, at }], "the feed branch forwards at too");
  }
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
    assert.deepEqual(feed.posted["f-feed"], [{ romp: "viewFile", path: "/p", sid: SID, at: null }]);
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
  assert.equal(asIdentity({ color: { bg: "#123456", fg: "#fff" } }), null, "no name, no chip — never invented");
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
  assert.deepEqual(asPlace({ ...PLACE, source: "lorem ipsum", text: "dolor" }), PLACE, "a stray text field is dropped on read: nothing but the eight fields reaches the store");
  assert.deepEqual(asPlace({ ...PLACE, top: 0, scrollTop: 0, atTop: true, view: "raw" }), { ...PLACE, top: 0, scrollTop: 0, atTop: true, view: "raw" }, "the top of a file in the Raw view is a place too");
  assert.equal(asPlace(null), null); assert.equal(asPlace(PLACE.start), null); assert.equal(asPlace({ ...PLACE, end: Infinity }), null);
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
  // the record's JSON, as localStorage will hold it: the eight fields and nothing that could hold the file's text
  const json = JSON.stringify(placed[0]);
  assert.deepEqual(Object.keys(JSON.parse(json).place).sort(), ["atTop", "end", "mtimeNs", "scrollTop", "start", "t", "top", "view"]);
  assert.doesNotMatch(json, /source|text|quote|lorem/, "no text field, no quote");
});

// EXECUTED: openHere as files.ts spells it, its body lifted from the source (the signature's types stripped) and run over
// stubs for the viewer's open, the store and the paint, with the real list functions. The Slice 6 review's round 1: the
// row's click alone passed the row's place, so after a page reload (the viewer's in-page map empty) a chat click on a
// file whose row held a record opened it at the top, and that open's leave wrote the top over the row. Every open through
// openHere now hands the row's record back; the viewer seats the later of that and its own (file-view.ts newerPlace) and
// ignores both under an `at` (openFileView's doc), so the pane hands it over regardless.
test("openHere, executed: every open of a path with a row hands the row's place to the viewer (the relay, a link, the row's click), none for another session's row or a path with none; a veto records nothing; the row keeps a fresher record its leave wrote during the open", () => {
  const src = SRC.split("function openHere(")[1].split("\n}")[0];
  const sig = src.slice(0, src.indexOf("{") + 1);
  const js = "function openHere(" + sig.replace(/: [A-Za-z]+(?: \| null)?/g, "") + src.slice(src.indexOf("{") + 1) + "\n}";   // the source's own parameters, their types stripped
  const opens: unknown[][] = []; const writes: number[] = []; const paints: number[] = [];
  const last = () => opens[opens.length - 1];
  let veto = false;
  let leaveOnOpen: (() => void) | null = null;   // the viewer's runLeave on a replace-open reaches the host's onLeave BEFORE openFileView returns
  const identities = new Map<string, unknown>();
  const world = new Function("openFileView", "rememberRecent", "writeStore", "paint", "identities", "list",
    "let recent = list; " + js + " return { openHere, get recent() { return recent; }, set recent(v) { recent = v; } };")(
    (p: string, sid: string | null, opts: unknown) => { opens.push([p, sid, opts]); if (leaveOnOpen) { const f = leaveOnOpen; leaveOnOpen = null; f(); } return !veto; },
    rememberRecent, () => { writes.push(1); }, () => { paints.push(1); }, identities,
    [row("/repo/notes-api/docs/notes.md", SID2, "api", 3), row("/repo/notes-api/docs/report.md", SID, "web", 2, PLACE), row("/repo/notes-api/docs/design.md", SID, "web", 1)],
  ) as { openHere: (p: string, sid: string | null, id: unknown, todoId?: string | null, at?: unknown) => void; recent: RecentFile[] };
  const identity = { name: "web", color: { bg: "#123456", fg: "#ffffff" } };
  // the shell's relay (a chat click) after a reload: no place in hand, the row's record rides
  world.openHere("/repo/notes-api/docs/report.md", SID, identity, null, null);
  assert.deepEqual(last(), ["/repo/notes-api/docs/report.md", SID, { todoId: null, at: null, place: PLACE }], "the relay's open hands the row's record back");
  assert.deepEqual(world.recent.map((r) => [r.path, r.place]), [["/repo/notes-api/docs/report.md", PLACE], ["/repo/notes-api/docs/notes.md", null], ["/repo/notes-api/docs/design.md", null]], "the row moves up and keeps its place");
  assert.equal(writes.length, 1); assert.equal(paints.length, 1);
  // a link inside a shown file (no identity in hand; the cache the relay filled names the chip): the same record
  world.openHere("/repo/notes-api/docs/report.md", SID, null, null, null);
  assert.deepEqual(last(), ["/repo/notes-api/docs/report.md", SID, { todoId: null, at: null, place: PLACE }], "a link's open too");
  assert.deepEqual(world.recent[0].identity, identity, "the chip's identity from the cache");
  // the row's click: the same call, the same record (one source, the store)
  world.openHere("/repo/notes-api/docs/report.md", SID, identity);
  assert.deepEqual((last()[2] as { place: unknown }).place, PLACE, "the row's click");
  // rows are per path + session: another session's open of the same path finds no record of its own
  world.openHere("/repo/notes-api/docs/report.md", SID2, null);
  assert.deepEqual(last(), ["/repo/notes-api/docs/report.md", SID2, { todoId: null, at: null, place: null }], "another session's row is another row");
  assert.deepEqual(world.recent.map((r) => [r.sid, r.place]), [[SID2, null], [SID, PLACE], [SID2, null], [SID, null]], "a new row for it; the first session's place stands");
  // a path with no row: nothing to hand back
  world.openHere("/repo/notes-api/README.md", SID, null);
  assert.deepEqual((last()[2] as { place: unknown }).place, null);
  // an `at` open (a todo's target): the pane hands the record all the same; the viewer lands on the target and ignores it
  world.openHere("/repo/notes-api/docs/report.md", SID, null, "t1", { heading: "results" });
  assert.deepEqual(last(), ["/repo/notes-api/docs/report.md", SID, { todoId: "t1", at: { heading: "results" }, place: PLACE }]);
  // the same file opened over itself: the viewer's leave writes a fresher record on the row DURING the open; the pane read
  // the row before it and hands the older one (the viewer seats the later of the two), and the row keeps the fresh record
  // afterwards, since the entry openHere writes brings none
  const fresh: RecentPlace = { ...PLACE, start: 2000, end: 2300, scrollTop: 5000, t: 9 };
  leaveOnOpen = () => { world.recent = placeRecent(world.recent, "/repo/notes-api/docs/report.md", SID, fresh); };
  world.openHere("/repo/notes-api/docs/report.md", SID, null);
  assert.deepEqual((last()[2] as { place: unknown }).place, PLACE, "read before the open");
  assert.deepEqual(world.recent[0].place, fresh, "the leave's fresher record stands on the row");
  // a dirty-edit veto: the open did not happen, so nothing is recorded, written or painted
  const n = opens.length, w = writes.length, k = paints.length, before = world.recent;
  veto = true;
  world.openHere("/repo/notes-api/docs/notes.md", SID2, null);
  assert.equal(opens.length, n + 1); assert.equal(writes.length, w); assert.equal(paints.length, k); assert.equal(world.recent, before, "the list is untouched");
  // the shape that makes this so: five parameters and no `place`, the row's record read inside, so no caller can pass a stale one or forget it
  assert.equal(sig, "path: string, sid: string | null, identity: FileViewIdentity | null, todoId: string | null = null, at: At | null = null): void {");
});

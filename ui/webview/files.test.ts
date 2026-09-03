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
  assert.match(SRC, /initFileView\(\(m\) => vscodeApi\?\.postMessage\(m\), \(m\) => \{\n\s*openHere\(m\.path, typeof m\.sid === "string" \? m\.sid : null, asIdentity\(m\.identity\)\);\n\}\);/);
  assert.match(SRC, /initFileBrowse\(\(m\) => vscodeApi\?\.postMessage\(m\)\);/, "the browser opens here too");
  assert.match(VIEW, /onRelay\?: \(m: \{ path: string; sid\?: unknown; identity\?: unknown \}\) => void\): void \{/);
  const relayBranch = VIEW.split('if (m.romp === "viewFile"')[1].split("} else if")[0];
  assert.ok(relayBranch.indexOf("if (onRelay) { onRelay(m); return; }") < relayBranch.indexOf("viaRelay = true;"),
    "a document's own contract takes the message before the feed's arms run");
  const code = SRC.replace(/^\s*\/\/.*$/gm, "");   // the header names the feed's contract to say the pane has none; the code must not touch it
  assert.doesNotMatch(code, /viaRelay|viewFileOpened|viewFileClosed|__rompFeedWasOff/, "none of the feed route's restore machinery");
  // not a feed consumer: no frame parsing of any kind
  assert.doesNotMatch(SRC, /m\.type === "feed"|feedDelta|userTodoRows|ledgers|\.asks\b|needFullFeed/);
  assert.match(SRC, /vscodeApi\?\.postMessage\(\{ type: "ready" \}\)/, "the ready handshake lifts the shim's hold");
});

test("the session chip resolves from what the relay carried, cached per sid, else the kernel's stub", () => {
  assert.match(SRC, /setFileViewIdentity\(\(id\) => identities\.get\(id\) \?\? hostStub\(id\)\);/);
  const openFn = SRC.split("function openHere(")[1].split("\n}")[0];
  assert.ok(openFn.indexOf("identities.set(sid, identity);") < openFn.indexOf("openFileView(path, sid)"),
    "the cache is filled BEFORE the open, so the title bar's chip resolves on the first paint");
  assert.match(openFn, /if \(sid && identity\) identities\.set\(sid, identity\);/);
  assert.doesNotMatch(SRC, /sessionsMeta|tabMeta|sessions\.get/, "the pane has no session list of its own");
});

test("recent files: recorded only on a REAL open, painted as re-open rows in the viewer's own dress, click-safe", () => {
  const openFn = SRC.split("function openHere(")[1].split("\n}")[0];
  assert.match(openFn, /if \(!openFileView\(path, sid\)\) return;\n\s*const known = /, "a dirty-edit veto records nothing");
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
  assert.match(SRC, /new MutationObserver\(paint\)\.observe\(document\.body, \{ childList: true \}\);/);
  assert.match(SRC, /const open = !!document\.getElementById\("romp-fileview"\);\n\s*empty\.hidden = open;\n\s*if \(open\) return;/);
  assert.doesNotMatch(SRC, /setInterval|setTimeout/, "event-based, no polling");
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

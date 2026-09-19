// The viewer's navigation trail as pure functions (file-trail.ts; plans/markdown-viewer.md, "Follow-on: Link
// navigation", L1 and L2): a push from inside the viewer puts the shown file behind and clears the steps ahead, a root
// starts over, back and forward step through the lists and move the shown file to the other side, an entry records
// the view the reader left it in, an empty trail steps nowhere, the chord table names the two steps and refuses every
// other modifier, and the buttons' titles name the target file. The wiring into the viewer is pinned at source in the
// second half (the one tag the viewer's own openers set and openFileView reads, both exits ending the trail, the
// conflict Reload keeping it, the capture-phase chord listener leaving with the viewer); the browser leg,
// file-trail-browser.test.ts, drives the real viewer. Synthetic values only: the notes-api world, a placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { EMPTY_TRAIL, trailRoot, trailPush, trailBack, trailForward, trailSetView, trailEnd, trailBackTarget, trailForwardTarget,
  fileNameOf, navTitle, navChord, liveTrail, setTrail, type TrailEntry, type TrailState } from "./file-trail";

const web = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const VIEW = web("file-view.ts");
const ICONS = web("icons.ts");

const SID = "11111111-2222-3333-4444-555555555555";
const A: TrailEntry = { path: "/repo/notes-api/docs/report.md", sid: SID, view: null };
const B: TrailEntry = { path: "/repo/notes-api/docs/notes.md", sid: SID, view: null };
const C: TrailEntry = { path: "/repo/notes-api/docs/figs/plot.svg", sid: SID, view: null };
const paths = (l: TrailEntry[]) => l.map((e) => fileNameOf(e.path));
const shape = (s: TrailState) => ({ back: paths(s.back), current: s.current ? fileNameOf(s.current.path) : null, forward: paths(s.forward) });

test("a root starts a trail with one file and nothing behind or ahead; a push puts the shown file behind; a second push lengthens the list behind", () => {
  const r = trailRoot(A);
  assert.deepEqual(shape(r), { back: [], current: "report.md", forward: [] });
  assert.equal(trailBackTarget(r), null); assert.equal(trailForwardTarget(r), null);
  const p1 = trailPush(r, B);
  assert.deepEqual(shape(p1), { back: ["report.md"], current: "notes.md", forward: [] });
  assert.deepEqual(trailBackTarget(p1), A);
  const p2 = trailPush(p1, C);
  assert.deepEqual(shape(p2), { back: ["report.md", "notes.md"], current: "plot.svg", forward: [] });
  assert.deepEqual(shape(r), { back: [], current: "report.md", forward: [] }, "pure: the root state is unchanged by the pushes");
});

test("back moves the shown file ahead and the nearest behind into view; forward mirrors it; the two are inverses over a three-file trail", () => {
  const s = trailPush(trailPush(trailRoot(A), B), C);
  const b1 = trailBack(s);
  assert.deepEqual(shape(b1), { back: ["report.md"], current: "notes.md", forward: ["plot.svg"] });
  assert.deepEqual(trailForwardTarget(b1), C);
  const b2 = trailBack(b1);
  assert.deepEqual(shape(b2), { back: [], current: "report.md", forward: ["notes.md", "plot.svg"] });
  assert.equal(trailBackTarget(b2), null, "nothing behind the root");
  assert.deepEqual(shape(trailForward(b2)), shape(b1), "forward undoes the last back");
  assert.deepEqual(shape(trailForward(trailForward(b2))), shape(s), "and the second forward reaches the end again");
  assert.deepEqual(shape(s), { back: ["report.md", "notes.md"], current: "plot.svg", forward: [] }, "pure: the input is unchanged");
});

test("a push after a back clears the list ahead (a new branch replaces the steps ahead, as a browser's history does)", () => {
  const s = trailBack(trailPush(trailPush(trailRoot(A), B), C));   // on notes.md, plot.svg ahead
  const p = trailPush(s, { path: "/repo/notes-api/docs/guide.md", sid: SID, view: null });
  assert.deepEqual(shape(p), { back: ["report.md", "notes.md"], current: "guide.md", forward: [] });
  assert.equal(trailForwardTarget(p), null);
});

test("an empty trail steps nowhere and stays empty; a push onto no trail is a root; a root over a trail drops it", () => {
  assert.equal(trailBack(EMPTY_TRAIL), EMPTY_TRAIL, "back over nothing is the same state");
  assert.equal(trailForward(EMPTY_TRAIL), EMPTY_TRAIL);
  assert.deepEqual(shape(trailPush(EMPTY_TRAIL, A)), { back: [], current: "report.md", forward: [] });
  const s = trailBack(trailPush(trailPush(trailRoot(A), B), C));
  assert.deepEqual(shape(trailRoot(B)), { back: [], current: "notes.md", forward: [] });
  assert.deepEqual(shape(s), { back: ["report.md"], current: "notes.md", forward: ["plot.svg"] }, "the old state is not touched by a root built beside it");
  const atEnd = trailPush(trailRoot(A), B);
  assert.deepEqual(trailForward(atEnd), atEnd, "forward at the end of the trail is the same state");
  assert.deepEqual(trailBack(trailRoot(A)), trailRoot(A), "back at the root is the same state");
});

test("trailEnd is the empty trail; the live instance starts empty and follows setTrail", () => {
  assert.deepEqual(trailEnd(), { back: [], current: null, forward: [] });
  assert.equal(liveTrail(), EMPTY_TRAIL, "the module's instance before any open");
  const s = trailPush(trailRoot(A), B);
  assert.equal(setTrail(s), s);
  assert.equal(liveTrail(), s);
  setTrail(trailEnd());
  assert.deepEqual(liveTrail(), EMPTY_TRAIL);
});

test("the view the reader left a file in is recorded on the current entry and rides with it behind and ahead; null records nothing; no current entry, no change", () => {
  const s = trailSetView(trailRoot(A), "raw");
  assert.equal(s.current!.view, "raw");
  assert.equal(A.view, null, "the input entry is not mutated");
  const p = trailPush(s, B);
  assert.equal(p.back[0].view, "raw", "the recorded view travels with the entry behind");
  assert.equal(p.current!.view, null, "a freshly opened file has no leave yet");
  const b = trailBack(trailSetView(p, "rendered"));
  assert.equal(b.current!.view, "raw", "back reaches the entry with its view, to open it in that view");
  assert.equal(b.forward[0].view, "rendered", "and the file just left carries the view it was left in");
  assert.equal(trailSetView(p, null), p, "null leaves the state as it is");
  assert.equal(trailSetView(EMPTY_TRAIL, "raw"), EMPTY_TRAIL, "nothing current, nothing to record");
});

test("the titles: the word and the target's file name, or the word alone when there is no target; a nameless path is given whole", () => {
  assert.equal(fileNameOf("/repo/notes-api/docs/report.md"), "report.md");
  assert.equal(fileNameOf("notes.md"), "notes.md");
  assert.equal(fileNameOf("~/docs/figs/plot.svg"), "plot.svg");
  assert.equal(fileNameOf("/repo/notes-api/docs/"), "/repo/notes-api/docs/", "a path ending in a slash names no file: given whole rather than as an empty title");
  assert.equal(navTitle("back", A), "Back to report.md");
  assert.equal(navTitle("forward", B), "Forward to notes.md");
  assert.equal(navTitle("back", null), "Back");
  assert.equal(navTitle("forward", null), "Forward");
});

test("the chord table: Alt+Left and Alt+Right on every platform, Cmd+[ and Cmd+] on a Mac only, and any other modifier held with them asks nothing", () => {
  const k = (key: string, mods: Partial<{ altKey: boolean; metaKey: boolean; ctrlKey: boolean; shiftKey: boolean }> = {}) =>
    ({ key, altKey: false, metaKey: false, ctrlKey: false, shiftKey: false, ...mods });
  for (const mac of [false, true]) {
    assert.equal(navChord(k("ArrowLeft", { altKey: true }), mac), "back", "Alt+Left, mac=" + mac);
    assert.equal(navChord(k("ArrowRight", { altKey: true }), mac), "forward", "Alt+Right, mac=" + mac);
    assert.equal(navChord(k("ArrowLeft"), mac), null, "a bare arrow scrolls, it does not navigate");
    assert.equal(navChord(k("ArrowLeft", { altKey: true, shiftKey: true }), mac), null, "Alt+Shift+Left is another chord");
    assert.equal(navChord(k("ArrowLeft", { altKey: true, ctrlKey: true }), mac), null);
    assert.equal(navChord(k("ArrowLeft", { altKey: true, metaKey: true }), mac), null);
    assert.equal(navChord(k("ArrowUp", { altKey: true }), mac), null);
    assert.equal(navChord(k("[", { ctrlKey: true }), mac), null, "Ctrl+[ is nobody's history chord");
    assert.equal(navChord(k("[", { metaKey: true, shiftKey: true }), mac), null);
    assert.equal(navChord(k("[", { metaKey: true, altKey: true }), mac), null);
    assert.equal(navChord(k("Escape"), mac), null);
  }
  assert.equal(navChord(k("[", { metaKey: true }), true), "back", "Cmd+[ on a Mac");
  assert.equal(navChord(k("]", { metaKey: true }), true), "forward", "Cmd+] on a Mac");
  assert.equal(navChord(k("[", { metaKey: true }), false), null, "Meta+[ elsewhere is the OS's, not the viewer's");
  assert.equal(navChord(k("]", { metaKey: true }), false), null);
});

// ── the wiring into the viewer, at source (the browser leg executes it) ────────────────────────────
test("the viewer's own openers set ONE tag that openFileView reads and clears before its close guard, so every untagged open is outside by construction", () => {
  assert.match(VIEW, /import \{ [^}]*liveTrail[^}]*\} from "\.\/file-trail";/, "file-view.ts imports the trail module");
  assert.match(VIEW, /^let trailNext: TrailHow \| null = null;$/m, "the tag: module-level, one at a time");
  assert.match(VIEW, /^function openFromViewer\(how: TrailHow, path: string, sid: string \| null, at: At \| null\): void \{\n  trailNext = how;\n  try \{ openLinkedFile\(path, sid, at\); \} finally \{ trailNext = null; \}\n\}$/m,
    "the one door for the viewer's own opens: the tag is set, the host's or the default opener runs, and the tag is cleared whatever happened (a host that never reached openFileView must not leave it armed)");
  const open = VIEW.slice(VIEW.indexOf("export function openFileView("), VIEW.indexOf("  const wrap = el(\"div\");\n  wrap.id = \"romp-fileview\";"));
  assert.ok(open.indexOf("const how = trailNext; trailNext = null;") >= 0, "openFileView takes the tag");
  assert.ok(open.indexOf("const how = trailNext; trailNext = null;") < open.indexOf("if (document.getElementById(\"romp-fileview\") && closeGuard && !closeGuard()) return false;"),
    "before the close guard, so a vetoed open never leaves a stale tag for the next one");
  assert.ok(open.indexOf("runLeave();") < open.indexOf("moveTrail(how,"), "the trail moves after runLeave wrote the leaving file's place, whose view the entry records");
  // the body delegate's path-link open and the Back and Forward controls are the callers; the delegate calls nothing else on openLinkedFile
  assert.match(VIEW, /openFromViewer\("push", p, sid \|\| null, ln > 0 \? \{ line: ln \} : x\.dataset\.frag \? \{ heading: x\.dataset\.frag \} : null\);/, "the delegate's path link is a push");
  assert.equal((VIEW.match(/openLinkedFile\(/g) || []).length, 1, "openLinkedFile is called from openFromViewer alone (its declaration is a type annotation, not a call)");
  assert.match(VIEW, /openFromViewer\(dir, target\.path, target\.sid, null\);/, "Back and Forward re-open their entry with NO target, so the remembered place re-seats it");
});

test("both exits end the trail after their guards, the URL viewer's replace ends it too, and the conflict Reload keeps it", () => {
  const close = VIEW.slice(VIEW.indexOf("export function closeFileView("), VIEW.indexOf("export function openFileClick("));
  assert.ok(close.indexOf("if (closeGuard && !closeGuard()) return;") < close.indexOf("setTrail(trailEnd());"), "closeFileView ends the trail once the close is happening (a vetoed close keeps it)");
  const url = VIEW.slice(VIEW.indexOf("export function openUrlView("), VIEW.indexOf("  const wrap = el(\"div\");", VIEW.indexOf("export function openUrlView(")));
  assert.ok(url.indexOf("closeGuard && !closeGuard()) return;") < url.indexOf("setTrail(trailEnd());"), "a URL document replacing the viewer ends the trail (its entries are files; a URL is none)");
  assert.match(VIEW, /trailNext = "reload"; openFileView\(path, sid, opts\);/, "the conflict Reload re-opens the same file as the same entry: the trail stands");
  assert.match(VIEW, /case "reload": setTrail\(s\); return null;/, "moveTrail: a reload records the leaving view and moves nothing");
});

test("the two glyph buttons stand first in the bar with the icon family's drawings, aria-disabled alone when empty; the chord listener is capture-phase, stands down for a prevented key or a typing target, and leaves with the viewer", () => {
  assert.match(ICONS, /^export const ICON_BACK = svg\(/m); assert.match(ICONS, /^export const ICON_FORWARD = svg\(/m);
  assert.match(VIEW, /import \{ ICON_DOWNLOAD, ICON_COPY, ICON_EDIT, ICON_ZOOM, ICON_CHECK, ICON_CROSS, ICON_BACK, ICON_FORWARD \} from "\.\/icons";/);
  assert.match(VIEW, /const nav = el\("span", "fileview-group fileview-nav"\);/);
  assert.match(VIEW, /b\.innerHTML = dir === "back" \? ICON_BACK : ICON_FORWARD; b\.dataset\.icon = "1";/);
  assert.match(VIEW, /if \(!target\) b\.setAttribute\("aria-disabled", "true"\);/, "the bar's precedent (the text-size ends): aria-disabled, never disabled, so the keyboard focus stays");
  assert.match(VIEW, /bar\.appendChild\(nav\);\n  \/\/ BACK to the listing/, "the nav group is the bar's first child; the pane's Files link follows it and keeps its meaning");
  assert.match(VIEW, /back\.textContent = "‹ Files"; back\.title = "Back to the file listing";/, "unchanged");
  assert.match(VIEW, /document\.addEventListener\("keydown", onNavKey, true\);\n  closeHooks\.push\(\(\) => document\.removeEventListener\("keydown", onNavKey, true\)\);/,
    "installed with the viewer, removed by both exits through the close hooks (runCloseHooks)");
  const nav = VIEW.slice(VIEW.indexOf("const onNavKey = (e: KeyboardEvent) => {"), VIEW.indexOf("document.addEventListener(\"keydown\", onNavKey, true);"));
  assert.ok(nav.includes("if (e.defaultPrevented || !document.getElementById(\"romp-fileview\")) return;"), "a key another listener already took, or no viewer: nothing");
  assert.ok(nav.includes("const dir = navChord(e, IS_MAC);"), "the chord table decides");
  assert.ok(nav.includes("if (a && a !== document.body && isTypingTarget(a)) return;"), "a text field keeps its own Alt+Left (the caret) and Cmd+[");
  assert.ok(nav.includes("e.preventDefault();"), "the browser's history step is taken over while the viewer is open, target or none");
});

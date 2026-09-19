// The viewer's navigation trail as pure functions (file-trail.ts; plans/markdown-viewer.md, "Follow-on: Link
// navigation", L1 and L2): a push from inside the viewer puts the shown file behind and clears the steps ahead, a root
// starts over, back and forward step through the lists and move the shown file to the other side, an entry records
// the view the reader left it in, an empty trail steps nowhere, the chord table names the two steps and refuses every
// other modifier, and the buttons' titles name the target file. The wiring into the viewer is pinned at source in the
// second half (the one tag the viewer's own openers set and openFileView reads, both exits ending the trail, the
// conflict Reload keeping it, the capture-phase chord listener leaving with the viewer); the browser leg,
// file-trail-browser.test.ts, drives the real viewer through its links, its buttons and its chords. The one road that leg
// never takes, the conflict bar's Reload file, is driven for real at the end of this module, in Chromium through
// real-viewer-leg.ts (a link push, Edit, a change, a Save refused as changed on disk, Reload file, and the bar read back),
// so a Reload re-routed around the tagged open fails by execution and not only where the source pins look. Synthetic
// values only: the notes-api world, a placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { EMPTY_TRAIL, trailRoot, trailPush, trailBack, trailForward, trailSetView, trailEnd, trailBackTarget, trailForwardTarget,
  fileNameOf, navTitle, navChord, liveTrail, setTrail, type TrailEntry, type TrailState } from "./file-trail";
import { inBrowser, openViewer, frames, ROOT, REPORT } from "./real-viewer-leg";

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
  assert.match(VIEW, /trailNext = "reload"; openFileView\(path, sid, opts\);/, "the conflict Reload re-opens the same file as the same entry: the trail stands (driven for real in the Chromium case at the end of this module)");
  assert.match(VIEW, /case "reload": setTrail\(s\); return null;/, "moveTrail: a reload records the leaving view and moves nothing");
});

test("the two glyph buttons stand first in the bar with the icon family's drawings, aria-disabled alone when empty; the chord listener is capture-phase, stands down for a prevented key or a typing target, and leaves with the viewer", () => {
  assert.match(ICONS, /^export const ICON_BACK = svg\(/m); assert.match(ICONS, /^export const ICON_FORWARD = svg\(/m);
  assert.match(VIEW, /import \{ ICON_DOWNLOAD, ICON_COPY, ICON_EDIT, ICON_ZOOM, ICON_CHECK, ICON_CROSS, ICON_BACK, ICON_FORWARD, ICON_EXPAND \} from "\.\/icons";/);   // the two arrows beside the bar's glyphs (and, since L3, the figure control's)
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

// ── the conflict Reload, driven in Chromium ────────────────────────────────────────────────────────
// The one road the source pins above held alone: the two Reload lines and moveTrail's reload arm say a Reload file after a
// refused save re-opens the same file as the same entry, so Back still names the file the link was followed from, but no
// leg pressed the button (file-view-notice.test.ts and its siblings press it over a shim and read the card, never the
// trail). This case drives it through the real viewer in the chat modal (real-viewer-leg.ts; the viewer's default opener):
// a link push, Edit, a change, a Save the kernel refuses as changed on disk, Reload file behind a discard ask answered yes,
// and the fresh card's Back read back; then Back itself, to show the entry behind is live and the reloaded file went
// ahead. A Reload re-routed through closeFileView (the trail ends), or through an untagged open (the trail roots), leaves
// both pinned lines in place and fails here at the fresh card's Back. Skips LOUDLY without a playwright browser (CI
// installs none), as every browser leg does.
const NOTES = ROOT + "/docs/notes.md";
const REPORT_TEXT = "# Report\n\nRead [the notes](./notes.md) before the results.\n\n"
  + Array.from({ length: 6 }, (_, i) => `Paragraph ${i + 1}: a line of the report.`).join("\n\n") + "\n";
const NOTES_TEXT = "# Notes\n\nBack to [the report](report.md).\n\nNote 1: a short line of notes.\n";
type NavRead = { title: string; disabled: string | null } | null;

test("in a browser, the conflict bar's Reload file keeps the trail: after a link push, Edit, a change and a Save refused as changed on disk, Reload file re-opens the notes fresh with Back still titled with the report's name, and Back then returns to the report with the reloaded notes ahead", async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openViewer(browser, "chat", 900, 520, { docs: { [REPORT]: REPORT_TEXT, [NOTES]: NOTES_TEXT } });
    // an untracked file: Save posts saveFile to the kernel and the refusal arrives as a fileSaveFailed message (a tracked
    // file saves through the comments host instead; file-view-keyboard-frames-browser.test.ts sets the same status)
    await page.evaluate(() => { const w = window as any; w.__status = { ...w.__status, trackedBy: null, store: null, storePath: null, storeMtimeNs: null }; });
    // what the case reads: the two buttons' titles and aria-disabled, as strings, and the bar's file name
    const nav = (): Promise<{ back: NavRead; forward: NavRead }> => page.evaluate(() => {
      const read = (dir: string) => { const b = document.querySelector("#romp-fileview .fileview-nav-" + dir) as HTMLButtonElement | null; return b ? { title: b.title, disabled: b.getAttribute("aria-disabled") } : null; };
      return { back: read("back"), forward: read("forward") };
    });
    const base = (): Promise<string | null> => page.locator("#romp-fileview .fileview-base").textContent();
    // a paint of the named file in either view: Edit on a markdown file switches the view to Raw and SAVES that preference
    // (the editor's own rule, from before the trail), so the reloaded notes come back Raw while the report, opened by
    // Back, comes back in the view its entry recorded; the view is read where the case cares, never assumed here
    const painted = async (name: string) => {
      await page.locator("#romp-fileview .fileview-base", { hasText: name }).waitFor({ timeout: 10000 });
      await page.waitForFunction(() => !!document.querySelector("#romp-fileview .fileview-md > p") || !!document.querySelector("#romp-fileview .fileview-body .fv-cl"), null, { timeout: 10000 });
      await frames(page, 2);
    };
    const view = (): Promise<"rendered" | "raw" | null> => page.evaluate(() => document.querySelector("#romp-fileview .fileview-md") ? "rendered" : document.querySelector("#romp-fileview .fileview-body .fv-cl") ? "raw" : null);
    // the push: the report's link to the notes
    await page.locator("#romp-fileview .fileview-body a", { hasText: "the notes" }).click();
    await painted("notes.md");
    assert.deepEqual(await nav(), { back: { title: "Back to report.md", disabled: null }, forward: { title: "Forward", disabled: "true" } }, "the link's open pushed the report behind");
    // Edit (the page inlines the bundle, so the editor chunk has no script tag to load from and the plain textarea mounts), a change, Save
    await page.locator("#romp-fileview .fileview-acts button[aria-label='Edit']").click();
    await page.waitForFunction(() => !!document.querySelector("#romp-fileview .fileview-body textarea.fileview-editor"), null, { timeout: 10000 });
    await frames(page, 2);
    await page.evaluate(() => { const ta = document.querySelector("#romp-fileview .fileview-body textarea.fileview-editor") as HTMLTextAreaElement; ta.focus(); ta.value = ta.value + "\nNote 2: a line added in the viewer.\n"; ta.dispatchEvent(new Event("input")); });
    const n0: number = await page.evaluate(() => (window as any).__posted.length);
    await page.locator("#romp-fileview .fileview-acts button", { hasText: /^Save$/ }).click();
    await page.waitForFunction((n: number) => (window as any).__posted.slice(n).some((m: any) => m && m.type === "saveFile"), n0, { timeout: 10000 });
    const save: { reqId: number; path: string } = await page.evaluate((n: number) => { const p = (window as any).__posted.slice(n).find((m: any) => m && m.type === "saveFile"); return { reqId: p.reqId, path: p.path }; }, n0);
    assert.equal(save.path, NOTES, "the save is the notes'");
    // the kernel's refusal, in its words: the file moved under the editor, so the notice carries Reload file
    await page.evaluate((reqId: number) => { window.dispatchEvent(new MessageEvent("message", { data: { type: "fileSaveFailed", reqId, error: "notes.md changed on disk since you opened it" } })); }, save.reqId);
    await page.waitForFunction(() => { const b = document.querySelector("#fileview-save-err button"); return !!b && b.textContent === "Reload file"; }, null, { timeout: 10000 });
    assert.deepEqual(await nav(), { back: { title: "Back to report.md", disabled: null }, forward: { title: "Forward", disabled: "true" } }, "the refused save moved nothing");
    // Reload file: the discard ask (the page is the kernel's, so it is window.confirm) says yes; the old card goes and a NEW one paints, in read mode, with no notice
    await page.evaluate(() => { const w = window as any; w.__asked = 0; w.confirm = () => { w.__asked++; return true; }; w.__oldWrap = document.getElementById("romp-fileview"); });
    await page.click("#fileview-save-err button");
    await page.waitForFunction(() => { const w = document.getElementById("romp-fileview"); return !!w && w !== (window as any).__oldWrap && !document.getElementById("fileview-save-err"); }, null, { timeout: 10000 });
    await painted("notes.md");
    assert.equal(await page.evaluate(() => (window as any).__asked), 1, "the discard ask ran once, before the old card went");
    assert.equal(await base(), "notes.md", "the fresh card shows the notes as they are now");
    assert.equal(await page.evaluate(() => !!document.querySelector("#romp-fileview .fileview-body textarea.fileview-editor")), false, "in read mode");
    assert.deepEqual(await nav(), { back: { title: "Back to report.md", disabled: null }, forward: { title: "Forward", disabled: "true" } },
      "the trail stood through the reload: the same entry, Back still names the report (a Reload that closed first, or opened untagged, leaves Back disabled here)");
    // Back after the reload: the report, with the reloaded notes ahead
    await page.click("#romp-fileview .fileview-nav-back");
    await painted("report.md");
    assert.deepEqual(await nav(), { back: { title: "Back", disabled: "true" }, forward: { title: "Forward to notes.md", disabled: null } }, "Back after the reload reaches the report, and the notes went ahead");
    assert.equal(await view(), "rendered", "the report opens in the view its entry recorded at the push (L2), whatever the saved preference says by now");
    assert.deepEqual(errors, [], "no page errors");
    await page.close();
  });
});

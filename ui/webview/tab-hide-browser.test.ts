// THE HIDE, THE SHOW AND THE NON-FOLDING DOOR over the real render path, in a real engine (round 1 of the tabhide
// review, 2026-09-08). tab-hide.test.ts executes the pure modules and pins render.ts at the source; this leg runs
// render.ts's OWN code for the section header (makeGroupHead), the #tabs delegate's header acts and the whole
// snapshot pane (snapView through fillSnapshotRow), sliced verbatim from render.ts when the test runs and bundled
// with the real pure modules over a stand-in for the rest of the page (renderTabs' plan-to-DOM loop, showActive,
// setActive, the page's maps), in headless Chromium with the real sheet and real pointer gestures. It proves what
// no source pin can:
//   - a header click on an open group folds it and shows the pane (as before); Hide in that pane writes the store
//     and leaves the fold as it is; the header opens the group again with the hidden member's tab left off;
//   - the open header over a hidden member wears "1 hidden" as a button, and a click on it, on the pip or on the
//     flag shows the pane and leaves the fold and the strip as they were; Show from that pane puts the tab back on
//     the strip at once, the group still open; the flag on a FOLDED header still opens the group;
//   - a double-click on Hide hides one session, not two (the platform's click count);
//   - a hidden idle session the feed files under needs-you paints the header's pip red and names it, and the
//     fold's head counts it;
//   - focus: the last hidden row shown from another pane, or gone from the section, under keyboard focus, lands
//     on a shown row, never on body; the Hidden fold's open state is the section's own.
// A slice that stops compiling against the stand-in fails loudly here (a ReferenceError in the page), which is
// the point: render.ts's code runs, not a copy. Skips, never fails, where playwright or Chromium is missing (CI
// installs none). The notes-api demo world, synthetic ids.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { sectionDoorTitle, SHOW_GROUP_CLICK } from "./tab-state";

const requireCjs = createRequire(__filename);
const EXT = process.cwd();                                        // npm test runs in vscode-extension
const UI = path.resolve(EXT, "..", "ui", "webview");
const RENDER = fs.readFileSync(path.join(UI, "render.ts"), "utf8");
const CSS = fs.readFileSync(path.join(UI, "styles.css"), "utf8");

/** a verbatim slice of render.ts, from one marker to the next; both must exist */
function slice(from: string, to: string): string {
  const a = RENDER.indexOf(from), b = RENDER.indexOf(to, a + 1);
  assert.ok(a >= 0 && b > a, `render.ts markers: ${from} .. ${to}`);
  return RENDER.slice(a, b);
}

// the demo world: web, api and tests in infra; old1 in archived (folded by default)
const V = { active: "all", tags: [
  { id: "g1", name: "infra", color: "#4EC9B0", members: ["web", "api", "tests"] },
  { id: "g2", name: "archived", color: "#6b7280", members: ["old1"] },
], seq: 3 };
const V_API_LEFT = { ...V, tags: [{ ...V.tags[0], members: ["web", "tests"] }, V.tags[1]], seq: 4 };
const SESS: Record<string, unknown> = {
  web: { name: "web", status: { state: "working" } },
  api: { name: "api", status: { state: "ready" }, userTodos: [] },
  tests: { name: "tests", status: { state: "ready" } },
  old1: { name: "old1", status: { state: "ready" } },
};

/** The probe: render.ts's own header, header acts and pane, over the stand-in page, as one browser bundle. */
function probeSource(): string {
  const HEAD = slice("function makeGroupHead(", "function sectionHeadOf(");
  const SNAP = slice("let snapView: string | null = null;", "function showActive() {");
  const ACTS = slice('"toggle-group": (el) => {', "    close: (el) => {");
  const RELEASE = slice("function releaseTabStrip(): void {", "// A SECTION HEADER for the tab strip");
  const WRITE = slice("function tabGroups() {", "let draggedGroup: string | null = null;");
  const UNFOLD = slice("function unfoldSectionOf(id: string): void {", '// "Enter to start typing"');
  return `
import { planStrip, readTabGroups, writeTabGroups, setSectionCollapsed, setHidden, prunePinned, headWords, homeSectionOf, neighborOfFolded, reachableFrom, sectionRef, TABGROUPS_KEY, TABGROUPS_EVENT } from "./tab-groups";
import { snapshotModel, snapshotHeading, rowWords, hiddenNeeds, hiddenFoldWords, actWords, standInPip } from "./tab-snapshot";
import { rowStillOpen, installSnapshotEscape, reconcileRows, repeatedClick } from "./tab-snapshot-view";
import { sectionPipTitle, sectionTodoFlag, sectionTodoTitle, sectionDoorTitle, SHOW_GROUP_CLICK } from "./tab-state";
import { viewTagUnion } from "./session-views";
import { hostNameNodes } from "./host-prefix";
import { ageColorReadable } from "./age-color";
import { delegate } from "./actions";
// THE STAND-IN PAGE: the maps and helpers the slices read, declared as render.ts declares them
const sessions = new Map<string, any>();
const ledgers = new Map<string, any>();
const tabMeta = new Map<string, any>();
const closingTabs = new Map<string, number>();
let order: string[] = [];
let activeId: string | null = null;
let collapsedTabIds = new Set<string>();
let hiddenTabIds = new Set<string>();
let lastStripItems: any[] = [];
let tabPointerHeld = false;
let renderPendingWhilePressed = false;
let draggedGroup: string | null = null;
let sessionViews: any = null;
const ctxMenuEl: any = null, metaMenuEl: any = null, citePreviewEl: any = null, openCommentKey: any = null;
function el(tag: string, cls?: string): HTMLElement { const e = document.createElement(tag); if (cls) e.className = cls; return e; }
function effViews() { return sessionViews; }
function knownTabIds(): Set<string> { return new Set<string>([...order, ...tabMeta.keys()]); }
function reachableHosts(): Set<string> { return reachableFrom((window as any).__rompFed); }
function isTypingTarget() { return false; }
function focusComposerOrAsk() { return false; }
function dragImageBlank() { return document.body; }
function hideTabTip() {}
function tabEmojiNode() { return null; }
function agehms(s: number) { return Math.round(s) + "s"; }
function phoneLayout() { return false; }
${WRITE}
${RELEASE}
${UNFOLD}
function focusActiveTab() {
  const bar = document.getElementById("tabs")!;
  const t = activeId ? bar.querySelector<HTMLElement>('.tab[data-id="' + activeId + '"]') : null;
  if (t) { t.focus(); return; }
  const home = activeId ? homeSectionOf(lastStripItems, activeId) : null;
  if (home && home.name !== null) Array.from(bar.querySelectorAll<HTMLElement>(".tab-group-head")).find((h) => h.dataset.group === home.name)?.focus();
}
function showActive() {
  const tx = document.getElementById("transcript")!;
  if (snapView && renderSnapshot()) { tx.style.display = "none"; return; }
  hideSnapshot();
  tx.style.display = "";
}
function setActive(id: string) {
  snapView = null;
  if (collapsedTabIds.has(id) && !hiddenTabIds.has(id)) unfoldSectionOf(id);
  activeId = id;
  renderTabs(); showActive();
}
// renderTabs' plan-to-DOM loop and its aftermath, as render.ts runs them (the signature skip and a tab's own parts left out)
function renderTabs() {
  if (tabPointerHeld) { renderPendingWhilePressed = true; return; }
  const bar = document.getElementById("tabs")!;
  const unions = viewTagUnion(effViews());
  const plan = planStrip(order, unions, readTabGroups(unions), activeId, phoneLayout(), null);
  collapsedTabIds = plan.folded;
  hiddenTabIds = new Set(plan.items.flatMap((it: any) => ("head" in it ? it.hides : [])));
  lastStripItems = plan.items;
  const focusedEl = document.activeElement as HTMLElement | null;
  const focusedGroup = (focusedEl?.closest(".tab-group-head") as HTMLElement | null)?.dataset.group;
  const focusedFlag = !!focusedEl?.classList.contains("tab-group-flag");
  const focusedDoor = !!focusedEl?.classList.contains("tab-group-door");
  bar.replaceChildren();
  for (const item of plan.items) {
    if ("head" in item) { bar.appendChild(makeGroupHead(item.head, item.folded, item.active, item.hidden)); continue; }
    const tab = el("div", "tab" + (item.id === activeId ? " active" : "")); tab.tabIndex = 0; tab.dataset.id = item.id; tab.dataset.act = "select";
    tab.textContent = sessions.get(item.id)?.name ?? item.id; bar.appendChild(tab);
  }
  if (focusedGroup !== undefined) {
    const h = Array.from(bar.querySelectorAll<HTMLElement>(".tab-group-head")).find((x) => x.dataset.group === focusedGroup);
    if (h) ((focusedFlag && h.querySelector<HTMLElement>(".tab-group-flag")) || (focusedDoor && h.querySelector<HTMLElement>(".tab-group-door")) || h).focus();
  }
  const shown = snapView;
  if (snapView) renderSnapshot();
  if (shown && !snapView) showActive();
}
${HEAD}
${SNAP}
const tabs = document.getElementById("tabs")!;
delegate(tabs, { select: (el) => { const id = el.dataset.id; if (id) { setActive(id); focusActiveTab(); } },
${ACTS} });
tabs.addEventListener("pointerdown", () => { tabPointerHeld = true; });
window.addEventListener("pointerup", releaseTabStrip);
window.addEventListener("pointercancel", releaseTabStrip);
window.addEventListener("blur", releaseTabStrip);
window.addEventListener("storage", (e) => { if (e.key === TABGROUPS_KEY) renderTabs(); });
window.addEventListener(TABGROUPS_EVENT, () => renderTabs());
(window as any).__probe = {
  setup(v: any, ids: string[], sess: Record<string, any>, active: string) {
    localStorage.removeItem(TABGROUPS_KEY);
    sessionViews = v; order = ids; activeId = active;
    sessions.clear(); for (const [k, s] of Object.entries(sess)) sessions.set(k, s);
    ledgers.clear();
    renderTabs(); showActive();
  },
  session(id: string, s: any) { sessions.set(id, s); renderTabs(); },
  ledger(id: string, l: any) { ledgers.set(id, l); renderTabs(); },
  views(v: any) { sessionViews = v; renderTabs(); },
  /** another pane's Hide or Show: the store written and the panes told, no pointer here */
  otherPane(section: string, sid: string, hide: boolean) {
    const unions = viewTagUnion(sessionViews);
    const u = unions.find((x: any) => x.name === section)!;
    writeTabGroups(setHidden(readTabGroups(unions), sectionRef(u), sid, hide));
  },
  state() {
    const bar = document.getElementById("tabs")!;
    const host = document.getElementById("tab-snapshot");
    const q = (root: Element, sel: string) => root.querySelector<HTMLElement>(sel);
    const heads = Array.from(bar.querySelectorAll<HTMLElement>(".tab-group-head")).map((h) => ({
      name: h.dataset.group, folded: h.dataset.folded, act: h.dataset.act, snapShown: h.classList.contains("snap-shown"),
      count: q(h, ".tab-group-count")?.textContent ?? null, countTag: q(h, ".tab-group-count")?.tagName ?? null,
      countAct: q(h, ".tab-group-count")?.dataset.act ?? null, countTitle: q(h, ".tab-group-count")?.title ?? null,
      pip: q(h, ".tab-group-pip")?.className ?? null, pipAct: q(h, ".tab-group-pip")?.dataset.act ?? null, pipTitle: q(h, ".tab-group-pip")?.title ?? null,
      flagAct: q(h, ".tab-group-flag")?.dataset.act ?? null, flagTitle: q(h, ".tab-group-flag")?.title ?? null,
      label: h.getAttribute("aria-label"),
    }));
    const a = document.activeElement as HTMLElement | null;
    const fold = host ? q(host, ".snap-hidden") : null;
    return {
      tabs: Array.from(bar.querySelectorAll<HTMLElement>(".tab")).map((t) => t.dataset.id),
      heads, snapView,
      paneShown: !!host && host.style.display !== "none",
      transcriptShown: document.getElementById("transcript")!.style.display !== "none",
      shownRows: host ? Array.from(host.querySelectorAll<HTMLElement>(":scope > .snap-list > .snap-item")).map((i) => i.dataset.id) : [],
      hiddenRows: host ? Array.from(host.querySelectorAll<HTMLElement>(".snap-hidden-list > .snap-item")).map((i) => i.dataset.id) : [],
      foldShown: !!fold && fold.style.display !== "none",
      foldOpen: !!fold && fold.classList.contains("open"),
      foldNeeds: fold ? q(fold, ".snap-hidden-needs")!.textContent : "",
      stored: JSON.parse(localStorage.getItem(TABGROUPS_KEY) || "null"),
      active: !a || a === document.body ? "body" : (a.className.split(" ")[0] || a.tagName) + (a.dataset.id ? "#" + a.dataset.id : "") + (a.dataset.group ? "@" + a.dataset.group : ""),
    };
  },
};
`;
}

/** The probe, bundled as the webview build bundles the page (in memory), served to the page as /probe.js. */
function bundle(): string {
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    stdin: { contents: probeSource(), resolveDir: UI, loader: "ts", sourcefile: "tab-hide-probe.ts" },
    bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], logLevel: "silent",
  });
  return r.outputFiles[0].text;
}
// the strip and the pane's host, under the real sheet (its @import and font urls 404 here, harmlessly)
const PAGE = `<!DOCTYPE html><html><head><meta charset=utf-8><link rel=stylesheet href=/styles.css>
<style>body{margin:0;padding:8px} #tabs{display:flex;flex-wrap:wrap;gap:4px;padding:4px}</style></head>
<body><div id=tabs></div><div id=content><div id=transcript>transcript</div></div><script src=/probe.js></script></body></html>`;

type Head = { name?: string; folded?: string; act?: string; snapShown: boolean; count: string | null; countTag: string | null; countAct: string | null; countTitle: string | null;
  pip: string | null; pipAct: string | null; pipTitle: string | null; flagAct: string | null; flagTitle: string | null; label: string | null };
type State = { tabs: string[]; heads: Head[]; snapView: string | null; paneShown: boolean; transcriptShown: boolean; shownRows: string[]; hiddenRows: string[];
  foldShown: boolean; foldOpen: boolean; foldNeeds: string; stored: any; active: string };

test("in Chromium, over render.ts's own header, header acts and pane: hide, show, the non-folding door, the flag, the double-click, the feed's verdict, focus and the fold", async (t) => {
  let pw: any = null;
  try { pw = requireCjs("playwright"); } catch { pw = null; }
  if (!pw) { t.skip("playwright is not installed under vscode-extension (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw.chromium.launch(); }
  catch (e) { t.skip("no playwright chromium on this box (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  try {
    const page = await browser.newPage({ viewport: { width: 1000, height: 700 } });
    const errors: string[] = [];
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    const js = bundle();
    await page.route("http://romp.test/**", (route: any) => {
      const u = new URL(route.request().url());
      if (u.pathname === "/page") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: PAGE });
      if (u.pathname === "/probe.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: js });
      if (u.pathname === "/styles.css") return route.fulfill({ status: 200, contentType: "text/css; charset=utf-8", body: CSS });
      return route.fulfill({ status: 404, body: "" });
    });
    await page.goto("http://romp.test/page");
    const state = (): Promise<State> => page.evaluate(() => (window as any).__probe.state());
    const head = async (name: string): Promise<Head> => { const s = await state(); const h = s.heads.find((x) => x.name === name); assert.ok(h, "a header for " + name); return h!; };
    const nameOf = (g: string) => `#tabs .tab-group-head[data-group="${g}"] .tab-group-name`;
    const act = (id: string) => `#tab-snapshot .snap-item[data-id="${id}"] .snap-act`;
    const inHead = (g: string, part: string) => `#tabs .tab-group-head[data-group="${g}"] ${part}`;
    await page.evaluate(([v, sess]: [unknown, unknown]) => (window as any).__probe.setup(v, ["web", "api", "tests", "old1"], sess, "web"), [V, SESS] as [unknown, unknown]);
    assert.deepEqual(errors, [], "the slices ran against the stand-in (a ReferenceError here means render.ts grew a dependency the probe lacks)");

    // S1: the strip as it starts: infra open with its three tabs, the count a plain span; archived folded away
    let s = await state();
    let h = await head("infra");
    assert.deepEqual([s.tabs, h.folded, h.count, h.countTag, h.countAct, h.pip, h.flagAct, s.paneShown], [["web", "api", "tests"], "0", "3", "SPAN", null, null, null, false]);

    // S2: the header's click on the open group folds it and shows the pane (as before)
    await page.click(nameOf("infra"));
    s = await state(); h = await head("infra");
    assert.deepEqual([s.tabs, h.folded, s.snapView, s.paneShown, s.transcriptShown], [[], "1", "infra", true, false]);
    assert.deepEqual([s.shownRows, s.hiddenRows, s.foldShown], [["web", "api", "tests"], [], false]);

    // S3: Hide in the pane: the store, not the fold
    await page.click(act("api"));
    s = await state();
    assert.deepEqual(s.stored.hidden, [{ sid: "api", name: "infra", id: "g1" }]);
    assert.deepEqual(s.stored.collapsed, ["infra"], "the fold as it was");
    assert.deepEqual([s.shownRows, s.hiddenRows, s.foldShown, s.foldOpen], [["web", "tests"], ["api"], true, false]);

    // S4: the header opens the group: api's tab left off, the count a door
    await page.click(nameOf("infra"));
    s = await state(); h = await head("infra");
    assert.deepEqual([s.tabs, h.folded, s.snapView, s.paneShown, h.snapShown], [["web", "tests"], "0", "infra", true, true]);
    assert.deepEqual([h.count, h.countTag, h.countAct, h.countTitle], ["1 hidden", "BUTTON", "show-group", sectionDoorTitle(1)]);
    assert.ok(h.label!.startsWith("infra, 3 sessions, 1 hidden"), h.label!);

    // S5: Escape leaves the pane; the group stays open
    await page.keyboard.press("Escape");
    s = await state();
    assert.deepEqual([s.paneShown, s.transcriptShown, s.snapView, s.tabs], [false, true, null, ["web", "tests"]]);

    // S6: THE DOOR: the pane comes, the fold, the strip and the store stay as they were
    const before = JSON.stringify(s.stored);
    await page.click(inHead("infra", ".tab-group-door"));
    s = await state(); h = await head("infra");
    assert.deepEqual([s.paneShown, s.snapView, h.folded, h.snapShown, s.tabs, JSON.stringify(s.stored)], [true, "infra", "0", true, ["web", "tests"], before]);

    // S7: Show from that pane: the tab back at once, the group still open, the pane still up
    await page.click("#tab-snapshot .snap-hidden-head");
    s = await state(); assert.equal(s.foldOpen, true, "the fold opens on its head's click");
    await page.click(act("api"));
    s = await state(); h = await head("infra");
    assert.deepEqual([s.tabs, h.folded, s.paneShown, s.stored.hidden, s.shownRows, s.foldShown, h.countTag], [["web", "api", "tests"], "0", true, [], ["web", "api", "tests"], false, "SPAN"]);

    // S8: the flag on an OPEN header is a door too (round 1: it opened a group that was already open, and nothing moved)
    await page.evaluate(() => (window as any).__probe.session("api", { name: "api", status: { state: "ready" }, userTodos: [{ id: "t1", text: "synthetic need" }] }));
    await page.click(act("api"));   // hide it again, from the open pane; the fold untouched
    s = await state(); h = await head("infra");
    assert.deepEqual([s.tabs, h.folded, h.flagAct], [["web", "tests"], "0", "show-group"]);
    assert.ok(h.flagTitle!.endsWith(SHOW_GROUP_CLICK), h.flagTitle!);
    await page.keyboard.press("Escape");
    await page.click(inHead("infra", ".tab-group-flag"));
    s = await state(); h = await head("infra");
    assert.deepEqual([s.paneShown, s.snapView, h.folded, s.tabs], [true, "infra", "0", ["web", "tests"]], "the flag shows the pane and leaves the fold alone");
    // ...and the pip, over a hidden member waiting on you
    await page.keyboard.press("Escape");
    await page.evaluate(() => (window as any).__probe.session("api", { name: "api", status: { state: "needsInput" }, userTodos: [] }));
    h = await head("infra");
    assert.deepEqual([h.pip, h.pipAct], ["tab-group-pip blocked", "show-group"]);
    assert.ok(h.pipTitle!.endsWith(SHOW_GROUP_CLICK), h.pipTitle!);
    await page.click(inHead("infra", ".tab-group-pip"));
    s = await state(); h = await head("infra");
    assert.deepEqual([s.paneShown, s.snapView, h.folded, s.tabs], [true, "infra", "0", ["web", "tests"]]);

    // S9: the flag on a FOLDED header still opens the group (open-group)
    await page.keyboard.press("Escape");
    await page.evaluate(() => (window as any).__probe.session("api", { name: "api", status: { state: "ready" }, userTodos: [{ id: "t1", text: "synthetic need" }] }));
    await page.click(nameOf("infra"));   // folds, and shows the pane
    h = await head("infra");
    assert.deepEqual([h.folded, h.flagAct, h.countTag], ["1", "open-group", "SPAN"]);
    assert.ok(h.flagTitle!.endsWith("click to open this group"), h.flagTitle!);
    await page.click(inHead("infra", ".tab-group-flag"));
    s = await state(); h = await head("infra");
    assert.deepEqual([h.folded, s.tabs, s.stored.collapsed, s.paneShown], ["0", ["web", "tests"], [], true]);

    // S10: a double-click on Hide hides ONE session: the second click lands on the next row's Hide and acts on nothing
    await page.evaluate(() => (window as any).__probe.session("api", { name: "api", status: { state: "ready" }, userTodos: [] }));
    s = await state(); assert.equal(s.foldOpen, true, "infra's fold is still open (S7): api's Show is on screen");
    await page.click(act("api"));
    s = await state(); assert.deepEqual(s.shownRows, ["web", "api", "tests"]);
    await page.dblclick(act("api"));
    s = await state();
    assert.deepEqual([s.shownRows, s.hiddenRows, s.stored.hidden.map((p: { sid: string }) => p.sid)], [["web", "tests"], ["api"], ["api"]]);

    // S11: the feed's verdict on a hidden idle session reaches the header's pip and the fold's head
    h = await head("infra");
    assert.equal(h.pip, null, "idle, no verdict: no pip");
    await page.evaluate(() => (window as any).__probe.ledger("api", { needsInput: true, summary: "Designing the notes schema" }));
    s = await state(); h = await head("infra");
    assert.deepEqual([h.pip, h.pipAct, s.foldNeeds], ["tab-group-pip blocked", "show-group", "1 needs you"]);
    assert.ok(h.pipTitle!.startsWith("a session in this group is blocked or waiting on you: api"), h.pipTitle!);
    assert.ok(h.label!.includes("a session in this group is blocked or waiting on you: api"), "spoken by the header's label too");
    await page.evaluate(() => (window as any).__probe.ledger("api", { needsInput: false }));
    s = await state(); h = await head("infra");
    assert.deepEqual([h.pip, s.foldNeeds], [null, ""], "the verdict withdrawn: the pip and the count go");

    // S12: focus. (a) api's Show focused inside the open fold; another pane shows api: focus lands on api's Hide, in the shown list
    await page.focus(act("api"));
    assert.equal((await state()).active, "snap-act#api");
    await page.evaluate(() => (window as any).__probe.otherPane("infra", "api", false));
    s = await state();
    assert.deepEqual([s.hiddenRows, s.foldShown, s.active], [[], false, "snap-act#api"], "the same session's button, in its new list");
    // (b) the fold's head focused; another pane shows the last hidden: the last shown row takes focus, not body
    await page.evaluate(() => (window as any).__probe.otherPane("infra", "api", true));
    await page.focus("#tab-snapshot .snap-hidden-head");
    assert.equal((await state()).active, "snap-hidden-head");
    await page.evaluate(() => (window as any).__probe.otherPane("infra", "api", false));
    s = await state();
    assert.deepEqual([s.foldShown, s.active], [false, "snap-row#tests"]);
    // (c) api's row focused inside the fold; api leaves the section: the last shown row
    await page.evaluate(() => (window as any).__probe.otherPane("infra", "api", true));
    await page.focus('#tab-snapshot .snap-hidden-list .snap-item[data-id="api"] .snap-row');
    assert.equal((await state()).active, "snap-row#api");
    await page.evaluate((v: unknown) => (window as any).__probe.views(v), V_API_LEFT);
    s = await state();
    assert.deepEqual([s.shownRows, s.hiddenRows, s.foldShown, s.active, s.tabs], [["web", "tests"], [], false, "snap-row#tests", ["web", "tests", "api"]], "api loose on the strip, focus on the fold's neighbour");

    // S13: the Hidden fold's open state is the section's own
    await page.evaluate((v: unknown) => (window as any).__probe.views(v), V);
    s = await state();
    assert.deepEqual([s.hiddenRows, s.foldOpen], [["api"], true], "back in infra, hidden again (the entry stood: no pin or hide write ran) under the fold the user left open");
    await page.click(nameOf("archived"));   // folded: the click opens it and shows its snapshot
    s = await state();
    assert.deepEqual([s.snapView, s.shownRows, s.foldShown, s.foldOpen], ["archived", ["old1"], false, false]);
    await page.evaluate(() => (window as any).__probe.otherPane("archived", "old1", true));
    s = await state();
    assert.deepEqual([s.hiddenRows, s.foldShown, s.foldOpen], [["old1"], true, false], "archived's fold starts closed, whatever infra's is");
    await page.click(nameOf("infra"));   // open, the pane on another section: the click folds infra and shows it
    s = await state();
    assert.deepEqual([s.snapView, s.hiddenRows, s.foldOpen], ["infra", ["api"], true], "infra's own fold state, still open");
    assert.deepEqual(errors, [], "no page errors");
    await page.close();
  } finally { await browser.close(); }
});

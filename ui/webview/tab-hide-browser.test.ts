// THE HIDE, THE SHOW AND THE NON-FOLDING DOOR over the real render path, in a real engine (round 1 of the tabhide
// review, 2026-09-08). tab-hide.test.ts executes the pure modules and pins render.ts at the source; this leg runs
// render.ts's OWN code for the section header (makeGroupHead), the #tabs delegate's header acts and the whole
// snapshot pane (snapView through fillSnapshotRow), sliced verbatim from render.ts when the test runs and bundled
// with the real pure modules over a stand-in for the rest of the page (renderTabs' plan-to-DOM loop, showActive,
// setActive, the page's maps), in headless Chromium with the real sheet and real pointer gestures. It proves what
// no source pin can:
//   - a header click on an open group folds it and shows the pane (as before); Hide in that pane writes the store
//     and leaves the fold as it is; the header opens the group again with the hidden member's tab left off;
//   - the count is a door on EVERY open header, nothing hidden included (round 2): a click on it shows the pane and
//     leaves the fold, the strip and the store's bytes as they were, so the first hide never goes through a fold;
//     its words lead with its visible text, and the header's spoken label never ends in the flag's click clause;
//   - while the pane already shows the section, the door is the way back (round 3): its act is show-transcript, its
//     words say the sessions are shown below, and a click puts the transcript back with nothing written, whether or
//     not the header holds the tab being read; the pip and the flag on that header do the same, their phrases kept;
//   - a repeat click (the platform's count) acts on nothing and shows no acknowledgement pulse (round 2);
//   - the open header over a hidden member wears "1 hidden" as a button, and a click on it, on the pip or on the
//     flag shows the pane and leaves the fold and the strip as they were; Show from that pane puts the tab back on
//     the strip at once, the group still open; the flag on a FOLDED header still opens the group;
//   - a double-click on Hide hides one session, not two (the platform's click count);
//   - a hidden idle session the feed files under needs-you paints the header's pip red and names it, and the
//     fold's head counts it;
//   - focus: the last hidden row shown from another pane, or gone from the section, under keyboard focus, lands
//     on a shown row, never on body; the Hidden fold's open state is the section's own.
// A second test launches Chromium as a trackpad-plus-touchscreen laptop (pointer: fine, hover: hover, any-pointer:
// coarse) and reads the pane's Hide at opacity 1 from the real sheet (round 3: the primary-device feature missed it).
// A slice that stops compiling against the stand-in fails loudly here (a ReferenceError in the page), which is
// the point: render.ts's code runs, not a copy. Skips, never fails, where playwright or Chromium is missing (CI
// installs none). The notes-api demo world, synthetic ids.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { sectionDoorTitle, sectionTodoPhrase, sectionTodoTitle, SHOW_GROUP_CLICK, BACK_TO_TRANSCRIPT_CLICK } from "./tab-state";

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
import { sectionPipTitle, sectionTodoFlag, sectionTodoTitle, sectionTodoPhrase, sectionDoorTitle, doorClick, SHOW_GROUP_CLICK } from "./tab-state";
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
  setSession(id: string, s: any) { sessions.set(id, s); renderTabs(); },
  setLedger(id: string, l: any) { ledgers.set(id, l); renderTabs(); },
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
      name: h.dataset.group, folded: h.dataset.folded, act: h.dataset.act, title: h.title, snapShown: h.classList.contains("snap-shown"),
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

type Head = { name?: string; folded?: string; act?: string; title: string; snapShown: boolean; count: string | null; countTag: string | null; countAct: string | null; countTitle: string | null;
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

    // S1: the strip as it starts: infra open with its three tabs, the count a button (the door, round 2) with nothing hidden;
    // archived folded away, its count a plain span
    let s = await state();
    let h = await head("infra");
    assert.deepEqual([s.tabs, h.folded, h.count, h.countTag, h.countAct, h.pip, h.flagAct, s.paneShown], [["web", "api", "tests"], "0", "3", "BUTTON", "show-group", null, null, false]);
    assert.equal(h.countTitle, sectionDoorTitle(0, 3));
    assert.ok(h.countTitle!.startsWith(h.count!), "label in name: the door's words lead with its visible text");
    assert.deepEqual([(await head("archived")).countTag, (await head("archived")).countAct], ["SPAN", null], "folded: a span, as before");
    // S1b: THE DOOR WITH NOTHING HIDDEN (round 2: it existed only once something was hidden, so the first hide of a group
    // went through the header's click, which folds the group over its reader): the pane comes; the fold, the strip and the
    // store (none written yet) stay as they were
    assert.equal(await page.evaluate(() => localStorage.getItem("romp:tabgroups")), null, "no store yet");
    await page.click(inHead("infra", ".tab-group-door"));
    s = await state(); h = await head("infra");
    assert.deepEqual([s.paneShown, s.snapView, h.folded, h.snapShown, s.tabs, s.shownRows, s.hiddenRows, s.foldShown], [true, "infra", "0", true, ["web", "api", "tests"], ["web", "api", "tests"], [], false]);
    assert.equal(await page.evaluate(() => localStorage.getItem("romp:tabgroups")), null, "the door writes nothing");
    // S1c: THE WAY BACK ON THE DOOR (round 3): with the pane already showing this section the door's click changed nothing and
    // its words still promised the pane; now it mirrors the header's second click (the header holds web, so both say so): act
    // show-transcript, words that say the sessions are shown below and end in the header's own way-back clause. The click puts
    // the transcript back; the fold, the strip and the store (still none) stay as they were, and the count is the door again
    assert.deepEqual([h.act, h.countAct, h.countTitle], ["show-transcript", "show-transcript", sectionDoorTitle(0, 3, true)]);
    assert.ok(h.countTitle!.startsWith(h.count!) && h.countTitle!.endsWith(BACK_TO_TRANSCRIPT_CLICK), h.countTitle!);
    assert.ok(h.title.includes("; " + BACK_TO_TRANSCRIPT_CLICK + "; "), "one voice with the header: " + h.title);
    await page.click(inHead("infra", ".tab-group-door"));
    s = await state(); h = await head("infra");
    assert.deepEqual([s.paneShown, s.transcriptShown, s.snapView, h.folded, h.snapShown, h.act, h.countAct, h.countTitle, s.tabs],
                     [false, true, null, "0", false, "toggle-group", "show-group", sectionDoorTitle(0, 3), ["web", "api", "tests"]]);
    assert.equal(await page.evaluate(() => localStorage.getItem("romp:tabgroups")), null, "the way back writes nothing either");
    await page.click(inHead("infra", ".tab-group-door"));   // the pane again, for the Escape below
    s = await state(); assert.deepEqual([s.paneShown, s.snapView], [true, "infra"]);
    await page.keyboard.press("Escape");
    s = await state(); assert.deepEqual([s.paneShown, s.snapView], [false, null]);

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
    // the header's click showed the section, so the count is the way back (round 3), its words led by its visible text
    assert.deepEqual([h.count, h.countTag, h.countAct, h.countTitle], ["1 hidden", "BUTTON", "show-transcript", sectionDoorTitle(1, 3, true)]);
    assert.ok(h.countTitle!.startsWith(h.count!), "label in name (round 2): the door's words lead with its visible text");
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
    assert.deepEqual([h.countAct, h.countTitle], ["show-transcript", sectionDoorTitle(1, 3, true)], "shown: the door is the way back (round 3)");

    // S7: Show from that pane: the tab back at once, the group still open, the pane still up
    await page.click("#tab-snapshot .snap-hidden-head");
    s = await state(); assert.equal(s.foldOpen, true, "the fold opens on its head's click");
    await page.click(act("api"));
    s = await state(); h = await head("infra");
    assert.deepEqual([s.tabs, h.folded, s.paneShown, s.stored.hidden, s.shownRows, s.foldShown, h.countTag, h.count], [["web", "api", "tests"], "0", true, [], ["web", "api", "tests"], false, "BUTTON", "3"]);
    // S7b: THE DOOR WITH NOTHING HIDDEN over a real store (round 2): Escape, then the count: the pane comes back; the fold,
    // the strip and the store's bytes stay as they were
    await page.keyboard.press("Escape");
    s = await state(); assert.deepEqual([s.paneShown, s.snapView], [false, null]);
    const rawBefore = await page.evaluate(() => localStorage.getItem("romp:tabgroups"));
    assert.ok(rawBefore && rawBefore.length > 2, "a store exists now");
    await page.click(inHead("infra", ".tab-group-door"));
    s = await state(); h = await head("infra");
    assert.deepEqual([s.paneShown, s.snapView, h.folded, h.snapShown, s.tabs, s.shownRows], [true, "infra", "0", true, ["web", "api", "tests"], ["web", "api", "tests"]]);
    assert.equal(await page.evaluate(() => localStorage.getItem("romp:tabgroups")), rawBefore, "the store's bytes, untouched");
    assert.ok(h.countTitle!.startsWith(h.count!) && h.countTitle === sectionDoorTitle(0, 3, true) && h.countAct === "show-transcript", h.countTitle!);

    // S8: the flag on an OPEN header is a door too (round 1: it opened a group that was already open, and nothing moved)
    await page.evaluate(() => (window as any).__probe.setSession("api", { name: "api", status: { state: "ready" }, userTodos: [{ id: "t1", text: "synthetic need" }] }));
    await page.click(act("api"));   // hide it again, from the open pane; the fold untouched
    s = await state(); h = await head("infra");
    // the pane shows infra (S7b's door click), so the flag is the way back, like the count (round 3): the who phrase, then the
    // header's own way-back clause
    assert.deepEqual([s.tabs, h.folded, h.flagAct, h.countAct], [["web", "tests"], "0", "show-transcript", "show-transcript"]);
    assert.equal(h.flagTitle, sectionTodoTitle({ count: 1, names: ["api"] }, true, true));
    assert.ok(h.flagTitle!.startsWith(sectionTodoPhrase({ count: 1, names: ["api"] }) + "; ") && h.flagTitle!.endsWith(BACK_TO_TRANSCRIPT_CLICK), h.flagTitle!);
    // the header's own spoken label (round 2): the flag's phrase rides it, the click clause does not (the header's click
    // folds the group or puts the transcript back, so the door's instruction there contradicted it)
    assert.ok(h.label!.endsWith("; " + sectionTodoPhrase({ count: 1, names: ["api"] })), h.label!);
    assert.ok(!h.label!.endsWith(SHOW_GROUP_CLICK) && !h.label!.includes("click to"), h.label!);
    await page.keyboard.press("Escape");
    h = await head("infra");
    assert.deepEqual([h.flagAct, h.flagTitle], ["show-group", sectionTodoTitle({ count: 1, names: ["api"] }, true)], "the pane gone: the flag is the door, as before");
    assert.ok(h.flagTitle!.endsWith(SHOW_GROUP_CLICK), h.flagTitle!);
    await page.click(inHead("infra", ".tab-group-flag"));
    s = await state(); h = await head("infra");
    assert.deepEqual([s.paneShown, s.snapView, h.folded, s.tabs], [true, "infra", "0", ["web", "tests"]], "the flag shows the pane and leaves the fold alone");
    // S8b: THE WAY BACK ON THE FLAG (round 3): the pane showing infra, the flag's act is show-transcript and its words end in the
    // header's way-back clause; the click puts the transcript back, the fold and the store's bytes stand, and the flag is the
    // door again
    const rawFlag = await page.evaluate(() => localStorage.getItem("romp:tabgroups"));
    assert.deepEqual([h.flagAct, h.flagTitle, h.countAct], ["show-transcript", sectionTodoTitle({ count: 1, names: ["api"] }, true, true), "show-transcript"]);
    await page.click(inHead("infra", ".tab-group-flag"));
    s = await state(); h = await head("infra");
    assert.deepEqual([s.paneShown, s.transcriptShown, s.snapView, h.folded, h.flagAct, h.countAct, s.tabs], [false, true, null, "0", "show-group", "show-group", ["web", "tests"]]);
    assert.equal(await page.evaluate(() => localStorage.getItem("romp:tabgroups")), rawFlag, "the flag's way back writes nothing");
    // ...and the pip, over a hidden member waiting on you
    await page.keyboard.press("Escape");
    await page.evaluate(() => (window as any).__probe.setSession("api", { name: "api", status: { state: "needsInput" }, userTodos: [] }));
    h = await head("infra");
    assert.deepEqual([h.pip, h.pipAct], ["tab-group-pip blocked", "show-group"]);
    assert.ok(h.pipTitle!.endsWith(SHOW_GROUP_CLICK), h.pipTitle!);
    const pipSaid = h.pipTitle!.slice(0, -("; " + SHOW_GROUP_CLICK).length);
    await page.click(inHead("infra", ".tab-group-pip"));
    s = await state(); h = await head("infra");
    assert.deepEqual([s.paneShown, s.snapView, h.folded, s.tabs], [true, "infra", "0", ["web", "tests"]]);
    // S8c: THE WAY BACK ON THE PIP (round 3): the same phrase, then the way-back clause; the header's spoken label still carries
    // the phrase alone; the click puts the transcript back and writes nothing
    assert.deepEqual([h.pipAct, h.pipTitle], ["show-transcript", pipSaid + "; " + BACK_TO_TRANSCRIPT_CLICK]);
    assert.ok(h.label!.includes("; " + pipSaid) && !h.label!.includes("click to"), h.label!);
    await page.click(inHead("infra", ".tab-group-pip"));
    s = await state(); h = await head("infra");
    assert.deepEqual([s.paneShown, s.transcriptShown, s.snapView, h.folded, h.pipAct, h.pipTitle, s.tabs], [false, true, null, "0", "show-group", pipSaid + "; " + SHOW_GROUP_CLICK, ["web", "tests"]]);
    assert.equal(await page.evaluate(() => localStorage.getItem("romp:tabgroups")), rawFlag, "the pip's way back writes nothing");

    // S9: the flag on a FOLDED header still opens the group (open-group)
    await page.keyboard.press("Escape");
    await page.evaluate(() => (window as any).__probe.setSession("api", { name: "api", status: { state: "ready" }, userTodos: [{ id: "t1", text: "synthetic need" }] }));
    await page.click(nameOf("infra"));   // folds, and shows the pane
    h = await head("infra");
    assert.deepEqual([h.folded, h.flagAct, h.countTag], ["1", "open-group", "SPAN"]);
    assert.ok(h.flagTitle!.endsWith("click to open this group"), h.flagTitle!);
    await page.click(inHead("infra", ".tab-group-flag"));
    s = await state(); h = await head("infra");
    assert.deepEqual([h.folded, s.tabs, s.stored.collapsed, s.paneShown], ["0", ["web", "tests"], [], true]);

    // S10: a double-click on Hide hides ONE session: the second click lands on the next row's Hide and acts on nothing
    await page.evaluate(() => (window as any).__probe.setSession("api", { name: "api", status: { state: "ready" }, userTodos: [] }));
    s = await state(); assert.equal(s.foldOpen, true, "infra's fold is still open (S7): api's Show is on screen");
    await page.click(act("api"));
    s = await state(); assert.deepEqual(s.shownRows, ["web", "api", "tests"]);
    await page.dblclick(act("api"));
    s = await state();
    assert.deepEqual([s.shownRows, s.hiddenRows, s.stored.hidden.map((p: { sid: string }) => p.sid)], [["web", "tests"], ["api"], ["api"]]);
    // S10b: a repeat click SHOWS nothing either (round 2): the delegate pulses every matched click before its handler, and
    // the swallowed click had pulsed the button it landed on while nothing happened. A click with the platform's count at 2,
    // dispatched at web's Hide: no pulse class on it, the rows and the store as they were. A fresh click on the fold's head
    // (count 1) is acknowledged and acts, so the probe does see the pulse when there is one.
    const pulse = (sel: string, detail: number) => page.$eval(sel, (b: Element, d: number) => {
      b.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true, detail: d }));
      return b.classList.contains("romp-acted");
    }, detail);
    assert.equal(await pulse(act("web"), 2), false, "no acknowledgement on a click that acted on nothing");
    s = await state();
    assert.deepEqual([s.shownRows, s.hiddenRows, s.stored.hidden.map((p: { sid: string }) => p.sid), s.foldOpen], [["web", "tests"], ["api"], ["api"], true], "and nothing changed");
    assert.equal(await pulse("#tab-snapshot .snap-hidden-head", 1), true, "a fresh click is acknowledged");
    s = await state(); assert.equal(s.foldOpen, false, "and acts");
    assert.equal(await pulse("#tab-snapshot .snap-hidden-head", 3), false, "a repeat on a node that keeps standing: no pulse (the fresh click's, if still running, is cut short)");
    s = await state(); assert.equal(s.foldOpen, false, "the repeat acted on nothing");
    await page.click("#tab-snapshot .snap-hidden-head");
    s = await state(); assert.equal(s.foldOpen, true, "back open for what follows");

    // S11: the feed's verdict on a hidden idle session reaches the header's pip and the fold's head
    h = await head("infra");
    assert.equal(h.pip, null, "idle, no verdict: no pip");
    await page.evaluate(() => (window as any).__probe.setLedger("api", { needsInput: true, summary: "Designing the notes schema" }));
    s = await state(); h = await head("infra");
    assert.deepEqual([h.pip, h.pipAct, s.foldNeeds], ["tab-group-pip blocked", "show-transcript", "1 needs you"], "the pane shows infra here, so the pip is the way back (round 3); the verdict paints it and the fold's head");
    assert.ok(h.pipTitle!.startsWith("a session in this group is blocked or waiting on you: api"), h.pipTitle!);
    assert.ok(h.label!.includes("a session in this group is blocked or waiting on you: api"), "spoken by the header's label too");
    await page.evaluate(() => (window as any).__probe.setLedger("api", { needsInput: false }));
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
    // S13b: THE WAY BACK ON THE DOOR of a header that does NOT hold the tab being read (round 3): archived's header keeps its
    // fold (toggle-group) while its count is the way back; infra's count, open and not shown, stays the door. The click puts
    // the transcript back and the store's bytes stand (archived's open state was written by the header's click); the count
    // is the door again, and takes the pane back for what follows
    let ah = await head("archived");
    assert.deepEqual([ah.act, ah.countAct, ah.countTitle, (await head("infra")).countAct], ["toggle-group", "show-transcript", sectionDoorTitle(0, 1, true), "show-group"]);
    const rawShown = await page.evaluate(() => localStorage.getItem("romp:tabgroups"));
    assert.ok(rawShown && rawShown.includes("archived"), "the header's click wrote archived's open state");
    await page.click(inHead("archived", ".tab-group-door"));
    s = await state(); ah = await head("archived");
    assert.deepEqual([s.paneShown, s.transcriptShown, s.snapView, ah.folded, ah.act, ah.countAct, s.tabs], [false, true, null, "0", "toggle-group", "show-group", ["web", "tests", "old1"]]);
    assert.equal(await page.evaluate(() => localStorage.getItem("romp:tabgroups")), rawShown, "the way back writes nothing");
    await page.click(inHead("archived", ".tab-group-door"));
    s = await state();
    assert.deepEqual([s.snapView, s.shownRows, (await head("archived")).countAct], ["archived", ["old1"], "show-transcript"]);
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

// THE TOUCHSCREEN LAPTOP (round 3 of the review). Round 2 put `(pointer: coarse)` beside `(hover: none)` for a laptop with a
// trackpad and a touchscreen, and neither fires there: `pointer` and `hover` describe the PRIMARY pointing device, which
// Chromium reports fine and hovering whenever a fine device is present, whatever the touchscreen can do; `any-pointer` is
// the union of the devices present, and the touchscreen makes it coarse. Playwright's hasTouch cannot build that laptop
// (its touch emulation makes the primary pointer coarse and the primary hover none, so the two clauses flip together),
// so Chromium is launched with Blink's own device settings: available pointer types coarse|fine (2|4) with the primary
// fine (4), available hover types none|hover (1|2) with the primary hover (2). The context is asserted before the sheet
// is, so a Chromium that stopped honouring the flag fails on the context, not on the opacity.
const LAPTOP = "--blink-settings=availablePointerTypes=6,primaryPointerType=4,availableHoverTypes=3,primaryHoverType=2";
const ONE_ROW = `<!DOCTYPE html><html><head><meta charset=utf-8><link rel=stylesheet href=/styles.css></head>
<body><div id=tab-snapshot><div class=snap-item><button class=snap-row>api</button><button class=snap-act>Hide</button></div></div></body></html>`;
type Pointing = { pointerCoarse: boolean; pointerFine: boolean; hoverNone: boolean; hoverHover: boolean; anyPointerCoarse: boolean; opacity: string };

test("in Chromium launched as a trackpad-plus-touchscreen laptop (pointer: fine, hover: hover, any-pointer: coarse): the pane's Hide stands at opacity 1 from the real sheet, where the desktop rests it at 0", async (t) => {
  let pw: any = null;
  try { pw = requireCjs("playwright"); } catch { pw = null; }
  if (!pw) { t.skip("playwright is not installed under vscode-extension (CI installs no browsers)"); return; }
  const read = async (args: string[]): Promise<Pointing> => {
    let browser: any;
    try { browser = await pw.chromium.launch({ args }); }
    catch (e) { t.skip("no playwright chromium on this box (CI installs none): " + String((e as Error).message).split("\n")[0]); return null as unknown as Pointing; }
    try {
      const page = await browser.newPage({ viewport: { width: 1000, height: 700 } });
      await page.route("http://romp.test/**", (route: any) => {
        const u = new URL(route.request().url());
        if (u.pathname === "/page") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: ONE_ROW });
        if (u.pathname === "/styles.css") return route.fulfill({ status: 200, contentType: "text/css; charset=utf-8", body: CSS });
        return route.fulfill({ status: 404, body: "" });
      });
      await page.goto("http://romp.test/page");
      return await page.evaluate(() => {
        const m = (q: string) => matchMedia(q).matches;
        return { pointerCoarse: m("(pointer: coarse)"), pointerFine: m("(pointer: fine)"), hoverNone: m("(hover: none)"), hoverHover: m("(hover: hover)"),
                 anyPointerCoarse: m("(any-pointer: coarse)"), opacity: getComputedStyle(document.querySelector(".snap-act")!).opacity };
      });
    } finally { await browser.close(); }
  };
  const laptop = await read([LAPTOP]);
  if (!laptop) return;
  assert.deepEqual([laptop.pointerCoarse, laptop.pointerFine, laptop.hoverNone, laptop.hoverHover, laptop.anyPointerCoarse], [false, true, false, true, true],
    "the laptop: the primary pointer fine and hovering (round 2's clauses both false), a coarse pointer present");
  assert.equal(laptop.opacity, "1", "the Hide stands: the sheet's any-pointer clause fired where pointer: coarse and hover: none are both false");
  const desktop = await read([]);
  if (!desktop) return;
  assert.deepEqual([desktop.pointerFine, desktop.hoverHover, desktop.anyPointerCoarse, desktop.opacity], [true, true, false, "0"],
    "the desktop: no coarse pointer anywhere, so the act rests unseen until the row's hover or focus (round 1's disclosure)");
});

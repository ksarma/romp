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
//   - the open header over a hidden member wears the compact "2+1" as a button (two tabs on the strip, one hidden;
//     the user 2026-09-08), and a click on it, on the pip or on the
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
import { headWords } from "./tab-groups";

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
  const SNAP = slice("let snapView: string | null = null;", "function showActive(");
  const ACTS = slice('"toggle-group": (el) => {', "    close: (el) => {");
  const RELEASE = slice("function releaseTabStrip(): void {", "// A SECTION HEADER for the tab strip");
  const WRITE = slice("function tabGroups() {", "let draggedGroup: string | null = null;");
  const UNFOLD = slice("function unfoldSectionOf(id: string): void {", '// "Enter to start typing"');
  return `
import { planStrip, readTabGroups, writeTabGroups, setSectionCollapsed, setHidden, prunePinned, headWords, homeSectionOf, neighborOfFolded, reachableFrom, sectionRef, TABGROUPS_KEY, TABGROUPS_EVENT } from "./tab-groups";
import { snapshotModel, snapshotHeading, rowWords, hiddenNeeds, hiddenFoldWords, actWords, standInPip } from "./tab-snapshot";
import { rowStillOpen, installSnapshotEscape, reconcileRows, repeatedClick } from "./tab-snapshot-view";
import { sectionPipTitle, sectionTodoFlag, sectionTodoTitle, sectionTodoPhrase, sectionDoorTitle, doorClick, SHOW_GROUP_CLICK } from "./tab-state";
import { tagChip } from "./tag-menu";   // the header wears the tag as its chip (upstream T251), the real builder, not a stub
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
let lastStripItems: any[] = [];
let tabPointerHeld = false;
let renderPendingWhilePressed = false;
let draggedGroup: string | null = null;
let sessionViews: any = null;
const settings: any = { stripGroupRows: false };   // render.ts's settings object (settings.ts) at the fork's default: makeGroupHead's trail branch reads it (the user 2026-09-08: the strip flows inline unless the per-row setting is on)
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
  if (collapsedTabIds.has(id)) unfoldSectionOf(id);
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
    // the header's label is the tag chip since upstream T251 (the swatch and the plain name span are gone): the click lands on it
    const nameOf = (g: string) => `#tabs .tab-group-head[data-group="${g}"] .tab-group-chip`;
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
    // ROUND 4: folded by that click, with its sessions in the pane, the header no longer promises "and see its sessions at a
    // glance": the click opens the group, and the title says that alone (the header stands in for web, the tab being read)
    assert.equal(h.title, headWords("infra", 3, 3, true, true, false, true).title, h.title);
    assert.ok(!/at a glance/.test(h.title) && h.title.endsWith("; click to open this group") && h.act === "toggle-group", h.title);

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
    assert.deepEqual([h.count, h.countTag, h.countAct, h.countTitle], ["2+1", "BUTTON", "show-transcript", sectionDoorTitle(1, 3, true)], "the compact count (the user 2026-09-08: the words took too much of the strip)");
    assert.ok(h.countTitle!.startsWith(h.count!), "label in name (round 2): the door's words lead with its visible text");
    assert.ok(h.label!.startsWith("infra, 3 sessions, 1 hidden"), h.label!);

    // S5: Escape leaves the pane; the group stays open
    await page.keyboard.press("Escape");
    s = await state(); h = await head("infra");
    assert.deepEqual([s.paneShown, s.transcriptShown, s.snapView, s.tabs], [false, true, null, ["web", "tests"]]);
    assert.ok(h.title.includes("; click to fold this group and see its sessions at a glance; "), "the pane gone, the open header's promise returns: " + h.title);

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
    // ROUND 4: the header's title in that state no longer promises to show what the pane already shows ("and see its sessions at
    // a glance") beside a count that says "shown below"; the click still folds, and the title says that alone. infra's header,
    // open and not shown, keeps the promise
    assert.equal(ah.title, headWords("archived", 1, 0, false, false, false, true).title, ah.title);
    assert.ok(!/at a glance/.test(ah.title) && ah.title.includes("; click to fold this group; ") && ah.countTitle!.includes("shown below"), ah.title + " || " + ah.countTitle);
    assert.ok((await head("infra")).title.includes("click to fold this group and see its sessions at a glance"), "the header the pane does not show keeps the promise");
    const rawShown = await page.evaluate(() => localStorage.getItem("romp:tabgroups"));
    assert.ok(rawShown && rawShown.includes("archived"), "the header's click wrote archived's open state");
    await page.click(inHead("archived", ".tab-group-door"));
    s = await state(); ah = await head("archived");
    assert.deepEqual([s.paneShown, s.transcriptShown, s.snapView, ah.folded, ah.act, ah.countAct, s.tabs], [false, true, null, "0", "toggle-group", "show-group", ["web", "tests", "old1"]]);
    assert.equal(ah.title, headWords("archived", 1, 0, false, false).title, "the transcript back: the promise returns with the door");
    assert.equal(await page.evaluate(() => localStorage.getItem("romp:tabgroups")), rawShown, "the way back writes nothing");
    await page.click(inHead("archived", ".tab-group-door"));
    s = await state();
    assert.deepEqual([s.snapView, s.shownRows, (await head("archived")).countAct], ["archived", ["old1"], "show-transcript"]);
    await page.evaluate(() => (window as any).__probe.otherPane("archived", "old1", true));
    s = await state();
    assert.deepEqual([s.hiddenRows, s.foldShown, s.foldOpen], [["old1"], true, false], "archived's fold starts closed, whatever infra's is");
    await page.click(nameOf("infra"));   // open, the pane on another section: the click folds infra and shows it
    s = await state(); h = await head("infra");
    assert.deepEqual([s.snapView, s.hiddenRows, s.foldOpen], ["infra", ["api"], true], "infra's own fold state, still open");
    assert.ok(h.folded === "1" && h.title.endsWith("; click to open this group"), "folded with its sessions in the pane (round 4): " + h.title);
    // S14: the pane gone while the header is still folded: the folded promise returns; opened again with the pane elsewhere, the open one
    await page.keyboard.press("Escape");
    s = await state(); h = await head("infra");
    assert.ok(s.snapView === null && h.folded === "1" && h.title.endsWith("; click to open and see its sessions at a glance"), h.title);
    await page.click(nameOf("infra"));   // opens infra and shows it in the pane
    s = await state(); h = await head("infra");
    assert.deepEqual([s.snapView, h.folded, s.tabs], ["infra", "0", ["web", "tests"]], "infra open again (api hidden inside it, old1 hidden inside archived)");
    assert.ok(h.title.includes("; " + BACK_TO_TRANSCRIPT_CLICK + "; "), "open, shown and holding web: the way back's words");

    // S15: A PICK UNDER TWO TAGS (T264b meets the hide; the fourth fold's review, UI-1), render.ts's own unfoldSectionOf
    // running: api under infra AND archived, hidden in infra, folded away in archived. Picked from infra's pane (its
    // Hidden fold), the pick opens archived, the folded holder that can show it, and api's tab appears there. The gate
    // used to read a hide anywhere as "hidden" and open nothing, and the unfold took the first holder, the one hiding it.
    const V_BOTH = { ...V, tags: [V.tags[0], { ...V.tags[1], members: ["old1", "api"] }], seq: 5 };
    const hiddenRow = (id: string) => `#tab-snapshot .snap-hidden-list .snap-item[data-id="${id}"] .snap-row`;
    const shownRow = (id: string) => `#tab-snapshot > .snap-list > .snap-item[data-id="${id}"] .snap-row`;
    // the stand-in's setup resets the world but not the pane (snapView) or the Hidden fold's open set, both module state
    // the slices own: leave any pane first, and open the fold only when it is closed
    const both = async () => {
      await page.evaluate(([v, sess]: [unknown, unknown]) => (window as any).__probe.setup(v, ["web", "api", "tests", "old1"], sess, "web"), [V_BOTH, SESS] as [unknown, unknown]);
      if ((await state()).paneShown) await page.keyboard.press("Escape");
      const st = await state();
      assert.deepEqual([st.paneShown, st.snapView, st.tabs], [false, null, ["web", "api", "tests"]], "api under infra and archived (folded by default): one tab, under infra");
    };
    const openFold = async () => { if (!(await state()).foldOpen) await page.click("#tab-snapshot .snap-hidden-head"); };
    await both();
    await page.evaluate(() => (window as any).__probe.otherPane("infra", "api", true));
    s = await state();
    assert.deepEqual([s.tabs, (await head("infra")).folded, (await head("archived")).folded], [["web", "tests"], "0", "1"], "api hidden in infra, folded away in archived: no tab anywhere");
    await page.click(inHead("infra", ".tab-group-door"));
    await openFold();
    s = await state();
    assert.deepEqual([s.snapView, s.hiddenRows, s.foldOpen], ["infra", ["api"], true]);
    await page.click(hiddenRow("api"));
    s = await state();
    assert.deepEqual([s.tabs, (await head("infra")).folded, (await head("archived")).folded, s.snapView, s.paneShown, s.transcriptShown],
                     [["web", "tests", "api", "old1"], "0", "0", null, false, true], "archived opened for the pick; infra's hide stands; the transcript shows");
    assert.deepEqual(s.stored.hidden, [{ sid: "api", name: "infra", id: "g1" }], "the pick wrote the fold, not the flag");
    // S16: the reverse: hidden in archived, infra folded. The pick from infra's pane opens infra, api's tab under it
    await both();
    await page.evaluate(() => (window as any).__probe.otherPane("archived", "api", true));
    await page.click(nameOf("infra"));   // folds infra and shows it: api is a shown row there
    s = await state();
    assert.deepEqual([s.tabs, s.snapView, s.shownRows], [[], "infra", ["web", "api", "tests"]], "both holders folded, api hidden only in archived");
    await page.click(shownRow("api"));
    s = await state();
    assert.deepEqual([s.tabs, (await head("infra")).folded, (await head("archived")).folded, s.snapView],
                     [["web", "api", "tests"], "0", "1", null], "infra opened for the pick; archived, hiding api, stays folded");
    // S17: hidden in both, infra folded: nothing opens; the transcript shows with a header as stand-in
    await both();
    await page.evaluate(() => (window as any).__probe.otherPane("infra", "api", true));
    await page.evaluate(() => (window as any).__probe.otherPane("archived", "api", true));
    await page.click(nameOf("infra"));
    await openFold();
    s = await state();
    assert.deepEqual([s.tabs, s.snapView, s.hiddenRows], [[], "infra", ["api"]]);
    const storedBefore = JSON.stringify(s.stored);
    await page.click(hiddenRow("api"));
    s = await state();
    assert.deepEqual([s.tabs, (await head("infra")).folded, (await head("archived")).folded, s.snapView, s.transcriptShown],
                     [[], "1", "1", null, true], "hidden in every holder: every fold stands, the transcript shows");
    assert.equal(JSON.stringify(s.stored), storedBefore, "nothing written");
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

// A TAG NAME NEVER WIDENS THE MAIN MENU (tab menu review rounds 2 to 5, 2026-09-09): the menu's rows are nowrap and the menu is sized
// by its widest row, so a row whose text carries a tag name grew the menu with the name (a 512px menu at the 40-character maximum in
// Inter, clipped at a narrow pane's edge under render.ts's clamp, which never shrinks the menu). Rounds 2 and 3 capped the sub-line at
// 36em of its own font: round 2 on .ctx-item-sub itself, which cut the Emoji row's sub-line, the widest fixed one, in the light theme's
// Space Grotesk and in a fallback face; round 3 on a modifier the Hide tab row wore, which still left the dark theme's menu 28px wider
// than its fixed rows (Emoji's sub-line is 33.1em in Inter), so a 400px pane overflowed where the base's menu fit. Round 4 made the
// rule structural (styles.css .ctx-sub-capped: the body takes the row's spare width, the label and sub-line contribute nothing to the
// menu's intrinsic width and elide) and put it on every row whose text carries a tag name, the Tags flyout's Move to and Show when
// folded rows included; round 5 takes it off the flyout, where no wide fixed row holds the menu open, so the rule collapsed the flyout
// to the New tag input's width and cut a five-character tag's Show when folded line (the next test measures the flyout). The wearers
// are the two MAIN-menu rows whose sub-line carries a tag name: the Hide tab row and the Tags row (its sub-line joins the names).
// Measured here over the real sheet with the faces served from the extension's media (the files the page loads): the dark theme's
// Inter and the light theme's Space Grotesk (body.theme-light, as theme.ts sets it), each at 450px, 400px and 383px panes, and the
// no-webfont fallback (the fonts 404'd) at 450px. Each pass inserts the rows FIRST, so the text starts the face's fetch (round 2
// awaited fonts.ready over an empty page and read the fallback face while calling it Inter), awaits document.fonts.ready and asserts
// the FontFace's own status and fonts.check, never the font-family string, then reads: the fixed sub-lines (Rename, Notify me, Emoji)
// are whole with their loaded-face widths, both tag-bearing sub-lines elide, and the menu holding the two tag-bearing rows with
// 40-character names is as wide (within 1px) as the same menu without them and stays inside the pane under the clamp at every width.
// The sub-lines are the page's own words, read from render.ts.
const INTER_PATH = path.join(EXT, "media", "InterVariable.woff2");
const SG_PATH = path.join(EXT, "media", "SpaceGroteskVariable.woff2");
const MENU_PAGE = `<!DOCTYPE html><html><head><meta charset=utf-8><link rel=stylesheet href=/styles.css><style>body{margin:0}</style></head><body></body></html>`;
type LineRead = { em: number; natural: number; elided: boolean; overflow: string };
type MenuRead = { faces: string[]; checkInter: boolean; checkSG: boolean; fixed: LineRead[]; tagged: LineRead[]; menuWidth: number; right: number; inner: number };
test("in Chromium, over the real sheet with the faces loaded: the main menu's two tag-bearing rows (menu review rounds 2 to 5: Hide tab and Tags) with 40-character names add nothing to the menu's width in Inter and in the light theme's Space Grotesk at 450px, 400px and 383px panes, and in the fallback face; their sub-lines elide; every fixed sub-line is whole, Emoji's 36.1em in Space Grotesk included; the menu stays inside the pane", async (t) => {
  let pw: any = null;
  try { pw = requireCjs("playwright"); } catch { pw = null; }
  if (!pw) { t.skip("playwright is not installed under vscode-extension (CI installs no browsers)"); return; }
  assert.ok(fs.existsSync(INTER_PATH) && fs.existsSync(SG_PATH), "the faces the page loads are in the extension's media (a missing file 404s, and the pass would read the fallback face while asserting a loaded one)");
  const inter = fs.readFileSync(INTER_PATH), sg = fs.readFileSync(SG_PATH);
  // the source pins sit BEFORE the launch (round 4): a pin that threw between chromium.launch() and the try whose finally
  // closes the browser left Chromium open, and node --test then never exited, so a sweep hung instead of going red. Each
  // read asserts with a message naming the literal, so a miss prints one line and not render.ts.
  const pick = (re: RegExp, what: string) => { const m = RENDER.match(re); assert.ok(m, `render.ts carries ${what}`); return m![1]; };
  const rename = pick(/sb\.textContent = "(the name is a label[^"]+)"; bodyEl\.appendChild\(sb\);/, "Rename's sub-line");
  const bell = pick(/"(system notification when its work blocks on you or completes)"/, "Notify me's sub-line");
  const emoji = pick(/sb\.textContent = "(one glyph before the name on the tab[^"]+)";/, "Emoji's sub-line");
  const name40 = "notes-api-customer-billing-migration-two";   // 40 characters, the New tag input's maxLength
  const other40 = "notes-api-customer-invoicing-rollout-one";
  assert.equal(name40.length, 40); assert.equal(other40.length, 40);
  const hide = `hidden in ${name40}; to show it, open the group's view`;
  for (const cls of ['"ctx-item ctx-item-toggle ctx-item-hide ctx-sub-capped"', '"ctx-item ctx-item-toggle ctx-item-tags ctx-sub-capped"'])
    assert.ok(RENDER.includes(`el("div", ${cls}`), "a tag-bearing row of the main menu wears the modifier this leg puts on its copy: " + cls);
  assert.ok(/for \(const g of others\) \{\s*\n\s*const row = el\("div", "ctx-item ctx-item-toggle"\);/.test(RENDER) && RENDER.includes('el("div", "ctx-item ctx-item-toggle ctx-item-pin" + (on ? " current" : ""));'),
    "the flyout's Move to and Show when folded rows wear no modifier (round 5): the next test measures them in the flyout, where they render");
  let browser: any;
  try { browser = await pw.chromium.launch(); }
  catch (e) { t.skip("no playwright chromium on this box (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  try {
    const pass = async (fonts: boolean, light: boolean, width: number, tagged: boolean): Promise<MenuRead> => {
      const page = await browser.newPage({ viewport: { width, height: 700 } });
      await page.route("http://romp.test/**", (route: any) => {
        const u = new URL(route.request().url());
        if (u.pathname === "/page") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: MENU_PAGE });
        if (u.pathname === "/styles.css") return route.fulfill({ status: 200, contentType: "text/css; charset=utf-8", body: CSS });
        if (fonts && u.pathname.endsWith("/InterVariable.woff2")) return route.fulfill({ status: 200, contentType: "font/woff2", body: inter });
        if (fonts && u.pathname.endsWith("/SpaceGroteskVariable.woff2")) return route.fulfill({ status: 200, contentType: "font/woff2", body: sg });
        return route.fulfill({ status: 404, body: "" });
      });
      await page.goto("http://romp.test/page");
      // the rows first, in the theme's face: the text is what starts the face's fetch. The fixed rows as render.ts builds them
      // (a 14px ctxIcon, the body with a label and a sub-line); the tag-bearing rows as their builders do: Hide tab (icon, label,
      // sub-line), Tags (icon, label, the joined names, the caret). The Move to and Show when folded rows render in the flyout, not
      // here (round 4 put copies of them in this menu, where the structural rule held; the next test builds the flyout they live in)
      await page.evaluate(([light, tagged, rename, bell, emoji, hide, name40, other40]: [boolean, boolean, string, string, string, string, string, string]) => {
        if (light) document.body.className = "theme-light";
        const el = (tag: string, cls: string) => { const e = document.createElement(tag); e.className = cls; return e; };
        const icon = () => { const ic = el("span", "ctx-icon"); ic.innerHTML = '<svg width="14" height="14" viewBox="0 0 16 14"></svg>'; return ic; };
        const body = (lab: string, sub: string | null, tag: boolean) => {
          const b = el("span", "ctx-item-body");
          const l = el("span", "ctx-item-label" + (tag ? " tagged" : "")); l.textContent = lab; b.appendChild(l);
          if (sub !== null) { const sb = el("span", "ctx-item-sub" + (tag ? " tagged" : "")); sb.textContent = sub; b.appendChild(sb); }
          return b;
        };
        const menu = el("div", "ctx-menu"); menu.id = "menu";
        for (const [lab, sub] of [["Rename", rename], ["Notify me", bell], ["Emoji…", emoji]]) {
          const item = el("div", "ctx-item ctx-item-toggle"); item.appendChild(icon()); item.appendChild(body(lab, sub, false)); menu.appendChild(item);
        }
        if (tagged) {
          const h = el("div", "ctx-item ctx-item-toggle ctx-item-hide ctx-sub-capped"); h.appendChild(icon()); h.appendChild(body("Hide tab", hide, true)); menu.appendChild(h);
          const tg = el("div", "ctx-item ctx-item-toggle ctx-item-tags ctx-sub-capped"); tg.appendChild(icon()); tg.appendChild(body("Tags", name40 + " · " + other40, true));
          const caret = el("span", "ctx-caret"); caret.textContent = "▸"; tg.appendChild(caret); menu.appendChild(tg);
        }
        document.body.appendChild(menu);
      }, [light, tagged, rename, bell, emoji, hide, name40, other40]);
      await page.evaluate(() => (document as any).fonts.ready);   // the fetch the rows started has landed (or failed) before the read
      const r = await page.evaluate(() => {
        const fontSet = (document as any).fonts;
        const faces: string[] = [];
        for (const f of fontSet as Iterable<{ family: string; status: string }>) faces.push(f.family + ":" + f.status);
        const menu = document.getElementById("menu")!;
        // render.ts's clamp (showTabMenu): at the cursor, never past the pane's right edge; the cursor here at 400px
        const rect = menu.getBoundingClientRect();
        const mx = Math.max(0, Math.min(400, window.innerWidth - rect.width - 4));
        menu.style.left = mx + "px"; menu.style.top = "10px";
        const read = (sb: Element) => { const fs = parseFloat(getComputedStyle(sb).fontSize); const b = sb.getBoundingClientRect(); return { em: +(b.width / fs).toFixed(2), natural: +(sb.scrollWidth / fs).toFixed(2), elided: sb.scrollWidth > sb.clientWidth, overflow: getComputedStyle(sb).textOverflow }; };
        return { faces, checkInter: fontSet.check("12px Inter"), checkSG: fontSet.check('12px "Space Grotesk"'),
          fixed: Array.from(menu.querySelectorAll(".ctx-item-sub:not(.tagged)")).map(read),
          tagged: Array.from(menu.querySelectorAll(".ctx-sub-capped .ctx-item-sub, .ctx-sub-capped .ctx-item-label")).filter((e) => (e.textContent || "").includes("notes-api-")).map(read),
          menuWidth: rect.width, right: menu.getBoundingClientRect().right, inner: window.innerWidth };
      });
      await page.close();
      return r as MenuRead;
    };
    const whole = (r: MenuRead, face: string) => {
      for (const [i, lab] of [[0, "Rename"], [1, "Notify me"], [2, "Emoji"]] as const) assert.equal(r.fixed[i].elided, false, `${lab}'s sub-line, a fixed one, is whole in ${face}: ${JSON.stringify(r.fixed[i])}`);
    };
    const holds = (bare: MenuRead, full: MenuRead, face: string) => {
      whole(bare, face); whole(full, face);
      // the pane: the menu with the tag-bearing rows sits where the fixed rows alone put it, so it is inside the pane wherever they are
      // (Inter's fixed rows make a 377px menu, inside all three panes; Space Grotesk's Emoji sub-line, 36.1em, makes 406px, past a
      // 400px pane with or without this PR's rows, the base's own width there) and never further right
      assert.ok(full.right <= bare.right + 1, `the tag-bearing rows never push the menu's right edge past the fixed rows' in ${face} at ${full.inner}px (right ${full.right} with them, ${bare.right} without)`);
      if (bare.right + 4 <= bare.inner) assert.ok(full.right + 4 <= full.inner, `the menu stays inside the ${full.inner}px pane under the clamp in ${face} (right ${full.right}, menu ${full.menuWidth}px; the fixed rows alone fit at ${bare.right})`);
      else assert.ok(face === "Space Grotesk" && full.inner <= 400, `only the light face's fixed rows overflow, and only under 400px: ${face} at ${full.inner}px, right ${bare.right}`);
      assert.equal(full.tagged.length, 2, "the two tag-bearing sub-lines were read: " + JSON.stringify(full.tagged));
      // each tag-bearing line is boxed by the fixed rows' width and elides when its words are wider (both sub-lines, at 0.82em, are)
      for (const l of full.tagged) assert.ok(l.overflow === "ellipsis" && (l.elided || l.natural <= l.em + 0.05), `a tag-bearing line elides when its words are wider than its box in ${face} at ${full.inner}px: ${JSON.stringify(l)}`);
      assert.equal(full.tagged.filter((l) => l.elided).length, 2, `the two 40-character sub-lines elide in ${face} at ${full.inner}px: ${JSON.stringify(full.tagged)}`);
      assert.ok(Math.abs(full.menuWidth - bare.menuWidth) <= 1, `the tag-bearing rows add nothing to the menu's width in ${face} at ${full.inner}px: ${full.menuWidth}px with them, ${bare.menuWidth}px without (round 3's 36em cap added 28px in Inter)`);
    };
    for (const width of [450, 400, 383]) {
      // the dark theme: Inter, loaded before the read (the face's own status, not the font-family string, which names Inter whether or
      // not it loaded); Rename 29.8em (round 2 read 31.8, the fallback face's), Emoji the widest fixed sub-line at 33.1em
      const dark = await pass(true, false, width, false), darkFull = await pass(true, false, width, true);
      for (const r of [dark, darkFull]) assert.ok(r.faces.includes("Inter:loaded") && r.checkInter, "Inter loaded before the read: " + JSON.stringify(r.faces));
      holds(dark, darkFull, "Inter");
      assert.ok(dark.fixed[0].em > 29 && dark.fixed[0].em < 30.5, "Rename's width is Inter's, 29.8em (31.8 is the fallback face's): " + JSON.stringify(dark.fixed[0]));
      assert.ok(dark.fixed[2].em > 32.5 && dark.fixed[2].em < 34 && dark.fixed[2].em > dark.fixed[0].em && dark.fixed[2].em > dark.fixed[1].em, "Emoji's is the widest fixed sub-line, 33.1em in Inter: " + JSON.stringify(dark.fixed[2]));
      // the light theme: Space Grotesk, loaded; Emoji's sub-line is 36.1em there, past round 3's cap, and whole because no fixed row is capped
      const light = await pass(true, true, width, false), lightFull = await pass(true, true, width, true);
      for (const r of [light, lightFull]) assert.ok(r.faces.includes("Space Grotesk:loaded") && r.checkSG, "Space Grotesk loaded before the read: " + JSON.stringify(r.faces));
      holds(light, lightFull, "Space Grotesk");
      assert.ok(light.fixed[2].em > 36 && light.fixed[2].em < 36.5, "Emoji's sub-line is 36.1em in Space Grotesk and whole: " + JSON.stringify(light.fixed[2]));
    }
    // no webfont: the fonts 404 and the host's fallback face renders (DejaVu Sans on a bare Linux box, another face elsewhere): the
    // same properties hold, with a sanity bound on the width instead of an exact one
    const fallback = await pass(false, false, 450, false), fallbackFull = await pass(false, false, 450, true);
    for (const r of [fallback, fallbackFull]) assert.ok(r.faces.includes("Inter:error") && !r.faces.includes("Inter:loaded") && !r.checkInter, "the fonts 404'd, so the fallback face read: " + JSON.stringify(r.faces));
    holds(fallback, fallbackFull, "the fallback face");
    assert.ok(fallback.fixed[2].em > 30 && fallback.fixed[2].em < 40, "Emoji's sub-line in the fallback face (36.1em in DejaVu Sans): " + JSON.stringify(fallback.fixed[2]));
  } finally { await browser.close(); }
});

// THE TAGS FLYOUT KEEPS ITS ROWS WHOLE (round 5 of the tab menu review, 2026-09-09): round 4's structural rule, worn by the
// flyout's Move to and Show when folded rows, collapsed the flyout to the New tag input's intrinsic width (231px in the dark
// theme, 191px in the light), because no wide fixed row holds a flyout open the way Rename and Emoji hold the main menu: the
// Show when folded line elided for a five-character tag and Move to labels from about sixteen characters, both whole at the
// base; round 4's leg measured copies of the two rows inside the MAIN menu, where the rule held, and passed. Round 5: no
// flyout row wears the modifier; a flyout row keeps its natural width up to a per-row cap with an ellipsis (styles.css
// .ctx-sub-tags rules: 22em for a label, 36em of its own font for a sub-line). Measured here as the flyout renders: a
// .ctx-menu.ctx-sub.ctx-sub-tags NESTED in a .ctx-menu beside a Tags row (the flyout's font compounds 0.92 x 0.92; a flat
// build overstates widths by eight percent), with the rows build() makes (a held row with its ✕, Move to rows with their +,
// the Show when folded row, the New tag input, Configure tags), in both engines and both faces, the fonts served and their
// status asserted as in the leg above. Reads: a 5-character and a 19-character destination whole, a 40-character one elided
// at the cap; the Show when folded line whole for a 5- and a 19-character home and elided for a 40-character one; the ✕ and
// the + eight pixels after their labels (the row's gap; round 4 put the + at the flyout's right edge, 74px past the label,
// while the ✕ hugged); the flyout wider than the input and no wider than the cap allows. A second pass builds thirty tags
// (ui/CLAUDE.md: a change to a tag surface is checked against thirty), placed as render.ts's place() does: every label
// under 31 characters whole, the 40-character ones elided, the + beside each; the flyout's height against a 700px pane is
// recorded (about 900px, top clamped to 0, no scroll: the base does the same, out of this change's scope).
const NAMES30 = ["qa", "infra", "docs", "archived", "notes-api", "notes-api-web", "notes-api-tests", "notes-api-invoicing",
  "notes-api-customer-billing", "notes-api-search-indexing", "notes-api-auth-and-sessions", "notes-api-mobile-sync",
  "notes-api-export-pipeline", "notes-api-rate-limits", "notes-api-onboarding", "notes-api-release-candidates",
  "notes-api-customer-billing-migration-two", "notes-api-customer-invoicing-rollout-one", "notes-api-observability-dash",
  "web", "api", "tests", "notes-api-import-jobs", "notes-api-webhooks", "notes-api-attachments", "notes-api-sharing-links",
  "notes-api-editor-collab", "notes-api-templates", "notes-api-backups-and-restore", "notes-api-search-relevance-experiments-3"];
type FlyLine = { name: string; em: number; natural: number; elided: boolean; overflow: string; gap: number | null };
type FlyRead = { faces: string[]; checkInter: boolean; checkSG: boolean; fontPx: number; held: FlyLine[]; moves: FlyLine[]; pin: FlyLine; fly: { width: number; height: number; top: number; left: number }; inputWidth: number; inner: { w: number; h: number } };
test("in Chromium and Firefox, the Tags flyout nested in the menu over the real sheet with the faces loaded (menu review round 5): a 5- and a 19-character destination whole and a 40-character one elided at the cap, the Show when folded line whole for a short home and elided for a 40-character one, the ✕ and the + beside their labels, in Inter and Space Grotesk; thirty tags: every label under 31 characters whole, the 40-character ones elided, the height recorded", async (t) => {
  let pw: any = null;
  try { pw = requireCjs("playwright"); } catch { pw = null; }
  if (!pw) { t.skip("playwright is not installed under vscode-extension (CI installs no browsers)"); return; }
  assert.ok(fs.existsSync(INTER_PATH) && fs.existsSync(SG_PATH), "the faces the page loads are in the extension's media");
  const inter = fs.readFileSync(INTER_PATH), sg = fs.readFileSync(SG_PATH);
  assert.equal(NAMES30.length, 30); assert.equal(new Set(NAMES30).size, 30);
  assert.deepEqual(NAMES30.filter((n) => n.length > 30 && n.length < 40), [], "no borderline name: under 31 characters is whole in every face and engine, 40 elides");
  assert.equal(NAMES30.filter((n) => n.length === 40).length, 3);
  const N5 = "infra", N19 = "notes-api-invoicing", N40 = "notes-api-customer-billing-migration-two";
  assert.deepEqual([N5.length, N19.length, N40.length], [5, 19, 40]);
  assert.match(CSS, /\n\.ctx-sub-tags \.ctx-item-label \{ max-width: 22em;[^\n]*\n\.ctx-sub-tags \.ctx-item-sub \{ max-width: 36em;/, "the flyout's per-row caps this leg measures");
  for (const engine of ["chromium", "firefox"] as const) {
    let browser: any;
    try { browser = await pw[engine].launch(); }
    catch (e) { t.skip(`no playwright ${engine} on this box (CI installs none): ` + String((e as Error).message).split("\n")[0]); return; }
    try {
      /** the menu with a Tags row and the flyout beside it: `held` rows with their ✕, `others` as Move to rows with their +, the pin row for `home` */
      const pass = async (light: boolean, home: string, held: string[], others: string[]): Promise<FlyRead> => {
        const page = await browser.newPage({ viewport: { width: 1200, height: 700 } });
        await page.route("http://romp.test/**", (route: any) => {
          const u = new URL(route.request().url());
          if (u.pathname === "/page") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: MENU_PAGE });
          if (u.pathname === "/styles.css") return route.fulfill({ status: 200, contentType: "text/css; charset=utf-8", body: CSS });
          if (u.pathname.endsWith("/InterVariable.woff2")) return route.fulfill({ status: 200, contentType: "font/woff2", body: inter });
          if (u.pathname.endsWith("/SpaceGroteskVariable.woff2")) return route.fulfill({ status: 200, contentType: "font/woff2", body: sg });
          return route.fulfill({ status: 404, body: "" });
        });
        await page.goto("http://romp.test/page");
        await page.evaluate(([light, home, held, others]: [boolean, string, string[], string[]]) => {
          if (light) document.body.className = "theme-light";
          const el = (tag: string, cls: string) => { const e = document.createElement(tag); e.className = cls; return e; };
          const chip = () => { const c = el("span", "ctx-tag-dot"); c.style.background = "var(--dim)"; return c; };
          const menu = el("div", "ctx-menu"); menu.id = "menu"; menu.style.left = "100px"; menu.style.top = "40px";
          // the Tags row as render.ts builds it (icon, label, the joined names, the caret), the flyout's anchor
          const tags = el("div", "ctx-item ctx-item-toggle ctx-item-tags ctx-sub-capped"); tags.id = "tags";
          const ic = el("span", "ctx-icon"); ic.innerHTML = '<svg width="14" height="14" viewBox="0 0 16 14"></svg>'; tags.appendChild(ic);
          const tb = el("span", "ctx-item-body"); const tl = el("span", "ctx-item-label"); tl.textContent = "Tags"; tb.appendChild(tl);
          const ts = el("span", "ctx-item-sub"); ts.textContent = held.join(" · "); tb.appendChild(ts); tags.appendChild(tb);
          const caret = el("span", "ctx-caret"); caret.textContent = "▸"; tags.appendChild(caret); menu.appendChild(tags);
          // the flyout as build() makes it
          const sub = el("div", "ctx-menu ctx-sub ctx-sub-tags"); sub.id = "fly";
          for (const name of held) {
            const row = el("div", "ctx-item ctx-item-toggle"); row.className += " probe-held"; row.appendChild(chip());
            const b = el("span", "ctx-item-body"); const l = el("span", "ctx-item-label"); l.textContent = name; b.appendChild(l); row.appendChild(b);
            const x = el("button", "ctx-tag-x"); (x as HTMLButtonElement).type = "button"; x.textContent = "✕"; row.appendChild(x);
            sub.appendChild(row);
          }
          if (held.length && others.length) sub.appendChild(el("div", "ctx-sep"));
          for (const name of others) {
            const row = el("div", "ctx-item ctx-item-toggle"); row.className += " probe-move"; row.appendChild(chip());
            const b = el("span", "ctx-item-body"); const l = el("span", "ctx-item-label"); l.textContent = "Move to " + name; b.appendChild(l); row.appendChild(b);
            const plus = el("button", "ctx-tag-x ctx-tag-plus"); (plus as HTMLButtonElement).type = "button"; plus.textContent = "+"; row.appendChild(plus);
            sub.appendChild(row);
          }
          sub.appendChild(el("div", "ctx-sep"));
          const pn = el("div", "ctx-item ctx-item-toggle ctx-item-pin"); pn.id = "pin"; pn.appendChild(chip());
          const pb = el("span", "ctx-item-body"); const pl = el("span", "ctx-item-label"); pl.textContent = "Show when folded"; pb.appendChild(pl);
          const ps = el("span", "ctx-item-sub"); ps.textContent = `keep this tab on the strip while ${home} is folded`; pb.appendChild(ps); pn.appendChild(pb); sub.appendChild(pn);
          sub.appendChild(el("div", "ctx-sep"));
          const nrow = el("div", "ctx-item ctx-item-newtag"); const inp = el("input", "ctx-tag-input") as HTMLInputElement; inp.placeholder = "New tag…"; inp.maxLength = 40; nrow.appendChild(inp); sub.appendChild(nrow);
          sub.appendChild(el("div", "ctx-sep"));
          const cfg = el("div", "ctx-item ctx-item-configtags"); const cb = el("span", "ctx-item-body"); const cl = el("span", "ctx-item-label"); cl.textContent = "Configure tags…"; cb.appendChild(cl); cfg.appendChild(cb); sub.appendChild(cfg);
          menu.appendChild(sub);
          document.body.appendChild(menu);
          // render.ts's place(): beside the Tags row, right when it fits, the top at the row's clamped to the pane
          const ir = tags.getBoundingClientRect(), sr = sub.getBoundingClientRect();
          if (ir.right + 2 + sr.width <= window.innerWidth - 8) sub.style.left = Math.round(ir.right + 2) + "px";
          else sub.style.left = Math.max(8, Math.round(ir.left) - sr.width - 2) + "px";
          sub.style.top = Math.max(0, Math.min(ir.top, window.innerHeight - sr.height - 4)) + "px";
        }, [light, home, held, others]);
        await page.evaluate(() => (document as any).fonts.ready);
        const r = await page.evaluate(() => {
          const fontSet = (document as any).fonts;
          const faces: string[] = [];
          for (const f of fontSet as Iterable<{ family: string; status: string }>) faces.push(f.family.replace(/"/g, "") + ":" + f.status);
          const fly = document.getElementById("fly")!;
          const fontPx = parseFloat(getComputedStyle(fly.querySelector(".ctx-item-label")!).fontSize);
          // a line: its box and natural width in its OWN em, whether it elides, and the gap from its text's end (a Range over the text
          // node; the box's right edge where the text is cut, since the range measures the whole text) to the row's button
          const read = (row: Element, sel: string, btn: string | null): FlyLine => {
            const e = row.querySelector(sel)!; const fs = parseFloat(getComputedStyle(e).fontSize); const b = e.getBoundingClientRect();
            let gap: number | null = null;
            if (btn) { const range = document.createRange(); range.selectNodeContents(e); gap = +(row.querySelector(btn)!.getBoundingClientRect().left - Math.min(range.getBoundingClientRect().right, b.right)).toFixed(1); }
            return { name: e.textContent || "", em: +(b.width / fs).toFixed(2), natural: +(e.scrollWidth / fs).toFixed(2), elided: e.scrollWidth > e.clientWidth, overflow: getComputedStyle(e).textOverflow, gap };
          };
          const fr = fly.getBoundingClientRect();
          return { faces, checkInter: fontSet.check("12px Inter"), checkSG: fontSet.check('12px "Space Grotesk"'), fontPx,
            held: Array.from(fly.querySelectorAll(".probe-held")).map((row) => read(row, ".ctx-item-label", ".ctx-tag-x")),
            moves: Array.from(fly.querySelectorAll(".probe-move")).map((row) => read(row, ".ctx-item-label", ".ctx-tag-plus")),
            pin: read(document.getElementById("pin")!, ".ctx-item-sub", null),
            fly: { width: fr.width, height: fr.height, top: fr.top, left: fr.left },
            inputWidth: (fly.querySelector(".ctx-tag-input") as HTMLElement).getBoundingClientRect().width,
            inner: { w: window.innerWidth, h: window.innerHeight } };
        });
        await page.close();
        return r as FlyRead;
      };
      const faceOf = (r: FlyRead, light: boolean, where: string) => {
        if (light) assert.ok(r.faces.includes("Space Grotesk:loaded") && r.checkSG, `Space Grotesk loaded before the read (${where}): ` + JSON.stringify(r.faces));
        else assert.ok(r.faces.includes("Inter:loaded") && r.checkInter, `Inter loaded before the read (${where}): ` + JSON.stringify(r.faces));
        return light ? "Space Grotesk" : "Inter";
      };
      const whole = (l: FlyLine, what: string) => assert.ok(!l.elided && l.natural <= l.em + 0.05, `${what} is whole: ${JSON.stringify(l)}`);
      const elided = (l: FlyLine, what: string) => assert.ok(l.elided && l.overflow === "ellipsis" && l.natural > l.em + 0.05, `${what} elides at the cap: ${JSON.stringify(l)}`);
      const beside = (l: FlyLine, what: string) => assert.ok(l.gap !== null && Math.abs(l.gap - 8) <= 1, `${what}'s button sits eight pixels after its label, the row's gap (round 4 put the + 74px past a short label): ${JSON.stringify(l)}`);
      for (const light of [false, true]) {
        for (const home of [N5, N19, N40]) {
          const others = [N5, N19, N40].filter((n) => n !== home);
          const r = await pass(light, home, [home], others);
          const face = faceOf(r, light, `${engine}, home ${home.length}`);
          const where = `${engine}, ${face}, home ${home.length} characters`;
          assert.ok(Math.abs(r.fontPx - 11) < 0.2, `the flyout's font is the compounded 11px (0.92 x 0.92 of 13px), not a flat build's 12px: ${r.fontPx} (${where})`);
          assert.equal(r.moves.length, 2); assert.equal(r.held.length, 1);
          for (const m of r.moves) {
            const n = m.name.replace(/^Move to /, "").length;
            if (n === 40) elided(m, `the 40-character destination (${where})`); else whole(m, `the ${n}-character destination (${where})`);
            beside(m, `the Move to row (${where})`);
          }
          const h = r.held[0];
          if (home.length === 40) assert.ok(h.natural > 19, `a 40-character held name is 19em or more (${where}): ${JSON.stringify(h)}`); else whole(h, `the ${home.length}-character held name (${where})`);
          beside(h, `the held row (${where})`);
          if (home.length === 40) elided(r.pin, `the Show when folded line for a 40-character home (${where})`);
          else whole(r.pin, `the Show when folded line for a ${home.length}-character home (${where}; round 4 cut it at ${r.inputWidth}px, the input's width)`);
          assert.ok(r.fly.width > r.inputWidth + 40, `the flyout is sized by its rows, not collapsed to the input (${where}): fly ${r.fly.width}, input ${r.inputWidth}`);
          assert.ok(r.fly.width <= 36 * 0.82 * r.fontPx + 100, `the flyout is no wider than its widest capped line and the row's chrome allow (${where}): ${r.fly.width}px`);
        }
        // THIRTY TAGS (ui/CLAUDE.md): the first held, the other 29 as Move to rows, placed by place()
        const r30 = await pass(light, NAMES30[0], [NAMES30[0]], NAMES30.slice(1));
        const face = faceOf(r30, light, `${engine}, thirty`);
        assert.equal(r30.moves.length, 29);
        const cut = r30.moves.filter((m) => m.elided).map((m) => m.name.replace(/^Move to /, ""));
        assert.deepEqual(cut.sort(), NAMES30.filter((n) => n.length === 40).sort(), `at thirty tags exactly the 40-character labels elide (${engine}, ${face}): ${JSON.stringify(r30.moves.map((m) => [m.name.length - 8, m.em, m.natural, m.elided]))}`);
        for (const m of r30.moves) { beside(m, `a Move to row among thirty (${engine}, ${face})`); assert.equal(m.overflow, "ellipsis"); }
        whole(r30.pin, `the Show when folded line for the two-character home among thirty (${engine}, ${face})`);
        assert.ok(r30.fly.width <= 22 * r30.fontPx + 100 && r30.fly.width > r30.inputWidth + 40, `thirty tags: the flyout's width is the capped label's plus the row's chrome (${engine}, ${face}): ${r30.fly.width}px`);
        t.diagnostic(`${engine}, ${face}, thirty tags: flyout ${Math.round(r30.fly.width)}x${Math.round(r30.fly.height)}px at top ${Math.round(r30.fly.top)} in a ${r30.inner.h}px pane (the height overflows the pane and the top clamps to 0 with no scroll: the base does the same, out of this change's scope); ${cut.length} of 29 labels elide, the 40-character ones`);
      }
    } finally { await browser.close(); }
  }
});

// THE MENU UNDER A PRESSED POINTER (round 5 of the tab menu review): render.ts's own showTabMenu, sliced verbatim and bundled
// with the real tab-groups, session-views and actions modules over a stand-in for the rest of the page (the maps and helpers
// named as render.ts names them; the same shape tab-hide.test's harness uses), run in headless Chromium and Firefox with the
// real sheet and REAL pointer input. Round 4 re-dressed the Hide tab row with replaceChildren on every hook run and rebuilt the
// flyout's rows on a signature change, so a push between a mousedown and its mouseup replaced the pressed node and the click
// was lost (no click at the row, the menu or the document, in both engines). Round 5 parks the hook's whole run through one
// pressHold(menu) while the pointer is down and runs it on the release, a tick after the click. Read here with the mouse:
//   - a press on the Hide tab row's label, a rename pushed mid-press, the release: the click lands (the hide is written for
//     the same copy by its id, the menu dismissed), and the re-dress never painted a dismissed menu;
//   - a press on a Move to row's label in the flyout, a recolour pushed mid-press (a signature change, so the rows would have
//     been rebuilt), the release: the move is posted;
//   - the same on the Show when folded row: the pin is written;
//   - a push that changes nothing the row shows leaves its label node in place (round 4 replaced it every time).
function menuProbeSource(): string {
  const a = RENDER.indexOf("function showTabMenu(e: MouseEvent, id: string, copy?: string) {");
  const end = RENDER.indexOf("seatMenu(e.clientX, e.clientY);", a);
  const b = RENDER.indexOf("\n}\n", end) + 3;
  assert.ok(a > 0 && end > a && b > end, "showTabMenu's anchors moved; re-anchor this probe");
  const MENU = RENDER.slice(a, b);
  return `
import { readTabGroups, writeTabGroups, prunePinned, sectionRef, isPinned, setPinned, isHidden, setHidden, TABGROUPS_KEY } from "./tab-groups";
import { viewTagUnion } from "./session-views";
import { pressHold } from "./actions";
// THE STAND-IN PAGE: what showTabMenu reads, declared as render.ts declares it
const sessions = new Map<string, any>([["api", { name: "api", status: { state: "working" } }], ["web", { name: "web", status: { state: "ready" } }]]);
const tabMeta = new Map<string, any>();
const paletteColors: string[] = [];
const H: any = { views: null, hides: [] as any[], edits: [] as any[], dismissed: 0, renders: 0, flags: [] as any[] };
let ctxMenuEl: HTMLElement | null = null, ctxMenuAt: any = null, tagsFlyNewInput: HTMLInputElement | null = null, pendingSessionViews: any = null;
let tabMenuViewsHook: () => void = () => {};
function el(tag: string, cls?: string): HTMLElement { const e = document.createElement(tag); if (cls) e.className = cls; return e; }
function ctxIcon(kind: string, off: boolean): HTMLElement { const sp = el("span", "ctx-icon" + (off ? " off" : "")); sp.innerHTML = '<svg width="14" height="14" viewBox="0 0 16 14"></svg>'; sp.dataset.kind = kind; return sp; }
function dismissTabMenu() { H.dismissed++; ctxMenuEl?.remove(); ctxMenuEl = null; tagsFlyNewInput = null; tabMenuViewsHook = () => {}; }
function closeEmojiPrompt() {}
function setSessionFlag(id: string, k: string, v: boolean) { H.flags.push([id, k, v]); }
function setSessionColor() {} function startTabRename() {} function showMovePrompt() {} function showEmojiPrompt() {}
function billingSubText() { return ""; }
const vscodeApi: any = null;
function renderTabs() { H.renders++; }
function postTagEdit(nv: any, op: any) { H.edits.push(op); H.views = nv; }
function syncNewTagInput() {}
function createInFlight() { return false; }
const viewsWrites: any[] = [];
function viewTags(v: any) { return (v && v.tags) || []; }
function effViews() { return H.views; }
function phoneLayout() { return false; }
function knownTabIds() { return new Set<string>(["api", "web", "tests", "old1", "old2"]); }
function reachableHosts() { return new Set<string>(); }
function tabGroups() { return readTabGroups(viewTagUnion(effViews())); }
function writeTabGroupsPruned(st: any) { const out = prunePinned(st, viewTagUnion(effViews()), knownTabIds(), reachableHosts()); H.hides.push(out.hidden); writeTabGroups(out); }
function browseRouteNow() { return "pane"; } function openBrowse() {}
${MENU}
let marked: Element | null = null;
const rowOf = () => ctxMenuEl?.querySelector(".ctx-item-hide") ?? null;
const flyRow = (label: string) => Array.from(ctxMenuEl?.querySelectorAll(".ctx-sub-tags .ctx-item") ?? []).find((r) => r.querySelector(".ctx-item-label")?.textContent === label) ?? null;
const rect = (e: Element | null) => { if (!e) return null; const r = e.getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; };
(window as any).__menu = {
  setup(v: any) { localStorage.removeItem(TABGROUPS_KEY); H.views = v; H.hides = []; H.edits = []; H.dismissed = 0; },
  open(id: string, copy: string, x: number, y: number) { showTabMenu({ clientX: x, clientY: y } as MouseEvent, id, copy); return !!ctxMenuEl; },
  openFly() { (ctxMenuEl!.querySelector(".ctx-item-tags") as HTMLElement).click(); return !!ctxMenuEl!.querySelector(".ctx-sub-tags"); },
  push(v: any) { H.views = v; tabMenuViewsHook(); },   // as viewsChanged runs the hook after the blob is held
  rowLabelAt() { return rect(rowOf()?.querySelector(".ctx-item-label") ?? null); },
  flyLabelAt(label: string) { return rect(flyRow(label)?.querySelector(".ctx-item-label") ?? null); },
  mark() { marked = rowOf()?.querySelector(".ctx-item-label") ?? null; return !!marked; },
  sameLabel() { return !!marked && rowOf()?.querySelector(".ctx-item-label") === marked; },
  state() {
    const row = rowOf();
    return { menu: !!ctxMenuEl && ctxMenuEl.isConnected, label: row?.querySelector(".ctx-item-label")?.textContent ?? null, sub: row?.querySelector(".ctx-item-sub")?.textContent ?? null,
      hides: H.hides, edits: H.edits, dismissed: H.dismissed, flyRows: Array.from(ctxMenuEl?.querySelectorAll(".ctx-sub-tags .ctx-item-label") ?? []).map((l) => l.textContent),
      stored: JSON.parse(localStorage.getItem(TABGROUPS_KEY) || "null") };
  },
};
`;
}
function bundleMenu(): string {
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    stdin: { contents: menuProbeSource(), resolveDir: UI, loader: "ts", sourcefile: "tab-menu-probe.ts" },
    bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], logLevel: "silent",
  });
  return r.outputFiles[0].text;
}
const MENU_PROBE_PAGE = `<!DOCTYPE html><html><head><meta charset=utf-8><link rel=stylesheet href=/styles.css><style>body{margin:0}</style></head><body><script src=/menu-probe.js></script></body></html>`;
type MenuState = { menu: boolean; label: string | null; sub: string | null; hides: any[][]; edits: any[]; dismissed: number; flyRows: (string | null)[]; stored: any };
test("in Chromium and Firefox, render.ts's own showTabMenu with real pointer input (menu review round 5): a push between mousedown and mouseup on the Hide tab row, a Move to row or the Show when folded row waits for the release, so the click lands (the hide written by the copy's id, the move posted, the pin written) and the rebuild follows; a push that changes nothing the row shows leaves its label node", async (t) => {
  let pw: any = null;
  try { pw = requireCjs("playwright"); } catch { pw = null; }
  if (!pw) { t.skip("playwright is not installed under vscode-extension (CI installs no browsers)"); return; }
  const js = bundleMenu();
  const V_QA = { ...V, tags: [{ ...V.tags[0], members: ["web", "api", "tests"] }, { ...V.tags[1], members: ["old1", "api"] }, { id: "g5", name: "qa", color: "#7aa2f7", members: [] as string[] }], seq: 6 };   // api under infra and archived, qa empty
  const renamed = (v: typeof V_QA, name: string, seq: number) => ({ ...v, tags: v.tags.map((tg, i) => (i === 0 ? { ...tg, name } : tg)), seq });
  const recoloured = (v: typeof V_QA, seq: number) => ({ ...v, tags: v.tags.map((tg, i) => (i === 1 ? { ...tg, color: "#abcdef" } : tg)), seq });
  for (const engine of ["chromium", "firefox"] as const) {
    let browser: any;
    try { browser = await pw[engine].launch(); }
    catch (e) { t.skip(`no playwright ${engine} on this box (CI installs none): ` + String((e as Error).message).split("\n")[0]); return; }
    try {
      const page = await browser.newPage({ viewport: { width: 1000, height: 700 } });
      const errors: string[] = [];
      page.on("pageerror", (e: Error) => { errors.push(e.message); });
      await page.route("http://romp.test/**", (route: any) => {
        const u = new URL(route.request().url());
        if (u.pathname === "/page") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: MENU_PROBE_PAGE });
        if (u.pathname === "/menu-probe.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: js });
        if (u.pathname === "/styles.css") return route.fulfill({ status: 200, contentType: "text/css; charset=utf-8", body: CSS });
        return route.fulfill({ status: 404, body: "" });
      });
      await page.goto("http://romp.test/page");
      const menu = (fn: string, ...args: unknown[]) => page.evaluate(([fn, args]: [string, unknown[]]) => (window as any).__menu[fn](...args), [fn, args] as [string, unknown[]]);
      const state = (): Promise<MenuState> => menu("state") as Promise<MenuState>;
      const settle = () => page.evaluate(() => new Promise((r) => setTimeout(r, 20)));   // pressHold's zero timer at the release, and the browser's own click dispatch
      const where = (what: string) => `${engine}: ${what}`;
      const open = async (copy: string) => { await menu("setup", V_QA); assert.ok(await menu("open", "api", copy, 40, 40), where("the menu opened")); assert.deepEqual(errors, [], where("the slice ran against the stand-in (a ReferenceError means render.ts grew a dependency the probe lacks)")); };
      // M1: THE HIDE TAB ROW. Press on its label; the rename pushed mid-press; release. The click lands on the node the user pressed and
      // writes the hide for the same copy under its new name (by the id), the menu is dismissed, and the parked run paints nothing
      await open("infra");
      let s = await state();
      assert.deepEqual([s.label, s.sub, s.menu], ["Hide tab", "hidden in infra; to show it, open the group's view", true], where("the row as built"));
      const d0 = s.dismissed;   // showTabMenu dismisses any earlier menu as it opens; the click's own dismissal is the one counted
      let at = await menu("rowLabelAt") as { x: number; y: number };
      await page.mouse.move(at.x, at.y);
      await page.mouse.down();
      await menu("push", renamed(V_QA, "platform", 7));
      const midPress = (await state()).sub;
      await page.mouse.up();
      await settle();
      s = await state();
      assert.deepEqual(s.hides, [[{ sid: "api", name: "platform", id: "g1" }]], where("the click landed: the hide written for the same copy by its id (round 4 lost the click to the mid-press replaceChildren)"));
      assert.deepEqual([s.dismissed, s.menu], [d0 + 1, false], where("dismissed by the click; the parked re-dress found the menu gone"));
      assert.equal(midPress, "hidden in infra; to show it, open the group's view", where("under the press the row still read infra (the re-dress was parked)"));
      // M2: A MOVE TO ROW in the flyout. Press on its label; a recolour of another tag pushed mid-press (a signature change: the flyout
      // would have been rebuilt); release: the move is posted, one op, from infra to qa
      await open("infra");
      assert.ok(await menu("openFly"), where("the flyout opened"));
      s = await state();
      assert.ok(s.flyRows.includes("Move to qa"), where("the Move to qa row: " + JSON.stringify(s.flyRows)));
      at = await menu("flyLabelAt", "Move to qa") as { x: number; y: number };
      await page.mouse.move(at.x, at.y);
      await page.mouse.down();
      await menu("push", recoloured(V_QA, 8));
      await page.mouse.up();
      await settle();
      s = await state();
      assert.deepEqual(s.edits, [{ op: "move", tid_from: "g1", tid_to: "g5", sid: "api" }], where("the click landed: the move posted (round 4 rebuilt the pressed row and lost the click)"));
      assert.equal(s.sub, "hidden in qa; to show it, open the group's view", where("the Hide tab row follows the move"));
      // M3: THE SHOW WHEN FOLDED ROW: the same press, a recolour mid-press, the release: the pin is written for infra
      await open("infra");
      assert.ok(await menu("openFly"));
      at = await menu("flyLabelAt", "Show when folded") as { x: number; y: number };
      await page.mouse.move(at.x, at.y);
      await page.mouse.down();
      await menu("push", recoloured(V_QA, 9));
      await page.mouse.up();
      await settle();
      s = await state();
      assert.deepEqual(s.stored?.pinned, [{ sid: "api", name: "infra", id: "g1" }], where("the click landed: the pin written"));
      // M4: an unchanged push leaves the row's label node in place (round 4 re-dressed on every run); a changing push replaces it
      await open("infra");
      assert.ok(await menu("mark"));
      await menu("push", { ...V_QA, tags: [V_QA.tags[0], { ...V_QA.tags[1], members: ["api"] }, V_QA.tags[2]], seq: 10 });   // old1 left archived: nothing the row shows
      await settle();
      assert.equal(await menu("sameLabel"), true, where("unchanged words: the same label node"));
      await menu("push", renamed(V_QA, "platform", 11));
      await settle();
      assert.equal(await menu("sameLabel"), false, where("changed words: re-dressed"));
      assert.equal((await state()).sub, "hidden in platform; to show it, open the group's view");
      assert.deepEqual(errors, [], where("no page errors"));
      await page.close();
    } finally { await browser.close(); }
  }
});
